# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Honest benchmark for the precision-union PoC (bitunion.py).

Reports, per representative array:
  * memory: union bytes vs dense uint8 and dense float32 (real packed size)
  * fidelity: max reconstruction error
  * bit histogram: what precision each tile actually needed (the audit)
  * speed: a chain of N affine ops then one materialise — union (O(#tiles) headers,
    codes untouched, decode once) vs dense (a*x+b every op).

Run: py -3.11 poc/bitunion_bench.py
"""
from __future__ import annotations

import time

import numpy as np

import bitunion as bu


def _bench_arrays():
    rng = np.random.default_rng(42)
    H, W = 256, 256
    yy, xx = np.mgrid[0:H, 0:W]
    smooth = (yy * 0.4 + xx * 0.3 + 30 * np.sin(xx * 0.02)).astype(np.float64)
    labels = rng.integers(0, 6, (H, W), dtype=np.int64)                 # 6 classes
    mask = (smooth > smooth.mean()).astype(np.int64)                    # binary
    # depth-map-like: smooth planes with a few sharp steps (piecewise flat regions)
    depth = np.zeros((H, W))
    depth[:128, :128] = 1.0 + 0.001 * xx[:128, :128]
    depth[128:, 128:] = 3.0 + 0.001 * yy[128:, 128:]
    depth[:128, 128:] = 2.0
    hdr = (1000.0 * np.exp(-((xx - 128) ** 2 + (yy - 128) ** 2) / 4000.0)).astype(np.float64)
    noise = rng.integers(0, 256, (H, W), dtype=np.int64)               # worst case
    photo = np.clip(smooth + rng.standard_normal((H, W)) * 12, 0, 255).astype(np.uint8)
    return {
        "smooth gradient (f64)": (smooth, 0.5),
        "label map / 6 classes": (labels, 0.0),
        "binary mask": (mask, 0.0),
        "depth map (piecewise)": (depth, 0.005),
        "HDR blob (f64)": (hdr, 1.0),
        "photo+noise (u8)": (photo, 0.0),
        "uniform noise (u8)": (noise, 0.0),
    }


def _fmt_bytes(n):
    return f"{n/1024:8.1f} KiB"


def memory_and_fidelity():
    print("=" * 92)
    print("MEMORY + FIDELITY  (tile=16)")
    print("-" * 92)
    print(f"{'array':<24}{'union':>12}{'/u8':>8}{'/f32':>8}{'maxerr':>12}   bit-histogram")
    print("-" * 92)
    for name, (arr, tol) in _bench_arrays().items():
        pu = bu.encode(arr, tile=16, tol=tol)
        u8 = pu.dense_nbytes(np.uint8)
        f32 = pu.dense_nbytes(np.float32)
        err = float(np.abs(pu.to_dense().astype(np.float64) - arr.astype(np.float64)).max())
        r8 = pu.nbytes / u8
        flag = "  <- LOSES vs u8" if r8 > 1.0 else ""
        print(f"{name:<24}{_fmt_bytes(pu.nbytes):>12}{r8:>8.2f}{pu.nbytes/f32:>8.2f}"
              f"{err:>12.4g}   {pu.bits_histogram()}{flag}")
    print("=" * 92)


def affine_chain_speed(n_ops=20, reps=50):
    print("\nSPEED: chain of {} affine ops then materialise once (median of {} reps)".format(n_ops, reps))
    print("-" * 92)
    arr, tol = _bench_arrays()["smooth gradient (f64)"]
    pu = bu.encode(arr, tile=16, tol=tol)
    base = pu.to_dense()                    # the array the union actually represents
    ops = [(1.0 + 0.01 * i, -0.5 * i) for i in range(n_ops)]

    def run_union():
        cur = pu
        for a, b in ops:
            cur = cur.scale_shift(a, b)     # O(#tiles): codes untouched
        return cur.to_dense()               # one decode

    def run_dense():
        # same starting array as the union (quantisation cost is accounted for in
        # the memory/fidelity table, not here); compare the op work fairly.
        cur = base.copy()
        for a, b in ops:
            cur = a * cur + b               # O(#pixels) every op
        return cur

    # correctness first
    assert np.allclose(run_union(), run_dense(), atol=1e-6)

    def timeit(f):
        ts = []
        for _ in range(reps):
            t0 = time.perf_counter(); f(); ts.append(time.perf_counter() - t0)
        return float(np.median(ts))

    tu, td = timeit(run_union), timeit(run_dense)
    ntiles = pu.headers.shape[0]
    npix = int(np.prod(pu.shape))
    print(f"union (headers O({ntiles} tiles) + 1 decode): {tu*1e3:7.3f} ms")
    print(f"dense (a*x+b over {npix} px, {n_ops}x)      : {td*1e3:7.3f} ms")
    print(f"speedup: {td/tu:5.2f}x   (grows with n_ops; the decode is paid once)")

    # headers-only cost (deferred, no materialise) — the true O(#tiles) part
    def run_union_lazy():
        cur = pu
        for a, b in ops:
            cur = cur.scale_shift(a, b)
        return cur
    tl = timeit(run_union_lazy)
    print(f"union deferred (no materialise)            : {tl*1e3:7.3f} ms  "
          f"({td/tl:6.1f}x vs dense; this is the O(#tiles) algebra alone)")
    print("=" * 92)


def threshold_speed(reps=50):
    print("\nSPEED: threshold on piecewise-flat depth map (one-sided tiles skip decode)")
    print("-" * 92)
    arr, tol = _bench_arrays()["depth map (piecewise)"]
    pu = bu.encode(arr, tile=16, tol=tol)
    dense = pu.to_dense()
    t = 1.5
    assert np.array_equal(pu.threshold(t), dense > t)

    def timeit(f):
        ts = []
        for _ in range(reps):
            t0 = time.perf_counter(); f(); ts.append(time.perf_counter() - t0)
        return float(np.median(ts))

    tu = timeit(lambda: pu.threshold(t))
    td = timeit(lambda: dense > t)
    print(f"union threshold (flat tiles O(1), py loop) : {tu*1e3:7.3f} ms")
    print(f"dense  (arr > t, one vectorised numpy op)  : {td*1e3:7.3f} ms")
    print(f"ratio: {tu/td:5.2f}x  -> union LOSES here. HONEST FINDING: dense threshold")
    print(f"       is already a single fully-vectorised pass (~memory-bandwidth bound);")
    print(f"       the code-space 'skip one-sided tiles' shortcut cannot beat it from a")
    print(f"       PYTHON per-tile loop. It would only pay off in a vectorised/compiled")
    print(f"       kernel, or when the input never materialises to a dense array at all.")
    print("=" * 92)


if __name__ == "__main__":
    memory_and_fidelity()
    affine_chain_speed()
    threshold_speed()
