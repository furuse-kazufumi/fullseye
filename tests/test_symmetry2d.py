"""Ground-truth gates for the five 2-D symmetry operators (Issue #197)."""
import math

import numpy as np
import pytest
from scipy.ndimage import gaussian_filter, rotate

import fullseye as fs
import opsaoi
import symmetry2d as S
import typed_catalog


def _centroid(region):
    yy, xx = np.indices(region.shape)
    mass = float(np.sum(region))
    return np.array([np.sum(region * yy) / mass, np.sum(region * xx) / mass])


def test_symmetric_edge_center_reproduces_bite_tradeoff_and_clean_tradeoff():
    n = 161
    yy, xx = np.indices((n, n))
    truth = np.array([80.23, 79.20])
    disc = (np.hypot(yy - truth[0], xx - truth[1]) <= 48.0).astype(float)
    bite = (yy - truth[0]) ** 2 + (xx - (truth[1] + 42.0)) ** 2 < 16.0 ** 2
    bitten = disc.copy()
    bitten[bite] = 0.0

    edge_clean = np.array(S.center_from_symmetric_edges(disc)["center"])
    edge_bite = np.array(S.center_from_symmetric_edges(bitten)["center"])
    centroid_clean = _centroid(disc)
    centroid_bite = _centroid(bitten)
    errors = {
        "edge_clean": float(np.linalg.norm(edge_clean - truth)),
        "centroid_clean": float(np.linalg.norm(centroid_clean - truth)),
        "edge_bite": float(np.linalg.norm(edge_bite - truth)),
        "centroid_bite": float(np.linalg.norm(centroid_bite - truth)),
    }
    assert 0.1 <= errors["edge_bite"] <= 0.3, errors
    assert 3.0 <= errors["centroid_bite"] <= 3.4, errors
    assert errors["centroid_clean"] < errors["edge_clean"], errors


@pytest.mark.parametrize("kind", ["disc", "rectangle", "gear"])
def test_symmetric_edge_center_known_shapes(kind):
    n = 141
    yy, xx = np.indices((n, n))
    truth = np.array([70.25, 69.65])
    dy, dx = yy - truth[0], xx - truth[1]
    radius = np.hypot(dy, dx)
    if kind == "disc":
        image = radius <= 42.0
    elif kind == "rectangle":
        image = (np.abs(dy) <= 31.0) & (np.abs(dx) <= 43.0)
    else:
        theta = np.arctan2(dy, dx)
        image = radius <= 37.0 * (1.0 + 0.13 * np.cos(8.0 * theta))
    got = np.array(S.center_from_symmetric_edges(image.astype(float))["center"])
    assert np.linalg.norm(got - truth) < 0.35, (kind, truth, got)


@pytest.mark.parametrize("rotation_deg", [-31.0, -13.0, 0.0, 17.0, 39.0])
def test_reflection_axis_angle_sweep_uses_greyscale_rotation(rotation_deg):
    n = 129
    yy, xx = np.indices((n, n))
    # One reflection axis only: an isosceles triangle, blurred before rotation.
    triangle = ((np.abs(xx - 64) < (yy - 0.15 * n) * 0.25) &
                (yy > 0.15 * n) & (yy < 0.88 * n)).astype(float)
    grey = gaussian_filter(triangle, 1.0)
    moved_grey = rotate(grey, rotation_deg, reshape=False, order=3, mode="constant")
    # If a region is desired it must be made after interpolating the greyscale.
    moved = (moved_grey >= 0.5).astype(float)
    out = S.reflection_axis(moved, angle_step=2.0)
    expected = (90.0 - rotation_deg) % 180.0
    error = (out["angle_deg"] - expected + 90.0) % 180.0 - 90.0
    assert abs(error) <= 0.1, (rotation_deg, expected, out)


def _rotor(order, noise=0.0, blur=1.1, seed=0):
    n = 161
    yy, xx = np.indices((n, n))
    center = np.array([80.2, 79.7])
    dy, dx = yy - center[0], xx - center[1]
    radius, theta = np.hypot(dy, dx), np.arctan2(dy, dx)
    boundary = 42.0 * (1.0 + 0.17 * np.cos(order * theta))
    image = gaussian_filter((radius <= boundary).astype(float), blur)
    if noise:
        image = np.clip(image + np.random.default_rng(seed).normal(0.0, noise, image.shape), 0.0, 1.0)
    return image, center


@pytest.mark.parametrize("order", [2, 3, 4, 6])
@pytest.mark.parametrize("noise,blur", [(0.0, 0.7), (0.01, 1.4), (0.025, 2.0)])
def test_rotational_order_truth_under_noise_and_blur(order, noise, blur):
    image, center = _rotor(order, noise=noise, blur=blur, seed=order + int(100 * noise))
    out = S.rotational_symmetry(image, max_order=8, score_threshold=0.18)
    assert out["order"] == order, (order, noise, blur, out["order_scores"])
    assert np.linalg.norm(np.asarray(out["center"]) - center) < 0.35
    assert out["point_symmetric"] is (order % 2 == 0)


def test_rotational_order_one_means_asymmetric():
    n = 161
    yy, xx = np.indices((n, n))
    dy, dx = yy - 80.2, xx - 79.7
    r, theta = np.hypot(dy, dx), np.arctan2(dy, dx)
    boundary = 42.0 * (1.0 + 0.12 * np.cos(3 * theta) + 0.08 * np.cos(5 * theta + 0.4))
    image = gaussian_filter((r <= boundary).astype(float), 1.2)
    out = S.rotational_symmetry(image, max_order=8)
    assert out["order"] == 1 and out["symmetric"] is False


def _inspection_scene():
    n = 161
    yy, xx = np.indices((n, n))
    center = 80.0
    part = (yy - center) ** 2 + (xx - center) ** 2 < 55.0 ** 2
    texture = 0.50 + 0.12 * np.cos((xx - center) * 0.45) + 0.10 * np.cos((yy - center) * 0.31)
    illumination = 0.18 * (xx / (n - 1) - 0.5) + 0.08 * (yy / (n - 1) - 0.5)
    base = np.where(part, texture + illumination, 0.0)
    defect = (yy - 62.0) ** 2 + (xx - 111.0) ** 2 < 5.0 ** 2
    twin = (yy - 62.0) ** 2 + (xx - 49.0) ** 2 < 7.0 ** 2
    model = {"kind": "reflection", "angle_deg": 90.0, "offset_px": 0.0}
    return base, part, defect, twin, model


def test_difference_map_leaves_defect_not_pattern_or_linear_illumination():
    base, part, defect, twin, model = _inspection_scene()
    image = base.copy()
    image[defect] += 0.30
    diff = S.symmetry_difference_map(image, model, detrend=True)
    defect_mean = float(np.mean(diff[defect | twin]))
    background_mean = float(np.mean(diff[part & ~(defect | twin)]))
    assert defect_mean > 0.18
    assert background_mean < 1e-10
    assert defect_mean / max(background_mean, 1e-15) > 1e8
    excluded = S.symmetry_difference_map(image, model, exclusion_mask=defect, detrend=True)
    assert np.max(excluded[defect | twin]) < 1e-12


def test_symmetry_score_is_monotone_with_disturbance():
    base, _, defect, _, model = _inspection_scene()
    scores = []
    for amplitude in (0.0, 0.1, 0.2, 0.3, 0.4):
        image = base.copy()
        image[defect] += amplitude
        scores.append(S.symmetry_score(image, model, detrend=True))
    assert np.all(np.diff(scores) > 0.0), scores


@pytest.mark.parametrize("name", S.__all__)
def test_public_registry_and_typed_catalog_reachability(name):
    assert callable(getattr(fs, name)) and name in fs.__all__
    assert callable(getattr(fs.ledger, name))
    assert name in opsaoi.list_ops("symmetry")
    rows = {row[0]: row for row in typed_catalog.catalog()}
    assert name in rows


@pytest.mark.parametrize("name", S.__all__[:3])
def test_uniform_input_fails_closed(name):
    with pytest.raises(ValueError, match="constant|uniform"):
        getattr(S, name)(np.full((65, 67), 0.3))
