"""medial(3D medial surface / 3D 骨格)テスト。

TRIZ 原理 #17「線→面」: 2D スケルトンの 3D 版。既知形状(中実球 / 中実円柱 / 棒 / Y 字)で
幾何的な ground-truth を検証する。

不変条件:
- 中実球 -> medial の最大半径点が球中心(<=2 voxel)、最大半径 ≈ 球半径。
- 中実円柱 -> medial / 骨格が軸に沿う線状(medial 点が軸線近傍に集中)。
- topology_signature -> 棒(端点2・分岐0)/ Y 字(端点3・分岐1)で期待通り。
- medial_match -> 同形状同士 > 異形状同士。
- 入力検証(fail-closed): 3D 以外・空配列・負の min_radius は ValueError。

EDT リッジ = 26 近傍の局所極大。塊は点、管は線、板は面に自然に潰れる。
"""
import numpy as np
import pytest

pytest.importorskip("skimage")           # skeletonize(method='lee') に必須

import medial


# ---------------------------------------------------------------- 形状ジェネレータ
def solid_ball(size, r, center=None):
    """中実球の bool voxel。"""
    zz, yy, xx = np.mgrid[0:size, 0:size, 0:size]
    if center is None:
        center = ((size - 1) / 2.0,) * 3
    cz, cy, cx = center
    return ((zz - cz) ** 2 + (yy - cy) ** 2 + (xx - cx) ** 2) <= r * r


def solid_cylinder(size, r, axis_margin=4):
    """z 軸に沿う中実円柱の bool voxel(両端に margin)。"""
    zz, yy, xx = np.mgrid[0:size, 0:size, 0:size]
    cy = cx = (size - 1) / 2.0
    radial = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    return (radial <= r) & (zz >= axis_margin) & (zz <= size - 1 - axis_margin)


def straight_rod(size, length, axis=0):
    """1 voxel 幅の直線骨格(端点2・分岐0)。"""
    sk = np.zeros((size, size, size), dtype=bool)
    c = size // 2
    for k in range(length):
        p = [c, c, c]
        p[axis] = c - length // 2 + k
        sk[tuple(p)] = True
    return sk


def y_skeleton(size, arm_len):
    """3 本の角対角枝が 1 点で交わる Y 字骨格(端点3・分岐1)。

    角方向 (±1,±1,±1) のうち互いに 2 座標以上異なる 3 方向を選ぶと、交点近傍で枝どうしが
    26 近傍で接触せず(チェビシェフ距離 2)、交点のみ次数 3 になる。
    """
    sk = np.zeros((size, size, size), dtype=bool)
    c = size // 2
    sk[c, c, c] = True
    for dz, dy, dx in [(1, 1, 1), (1, -1, -1), (-1, 1, -1)]:
        for k in range(1, arm_len + 1):
            sk[c + dz * k, c + dy * k, c + dx * k] = True
    return sk


# ---------------------------------------------------------------- 中実球
def test_ball_medial_max_radius_at_center():
    """中実球 -> medial 最大半径点が球中心付近、最大半径 ≈ 球半径。"""
    size, r = 41, 12
    center = np.array([20.0, 20.0, 20.0])
    vol = solid_ball(size, r, tuple(center))
    points, radius = medial.medial_axis_points(vol)

    assert points.shape[0] >= 1 and points.shape[1] == 3
    assert radius.shape == (points.shape[0],)

    imax = int(np.argmax(radius))
    err = np.linalg.norm(points[imax] - center)
    assert err <= 2.0, f"最大半径点が中心から {err:.2f} voxel"
    assert abs(radius[imax] - r) <= 1.5, f"最大半径 {radius[imax]:.2f} vs 球半径 {r}"


def test_ball_medial_collapses_to_point():
    """中実球の medial は点状(全 medial 点が中心近傍の小さな塊)。"""
    vol = solid_ball(41, 12)
    points, _ = medial.medial_axis_points(vol)
    center = np.array([20.0, 20.0, 20.0])
    spread = np.linalg.norm(points - center, axis=1).max()
    assert spread <= 2.0, f"球 medial の広がり {spread:.2f}(点状のはず)"


# ---------------------------------------------------------------- 中実円柱
def test_cylinder_medial_on_axis():
    """中実円柱 -> medial 点が軸線近傍に集中(線状)、最大半径 ≈ 円柱半径。"""
    size, r = 41, 7
    vol = solid_cylinder(size, r)
    points, radius = medial.medial_axis_points(vol)
    assert points.shape[0] >= 5

    axis = (size - 1) / 2.0
    d_axis = np.sqrt((points[:, 1] - axis) ** 2 + (points[:, 2] - axis) ** 2)
    assert (d_axis <= 2.0).mean() >= 0.8, "medial 点が軸線に集中していない"
    assert np.median(d_axis) <= 1.5
    assert abs(radius.max() - r) <= 1.5, f"最大半径 {radius.max():.2f} vs 円柱半径 {r}"


def test_cylinder_skeleton_is_linear():
    """中実円柱の骨格は 1 本の線(端点2・分岐0)。"""
    vol = solid_cylinder(41, 7)
    skel = medial.skeletonize_vol(vol)
    assert skel.dtype == bool and skel.shape == vol.shape
    assert np.all(vol[skel]), "骨格が前景の外に出ている"
    sig = medial.topology_signature(skel)
    assert sig["endpoints"] == 2 and sig["branches"] == 0
    assert sig["total"] >= 5


# ---------------------------------------------------------------- topology_signature
def test_topology_signature_rod():
    """直線棒 -> 端点2・分岐0。"""
    sig = medial.topology_signature(straight_rod(21, 11))
    assert sig["endpoints"] == 2
    assert sig["branches"] == 0
    assert sig["normal"] == 9
    assert sig["total"] == 11


def test_topology_signature_y():
    """Y 字 -> 端点3・分岐1。"""
    sig = medial.topology_signature(y_skeleton(25, 6))
    assert sig["endpoints"] == 3
    assert sig["branches"] == 1
    assert sig["degree_hist"].get(3, 0) == 1


def test_topology_signature_translation_invariant():
    """位相記述子は平行移動不変。"""
    rod = straight_rod(31, 9)
    shifted = np.zeros_like(rod)
    shifted[3:, 2:, 1:] = rod[:-3, :-2, :-1]
    assert medial.topology_signature(rod) == medial.topology_signature(shifted)


# ---------------------------------------------------------------- medial_match
def test_medial_match_same_greater_than_different():
    """同形状同士 > 異形状同士。"""
    ball_a = solid_ball(41, 12)
    ball_b = solid_ball(41, 12, center=(18, 22, 19))     # 同形状・平行移動
    cyl = solid_cylinder(41, 7)

    s_same = medial.medial_match(ball_a, ball_b)
    s_diff = medial.medial_match(ball_a, cyl)
    assert s_same > s_diff
    assert medial.medial_match(cyl, solid_cylinder(41, 7)) > medial.medial_match(cyl, ball_a)


def test_medial_match_self_is_maximal():
    """自己照合はほぼ 1.0、スコアは [0,1]。"""
    cyl = solid_cylinder(41, 7)
    s = medial.medial_match(cyl, cyl)
    assert 0.95 <= s <= 1.0
    assert 0.0 <= medial.medial_match(cyl, solid_ball(41, 12)) <= 1.0


# ---------------------------------------------------------------- 整合性 / 入力検証
def test_distance_ridge_consistency():
    """ridge は前景の部分集合、edt は scipy EDT と一致、radius は edt と整合。"""
    from scipy.ndimage import distance_transform_edt

    vol = solid_ball(31, 9)
    ridge, edt = medial.distance_ridge(vol)
    assert np.array_equal(edt, distance_transform_edt(vol).astype(np.float64))
    assert np.all(vol[ridge]), "ridge が前景外"
    points, radius = medial.medial_axis_points(vol)
    idx = points.astype(int)
    assert np.allclose(radius, edt[idx[:, 0], idx[:, 1], idx[:, 2]])


def test_min_radius_filters_thin_medial():
    """min_radius で薄い(半径の小さい)medial を除外できる。"""
    vol = solid_cylinder(41, 7)
    _, r_all = medial.medial_axis_points(vol, min_radius=0.0)
    _, r_hi = medial.medial_axis_points(vol, min_radius=3.0)
    assert r_hi.size <= r_all.size
    assert r_hi.min(initial=99.0) > 3.0 if r_hi.size else True


@pytest.mark.parametrize("bad", [np.zeros((8, 8)), np.zeros((8, 8, 8, 2)), np.zeros((0, 0, 0))])
def test_input_validation_rejects_non_3d_or_empty(bad):
    """3D 以外・空配列は fail-closed(ValueError)。"""
    with pytest.raises(ValueError):
        medial.distance_ridge(bad)


def test_negative_min_radius_rejected():
    """負の min_radius は ValueError。"""
    with pytest.raises(ValueError):
        medial.distance_ridge(solid_ball(21, 6), min_radius=-1.0)


def test_skeletonize_empty_volume():
    """空(全背景)-> 骨格も空、topology は全 0。"""
    empty = np.zeros((16, 16, 16), dtype=bool)
    skel = medial.skeletonize_vol(empty)
    assert skel.shape == empty.shape and not skel.any()
    sig = medial.topology_signature(skel)
    assert sig["total"] == 0 and sig["endpoints"] == 0 and sig["branches"] == 0


# --------------------------------------------------------------------------- #
# 骨格グラフ要素(junctions / endpoints / prune / branches)の 3D 版
# --------------------------------------------------------------------------- #
def _y_tube(size=40, c=20, half=1):
    """3 本の太い腕が中心で合流する Y 字ボリューム。"""
    vol = np.zeros((size, size, size), bool)
    vol[c - half:c + half + 1, c - half:c + half + 1, 4:c + half + 1] = True
    vol[c - half:c + half + 1, 4:c + half + 1, c - half:c + half + 1] = True
    vol[4:c + half + 1, c - half:c + half + 1, c - half:c + half + 1] = True
    return vol


def test_skeleton_graph3d_y_tube_counts():
    from scipy import ndimage
    import medial
    vol = _y_tube()
    st = np.ones((3, 3, 3), dtype=np.int32)
    _, nj = ndimage.label(medial.skeleton_junctions3d(vol), structure=st)
    _, ne = ndimage.label(medial.skeleton_endpoints3d(vol), structure=st)
    _, nb = ndimage.label(medial.skeleton_branches3d(vol, min_length=3),
                          structure=st)
    assert nj == 1, f"Y 字の分岐クラスタは 1 のはず (got {nj})"
    assert ne == 3, f"Y 字の端点は 3 のはず (got {ne})"
    assert nb == 3, f"分岐で切ると枝は 3 本のはず (got {nb})"


def test_skeleton_prune3d_removes_spur_keeps_trunk():
    import medial
    vol = _y_tube()
    skel = medial.skeletonize_vol(vol)
    zs, ys, xs = np.nonzero(skel)
    i = len(zs) // 3
    spur = skel.copy()
    spur[zs[i] + 1, ys[i] + 1, xs[i]] = True     # 長さ 2 のヒゲ
    spur[zs[i] + 2, ys[i] + 2, xs[i]] = True
    pruned = medial.skeleton_prune3d(spur, length=3)
    assert not pruned[zs[i] + 2, ys[i] + 2, xs[i]], "ヒゲが刈られていない"
    assert pruned.sum() > 0.5 * skel.sum(), "本体まで消えている"


def test_skeleton_graph3d_empty_and_thick_input():
    import medial
    empty = np.zeros((8, 8, 8))
    assert medial.skeleton_junctions3d(empty).sum() == 0
    assert medial.skeleton_endpoints3d(empty).sum() == 0
    # 太い塊(骨格でない)を渡しても内部で細線化されて動く
    solid = np.zeros((16, 16, 16), bool)
    solid[4:12, 4:12, 4:12] = True
    out = medial.skeleton_endpoints3d(solid)
    assert out.shape == solid.shape and out.dtype == bool
