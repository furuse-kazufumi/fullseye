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
