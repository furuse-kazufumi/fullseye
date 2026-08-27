"""edges3d — 3D エッジ抽出の ground-truth 検証。

既知形状(中実立方体・階段状ステップ・分離した箱)のエッジ位置を幾何的に検証する。
NMS の細線化・境界再現率・LoG ゼロ交差・連結ラベリング・点群化を実測値で確認。
"""
import numpy as np
import pytest

pytest.importorskip("scipy")
from scipy.ndimage import binary_dilation, binary_erosion  # noqa: E402

import edges3d as E  # noqa: E402


# --------------------------------------------------------------------------- #
# fixtures                                                                     #
# --------------------------------------------------------------------------- #
def _solid_cube(n=32, lo=8, hi=24, val=1.0):
    """(n,n,n) の中に中実立方体 [lo:hi]^3 を置いたグレー voxel。"""
    v = np.zeros((n, n, n), dtype=np.float64)
    v[lo:hi, lo:hi, lo:hi] = val
    return v


def _canny_auto(v, sigma=1.0, hi_frac=0.3, lo_frac=0.1):
    """gmag スケールに応じた閾値で canny3d を掛けるヘルパ。"""
    gmag, _ = E.gradient3d(v, sigma=sigma)
    m = gmag.max()
    return E.canny3d(v, lo_frac * m, hi_frac * m, sigma=sigma), gmag, lo_frac * m


# --------------------------------------------------------------------------- #
# 1. gradient3d の形状・向き                                                   #
# --------------------------------------------------------------------------- #
def test_gradient3d_shapes_and_direction():
    """gmag=(D,H,W), gvec=(D,H,W,3)。軸方向ランプで勾配がその軸だけに立つ。"""
    D, H, W = 10, 12, 14
    zz, yy, xx = np.indices((D, H, W), dtype=float)
    vol = 2.0 * xx  # axis2(width)方向のみ勾配
    gmag, gvec = E.gradient3d(vol, sigma=0.0)
    assert gmag.shape == (D, H, W)
    assert gvec.shape == (D, H, W, 3)
    inner = (slice(1, -1),) * 3
    assert np.allclose(gvec[inner][..., 2], 2.0)          # ∂/∂axis2 = 2
    assert np.allclose(gvec[inner][..., 0], 0.0, atol=1e-9)
    assert np.allclose(gvec[inner][..., 1], 0.0, atol=1e-9)
    assert np.allclose(gmag[inner], 2.0)


# --------------------------------------------------------------------------- #
# 2. canny3d: 境界に集中 / 内部は非エッジ / 高い再現率                          #
# --------------------------------------------------------------------------- #
def test_canny3d_edges_on_faces_high_recall():
    """中実立方体で、エッジは表面シェルに集中し内部はエッジ無し(再現率が高い)。"""
    v = _solid_cube()
    edges, _, _ = _canny_auto(v)
    block = v > 0.5
    surface = block & ~binary_erosion(block)  # 1 voxel 内側シェル(真の境界)

    # 再現率: 表面シェルの各 voxel の近傍(<=2)にエッジがあるか。
    covered = surface & binary_dilation(edges, iterations=2)
    recall = covered.sum() / surface.sum()
    assert recall > 0.9, f"境界再現率が低い: {recall:.3f}"

    # 内部: 深い内側(3 voxel 侵食)にはエッジがほぼ無い。
    interior = binary_erosion(block, iterations=3)
    assert interior.sum() > 0
    assert edges[interior].mean() < 0.01, f"内部エッジ率={edges[interior].mean():.4f}"

    # エッジは全て表面近傍(<=2)に位置する = 境界に集中。
    near_surf = binary_dilation(surface, iterations=2)
    assert edges[near_surf].sum() / edges.sum() > 0.95


def test_canny3d_edges_are_thin():
    """NMS により境界法線方向のエッジ厚が概ね 1 voxel(厚いバンドより有意に少ない)。"""
    v = _solid_cube()
    edges, gmag, low = _canny_auto(v)
    thick = gmag >= low  # NMS 前の「厚いバンド」

    # NMS 済みエッジ数は厚いバンドより有意に少ない(細線化されている)。
    ratio = edges.sum() / thick.sum()
    assert ratio < 0.5, f"NMS が細線化していない: edges/thick={ratio:.3f}"

    # 面中心を貫く法線ラインは、対向 2 面 = ちょうど 2 voxel だけ(各面 1 voxel)。
    line_x = edges[16, 16, :]
    assert line_x.sum() == 2, f"x 法線ライン上のエッジ数={int(line_x.sum())}(対向 2 面で 1 voxel ずつ)"
    pos = np.where(line_x)[0]
    assert pos[1] - pos[0] > 10, "2 つのエッジは対向面(離れている)であるべき"

    # 別軸でも同様に 1 voxel/面。
    assert edges[16, :, 16].sum() == 2
    assert edges[:, 16, 16].sum() == 2


# --------------------------------------------------------------------------- #
# 3. log_zero_crossings: 階段状エッジで境界に反応                              #
# --------------------------------------------------------------------------- #
def test_log_zero_crossings_step():
    """半空間ステップ(x>=12 で 1)で、ゼロ交差が境界 x≈11.5 に反応し平坦部には出ない。"""
    v = np.zeros((24, 24, 24), dtype=np.float64)
    v[:, :, 12:] = 1.0
    zc = E.log_zero_crossings(v, sigma=1.5)

    assert zc.any(), "ステップ境界でゼロ交差が検出されるべき"
    xs = np.argwhere(zc)[:, 2]
    # 全てのゼロ交差が境界(x=11.5)近傍に集中。
    assert np.median(np.abs(xs - 11.5)) < 2.0
    assert zc[:, :, 10:14].sum() > 0, "境界帯にゼロ交差があるべき"
    # 境界から遠い平坦部にはゼロ交差が出ない(数値ノイズを rel_thresh で抑制)。
    assert zc[:, :, :6].sum() == 0
    assert zc[:, :, 18:].sum() == 0


def test_log_zero_crossings_flat_is_empty():
    """完全平坦なら LoG ゼロ交差なし。"""
    v = np.full((16, 16, 16), 0.5, dtype=np.float64)
    zc = E.log_zero_crossings(v, sigma=1.5)
    assert not zc.any()


def _tanh_step(center, n=33, axis=2):
    """axis 方向に tanh(x-center) で符号反転する SDF 風の場(n,n,n)。"""
    coords = np.indices((n, n, n), dtype=np.float64)
    return np.tanh(coords[axis] - center)


def test_log_zero_crossings_on_grid_edge_not_dropped():
    """格子整列面(LoG がちょうど格子点上で 0)でも取りこぼさない。

    対称ステップの中心を格子点 x=16 に置くと LoG は x=16 で厳密に 0 になり、隣接ペアの
    符号積は常に 0(a*b<0 が成立しない)。旧実装はこの真のエッジを丸ごと落としていた。
    格子間 x=16.5 と同程度に検出され、しかも交差面は x=16 の 1 voxel 厚であること。
    """
    on_grid = E.log_zero_crossings(_tanh_step(16.0), sigma=1.5)
    off_grid = E.log_zero_crossings(_tanh_step(16.5), sigma=1.5)

    assert on_grid.any(), "格子整列エッジ(x=16)を落としてはならない(旧挙動=0)"
    # off-grid と同程度の検出量(planar な交差面なので概ね一致するはず)。
    assert on_grid.sum() >= 0.9 * off_grid.sum(), (
        f"on-grid={int(on_grid.sum())} が off-grid={int(off_grid.sum())} に比べ過少"
    )
    # 交差は格子点 x=16 の 1 voxel 面に集中(厚くならない)。
    xs = np.unique(np.argwhere(on_grid)[:, 2])
    assert xs.tolist() == [16], f"格子整列交差は x=16 の 1 voxel 面のはず: {xs.tolist()}"


def test_log_zero_crossings_constant_zero_no_false_positive():
    """定数ゼロ場は交差ではない — L==0 を含める修正で誤検出しないこと。"""
    v = np.zeros((16, 16, 16), dtype=np.float64)
    zc = E.log_zero_crossings(v, sigma=1.5)
    assert not zc.any(), "定数ゼロ場を交差として立ててはならない"


# --------------------------------------------------------------------------- #
# 4. link_edges: 分離した 2 箱で n>=2                                          #
# --------------------------------------------------------------------------- #
def test_link_edges_two_boxes():
    """y 方向に分離した 2 つの立方体 → 26 連結ラベルが 2 成分以上。"""
    v = np.zeros((20, 40, 20), dtype=np.float64)
    v[5:15, 3:13, 5:15] = 1.0    # box 1
    v[5:15, 27:37, 5:15] = 1.0   # box 2(y 方向にギャップ)
    edges, _, _ = _canny_auto(v)
    labels, n = E.link_edges(edges)
    assert n >= 2, f"分離した 2 箱で n>=2 のはず: n={n}"
    assert labels.shape == v.shape
    assert labels.max() == n

    # 各箱の領域にエッジ成分が存在する(片方に寄っていない)。
    assert edges[:, :20, :].any() and edges[:, 20:, :].any()


def test_link_edges_single_component():
    """単純な連結ブロブは 1 成分。"""
    mask = np.zeros((10, 10, 10), dtype=bool)
    mask[3:7, 3:7, 3:7] = True
    labels, n = E.link_edges(mask)
    assert n == 1


def test_link_edges_26_connectivity():
    """対角(面を共有しない角接触)でも 26 連結で 1 成分になる。"""
    mask = np.zeros((5, 5, 5), dtype=bool)
    mask[1, 1, 1] = True
    mask[2, 2, 2] = True  # 角のみ接触(6 連結なら別成分)
    _, n = E.link_edges(mask)
    assert n == 1


# --------------------------------------------------------------------------- #
# 5. edge_points: (M,3) で全点が有効範囲内                                     #
# --------------------------------------------------------------------------- #
def test_edge_points_shape_and_bounds():
    """edge_points が (M,3) を返し、全点が volume の範囲内。"""
    v = _solid_cube()
    edges, _, _ = _canny_auto(v)
    pts = E.edge_points(edges)
    assert pts.ndim == 2 and pts.shape[1] == 3
    assert pts.shape[0] == int(edges.sum())
    D, H, W = edges.shape
    for axis, hi in enumerate((D, H, W)):
        assert (pts[:, axis] >= 0).all()
        assert (pts[:, axis] < hi).all()
    # 座標 → mask の往復整合。
    idx = pts.astype(int)
    assert edges[idx[:, 0], idx[:, 1], idx[:, 2]].all()


def test_edge_points_empty():
    """エッジ無しなら (0,3)。"""
    pts = E.edge_points(np.zeros((6, 6, 6), dtype=bool))
    assert pts.shape == (0, 3)


# --------------------------------------------------------------------------- #
# 6. 入力検証・エラー処理                                                      #
# --------------------------------------------------------------------------- #
def test_input_validation():
    """次元不正・閾値不正・NaN を明示的に拒否する。"""
    with pytest.raises(ValueError):
        E.gradient3d(np.zeros((4, 4)))          # 2D は不可
    with pytest.raises(ValueError):
        E.gradient3d(np.zeros((4, 4, 4)), sigma=-1.0)
    with pytest.raises(ValueError):
        E.canny3d(np.zeros((4, 4, 4)), low=0.5, high=0.2, sigma=1.0)  # low>high
    with pytest.raises(ValueError):
        E.canny3d(np.zeros((4, 4, 4)), low=0.1, high=0.0, sigma=1.0)  # high<=0
    with pytest.raises(ValueError):
        E.log_zero_crossings(np.zeros((4, 4, 4)), sigma=0.0)          # sigma<=0
    bad = np.zeros((4, 4, 4)); bad[0, 0, 0] = np.nan
    with pytest.raises(ValueError):
        E.gradient3d(bad)


def test_canny3d_high_threshold_empty():
    """max 勾配を超える high では種が無く空になる(ヒステリシスの健全性)。"""
    v = _solid_cube()
    gmag, _ = E.gradient3d(v, sigma=1.0)
    edges = E.canny3d(v, low=0.1 * gmag.max(), high=1.0e9, sigma=1.0)
    assert not edges.any()
