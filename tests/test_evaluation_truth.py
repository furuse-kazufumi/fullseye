"""TruthBundle rejects coordinate, unit, stage, and mask ambiguity."""

import numpy as np
import pytest

from fullseye.evaluation.truth import TruthBundle, TruthContractError


def _bundle(**changes):
    values = {
        "fields": {"depth": np.ones((4, 5))},
        "units": {"depth": "mm"},
        "frames": {"depth": "image-row-col-isp"},
        "masks": {"valid": np.ones((4, 5), bool)},
        "provenance": {"processing_stage": "isp-post", "generator": "test"},
        "seed": 7,
    }
    values.update(changes)
    return TruthBundle(**values)


def test_truth_bundle_accepts_explicit_image_contract():
    truth = _bundle()
    assert truth.units["depth"] == "mm"
    assert truth.frames["depth"] == "image-row-col-isp"
    assert truth.seed == 7


def test_truth_bundle_detects_unit_frame_and_stage_mixups():
    with pytest.raises(TruthContractError, match="units keys"):
        _bundle(units={})
    with pytest.raises(TruthContractError, match="last axis is not length 3"):
        _bundle(frames={"depth": "physical-x-y-z"})
    with pytest.raises(TruthContractError, match="ISP image frame"):
        _bundle(provenance={"processing_stage": "raw-pre-isp"})


def test_truth_bundle_detects_mask_meaning_dtype_and_shape():
    with pytest.raises(TruthContractError, match="valid/ignore/defect"):
        _bundle(masks={"roi": np.ones((4, 5), bool)})
    with pytest.raises(TruthContractError, match="boolean dtype"):
        _bundle(masks={"valid": np.ones((4, 5), np.uint8)})
    with pytest.raises(TruthContractError, match="does not match"):
        _bundle(masks={"valid": np.ones((2, 2), bool)})
