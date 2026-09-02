"""caltab: mark detection + homography-guided correspondence + refined pose.

Regression for the 2026-09-02 finding: `find_marks_and_pose` matched detected marks
to the ideal grid by a row-major lexsort, which scrambles rows under any tilt
(depth off by ~500 mm with no error).  Now: 4-corner homography seed -> nearest
assignment -> refit, plus a reprojection-RMS gate and a 6-DoF pose refinement.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import caltab  # noqa: E402
import calib  # noqa: E402

K = {"fx": 500.0, "fy": 500.0, "cx": 128.0, "cy": 128.0}


def _rotm(rx, ry, rz):
    cx, sx, cy, sy, cz, sz = np.cos(rx), np.sin(rx), np.cos(ry), np.sin(ry), np.cos(rz), np.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def _pose(rx, ry, rz, t=(0, 0, 600)):
    T = np.eye(4)
    T[:3, :3] = _rotm(rx, ry, rz)
    T[:3, 3] = t
    return T


def _ang_err(Ra, Rb):
    d = Ra.T @ Rb
    return np.degrees(np.arccos(np.clip((np.trace(d) - 1) / 2, -1, 1)))


CT = caltab.create_caltab(7, 7, 10.0)
SWEEP = [(rx, ry, rz) for rx in (0.0, 0.1, 0.2, 0.3) for ry in (0.0, 0.1, 0.2, 0.3) for rz in (0.0, 0.1)]


@pytest.mark.parametrize("rx,ry,rz", SWEEP)
def test_pose_recovered_under_tilt(rx, ry, rz):
    T = _pose(rx, ry, rz)
    sim = caltab.sim_caltab(CT, K, T, 256)
    res = caltab.find_marks_and_pose(sim["image"], K, CT)
    assert len(res["marks"]) == 49 and res["n_marks"] == 49
    assert _ang_err(res["pose"][:3, :3], T[:3, :3]) < 1.0
    assert np.linalg.norm(res["pose"][:3, 3] - T[:3, 3]) < 5.0
    assert res["reproj_rms"] < 0.5
    assert res["residuals"].shape == (49,)


def test_correspondence_is_grid_consistent_not_lexsort():
    """rx=0.2 alone used to scramble rows; check every mark maps to its own ideal point."""
    T = _pose(0.2, 0.0, 0.0)
    sim = caltab.sim_caltab(CT, K, T, 256)
    res = caltab.find_marks_and_pose(sim["image"], K, CT)
    truth = sim["marks"][res["ideal_index"]]
    assert np.abs(res["marks"] - truth).max() < 0.5


def test_in_plane_rotation_up_to_35deg():
    T = _pose(0.2, -0.1, 0.6)
    sim = caltab.sim_caltab(CT, K, T, 256)
    res = caltab.find_marks_and_pose(sim["image"], K, CT)
    assert _ang_err(res["pose"][:3, :3], T[:3, :3]) < 1.0
    assert np.linalg.norm(res["pose"][:3, 3] - T[:3, 3]) < 5.0


def test_sim_and_find_share_the_plate_centred_frame():
    """create_caltab points are plate-centred; sim_caltab does not re-centre, so the
    pose fed to sim_caltab is the pose find_marks_and_pose returns (no R*(30,30,0) shift)."""
    assert np.allclose(CT["points"].mean(0), 0.0)
    T = _pose(0.1, 0.1, 0.0, t=(4.0, -6.0, 550.0))
    sim = caltab.sim_caltab(CT, K, T, 256)
    res = caltab.find_marks_and_pose(sim["image"], K, CT)
    assert np.abs(res["pose"][:3, 3] - T[:3, 3]).max() < 3.0


def test_wrong_intrinsics_are_flagged_by_reprojection_rms():
    """A wrong pixel aspect (fy) cannot be absorbed by the 6-DoF pose -> RMS gate fires.
    (A wrong principal point mostly CAN be absorbed by re-posing a planar target, so
    it is not a usable probe here.)"""
    T = _pose(0.2, 0.1, 0.0)
    sim = caltab.sim_caltab(CT, K, T, 256)
    bad_K = {"fx": 500.0, "fy": 300.0, "cx": 128.0, "cy": 128.0}
    with pytest.raises(ValueError, match="reprojection RMS"):
        caltab.find_marks_and_pose(sim["image"], bad_K, CT, max_reproj_rms=3.0)
    res = caltab.find_marks_and_pose(sim["image"], bad_K, CT, max_reproj_rms=None)
    assert res["reproj_rms"] > 3.0                                 # returned, not hidden


def test_non_planar_target_is_flagged():
    """Marks that do not lie on a plane (curved target) leave a residual the gate reports."""
    T = _pose(0.2, 0.1, 0.0)
    pts = CT["points"]
    world = np.column_stack([pts[:, 1], pts[:, 0], 0.05 * pts[:, 1] ** 2])
    px = calib.project_3d_point(world, K, T)
    img = np.zeros((256, 256))
    yy, xx = np.mgrid[0:256, 0:256]
    for row, col in px:
        img[(yy - row) ** 2 + (xx - col) ** 2 <= 9] = 1.0
    with pytest.raises(ValueError, match="reprojection RMS"):
        caltab.find_marks_and_pose(img, K, CT, max_reproj_rms=1.0)
    assert caltab.find_marks_and_pose(img, K, CT, max_reproj_rms=None)["reproj_rms"] > 1.0


def test_too_few_marks_raises():
    img = np.zeros((64, 64))
    img[10:14, 10:14] = 1.0
    img[40:44, 40:44] = 1.0
    with pytest.raises(ValueError, match=">= 4 marks"):
        caltab.find_marks_and_pose(img, K, CT)


def test_gen_caltab_and_find_caltab_roundtrip():
    g = caltab.gen_caltab(5, 5, 1.0, 0.3, 128)
    fc = caltab.find_caltab(g["image"])
    assert len(fc) == 25
    assert np.abs(np.sort(fc, 0) - np.sort(g["centers"], 0)).max() < 0.5


def test_image_to_world_plane_map_roundtrip():
    T = _pose(0.15, -0.1, 0.05)
    xy = CT["points"][:, ::-1]
    world = np.column_stack([xy, np.zeros(len(xy))])
    px = calib.project_3d_point(world, K, T)
    back = calib.image_points_to_world_plane(K, T, px)
    assert np.abs(back - xy).max() < 1e-6
