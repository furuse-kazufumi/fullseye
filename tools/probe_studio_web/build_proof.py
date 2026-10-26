# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""探針(probe): 「ブラウザで fullseye の op 列を 1 本走らせる」最小の証明ページを、**repo の外**に組む。

    py -3.11 tools/probe_studio_web/build_proof.py --pyodide-dir <pyodide npm 配布物> --wheels-dir <numpy/scipy の wheel> --out <dist>

出来るもの(すべて dist の中、外部 URL を読まない):
  proof.html                 … ページ本体(tools/probe_studio_web/proof.html の複製)
  pyodide/                   … Pyodide 本体(pyodide.asm.wasm / .mjs / python_stdlib.zip / pyodide-lock.json)+ wheel
  fullseye_subset.zip        … ``import api`` が読む repo 内モジュール(実測で 414 本)を zip にしたもの
  sizes.json                 … 各部のバイト数

これは生成物ではない(dist は repo に入れない)。regen_all の表には NOT_A_GENERATOR として載せる。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

PYODIDE_FILES = ["pyodide.asm.wasm", "pyodide.asm.mjs", "pyodide.mjs", "pyodide.js",
                 "python_stdlib.zip", "pyodide-lock.json"]
EXTRA_DATA = ["fullseye/data"]      # knob 表など、api が遅延で読む小さな JSON


def subset_modules() -> list[str]:
    """``import api``(+ 3-D / 光学の代表モジュール)で読まれる repo 内 .py の相対パス。"""
    import importlib
    cwd = ROOT.lower()
    importlib.import_module("api")
    for m in ("ransac_fit", "curvature3d", "optics", "param_specs", "recipes", "engine"):
        try:
            importlib.import_module(m)
        except Exception:  # noqa: BLE001  (探針: 読めない物は入れないだけ)
            pass
    files = []
    for m in list(sys.modules.values()):
        f = getattr(m, "__file__", None)
        if f and os.path.isfile(f) and os.path.dirname(os.path.abspath(f)).lower().startswith(cwd):
            rel = os.path.relpath(os.path.abspath(f), ROOT).replace(os.sep, "/")
            if not rel.startswith(("tools/", "tests/")):
                files.append(rel)
    return sorted(set(files))


def build_zip(path: str) -> int:
    mods = subset_modules()
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel in mods:
            z.write(os.path.join(ROOT, rel), rel)
        for d in EXTRA_DATA:
            base = os.path.join(ROOT, d)
            if os.path.isdir(base):
                for n in sorted(os.listdir(base)):
                    p = os.path.join(base, n)
                    if os.path.isfile(p) and n.endswith(".json"):
                        z.write(p, d + "/" + n)
    return len(mods)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pyodide-dir", required=True)
    ap.add_argument("--wheels-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--page", default=os.path.join(HERE, "proof.html"))
    a = ap.parse_args(argv)
    out = a.out
    os.makedirs(os.path.join(out, "pyodide"), exist_ok=True)
    sizes = {}
    for n in PYODIDE_FILES:
        src = os.path.join(a.pyodide_dir, n)
        if not os.path.exists(src):
            raise SystemExit("pyodide の配布物に %s が無い" % n)
        shutil.copy2(src, os.path.join(out, "pyodide", n))
        sizes["pyodide/" + n] = os.path.getsize(src)
    for n in sorted(os.listdir(a.wheels_dir)):
        if n.endswith(".whl"):
            shutil.copy2(os.path.join(a.wheels_dir, n), os.path.join(out, "pyodide", n))
            sizes["pyodide/" + n] = os.path.getsize(os.path.join(a.wheels_dir, n))
    zpath = os.path.join(out, "fullseye_subset.zip")
    n_mod = build_zip(zpath)
    sizes["fullseye_subset.zip"] = os.path.getsize(zpath)
    sizes["fullseye_subset_modules"] = n_mod
    shutil.copy2(a.page, os.path.join(out, "proof.html"))
    sizes["proof.html"] = os.path.getsize(a.page)
    sizes["total_bytes"] = sum(v for k, v in sizes.items() if k != "fullseye_subset_modules")
    with open(os.path.join(out, "sizes.json"), "w", encoding="utf-8") as f:
        json.dump(sizes, f, ensure_ascii=False, indent=1)
    print(json.dumps(sizes, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
