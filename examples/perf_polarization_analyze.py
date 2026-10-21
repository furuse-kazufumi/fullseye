# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""偏光の分離・DoLP・Stokesを個別呼び出しと一括呼び出しで実測する。"""
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
    angles = np.array([0.0, 45.0, 90.0, 135.0])
    y, x = np.mgrid[:1024, :1024]
    a0 = 4.0 + 0.0002 * x
    a1 = 0.8 + 0.0001 * y
    a2 = np.full_like(a0, 0.6)
    frames = np.stack([a0 + a1*np.cos(np.deg2rad(2*a)) + a2*np.sin(np.deg2rad(2*a))
                       for a in angles])

    def separate():
        diffuse, specular = fs.polarization_separate(frames, angles)
        return diffuse, specular, fs.polarization_dolp_map(frames, angles), \
            fs.polarization_stokes(frames, angles)

    def combined():
        result = fs.polarization_analyze(frames, angles)
        return tuple(result[k] for k in ("diffuse", "specular", "dolp", "stokes"))

    reference, got = separate(), combined()
    error = max(float(np.max(np.abs(a - b))) for a, b in zip(reference, got))
    for actual, desired in zip(got, reference):
        np.testing.assert_allclose(actual, desired, atol=1e-12)
    separate_s, combined_s = _median_seconds(separate), _median_seconds(combined)
    ratio = separate_s / combined_s
    examplefig.save_plot(
        "polarization_analyze_runtime",
        [("個別 3 回", [0], [1000.0 * separate_s]),
         ("一括", [1], [1000.0 * combined_s])],
        ylabel="中央値 [ms]", title="4×1024×1024 偏光解析 (3 回の中央値)",
        kinds=["bar", "bar"], colors=["wrong", "right"], xlim=(-0.5, 1.5),
        caption="同じ4方位画像から分離・DoLP・Stokesを得る時間。")
    print(f"PASS polarization: max error {error:.3g}; separate {separate_s:.6f} s; "
          f"combined {combined_s:.6f} s; {ratio:.2f}x")


if __name__ == "__main__":
    main()
