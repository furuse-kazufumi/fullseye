# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""体積検証と cubic spline 係数を複数の線プローブで再利用する例。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

import examplefig
import fullseye as fs


def main():
    z, y, x = np.mgrid[:24, :20, :18]
    volume = 0.5 * z + 0.25 * y + x
    prepared = fs.prepare_vol_probe(volume, spline_orders=(3,))
    assert isinstance(prepared, fs.PreparedVolProbe)
    assert not prepared.volume.flags.writeable
    for p0, p1 in [((2, 3, 4), (20, 16, 14)), ((3, 15, 2), (19, 4, 15))]:
        t0, raw = fs.vol_profile_line(volume, p0, p1, n=51, order=3)
        t1, cached = fs.vol_profile_line(prepared, p0, p1, n=51, order=3)
        np.testing.assert_allclose(t1, t0, atol=0.0)
        np.testing.assert_allclose(cached, raw, atol=1e-12)
    examplefig.save("prepared_volume_slice", volume[12],
                    "複数の線プローブが共有する検証済み体積の中央断面")
    print("PASS prepared volume probe matches ordinary cubic probes")


if __name__ == "__main__":
    main()
