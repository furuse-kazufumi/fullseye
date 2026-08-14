"""Ground-truth tests for sparse feature detection / matching (features.py).

Corners are placed at known pixels (a synthetic checkerboard / squares), and the
second image is a known integer shift of the first, so detected keypoints and the
recovered match displacement are checked against exact answers."""
import numpy as np
from scipy import ndimage

import features


def _squares(h=120, w=140, seed=0):
    """A textured image with clear corners (random bright squares on a dark field)."""
    rng = np.random.default_rng(seed)
    img = np.zeros((h, w))
    for _ in range(12):
        y, x = rng.integers(10, h - 20), rng.integers(10, w - 20)
        img[y:y + 8, x:x + 8] = rng.uniform(0.5, 1.0)
    return ndimage.gaussian_filter(img, 0.6)


def _shift(img, dy, dx):
    return ndimage.shift(img, (dy, dx), order=1, mode="nearest")


def test_harris_finds_corners():
    img = np.zeros((60, 60))
    img[20:40, 20:40] = 1.0                            # a bright square -> 4 corners
    kp = features.harris_corners(img, min_distance=5, max_n=50)
    assert kp.shape[0] >= 4
    corners = {(20, 20), (20, 39), (39, 20), (39, 39)}
    # every true corner has a detected keypoint within 2 px
    for cy, cx in corners:
        assert np.min(np.abs(kp - np.array([cy, cx])).sum(1)) <= 4


def test_fast_finds_corners():
    img = np.zeros((60, 60))
    img[20:40, 20:40] = 1.0
    kp = features.fast_corners(img, thresh=0.2, min_distance=5)
    assert kp.shape[0] >= 4


def test_match_recovers_known_shift():
    img1 = _squares(seed=1)
    dy, dx = 0.0, 6.0
    img2 = _shift(img1, dy, dx)
    pts1, pts2 = features.match_keypoints(img1, img2, detector="harris",
                                          min_distance=6, max_n=200)
    assert pts1.shape[0] >= 5                           # several confident matches
    disp = pts2 - pts1                                  # (x, y) displacement
    # a feature at (x,y) moves to (x+dx, y+dy) -> median displacement recovers it
    assert abs(np.median(disp[:, 0]) - dx) < 1.0
    assert abs(np.median(disp[:, 1]) - dy) < 1.0


def test_describe_drops_border_keypoints():
    img = _squares(seed=2)
    kp = np.array([[1, 1], [60, 70], [0, 0]])          # two are within a 9-patch border
    desc, kept = features.describe_patches(img, kp, patch=9)
    assert kept.shape[0] == 1 and tuple(kept[0]) == (60, 70)
    assert desc.shape == (1, 81)
    assert abs(desc[0].mean()) < 1e-9                   # zero-mean patch descriptor
    # a textured keypoint gives a unit-norm descriptor (a flat patch -> zero, honestly)
    img2 = np.zeros((40, 40)); img2[10:30, 10:30] = 1.0
    d2, _ = features.describe_patches(img2, np.array([[10, 10]]), patch=9)
    assert np.isclose(np.linalg.norm(d2[0]), 1.0)


def test_match_descriptors_ratio_rejects_ambiguous():
    # three identical descriptors in set2 -> every match is ambiguous -> rejected
    d1 = np.array([[1.0, 0.0], [0.0, 1.0]])
    d2 = np.array([[1.0, 0.0], [1.0, 0.0], [1.0, 0.0]])
    m = features.match_descriptors(d1, d2, ratio=0.8)
    assert m.shape[0] == 0                              # ratio test kills the ties


def test_match_feeds_pose_recovery():
    # matched correspondences under a pure shift are consistent with a translating camera
    img1 = _squares(seed=3)
    img2 = _shift(img1, 0.0, 5.0)
    pts1, pts2 = features.match_keypoints(img1, img2, min_distance=6)
    assert pts1.shape[0] >= 5
    # correspondences are row-aligned (a horizontal shift) -> small y disparity
    assert np.median(np.abs(pts2[:, 1] - pts1[:, 1])) < 1.0
