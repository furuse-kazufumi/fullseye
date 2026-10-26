# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""探針(probe): 全 op を「どの外部依存で動くか」で棚卸しする(Studio をブラウザで動かす可否の実測用)。

    py -3.11 tools/probe_studio_web/op_inventory.py --out <repo の外のディレクトリ>

op の 3 層(registry / n-ary / 型付き台帳)を全部数え、各 op の実装関数が住むモジュールの
import を AST で読む。モジュール先頭の素の import(無ければモジュール自体が読めない)、
try で守られた import、関数の中の遅延 import を区別し、さらに**そのモジュールが読む repo 内の
モジュール**の先頭 import も辿る(A が B を読み、B が先頭で torch を読めば A も読めない)。

分類は Pyodide(ブラウザの CPython)に**同梱されている**かで切る —— numpy / scipy / cv2 /
skimage / imageio / Pillow / PyWavelets / networkx / sympy / h5py は同梱、torch / kornia /
mitsuba / mujoco / mediapipe / SimpleITK / PySide6 は無い。生成物ではなく実測で、出力は指定先へ。
"""
from __future__ import annotations

import argparse
import ast
import collections
import importlib
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

#: Pyodide 314.0.7 の pyodide-lock.json に載っている(= ブラウザで pip 無しに読める)配布物。
#: import 名 -> 配布名。ここに無い第三者 import は「ブラウザで動かない」側に数える。
PYODIDE_AVAILABLE = {
    "numpy": "numpy", "scipy": "scipy", "cv2": "opencv-python", "skimage": "scikit-image",
    "imageio": "imageio", "PIL": "pillow", "pywt": "pywavelets", "networkx": "networkx",
    "sympy": "sympy", "h5py": "h5py", "threadpoolctl": "threadpoolctl", "matplotlib": "matplotlib",
    "sklearn": "scikit-learn", "pandas": "pandas", "yaml": "pyyaml", "lxml": "lxml",
    "shapely": "shapely", "tifffile": "tifffile", "openpyxl": "openpyxl",
    "lazy_loader": "lazy_loader", "packaging": "packaging", "pydantic": "pydantic",
    "regex": "regex", "msgpack": "msgpack", "pyparsing": "pyparsing", "mpmath": "mpmath",
    "jsonschema": "jsonschema", "certifi": "certifi", "requests": "requests", "six": "six", "attr": "attrs",
}

#: 分類の優先順(重い方が勝つ)。
CLASS_ORDER = ["torch", "other_heavy", "cv2", "skimage", "imageio_pil", "scipy", "numpy_only", "pure_python"]


def _stdlib_names() -> set:
    names = set(sys.stdlib_module_names)
    names |= {"__future__", "typing_extensions"}
    return names


STDLIB = _stdlib_names()


def _local_modules() -> set:
    out = set()
    for n in os.listdir(ROOT):
        if n.endswith(".py"):
            out.add(n[:-3])
        elif os.path.isdir(os.path.join(ROOT, n)) and os.path.exists(os.path.join(ROOT, n, "__init__.py")):
            out.add(n)
    return out


LOCAL = _local_modules()


class _ImportWalker(ast.NodeVisitor):
    """モジュールの import を 3 種に分ける: top(素の先頭) / guarded(try の中) / lazy(関数・クラスの中)。"""

    def __init__(self):
        self.top, self.guarded, self.lazy = set(), set(), set()
        self._depth_fn = 0
        self._depth_try = 0

    def _add(self, root):
        if self._depth_fn:
            self.lazy.add(root)
        elif self._depth_try:
            self.guarded.add(root)
        else:
            self.top.add(root)

    def visit_Import(self, node):
        for a in node.names:
            self._add(a.name.split(".")[0])

    def visit_ImportFrom(self, node):
        if node.level == 0 and node.module:
            self._add(node.module.split(".")[0])

    def visit_FunctionDef(self, node):
        self._depth_fn += 1
        self.generic_visit(node)
        self._depth_fn -= 1

    visit_AsyncFunctionDef = visit_FunctionDef
    visit_Lambda = visit_FunctionDef

    def visit_Try(self, node):
        self._depth_try += 1
        self.generic_visit(node)
        self._depth_try -= 1

    visit_TryStar = visit_Try


_CACHE: dict = {}


def module_imports(mod: str) -> dict:
    """repo 直下の ``<mod>.py``(または package)の import 3 種。見つからなければ空。"""
    if mod in _CACHE:
        return _CACHE[mod]
    path = os.path.join(ROOT, mod + ".py")
    if not os.path.exists(path):
        path = os.path.join(ROOT, mod, "__init__.py")
    res = {"top": set(), "guarded": set(), "lazy": set()}
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                tree = ast.parse(f.read())
            w = _ImportWalker()
            w.visit(tree)
            res = {"top": w.top, "guarded": w.guarded, "lazy": w.lazy}
        except SyntaxError:
            pass
    _CACHE[mod] = res
    return res


def third_party(names) -> set:
    return {n for n in names if n not in STDLIB and n not in LOCAL and not n.startswith("_")}


def hard_closure(mod: str) -> tuple[set, set]:
    """モジュールを読む時に**必ず**走る import の閉包: (第三者 import, 辿った repo 内モジュール)。"""
    seen, todo, third = set(), [mod], set()
    while todo:
        m = todo.pop()
        if m in seen:
            continue
        seen.add(m)
        imp = module_imports(m)
        third |= third_party(imp["top"])
        for n in imp["top"]:
            if n in LOCAL and n not in seen:
                todo.append(n)
    return third, seen


def classify(third: set) -> str:
    if "torch" in third or "kornia" in third:
        return "torch"
    if any(t not in PYODIDE_AVAILABLE for t in third):
        return "other_heavy"
    if "cv2" in third:
        return "cv2"
    if "skimage" in third:
        return "skimage"
    if third & {"imageio", "PIL", "tifffile"}:
        return "imageio_pil"
    if "scipy" in third:
        return "scipy"
    if "numpy" in third:
        return "numpy_only"
    return "pure_python"


def unwrap(fn):
    n = 0
    while hasattr(fn, "__wrapped__") and n < 12:
        fn = fn.__wrapped__
        n += 1
    return fn


def fn_module(fn):
    f = unwrap(fn)
    m = getattr(f, "__module__", None)
    if m is None and hasattr(f, "func"):          # functools.partial
        m = getattr(unwrap(f.func), "__module__", None)
    return m


def collect() -> list:
    import api
    import opassist
    import ops
    rows = []
    for o in ops.REGISTRY:
        rows.append({"name": o.name, "tier": "registry", "ledger": "ops", "in_sort": o.in_sort,
                     "out_sort": o.out_sort, "module": fn_module(o.fn)})
    for o in {id(o): o for o in api._nary_by_name().values()}.values():
        rows.append({"name": o.name, "tier": "nary", "ledger": "nary", "in_sort": o.in_sorts[0],
                     "out_sort": o.out_sort, "module": fn_module(o.fn)})
    seen = {r["name"] for r in rows}
    for mod_name, table in opassist._LEDGERS:
        entries = getattr(importlib.import_module(mod_name), table)
        for name, info in entries.items():
            if name in seen:
                continue
            seen.add(name)
            f = info.get("func")
            m = fn_module(f) if f is not None else info.get("module")
            if m in (None, "builtins"):
                m = info.get("module") or mod_name
            ins = list(info.get("in") or [])
            rows.append({"name": name, "tier": "ledger", "ledger": mod_name, "in_sort": ins[0] if ins else None,
                         "out_sort": info.get("out"), "module": m})
    return rows


THREE_D = {"match3d", "volops", "render3d", "meshres", "pcseg", "mesh", "pointcloud", "registration",
           "ppf", "terrain", "stereo", "annotate3d"}


def annotate(rows: list) -> None:
    for r in rows:
        m = r["module"] or "?"
        hard, chain = hard_closure(m)
        imp = module_imports(m)
        soft = third_party(imp["guarded"] | imp["lazy"])
        r["hard_imports"] = sorted(hard)
        r["soft_imports"] = sorted(soft)
        r["class_hard"] = classify(hard)              # モジュールが読めるか(import 時)
        r["class_all"] = classify(hard | soft)        # op を呼んだ時まで含めて
        r["pyodide_importable"] = all(t in PYODIDE_AVAILABLE for t in hard)
        r["pyodide_runnable_by_imports"] = all(t in PYODIDE_AVAILABLE for t in (hard | soft))
        r["dim"] = "3d" if (r["ledger"] == "ops3d" or r["module"] in THREE_D) else "2d_or_other"


def summarise(rows: list) -> dict:
    def pct(n, d):
        return round(100.0 * n / d, 1) if d else 0.0
    out = {"total": len(rows)}
    for tier in ("registry", "nary", "ledger", "3d", "ALL"):
        if tier == "ALL":
            sub = rows
        elif tier == "3d":
            sub = [r for r in rows if r["dim"] == "3d"]
        else:
            sub = [r for r in rows if r["tier"] == tier]
        n = len(sub)
        c_hard = collections.Counter(r["class_hard"] for r in sub)
        c_all = collections.Counter(r["class_all"] for r in sub)
        imp_ok = sum(r["pyodide_importable"] for r in sub)
        run_ok = sum(r["pyodide_runnable_by_imports"] for r in sub)
        out[tier] = {
            "n": n,
            "class_by_module_import": {k: [c_hard.get(k, 0), pct(c_hard.get(k, 0), n)] for k in CLASS_ORDER},
            "class_including_lazy": {k: [c_all.get(k, 0), pct(c_all.get(k, 0), n)] for k in CLASS_ORDER},
            "pyodide_importable": [imp_ok, pct(imp_ok, n)],
            "pyodide_runnable_by_imports": [run_ok, pct(run_ok, n)],
        }
    blockers = collections.Counter()
    for r in rows:
        for t in set(r["hard_imports"] + r["soft_imports"]):
            if t not in PYODIDE_AVAILABLE:
                blockers[t] += 1
    out["blocking_imports_op_count"] = blockers.most_common()
    mods = collections.Counter(r["module"] for r in rows)
    out["modules"] = len(mods)
    out["modules_not_pyodide_importable"] = sorted({str(r["module"]) for r in rows if not r["pyodide_importable"]})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="結果を書くディレクトリ(repo の外)")
    a = ap.parse_args(argv)
    t = time.perf_counter()
    rows = collect()
    annotate(rows)
    s = summarise(rows)
    s["seconds"] = round(time.perf_counter() - t, 2)
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "op_inventory_rows.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=0)
    with open(os.path.join(a.out, "op_inventory_summary.json"), "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in s.items() if k != "modules_not_pyodide_importable"}, ensure_ascii=False, indent=1))
    print("modules_not_pyodide_importable:", s["modules_not_pyodide_importable"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
