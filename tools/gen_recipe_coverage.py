"""Generate docs/RECIPE_COVERAGE.md + docs/recipe_coverage.json — how far the recipes cover Fullseye.

Static (nothing is executed here; tests/test_recipebook.py runs every recipe). Per recipe: family, task
class, runner (mcp / python), stages, **type cuts** (declared sorts that do not connect, target 0) and
**GPU route switches** (adjacent stages where one has a pipeline GPU route and the other does not — each one
is a host<->device hand-over), read from the snapshot docs/recipe_gpu_routes.json
(tools/snapshot_recipe_gpu_routes.py). Ops absent from the snapshot are 未計測 and the recipe's switch count
is then 未計測 too (never guessed as "CPU").

    py -3.11 tools/gen_recipe_coverage.py            # write
    py -3.11 tools/gen_recipe_coverage.py --check    # exit 1 if the committed files differ
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "docs" / "RECIPE_COVERAGE.md"
JS = ROOT / "docs" / "recipe_coverage.json"
SNAP = ROOT / "docs" / "recipe_gpu_routes.json"


def _legacy_as_book(r):
    return {"name": r["name"], "family": "2d", "input_sort": "image",
            "stages": [{"op": op, "a": a, "b": b} for op, a, b in r["stages"]]}


def gpu_flags(stages, routes):
    """段ごとの GPU 経路の有無(True/False)、snapshot に無い op は None。"""
    out = []
    for st in stages:
        if st["op"] not in routes:
            out.append(None)
        else:
            out.append(routes[st["op"]] is not None)
    return out


def switches(flags):
    if any(f is None for f in flags):
        return None
    return sum(1 for a, b in zip(flags, flags[1:]) if a != b)


def build() -> dict:
    os.environ.setdefault("FULLSEYE_DEVICE", "cpu")
    sys.path.insert(0, str(ROOT))
    import fullseye  # noqa: F401
    import recipes
    from fullseye import recipebook as rb
    # RECIPE_INDEX は読まない(docmap の段より前に回すため。runner / 分類は同じ規則でここで決める)。
    sys.path.insert(0, str(ROOT / "tools"))
    from gen_recipe_index import LEGACY_TASK_CLASS
    index = {r["name"]: {"runner": "mcp", "task_class": LEGACY_TASK_CLASS.get(r["task"], "preprocess"), "halcon": None}
             for r in recipes.RECIPES}
    index.update({r["name"]: {"runner": "mcp" if rb.is_mcp_runnable(r) else "python",
                              "task_class": r["task_class"], "halcon": r.get("halcon")} for r in rb.RECIPES})
    snap = json.loads(SNAP.read_text(encoding="utf-8")) if SNAP.exists() else {"routes": {}}
    routes = snap.get("routes", {})
    fam_ops = rb.op_families()
    fam_size = Counter(f for fams in fam_ops.values() for f in fams)
    cat_of = {}
    for p in (ROOT / "docs" / "ops" / "2d").glob("*/*.md"):
        if p.parent.name != "guides":
            cat_of[p.stem] = p.parent.name
    rows = []
    for src, recs in (("recipes.py", [_legacy_as_book(r) for r in recipes.RECIPES]), ("recipebook", rb.RECIPES)):
        for r in recs:
            ix = index.get(r["name"], {})
            flags = gpu_flags(r["stages"], routes)
            rows.append({
                "name": r["name"], "source": src, "family": r["family"],
                "task_class": ix.get("task_class") or r.get("task_class"), "halcon": ix.get("halcon"),
                "runner": ix.get("runner"), "stages": len(r["stages"]),
                "ops": [st["op"] for st in r["stages"]],
                "type_cuts": rb.type_cuts(r),
                "truth_gate": bool(r.get("expect")) if src == "recipebook" else (r["name"].startswith("FA — ")),
                "gpu_stages": None if None in flags else sum(flags),
                "gpu_unmeasured_ops": [st["op"] for st, f in zip(r["stages"], flags) if f is None],
                "gpu_switches": switches(flags)})
    fams = list(rb.families())
    by_fam = Counter(r["family"] for r in rows)
    ops_used = {}
    for r in rows:
        for op in r["ops"]:
            for f in fam_ops.get(op, ()):
                ops_used.setdefault(f, set()).add(op)
    cats_2d = sorted(set(cat_of.values()))
    cats_hit = sorted({cat_of[op] for r in rows for op in r["ops"] if op in cat_of})
    measured = [r for r in rows if r["gpu_switches"] is not None]
    summary = {
        "recipes": len(rows), "recipes_py": sum(r["source"] == "recipes.py" for r in rows),
        "recipebook": sum(r["source"] == "recipebook" for r in rows),
        "multi_stage": sum(r["stages"] >= 2 for r in rows),
        "families_total": len(fams), "families_covered": sum(1 for f in fams if by_fam.get(f)),
        "families_uncovered": [f for f in fams if not by_fam.get(f)],
        "task_class": dict(sorted(Counter(r["task_class"] for r in rows).items())),
        "halcon_chapters": dict(sorted(Counter(r["halcon"] for r in rows if r["halcon"]).items())),
        "runner": dict(sorted(Counter(r["runner"] for r in rows).items())),
        "truth_gated": sum(r["truth_gate"] for r in rows),
        "type_cuts_total": sum(r["type_cuts"] for r in rows),
        "recipes_with_type_cuts": sum(r["type_cuts"] > 0 for r in rows),
        "distinct_ops": len({op for r in rows for op in r["ops"]}),
        "categories_2d_total": len(cats_2d), "categories_2d_covered": len(cats_hit),
        "categories_2d_uncovered": [c for c in cats_2d if c not in cats_hit],
        "gpu": {"snapshot_commit": snap.get("gpu_worktree_commit"),
                "recipes_measured": len(measured), "recipes_unmeasured": len(rows) - len(measured),
                "recipes_with_gpu_stage": sum(1 for r in measured if r["gpu_stages"]),
                "switches_total": sum(r["gpu_switches"] for r in measured),
                "switch_histogram": dict(sorted(Counter(r["gpu_switches"] for r in measured).items()))},
    }
    families = [{"family": f, "ops": fam_size[f], "recipes": by_fam.get(f, 0),
                 "ops_used": len(ops_used.get(f, ()))} for f in fams]
    return {"summary": summary, "families": families, "recipes": rows,
            "missing_ops": list(rb.MISSING_OPS), "failed_attempts": list(rb.FAILED_ATTEMPTS)}


def _cell(v):
    return "未計測" if v is None else str(v)


def render(d: dict) -> str:
    s = d["summary"]
    g = s["gpu"]
    L = ["<!-- generated by tools/gen_recipe_coverage.py — do not edit by hand -->",
         "# レシピの網羅(族・課題・型の繋がり・GPU 経路)", "",
         "レシピ = 型で繋がる op の組み合わせ例。正本は `recipes.py`(Studio の見本 %d 本)と "
         "`fullseye/recipebook/`(網羅用 %d 本)。全部を `tests/test_recipebook.py` が合成入力 2 種で実際に走らせ、"
         "型の繋がり・出力が定数でないこと・入力に応じて動くこと・真値の門(ある物)を確かめる。" % (s["recipes_py"], s["recipebook"]),
         "MCP の検索(`fullseye_find_ops`)は runner = mcp(MCP の pipeline でそのまま走る物)だけを返す。", "",
         "## 要約", "",
         "| 項目 | 値 |", "|---|---|",
         "| レシピ | %d(2 段以上 %d) |" % (s["recipes"], s["multi_stage"]),
         "| 族(docs/ops)の網羅 | %d / %d |" % (s["families_covered"], s["families_total"]),
         "| 2-D の category の網羅 | %d / %d |" % (s["categories_2d_covered"], s["categories_2d_total"]),
         "| 使った op(重複なし) | %d |" % s["distinct_ops"],
         "| 真値の門つき | %d |" % s["truth_gated"],
         "| runner | %s |" % ", ".join("%s %d" % kv for kv in s["runner"].items()),
         "| 型の切れ目 | 合計 %d(切れ目のあるレシピ %d) |" % (s["type_cuts_total"], s["recipes_with_type_cuts"]),
         "| GPU 経路の切り替わり | 合計 %d(測ったレシピ %d、GPU 段を含む %d、未計測 %d、snapshot `%s`) |"
         % (g["switches_total"], g["recipes_measured"], g["recipes_with_gpu_stage"], g["recipes_unmeasured"],
            (g["snapshot_commit"] or "なし")[:10]),
         "", "課題の分類: " + ", ".join("%s %d" % kv for kv in s["task_class"].items()), "",
         "HALCON の章: " + ", ".join("%s %d" % kv for kv in s["halcon_chapters"].items()), ""]
    if s["families_uncovered"]:
        L += ["**レシピの無い族**: " + ", ".join(s["families_uncovered"]), ""]
    if s["categories_2d_uncovered"]:
        L += ["2-D でレシピの無い category: " + ", ".join(s["categories_2d_uncovered"]), ""]
    L += ["GPU の切り替わり = 隣り合う 2 段で、片方だけが pipeline 文脈の GPU 経路(`gpu_route.route(op, \"pipeline\")`)"
          "を持つ箇所の数(CPU と GPU の間の受け渡し 1 回)。snapshot に無い op を含むレシピは未計測。", "",
          "## 族ごと", "", "| 族 | op 数 | レシピ | 使った op |", "|---|---:|---:|---:|"]
    for f in d["families"]:
        L.append("| %s | %d | %d | %d |" % (f["family"], f["ops"], f["recipes"], f["ops_used"]))
    L += ["", "## レシピごと", "",
          "| レシピ | 族 | 課題 | runner | 段 | 型の切れ目 | GPU 段 | GPU 切替 | 真値 |",
          "|---|---|---|---|---:|---:|---:|---:|---|"]
    for r in d["recipes"]:
        L.append("| %s | %s | %s | %s | %d | %d | %s | %s | %s |" % (
            r["name"].replace("|", "/"), r["family"], r["task_class"], r["runner"], r["stages"], r["type_cuts"],
            _cell(r["gpu_stages"]), _cell(r["gpu_switches"]), "あり" if r["truth_gate"] else "—"))
    L += ["", "## 足りない op(レシピを組もうとして無かった物)", ""]
    if d["missing_ops"]:
        L += ["| 族 | 欲しい物 | 理由 |", "|---|---|---|"]
        for m in d["missing_ops"]:
            L.append("| %s | %s | %s |" % (m.get("family"), str(m.get("need")).replace("|", "/"), str(m.get("why")).replace("|", "/")))
    else:
        L.append("なし")
    L += ["", "## 組もうとして落とした鎖(op の不具合・宣言の嘘・入力が作れない等)", ""]
    if d["failed_attempts"]:
        L += ["| 族 | 鎖 | op | 原因 | 内容 |", "|---|---|---|---|---|"]
        for f in d["failed_attempts"]:
            L.append("| %s | %s | %s | %s | %s |" % (f.get("family"), str(f.get("recipe")).replace("|", "/"), f.get("op"),
                                                    f.get("cause"), str(f.get("error")).replace("|", "/").replace("\n", " ")[:240]))
    else:
        L.append("なし")
    L.append("")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    d = build()
    md, js = render(d), json.dumps(d, ensure_ascii=False, indent=1) + "\n"
    if a.check:
        bad = [p for p, t in ((MD, md), (JS, js)) if not p.exists() or p.read_text(encoding="utf-8") != t]
        if bad:
            print("drift:", *[str(p) for p in bad])
            return 1
        return 0
    MD.write_text(md, encoding="utf-8", newline="\n")
    JS.write_text(js, encoding="utf-8", newline="\n")
    print(MD, JS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
