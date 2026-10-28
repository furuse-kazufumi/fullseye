# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0.
"""Generate the measured RAG recall and synonym-gap report.

This is deliberately CPU-only and does not execute operators.  It measures the
committed benchmark using the same public retrieval functions as MCP.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fullseye.opsearch import plan, plan_chain, search_ops  # noqa: E402

SOURCE = os.path.join(ROOT, "docs", "ops", "rag_benchmark.json")
OUTPUT = os.path.join(ROOT, "docs", "rag_synonym_gaps.json")


def recall(found, relevant):
    return len(set(found) & set(relevant)) / len(set(relevant))


def build() -> dict:
    with open(SOURCE, encoding="utf-8") as f:
        rows = json.load(f)["queries"]
    if not rows:
        raise SystemExit("rag_benchmark.json has no queries")
    categories = defaultdict(lambda: {"search": [], "plan": [], "executable": []})
    queries, gaps = [], []
    for row in rows:
        direct = [x["name"] for x in search_ops(row["query"], 10)["ops"]]
        planned = plan_chain(row["query"], row["start_sort"], row["goal_sort"], k=10, max_depth=4)
        names = [x["name"] for stage in planned.get("stages", []) for x in stage["candidates"]]
        default = plan(row["start_sort"], row["goal_sort"], goal=row["query"])
        executable_names = [name for p in default.get("plans", []) for name in p["ops"]]
        sr, pr = recall(direct, row["relevant"]), recall(names, row["relevant"])
        er = recall(executable_names, row["relevant"])
        categories[row["category"]]["search"].append(sr)
        categories[row["category"]]["plan"].append(pr)
        categories[row["category"]]["executable"].append(er)
        rec = {"id": row["id"], "category": row["category"], "query": row["query"],
               "search_recall_at_10": sr, "untyped_recall_at_10": sr, "plan_recall_at_10": pr,
               "executable_plan_recall_at_10": er,
               "missed_by_search": sorted(set(row["relevant"]) - set(direct)),
               "missed_by_plan": sorted(set(row["relevant"]) - set(names))}
        queries.append(rec)
        if rec["missed_by_search"]:
            gaps.append({k: rec[k] for k in ("id", "category", "query", "missed_by_search")})
    av = lambda xs: round(sum(xs) / len(xs), 6)
    by_category = {name: {"n_queries": len(v["plan"]), "search_recall_at_10": av(v["search"]),
                          "plan_recall_at_10": av(v["plan"]),
                          "executable_plan_recall_at_10":av(v["executable"])} for name, v in sorted(categories.items())}
    return {"generated_by": "tools/gen_rag_benchmark_report.py", "source": "docs/ops/rag_benchmark.json",
            "n_queries": len(rows),
            "overall": {"search_recall_at_10": av([q["search_recall_at_10"] for q in queries]),
                        "untyped_recall_at_10": av([q["untyped_recall_at_10"] for q in queries]),
                        "plan_recall_at_10": av([q["plan_recall_at_10"] for q in queries]),
                        "executable_plan_recall_at_10":av([q["executable_plan_recall_at_10"] for q in queries])},
            "categories": by_category, "queries": queries, "synonym_gaps": gaps}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    text = json.dumps(build(), ensure_ascii=False, indent=2) + "\n"
    current = open(OUTPUT, encoding="utf-8").read() if os.path.exists(OUTPUT) else None
    if args.check:
        if current != text:
            print("rag synonym-gap report is stale; run tools/gen_rag_benchmark_report.py")
            return 1
    else:
        with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print("wrote %s (%d queries)" % (os.path.relpath(OUTPUT, ROOT), len(build()["queries"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
