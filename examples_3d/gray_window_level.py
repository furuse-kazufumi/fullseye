"""事例: CT の HU windowing — 骨窓と軟部組織窓で「見えるもの」が変わる (volgray).

実世界の問題:
    CT ボリュームは Hounsfield 単位(HU)で -1000(空気)〜 +700 以上(骨)まで
    3桁のダイナミックレンジを持つが、表示・後段処理は [0,1] の狭い範囲しか扱えない。
    放射線科では **window/level(窓中心 C・窓幅 W)** で見たい組織の HU 帯だけを
    [0,1] に線形写像し、外側はクリップする — 毎日の操作そのもの。

原理(GT で判別的に示す):
    * 軟部組織窓 C=40, W=400 → [-160, +240]:軟部組織(40 HU)は 0.5 に写り
      背景(-1000 HU)と大差がつく。一方 **骨(700 HU)は 1.0 に飽和**して
      内部のテクスチャ(ノイズ)が std≈0 に潰れる。
    * 骨窓 C=700, W=500 → [+450, +950]:骨は 0.5 中心にコントラストが立つが、
      **軟部組織(40 HU)は 0.0 にクリップされ背景と区別不能**になる。
    つまり同じボリュームでも窓の選択で「見える構造」が入れ替わる。これを
    ボクセル集団の平均・標準偏差で機械検証する(beat-the-null: 各窓で
    「立つ側」と「潰れる側」の両方をアサート)。

    仕上げに同じ CT へ vol_equalize(mask=体部 — 空気が全ヒストグラムを飲み込む
    のを防ぐ HALCON reduce_domain 流儀)/ vol_gamma / vol_stretch も適用する。
"""
from __future__ import annotations

import os
import sys

import numpy as np

# --- fullseye モジュールを import 可能にする(リポジトリルートを sys.path へ) ---
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import volgray

HU_AIR, HU_SOFT, HU_BONE = -1000.0, 40.0, 700.0     # 定番の HU 値
NOISE_HU = 15.0                                      # CT らしい軽いノイズ


def synthetic_ct(shape=(60, 80, 80), seed=0):
    """空気 (-1000 HU) の中に軟部組織の楕円体 (40 HU)、その内部に骨球 (700 HU)。
    返り値: (vol, soft_mask, bone_mask, bg_mask) — マスクは GT 計測用。"""
    D, H, W = shape
    zz, yy, xx = np.mgrid[0:D, 0:H, 0:W].astype(np.float64)
    cz, cy, cx = D / 2.0, H / 2.0, W / 2.0
    body = (((zz - cz) / (0.40 * D)) ** 2 + ((yy - cy) / (0.35 * H)) ** 2
            + ((xx - cx) / (0.35 * W)) ** 2) <= 1.0
    bone = ((zz - cz) ** 2 + (yy - cy) ** 2 + (xx - cx) ** 2) <= (0.12 * min(shape)) ** 2
    vol = np.full(shape, HU_AIR)
    vol[body] = HU_SOFT
    vol[bone] = HU_BONE
    vol += NOISE_HU * np.random.default_rng(seed).standard_normal(shape)
    soft = body & ~bone
    return vol, soft, bone, ~body


vol, soft, bone, bg = synthetic_ct()
print(f"CT 風ボリューム       : {vol.shape}, HU range [{vol.min():.0f}, {vol.max():.0f}]")
print(f"組織ボクセル数        : 軟部 {soft.sum()} / 骨 {bone.sum()} / 背景 {bg.sum()}")

# --- 1) 軟部組織窓 C=40, W=400 → 軟部が立ち、骨は飽和して潰れる ---------------
wl_soft = volgray.vol_window_level(vol, center=40.0, width=400.0)
s_mean, b_mean, bone_mean = wl_soft[soft].mean(), wl_soft[bg].mean(), wl_soft[bone].mean()
bone_std = wl_soft[bone].std()
print(f"軟部窓  : 軟部 {s_mean:.3f} / 背景 {b_mean:.4f} / 骨 {bone_mean:.4f} (骨 std {bone_std:.5f})")
assert s_mean - b_mean > 0.4, "軟部窓で軟部組織のコントラストが背景比で立っていない"
assert bone_mean > 0.99, "軟部窓で骨が飽和していない"
assert bone_std < 0.005, "軟部窓で骨内部テクスチャが潰れていない(飽和の証拠が無い)"

# --- 2) 骨窓 C=700, W=500 → 骨が立ち、軟部は背景と区別不能に -------------------
wl_bone = volgray.vol_window_level(vol, center=700.0, width=500.0)
k_mean, k_std = wl_bone[bone].mean(), wl_bone[bone].std()
s2_mean, b2_mean = wl_bone[soft].mean(), wl_bone[bg].mean()
print(f"骨窓    : 骨 {k_mean:.3f} (std {k_std:.4f}) / 軟部 {s2_mean:.5f} / 背景 {b2_mean:.5f}")
assert abs(k_mean - 0.5) < 0.05, "骨窓で骨が窓中心付近に写っていない"
assert k_std > 0.01, "骨窓で骨内部のコントラスト(テクスチャ)が出ていない"
assert abs(s2_mean - b2_mean) < 0.01, "骨窓で軟部組織が背景と区別されてしまっている(クリップされていない)"

# --- 3) equalize: 空気が支配する全体ヒストグラムを mask(体部)で回避 -----------
body_mask = (~bg).astype(np.float64)
eq = volgray.vol_equalize(vol, mask=body_mask)
assert 0.0 <= eq.min() and eq.max() <= 1.0
assert eq[bone].mean() > eq[soft].mean(), "equalize が単調性(骨 > 軟部)を壊した"
print(f"equalize: mask=体部で LUT 構築 → 軟部 {eq[soft].mean():.3f} / 骨 {eq[bone].mean():.3f}")

# --- 4) gamma: 軟部窓画像の中間調(軟部 0.5 付近)を gamma=2 で暗く -------------
gm = volgray.vol_gamma(wl_soft, 2.0)
assert gm[soft].mean() < wl_soft[soft].mean() - 0.1, "gamma=2 が中間調を暗くしていない"
assert abs(gm.max() - wl_soft.max()) < 1e-9, "gamma が range 端を動かした"
print(f"gamma=2 : 軟部の中間調 {wl_soft[soft].mean():.3f} → {gm[soft].mean():.3f}(端点は固定)")

# --- 5) stretch: 生 HU をパーセンタイルで [0,1] へ(外れ値に頑健) --------------
st = volgray.vol_stretch(vol, p_low=1.0, p_high=99.0)
assert st.min() == 0.0 and st.max() == 1.0, "stretch の出力が [0,1] に張り付いていない"
print(f"stretch : 生 HU [{vol.min():.0f}, {vol.max():.0f}] → [0,1](1/99 パーセンタイル基準)")

print(f"PASS: 軟部窓は軟部 Δ{s_mean - b_mean:.2f} が立ち骨は飽和 (std {bone_std:.4f})、"
      f"骨窓は骨 {k_mean:.2f}±{k_std:.3f} が立ち軟部は背景と同化 (Δ{abs(s2_mean - b2_mean):.4f})"
      f" = 窓の選択が「見える構造」を入れ替える")
