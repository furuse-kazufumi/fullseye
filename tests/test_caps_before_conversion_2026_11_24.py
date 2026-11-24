"""Regression gates: oversized zero-stride inputs must fail before conversion.

Each array below has the reported logical shape but is backed by one uint8.  The
patched conversion therefore proves call order without allocating the multi-GB
float64 copy that the public cap is intended to prevent.
"""
from __future__ import annotations

import numpy as np
import pytest

import astrostack as AS
import deconvstop as DS
import hdrfusion as HF
import lockin as LI
import sensitivity as SN
import volregion as VR


def _zero_stride(shape):
    """Logical *shape*, one-byte storage: safe only for a pre-conversion gate."""
    return np.lib.stride_tricks.as_strided(
        np.zeros(1, dtype=np.uint8), shape=shape, strides=(0,) * len(shape))


def _conversion_must_not_run(*_args, **_kwargs):
    raise AssertionError("conversion/copy was attempted before the cap validation")


def test_vol_rle_cap_is_checked_before_contiguous_copy(monkeypatch):
    vol = _zero_stride((513, 512, 512))
    expected = 513 * 512 * 512
    monkeypatch.setattr(VR.np, "ascontiguousarray", _conversion_must_not_run)
    with pytest.raises(ValueError, match=rf"{expected} elements.*cap"):
        VR.vol_rle_encode(vol)


@pytest.mark.parametrize(
    ("fn", "args", "shape", "frames"),
    [
        (LI.lockin_ring_synthesize, (45.0, 3, 1, 3, 1), (4097, 1366), 3),
        (LI.lockin_thermal_wave, (1.0e-6, 1.0e-6, 3, 1), (4097, 1366), 3),
    ],
)
def test_lockin_synthesis_caps_precede_float64_conversion(monkeypatch, fn, args, shape, frames):
    image = _zero_stride(shape)
    expected = frames * shape[0] * shape[1]
    monkeypatch.setattr(LI.np, "asarray", _conversion_must_not_run)
    with pytest.raises(ValueError, match=rf"{expected} elements.*cap"):
        fn(image, *args)


def test_hdr_series_cap_is_checked_before_float64_conversion(monkeypatch):
    radiance = _zero_stride((4097, 8192))
    expected = 4097 * 8192
    monkeypatch.setattr(HF.np, "asarray", _conversion_must_not_run)
    with pytest.raises(ValueError, match=rf"{expected} elements.*cap"):
        HF.hdr_exposure_series_simulate(radiance, [1.0])


@pytest.mark.parametrize(
    ("fn", "shape", "kwargs"),
    [
        (SN.mv_confounding, (2, 25_000_001), {}),
        (SN.mv_residual_pca, (3, 16_666_668), {"noise_sigma": 1.0}),
    ],
)
def test_multivariate_caps_precede_float64_conversion(monkeypatch, fn, shape, kwargs):
    matrix = _zero_stride(shape)
    expected = shape[0] * shape[1]
    monkeypatch.setattr(SN.np, "asarray", _conversion_must_not_run)
    with pytest.raises(ValueError, match=rf"{expected} elements.*cap"):
        fn(matrix, **kwargs)


def test_richardson_lucy_cap_is_checked_before_float64_conversion(monkeypatch):
    image = _zero_stride((4001, 4000))
    expected = 4001 * 4000
    monkeypatch.setattr(DS.np, "asarray", _conversion_must_not_run)
    with pytest.raises(ValueError, match=rf"{expected} elements.*cap"):
        DS.iv_richardson_lucy_until(image)


def test_lucky_select_cap_is_checked_before_float64_conversion(monkeypatch):
    image = _zero_stride((4097, 4096))
    expected = 4097 * 4096
    monkeypatch.setattr(AS.np, "asarray", _conversion_must_not_run)
    with pytest.raises(ValueError, match=rf"{expected} elements.*cap"):
        AS.lucky_select([image])
