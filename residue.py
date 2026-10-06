# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""residue — values known only modulo several periods, recovered by the Chinese remainder theorem.

A phase measures a quantity only *modulo its period*: the local phase of a 9 px
texture band tells a displacement modulo 9 px, the 4th circular harmonic of a part
tells its rotation modulo 90 degrees, a fringe of period p tells depth modulo p.
One period alone is ambiguous. Several periods with no common structure are not:
the residues ``v mod p_i`` pin ``v`` down over the least common multiple of the
periods — the Chinese remainder theorem (CRT). The same arithmetic is what lets
Ozaki scheme II rebuild an exact FP64 matrix product from INT8 products modulo
several small integers (Ozaki, Uchino & Imamura, arXiv:2504.08009).

This module carries that idea into images. Every op returns not only the value but
how it was reached (per-band residuals, the score margin over the runner-up
candidate) so that a wrong unwrap is visible rather than silent.

Ops
---
``residue_integer_crt``   exact integer CRT (Garner, arbitrary precision) —
                          the theorem itself, the oracle for the rest.
``residue_crt``           real-valued, weighted (amplitude = reliability) robust
                          CRT over phases of any real periods, vectorised per sample.
``residue_fault_locate``  redundant residue number system (RRNS): with more bands
                          than the range needs, find *which* band is corrupted
                          and solve without it — or say it cannot tell.
``crt_displacement``      local displacement between two images from band phases
                          at coprime wavelengths: passes the half-wavelength
                          wrap limit that bounds any single-band phase method
                          (see ``motionmag.phase_displacement``).
``harmonic_rotation``     absolute in-plane rotation over the full 360 degrees from
                          circular harmonics of orders whose symmetries are each
                          ambiguous (order n alone gives the angle modulo 360/n).

Provenance (public literature only): Chinese remainder theorem, Garner 1959
(mixed-radix reconstruction); Xia & Wang, closed-form and maximum-likelihood robust
CRT for reals (IEEE TSP 2007 / 2015); redundant residue number systems (Watson &
Hastings 1966); Fleet & Jepson 1990 (phase-based displacement); circular harmonic
(angular Fourier) phase for rotation.

Fail-closed: non-finite input, non-positive periods, negative weights, a search
range wider than the periods can resolve, and candidate grids too large to search
are all refused with ``ValueError`` — never clipped.
"""
from __future__ import annotations

import operator
from fractions import Fraction
from math import gcd

import numpy as np

__all__ = [
    "residue_integer_crt", "residue_crt", "residue_fault_locate",
    "crt_displacement", "harmonic_rotation",
]

#: cap on (candidates x samples x bands) evaluated by one ``residue_crt`` call
MAX_SEARCH_ELEMENTS = 60_000_000
#: cap on image elements for the image ops
MAX_IMAGE_ELEMENTS = 4_000_000


# --------------------------------------------------------------------------- #
# validation helpers (fail-closed)                                            #
# --------------------------------------------------------------------------- #
def _finite_array(a, name: str, op: str) -> np.ndarray:
    try:
        arr = np.asarray(a, dtype=np.float64)
    except (TypeError, ValueError) as e:
        raise ValueError("%s: %s is not numeric (%s)" % (op, name, e)) from None
    if arr.size == 0:
        raise ValueError("%s: %s is empty" % (op, name))
    if not np.isfinite(arr).all():
        raise ValueError("%s: %s contains NaN or inf" % (op, name))
    return arr


def _periods(p, op: str) -> np.ndarray:
    arr = _finite_array(p, "periods", op)
    if arr.ndim != 1:
        raise ValueError("%s: periods must be 1-D, got shape %s" % (op, arr.shape))
    if arr.size < 2:
        raise ValueError("%s: need at least 2 periods, got %d" % (op, arr.size))
    if (arr <= 0).any():
        raise ValueError("%s: periods must be > 0, got %s" % (op, arr.tolist()))
    return arr


def _residues(r, n: int, op: str) -> np.ndarray:
    arr = _finite_array(r, "residues", op)
    if arr.ndim == 0 or arr.shape[0] != n:
        raise ValueError("%s: residues must have the band axis first with length %d "
                         "(= len(periods)), got shape %s" % (op, n, arr.shape))
    return arr


def _weights(w, shape, op: str) -> np.ndarray:
    if w is None:
        return np.ones(shape)
    arr = _finite_array(w, "weights", op)
    if (arr < 0).any():
        raise ValueError("%s: weights must be >= 0" % op)
    try:
        return np.broadcast_to(arr if arr.ndim == len(shape) else
                               arr.reshape(arr.shape + (1,) * (len(shape) - arr.ndim)), shape).astype(np.float64)
    except ValueError:
        raise ValueError("%s: weights shape %s does not broadcast to residues %s"
                         % (op, arr.shape, shape)) from None


def _wrap_signed(e, period):
    """Map ``e`` into ``[-period/2, period/2)``."""
    return (e + 0.5 * period) % period - 0.5 * period


def _rational_lcm(periods: np.ndarray, max_den: int = 64):
    """LCM of the periods if they are (nearly) commensurate, else ``inf``.

    Each period is approximated by a fraction with denominator <= ``max_den``;
    if any approximation is off by more than 1e-9 relative, the set is treated
    as incommensurate (no finite exact repeat)."""
    fr = []
    for p in periods:
        f = Fraction(float(p)).limit_denominator(max_den)
        if abs(float(f) - p) > 1e-9 * p:
            return float("inf")
        fr.append(f)
    num = 1
    den = 0
    for f in fr:
        # lcm of fractions a/b = lcm(a) / gcd(b)
        num = num * f.numerator // gcd(num, f.numerator)
        den = f.denominator if den == 0 else gcd(den, f.denominator)
    return num / den


# --------------------------------------------------------------------------- #
# 1. the theorem                                                              #
# --------------------------------------------------------------------------- #
def _exact_int(x, op: str) -> int:
    """One element -> Python ``int`` with exact integer semantics, else ``ValueError``.

    ★2026-10-07: 以前は ``int(x)`` で切り捨ててから float で比較していた → 生成器だと 2 回目の走査が空で
    1.5 が 1 に化け、1e308 超の int は float 化で OverflowError。int / numpy 整数は float を通さず、
    float は有限かつ整数値のときだけ受ける。"""
    if isinstance(x, (bool, np.bool_)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        xf = float(x)
        if not (np.isfinite(xf) and xf.is_integer()):
            raise ValueError("%s: residues and moduli must be integer-valued, got %r" % (op, x))
        return int(xf)
    try:
        return operator.index(x)            # int / numpy integer: arbitrary precision, no float
    except TypeError:
        pass
    if isinstance(x, Fraction) and x.denominator == 1:
        return int(x)
    raise ValueError("%s: residues and moduli must be integers, got %r (%s)" % (op, x, type(x).__name__))


def residue_integer_crt(residues, moduli) -> dict:
    """Exact integer CRT (Garner's mixed-radix algorithm) -> ``dict``.

    ``residues`` and ``moduli`` are equal-length integer sequences; the moduli must
    be pairwise coprime and >= 2. Returns ``{"value": int, "modulus": int,
    "mixed_radix": [digits]}`` where ``value`` is the unique solution in
    ``[0, prod(moduli))``. Arithmetic is Python's arbitrary-precision ``int`` —
    there is no rounding anywhere, which is why this op is the oracle for
    :func:`residue_crt`.

    The mixed-radix digits ``d_k`` satisfy ``value = d_0 + d_1 m_0 + d_2 m_0 m_1 + ...``:
    the *positional* (coarse-to-fine) reading of the same residues, i.e. the
    bridge between the residue view and the place-value view."""
    op = "residue_integer_crt"
    try:
        r_in, m_in = list(residues), list(moduli)     # ★2026-10-07: 生成器は 1 回だけ走査する
    except TypeError:
        raise ValueError("%s: residues and moduli must be sequences of integers" % op) from None
    r = [_exact_int(x, op) for x in r_in]
    m = [_exact_int(x, op) for x in m_in]
    assert len(r) == len(r_in) and len(m) == len(m_in)
    if len(r) != len(m) or len(m) < 1:
        raise ValueError("%s: need equal, non-zero lengths, got %d residues / %d moduli"
                         % (op, len(r), len(m)))
    if any(x < 2 for x in m):
        raise ValueError("%s: moduli must be >= 2, got %s" % (op, m))
    for i in range(len(m)):
        for j in range(i + 1, len(m)):
            if gcd(m[i], m[j]) != 1:
                raise ValueError("%s: moduli %d and %d are not coprime (gcd %d) — the "
                                 "solution would not be unique" % (op, m[i], m[j], gcd(m[i], m[j])))
    r = [x % mi for x, mi in zip(r, m)]
    digits = []
    for k in range(len(m)):
        v = r[k]
        # subtract the contribution of earlier digits, divide by the earlier moduli
        acc = 0
        place = 1
        for j in range(k):
            acc += digits[j] * place
            place *= m[j]
        v = ((r[k] - acc) * pow(place % m[k], -1, m[k])) % m[k] if k else r[0]
        digits.append(v)
    value = 0
    place = 1
    for d, mi in zip(digits, m):
        value += d * place
        place *= mi
    return {"value": int(value), "modulus": int(place), "mixed_radix": digits}


# --------------------------------------------------------------------------- #
# 2. weighted robust CRT over reals                                            #
# --------------------------------------------------------------------------- #
def _crt_core(r, p, w, lo, hi, ref):
    n = r.shape[0]
    shp = r.shape[1:]
    pb = p.reshape((n,) + (1,) * len(shp))
    pr = p[ref]
    ks = np.arange(np.floor((lo - pr) / pr), np.ceil(hi / pr) + 1)
    cand = r[ref][None] + ks.reshape((-1,) + (1,) * len(shp)) * pr
    inside = (cand >= lo) & (cand < hi)
    ph = 2.0 * np.pi * (cand[None] - r[:, None]) / pb[:, None]
    score = (w[:, None] * np.cos(ph)).sum(0)
    score = np.where(inside, score, -np.inf)
    order = np.argsort(-score, axis=0, kind="stable")
    best = np.take_along_axis(cand, order[:1], 0)[0]
    s1 = np.take_along_axis(score, order[:1], 0)[0]
    s2 = (np.take_along_axis(score, order[1:2], 0)[0] if score.shape[0] > 1
          else np.full(shp, -np.inf))
    e = _wrap_signed(r - best[None], pb)
    iv = w / pb ** 2                       # equal phase noise -> variance ~ period^2
    ivs = iv.sum(0)
    val = best + np.where(ivs > 0, (iv * e).sum(0) / np.where(ivs > 0, ivs, 1.0), 0.0)
    resid = _wrap_signed(r - val[None], pb)
    wsum = w.sum(0)
    safe = np.where(wsum > 0, wsum, 1.0)
    with np.errstate(invalid="ignore"):
        margin = np.where(np.isfinite(s2), (s1 - s2) / safe, 2.0)
    score_out = np.where(wsum > 0, s1 / safe, 0.0)
    margin = np.where(wsum > 0, margin, 0.0)
    empty = ~np.isfinite(s1)
    if empty.any():
        # ★2026-10-07: [lo, hi) に候補が 1 つも無い標本は範囲外の値・score -inf・margin 2.0(最大の確信)を
        # 返していた → 値と score は NaN、margin 0(residue_fault_locate の「決められない = NaN」と同じ約束)。
        val = np.where(empty, np.nan, val)
        score_out = np.where(empty, np.nan, score_out)
        margin = np.where(empty, 0.0, margin)
        resid = np.where(empty[None], np.nan, resid)
    return val, score_out, margin, resid, cand.shape[0]


def residue_crt(residues, periods, weights=None, lo=0.0, hi=None) -> dict:
    """Weighted robust CRT over real periods -> ``dict``.

    Solve ``v ≡ residues[i] (mod periods[i])`` for ``v`` in ``[lo, hi)``.
    ``residues`` has the band axis first, shape ``(N,)`` or ``(N, ...)`` — every
    trailing element is solved independently (one pixel, one sample).
    ``weights`` (same shape, or ``(N,)``) say how much each band is trusted —
    typically the product of the two amplitudes the phase came from, so a band
    with no contrast gets no vote.

    Method: every candidate ``v = r_ref + k p_ref`` of the longest period inside
    the range is scored by phasor agreement ``sum_i w_i cos(2 pi (v - r_i)/p_i)``
    (the maximum-likelihood criterion for von-Mises phase noise); the best one is
    refined by the inverse-variance-weighted mean of the signed residuals.

    Returns ``{"value", "score", "margin", "residual", "n_candidates",
    "unambiguous_range"}``: ``score`` in ``[-1, 1]`` (1 = all bands agree
    exactly), ``margin`` = best minus runner-up score (small = the answer was a
    near tie — treat as unreliable), ``residual`` per band in the units of
    ``v``. ``hi`` defaults to ``lo`` + the least common multiple of the periods
    (when they are commensurate); a range wider than that is refused, because
    two values in it would have identical residues.

    Exactness: integer residues of pairwise-coprime integer periods reproduce
    :func:`residue_integer_crt` exactly. Robustness: with periods ``Γ M_i`` (``M_i``
    coprime integers) a value is recovered exactly whenever every residue error is
    below ``Γ/4`` (Wang & Xia's bound); beyond it the margin collapses first."""
    op = "residue_crt"
    p = _periods(periods, op)
    r = _residues(residues, p.size, op)
    w = _weights(weights, r.shape, op)
    lo = float(lo)
    if not np.isfinite(lo):
        raise ValueError("%s: lo must be finite" % op)
    lcm = _rational_lcm(p)
    if hi is None:
        if not np.isfinite(lcm):
            raise ValueError("%s: periods are not commensurate — give hi explicitly" % op)
        hi = lo + lcm
    hi = float(hi)
    if not np.isfinite(hi) or hi <= lo:
        raise ValueError("%s: need finite hi > lo, got [%r, %r)" % (op, lo, hi))
    if hi - lo > lcm * (1 + 1e-12):
        raise ValueError("%s: range %.6g is wider than the unambiguous range %.6g "
                         "(lcm of the periods) — two values would share every residue"
                         % (op, hi - lo, lcm))
    r = np.mod(r, p.reshape((p.size,) + (1,) * (r.ndim - 1)))
    ref = int(np.argmax(p))
    k = int(np.ceil((hi - lo) / p[ref])) + 2
    if k * max(r[0].size, 1) * p.size > MAX_SEARCH_ELEMENTS:
        raise ValueError("%s: %d candidates x %d samples x %d bands exceeds %d — "
                         "narrow [lo, hi) or split the samples"
                         % (op, k, r[0].size, p.size, MAX_SEARCH_ELEMENTS))
    val, score, margin, resid, nc = _crt_core(r, p, w, lo, hi, ref)
    return {"value": val, "score": score, "margin": margin, "residual": resid,
            "n_candidates": int(nc), "unambiguous_range": float(lcm)}


# --------------------------------------------------------------------------- #
# 3. RRNS fault localisation                                                  #
# --------------------------------------------------------------------------- #
def residue_fault_locate(residues, periods, weights=None, lo=0.0, hi=None, tol=0.05) -> dict:
    """Which band is corrupted? (redundant residue number system) -> ``dict``.

    With more bands than ``[lo, hi)`` needs, the bands check each other. Each
    band is left out in turn and the rest are solved; the band whose removal
    leaves a consistent set (every residual within ``tol`` x its period) while
    itself disagreeing by more than ``tol`` is the corrupted one. If no single
    removal is consistent, or two different removals both are, the answer is
    **undecidable** and the value is NaN — never a guess.

    Returns ``{"value", "faulty", "consistent_all", "worst_leave_one_out"}``:
    ``faulty`` is the band index, ``-1`` = all bands agree (no fault),
    ``-2`` = undecidable. Localising one fault needs the range to be resolvable by
    every subset of ``N-1`` bands (it is refused otherwise); the narrower
    ``[lo, hi)`` is relative to the periods' least common multiple, the more of
    the redundancy is left to localise with."""
    op = "residue_fault_locate"
    p = _periods(periods, op)
    if p.size < 3:
        raise ValueError("%s: localising a fault needs >= 3 bands, got %d" % (op, p.size))
    r = _residues(residues, p.size, op)
    w = _weights(weights, r.shape, op)
    tol = float(tol)
    if not (0.0 < tol < 0.25):
        raise ValueError("%s: tol must be in (0, 0.25) of a period, got %r" % (op, tol))
    full = residue_crt(r, p, w, lo, hi)
    hi_eff = float(lo) + full["unambiguous_range"] if hi is None else float(hi)
    pb = p.reshape((p.size,) + (1,) * (r.ndim - 1))
    ok_all = (np.abs(full["residual"]) <= tol * pb).all(0)
    worst, vals, outl = [], [], []
    for j in range(p.size):
        keep = [i for i in range(p.size) if i != j]
        sub = residue_crt(r[keep], p[keep], w[keep], lo, hi_eff)   # refuses if N-1 cannot resolve
        worst.append((np.abs(sub["residual"]) / pb[keep]).max(0))
        vals.append(sub["value"])
        outl.append(np.abs(_wrap_signed(r[j] - sub["value"], p[j])) / p[j])
    worst = np.stack(worst)
    vals = np.stack(vals)
    outl = np.stack(outl)
    j = np.argmin(worst, 0)
    wj = np.take_along_axis(worst, j[None], 0)[0]
    oj = np.take_along_axis(outl, j[None], 0)[0]
    runner = np.sort(worst, 0)[1]
    good = (wj <= tol) & (oj > tol) & (runner > tol)
    faulty = np.where(ok_all, -1, np.where(good, j, -2)).astype(np.int64)
    value = np.where(ok_all, full["value"],
                     np.where(good, np.take_along_axis(vals, j[None], 0)[0], np.nan))
    return {"value": value, "faulty": faulty, "consistent_all": ok_all,
            "worst_leave_one_out": wj}


# --------------------------------------------------------------------------- #
# 4. images: displacement beyond the wrap limit                                #
# --------------------------------------------------------------------------- #
def _image(a, name: str, op: str) -> np.ndarray:
    arr = _finite_array(a, name, op)
    if arr.ndim != 2 or min(arr.shape) < 8:
        raise ValueError("%s: %s must be a 2-D image of at least 8x8, got shape %s"
                         % (op, name, arr.shape))
    if arr.size > MAX_IMAGE_ELEMENTS:
        raise ValueError("%s: %s has %d pixels, cap is %d" % (op, name, arr.size, MAX_IMAGE_ELEMENTS))
    return arr


def _band(spec, shape, period, sigma_px, axis):
    """Analytic band at wavelength ``period`` -> (z, k_local [rad/px along axis])."""
    fu = np.fft.fftfreq(shape[1])[None, :]
    fv = np.fft.fftfreq(shape[0])[:, None]
    sf = 1.0 / (2.0 * np.pi * sigma_px)
    if axis == 1:
        g = np.exp(-((fu - 1.0 / period) ** 2 + fv ** 2) / (2.0 * sf * sf))
        dgrid = fu
    else:
        g = np.exp(-(fu ** 2 + (fv - 1.0 / period) ** 2) / (2.0 * sf * sf))
        dgrid = fv
    zs = spec * g
    z = np.fft.ifft2(zs)
    dz = np.fft.ifft2(zs * (2j * np.pi * dgrid))
    p2 = np.abs(z) ** 2
    k = np.imag(np.conj(z) * dz) / np.where(p2 > 0, p2, 1.0)
    return z, k


def _band_measure(img0, img1, periods, sigma_px, axis):
    """Per band: residue of d modulo the *local* wavelength, that wavelength, and weight.

    Natural images are broadband: inside a band the local spatial frequency
    wanders around the nominal 1/p, and dividing a phase difference by the
    nominal frequency turns a 10 % frequency error into a d/10 residue error —
    beyond the robust-CRT tolerance at once for large d (measured: with nominal
    wavelengths, 17 px shifts of the grass texture failed on 45-49 % of pixels;
    with local ones on 1-2 %). The local frequency ``Im(conj z dz/dx)/|z|^2``
    (averaged over the two images) is used; where it is implausible (outside a
    factor 3 of nominal) the nominal one is kept."""
    s0 = np.fft.fft2(img0)
    s1 = np.fft.fft2(img1)
    res, per, wts = [], [], []
    for p in periods:
        z0, k0 = _band(s0, img0.shape, p, sigma_px, axis)
        z1, k1 = _band(s1, img1.shape, p, sigma_px, axis)
        k = 0.5 * (k0 + k1)
        knom = 2.0 * np.pi / p
        k = np.where((k > knom / 3.0) & (k < 3.0 * knom), k, knom)
        pl = 2.0 * np.pi / k
        dphi = np.angle(z1 * np.conj(z0))              # = -k d  (mod 2 pi)
        res.append(np.mod(-dphi / k, pl))
        per.append(pl)
        wts.append(np.abs(z0) * np.abs(z1))
    return np.stack(res), np.stack(per), np.stack(wts)


def _crt_core_var(r, pb, w, lo, hi):
    """:func:`_crt_core` with per-sample periods ``pb`` (same shape as ``r``)."""
    ref = int(np.argmax(pb.reshape(pb.shape[0], -1).mean(1)))
    pr = pb[ref]
    kmax = int(np.ceil(max(abs(lo), abs(hi)) / float(pr.min()))) + 2
    ks = np.arange(-kmax, kmax + 1).reshape((-1,) + (1,) * (r.ndim - 1))
    cand = r[ref][None] + ks * pr[None]
    inside = (cand >= lo) & (cand < hi)
    score = (w[:, None] * np.cos(2.0 * np.pi * (cand[None] - r[:, None]) / pb[:, None])).sum(0)
    score = np.where(inside, score, -np.inf)
    order = np.argsort(-score, axis=0, kind="stable")
    best = np.take_along_axis(cand, order[:1], 0)[0]
    s1 = np.take_along_axis(score, order[:1], 0)[0]
    s2 = np.take_along_axis(score, order[1:2], 0)[0]
    e = _wrap_signed(r - best[None], pb)
    iv = w / pb ** 2
    ivs = iv.sum(0)
    val = best + np.where(ivs > 0, (iv * e).sum(0) / np.where(ivs > 0, ivs, 1.0), 0.0)
    wsum = w.sum(0)
    safe = np.where(wsum > 0, wsum, 1.0)
    with np.errstate(invalid="ignore"):
        margin = np.where(np.isfinite(s2), (s1 - s2) / safe, 2.0)
    # ★2026-10-07: 範囲内に候補が無い画素は margin 0(= valid にしない)。値は warp 用に有限のまま残す。
    margin = np.where(np.isfinite(s1), margin, 0.0)
    return val, np.where(wsum > 0, margin, 0.0), _wrap_signed(r - val[None], pb)


def crt_displacement(image0, image1, periods=(5.0, 7.0, 9.0, 11.0, 13.0, 16.0), sigma_px=40.0,
                     max_disp=40.0, axis="x", refine=2) -> dict:
    """Local displacement from band phases at several wavelengths, unwrapped by CRT -> ``dict``.

    A band of wavelength ``p`` measures the local shift only modulo ``p``, so
    any single-band phase method breaks at ``|d| = p/2`` (``motionmag.phase_displacement``
    reports this as ``wrap_limit_px``). Bands at *coprime* wavelengths each break
    there too, but together they fix ``d`` over the least common multiple —
    693 px for 7/9/11 — so the limit becomes ``max_disp``, the search half-width.

    ``image1`` is ``image0`` with its content moved by ``d(y, x)`` along ``axis``
    (``"x"`` = columns, ``"y"`` = rows; positive towards increasing index). For each
    wavelength a Gaussian band-pass (analytic, one-sided, spatial std ``sigma_px``)
    gives a local phase and a *local* wavelength (measured, not nominal — see
    ``_band_measure``); their phase differences are residues of ``d``; amplitude
    products are the weights; every pixel is solved by the phasor-agreement search
    of :func:`residue_crt`. ``refine`` iterations then warp ``image1`` back by the
    current estimate and add the (now small, wrap-free) weighted residual.

    Returns ``{"d", "weight", "margin", "residual", "valid", "wrap_limit_single_px"}``.
    ``valid`` = enough contrast in the bands *and* a margin above 0.05; a pixel
    that fails is still returned but should not be trusted.

    **Where it applies**: textured regions that each move (nearly) rigidly by a
    large amount — measured on two regions of the public scikit-image textures moving
    +20 / -15 px, pixels farther than 1.5 ``sigma_px`` from the region boundary are
    off by more than 1 px on 2 % (grass) / 5 % (gravel) / 6 % (brick), where the
    best pyramid Lucas-Kanade (3-6 levels) is off on 49 / 50 / 67 %.
    **Where it does not**: within ~1.5 ``sigma_px`` of a motion boundary; where the
    displacement changes inside the window (a 6 px field with gradient 0.07 is
    already off on half the pixels — a band narrow enough to keep the local
    frequency stable needs a window too wide to follow the field); flat regions
    (``weight`` and ``valid`` say where); occlusions. A single global translation is
    better served by phase correlation. Numbers: ``examples/poc_residue_crt.py``."""
    op = "crt_displacement"
    a = _image(image0, "image0", op)
    b = _image(image1, "image1", op)
    if a.shape != b.shape:
        raise ValueError("%s: image shapes differ %s vs %s" % (op, a.shape, b.shape))
    p = _periods(periods, op)
    if (p < 2.0).any():
        raise ValueError("%s: wavelengths must be >= 2 px (Nyquist), got %s" % (op, p.tolist()))
    sigma_px = float(sigma_px)
    if not np.isfinite(sigma_px) or sigma_px < 2.0:
        raise ValueError("%s: sigma_px must be >= 2, got %r" % (op, sigma_px))
    max_disp = float(max_disp)
    if not np.isfinite(max_disp) or max_disp <= 0:
        raise ValueError("%s: max_disp must be > 0, got %r" % (op, max_disp))
    if 2.0 * max_disp > _rational_lcm(p) * (1 + 1e-12):
        raise ValueError("%s: 2*max_disp = %g exceeds the lcm %g of the wavelengths — "
                         "the answer would not be unique" % (op, 2 * max_disp, _rational_lcm(p)))
    if axis not in ("x", "y"):
        raise ValueError("%s: axis must be 'x' or 'y', got %r" % (op, axis))
    refine = int(refine)
    if refine < 0 or refine > 10:
        raise ValueError("%s: refine must be in 0..10, got %r" % (op, refine))
    ax = 1 if axis == "x" else 0
    kmax = int(np.ceil(max_disp / (p.max() / 3.0))) + 2
    if (2 * kmax + 1) * a.size * p.size > MAX_SEARCH_ELEMENTS:
        raise ValueError("%s: search too large (%d candidates x %d px x %d bands) — "
                         "reduce max_disp or the image" % (op, 2 * kmax + 1, a.size, p.size))
    from scipy.ndimage import map_coordinates

    res, per, wts = _band_measure(a, b, p, sigma_px, ax)
    d, margin, resid = _crt_core_var(res, per, wts, -max_disp, max_disp)
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]].astype(np.float64)
    for _ in range(refine):
        coords = [yy, xx + d] if ax == 1 else [yy + d, xx]
        back = map_coordinates(b, coords, order=3, mode="grid-wrap")   # same circular world as the FFT band-pass
        res2, per2, wts = _band_measure(a, back, p, sigma_px, ax)
        e = _wrap_signed(res2, per2)
        iv = wts / per2 ** 2
        ivs = iv.sum(0)
        d = d + np.where(ivs > 0, (iv * e).sum(0) / np.where(ivs > 0, ivs, 1.0), 0.0)
    weight = wts.sum(0)
    floor = 1e-3 * float(weight.max()) if weight.size and weight.max() > 0 else 0.0
    # ★2026-10-07: refine 後に |d| が探索範囲 max_disp を越えた画素は黙って切らず valid=False にする。
    valid = (weight > floor) & (margin > 0.05) & np.isfinite(d) & (np.abs(d) <= max_disp)
    return {"d": d, "weight": weight, "margin": margin, "residual": resid,
            "valid": valid, "wrap_limit_single_px": float(p.max() / 2.0)}


# --------------------------------------------------------------------------- #
# 5. images: absolute rotation from circular harmonics                         #
# --------------------------------------------------------------------------- #
def _ring_harmonic(img, ctr, r0, r1, n, n_theta=720, n_r=12):
    from scipy.ndimage import map_coordinates
    th = np.linspace(0.0, 2.0 * np.pi, n_theta, endpoint=False)
    rr = np.linspace(r0, r1, n_r)
    R, T = np.meshgrid(rr, th, indexing="ij")
    v = map_coordinates(img, [ctr[0] + R * np.sin(T), ctr[1] + R * np.cos(T)], order=3, mode="nearest")
    return np.fft.fft(v, axis=1)[:, n].sum()


def harmonic_rotation(image, reference, orders=(3, 4, 5), rings=((14, 24), (30, 40), (46, 56)),
                      center=None, tol=0.05) -> dict:
    """Absolute in-plane rotation of ``image`` relative to ``reference`` over 360 degrees -> ``dict``.

    A feature with n-fold symmetry (n lobes, n holes, n slots) tells the
    rotation only modulo ``360/n`` degrees: its order-``n`` circular harmonic has
    phase ``n*theta``. Features of several orders, each ambiguous alone, fix
    ``theta`` uniquely whenever the orders have no common divisor (3 and 4: 360 /
    gcd = 360). This op samples each annulus ``rings[i]`` (radii in px around
    ``center``, default the image centre), takes the order ``orders[i]`` angular
    Fourier coefficient of image and reference, and solves the angle by
    :func:`residue_crt` with the coefficient amplitudes as weights.

    Returns ``{"angle_deg", "per_order_deg", "residual_deg", "margin", "suspect",
    "amplitude"}``. ``angle_deg`` is counter-clockwise on screen (rows down) — the
    convention of ``scipy.ndimage.rotate`` — in ``[0, 360)``. ``suspect`` is the index of the ring whose residual is
    worst relative to its period (or ``-1`` if all are within ``tol``) — a smudged,
    occluded or broken feature shows up there before it corrupts the angle.
    With >= 3 orders and only one corrupted, :func:`residue_fault_locate` gives a
    hard decision; this op keeps the soft one.

    Rotate greyscale images (interpolate, then threshold if needed): rotating a
    binary mask with nearest-neighbour sampling roughens the edges and biases the
    harmonics."""
    op = "harmonic_rotation"
    img = _image(image, "image", op)
    ref = _image(reference, "reference", op)
    if img.shape != ref.shape:
        raise ValueError("%s: image shapes differ %s vs %s" % (op, img.shape, ref.shape))
    try:
        ords = [int(o) for o in orders]
    except (TypeError, ValueError):
        raise ValueError("%s: orders must be integers" % op) from None
    if len(ords) < 2 or any(o < 1 for o in ords) or any(float(o) != float(x) for o, x in zip(ords, orders)):
        raise ValueError("%s: need >= 2 integer orders >= 1, got %r" % (op, orders))
    g = 0
    for o in ords:
        g = gcd(g, o)
    if g != 1:
        raise ValueError("%s: orders %s share the divisor %d — the angle would only be "
                         "known modulo %g degrees" % (op, ords, g, 360.0 / g))
    rg = _finite_array(rings, "rings", op)
    if rg.shape != (len(ords), 2) or (rg[:, 0] < 0).any() or (rg[:, 1] <= rg[:, 0]).any():
        raise ValueError("%s: rings must be %d pairs (r_in < r_out), got %s" % (op, len(ords), rg.tolist()))
    if center is None:
        ctr = ((img.shape[0] - 1) / 2.0, (img.shape[1] - 1) / 2.0)
    else:
        c = _finite_array(center, "center", op)
        if c.shape != (2,):
            raise ValueError("%s: center must be (row, col)" % op)
        ctr = (float(c[0]), float(c[1]))
    if (rg[:, 1].max() > min(ctr[0], ctr[1], img.shape[0] - 1 - ctr[0], img.shape[1] - 1 - ctr[1]) + 1e-9):
        raise ValueError("%s: the outer ring (r=%g) leaves the image around center %s"
                         % (op, rg[:, 1].max(), ctr))
    tol = float(tol)
    if not (0.0 < tol < 0.25):
        raise ValueError("%s: tol must be in (0, 0.25), got %r" % (op, tol))
    c_img = np.array([_ring_harmonic(img, ctr, r0, r1, n) for n, (r0, r1) in zip(ords, rg)])
    c_ref = np.array([_ring_harmonic(ref, ctr, r0, r1, n) for n, (r0, r1) in zip(ords, rg)])
    amp = np.abs(c_img) * np.abs(c_ref)
    if amp.max() <= 0:
        raise ValueError("%s: no ring carries its harmonic (all amplitudes are zero)" % op)
    L = 360.0
    per = L / np.array(ords, float)
    # sampling angle T runs clockwise on screen (rows down), so rotating the content by
    # +theta counter-clockwise on screen (the scipy.ndimage.rotate convention) multiplies
    # the order-n coefficient by exp(+i n theta) -> n*theta = arg(img * conj(ref))
    nth = np.angle(c_img * np.conj(c_ref))
    res = np.mod(np.degrees(nth) / np.array(ords, float), per)
    out = residue_crt(res, per, amp, 0.0, L)
    rel = np.abs(out["residual"]) / per
    suspect = int(np.argmax(rel)) if rel.max() > tol else -1
    return {"angle_deg": float(np.mod(out["value"], L)), "per_order_deg": res,
            "residual_deg": out["residual"], "margin": float(out["margin"]),
            "suspect": suspect, "amplitude": amp}
