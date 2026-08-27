"""evolve_params の GT 検証: param 共進化が固定 param 進化(pipeline_evolve)以上、baseline 超え。

honest 規律([[feedback_beat_the_null]]): param 共進化の価値は「固定 param 進化を下回らない(=param 探索が
探索を深めた)」「identity/hand-designed を上回る」で示す。
"""
import numpy as np

import pipeline_evolve as pe
import evolve_params as ep


def test_param_coevolution_matches_or_beats_fixed():
    task = pe.make_denoise_task(seed=0)
    fixed = pe.evolve(task, pop=24, gens=12, seed=0)
    par = ep.evolve_params(task, pop=24, gens=12, seed=0)
    ident = pe.evaluate((), task)
    hand = pe.evaluate(pe.hand_designed_chain(), task)
    # param 共進化は固定 param 進化以上(param 探索が探索を深める)
    assert par["fitness"] >= fixed["fitness"] - 1e-3, (par["fitness"], fixed["fitness"])
    # baseline を上回る
    assert par["fitness"] > ident and par["fitness"] > hand
    # 無処理を大きく改善
    assert -par["fitness"] < 0.6 * (-ident)


def test_deterministic():
    task = pe.make_denoise_task(seed=0)
    a = ep.evolve_params(task, pop=20, gens=8, seed=5)
    b = ep.evolve_params(task, pop=20, gens=8, seed=5)
    assert a["best"] == b["best"] and a["fitness"] == b["fitness"]


def test_history_non_decreasing():
    task = pe.make_denoise_task(seed=1)
    ev = ep.evolve_params(task, pop=24, gens=12, seed=1)
    h = ev["history"]
    assert all(h[i + 1] >= h[i] - 1e-9 for i in range(len(h) - 1)), h


def test_params_within_bounds():
    # 進化した genome の param は各 op の [lo,hi] 内(clip が効いている)
    task = pe.make_denoise_task(seed=2)
    ev = ep.evolve_params(task, pop=20, gens=8, seed=2)
    for op, a in ev["best"]:
        lo, hi, _ = ep._PSPACE[op]
        assert lo - 1e-9 <= a <= hi + 1e-9, (op, a, lo, hi)


def test_execute_handles_empty_and_failure():
    task = pe.make_denoise_task(seed=0)
    assert np.array_equal(ep.execute((), task.x), task.x)   # identity
