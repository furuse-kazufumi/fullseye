# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""型付き台帳の**全 op**(索引の ledger 層、2,130 本)に契約の門を立てる。

★2026-10-11: 変異探針(わざと壊した op を各層へ差し込み、どのテストが捕まえるかを
数えた)で、**tb_* に橋の無い台帳 op はほぼ無検査**だと分かった。橋のある op は橋経由で
13 の門(test_op_contracts / test_op_probe_ledger / 決定性 / liveness …)に掛かるが、
橋の無い op(``opsspc`` の table→table、``ops3d`` / ``measure3d`` …)は、例外を投げても、
NaN を返しても、宣言と違う sort を返しても、種なし乱数で毎回違っても**スイート全体が緑**
だった。3-D 台帳に在ったのは「生の例外」と「宣言 out 型」の 2 本だけ。

ここでは全台帳 op を、宣言 in sort から作った代表入力(連鎖ファザーの生成器・
``OP_ARG_BUILDERS``・型の不動点閉包をそのまま再利用)で呼び、4 つの契約を見る:

1. 例外を投げない(``ValueError`` は型つきの拒否として別勘定 ``refused``)
2. 数値の出力が有限(``NONFINITE_BY_CONTRACT`` は契約として免除)
3. 出力が宣言 out sort の述語(``TYPE_CHECKS``)を通る
4. 同じ入力の 2 回の呼び出しが同じ値を返す(決定的)

★**一括修正はしない。** 既存 op の違反は ``docs/LEDGER_CONTRACT_DEBT.json`` に契約ごと・
理由の区分つきで固定し、(a) 台帳に無い op が違反したら落ちる、(b) 台帳に在る op が
通るようになったら落ちる(= 台帳は縮むしかない)。``docs/VACUOUS_ASSERTION_DEBT.json``
と同じラチェット。直したら ``py -3.11 tools/ledger_contracts.py --write`` で台帳を下げる。

★**環境で台帳が変わらないこと。** optional backend が無い環境(CI の py3.10 / 3.12 は
torch も open3d も無い)で ``ImportError`` / ``NotImplementedError`` になる op は
``skip``(理由つき)で、合格にも失格にも数えない。台帳に在る op が skip になっても
「直った」とは見なさない。
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (ROOT, os.path.join(ROOT, "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

lc = pytest.importorskip(
    "ledger_contracts", reason="tools/ledger_contracts.py が読めない(探針の正本)")

#: 実際に呼べた(値を返した or 契約違反として判定まで進んだ)op の下限。
#: このコミット時点の実測から少し下げた床。範囲が黙って縮むのを止めるためのもの。
#: 実測 2026-10-11: 手元(全 optional あり)1,919 / CI py3.10・3.12 相当(torch・open3d・
#: sklearn … を import で塞いで再現)1,884。違いは torch が要る 29 op とその下流 8 op が
#: skip になる分だけ(判定が skip 以外へ動いた op は 0)。床はその下に置く。
#: ★同日の 2 回目: 探針側の builder(``ledger_contracts.probe_builders``)で 2,055 / CI 相当
#: 2,019 に上がったので床も上げた(床を据え置くと、builder が黙って外れても気づけない)。
EXECUTED_FLOOR = 2000

@pytest.fixture(scope="module")
def probe():
    t0 = time.perf_counter()
    v = lc.run()
    return v, time.perf_counter() - t0


@pytest.fixture(scope="module")
def debt():
    with open(lc.DEBT, encoding="utf-8") as f:
        return json.load(f)["debt"]


def _index_ledger_count():
    with open(os.path.join(ROOT, "docs", "OP_INDEX.json"), encoding="utf-8") as f:
        return sum(1 for r in json.load(f)["ops"] if r.get("tier") == "ledger")


# --------------------------------------------------------------------------- #
def test_scope_is_the_whole_ledger_tier(probe, capsys):
    """探針が判定した op の数 == 索引の ledger 層の数(黙って範囲を縮めない)。

    数えるのは**配布物の側**(``docs/OP_INDEX.json`` と ``api.ledger_rows``)から。
    探針が自分で範囲を読むと、範囲ごと縮んでも門は緑のままになる。
    """
    verdict, sec = probe
    import api
    names = {r["name"] for r in api.ledger_rows()}
    assert set(verdict) == names, {"not_probed": sorted(names - set(verdict))[:20],
                                   "not_in_index": sorted(set(verdict) - names)[:20]}
    assert len(verdict) == _index_ledger_count(), (len(verdict), _index_ledger_count())
    executed = lc.executed(verdict)
    with capsys.disabled():
        print("\n== 台帳契約の門: %.1f s\n%s\n   値を返した op %d"
              % (sec, lc.summary(verdict), len(executed)))
        skipped = sorted(n for n, v in verdict.items() if v["status"] == "skip")
        if skipped:
            print("   optional backend が無く判定しなかった op %d 本: %s"
                  % (len(skipped), ", ".join(skipped[:30])))
    assert len(executed) >= EXECUTED_FLOOR, (
        "値を返すところまで届いた台帳 op が床 %d を割った: %d"
        % (EXECUTED_FLOOR, len(executed)))


def test_no_new_contract_violation(probe, debt):
    """台帳(``LEDGER_CONTRACT_DEBT.json``)に無い違反が出たら落ちる。

    落ちたら**新しく書いた op を直す**(台帳に足すのではない)。探針の入力が本当に
    その op にとって不正なら、``chain_fuzz.OP_ARG_BUILDERS`` / ``OP_PARAM_HINTS`` に
    正しい入力を足すのが筋。
    """
    verdict, _ = probe
    new = lc.new_violations(verdict, debt)
    assert not new, ("台帳に無い契約違反(新規):\n" + "\n".join(
        "  [%s] %s: %s" % (c, n, d) for c, n, d in new[:60]))


def test_the_debt_only_shrinks(probe, debt):
    """台帳に在るのに、その契約を**通った** op があれば落ちる(直したら台帳から消す)。

    skip(この環境に backend が無い)は「通った」に数えない —— 環境差で台帳が
    揺れないように。
    """
    verdict, _ = probe
    stale = lc.stale_debt(verdict, debt)
    assert not stale, ("台帳に在るが、もうその契約を破っていない(台帳から消すこと。"
                       "py -3.11 tools/ledger_contracts.py --write):\n" + "\n".join(
                           "  [%s] %s -> %s" % s for s in stale[:60]))


def test_every_debt_row_has_a_known_reason(debt):
    """台帳の各行は契約名の下にあり、理由の区分(文字列)を持つ。空の台帳は失格。"""
    assert set(debt) == set(lc.CHECKS), sorted(set(debt) ^ set(lc.CHECKS))
    rows = [(c, n, r) for c in debt for n, r in debt[c].items()]
    assert rows, "台帳が空 —— 空の台帳はこの門を素通りさせるので失格にする"
    bad = [(c, n, r) for c, n, r in rows if not lc.known_category(c, r)]
    assert not bad, bad[:20]


def test_none_and_volatile_contracts_are_exact(probe):
    """None を契約として許す op・決定性から外す欄は、**ちょうど実在するものだけ**。

    ``NONE_BY_CONTRACT`` に載っているのに値を返した op は表から消す(載せたままだと、
    いつか本当に None を返すようになっても素通りする)。backend 欠落の skip は別扱い。
    """
    verdict, _ = probe
    import api
    names = {r["name"] for r in api.ledger_rows()}
    assert set(lc.NONE_BY_CONTRACT) <= names, sorted(set(lc.NONE_BY_CONTRACT) - names)
    assert set(lc.VOLATILE_FIELDS) <= names, sorted(set(lc.VOLATILE_FIELDS) - names)
    stale = sorted(n for n in lc.NONE_BY_CONTRACT
                   if verdict[n]["status"] != "skip" and not verdict[n].get("returned_none"))
    assert not stale, "NONE_BY_CONTRACT に在るが None を返さなかった op: %s" % stale
    for n, why in lc.NONE_BY_CONTRACT.items():
        assert isinstance(why, str) and len(why) > 20, n


# --------------------------------------------------------------------------- #
# 門を壊して確かめる                                                            #
# --------------------------------------------------------------------------- #
def _raise(x):
    raise TypeError("fake op broke")


def _nan(x):
    out = np.asarray(x, dtype=float).copy()
    out[0, 0] = np.nan
    return out


def _wrong_sort(x):
    return "not an image"


def _random(x):
    return np.asarray(x, dtype=float) + np.random.default_rng().random(np.shape(x))


def _global_random(x):
    return np.asarray(x, dtype=float) + np.random.random(np.shape(x))


def _refuse(x):
    raise ValueError("fake op refuses this input")


def _missing_backend(x):
    raise ImportError("fake op needs the optional torch")


def _good(x):
    return np.asarray(x, dtype=float) * 0.5


def _none(x):
    return None


def _timed(x):
    import time as _t
    return {"value": np.asarray(x, dtype=float) * 2.0, "seconds": _t.perf_counter()}


_FAKES = {
    "zz_fake_raise": (_raise, ("fail", ["raises"])),
    "zz_fake_nan": (_nan, ("fail", ["nonfinite"])),
    "zz_fake_wrong_sort": (_wrong_sort, ("fail", ["sort"])),
    "zz_fake_random": (_random, ("fail", ["nondeterministic"])),
    "zz_fake_global_random": (_global_random, ("fail", ["nondeterministic"])),
    "zz_fake_refuse": (_refuse, ("fail", ["refused"])),
    "zz_fake_missing_backend": (_missing_backend, ("skip", None)),
    "zz_fake_good": (_good, ("ok", None)),
    "zz_fake_none": (_none, ("fail", ["sort"])),
    "zz_fake_none_by_contract": (_none, ("ok", None)),
    "zz_fake_timed": (_timed, ("fail", ["nondeterministic"])),
    "zz_fake_timed_volatile": (_timed, ("ok", None)),
}


def test_each_check_catches_a_planted_broken_op(monkeypatch):
    """★わざと壊した偽 op を**本物の台帳表へ**差し込み、各契約が捕まえることを見る。

    偽 op は索引の列挙(``api.ledger_rows``)を通って探針に届くので、「列挙に載る」
    ことと「各検査が鳴る」ことを同時に確かめる。健全な対照(``zz_fake_good``)が
    ok であること、backend 欠落が skip(失格ではない)であることも見る —— 片方だけ
    では、常に鳴る門でも常に黙る門でも通ってしまう。
    """
    import ops3d
    # 契約の表に載せた偽 op だけが通ることも見る(表の外の None / 時刻は落ちる)
    monkeypatch.setitem(lc.NONE_BY_CONTRACT, "zz_fake_none_by_contract", "a fake in-place op for this test")
    monkeypatch.setitem(lc.VOLATILE_FIELDS, "zz_fake_timed_volatile", ("seconds",))
    for name, (fn, _) in _FAKES.items():
        out = "table" if name.startswith("zz_fake_timed") else "image2d"
        monkeypatch.setitem(ops3d.OPS3D, name, {"in": ["image2d"], "out": out,
                                                "category": "fake", "func": fn})
    ops = [o for o in lc.ledger_ops() if o[0] in _FAKES]
    assert sorted(o[0] for o in ops) == sorted(_FAKES), "偽 op が索引の列挙に載らない"
    verdict = lc.run(ops=ops)
    for name, (_, (status, checks)) in _FAKES.items():
        v = verdict[name]
        assert v["status"] == status, (name, v)
        if checks is not None:
            assert v["check"] == checks, (name, v)
    cats = lc.debt_from(verdict)
    assert cats["raises"]["zz_fake_raise"] == "raw_TypeError"
    assert cats["nondeterministic"]["zz_fake_random"] == "fresh_state"
    assert cats["nondeterministic"]["zz_fake_global_random"] == "global_rng"
    # ラチェットも鳴る: 空の台帳に対して 6 件が「新規」、skip と ok は数えない
    empty = {c: {} for c in lc.CHECKS}
    assert sorted(n for _, n, _ in lc.new_violations(verdict, empty)) == sorted(
        n for n, (_, (s, _)) in _FAKES.items() if s == "fail")
    # 台帳に載せたまま直した(= 通る)op は stale、skip の op は stale にしない
    listed = {c: {} for c in lc.CHECKS}
    listed["raises"]["zz_fake_good"] = "raw_TypeError"
    listed["raises"]["zz_fake_missing_backend"] = "raw_TypeError"
    assert [s[1] for s in lc.stale_debt(verdict, listed)] == ["zz_fake_good"]


def test_value_helpers_compare_and_scan_structurally():
    """決定性と有限性の判定器そのもの(dict / list / 物体の属性まで見る)。"""
    class Box:
        def __init__(self, v):
            self.v = v
    assert lc.same({"a": np.array([1.0, np.nan])}, {"a": np.array([1.0, np.nan])}) is True
    assert lc.same([1.0, 2.0], [1.0, 2.5]) is False
    assert lc.same(Box(np.zeros(3)), Box(np.ones(3))) is False
    assert lc.same(np.zeros(3, np.float32), np.zeros(3, np.float64)) is False
    assert lc.nonfinite({"x": [1.0, Box(np.array([np.inf]))]})
    assert lc.nonfinite(float("nan"))
    assert not lc.nonfinite({"x": [1, 2.0, "nan", Box(np.zeros(2))]})
