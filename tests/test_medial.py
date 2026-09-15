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


# --------------------------------------------------------------------------- #
# skeleton_graph3d — 骨格を「ノードと枝のグラフ」に組み立てる                   #
#                                                                             #
# 許容値は**実測から決めてある**(この repo の規律: 乱数だけの門にしない)。     #
# 太い入力は細線化が端を内側へ寄せるので、長さの厳密な門は 1 voxel 幅の骨格で   #
# 見る —— ずれるのはこの op ではなくヘルパ(skimage Lee)だから                 #
# ([[feedback_invariance_claims_break_at_the_helper]])。                       #
# --------------------------------------------------------------------------- #
def _tube_z(shape, cy, cx, z0, z1, r):
    """z 軸に沿う中実の管(両端は平らな蓋)。"""
    zz, yy, xx = np.mgrid[0:shape[0], 0:shape[1], 0:shape[2]]
    radial = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    return (radial <= r) & (zz >= z0) & (zz <= z1)


def _thin_line(shape, cy, cx, z0, z1):
    """1 voxel 幅の直線骨格(細線化を通らない = 長さの真値が厳密に分かる)。"""
    s = np.zeros(shape, dtype=bool)
    s[z0:z1 + 1, cy, cx] = True
    return s


def _thin_y(size=25, arm=6):
    """1 voxel 幅の Y 字骨格。3 本の角対角枝(1 歩 = sqrt(3))。"""
    s = np.zeros((size, size, size), dtype=bool)
    c = size // 2
    s[c, c, c] = True
    for dz, dy, dx in [(1, 1, 1), (1, -1, -1), (-1, 1, -1)]:
        for k in range(1, arm + 1):
            s[c + dz * k, c + dy * k, c + dx * k] = True
    return s


def _torus_vol(size=48, major=14.0, minor=3.0):
    """閉じた管(輪)。骨格は端点も分岐も持たない閉ループになる。"""
    zz, yy, xx = np.mgrid[0:size, 0:size, 0:size]
    c = (size - 1) / 2.0
    rho = np.sqrt((yy - c) ** 2 + (xx - c) ** 2)
    return (rho - major) ** 2 + (zz - c) ** 2 <= minor * minor


def _graph_key(g):
    """回転で不変であるべきものすべて(構造 + 長さ)。"""
    return (g["n_nodes"], g["n_edges"], g["n_components"], g["n_cycles"],
            tuple(sorted(n["degree"] for n in g["nodes"])),
            tuple(sorted(n["kind"] for n in g["nodes"])),
            tuple(np.round(sorted(e["length"] for e in g["edges"]), 9)))


# ---- 門 1: まっすぐな円柱 -> ノード 2・枝 1、長さと半径が真値と一致 ---------- #
def test_graph3d_straight_cylinder_length_and_radius():
    """長さ 35・半径 2 の管 -> ノード 2(端点)・枝 1、長さも半径も 1 voxel 以内。"""
    z0, z1, r = 5, 40, 2.0
    vol = _tube_z((50, 40, 40), 20, 20, z0, z1, r)
    dist = medial.distance_ridge(vol)[1]                 # EDT(= vol_distance_transform)
    g = medial.skeleton_graph3d(vol, distance=dist)

    assert (g["n_nodes"], g["n_edges"]) == (2, 1)
    assert g["n_components"] == 1 and g["n_cycles"] == 0
    assert sorted(n["kind"] for n in g["nodes"]) == ["endpoint", "endpoint"]

    e = g["edges"][0]
    assert abs(e["length"] - (z1 - z0)) <= 1.0, f"長さ {e['length']} vs 真値 {z1 - z0}"
    assert abs(e["radius_mean"] - r) <= 1.0, f"半径 {e['radius_mean']} vs 真値 {r}"
    assert g["has_radius"] and e["n_points"] == int(e["length"]) + 1


def test_graph3d_thin_line_length_is_exact():
    """1 voxel 幅の直線(細線化を通らない)では長さが**厳密に**一致する。"""
    g = medial.skeleton_graph3d(_thin_line((41, 21, 21), 10, 10, 5, 35))
    assert (g["n_nodes"], g["n_edges"]) == (2, 1)
    assert g["edges"][0]["length"] == 30.0            # 31 voxel = 30 歩
    assert g["edges"][0]["n_points"] == 31


# ---- 門 2: Y 字 -> ノード 4・枝 3、太さの違う枝を見分けられる ---------------- #
def test_graph3d_y_tube_counts_lengths_and_radii():
    """腕ごとに長さも半径も違う Y 字。ノード 4(端点 3 + 接合 1)・枝 3。

    太い入力なので、自由端は細線化で内側へ寄る(実測: 半径 3 の腕で 2 voxel)。
    だから長さの許容は「真値 − (半径 + 1) 〜 真値 + 1」。半径は枝の平均で見る。
    """
    n, c = 60, 30
    zz, yy, xx = np.mgrid[0:n, 0:n, 0:n]
    trunk = (np.sqrt((yy - c) ** 2 + (zz - c) ** 2) <= 3.0) & (xx >= 5) & (xx <= c)
    arm1 = (np.sqrt((xx - c) ** 2 + (zz - c) ** 2) <= 2.0) & (yy >= 8) & (yy <= c)
    arm2 = (np.sqrt((xx - c) ** 2 + (yy - c) ** 2) <= 1.0) & (zz >= 12) & (zz <= c)
    vol = trunk | arm1 | arm2
    dist = medial.distance_ridge(vol)[1]
    g = medial.skeleton_graph3d(vol, distance=dist)

    assert (g["n_nodes"], g["n_edges"]) == (4, 3)
    kinds = sorted(n_["kind"] for n_ in g["nodes"])
    assert kinds == ["endpoint", "endpoint", "endpoint", "junction"]
    assert sorted(n_["degree"] for n_ in g["nodes"]) == [1, 1, 1, 3]
    assert g["n_cycles"] == 0 and g["n_components"] == 1

    # 枝を太さ順に並べる = 幹(3)・中(2)・細(1)。**区別できること**が要点。
    by_r = sorted(g["edges"], key=lambda e: e["radius_mean"])
    truth = [(18, 1.0), (22, 2.0), (25, 3.0)]            # (長さ, 半径)
    got_r = [e["radius_mean"] for e in by_r]
    assert got_r[0] < got_r[1] < got_r[2], f"太さの違う枝を区別できていない: {got_r}"
    for e, (L, r) in zip(by_r, truth):
        assert abs(e["radius_mean"] - r) <= 0.5, f"半径 {e['radius_mean']:.2f} vs {r}"
        assert L - (r + 1.0) <= e["length"] <= L + 1.0, \
            f"長さ {e['length']:.2f} が真値 {L}(半径 {r} ぶん端が縮む)から外れた"


def test_graph3d_radius_comes_from_the_distance_volume():
    """半径は渡した距離場そのもの: 太さだけを変えた 3 枝を厳密に見分ける。"""
    sk = np.zeros((41, 41, 41), dtype=bool)
    sk[20, 20, 5:21] = True
    sk[20, 5:21, 20] = True
    sk[5:21, 20, 20] = True
    dist = np.zeros(sk.shape)
    dist[20, 20, 5:21] = 3.0
    dist[20, 5:21, 20] = 2.0
    dist[5:21, 20, 20] = 1.0
    dist[20, 20, 20] = 3.0
    g = medial.skeleton_graph3d(sk, distance=dist)
    assert (g["n_nodes"], g["n_edges"]) == (4, 3)
    assert sorted(e["radius_mean"] for e in g["edges"]) == [1.0, 2.0, 3.0]
    assert sorted(e["radius_min"] for e in g["edges"]) == [1.0, 2.0, 3.0]
    # 距離場を渡さなければ半径は None(「知らない」を 0 と嘘をつかない)
    g0 = medial.skeleton_graph3d(sk)
    assert not g0["has_radius"]
    assert all(e["radius_mean"] is None for e in g0["edges"])
    assert all(n_["radius"] is None for n_ in g0["nodes"])


# ---- 門 3: 輪(サイクル)-> 木だと仮定しない。オイラーの関係で検査 ----------- #
@pytest.mark.parametrize("major", [10.0, 14.0, 18.0])
def test_graph3d_closed_ring_satisfies_euler(major):
    """閉じた管: ノード 1・枝 1(自己ループ)で 閉路数 = E - N + C = 1。"""
    g = medial.skeleton_graph3d(_torus_vol(major=major))
    assert (g["n_nodes"], g["n_edges"], g["n_components"]) == (1, 1, 1)
    assert g["n_cycles"] == g["n_edges"] - g["n_nodes"] + g["n_components"] == 1
    e = g["edges"][0]
    assert e["u"] == e["v"], "輪は自己ループの枝になるはず"
    # 26 近傍の折れ線は曲線より長く出る(実測 +7 % 前後)。**短くは出ない**。
    ratio = e["length"] / (2.0 * np.pi * major)
    assert 1.0 <= ratio <= 1.15, f"輪の長さ比 {ratio:.3f}"


def test_graph3d_two_rings_keep_euler_per_component():
    """輪 2 つ(成分 2)-> N 2 / E 2 / 閉路 2。木の仮定は入っていない。"""
    size = 48
    zz, yy, xx = np.mgrid[0:size, 0:size, 0:size]
    c = (size - 1) / 2.0
    rho = np.sqrt((yy - c) ** 2 + (xx - c) ** 2)
    two = (((rho - 16.0) ** 2 + (zz - 12) ** 2 <= 2.5 ** 2)
           | ((rho - 8.0) ** 2 + (zz - 35) ** 2 <= 2.5 ** 2))
    g = medial.skeleton_graph3d(two)
    assert (g["n_nodes"], g["n_edges"], g["n_components"]) == (2, 2, 2)
    assert g["n_cycles"] == g["n_edges"] - g["n_nodes"] + g["n_components"] == 2


# ---- 門 4: 異方 spacing。渡さないと外れることまで確かめる -------------------- #
def test_graph3d_anisotropic_spacing_matches_isotropic():
    """z だけ 2 倍粗い格子 + spacing=(2,1,1) が等方の長さと**厳密に**一致する。

    門が効いている証拠として、**spacing を渡さないと外れる**ことも見る
    (一致しかテストしないと「spacing を無視する実装」でも緑になる)。
    """
    iso = medial.skeleton_graph3d(_thin_line((41, 21, 21), 10, 10, 5, 35))
    coarse_vol = _thin_line((21, 21, 21), 10, 10, 2, 17)       # 16 層 x 2 = 同じ物理長
    with_sp = medial.skeleton_graph3d(coarse_vol, spacing=(2.0, 1.0, 1.0))
    without = medial.skeleton_graph3d(coarse_vol)

    li = iso["edges"][0]["length"]
    assert with_sp["edges"][0]["length"] == li == 30.0
    assert with_sp["spacing"] == (2.0, 1.0, 1.0)
    assert abs(without["edges"][0]["length"] - li) == 15.0, \
        "spacing を無視しても同じ長さが出る = この門は何も見ていない"


# ---- 門 5: 90 度回転でグラフが同型・長さも一致 ------------------------------- #
def test_graph3d_is_invariant_under_axis_rotations():
    """1 voxel 幅の骨格を 90 度の倍数で回すと、構造も長さも厳密に一致(9 通り)。"""
    y = _thin_y()
    base = _graph_key(medial.skeleton_graph3d(y))
    assert base[0:2] == (4, 3)
    for axes in [(0, 1), (0, 2), (1, 2)]:
        for k in (1, 2, 3):
            got = _graph_key(medial.skeleton_graph3d(np.rot90(y, k, axes=axes)))
            assert got == base, f"回転 {axes} x{k} でグラフが変わった: {got} != {base}"


def test_graph3d_rotation_check_is_not_vacuous():
    """★門を壊して確かめる: 格子が**本当に異方**なら回転で長さは変わるべき。

    等方なら 9 通りすべて 0 ずれ、``spacing=(3,1,1)`` なら最大 20 ずれる。
    後者が 0 なら「この比較は何を入れても一致する」= 門が鈍感、という意味になる。
    """
    seg = np.zeros((31, 31, 31), dtype=bool)
    seg[10:21, 8, 8] = True                    # z 沿い 10 歩
    seg[24, 20, 14:21] = True                  # x 沿い  6 歩(別の成分)
    base_iso = sorted(e["length"] for e in medial.skeleton_graph3d(seg)["edges"])
    base_ani = sorted(e["length"] for e in
                      medial.skeleton_graph3d(seg, spacing=(3.0, 1.0, 1.0))["edges"])
    assert base_iso == [6.0, 10.0] and base_ani == [6.0, 30.0]

    worst_iso = worst_ani = 0.0
    for axes in [(0, 1), (0, 2), (1, 2)]:
        for k in (1, 2, 3):
            rot = np.rot90(seg, k, axes=axes)
            a = sorted(e["length"] for e in medial.skeleton_graph3d(rot)["edges"])
            b = sorted(e["length"] for e in
                       medial.skeleton_graph3d(rot, spacing=(3.0, 1.0, 1.0))["edges"])
            worst_iso = max(worst_iso, max(abs(x - y) for x, y in zip(a, base_iso)))
            worst_ani = max(worst_ani, max(abs(x - y) for x, y in zip(b, base_ani)))
    assert worst_iso == 0.0, "等方なのに回転で長さが変わった"
    assert worst_ani == 20.0, ("異方 spacing でも回転で長さが変わらない —— "
                               "長さの比較が spacing を見ていない(門が鈍感)")


# ---- 門 6: 連結成分。離れたものを黙って繋がない ------------------------------ #
def test_graph3d_does_not_join_separate_components():
    """離れた 2 本の管 -> 成分 2 と報告し、成分をまたぐ枝を作らない。"""
    shape = (40, 40, 40)
    two = _tube_z(shape, 12, 12, 4, 34, 2.0) | _tube_z(shape, 28, 28, 4, 34, 2.0)
    g = medial.skeleton_graph3d(two)
    assert g["n_components"] == 2
    assert (g["n_nodes"], g["n_edges"]) == (4, 2)
    comp_of = {n_["id"]: n_["component"] for n_ in g["nodes"]}
    for e in g["edges"]:
        assert comp_of[e["u"]] == comp_of[e["v"]] == e["component"], \
            "成分をまたぐ枝を作っている(繋がっていないものを繋いだ)"
    assert {n_["component"] for n_ in g["nodes"]} == {1, 2}


# ---- 門 7: fail-closed ------------------------------------------------------- #
@pytest.mark.parametrize("bad", [
    np.zeros((8, 8)),                       # 3-D でない
    np.zeros((8, 8, 8, 2)),                 # 3-D でない
    np.zeros((0, 0, 0)),                    # 空
    np.zeros((8, 8, 8), dtype=bool),        # 前景ゼロ
    np.full((8, 8, 8), np.nan),             # 非有限
    np.full((8, 8, 8), 0.37),               # 二値でない
])
def test_graph3d_rejects_bad_volumes(bad):
    with pytest.raises(ValueError):
        medial.skeleton_graph3d(bad)


@pytest.mark.parametrize("kwargs", [
    {"distance": np.zeros((8, 8, 8))},          # 形が違う
    {"distance": -np.ones((30, 30, 30))},       # 負の距離
    {"distance": np.full((30, 30, 30), np.nan)},
    {"spacing": (0.0, 1.0, 1.0)},               # 0 は許さない
    {"spacing": (1.0, 1.0)},                    # 3 つでない
    {"spacing": (1.0, 1.0, -1.0)},
    {"min_branch_len": -1.0},
])
def test_graph3d_rejects_bad_arguments(kwargs):
    ok = _tube_z((30, 30, 30), 15, 15, 4, 24, 2.0)
    with pytest.raises(ValueError):
        medial.skeleton_graph3d(ok, **kwargs)


# ---- 門 8: 「走った」≠「意味のある出力」 ------------------------------------- #
def test_graph3d_never_returns_an_empty_graph_silently():
    """ノード 0 で返る経路が無いこと。**空は例外**であって空の出力ではない。"""
    cases = {
        "cylinder": _tube_z((40, 40, 40), 20, 20, 4, 34, 2.0),
        "thin_line": _thin_line((41, 21, 21), 10, 10, 5, 35),
        "y": _thin_y(),
        "ring": _torus_vol(),
    }
    for name, vol in cases.items():
        g = medial.skeleton_graph3d(vol)
        assert g["n_nodes"] >= 1 and g["n_edges"] >= 1, f"{name} が空のグラフ"
        assert g["n_skeleton_voxels"] > 0
        assert len(g["nodes"]) == g["n_nodes"] and len(g["edges"]) == g["n_edges"]

    # 孤立 1 voxel は「ノード 1・枝 0」と**名指しで**返る(黙って空ではない)
    one = np.zeros((5, 5, 5), dtype=bool)
    one[2, 2, 2] = True
    g1 = medial.skeleton_graph3d(one)
    assert (g1["n_nodes"], g1["n_edges"]) == (1, 0)
    assert g1["nodes"][0]["kind"] == "isolated"
    # 前景が無いときだけが「グラフが無い」で、それは例外
    with pytest.raises(ValueError):
        medial.skeleton_graph3d(np.zeros((5, 5, 5), dtype=bool))


# ---- ヒゲ刈り(min_branch_len)------------------------------------------------ #
def test_graph3d_prunes_short_terminal_branches_only():
    """末端の短い枝だけを刈る。長いヒゲも、両端が端点の孤立管も残す。"""
    sk = _thin_line((41, 21, 21), 10, 10, 5, 35)
    for k in (1, 2, 3):
        sk[20, 10 + k, 10] = True                     # 3 voxel のヒゲ -> 枝長 2.0
    g0 = medial.skeleton_graph3d(sk)
    assert (g0["n_nodes"], g0["n_edges"]) == (4, 3)
    assert sorted(round(e["length"], 3) for e in g0["edges"]) == [2.0, 14.0, 14.0]

    keep = medial.skeleton_graph3d(sk, min_branch_len=1.5)
    assert keep["n_edges"] == 3 and keep["n_pruned_branches"] == 0

    cut = medial.skeleton_graph3d(sk, min_branch_len=3.5)
    assert cut["n_edges"] == 2 and cut["n_pruned_branches"] == 1
    assert sorted(round(e["length"], 3) for e in cut["edges"]) == [14.0, 14.0]

    # 長いヒゲ(5.0)は同じ閾値では残る
    long_spur = _thin_line((41, 21, 21), 10, 10, 5, 35)
    for k in (1, 2, 3, 4, 5, 6):
        long_spur[20, 10 + k, 10] = True
    assert medial.skeleton_graph3d(long_spur, min_branch_len=3.5)["n_edges"] == 3

    # 両端が端点の短い孤立管は「末端の枝」ではない(刈ると構造ごと消える)
    short = _thin_line((20, 20, 20), 10, 10, 8, 11)
    g = medial.skeleton_graph3d(short, min_branch_len=100.0)
    assert (g["n_nodes"], g["n_edges"], g["n_pruned_branches"]) == (2, 1, 0)


# ---- 台帳経由(宣言 out 型 = table)------------------------------------------- #
def test_graph3d_is_reachable_through_the_ledger_as_a_table():
    """``ops3d`` の宣言 out 型 ``table`` と実返り(dict)が一致する。"""
    pytest.importorskip("torch")                      # ops3d は torch 依存を束ねる
    import ops3d
    meta = ops3d.info("skeleton_graph3d")
    assert meta["out"] == "table" and meta["in"] == ["voxel"]
    assert meta["module"] == "medial" and meta["category"] == "medial"
    r = ops3d.call("skeleton_graph3d", _thin_line((31, 11, 11), 5, 5, 5, 25))
    assert isinstance(r, dict)                        # table = list | dict
    assert (r["n_nodes"], r["n_edges"]) == (2, 1)
    assert r["edges"][0]["length"] == 20.0
