# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""evolve_loop — 拡散 → 収縮 → 昇格 を 1 本で回す進化型アルゴリズム開発環境。

fullseye には部品が揃っていたが、**繋がっていなかった**:

  * 拡散 — 型付きランダム連鎖(``tools/chain_fuzz`` はバグ発見、``tools/chain_mine``
    は有用な合成の採掘)。op の組み合わせ空間を機械的に舐める。
  * 収縮 — 進化(``evolve.py`` / ``robust.py``)。problem の fitness で絞る。
  * 昇格 — champion を 1 個の op に凍結して語彙へ足す(``champion_to_macro`` +
    ``backends_macro``)。次の探索はその op を 1 段として選べる = 自己拡張。

本モジュールはその 3 段を 1 コマンドにする。**環境の本体は「判定を通った op だけが
語彙に入る」という規律**であって、実行の自動化そのものではない。だから driver は
どの段でも判定を緩めない — 緩めたい場合は明示のフラグが要り、その事実が記録に残る。

**なぜ「増加」と「洗練」が同時に要るか**: 語彙を増やすだけなら合成をいくらでも
足せるが、それは探索空間を薄めるだけで、悪い op は将来の探索すべてを汚染する。
逆に洗練だけでは既存語彙の組み替えに閉じる。**増やす経路(拡散)と、通さない
規律(ゲート)を同じループに置く**のがこの環境の設計。

段の責務分担(混ぜない):
  1. ``mine``    候補を出す。良し悪しは判定しない(記述子を多次元のまま残す)。
  2. ``screen``  安い判定で候補を落とす(恒等に近い・非決定的・型が課題に合わない)。
  3. ``gate``    高い判定 = counterfactual utility + 重複排除 + 容量上限。
  4. ``report``  何が通り、**何がどの理由で落ちたか**を必ず出す(無言の切り捨て禁止)。

昇格の実書き込み(``data/macro_champions.json`` の更新)は既定では **行わない**。
語彙を書き換えるのは不可逆に近い操作なので、``--write`` を明示したときだけ
``champion_to_macro.py`` を呼ぶ。既定は「通る候補の一覧を出すところまで」。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

#: 候補の連鎖長がこれを超えると昇格しない。長い合成は「1 op として読める」限界を
#: 超え、後から人が理解も検証もできない(進化した画像フィルタが解釈不能になる、と
#: いう GP の古典的な失敗)。
MAX_CHAIN_LEN = 6


def _run(cmd, *, check=True):
    """子プロセス実行(出力はそのまま流す)。失敗は例外にする。"""
    print("$ " + " ".join(cmd), flush=True)
    res = subprocess.run(cmd, cwd=ROOT, text=True)
    if check and res.returncode != 0:
        raise SystemExit(f"[abort] 失敗 (exit {res.returncode}): {' '.join(cmd)}")
    return res.returncode


def mine(chains, length, seed, out_path):
    """拡散: 候補となる op 合成を採掘する。→ 候補リスト。"""
    _run([sys.executable, os.path.join("tools", "chain_mine.py"),
          "--chains", str(chains), "--length", str(length),
          "--seed", str(seed), "--out", out_path])
    cands = []
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    cands.append(json.loads(line))
    return cands


def _sort_of(type_name):
    """型名 → 進化の sort。カタログ型名(``voxel``/``image2d``)と進化 sort 名
    (``volume``/``image``)の**どちらで来ても**解決する。

    採掘器はカタログ型名で連鎖を記録するが、進化側の記録や手書きの候補は sort 名を
    使う。ここを片方だけにすると、正しい候補を「型が不明」として黙って捨てる
    (実測でそれが起きた)。解決できなければ None — 推測で寄せない。
    """
    import backends_typed as bt
    import ops as _ops

    mapped = bt.TYPE_TO_SORT.get(type_name)
    if mapped is not None:
        return mapped
    known = {o.in_sort for o in _ops.REGISTRY} | {o.out_sort for o in _ops.REGISTRY}
    return type_name if type_name in known else None


def screen(candidates, problems, max_len=MAX_CHAIN_LEN):
    """安い判定で候補を絞る。→ (残った候補, 落とした理由の内訳)。

    ここで落とすのは「そもそも昇格の土俵に乗らないもの」だけ。**有用かどうかは
    判定しない**(それは gate の責務)。
    """
    from collections import Counter

    # ワークロードが実際に受け付ける入力型(進化の problem が持つ sort)
    accepted_sorts = {p.in_sort for p in problems.PROBLEMS.values()}
    kept, dropped = [], Counter()
    for c in candidates:
        ops_chain = c.get("ops") or []
        if not ops_chain:
            dropped["op 列が空"] += 1
            continue
        if len(ops_chain) > max_len:
            dropped[f"長すぎる(>{max_len} op)"] += 1
            continue
        if not c.get("deterministic", False):
            dropped["非決定的"] += 1
            continue
        in_sort = _sort_of(c.get("start"))
        if in_sort is None or in_sort not in accepted_sorts:
            dropped[f"課題が受け付けない入力型({c.get('start')})"] += 1
            continue
        kept.append(c)
    return kept, dropped


def _registry_name(ops, catalog_name):
    """採掘器のカタログ名 → 進化レジストリ名。

    橋渡し(``backends_typed``)は名前空間の衝突を避けるため ``tb_`` を前置する。
    採掘器はカタログ名で連鎖を作るので、ここで対応づける。どちらにも無ければ
    ``KeyError`` — **勝手に似た名前へ寄せない**(別の op を実行してしまう)。
    """
    if catalog_name in ops._BY_NAME:
        return catalog_name
    bridged = "tb_" + catalog_name
    if bridged in ops._BY_NAME:
        return bridged
    raise KeyError(catalog_name)


def gate(candidates, ops, problems, max_existing=None, capacity=None, verbose=False):
    """高い判定: counterfactual utility + 重複排除 + 容量上限。

    → (通った候補 [(候補, 理由, 詳細)], 落ちた候補 [(候補, 理由)])。
    """
    from promote_gate import DNA_CAPACITY, gate_candidate, stages_runner

    cap = DNA_CAPACITY if capacity is None else capacity
    passed, failed = [], []
    for i, c in enumerate(candidates):
        try:
            spec = [{"op": _registry_name(ops, name), "a": 0.5, "b": 0.5}
                    for name in c["ops"]]
            fn = stages_runner(ops, spec)
        except KeyError as exc:
            # 採掘器はカタログ名で連鎖を作るが、進化レジストリに橋渡しされて
            # いない op は再構成できない(既定は新 sort のみ = 58 op)。
            # IMGEVOLVE_WIDE_VOCAB=1 で 125 op まで広がる。
            failed.append((c, f"進化レジストリに無い op: {exc}"))
            continue
        in_sort = _sort_of(c["start"])
        out_sort = _sort_of(c.get("out_type")) or in_sort
        name = "_cand_%03d" % i
        try:
            ok, reason, detail = gate_candidate(
                ops, problems, name, fn, in_sort, out_sort,
                max_existing=max_existing, capacity=cap, verbose=verbose)
        except Exception as exc:                          # noqa: BLE001
            failed.append((c, f"判定中の例外: {type(exc).__name__}: {exc}"))
            continue
        (passed if ok else failed).append((c, reason, detail) if ok else (c, reason))
    return passed, failed


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--chains", type=int, default=400, help="拡散する連鎖数")
    ap.add_argument("--length", type=int, default=4, help="1 連鎖の op 数")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--mine-out", default=os.path.join("out", "evolve_loop_mine.jsonl"))
    ap.add_argument("--report", default=os.path.join("out", "evolve_loop_report.json"))
    ap.add_argument("--max-existing", type=int, default=120,
                    help="utility 判定で走査する既存 op 数の上限(速度と精度の trade-off)")
    ap.add_argument("--max-candidates", type=int, default=25,
                    help="gate にかける候補数の上限。**超過分は落としたものとして報告する**")
    ap.add_argument("--capacity", type=int, default=None, help="DNA 語彙の容量上限")
    ap.add_argument("--skip-mine", action="store_true",
                    help="採掘を省き、既存の --mine-out を読む(判定だけ回す)")
    ap.add_argument("--write", action="store_true",
                    help="通った候補を実際に語彙へ書き込む(既定は一覧を出すだけ)")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    import ops
    import problems

    t0 = time.perf_counter()
    print(f"== 進化型アルゴリズム開発環境: 語彙 {ops.N_OPS} op / "
          f"課題 {len(problems.PROBLEMS)} problem")

    print("\n== 1. 拡散(採掘)")
    if args.skip_mine:
        cands = []
        if os.path.exists(args.mine_out):
            with open(args.mine_out, encoding="utf-8") as fh:
                cands = [json.loads(x) for x in fh if x.strip()]
        print(f"   採掘を省略し {len(cands)} 候補を読み込み <- {args.mine_out}")
    else:
        cands = mine(args.chains, args.length, args.seed, args.mine_out)
        print(f"   候補 {len(cands)} 件")

    print("\n== 2. 収縮(安い判定)")
    kept, dropped = screen(cands, problems)
    for reason, n in dropped.most_common():
        print(f"   落選 {n:5d}  {reason}")
    print(f"   残り {len(kept)} 件")
    truncated = 0
    if len(kept) > args.max_candidates:
        truncated = len(kept) - args.max_candidates
        kept = kept[:args.max_candidates]
        # 無言の切り捨て禁止: 何件を見送ったかを必ず出す
        print(f"   [cap] gate にかけるのは先頭 {args.max_candidates} 件。"
              f"**{truncated} 件は今回未評価**(--max-candidates で増やせる)")

    print("\n== 3. 昇格判定(counterfactual utility + 重複 + 容量)")
    passed, failed = gate(kept, ops, problems, max_existing=args.max_existing,
                          capacity=args.capacity, verbose=args.verbose)
    from collections import Counter
    fail_reasons = Counter(r.split(";")[0].split("(")[0].strip() for _c, r in failed)
    for reason, n in fail_reasons.most_common(8):
        print(f"   不通過 {n:4d}  {reason}")
    print(f"   通過 {len(passed)} 件 / 判定 {len(kept)} 件")

    for c, reason, detail in passed:
        print(f"\n   ★ {' -> '.join(c['ops'])}")
        print(f"      {reason}")
        for row in detail["utility"]["per_problem"]:
            # relative_gain は **None になりうる**: 既存最良が 0 の課題では比が
            # 定義できないので promote_gate が None を入れ、絶対改善で判定する
            # (以前は 1e-12 を足して +7e11 を作っていた)。None を数値として
            # 扱うと TypeError で落ちるので、比の有無で表示を分ける。
            rel = row["relative_gain"]
            if not row.get("improved", (rel or 0.0) > 0):
                continue
            shown = "rel undefined (abs %+.4f)" % row["absolute_gain"] \
                if rel is None else "%+.4f" % rel
            print(f"        {row['problem']}: {row['candidate']} vs "
                  f"{row['best_existing']} ({row['best_existing_op']}) "
                  f"{shown} {row['unit']}")

    rec = {
        "vocabulary_size": ops.N_OPS,
        "problems": list(problems.PROBLEMS),
        "mined": len(cands),
        "screened_out": dict(dropped),
        "gated": len(kept),
        "not_evaluated_due_to_cap": truncated,
        "passed": [{"ops": c["ops"], "start": c["start"], "reason": r,
                    "utility": d["utility"]} for c, r, d in passed],
        "failed": [{"ops": c.get("ops"), "reason": r} for c, r in failed],
        "wrote_to_vocabulary": False,
        "seconds": round(time.perf_counter() - t0, 1),
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)
    with open(args.report, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, ensure_ascii=False, indent=1, default=str)
    print(f"\n== 報告 -> {args.report}  ({rec['seconds']}s)")

    if args.write and passed:
        # 語彙の書き換えは不可逆に近い。ここへ来るのは --write を明示したときだけ。
        print("\n== 4. 語彙へ書き込み(--write 指定)")
        print("   注意: 現状の champion_to_macro.py は champion_<problem>.json を"
              " 入力に取るため、採掘候補の直接書き込みは未実装。"
              "通過候補を進化の初期値として使うのが次の段。")
    elif args.write:
        print("\n== 4. 書き込み対象なし(通過候補ゼロ)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
