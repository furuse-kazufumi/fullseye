// Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
// 探針(probe): node 上の Pyodide に repo を NODEFS で見せ、`import api` と代表 10 op を計時する。
//   node pyodide_trial.mjs <repo root> <bench_body.py> <inventory rows json> <out json> [min|full]
// 依存は pyodide npm(scratchpad に導入)。配布物 wheel は Pyodide の CDN から取り、PYO_CACHE に置く。
import { loadPyodide } from "pyodide";
import { writeFileSync, readFileSync } from "node:fs";

const [repo, benchBody, rowsJson, outJson, mode = "min"] = process.argv.slice(2);
const pkgs = mode === "full"
  ? ["numpy", "scipy", "threadpoolctl", "opencv-python", "scikit-image", "pillow", "pywavelets", "imageio"]
  : ["numpy", "scipy", "threadpoolctl"];

const res = { mode, pkgs };
let t = performance.now();
const py = await loadPyodide({ packageCacheDir: process.env.PYO_CACHE });
res.boot_ms = Math.round(performance.now() - t);
t = performance.now();
await py.loadPackage(pkgs, { messageCallback: () => {} });
res.load_pkgs_ms = Math.round(performance.now() - t);
py.FS.mkdir("/repo");
py.FS.mount(py.FS.filesystems.NODEFS, { root: repo }, "/repo");
py.runPython(`import sys, os; sys.path.insert(0, "/repo"); os.chdir("/repo")`);

// 1) op を定義する全モジュールを 1 つずつ import して、読めないものと理由を集める。
const mods = [...new Set(JSON.parse(readFileSync(rowsJson, "utf-8")).map(r => r.module).filter(Boolean))].sort();
py.globals.set("MODS", py.toPy(mods));
t = performance.now();
const modReport = py.runPython(`
import importlib, json, time, traceback
ok, bad = [], {}
for m in MODS:
    try:
        t0 = time.perf_counter(); importlib.import_module(m); ok.append(m)
    except BaseException as e:
        bad[m] = "%s: %s" % (type(e).__name__, str(e)[:200])
json.dumps({"ok": len(ok), "bad": bad})
`);
res.module_import_ms = Math.round(performance.now() - t);
res.modules = JSON.parse(modReport);

// 2) 代表 10 op の計時(CPython と同じ本体ファイル)。
py.FS.writeFile("/tmp/bench_body.py", readFileSync(benchBody, "utf-8"));
py.runPython(`sys.path.insert(0, "/tmp")`);
t = performance.now();
const bench = py.runPython(`
import json, bench_body
json.dumps(bench_body.run_bench(5))
`);
res.bench_wall_ms = Math.round(performance.now() - t);
res.bench = JSON.parse(bench);
writeFileSync(outJson, JSON.stringify(res, null, 1));
console.log(JSON.stringify({ mode, boot_ms: res.boot_ms, load_pkgs_ms: res.load_pkgs_ms, modules_ok: res.modules.ok,
  modules_bad: Object.keys(res.modules.bad).length, import_api_s: res.bench.import_api_s, ops: res.bench.ops }));
