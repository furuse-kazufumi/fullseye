"""Ground-truth tests for silhouette pose descriptors: synthetic figures with
known skeleton topology and orientation."""
import numpy as np

import pose


def _line(img, y0, x0, y1, x1, width=1):
    n = int(max(abs(y1 - y0), abs(x1 - x0))) + 1
    ys = np.linspace(y0, y1, n).round().astype(int)
    xs = np.linspace(x0, x1, n).round().astype(int)
    for dy in range(-width, width + 1):
        for dx in range(-width, width + 1):
            img[np.clip(ys + dy, 0, img.shape[0] - 1),
                np.clip(xs + dx, 0, img.shape[1] - 1)] = 1.0
    return img


def test_straight_line_has_two_endpoints_no_junction():
    img = _line(np.zeros((80, 80)), 40, 10, 40, 70)
    nodes = pose.skeleton_nodes(img)
    assert nodes["n_endpoints"] == 2
    assert nodes["n_junctions"] == 0


def test_cross_has_four_endpoints_one_junction():
    img = np.zeros((81, 81))
    _line(img, 40, 8, 40, 72)      # horizontal
    _line(img, 8, 40, 72, 40)      # vertical
    nodes = pose.skeleton_nodes(img)
    assert nodes["n_endpoints"] == 4
    assert nodes["n_junctions"] == 1


def test_principal_axis_orientation_and_elongation():
    img = np.zeros((100, 60))
    img[10:90, 28:32] = 1.0        # tall thin vertical bar
    orient, elong = pose.principal_axis(img)
    # major axis is vertical -> |orientation| ~ pi/2, and highly elongated
    assert abs(abs(orient) - np.pi / 2) < 0.15
    assert elong > 5.0


def test_pose_descriptor_distinguishes_postures():
    upright = np.zeros((100, 60)); upright[10:90, 28:32] = 1.0     # tall bar
    tucked = np.zeros((60, 60)); tucked[24:36, 10:50] = 1.0        # wide bar
    du = pose.pose_descriptor(upright)
    dt = pose.pose_descriptor(tucked)
    assert du.shape == (6,)
    # aspect ratio (h/w) clearly separates the two postures
    assert du[5] > 1.0 and dt[5] < 1.0
