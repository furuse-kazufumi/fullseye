# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""体積のcubic spline係数を50本の線プローブで再利用して実測する。"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

import examplefig
import fullseye as fs


def _median_seconds(call, repeats=3):
    values = []
    for _ in range(repeats):
        start = time.perf_counter()
        call()
        values.append(time.perf_counter() - start)
    return float(np.median(values))


def main():
    z, y, x = np.mgrid[:64, :64, :64]
    volume = np.sin(x / 11.0) + np.cos(y / 13.0) + 0.01 * z
    prepared = fs.prepare_vol_probe(volume, spline_orders=(3,))
    assert isinstance(prepared, fs.PreparedVolProbe) and not prepared.volume.flags.writeable
    rng = np.random.default_rng(271)
    endpoints = [(rng.uniform(0, 63, 3), rng.uniform(0, 63, 3)) for _ in range(50)]

    def probe(source):
        return [fs.vol_profile_line(source, a, b, n=1024, order=3) for a, b in endpoints]

    raw, cached = probe(volume), probe(prepared)
    error = max(float(np.max(np.abs(a[1] - b[1]))) for a, b in zip(raw, cached))
    for a, b in zip(raw, cached):
        np.testing.assert_allclose(b[0], a[0], atol=0.0)
        np.testing.assert_allclose(b[1], a[1], atol=1e-12)

    raw_s = _median_seconds(lambda: probe(volume))
    cached_s = _median_seconds(lambda: probe(prepared))
    ratio = raw_s / cached_s
    examplefig.save_plot(
        "prepared_volume_probe_runtime",
        [("毎回係数を計算", [0], [1000.0 * raw_s]),
         ("係数を再利用", [1], [1000.0 * cached_s])],
        ylabel="中央値 [ms]", title="64³体積・50本×1024標本 (3 回の中央値)",
        kinds=["bar", "bar"], colors=["wrong", "right"], xlim=(-0.5, 1.5),
        caption="cubic spline係数を準備済み体積から再利用する時間。")
    print(f"PASS volume probe: max error {error:.3g}; raw {raw_s:.6f} s; "
          f"prepared {cached_s:.6f} s; {ratio:.2f}x")


if __name__ == "__main__":
    main()
