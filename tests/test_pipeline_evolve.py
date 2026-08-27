"""pipeline_evolve の GT 検証: 進化が baseline(identity/random/hand)を上回り、文法が型整合であること。

honest 規律([[feedback_beat_the_null]]): 進化の価値は「無処理を大きく改善」「hand-designed を下回らない」
「同予算の random search 以上」で示す。加えて文法(ops3d 型整合)が袋小路を枝刈りすることを検証する。
"""
import numpy as np

import pipeline_evolve as pe


def test_evolution_beats_identity_and_matches_hand():
    task = pe.make_denoise_task(seed=0)
    ev = pe.evolve(task, pop=24, gens=12, seed=0)
    ident = pe.evaluate((), task)                       # 無処理(ノイズ+外れ値のまま)
    hand = pe.evaluate(pe.hand_designed_chain(), task)  # SOR→MLS
    # 無処理を大きく改善(chamfer が 0.6 倍未満)
    assert -ev["fitness"] < 0.6 * (-ident), (-ev["fitness"], -ident)
    # hand-designed を下回らない(このタスクでは実際に上回る)
    assert ev["fitness"] >= hand, (ev["fitness"], hand)


def test_evolution_at_least_matches_random_same_budget():
    task = pe.make_denoise_task(seed=0)
    ev = pe.evolve(task, pop=24, gens=12, seed=0)
    rs = pe.random_search(task, ev["n_evals"], seed=100)
    ident = pe.evaluate((), task)
    # 探索(進化も random も)は無処理より良い
    assert ev["fitness"] > ident and rs["fitness"] > ident
    # 進化は同じ評価予算の random search 以上(このタスクは探索空間が小さく差は僅少=honest)
    assert ev["fitness"] >= rs["fitness"] - 1e-3, (ev["fitness"], rs["fitness"])


def test_grammar_type_valid_and_prunes_deadends():
    # normals は袋小路(VOCAB に normals→ op が無い)→ 後続候補は空
    assert pe.valid_successors("normals") == []
    task = pe.make_denoise_task(seed=1)
    ev = pe.evolve(task, pop=20, gens=8, seed=1)
    # best は goal 型で終わり、袋小路 op を含まない
    assert pe._chain_out_type(ev["best"], task.input_type) == task.goal_type
    assert "estimate_point_normals" not in ev["best"]


def test_random_chain_always_type_valid():
    task = pe.make_denoise_task(seed=2)
    rng = np.random.default_rng(0)
    for _ in range(200):
        c = pe.random_chain(rng, task)
        t = task.input_type
        for op in c:
            assert pe.VOCAB[op]["in"] == t     # 各 op の入力型 == 直前の出力型
            t = pe.VOCAB[op]["out"]
        assert t == task.goal_type             # goal 型で終わる


def test_deterministic():
    task = pe.make_denoise_task(seed=0)
    a = pe.evolve(task, pop=20, gens=8, seed=7)
    b = pe.evolve(task, pop=20, gens=8, seed=7)
    assert a["best"] == b["best"] and a["fitness"] == b["fitness"]


def test_history_non_decreasing():
    # エリート保存 → 各世代の best fitness は悪化しない
    task = pe.make_denoise_task(seed=0)
    ev = pe.evolve(task, pop=24, gens=12, seed=0)
    h = ev["history"]
    assert all(h[i + 1] >= h[i] - 1e-9 for i in range(len(h) - 1)), h
