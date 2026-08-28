# -*- coding: utf-8 -*-
"""事例: 3D 再構成/登録の良し悪しを 4 つの評価指標で数値化する (reconstruction).

平たく言うと: 「復元した 3D 形状は正解にどれだけ近いか」を人の目でなく数字で言い切りたい。
1 つの指標では嘘をつける(位置は合っても向きが逆、体積は合っても表面がズレ 等)ので、性質の
違う 4 指標を組み合わせる:
  - fscore(tau)            : 表面点が許容半径 tau 内で「取りこぼしなく(recall)・余計なく(precision)」
                             一致しているか。再構成の標準スコア。
  - rmse_correspondence    : 対応が既知(同 index)な点対の位置ズレの二乗平均平方根。登録残差。
  - normal_consistency     : 最近傍で結んだ法線の向き一致度 mean|cos|。表面の「向き」が合っているか。
  - voxel_iou              : 占有ボクセルの体積一致度(intersection over union)。中身が合っているか。
ここでは **正解が既知の合成データ**を作り、4 指標が解析的な真値に一致することを検証し、さらに
劣化した再構成では各指標が正しく下がる(=検出できる)ことを示す。

検証(GT): 各指標を「作り方から閉形式で分かる真値」と 1e-9 で照合する。
  - fscore   : 正解 N 点のうち n_cov 点を厳密コピー・n_out 個を tau 外の外れ点にした再構成を作ると
               precision = n_cov/(n_cov+n_out), recall = n_cov/N が厳密に決まる(点間隔 > tau が前提)。
  - rmse     : 既知オフセット v を全点に足せば残差は厳密に |v|、恒等コピーは厳密に 0。
  - normal_c : 同一/反転法線は |cos|=1 で厳密に 1.0(向き無視)。無作為法線は E[|cos|]=0.5。
  - voxel_iou: 一辺 L の 2 立方体を既知量 (dx,dy,dz) ずらすと交わり=(L-dx)(L-dy)(L-dz)、
               和=2L^3-交わり で IoU が閉形式に決まる。恒等=1、離れた立方体=0。

beat-the-null: 各指標が「当てずっぽうの再構成(null)」を判別的に上回ることを assert する。
無作為点群では fscore≈0、無作為法線では normal_consistency≈0.5、離れた立方体では voxel_iou=0 に落ち、
真の再構成のスコア(それぞれ 0.727 / 1.0 / 0.28)がこの null を明確に上回る。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np
import metrics3d as M


def fibonacci_sphere(n, seed=0):
    """単位球面上に n 点をほぼ等間隔に配置(黄金角スパイラル)。半径 1 なので法線=座標そのもの。"""
    i = np.arange(n) + 0.5
    phi = np.arccos(1.0 - 2.0 * i / n)          # 極角
    gold = np.pi * (1.0 + 5.0 ** 0.5)           # 黄金角
    theta = gold * i
    x = np.sin(phi) * np.cos(theta)
    y = np.sin(phi) * np.sin(theta)
    z = np.cos(phi)
    return np.stack([x, y, z], axis=1)


rng = np.random.default_rng(0)

# ── 正解サーフェス: 単位球点群 + 解析的な法線(放射方向 = 座標)────────────────
N = 150
P_gt = fibonacci_sphere(N)                       # 正解の表面点群
n_gt = P_gt.copy()                               # 単位球なので法線 = 位置ベクトル(既に単位長)

# 点間隔(最近傍距離)の最小値を測る: fscore の recall 真値には「点間隔 > tau」が前提。
from scipy.spatial import cKDTree
d2, _ = cKDTree(P_gt).query(P_gt, k=2)           # k=2 の 2 列目 = 最近傍(自分以外)距離
min_spacing = float(d2[:, 1].min())

# ═══════════════════════════════════════════════════════════════════════════
# 1) fscore — precision/recall を作り方から厳密に決めた再構成で検証
# ═══════════════════════════════════════════════════════════════════════════
tau = 0.05
assert min_spacing > tau, f"点間隔 {min_spacing:.3f} が tau {tau} を下回ると recall 真値が崩れる"

n_cov, n_out = 120, 60                            # 120 点は厳密コピー / 60 点は外れ点
# 外れ点: 半径 5 の球殻上(正解球=半径1 なので最近傍距離 >= 4 >> tau → precision に入らない)
dirs = rng.normal(size=(n_out, 3))
dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
outliers = dirs * 5.0
A_recon = np.vstack([P_gt[:n_cov], outliers])    # 劣化再構成: 一部取りこぼし + 一部外れ点

# 完全再構成(= 正解のコピー)
f_perfect, p_perfect, r_perfect = M.fscore(P_gt, P_gt, tau)
# 劣化再構成
f_deg, p_deg, r_deg = M.fscore(A_recon, P_gt, tau)
# null: 箱 [-3,3]^3 に無作為点(表面にほぼ乗らない)
A_null = rng.uniform(-3.0, 3.0, size=(n_cov + n_out, 3))
f_null, p_null, r_null = M.fscore(A_null, P_gt, tau)

# 解析真値
p_true = n_cov / (n_cov + n_out)                 # 120/180 = 0.6667
r_true = n_cov / N                               # 120/150 = 0.8
f_true = 2 * p_true * r_true / (p_true + r_true) # 0.7273

print("[1] fscore@%.2f" % tau)
print("  perfect : f=%.6f p=%.6f r=%.6f" % (f_perfect, p_perfect, r_perfect))
print("  degraded: f=%.6f p=%.6f r=%.6f  (true p=%.6f r=%.6f f=%.6f)"
      % (f_deg, p_deg, r_deg, p_true, r_true, f_true))
print("  null    : f=%.6f p=%.6f r=%.6f" % (f_null, p_null, r_null))

assert abs(f_perfect - 1.0) < 1e-9 and abs(p_perfect - 1.0) < 1e-9 and abs(r_perfect - 1.0) < 1e-9, \
    "完全再構成は f=p=r=1.0 のはず"
assert abs(p_deg - p_true) < 1e-9, f"precision 真値と不一致: {p_deg} vs {p_true}"
assert abs(r_deg - r_true) < 1e-9, f"recall 真値と不一致: {r_deg} vs {r_true}"
assert abs(f_deg - f_true) < 1e-9, f"F-score 真値と不一致: {f_deg} vs {f_true}"
# beat-null: 真の劣化再構成(0.727)は当てずっぽう(≈0)を大きく上回り、完全(1.0)は下回る
assert f_null < 0.05, f"null の F-score が高すぎる: {f_null}"
assert f_deg > f_null + 0.3 and f_deg < f_perfect, "F-score が null と perfect の間に来ていない"

# ═══════════════════════════════════════════════════════════════════════════
# 2) rmse_correspondence — 対応既知の点対の残差を既知オフセットで検証
# ═══════════════════════════════════════════════════════════════════════════
v = np.array([0.06, -0.08, 0.0])                 # 既知の並進オフセット
offset_norm = float(np.linalg.norm(v))           # |v| = 0.1 が残差の真値
P_shift = P_gt + v                               # index 対応を保ったままズラす

rmse_identity = M.rmse_correspondence(P_gt, P_gt)      # 恒等 → 0
rmse_shift = M.rmse_correspondence(P_shift, P_gt)      # 一様オフセット → |v|

print("[2] rmse_correspondence")
print("  identity=%.9f  shift=%.9f  (true |v|=%.9f)" % (rmse_identity, rmse_shift, offset_norm))

assert rmse_identity < 1e-12, f"恒等コピーの RMSE は 0 のはず: {rmse_identity}"
assert abs(rmse_shift - offset_norm) < 1e-9, f"一様オフセットの RMSE 真値と不一致: {rmse_shift} vs {offset_norm}"
assert rmse_shift > rmse_identity, "オフセットありの残差が恒等を上回っていない(検出できていない)"
# fail-closed: 対応数が違えば静かに 0 を返さず ValueError(honest)
try:
    M.rmse_correspondence(P_gt, P_gt[:100])
    raise AssertionError("対応数不一致で ValueError が出ていない")
except ValueError:
    pass

# ═══════════════════════════════════════════════════════════════════════════
# 3) normal_consistency — 向き一致度。同一/反転=1.0、無作為=0.5(null)
# ═══════════════════════════════════════════════════════════════════════════
# 同一法線
nc_same = M.normal_consistency(P_gt, n_gt, P_gt, n_gt)
# 反転法線: |cos| なので向きを反転しても 1.0(向き無視の性質)
nc_flip = M.normal_consistency(P_gt, n_gt, P_gt, -n_gt)
# 点に微小ノイズ(< 最近傍間隔の半分)を載せても最近傍対応は同一 index に戻る → 1.0
P_noisy = P_gt + rng.normal(scale=0.01, size=P_gt.shape)
nc_noisy = M.normal_consistency(P_noisy, n_gt, P_gt, n_gt)
# null: 無作為な単位法線(向きが正解と無関係)→ E[|cos|]=0.5
rand_n = rng.normal(size=(N, 3))
rand_n /= np.linalg.norm(rand_n, axis=1, keepdims=True)
nc_rand = M.normal_consistency(P_gt, n_gt, P_gt, rand_n)

print("[3] normal_consistency")
print("  same=%.9f  flip=%.9f  noisy_pts=%.9f  random=%.6f" % (nc_same, nc_flip, nc_noisy, nc_rand))

assert abs(nc_same - 1.0) < 1e-9, f"同一法線は 1.0 のはず: {nc_same}"
assert abs(nc_flip - 1.0) < 1e-9, f"反転法線も |cos|=1 で 1.0 のはず(向き無視): {nc_flip}"
assert nc_noisy > 0.999, f"微小点ノイズでも最近傍対応で 1.0 近傍のはず: {nc_noisy}"
# beat-null: 無作為法線は 0.5 付近、真の一致(1.0)がこれを明確に上回る
assert 0.4 < nc_rand < 0.6, f"無作為法線の |cos| 期待値 0.5 から外れすぎ: {nc_rand}"
assert nc_same - nc_rand > 0.3, "法線一致度が無作為 null を判別的に上回れていない"

# ═══════════════════════════════════════════════════════════════════════════
# 4) voxel_iou — 占有体積の一致度。2 立方体の重なりを閉形式で検証
# ═══════════════════════════════════════════════════════════════════════════
G = 32
L = 12
dx, dy, dz = 5, 3, 0                              # 立方体 B のズレ量(各軸)
V_a = np.zeros((G, G, G), dtype=float)
V_b = np.zeros((G, G, G), dtype=float)
V_d = np.zeros((G, G, G), dtype=float)           # 離れた立方体(null)
V_a[4:4 + L, 4:4 + L, 4:4 + L] = 1.0
V_b[4 + dx:4 + dx + L, 4 + dy:4 + dy + L, 4 + dz:4 + dz + L] = 1.0
V_d[4 + L + 4:4 + L + 4 + L, 4:4 + L, 4:4 + L] = 1.0  # x 方向に完全に離す

inter = (L - dx) * (L - dy) * (L - dz)           # 交わり体積(閉形式)
union = 2 * L ** 3 - inter                        # 和 = |A|+|B|-|A∩B|
iou_true = inter / union                          # 756/2700 = 0.28

iou_identity = M.voxel_iou(V_a, V_a)             # 恒等 → 1.0
iou_overlap = M.voxel_iou(V_a, V_b)              # 部分重なり → 閉形式真値
iou_disjoint = M.voxel_iou(V_a, V_d)             # 離れている → 0.0

print("[4] voxel_iou")
print("  identity=%.9f  overlap=%.9f  (true=%.9f)  disjoint=%.9f"
      % (iou_identity, iou_overlap, iou_true, iou_disjoint))

assert abs(iou_identity - 1.0) < 1e-12, f"恒等の IoU は 1.0 のはず: {iou_identity}"
assert abs(iou_overlap - iou_true) < 1e-12, f"部分重なりの IoU 真値と不一致: {iou_overlap} vs {iou_true}"
assert iou_disjoint == 0.0, f"離れた立方体の IoU は 0 のはず: {iou_disjoint}"
# beat-null: 部分重なり(0.28)は離れ(0)を上回り、恒等(1.0)を下回る = ズレを検出できる
assert iou_disjoint < iou_overlap < iou_identity, "IoU が disjoint < overlap < identity の順になっていない"
# fail-closed: shape 不一致は broadcasting で誤魔化さず ValueError(honest)
try:
    M.voxel_iou(V_a, np.zeros((G, G, G // 2), dtype=float))
    raise AssertionError("shape 不一致で ValueError が出ていない")
except ValueError:
    pass

# ── 総括: 4 指標が完全再構成では理想値、劣化では正しく低下(null を判別的に超える)────
print("PASS: 4 評価指標を解析真値と 1e-9 で照合 — "
      "fscore(perfect f=1.0 / degraded f=%.4f=真値 / null≈%.3f), "
      "rmse(identity=0 / offset=%.3f=|v|), "
      "normal_consistency(same/flip=1.0 / random≈%.3f=null), "
      "voxel_iou(identity=1.0 / overlap=%.4f=真値 / disjoint=0)。"
      "各指標が当てずっぽう null を判別的に上回ることを確認。"
      % (f_deg, f_null, rmse_shift, nc_rand, iou_overlap))
