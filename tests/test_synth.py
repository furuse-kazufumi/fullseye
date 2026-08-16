"""Tests for synth.py — learn an image's features and synthesise a similar one.

Contracts pinned here (honest, ground-truth):
  * spectral synthesis MATCHES the exemplar's learned features (spectrum + marginal
    histogram) — closer than an independent same-process sample — while being
    GENUINELY NEW (as patch-novel as an independent sample; not a copy);
  * a known dominant frequency / spectral character is preserved;
  * histogram matching is exact; determinism; size control; edge cases don't crash;
  * quilting produces a larger, finite, in-range image that resembles the exemplar.
"""
from __future__ import annotations

import numpy as np
import pytest

import synth


def _pink(h, w, seed):
    """1/f (pink) noise — a stochastic texture with a known spectral character."""
    rng = np.random.default_rng(seed)
    wn = rng.standard_normal((h, w))
    F = np.fft.fftshift(np.fft.fft2(wn))
    cy, cx = h // 2, w // 2
    y, x = np.ogrid[:h, :w]
    r = np.hypot(y - cy, x - cx)
    r[cy, cx] = 1.0
    F = F / r
    out = np.real(np.fft.ifft2(np.fft.ifftshift(F)))
    return (out - out.min()) / (np.ptp(out) + 1e-9)


# --------------------------------------------------------------------------- #
# spectral synthesis: matches learned features AND is genuinely new
# --------------------------------------------------------------------------- #
def test_spectral_matches_features_and_is_novel():
    src = _pink(128, 128, 0)
    syn = synth.synthesize_like(src, seed=5, method="spectral")
    d = synth.feature_distance(src, syn)
    # imposes the exemplar's amplitude + histogram -> statistics match tightly
    assert d["hist_chi2"] < 0.01
    assert d["spectrum_l2"] < 0.05
    # ...yet it is a NEW instance: as patch-novel as an independent same-process draw
    ind = _pink(128, 128, 999)
    nov_syn = synth.patch_novelty(syn, src, seed=1)
    nov_ind = synth.patch_novelty(ind, src, seed=1)
    assert nov_syn > 0.5 * nov_ind, (nov_syn, nov_ind)
    # and not a copy
    assert not np.array_equal(syn, src)
    assert abs(float(np.corrcoef(syn.ravel(), src.ravel())[0, 1])) < 0.3


def test_spectral_preserves_dominant_frequency():
    h = w = 128
    yy, xx = np.mgrid[0:h, 0:w]
    grating = 0.5 + 0.4 * np.sin(2 * np.pi * 8 * xx / w)
    out = synth.synthesize_like(grating, seed=1, method="spectral")
    fr, ps = synth.radial_power_spectrum(grating)
    fr2, ps2 = synth.radial_power_spectrum(out)
    peak_src = fr[np.argmax(ps[1:]) + 1]
    peak_out = fr2[np.argmax(ps2[1:]) + 1]
    assert abs(peak_src - peak_out) < 0.03


def test_spectral_is_deterministic():
    src = _pink(64, 64, 3)
    a = synth.synthesize_like(src, seed=7, method="spectral")
    b = synth.synthesize_like(src, seed=7, method="spectral")
    assert np.array_equal(a, b)
    c = synth.synthesize_like(src, seed=8, method="spectral")
    assert not np.array_equal(a, c)                      # different seed -> different image


def test_size_control():
    src = _pink(64, 64, 1)
    out = synth.synthesize_like(src, size=(96, 128), seed=2, method="spectral")
    assert out.shape == (96, 128)
    assert np.isfinite(out).all() and out.min() >= 0.0 and out.max() <= 1.0


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def test_match_histogram_is_exact():
    src = _pink(80, 80, 2)
    noise = np.random.default_rng(0).standard_normal((60, 60))
    matched = synth.match_histogram(noise, src)
    h1, _ = np.histogram(matched, 64, (0, 1))
    h2, _ = np.histogram(src, 64, (0, 1))
    h1 = h1 / h1.sum()
    h2 = h2 / h2.sum()
    chi2 = 0.5 * float(np.sum((h1 - h2) ** 2 / (h1 + h2 + 1e-12)))
    assert chi2 < 0.01


def test_feature_distance_zero_for_identical():
    src = _pink(48, 48, 4)
    d = synth.feature_distance(src, src)
    assert d["hist_chi2"] < 1e-9 and d["spectrum_l2"] < 1e-9
    assert d["mean_diff"] < 1e-12 and d["std_diff"] < 1e-12


def test_radial_power_spectrum_shape():
    fr, ps = synth.radial_power_spectrum(_pink(32, 32, 0), nbins=16)
    assert fr.shape == (16,) and ps.shape == (16,)
    assert np.isfinite(ps).all()


# --------------------------------------------------------------------------- #
# patch / quilting
# --------------------------------------------------------------------------- #
def test_patch_quilting_enlarges_and_resembles():
    h = w = 96
    yy, xx = np.mgrid[0:h, 0:w]
    chk = ((xx // 12 + yy // 12) % 2).astype(float)
    q = synth.synthesize_like(chk, size=(160, 160), seed=2, method="patch",
                              block=32, overlap=8)
    assert q.shape == (160, 160)
    assert np.isfinite(q).all() and q.min() >= 0.0 and q.max() <= 1.0
    # resembles the exemplar (structured texture) — bounded feature distance
    d = synth.feature_distance(chk, q)
    assert d["hist_chi2"] < 0.2
    # not a single verbatim crop of the exemplar
    assert not np.array_equal(q[:h, :w], chk)


def test_patch_quilting_deterministic():
    src = _pink(64, 64, 6)
    a = synth.synthesize_like(src, size=(96, 96), seed=1, method="patch", block=24, overlap=6)
    b = synth.synthesize_like(src, size=(96, 96), seed=1, method="patch", block=24, overlap=6)
    assert np.array_equal(a, b)


# --------------------------------------------------------------------------- #
# edge cases / contracts
# --------------------------------------------------------------------------- #
def test_constant_image_does_not_crash():
    const = np.full((32, 32), 0.5)
    out = synth.synthesize_like(const, seed=0, method="spectral")
    assert out.shape == (32, 32) and np.isfinite(out).all()


def test_tiny_image():
    tiny = np.array([[0.1, 0.9], [0.8, 0.2]])
    out = synth.synthesize_like(tiny, seed=0, method="spectral")
    assert out.shape == (2, 2) and np.isfinite(out).all()


def test_color_input_reduced_to_gray():
    src = np.stack([_pink(48, 48, i) for i in range(3)], axis=2)
    out = synth.synthesize_like(src, seed=0, method="spectral")
    assert out.ndim == 2 and out.shape == (48, 48)


def test_invalid_args_fail_closed():
    src = _pink(32, 32, 0)
    with pytest.raises(ValueError):
        synth.synthesize_like(src, size=(1, 1))
    with pytest.raises(ValueError):
        synth.synthesize_like(src, method="nope")


# --------------------------------------------------------------------------- #
# facade
# --------------------------------------------------------------------------- #
def test_facade_exposes_synth():
    import fullseye
    src = _pink(48, 48, 0)
    out = fullseye.synthesize_like(src, seed=1)
    assert out.shape == src.shape
    feats = fullseye.learn_features(src)
    assert "histogram" in feats and "radial_power" in feats
    d = fullseye.feature_distance(src, out)
    assert d["spectrum_l2"] < 0.05
