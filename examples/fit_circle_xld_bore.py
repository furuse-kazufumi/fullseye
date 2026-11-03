"""穴の位置と半径を XLD 輪郭から読む —— ``fit_circle_xld``(HALCON fit_circle_contour_xld)の呼び出し例.

明るい円板(穴の抜け・ワッシャ・丸い部品)をサブピクセルの輪郭にし(``threshold_sub_pix``)、
輪郭 1 本ごとに円を当てはめて中心の行・列と半径を読む。真値は描いた円そのもの
(中心 (50.3, 44.6)、半径 20.5 px)。幾何距離の当てはめ(既定)と代数的な当てはめ
(Kåsa)を並べ、短い円弧で代数法が半径を小さく偏らせることも確かめる。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

import api
import fullseye as fs


def main():
    cy, cx, r = 50.3, 44.6, 20.5
    yy, xx = np.mgrid[0:96, 0:96]
    # 画素を 8x8 に細分した被覆率で描く(縁の灰色が真の円の位置を持つ)
    sub = (np.arange(8) + 0.5) / 8.0 - 0.5
    cover = np.zeros((96, 96))
    for dy in sub:
        for dx in sub:
            cover += ((yy + dy - cy) ** 2 + (xx + dx - cx) ** 2 <= r * r)
    img = 0.15 + 0.7 * cover / 64.0

    xld = api.apply(img, "threshold_sub_pix", 0.5, 0.5, device="cpu")     # contour(XLD dict)
    geo = fs.ledger.fit_circle_xld(xld)                                    # 既定 method="geometric"
    alg = fs.ledger.fit_circle_xld(xld, method="algebraic")
    print("geometric: row=%.3f col=%.3f radius=%.3f rms=%.3f (%d points)"
          % (geo["row"][0], geo["col"][0], geo["radius"][0], geo["rms"][0], geo["n_points"][0]))
    print("algebraic: radius=%.3f" % alg["radius"][0])
    assert geo["n_contours"] == 1
    assert abs(geo["row"][0] - cy) < 0.05 and abs(geo["col"][0] - cx) < 0.05, geo
    # 半径の 0.1 px 弱の偏りは輪郭抽出(被覆率の縁を直線補間)の側。当てはめ自体は点が円上なら厳密
    assert abs(geo["radius"][0] - r) < 0.15, geo

    # 短い円弧(右上 60° だけ): 幾何法は半径を保ち、代数法は偏りうる
    t = np.radians(np.linspace(0.0, 60.0, 40))
    rng = np.random.default_rng(0)
    arc = np.c_[cy - r * np.sin(t), cx + r * np.cos(t)] + 0.05 * rng.standard_normal((40, 2))
    short = {"shape": (96, 96), "cs": [arc]}
    g2 = fs.ledger.fit_circle_xld(short)["radius"][0]
    a2 = fs.ledger.fit_circle_xld(short, method="algebraic")["radius"][0]
    print("60-degree arc: geometric r=%.3f, algebraic r=%.3f (truth %.1f)" % (g2, a2, r))
    assert abs(g2 - r) < 1.0
    print("PASS")


if __name__ == "__main__":
    main()
