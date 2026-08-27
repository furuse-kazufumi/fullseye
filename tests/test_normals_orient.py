"""normals_orient の GT 検証: 閉曲面の外向き一貫性・平面の半球一貫性・単位性・縮退。

すべて独立 GT(球=中心既知で外向き p−center>0 / 平面=既知法線 / 単位性=解析値 1)で、
実装の再導出には依らない。スケール依存を避けるため主要テストは 2 スケールで確認する。
"""
import numpy as np
import pytest

import normals_orient as no


# ---------- サンプラ(独立 GT の生成) ----------
def _fib_sphere(n, R, center=(0.0, 0.0, 0.0)):
    """Fibonacci 球で半径 R の閉曲面を n 点均一サンプル(外向き = p − center)。"""
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    gold = np.pi * (1 + 5 ** 0.5)
    theta = gold * i
    x = np.sin(phi) * np.cos(theta)
    y = np.sin(phi) * np.sin(theta)
    z = np.cos(phi)
    c = np.asarray(center, float)
    return R * np.stack([x, y, z], axis=1) + c


def _plane(n, L, normal=(0.0, 0.0, 1.0), seed=0):
    """法線 normal・一辺 2L の平面パッチを n 点(z=0 面を回転)。真の法線を併せて返す。"""
    rng = np.random.default_rng(seed)
    xy = rng.uniform(-L, L, size=(n, 2))
    pts = np.stack([xy[:, 0], xy[:, 1], np.zeros(n)], axis=1)
    nrm = np.asarray(normal, float)
    nrm = nrm / np.linalg.norm(nrm)
    # z 軸を nrm へ回す回転(Rodrigues)。nrm=+z ならそのまま。
    z = np.array([0.0, 0.0, 1.0])
    v = np.cross(z, nrm)
    s = np.linalg.norm(v)
    if s < 1e-12:
        R = np.eye(3) if nrm[2] > 0 else np.diag([1.0, -1.0, -1.0])
    else:
        c = np.dot(z, nrm)
        vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
        R = np.eye(3) + vx + vx @ vx * ((1 - c) / (s * s))
    return pts @ R.T, nrm


def _knn_pairs(P, k):
    """kNN の (i,j) ペア(自身除く)。近傍一貫性チェック用。"""
    from scipy.spatial import cKDTree
    _, idx = cKDTree(P).query(P, k=k + 1)
    rows = np.repeat(np.arange(len(P)), k)
    cols = idx[:, 1:].ravel()
    return rows, cols


# ---------- PCA 法線: 単位性・幾何 ----------
def test_pca_normals_are_unit():
    P = _fib_sphere(1200, 2.0)
    N = no.estimate_normals(P, k=20)
    mags = np.linalg.norm(N, axis=1)
    assert np.allclose(mags, 1.0, atol=1e-9)          # 解析 GT: 単位ベクトル


def test_pca_normals_perpendicular_to_plane():
    # 平面上の PCA 法線は面法線に平行(向き未定なので |cos| で判定)。
    P, nrm = _plane(1500, 3.0, normal=(0.0, 0.0, 1.0))
    N = no.estimate_normals(P, k=20)
    cos = np.abs(N @ nrm)
    assert np.median(cos) > 0.999                      # GT: 面法線に平行


def test_pca_unit_at_two_scales():
    for R in (0.05, 5.0):                               # スケール相対性(discipline A)
        N = no.estimate_normals(_fib_sphere(1000, R), k=20)
        assert np.allclose(np.linalg.norm(N, axis=1), 1.0, atol=1e-9)


# ---------- 閉曲面: 全点外向き(GT = p − center) ----------
def test_sphere_all_outward_two_scales():
    for R in (0.05, 5.0):                               # 2 スケールで確認
        center = np.array([1.0, -2.0, 0.5]) * R
        P = _fib_sphere(1600, R, center=center)
        N = no.estimate_oriented_normals(P, k=20)
        outward = P - center                            # 独立 GT: 外向き方向
        frac_out = np.mean(np.sum(N * outward, axis=1) > 0)
        assert frac_out >= 0.99, f"R={R}: outward fraction {frac_out:.4f}"


def test_orientation_actually_does_work():
    # 判別ケース: 向き付け前(PCA 生)は外向き率が中途半端、向き付け後は ~100%。
    center = np.zeros(3)
    P = _fib_sphere(1600, 2.0, center=center)
    raw = no.estimate_normals(P, k=20)
    oriented = no.orient_normals(P, raw, k=20)
    outward = P - center
    frac_raw = np.mean(np.sum(raw * outward, axis=1) > 0)
    frac_ori = np.mean(np.sum(oriented * outward, axis=1) > 0)
    assert frac_raw < 0.95                              # 生は一貫していない
    assert frac_ori >= 0.99                             # 伝播で一貫化
    assert frac_ori > frac_raw + 0.05


def test_neighbor_consistency():
    P = _fib_sphere(1600, 2.0)
    N = no.estimate_oriented_normals(P, k=20)
    r, c = _knn_pairs(P, k=20)
    agree = np.mean(np.sum(N[r] * N[c], axis=1) > 0)
    assert agree >= 0.99, f"neighbor agreement {agree:.4f}"


# ---------- 平面: 同一半球へ一貫化 ----------
def test_plane_consistent_half_space_two_scales():
    for L in (0.1, 10.0):                               # 2 スケール
        P, nrm = _plane(1500, L, normal=(0.3, -0.5, 1.0))
        N = no.estimate_oriented_normals(P, k=20)
        sign = np.sign(N @ nrm)                          # 各点が真法線のどちら側か
        majority = np.sign(np.sum(sign))
        frac = np.mean(sign == majority)
        assert frac >= 0.99, f"L={L}: half-space consistency {frac:.4f}"


def test_seed_dir_controls_global_sign():
    # 判別ケース: seed_dir を反転すると全法線が反転する(種制御が効く)。
    P, nrm = _plane(1500, 3.0, normal=(0.0, 0.0, 1.0))
    Npos = no.estimate_oriented_normals(P, k=20, seed_dir=nrm)
    Nneg = no.estimate_oriented_normals(P, k=20, seed_dir=-nrm)
    assert np.mean((Npos @ nrm) > 0) >= 0.99            # +基準 → 全て +側
    assert np.mean((Nneg @ nrm) < 0) >= 0.99            # −基準 → 全て −側


def test_seed_dir_below_perp_threshold_controls_sign():
    # 回帰(finding [5]): seed_dir の法線成分が _PERP_COS 未満でも、その符号は情報を持つ。
    # 旧実装は seed 点単独の |cos| < _PERP_COS で「退化」とみなし fallback するため、
    # +d と -d が同じ大域符号を返していた(BUG)。伝播後に bulk(成分全点の射影集約)で
    # 符号を決めることで、±d が確実に**逆の大域符号**を返す。
    P, nrm = _plane(1500, 3.0, normal=(0.0, 0.0, 1.0))      # 真法線 +z
    comp = 0.09
    assert comp < no._PERP_COS                              # seed 単独では捨てられる領域
    d = np.array([1.0, 0.0, comp])                          # 法線成分は小さいが符号は明確
    Npos = no.estimate_oriented_normals(P, k=20, seed_dir=d)
    Nneg = no.estimate_oriented_normals(P, k=20, seed_dir=-d)
    assert np.mean((Npos @ nrm) > 0) >= 0.99                # +d(法線成分 +z)→ 全て +側
    assert np.mean((Nneg @ nrm) < 0) >= 0.99                # −d(法線成分 −z)→ 全て −側
    # 明示: ±d は逆の大域符号(旧実装では同符号で FAIL)
    assert np.sign(np.median(Npos @ nrm)) == -np.sign(np.median(Nneg @ nrm))


def test_seed_dir_orthogonal_to_normals_is_fail_closed():
    # 回帰(finding [5]): seed_dir が面内(全法線と直交)= 大域符号は原理的に決まらない。
    # 旧実装は無警告で max 成分 fallback に縮退した。fail-closed で ValueError を要求する。
    P, nrm = _plane(1500, 3.0, normal=(0.0, 0.0, 1.0))      # 真法線 +z
    with pytest.raises(ValueError):
        no.estimate_oriented_normals(P, k=20, seed_dir=[1.0, 0.0, 0.0])  # 面内 x
    with pytest.raises(ValueError):
        no.estimate_oriented_normals(P, k=20, seed_dir=[0.0, 1.0, 0.0])  # 面内 y


def test_seed_dir_on_closed_surface_stays_outward():
    # 閉曲面(球)は seed_dir が平均的に法線と直交(bulk 射影≈0)。大域符号は一意でないので
    # ValueError で落とさず、最突出点=外向き基準の向き付けを保持する(退化と誤判定しない)。
    center = np.array([0.5, -1.0, 2.0])
    P = _fib_sphere(1600, 2.0, center=center)
    outward = P - center
    for sd in ([0.0, 0.0, 1.0], [1.0, 2.0, -1.0]):
        N = no.estimate_oriented_normals(P, k=20, seed_dir=sd)  # raise しない
        frac_out = np.mean(np.sum(N * outward, axis=1) > 0)
        assert frac_out >= 0.99, f"seed_dir={sd}: outward fraction {frac_out:.4f}"


# ---------- end-to-end: shape_index の凹/凸符号(wave7 監査 [2] のギャップ) ----------
def test_shape_index_convex_sign_with_oriented_normals():
    import curvature3d
    P = _fib_sphere(2000, 2.0)                           # 凸球(cap)
    N = no.estimate_oriented_normals(P, k=25)
    s = curvature3d.shape_index(P, k=25, normals=N)
    # 独立 GT: 凸球の shape index = +1。外向き法線を渡せば正しく凸符号が出る。
    assert np.median(s) > 0.9, f"median shape_index {np.median(s):.3f}"
    assert np.mean(s > 0.5) >= 0.95


# ---------- 縮退: fail-closed ----------
def test_degenerate_too_few_points():
    P = _fib_sphere(5, 1.0)                              # 点数 < k
    with pytest.raises(ValueError):
        no.estimate_normals(P, k=20)
    with pytest.raises(ValueError):
        no.estimate_oriented_normals(P, k=20)
    N = np.tile([0.0, 0.0, 1.0], (5, 1))
    with pytest.raises(ValueError):
        no.orient_normals(P, N, k=20)


def test_input_validation():
    with pytest.raises(ValueError):
        no.estimate_normals(np.zeros((10, 2)), k=3)     # 形状不正
    with pytest.raises(ValueError):
        no.estimate_normals(np.full((30, 3), np.nan), k=5)  # 非有限
    P = _fib_sphere(50, 1.0)
    with pytest.raises(ValueError):
        no.orient_normals(P, np.zeros((50, 3)), k=10)   # ゼロ長法線 → fail-closed
    with pytest.raises(ValueError):
        no.orient_normals(P, np.zeros((49, 3)), k=10)   # 法線数不一致
    with pytest.raises(ValueError):
        no.estimate_oriented_normals(P, k=10, seed_dir=[0, 0, 0])  # ゼロ seed_dir
