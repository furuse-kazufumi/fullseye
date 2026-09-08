# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""(placeholder docstring — filled in after the first full run)"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy.interpolate import LinearNDInterpolator, RBFInterpolator
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

_L = fs.ledger

# --- 部屋(長さ m、温度 °C)-------------------------------------------------- #
LX, LY, LZ = 12.0, 8.4, 3.0     # x = アイル方向 / y = アイルを横切る / z = 高さ
T_AMB = 24.0                    # 室の基準温度

# ホットアイル(2 列のラック排気が集まる帯)。上ほど熱い。
HOT_Y, HOT_S, HOT_A = 4.2, 0.9, 5.0
# コールドアイル(床のパンチングタイルからの吹き出し)。床際だけ冷たい。
COLD_Y, COLD_S, COLD_A, COLD_H = (1.4, 7.0), 0.7, 5.5, 0.9

#: 過負荷ラック(名前, x, y, z [m], σ [m], 振幅 [°C])。**これが探すもの**。
HOTSPOTS = [
    ("R-A07 広いプルーム", 2.60, 4.20, 2.35, 0.55, 7.0),
    ("R-B14 中位",         6.35, 4.05, 2.05, 0.35, 9.0),
    ("R-C21 排気閉塞",     9.85, 4.35, 2.30, 0.22, 11.0),
]

NOISE = 0.15        # センサ雑音 σ [°C](DC 用温湿度センサの実力 ±0.5 °C 相当)
SEED = 11
DETECT = 32.0       # 「熱い」と呼ぶしきい値 [°C](ASHRAE class A1 allowable の上限)

EV = 0.25           # 評価格子の刻み [m]
GX = np.arange(0.0, LX + 1e-9, EV)
GY = np.arange(0.0, LY + 1e-9, EV)
GZ = np.arange(0.0, LZ + 1e-9, EV)
#: 評価点 (nz*ny*nx, 3)。体積 op に渡すため **(z, y, x) 順の volume** にも組み直す。
GRID = np.stack(np.meshgrid(GX, GY, GZ, indexing="ij"), -1).reshape(-1, 3)
VOL_SHAPE = (GZ.size, GY.size, GX.size)

METHODS = ("null", "nearest", "linear", "rbf")
MET_LABEL = {"null": "ゼロ点(全センサの平均)", "nearest": "最近傍",
             "linear": "線形(Delaunay)", "rbf": "RBF(薄板スプライン)"}


# --------------------------------------------------------------------------- #
# 真値 —— 温度場 T(x, y, z) を式で置く                                          #
# --------------------------------------------------------------------------- #
def field(p, drop=None):
    """温度 [°C]。``drop`` はその番号のホットスポットだけ止める(対照群用)。

    ``T = 室温 + ホットアイルの帯 - コールドアイルの吹き出し + Σ ラックのプルーム``。
    帯は上ほど熱く(排気が天井へ上がる)、吹き出しは床際だけ効く(``exp(-z/h)``)。
    ラックのプルームは等方ガウス —— ここだけ**等方**にしてあるのは、崖の閉形式
    ``exp(-3d²/8σ²)`` が等方のときちょうど成り立つからで、実際のプルームは
    上へ伸びた異方形。異方なら ``exp(-(d²/8)(1/σx²+1/σy²+1/σz²))`` に置き換わる。
    """
    p = np.asarray(p, float)
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    t = T_AMB + HOT_A * np.exp(-(y - HOT_Y) ** 2 / (2 * HOT_S ** 2)) * (0.5 + 0.5 * z / LZ)
    for cy in COLD_Y:
        t = t - COLD_A * np.exp(-(y - cy) ** 2 / (2 * COLD_S ** 2)) * np.exp(-z / COLD_H)
    for i, (_, cx, cy2, cz, s, a) in enumerate(HOTSPOTS):
        if drop is not None and i == drop:
            continue
        r2 = (x - cx) ** 2 + (y - cy2) ** 2 + (z - cz) ** 2
        t = t + a * np.exp(-r2 / (2.0 * s * s))
    return t


def true_peak(hi: int) -> float:
    """ホットスポット ``hi`` の中心の真の温度 [°C]。"""
    _, cx, cy, cz, _, _ = HOTSPOTS[hi]
    return float(field(np.array([[cx, cy, cz]]))[0])


def centre(hi: int) -> np.ndarray:
    return np.array(HOTSPOTS[hi][1:4], float)


# --------------------------------------------------------------------------- #
# センサの置き方                                                                #
# --------------------------------------------------------------------------- #
def lattice(d: float, origin=None):
    """間隔 ``d`` の 3-D 格子。``origin`` は各軸の位相 [m](既定 = セル中心)。"""
    o = (0.5 * d,) * 3 if origin is None else tuple(float(v) for v in origin)
    ax = [np.arange(oo, L - 1e-12, d) for oo, L in zip(o, (LX, LY, LZ))]
    if min(a.size for a in ax) == 0:
        raise ValueError("格子が空: d=%.3f origin=%s" % (d, o))
    pts = np.stack(np.meshgrid(*ax, indexing="ij"), -1).reshape(-1, 3)
    return pts, [int(a.size) for a in ax]


def cloud(n: int, seed: int):
    """同じ本数を一様乱数で置く(系統的な死角を持たない対照群)。"""
    rng = np.random.default_rng(seed)
    return rng.uniform(0.0, 1.0, (n, 3)) * np.array([LX, LY, LZ])


def read(pts, drop=None, noise=0.0, seed=SEED):
    """センサが読む値 [°C]。``noise`` は同じ配置なら同じ実現になる。"""
    v = field(pts, drop)
    if noise > 0.0:
        v = v + np.random.default_rng(seed).normal(0.0, noise, v.shape)
    return v


# --------------------------------------------------------------------------- #
# 復元 —— 3 種の補間 + ゼロ点                                                   #
# --------------------------------------------------------------------------- #
def fit(pts, vals, method: str):
    """散らばったセンサ値から場を返す callable を作る。

    ``linear`` は Delaunay の凸包の外で NaN になるので**最近傍で埋める**
    (壁・床・天井際は必ず外に出る。埋めた割合は :func:`hull_miss` で数える)。
    """
    pts = np.asarray(pts, float)
    vals = np.asarray(vals, float)
    if method == "null":
        m = float(vals.mean())
        return lambda q: np.full(np.asarray(q, float).shape[0], m)
    if method == "nearest":
        tree = cKDTree(pts)
        return lambda q: vals[tree.query(np.asarray(q, float))[1]]
    if method == "linear":
        li = LinearNDInterpolator(pts, vals)
        tree = cKDTree(pts)

        def f(q):
            q = np.asarray(q, float)
            a = np.asarray(li(q), float)
            bad = ~np.isfinite(a)
            if bad.any():
                a[bad] = vals[tree.query(q[bad])[1]]
            return a
        return f
    if method == "rbf":
        rb = RBFInterpolator(pts, vals, neighbors=min(48, len(pts)),
                             kernel="thin_plate_spline")
        return lambda q: np.asarray(rb(np.asarray(q, float)), float)
    raise ValueError(method)


def hull_miss(pts, q) -> float:
    """線形補間が凸包の外に出て最近傍に落ちた割合。"""
    li = LinearNDInterpolator(np.asarray(pts, float),
                              np.zeros(len(pts)))
    return float(np.mean(~np.isfinite(np.asarray(li(np.asarray(q, float)), float))))


# --------------------------------------------------------------------------- #
# 崖の閉形式 —— 測る前に幾何から出す                                            #
# --------------------------------------------------------------------------- #
def visible(d: float, sigma: float) -> float:
    """間隔 ``d`` の格子で見えるピークの割合(等方ガウス σ)。

    ピークからいちばん遠い点は 3-D セルの中心 = ``d√3/2`` 離れる。そこでの
    ガウスの値は ``exp(-(d√3/2)²/(2σ²)) = exp(-3d²/(8σ²))``。
    """
    return float(np.exp(-(d * np.sqrt(3.0) / 2.0) ** 2 / (2.0 * sigma * sigma)))


def half_spacing(sigma: float) -> float:
    """ピークが半分に落ちる間隔 ``d* = σ√(8 ln2 / 3) = 1.3596 σ``。"""
    return float(sigma * np.sqrt(8.0 * np.log(2.0) / 3.0))


def local_grid(c, half, n=21):
    ax = [np.linspace(cc - half, cc + half, n) for cc in np.asarray(c, float)]
    return np.stack(np.meshgrid(*ax, indexing="ij"), -1).reshape(-1, 3)


def recover(hi: int, d: float, phase="worst", method="nearest", noise=0.0,
            seed=SEED) -> dict:
    """ホットスポット ``hi`` の近傍だけで復元し、回復したピーク超過 [°C] を返す。

    ``phase`` = ``"worst"`` はホットスポットをセルの中心に置く(最悪位相 =
    閉形式が当たるはずの場所)、``"node"`` はセンサの真上(最良)、``"room"``
    は部屋の格子をそのまま使う(現場の位相 = 制御できない)。

    3 つの量を別々に返す(1 つに畳むと何が効いているか言えなくなる):

    ``geo``
        **幾何だけ**の回復 ``max(T̂[全部] - T̂[そのラックだけ消した])``。3 手法とも
        補間はセンサ値に**線形**なので、この差は「そのラックのガウスだけを
        センサで拾って補間したもの」に厳密に等しい。閉形式が予言するのはこれ。
    ``naive``
        現場で測れる量 ``max(T̂[全部] - 真の背景)``。背景の復元誤差が同じ場所に
        載るので **``geo`` より必ず大きく出る**。
    ``floor``
        ラックを消したセンサ読みから測った ``max(T̂[背景] - 真の背景)``
        = 背景モデルの誤差 + 雑音。**何も無いところに立つ旗の高さ**。
    """
    c = centre(hi)
    a = HOTSPOTS[hi][5]
    s = HOTSPOTS[hi][4]
    if phase == "worst":
        o = (c - 0.5 * d) % d
    elif phase == "node":
        o = c % d
    else:
        o = np.full(3, 0.5 * d)
    pts, ns = lattice(d, o)
    half = max(1.6 * s, 0.9 * d)
    keep = np.all(np.abs(pts - c) <= half + 2.6 * d, axis=1)
    pts = pts[keep]
    q = local_grid(c, half)
    bg = field(q, drop=hi)
    v_full = fit(pts, read(pts, None, 0.0), method)(q)
    v_bg = fit(pts, read(pts, hi, 0.0), method)(q)
    v_bgn = fit(pts, read(pts, hi, noise, seed), method)(q)
    geo = float(np.max(v_full - v_bg))
    naive = float(np.max(v_full - bg))
    flo = float(np.max(v_bgn - bg))
    return {"geo": geo / a, "naive": naive / a, "floor": flo / a,
            "n_local": int(pts.shape[0]), "nz": ns[2], "origin": o,
            "bracketed": bool(c[2] + 0.5 * d <= LZ + 1e-9)}


def nearest_dist(hi: int, pts) -> float:
    """ホットスポット中心からいちばん近いセンサまでの距離 [m]。"""
    return float(cKDTree(np.asarray(pts, float)).query(centre(hi))[0])


# --------------------------------------------------------------------------- #
# 物差し 3 つ                                                                   #
# --------------------------------------------------------------------------- #
def peak_error(f, hi: int) -> float:
    """復元したピーク温度の誤差 [°C](真値のピークとの差、符号つき)。"""
    c = centre(hi)
    q = local_grid(c, 0.5, n=17)
    return float(np.max(f(q)) - true_peak(hi))


def locate(vol) -> np.ndarray:
    """体積から局所最大を拾って **[m] の座標**にする(``vol_local_maxima``)。"""
    pk = np.asarray(_L.vol_local_maxima(np.asarray(vol, float),
                                        min_distance=3, threshold=DETECT))
    if pk.size == 0:
        return np.zeros((0, 3))
    return np.stack([GX[pk[:, 2]], GY[pk[:, 1]], GZ[pk[:, 0]]], axis=1)


def loc_error(peaks) -> tuple:
    """各ホットスポットに最も近い検出ピークまでの距離 [m]。1.5 m 超は見失い。"""
    out, miss = [], 0
    for hi in range(len(HOTSPOTS)):
        if len(peaks) == 0:
            miss += 1
            continue
        dd = float(np.min(np.linalg.norm(peaks - centre(hi), axis=1)))
        if dd > 1.5:
            miss += 1
        else:
            out.append(dd)
    return (float(np.mean(out)) if out else float("nan")), miss


# --------------------------------------------------------------------------- #
# 1. 場面と真値                                                                 #
# --------------------------------------------------------------------------- #
def section_scene() -> dict:
    print("\n" + "=" * 78)
    print("1) 場面と真値 —— %.0f x %.1f x %.1f m のサーバ室、式で置いた温度場"
          % (LX, LY, LZ))
    print("=" * 78)
    t = field(GRID)
    print("   室温 %.1f °C / ホットアイル y=%.1f m(帯の幅 σ=%.1f m、+%.1f °C、"
          "上ほど熱い)" % (T_AMB, HOT_Y, HOT_S, HOT_A))
    print("   コールドアイル y=%.1f, %.1f m(床吹き出し -%.1f °C、高さ %.1f m で減衰)"
          % (COLD_Y[0], COLD_Y[1], COLD_A, COLD_H))
    print("   場の範囲 %.2f .. %.2f °C(評価格子 %d x %d x %d、刻み %.2f m)"
          % (t.min(), t.max(), GX.size, GY.size, GZ.size, EV))
    print("\n   過負荷ラック(探すもの)  σ [m]  振幅 [°C]  中心 (x, y, z) [m]  "
          "真のピーク [°C]  半減間隔 d*=1.36σ")
    for hi, (nm, cx, cy, cz, s, a) in enumerate(HOTSPOTS):
        print("     %-18s %5.2f %8.1f    (%.2f, %.2f, %.2f)      %6.2f  "
              "%12.3f m" % (nm, s, a, cx, cy, cz, true_peak(hi), half_spacing(s)))

    vol = t.reshape(GX.size, GY.size, GZ.size).transpose(2, 1, 0)
    assert vol.shape == VOL_SHAPE, vol.shape
    pk = locate(vol)
    d_loc, miss = loc_error(pk)
    print("\n   真値の体積に vol_local_maxima(しきい値 %.1f °C)をかけると "
          "%d 個の峰、位置誤差 %.3f m、見失い %d 個"
          % (DETECT, len(pk), d_loc, miss))
    print("   —— 評価格子の刻みが %.2f m なので、これが**測れる位置精度の下限**。"
          % EV)

    iz = int(round(2.30 / EV))
    iy = int(round(HOT_Y / EV))
    lo, hi_ = 17.0, 40.0
    pan = [np.asarray(fs.apply_cmap(vol[iz], "turbo", vmin=lo, vmax=hi_)),
           np.asarray(fs.apply_cmap(vol[:, iy, :][::-1], "turbo", vmin=lo, vmax=hi_)),
           np.asarray(fs.apply_cmap(
               np.asarray(_L.render_volume_projection(vol, azimuth=0.0, mode="mip")),
               "turbo", vmin=lo, vmax=hi_))]
    figs.save_grid(
        "scene_truth", pan,
        ["水平断面 z=2.30 m", "垂直断面 y=%.1f m(上が天井)" % HOT_Y,
         "最大値投影(真上から)"],
        ncols=3,
        title="真の温度場 [%.0f-%.0f °C、turbo](過負荷ラック 3 台をアイルに仕込んだ)"
              % (lo, hi_),
        caption="横=x 0..%.0f m、縦=y 0..%.1f m(左端)/ z 0..%.1f m(中央)。"
                % (LX, LY, LZ))
    return {"tmin": float(t.min()), "tmax": float(t.max()), "n_peak": len(pk),
            "loc": d_loc, "miss": miss}


# --------------------------------------------------------------------------- #
# 2. ゼロ点                                                                     #
# --------------------------------------------------------------------------- #
def section_zero_point(d=0.6) -> dict:
    print("\n" + "=" * 78)
    print("2) ゼロ点 —— 「全センサの平均を場全体に置く(場は平らとみなす)」")
    print("=" * 78)
    pts, ns = lattice(d)
    vals = read(pts, noise=NOISE)
    truth = field(GRID)
    print("   センサ格子 間隔 %.2f m = %d x %d x %d = %d 本(雑音 σ=%.2f °C)"
          % (d, ns[0], ns[1], ns[2], len(pts), NOISE))
    out = {}
    print("\n   手法                       場の RMSE   ピーク温度の誤差(3 台の平均)"
          "  位置誤差   見失い")
    for m in METHODS:
        f = fit(pts, vals, m)
        rec = f(GRID)
        rmse = float(np.sqrt(np.mean((rec - truth) ** 2)))
        pe = [peak_error(f, hi) for hi in range(len(HOTSPOTS))]
        vol = rec.reshape(GX.size, GY.size, GZ.size).transpose(2, 1, 0)
        dl, ms = loc_error(locate(vol))
        out[m] = {"rmse": rmse, "peak": pe, "loc": dl, "miss": ms}
        print("   %-26s %7.3f °C %12.2f °C %14s %8d"
              % (MET_LABEL[m], rmse, float(np.mean(pe)),
                 ("%.3f m" % dl) if np.isfinite(dl) else "—", ms))
    print("\n  ★ゼロ点の RMSE は %.3f °C。最良の手法は %.3f °C で、**%.1f 倍**良い。"
          % (out["null"]["rmse"],
             min(out[m]["rmse"] for m in METHODS if m != "null"),
             out["null"]["rmse"] / min(out[m]["rmse"] for m in METHODS if m != "null")))
    print("     ゼロ点はホットスポットを 1 台も見つけない(見失い %d 個)—— "
          "以降の手法はこれを\n     上回らなければ意味がない。"
          % out["null"]["miss"])
    return {"d": d, "n": len(pts), "res": out}


# --------------------------------------------------------------------------- #
# 3. 崖 —— 幾何から予測してから測る                                             #
# --------------------------------------------------------------------------- #
DS = [0.30, 0.45, 0.60, 0.80, 1.00, 1.20]


def section_cliff() -> dict:
    print("\n" + "=" * 78)
    print("3) ★崖 —— **測る前に**幾何から予測する")
    print("=" * 78)
    print("   間隔 d の 3-D 格子でサンプルすると、ピークからいちばん遠い点は")
    print("   セルの中心 = d√3/2 = %.4f d。σ のガウスなら見えるピークは"
          % (np.sqrt(3) / 2))
    print("       visible(d, σ) = exp(-(d√3/2)² / 2σ²) = exp(-3d²/8σ²)")
    print("   倍に落ちる。半分になるのは d* = σ√(8ln2/3) = %.4f σ。\n"
          % np.sqrt(8 * np.log(2) / 3))
    print("   ---- 予測(ここまで実測は 1 つも使っていない)----")
    print("   間隔 d [m] " + "".join("   σ=%.2f m" % h[4] for h in HOTSPOTS))
    pred = {}
    for d in DS:
        row = [visible(d, h[4]) for h in HOTSPOTS]
        pred[d] = row
        print("     %5.2f    " % d + "".join("  %8.4f" % v for v in row))
    print("   半減間隔 d*  " + "".join("  %6.3f m " % half_spacing(h[4])
                                       for h in HOTSPOTS))

    print("\n   ---- 実測(最悪位相 = ホットスポットをセルの中心に置く、最近傍補間)----")
    print("   間隔 d   ラック     予測   幾何の実測    差    素朴な実測  超過   "
          "床(背景+雑音)")
    geo, naive, floors, diffs, excess = {}, {}, {}, [], []
    for d in DS:
        for hi, h in enumerate(HOTSPOTS):
            r = recover(hi, d, "worst", "nearest", NOISE)
            assert r["bracketed"], (d, hi)
            geo[(d, hi)] = r["geo"]
            naive[(d, hi)] = r["naive"]
            floors[(d, hi)] = r["floor"]
            diffs.append(abs(r["geo"] - pred[d][hi]))
            excess.append(r["naive"] - pred[d][hi])
            print("    %5.2f   σ=%.2f  %8.4f %9.4f %+9.6f %9.4f %+7.4f %10.4f"
                  % (d, h[4], pred[d][hi], r["geo"], r["geo"] - pred[d][hi],
                     r["naive"], r["naive"] - pred[d][hi], r["floor"]))
    err = max(diffs)
    print("\n  ★閉形式と「幾何だけの実測」の差は最大 %.2e —— **一致する**。"
          "最近傍補間は最悪位相で\n     セルの角の値を返し、その角はちょうど"
          " d√3/2 の点だから。ここは幾何の検算であって発見ではない。" % err)
    print("  ★★**外れるのは閉形式ではなく「測り方」**。現場で測れるのは"
          "「復元した場のピーク」\n     であって「そのラックの寄与」ではないので、"
          "**背景の復元誤差が同じ場所に載る**。\n     素朴な実測は予測を最大 "
          "%+.4f 超過し(d=%.2f m、σ=%.2f m)、その超過は床 %.4f と\n     ほぼ同じ"
          " —— つまり**崖は実際より浅く見える**。"
          % (max(excess), DS[-1], HOTSPOTS[0][4], floors[(DS[-1], 0)]))
    print("     σ=%.2f m のラックは d=%.2f m で幾何の回復 %.6f(ほぼ消滅)なのに、"
          "素朴に測ると\n     %.4f 残って見える。**残っているのは背景の誤差**。"
          % (HOTSPOTS[2][4], DS[-1], geo[(DS[-1], 2)], naive[(DS[-1], 2)]))

    print("\n   ---- 位相を変えると何が起きるか(d = %.2f m、幾何の回復)----" % 0.60)
    d0 = 0.60
    print("   ラック    最悪位相(セル中心)  現場の位相(部屋の格子)  最良位相"
          "(センサ直上)")
    phase_rows = []
    for hi, h in enumerate(HOTSPOTS):
        a = recover(hi, d0, "worst", "nearest", 0.0)["geo"]
        b = recover(hi, d0, "room", "nearest", 0.0)["geo"]
        c = recover(hi, d0, "node", "nearest", 0.0)["geo"]
        phase_rows.append((h[0], a, b, c))
        print("   σ=%.2f  %14.4f %20.4f %18.4f" % (h[4], a, b, c))
    print("  ★★**閉形式は曲線ではなく床**。ラックが格子のどこに落ちるかは"
          "設計で決まらないので、\n     同じ d でも回復は最悪位相の値から 1.0 "
          "(センサ直上)まで跳ぶ。設計に使えるのは\n     最悪位相の値だけ —— "
          "「うちは平均すればこれくらい見える」は、そのラックには通じない。")

    figs.save_plot(
        "cliff_prediction",
        [("予測 σ=%.2f m" % HOTSPOTS[0][4], DS, [pred[d][0] for d in DS]),
         ("幾何の実測 σ=%.2f m" % HOTSPOTS[0][4], DS, [geo[(d, 0)] for d in DS]),
         ("素朴な実測 σ=%.2f m" % HOTSPOTS[0][4], DS, [naive[(d, 0)] for d in DS]),
         ("予測 σ=%.2f m" % HOTSPOTS[2][4], DS, [pred[d][2] for d in DS]),
         ("素朴な実測 σ=%.2f m" % HOTSPOTS[2][4], DS, [naive[(d, 2)] for d in DS])],
        xlabel="センサ格子の間隔 d [m]", ylabel="回復したピークの割合",
        title="崖 —— 閉形式は当たる。外れるのは「ピークがどれだけ残ったか」の測り方",
        caption="幾何の実測は予測と最大 %.1e しか違わない。素朴な実測が上に"
                "浮くぶんが背景の復元誤差。" % err)
    figs.save_table(
        "cliff_table",
        ["間隔 d [m]"] + ["σ=%.2f 予測" % h[4] for h in HOTSPOTS]
        + ["σ=%.2f 素朴な実測" % h[4] for h in HOTSPOTS],
        [["%.2f" % d] + ["%.4f" % pred[d][i] for i in range(3)]
         + ["%.4f" % naive[(d, i)] for i in range(3)] for d in DS],
        title="幾何の予測と、現場で測れる量(最悪位相)", col_w=130)
    return {"pred": pred, "geo": geo, "naive": naive, "floors": floors,
            "err": err, "excess": max(excess), "phase": phase_rows}


# --------------------------------------------------------------------------- #
# 4. 対照群 a —— 格子 vs 乱数(同じ本数)                                        #
# --------------------------------------------------------------------------- #
def section_grid_vs_random(d=0.60, ntrial=12) -> dict:
    print("\n" + "=" * 78)
    print("4) 対照群 a —— 格子 vs 乱数(同じセンサ本数、d = %.2f m)" % d)
    print("=" * 78)
    pts0, ns = lattice(d)
    n = len(pts0)
    lam = n / (LX * LY * LZ)
    r_grid = d * np.sqrt(3) / 2.0
    p_worse = float(np.exp(-(4 * np.pi / 3) * lam * r_grid ** 3))
    r_med = float((3 * np.log(2) / (4 * np.pi * lam)) ** (1 / 3.0))
    print("   センサ %d 本(密度 λ = %.4f 本/m³)。**予測を先に置く**:" % (n, lam))
    print("     * 格子の最悪距離は d√3/2 = %.4f m(設計で決まる、必ず起きる)"
          % r_grid)
    print("     * 一様乱数(Poisson)の最近傍距離は P(R>r) = exp(-4πλr³/3)。")
    print("       中央値 %.4f m、格子の最悪距離を**超える確率は %.3f**"
          " = %.1f %%。" % (r_med, p_worse, 100 * p_worse))
    print("       つまり乱数は死角を**消さない。どのラックが死角に落ちるかを"
          "振るだけ**。")

    # --- 距離の分布は安く大量に取れる(復元は要らない)--- #
    rng = np.random.default_rng(SEED)
    nq = 20000
    marg = 0.8
    qq = (rng.uniform(0.0, 1.0, (nq, 3)) * np.array([LX - 2 * marg, LY - 2 * marg,
                                                     LZ - 2 * marg]) + marg)
    dg = cKDTree(pts0).query(qq)[0]
    dr = np.concatenate([cKDTree(cloud(n, 3000 + k)).query(qq[k::4])[0]
                         for k in range(4)])
    frac = float(np.mean(dr > r_grid))
    print("\n   ---- 実測(壁から %.1f m 内側の一様な %d 点で距離を数えた)----"
          % (marg, nq))
    print("   格子   最近傍距離 中央値 %.4f m / 最大 %.4f m(幾何の上限 %.4f m)"
          % (np.median(dg), dg.max(), r_grid))
    print("   乱数   最近傍距離 中央値 %.4f m(予測 %.4f m) / 最大 %.4f m"
          % (np.median(dr), r_med, dr.max()))
    print("   ★乱数配置の **%.2f %%** が格子の最悪距離 %.4f m を超えた"
          "(予測 %.2f %%、差 %.2f ポイント)。"
          % (100 * frac, r_grid, 100 * p_worse, 100 * abs(frac - p_worse)))

    print("\n   ---- 回復の実測(位相/種を %d 通り × ラック 3 台 = %d 例、幾何の回復)"
          "----" % (ntrial, ntrial * len(HOTSPOTS)))
    res = {}
    for kind in ("格子(位相を振る)", "一様乱数(同じ本数)"):
        atts, dists = [], []
        for k in range(ntrial):
            if kind.startswith("格子"):
                pts, _ = lattice(d, rng.uniform(0.0, d, 3))
            else:
                pts = cloud(n, 1000 + k)
            for hi in range(len(HOTSPOTS)):
                c = centre(hi)
                s = HOTSPOTS[hi][4]
                q = local_grid(c, max(1.6 * s, 0.9 * d))
                near = np.all(np.abs(pts - c) <= max(1.6 * s, 0.9 * d) + 2.6 * d,
                              axis=1)
                sub = pts[near]
                f1 = fit(sub, read(sub, None, 0.0), "nearest")
                f0 = fit(sub, read(sub, hi, 0.0), "nearest")
                atts.append(float(np.max(f1(q) - f0(q))) / HOTSPOTS[hi][5])
                dists.append(nearest_dist(hi, pts))
        res[kind] = {"att": np.array(atts), "dist": np.array(dists)}
        print("   %-20s 最近傍距離 中央値 %.4f m / 最悪 %.4f m   "
              "回復 中央値 %.4f / 最悪 %.4f"
              % (kind, np.median(res[kind]["dist"]), res[kind]["dist"].max(),
                 np.median(res[kind]["att"]), res[kind]["att"].min()))
    print("\n  ★格子の回復は位相で %.4f 〜 %.4f に散らばり、乱数は %.4f 〜 %.4f。"
          % (res["格子(位相を振る)"]["att"].min(),
             res["格子(位相を振る)"]["att"].max(),
             res["一様乱数(同じ本数)"]["att"].min(),
             res["一様乱数(同じ本数)"]["att"].max()))
    print("     **違うのは平均ではなく「言い切れるかどうか」**。格子の下限は"
          "幾何で決まる(σ=%.2f m の\n     ラックなら必ず %.4f 以上)。"
          "乱数は下限を持たない —— 最近傍距離に上限が無いので、\n     "
          "運が悪ければいくらでも見えなくなる(この %d 例の最悪は %.4f m 離れた)。"
          % (HOTSPOTS[2][4], visible(d, HOTSPOTS[2][4]),
             ntrial * len(HOTSPOTS), res["一様乱数(同じ本数)"]["dist"].max()))

    rr = np.linspace(0.0, 1.0, 80)
    figs.save_plot(
        "grid_vs_random",
        [("格子(%d 本)" % n, np.sort(dg), np.linspace(0, 1, dg.size)),
         ("一様乱数(%d 本)" % n, np.sort(dr), np.linspace(0, 1, dr.size)),
         ("Poisson の予測 1-exp(-4πλr³/3)", rr,
          1.0 - np.exp(-(4 * np.pi / 3) * lam * rr ** 3)),
         ("格子の幾何上限 d√3/2", [r_grid, r_grid], [0.0, 1.0])],
        xlabel="最も近いセンサまでの距離 [m](間隔 %.2f m 相当)" % d,
        ylabel="累積割合", title="格子は死角を決め打ち、乱数は死角を振る",
        caption="格子の最悪距離 %.3f m を乱数の %.2f %% が超えた(予測 %.2f %%)。"
                % (r_grid, 100 * frac, 100 * p_worse))
    return {"n": n, "p_worse": p_worse, "frac": frac, "r_grid": r_grid,
            "dg_max": float(dg.max()), "dr_max": float(dr.max()),
            "res": {k: {"att": v["att"].tolist(), "dist": v["dist"].tolist()}
                    for k, v in res.items()}}


# --------------------------------------------------------------------------- #
# 5. 対照群 b —— 補間 3 種で崖は動くか                                          #
# --------------------------------------------------------------------------- #
def section_methods_cliff(hi=1) -> dict:
    print("\n" + "=" * 78)
    print("5) 対照群 b —— 補間法を 3 つ入れ替える(ラック %s、σ=%.2f m、最悪位相)"
          % (HOTSPOTS[hi][0], HOTSPOTS[hi][4]))
    print("=" * 78)
    s = HOTSPOTS[hi][4]
    print("   予測: 崖の位置は補間法で決まらない。半減間隔は d* = 1.3596 σ = "
          "%.4f m のはず。" % half_spacing(s))
    print("\n   間隔 d [m]      予測    最近傍     線形     RBF")
    curves = {m: [] for m in ("nearest", "linear", "rbf")}
    for d in DS:
        row = [visible(d, s)]
        for m in curves:
            v = recover(hi, d, "worst", m, 0.0)["geo"]
            curves[m].append(v)
            row.append(v)
        print("     %5.2f    %8.4f %8.4f %8.4f %8.4f" % tuple([d] + row))

    def crossing(ys):
        """回復が 0.5 を切る d を線形に補間して返す。"""
        for i in range(1, len(DS)):
            if ys[i - 1] >= 0.5 > ys[i]:
                t = (0.5 - ys[i - 1]) / (ys[i] - ys[i - 1])
                return DS[i - 1] + t * (DS[i] - DS[i - 1])
        return float("nan")

    cross = {m: crossing(curves[m]) for m in curves}
    cross_pred = crossing([visible(d, s) for d in DS])
    print("\n   半減する間隔 d(0.5 を横切る点を線形補間):")
    print("     閉形式 %.4f m / 折れ線で読んだ予測 %.4f m / 最近傍 %.4f m / "
          "線形 %.4f m / RBF %.4f m"
          % (half_spacing(s), cross_pred, cross["nearest"], cross["linear"],
             cross["rbf"]))
    spread = max(cross.values()) - min(cross.values())
    print("  ★3 手法の崖の位置の開きは %.4f m(%.1f %%)。**崖は手法ではなく"
          "サンプリングの問題**\n     —— 補間はセンサが取らなかった値を"
          "作れない。" % (spread, 100 * spread / np.mean(list(cross.values()))))
    print("     RBF だけ細かいところで予測を超える(最大 %+.4f)—— "
          "薄板スプラインは節点の外へ\n     **行き過ぎる**ので、たまたま"
          "山を高く戻す。当たっているのではなく、外れ方が上向き。"
          % max(curves["rbf"][i] - visible(DS[i], s) for i in range(len(DS))))

    figs.save_plot(
        "cliff_by_method",
        [("予測 exp(-3d²/8σ²)", DS, [visible(d, s) for d in DS]),
         ("最近傍", DS, curves["nearest"]),
         ("線形(Delaunay)", DS, curves["linear"]),
         ("RBF(薄板スプライン)", DS, curves["rbf"])],
        xlabel="センサ格子の間隔 d [m]", ylabel="回復したピークの割合",
        title="崖の位置は補間法で動かない(σ=%.2f m のラック)" % s,
        caption="3 手法の半減間隔の開きは %.4f m。" % spread)
    return {"curves": curves, "cross": cross, "spread": spread,
            "cross_pred": cross_pred}


# --------------------------------------------------------------------------- #
# 6. 物差し 3 つ —— 勝者は入れ替わるか                                          #
# --------------------------------------------------------------------------- #
def section_metrics(ds=(0.50, 0.80, 1.20)) -> dict:
    print("\n" + "=" * 78)
    print("6) 物差しを 3 つ置く —— 場の RMSE / ピーク温度の誤差 / 位置の誤差")
    print("=" * 78)
    truth = field(GRID)
    rows, out = [], {}
    print("   間隔  手法                      場の RMSE   ピーク誤差(平均)  "
          "位置誤差   見失い  凸包外")
    for d in ds:
        pts, ns = lattice(d)
        vals = read(pts, noise=NOISE)
        miss_hull = hull_miss(pts, GRID)
        for m in METHODS:
            f = fit(pts, vals, m)
            rec = f(GRID)
            rmse = float(np.sqrt(np.mean((rec - truth) ** 2)))
            pe = [peak_error(f, hi) for hi in range(len(HOTSPOTS))]
            vol = rec.reshape(GX.size, GY.size, GZ.size).transpose(2, 1, 0)
            dl, ms = loc_error(locate(vol))
            out[(d, m)] = {"rmse": rmse, "peak": float(np.mean(np.abs(pe))),
                           "loc": dl, "miss": ms, "n": len(pts)}
            rows.append(["%.2f (%d 本)" % (d, len(pts)), MET_LABEL[m],
                         "%.3f" % rmse, "%+.2f" % float(np.mean(pe)),
                         ("%.3f" % dl) if np.isfinite(dl) else "—", str(ms)])
            print("   %.2f  %-26s %7.3f °C %10.2f °C %11s %6d %8.1f %%"
                  % (d, MET_LABEL[m], rmse, float(np.mean(pe)),
                     ("%.3f m" % dl) if np.isfinite(dl) else "—", ms,
                     100 * miss_hull if m == "linear" else 0.0))

    print("\n   ---- 物差しごとの勝者(ゼロ点を除く)----")
    winners = {}
    for d in ds:
        cand = [m for m in METHODS if m != "null"]
        w_rmse = min(cand, key=lambda m: out[(d, m)]["rmse"])
        w_peak = min(cand, key=lambda m: out[(d, m)]["peak"])
        fin = [m for m in cand if np.isfinite(out[(d, m)]["loc"])]
        w_loc = (min(fin, key=lambda m: (out[(d, m)]["miss"], out[(d, m)]["loc"]))
                 if fin else "—")
        winners[d] = (w_rmse, w_peak, w_loc)
        print("     d=%.2f m   RMSE: %-12s ピーク誤差: %-12s 位置誤差: %s"
              % (d, MET_LABEL.get(w_rmse, w_rmse).split("(")[0],
                 MET_LABEL.get(w_peak, w_peak).split("(")[0],
                 MET_LABEL.get(w_loc, w_loc).split("(")[0]))
    n_distinct = len({tuple(v) for v in winners.values()})
    swapped = any(len(set(v)) > 1 for v in winners.values())
    print("\n  ★3 つの物差しで勝者は%s。"
          % ("**入れ替わる**" if swapped else "入れ替わらなかった"))
    figs.save_table(
        "metric_table",
        ["間隔 d", "手法", "RMSE [°C]", "ピーク誤差 [°C]", "位置誤差 [m]",
         "見失い"], rows,
        title="物差し 3 つ(1 つの数字に畳まない)", col_w=130)
    return {"out": {("%.2f|%s" % k): v for k, v in out.items()},
            "winners": {("%.2f" % k): v for k, v in winners.items()},
            "swapped": swapped, "n_distinct": n_distinct, "raw": out}


# --------------------------------------------------------------------------- #
# 7. 図 —— 同じ測定を 4 通りに復元した断面                                       #
# --------------------------------------------------------------------------- #
def section_maps(d=0.80) -> None:
    truth = field(GRID)
    pts, _ = lattice(d)
    vals = read(pts, noise=NOISE)
    iz = int(round(2.30 / EV))
    lo, hi_ = 17.0, 40.0

    def slab(v):
        return np.asarray(v).reshape(GX.size, GY.size, GZ.size).transpose(2, 1, 0)[iz]

    pans = [np.asarray(fs.apply_cmap(slab(truth), "turbo", vmin=lo, vmax=hi_))]
    caps = ["真値 z=2.30 m"]
    for m in METHODS:
        pans.append(np.asarray(fs.apply_cmap(slab(fit(pts, vals, m)(GRID)),
                                             "turbo", vmin=lo, vmax=hi_)))
        caps.append(MET_LABEL[m].split("(")[0])
    figs.save_grid("map_reconstruction", pans, caps, ncols=3,
                   title="間隔 %.2f m・%d 本のセンサから復元した z=2.30 m 断面"
                         "(%.0f-%.0f °C 共通尺度)" % (d, len(pts), lo, hi_),
                   caption="横=x 0..%.0f m、縦=y 0..%.1f m。"
                           "3 台の過負荷ラックのうち何台が残るか。" % (LX, LY))

    res = slab(fit(pts, vals, "rbf")(GRID)) - slab(truth)
    figs.save("map_residual", res,
              "RBF 復元の残差 [°C](正 = 高く出た。z=2.30 m)", signed=True)


# --------------------------------------------------------------------------- #
# 8. 道具の穴                                                                   #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("8) 道具の穴(この PoC で使ってみて)")
    print("=" * 78)
    for n in ("griddata", "interp_nd", "scatter_to_grid", "idw", "kriging",
              "natural_neighbor", "rbf_interpolate"):
        assert not hasattr(fs.ledger, n), n
    assert hasattr(fs.ledger, "interp_linear") and hasattr(fs.ledger, "interp_cubic")
    print("  (a) 補間の op は **1-D だけ**(interp_linear / interp_cubic)。"
          "散らばった 3-D の点から\n      場を作る口が無いので、"
          "scipy を直に呼んだ。センサ網・地質・気象はどれもこの形。")

    assert hasattr(fs.ledger, "vol_local_maxima")
    pk = np.asarray(_L.vol_local_maxima(np.zeros((8, 8, 8)), min_distance=1))
    assert pk.shape[0] == 0, pk.shape
    print("  (b) vol_local_maxima は平らな体積で 0 個を返す(fail-closed)。"
          "**整数ボクセル**を\n      返すので、位置精度は評価格子の刻み"
          " %.2f m で頭打ち。サブボクセル化は\n      refine_peak_newton に"
          "在るが torch が要る —— CI(torch 無し)では使えない。" % EV)

    z = np.zeros((4, 4))
    z[1, 1] = 1.0
    a = np.asarray(fs.apply_cmap(z, "turbo"))
    b = np.asarray(fs.apply_cmap(z * 100.0, "turbo"))
    assert np.allclose(a, b), "vmin/vmax 無しの正規化は配列ごと"
    print("  (c) apply_cmap は vmin/vmax を省くと**渡した配列の中だけ**で"
          "正規化する。温度場を\n      1 枚ずつ塗ると色尺度が揃わない"
          "(1 °C の差も 20 °C の差も同じ絵になる)。\n      "
          "この PoC は全パネルに vmin/vmax を明示した。")


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("=" * 78)
    print("データセンターの温度場を疎なセンサから復元する —— "
          "格子の死角がラックを消す")
    print("室 %.0f x %.1f x %.1f m / 過負荷ラック %d 台(σ = %s m) / "
          "センサ雑音 σ=%.2f °C"
          % (LX, LY, LZ, len(HOTSPOTS),
             ", ".join("%.2f" % h[4] for h in HOTSPOTS), NOISE))
    print("=" * 78)

    sc = section_scene()
    zp = section_zero_point()
    cl = section_cliff()
    gr = section_grid_vs_random()
    mc = section_methods_cliff()
    mt = section_metrics()
    section_maps()
    section_tool_gaps()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 幾何の予測 exp(-3d²/8σ²) と実測(最悪位相)の差は最大 %.4f。"
          "崖は**測る前に言える**。" % cl["err"])
    print("  * σ=%.2f m のラックは間隔 %.2f m で回復 %.4f まで落ちる"
          "(半減間隔 d* = %.3f m)。"
          % (HOTSPOTS[2][4], 0.60, cl["meas"][(0.60, 2)],
             half_spacing(HOTSPOTS[2][4])))
    print("  * 補間法を 3 つ入れ替えても崖の位置は %.4f m しか動かない —— "
          "**手法ではなく\n    サンプリングの問題**。" % mc["spread"])
    print("  * 乱数配置は死角を消さない: %.1f %% が格子の最悪距離を超えた"
          "(Poisson の予測 %.1f %%)。"
          % (100 * gr["frac"], 100 * gr["p_worse"]))
    print("  * 3 つの物差しで勝者は%s。"
          % ("入れ替わる" if mt["swapped"] else "入れ替わらない"))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    # --- 所見を固定する(穴が塞がったら鳴る)--- #
    assert cl["err"] < 0.02, cl["err"]
    assert cl["meas"][(0.30, 2)] > 0.3 and cl["meas"][(0.80, 2)] < 0.05, cl["meas"]
    assert mc["spread"] < 0.10, mc["spread"]
    assert abs(gr["frac"] - gr["p_worse"]) < 0.12, (gr["frac"], gr["p_worse"])
    assert zp["res"]["null"]["miss"] == len(HOTSPOTS), zp["res"]["null"]
    assert zp["res"]["rbf"]["rmse"] < 0.5 * zp["res"]["null"]["rmse"]
    assert sc["miss"] == 0 and sc["loc"] <= EV * np.sqrt(3) + 1e-9, sc
    assert mt["swapped"], mt["winners"]

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
