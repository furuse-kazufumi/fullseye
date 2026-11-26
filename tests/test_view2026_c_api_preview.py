# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ViEW2026 冒頭の C/C++ API(プレビュー)案内を、C SDK 台帳と照合する。"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = ROOT / "tools" / "gen_view2026_pages.py"
SPEC = importlib.util.spec_from_file_location("gen_view2026_pages_c_api_preview", GENERATOR_PATH)
G = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(G)

C_API_OPS = ROOT / "fullseye" / "data" / "C_API_OPS.json"
LANGS = ("ja", "en", "zh", "tw", "ko", "de", "hi", "fr")


def test_c_api_preview_is_below_the_about_paragraph_in_all_languages() -> None:
    data = G.load()
    assert tuple(data["langs"]) == LANGS
    for lang in LANGS:
        ui = {key: value[lang] for key, value in data["ui"].items()}
        page = G.build(data, lang)
        intro = page[page.index('<div class="vintro">'):page.index("</div></div>", page.index('<div class="vintro">'))]
        line = G._esc(ui["c_api_preview"].replace("{n_c_api}", str(G.c_api_callable_count())))
        assert intro.index(G._esc(ui["about"])) < intro.index(line), lang
        assert intro.count('href="%s"' % G.C_API_DOC_URL) == 1, lang
        assert 'href="C_API.md"' not in intro, lang


def test_c_api_preview_count_matches_the_generated_c_sdk_ledger() -> None:
    if not C_API_OPS.is_file():
        pytest.skip("C_API_OPS.json is added by the C API PR")
    ledger = json.loads(C_API_OPS.read_text(encoding="utf-8"))
    expected = ledger["n_callable"]
    assert expected == sum(row["callable"] for row in ledger["ops"])
    assert G.c_api_callable_count() == expected
    data = G.load()
    for lang in LANGS:
        text = data["ui"]["c_api_preview"][lang]
        # 数は手で書かない: 差し込み口が 1 つで、ほかに数字は無い(pybind11 は名前なので除く)
        assert text.count("{n_c_api}") == 1, lang
        assert re.findall(r"\d+", text.replace("pybind11", "")) == [], lang
        page = G.build(data, lang)
        intro = page[page.index('<div class="vintro">'):page.index("</div></div>", page.index('<div class="vintro">'))]
        assert "{n_c_api}" not in page, lang
        line = G._esc(text.replace("{n_c_api}", str(expected)))
        assert line in intro and str(expected) in line, (lang, expected)
