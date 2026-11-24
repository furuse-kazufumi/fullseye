"""Regression gates for the remaining pre-conversion input caps.

The virtual arrays below have their advertised logical shape while holding one
byte.  The fake frame lists similarly advertise a forbidden count without
allocating it.  Together they prove that the refusal happens before a dtype
copy, a frame conversion, or ``np.stack``.
"""
from __future__ import annotations

import numpy as np
import pytest

import balltrack as BT
import lockin as LI
import motionmag as MM
import quatimage as QI
import volfreq as VF
import volgray as VG
import volops as VO


def _zero_stride(shape):
    return np.lib.stride_tricks.as_strided(
        np.zeros(1, dtype=np.uint8), shape=shape, strides=(0,) * len(shape))


def _conversion_must_not_run(*_args, **_kwargs):
    raise AssertionError("conversion/copy was attempted before the cap validation")


class _NoAsarray:
    """Proxy used only to prove the module reaches its shared guard first."""

    def __init__(self, wrapped):
        self._wrapped = wrapped

    def __getattr__(self, name):
        if name == "asarray":
            return _conversion_must_not_run
        return getattr(self._wrapped, name)


class _TooManyFrames(list):
    """An empty list that reports a forbidden frame count without storing it."""

    def __init__(self, count):
        super().__init__()
        self._count = count

    def __len__(self):
        return self._count


@pytest.mark.parametrize("module", [VO, VG])
def test_volume_caps_precede_contiguous_float64_copy(monkeypatch, module):
    virtual = _zero_stride((2, 2, module.MAX_VOXELS // 4 + 1))
    monkeypatch.setattr(module.np, "ascontiguousarray", _conversion_must_not_run)
    with pytest.raises(ValueError, match="cap"):
        module._require_volume(virtual)


def test_volops_eigen_cap_precedes_contiguous_float64_copy(monkeypatch):
    virtual = _zero_stride((2, 2, VO.MAX_EIGEN_VOXELS // 4 + 1))
    monkeypatch.setattr(VO.np, "ascontiguousarray", _conversion_must_not_run)
    with pytest.raises(ValueError, match="MAX_EIGEN_VOXELS"):
        VO.vol_frangi(virtual)


def test_volfreq_list_or_array_cap_uses_shared_precheck_before_asarray(monkeypatch):
    virtual = _zero_stride((2, 2, VF.MAX_VOXELS // 4 + 1))
    monkeypatch.setattr(VF, "np", _NoAsarray(np))
    with pytest.raises(ValueError, match="cap"):
        VF._require_volume(virtual)


@pytest.mark.parametrize("module", [LI, MM, QI])
def test_video_frame_count_is_refused_before_frame_iteration(module):
    with pytest.raises(ValueError, match="MAX_FRAMES"):
        module._require_video(_TooManyFrames(module.MAX_FRAMES + 1), "video", "test", 1)


def test_lockin_total_list_cap_precedes_stack(monkeypatch):
    frames = [_zero_stride((1, LI.MAX_VIDEO_ELEMENTS // 3 + 1)) for _ in range(3)]
    monkeypatch.setattr(LI.np, "stack", _conversion_must_not_run)
    with pytest.raises(ValueError, match="cap"):
        LI._require_video(frames, "video", "test", LI.MAX_VIDEO_ELEMENTS)


@pytest.mark.parametrize("module", [MM, QI])
def test_video_total_list_cap_precedes_frame_conversion(monkeypatch, module):
    cap = module.MAX_PYRAMID_ELEMENTS
    frames = [_zero_stride((4, cap // 3 + 1)) for _ in range(3)]
    if module is MM:
        monkeypatch.setattr(module, "np", _NoAsarray(np))
    else:
        monkeypatch.setattr(module, "_require_image", _conversion_must_not_run)
    with pytest.raises(ValueError, match="cap"):
        module._require_video(frames, "video", "test", cap)


def test_track_triangulate_checks_all_view_counts_before_uv_allocation(monkeypatch):
    tracks = [
        {"frame": np.empty(0, np.int64), "col": np.empty(0), "row": np.empty(0)},
        {"frame": np.empty(0, np.int64), "col": np.empty(0), "row": np.empty(0)},
    ]
    monkeypatch.setattr(BT.np, "full", _conversion_must_not_run)
    with pytest.raises(ValueError, match="tracks, poses, and Ks"):
        BT.track_triangulate(tracks, [np.eye(4)], [np.eye(3)], n_frames=1)
