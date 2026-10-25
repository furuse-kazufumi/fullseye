// Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
// Studio-lite v0 の門(ブラウザ側): Pyodide(node)で core.py を通して 10 レシピを走らせ、
//   <out>/recipes/<i>.json    … ブラウザが書くレシピ(core.recipe_json = engine.to_dict の形)
//   <out>/browser_outputs.npz … 各レシピの最終結果(配列)
//   <out>/browser_gate.json   … 所要 ms と Studio 形式(bypass つき)の読み込み結果
// を残す。CPython 側(gate_native.py)がこれを読んで照合する。
//   node gate_browser.mjs <repo root> <out dir>
import { loadPyodide } from "pyodide";
import { readFileSync } from "node:fs";

const [repo, outDir] = process.argv.slice(2);
const py = await loadPyodide({ packageCacheDir: process.env.PYO_CACHE });
await py.loadPackage(["numpy", "scipy", "threadpoolctl"], { messageCallback: () => {} });
py.FS.mkdir("/repo"); py.FS.mount(py.FS.filesystems.NODEFS, { root: repo }, "/repo");
py.FS.mkdir("/out"); py.FS.mount(py.FS.filesystems.NODEFS, { root: outDir }, "/out");
py.FS.writeFile("/tmp/verify_ops_body.py", readFileSync(`${repo}/tools/probe_studio_web/verify_ops_body.py`, "utf-8"));
const r = py.runPython(`
import sys, os, json, time
sys.path.insert(0, "/tmp"); sys.path.insert(0, "/repo"); sys.path.insert(0, "/repo/studio_lite"); os.chdir("/repo")
import numpy as np, core, verify_ops_body
core.set_subset(open("/repo/studio_lite/ops_subset.json", encoding="utf-8").read())
G = json.load(open("/repo/studio_lite/gates/recipes_gate.json", encoding="utf-8"))
img = verify_ops_body.load_input("/repo")
os.makedirs("/out/recipes", exist_ok=True)
arrays, rows = {}, []
for i, rc in enumerate(G["recipes"]):
    st = json.dumps(rc["stages"])
    text = core.recipe_json(rc["name"], st)
    open("/out/recipes/%02d.json" % i, "w", encoding="utf-8").write(text)
    t = time.perf_counter(); out = core.run_chain_raw(img, st); ms = (time.perf_counter() - t) * 1e3
    shown = core.run_chain(img, st, "gray")
    key = "r%02d" % i
    if isinstance(out, np.ndarray):
        arrays[key] = out
        rows.append({"i": i, "name": rc["name"], "kind": "ndarray", "dtype": str(out.dtype), "shape": list(out.shape),
                     "ms": round(ms, 2), "stage_ms": [c["ms"] for c in shown["cards"][1:]], "error": shown["error"]})
    else:
        rows.append({"i": i, "name": rc["name"], "kind": type(out).__name__, "repr": repr(out), "ms": round(ms, 2),
                     "stage_ms": [c["ms"] for c in shown["cards"][1:]], "error": shown["error"]})
np.savez_compressed("/out/browser_outputs.npz", **arrays)
# Studio が保存する形(4 要素の bypass つき段)をブラウザ側が読めるか
sf = core.load_recipe(json.dumps(G["studio_format_sample"]))
res = {"python": sys.version.split()[0], "platform": sys.platform, "rows": rows, "studio_format_loaded": json.loads(sf)}
open("/out/browser_gate.json", "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1))
json.dumps({"n": len(rows), "errors": [r["name"] for r in rows if r["error"]], "studio_format_loaded": res["studio_format_loaded"]})
`);
console.log(r);
