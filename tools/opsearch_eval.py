# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsearch_eval — 意味で op を引く検索(``fullseye.search_ops``)を評価問題集で採点する。

    py -3.11 tools/opsearch_eval.py                 # 集合ごとの hit@k と MRR、外した問い合わせ
    py -3.11 tools/opsearch_eval.py --json          # 機械可読

問題集 ``tests/data/rag_eval_queries.json``: 問い合わせ(利用者の言い方、ja / en)と、上位 k に 1 つでも入れば
当たりとする op の集合。期待する op は**全部が出荷ノートに実在すること**を先に確かめる(改名・削除で問題が
黙って解けなくなるのを防ぐ —— 実在しない名前があれば exit 2)。門は ``tests/test_rag_by_ops.py``。
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

EVAL = os.path.join(_ROOT, "tests", "data", "rag_eval_queries.json")


def load(path: str = EVAL) -> dict:
    with open(path, encoding="utf-8") as f:
        ev = json.load(f)
    if not ev.get("queries"):
        raise ValueError("評価問題集が空: %s" % path)
    return ev


def unknown_ops(ev: dict) -> list:
    """問題集が名指しする op のうち、出荷ノート(OP_NOTES.json)に無いもの。"""
    with open(os.path.join(_ROOT, "fullseye", "data", "OP_NOTES.json"), encoding="utf-8") as f:
        names = set(json.load(f)["notes"])
    return sorted({o for q in ev["queries"] for o in q["ops"] if o not in names})


def score(ev: dict, k: int | None = None, index_path: str | None = None) -> dict:
    """集合ごと(と全体)の hit@k と MRR(上位 20 まで)。外した問い合わせは上位 k の名前つきで返す。"""
    from fullseye.opsearch import search_ops
    k = k or int(ev.get("k", 5))
    per: dict = {}
    misses = []
    for q in ev["queries"]:
        names = [o["name"] for o in search_ops(q["q"], k=20, index_path=index_path)["ops"]]
        want = set(q["ops"])
        rank = next((i + 1 for i, n in enumerate(names) if n in want), None)
        hit = rank is not None and rank <= k
        for key in (q.get("set", "all"), "all"):
            s = per.setdefault(key, {"n": 0, "hit": 0, "rr": 0.0})
            s["n"] += 1
            s["hit"] += int(hit)
            s["rr"] += (1.0 / rank) if rank else 0.0
        if not hit:
            misses.append({"q": q["q"], "set": q.get("set"), "rank": rank, "top": names[:k]})
    for s in per.values():
        s["hit_at_k"] = round(s["hit"] / s["n"], 3)
        s["mrr"] = round(s["rr"] / s["n"], 3)
        del s["rr"]
    return {"k": k, "sets": per, "misses": misses}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("-k", type=int, default=None)
    ap.add_argument("--index", default=None, help="OP_SEARCH.json の別の版(比較用)")
    a = ap.parse_args(argv)
    ev = load()
    bad = unknown_ops(ev)
    if bad:
        print("評価問題集に実在しない op: %s" % ", ".join(bad), file=sys.stderr)
        return 2
    res = score(ev, a.k, a.index)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0
    for key in sorted(res["sets"]):
        s = res["sets"][key]
        print("%-8s hit@%d %d/%d = %.3f   MRR %.3f" % (key, res["k"], s["hit"], s["n"], s["hit_at_k"], s["mrr"]))
    for m in res["misses"]:
        print("  外れ [%s] %s  (rank %s)  top: %s" % (m["set"], m["q"], m["rank"], ", ".join(m["top"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
