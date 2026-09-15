# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""aoi_frontend_tour — 外観検査の「測る前」の 3 段を、真値を植えた合成ラインで一巡する。

    py -3.11 examples/aoi_frontend_tour.py

【この例が示すこと】
検査ラインは画像から寸法・欠陥・位置ずれを**測る**が、その手前には必ず 3 段が入る:
照明ムラを戻す → 基準画像へ合わせる → タイルごとの量を地図にする。
この 3 段を ``aoi`` の 3 op で通し、**戻るはずの条件で戻ること**と、
**戻らないはずの条件で本当に戻らないこと**を対にして印字する。

【グラウンドトゥルース(すべて assert で落とす)】
1. 既知の cos⁴ ビネット(隅が中心の 0.196 倍)+ 暗電流 0.05 を掛けた絵が、
   ``flat_field_correct`` で**機械精度で元に戻る**(最大相対誤差 1.8e-16)。
   ★同じ絵から dark を省くと 2.3e-01 までしか戻らず、隅 / 中心の比は
   真値 0.1209 に対し 0.4867 のまま —— **絵は破綻しないので目では合格に見える**。
2. 既知の並進 (3, 5) px を ``register_image`` が回収し、残差 0.000000 / consistent=True。
   副画素 (2.5, -1.5) px も誤差 0.0000 px。
   ★回転 5 度を渡すと残差 0.6555 で **consistent=False**(小さい並進として返るが、
   「合っていない」と分かる量が一緒に返る)。
3. 周期 8 px の市松では答えが一意に決まらず ``ambiguous=True``(peak_ratio 1.0000)。
   ★縞は ``ambiguous=False`` のまま —— 尾根は山として数えられない、という正直な限界。
4. ``tiled_map`` の平均は分解可能なので、タイル統計から全体平均に戻る(誤差 0.0e+00)。
   端数のあるタイル(70 px を 16 px 角)も**捨てずに数え**、捨てる指定をしたときは
   ``dropped_tiles=9`` / ``covered_fraction=0.8360`` として返り値に残る。

【読み方】各節の印字は「真値 / 実測 / 差」。PASS 行が出れば全部通っている。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import aoi  # noqa: E402


def scene(n=128, seed=0):
    """勾配 + 円 + 棒 + 1 点 + 雑音。乱数だけの絵は対称性の破れを隠すので使わない。"""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    disk = (((yy - n * 0.35) ** 2 + (xx - n * 0.40) ** 2) < (n * 0.18) ** 2) * 0.35
    bar = np.zeros((n, n))
    bar[n // 2: n // 2 + 6, 10:n - 10] = 0.25
    spot = np.zeros((n, n))
    spot[n // 3, 2 * n // 3] = 0.6
    return np.clip(0.30 * (xx / (n - 1)) + disk + bar + spot
                   + 0.08 * rng.standard_normal((n, n)), 0.02, 1.0)


def corner_centre(a, n=128):
    c, k = slice(n // 2 - 8, n // 2 + 8), slice(0, 16)
    return float(a[k, k].mean() / a[c, c].mean())


def bilinear(img, sy, sx):
    n, m = img.shape
    y0 = np.clip(np.floor(sy).astype(int), 0, n - 2)
    x0 = np.clip(np.floor(sx).astype(int), 0, m - 2)
    fy, fx = np.clip(sy - y0, 0, 1), np.clip(sx - x0, 0, 1)
    return ((1 - fy) * (1 - fx) * img[y0, x0] + fy * (1 - fx) * img[y0 + 1, x0]
            + (1 - fy) * fx * img[y0, x0 + 1] + fy * fx * img[y0 + 1, x0 + 1])


def rotate(img, deg):
    n = img.shape[0]
    yy, xx = np.mgrid[0:n, 0:n].astype(float) - (n - 1) / 2.0
    t = np.deg2rad(deg)
    return bilinear(img, np.cos(t) * yy + np.sin(t) * xx + (n - 1) / 2.0,
                    -np.sin(t) * yy + np.cos(t) * xx + (n - 1) / 2.0)


def main() -> int:
    n = 128
    print("=" * 78)
    print("外観検査の前段 3 段 —— 照明を戻す / 位置を合わせる / タイルの地図にする")
    print("=" * 78)

    # ---------------------------------------------------------------- #
    # 1) 照明ムラを戻す                                                  #
    # ---------------------------------------------------------------- #
    print("\n1) flat_field_correct —— 既知の cos^4 ビネットを戻す")
    truth = scene(n, seed=3)
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    c = (n - 1) / 2.0
    rr = np.hypot(yy - c, xx - c) / (n / 2.0)
    vign = np.cos(np.arctan(rr * 0.8)) ** 4
    gain, dark = 0.9, 0.05
    flat = vign * gain + dark
    raw = truth * (vign * gain) + dark
    print("   仕込んだ感度ムラ: 隅 / 中心 = %.3f、暗電流 = %.2f" % (vign.min() / vign.max(), dark))

    good = aoi.flat_field_correct(raw, flat, dark=dark, target=1.0, clip=False)
    bad = aoi.flat_field_correct(raw, flat, dark=None, target=1.0, clip=False)
    e_good = float(np.abs(good - truth).max() / truth.max())
    e_bad = float(np.abs(bad - truth).max() / truth.max())
    print("   dark を渡す : 最大相対誤差 %.3e   隅/中心 %.4f(真値 %.4f)"
          % (e_good, corner_centre(good), corner_centre(truth)))
    print("   dark を省く : 最大相対誤差 %.3e   隅/中心 %.4f  ← 戻っていない"
          % (e_bad, corner_centre(bad)))
    print("   ★誤差の比 %.1e 倍。省いた側も絵としては破綻しないので、"
          "目では合格に見えて数字だけ狂う。" % (e_bad / e_good))
    assert e_good < 1e-12, e_good
    assert e_bad > 0.2, e_bad
    assert corner_centre(bad) > 3 * corner_centre(truth)

    # ---------------------------------------------------------------- #
    # 2) 基準画像へ合わせる                                              #
    # ---------------------------------------------------------------- #
    print("\n2) register_image —— 既知の並進を回収し、回転は「合っていない」と言う")
    ref = scene(n, seed=0)
    for dy, dx in ((3, 5), (-4, 2)):
        r = aoi.register_image(ref, np.roll(np.roll(ref, dy, 0), dx, 1))
        print("   整数 (%+d, %+d) -> (%+.3f, %+.3f) 残差 %.6f consistent=%s"
              % (dy, dx, r["dy"], r["dx"], r["residual"], r["consistent"]))
        assert abs(r["dy"] - dy) < 0.05 and abs(r["dx"] - dx) < 0.05
        assert r["consistent"] and r["residual"] < 1e-6

    for dy, dx in ((2.5, -1.5), (0.5, 0.0)):
        r = aoi.register_image(ref, aoi._shift_fourier(ref, dy, dx))
        err = float(np.hypot(r["dy"] - dy, r["dx"] - dx))
        print("   副画素 (%+.1f, %+.1f) -> (%+.3f, %+.3f) 誤差 %.4f px 残差 %.6f"
              % (dy, dx, r["dy"], r["dx"], err, r["residual"]))
        assert err < 0.05, err
        assert r["consistent"]

    rr5 = aoi.register_image(ref, rotate(ref, 5.0))
    print("   ★回転 5 度 -> (%+.3f, %+.3f) 残差 %.4f consistent=%s"
          % (rr5["dy"], rr5["dx"], rr5["residual"], rr5["consistent"]))
    print("     小さい並進として返るが、残差が跳ねるので黙って成功にはならない。")
    assert rr5["residual"] > 0.3 and rr5["consistent"] is False

    # 周期構造 —— 答えが 1 つに決まらない
    yy2, xx2 = np.mgrid[0:n, 0:n]
    check = (((xx2 // 8) + (yy2 // 8)) % 2).astype(float)
    stripe = ((xx2 // 8) % 2).astype(float)
    rc = aoi.register_image(check, np.roll(np.roll(check, 3, 0), 5, 1))
    rs = aoi.register_image(stripe, np.roll(np.roll(stripe, 3, 0), 5, 1))
    print("   市松 8px : peak_ratio %.4f ambiguous=%s  (周期 8 を法として等価な答えが並ぶ)"
          % (rc["peak_ratio"], rc["ambiguous"]))
    print("   ★縞 8px  : peak_ratio %.4f ambiguous=%s dy=%+.3f"
          % (rs["peak_ratio"], rs["ambiguous"], rs["dy"]))
    print("     縞は dy が原理的に決まらないのに ambiguous に掛からない —— peak_ratio は")
    print("     離れた 2 番目の『山』を見る量で、縞が作るのは『尾根』だから。正直な限界。")
    assert rc["ambiguous"] is True and rc["peak_ratio"] > 0.9
    assert rs["ambiguous"] is False and abs(rs["dy"]) < 0.1

    # ---------------------------------------------------------------- #
    # 3) タイルごとの量を地図にする                                      #
    # ---------------------------------------------------------------- #
    print("\n3) tiled_map —— 半端なタイルを黙って捨てない")
    img = scene(64, seed=7)
    t = aoi.tiled_map(img, tile=16, stat="mean")
    w = float((t["map"] * t["counts"]).sum() / t["counts"].sum())
    print("   64px / 16px 角: 地図 %s 端数 %d 枚 覆い %.4f"
          % (t["map"].shape, t["partial_tiles"], t["covered_fraction"]))
    print("   タイル平均から戻した全体平均 %.12f / 全画素の平均 %.12f / 差 %.1e"
          % (w, img.mean(), abs(w - img.mean())))
    assert abs(w - float(img.mean())) < 1e-12

    ragged = scene(70, seed=7)
    tr = aoi.tiled_map(ragged, tile=16, stat="mean")
    td = aoi.tiled_map(ragged, tile=16, stat="mean", drop_partial=True)
    wr = float((tr["map"] * tr["counts"]).sum() / tr["counts"].sum())
    print("   70px / 16px 角(端数あり): 地図 %s 端数 %d 枚 覆い %.4f 全体平均の差 %.1e"
          % (tr["map"].shape, tr["partial_tiles"], tr["covered_fraction"],
             abs(wr - ragged.mean())))
    print("   ★捨てる指定: 地図 %s 捨てた %d 枚 覆い %.4f —— 捨てたことが返り値に残る"
          % (td["map"].shape, td["dropped_tiles"], td["covered_fraction"]))
    assert tr["partial_tiles"] == 9 and abs(wr - float(ragged.mean())) < 1e-12
    assert td["dropped_tiles"] == 9 and td["covered_fraction"] < 1.0

    ts = aoi.tiled_map(img, tile=16, stat="std")
    ws = float((ts["map"] * ts["counts"]).sum() / ts["counts"].sum())
    print("   ★std はまとめ直せない: タイル std の平均 %.6f / 全体 std %.6f"
          % (ws, img.std()))
    assert abs(ws - float(img.std())) > 0.01

    big = aoi.tiled_map(img, tile=200, stat="mean")
    print("   タイルが画像より大きい: 地図 %s 端数 %d 枚 値 %.6f(= 全体平均)"
          % (big["map"].shape, big["partial_tiles"], big["map"][0, 0]))
    assert big["map"].shape == (1, 1) and big["partial_tiles"] == 1

    # 「走った」!= 「意味のある出力」
    for name, arr in (("flat_field", good), ("tiled_map", t["map"])):
        assert np.isfinite(arr).all() and float(np.ptp(arr)) > 0.0, name

    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
