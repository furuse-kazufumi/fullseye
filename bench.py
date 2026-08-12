"""Throughput benchmark — CPU baseline vs batched backend (GPU-ready).

Establishes the null (feedback_beat_the_null): the per-image scipy/OpenCV loop is
the baseline. The batched torch backend (accel.py) is timed on the chosen device.
On CPU, batching + fused kernels may or may not beat scipy — measured, not assumed.
On the user's RTX 5090 (`--device cuda`) the batch runs on the GPU; that number is
measured there, never claimed here.

    py -3.11 bench.py                       # CPU: images/sec baseline vs batch
    py -3.11 bench.py --n 400 --size 256    # bigger workload
    py -3.11 bench.py --device cuda         # on a CUDA box: GPU throughput
"""
from __future__ import annotations

import argparse
import os
import time

import numpy as np

import accel
import ops

HERE = os.path.dirname(os.path.abspath(__file__))


def _timed(fn, reps=3):
    fn()                                     # warmup
    best = 1e18
    for _ in range(reps):
        t0 = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - t0)
    return best


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--size", type=int, default=256)
    ap.add_argument("--device", default="cpu")
    a = ap.parse_args()

    if not accel._HAS_TORCH:
        print("torch not available — cannot benchmark the batch backend")
        return 1
    import torch
    dev = a.device if (a.device == "cpu" or torch.cuda.is_available()) else "cpu"
    note = "" if dev == a.device else "  (CUDA unavailable here -> CPU; run on the RTX 5090 for GPU)"

    rng = np.random.default_rng(0)
    imgs = [np.clip(rng.random((a.size, a.size)), 0, 1) for _ in range(a.n)]

    print("throughput: %d imgs @ %dx%d | device=%s | torch threads=%d%s"
          % (a.n, a.size, a.size, dev, torch.get_num_threads(), note))
    print("  %-20s %12s %12s %9s" % ("op", "baseline i/s", "batch i/s", "speedup"))
    tot_base = tot_batch = 0.0
    for name, (fn, core_name, halcon) in accel.ACCEL.items():
        rt = ops.RT[core_name]

        def base():
            for im in imgs:
                rt(im, 0.5, 0.4)

        def batch():
            accel.run_batch(name, imgs, 0.5, 0.4, dev)

        tb = _timed(base)
        ta = _timed(batch)
        base_ips, batch_ips = a.n / tb, a.n / ta
        tot_base += tb
        tot_batch += ta
        print("  %-20s %12.0f %12.0f %8.2fx" % (name, base_ips, batch_ips, base_ips and batch_ips / base_ips))
    print("  %-20s %12.0f %12.0f %8.2fx  (aggregate)"
          % ("TOTAL", a.n * len(accel.ACCEL) / tot_base, a.n * len(accel.ACCEL) / tot_batch,
             tot_base / tot_batch if tot_batch else 0))
    print("honest: CPU numbers measured here; GPU speedup is measured on a CUDA device"
          " (batch backend is device-agnostic).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
