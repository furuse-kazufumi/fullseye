# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""点群の曲率諸量と SDF の座標軸を、一度だけ組み立てて使う例。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

import examplefig
import fullseye as fs
import curvature3d


def main():
    y, x = np.mgrid[-1.0:1.0:13j, -1.0:1.0:13j]
    points = np.column_stack((x.ravel(), y.ravel(), (0.20 * (x*x + y*y)).ravel()))
    got = fs.curvature_descriptors(points, k=20, include_normals=True)
    np.testing.assert_allclose(got["mean"], curvature3d.mean_curvature(points, k=20), atol=1e-12)
    np.testing.assert_allclose(got["gaussian"], curvature3d.gaussian_curvature(points, k=20), atol=1e-12)
    assert got["normals"].shape == points.shape

    axes, extent = fs.grid_axes(((-2, 2), (-1, 1), (0, 3)), (8, 6, 4))
    assert tuple(map(len, axes)) == (8, 6, 4)
    np.testing.assert_allclose([a.mean() for a in axes], (0.0, 0.0, 1.5))
    assert extent == (-2.0, 2.0, -1.0, 1.0, 0.0, 3.0)

    examplefig.save("pointcloud_curvedness", got["curvedness"].reshape(x.shape),
                    "放物面点群の curvedness。近傍探索は全記述子で一度だけ")
    print("PASS curvature descriptors and voxel-centre axes")


if __name__ == "__main__":
    main()
