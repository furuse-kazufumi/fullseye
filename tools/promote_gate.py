# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""promote_gate — 合成 op を語彙へ「昇格」させてよいかを判定するゲート。

進化が見つけた champion をそのまま 1 個の op に凍結する仕組み
(``champion_to_macro.py`` + ``backends_macro.py``)は既にある。既存ゲートは
「その problem の locked holdout で hand baseline を上回るか」を強制していて、
これは正しいが **1 つの problem しか見ていない**。本モジュールはそこに、
先行研究が要求する 3 つの判定を足す:

**1. counterfactual utility(反実仮想効用)**
   問うべきは「この op はその課題で強いか」ではなく
   「**この op が語彙にあると、ワークロード全体がどれだけ改善するか**」。
   数値カーネルの library learning(GrowLibm, arXiv 2603.24812, 2026)が
   「中間探索結果を候補鉱脈とみなし、反実仮想効用で順位付けし、冗長を剪定する」
   という形で確立した基準を、画像/幾何 op ライブラリに移したもの。
   実装は「候補を 1 段として使ったときの各 problem のスコア」対
   「**既存語彙の最良 1 段**のスコア」の改善量を全 problem で集計する
   (= その op が無くても既存語彙で届く分を差し引く)。

**2. 振る舞いによる重複排除**
   同じことをする合成 op が乱立すると語彙が汚れる。式の等価性を潰す装置
   (e-graph / equality saturation)の数値版として、**固定プローブ集合上の出力が
   既存 op と一致するなら重複として却下**する。

**3. 容量上限(capacity bound)**
   昇格を無制限に続けると、到達可能なモデル族が capacity-bounded でなくなり
   一般化の保証が壊れる(arXiv 2510.04399)。上限に達したら、**効用が最下位の
   既存 DNA op を押し出す**か、候補を却下する。どちらの場合も**何を落としたかを
   必ず記録する**(無言の切り捨て禁止)。

正直な限界:
  * counterfactual utility は「1 段として使う」近似で測る。本来は「候補を語彙に
    入れて進化をやり直したときの改善」だが、それは 1 候補あたり数十分かかる。
    近似であることを ``utility_method`` に明記して出力する。
  * プローブ集合上での一致は「その入力では区別できない」という意味であって、
    数学的な等価性の証明ではない。プローブを増やせば分解能は上がる。
  * ゲートを通ることは「有用」の十分条件ではない。悪い op が 1 本入ると、
    それを引く将来の探索すべてを汚染する(bad-skill propagation)ので、
    判定は**厳しい側に倒してある**(改善が測定誤差内なら却下)。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

#: DNA(macro)語彙の上限。capacity bound の実体 — 増やすなら「なぜその数か」を
#: ここに書くこと。既定 32 は「語彙の 4% 未満に抑える」という保守的な線
#: (実測 2026-09-01: 語彙 800 op)。
DNA_CAPACITY = 32

#: 改善が測定誤差内なら却下する幅。problem のスコア単位は dB / F1 / IoU など
#: まちまちなので、**相対**で見る(既存最良比 +0.5% 未満は「差が無い」)。
MIN_RELATIVE_GAIN = 0.005

#: 相対改善(比)を定義してよい既存最良スコアの下限。
#:
#: ここが本 module で唯一の「0 割り」だった。``denom = abs(best_existing) + 1e-12``
#: は例外を出さない代わりに **もっともらしく間違った数**を返す ―― 実測
#: 2026-09-02: ``vibration_map`` の既存 video op は 1 個(``tb_temporal_bandpass``)
#: だけで locked スコアがちょうど 0.0000、候補 0.72448 に対し
#: ``rel = +724476067514.2847`` が出て判定は **PROMOTE**。無言の誤昇格であり、
#: `best_relative_gain` の集計も 1 件で汚染される。
#:
#: 直し方は「比が定義できないことを印にする」+「その problem 固有の尺度で
#: **絶対改善**として判定する」の 2 段。比を無理に作らないので、既存の
#: 非退化ケースの相対値は **1 つも動かない**(公開済みの +37.9% 等はそのまま)。
RATIO_FLOOR = 1e-6

#: 重複判定の許容差(プローブ出力の相対 L2 距離)。これ未満なら同じ振る舞い。
DUP_TOLERANCE = 1e-6


def _probe_inputs(sort, n=3, size=64):
    """重複判定用の固定プローブ。決定的(seed 固定)。"""
    outs = []
    for i in range(n):
        rng = np.random.default_rng(1000 + i)
        if sort == "volume":
            g = np.mgrid[0:24, 0:24, 0:24].astype(np.float64)
            c = 12.0
            v = (((g[0] - c) ** 2 + (g[1] - c) ** 2 + (g[2] - c) ** 2) <= 8.0 ** 2)
            outs.append(np.clip(v + 0.1 * rng.standard_normal(v.shape), 0, 1))
        elif sort == "points":
            outs.append(rng.random((120, 3)) * 10.0)
        elif sort == "signal":
            outs.append(np.sin(np.linspace(0, 8 * np.pi, 192))
                        + 0.1 * rng.standard_normal(192))
        elif sort == "matrix":
            outs.append(rng.standard_normal((6, 4)))
        elif sort == "cimage":
            outs.append(np.fft.fftshift(np.fft.fft2(rng.random((32, 32)))))
        else:                                             # image / region / …
            x = np.linspace(0, 1, size)
            base = np.outer(np.sin(4 * np.pi * x), np.cos(3 * np.pi * x)) * 0.5 + 0.5
            outs.append(np.clip(base + 0.08 * rng.standard_normal((size, size)), 0, 1))
    return outs


def _flat(value):
    """比較用に数値ベクトル化(型が違えば None)。"""
    if isinstance(value, (int, float, np.floating, np.integer)):
        return np.asarray([float(value)])
    if isinstance(value, np.ndarray) and value.dtype.kind in "fciub":
        return np.asarray(value, np.complex128).ravel()
    return None


def _same_behaviour(a, b):
    """2 つの出力が(このプローブでは)区別できないか。"""
    fa, fb = _flat(a), _flat(b)
    if fa is None or fb is None or fa.shape != fb.shape or fa.size == 0:
        return False
    denom = float(np.linalg.norm(fa)) + float(np.linalg.norm(fb)) + 1e-12
    return float(np.linalg.norm(fa - fb)) / denom < DUP_TOLERANCE


def find_behavioural_duplicate(ops, fn, in_sort, a=0.5, b=0.5, limit=None):
    """*fn* と同じ振る舞いをする既存 op 名(無ければ None)。

    プローブ全件で一致したときだけ重複と判定する(1 件の偶然一致で却下しない)。
    """
    probes = _probe_inputs(in_sort)
    try:
        mine = [fn(p.copy(), a, b) for p in probes]
    except Exception:                                     # noqa: BLE001
        return None
    cands = [o for o in ops.REGISTRY if o.in_sort == in_sort]
    if limit is not None:
        cands = cands[:limit]
    for op in cands:
        if op.fn is fn:
            continue
        try:
            theirs = [op.fn(p.copy(), a, b) for p in probes]
        except Exception:                                 # noqa: BLE001
            continue
        if all(_same_behaviour(x, y) for x, y in zip(mine, theirs)):
            return op.name
    return None


class temp_op:                                            # noqa: N801 - context manager
    """候補を**登録せずに**採点するための一時 op。

    昇格ゲートは「まだ語彙に無いもの」を判定する道具なので、判定のために本登録
    するのは順序が逆(却下しても痕跡が残る)。``ops`` の名前解決表へ一時的に
    差し込み、抜けるときに必ず元へ戻す。既存名を上書きしそうな場合は拒否する
    (静かに既存 op を壊さない)。
    """

    def __init__(self, ops_mod, name, fn, in_sort, out_sort):
        self.ops, self.name, self.fn = ops_mod, name, fn
        self.in_sort, self.out_sort = in_sort, out_sort

    def __enter__(self):
        if self.name in self.ops._BY_NAME:
            raise ValueError(f"temp_op: {self.name!r} は既存 op と衝突する")
        Op = type(self.ops.REGISTRY[0])
        op = Op(self.name, "candidate", "", self.in_sort, self.out_sort, self.fn)
        self.ops._BY_NAME[self.name] = op
        self.ops.RT[self.name] = self.fn
        self.ops.REGISTRY.append(op)
        return op

    def __exit__(self, *exc):
        self.ops._BY_NAME.pop(self.name, None)
        self.ops.RT.pop(self.name, None)
        self.ops.REGISTRY[:] = [o for o in self.ops.REGISTRY if o.name != self.name]
        return False


def stages_runner(ops, stages_spec):
    """名前ピン留めされた stage 列を ``fn(v, a, b)`` 規約の 1 個の op にする。

    ``backends_macro`` と同じ「champion を凍結して 1 op にする」変換だが、
    こちらは**登録しない**(ゲート判定用)。a, b は凍結 — 進化が選んだ値を
    ゲートで動かしたら、判定対象が別物になってしまう。
    """
    stages = ops.decode_by_names(stages_spec)

    def _run(v, a, b):                                    # noqa: ARG001 - 凍結
        try:
            return ops.run_stages(stages, v)
        except Exception:                                 # noqa: BLE001 - fail-soft
            return np.asarray(v)
    return _run


def _score_single_stage(prob, ops, op_name, a, b, cfg, split_seed_offset):
    """1 段パイプライン(その op 単体)の split スコア。失敗は -inf 扱い。"""
    data = prob.make(cfg["n_holdout"], cfg["size"], cfg["seed"] + split_seed_offset)
    try:
        stages = ops.decode_by_names([{"op": op_name, "a": a, "b": b}])
        return float(prob.score_stages(stages, data))
    except Exception:                                     # noqa: BLE001
        return float("-inf")


#: 「既存語彙の最良 1 段」のキャッシュ。候補ごとに再計算していたが、**この値は
#: 候補に依存しない**(problem と split と走査範囲だけで決まる)。60 候補を判定
#: すると 60 倍の重複計算になっていた — 実測で気づいた無駄。キーに語彙サイズを
#: 含めるのは、語彙が増えた後に古い最良を使い回さないため。
_BEST_EXISTING_CACHE: dict = {}


def _best_existing(ops, prob, pname, a, b, cfg, offset, exclude, max_existing):
    """その problem における既存語彙の最良 1 段。→ (スコア, op 名)。"""
    key = (pname, offset, a, b, cfg["n_holdout"], cfg["size"], cfg["seed"],
           max_existing, len(ops.REGISTRY))
    cached = _BEST_EXISTING_CACHE.get(key)
    if cached is not None and cached[1] != exclude:
        return cached
    best, best_name = float("-inf"), None
    pool = [o for o in ops.REGISTRY if o.in_sort == prob.in_sort and o.name != exclude]
    if max_existing is not None:
        pool = pool[:max_existing]
    for op in pool:
        s = _score_single_stage(prob, ops, op.name, a, b, cfg, offset)
        if s > best:
            best, best_name = s, op.name
    if exclude is None or best_name != exclude:
        _BEST_EXISTING_CACHE[key] = (best, best_name)
    return best, best_name


def counterfactual_utility(ops, problems, op_name, a=0.5, b=0.5, cfg=None,
                           split="locked", max_existing=None, verbose=False):
    """候補 op の反実仮想効用を全 problem で測る。

    各 problem について「候補を 1 段で使ったスコア」と「**既存語彙の最良 1 段**」を
    比べ、相対改善を集計する。既存語彙で届く分を差し引くのが要点 — 「強い」だけの
    op ではなく「**既存では届かないところに届く**」op を通す。

    評価は locked split(進化が一度も選択に使っていない分割)で行う。
    """
    cfg = cfg or {"n_train": 6, "n_holdout": 6, "size": 96, "seed": 0}
    offset = {"train": 0, "holdout": 10_000, "locked": 20_000}[split]
    rows = []
    for pname, prob in problems.PROBLEMS.items():
        cand = _score_single_stage(prob, ops, op_name, a, b, cfg, offset)
        if not np.isfinite(cand):
            continue                                      # その sort では動かない
        best_existing, best_name = _best_existing(
            ops, prob, pname, a, b, cfg, offset, op_name, max_existing)
        if not np.isfinite(best_existing):
            continue
        denom = abs(best_existing) + 1e-12
        rel = (cand - best_existing) / denom
        rows.append({"problem": pname, "unit": prob.unit,
                     "candidate": round(cand, 5),
                     "best_existing": round(best_existing, 5),
                     "best_existing_op": best_name,
                     "relative_gain": round(float(rel), 5)})
        if verbose:
            print(f"  {pname:12s} cand {cand:9.4f}  best-existing {best_existing:9.4f}"
                  f"  ({best_name})  rel {rel:+.4f}")
    gains = [r["relative_gain"] for r in rows]
    return {
        "per_problem": rows,
        "problems_evaluated": len(rows),
        "problems_improved": int(sum(1 for g in gains if g > MIN_RELATIVE_GAIN)),
        "best_relative_gain": round(float(max(gains)), 5) if gains else 0.0,
        "mean_relative_gain": round(float(np.mean(gains)), 5) if gains else 0.0,
        "utility_method": ("single-stage substitution on the locked split: the "
                           "candidate is compared against the BEST existing op of "
                           "the same in_sort, per problem. This is an approximation "
                           "of 're-run evolution with and without the op', which "
                           "would cost tens of minutes per candidate."),
        "split": split,
    }


def decide(utility, duplicate_of, library_size, capacity=DNA_CAPACITY):
    """昇格の可否と理由(判定はここに集約 — 呼び出し側で解釈を分岐させない)。"""
    if duplicate_of is not None:
        return False, f"behavioural duplicate of {duplicate_of!r}"
    if utility["problems_evaluated"] == 0:
        return False, "no problem in the workload accepts this in_sort"
    if utility["problems_improved"] == 0:
        return False, (f"improves no problem beyond the {MIN_RELATIVE_GAIN:.1%} "
                       f"noise floor (best {utility['best_relative_gain']:+.4f})")
    if library_size >= capacity:
        return False, (f"DNA library is at its capacity bound ({library_size}/"
                       f"{capacity}); displace the least-useful entry first")
    return True, (f"improves {utility['problems_improved']} problem(s); "
                  f"best relative gain {utility['best_relative_gain']:+.4f}")


def gate_candidate(ops, problems, name, fn, in_sort, out_sort, a=0.5, b=0.5,
                   split="locked", max_existing=None, capacity=DNA_CAPACITY,
                   library_size=None, verbose=False):
    """未登録の候補(callable)を一時登録して判定する。→ (promote, reason, 詳細)。

    ``champion_to_macro`` から呼ぶ入口。候補は判定が終われば必ず外れる。
    """
    dup = find_behavioural_duplicate(ops, fn, in_sort, a, b, limit=max_existing)
    with temp_op(ops, name, fn, in_sort, out_sort):
        util = counterfactual_utility(ops, problems, name, a, b, split=split,
                                      max_existing=max_existing, verbose=verbose)
    size = len(_load_library()) if library_size is None else library_size
    ok, reason = decide(util, dup, size, capacity)
    return ok, reason, {"duplicate_of": dup, "utility": util,
                        "library_size": size, "capacity": capacity}


def _load_library():
    path = os.path.join(ROOT, "data", "macro_champions.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data.get("macros", data) if isinstance(data, dict) else data
    except (OSError, ValueError):
        return []


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--op", required=True,
                    help="判定する op 名(レジストリに登録済みであること)")
    ap.add_argument("-a", type=float, default=0.5)
    ap.add_argument("-b", type=float, default=0.5)
    ap.add_argument("--split", default="locked",
                    choices=("train", "holdout", "locked"))
    ap.add_argument("--max-existing", type=int, default=None,
                    help="既存語彙の走査数を制限(粗いが速い予備判定用)")
    ap.add_argument("--capacity", type=int, default=DNA_CAPACITY)
    ap.add_argument("--json", metavar="PATH", help="判定結果を JSON で書き出す")
    args = ap.parse_args()

    import ops
    import problems

    if args.op not in ops._BY_NAME:
        raise SystemExit(f"[abort] op {args.op!r} がレジストリに無い")
    op = ops._BY_NAME[args.op]
    print(f"== promote gate: {args.op}  ({op.in_sort} -> {op.out_sort}, "
          f"category={op.category})")

    t0 = time.perf_counter()
    dup = find_behavioural_duplicate(ops, op.fn, op.in_sort, args.a, args.b,
                                     limit=args.max_existing)
    print(f"-- 重複判定: {dup or '重複なし'}  ({time.perf_counter() - t0:.1f}s)")

    t1 = time.perf_counter()
    print("-- counterfactual utility(既存語彙の最良 1 段との比較):")
    util = counterfactual_utility(ops, problems, args.op, args.a, args.b,
                                  split=args.split, max_existing=args.max_existing,
                                  verbose=True)
    print(f"   評価 {util['problems_evaluated']} problem / 改善 "
          f"{util['problems_improved']} / 最良 {util['best_relative_gain']:+.4f} "
          f"({time.perf_counter() - t1:.1f}s)")

    lib = _load_library()
    ok, reason = decide(util, dup, len(lib), args.capacity)
    print(f"\n== 判定: {'PROMOTE' if ok else 'REJECT'} — {reason}")
    print(f"   DNA library: {len(lib)}/{args.capacity}")

    if args.json:
        rec = {"op": args.op, "a": args.a, "b": args.b, "promote": ok,
               "reason": reason, "duplicate_of": dup, "utility": util,
               "library_size": len(lib), "capacity": args.capacity}
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, ensure_ascii=False, indent=1, default=str)
        print(f"   -> {args.json}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
