"""fullseye_3dgs ランチャの非GPU部分(scene解決/preset/builtin)の回帰。"""
from __future__ import annotations
import os
import fullseye_3dgs as F


def test_presets_shape():
    for k in ("fast", "balanced", "high"):
        res, ng, it, nv = F.PRESETS[k]
        assert res > 0 and ng > 0 and it > 0 and nv > 0
    assert F.PRESETS["high"][0] > F.PRESETS["fast"][0]     # high の方が高解像


def test_resolve_builtin():
    r = F.resolve_scene("go2")
    assert r is not None and r[0].endswith(".xml")


def test_resolve_unknown_is_none():
    assert F.resolve_scene("does-not-exist") is None


def test_resolve_xml_path(tmp_path):
    p = tmp_path / "s.xml"; p.write_text("<mujoco/>", encoding="utf-8")
    r = F.resolve_scene(str(p))
    assert r is not None and r[0] == str(p)


def test_builtins_registered():
    assert set(["go2", "cassie", "apollo"]).issubset(F.BUILTIN)
