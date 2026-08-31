# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""連鎖採掘器(拡散フェーズ)の契約。

``tools/chain_mine.py`` はファザーの裏返しで、**成功した合成**を振る舞い記述子
つきで記録する。ここで固定するのは 3 つ:

  1. **恒等に近い連鎖は落ちる** — 入力とほぼ同じものを返す鎖に価値は無い。
     実物の往復(``cx_fft`` → ``cx_ifft``、delta = 0.0)で確かめる。
  2. **決定性** — 同じ seed の 2 回走は実測秒を除いてビット一致する。
     壁時計だけは測定値なので原理的に一致しない(``stable_record`` で除く)。
     選抜を秒に依存させると 95 代表中 4 件が走るたびに入れ替わった(実測)。
  3. **ビン分けが多様性を保つ** — 単一スコアの上位 N 件を取ると同じ発見ばかりに
     なる(多様性の崩壊)。格子で間引くと同じ件数でより多くのセルを覆う。

加えて **無言の切り捨て禁止** を機械で強制する: 完走した候補は必ず
「代表」か「理由つきで落とした」かのどちらかに勘定が合う。
"""
import numpy as np
import pytest

pytest.importorskip("torch")   # catalog は torch 依存モジュールを束ねる

from tools import chain_fuzz as cf
from tools.chain_mine import (IDENTITY_EPS, bin_key, contract, describe,
                              _init_pool, mine, mine_chain, replay_chain,
                              stable_record)


@pytest.fixture(scope="module")
def env():
    return cf.catalog(), cf.make_generators()


@pytest.fixture(scope="module")
def mined(env):
    """200 連鎖 x len 5 の実採掘(モジュール内で使い回す)。"""
    ops, gens = env
    cands, tally, _wall = mine(ops, gens, 200, 5, 3)
    assert cands, "200 連鎖で 1 件も完走しない = 採掘器が壊れている"
    return cands, tally


# --------------------------------------------------------------------------- #
# (a) 恒等に近い連鎖が落ちる                                                    #
# --------------------------------------------------------------------------- #
def test_identity_roundtrip_is_measured_as_zero_delta(env):
    """実物の往復(FFT → 逆 FFT)は delta = 0 / corr = 1 と測れる。"""
    ops, gens = env
    y, out_type, sec = replay_chain(ops, gens, 7, "image2d",
                                    ["cx_fft", "cx_ifft"], [1, 1])
    assert y is not None and out_type == "image2d"
    x = _init_pool(gens, np.random.default_rng(7))["image2d"][0]
    d = describe(x, y, "image2d", out_type, ["cx_fft", "cx_ifft"], sec)
    assert d["delta"] == 0.0 and d["corr"] == 1.0
    assert d["delta"] < IDENTITY_EPS


def test_identity_like_candidate_is_dropped_with_a_reason(env):
    """恒等に近い候補は収縮で落ち、``identity_like`` として**数えられる**。"""
    ops, gens = env
    y, out_type, sec = replay_chain(ops, gens, 7, "image2d",
                                    ["cx_fft", "cx_ifft"], [1, 1])
    x = _init_pool(gens, np.random.default_rng(7))["image2d"][0]
    ident = {"seed": 7, "start": "image2d", "ops": ["cx_fft", "cx_ifft"],
             "arg_keys": [1, 1], "out_type": out_type, "deterministic": True,
             "desc": describe(x, y, "image2d", out_type,
                              ["cx_fft", "cx_ifft"], sec)}
    reps, dropped = contract([ident], ops, gens)
    assert reps == []
    assert dropped["identity_like"] == 1


def test_constant_slow_and_nondeterministic_are_dropped(env):
    """(b) 定数 (c) 非決定 (d) 遅すぎ も理由つきで落ちる。"""
    ops, gens = env

    def cand(seed, **over):
        d = {"in_type": "image2d", "out_type": "image2d", "n_ops": 2,
             "sec": 0.01, "delta": 0.5, "corr": 0.1, "same_type": True,
             "size": 1024, "finite_frac": 1.0, "mean": 1.0, "std": 0.5,
             "vmin": 0.0, "vmax": 2.0, "rel_std": 0.25, "entropy": 0.7,
             "nonzero": 1.0, "log_size_ratio": 0.0}
        d.update(over.pop("desc", {}))
        return {"seed": seed, "start": "image2d", "ops": ["a", "b"],
                "arg_keys": [1, 1], "out_type": "image2d",
                "deterministic": True, "desc": d, **over}

    reps, dropped = contract(
        [cand(1, desc={"rel_std": 1e-18, "std": 0.0}),      # 定数に潰れた
         cand(2, deterministic=False),                       # 非決定的
         cand(3, desc={"sec": 60.0}),                        # 遅すぎる
         cand(4, desc={"size": 0, "rel_std": None})],        # 数値内容が無い
        ops, gens)
    assert reps == []
    assert dropped["const_output"] == 1
    assert dropped["nondeterministic"] == 1
    assert dropped["too_slow"] == 1
    assert dropped["no_numeric_output"] == 1


def test_nothing_is_discarded_silently(env, mined):
    """完走した候補は「代表」か「理由つきで落とした」かに必ず勘定が合う。"""
    ops, gens = env
    cands, _tally = mined
    reps, dropped = contract(cands, ops, gens)
    assert len(cands) == len(reps) + sum(dropped.values())
    assert reps, "全部落ちる = 閾値が厳しすぎる"


# --------------------------------------------------------------------------- #
# (b) 決定性                                                                    #
# --------------------------------------------------------------------------- #
def test_same_seed_gives_identical_records(env):
    """同じ seed の 2 回走は**実測秒を除いて**完全一致する。"""
    ops, gens = env
    a, _ta, _wa = mine(ops, gens, 60, 4, 11)
    b, _tb, _wb = mine(ops, gens, 60, 4, 11)
    assert a and len(a) == len(b)
    assert [stable_record(r) for r in a] == [stable_record(r) for r in b]
    ra, _da = contract(a, ops, gens)
    rb, _db = contract(b, ops, gens)
    assert [stable_record(r) for r in ra] == [stable_record(r) for r in rb]


def test_replay_reproduces_the_mined_output(env):
    """記録した (seed, 開始型, op 列, 抽選回数) で出力がビット単位で再現する。

    失敗 op はプールに何も足さないため、成功列だけの再走で各 step のプールは
    採掘時と同一 — これが崩れると ``deterministic`` の判定が全件 False になる。
    """
    ops, gens = env
    checked = 0
    for i in range(40):
        got = mine_chain(ops, gens, 500_000 + i, 4)
        if got is None:
            continue
        y, t, _sec = replay_chain(ops, gens, got["seed"], got["start"],
                                  got["ops"], got["arg_keys"])
        assert t == got["out_type"], got["ops"]
        if isinstance(y, np.ndarray) and isinstance(got["y_out"], np.ndarray):
            assert np.array_equal(y, got["y_out"], equal_nan=True), got["ops"]
        checked += 1
    assert checked >= 5, "再走を検査できた連鎖が少なすぎる"


def test_determinism_flag_is_actually_evaluated(env, mined):
    """``deterministic`` は None(検査省略)か bool。捏造の True を置かない。"""
    cands, _tally = mined
    assert all(c["deterministic"] in (None, True, False) for c in cands)
    assert any(c["deterministic"] is True for c in cands), "検査が動いていない"


# --------------------------------------------------------------------------- #
# (c) ビン分けが多様性を保つ                                                    #
# --------------------------------------------------------------------------- #
def test_grid_keeps_one_representative_per_cell(env, mined):
    ops, gens = env
    cands, _tally = mined
    reps, _dropped = contract(cands, ops, gens)
    keys = [bin_key(r["desc"]) for r in reps]
    assert len(set(keys)) == len(reps), "同じセルに 2 件残っている"
    assert all(r["bin_members"] >= 1 for r in reps)
    assert sum(r["bin_members"] for r in reps) >= len(reps)


def test_grid_beats_single_score_ranking_on_diversity(env, mined):
    """**同じ件数**で比べて、格子は単一スコアの上位取りより広く覆う。

    「変化量が大きいほど良い」式の 1 次元ランキングは同じ発見ばかり残す
    (多様性の崩壊)。ここでは entropy を素朴なスコアに見立てて比較する。
    """
    ops, gens = env
    cands, _tally = mined
    reps, _dropped = contract(cands, ops, gens)
    n = len(reps)
    scored = [c for c in cands if c["desc"]["entropy"] is not None]
    top = sorted(scored, key=lambda c: (-c["desc"]["entropy"], c["seed"]))[:n]
    cells_grid = {bin_key(r["desc"]) for r in reps}
    cells_top = {bin_key(c["desc"]) for c in top}
    assert len(cells_grid) > len(cells_top), (len(cells_grid), len(cells_top))
    types_grid = {r["out_type"] for r in reps}
    types_top = {c["out_type"] for c in top}
    assert len(types_grid) >= len(types_top)


def test_descriptor_is_multidimensional_not_a_single_score(env, mined):
    """記述子は「良さ」の 1 スコアに潰さない(判定は後段の別ツールの責務)。"""
    cands, _tally = mined
    keys = set(cands[0]["desc"])
    for must in ("delta", "corr", "entropy", "nonzero", "std", "rel_std",
                 "log_size_ratio", "n_ops", "sec", "in_type", "out_type"):
        assert must in keys, must
    assert not {"score", "quality", "fitness"} & keys


# --------------------------------------------------------------------------- #
# メモリ暴走の防波堤(ファザーと同じ上限を共有していること)                    #
# --------------------------------------------------------------------------- #
def test_growth_guard_shares_the_fuzzer_limit():
    from tools.chain_mine import MAX_POOL_BYTES
    assert MAX_POOL_BYTES == cf.MAX_POOL_BYTES


def test_chain_threads_the_input_through_every_step(env):
    """各 step は直前の産物を必ず食う(= 連鎖全体が 1 つの写像になっている)。"""
    ops, gens = env
    by_name = {o[0]: o for o in ops}
    found = 0
    for i in range(60):
        got = mine_chain(ops, gens, 700_000 + i, 4)
        if got is None:
            continue
        cur = got["start"]
        for name in got["ops"]:
            ins = by_name[name][2]
            assert cur in ins or "any" in ins, (cur, name, ins)
            cur = by_name[name][3]
        assert cur == got["out_type"]
        assert len(got["ops"]) >= 2, "1 op は合成ではない"
        found += 1
    assert found >= 5
