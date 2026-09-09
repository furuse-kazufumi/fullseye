# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""散文ドキュメントの翻訳が**日本語側から古びていない**ことの門(2026-09-09)。

散文ドキュメント(README のような生成物ではない手書き文書)は日本語を正本とし、
翻訳は並行ファイル `X.<lang>.md` に置く。日本語を直したとき訳が黙って古びると、
読み手は「その言語の最新」だと思って古い内容を読む —— 古い訳は無訳より悪い。

各訳ファイル先頭の `<!-- i18n-source-sha: … -->` が、訳した時点の日本語本文の
指紋。現在の日本語本文と食い違えば stale。**stale をゼロに保つ**のがこの門。
missing(まだ訳が無い)は完全多言語化の途中なので**止めない** —— 進捗は
`tools/i18n_docs.py` が数える。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import i18n_docs as D  # noqa: E402


def test_no_stale_translations():
    rows, fresh, stale, missing = D.status()
    bad = [(s, l, st) for s, l, st in rows if st in ("stale", "no-stamp")]
    assert not bad, (
        "日本語が変わったのに追随していない訳が %d 件: %s —— 訳を直して "
        "`py -3.11 tools/i18n_docs.py --stamp docs/<name>.<lang>.md` で指紋を打ち直すこと"
        % (len(bad), ", ".join("%s.%s[%s]" % (s, l, st) for s, l, st in bad)))


def test_the_ledger_sees_the_docs():
    """散文ドキュメントの列挙が空になれば門は無言で通る ——「空を通す」を封じる。"""
    docs = D.prose_docs()
    assert len(docs) >= 40, (
        "散文ドキュメントが %d 本しか見えない(2026-09-09 実測は 68 本)—— "
        "列挙が壊れていないか" % len(docs))


def test_at_least_one_translation_exists():
    """1 本も訳が無ければ、そもそも仕組みが動いていない疑い。"""
    rows, fresh, stale, missing = D.status()
    assert fresh >= 1, "fresh な訳が 1 本も無い(第一陣 GETTING_STARTED.en が消えた?)"
