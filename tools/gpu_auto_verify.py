#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Check the adopted ops at full resolution: the sweep compares a thinned sample.

採用 op の倍率上位と無作為標本について、実寸の出力を間引かずに CPU と比べる。掃引の比較は
間引いた標本なので、間引きで見落とす差が無いかをここで見る。2 段に分け、CPU の出力を
ロックの外で作ってから、GPU の実行だけロックの中で行う。

    py tools/gpu_auto_verify.py cpu --top 20 --sample 20
    py tools/gpu_auto_verify.py gpu --gpu-lock <file>
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import pickle
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))


def pick_all(S):
    """許可リストの 3 枠(単独・常駐・パイプライン)のうち、まだ全画素照合していない op 全部。"""
    allow = json.loads((ROOT / "fullseye" / "data" / "gpu_auto_allow.json").read_text("utf-8"))
    listed = set(allow["ops"]) | set(allow["resident_ops"]) | set(allow.get("pipeline_ops", {}))
    jf = S.OUT / "verify.json"
    done = set(json.loads(jf.read_text("utf-8"))) if jf.exists() else set()
    sca, base = S.read_rows("scale"), S.read_rows("scale_cpu")
    return [(n, base[n]["t_cpu"]) for n in sorted(sca) if n in listed and n not in done
            and sca[n].get("status") == "measured" and base.get(n, {}).get("t_cpu")
            and base[n]["t_cpu"] < 45.0]


def pick(S, top, sample):
    """倍率 5 以上の op から上位 *top* 件と残りの無作為 *sample* 件。"""
    sca, base = S.read_rows("scale"), S.read_rows("scale_cpu")
    rows = []
    for n, r in sca.items():
        tc = base.get(n, {}).get("t_cpu")
        if r.get("status") == "measured" and r.get("t_gpu") and tc and tc / r["t_gpu"] >= S.MIN_RATIO:
            rows.append((tc / r["t_gpu"], n, tc))
    rows.sort(reverse=True)
    head = rows[:top]
    rest = rows[top:]
    random.Random(20261102).shuffle(rest)
    return [(n, tc) for _r, n, tc in head + rest[:sample] if tc < 45.0]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["cpu", "gpu"])
    ap.add_argument("--all", action="store_true", help="every allow-listed op not yet verified")
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--sample", type=int, default=20)
    ap.add_argument("--gpu-lock", default=os.environ.get("FULLSEYE_GPU_LOCK"))
    a = ap.parse_args()
    os.environ.setdefault("IMGEVOLVE_STRICT_BACKENDS", "1")
    import warnings
    warnings.simplefilter("ignore")
    import gpu_auto_sweep as S
    env = S.Env()
    np = env.np
    d = S.OUT / "verify"
    d.mkdir(exist_ok=True)
    os.chdir(S.OUT / "cwd")
    if a.cmd == "cpu":
        names = pick_all(S) if a.all else pick(S, a.top, a.sample)
        print(len(names), "ops", flush=True)
        for n, _tc in names:
            args, kw = env.probes(n)[0]
            sargs, skw = S.scale_args(env, n, args, kw, S.real_size)
            S._seed(np)
            c = env.fn(n)(*copy.deepcopy(sargs), **copy.deepcopy(skw))
            with (d / (n + ".pkl")).open("wb") as f:
                pickle.dump(c, f, protocol=4)
            print("cpu", n, flush=True)
        return 0
    # CPU 側を numpy 2 系で作った保存物を、numpy 1 系の loco 環境で読めるよう別名を張る
    import numpy
    if not hasattr(numpy, "_core"):
        import numpy.core as _nc
        sys.modules.setdefault("numpy._core", _nc)
        for _m in ("multiarray", "numeric", "_multiarray_umath"):
            try:
                sys.modules.setdefault("numpy._core." + _m, __import__("numpy.core." + _m, fromlist=["x"]))
            except ImportError:
                pass
    lock = S.GpuLock(a.gpu_lock, "gpu_auto_verify_%d" % os.getpid())
    if not lock.acquire(3000):
        print("GPU busy")
        return 4
    out = {}
    try:
        t0 = time.time()
        import gpu_shadow as G
        sh = G.get_shadow()
        ops_s = sh.load("ops")
        nary_s = {o.name: o.fn for o in sh.load("imgops_nary").build_nary()}
        cat_s = {c[0]: c[4] for c in sh.load("typed_catalog").catalog()}
        for p in sorted(d.glob("*.pkl")):
            n = p.stem
            if time.time() - t0 > 500:
                print("hold over; stopped", flush=True)
                break
            with p.open("rb") as f:
                c = pickle.load(f)
            args, kw = env.probes(n)[0]
            sargs, skw = S.scale_args(env, n, args, kw, S.real_size)
            fn = ops_s.RT.get(n) or nary_s.get(n) or cat_s.get(n)
            S._seed(np)
            try:
                g = G.to_cpu(fn(*G.to_gpu(sargs), **G.to_gpu(skw)))
                r = S.compare(c, g, np)
                out[n] = {"ok": bool(r["ok"]), "rel": r.get("rel"), "why": r.get("why")}
            except Exception as e:  # noqa: BLE001
                out[n] = {"ok": False, "why": repr(e)[:160]}
            print(n, out[n], flush=True)
            p.unlink()
    finally:
        lock.release()
    prev = {}
    jf = S.OUT / "verify.json"
    if jf.exists():
        prev = json.loads(jf.read_text(encoding="utf-8"))
    prev.update(out)
    jf.write_text(json.dumps(prev, indent=1), encoding="utf-8")
    print(sum(v["ok"] for v in prev.values()), "of", len(prev))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
