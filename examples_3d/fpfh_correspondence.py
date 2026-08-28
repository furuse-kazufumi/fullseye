"""事例: 2つの部分ビュー間の点対応を FPFH 記述子で張る (features).

同じ物体を別角度から2回スキャンすると、視点が変わって重なりは一部だけ、しかも初期姿勢は
未知になる。位置合わせ(register)に進む前段として、まず「A の各点は B のどの点か」という
**対応(correspondence)** を張る必要がある。FPFH(Fast Point Feature Histogram)は各点の
まわりの法線角ヒストグラムを剛体不変にまとめた記述子で、これが一致する点どうしを最近傍で
結べば、大回転していても初期推定なしに対応が付く。ここは register パイプライン全体ではなく、
その心臓部である **記述子マッチそのものの品質(正答率)** を測る。

ビュー A(物体座標)とビュー B(既知の R,t で回転並進した別の部分)を作り、重なり領域の
点には真の対応(同一物体点)を保持する。両ビューで FPFH を計算し、記述子最近傍で対応を張り、
「結ばれた B 点を既知変換で A 座標へ戻すと真の A 点の近くに落ちるか」で幾何的な正誤を数える。

検証(GT): 重なり点での FPFH 正答率は偶然(ランダム対応/記述子をシャッフルした対応)の
正答率を大きく上回る。ランダム対応は「B 点が真の位置の許容半径内に居る割合」= チャンス率
そのものなので、FPFH 正答率 >> チャンス率 なら記述子が実際に位置を識別できている証拠になる。
"""
import sys
from pathlib import Path

# リポジトリ直下を sys.path 先頭へ(examples_3d の同名ファイルがトップレベル module を
# 隠すのを防ぐ。fullseye module を import する前に必ず行う)。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from scipy.spatial import cKDTree          # 記述子最近傍検索と幾何計測(measurement のみ)
import feat_fpfh                            # fullseye の FPFH op(記述子=本例の主役)


def rotation_matrix(axis, deg):
    """軸まわり deg 度の回転行列(ロドリゲスの公式)。"""
    a = np.asarray(axis, float)
    a /= np.linalg.norm(a)
    th = np.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * K @ K


def lumpy_object(n=3000, seed=0):
    """非対称な「でこぼこの塊」の表面点を返す(原点まわりの星形=法線が外向きに一意)。

    球面上に一様(Fibonacci 螺旋)な方向 d を取り、半径を R0 + Σ 異方ガウス隆起/窪みで
    変調する。隆起は振幅・幅・向きをすべて違えて置くので回転対称が無く、局所曲率が場所ごと
    に異なる=FPFH が識別的になる(平坦な面や球だと記述子が縮退してマッチが曖昧になる)。
    """
    # Fibonacci 球面サンプリング(決定的・ほぼ一様)
    i = np.arange(n) + 0.5
    phi = np.arccos(1.0 - 2.0 * i / n)              # 極角
    gold = np.pi * (1.0 + 5.0 ** 0.5)               # 黄金角
    tha = gold * i
    d = np.stack([np.sin(phi) * np.cos(tha),
                  np.sin(phi) * np.sin(tha),
                  np.cos(phi)], axis=1)              # (n,3) 単位方向
    # 非対称な隆起/窪み(中心方向, 振幅, 角度幅)。振幅負=窪み。
    bumps = [([1.0, 0.0, 0.0],  0.35, 0.50),
             ([0.0, 1.0, 0.0], -0.22, 0.40),
             ([0.0, 0.0, 1.0],  0.28, 0.60),
             ([-1.0, 0.5, 0.3], 0.20, 0.35),
             ([0.4, -1.0, 0.5], 0.26, 0.45),
             ([0.2, 0.3, -1.0], -0.16, 0.50)]
    r = np.full(n, 1.0)                              # R0 = 1
    for c, amp, w in bumps:
        c = np.asarray(c, float); c /= np.linalg.norm(c)
        theta = np.arccos(np.clip(d @ c, -1.0, 1.0))
        r = r + amp * np.exp(-theta ** 2 / (2.0 * w ** 2))
    return d * r[:, None]                            # 表面点 = 半径 × 方向


# --- 1) 物体と、2つの部分ビュー(既知の剛体変換で重なり一部)-----------------
obj = lumpy_object(n=3000, seed=0)                   # 物体座標系の全点
R_gt = rotation_matrix([0.3, 1.0, 0.2], 58.0)        # ビュー B の未知姿勢(真値)= 58度回転
t_gt = np.array([2.0, -1.0, 0.5])                    # ビュー B の未知並進(真値)

# 各点の視方向で「どちらのビューに写るか」を決める(重なりのある2つの部分ビュー)。
dirn = obj / np.linalg.norm(obj, axis=1, keepdims=True)
axA = np.array([1.0, 0.2, 0.1]); axA /= np.linalg.norm(axA)
axB = np.array([0.2, 1.0, 0.3]); axB /= np.linalg.norm(axB)   # A と ~60度離す
maskA = (dirn @ axA) > -0.35                         # A に写る点(半球より少し広い cap)
maskB = (dirn @ axB) > -0.35                         # B に写る点(別向きの cap)
idxA = np.where(maskA)[0]                             # A の各行が指す物体点の global index
idxB = np.where(maskB)[0]

res_probe = float(np.median(cKDTree(obj).query(obj, k=2)[0][:, -1]))  # 点間隔(解像度)
rng = np.random.default_rng(42)
# ビュー A は物体座標のまま、ビュー B は真の (R,t) で置き直す。両者に独立なセンサノイズ。
viewA = obj[idxA] + rng.normal(0.0, 0.25 * res_probe, (len(idxA), 3))
viewB = obj[idxB] @ R_gt.T + t_gt + rng.normal(0.0, 0.25 * res_probe, (len(idxB), 3))

# 重なり点の真の対応: 同一 global index g が A・B 双方に写る点。
overlap_g = np.intersect1d(idxA, idxB)               # 重なり領域の global index
posA = {g: r for r, g in enumerate(idxA)}            # global -> A の行
posB = {g: r for r, g in enumerate(idxB)}            # global -> B の行
a_rows = np.array([posA[g] for g in overlap_g])      # 評価する A 行
gt_pos = obj[overlap_g]                              # その真の物体位置(GT)

res = float(np.median(cKDTree(viewA).query(viewA, k=2)[0][:, -1]))    # A の解像度
tol = 1.5 * res                                       # 正答許容半径(点間隔の1.5倍=厳しめ)

# --- 2) fullseye の FPFH op で両ビューの記述子を計算 --------------------------
# 法線は既知の視点(物体中心)を参照に外向き統一 — A は原点、B はその像 t_gt。
# これで部分重なりでも法線符号が一致し、測るのが純粋に「記述子の識別力」になる。
nA = feat_fpfh.estimate_point_normals(viewA, k=16, orient_ref=[0.0, 0.0, 0.0])
nB = feat_fpfh.estimate_point_normals(viewB, k=16, orient_ref=t_gt)
fA = feat_fpfh.compute_fpfh(viewA, nA, k=60, n_bins=11)   # (len(A), 33)
fB = feat_fpfh.compute_fpfh(viewB, nB, k=60, n_bins=11)   # (len(B), 33)
assert fA.shape == (len(viewA), 33) and fB.shape == (len(viewB), 33)


def correct_rate(matched_rows):
    """B の行 index 列 → 幾何的に正しい対応の割合。

    結ばれた B 点を既知変換で A 座標へ戻し、真の A 点(gt_pos)との距離が tol 未満なら正答。
    """
    b = viewB[matched_rows]
    b_back = (b - t_gt) @ R_gt                        # R^T (b - t):A 座標へ戻す
    err = np.linalg.norm(b_back - gt_pos, axis=1)
    return float((err < tol).mean())


# --- 3) FPFH: 記述子最近傍で対応を張る ---------------------------------------
tB = cKDTree(fB)
_, nn = tB.query(fA[a_rows], k=1)                     # A 重なり点 → B の記述子最近傍
fpfh_rate = correct_rate(nn)

# --- 4) null-A: ランダム対応(= チャンス率。B 点が真位置の tol 内に居る割合)-----
rng_null = np.random.default_rng(7)
rand_rates = [correct_rate(rng_null.integers(0, len(viewB), len(a_rows)))
              for _ in range(30)]
null_random = float(np.mean(rand_rates))

# --- 5) null-B: 記述子をシャッフルしてから同じ最近傍マッチ(信号を壊した同一手続き)---
perm = np.random.default_rng(11).permutation(len(fB))
tB_shuf = cKDTree(fB[perm])                           # 位置と記述子の対応を破壊
_, nn_shuf_local = tB_shuf.query(fA[a_rows], k=1)
null_shuffled = correct_rate(perm[nn_shuf_local])     # 実際に選ばれた B 行へ戻す

print(f"物体点数 / 解像度(点間隔)     : {len(obj)} 点 / res={res:.4f}")
print(f"ビュー A / B / 重なり点数        : {len(viewA)} / {len(viewB)} / {len(overlap_g)}")
print(f"正答許容半径 tol                 : {tol:.4f}  (= 1.5 * res)")
print(f"FPFH 正答率(重なり)            : {fpfh_rate:.3f}")
print(f"null ランダム対応(チャンス率)  : {null_random:.4f}")
print(f"null 記述子シャッフル対応        : {null_shuffled:.4f}")
print(f"FPFH / チャンス 比               : {fpfh_rate / max(null_random, 1e-9):.1f} 倍")

# GT: FPFH の対応正答率はチャンス率を大きく上回る(記述子が位置を識別できている)。
# 重なりには境界点も含む(そこは近傍構成が食い違い記述子が劣化)ので 1.0 にはならないが、
# 内部の重なり点は正しく対応が付き、偶然(< 数%)を桁で引き離す。判別的な下限を要求:
assert len(overlap_g) >= 300, f"重なり点が少なすぎ評価が不安定: {len(overlap_g)}"
assert null_random < 0.05, f"チャンス率が高すぎ(tol/密度が緩い): {null_random:.4f}"
assert null_shuffled < 0.05, f"シャッフル null が高すぎ: {null_shuffled:.4f}"
assert fpfh_rate > 0.35, f"FPFH 正答率が低すぎ(記述子が識別できていない): {fpfh_rate:.3f}"
assert fpfh_rate > 8.0 * null_random, \
    f"FPFH がチャンスを十分に上回っていない: {fpfh_rate:.3f} vs {null_random:.4f}"
assert fpfh_rate > 8.0 * null_shuffled, \
    f"FPFH がシャッフル null を十分に上回っていない: {fpfh_rate:.3f} vs {null_shuffled:.4f}"
print(f"PASS: FPFH 対応正答率 {fpfh_rate:.3f} が偶然 {null_random:.4f} を "
      f"{fpfh_rate / max(null_random, 1e-9):.0f}倍上回る(58度回転+部分重なりで記述子マッチが機能)")
