# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""レシピ全部に経路の検査を当てた表 / The route table over every existing recipe.

``docs/perf/pipeline_routes.{json,md}`` —— 既存のレシピ全部(``fullseye/data/RECIPE_INDEX.json``)に
   :func:`fullseye.explain_pipeline` を当てた表(一辺 2048、``device="auto"``、``assume_cuda=True`` = 経路表
   だけで決める)。比較のため、領域の解析の族(``accel_label.ADOPTED``)を経路から外した場合も並べる。
手書き経路の場面の台帳 ``GPU_ACCEL_USE.json`` は ``tools/gen_accel_use.py``(鎖の先頭近く)が書く。

    py -3.11 tools/gen_gpu_routes.py           # 書く
    py -3.11 tools/gen_gpu_routes.py --check   # 差があれば exit 1
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "docs" / "perf" / "pipeline_routes.json"
OUT_MD = ROOT / "docs" / "perf" / "pipeline_routes.md"
SHAPE = (2048, 2048)


def _dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def _plan(names):
    import api
    p = api.explain_pipeline(names, SHAPE, device="auto", assume_cuda=True)
    return {"n_gpu_stages": p["n_gpu_stages"], "n_switches": p["n_switches"], "n_transfers": p["n_transfers"],
            "stages": [{"op": s["op"], "on": s["on"], "path": s["path"], "reason": s["reason"]} for s in p["stages"]],
            "switches": p["switches"], "type_breaks": p["type_breaks"]}


def routes_table() -> dict:
    sys.path.insert(0, str(ROOT))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        import accel_label
        import gpu_route
    recipes = json.loads((ROOT / "fullseye" / "data" / "RECIPE_INDEX.json").read_text(encoding="utf-8"))["recipes"]
    rows = []
    gpu_route.clear_cache()
    after = {r["name"]: _plan([s["op"] for s in r["stages"]]) for r in recipes}
    full = gpu_route._accel_names()
    original = gpu_route._accel_names
    try:
        gpu_route._accel_names = lambda: frozenset(full - accel_label.ADOPTED)
        before = {r["name"]: _plan([s["op"] for s in r["stages"]]) for r in recipes}
    finally:
        gpu_route._accel_names = original
        gpu_route.clear_cache()
    for r in recipes:
        rows.append({"recipe": r["name"], "stages": [s["op"] for s in r["stages"]],
                     "before": before[r["name"]], "after": after[r["name"]]})
    multi = [x for x in rows if len(x["stages"]) >= 2]
    total = sum(len(x["stages"]) for x in multi)

    def summary(key):
        return {"recipes": len(multi), "stages": total,
                "gpu_stages": sum(x[key]["n_gpu_stages"] for x in multi),
                "all_gpu_recipes": sum(1 for x in multi if x[key]["n_gpu_stages"] == len(x["stages"])),
                "switches": sum(x[key]["n_switches"] for x in multi),
                "transfers": sum(x[key]["n_transfers"] for x in multi)}

    return {"generated_by": "tools/gen_gpu_routes.py", "shape": list(SHAPE), "device": "auto", "assume_cuda": True,
            "excluded_for_before": sorted(accel_label.ADOPTED),
            "summary": {"before": summary("before"), "after": summary("after")}, "recipes": rows}


def _mark(stage) -> str:
    return "%s[GPU]" % stage["op"] if stage["on"] == "gpu" else "%s[CPU:%s]" % (stage["op"], stage["reason"])


def routes_md(table: dict) -> str:
    sb, sa = table["summary"]["before"], table["summary"]["after"]
    out = ["# レシピの GPU 経路(生成物)", "",
           "`tools/gen_gpu_routes.py` が `fullseye.explain_pipeline(stages, (2048, 2048), device=\"auto\", "
           "assume_cuda=True)` を既存のレシピ全部(`fullseye/data/RECIPE_INDEX.json`)に当てた表。手で直さない。",
           "**前** = 領域の解析の族(`accel_label.ADOPTED`、%d op)を経路から外した場合、**後** = 今の経路。" % len(
               table["excluded_for_before"]),
           "`assume_cuda=True` は CUDA・CuPy・空き VRAM のある機械として経路表だけで決める(GPU の無い CI でも同じ表)。",
           "",
           "| 2 段以上のレシピ %d 本・%d 段 | GPU の段 | 全段 GPU | 切り替わり | 往復の見込み |" % (sa["recipes"], sa["stages"]),
           "|---|---:|---:|---:|---:|",
           "| 前 | %d | %d | %d | %d |" % (sb["gpu_stages"], sb["all_gpu_recipes"], sb["switches"], sb["transfers"]),
           "| 後 | %d | %d | %d | %d |" % (sa["gpu_stages"], sa["all_gpu_recipes"], sa["switches"], sa["transfers"]),
           "", "| レシピ | 前: 切替 / 往復 | 後: 切替 / 往復 | 後の段(CPU の段は理由つき) |", "|---|---:|---:|---|"]
    for r in table["recipes"]:
        b, a = r["before"], r["after"]
        out.append("| %s | %d / %d | %d / %d | %s |" % (
            r["recipe"], b["n_switches"], b["n_transfers"], a["n_switches"], a["n_transfers"],
            " → ".join(_mark(s) for s in a["stages"])))
    out += ["", "理由の語: `not_listed` = GPU 経路が無い / `chain_only` = 鎖の枠だけの経路で隣が GPU でない / "
            "`crossover` = 損益分岐。往復 = GPU の区間ごとに送り 1 回・戻し 1 回。", ""]
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    ns = ap.parse_args(argv)
    stale = []
    table = routes_table()
    for path, text in ((OUT_JSON, _dump(table)), (OUT_MD, routes_md(table))):
        if ns.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(path)
        else:
            path.write_text(text, encoding="utf-8", newline="\n")
    if stale:
        print("stale: " + ", ".join(str(p.relative_to(ROOT)) for p in stale))
        return 1
    if not ns.check:
        s = table["summary"]
        print("wrote pipeline_routes: before %s / after %s" % (s["before"], s["after"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
