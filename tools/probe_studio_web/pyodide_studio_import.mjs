// Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
// 探針(probe): Studio の Qt でない部品(studio.apply_display / param_specs / recipes / engine / studio_display /
// studio_search / studio_batch / studio_layout)が Pyodide で読めるかを 1 つずつ測る。
//   node pyodide_studio_import.mjs <repo root> <out json>
import { loadPyodide } from "pyodide";
import { writeFileSync } from "node:fs";

const [repo, outJson] = process.argv.slice(2);
const py = await loadPyodide({ packageCacheDir: process.env.PYO_CACHE });
await py.loadPackage(["numpy", "scipy", "threadpoolctl"], { messageCallback: () => {} });
py.FS.mkdir("/repo");
py.FS.mount(py.FS.filesystems.NODEFS, { root: repo }, "/repo");
const r = py.runPython(`
import sys, os, time, json, importlib, traceback
sys.path.insert(0, "/repo"); os.chdir("/repo")
res = {}
for m in ["api", "engine", "recipes", "param_specs", "studio_display", "studio_layout", "studio_search",
          "studio_batch", "studio_errors", "imgio", "studio"]:
    t = time.perf_counter()
    try:
        importlib.import_module(m); res[m] = {"ok": True, "s": round(time.perf_counter() - t, 2)}
    except BaseException as e:
        res[m] = {"ok": False, "err": "%s: %s" % (type(e).__name__, str(e)[:300])}
# apply_display と param_specs を実際に呼ぶ
try:
    import numpy as np, studio, param_specs, recipes, engine, api
    img = np.linspace(0, 1, 64 * 64, dtype=np.float32).reshape(64, 64)
    reg = api.apply(img, "otsu")
    outs = {}
    for mode in ["gray", "region overlay", "shaded relief", "height (color)", "viridis"]:
        t = time.perf_counter(); o = studio.apply_display(reg if mode == "region overlay" else img, mode, base=img)
        outs[mode] = [list(np.shape(o)), str(np.asarray(o).dtype), round((time.perf_counter() - t) * 1e3, 2)]
    res["apply_display"] = outs
    res["spec_gaussian"] = param_specs.spec_for("gaussian")["a"]["label"]
    res["recipes_n"] = len(recipes.names())
    eng = engine.FullseyeEngine.from_dict({"stages": [["gaussian", 0.4, 0.5], ["sobel_amp", 0.5, 0.5], ["otsu", 0.4, 0.5]]})
    res["engine_run_shape"] = list(np.shape(eng.run(img)))
except BaseException as e:
    res["calls_err"] = traceback.format_exc()[-800:]
json.dumps(res)
`);
writeFileSync(outJson, r);
console.log(r);
