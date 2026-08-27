# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""evolve_params — op-chain 進化探索にパラメータ共進化を追加(収束フェーズの深化)。

pipeline_evolve は op の**並び**だけを進化させ各 op は固定デフォルト param だった。本モジュールは
genome を **(op 名, スカラ強度 param) の列**にして、**並びと param を同時進化**させる(共進化)。
これで探索が「どの op をどの強さで」まで最適化でき、固定 param 版より良いパイプラインに届く。

fitness は pipeline_evolve と同じ metrics3d.chamfer(点群デノイズタスクを共用)。honest 規律:
進化(param 共進化)を identity / hand-designed / **固定 param 進化(pipeline_evolve.evolve)** と比較し、
固定 param 版**以上**であることを GT 検証する(param 共進化が探索を深めた証拠)。ただし固定 param 版は
連続 param が無く cache が効くため同 pop/gens だと評価数が少ない(param 版は ~1.47 倍多く評価する)。
公正な比較のため **固定 param 版に param 版と同数以上の評価予算を与えて** 検証する(test 参照)。
固定は離散 op 空間を探索し尽くすと頭打ちになり、連続 param の微調整がその上限を超える。
"""
import numpy as np

import metrics3d
import pcl_filter
import pcl_augment
import pipeline_evolve as pe


def _res(p):
    return pcl_filter.estimate_resolution(p)


# op 名 → (param 下限, 上限, apply(param, points)->points)。全て points→points(このタスクは単一型)。
_PSPACE = {
    "sor": (0.5, 3.0, lambda a, p: pe._pts(pcl_filter.statistical_outlier_removal(p, k=16, std_ratio=a))),
    "mls": (1.5, 5.0, lambda a, p: pe._pts(pcl_filter.mls_smooth(p, radius=a * _res(p), order=2))),
    "voxel": (0.5, 3.0, lambda a, p: pe._pts(pcl_filter.voxel_grid_downsample(p, voxel_size=a * _res(p)))),
    "ror": (1.5, 4.0, lambda a, p: pe._pts(pcl_filter.radius_outlier_removal(p, radius=a * _res(p), min_neighbors=6))),
    "jitter": (0.01, 0.06, lambda a, p: pcl_augment.jitter(p, sigma=a, seed=0)),
    "dropout": (0.05, 0.4, lambda a, p: pe._pts(pcl_augment.random_dropout(p, ratio=a, seed=0))),
}
_OPS = list(_PSPACE)
_PENALTY = -1e9


def _clip(op, a):
    lo, hi, _ = _PSPACE[op]
    return float(min(max(a, lo), hi))


def random_gene(rng, op=None):
    """(op 名, 一様乱数 param) の遺伝子を 1 つ。→ (op, param)。"""
    if op is None:
        op = _OPS[int(rng.integers(len(_OPS)))]
    lo, hi, _ = _PSPACE[op]
    return (op, float(rng.uniform(lo, hi)))


def random_pchain(rng, max_len=4):
    """(op, param) 遺伝子の列(長さ 0..max_len)。→ tuple。"""
    n = int(rng.integers(0, max_len + 1))
    return tuple(random_gene(rng) for _ in range(n))


def execute(chain, x):
    """(op, param) 列を順に適用。失敗/空は None。→ 出力 or None。"""
    cur = np.asarray(x, float)
    for op, a in chain:
        try:
            cur = _PSPACE[op][2](a, cur)
        except Exception:
            return None
        if cur is None or len(cur) == 0:
            return None
    return cur


def evaluate(chain, task, cache=None):
    """fitness = -chamfer(出力, 目標)(大きいほど良い)。失敗は大ペナルティ。"""
    key = tuple((op, round(a, 4)) for op, a in chain)
    if cache is not None and key in cache:
        return cache[key]
    out = execute(chain, task.x)
    fit = _PENALTY if (out is None or len(out) == 0) else -float(task.metric(out, task.target))
    if cache is not None:
        cache[key] = fit
    return fit


def mutate(chain, rng, sigma=0.25):
    """並び(置換/挿入/削除)と param(ガウス摂動)の変異。→ tuple。"""
    g = list(chain)
    kind = rng.integers(4)
    if kind == 0 and g:                                  # op 置換(param は新規乱数)
        g[int(rng.integers(len(g)))] = random_gene(rng)
    elif kind == 1 and len(g) < 5:                        # 挿入
        g.insert(int(rng.integers(len(g) + 1)), random_gene(rng))
    elif kind == 2 and g:                                 # 削除
        g.pop(int(rng.integers(len(g))))
    elif g:                                               # param 摂動(op はそのまま強さを微調整)
        i = int(rng.integers(len(g)))
        op, a = g[i]
        lo, hi, _ = _PSPACE[op]
        a2 = _clip(op, a + rng.normal(0, sigma) * (hi - lo))
        g[i] = (op, a2)
    return tuple(g)


def crossover(a, b, rng, max_len=5):
    """型は単一(points)なので任意点でスプライス。max_len で bloat 抑制。→ tuple。"""
    if not a or not b:
        return (a or b)[:max_len]
    ca = int(rng.integers(len(a) + 1))
    cb = int(rng.integers(len(b) + 1))
    return tuple((list(a[:ca]) + list(b[cb:]))[:max_len])


def evolve_params(task, pop=24, gens=12, elite=3, seed=0, max_len=4):
    """並び + param を共進化。→ dict{best, fitness, n_evals, history}。"""
    rng = np.random.default_rng(seed)
    cache = {}
    population = [random_pchain(rng, max_len) for _ in range(pop)]
    history = []
    for _ in range(gens):
        scored = sorted(population, key=lambda c: evaluate(c, task, cache), reverse=True)
        history.append(evaluate(scored[0], task, cache))
        nxt = list(scored[:elite])
        while len(nxt) < pop:
            def pick():
                cand = [population[int(rng.integers(len(population)))] for _ in range(3)]
                return max(cand, key=lambda c: evaluate(c, task, cache))
            child = crossover(pick(), pick(), rng, max_len)
            if rng.random() < 0.7:
                child = mutate(child, rng)
            nxt.append(child)
        population = nxt
    best = max(population, key=lambda c: evaluate(c, task, cache))
    return {"best": best, "fitness": evaluate(best, task, cache),
            "n_evals": len(cache), "history": history}


def describe(chain):
    """(op, param) 列を読みやすい文字列に。"""
    return " → ".join(f"{op}({a:.2f})" for op, a in chain) if chain else "(identity)"
