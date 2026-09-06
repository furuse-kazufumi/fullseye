# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""blob_split_tour — 融合した 2 つの円板を距離変換 → h-maxima の種 → 分水嶺で割り、既知の答えと突き合わせる。

    py -3.11 examples/blob_split_tour.py

【この例が示すこと】
細胞・粒子・錠剤のように「触れ合って 1 塊に見える物体」を数えるときの定番手順
``blob_distance`` → ``blob_seeds`` → ``blob_split``。それぞれの出力を閉形式で検算する。

【場面(答えを自分で埋める)】
* 半径 22 と 16 の円板を中心間 32 px で重ねる(融合塊、くびれの半幅 ≈ 10)。
* 孤立した半径 10 の円板(割ってはいけない)。
* 厚さ 3 px の棒(距離の最大 2 < h → 種が立たないはず。**種の無い塊はそのまま残す**を検算)。

【グラウンドトゥルース(すべて assert で落とす)】
1. ``blob_distance``: 各円板の中心の値 == 半径(22 / 16 / 10 ちょうど)、棒の最大 == 2、
   ``spacing=0.5`` で値がちょうど半分。
2. ``blob_seeds(h=4)``: 円板 3 つの種は「その山の高さ − h より高い画素」の集合と**画素単位で
   一致**(h-maxima の閉形式)。★実測(honest): 高さ 2 < h の棒にも種が立つ(棒の全画素 +
   背景 1 px の縁)。成分ごとに背景 0 で再構成すると M < h の成分は R = M − h < 0 になり
   残差 ``f − R > 0`` が全域で真になるため。実装は直さず報告し、例では棒の種を外して進む。
3. ``blob_split``: 結果は 4 領域。融合塊の 2 中心は別ラベル、棒と孤立円板は元のまま
   (画素単位)、前景の画素は 1 つも失われない。割れ目は 2 円の交線(くびれ)に乗るはずだが、
   ★実測(honest): 交線で分けた期待と 5 % 台(116 画素)食い違い、**番号の大きい種の側が
   谷に沿って数列ぶん食い込む**(大円板にしか属さない画素まで小円板側へ)。段ごとの膨張で
   両領域に触れた画素を max 番号に与える tie の偏りで、種番号を入れ替えると向きも逆になる。
   実装は直さず報告し、例は 10 % 未満で通す。
4. h を上げたときの融合: 教科書の h-maxima なら低い山のそびえ(16 − くびれ 10.07 = 5.93)を
   h が超えると種が 1 つになるが、★実測(honest): ``blob_seeds`` は残差 > 0 判定なので
   残差 = min(h, そびえ) > 0 が常に真で h=6 / 8 でも種は 2 つのまま。1 つになるのは
   「高い山 − くびれ(22 − 10.07 = 11.93)」を h が超えたとき(h=12.5 で 3 領域)。
   参照する山が逆なので、大きい塊についた小さいこぶを h で消す用途には効かない(報告のみ)。

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
    ids = (int(seeds[C1]), int(seeds[C2]), int(seeds[C3]))
    # ★実測(honest): 高さ 2 < h の棒にも種が立つ。blob_seeds は残差 ``f - R > 0`` を種にするが、
    # 成分ごとに背景 0 で再構成すると山の高さ M < h の成分は R = M - h < 0 になり、成分の
    # 全画素と背景 1 px の縁まで残差が正になる(skimage の h_maxima は ``残差 >= h`` で弾く)。
    # 実装は直さず報告する。ここでは棒の種を外して「種の無い塊」の経路を検算する。
    bar_seed_id = int(seeds[BAR][1, 30])
    bar_seed_px = int((seeds == bar_seed_id).sum()) if bar_seed_id > 0 else 0
    seeds_use = seeds.copy()
    if bar_seed_id > 0:
        seeds_use[seeds == bar_seed_id] = 0
    n_use = int(len(np.unique(seeds_use[seeds_use > 0])))
    seed_exact = np.array_equal(seeds_use > 0, seed_want)
    print(f"2) blob_seeds(h={h:g}): 種 {n_seeds} 個(期待 3: 棒は最大 2 < h なので立たないはず)、"
          f"中心の種番号 {ids}(全部違う)")
    print(f"   ★棒(高さ 2 < h)にも種 {bar_seed_px} 画素(棒 {int(bar.sum())} + 背景の縁 "
          f"{bar_seed_px - int(bar.sum())})—— 残差 > 0 判定の帰結。報告のみ、以下は棒の種を外して進める")
    print(f"   円板 3 つの種は h-maxima 閉形式(山の高さ - h より高い画素)と画素単位で一致 {seed_exact}")
    assert len(set(ids)) == 3 and min(ids) > 0 and n_use == 3 and seed_exact
    assert bar_seed_px > 0                              # この行が落ちたら上の挙動が直っている(報告を更新)

    # 3) 分水嶺で割る
    split = B.blob_split(lab, seeds_use, dist)
    n_split = int(split.max())
    l1, l2, l3, lb = int(split[C1]), int(split[C2]), int(split[C3]), int(split[BAR][1, 30])
    kept_bar = np.array_equal(split == lb, bar)
    kept_d3 = np.array_equal(split == l3, d3)
    no_loss = np.array_equal(split > 0, mask)
    region1, region2 = split == l1, split == l2
    mismatch = int(((region1 & side2) | (region2 & side1)).sum())
    invaded = int((region2 & d1 & ~d2).sum())            # 大円板にしか属さない画素が小円板側に
    pair_area = int((d1 | d2).sum())
    a1, a2 = int(region1.sum()), int(region2.sum())
    # ★実測(honest): 割れ目は交線に乗らず、**番号の大きい種の側が谷に沿って食い込む**。
    # blob_split は段ごとの膨張で「両方の領域に触れた画素」を grey_dilation の max(= 大きい番号)に
    # 与えるので、8 連結の斜め連鎖で番号の大きい領域が谷線に沿って数列ぶん侵入する。種番号を
    # 入れ替えると侵入の向きも入れ替わる(幾何ではなく番号の偏り)。実装は直さず報告する。
    swapped = seeds_use.copy()
    swapped[seeds_use == ids[0]] = ids[1]
    swapped[seeds_use == ids[1]] = ids[0]
    split_sw = B.blob_split(lab, swapped, dist)
    r1_sw, r2_sw = split_sw == split_sw[C1], split_sw == split_sw[C2]
    mismatch_sw = int(((r1_sw & side2) | (r2_sw & side1)).sum())
    invaded_sw = int((r1_sw & d2 & ~d1).sum())
    print(f"3) blob_split: {n_split} 領域(真値 4)、融合塊の 2 中心は別ラベル {l1 != l2}、"
          f"棒がそのまま {kept_bar}、孤立円板がそのまま {kept_d3}、前景を失わない {no_loss}")
    print(f"   割れ目: 交線 col={chord:.2f} で分けた期待と違う画素 {mismatch} / {pair_area}"
          f"({100.0 * mismatch / pair_area:.2f} %)、面積 {a1} / {a2}"
          f"(交線で分けた期待 {int(side1.sum())} / {int(side2.sum())})")
    print(f"   ★番号の大きい種(小円板 #{ids[1]})が大円板側へ食い込む: 大円板にしか属さない画素 {invaded} 個が"
          f"小円板の領域に。種番号を入れ替えると逆向きに {invaded_sw} 個(不一致 {mismatch_sw})—— "
          f"段ごとの膨張の tie が max 番号に倒れる偏り。報告のみ")
    assert n_split == 4 and l1 != l2 and kept_bar and kept_d3 and no_loss
    assert mismatch < 0.10 * pair_area                  # 観測 5 % 台。ゼロではないことを隠さない
    assert invaded > 0 and invaded_sw > 0               # 落ちたら偏りが直っている(報告を更新)

    # 4) h を上げると割れない(割りすぎ↔割り残しのつまみ)
    # ★実測(honest): 教科書の h-maxima なら「低いほうの山のそびえ(16 - くびれ 10.07 = 5.93)」
    # を h が超えた時点で種が 1 つに融合する。blob_seeds は残差 > 0 を種にするので、残差 =
    # min(h, そびえ) > 0 が常に成り立ち、低い山の種は h では消えない。融合するのは
    # 「高いほうの山 - くびれ(22 - 10.07 = 11.93)」を h が超えたとき —— 参照する山が逆。
    for h_try in (6.0, 8.0):
        s_try = B.blob_seeds(dist, h=h_try)
        s_try[bar] = 0
        s_try[~mask] = 0
        n_try = int(len(np.unique(s_try[(d1 | d2) & (s_try > 0)])))
        print(f"4) h={h_try:g}(そびえ 5.93 より大): 融合塊の種 {n_try} 個 —— 教科書なら 1 個。"
              f"blob_seeds は残差 > 0 判定なので 2 個のまま(報告のみ)")
        assert n_try == 2
    h_hi = 12.5                                         # 22 - 10.07 = 11.93 より大 → ようやく 1 個
    seeds_hi = B.blob_seeds(dist, h=h_hi)
    seeds_hi[bar] = 0                                   # 棒の種は上と同じ理由で外す
    seeds_hi[~mask] = 0                                 # 背景の縁に出た種も外す
    split_hi = B.blob_split(lab, seeds_hi, dist)
    n_pair_hi = int(len(np.unique(seeds_hi[(d1 | d2) & (seeds_hi > 0)])))
    print(f"   h={h_hi:g}(高い山 - くびれ 11.93 より大): 融合塊の種 {n_pair_hi} 個、"
          f"領域 {int(split_hi.max())} 個(融合塊は割れない)、2 中心は同じラベル {split_hi[C1] == split_hi[C2]}")
    assert n_pair_hi == 1 and int(split_hi.max()) == 3 and split_hi[C1] == split_hi[C2]

    return {"components_before": n0, "center_distances": vals[:3], "bar_max_distance": vals[3],
            "n_seeds_raw": n_seeds, "bar_seed_px": bar_seed_px, "seed_closed_form_exact": seed_exact,
            "n_regions": n_split, "bar_kept": kept_bar, "isolated_kept": kept_d3,
            "no_pixel_lost": no_loss, "chord_col": float(chord),
            "split_mismatch_px": mismatch, "pair_area_px": pair_area,
            "invaded_exclusive_px": invaded, "invaded_exclusive_px_swapped": invaded_sw,
            "areas": (a1, a2), "areas_want": (int(side1.sum()), int(side2.sum())),
            "elapsed_s": time.perf_counter() - t0}


def main():
    r = run()
    print(f"\nPASS: blob_distance(中心値=半径)/ blob_seeds(円板は h-maxima 閉形式と画素一致。h より低い棒にも"
          f"種が立つ・h で低い山を消せないのは報告)/ blob_split(4 領域・前景保存。割れ目は交線から "
          f"{100.0 * r['split_mismatch_px'] / r['pair_area_px']:.2f} % ずれ = 番号の偏り、報告)。"
          f" 実行 {r['elapsed_s']:.2f} 秒")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
