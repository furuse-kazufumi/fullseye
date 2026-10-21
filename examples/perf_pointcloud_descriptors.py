# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""点群の曲率3量を個別呼び出しと一括呼び出しで実測する。"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

import curvature3d
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
    rng = np.random.default_rng(271)
    xy = rng.uniform(-1.0, 1.0, (20_000, 2))
    points = np.column_stack((xy, 0.20 * np.sum(xy * xy, axis=1)))

    separate = lambda: (curvature3d.mean_curvature(points, k=20),       # noqa: E731
                        curvature3d.gaussian_curvature(points, k=20),
                        curvature3d.shape_index(points, k=20))
    combined = lambda: fs.curvature_descriptors(points, k=20)          # noqa: E731
    reference, got = separate(), combined()
    selected = tuple(got[k] for k in ("mean", "gaussian", "shape_index"))
    error = max(float(np.max(np.abs(a - b))) for a, b in zip(reference, selected))
    np.testing.assert_allclose(selected, reference, atol=0.0)

    axes, extent = fs.grid_axes(((-2, 2), (-1, 1), (0, 3)), (8, 6, 4))
    assert tuple(map(len, axes)) == (8, 6, 4)
    assert extent == (-2.0, 2.0, -1.0, 1.0, 0.0, 3.0)

    separate_s, combined_s = _median_seconds(separate), _median_seconds(combined)
    ratio = separate_s / combined_s
    examplefig.save_plot(
        "pointcloud_descriptors_runtime",
        [("個別 3 回", [0], [separate_s]), ("一括", [1], [combined_s])],
        ylabel="中央値 [s]", title="20,000点の曲率3量 (3 回の中央値)",
        kinds=["bar", "bar"], colors=["wrong", "right"], xlim=(-0.5, 1.5),
        caption="平均・Gauss曲率・shape indexを同じ近傍探索から得る時間。")
    detail = "0.0 (bit-exact)" if error == 0.0 else f"{error:.3g}"
    print(f"PASS curvature: max error {detail}; separate {separate_s:.6f} s; "
          f"combined {combined_s:.6f} s; {ratio:.2f}x")


if __name__ == "__main__":
    main()
