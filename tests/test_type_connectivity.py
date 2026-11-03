"""型(sort)のつながりの門(2026-11-03)。

``docs/OP_INDEX.json`` の全型が ``docs/TYPE_ROLES.json`` に理由つきで載り、

* どの型も、入口として正しい型(と引数だけで値を作る op)から**全入力がそろう op**を
  たどって届く
* どの型も、受ける op をたどって終端として正しい型へ届く
* 行き止まり(作られるのに受け手 0)と入口なし(受け手はあるのに作り手 0)は、
  台帳に終端 / 入口の理由がある型だけ

を数える。**台帳に entry / terminal を書けば通る**門にならないよう、入口と終端の
件数には天井を置く(増やすなら天井を上げる commit で理由を書く)。数え方そのものが
空回りしていないことは、偽の op を足すと赤になる検査で確かめる。
"""
from __future__ import annotations

import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import type_connectivity as TC  # noqa: E402

#: 入口として数える型の天井(2026-11-03 の実数)。増やすなら理由を台帳と commit に。
MAX_ENTRY = 29
#: 終端として数える型の天井(2026-11-03 の実数)。
MAX_TERMINAL = 13
#: 数えた母集団の床(門が空の索引を読んで素通りしないため)。
MIN_SORTS = 101
MIN_OPS = 3600


@pytest.fixture(scope="module")
def state():
    sorts, ops = TC.load_ops()
    roles = TC.load_roles()
    return sorts, ops, roles, TC.analyse(sorts, ops, roles)


def test_population_floor(state):
    sorts, ops, _roles, a = state
    assert len(ops) >= MIN_OPS, f"OP_INDEX の op が {len(ops)} しか読めていない(床 {MIN_OPS})"
    assert len(a["sorts"]) >= MIN_SORTS, f"型が {len(a['sorts'])}(床 {MIN_SORTS})"
    n_inputs = sum(len(ins) for _n, ins, _o in ops)
    assert n_inputs > len(ops), "多入力が数えられていない(in_sorts を読んでいない)"


def test_every_sort_has_exactly_one_role_row(state):
    _s, _o, _r, a = state
    assert not a["missing_roles"], (
        "docs/TYPE_ROLES.json に行の無い型: %s —— 新しい型を足したら、分類・理由・"
        "根拠を台帳に書くこと" % a["missing_roles"])
    assert not a["stale_roles"], "台帳にだけ残っている型(op 側から消えた): %s" % a["stale_roles"]


def test_every_role_row_is_filled_in(state):
    _s, _o, roles, _a = state
    for sort, r in roles.items():
        assert r.get("class") in TC.CLASSES, f"{sort}: class {r.get('class')!r} は {list(TC.CLASSES)} のどれでもない"
        assert len(r.get("why", "")) >= 20, f"{sort}: why が短すぎる"
        assert len(r.get("evidence", "")) >= 16, f"{sort}: evidence(検索語・確かめた関数)が空"
        assert r.get("status") in ("fixed", "open", "none"), f"{sort}: status が不正"
        for key in ("entry", "terminal"):
            if key in r:
                assert isinstance(r[key], str) and len(r[key]) >= 15, f"{sort}: {key} の理由が短すぎる"
        if r["status"] == "fixed":
            assert len(r.get("action", "")) >= 20, f"{sort}: fixed なのに action(何を足したか)が無い"
        if r["status"] == "open":
            assert len(r.get("design", "")) >= 20, f"{sort}: open なのに design(案)が無い"
        if r["class"] == "b":
            assert r["status"] in ("fixed", "open"), f"{sort}: b(本当の欠け)は fixed か open"
        if r["class"] == "d":
            assert r.get("entry"), f"{sort}: d(入口として正しい)なのに entry の理由が無い"
        if r["class"] == "c":
            assert r.get("terminal"), f"{sort}: c(終端として正しい)なのに terminal の理由が無い"


def test_entry_and_terminal_counts_have_a_ceiling(state):
    _s, _o, _r, a = state
    assert len(a["entry"]) <= MAX_ENTRY, (
        f"入口として数える型が {len(a['entry'])} に増えた(天井 {MAX_ENTRY})。"
        "入口を書いて門を通していないか確かめ、正しければ天井を上げる")
    assert len(a["terminal"]) <= MAX_TERMINAL, (
        f"終端として数える型が {len(a['terminal'])} に増えた(天井 {MAX_TERMINAL})")
    assert len(a["entry"]) >= 10 and len(a["terminal"]) >= 5, "入口・終端の数が少なすぎる(台帳を読めていない?)"


def test_dead_ends_and_missing_producers_are_only_the_explained_ones(state):
    _s, _o, _r, a = state
    assert not a["dead_ends_unexplained"], (
        "作られるのに誰も受けない型(終端の理由なし): %s —— 受ける op を足すか、"
        "終端として正しいなら TYPE_ROLES.json に terminal を書く" % a["dead_ends_unexplained"])
    assert not a["no_entry_unexplained"], (
        "受ける op はあるのに誰も作らない型(入口の理由なし): %s" % a["no_entry_unexplained"])


def test_every_sort_is_reachable_from_an_entry(state):
    _s, _o, _r, a = state
    assert not a["unreachable"], (
        "入口から全入力のそろう op をたどっても届かない型: %s" % a["unreachable"])


def test_every_sort_reaches_a_terminal(state):
    _s, _o, _r, a = state
    assert not a["no_terminal"], "終端(表・測定値・絵)へ出られない型: %s" % a["no_terminal"]


def test_the_fixed_gaps_stay_fixed(state):
    """直した 10 型は、足した op が受け手 / 作り手として索引に載っていること。"""
    _s, _o, roles, a = state
    fixed = sorted(s for s, r in roles.items() if r["class"] == "b" and r["status"] == "fixed")
    assert len(fixed) >= 10, fixed
    for s in fixed:
        assert a["produced"][s] >= 1 and a["consumed"][s] >= 1, (
            f"{s}: fixed なのに作り手 {a['produced'][s]} / 受け手 {a['consumed'][s]}")


def test_the_counter_is_not_blind():
    """偽の op を足すと、行き止まり・入口なし・未分類・届かないが**全部**赤になる。"""
    sorts, ops = TC.load_ops()
    roles = TC.load_roles()
    fake = ops + [("fake_sink", ["image"], "zz_new_sort"),
                  ("fake_source_needed", ["zz_orphan"], "table")]
    a = TC.analyse(sorts, fake, roles)
    assert "zz_new_sort" in a["dead_ends_unexplained"]
    assert "zz_orphan" in a["no_entry_unexplained"]
    assert {"zz_new_sort", "zz_orphan"} <= set(a["missing_roles"])
    assert "zz_orphan" in a["unreachable"]
    assert "zz_new_sort" in a["no_terminal"]
    # 終端の理由を消すと、その型が行き止まりとして出てくる(理由の有無を本当に見ている)
    roles2 = {k: dict(v) for k, v in roles.items()}
    roles2["feature"].pop("terminal")
    no_feature_consumer = [op for op in ops if "feature" not in op[1]]
    assert len(no_feature_consumer) < len(ops)
    a2 = TC.analyse(sorts, no_feature_consumer, roles2)
    assert "feature" in a2["dead_ends_unexplained"]


def test_first_input_only_count_is_reported_and_differs():
    """第 1 入力だけで数えると lut が行き止まりに見える —— 両方の数え方を並べている。"""
    sorts, ops = TC.load_ops()
    a = TC.analyse(sorts, ops, TC.load_roles())
    assert "lut" in a["legacy"]["dead_ends"]
    assert "lut" not in a["dead_ends"]


def test_generated_doc_is_fresh():
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "type_connectivity.py"), "--check"],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr

def test_match_seed_does_not_shift_the_other_seeds():
    """W1 で足した ``match`` の種は、共有の乱数列を進めない(2026-11-04 の回帰)。

    台帳の探針(``ledger_contracts._run``)は全型の種を 1 本の乱数列から型名の順に引く。
    ``match`` が列を消費していた間は、名前がそれより後ろの型(mesh / sweep / video /
    volseq / voxel …)の種がすべて変わり、W1 と無関係な 15 個のつまみの判定が動いた。
    ここでは「``match`` を抜いた種の列」と「入れた種の列」で、他の型の値が 1 つも
    変わらないことを、型名の順・辞書の順の両方で確かめる。
    """
    import pickle

    import numpy as np

    import chain_fuzz as cf

    gens = cf.make_generators()
    assert "match" in gens
    rng = np.random.default_rng(20261104)
    before = rng.bit_generator.state
    v1 = gens["match"](rng)
    assert rng.bit_generator.state == before, "match の種が呼び手の乱数列を進めた"
    assert np.array_equal(v1, gens["match"](rng)), "同じ状態から違う値が出た"
    assert v1.shape == (3,) and np.all(np.isfinite(v1))

    def draws(items):
        base = np.random.default_rng(7)
        out = {}
        for t, g in items:
            v = g(base)
            if t != "match":
                out[t] = pickle.dumps(v)
        return out

    without = [(t, g) for t, g in gens.items() if t != "match"]
    for with_order, without_order in ((sorted(gens.items()), sorted(without)),
                                      (list(gens.items()), without)):
        a, b = draws(with_order), draws(without_order)
        assert len(a) >= 60
        moved = sorted(t for t in a if a[t] != b[t])
        assert moved == [], "match の種が他の型の種をずらした: %s" % moved
