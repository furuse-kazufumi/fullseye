"""`backends_typed` の出荷側台帳 3 つに**陳腐化の門**を立てる。

門の変異テスト(2026-09-05)で判明: `_OP_BRIDGE_SKIP` / `_OP_SORT_OVERRIDE` /
`OP_TUNABLE_OVERRIDE` は、**実在しない op 名を足しても何も落ちなかった**。
橋渡しループはカタログを走査して台帳を引くだけなので、台帳側の
タイポ・改名後の残骸は**どのカタログ項目にも一致せず、静かに無害化される**。
「見落とし方向(本物を消す)」は既存テストが拾うが、逆方向は誰も見ていなかった。

ここでは「台帳の鍵はすべて、いまカタログに居る op 名である」を要求する。
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest                                              # noqa: E402

bt = pytest.importorskip("backends_typed")


def _catalog_names() -> set[str]:
    cf = bt._catalog_entries()
    return {row[0] for row in cf.catalog()}


def test_bridge_skip_names_only_catalog_ops():
    live = _catalog_names()
    assert len(live) > 100, "カタログが小さすぎる(%d) —— 検査の前提が違う" % len(live)
    stale = sorted(set(bt._OP_BRIDGE_SKIP) - live)
    assert not stale, "_OP_BRIDGE_SKIP にカタログに居ない名前: %s" % stale


def test_sort_override_names_only_catalog_ops_and_valid_sorts():
    live = _catalog_names()
    stale = sorted(set(bt._OP_SORT_OVERRIDE) - live)
    assert not stale, "_OP_SORT_OVERRIDE にカタログに居ない名前: %s" % stale
    import op_probe
    known_sorts = set(op_probe.SORT_TO_GENERATOR) | set(getattr(op_probe, "LOCAL_SORTS", ()))
    bad = {k: v for k, v in bt._OP_SORT_OVERRIDE.items()
           if not (isinstance(v, tuple) and len(v) == 2 and all(s in known_sorts for s in v))}
    assert not bad, "_OP_SORT_OVERRIDE の sort が不正: %s" % bad


def test_tunable_override_names_only_catalog_ops_and_real_parameters():
    """鍵が実在するだけでなく、指定した**引数名がその op の signature に在る**こと。"""
    import inspect
    cf = bt._catalog_entries()
    fns = {row[0]: row[4] for row in cf.catalog()}
    stale = sorted(set(bt.OP_TUNABLE_OVERRIDE) - set(fns))
    assert not stale, "OP_TUNABLE_OVERRIDE にカタログに居ない名前: %s" % stale
    bad = {}
    for name, want in bt.OP_TUNABLE_OVERRIDE.items():
        params = set(inspect.signature(fns[name]).parameters)
        missing = [w for w in want if w not in params]
        if missing:
            bad[name] = missing
    assert not bad, "OP_TUNABLE_OVERRIDE が指す引数が signature に無い: %s" % bad
