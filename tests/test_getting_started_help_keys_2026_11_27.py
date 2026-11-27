"""GETTING_STARTEDのヘルプキーをStudioの実割り当てに合わせる。

Keep the localized help-key guidance aligned with the Studio key map.
"""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PAGES = [DOCS / "GETTING_STARTED.md"] + sorted(DOCS.glob("GETTING_STARTED.*.md"))


def test_help_keys_match_the_studio_keymap():
    keymap = (ROOT / "studio_keymap.py").read_text(encoding="utf-8")
    assert '_c("help_here", "Help here", _W, "F1"' in keymap
    assert '_c("shortcuts", "Keyboard shortcuts", _W, "Ctrl+F1"' in keymap
    assert len(PAGES) == 7
    for page in PAGES:
        text = page.read_text(encoding="utf-8")
        normalized = text.replace("Strg+F1", "Ctrl+F1")
        assert "**Ctrl+F1**" in normalized, page.name
        assert "**F1**" in normalized, page.name
