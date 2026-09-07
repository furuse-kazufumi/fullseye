# -*- coding: utf-8 -*-
"""公開している parity の数字が、**内訳としても成り立つ**ことを見る。

## なぜ要るか(2026-09-08)

``docs/HALCON_PARITY.md`` の見出しは長らく正しかった(``979 / 2313``、数え直しても
979)。ところがその直下の内訳が

    = 979 evolvable registry ops + 17 n-ary capability ops (disjoint).

と書いてあり、**足すと 996 になる**。実測すると n-ary の 17 本は registry 側の
**部分集合**(``nary_names - reg_counted`` が空)で、"disjoint" は誤り。
見出しの数字を検算する門は在った(``tests/test_docs_index_numbers.py`` が 6 言語の
README と突き合わせる)が、**内訳が和として成り立つかを見る門は無かった**。

同じ回に見つけた 5 つ(KNOWN_ISSUES §42)と同じ型 —— 記録も門も在るのに、
読む側が別のところを見ている。数字は合っていても**説明が嘘をつく**ことがある。

## 何を守るか

* 見出しの ``N / 2313`` が、内訳に書いた集合の**和集合の大きさ**と一致すること。
* 「部分集合」と書いたものが本当に部分集合であること(``disjoint`` に戻らない)。

重いので(機能ゲートを 227 spec 走らせる)、満杯の環境でだけ回す。
"""
from __future__ import annotations

import os
import re
import warnings
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PARITY = ROOT / "docs" / "HALCON_PARITY.md"


def _counts():
    """``honest_summary`` と同じ集合を、同じ手順で数え直す。"""
    warnings.filterwarnings("ignore")
    import backends_auto as BA
    import halcon_coverage as HC
    import imgops_nary as NA
    import ops as R
    import verify_auto as VA

    data = HC.load_operators(os.path.join(str(ROOT), "data", "halcon_operators.json"))
    vers = HC.load_versions(os.path.join(str(ROOT), "data", "halcon_versions.json"))
    a = HC.analyze(data, R.REGISTRY, vers)
    reg_covered = set(a["covered"])
    auto_pass = set(VA.run(verbose_failures=False)["passing_ops"])
    auto_names = {s["halcon"] for s in BA.load_specs()}
    reg_counted = reg_covered - ((reg_covered & auto_names) - auto_pass)
    nary = set(NA.coverage()["halcon_names"])
    return reg_counted, nary, a["n_real"]


@pytest.mark.slow
def test_the_headline_equals_the_union_of_its_parts():
    pytest.importorskip("cv2", reason="満杯の環境でだけ意味がある")
    reg, nary, n_real = _counts()
    total = reg | nary
    md = PARITY.read_text(encoding="utf-8")
    m = re.search(r"\*\*(\d+)\s*/\s*(\d+) distinct real HALCON operators", md)
    assert m, "HALCON_PARITY.md の見出しが読めない(生成器が変わった?)"
    assert int(m.group(1)) == len(total), (
        "見出しの数が和集合と違う: 見出し %s / 実測 %d —— "
        "`py -3.11 honest_summary.py` で作り直すこと" % (m.group(1), len(total)))
    assert int(m.group(2)) == n_real, (m.group(2), n_real)


@pytest.mark.slow
def test_the_breakdown_does_not_claim_a_sum_that_is_not_one():
    """内訳の行が「A + B」を名乗るなら、A と B は本当に交わらないこと。"""
    pytest.importorskip("cv2", reason="満杯の環境でだけ意味がある")
    reg, nary, _ = _counts()
    md = PARITY.read_text(encoding="utf-8")
    head = md.split("## Evolvable registry", 1)[0]
    overlap = len(reg & nary)
    if overlap:
        assert "disjoint" not in head, (
            "内訳が 'disjoint' を名乗っているが %d 本が重なっている"
            "(n-ary のうち registry にも在るもの)。足し算に見える書き方は"
            "読者に 996 と数えさせる —— 部分集合であることを書くこと" % overlap)
        assert "subset, not an addition" in head, (
            "重なりが %d 本あるのに、内訳が部分集合だと書いていない" % overlap)
    else:
        assert "disjoint" in head, "本当に交わらないなら、そう書いてよい"
