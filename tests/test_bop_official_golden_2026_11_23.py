"""Small synthetic golden errors checked against the official BOP toolkit.

Set ``BOP_TOOLKIT_ROOT`` to an explicit local checkout.  CI does not download the
toolkit; the stage-1 verification run pins and reports the checkout commit.
"""
from __future__ import annotations

import math
import os
from pathlib import Path
import sys

import numpy as np
import pytest


TOOLKIT_ROOT = os.environ.get("BOP_TOOLKIT_ROOT")
pytestmark = pytest.mark.skipif(not TOOLKIT_ROOT, reason="BOP_TOOLKIT_ROOT is not set")


class _SequenceDepthRenderer:
    """Return the synthetic estimate then truth, matching official VSD call order."""

    def __init__(self, estimate, truth):
        self._depths = iter((estimate, truth))

    def render_object(self, _obj_id, _R, _t, _fx, _fy, _cx, _cy):
        return {"depth": next(self._depths)}


def _official_pose_error():
    root = Path(TOOLKIT_ROOT).resolve()
    if not (root / "LICENSE").is_file():
        pytest.fail(f"BOP_TOOLKIT_ROOT has no LICENSE: {root}")
    sys.path.insert(0, str(root))
    try:
        from bop_toolkit_lib import pose_error
    finally:
        sys.path.pop(0)
    return pose_error


def test_official_vsd_mssd_mspd_match_synthetic_golden_values():
    pose_error = _official_pose_error()
    identity = np.eye(3)
    points = np.array([[-2.0, -1.0, 0.0], [3.0, -1.0, 0.0],
                       [0.5, 2.0, 0.0], [0.0, 0.0, 1.0]])
    symmetry_identity = [{"R": identity, "t": np.zeros((3, 1))}]

    # Every point moves by the signed translation (-2,+3,0), so max distance
    # is exactly sqrt(13), not a self-comparison or ratio-only assertion.
    mssd = pose_error.mssd(
        identity, np.array([[-2.0], [3.0], [100.0]]),
        identity, np.array([[0.0], [0.0], [100.0]]),
        points, symmetry_identity)
    assert mssd == pytest.approx(math.sqrt(13.0), abs=1e-12)

    # At Z=100 and fx=100, +2 model units in X is exactly +2 pixels.
    K = np.array([[100.0, 0.0, 2.0], [0.0, 100.0, 2.0], [0.0, 0.0, 1.0]])
    mspd = pose_error.mspd(
        identity, np.array([[2.0], [0.0], [100.0]]),
        identity, np.array([[0.0], [0.0], [100.0]]),
        K, points, symmetry_identity)
    assert mspd == pytest.approx(2.0, abs=1e-12)

    depth_truth = np.zeros((5, 5), np.float64)
    depth_estimate = np.zeros((5, 5), np.float64)
    depth_truth[2, 2] = 100.0
    depth_estimate[2, 2] = 102.0
    vsd = pose_error.vsd(
        identity, np.array([[0.0], [0.0], [102.0]]),
        identity, np.array([[0.0], [0.0], [100.0]]),
        depth_truth, K, delta=5.0, taus=[0.1, 0.3],
        normalized_by_diameter=True, diameter=10.0,
        renderer=_SequenceDepthRenderer(depth_estimate, depth_truth), obj_id=1)
    assert vsd == [1.0, 0.0]
