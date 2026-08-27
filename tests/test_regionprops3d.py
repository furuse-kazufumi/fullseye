"""regionprops3d — 3D 連結成分ラベリング + リージョンプロパティの ground-truth 検証。

既知の複数物体(離散球・箱)を合成し、体積・重心・等価半径・真球度・主軸長を
数値で検証する。離散化誤差を見込んだ許容幅で確認する。
"""
import numpy as np
import pytest

pytest.importorskip("scipy")

import regionprops3d as R  # noqa: E402


# --------------------------------------------------------------------------- #
# 合成ジェネレータ                                                              #
# --------------------------------------------------------------------------- #
def _ball(shape, center, radius):
    """center (z,y,x) 中心・半径 radius の離散球 bool ボリューム。"""
    zz, yy, xx = np.ogrid[: shape[0], : shape[1], : shape[2]]
    cz, cy, cx = center
    return ((zz - cz) ** 2 + (yy - cy) ** 2 + (xx - cx) ** 2) <= radius ** 2


def _two_balls():
    """分離した 2 球(半径 6 と 8)を 1 つのボリュームに配置。"""
    shape = (40, 40, 40)
    vol = np.zeros(shape, dtype=bool)
    c1, r1 = (10, 10, 10), 6
    c2, r2 = (28, 28, 28), 8
    vol |= _ball(shape, c1, r1)
    vol |= _ball(shape, c2, r2)
    return vol, (c1, r1), (c2, r2)


def _theoretical_volume(r):
    return (4.0 / 3.0) * np.pi * r ** 3


# --------------------------------------------------------------------------- #
# label_components                                                             #
# --------------------------------------------------------------------------- #
def test_two_balls_labeled_as_two_components():
    vol, _, _ = _two_balls()
    labels, n = R.label_components(vol, connectivity=26)
    assert n == 2
    assert labels.shape == vol.shape
    # ラベルは 0(背景) + {1,2}
    assert set(np.unique(labels).tolist()) == {0, 1, 2}


def test_empty_input_graceful():
    vol = np.zeros((8, 8, 8), dtype=bool)
    labels, n = R.label_components(vol)
    assert n == 0
    assert not labels.any()
    assert R.region_props(vol) == []
    assert not R.largest_component(vol).any()
    assert not R.filter_by_volume(vol, 5).any()


def test_connectivity_diagonal_only():
    """角のみで接する 2 ボクセルは 6 連結では別成分、26 連結では 1 成分。"""
    vol = np.zeros((3, 3, 3), dtype=bool)
    vol[0, 0, 0] = True
    vol[1, 1, 1] = True  # 角接続のみ
    assert R.label_components(vol, connectivity=6)[1] == 2
    assert R.label_components(vol, connectivity=26)[1] == 1


def test_invalid_connectivity_raises():
    vol = np.zeros((4, 4, 4), dtype=bool)
    with pytest.raises(ValueError):
        R.label_components(vol, connectivity=7)


def test_non_3d_raises():
    with pytest.raises(ValueError):
        R.label_components(np.zeros((4, 4), dtype=bool))


# --------------------------------------------------------------------------- #
# region_props — volume / centroid / equivalent_radius                        #
# --------------------------------------------------------------------------- #
def test_region_props_volume_and_centroid():
    vol, (c1, r1), (c2, r2) = _two_balls()
    props = R.region_props(vol, connectivity=26)
    assert len(props) == 2

    # 体積で成分を同定(小球=r1, 大球=r2)。
    props_sorted = sorted(props, key=lambda p: p["volume"])
    small, large = props_sorted

    for p, (center, radius) in ((small, (c1, r1)), (large, (c2, r2))):
        theo = _theoretical_volume(radius)
        # 離散化: 理論体積に対し ±15%。
        assert abs(p["volume"] - theo) / theo < 0.15, (radius, p["volume"], theo)
        # 重心は既知中心 ±1 voxel。
        for got, exp in zip(p["centroid"], center):
            assert abs(got - exp) <= 1.0, (p["centroid"], center)
        # 等価半径 ≈ R(±10%)。
        assert abs(p["equivalent_radius"] - radius) / radius < 0.10, (
            p["equivalent_radius"],
            radius,
        )


# --------------------------------------------------------------------------- #
# sphericity — 球 ~1 / 細長い箱は有意に小さい                                    #
# --------------------------------------------------------------------------- #
def test_sphericity_sphere_high_box_low():
    shape = (40, 40, 40)
    ball = _ball(shape, (20, 20, 20), 10)
    ball_prop = R.region_props(ball)[0]
    assert ball_prop["sphericity"] > 0.7, ball_prop["sphericity"]

    # 細長い箱(1x1x20 相当)。表面積が体積に対して大きく真球度は低い。
    box = np.zeros(shape, dtype=bool)
    box[20, 20, 5:35] = True  # 長さ 30、断面 1x1
    box_prop = R.region_props(box)[0]
    assert box_prop["sphericity"] < ball_prop["sphericity"]
    assert box_prop["sphericity"] < 0.5, box_prop["sphericity"]


# --------------------------------------------------------------------------- #
# principal_lengths — 細長い箱で 1 軸が突出                                      #
# --------------------------------------------------------------------------- #
def test_principal_lengths_elongated_box():
    shape = (30, 30, 40)
    box = np.zeros(shape, dtype=bool)
    box[13:17, 13:17, 5:35] = True  # x 方向に長い(長さ 30、断面 4x4)
    prop = R.region_props(box)[0]
    lengths = prop["principal_lengths"]
    # 降順で返る前提。最長軸が 2 番目より十分大きい。
    assert lengths[0] > 2.5 * lengths[1], lengths
    # 主軸(最長)は x 方向 (z,y,x) の第 3 成分が支配的。
    major = prop["principal_axes"][0]
    assert abs(major[2]) > abs(major[0]) and abs(major[2]) > abs(major[1]), major


# --------------------------------------------------------------------------- #
# largest_component                                                            #
# --------------------------------------------------------------------------- #
def test_largest_component_keeps_bigger_ball():
    vol, (c1, r1), (c2, r2) = _two_balls()
    mask = R.largest_component(vol, connectivity=26)
    assert mask.shape == vol.shape
    # 大球(r2=8)側のみ残る。小球中心は False、大球中心は True。
    assert mask[c2] == True  # noqa: E712
    assert mask[c1] == False  # noqa: E712
    # 残ったマスクは 1 成分。
    assert R.label_components(mask)[1] == 1
    # ボクセル数は大球の理論値近傍。
    theo = _theoretical_volume(r2)
    assert abs(mask.sum() - theo) / theo < 0.15


# --------------------------------------------------------------------------- #
# filter_by_volume — 小さい成分が消える                                         #
# --------------------------------------------------------------------------- #
def test_filter_by_volume_removes_small():
    vol, (c1, r1), (c2, r2) = _two_balls()
    v_small = _ball(vol.shape, c1, r1).sum()
    v_large = _ball(vol.shape, c2, r2).sum()
    # 小球より大きく大球以下の閾値 -> 小球のみ除去。
    thr = v_small + 1
    mask = R.filter_by_volume(vol, thr, connectivity=26)
    assert mask[c2] == True  # noqa: E712  大球残る
    assert mask[c1] == False  # noqa: E712  小球消える
    assert R.label_components(mask)[1] == 1

    # 両方より大きい閾値 -> 全消去。
    assert not R.filter_by_volume(vol, v_large + 1, connectivity=26).any()
    # 十分小さい閾値 -> 両方残る。
    assert R.label_components(R.filter_by_volume(vol, 1, connectivity=26))[1] == 2
