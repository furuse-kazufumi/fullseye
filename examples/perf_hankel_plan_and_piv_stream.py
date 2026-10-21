# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Hankel核の再利用とPIV/packed pixelのピークメモリを実測する。"""
import os
import sys
import time
import tracemalloc

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

import examplefig
import fullseye as fs
import pivops


def _median_seconds(call, repeats=3):
    values = []
    for _ in range(repeats):
        start = time.perf_counter()
        call()
        values.append(time.perf_counter() - start)
    return float(np.median(values))


def _peak_mb(call):
    tracemalloc.start()
    try:
        call()
        return tracemalloc.get_traced_memory()[1] / (1024.0 * 1024.0)
    finally:
        tracemalloc.stop()


def _pack_lsb(values, bits):
    stream = ((np.asarray(values, np.uint16)[:, None] >> np.arange(bits)) & 1)
    return np.packbits(stream.astype(np.uint8).ravel(), bitorder="little")


def _unpack_lsb_naive(packed, bits, count):
    """参照: 全バイトを 8 ビットに広げてから並べ直す素朴な展開(省メモリ版が既定になる前の考え方)。"""
    b = np.unpackbits(np.asarray(packed, dtype=np.uint8), bitorder="little")[: bits * count]
    weights = (np.uint32(1) << np.arange(bits, dtype=np.uint32))
    return (b.reshape(count, bits).astype(np.uint32) * weights).sum(axis=1).astype(np.uint16)


def main():
    r = np.linspace(0.0, 4.0, 401)
    f = np.exp(-np.pi * r*r)
    plan = fs.HankelPlan(order=0, n=200)
    before = fs.HankelPlan.constructions

    def transforms():
        return [fs.hankel_transform(r, f, r_max=4.0, n=200, plan=plan) for _ in range(50)]

    transformed = transforms()[-1]
    assert fs.HankelPlan(order=0, n=200) is plan
    assert fs.HankelPlan.constructions == before
    np.testing.assert_allclose(transformed["F"], np.exp(-np.pi*transformed["nu"]**2), atol=3e-3)
    hankel_s = _median_seconds(transforms)

    yy, xx = np.mgrid[:1024, :1024]
    flow = np.stack((0.002*yy, 0.003*xx)).astype(float)
    flow[:, 512, 512] += 20.0
    whole = pivops.piv_outlier_mask(flow)
    streamed = fs.piv_outlier_mask_stream(flow, chunk=4)
    np.testing.assert_array_equal(streamed, whole)
    whole_mb = _peak_mb(lambda: pivops.piv_outlier_mask(flow))
    stream_mb = _peak_mb(lambda: fs.piv_outlier_mask_stream(flow, chunk=4))

    count, bits = 1_600_000, 10                  # 16 Mbitのpacked pixel列
    values = (np.arange(count, dtype=np.uint32) * 37 % (1 << bits)).astype(np.uint16)
    packed = _pack_lsb(values, bits)
    naive = _unpack_lsb_naive(packed, bits, count)      # 参照: 全バイトを 8 ビットに広げる素朴な展開
    shipped = fs.unpack_lsb(packed, bits, count)        # 出荷の経路(省メモリ版が唯一の経路、0.7.2)
    np.testing.assert_array_equal(naive, values)
    np.testing.assert_array_equal(shipped, values)
    exact_mb = _peak_mb(lambda: _unpack_lsb_naive(packed, bits, count))
    low_mb = _peak_mb(lambda: fs.unpack_lsb(packed, bits, count))

    examplefig.save_plot(
        "bounded_memory_peak",
        [("PIV一括", [0], [whole_mb]), ("PIV stream", [1], [stream_mb]),
         ("unpack 素朴", [2], [exact_mb]), ("unpack 出荷", [3], [low_mb])],
        ylabel="tracemalloc peak [MiB]", title="省メモリ経路のピーク割り当て",
        kinds=["bar"] * 4, colors=["wrong", "right", "wrong", "right"],
        xlim=(-0.5, 3.5), caption="PIV 1024²場と16 Mbit packed pixel列。")
    print(f"PASS bounded helpers: Hankel 50x {hankel_s:.6f} s, error < 0.003; "
          f"PIV {whole_mb:.2f}->{stream_mb:.2f} MiB; unpack {exact_mb:.2f}->{low_mb:.2f} MiB")


if __name__ == "__main__":
    main()
