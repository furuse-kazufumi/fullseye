"""統一視覚 I/F(unified.py)の回帰テスト — F1/F2/F3/F7 を守る。"""
from __future__ import annotations

import warnings

import numpy as np
import pytest

warnings.simplefilter("ignore")

import unified as u  # noqa: E402


def test_registry_builds_all_layers():
    """F2: 3 層(facade / 進化 / 知覚)が単一 registry に統合される。"""
    assert len(u.ops) >= 1400
    st = u.ops.stats()
    assert st["total"] == len(u.ops)
    assert st["namespaces"] >= 30
    prov = st["by_provenance"]
    assert prov.get("facade", 0) >= 590
    assert prov.get("evolution", 0) >= 700
    assert prov.get("perception", 0) >= 150


def test_every_op_has_metadata():
    """F3: 全 op が name/namespace/chapter/doc/render_hint/provenance/params を持つ。"""
    valid_hints = {"image", "region", "contour", "pose", "point_cloud",
                   "matches", "scalar", "matrix"}
    valid_prov = {"facade", "evolution", "perception", "oss-adapter"}
    for name in u.ops.list():
        d = u.ops.describe(name)
        assert d["name"] == name
        assert d["namespace"] and d["chapter"]
        assert d["render_hint"] in valid_hints
        assert d["provenance"] in valid_prov
        assert "signature" in d and d["signature"].startswith(name + "(")


def test_all_ops_resolve_to_callables():
    """F3: 全 op の func が実在の callable(facade 解決)。"""
    for name in u.ops.list():
        assert callable(u.ops[name])


def test_namespaces_exposed_as_attributes():
    """F1: 章別名前空間が module 属性として公開される。"""
    for ns in u.ops.namespaces():
        assert hasattr(u, ns)
        obj = getattr(u, ns)
        # 名前空間の各 op が属性アクセスで取れる
        for name in u.ops.list(namespace=ns)[:3]:
            assert getattr(obj, name) is u.ops[name]


def test_find_search():
    """F2: 名前/doc/章の全文検索。"""
    assert any(o.name == "camera_calibration" for o in u.ops.find("calibration"))
    assert any(o.name == "gen_circle_contour_xld" for o in u.ops.find("circle"))
    assert u.ops.find("この文字列は存在しないはず_xyzzy") == []


def test_f1_natural_call_contour():
    """F1: 名前空間経由で genuine 実装が実行される(輪郭)。"""
    c = u.contour.gen_circle_contour_xld(row=50, col=50, radius=10, n=40)
    arr = c["cs"][0]
    assert arr.shape == (40, 2)
    d = np.hypot(arr[:, 0] - 50, arr[:, 1] - 50)
    assert np.allclose(d, 10, atol=1e-6)


def test_f1_natural_call_calib():
    """F1: Zhang 校正が名前空間経由で真値を復元。"""
    import calib as C
    obj = np.array([[x, y] for x in range(5) for y in range(5)], float) * 0.05
    Ktrue = np.array([[700, 0, 100], [0, 700, 100], [0, 0, 1.0]])
    views = []
    for k in range(8):
        R = C._axis_to_rot(np.array([0.2 * np.sin(k), 0.1 * k, 0.05]))
        t = np.array([0.05, 0.1 * k - 0.3, 1.5 + 0.1 * k])
        P = np.column_stack([obj, np.zeros(len(obj))]) @ R.T + t
        uv = P @ Ktrue.T
        views.append(uv[:, :2] / uv[:, 2:3])
    K = u.calib.camera_calibration(obj, views)
    assert abs(K["fx"] - 700) < 10 and abs(K["cx"] - 100) < 10


def test_unknown_op_raises_helpful():
    """F1: 未知 op はヒント付きで AttributeError。"""
    with pytest.raises(AttributeError):
        u.contour.no_such_operator_zzz(1, 2)


def test_backward_compat_fullseye_package():
    """F7: fullseye パッケージ経由でも到達でき、進化 registry と共存。"""
    import fullseye as fs
    assert hasattr(fs, "vision") and hasattr(fs, "vision_ops")
    assert len(fs.vision_ops) == len(u.ops)
    assert len(fs.REGISTRY) > 0             # 進化 registry 健在
    c = fs.vision.contour.gen_circle_contour_xld(row=10, col=10, radius=5, n=12)
    assert c["cs"][0].shape == (12, 2)
