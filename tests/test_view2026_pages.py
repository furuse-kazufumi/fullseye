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
import json
import os
import re

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
    assert langs[0] == "ja" and len(langs) >= 7   # 言語を足しても通る(ja が先頭、既存の 7 言語は残る)
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


def test_every_highlight_has_lead_in_all_languages_and_renders_it_first():
    d = G.load()
    assert len(d["exhibits"]) >= 13, "目玉展示の件数が縮んでいる"
    assert len(d["langs"]) >= 7, "目玉展示の対応言語が縮んでいる"
    ledger = {
        e["id"]: e for e in json.loads(
            (G.ROOT / d["all_source"]).read_text(encoding="utf-8"))["exhibits"]
    }
    for exhibit in d["exhibits"]:
        assert set(exhibit["lead"]) == set(d["langs"]), exhibit["id"]
        assert all(exhibit["lead"][lang].strip() for lang in d["langs"]), exhibit["id"]
        source = ledger.get(exhibit["id"])
        if source:
            expected_ja = source["lead_ja"] or source["caption_ja"]
            expected_en = source["lead_en"] or source["caption_en"]
            if not source["lead_en"] and re.search(r"[\u3040-\u30ff]", expected_en):
                expected_en += " _(ja)_"
            assert exhibit["lead"]["ja"] == expected_ja
            assert exhibit["lead"]["en"] == expected_en
            for lang in d["langs"][2:]:
                assert exhibit["lead"][lang] == expected_en

    page = G.build(d, "ja")
    for exhibit in d["exhibits"]:
        marker = "- [%s]" % exhibit["label"]["ja"]
        start = page.index(marker)
        end = page.find("\n- [", start + len(marker))
        block = page[start:end if end >= 0 else None]
        lead_at = block.index(exhibit["lead"]["ja"])
        see_at = block.find(exhibit["see"]["ja"], lead_at + len(exhibit["lead"]["ja"]))
        assert lead_at < see_at, exhibit["id"]


def test_a_missing_translation_stops_the_generator():
    d = G.load()
    assert G.validate(d) == []
    broken = copy.deepcopy(d)
    cid = sorted(broken["capabilities"]["titles"])[0]
    del broken["capabilities"]["titles"][cid]
    bad = G.validate(broken)
    assert bad
    assert any(cid in b for b in bad), bad


def test_youtube_is_hidden_when_empty_and_invalid_urls_stop_generation():
    d = G.load()
    assert len(d["exhibits"]) >= 100
    assert all("youtube_url" in e for e in d["exhibits"])
    assert "[YouTube](" not in G.build(d, "en")
    broken = copy.deepcopy(d)
    broken["exhibits"][0]["youtube_url"] = "https://example.invalid/static.mp4"
    bad = G.validate(broken)
    assert len(bad) >= 1
    assert any("YouTube" in x for x in bad)


def test_a_stale_translation_stops_the_generator():
    broken = copy.deepcopy(G.load())
    broken["capabilities"]["titles"]["no-such-capability"] = {"zh": "x"}
    bad = G.validate(broken)
    assert bad
    assert any("no-such-capability" in b for b in bad)


def test_a_one_character_change_to_a_ledger_caption_stops_the_generator():
    broken = copy.deepcopy(G.load())
    item = next(e for e in broken["exhibits"] if "numbers_source" in e)
    item["see"]["ja"] += "改"
    bad = G.validate(broken)
    assert len(bad) >= 1
    assert any(item["id"] in message and "逐語一致" in message for message in bad), bad


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
