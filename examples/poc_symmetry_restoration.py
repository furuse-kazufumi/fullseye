# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""(暫定 docstring —— 実行後に実測値へ差し替える)"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

_L = fs.ledger

# --- 仮面の諸元(すべて mm)------------------------------------------------- #
A, B, HGT = 90.0, 118.0, 52.0        # 楕円の半幅・半高・最大隆起
EYE_X, EYE_Y, EYE_S, EYE_D = 34.0, 34.0, 13.0, 9.0      # 眼窩(くぼみ)
BROW_A, BROW_Y = 4.0, 58.0                              # 眉の隆起
NOSE_A, NOSE_W, NOSE_Y, NOSE_L = 8.0, 10.0, 2.0, 34.0   # 鼻梁(尾根)
MOUTH_D, MOUTH_Y, MOUTH_W, MOUTH_L = 5.0, -54.0, 8.0, 34.0
CHEEK_A, CHEEK_X, CHEEK_Y, CHEEK_S = 3.0, 55.0, -16.0, 20.0
RIM_A, RIM_R, RIM_W = 5.0, 0.87, 0.055                  # 縁の隆起帯

# 非対称の仕込み(偽陽性の節でだけ入れる)
DECO_A, DECO_X, DECO_Y, DECO_S = 3.0, 50.0, -2.0, 13.0  # 片側だけの装飾(右頬)
WARP_A = 2.2                                            # 経年のねじれ(x に対し奇関数)

# 欠損(既定)
DEF_C_XY = (40.0, 28.0)       # 欠損の中心(右眼〜右頬)
DEF_R = 34.0                  # 欠損球の半径 [mm]

N_WORK = 20000
SEED = 20260907
TAU_K = 2.5           # 「既存点から離れている」の閾値 = TAU_K x 中央値間隔
SPUR_TOL = 1.0        # 「真の面から浮いている」と数える距離 [mm](幾何の公差)

TRUE_P0 = np.array([0.0, 0.0, 0.0])
TRUE_N = np.array([1.0, 0.0, 0.0])


# --------------------------------------------------------------------------- #
# 形 —— 左右対称な高さ場 z = f(x, y)(x = 0 が真の対称面)                       #
# --------------------------------------------------------------------------- #
def mask_height(x, y, deco: float = 0.0, warp: float = 0.0):
    """仮面の高さ [mm] と、楕円の内側かどうかを返す。

    ``deco`` / ``warp`` を 0 にすると **x について厳密に偶関数**(= x=0 が対称面)。
    ``deco`` は右頬だけの装飾、``warp`` は x の奇関数のねじれで、どちらも
    対称性を壊す(偽陽性の節で使う)。
    """
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    rr = (x / A) ** 2 + (y / B) ** 2
    inside = rr <= 1.0
    t = np.clip(1.0 - rr, 0.0, None)
    z = HGT * t ** 1.3                                       # 楕円ドームの土台
    ax = np.abs(x)
    z = z - EYE_D * np.exp(-(((ax - EYE_X) / EYE_S) ** 2
                             + ((y - EYE_Y) / EYE_S) ** 2))
    z = z + BROW_A * np.exp(-(((ax - EYE_X) / (1.35 * EYE_S)) ** 2
                              + ((y - BROW_Y) / (0.55 * EYE_S)) ** 2))
    z = z + NOSE_A * np.exp(-(x / NOSE_W) ** 2 - ((y - NOSE_Y) / NOSE_L) ** 2)
    z = z - MOUTH_D * np.exp(-((y - MOUTH_Y) / MOUTH_W) ** 2 - (x / MOUTH_L) ** 4)
    z = z + CHEEK_A * np.exp(-(((ax - CHEEK_X) / CHEEK_S) ** 2
                               + ((y - CHEEK_Y) / CHEEK_S) ** 2))
    z = z + RIM_A * np.exp(-((np.sqrt(rr) - RIM_R) / RIM_W) ** 2)
    if deco:
        z = z + deco * np.exp(-(((x - DECO_X) / DECO_S) ** 2
                                + ((y - DECO_Y) / DECO_S) ** 2))
    if warp:
        z = z + warp * (x / A) * (0.55 + 0.45 * (y / B)) * t
    return z, inside


def _grad(x, y, deco=0.0, warp=0.0, h=0.05):
    """高さ場の勾配(中心差分)。法線 = (-zx, -zy, 1) の正規化。"""
    zx = (mask_height(x + h, y, deco, warp)[0]
          - mask_height(x - h, y, deco, warp)[0]) / (2 * h)
    zy = (mask_height(x, y + h, deco, warp)[0]
          - mask_height(x, y - h, deco, warp)[0]) / (2 * h)
    return zx, zy


def sample_mask(n: int, seed: int, deco: float = 0.0, warp: float = 0.0) -> dict:
    """仮面の表面を**面積一様**に標本した点群 (N,3) = (x,y,z) と法線を返す。

    (x, y) 一様では傾いた面が薄くなるので、面素 sqrt(1+|∇z|^2) で棄却抽出する。
    """
    rng = np.random.default_rng(seed)
    xs, ys, zs = [], [], []
    got = 0
    while got < n:
        m = int(1.9 * (n - got)) + 512
        x = rng.uniform(-A, A, m)
        y = rng.uniform(-B, B, m)
        z, ins = mask_height(x, y, deco, warp)
        zx, zy = _grad(x, y, deco, warp)
        w = np.sqrt(1.0 + zx ** 2 + zy ** 2)
        keep = ins & (rng.uniform(0.0, 4.0, m) < w)          # 4.0 = w の上限側
        xs.append(x[keep]); ys.append(y[keep]); zs.append(z[keep])
        got += int(keep.sum())
    x = np.concatenate(xs)[:n]
    y = np.concatenate(ys)[:n]
    z = np.concatenate(zs)[:n]
    zx, zy = _grad(x, y, deco, warp)
    nrm = np.column_stack([-zx, -zy, np.ones_like(zx)])
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    return {"pts": np.column_stack([x, y, z]), "nrm": nrm}


def off_surface(P, deco: float = 0.0, warp: float = 0.0) -> np.ndarray:
    """点から**真の面**までの直交距離 [mm](閉形式)。楕円の外は inf。

    点群どうしの最近傍距離で「面から浮いているか」を測ると、標本間隔の裾を
    拾って**同じ面の上の点まで浮いていることになる**(最初にそう書いて、
    面が真値のときですら 68 % が「偽の面」と数えられた)。真値があるのだから
    真値と比べる。
    """
    P = np.asarray(P, float)
    z, ins = mask_height(P[:, 0], P[:, 1], deco, warp)
    zx, zy = _grad(P[:, 0], P[:, 1], deco, warp)
    d = np.abs(P[:, 2] - z) / np.sqrt(1.0 + zx ** 2 + zy ** 2)
    return np.where(ins, d, np.inf)


def damage_center(cxy=DEF_C_XY, deco=0.0, warp=0.0) -> np.ndarray:
    """欠損球の中心(面の少し内側に置く)。"""
    z, _ = mask_height(np.array([cxy[0]]), np.array([cxy[1]]), deco, warp)
    return np.array([cxy[0], cxy[1], float(z[0]) - 0.30 * DEF_R])


def break_off(pts, centre, radius) -> np.ndarray:
    """欠損マスク(True = 失われた点)。"""
    return np.linalg.norm(np.asarray(pts, float) - centre, axis=1) <= radius


# --------------------------------------------------------------------------- #
# 対称面の道具                                                                  #
# --------------------------------------------------------------------------- #
def _pca_axes_of(pts):
    """PCA の 3 主軸(列)。``detect_reflection_symmetry`` が候補にするのと同じもの。"""
    p = np.asarray(pts, float)
    c = p - p.mean(axis=0)
    _, _, vt = np.linalg.svd(c, full_matrices=False)
    return vt.T


def plane_from_v(v):
    """最適化変数 (ay, az, t) → (平面上の点, 単位法線)。"""
    n = np.array([1.0, float(v[0]), float(v[1])])
    n /= np.linalg.norm(n)
    return float(v[2]) * n, n


def plane_error(p0, n):
    """真の対称面(x=0)からのずれ: 角度 [deg] と原点での位置ずれ [mm]。"""
    n = np.asarray(n, float) / np.linalg.norm(n)
    if n[0] < 0:
        n = -n
    ang = np.degrees(np.arccos(np.clip(abs(n @ TRUE_N), -1.0, 1.0)))
    off = abs(float(np.asarray(p0, float) @ n))
    return float(ang), off


def sym_residual(pts, tree, p0, n) -> float:
    """鏡映した点から元の点群への片側 NN 距離の RMS [mm](掃引用の速い目的関数)。

    公開 op ``reflection_symmetry_score`` と同じ量を測るが、KD 木と中央値間隔を
    毎回作り直さない(§9 の「道具の穴」を参照)。
    """
    q = np.asarray(_L.reflect_points(pts, p0, n), float)
    d, _ = tree.query(q, k=1, workers=-1)
    return float(np.sqrt(np.mean(d ** 2)))


def estimate_plane(pts, refine: str = "nm", axis_hint: bool = False) -> dict:
    """対称面を推定する。粗 = ``detect_reflection_symmetry``(PCA 3 候補)。

    ``axis_hint=True`` なら PCA の 3 候補のうち **x に最も近い軸**を人が選ぶ
    (自動選択が別の軸へ飛ぶかどうかを、面の精度と切り離して測るため)。
    ``refine='nm'`` は公開 op と同じ残差を Nelder-Mead で 3 自由度(2 角 + 位置)
    掃引。``refine='icp'`` は「鏡映 → ``icp_point2point_3d`` → 対応点の中点に
    ``fit_plane_3d``」の古典手法。``refine='none'`` は粗のまま。
    """
    pts = np.asarray(pts, float)
    tree = cKDTree(pts)
    det = _L.detect_reflection_symmetry(pts)
    p0 = np.asarray(det["plane_point"], float)
    n = np.asarray(det["plane_normal"], float)
    axes = _pca_axes_of(pts)
    picked_ang = float(np.degrees(np.arccos(np.clip(abs(n @ TRUE_N), -1, 1))))
    if axis_hint:
        n = axes[:, int(np.argmax(np.abs(axes[0, :])))]
    if n[0] < 0:
        n = -n
    out = {"coarse": (p0, n), "margin": float(det["margin"]),
           "score": float(det["score"]), "all_scores": list(det["all_scores"]),
           "auto_axis_deg": picked_ang, "flipped": picked_ang > 45.0}
    if refine == "none":
        out["p0"], out["n"] = p0, n
        return out
    if refine == "icp":
        p0r, nr = _refine_icp(pts, tree, p0, n)
        out["p0"], out["n"] = p0r, nr
        return out
    # Nelder-Mead: n = normalize([1, ay, az]), 平面は t*n を通る
    v0 = np.array([n[1] / n[0], n[2] / n[0], float(p0 @ n)])
    res = minimize(lambda v: sym_residual(pts, tree, *plane_from_v(v)), v0,
                   method="Nelder-Mead",
                   options={"xatol": 1e-4, "fatol": 1e-6, "maxfev": 220,
                            "initial_simplex": np.vstack([
                                v0, v0 + [0.03, 0, 0], v0 + [0, 0.03, 0],
                                v0 + [0, 0, 1.5]])})
    out["p0"], out["n"] = plane_from_v(res.x)
    out["nfev"] = int(res.nfev)
    return out


def _refine_icp(pts, tree, p0, n):
    """鏡映 → ICP → 対応点の中点に平面をあてる(Combes 流)。"""
    q = np.asarray(_L.reflect_points(pts, p0, n), float)
    R, t, _info = _L.icp_point2point_3d.raw(q, pts, iters=30, trim_ratio=0.85)
    R = np.asarray(R, float); t = np.asarray(t, float)
    q2 = q @ R.T + t                       # 合成 = 改良された鏡映像
    d, j = tree.query(q2, k=1, workers=-1)
    ok = (d < np.median(d) * 3.0 + 1e-9)
    a, b = pts[ok], pts[j[ok]]             # a とその対称の相手 b
    sep = np.linalg.norm(a - b, axis=1)
    ok2 = sep > np.percentile(sep, 25)     # 面の近く(自分自身と組む点)を捨てる
    mid = 0.5 * (a[ok2] + b[ok2])
    pp, nn, _ = _L.fit_plane_3d(mid)
    nn = np.asarray(nn, float)
    if nn @ n < 0:
        nn = -nn
    return np.asarray(pp, float), nn


# --------------------------------------------------------------------------- #
# 復元                                                                          #
# --------------------------------------------------------------------------- #
def restore_symmetric(surv, p0, n, tau) -> dict:
    """残った点を対称面で鏡映し、既存点から tau 以上離れた鏡像だけを足す。"""
    surv = np.asarray(surv, float)
    tree = cKDTree(surv)
    mir = np.asarray(_L.reflect_points(surv, p0, n), float)
    d, _ = tree.query(mir, k=1, workers=-1)
    fill = mir[d > tau]
    return {"fill": fill, "restored": np.vstack([surv, fill]) if len(fill) else surv}


def score_restoration(gt_missing, restored, fill, deco=0.0, warp=0.0) -> dict:
    """壊れ方を **2 種類**に分けて数える。

    * 穴が埋まらない: 失われた真値の点から復元点群への距離 [mm]。
    * 偽の面が生える: 足した点のうち、真の面から ``SPUR_TOL`` 以上浮いたもの。
    """
    d, _ = cKDTree(restored).query(np.asarray(gt_missing, float), k=1, workers=-1)
    out = {"rms": float(np.sqrt(np.mean(d ** 2))), "p95": float(np.percentile(d, 95)),
           "max": float(d.max()), "per_pt": d, "n_fill": int(len(fill))}
    if len(fill):
        e = off_surface(fill, deco, warp)
        bad = e > SPUR_TOL
        out["spur_frac"] = float(bad.mean())
        out["spur_rms"] = float(np.sqrt(np.mean(np.minimum(e, 1e3) ** 2)))
    else:
        out["spur_frac"], out["spur_rms"] = 0.0, 0.0
    return out


# --------------------------------------------------------------------------- #
# ゼロ点 —— 対称性を使わない穴埋め(深度格子 + 調和緩和 fill_holes)             #
# --------------------------------------------------------------------------- #
PATCH_PX = 0.8                       # ゼロ点に与える深度格子の画素 [mm]


def patch_grid(centre, half=62.0, px=PATCH_PX):
    xs = np.arange(centre[0] - half, centre[0] + half, px)
    ys = np.arange(centre[1] + half, centre[1] - half, -px)
    return xs, ys, *np.meshgrid(xs, ys)


def zero_point_fill(centre, radius, deco=0.0, warp=0.0) -> np.ndarray:
    """穴の周りの深度格子を ``fill_holes`` で埋め、穴の中の点を 3-D に戻す。

    ★ゼロ点には**有利な条件**を与えている —— 点群ではなく、穴の外が
    びっしり埋まった密な深度格子(画素 %.1f mm)を渡している。
    """
    xs, ys, X, Y = patch_grid(centre, px=PATCH_PX)
    Z, ins = mask_height(X, Y, deco, warp)
    hole = (np.sqrt((X - centre[0]) ** 2 + (Y - centre[1]) ** 2
                    + (Z - centre[2]) ** 2) <= radius) & ins
    obs = np.where(hole | ~ins, np.nan, Z)
    filled = np.asarray(_L.fill_holes(obs, max_radius=radius / PATCH_PX + 6.0,
                                      invalid=np.nan, max_iter=1400))
    m = hole & np.isfinite(filled)
    return np.column_stack([X[m], Y[m], filled[m]]), hole, X, Y, Z, ins


# --------------------------------------------------------------------------- #
# 図の道具                                                                      #
# --------------------------------------------------------------------------- #
LIGHT = np.array([-0.45, 0.42, 0.79])


def grid_xy(nx=252, ny=330, pad=1.02):
    xs = np.linspace(-A * pad, A * pad, nx)
    ys = np.linspace(B * pad, -B * pad, ny)
    return xs, ys, *np.meshgrid(xs, ys)


def shaded(Z, ins, xs, ys):
    """陰影起伏図(Lambert)。外側は暗く落とす。"""
    gy, gx = np.gradient(np.where(ins, Z, 0.0), ys, xs)
    n = np.stack([-gx, -gy, np.ones_like(Z)], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    lam = n @ (LIGHT / np.linalg.norm(LIGHT))
    img = 0.16 + 0.84 * np.clip(lam, 0.0, 1.0)
    return np.where(ins, img, 0.03)


def scatter_map(P, val, xs, ys, rmax=2.4, fill=0.0):
    """点ごとの値を (x,y) 格子へ最近傍で塗る(疑似カラーの誤差地図用)。"""
    X, Y = np.meshgrid(xs, ys)
    out = np.full(X.shape, fill, float)
    P = np.asarray(P, float)
    if len(P) < 3:
        return out
    d, i = cKDTree(P[:, :2]).query(np.column_stack([X.ravel(), Y.ravel()]),
                                   k=1, workers=-1)
    v = np.asarray(val, float)[i]
    v[d > rmax] = fill
    return v.reshape(X.shape)


def with_scalebar(img, s: float, wpx: int = 12, lo: float | None = None):
    """右端に色の目盛り帯を足す(パネル間で色と値の対応を固定する)。

    ``lo`` を渡すと [lo, s] の片側目盛り(距離のような符号なしの量)、
    既定は ±s の両側目盛り(符号つきの量)。
    """
    h = img.shape[0]
    a = lo if lo is not None else -s
    ramp = np.linspace(s, a, h)[:, None] * np.ones((1, wpx))
    return np.concatenate([np.clip(img, a, s), np.full((h, 4), a), ramp], axis=1)


# --------------------------------------------------------------------------- #
# 1. 場面と真値                                                                 #
# --------------------------------------------------------------------------- #
def section_scene() -> dict:
    print("\n" + "=" * 78)
    print("1) 仮面と欠損 —— 真値は「完全形」と「真の対称面 x = 0」")
    print("=" * 78)
    sc = sample_mask(N_WORK, SEED)
    pts, nrm = sc["pts"], sc["nrm"]
    # 対称性の検算: 高さ場が x について偶関数であることを直接確かめる
    xs, ys, X, Y = grid_xy()
    Z, ins = mask_height(X, Y)
    Zm, _ = mask_height(-X, Y)
    asym = float(np.sqrt(np.mean((Z - Zm)[ins] ** 2)))
    print("  仮面 %.0f x %.0f mm・最大隆起 %.1f mm / 点 %d 個" % (2 * A, 2 * B, Z[ins].max(), len(pts)))
    print("  真値の検算: |z(x,y) - z(-x,y)| の RMS = %.3e mm(厳密に対称)" % asym)

    centre = damage_center()
    miss = break_off(pts, centre, DEF_R)
    surv = pts[~miss]
    spacing = float(np.median(cKDTree(surv).query(surv, k=2)[0][:, 1]))
    print("  欠損: 中心 (%.0f, %.0f) mm・半径 %.0f mm -> %d 点(全体の %.1f %%)が失われた"
          % (centre[0], centre[1], DEF_R, int(miss.sum()), 100 * miss.mean()))
    print("  残った点の中央値間隔 %.3f mm(判定の閾値 tau = %.3f mm)"
          % (spacing, TAU_K * spacing))
    print("  欠損で重心が動く量: x = %+.3f mm(完全形は %+.3f mm)"
          % (surv[:, 0].mean(), pts[:, 0].mean()))

    if figs.enabled():
        Zd = np.where(np.sqrt((X - centre[0]) ** 2 + (Y - centre[1]) ** 2
                              + (Z - centre[2]) ** 2) <= DEF_R, np.nan, Z)
        holem = ins & ~np.isfinite(Zd)
        figs.save_grid(
            "scene",
            [shaded(Z, ins, xs, ys),
             np.where(ins, Z, 0.0),
             np.where(np.isfinite(Zd), shaded(Z, ins, xs, ys), 0.0),
             holem.astype(float)],
            ["完全形(陰影起伏、光源は左上)",
             "完全形の高さ [mm](0〜%.0f)" % Z[ins].max(),
             "欠損した仮面(半径 %.0f mm の球で削り取った)" % DEF_R,
             "真の欠損領域(%.0f mm^2 相当)" % (holem.sum() * (xs[1] - xs[0])
                                              * abs(ys[1] - ys[0]))],
            title="左右対称な仮面と、既知の欠損 —— 真の対称面は x = 0",
            ncols=2,
            caption="高さ場 z=f(x,y) は x について厳密に偶関数(検算 RMS %.1e mm)。"
                    "欠損は既知の球で削る。" % asym)
    return {"pts": pts, "nrm": nrm, "surv": surv, "miss": miss, "centre": centre,
            "spacing": spacing, "tau": TAU_K * spacing, "asym": asym}


# --------------------------------------------------------------------------- #
# 2. ゼロ点と、真値の面での対称復元                                             #
# --------------------------------------------------------------------------- #
def section_zero_point(S: dict) -> dict:
    print("\n" + "=" * 78)
    print("2) ゼロ点(対称性を使わない)と、真値の面での対称復元")
    print("=" * 78)
    pts, surv, miss, tau = S["pts"], S["surv"], S["miss"], S["tau"]
    gt = pts[miss]

    # (0) 何もしない
    d0, _ = cKDTree(surv).query(gt, k=1, workers=-1)
    print("  (0) 何もしない(欠損のまま)     : RMS %6.2f mm / p95 %6.2f / 最大 %6.2f"
          % (np.sqrt(np.mean(d0 ** 2)), np.percentile(d0, 95), d0.max()))

    # (1) 穴埋め補間(密な深度格子 + 調和緩和)
    fillpts, hole, X, Y, Z, ins = zero_point_fill(S["centre"], DEF_R)
    z1 = score_restoration(gt, np.vstack([surv, fillpts]), fillpts)
    print("  (1) 穴埋め補間(fill_holes)     : RMS %6.2f mm / p95 %6.2f / 最大 %6.2f"
          "(補間点 %d)" % (z1["rms"], z1["p95"], z1["max"], len(fillpts)))

    # (2) 対称復元(対称面は真値)
    r2 = restore_symmetric(surv, TRUE_P0, TRUE_N, tau)
    s2 = score_restoration(gt, r2["restored"], r2["fill"])
    print("  (2) 対称復元(面は真値)         : RMS %6.2f mm / p95 %6.2f / 最大 %6.2f"
          "(足した点 %d、偽の面 %.2f %%)"
          % (s2["rms"], s2["p95"], s2["max"], s2["n_fill"], 100 * s2["spur_frac"]))
    gain = z1["rms"] / s2["rms"]
    print("  -> 対称復元はゼロ点の %.1f 倍うまい(RMS 比)。ただしそれは"
          "「面が真値のとき」の話。" % gain)

    if figs.enabled():
        xs, ys, _, _ = grid_xy()
        S_ = 6.0
        e0 = scatter_map(gt, d0, xs, ys)
        e1 = scatter_map(gt, z1["per_pt"], xs, ys)
        e2 = scatter_map(gt, s2["per_pt"], xs, ys)
        figs.save_grid(
            "restore_error_maps",
            [with_scalebar(e0, S_, lo=0.0), with_scalebar(e1, S_, lo=0.0),
             with_scalebar(e2, S_, lo=0.0)],
            ["何もしない: RMS %.2f mm" % np.sqrt(np.mean(d0 ** 2)),
             "ゼロ点 穴埋め補間: RMS %.2f mm" % z1["rms"],
             "対称復元(面は真値): RMS %.2f mm" % s2["rms"]],
            title="欠損部の復元誤差地図 [mm](0〜%.0f mm、右端が目盛り)" % S_,
            ncols=3,
            caption="失われた真値の点から復元点群までの距離(符号なし、%.0f mm で頭打ち)。"
                    "対称復元だけが眼窩の形を取り戻す。" % S_)
    return {"zero_rms": z1["rms"], "zero_fill": fillpts, "true_rms": s2["rms"],
            "none_rms": float(np.sqrt(np.mean(d0 ** 2))), "gain": gain,
            "s2": s2, "z1": z1, "hole_grid": (hole, X, Y, Z, ins)}


# --------------------------------------------------------------------------- #
# 3. 崖 —— 対称面の角度ずれ(幾何で先に予測する)                                #
# --------------------------------------------------------------------------- #
def predict_angle(surv, fill_src_mask, alpha_deg, nrm_of):
    """角度 alpha の面ずれで鏡像点が動く量の 3 通りの予測 [mm]。

    真の面 n0=(1,0,0) を y 軸のまわりに alpha だけ倒すと、回転軸は
    w = n0 x u = (0,0,1)。点 p の変位は厳密に
        |dp| = 2 sin(alpha) * sqrt(d^2 + e^2),  d = p.n0, e = p.u
    で、これは **回転軸からの距離** r = sqrt(x^2+z^2)(u=(0,0,1) のとき)に比例する。
    面に沿った成分は面が吸うので、表面誤差に効くのは法線成分だけ。
    """
    a = np.radians(alpha_deg)
    p = np.asarray(surv, float)[fill_src_mask]
    n0 = TRUE_N
    u = np.array([0.0, 0.0, 1.0])                 # 倒す向き(y 軸まわり)
    w = np.cross(n0, u)                           # 回転軸
    d = p @ n0
    e = p @ u
    r = np.sqrt(d ** 2 + e ** 2)
    # 厳密な変位ベクトル
    n = np.cos(a) * n0 + np.sin(a) * u
    dp = 2.0 * ((p @ n0)[:, None] * n0 - (p @ n)[:, None] * n)
    nb = np.asarray(nrm_of, float)[fill_src_mask]
    nb = nb * np.sign(nb[:, [0]] * 0 + 1.0)
    nb_ref = nb - 2.0 * (nb @ n0)[:, None] * n0   # 鏡像側の法線
    normal_comp = np.abs(np.einsum("ij,ij->i", dp, nb_ref))
    return {"naive": float(2 * np.sin(a) * np.sqrt(np.mean(d ** 2))),
            "full": float(2 * np.sin(a) * np.sqrt(np.mean(r ** 2))),
            "normal": float(np.sqrt(np.mean(normal_comp ** 2))),
            "w": w}


def section_angle_cliff(S: dict, Z: dict) -> dict:
    print("\n" + "=" * 78)
    print("3) 崖(その 1)—— 対称面の角度ずれ alpha を掃引する")
    print("=" * 78)
    pts, surv, miss, tau = S["pts"], S["surv"], S["miss"], S["tau"]
    gt = pts[miss]
    nrm = S["nrm"][~miss]
    # 真値の面で「穴を埋めた鏡像」の元になった点(予測はこの集合で立てる)
    mir0 = np.asarray(_L.reflect_points(surv, TRUE_P0, TRUE_N), float)
    d0, _ = cKDTree(surv).query(mir0, k=1, workers=-1)
    src = d0 > tau                                # 穴を埋める鏡像の元になる点

    alphas = np.array([0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0])
    meas, pn, pf, pnorm, spur = [], [], [], [], []
    for a in alphas:
        n = np.array([np.cos(np.radians(a)), 0.0, np.sin(np.radians(a))])
        r = restore_symmetric(surv, TRUE_P0, n, tau)
        s = score_restoration(gt, r["restored"], r["fill"])
        p = predict_angle(surv, src, a, nrm)
        meas.append(s["rms"]); spur.append(100 * s["spur_frac"])
        pn.append(p["naive"]); pf.append(p["full"]); pnorm.append(p["normal"])
    meas = np.array(meas); pn = np.array(pn); pf = np.array(pf); pnorm = np.array(pnorm)
    floor = float(meas[0])                       # alpha=0 での標本間隔の床
    pnorm = np.sqrt(floor ** 2 + pnorm ** 2)     # 床と独立に足す

    print("  予測は 3 通り立てた(いずれも実行前に幾何から):")
    print("    (i)  2 d sin(alpha)        —— 面からの距離 d だけを見る素朴な式")
    print("    (ii) 2 r sin(alpha)        —— 回転軸からの距離 r = sqrt(d^2+e^2)(厳密な変位)")
    print("    (iii) 変位の**法線成分** (+ 標本の床 %.3f mm)—— 面に沿った分は面が吸う"
          % floor)
    print("  alpha[deg] |  実測 RMS |  (i) 素朴 |  (ii) 変位 | (iii) 法線 | 偽の面 [%]")
    for a, m, x1, x2, x3, sp in zip(alphas, meas, pn, pf, pnorm, spur):
        print("     %5.2f   |  %7.3f  |  %7.3f  |  %7.3f  |  %7.3f  |  %6.2f"
              % (a, m, x1, x2, x3, sp))
    # 予測の当たり具合(alpha >= 0.5 deg の範囲で相対誤差)
    sel = alphas >= 0.5
    rel = lambda p: float(np.mean(np.abs(p[sel] - meas[sel]) / meas[sel]) * 100)
    print("  予測の平均相対誤差(alpha >= 0.5 deg): 素朴 %.1f %% / 変位 %.1f %% / 法線 %.1f %%"
          % (rel(pn), rel(pf), rel(pnorm)))
    big = alphas >= 3.0
    print("  ★残る系統差: alpha >= 3 deg で法線予測は実測より %+.1f %% 上振れする ——"
          % float(np.mean((pnorm[big] - meas[big]) / meas[big]) * 100))
    print("    最近傍距離は**多数の候補の最小値**なので、対応点の変位より必ず小さくなる。")

    # 崖 = ゼロ点に負ける alpha
    zr = Z["zero_rms"]
    cross = np.nan
    for i in range(1, len(alphas)):
        if meas[i - 1] < zr <= meas[i]:
            cross = alphas[i - 1] + (zr - meas[i - 1]) / (meas[i] - meas[i - 1]) \
                * (alphas[i] - alphas[i - 1])
            break
    print("  崖: 対称復元がゼロ点(RMS %.2f mm)に負けるのは alpha = %.2f deg から。"
          % (zr, cross))
    print("      角度に直すと **%.0f 分角**。手で対称面を置く精度では簡単に超える。"
          % (cross * 60))

    if figs.enabled():
        figs.save_plot(
            "angle_cliff",
            [("実測", alphas, meas),
             ("予測(iii) 法線成分", alphas, pnorm),
             ("予測(ii) 2r sin a", alphas, pf),
             ("予測(i) 2d sin a", alphas, pn),
             ("ゼロ点", alphas, np.full_like(alphas, zr))],
            xlabel="alpha [deg]", ylabel="RMS [mm]", size=(700, 430),
            title="崖(1): 対称面が傾いた分だけ復元は嘘をつく",
            caption="崖は alpha = %.2f deg(%.0f 分角)。そこから先はゼロ点の"
                    "穴埋め補間のほうが正しい。" % (cross, cross * 60))
        figs.save_plot(
            "angle_spurious",
            [("偽の面になった鏡像点 [%]", alphas, np.array(spur))],
            xlabel="alpha [deg]", ylabel="偽の面 [%]", size=(700, 430),
            title="崖(1)の裏側: 穴が埋まらないのとは別に「無い面」が生える",
            caption="真の面から %.1f mm 以上浮いた鏡像点の割合。"
                    "壊れ方は 2 種類あり、別々に数える必要がある。" % SPUR_TOL)
    return {"alphas": alphas, "meas": meas, "pred": pnorm, "cross": float(cross),
            "rel": (rel(pn), rel(pf), rel(pnorm)), "spur": np.array(spur),
            "src": src, "nrm": nrm}


# --------------------------------------------------------------------------- #
# 4. 崖(その 2)—— 対称面の位置ずれ                                             #
# --------------------------------------------------------------------------- #
def section_offset_cliff(S: dict, Z: dict) -> dict:
    print("\n" + "=" * 78)
    print("4) 崖(その 2)—— 対称面の位置ずれ t を掃引する(予測は厳密に 2t)")
    print("=" * 78)
    pts, surv, miss, tau = S["pts"], S["surv"], S["miss"], S["tau"]
    gt = pts[miss]
    nrm = S["nrm"][~miss]
    mir0 = np.asarray(_L.reflect_points(surv, TRUE_P0, TRUE_N), float)
    d0, _ = cKDTree(surv).query(mir0, k=1, workers=-1)
    src = d0 > tau
    nb = nrm[src]
    nb_ref = nb - 2.0 * (nb @ TRUE_N)[:, None] * TRUE_N        # 鏡像側の法線
    cosb = float(np.sqrt(np.mean((nb_ref @ TRUE_N) ** 2)))     # |n_面 . x| の RMS
    ts = np.array([0.0, 0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0])
    meas = []
    for t in ts:
        r = restore_symmetric(surv, np.array([t, 0.0, 0.0]), TRUE_N, tau)
        meas.append(score_restoration(gt, r["restored"], r["fill"])["rms"])
    meas = np.array(meas)
    floor = float(meas[0])
    naive = 2.0 * ts                                    # 鏡像点が動く量(厳密)
    pred = np.sqrt(floor ** 2 + (2.0 * ts * cosb) ** 2)  # その法線成分 + 床
    print("  面を t だけ平行移動すると鏡像点は**厳密に 2t** 動く(位置に依らない)。")
    print("  ただし面に沿った分は面が吸うので、表面誤差に効くのは法線成分だけ:")
    print("  穴を埋める鏡像点での |n_面 . x| の RMS = %.3f -> 予測 = %.3f * 2t(+床 %.3f mm)"
          % (cosb, cosb, floor))
    print("  位置ずれ t [mm] | 実測 RMS [mm] | 素朴 2t [mm] | 法線成分の予測 [mm]")
    for t, m, a, p in zip(ts, meas, naive, pred):
        print("      %5.2f      |    %6.3f     |   %6.3f     |   %6.3f" % (t, m, a, p))
    sel = ts >= 0.5
    rel_n = float(np.mean(np.abs(naive[sel] - meas[sel]) / meas[sel]) * 100)
    rel = float(np.mean(np.abs(pred[sel] - meas[sel]) / meas[sel]) * 100)
    print("  平均相対誤差(t >= 0.5 mm): 素朴 2t は %.1f %%、法線成分は %.1f %%。" % (rel_n, rel))
    print("  ★角度ずれと違い、位置ずれは**形の広がりで増幅されない**"
          "(2t は点の位置に依らない)。")
    zr = Z["zero_rms"]
    cross = np.nan
    for i in range(1, len(ts)):
        if meas[i - 1] < zr <= meas[i]:
            cross = ts[i - 1] + (zr - meas[i - 1]) / (meas[i] - meas[i - 1]) * (ts[i] - ts[i - 1])
            break
    print("  崖: ゼロ点に負けるのは t = %.2f mm から(仮面の幅 %.0f mm の %.2f %%)。"
          % (cross, 2 * A, 100 * cross / (2 * A)))
    if figs.enabled():
        figs.save_plot(
            "offset_cliff",
            [("実測", ts, meas),
             ("予測(2t の法線成分)", ts, pred),
             ("素朴な予測 2t", ts, naive),
             ("ゼロ点", ts, np.full_like(ts, zr))],
            xlabel="t [mm]", ylabel="RMS [mm]", size=(700, 430),
            title="崖(2): 位置ずれは形に依らず 2t だけ効く",
            caption="鏡像点は厳密に 2t 動くが、表面誤差になるのはその法線成分"
                    "(|n.x| の RMS = %.2f)だけ。崖は t = %.2f mm。" % (cosb, cross))
    return {"ts": ts, "meas": meas, "cross": float(cross), "rel": rel,
            "rel_naive": rel_n, "cosb": cosb}


# --------------------------------------------------------------------------- #
# 5. 対照群 —— 対称面をどこから推定するか                                       #
# --------------------------------------------------------------------------- #
def trim_symmetric(pts, p0, n, tau, rounds=2):
    """鏡像に相手がいない点(= 欠損の反対側)を落としてから推定し直す。"""
    cur = np.asarray(pts, float)
    P0, N = np.asarray(p0, float), np.asarray(n, float)
    for _ in range(rounds):
        tree = cKDTree(cur)
        d, _ = tree.query(np.asarray(_L.reflect_points(cur, P0, N), float),
                          k=1, workers=-1)
        keep = d <= tau
        if keep.sum() < 500:
            break
        cur = cur[keep]
        est = estimate_plane(cur, refine="nm", axis_hint=True)
        P0, N = est["p0"], est["n"]
    return P0, N, len(cur)


def section_controls(S: dict, Z: dict, O: dict) -> dict:
    print("\n" + "=" * 78)
    print("5) 対照群 —— 欠損そのものが対称面の推定をどれだけ歪めるか")
    print("=" * 78)
    pts, surv, miss, tau = S["pts"], S["surv"], S["miss"], S["tau"]
    gt = pts[miss]
    rows, res = [], {}

    def run(key, label, p0, n, extra=""):
        r = restore_symmetric(surv, p0, n, tau)
        s = score_restoration(gt, r["restored"], r["fill"])
        a, o = plane_error(p0, n)
        rows.append([label, "%.3f" % a, "%.3f" % o, "%.2f" % s["rms"],
                     "%.2f" % s["max"], "%.1f" % (100 * s["spur_frac"])])
        print("  %-30s 角度 %7.3f deg / 位置 %6.3f mm -> RMS %6.2f mm / 最大 %6.2f"
              " / 偽の面 %5.1f %% %s"
              % (label, a, o, s["rms"], s["max"], 100 * s["spur_frac"], extra))
        res[key] = {"ang": a, "off": o, "rms": s["rms"], "max": s["max"],
                    "spur": s["spur_frac"], "p0": p0, "n": n}

    # まず PCA の候補そのものを見る —— 欠損は面をずらす前に「軸を取り違えさせる」
    e_full_auto = estimate_plane(pts, refine="none")
    e_dmg_auto = estimate_plane(surv, refine="none")
    print("  PCA 候補のスコア(小さいほど対称。detect_reflection_symmetry の all_scores):")
    print("    完全形 : %s -> 選ばれた軸は x から %.2f deg"
          % (" / ".join("%.2f" % v for v in e_full_auto["all_scores"]),
             e_full_auto["auto_axis_deg"]))
    print("    欠損後 : %s -> 選ばれた軸は x から %.2f deg"
          % (" / ".join("%.2f" % v for v in e_dmg_auto["all_scores"]),
             e_dmg_auto["auto_axis_deg"]))
    print("  ★★ 欠損は対称面を**少しずらす**のではなく、"
          "候補の順位を入れ替えて**別の軸へ飛ばす**。")

    run("truth", "(a) 真値の面", TRUE_P0, TRUE_N)

    e_full = estimate_plane(pts, refine="nm")                    # 完全形から(自動)
    run("full", "(b) 完全形から推定(自動)", e_full["p0"], e_full["n"])

    e_dmg = estimate_plane(surv, refine="nm")                    # 欠損したまま(自動)
    run("damaged_auto", "(c) 欠損のまま推定(自動)", e_dmg["p0"], e_dmg["n"])

    e_hint = estimate_plane(surv, refine="nm", axis_hint=True)   # 軸は人が選ぶ
    run("damaged", "(c') 欠損のまま・軸は人が選ぶ", e_hint["p0"], e_hint["n"])

    p0t, nt, nkeep = trim_symmetric(surv, e_hint["p0"], e_hint["n"], tau)
    run("trim", "(d) (c')+対称トリミング", p0t, nt, "(残した点 %d)" % nkeep)

    e_icp = estimate_plane(surv, refine="icp", axis_hint=True)
    run("icp", "(e) (c')の軸 + 鏡映+ICP+中点面", e_icp["p0"], e_icp["n"])

    e_c = estimate_plane(surv, refine="none", axis_hint=True)
    run("coarse", "(f) 粗のみ(重心を通す面)", e_c["p0"], e_c["n"])

    print("\n  推定器そのものの偏り(b): 角度 %.3f deg / 位置 %.3f mm"
          "(完全形でもゼロにはならない)" % (res["full"]["ang"], res["full"]["off"]))
    print("  欠損が加える歪み(c' - b): 角度 %+.3f deg / 位置 %+.3f mm"
          % (res["damaged"]["ang"] - res["full"]["ang"],
             res["damaged"]["off"] - res["full"]["off"]))
    print("  軸を取り違えた場合(c)の代償: 復元 RMS %.2f -> %.2f mm"
          % (res["damaged"]["rms"], res["damaged_auto"]["rms"]))
    print("  ★予想は外れた。欠損は重心を x = %+.2f mm 動かすので"
          "「面もそれだけずれる」と踏んでいた —— " % surv[:, 0].mean())
    print("    重心を通す粗い面 (f) は確かに %.2f mm ずれる(同時に %.2f deg 傾く)。"
          % (res["coarse"]["off"], res["coarse"]["ang"]))
    print("    位置ぶんだけで 4 節の式が %.2f mm を予測し、実測は %.2f mm"
          "(残りは角度ぶん)。しかし "
          % (np.sqrt(O["meas"][0] ** 2 + (2 * res["coarse"]["off"] * O["cosb"]) ** 2),
             res["coarse"]["rms"]))
    print("    残差を掃引する精緻化 (c') は重心を使わないので %.3f mm まで戻す"
          "(粗い面のずれの %.0f %% を吸う)。"
          % (res["damaged"]["off"],
             100 * (1 - res["damaged"]["off"] / res["coarse"]["off"])))
    print("  ★ (e) 鏡映+ICP+中点面は**悪化した**(角度 %.2f deg / RMS %.2f mm)。"
          % (res["icp"]["ang"], res["icp"]["rms"]))
    print("    欠損側では対応が付かないまま偽の対が中点に混ざり、"
          "最小二乗の面がそれに引かれる。")
    print("  ★ (c) の復元 RMS %.2f mm は「何もしない %.2f mm」よりずっと小さい ——"
          % (res["damaged_auto"]["rms"], Z["none_rms"]))
    print("    軸を 90 度取り違えても**もっともらしい面**が生える"
          "(足した点の %.0f %% は真の面から %.1f mm 以上浮いている)ので、"
          % (100 * res["damaged_auto"]["spur"], SPUR_TOL))
    print("    復元誤差そのものでは気づけない。偽の面の割合を別に数えること。")

    if figs.enabled():
        figs.save_table(
            "controls", ["対称面の出どころ", "角度誤差 [deg]", "位置誤差 [mm]",
                         "復元 RMS [mm]", "復元 最大 [mm]", "偽の面 [%]"],
            rows, title="対照群: 対称面をどこから推定するか",
            caption="(b) と (c) の差が「欠損そのものが推定を歪める量」。"
                    "ゼロ点(穴埋め補間)は RMS %.2f mm。" % Z["zero_rms"])
        xs, ys, _, _ = grid_xy()
        S_ = 6.0
        panels, caps = [], []
        for key, lab in (("truth", "真値の面"),
                         ("damaged_auto", "欠損のまま自動推定(軸ごと飛ぶ)"),
                         ("damaged", "軸は人が選ぶ"),
                         ("trim", "対称トリミング後")):
            r = restore_symmetric(surv, res[key]["p0"], res[key]["n"], tau)
            s = score_restoration(gt, r["restored"], r["fill"])
            panels.append(with_scalebar(scatter_map(gt, s["per_pt"], xs, ys), S_, lo=0.0))
            caps.append("%s: RMS %.2f mm" % (lab, s["rms"]))
        figs.save_grid("controls_maps", panels, caps,
                       title="対照群の復元誤差地図 [mm](0〜%.0f mm)" % S_,
                       ncols=2,
                       caption="欠損のまま推定した面で復元すると、"
                               "欠損部の全体が一様にずれる(位置ずれの署名)。")
    return res


# --------------------------------------------------------------------------- #
# 6. 欠損の大きさ・位置の掃引                                                   #
# --------------------------------------------------------------------------- #
def section_defect_sweep(S: dict) -> dict:
    print("\n" + "=" * 78)
    print("6) 欠損の大きさを振る —— 軸を取り違える境目はどこか")
    print("=" * 78)
    pts = S["pts"]
    radii = np.array([10.0, 16.0, 20.0, 23.0, 26.0, 30.0, 34.0, 42.0, 50.0])
    angs, offs, rmss, fr, flip, cx = [], [], [], [], [], []
    for r in radii:
        c = damage_center()
        miss = break_off(pts, c, r)
        surv = pts[~miss]
        tau = TAU_K * float(np.median(cKDTree(surv).query(surv, k=2)[0][:, 1]))
        auto = estimate_plane(surv, refine="none")
        est = estimate_plane(surv, refine="nm", axis_hint=True)
        a, o = plane_error(est["p0"], est["n"])
        rr = restore_symmetric(surv, est["p0"], est["n"], tau)
        s = score_restoration(pts[miss], rr["restored"], rr["fill"])
        angs.append(a); offs.append(o); rmss.append(s["rms"])
        fr.append(100 * miss.mean()); flip.append(bool(auto["flipped"]))
        cx.append(abs(float(surv[:, 0].mean())))
        print("  半径 %4.0f mm(失った点 %5.1f %%): 自動の軸 %s / 重心のずれ %5.2f mm"
              " -> 角度 %6.3f deg・位置 %6.3f mm・復元 RMS %6.2f mm"
              % (r, 100 * miss.mean(), "取り違え" if flip[-1] else "正しい ",
                 cx[-1], a, o, s["rms"]))
    angs = np.array(angs); offs = np.array(offs); rmss = np.array(rmss)
    fr = np.array(fr); cx = np.array(cx)
    first = int(np.argmax(flip)) if any(flip) else -1
    if first > 0:
        print("  ★ 自動選択が軸を取り違えるのは、失った点が %.1f %% を超えたあたり"
              "(半径 %.0f -> %.0f mm の間)。"
              % (fr[first - 1], radii[first - 1], radii[first]))
    print("  ★ 軸さえ正しければ復元 RMS は %.2f〜%.2f mm でほぼ平ら —— "
          "崖は欠損の大きさでなく**軸の取り違え**にある。" % (rmss.min(), rmss.max()))
    print("     重心は最大 %.1f mm 動くのに、精緻化後の面の位置誤差は残り %s %%"
          % (cx.max(), " ".join("%.0f" % v for v in 100 * offs / np.maximum(cx, 1e-9))))
    if figs.enabled():
        figs.save_plot(
            "defect_size",
            [("面の位置誤差 [mm]", radii, offs),
             ("重心の x ずれ [mm]", radii, cx),
             ("復元 RMS [mm]", radii, rmss),
             ("面の角度誤差 [deg]", radii, angs)],
            xlabel="欠損半径 [mm]", ylabel="誤差", size=(700, 430),
            title="欠損が大きいほど対称面がずれる —— 主因は重心の移動",
            caption="正しい軸に固定しても位置は重心のずれに引きずられる。"
                    "自動選択が軸を取り違えるのは失った点 %.1f %% 以上。"
                    % (fr[first - 1] if first > 0 else 0.0))
    return {"radii": radii, "ang": angs, "off": offs, "rms": rmss, "frac": fr,
            "flip": flip, "first": first, "cx": cx}


# --------------------------------------------------------------------------- #
# 7. 偽陽性 —— 本当は対称でない形に対称復元をかける                             #
# --------------------------------------------------------------------------- #
def section_false_symmetry(S: dict) -> dict:
    print("\n" + "=" * 78)
    print("7) 偽陽性 —— 本当は対称でない形(片側の装飾 + 経年のねじれ)")
    print("=" * 78)
    sc = sample_mask(N_WORK, SEED, deco=DECO_A, warp=WARP_A)
    pts = sc["pts"]
    xs, ys, X, Y = grid_xy()
    Z, ins = mask_height(X, Y, DECO_A, WARP_A)
    Zm, _ = mask_height(-X, Y, DECO_A, WARP_A)
    da = (Z - Zm)
    asym_true = float(np.sqrt(np.mean(da[ins] ** 2)))
    print("  仕込んだ非対称: 右頬の装飾 %.1f mm + ねじれ %.1f mm"
          " -> |z(x,y)-z(-x,y)| の RMS = %.3f mm(最大 %.2f mm)"
          % (DECO_A, WARP_A, asym_true, np.abs(da[ins]).max()))

    est = estimate_plane(pts, refine="nm")
    a_e, o_e = plane_error(est["p0"], est["n"])
    est_sym = estimate_plane(S["pts"], refine="nm")
    a_s, o_s = plane_error(est_sym["p0"], est_sym["n"])
    print("  非対称な形から推定した対称面: 角度 %.3f deg / 位置 %.3f mm"
          "(対称な形では %.3f deg / %.3f mm)" % (a_e, o_e, a_s, o_s))

    out, rows = {}, []
    px = xs[1] - xs[0]
    py = abs(ys[1] - ys[0])
    for side, sx in (("装飾のある側(右)", +1.0), ("無地の側(左)", -1.0)):
        c = damage_center((sx * DECO_X, DECO_Y), DECO_A, WARP_A)
        miss = break_off(pts, c, 30.0)
        surv = pts[~miss]
        tau = TAU_K * float(np.median(cKDTree(surv).query(surv, k=2)[0][:, 1]))
        r = restore_symmetric(surv, TRUE_P0, TRUE_N, tau)   # 面は真値(最良条件)
        s = score_restoration(pts[miss], r["restored"], r["fill"], DECO_A, WARP_A)
        # 同じ欠損を **対称な形**に入れた対照(非対称そのものの寄与を分ける)
        c0 = damage_center((sx * DECO_X, DECO_Y))
        miss0 = break_off(S["pts"], c0, 30.0)
        surv0 = S["pts"][~miss0]
        tau0 = TAU_K * float(np.median(cKDTree(surv0).query(surv0, k=2)[0][:, 1]))
        r0 = restore_symmetric(surv0, TRUE_P0, TRUE_N, tau0)
        s0 = score_restoration(S["pts"][miss0], r0["restored"], r0["fill"])
        # 高さ場での捏造 / 消失(格子で積む)
        hole = (np.sqrt((X - c[0]) ** 2 + (Y - c[1]) ** 2 + (Z - c[2]) ** 2) <= 30.0) & ins
        dz = Zm - Z                     # 復元後(=鏡像)- 真値
        fab = float(np.clip(dz[hole], 0, None).sum() * px * py)     # 捏造 [mm^3]
        ers = float(np.clip(-dz[hole], 0, None).sum() * px * py)    # 消失 [mm^3]
        peak = float(np.abs(dz[hole]).max())
        print("  %-16s 欠損 %d 点 -> 復元 RMS %5.2f mm(対称な形の対照は %.2f mm)"
              % (side, int(miss.sum()), s["rms"], s0["rms"]))
        print("       捏造された肉 %7.1f mm^3 / 消された肉 %7.1f mm^3 / 高さの最大差 %.2f mm"
              % (fab, ers, peak))
        rows.append([side, "%d" % int(miss.sum()), "%.2f" % s["rms"], "%.2f" % s0["rms"],
                     "%.1f" % fab, "%.1f" % ers, "%.2f" % peak])
        out[side] = {"rms": s["rms"], "ctrl_rms": s0["rms"], "fab": fab, "ers": ers,
                     "peak": peak, "hole": hole, "c": c}

    # 復元後の見かけの非対称度(欠損部は定義上ぴったり対称になる)
    for side in out:
        h = out[side]["hole"]
        out[side]["asym_in_hole"] = float(np.sqrt(np.mean(da[h] ** 2)))
        out[side]["asym_after"] = float(np.sqrt(np.mean(np.where(h, 0.0, da)[ins] ** 2)))
    print("  ★★ 欠損部だけを見ると、真の非対称は RMS %.2f / %.2f mm あったのに"
          % (out["装飾のある側(右)"]["asym_in_hole"], out["無地の側(左)"]["asym_in_hole"]))
    print("     復元後は**厳密に 0**(鏡像なので)。仮面全体でも %.3f mm -> %.3f / %.3f mm。"
          % (asym_true, out["装飾のある側(右)"]["asym_after"],
             out["無地の側(左)"]["asym_after"]))
    print("     復元した所は定義上ぴったり対称なので、"
          "「対称だから正しい」という検算は原理的にできない。")

    if figs.enabled():
        S_ = 3.5
        pan, cap = [], []
        pan.append(shaded(Z, ins, xs, ys)); cap.append("真の形(右頬に装飾+ねじれ)")
        pan.append(with_scalebar(np.where(ins, da, 0.0), S_))
        cap.append("真の非対称 [mm](RMS %.2f)" % asym_true)
        short = {"無地の側(左)": "左(無地)を欠損: 捏造 %.0f mm^3",
                 "装飾のある側(右)": "右(装飾)を欠損: 消失 %.0f mm^3"}
        for side in ("無地の側(左)", "装飾のある側(右)"):
            h = out[side]["hole"]
            pan.append(with_scalebar(np.where(h, Zm - Z, 0.0), S_))
            cap.append(short[side] % (out[side]["fab"] + out[side]["ers"]))
        figs.save_grid("false_symmetry", pan, cap,
                       title="偽陽性: 対称でない形に対称復元をかけると何が起きるか",
                       ncols=2, signed=[False, True, True, True],
                       caption="欠損がどちら側かで、装飾は**複製される**か"
                               "**消される**かが決まる(面は真値でもこうなる)。")
        figs.save_table(
            "false_symmetry_table",
            ["欠損の側", "失った点", "復元 RMS [mm]", "対称な形の対照 [mm]",
             "捏造 [mm^3]", "消失 [mm^3]", "高さの最大差 [mm]"], rows,
            title="偽陽性: 実在しない対称性を作った量",
            caption="真の非対称 RMS %.2f mm。復元部は定義上ぴったり対称になるので、"
                    "見かけの非対称度は %.2f -> %.2f / %.2f mm に下がる。"
                    % (asym_true, asym_true,
                       out["装飾のある側(右)"]["asym_after"],
                       out["無地の側(左)"]["asym_after"]))
    return {"asym_true": asym_true, "ang": a_e, "off": o_e, "out": out}


# --------------------------------------------------------------------------- #
# 8. 道具の穴                                                                   #
# --------------------------------------------------------------------------- #
def section_tool_gaps(S: dict) -> None:
    print("\n" + "=" * 78)
    print("8) 道具の穴(symmetry3d 族を使ってみて)")
    print("=" * 78)
    P = S["surv"][:6000]
    t0 = time.perf_counter()
    for _ in range(10):
        _L.reflection_symmetry_score(P, TRUE_P0, TRUE_N)
    t_pub = (time.perf_counter() - t0) / 10
    tree = cKDTree(P)
    t0 = time.perf_counter()
    for _ in range(10):
        sym_residual(P, tree, TRUE_P0, TRUE_N)
    t_own = (time.perf_counter() - t0) / 10
    print("  (a) 面を掃引する口が無い。``detect_reflection_symmetry`` の候補は"
          "PCA の 3 軸だけで、")
    print("      精緻化は呼び手が書く。公開の score は毎回 KD 木と中央値間隔を"
          "作り直すので")
    print("      1 回 %.1f ms(自前の使い回しは %.1f ms、%.0f 倍)。掃引 200 回で差が出る。"
          % (1e3 * t_pub, 1e3 * t_own, t_pub / max(t_own, 1e-9)))
    assert not hasattr(fs, "refine_reflection_symmetry")
    assert not hasattr(_L, "refine_reflection_symmetry")
    print("  (b) 対称性で欠損を埋める op が無い(鏡映 + 近傍しきい値は呼び手が書いた)。")
    assert not hasattr(_L, "symmetrize_points") and not hasattr(_L, "complete_by_symmetry")
    print("  (c) 3-D の点群向けの穴埋めが無い。``fill_holes`` は深度画像 (H,W) 専用なので、")
    print("      いったん高さ場に落とした(点群のままでは通らない)。")
    assert not hasattr(_L, "fill_holes_points")
    print("  (d) ``icp_point2point_3d`` は torch のテンソルを返す(numpy で受けるには"
          "``np.asarray``)。")
    print("      台帳経由 ``_L.icp_point2point_3d(...)`` は宣言 out 型なので"
          "``.raw`` で (R, t, info) を取った。")
    print("  (e) 反射の合成(鏡映と剛体変換の積から対称面を取り出す)口が無いので、"
          "対応点の中点に")
    print("      ``fit_plane_3d`` をあてた。これは正しいが、"
          "**面の近くの点が自分自身と組む**のを外す必要がある(自前)。")


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("=" * 78)
    print("対称性を使った欠損復元 —— 対称面がずれた分だけ復元は嘘をつく")
    print("仮面 %.0f x %.0f mm / 真の対称面 x = 0 / 欠損は半径 %.0f mm の球"
          % (2 * A, 2 * B, DEF_R))
    print("=" * 78)

    S = section_scene()
    Z = section_zero_point(S)
    Aeng = section_angle_cliff(S, Z)
    O = section_offset_cliff(S, Z)
    C = section_controls(S, Z, O)
    D = section_defect_sweep(S)
    F = section_false_symmetry(S)
    section_tool_gaps(S)

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 面が真値なら対称復元はゼロ点(穴埋め補間)の %.1f 倍うまい"
          "(%.2f -> %.2f mm)。" % (Z["gain"], Z["zero_rms"], Z["true_rms"]))
    print("  * 崖は角度 %.2f deg(%.0f 分角)/ 位置 %.2f mm。"
          "そこから先はゼロ点のほうが正しい。" % (Aeng["cross"], Aeng["cross"] * 60,
                                                O["cross"]))
    print("  * 角度の効き方は 2 r sin(alpha) の**法線成分**で予測できる"
          "(相対誤差 %.1f %%)。素朴な 2 d sin(alpha) は %.1f %% 外す。"
          % (Aeng["rel"][2], Aeng["rel"][0]))
    print("  * 欠損は面を「ずらす」前に**軸ごと飛ばす**。失った点が %.1f %% を超えると"
          "PCA の候補順位が入れ替わった。" % (D["frac"][D["first"] - 1] if D["first"] > 0
                                              else float("nan")))
    print("  * 重心を通す粗い面は %.2f mm ずれるが、残差の掃引がその %.0f %% を吸う"
          "(残り %.3f mm、完全形なら %.3f mm)。"
          % (C["coarse"]["off"], 100 * (1 - C["damaged"]["off"] / C["coarse"]["off"]),
             C["damaged"]["off"], C["full"]["off"]))
    print("  * 対称でない形では、欠損の側で装飾が %.0f mm^3 捏造されるか"
          " %.0f mm^3 消されるかが決まる(面が真値でも)。"
          % (F["out"]["無地の側(左)"]["fab"], F["out"]["装飾のある側(右)"]["ers"]))

    # 所見を固定する
    assert Z["true_rms"] < Z["zero_rms"], "面が真値なら対称復元が勝つはず"
    assert Aeng["cross"] < 3.0, "崖が甘すぎる"
    assert Aeng["rel"][2] < Aeng["rel"][0], "法線成分の予測が素朴式に負けた"
    assert O["rel"] < O["rel_naive"], "位置ずれも法線成分のほうが当たるはず"
    assert C["damaged"]["off"] > 2 * C["full"]["off"], "欠損の歪みが出ていない"
    assert C["coarse"]["off"] > 10 * C["damaged"]["off"], "粗い面の重心ずれが出ていない"
    assert C["trim"]["off"] < C["damaged"]["off"], "対称トリミングが効いていない"
    assert C["damaged_auto"]["ang"] > 45.0, "自動選択が軸を取り違える所見が消えた"
    assert D["first"] > 0, "軸の取り違えが起きる境目が掃引の中に無い"
    assert F["out"]["無地の側(左)"]["fab"] > 100.0, "捏造が測れていない"
    assert F["out"]["装飾のある側(右)"]["ers"] > 100.0, "消失が測れていない"
    assert F["out"]["装飾のある側(右)"]["rms"] > 1.8 * F["out"]["装飾のある側(右)"]["ctrl_rms"], \
        "非対称そのものの寄与が対照より大きくない"

    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
