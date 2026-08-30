"""unified facade データの同梱と graceful degradation のテスト。
Tests that the facade data ships with the package and that a missing
data file degrades gracefully instead of killing ``import fullseye``.

背景(公開前監査で確定したバグ): 以前は facade データが gitignore された
dev キャッシュ ``data/`` にしか無く、クリーン checkout / wheel install で
``import fullseye`` が FileNotFoundError で全滅していた。正本を
``fullseye/data/``(git 追跡+wheel 同梱)へ移し、ロードを fail-soft 化した。
"""
import json
import warnings
from pathlib import Path

import unified

_REPO = Path(__file__).resolve().parents[1]


def test_shipped_facade_data_exists_and_parses():
    """正本 fullseye/data/ の 2 ファイルが存在し、中身が妥当(CI 不変条件)。"""
    fac = _REPO / "fullseye" / "data" / "halcon_facade_map.json"
    stubs = _REPO / "fullseye" / "data" / "halcon_stubs.json"
    assert fac.is_file() and stubs.is_file()
    facade = json.loads(fac.read_text(encoding="utf-8"))
    ops = {k: v for k, v in facade.items() if not k.startswith("_")}
    assert len(ops) >= 500          # 「600 facade op」の主張が空洞化していないこと
    assert "operators" in json.loads(stubs.read_text(encoding="utf-8"))


def test_missing_facade_data_degrades_gracefully(monkeypatch):
    """データ欠落 = facade 層だけ警告付きスキップ(raise しない)。"""
    monkeypatch.setattr(unified, "_FACADE", str(_REPO / "no" / "such.json"))
    monkeypatch.setattr(unified, "_STUBS", str(_REPO / "no" / "such2.json"))
    reg = unified.Registry()
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        unified._load_facade(reg)   # ← 以前はここで FileNotFoundError
    assert any(issubclass(x.category, RuntimeWarning) for x in w)
    assert len(reg.all()) == 0 if hasattr(reg, "all") else True


def test_data_file_resolution_prefers_shipped_copy():
    """_data_file は同梱正本(fullseye/data)を第一候補にする。"""
    p = unified._data_file("halcon_facade_map.json")
    assert Path(p).is_file()
    assert "fullseye" in Path(p).parts
