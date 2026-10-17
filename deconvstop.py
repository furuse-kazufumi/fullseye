# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""deconvstop — Richardson-Lucy deconvolution that stops by a discrepancy principle, not by a fixed count.

``backends_inverse.iv_richardson_lucy`` runs 1..15 iterations chosen by a knob: nothing in it
says when to stop, and Richardson-Lucy run too long amplifies the noise (semi-convergence —
the error to the truth falls, then rises). This module stops it where the data say to stop:
at the first iteration whose fit to the data is as good as the noise allows, and no better.

Model: y = H x + noise with H a convolution by a normalised PSF on the periodic grid (so
H^T 1 = 1 and the Richardson-Lucy / EM iteration conserves the total, see below).

* Poisson noise (photon counts): the Poisson discrepancy criterion of Bertero, Boccacci,
  Talenti, Zanella & Zanni 2010, as written in Benvenuto & Piana 2012 eq. (30):

      D_k = (2/N) sum_i [ y_i ln(y_i / (H x_k)_i) + (H x_k)_i - y_i ]  <=  tau,  tau = 1.

* Gaussian noise of known sigma: Morozov's discrepancy principle (Benvenuto & Piana eq. (18)):

      ||H x_k - y||^2  <=  tau N sigma^2.

The first k that satisfies the criterion is returned. Benvenuto & Piana prove the rule is a
regularisation only when y lies in the range of the model, y in H(C) (their Theorems 3.1-3.4);
when the discrepancy levels off above tau the data are **outside the model's range** (a
wrong PSF, a missing background) and no image is returned — the last iterate is kept under
``last_iterate``, explicitly not an estimate.

Conservation (gate): for every EM iterate, sum_i (H x_k)_i = sum_i y_i (Benvenuto & Piana
Lemma 3.2, eq. (22)); the record carries the largest relative deviation over the run.
"""
from __future__ import annotations

import math

import numpy as np

from metriccontract import MetricContractError

__all__ = ["iv_richardson_lucy_until"]

MAX_ITER_CAP = 100_000
MAX_PIXELS = 16_000_000
TINY = 1e-300


def _gauss_psf(sigma, shape):
    r = max(1, int(math.ceil(4.0 * sigma)))
    r = min(r, (min(shape) - 1) // 2)
    ax = np.arange(-r, r + 1, dtype=np.float64)
    g = np.exp(-0.5 * (ax / sigma) ** 2)
    k = np.outer(g, g)
    return k / k.sum()


def _otf(psf, shape):
    """Optical transfer function of a centred PSF on the periodic grid of ``shape``."""
    P = np.zeros(shape, dtype=np.float64)
    ph, pw = psf.shape
    P[:ph, :pw] = psf
    P = np.roll(P, (-(ph // 2), -(pw // 2)), axis=(0, 1))
    return np.fft.rfft2(P)


def iv_richardson_lucy_until(image=None, psf_sigma=1.5, psf=None, noise="poisson", sigma=None, gain=1.0, tau=1.0,
                             max_iter=2000, plateau_window=25, plateau_rtol=1e-4, keep_history=True, callback=None) -> dict:
    """Richardson-Lucy deconvolution stopped by the discrepancy principle (Poisson: Bertero 2010, tau = 1; Gaussian: Morozov); refuses data outside the model's range.

    ``image``: the blurred, noisy 2-D image. ``psf``: a 2-D PSF (normalised here), or a
    Gaussian of ``psf_sigma`` px. The blur is periodic (FFT), so the RL step
    x <- x * H^T(y / H x) keeps sum(H x) = sum(y) exactly (Lemma 3.2 of Benvenuto & Piana).

    * ``noise="poisson"``: ``image * gain`` must be photon counts (non-negative integers within
      1e-6); stop at the first k with the Poisson discrepancy D_k <= ``tau`` (Benvenuto &
      Piana 2012 eq. (30); tau = 1 as proposed by Bertero et al. 2010).
    * ``noise="gaussian"``: ``sigma`` (the noise standard deviation, in image units) is
      required; stop at the first k with ||H x_k - y||^2 / (N sigma^2) <= ``tau`` (Morozov,
      eq. (18)). The image must be non-negative (add the known offset first).

    The iteration starts from the flat image of the data's mean (k = 0). Returns ``image``
    (x_k in the input units), ``stopped``, ``status``, ``k_stop``, ``discrepancy_history``
    (D_0, D_1, ...), ``mass_rel_error_max`` (Lemma 3.2), ``tau`` and ``noise``.

    Not stopped -> ``image = None`` and ``status``:

    * ``"outside_model_range"`` — the discrepancy levelled off above tau (relative decrease
      below ``plateau_rtol`` per iteration over ``plateau_window`` iterations): y is not in the
      range of the model, so the criterion can never be met (Benvenuto & Piana: the rule is a
      regularisation iff y is in H(C)). Typical causes: the assumed PSF is wider than the real
      blur, a background is missing, the noise level is wrong.
    * ``"max_iter"`` — still decreasing when ``max_iter`` ran out.

    The last iterate is under ``last_iterate`` (not an estimate). ``callback(k, x_k, D_k)``, if
    given, is called after every iteration (x_k in the input units) — for plotting the run.
    """
    op = "iv_richardson_lucy_until"
    if image is None:
        image = _example_counts()
    try:
        y0 = np.asarray(image, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("%s: image must be numeric" % op) from None
    if y0.ndim != 2 or min(y0.shape) < 8:
        raise ValueError("%s: image must be 2-D and at least 8 x 8, got shape %s" % (op, y0.shape))
    if y0.size > MAX_PIXELS:
        raise ValueError("%s: image has %d pixels (cap %d)" % (op, y0.size, MAX_PIXELS))
    if not np.isfinite(y0).all():
        raise ValueError("%s: image contains NaN or inf" % op)
    if noise not in ("poisson", "gaussian"):
        raise ValueError("%s: noise must be 'poisson' or 'gaussian', got %r" % (op, noise))
    gain = float(gain)
    if not (math.isfinite(gain) and gain > 0):
        raise ValueError("%s: gain must be > 0" % op)
    tau = float(tau)
    if not (math.isfinite(tau) and tau > 0):
        raise ValueError("%s: tau must be > 0" % op)
    try:
        max_iter, plateau_window = int(max_iter), int(plateau_window)
    except (TypeError, ValueError):
        raise ValueError("%s: max_iter and plateau_window must be integers" % op) from None
    if callback is not None and not callable(callback):
        raise ValueError("%s: callback must be callable(k, x_k, D_k)" % op)
    if not 1 <= max_iter <= MAX_ITER_CAP or plateau_window < 2:
        raise ValueError("%s: need 1 <= max_iter <= %d and plateau_window >= 2" % (op, MAX_ITER_CAP))
    plateau_rtol = float(plateau_rtol)
    if not (math.isfinite(plateau_rtol) and plateau_rtol > 0):
        raise ValueError("%s: plateau_rtol must be > 0" % op)

    y = y0 * gain
    if (y < 0).any():
        raise MetricContractError("%s: the data have negative values — Richardson-Lucy needs y >= 0 "
                                  "(subtract nothing; add the known offset, or check the noise model)" % op)
    if noise == "poisson":
        if np.abs(y - np.round(y)).max() > 1e-6:
            raise MetricContractError("%s: noise='poisson' needs photon counts — image * gain must be integers "
                                      "(pass gain = counts per unit, or use noise='gaussian' with sigma)" % op)
        y = np.round(y)
        sig2 = None
    else:
        if sigma is None:
            raise MetricContractError("%s: noise='gaussian' needs sigma (the noise level is not guessed)" % op)
        s = float(sigma) * gain
        if not (math.isfinite(s) and s > 0):
            raise ValueError("%s: sigma must be > 0" % op)
        sig2 = s * s
    total = float(y.sum())
    if total <= 0:
        raise MetricContractError("%s: the image is all zero — nothing to deconvolve" % op)

    if psf is None:
        ps = float(psf_sigma)
        if not (math.isfinite(ps) and ps > 0):
            raise ValueError("%s: psf_sigma must be > 0" % op)
        k = _gauss_psf(ps, y.shape)
    else:
        k = np.asarray(psf, dtype=np.float64)
        if k.ndim != 2 or k.shape[0] > y.shape[0] or k.shape[1] > y.shape[1]:
            raise ValueError("%s: psf must be 2-D and not larger than the image" % op)
        if not np.isfinite(k).all() or (k < 0).any() or k.sum() <= 0:
            raise ValueError("%s: psf must be finite, non-negative and not all zero" % op)
        k = k / k.sum()
    otf = _otf(k, y.shape)
    shape = y.shape

    def H(v):
        return np.fft.irfft2(np.fft.rfft2(v) * otf, s=shape)

    def Ht(v):
        return np.fft.irfft2(np.fft.rfft2(v) * np.conj(otf), s=shape)

    N = y.size
    pos = y > 0

    def disc(Hx):
        Hx = np.maximum(Hx, TINY)
        if noise == "poisson":
            t = Hx - y
            t[pos] += y[pos] * np.log(y[pos] / Hx[pos])
            return float(2.0 / N * t.sum())
        return float(((Hx - y) ** 2).sum() / (N * sig2))

    x = np.full(shape, total / N)
    Hx = H(x)
    D = [disc(Hx)]
    mass_err = 0.0
    status = None
    kk = 0
    if D[0] <= tau:
        status = "stopped"
    else:
        for kk in range(1, max_iter + 1):
            ratio = y / np.maximum(Hx, TINY)
            x = x * Ht(ratio)
            x = np.maximum(x, 0.0)
            Hx = H(x)
            mass_err = max(mass_err, abs(float(Hx.sum()) - total) / total)
            D.append(disc(Hx))
            if callback is not None:
                callback(kk, x / gain, D[-1])
            if not math.isfinite(D[-1]):
                raise MetricContractError("%s: the discrepancy became NaN or inf at iteration %d" % (op, kk))
            if D[-1] <= tau:
                status = "stopped"
                break
            if kk >= plateau_window:
                prev = D[-1 - plateau_window]
                if prev - D[-1] < plateau_rtol * plateau_window * D[-1]:
                    status = "outside_model_range"
                    break
        if status is None:
            status = "max_iter"
    rec = {"op": op, "noise": noise, "tau": tau, "status": status, "stopped": status == "stopped",
           "k_stop": int(kk) if status == "stopped" else None, "n_iter": int(kk),
           "discrepancy": D[-1], "mass_rel_error_max": mass_err,
           "criterion": ("Poisson discrepancy (2/N) sum[y ln(y/Hx) + Hx - y] <= tau (Benvenuto & Piana 2012 eq. 30; "
                         "Bertero et al. 2010)" if noise == "poisson" else
                         "Morozov ||Hx - y||^2 / (N sigma^2) <= tau (Benvenuto & Piana 2012 eq. 18)")}
    if keep_history:
        rec["discrepancy_history"] = [float(v) for v in D]
    if status == "stopped":
        rec["image"] = x / gain
    else:
        rec["image"] = None
        rec["last_iterate"] = x / gain
        rec["reason"] = ("the discrepancy levelled off at %.4g > tau = %.4g: the data are outside the range of the "
                         "model (wrong PSF, missing background or wrong noise level)" % (D[-1], tau)
                         if status == "outside_model_range" else
                         "max_iter = %d reached while the discrepancy (%.4g) was still above tau = %.4g"
                         % (max_iter, D[-1], tau))
    return rec


def _example_counts(seed=0):
    """A small Poisson-count example (bars and a disc, blurred by a Gaussian of sigma 1.5 px, ~200 counts peak)."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:48, 0:48]
    truth = np.full((48, 48), 10.0)
    truth[8:40, 10:13] += 150.0
    truth[8:40, 16:19] += 150.0
    truth[((yy - 24) ** 2 + (xx - 34) ** 2) <= 36] += 120.0
    otf = _otf(_gauss_psf(1.5, truth.shape), truth.shape)
    blurred = np.fft.irfft2(np.fft.rfft2(truth) * otf, s=truth.shape)
    return rng.poisson(np.maximum(blurred, 0.0)).astype(np.float64)
