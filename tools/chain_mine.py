# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
# -*- coding: utf-8 -*-
"""chain_mine — 連鎖ファザーの裏返し: **成功した合成**を採掘する(拡散フェーズ)。

``tools/chain_fuzz.py`` は「op を鎖にしたときだけ壊れるもの」を探して**失敗
だけ**を記録する。こちらは同じ型付きプールの仕掛けを使い、**例外も NaN も型の
嘘も出さずに完走した連鎖**を、その振る舞いの特徴量つきで記録する。

狙いは「op の種類の増加と洗練」の *拡散* 側 — 800 個の op から人手では思いつか
ない合成を機械的に列挙し、後段の別ツール(良し悪しの判定担当)へ候補として渡す。

## ファザーとの決定的な違い: 入力を 1 本の糸で通す

ファザーの連鎖は「プールを育てるランダムウォーク」で、入出力の関係が無い。
採掘器では **各 step が直前の産物を必ず食う**(current value threading)。
そうして初めて連鎖全体が 1 つの写像 ``x -> y`` になり、「入力から見て何が
起きたか」を記述子で語れる。ほかの引数(2 入力 op の相方など)は
ファザーと同じくプールから引く。

## 振る舞い記述子(behavior descriptor / MAP-Elites の BD)

**入力そのものとの差**が本質。単一スコアに潰さず多次元のまま出す
(「大きく変える」ことと「有用」は別物 — 変化量だけを最大化すると
ノイズを足す op が勝ってしまう。良し悪しの判定は後段の責務)。

  delta            入力からの正規化距離 ``|y-x| / (|x|+|y|)`` ∈ [0,1]。
                   同型・同形状のときのみ(型が変われば None)。0 = 恒等
  corr             入力と出力の相関(同形状のみ)。1 に近い = 単調な焼き直し
  entropy          出力ヒストグラムの Shannon エントロピー / log(bins) ∈ [0,1]
  nonzero          |v| > 1e-12 の割合
  mean/std/vmin/vmax  出力の素の統計(std ≈ 0 = 定数に潰れた)
  log_size_ratio   log2(出力要素数 / 入力要素数)。負 = 縮約系(特徴抽出)
  n_ops / sec      連鎖長と実測秒
  deterministic    同じ seed で 2 回走らせて出力が一致するか

## 収縮(絞り込み)

(a) 恒等に近い (b) 定数に潰れる (c) 非決定的 (d) 遅すぎる、および数値内容が無い
/ 統計が溢れて測れないものを落とし、残りを記述子でビン分けして各ビンの代表
1 件だけ残す。**上位 N 件を取ると同じ発見ばかりが残る**(多様性の崩壊)ので、
順位ではなく格子で間引く。代表の選び方は品質判定ではなく**簡潔さ**
(op 数 → seed)で決める。

落とした件数は理由別に必ず出す(無言の切り捨て禁止)。

## 極値に対する構え(実測で踏んだもの)

有限な入力でも**集約は溢れる**。|v| ~ 1e308 の出力では norm も mean も inf に
なり inf/inf = NaN が記述子へ漏れる。また ``hi > lo`` でも幅が bin 数に対して
小さすぎると ``np.histogram`` は落ちる(実測: ``(1.0, 1.0+5e-16)`` /
``(0.0, 1e-323)`` / 幅が inf の ``(-1e308, 1e308)``)。対策は 2 つとも
**条件を明示して弾く**(try/except の対症療法にしない):
``_bins_are_formable`` がビンの成立条件を、``_num`` が「有限な float だけ通す」
規律を担う。NaN を素通しすると ``_bucket`` の比較が常に False になり
**壊れた測定が黙って「最大変化」ビンに着地する**ため、記録・ビン・書き出し
(``allow_nan=False``)の三段で止める。

## 再現性(どこまで一致するか、正直に)

同じ ``--seed`` の 2 回走で jsonl は **実測秒 ``desc.sec`` を除いてビット一致**
する。壁時計だけは測定値なので原理的に一致しない — ``--no-timing`` を付けると
その 1 フィールドを落として完全にビット一致する。選抜(格子の代表)も
``(op 数, seed)`` だけで決め、秒に依存させていない。**依存させていた時は
95 代表のうち 4 件が走るたびに入れ替わった**(実測)。

使い方:
    py -3.11 tools/chain_mine.py --chains 2000 --length 6 --seed 0 \
        --out out/chain_mine.jsonl
    # 採掘した候補を手で再走(記述子の一次検証)
    py -3.11 tools/chain_mine.py --replay 3 --start voxel \
        --script vol_gaussian,vol_sobel --arg-keys 1,1
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools import chain_fuzz as cf                                    # noqa: E402

#: メモリ暴走の防波堤。ファザーと同じ値を**参照で**共有する(片方だけ緩めると
#: 実測で 34GB / 12GB のストールが起きた前科がある)。
MAX_POOL_BYTES = cf.MAX_POOL_BYTES
BIG_INPUT_BYTES = 32 * 2 ** 20

#: 既定の絞り込み閾値
IDENTITY_EPS = 0.02        # delta がこれ未満 = 恒等に近い(価値なし)
#: 相対標準偏差がこれ未満 = 定数に潰れた。float64 の丸め誤差スケール(~1e-16)より
#: 十分上、意味のある濃淡(1e-4 以上)より十分下。実測で std=6.8e-8 の
#: 「見た目まっ平らな像」が 1e-9 では素通りしたので 1e-6 に置いた。
CONST_EPS = 1e-6
SLOW_S = 5.0               # 連鎖全体がこれを超える = 遅すぎる
MIN_OPS = 2                # 1 op は「合成」ではない
HIST_BINS = 32

DROP_REASONS = ("identity_like", "const_output", "nondeterministic",
                "too_slow", "no_numeric_output", "unmeasurable_stats",
                "binned_duplicate")
#: 連鎖の途中で step を読み飛ばした理由(= ファザーの領分。ここでは数えるだけ)。
#: ``chain_too_short`` だけは step ではなく連鎖単位の結末(2 op に届かなかった)。
SKIP_REASONS = ("exception", "nonfinite", "typemiss", "growth",
                "unbindable_args", "adapter_none", "chain_too_short")


# --------------------------------------------------------------------------- #
# 数値要約のためのユーティリティ                                                #
# --------------------------------------------------------------------------- #
def _numeric_leaves(val, out):
    """入れ物を再帰的に辿って数値 ndarray / スカラを *out* に積む。"""
    if isinstance(val, np.ndarray):
        if val.dtype.kind in "fciub":
            out.append(val.reshape(-1))
        return
    if isinstance(val, (bool, int, float, np.floating, np.integer)):
        out.append(np.asarray([val], dtype=np.float64))
        return
    if isinstance(val, complex):
        out.append(np.asarray([val], dtype=np.complex128))
        return
    if isinstance(val, (list, tuple)):
        for v in val:
            _numeric_leaves(v, out)
        return
    if isinstance(val, dict):
        for k in sorted(val, key=str):       # 決定性: dict は鍵順で辿る
            _numeric_leaves(val[k], out)


def _flat(val):
    """産物の全数値内容を 1 本の実 1-D 配列に(complex は絶対値)。無ければ None。"""
    leaves = []
    _numeric_leaves(val, leaves)
    leaves = [a for a in leaves if a.size]
    if not leaves:
        return None
    parts = [np.abs(a).astype(np.float64) if a.dtype.kind == "c"
             else a.astype(np.float64) for a in leaves]
    return np.concatenate(parts)


def _num(v):
    """有限な float だけを通す(非有限は「測れなかった」= None)。

    集約は入力が有限でも溢れる: |v| ~ 1e308 の配列は ``norm`` も ``mean`` も
    inf になり、inf/inf = NaN が記述子へ漏れる。NaN を素通しすると二重に害が
    ある — ① ``json.dumps`` が strict JSON にならない ② ``_bucket`` の比較は
    NaN で必ず False なので**壊れた測定が黙って「最大変化」ビンに入る**
    (実測で delta=NaN が delta ビン 4 に着地した)。None にすれば "na" ビンへ
    行き、絞り込みの ``is not None`` 判定も正しく素通しになる。
    """
    if v is None:
        return None
    f = float(v)
    return f if math.isfinite(f) else None


def _r(v, n):
    """有限なら丸め、非有限/None なら None(記録に NaN を残さない)。"""
    v = _num(v)
    return None if v is None else round(v, n)


def _bins_are_formable(lo, hi, bins=HIST_BINS):
    """[lo, hi] を *bins* 本の有限幅ビンに刻めるか(np.histogram の成立条件)。

    ``hi > lo`` だけでは足りない。幅が bin 数に対して小さすぎると端点が同値に
    潰れ、np.histogram は "Too many bins for data range" で落ちる。実測の破綻例:
    ``(1.0, 1.0+5e-16)`` = 2 ULP しかない / ``(0.0, 1e-323)`` = 非正規化数 /
    ``(-1e308, 1e308)`` = 幅が inf。**対症療法の try/except ではなく条件を書く**:
    幅が有限かつ正で、境界 33 本が狭義単調ならビンは刻める。これは numpy 自身の
    判定と厳密に一致する(1e-323〜1e308 の 39,358 組でランダム照合、不一致 0)。
    """
    width = hi - lo
    if not (math.isfinite(width) and width > 0.0):
        return False
    edges = np.linspace(lo, hi, bins + 1)
    return bool(np.all(np.isfinite(edges)) and np.all(edges[:-1] < edges[1:]))


def _entropy01(flat):
    """ヒストグラムの Shannon エントロピー / log(bins) ∈ [0,1]。

    ビンを刻めない幅(極小幅・非正規化数・幅が inf)は**事実上の定数**なので
    0.0 を返す — fail-safe だが無言ではなく、条件は上の述語に明示してある。
    """
    f = flat[np.isfinite(flat)]
    if f.size < 2:
        return 0.0
    lo, hi = float(f.min()), float(f.max())
    if not _bins_are_formable(lo, hi):
        return 0.0
    counts, _ = np.histogram(f, bins=HIST_BINS, range=(lo, hi))
    p = counts.astype(np.float64)
    s = p.sum()
    if s <= 0:
        return 0.0
    p = p[p > 0] / s
    return float(-(p * np.log(p)).sum() / math.log(HIST_BINS))


def _comparable(a, b):
    """delta / corr を測ってよい組か(同じ形・同じ数値種)。"""
    if isinstance(a, np.ndarray) and isinstance(b, np.ndarray):
        return (a.shape == b.shape and a.dtype.kind in "fciub"
                and b.dtype.kind in "fciub")
    scal = (bool, int, float, np.floating, np.integer, complex)
    return isinstance(a, scal) and isinstance(b, scal)


def _delta_corr(x, y):
    """入力 *x* と出力 *y* の (正規化距離, 相関)。測れなければ (None, None)。"""
    if not _comparable(x, y):
        return None, None
    xa = np.asarray(x, dtype=np.complex128 if np.iscomplexobj(x) else np.float64)
    ya = np.asarray(y, dtype=np.complex128 if np.iscomplexobj(y) else np.float64)
    xa, ya = xa.reshape(-1), ya.reshape(-1)
    if xa.size != ya.size or xa.size == 0:
        return None, None
    if not (np.isfinite(xa).all() and np.isfinite(ya).all()):
        return None, None
    # ノルムは要素が有限でも溢れる(|v| ~ 1e308 の配列 → inf)。溢れたら
    # inf/inf = NaN が出るので、**測れなかった**と正直に None を返す
    nx, ny, nd = (float(np.linalg.norm(xa)), float(np.linalg.norm(ya)),
                  float(np.linalg.norm(ya - xa)))
    if not (math.isfinite(nx) and math.isfinite(ny) and math.isfinite(nd)):
        return None, None
    den = nx + ny
    delta = 0.0 if den <= 0 else nd / den
    corr = None
    if xa.size >= 2:
        xr, yr = np.abs(xa) if np.iscomplexobj(xa) else xa.real, \
                 np.abs(ya) if np.iscomplexobj(ya) else ya.real
        sx, sy = float(xr.std()), float(yr.std())
        if math.isfinite(sx) and math.isfinite(sy) and sx > 0 and sy > 0:
            corr = _num(np.clip(np.corrcoef(xr, yr)[0, 1], -1.0, 1.0))
    delta = _num(delta)
    return (None if delta is None else round(delta, 6),
            None if corr is None else round(corr, 6))


def describe(x_in, y_out, in_type, out_type, ops_seq, sec):
    """1 連鎖の振る舞い記述子。**単一スコアに潰さない**(多次元のまま返す)。"""
    fo = _flat(y_out)
    fi = _flat(x_in)
    delta, corr = _delta_corr(x_in, y_out)
    d = {"in_type": in_type, "out_type": out_type, "n_ops": len(ops_seq),
         "sec": round(sec, 4), "delta": delta, "corr": corr,
         "same_type": in_type == out_type}
    if fo is None:
        d.update({"size": 0, "mean": None, "std": None, "vmin": None,
                  "vmax": None, "entropy": None, "nonzero": None,
                  "rel_std": None, "log_size_ratio": None, "finite_frac": None})
        return d
    finite = np.isfinite(fo)
    ff = fo[finite]
    d["size"] = int(fo.size)
    d["finite_frac"] = round(float(finite.mean()), 6)
    if ff.size:
        # mean/std は要素が有限でも溢れる(1e308 の配列)。溢れた統計は None =
        # 「測れなかった」にして、NaN が下流のビンや絞り込みへ漏れるのを断つ
        mean, std = _num(ff.mean()), _num(ff.std())
        rel = (None if (mean is None or std is None)
               else _num(std / (abs(mean) + 1.0)))
        d.update({"mean": _r(mean, 6), "std": _r(std, 6),
                  "vmin": _r(ff.min(), 6), "vmax": _r(ff.max(), 6),
                  "rel_std": _r(rel, 9),
                  "entropy": _r(_entropy01(ff), 6),
                  "nonzero": _r(float((np.abs(ff) > 1e-12).mean()), 6)})
    else:
        d.update({"mean": None, "std": None, "vmin": None, "vmax": None,
                  "rel_std": None, "entropy": None, "nonzero": None})
    d["log_size_ratio"] = (None if fi is None or fi.size == 0 else
                           _r(math.log2(fo.size / fi.size), 4))
    return d


# --------------------------------------------------------------------------- #
# ビン分け(MAP-Elites の格子)                                                  #
# --------------------------------------------------------------------------- #
def _bucket(v, edges):
    """*v* を *edges* で離散化。測れなかった値は "na"(潰さない)。

    非有限も "na" に落とす。NaN は ``v < e`` が常に False なので、素通しすると
    **黙って最上位ビンに着地する**(実測: delta=NaN が delta ビン 4 に入った)
    = 壊れた測定が「最大変化の発見」に化ける。記述子側で既に None 化している
    が、ここでも二重に止める。
    """
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return "na"
    for i, e in enumerate(edges):
        if v < e:
            return i
    return len(edges)


def bin_key(d):
    """記述子 → 格子セル。順位ではなく格子で間引くことで多様性を保つ。"""
    return (str(d["out_type"]),
            _bucket(d["delta"], [0.05, 0.2, 0.5, 0.8]),
            _bucket(d["entropy"], [0.3, 0.6, 0.85]),
            _bucket(d["log_size_ratio"], [-2.0, -0.5, 0.5, 2.0]),
            _bucket(d["nonzero"], [0.1, 0.6, 0.95]),
            _bucket(d["corr"], [-0.5, 0.5, 0.9]))


# --------------------------------------------------------------------------- #
# 採掘ランナー(成功した連鎖と出力を返す — ファザーの run_chain は失敗記録用)   #
# --------------------------------------------------------------------------- #
def _init_pool(gens, rng):
    return {t: [g(rng)] for t, g in gens.items()}


def _eligible(ops, cur_type, pool):
    """*cur_type* を食えて、残りの引数もプールで賄える op。"""
    out = []
    for o in ops:
        name, _dim, ins, _out, _fn = o
        if name in cf.OP_ARG_BUILDERS:
            continue          # 専用ビルダーは current value を通せない = 対象外
        if not (cur_type in ins or "any" in ins):
            continue
        if all((t in pool and pool[t]) or t == "any" for t in ins):
            out.append(o)
    return out


def _thread_args(ins, cur_type, cur_val, pool, arng):
    """current value を 1 スロットに差し込み、残りはプールから引く。"""
    slot = ins.index(cur_type) if cur_type in ins else ins.index("any")
    args = []
    for i, t in enumerate(ins):
        if i == slot:
            args.append(cur_val)
            continue
        src = pool[t] if t != "any" else pool[arng.choice(sorted(pool))]
        args.append(src[arng.integers(len(src))])
    return args


def _run_step(op, cur_type, cur_val, pool, arng, tally, verbose):
    """1 op を実行して (ok, result)。失敗理由は *tally* に理由別で積む。"""
    name, _dim, ins, out, fn = op
    args = _thread_args(list(ins), cur_type, cur_val, pool, arng)
    bound = cf._bind_args(name, fn, args, arng)
    if bound is None:
        tally["unbindable_args"] = tally.get("unbindable_args", 0) + 1
        return False, None
    a, kw = bound
    big = sum(cf._nbytes(v) for v in a)
    if big > BIG_INPUT_BYTES and verbose:
        # 重い入力は実行前に予告(万一のストールでもログだけで犯人が判る)
        print(f"  big-input: {name} ({big / 2 ** 20:.0f} MB)", flush=True)
    try:
        result = fn(*a, **kw)
    except Exception:                     # noqa: BLE001 — 失敗はファザーの領分
        tally["exception"] = tally.get("exception", 0) + 1
        return False, None
    if name in cf.ADAPTERS:
        result = cf.ADAPTERS[name](result)
    if result is None:
        tally["adapter_none"] = tally.get("adapter_none", 0) + 1
        return False, None
    if not cf._finite_ok(result):
        tally["nonfinite"] = tally.get("nonfinite", 0) + 1
        return False, None
    if cf._nbytes(result) > MAX_POOL_BYTES:
        tally["growth"] = tally.get("growth", 0) + 1
        return False, None                # 巨大産物はプールに入れない(指数増殖防止)
    check = cf.TYPE_CHECKS.get(out)
    if check is not None and not check(result):
        tally["typemiss"] = tally.get("typemiss", 0) + 1
        return False, None
    return True, result


def mine_chain(ops, gens, chain_seed, length, tally=None, verbose=False):
    """1 連鎖を採掘 → 成功なら候補 dict、駄目なら None。

    各 step は直前の産物を必ず食う(current value threading)。失敗した op は
    プールを汚さずに読み飛ばし、別の op を引き直す(予算 = length * 3 回)。
    引数抽選は ``(chain_seed, op 名, その op の抽選回数)`` の位置独立な乱数源
    (ファザーと同じ)。抽選回数を記録しておくので --replay で厳密に再走できる。
    """
    tally = {} if tally is None else tally
    rng = np.random.default_rng(chain_seed)
    pool = _init_pool(gens, rng)
    starts = sorted(t for t in pool if _eligible(ops, t, pool))
    if not starts:
        return None
    start_type = starts[int(rng.integers(len(starts)))]
    x_in = pool[start_type][0]
    cur_type, cur_val = start_type, x_in
    seq, keys, occ = [], [], {}
    t0 = time.perf_counter()
    for _ in range(length * 3):
        if len(seq) >= length:
            break
        cands = _eligible(ops, cur_type, pool)
        if not cands:
            break
        op = cands[int(rng.integers(len(cands)))]
        name = op[0]
        occ[name] = occ.get(name, 0) + 1
        k = occ[name]
        arng = cf._step_rng(chain_seed, name, k, rng)
        ok, result = _run_step(op, cur_type, cur_val, pool, arng, tally, verbose)
        if not ok:
            continue
        seq.append(name)
        keys.append(k)
        cur_type, cur_val = op[3], result
        pool.setdefault(cur_type, []).append(result)
    sec = time.perf_counter() - t0
    if len(seq) < MIN_OPS:
        tally["chain_too_short"] = tally.get("chain_too_short", 0) + 1
        return None
    return {"seed": int(chain_seed), "start": start_type, "ops": seq,
            "arg_keys": keys, "sec": sec, "x_in": x_in, "y_out": cur_val,
            "out_type": cur_type}


def replay_chain(ops, gens, chain_seed, start_type, script, arg_keys,
                 verbose=False):
    """記録した (seed, 開始型, op 列, 抽選回数) を厳密に再走 → (出力, 型, 秒)。

    失敗 op はプールに何も足さないため、成功列だけを再走すれば各 step の
    プールは採掘時と同一。抽選回数を記録しているので引数も同一になる。
    """
    by_name = {o[0]: o for o in ops}
    rng = np.random.default_rng(chain_seed)
    pool = _init_pool(gens, rng)
    if start_type not in pool or not pool[start_type]:
        return None, None, 0.0
    cur_type, cur_val = start_type, pool[start_type][0]
    tally = {}
    t0 = time.perf_counter()
    for name, k in zip(script, arg_keys):
        op = by_name.get(name)
        if op is None:
            return None, None, time.perf_counter() - t0
        arng = cf._step_rng(chain_seed, name, k, rng)
        ok, result = _run_step(op, cur_type, cur_val, pool, arng, tally, verbose)
        if not ok:
            return None, None, time.perf_counter() - t0
        cur_type, cur_val = op[3], result
        pool.setdefault(cur_type, []).append(result)
    return cur_val, cur_type, time.perf_counter() - t0


def _same_output(a, b):
    """2 回走らせた出力が同一か(NaN 同士も同一とみなす)。"""
    if type(a) is not type(b):
        return False
    if isinstance(a, np.ndarray):
        if a.shape != b.shape or a.dtype != b.dtype:
            return False
        if a.dtype.kind in "fc":
            return bool(np.array_equal(a, b, equal_nan=True))
        return bool(np.array_equal(a, b))
    if isinstance(a, (list, tuple)):
        return len(a) == len(b) and all(_same_output(x, y) for x, y in zip(a, b))
    if isinstance(a, dict):
        return sorted(a, key=str) == sorted(b, key=str) and all(
            _same_output(a[k], b[k]) for k in a)
    if isinstance(a, (float, np.floating)):
        return bool(a == b or (np.isnan(a) and np.isnan(b)))
    try:
        return bool(a == b)
    except Exception:                     # noqa: BLE001 — 比較不能な型は不一致扱い
        return False


# --------------------------------------------------------------------------- #
# 収縮(絞り込み)                                                              #
# --------------------------------------------------------------------------- #
def contract(cands, ops, gens, identity_eps=IDENTITY_EPS, const_eps=CONST_EPS,
             slow_s=SLOW_S, check_determinism=True):
    """候補列 → (代表のみの候補列, 落とした理由の内訳)。

    (a) 恒等に近い (b) 定数に潰れる (c) 非決定的 (d) 遅すぎる を落としてから、
    残りを ``bin_key`` の格子に配り**各セル 1 件**にする。代表は品質ではなく
    簡潔さ(op 数 → 秒 → seed)で選ぶ — 良し悪しの判定は後段の別ツールの責務。
    """
    dropped = {r: 0 for r in DROP_REASONS}
    survivors = []
    for c in cands:
        d = c["desc"]
        if d["delta"] is not None and d["delta"] < identity_eps:
            dropped["identity_like"] += 1
            continue
        if d["size"] == 0:
            dropped["no_numeric_output"] += 1
            continue
        if d["rel_std"] is None:
            # 数値はあるのに統計が測れない = 集約が溢れた(|v| ~ 1e308)。
            # 後段の判定器に null 統計を渡しても使えないので落とす — ただし
            # 無言ではなく理由つきで数える
            dropped["unmeasurable_stats"] += 1
            continue
        if d["rel_std"] < const_eps:
            dropped["const_output"] += 1
            continue
        if d["sec"] > slow_s:
            dropped["too_slow"] += 1
            continue
        survivors.append(c)
    kept = []
    for c in survivors:
        if check_determinism and not c.get("deterministic", False):
            dropped["nondeterministic"] += 1
            continue
        kept.append(c)
    bins = {}
    for c in kept:
        key = bin_key(c["desc"])
        cur = bins.get(key)
        # 代表は品質ではなく**簡潔さ**で選ぶ。順位に秒を入れてはいけない
        # (実測: 秒でタイを割ると 95 代表中 4 件が走るたびに入れ替わり、
        #  同じ seed でも出力 jsonl が一致しなくなった)
        rank = (c["desc"]["n_ops"], c["seed"])
        if cur is None or rank < cur[0]:
            bins[key] = (rank, c, (0 if cur is None else cur[2]) + 1)
        else:
            bins[key] = (cur[0], cur[1], cur[2] + 1)
    reps = []
    for key in sorted(bins, key=lambda k: tuple(str(x) for x in k)):
        _rank, c, n = bins[key]
        rec = dict(c)
        rec["bin"] = list(key)
        rec["bin_members"] = n
        reps.append(rec)
        dropped["binned_duplicate"] += n - 1
    return reps, dropped


# --------------------------------------------------------------------------- #
# 走査本体                                                                      #
# --------------------------------------------------------------------------- #
def mine(ops, gens, chains, length, seed, check_determinism=True,
         progress=0, verbose=False):
    """*chains* 本を採掘し (候補列, step 失敗の内訳, 秒) を返す。"""
    tally = {}
    cands = []
    t0 = time.perf_counter()
    for i in range(chains):
        # 連鎖固有 seed(ファザーと同じ規則)= 後から i 番目だけを再走できる
        chain_seed = seed * 1_000_003 + i
        got = mine_chain(ops, gens, chain_seed, length, tally, verbose)
        if progress and (i + 1) % progress == 0:
            print(f"  {i + 1}/{chains} chains, candidates {len(cands)}",
                  flush=True)
        if got is None:
            continue
        d = describe(got["x_in"], got["y_out"], got["start"], got["out_type"],
                     got["ops"], got["sec"])
        rec = {"seed": got["seed"], "start": got["start"], "ops": got["ops"],
               "arg_keys": got["arg_keys"], "out_type": got["out_type"],
               "desc": d, "deterministic": None}
        if check_determinism:
            # 高い検査なので、恒等・定数で落ちる候補には掛けない(収縮と同じ判定)
            cheap_out = ((d["delta"] is not None and d["delta"] < IDENTITY_EPS)
                         or d["size"] == 0
                         or (d["rel_std"] is not None and d["rel_std"] < CONST_EPS)
                         or d["sec"] > SLOW_S)
            if cheap_out:
                rec["deterministic"] = None
            else:
                y2, t2, _ = replay_chain(ops, gens, got["seed"], got["start"],
                                         got["ops"], got["arg_keys"], verbose)
                rec["deterministic"] = bool(t2 == got["out_type"]
                                            and _same_output(got["y_out"], y2))
        cands.append(rec)
    return cands, tally, time.perf_counter() - t0


#: 記録のうち **測定値ゆえに再走で一致しない**唯一のフィールド(壁時計)。
#: これ以外は同じ seed なら必ずビット一致する — 選抜も格子も秒に依存させない。
TIMING_FIELDS = ("sec",)


def stable_record(rec):
    """壁時計を除いた記録。同じ seed の 2 回走で**必ず一致する**部分。"""
    r = dict(rec)
    r["desc"] = {k: v for k, v in rec["desc"].items() if k not in TIMING_FIELDS}
    return r


def _write(path, reps, timing=True):
    """代表を jsonl へ。*timing* を落とすと同じ seed でビット一致する。"""
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for r in reps:
            rec = r if timing else stable_record(r)
            # allow_nan=False = fail-closed。NaN/Inf が記述子に漏れたら黙って
            # 不正な JSON("NaN" は strict parser が拒む)を書かず、ここで落ちる
            fh.write(json.dumps(rec, ensure_ascii=False, default=str,
                                sort_keys=True, allow_nan=False) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--chains", type=int, default=200)
    ap.add_argument("--length", type=int, default=6)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "chain_mine.jsonl"))
    ap.add_argument("--identity-eps", type=float, default=IDENTITY_EPS)
    ap.add_argument("--slow-sec", type=float, default=SLOW_S)
    ap.add_argument("--no-determinism", action="store_true",
                    help="決定性チェックを省く(速いが (c) の絞り込みが効かない)")
    ap.add_argument("--no-timing", action="store_true",
                    help="記録から実測秒を落とす(唯一の非再現フィールド)= "
                         "同じ seed の 2 回走で jsonl がビット一致する")
    ap.add_argument("--replay", type=int, metavar="SEED",
                    help="採掘済み候補を厳密に再走(--start/--script/--arg-keys)")
    ap.add_argument("--start", help="--replay の開始型")
    ap.add_argument("--script", help="--replay の op 名カンマ区切り")
    ap.add_argument("--arg-keys", help="--replay の抽選回数カンマ区切り")
    args = ap.parse_args(argv)

    ops, gens = cf.catalog(), cf.make_generators()

    if args.replay is not None:
        if not (args.start and args.script):
            print("--replay には --start と --script が要る", file=sys.stderr)
            return 2
        script = [s for s in args.script.split(",") if s]
        keys = ([int(k) for k in args.arg_keys.split(",")] if args.arg_keys
                else [1] * len(script))
        y, t, sec = replay_chain(ops, gens, args.replay, args.start, script,
                                 keys, verbose=True)
        print(f"== replay seed={args.replay} start={args.start} script={script}")
        if y is None:
            print("  再走に失敗(この seed/script では完走しない)")
            return 1
        pool = _init_pool(gens, np.random.default_rng(args.replay))
        d = describe(pool[args.start][0], y, args.start, t, script, sec)
        print(f"  out_type={t}  {type(y).__name__}"
              f"{getattr(y, 'shape', '')}")
        for k in ("delta", "corr", "entropy", "nonzero", "mean", "std",
                  "log_size_ratio", "size", "sec"):
            print(f"  {k:15s} {d[k]}")
        return 0

    cands, tally, wall = mine(ops, gens, args.chains, args.length, args.seed,
                              check_determinism=not args.no_determinism,
                              progress=max(1, args.chains // 10), verbose=True)
    reps, dropped = contract(cands, ops, gens, identity_eps=args.identity_eps,
                             slow_s=args.slow_sec,
                             check_determinism=not args.no_determinism)
    _write(args.out, reps, timing=not args.no_timing)

    print(f"\n== 拡散 {args.chains} 連鎖 x len {args.length}"
          f"(seed {args.seed}, {wall:.0f}s)")
    print(f"== 完走した連鎖(候補): {len(cands)}")
    print(f"== 収縮後の代表: {len(reps)}  / ビン数 {len(reps)}")
    print("== 落とした候補(理由別):")
    for r in DROP_REASONS:
        print(f"     {r:20s} {dropped.get(r, 0)}")
    print(f"     {'(合計)':20s} {sum(dropped.values())}")
    print("== 連鎖中に読み飛ばした step(理由別、= ファザーの領分):")
    for r in sorted(tally):
        print(f"     {r:20s} {tally[r]}")
    used = sorted({o for c in cands for o in c["ops"]})
    print(f"== 候補に現れた op: {len(used)}/{len(ops)}")
    print(f"== 代表一覧 -> {args.out}")
    for r in reps[:10]:
        d = r["desc"]
        print(f"  {r['start']}->{r['out_type']} delta={d['delta']} "
              f"ent={d['entropy']} x{r['bin_members']}  {'|'.join(r['ops'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
