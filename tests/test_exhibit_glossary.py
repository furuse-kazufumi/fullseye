# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""展示の専門用語集、抽出辞書、生成ページを一緒に守る門。"""
from __future__ import annotations

import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
sys.path.insert(0, TOOLS)

import exhibit_glossary as G

_spec = importlib.util.spec_from_file_location(
    "gen_view2026_pages_for_glossary", os.path.join(TOOLS, "gen_view2026_pages.py"))
VIEW = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(VIEW)


def _ledger() -> list[dict]:
    return json.loads(G.LEDGER.read_text(encoding="utf-8"))["exhibits"]


def test_glossary_schema_length_and_review_count(capsys):
    glossary = G.load_glossary()
    assert len(glossary) >= 56, "用語集が縮んでいる"
    for term_id, entry in glossary.items():
        assert {"match", "ja", "en", "source", "review"} <= set(entry), term_id
        assert all(k in {"match", "ja", "en", "source", "review"} or
                   (len(k) == 2 and k.isalpha()) for k in entry), term_id
        assert entry["match"] and all(isinstance(x, str) and x.strip() for x in entry["match"]), term_id
        for field in ("ja", "en", "source"):
            assert isinstance(entry[field], str) and entry[field].strip(), (term_id, field)
            assert len(G.sentences(entry[field])) <= 2, "%s.%s は3文以上" % (term_id, field)
        assert isinstance(entry["review"], bool), term_id
    reviews = [term_id for term_id, entry in glossary.items() if entry["review"]]
    print("glossary review:true = %d: %s" % (len(reviews), ", ".join(reviews)))
    assert "review:true" in capsys.readouterr().out


def test_every_candidate_in_the_opening_has_a_definition():
    glossary = G.load_glossary()
    missing = {}
    for exhibit in _ledger():
        for lang in ("ja", "en"):
            for term_id in G.candidate_hits(exhibit, lang):
                if term_id not in glossary:
                    missing.setdefault(term_id, []).append("%s[%s]" % (exhibit["id"], lang))
    assert not missing, "冒頭に出るのに未定義の用語: %s" % missing


def test_glossary_has_no_dead_entries():
    glossary = G.load_glossary()
    used = set()
    for exhibit in _ledger():
        for lang in ("ja", "en"):
            used.update(term_id for term_id, _entry in G.terms_for_exhibit(exhibit, lang, glossary, 999))
    dead = sorted(set(glossary) - used)
    assert not dead, "台帳の題・冒頭2文に無い死にエントリ: %s" % dead


def test_every_view_exhibit_with_terms_gets_a_term_line_in_every_language():
    data = VIEW.load()
    public = VIEW.public_data(data)
    glossary = G.load_glossary()
    ledger = {e["id"]: e for e in _ledger()}
    for lang in data["langs"]:
        expected = sum(bool(G.terms_for_exhibit(ledger[e["id"]], lang, glossary))
                       for e in public["exhibits"] if e["id"] in ledger)
        assert expected >= 60, "%s: 用語を含む公開展示が %d 本まで減った" % (lang, expected)
        pages = [VIEW.build(data, lang)]
        if lang in ("ja", "en"):
            pages.append(VIEW.build_more(data, lang))
        label = "  用語:" if lang == "ja" else "  Terms:"
        actual = sum(line.startswith(label) for page in pages for line in page.splitlines())
        assert actual >= expected, "%s: 用語行 %d / 用語を含む展示 %d" % (lang, actual, expected)


def test_sam_homographs_are_separate_and_gallery_can_render_terms():
    glossary = G.load_glossary()
    ledger = {e["id"]: e for e in _ledger()}
    spectral = G.terms_for_exhibit(ledger["poc_recycling_sorting"], "en", glossary)
    acoustic = G.terms_for_exhibit(ledger["poc_sam_hybrid_bonding_voids"], "en", glossary)
    assert "sam_spectral" in {x for x, _ in spectral}
    assert "sam_ultrasonic" not in {x for x, _ in spectral}
    assert "sam_ultrasonic" in {x for x, _ in acoustic}
    assert "sam_spectral" not in {x for x, _ in acoustic}
    assert G.glossary_line(ledger["poc_recycling_sorting"], "ja", glossary).startswith("用語:")
    assert G.glossary_line(ledger["poc_recycling_sorting"], "en", glossary).startswith("Terms:")


def test_airy_pattern_and_multiple_reflection_formula_are_separate():
    glossary = G.load_glossary()
    ledger = {e["id"]: e for e in _ledger()}
    pattern = G.terms_for_exhibit(ledger["poc_zoom_configurations"], "en", glossary, 999)
    formula = G.terms_for_exhibit(ledger["poc_sam_hybrid_bonding_voids"], "en", glossary, 999)
    assert "airy_pattern" in {term_id for term_id, _entry in pattern}
    assert "airy_formula" not in {term_id for term_id, _entry in pattern}
    assert "airy_formula" in {term_id for term_id, _entry in formula}
    assert "airy_pattern" not in {term_id for term_id, _entry in formula}
