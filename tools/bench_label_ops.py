# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""領域の解析の族(``accel_label``)を CPU の op と比べる: 一致・出力が定数でない・倍率(転送込み / 常駐)。

    FULLSEYE_GPU_LOCK=<共有ロックのパス> <GPU の venv の python> tools/bench_label_ops.py measure   # GPU(1 回 9.5 分まで)
    py -3.11 tools/gen_gpu_routes.py                                        # ログ -> fullseye/data/GPU_ACCEL_USE.json

台帳はこのファイルの :func:`build` が決め、書くのは ``tools/gen_gpu_routes.py``(regen_all の鎖)。

入力(1 辺 512 / 1024 / 2048、各 1 枚、``float64`` の 0/1):

* ``blobs``  — なだらかな雑音を中央値で切った領域(成分が多く、最大の成分は画像の大半を占める)
* ``coins``  — 大きい σ で切った 2 割の前景(数十個の丸い成分)
* ``spiral`` — 幅 1 画素・間 1 画素の渦巻き 1 本(ラベル付けの反復がいちばん長くなる形)
* ``scene``  — ``tools/bench_gpu_crossover.py`` の検査画像を 0.5 で切ったもの(``region`` の掃引と同じ入力)

測るもの(1 op 1 入力 1 辺ごとに 1 行):

* ``cpu_s``      — 登録簿の CPU の op(``ops.RT``)。
* ``gpu_s``      — ホストの ``float64`` から GPU へ送り、計算し、答えを戻すまで(``accel.run_batch`` と同じ道)。
* ``resident_s`` — 入力が GPU に載っている状態での計算だけ(鎖の途中の段)。答えが領域なら GPU に残す
  (次の段が使う)、特徴なら数を戻すところまで。
* ``ok``         — 答えが CPU と一致したか(領域は画素ごとに完全一致、特徴は相対 1e-9)。つまみ 3 点で見る。

採用の門(:func:`build`、全入力の 2048 の点で): 全点で一致・出力が入力で変わる(定数でない)ことが前提。
転送込みの倍率の最小が 5 倍以上なら ``use="single"``、常駐の倍率の最小が 1 倍以上なら ``use="pipeline"``
(隣も GPU の段のときだけ GPU)、どちらでもなければ不採用(理由を台帳に残す)。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "docs" / "perf" / "logs" / "label" / "label_ops.jsonl"
#: 共有 GPU のロックのパス。環境変数 FULLSEYE_GPU_LOCK(``tools/bench_gpu_crossover.py`` と同じ)。未指定なら測らない。
LOCK_ENV = "FULLSEYE_GPU_LOCK"
SIDES = (512, 1024, 2048)
KNOBS = ((0.5, 0.5), (0.1, 0.9), (0.9, 0.2))
GATE_SIDE = 2048
SINGLE_MIN = 5.0
PIPELINE_MIN = 1.0
LIMIT_S = 570.0


# ---- 入力 -------------------------------------------------------------------------------------
def spiral(side: int) -> np.ndarray:
    """幅 1・間 1 の矩形の渦巻き 1 本(8 連結でも 4 連結でも 1 成分)。"""
    m = np.zeros((side, side))
    y, x, d = 0, 0, 0
    moves = ((0, 1), (1, 0), (0, -1), (-1, 0))
    m[0, 0] = 1
    lengths = [side - 1, side - 1, side - 1]          # 右・下・左の外周、以後 2 本ずつ 2 短く
    k = side - 3
    while k > 0:
        lengths += [k, k]
        k -= 2
    for length in lengths:
        dy, dx = moves[d]
        for _ in range(length):
            y, x = y + dy, x + dx
            m[y, x] = 1
        d = (d + 1) % 4
    return m


def fixtures(side: int) -> dict:
    from scipy import ndimage
    sys.path.insert(0, str(ROOT))
    from tools.bench_gpu_crossover import _image
    r = np.random.default_rng(1)
    g = ndimage.gaussian_filter(r.random((side, side)), 2.0)
    blobs = (g > np.quantile(g, 0.5)).astype(np.float64)
    r = np.random.default_rng(2)
    g = ndimage.gaussian_filter(r.random((side, side)), 12.0 * side / 2048)
    coins = (g > np.quantile(g, 0.8)).astype(np.float64)
    scene = (_image(side, 0) > 0.5).astype(np.float64)
    return {"blobs": blobs, "coins": coins, "spiral": spiral(side), "scene": scene}


# ---- 比較 -------------------------------------------------------------------------------------
def same(got, ref, reducer: bool) -> bool:
    if reducer:
        g = np.asarray(got, np.float64)
        r = np.asarray(ref, np.float64)
        return g.shape == r.shape and bool(np.allclose(g, r, rtol=1e-9, atol=1e-12))
    return bool(np.array_equal(np.asarray(got, np.float64), np.clip(np.asarray(ref, np.float64), 0, 1)))


def _median(fn, sync, reps: int) -> float:
    fn()
    sync()
    ws = []
    for _ in range(reps):
        t0 = time.perf_counter()
        fn()
        sync()
        ws.append(time.perf_counter() - t0)
    return float(np.median(ws))


def _lock_path() -> Path:
    """共有ロックのパス(``FULLSEYE_GPU_LOCK``)。無ければ fail-closed で止める(ロックなしに GPU を使わない)。"""
    raw = os.environ.get(LOCK_ENV, "").strip()
    if not raw:
        raise SystemExit("%s が無い: 共有ロックを指定せずに GPU を使わない" % LOCK_ENV)
    return Path(raw)


def _acquire(owner: str):
    import subprocess
    LOCK = _lock_path()
    if "unrealeditor" in subprocess.run(["tasklist"], capture_output=True, text=True,
                                        errors="replace").stdout.lower():
        raise SystemExit("UnrealEditor is running: the GPU is not used")
    fd = os.open(str(LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    with os.fdopen(fd, "w") as f:
        f.write("%s %s pid=%d\n" % (owner, time.strftime("%Y-%m-%dT%H:%M:%S"), os.getpid()))

    def release():
        try:
            if LOCK.read_text().startswith(owner):
                LOCK.unlink()
        except OSError:
            pass

    def stop():
        release()
        os._exit(43)

    dog = threading.Timer(LIMIT_S, stop)
    dog.daemon = True
    dog.start()
    return release


def cmd_measure(ns) -> int:
    sys.path.insert(0, str(ROOT))
    release = _acquire("bench_label_ops")
    try:
        import warnings
        warnings.filterwarnings("ignore")
        import torch
        import accel_label as AL
        import ops
        sync = torch.cuda.synchronize
        table = AL.table()
        only = set(ns.ops.split(",")) if ns.ops else None
        LOG.parent.mkdir(parents=True, exist_ok=True)
        done = set()
        if LOG.exists():
            for line in LOG.read_text(encoding="utf-8").splitlines():
                r = json.loads(line)
                done.add((r["op"], r["fixture"], r["side"]))
        t_start = time.time()
        for side in SIDES:
            fx = fixtures(side)
            for key, (fn, core, _h) in table.items():
                if only and core not in only:
                    continue
                reducer = key in AL.REDUCERS
                for fname, f in fx.items():
                    if (core, fname, side) in done:
                        continue
                    if time.time() - t_start > LIMIT_S - 150:      # 1 点に 1 分以上かかる op がある
                        print("window used up; run again to continue")
                        return 0
                    ok = True
                    outs = []
                    for a, b in KNOBS:
                        ref = ops.RT[core](f.copy(), a, b)
                        t = torch.as_tensor(f[None, None].astype(np.float32), device="cuda")
                        got = fn(t, a, b, "cuda")
                        got = got[0] if reducer else got[0, 0].cpu().numpy()
                        ok = ok and same(got, ref, reducer)
                        outs.append(np.asarray(ref, np.float64).ravel())
                    a, b = KNOBS[0]
                    cpu = _median(lambda: ops.RT[core](f, a, b), lambda: None, 3)

                    def full():
                        t = torch.as_tensor(f[None, None].astype(np.float32), device="cuda")
                        out = fn(t, a, b, "cuda")
                        if not reducer:
                            out.detach().cpu().numpy()

                    t_res = torch.as_tensor(f[None, None].astype(np.float32), device="cuda")
                    gpu = _median(full, sync, 5)
                    res = _median(lambda: fn(t_res, a, b, "cuda"), sync, 5)
                    rec = {"op": core, "accel": key, "fixture": fname, "side": side, "reducer": reducer,
                           "ok": ok, "out_sig": float(np.sum([o.sum() for o in outs[:1]])),
                           "cpu_s": cpu, "gpu_s": gpu, "resident_s": res, "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                           "env": {"torch": torch.__version__, "device": torch.cuda.get_device_name(0)}}
                    with LOG.open("a", encoding="utf-8") as fh:
                        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    print("%-24s %-6s %4d ok=%d cpu=%.2fms gpu=%.2fms x%.1f res=%.2fms x%.1f" % (
                        core, fname, side, ok, cpu * 1e3, gpu * 1e3, cpu / gpu, res * 1e3, cpu / res), flush=True)
        return 0
    finally:
        release()


# ---- 台帳 -------------------------------------------------------------------------------------
def build(log: Path = LOG) -> dict:
    rows = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines() if x.strip()] if log.exists() else []
    by_op: dict = {}
    for r in rows:
        by_op.setdefault(r["op"], []).append(r)
    out = {}
    for op in sorted(by_op):
        rs = by_op[op]
        gate = [r for r in rs if r["side"] == GATE_SIDE]
        ok = all(r["ok"] for r in rs)
        sigs = {round(r["out_sig"], 6) for r in rs}
        nonconst = len(sigs) > 1
        single = min((r["cpu_s"] / r["gpu_s"] for r in gate), default=None)
        resident = min((r["cpu_s"] / r["resident_s"] for r in gate), default=None)
        if not gate:
            use, why = None, "not_measured_at_%d" % GATE_SIDE
        elif not ok:
            use, why = None, "mismatch"
        elif not nonconst:
            use, why = None, "constant_output"
        elif single >= SINGLE_MIN:
            use, why = "single", None
        elif resident >= PIPELINE_MIN:
            use, why = "pipeline", None
        else:
            use, why = None, "slower_than_cpu_even_resident"
        worst = min(gate, key=lambda r: r["cpu_s"] / r["resident_s"])["fixture"] if gate else None
        out[op] = {"use": use, "rejected": why, "ratio_single": round(single, 3) if single else None,
                   "ratio_resident": round(resident, 3) if resident else None, "worst_fixture": worst,
                   "elems": GATE_SIDE * GATE_SIDE, "points": len(rs), "ok": ok, "nonconst": nonconst}
    return {"generated_by": "tools/bench_label_ops.py", "log": "docs/perf/logs/label/label_ops.jsonl",
            "gate": {"side": GATE_SIDE, "single_min": SINGLE_MIN, "pipeline_min": PIPELINE_MIN,
                     "parity": "region: pixel-exact; feature: rtol 1e-9", "knobs": [list(k) for k in KNOBS]},
            "ops": out}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("measure")
    p.add_argument("--ops", default="")
    p.set_defaults(fn=cmd_measure)
    ns = ap.parse_args(argv)
    return ns.fn(ns)


if __name__ == "__main__":
    raise SystemExit(main())
