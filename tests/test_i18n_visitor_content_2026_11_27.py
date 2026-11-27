"""訪問者向け翻訳が正本の操作と導線を保つことを検査する。
Check that visitor-facing translations preserve current actions and navigation.
"""
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
LANGS = ("en", "zh", "tw", "ko", "de", "hi")
FAMILIES = ("GETTING_STARTED", "INSTALL", "STUDIO_GUIDE", "ENGINE")


def _translations(stem: str) -> list[Path]:
    return [DOCS / f"{stem}.{lang}.md" for lang in LANGS if (DOCS / f"{stem}.{lang}.md").is_file()]


def test_rag_translations_include_the_op_graph_contract():
    for path in _translations("AI_RAG_GUIDE"):
        text = path.read_text(encoding="utf-8")
        assert 'constraints={"executable_only": false}' in text, path.name
        assert "docs/op_knob.json" in text, path.name


def test_german_studio_shortcuts_match_the_current_actions():
    text = (DOCS / "STUDIO_GUIDE.de.md").read_text(encoding="utf-8")
    assert "Synthetic demo (Strg+D)" not in text
    assert "1:1 (Strg+Alt+1)" in text
    assert "3D surface (Strg+Alt+3)" in text


def test_translated_guides_link_to_an_available_translation():
    suffix = re.compile(r"\.(?:en|zh|tw|ko|de|hi)\.md$")
    links = re.compile(r"\[[^]]+\]\(([^)#?]+\.md)(?:#[^)]*)?\)")
    for family in FAMILIES:
        for path in _translations(family):
            lang = path.name.rsplit(".", 2)[1]
            for line in path.read_text(encoding="utf-8").splitlines()[12:]:
                for destination in links.findall(line):
                    if suffix.search(destination):
                        continue
                    target = (path.parent / destination).resolve()
                    localized = target.with_name(f"{target.stem}.{lang}{target.suffix}")
                    assert not localized.is_file(), (path.name, destination, localized.name)


def test_install_shows_the_literal_message_the_program_prints():
    literal = "スタートメニューに Fullseye Studio を登録しました"
    pages = [DOCS / "INSTALL.md", *_translations("INSTALL")]
    assert len(pages) == 7
    for path in pages:
        assert literal in path.read_text(encoding="utf-8"), path.name


def test_every_readme_has_setup_and_uninstall_entry_points():
    pages = sorted(DOCS.glob("README*.md"))
    assert len(pages) == 6
    for path in pages:
        text = path.read_text(encoding="utf-8")
        assert "fullseye setup" in text, path.name
        assert "fullseye setup --uninstall" in text, path.name
        assert "fullseye[gui]" not in text, path.name
    korean = (DOCS / "README.ko.md").read_text(encoding="utf-8")
    assert "타입 원장" in korean
    assert "타입 台帳" not in korean


def test_english_operational_tables_keep_safety_significant_literals():
    chain = (DOCS / "CHAIN_FUZZ.en.md").read_text(encoding="utf-8")
    troubleshooting = (DOCS / "TROUBLESHOOTING.en.md").read_text(encoding="utf-8")
    assert "| wave-6 | **non-CONTRACT 0** |" in chain
    assert "`File name too long`" in troubleshooting
    assert "`--trusted-host`" in troubleshooting
