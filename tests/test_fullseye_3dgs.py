"""fullseye_3dgs ランチャの非GPU部分(preset)の回帰。scene 解決は scene_registry に移設。"""
from __future__ import annotations
import fullseye_3dgs as F
import scene_registry as R


def test_presets_shape():
    for k in ("fast", "balanced", "high"):
        res, ng, it, nv = F.PRESETS[k]
        assert res > 0 and ng > 0 and it > 0 and nv > 0
    assert F.PRESETS["high"][0] > F.PRESETS["fast"][0]     # high の方が高解像


def test_scene_resolution_via_registry():
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
