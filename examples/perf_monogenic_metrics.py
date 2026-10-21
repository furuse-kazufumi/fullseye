# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""monogenic 場の振幅・位相・向きを一度の検証で読む例。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

import examplefig
import fullseye as fs


def main():
    y, x = np.mgrid[:48, :64]
    phase = 2.0 * np.pi * (3.0 * x / 64.0 + 2.0 * y / 48.0)
    image = np.cos(phase)
    q = fs.monogenic_signal(image)
    amplitude, local_phase, orientation = fs.monogenic_metrics(q)
    np.testing.assert_allclose(amplitude, fs.monogenic_amplitude(q), atol=1e-12)
    np.testing.assert_allclose(local_phase, fs.monogenic_phase(q), atol=1e-12)
    np.testing.assert_allclose(orientation, fs.monogenic_orientation(q), atol=1e-12)
    assert np.all(amplitude >= 0.0) and np.all((orientation >= 0.0) & (orientation < np.pi))
    examplefig.save("monogenic_amplitude", amplitude,
                    "正弦格子の monogenic 振幅。位相・向きも同じ検証から得る")
    print("PASS monogenic amplitude, phase and orientation")


if __name__ == "__main__":
    main()
