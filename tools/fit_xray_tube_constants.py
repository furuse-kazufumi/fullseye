# -*- coding: utf-8 -*-
"""dualxray の X 線管の模型の 4 定数を、SpekPy(MIT)のスペクトルに合わせ直して印字する(ファイルは書かない)。

使い方(SpekPy は optional。fullseye の実行には要らない)::

    py -3.11 -m pip install spekpy
    py -3.11 tools/fit_xray_tube_constants.py

合わせるもの(2026-10-15 に決めた手順):

1. 制動放射だけ(SpekPy の ``char=False``)の形: W 陽極 12°・Al 2.5 mm・40〜150 kV の 11 点で、正規化した
   スペクトルの全変動距離の平均が最小になる (DEPTH_FRACTION, DEPTH_EXPONENT) を格子で探す。
2. 特性線の割合(SpekPy の ``char=True`` と ``False`` の光子数の差 / 全体)を 80〜150 kV の 7 点で二乗誤差最小に
   する (K_SCALE, K_EXPONENT) を格子で探す。

IEC 61267 の線質の半価層は**合わせに使わない**(門の外部真値として取っておく)。結果は
``dualxray.py`` の定数と見比べる(違えば手で写す。2026-10-15 の値: 0.25 / 0.95 / 0.035 / 1.15)。
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dualxray as d  # noqa: E402

try:
    import spekpy
except ImportError:  # pragma: no cover
    sys.exit("SpekPy is required: py -3.11 -m pip install spekpy")

KV_SHAPE = (40, 50, 60, 70, 80, 90, 100, 110, 120, 135, 150)
KV_CHAR = (80, 90, 100, 110, 120, 135, 150)


def _spek(kv, char):
    s = spekpy.Spek(kvp=kv, th=12, dk=0.5, char=char)
    s.filter("Al", 2.5)
    k, f = s.get_spectrum()
    return np.asarray(k), np.asarray(f)


def main():
    ref = {(kv, c): _spek(kv, c) for kv in sorted(set(KV_SHAPE) | set(KV_CHAR)) for c in (True, False)}

    def shape_err(kv):
        k, f = ref[(kv, False)]
        m = d.xray_tube_spectrum(kv, e_min_kev=k[0] - 0.25, de_kev=0.5, characteristic=False)
        g = np.interp(m[:, 0], k, f)
        g = g / (g.sum() * 0.5)
        return 0.5 * np.sum(np.abs(m[:, 1] - g)) * 0.5

    best = None
    for F in np.linspace(0.15, 0.5, 36):
        for b in np.linspace(0.0, 1.2, 25):
            d.DEPTH_FRACTION, d.DEPTH_EXPONENT = F, b
            e = float(np.mean([shape_err(kv) for kv in KV_SHAPE]))
            if best is None or e < best[0]:
                best = (e, F, b)
    d.DEPTH_FRACTION, d.DEPTH_EXPONENT = best[1], best[2]
    print("DEPTH_FRACTION = %.2f, DEPTH_EXPONENT = %.2f (mean total-variation distance %.4f)" % (best[1], best[2], best[0]))

    target = {kv: (ref[(kv, True)][1].sum() - ref[(kv, False)][1].sum()) / ref[(kv, True)][1].sum() for kv in KV_CHAR}

    def char_fraction(kv):
        a = d.xray_tube_spectrum(kv, de_kev=0.5)
        b = d.xray_tube_spectrum(kv, de_kev=0.5, characteristic=False)
        j = int(np.argmin(np.abs(a[:, 0] - 40.0)))
        return 1.0 - a[j, 1] / b[j, 1]

    best = None
    for A in np.linspace(0.01, 0.12, 45):
        for p in np.linspace(0.6, 1.8, 25):
            d.K_SCALE, d.K_EXPONENT = A, p
            e = sum((char_fraction(kv) - target[kv]) ** 2 for kv in KV_CHAR)
            if best is None or e < best[0]:
                best = (e, A, p)
    d.K_SCALE, d.K_EXPONENT = best[1], best[2]
    print("K_SCALE = %.3f, K_EXPONENT = %.2f" % (best[1], best[2]))
    for kv in KV_CHAR:
        print("  %3d kV: K-line fraction SpekPy %.4f, model %.4f" % (kv, target[kv], char_fraction(kv)))


if __name__ == "__main__":
    main()
