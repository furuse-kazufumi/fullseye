# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""非日本語版に**黙って混ざる日本語**を禁じる門(2026-09-09)。

言語を切り替えたのに日本語が出てくる、という状態は 2 通りある:

* **未訳だと分かる形で出ている** —— `(ja)` の印つき。これは途中経過であって嘘ではない。
* **黙って原文に落ちている** —— 読み手には「これがその言語の文章だ」と見える。
  これは「訳したつもり」の状態で、**無訳より悪い**。

ここで止めるのは後者だけ。実測 2026-09-09: 英語版 README には 71 行の日本語が
黙って出ていた(PoC 表 27 行 + 文書地図 44 行)。PoC は展示字幕の `title_en` に
差し替え、地図はリンク先が本当に日本語なので `(ja)` を添える形にした。

判定は**かな**で行う。漢字は中国語版と共有するので、漢字で数えると中国語の訳を
「日本語が残っている」と誤判定する。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import i18n_status as S  # noqa: E402


def _scan():
    docs = os.path.join(ROOT, "docs")
    out = {}
    for name in sorted(os.listdir(docs)):
        if not name.endswith(".md") or name.count(".") < 2:
            continue          # `X.md` は日本語版。`X.en.md` だけを見る
        out[name] = S._kana_lines(os.path.join(docs, name))
    return out


def test_no_silent_japanese_in_translated_docs():
    scanned = _scan()
    assert scanned, "非日本語版の文書が 1 つも見つからない(走査が壊れている)"
    bad = {n: bare for n, (_m, bare) in scanned.items() if bare}
    assert not bad, (
        "非日本語版に印の無い日本語がある: %s —— 訳すか、`_(ja)_` を添えて"
        "「これは日本語だ」と示すこと(`py -3.11 tools/i18n_status.py` で内訳)"
        % ", ".join("%s(%d 行)" % (n, v) for n, v in sorted(bad.items())))


def test_the_scan_actually_looks_at_something():
    """走査が空になれば上の門は無言で通る ——「一致の門は空を通す」を封じる。"""
    scanned = _scan()
    assert len(scanned) >= 10, (
        "非日本語版が %d 本しか見つからない(2026-09-09 の実測は 12 本)" % len(scanned))
    assert sum(m for m, _b in scanned.values()) > 0, (
        "`(ja)` の印が 1 つも無い —— 全部訳し終えたのでなければ、"
        "印を出す仕組みが壊れている(黙って落ちていないか確かめること)")
