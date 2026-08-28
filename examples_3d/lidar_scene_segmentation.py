"""事例: 屋外 LiDAR シーンから地面を剥がして物体を数える (segmentation).

自動運転車や屋外ロボットの LiDAR は、広い地面(緩やかに傾いたアスファルト等)の上に
点在する物体(車・箱・柱・岩)を一度に捉える。掴む・避ける・数える前に知覚がまず
答えるべきは「どこが地面で、その上に分離した物体がいくつあるか」。生の点群では
地面が全物体を橋渡しして繋いでしまうので、素朴に近接クラスタリングしても全部が
1 塊に癒着して分離できない。そこで (1) RANSAC で支配平面(=地面)を当て、
height_above_plane で地面帯より上の点だけ残して地面を除去し、(2) 残差点を
euclidean_clusters で近接連結成分に束ねて個々の物体へ分ける。地面は水平ではなく
緩く傾けてあるので、単純な z しきい値では分離できず平面フィットが本質的に効く。

検証(GT): 地面(傾斜平面)の上に既知位置で K=4 物体(球・箱・円柱・円錐の表面点群)を
合成する。各物体の真の重心を生成時に保持しているので検出クラスタと突き合わせられる。
  * GT-1: 地面除去後のクラスタ数 == K(=4)。
  * GT-2: 各クラスタ重心が対応する生成物体の重心へ全単射で一致(許容 0.5m、
          物体間隔 4.0m の 1/8 未満 = 取り違え不可能)。
  beat-null: 地面を除去せず全点をそのまま euclidean_clusters にかけると、地面が
  全物体を繋いで 1 クラスタ(=全物体癒着)にしかならない。地面除去ありは K を復元し、
  地面除去なし null は K より遥かに小さい数(=1)しか出せないことを判別的に確認する。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# examples_3d/ の 1 つ上(imgevolve リポジトリルート)を import パスへ。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pcseg import centroid, euclidean_clusters, fit_plane_ransac, height_above_plane  # noqa: E402


# ═══════════════════════════════════════════════════════════════════════════
# 合成データ: 緩く傾いた地面 + 既知位置の 4 物体(球 / 箱 / 円柱 / 円錐の表面点群)
# ═══════════════════════════════════════════════════════════════════════════
# 地面の高さ z = GA*x + GB*y(原点を通る傾斜平面)。傾き ~5.4 度(atan(√(GA²+GB²)))。
GA, GB = 0.08, 0.05


def ground_z(x, y):
    """地面(傾斜平面)の高さ z を (x,y) から返す。"""
    return GA * np.asarray(x, float) + GB * np.asarray(y, float)


def ground_surface(half=4.0, step=0.15, noise=0.01, rng=None):
    """[-half,half]^2 を step 刻みでサンプルした傾斜地面 + 微小センサノイズ。"""
    g = np.arange(-half, half + 1e-9, step)
    gx, gy = np.meshgrid(g, g)
    gx, gy = gx.ravel(), gy.ravel()
    gz = ground_z(gx, gy) + rng.normal(0.0, noise, gx.shape)
    return np.column_stack([gx, gy, gz])


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


def cylinder_surface(base_center, radius, height, n, rng):
    """z 軸に平行な円柱(底面が base_center)の側面 + 上下キャップに一様サンプル。"""
    c = np.asarray(base_center, float)
    pts = np.empty((n, 3))
    for i in range(n):
        theta = rng.random() * 2.0 * np.pi
        if rng.random() < 0.7:                       # 側面
            z = rng.random() * height
            r = radius
        else:                                        # 上下いずれかのキャップ
            z = height if rng.random() < 0.5 else 0.0
            r = radius * np.sqrt(rng.random())       # 面積一様な半径
        pts[i] = c + np.array([r * np.cos(theta), r * np.sin(theta), z])
    return pts


def cone_surface(base_center, radius, height, n, rng):
    """底面が base_center・頂点が上の円錐の側面 + 底面円板に一様サンプル。"""
    c = np.asarray(base_center, float)
    pts = np.empty((n, 3))
    for i in range(n):
        theta = rng.random() * 2.0 * np.pi
        if rng.random() < 0.75:                       # 側面(高さ u で半径 radius*(1-u))
            u = rng.random()
            r = radius * (1.0 - u)
            z = height * u
        else:                                         # 底面円板
            r = radius * np.sqrt(rng.random())
            z = 0.0
        pts[i] = c + np.array([r * np.cos(theta), r * np.sin(theta), z])
    return pts


def build_scene(seed=0):
    """傾斜地面の上に 4 物体(球/箱/円柱/円錐)を四隅へ十分離して合成する。

    各物体は自分の (x,y) での地面高さに底を接地させて配置する。
    Returns: (points (N,3), gt_centroids (4,3), n_ground)
    """
    rng = np.random.default_rng(seed)
    ground = ground_surface(half=4.0, step=0.15, noise=0.01, rng=rng)

    # 四隅に配置(間隔 4.0m >> クラスタ近接半径 tol=0.25m)。底 z = 各 (x,y) の地面高さ。
    N = 600
    px, py = 2.0, 2.0
    sph = sphere_surface(center=(-px, -py, ground_z(-px, -py) + 0.35),
                         radius=0.35, n=N, rng=rng)
    box = box_surface(center=(px, -py, ground_z(px, -py) + 0.35),
                      half=(0.30, 0.30, 0.35), n=N, rng=rng)
    cyl = cylinder_surface(base_center=(-px, py, ground_z(-px, py)),
                           radius=0.30, height=0.70, n=N, rng=rng)
    con = cone_surface(base_center=(px, py, ground_z(px, py)),
                       radius=0.35, height=0.80, n=N, rng=rng)

    objs = [sph, box, cyl, con]
    gt_centroids = np.stack([o.mean(0) for o in objs])   # 真の物体重心(全表面点の平均)
    points = np.vstack([ground, *objs])
    return points, gt_centroids, len(ground)


# ═══════════════════════════════════════════════════════════════════════════
# メイン: 地面除去 → クラスタリングで K 物体を復元し、GT と null を突き合わせる
# ═══════════════════════════════════════════════════════════════════════════
def main():
    K = 4                                             # 既知の物体数
    TOL = 0.25                                         # クラスタ近接半径(物体内間隔<TOL<物体間 4.0m)
    H_CUT = 0.08                                       # 地面帯の上端(この高さ以下は地面として除去)
    MATCH_TOL = 0.5                                    # 重心一致許容(物体間 4.0m の 1/8)

    points, gt_centroids, n_ground = build_scene(seed=0)
    print(f"合成シーン点数           : {len(points)}  (地面 {n_ground} + 物体 {K}x600)")
    print(f"地面の傾き               : z={GA}x+{GB}y  (~{np.degrees(np.arctan(np.hypot(GA, GB))):.1f}度)")
    print(f"真の物体重心 (4 個)       :\n{np.round(gt_centroids, 3)}")

    # --- op1: RANSAC で支配平面(=地面)を当てる ------------------------------
    plane, inliers = fit_plane_ransac(points, thresh=0.03, iters=200, seed=0)
    if plane[2] < 0:                                   # 法線を上向き(+z 側)へ揃える
        plane = -plane
    n_inliers = int(inliers.sum())
    print(f"RANSAC 地面平面           : [{plane[0]:.3f},{plane[1]:.3f},{plane[2]:.3f},{plane[3]:.3f}]"
          f"  inlier {n_inliers}")

    # --- op1(続き): height_above_plane で地面帯より上の点だけ残す = 地面除去 ---
    heights = height_above_plane(points, plane)        # 平面法線方向の符号付き高さ
    above = heights > H_CUT
    above_pts = points[above]
    print(f"地面帯(高さ<={H_CUT}m)除去後 : 残差 {len(above_pts)} 点  "
          f"(高さ範囲 [{heights.min():.2f},{heights.max():.2f}]m)")

    # --- op2: euclidean_clusters で残差点を近接連結成分へ束ねる ----------------
    real_clusters = euclidean_clusters(above_pts, tol=TOL, min_size=50)
    real_n = len(real_clusters)
    print(f"地面除去あり クラスタ数   : {real_n}  (各サイズ {[len(c) for c in real_clusters]})")

    # --- beat-null: 地面を除去せず全点をそのままクラスタリング -----------------
    #   地面が全物体を橋渡しするので 1 塊(=全物体癒着)にしかならない。
    null_clusters = euclidean_clusters(points, tol=TOL, min_size=50)
    null_n = len(null_clusters)
    print(f"地面除去なし null クラスタ: {null_n}  (各サイズ {[len(c) for c in null_clusters]})  "
          f"= 全物体が地面経由で癒着")

    # --- GT: 検出クラスタ重心を各真重心へ全単射(最近傍)マッチ ----------------
    #   物体間隔 4.0m >> 許容 0.5m なので、0.5m 以内に入る真重心は一意 = 取り違え不可能。
    cluster_centroids = np.stack([centroid(above_pts[c]) for c in real_clusters]) \
        if real_n > 0 else np.zeros((0, 3))
    gaps = [np.linalg.norm(gt_centroids[i] - gt_centroids[j])
            for i in range(K) for j in range(i + 1, K)]
    min_gap = min(gaps)
    match_errors, used = [], set()
    if real_n == K:
        for cc in cluster_centroids:
            d = np.linalg.norm(gt_centroids - cc, axis=1)
            j = next(k for k in np.argsort(d) if k not in used)   # 未使用の最近傍(全単射)
            used.add(int(j))
            match_errors.append(float(d[j]))
        print(f"重心マッチ誤差 (最大)     : {max(match_errors):.4f}m  "
              f"(許容 {MATCH_TOL}m / 物体最小間隔 {min_gap:.2f}m)")

    # ═══ GT アサート ═══════════════════════════════════════════════════════
    # GT-1 & beat-null: 地面除去ありは K を復元、地面除去なし null は K より遥かに小さい。
    assert real_n == K, f"地面除去後のクラスタ数が K={K} でない: {real_n}"
    assert null_n < real_n, \
        f"地面除去なし null が地面除去ありを下回っていない: null {null_n} vs real {real_n}"
    assert null_n <= 2, f"地面除去なし null が癒着せず物体を分離してしまった: {null_n}"
    # GT-2: 全クラスタが別々の真物体へ、物体間隔の 1/8 未満の誤差で全単射一致。
    assert MATCH_TOL < min_gap / 2.0, \
        f"許容 {MATCH_TOL}m が物体間隔の半分 {min_gap/2:.2f}m 未満でない(取り違え可能)"
    assert len(match_errors) == K, "全クラスタを真重心へ全単射マッチできていない"
    assert len(used) == K, "複数クラスタが同一物体に割り当たった(全単射でない)"
    assert max(match_errors) < MATCH_TOL, \
        f"重心誤差が許容超過: {max(match_errors):.4f}m >= {MATCH_TOL}m"

    print(f"PASS: 傾斜地面をRANSAC+height_above_plane除去→クラスタリングで {real_n} 物体を復元"
          f"(検出 {real_n} == K={K})。地面除去なし null は {null_n} クラスタ(全物体癒着)。"
          f"全クラスタが正しいGT物体へ全単射(最大重心誤差 {max(match_errors):.3f}m < 許容 {MATCH_TOL}m "
          f"<< 物体間隔 {min_gap:.1f}m)")


if __name__ == "__main__":
    main()
