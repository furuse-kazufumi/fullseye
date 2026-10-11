# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""非日本語の README の手書きリンクは、訳があればその言語の版を指す(2026-10-11)。

各言語の docs/README.<lang>.md の「ここから始める」とガイド表は、韓国語版にも
GETTING_STARTED.ko.md があるのに日本語の GETTING_STARTED.md を指していた —— 入口で
いちばん押されるリンクが、読めない言語の文書を開いていた。英語のルート README も
CAPABILITIES.en.md / HARDENING.en.md があるのに日本語版を指していた。

生成ブロック(``<!-- x:start -->`` 〜 ``<!-- x:end -->``)の中は対象外: そこは文書の地図で、
原文(日本語)へのリンクと訳へのリンクを並べて出す設計(tools/gen_docs_index_ops.py)。
"""
from __future__ import annotations

import io
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
LINK = re.compile(r"\]\(((?:[\w./-]+/)?[\w-]+)\.md(?:#[^)]*)?\)")
BLOCK = re.compile(r"<!-- ([\w-]+):start -->.*?<!-- \1:end -->", re.S)
TRANS = re.compile(r"\.(en|zh|tw|ko|de|hi)$")

#: (README のパス, その言語, リンクの基準ディレクトリ)
PAGES = [(os.path.join(DOCS, "README.%s.md" % l), l, DOCS) for l in ("en", "zh", "tw", "ko", "de")]
PAGES.append((os.path.join(ROOT, "README.md"), "en", ROOT))


def stale_links(path, lang, base):
    """訳があるのに原文を指している手書きリンク。"""
    s = io.open(path, encoding="utf-8").read()
    spans = [m.span() for m in BLOCK.finditer(s)]
    bad = []
    for m in LINK.finditer(s):
        if any(a <= m.start() < b for a, b in spans):
            continue
        stem = m.group(1)
        if TRANS.search(stem) or os.path.basename(stem).startswith("README") or "://" in stem:
            continue
        if not os.path.isfile(os.path.join(base, stem + ".md")):
            continue
        for code in dict.fromkeys((lang, "en")):
            if os.path.isfile(os.path.join(base, "%s.%s.md" % (stem, code))):
                bad.append("%s.md -> %s.%s.md" % (stem, stem, code))
                break
    return bad


def test_the_pages_exist():
    assert len(PAGES) == 6
    for p, _l, _b in PAGES:
        assert os.path.isfile(p), p


@pytest.mark.parametrize("path,lang,base", PAGES, ids=[os.path.relpath(p, ROOT) for p, _, _ in PAGES])
def test_hand_written_links_point_to_the_readers_language(path, lang, base):
    bad = stale_links(path, lang, base)
    assert not bad, "%s: 訳があるのに原文(日本語)を指しているリンク: %s" % (os.path.relpath(path, ROOT), bad)


def test_the_gate_catches_a_link_to_the_japanese_original(tmp_path):
    """門が本当に引っかかるか: 英訳のある文書へ原文のリンクを書いた README を作って確かめる。"""
    (tmp_path / "GUIDE.md").write_text("# ガイド\n", encoding="utf-8")
    (tmp_path / "GUIDE.en.md").write_text("# Guide\n", encoding="utf-8")
    page = tmp_path / "README.ko.md"
    page.write_text("Start: [GUIDE.md](GUIDE.md)\n<!-- m:start -->\n[x](GUIDE.md)\n<!-- m:end -->\n",
                    encoding="utf-8")
    assert stale_links(str(page), "ko", str(tmp_path)) == ["GUIDE.md -> GUIDE.en.md"]
    (tmp_path / "GUIDE.ko.md").write_text("# 가이드\n", encoding="utf-8")
    assert stale_links(str(page), "ko", str(tmp_path)) == ["GUIDE.md -> GUIDE.ko.md"]
