# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 非共軸の光学系 —— 同軸落射の半透鏡が鏡面の部品に偽の欠陥を写し、膜と傾きで消す。折り返しで装置を小さくする。

【問い】外観検査の光学系は、光軸が 1 本の直線とは限らない。鏡面の部品を真上から照らす同軸落射は 45° の半透鏡を
通して見るし、装置を小さくするには折り返しミラーで光路を曲げ、傾いた面を全面で合焦させるにはシャインプルーフ
配置で撮像素子を傾ける。Fullseye の光線追跡 ``raytrace`` は共軸の系しか組めず、半透鏡の裏面が作るゴースト
(2 回反射でできる像)も計算できなかった。新 op 13 本(``raytrace3d``、``opsoptics`` の ``noncoaxial``)と
``optdraw.noncoaxial_drawing`` で組み、外の真値で採点する。収蔵番号 2026.248。7 章:

  1. **共軸の一致**: ``raytrace`` の処方 8 本(単レンズ・2 枚玉・硝材つき 2 枚玉・非球面・放物面鏡・球面鏡・偏心と
     傾きのある副鏡のカセグレン・傾いた単レンズ)を ``noncoaxial_system`` に変換し、同じ光線の交点・光路長が
     ``raytrace.trace_rays`` と 1e-12 で一致(門)。
  2. **折り返しミラー**: 45° の鏡で光路を 90° 曲げた像は、展開した系の像の Householder 鏡映 p − 2((p − p₀)·n)n と
     1e-9 mm で一致(x・y・斜めの 4 通りの傾き)。反射 1 回で像は裏返り(行列式が負)、潜望鏡(2 回)では裏返らない。
     同軸落射の検査レンズのカメラ側の 204 mm を 2 枚の鏡で折り返すと、装置の高さが 393 → 249 mm に縮み、像の RMS は
     1e-12 で変わらない。
  3. **傾いた平板と半透鏡の 2 本の枝**: 30° に傾けた 5 mm の平板の横ずれ t·sinθ(1 − cosθ/√(n² − sin²θ))(Smith)と
     非点隔差(Coddington の式から導出、接線像が遠い)が、実光線と 1e-6 mm で一致(0〜60°。焦点はほぼ平行な 2 本の交点なので丸めの床が環境により 1e-9〜1e-7 mm)。45° の半透鏡の
     反射の枝の像は展開した焦点の鏡映、透過の枝は閉形式の横ずれ。
  4. **シャインプルーフ**: 30° に傾いた物面を 2 枚玉で撮ると、撮像素子を tanθ' = m·tanθ だけ傾けたときに全面の
     ぼけが最小になる。実光線で求めた像面の傾きが閉形式と 1e-3° 以内、ヒンジ(物面と前側主面・像面と後側主面が
     同じ高さで交わる)は閉形式どおり。
  5. **偽の欠陥**: 同軸落射の検査で、半透鏡(3 mm、前面 R = 50 %)の裏面と前面の 2 回反射のゴーストが、鏡面の部品の
     凹み(直径 2 mm)の**ずれた写し**を像面に作る。ゴーストのエネルギー比は R_前(0.5)× R_裏(入射角 28° の
     Fresnel、無偏光)= 2.6 % で閉形式と 1e-6 で一致、ずれは倍率 × 2t·tanθ'·cosθ と 5 % 以内。単純な欠陥の検出
     (背景との差が 1.5 % を超える塊)で、本物の凹みと傷に加えて、ゴーストの「偽の凹み」が予測した位置に出る(3 個)。
     ★裏面に MgF₂ の λ/4 単層を付けても、45° の板では反射率が 2.1 % にしか下がらない(垂直入射なら 1.25 %)。
     入射角に合わせた 2 層の膜(Ta₂O₅ 20 nm + MgF₂ 157.5 nm、0.39 %)でゴーストは 0.19 % に落ちて偽の凹みが消え、
     裏面を 1° 傾けた楔の板にするとゴーストは 9.5 mm ずれて撮像素子の外へ出る。
  6. **第 2 実装**: OSS の光線追跡 optiland(MIT)で同じ姿勢の面を絶対座標で組み、同じ光線の各面の交点が 1e-12 mm で
     一致(6 系: 折り返し・潜望鏡・傾いた平板・軸外し放物面・x と y の複合傾き + 偏心した傾いたレンズ・同軸落射)。
     手元に optiland が無いとき(CI)は 2026-10-15 の記録値と 1e-7 mm で照合する(記録は 1e-10 に丸め、起点を絞りへ狙う
     反復の床が環境で変わるので、生の照合の 1e-10 より緩い)。軸外し放物面は optiland の公開例と同じ配置で、
     全光線が親の焦点 (0, 0, −50) に 1e-8 mm で集まる。
  7. **壊して確かめる**: 反射の後の座標系の曲げを y 軸まわりに取り違える・折り返しの前後の切り替えを同じ順序にする・
     ゴーストの経路の逆向きの区間を順向きにする、の 3 通りで、上の門が赤になる。

【外部真値】Householder の鏡映・反射の回数と裏返り、Smith / Coddington の平板の式、Gauss の結像式と
シャインプルーフの tanθ' = m·tanθ、Fresnel の式と λ/4 単層膜の閉形式、平板の 2 回反射のずれ 2t·tanθ'·cosθ、
軸外し放物面の焦点、OSS の optiland(MIT)。【学習】0。【較正】0。

【正直な限界】ゴーストの照度は、視野 0 の点光源のゴーストの光線の分布を全視野に使う(視野で形が変わるのは無視)。
各面の反射率は視野 0 の主光線の入射角での無偏光の値。半透鏡の膜は与えた R(50 %)で、角度・波長の依存は持たない。
検出は雑音の無い像の差の閾値(1.5 %)で、実際の閾値は雑音と照明のむらで決まる。

【来歴】Smith, *Modern Optical Engineering*(平面鏡・平行平板・ゴースト)/ Welford, *Aberrations of Optical
Systems*(傾き・偏心)/ Scheimpflug, GB 1196(1904)/ Merklinger, *Focusing the View Camera*(1993)/
Born & Wolf §1.6・Macleod §2(膜)/ optiland の文書(MIT、絶対座標の置き方と軸外し放物面の例)/
ray-optics の文書(BSD-3、座標の切り替えの種類)。コードは写していない。

使い方:
    py -3.11 examples/poc_noncoaxial_optics.py               # 門だけ(CI=1 で短く)
    FULLSEYE_FIGURE_DIR=DIR py -3.11 examples/poc_noncoaxial_optics.py   # 図も書く
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import optdraw as OD  # noqa: E402
import raytrace as RT  # noqa: E402
import raytrace3d as R3  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"
INF = math.inf
FAILS: list[str] = []
GATES: list[str] = []
NUMBERS: dict[str, float] = {}

#: 2026-10-15 に optiland 0.6.3(別の venv、絶対座標で同じ姿勢の面を組む)で得た、各系の束の最初の光線(主光線)と
#: 最後の光線の像面の点 [mm](大域、x y z を 2 本ぶん)。手元に optiland が無いときはこの値と照合する(門)。
OPTILAND_RECORDED = {
    "folded_singlet": [0.0, 56.7035864987, 45.0, -0.1508769298, 56.7035864987, 45.0549147115],
    "periscope": [0.0, 30.0, 71.7035864988, -0.1508769298, 30.0549147115, 71.7035864988],
    "tilted_plate": [0.0, -0.9881057337, 103.6918598033, -0.0204058814, -0.9902494119, 103.6918598033],
    "off_axis_parabola": [0.0, -7e-10, -50.0000000019, -1e-10, -7e-10, -50.0000000019],
    "compound_fold": [-43.9214946643, 25.6378926469, 26.8292942688, -43.6123260635, 25.6377213052, 26.0537705625],
    "epi_beamsplitter": [0.0, 1.1640138876, 242.9144678983, -0.3412351061, 1.2605468506, 242.9144678983],
}


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


def _householder(p, p0, n):
    return p - 2.0 * ((p - p0) @ n) * n


# --------------------------------------------------------------------------- #
# 1. 共軸の一致
# --------------------------------------------------------------------------- #
def coaxial_cases():
    cass = RT.lens_system([{"R": -400.0, "t": 150.0, "n": 1.0, "k": -1.0, "ap": 50, "mirror": True},
                           {"R": -120.0, "t": 200.0, "n": 1.0, "k": -3.0, "ap": 15, "mirror": True,
                            "decenter": (0.1, 0.2), "tilt": (0.05, 0.03)}], stop=0, field=0.2)
    tilted = RT.lens_system([{"R": 40, "t": 5, "n": "BK7", "ap": 10, "tilt": (0.3, 0.2), "decenter": (0.05, -0.02)},
                             {"R": -60, "t": None, "n": 1.0, "asph": (1e-6, -2e-9)}], object_mm=300, field=3.0)
    return [RT.lens_system(), doublet(),
            RT.lens_system([{"R": 61.47, "t": 6.0, "n": "BK7", "ap": 12.5}, {"R": -44.64, "t": 2.5, "n": "SF2"},
                            {"R": -129.94, "t": None, "n": 1.0}], stop=0),
            RT.lens_system([{"R": INF, "t": 5.0, "n": "BK7", "ap": 12.5},
                            {"R": -(RT.refractive_index("BK7") - 1.0) * 100.0, "t": None, "n": 1.0,
                             "k": -RT.refractive_index("BK7") ** 2}], stop=0),
            RT.lens_system([{"R": -200.0, "t": None, "n": 1.0, "k": -1.0, "ap": 25.0, "mirror": True}], stop=0),
            RT.lens_system([{"R": -200.0, "t": None, "n": 1.0, "ap": 25.0, "mirror": True}], stop=0),
            cass, tilted]


def doublet():
    """接合の 2 枚玉(BK7 相当のクラウン n_d 1.5168 / ν_d 64.17 + SF2 相当のフリント 1.6477 / 33.85、f ≈ 100 mm)。"""
    return RT.lens_system([{"R": 61.47, "t": 6.0, "n": (1.5168, 64.17), "ap": 12.5},
                           {"R": -44.64, "t": 2.5, "n": (1.6477, 33.85)},
                           {"R": -129.94, "t": None, "n": 1.0}], stop=0)


def coaxial_worst(trace=None):
    trace = R3._trace if trace is None else trace
    worst, n_ok = 0.0, 0
    for s in coaxial_cases():
        ap = s["surfaces"][s["stop"]]["ap"]
        g = np.linspace(-1.0, 1.0, 9)
        X, Y = np.meshgrid(g, g)
        P = np.stack([X.ravel() * ap * 0.9, Y.ravel() * ap * 0.9, np.full(X.size, -20.0)], 1)
        D = np.tile([0.0, 0.02, 1.0], (X.size, 1))
        a = RT.trace_rays(s, P, D)
        b = trace(R3.noncoaxial_system(s), P, D)
        if not np.array_equal(a["valid"], b["valid"]):
            return math.inf, n_ok
        worst = max(worst, float(np.nanmax(np.abs(a["points"] - b["points"]))),
                    float(np.nanmax(np.abs(a["opl"] - b["opl"]))))
        n_ok += int(a["valid"].sum())
    return worst, n_ok


def chapter_coaxial():
    print("\n1. 共軸の一致(raytrace の処方 8 本を noncoaxial_system に変換)")
    w, n = coaxial_worst()
    NUMBERS["coaxial_worst"] = w
    gate("共軸の処方 8 本の交点・光路長が raytrace.trace_rays と 1e-12 以内", w <= 1e-12,
         "最大 %.1e mm(%d 本の有効な光線。鏡の後の座標系の反転は R と y の符号の反転で、丸めない)" % (w, n))
    # 瞳を満たす束(raytrace.ray_bundle の打ち出し)も、変換した系の noncoaxial_trace と同じ像面の点になる
    d = doublet()
    rb = RT.ray_bundle(d, field=0.0, rings=4)
    tb = R3.noncoaxial_trace(R3.noncoaxial_system(d), fields=[(0.0, 0.0)], rings=4)["fields"][0]
    wb = float(np.nanmax(np.abs(rb["image_xy"][rb["valid"]] - tb["image_xy"][tb["valid"]])))
    px, py, opd, val = RT.opd_samples(d, field=0.0, size=32)
    rms = float(np.sqrt(np.mean(np.asarray(opd)[np.asarray(val)] ** 2)))
    NUMBERS["bundle_worst"] = wb
    gate("瞳を満たす束の像面の点が raytrace.ray_bundle と 1e-12 以内(同じ打ち出し)", wb <= 1e-12 and
         int(rb["valid"].sum()) == int(tb["valid"].sum()),
         "最大 %.1e mm(%d 本)。参考: 同じ 2 枚玉の軸上の OPD の RMS %.3f 波(raytrace.opd_samples)"
         % (wb, int(rb["valid"].sum()), rms))


# --------------------------------------------------------------------------- #
# 2. 折り返しミラー
# --------------------------------------------------------------------------- #
LENS = [{"R": 51.68, "t": 5.0, "n": (1.5168, 64.17), "ap": 12.5}, {"R": INF, "t": 40.0, "n": 1.0}]


def fold_worst(tilts, expand=None):
    bfl = RT.paraxial_trace(RT.lens_system())["bfl"]
    worst = 0.0
    unfolded = R3.noncoaxial_system([LENS[0], {"R": INF, "t": bfl, "n": 1.0}], stop=0)
    for tilt in tilts:
        els = LENS + ([{"type": "fold_mirror", "tilt": tilt, "ap": 40, "t": bfl - 40.0}] if expand is None
                      else expand(tilt, bfl - 40.0))
        folded = R3.noncoaxial_system(els, stop=0)
        mir = [s_ for s_ in R3.noncoaxial_layout(folded)["surfaces"] if s_["mirror"]][0]
        n = np.array(mir["normal"])                         # 鏡の法線(大域)= 姿勢の局所 z
        assert np.max(np.abs(n - RT._rot(*tilt)[:, 2])) < 1e-15
        p0 = np.array([0.0, 0.0, 45.0])
        for f in [(0.0, 0.0), (1.5, 0.0), (0.0, 2.0), (1.0, -1.5)]:
            a = R3._chief(folded, f)["points"][0, -1]
            b = R3._chief(unfolded, f)["points"][0, -1]
            worst = max(worst, float(np.max(np.abs(a - _householder(b, p0, n)))))
    return worst


def folded_epi(n_mirrors):
    """同軸落射の検査レンズ(noncoaxial_example の epi_beamsplitter)の、カメラ側をミラーで折った版。"""
    base = R3.noncoaxial_example("epi_beamsplitter")
    img = base["image_mm"]
    els = [dict(e) for e in base["elements"]]
    last = els[-1]
    if n_mirrors == 0:
        els[-1] = dict(last, t=img)
    elif n_mirrors == 1:
        els[-1] = dict(last, t=40.0)
        els.append({"type": "fold_mirror", "tilt": (45.0, 0.0), "ap": 25.0, "t": img - 40.0, "label": "M1"})
    else:
        els[-1] = dict(last, t=40.0)
        els.append({"type": "fold_mirror", "tilt": (45.0, 0.0), "ap": 25.0, "t": 70.0, "label": "M1"})
        els.append({"type": "fold_mirror", "tilt": (45.0, 0.0), "ap": 25.0, "t": img - 110.0, "label": "M2"})
    return R3.noncoaxial_system(els, stop="L1", object_mm=150.0)


def chapter_fold():
    print("\n2. 折り返しミラー: 像 = 展開した像の鏡映、反射の回数と裏返り、装置を小さくする")
    tilts = [(45.0, 0.0), (0.0, 30.0), (20.0, 30.0), (-35.0, 10.0)]
    w = fold_worst(tilts)
    NUMBERS["fold_worst"] = w
    gate("折り返した像 = 展開した像の Householder 鏡映(4 通りの傾き × 4 視野)", w < 1e-9, "最大 %.1e mm" % w)
    o1 = R3.image_orientation(R3.noncoaxial_example("folded_singlet"))
    o2 = R3.image_orientation(R3.noncoaxial_example("periscope"))
    o0 = R3.image_orientation(R3.noncoaxial_system(RT.lens_system()))
    gate("像の向き: 反射 0 回は倒立(180° 回転)、1 回は裏返り、2 回は裏返らない(sign det = (−1)^n)",
         (not o0["reversed"]) and abs(abs(o0["rotation_deg"]) - 180.0) < 1e-9 and o1["reversed"]
         and not o2["reversed"] and o1["parity_closed_form"] == -1 and o2["parity_closed_form"] == 1,
         "det = %+.3f / %+.3f / %+.3f" % (o0["det"], o1["det"], o2["det"]))
    sys0, sys1, sys2 = folded_epi(0), folded_epi(1), folded_epi(2)
    d0, d2 = OD.noncoaxial_drawing(sys0, rotate_deg=90), OD.noncoaxial_drawing(sys2, rotate_deg=90)
    s0, s2 = R3.noncoaxial_spot(sys0, rings=6), R3.noncoaxial_spot(sys2, rings=6)
    h0, h2 = d0["values"]["footprint"][1], d2["values"]["footprint"][1]
    NUMBERS.update({"height_straight": h0, "height_folded": h2, "path_folded": d2["values"]["path_length"]})
    gate("同軸落射のカメラ側を 2 枚の鏡で折り返すと装置の高さが 3 分の 2 以下になり、像の RMS は変わらない",
         h2 < 2.0 / 3.0 * h0 and abs(s0["rms_radius"] - s2["rms_radius"]) < 1e-12,
         "高さ %.1f → %.1f mm、光路長 %.2f / %.2f mm、RMS %.6f / %.6f mm"
         % (h0, h2, d0["values"]["path_length"], d2["values"]["path_length"], s0["rms_radius"], s2["rms_radius"]))
    return d0, d2


# --------------------------------------------------------------------------- #
# 3. 傾いた平板と半透鏡
# --------------------------------------------------------------------------- #
def plate_curves(angles):
    rows = []
    base = [{"R": 51.68, "t": 5.0, "n": (1.5168, 64.17), "ap": 2.0}, {"R": INF, "t": 40.0, "n": 1.0}]
    sn = R3.noncoaxial_system(base[:1] + [{"R": INF, "t": 70.0, "n": 1.0}], stop=0)
    f0t, f0s = R3._foci(sn, (0.0, 0.0))
    for th in angles:
        sp = R3.noncoaxial_system(base + [{"type": "plate", "thickness": 5.0, "n": "BK7", "tilt": (th, 0.0), "ap": 30,
                                  "t": 30.0}], stop=0)
        ft, fs = R3._foci(sp, (0.0, 0.0))
        ch = R3._chief(sp, (0.0, 0.0))
        d = ch["dirs"][0, -1]
        cf = R3.tilted_plate_shift(5.0, "BK7", th)
        rows.append({"theta": th, "lat": abs(float(ch["points"][0, -1][1])), "lat_cf": cf["lateral_shift_mm"],
                     "ast": float((ft - fs) @ d), "ast_cf": cf["astigmatism_signed_mm"],
                     "sag": float((fs - f0s) @ d), "sag_cf": cf["sagittal_shift_mm"]})
    return rows


def chapter_plate():
    print("\n3. 傾いた平板と半透鏡の 2 本の枝")
    angles = [0.0, 10.0, 20.0, 30.0, 45.0, 60.0] if REDUCED else list(np.arange(0.0, 61.0, 5.0))
    rows = plate_curves(angles)
    wl = max(abs(r["lat"] - r["lat_cf"]) for r in rows)
    wa = max(abs(r["ast"] - r["ast_cf"]) for r in rows)
    ws = max(abs(r["sag"] - r["sag_cf"]) for r in rows)
    NUMBERS.update({"plate_lat_err": wl, "plate_ast_err": wa})
    r30 = [r for r in rows if r["theta"] == 30.0][0]
    gate("横ずれ t·sinθ(1 − cosθ/√(n² − sin²θ)) が実光線と 1e-12 mm、非点隔差が 1e-6 mm、球欠の焦点ずれが 1e-6 mm",
         wl < 1e-12 and wa < 1e-6 and ws < 1e-6,
         "30° で横ずれ %.4f mm・非点隔差 %.4f mm(接線像が遠い)。最大誤差 %.1e / %.1e / %.1e" % (r30["lat"], r30["ast"], wl, wa, ws))
    b = R3.beamsplitter_branches()
    cf = R3.tilted_plate_shift(3.0, "BK7", 45.0)
    lens = R3._paraxial_lens_elements(100.0, 5.0, 40.0)
    s0 = R3.noncoaxial_system(lens[:1] + [dict(lens[1], t=None)], stop=0)
    fp = R3._focus_point(s0, (0.0, 0.0))
    want = _householder(fp, np.array([0.0, 0.0, 42.0]), RT._rot(45.0, 0.0)[:, 2])
    er = float(np.max(np.abs(np.array(b["reflect"]["image_point"]) - want)))
    et = abs(abs(b["transmit"]["image_point"][1]) - cf["lateral_shift_mm"])
    gate("45° の半透鏡: 反射の枝の像 = 展開した焦点の鏡映、透過の枝の横ずれ = 閉形式", er < 1e-6 and et < 1e-12,
         "反射 %.1e mm、透過 %.1e mm(横ずれ %.4f mm)、エネルギー 0.5 / 0.5" % (er, et, cf["lateral_shift_mm"]))
    return rows


# --------------------------------------------------------------------------- #
# 4. シャインプルーフ
# --------------------------------------------------------------------------- #
def scheimpflug_system(image_tilt):
    d = doublet()
    sch = R3.scheimpflug_tilt(d, object_distance_mm=200.0, object_tilt_deg=30.0, verify=False)
    els = [dict(R=s["R"], t=s["t"], n=s["n"]) for s in d["surfaces"][:-1]]
    els[0]["ap"] = 4.0                                  # f/12.5: 高さによるピントずれが収差より大きくなる絞り
    els.append({"R": d["surfaces"][-1]["R"], "t": sch["image_distance_mm"], "n": 1.0})
    return R3.noncoaxial_system(els, stop=0, object_mm=200.0, object_tilt=(30.0, 0.0), image_tilt=(image_tilt, 0.0)), sch


def chapter_scheimpflug():
    print("\n4. シャインプルーフ: 傾いた物面(30°)に対する像面の傾き")
    r = R3.scheimpflug_tilt(doublet(), 200.0, 30.0, heights_mm=[-0.2, -0.1, 0.0, 0.1, 0.2])
    err = abs(r["image_tilt_traced_deg"] - r["image_tilt_deg"])
    NUMBERS.update({"sch_tilt": r["image_tilt_deg"], "sch_err": err})
    # 閉形式の独立の確かめ: Gauss の式で傾いた物面の 2 点を写す
    f, s = r["efl_mm"], r["s_mm"]
    pts = []
    for y in (-1.0, 1.0):
        sy = s - y * math.tan(math.radians(30.0))
        spy = sy * f / (sy - f)
        pts.append((-spy / sy * y, spy))
    slope = (pts[1][1] - pts[0][1]) / (pts[1][0] - pts[0][0])
    gate("像面の傾き: 実光線(近軸極限)が閉形式 tanθ' = m·tanθ と 1e-3° 以内、Gauss の式の 2 点とも一致",
         err < 1e-3 and abs(math.degrees(math.atan(slope)) - r["image_tilt_deg"]) < 1e-9,
         "θ' = %.4f°(m = %.4f)、実光線 %.4f°" % (r["image_tilt_deg"], r["magnification"], r["image_tilt_traced_deg"]))
    heights = [-6.0, -3.0, 0.0, 3.0, 6.0] if REDUCED else list(np.linspace(-6.0, 6.0, 25))
    flat, _ = scheimpflug_system(0.0)
    tilt, _ = scheimpflug_system(r["image_tilt_deg"])
    rf = [R3.noncoaxial_spot(flat, field=(0.0, h), rings=4)["rms_radius"] for h in heights]
    rt = [R3.noncoaxial_spot(tilt, field=(0.0, h), rings=4)["rms_radius"] for h in heights]
    NUMBERS.update({"sch_rms_flat": max(rf), "sch_rms_tilt": max(rt)})
    gate("撮像素子を閉形式の角だけ傾けると、物面の全体(±6 mm、f/12.5)のぼけの最大が 3 分の 1 以下になる",
         max(rt) < max(rf) / 3.0, "最大 RMS %.4f → %.4f mm(残りは像面の湾曲と非点)" % (max(rf), max(rt)))
    y_h = r["hinge_height_mm"]
    zi = r["rear_principal_mm"] + r["s_prime_mm"]
    hinge_img = (r["rear_principal_mm"] - zi) / math.tan(math.radians(r["image_tilt_deg"]))
    gate("ヒンジ: 物面と前側主面、像面と後側主面が同じ高さ s/tanθ で交わる", abs(hinge_img - y_h) < 1e-9 * y_h,
         "高さ %.3f mm" % y_h)
    return heights, rf, rt, tilt


# --------------------------------------------------------------------------- #
# 5. 偽の欠陥
# --------------------------------------------------------------------------- #
#: 裏面の 2 層の反射防止膜(ガラス側から Ta₂O₅ 20 nm・MgF₂ 157.5 nm)。裏面の入射角(ガラスの中で 28°、空気側で 45°)
#: で反射率が最小になるように、20 / 2.5 nm 刻みの格子で探した(0.39 %)。単層の MgF₂ λ/4 は同じ角で 2.1 %。
VCOAT = [("TA2O5", 20.0), ("MGF2", 157.5)]


def epi_variant(kind):
    """同軸落射の検査レンズ: 裏面が裸(bare)/ MgF₂ の λ/4(mgf2)/ 2 層の膜(vcoat)/ 1° の楔(wedge)。"""
    plate = {"type": "plate", "thickness": 3.0, "n": "BK7", "tilt": (45.0, 0.0), "ap": 30.0, "beamsplitter": 0.5,
             "branch": "transmit", "t": 30.0, "label": "BS"}
    if kind == "mgf2":
        plate["coating_back"] = "MGF2"
    if kind == "vcoat":
        plate["coating_back"] = VCOAT
    if kind == "wedge":
        plate["wedge"] = (1.0, 0.0)
    els = [plate, {"R": 61.47, "t": 6.0, "n": "BK7", "ap": 12.5, "label": "L1"},
           {"R": -44.64, "t": 2.5, "n": "SF2", "label": "L2"}, {"R": -129.94, "t": None, "n": 1.0}]
    return R3.noncoaxial_system(els, stop="L1", object_mm=150.0)


def scene(xs, ys):
    """鏡面の部品(同軸落射で明るい = 1)に、凹み(直径 2 mm)と細い傷(幅 0.15 mm)。欠陥は光を散らして暗い(0.1)。"""
    X, Y = np.meshgrid(xs, ys)
    S = np.ones_like(X)
    S[(X + 1.0) ** 2 + (Y + 1.0) ** 2 < 1.0 ** 2] = 0.1
    S[(np.abs(X - 2.0) < 0.075) & (np.abs(Y) < 2.0)] = 0.1
    return S


def sensor_image(sysd, npx=360, pitch=0.02):
    """像面の照度の画像: 本来の像 + 全てのゴースト(視野 0 の点像のゴーストの光線分布を、写像のヤコビアンで置く)。"""
    from scipy import ndimage
    ga = R3.ghost_analysis(sysd, rings=6)
    Jn = np.array(ga["image_jacobian"])
    cn = np.array(ga["image_chief_xy"])
    u = (np.arange(npx) - (npx - 1) / 2.0) * pitch
    U, V = np.meshgrid(u + cn[0], -u + cn[1])               # 像面の (x, y)、本来の像の中心を真ん中に、行 = 上から
    obj_span = (npx * pitch / abs(Jn[1, 1])) * 0.5 + 6.0
    xs = np.linspace(-obj_span, obj_span, 2 * npx + 1)
    S = scene(xs, xs)
    dx = xs[1] - xs[0]

    def sample(J, c, img):
        Ji = np.linalg.inv(J)
        q = np.stack([U.ravel() - c[0], V.ravel() - c[1]], 0)
        p = Ji @ q                                          # 物面の (x, y)
        col = (p[0] - xs[0]) / dx
        row = (p[1] - xs[0]) / dx
        return ndimage.map_coordinates(img, [row, col], order=1, mode="nearest").reshape(U.shape)

    I = sample(Jn, cn, S)
    lay = R3._layout(sysd)
    for g in ga["ghosts"]:
        if g["jacobian"] is None or not math.isfinite(g["radius_mm"]) or g["reach_fraction"] == 0.0:
            continue
        gp = R3.ghost_path(sysd, i=g["i"], j=g["j"], rings=8)
        hits = gp["image_xy"][gp["valid"]]
        if len(hits) < 3:
            continue
        cen = hits.mean(0)
        # 点像のゴーストの形(画素に積む)。広がりが像面の 3 倍を超えるものは一様な明るさとして足す
        rel = hits - cen
        if np.max(np.abs(rel)) > 3.0 * npx * pitch:
            I += g["energy_ratio"] * g["reach_fraction"] * float(np.mean(S))
            continue
        k = int(np.ceil(np.max(np.abs(rel)) / pitch)) + 1
        K = np.zeros((2 * k + 1, 2 * k + 1))
        ij = np.round(rel / pitch).astype(int) + k
        np.add.at(K, (2 * k - ij[:, 1], ij[:, 0]), 1.0)
        K /= K.sum()
        G = sample(np.array(g["jacobian"]), np.array(g["centroid_xy"]) - (cen - np.array(g["centroid_xy"])), S)
        G = ndimage.convolve(G, K, mode="nearest")
        I += g["energy_ratio"] * g["reach_fraction"] * G
    return I, ga, (cn, Jn, u)


def detect(I, thr=0.015, min_px=30):
    """背景(像全体の中央値 = 照明のむらの無い鏡面)との差が −thr を下回る画素の塊を数える(雑音の無い像の単純な検出)。"""
    from scipy import ndimage
    bg = float(np.median(I))
    m = (I - bg) / bg < -thr
    lab, n = ndimage.label(m)
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    keep = [i + 1 for i, s_ in enumerate(sizes) if s_ >= min_px]
    cents = [ndimage.center_of_mass(m, lab, i) for i in keep]
    return len(keep), cents, np.isin(lab, keep)


def chapter_ghost():
    print("\n5. 偽の欠陥: 同軸落射の半透鏡の裏面が作るゴースト、膜と傾きで消す")
    out = {}
    for kind in ("bare", "mgf2", "vcoat", "wedge"):
        sysd = epi_variant(kind)
        npx = 240 if REDUCED else 360
        I, ga, geo = sensor_image(sysd, npx=npx, pitch=0.03 if REDUCED else 0.02)
        n, cents, mask = detect(I)
        bsg = [g for g in ga["ghosts"] if g["label"] == "BS:front/BS:back"][0]
        out[kind] = {"I": I, "n": n, "cents": cents, "mask": mask, "ghost": bsg, "ga": ga, "geo": geo, "sys": sysd}
        print("   %-6s ゴースト(BS 前面/裏面)エネルギー比 %.4f、ずれ %s mm、半径 %.3f mm → 検出 %d 個"
              % (kind, bsg["energy_ratio"], np.round(bsg["offset_xy"], 3), bsg["radius_mm"], n))
    g = out["bare"]["ghost"]
    # 閉形式: Fresnel(無偏光)を裏面の入射角で
    n_ = RT.refractive_index("BK7")
    ang = math.radians(out["bare"]["ga"]["incidence_deg"]["2"])
    ci = math.cos(ang)
    # 裏面は「ガラス → 空気」。前の媒質(ガラス)の中の角 ang から、空気側の角を Snell で
    s_air = n_ * math.sin(ang)
    c_air = math.sqrt(1.0 - s_air * s_air)
    rs = ((n_ * ci - c_air) / (n_ * ci + c_air)) ** 2
    rp = ((ci - n_ * c_air) / (ci + n_ * c_air)) ** 2
    Rb = 0.5 * (rs + rp)
    e_cf = 0.5 * Rb
    # surface_reflectance(材料表 + 膜の特性行列、別の実装)も同じ値を出す
    Rs_op = R3.surface_reflectance("BK7", 1.0, angle_deg=math.degrees(ang))["R"]
    NUMBERS["back_R_op"] = Rs_op
    NUMBERS.update({"ghost_energy": g["energy_ratio"], "ghost_energy_cf": e_cf})
    gate("ゴーストのエネルギー比 = R_前(0.5)× Fresnel(裏面、入射角 %.2f°、無偏光)" % math.degrees(ang),
         abs(g["energy_ratio"] - e_cf) < 1e-6 and abs(Rs_op - Rb) < 1e-9,
         "%.6f / 閉形式 %.6f(裏面の R: surface_reflectance %.6f / Fresnel %.6f)" % (g["energy_ratio"], e_cf, Rs_op, Rb))
    # 点光源の像面の照度の図(ghost_image): 最も明るいゴーストの画素は像の最も明るい画素の何分の 1 か
    gi = R3.ghost_image(out["bare"]["sys"], size=96)
    NUMBERS["ghost_image_max_log10"] = float(gi.max())
    print("   ghost_image(点光源、96 画素、視野は最も広いゴーストまで): 像の最も明るい画素を 1 とした最大 %.2f(log10。像とゴーストが同じ画素に重なる)" % gi.max())
    # ずれ: 物面で 2t·tanθ'·cosθ(主光線が平板に当たる角で)、像面で × 倍率
    th = math.radians(out["bare"]["ga"]["incidence_deg"]["1"])
    tp = math.asin(math.sin(th) / n_)
    d_obj = 2.0 * 3.0 * math.tan(tp) * math.cos(th)
    m = abs(out["bare"]["ga"]["image_jacobian"][1][1])
    off = abs(g["offset_xy"][1])
    NUMBERS.update({"ghost_offset": off, "ghost_offset_cf": m * d_obj})
    gate("偽の欠陥のずれ = 倍率 × 2t·tanθ'·cosθ(5 % 以内。ぼけたゴーストの重心と主光線の差)",
         abs(off - m * d_obj) < 0.05 * m * d_obj, "像面で %.3f mm / 閉形式 %.3f mm" % (off, m * d_obj))
    # 3 個目の検出が、ゴーストの予測位置(凹みの像 + ゴーストのずれ)にあること
    cn, Jn, uu = out["bare"]["geo"]
    pit = Jn @ np.array([-1.0, -1.0]) + cn
    want_g = pit + np.array(g["offset_xy"])
    pitch = uu[1] - uu[0]
    pos = [np.array([uu[int(round(c))] + cn[0], -uu[int(round(r))] + cn[1]]) for r, c in
           [(rc[0], rc[1]) for rc in out["bare"]["cents"]]]
    dist = min(float(np.hypot(*(p_ - want_g))) for p_ in pos) if pos else math.inf
    NUMBERS["false_defect_pos_err"] = dist
    gate("裏面が裸の半透鏡では欠陥が 3 個(本物の凹みと傷 + ゴーストの偽の凹み)、2 層の膜と 1° の楔では本物の 2 個だけ。"
         "偽の凹みの位置 = 凹みの像 + ゴーストのずれ(0.2 mm 以内)",
         out["bare"]["n"] == 3 and out["vcoat"]["n"] == 2 and out["wedge"]["n"] == 2 and dist < 0.2,
         "検出数 裸 %d / MgF₂ 単層 %d / 2 層 %d / 楔 %d(本物は凹みと傷の 2 個)、偽の凹みの位置の誤差 %.3f mm(画素 %.2f mm)"
         % (out["bare"]["n"], out["mgf2"]["n"], out["vcoat"]["n"], out["wedge"]["n"], dist, pitch))
    ev, em = out["vcoat"]["ghost"]["energy_ratio"], out["mgf2"]["ghost"]["energy_ratio"]
    rw = out["wedge"]["ghost"]
    u = out["wedge"]["geo"][2]
    half = 0.5 * (u[-1] - u[0])
    NUMBERS.update({"ghost_mgf2": em, "ghost_vcoat": ev, "ghost_wedge_offset": abs(rw["offset_xy"][1])})
    gate("2 層の膜でゴーストが 0.5 % 未満(単層の MgF₂ は 45° で 1 % 前後)、楔でゴーストの重心が撮像素子の外",
         ev < 0.005 and (abs(rw["offset_xy"][1]) > half or rw["reach_fraction"] == 0.0),
         "単層 %.4f・2 層 %.4f、楔のずれ %.2f mm(撮像素子の半幅 %.2f mm)" % (em, ev, abs(rw["offset_xy"][1]), half))
    return out


# --------------------------------------------------------------------------- #
# 6. 第 2 実装(optiland)
# --------------------------------------------------------------------------- #
def second_systems():
    yield "folded_singlet", R3.noncoaxial_example("folded_singlet")
    yield "periscope", R3.noncoaxial_example("periscope")
    yield "tilted_plate", R3.noncoaxial_example("tilted_plate")
    yield "off_axis_parabola", R3.noncoaxial_example("off_axis_parabola")
    yield "compound_fold", R3.noncoaxial_system([{"R": 51.68, "t": 5.0, "n": 1.5168, "ap": 12.5},
                                        {"R": INF, "t": 40.0, "n": 1.0},
                                        {"type": "fold_mirror", "tilt": (20.0, 30.0), "ap": 40.0, "t": 30.0},
                                        {"R": -80.0, "t": 4.0, "n": 1.6, "ap": 15.0},
                                        {"R": INF, "t": 20.0, "n": 1.0, "tilt": (3.0, -2.0), "decenter": (0.3, -0.2)}],
                                       stop=0)
    yield "epi_beamsplitter", R3.noncoaxial_example("epi_beamsplitter")


def chapter_second():
    print("\n6. 第 2 実装(OSS optiland、MIT)")
    try:
        from optiland import optic
        from optiland.materials import IdealMaterial
        from optiland.rays import RealRays
        have = True
    except ImportError:
        have = False
    worst_rec, worst_live = 0.0, 0.0
    for name, s in second_systems():
        b = R3._bundle(s, tuple(s["field"]), rings=3, pupil_fill=0.9)
        ok = b["valid"]
        P0, D0 = b["points"][ok, 0, :], b["dirs"][ok, 0, :]
        tr = R3._trace(s, P0, D0)
        ours = np.concatenate([tr["points"][0, -1], tr["points"][-1, -1]])
        worst_rec = max(worst_rec, float(np.max(np.abs(ours - np.array(OPTILAND_RECORDED[name])))))
        if not have:
            continue
        lay = R3._layout(s)
        before, after = R3._media(s)
        o = optic.Optic()
        o.surfaces.add(index=0, x=0.0, y=0.0, z=float(P0[0, 2]), material=IdealMaterial(n=s["index_object"]))
        idx = 1
        for k, r in enumerate(s["records"]):
            if r["kind"] != "surface":
                continue
            Rg, og = lay["poses"][k]
            a, bb, g = (math.radians(v) for v in R3._euler_zyx(Rg))
            R = r["R"] if math.isfinite(r["R"]) else np.inf
            o.surfaces.add(index=idx, x=og[0], y=og[1], z=og[2], rx=a, ry=bb, rz=g, radius=R, conic=r["k"],
                           material="mirror" if r["reflect"] else IdealMaterial(n=after[k]), is_stop=(idx == 1))
            idx += 1
        Fi, oi = lay["image"]
        a, bb, g = (math.radians(v) for v in R3._euler_zyx(Fi))
        o.surfaces.add(index=idx, x=oi[0], y=oi[1], z=oi[2], rx=a, ry=bb, rz=g)
        o.set_aperture(aperture_type="EPD", value=10.0)
        o.add_wavelength(value=s["wavelength_um"], is_primary=True)
        o.set_field_type(field_type="angle")
        o.add_field(y=0.0)
        n = len(P0)
        rays = RealRays(P0[:, 0], P0[:, 1], P0[:, 2], D0[:, 0], D0[:, 1], D0[:, 2], np.ones(n),
                        np.full(n, s["wavelength_um"]))
        o.surfaces.trace(rays)
        pts = np.stack([np.asarray(o.surfaces.x), np.asarray(o.surfaces.y), np.asarray(o.surfaces.z)], -1)[1:]
        pts = np.transpose(pts, (1, 0, 2))
        worst_live = max(worst_live, float(np.nanmax(np.abs(pts - tr["points"][:, 1:, :]))))
    NUMBERS["optiland_recorded_worst"] = worst_rec
    # 記録値との許容差 1e-7 mm: 記録は 1e-10 に丸めてあり、起点の光線は _aim(有限差分ヤコビアンの Newton 法、絞りでの収束判定
    # 1e-11 × 口径)で作る。その床が環境で変わり、半透鏡の系では起点の 1e-10 mm のずれが像面で約 4 倍になる。CI の 1 環境で
    # 1.6e-8 mm が出て 1e-8 が落ちた(手元 5e-11)。生の照合(同じ光線を optiland へ渡す)は起点が共通なので 1e-10 のまま。
    gate("optiland(2026-10-15 の記録、6 系)の像面の点と 1e-7 mm 以内", worst_rec < 1e-7,
         "最大 %.1e mm(記録は 1e-10 に丸め)" % worst_rec)
    if have:
        NUMBERS["optiland_live_worst"] = worst_live
        gate("optiland と同じ光線の全ての面の交点が 1e-10 mm 以内(6 系)", worst_live < 1e-10, "最大 %.1e mm" % worst_live)
    else:
        print("   optiland が入っていない —— 記録値だけで照合した(2026-10-15 の実測は全ての面の交点で最大 9.8e-14 mm)")
    oap = R3.noncoaxial_trace(R3.noncoaxial_example("off_axis_parabola"), rings=4)["fields"][0]
    p = oap["points"][oap["valid"], -1, :]
    w = float(np.max(np.abs(p - np.array([0.0, 0.0, -50.0]))))
    gate("軸外し放物面(R −200、36 mm 外し)の全光線が親の焦点 (0, 0, −50) に集まる", w < 1e-8, "最大 %.1e mm" % w)


# --------------------------------------------------------------------------- #
# 7. 壊して確かめる
# --------------------------------------------------------------------------- #
def chapter_probes():
    print("\n7. 壊して確かめる")
    keep = R3._REV
    try:
        R3._REV = np.diag([-1.0, 1.0, -1.0])
        w, _ = coaxial_worst()
    finally:
        R3._REV = keep
    gate("探針: 反射の後の座標系を y 軸まわりに回すと、共軸の門が赤", w > 1e-3, "最大 %.2g" % w)

    def naive(tilt, t):
        return [{"type": "break", "tilt": (tilt[0], tilt[1], 0.0), "t": 0.0},
                {"R": INF, "mirror": True, "ap": 40, "t": 0.0},
                {"type": "break", "tilt": (tilt[0], tilt[1], 0.0), "t": t}]
    w = fold_worst([(0.0, 30.0), (20.0, 30.0)], expand=naive)
    gate("探針: 折り返しの前後の切り替えを同じ順序・同じ角にすると、鏡映の門が赤", w > 1.0, "最大 %.3g mm" % w)
    keep_steps = R3._ghost_steps

    def forward_only(sysd, i, j):
        st = keep_steps(sysd, i, j)
        return [(k, a, +1) for (k, a, _) in st]
    # 2 枚を貼り合わせた平板(3 mm の n 1.5 と 2 mm の n 1.7): 外側の 2 面のゴーストは間の接合面を逆向きにくぐる
    s = R3.noncoaxial_system([{"R": 51.68, "t": 5.0, "n": (1.5168, 64.17), "ap": 0.3}, {"R": INF, "t": 40.0, "n": 1.0},
                     {"R": INF, "t": 3.0, "n": 1.5, "ap": 20, "label": "W1"},
                     {"R": INF, "t": 2.0, "n": 1.7, "ap": 20, "label": "W2"},
                     {"R": INF, "t": None, "n": 1.0, "ap": 20, "label": "W3"}], stop=0)
    want = -2.0 * (3.0 / 1.5 + 2.0 / 1.7)                 # 近軸の換算厚の 2 倍だけ像面の前

    def pick(ga):
        return [g for g in ga["ghosts"] if g["label"] == "W1/W3"][0]
    good = pick(R3.ghost_analysis(s, pupil_fill=0.5))
    try:
        R3._ghost_steps = forward_only
        bad = pick(R3.ghost_analysis(s, pupil_fill=0.5))
    finally:
        R3._ghost_steps = keep_steps
    gate("貼り合わせた平板の外側 2 面のゴーストの焦点 = 像面の前 2Σt/n(閉形式)、探針: 逆向きの区間を順向きにすると外れる",
         abs(good["focus_offset_mm"] - want) < 2e-4 and not (abs(bad["focus_offset_mm"] - want) < 2e-4),
         "%.4f mm(閉形式 %.4f)/ 壊すと %.4f mm" % (good["focus_offset_mm"], want, bad["focus_offset_mm"]))


# --------------------------------------------------------------------------- #
# 図
# --------------------------------------------------------------------------- #
def _stack_h(imgs, pad=12):
    h = max(i.shape[0] for i in imgs)
    out = []
    for im in imgs:
        a = np.full((h, im.shape[1], 3), 255, np.uint8)
        a[:im.shape[0]] = im
        out.append(a)
        out.append(np.full((h, pad, 3), 255, np.uint8))
    return np.concatenate(out[:-1], 1)


def _norm8(I, lo, hi):
    return (np.clip((I - lo) / (hi - lo), 0.0, 1.0) * 255.0).astype(np.uint8)


def make_figures(drawings, plate_rows, sch, ghost):
    if not figs.enabled():
        return
    import fullseye as fs
    d0, d2 = drawings
    try:
        r0 = OD.drawing_raster(d0, dpi=110)
        r2 = OD.drawing_raster(d2, dpi=110)
        figs.save("folded_setup", _stack_h([r0, r2]),
                  "同軸落射の検査レンズ(物体 → 45° の半透鏡 → 2 枚玉 → カメラ)の設置図。左はまっすぐ、右はカメラ側を 2 枚の "
                  "45° の鏡で折った版で、装置の高さが %.0f → %.0f mm に縮む。像の RMS は変わらない(門)。図は noncoaxial_drawing が"
                  "大域の座標で描いた実寸の断面で、光線は絞り(L1)を狙った実光線。" % (NUMBERS["height_straight"],
                                                                                NUMBERS["height_folded"]))
        ill = R3.noncoaxial_system([{"type": "break", "decenter": (0.0, 60.0), "tilt": (90.0, 0.0, 0.0), "t": 0.0},
                           {"R": INF, "n": 1.0, "ap": 10.0, "t": 60.0, "label": "LED"},
                           {"type": "fold_mirror", "tilt": (-45.0, 0.0), "ap": 30.0, "t": 150.0, "label": "BS"}],
                          stop=1)
        de = OD.noncoaxial_drawing(R3.noncoaxial_example("epi_beamsplitter"), rotate_deg=90, overlays=[ill])
        figs.save("epi_layout", OD.drawing_raster(de, dpi=120),
                  "同軸落射の光学系: 横から来る照明(赤)を半透鏡が真下の部品へ曲げ、部品で鏡面反射した光が半透鏡を透過して"
                  "2 枚玉に入る(青)。半透鏡の裏面で反射して前面で戻った光が、ずれたゴーストを作る。")
    except ImportError:
        pass
    # 平板の閉形式
    th = [r["theta"] for r in plate_rows]
    ser = [("横ずれ(実光線)", th, [r["lat"] for r in plate_rows]),
           ("非点隔差(実光線)", th, [r["ast"] for r in plate_rows]),
           ("閉形式", th, [r["lat_cf"] for r in plate_rows]), ("", th, [r["ast_cf"] for r in plate_rows])]
    figs.save_plot("plate_closed_form", ser, xlabel="平板の傾き θ [度](BK7、5 mm)", ylabel="[mm]",
                   kinds=["scatter", "scatter", "line", "line"], styles=[None, None, "dashed", "dashed"],
                   colors=["emphasis", "right", "reference", "reference"],
                   title="傾いた平板: 横ずれと非点隔差(点 = 実光線、破線 = Smith / Coddington の閉形式)",
                   caption="集光する光束(f/25)に 5 mm の平板を傾けて入れたときの、主光線の横ずれと、接線像と球欠像の"
                           "距離(非点隔差)。実光線は閉形式と 1e-6 mm 以内で重なる。")
    heights, rf, rt, _ = sch
    figs.save_plot("scheimpflug_blur", [("撮像素子を傾けない", heights, [1000 * v for v in rf]),
                                        ("閉形式の角 %.2f° だけ傾ける" % NUMBERS["sch_tilt"], heights,
                                         [1000 * v for v in rt])],
                   xlabel="物面の高さ [mm](物面は 30° 傾いている)", ylabel="ぼけの RMS [µm]",
                   colors=["wrong", "right"], title="シャインプルーフ: 撮像素子を傾けると傾いた物面の全体に合う",
                   caption="2 枚玉(f ≈ 100 mm)で 200 mm 先の 30° に傾いた面を撮る。像面を tanθ' = m·tanθ だけ傾けると、"
                           "高さによるぼけが消える(残りは収差)。")
    # 偽の欠陥
    tiles = []
    for kind, lab in (("bare", "裏面 裸: 検出 %d 個"), ("mgf2", "MgF2 単層: 検出 %d 個"), ("vcoat", "2 層の膜: 検出 %d 個"),
                      ("wedge", "1° の楔: 検出 %d 個")):
        g = ghost[kind]
        I = g["I"]
        lo, hi = float(np.percentile(I, 50)) * 0.94, float(np.percentile(I, 50)) * 1.03
        a = _norm8(I, lo, hi)
        rgb = np.stack([a, a, a], -1)
        from scipy import ndimage
        edge = g["mask"] & ~ndimage.binary_erosion(g["mask"], iterations=2)
        rgb[edge] = (230, 60, 30)
        img = rgb.astype(np.float64) / 255.0
        img = np.asarray(fs.text_box(img, lab % g["n"], (6, 6), anchor="lt", font_size=16))
        tiles.append((np.clip(img, 0, 1) * 255).astype(np.uint8))
    figs.save("false_defect", _stack_h(tiles, pad=8),
              "鏡面の部品(凹み 2 mm と傷)を同軸落射で撮った像(明るさは背景の −6〜+3 %% に伸ばして表示、赤い縁 = 検出)。"
              "1 枚目: 半透鏡の裏面が裸だと、裏面と前面の 2 回反射のゴースト(エネルギー比 %.1f %%)が凹みのずれた写しを作り、"
              "検出が 3 個になる。2 枚目: MgF2 の単層(45° で %.1f %%)。3 枚目: 2 層の膜(%.2f %%)で偽の凹みが消える。"
              "4 枚目: 裏面を 1° 傾けた楔では、ゴーストが %.1f mm ずれて撮像素子の外へ出る。"
              % (100 * NUMBERS["ghost_energy"], 100 * NUMBERS["ghost_mgf2"], 100 * NUMBERS["ghost_vcoat"],
                 NUMBERS["ghost_wedge_offset"]))
    rows = [r for r in ghost["bare"]["ga"]["ghosts"] if r["reach_fraction"] > 0.0]
    n_all = len(ghost["bare"]["ga"]["ghosts"])
    labels = [r["label"] for r in rows]
    vals = [math.log10(max(r["energy_ratio"] * r["reach_fraction"], 1e-6)) for r in rows]
    figs.save_plot("ghost_pairs", [("像面に届くエネルギー比(log10)", list(range(len(rows))), vals)],
                   xlabel="面の組(%s)" % " / ".join("%d=%s" % (i, l) for i, l in enumerate(labels)),
                   ylabel="log10(ゴースト / 像)", kinds=["bar"], colors=["emphasis"], ylim=(-6.0, 0.0),
                   xlim=(-0.6, len(rows) - 0.4),
                   title="同軸落射の検査レンズの 2 回反射のゴースト(%d 組のうち像面に届く %d 組)" % (n_all, len(rows)),
                   caption="全ての 2 面の組(N(N−1)/2 = %d)のうち、像面に光が届く組の、像に対するエネルギー比(届く割合を掛けた値)。"
                           "半透鏡の前面/裏面の組は 2.6 %% と大きいうえ、像面の近くに集まる(半径 0.3 mm)ので偽の欠陥になる。"
                           "ほかの組は像面で数 mm〜数百 mm に広がり、一様な明るさの上乗せになる。" % n_all,
                   size=(900, 380))


def main():
    t0 = time.process_time()
    print("PoC 非共軸の光学系(予算 %s)" % ("reduced" if REDUCED else "full"))
    chapter_coaxial()
    drawings = chapter_fold()
    rows = chapter_plate()
    sch = chapter_scheimpflug()
    ghost = chapter_ghost()
    chapter_second()
    chapter_probes()
    make_figures(drawings, rows, sch, ghost)
    print("\n所要 %.1f s(CPU)、門 %d 件中 NG %d 件" % (time.process_time() - t0, len(GATES), len(FAILS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
