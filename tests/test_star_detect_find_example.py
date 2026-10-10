# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""astrostack.star_detect の docstring に書いた ``op_find`` の例が本当に当たるか。

docstring の検索例は実行する門が無いと静かに壊れる(2026-10-11 まで書かれていた
``op_find("点 検出")`` は無関係な op を返していた)。書いた 3 つのクエリが
``star_detect`` を先頭に返すことを固定する。
"""
import pytest

import astrostack
import opassist

_QUERIES = ("輝点 検出", "点状目標", "粒子 検出")


def test_queries_are_the_ones_in_the_docstring():
    doc = astrostack.star_detect.__doc__
    for q in _QUERIES:
        assert f'op_find("{q}")' in doc, q


@pytest.mark.parametrize("q", _QUERIES)
def test_op_find_returns_star_detect_first(q):
    hits = opassist.op_find(q)
    assert hits and hits[0]["op"] == "star_detect", [h["op"] for h in hits[:5]]
