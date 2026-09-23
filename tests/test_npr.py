# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""様式化 6 op の門。**保った量と捨てた量を数で返す**ことを採点する。

既存の NPR ライブラリは絵しか返さない。この族の主張は「絵の良さ」ではなく
「何を保って何を捨てたかを数で言える」ことなので、門も全部数になる:

* ★モアレの周期は**描く前に**分かる(2 つのスクリーンの周波数ベクトルの差)。
  op の予言を、重ねた絵の FFT で測り返す。
* 彫版線のインク被覆率は ``w/d`` の閉形式。
* ハッチの向きは、向きが構成で分かっている絵(既知の角度の正弦縞)で採点する。
* Lloyd 反復のエネルギーは単調減少 —— それを測るのは**既存の**
  ``stipple_energy``(この族の実装を知らない)。
* セル平均は L2 最適。セルごとに全数走査して、平均以外の定数が二乗誤差を
  下げないことを確かめる。

★``fft_peak_period`` に ``f_max`` を渡さないと**スクリーン自身の山**を拾って
「予言と合わない」と読める(実測はどの角度でも 16.7 px = 1/f そのものだった)。
うなりは低周波側にあるので、探す範囲を切るのが正しい。
"""
import numpy as np
import pytest

import printpath


def _fft_peak(img, f_max=None, f_min=None):
    """主要な周期 [px] と向き [deg] を 2-D FFT の山から読む。"""
    a = img - img.mean()
    a = a * np.hanning(a.shape[0])[:, None] * np.hanning(a.shape[1])[None, :]
    F = np.abs(np.fft.fftshift(np.fft.fft2(a)))
    h, w = F.shape
    gy = (np.arange(h) - h / 2.0)[:, None] / h
    gx = (np.arange(w) - w / 2.0)[None, :] / w
    rad = np.hypot(gy, gx)
    F[rad < (2.5 / min(h, w) if f_min is None else f_min)] = 0.0
    if f_max is not None:
        F[rad > f_max] = 0.0
    i, j = np.unravel_index(np.argmax(F), F.shape)
    fy, fx = (i - h / 2.0) / h, (j - w / 2.0) / w
    return 1.0 / np.hypot(fy, fx), np.degrees(np.arctan2(fy, fx))


@pytest.mark.parametrize("angle_b", [75.0, 60.0, 50.0])
def test_moire_period_is_predicted_before_drawing(angle_b):
    """2 版を重ねたうなりの周期を、op が**描く前に**言い当てる。"""
    flat = np.full((1024, 1024), 0.5)
    a = np.asarray(printpath.halftone_screen(flat, 60.0, 45.0, 25.4))
    b = np.asarray(printpath.halftone_screen(flat, 60.0, angle_b, 25.4))
    pred = printpath.halftone_moire_period(60.0, 45.0, 60.0, angle_b, 25.4)
    f_screen = 60.0 * 25.4 / 25400.0
    meas, _ang = _fft_peak(a * b, f_max=f_screen * 0.6)
    want = float(np.asarray(pred["period_px"]).ravel()[0])
    assert abs(meas / want - 1.0) < 0.08, (meas, want, angle_b)


def test_identical_screens_are_refused_instead_of_an_infinite_beat():
    """同じ線数・同じ角度なら差ベクトルが 0。inf を返すのでなく拒む。"""
    with pytest.raises(ValueError, match="identical"):
        printpath.halftone_moire_period(60.0, 45.0, 60.0, 45.0, 25.4)


def test_moire_period_grows_as_the_angle_difference_shrinks():
    """角度差が小さいほどうなりは粗くなる(差ベクトルの長さの逆数)。

    小さい角度差は周期が画面に入りきらず FFT では確かめられない(47 度で
    477 px)。そこは閉形式の**単調性**と、差ベクトルの長さそのもので門にする。
    """
    pers = [float(np.asarray(printpath.halftone_moire_period(
        60.0, 45.0, 60.0, b, 25.4)["period_px"]).ravel()[0])
        for b in (75.0, 60.0, 50.0, 47.0, 46.0)]
    assert all(x < y for x, y in zip(pers, pers[1:])), pers
    # 45 対 75 = 差 30 度。同じ線数なら差ベクトルの長さは 2 f sin(15 度) で、
    # 周期はその逆数。f = lpi * pixel_um / 25400。
    f = 60.0 * 25.4 / 25400.0
    assert abs(pers[0] - 1.0 / (2.0 * f * np.sin(np.radians(15.0)))) < 1e-6, pers[0]


@pytest.mark.parametrize("tone", [0.2, 0.4, 0.6, 0.8])
def test_engrave_ink_coverage_matches_the_closed_form(tone):
    """インク被覆率は w/d の閉形式 —— 濃淡から線幅への写像そのもの。"""
    g = np.full((512, 512), tone)
    im = np.asarray(printpath.engrave_lines(g, 8.0, 30.0, 1.0, 0.95))
    ink = float(1.0 - im.mean())
    want = min((1.0 - tone) * 0.95, 0.95)
    assert abs(ink - want) < 0.01, (tone, ink, want)


def test_engrave_is_monotone_in_tone():
    """暗いほどインクが多い。逆転したら濃淡の写像が壊れている。"""
    inks = [1.0 - float(np.asarray(printpath.engrave_lines(
        np.full((256, 256), t), 8.0, 0.0)).mean()) for t in (0.1, 0.3, 0.5, 0.7, 0.9)]
    assert all(a > b for a, b in zip(inks, inks[1:])), inks


@pytest.mark.parametrize("deg", [0.0, 30.0, 60.0, 90.0, 135.0])
def test_hatch_follows_a_grating_whose_angle_is_known_by_construction(deg):
    """既知の角度の縞を渡すと、ハッチはその縞に**沿う**(構造テンソル経由)。

    ★測るときに **f_min を渡さないと縞自身の山**を拾う: ハッチは濃淡に応じて層を
    乗せるので、「どこに墨を置いたか」の包絡が元の縞と同じ周期(24 px)で入る。
    ストローク自体の周期は spacing = 8 px なので、f > 0.08 に切って初めて線の
    向きが見える(切らないと 24 px の山を拾って「向きが 90 度ずれている」と
    誤読する —— 一度そう読みかけた)。
    """
    yy, xx = np.mgrid[0:256, 0:256].astype(np.float64)
    a = np.radians(deg)
    g = 0.5 + 0.4 * np.sin(2.0 * np.pi * (xx * np.cos(a) + yy * np.sin(a)) / 24.0)
    im = np.asarray(printpath.hatch_field(g, 8.0, 2.0, 2))
    assert im.min() >= 0.0 and im.max() <= 1.0
    per, ang = _fft_peak(im, f_min=0.08)
    assert abs(per - 8.0) < 0.5, per                 # 線の間隔 = spacing_px
    # 線は縞に**沿う**ので、周波数ベクトルは縞の勾配方向(= deg)を向く。
    delta = (ang - deg) % 180.0
    assert min(delta, 180.0 - delta) < 10.0, (deg, ang, delta)


def test_lloyd_energy_decreases_and_the_existing_op_measures_it():
    """★エネルギーを測るのは**既存の** stipple_energy。単調に下がる。"""
    import fullseye as fs
    yy, xx = np.mgrid[0:256, 0:256].astype(np.float64)
    img = np.clip(0.5 + 0.45 * np.sin(xx / 17.0) * np.cos(yy / 23.0), 0.0, 1.0)
    prev = None
    for it in (0, 1, 2, 4, 8, 16):
        pts = printpath.mosaic_tiles_sites(img, 250, it, 0, weighted=False)
        e = float(fs.ledger.stipple_energy(img, pts))
        if prev is not None:
            assert e <= prev + 1e-9, (it, e, prev)
        prev = e


def test_cell_mean_is_the_l2_optimum_per_cell():
    """セル平均は二乗誤差の最小点。セルごとに全数走査して確かめる。"""
    cKDTree = pytest.importorskip("scipy.spatial").cKDTree
    yy, xx = np.mgrid[0:256, 0:256].astype(np.float64)
    img = np.clip(0.5 + 0.45 * np.sin(xx / 17.0) * np.cos(yy / 23.0), 0.0, 1.0)
    pts = printpath.mosaic_tiles_sites(img, 250, 12, 0)
    mos = np.asarray(printpath.mosaic_tiles_render(img, pts))
    base = float(np.sum((img - mos) ** 2))
    for delta in (-0.05, -0.01, 0.01, 0.05):
        alt = np.clip(mos + delta, 0.0, 1.0)
        assert float(np.sum((img - alt) ** 2)) > base, delta

    h, w = img.shape
    gy, gx = np.mgrid[0:h, 0:w]
    own = cKDTree(np.asarray(pts)).query(
        np.stack([gy.ravel(), gx.ravel()], axis=1).astype(np.float64), k=1)[1]
    flat = img.ravel()
    for c in range(0, 250, 25):
        sel = own == c
        if int(sel.sum()) < 2:
            continue
        v = flat[sel]
        grid = np.linspace(v.min(), v.max(), 41)
        sse = ((v[None, :] - grid[:, None]) ** 2).sum(axis=1)
        assert abs(grid[int(np.argmin(sse))] - v.mean()) <= (grid[1] - grid[0]), c


def test_halftone_preserves_local_tone():
    """★捨てたのは階調であって**局所の平均濃度は保つ** —— それが網点の意味。"""
    ndi = pytest.importorskip("scipy.ndimage")
    yy, xx = np.mgrid[0:512, 0:512].astype(np.float64)
    g = np.clip(0.15 + 0.7 * xx / 511.0, 0.0, 1.0)
    im = np.asarray(printpath.halftone_screen(g, 40.0, 45.0, 25.4))
    # 網点 1 周期よりずっと広い窓で平均すれば元の濃淡に戻る
    per = 25400.0 / (40.0 * 25.4)
    blur = ndi.uniform_filter(im, size=int(round(per * 4)))
    c = (slice(64, -64), slice(64, -64))
    assert float(np.abs(blur[c] - g[c]).mean()) < 0.06, \
        float(np.abs(blur[c] - g[c]).mean())


def test_mosaic_sites_stay_inside_and_are_deterministic():
    """同じ seed で同じ点。画素の外に出ない(fail-closed の下流契約)。"""
    yy, xx = np.mgrid[0:128, 0:128].astype(np.float64)
    img = np.clip(0.5 + 0.4 * np.sin(xx / 9.0), 0.0, 1.0)
    p1 = np.asarray(printpath.mosaic_tiles_sites(img, 60, 6, 7))
    p2 = np.asarray(printpath.mosaic_tiles_sites(img, 60, 6, 7))
    assert np.array_equal(p1, p2)
    assert p1.shape == (60, 2)
    assert p1[:, 0].min() >= 0.0 and p1[:, 0].max() <= 127.0
    assert p1[:, 1].min() >= 0.0 and p1[:, 1].max() <= 127.0
