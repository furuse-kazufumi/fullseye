# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""mcp_find_ops_eval — MCP の ``fullseye_find_ops`` を、日本語を含む評価問題集で採点する。

    py -3.11 tools/mcp_find_ops_eval.py                  # この木: 集合ごとの数と、外した問い
    py -3.11 tools/mcp_find_ops_eval.py --json           # 機械可読
    py -3.11 tools/mcp_find_ops_eval.py --root <木>      # 別の木のコードで採点する(問いはこの木の物)

別の木(例: origin/master)と比べる時は、その木を取り出して ``--root`` に渡す::

    git archive origin/master | tar -x -C <空のフォルダ>
    py -3.11 tools/mcp_find_ops_eval.py --root <空のフォルダ>

問題集は ``tests/data/mcp_find_ops_eval_ja.json``。数えるのは集合ごとに:

- ``hit``: 上位 k 件に「関係する」op が 1 件でも入った問いの数(関係する = 名前が問いの正解の型に合う)
- ``usable``: 上位 k 件に「関係する かつ その木の OP_GRAPH で MCP から走る(verified_executable)」op が入った問いの数
- ``relevant_ops`` / ``usable_ops``: 上位 k 件のうち関係する op の数 / そのうち MCP で走る op の数(全問の合計)

★2026-11-15(独立レビュー): PR #318 の本文の「find_ops 23 回、14 → 19 / 5 → 16」は、問いと採点が repo に
無く再現できなかった。問いと正解の型をここに置き、合わせるのに使った問い(``tuned``)とそうでない問いを分けて
数える。異常に良い数は、合わせた問いの側に偏っていないかを先に見る。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVAL = os.path.join(_ROOT, "tests", "data", "mcp_find_ops_eval_ja.json")


def load(path: str = EVAL) -> dict:
    """問題集を読む。空・正規表現の壊れた問いは ``ValueError``。"""
    with open(path, encoding="utf-8") as fh:
        ev = json.load(fh)
    if not ev.get("queries"):
        raise ValueError("評価問題集が空: %s" % path)
    for q in ev["queries"]:
        re.compile(q["relevant"])
        if not isinstance(q.get("args"), dict) or not q["args"].get("query"):
            raise ValueError("問い合わせの無い問い: %r" % (q,))
    return ev


def evaluate(ev: dict | None = None, *, root: str | None = None, cat=None, store=None) -> dict:
    """問題集を ``fullseye_find_ops`` で採点する。``root`` を渡すとその木の fullseye を読む(先に import していない時だけ)。

    返り値 ``{"k", "sets": {集合: {"n", "hit", "usable", "relevant_ops", "usable_ops"}}, "rows": [...]}``。集合は
    問題集の ``set`` と、それを ``tuned`` / ``untuned`` で分けた ``<set>/tuned`` ``<set>/untuned``。"""
    ev = ev or load()
    # ★既定はこの道具のある木。sys.path に足さないと、tools/ から起動した時に editable install の別の木の
    #   fullseye を読む(2026-11-15 に実際に別の木の数を出した)。
    root = os.path.abspath(root or _ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    from fullseye.mcp import server as S
    from fullseye.mcp.catalog import Catalog
    from fullseye.mcp.handles import HandleStore
    from fullseye.opsearch import _graph
    if not os.path.abspath(S.__file__).startswith(root + os.sep):
        raise RuntimeError("%s の fullseye を読めなかった(読んだのは %s)" % (root, S.__file__))
    cat = cat if cat is not None else Catalog.load()
    store = store if store is not None else HandleStore(thumb_dir=tempfile.mkdtemp(prefix="fullseye-eval-"))
    runnable = {e["op"] for e in _graph()["edges"] if e.get("verified_executable")}
    k = int(ev.get("k", 5))
    sets: dict = {}
    rows = []
    for q in ev["queries"]:
        ops = S.call_tool("fullseye_find_ops", dict(q["args"]), cat, store)["structuredContent"]["ops"]
        top = [o["name"] for o in ops[:k]]
        rel = [n for n in top if re.search(q["relevant"], n)]
        use = [n for n in rel if n in runnable]
        for key in (q["set"], "%s/%s" % (q["set"], "tuned" if q.get("tuned") else "untuned")):
            s = sets.setdefault(key, {"n": 0, "hit": 0, "usable": 0, "relevant_ops": 0, "usable_ops": 0})
            s["n"] += 1
            s["hit"] += bool(rel)
            s["usable"] += bool(use)
            s["relevant_ops"] += len(rel)
            s["usable_ops"] += len(use)
        rows.append({"set": q["set"], "tuned": bool(q.get("tuned")), "query": q["args"]["query"], "top": top,
                     "relevant": rel, "usable": use})
    return {"k": k, "fullseye": os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(S.__file__)))),
            "sets": sets, "rows": rows}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--root", default=None, help="採点する木(既定はこの道具のある木)")
    a = ap.parse_args(argv)
    res = evaluate(root=a.root)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0
    print("k=%d  fullseye=%s" % (res["k"], res["fullseye"]))
    for key in sorted(res["sets"]):
        s = res["sets"][key]
        print("%-34s n=%2d  hit %2d  usable %2d  relevant_ops %3d  usable_ops %3d"
              % (key, s["n"], s["hit"], s["usable"], s["relevant_ops"], s["usable_ops"]))
    for r in res["rows"]:
        if not r["relevant"]:
            print("  外れ [%s%s] %s  top: %s" % (r["set"], "/tuned" if r["tuned"] else "", r["query"], ", ".join(r["top"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
