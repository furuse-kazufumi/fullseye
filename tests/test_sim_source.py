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


def test_scene_geometries_builds_meshes():
    """F6: MuJoCo geom を実形状 Open3D メッシュ化(evis/ロケットを窓で見る橋)。"""
    import pytest
    o3d = pytest.importorskip("open3d")
    s = _src()   # floor(box) + block(box) の 2 geom
    geoms = s.scene_geometries()
    assert len(geoms) == 2
    for g in geoms:
        assert isinstance(g, o3d.geometry.TriangleMesh)
        assert len(g.vertices) > 0 and len(g.triangles) > 0
    s.close()


def test_save_animation_bundle(tmp_path):
    """アニメ: モデル XML + qpos 軌道をバンドル化し再構築できる(rollout を動きで見る基盤)。"""
    import json, os, numpy as np, mujoco
    s = S.MuJoCo(_XML)                          # XML 由来なので save_animation 可
    m = s._m
    traj = np.tile(np.asarray(s._d.qpos), (10, 1))   # 10 フレーム(静止軌道)
    man = s.save_animation(str(tmp_path / "anim"), traj, fps=20, title="テスト")
    spec = json.load(open(man, encoding="utf-8"))
    assert spec["kind"] == "animation" and spec["n_frames"] == 10 and spec["fps"] == 20
    q = np.load(os.path.join(os.path.dirname(man), spec["frames"]))
    m2 = mujoco.MjModel.from_xml_string(
        open(os.path.join(os.path.dirname(man), spec["model"]), encoding="utf-8").read())
    assert q.shape == (10, m.nq) and m2.nq == m.nq
    s.close()


def test_save_animation_requires_xml():
    """アニメ: MjModel 直渡し(XML 無し)では save_animation は明示 raise。"""
    import mujoco, pytest, numpy as np
    m = mujoco.MjModel.from_xml_string(_XML)
    s = S.MuJoCo(m)                             # XML を保持しない
    with pytest.raises(RuntimeError):
        s.save_animation("x", np.zeros((3, m.nq)))
    s.close()


def test_camera_pose_reprojection_exact():
    """3DGS: camera_to_world/project が正しい(真値点の再投影が描画深度と一致)。"""
    s = _src()   # top カメラ(真上)+ block(0.2,0,0.1)
    p = np.array([[0.2, 0.0, 0.2]])                 # block 上面の world 点
    uv, zproj = s.project(p, "top")
    u, v = uv[0]
    dep = s.depth("top")
    drend = dep[int(round(v)), int(round(u))]
    assert abs(float(zproj[0]) - float(drend)) < 1e-3   # 真値深度 == 描画深度
    c2w = s.camera_to_world("top")
    assert c2w.shape == (4, 4)
    assert np.allclose(s.extrinsics("top") @ c2w, np.eye(4), atol=1e-6)
    s.close()


def test_capture_orbit_dataset(tmp_path):
    """3DGS: オービット多視点 → transforms.json + images(姿勢=sim真値, COLMAP不要)。"""
    import json, os
    xml = ('<mujoco><worldbody><light pos="0 0 3"/>'
           '<geom type="sphere" size=".15" pos="0 0 .25" rgba=".9 .2 .2 1"/>'
           '</worldbody></mujoco>')
    path = S.capture_orbit(xml, str(tmp_path), n_views=8, radius=1.5,
                           elevation_deg=35, lookat=(0, 0, 0.25),
                           width=200, height=200)
    meta = json.load(open(path, encoding="utf-8"))
    assert len(meta["frames"]) == 8
    assert len([f for f in os.listdir(os.path.join(str(tmp_path), "images"))
                if f.endswith(".png")]) == 8
    # 全ビューで lookat が画像中心へ再投影(姿勢の正しさ)
    K = np.array([[meta["fl_x"], 0, meta["cx"]],
                  [0, meta["fl_y"], meta["cy"]], [0, 0, 1]])
    la = np.array([0, 0, 0.25])
    for fr in meta["frames"]:
        w2c = np.linalg.inv(np.array(fr["transform_matrix"]))
        cp = w2c[:3, :3] @ la + w2c[:3, 3]
        u = K[0, 2] + K[0, 0] * (cp[0] / -cp[2])
        v = K[1, 2] - K[1, 1] * (cp[1] / -cp[2])
        assert np.hypot(u - meta["cx"], v - meta["cy"]) < 0.5
