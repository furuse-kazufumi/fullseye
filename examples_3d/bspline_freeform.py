# -*- coding: utf-8 -*-
"""事例: B スプラインで自由曲線・自由曲面を張り、再サンプル/平滑/残差計測まで通す (freeform_geometry).

平たく言うと: 直線・平面・円のような大域基底では表せない「くねる曲線」「うねる曲面」を、
区分多項式(B スプライン)で局所的に曲げて復元する。順序付き 3D 点列(シーム/軌跡)は
自由曲線 r(u) に、散布した (x,y,z) 高さは自由曲面 z=f(x,y) に当てはめる。曲線側では弧長で
等間隔に打ち直す(resample)・ノイズを平滑で吸う、曲面側では観測と当てはめの逸脱量(残差)を
測る、という計測の一連を 1 本に通す。

検証(GT): すべて解析的な真値を持つ合成データで裏取りする。
  - 曲面: 既知の f(x,y)=0.7 sin(1.6x)cos(1.3y)+0.3 xy を散布サンプルから復元し、
    学習に使っていない格子点で解析真値との RMS が小さいこと(eval_bspline_surface)。
  - 曲面残差: surface_residual の RMS が、同じ点に対する「平面 null(kx=ky=1・強平滑)」の
    残差を桁違いに下回ること(自由曲面がうねりを本当に捉えている)。
  - 曲線: 螺旋 r(θ)=(cosθ,sinθ,0.3θ) 上の点列を fit_bspline_curve→eval_bspline_curve で
    密に復元し、各評価点の解析螺旋への最近傍距離が微小(かつ二度呼んで決定的)。
  - 再サンプル: θ を偏らせた非一様な生ポリラインを resample_uniform で弧長等間隔化し、
    区間長の変動係数(CV)が激減し全長がほぼ保存されること。
  - 平滑: ノイズを乗せた螺旋を fit_spline_curve で平滑すると、真の螺旋への幾何誤差が
    ノイズ入力より小さくなること。

beat-the-null: (曲面) 大域平均を返すだけの null / 最小二乗平面 null を残差で明確に下回る。
(曲線) 復元曲線の解析螺旋への距離が、螺旋軸の直線 null への距離(≈半径 1.0)を桁違いに下回る。
(平滑) 平滑後誤差 < 平滑前(ノイズ)誤差。いずれも「偶然当たった」のではなく形状を捉えた証拠。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np
import curve3d as cv          # resample_uniform, fit_spline_curve
import bspline_surf as bs     # fit/eval bspline surface & curve, surface_residual


def nearest_dist(pts, dense):
    """pts (P,3) の各点から dense (Q,3) への最近傍距離 (P,)。"""
    pts = np.asarray(pts, float)
    dense = np.asarray(dense, float)
    out = np.empty(len(pts))
    for i, p in enumerate(pts):
        out[i] = np.min(np.linalg.norm(dense - p, axis=1))
    return out


# =========================================================================== #
# 自由曲面 z = f(x, y) — fit_bspline_surface / eval_bspline_surface / surface_residual
# =========================================================================== #
def f_surface(x, y):
    """既知の自由曲面(平面や単純多項式では表せないうねり)。"""
    return 0.7 * np.sin(1.6 * x) * np.cos(1.3 * y) + 0.3 * x * y


rng = np.random.default_rng(7)
# 学習: ドメイン [-1.2,1.2]^2 に散布サンプル(ノイズ無し=丸め以外)
xt = rng.uniform(-1.2, 1.2, 600)
yt = rng.uniform(-1.2, 1.2, 600)
zt = f_surface(xt, yt)

# --- 1) 自由曲面フィット(双三次 B スプライン) ---------------------------------
tck_s = bs.fit_bspline_surface(xt, yt, zt, kx=3, ky=3, smooth=1e-3)

# --- 2) GT: 学習に使っていない内部格子で解析真値と照合(eval_bspline_surface) -----
gx = np.linspace(-0.9, 0.9, 25)
gy = np.linspace(-0.9, 0.9, 25)
Z_pred = bs.eval_bspline_surface(tck_s, gx, gy, grid=True)   # (25,25)
XX, YY = np.meshgrid(gx, gy, indexing="ij")
Z_true = f_surface(XX, YY)
surf_rms = float(np.sqrt(np.mean((Z_pred - Z_true) ** 2)))
null_rms = float(np.std(Z_true))                             # 大域平均を返すだけの null
print(f"[surface] held-out RMS = {surf_rms:.4e}  (mean-null RMS = {null_rms:.4e})")
assert Z_pred.shape == (25, 25)
assert np.all(np.isfinite(Z_pred))
assert surf_rms < 0.03, f"自由曲面が真値を復元できていない: {surf_rms:.4e}"
assert surf_rms < 0.05 * null_rms, "曲面フィットが大域平均 null を判別的に下回れていない"

# --- 3) surface_residual: 自由曲面 vs 平面 null(kx=ky=1・強平滑)の残差比較 --------
res_free = bs.surface_residual(xt, yt, zt, tck_s)
tck_plane = bs.fit_bspline_surface(xt, yt, zt, kx=1, ky=1, smooth=1e6)   # 最小二乗平面へ潰す
res_plane = bs.surface_residual(xt, yt, zt, tck_plane)
print(f"[surface] residual rms free = {res_free['rms']:.4e} / plane-null = {res_plane['rms']:.4e}"
      f"  (max={res_free['max']:.3e}, pv={res_free['pv']:.3e})")
assert set(res_free) == {"rms", "max", "pv"}
assert res_free["rms"] < 0.03, "自由曲面の当てはめ残差が大きすぎる"
assert res_free["rms"] < 0.2 * res_plane["rms"], \
    "自由曲面残差が平面 null 残差を判別的に下回れていない(うねりを捉えていない)"

# =========================================================================== #
# 自由曲線(螺旋) — fit_bspline_curve / eval_bspline_curve
# =========================================================================== #
a, b = 1.0, 0.3
theta_dense = np.linspace(0.0, 4.0 * np.pi, 5000)
helix_dense = np.stack([a * np.cos(theta_dense), a * np.sin(theta_dense), b * theta_dense], axis=1)

# 螺旋上の順序付き標本(真に曲線上、一様 θ)
theta_s = np.linspace(0.0, 4.0 * np.pi, 48)
pts_curve = np.stack([a * np.cos(theta_s), a * np.sin(theta_s), b * theta_s], axis=1)

# --- 4) 曲線フィット→密評価(FITPACK パラメトリック) --------------------------
tck_c = bs.fit_bspline_curve(pts_curve, smooth=0.0, k=3)     # 補間
curve_eval = bs.eval_bspline_curve(tck_c, n=400)             # (400,3)
curve_eval2 = bs.eval_bspline_curve(tck_c, n=400)
assert curve_eval.shape == (400, 3)
assert np.array_equal(curve_eval, curve_eval2), "eval_bspline_curve が決定的でない"

d_curve = nearest_dist(curve_eval, helix_dense)
# beat-null: 螺旋軸の直線(半径ぶんずれる)への距離
axis_null = np.stack([np.zeros(400), np.zeros(400), np.linspace(0, b * 4 * np.pi, 400)], axis=1)
d_axis = nearest_dist(axis_null, helix_dense)
print(f"[curve] eval→helix  mean={d_curve.mean():.4e} max={d_curve.max():.4e}"
      f"  (axis-null mean={d_axis.mean():.4e})")
assert d_curve.max() < 0.03, f"復元曲線が螺旋から外れている: max={d_curve.max():.4e}"
assert d_curve.mean() < 0.05 * d_axis.mean(), "復元曲線が軸 null を判別的に下回れていない"

# =========================================================================== #
# 弧長再サンプル — resample_uniform
# =========================================================================== #
# 生ポリライン: θ を二乗で偏らせて非一様な区間長にする
theta_raw = 4.0 * np.pi * (np.linspace(0.0, 1.0, 60) ** 2)
raw = np.stack([a * np.cos(theta_raw), a * np.sin(theta_raw), b * theta_raw], axis=1)

# --- 5) 弧長等間隔へ打ち直し --------------------------------------------------
uni = cv.resample_uniform(raw, 400)
assert uni.shape == (400, 3)


def seg_cv(poly):
    seg = np.linalg.norm(np.diff(poly, axis=0), axis=1)
    return float(np.std(seg) / (np.mean(seg) + 1e-12))


cv_raw, cv_uni = seg_cv(raw), seg_cv(uni)
len_raw = float(np.sum(np.linalg.norm(np.diff(raw, axis=0), axis=1)))
len_uni = float(np.sum(np.linalg.norm(np.diff(uni, axis=0), axis=1)))
print(f"[resample] seg-length CV  raw={cv_raw:.3f} -> uniform={cv_uni:.3e}"
      f"   length raw={len_raw:.4f} uni={len_uni:.4f}")
assert cv_raw > 0.5, "生ポリラインが十分に非一様でない(前提崩れ)"
assert cv_uni < 0.05, f"再サンプル後も区間長が一様でない: CV={cv_uni:.3e}"
assert cv_uni < 0.1 * cv_raw, "再サンプルが区間長の非一様性を判別的に均せていない"
assert abs(len_uni - len_raw) / len_raw < 0.02, "再サンプルで全長が保存されていない"

# =========================================================================== #
# 平滑 — fit_spline_curve(curve3d, ノイズ除去)
# =========================================================================== #
noise = 0.03
noisy = pts_curve + rng.normal(0.0, noise, pts_curve.shape)
smoothed = cv.fit_spline_curve(noisy, smooth=len(noisy) * noise ** 2, k=3)
assert smoothed.shape == pts_curve.shape

err_noisy = nearest_dist(noisy, helix_dense).mean()
err_smooth = nearest_dist(smoothed, helix_dense).mean()
print(f"[smooth] mean dist to helix  noisy={err_noisy:.4e} -> smoothed={err_smooth:.4e}")
assert err_smooth < err_noisy, "平滑後がノイズ入力より真の螺旋に近づいていない"
assert err_smooth < 0.8 * err_noisy, "平滑のノイズ除去効果が判別的でない"

print(f"PASS: 自由曲面を散布点から復元(held-out RMS {surf_rms:.2e} << mean-null {null_rms:.2e}、"
      f"残差 {res_free['rms']:.2e} << 平面null {res_plane['rms']:.2e})、螺旋を "
      f"fit/eval_bspline_curve で復元(max {d_curve.max():.2e} << 軸null {d_axis.mean():.2e})、"
      f"resample_uniform で区間長CV {cv_raw:.2f}->{cv_uni:.1e}(全長保存)、"
      f"fit_spline_curve でノイズ誤差 {err_noisy:.2e}->{err_smooth:.2e} に低減")
