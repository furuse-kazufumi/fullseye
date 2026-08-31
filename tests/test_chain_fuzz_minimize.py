# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""連鎖ファザーの収束フェーズ(--minimize / --replay)の回帰。

拡散(ランダム連鎖)で見つけた発見は、そのままでは 6〜8 op の長い trace を
伴う。デバッグに使えるのは「その署名を出す最小の op 列」なので、収束側に
delta debugging を置いた(2026-09-01)。ここで固定する契約:

  1. 連鎖は **連鎖固有 seed** で回り、findings がその seed を持つ
     (共有 rng だと i 番目だけを後から再走できない = 最小化の前提が崩れる)。
  2. script を渡した run_chain は **その順で強制実行**する。
  3. 最小化は無関係な前段だけを落とし、署名は保存される。
  4. 再現しない発見(seed 欠落・非決定的)には **False を返す**
     — 「短縮できた」と嘘をつくと推測パッチを誘発するため。
"""
import numpy as np
import pytest

pytest.importorskip("torch")   # catalog は torch 依存モジュールを束ねる

from tools.chain_fuzz import (catalog, make_generators, minimize_finding,
                              reproduces, run_chain, signature)


@pytest.fixture(scope="module")
def env():
    return catalog(), make_generators()


def test_chain_seed_is_recorded_on_every_finding(env):
    """発見には必ず seed が載る(= 後から正確に再走できる)。"""
    ops, gens = env
    log = []
    for i in range(40):
        seed = 12_345 + i
        run_chain(ops, gens, np.random.default_rng(seed), 6, log, chain_seed=seed)
    assert log, "40 連鎖で 1 件も発見が無い = 探索が壊れている"
    assert all(f.get("seed") is not None for f in log)
    # seed を渡さない旧来の呼び方でも落ちない(None が載るだけ)
    log2 = []
    run_chain(ops, gens, np.random.default_rng(0), 3, log2)
    assert all("seed" in f for f in log2)


def test_script_forces_the_op_order(env):
    """script を渡すと候補ランダム抽選をせず、その op だけを実行する。"""
    ops, gens = env
    log = []
    trace = run_chain(ops, gens, np.random.default_rng(7), 0, log,
                      chain_seed=7, script=["vol_gaussian", "vol_gaussian"])
    # 成功すれば trace に、失敗すれば log に出る。いずれにせよ他の op は動かない
    assert set(trace) <= {"vol_gaussian"}
    assert all(f["op"] == "vol_gaussian" for f in log)
    # 存在しない op 名は黙って飛ばす(短縮の途中で壊れないこと)
    log3 = []
    run_chain(ops, gens, np.random.default_rng(7), 0, log3, chain_seed=7,
              script=["no_such_op_at_all"])
    assert log3 == []


def test_minimize_reduces_and_preserves_the_signature(env):
    """長い trace を持つ発見が 1 op まで縮み、署名が保存される。"""
    ops, gens = env
    log = []
    for i in range(60):
        seed = 3_000_000 + i
        run_chain(ops, gens, np.random.default_rng(seed), 6, log, chain_seed=seed)
    long_ones = [f for f in log if len(f.get("trace") or []) >= 2]
    assert long_ones, "2 op 以上の trace を持つ発見が無い = 前提が崩れている"
    reduced_any = False
    for f in long_ones[:5]:
        script, ok = minimize_finding(ops, gens, f, verbose=False)
        if not ok:
            continue                      # 非決定的な発見は honest に skip
        assert script[-1] == f["op"], "当該 op は末尾に残る"
        assert len(script) <= len(f["trace"])
        assert reproduces(ops, gens, script, f["seed"], signature(f))
        reduced_any = reduced_any or len(script) < len(f["trace"])
    assert reduced_any, "5 件試して 1 件も短縮できない = 削り込みが効いていない"


def test_minimize_is_honest_when_it_cannot_reproduce(env):
    """seed を持たない発見(旧形式 jsonl)は「再現せず」を返す。捏造しない。"""
    ops, gens = env
    stale = {"kind": "SUSPECT", "op": "vol_resize", "exc": "TypeError",
             "msg": "…", "trace": ["vol_resize"]}       # seed 無し
    script, ok = minimize_finding(ops, gens, stale, verbose=False)
    assert (script, ok) == (None, False)
    # trace が空の場合も同様
    assert minimize_finding(ops, gens, {"kind": "SUSPECT", "op": "x", "seed": 1,
                                        "trace": []}, verbose=False) == (None, False)
