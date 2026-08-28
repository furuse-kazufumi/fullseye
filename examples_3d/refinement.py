# -*- coding: utf-8 -*-
"""事例: 粗いマッチを Newton/LK/LM/回転GN/点-面ICP で仕上げ精度へ締め上げる (pose_refinement).

平たく言うと: テンプレート照合や相関ピーク検出が返す「整数ボクセル/±3度」級の粗い姿勢を、
そのまま使うと 0.5 ボクセルも 3 度もズレている。これを連続座標・連続角へ収束させる「仕上げ
(refinement)」の道具箱をまとめて示す。5 つの精緻化器はいずれも「粗い初期値 → 局所モデルを
反復で最小化 → サブボクセル/サブ度精度」という同じ骨格を持つ:
    - refine_peak_newton     : スコア/相関 volume の整数ピーク → 3D Newton でサブボクセル
    - refine_translation_lk  : 逆合成 Lucas-Kanade で並進(corner 座標)を締める
    - refine_lm              : Levenberg-Marquardt で並進(+等方スケール/輝度ゲイン, center 座標)
    - refine_rotation_z      : z 軸回転角を 1 パラメータ Gauss-Newton で締める
    - icp_point2plane        : 点-面 ICP で剛体 6-DoF 姿勢を締める

これらが「同じ 1 つの真の並進」を別々の規約(corner/center)で復元して一致することを示し
(合成)、回転・剛体姿勢も既知真値へ収束することを確認する。

検証(GT): すべて既知真値から合成データを作る。
    - 帯域制限した滑らかな解析場 F を整数格子でサンプルして scene、既知の分数オフセットで
      サンプルして template を作る → 真の並進 corner=offset_corner / center=offset_corner+c_T を
      Newton(スコア山のピーク)・LK(corner)・LM(center)が一致復元するか。三者が真値へ、
      かつ互いに(規約変換 c_T を挟んで)一致することを assert。
    - refine_lm は既知スケール s_true・輝度ゲイン g_true でリサンプル/減光した template2 から
      s_true / g_true / 並進を同時復元できるか(LK に無い LM 固有能力)。
    - refine_rotation_z は既知 7 度回転(scene は別補間器 scipy order=3 で生成し inverse crime 回避)
      を init=0 から 0.3 度以内へ。
    - icp_point2plane は波打つ表面へ掛けた既知剛体 (R_true,t_true) を単位行列開始で機械精度へ。

beat-the-null: 各仕上げ後の誤差が、仕上げ前の粗い初期値の誤差を桁違いに下回ることを判別的に
示す(Newton: 整数 argmax の 0.58 voxel / LK-LM: 整数初期の ~0.4 voxel / 回転: init 7 度 /
ICP: 単位行列整列の点-面 RMSE)。仕上げが偶然でなく本当に効いていることの裏付け。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np
from scipy.ndimage import rotate as ndrotate

import match3d as M


def _np(x):
    """torch.Tensor / ndarray を numpy に正規化。"""
    return x.detach().cpu().numpy() if hasattr(x, "detach") else np.asarray(x)


def rotation_matrix(axis, deg):
    """軸まわり deg 度の回転行列(ロドリゲスの公式)。"""
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    th = np.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * K @ K


def rotation_error_deg(R_est, R_gt):
    """2 つの回転行列の間の測地距離(度)。"""
    cos = (np.trace(np.asarray(R_est).T @ R_gt) - 1) / 2
    return float(np.degrees(np.arccos(np.clip(cos, -1.0, 1.0))))


def field(z, y, x):
    """帯域制限した滑らかな解析スカラー場(波長 ~18 voxel、全方向に勾配あり)。

    scene(整数格子)と template(分数オフセット格子)を同じ F からサンプルすることで
    「連続な真の並進」を厳密に定義する(trilinear 補間の誤差のみが残差)。
    """
    return (np.sin(0.35 * z + 0.5) * np.cos(0.28 * y - 0.3)
            + 0.7 * np.cos(0.22 * x + 0.9) * np.sin(0.31 * z)
            + 0.5 * np.sin(0.19 * y + 0.4) * np.cos(0.24 * x)
            + 0.3 * np.cos(0.15 * (z + y)) * np.sin(0.17 * (x - z)))


# ═══════════════════════════════════════════════════════════════════════════
# セクション A: 1 つの真の並進を Newton / LK / LM が別規約で一致復元する(合成)
# ═══════════════════════════════════════════════════════════════════════════
D = 40                                          # scene 格子 (D,D,D)
T = 9                                           # template 一辺
c_T = (T - 1) / 2.0                             # center 規約と corner 規約の差 = 4.0

zz, yy, xx = np.meshgrid(np.arange(D), np.arange(D), np.arange(D), indexing="ij")
scene = field(zz, yy, xx).astype(np.float64)    # 整数格子上の F

offset_corner = np.array([14.30, 16.70, 11.40])          # 真の並進(corner 規約 = template 原点)
p_center_true = offset_corner + c_T                       # 真の並進(center 規約 = template 中心)

# template[a,b,c] = F(a+oz, b+oy, c+ox) : 既知の分数オフセットで解析場をサンプル
ta, tb, tc = np.meshgrid(np.arange(T), np.arange(T), np.arange(T), indexing="ij")
template = field(ta + offset_corner[0], tb + offset_corner[1],
                 tc + offset_corner[2]).astype(np.float64)

# --- A-1) refine_peak_newton: スコア/相関 volume の整数ピーク → サブボクセル ---
# 相関ピークは「template 中心が scene のどこに載るか」= p_center_true に山を持つ。
sig = 2.5
score = np.exp(-((zz - p_center_true[0]) ** 2 + (yy - p_center_true[1]) ** 2
                 + (xx - p_center_true[2]) ** 2) / (2 * sig ** 2)).astype(np.float64)
peak_idx = np.unravel_index(int(np.argmax(score)), score.shape)   # 整数 argmax(粗ピーク)
newton = M.refine_peak_newton(score, peak_idx)                    # [peak, z, y, x]
newton_xyz = newton[1:4]
newton_null = np.linalg.norm(np.array(peak_idx, float) - p_center_true)  # 整数 argmax の誤差
newton_err = float(np.linalg.norm(newton_xyz - p_center_true))
print(f"[Newton] 整数argmax {tuple(peak_idx)} (誤差 {newton_null:.3f}) → "
      f"サブボクセル {np.round(newton_xyz, 3)} (真値 {p_center_true.tolist()}, 誤差 {newton_err:.4f})")

# --- A-2) refine_translation_lk: 逆合成 LK で並進(corner 規約) ---
lk_init = np.round(offset_corner).astype(int)                     # 整数初期(粗マッチ)
lk_pos = M.refine_translation_lk(scene, template, lk_init)        # (dz,dy,dx) corner
lk_null = float(np.linalg.norm(lk_init - offset_corner))
lk_err = float(np.linalg.norm(lk_pos - offset_corner))
print(f"[LK]     整数初期 {tuple(lk_init)} (誤差 {lk_null:.3f}) → "
      f"corner {np.round(lk_pos, 4)} (真値 {offset_corner.tolist()}, 誤差 {lk_err:.5f})")

# --- A-3) refine_lm: LM で並進(center 規約, 純並進 scale=False)---
lm_init = np.round(p_center_true).astype(int)
lm = M.refine_lm(scene, template, lm_init, scale=False, gain=False)
lm_pos = np.array(lm["pos"])
lm_null = float(np.linalg.norm(lm_init - p_center_true))
lm_err = float(np.linalg.norm(lm_pos - p_center_true))
print(f"[LM]     整数初期 {tuple(lm_init)} (誤差 {lm_null:.3f}) → "
      f"center {np.round(lm_pos, 4)} (真値 {p_center_true.tolist()}, 誤差 {lm_err:.5f}, "
      f"rms {lm['rms']:.2e})")

# --- A-4) 合成: 三つの仕上げが「同じ真の並進」を規約変換 c_T を挟んで一致 ---
lk_to_center = lk_pos + c_T                                       # corner → center へ規約変換
agree_lk_lm = float(np.linalg.norm(lk_to_center - lm_pos))        # LK(→center) と LM
agree_newton_lm = float(np.linalg.norm(newton_xyz - lm_pos))     # Newton と LM
print(f"[合成]   LK+c_T vs LM = {agree_lk_lm:.5f} / Newton vs LM = {agree_newton_lm:.4f} voxel 一致")

# GT + beat-null(A)
assert newton_err < 0.12, f"Newton がサブボクセルに収束していない: {newton_err:.4f}"
assert newton_err < 0.4 * newton_null, f"Newton が整数 argmax null を下回れていない: {newton_err:.4f} vs {newton_null:.3f}"
assert lk_err < 0.05, f"LK の並進誤差が大きい: {lk_err:.5f}"
assert lk_err < 0.1 * lk_null, f"LK が整数初期 null を下回れていない: {lk_err:.5f} vs {lk_null:.3f}"
assert lm_err < 0.05, f"LM の並進誤差が大きい: {lm_err:.5f}"
assert lm_err < 0.1 * lm_null, f"LM が整数初期 null を下回れていない: {lm_err:.5f} vs {lm_null:.3f}"
assert agree_lk_lm < 0.06, f"LK(→center) と LM が一致しない(規約変換の合成が崩れる): {agree_lk_lm:.5f}"
assert agree_newton_lm < 0.15, f"Newton と LM が一致しない: {agree_newton_lm:.4f}"

# ═══════════════════════════════════════════════════════════════════════════
# セクション B: refine_lm 固有能力 — 既知スケール s_true・輝度ゲイン g_true を復元
# ═══════════════════════════════════════════════════════════════════════════
s_true, g_true = 1.08, 0.85
t_true_b = p_center_true.copy()
# template2[x] = (1/g_true)·F(t_true + s_true·(x - c_T)) : スケール+減光した観測を模す
oz2, oy2, ox2 = ta - c_T, tb - c_T, tc - c_T
template2 = ((1.0 / g_true) * field(t_true_b[0] + s_true * oz2,
                                    t_true_b[1] + s_true * oy2,
                                    t_true_b[2] + s_true * ox2)).astype(np.float64)
lm2 = M.refine_lm(scene, template2, np.round(t_true_b).astype(int),
                  scale=True, gain=True)
s_err = abs(lm2["scale"] - s_true)
g_err = abs(lm2["gain"] - g_true)
t_err_b = float(np.linalg.norm(np.array(lm2["pos"]) - t_true_b))
print(f"[LM+SG]  scale {lm2['scale']:.4f} (真 {s_true}, 誤差 {s_err:.4f}) / "
      f"gain {lm2['gain']:.4f} (真 {g_true}, 誤差 {g_err:.4f}) / 並進誤差 {t_err_b:.4f}")
assert s_err < 0.02, f"等方スケールを復元できていない: {s_err:.4f}"
assert g_err < 0.02, f"輝度ゲインを復元できていない: {g_err:.4f}"
assert t_err_b < 0.1, f"スケール/ゲイン同時最適化で並進が復元できていない: {t_err_b:.4f}"

# ═══════════════════════════════════════════════════════════════════════════
# セクション C: refine_rotation_z — 既知 z 軸回転を init=0 から締める
# ═══════════════════════════════════════════════════════════════════════════
Dr = 40
zc = (Dr - 1) / 2.0
zr, yr, xr = np.meshgrid(np.arange(Dr), np.arange(Dr), np.arange(Dr), indexing="ij")
# y-x 平面に非対称に配した複数ガウス瘤 → z 軸回転が一意に定まる非対称 volume
blobs = [(zc, 26.0, 22.0, 1.0, 3.0), (17.0, 14.0, 24.0, 0.8, 2.5),
         (22.0, 20.0, 13.0, 0.9, 3.5), (zc, 24.0, 16.0, 0.6, 2.0)]
vol_t = np.zeros((Dr, Dr, Dr), np.float64)
for bz, by, bx, amp, w in blobs:
    vol_t += amp * np.exp(-((zr - bz) ** 2 + (yr - by) ** 2 + (xr - bx) ** 2) / (2 * w ** 2))

theta_true = 7.0
# scene は別補間器(scipy order=3)で生成 → refine の grid_sample と別経路 = inverse crime 回避
scene_rot = ndrotate(vol_t, theta_true, axes=(1, 2), reshape=False, order=3,
                     mode="constant", cval=0.0)
rot_deg, rot_iters = M.refine_rotation_z(scene_rot, vol_t, init_angle_deg=0.0)
rot_err = abs(rot_deg - theta_true)
rot_null = abs(0.0 - theta_true)                                  # init=0 の誤差 = 7 度
print(f"[RotZ]   init 0.0度 (誤差 {rot_null:.1f}) → {rot_deg:.4f}度 "
      f"(真 {theta_true}, 誤差 {rot_err:.4f}, {rot_iters} 反復)")
assert rot_err < 0.3, f"z 軸回転角が収束していない: {rot_err:.4f} 度"
assert rot_err < 0.05 * rot_null, f"回転が init null を下回れていない: {rot_err:.4f} vs {rot_null:.1f}"

# ═══════════════════════════════════════════════════════════════════════════
# セクション D: icp_point2plane — 波打つ表面へ掛けた既知剛体姿勢を機械精度で復元
# ═══════════════════════════════════════════════════════════════════════════
gx1d = np.linspace(-2.0, 2.0, 45)
gy1d = np.linspace(-2.0, 2.0, 45)
XX, YY = np.meshgrid(gx1d, gy1d, indexing="ij")
Xf, Yf = XX.ravel(), YY.ravel()
# 二周波の波打つ高さ場 z=f(x,y):法線が x,y 方向に十分傾き 6-DoF を拘束
Zf = 0.35 * np.sin(1.4 * Xf) * np.cos(1.1 * Yf) + 0.15 * np.cos(2.1 * Xf + 0.7 * Yf)
dst = np.stack([Xf, Yf, Zf], axis=1)
fx = 0.35 * 1.4 * np.cos(1.4 * Xf) * np.cos(1.1 * Yf) - 0.15 * 2.1 * np.sin(2.1 * Xf + 0.7 * Yf)
fy = -0.35 * 1.1 * np.sin(1.4 * Xf) * np.sin(1.1 * Yf) - 0.15 * 0.7 * np.sin(2.1 * Xf + 0.7 * Yf)
dst_normals = np.stack([-fx, -fy, np.ones_like(Xf)], axis=1)
dst_normals /= np.linalg.norm(dst_normals, axis=1, keepdims=True)

R_true = rotation_matrix([0.3, 0.5, 1.0], 7.0)                    # 復元すべき回転(7 度)
t_true = np.array([0.03, -0.02, 0.04])                            # 復元すべき並進
# src_i = R_true.T·(dst_i - t_true) → R_true·src_i + t_true = dst_i(ICP が R_true,t_true を復元)
src = (dst - t_true) @ R_true

R_icp, t_icp, aligned, rmse, n_iter = M.icp_point2plane(src, dst, dst_normals)
icp_rot_err = rotation_error_deg(R_icp, R_true)
icp_t_err = float(np.linalg.norm(t_icp - t_true))

# beat-null: 単位行列(=仕上げ前)整列の点-面 RMSE(最近傍で評価)
from scipy.spatial import cKDTree
nn = cKDTree(dst).query(src, k=1)[1]
null_p2pl = float(np.sqrt(np.mean(np.einsum("ij,ij->i", src - dst[nn], dst_normals[nn]) ** 2)))
print(f"[ICP]    単位行列整列 点-面RMSE {null_p2pl:.4f} → {n_iter} 反復で RMSE {rmse:.2e}")
print(f"[ICP]    回転誤差 {icp_rot_err:.4f}度 (真 7度) / 並進誤差 {icp_t_err:.2e} (真 {t_true.tolist()})")
assert icp_rot_err < 0.05, f"ICP の回転が真値へ収束していない: {icp_rot_err:.4f} 度"
assert icp_t_err < 1e-3, f"ICP の並進が真値へ収束していない: {icp_t_err:.2e}"
assert rmse < 1e-4, f"ICP の点-面 RMSE が機械精度まで下がっていない: {rmse:.2e}"
assert rmse < 1e-3 * null_p2pl, f"ICP が単位行列 null を桁違いに下回れていない: {rmse:.2e} vs {null_p2pl:.4f}"

print("PASS: Newton/LK/LM が同一の真並進を規約変換 c_T を挟み一致復元"
      f"(LK+c_T vs LM {agree_lk_lm:.1e}), LM は scale {s_true}/gain {g_true} も復元, "
      f"RotZ が 7度→誤差 {rot_err:.3f}度, 点-面ICP が剛体姿勢を回転誤差 {icp_rot_err:.1e}度・"
      f"RMSE {rmse:.1e} で締める。全器が仕上げ前 null を桁違いに下回る")
