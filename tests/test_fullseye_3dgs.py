"""fullseye_3dgs ランチャの非GPU部分(preset)の回帰。scene 解決は scene_registry に移設。"""
from __future__ import annotations

import os

import fullseye_3dgs as F
import scene_registry as R


def test_presets_shape():
    for k in ("fast", "balanced", "high"):
        res, ng, it, nv = F.PRESETS[k]
        assert res > 0 and ng > 0 and it > 0 and nv > 0
    assert F.PRESETS["high"][0] > F.PRESETS["fast"][0]     # high の方が高解像


def test_scene_resolution_via_registry():
    """go2 resolves to a real MJCF path via scene_registry.

    Honest note (2026-08-30 CI investigation): despite living in test_fullseye_3dgs.py,
    this check has no torch dependency — scene_registry.py imports only json/os and
    resolve() is pure path logic. The actual CI-only failure is that
    scene_registry._MENAGERIE hardcodes an absolute local path
    (C:/dev/projects/mujoco_menagerie) to a sibling checkout of mujoco_menagerie that
    is not part of this repo and is not cloned on CI runners (ubuntu-latest); on Linux
    that Windows path also just doesn't exist. So resolve("go2") legitimately returns
    None there. Skip when the asset tree is absent, matching this file's existing
    mujoco-asset skip convention (see test_pick_gif_headless_grasps etc.), rather than
    torch.importorskip which would not address the real cause.
    """
    go2_xml = os.path.join(R._MENAGERIE, "unitree_go2", "scene.xml")
    if not os.path.exists(go2_xml):
        import pytest
        pytest.skip("mujoco_menagerie(go2) 未取得 — scene_registry._MENAGERIE の資産チェックアウトが無い")
    r = R.resolve("go2")
    assert r is not None and r["xml"].endswith(".xml")
    assert R.resolve("does-not-exist") is None


def test_builtins_registered():
    assert {"go2", "cassie", "apollo", "evis", "terrain"}.issubset(set(R.names()))


def test_tsdf_mesh_op_registered():
    """TSDF メッシャが共通 I/F(unified)op として登録されている(GPU 不要経路)。"""
    import unified as u
    assert "tsdf_mesh" in u.ops
    assert "sugar_mesh" in u.ops


def test_fullseye3d_mesh_accepts_method():
    """fullseye3d.Scene.mesh(method=...) が tsdf/sugar を受ける(署名の固定)。"""
    import inspect
    import fullseye3d as f3d
    sig = inspect.signature(f3d.Scene.mesh)
    assert "method" in sig.parameters
    assert sig.parameters["method"].default == "tsdf"       # 既定は GPU 不要の TSDF


def test_world_walk_accepts_mesh_method():
    import inspect
    import recipe_world_walk as rw
    sig = inspect.signature(rw.world_walk)
    assert sig.parameters["mesh_method"].default == "tsdf"


def test_render_walk_gif_op_registered():
    import unified as u
    assert "render_walk_gif" in u.ops


def test_render_walk_gif_headless(tmp_path):
    """headless GIF 生成が go2 トロット×rolling で通る(GPU 不要・MuJoCo offscreen)。"""
    import importlib.util
    if importlib.util.find_spec("mujoco") is None:
        import pytest
        pytest.skip("mujoco 未インストール")
    import world_render as WR
    out = str(tmp_path / "walk.gif")
    r = WR.render_walk_gif(out, walker="go2", terrain="rolling", gait="trot",
                           n_frames=6, max_gif_frames=4, width=160, height=120,
                           log=lambda *_: None)
    import os
    assert os.path.isfile(out) and os.path.getsize(out) > 0
    assert r["frames"] >= 1 and r["nq"] == r["nq"]


def test_pick_gif_op_registered():
    import unified as u
    assert "pick_gif" in u.ops


def test_pick_gif_headless_grasps(tmp_path):
    """Panda pick-and-place が headless で通り、キューブを実測で持ち上げる(グルー無し)。

    把持成否はシミュレーションが吐く箱の実測高さ(lift_m)で判定する — 誇張せず、
    掴めていなければ落ちる。Menagerie / mujoco が無い環境では skip。"""
    import importlib.util
    import os
    if importlib.util.find_spec("mujoco") is None:
        import pytest
        pytest.skip("mujoco 未インストール")
    import pick_render as PR
    if not os.path.exists(PR._PANDA_CUBE):
        import pytest
        pytest.skip("mujoco_menagerie(panda)未取得")
    out = str(tmp_path / "pick.gif")
    r = PR.render_pick_gif(out, width=160, height=120, max_gif_frames=8, log=lambda *_: None)
    assert os.path.isfile(out) and os.path.getsize(out) > 0
    assert r["grasped"] is True and r["lift_m"] > 0.10       # cube genuinely cleared the table


def test_sensor_fusion_op_registered():
    import unified as u
    assert "sensor_fusion" in u.ops


def test_sensor_fusion_beats_single_sensors(tmp_path):
    """Kalman 融合が位置センサ単体・IMU 単体の RMSE を実測で下回る(GPU 不要)。

    誇張防止: 融合が勝てなければ fused_wins=False になる設計なので、テストは実測の勝ちを要求。"""
    import importlib.util
    import os
    if importlib.util.find_spec("mujoco") is None:
        import pytest
        pytest.skip("mujoco 未インストール")
    import sensor_fusion as SF
    out = str(tmp_path / "fuse.png")
    r = SF.run_fusion_demo(out, log=lambda *_: None)
    assert os.path.isfile(out) and os.path.getsize(out) > 0
    rmse = r["rmse_m"]
    assert r["fused_wins"] is True
    assert rmse["kalman_fused"] < rmse["position_sensor_only"]
    assert rmse["kalman_fused"] < rmse["imu_dead_reckoning"]


def test_bin_pick_op_registered():
    import unified as u
    assert "bin_pick_gif" in u.ops


def test_bin_pick_headless_picks(tmp_path):
    """バラ積みピッキングが headless で通り、実際に部品を bin から取り出す(グルー無し)。

    成功数は部品が bin を出たかで数える実測値。Menagerie/mujoco 不在なら skip。"""
    import importlib.util
    import os
    if importlib.util.find_spec("mujoco") is None:
        import pytest
        pytest.skip("mujoco 未インストール")
    import bin_pick as BP
    if not os.path.exists(BP._PANDA_SCENE):
        import pytest
        pytest.skip("mujoco_menagerie(panda)未取得")
    out = str(tmp_path / "bin.gif")
    r = BP.render_bin_pick_gif(out, n_cubes=8, n_picks=3, width=320, height=240,
                               max_gif_frames=40, log=lambda *_: None)
    assert os.path.isfile(out) and os.path.getsize(out) > 0
    assert r["n_picked"] >= 2                                 # at least 2 of 3 attempts succeed


def test_walk_physics_op_registered():
    import unified as u
    assert "walk_physics" in u.ops


def test_walk_physics_is_dynamic(tmp_path):
    """go2 が本物の物理(mj_step+接触+重力)で自立して歩き、胴体が動的に傾く(運動学でない)。

    honest: 転倒すれば upright=False、傾きが出なければ dynamic=False を返す設計。"""
    import importlib.util
    import os
    if importlib.util.find_spec("mujoco") is None:
        import pytest
        pytest.skip("mujoco 未インストール")
    import walk_physics as WP
    if not os.path.exists(WP._GO2):
        import pytest
        pytest.skip("mujoco_menagerie(go2)未取得")
    out = str(tmp_path / "walk.gif")
    r = WP.run_walk_physics(out, secs=3.0, width=200, height=150, max_gif_frames=20,
                            log=lambda *_: None)
    assert os.path.isfile(out) and os.path.getsize(out) > 0
    assert r["upright"] is True                              # stayed up under real dynamics
    assert r["dynamic"] is True                              # body genuinely tilts (CoM shifts)
    assert r["mean_contacts"] > 1.0                          # real foot–terrain contacts


def test_jump_physics_op_registered():
    import unified as u
    assert "jump_physics" in u.ops


def test_jump_physics_leaves_ground(tmp_path):
    """go2 が本物の物理でジャンプし、全足が地面を離れる弾道飛行(接触0)を実測で示す。

    honest: 跳べなければ left_ground=False。摩擦・重力・接触は mj_step が解く。"""
    import importlib.util
    import os
    if importlib.util.find_spec("mujoco") is None:
        import pytest
        pytest.skip("mujoco 未インストール")
    import walk_physics as WP
    if not os.path.exists(WP._GO2):
        import pytest
        pytest.skip("mujoco_menagerie(go2)未取得")
    out = str(tmp_path / "jump.gif")
    r = WP.run_jump_physics(out, width=200, height=150, max_gif_frames=20, log=lambda *_: None)
    assert os.path.isfile(out) and os.path.getsize(out) > 0
    assert r["left_ground"] is True                          # genuine ballistic flight
    assert r["airtime_s"] > 0.1 and r["jump_height_m"] > 0.1


def test_hurdle_physics_op_registered():
    import unified as u
    assert "hurdle_physics" in u.ops


def test_hurdle_physics_clears_barrier(tmp_path):
    """go2 が助走→物理ジャンプで障害物を越え、向こう側に自立着地する(実測)。"""
    import importlib.util
    import os
    if importlib.util.find_spec("mujoco") is None:
        import pytest
        pytest.skip("mujoco 未インストール")
    import walk_physics as WP
    if not os.path.exists(WP._GO2):
        import pytest
        pytest.skip("mujoco_menagerie(go2)未取得")
    out = str(tmp_path / "hurdle.gif")
    r = WP.run_hurdle_physics(out, width=200, height=150, max_gif_frames=20, log=lambda *_: None)
    assert os.path.isfile(out) and os.path.getsize(out) > 0
    assert r["success"] is True and r["cleared"] is True and r["upright"] is True
