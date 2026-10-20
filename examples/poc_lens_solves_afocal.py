# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 設計の関係を「解(solve)」で持つ ―― 絞りを変えても焦点と F ナンバーが追従する二重ガウス型、afocal 望遠鏡、曲面の像面、奇数次の非球面。

【問い】(1) 設計は数字の並びではなく関係の束である。「像面は近軸の焦点」「F/# は 5」「この面は前の面と同心」を数字でなく
**規則**として持てば、絞りの半径や硝材を変えたときに残りが自分で解き直されるか。(2) 像側が平行光の系(望遠鏡)を、焦点距離でなく
角倍率と**角度の収差**(分角)で語れるか。(3) 像面を曲面にすると、ペッツバール湾曲の分だけスポットが縮むか。(4) 非球面に r¹・r³ の奇数次と
r² の項を足すと、何ができるか。
新 op 9 本(`lenssolve`、`opsoptics` の `lenssolve`): `lens_apply_solves` / `lens_solve_set` / `lens_solve_clear` / `lens_solves_list` /
`afocal_system` / `lens_afocal_report` / `lens_image_surface` / `lens_petzval_radius` / `lens_zmx_solves_roundtrip`。規則は面の辞書に
`solve` として載り(傍らの `R` / `t` は解いた値)、`raytrace` の追跡のたびに解き直される。種類は、厚みの解(主光線・主光線の高さ、近軸の像)、
曲率の解(主光線・主光線の角度、F ナンバー、同心、アプラナティック)、ピックアップ(曲率・厚み・非球面係数)。`raytrace` には像面の曲率
(`image_R`)、`afocal`、非球面の `a2`(r² の項)と `odd`(rⁱ、i = 1..8)を足した。6 章:

  1. **閉形式**: 主光線の高さ・角度の解は 1 本の線形方程式の手解き(1e-12)、F/# の解は根が 2 本(正負の屈折力)で閉形式の両方と一致、
     アプラナティックな面は物点を**厳密に**結像(全光線のスポット 1e-9 以下)、同心の玉は中心へ向かう光線を曲げない。
  2. **二重ガウス型**: 最終素子の曲率に F/# の解、像距離に近軸の像の解。絞りの半径を 5.0 → 7.6 mm と動かすと解が解き直され、F/# は 5 のまま、
     像面は焦点に追従する。解かずに数字を固めた版と並べる(F/# は 6.3 → 4.2 に流れる)。限界: F/# の解は根が 2 本で、近い方を採る。
  3. **afocal**: 理想レンズのケプラー・ガリレイ望遠鏡の角倍率は ∓4 で全光線・全視野に厳密(角度の収差 0)。実ガラスの 2 つの色消し 2 枚の望遠鏡は
     角度のスポットを分角で出す。afocal の印は `.zmx` を往復する。
  4. **曲面の像面**: 非点収差を 0 にした薄いメニスカスで、ペッツバール半径の像面は 0.7 視野のスポットを平らな像面の 1/9 にする。
  5. **奇数次の非球面**: r¹(円錐)の板は軸上の光線を軸の 1 点でなく**線**に集め、その位置は閉形式と 1e-9 で合う(軸子レンズ)。球面収差の補正板は
     r⁴ が 466 分の 1、r³ は 7 分の 1 まで。
  6. **`.zmx` と壊して確かめる**: 3 種のピックアップ + 規則が `.zmx` を往復して不動点、解の無い入力は ValueError。

【外部真値】近軸の線形方程式の手解き(Smith / Kingslake)、屈折球面のアプラナティック点(Weierstrass)、理想レンズの薄肉レンズの式、
円錐面の Snell の式、ペッツバール半径 −N f と Seidel 和。【学習】0。【較正】0。
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import lensfile as LF  # noqa: E402
import lenssolve as LS  # noqa: E402
import raytrace as RT  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"
FAILS: list[str] = []
GATES: list[str] = []
NUMBERS: dict[str, float] = {}
INF = float("inf")
CROWN, FLINT = (1.5168, 64.17), (1.6200, 36.37)          # モデル硝材 (n_d, V_d)。銘柄は使わない
HERE = os.path.dirname(os.path.abspath(__file__))
DG_PATH = os.path.join(HERE, "..", "tests", "data", "lensfile", "double_gauss_const.zmx")
#: 色消し 2 枚の半径(lensopt で F・d・C の 3 波長・3 視野を最適化した値を固定した)。物体側と接眼側
RO = [51.00259848782082, -42.9290918429939, -279.5654884185966]       # f ≈ 100.7 mm、F/5
RE = [15.635438573448113, -8.857785946688509, -31.813007197894247]    # f ≈ 25.0 mm(集光する向きに設計、使うときは反転)
RINGS = 4 if REDUCED else 6


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


def rebuild(system, surfaces=None, **kw):
    """辞書を直した系を作り直す(規則は辞書に載っているので、作り直しで解き直される)。"""
    return RT.lens_system(surfaces if surfaces is not None else [dict(s) for s in system["surfaces"]],
                          stop=system["stop"], object_mm=system["object_mm"], wavelength_um=system["wavelength_um"],
                          index_object=system["index_object"], image_mm=system["image_mm"], field=system["field"],
                          aim=system.get("aim", "paraxial"), vignetting=system.get("vignetting"),
                          **dict(RT._system_extras(system), **kw))


# --------------------------------------------------------------------------- #
def chapter_closed_forms():
    print("\n1. 閉形式(解は 1 本の線形方程式の手解きと合う)")
    # (a) 主光線の高さ: n' u' = n u - y c (n' - n)、y' = y + t u'
    y0, c, n = 5.0, 1.0 / 50.0, 1.5
    u1 = -y0 * c * (n - 1.0) / n
    worst = 0.0
    for h in (1.5, 3.25):
        s = RT.lens_system([{"R": 50.0, "t": None, "n": n, "ap": y0, "solve": {"kind": "marginal_ray_height", "h": h}},
                            {"R": INF, "t": 20.0, "n": 1.0}], stop=0)
        worst = max(worst, abs(s["surfaces"][0]["t"] - (h - y0) / u1))
    gate("主光線の高さの解: 厚みは (h − y)/u' と 1e-12 以内(h = 1.5, 3.25)", worst < 1e-12, "%.1e" % worst)
    NUMBERS["marginal_height_err"] = worst

    # (b) 角度の解
    ang = -2.0
    s = RT.lens_system([{"R": 80.0, "t": 4.0, "n": n, "ap": y0, "solve": {"kind": "marginal_ray_angle", "angle_deg": ang}},
                        {"R": INF, "t": 30.0, "n": 1.0}], stop=0)
    want = -1.5 * math.tan(math.radians(ang)) / (y0 * 0.5)
    err = abs(1.0 / s["surfaces"][0]["R"] - want)
    gate("周辺光線の角度の解: 曲率は (n u − n' u')/(y (n' − n)) と 1e-12 以内", err < 1e-12, "%.1e" % err)

    # (c) F/# の解: 根が 2 本(正と負の屈折力)
    n, c1, t, F = 1.5, 1.0 / 60.0, 3.0, 4.0
    nu1 = -y0 * c1 * (n - 1.0)
    y1 = y0 + t * nu1 / n
    roots = sorted((sg / (2.0 * F) - nu1) / (0.5 * y1) for sg in (1.0, -1.0))
    lens = RT.lens_system([{"R": 60.0, "t": t, "n": n, "ap": y0}, {"R": -60.0, "t": 40.0, "n": 1.0}], stop=0)
    sv = LS.lens_solve_set(lens, 1, "f_number", fno=F)
    row = LS.lens_solves_list(sv)["solves"][0]
    err = max(abs(a - b) for a, b in zip(row["roots"], roots))
    print("   F/# 4 の解の根 c = %s(閉形式 %s)。採った枝 %d、そのときの F/# %.12f" % (
        ["%.8f" % r for r in row["roots"]], ["%.8f" % r for r in roots], row["branch"], RT.paraxial_trace(sv)["fno"]))
    gate("F/# の解は根が 2 本で、閉形式の 2 根と 1e-9 以内。F/# は 4 に 1e-9 で着く",
         row["n_roots"] == 2 and err < 1e-9 and abs(RT.paraxial_trace(sv)["fno"] / F - 1.0) < 1e-9, "%.1e" % err)

    # (d) アプラナティック: 厳密に結像する
    s_obj, n2 = 10.0, 1.5
    lens = RT.lens_system([{"R": -3.0, "t": 0.0, "n": n2, "ap": 3.0, "solve": {"kind": "aplanatic"}},
                           {"R": INF, "t": 5.0, "n": n2}], stop=0, object_mm=s_obj)
    R = lens["surfaces"][0]["R"]
    lp = R * (1.0 + n2) / n2
    rms = RT.spot_stats(lens, field=0.0, rings=8, image_mm=lp)["rms_radius"]
    bad = RT.lens_system([{"R": -3.0, "t": 0.0, "n": n2, "ap": 3.0}, {"R": INF, "t": 5.0, "n": n2}], stop=0, object_mm=s_obj)
    rms_bad = RT.spot_stats(bad, field=0.0, rings=8, image_mm=lp)["rms_radius"]
    print("   アプラナティックな面 R = %.6f mm(−s n/(n + n') = %.6f)、虚像 %.4f mm のスポット RMS %.1e mm(R = −3 mm なら %.1e mm)" % (
        R, -s_obj / (1.0 + n2), lp, rms, rms_bad))
    gate("アプラナティックな面は物点を厳密に結像する(スポット 1e-9 mm 以下)。普通の半径では 1e-3 mm 以上",
         rms < 1e-9 and rms_bad > 1e-3 and abs(R + s_obj / (1.0 + n2)) < 1e-12)
    NUMBERS["aplanatic_rms"] = rms

    # (e) 同心の玉
    ball = RT.lens_system([{"R": 20.0, "t": 10.0, "n": 1.7, "ap": 9.0},
                           {"R": -5.0, "t": 30.0, "n": 1.0, "ap": 9.0, "solve": {"kind": "concentric"}}], stop=0)
    P = np.array([[0.0, 5.0, -30.0], [0.0, -3.0, -10.0], [4.0, 0.0, -25.0]])
    D = np.array([0.0, 0.0, 20.0]) - P
    D = D / np.linalg.norm(D, axis=1, keepdims=True)
    tr = RT.trace_rays(ball, P, D)
    dev = float(np.max(np.abs(tr["dirs"][:, -1, :] - D)))
    gate("同心の玉: 共通の中心へ向かう光線は 2 面とも垂直に当たり、曲がらない(方向の差 1e-12 以内)",
         tr["valid"].all() and dev < 1e-12 and abs(ball["surfaces"][1]["R"] - 10.0) < 1e-13, "%.1e" % dev)
    NUMBERS["concentric_dev"] = dev


# --------------------------------------------------------------------------- #
def chapter_double_gauss():
    print("\n2. 二重ガウス型: 絞りを動かしても焦点と F/# が追従する")
    p = LF.lens_file_read(DG_PATH)
    s0 = p["system"]
    stop = s0["stop"]
    ap0 = s0["surfaces"][stop]["ap"]
    s1 = LS.lens_solve_set(s0, 10, "paraxial_image")              # 像距離 = 近軸の焦点
    s2 = LS.lens_solve_set(s1, 9, "f_number", fno=5.0)            # 最終素子の前面の曲率で F/# = 5
    rows = LS.lens_solves_list(s2)["solves"]
    before = [dict(x) for x in s2["surfaces"]]
    res = LS.lens_apply_solves(s2)
    again = LS.lens_apply_solves(res)
    pure = (s2["surfaces"] == before and res["surfaces"][9]["solve"]["kind"] == "f_number"
            and all(a["R"] == b["R"] and a["t"] == b["t"] for a, b in zip(res["surfaces"], again["surfaces"])))
    gate("lens_apply_solves は純粋: 入力の辞書を変えず、規則を残し、2 回掛けても同じ(R9 = %.4f mm、t10 = %.4f mm)" % (
        res["surfaces"][9]["R"], res["surfaces"][10]["t"]), pure)
    print("   規則: " + "、".join("面 %d %s" % (r["surface"], r["kind"]) for r in rows) + "(1 面に規則は 1 つ)")
    aps = [5.0, 5.7, ap0, 7.0, 7.6]
    tab = []
    froz = LS.lens_solve_clear(s2)
    print("   絞りの半径 [mm] | 解いた R9 [mm] | 像距離 t10 [mm] | EFL [mm] |  F/# | RMS(軸上/10°) [µm] || 数字を固めた版: EFL [mm] | F/# | RMS(軸上/10°) [µm]")
    for ap in aps:
        surf = [dict(x) for x in s2["surfaces"]]
        surf[stop]["ap"] = ap
        a = rebuild(s2, surf)
        pa = RT.paraxial_trace(a)
        sf = [{k: v for k, v in x.items() if k != "solve"} for x in froz["surfaces"]]
        sf[stop]["ap"] = ap
        b = rebuild(froz, sf)
        pb = RT.paraxial_trace(b)
        r0, r10 = (RT.spot_stats(a, field=f, rings=RINGS)["rms_radius"] * 1e3 for f in (0.0, 10.0))
        b0, b10 = (RT.spot_stats(b, field=f, rings=RINGS)["rms_radius"] * 1e3 for f in (0.0, 10.0))
        tab.append({"ap": ap, "R9": a["surfaces"][9]["R"], "t10": a["surfaces"][10]["t"], "efl": pa["efl"], "fno": pa["fno"],
                    "bfl": pa["bfl"], "fno_frozen": pb["fno"], "efl_frozen": pb["efl"],
                    "rms": (r0, r10), "rms_frozen": (b0, b10)})
        print("   %5.2f | %9.3f | %9.4f | %8.3f | %.5f | %6.1f / %6.1f || %8.3f | %.4f | %6.1f / %6.1f" % (
            ap, a["surfaces"][9]["R"], a["surfaces"][10]["t"], pa["efl"], pa["fno"], r0, r10, pb["efl"], pb["fno"], b0, b10))
    gate("絞りの半径を 5 通りに動かしても F/# は 5 に 1e-9 以内で追従する",
         all(abs(t["fno"] / 5.0 - 1.0) < 1e-9 for t in tab), "最大 %.1e" % max(abs(t["fno"] / 5.0 - 1.0) for t in tab))
    gate("像距離は近軸の焦点(BFL)に 1e-12 以内で追従する", all(abs(t["t10"] / t["bfl"] - 1.0) < 1e-12 for t in tab),
         "最大 %.1e" % max(abs(t["t10"] / t["bfl"] - 1.0) for t in tab))
    gate("解かない版(数字を固めた系)は F/# が %.2f 〜 %.2f に流れる" % (min(t["fno_frozen"] for t in tab), max(t["fno_frozen"] for t in tab)),
         max(t["fno_frozen"] for t in tab) - min(t["fno_frozen"] for t in tab) > 1.5)
    print("   ★正直な限界: F/# を保ったまま絞りを開く(5.0 → 7.6 mm)と、最終素子の曲率が 79 → 768 mm と大きく動く。ほかの面は設計し直していないので、"
          "10° のスポットは %.1f → %.1f µm と悪化する面もある(解は関係を保つだけで、性能は保証しない)" % (
              tab[0]["rms"][1], tab[-1]["rms"][1]))
    NUMBERS.update({"dg_fno_err": max(abs(t["fno"] / 5.0 - 1.0) for t in tab), "dg_R9_min": tab[0]["R9"], "dg_R9_max": tab[-1]["R9"],
                    "dg_fno_frozen_min": min(t["fno_frozen"] for t in tab), "dg_fno_frozen_max": max(t["fno_frozen"] for t in tab)})
    row = [r for r in rows if r["kind"] == "f_number"][0]
    print("   F/# の解の根(曲率 c9 [1/mm]): %s、採った枝 %d(開始の曲率に近い方)。もう一方は EFL が負、F/# の大きさは同じ" % (
        ["%.6f" % r for r in row["roots"]], row["branch"]))
    other = [r for r in row["roots"] if abs(r - row["chosen"]) > 1e-9][0]
    surf = [{k: v for k, v in x.items() if k != "solve"} for x in s2["surfaces"]]
    surf[9]["R"] = 1.0 / other
    alt = rebuild(s2, surf)
    pe = RT.paraxial_trace(alt)
    print("   もう一方の根: R9 = %.3f mm、EFL %.3f mm、F/# %.5f" % (1.0 / other, pe["efl"], pe["fno"]))
    gate("F/# の解は 2 根を報告し、もう一方の根は EFL の符号が逆で F/# の大きさは同じ",
         row["n_roots"] == 2 and pe["efl"] < 0 and abs(pe["fno"] / 5.0 - 1.0) < 1e-9)
    try:
        LS.lens_solve_set(s1, 9, "f_number", fno=1.0)
        gate("届かない F/# の解は ValueError", False)
    except ValueError as e:
        print("   届かない F/# = 1.0 → ValueError: " + str(e)[:150])
        gate("届かない F/# の解は、探した範囲の F/# の幅を添えて ValueError", "found no curvature" in str(e) and "F/#" in str(e))
    return tab, s2


# --------------------------------------------------------------------------- #
def telescope(gap, afocal=False, Ro=RO, Re=RE, ap=10.0, ap_e=6.0, field=1.0):
    """物体側 f ≈ 100 mm、接眼 f ≈ 25 mm の 2 つの色消し 2 枚(接眼は反転して使う)。"""
    return RT.lens_system([
        {"R": Ro[0], "t": 4.0, "n": CROWN, "ap": ap}, {"R": Ro[1], "t": 2.0, "n": FLINT}, {"R": Ro[2], "t": gap, "n": 1.0},
        {"R": -Re[2], "t": 1.5, "n": FLINT, "ap": ap_e}, {"R": -Re[1], "t": 3.0, "n": CROWN},
        {"R": -Re[0], "t": 8.0, "n": 1.0, "ap": ap_e}], stop=0, afocal=afocal, field=field, aim="stop")


def afocal_gap():
    """平行光が平行光で出る間隔(出射の傾きの根を二分法で)。"""
    def slope(g):
        return RT.paraxial_trace(telescope(g))["marginal"]["u"][-1]
    lo, hi = 100.0, 140.0
    for _ in range(90):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if slope(lo) * slope(mid) > 0 else (lo, mid)
    return 0.5 * (lo + hi)


def chapter_afocal():
    print("\n3. afocal: 角倍率と角度の収差(分角)")
    fields = [0.0, 0.5, 1.0, 2.0]
    out = {}
    for name, f1, f2, M in (("ケプラー", 100.0, 25.0, -4.0), ("ガリレオ", 100.0, -25.0, 4.0)):
        tele = LS.afocal_system(f1=f1, f2=f2)
        pt = RT.paraxial_trace(tele)
        r = LS.lens_afocal_report(tele, fields=fields)
        rms = [f["rms_arcmin"] for f in r["fields"]]
        tanr = [math.tan(math.radians(f["chief_arcmin"][1] / 60.0)) / math.tan(math.radians(f["field"])) for f in r["fields"][1:]]
        print("   %s f1=%g f2=%g: 角倍率 %.15f(閉形式 %+g)、EFL = %s、角度の RMS [arcmin] %s、tan θ'/tan θ の誤差 %.1e" % (
            name, f1, f2, pt["angular_magnification"], M, pt["efl"], ["%.1e" % x for x in rms], max(abs(t / M - 1.0) for t in tanr)))
        gate("%s望遠鏡の角倍率は %+g に 1e-12 以内。EFL = inf でも例外にならない" % (name, M),
             abs(pt["angular_magnification"] - M) < 1e-12 and pt["efl"] == INF)
        gate("%s望遠鏡の角度の収差は 0(全視野で RMS 1e-9 分角以下、tan θ'/tan θ = M が 1e-12 以内)" % name,
             max(rms) < 1e-9 and max(abs(t / M - 1.0) for t in tanr) < 1e-12)
        out[name] = r
    gap = afocal_gap()
    real = telescope(gap, afocal=True)
    pt = RT.paraxial_trace(real)
    r = LS.lens_afocal_report(real, fields=[0.0, 0.25, 0.5, 0.75, 1.0])
    print("   実ガラスの 2 つの色消し 2 枚: 間隔 %.5f mm(出射の傾きの根)、角倍率 %.6f、射出瞳 %.2f mm(半径 %.3f mm)、倍率 %.3f 倍に絞る" % (
        gap, pt["angular_magnification"], pt["xp_position"], pt["xp_radius"], r["beam_compression"]))
    for f in r["fields"]:
        print("     視野 %.2f°: 主光線の射出角 %+.2f 分角、角度のスポット RMS %.3f 分角(最大 %.3f)、波面 RMS %.3f 波長" % (
            f["field"], f["chief_arcmin"][1], f["rms_arcmin"], f["geo_arcmin"], f["wavefront_rms_waves"]))
    rms = [f["rms_arcmin"] for f in r["fields"]]
    gate("実望遠鏡の軸上の角度のスポットは 1 分角未満で、波面は回折限界(RMS < 0.0714 波長)",
         rms[0] < 1.0 and r["fields"][0]["wavefront_rms_waves"] < 0.0714,
         "%.3f 分角、%.3f 波長" % (rms[0], r["fields"][0]["wavefront_rms_waves"]))
    gate("角度のスポットは視野とともに単調に増える(軸外の収差)", all(b > a for a, b in zip(rms, rms[1:])),
         "0° %.2f → 1° %.2f 分角" % (rms[0], rms[-1]))
    ch = RT.chief_ray(real, field=1.0)
    ang = math.atan2(ch["dirs"][-1][1], abs(ch["dirs"][-1][2]))
    dist = (math.tan(ang) / math.tan(math.radians(1.0)) / pt["angular_magnification"] - 1.0) * 100.0
    print("   角倍率の歪み(1°): tan θ'/tan θ は近軸の角倍率より %+.2f %%" % dist)
    NUMBERS.update({"tele_rms_axis": rms[0], "tele_rms_1deg": rms[-1], "tele_M": pt["angular_magnification"],
                    "tele_distortion_pct": dist})
    # afocal の印は .zmx を往復する
    w = LF.lens_file_write(LF._prescription_from_system(real), system=real)["text"]
    back = LF.lens_file_read(w)["system"]
    ok = back.get("afocal") is True and abs(RT.paraxial_trace(back)["angular_magnification"] - pt["angular_magnification"]) < 1e-12
    gate("afocal の印は .zmx を往復する(NOTE 行、形式に afocal の行の例が無いので作らない)。読み戻しの角倍率が 1e-12 以内", ok)
    try:
        RT.paraxial_trace(RT.lens_system([{"R": 50.0, "t": 30.0, "n": 1.5, "ap": 5.0}, {"R": INF, "t": 10.0, "n": 1.0}], stop=0,
                                         afocal=True))
        gate("集光する系に afocal の印を付けると ValueError", False)
    except ValueError as e:
        gate("集光する系に afocal の印を付けると ValueError(平行光が平行光で出ない)", "flagged afocal" in str(e))
    return out, r, real


# --------------------------------------------------------------------------- #
def landscape_lens(ap=0.5):
    """正のメニスカス(物体側が凹、f = 99.8 mm)の前に絞り。絞りの位置は Seidel の非点収差 S_III = 0 の根(二分法)。"""
    R1, R2, t = -100.0, -34.071729957805914, 0.3

    def build(d, a):
        return RT.lens_system([{"R": INF, "t": d, "n": 1.0, "ap": a}, {"R": R1, "t": t, "n": CROWN, "ap": 14.0},
                               {"R": R2, "t": None, "n": 1.0, "ap": 14.0}], stop=0, field=10.0)

    def f(d):
        return RT.seidel_coefficients(build(d, 1.0), field=10.0)["total"]["S_III"]
    lo, hi = 10.0, 20.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if f(lo) * f(mid) > 0 else (lo, mid)
    return build(0.5 * (lo + hi), ap), 0.5 * (lo + hi)


def chapter_image_surface():
    print("\n4. 曲面の像面: ペッツバール湾曲を像面の曲率で消す")
    lens, d0 = landscape_lens()
    sd = RT.seidel_coefficients(lens, field=10.0)
    rp = LS.lens_petzval_radius(lens)["radius"]
    print("   薄いメニスカス(物体側が凹)の前 %.4f mm に絞り: S_III = %.1e(0)、S_IV = %.3e、ペッツバール半径 %.4f mm(Seidel 側の値 %.4f)" % (
        d0, sd["total"]["S_III"], sd["total"]["S_IV"], rp, sd["petzval_radius"]))
    thin = RT.lens_system([{"R": 100.0, "t": 0.0, "n": 1.5, "ap": 2.0}, {"R": -100.0, "t": None, "n": 1.0}], stop=0)
    gate("ペッツバール半径は薄肉レンズの閉形式 −N f と 1e-12、Seidel 和の値と 1e-12 で一致",
         abs(LS.lens_petzval_radius(thin)["radius"] / (-1.5 * 100.0) - 1.0) < 1e-12 and abs(rp / sd["petzval_radius"] - 1.0) < 1e-12)
    curved = LS.lens_image_surface(lens, R="petzval")
    a, b = RT.paraxial_trace(lens), RT.paraxial_trace(curved)
    dpar = max(abs(a[k] - b[k]) for k in ("efl", "bfl", "image_mm", "ep_radius", "xp_position", "lagrange"))
    gate("近軸の像（位置・高さ・瞳）は像面の曲率に依らない(差 1e-9 以内)", dpar < 1e-9, "%.1e" % dpar)
    bfl = a["bfl"]
    flds = [0.0, 5.0, 7.0, 10.0]
    print("   視野 [°] | 平らな像面 RMS [µm] | ペッツバールの像面 RMS [µm] | 平面の最良の像面 RMS [µm]")
    rows = {}
    for f in flds:
        fl = RT.spot_stats(lens, field=f, rings=RINGS + 2)["rms_radius"]
        cu = RT.spot_stats(curved, field=f, rings=RINGS + 2)["rms_radius"]
        fl_best = min(RT.spot_stats(lens, field=f, rings=RINGS + 2, image_mm=bfl + d)["rms_radius"]
                      for d in np.linspace(-4.0, 1.0, 51 if REDUCED else 101)) if f > 0 else fl
        rows[f] = (fl, cu, fl_best)
        print("   %5.1f | %8.3f | %8.3f | %8.3f" % (f, fl * 1e3, cu * 1e3, fl_best * 1e3))
    f7 = rows[7.0]
    term_flat = math.sqrt(max(f7[0] ** 2 - f7[2] ** 2, 0.0))
    term_cur = math.sqrt(max(f7[1] ** 2 - f7[2] ** 2, 0.0))
    print("   0.7 視野の像面湾曲の項(RMS² − 最良の像面の RMS²)の平方根: 平らな像面 %.3f µm → ペッツバール %.3f µm(1/%.0f)、RMS %.3f → %.3f µm" % (
        term_flat * 1e3, term_cur * 1e3, term_flat / max(term_cur, 1e-12), f7[0] * 1e3, f7[1] * 1e3))
    gate("0.7 視野の RMS は、ペッツバールの像面で平らな像面の 1/5 未満(最良の像面の床の 1.2 倍以内)",
         f7[1] < 0.2 * f7[0] and f7[1] < 1.2 * f7[2], "%.3f → %.3f µm(床 %.3f)" % (f7[0] * 1e3, f7[1] * 1e3, f7[2] * 1e3))
    gate("像面湾曲の項は 1/10 未満に減る", term_cur < 0.1 * term_flat)
    gate("軸上は像面の曲率に依らない(相対 1e-3)", abs(rows[0.0][1] / rows[0.0][0] - 1.0) < 1e-3)
    NUMBERS.update({"petzval_radius": rp, "rms7_flat_um": f7[0] * 1e3, "rms7_curved_um": f7[1] * 1e3, "rms7_floor_um": f7[2] * 1e3,
                    "fc_term_flat_um": term_flat * 1e3, "fc_term_curved_um": term_cur * 1e3})
    # 光線は像面の式に載る
    cur2 = LS.lens_image_surface(landscape_lens(ap=2.0)[0], R=-120.0, k=-0.5)
    bd = RT.ray_bundle(cur2, field=8.0, rings=4)
    pts = bd["points"][bd["valid"]][:, -1, :]
    r2 = pts[:, 0] ** 2 + pts[:, 1] ** 2
    c = 1.0 / -120.0
    sag = c * r2 / (1.0 + np.sqrt(1.0 - 0.5 * c * c * r2))
    dev = float(np.max(np.abs(pts[:, 2] - bd["z_image_global"] - sag)))
    gate("光線の像面上の点は像面の式 z = c r²/(1 + √(1 − (1+k) c² r²)) に 1e-11 以内で載る", dev < 1e-11, "%.1e" % dev)
    return lens, curved, rows


# --------------------------------------------------------------------------- #
def plate_system(a2=0.0, A4=0.0, B1=0.0, B3=0.0, ap=6.0):
    back = {"R": INF, "t": 5.0, "n": 1.0, "ap": ap}
    if a2:
        back["a2"] = a2
    if A4:
        back["asph"] = (A4,)
    if B1 or B3:
        back["odd"] = (B1, 0.0, B3)
    return RT.lens_system([{"R": INF, "t": 2.0, "n": CROWN, "ap": ap}, back, {"R": 51.68, "t": 5.0, "n": CROWN, "ap": ap + 1},
                           {"R": INF, "t": 90.0, "n": 1.0, "solve": {"kind": "paraxial_image"}}], stop=0)


def best_over(name, lo, hi, other=None, n_scan=41):
    other = other or {}

    def f(x):
        return RT.spot_stats(plate_system(**dict(other, **{name: x})), field=0.0, rings=8)["rms_radius"]
    xs = np.linspace(lo, hi, n_scan)
    vals = [f(x) for x in xs]
    k = int(np.argmin(vals))
    a, b = xs[max(k - 1, 0)], xs[min(k + 1, len(xs) - 1)]
    g = (math.sqrt(5.0) - 1.0) / 2.0
    c, d = b - g * (b - a), a + g * (b - a)
    fc, fd = f(c), f(d)
    for _ in range(30):
        if fc < fd:
            b, d, fd = d, c, fc
            c = b - g * (b - a)
            fc = f(c)
        else:
            a, c, fc = c, d, fd
            d = a + g * (b - a)
            fd = f(d)
    x = 0.5 * (a + b)
    return x, f(x)


def conic_sag(r, c, k):
    return c * r * r / (1.0 + np.sqrt(1.0 - (1.0 + k) * c * c * r * r))


def chapter_asphere():
    print("\n5. 奇数次の非球面と r² の項")
    c, k = 1.0 / 40.0, -0.3
    a2, odd, asph = 2e-4, (1e-4, -3e-5, 2e-6, 0.0, -1e-9), (4e-7, -2e-10)
    h = np.linspace(0.5, 9.5, 10)
    want = conic_sag(h, c, k) + a2 * h ** 2 + sum(b * h ** (i + 1) for i, b in enumerate(odd)) \
        + sum(a * h ** (2 * i + 4) for i, a in enumerate(asph))
    err = float(np.max(np.abs(RT._sag(h * h, c, k, asph, (a2, odd)) - want)))
    gate("奇数次の非球面のサグは、円錐 + a2 r² + Σ B_i r^i + Σ A r^(2i) の手書きの式と 10 点で 1e-12 以内", err < 1e-12, "%.1e" % err)
    rng = np.random.default_rng(5)
    P = np.column_stack([rng.uniform(-6, 6, 40), rng.uniform(-6, 6, 40), np.full(40, -3.0)])
    D = np.column_stack([rng.uniform(-0.1, 0.1, 40), rng.uniform(-0.1, 0.1, 40), np.ones(40)])
    D /= np.linalg.norm(D, axis=1, keepdims=True)
    t = RT._intersect_surface(P, D, c, k, (), (a2, odd[:3]))
    Q = P + t[:, None] * D
    r = np.hypot(Q[:, 0], Q[:, 1])
    res = float(np.max(np.abs(Q[:, 2] - (conic_sag(r, c, k) + a2 * r ** 2 + sum(b * r ** (i + 1) for i, b in enumerate(odd[:3]))))))
    gate("光線の交点は面の式を 1e-10 以内で満たす(40 本)", res < 1e-10, "%.1e" % res)
    base = [{"R": 40.0, "t": 4.0, "n": 1.5, "ap": 8.0, "k": -0.3, "asph": (1e-7, -2e-10)}, {"R": -90.0, "t": None, "n": 1.0}]
    za, zb = RT.lens_system(base, stop=0), RT.lens_system([dict(base[0], odd=(0.0, 0.0), a2=0.0), base[1]], stop=0)
    ta, tb = RT.ray_bundle(za, field=3.0, rings=6), RT.ray_bundle(zb, field=3.0, rings=6)
    same = np.array_equal(ta["points"], tb["points"], equal_nan=True) and np.array_equal(ta["opl"], tb["opl"], equal_nan=True)
    gate("B_i = 0 の奇数次は偶数次の非球面と光線の座標・光路まで一字一句同じ", same)
    # 円錐(r¹)= 軸子レンズ: 軸との交点の位置が閉形式
    n = 1.5
    B1 = -math.tan(math.radians(5.0))
    T = 3.0
    ax = RT.lens_system([{"R": INF, "t": T, "n": n, "ap": 6.0}, {"R": INF, "t": None, "n": 1.0, "ap": 6.0, "odd": (B1,)}],
                        stop=0, image_mm=100.0)
    rr = np.array([0.5, 1.0, 2.0, 3.5, 5.0])
    trc = RT.trace_rays(ax, np.column_stack([np.zeros(5), rr, np.full(5, -1.0)]), np.tile([0.0, 0.0, 1.0], (5, 1)))
    alpha = math.atan(abs(B1))
    beta = math.asin(n * math.sin(alpha)) - alpha
    zc = []
    for q in range(5):
        Pq, dq = trc["points"][q, -2], trc["dirs"][q, -1]
        zc.append(Pq[2] - Pq[1] / dq[1] * dq[2])
    zc = np.array(zc)
    want_z = T + B1 * rr + rr / math.tan(beta)
    err = float(np.max(np.abs(zc - want_z)))
    print("   軸子レンズ(B1 = −tan 5°、n = 1.5): 半径 %s mm の光線が軸を横切る位置 %s mm(閉形式 r/tan β + T + B1 r で差 %.1e)" % (
        [float(x) for x in rr], ["%.3f" % z for z in zc], err))
    gate("円錐面(B1 r)の板は光線を軸の 1 点でなく線に集め、軸との交点は Snell の閉形式と 1e-9 以内", err < 1e-9 and np.ptp(zc) > 50.0,
         "%.1e、線の長さ %.1f mm" % (err, float(np.ptp(zc))))
    NUMBERS["axicon_err"] = err
    # 補正板
    base_rms = RT.spot_stats(plate_system(), field=0.0, rings=8)["rms_radius"]
    n_scan = 21 if REDUCED else 41
    xa, fa = best_over("A4", -4e-6, 4e-6, n_scan=n_scan)
    xb, fb = best_over("B3", -4e-5, 4e-5, n_scan=n_scan)
    xc, fc = best_over("B1", -2e-3, 2e-3, n_scan=n_scan)
    xd, fd = best_over("a2", -1e-3, 1e-3, n_scan=n_scan)
    print("   平凸レンズ(f = 100 mm、F/8)の前の補正板(ガラス面が平らな板の後ろ面に 1 項だけ足す)、軸上の RMS スポット [µm]:")
    print("     板なし %.3f | a2 r²(最良 %.2e)%.3f | B1 r(最良 %.2e)%.3f | B3 r³(最良 %.2e)%.3f | A4 r⁴(最良 %.2e)%.4f" % (
        base_rms * 1e3, xd, fd * 1e3, xc, fc * 1e3, xb, fb * 1e3, xa, fa * 1e3))
    gate("球面収差の補正板は r⁴(偶数次)が最も効き、r³(奇数次)がそれに次ぎ、r² と r¹ は少ししか効かない: A4 < B3 < B1 < a2 < 板なし",
         fa < fb < fc < fd < base_rms, "1/%.0f、1/%.1f、1/%.2f、1/%.2f" % (base_rms / fa, base_rms / fb, base_rms / fc, base_rms / fd))
    gate("r⁴ の補正板は軸上のスポットを 1/100 以下にする", fa < 0.01 * base_rms)
    # a2 は曲率の変化と同じ近軸の屈折力
    a2v = 3e-4
    pa = RT.paraxial_trace(RT.lens_system([{"R": 40.0, "t": 4.0, "n": 1.5, "ap": 6.0, "a2": a2v}, {"R": INF, "t": 50.0, "n": 1.0}], stop=0))
    pc = RT.paraxial_trace(RT.lens_system([{"R": 1.0 / (1.0 / 40.0 + 2.0 * a2v), "t": 4.0, "n": 1.5, "ap": 6.0},
                                           {"R": INF, "t": 50.0, "n": 1.0}], stop=0))
    gate("r² の項 a2 は曲率の変化 2·a2 と同じ近軸の屈折力(EFL が 1e-13 相対で同じ)", abs(pa["efl"] / pc["efl"] - 1.0) < 1e-13)
    NUMBERS.update({"plate_base_um": base_rms * 1e3, "plate_A4_um": fa * 1e3, "plate_B3_um": fb * 1e3, "plate_B1_um": fc * 1e3,
                    "plate_a2_um": fd * 1e3})
    print("   ★限界: 奇数次(特に r¹ の円錐)は頂点で滑らかでなく(傾きが跳ぶ)、近軸の屈折力は r¹ に無い(paraxial は r¹ を無視)。"
          "seidel_coefficients・raytrace3d・PSF/MTF は a2 / odd を持つ系を拒否する。")
    return {"zc": zc, "rr": rr, "want": want_z, "bars": [base_rms, fd, fc, fb, fa]}


# --------------------------------------------------------------------------- #
def chapter_zmx():
    print("\n6. .zmx と壊して確かめる")
    s = RT.lens_system([
        {"R": 62.0, "t": 4.0, "n": CROWN, "ap": 9.0, "asph": (1e-7, -2e-11), "a2": 2e-4},
        {"R": -45.0, "t": 2.0, "n": FLINT},
        {"R": -130.0, "t": 6.0, "n": 1.0, "solve": {"kind": "marginal_ray_angle", "angle_deg": -3.0}},
        {"R": 99.0, "t": 3.0, "n": CROWN, "asph": (0.0,), "solve": {"kind": "pickup", "source": 0, "quantity": "A4", "scale": -1.0}},
        {"R": 99.0, "t": 9.0, "n": 1.0, "solve": {"kind": "pickup", "source": 2, "quantity": "c", "scale": -1.0}},
        {"R": 70.0, "t": 5.0, "n": FLINT, "solve": {"kind": "pickup", "source": 3, "quantity": "t", "scale": 2.0, "offset": 0.25}},
        {"R": -80.0, "t": 1.0, "n": 1.0, "solve": {"kind": "f_number", "fno": 7.5, "c0": -0.0125}},
        {"R": INF, "t": 1.0, "n": 1.0, "solve": {"kind": "paraxial_image"}}], stop=0)
    rt = LS.lens_zmx_solves_roundtrip(s)
    kinds = [x["rule"]["kind"] for x in LS.lens_solves_list(s)["solves"]]
    print("   規則 %d 本(%s)。.zmx の行にできるもの(面 %s)は CURV c 4 source scale offset / PZUP / PPAR、それ以外(面 %s)は NOTE 行。" % (
        len(kinds), "、".join(kinds), [i + 1 for i in rt["native"]], [i + 1 for i in rt["as_note"]]))
    for ln in rt["text"].splitlines():
        if ln.startswith(("NOTE", "  PZUP", "  PPAR")) or ("CURV" in ln and " 4 " in ln):
            print("     " + ln[:110])
    gate("3 種のピックアップ(曲率 −c・厚み・非球面係数)と 3 種の規則が .zmx を往復し、書く→読む→書くが不動点(差 1e-12 以内)",
         rt["fixed_point"] and rt["rules_equal"] and rt["max_diff"] < 1e-12, "最大差 %.1e" % rt["max_diff"])
    gate("凍結して捨てる解(dropped_solves)は空", rt["dropped_solves"] == [])
    NUMBERS["zmx_roundtrip_diff"] = rt["max_diff"]
    cases = [
        ("未知の種類", lambda: LS.lens_solve_set(None, 0, "cleverness")),
        ("その種類が取らない引数", lambda: LS.lens_solve_set(None, 0, "paraxial_image", h=1.0)),
        ("循環したピックアップ", lambda: RT.lens_system(
            [{"R": 50.0, "t": 4.0, "n": 1.5, "ap": 6.0, "solve": {"kind": "pickup", "source": 1}},
             {"R": -30.0, "t": 3.0, "n": 1.0, "solve": {"kind": "pickup", "source": 0}},
             {"R": INF, "t": 10.0, "n": 1.0}], stop=0)),
        ("絞りを動かす厚みの解", lambda: LS.lens_solve_set(RT.lens_system(
            [{"R": 50.0, "t": 4.0, "n": 1.5, "ap": 5.0}, {"R": INF, "t": 5.0, "n": 1.0, "ap": 5.0},
             {"R": INF, "t": 10.0, "n": 1.0}], stop=1), 0, "marginal_ray_height", h=1.0)),
        ("軸上の主光線の解", lambda: LS.lens_solve_set(RT.lens_system(
            [{"R": 50.0, "t": 4.0, "n": 1.5, "ap": 5.0}, {"R": INF, "t": 10.0, "n": 1.0}], stop=0), 1, "chief_ray_height", h=1.0)),
        ("理想レンズの曲率の解", lambda: LS.lens_solve_set(RT.lens_system(
            [{"f": 50.0, "t": 10.0, "ap": 5.0}, {"f": 50.0, "t": 10.0}], stop=0), 0, "marginal_ray_angle")),
        ("集光する系の afocal", lambda: RT.paraxial_trace(RT.lens_system(
            [{"R": 50.0, "t": 30.0, "n": 1.5, "ap": 5.0}, {"R": INF, "t": 10.0, "n": 1.0}], stop=0, afocal=True))),
        ("理想レンズを .zmx に書く", lambda: LF.lens_file_write(LF._prescription_from_system(LS.afocal_system()),
                                                         system=LS.afocal_system())),
        ("a2 / odd を持つ系の Seidel 和", lambda: RT.seidel_coefficients(RT.lens_system(
            [{"R": 40.0, "t": 4.0, "n": 1.5, "ap": 6.0, "a2": 1e-4}, {"R": INF, "t": 50.0, "n": 1.0}], stop=0))),
    ]
    ok = 0
    for name, fn in cases:
        try:
            fn()
        except ValueError as e:
            ok += 1
            print("   %s → ValueError: %s" % (name, str(e)[:100]))
    gate("壊した入力 %d 通りがすべて ValueError" % len(cases), ok == len(cases))


# --------------------------------------------------------------------------- #
def _fit(img, w, h):
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


def _spot(d, title, lim):
    d = d * 1e3
    return figs.render_plot([("", d[:, 0], d[:, 1])], title=title, size=(300, 270), kinds=["scatter"], colors=["emphasis"],
                            xlim=(-lim, lim), ylim=(-lim, lim), aspect="equal", xlabel="x [µm]", ylabel="y [µm]")


def make_figure(tab, s2, tele_out, real, lens, curved, rows, asph):
    # 1 段目: F/# の解の根(曲線)と、絞りを動かしたときの解
    stop = s2["stop"]
    cs = np.linspace(-0.07, 0.03, 400)
    fn = []
    for cj in cs:
        surf = [{k: v for k, v in x.items() if k != "solve"} for x in s2["surfaces"]]
        surf[9]["R"] = INF if abs(cj) < 1e-12 else 1.0 / cj
        try:
            f = RT.paraxial_trace(rebuild(s2, surf))["fno"]
        except ValueError:
            f = np.nan
        fn.append(f if np.isfinite(f) and 0.0 < f < 14.0 else np.nan)
    row0 = LS.lens_solves_list(s2)["solves"][0]
    fn = np.array(fn)
    ok = np.isfinite(fn)
    p1 = figs.render_plot([("F/#(c9)", cs[ok], fn[ok]), ("目標 5", cs, np.full_like(cs, 5.0)),
                           ("根", np.array(row0["roots"]), np.array([5.0, 5.0]))], title="F/# の解: 根は 2 本(近い方を採る)",
                          size=(440, 330), kinds=["scatter", "line", "scatter"], styles=[None, "dashed", None],
                          colors=["emphasis", "reference", "wrong"], xlabel="c9 [1/mm]", ylabel="F/#", ylim=(0.0, 14.0))
    aps = [t["ap"] for t in tab]
    p2 = figs.render_plot([("解いた版 F/#", aps, [t["fno"] for t in tab]), ("固めた版 F/#", aps, [t["fno_frozen"] for t in tab])],
                          title="絞りを動かしたときの F/#", size=(440, 330), colors=["right", "wrong"], xlabel="絞りの半径 [mm]",
                          ylabel="F/#", ylim=(3.5, 6.6))
    p3 = figs.render_plot([("EFL", aps, [t["efl"] for t in tab]), ("像距離 t10", aps, [t["t10"] for t in tab])],
                          title="解いた値: EFL と像距離", size=(440, 330), colors=["emphasis", "reference"], xlabel="絞りの半径 [mm]",
                          ylabel="[mm]")
    # 2 段目: 望遠鏡
    flds = np.linspace(0.0, 1.5, 7)
    rep = LS.lens_afocal_report(real, fields=list(flds))
    p4 = figs.render_plot([("実ガラス 2 つの色消し 2 枚", flds, [f["rms_arcmin"] for f in rep["fields"]]),
                           ("(理想レンズ: 0)", flds, np.zeros(len(flds)))], title="角度のスポット RMS [分角]",
                          size=(440, 330), styles=[None, "dashed"], colors=["wrong", "reference"], xlabel="視野 [°]", ylabel="分角")
    ch = [(math.tan(math.radians(f["chief_arcmin"][1] / 60.0)) / math.tan(math.radians(f["field"])) / rep["angular_magnification"]
           - 1.0) * 100.0 for f in rep["fields"][1:]]
    p5 = figs.render_plot([("実望遠鏡", flds[1:], ch)], title="角倍率の歪み [%]（近軸の角倍率に対して）", size=(440, 330),
                          colors=["wrong"], xlabel="視野 [°]", ylabel="%")
    b0 = RT.ray_bundle(real, field=1.0, rings=6)
    d = (b0["image_xy"] - b0["chief_xy"])[b0["valid"]]
    lim = float(np.abs(d).max()) * 1.1
    p6 = figs.render_plot([("", d[:, 0], d[:, 1])], title="1° の射出角の散らばり", size=(330, 330), kinds=["scatter"],
                          colors=["emphasis"], xlim=(-lim, lim), ylim=(-lim, lim), aspect="equal", xlabel="x [分角]", ylabel="y [分角]")
    # 3 段目: 平らな像面と曲面の像面のスポット
    sp = []
    for sysd, nm in ((lens, "平ら"), (curved, "ペッツバール")):
        pan = []
        for f in (0.0, 5.0, 7.0, 10.0):
            b = RT.ray_bundle(sysd, field=f, rings=6)
            d = (b["image_xy"] - b["chief_xy"])[b["valid"]]
            pan.append((f, d))
        sp.append((nm, pan))
    lim = 1.1 * max(float(np.abs(d).max()) for _, pan in sp for _, d in pan) * 1e3
    r3a = _row([_spot(d, "%s %g°: RMS %.2f µm" % (nm, f, 1e3 * np.sqrt(np.mean(np.sum(d * d, 1)))), lim) for f, d in sp[0][1]
                for nm in [sp[0][0]]])
    r3b = _row([_spot(d, "%s %g°: RMS %.2f µm" % (nm, f, 1e3 * np.sqrt(np.mean(np.sum(d * d, 1)))), lim) for f, d in sp[1][1]
                for nm in [sp[1][0]]])
    # 4 段目: 軸子レンズと補正板
    rr = np.linspace(0.2, 5.5, 12)
    B1 = -math.tan(math.radians(5.0))
    alpha = math.atan(abs(B1))
    beta = math.asin(1.5 * math.sin(alpha)) - alpha
    p7 = figs.render_plot([("閉形式", rr, 3.0 + B1 * rr + rr / math.tan(beta)), ("追跡", asph["rr"], asph["zc"])],
                          title="円錐面の板: 光線が軸を横切る位置", size=(440, 330), kinds=["line", "scatter"], colors=["reference", "emphasis"],
                          styles=["dashed", None], xlabel="光線の高さ [mm]", ylabel="z [mm]")
    bars = asph["bars"]
    lab = ["板なし", "a2", "B1", "B3", "A4"]
    import fullseye as fs
    wb, hb = 440, 330
    p8 = figs.render_plot([("RMS / 板なし", np.arange(1, 6, dtype=float), np.array(bars) / bars[0])], title="補正板の項ごとの軸上スポット(板なし = 1)",
                          size=(wb, hb), kinds=["bar"], colors=["emphasis"], xlim=(0.5, 5.5), xlabel="", ylabel="RMS 比")
    x0, y0, rw, rh = 72, 44, wb - 96, hb - 108
    for i, nm in enumerate(lab):
        p8 = np.asarray(fs.text_box(p8, nm, (x0 + (i + 0.5) / 5 * rw, y0 + rh + 22), anchor="ct", font_size=9))
    img = _stack([_row([p1, p2, p3]), _row([p4, p5, p6]), r3a, r3b, _row([p7, p8])])
    figs.save("lens_solves_afocal", img,
              caption="1 段目: 左 二重ガウス型の最終素子の前面の曲率で F/# = 5 を解く(F/#(c) の曲線と 2 つの根、採るのは近い方)、"
                      "中 絞りの半径を動かしたときの F/#(解いた版は 5 のまま、数字を固めた版は流れる)、右 解いた EFL と像距離。"
                      "2 段目: 実ガラスの 2 つの色消し 2 枚の afocal 望遠鏡の角度のスポット RMS(分角)と角倍率の歪み、1° の射出角の散らばり。"
                      "3・4 段目: 非点収差を 0 にした薄いメニスカスの 0 / 5 / 7 / 10° のスポット、平らな像面(3 段目)とペッツバール半径の像面(4 段目)。"
                      "最下段: 左 円錐面(r¹)の板の光線が軸を横切る位置と閉形式、右 球面収差の補正板に足す項ごとの軸上スポット(板なし = 1)。")
    frames = []
    for field in np.linspace(0.0, 10.0, 32):
        b = RT.ray_bundle(curved, field=float(field), rings=6)
        d = (b["image_xy"] - b["chief_xy"])[b["valid"]]
        frames.append(figs.video_frame(_spot(d, "", 80.0), "視野角 %.1f°" % field))
    assert len(frames) >= 24
    assert np.ptp(np.stack(frames).astype(np.int16), axis=0).max() > 0
    figs.save_video("solved_surface_field_sweep", frames,
                    caption="解いた曲面像面で視野角を掃引したスポット。", fps=10.0,
                    gif_every=2, gif_fps=5.0, gif_width=480)


def main():
    t0 = time.time()
    c0 = time.process_time()
    print("PoC 解・afocal・曲面の像面・奇数次の非球面(予算 %s)" % ("reduced" if REDUCED else "full"))
    chapter_closed_forms()
    tab, s2 = chapter_double_gauss()
    tele_out, real_rep, real = chapter_afocal()
    lens, curved, rows = chapter_image_surface()
    asph = chapter_asphere()
    chapter_zmx()
    if not REDUCED and figs.target_dir() is not None:
        make_figure(tab, s2, tele_out, real, lens, curved, rows, asph)
    cpu = time.process_time() - c0
    print("\n所要 CPU %.1f s(壁時計 %.1f s)、門 %d 件中 NG %d 件" % (cpu, time.time() - t0, len(GATES), len(FAILS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
