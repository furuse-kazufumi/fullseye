# -*- coding: utf-8 -*-
"""成熟度台帳(``docs/MATURITY.md`` / ``docs/maturity.json``)が事実と一致していること。

## なぜ要るか(2026-09-09)

v0.1.10 のリリースノートに「実データで検証済み」という成熟度の段を書いた。
書いた時点で**実写 PoC は 1 本も入っていなかった**(タグの中身を数えたら 0 件)。
公開後に自分で気づいて消した。**散文で書く成熟度は、この種の嘘を止められない。**

そこで台帳は生成物にし、ここで 3 つを見張る:

1. **コミット済み == 生成物**(古びたら CI が落ちる。他の docs 生成物と同じ drift 検査)
2. **``validated-hardware`` は決して出ない**(CI に実機が無いので、構造的に到達不能)
3. **段の主張には裏づけがある**(実データを名乗るなら、``data: real`` の例が
   実際に門で走っていること)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _ledger() -> dict:
    with open(os.path.join(ROOT, "docs", "maturity.json"), encoding="utf-8") as fh:
        return json.load(fh)


def test_the_committed_ledger_matches_what_the_generator_produces():
    """★本体の門。台帳が古びたらここで落ちる(直し方はコマンドを出す)。"""
    r = subprocess.run([sys.executable, os.path.join("tools", "gen_maturity.py"), "--check"],
                       cwd=ROOT, capture_output=True, text=True, errors="replace")
    assert r.returncode == 0, (
        "成熟度台帳がコミット済みと食い違う —— `py -3.11 tools/gen_maturity.py` で作り直す\n"
        + (r.stdout or "") + (r.stderr or ""))


def test_hardware_validation_is_structurally_unreachable():
    """実機の段は決して出ない。**段を先に書くのは順序が逆**なので生成器が拒む。"""
    d = _ledger()
    assert any(x["id"] == "validated-hardware" for x in d["ladder"]), \
        "はしごの定義から実機の段が消えている(消すのではなく、到達不能のまま残す)"
    claimed = [r["id"] for r in d["capabilities"] if r["status"] == "validated-hardware"]
    assert not claimed, (
        "実機検証を名乗っている能力がある: %s —— CI に実機が無い以上、これは書けない。"
        "名乗りたいなら先に実機を回す門を作ること" % claimed)


def test_a_real_data_claim_is_backed_by_an_example_that_actually_runs():
    """「実データで検証済み」は、**走る例**と ``data: real`` の両方が要る。

    ★v0.1.10 で私が書いた嘘が、ここに引っかかる形。片方(例が実データ)だけでは
    足りない —— 走らない例は、実データを使っていても何も検証していない。
    """
    for r in _ledger()["capabilities"]:
        if r["status"] != "validated-public-real-data":
            continue
        ran_real = [e for e in r["examples"] if e["executed"] and e["data"] == "real"]
        assert ran_real, (
            "%s が実データ検証を名乗っているのに、走る実データの例が無い" % r["id"])


def test_every_capability_example_is_executed_by_some_gate():
    """能力ノートが名指す例は、全部どれかの門が走らせること。

    ★2026-09-09 まで、`annotate_paper_tour` など 5 件は**どの門も走らせていなかった**
    (`poc_*` 以外を走らせる門が無かった)。裏づけに挙げた例が走らないなら、
    その能力の裏づけは紙の上にしかない。
    """
    bad = [(r["id"], e["id"]) for r in _ledger()["capabilities"]
           for e in r["examples"] if not e["executed"]]
    assert not bad, "走る門が無い例を裏づけにしている: %s" % bad


def test_the_ledger_keeps_the_facts_not_just_the_verdict():
    """★1 つの数字に畳まない。判定を再現できるだけの生の事実が残っていること。"""
    d = _ledger()
    assert d["capabilities"], "能力が 1 件も無い"
    for r in d["capabilities"]:
        for key in ("ops_total", "ops_named_in_tests", "ops_not_named_in_tests",
                    "examples", "status", "note"):
            assert key in r, "%s に %s が無い" % (r["id"], key)
        for e in r["examples"]:
            assert set(e) >= {"id", "data", "gate", "executed", "registry"}
    e = d["example_execution"]
    assert e["run_by_the_poc_gate"] + e["run_by_the_example_gate"] == e["examples2d_total"], \
        "2-D 台帳の件数と、門が走らせる件数の合計が合わない"
    assert e["not_run_by_any_gate"] == 0
