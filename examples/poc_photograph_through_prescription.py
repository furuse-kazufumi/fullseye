# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 処方どおりのレンズ越しに 3 次元の場面を撮る ―― 被写界深度・猫の目のボケ・隅の光量・色収差・ゴーストを、レンズの設計データだけから。

【問い】レンズ設計の画面は、スポットダイアグラムや MTF の数字までは出してくれる。では「この処方で 1 m 先の資料を撮ると、絵は実際どう写るのか」は?
同じ EFL・同じ F ナンバーの三枚玉が 2 本あって、片方は半径を 7〜10 % の 1.5 倍ずらしてある。数字(RMS スポット)の差は、解像チャート・傷・ボケ・隅の光量・
ゴーストの絵ではどう見えるのか。新 op 8 本(`lensrender`、`opsoptics` の `lensrender`)に切り出し、センサ側から射出瞳を標本化して処方の全面を**逆向きに**追跡し
(Kolb, Mitchell & Hanrahan 1995)、物体空間の場面で陰影をつけ、光子・ショットノイズ・読み出しノイズ・量子化まで通す。8 章:

  1. **検算**: 逆向きの追跡は `ray_bundle` の逆(入射点 8.7e-15 mm、方向 4.2e-16)。理想レンズ越しの白い面の放射照度は π L sin²α に相対 2e-6(電子数)、点光源は画素 1 つに入り
     光子数が I Ω t QE λ/hc に 1e-6(5,524 電子、50 回の撮り直しの平均 5,521.9)。市松の刃 15 本は `lensimage.distortion_map` に 0.096 px(歪みは外縁で 5.2 px)、
     0.7 視野の刃の F 線と C 線の差 1.08 px は `chromatic_shift` の 1.00 px に 0.081 px。
  2. **同じ焦点距離の三枚玉 2 本**で解像チャート(市松・傾いた刃・シーメンススター)を 1 m で撮り、品質の表を作る。RMS スポット(0 / 7.7° / 11°)は良い方 10.7 / 10.4 / 13.4 µm、
     ずらした方 53.4 / 35.9 / 24.6 µm(軸上で 5.0 倍)。絵から測った刃の 10–90 % は 4.6 px と 15.4 px、MTF50 は 0.116 と 0.053 cyc/px。順は `spot_stats` の順と一致する。
  3. **被写界深度と猫の目**: 理想レンズの 0.5 m の点光源のボケは薄肉レンズの錯乱円に 0.31 %、F/8 は F/2.8 の 0.349 倍(2.8/8 = 0.350)。三枚玉は 0.45 倍(球面収差で F/2.8 の円が小さく
     出る。閉形式とのずれとして出す)。理想レンズの 20 mm 後ろの丸い遮光板では像が点なので、猫の目の面積比は 2 つの円の重なりの閉形式 0.635 に、凸包 0.625・描いた絵 0.639・瞳の通過率 0.636
     が 1.6 % 以内で一致し、子午面に 3.6e-15 mm で対称。三枚玉の隅(F/2.8、0.7 m)は遮光筒で瞳の 10 % が削られるが、像面湾曲でボケの円そのものが 1.3 倍になるので面積比は通過率と一致しない(そう書く)。
  4. **隅の光量と歪みの格子**: 白い面の相対照度は `lensimage` に 0.7 視野(7.7°)まで 1.61 %、8.7° では 3.20 % 離れる(`lensimage` は物体側の cos⁴、描画は像側の cos⁴)。絞りを前に置いた単玉の格子は
     隅で −6.6 % の樽型で、理想の格子の点(赤)から内側へ 6.6 px。
  5. **隅の強い光源のゴースト**: 面ごとの反射率 4 % と 0.5 % で、2 回反射の 15 本を重ねる。エネルギー比は閉形式 r² (1−r)^(2(j−i)−2) に 4.4e-16、センサに入るゴーストの光量は
     エネルギー比 × 届く割合に 0.00 %、重心は `raytrace3d.ghost_analysis` に 8e-4 px。反射率 0 では重ねが厳密に 0。4 % のゴーストの総量は点の像の 0.38 %(0.5 % の 59 倍。r² の比は 64 倍で、残りは透過)。
  6. **傷**: 同じチャートの 0.2 mm の傷(センサ上で 10.4 µm = 2.6 画素)の対比は、良い方 0.547・ずらした方 0.261(48 %)。前向きに追跡したスポットを線に畳み込んだ独立の予測は 0.542 と 0.261。
  7. **限界**: 幾何光学だけで回折が無い。良い方の点像は F/6.25(収差が支配)で EE 83.8 % の半径が Airy の 2.7 倍だが、F/11 に絞ると 0.32 倍 ―― 実物より鋭く描いている。
  8. **壊して確かめる**: 屈折率の向きを逆にする(逆向きの門が 1.1 mm で赤)、絞りの半径を 10 % 違える(電子数が 19 % 動く)、合焦を 1.5 m にずらす(刃が 4.6 → 17.6 px)、
     射出瞳が無限遠の系・系でない入力・負の波長・範囲の外の照明の表は拒否。

【外部真値】閉形式(π L sin²α、I Ω t QE λ/hc、薄肉レンズの錯乱円、2 つの円の重なり、円盤ぼけの刃の応答)、既存の op(`ray_bundle`・`distortion_map`・`chromatic_shift`・
`spot_stats`・`ghost_analysis`・`edgesfr`)、独立の前向き追跡。手法: Kolb, Mitchell & Hanrahan, SIGGRAPH 1995。【学習】0。【較正】0。

★正直な限界: 幾何光学のみ ―― 回折が無いので、絞った良いレンズの点像は Airy より小さく描かれる。射出瞳は近軸の位置と大きさで標本化するので、瞳収差で実際の瞳が外へはみ出すレンズは
その分の光を取りこぼす。ゴーストは 2 回反射だけで、コーティングの角度依存・ガラス内の吸収・鏡筒の散乱(フレア)は無い。点光源は前向きの追跡で重ねるので、遮られず影も作らない。
図の絵のざらつきは瞳の標本化の確率誤差(瞳 32〜48 点)で、センサのノイズではない。
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import edgesfr  # noqa: E402
import examplefig as figs  # noqa: E402
import lensimage as LI  # noqa: E402
import lensrender as LR  # noqa: E402
import raytrace as RT  # noqa: E402
import raytrace3d as R3  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"
FAILS: list[str] = []
GATES: list[str] = []
NUMBERS: dict[str, float] = {}
INF = float("inf")

#: 古典的な三枚玉の半径と間隔(公開のサンプル、MIT)。EFL 50 mm、絞りは前玉。ずらした方は半径を 7〜10 % 変える
RS = [22.01359, -435.76044, -22.21328, 20.29192, 79.6836, -18.39533]
TS = [3.25896, 6.00755, 0.99997, 4.75041, 2.95208, None]
NS = [(1.62041, 60.32), 1.0, (1.62004, 36.37), 1.0, (1.62041, 60.32), 1.0]      # モデル硝材 (n_d, V_d)。銘柄は使わない
MULT = [1.08, 0.90, 0.93, 1.10, 0.92, 1.07]
SCENE_Z = -1000.0                                                                  # 資料までの距離 [mm]
FIELD_MAX_MM = 194.0                                                                # 表の「1 視野」= 1 m で物体の高さ 194 mm(半画角 11°)
D = {"type": "directional", "to_light": (0.0, 0.0, 1.0), "irradiance_W_m2_nm": 1.0}

#: 予算: 画素のピッチ [µm]、センサの大きさ、瞳の標本数。同じ視野(0.96 × 0.64 mm)を、CI では粗い画素で撮る
if REDUCED:
    PITCH, SIZE, NPUP, OVS = 8.0, (80, 120), 16, 1
else:
    PITCH, SIZE, NPUP, OVS = 4.0, (160, 240), 32, 1


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


def triplet(stop_ap=4.0, rear=6.0, object_mm=SCENE_Z * -1.0, radii=None, scale=1.0, aim="stop"):
    """EFL 50 mm の三枚玉(絞りは前玉)。*scale* は全長を一様に拡大・縮小する(ずらした方の EFL を合わせるのに使う)。"""
    r = RS if radii is None else radii
    surf = [{"R": r[i] * scale, "t": None if TS[i] is None else TS[i] * scale, "n": NS[i],
             "ap": (stop_ap if i == 0 else rear) * scale} for i in range(6)]
    return RT.lens_system(surf, stop=0, aim=aim, object_mm=object_mm)


def chart_texture(texel=0.01, scratch=False):
    """解像チャート(24 × 16 mm): 市松 1 mm、傾いた刃 2 本(5°)、シーメンススター。scratch が "clean" / "scratch" なら下の刃を明るい帯に(後者は 0.2 mm の傷つき)。(行 0 が上)"""
    wmm, hmm = 24.0, 16.0
    nu, nv = int(round(wmm / texel)), int(round(hmm / texel))
    u = (np.arange(nu) + 0.5) * texel - wmm / 2
    v = hmm / 2 - (np.arange(nv) + 0.5) * texel
    U, V = np.meshgrid(u, v)
    tex = np.full(U.shape, 0.5)
    m = (U >= -10) & (U < -4) & (V >= -3) & (V < 3)                                  # 市松
    tex = np.where(m, 0.1 + 0.8 * ((np.floor(U + 10) + np.floor(V + 3)) % 2), tex)
    a = math.radians(5.0)
    m = (np.abs(U) <= 2.5) & (V >= 2.0) & (V <= 6.5)                                 # 傾いた刃(上)
    tex = np.where(m, np.where(U * math.cos(a) + (V - 4.25) * math.sin(a) > 0, 0.9, 0.1), tex)
    if scratch in ("clean", "scratch"):
        m = (np.abs(U) <= 3.0) & (V >= -6.5) & (V <= -2.5)                           # 明るい帯(と、"scratch" ならその上の縦の傷、幅 0.2 mm)
        tex = np.where(m, np.where((np.abs(U) <= 0.1) & (scratch == "scratch"), 0.1, 0.9), tex)
    else:
        m = (np.abs(U) <= 2.5) & (V >= -6.5) & (V <= -2.0)                           # 傾いた刃(下、90° 回して 5° 傾ける)
        tex = np.where(m, np.where(V * math.cos(a) - U * math.sin(a) + 4.25 * math.cos(a) > 0, 0.1, 0.9), tex)
    r = np.hypot(U - 7.0, V)
    th = np.arctan2(V, U - 7.0)
    m = r <= 3.5                                                                     # スター(24 本)
    tex = np.where(m, 0.1 + 0.8 * (np.sin(24 * th) > 0), tex)
    return tex, (wmm, hmm)


def chart_scene(scratch=False, z=SCENE_Z):
    tex, size = chart_texture(0.01, scratch)
    return LR.lens_scene([{"type": "plane", "z_mm": z, "size_mm": size, "albedo": tex}], [D])


def sensor_dict(pitch=None, size=None, **kw):
    d = {"pixel_pitch_um": PITCH if pitch is None else pitch, "size": SIZE if size is None else size}
    d.update(kw)
    return d


def px_per_mm_object(system, pitch=None):
    """物体面の 1 mm が画素いくつに写るか(|m| / ピッチ)。"""
    return abs(RT.paraxial_trace(system)["magnification"]) / ((PITCH if pitch is None else pitch) * 1e-3)


def chart_roi(system, v_lo=2.5, v_hi=5.8, u_half=2.0):
    """上の傾いた刃を囲む画素の ROI (y0, y1, x0, x1)。"""
    s = px_per_mm_object(system)
    h, w = SIZE
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    return int(math.ceil(cy - v_hi * s)), int(math.floor(cy - v_lo * s)), int(math.ceil(cx - u_half * s)), int(math.floor(cx + u_half * s))


#: 刃の測定用の窓の画素 [µm]。予算に関わらず細かくする(窓は 57 × 57 画素しかなく安い。ずらした玉の刃は 15 px 幅にぼけるので、粗い画素では測れない)
PITCH_EDGE = 4.0
NPUP_EDGE = 64                                                                     # 窓の瞳の標本数(窓は安いので、傾きの推定が確率誤差に負けない数にする)


def edge_window(system, half_mm=1.9):
    """傾いた刃(上)だけを写す小さな窓のセンサ設定と ROI: 窓の中心を刃の中心に置く(センサの一部だけを撮る)。"""
    s = px_per_mm_object(system, PITCH_EDGE)
    m = RT.paraxial_trace(system)["magnification"]
    n = 2 * int(math.ceil(2.1 * s)) + 1
    c = (n - 1) / 2.0
    roi = (int(math.ceil(c - half_mm * s)), int(math.floor(c + half_mm * s)), int(math.ceil(c - half_mm * s)), int(math.floor(c + half_mm * s)))
    return {"pixel_pitch_um": PITCH_EDGE, "size": (n, n), "center_mm": (0.0, m * 4.25)}, roi


def _edges(row, level=None):
    lo, hi = row.min(), row.max()
    mid = 0.5 * (lo + hi) if level is None else level
    k = np.nonzero((row[:-1] - mid) * (row[1:] - mid) < 0)[0]
    return k + (mid - row[k]) / (row[k + 1] - row[k])


def detuned_pair(k=1.5, rear=6.0, object_mm=-SCENE_Z):
    """良い三枚玉と、同じ EFL・同じ F ナンバーで半径を MULT の k 倍ずらした三枚玉。"""
    good = triplet(4.0, rear, object_mm)
    ft = RT.paraxial_trace(good)["fno"]
    radii = [RS[i] * (1.0 + k * (MULT[i] - 1.0)) for i in range(6)]
    efl = RT.paraxial_trace(triplet(4.0, rear, INF, radii))["efl"]
    scale = RT.paraxial_trace(good)["efl"] / efl
    ap = 4.0
    for _ in range(8):
        bad = triplet(ap, rear, object_mm, radii, scale=scale)
        ap *= RT.paraxial_trace(bad)["fno"] / ft
    return good, bad


def to_rgb(res, gamma=2.2, scale=None):
    """3 つの帯(F, d, C 線 = 青・緑・赤)の画像を、そのまま RGB の 3 チャネルとして並べる(センサの電子数、露出は固定)。"""
    e = res["electrons_per_wavelength"]
    rgb = np.stack([e[2], e[1], e[0]], -1)
    s = scale if scale is not None else np.percentile(rgb, 99.5)
    return np.clip(rgb / s, 0.0, 1.0) ** (1.0 / gamma)


def disc_diameter_px(e, level=0.5):
    """点光源の像(背景 0)の、プラトーの 50 % より明るい画素の面積から求めた円の直径 [px]。"""
    plate = np.median(e[e > 0.5 * e.max()])
    return 2.0 * math.sqrt(float((e > level * plate).sum()) / math.pi)


# --------------------------------------------------------------------------- #
# 1. 検算                                                                       #
# --------------------------------------------------------------------------- #
def chapter_checks():
    print("\n1. 検算(逆向きの追跡・閉形式・既存の op)")
    # (a) ray_bundle の逆
    s = triplet(object_mm=INF)
    geo = LR._geometry(s, s["wavelength_um"])
    wp, wd, n = 0.0, 0.0, 0
    for fld in (0.0, 7.0, 12.0):
        b = RT.ray_bundle(s, field=fld, rings=5)
        v = b["valid"]
        pts, dirs = b["points"][v], b["dirs"][v]
        img, dl = pts[:, -1, :], dirs[:, -1, :]
        pp = img + ((geo["z_xp"] - img[:, 2]) / dl[:, 2])[:, None] * dl
        Dv = pp - img
        Dv /= np.linalg.norm(Dv, axis=1, keepdims=True)
        o, d, tr, ok, tir = LR._trace_back(s, geo, img, Dv)
        wp = max(wp, float(np.abs(o - pts[:, 1, :]).max()))
        wd = max(wd, float(np.abs(d + dirs[:, 0, :]).max()))
        n += int(v.sum())
    gate("逆向きの追跡は ray_bundle の逆: 入射点 1e-9 mm、方向 1e-12(3 視野 %d 本)" % n, wp < 1e-9 and wd < 1e-12 and n > 200,
         "%.1e mm、%.1e" % (wp, wd))
    NUMBERS.update({"reverse_point_mm": wp, "reverse_dir": wd})
    # (b) 理想レンズ越しの白い面と点光源の光子数
    f, d_, ap = 50.0, 1000.0, 5.0
    ideal = RT.lens_system([{"f": f, "t": None, "ap": ap}], stop=0, object_mm=d_)
    sp = RT.paraxial_trace(ideal)["image_mm"]
    wl, t_exp, qe = 0.588, 1e-4, 0.55
    sens = {"size": (5, 5), "pixel_pitch_um": 10.0, "qe": qe, "full_well": 65535.0, "read_noise_e": 0.0, "bits": 16}
    white = LR.lens_scene([{"type": "plane", "z_mm": -d_, "albedo": 0.5}], [D])
    r = LR.render_scene_through_lens(ideal, white, sens, pupil_samples=256, wavelengths=[wl], exposure_s=t_exp, add_noise=False, band_nm=100.0)
    E_closed = math.pi * (0.5 / math.pi) * ap ** 2 / (ap ** 2 + sp ** 2)
    e_closed = E_closed * 100.0 * (10e-6) ** 2 * t_exp * (wl * 1e-6 / (6.62607015e-34 * 299792458.0)) * qe
    err_e = abs(r["electrons_mean"][2, 2] / e_closed - 1.0)
    gate("理想レンズ越しの白い面の放射照度は π L sin²α(閉形式)に 1e-3、画素の電子数は E dλ A t (λ/hc) QE に 1e-3",
         abs(r["irradiance_W_m2_nm"][0][2, 2] / E_closed - 1.0) < 1e-3 and err_e < 1e-3, "電子数 %.1e" % err_e)
    I0 = 1.2e-8
    srcs = LR.lens_scene([], [], sources=[{"position_mm": (0.0, 0.0, -d_), "intensity_W_sr_nm": I0}])
    ideal3 = RT.lens_system([{"f": f, "t": None, "ap": 3.0}], stop=0, object_mm=d_)
    rp = LR.render_scene_through_lens(ideal3, srcs, dict(sens, size=(9, 9), pixel_pitch_um=8.0), wavelengths=[wl], exposure_s=1e-3,
                                      add_noise=False, band_nm=10.0)
    omega = 2.0 * math.pi * (1.0 - d_ / math.hypot(d_, 3.0))
    ep = I0 * omega * 10.0 * 1e-3 * (wl * 1e-6 / (6.62607015e-34 * 299792458.0)) * qe
    e = rp["electrons_mean"]
    reps = np.array([LR.render_scene_through_lens(ideal3, srcs, dict(sens, size=(9, 9), pixel_pitch_um=8.0), wavelengths=[wl], exposure_s=1e-3,
                                                  seed=k, band_nm=10.0)["image"][4, 4] for k in range(50)]) * 65535.0
    gate("理想レンズ(絞り小)の点光源は画素 1 つに入り、光子数は I Ω t QE λ/hc に 1e-6、50 回の撮り直しの平均は 3σ 以内",
         e[4, 4] / e.sum() > 1 - 1e-9 and abs(e[4, 4] / ep - 1) < 1e-6 and abs(reps.mean() - ep) < 3 * math.sqrt(ep / 50) + 0.5,
         "%.0f 電子、撮り直しの平均 %.1f" % (ep, reps.mean()))
    NUMBERS["point_photons_rel_err"] = abs(e[4, 4] / ep - 1)
    # (c) 市松の刃の位置 = distortion_map
    sd = RT.lens_system([{"R": INF, "t": 12.0, "n": 1.0, "ap": 1.2}, {"R": 28.0, "t": 3.5, "n": (1.5168, 64.17), "ap": 15.0},
                         {"R": -120.0, "t": None, "n": 1.0, "ap": 15.0}], stop=0, object_mm=1000.0)
    para = RT.paraxial_trace(sd)
    pitch, W = 12.0, 1201
    dm = LI.distortion_map(sd, (3, W), pitch, fields=np.linspace(0.0, 160.0, 9))
    n, sq = 32, 20.0
    tex = np.tile(np.kron([[0.1, 0.9], [0.9, 0.1]], np.ones((20, 20))), (n // 2, n // 2))
    sc = LR.lens_scene([{"type": "plane", "point_mm": (0.0, 10.0, -1000.0), "size_mm": (n * sq, n * sq), "albedo": tex}], [D])
    rr = LR.render_scene_through_lens(sd, sc, {"size": (3, W), "pixel_pitch_um": pitch}, pupil_samples=48, wavelengths=[0.588], add_noise=False, oversample=2)
    cols = _edges(rr["electrons_mean"][1])
    cx = (W - 1) / 2
    xs = cols - cx
    pred, idl = [], []
    for x in np.arange(-n / 2 * sq, n / 2 * sq + 1, sq):
        ri = abs(para["magnification"] * x)
        rd = ri + sum(c * ri ** p for c, p in zip(dm["coefficients"], dm["powers"]))
        pred.append(math.copysign(rd, x) / (pitch * 1e-3))
        idl.append(math.copysign(ri, x) / (pitch * 1e-3))
    pred, idl = np.array(pred), np.array(idl)
    keep = np.abs(pred) < cx - 2
    pred, idl = pred[keep], idl[keep]
    dist_err = float(np.abs(xs - pred).max())
    gate("市松の刃(15 本、物体の高さ 60〜140 mm の 3 つの視野を含む)の位置が distortion_map の予測に 0.3 px 以内(歪みは外縁で %.1f px)" % np.abs(pred - idl).max(),
         len(xs) == len(pred) == 15 and dist_err < 0.3 and np.abs(pred - idl).max() > 4.0, "%.3f px" % dist_err)
    NUMBERS["distortion_edge_px"] = dist_err
    # (d) 横色収差
    sl = RT.lens_system([{"R": INF, "t": 20.0, "n": 1.0, "ap": 1.0}, {"R": 28.0, "t": 3.5, "n": (1.5168, 64.17), "ap": 15.0},
                         {"R": -120.0, "t": None, "n": 1.0, "ap": 15.0}], stop=0, object_mm=1000.0)
    m = RT.paraxial_trace(sl)["magnification"]
    Y = 2.1 / abs(m)
    cs = RT.chromatic_shift(sl, field=Y)
    pitch2, Hh = 15.0, 401
    t2 = np.zeros((400, 400))
    t2[:200, :] = 0.9
    t2[200:, :] = 0.1
    sc2 = LR.lens_scene([{"type": "plane", "point_mm": (0.0, Y, -1000.0), "size_mm": (200.0, 200.0), "albedo": t2}], [D])
    r2 = LR.render_scene_through_lens(sl, sc2, {"size": (Hh, 3), "pixel_pitch_um": pitch2}, pupil_samples=64, add_noise=False, oversample=2)
    e2 = r2["electrons_per_wavelength"][:, :, 1]
    cy = (Hh - 1) / 2
    ys = []
    for j in range(3):
        c_ = _edges(e2[j])
        ys.append((c_[np.argmin(np.abs(c_ - (cy - 2.1 / (pitch2 * 1e-3))))] - cy) * pitch2 * 1e-3)
    shift_px = (ys[0] - ys[2]) / (pitch2 * 1e-3)
    ref_px = cs["lateral_color"] / (pitch2 * 1e-3)
    gate("0.7 視野の刃の F 線と C 線の位置の差(%.2f px)が chromatic_shift の横色収差(%.2f px)に 0.3 px 以内" % (shift_px, ref_px),
         abs(ref_px) > 0.8 and abs(shift_px - ref_px) < 0.3, "差 %.3f px" % abs(shift_px - ref_px))
    NUMBERS["lateral_colour_px_err"] = abs(shift_px - ref_px)


# --------------------------------------------------------------------------- #
# 2. 解像チャート                                                                #
# --------------------------------------------------------------------------- #
def chapter_chart():
    print("\n2. 同じ焦点距離の三枚玉 2 本で、解像チャートを 1 m で撮る")
    good, bad = detuned_pair()
    pg, pb = RT.paraxial_trace(good), RT.paraxial_trace(bad)
    print("   EFL %.4f / %.4f mm、F ナンバー %.3f / %.3f" % (pg["efl"], pb["efl"], pg["fno"], pb["fno"]))
    gate("2 本の EFL は 1e-6 mm 以内で一致し、F ナンバーは 1e-3 以内", abs(pg["efl"] - pb["efl"]) < 1e-6 and abs(pg["fno"] - pb["fno"]) < 1e-3,
         "ΔEFL %.1e mm、ΔF %.1e" % (abs(pg["efl"] - pb["efl"]), abs(pg["fno"] - pb["fno"])))
    sc = chart_scene()
    sens, roi = edge_window(good)                                                  # 表の刃の測定は、刃の周りの窓だけを撮った絵で(全体の絵は図の所で撮る)
    out = LR.render_compare_prescriptions([good, bad], sc, sens, labels=["良い三枚玉", "ずらした三枚玉"], edge_roi=roi, field_max=FIELD_MAX_MM,
                                          pupil_samples=NPUP_EDGE, add_noise=True, focus_mm=-SCENE_Z, seed=1, exposure_s=1e-4)
    t = out["table"]
    for r in t:
        print("   %s: RMS スポット(0 / 0.7 / 1 視野 = 物体の高さ 0 / %.0f / %.0f mm)%s µm、隅の光量 %.3f、歪み %.4f %%、横色収差 %.3f µm、刃の 10–90 %% %.2f px、MTF50 %.3f cyc/px" % (
            r["label"], 0.7 * FIELD_MAX_MM, FIELD_MAX_MM, " ".join("%.1f" % v for v in r["rms_spot_um"]), r["relative_illumination_corner"], r["distortion_pct"],
            r["lateral_color_um"], r["edge_width_10_90_px"], r["edge_mtf50_cyc_px"]))
    spots = [RT.spot_stats(s, field=0.0, rings=6)["rms_radius"] for s in (good, bad)]
    order_tab = np.argsort([r["rms_spot_um"][0] for r in t]).tolist()
    gate("品質の表の RMS スポットの順(軸上・0.7・1 視野の 3 つとも)は raytrace.spot_stats の順に一致し、ずらした方が %.1f 倍大きい" % (t[1]["rms_spot_um"][0] / t[0]["rms_spot_um"][0]),
         order_tab == np.argsort(spots).tolist() == [0, 1] and all(t[0]["rms_spot_um"][i] < t[1]["rms_spot_um"][i] for i in range(3))
         and all(abs(r["rms_spot_um"][0] - 1000.0 * sp_) < 1e-9 for r, sp_ in zip(t, spots)))
    gate("絵から測った刃の 10–90 % の立ち上がりも MTF50 も、表のスポットの順と同じ向き(良い方が鋭い)",
         t[0]["edge_width_10_90_px"] < t[1]["edge_width_10_90_px"] and t[0]["edge_mtf50_cyc_px"] > t[1]["edge_mtf50_cyc_px"],
         "%.2f < %.2f px、MTF50 %.3f > %.3f" % (t[0]["edge_width_10_90_px"], t[1]["edge_width_10_90_px"], t[0]["edge_mtf50_cyc_px"], t[1]["edge_mtf50_cyc_px"]))
    NUMBERS.update({"edge_width_good_px": t[0]["edge_width_10_90_px"], "edge_width_bad_px": t[1]["edge_width_10_90_px"],
                    "rms_ratio": t[1]["rms_spot_um"][0] / t[0]["rms_spot_um"][0]})
    return good, bad, out


# --------------------------------------------------------------------------- #
# 3. 被写界深度と玉ねぎボケ・猫の目                                                #
# --------------------------------------------------------------------------- #
def dof_lens(N, rear=9.0, hood=9.6):
    """EFL 50 mm の三枚玉を F/N に絞る(絞りは最初のガラス面)。その 15 mm 前に半径 *hood* の遮光筒の縁があり、隅の斜めの光束を削る。1 m に合焦(距離は遮光筒から測る)。"""
    surf = [{"R": INF, "t": 15.0, "n": 1.0, "ap": hood}]
    surf += [{"R": RS[i], "t": TS[i], "n": NS[i], "ap": (50.0 / (2.0 * N) if i == 0 else rear)} for i in range(6)]
    return RT.lens_system(surf, stop=1, aim="stop", object_mm=-SCENE_Z)


def dof_scene():
    ys, xs = np.mgrid[0:200, 0:300]
    back = 0.15 + 0.6 * (((ys // 20) + (xs // 20)) % 2)
    mat = {"specular": 0.3, "shininess": 40.0}
    objs = [{"type": "plane", "z_mm": -4000.0, "size_mm": (1500.0, 1000.0), "albedo": back, "name": "backdrop"},
            dict({"type": "sphere", "center_mm": (-30.0, -5.0, -500.0), "radius_mm": 8.0, "albedo": (0.85, 0.3, 0.2)}, **mat),
            dict({"type": "sphere", "center_mm": (0.0, 0.0, -1000.0), "radius_mm": 15.0, "albedo": (0.3, 0.75, 0.3)}, **mat),
            dict({"type": "sphere", "center_mm": (90.0, 5.0, -2000.0), "radius_mm": 25.0, "albedo": (0.25, 0.35, 0.85)}, **mat)]
    srcs = [{"position_mm": (35.0, 22.0, -520.0), "intensity_W_sr_nm": 4e-5, "name": "near"},
            {"position_mm": (-120.0, -15.0, -2400.0), "intensity_W_sr_nm": 6e-4, "name": "far"},
            {"position_mm": (70.0, 45.0, -700.0), "intensity_W_sr_nm": 1e-4, "name": "corner"}]
    return LR.lens_scene(objs, [dict(D, to_light=(0.3, 0.4, 1.0), irradiance_W_m2_nm=3.0)], sources=srcs, ambient=0.3)


def thin_lens_coc_mm(f, N, d_focus, d_obj):
    """薄肉レンズの錯乱円の直径 c = f² |d_o − d_f| / (N (d_f − f) d_o)(閉形式)。"""
    return f * f * abs(d_obj - d_focus) / (N * (d_focus - f) * d_obj)


def disc_overlap(r1, r2, dist):
    """半径 r1・r2 の 2 つの円(中心間 dist)の重なりの面積(閉形式)。"""
    if dist >= r1 + r2:
        return 0.0
    if dist <= abs(r1 - r2):
        return math.pi * min(r1, r2) ** 2
    a = r1 * r1 * math.acos((dist * dist + r1 * r1 - r2 * r2) / (2 * dist * r1))
    b = r2 * r2 * math.acos((dist * dist + r2 * r2 - r1 * r1) / (2 * dist * r2))
    c = 0.5 * math.sqrt((-dist + r1 + r2) * (dist + r1 - r2) * (dist - r1 + r2) * (dist + r1 + r2))
    return a + b - c


def chapter_dof():
    print("\n3. 被写界深度と、画面の隅の猫の目")
    pitch = 20.0
    sens = {"size": (161, 161), "pixel_pitch_um": pitch}
    src = LR.lens_scene([], [], sources=[{"position_mm": (0.0, 0.0, -500.0), "intensity_W_sr_nm": 1e-5}])
    # (a) 理想レンズ(収差ゼロ): ボケの円は薄肉レンズの錯乱円
    worst, diam = 0.0, {}
    for N in (2.8, 8.0):
        s = RT.lens_system([{"f": 50.0, "t": None, "ap": 50.0 / (2.0 * N)}], stop=0, object_mm=-SCENE_Z)
        r = LR.render_scene_through_lens(s, src, sens, pupil_samples=1, wavelengths=[0.588], add_noise=False, focus_mm=-SCENE_Z, source_rings=40)
        dia = disc_diameter_px(r["electrons_mean"]) * pitch * 1e-3
        coc = thin_lens_coc_mm(50.0, N, 1000.0, 500.0)
        diam[N] = dia
        worst = max(worst, abs(dia / coc - 1.0))
        print("   理想レンズ F/%.1f: 0.5 m の点光源のボケの円の直径 %.4f mm(薄肉レンズの錯乱円 %.4f mm)" % (N, dia, coc))
    gate("理想レンズの 0.5 m の点光源のボケの円の直径は、薄肉レンズの錯乱円 f² |Δd| / (N (d_f − f) d_o) に 3 % 以内(F/2.8 と F/8)", worst < 0.03, "%.2f %%" % (100 * worst))
    ratio = diam[8.0] / diam[2.8]
    gate("F/8 のボケの円は F/2.8 の 2.8/8 = 0.35 倍(3 % 以内)", abs(ratio / 0.35 - 1.0) < 0.03, "%.3f" % ratio)
    NUMBERS.update({"coc_rel_err": worst, "bokeh_f8_over_f28": ratio})
    # (b) 三枚玉の同じ量: 球面収差と絞りの位置で、閉形式からずれる(ずれを出す)
    tri = {}
    for N in (2.8, 8.0):
        s = dof_lens(N)
        r = LR.render_scene_through_lens(s, src, sens, pupil_samples=1, wavelengths=[0.588], add_noise=False, focus_mm=-SCENE_Z, source_rings=40)
        tri[N] = disc_diameter_px(r["electrons_mean"]) * pitch * 1e-3
    print("   三枚玉: F/2.8 で %.3f mm、F/8 で %.3f mm(比 %.2f。理想なら 0.35 ―― 球面収差が F/2.8 の円の縁を作る)" % (tri[2.8], tri[8.0], tri[8.0] / tri[2.8]))
    gate("三枚玉でも絞ればボケは小さくなる(F/8 の円は F/2.8 の 0.25〜0.6 倍)", 0.25 < tri[8.0] / tri[2.8] < 0.6, "%.2f" % (tri[8.0] / tri[2.8]))
    # (c) 猫の目: 理想レンズの 20 mm 後ろの丸い遮光板 ―― 像は点(収差ゼロ)なので、ボケの形は 2 つの円の重なりの閉形式
    f, a1, a2, tb, d = 50.0, 5.0, 5.0, 20.0, 1000.0
    sb = RT.lens_system([{"f": f, "t": tb, "ap": a1}, {"R": INF, "t": None, "n": 1.0, "ap": a2}], stop=0, object_mm=d)
    spi = f * d / (d - f)
    k = tb / spi
    pup = LR.exit_pupil_samples(sb, 1500, "hexapolar")
    rows = []
    for H in (100.0, 200.0):
        closed = disc_overlap(a1, a2 / (1 - k), k * H * spi / d / (1 - k)) / (math.pi * a1 ** 2)
        bk = LR.bokeh_shape(sb, (0.0, H), 2.0, 1200)
        cr = RT.chief_ray(sb, H)
        tr = LR.trace_sensor_rays(sb, [[cr["image_x"], cr["image_y"]]], pup["xy_mm"])
        g2 = float(np.sum(pup["weights_mm2"] * (~tr["vignetted"][0])) / pup["area_mm2"])
        areas = []
        for hh in (0.0, H):
            cc = tuple(LR.bokeh_shape(sb, (0.0, hh), 2.0, 800)["centroid_xy_mm"])
            sc_ = LR.lens_scene([], [], sources=[{"position_mm": (0.0, hh, -d), "intensity_W_sr_nm": 1e-3}])
            rr = LR.render_scene_through_lens(sb, sc_, {"size": (161, 161), "pixel_pitch_um": 5.0, "center_mm": cc}, pupil_samples=1, wavelengths=[0.588],
                                              add_noise=False, defocus_mm=2.0, source_rings=60)
            e = rr["electrons_mean"]
            areas.append(float((e > 0.5 * np.percentile(e[e > 0], 90)).sum()))
        rows.append((H, closed, bk["area_ratio"], g2, areas[1] / areas[0], bk["symmetry_error_mm"]))
        print("   猫の目(物体の高さ %.0f mm、2 mm のピントはずれ): 面積比 閉形式 %.3f、凸包 %.3f、瞳の通過率 %.3f、描いた絵 %.3f、対称性の誤差 %.1e mm" % rows[-1])
    gate("猫の目と軸上の円の面積比(凸包・描いた絵)は 2 つの円の重なりの閉形式に 5 % 以内、瞳の通過率(口径食の係数)にも 5 % 以内(2 つの高さ)",
         all(abs(r_[2] / r_[1] - 1) < 0.05 and abs(r_[4] / r_[1] - 1) < 0.05 and abs(r_[3] / r_[1] - 1) < 0.01 for r_ in rows) and rows[1][1] < 0.7,
         "最大 %.1f %%" % (100 * max(max(abs(r_[2] / r_[1] - 1), abs(r_[4] / r_[1] - 1)) for r_ in rows)))
    gate("猫の目は子午面について対称(1e-9 mm)", max(r_[5] for r_ in rows) < 1e-9, "%.1e mm" % max(r_[5] for r_ in rows))
    NUMBERS.update({"cats_eye_hull_vs_closed": rows[1][2] / rows[1][1] - 1, "cats_eye_render_vs_closed": rows[1][4] / rows[1][1] - 1})
    # (d) 三枚玉の隅の点光源(F/2.8、0.7 m): 図に出す形(ここは閉形式が無い。像面湾曲で円盤の大きさも変わるので、面積比は通過率とは一致しない)
    s28 = dof_lens(2.8)
    bt = LR.bokeh_shape(s28, (70.0, 45.0), 0.0, 1200, object_mm=700.0)
    b0 = LR.bokeh_shape(s28, (0.0, 0.0), 0.0, 1200, object_mm=700.0)
    print("   三枚玉 F/2.8 の隅の点光源(0.7 m): 軸上との面積比 %.2f、瞳の通過率 %.2f(像面湾曲・非点収差で円盤そのものも大きくなるので両者は一致しない)" % (
        bt["area_ratio"], bt["vignetting_factor"]))
    gate("三枚玉の隅の点光源は口径食(遮光筒)で瞳が削られ(通過率 %.2f < 0.95)、ボケの形が円から外れる(凸包の面積 / 同じ面積の円 = %.3f)" % (
        bt["vignetting_factor"], bt["area_mm2"] / (math.pi * (np.sqrt(bt["area_mm2"] / math.pi)) ** 2)), bt["vignetting_factor"] < 0.95 and bt["symmetry_error_mm"] < 1e-9)
    # 場面全体(F/2.8 と F/8、露出は F ナンバーの 2 乗に比例させて明るさを揃える)
    scene = dof_scene()
    imgs = {}
    npup = 12 if REDUCED else 40
    size = (48, 72) if REDUCED else (120, 180)
    ptc = 160.0 if REDUCED else 64.0
    for N in (2.8, 8.0):
        imgs[N] = LR.render_scene_through_lens(dof_lens(N), scene, {"size": size, "pixel_pitch_um": ptc}, pupil_samples=npup, focus_mm=-SCENE_Z,
                                               exposure_s=2.5e-6 * (N / 2.8) ** 2, seed=2)
    return {"images": imgs, "bokeh_tri": bt, "bokeh_tri_axis": b0, "ideal": rows, "pitch": pitch, "baffled": sb}


# --------------------------------------------------------------------------- #
# 4. 隅の光量と歪みの格子                                                         #
# --------------------------------------------------------------------------- #
def chapter_corner():
    print("\n4. 隅の光量と歪みの格子")
    s = triplet(rear=6.0, object_mm=INF)
    para = RT.paraxial_trace(s)
    pitch, W = 24.0, 801
    white = LR.lens_scene([{"type": "plane", "z_mm": -20000.0, "albedo": 0.5}], [D])
    r = LR.render_scene_through_lens(s, white, {"size": (3, W), "pixel_pitch_um": pitch}, pupil_samples=120 if REDUCED else 200, wavelengths=[0.588],
                                     add_noise=False, pupil_pattern="hexapolar")
    E = r["irradiance_W_m2_nm"][0][1]
    cx = (W - 1) / 2
    fr, rend, lens_i, c4, flds = [], [], [], [], []
    for frac in np.linspace(0.0, 0.9, 10):
        col = int(round(cx + frac * cx))
        fld = LI._field_for_radius(para, (col - cx) * pitch * 1e-3, True) if col > cx else 0.0
        ri = LI._relative_illumination(s, para, [0.0, fld], True, rings=12)[-1] if col > cx else 1.0
        fr.append(frac)
        flds.append(fld)
        rend.append(E[col] / E[int(cx)])
        lens_i.append(ri)
        c4.append(math.cos(math.radians(fld)) ** 4)
    rend, lens_i, c4, flds = map(np.array, (rend, lens_i, c4, flds))
    d07 = np.abs(rend / lens_i - 1.0)[np.array(fr) <= 0.71]
    d09 = abs(rend[-2] / lens_i[-2] - 1.0)
    print("   白い面の相対照度: 0.7 視野(%.1f°)までの lensimage との差の最大 %.2f %%、0.8 視野(%.1f°)で %.2f %%" % (
        flds[np.array(fr) <= 0.71][-1], 100 * d07.max(), flds[-2], 100 * d09))
    gate("白い面の相対照度は lensimage(traced)に 0.7 視野まで 2 %% 以内(%.2f %%)、それより外では物体側の cos⁴ と像側の cos⁴ の差で最大 %.1f %% 離れる" % (100 * d07.max(), 100 * d09),
         d07.max() < 0.02 and 0.01 < d09 < 0.06)
    NUMBERS.update({"ri_vs_lensimage_07": float(d07.max()), "ri_vs_lensimage_08": float(d09)})
    # 歪みの格子(絞りを前に置いた単玉: 樽型)
    sd = RT.lens_system([{"R": INF, "t": 35.0, "n": 1.0, "ap": 1.2}, {"R": 28.0, "t": 3.5, "n": (1.5168, 64.17), "ap": 15.0},
                         {"R": -120.0, "t": None, "n": 1.0, "ap": 15.0}], stop=0, object_mm=1000.0)
    pd_ = RT.paraxial_trace(sd)
    size_g = (84, 126) if REDUCED else (112, 168)
    pg = 140.0 if REDUCED else 100.0
    n_t, ext = 1200, 600.0
    tx = np.full((n_t, n_t), 0.85)
    g = (np.arange(n_t) + 0.5) * ext / n_t - ext / 2
    on = (np.abs((g + 15.0) % 30.0 - 15.0) < 1.5)
    tx = np.where(on[None, :] | on[:, None], 0.1, tx)
    sc = LR.lens_scene([{"type": "plane", "z_mm": -1000.0, "size_mm": (ext, ext), "albedo": tx}], [D])
    rg = LR.render_scene_through_lens(sd, sc, {"size": size_g, "pixel_pitch_um": pg}, pupil_samples=12 if REDUCED else 24, wavelengths=[0.588], add_noise=False, exposure_s=1e-4,
                                      oversample=1 if REDUCED else 2)
    dm = LI.distortion_map(sd, size_g, pg, fields=np.linspace(0.0, 190.0, 9))
    h, w = size_g
    cy_, cx_ = (h - 1) / 2, (w - 1) / 2
    grid_img = rg["electrons_mean"] / rg["electrons_mean"].max()
    rgb = np.stack([grid_img] * 3, -1)
    corner = None
    for gx in range(-8, 9):
        for gy in range(-8, 9):
            X, Y = 30.0 * gx, 30.0 * gy
            ri = math.hypot(X, Y) * abs(pd_["magnification"])
            col = cx_ + X * abs(pd_["magnification"]) / (pg * 1e-3)
            row = cy_ - Y * abs(pd_["magnification"]) / (pg * 1e-3)
            if 1 <= row < h - 1 and 1 <= col < w - 1:
                rgb[int(round(row)) - 1:int(round(row)) + 2, int(round(col)) - 1:int(round(col)) + 2] = [1.0, 0.1, 0.1]
                corner = (X, Y, ri)
    print("   絞りを前に置いた単玉の格子: 隅の歪み %.2f %%(distortion_map)、理想の格子の点(赤)から %.1f px 内側" % (
        dm["max_distortion_pct"], abs(dm["max_distortion_pct"]) / 100 * math.hypot(cx_, cy_)))
    return {"E": rend, "lens": lens_i, "c4": c4, "fields": flds, "frac": np.array(fr), "grid_rgb": rgb, "dist_pct": dm["max_distortion_pct"], "corner": corner}


# --------------------------------------------------------------------------- #
# 5. ゴースト                                                                    #
# --------------------------------------------------------------------------- #
def chapter_ghost():
    print("\n5. 隅の強い光源のゴースト")
    s = triplet(rear=6.0, object_mm=-SCENE_Z)
    light = (-133.0, -95.0)
    size = (70, 100) if REDUCED else (140, 200)
    pg = 240.0 if REDUCED else 120.0
    sens = {"size": size, "pixel_pitch_um": pg}
    common = dict(light_xy_mm=light, distance_mm=-SCENE_Z, sensor=sens, wavelengths=[0.588], focus_mm=-SCENE_Z, rings=10 if REDUCED else 14, max_ghosts=15)
    out = {}
    for r_ in (0.0, 0.04, 0.005):
        out[r_] = LR.render_ghost_overlay(s, reflectance=r_, intensity_W_sr_nm=3e-7, exposure_s=1e-3, **common)
    z = out[0.0]
    gate("反射率 0 のゴーストの重ねは、すべて厳密に 0", float(np.abs(z["overlay_electrons"]).max()) == 0.0 and z["ghosts"] == [] and z["image_electrons"].sum() > 0)
    g = out[0.04]
    worst = 0.0
    for row in g["ghosts"]:
        closed = 0.04 ** 2 * (1 - 0.04) ** (2 * (row["j"] - row["i"]) - 2)
        worst = max(worst, abs(row["energy_ratio"] / closed - 1.0))
    gate("反射率 4 %% のゴースト %d 本のエネルギー比は閉形式 r² (1−r)^(2(j−i)−2) に 1e-9(面の対 (i, j))" % len(g["ghosts"]), len(g["ghosts"]) >= 12 and worst < 1e-9, "%.1e" % worst)
    # エネルギー: 全部がセンサに入る大きな窓で、スプレッドした光量が energy_ratio × 届いた割合に 5 %
    big = LR.render_ghost_overlay(s, light_xy_mm=light, distance_mm=-SCENE_Z, sensor={"size": (600, 600), "pixel_pitch_um": 150.0}, wavelengths=[0.588],
                                  focus_mm=-SCENE_Z, rings=10, max_ghosts=15, reflectance=0.04)
    fit = [r for r in big["ghosts"] if math.hypot(r["centroid_px"][0] - 299.5, r["centroid_px"][1] - 299.5) + 3 * r["radius_px"] < 0.95 * 300]
    e_err = max(abs(r["spread_power_ratio"] / r["power_ratio"] - 1.0) for r in fit)
    gate("センサに全部入るゴースト %d 本の光量は、エネルギー比 × 届く割合(r² × 透過)に 5 %% 以内" % len(fit), len(fit) >= 3 and e_err < 0.05, "%.2f %%" % (100 * e_err))
    # 位置: raytrace3d.ghost_analysis の重心
    s3 = R3.noncoaxial_system(RT.with_wavelength(s, 0.588))
    ga = R3.ghost_analysis(s3, coatings={"R": 0.04}, field=light, rings=common["rings"])
    cy_, cx_ = (size[0] - 1) / 2.0, (size[1] - 1) / 2.0
    pos_err = 0.0
    for r in g["ghosts"]:
        ref = [x for x in ga["ghosts"] if x["i"] == r["i"] and x["j"] == r["j"]][0]["centroid_xy"]
        pos_err = max(pos_err, abs(r["centroid_px"][0] - (cy_ + ref[1] / (pg * 1e-3))), abs(r["centroid_px"][1] - (cx_ - ref[0] / (pg * 1e-3))))
    gate("ゴーストの重心の位置は raytrace3d.ghost_analysis の重心と 0.5 px 以内(%d 本)" % len(g["ghosts"]), pos_err < 0.5, "%.1e px" % pos_err)
    tot = {r_: float(out[r_]["overlay_electrons"].sum()) for r_ in out}
    ratio_img = {r_: tot[r_] / float(out[r_]["image_electrons"].sum()) for r_ in out}
    print("   画面内のゴースト光量 / 点の像: r = 4 %% で %.2e、0.5 %% で %.2e(r² の比 %.0f 倍、エネルギーの比 %.0f 倍)" % (
        ratio_img[0.04], ratio_img[0.005], (0.04 / 0.005) ** 2, ratio_img[0.04] / ratio_img[0.005]))
    NUMBERS.update({"ghost_energy_closed_err": worst, "ghost_spread_err": e_err, "ghost_pos_px": pos_err})
    return out


# --------------------------------------------------------------------------- #
# 6. 傷                                                                         #
# --------------------------------------------------------------------------- #
def predicted_line_profile(system, wavelengths, line_mm, bg, fg, pitch_um, xc_px, nrings=40):
    """前向きに追跡した軸上のスポットを、明るい帯の中の暗い線(幅 line_mm)に畳み込んだ画素中心の値(独立の予測)。3 つの帯を電子数の重みで足す。"""
    m = abs(RT.paraxial_trace(system)["magnification"])
    img = RT.paraxial_trace(system)["image_mm"]
    p = pitch_um * 1e-3
    bw = LR._band_widths(list(wavelengths), None, "x")
    acc = np.zeros(len(xc_px))
    wsum = 0.0
    for wl, bnd in zip(wavelengths, bw):
        sw = RT.with_wavelength(system, wl)
        b = RT.ray_bundle(sw, field=0.0, rings=nrings, kind="hexapolar", image_mm=img)
        v = b["valid"]
        xs = b["image_xy"][v, 0]
        w = LR._ring_weights(b["pupil"], nrings)[v]
        w = w / w.sum()
        half = 0.5 * line_mm * m
        wt = bnd * wl
        for k, xc in enumerate(xc_px):
            xm = xc * p - xs
            acc[k] += wt * float(np.sum(w * np.where(np.abs(xm) <= half, fg, bg)))
        wsum += wt
    return acc / wsum


def chapter_scratch(good, bad):
    print("\n6. 0.2 mm の傷は、ずらした三枚玉の絵でまだ見えるか")
    npup = 64 if REDUCED else 128
    res = {}
    for nm, s in (("良い", good), ("ずらした", bad)):
        m = RT.paraxial_trace(s)["magnification"]
        sp = px_per_mm_object(s)
        sens = {"pixel_pitch_um": PITCH, "size": (25, 61), "center_mm": (0.0, m * -4.5)}       # 傷の帯(v = −4.5 mm)の周りだけを写す窓
        ims = {}
        for tag in ("clean", "scratch"):
            ims[tag] = LR.render_scene_through_lens(s, chart_scene(scratch=tag), sens, pupil_samples=npup, add_noise=False, focus_mm=-SCENE_Z)
        eC, eS = ims["clean"]["electrons_mean"], ims["scratch"]["electrons_mean"]
        segC = eC.mean(axis=0)[30 - 8:30 + 9]
        segS = eS.mean(axis=0)[30 - 8:30 + 9]
        contrast = float(np.max((segC - segS) / segC))
        xc = np.arange(-8, 9)
        wls = list(LR.WL_BANDS)
        predS = predicted_line_profile(s, wls, 0.2, 0.9, 0.1, PITCH, xc)
        predC = predicted_line_profile(s, wls, 0.2, 0.9, 0.9, PITCH, xc)
        pred_contrast = float(np.max((predC - predS) / predC))
        res[nm] = {"contrast": contrast, "pred": pred_contrast, "clean": ims["clean"], "scratch": ims["scratch"], "seg": (segC, segS), "line_px": 0.2 * sp}
        print("   %s: 傷(幅 %.1f px)の対比 %.3f(前向きのスポットとの畳み込みの予測 %.3f)" % (nm, 0.2 * sp, contrast, pred_contrast))
    gate("傷の対比は、前向きに追跡したスポットと線の畳み込み(独立の予測)に 8 %% 以内(良い %.3f / %.3f、ずらした %.3f / %.3f)" % (
        res["良い"]["contrast"], res["良い"]["pred"], res["ずらした"]["contrast"], res["ずらした"]["pred"]),
         all(abs(res[k]["contrast"] / res[k]["pred"] - 1.0) < 0.08 for k in res))
    gate("ずらした三枚玉では傷の対比が良い方の %.0f %% に落ちる(%.2f → %.2f)" % (100 * res["ずらした"]["contrast"] / res["良い"]["contrast"], res["良い"]["contrast"], res["ずらした"]["contrast"]),
         res["ずらした"]["contrast"] < 0.6 * res["良い"]["contrast"] and res["良い"]["contrast"] > 0.3)
    NUMBERS.update({"scratch_contrast_good": res["良い"]["contrast"], "scratch_contrast_bad": res["ずらした"]["contrast"]})
    return res


# --------------------------------------------------------------------------- #
# 7. 限界(回折は無い)                                                            #
# --------------------------------------------------------------------------- #
def airy_ee(r_um, wl_um, fno):
    from scipy.special import j0, j1
    x = np.pi * np.maximum(r_um, 1e-9) / (wl_um * fno)
    return 1.0 - j0(x) ** 2 - j1(x) ** 2


def chapter_limit():
    print("\n7. 限界: 幾何光学だけで回折が無い")
    out = {}
    for N in (6.25, 11.0):
        s = triplet(stop_ap=50.0 / (2 * N), rear=6.0, object_mm=INF)
        b = RT.ray_bundle(s, field=0.0, rings=60)
        v = b["valid"]
        xy = b["image_xy"][v]
        w = LR._ring_weights(b["pupil"], 60)[v]
        w = w / w.sum()
        c = (xy * w[:, None]).sum(0)
        r = np.hypot(*(xy - c).T) * 1000.0
        o = np.argsort(r)
        cum = np.cumsum(w[o])
        fn = RT.paraxial_trace(s)["fno"]
        r838 = float(np.interp(0.838, cum, r[o]))
        airy = 1.22 * RT.WL_D * fn
        out[N] = {"r": r[o], "cum": cum, "fno": fn, "geo": r838, "airy": airy}
        print("   F/%.1f: 幾何光学の EE 83.8 %% の半径 %.2f µm、Airy 円盤の半径 %.2f µm(比 %.2f)" % (N, r838, airy, r838 / airy))
    gate("F/6.25(収差が支配): 描かれる点像は Airy より大きい(%.1f 倍)ので、幾何光学の絵が実物に近い" % (out[6.25]["geo"] / out[6.25]["airy"]), out[6.25]["geo"] > 2.0 * out[6.25]["airy"])
    gate("F/11(回折が支配): 描かれる点像は Airy 円盤の %.0f %% しかない ―― 実物より鋭く描いている(限界)" % (100 * out[11.0]["geo"] / out[11.0]["airy"]), out[11.0]["geo"] < 0.5 * out[11.0]["airy"])
    NUMBERS.update({"geo_over_airy_f625": out[6.25]["geo"] / out[6.25]["airy"], "geo_over_airy_f11": out[11.0]["geo"] / out[11.0]["airy"]})
    return out


def chapter_probes():
    print("\n8. 壊して確かめる(門が赤になること)")
    s = triplet(object_mm=INF)
    geo = LR._geometry(s, s["wavelength_um"])
    bad = dict(geo)
    bad["na"], bad["nb"] = geo["nb"], geo["na"]                        # 屈折率の向きを逆にする
    b = RT.ray_bundle(s, field=7.0, rings=4)
    v = b["valid"]
    pts, dirs = b["points"][v], b["dirs"][v]
    img, dl = pts[:, -1, :], dirs[:, -1, :]
    pp = img + ((geo["z_xp"] - img[:, 2]) / dl[:, 2])[:, None] * dl
    Dv = pp - img
    Dv /= np.linalg.norm(Dv, axis=1, keepdims=True)
    o, d, tr, ok, tir = LR._trace_back(s, bad, img, Dv)
    err = float(np.nanmax(np.abs(o[ok] - pts[ok, 1, :]))) if ok.any() else INF
    gate("屈折率の向きを逆にすると、逆向きの追跡の門(1e-9 mm)は %.1e mm で赤になる" % err, err > 1e-3)
    ideal = RT.lens_system([{"f": 50.0, "t": None, "ap": 5.0}], stop=0, object_mm=1000.0)
    white = LR.lens_scene([{"type": "plane", "z_mm": -1000.0, "albedo": 0.5}], [D])
    full = LR.render_scene_through_lens(ideal, white, {"size": (3, 3), "pixel_pitch_um": 10.0}, pupil_samples=64, add_noise=False)["electrons_mean"][1, 1]
    half = LR.render_scene_through_lens(RT.lens_system([{"f": 50.0, "t": None, "ap": 4.5}], stop=0, object_mm=1000.0), white, {"size": (3, 3), "pixel_pitch_um": 10.0},
                                        pupil_samples=64, add_noise=False)["electrons_mean"][1, 1]
    gate("絞りの半径を 10 %% 違えると、電子数が %.0f %% 変わる(閉形式の門 1e-3 が赤になる)" % (100 * abs(half / full - 1.0)), abs(half / full - 1.0) > 0.15)
    g0, b0 = detuned_pair()
    sw, roi = edge_window(g0)
    sc = chart_scene()
    r_good = LR.render_scene_through_lens(g0, sc, sw, pupil_samples=NPUP_EDGE, add_noise=False, focus_mm=-SCENE_Z)
    r_off = LR.render_scene_through_lens(g0, sc, sw, pupil_samples=NPUP_EDGE, add_noise=False, focus_mm=1500.0)
    w_good = LR._edge_metrics(r_good["image_noiseless"], roi, "probe")[0]
    w_off = LR._edge_metrics(r_off["image_noiseless"], roi, "probe")[0]
    gate("合焦の距離を 1 m から 1.5 m にずらすと、刃の立ち上がりが %.2f → %.2f px に太る(焦点の門が赤になる)" % (w_good, w_off), w_off > 1.3 * w_good)
    for name, fn_ in (("射出瞳が無限遠の系", lambda: LR.exit_pupil_samples(RT.lens_system([{"R": INF, "t": 50.0, "n": 1.0, "ap": 2.0}, {"f": 50.0, "t": None, "ap": 20.0}], stop=0), 8)),
                      ("系でない入力", lambda: LR.render_scene_through_lens({"x": 1})),
                      ("負の波長", lambda: LR.trace_sensor_rays(g0, wavelength_um=-1.0)),
                      ("範囲の外の照明の表", lambda: LR.render_scene_through_lens(g0, None, {"size": (4, 4)}, pupil_samples=2, illuminant=np.array([[500.0, 1.0], [510.0, 1.0]])))):
        try:
            fn_()
            gate("拒否: %s" % name, False)
        except ValueError:
            gate("拒否: %s は ValueError" % name, True)


# --------------------------------------------------------------------------- #
# 図                                                                            #
# --------------------------------------------------------------------------- #
def make_figures(chart, dof, corner, ghost, scratch, limit):
    good, bad, out = chart
    t = out["table"]
    npd = 48                                                                         # 図は瞳 48 点で撮り直す(絵のざらつきは瞳の標本化の確率誤差)
    sg = LR.render_scene_through_lens(good, chart_scene(), sensor_dict(), pupil_samples=npd, focus_mm=-SCENE_Z, seed=1, exposure_s=1e-4)
    sb_ = LR.render_scene_through_lens(bad, chart_scene(), sensor_dict(), pupil_samples=npd, focus_mm=-SCENE_Z, seed=1, exposure_s=1e-4)
    scale = float(np.percentile(np.stack([sg["electrons_per_wavelength"], sb_["electrons_per_wavelength"]]), 99.5))
    figs.save_grid("chart_good_vs_detuned", [to_rgb(sg, scale=scale), to_rgb(sb_, scale=scale)],
                   captions=["良い三枚玉(F/%.2f、EFL %.2f mm)" % (t[0]["fno"], t[0]["efl_mm"]), "半径をずらした三枚玉(同じ EFL・同じ F ナンバー)"], ncols=2,
                   title="同じ解像チャートを 1 m で撮る(処方どおりのレンズ越し、露出・ガンマ固定、青・緑・赤の 3 帯をそのまま RGB に)",
                   caption="左は市松 1 mm・傾いた刃 2 本・シーメンススター(24 本)が読める。右は RMS スポットが %.1f 倍(軸上 %.0f → %.0f µm)で、市松のコントラストは落ち、"
                           "スターは中心から先にぼけ、刃の縁に色が付く。1 画素 %.0f µm、ショットノイズ・読み出しノイズ・12 bit の量子化つき。" % (
                               t[1]["rms_spot_um"][0] / t[0]["rms_spot_um"][0], t[0]["rms_spot_um"][0], t[1]["rms_spot_um"][0], PITCH))
    good_rgb, bad_rgb = to_rgb(sg, scale=scale), to_rgb(sb_, scale=scale)
    frames = []
    for u in np.linspace(0.0, 1.0, 32):
        frames.append(figs.video_frame((1.0 - u) * good_rgb + u * bad_rgb,
                                      "処方ずれ %.0f %%" % (100 * u), size=(960, 540)))
    assert len(frames) >= 24
    assert np.ptp(np.stack(frames).astype(np.int16), axis=0).max() > 0
    figs.save_video("prescription_detune_morph", frames,
                    caption="同じチャートを良好な処方からずらした処方へ連続的に比較する。",
                    fps=10.0, gif_every=2, gif_fps=5.0, gif_width=480)
    rows = []
    for r in t:
        rows.append([r["label"], "%.2f / %.2f" % (r["efl_mm"], r["fno"]), " / ".join("%.1f" % v for v in r["rms_spot_um"]), "%.3f" % r["relative_illumination_corner"],
                     "%.3f" % r["distortion_pct"], "%.2f" % r["lateral_color_um"], "%.2f" % r["edge_width_10_90_px"], "%.3f" % r["edge_mtf50_cyc_px"]])
    figs.save_table("quality_table", ["処方", "EFL mm / F", "RMS スポット µm(0 / 0.7 / 1 視野 = 0 / 7.7° / 11°)", "11° の光量", "11° の歪み %", "0.7 視野の横色収差 µm", "刃 10–90 % px", "MTF50 cyc/px"], rows,
                    title="同じ場面を撮った 2 本の処方の品質の表", caption="RMS スポットは raytrace.spot_stats、光量は lensimage、刃は edgesfr で同じ絵から測った。")
    im = dof["images"]
    sc2 = float(np.percentile(im[2.8]["electrons_per_wavelength"], 99.0))
    figs.save_grid("depth_of_field", [to_rgb(im[2.8], scale=sc2), to_rgb(im[8.0], scale=sc2)], captions=["F/2.8", "F/8(露出は F ナンバーの 2 乗に比例)"], ncols=2,
                   title="0.5 / 1 / 2 m の 3 つの球(1 m に合焦)と、手前・奥・隅の点光源",
                   caption="F/2.8 では 1 m の緑の球だけが締まり、手前の赤い球と奥の青い球、市松の背景(4 m)はぼける。点光源は円盤になり、画面の隅(右上)のものは口径食で猫の目になる。"
                           "F/8 では被写界深度が深くなりボケは 0.35 倍。幾何光学なので円盤の縁は実物より鋭い。")
    bt = LR.bokeh_shape(dof_lens(2.8), (70.0, 45.0), 0.0, 5000, object_mm=700.0)
    pol_c = bt["polygon_xy_mm"]
    pol_a = LR.bokeh_shape(dof_lens(2.8), (0.0, 0.0), 0.0, 5000, object_mm=700.0)["polygon_xy_mm"]
    cl = lambda p: np.vstack([p, p[:1]]) * 1000.0                                   # noqa: E731
    figs.save_plot("cats_eye", [("軸上の点(円盤)", cl(pol_a)[:, 0], cl(pol_a)[:, 1]), ("画面の隅の点(猫の目)", cl(pol_c)[:, 0], cl(pol_c)[:, 1])],
                   xlabel="センサ上の x [µm]", ylabel="y [µm]", colors=["reference", "emphasis"], aspect="equal", size=(520, 480),
                   title="F/2.8 の 0.7 m の点光源のボケ(1 m に合焦): 軸上は円、隅は瞳の重なり",
                   caption="遮光筒が隅の斜めの光束を削り、瞳の通過率は %.0f %%(形は円から外れる)。面積は軸上の %.0f %% ―― 像面湾曲で円盤そのものが大きくなるので、通過率とは一致しない"
                           "(収差ゼロの理想レンズなら一致する: 門 2 つの円の重なり)。" % (
                       100 * dof["bokeh_tri"]["vignetting_factor"], 100 * dof["bokeh_tri"]["area_ratio"]))
    sb = dof["baffled"]
    bi0 = LR.bokeh_shape(sb, (0.0, 0.0), 2.0, 5000)
    bi1 = LR.bokeh_shape(sb, (0.0, 200.0), 2.0, 5000)
    figs.save_plot("cats_eye_ideal", [("軸上の点(円盤)", cl(bi0["polygon_xy_mm"])[:, 0], cl(bi0["polygon_xy_mm"])[:, 1]),
                                      ("物体の高さ 200 mm の点(猫の目)", cl(bi1["polygon_xy_mm"])[:, 0], cl(bi1["polygon_xy_mm"])[:, 1])],
                   xlabel="センサ上の x [µm]", ylabel="y [µm]", colors=["reference", "emphasis"], aspect="equal", size=(520, 480),
                   title="理想レンズの 20 mm 後ろの丸い遮光板: 2 mm ピントがずれた点光源のボケ",
                   caption="像は点(収差ゼロ)なので、ボケは瞳と遮光板の像の重なり ―― 2 つの円の重なりの閉形式 %.3f に、凸包の面積比 %.3f、瞳の通過率、描いた絵が 5 %% 以内で一致する。" % (
                       dof["ideal"][1][1], bi1["area_ratio"]))
    figs.save_plot("relative_illumination", [("描いた絵(逆向きの追跡)", corner["fields"], corner["E"]),
                                              ("lensimage の相対照度(物体側の cos⁴ × 通過率)", corner["fields"], corner["lens"]),
                                              ("cos⁴ だけ", corner["fields"], corner["c4"])],
                   xlabel="物体側の視野角 [度]", ylabel="相対照度(軸上 = 1)", colors=["emphasis", "reference", "wrong"], styles=[None, "dashed", "dotted"], size=(600, 380),
                   title="白い面の隅の光量(三枚玉、後ろの玉が視野の外側を削る)",
                   caption="0.7 視野(7.7°)までは lensimage と 2 %% 以内(最大 %.1f %%)。8.7° では %.1f %% 離れる ―― lensimage は物体側の角度の cos⁴ を使い、描画は像側の角度を使うため。" % (
                       100 * NUMBERS["ri_vs_lensimage_07"], 100 * NUMBERS["ri_vs_lensimage_08"]))
    figs.save("distortion_grid", np.kron(corner["grid_rgb"], np.ones((4, 4, 1))), "絞りを前に置いた単玉(樽型 %.1f %%)で撮った 30 mm 格子の絵。赤い点が歪みの無い理想の格子の交点。" % corner["dist_pct"])
    s_g = triplet(rear=6.0, object_mm=-SCENE_Z)                                       # 図は光線を増やして撮り直す(1 本のゴーストを細かい点で埋める)
    gh = {r_: LR.render_ghost_overlay(s_g, light_xy_mm=(-133.0, -95.0), distance_mm=-SCENE_Z, sensor={"size": (70, 100), "pixel_pitch_um": 240.0}, wavelengths=[0.588],
                                      focus_mm=-SCENE_Z, rings=60, max_ghosts=15, reflectance=r_, intensity_W_sr_nm=3e-7, exposure_s=1e-3) for r_ in (0.0, 0.04, 0.005)}
    g0, g4, g5 = gh[0.0], gh[0.04], gh[0.005]
    e0 = g0["image_electrons"]
    white = 1e-5 * float(e0.max())                                                   # 光源は場面の白の 1e5 倍明るいとして、白を 1e-5 × ピークに置く
    pan = [np.clip((e0 + gg["overlay_electrons"]) / white, 0.0, 1.0) ** (1.0 / 2.2) for gg in (g0, g4, g5)]
    figs.save_grid("ghost_overlay", pan, captions=["ゴーストなし(反射率 0)", "面ごとの反射率 4 %(無コート)", "0.5 %(コーティングあり)"], ncols=3, gray=True, vrange=(0.0, 1.0),
                   title="隅の強い光源 ―― 2 回反射のゴースト 15 本の重ね(光源のピークの 1e-5 を白に、ガンマ 2.2)",
                   caption="光源は場面の白の 1e5 倍明るいとして、ピークの 1e-5 を白にした表示。ゴーストは大きく薄い(焦点が遠い)ので、画素ごとの明るさはピークの 1e-7 程度でも、"
                           "全体では光源の 0.4 % になる。エネルギーは r² (1−r)^(2(j−i)−2) に従い、0.5 % では 4 % の 1/64。")
    seg = {k: v["seg"] for k, v in scratch.items()}
    x = np.arange(-8, 9) * PITCH
    ser = []
    for k, col in (("良い", "emphasis"), ("ずらした", "wrong")):
        ser.append(("%s: 描いた絵(傷の対比 %.2f)" % (k, scratch[k]["contrast"]), x, (seg[k][0] - seg[k][1]) / seg[k][0]))
    figs.save_plot("scratch_profile", ser, xlabel="センサ上の x [µm](傷の中心 = 0)", ylabel="傷による暗さ (清浄 − 傷) / 清浄", colors=["emphasis", "wrong"], size=(600, 380),
                   title="0.2 mm の傷(センサ上で %.1f µm = %.1f 画素)の断面" % (0.2 * abs(RT.paraxial_trace(good)["magnification"]) * 1000, scratch["良い"]["line_px"]),
                   caption="良い三枚玉では傷の中心の画素が %.0f %% 暗くなるが、ずらした方では %.0f %% しか暗くならず、周りの画素と区別がつきにくい。" % (
                       100 * scratch["良い"]["contrast"], 100 * scratch["ずらした"]["contrast"]))
    cr = lambda res: np.hstack([to_rgb(res["clean"]), to_rgb(res["scratch"])])      # noqa: E731
    up6 = lambda im_: np.kron(im_, np.ones((6, 6, 1)))                               # noqa: E731
    figs.save_grid("scratch_images", [up6(to_rgb(scratch["良い"]["scratch"], scale=scale)), up6(to_rgb(scratch["ずらした"]["scratch"], scale=scale))],
                   captions=["良い三枚玉", "ずらした三枚玉"], ncols=2, title="明るい帯の上の 0.2 mm の縦の傷(傷の周り 61 × 25 画素を拡大して並べた)",
                   caption="同じ露出。良い方は細い暗線が読め、ずらした方は線が薄れて周りのぼけに埋もれかけている。")
    s6, s11 = limit[6.25], limit[11.0]
    rg = np.linspace(0.0, 20.0, 201)
    geo = lambda s_: np.interp(rg, s_["r"], s_["cum"], left=0.0, right=1.0)           # noqa: E731
    ser = [("F/6.25 幾何光学(描かれる点像)", rg, geo(s6)), ("F/6.25 Airy(回折限界)", rg, airy_ee(rg, RT.WL_D, s6["fno"])),
           ("F/11 幾何光学(描かれる点像)", rg, geo(s11)), ("F/11 Airy(回折限界)", rg, airy_ee(rg, RT.WL_D, s11["fno"]))]
    figs.save_plot("geometric_vs_airy", ser, xlabel="点像の中心からの半径 [µm]", ylabel="囲まれたエネルギー", xlim=(0, 20), ylim=(0, 1.02),
                   colors=["emphasis", "reference", "wrong", "right"], styles=[None, "dashed", None, "dashed"], size=(640, 400),
                   title="限界: 幾何光学の点像は、絞ると Airy 円盤より小さくなる(回折が無い)",
                   caption="F/6.25 は収差が支配(EE 83.8 %% の半径は Airy の %.1f 倍)。F/11 は %.0f %% しかなく、実物より鋭く描いている。" % (
                       s6["geo"] / s6["airy"], 100 * s11["geo"] / s11["airy"]))


def main():
    t0 = time.time()
    c0 = time.process_time()
    print("PoC 処方どおりのレンズ越しに 3 次元の場面を撮る(予算 %s: 画素 %.0f µm、%d × %d、瞳 %d 点)" % ("reduced" if REDUCED else "full", PITCH, SIZE[0], SIZE[1], NPUP))
    chapter_checks()
    chart = chapter_chart()
    dof = chapter_dof()
    corner = chapter_corner()
    ghost = chapter_ghost()
    scratch = chapter_scratch(chart[0], chart[1])
    limit = chapter_limit()
    chapter_probes()
    if not REDUCED and figs.target_dir() is not None:
        make_figures(chart, dof, corner, ghost, scratch, limit)
    cpu = time.process_time() - c0
    print("\n所要 CPU %.1f s(壁時計 %.1f s)、門 %d 件中 NG %d 件" % (cpu, time.time() - t0, len(GATES), len(FAILS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
