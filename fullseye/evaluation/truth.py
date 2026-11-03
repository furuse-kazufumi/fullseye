# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Truth bundle contract for PoC evaluation.

The bundle shape is taken from the field dictionaries returned by the first-wave
truth builders, in particular ``poc_pv_thermal_survey.ground_truth``.  The shared
layer adds only information those dictionaries lacked: unit, coordinate frame,
mask meaning, processing stage, provenance, and seed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np


class TruthContractError(ValueError):
    """A truth bundle is ambiguous or internally inconsistent."""


_MASK_MEANINGS = frozenset({"valid", "ignore", "defect"})
_STAGES = frozenset({"raw-pre-isp", "isp-post", "physical", "synthetic"})
_IMAGE_FRAMES = frozenset({"image-row-col", "image-row-col-raw", "image-row-col-isp"})
_PHYSICAL_FRAMES = frozenset({"physical-x-y-z", "physical-x-y", "physical-z"})
_OTHER_FRAMES = frozenset({"scalar", "time", "index", "label"})
_FRAMES = _IMAGE_FRAMES | _PHYSICAL_FRAMES | _OTHER_FRAMES


@dataclass(frozen=True)
class TruthBundle:
    """Named truth fields plus the metadata required to interpret each field.

    ``units`` and ``frames`` must name every field exactly.  Frame vocabulary keeps
    array indices (row/col) distinct from physical axes (x/y/z).  Masks are named by
    meaning rather than by a generic ``mask`` key.  ``provenance['processing_stage']``
    explicitly says whether image truth is before or after the ISP.
    """

    fields: Mapping[str, Any]
    units: Mapping[str, str]
    frames: Mapping[str, str]
    masks: Mapping[str, Any]
    provenance: Mapping[str, Any]
    seed: int | None

    def __post_init__(self) -> None:
        fields = dict(self.fields)
        units = dict(self.units)
        frames = dict(self.frames)
        masks = dict(self.masks)
        provenance = dict(self.provenance)
        if not fields:
            raise TruthContractError("TruthBundle.fields must not be empty")
        names = set(fields)
        if set(units) != names:
            raise TruthContractError(_key_difference("units", names, set(units)))
        if set(frames) != names:
            raise TruthContractError(_key_difference("frames", names, set(frames)))
        for name, unit in units.items():
            if not isinstance(unit, str) or not unit:
                raise TruthContractError(f"unit for {name!r} must be a non-empty string")
        for name, frame in frames.items():
            if frame not in _FRAMES:
                raise TruthContractError(
                    f"frame for {name!r} is {frame!r}; use an explicit row/col or x/y/z frame"
                )
            _validate_field_frame(name, fields[name], frame)
        unknown_masks = set(masks) - _MASK_MEANINGS
        if unknown_masks:
            raise TruthContractError(
                "mask keys state their meaning and must be valid/ignore/defect; got %s"
                % sorted(unknown_masks)
            )
        for meaning, mask in masks.items():
            arr = np.asarray(mask)
            if arr.dtype != np.bool_:
                raise TruthContractError(f"{meaning} mask must have boolean dtype")
            if arr.size == 0:
                raise TruthContractError(f"{meaning} mask must not be empty")
            if not any(_mask_matches(arr.shape, np.shape(value)) for value in fields.values()):
                raise TruthContractError(
                    f"{meaning} mask shape {arr.shape} does not match any truth field"
                )
        stage = provenance.get("processing_stage")
        if stage not in _STAGES:
            raise TruthContractError(
                "provenance.processing_stage must be raw-pre-isp, isp-post, physical, or synthetic"
            )
        if any(frame == "image-row-col-raw" for frame in frames.values()) and stage != "raw-pre-isp":
            raise TruthContractError("raw image frame requires processing_stage='raw-pre-isp'")
        if any(frame == "image-row-col-isp" for frame in frames.values()) and stage != "isp-post":
            raise TruthContractError("ISP image frame requires processing_stage='isp-post'")
        if self.seed is not None and (isinstance(self.seed, bool) or not isinstance(self.seed, int)):
            raise TruthContractError("seed must be int or None")
        object.__setattr__(self, "fields", fields)
        object.__setattr__(self, "units", units)
        object.__setattr__(self, "frames", frames)
        object.__setattr__(self, "masks", masks)
        object.__setattr__(self, "provenance", provenance)

    def as_dict(self) -> dict[str, Any]:
        return {
            "fields": dict(self.fields),
            "units": dict(self.units),
            "frames": dict(self.frames),
            "masks": dict(self.masks),
            "provenance": dict(self.provenance),
            "seed": self.seed,
        }


def _key_difference(label: str, expected: set[str], actual: set[str]) -> str:
    return "%s keys must equal field keys (missing=%s, extra=%s)" % (
        label,
        sorted(expected - actual),
        sorted(actual - expected),
    )


def _validate_field_frame(name: str, value: Any, frame: str) -> None:
    shape = np.shape(value)
    if frame == "physical-x-y-z" and (not shape or shape[-1] != 3):
        raise TruthContractError(
            f"field {name!r} uses physical-x-y-z but its last axis is not length 3: {shape}"
        )
    if frame == "physical-x-y" and (not shape or shape[-1] != 2):
        raise TruthContractError(
            f"field {name!r} uses physical-x-y but its last axis is not length 2: {shape}"
        )
    if frame in _IMAGE_FRAMES and len(shape) < 2:
        raise TruthContractError(f"field {name!r} uses row/col but has shape {shape}")
    if frame in _IMAGE_FRAMES and len(shape) == 2 and shape[-1] in (2, 3) and name.endswith("_xyz"):
        raise TruthContractError(
            f"field {name!r} looks like physical coordinates but declares row/col"
        )


def _mask_matches(mask_shape: tuple[int, ...], field_shape: tuple[int, ...]) -> bool:
    return mask_shape == field_shape or (len(field_shape) > len(mask_shape) and field_shape[: len(mask_shape)] == mask_shape)
