# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""河川の水位を斜め写真から測る —— 透視を無視した「行番号」は弓なりに外れる。

    py -3.11 examples/poc_water_level.py

護岸の壁に量水標(既知間隔の目盛り)が貼ってあり、監視カメラが斜め上から
その壁を撮っている、という場面です。**真値は水位**(基準面からの高さ [m])。
水面は水平な平面なので水面線は世界では水平ですが、斜めから見ているので
**画像の上では傾いた直線**になり、しかも**行番号と高さの対応が線形ではない**。

EXTEND: 実写に差し替えるなら :func:`render` が返す画像を実画像に、
:data:`CAL_MARKS` を「測量済みの標定点(画像座標 ↔ 壁面座標)」の実測表に
置き換えます。カメラは固定・壁面は平面という前提だけが要ります。標定点は
**撮影時に見えている必要はありません**(据付時に一度測っておく量なので、
いま水没していてもかまわない —— この PoC もその前提で書いています)。

この PoC が示すこと(数字はすべて実行時に印字される実測値):

 1. ★★**「水位が高いほど誤差が大きくなる」という予想は外れた**。行番号を
    2 点の目盛りで線形に高さへ直す素朴法は、**弓なり**に外れる ——
    アンカー(0.00 / 2.00 m)の上では誤差 0、その間で最大 **-6.4 cm**
    (水位 1.0 m 付近)。単調ではありません。透視の写像は行 = (aZ+b)/(cZ+d)
    という一次分数関数で、直線で近似すると**弦と双曲線の差**になるからです。
 2. ★**符号を決めるのは水位ではなく「内挿か外挿か」**。同じ画像・同じ
    水面線でも、全 span(0.00/2.00 m)で較正した内挿は **-6.6 cm**(低く出る)、
    下ペア(0.00/0.50 m)で較正して水位 1.8 m を読む外挿は **+16.3 cm**、
    上ペア(1.50/2.00 m)で水位 0.2 m を読む外挿は **+14.6 cm** —— どちらの
    外挿も**逆符号**。「透視を無視すると高く出るのか低く出るのか」は
    水位ではなく**現場の較正表**が決めます。
 3. **4 点のホモグラフィで正対化すると誤差は 1 桁以上落ちる**(素朴法の
    最悪 6.4 cm に対して **0.21 cm**)。残っているのは透視の誤差ではなく
    **水面線の検出誤差**(0.12 px 相当)で、対照群(検出を使わず厳密な交点を
    入れる)では **4e-14 m** まで落ちます。
 4. ★**波立ちだけならロバスト当てはめは要らない**。零平均の波 ±4 cm では
    最小二乗もロバストもほぼ同じ(RANSAC は 1.11 倍)。効くのは**泡で検出が
    外れた列**が混ざったときで、そこでは RANSAC が最小二乗の **9.1 倍**良い。
    「ロバストにしておけば安心」ではなく、**外れ値があるときだけ効く**。
 5. ★★**同じ反射が、検出器によって正反対の顔を見せる**。しきい値交差の
    検出器は**静かに低く読む**(反射率 0.7 で **-18.9 cm**、対照群の反射率 0 は
    -0.03 cm)。同じ画像でキャリパー(勾配ピーク + 振幅の門)は、壁 -> 水の
    グレー差が 0.38 -> 0.12 と潰れて門を通らず、**検出できた列が 149 -> 9 に
    落ちて黙って止まる**。運用上、この 2 つはまったく別の故障です ——
    前者は監視では気づけません。
 6. 夜間の低コントラスト(コントラスト 1/4)では、雑音 σ=0.06 でも**偏りは
    1.3 mm しか動かず**、ばらつきが 1.5 -> 2.5 mm、検出できる列が 149 -> 131
    に減る。夜間の弱点は「ずれ」ではなく「揺れと歯抜け」でした。

来歴(公開文献のみ): Hartley & Zisserman, *Multiple View Geometry* 2nd ed.,
§4.1(4 点 DLT)/ 国土交通省「河川砂防技術基準」の量水標 /
Fischler & Bolles, *CACM* 24 (1981) 381 —— RANSAC。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 場面の諸元 -------------------------------------------------------------- #
W_PIX, H_PIX = 640, 512      # 監視カメラの画素数
F_PIX = 700.0                # 焦点距離 [px]
CAM = np.array([1.0, -6.0, 4.2])   # カメラ位置 [m](壁は Y=0 面、Z が高さ)
TGT = np.array([1.0, 0.0, 1.2])    # 光軸が壁を貫く点
X_GAUGE = 1.0                # 量水標の壁面上の位置 [m]
X_REF = 3.0                  # 標定用の十字がもう 1 本ある位置 [m]
Z_CAL = (0.0, 2.0)           # 標定点の高さ [m](据付時に測量してある)
TICK_DZ = 0.1                # 目盛りの間隔 [m]


def look_at(c: np.ndarray, t: np.ndarray) -> np.ndarray:
    """world -> camera の回転(行が camera 軸、y は画像下向き)。"""
    z = t - c
    z = z / np.linalg.norm(z)
    x = np.cross(z, np.array([0.0, 0.0, 1.0]))
    x = x / np.linalg.norm(x)
    y = np.cross(z, x)
    return np.stack([x, y, z], axis=0)


_R = look_at(CAM, TGT)
_K = np.array([[F_PIX, 0.0, W_PIX / 2.0], [0.0, F_PIX, H_PIX / 2.0], [0.0, 0.0, 1.0]])
#: 壁面 (X, Z, 1) -> 画像 (u, v, 1) のホモグラフィ。**真値の出どころ**。
H_TRUE = np.stack([_K @ _R[:, 0], _K @ _R[:, 2], -_K @ _R @ CAM], axis=1)
H_INV = np.linalg.inv(H_TRUE)


def w2i(x, z):
    """壁面座標 (X, Z) [m] -> 画像座標 (u, v) [px]。"""
    x = np.atleast_1d(np.asarray(x, np.float64))
    z = np.atleast_1d(np.asarray(z, np.float64))
    x, z = np.broadcast_arrays(x, z)
    p = H_TRUE @ np.stack([x.ravel(), z.ravel(), np.ones(x.size)])
    return (p[0] / p[2]).reshape(x.shape), (p[1] / p[2]).reshape(x.shape)


def i2w(u, v, hmat=None):
    """画像座標 -> 壁面座標。``hmat`` を渡すとその推定ホモグラフィを使う。"""
    hin = H_INV if hmat is None else np.linalg.inv(np.asarray(hmat, np.float64))
    u = np.atleast_1d(np.asarray(u, np.float64))
    v = np.atleast_1d(np.asarray(v, np.float64))
    p = hin @ np.stack([u.ravel(), v.ravel(), np.ones(u.size)])
    return (p[0] / p[2]).reshape(u.shape), (p[1] / p[2]).reshape(u.shape)


#: 標定点 —— (X, Z, u, v)。4 点が同一直線に乗らないよう 2 本の柱から取る。
CAL_MARKS = [(x, z, float(w2i(x, z)[0][0]), float(w2i(x, z)[1][0]))
             for x in (X_GAUGE, X_REF) for z in Z_CAL]


# --------------------------------------------------------------------------- #
# 壁面の見え方 —— (X, Z) の**関数**として書く(反射を厳密に作るため)         #
# --------------------------------------------------------------------------- #
def wall_albedo(x: np.ndarray, z: np.ndarray) -> np.ndarray:
    """護岸の壁の反射率。目地 + コンクリートの斑 + 量水標。"""
    t = 0.58 + 0.045 * np.sin(6.1 * x + 1.3) * np.sin(4.7 * z + 0.4)
    t = t + 0.030 * np.sin(23.0 * x + 2.0) + 0.026 * np.sin(31.0 * z + 0.7)
    t = t + 0.018 * np.sin(53.0 * x + 11.0 * z)
    t = t - 0.10 * (np.abs(((z + 0.25) % 0.5) - 0.25) < 0.012)      # 水平目地
    t = t - 0.08 * (np.abs(((x + 0.5) % 1.0) - 0.5) < 0.012)        # 垂直目地
    # 量水標(白地に黒の目盛り)。0.1 m ごとに短い黒帯、0.5 m ごとに長い黒帯。
    on_gauge = np.abs(x - X_GAUGE) < 0.06
    dz = np.abs(((z + TICK_DZ / 2) % TICK_DZ) - TICK_DZ / 2)
    minor = (dz < 0.016) & (np.abs(x - X_GAUGE) < 0.030)
    dz5 = np.abs(((z + 0.25) % 0.5) - 0.25)
    major = (dz5 < 0.022) & on_gauge
    t = np.where(on_gauge, 0.90, t)
    t = np.where(minor | major, 0.12, t)
    # 標定用の十字(X_REF の柱)
    for _, zc in [(X_REF, z0) for z0 in Z_CAL]:
        cross = ((np.abs(x - X_REF) < 0.10) & (np.abs(z - zc) < 0.015)) | \
                ((np.abs(x - X_REF) < 0.015) & (np.abs(z - zc) < 0.10))
        t = np.where(cross, 0.10, t)
    return t


def render(level: float, refl: float = 0.0, wave_amp: float = 0.0,
           foam: bool = False, noise: float = 0.0, gain: float = 1.0,
           ss: int = 2, seed: int = 7) -> np.ndarray:
    """斜めから見た護岸を描く。**真値は ``level``(平均水位 [m])**。

    反射は「水面(Z=level の水平面)に対する鏡像」。壁は鉛直なので、鏡像は
    **同じ壁面の Z -> 2*level - Z** に厳密に一致します(鉛直面を水平面で
    折り返しても面は変わらない)—— だから補間なしで厳密に描けます。

    ``gain`` は夜間の低コントラスト(1 未満で壁と水の差が縮む)。
    """
    off = (np.arange(ss) + 0.5) / ss - 0.5
    uu = (np.arange(W_PIX)[None, :, None, None] + off[None, None, None, :])
    vv = (np.arange(H_PIX)[:, None, None, None] + off[None, None, :, None])
    uu, vv = np.broadcast_arrays(uu, vv)
    x, z = i2w(uu, vv)

    zs = np.full_like(z, float(level))
    if wave_amp > 0.0:
        zs = zs + wave_amp * (np.sin(2.3 * x + 0.4) + 0.6 * np.sin(5.7 * x + 1.9)
                              + 0.4 * np.sin(11.3 * x + 3.1)) / 2.0
    above = z > zs
    wall = wall_albedo(x, z)
    val = np.where(above, wall, 0.0)
    if not above.all():
        depth = np.maximum(zs - z, 0.0)
        mirror = wall_albedo(x, 2.0 * zs - z)
        water = 0.18 + 0.03 * np.sin(9.0 * x + 40.0 * z)
        water = water + refl * mirror * np.exp(-depth / 0.30)
        val = np.where(above, val, water)
    if foam:
        # 泡(白波)—— 水面直下の一部の列だけが白く光る。検出を壊す外れ値の源。
        band = (np.sin(1.7 * x + 0.9) > 0.55) | (np.sin(4.1 * x - 2.2) > 0.80)
        near = (z <= zs) & (z > zs - 0.22)
        val = np.where(band & near, 0.86, val)
    img = val.mean(axis=(2, 3))
    img = 0.5 + gain * (img - 0.5)
    if noise > 0.0:
        img = img + np.random.default_rng(seed).normal(0.0, noise, img.shape)
    return np.clip(img, 0.0, 1.0)


# --------------------------------------------------------------------------- #
# 水面線の検出 —— 列ごとに「明->暗」の交差をサブピクセルで拾う                 #
# --------------------------------------------------------------------------- #
#: 検出に使う列(量水標と標定十字の柱は黒帯があるので**外す**)
def _detect_cols() -> np.ndarray:
    ug = w2i(X_GAUGE, 1.0)[0][0]
    ur = w2i(X_REF, 1.0)[0][0]
    cols = np.arange(40, W_PIX - 40, 3)
    keep = (np.abs(cols - ug) > 26) & (np.abs(cols - ur) > 30)
    return cols[keep]


def detect_caliper(img: np.ndarray) -> np.ndarray:
    """★fullseye の**キャリパー**で水面線を拾う -> (row, col)。

    ``fs.ledger.gen_measure_rectangle2`` で列ごとに鉛直な測定矩形を立て、
    ``fs.ledger.measure_pos`` の**負極性エッジ**(下へ向かって暗くなる = 壁 -> 水)の
    うち上から最初のものを採る。振幅のしきい値は画像の分位点から決める
    (真値を見ない)。目地(振幅 0.10)は落ち、壁 -> 水(0.38)は残る。
    """
    lo, hi = np.percentile(img, [15.0, 85.0])
    thr = max(0.45 * float(hi - lo), 1e-4)
    pts = []
    for c in _detect_cols():
        m = fs.ledger.gen_measure_rectangle2(H_PIX / 2.0, float(c), np.pi / 2.0,
                                             (H_PIX - 8) / 2.0, 3, (H_PIX, W_PIX))
        edges = fs.ledger.measure_pos(img, m, sigma=1.2, threshold=thr,
                                      transition="negative")
        edges = [e for e in edges if e["row"] > 8.0]
        if not edges:
            continue
        pts.append((float(edges[0]["row"]), float(c)))
    return np.asarray(pts, np.float64).reshape(-1, 2)


def detect_threshold(img: np.ndarray) -> np.ndarray:
    """対照の検出器 —— 現場でまず書かれる「明るさが半分を切った行」。

    キャリパーが**勾配のピーク**を探すのに対し、こちらは**しきい値の交差**を
    探す。反射があるとこの違いが効きます(5 節)。
    """
    lo, hi = np.percentile(img, [15.0, 85.0])
    thr = 0.5 * float(lo + hi)
    k = np.ones(5) / 5.0
    cols = _detect_cols()
    sm = np.apply_along_axis(lambda a: np.convolve(a, k, mode="same"), 0, img[:, cols])
    below = sm < thr
    trans = below[1:] & ~below[:-1]
    trans[:9] = False
    has = trans.any(axis=0)
    r = trans.argmax(axis=0)
    j = np.arange(len(cols))
    a, b = sm[r, j], sm[r + 1, j]
    frac = np.where(np.abs(a - b) < 1e-9, 0.0, (a - thr) / (a - b + 1e-12))
    row = r + np.clip(frac, 0.0, 1.0)
    return np.column_stack([row[has], cols[has]]).astype(np.float64)


def detect_waterline(img: np.ndarray, how: str = "caliper") -> np.ndarray:
    """水面線の点列 (row, col)。``how`` = caliper(既定)/ threshold。"""
    return detect_caliper(img) if how == "caliper" else detect_threshold(img)


def _line_from_two(p, q):
    """2 点 (u, v) を通る画像直線の同次表現。"""
    return np.cross(np.array([p[0], p[1], 1.0]), np.array([q[0], q[1], 1.0]))


def cross_at_gauge(cy: float, cx: float, dy: float, dx: float) -> tuple[float, float]:
    """水面線(点 + 方向、(row, col))と量水標の像との交点 (u, v)。"""
    p0 = (float(w2i(X_GAUGE, 0.0)[0][0]), float(w2i(X_GAUGE, 0.0)[1][0]))
    p1 = (float(w2i(X_GAUGE, 2.4)[0][0]), float(w2i(X_GAUGE, 2.4)[1][0]))
    lg = _line_from_two(p0, p1)
    lw = _line_from_two((cx, cy), (cx + dx, cy + dy))
    h = np.cross(lg, lw)
    return float(h[0] / h[2]), float(h[1] / h[2])


def fit_waterline(pts: np.ndarray, how: str = "tls") -> tuple[float, float]:
    """水面線を当てはめて量水標との交点 (u, v) を返す。``how`` = tls / trim / ransac。"""
    if how == "ransac":
        p3 = np.column_stack([pts, np.zeros(len(pts))])
        par, _mask, _info = fs.ledger.ransac_line(p3, 2.0, iters=400, seed=3)
        cy, cx = float(par["point"][0]), float(par["point"][1])
        dy, dx = float(par["direction"][0]), float(par["direction"][1])
        return cross_at_gauge(cy, cx, dy, dx)
    f = fs.fit_line(pts)
    if how == "trim":
        dy, dx = f["dy"], f["dx"]
        res = (pts[:, 0] - f["cy"]) * dx - (pts[:, 1] - f["cx"]) * dy
        mad = np.median(np.abs(res - np.median(res))) + 1e-9
        keep = np.abs(res - np.median(res)) < 2.5 * 1.4826 * mad
        if keep.sum() >= 3:
            f = fs.fit_line(pts[keep])
    return cross_at_gauge(f["cy"], f["cx"], f["dy"], f["dx"])


# --------------------------------------------------------------------------- #
# 2 つの読み方                                                                  #
# --------------------------------------------------------------------------- #
def naive_level(v: float, anchors: tuple[float, float]) -> float:
    """★ゼロ点 —— **行番号**を 2 つの目盛りで線形に高さへ直す(透視を無視)。"""
    z1, z2 = anchors
    v1 = float(w2i(X_GAUGE, z1)[1][0])
    v2 = float(w2i(X_GAUGE, z2)[1][0])
    return z1 + (z2 - z1) * (v1 - v) / (v1 - v2)


def homography_from_marks(marks=None) -> np.ndarray:
    """4 点対応から DLT でホモグラフィを解く(``fs.mat_svd`` の右零空間)。"""
    ms = CAL_MARKS if marks is None else marks
    rows = []
    for x, z, u, v in ms:
        rows.append([-x, -z, -1.0, 0.0, 0.0, 0.0, u * x, u * z, u])
        rows.append([0.0, 0.0, 0.0, -x, -z, -1.0, v * x, v * z, v])
    _u, _s, vt = fs.mat_svd(np.asarray(rows, np.float64), full_matrices=True)
    h = vt[-1].reshape(3, 3)
    return h / h[2, 2]


def rectified_level(u: float, v: float, hmat: np.ndarray) -> float:
    """★対比 —— ホモグラフィで正対化して**壁面座標の Z** をそのまま読む。"""
    return float(i2w(u, v, hmat)[1][0])


# --------------------------------------------------------------------------- #
# 1. 合成器の検算                                                               #
# --------------------------------------------------------------------------- #
def section_sanity() -> None:
    print("\n" + "=" * 78)
    print("1) 合成器の検算 —— 真値が本当に厳密か")
    print("=" * 78)
    x0 = np.array([0.3, 1.0, 2.7, 3.4])
    z0 = np.array([0.1, 1.2, 2.0, 0.7])
    u, v = w2i(x0, z0)
    xr, zr = i2w(u, v)
    err = float(np.max(np.abs(np.stack([xr - x0, zr - z0]))))
    print("  ホモグラフィの往復誤差 %.2e m" % err)
    assert err < 1e-9

    hhat = homography_from_marks()
    dh = float(np.max(np.abs(hhat - H_TRUE / H_TRUE[2, 2])))
    print("  4 点 DLT が真の H を復元する誤差 %.2e" % dh)
    assert dh < 1e-6

    # 水面線 (Z=h の直線) は画像の上でも厳密に直線
    xs = np.linspace(-0.5, 4.0, 40)
    uu, vv = w2i(xs, np.full_like(xs, 1.1))
    r = fs.fit_line(np.column_stack([vv, uu]))["rms"]
    print("  Z=1.1 m の水面線を画像で直線当てはめした残差 %.2e px" % r)
    assert r < 1e-9

    # 反射は Z -> 2h-Z の厳密な鏡像(壁が鉛直、水面が水平だから)
    h = 1.0
    a = wall_albedo(np.array([2.0]), np.array([1.4]))
    b = wall_albedo(np.array([2.0]), np.array([2 * h - 0.6]))
    print("  鏡像の検算 wall(Z=1.4) == wall(2h-0.6) : %.6f == %.6f" % (a[0], b[0]))
    assert abs(a[0] - b[0]) < 1e-12
    print("  -> 真値(水位)も、反射の作り方も、補間を一度も通していない。")


# --------------------------------------------------------------------------- #
# 2. ★ゼロ点 vs ホモグラフィ                                                   #
# --------------------------------------------------------------------------- #
LEVELS = np.round(np.arange(0.2, 1.81, 0.2), 2)


def section_zero_point() -> dict:
    print("\n" + "=" * 78)
    print("2) ★ゼロ点(行番号 + 線形目盛り)vs ホモグラフィ正対化")
    print("=" * 78)
    print("  水位[m]  ゼロ点[m]   誤差      ホモグラフィ   誤差     検出のずれ[px]")

    hhat = homography_from_marks()
    naive_err, homo_err, model_err, det_px = [], [], [], []
    for h in LEVELS:
        img = render(float(h))
        pts = detect_waterline(img)
        u, v = fit_waterline(pts, "tls")
        ue, ve = float(w2i(X_GAUGE, h)[0][0]), float(w2i(X_GAUGE, h)[1][0])
        n = naive_level(v, (0.0, 2.0))
        r = rectified_level(u, v, hhat)
        # 対照群: 検出を使わず**厳密な交点**を入れる -> 透視の模型誤差だけが残る
        m = naive_level(ve, (0.0, 2.0))
        naive_err.append(n - h)
        homo_err.append(r - h)
        model_err.append(m - h)
        det_px.append(v - ve)
        print("   %4.2f    %7.4f  %+7.4f    %7.4f  %+7.4f     %+6.3f" % (
            h, n, n - h, r, r - h, v - ve))

    i = int(np.argmax(np.abs(naive_err)))
    print("\n  ★ゼロ点の誤差は**単調ではなく弓なり**。最大 %+.4f m(水位 %.2f m)、"
          % (naive_err[i], LEVELS[i]))
    print("    アンカー(%.2f / %.2f m)の上では 0 に戻る。行 = (aZ+b)/(cZ+d) を"
          % Z_CAL)
    print("    直線で近似した**弦と双曲線の差**なので、内挿の範囲では符号が一定。")
    print("  ホモグラフィの誤差は最大 %+.4f m。うち透視の模型誤差は %.1e m で、"
          % (homo_err[int(np.argmax(np.abs(homo_err)))], float(np.max(np.abs(
              [rectified_level(*w2i(X_GAUGE, h), hhat) - h for h in LEVELS])))))
    print("    残りは**水面線の検出誤差**(%.3f px 相当)。" % float(np.mean(np.abs(det_px))))
    return {"naive": naive_err, "homo": homo_err, "model": model_err, "det": det_px}


# --------------------------------------------------------------------------- #
# 3. ★アンカーの位置で符号が変わる                                             #
# --------------------------------------------------------------------------- #
ANCHOR_SETS = {"下ペア 0.00/0.50": (0.0, 0.5),
               "全span 0.00/2.00": (0.0, 2.0),
               "上ペア 1.50/2.00": (1.5, 2.0)}


def section_anchors() -> dict:
    print("\n" + "=" * 78)
    print("3) ★目盛りのどこで較正するかで**誤差の符号が変わる**")
    print("=" * 78)
    print("  水位[m] " + "".join("  %-16s" % k for k in ANCHOR_SETS))

    out = {k: [] for k in ANCHOR_SETS}
    for h in LEVELS:
        ve = float(w2i(X_GAUGE, h)[1][0])       # 検出誤差を混ぜない(模型だけ見る)
        line = "   %4.2f  " % h
        for k, a in ANCHOR_SETS.items():
            e = naive_level(ve, a) - h
            out[k].append(e)
            line += "     %+8.4f    " % e
        print(line)
    for k in ANCHOR_SETS:
        e = np.asarray(out[k])
        print("  %-16s 最大 %+.4f m / 平均 %+.4f m" % (k, e[np.argmax(np.abs(e))], e.mean()))
    print("\n  ★下のペアで較正して高い水位を読むと**外挿**になり、誤差は水位とともに")
    print("    単調に増える(+%.1f cm)。全 span の内挿では逆符号(%.1f cm)。"
          % (100 * max(out["下ペア 0.00/0.50"]), 100 * min(out["全span 0.00/2.00"])))
    print("    「透視を無視すると高く出るのか低く出るのか」は較正表しだい。")
    return out


# --------------------------------------------------------------------------- #
# 4. ★波立ち —— ロバストが効くのは外れ値があるときだけ                          #
# --------------------------------------------------------------------------- #
def section_waves() -> dict:
    print("\n" + "=" * 78)
    print("4) ★波立ち: 最小二乗 vs トリム vs RANSAC(泡の有無を対照群にする)")
    print("=" * 78)
    print("  条件            当てはめ    水位誤差[m]  |誤差| 平均   最小二乗比")

    hhat = homography_from_marks()
    res = {}
    for cond, (amp, foam) in {"波のみ ±4 cm": (0.04, False),
                              "波 + 泡": (0.04, True)}.items():
        base = None
        for how in ("tls", "trim", "ransac"):
            errs = []
            for h in (0.6, 1.0, 1.4):
                img = render(h, wave_amp=amp, foam=foam)
                pts = detect_waterline(img)
                u, v = fit_waterline(pts, how)
                errs.append(rectified_level(u, v, hhat) - h)
            m = float(np.mean(np.abs(errs)))
            base = m if how == "tls" else base
            res[(cond, how)] = m
            print("  %-14s  %-8s   %+8.4f     %7.4f      %5.2f x" % (
                cond, how, errs[1], m, base / m if m > 0 else float("nan")))

    r1 = res[("波のみ ±4 cm", "tls")] / res[("波のみ ±4 cm", "ransac")]
    r2 = res[("波 + 泡", "tls")] / res[("波 + 泡", "ransac")]
    print("\n  ★波だけなら RANSAC は最小二乗の %.2f 倍 —— **効いていない**"
          "(零平均の波は平均で消える)。" % r1)
    print("    泡で検出が外れる列が混ざると %.1f 倍。ロバストは「安心のため」ではなく"
          % r2)
    print("    **外れ値があるときだけ**効く道具です。")
    return res


# --------------------------------------------------------------------------- #
# 5. ★★反射 —— 系統的に低く出る                                               #
# --------------------------------------------------------------------------- #
def section_reflection() -> dict:
    print("\n" + "=" * 78)
    print("5) ★★護岸が水面に映ると —— 2 つの検出器が**別の壊れ方**をする")
    print("=" * 78)
    print("  反射率  [しきい値交差] 平均誤差   検出列   [キャリパー] 平均誤差   検出列")

    hhat = homography_from_marks()
    out, rate = {}, {}
    ncol = len(_detect_cols())
    for refl in (0.0, 0.25, 0.5, 0.7):
        row = {}
        for how in ("threshold", "caliper"):
            errs, ns = [], []
            for h in (0.6, 1.0, 1.4):
                img = render(h, refl=refl)
                pts = detect_waterline(img, how)
                ns.append(len(pts))
                if len(pts) < 3:
                    continue
                u, v = fit_waterline(pts, "trim")
                errs.append(rectified_level(u, v, hhat) - h)
            row[how] = (float(np.mean(errs)) if errs else float("nan"),
                        int(np.mean(ns)))
        out[refl] = [row["threshold"][0], row["caliper"][0]]
        rate[refl] = [row["threshold"][1], row["caliper"][1]]
        print("   %4.2f        %+8.4f m       %3d/%d        %+8.4f m       %3d/%d" % (
            refl, row["threshold"][0], row["threshold"][1], ncol,
            row["caliper"][0], row["caliper"][1], ncol))

    print("\n  ★★**同じ物理現象が、検出器によって逆の顔を見せる**。")
    print("   * しきい値交差は**系統的に低く**読む(%.2f -> %.2f m)。水面直下は"
          % (out[0.0][0], out[0.7][0]))
    print("     壁の鏡像なので明るく、交差点が下へ落ちるから。対照群(反射率 0)は")
    print("     %+.4f m なので、これは反射の効果です。**偏りは片方向なので"
          % out[0.0][0])
    print("     何枚平均しても消えません**。")
    print("   * キャリパー(勾配ピーク + 振幅の門)は**見失う** —— 壁 -> 水の")
    print("     グレー差が 0.38 -> 0.12 と潰れて門を通らず、検出列が %d -> %d に落ちる。"
          % (rate[0.0][1], rate[0.7][1]))
    print("     「静かに嘘をつく」のと「黙って落ちる」のは、運用上まったく別の")
    print("     故障です。前者は監視で気づけません。")
    return out


# --------------------------------------------------------------------------- #
# 6. 夜間 —— 低コントラスト                                                     #
# --------------------------------------------------------------------------- #
def section_night() -> dict:
    print("\n" + "=" * 78)
    print("6) 夜間(コントラスト 1/4)+ 雑音 —— 偏りではなくばらつきが増える")
    print("=" * 78)
    print("   雑音σ   誤差の平均[m]   誤差の標準偏差[m]   検出できた列")

    hhat = homography_from_marks()
    out = {}
    for sig in (0.0, 0.01, 0.03, 0.06):
        errs, ncol = [], []
        for k, h in enumerate((0.6, 1.0, 1.4)):
            img = render(h, gain=0.25, noise=sig, seed=17 + k)
            pts = detect_waterline(img)
            ncol.append(len(pts))
            u, v = fit_waterline(pts, "trim")
            errs.append(rectified_level(u, v, hhat) - h)
        out[sig] = errs
        print("   %5.3f    %+9.4f        %9.4f          %4d / %d" % (
            sig, float(np.mean(errs)), float(np.std(errs)),
            int(np.mean(ncol)), len(_detect_cols())))
    print("\n  偏りはほぼ動かず、ばらつきが σ とともに増える —— 夜間の弱点は"
          "「ずれ」ではなく「揺れ」。")
    return out


# --------------------------------------------------------------------------- #
# 7. 図                                                                         #
# --------------------------------------------------------------------------- #
def section_figures(zp: dict, anc: dict, refl: dict) -> None:
    if not figs.enabled():
        return
    day = render(1.0, ss=3)
    mir = render(1.0, refl=0.7, ss=3)
    figs.save_grid("scene", [day, mir, mir - day],
                   ["昼 (反射なし)", "反射 0.7", "差"],
                   title="斜めから見た護岸と量水標 (水位 1.00 m)",
                   signed=[False, False, True])

    figs.save_plot("bias_vs_level",
                   [("ゼロ点(行番号)", LEVELS, np.asarray(zp["naive"]) * 100),
                    ("うち透視の模型誤差", LEVELS, np.asarray(zp["model"]) * 100),
                    ("ホモグラフィ", LEVELS, np.asarray(zp["homo"]) * 100),
                    ("誤差ゼロ", LEVELS, np.zeros_like(LEVELS))],
                   xlabel="真の水位 [m]", ylabel="水位の誤差 [cm]",
                   title="透視を無視すると弓なりに外れる")

    figs.save_plot("anchors",
                   [(k, LEVELS, np.asarray(v) * 100) for k, v in anc.items()]
                   + [("誤差ゼロ", LEVELS, np.zeros_like(LEVELS))],
                   xlabel="真の水位 [m]", ylabel="水位の誤差 [cm]",
                   title="較正に使う目盛りのペアで符号が変わる")

    rows = [["%.2f" % r, "%+.1f" % (100 * v[0]), "%+.1f" % (100 * v[1])]
            for r, v in refl.items()]
    figs.save_table("reflection", ["反射率", "しきい値交差 [cm]", "キャリパー [cm]"],
                    rows, title="反射があるときの水位誤差(負 = 低く読む / nan = 見失う)")


# --------------------------------------------------------------------------- #
# 8. 道具の穴                                                                   #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("7) 道具の穴(この PoC で 3 層すべて引いてみて)")
    print("=" * 78)

    # (a) 4 点対応 -> ホモグラフィを解く口が無い(HALCON の vector_to_proj_hom_mat2d)
    for name in ("vector_to_proj_hom_mat2d", "homography_from_points",
                 "find_homography", "fit_homography"):
        assert not hasattr(fs, name), name
        assert not hasattr(fs.ledger, name), name
    assert hasattr(fs.ledger, "warp_by_plane"), "H を**使う**口はある"
    print("  (a) ホモグラフィを**使う**口(ledger.warp_by_plane)はあるのに、")
    print("      **4 点対応から解く**口が 3 層のどこにも無い。この PoC は")
    print("      fs.mat_svd で DLT を自前で書いた(20 行)。族に入れる価値がある。")

    # (b) 射影変換 op はホモグラフィを受け取れない(台形 1 パターンの近似)
    import ops
    op = {o.name: o for o in ops.REGISTRY}["projective_trans_image"]
    assert "台形" in (op.doc or ""), op.doc
    print("  (b) 進化 op の projective_trans_image は**台形歪み 1 パターン**で、")
    print("      任意の H を渡せない(doc にもそう書いてある)。正対化には使えない。")

    # (c) 2-D の RANSAC 直線が無い(ransac_line は (N,3) 専用)
    assert hasattr(fs.ledger, "ransac_line")
    try:
        fs.ledger.ransac_line(np.zeros((10, 2)), 1.0)
        raise AssertionError("2-D を受けるようになった(この節を書き換えること)")
    except (ValueError, IndexError, AssertionError) as exc:
        assert not isinstance(exc, AssertionError) or "書き換え" not in str(exc), exc
    print("  (c) ledger.ransac_line は (N,3) 専用。画像の直線は (N,2) なので")
    print("      呼び手が毎回 z=0 を足している。fit_line(2-D TLS)には")
    print("      ロバスト版が無い。")

    # (d) キャリパーは在った(★「無い」と書きかけて 3 層引いて見つけた)
    assert hasattr(fs.ledger, "measure_pos") and hasattr(fs.ledger, "gen_measure_rectangle2")
    assert not hasattr(fs, "measure_pos"), "ファサードに出た(この節を書き換えること)"
    print("  (d) ★サブピクセル・エッジは**在った**(ledger.measure_pos + ")
    print("      gen_measure_rectangle2 = HALCON のキャリパー)。この PoC は最初")
    print("      「無い」と書きかけて自前の線形内挿を使っていた —— 3 層引いて")
    print("      見つけたので差し替えた。ただし**測定線を束ねて 1 本の直線に")
    print("      当てる口**(fit_line_measure に当たるもの)は無く、呼び手が")
    print("      列ごとに measure_pos を呼んで自分で束ねている。")

    # (e) 台帳にあるのにファサードに出ていない
    assert hasattr(fs.ledger, "warp_by_plane") and not hasattr(fs, "warp_by_plane")
    print("  (e) warp_by_plane / ransac_line / measure_pos は fullseye.ledger から")
    print("      しか呼べない(1 行ファサードの規約とは食い違っている)。")


# --------------------------------------------------------------------------- #
def main() -> None:
    t0 = time.perf_counter()
    print("=" * 78)
    print("河川の水位を斜め写真から測る —— 透視を無視した行番号は弓なりに外れる")
    print("カメラ %.1f m 手前・%.1f m 上 / 画像 %d x %d / 量水標 %.1f m ごとの目盛り"
          % (-CAM[1], CAM[2], W_PIX, H_PIX, TICK_DZ))
    print("=" * 78)

    section_sanity()
    zp = section_zero_point()
    anc = section_anchors()
    section_waves()
    refl = section_reflection()
    section_night()
    section_figures(zp, anc, refl)
    section_tool_gaps()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 透視を無視した行番号の誤差は**単調でなく弓なり**(最大 %.1f cm)。"
          % (100 * max(abs(e) for e in zp["naive"])))
    print("  * その符号は**較正に使った目盛りのペア**で反転する(内挿 vs 外挿)。")
    print("  * 4 点ホモグラフィなら %.1f cm 以下。残りは検出誤差で、透視ではない。"
          % (100 * max(abs(e) for e in zp["homo"])))
    print("  * ロバスト当てはめは**外れ値があるときだけ**効く(波だけなら無意味)。")
    print("  * 反射の偏りは片方向(低く読む)なので、枚数を増やしても消えない。")
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
