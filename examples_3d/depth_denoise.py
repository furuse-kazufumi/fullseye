# -*- coding: utf-8 -*-
"""事例: エッジ保存の深度デノイズ + 穴埋め。

深度センサ(ToF/構造化光/LiDAR)の生画像は、ノイズと無効画素(no-return, 影, 反射欠損=穴)を
必ず含む。素朴なガウス平滑はノイズを消す代わりに、前景/背景の段差(不連続)までぼかしてしまい、
下流の法線推定・地面除去・把持点判定を壊す。ここでは
  1) fill_holes で浅い穴を近傍の平面値で埋め(調和緩和)、
  2) bilateral_filter_depth で段差を保存したままノイズだけを平滑する、
という前処理を行い、(a)段差が残る (b)ノイズが減る (c)穴が平面値で埋まる を数値で確認する。
対照として素朴ガウスが段差をぼかすことも示す(bilateral の優位の判別)。
"""
import numpy as np
from scipy import ndimage
import depth_bilateral as DB


def rmse(a, b, sl=np.s_[5:-5, 5:-5]):
    """内側領域(境界パディングの影響を避ける)の RMSE。"""
    return float(np.sqrt(np.mean((a[sl] - b[sl]) ** 2)))


def edge_jump(a, col, rows=np.s_[6:-6]):
    """段差列 col と col-1 の隣接列深度差の平均(段差の鮮鋭さの指標)。"""
    return float(np.mean(a[rows, col] - a[rows, col - 1]))


# 合成データ: 区分的平面(共通の緩い傾斜 + 中央列で段差)+ ノイズ + 穴
H = W = 48
uu, vv = np.meshgrid(np.arange(W), np.arange(H))
base = 20.0
slope_x, slope_y = 0.05, 0.03
col = W // 2
step = 0.2 * base                       # 段差 = 4.0(前景/背景の不連続)
clean = base + slope_x * uu + slope_y * vv
clean[:, col:] += step                  # 右半分が step だけ手前(段差)

rng = np.random.default_rng(0)
noise_std = 0.02 * base                 # ノイズ std = 0.4
noisy = clean + rng.normal(0.0, noise_std, clean.shape)

# 浅い穴(左の平面領域内、段差から離す)を sentinel=0 で作る。
hole = np.zeros((H, W), bool)
hole[20:24, 10:14] = True               # 4x4、最寄り有効画素まで <=2px の浅い穴
depth_in = noisy.copy()
depth_in[hole] = 0.0                    # 0 = 無効(no-return を模擬)

ss = 2.0
sr = 3.0 * noise_std                    # noise_std(0.4) < range_sigma(1.2) < step(4.0)

# ステップ1: 穴埋め(調和緩和で近傍の平面値へ補間)
filled = DB.fill_holes(depth_in, max_radius=6.0)
assert not np.any(np.isnan(filled[hole])), "浅い穴が埋まっていない"
hole_err = rmse(filled, clean, sl=hole)          # 埋めた値 vs 真の平面値
print("[穴埋め] 埋めた画素の対真値RMSE = %.4f (ノイズstd=%.3f, 段差=%.1f)"
      % (hole_err, noise_std, step))
# 穴は平面領域なので真の平面値に埋まる(誤差はノイズstd以下、段差の1/10未満)。
assert hole_err < noise_std, hole_err
assert hole_err < 0.1 * step, hole_err

# ステップ2: bilateral デノイズ(段差保存) vs 対照ガウス
filt = DB.bilateral_filter_depth(filled, ss, sr)
gauss = ndimage.gaussian_filter(filled, ss)      # 対照: 段差もぼかす素朴平滑

rmse_noisy = rmse(noisy, clean)
rmse_bilat = rmse(filt, clean)
rmse_gauss = rmse(gauss, clean)
print("[デノイズ] RMSE  noisy=%.4f  bilateral=%.4f  gauss=%.4f" % (rmse_noisy, rmse_bilat, rmse_gauss))
# (b) ノイズが減る: bilateral は入力ノイズの半分未満、かつ段差をぼかすガウスより良い。
assert rmse_bilat < 0.5 * rmse_noisy, rmse_bilat
assert rmse_bilat < rmse_gauss, (rmse_bilat, rmse_gauss)

# (a) 段差保存: 隣接列ジャンプ / 真の段差。bilateral≈1、ガウスは大きくぼける。
true_jump = edge_jump(clean, col)
r_bilat = edge_jump(filt, col) / true_jump
r_gauss = edge_jump(gauss, col) / true_jump
print("[段差保存] 段差保持率  bilateral=%.3f  gauss=%.3f (1.0=完全保存)" % (r_bilat, r_gauss))
assert r_bilat > 0.7, r_bilat                    # bilateral は段差を保存
assert r_gauss < 0.4, r_gauss                    # 素朴ガウスは段差をぼかす(判別性)
assert r_bilat > 2.0 * r_gauss

# (c) 深い穴の fail-closed: max_radius を超える穴中心は捏造せず NaN で残す
d2 = np.full((40, 40), 9.0)
d2[10:30, 10:30] = 0.0                            # 20x20 の大穴(中心は有効画素から ~10px)
out2 = DB.fill_holes(d2, max_radius=3.0)
print("[fail-closed] 深穴中心=%s (NaN=補間せず正直に無効)  境界近傍=%.3f"
      % (out2[20, 20], out2[11, 11]))
assert np.isnan(out2[20, 20]), "深い穴の中心は NaN で残すべき(値を捏造しない)"
assert np.isfinite(out2[11, 11]) and abs(out2[11, 11] - 9.0) < 1e-6, "境界近傍(半径内)は埋まる"

print("\nOK: 穴は平面値で埋まり / ノイズは半減 / 段差は保存 / 深穴は正直にNaN")
