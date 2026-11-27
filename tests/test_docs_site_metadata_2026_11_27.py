"""公開文書の題・説明・言語を、Jekyll の入力側で検査する。

Validate page titles, descriptions, and languages before Jekyll renders the public site.
"""
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
LANGS = {"ja", "en", "zh", "zh-CN", "tw", "zh-Hant", "ko", "de", "hi", "fr"}


def _front_matter(path: Path) -> dict[str, str]:
    """先頭の YAML を単純な文字列値として読む。 / Read scalar YAML front matter."""
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), path
    _empty, raw, _body = text.split("---\n", 2)
    values = {}
    for line in raw.splitlines():
        match = re.match(r"([a-z]+):\s*[\"']?(.*?)[\"']?$", line)
        if match:
            values[match.group(1)] = match.group(2)
    return values


def test_visitor_entry_docs_have_page_specific_metadata():
    """入口の翻訳を同じ ``fullseye`` 題へ戻さない。 / Keep translated entry pages distinct."""
    pages = []
    for stem in ("README", "GETTING_STARTED", "INSTALL", "STUDIO_GUIDE"):
        pages.extend(DOCS.glob(stem + ".md"))
        pages.extend(DOCS.glob(stem + ".*.md"))
    assert len(pages) == 27
    for page in pages:
        meta = _front_matter(page)
        assert meta.get("title") and meta["title"].lower() != "fullseye", page
        assert meta.get("description") and len(meta["description"]) >= 20, page
        assert meta.get("lang") in LANGS, page


def test_custom_layout_uses_each_pages_language():
    """テーマ既定の英語へ倒さない。 / Do not fall back to the theme's English language."""
    layout = (DOCS / "_layouts" / "default.html").read_text(encoding="utf-8")
    assert '<html lang="{{ page_lang }}">' in layout
    for marker in (".en.", ".zh.", ".tw.", ".ko.", ".de.", ".hi.", ".fr."):
        assert marker in layout


def test_site_metadata_enables_sitemap_and_names_robots_target():
    """検索用の入口を配信対象に保つ。 / Keep crawler entry points in the published source."""
    config = (DOCS / "_config.yml").read_text(encoding="utf-8")
    assert "jekyll-sitemap" in config
    robots = (DOCS / "robots.txt").read_text(encoding="utf-8")
    assert "Sitemap: https://furuse.work/sitemap.xml" in robots
