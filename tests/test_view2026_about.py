# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ViEW2026 の手書き読み物と、生成される入口リンクの門。"""
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VIEW = ROOT / "docs" / "view2026"
JA = VIEW / "about.md"
EN = VIEW / "en" / "about.md"


def _quote_blocks(text: str) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in text.splitlines():
        if line.startswith(">"):
            current.append(line)
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def test_english_preserves_the_japanese_document_structure():
    ja = JA.read_text(encoding="utf-8")
    en = EN.read_text(encoding="utf-8")

    ja_headings = re.findall(r"^#{1,6} .+$", ja, re.MULTILINE)
    en_headings = re.findall(r"^#{1,6} .+$", en, re.MULTILINE)
    assert len(en_headings) == len(ja_headings)
    assert re.findall(r"^## (0[1-6])", en, re.MULTILINE) == [
        "01", "02", "03", "04", "05", "06"]

    ja_table_rows = re.findall(r"^\|.*\|$", ja, re.MULTILINE)
    en_table_rows = re.findall(r"^\|.*\|$", en, re.MULTILINE)
    assert len(en_table_rows) == len(ja_table_rows)

    ja_quotes = _quote_blocks(ja)
    en_quotes = _quote_blocks(en)
    assert len(en_quotes) == len(ja_quotes)
    assert [len(block) for block in en_quotes] == [len(block) for block in ja_quotes]

    ja_lines = ja.splitlines()
    en_lines = en.splitlines()
    assert len(en_lines) == len(ja_lines)
    assert [("**" in line) for line in en_lines] == [("**" in line) for line in ja_lines]


def test_generated_index_links_point_to_the_handwritten_pages():
    expected = [
        (VIEW / "index.md", "Fullseye とは(読み物)", "about.html"),
        (VIEW / "en" / "index.md", "About Fullseye (reading)", "about.html"),
    ]
    for index, label, relative in expected:
        link = f'<a href="{relative}">{label}</a>'  # 冒頭の「Fullseye とは」の段落の末尾(HTML のかたまりの中なので <a>)
        assert link in index.read_text(encoding="utf-8")
        # 生の HTML の中のリンクは Jekyll が .md -> .html に書き換えない。配信される .html を指し、元の .md が在ること。
        assert (index.parent / relative.replace(".html", ".md")).is_file()

    for lang in ("de", "fr", "hi", "ko", "tw", "zh"):
        text = (VIEW / lang / "index.md").read_text(encoding="utf-8")
        assert "Fullseye とは(読み物)" not in text
        assert "About Fullseye (reading)" not in text


def test_raw_html_links_never_point_at_markdown_sources():
    """生の HTML(<a href> / <img src>)の中の相対リンクは Jekyll が .md -> .html に書き換えない。
    .md を指すと、配信は text/markdown の原文を返す(11/24、「Fullseye とは」と全言語の「くわしく」242 本)。
    docs/ の下の .md と .html を全部読み、相対の .md を指す生の HTML のリンクが 0 本であること。"""
    import re

    docs = VIEW.parent
    pat = re.compile(r"""(?:href|src)\s*=\s*["']([^"'#?]+\.md)(?:#[^"']*)?["']""", re.I)
    scanned = 0
    bad = []
    for path in docs.rglob("*"):
        if path.suffix.lower() not in (".md", ".html", ".htm") or not path.is_file():
            continue
        scanned += 1
        for m in pat.finditer(path.read_text(encoding="utf-8", errors="replace")):
            url = m.group(1)
            if re.match(r"[a-z][a-z0-9+.-]*://", url, re.I) or url.startswith("//"):
                continue
            bad.append(f"{path.relative_to(docs).as_posix()}: {url}")
    assert scanned > 1000, scanned  # 走査が黙って縮んでいないこと
    assert not bad, "\n".join(bad[:30])
