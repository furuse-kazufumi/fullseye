"""Regression coverage for every additional static cap/coercion match.

The static extractor found these shared validators after the original eight
public-operator reports.  Each virtual input is one uint8 in storage; replacing
the next conversion proves that the named cap rejects it first.
"""
from __future__ import annotations

import numpy as np
import pytest

import aoi as AOI
import dualxray as DX
import illumdesign as IL
import imgforensics as IF
import lensimage as LIM
import live4d as L4
import segcompare as SC
import segcontour as SCT
import seggraph as SG
import sfpolar as SP
import videocube as VC
import visiondesign as VD
import volfreq as VF
import volprobe as VP
import volrestore as VR
import volxform as VX


def _zero_stride(shape):
    return np.lib.stride_tricks.as_strided(
        np.zeros(1, dtype=np.uint8), shape=shape, strides=(0,) * len(shape))


def _conversion_must_not_run(*_args, **_kwargs):
    raise AssertionError("conversion/copy was attempted before the cap validation")


_CASES = [
    pytest.param(AOI, "asarray", lambda a: AOI._require_image(a, "image", "aoi_op"),
                 (2, AOI.MAX_IMAGE_ELEMENTS // 2 + 1), id="aoi-image"),
    pytest.param(IL, "asarray", lambda a: IL.illumination_uniformity(a),
                 (2, IL.MAX_MAP_ELEMENTS // 2 + 1), id="illumdesign-map"),
    pytest.param(IF, "asarray", lambda a: IF._as_image(a),
                 (2, IF.MAX_PIXELS // 2 + 1), id="imgforensics-image"),
    pytest.param(LIM, "asarray", lambda a: LIM._image(a),
                 (2, LIM.MAX_IMAGE_PIXELS // 2 + 1), id="lensimage-image"),
    pytest.param(L4, "asarray", lambda a: L4._series(a, "live4d_op"),
                 (2, 2, 2, L4.MAX_SERIES_ELEMENTS // 8 + 1), id="live4d-series"),
    pytest.param(L4, "asarray", lambda a: L4._vol(a, "live4d_op", "vol"),
                 (2, 2, L4.MAX_SERIES_ELEMENTS // 4 + 1), id="live4d-volume"),
    pytest.param(SC, "asarray", lambda a: SC._labels(a, "labels", "segcompare_op"),
                 (2, SC.MAX_SEG_PIXELS // 2 + 1), id="segcompare-labels"),
    pytest.param(SCT, "asarray", lambda a: SCT._image(a, "image", "segcontour_op"),
                 (2, SCT.MAX_PIXELS // 2 + 1), id="segcontour-image"),
    pytest.param(SG, "asarray", lambda a: SG._image(a, "image", "seggraph_op"),
                 (2, SG.MAX_PIXELS // 2 + 1), id="seggraph-image"),
    pytest.param(SP, "asarray", lambda a: SP._real(a, "map", "sfpolar_op"),
                 (2, SP.MAX_PIXELS * 2 + 1), id="sfpolar-map"),
    pytest.param(VC, "asarray", lambda a: VC._video(a, "videocube_op"),
                 (2, 2, VC.MAX_CUBE_ELEMENTS // 4 + 1), id="videocube-video"),
    pytest.param(VC, "asarray", lambda a: VC._cube(a, "videocube_op"),
                 (2, 2, VC.MAX_CUBE_ELEMENTS // 4 + 1), id="videocube-cube"),
    pytest.param(VD, "asarray", lambda a: VD.image_formation(a, vignetting=False),
                 (2, VD.MAX_IMAGE_PIXELS // 2 + 1), id="visiondesign-image"),
    pytest.param(VP, "ascontiguousarray", lambda a: VP._require_volume(a),
                 (2, 2, VP.MAX_VOXELS // 4 + 1), id="volprobe-volume"),
    pytest.param(VR, "ascontiguousarray", lambda a: VR._require_volume(a),
                 (2, 2, VR.MAX_VOXELS // 4 + 1), id="volrestore-volume"),
    pytest.param(VX, "ascontiguousarray", lambda a: VX._require_volume(a),
                 (2, 2, VX.MAX_VOXELS // 4 + 1), id="volxform-volume"),
    pytest.param(VF, "ascontiguousarray", lambda a: VF._require_volume(a),
                 (2, 2, VF.MAX_VOXELS // 4 + 1), id="volfreq-volume"),
]

_CAP_DETAILS = {
    AOI: (AOI.MAX_IMAGE_ELEMENTS, "scipy.ndimage.zoom"),
    IL: (IL.MAX_MAP_ELEMENTS, "scipy.ndimage.zoom"),
    IF: (IF.MAX_PIXELS, "scipy.ndimage.zoom"),
    LIM: (LIM.MAX_IMAGE_PIXELS, "scipy.ndimage.zoom"),
    L4: (L4.MAX_SERIES_ELEMENTS, "process"),
    SC: (SC.MAX_SEG_PIXELS, "scipy.ndimage.zoom"),
    SCT: (SCT.MAX_PIXELS, "scipy.ndimage.zoom"),
    SG: (SG.MAX_PIXELS, "scipy.ndimage.zoom"),
    SP: (SP.MAX_PIXELS * 4, "scipy.ndimage.zoom"),
    VC: (VC.MAX_CUBE_ELEMENTS, "process"),
    VD: (VD.MAX_IMAGE_PIXELS, "scipy.ndimage.zoom"),
    VF: (VF.MAX_VOXELS, "volops.volume_downsample"),
    VP: (VP.MAX_VOXELS, "volops.volume_downsample"),
    VR: (VR.MAX_VOXELS, "volops.volume_downsample"),
    VX: (VX.MAX_VOXELS, "volops.volume_downsample"),
}


@pytest.mark.parametrize(("module", "conversion", "call", "shape"), _CASES)
def test_static_cap_matches_are_refused_before_conversion(monkeypatch, module, conversion, call, shape):
    virtual = _zero_stride(shape)
    monkeypatch.setattr(module.np, conversion, _conversion_must_not_run)
    with pytest.raises(ValueError, match="exceeding the limit") as error:
        call(virtual)
    cap, remedy = _CAP_DETAILS[module]
    message = str(error.value)
    assert f"{int(np.prod(shape)):,} elements" in message
    assert f"{cap:,} elements" in message
    assert "input dtype uint8" in message
    assert f"{int(np.prod(shape)) * np.dtype(np.float64).itemsize:,} bytes" in message
    assert remedy in message and "Why:" in message and "対処:" in message


def test_dual_xray_channel_count_is_checked_before_float64_conversion(monkeypatch):
    n = DX.MAX_CHANNELS + 1
    channels = {
        "energy_kev": np.ones(3, dtype=np.uint8),
        "weights": _zero_stride((n, 3)),
        "gain": np.ones(3, dtype=np.uint8),
        "mode": "energy_integrating",
    }
    monkeypatch.setattr(DX.np, "asarray", _conversion_must_not_run)
    with pytest.raises(ValueError) as error:
        DX._channels(channels, "dual_xray_op")
    message = str(error.value)
    assert f"{n} channels" in message and f"{DX.MAX_CHANNELS} channels" in message
    assert "thresholds_kev" in message and "対処:" in message
