# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""examples_3d/anatomical_hand.py — real hand bones assembled from an MJCF tree.

The stdlib kinematic walker must place every bone exactly where MuJoCo's forward
kinematics puts it (checked when ``mujoco`` is importable), find all 27 hand bones,
and the assembled hand must be anatomically ordered (middle > index/ring > little).
Skipped honestly when the ``myo_sim`` data (Apache-2.0, not shipped) is absent.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

_MYO = Path(os.environ.get("MYO_SIM_DIR", r"C:/dev/projects/myo_sim"))
_XML = _MYO / "hand" / "myohand.xml"
pytestmark = pytest.mark.skipif(not _XML.exists(), reason="myo_sim (MyoHub/myo_sim) not present")


def _mod():
    p = Path(__file__).resolve().parents[1] / "examples_3d" / "anatomical_hand.py"
    spec = importlib.util.spec_from_file_location("anatomical_hand", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def bones():
    return _mod().load_mjcf_bone_meshes(_XML)


def test_all_27_hand_bones_are_found(bones):
    names = sorted(n for n, *_ in bones)
    assert len(bones) == 27, names
    assert {"thumbprox", "thumbdist", "1mc", "5distph", "scaphoid", "pisiform"} <= set(names)
    for _n, _b, V, F in bones:
        assert np.isfinite(V).all() and F.max() < V.shape[0]


def test_stdlib_kinematics_match_mujoco_forward_kinematics(bones):
    ah = _mod()
    chk = ah.crosscheck_with_mujoco(_XML, bones)
    if chk is None:
        pytest.skip("mujoco not installed — cannot cross-check the walker")
    assert chk["n"] == 27
    assert chk["max_pos_err"] < 1e-6 and chk["max_vert_err"] < 1e-6, chk


def test_finger_lengths_are_anatomically_ordered(bones):
    fl = _mod().finger_lengths(bones)
    assert fl["middle"] > fl["index"] > fl["little"], fl
    assert fl["middle"] > fl["ring"] > fl["little"], fl
    # real hand scale: fingertips 90-140 mm from the metacarpal centroid
    assert all(0.09 < v < 0.14 for v in fl.values()), fl


def test_euler_and_quat_conventions():
    ah = _mod()
    # MuJoCo eulerseq="xyz" (intrinsic): R = Rx Ry Rz; a pure z rotation of 90 deg
    R = ah._euler_xyz((0.0, 0.0, np.pi / 2))
    np.testing.assert_allclose(R @ [1, 0, 0], [0, 1, 0], atol=1e-12)
    # quaternion (w,x,y,z): identity and the same 90-deg z rotation
    np.testing.assert_allclose(ah._quat_wxyz((1, 0, 0, 0)), np.eye(3), atol=1e-12)
    q = (np.cos(np.pi / 4), 0, 0, np.sin(np.pi / 4))
    np.testing.assert_allclose(ah._quat_wxyz(q), R, atol=1e-12)
