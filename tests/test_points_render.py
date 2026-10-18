# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Gates for ``render3d.points_render`` (point cloud -> RGB image).

Each gate is scored against something the renderer did not compute itself:

* projection   -- the closed-form pinhole / orthographic formula written out here, and
                  ``match3d.project_points`` as a second implementation; the splat's
                  intensity centroid must land on it at sub-pixel positions.
* z-buffer     -- the nearer of two coincident points wins whatever the input order, and
                  with ``footprint="point"`` the winning point at every pixel is the one
                  whose depth ``match3d.render_point_depth`` (an independent z-buffer)
                  reports.
* energy       -- ``composite="add"`` keeps the total light: sum(image - background)
                  equals sum(opacity * colour) of the points in frame.
* rotation     -- rotating the cloud equals rotating the camera; and a quarter turn about
                  the optical axis equals ``numpy.rot90`` of the image (a pixel
                  permutation the renderer never sees).
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import match3d  # noqa: E402
import render3d as r3  # noqa: E402

K_ORTHO = np.array([[20.0, 0.0, 31.5], [0.0, 20.0, 31.5], [0.0, 0.0, 1.0]])
K_PERSP = np.array([[80.0, 0.0, 31.5], [0.0, 80.0, 31.5], [0.0, 0.0, 1.0]])


def _centroids(img, centres, half=4):
    """Intensity centroid (u, v) of the splat around each expected centre."""
    g = img.sum(axis=2)
    out = []
    for u0, v0 in centres:
        c0, r0 = int(round(u0)), int(round(v0))
        win = g[r0 - half:r0 + half + 1, c0 - half:c0 + half + 1]
        rr, cc = np.mgrid[r0 - half:r0 + half + 1, c0 - half:c0 + half + 1]
        out.append(((win * cc).sum() / win.sum(), (win * rr).sum() / win.sum()))
    return np.array(out)


def _isolated_points():
    """Points on a sparse grid with sub-pixel offsets (none of the splats overlap)."""
    rng = np.random.default_rng(7)
    g = np.array([(x, y) for x in (-1.0, -0.4, 0.2, 0.8) for y in (-1.0, -0.4, 0.2, 0.8)])
    jitter = rng.uniform(-0.02, 0.02, g.shape)            # up to 0.4 px at fx = 20
    z = rng.uniform(2.0, 4.0, len(g))
    return np.column_stack([g + jitter, z])


# --------------------------------------------------------------------------- projection
@pytest.mark.parametrize("footprint, tol", [("gaussian", 1e-3), ("disc", 0.05)])
def test_orthographic_centroid_matches_closed_form(footprint, tol):
    P = _isolated_points()
    img = r3.points_render(P, size=64, K=K_ORTHO, footprint=footprint, composite="add", radius_px=1.5)
    expect = np.column_stack([20.0 * P[:, 0] + 31.5, 20.0 * P[:, 1] + 31.5])   # u = fx X + cx
    got = _centroids(img, expect, half=6)
    assert np.abs(got - expect).max() < tol
    # the same answer half a pixel off (the w/2 convention) is caught
    assert np.abs(got - (expect + 0.5)).max() > 0.45


def test_perspective_centroid_matches_closed_form_and_project_points():
    P = _isolated_points()
    P[:, :2] *= 0.6 * P[:, 2:3] / 2.0                      # keep the splats inside 64 px
    img = r3.points_render(P, size=64, K=K_PERSP, projection="perspective", composite="add")
    expect = np.column_stack([80.0 * P[:, 0] / P[:, 2] + 31.5, 80.0 * P[:, 1] / P[:, 2] + 31.5])
    uv, _z = match3d.project_points(P, K_PERSP)
    assert np.abs(uv - expect).max() < 1e-12              # second implementation agrees
    got = _centroids(img, expect, half=6)
    assert np.abs(got - expect).max() < 1e-3


def test_points_behind_the_camera_are_not_drawn():
    P = np.array([[0.0, 0.0, 2.0], [0.0, 0.0, -2.0]])
    a = r3.points_render(P[:1], size=32, K=K_PERSP, projection="perspective")
    b = r3.points_render(P, size=32, K=K_PERSP, projection="perspective")
    assert np.array_equal(a, b)


def test_auto_fit_centres_the_box_and_keeps_the_margin():
    P = np.array([[-3.0, -1.0, 0.0], [5.0, 3.0, 1.0]])
    img = r3.points_render(P, size=(101, 101), footprint="point", margin=0.1)
    lit = np.argwhere(img.sum(axis=2) > 0)
    # x span 8 maps onto (101-1)*(1-0.2) = 80 px, centred on column 50
    assert sorted(lit[:, 1].tolist()) == [10, 90]
    # y span 4 at the same scale = 40 px, centred on row 50
    assert sorted(lit[:, 0].tolist()) == [30, 70]


# --------------------------------------------------------------------------- z-buffer
def test_nearer_point_wins_exactly_at_the_centre_pixel():
    K = np.array([[10.0, 0.0, 16.0], [0.0, 10.0, 16.0], [0.0, 0.0, 1.0]])
    P = np.array([[0.0, 0.0, 5.0], [0.0, 0.0, 3.0], [0.0, 0.0, 4.0]])
    col = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    for o in ([0, 1, 2], [2, 1, 0], [1, 2, 0]):
        img = r3.points_render(P[o], colors=col[o], size=33, K=K, footprint="disc", radius_px=2.0)
        assert np.array_equal(img[16, 16], [0.0, 1.0, 0.0])
    # a renderer that painted in input order (no depth sort) would show the last point
    last = r3.points_render(P[[1, 2, 0]], colors=col[[1, 2, 0]], size=33, K=K, footprint="disc",
                            radius_px=2.0)
    assert not np.array_equal(last[16, 16], col[0])


def test_point_footprint_agrees_with_render_point_depth():
    """Independent z-buffer: at every lit pixel the visible colour belongs to the point
    whose depth render_point_depth keeps."""
    rng = np.random.default_rng(11)
    n = 4000
    P = np.column_stack([rng.uniform(-1, 1, n), rng.uniform(-1, 1, n), rng.uniform(2, 6, n)])
    K = np.array([[60.0, 0.0, 39.5], [0.0, 60.0, 29.5], [0.0, 0.0, 1.0]])
    zcol = (P[:, 2] - 2.0) / 4.0                         # colour encodes the point's depth
    col = np.column_stack([zcol, 1.0 - zcol, np.full(n, 0.5)])
    img = r3.points_render(P, colors=col, size=(60, 80), K=K, projection="perspective",
                           footprint="point")
    dep = match3d.render_point_depth(P, K, (60, 80))
    lit = dep > 0
    assert lit.sum() > 1200                               # many collisions resolved
    assert np.array_equal(lit, img[:, :, 2] > 0)
    assert np.abs(img[:, :, 0][lit] - (dep[lit] - 2.0) / 4.0).max() < 1e-12


def test_input_order_does_not_change_the_image():
    rng = np.random.default_rng(3)
    P = rng.normal(size=(3000, 3))
    col = rng.uniform(0, 1, (3000, 3))
    a = r3.points_render(P, colors=col, size=48, opacity=0.6)
    perm = rng.permutation(3000)
    b = r3.points_render(P[perm], colors=col[perm], size=48, opacity=0.6)
    assert np.abs(a - b).max() < 1e-12


# --------------------------------------------------------------------------- energy
@pytest.mark.parametrize("footprint", ["gaussian", "disc", "point"])
def test_add_composite_conserves_the_total_light(footprint):
    rng = np.random.default_rng(5)
    n = 2000
    P = np.column_stack([rng.uniform(-1, 1, n), rng.uniform(-1, 1, n), rng.uniform(1, 2, n)])
    col = rng.uniform(0, 1, (n, 3))
    bg = np.array([0.1, 0.2, 0.05])
    img = r3.points_render(P, colors=col, size=64, footprint=footprint, composite="add",
                           opacity=0.7, radius_px=2.5, background=bg, margin=0.1)
    got = (img - bg).reshape(-1, 3).sum(axis=0)
    assert np.abs(got - 0.7 * col.sum(axis=0)).max() < 1e-9 * n


def test_over_composite_stays_in_range_and_opaque_hides_background():
    rng = np.random.default_rng(9)
    P = rng.normal(size=(5000, 3))
    img = r3.points_render(P, colors=np.ones(3), size=40, background=(0.3, 0.3, 0.3),
                           footprint="disc", radius_px=3.0)
    assert img.min() >= 0.0 and img.max() <= 1.0
    assert np.array_equal(img[20, 20], [1.0, 1.0, 1.0])    # dense centre: fully covered


def test_gaussian_footprint_is_separable_so_column_sums_ignore_the_row():
    """The cut is per axis, so a splat's column profile does not depend on its row offset."""
    K = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    cols = []
    for v in (10.1, 20.5, 25.73):
        img = r3.points_render(np.array([[10.3, v, 1.0]]), size=(40, 30), K=K, composite="add",
                               radius_px=1.5)
        cols.append(img[:, :, 0].sum(axis=0))
    assert np.abs(cols[0] - cols[1]).max() < 1e-12 and np.abs(cols[0] - cols[2]).max() < 1e-12


# --------------------------------------------------------------------------- rotation
def _rot(axis, deg):
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    if axis == "x":
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    if axis == "y":
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def test_rotating_the_cloud_equals_rotating_the_camera():
    rng = np.random.default_rng(13)
    P = rng.normal(size=(2000, 3))
    col = rng.uniform(0, 1, (2000, 3))
    Q = _rot("y", 37.0) @ _rot("x", -21.0)
    K = np.array([[25.0, 0.0, 31.5], [0.0, 25.0, 31.5], [0.0, 0.0, 1.0]])
    a = r3.points_render(P @ Q.T, colors=col, size=64, K=K, opacity=0.5)
    b = r3.points_render(P, colors=col, size=64, K=K, R=Q, opacity=0.5)
    assert np.abs(a - b).max() < 1e-12
    assert np.abs(a - r3.points_render(P, colors=col, size=64, K=K, opacity=0.5)).max() > 0.1


@pytest.mark.parametrize("projection", ["orthographic", "perspective"])
def test_quarter_turn_about_the_axis_is_rot90_of_the_image(projection):
    rng = np.random.default_rng(17)
    n = 3000
    P = np.column_stack([rng.normal(0, 0.5, n), rng.normal(0, 0.3, n), rng.uniform(3, 5, n)])
    col = rng.uniform(0, 1, (n, 3))
    K = np.array([[30.0, 0.0, 31.5], [0.0, 30.0, 31.5], [0.0, 0.0, 1.0]])
    kw = dict(colors=col, size=64, K=K, projection=projection, opacity=0.6, depth_cue=0.5)
    a = r3.points_render(P, **kw)
    b = r3.points_render(P, R=_rot("z", 90.0), **kw)
    assert np.abs(b - np.rot90(a, k=-1)).max() < 1e-9
    assert np.abs(b - a).max() > 0.1                       # the turn really moved the picture


# --------------------------------------------------------------------------- knobs
def test_depth_cue_darkens_the_far_point_by_the_closed_form():
    K = np.array([[10.0, 0.0, 16.0], [0.0, 10.0, 16.0], [0.0, 0.0, 1.0]])
    P = np.array([[-1.0, 0.0, 2.0], [1.0, 0.0, 6.0], [0.0, 1.0, 3.0]])
    img = r3.points_render(P, colors=np.ones(3), size=33, K=K, footprint="point", depth_cue=0.8)
    assert np.allclose(img[16, 6], 1.0)                   # nearest: zn = 0
    assert np.allclose(img[16, 26], 1.0 - 0.8)            # farthest: zn = 1
    assert np.allclose(img[26, 16], 1.0 - 0.8 * 0.25)     # zn = (3-2)/(6-2)


def test_deterministic():
    P = np.random.default_rng(1).normal(size=(1000, 3))
    a = r3.points_render(P, size=32)
    b = r3.points_render(P.copy(), size=32)
    assert np.array_equal(a, b)


# --------------------------------------------------------------------------- fail-closed
@pytest.mark.parametrize("kw, msg", [
    (dict(points=np.zeros((0, 3))), "empty"),
    (dict(points=np.zeros((4, 2))), r"\(N, 3\)"),
    (dict(points=np.array([[0.0, 0.0, np.nan]])), "NaN"),
    (dict(projection="perspective"), "needs K"),
    (dict(projection="fisheye"), "projection"),
    (dict(footprint="square"), "footprint"),
    (dict(composite="max"), "composite"),
    (dict(radius_px=0.0), "radius_px"),
    (dict(opacity=0.0), "opacity"),
    (dict(depth_cue=1.5), "depth_cue"),
    (dict(margin=0.5), "margin"),
    (dict(colors=np.full((3, 3), 2.0)), "colors"),
    (dict(colors=np.zeros((2, 3))), "colors"),
    (dict(background=(0.0, 0.0)), "background"),
    (dict(size=(0, 10)), "positive"),
    (dict(K=np.eye(2)), "K must"),
])
def test_fail_closed(kw, msg):
    args = dict(points=np.random.default_rng(0).normal(size=(3, 3)))
    args.update(kw)
    with pytest.raises(ValueError, match=msg):
        r3.points_render(**args)


def test_pair_cap_refuses_instead_of_running_slowly(monkeypatch):
    monkeypatch.setattr(r3, "POINTS_RENDER_MAX_PAIRS", 100)
    with pytest.raises(ValueError, match="POINTS_RENDER_MAX_PAIRS"):
        r3.points_render(np.random.default_rng(0).normal(size=(50, 3)), size=16)


def test_nothing_in_frame_returns_the_background():
    P = np.array([[0.0, 0.0, -1.0]])
    img = r3.points_render(P, size=8, K=K_PERSP, projection="perspective", background=(0.2, 0.1, 0.0))
    assert np.allclose(img, [0.2, 0.1, 0.0])


def test_registered_in_ops3d_render():
    import ops3d
    m = ops3d.info("points_render") if hasattr(ops3d, "info") else ops3d.OPS3D["points_render"]
    assert m["category"] == "render" and m["in"] == ["points"] and m["out"] == "rgbimage"
