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
    _yy, xx = np.mgrid[0:h, 0:w]
    grating = 0.5 + 0.4 * np.sin(2 * np.pi * 8 * xx / w)   # true freq 8/128 = 0.0625 cyc/px
    out = synth.synthesize_like(grating, seed=1, method="spectral")
    fr, ps = synth.radial_power_spectrum(grating)
    fr2, ps2 = synth.radial_power_spectrum(out)
    peak_src = fr[np.argmax(ps[1:]) + 1]
    peak_out = fr2[np.argmax(ps2[1:]) + 1]
    assert abs(peak_src - peak_out) < 0.02
    # the frequency axis is physically correct (Nyquist=0.5 at radius N/2), so the
    # reported peak matches the TRUE 0.0625 cyc/px (not the ~0.039 of the old axis).
    assert abs(peak_out - 0.0625) < 0.01, peak_out


def test_match_histogram_nearest_rank_no_invented_values():
    # tied (discrete) reference + different size: output must contain ONLY values
    # that exist in ref (nearest-rank), never interpolated in-betweens.
    ref = np.array([[0.0, 1.0], [1.0, 0.0]])          # only {0, 1}
    src = np.random.default_rng(0).standard_normal((6, 6))
    out = synth.match_histogram(src, ref)
    assert set(np.unique(out)).issubset({0.0, 1.0})
    # equal sizes -> exact rank mapping
    src2 = np.random.default_rng(1).standard_normal((2, 2))
    out2 = synth.match_histogram(src2, ref)
    assert sorted(out2.ravel()) == sorted(ref.ravel())


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
# pyramid (multi-scale Heeger-Bergen): per-scale marginals the single-band can't
# --------------------------------------------------------------------------- #
def _multiscale_tex(h, w, seed):
    """Smooth low-frequency base + SPARSE impulsive fine detail. The fine-scale
    (Laplacian) band is heavy-tailed/sparse — a per-scale marginal NOT implied by the
    global amplitude spectrum + intensity histogram, so it separates pyramid from
    spectral synthesis."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w]
    coarse = 0.5 + 0.22 * np.sin(2 * np.pi * 3 * xx / w) + 0.14 * np.cos(2 * np.pi * 2 * yy / h)
    fine = np.zeros((h, w))
    n = (h * w) // 40
    ys, xs = rng.integers(0, h, n), rng.integers(0, w, n)
    fine[ys, xs] = rng.choice([-1.0, 1.0], n) * rng.uniform(0.3, 0.5, n)   # sparse spikes
    return np.clip(coarse + fine, 0.0, 1.0)


def test_pyramid_matches_features_and_is_novel():
    src = _pink(128, 128, 0)
    syn = synth.synthesize_like(src, seed=5, method="pyramid")
    d = synth.feature_distance(src, syn)
    assert d["hist_chi2"] < 0.02                          # global marginal matched tightly
    # HONEST scope: pyramid matches per-SCALE MARGINALS, not the exact amplitude spectrum,
    # so its spectrum_l2 (~0.28 here) is LOOSER than the spectral method's (< 0.05). It
    # preserves the general spectral character, not the fine 2nd-order fit — the two
    # methods are complementary (pyramid's win is per-scale marginals; see the next test).
    assert d["spectrum_l2"] < 0.4
    ind = _pink(128, 128, 999)
    nov_syn = synth.patch_novelty(syn, src, seed=1)
    nov_ind = synth.patch_novelty(ind, src, seed=1)
    assert nov_syn > 0.5 * nov_ind                        # genuinely new, not a copy
    assert not np.array_equal(syn, src)


def test_pyramid_matches_per_scale_marginals_better_than_spectral():
    # the honest "deepening" claim, MEASURED: on a texture with scale-dependent marginals
    # the pyramid method matches the per-band marginals; the single-band spectral does not.
    src = _multiscale_tex(128, 128, 0)
    pyr = synth.synthesize_like(src, seed=1, method="pyramid")
    spec = synth.synthesize_like(src, seed=1, method="spectral")
    d_pyr = synth.pyramid_stat_distance(src, pyr)
    d_spec = synth.pyramid_stat_distance(src, spec)
    assert d_pyr < d_spec, (d_pyr, d_spec)                # pyramid matches per-scale marginals better
    # ...and the pyramid result is still novel + matches the global marginal
    assert synth.patch_novelty(pyr, src, seed=1) > 0.0
    assert synth.feature_distance(src, pyr)["hist_chi2"] < 0.05


def test_pyramid_stat_distance_zero_for_identical():
    src = _multiscale_tex(96, 96, 2)
    assert synth.pyramid_stat_distance(src, src) < 1e-9


def test_pyramid_is_deterministic_and_size_controlled():
    src = _pink(64, 64, 3)
    a = synth.synthesize_like(src, seed=7, method="pyramid")
    b = synth.synthesize_like(src, seed=7, method="pyramid")
    assert np.array_equal(a, b)
    out = synth.synthesize_like(src, size=(96, 128), seed=2, method="pyramid")
    assert out.shape == (96, 128) and np.isfinite(out).all()
    assert out.min() >= 0.0 and out.max() <= 1.0


def test_pyramid_edge_cases_do_not_crash():
    assert synth.synthesize_like(np.full((32, 32), 0.5), seed=0, method="pyramid").shape == (32, 32)
    assert synth.synthesize_like(np.array([[0.1, 0.9], [0.8, 0.2]]), seed=0, method="pyramid").shape == (2, 2)


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


def test_nonfinite_input_fails_closed():
    with pytest.raises(ValueError):
        synth.synthesize_like(np.full((32, 32), np.nan))
    with pytest.raises(ValueError):
        synth.synthesize_like(np.full((16, 16), np.inf), method="patch")


def test_patch_novelty_detects_verbatim_copy():
    src = _pink(64, 64, 0)
    # an exact crop of the source scores ~0; an independent image scores clearly higher
    crop = src.copy()
    nov_copy = synth.patch_novelty(crop, src, seed=0)
    nov_indep = synth.patch_novelty(_pink(64, 64, 123), src, seed=0)
    assert nov_copy < 1e-9
    assert nov_indep > 10 * max(nov_copy, 1e-6)


def test_patch_quilting_is_bounded_in_time():
    # the candidate cap bounds the search: a documented call must not hang.
    import time
    src = _pink(160, 160, 0)
    t = time.perf_counter()
    out = synth.synthesize_like(src, size=(256, 256), seed=0, method="patch",
                                block=32, overlap=8)
    dt = time.perf_counter() - t
    assert out.shape == (256, 256) and np.isfinite(out).all()
    assert dt < 20.0, f"quilting took {dt:.1f}s (candidate cap should bound it)"


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
    assert fullseye.pyramid_stat_distance(src, src) < 1e-9        # per-scale metric exposed


def test_cli_synth_subcommand(tmp_path, capsys):
    import types

    import imgevolve
    import imgio
    inp = tmp_path / "ex.png"
    out = tmp_path / "syn.png"
    imgio.save(str(inp), _pink(64, 64, 0))
    rc = imgevolve.cmd_synth(types.SimpleNamespace(
        inp=str(inp), out=str(out), method="spectral", size="", seed=1))
    assert rc == 0 and out.exists()
    assert "spectrum_l2" in capsys.readouterr().out
    assert imgio.load(str(out)).shape == (64, 64)
