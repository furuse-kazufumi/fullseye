"""縞・格子の周期と向きを 1 回で読む —— ``wave_dominant_frequency`` の呼び出し例.

向き θ・周期 p の縞 ``cos(2π(x cosθ + y sinθ)/p)`` を描き、2-D FFT の DC 以外で最大の山から
周期 [px] と向き [deg] を読み返す。真値は描いた (θ, p)。1 軸の ``wave_fringe_period`` は
縞が斜めだと列方向の見かけの周期 p / cosθ を返す —— 向きつきの 2-D 版が要る理由を並べて示す。
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

import fullseye as fs


def grating(theta_deg, period, n=64):
    th = math.radians(theta_deg)
    yy, xx = np.mgrid[0:n, 0:n]
    return 0.5 + 0.4 * np.cos(2 * np.pi * (xx * math.cos(th) + yy * math.sin(th)) / period)


def main():
    for theta, p in ((30.0, 8.0), (60.0, 8.0), (120.0, 11.0), (0.0, 6.5)):
        img = grating(theta, p)
        r = fs.ledger.wave_dominant_frequency(img)
        one_axis = fs.ledger.wave_fringe_period(img)
        print("theta=%5.1f p=%4.1f -> angle=%7.3f period=%6.3f px (peak %.2f) | 1-axis period=%6.3f"
              % (theta, p, r["angle_deg"], r["period_px"], r["peak_fraction"], one_axis))
        assert abs(r["period_px"] - p) < 0.02 * p, r
        assert min(abs(r["angle_deg"] - theta), 180 - abs(r["angle_deg"] - theta)) < 0.3, r
    print("PASS")


if __name__ == "__main__":
    main()
