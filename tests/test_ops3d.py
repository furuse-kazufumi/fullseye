"""ops3d レジストリの健全性: 全 op が実体を持ち、カテゴリ/型連結が一貫。"""
import pytest
pytest.importorskip("torch")
import ops3d


def _size_floor(key):
    """``docs/COLLECTION_SIZES.json`` の記録値(床を 1 か所に集める)。

    ★2026-09-08 まで、ここは「昔の小さい定数」だった。台帳と門の詳細は
    ``tests/test_collection_sizes.py``。
    """
    import json as _json
    import os as _os
    _p = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                       "..", "docs", "COLLECTION_SIZES.json")
    with open(_p, encoding="utf-8") as _fh:
        return _json.load(_fh)["sizes"][key]


def test_all_ops_resolve():
    """レジストリの全 op が実体(callable)を持つ(欠損なし)。"""
    assert ops3d.missing() == []
    assert len(ops3d.OPS3D) >= _size_floor("ops3d.OPS3D")
    for name, m in ops3d.OPS3D.items():
        assert callable(m["func"]), f"{name} が callable でない"
        assert m["category"] in ops3d.categories()


def test_op_chaining_discovery():
    """op×op 連結: 出力種別が別 op の入力になる後続候補を型で発見できる。"""
    # points 出力 → points を入力に取る op が後続候補に出る
    nxt = ops3d.compatible("mesh_to_points")           # 出力=points
    assert "register_fpfh" in nxt or "icp_point2point_3d" in nxt
    # transform は全連結のハブ(後続が多い)
    assert len(ops3d.compatible("signed_distance_field")) > 0
