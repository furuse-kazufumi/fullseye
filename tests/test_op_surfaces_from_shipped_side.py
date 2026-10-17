# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""op を足したら、探す面の全部に載ること —— **配布物の側から**数える門。

外部 AI のレビュー(PyPI 0.6.0、2026-10-18 に一次検証)の推奨:
「新 op を登録したら list_ops(include_ledger=True) / OP_INDEX / OP_SEARCH / op_knob の 4 つ全部に載ることを
CI で検査する」。

登録済み(``opassist._LEDGERS``)から数える門は、未登録の族に盲目になる
([[feedback_registered_only_gates_miss_unregistered]])。ここでは母集団を**wheel に入る物**から作る:

1. ``pyproject.toml`` の ``py-modules`` を全部開き、台帳の形の表(大文字の dict、値が ``func`` と ``out`` を持つ)
   を探す。``opassist._LEDGERS`` に無い表が 1 つでも在れば赤(登録漏れの族)。
2. その全 op + 2-D レジストリ + n-ary が、``list_ops(include_ledger=True)`` / 同梱の ``OP_INDEX.json`` /
   ``docs/OP_INDEX.json`` / ``OP_SEARCH.json`` の全部に載る。
3. ``op_knob.json`` は**設計上の範囲**(1 画像 + つまみ a・b の 2-D 呼び出しのうち、image→image /
   image→region / region→region。``tools/impl2/knob_probe.py`` が測れる型)だけを数える。台帳の op は a・b の
   つまみを持たないので、対象外が正しい(レビューの N220 が挙げた msa_gauge_rr ほか 7 本は全部台帳の op)。
   ★ただし範囲の中は 2026-10-18 まで 461 / 567 しか載っておらず、region→region の 87 本は一度も測られて
   いなかった。9-17 に b を端の扱いに配線した 7 op(gaussian / mean_box / median / gopen …)は「b 未使用」の
   まま残っていた。
"""
from __future__ import annotations

import importlib
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    import tomllib
except ModuleNotFoundError:  # py3.10
    tomllib = None

#: op_knob の範囲(knob_probe の --all-image / --all-region-out / --all-region と同じ)
KNOB_SCOPE = {("image", "image"), ("image", "region"), ("region", "region")}


def _py_modules() -> list[str]:
    path = os.path.join(ROOT, "pyproject.toml")
    if tomllib is not None:
        with open(path, "rb") as f:
            return list(tomllib.load(f)["tool"]["setuptools"]["py-modules"])
    import re
    text = open(path, encoding="utf-8").read()
    block = text.split("py-modules = [", 1)[1].split("]", 1)[0]
    return re.findall(r'"([A-Za-z0-9_]+)"', block)


def _is_ledger_table(name: str, value) -> bool:
    return (name.isupper() and isinstance(value, dict) and bool(value)
            and all(isinstance(v, dict) and "func" in v and "out" in v for v in value.values()))


def _shipped_ledger_tables() -> dict:
    """wheel に入るモジュールから、台帳の形の表を全部 ``{(module, table): {op: entry}}`` で。"""
    found = {}
    for m in _py_modules():
        src_path = os.path.join(ROOT, m + ".py")
        if not os.path.isfile(src_path):
            continue
        with open(src_path, encoding="utf-8") as f:
            src = f.read()
        if '"func"' not in src and "'func'" not in src:
            continue                       # 表を持てないモジュールは import しない(速さ)
        mod = importlib.import_module(m)
        for k, v in vars(mod).items():
            if _is_ledger_table(k, v):
                found[(m, k)] = v
    return found


@pytest.fixture(scope="module")
def shipped():
    import ops
    import opassist
    tables = _shipped_ledger_tables()
    ledger_ops = set()
    for t in tables.values():
        ledger_ops |= set(t)
    registry = {o.name: (o.in_sort, o.out_sort) for o in ops.REGISTRY}
    nary = {n.name for n in opassist._nary_ops()}
    return {"tables": tables, "ledger": ledger_ops, "registry": registry, "nary": nary}


def _load(rel: str):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return json.load(f)


def _surfaces() -> dict:
    import fullseye as fs
    return {
        "list_ops(include_ledger=True)": {r["name"] for r in fs.list_ops(include_ledger=True)},
        "fullseye/data/OP_INDEX.json": {o["name"] for o in _load("fullseye/data/OP_INDEX.json")["ops"]},
        "docs/OP_INDEX.json": {o["name"] for o in _load("docs/OP_INDEX.json")["ops"]},
        "fullseye/data/OP_SEARCH.json": {r["n"] for r in _load("fullseye/data/OP_SEARCH.json")["ops"]},
    }


def _missing(population: set, surfaces: dict) -> dict:
    """面ごとに、母集団のうち載っていない op。"""
    return {k: sorted(population - v) for k, v in surfaces.items() if population - v}


def test_the_population_is_not_silently_small(shipped):
    """範囲を自分で読む門は黙って縮む —— 件数に床を置く(2026-10-18 の実測: 台帳 49 表 2,350 op)。"""
    assert len(shipped["tables"]) >= 49
    assert len(shipped["ledger"]) >= 2350
    assert len(shipped["registry"]) >= 930
    assert len(shipped["nary"]) >= 17


def test_every_shipped_ledger_table_is_registered(shipped):
    import opassist
    registered = {(m, t) for m, t in opassist._LEDGERS}
    unregistered = sorted(set(shipped["tables"]) - registered)
    assert not unregistered, (
        "wheel に入る台帳の表が opassist._LEDGERS に無い(op_run / op_find / list_ops / 索引のどれからも"
        "見えない族になる): %s" % unregistered)


def test_every_shipped_op_is_on_all_four_surfaces(shipped):
    population = shipped["ledger"] | set(shipped["registry"]) | shipped["nary"]
    miss = _missing(population, _surfaces())
    assert not miss, "\n".join("%s に無い %d op: %s" % (k, len(v), v[:15]) for k, v in miss.items())


def test_op_knob_covers_its_declared_scope(shipped):
    scope = {n for n, pair in shipped["registry"].items() if pair in KNOB_SCOPE}
    assert len(scope) >= 567
    for rel in ("docs/op_knob.json", "fullseye/data/op_knob.json"):
        rows = {r["op"]: r for r in _load(rel)}
        lacking = sorted(scope - set(rows))
        assert not lacking, ("%s に範囲内の op が %d 本無い(tools/impl2/knob_probe.py --all-image "
                             "--all-region-out --all-region で測り直す): %s" % (rel, len(lacking), lacking[:15]))
        undecided = [n for n in scope if rows[n].get("status") != "determined" and not rows[n].get("reason")]
        assert not undecided, "測れなかった理由の無い行: %s" % undecided[:10]


def test_op_knob_agrees_with_what_b_actually_does():
    """9-17 に b を端の扱いに配線した op が「b 未使用」のまま残っていた —— その再発を止める。"""
    import numpy as np
    import fullseye as fs
    rows = {r["op"]: r for r in _load("fullseye/data/op_knob.json")}
    rng = np.random.default_rng(20261018)
    img = rng.random((24, 24))
    for op in ("gaussian", "mean_box", "median", "gopen", "gclose", "gdilate", "gerode"):
        moved = float(np.max(np.abs(fs.apply(img, op, 0.6, 0.0) - fs.apply(img, op, 0.6, 1.0))))
        assert moved > 1e-6, "%s の b が出力を動かさない(%.2e)" % (op, moved)
        assert rows[op]["b_used"] is True, "%s: op_knob が b 未使用と言う" % op
        assert fs.knob_summary(op)["b"] is True


def test_the_gate_sees_a_planted_gap(shipped):
    """壊して確かめる探針: 架空の op を母集団に足すと、4 面すべてで「無い」と言う。"""
    surfaces = _surfaces()
    population = set(shipped["registry"]) | {"__planted_op_not_on_any_surface__"}
    miss = _missing(population, surfaces)
    assert set(miss) == set(surfaces)
    assert all(v == ["__planted_op_not_on_any_surface__"] for v in miss.values())
    # 台帳の表の判定も、形を壊すと外れる
    assert _is_ledger_table("X", {"a": {"func": len, "out": "table"}})
    assert not _is_ledger_table("X", {"a": {"func": len}})
    assert not _is_ledger_table("x", {"a": {"func": len, "out": "table"}})
