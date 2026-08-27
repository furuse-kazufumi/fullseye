# 事例: 動的シーンの剛体運動セグメンテーション
# ----------------------------------------------------------------------------
# 実問題: 2 時刻に撮った点群のあいだで、シーンの中を「別々に動いた 2 つの物体」を
#   運動の一致だけを手がかりに切り分ける(どちらの点がどの物体かの事前ラベルは無い)。
#   さらに、動きに何の規則も無いバラバラのノイズ点群からは「物体があるフリ」をせず
#   0 個と答える(honest = 存在しない剛体を捏造しない)ことを確かめる。
import numpy as np
import motion_seg3d as ms


def rodrigues(axis, deg):
    """軸と角度から回転行列を作る(実装の Kabsch とは独立の正解生成器)。"""
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    th = np.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * (K @ K)


def rot_angle_deg(Ra, Rb):
    """2 つの回転のあいだの角度(度)。"""
    c = (np.trace(np.asarray(Ra).T @ np.asarray(Rb)) - 1.0) / 2.0
    return float(np.degrees(np.arccos(np.clip(c, -1.0, 1.0))))


def grid(n, spacing, center):
    """中心 center・間隔 spacing の n^3 個の格子点。"""
    c = (np.arange(n, dtype=float) - (n - 1) / 2.0) * spacing
    gx, gy, gz = np.meshgrid(c, c, c, indexing="ij")
    P = np.stack([gx.ravel(), gy.ravel(), gz.ravel()], axis=1)
    return P + np.asarray(center, float)


# --- シーン A: 別々に動く 2 つの剛体 -----------------------------------------
# x 方向に大きく離した 2 つの立方体格子(間の隙間 6 は各物体の動き 0.2 より遥かに大きい
# ので、最近傍対応が物体をまたいで混ざらない = 小運動の前提が成り立つ)。
n = 4
npts = n ** 3  # 1 物体あたりの既知点数 = 64
L0 = grid(n, 1.0, (-3.0, 0.0, 0.0))  # 左の物体
R0 = grid(n, 1.0, (+3.0, 0.0, 0.0))  # 右の物体

# 左の物体は一様に平行移動する
T_left = np.array([0.2, 0.1, -0.05])
L1 = L0 + T_left

# 右の物体は自分の中心まわりに 6 度だけ回る
R_rot = rodrigues([0.2, 1.0, -0.3], 6.0)
cR = np.array([3.0, 0.0, 0.0])
R1 = (R0 - cR) @ R_rot.T + cR
t_right_true = cR - R_rot @ cR  # p1 = R p0 + (c - R c) の並進成分

P0 = np.vstack([L0, R0])
P1 = np.vstack([L1, R1])
# 各点がどちらの物体の正解か(検証専用。アルゴリズムには渡さない)
gt_is_left = np.concatenate([np.ones(npts, bool), np.zeros(npts, bool)])

out = ms.segment_rigid_motions(P0, P1, thresh=0.05, max_bodies=5)
labels = out["labels"]
motions = out["motions"]

print("[シーン A: 2 剛体]")
print("  検出された剛体の数:", len(motions))
print("  出現ラベル:", sorted(set(labels.tolist())))
for lab in sorted(set(labels.tolist())):
    print(f"    label {lab}: {int((labels == lab).sum())} 点")

# --- 検証 A: ちょうど 2 体・各ラベルが 1 物体を純粋に占める・運動が正解に一致 -----
assert len(motions) == 2, f"剛体は 2 個のはず: {len(motions)}"
assert set(np.unique(labels)) == {0, 1}, "外れ値なし(全点が対応)のはず"
for lab in (0, 1):
    member = labels == lab
    assert member.sum() == npts, f"label {lab} の点数が 64 でない: {member.sum()}"
    # そのラベルの点はすべて同じ正解物体(混ざっていない = 純度 100%)
    pure = gt_is_left[member].all() or (~gt_is_left[member]).all()
    assert pure, f"label {lab} に 2 物体が混在"

# ラベルごとの回転が「平行移動物体(R≈I)」か「回転物体」かを判定して正解照合
for lab in (0, 1):
    member = labels == lab
    is_left_body = bool(gt_is_left[member][0])
    R, t = motions[lab]
    assert np.isclose(np.linalg.det(R), 1.0, atol=1e-9)  # 正しい回転行列
    if is_left_body:
        assert rot_angle_deg(R, np.eye(3)) < 1e-3
        assert np.allclose(t, T_left, atol=1e-5)
        print(f"  label {lab} = 平行移動物体: 並進 {np.round(t, 4)} (正解 {T_left})")
    else:
        assert rot_angle_deg(R, R_rot) < 1e-3
        assert np.allclose(t, t_right_true, atol=1e-5)
        ang = rot_angle_deg(R, np.eye(3))
        print(f"  label {lab} = 回転物体: 回転角 {ang:.3f}° (正解 6.000°)")

# --- シーン B: 剛体構造ゼロの無相関ノイズ点群 --------------------------------
# 各点が独立にランダムに揺れるだけ(物体としての一貫した動きは無い)。
# 6 自由度の剛体は数点になら「偶然」当たってしまうが、有意性ゲートがそれを弾く。
rng = np.random.default_rng(7)
Q0 = rng.uniform(size=(40, 3))
Q1 = Q0 + rng.normal(0.0, 0.3, size=(40, 3))  # 各点バラバラの変位 = 剛体相関ゼロ

out_noise = ms.segment_rigid_motions(Q0, Q1, thresh=0.35, max_bodies=5)
labels_n = out_noise["labels"]
motions_n = out_noise["motions"]

print("\n[シーン B: 無相関ノイズ]")
print("  検出された剛体の数:", len(motions_n))
print("  全点が外れ値 (-1) か:", bool(np.all(labels_n == -1)))

# --- 検証 B: 剛体を 1 つも捏造しない・全点 -1 ---------------------------------
assert len(motions_n) == 0, f"ノイズから剛体を捏造した: {len(motions_n)}"
assert np.all(labels_n == -1), "ノイズ点が剛体に割り当てられた"

print("\nALL ASSERTIONS PASSED")