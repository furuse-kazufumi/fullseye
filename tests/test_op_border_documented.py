# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""実測した**端の規約**が、ノートに載り続けていることを検査する。

2026-09-16、近傍窓を使う op 213 本のうち **198 本(93%)** が端の規約に触れていなかった。
そして端の規約は答えを**値域の 2 割**動かす —— 同じ「矩形平均」でも `mean_box` は
`symmetric`、`cv_box` は `reflect` で、利用者にはどちらとも書かれていなかった
(`impl2/FINDINGS.md`)。`tools/impl2/border_probe.py` で image->image の全 378 op を
測り、確定した 106 本を `docs/op_border.json` に置いて、ノート生成器が本文へ差し込む
ようにした。

**この門が守るのは「差し込みが黙って剥がれないこと」**。生成器の分岐が消えても、
`op_border.json` が古くなっても、ノートは前と同じ見た目のまま**規約だけが消える** ——
それは最初の状態(93% が沈黙)に戻ったのと同じで、誰も気づけない。

門は**壊して確かめてある**: 台帳が空なら失格、確定件数が実測より大きく減ったら失格、
台帳に居る op が registry から消えていたら失格。
"""
from __future__ import annotations

import json
import os
import re

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BORDER_JSON = os.path.join(ROOT, "docs", "op_border.json")
OPS_DIR = os.path.join(ROOT, "docs", "ops")

#: 2026-09-16 の実測値。**下振れしたら知らせる**ための床であって、上げるのは自由。
#: (op を足して確定数が増えるのは歓迎。減るのは「測れなくなった」か「台帳が壊れた」)
MEASURED_DETERMINED = 106
FLOOR = 90

_MENTIONS_BORDER = re.compile(r"端の扱い|境界|端は|BORDER_|パディング")


def _rows():
    if not os.path.exists(BORDER_JSON):
        pytest.skip("docs/op_border.json が無い(tools/impl2/border_probe.py --all で作る)")
    with open(BORDER_JSON, encoding="utf-8") as f:
        return json.load(f)


def _note_path(op: str) -> str | None:
    for dirpath, _dirnames, filenames in os.walk(OPS_DIR):
        if f"{op}.md" in filenames:
            return os.path.join(dirpath, f"{op}.md")
    return None


def test_the_border_ledger_is_not_empty():
    """**空の台帳は全部を素通りさせる。** 件数そのものを別に数える。"""
    rows = _rows()
    assert rows, "docs/op_border.json が空"
    determined = [r for r in rows if r.get("status") == "determined"]
    assert len(determined) >= FLOOR, (
        f"端の規約が確定している op が {len(determined)} 本しかない"
        f"(2026-09-16 の実測は {MEASURED_DETERMINED} 本)。測定が壊れたか台帳が古い")


def test_every_determined_op_says_its_border_in_the_note():
    """確定した規約が**ノートに載っている**こと。生成器の差し込みが消えたら落ちる。"""
    missing = []
    for r in _rows():
        if r.get("status") != "determined":
            continue
        p = _note_path(r["op"])
        if p is None:
            missing.append(f"{r['op']}: ノートが無い")
            continue
        if not _MENTIONS_BORDER.search(open(p, encoding="utf-8").read()):
            missing.append(f"{r['op']}: ノートが端の扱いを書いていない")
    assert not missing, (
        "実測した端の規約がノートから消えている(生成器の差し込みが効いていない):\n"
        + "\n".join(missing[:20]))


def test_undetermined_ops_are_not_given_a_guessed_border():
    """**測れなかったものに規約を書かない。** 推測を書けば、その推測が契約になる。

    `undetermined` は「判定法の前提(``op(pad_P(x))[crop] == op(x)``)が成り立たない」
    という意味で、「規約が無い」ではない。ここに当てずっぽうを載せるくらいなら
    黙っているほうがよい。
    """
    for r in _rows():
        if r.get("status") == "undetermined":
            assert "border" not in r, (
                f"{r['op']}: 判定できていないのに規約が入っている(推測を契約にしている)")


def test_the_ledger_only_names_ops_that_exist():
    """台帳が古くなって、もう無い op を指していないこと。"""
    idx_path = os.path.join(ROOT, "docs", "OP_INDEX.json")
    if not os.path.exists(idx_path):
        pytest.skip("docs/OP_INDEX.json が無い")
    with open(idx_path, encoding="utf-8") as f:
        known = {o["name"] for o in json.load(f)["ops"]}
    gone = [r["op"] for r in _rows() if r["op"] not in known]
    assert not gone, f"台帳が存在しない op を指している(古い): {gone[:10]}"
