"""Ground-truth tests for the complex-image module (complexops.py).

The claims under test, one anchor apiece: the FFT round-trips, the
magnitude/phase decomposition recomposes the exact field, phase unwrapping
recovers a known continuous ramp up to a constant (the differentiator HALCON
lacks), Wiener deconvolution measurably reverses a known blur, a transfer
function filters a spectrum, and every op fails closed on malformed input.

These are plain module functions (like mesh / pointcloud / volops), so they are
imported directly as ``complexops`` — the ``fullseye`` facade wiring is done
elsewhere and is not exercised here.
"""
import numpy as np
import pytest
from scipy import ndimage

import complexops as cx


# --------------------------------------------------------------------------- #
# deterministic test images                                                    #
# --------------------------------------------------------------------------- #
def _image(n=64):
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    grad = xx / (n - 1)
    disk = ((yy - n * 0.35) ** 2 + (xx - n * 0.4) ** 2) < (n * 0.18) ** 2
    checker = ((xx.astype(int) // 6 + yy.astype(int) // 6) % 2) * 0.15
    rng = np.random.default_rng(20260814)
    return np.clip(0.35 * grad + 0.45 * disk + checker
                   + 0.03 * rng.standard_normal((n, n)), 0.0, 1.0)


def _gauss_psf(size=15, sigma=2.0):
    r = np.arange(size) - (size - 1) / 2.0
    g = np.exp(-(r[:, None] ** 2 + r[None, :] ** 2) / (2.0 * sigma ** 2))
    return g / g.sum()


# --------------------------------------------------------------------------- #
# transform round-trip                                                         #
# --------------------------------------------------------------------------- #
def test_fft_ifft_round_trips_an_image():
    img = _image()
    spec = cx.cx_fft(img)
    assert spec.dtype == np.complex128 and spec.shape == img.shape
    back = cx.cx_ifft(spec, real=True)
    assert back.dtype == np.float64
    assert np.allclose(back, img, atol=1e-10)


def test_ifft_complex_recovers_full_field():
    img = _image(32)
    field = cx.cx_ifft(cx.cx_fft(img), real=False)
    assert np.iscomplexobj(field)
    assert np.allclose(field.real, img, atol=1e-10)
    assert np.allclose(field.imag, 0.0, atol=1e-10)     # a real image has ~zero imaginary part


# --------------------------------------------------------------------------- #
# magnitude / phase decomposition + recomposition                             #
# --------------------------------------------------------------------------- #
def test_magnitude_phase_decompose_and_recompose_exactly():
    spec = cx.cx_fft(_image())
    mag = cx.cx_magnitude(spec)                          # raw |cx| (metric, not [0,1])
    phase = cx.cx_phase(spec, display=False)             # raw radians in (-pi, pi]
    recomposed = cx.cx_from_mag_phase(mag, phase)
    assert recomposed.dtype == np.complex128
    assert np.allclose(recomposed, spec, atol=1e-9)


def test_phase_display_maps_zero_to_half():
    # a constant real field -> its spectrum is a single real DC spike (phase 0)
    spec = cx.cx_fft(np.full((16, 16), 0.5))
    disp = cx.cx_phase(spec, display=True)
    assert disp.min() >= 0.0 and disp.max() <= 1.0
    dc = disp[8, 8]                                      # centred spectrum: DC at the middle
    assert abs(dc - 0.5) < 1e-9                          # zero phase -> 0.5


def test_real_imag_and_log_magnitude_shapes_and_domain():
    spec = cx.cx_fft(_image(32))
    assert cx.cx_real(spec).shape == (32, 32)
    assert cx.cx_imag(spec).shape == (32, 32)
    logm = cx.cx_log_magnitude(spec)
    assert logm.min() >= 0.0 and logm.max() <= 1.0 + 1e-12   # display-normalised


def test_real_input_to_complex_op_is_ffted():
    """A real image handed to a complex-only op is interpreted as spatial and
    FFT'd (documented): cx_magnitude(image) == |cx_fft(image)|."""
    img = _image(32)
    assert np.allclose(cx.cx_magnitude(img), np.abs(cx.cx_fft(img)))


# --------------------------------------------------------------------------- #
# phase unwrapping — the differentiator                                        #
# --------------------------------------------------------------------------- #
def _assert_unwraps_to(ramp):
    wrapped = np.angle(np.exp(1j * ramp))               # wrap into (-pi, pi]
    assert wrapped.max() <= np.pi + 1e-9 and wrapped.min() >= -np.pi - 1e-9
    assert (np.abs(wrapped - ramp) > 1.0).any()         # the ramp really did wrap
    unwrapped = cx.phase_unwrap(wrapped)
    assert unwrapped.dtype == np.float64
    resid = unwrapped - ramp                            # recovered up to a global constant
    assert np.allclose(resid - resid.mean(), 0.0, atol=1e-6)


def test_phase_unwrap_linear_ramp():
    n = 64
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    ramp = 0.30 * xx + 0.15 * yy                         # < pi/pixel, spans several 2*pi
    _assert_unwraps_to(ramp)


def test_phase_unwrap_quadratic_ramp():
    n = 64
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    ramp = 0.01 * (xx ** 2 + yy ** 2)                    # max adjacent step < pi
    _assert_unwraps_to(ramp)


def test_phase_unwrap_flat_stays_flat():
    out = cx.phase_unwrap(np.zeros((24, 24)))
    assert np.allclose(out, 0.0, atol=1e-12)
    # a non-zero constant wrapped phase unwraps to that same constant (flat)
    out2 = cx.phase_unwrap(np.full((24, 24), 0.7))
    assert float(out2.std()) < 1e-9


def test_phase_unwrap_matches_numpy_1d_reference_per_row():
    """On a clean 1-D-separable ramp, np.unwrap along a row is a ground truth for
    the recovered continuous phase (up to a per-row constant)."""
    n = 48
    xx = np.arange(n, dtype=np.float64)
    ramp = np.tile(0.4 * xx, (n, 1))                     # each row identical
    unwrapped = cx.phase_unwrap(np.angle(np.exp(1j * ramp)))
    row = unwrapped[n // 2]
    ref = np.unwrap(np.angle(np.exp(1j * (0.4 * xx))))
    assert np.allclose(row - row.mean(), ref - ref.mean(), atol=1e-6)


# --------------------------------------------------------------------------- #
# Wiener deconvolution                                                          #
# --------------------------------------------------------------------------- #
def test_wiener_reduces_error_versus_blurred_input():
    img = _image(96)
    psf = _gauss_psf(size=17, sigma=2.0)
    blurred = ndimage.convolve(img, psf, mode="wrap")   # circular blur == the Wiener model
    rng = np.random.default_rng(7)
    noisy = np.clip(blurred + 1e-3 * rng.standard_normal(img.shape), 0.0, 1.0)
    restored = cx.cx_wiener_deconvolve(noisy, psf, nsr=1e-3)
    assert restored.shape == img.shape
    assert restored.min() >= 0.0 and restored.max() <= 1.0
    mse_blur = float(np.mean((noisy - img) ** 2))
    mse_deconv = float(np.mean((restored - img) ** 2))
    assert mse_deconv < mse_blur, (mse_deconv, mse_blur)


# --------------------------------------------------------------------------- #
# transfer-function filtering                                                   #
# --------------------------------------------------------------------------- #
def _radial(shape):
    fy = np.fft.fftshift(np.fft.fftfreq(shape[0]))
    fx = np.fft.fftshift(np.fft.fftfreq(shape[1]))
    return np.sqrt(fy[:, None] ** 2 + fx[None, :] ** 2)


def test_transfer_function_unit_is_identity():
    spec = cx.cx_fft(_image(48))
    out = cx.cx_apply_transfer_function(spec, np.ones_like(spec))
    assert out.dtype == np.complex128
    assert np.allclose(out, spec)


def test_transfer_function_lowpass_removes_high_frequency_energy():
    img = _image(64)
    spec = cx.cx_fft(img)
    rad = _radial(img.shape)
    lp_mask = (rad <= 0.12).astype(np.float64)           # keep only low frequencies
    filtered = cx.cx_apply_transfer_function(spec, lp_mask)
    hi = rad > 0.30
    e_before = float((np.abs(spec[hi]) ** 2).sum())
    e_after = float((np.abs(filtered[hi]) ** 2).sum())
    assert e_before > 0.0
    assert e_after < 1e-9 * e_before                     # high-band energy is gone


# --------------------------------------------------------------------------- #
# convenience band-pass                                                         #
# --------------------------------------------------------------------------- #
def test_bandpass_returns_display_image():
    out = cx.cx_bandpass(_image(48), low=0.05, high=0.25)
    assert out.shape == (48, 48) and out.dtype == np.float64
    assert out.min() >= 0.0 and out.max() <= 1.0


# --------------------------------------------------------------------------- #
# fail-closed on malformed input                                              #
# --------------------------------------------------------------------------- #
def test_one_dimensional_input_is_refused():
    with pytest.raises(ValueError):
        cx.cx_fft(np.arange(10, dtype=np.float64))
    with pytest.raises(ValueError):
        cx.cx_magnitude(np.arange(10, dtype=np.float64))
    with pytest.raises(ValueError):
        cx.phase_unwrap(np.linspace(0.0, 1.0, 10))


def test_non_finite_input_is_refused():
    bad = _image(16)
    bad[0, 0] = np.nan
    with pytest.raises(ValueError):
        cx.cx_fft(bad)
    field = cx.cx_fft(_image(16)).copy()
    field[1, 1] = np.inf
    with pytest.raises(ValueError):
        cx.cx_magnitude(field)                            # non-finite complex field
    with pytest.raises(ValueError):
        cx.phase_unwrap(bad)


def test_complex_image_to_real_op_is_refused():
    with pytest.raises(ValueError):
        cx.cx_fft(cx.cx_fft(_image(16)))                  # a complex array is not an image


def test_wiener_rejects_bad_psf_and_nsr():
    img = _image(32)
    with pytest.raises(ValueError):
        cx.cx_wiener_deconvolve(img, np.zeros((5, 5)))    # zero-sum PSF
    with pytest.raises(ValueError):
        cx.cx_wiener_deconvolve(img, np.ones((5, 5, 5)))  # 3-D PSF
    with pytest.raises(ValueError):
        cx.cx_wiener_deconvolve(img, np.ones((64, 64)) / 4096)  # PSF larger than image
    with pytest.raises(ValueError):
        cx.cx_wiener_deconvolve(img, _gauss_psf(9, 1.5), nsr=0.0)  # nsr must be > 0


def test_from_mag_phase_and_transfer_function_shape_checks():
    with pytest.raises(ValueError):
        cx.cx_from_mag_phase(np.ones((8, 8)), np.ones((8, 9)))    # mismatched shapes
    spec = cx.cx_fft(_image(16))
    with pytest.raises(ValueError):
        cx.cx_apply_transfer_function(spec, np.ones((16, 15)))    # H shape mismatch


def test_unknown_and_unimplemented_unwrap_methods_raise():
    w = np.angle(np.exp(1j * np.zeros((8, 8))))
    with pytest.raises(ValueError):
        cx.phase_unwrap(w, method="goldstein")            # documented, not implemented
    with pytest.raises(ValueError):
        cx.phase_unwrap(w, method="nonsense")


# --------------------------------------------------------------------------- #
# introspection                                                                #
# --------------------------------------------------------------------------- #
def test_complexops_namelist_is_consistent():
    for name in cx.COMPLEXOPS:
        assert hasattr(cx, name) and callable(getattr(cx, name)), name
    assert set(cx.COMPLEXOPS) == set(cx.__all__) - {"COMPLEXOPS"}
