"""事例: ボリュームの幾何変換 3 op(vol_resize / vol_rotate / vol_affine)を真値で検証.

2D には geometry 28 op があるのに voxel 界は形式変換のみだった確定ギャップを
``volxform`` が埋める。位置合わせ後のリサンプリング(CT を CAD 座標へ回す・等方
voxel へ揃える・姿勢推定の逆変換で切り出す)の核。規約は全て docstring に固定:

  * ``vol_resize`` — セル方式 (``grid_mode=True``)。整数倍 f の拡大は voxel i を
    ブロック [f*i, f*(i+1)) に写す(order=0 で厳密)。spacing を渡すと新 spacing を
    返し、**物理サイズ(mm)は不変**。
  * ``vol_rotate`` — 正の角度は axes[0] から axes[1] へ回る(np.rot90 と同符号)。
  * ``vol_affine`` — scipy 流 **pull**(出力座標→入力座標): out[o] = vol[M@o + off]。
    物体を +t 動かすには offset=-t(逆変換を渡す)。

検証(GT): 非対称な L 字ブロック(真値既知)で
  (1) rotate 90°x4 = 恒等(最大差で assert)
  (2) resize 2 倍で重心が「2 倍位置」(セル規約では index 重心 = 2c+0.5、
      物理重心 (c+0.5)*spacing は不変 — 両方を機械検証)
  (3) affine 平行移動(4x4 同次)で bbox シフトが厳密一致
  (4) spacing 再計算で物理体積 mm^3 が保存(voxel 数 x new_spacing 積で機械検証)
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from volxform import vol_affine, vol_resize, vol_rotate  # noqa: E402

# --- 非対称な合成部品: L 字ブロック(真値既知)------------------------------
# (24, 32, 32) の中に、z 方向に厚みを持つ L 字(縦棒 + 足)。回転平面 (y, x) は
# 正方形なので reshape=False の 90°回転が無損失。
SHAPE = (24, 32, 32)
vol = np.zeros(SHAPE)
vol[6:18, 8:24, 10:14] = 1.0        # 縦棒 (y 方向に長い)
vol[6:18, 20:24, 10:22] = 1.0       # 足   (x 方向に伸びる) → L 字で非対称
n_in = int(vol.sum())
print(f"L 字ブロック          : shape={SHAPE}, 前景 {n_in} voxel(非対称)")

# --- 1) rotate: 90°x 4 = 恒等 -----------------------------------------------
r = vol
for _ in range(4):
    r = vol_rotate(r, 90, axes=(1, 2), order=0, reshape=False)
maxdiff = float(np.abs(r - vol).max())
print(f"rotate 90°x4          : 最大差 = {maxdiff}(恒等)")
assert maxdiff == 0.0, f"90°x4 が恒等でない: 最大差 {maxdiff}"

# 90°一回は np.rot90 と厳密一致(回転方向規約の再確認)
r1 = vol_rotate(vol, 90, axes=(1, 2), order=0, reshape=False)
assert np.array_equal(r1, np.rot90(vol, 1, axes=(1, 2))), "回転方向規約が破れた"

# --- 2) resize 2 倍: 重心が 2 倍位置(セル規約 2c+0.5)-----------------------
SPACING = (0.8, 0.5, 0.5)           # mm/voxel (sz, sy, sx)
big, new_spacing = vol_resize(vol, factor=2, order=0, spacing=SPACING)
c_in = np.argwhere(vol > 0.5).mean(axis=0)
c_out = np.argwhere(big > 0.5).mean(axis=0)
expect = 2.0 * c_in + 0.5           # voxel i -> ブロック [2i, 2i+2) の中心 = 2i+0.5
print(f"resize 2x 重心(index) : in={c_in} -> out={c_out}(期待 2c+0.5={expect})")
assert np.allclose(c_out, expect, atol=1e-9), f"重心が 2 倍位置でない: {c_out} != {expect}"

# 物理重心 (index+0.5)*spacing は resize 前後で不変(セル規約の帰結)
phys_in = (c_in + 0.5) * np.asarray(SPACING)
phys_out = (c_out + 0.5) * np.asarray(new_spacing)
print(f"resize 物理重心 [mm]  : in={phys_in} == out={phys_out}")
assert np.allclose(phys_in, phys_out, atol=1e-9), "物理重心が動いた"

# --- 3) affine 平行移動(4x4 同次): bbox が厳密に +t シフト -----------------
t = np.array([2, 3, 4])             # 物体を +t 動かしたい(pull なので offset=-t)
M = np.eye(4)
M[:3, 3] = -t
moved = vol_affine(vol, M, order=0)
bb_in = np.array([np.argwhere(vol > 0.5).min(axis=0), np.argwhere(vol > 0.5).max(axis=0)])
bb_mv = np.array([np.argwhere(moved > 0.5).min(axis=0), np.argwhere(moved > 0.5).max(axis=0)])
print(f"affine 平行移動 +{tuple(int(x) for x in t)} : bbox {bb_in.tolist()} -> {bb_mv.tolist()}")
assert np.array_equal(bb_mv, bb_in + t), f"bbox シフト不一致: {bb_mv} != {bb_in + t}"
assert int(moved.sum()) == n_in, "平行移動で voxel 数が変わった(フレーム外に出た?)"

# --- 4) spacing 再計算: 物理体積 mm^3 が保存 ---------------------------------
n_out = int(big.sum())
vol_mm3_in = n_in * float(np.prod(SPACING))
vol_mm3_out = n_out * float(np.prod(new_spacing))
print(f"spacing 再計算        : {SPACING} -> {tuple(round(s, 6) for s in new_spacing)}")
print(f"物理体積 [mm^3]       : in={vol_mm3_in:.6f} (={n_in} voxel) == "
      f"out={vol_mm3_out:.6f} (={n_out} voxel)")
assert n_out == 8 * n_in, f"2 倍拡大で voxel 数が 8 倍でない: {n_out} != {8 * n_in}"
assert abs(vol_mm3_in - vol_mm3_out) < 1e-9 * vol_mm3_in, "物理体積が保存されていない"

print(f"PASS: rotate 90°x4 恒等(最大差 {maxdiff})・resize 2x 重心 2c+0.5 一致・"
      f"affine +{tuple(int(x) for x in t)} bbox 厳密シフト・物理体積 {vol_mm3_in:.4f} mm^3 保存 "
      f"= volxform 3 op の規約を真値で機械検証")
