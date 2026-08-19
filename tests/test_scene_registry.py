"""scene_registry(モデル一元管理)の回帰。gsplat/GPU 不要(os/json のみ)。"""
from __future__ import annotations
import os
import scene_registry as R


def test_list_has_builtins():
    names = R.names()
    assert {"demo", "go2", "evis"}.issubset(names)


def test_list_shape():
    rows = R.entries()
    assert all(len(t) == 3 for t in rows)          # (name, spec, available)


def test_resolve_demo_is_loadable_xml():
    """demo は外部依存ゼロ。解決すると実在する .xml を返す。"""
    s = R.resolve("demo")
    assert s and os.path.isfile(s["xml"]) and s["xml"].endswith(".xml")
    assert "lookat" in s and "radius" in s and "elevation_deg" in s


def test_resolve_unknown_is_none():
    assert R.resolve("no-such-scene") is None


def test_resolve_xml_path_passthrough(tmp_path):
    p = tmp_path / "s.xml"; p.write_text("<mujoco/>", encoding="utf-8")
    s = R.resolve(str(p))
    assert s and s["xml"] == str(p)


def test_register_and_motion(tmp_path):
    traj = tmp_path / "m.npy"; traj.write_bytes(b"x")
    R.register("unittest_scene", xml="none.xml", category="test",
               motions={"walk": str(traj)})
    assert "unittest_scene" in R.names()
    assert R.motion("unittest_scene", "walk") == str(traj)
    assert R.motion("unittest_scene", "nope") is None


def test_evis_registered_with_walk():
    """evis はレジストリに存在し walk モーションを持つ(ファイル有無に関わらず定義は在る)。"""
    assert "evis" in R.names()
    assert "walk" in R._CATALOG["evis"].get("motions", {})
