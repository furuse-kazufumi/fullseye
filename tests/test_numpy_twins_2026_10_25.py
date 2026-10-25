# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""門: ``numpy_twins`` の各関数は scikit-image の同名関数と **bit 一致**(浮動小数は 4 ULP かつ 1e-12 以内)。

登録 op 単位の門(``tests/test_fallback_parity_2026_10_25.py``)は coins と合成画像の 2 枚 × ノブ 2 点しか見ない。
こちらは双子を関数単位で、乱数の塊(円・矩形・雑音・帯)を何十枚も流して実物と突き合わせる —— 探針 1 枚は網羅では
ない。scikit-image が無い環境では比べる相手が居ないので理由つきで skip する。
"""
from __future__ import annotations

import numpy as np
import pytest

skimage = pytest.importorskip("skimage", reason="双子の比較相手(scikit-image)が無い")
import skimage.feature as skfe  # noqa: E402
import skimage.filters as skf  # noqa: E402
import skimage.measure as skme  # noqa: E402
import skimage.morphology as skm  # noqa: E402
from scipy import ndimage  # noqa: E402

import numpy_twins as nt  # noqa: E402

LEDGER_ULP, LEDGER_ABS = 4, 1e-12


def _ulp(a, b):
    a = np.atleast_1d(np.asarray(a, np.float64))
    b = np.atleast_1d(np.asarray(b, np.float64))
    assert a.shape == b.shape
    both_nan = np.isnan(a) & np.isnan(b)
    d = np.abs(a.view(np.int64) - b.view(np.int64))
    d[both_nan] = 0
    ad = np.abs(a - b)
    ad[both_nan] = 0
    return int(d.max()), float(ad.max())


def _close(a, b):
    u, d = _ulp(a, b)
    assert u <= LEDGER_ULP and d <= LEDGER_ABS, (u, d)


def _blobs(rng, n=64, k=5):
    m = np.zeros((n, n), bool)
    yy, xx = np.ogrid[:n, :n]
    for _ in range(k):
        cy, cx, r = rng.integers(5, n - 5), rng.integers(5, n - 5), rng.integers(2, 12)
        m |= (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r
    for _ in range(2):
        y0, x0 = rng.integers(0, n - 20, 2)
        m[y0:y0 + rng.integers(2, 15), x0:x0 + rng.integers(2, 15)] = True
    return m


def _masks(seed, count):
    rng = np.random.default_rng(seed)
    for i in range(count):
        m = _blobs(rng)
        if i % 5 == 1:
            m = rng.random(m.shape) > 0.55                      # 雑音(細い橋と穴が多い)
        if i % 7 == 2:
            m[:, :] = True
            m[10:20, :] = False                                 # 画像の縁に接する帯
        if i % 11 == 3:
            m[:] = False
            m[30, 10:50] = True                                 # 1 画素幅の線
        yield m


def _largest(m):
    lab, n = ndimage.label(m)
    assert n > 0
    return lab == (np.argmax(np.bincount(lab.ravel())[1:]) + 1)


def test_disk_matches_for_every_radius_the_ops_use():
    for r in range(1, 8):
        assert np.array_equal(nt.disk(r), skm.disk(r))
        assert nt.disk(r).dtype == skm.disk(r).dtype


def test_threshold_otsu_and_hysteresis_match_bit_for_bit():
    rng = np.random.default_rng(1)
    for i in range(40):
        img = np.clip(rng.normal(0.5, 0.2, (37, 53)) + (rng.random((37, 53)) > 0.7) * 0.3, 0, 1)
        if i % 9 == 0:
            img = img.astype(np.float32)
        assert nt.threshold_otsu(img) == skf.threshold_otsu(img)
        assert np.array_equal(nt.apply_hysteresis_threshold(img, 0.3, 0.6), skf.apply_hysteresis_threshold(img, 0.3, 0.6))
    flat = np.full((5, 5), 0.3)
    assert nt.threshold_otsu(flat) == skf.threshold_otsu(flat)


def test_skeletonize_and_thin_match_bit_for_bit():
    for m in _masks(2, 60):
        assert np.array_equal(nt.skeletonize(m), skm.skeletonize(m))
        assert np.array_equal(nt.thin(m), skm.thin(m))
    sq = np.zeros((7, 7), bool)
    sq[1:6, 1:6] = True                                          # 5x5 の正方形: Zhang–Suen は非対称な L を残す
    assert np.array_equal(nt.skeletonize(sq), skm.skeletonize(sq))


def test_remove_small_holes_perimeter_euler_match():
    for i, m in enumerate(_masks(3, 50)):
        thr = (16, 40, 100, 216)[i % 4]
        assert np.array_equal(nt.remove_small_holes(m, thr), skm.remove_small_holes(m, area_threshold=thr))
        _close(nt.perimeter(m, 4), skme.perimeter(m, 4))
        assert nt.euler_number(m) == skme.euler_number(m)
        assert nt.euler_number(m, connectivity=1) == skme.euler_number(m, connectivity=1)


def test_region_twin_matches_regionprops_on_every_attribute_the_ops_read():
    for m in _masks(4, 60):
        big = _largest(m)
        pr = skme.regionprops(big.astype(int))[0]
        tw = nt.RegionTwin(big)
        assert tw.bbox == pr.bbox
        for attr in ("area", "area_filled", "perimeter", "orientation", "axis_major_length", "axis_minor_length",
                     "inertia_tensor", "moments_central", "centroid_local", "moments"):
            _close(getattr(tw, attr), getattr(pr, attr))
        assert tw.moments.dtype == pr.moments.dtype
    with pytest.raises(Exception, match="not installed|convex"):
        _ = nt.RegionTwin(big).area_convex


def test_moments_path_used_by_the_moment_ops_matches():
    for m in _masks(5, 40):
        big = _largest(m).astype(float)
        nu1 = nt.moments_normalized(nt.moments_central(big))
        nu2 = skme.moments_normalized(skme.moments_central(big))
        _close(np.nan_to_num(nu1), np.nan_to_num(nu2))
        _close(nt.moments_hu(nu1), skme.moments_hu(nu2))


def test_graycomatrix_and_props_match():
    rng = np.random.default_rng(6)
    for _ in range(12):
        xq = rng.integers(0, 16, (30, 41)).astype(np.uint8)
        for d in (1, 2, 3, 4):
            for angles in ([0.0], [0.0, np.pi / 4, np.pi / 2, 3 * np.pi / 4]):
                g1 = nt.graycomatrix(xq, [d], angles, levels=16, symmetric=True, normed=True)
                g2 = skfe.graycomatrix(xq, [d], angles, levels=16, symmetric=True, normed=True)
                assert np.array_equal(g1, g2)
                for prop in ("energy", "contrast", "dissimilarity", "homogeneity", "correlation", "ASM"):
                    _close(nt.graycoprops(g1, prop), skfe.graycoprops(g2, prop))


def test_corner_harris_and_foerstner_match():
    rng = np.random.default_rng(7)
    for _ in range(8):
        img = rng.random((45, 61))
        for s in (0.5, 1.0, 1.3, 2.5):
            _close(nt.corner_harris(img, sigma=s), skfe.corner_harris(img, sigma=s))
            w1, q1 = nt.corner_foerstner(img, sigma=s)
            w2, q2 = skfe.corner_foerstner(img, sigma=s)
            _close(np.nan_to_num(w1), np.nan_to_num(w2))
            _close(np.nan_to_num(q1), np.nan_to_num(q2))
