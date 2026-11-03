#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Compare three mechanical GPU methods on a stratified sample of operators.

機械的 GPU 化の方式を、同じ op 標本・同じ入力・同じ判定(``gpu_auto_sweep.compare``)で比べる。

* ``cupy_shadow``: :mod:`gpu_shadow` —— ソースを再実行し np/scipy を CuPy へ向ける。
* ``nep18``: 配列だけ CuPy にして本物の関数へ渡す(``__array_function__`` 任せ)。
* ``torch_shadow``: 同じ影の仕組みで np を ``array_api_compat.torch`` へ向ける。
  scipy の torch 版は無いので、``scipy.ndimage`` 等を使う op は例外になる。

    py tools/gpu_auto_method_compare.py --n 90 --out <json>
"""
from __future__ import annotations

import argparse
import collections
import copy
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))


def build_torch_shadow():
    """``gpu_shadow.ShadowImporter`` の np を torch の array-API 名前空間へ向けた版。"""
    import numpy as np
    import torch
    from scipy._lib.array_api_compat import torch as xp_torch

    import gpu_shadow as G

    class TorchNs:
        def __init__(self, base):
            self._b = base

        def __getattr__(self, name):
            if name in ("asarray", "array", "asanyarray"):
                def make(x, dtype=None, **k):
                    if torch.is_tensor(x):
                        return x if dtype is None else x.to(dtype=_dt(dtype))
                    arr = np.asarray(x, dtype=dtype)
                    return torch.as_tensor(arr, device="cuda")
                return make
            if name == "ndarray":
                return (torch.Tensor, np.ndarray)
            if hasattr(self._b, name):
                return getattr(self._b, name)
            return getattr(np, name)         # 定数と型は numpy のまま。関数は tensor で落ちる

    def _dt(dtype):
        return getattr(torch, np.dtype(dtype).name)

    class TorchShadow(G.ShadowImporter):
        def namespace(self, dotted):
            if dotted == "numpy":
                ns = self.spaces.get(dotted)
                if ns is None:
                    ns = self.spaces[dotted] = TorchNs(xp_torch)
                return ns
            import importlib
            return importlib.import_module(dotted)   # scipy は本物(tensor を渡せば落ちる)

        def _rebind(self, mod):
            ns = mod.__dict__
            for k, v in list(ns.items()):
                if getattr(v, "__name__", "") == "numpy":
                    ns[k] = self.namespace("numpy")
    return TorchShadow()


def to_torch(x, np, torch):
    if isinstance(x, np.ndarray) and x.dtype.kind in "biufc":
        return torch.as_tensor(x.copy(), device="cuda")
    if isinstance(x, (list, tuple)):
        return type(x)(to_torch(v, np, torch) for v in x)
    if isinstance(x, dict):
        return {k: to_torch(v, np, torch) for k, v in x.items()}
    return x


def from_torch(x, np, torch):
    if torch.is_tensor(x):
        return x.detach().cpu().numpy()
    if isinstance(x, (list, tuple)):
        return type(x)(from_torch(v, np, torch) for v in x)
    if isinstance(x, dict):
        return {k: from_torch(v, np, torch) for k, v in x.items()}
    return x


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=90)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    import os
    os.environ.setdefault("IMGEVOLVE_STRICT_BACKENDS", "1")
    import warnings
    warnings.simplefilter("ignore")
    import gpu_auto_sweep as S
    import gpu_shadow as G
    import torch
    env = S.Env()
    np = env.np
    cpu = S.read_rows("cpu")
    pool = [n for n, r in cpu.items() if r.get("status") == "ok"
            and not r.get("libs") and (r.get("t_small") or 9) < 1.0]
    wrap = [n for n, r in cpu.items() if r.get("status") == "ok" and r.get("libs")]
    rng = random.Random(20261102)
    rng.shuffle(pool)
    rng.shuffle(wrap)
    names = pool[:int(a.n * 0.85)] + wrap[:a.n - int(a.n * 0.85)]
    sh = G.get_shadow()
    ops_s = sh.load("ops")
    nary_s = {o.name: o.fn for o in sh.load("imgops_nary").build_nary()}
    cat_s = {c[0]: c[4] for c in sh.load("typed_catalog").catalog()}
    tsh = build_torch_shadow()
    t_ops = tsh.load("ops")
    t_nary = {o.name: o.fn for o in tsh.load("imgops_nary").build_nary()}
    t_cat = {c[0]: c[4] for c in tsh.load("typed_catalog").catalog()}

    def run_method(m, name, args, kw):
        if m == "cupy_shadow":
            f = ops_s.RT.get(name) or nary_s.get(name) or cat_s.get(name)
            return G.to_cpu(f(*G.to_gpu(copy.deepcopy(args)), **G.to_gpu(copy.deepcopy(kw))))
        if m == "nep18":
            return G.to_cpu(env.fn(name)(*G.to_gpu(copy.deepcopy(args)),
                                         **G.to_gpu(copy.deepcopy(kw))))
        f = t_ops.RT.get(name) or t_nary.get(name) or t_cat.get(name)
        return from_torch(f(*to_torch(copy.deepcopy(args), np, torch),
                            **to_torch(copy.deepcopy(kw), np, torch)), np, torch)

    tally = {m: collections.Counter() for m in ("cupy_shadow", "nep18", "torch_shadow")}
    why = {m: collections.Counter() for m in tally}
    rows = []
    for name in names:
        args, kw = env.probes(name)[0]
        S._seed(np)
        c = env.fn(name)(*copy.deepcopy(args), **copy.deepcopy(kw))
        row = {"name": name}
        for m in tally:
            S._seed(np)
            t0 = time.perf_counter()
            try:
                g = run_method(m, name, args, kw)
                r = S.compare(c, g, np)
                v = "match" if r["ok"] else "mismatch"
                if not r["ok"]:
                    why[m][(r["why"] or "")[:30]] += 1
            except Exception as e:  # noqa: BLE001
                v = "exception"
                why[m][S.classify_exc(e)] += 1
            tally[m][v] += 1
            row[m] = v
            row[m + "_s"] = round(time.perf_counter() - t0, 4)
        rows.append(row)
    res = {"n": len(names), "tally": {k: dict(v) for k, v in tally.items()},
           "why": {k: dict(v.most_common(10)) for k, v in why.items()}, "rows": rows,
           "cupy": __import__("cupy").__version__, "torch": torch.__version__,
           "numpy": np.__version__}
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("n", "tally", "why")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
