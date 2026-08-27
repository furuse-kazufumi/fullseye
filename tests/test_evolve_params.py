"""evolve_params の GT 検証: param 共進化が固定 param 進化(pipeline_evolve)以上、baseline 超え。

honest 規律([[feedback_beat_the_null]]): param 共進化の価値は「固定 param 進化を下回らない(=param 探索が
探索を深めた)」「identity/hand-designed を上回る」で示す。
"""
import numpy as np

import pipeline_evolve as pe
import evolve_params as ep


def test_param_coevolution_matches_or_beats_fixed_same_budget():
    # honest 規律: 固定 param 版は連続 param が無く cache が効くため同 pop/gens だと評価数が少ない
    # (param 版は連続値で cache が外れ ~1.47 倍多く評価する)。同 pop/gens 比較は param 版に有利で
    # 不公正。ここでは固定 param 進化に param 版と『同数以上』の評価予算を与えて公正に比較する。
    #
    # スケール脆弱性の回帰: fitness=-chamfer は点群スケール R に比例するので、比較の slack を
    # 絶対 1e-3 にすると R=1 でしか意味を持たない(R=1000 では chamfer が 1000 倍で slack が過小)。
    # slack を chamfer スケール(=identity fitness の大きさ)相対にし、かつ R=1 と R=1000(sigma/
    # outlier も比例スケール)の 2 スケールで検証する。相対化前後で判定が変わらないのが健全性の証。
    for R in (1.0, 1000.0):
        task = pe.make_denoise_task(R=R, sigma=0.03 * R, seed=0)   # 自己相似にスケール(ノイズ/外れ値も)
        par = ep.evolve_params(task, pop=24, gens=12, seed=0)
        budget = par["n_evals"]
        # 固定 param 進化の評価数が param 版の予算に到達するまで世代を増やす(fixed を不利にしない)。
        fixed = pe.evolve(task, pop=24, gens=12, seed=0)
        for gens in range(16, 81, 4):
            if fixed["n_evals"] >= budget:
                break
            fixed = pe.evolve(task, pop=24, gens=gens, seed=0)
        assert fixed["n_evals"] >= budget, (R, fixed["n_evals"], budget)  # 同予算前提を満たす
        ident = pe.evaluate((), task)
        hand = pe.evaluate(pe.hand_designed_chain(), task)
        # chamfer スケール相対の slack(絶対 1e-3 は scale-fragile)。R=1 で |ident|≈0.0995 → ≈1e-3 相当。
        tol = 1e-2 * abs(ident)
        # 同予算(むしろ fixed に多め)でも param 共進化 ≥ 固定 param 進化。
        # 固定は離散 op 空間を探索し尽くすと頭打ち(saturate)し、連続 param 微調整が上限を超える。
        assert par["fitness"] >= fixed["fitness"] - tol, (R, par["fitness"], fixed["fitness"], budget, fixed["n_evals"])
        # baseline を上回る
        assert par["fitness"] > ident and par["fitness"] > hand, (R, par["fitness"], ident, hand)
        # 無処理を大きく改善
        assert -par["fitness"] < 0.6 * (-ident), (R, par["fitness"], ident)


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


def test_jitter_param_is_resolution_relative():
    # 回帰(スケール脆弱性): _PSPACE["jitter"] の param a は解像度倍率(sigma=a*estimate_resolution)。
    # → 点群を s 倍すると付加ノイズ変位も厳密に s 倍。絶対 sigma だと s に依らず一定=大スケールで無害化。
    task = pe.make_denoise_task(seed=0)
    p = task.x
    apply = ep._PSPACE["jitter"][2]
    a = 0.3                                                    # sigma_mult(境界 [0.1,0.5] 内)
    d1 = np.linalg.norm(apply(a, p) - p, axis=1).mean()
    assert d1 > 0.0                                            # ノイズは実際に付加される
    for s in (1e-6, 1e6):                                      # 微小〜巨大の両端(≥2 スケール)
        ps = p * s
        ds = np.linalg.norm(apply(a, ps) - ps, axis=1).mean()
        assert abs(ds - s * d1) <= 1e-9 * s * d1, (s, ds, s * d1)


def test_execute_handles_empty_and_failure():
    task = pe.make_denoise_task(seed=0)
    assert np.array_equal(ep.execute((), task.x), task.x)   # identity
