# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""偏光スイープを一度だけ当てはめ、分離・DoLP・Stokes をまとめて得る例。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

import examplefig
import fullseye as fs


def main():
    angles = np.array([0.0, 45.0, 90.0, 135.0])
    y, x = np.mgrid[:32, :40]
    a0 = 4.0 + 0.01 * x
    a1 = 0.8 + 0.002 * y
    a2 = np.full_like(a0, 0.6)
    frames = np.stack([a0 + a1*np.cos(np.deg2rad(2*a)) + a2*np.sin(np.deg2rad(2*a))
                       for a in angles])
    got = fs.polarization_analyze(frames, angles)
    np.testing.assert_allclose(got["dolp"], fs.polarization_dolp_map(frames, angles), atol=1e-12)
    np.testing.assert_allclose(got["stokes"], fs.polarization_stokes(frames, angles), atol=1e-12)
    diffuse, specular = fs.polarization_separate(frames, angles)
    np.testing.assert_allclose(got["diffuse"], diffuse, atol=1e-12)
    np.testing.assert_allclose(got["specular"], specular, atol=1e-12)
    examplefig.save("polarization_dolp", got["dolp"],
                    "4 方位の偏光像から一度の当てはめで得た直線偏光度")
    print("PASS polarization separation, DoLP and Stokes")


if __name__ == "__main__":
    main()
