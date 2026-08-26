"""descriptors3d — 大域形状記述子の ground-truth 検証。

不変性(回転・平行移動・スケール)と識別性(球 / 立方体 / 棒)を数値で確認する。
点群は決定論的な rng で生成し、記述子の乱択は seed 固定で再現する。
"""
import numpy as np
import pytest

# 本体は numpy のみで動くが、scipy は fullseye の 3D スイート共通前提なので合わせる。
pytest.importorskip("numpy")

import descriptors3d as D  # noqa: E402


# --------------------------------------------------------------------------- #
# 形状ジェネレータ(いずれも体積を一様に充填した点群)                          #
# --------------------------------------------------------------------------- #
def _sphere(n=4000, r=1.0, seed=1):
    """半径 r の球の内部を一様充填した点群 (n,3)。"""
    rng = np.random.default_rng(seed)
    pts = []
    while len(pts) < n:
        c = rng.uniform(-r, r, size=(n, 3))
        c = c[np.einsum("ij,ij->i", c, c) <= r * r]
        pts.extend(c.tolist())
    return np.asarray(pts[:n], dtype=np.float64)


def _cube(n=4000, s=1.0, seed=2):
    """一辺 2s の立方体を一様充填した点群 (n,3)。"""
    rng = np.random.default_rng(seed)
    return rng.uniform(-s, s, size=(n, 3))


def _rod(n=4000, length=6.0, thick=0.15, seed=3):
    """細長い棒(x 方向に長い直方体)を一様充填した点群 (n,3)。"""
    rng = np.random.default_rng(seed)
    x = rng.uniform(-length, length, size=n)
    y = rng.uniform(-thick, thick, size=n)
    z = rng.uniform(-thick, thick, size=n)
    return np.stack([x, y, z], axis=1)


def _rot_matrix(seed=7):
    """QR 分解で作る決定論的な回転行列(det=+1 に補正)。"""
    rng = np.random.default_rng(seed)
    q, r = np.linalg.qr(rng.standard_normal((3, 3)))
    q *= np.sign(np.diag(r))          # QR の符号任意性を除去
    if np.linalg.det(q) < 0:
        q[:, 0] = -q[:, 0]            # 反射を回転へ
    return q


# --------------------------------------------------------------------------- #
# 1. 回転不変性                                                                #
# --------------------------------------------------------------------------- #
def test_rotation_invariance_describe():
    """既知回転を掛けても describe / shape_distance がほぼ 0(< 0.05)。"""
    pts = _cube(n=3000, seed=11)
    R = _rot_matrix(seed=7)
    rot = pts @ R.T
    da = D.describe(pts, bins=64, seed=0)
    db = D.describe(rot, bins=64, seed=0)
    dist = D.shape_distance(da, db)
    assert dist < 0.05, f"回転で記述子が動きすぎ: {dist}"


def test_translation_invariance():
    """平行移動しても記述子は不変(距離・角度・共分散すべて並進不変)。"""
    pts = _sphere(n=3000, seed=12)
    shifted = pts + np.array([13.0, -7.5, 4.2])
    da = D.describe(pts, seed=0)
    db = D.describe(shifted, seed=0)
    assert D.shape_distance(da, db) < 1e-9


# --------------------------------------------------------------------------- #
# 2. スケール不変性(D2)                                                       #
# --------------------------------------------------------------------------- #
def test_scale_invariance_d2():
    """定数倍しても D2 記述子はほぼ不変(平均距離で正規化しているため)。"""
    pts = _sphere(n=3000, seed=13)
    h1 = D.d2_distribution(pts, seed=0)
    h2 = D.d2_distribution(pts * 4.7, seed=0)
    # 同一点群を一様スケールしただけ・同 seed なので厳密一致するはず。
    assert np.allclose(h1, h2, atol=1e-12)


def test_scale_invariance_describe():
    """describe 全体もスケールでほぼ不変。"""
    pts = _cube(n=3000, seed=14)
    da = D.describe(pts, seed=0)
    db = D.describe(pts * 0.31, seed=0)
    assert D.shape_distance(da, db) < 1e-9


# --------------------------------------------------------------------------- #
# 3. 識別性(同形状 < 異形状 を厳密に)                                         #
# --------------------------------------------------------------------------- #
def test_discrimination_sphere_cube_rod():
    """shape_distance(同形状) < shape_distance(異形状) をすべての組で厳密に。"""
    sphere_a = D.describe(_sphere(n=4000, seed=101), seed=0)
    sphere_b = D.describe(_sphere(n=4000, seed=202), seed=0)   # 別サンプルの同形状
    cube = D.describe(_cube(n=4000, seed=303), seed=0)
    rod = D.describe(_rod(n=4000, seed=404), seed=0)

    within = D.shape_distance(sphere_a, sphere_b)             # 同形状(球 vs 球)
    d_sphere_cube = D.shape_distance(sphere_a, cube)
    d_sphere_rod = D.shape_distance(sphere_a, rod)
    d_cube_rod = D.shape_distance(cube, rod)

    assert within < d_sphere_cube, (within, d_sphere_cube)
    assert within < d_sphere_rod, (within, d_sphere_rod)
    assert within < d_cube_rod, (within, d_cube_rod)
    # 棒は等方形状(球・立方体)から最も遠いはず。
    assert d_sphere_rod > d_sphere_cube


def test_discrimination_within_cube_and_rod():
    """立方体・棒それぞれも「同形状同士 < 異形状」を満たす。"""
    cube_a = D.describe(_cube(n=4000, seed=11), seed=0)
    cube_b = D.describe(_cube(n=4000, seed=22), seed=0)
    rod_a = D.describe(_rod(n=4000, seed=33), seed=0)
    rod_b = D.describe(_rod(n=4000, seed=44), seed=0)

    assert D.shape_distance(cube_a, cube_b) < D.shape_distance(cube_a, rod_a)
    assert D.shape_distance(rod_a, rod_b) < D.shape_distance(rod_a, cube_a)


# --------------------------------------------------------------------------- #
# 4. 決定論                                                                    #
# --------------------------------------------------------------------------- #
def test_determinism_same_seed():
    """同 seed で 2 回呼ぶと厳密に同一。"""
    pts = _cube(n=2000, seed=15)
    assert np.array_equal(D.d2_distribution(pts, seed=5), D.d2_distribution(pts, seed=5))
    assert np.array_equal(D.a3_distribution(pts, seed=5), D.a3_distribution(pts, seed=5))
    assert np.array_equal(D.describe(pts, seed=5), D.describe(pts, seed=5))


def test_different_seed_differs():
    """異なる seed では(乱択が変わるので)一般に異なる。"""
    pts = _cube(n=2000, seed=16)
    h1 = D.d2_distribution(pts, seed=1)
    h2 = D.d2_distribution(pts, seed=2)
    assert not np.array_equal(h1, h2)


# --------------------------------------------------------------------------- #
# 5. extent_signature の意味                                                   #
# --------------------------------------------------------------------------- #
def test_extent_sphere_isotropic():
    """球は 3 軸がほぼ等値(各成分が 1/3 近傍)。"""
    ext = D.extent_signature(_sphere(n=5000, seed=21))
    assert ext.shape == (3,)
    assert np.isclose(ext.sum(), 1.0)
    assert np.all(np.abs(ext - 1.0 / 3.0) < 0.05), ext


def test_extent_rod_dominant_axis():
    """棒は 1 軸が突出(最大成分 > 0.8、最小成分 < 0.1)。"""
    ext = D.extent_signature(_rod(n=5000, seed=22))
    assert ext[0] > 0.8, ext
    assert ext[2] < 0.1, ext
    # 降順で返る契約。
    assert ext[0] >= ext[1] >= ext[2]


def test_extent_rotation_invariance():
    """extent は既知回転で不変。"""
    pts = _rod(n=4000, seed=23)
    R = _rot_matrix(seed=9)
    e1 = D.extent_signature(pts)
    e2 = D.extent_signature(pts @ R.T)
    assert np.allclose(e1, e2, atol=1e-6)


# --------------------------------------------------------------------------- #
# 6. 形状・正規化・エラー処理                                                  #
# --------------------------------------------------------------------------- #
def test_histograms_shape_and_normalization():
    """D2 / A3 は (bins,)・総和 1・非負。"""
    pts = _sphere(n=2000, seed=31)
    for bins in (16, 64, 100):
        h2 = D.d2_distribution(pts, bins=bins, seed=0)
        ha = D.a3_distribution(pts, bins=bins, seed=0)
        assert h2.shape == (bins,) and ha.shape == (bins,)
        assert np.isclose(h2.sum(), 1.0) and np.isclose(ha.sum(), 1.0)
        assert np.all(h2 >= 0) and np.all(ha >= 0)


def test_describe_length():
    """describe の長さは 2*bins + 3。"""
    pts = _cube(n=1500, seed=32)
    for bins in (16, 64):
        assert D.describe(pts, bins=bins, seed=0).shape == (2 * bins + 3,)


def test_shape_distance_metrics():
    """L1 は非負・自己距離 0、JSD は [0,1] 有界・自己距離 0。"""
    a = D.describe(_sphere(n=2000, seed=41), seed=0)
    b = D.describe(_rod(n=2000, seed=42), seed=0)
    assert D.shape_distance(a, a, metric="l1") == 0.0
    assert D.shape_distance(a, a, metric="jsd") < 1e-9
    jsd = D.shape_distance(a, b, metric="jsd")
    assert 0.0 <= jsd <= 1.0
    assert D.shape_distance(a, b, metric="l1") > 0.0


def test_point_shortage_raises():
    """点数不足・形状不正は明示的な ValueError。"""
    with pytest.raises(ValueError):
        D.d2_distribution(np.zeros((1, 3)))           # N<2
    with pytest.raises(ValueError):
        D.a3_distribution(np.zeros((2, 3)))           # N<3
    with pytest.raises(ValueError):
        D.extent_signature(np.zeros((2, 3)))          # N<3
    with pytest.raises(ValueError):
        D.d2_distribution(np.zeros((10, 2)))          # (N,2) 不正
    with pytest.raises(ValueError):
        D.describe(np.array([[np.nan, 0, 0], [1, 2, 3], [4, 5, 6]]))  # 非有限


def test_shape_distance_length_mismatch_raises():
    """長さ不一致の記述子比較は ValueError。"""
    with pytest.raises(ValueError):
        D.shape_distance(np.zeros(5), np.zeros(6))


def test_degenerate_all_identical_points():
    """全点同一(退化)でも例外を出さず定義済みの値を返す。"""
    pts = np.ones((20, 3))
    ext = D.extent_signature(pts)
    assert np.allclose(ext, 1.0 / 3.0)                # 等方フォールバック
    h = D.d2_distribution(pts, seed=0)
    assert np.isclose(h.sum(), 1.0)                   # bin0 に質量
    assert h[0] == 1.0
