# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""blob_split_tour — 融合した 2 つの円板を距離変換 → h-maxima の種 → 分水嶺で割り、既知の答えと突き合わせる。

    py -3.11 examples/blob_split_tour.py

【この例が示すこと】
細胞・粒子・錠剤のように「触れ合って 1 塊に見える物体」を数えるときの定番手順
``blob_distance`` → ``blob_seeds`` → ``blob_split``。それぞれの出力を閉形式で検算する。

【場面(答えを自分で埋める)】
* 半径 22 と 16 の円板を中心間 32 px で重ねる(融合塊、くびれの半幅 ≈ 10)。
* 孤立した半径 10 の円板(割ってはいけない)。
* 厚さ 3 px の棒(距離の最大 2 < h → 種が立たない。**種の無い塊はそのまま残す**)。

【グラウンドトゥルース(すべて assert で落とす)】
1. ``blob_distance``: 各円板の中心の値 == 半径(22 / 16 / 10 ちょうど)、棒の最大 == 2、
   ``spacing=0.5`` で値がちょうど半分。
2. ``blob_seeds(h=4)``: 種は 3 つ(融合塊に 2、孤立円板に 1、棒に 0)。各種は
   「その山の高さ − h より高い画素」の集合と**画素単位で一致**(h-maxima の閉形式)。
3. ``blob_split``: 結果は 4 領域。融合塊の 2 中心は別ラベル、棒と孤立円板は元のまま
   (画素単位)、前景の画素は 1 つも失われない。融合塊の割れ目は 2 円の交線(くびれ)——
   交線で分けた期待領域との不一致画素を数え、2 % 未満(honest に個数を印字)。

【読み方】各節の印字は「真値 / 実測 / 差」。PASS 行が出れば全部通っている。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import blob2d as B            # noqa: E402  blob 層(ラベル・距離・種・分水嶺)

H, W = 120, 180
C1, R1 = (50, 60), 22         # (row, col), 半径 —— 融合塊の大きいほう
C2, R2 = (50, 92), 16         # 中心間 32 = 22 + 16 - 6(6 px 重なる)
C3, R3 = (25, 150), 10        # 孤立円板
BAR = (slice(95, 98), slice(20, 80))   # 厚さ 3 の棒


def _disk(center, r):
    yy, xx = np.mgrid[0:H, 0:W]
    return ((yy - center[0]) ** 2 + (xx - center[1]) ** 2) < r * r


def scene():
    """合成マスクと、検算に使う部品マスク。★EXTEND: mask を自分の二値画像に差し替える。"""
    d1, d2, d3 = _disk(C1, R1), _disk(C2, R2), _disk(C3, R3)
    bar = np.zeros((H, W), bool)
    bar[BAR] = True
    return (d1 | d2 | d3 | bar), d1, d2, d3, bar


def run() -> dict:
    t0 = time.perf_counter()
    mask, d1, d2, d3, bar = scene()

    # 0) 連結成分(融合塊は 1 つに数えられてしまう —— これを割るのが目的)
    lab = B.blob_label(mask)
    n0 = int(lab.max())
    print(f"0) blob_label: 連結成分 {n0} 個(円板 3 + 棒 1 のはずが、2 つは融合して 1 つ)")
    assert n0 == 3 and lab[C1] == lab[C2]

    # 1) 距離変換: 中心の値 == 半径(格子中心なので厳密)
    dist = B.blob_distance(mask)
    vals = (float(dist[C1]), float(dist[C2]), float(dist[C3]), float(dist[bar].max()))
    half = B.blob_distance(mask, spacing=0.5)
    print(f"1) blob_distance: 中心の値 {vals[:3]}(真値 {R1}, {R2}, {R3})、棒の最大 {vals[3]}(真値 2)、"
          f"spacing=0.5 で厳密に半分 {np.array_equal(half, dist * 0.5)}")
    assert vals == (float(R1), float(R2), float(R3), 2.0)
    assert np.array_equal(half, dist * 0.5)

    # 2) 種: h-maxima の閉形式(山の高さ - h より高い画素)
    h = 4.0
    seeds = B.blob_seeds(dist, h)
    n_seeds = int(seeds.max())
    # 交線(くびれ)の col: 2 円の交点を通る直線 —— 中心線上の位置 a = (d^2 + R1^2 - R2^2) / 2d
    d = C2[1] - C1[1]
    chord = C1[1] + (d * d + R1 * R1 - R2 * R2) / (2.0 * d)
    cols = np.arange(W)[None, :]
    side1 = (d1 | d2) & (cols < chord)
    side2 = (d1 | d2) & (cols >= chord)
    seed_want = ((dist > R1 - h) & side1) | ((dist > R2 - h) & side2) | ((dist > R3 - h) & d3)
    seed_exact = np.array_equal(seeds > 0, seed_want)
    ids = (int(seeds[C1]), int(seeds[C2]), int(seeds[C3]))
    print(f"2) blob_seeds(h={h:g}): 種 {n_seeds} 個(真値 3: 棒は最大 2 < h で立たない)、"
          f"中心の種番号 {ids}(全部違う)、h-maxima 閉形式と画素単位で一致 {seed_exact}、"
          f"棒の上の種 {int((seeds[bar] > 0).sum())} 画素")
    assert n_seeds == 3 and len(set(ids)) == 3 and min(ids) > 0
    assert seed_exact and not (seeds[bar] > 0).any()

    # 3) 分水嶺で割る
    split = B.blob_split(lab, seeds, dist)
    n_split = int(split.max())
    l1, l2, l3, lb = int(split[C1]), int(split[C2]), int(split[C3]), int(split[BAR][1, 30])
    kept_bar = np.array_equal(split == lb, bar)
    kept_d3 = np.array_equal(split == l3, d3)
    no_loss = np.array_equal(split > 0, mask)
    region1, region2 = split == l1, split == l2
    mismatch = int(((region1 & side2) | (region2 & side1)).sum())
    pair_area = int((d1 | d2).sum())
    a1, a2 = int(region1.sum()), int(region2.sum())
    print(f"3) blob_split: {n_split} 領域(真値 4)、融合塊の 2 中心は別ラベル {l1 != l2}、"
          f"棒がそのまま {kept_bar}、孤立円板がそのまま {kept_d3}、前景を失わない {no_loss}")
    print(f"   割れ目: 交線 col={chord:.2f} で分けた期待と違う画素 {mismatch} / {pair_area}"
          f"({100.0 * mismatch / pair_area:.2f} %)、面積 {a1} / {a2}"
          f"(交線で分けた期待 {int(side1.sum())} / {int(side2.sum())})")
    assert n_split == 4 and l1 != l2 and kept_bar and kept_d3 and no_loss
    assert mismatch < 0.02 * pair_area

    # 4) h を上げると割れない(割りすぎ↔割り残しのつまみ)—— くびれの高さ差より大きい h
    seeds_hi = B.blob_seeds(dist, h=8.0)
    split_hi = B.blob_split(lab, seeds_hi, dist)
    print(f"4) h=8(小さい山の高さ 16 - くびれ 10 = 6 より大): 種 {int(seeds_hi.max())} 個、"
          f"領域 {int(split_hi.max())} 個(融合塊は割れない)、2 中心は同じラベル {split_hi[C1] == split_hi[C2]}")
    assert int(split_hi.max()) == 3 and split_hi[C1] == split_hi[C2]

    return {"components_before": n0, "center_distances": vals[:3], "bar_max_distance": vals[3],
            "n_seeds": n_seeds, "seed_closed_form_exact": seed_exact,
            "n_regions": n_split, "bar_kept": kept_bar, "isolated_kept": kept_d3,
            "no_pixel_lost": no_loss, "chord_col": float(chord),
            "split_mismatch_px": mismatch, "pair_area_px": pair_area,
            "areas": (a1, a2), "areas_want": (int(side1.sum()), int(side2.sum())),
            "elapsed_s": time.perf_counter() - t0}


def main():
    r = run()
    print(f"\nPASS: blob_distance(中心値=半径)/ blob_seeds(h-maxima 閉形式と画素一致)/ "
          f"blob_split(4 領域・前景保存・割れ目は交線 ±{100.0 * r['split_mismatch_px'] / r['pair_area_px']:.2f} %)。"
          f" 実行 {r['elapsed_s']:.2f} 秒")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
