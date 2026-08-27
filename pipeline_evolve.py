# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""pipeline_evolve — 3D op-chain の進化探索 PoC(発散の収束: 手動 op×op 採点 → fitness 自動探索)。

**核心**: これまでの発散(ops3d = 192 op)で「手で op×op を並べ実現性 F × 差別化 D で採点し優先度化」
してきた営みは、**進化アルゴリズムが fitness で自動化する工程そのもの**。本 PoC はそれを実体化する:

  1. **文法(探索空間)** = `ops3d` の型整合。各 op は入力種別→出力種別を持ち、出力=次の入力が合う
     op だけが連結できる(`ops3d.compatible`)。型が合わない連結は文法段階で自動枝刈りされる。
  2. **fitness** = `metrics3d`(chamfer 等)。パイプラインの出力を GT と比べた距離が小さいほど良い。
  3. **探索** = 遺伝的アルゴリズム(トーナメント選択・型保存変異・型整合交叉・エリート)で
     良い op-chain を自動発見する。= `register_auto`(データを見てルールで手法選択)の一般化。

honest 規律([[feedback_beat_the_null]]): 進化の best を **identity(無処理)/ random search(同評価予算)/
hand-designed(既知の良パイプライン)** と必ず比較する。進化がこれらを上回らなければ価値がない。

PoC タスク = 点群デノイズ(ノイズ+外れ値を除去して clean 表面に近づける)。VOCAB は ops3d の
preprocess(SOR/radius/voxel/MLS)+ augment(jitter/dropout=有害/中立)+ transform(法線推定=型の袋小路)。
"""
import numpy as np

import ops3d
import metrics3d
import pcl_filter
import pcl_augment
import match3d


# ---- op adapter: ops3d op を「デフォルト param で単一入力 実行可能」に包む ----------------
def _pts(x):
    """tuple を返す op はデータ本体(先頭)を取る。"""
    return x[0] if isinstance(x, tuple) else x


def _sor(p):
    return _pts(pcl_filter.statistical_outlier_removal(p, k=16, std_ratio=2.0))


def _ror(p):
    res = pcl_filter.estimate_resolution(p)
    return _pts(pcl_filter.radius_outlier_removal(p, radius=2.5 * res, min_neighbors=6))


def _voxel(p):
    res = pcl_filter.estimate_resolution(p)
    return _pts(pcl_filter.voxel_grid_downsample(p, voxel_size=1.5 * res))


def _mls(p):
    res = pcl_filter.estimate_resolution(p)
    return _pts(pcl_filter.mls_smooth(p, radius=3.0 * res, order=2))


# jitter の sigma は点群解像度に相対的(sigma_mult * estimate_resolution)。他の op(ror/voxel/mls)は
# 既に k*resolution で scale 適応するのに対し、絶対 sigma だと大スケールで無害化・小スケールで破壊的になり
# 「jitter=有害ノイズ」という文法前提が崩れる。res 相対なら任意スケールで一定強度の有害ノイズになる。
_JITTER_SIGMA_MULT = 0.28                                     # R=1 デノイズタスクで従来 sigma≈0.03 相当


def _jitter(p):
    sigma = _JITTER_SIGMA_MULT * pcl_filter.estimate_resolution(p)
    return pcl_augment.jitter(p, sigma=sigma, seed=0)         # 有害(解像度相対のノイズ付加)


def _dropout(p):
    return _pts(pcl_augment.random_dropout(p, ratio=0.2, seed=0))  # 中立(無作為 20% 除去)


def _normals(p):
    return match3d.estimate_point_normals(p)                  # points→normals(型の袋小路)


# VOCAB = ops3d の op 名 → adapter。型(in/out)は ops3d.info から引く(= 文法は ops3d 由来)。
_ADAPTERS = {
    "statistical_outlier_removal": _sor,
    "radius_outlier_removal": _ror,
    "voxel_grid_downsample": _voxel,
    "mls_smooth": _mls,
    "jitter": _jitter,
    "random_dropout": _dropout,
    "estimate_point_normals": _normals,
}


def _op_type(name):
    """ops3d.info から (入力種別, 出力種別) を取る(単一入力 op を前提)。"""
    info = ops3d.info(name)
    ins = info["in"]
    return ins[0], info["out"]


VOCAB = {name: {"fn": _ADAPTERS[name], "in": _op_type(name)[0], "out": _op_type(name)[1]}
         for name in _ADAPTERS}


# ---- タスク定義 --------------------------------------------------------------------------
class Task:
    """進化探索の 1 タスク: 入力・目標・型・fitness メトリクス。"""

    def __init__(self, x, target, input_type, goal_type, metric, name=""):
        self.x = np.asarray(x, float)
        self.target = np.asarray(target, float)
        self.input_type = input_type
        self.goal_type = goal_type
        self.metric = metric            # (out, target) -> float(小さいほど良い)
        self.name = name


def _fib_sphere(n, R, seed=0):
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    gold = np.pi * (1 + 5 ** 0.5)
    th = gold * i
    return R * np.stack([np.sin(phi) * np.cos(th), np.sin(phi) * np.sin(th), np.cos(phi)], 1)


def make_denoise_task(n=700, R=1.0, sigma=0.03, n_outliers=90, seed=0):
    """点群デノイズタスク: clean 球面 + ガウスノイズ + 一様外れ値 → clean を目標に chamfer 最小化。"""
    rng = np.random.default_rng(seed)
    clean = _fib_sphere(n, R)
    noisy = clean + rng.normal(0, sigma, clean.shape)
    outliers = rng.uniform(-2 * R, 2 * R, size=(n_outliers, 3))
    x = np.vstack([noisy, outliers])
    return Task(x, clean, "points", "points",
                metric=lambda out, tgt: metrics3d.chamfer_distance(out, tgt),
                name="denoise")


# ---- 文法(ops3d の型整合で連結可能な op を列挙)------------------------------------------
def valid_successors(cur_type):
    """現在の型を入力に取れる VOCAB op 名(= ops3d 型整合な後続候補)。"""
    return [n for n, m in VOCAB.items() if m["in"] == cur_type]


def _chain_out_type(chain, input_type):
    t = input_type
    for op in chain:
        t = VOCAB[op]["out"]
    return t


def random_chain(rng, task, max_len=4):
    """型整合に成長し goal_type で終わる op-chain を生成(袋小路は自動回避)。→ tuple(op名...)。"""
    for _ in range(30):                          # 数回試行(袋小路なら破棄して再生成)
        chain = []
        t = task.input_type
        target_len = int(rng.integers(0, max_len + 1))
        ok = True
        while len(chain) < target_len:
            succ = valid_successors(t)
            if not succ:
                ok = False
                break
            op = succ[int(rng.integers(len(succ)))]
            chain.append(op)
            t = VOCAB[op]["out"]
        if ok and t == task.goal_type:
            return tuple(chain)
    return tuple()                               # 空(identity)は必ず goal 型(points→points)


# ---- 実行と fitness ----------------------------------------------------------------------
_PENALTY = -1e9


def execute(chain, x):
    """op-chain を順に適用。入力/中間/出力が空、または失敗は None。→ 出力配列 or None。"""
    cur = np.asarray(x, float)
    if len(cur) == 0:                # 空入力は identity でも素通しさせず fail-closed
        return None
    for op in chain:
        try:
            cur = VOCAB[op]["fn"](cur)
        except Exception:
            return None
        if cur is None or len(cur) == 0:
            return None
    return cur


def evaluate(chain, task, cache=None):
    """fitness = -metric(出力, 目標)(大きいほど良い)。失敗/空出力は大ペナルティ(nan 詐称禁止)。"""
    if cache is not None and chain in cache:
        return cache[chain]
    out = execute(chain, task.x)
    # 空出力(len==0)も None と同列に扱う: metric を呼ばず _PENALTY(evolve_params と一致)。
    if out is None or len(out) == 0 or _chain_out_type(chain, task.input_type) != task.goal_type:
        fit = _PENALTY
    else:
        fit = -float(task.metric(out, task.target))
    if cache is not None:
        cache[chain] = fit
    return fit


# ---- 遺伝的操作(型を保存)---------------------------------------------------------------
def _self_loop_ops(t):
    """型 t を保存する op(in==out==t)= chain の任意位置に挿入/置換できる。"""
    return [n for n, m in VOCAB.items() if m["in"] == t and m["out"] == t]


def mutate(chain, rng, task):
    """型保存の変異(置換/挿入/削除)。goal 型を保つ。→ tuple。"""
    chain = list(chain)
    kind = rng.integers(3)
    loops = _self_loop_ops(task.goal_type)       # points→points op(このタスクでは全 preprocess+augment)
    if kind == 0 and chain:                       # 置換
        i = int(rng.integers(len(chain)))
        cands = [o for o in _self_loop_ops(VOCAB[chain[i]]["in"]) if VOCAB[o]["out"] == VOCAB[chain[i]]["out"]]
        if cands:
            chain[i] = cands[int(rng.integers(len(cands)))]
    elif kind == 1 and loops and len(chain) < 5:  # 挿入(self-loop op を任意位置)
        i = int(rng.integers(len(chain) + 1))
        chain.insert(i, loops[int(rng.integers(len(loops)))])
    elif kind == 2 and chain:                     # 削除
        del chain[int(rng.integers(len(chain)))]
    return tuple(chain)


def crossover(a, b, rng, max_len=5):
    """型が一致する切断点で 2 chain をスプライス(このタスクは全点 points なので任意点)。→ tuple。

    max_len で切り詰めて genome の肥大化(bloat、GP 定番の問題)を抑える。
    """
    if not a or not b:
        return (a or b)[:max_len]
    ca = int(rng.integers(len(a) + 1))
    cb = int(rng.integers(len(b) + 1))
    return tuple((list(a[:ca]) + list(b[cb:]))[:max_len])


# ---- 進化ループ + baseline --------------------------------------------------------------
def evolve(task, pop=24, gens=12, elite=3, seed=0, max_len=4):
    """GA で op-chain を進化。→ dict{best, fitness, n_evals, history}。"""
    rng = np.random.default_rng(seed)
    cache = {}
    population = [random_chain(rng, task, max_len) for _ in range(pop)]
    history = []
    for g in range(gens):
        scored = sorted(population, key=lambda c: evaluate(c, task, cache), reverse=True)
        history.append(evaluate(scored[0], task, cache))
        nxt = list(scored[:elite])                # エリート保存
        while len(nxt) < pop:
            # トーナメント選択(k=3)
            def pick():
                cand = [population[int(rng.integers(len(population)))] for _ in range(3)]
                return max(cand, key=lambda c: evaluate(c, task, cache))
            child = crossover(pick(), pick(), rng, max_len)
            if rng.random() < 0.6:
                child = mutate(child, rng, task)
            # 型不正(goal に終わらない)は破棄して親を採用
            if _chain_out_type(child, task.input_type) != task.goal_type:
                child = pick()
            nxt.append(child)
        population = nxt
    best = max(population, key=lambda c: evaluate(c, task, cache))
    return {"best": best, "fitness": evaluate(best, task, cache),
            "n_evals": len(cache), "history": history}


def random_search(task, n_evals, seed=0, max_len=4):
    """同じ評価予算(ユニーク数)でランダムな型整合 chain を探す baseline。→ dict{best, fitness, n_evals}。"""
    rng = np.random.default_rng(seed)
    cache = {}
    best, best_fit = tuple(), _PENALTY
    guard = 0
    while len(cache) < n_evals and guard < n_evals * 50:
        guard += 1
        c = random_chain(rng, task, max_len)
        f = evaluate(c, task, cache)
        if f > best_fit:
            best, best_fit = c, f
    return {"best": best, "fitness": best_fit, "n_evals": len(cache)}


def hand_designed_chain():
    """既知の良パイプライン(外れ値除去→平滑化)= 進化が到達すべき目標水準。"""
    return ("statistical_outlier_removal", "mls_smooth")


def describe(chain):
    """op-chain を読みやすい文字列に。"""
    return " → ".join(chain) if chain else "(identity)"
