# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""``tools/fetch_realinsp_data.py`` の台帳と展開の門(ネットへは出ない)。

検査 PoC 4 本(ひび割れ幅・EL・金属粒度・織物)の実データは repo に入れず、この道具で取得して
バイト数と SHA-256 で固定する。ここでは台帳の形と、書庫の危険な名前を拒むことだけを見る。
"""
from __future__ import annotations

import importlib.util
import re
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _tool():
    spec = importlib.util.spec_from_file_location("fetch_realinsp_data", ROOT / "tools" / "fetch_realinsp_data.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_ledger_is_pinned_and_redistributable():
    mod = _tool()
    assert set(mod.DATASETS) == {"concrete_crack", "sipv_el", "tbm", "raw_fabrid"}
    for name, spec in mod.DATASETS.items():
        assert re.fullmatch(r"[0-9a-f]{64}", spec["sha256"]), name
        assert spec["bytes"] > 0, name
        assert spec["url"].startswith("https://"), name
        # 図に出すデータは再配布可のライセンスだけ(非商用 NC・研究限定は入れない)
        assert "NC" not in spec["license"] and "NonCommercial" not in spec["license"], name
        assert "4.0" in spec["license"], name
        for ex in spec.get("extra", []):
            assert re.fullmatch(r"[0-9a-f]{64}", ex["sha256"]) and ex["bytes"] > 0


def test_tbm_has_one_fetcher():
    """TBM の取得器は tools/fetch_tbm.py の 1 本(poc_real_grain_skiz と共用)。ここは台帳を読み込むだけ。"""
    mod = _tool()
    tbm = mod.DATASETS["tbm"]
    assert tbm["delegate"] == "fetch_tbm"
    assert (tbm["url"], tbm["bytes"], tbm["sha256"]) == (mod._TBM.TBM_URL, mod._TBM.TBM_BYTES, mod._TBM.TBM_SHA256)
    src = (ROOT / "tools" / "fetch_realinsp_data.py").read_text(encoding="utf-8")
    assert tbm["sha256"] not in src, "TBM の SHA-256 を 2 か所に書かない"


@pytest.mark.parametrize("bad", ["../x.png", "/etc/passwd", "a/../../b"])
def test_rejects_paths_outside_the_archive(bad):
    mod = _tool()
    with pytest.raises(SystemExit):
        mod._check_name(bad)


def test_zip_extract_filters_members_and_skips_junk(tmp_path):
    mod = _tool()
    arc = tmp_path / "a.zip"
    with zipfile.ZipFile(arc, "w") as zf:
        zf.writestr("TBM/input_image/1.png", b"x")
        zf.writestr("TBM/.DS_Store", b"junk")
        zf.writestr("__MACOSX/TBM/._1.png", b"junk")
        zf.writestr("other/2.png", b"y")
    out = tmp_path / "out"
    n = mod._extract_zip(arc, out, ("TBM/",))
    assert n == 1
    assert (out / "TBM" / "input_image" / "1.png").read_bytes() == b"x"
    assert not (out / "other").exists()


def test_offline_refuses_network(tmp_path, monkeypatch):
    mod = _tool()
    monkeypatch.setenv("FULLSEYE_OFFLINE", "1")
    monkeypatch.delenv("CI", raising=False)
    with pytest.raises(SystemExit):
        mod._fetch("https://example.invalid/x", tmp_path / "x.zip", 10, "0" * 64)
