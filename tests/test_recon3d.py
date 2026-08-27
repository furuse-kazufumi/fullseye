"""recon3d(点群 → 表面再構成)テスト。

ground-truth 検証(既知形状の幾何で確かめる):
    - poisson_lite(占有): 球面サンプル点 → 再構成頂点が半径 R の球面近傍に載る
      (|dist(v,center) − R| の中央値が R の 10% 以内)、頂点/面が非空で面 index が有効。
    - poisson_lite(法線/winding): 向き付き球面点 → 同様に球面近傍(より密着)。
    - alpha_shape_boundary: 表面殻+内部コアの中実球から境界点を取ると、境界点は球面殻に
      集中し内部コア点はほとんど選ばれない。
    - alpha_shape_mesh: (V,3)/(F,3) を返し面 index が範囲内。
    - estimate_alpha: 正の有限値。

numpy in / numpy out。scipy・skimage が無ければ skip。
"""
import numpy as np
import pytest

pytest.importorskip("scipy")
pytest.importorskip("skimage")

import recon3d as R  # noqa: E402


# --------------------------------------------------------------------------- #
# 入力生成ヘルパ(すべて既知 center/R で幾何検証できる形)                     #
# --------------------------------------------------------------------------- #
def _fib_sphere(n, radius, center):
    """フィボナッチ螺旋で球面 (n,3) を一様サンプル。外向き単位法線も返す。"""
    i = np.arange(n) + 0.5
    phi = np.arccos(1.0 - 2.0 * i / n)
    gold = np.pi * (1.0 + 5.0 ** 0.5)
    theta = gold * i
    dirs = np.stack([np.sin(phi) * np.cos(theta),
                     np.sin(phi) * np.sin(theta),
                     np.cos(phi)], axis=1)
    return np.asarray(center) + radius * dirs, dirs


def _solid_ball(n, radius, center, seed):
    """半径 radius の中実球を一様サンプル (n,3)。"""
    rng = np.random.default_rng(seed)
    u = rng.normal(size=(n, 3))
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    rad = radius * rng.random(n) ** (1.0 / 3.0)
    return np.asarray(center) + u * rad[:, None]


CENTER = np.array([0.2, 0.1, -0.3])
RADIUS = 1.0


def _count_radial_shells(verts, center, bins=40, min_frac=0.005):
    """再構成頂点の半径分布から**同心殻の本数**を数える。

    中心からの半径ヒストグラムで、頂点が十分載っている bin(全体の min_frac 超)の
    連続した塊の数を返す。単一殻なら 1、同心二重殻(内側/外側に分かれ radius に空白帯が
    できる)なら 2 以上。二重殻バグ([8])を捕捉するための構造的判定。
    """
    r = np.linalg.norm(np.asarray(verts) - np.asarray(center), axis=1)
    hist, _ = np.histogram(r, bins=bins)
    occupied = hist > (min_frac * len(r))
    padded = np.concatenate([[0], occupied.astype(int), [0]])
    return int((np.diff(padded) == 1).sum())


# --------------------------------------------------------------------------- #
# poisson_lite: 占有モード(球面サンプル → 球面近傍メッシュ)                  #
# --------------------------------------------------------------------------- #
def test_poisson_lite_occupancy_sphere_geometry():
    pts, _ = _fib_sphere(4000, RADIUS, CENTER)
    verts, faces = R.poisson_lite(pts, size=64, sigma=1.5, iso=0.5)

    # 非空・形・型
    assert verts.ndim == 2 and verts.shape[1] == 3
    assert faces.ndim == 2 and faces.shape[1] == 3
    assert len(verts) > 0 and len(faces) > 0

    # 面 index が有効頂点範囲内
    assert faces.min() >= 0
    assert faces.max() < len(verts)

    # 頂点が球面近傍(残差中央値が R の 10% 以内)
    resid = np.abs(np.linalg.norm(verts - CENTER, axis=1) - RADIUS)
    assert np.median(resid) < 0.10 * RADIUS
    # 大多数(90 パーセンタイル)も明確に球面付近
    assert np.percentile(resid, 90) < 0.15 * RADIUS


def test_poisson_lite_normals_winding_sphere_geometry():
    pts, normals = _fib_sphere(4000, RADIUS, CENTER)
    verts, faces = R.poisson_lite(pts, size=64, sigma=1.5, iso=0.5, normals=normals)

    assert len(verts) > 0 and len(faces) > 0
    assert faces.max() < len(verts) and faces.min() >= 0

    resid = np.abs(np.linalg.norm(verts - CENTER, axis=1) - RADIUS)
    # winding(内外指標)は表面のみ点群でも内部を埋めるため、より密着した単一殻になる
    assert np.median(resid) < 0.10 * RADIUS


def test_poisson_lite_rejects_too_few_points():
    with pytest.raises(ValueError):
        R.poisson_lite(np.zeros((3, 3)))


def test_poisson_lite_rejects_bad_shape():
    with pytest.raises(ValueError):
        R.poisson_lite(np.zeros((10, 2)))


def test_poisson_lite_normals_shape_mismatch():
    pts, _ = _fib_sphere(500, RADIUS, CENTER)
    with pytest.raises(ValueError):
        R.poisson_lite(pts, normals=np.zeros((499, 3)))


# --------------------------------------------------------------------------- #
# alpha_shape_boundary: 中実球(殻+コア)→ 境界は殻に集中                     #
# --------------------------------------------------------------------------- #
def _shell_and_core():
    """密な表面殻 + まばらな内部コアの中実球。ラベル is_surf を返す。"""
    n_surf = 2500
    surf, _ = _fib_sphere(n_surf, RADIUS, CENTER)
    core = _solid_ball(1200, 0.6 * RADIUS, CENTER, seed=7)
    pts = np.vstack([surf, core])
    is_surf = np.zeros(len(pts), dtype=bool)
    is_surf[:n_surf] = True
    return pts, is_surf, n_surf


def test_alpha_shape_boundary_selects_surface_not_interior():
    pts, is_surf, n_surf = _shell_and_core()
    # estimate の半分 = 半径しきい値 1/alpha を約 2 倍広げ、凸な球殻を素直に張らせる
    alpha = R.estimate_alpha(pts) * 0.5
    bidx = R.alpha_shape_boundary(pts, alpha)

    assert bidx.ndim == 1
    assert 0 < len(bidx) < len(pts)          # 一部だけが境界
    assert bidx.max() < len(pts)             # 有効 index

    # 境界点は球面殻に集中(半径中央値が R 近傍)
    br = np.linalg.norm(pts[bidx] - CENTER, axis=1)
    assert np.median(br) > 0.85 * RADIUS

    # 境界点の大多数は表面点、内部コア点はほとんど選ばれない
    frac_surface_in_boundary = is_surf[bidx].mean()
    assert frac_surface_in_boundary > 0.85

    core_selected = np.mean(np.isin(np.arange(n_surf, len(pts)), bidx))
    assert core_selected < 0.15

    # 境界点半径は全体より明確に外側へ偏る
    all_r = np.linalg.norm(pts - CENTER, axis=1)
    assert np.median(br) > np.median(all_r)


def test_alpha_shape_boundary_empty_when_alpha_too_large():
    # alpha を極端に大きくすると 1/alpha が微小になり、残る四面体が無く空になる
    pts = _solid_ball(500, RADIUS, CENTER, seed=3)
    bidx = R.alpha_shape_boundary(pts, alpha=1e6)
    assert bidx.shape == (0,)


def test_alpha_shape_boundary_rejects_bad_alpha():
    pts = _solid_ball(100, RADIUS, CENTER, seed=1)
    with pytest.raises(ValueError):
        R.alpha_shape_boundary(pts, alpha=0.0)


# --------------------------------------------------------------------------- #
# alpha_shape_mesh: (V,3)/(F,3)・面 index 範囲内                              #
# --------------------------------------------------------------------------- #
def test_alpha_shape_mesh_shapes_and_indices():
    pts, _, _ = _shell_and_core()
    alpha = R.estimate_alpha(pts) * 0.5
    verts, faces = R.alpha_shape_mesh(pts, alpha)

    assert verts.ndim == 2 and verts.shape[1] == 3
    assert faces.ndim == 2 and faces.shape[1] == 3
    assert len(verts) > 0 and len(faces) > 0

    # 面 index が頂点範囲内
    assert faces.min() >= 0
    assert faces.max() < len(verts)

    # メッシュ頂点(境界に使われた点)は球面殻近傍
    r = np.linalg.norm(verts - CENTER, axis=1)
    assert np.median(r) > 0.85 * RADIUS


def test_alpha_shape_mesh_empty_graceful():
    pts = _solid_ball(500, RADIUS, CENTER, seed=5)
    verts, faces = R.alpha_shape_mesh(pts, alpha=1e6)
    assert verts.shape == (0, 3)
    assert faces.shape == (0, 3)


# --------------------------------------------------------------------------- #
# estimate_alpha: 正の有限値                                                  #
# --------------------------------------------------------------------------- #
def test_estimate_alpha_positive_finite():
    pts, _ = _fib_sphere(2000, RADIUS, CENTER)
    alpha = R.estimate_alpha(pts)
    assert np.isfinite(alpha)
    assert alpha > 0.0


def test_estimate_alpha_scales_with_spacing():
    # 点を 2 倍に広げると間隔 2 倍 → 推奨 alpha は約半分(1/alpha ∝ 間隔)
    pts = _solid_ball(1500, RADIUS, CENTER, seed=2)
    a1 = R.estimate_alpha(pts)
    a2 = R.estimate_alpha(pts * 2.0)
    assert np.isfinite(a1) and np.isfinite(a2)
    assert a2 == pytest.approx(a1 / 2.0, rel=0.1)


def test_estimate_alpha_rejects_too_few_points():
    with pytest.raises(ValueError):
        R.estimate_alpha(np.zeros((1, 3)))
