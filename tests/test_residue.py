# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""residue — 中国剰余定理の op の厳密な真値と fail-closed を検査する。

真値は 4 種類: (1) 定理そのもの(整数 CRT = 総当たり、任意精度)、(2) 実数版は整数入力で
整数版と 1 ビットも違わない、(3) robust CRT の保証(剰余の誤差 < Γ/4 なら厳密に復元)、
(4) 画像 op は解析的に作った絵(純音の重ね合わせの巡回シフト、解析的に描いた部品の回転)。
乱数は使わない —— 誤差は構造的な並び(±一定、交互)で与える。
"""
from __future__ import annotations

import numpy as np
import pytest

import residue as R


# ---- 1. 定理 ------------------------------------------------------------------
def test_integer_crt_equals_brute_force_over_the_whole_range():
    m = [7, 9, 11]
    for v in range(7 * 9 * 11):
        assert R.residue_integer_crt([v % x for x in m], m)["value"] == v


def test_integer_crt_is_exact_beyond_float_precision_and_mixed_radix_rebuilds_it():
    m = [101, 103, 107, 109, 113, 127, 131, 137, 139, 149]
    P = 1
    for x in m:
        P *= x
    v = P - 987654321                       # > 2**53: a float could not hold it
    out = R.residue_integer_crt([v % x for x in m], m)
    assert out["value"] == v and out["modulus"] == P
    assert len(out["mixed_radix"]) == len(m)
    acc, place = 0, 1
    for d, x in zip(out["mixed_radix"], m):
        assert 0 <= d < x
        acc += d * place
        place *= x
    assert acc == v


@pytest.mark.parametrize("res,mod", [([1, 2], [6, 9]), ([1], [1]), ([1.5, 2], [7, 9]), ([1, 2], [7])])
def test_integer_crt_refuses_non_coprime_trivial_fractional_or_ragged(res, mod):
    with pytest.raises(ValueError):
        R.residue_integer_crt(res, mod)


# ---- 2. 実数版 = 整数版 --------------------------------------------------------
def test_real_crt_reproduces_the_integer_crt_bit_for_bit():
    m = np.array([7, 9, 11])
    v = np.arange(693)
    out = R.residue_crt((v[None] % m[:, None]).astype(float), m)
    assert np.array_equal(out["value"], v.astype(float))
    assert out["unambiguous_range"] == 693.0
    assert np.all(out["score"] == 1.0)


# ---- 3. robust CRT の保証 ------------------------------------------------------
@pytest.mark.parametrize("pattern", [(+1, +1, +1), (+1, -1, +1), (-1, +1, -1), (-1, -1, +1)])
def test_errors_below_quarter_gamma_are_absorbed(pattern):
    # periods Γ*M_i with Γ = 2, M = (3, 5, 7): any residue error < Γ/4 = 0.5 is absorbed
    p = np.array([6.0, 10.0, 14.0])
    v = np.linspace(0.3, 209.7, 400)
    err = 0.49 * np.array(pattern, float)[:, None]
    out = R.residue_crt((v[None] + err) % p[:, None], p, lo=0.0, hi=210.0)
    # compared on the circle of length 210: a value pushed past the end of the range wraps to its start
    assert np.abs((out["value"] - v + 105.0) % 210.0 - 105.0).max() < 0.49 + 1e-9


def test_a_band_with_zero_weight_has_no_vote():
    p = np.array([7.0, 9.0, 11.0, 13.0])
    v = np.array([123.4])
    r = (v[None] % p[:, None]).copy()
    r[2] = (r[2] + 5.0) % 11.0                     # garbage in band 2 ...
    w = np.array([1.0, 1.0, 0.0, 1.0])             # ... but it carries no contrast
    out = R.residue_crt(r, p, w, lo=0, hi=693)
    assert abs(out["value"][0] - 123.4) < 1e-9


def test_range_wider_than_the_lcm_is_refused_and_incommensurate_needs_hi():
    with pytest.raises(ValueError, match="unambiguous"):
        R.residue_crt([1.0, 2.0], [7.0, 9.0], lo=0, hi=64)
    with pytest.raises(ValueError, match="commensurate"):
        R.residue_crt([1.0, 2.0], [7.0, np.pi])
    out = R.residue_crt([1.0, 2.0], [7.0, np.pi], lo=0, hi=20)  # explicit range is accepted
    assert np.isfinite(out["value"]).all()


@pytest.mark.parametrize("kw", [dict(residues=[1.0, np.nan], periods=[7, 9]),
                                dict(residues=[1.0, 2.0], periods=[7, -9]),
                                dict(residues=[1.0, 2.0], periods=[7]),
                                dict(residues=[1.0, 2.0, 3.0], periods=[7, 9]),
                                dict(residues=[1.0, 2.0], periods=[7, 9], weights=[1, -1])])
def test_residue_crt_fails_closed(kw):
    with pytest.raises(ValueError):
        R.residue_crt(**kw)


# ---- RRNS: 犯人探し ------------------------------------------------------------
def _corrupt(v, p, band, shift):
    r = (v[None] % p[:, None]).copy()
    r[band] = (r[band] + shift * p[band]) % p[band]
    return r


@pytest.mark.parametrize("band", [0, 1, 2, 3])
def test_fault_locate_names_the_corrupted_band_and_recovers_the_value(band):
    p = np.array([7.0, 9.0, 11.0, 13.0])
    v = np.array([-31.5, -2.25, 0.0, 17.75, 38.5])
    fl = R.residue_fault_locate(_corrupt(v, p, band, 0.5), p, lo=-40, hi=40)
    named = fl["faulty"] == band
    # it may decline (-2) but must never blame another band, and must name most
    assert np.all(named | (fl["faulty"] == -2))
    assert named.sum() >= 4
    assert np.allclose(fl["value"][named], v[named])


def test_fault_locate_reports_no_fault_when_all_agree():
    p = np.array([7.0, 9.0, 11.0, 13.0])
    v = np.array([5.0, -12.5])
    fl = R.residue_fault_locate(v[None] % p[:, None], p, lo=-40, hi=40)
    assert np.all(fl["faulty"] == -1) and np.all(fl["consistent_all"])


def test_fault_locate_says_undecidable_rather_than_guessing():
    # two bands corrupted: no single removal is consistent -> -2 and NaN, never a band index
    p = np.array([7.0, 9.0, 11.0, 13.0])
    v = np.array([10.0])
    r = _corrupt(v, p, 0, 0.5)
    r[2] = (r[2] + 0.4 * 11.0) % 11.0
    fl = R.residue_fault_locate(r, p, lo=-40, hi=40)
    assert fl["faulty"][0] == -2 and np.isnan(fl["value"][0])


def test_fault_locate_needs_three_bands_and_a_sane_tolerance():
    with pytest.raises(ValueError):
        R.residue_fault_locate([1.0, 2.0], [7.0, 9.0])
    with pytest.raises(ValueError):
        R.residue_fault_locate([1.0, 2.0, 3.0], [7.0, 9.0, 11.0], tol=0.3)


# ---- 4. 画像 op ----------------------------------------------------------------
# wavelengths with a whole number of cycles across the 96 x 192 test image (192/27 ... 192/15, and
# 96/13 ... 96/7 down the rows), so the circular shift has no seam; still about 7..13 px, and
# their least common multiple (192 px) covers the +-40 px search
_PER = tuple(192.0 / np.array([27, 21, 17, 15]))
_PER_Y = tuple(96.0 / np.array([13, 11, 9, 7]))


def _tones(shape):
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]].astype(float)
    out = np.zeros(shape)
    for i, p in enumerate(_PER):
        out += np.cos(2 * np.pi * xx / p + 0.7 * i)
    for i, p in enumerate(_PER_Y):
        out += np.cos(2 * np.pi * yy / p + 1.3 * i)
    return out


def _shift(img, dx=0.0, dy=0.0):
    # exact circular sub-pixel shift (Fourier phase ramp): consistent with the op's FFT band-pass,
    # so the only error left is the method's own
    F = np.fft.fft2(img)
    fu = np.fft.fftfreq(img.shape[1])[None, :]
    fv = np.fft.fftfreq(img.shape[0])[:, None]
    return np.real(np.fft.ifft2(F * np.exp(-2j * np.pi * (fu * dx + fv * dy))))


@pytest.mark.parametrize("d", [-23.5, -6.0, 0.0, 4.25, 17.3, 31.0])
def test_displacement_beyond_the_single_band_wrap_limit(d):
    a = _tones((96, 192))
    b = _shift(a, dx=d)
    o = R.crt_displacement(a, b, periods=_PER, sigma_px=25.0, max_disp=40.0)
    core = o["d"][30:-30, 40:-40]
    assert o["wrap_limit_single_px"] == max(_PER) / 2.0
    assert np.abs(core - d).max() < 0.02, (d, np.abs(core - d).max())


def test_displacement_along_y_is_the_transpose_of_x():
    a = _tones((96, 192))
    b = _shift(a, dy=-14.0)
    o = R.crt_displacement(a, b, periods=_PER_Y, sigma_px=25.0, max_disp=40.0, axis="y")
    assert np.abs(o["d"][30:-30, 40:-40] + 14.0).max() < 0.02


@pytest.mark.parametrize("kw", [dict(max_disp=400.0, periods=(7.0, 9.0)),   # 2*400 > lcm 63
                                dict(periods=(1.5, 9.0)),
                                dict(axis="z"), dict(sigma_px=1.0), dict(refine=-1)])
def test_displacement_fails_closed(kw):
    a = _tones((64, 64))
    with pytest.raises(ValueError):
        R.crt_displacement(a, a, **kw)


def _part(theta_deg, n=121, ss=3):
    c = (n - 1) / 2.0
    g = (np.arange(n * ss) + 0.5) / ss - 0.5
    X, Y = np.meshgrid(g - c, g - c)
    r = np.hypot(X, Y)
    a = np.arctan2(-Y, X) - np.radians(theta_deg)
    img = ((r > 10) & (r < 18) & (np.cos(3 * a) > 0.3)).astype(float)
    img += ((r > 22) & (r < 30) & (np.cos(4 * a) > 0.0)).astype(float)
    img += ((r > 34) & (r < 42) & (np.cos(5 * a) < 0.6)).astype(float)
    return img.reshape(n, ss, n, ss).mean((1, 3))


_RINGS = ((10, 18), (22, 30), (34, 42))


@pytest.mark.parametrize("theta", [0.0, 7.5, 89.0, 133.3, 211.0, 359.0])
def test_rotation_is_recovered_over_the_full_circle(theta):
    o = R.harmonic_rotation(_part(theta), _part(0.0), rings=_RINGS)
    err = abs((o["angle_deg"] - theta + 180.0) % 360.0 - 180.0)
    assert err < 0.2, (theta, o["angle_deg"])
    assert o["suspect"] == -1


def test_each_order_alone_is_ambiguous_but_together_they_are_not():
    o = R.harmonic_rotation(_part(250.0), _part(0.0), rings=_RINGS)
    assert len(o["per_order_deg"]) == 3
    for n, per_order in zip((3, 4, 5), o["per_order_deg"]):
        assert abs(per_order - (250.0 % (360.0 / n))) < 0.2       # each ring: angle mod 360/n
    assert abs(o["angle_deg"] - 250.0) < 0.2


def test_rotation_matches_scipy_rotate_convention():
    from scipy.ndimage import rotate
    ref = _part(0.0)
    o = R.harmonic_rotation(rotate(ref, 40.0, reshape=False, order=3), ref, rings=_RINGS)
    assert abs(o["angle_deg"] - 40.0) < 0.3


@pytest.mark.parametrize("kw", [dict(orders=(2, 4), rings=((10, 18), (22, 30))),     # gcd 2
                                dict(rings=((10, 18), (22, 30), (34, 70))),           # leaves image
                                dict(orders=(3, 4), rings=_RINGS)])                   # count mismatch
def test_rotation_fails_closed(kw):
    with pytest.raises(ValueError):
        R.harmonic_rotation(_part(10.0), _part(0.0), **kw)


# ---- 台帳 ----------------------------------------------------------------------
def test_ledger_matches_module_and_is_reachable():
    import opsresidue
    assert opsresidue.missing() == []
    assert sorted(opsresidue.list_ops()) == sorted(R.__all__)
    import fullseye as fs
    assert len(R.__all__) == 5
    for name in R.__all__:
        assert callable(getattr(fs.ledger, name))
