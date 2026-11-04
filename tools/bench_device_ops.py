#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Measure ops that carry their own ``device=`` argument (torch-native GPU paths).

掃引(``tools/gpu_auto_sweep.py``)の shim は numpy / scipy を CuPy に向けるだけで、torch の
``device`` 引数は変えられない。``edt_jfa`` のように最初から torch で書かれ ``device="cuda"`` で
GPU に載る op は、掃引では両側とも torch の CPU で走り「1 倍前後」と出ていた(2026-11-03 発見)。
ここでは op 自身の ``device`` を切り替えて測る。

* 入力 = 掃引と同じ構造のある探針(``op_probe``)を実寸へ(``scale_args``。点群は 2**14 点)。
* CPU = 登録経路そのもの(``device="cpu"``)。GPU = ``device="cuda"``、入力は numpy のまま渡し
  出力を numpy へ戻すまで(転送込み、``torch.cuda.synchronize()`` の後に時計を読む)。
  準備運転 1 回、CPU 2 回・GPU 3 回の最小値。
* 一致 = 掃引と同じ ``compare``(内部差が振れ幅の 5e-3 未満、端 4 画素は比べない)。出力が定数なら
  判定不能。採用 = 一致 かつ 転送込み 5.0 倍以上(掃引と同じ門)。
* GPU は ``--gpu-lock`` のロックの中だけで使う。結果は ``out/device_ops/rows.jsonl`` に追記。

    <GPU の venv の python> tools/bench_device_ops.py run --names <file> --gpu-lock <ロックファイル>
    py -3.11 tools/bench_device_ops.py report
"""
from __future__ import annotations

import argparse
import collections
import copy
import inspect
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

OUT = ROOT / "out" / "device_ops"


def _to_np(x, np):
    """torch tensor を含む出力を numpy へ(dict / list / tuple は中まで)。"""
    if hasattr(x, "detach") and hasattr(x, "cpu"):
        return x.detach().cpu().numpy()
    if isinstance(x, dict):
        return {k: _to_np(v, np) for k, v in x.items()}
    if isinstance(x, list):
        return [_to_np(v, np) for v in x]
    if isinstance(x, tuple) and not hasattr(x, "_fields"):
        return tuple(_to_np(v, np) for v in x)
    return x


def _accepts_device(fn) -> bool:
    try:
        return "device" in inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return False


def _impl(name):
    """op 名 → ``device`` 引数を持つ実装関数(台帳の包みではなく元の関数)。"""
    import importlib
    import api
    op = api.find_op(name)
    fn = getattr(op, "fn", None) if op is not None else None
    if fn is not None and _accepts_device(fn):
        return fn
    for mod in ("match3d", "feat_shot", "feat_fpfh", "feat_harris", "feat_spin", "fuse3d"):
        m = importlib.import_module(mod)
        f = getattr(m, name, None)
        if f is not None and _accepts_device(f):
            return f
    return None


def measure(name, S, env, torch) -> dict:
    np = env.np
    row = {"name": name}
    fn = _impl(name)
    if fn is None:
        return dict(row, status="no_device_impl")
    try:
        args, kw = env.probes(name)[0]
    except Exception as e:  # noqa: BLE001
        return dict(row, status="no_probe", err=str(e)[:160])
    sc = S.scale_args(env, name, args, kw, S.real_size)
    if sc is None:
        sargs, skw, row["scaled"] = args, kw, False
    else:
        (sargs, skw), row["scaled"] = sc, True
    row["elems"] = S.nelem(sargs, np)

    def run(dev):
        S._seed(np)
        torch.manual_seed(0)
        out = fn(*copy.deepcopy(sargs), **dict(copy.deepcopy(skw), device=dev))
        out = _to_np(out, np)
        if dev == "cuda":
            torch.cuda.synchronize()
        return out

    try:
        c = run("cpu")
        t_cpu = []
        for _ in range(2):
            t0 = time.perf_counter()
            run("cpu")
            t_cpu.append(time.perf_counter() - t0)
    except Exception as e:  # noqa: BLE001
        return dict(row, status="cpu_exception", err=repr(e)[:200])
    try:
        run("cuda")                      # 準備運転(カーネルの読み込み)
        g = None
        t_gpu = []
        for _ in range(3):
            torch.cuda.synchronize()
            t0 = time.perf_counter()
            g = run("cuda")
            t_gpu.append(time.perf_counter() - t0)
    except Exception as e:  # noqa: BLE001
        return dict(row, status="gpu_exception", err=repr(e)[:200])
    r = S.compare(c, g, np)
    row.update(t_cpu=min(t_cpu), t_gpu=min(t_gpu), ratio=min(t_cpu) / max(min(t_gpu), 1e-9),
               ok=bool(r.get("ok")), rel=r.get("rel"), why=r.get("why"),
               nonconst=bool(r.get("nonconst")))
    row["status"] = "measured" if row["ok"] else "mismatch"
    return row


def cmd_one(a) -> int:
    """1 op を測って JSON 1 行を標準出力へ(親が時間の上限つきで呼ぶ。ロックは親が持つ)。"""
    import torch
    import gpu_auto_sweep as S
    env = S.Env()
    row = measure(a.name, S, env, torch)
    print("ROW " + json.dumps(row, ensure_ascii=False, default=str), flush=True)
    return 0


def _run_child(name: str, timeout: float) -> dict:
    """1 op を子プロセスで測る。*timeout* 秒を超えたら打ち切って ``timeout`` と記録する。

    2026-11-03: ``match_chamfer_3d`` の CPU 側(2**14 点の全点対)が 94 分 CPU 24.5 時間を使って
    返らず、その間 GPU ロックを握り続けた(10 分の規則違反)。1 op ごとの上限で防ぐ。
    """
    import subprocess
    cmd = [sys.executable, str(Path(__file__).resolve()), "one", "--name", name]
    try:
        cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"name": name, "status": "timeout", "timeout_s": timeout}
    for ln in cp.stdout.splitlines():
        if ln.startswith("ROW "):
            return json.loads(ln[4:])
    return {"name": name, "status": "child_failed", "rc": cp.returncode,
            "err": (cp.stderr or "")[-300:]}


def cmd_run(a) -> int:
    import torch
    import gpu_auto_sweep as S
    if not torch.cuda.is_available():
        print("CUDA not available")
        return 3
    names = [ln.strip() for ln in Path(a.names).read_text(encoding="utf-8").splitlines() if ln.strip()]
    OUT.mkdir(parents=True, exist_ok=True)
    done = set()
    rows_f = OUT / "rows.jsonl"
    if rows_f.exists():
        done = {json.loads(ln)["name"] for ln in rows_f.read_text(encoding="utf-8").splitlines() if ln.strip()}
    todo = [n for n in names if n not in done]
    lock = S.GpuLock(a.gpu_lock, "bench_device_ops_%d" % os.getpid())
    if not lock.acquire(3000):
        print("GPU busy")
        return 4
    t_start = time.time()
    try:
        for n in todo:
            if time.time() - t_start > a.hold:
                print("hold over; stopped (run again to continue)", flush=True)
                break
            left = a.hold - (time.time() - t_start)
            row = _run_child(n, timeout=max(30.0, min(a.op_timeout, left)))
            with rows_f.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
            print(n, row.get("status"), "x%.1f" % row["ratio"] if "ratio" in row else "", flush=True)
    finally:
        lock.release()
    return 0


def cmd_report(_a) -> int:
    rows_f = OUT / "rows.jsonl"
    rows = {}
    for ln in rows_f.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            r = json.loads(ln)
            rows[r["name"]] = r
    cnt = collections.Counter()
    for r in rows.values():
        if r.get("status") == "measured":
            if r.get("nonconst") is False:
                k = "vacuous"
            elif r["ratio"] >= 5.0:
                k = "adopted"
            elif r["ratio"] >= 1.0:
                k = "faster_1_5"
            else:
                k = "slower"
        else:
            k = r.get("status")
        cnt[k] += 1
        r["class"] = k
    print(dict(cnt))
    for r in sorted(rows.values(), key=lambda r: -(r.get("ratio") or 0)):
        print("%-26s %-12s %s %s" % (r["name"], r["class"],
                                     "x%.1f cpu %.3fs gpu %.4fs" % (r["ratio"], r["t_cpu"], r["t_gpu"])
                                     if "ratio" in r else "", r.get("why") or r.get("err") or ""))
    (OUT / "summary.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1, default=str),
                                      encoding="utf-8")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["run", "report", "one"])
    ap.add_argument("--name")
    ap.add_argument("--op-timeout", type=float, default=180.0, help="seconds per op (child process)")
    ap.add_argument("--names")
    ap.add_argument("--gpu-lock", default=os.environ.get("FULLSEYE_GPU_LOCK"))
    ap.add_argument("--hold", type=float, default=480.0, help="seconds per lock hold")
    a = ap.parse_args(argv)
    if a.cmd == "one":
        return cmd_one(a)
    return cmd_run(a) if a.cmd == "run" else cmd_report(a)


if __name__ == "__main__":
    raise SystemExit(main())
