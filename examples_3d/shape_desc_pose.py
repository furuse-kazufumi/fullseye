# -*- coding: utf-8 -*-
"""事例: 大域形状記述子で「同じ部品」を姿勢に依らず同定し、姿勢照合で実際の姿勢を復元する (shape_descriptors).

平たく言うと: 3D スキャンした部品は毎回バラバラの位置・向き・大きさで置かれる。まず「形そのもの」を
姿勢不変な**大域記述子**で数値化する — ランダム 2 点対の距離分布 D2、ランダム 3 点の角度分布 A3、
PCA 主軸方向の広がり比 extent、そして主慣性モーメント。これらは回転・平行移動・(D2/A3/extent は)
スケールにも不変なので、同じ部品は向きが違っても同じ記述子になり、別の部品とは判別できる(=「何の形か」)。
次に、その部品が実際にどれだけ回って・ずれて・拡大されたかを**姿勢照合**で復元する — PCA 主軸整列で
剛体変換 (R,t)、位相相関(FFT)で整数平行移動、log-polar × 位相相関(Fourier-Mellin)で z 軸回転+スケール
(=「どんな姿勢か」)。記述子と照合はこう分担する。

検証(GT):
  1. extent_signature と principal_moments は**同じ共分散(2 次モーメント)の別表現**。
     principal_moments から共分散固有値を復元して extent を組み直すと、extent_signature の出力と
     機械精度で一致する(合成関係の裏取り)。principal_moments は回転で厳密不変・スケールで s² 倍という
     解析則を満たす。
  2. d2_distribution / a3_distribution は相似変換(回転+平行移動+スケール、同順の点列)で
     **bit 完全に不変**。別形状とは記述子距離が桁違いに開く(判別)。
  3. match_pca は既知の (R,t) を機械精度で復元。match_phase_3d は既知の整数平行移動を厳密復元
     (元ボリュームを bit 一致で再構成)。match_logpolar_z は既知の z 軸回転(+等方スケール)を
     数度以内・スケール ~数% で復元(coarse 推定器)。

beat-the-null:
  - 記述子: 同一部品(姿勢違い)の記述子距離 ≈ 0 に対し、別形状(等方ブロック)は 6 桁以上大きい。
  - match_pca: 復元変換の整列残差 ≈ 0(≈1e-14)に対し、無変換(恒等)の残差は物体サイズ級(数単位)。
  - match_phase_3d: 復元シフトで元ボリュームを bit 一致再構成できる一方、シフト済みボリューム自体は
    元と不一致。
  - match_logpolar_z: 真に 20° 回した対では ~20° を返すのに、無回転(自己照合)では ~0° を返す
    (回転量に追従している証拠)。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np

import descriptors3d as D   # d2_distribution / a3_distribution / extent_signature / describe / shape_distance
import moments3d as MO      # principal_moments(慣性テンソル固有値、回転不変)
import match3d as X         # match_pca / match_phase_3d / match_logpolar_z / points_to_voxel


# --------------------------------------------------------------------------- #
# 部品(scalene な本体 + 面内非対称なコーナーブロック)。非対称性は Fourier-Mellin の
# 回転検出を一意化するために効く(完全対称な充実直方体は |FFT| の 90°/180° 別名で外れやすい)。
# --------------------------------------------------------------------------- #
def make_part(seed: int = 0) -> np.ndarray:
    r = np.random.default_rng(seed)
    body = r.uniform(-1, 1, (6000, 3)) * np.array([1.2, 2.6, 1.1])          # 細長い本体
    block = r.uniform(-1, 1, (1600, 3)) * np.array([1.2, 0.6, 0.5]) + np.array([0.0, 1.9, 0.7])
    return np.vstack([body, block])


def rand_rotation(seed: int) -> np.ndarray:
    q, _ = np.linalg.qr(np.random.default_rng(seed).standard_normal((3, 3)))
    if np.linalg.det(q) < 0:
        q[:, 0] = -q[:, 0]
    return q


def rot_axis0(P: np.ndarray, deg: float) -> np.ndarray:
    """voxel 軸 0(match_logpolar_z の投影/回転軸)まわりの回転 = (軸1,軸2) 面内回転。"""
    th = np.radians(deg)
    c, s = np.cos(th), np.sin(th)
    R = np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])
    return (R @ P.T).T


P = make_part()
print(f"部品点数 N = {len(P)}")

# =========================================================================== #
# 1) principal_moments ↔ extent_signature: 同じ共分散の 2 表現が一致する(合成)
# =========================================================================== #
pm = MO.principal_moments(P)          # 慣性テンソル固有値(降順)
ext = D.extent_signature(P)           # 共分散固有値の平方根の比(降順・総和1)

# 慣性テンソル I = tr(C)·E − C なので、固有値も λ_I(降順) = tr(C) − λ_C(昇順)。
# よって λ_C(昇順) = sum(pm)/2 − pm、これから extent を組み直せる。
var_from_pm = pm.sum() / 2.0 - pm                     # 共分散固有値(昇順)
std_from_pm = np.sort(np.sqrt(np.clip(var_from_pm, 0.0, None)))[::-1]
ext_from_pm = std_from_pm / std_from_pm.sum()
identity_err = float(np.abs(ext_from_pm - ext).max())
print(f"principal_moments = {pm}")
print(f"extent_signature  = {ext}")
print(f"pm から復元した extent = {ext_from_pm}  (extent_signature との最大差 = {identity_err:.2e})")

assert pm.shape == (3,) and ext.shape == (3,)
assert np.all(np.diff(pm) <= 0) and np.all(pm > 0), "principal_moments は降順・正でない"
assert np.all(np.diff(ext) <= 0) and abs(ext.sum() - 1.0) < 1e-12, "extent は降順・総和1でない"
assert identity_err < 1e-9, f"pm と extent の合成関係が一致しない: {identity_err:.2e}"

# principal_moments の解析則: 回転で厳密不変、スケールで s² 倍。
pm_rot = MO.principal_moments((rand_rotation(11) @ P.T).T)
rot_inv_err = float(np.abs(pm_rot - pm).max())
s_scale = 3.7
pm_scaled = MO.principal_moments(P * s_scale)
scale_ratio = pm_scaled / pm
print(f"principal_moments 回転不変の最大差 = {rot_inv_err:.2e}")
print(f"principal_moments スケール比 = {scale_ratio}  (解析値 s² = {s_scale ** 2:.3f})")
assert rot_inv_err < 1e-9, f"principal_moments が回転で変化した: {rot_inv_err:.2e}"
assert np.allclose(scale_ratio, s_scale ** 2, rtol=1e-9), "principal_moments のスケール則 s² が破れた"

# =========================================================================== #
# 2) D2 / A3 の相似変換不変性 + 判別性(別形状との分離)
# =========================================================================== #
# 同じ点列に既知の相似変換(回転 Rr・スケール s・平行移動 t)を掛けた「別姿勢の同一部品」。
Rr = rand_rotation(11)
tt = np.array([4.0, 1.0, -2.0])
P_pose = (Rr @ P.T).T * s_scale + tt

BINS, SAMP, SEED = 64, 80_000, 3
d2_a = D.d2_distribution(P, bins=BINS, samples=SAMP, seed=SEED)
d2_b = D.d2_distribution(P_pose, bins=BINS, samples=SAMP, seed=SEED)
a3_a = D.a3_distribution(P, bins=BINS, samples=SAMP, seed=SEED)
a3_b = D.a3_distribution(P_pose, bins=BINS, samples=SAMP, seed=SEED)
# 距離は相似で(平均正規化により)不変、角度も不変。同順・同 seed なので bit 完全一致。
assert d2_a.shape == (BINS,) and abs(d2_a.sum() - 1.0) < 1e-9
assert np.array_equal(d2_a, d2_b), "D2 が相似変換で bit 不変でない"
assert np.array_equal(a3_a, a3_b), "A3 が相似変換で bit 不変でない"

# 別形状(等方ブロック)。D2/A3/extent を連結した describe 記述子で距離を測る。
P_other = np.random.default_rng(9).uniform(-1, 1, (7600, 3)) * np.array([1.5, 1.5, 1.5])
desc_P = D.describe(P, bins=BINS, seed=SEED)
desc_pose = D.describe(P_pose, bins=BINS, seed=SEED)
desc_other = D.describe(P_other, bins=BINS, seed=SEED)
dist_same = D.shape_distance(desc_P, desc_pose)     # 同一部品(姿勢違い)
dist_diff = D.shape_distance(desc_P, desc_other)    # 別形状
print(f"describe 距離: 同一部品(姿勢違い) = {dist_same:.2e} / 別形状(等方ブロック) = {dist_diff:.4f}")
assert dist_same < 1e-9, f"同一部品の記述子距離が 0 でない: {dist_same:.2e}"
assert dist_diff > 0.1, f"別形状との記述子距離が小さすぎる(判別できない): {dist_diff:.4f}"
assert dist_diff > 1e6 * max(dist_same, 1e-15), "同一/別形状の分離が不十分(beat-the-null 不成立)"

# =========================================================================== #
# 3) match_pca: 既知の剛体変換 (R,t) を機械精度で復元
# =========================================================================== #
# 記述子は「同一部品」と言い切った(dist_same≈0)。では実際の姿勢は? を PCA 主軸整列で復元。
R_true = rand_rotation(3)
t_true = np.array([2.0, 1.0, -3.0])
scene = (R_true @ P.T).T + t_true                 # scene = R_true @ model + t_true(同順)
R_est, t_est = X.match_pca(scene, P)
aligned = (R_est @ P.T).T + t_est
align_err = float(np.abs(aligned - scene).max())   # 復元変換で model→scene を整列した残差
null_err = float(np.abs(P - scene).max())          # null: 無変換(恒等)の残差
print(f"match_pca: 整列残差 = {align_err:.2e} / R 誤差 = {np.abs(R_est - R_true).max():.2e} / "
      f"t 誤差 = {np.abs(t_est - t_true).max():.2e}  (null 恒等残差 = {null_err:.3f})")
assert np.allclose(R_est, R_true, atol=1e-9), "match_pca が回転を復元できていない"
assert np.allclose(t_est, t_true, atol=1e-9), "match_pca が並進を復元できていない"
assert align_err < 1e-9, f"match_pca の整列残差が大きい: {align_err:.2e}"
assert null_err > 1.0 and null_err > 1e6 * max(align_err, 1e-15), "beat-the-null 不成立(恒等が同等)"

# =========================================================================== #
# 4) match_phase_3d: 既知の整数平行移動を厳密復元(FFT 位相相関)
# =========================================================================== #
bounds = (P.min(0) - 0.5, P.max(0) + 0.5)
vol = X.points_to_voxel(P, 40, bounds=bounds, smooth=1.0)      # 密度ボリューム
s_true = (7, -5, 3)                                            # 既知の整数シフト
vol_shifted = np.roll(vol, shift=s_true, axis=(0, 1, 2))        # b = shift(a)
shift_est = X.match_phase_3d(vol, vol_shifted)                 # b を a に戻すシフト(= -s_true)
recon = np.roll(vol_shifted, shift=shift_est, axis=(0, 1, 2))   # 復元シフトで a を再構成
print(f"match_phase_3d: 復元シフト = {shift_est}  (解析値 -s_true = {tuple(int(-x) for x in s_true)})")
assert tuple(shift_est) == tuple(int(-x) for x in s_true), "位相相関が整数シフトを外した"
assert np.array_equal(recon, vol), "復元シフトで元ボリュームを bit 再構成できていない"
assert not np.array_equal(vol_shifted, vol), "シフト前後が同一(テストが退化)"

# =========================================================================== #
# 5) match_logpolar_z: 既知の z 軸回転(+等方スケール)を復元(Fourier-Mellin, coarse)
# =========================================================================== #
ANG_TRUE = 20.0
# (a) 回転のみ
P_rot = rot_axis0(P, ANG_TRUE)
allp = np.vstack([P, P_rot])
bnds = (allp.min(0) - 0.6, allp.max(0) + 0.6)
v_ref = X.points_to_voxel(P, 64, bounds=bnds, smooth=1.0)
v_rot = X.points_to_voxel(P_rot, 64, bounds=bnds, smooth=1.0)
ang_est, sc_est = X.match_logpolar_z(v_ref, v_rot)
# beat-null: 無回転(自己照合)は ~0°
ang_self, sc_self = X.match_logpolar_z(v_ref, v_ref)
print(f"match_logpolar_z 回転のみ: 復元角 = {ang_est:.2f}° (真 {ANG_TRUE}°) / スケール = {sc_est:.3f}"
      f"  (自己照合 = {ang_self:.2f}°)")
assert abs(ang_est - ANG_TRUE) < 5.0, f"z 軸回転の復元角が真値から離れすぎ: {ang_est:.2f}"
assert 0.85 < sc_est < 1.15, f"回転のみでスケールが 1 から外れすぎ: {sc_est:.3f}"
assert abs(ang_self) < 1.5, f"自己照合(無回転)が 0° を返さない: {ang_self:.2f}"
assert abs(ang_est - ANG_TRUE) < abs(ang_self - ANG_TRUE), "真の回転に追従できていない(beat-null 不成立)"

# (b) 回転 + 面内等方スケール
SC_TRUE = 1.25
P_rs = rot_axis0(P, ANG_TRUE) * np.array([1.0, SC_TRUE, SC_TRUE])
allp2 = np.vstack([P, P_rs])
bnds2 = (allp2.min(0) - 0.6, allp2.max(0) + 0.6)
v_ref2 = X.points_to_voxel(P, 64, bounds=bnds2, smooth=1.0)
v_rs = X.points_to_voxel(P_rs, 64, bounds=bnds2, smooth=1.0)
ang_rs, sc_rs = X.match_logpolar_z(v_ref2, v_rs)
print(f"match_logpolar_z 回転+スケール: 復元角 = {ang_rs:.2f}° (真 {ANG_TRUE}°) / "
      f"スケール = {sc_rs:.3f} (真 {SC_TRUE})")
assert abs(ang_rs - ANG_TRUE) < 5.0, f"回転+スケール時の角度復元が甘い: {ang_rs:.2f}"
assert abs(sc_rs - SC_TRUE) < 0.15, f"スケール復元が真値から離れすぎ: {sc_rs:.3f} (真 {SC_TRUE})"

print(
    "PASS: extent_signature≡principal_moments(共分散の別表現、合成差 {:.1e})、"
    "principal_moments は回転不変・スケール s² 則。D2/A3 は相似変換で bit 不変・別形状距離 {:.3f}≫0。"
    "match_pca は (R,t) を残差 {:.1e} で復元(null 恒等残差 {:.2f})、match_phase_3d は整数シフトを"
    "bit 一致で復元、match_logpolar_z は z 軸回転 {:.0f}°→{:.1f}°・スケール{:.2f}→{:.2f} を復元"
    .format(identity_err, dist_diff, align_err, null_err, ANG_TRUE, ang_rs, SC_TRUE, sc_rs)
)
