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


def test_operators_catalog_is_in_the_chain_and_counts_the_shipped_index():
    """★比べる相手は**同梱索引**(生成環境 = 全 backend)であって、この環境の生きた registry ではない。
    2026-09-20 の CI(run 35482450634)で py3.12 が赤: torch / kornia の無い環境では ops.REGISTRY が 905 で、
    OPERATORS.md の 931(= 索引の registry 919 + color 12)と食い違う。生成物は py3.11(全 backend)の regen 検査が
    守るので、他の環境の門は「生成物が索引と一致する」ことを問う([[feedback_os_walk_order_makes_gates_environment_dependent]])。"""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import regen_all
    assert any(cmd[0] == "catalog.py" for cmd, _ in regen_all.CHAIN), "catalog.py が regen_all の鎖に無い"
    idx = _index()
    rows = [r for r in idx["ops"] if r["tier"] in ("registry", "color")]      # ops.REGISTRY に載る 2 層
    md = _read(os.path.join("docs", "OPERATORS.md"))
    m = re.search(r"^(\d+) operators across (\d+) categories", md, re.M)
    assert m, "docs/OPERATORS.md の見出しに『N operators across M categories』が無い"
    assert int(m.group(1)) == len(rows), "OPERATORS.md の op 数 %s が索引の registry + color %d と違う(regen_all を回す)" % (m.group(1), len(rows))
    assert int(m.group(2)) == len({r["category"] for r in rows})
    import ops
    if len(ops.REGISTRY) == len(rows):                                        # 全 backend の環境でだけ生きた registry とも照合
        assert {op.name for op in ops.REGISTRY} == {r["name"] for r in rows}


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


def test_no_note_path_is_gitignored():
    """docs/ops の下のディレクトリ・ノートが 1 つも .gitignore に当たらないこと。

    ★2026-09-20: conngraph のカテゴリ ``build`` が packaging 用の ``build/`` 規則に当たり、
    ノート 3 枚が**手元には在るのに commit されず**、CI だけで 10 件の失敗に連鎖した
    (ノート欠落 → 索引のリンク切れ → MCP 複製の不一致 → コーパス地図の drift)。
    手元の「ノートが在る」門は tracked かどうかを見ていなかった —— 門は事故の起きる場所に。
    """
    import subprocess
    paths = sorted(glob.glob(os.path.join(ROOT, "docs", "ops", "*", "*")) +
                   glob.glob(os.path.join(ROOT, "docs", "ops", "*", "*", "*.md")))
    rel = [os.path.relpath(p, ROOT).replace(os.sep, "/") for p in paths]
    try:
        r = subprocess.run(["git", "check-ignore", "--stdin"], input="\n".join(rel), capture_output=True,
                           text=True, cwd=ROOT, encoding="utf-8", timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:        # git が無い環境は判定できない
        import pytest
        pytest.skip("git が使えない: %s" % exc)
    ignored = [ln for ln in r.stdout.splitlines() if ln.strip()]
    assert not ignored, "docs/ops の下で .gitignore に当たるものがある(commit されずに CI だけ赤になる):\n" + "\n".join(ignored[:20])
