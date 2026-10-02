# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""watershed3d_tour — 接触した 2 つの球を、距離変換シードの 3-D 分水嶺で 2 個に割る。

    py -3.11 examples/watershed3d_tour.py

【この例が示すこと】
``fullseye.ledger`` の 3 本(distance_peaks / watershed_vol / separate_touching、台帳 opssegmentation の
``watershed3d``)を、答えが決まる体積で呼ぶ。連結成分ラベリングでは 1 個に融合する「接した 2 球」が、
分水嶺では 2 個に分かれることを数で見る。

【場面】
* (24, 24, 40) の体積に半径 7 の球を 2 つ、中心 x = 13 と 26(中心間 13 < 14 = 直径なので接して融合する)。
  x → 39 − x の鏡映で 2 球は入れ替わり、格子も自分に写る(中面 x = 19.5 は画素の間)。
* 半径の違う 2 球(7 と 5)。

【グラウンドトゥルース(すべて assert で落とす)】
1. 連結成分では 1 個(融合している)/ distance_peaks のシードは 2 個(1 球 1 個)。
2. watershed_vol は 2 ラベルで、前景をちょうど覆う(ラベル > 0 の集合 = 前景)。
3. 鏡映対称なので 2 ラベルの体積は**厳密に等しい**。
4. separate_touching(v, d) は watershed_vol(v, markers=None, min_distance=d) と画素一致(畳んだだけ)。
5. 半径の違う 2 球では大きい球のラベルの体積が大きい。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fullseye as fs          # noqa: E402  公開経路(fs.ledger.<op>)から呼ぶ


def two_balls(r1=7, r2=7, shape=(24, 24, 40), c1=13, c2=26):
    z, y, x = np.mgrid[:shape[0], :shape[1], :shape[2]]
    zc, yc = (shape[0] - 1) / 2.0, (shape[1] - 1) / 2.0
    a = (z - zc) ** 2 + (y - yc) ** 2 + (x - c1) ** 2 <= r1 * r1
    b = (z - zc) ** 2 + (y - yc) ** 2 + (x - c2) ** 2 <= r2 * r2
    return a | b


def run() -> dict:
    t0 = time.perf_counter()
    L = fs.ledger
    out = {}

    v = two_balls()
    n_cc = ndimage.label(v)[1]
    seeds = np.asarray(L.distance_peaks(v, min_distance=5.0))
    n_seed = len(np.unique(seeds)) - 1
    print("1) 接した 2 球: 前景 %d 画素、連結成分 %d 個、distance_peaks のシード %d 個" % (int(v.sum()), n_cc, n_seed))
    assert n_cc == 1 and n_seed == 2

    lab = np.asarray(L.watershed_vol(v, min_distance=5.0))
    ids = [i for i in np.unique(lab) if i != 0]
    vols = [int((lab == i).sum()) for i in ids]
    print("2) watershed_vol: ラベル %d 個、体積 %s、前景を覆う = %s" % (len(ids), vols, bool(np.array_equal(lab > 0, v))))
    assert len(ids) == 2 and np.array_equal(lab > 0, v)
    assert vols[0] == vols[1], vols
    print("3) 鏡映対称 → 2 つの体積は厳密に等しい: %d = %d" % tuple(vols))

    st = np.asarray(L.separate_touching(v, min_distance=5.0))
    assert np.array_equal(st, lab)
    print("4) separate_touching は watershed_vol(markers=None) と画素一致")

    u = two_balls(7, 5)
    lu = np.asarray(L.separate_touching(u, min_distance=4.0))
    big = int(lu[12, 12, 13])
    small = int(lu[12, 12, 26])
    vb, vs = int((lu == big).sum()), int((lu == small).sum())
    print("5) 半径 7 と 5: 体積 %d と %d(大きい球が大きい)" % (vb, vs))
    assert big != small and vb > vs

    out.update(n_cc=n_cc, n_seed=n_seed, volumes=vols, unequal=(vb, vs))
    out["elapsed_s"] = round(time.perf_counter() - t0, 3)
    print("PASS  watershed3d_tour  (%.3f s)" % out["elapsed_s"])
    return out


if __name__ == "__main__":
    run()
