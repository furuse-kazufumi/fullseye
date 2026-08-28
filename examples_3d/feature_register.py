# -*- coding: utf-8 -*-
"""事例: 疎特徴で初期推定なしに 2 点群を位置合わせする (registration).

平たく言うと: 同じ物体を別角度でスキャンした 2 つの点群は、初期姿勢が分からないまま
大きく回っている。密な相関(NCC/位相相関)や PCA 主軸整列はこの「大回転+部分情報」に弱い。
そこで **疎特徴レジストレーション** — (1) 形の角ばった特徴点(keypoint)だけを拾い、
(2) その周りの形を回転不変な記述子(descriptor)にまとめ、(3) 記述子が一致する点どうしを
結んで RANSAC で剛体姿勢を解く — を使うと、初期推定ゼロでも 57 度回った相手を合わせられる。
この道具箱の 6 op を 1 本で通す:

  keypoint 検出 : harris3d_keypoints(密度 voxel の 3D コーナー) / iss_keypoints(点群)
  記述子       : shot_descriptor(局所参照枠 + 法線角ヒストグラム 352 次元、回転不変)
  全体 pipeline : register_spin / register_fpfh / register_shot(検出→記述→マッチ→RANSAC)

register_shot は内部で iss_keypoints → shot_descriptor → RANSAC をこの順に呼ぶので、
単体で叩く iss/shot は register_shot の"中身"そのもの(合成関係を可視化するための構成)。

検証(GT):
  - harris3d_keypoints: 立方体の密度場は 8 頂点が唯一の 3D コーナー(3 面が交わる)。解析的な
    8 頂点座標を真値とし、検出 keypoint が 8 頂点と 1 対 1 に(voxel 精度で)対応するか。
  - iss_keypoints: ISS は回転不変。同一点群を既知 (R,t) で回した雲に当てると、選ばれる点の
    index 配列が**完全一致**するはず(解析的な不変性が真値)。
  - shot_descriptor: SHOT も回転不変。対応点どうしの記述子はほぼ一致(距離~0)、かつ記述子
    最近傍マッチが正しい対応を高率で復元する(識別的)。
  - register_{spin,fpfh,shot}: 既知の剛体変換 (R_gt=57度, t_gt) を真値とし、復元 (R,t) の
    回転角誤差・並進誤差が小さいこと。

beat-the-null: 位置合わせの null は「何もしない=恒等変換」。これは 57 度・並進 2.29 ずれたまま
なので、各 register op の復元誤差がこの null を桁違いに下回ることを assert する。keypoint 側も
「無作為 voxel は頂点から遠い」「無作為な記述子対応は不正解」を null として判別的に上回る。
"""
import sys
from pathlib import Path

# リポジトリ直下を sys.path 先頭へ(examples_3d の同名ファイルがトップレベル module を
# 隠すのを防ぐ。fullseye の op module を import する前に必ず行う)。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from scipy.spatial import cKDTree          # 記述子最近傍・幾何計測(measurement のみ)

import feat_harris                          # harris3d_keypoints(密度 voxel の 3D コーナー)
import feat_shot                            # iss_keypoints / shot_descriptor / register_shot
import feat_spin                            # register_spin
import feat_fpfh                            # register_fpfh


# ─────────────────────────────────────────────────────────────────────────────
# 小道具
# ─────────────────────────────────────────────────────────────────────────────
def rotation_matrix(axis, deg):
    """軸まわり deg 度の回転行列(ロドリゲスの公式)。"""
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    th = np.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * K @ K


def rot_angle_deg(Ra, Rb):
    """2 つの回転行列の差の角度(度)。geodesic distance on SO(3)。"""
    c = (np.trace(Ra.T @ Rb) - 1.0) / 2.0
    return float(np.degrees(np.arccos(np.clip(c, -1.0, 1.0))))


def lumpy_object(n=2500, seed=0):
    """非対称な「でこぼこの塊」の表面点(原点まわりの星形=法線が外向きに一意)。

    球面上に一様(Fibonacci 螺旋)な方向 d を取り、半径を R0 + Σ 異方ガウス隆起/窪みで
    変調する。隆起は振幅・幅・向きをすべて違えて置くので回転対称が無い ⇒ 局所曲率が
    場所ごとに異なり記述子が識別的になり、かつ位置合わせの解が一意に定まる(立方体等の
    対称形は幾何的に等価な誤姿勢が複数あり RANSAC が誤解に固着しうるので使わない)。
    """
    i = np.arange(n) + 0.5
    phi = np.arccos(1.0 - 2.0 * i / n)                  # 極角
    gold = np.pi * (1.0 + 5.0 ** 0.5)                   # 黄金角
    tha = gold * i
    d = np.stack([np.sin(phi) * np.cos(tha),
                  np.sin(phi) * np.sin(tha),
                  np.cos(phi)], axis=1)                 # (n,3) 単位方向
    bumps = [([1.0, 0.0, 0.0],  0.35, 0.50),
             ([0.0, 1.0, 0.0], -0.22, 0.40),
             ([0.0, 0.0, 1.0],  0.28, 0.60),
             ([-1.0, 0.5, 0.3], 0.20, 0.35),
             ([0.4, -1.0, 0.5], 0.26, 0.45),
             ([0.2, 0.3, -1.0], -0.16, 0.50)]
    r = np.full(n, 1.0)                                 # R0 = 1
    for c, amp, w in bumps:
        c = np.asarray(c, float); c = c / np.linalg.norm(c)
        theta = np.arccos(np.clip(d @ c, -1.0, 1.0))
        r = r + amp * np.exp(-theta ** 2 / (2.0 * w ** 2))
    return d * r[:, None]


# ═════════════════════════════════════════════════════════════════════════════
# PART 1 — harris3d_keypoints: 立方体密度場の 3D コーナー = 8 頂点(解析 GT)
# ═════════════════════════════════════════════════════════════════════════════
# 立方体を密度 voxel として置く。内部は一様(勾配 0)、面は 1 方向・稜は 2 方向・頂点は
# 3 方向に勾配が立つ ⇒ 構造テンソルの最小固有値(Shi-Tomasi コーナー性)は 8 頂点でだけ
# 大きい。よって 8 頂点が「唯一の 3D コーナー」= 解析的な真値になる。
GRID = 44
LO, HI = 12, 32                                          # 立方体の占有区間 [LO, HI)
vol = np.zeros((GRID, GRID, GRID), np.float64)
vol[LO:HI, LO:HI, LO:HI] = 1.0

# 解析的な 8 頂点(占有ブロックの角 voxel)。座標順は sobel3d と同じ (z,y,x)。
corners = np.array([[z, y, x] for z in (LO, HI - 1)
                    for y in (LO, HI - 1) for x in (LO, HI - 1)], float)

kp_vox, resp = feat_harris.harris3d_keypoints(
    vol, response="mineig", sigma_i=1.5, border=3, topn=32)

# 応答降順の上位 8 個を取り、各々を最近傍の解析頂点へ割り当てる。
ctree = cKDTree(corners)
top8 = kp_vox[:8]
d_corner, corner_id = ctree.query(top8)
n_distinct = len(set(corner_id.tolist()))               # 8 頂点と 1 対 1 か

# beat-null: 有効領域から無作為に取った voxel は頂点から遠い(検出が頂点を狙えている証拠)。
rng_h = np.random.default_rng(0)
rand_vox = rng_h.uniform(3, GRID - 3, size=(4000, 3))
null_corner_dist = float(cKDTree(corners).query(rand_vox)[0].mean())
kp_corner_dist = float(d_corner.mean())

print("[harris3d] 検出 keypoint 数            :", len(kp_vox))
print(f"[harris3d] 上位8の頂点までの距離(平均) : {kp_corner_dist:.3f} voxel")
print(f"[harris3d] 対応した相異なる頂点数        : {n_distinct} / 8")
print(f"[harris3d] null(無作為voxel)の頂点距離 : {null_corner_dist:.3f} voxel")

assert len(kp_vox) >= 8, f"3D コーナーが 8 個検出できていない: {len(kp_vox)}"
assert n_distinct == 8, f"上位8が 8 頂点と 1 対 1 対応しない(重複/取りこぼし): {n_distinct}"
assert kp_corner_dist < 2.5, f"検出 keypoint が頂点から離れすぎ: {kp_corner_dist:.3f}"
assert kp_corner_dist < 0.4 * null_corner_dist, \
    f"頂点への集中が null を判別的に上回れていない: {kp_corner_dist:.3f} vs {null_corner_dist:.3f}"


# ═════════════════════════════════════════════════════════════════════════════
# 位置合わせ用シーン: でこぼこの塊(src)と、既知 (R_gt, t_gt) で回した相手(dst)
# ═════════════════════════════════════════════════════════════════════════════
src = lumpy_object(n=2500, seed=0)                       # 移動側(物体座標)
R_gt = rotation_matrix([0.3, 1.0, 0.2], 57.0)           # 未知姿勢の真値 = 57 度回転
t_gt = np.array([2.0, -1.0, 0.5])                       # 未知並進の真値
dst = src @ R_gt.T + t_gt                               # 固定側 = R_gt·src + t_gt(同一サンプル)

res = float(np.median(cKDTree(src).query(src, k=2)[0][:, -1]))   # 点間隔(解像度)
radius = 6.0 * res                                       # keypoint/記述子の支持半径

# 恒等変換 null(=何もしない位置合わせ)の誤差。全 register op がこれを下回るべき目標。
null_R = rot_angle_deg(np.eye(3), R_gt)                  # 57.0 度
null_t = float(np.linalg.norm(t_gt))                    # 2.291


# ═════════════════════════════════════════════════════════════════════════════
# PART 2 — iss_keypoints: 回転不変 ⇒ 回した雲でも同じ index が選ばれる(解析 GT)
# ═════════════════════════════════════════════════════════════════════════════
# ISS の saliency(局所共分散の最小固有値)も NMS(点間距離)も剛体変換で不変なので、
# 同一点群を回した dst に当てると、選ばれる点の index 配列が完全一致するはず。
kp_s = feat_shot.iss_keypoints(src, radius, max_kp=200)
kp_d = feat_shot.iss_keypoints(dst, radius, max_kp=200)

iss_identical = np.array_equal(kp_s, kp_d)
print(f"\n[iss] keypoint 数 src/dst            : {len(kp_s)} / {len(kp_d)}")
print(f"[iss] 回転不変(index 配列が一致)     : {iss_identical}")

assert len(kp_s) >= 30, f"ISS keypoint が少なすぎ評価が不安定: {len(kp_s)}"
assert iss_identical, "ISS が回転不変でない(回した雲で別の点を選んだ)"


# ═════════════════════════════════════════════════════════════════════════════
# PART 3 — shot_descriptor: 回転不変(対応距離~0)かつ識別的(自己マッチ高率)
# ═════════════════════════════════════════════════════════════════════════════
# src/dst は同一点を回した関係で index が揃う ⇒ keypoint i の真の対応は dst の同 index i。
ns = feat_shot.estimate_normals(src, k=16)
nd = feat_shot.estimate_normals(dst, k=16)
tree_s, tree_d = cKDTree(src), cKDTree(dst)
desc_s = feat_shot.shot_descriptor(src, ns, kp_s, tree_s, radius)   # (Kp, 352)
desc_d = feat_shot.shot_descriptor(dst, nd, kp_d, tree_d, radius)
assert desc_s.shape == (len(kp_s), 352) and desc_d.shape == (len(kp_d), 352)

valid = (np.linalg.norm(desc_s, axis=1) > 1e-6) & (np.linalg.norm(desc_d, axis=1) > 1e-6)
Ds, Dd = desc_s[valid], desc_d[valid]                   # 有効行のみ(index は揃ったまま)
n_valid = int(valid.sum())

# 回転不変性: 対応点どうしの記述子距離 vs 無作為対応の距離。
corr_dist = float(np.linalg.norm(Ds - Dd, axis=1).mean())
perm = np.random.default_rng(1).permutation(n_valid)
rand_dist = float(np.linalg.norm(Ds - Dd[perm], axis=1).mean())

# 識別性: 記述子最近傍マッチが正しい対応(i→i)を復元する率。chance = 1/n_valid。
_, nn = cKDTree(Dd).query(Ds, k=1)
match_acc = float(np.mean(nn == np.arange(n_valid)))
chance = 1.0 / n_valid

print(f"\n[shot] 有効記述子 / 次元             : {n_valid} / 352")
print(f"[shot] 対応距離 vs 無作為距離        : {corr_dist:.4f}  vs  {rand_dist:.4f}")
print(f"[shot] 記述子最近傍の対応正答率       : {match_acc:.3f}  (chance={chance:.4f})")

assert n_valid >= 30, f"有効な SHOT 記述子が少なすぎ: {n_valid}"
assert corr_dist < 0.2 * rand_dist, \
    f"SHOT が回転不変でない(対応距離が無作為と大差ない): {corr_dist:.4f} vs {rand_dist:.4f}"
assert match_acc > 0.5, f"SHOT の識別性不足(最近傍が対応を復元できない): {match_acc:.3f}"
assert match_acc > 20.0 * chance, \
    f"SHOT 自己マッチが偶然を判別的に上回れていない: {match_acc:.3f} vs {chance:.4f}"


# ═════════════════════════════════════════════════════════════════════════════
# PART 4 — register_{spin,fpfh,shot}: 初期推定なしで既知 57 度姿勢を復元(GT)
# ═════════════════════════════════════════════════════════════════════════════
# 各 op は「dst ≈ src @ R.T + t」(=R@src_i+t)の規約。復元 (R,t) を真値 (R_gt,t_gt) と照合。
def to_np(x):
    import torch
    return x.cpu().numpy() if isinstance(x, torch.Tensor) else np.asarray(x)


R_spin, t_spin, info_spin = feat_spin.register_spin(src, dst, seed=0)
R_fpfh, t_fpfh, info_fpfh = feat_fpfh.register_fpfh(src, dst, seed=0)
R_shot, t_shot, info_shot = feat_shot.register_shot(src, dst, seed=0)

results = {
    "register_spin": (to_np(R_spin), to_np(t_spin), info_spin),
    "register_fpfh": (to_np(R_fpfh), to_np(t_fpfh), info_fpfh),
    "register_shot": (to_np(R_shot), to_np(t_shot), info_shot),
}

TOL_R, TOL_T = 5.0, 0.15                                 # 姿勢復元の許容(coarse registration 帯域)
print(f"\n[register] null(恒等変換)の誤差     : 回転 {null_R:.1f}度 / 並進 {null_t:.3f}")
Rs = []
for name, (R, t, info) in results.items():
    eR = rot_angle_deg(R, R_gt)
    eT = float(np.linalg.norm(t - t_gt))
    Rs.append(R)
    print(f"[register] {name:14s}: 回転誤差 {eR:5.2f}度 / 並進誤差 {eT:.3f}  "
          f"(null比 回転 {null_R / max(eR, 1e-9):5.0f}x)")
    assert eR < TOL_R, f"{name}: 回転誤差が大きすぎる {eR:.2f} 度"
    assert eT < TOL_T, f"{name}: 並進誤差が大きすぎる {eT:.3f}"
    # beat-null: 復元は「何もしない」を桁違いに下回る
    assert eR < 0.2 * null_R, f"{name}: 回転が null を判別的に下回れていない {eR:.2f} vs {null_R:.1f}"
    assert eT < 0.2 * null_t, f"{name}: 並進が null を判別的に下回れていない {eT:.3f} vs {null_t:.3f}"

# 3 手法が互いに整合(同じ姿勢へ収束)することも確認。
for i in range(len(Rs)):
    for j in range(i + 1, len(Rs)):
        assert rot_angle_deg(Rs[i], Rs[j]) < 2 * TOL_R, "register 3 手法の姿勢が食い違う"

print(f"\nPASS: harris3d が立方体の 8 頂点を voxel 精度(平均 {kp_corner_dist:.2f}, null {null_corner_dist:.1f})"
      f"で検出、ISS が回転不変({len(kp_s)} 点の index 完全一致)、SHOT が回転不変"
      f"(対応距離 {corr_dist:.3f}<<無作為 {rand_dist:.3f})かつ識別的(自己マッチ {match_acc:.2f})、"
      f"register_spin/fpfh/shot が初期推定なしで 57 度姿勢を回転誤差<{TOL_R}度・並進<{TOL_T}"
      f"(恒等 null 回転 {null_R:.0f}度を桁違いに下回る)で復元")
