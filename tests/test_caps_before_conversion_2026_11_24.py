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


def _assert_kind_cap_message(error, actual, cap, remedy):
    """親切な拒否が実測値、上限、直し方を日英で伝える。"""
    message = str(error.value)
    assert f"{actual:,} elements" in message
    assert f"{cap:,} elements" in message
    assert "Why:" in message and "理由:" in message
    assert remedy in message and "対処:" in message


def test_vol_rle_cap_is_checked_before_contiguous_copy(monkeypatch):
    vol = _zero_stride((513, 512, 512))
    expected = 513 * 512 * 512
    monkeypatch.setattr(VR.np, "ascontiguousarray", _conversion_must_not_run)
    with pytest.raises(ValueError) as error:
        VR.vol_rle_encode(vol)
    _assert_kind_cap_message(error, expected, VR.MAX_VOXELS, "volops.volume_downsample")


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
    with pytest.raises(ValueError) as error:
        fn(image, *args)
    _assert_kind_cap_message(error, expected, LI.MAX_VIDEO_ELEMENTS, "frames_per_period")


def test_hdr_series_cap_is_checked_before_float64_conversion(monkeypatch):
    radiance = _zero_stride((4097, 8192))
    expected = 4097 * 8192
    monkeypatch.setattr(HF.np, "asarray", _conversion_must_not_run)
    with pytest.raises(ValueError) as error:
        HF.hdr_exposure_series_simulate(radiance, [1.0])
    _assert_kind_cap_message(error, expected, HF.MAX_PIXELS, "scipy.ndimage.zoom")


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
    with pytest.raises(ValueError) as error:
        fn(matrix, **kwargs)
    _assert_kind_cap_message(error, expected, SN.MAX_ELEMENTS, "Subsample")


def test_richardson_lucy_cap_is_checked_before_float64_conversion(monkeypatch):
    image = _zero_stride((4001, 4000))
    expected = 4001 * 4000
    monkeypatch.setattr(DS.np, "asarray", _conversion_must_not_run)
    with pytest.raises(ValueError) as error:
        DS.iv_richardson_lucy_until(image)
    _assert_kind_cap_message(error, expected, DS.MAX_PIXELS, "scipy.ndimage.zoom")


def test_lucky_select_cap_is_checked_before_float64_conversion(monkeypatch):
    image = _zero_stride((4097, 4096))
    expected = 4097 * 4096
    monkeypatch.setattr(AS.np, "asarray", _conversion_must_not_run)
    with pytest.raises(ValueError) as error:
        AS.lucky_select([image])
    _assert_kind_cap_message(error, expected, AS.MAX_IMAGE_ELEMENTS, "scipy.ndimage.zoom")
