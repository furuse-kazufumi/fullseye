# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""``tools/preflight.py`` が、全数テストの**落ちた理由**を残すことの門。

2026-09-25 の実測: `check_full_suite()` は stdout の**最終行だけ**を verdict に
添えていた。fullseye のスイートは動画を扱う PoC が ffmpeg の警告を stdout に吐く
ので、最終行が `[mov,mp4,...] moov atom not found` になることがある —— 36 分
走らせた末に「FAIL、moov atom not found」しか残らず、**何が落ちたのか分からな
かった**。同じ行は前回の **PASS** にも出ていたので、その行は合否と無関係である。

長い検査ほど、失敗したときの情報量が価値を決める。「落ちた」しか返さない 36 分は、
原因究明のために**もう 1 回 36 分**を払わせる。
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

preflight = pytest.importorskip("preflight", reason="tools/preflight.py が読めない")

#: 実際に踏んだ形 —— 最終行が ffmpeg の雑音で、その上に本当の理由が在る。
_NOISY_FAIL = "\n".join([
    "tests/test_x.py .....F",
    "FAILED tests/test_x.py::test_one - AssertionError: boom",
    "FAILED tests/test_y.py::test_two - ValueError: nope",
    "[mov,mp4,m4a,3gp,3g2,mj2] moov atom not found",
    "1 failed, 3 passed in 12.34s",
    "[mov,mp4,m4a,3gp,3g2,mj2] moov atom not found",
])

_QUIET_PASS = "\n".join([
    "tests/test_x.py ....",
    "4 passed in 3.21s",
    "[mov,mp4,m4a,3gp,3g2,mj2] moov atom not found",
])


def test_the_verdict_names_what_failed():
    detail = preflight._suite_detail(_NOISY_FAIL)
    assert "test_one" in detail and "test_two" in detail, detail
    assert "1 failed, 3 passed" in detail, detail


def test_the_verdict_does_not_quote_the_ffmpeg_noise():
    """★合否と無関係な行を添えない —— 同じ行が PASS にも出る。"""
    assert "moov atom" not in preflight._suite_detail(_NOISY_FAIL)
    assert "moov atom" not in preflight._suite_detail(_QUIET_PASS)


def test_a_passing_run_still_says_how_many_ran():
    assert "4 passed" in preflight._suite_detail(_QUIET_PASS)


def test_many_failures_are_summarised_with_a_count():
    """落ちた数が多いときも、何件あるかは残ること(先頭だけ見て安心しない)。"""
    lines = ["FAILED tests/t%d.py::test_%d - AssertionError: boom" % (i, i) for i in range(9)]
    detail = preflight._suite_detail("\n".join(lines + ["9 failed, 1 passed in 5.00s"]))
    assert "ほか 6 件" in detail, detail
    assert "9 failed" in detail, detail


def test_an_output_with_nothing_useful_says_so():
    """★空を「異常なし」に見せない —— 拾えなかったことを言う。"""
    assert "FAILED も集計行も無い" in preflight._suite_detail("なにも無い\n")
