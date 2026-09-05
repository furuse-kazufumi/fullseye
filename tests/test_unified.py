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
                   "matches", "scalar", "matrix",
                   "mesh", "gaussians", "dataset", "animation"}   # 3DGS/SuGaR 出力種別
    valid_prov = {"facade", "evolution", "perception", "oss-adapter", "sim-source", "3dgs"}
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
    """F1: Zhang 校正が名前空間経由で真値を復元。

    image points are (row, col) — the convention of every calib API (2026-09-02:
    this test used to hand-build (x, y) points; with fx=fy, cx=cy the swap was
    invisible, so the truth is now asymmetric to pin the axes)."""
    import calib as C
    obj = np.array([[x, y] for x in range(5) for y in range(5)], float) * 0.05
    Ktrue = np.array([[700, 0, 100], [0, 650, 120], [0, 0, 1.0]])
    views = []
    for k in range(8):
        R = C._axis_to_rot(np.array([0.2 * np.sin(k), 0.1 * k, 0.05]))
        t = np.array([0.05, 0.1 * k - 0.3, 1.5 + 0.1 * k])
        P = np.column_stack([obj, np.zeros(len(obj))]) @ R.T + t
        uv = P @ Ktrue.T
        xy = uv[:, :2] / uv[:, 2:3]
        views.append(xy[:, ::-1])                      # (x, y) -> (row, col)
    K = u.calib.camera_calibration(obj, views)
    assert abs(K["fx"] - 700) < 1 and abs(K["fy"] - 650) < 1
    assert abs(K["cx"] - 100) < 1 and abs(K["cy"] - 120) < 1


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


def test_every_facade_reference_actually_imports():
    """facade map の**全参照が実際に解決する**こと(黙って欠ける経路を塞ぐ)。

    ``_load_facade`` は import に失敗した参照を ``except Exception: continue`` で
    握りつぶす。設計としては正しい(データ 1 行の綻びで層ごと落とさない)が、その
    ぶん**永久に解決しない参照が無言で減るだけ**になる ―― 落ちないので誰も気づかない。

    2026-09-05 の実測: `color_pca.py` を「どこからも import されていない死んだ
    モジュール」と判断して削除したところ、facade は 600 → **589** へ静かに減った。
    実体は HALCON facade 11 op(``create_color_trans_lut`` / ``inpainting_ced`` /
    ``inpainting_mcf`` / ``inpainting_texture`` / ``exhaustive_match_mg`` /
    ``gen_principal_comp_trans`` / ``gen_canonical_variates_trans`` …)の中身だった。
    `ops.REGISTRY` にはひとつも登録されないので、**そちらだけを見ると死んで見える**。

    さらに `color_pca` は ``py-modules`` に無かったので、**pip install した wheel では
    もともとこの 11 op が消えていた**(リポジトリでだけ通る、を検査が見逃していた)。
    数の閾値(>= 590)ではなく、**参照そのものの解決**を検査する。
    """
    import json
    import os
    with open(u._FACADE, encoding="utf-8") as f:
        facade = json.load(f)
    refs = {k: v for k, v in facade.items() if not k.startswith("_")}
    broken = {}
    for name, ref in sorted(refs.items()):
        try:
            u._import(ref)
        except Exception as e:                       # noqa: BLE001 — 何が壊れたかを出す
            broken[name] = "%s (%s: %s)" % (ref, type(e).__name__, e)
    assert not broken, (
        "facade map の参照が %d 件解決しない —— _load_facade は例外を握るので "
        "op が黙って消えるだけになる:\n" % len(broken)
        + "\n".join("  %s -> %s" % kv for kv in sorted(broken.items())[:20]))
    assert u.ops.stats()["by_provenance"]["facade"] == len(refs), (
        "解決したのに registry に載っていない facade op がある")


def test_facade_module_dependencies_ship_in_the_wheel():
    """facade map が指す**ルート直下のモジュールが py-modules に載っている**こと。

    リポジトリでは import できるのに wheel には入っていない、という取りこぼしを
    塞ぐ(``color_pca`` が実際にそれだった)。``fullseye/`` パッケージ配下の参照は
    packages で運ばれるのでここでは見ない。
    """
    import json
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(u._FACADE, encoding="utf-8") as f:
        facade = json.load(f)
    mods = {str(v).split(".")[0] for k, v in facade.items() if not k.startswith("_")}
    with open(os.path.join(root, "pyproject.toml"), encoding="utf-8") as f:
        toml = f.read()
    py_modules = toml.split("py-modules = [", 1)[1].split("\n]", 1)[0]
    missing = sorted(m for m in mods
                     if os.path.exists(os.path.join(root, m + ".py"))
                     and ('"%s"' % m) not in py_modules)
    assert not missing, (
        "facade が使うルートモジュールが py-modules に無い(wheel でその op が黙って"
        "消える): " + ", ".join(missing))
