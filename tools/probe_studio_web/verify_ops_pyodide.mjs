// Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
// 探針(probe): Pyodide(node)で verify_ops_body.run_all を回す —— ブラウザで実際に動く op を数える。
//   node verify_ops_pyodide.mjs <repo root> <verify_ops_body.py> <out dir> [min|full]
import { loadPyodide } from "pyodide";
import { readFileSync } from "node:fs";

const [repo, body, outDir, mode = "min"] = process.argv.slice(2);
const pkgs = mode === "full"
  ? ["numpy", "scipy", "threadpoolctl", "opencv-python", "scikit-image", "pillow", "pywavelets", "imageio"]
  : ["numpy", "scipy", "threadpoolctl"];
const t0 = performance.now();
const py = await loadPyodide({ packageCacheDir: process.env.PYO_CACHE });
await py.loadPackage(pkgs, { messageCallback: () => {} });
py.FS.mkdir("/repo"); py.FS.mount(py.FS.filesystems.NODEFS, { root: repo }, "/repo");
py.FS.mkdir("/out"); py.FS.mount(py.FS.filesystems.NODEFS, { root: outDir }, "/out");
py.FS.writeFile("/tmp/verify_ops_body.py", readFileSync(body, "utf-8"));
py.runPython(`import sys, os; sys.path.insert(0, "/tmp"); os.chdir("/repo")`);
const r = py.runPython(`
import json, verify_ops_body
s = verify_ops_body.run_all("/repo", "/out", "pyodide_${mode}")
json.dumps({k: v for k, v in s.items() if k != "rows"})
`);
console.log(r, JSON.stringify({ wall_s: Math.round((performance.now() - t0) / 1000) }));
