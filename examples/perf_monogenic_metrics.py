# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""monogenic の三つの指標を個別呼び出しと一括呼び出しで実測する。"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

import examplefig
import fullseye as fs


def _median_seconds(call, repeats=3):
    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        call()
        samples.append(time.perf_counter() - start)
    return float(np.median(samples))


def main():
    y, x = np.mgrid[:1024, :1024]
    image = np.cos(2.0 * np.pi * (31.0 * x / 1024.0 + 19.0 * y / 1024.0))
    q = fs.monogenic_signal(image)

    separate = lambda: (fs.monogenic_amplitude(q), fs.monogenic_phase(q),  # noqa: E731
                        fs.monogenic_orientation(q))
    combined = lambda: fs.monogenic_metrics(q)                            # noqa: E731
    reference = separate()
    got = combined()
    error = max(float(np.max(np.abs(a - b))) for a, b in zip(reference, got))
    np.testing.assert_allclose(got, reference, atol=1e-12)

    separate_s = _median_seconds(separate)
    combined_s = _median_seconds(combined)
    ratio = separate_s / combined_s
    examplefig.save_plot(
        "monogenic_metrics_runtime",
        [("個別 3 回", [0], [1000.0 * separate_s]),
         ("一括", [1], [1000.0 * combined_s])],
        ylabel="中央値 [ms]", title="1024×1024 monogenic 指標 (3 回の中央値)",
        kinds=["bar", "bar"], colors=["wrong", "right"], xlim=(-0.5, 1.5),
        caption="同じ quaternion 場から振幅・位相・向きを得る時間。")
    print(f"PASS monogenic: max error {error:.3g}; separate {separate_s:.6f} s; "
          f"combined {combined_s:.6f} s; {ratio:.2f}x")


if __name__ == "__main__":
    main()
