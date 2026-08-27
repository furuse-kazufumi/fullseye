"""事例: ビンピッキングの下ごしらえ「台を消して、掴める塊を数える」.

ロボットが台の上に置かれた複数の物体を掴むとき、まず知覚が答えるべきは
「台はどこで、その上に分離した塊が何個あるか」。生のセンサ点群には (a) 大きな
接地平面(テーブル)と (b) その上の複数物体が混ざって入ってくる。台の点を先に
剥がし、残った点を空間的な近さで束ねれば「掴める候補」が塊単位で得られる。

方法(2 つの op を連結):
1. plane_segmentation で最大 consensus 平面(=テーブル)を 1 枚だけ抽出し、その
   inlier(台の点)を除去する。残差点(labels == -1)が「台に載っている物体」。
2. euclidean_cluster で残差点を近接半径 tol の連結成分に束ね、個々の物体へ分離する。
   op1 の出力(非台点)を op2 の入力に流し込む = op の協調を見せるのが主眼。

正解データ(GT): 台の上に既知位置で 3 物体(球・箱・円柱の表面点群)を合成する。
生成時に各物体の真の重心を保持しているので、検出クラスタと突き合わせられる。
- GT-1: 検出クラスタ数 == 3。
- GT-2: 各クラスタ重心が、対応する生成重心から 1 ボクセル以内。
beat-the-null: 非台点をひとまとめ(1 クラスタ)として扱う素朴な基準線では、3 物体は
1 個の塊にしか見えない(クラスタ数 == 1)。実手法がこの基準線を上回る(3 != 1)ことを
明示的に確認する。

段階的な検証: op を 1 つずつ通し、各段の中間結果(台点数 / 残差点数 / クラスタ数)を
表示してから最終 assert に進む。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# examples_3d/ の 1 つ上(imgevolve リポジトリルート)を import パスへ。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from segment3d import euclidean_cluster, plane_segmentation  # noqa: E402


# ═══════════════════════════════════════════════════════════════════════════
# 合成データ: 台平面 + 既知位置の 3 物体(球 / 箱 / 円柱の表面点群)
# ═══════════════════════════════════════════════════════════════════════════
def sphere_surface(center, radius, n, rng):
    """半径 radius の球面上に一様サンプル(方向は正規分布を正規化)。"""
    v = rng.normal(size=(n, 3))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    return np.asarray(center, float) + radius * v


def box_surface(center, half, n, rng):
    """直方体(半辺 half=(hx,hy,hz))の 6 面上に一様サンプル。"""
    c = np.asarray(center, float)
    h = np.asarray(half, float)
    pts = np.empty((n, 3))
    for i in range(n):
        f = rng.integers(0, 6)                       # 6 面のどれか
        u = (rng.random(3) * 2.0 - 1.0) * h          # 立方体内の一様点(面へ貼る前)
        u[f // 2] = (-h if f % 2 == 0 else h)[f // 2]  # 該当軸を面に固定
        pts[i] = c + u
    return pts


def cylinder_surface(center, radius, height, n, rng):
    """z 軸に平行な円柱の側面 + 上下キャップに一様サンプル(重心が中心に来る対称形)。"""
    c = np.asarray(center, float)
    pts = np.empty((n, 3))
    for i in range(n):
        theta = rng.random() * 2.0 * np.pi
        if rng.random() < 0.6:                       # 側面
            z = (rng.random() - 0.5) * height
            r = radius
        else:                                        # 上下いずれかのキャップ
            z = (0.5 if rng.random() < 0.5 else -0.5) * height
            r = radius * np.sqrt(rng.random())       # 面積一様な半径
        pts[i] = c + np.array([r * np.cos(theta), r * np.sin(theta), z])
    return pts


def build_scene(seed=0):
    """台(z=0 平面)の上に 3 物体を置いたシーンを合成し、各物体の真の重心も返す。

    Returns:
        points: (N,3) 台 + 3 物体を連結した点群(順序はシャッフルしない=決定論)。
        gt_centroids: (3,3) 生成した各物体点群の平均(真の重心)。
        ground_size: 台に属する点数(中間検証の参照値)。
    """
    rng = np.random.default_rng(seed)

    # 台: [-1.5,1.5]^2 の 30x30 グリッド at z=0 に微小ノイズ(センサ床)。
    g = np.linspace(-1.5, 1.5, 30)
    gx, gy = np.meshgrid(g, g)
    ground = np.column_stack([gx.ravel(), gy.ravel(),
                              rng.normal(0.0, 0.005, gx.size)])

    # 3 物体: xy で十分離し(gap ~1 以上)、最下点は z>=0.15(台の inlier 帯 thresh=0.03 の外)。
    sph = sphere_surface(center=(-1.0, 0.0, 0.35), radius=0.20, n=300, rng=rng)
    box = box_surface(center=(1.0, 0.0, 0.35), half=(0.15, 0.15, 0.15), n=300, rng=rng)
    cyl = cylinder_surface(center=(0.0, 1.0, 0.35), radius=0.15, height=0.30, n=300, rng=rng)

    gt_centroids = np.stack([sph.mean(0), box.mean(0), cyl.mean(0)])
    points = np.vstack([ground, sph, box, cyl])
    return points, gt_centroids, len(ground)


# ═══════════════════════════════════════════════════════════════════════════
# メイン: op を連結(台除去 → クラスタリング)して GT を検証
# ═══════════════════════════════════════════════════════════════════════════
def main():
    voxel_size = 0.05                                 # 重心一致の許容(1 ボクセル)
    tol = 0.15                                         # クラスタ近接半径(物体内間隔<tol<物体間 gap)

    points, gt_centroids, ground_size = build_scene(seed=0)
    print(f"合成シーン点数           : {len(points)}  (台 {ground_size} + 物体 900)")
    print(f"真の物体重心 (3 個)       :\n{np.round(gt_centroids, 3)}")

    # --- op1: plane_segmentation で台(最大 consensus 平面)を 1 枚だけ抽出 ---
    #   max_planes=1 = 台だけを剥がす(箱の平らな面まで平面として拾わない)。
    plane_labels = plane_segmentation(points, thresh=0.03, min_inliers=100,
                                      max_planes=1, iters=300, seed=0)
    is_table = plane_labels == 0                       # ラベル 0 = 抽出された台
    non_table = points[~is_table]                      # 残差点(labels==-1)= 台に載る物体
    print(f"台として除去した点数     : {int(is_table.sum())}")
    print(f"残差(非台)点数         : {len(non_table)}")

    # --- op2: euclidean_cluster で残差点を空間的近さで塊へ分離 ---
    #   op1 の出力(非台点)を op2 の入力に流す = op 連結の要。
    cluster_labels = euclidean_cluster(non_table, tol=tol, min_size=20)
    valid = np.unique(cluster_labels[cluster_labels >= 0])
    n_clusters = len(valid)
    print(f"検出クラスタ数           : {n_clusters}")

    # --- beat-the-null: 非台点を「1 クラスタ」とみなす素朴基準線 ---
    #   台さえ剥がせば 1 塊、と決め打つと 3 物体を分離できない(クラスタ数 1)。
    null_n_clusters = 1
    print(f"null 基準線のクラスタ数   : {null_n_clusters}  (非台点をひとまとめ)")

    # --- 検出クラスタ重心を各真重心へ最近傍マッチ ---
    cluster_centroids = np.stack([non_table[cluster_labels == c].mean(0) for c in valid]) \
        if n_clusters > 0 else np.zeros((0, 3))
    match_errors = []
    if n_clusters == len(gt_centroids):
        used = set()
        for cc in cluster_centroids:
            d = np.linalg.norm(gt_centroids - cc, axis=1)
            order = np.argsort(d)
            j = next(k for k in order if k not in used)  # 未使用の最近傍(全単射)
            used.add(int(j))
            match_errors.append(float(d[j]))
        print(f"重心マッチ誤差 (最大)     : {max(match_errors):.4f}  (許容 1 voxel={voxel_size})")

    # --- GT アサート ---
    # GT-1 & beat-the-null: 実手法は 3 クラスタ、null 基準線(1)を上回る。
    assert n_clusters == 3, f"クラスタ数が 3 でない: {n_clusters}"
    assert n_clusters > null_n_clusters, \
        f"実手法が null 基準線を上回っていない: {n_clusters} vs {null_n_clusters}"
    # GT-2: 各クラスタ重心が対応する生成重心から 1 ボクセル以内。
    assert len(match_errors) == 3, "全クラスタを真重心へ全単射マッチできていない"
    assert max(match_errors) < voxel_size, \
        f"重心誤差が 1 voxel を超過: {max(match_errors):.4f} >= {voxel_size}"

    print(f"PASS: 台除去→クラスタリングで 3 物体を分離(null 基準線 1 を上回る)、"
          f"全重心誤差 {max(match_errors):.4f} < 1 voxel {voxel_size}")


if __name__ == "__main__":
    main()
