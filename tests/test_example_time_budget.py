# -*- coding: utf-8 -*-
"""3-D 例の時間予算が、正直に宣言されていること。

``examples3d.validate()`` は全例を副プロセスで走らせて「使える例」を数える。
2026-09-05 まで**全例に一律 240 秒**を課していたため、単独で 12 分近くかかる
``render_beauty`` は必ず ``timeout`` として返っていた —— 中身は PASS なのに。
CI は代表 3 本しか走らせないので、この状態が誰にも見えていなかった。

予算を例ごとに宣言できるようにしたので、ここでは**宣言が正直か**を見る:

* 既定(240 秒)より短い予算は意味が無い(短くしたいなら例を速くする)
* 予算を伸ばすなら**理由を書く**。黙って伸ばすと「遅い」が「壊れている」を隠す
* 予算は青天井にしない —— 上限を超えるなら例の側を直す話になる
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import examples3d                                        # noqa: E402

#: これ以上の予算を宣言したくなったら、例そのものを見直す。
MAX_BUDGET_S = 1800


def _declared():
    return [e for e in examples3d.EXAMPLES if e.get("budget_s")]


def test_the_default_budget_is_what_run_uses_when_nothing_is_declared():
    plain = [e for e in examples3d.EXAMPLES if not e.get("budget_s")]
    assert plain, "全例が予算を宣言している = 既定が意味を失っている"
    assert examples3d.budget(plain[0]["id"]) == examples3d.DEFAULT_BUDGET_S


def test_an_unknown_example_falls_back_to_the_default():
    assert examples3d.budget("no_such_example") == examples3d.DEFAULT_BUDGET_S


@pytest.mark.parametrize("entry", _declared(), ids=lambda e: e["id"])
def test_a_declared_budget_is_longer_than_the_default_and_says_why(entry):
    b = int(entry["budget_s"])
    assert b > examples3d.DEFAULT_BUDGET_S, (
        f"{entry['id']}: 予算 {b}s が既定 {examples3d.DEFAULT_BUDGET_S}s 以下 —— "
        "宣言する意味が無い(速くしたいなら例の側を直す)")
    assert b <= MAX_BUDGET_S, (
        f"{entry['id']}: 予算 {b}s が上限 {MAX_BUDGET_S}s を超える —— "
        "予算を伸ばすのではなく例を見直すべき水準")
    note = (entry.get("budget_note") or "").strip()
    assert len(note) >= 20, (
        f"{entry['id']}: budget_note が無い/短い。**なぜ遅いのか**を書くこと "
        "(黙って伸ばすと『遅い』が『壊れている』を隠す)")


def test_run_uses_the_declared_budget_not_the_default():
    """宣言が実際に :func:`examples3d.run` へ届いていること。"""
    declared = _declared()
    if not declared:
        pytest.skip("予算を宣言している例がまだ無い")
    e = declared[0]
    assert examples3d.budget(e["id"]) == int(e["budget_s"])
