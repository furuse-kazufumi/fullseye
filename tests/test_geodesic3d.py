"""geodesic3d — 平面(=Euclid)・球面(=大円距離)・メッシュ(閉形式)で測地距離を ground-truth 検証。"""
import numpy as np
import pytest
from scipy.spatial import cKDTree

import geodesic3d as G


# ----------------------------------------------------------------------------
# knn_graph の構造検証
# ----------------------------------------------------------------------------
def test_knn_graph_excludes_self_and_sorted():
    """kNN は自己を含まず、距離は昇順、インデックスは実際の k 近傍と一致。"""
    P = np.random.default_rng(1).random((60, 3))
    idx, dist = G.knn_graph(P, k=8)
    assert idx.shape == (60, 8) and dist.shape == (60, 8)
    # 自己を含まない
    assert np.all(idx != np.arange(60)[:, None])
    # 距離は各行昇順
    assert np.all(np.diff(dist, axis=1) >= -1e-12)
    # 返した距離が実 Euclid 距離と一致(GT)
    recon = np.linalg.norm(P[:, None, :] - P[idx], axis=2)
    assert np.allclose(recon, dist, atol=1e-9)
    # ブルートフォースの最近傍集合と一致(自己除く先頭 k)
    D = np.linalg.norm(P[:, None, :] - P[None, :, :], axis=2)
    for i in range(60):
        order = np.argsort(D[i])
        order = order[order != i][:8]
        assert set(idx[i].tolist()) == set(order.tolist())


# ----------------------------------------------------------------------------
# 平面: 測地距離 = Euclid 距離
# ----------------------------------------------------------------------------
def test_geodesic_plane_approximates_euclidean():
    """平坦面(z=0)では真の測地=Euclid。kNN グラフ最短路はそれを上から近似。

    GT(厳密): 各エッジは端点間の直線距離なので、経路長 = 直線分の総和 >= 端点間直線距離。
      ゆえに d_graph >= d_euclid が常に成り立つ(浮動小数点誤差のみ許容)。
    近似(密度依存): Bernstein et al. 2000 より十分密なら d_graph ≈ d_euclid。
      k=12・N=2500 の実測で平均相対過大評価 ≈ 2.7%(< 数%)。個々の最大は kNN グラフの
      異方性(方向により octile 状の遠回り)で ~11% まで出るため、平均で評価する。
    """
    rng = np.random.default_rng(0)
    P = rng.random((2500, 3))
    P[:, 2] = 0.0
    src = int(np.argmin(P[:, 0] + P[:, 1]))  # 隅付近
    d = G.geodesic_distances(P, src, k=12)
    eu = np.linalg.norm(P - P[src], axis=1)

    assert np.all(np.isfinite(d)), "十分密な kNN グラフは連結のはず"
    # 厳密な下界: グラフ最短路は直線距離を下回れない
    assert np.all(d >= eu - 1e-9)
    # 近似: 過大評価は平均で数%以内(近すぎる点は相対誤差が不安定なので除外)
    mask = eu > 0.15
    rel = (d[mask] - eu[mask]) / eu[mask]
    assert rel.mean() < 0.05, f"plane mean rel err {rel.mean():.4f}"
    assert np.median(rel) < 0.04, f"plane median rel err {np.median(rel):.4f}"


# ----------------------------------------------------------------------------
# 球面: 測地距離 = R * 中心角(大円距離)
# ----------------------------------------------------------------------------
def _fib_sphere(n: int, R: float = 1.0) -> np.ndarray:
    """Fibonacci 球で半径 R の球面を準一様サンプリング(決定論的)。"""
    i = np.arange(n) + 0.5
    phi = np.arccos(1.0 - 2.0 * i / n)
    golden = np.pi * (1.0 + 5.0 ** 0.5)
    theta = golden * i
    x = np.sin(phi) * np.cos(theta)
    y = np.sin(phi) * np.sin(theta)
    z = np.cos(phi)
    return R * np.stack([x, y, z], axis=1)


def test_geodesic_sphere_great_circle():
    """半径 R の球面で測地距離 ≈ 大円距離 R*arccos(cosθ)。

    GT: 球面 2 点の真の測地は大円距離 R*Δσ(Δσ=中心角)。
    近似の向き(Bernstein et al. 2000): kNN のエッジ長は弦長(3D 直線)で弧を僅かに
      過小評価する一方、経路のジグザグが過大評価に寄与する。密なサンプリングでは後者が
      優勢で系統的に上振れ、一様サンプリングで ~8% が経験的上限。
    実測(Fibonacci 球 n=4000, k=8): 中域(0.3<Δσ<0.9π)で相対誤差 平均 ≈ 2.7% /
      最大 ≈ 5.3% / 最小 ≈ +0.7%。弦短絡による僅かな過小評価も許すため下側 -3% まで許容。
    """
    R = 1.0
    S = _fib_sphere(4000, R)
    src = 0
    d = G.geodesic_distances(S, src, k=8)
    cosang = np.clip((S @ S[src]) / (R * R), -1.0, 1.0)
    gc = R * np.arccos(cosang)  # 大円距離(GT)

    # 両極(角 0 や ~π)は相対誤差が不安定 → 中域のみで評価
    mask = np.isfinite(d) & (gc > 0.3) & (gc < np.pi * R * 0.9)
    assert mask.sum() > 1000
    rel = (d[mask] - gc[mask]) / gc[mask]
    # 上側は既知上限 ~8% + マージンで 10%、下側は弦短絡ぶんの -3% を許容
    assert rel.max() < 0.10, f"sphere max rel err {rel.max():.4f}"
    assert rel.min() > -0.03, f"sphere min rel err {rel.min():.4f}"
    # 平均は数%(密なので上振れ主体)
    assert 0.0 <= rel.mean() < 0.05, f"sphere mean rel err {rel.mean():.4f}"


# ----------------------------------------------------------------------------
# メッシュ: 平面三角グリッドの閉形式 GT
# ----------------------------------------------------------------------------
def _tri_grid(m: int, h: float = 0.5):
    """m×m の平面三角グリッド(各セルを主対角 (r,c)-(r+1,c+1) で二分)。→ (V, F, vid)。"""
    verts = []
    for r in range(m + 1):
        for c in range(m + 1):
            verts.append([c * h, r * h, 0.0])
    V = np.asarray(verts, float)

    def vid(r, c):
        return r * (m + 1) + c

    faces = []
    for r in range(m):
        for c in range(m):
            a, b = vid(r, c), vid(r, c + 1)
            d, e = vid(r + 1, c), vid(r + 1, c + 1)
            faces.append([a, b, e])   # 共有対角 a-e
            faces.append([a, e, d])
    return V, np.asarray(faces, int), vid


def test_geodesic_mesh_grid_closed_form():
    """平面三角グリッド上でメッシュ測地を閉形式 GT と一致検証。

    GT(厳密):
      - source(0,0)→同一行の端 (0,m): 一直線に並んだエッジ列を辿るので厳密に m*h。
      - source→主対角端 (m,m): 対角エッジ (i,i)-(i+1,i+1) が全て存在 → 厳密に m*√2*h。
      - source 自身は 0、全頂点で d >= Euclid(グラフ最短路の下界)。
    """
    m, h = 8, 0.5
    V, F, vid = _tri_grid(m, h)
    src = vid(0, 0)
    d = G.geodesic_mesh(V, F, src)

    assert d[src] == 0.0
    # 同一行(collinear エッジ列)= 厳密 Euclid
    assert abs(d[vid(0, m)] - m * h) < 1e-9
    assert abs(d[vid(m, 0)] - m * h) < 1e-9
    # 主対角(対角エッジ連鎖)= 厳密 √2
    assert abs(d[vid(m, m)] - m * np.sqrt(2.0) * h) < 1e-9
    # 下界: グラフ最短路は直線距離を下回らない
    eu = np.linalg.norm(V - V[src], axis=1)
    assert np.all(d >= eu - 1e-9)


def test_geodesic_mesh_empty_faces():
    """faces 空 → source のみ 0、他は inf(退化ケースの明示的挙動)。"""
    V = np.random.default_rng(2).random((5, 3))
    d = G.geodesic_mesh(V, np.zeros((0, 3), int), 2)
    assert d[2] == 0.0
    assert np.all(np.isinf(np.delete(d, 2)))


# ----------------------------------------------------------------------------
# Farthest point sampling: 単純ランダムより均等に散らばる
# ----------------------------------------------------------------------------
def test_fps_spreads_more_than_random():
    """測地 FPS の最小ペア距離が、同数の単純ランダム選択より有意に大きい。

    GT 的性質(閉形式ではないが定義から従う不等式): FPS は各段で既選択集合から最遠の点を
      選ぶので選択点は均等に散る → 選択点集合の最小ペア距離(被覆の粗さの下限指標)が
      ランダム抽出の期待値より大きくなる。平面(z=0)で評価するので測地≈Euclid。
    実測: FPS 最小ペア ≈ 0.187 に対しランダム平均 ≈ 0.038(200 試行)。
    """
    rng = np.random.default_rng(7)
    P = rng.random((800, 3))
    P[:, 2] = 0.0
    n = 20

    sel = G.farthest_point_sampling(P, n, k=8)
    assert sel.shape == (n,)
    assert len(np.unique(sel)) == n  # 重複選択しない

    def min_pair(pts):
        dd, _ = cKDTree(pts).query(pts, k=2)
        return float(dd[:, 1].min())

    fps_mp = min_pair(P[sel])
    rnd = [min_pair(P[np.random.default_rng(s).choice(len(P), n, replace=False)])
           for s in range(200)]
    rnd_mean = float(np.mean(rnd))
    rnd_max = float(np.max(rnd))
    # FPS はランダム平均の 2 倍超、かつ 200 試行の最良ランダムより大きい(強い分離)
    assert fps_mp > 2.0 * rnd_mean, f"fps {fps_mp:.4f} vs 2*rnd_mean {2*rnd_mean:.4f}"
    assert fps_mp > rnd_max, f"fps {fps_mp:.4f} vs rnd_max {rnd_max:.4f}"


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-q"]))
