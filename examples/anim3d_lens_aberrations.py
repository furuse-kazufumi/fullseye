# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""anim3d_lens_aberrations — レンズの収差を、実際に追った光線で見る(動く 3-D + Fullseye の処理の帯)。

    py -3.11 examples/anim3d_lens_aberrations.py                     # 検査だけ(コマを減らし、一時フォルダに書く。十数秒)
    py -3.11 examples/anim3d_lens_aberrations.py --out out/ab.html   # 開いて触れる HTML を残す(58 コマ、約 1 分、3 MB)
    py -3.11 examples/anim3d_lens_aberrations.py --out a.html --quick  # 残すが、コマは少なく
    # repo に置いてある完成品 docs/anim3d/poc_lens_aberrations.html は
    #   py -3.11 examples/anim3d_lens_aberrations.py --out docs/anim3d/poc_lens_aberrations.html で作り直す

【この例が示すこと】
教科書の収差の図は 1 枚の静止画だが、ここでは **1 つのつまみ(絞り・画角・波長)をゆっくり振り**、
光線とスポットと PSF が連続に変わる様子を 4 つのタブで見せる。光線はすべて fullseye の光線追跡の op
(``trace_rays`` ほか)が実際に追ったもの(手で描いた線ではない)。

* **球面収差**(絞りを開く): 平凸の単レンズ。周辺の光線ほど手前で軸を横切る(縦収差)。
* **コマ収差**(画角を振る): 軸上では無収差の非球面レンズ(デカルトの卵形)。斜めの光は彗星の形に。
  瞳の 1 つの輪は像面で「2 周する円」になる(色が 2 回巡る)。
* **非点収差と像面湾曲**(画角を振る): 絞りを前に出した単レンズ。メリディオナル(縦の面)と
  サジタル(横の面)の焦点が別々に手前へずれ、その軌跡が 2 本の曲がった像面になる。
* **色収差**(波長を振る): 単レンズは青ほど手前で焦点を結ぶ。BK7 と SF2 の貼り合わせ(アクロマート)は
  F 線と C 線の焦点がそろう。残り(二次スペクトル)も見せる。

Fullseye の処理の帯(タブごと 4 段、いま効いている段を光らせる):
  ① ``trace_rays`` → ``ray_fan``(横収差の扇。点 = 実光線、白い線 = 3 次(ザイデル)の式 = 門の値)。
     色収差のタブでは ``paraxial_trace``(焦点 vs 波長。白い線 = 厚肉レンズの閉形式)
  ② ``ray_bundle``(像面のスポット。点の色 = 瞳のどこを通ったか。3-D の拡大スポットと同じ色)
  ③ ``psf_field_grid``(瞳の波面から FFT で回折の PSF。②と同じ尺度の窓)
  ④ ``opd_samples`` / ``wavefront_from_opd``(瞳の波面 = OPD の地図と、ゼルニケ係数を種類別に
     —— ピント Z20・非点 Z22・コマ Z31・球面 Z40 の小さな色地図(共通の尺度)と大きさの棒)
帯の下の行に、その時刻の量を入れた式・実光線の値・差。

用語(最初に短く):
* **収差** = 1 点から出た光がレンズを通ったあと、1 点に集まらないずれ。
* **近軸(きんじく)** = 軸のすぐ近くを通る光だけを考える近似。教科書の結像の式(1/a + 1/b = 1/f)はこれ。
* **3 次の収差(ザイデルの 5 収差)** = 近軸の次の近似で出る、収差の大きさの式(``seidel_coefficients``)。
  W040(球面)・W131(コマ)・W222(非点)・W220(像面湾曲)。
* **横収差** = 像面で、光線が理想の点からどれだけ横にずれたか。式は ε = (1/(n′u′))·∂W/∂ρ
  (W = 瞳の波面のずれ、ρ = 瞳の中での位置 0..1、u′ = 近軸の周辺光線の傾き、収束で負)。

限界(正直に): 3 次の式は近軸の次の近似にすぎない。絞りを開く・画角を広げると、実光線との差が開く。
実光線 / 3 次の式 は、球面収差が f/4 で 1.046・f/2.5 で 1.129、コマが 10° で 1.059、メリディオナル(T)の
像面が 20° で 0.799(実光線の焦点は 2 本の近い光線の交点、主光線の上。3 次の式より像面に近い。9.7° で 5 % を越える)
(タブの中の段「限界: 3 次の式から N % 外れる」)。

**幾何光学の領域**: 瞳の波面が数十波長を越えると、``psf_field_grid`` は回折の PSF を作れない。瞳の格子は最大
512 点で、隣どうしの位相差が 0.5 波を越える(コマ 10° なら 1,746 点が要る)と、折り返しを避けるために op が
計算を断る。これは op の正しい振る舞いで、物理の上でもこの領域の PSF は光線の密度(スポット図)で決まる
(回折は Airy の芯ほどの幅しかぼかさない)。帯の③は、そのコマで「幾何の PSF」に切り替える。dense な ``ray_bundle``
(40 輪 4,921 本、輪ごとに瞳の面積で重みづけ)の像面の密度に、無収差の ``airy_pattern`` を畳み込んだもの。
③の左上に「geometric / PV N wv >> 1」と書く。回折の PSF も作れる重なりの領域(球面 f/3.6、コマ 4°、
PV 18〜60 波)で、両者の 50 %・80 % の集中半径が 12 % 以内で一致することを門にした。

出典(一般的な式): W. T. Welford, *Aberrations of Optical Systems* (1986) — ザイデル和と波面係数の
規格化、横収差と波面の関係。M. Born & E. Wolf, *Principles of Optics* — コマの円(瞳の輪が像で 2 周する)。
アクロマートの条件 φ1/V1 + φ2/V2 = 0。

検査(PASS の条件、``main`` の中):
* 球面: 実光線の横収差 / 3 次の式 が f/12 より暗い絞りで 1 % 以内、絞りとともに単調に開き、最後(f/2.5)で 8 % 超。
  ゼルニケの Z(4,0)×6 が W040 と f/8 より暗い絞りで 3 % 以内。
* コマ: メリディオナルのコマ(扇の偶の部分)が 3·W131/(n′u′) と 2° 以下で 1 % 以内。
  サジタルのコマがその 1/3(1° 以下で 2 % 以内)。軸上ではスポットが 1 µm 未満(非球面の無収差)。
* 非点: 2 本の近い光線の交点で求めた実光線の焦点(T・S)が、−2(W220+W222)/u′² と −2·W220/u′² と
  2° 以下で 1 % 以内。T−P = 3(S−P)(3 対 1 の規則)が 2 % 以内。
* 色: 単レンズの近軸の焦点が、厚肉レンズの閉形式 bfl = R1/(n(λ)−1) − t/n(λ) と 1e-9 mm で一致。
  F−C の焦点差が ザイデルの C_L/u′² と 1.5 % 以内。アクロマートの F−C の差 < 1e-6 mm、
  F..C の範囲の焦点のゆれが単レンズの 1/20 未満。
* 幾何の PSF: 回折の PSF と両方作れる所(球面 a = 14 mm、コマ 4°)で、エネルギーの 50 %・80 % が入る半径が 12 % 以内。
* HTML: 外部 URL が無い、帯の PNG が描いた画像と画素ごとに一致、物体の姿勢の復元が量子化の刻みの半分以内。
  光線の棒が op の点を結ぶ線分にちょうど重なること(はみ出さない・隙間が無い)は tests/ の門で確かめる。

EXTEND: 自分の処方(``fs.lens_system`` の表)を ``Aberration`` の関数に渡せば、同じ帯と 3-D が出る。
"""
from __future__ import annotations

import argparse
import colorsys
import json
import math
import os
import re
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fullseye as fs  # noqa: E402

pv = fs.pocviewer
INF = float("inf")
FPS = 15
T_FULL = 58                     # 約 4 秒(再生の速さは 0.25〜4 倍で変えられる)
T_QUICK = 10
WL_F, WL_D, WL_C = 0.4861327, 0.5875618, 0.6562725
RAY_W = 0.32                    # 3-D の光線の太さ [mm]
LIN = 22.0                      # 入射光線をレンズの手前どれだけから描くか [mm]
STAGE_PERIOD = 9                # 帯の段の強調が次へ移るコマ数(0.5 s)


def _t(ja: str, en: str) -> dict:
    return fs.viewer_text(ja, en)


def ease(u):
    return 0.5 - 0.5 * np.cos(np.pi * np.clip(u, 0.0, 1.0))


# =========================================================================== 処方
def singlet(ap=12.5, image_mm=None):
    """平凸の単レンズ(N-BK7、凸面を物体側、中心厚 9 mm、f ≈ 100 mm)。絞り = 第 1 面。"""
    return fs.lens_system([{"R": 51.68, "t": 9.0, "n": "N-BK7", "ap": ap}, {"R": INF, "t": None, "n": 1.0}],
                          stop=0, image_mm=image_mm)


def descartes(image_mm=None):
    """軸上で無収差の平凸非球面(``example_system("asphere")``: 平面を物体側、出口の円錐定数 k = −n²)。"""
    s = fs.example_system("asphere")
    if image_mm is None:
        return s
    return fs.lens_system([{k: v for k, v in q.items() if k not in ("solve", "dn")} for q in s["surfaces"]],
                          stop=0, image_mm=image_mm)


def stop_front(image_mm=None, d=20.0, a=4.0):
    """絞りを 20 mm 前に出した単レンズ(f/12.5)。非点収差と像面湾曲が主役になる。"""
    return fs.lens_system([{"R": INF, "t": d, "n": 1.0, "ap": a}, {"R": 51.68, "t": 9.0, "n": "N-BK7"},
                           {"R": INF, "t": None, "n": 1.0}], stop=0, image_mm=image_mm)


ACH_R1 = 48.84                  # 薄肉の解(φ1 = φV1/(V1−V2)、等凸)から


def achromat(R3, image_mm=None):
    """N-BK7(等凸)+ N-SF2 の貼り合わせ。R3 は F 線と C 線の焦点をそろえる値(``achromat_r3``)。"""
    return fs.lens_system([{"R": ACH_R1, "t": 6.0, "n": "N-BK7", "ap": 12.5}, {"R": -ACH_R1, "t": 2.5, "n": "N-SF2"},
                           {"R": R3, "t": None, "n": 1.0}], stop=0, image_mm=image_mm)


def bfl_at(system, wl):
    return fs.paraxial_trace(fs.with_wavelength(system, wl))["bfl"]


def fmt_fc(d_mm, lang="ja"):
    """F−C の焦点差の表示。二分法で詰めたアクロマートは浮動小数の丸めの所で 0 になるので、0 と書かず上限で書く。"""
    if abs(d_mm) < 1e-13:
        return ("< 1e-13 mm(二分法が浮動小数の精度まで詰めた)" if lang == "ja"
                else "< 1e-13 mm (bisection to floating-point precision)")
    return "%.1e mm" % d_mm


def achromat_r3():
    """F 線と C 線の近軸の焦点が一致する R3 を二分法で(``paraxial_trace`` の値だけを使う)。"""
    def g(r3):
        s = achromat(r3)
        return bfl_at(s, WL_F) - bfl_at(s, WL_C)
    lo, hi = -200.0, -600.0
    glo = g(lo)
    if np.sign(glo) == np.sign(g(hi)):
        raise ValueError("achromat_r3: 区間に解が無い")
    for _ in range(90):
        m = 0.5 * (lo + hi)
        if np.sign(g(m)) == np.sign(glo):
            lo = m
        else:
            hi = m
    return 0.5 * (lo + hi)


# =========================================================================== 光線を追う
def launch(field_deg, sx, sy, z_stop=0.0, lin=LIN):
    """無限遠の物体、画角 field_deg(y 方向)の平行光で、絞りの面 (z = z_stop) の点 (sx, sy) を通る光線。"""
    th = math.radians(field_deg)
    D = np.array([0.0, math.sin(th), math.cos(th)])
    P = np.column_stack([sx, sy, np.full(len(sx), z_stop)]) - lin * D
    return P, np.tile(D, (len(sx), 1))


def trace(system, field_deg, sx, sy, z_stop=0.0, wl=None):
    """fs.trace_rays の点の列 (N, 面の数 + 2, 3)。けられた光線があれば止める(作例の設計の誤り)。"""
    P, D = launch(field_deg, np.asarray(sx, float), np.asarray(sy, float), z_stop)
    tr = fs.trace_rays(system, P, D, wavelength_um=wl)
    if not tr["valid"].all():
        raise ValueError("光線がけられた(field %.2f°)" % field_deg)
    return tr


def crossing(P1, D1, P2, D2):
    """2 本の直線の最接近点の中点(近い 2 本の光線の焦点)。"""
    w = P1 - P2
    a, b, c = D1 @ D1, D1 @ D2, D2 @ D2
    d, e = D1 @ w, D2 @ w
    den = a * c - b * b
    s = (b * e - c * d) / den
    t = (a * e - b * d) / den
    return 0.5 * ((P1 + s * D1) + (P2 + t * D2))


def diff_foci(system, field_deg, a_stop, z_stop=0.0, eps=0.03):
    """瞳の中心の近くの 2 本ずつの光線(縦 ±eps・横 ±eps)の交点 = メリディオナル(T)とサジタル(S)の焦点。"""
    tr = trace(system, field_deg, [0, 0, -eps * a_stop, eps * a_stop], [-eps * a_stop, eps * a_stop, 0, 0], z_stop)
    P, D = tr["points"][:, -2, :], tr["dirs"][:, -1, :]
    return crossing(P[0], D[0], P[1], D[1]), crossing(P[2], D[2], P[3], D[3])


def pupil_rgb(px, py):
    """瞳の位置 → 色(方位 = 色相、中心から外へ = 鮮やかさ)。3-D の光線・スポット・扇で同じ色。"""
    px, py = np.atleast_1d(px), np.atleast_1d(py)
    out = np.zeros((len(px), 3))
    for i, (x, y) in enumerate(zip(px, py)):
        r = min(1.0, math.hypot(x, y))
        h = (math.atan2(y, x) / (2 * math.pi)) % 1.0
        out[i] = colorsys.hsv_to_rgb(h, 0.15 + 0.85 * r, 1.0)
    return out


def wl_rgb(wl_um):
    """波長 → 見た目の色(表示だけ。CIE の厳密な変換ではなく、よく使われる区分的な近似)。"""
    w = wl_um * 1000.0
    if w < 440:
        r, g, b = -(w - 440) / 60, 0.0, 1.0
    elif w < 490:
        r, g, b = 0.0, (w - 440) / 50, 1.0
    elif w < 510:
        r, g, b = 0.0, 1.0, -(w - 510) / 20
    elif w < 580:
        r, g, b = (w - 510) / 70, 1.0, 0.0
    elif w < 645:
        r, g, b = 1.0, -(w - 645) / 65, 0.0
    else:
        r, g, b = 1.0, 0.0, 0.0
    return np.clip(np.array([r, g, b]) * 0.85 + 0.15, 0, 1)


def fan_odd_slope(fan):
    """扇 (ρ, ε) の奇の部分を ρ + ρ³ + ρ⁵ で当てはめた 1 次の係数(焦点のずれ = −係数/u′)。"""
    q, v = fan[:, 0], fan[:, 1]
    od = 0.5 * (v - v[::-1])
    m = q > 0
    A = np.stack([q[m], q[m] ** 3, q[m] ** 5], 1)
    return float(np.linalg.lstsq(A, od[m], rcond=None)[0][0])


# =========================================================================== 波面・PSF
def zgroups(z):
    """ゼルニケ係数 {(n,m): 波長} → 種類別の大きさ(同じ種類の項の二乗和の根)。"""
    g = {"tilt": 0.0, "defocus": 0.0, "astig": 0.0, "coma": 0.0, "spherical": 0.0, "higher": 0.0}
    for (n, m), c in z.items():
        if n == 0:
            continue
        key = {(1, 1): "tilt", (2, 0): "defocus", (2, 2): "astig", (3, 1): "coma", (4, 0): "spherical"}.get((n, abs(m)),
                                                                                                         "higher")
        g[key] += c * c
    return {k: math.sqrt(v) for k, v in g.items()}


ZCOL = {"tilt": (0.55, 0.55, 0.55), "defocus": (0.45, 0.80, 0.45), "astig": (0.85, 0.45, 0.90),
        "coma": (0.35, 0.80, 0.95), "spherical": (1.0, 0.65, 0.25), "higher": (0.95, 0.35, 0.35)}


def psf_safe(system, field, wl=None):
    """``psf_field_grid`` の 1 視野。瞳の波面が標本化できない(収差が大きすぎる)ときは None(null)。"""
    try:
        g = fs.psf_field_grid(system, fields=(field,), wavelength_um=wl, oversample=3)
    except ValueError:
        return None
    return {"psf": g["psfs"][0], "dx": g["sample_um"][0], "strehl": g["strehl"][0]}


GEO_RINGS = 40                  # 幾何の PSF の光線(六角の輪 40 = 4,921 本)


def geo_rays(system, field, wl=None, image_mm=None):
    """幾何の PSF の材料: ``ray_bundle``(40 輪)の像面の点(主光線から、µm)と、その光線が代表する瞳の面積の重み。

    六角の輪 i(半径 i/40、6i 本)が受け持つのは半径 (i±0.5)/40 の輪帯(外側は瞳の縁 1 で切る)。
    重み = 輪帯の面積 / その輪の本数。一様に明るい瞳なら、像面の密度 = 光の強さ(幾何光学)。"""
    b = fs.ray_bundle(system, field=field, rings=GEO_RINGS, wavelength_um=wl, image_mm=image_mm)
    v = b["valid"]
    xy = (b["image_xy"][v] - b["chief_xy"]) * 1000.0
    ri = np.rint(np.hypot(b["pupil"][v, 0], b["pupil"][v, 1]) * GEO_RINGS).astype(int)
    lo = np.clip((ri - 0.5) / GEO_RINGS, 0.0, 1.0)
    hi = np.clip((ri + 0.5) / GEO_RINGS, 0.0, 1.0)
    w = (hi ** 2 - lo ** 2) / np.bincount(ri, minlength=GEO_RINGS + 1)[ri]
    para = fs.paraxial_trace(system if wl is None else fs.with_wavelength(system, wl))
    return {"xy": xy, "w": w, "fno": float(para["fno"]), "wl": WL_D if wl is None else float(wl)}


def geo_psf(g, rows, cols, pitch_um, cx_um=0.0):
    """幾何の PSF を rows×cols(画素 pitch_um、中心 = 主光線 + (cx_um, 0))の格子に: 光線の密度 ⊗ ``airy_pattern``。

    回折は Airy の芯の幅(1.22 λF#)だけぼかす。PSF の形を決めるのは光線の密度で、これは収差が波長より
    ずっと大きい所での近似(``tests`` で回折の PSF と照合)。和 = 1 に正規化。"""
    ex = (np.arange(cols + 1) - cols / 2) * pitch_um + cx_um
    ey = (np.arange(rows + 1) - rows / 2) * pitch_um
    H = np.histogram2d(g["xy"][:, 1], g["xy"][:, 0], bins=[ey, ex], weights=g["w"])[0][::-1]   # 行 = −y
    k = fs.airy_pattern(size=31, wavelength_um=g["wl"], f_number=g["fno"], pixel_pitch_um=pitch_um)
    k = k / k.sum()
    n0, n1 = rows + 31, cols + 31
    F = np.fft.irfft2(np.fft.rfft2(H, (n0, n1)) * np.fft.rfft2(k, (n0, n1)), (n0, n1))[15:15 + rows, 15:15 + cols]
    F = np.clip(F, 0.0, None)
    return F / max(F.sum(), 1e-300)


def wavefront(system, field, wl=None, size=40):
    """``opd_samples`` の地図(表示用)と ``wavefront_from_opd`` のゼルニケ係数。"""
    px, py, w, ok = fs.opd_samples(system, field=field, size=size, wavelength_um=wl)
    m = np.full(size * size, np.nan)
    m[ok] = w[ok] - np.mean(w[ok])
    st = fs.wavefront_from_opd(system, field=field, n_max=6, wavelength_um=wl)
    return m.reshape(size, size), st


# =========================================================================== 1 コマの記録
def spot_of(system, field, wl=None, image_mm=None, rings=5):
    b = fs.ray_bundle(system, field=field, rings=rings, wavelength_um=wl, image_mm=image_mm)
    v = b["valid"]
    return {"xy": (b["image_xy"][v] - b["chief_xy"]) * 1000.0, "pupil": b["pupil"][v], "chief": b["chief_xy"]}


def frame_common(system, field, wl=None):
    sp = spot_of(system, field, wl)
    psf = psf_safe(system, field, wl)
    geo = geo_rays(system, field, wl) if psf is None else None
    wmap, wst = wavefront(system, field, wl)
    st = fs.spot_stats(system, field=field, wavelength_um=wl)
    return {"spot": sp, "psf": psf, "geo": geo, "wmap": wmap, "zern": wst["zernike"], "rms_w": wst["rms_waves"],
            "pv": float(np.nanmax(wmap) - np.nanmin(wmap)),
            "rms_um": st["rms_radius"] * 1000.0}


# --------------------------------------------------------------------------- 球面収差
def record_spherical(T):
    """絞りの半径 a を 1.5 → 20 mm(f/33 → f/2.5)へ。"""
    a_s = 1.5 + (20.0 - 1.5) * ease(np.linspace(0, 1, T))
    rho = np.linspace(-1, 1, 11)
    fr = []
    for a in a_s:
        s = singlet(a)
        p = fs.paraxial_trace(s)
        um = p["marginal"]["u"][-1]
        W = fs.seidel_coefficients(s, field=0.0)["wavefront_mm"]
        tr = trace(s, 0.0, np.zeros_like(rho), rho * a * 0.999)
        fan = fs.ray_fan(s, field=0.0, n=21)
        th = 4 * W["W040"] * fan[:, 0] ** 3 / um                     # ε = (1/(n′u′)) ∂W/∂ρ, n′ = 1
        # 周辺光線(ρ = 1)が軸を横切る位置
        P, D = tr["points"][-1, -2], tr["dirs"][-1, -1]
        z_marg = P[2] - P[1] / D[1] * D[2]
        rec = frame_common(s, 0.0)
        rec.update({"knob": a, "fno": p["fno"], "um": um, "W": W, "pts": tr["points"], "rays_px": np.zeros_like(rho),
                    "rays_py": rho, "fan": [fan], "fan_th": [np.column_stack([fan[:, 0], th])],
                    "img_z": tr["points"][0, -1, 2], "z_marg": z_marg,
                    "z_marg_th": tr["points"][0, -1, 2] - th[-1] / um,
                    "ta_real": fan[-1, 1] * 1000, "ta_th": th[-1] * 1000})
        fr.append(rec)
    return fr


# --------------------------------------------------------------------------- コマ収差
def record_coma(T):
    """画角 0 → 10°(軸上で無収差の非球面、f/4)。"""
    f_s = 10.0 * ease(np.linspace(0, 1, T))
    a = 12.5 * 0.999
    ang = np.linspace(0, 2 * np.pi, 12, endpoint=False)
    px = np.r_[np.cos(ang), 0.5 * np.cos(ang[::2]), 0.0]
    py = np.r_[np.sin(ang), 0.5 * np.sin(ang[::2]), 0.0]
    fr = []
    s = descartes()
    p = fs.paraxial_trace(s)
    um = p["marginal"]["u"][-1]
    for f in f_s:
        W = fs.seidel_coefficients(s, field=f)["wavefront_mm"]
        tr = trace(s, f, px * a, py * a)
        ft = fs.ray_fan(s, field=f, n=21, axis="y")
        fx = fs.ray_fan(s, field=f, n=21, axis="x")
        q = ft[:, 0]
        tht = 3 * W["W131"] * q ** 2 / um + 2 * (W["W222"] + W["W220"]) * q / um
        ths = W["W131"] * q ** 2 / um
        rec = frame_common(s, f)
        sym_t = 0.5 * (ft[-1, 1] + ft[0, 1])
        sag_y = coma_sagittal_y(s, f)
        rec.update({"knob": f, "fno": p["fno"], "um": um, "W": W, "pts": tr["points"], "rays_px": px, "rays_py": py,
                    "fan": [ft, sagittal_y_fan(s, f, q)], "fan_th": [np.column_stack([q, tht]), np.column_stack([q, ths])],
                    "img_z": tr["points"][0, -1, 2], "tc_real": sym_t * 1000, "tc_th": 3 * W["W131"] / um * 1000,
                    "sc_real": sag_y * 1000})
        fr.append(rec)
    return fr


def sagittal_y_fan(system, field, q):
    """サジタルの扇(瞳の x に沿う光線)の像面での **y** のずれ(コマのサジタル成分は y に出る)。"""
    tr = trace(system, field, q * 12.5 * 0.999, np.zeros_like(q))
    ch = trace(system, field, [0.0], [0.0])["points"][0, -1]
    return np.column_stack([q, tr["points"][:, -1, 1] - ch[1]])


def coma_sagittal_y(system, field):
    f = sagittal_y_fan(system, field, np.array([-1.0, 1.0]))
    return float(np.mean(f[:, 1]))


# --------------------------------------------------------------------------- 非点収差と像面湾曲
def record_astig(T):
    """画角 0 → 20°(絞りを 20 mm 前に出した単レンズ、f/12.5)。"""
    f_s = 20.0 * ease(np.linspace(0, 1, T))
    s = stop_front()
    p = fs.paraxial_trace(s)
    um = p["marginal"]["u"][-1]
    a = 4.0 * 0.999
    qq = np.linspace(-1, 1, 7)
    px = np.r_[np.zeros(7), np.array([-1, -0.5, 0.5, 1.0])]
    py = np.r_[qq, np.zeros(4)]
    img_d = p["bfl"]
    fr = []
    for f in f_s:
        W = fs.seidel_coefficients(s, field=f)["wavefront_mm"]
        tr = trace(s, f, px * a, py * a)
        ft = fs.ray_fan(s, field=f, n=21, axis="y")
        fx = fs.ray_fan(s, field=f, n=21, axis="x")
        q = ft[:, 0]
        PT, PS = diff_foci(s, f, 4.0)
        z_img = tr["points"][0, -1, 2]
        dzT_th = -2 * (W["W220"] + W["W222"]) / um ** 2
        dzS_th = -2 * W["W220"] / um ** 2
        dzP_th = dzS_th - 0.5 * (dzT_th - dzS_th)
        dzT, dzS = PT[2] - z_img, PS[2] - z_img
        # 像面を T と S の焦点(軸の位置)に置いたスポット(焦線)と、その中間の PSF・波面
        zl = s["surfaces"][-1]
        last = z_img - img_d                                         # 最後の面の頂点の z
        spT = spot_of(s, f, image_mm=PT[2] - last, rings=4)
        spS = spot_of(s, f, image_mm=PS[2] - last, rings=4)
        mid = stop_front(image_mm=0.5 * (PT[2] + PS[2]) - last)
        rec = frame_common(mid, f)
        rec["spot2"] = [spT, spS]
        tht = 2 * (W["W222"] + W["W220"]) * q / um
        ths = 2 * W["W220"] * q / um
        rec.update({"knob": f, "fno": p["fno"], "um": um, "W": W, "pts": tr["points"], "rays_px": px, "rays_py": py,
                    "fan": [ft, fx], "fan_th": [np.column_stack([q, tht]), np.column_stack([q, ths])],
                    "img_z": z_img, "PT": PT, "PS": PS, "dzT": dzT, "dzS": dzS, "dzT_th": dzT_th, "dzS_th": dzS_th,
                    "dzP_th": dzP_th, "zl": zl})
        fr.append(rec)
    return fr


# --------------------------------------------------------------------------- 色収差
def record_chroma(T, R3):
    """波長 0.43 → 0.70 µm。単レンズとアクロマート、像面はどちらも d 線の近軸の焦点に固定。"""
    wls = 0.43 + (0.70 - 0.43) * ease(np.linspace(0, 1, T))
    s1, s2 = singlet(12.5), achromat(R3)
    q = np.linspace(-1, 1, 9)
    out = []
    n_d = fs.refractive_index("N-BK7", WL_D)
    for wl in wls:
        recs = []
        for s in (s1, s2):
            tr = trace(s, 0.0, np.zeros_like(q), q * 12.5 * 0.999, wl=wl)
            rec = frame_common(s, 0.0, wl)
            rec.update({"pts": tr["points"], "bfl": bfl_at(s, wl), "img_z": tr["points"][0, -1, 2]})
            recs.append(rec)
        n = fs.refractive_index("N-BK7", wl)
        out.append({"knob": wl, "lens": recs, "rays_px": np.zeros_like(q), "rays_py": q,
                    "bfl_th": 51.68 / (n - 1.0) - 9.0 / n, "n": n, "n_d": n_d})
    return out


# =========================================================================== 3-D の形
def box_mesh(lo, hi):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    c = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    quads = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    pos, tri = [], []
    for qd in quads:
        k = len(pos)
        pos += [c[i] for i in qd]
        tri += [[k, k + 1, k + 2], [k, k + 2, k + 3]]
    return np.array(pos), np.array(tri)


def s2w(p):
    """系の座標 (x, y, z)(z = 光軸)→ 3-D の世界 (X, Y, Z) = (z, x, y)。巡回の置換なので回転(鏡映ではない)。"""
    p = np.asarray(p, float)
    return np.stack([p[..., 2], p[..., 0], p[..., 1]], -1)


def sag(r, R, k=0.0):
    if R == INF:
        return np.zeros_like(r)
    c = 1.0 / R
    return c * r * r / (1 + np.sqrt(np.maximum(0.0, 1 - (1 + k) * c * c * r * r)))


def half_lens_mesh(z0, R0, k0, z1, R1, k1, ap, n_r=10, n_p=18, cut=0.5):
    """レンズの半分(x ≥ cut、手前 = −x の側から断面と中の光線が見える)。表面の形は面の式(sag)から。系の座標で返す。"""
    phi = np.linspace(-np.pi / 2, np.pi / 2, n_p)
    r = np.linspace(0, ap, n_r)
    Rg, Pg = np.meshgrid(r, phi, indexing="ij")
    X, Y = Rg * np.cos(Pg) + cut, Rg * np.sin(Pg)
    pos, tri = [], []

    def grid(Z, flip):
        k0_ = len(pos)
        pos.extend(np.stack([X, Y, Z], -1).reshape(-1, 3))
        for i in range(n_r - 1):
            for j in range(n_p - 1):
                a, b, c, d = (k0_ + i * n_p + j, k0_ + i * n_p + j + 1, k0_ + (i + 1) * n_p + j + 1,
                              k0_ + (i + 1) * n_p + j)
                tri.extend([[a, c, b], [a, d, c]] if flip else [[a, b, c], [a, c, d]])
    grid(z0 + sag(Rg, R0, k0), False)
    grid(z1 + sag(Rg, R1, k1), True)
    # 縁(r = ap)と断面(x = −cut の面)
    for ring_pts in ([(X[-1, j], Y[-1, j]) for j in range(n_p)],):
        kk = len(pos)
        for x, y in ring_pts:
            rr = ap
            pos.append([x, y, z0 + sag(np.array(rr), R0, k0)])
            pos.append([x, y, z1 + sag(np.array(rr), R1, k1)])
        for j in range(n_p - 1):
            a, b, c, d = kk + 2 * j, kk + 2 * j + 1, kk + 2 * j + 3, kk + 2 * j + 2
            tri.extend([[a, b, c], [a, c, d]])
    ys = np.linspace(-ap, ap, 2 * n_r - 1)
    kk = len(pos)
    for y in ys:
        pos.append([cut, y, z0 + sag(np.array(abs(y)), R0, k0)])
        pos.append([cut, y, z1 + sag(np.array(abs(y)), R1, k1)])
    for j in range(len(ys) - 1):
        a, b, c, d = kk + 2 * j, kk + 2 * j + 1, kk + 2 * j + 3, kk + 2 * j + 2
        tri.extend([[a, c, b], [a, d, c]])
    return np.array(pos, float), np.array(tri)


def lens_bodies(system, ap, name, rgb=(150, 200, 230), z_off=0.0, lift=0.0):
    """処方の面から、ガラスの区間ごとの半分のレンズ(世界座標の静止物体)。"""
    out = []
    z = 0.0
    nglass = 0
    sf = system["surfaces"]
    for i, s in enumerate(sf[:-1]):
        nxt = sf[i + 1]
        if s["t"] is None:
            break
        glass = abs(float(s["n_value"]) - 1.0) > 1e-12
        if glass:
            P, F = half_lens_mesh(z, s["R"], s.get("k", 0.0), z + s["t"], nxt["R"], nxt.get("k", 0.0), ap)
            Pw = s2w(P) + [z_off, 0, lift]
            col = rgb if nglass == 0 else (110, 150, 200)            # 2 枚目のガラス(フリント)は濃い色
            nglass += 1
            out.append({"name": "%s_%d" % (name, i), "pos": Pw, "faces": F, "rgb": list(col)})
        z += s["t"]
    return out


class Rays:
    """光線の折れ線を「長さの決まった細い棒」の剛体の組で描く。

    anim3d の物体はメッシュが 1 回だけでコマごとには姿勢しか持てない。線分 PQ の長さはコマごとに変わるので、
    長さ L0(全コマの最短)の棒を k = ceil(最長 / L0) 本、P から Q まで等間隔にずらして並べる(和集合が PQ に
    ちょうど重なり、どの棒も PQ からはみ出さない)。棒の向き = 線分の向き、位置 = op が返した点そのもの。
    """

    def __init__(self, pts_w, rgb, name, width=RAY_W):
        self.P = np.asarray(pts_w, float)                       # (T, N, K, 3) 世界座標
        T, N, K, _ = self.P.shape
        self.rgb = np.asarray(rgb)
        L = np.linalg.norm(np.diff(self.P, axis=2), axis=-1)       # (T, N, K-1)
        self.bodies, self.meta = [], []
        for i in range(N):
            for j in range(K - 1):
                lmin, lmax = float(L[:, i, j].min()), float(L[:, i, j].max())
                if lmax < 1e-6:
                    continue
                L0 = max(lmin, 1e-3)
                k = max(1, int(math.ceil(lmax / L0 - 1e-9)))
                pos, tri = box_mesh([0, -width / 2, -width / 2], [L0, width / 2, width / 2])
                c = [int(v) for v in np.clip(self.rgb[i] * 255, 0, 255)]
                for m in range(k):
                    self.bodies.append({"name": "%s_r%d_s%d_%d" % (name, i, j, m), "pos": pos, "faces": tri, "rgb": c})
                    self.meta.append((i, j, m, k, L0))

    def poses(self):
        T = self.P.shape[0]
        xyz = np.zeros((T, len(self.meta), 3))
        quat = np.zeros((T, len(self.meta), 4))
        for b, (i, j, m, k, L0) in enumerate(self.meta):
            P0, P1 = self.P[:, i, j], self.P[:, i, j + 1]
            d = P1 - P0
            L = np.linalg.norm(d, axis=-1)
            u = d / np.maximum(L, 1e-12)[:, None]
            off = np.zeros(T) if k == 1 else (L - L0) * m / (k - 1)
            xyz[:, b] = P0 + u * off[:, None]
            quat[:, b] = quat_x_to(u)
        return xyz, quat


def quat_x_to(u):
    """x 軸を単位ベクトル u に回す四元数 (w, x, y, z)。u は +x 寄り(光は +X へ進む)。"""
    w = 1.0 + u[:, 0]
    q = np.stack([w, np.zeros(len(u)), -u[:, 2], u[:, 1]], -1)
    bad = w < 1e-9
    q[bad] = [0.0, 0.0, 0.0, 1.0]
    return q / np.linalg.norm(q, axis=-1, keepdims=True)


# =========================================================================== 帯
CW = 100                        # 1 段の小窓
HEAD = 22
GAP = 14
STRIP = 34                      # 式の行
STAGE_RGB = [(0.95, 0.85, 0.35), (0.40, 0.85, 0.95), (1.0, 0.55, 0.35), (0.70, 0.55, 1.0)]
BG = 0.11


def _px(img, r, c, col, rad=1.0):
    h, w = img.shape[:2]
    r0, r1 = int(max(0, math.floor(r - rad))), int(min(h, math.ceil(r + rad) + 1))
    c0, c1 = int(max(0, math.floor(c - rad))), int(min(w, math.ceil(c + rad) + 1))
    if r0 >= r1 or c0 >= c1:
        return
    yy, xx = np.mgrid[r0:r1, c0:c1]
    m = np.hypot(yy - r, xx - c) <= rad + 0.2
    img[r0:r1, c0:c1][m] = col


def _poly(img, rr, cc, col, n=3):
    for i in range(len(rr) - 1):
        for t in np.linspace(0, 1, n):
            _px(img, rr[i] + t * (rr[i + 1] - rr[i]), cc[i] + t * (cc[i + 1] - cc[i]), col, 0.6)


def _text(img, s, xy, col, size=9, anchor="lm"):
    """文字(fs.text_box)。にじみを 2 値にして色を 1 つに(帯の PNG を小さく保つ。読みやすさは変わらない)。"""
    blank = np.zeros(img.shape[:2] + (3,))
    m = fs.text_box(blank, s, xy, anchor=anchor, font_size=size, min_font_size=6, pad=1, wrap=False,
                    text_color=(1.0, 1.0, 1.0), box_alpha=0.0, line_spacing=1.0).max(-1)
    out = np.array(img, float, copy=True)
    out[m > 0.35] = col
    return out


def nice(v):
    for s in (0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000):
        if v <= s:
            return s
    return 10000


def cell_fan(fans, ths, lim_um, cols_fn):
    """横収差の扇: 点 = 実光線(op の ray_fan)、線 = 3 次の式。縦軸 ±lim µm。"""
    c = np.full((CW, CW, 3), 0.08)
    c[CW // 2, 4:CW - 4] = 0.30
    c[4:CW - 4, CW // 2] = 0.30
    sc = (CW / 2 - 8) / lim_um

    def rc(q, e):
        return CW / 2 - e * sc, CW / 2 + q * (CW / 2 - 8)
    styles = [(1.0, 1.3), (0.55, 1.0)]
    for k, (fan, th) in enumerate(zip(fans, ths)):
        r, cc = rc(th[:, 0], np.clip(th[:, 1] * 1000, -lim_um * 1.05, lim_um * 1.05))
        _poly(c, r, cc, (0.95, 0.95, 0.95) if k == 0 else (0.6, 0.6, 0.6))
        for q, e in fan:
            if not np.isfinite(e):
                continue
            rr, ccc = rc(q, np.clip(e * 1000, -lim_um * 1.05, lim_um * 1.05))
            col = cols_fn(k, q)
            _px(c, rr, ccc, col, styles[k][1])
    c = _text(c, "+-%g um" % lim_um, (3, 9), (0.75, 0.75, 0.75), 8)
    return c


def cell_spot(spots, half_um, cols=None):
    """スポット(1 つか 2 つ)。窓は ±half_um。点の色 = 瞳の位置(または波長)。"""
    c = np.full((CW, CW, 3), 0.08)
    n = len(spots)
    w = CW // n
    for k, sp in enumerate(spots):
        cx = w * k + w / 2
        sc = (w / 2 - 3) / half_um
        col = pupil_rgb(sp["pupil"][:, 0], sp["pupil"][:, 1]) if cols is None else np.tile(cols[k], (len(sp["xy"]), 1))
        for (x, y), cl in zip(sp["xy"], col):
            r, cc = CW / 2 - y * sc, cx + x * sc
            if 0 <= r < CW and w * k <= cc < w * (k + 1):
                _px(c, r, cc, cl, 0.7)
        if k:
            c[:, w * k] = 0.3
    bar = nice(half_um * 0.6)
    L = bar * (w / 2 - 3) / half_um
    c[CW - 10:CW - 8, 4:4 + int(round(L))] = 0.85
    c = _text(c, "%g um" % bar, (4, CW - 19), (0.85, 0.85, 0.85), 8)
    return c


def _log_inferno(v):
    v = np.log10(1.0 + 999.0 * np.clip(v / max(float(v.max()), 1e-300), 0, 1)) / 3.0     # 対数(暈も見える)
    return fs.apply_cmap(v, "inferno", vmin=0.0, vmax=1.0, levels=6)


def cell_psf(psfs, half_um, pvs, geos=None):
    """③: 回折の PSF(対数の明るさ)。②と同じ µm の窓。

    回折の PSF を作れない(瞳の波面が数十波長で、op の 512 点の瞳の格子では折り返す)コマでは、幾何の PSF
    (``geo_psf``: 光線の密度 ⊗ Airy)を同じ窓に描き、左上に「geometric」と波面の PV を書く。"""
    c = np.full((CW, CW, 3), 0.08)
    n = len(psfs)
    w = CW // n
    geos = geos or [None] * n
    for k, ps in enumerate(psfs):
        if ps is None:
            if geos[k] is None:
                raise ValueError("cell_psf: 回折の PSF も幾何の PSF も無い")
            pitch = 2 * half_um / w
            c[:, w * k:w * (k + 1)] = _log_inferno(geo_psf(geos[k], CW, w, pitch))
            c[:24, w * k:w * (k + 1)] *= 0.35                         # 字の下地を暗く(PSF の上でも読める)
            c = _text(c, "geometric", (w * k + 2, 7), (0.55, 0.85, 1.0), 8)
            c = _text(c, "PV %.0fwv>>1" % pvs[k], (w * k + 2, 18), (0.55, 0.85, 1.0), 8)
            if k:
                c[:, w * k] = 0.3
            continue
        P, dx = ps["psf"], ps["dx"]
        M = P.shape[0]
        g = (np.arange(w) - (w - 1) / 2) * (2 * half_um / w)
        gr = (np.arange(CW) - (CW - 1) / 2) * (2 * half_um / w)
        ii = gr[:, None] / dx * -1 + M // 2                        # 行 = −y
        jj = g[None, :] / dx + M // 2
        i0, j0 = np.floor(ii).astype(int), np.floor(jj).astype(int)
        fi, fj = ii - i0, jj - j0

        def at(i, j):
            ok = (i >= 0) & (i < M) & (j >= 0) & (j < M)
            return np.where(ok, P[np.clip(i, 0, M - 1), np.clip(j, 0, M - 1)], 0.0)
        v = ((1 - fi) * (1 - fj) * at(i0, j0) + (1 - fi) * fj * at(i0, j0 + 1)
             + fi * (1 - fj) * at(i0 + 1, j0) + fi * fj * at(i0 + 1, j0 + 1))
        c[:, w * k:w * (k + 1)] = _log_inferno(v)
        c = _text(c, "S=%.2f" % ps["strehl"], (w * k + 2, 9), (0.85, 0.85, 0.85), 7)
        if k:
            c[:, w * k] = 0.3
    return c


def zmap(z, keys, D):
    """ゼルニケの項の和を D×D の瞳の格子に(match3d.fit_zernike と同じ規格化: Z20 = 2ρ²−1 など、正規化しない)。"""
    g = (np.arange(D) + 0.5) / D * 2 - 1
    X, Y = np.meshgrid(g, -g)
    r, th = np.hypot(X, Y), np.arctan2(Y, X)
    out = np.zeros((D, D))
    for (n, m), c in z.items():
        if (n, abs(m)) not in keys:
            continue
        R = {(2, 0): 2 * r ** 2 - 1, (2, 2): r ** 2, (3, 1): 3 * r ** 3 - 2 * r, (4, 0): 6 * r ** 4 - 6 * r ** 2 + 1}[(n, abs(m))]
        out += c * R * (np.cos(abs(m) * th) if m >= 0 else np.sin(abs(m) * th))
    out[r > 1] = np.nan
    return out


ZKEYS = (("defocus", (2, 0)), ("astig", (2, 2)), ("coma", (3, 1)), ("spherical", (4, 0)))


def cell_wave(wmap, zern):
    """④: 瞳の波面(OPD、全体)の地図と、ゼルニケの種類別の地図(ピント・非点・コマ・球面、共通の尺度)と大きさの棒。"""
    c = np.full((CW, CW, 3), 0.08)
    n = wmap.shape[0]
    D = 56
    lim = max(np.nanmax(np.abs(wmap)), 1e-6)
    rr = (np.arange(D) + 0.5) / D * n
    sub = wmap[np.clip(rr.astype(int), 0, n - 1)][:, np.clip(rr.astype(int), 0, n - 1)][::-1]
    rgb = fs.apply_cmap(np.nan_to_num(sub / lim), "coolwarm", vmin=-1.0, vmax=1.0, levels=8)
    rgb[~np.isfinite(sub)] = 0.08
    c[4:4 + D, 4:4 + D] = rgb
    c = _text(c, "+-%.3g wv" % lim if lim < 10 else "+-%.0f wv" % lim, (4, 4 + D + 8), (0.8, 0.8, 0.8), 7)
    d = 16
    maps = [zmap(zern, (key,), d) for _k, key in ZKEYS]
    ml = max(max(float(np.nanmax(np.abs(m))) for m in maps), 1e-9)
    for i, ((k, _key), m) in enumerate(zip(ZKEYS, maps)):
        y, x = 5 + (i // 2) * (d + 4), 4 + D + 3 + (i % 2) * (d + 4)
        c[y - 1:y + d + 1, x - 1:x + d + 1] = ZCOL[k]
        sm = fs.apply_cmap(np.nan_to_num(m / ml), "coolwarm", vmin=-1.0, vmax=1.0, levels=8)
        sm[~np.isfinite(m)] = 0.08
        c[y:y + d, x:x + d] = sm
    g = zgroups(zern)
    gm = max(max(g.values()), 1e-9)
    for i, k in enumerate(("defocus", "astig", "coma", "spherical", "higher")):
        y = 76 + i * 4
        L = int(round((CW - 8) * g[k] / gm))
        c[y:y + 3, 4:4 + max(L, 1)] = ZCOL[k]
    return c


STAGES = ("1 trace_rays > ray_fan", "2 ray_bundle (spot)", "3 psf_field_grid", "4 wavefront_from_opd")


def band_static(names=STAGES):
    """見出しの行(段ごとの op の登録名)を、強調する段ごとに前もって描く(コマごとに字を描かない)。

    見出しは 2 値にすると細い字(_ や r)が欠けるので、ここだけ 3 段のにじみを残す。"""
    W = 4 * (CW + 4) + 3 * GAP
    heads = []
    blank = np.zeros((HEAD, W, 3))
    masks = [fs.text_box(blank, nm, (3 + s * (CW + 4 + GAP), HEAD // 2) if s < 3 else (W - 1, HEAD // 2),
                         anchor="lm" if s < 3 else "rm", font_size=9, min_font_size=7,
                         pad=1, wrap=False, text_color=(1.0, 1.0, 1.0), box_alpha=0.0).max(-1)
             for s, nm in enumerate(names)]
    for active in range(4):
        hb = np.full((HEAD, W, 3), BG)
        for s, m in enumerate(masks):
            col = np.asarray(STAGE_RGB[s] if s == active else (0.55, 0.55, 0.55))
            for lo, a in ((0.2, 0.5), (0.6, 1.0)):
                sel = m > lo
                hb[sel] = (1 - a) * BG + a * col
        heads.append(hb)
    return heads


def band_frame(cells, active, formula, heads):
    cols = []
    for s, p in enumerate(cells):
        on = s == active
        body = p if on else 0.6 * p + 0.4 * BG
        body = np.pad(body, ((2, 2), (2, 2), (0, 0)), constant_values=0)
        bc = STAGE_RGB[s] if on else (0.25, 0.25, 0.25)
        body[:2], body[-2:], body[:, :2], body[:, -2:] = bc, bc, bc, bc
        cols.append(body)
        if s < 3:
            arr = np.full((cols[-1].shape[0], GAP, 3), BG)
            mid = CW // 2 + 2
            ac = STAGE_RGB[s + 1] if s + 1 == active else (0.45, 0.45, 0.45)
            arr[mid - 1:mid + 2, 2:GAP - 5] = ac
            for t in range(5):
                arr[mid - (5 - t):mid + (5 - t) + 1, GAP - 6 + t] = ac
            cols.append(arr)
    out = np.concatenate([heads[active], np.concatenate(cols, 1)], 0)
    strip = np.full((STRIP, out.shape[1], 3), BG)
    for i, line in enumerate(formula[:2]):
        strip = _text(strip, line, (4, 9 + 15 * i), (0.88, 0.88, 0.80), 9)
    strip = _text(strip, "Fullseye", (out.shape[1] - 4, STRIP - 8), (0.45, 0.62, 0.80), 8, "rm")
    out = np.concatenate([out, strip], 0)
    return np.rint(np.clip(out, 0, 1) * 255).astype(np.uint8)


def half_window(spots, psfs, fno, wl=WL_D):
    r = 0.0
    for sp in spots:
        if len(sp["xy"]):
            r = max(r, float(np.max(np.abs(sp["xy"]))))
    airy = 1.22 * wl * fno
    return float(max(1.25 * r, 2.5 * airy, 2.0))


# =========================================================================== タブ
def stage_of(k):
    return (k // STAGE_PERIOD) % 4


def tab_from(frames, t, tab_id, label, badge, text, rays_list, statics, extra_bodies, trails, clouds, events,
             series, cells_fn, formula_fn, numbers, view, stages=STAGES):
    heads = band_static(stages)
    band = np.stack([band_frame(cells_fn(k, fr), stage_of(k), formula_fn(fr), heads) for k, fr in enumerate(frames)])
    bodies = list(statics)
    T = len(frames)
    xyz_s, quat_s = [], []
    for b in statics:
        xyz_s.append(np.zeros((T, 3)))
        quat_s.append(np.tile([1.0, 0, 0, 0], (T, 1)))
    for b, x, q in extra_bodies:
        bodies.append(b)
        xyz_s.append(x)
        quat_s.append(q)
    xyz = np.stack(xyz_s, 1) if xyz_s else np.zeros((T, 0, 3))
    quat = np.stack(quat_s, 1) if quat_s else np.zeros((T, 0, 4))
    for R in rays_list:
        x, q = R.poses()
        bodies += R.bodies
        xyz = np.concatenate([xyz, x], 1)
        quat = np.concatenate([quat, q], 1)
    tab = fs.viewer_anim3d_tab(
        tab_id, label, badge, text, t, bodies, xyz, quat, trails=trails, clouds=clouds, events=events, series=series,
        panes=[{"label": _t("Fullseye の処理の帯(いま効いている段を色で強調。② の点の色 = 3-D の拡大スポットの色。"
                            "③ に「geometric」とあるコマは幾何光学の領域: 瞳の波面が PV で数十波長(≫ 1 波長)あり、回折の PSF は"
                            "op の瞳の格子では折り返すので作らず、光線の密度に Airy を畳み込んだ幾何の PSF(② のスポット図と同じ形)を描く。"
                            "④ 左 = 瞳の波面の全体、右の 4 枚と下の棒 = ゼルニケの種類別: 緑 Z20 ピント・紫 Z22 非点・"
                            "水色 Z31 コマ・橙 Z40 球面・赤 5 次より上)",
                            "Fullseye processing band (active stage highlighted; the colours in 2 are those of the "
                            "magnified spot in 3-D; 3 marked 'geometric' = geometric-optics regime: the pupil wavefront is tens of waves PV, "
                            "so the diffraction PSF would alias on the op's pupil grid; the ray density convolved with an Airy "
                            "disc is drawn instead, the same shape as the spot in 2; 4: left = whole pupil wavefront, right maps and bars = Zernike by "
                            "kind: green Z20 defocus, purple Z22 astigmatism, cyan Z31 coma, orange Z40 spherical, "
                            "red higher)"), "frames": band, "png": True}],
        numbers=numbers, view=view)
    return tab, band, bodies, xyz, quat


def screen(name, z_w, half, rgb=(46, 52, 60), y0=0.0, thick=0.3, lift=0.0):
    P, F = box_mesh([z_w - thick / 2, y0 - half, lift - half], [z_w + thick / 2, y0 + half, lift + half])
    return {"name": name, "pos": P, "faces": F, "rgb": list(rgb)}


def marker(name, size, rgb):
    P, F = box_mesh([-size / 2] * 3, [size / 2] * 3)
    return {"name": name, "pos": P, "faces": F, "rgb": list(rgb)}


def panel(name, cx, cz, half, rgb=(30, 34, 40)):
    """拡大スポットの板(見る人の方 = −Y を向く。点は Y = 0、板はその奥)。"""
    P, F = box_mesh([cx - half, 0.6, cz - half], [cx + half, 0.9, cz + half])
    return {"name": name, "pos": P, "faces": F, "rgb": list(rgb)}


def spot_cloud(sp, centre_w, mag, cols=None, offset=(0.0, 0.0)):
    """スポットを mag 倍し、見る人の方へ向けた板の上に点で置く(像面の x → 板の横、y → 板の縦)。色 = 帯の②と同じ。"""
    xy = sp["xy"] / 1000.0 * mag
    p = np.column_stack([centre_w[0] + offset[0] + xy[:, 0], np.zeros(len(xy)),
                         centre_w[2] + offset[1] + xy[:, 1]])
    col = pupil_rgb(sp["pupil"][:, 0], sp["pupil"][:, 1]) if cols is None else np.tile(cols, (len(xy), 1))
    return p, col


def fan_lim(f):
    """扇の縦軸の範囲(コマごと、きりのよい値)。実光線と式の大きい方の 1.1 倍。"""
    m = 0.0
    for a in list(f["fan"]) + list(f["fan_th"]):
        v = np.abs(a[:, 1])
        m = max(m, float(np.nanmax(v)) if np.isfinite(v).any() else 0.0)
    return nice(max(m * 1000 * 1.1, 0.5))


def fan_cols(k, q):
    return tuple(pupil_rgb([0.0], [q])[0]) if k == 0 else tuple(pupil_rgb([q], [0.0])[0] * 0.8)


# --------------------------------------------------------------------------- 球面収差のタブ
def tab_spherical(fr, t):
    T = len(fr)
    pts = np.stack([f["pts"] for f in fr])                           # (T, N, K, 3)
    pts = pts.copy()
    pts[:, :, 0] = pts[:, :, 1] - (pts[:, :, 1] - pts[:, :, 0]) / np.linalg.norm(
        pts[:, :, 1] - pts[:, :, 0], axis=-1, keepdims=True) * LIN   # 入射の線の長さを LIN にそろえる
    W_ = s2w(pts)
    rgb = pupil_rgb(fr[0]["rays_px"], fr[0]["rays_py"])
    rays = Rays(W_, rgb, "ray")
    img_x = float(fr[0]["img_z"])
    statics = lens_bodies(singlet(20.0), 20.5, "lens")
    statics.append(screen("image_plane", img_x, 4.0))
    panel_c = np.array([img_x - 20.0, 0.0, 17.0])
    statics.append(panel("spot_panel", panel_c[0], panel_c[2], 9.0))
    mk = marker("marginal_focus", 0.9, (255, 170, 60))
    mx = np.stack([[f["z_marg"], 0.0, 0.0] for f in fr])
    extra = [(mk, mx, np.tile([1.0, 0, 0, 0], (T, 1)))]
    mag = 7.5 / max(1e-9, max(np.abs(f["spot"]["xy"]).max() for f in fr) / 1000.0)
    clouds = []
    for k, f in enumerate(fr):
        p, c = spot_cloud(f["spot"], panel_c, mag)
        clouds.append({"k": k, "pos": p, "rgb": c, "point_size": 0.35})
    trails = [{"xyz": mx + [0, 0, 0.0], "color": "#ffb74d", "tail": 0,
               "label": _t("周辺光線の焦点(実光線)", "Marginal focus (real rays)")},
              {"xyz": np.stack([[f["z_marg_th"], 0.0, -1.2] for f in fr]), "color": "#e0e0e0", "tail": 0,
               "label": _t("3 次の式の予測(1.2 mm 下にずらして描く)", "Third-order prediction (drawn 1.2 mm lower)")}]
    ratio = np.array([f["ta_real"] / f["ta_th"] for f in fr])
    strehl = np.array([f["psf"]["strehl"] if f["psf"] else np.nan for f in fr])
    events = [{"t": t[0], "label": _t("f/33: ほぼ 1 点に集まる", "f/33: nearly a point")}]
    k8 = next((k for k, s in enumerate(strehl) if np.isfinite(s) and s < 0.8), None)
    if k8 is not None:
        events.append({"t": t[k8], "label": _t("回折の限界を越える(Strehl < 0.8、f/%.0f)" % fr[k8]["fno"],
                                              "Beyond the diffraction limit (Strehl < 0.8, f/%.0f)" % fr[k8]["fno"])})
    for lim, ja, en in ((1.05, "限界: 3 次の式から 5 %% 外れる(f/%.1f)", "Limit: third order off by 5 %% (f/%.1f)"),
                        (1.10, "限界: 10 %% 外れる(f/%.1f)", "Limit: off by 10 %% (f/%.1f)")):
        kk = next((k for k, r in enumerate(ratio) if r > lim), None)
        if kk is not None:
            events.append({"t": t[kk], "label": _t(ja % fr[kk]["fno"], en % fr[kk]["fno"])})

    def cells(k, f):
        hw = half_window([f["spot"]], [f["psf"]], f["fno"])
        return [cell_fan(f["fan"], f["fan_th"], fan_lim(f), fan_cols), cell_spot([f["spot"]], hw),
                cell_psf([f["psf"]], hw, [f["pv"]], [f["geo"]]), cell_wave(f["wmap"], f["zern"])]

    def formula(f):
        wl = WL_D * 1e-3
        return ["f/%.1f  eps(rho=1) = 4 W040/(n'u') = 4x%.2f wv x %.3g um / %.4f = %.1f um" % (
                    f["fno"], f["W"]["W040"] / wl, WL_D, f["um"], f["ta_th"]),
                "traced %.1f um  ratio %.3f   6 Z40 = %.2f wv vs W040 = %.2f wv" % (
                    f["ta_real"], f["ta_real"] / f["ta_th"], 6 * f["zern"].get((4, 0), 0.0), f["W"]["W040"] / wl)]
    series = [{"label": _t("周辺光線の焦点のずれ(手前が負)", "Marginal focus shift (negative = towards the lens)"),
               "values": np.array([f["z_marg"] - f["img_z"] for f in fr]), "lo": -4.0, "hi": 0.2, "unit": "mm",
               "decimals": 3, "color": "#ffb74d"},
              {"label": _t("横収差 実光線 / 3 次の式", "Transverse aberration real / third order"), "values": ratio,
               "lo": 0.98, "hi": 1.16, "unit": "", "decimals": 3, "color": "#e0e0e0"},
              {"label": _t("Strehl 比(PSF の頂 / 無収差の頂。幾何光学の領域は —)", "Strehl ratio (— in the geometric regime)"), "values": strehl,
               "lo": 0.0, "hi": 1.0, "unit": "", "decimals": 3, "color": "#ff8a65"}]
    nums = [fs.viewer_number(_t("レンズ", "Lens"), "N-BK7 plano-convex, f = %.1f mm" % fs.paraxial_trace(singlet())["efl"]),
            fs.viewer_number(_t("つまみ", "Knob"), _t("絞りの半径 1.5 → 20 mm(f/33 → f/2.5)", "stop radius 1.5 → 20 mm")),
            fs.viewer_number(_t("実光線 / 3 次(f/33 → f/4 → f/2.5)", "Real / third order"),
                             "%.3f → %.3f → %.3f" % (ratio[0], ratio[np.argmin(np.abs([f["fno"] - 4 for f in fr]))],
                                                    ratio[-1]))]
    text = _t("球面収差: 絞りを開くと、レンズの縁を通る光ほど手前で軸を横切る(橙の箱 = 周辺の光の焦点、"
              "白い板 = 近軸の像面)。上の板は像面のスポットを拡大してこちらへ向けたもの(色 = 瞳のどこを通ったか)。"
              "帯の①は横収差の扇: 点が実光線、白い線が 3 次(ザイデル)の式。暗い絞りでは重なり、"
              "開くほど離れる(近軸の近似の限界)。",
              "Spherical aberration: opening the stop makes rays through the rim cross the axis earlier (orange box = "
              "marginal focus, white plate = paraxial image). The panel above shows the image-plane spot magnified and turned to face you "
              "(colour = where the ray crossed the pupil). Band 1: dots are real rays, the white curve is the "
              "third-order (Seidel) formula; they agree at small apertures and part as the stop opens.")
    return tab_from(fr, t, "spherical", _t("球面収差(絞り)", "Spherical (aperture)"), "passed", text, [rays], statics,
                    extra, trails, clouds, events, series, cells, formula, nums,
                    {"az": -1.25, "el": 0.22, "dist": 0.6})


# --------------------------------------------------------------------------- コマ収差のタブ
SMALL_FIELD = 0.5               # これより小さい画角では、比は 0/0 に近く意味が無い(「—」で出す)


def coma_ratio(f):
    return f["tc_real"] / f["tc_th"] if f["knob"] >= SMALL_FIELD else np.nan


def fmt_ratio(r, fmt="%.3f"):
    return "-" if not np.isfinite(r) else fmt % r


def tab_coma(fr, t):
    T = len(fr)
    pts = np.stack([f["pts"] for f in fr])
    W_ = s2w(pts)
    rgb = pupil_rgb(fr[0]["rays_px"], fr[0]["rays_py"])
    rays = Rays(W_, rgb, "ray")
    img_x = float(fr[0]["img_z"])
    statics = lens_bodies(descartes(), 12.8, "lens")
    statics.append(screen("image_plane", img_x, 11.0, lift=9.0))
    mag = 12.0 / max(1e-9, max(np.abs(f["spot"]["xy"]).max() for f in fr) / 1000.0)
    clouds, ch = [], []
    pc = np.array([img_x - 28.0, 0.0, 32.0])
    statics.append(panel("spot_panel", pc[0], pc[2], 9.0))
    for k, f in enumerate(fr):
        ch.append(s2w(f["pts"][-1, -1]))
        p, c = spot_cloud(f["spot"], pc + [0, 0, -4.0], mag)        # 尾は上(+y)へ伸びるので頭を板の下寄りに
        clouds.append({"k": k, "pos": p, "rgb": c, "point_size": 0.3})
    ch = np.array(ch)
    extra = []
    trails = [{"xyz": ch, "color": "#80deea", "tail": 0,
               "label": _t("主光線が像面に当たる点", "Chief ray on the image plane")}]
    ratio = np.array([coma_ratio(f) for f in fr])
    events = [{"t": t[0], "label": _t("0°: 1 点(このレンズは軸上で無収差)", "0°: a point (stigmatic on axis)")}]
    for fd, ja, en in ((2.0, "2°: 彗星の尾が出る", "2°: a comet tail appears"),
                       (6.0, "6°: 尾 = 瞳の輪が 2 周する円の重なり", "6°: the tail is circles traced twice")):
        kk = int(np.argmin(np.abs([f["knob"] - fd for f in fr])))
        events.append({"t": t[kk], "label": _t(ja, en)})
    kk = next((k for k, r in enumerate(ratio) if k > 0 and r > 1.05), None)
    if kk is not None:
        events.append({"t": t[kk], "label": _t("限界: 3 次の式から 5 %% 外れる(%.1f°)" % fr[kk]["knob"],
                                              "Limit: third order off by 5 %% (%.1f°)" % fr[kk]["knob"])})

    def cells(k, f):
        hw = half_window([f["spot"]], [f["psf"]], f["fno"])
        return [cell_fan(f["fan"], f["fan_th"], fan_lim(f), fan_cols), cell_spot([f["spot"]], hw),
                cell_psf([f["psf"]], hw, [f["pv"]], [f["geo"]]), cell_wave(f["wmap"], f["zern"])]

    def formula(f):
        wl = WL_D * 1e-3
        return ["%.1f deg  tangential coma = 3 W131/(n'u') = 3x%.2f wv x %.3g um / %.3f = %.1f um" % (
                    f["knob"], f["W"]["W131"] / wl, WL_D, f["um"], f["tc_th"]),
                "traced T %.1f um (ratio %s)  S %.1f um (S/T %s, theory 1/3)" % (
                    f["tc_real"], fmt_ratio(coma_ratio(f)), f["sc_real"],
                    fmt_ratio(f["sc_real"] / f["tc_real"] if f["knob"] >= SMALL_FIELD else np.nan))]
    series = [{"label": _t("メリディオナルのコマ(実光線)", "Tangential coma (real rays)"),
               "values": np.array([f["tc_real"] for f in fr]), "lo": -50.0, "hi": 1400.0, "unit": "µm", "decimals": 1,
               "color": "#80deea"},
              {"label": _t("実光線 / 3 次の式", "Real / third order"), "values": ratio, "lo": 0.98, "hi": 1.08,
               "unit": "", "decimals": 3, "color": "#e0e0e0"},
              {"label": _t("RMS スポット半径", "RMS spot radius"), "values": np.array([f["rms_um"] for f in fr]),
               "lo": 0.0, "hi": 500.0, "unit": "µm", "decimals": 1, "color": "#ffb74d"}]
    nums = [fs.viewer_number(_t("レンズ", "Lens"), _t("平凸の非球面(出口 k = −n²)、f/4", "plano-aspheric (exit k = −n²), f/4")),
            fs.viewer_number(_t("つまみ", "Knob"), _t("画角 0 → 10°", "field 0 → 10°")),
            fs.viewer_number(_t("実光線 / 3 次(2° → 10°)", "Real / third order (2° → 10°)"),
                             "%.3f → %.3f" % (ratio[int(np.argmin(np.abs([f["knob"] - 2 for f in fr])))], ratio[-1]))]
    text = _t("コマ収差: 軸上では 1 点に集まるよう作った非球面レンズでも、斜めから来た光は彗星の形に広がる。"
              "瞳の 1 つの輪(同じ色の並び)は像面で円になり、その円を 2 周する(色が 2 回巡る)。"
              "輪が大きいほど円も大きく、主光線から遠くへずれる —— それが尾。"
              "帯の①: 白い線 = メリディオナル(縦)の扇の 3 次の式 3·W131·ρ²、灰の線 = サジタル(横)の W131·ρ²(1/3)。",
              "Coma: even a lens built to focus perfectly on axis spreads oblique light into a comet. One pupil ring "
              "(one run of colours) becomes a circle on the image plane, traced twice (the colours repeat twice). "
              "Bigger rings give bigger circles further from the chief ray: the tail. Band 1: white = tangential "
              "third order 3·W131·ρ², grey = sagittal W131·ρ² (one third).")
    return tab_from(fr, t, "coma", _t("コマ収差(画角)", "Coma (field)"), "passed", text, [rays], statics, extra,
                    trails, clouds, events, series, cells, formula, nums, {"az": -1.25, "el": 0.22, "dist": 0.6})


# --------------------------------------------------------------------------- 非点収差のタブ
def tab_astig(fr, t):
    T = len(fr)
    pts = np.stack([f["pts"] for f in fr])
    W_ = s2w(pts)
    rgb = pupil_rgb(fr[0]["rays_px"], fr[0]["rays_py"])
    rays = Rays(W_, rgb, "ray")
    img_x = float(fr[0]["img_z"])
    statics = lens_bodies(stop_front(), 12.0, "lens")
    stop_P, stop_F = box_mesh([-0.3, -9.0, 4.0], [0.3, 9.0, 9.0])
    stop_P2, stop_F2 = box_mesh([-0.3, -9.0, -9.0], [0.3, 9.0, -4.0])
    statics.append({"name": "stop_top", "pos": stop_P, "faces": stop_F, "rgb": [90, 90, 96]})
    statics.append({"name": "stop_bottom", "pos": stop_P2, "faces": stop_F2, "rgb": [90, 90, 96]})
    statics.append(screen("image_plane", img_x, 19.0, lift=14.0))
    PT = s2w(np.stack([f["PT"] for f in fr]))
    PS = s2w(np.stack([f["PS"] for f in fr]))
    mT, mS = marker("T_focus", 0.9, (255, 120, 120)), marker("S_focus", 0.9, (120, 170, 255))
    one = np.tile([1.0, 0, 0, 0], (T, 1))
    extra = [(mT, PT, one), (mS, PS, one)]

    def along(f, dz):                                              # 主光線の上で、軸の位置が img + dz の点
        ch = f["pts"][6]                                           # 扇の中央 = 主光線
        P, Q = ch[-2], ch[-1]
        u = (Q - P) / np.linalg.norm(Q - P)
        s_ = (f["img_z"] + dz - P[2]) / u[2]
        return P + s_ * u
    thT = s2w(np.stack([along(f, f["dzT_th"]) for f in fr]))
    thS = s2w(np.stack([along(f, f["dzS_th"]) for f in fr]))
    thP = s2w(np.stack([along(f, f["dzP_th"]) for f in fr]))
    trails = [{"xyz": PT, "color": "#ff7b7b", "tail": 0, "label": _t("T 像面(実光線)", "T image surface (real rays)")},
              {"xyz": PS, "color": "#7baaff", "tail": 0, "label": _t("S 像面(実光線)", "S image surface (real rays)")},
              {"xyz": thT + [0, 1.5, 0], "color": "#ffd0d0", "tail": 0, "label": _t("T の 3 次の式", "T, third order")},
              {"xyz": thS + [0, 1.5, 0], "color": "#d0e0ff", "tail": 0, "label": _t("S の 3 次の式", "S, third order")},
              {"xyz": thP + [0, 1.5, 0], "color": "#c8e6c9", "tail": 0,
               "label": _t("ペッツバール面(3 次の式)", "Petzval surface (third order)")}]
    half = max(max(np.abs(sp["xy"]).max() for sp in f["spot2"]) for f in fr) / 1000.0
    mag = 4.2 / max(half, 1e-9)
    clouds = []
    pc = np.array([img_x - 24.0, 0.0, -16.0])
    statics.append(panel("spot_panel", pc[0], pc[2], 10.0))
    for k, f in enumerate(fr):
        pa, ca = spot_cloud(f["spot2"][0], pc, mag, offset=(-5.0, 0.0))
        pb, cb = spot_cloud(f["spot2"][1], pc, mag, offset=(5.0, 0.0))
        clouds.append({"k": k, "pos": np.vstack([pa, pb]), "rgb": np.vstack([ca, cb]), "point_size": 0.3})
    events = [{"t": t[0], "label": _t("0°: T と S が一致", "0°: T and S coincide")}]
    for fd, ja, en in ((8.0, "8°: T と S の焦点が離れる", "8°: T and S foci separate"),
                       (14.0, "14°: 2 本の像面が手前へ曲がる", "14°: both image surfaces curve inward")):
        kk = int(np.argmin(np.abs([f["knob"] - fd for f in fr])))
        events.append({"t": t[kk], "label": _t(ja, en)})
    rT = np.array([f["dzT"] / f["dzT_th"] if f["knob"] >= SMALL_FIELD else np.nan for f in fr])
    kk = next((k for k, r in enumerate(rT) if k > 0 and abs(r - 1) > 0.05), None)
    if kk is not None:
        events.append({"t": t[kk], "label": _t("限界: T 像面が 3 次の式から 5 %% 外れる(%.1f°)" % fr[kk]["knob"],
                                              "Limit: T surface off third order by 5 %% (%.1f°)" % fr[kk]["knob"])})

    def cells(k, f):
        hw = max(half_window(f["spot2"], [f["psf"]], f["fno"]), half_window([f["spot"]], [], f["fno"]) * 0)
        return [cell_fan(f["fan"], f["fan_th"], fan_lim(f), fan_cols), cell_spot(f["spot2"], hw),
                cell_psf([f["psf"]], half_window([f["spot"]], [f["psf"]], f["fno"]), [f["pv"]], [f["geo"]]),
                cell_wave(f["wmap"], f["zern"])]

    def formula(f):
        return ["%.1f deg  zT = -2(W220+W222)/u'^2 = %.3f mm  zS = -2 W220/u'^2 = %.3f mm" % (
                    f["knob"], f["dzT_th"], f["dzS_th"]),
                "traced zT %.3f  zS %.3f mm   (T-P)/(S-P) = %s (3 by theory)" % (
                    f["dzT"], f["dzS"], fmt_ratio((f["dzT"] - f["dzP_th"]) / (f["dzS"] - f["dzP_th"])
                                                  if f["knob"] >= SMALL_FIELD else np.nan, "%.2f"))]
    series = [{"label": _t("T の焦点のずれ(実光線)", "T focus shift (real rays)"), "values": np.array([f["dzT"] for f in fr]),
               "lo": -32.0, "hi": 1.0, "unit": "mm", "decimals": 3, "color": "#ff7b7b"},
              {"label": _t("S の焦点のずれ(実光線)", "S focus shift (real rays)"), "values": np.array([f["dzS"] for f in fr]),
               "lo": -32.0, "hi": 1.0, "unit": "mm", "decimals": 3, "color": "#7baaff"},
              {"label": _t("T: 実光線 / 3 次の式", "T: real / third order"), "values": rT, "lo": 0.98, "hi": 1.10,
               "unit": "", "decimals": 3, "color": "#e0e0e0"}]
    nums = [fs.viewer_number(_t("レンズ", "Lens"), _t("単レンズ + 20 mm 前の絞り(f/12.5)", "singlet + stop 20 mm ahead (f/12.5)")),
            fs.viewer_number(_t("つまみ", "Knob"), _t("画角 0 → 20°", "field 0 → 20°")),
            fs.viewer_number(_t("T: 実光線 / 3 次(20°)", "T: real / third order (20°)"), "%.3f" % rT[-1])]
    text = _t("非点収差と像面湾曲: 斜めの光では、縦の面(メリディオナル、赤)と横の面(サジタル、青)の光が"
              "別々の所で焦点を結ぶ。画角を広げると 2 つの焦点の軌跡が手前へ曲がった 2 本の像面になる"
              "(淡い線 = 3 次の式の予測、緑 = ペッツバール面)。下の板(拡大): 赤の焦点に置いた像は横に伸びた線、"
              "青の焦点では縦の線(焦線)。",
              "Astigmatism and field curvature: for oblique light the tangential (red) and sagittal (blue) fans focus "
              "at different places. Widening the field traces two inward-curving image surfaces (pale = third-order "
              "prediction, green = Petzval surface). Panel: at the red focus the image is a horizontal line, at the "
              "blue focus a vertical one (focal lines).")
    return tab_from(fr, t, "astig", _t("非点収差・像面湾曲(画角)", "Astigmatism & field curvature (field)"), "passed",
                    text, [rays], statics, extra, trails, clouds, events, series, cells, formula, nums,
                    {"az": -1.25, "el": 0.22, "dist": 0.6})


# --------------------------------------------------------------------------- 色収差のタブ
CH_LIFT = -34.0                 # アクロマートを描く高さ(単レンズの 34 mm 下)


def tab_chroma(fr, t, R3):
    T = len(fr)
    lifts = (0.0, CH_LIFT)
    statics = lens_bodies(singlet(12.5), 12.8, "singlet") + lens_bodies(achromat(R3), 12.8, "achromat", lift=CH_LIFT)
    rays_list, clouds, trails = [], [], []
    img_w = []
    q5 = np.linspace(-1, 1, 5)
    for j, sysj in enumerate((singlet(12.5), achromat(R3))):
        pts = np.stack([f["lens"][j]["pts"] for f in fr])
        Wp = s2w(pts) + [0, 0, lifts[j]]
        img_w.append(float(Wp[0, 0, -1, 0]))
        pin = Wp[:, :, :-1]                                       # レンズの出口まで(白い光)
        rays_list.append(Rays(pin, np.ones((pin.shape[1], 3)) * 0.92, "white%d" % j))
        statics.append(screen("sensor%d" % j, img_w[j], 3.0, lift=lifts[j]))
        # 教科書の 3 本の色(F 青・d 黄緑・C 赤)のレンズの後ろの光線: 時間で変わらない(淡い色で常に出す)
        for wl, nm in ((WL_F, "F"), (WL_D, "d"), (WL_C, "C")):
            tr = trace(sysj, 0.0, np.zeros(5), q5 * 12.5 * 0.999, wl=wl)
            seg = np.repeat((s2w(tr["points"][:, -2:]) + [0, 0, lifts[j]])[None], T, 0)
            rays_list.append(Rays(seg, np.tile(wl_rgb(wl) * 0.75, (5, 1)), "%s%d" % (nm, j), width=0.22))
    smax = max(np.abs(f["lens"][j]["spot"]["xy"]).max() for f in fr for j in range(2)) / 1000.0
    cmag = 5.0 / max(smax, 1e-9)
    for k, f in enumerate(fr):
        P = []
        col = wl_rgb(f["knob"])
        for j in range(2):
            pts = s2w(f["lens"][j]["pts"]) + [0, 0, lifts[j]]
            for r in range(0, pts.shape[0], 4):                    # いまの波長の光線(縁・中心・縁): 焦点の近く(後ろ 35 %)だけを点で
                a, b = pts[r, -2], pts[r, -1]
                s_ = np.linspace(0.65, 1.0, 14)
                P.append(a + s_[:, None] * (b - a))
            sp = f["lens"][j]["spot"]
            p, _c = spot_cloud(sp, np.array([img_w[j] - 24.0, 0.0, lifts[j] + 13.0]), cmag, cols=col)
            P.append(p)
        clouds.append({"k": k, "pos": np.vstack(P), "color": "#%02x%02x%02x" % tuple(int(round(v * 255)) for v in col),
                       "point_size": 0.55})
    for j in range(2):
        statics.append(panel("spot_panel%d" % j, img_w[j] - 24.0, lifts[j] + 13.0, 6.0))
    # 焦点の位置 vs 波長を 3-D の中にグラフとして描く(横 = 焦点の位置、縦 = 波長)
    ys = -5.0 - (np.array([f["knob"] for f in fr]) - 0.43) / 0.27 * 10.0         # 軸の下、長い波長ほど下
    for j, nm in enumerate((_t("単レンズの焦点 vs 波長(下へ行くほど長い波長)", "Singlet focus vs wavelength (down = longer)"),
                            _t("アクロマートの焦点 vs 波長", "Achromat focus vs wavelength"))):
        bfl0 = fr[0]["lens"][j]["bfl"]
        xs = np.array([img_w[j] + (f["lens"][j]["bfl"] - fr[0]["lens"][j]["bfl"]) * 4.0 for f in fr])
        xs = xs - (xs[np.argmin(np.abs([f["knob"] - WL_D for f in fr]))] - img_w[j])
        trails.append({"xyz": np.column_stack([xs, np.zeros(T), lifts[j] + ys]), "color": "#fff59d" if j == 0 else "#a5d6a7",
                       "tail": 0, "label": nm})
        del bfl0
    events = []
    for wl, ja, en in ((0.43, "430 nm(紫)", "430 nm (violet)"), (WL_F, "F 線 486 nm(青)", "F line 486 nm (blue)"),
                       (WL_D, "d 線 588 nm(設計の波長、像面はここ)", "d line 588 nm (design; the sensor is here)"),
                       (WL_C, "C 線 656 nm(赤): アクロマートは F と同じ焦点", "C line 656 nm: the achromat matches F")):
        kk = int(np.argmin(np.abs([f["knob"] - wl for f in fr])))
        if not events or t[kk] > events[-1]["t"]:
            events.append({"t": t[kk], "label": _t(ja, en)})
    events.append({"t": t[-1], "label": _t("限界: 二次スペクトル(アクロマートでも端の色はずれる)",
                                          "Limit: secondary spectrum (the ends still drift)")})
    d1 = np.array([f["lens"][0]["bfl"] - bfl_at(singlet(12.5), WL_D) for f in fr])
    d2 = np.array([f["lens"][1]["bfl"] - bfl_at(achromat(R3), WL_D) for f in fr])
    lim_mm = 2.0

    def cells(k, f):
        c1 = cell_chroma_curve(fr, k, lim_mm, R3)
        sp = [f["lens"][0]["spot"], f["lens"][1]["spot"]]
        col = wl_rgb(f["knob"])
        hw = max(half_window(sp, [], 4.0, f["knob"]), 8.0)
        return [c1, cell_spot(sp, hw, cols=[col, col]), cell_psf([f["lens"][0]["psf"], f["lens"][1]["psf"]], hw, [f["lens"][0]["pv"], f["lens"][1]["pv"]],
                         [f["lens"][0]["geo"], f["lens"][1]["geo"]]),
                cell_wave(f["lens"][0]["wmap"], f["lens"][0]["zern"])]

    def formula(f):
        return ["%.0f nm  singlet: bfl = R1/(n-1) - t/n = 51.68/%.5f - 9/%.5f = %.4f mm" % (
                    f["knob"] * 1000, f["n"] - 1, f["n"], f["bfl_th"]),
                "traced (paraxial_trace) %.4f mm   achromat shift %+.4f mm (singlet %+.4f)" % (
                    f["lens"][0]["bfl"], f["lens"][1]["bfl"] - bfl_at(achromat(R3), WL_D),
                    f["lens"][0]["bfl"] - bfl_at(singlet(12.5), WL_D))]
    series = [{"label": _t("単レンズの焦点のずれ(d 線から)", "Singlet focus shift (from d)"), "values": d1, "lo": -2.0,
               "hi": 1.0, "unit": "mm", "decimals": 3, "color": "#fff59d"},
              {"label": _t("アクロマートの焦点のずれ", "Achromat focus shift"), "values": d2, "lo": -2.0, "hi": 1.0,
               "unit": "mm", "decimals": 3, "color": "#a5d6a7"},
              {"label": _t("波長", "Wavelength"), "values": np.array([f["knob"] * 1000 for f in fr]), "lo": 430.0,
               "hi": 700.0, "unit": "nm", "decimals": 0, "color": "#ce93d8"}]
    fc_s = bfl_at(singlet(12.5), WL_F) - bfl_at(singlet(12.5), WL_C)
    fc_a = bfl_at(achromat(R3), WL_F) - bfl_at(achromat(R3), WL_C)
    nums = [fs.viewer_number(_t("上", "Top"), "N-BK7 singlet, f/4"),
            fs.viewer_number(_t("下", "Bottom"), "N-BK7 + N-SF2 achromat, R3 = %.2f mm" % R3),
            fs.viewer_number(_t("F−C の焦点差 単 / アクロ", "F−C focus difference singlet / achromat"),
                             _t("%.3f mm / %s" % (fc_s, fmt_fc(fc_a, "ja")), "%.3f mm / %s" % (fc_s, fmt_fc(fc_a, "en"))))]
    text = _t("色収差: ガラスの屈折率は色(波長)で違う(青ほど大きい)ので、単レンズ(上)は青い光ほど手前で焦点を結ぶ。"
              "下のアクロマートは、凸の BK7 と凹の SF2(色による屈折率の変わり方が違うガラス)を貼り合わせ、"
              "青(F 線)と赤(C 線)の焦点をそろえた。3-D の中の黄・緑の線は「焦点の位置(横、4 倍に拡大)対 波長(下へ行くほど長い)」のグラフ。"
              "アクロマートでも端の色は少しずれる(二次スペクトル)。",
              "Chromatic aberration: glass bends blue more than red, so the singlet (top) focuses blue closer. The "
              "achromat (bottom) cements a convex BK7 to a concave SF2 so the F (blue) and C (red) foci coincide. The "
              "yellow / green lines in 3-D plot focus position (across, magnified x4) against wavelength (longer downwards). Even the "
              "achromat drifts at the ends (secondary spectrum).")
    return tab_from(fr, t, "chroma", _t("色収差(波長)", "Chromatic (wavelength)"), "passed", text, rays_list, statics,
                    [], trails, clouds, events, series, cells, formula, nums, {"az": -1.25, "el": 0.18, "dist": 0.6},
                    ("1 paraxial_trace (focus)",) + STAGES[1:])


def cell_chroma_curve(fr, k, lim_mm, R3):
    """焦点のずれ vs 波長: 点 = paraxial_trace(単レンズ・アクロマート)、白い線 = 単レンズの閉形式。"""
    c = np.full((CW, CW, 3), 0.08)
    wl = np.array([f["knob"] for f in fr])
    b0 = fr[int(np.argmin(np.abs(wl - WL_D)))]

    def rc(w, d):
        return CW / 2 - d / lim_mm * (CW / 2 - 8), 6 + (w - 0.43) / 0.27 * (CW - 12)
    c[CW // 2, 4:CW - 4] = 0.3
    th = np.array([f["bfl_th"] for f in fr]) - b0["bfl_th"]
    r, cc = rc(wl, th)
    _poly(c, r, cc, (0.95, 0.95, 0.95))
    for j, colj in enumerate(((1.0, 0.96, 0.62), (0.65, 0.84, 0.65))):
        d = np.array([f["lens"][j]["bfl"] for f in fr]) - b0["lens"][j]["bfl"]
        for i in range(0, k + 1):
            rr, ccc = rc(wl[i], d[i])
            _px(c, rr, ccc, wl_rgb(wl[i]) if i == k else colj, 1.6 if i == k else 0.8)
    c = _text(c, "+-%g mm" % lim_mm, (3, 9), (0.75, 0.75, 0.75), 8)
    c = _text(c, "430-700 nm", (3, CW - 9), (0.75, 0.75, 0.75), 8)
    return c


# =========================================================================== 実行と検査
def run(quick=False):
    T = T_QUICK if quick else T_FULL
    t = np.arange(T) / FPS
    R3 = achromat_r3()
    return {"t": t, "R3": R3, "sph": record_spherical(T), "coma": record_coma(T), "astig": record_astig(T),
            "chroma": record_chroma(T, R3)}


def gates(rec):
    """理論の線(3 次の式・閉形式)と実光線の照合。戻り値 = 表示用の数字。失敗は AssertionError。"""
    out = {}
    # ---- 球面: 小さい絞りで 1 %、単調に開き、最後で 8 % 超
    gap = []
    for a in (1.5, 3.0, 4.0, 6.0, 9.0, 12.5, 16.0, 20.0):
        s = singlet(a)
        W = fs.seidel_coefficients(s, field=0.0)["wavefront_mm"]
        um = fs.paraxial_trace(s)["marginal"]["u"][-1]
        fan = fs.ray_fan(s, field=0.0, n=11)
        r = fan[-1, 1] / (4 * W["W040"] / um)
        gap.append((a, r))
        if a <= 4.0:
            assert abs(r - 1) < 0.01, ("球面: 小さい絞りで 3 次と合わない", a, r)
        if a <= 6.0:
            z = fs.wavefront_from_opd(s, n_max=6)["zernike"][(4, 0)]
            assert abs(6 * z / (W["W040"] / (WL_D * 1e-3)) - 1) < 0.03, ("球面: Z40", a, z)
    rs = [r for _a, r in gap]
    assert all(b > a for a, b in zip(rs, rs[1:])), ("球面: 比が単調でない", rs)
    assert rs[-1] > 1.08, ("球面: f/2.5 で 3 次から外れない(限界が見えない)", rs[-1])
    out["sph"] = gap
    # ---- コマ
    s = descartes()
    um = fs.paraxial_trace(s)["marginal"]["u"][-1]
    for f in (0.5, 1.0, 2.0):
        W = fs.seidel_coefficients(s, field=f)["wavefront_mm"]
        ft = fs.ray_fan(s, field=f, n=21, axis="y")
        sym = 0.5 * (ft[-1, 1] + ft[0, 1])
        th = 3 * W["W131"] / um
        assert abs(sym / th - 1) < 0.01, ("コマ: メリディオナル", f, sym, th)
        sc = coma_sagittal_y(s, f)
        assert f > 1.0 or abs(3 * sc / sym - 1) < 0.02, ("コマ: サジタル 1/3", f, sc / sym)
    st0 = fs.spot_stats(s, field=0.0)
    assert st0["geo_radius"] < 1e-3, ("コマ: 軸上で無収差でない", st0["geo_radius"])
    out["coma_axis_um"] = st0["geo_radius"] * 1000
    # ---- 非点
    s = stop_front()
    um = fs.paraxial_trace(s)["marginal"]["u"][-1]
    img = fs.paraxial_trace(s)["bfl"] + 29.0
    for f in (1.0, 2.0):
        W = fs.seidel_coefficients(s, field=f)["wavefront_mm"]
        PT, PS = diff_foci(s, f, 4.0)
        dzT, dzS = PT[2] - img, PS[2] - img
        tT, tS = -2 * (W["W220"] + W["W222"]) / um ** 2, -2 * W["W220"] / um ** 2
        tP = tS - 0.5 * (tT - tS)
        assert abs(dzT / tT - 1) < 0.01 and abs(dzS / tS - 1) < 0.01, ("非点: T/S", f, dzT, tT, dzS, tS)
        assert abs((dzT - tP) / (dzS - tP) / 3 - 1) < 0.02, ("非点: 3 対 1", f)
    # ---- 色
    s1 = singlet(12.5)
    for wl in (0.43, WL_F, WL_D, WL_C, 0.70):
        n = fs.refractive_index("N-BK7", wl)
        assert abs(bfl_at(s1, wl) - (51.68 / (n - 1) - 9.0 / n)) < 1e-9, ("色: 閉形式", wl)
    fc1 = bfl_at(s1, WL_F) - bfl_at(s1, WL_C)
    sd = fs.seidel_coefficients(s1)
    um = fs.paraxial_trace(s1)["marginal"]["u"][-1]
    assert abs(fc1 / (sd["total"]["C_L"] / um ** 2) - 1) < 0.015, ("色: C_L", fc1, sd["total"]["C_L"] / um ** 2)
    s2 = achromat(rec["R3"])
    fc2 = bfl_at(s2, WL_F) - bfl_at(s2, WL_C)
    assert abs(fc2) < 1e-6, ("色: アクロマートの F−C", fc2)
    wls = np.linspace(WL_F, WL_C, 15)
    sp1 = np.ptp([bfl_at(s1, w) for w in wls])
    sp2 = np.ptp([bfl_at(s2, w) for w in wls])
    assert sp2 < sp1 / 20, ("色: 二次スペクトルが大きい", sp1, sp2)
    out.update({"fc1": fc1, "fc2": fc2, "sec1": sp1, "sec2": sp2})
    # ---- 幾何の PSF: 回折の PSF も作れる重なりの領域で、集中半径が 12 % 以内
    out["geo_vs_diff"] = []
    for name, sys_, fd in (("sph f/3.6", singlet(14.0), 0.0), ("coma 4deg", descartes(), 4.0)):
        r50, r80 = geo_vs_diffraction(sys_, fd)
        assert abs(r50 - 1) < 0.12 and abs(r80 - 1) < 0.12, ("幾何の PSF が回折の PSF と合わない", name, r50, r80)
        out["geo_vs_diff"].append((name, r50, r80))
    return out


def encircled_radius(img, pitch_um, frac):
    """重心のまわりで、エネルギーの frac が入る半径 [µm]。"""
    n0, n1 = img.shape
    y = (np.arange(n0) - (n0 - 1) / 2) * pitch_um
    x = (np.arange(n1) - (n1 - 1) / 2) * pitch_um
    X, Y = np.meshgrid(x, y)
    tot = img.sum()
    cx, cy = (img * X).sum() / tot, (img * Y).sum() / tot
    r = np.hypot(X - cx, Y - cy).ravel()
    o = np.argsort(r)
    c = np.cumsum(img.ravel()[o])
    return float(r[o][np.searchsorted(c, frac * c[-1])])


def geo_vs_diffraction(system, field, n=200):
    """同じ視野で、幾何の PSF と ``psf_field_grid`` の回折の PSF を同じ格子に置き、50 %・80 % の集中半径の比を返す。"""
    g = geo_rays(system, field)
    pitch = 2.6 * float(np.abs(g["xy"]).max()) / n
    G = geo_psf(g, n, n, pitch)
    d = fs.psf_field_grid(system, fields=(field,), oversample=3)
    P, dx = d["psfs"][0], d["sample_um"][0]
    M = P.shape[0]
    gg = (np.arange(n) - (n - 1) / 2) * pitch
    jj = gg / dx + M // 2                                   # 列 = x
    ii = -gg / dx + M // 2                                  # 行 = −y(geo_psf と同じ向き)
    i0, j0 = np.floor(ii).astype(int), np.floor(jj).astype(int)
    fi, fj = (ii - i0)[:, None], (jj - j0)[None, :]

    def at(i, j):
        ok = (i[:, None] >= 0) & (i[:, None] < M) & (j[None, :] >= 0) & (j[None, :] < M)
        return np.where(ok, P[np.clip(i, 0, M - 1)[:, None], np.clip(j, 0, M - 1)[None, :]], 0.0)
    D = ((1 - fi) * (1 - fj) * at(i0, j0) + (1 - fi) * fj * at(i0, j0 + 1)
         + fi * (1 - fj) * at(i0 + 1, j0) + fi * fj * at(i0 + 1, j0 + 1))
    return tuple(encircled_radius(G, pitch, q) / encircled_radius(D, pitch, q) for q in (0.5, 0.8))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", help="HTML を残す先(省略すると一時フォルダに書いて検査だけ。そのときはコマを減らす)")
    ap.add_argument("--quick", action="store_true", help="コマを減らす(検査は同じ。--out と一緒に使える)")
    a = ap.parse_args(argv)
    rec = run(a.quick or not a.out)
    g = gates(rec)
    t = rec["t"]
    built = [tab_spherical(rec["sph"], t), tab_coma(rec["coma"], t), tab_astig(rec["astig"], t),
             tab_chroma(rec["chroma"], t, rec["R3"])]
    spec = fs.viewer_spec("anim3d_lens_aberrations", _t("レンズの収差を光線で見る", "Lens aberrations, ray by ray"),
                          _t("絞り・画角・波長をゆっくり振り、fullseye の光線追跡で追った光線と、スポット・PSF・波面を同じ時間軸で。",
                             "Sweep the stop, the field and the wavelength; rays traced by Fullseye with spot, PSF and "
                             "wavefront on the same time axis."),
                          _t("ドラッグで回転、ホイールで拡大。空白で再生/停止、← → でコマ送り。段のボタンで跳ぶ。",
                             "Drag to rotate, wheel to zoom. Space plays/pauses, arrow keys step. Stage buttons jump."),
                          [b[0] for b in built])
    with tempfile.TemporaryDirectory() as d:
        path = fs.write_viewer(spec, a.out or os.path.join(d, "ab.html"), ["ja", "en"])
        html = open(path, encoding="utf-8").read()
        size = os.path.getsize(path)
        data = json.loads(re.search(r"const D = (\{.*?\});\nconst \$ = ", html, re.S).group(1))
        A_ = data["arrays"]
        same = all(np.array_equal(pv._decode_array(A_[tb["panes"][0]["frames"]]), b[1])
                   for tb, b in zip(data["tabs"], built))
        # 光線の棒の端(戻した姿勢)が op の点に一致するか: 各棒の始点は P + u·off
        worst = 0.0
        for tb, b in zip(data["tabs"], built):
            bx = pv._decode_array(A_[tb["xyz"]])
            step = pv._quant_step(A_[tb["xyz"]])
            worst = max(worst, float(np.max(np.abs(bx - b[3]) / (step / 2))))
        assert same, "PNG で戻した帯が元と違う"
        assert worst <= 1.0 + 1e-9, worst
        assert "http://" not in html and "https://" not in html, "外部 URL がある"
    print("書いた: %s(%.0f KB、ja+en、4 タブ・各 %d コマ)" % (path if a.out else "一時フォルダ", size / 1e3, len(t)))
    print("球面: 実光線 / 3 次の式 = " + "  ".join("a=%g:%.3f" % (a_, r) for a_, r in g["sph"]))
    print("コマ: 軸上のスポット半径 %.2g µm(非球面の無収差)" % g["coma_axis_um"])
    print("色: F−C の焦点差 単レンズ %.3f mm / アクロマート %s、F..C の焦点のゆれ %.3f / %.4f mm"
          % (g["fc1"], fmt_fc(g["fc2"]), g["sec1"], g["sec2"]))
    print("限界(実光線 / 3 次の式): 球面 f/%.1f で %.3f、コマ %.0f° で %.3f、T 像面 %.0f° で %.3f"
          % (rec["sph"][-1]["fno"], rec["sph"][-1]["ta_real"] / rec["sph"][-1]["ta_th"], rec["coma"][-1]["knob"],
             rec["coma"][-1]["tc_real"] / rec["coma"][-1]["tc_th"], rec["astig"][-1]["knob"],
             rec["astig"][-1]["dzT"] / rec["astig"][-1]["dzT_th"]))
    for key, nm in (("sph", "球面"), ("coma", "コマ"), ("astig", "非点")):
        nn = sum(f["psf"] is None for f in rec[key])
        print("幾何の PSF に切り替えたコマ(%sのタブ): %d / %d(瞳の波面が数十波長で、回折の PSF は op の格子で折り返す)"
              % (nm, nn, len(rec[key])))
    print("幾何の PSF / 回折の PSF の集中半径(50 %・80 %): " + "  ".join(
        "%s %.3f・%.3f" % (k, r50, r80) for k, r50, r80 in g["geo_vs_diff"]))
    print("姿勢の復元は量子化の刻みの半分の %.2f 倍以内、帯の PNG は画素ごとに一致" % worst)
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
