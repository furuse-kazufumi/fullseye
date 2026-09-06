# -*- coding: utf-8 -*-
"""★索引から 1 本も辿れない文書を作らない。

## なぜ要るか(2026-09-06)

`docs/README.md` は GitHub Pages のトップ(<https://furuse.work/>)であり、
**AI コーディング支援が引く検索面**でもある(README が「op ノートは RAG
コーパスを兼ねる」と書いている)。この日に数えたところ:

| | 到達 / 全体 |
|---|---|
| `docs/*.md` | **31 / 74** |
| `docs/ops/**/INDEX.md` | **0 / 32** |
| 族ガイド | **0 / 48** |
| op ノート | **0 / 1,843** |
| `docs/articles/**` | **0 / 40** |

op ノート 1,843 本 —— **この repo でいちばん大きい中身**が、入口から 1 本も
辿れなかった。原因は 2 つあって、どちらも「在るものを無いことにする」形:

1. 索引に `docs/ops/` へのリンクが 1 本も無かった。
2. 足したはずの生成器が `OD.records()`(実体は `_records`)を `hasattr` で
   探し、**見つからないと黙って空を返して**いた。表が空・「0 本の op ノート」
   と書かれた索引が 6 言語ぶん公開されていた。

数が減っていくのを止めるのではなく、**ゼロであることを守る**門にする。
新しい文書を足したら、索引のどこかから辿れるようにするか、
`tools/gen_docs_index_ops.py` の `DOC_GROUPS` に足す(足し忘れても
「そのほか」に自動で出るので、この門が落ちるのは**リンクを壊したとき**だけ)。
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from collections import deque
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
INDEX = DOCS / "README.md"

#: 索引の言語版。ja(README.md)以外は同じ生成ブロックを持つ。
LANGS = ["", "en", "zh", "tw", "ko", "de"]

#: 生成ブロックのマーカー。**外したら索引が腐る**ので存在も確かめる。
MARKERS = ["<!-- ops-index:start -->", "<!-- ops-index:end -->",
           "<!-- poc-index:start -->", "<!-- poc-index:end -->",
           "<!-- docmap:start -->", "<!-- docmap:end -->"]

_LINK = re.compile(r"\]\(([^)\s]+)")
#: ```…``` のブロックと `…` のインラインコード。**この中はリンクではない**
#: (`docs/I18N.md` が検査の説明として `](*.md)` と書いており、素朴に走査すると
#: 「リンク切れ」に見える)。
_FENCE = re.compile(r"^```.*?^```", re.S | re.M)
_CODE = re.compile(r"`[^`\n]*`")


def _prose(text: str) -> str:
    return _CODE.sub("", _FENCE.sub("", text))


def _links(path: Path) -> list:
    """md 内の相対リンク先を絶対パスで返す(http / mailto / アンカーは除く)。"""
    out = []
    for m in _LINK.finditer(_prose(path.read_text(encoding="utf-8"))):
        t = m.group(1).split("#")[0].strip()
        if not t or t.startswith(("http://", "https://", "mailto:", "<")):
            continue
        out.append((path.parent / t).resolve())
    return out


def _reachable() -> set:
    seen = {INDEX.resolve()}
    q = deque(seen)
    while q:
        cur = q.popleft()
        for nxt in _links(Path(cur)):
            if nxt in seen or nxt.suffix != ".md" or not nxt.is_file():
                continue
            seen.add(nxt)
            q.append(nxt)
    return seen


def _all_md() -> list:
    return sorted(p.resolve() for p in DOCS.rglob("*.md"))


def test_every_document_is_reachable_from_the_index():
    """★これが本体。`docs/**/*.md` が 1 本残らず索引から辿れること。"""
    seen = _reachable()
    orphans = [p for p in _all_md() if p not in seen]
    rel = sorted(str(p.relative_to(ROOT)).replace("\\", "/") for p in orphans)
    assert not orphans, (
        "索引 docs/README.md から辿れない文書が %d 本ある。入口が無い文書は "
        "在っても無いのと同じ。`py -3.11 tools/gen_docs_index_ops.py` を走らせるか、"
        "どこかからリンクすること:\n  %s" % (len(rel), "\n  ".join(rel[:40])))


def test_the_index_has_no_broken_links():
    """★リンク切れは到達性より先に効く(切れた先はそもそも数えられない)。"""
    bad = []
    for md in _all_md():
        for t in _links(Path(md)):
            if t.suffix in (".md", ".json", ".py", ".cff", ".toml", ".txt") \
                    and not t.exists():
                bad.append("%s -> %s" % (
                    Path(md).relative_to(ROOT), t.relative_to(ROOT)
                    if str(t).startswith(str(ROOT)) else t))
    assert not bad, "リンク切れ %d 件:\n  %s" % (len(bad), "\n  ".join(bad[:40]))


@pytest.mark.parametrize("lang", LANGS, ids=lambda x: x or "ja")
def test_every_language_index_carries_the_generated_blocks(lang):
    """片方の言語だけ生成し忘れる事故を止める。"""
    name = "README.md" if not lang else "README.%s.md" % lang
    s = (DOCS / name).read_text(encoding="utf-8")
    missing = [m for m in MARKERS if m not in s]
    assert not missing, "%s に生成ブロックが無い: %s —— " \
        "`py -3.11 tools/gen_docs_index_ops.py`" % (name, missing)


def test_the_operator_table_is_not_empty():
    """★空の表を公開しない(実際に「0 本の op ノート」を 6 言語で公開した)。

    生成器が一次情報の名前を取り違えて黙って空を返したときに鳴る。
    「N 本」の N が 0 でないこと、次元の行が実際にあることを見る。
    """
    s = (DOCS / "README.md").read_text(encoding="utf-8")
    block = s.split("<!-- ops-index:start -->", 1)[1].split("<!-- ops-index:end -->")[0]
    rows = [l for l in block.splitlines() if l.startswith("| `")]
    assert len(rows) >= 20, "次元の行が %d 行しかない(生成器が空を返している?)" % len(rows)
    assert "**0 " not in block, "「0 本の op ノート」と書かれている —— 生成器が壊れている"
    for dim in ("`2d`", "`3d`", "`optics`", "`blob`"):
        assert dim in block, "%s の行が無い" % dim


def test_the_generated_blocks_are_current():
    """生成物と commit 済みが一致していること(ドリフト門)。"""
    sys.path.insert(0, str(ROOT / "tools"))
    sys.path.insert(0, str(ROOT))
    import gen_docs_index_ops as G

    for lang in LANGS:
        name = "README.md" if not lang else "README.%s.md" % lang
        s = (DOCS / name).read_text(encoding="utf-8")
        for want, a, b in ((G.build(lang), G.START, G.END),
                           (G.build_poc(lang), G.PSTART, G.PEND),
                           (G.build_docmap(lang), G.DSTART, G.DEND)):
            got = a + s.split(a, 1)[1].split(b, 1)[0] + b
            assert got == want, (
                "%s の %s ブロックが古い —— "
                "`py -3.11 tools/gen_docs_index_ops.py` で再生成すること" % (name, a))

    s = (DOCS / "articles" / "README.md").read_text(encoding="utf-8")
    want = G.build_articles()
    got = G.ASTART + s.split(G.ASTART, 1)[1].split(G.AEND, 1)[0] + G.AEND
    assert got == want, ("docs/articles/README.md の一覧が古い —— "
                         "`py -3.11 tools/gen_docs_index_ops.py`")


def test_the_index_points_at_the_machine_readable_entry_points():
    """★索引は人だけでなく RAG の入口でもある。

    op ノートは AI コーディング支援の検索コーパスを兼ねる(README がそう
    書いている)。機械が読む入口 —— `OP_INDEX.json` と `AI_RAG_GUIDE.md` ——
    が索引から辿れること。
    """
    s = INDEX.read_text(encoding="utf-8")
    for target in ("OP_INDEX.json", "AI_RAG_GUIDE.md", "OP_CATALOG.md"):
        assert "(%s)" % target in s, (
            "索引から %s へのリンクが無い。AI から引く入口なので消さないこと。"
            % target)
    assert (DOCS / "OP_INDEX.json").is_file(), "OP_INDEX.json が無い"


def test_the_docmap_lists_every_top_level_document():
    """地図が `docs/*.md` と `docs/design/*.md` を 1 本残らず含むこと。"""
    sys.path.insert(0, str(ROOT / "tools"))
    sys.path.insert(0, str(ROOT))
    import gen_docs_index_ops as G

    block = INDEX.read_text(encoding="utf-8").split(G.DSTART, 1)[1].split(G.DEND)[0]
    missing = [d for d in G._all_docs() if "](%s)" % d not in block]
    assert not missing, "地図に載っていない文書: %s" % missing


def test_the_index_renders_as_a_page_without_local_paths():
    """公開ページにローカル絶対パスを載せない(前に api-keys.json の絶対パスが
    載っていた)。索引は 6 言語すべて見る。"""
    bad = []
    for lang in LANGS:
        name = "README.md" if not lang else "README.%s.md" % lang
        s = (DOCS / name).read_text(encoding="utf-8")
        for m in re.finditer(r"[A-Za-z]:[\\/](?:dev|Users)[\\/][^\s`)\"']+", s):
            bad.append("%s: %s" % (name, m.group(0)))
    assert not bad, "公開索引にローカル絶対パス: %s" % bad
