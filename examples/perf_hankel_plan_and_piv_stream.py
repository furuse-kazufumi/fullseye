# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Hankel 核の再利用、PIV の行分割、packed pixel の省メモリ復号を確かめる例。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

import examplefig
import fullseye as fs
import pivops


def _pack_lsb(values, bits):
    values = np.asarray(values, np.uint16)
    stream = ((values[:, None] >> np.arange(bits)) & 1).astype(np.uint8).ravel()
    return np.packbits(stream, bitorder="little")


def main():
    r = np.linspace(0.0, 4.0, 401)
    f = np.exp(-np.pi * r*r)
    plan = fs.HankelPlan(order=0, n=48)
    assert fs.HankelPlan(order=0, n=48) is plan
    transformed = fs.hankel_transform(r, f, r_max=4.0, n=48, plan=plan)
    np.testing.assert_allclose(transformed["F"], np.exp(-np.pi*transformed["nu"]**2), atol=3e-3)

    yy, xx = np.mgrid[:25, :31]
    flow = np.stack((0.02*yy, 0.03*xx)).astype(float)
    flow[:, 12, 15] += 20.0
    streamed = fs.piv_outlier_mask_stream(flow, chunk=4)
    np.testing.assert_array_equal(streamed, pivops.piv_outlier_mask(flow))

    values = np.array([0, 1, 1023, 513, 17, 999], np.uint16)
    packed = _pack_lsb(values, 10)
    exact = fs.unpack_lsb(packed, 10, len(values), method="exact")
    low_memory = fs.unpack_lsb(packed, 10, len(values), method="low_memory")
    np.testing.assert_array_equal(exact, values)
    np.testing.assert_array_equal(low_memory, values)
    examplefig.save("piv_stream_outlier", streamed.astype(float),
                    "行分割で作った PIV 外れ値マスク。全体計算と同じ結果")
    print("PASS reusable Hankel plan, streamed PIV mask and low-memory unpack")


if __name__ == "__main__":
    main()
