# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 三枚玉を「要求の表」で設計する ―― 縁厚・中心厚・空気間隔の境界つきメリット関数を、閉形式と独立実装で採点する。

【問い】(1) 設計者のメリット関数は「ここの縁厚は 1 mm 以上、EFL は 50 mm、波面は小さく」という要求の表である。
その表を、行ごとに目標・重み・片側の境界として持ち、最適化が何に引っ張られているかを行ごとの割合で言えるか。
(2) 硝材を変数にして離散の外側ループで選ばせると、色収差はどれだけ落ちるか。
新 op 6 本(`lensmerit`、`opsoptics` の `lensmerit`): `merit_operands_list` / `merit_evaluate` / `merit_default` /
`merit_boundary_operands` / `optimize_lens_operands` / `merit_contributions`。連続変数の最適化は `lensopt` の変数・
減衰最小二乗・刻みをそのまま使い、硝材 `g<i>` だけを外側で候補から選ぶ。5 章:

  1. **閉形式**: 薄肉色消し 2 枚(EFFL と AXCL = 0 の最適化が φ1 = φV1/(V1−V2)、φ2 = −φV2/(V1−V2) に着く)、
     平凸の縁厚 t − (R − √(R²−h²))(1e-12)、全長、屈折球面の実光線の高さ、理想レンズの作動 F ナンバー。
  2. **突き合わせ**: 既定の表(スポット)が `lensopt.merit_function` と相対 1e-9 で一致。別の独立実装(MIT ライセンスの
     公開ライブラリ)が出した EFL・像面の実光線の位置・OPD(記録値、`tests/data/lensmerit_optiland_ref.json`)と合う。
  3. **三枚玉**: 縁が薄く、EFL が 50 mm から外れた出発点を、波面(3 視野 × F・d・C)+ EFL の保持 + 境界(縁厚 ≥ 1 mm、
     中心厚 2〜8 mm、空気間隔 ≥ 0.5 mm)の表で最適化する。行ごとの割合が「EFL の保持」から「軸外の波面」へ移る。
  4. **硝材を変数に**: 負レンズの硝材を間違えた(クラウン)出発点を、軸上色・倍率色の行を足した表で、連続変数だけ・
     連続変数 + `g2`(6 種のモデル硝材)の 2 通りで最適化する。硝材は連続変数では直せない。
  5. **壊して確かめる**: 未知のオペランド、重みが全部 0、範囲外の視野、届かない縁厚の境界。

【外部真値】薄肉色消しの閉形式(Smith / Kingslake)、屈折球面の Snell の式、理想レンズの F ナンバー・倍率、別実装の記録値。
【学習】0。【較正】0。
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import lensmerit as LM  # noqa: E402
import lensopt as LO  # noqa: E402
import raytrace as RT  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"
FAILS: list[str] = []
GATES: list[str] = []
NUMBERS: dict[str, float] = {}
INF = float("inf")

#: 古典的な 40° 三枚玉の半径と間隔(公開のサンプル、MIT)を、すべて 7〜10 % ずらしたものが出発点
RS = [22.01359, -435.76044, -22.21328, 20.29192, 79.6836, -18.39533]
MULT = [1.08, 0.90, 0.93, 1.10, 0.92, 1.07]
CROWN = (1.62041, 60.32)             # モデル硝材 (n_d, V_d)。銘柄は使わない
FLINT = (1.62004, 36.37)
GLASS = [CROWN, 1.0, FLINT, 1.0, CROWN, 1.0]
T0 = [2.2, 6.0, 1.0, 4.7, 1.9, None]          # 最後の厚みは None(像面は近軸の焦点に取り直される)
AP = [4.0, 4.8, 5.2, 5.6, 7.2, 7.4]           # 前玉が絞り。後ろの玉は 12° の主光線と周辺光線が通る大きさ
FIELDS = [0.0, 8.4, 12.0]
WLS = [RT.WL_F, RT.WL_D, RT.WL_C]
GRID = [(1.52, 64.2), CROWN, (1.72, 50.5), FLINT, (1.72, 29.3), (1.80, 25.4)]     # 6 種のモデル硝材
VARS = ["c0", "c1", "c2", "c3", "c4", "c5", "t0", "t1", "t2", "t3", "t4"]
REF_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tests", "data", "lensmerit_optiland_ref.json")


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


def start_system():
    surf = [{"R": RS[i] * MULT[i], "t": T0[i], "n": GLASS[i], "ap": AP[i]} for i in range(6)]
    return RT.lens_system(surf, stop=0, field=12.0, wavelength_um=RT.WL_D)


def with_glass(system, i, medium):
    surf = [dict(s) for s in system["surfaces"]]
    surf[i]["n"] = medium
    return RT.lens_system(surf, stop=system["stop"], object_mm=system["object_mm"], wavelength_um=system["wavelength_um"],
                          field=system["field"])


def one(system, row, **kw):
    return LM.merit_evaluate(system, [dict(row, target=row.get("target", 0.0))], **kw)["table"][0]["value"]


# --------------------------------------------------------------------------- #
def chapter_closed_forms():
    print("\n1. 閉形式")
    n1, v1, n2, v2 = 1.5168, 64.17, 1.6200, 36.37
    phi = 0.01
    p1, p2 = phi * v1 / (v1 - v2), -phi * v2 / (v1 - v2)
    c0 = 0.012
    c1 = c0 - p1 / (n1 - 1.0)
    c2 = c1 - p2 / (n2 - 1.0)

    def pair(a, b, c):
        return RT.lens_system([{"R": 1 / a, "t": 0.0, "n": (n1, v1), "ap": 5.0}, {"R": 1 / b, "t": 0.0, "n": (n2, v2)},
                               {"R": 1 / c, "t": None, "n": 1.0}], stop=0, object_mm=INF)

    ops = [{"op": "EFFL", "target": 100.0, "weight": 1.0}, {"op": "AXCL", "target": 0.0, "weight": 10.0}]
    r = LM.optimize_lens_operands(pair(1.3 * c0, 0.7 * c1, 1.4 * c2), ops, ["c0", "c1", "c2"], iterations=80,
                                  tolerance=1e-14, min_thickness=0.0)
    s = r["system"]
    g1 = (n1 - 1.0) * (1 / s["surfaces"][0]["R"] - 1 / s["surfaces"][1]["R"])
    g2 = (n2 - 1.0) * (1 / s["surfaces"][1]["R"] - 1 / s["surfaces"][2]["R"])
    e1, e2 = abs(g1 / p1 - 1.0), abs(g2 / p2 - 1.0)
    print("   薄肉色消し: 出発点の EFL %.1f mm → %.4f mm、屈折力の閉形式との相対差 %.1e / %.1e(merit %.2e → %.2e)" % (
        RT.paraxial_trace(pair(1.3 * c0, 0.7 * c1, 1.4 * c2))["efl"], RT.paraxial_trace(s)["efl"], e1, e2,
        r["merit_initial"], r["merit_final"]))
    gate("EFFL = 100 と AXCL = 0 の最適化が、閉形式の屈折力の配分 φ1 = φV1/(V1−V2)、φ2 = −φV2/(V1−V2) に 1e-4 以内で着く",
         max(e1, e2) < 1e-4, "%.1e" % max(e1, e2))
    NUMBERS["achromat_split_err"] = max(e1, e2)

    worst = 0.0
    for R, t, h in ((50.0, 4.0, 10.0), (30.0, 6.5, 12.0), (-80.0, 3.0, 20.0), (120.0, 2.0, 5.0)):
        s1 = RT.lens_system([{"R": R, "t": t, "n": 1.5, "ap": h}, {"R": INF, "t": 30.0, "n": 1.0, "ap": h}], stop=0)
        sag = R - np.sign(R) * np.sqrt(R * R - h * h)
        worst = max(worst, abs(one(s1, {"op": "ETGT", "surf": 0}) - (t - sag)))
    gate("平凸の縁厚は t − (R − √(R²−h²)) と 1e-12 以内(4 通り)", worst < 1e-12, "%.1e" % worst)

    tp = start_system()
    gate("全長 TOTR は厚みの和と 1e-12 以内(像面を近軸の焦点に取る最後の厚みも含む)",
         abs(one(tp, {"op": "TOTR"}) - (sum(t for t in T0[:5]) + RT.paraxial_trace(tp)["bfl"])) < 1e-12)

    R, n, d, ap = 50.0, 1.5, 30.0, 5.0
    s2 = RT.lens_system([{"R": R, "t": d, "n": n, "ap": ap}], stop=0)
    worst = 0.0
    for py in (0.2, 0.6, 0.9):
        h = py * ap
        ti = np.arcsin(h / R)
        tt = np.arcsin(np.sin(ti) / n)
        zs = R - np.sqrt(R * R - h * h)
        worst = max(worst, abs(one(s2, {"op": "REAY", "surf": 1, "py": py}) - (h - (d - zs) * np.tan(ti - tt))),
                    abs(one(s2, {"op": "RAID", "surf": 0, "py": py}) - np.degrees(ti)))
    gate("屈折球面の実光線の高さ REAY と入射角 RAID は Snell の式と 1e-12 以内", worst < 1e-12, "%.1e" % worst)

    f, h = 1000.0, 0.5
    ideal = RT.lens_system([{"f": f, "t": None, "ap": h}], stop=0)
    err = abs(one(ideal, {"op": "WFNO"}) / (f / (2 * h)) - 1.0)
    gate("理想レンズの作動 F ナンバー WFNO は f/2h と相対 1e-6 以内", err < 1e-6, "%.1e" % err)

    cat = LM.merit_operands_list()
    one_sided = [o["name"] for o in cat["operands"] if o["sense"] != "eq"]
    print("   オペランド %d 個(スカラー %d、群 %d)、片側の既定: %s" % (
        cat["n_operands"], sum(o["kind"] == "scalar" for o in cat["operands"]), sum(o["kind"] == "group" for o in cat["operands"]),
        " ".join(one_sided)))
    gate("オペランドの一覧は 32 個(スカラー 30 + 群 2。2026-10-20 に afocal の ANGM / RSAN を足した)で、全部に意味・単位・引数があり、"
         "片側は CTGT/CTLT/ETGT/ETLT/MNCG/MXCG/MNCA/MXCA の 8 個",
         cat["n_operands"] == 32 and all(o["description"] and isinstance(o["unit"], str) for o in cat["operands"])
         and sorted(one_sided) == sorted(["CTGT", "CTLT", "ETGT", "ETLT", "MNCG", "MXCG", "MNCA", "MXCA"]))


def chapter_consistency():
    print("\n2. 突き合わせ")
    s = start_system()
    worst = 0.0
    for kw in ({}, {"fields": FIELDS}, {"fields": FIELDS, "wavelengths": WLS, "rings": 3}):
        kw = dict(kw)
        kw.setdefault("rings", 4)
        ref = LO.merit_function(s, efl_target=RT.paraxial_trace(s)["efl"], pupil_fill=0.98, **kw)["merit"]
        got = LM.merit_evaluate(s, LM.merit_default(s, kind="spot", reference="chief", **kw))["merit"]
        worst = max(worst, abs(got - ref) / ref)
    gate("既定の表(スポット、主光線基準)の merit は lensopt.merit_function と相対 1e-9 以内(3 通りの視野・波長)", worst < 1e-9,
         "%.1e" % worst)
    NUMBERS["default_vs_lensopt"] = worst
    a = LM.merit_evaluate(s, LM.merit_default(s, reference="chief", fields=FIELDS, rings=3, pupil_fill=0.9))["merit"]
    b = LM.merit_evaluate(s, LM.merit_default(s, reference="centroid", fields=FIELDS, rings=3, pupil_fill=0.9))["merit"]
    gate("重心基準の merit は主光線基準を超えない(重心が二乗和を最小にする)", b <= a, "%.4g ≤ %.4g" % (b, a))
    e = one(s, {"op": "RSCE", "field": 2}, fields=FIELDS)
    h = one(s, {"op": "RSCH", "field": 2}, fields=FIELDS)
    gate("主光線まわりの RMS スポット RSCH は重心まわりの RSCE 以上", h >= e, "%.4f ≥ %.4f mm" % (h, e))
    if os.path.exists(REF_PATH):
        ref = json.load(open(REF_PATH, encoding="utf-8"))
        rs = [22.01359, -435.76044, -22.21328, 20.29192, 79.6836, -18.39533]
        ts = [3.25896, 6.00755, 0.99997, 4.75041, 2.95208, 42.20778]
        ns = [1.62041, 1.0, 1.62004, 1.0, 1.62041, 1.0]
        sc = RT.lens_system([{"R": rs[i], "t": ts[i], "n": ns[i], "ap": 4.0 if i == 0 else None} for i in range(6)],
                            stop=0, wavelength_um=0.58756)
        fl = [0.0, 14.0, 20.0]
        d_efl = abs(one(sc, {"op": "EFFL"}) - ref["efl"])
        d_xy = 0.0
        for key, (rx, ry) in ref["image_xy"].items():
            fi, px, py = key.split(",")
            for op, rv in (("REAX", rx), ("REAY", ry)):
                d_xy = max(d_xy, abs(one(sc, {"op": op, "surf": 6, "field": int(fi), "px": float(px), "py": float(py)}, fields=fl) - rv))
        gate("独立実装(MIT の公開ライブラリ)の記録値と EFL・像面の実光線(3 瞳点 × 2 視野)が 1e-6 mm 以内",
             d_efl < 1e-6 and d_xy < 1e-6, "EFL %.1e、実光線 %.1e mm" % (d_efl, d_xy))
        NUMBERS.update({"second_impl_efl": d_efl, "second_impl_xy": d_xy})
    else:
        print("   (独立実装の記録値 %s が無いので、この門は飛ばす)" % os.path.basename(REF_PATH))


def edge_margins(system, bound=1.0):
    ev = LM.merit_evaluate(system, [{"op": "ETGT", "surf": i, "target": bound} for i in (0, 2, 4)])
    return [r["margin"] for r in ev["table"]], [r["value"] for r in ev["table"]]


def group_rows(table):
    """表を図の棒にまとめる: 波面の行は視野ごとに足す。"""
    out = []
    for f in range(3):
        rows = [r for r in table if r["op"] == "OPDW" and r["args"]["field"] == f]
        out.append(("波面%d" % f, sum(r["percent"] for r in rows)))
    out.append(("EFL", sum(r["percent"] for r in table if r["op"] == "EFFL")))
    for k, i in enumerate((0, 2, 4)):
        out.append(("縁%d" % (k + 1), sum(r["percent"] for r in table if r["op"] == "ETGT" and r["args"]["surf"] == i)))
    out.append(("中心厚", sum(r["percent"] for r in table if r["op"] in ("MNCG", "MXCG"))))
    out.append(("空気", sum(r["percent"] for r in table if r["op"] in ("MNCA", "MXCA"))))
    return out


def chapter_triplet():
    print("\n3. 三枚玉(メリット関数 = 波面 + EFL の保持 + 境界)")
    s0 = start_system()
    md = LM.merit_default(s0, kind="wavefront", fields=FIELDS, wavelengths=WLS, rings=3, pupil_fill=0.9, efl_target=50.0)
    bd = LM.merit_boundary_operands(s0, min_edge=1.0, min_centre=2.0, max_centre=8.0, min_air=0.5, weight=100.0)
    ops = md["operands"] + bd["operands"]
    kw = dict(fields=FIELDS, wavelengths=WLS)
    t0 = time.process_time()
    r = LM.optimize_lens_operands(s0, ops, VARS, iterations=40, max_thickness=9.0, **kw)
    print("   %d 行の表(波面 %d + EFL 1 + 境界 %d)、変数 %d 個: merit %.4g → %.4g(%d 反復、却下 %d、%s、CPU %.1f s)" % (
        r["table_before"]["n_operands"], len(FIELDS) * len(WLS), bd["n_operands"], len(VARS), r["merit_initial"], r["merit_final"],
        r["iterations"], r["rejected_steps"], r["status"], time.process_time() - t0))
    cs = r["system"]
    tb, ta = r["table_before"]["table"], r["table_after"]["table"]
    print("   メリット関数への寄与の割合 [%]    開始 → 最適化後")
    for (lab, p0), (_l, p1) in zip(group_rows(tb), group_rows(ta)):
        print("     %-8s %7.2f → %7.2f" % (lab, p0, p1))
    m0, v0 = edge_margins(s0)
    m1, v1 = edge_margins(cs)
    print("   縁厚 [mm]: 開始 %s → 最適化後 %s(境界 1.0)" % (" ".join("%.3f" % v for v in v0), " ".join("%.3f" % v for v in v1)))
    efl = RT.paraxial_trace(cs)["efl"]
    gate("merit は 1000 分の 1 以下に下がる", r["merit_final"] < 1e-3 * r["merit_initial"],
         "%.4g → %.4g(1/%.0f)" % (r["merit_initial"], r["merit_final"], r["merit_initial"] / r["merit_final"]))
    gate("EFL は 50 mm に 2e-3 mm 以内で保たれる", abs(efl - 50.0) < 2e-3, "%.5f mm(出発点 %.2f)" % (efl, RT.paraxial_trace(s0)["efl"]))
    gate("出発点は縁厚の境界(1 mm)を破っている(開始の最小の余裕が負)", min(m0) < 0.0, "余裕 %s" % " ".join("%+.3f" % v for v in m0))
    viol = max(0.0, -min(x["margin"] for x in r["table_after"]["table"] if x["margin"] is not None))
    gate("最適化後は全部の境界(縁厚・中心厚・空気間隔)が 0.02 mm 以内で守られる", viol < 0.02, "最大の破れ %.4f mm" % viol)
    lost = sum(x.get("rays_lost", 0) for x in ta) + sum(x.get("rays_lost", 0) for x in tb)
    gate("開始・最適化後とも、どの光線も失われない(口径でけられない)", lost == 0)
    dom0 = r["table_before"]["dominant"]
    dom1 = r["table_after"]["dominant"]
    pe0 = [x["percent"] for x in tb if x["op"] == "EFFL"][0]
    pe1 = [x["percent"] for x in ta if x["op"] == "EFFL"][0]
    print("   支配する行: %s(%.1f %%) → %s" % (dom0, max(x["percent"] for x in tb), dom1))
    gate("開始は EFL の保持が最大の行(50 % 以上)で、最適化後は 1 % 未満になって波面の行へ移る",
         pe0 > 50.0 and pe0 == max(x["percent"] for x in tb) and pe1 < 1.0 and dom1.startswith("OPDW"), "EFL %.1f %% → %.2f %%" % (pe0, pe1))
    cc = LM.merit_contributions(cs, ops, top=3, **kw)
    print("   最適化後の上位 3 行: " + "、".join("%s %.1f %%" % (x["label"], x["percent"]) for x in cc["contributions"]))
    gate("merit_contributions の先頭は最適化後の表の支配する行で、割合は大きい順",
         cc["dominant"]["label"] == dom1 and [x["percent"] for x in cc["contributions"]] == sorted(
             (x["percent"] for x in cc["contributions"]), reverse=True))
    again = LM.optimize_lens_operands(s0, ops, VARS, iterations=40, max_thickness=9.0, **kw)
    gate("同じ入力は同じ結果(履歴・半径・厚みが一致)", again["history"] == r["history"] and
         [x["R"] for x in again["system"]["surfaces"]] == [x["R"] for x in cs["surfaces"]])
    NUMBERS.update({"merit_initial": r["merit_initial"], "merit_final": r["merit_final"], "efl_final": efl})
    spots = {}
    for tag, sysd in (("before", s0), ("after", cs)):
        spots[tag] = []
        for f in FIELDS:
            b = RT.ray_bundle(sysd, field=f, rings=6, pupil_fill=1.0)
            d = (b["image_xy"] - b["chief_xy"])[b["valid"]]
            spots[tag].append(d)
    for tag in ("before", "after"):
        print("   RMS スポット(%s)軸上 / 8.4° / 12°: %s µm" % ("開始" if tag == "before" else "最適化後", " / ".join(
            "%.1f" % (1e3 * np.sqrt(np.mean(np.sum(d * d, 1)))) for d in spots[tag])))
    return r, cs, md, spots, (m0, m1)


def axial_colour(system):
    return one(system, {"op": "AXCL"})


def lateral_colour(system):
    return one(system, {"op": "LACL", "field": 2}, fields=FIELDS)


def chapter_glass(cs, md):
    print("\n4. 硝材を変数に(負レンズの硝材を間違えた出発点)")
    wrong = with_glass(cs, 2, CROWN)
    colour = [{"op": "AXCL", "target": 0.0, "weight": 20.0}, {"op": "LACL", "field": 2, "target": 0.0, "weight": 2000.0}]
    bd = LM.merit_boundary_operands(wrong, min_edge=1.0, min_centre=2.0, max_centre=8.0, min_air=0.5, weight=100.0)
    ops = md["operands"] + bd["operands"] + colour
    kw = dict(fields=FIELDS, wavelengths=WLS, max_thickness=9.0)
    it = 40
    t0 = time.process_time()
    rc = LM.optimize_lens_operands(wrong, ops, VARS, iterations=it, **kw)
    t1 = time.process_time()
    rg = LM.optimize_lens_operands(wrong, ops, VARS + ["g2"], iterations=it, glass_candidates=GRID,
                                   glass_iterations=6 if REDUCED else 8, outer_iterations=1 if REDUCED else 2, **kw)
    t2 = time.process_time()
    g = rg["glass"][0]
    print("   連続変数だけ: merit %.4g → %.4g(CPU %.1f s)。+ g2: → %.4g(CPU %.1f s、却下 %d)" % (
        rc["merit_initial"], rc["merit_final"], t1 - t0, rg["merit_final"], t2 - t1, rg["rejected_steps"]))
    print("   g2 の候補(最初の外側ループ、再最適化後の merit): " + "、".join(
        "(%.2f, %.1f) %.4g" % (t["candidate"][0], t["candidate"][1], t["merit"]) for t in g["tried"][:len(GRID) - 1]))
    print("   g2: (%.5f, %.2f) → (%.5f, %.2f)" % (g["initial"] + g["final"]))
    a_c, a_g = axial_colour(rc["system"]), axial_colour(rg["system"])
    l_c, l_g = lateral_colour(rc["system"]), lateral_colour(rg["system"])
    a_w, l_w = axial_colour(wrong), lateral_colour(wrong)
    print("   軸上色 AXCL [mm]: 間違えた硝材 %+.4f → 連続変数だけ %+.4f → + g2 %+.6f" % (a_w, a_c, a_g))
    print("   倍率色 LACL(12°) [mm]: %+.5f → %+.5f → %+.7f" % (l_w, l_c, l_g))
    gate("連続変数だけでは軸上色を直せない(最適化後も |AXCL| > 0.5 mm)", abs(a_c) > 0.5, "%+.4f mm" % a_c)
    gate("g2 を変数にすると高分散のフリント(V_d < 40)が選ばれる", g["changed"] and g["final"][1] < 40.0,
         "(%.5f, %.2f)" % g["final"])
    gate("軸上色は 10 分の 1 以下、倍率色は 50 分の 1 以下に落ちる", abs(a_g) < abs(a_c) / 10.0 and abs(l_g) < abs(l_c) / 50.0,
         "AXCL 1/%.0f、LACL 1/%.0f" % (abs(a_c / a_g), abs(l_c / l_g)))
    gate("merit は連続変数だけの 1/5 以下", rg["merit_final"] < 0.2 * rc["merit_final"],
         "%.4g → %.4g(1/%.1f)" % (rc["merit_final"], rg["merit_final"], rc["merit_final"] / rg["merit_final"]))
    gate("硝材の候補は最初の外側ループで全部試される(エラーなし)",
         all(t["error"] is None for t in g["tried"][:len(GRID) - 1]) and len(g["tried"]) >= len(GRID) - 1)
    NUMBERS.update({"axcl_cont": a_c, "axcl_glass": a_g, "lacl_cont": l_c, "lacl_glass": l_g,
                    "merit_cont": rc["merit_final"], "merit_glass": rg["merit_final"]})
    return wrong, rc, rg


def chapter_probes():
    print("\n5. 壊して確かめる")
    s = start_system()
    cases = [
        ("未知のオペランド", lambda: LM.merit_evaluate(s, [{"op": "NOPE", "target": 0}])),
        ("重みが全部 0 の表(空のメリット)", lambda: LM.merit_evaluate(s, [{"op": "EFFL", "target": 50.0, "weight": 0.0}])),
        ("範囲外の視野の添字", lambda: LM.merit_evaluate(s, [{"op": "RSCE", "field": 5, "target": 0.0}], fields=FIELDS)),
        ("足りない引数(面の番号)", lambda: LM.merit_evaluate(s, [{"op": "ETGT", "target": 1.0}])),
        ("硝材の変数に候補が無い", lambda: LM.optimize_lens_operands(s, None, ["c0", "g0"])),
    ]
    ok = 0
    for name, fn in cases:
        try:
            fn()
        except ValueError as e:
            ok += 1
            print("   %s → ValueError: %s" % (name, str(e)[:90]))
    gate("壊した入力 5 通りがすべて ValueError", ok == len(cases))
    ops = [{"op": "EFFL", "target": RT.paraxial_trace(s)["efl"]}, {"op": "RSCH", "target": 0.0},
           {"op": "ETGT", "surf": 0, "target": 50.0}]
    r = LM.optimize_lens_operands(s, ops, ["c0", "c1", "t0"], iterations=15, max_thickness=6.0, fields=FIELDS)
    row = [x for x in r["table_after"]["table"] if x["op"] == "ETGT"][0]
    gate("届かない縁厚の境界(50 mm)は、支配する行として報告され、最後の表に破れが残る",
         r["dominant_after"] == "ETGT(surf=0)" and not row["satisfied"] and row["margin"] < -40.0 and row["percent"] > 99.0,
         "余裕 %.1f mm、割合 %.2f %%" % (row["margin"], row["percent"]))


# --------------------------------------------------------------------------- #
def _fit(img, w, h):
    """絵を (h, w, 3) の白地に左上詰めで置く(凡例で広がった絵もそろえる)。"""
    out = np.ones((h, w, 3))
    hh, ww = min(h, img.shape[0]), min(w, img.shape[1])
    out[:hh, :ww] = img[:hh, :ww]
    return out


def _row(panels):
    w = max(p.shape[1] for p in panels)
    h = max(p.shape[0] for p in panels)
    return np.concatenate([_fit(p, w, h) for p in panels], axis=1)


def _stack(rows):
    w = max(r.shape[1] for r in rows)
    return np.concatenate([_fit(r, w, r.shape[0]) for r in rows], axis=0)


def _bars(groups_a, title):
    import fullseye as fs
    size = (440, 340)
    n = len(groups_a)
    x = np.arange(1, n + 1, dtype=float)
    y = np.array([v for _, v in groups_a])
    img = figs.render_plot([("寄与 [%]", x, y)], title=title, size=size, kinds=["bar"], colors=["emphasis"],
                           xlim=(0.5, n + 0.5), ylim=(0.0, max(100.0, float(y.max()))), xlabel="", ylabel="寄与 [%]")
    w, h = size
    x0, y0, rw, rh = 72, 44, w - 96, h - 108
    for i, (lab, _v) in enumerate(groups_a):
        px = x0 + (i + 0.5) / n * rw
        img = np.asarray(fs.text_box(img, lab, (px, y0 + rh + 22), anchor="ct", font_size=9))
    return img


def _spot(d, title, lim=None):
    d = d * 1e3
    m = float(np.abs(d).max()) * 1.1 if lim is None else lim
    return figs.render_plot([("", d[:, 0], d[:, 1])], title=title, size=(330, 300), kinds=["scatter"], colors=["emphasis"],
                            xlim=(-m, m), ylim=(-m, m), aspect="equal", xlabel="x [µm]", ylabel="y [µm]")


def _poly(system, title, lim):
    series, colors = [], ["reference", "right", "wrong"]
    ref = RT.ray_bundle(system, field=12.0, rings=5, wavelength_um=RT.WL_D)["chief_xy"]
    for wl, lab in zip(WLS, ("F", "d", "C")):
        b = RT.ray_bundle(system, field=12.0, rings=5, wavelength_um=wl)
        d = (b["image_xy"] - ref)[b["valid"]] * 1e3
        series.append((lab, d[:, 0], d[:, 1]))
    return figs.render_plot(series, title=title, size=(330, 300), kinds=["scatter"] * 3, colors=colors,
                            xlim=(-lim, lim), ylim=(-lim, lim), aspect="equal", xlabel="x [µm]", ylabel="y [µm]")


def make_figure(r, spots, margins, wrong, rc, rg):
    tb, ta = r["table_before"]["table"], r["table_after"]["table"]
    row1 = _row([_bars(group_rows(tb), "開始: 何がメリット関数を引っ張るか"),
                 _bars(group_rows(ta), "最適化後"),
                 figs.render_plot([("開始", [0.8, 1.8, 2.8], margins[0]), ("最適化後", [1.2, 2.2, 3.2], margins[1])],
                                  title="縁厚の余裕(縁厚 − 1.0 mm)", size=(440, 340), kinds=["bar", "bar"],
                                  colors=["wrong", "right"], xlim=(0.4, 3.6), xlabel="素子 1 / 2 / 3", ylabel="余裕 [mm]")])
    names = ["軸上", "8.4°", "12°"]
    row2 = _row([_spot(d, "開始 %s: RMS %.0f µm" % (n, 1e3 * np.sqrt(np.mean(np.sum(d * d, 1))))) for n, d in zip(names, spots["before"])])
    row3 = _row([_spot(d, "最適化後 %s: RMS %.1f µm" % (n, 1e3 * np.sqrt(np.mean(np.sum(d * d, 1))))) for n, d in zip(names, spots["after"])])
    wl = np.linspace(0.46, 0.68, 12)
    series = []
    for sysd, lab, col in ((rc["system"], "連続変数だけ(硝材が違う)", "wrong"), (rg["system"], "+ g2(硝材を選ぶ)", "right")):
        b = [RT.paraxial_trace(RT.with_wavelength(sysd, w))["bfl"] for w in wl]
        series.append((lab, wl, (np.array(b) - RT.paraxial_trace(sysd)["bfl"]) * 1e3))
    lim = 1.2 * max(float(np.abs((RT.ray_bundle(q, field=12.0, rings=5, wavelength_um=w)["image_xy"]
                                  - RT.ray_bundle(q, field=12.0, rings=5, wavelength_um=RT.WL_D)["chief_xy"])[
        RT.ray_bundle(q, field=12.0, rings=5, wavelength_um=w)["valid"]]).max()) * 1e3 for q in (rc["system"], rg["system"]) for w in WLS)
    row4 = _row([figs.render_plot(series, title="焦点位置の波長依存(d 線から)", size=(440, 300), colors=["wrong", "right"],
                                  xlabel="波長 [µm]", ylabel="BFL(λ) − BFL(d) [µm]"),
                 _poly(rc["system"], "12°: 連続変数だけ", lim), _poly(rg["system"], "12°: + g2", lim)])
    figs.save("lens_merit_operands", _stack([row1, row2, row3, row4]),
              caption="上段: 左 開始・中 最適化後 = メリット関数への寄与の割合(波面は視野ごとに合算)、右 = 素子ごとの縁厚の余裕。"
                      "2・3 段: 開始と最適化後のスポット(3 視野)。下段: 負レンズの硝材を間違えた出発点を、連続変数だけで最適化した場合と "
                      "硝材 g2 を変数にした場合の焦点位置の波長依存と、12° の F・d・C のスポット。")
    a, b = spots["before"][2], spots["after"][2]
    frames = []
    merits = np.geomspace(r["merit_initial"], r["merit_final"], 32)
    for i, merit in enumerate(merits):
        u = i / (len(merits) - 1)
        d = (1.0 - u) * a + u * b
        frames.append(figs.video_frame(_spot(d, "", lim=1.1 * 1e3 * np.abs(a).max()),
                                      "merit %.4g" % merit))
    assert len(frames) >= 24
    assert np.ptp(np.stack(frames).astype(np.int16), axis=0).max() > 0
    figs.save_video("merit_spot_optimization", frames,
                    caption="最適化に伴い12度視野のスポットが収束する。", fps=10.0,
                    gif_every=2, gif_fps=5.0, gif_width=480)


def main():
    t0 = time.time()
    c0 = time.process_time()
    print("PoC 要求の表で三枚玉を設計する(予算 %s)" % ("reduced" if REDUCED else "full"))
    chapter_closed_forms()
    chapter_consistency()
    r, cs, md, spots, margins = chapter_triplet()
    wrong, rc, rg = chapter_glass(cs, md)
    chapter_probes()
    if not REDUCED and figs.target_dir() is not None:
        make_figure(r, spots, margins, wrong, rc, rg)
    cpu = time.process_time() - c0
    print("\n所要 CPU %.1f s(壁時計 %.1f s)、門 %d 件中 NG %d 件" % (cpu, time.time() - t0, len(GATES), len(FAILS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
