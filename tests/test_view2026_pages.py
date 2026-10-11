# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ViEW2026 案内ページ(論文の QR の行き先)の生成器の門。

★2026-10-11: ページは PoC しか載せておらず、「生成 AI の画像の文字を直す」のような
PoC でない機能(``docs/capabilities/``)は QR の先から辿れなかった(ユーザー指摘)。
ここでは「説明のページが 1 件残らず全言語のページに載る」ことと、検査が**本当に**
漏れを止めること(壊して確かめる)を見る。
"""
from __future__ import annotations

import copy
import importlib.util
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "gen_view2026_pages", os.path.join(ROOT, "tools", "gen_view2026_pages.py"))
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)


def test_committed_pages_are_current():
    assert G.main(["--check"]) == 0


def test_every_capability_doc_is_on_every_page():
    caps = G.capabilities()
    assert len(caps) >= 30, "docs/capabilities/ の件数が縮んでいる"
    d = G.load()
    langs = d["langs"]
    assert len(langs) == 7
    for lang in langs:
        page = G.build(d, lang)
        missing = [c["id"] for c in caps if "capabilities/%s.md" % c["id"] not in page]
        assert not missing, "%s: 載っていない説明がある: %s" % (lang, missing)
        assert "fix_text_in_image" in page, "%s: 生成画像の文字を直す例が辿れない" % lang


def test_other_examples_are_counted_not_typed():
    n = G.other_example_count()
    assert n > 50
    page = G.build(G.load(), "ja")
    assert ("PoC 以外の使用例 %d 本" % n) in page


def test_a_missing_translation_stops_the_generator():
    d = G.load()
    assert G.validate(d) == []
    broken = copy.deepcopy(d)
    cid = sorted(broken["capabilities"]["titles"])[0]
    del broken["capabilities"]["titles"][cid]
    bad = G.validate(broken)
    assert bad
    assert any(cid in b for b in bad), bad


def test_a_stale_translation_stops_the_generator():
    broken = copy.deepcopy(G.load())
    broken["capabilities"]["titles"]["no-such-capability"] = {"zh": "x"}
    bad = G.validate(broken)
    assert bad
    assert any("no-such-capability" in b for b in bad)


def test_a_missing_example_stops_the_generator(monkeypatch):
    real = G.capabilities()
    assert real
    fake = copy.deepcopy(real)
    fake[0]["examples"] = ["no_such_example_script"]
    monkeypatch.setattr(G, "capabilities", lambda: fake)
    bad = G.validate(G.load())
    assert bad
    assert any("no_such_example_script" in b for b in bad)


def test_japanese_only_docs_are_marked_on_other_languages():
    d = G.load()
    page = G.build(d, "en")
    lines = [ln for ln in page.splitlines() if "/capabilities/" in ln]
    assert lines
    assert all(G.JA_MARK in ln for ln in lines)
