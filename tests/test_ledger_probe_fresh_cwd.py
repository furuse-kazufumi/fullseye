"""台帳契約の探針は、捨て場に前の実行の残り物があっても判定を変えない(2026-10-13)。

全量スイートで ``test_the_debt_only_shrinks`` が順序しだいで赤になった:
同じ xdist ワーカーで先に走った連鎖ファズの ``write_3mf`` が、探針の文字列
(``"ラベル 5"`` のように相対パスとして成立する)の名で 3MF を捨て場に置き、
探針の ``read_3mf`` がそれを読んで「拒否のはずが成功」になった。
ここでは残り物を**わざと置いて**から ``read_3mf`` だけを探針にかける。
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (ROOT, os.path.join(ROOT, "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

lc = pytest.importorskip("ledger_contracts", reason="tools/ledger_contracts.py が読めない")


def test_a_leftover_file_in_the_scratch_dir_does_not_flip_read_3mf():
    import printpath as P

    cf = lc._cf()
    ops = [op for op in lc.ledger_ops() if op[0] == "read_3mf"]
    assert len(ops) == 1
    clean = lc.run(ops=ops)["read_3mf"]["status"]

    V = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=float)
    F = np.array([[0, 1, 2]])
    planted = []
    with cf._scratch_cwd() as d:
        # 探針の text 生成器が出しうる名を広めに埋める(生成器の文字列は「ラベル N」)
        for n in range(0, 200):
            name = "ラベル %d" % n
            if not os.path.exists(name):
                P.write_3mf(name, (V, F))
                planted.append(os.path.join(d, name))
    try:
        dirty = lc.run(ops=ops)["read_3mf"]["status"]
    finally:
        for p in planted:
            os.remove(p)
    assert planted, "残り物を 1 本も置けなかった(探針になっていない)"
    assert dirty == clean, (clean, dirty)
