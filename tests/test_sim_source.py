"""F4 sim-source(物理→視覚の入力供給)の回帰テスト — 同一契約 + sim→vision フロー。"""
from __future__ import annotations

import warnings

import numpy as np

warnings.simplefilter("ignore")
import sim_source as S  # noqa: E402

_XML = ('<mujoco><worldbody><light pos="0 0 2"/>'
        '<geom name="floor" type="box" size=".5 .5 .02" pos="0 0 .02"/>'
        '<geom name="block" type="box" size=".1 .1 .1" pos=".2 0 .1"/>'
        '<camera name="top" pos="0 0 1.2" xyaxes="1 0 0 0 1 0"/></worldbody></mujoco>')


def _src():
    return S.MuJoCo(_XML, width=160, height=160)


def test_backends_reported():
    """F4: MuJoCo は実供給、Gazebo/IsaacSim は honest scaffold。"""
    b = S.backends()
    assert b["MuJoCo"]["available"] is True
    assert b["Gazebo"]["available"] is False and b["IsaacSim"]["available"] is False


def test_intrinsics_from_fovy():
    """F4: 内部行列 K が fovy と解像度から算出される(GL 不要・正方画素)。"""
    s = _src()
    K = s.intrinsics("top")
    assert K.shape == (3, 3)
    assert np.isclose(K[0, 0], K[1, 1])          # fx == fy
    assert np.isclose(K[0, 2], 80) and np.isclose(K[1, 2], 80)   # 主点 = 画像中心
    s.close()


def test_ground_truth_has_true_poses():
    """F4: ground_truth が真の body 姿勢(honest 評価の真値源)を返す。"""
    s = _src()
    gt = s.ground_truth()
    assert "world" in gt
    pos, quat = gt["world"]
    assert pos.shape == (3,) and quat.shape == (4,)
    s.close()


def test_rgb_and_depth_render():
    """F4: RGB/深度が headless で描画できる。"""
    s = _src()
    rgb = s.rgb("top")
    dep = s.depth("top")
    assert rgb.shape == (160, 160, 3) and rgb.dtype == np.uint8
    assert dep.shape == (160, 160) and dep.min() > 0
    s.close()


def test_point_cloud_backprojects_to_world():
    """F4: 深度を逆投影した world 点群がシーン形状に一致(sim→vision の橋)。"""
    s = _src()
    pc = s.point_cloud("top", stride=2)
    assert pc.shape[1] == 3 and len(pc) > 100
    # 上面視: 最大高 ~0.2m(block 上面)、床は ~0.04m
    assert 0.15 < pc[:, 2].max() < 0.25
    s.close()


def test_sim_to_vision_pipeline():
    """F4+F5: MuJoCo 点群 → fs.elevation_map(視覚 op)が繋がる。"""
    import fullseye as fs
    s = _src()
    cloud = s.point_cloud("top", stride=2)
    grid, extent = fs.elevation_map(cloud, cell=0.03, agg="max")
    assert grid.ndim == 2
    assert 0.15 < float(np.nanmax(grid)) < 0.25       # block の高さを知覚
    s.close()


def test_registered_in_unified():
    """F2/F3: sim-source が統一 registry に provenance=sim-source で載る。"""
    import unified as u
    assert "MuJoCo" in u.ops.list(namespace="sim")
    d = u.ops.describe("MuJoCo")
    assert d["provenance"] == "sim-source" and d["render_hint"] == "point_cloud"


def test_scaffold_raises_clearly():
    """F4: 未接続 sim-source は動詞で明示 raise(optional-extras)。"""
    import pytest
    g = S.Gazebo()
    assert g.available is False
    with pytest.raises(RuntimeError):
        g.depth("cam")
