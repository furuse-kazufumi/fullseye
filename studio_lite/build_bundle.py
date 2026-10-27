# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""studio_lite/build_bundle.py — ブラウザ版 Studio-lite(v0)の配布物(dist)を **repo の外** に組む。

    py -3.11 studio_lite/build_bundle.py --pyodide-dir <pyodide npm の配布物> --wheels-dir <numpy/scipy/threadpoolctl の wheel> --out <dist>

dist の中身(外部 URL は一切読まない。http で配信する —— file:// では WebAssembly を fetch できない):

    index.html            … ページ(studio_lite/index.html の複製)
    i18n.json             … UI 文字列 8 言語(pocviewer.LANGS と同じ並び)
    ops_subset.json       … ブラウザで使える op の台帳(**実測**: Pyodide で走って CPython と 1 ULP 以内。
                             tools/probe_studio_web/compare_outputs.py --ops-json が書く。studio_lite/ops_subset.json の複製)
    pyodide/              … Pyodide 本体(版は pyodide-lock.json の info に書いてある)+ wheel
    fullseye_bundle.zip   … ``import api`` と ``studio``(描画入口)が読む repo 内モジュール + studio_lite/core.py + fullseye/data の JSON
    samples/coins.png, samples/blobs.png … 同梱サンプル(studio_assets/sample_images から)
    sizes.json            … 各部のバイト数
    serve.py              … 手元で配信する最小サーバ(``py -3.11 serve.py [port]``)

Pyodide の版は固定する(``PYODIDE_VERSION``)。配布物の版が違えば止める(黙って別の版を同梱しない)。
これは生成物ではない(dist は repo に入れない)。regen_all の表では NOT_A_GENERATOR。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

PYODIDE_VERSION = "314.0.7"           # 2026-10-25 に測った版(Python 3.14.2 / numpy 2.4.6 / scipy 1.18.0)
PYODIDE_FILES = ["pyodide.asm.wasm", "pyodide.asm.mjs", "pyodide.mjs", "pyodide.js", "python_stdlib.zip", "pyodide-lock.json"]
WHEELS = ("numpy-", "scipy-", "threadpoolctl-")
SAMPLES = ["coins.png", "blobs.png"]
SERVE_PY = '''"""Studio-lite の dist を手元で配信する(標準ライブラリだけ)。``py -3.11 serve.py [port]`` → http://127.0.0.1:<port>/"""
import http.server, os, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))
port = int(sys.argv[1]) if len(sys.argv) > 1 else 8766
http.server.ThreadingHTTPServer.allow_reuse_address = True
print("http://127.0.0.1:%d/  (Ctrl+C で止める)" % port)
http.server.ThreadingHTTPServer(("127.0.0.1", port), http.server.SimpleHTTPRequestHandler).serve_forever()
'''


def bundle_modules() -> list:
    """ページが読むモジュール: ``import api`` + ``studio``(描画入口)+ core が読むもの。"""
    import importlib
    cwd = ROOT.lower()
    # halcon_names_data / auto_specs_data は backends_auto が **data/*.json が無いときだけ** 読む同梱の
    # 代替(wheel と同じ事情)。repo では JSON が在るので import 時には読まれず、zip から漏れて
    # backends_auto の 25 op が黙って登録されなかった(2026-10-25 実測: ページ 325 / 台帳 350)。
    for m in ("api", "studio", "engine", "recipes", "param_specs", "imgio", "halcon_names_data", "auto_specs_data"):
        importlib.import_module(m)
    files = []
    for m in list(sys.modules.values()):
        f = getattr(m, "__file__", None)
        if f and os.path.isfile(f) and os.path.dirname(os.path.abspath(f)).lower().startswith(cwd):
            rel = os.path.relpath(os.path.abspath(f), ROOT).replace(os.sep, "/")
            if not rel.startswith(("tools/", "tests/", "studio_lite/")):
                files.append(rel)
    return sorted(set(files))


def build_zip(path: str) -> dict:
    mods = bundle_modules()
    n_data = 0
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel in mods:
            z.write(os.path.join(ROOT, rel), rel)
        z.write(os.path.join(HERE, "core.py"), "studio_lite/core.py")
        base = os.path.join(ROOT, "fullseye", "data")
        for n in sorted(os.listdir(base)):
            if n.endswith(".json"):
                z.write(os.path.join(base, n), "fullseye/data/" + n)
                n_data += 1
    return {"modules": len(mods), "data_json": n_data}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pyodide-dir", required=True)
    ap.add_argument("--wheels-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ops-json", default=os.path.join(HERE, "ops_subset.json"))
    a = ap.parse_args(argv)
    with open(os.path.join(a.pyodide_dir, "package.json"), encoding="utf-8") as f:
        ver = json.load(f).get("version")
    if ver != PYODIDE_VERSION:
        raise SystemExit("Pyodide の版が違う: 配布物 %s / 固定 %s(studio_lite/build_bundle.py の PYODIDE_VERSION)" % (ver, PYODIDE_VERSION))
    out = a.out
    os.makedirs(os.path.join(out, "pyodide"), exist_ok=True)
    os.makedirs(os.path.join(out, "samples"), exist_ok=True)
    sizes = {"pyodide_version": ver}
    for n in PYODIDE_FILES:
        src = os.path.join(a.pyodide_dir, n)
        if not os.path.exists(src):
            raise SystemExit("pyodide の配布物に %s が無い" % n)
        shutil.copy2(src, os.path.join(out, "pyodide", n))
        sizes["pyodide/" + n] = os.path.getsize(src)
    got = []
    for n in sorted(os.listdir(a.wheels_dir)):
        if n.endswith(".whl") and n.startswith(WHEELS):
            shutil.copy2(os.path.join(a.wheels_dir, n), os.path.join(out, "pyodide", n))
            sizes["pyodide/" + n] = os.path.getsize(os.path.join(a.wheels_dir, n))
            got.append(n)
    missing = [w for w in WHEELS if not any(g.startswith(w) for g in got)]
    if missing:
        raise SystemExit("wheel が足りない: %s(--wheels-dir %s)" % (missing, a.wheels_dir))
    zpath = os.path.join(out, "fullseye_bundle.zip")
    info = build_zip(zpath)
    sizes["fullseye_bundle.zip"] = os.path.getsize(zpath)
    sizes.update({"bundle_" + k: v for k, v in info.items()})
    for n in ("index.html", "i18n.json"):
        shutil.copy2(os.path.join(HERE, n), os.path.join(out, n))
        sizes[n] = os.path.getsize(os.path.join(HERE, n))
    if not os.path.exists(a.ops_json):
        raise SystemExit("ops_subset.json が無い(%s)。tools/probe_studio_web/compare_outputs.py --ops-json で作る" % a.ops_json)
    shutil.copy2(a.ops_json, os.path.join(out, "ops_subset.json"))
    sizes["ops_subset.json"] = os.path.getsize(a.ops_json)
    with open(a.ops_json, encoding="utf-8") as f:
        sizes["ops_in_subset"] = len(json.load(f)["ops"])
    for n in SAMPLES:
        src = os.path.join(ROOT, "studio_assets", "sample_images", n)
        shutil.copy2(src, os.path.join(out, "samples", n))
        sizes["samples/" + n] = os.path.getsize(src)
    with open(os.path.join(out, "serve.py"), "w", encoding="utf-8") as f:
        f.write(SERVE_PY)
    sizes["total_bytes"] = sum(v for k, v in sizes.items() if isinstance(v, int) and "/" in k or k in ("fullseye_bundle.zip", "index.html", "i18n.json", "ops_subset.json"))
    with open(os.path.join(out, "sizes.json"), "w", encoding="utf-8") as f:
        json.dump(sizes, f, ensure_ascii=False, indent=1)
    print(json.dumps(sizes, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
