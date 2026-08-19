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
