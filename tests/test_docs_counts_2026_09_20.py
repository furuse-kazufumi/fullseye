# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""手書きの op 数が索引とずれない(2026-09-20、利用者の指摘)。

`docs/OPERATORS.md` は 885 op / 47 分類(2026-09-06)のまま置き去りだった —— 生成器 `catalog.py` が
`tools/` の外にあって再生成の鎖に無く、`docs/INTEGRATION.md` と INSTALL / GETTING_STARTED の 6 言語は
手書きの数だった。ここでは (1) 生成物が鎖にあり、見出しの数が生きたレジストリと一致すること、
(2) 手書き文書の数が同梱索引と一致すること、(3) 導入文書に op 数を書かないこと(数は必ず古びる)、
(4) 外部レビューの報告通数が CHANGELOG と記事で同じこと、を問う。
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


def _index():
    return json.loads(_read(os.path.join("docs", "OP_INDEX.json")))


def test_operators_catalog_is_in_the_chain_and_counts_the_live_registry():
    import ops
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import regen_all
    assert any(cmd[0] == "catalog.py" for cmd, _ in regen_all.CHAIN), "catalog.py が regen_all の鎖に無い"
    md = _read(os.path.join("docs", "OPERATORS.md"))
    m = re.search(r"^(\d+) operators across (\d+) categories", md, re.M)
    assert m, "docs/OPERATORS.md の見出しに『N operators across M categories』が無い"
    assert int(m.group(1)) == len(ops.REGISTRY), "OPERATORS.md の op 数 %s がレジストリ %d と違う(regen_all を回す)" % (m.group(1), len(ops.REGISTRY))
    assert int(m.group(2)) == len({op.category for op in ops.REGISTRY})


def test_integration_doc_counts_match_the_shipped_index():
    idx = _index()
    md = _read(os.path.join("docs", "INTEGRATION.md"))
    assert "({:,} operators in the machine-readable".format(idx["n_ops"]) in md
    assert "ledgers ({:,} operators whose inputs".format(idx["tiers"]["ledger"]) in md


def test_install_docs_do_not_hand_write_an_op_count():
    bad = []
    for stem in ("INSTALL", "GETTING_STARTED"):
        for p in glob.glob(os.path.join(ROOT, "docs", stem + "*.md")):
            for ln in open(p, encoding="utf-8"):
                if "pip install -e ." in ln and re.search(r"\b\d{3,4}\b", ln.split("#", 1)[-1]):
                    bad.append(os.path.basename(p) + ": " + ln.strip())
    assert not bad, "導入文書の install 行に op 数が手書きされている(必ず古びる):\n" + "\n".join(bad)


def test_external_review_report_count_agrees_across_documents():
    ch = _read("CHANGELOG.md")
    sec = ch[ch.index("## 0.2.1 —"):ch.index("## 0.2.0 —")]
    m = re.search(r"(\d+) 通の報告", sec)
    assert m, "CHANGELOG 0.2.1 に報告の通数が無い"
    n = m.group(1)
    assert "報告を %s 通" % n in _read(os.path.join("docs", "articles", "fullseye_overview_qiita_ja.md"))
    assert "sent back %s reports" % n in _read(os.path.join("docs", "articles", "fullseye_overview_qiita_en.md"))
