# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""`opsmv` 台帳 —— 閉形式・独立実装・既知の幾何を真値にした門。

どの門も、**出力の中身を数えてから**比べる。入力が空でも通る比較(全画素の一致、最大誤差)は、
対象の画素が 0 個だと黙って緑になるので、先に件数の下限を置く。
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
import pytest
from scipy import interpolate, ndimage, stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import final_genuine2  # noqa: E402
import mathgeometry  # noqa: E402
import matching  # noqa: E402
import mvclass  # noqa: E402
import mvimage  # noqa: E402
import mvmorph  # noqa: E402
import mvstereo  # noqa: E402
import mvtext  # noqa: E402
import mvtrack  # noqa: E402
import opsmv  # noqa: E402
import reconstruction  # noqa: E402

CAM = {"fx": 400.0, "fy": 400.0, "cx": 64.0, "cy": 48.0}


def _smooth_texture(shape, seed=0, sigma=1.2):
    rng = np.random.default_rng(seed)
    t = ndimage.gaussian_filter(rng.random(shape), sigma)
    return (t - t.min()) / (t.max() - t.min())


# ---- ステレオ ------------------------------------------------------------- #
def _stereo_pair(d_true, seed=0):
    H, W = d_true.shape
    right = _smooth_texture((H, W), seed, 1.0)
    rr, cc = np.mgrid[0:H, 0:W].astype(float)
    left = ndimage.map_coordinates(right, [rr, cc - d_true], order=3, mode="nearest")
    return left, right


def test_disparity_recovers_a_known_step():
    d = np.full((60, 120), 6.0)
    d[20:40, 40:80] = 10.0
    left, right = _stereo_pair(d)
    res = opsmv.call("binocular_disparity_ms", left, right, max_disp=16)
    inner = res["valid"].copy()
    inner[:, :20] = False
    assert inner.sum() > 0.6 * inner.size                    # 中身を数える
    good = np.abs(res["disparity"][inner] - d[inner]) <= 1.0
    assert good.mean() > 0.97


def test_disparity_marks_the_unmatchable_left_columns_invalid():
    d = np.full((40, 90), 8.0)
    left, right = _stereo_pair(d)
    res = opsmv.call("binocular_disparity_ms", left, right, max_disp=12)
    assert not res["valid"][:, :4].any()
    assert np.isnan(res["disparity"][:, :4]).all()
    assert res["valid"][:, 20:].mean() > 0.9


def test_disparity_subpixel_beats_the_integer_rounding_on_a_slanted_plane():
    H, W = 60, 160
    _, cc = np.mgrid[0:H, 0:W].astype(float)
    d = 5.0 + 0.03 * cc
    left, right = _stereo_pair(d, seed=2)
    res = opsmv.call("binocular_disparity_ms", left, right, max_disp=16)
    use = res["valid"].copy()
    use[:, :24] = False
    assert use.sum() > 2000
    err = np.abs(res["disparity"][use] - d[use])
    rounded = np.abs(np.rint(res["disparity"][use]) - d[use])
    assert err.mean() < rounded.mean()
    assert np.median(err) < 0.2


def test_distance_follows_the_closed_form():
    d = np.full((50, 110), 7.0)
    left, right = _stereo_pair(d, seed=3)
    res = opsmv.call("binocular_distance_ms", left, right, 500.0, 0.2, doffs=1.0, max_disp=12)
    use = res["valid"].copy()
    use[:, :16] = False
    assert use.sum() > 2000
    want = 500.0 * 0.2 / (res["disparity"][use] + 1.0)
    assert np.allclose(res["distance"][use], want)
    assert abs(np.median(res["distance"][use]) - 500.0 * 0.2 / 8.0) < 0.5
    assert np.isnan(res["distance"][~res["valid"]]).all()


def test_depth_from_focus_recovers_step_depth_from_a_defocus_stack():
    tex = _smooth_texture((64, 64), 1, 0.6)
    truth = np.full((64, 64), 2)
    truth[:, 32:] = 6
    stack = []
    for k in range(9):
        near = ndimage.gaussian_filter(tex, 0.1 + 0.9 * abs(k - 2))
        far = ndimage.gaussian_filter(tex, 0.1 + 0.9 * abs(k - 6))
        stack.append(np.where(truth == 2, near, far))
    idx = reconstruction.depth_from_focus(stack)["index"]
    use = np.zeros(truth.shape, bool)
    use[8:-8, 8:24] = use[8:-8, 40:-8] = True
    assert use.sum() > 1000
    assert (idx[use] == truth[use]).mean() > 0.95


def test_reconstruct_surface_stereo_is_a_plane_for_constant_disparity():
    d = np.full((10, 12), 4.0)
    d[0, 0] = np.nan
    d[1, 1] = 0.0
    pts = opsmv.call("reconstruct_surface_stereo", d, 200.0, 0.5, 6.0, 5.0)
    assert pts.shape == (118, 3)
    assert np.allclose(pts[:, 2], 200.0 * 0.5 / 4.0)
    assert np.isclose(pts[:, 0].max(), (11 - 6.0) * 0.5 / 4.0)
    assert opsmv.call("reconstruct_surface_stereo", np.full((3, 3), np.nan)).shape == (0, 3)


# ---- 幾何の再標本化 ------------------------------------------------------- #
def test_map_image_applies_a_known_shift_exactly_on_a_ramp():
    rr, cc = np.mgrid[0:30, 0:40].astype(float)
    ramp = 0.5 * rr + 0.25 * cc
    out = opsmv.call("map_image", ramp, {"row_map": rr[5:25, 5:35] + 1.5, "col_map": cc[5:25, 5:35] - 2.5})
    assert out.shape == (20, 30)
    assert np.allclose(out, 0.5 * (rr[5:25, 5:35] + 1.5) + 0.25 * (cc[5:25, 5:35] - 2.5))


def test_map_image_composes_with_the_radial_distortion_map():
    import calib
    m = calib.gen_radial_distortion_map({"fx": 1.0, "fy": 1.0, "cx": 32.0, "cy": 32.0}, 1e-5, (64, 64))
    im = _smooth_texture((64, 64), 4, 2.0)
    out = opsmv.call("map_image", im, m)
    want = ndimage.map_coordinates(im, [m["row_map"], m["col_map"]], order=1)
    assert out.std() > 0.01
    assert np.allclose(out, want)
    with pytest.raises(ValueError):
        opsmv.call("map_image", im, {"x_map": m["row_map"], "y_map": m["col_map"]})


def _tilted_pose(rx=0.35, ry=-0.2, t=(-0.5, -0.4, 2.0)):
    cx, sx, cy, sy = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry)
    R = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]) @ np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = t
    return T


def _plane_pattern(x, y):
    return 0.5 + 0.25 * np.sin(9.0 * x) * np.cos(7.0 * y) + 0.2 * x


def test_rectify_undoes_a_known_perspective_view_of_a_plane():
    T = _tilted_pose()
    cam = {"fx": 300.0, "fy": 300.0, "cx": 160.0, "cy": 120.0}
    # カメラ画素ごとに光線を平面 z=0 へ当てて、閉形式で斜めの像を作る(独立の経路)。
    rr, cc = np.mgrid[0:240, 0:320].astype(float)
    d = np.stack([(cc - 160.0) / 300.0, (rr - 120.0) / 300.0, np.ones_like(cc)], -1)
    R, t = T[:3, :3], T[:3, 3]
    dw = d @ R
    o = -R.T @ t
    s = -o[2] / dw[..., 2]
    x, y = o[0] + s * dw[..., 0], o[1] + s * dw[..., 1]
    view = _plane_pattern(x, y)
    out = opsmv.call("rectify_to_world_plane", view, cam, T, 200, 160, 0.005)
    assert out.shape == (160, 200)
    yy, xx = np.mgrid[0:160, 0:200] * 0.005
    want = _plane_pattern(xx, yy)
    assert want.std() > 0.1
    assert np.sqrt(np.mean((out - want) ** 2)) < 0.01


def test_change_radial_distortion_moves_a_dot_to_the_closed_form_place():
    cam0 = {"fx": 300.0, "fy": 300.0, "cx": 64.0, "cy": 64.0, "kappa": 0.0}
    cam1 = dict(cam0, kappa=-3e-5)
    rr, cc = np.mgrid[0:129, 0:129].astype(float)
    r0, c0 = 100.0, 30.0
    dot = np.exp(-((rr - r0) ** 2 + (cc - c0) ** 2) / (2 * 2.0 ** 2))
    # cam0 の像 → 歪んだ cam1 の像。点の行き先は歪みの閉形式。
    out = opsmv.call("change_radial_distortion_image", dot, cam0, cam1)
    ux, uy = mvimage.undistort_division(np.array([1.0]), np.array([0.0]), 0.0)
    assert ux[0] == 1.0 and uy[0] == 0.0
    dx, dy = mvimage.distort_division(np.array([c0 - 64.0]), np.array([r0 - 64.0]), -3e-5)
    assert np.hypot(dx[0] - (c0 - 64.0), dy[0] - (r0 - 64.0)) > 1.5        # 動く量が 0 でない
    w = np.where(out > 0.1, out, 0.0)
    assert (w > 0).sum() > 10
    got = (float((w * rr).sum() / w.sum()), float((w * cc).sum() / w.sum()))
    assert abs(got[0] - (64.0 + dy[0])) < 0.15 and abs(got[1] - (64.0 + dx[0])) < 0.15


def test_change_radial_distortion_is_the_identity_when_the_cameras_agree():
    im = _smooth_texture((60, 80), 5, 1.5)
    cam = {"fx": 200.0, "fy": 200.0, "cx": 40.0, "cy": 30.0, "kappa": 3e-6}
    assert np.allclose(opsmv.call("change_radial_distortion_image", im, cam, dict(cam)), im, atol=1e-9)


def test_division_model_inverse_is_exact():
    x, y = np.array([10.0, -50.0, 120.0]), np.array([3.0, 80.0, -40.0])
    for k in (-1e-5, 2e-6):
        ux, uy = mvimage.distort_division(x, y, k)
        bx, by = mvimage.undistort_division(ux, uy, k)
        assert np.allclose(bx, x) and np.allclose(by, y)


def test_crop_rectangle2_reads_the_closed_form_coordinates_on_a_ramp():
    rr, cc = np.mgrid[0:100, 0:100].astype(float)
    ramp = 0.3 * rr + 0.7 * cc
    out = opsmv.call("crop_rectangle2", ramp, 50.0, 40.0, 0.3, 12.0, 5.0)
    assert out.shape == (11, 25)
    jj, ii = np.meshgrid(np.arange(25) - 12.0, np.arange(11) - 5.0)
    c, s = math.cos(0.3), math.sin(0.3)
    want = 0.3 * (50.0 + jj * s + ii * c) + 0.7 * (40.0 + jj * c - ii * s)
    assert np.allclose(out, want)


# ---- 灰色値の計測 --------------------------------------------------------- #
def test_atan2_image_matches_math_atan2_pixel_by_pixel():
    a = np.array([[1.0, -1.0, 0.0], [0.5, 2.0, -3.0]])
    b = np.array([[1.0, 1.0, -1.0], [-2.0, 0.0, -1.0]])
    out = opsmv.call("atan2_image", a, b)
    want = [[math.atan2(y, x) for y, x in zip(r1, r2)] for r1, r2 in zip(a.tolist(), b.tolist())]
    assert np.allclose(out, want)


def test_area_center_gray_of_two_point_masses():
    im = np.zeros((20, 30))
    im[4, 6] = 1.0
    im[14, 26] = 3.0
    res = opsmv.call("area_center_gray", im)
    assert res["area"] == 4.0
    assert res["row"] == pytest.approx((4 * 1 + 14 * 3) / 4)
    assert res["column"] == pytest.approx((6 * 1 + 26 * 3) / 4)
    assert opsmv.call("area_center_gray", np.zeros((3, 3)))["area"] == 0.0


def test_gray_histo_counts_like_a_loop_and_refuses_8bit_values():
    im = np.random.default_rng(0).random((40, 50))
    res = opsmv.call("gray_histo", im, None, 8)
    loop = [0] * 8
    for v in im.ravel():
        loop[min(int(v * 8), 7)] += 1
    assert res["absolute"].tolist() == loop
    assert res["absolute"].sum() == 2000
    assert res["relative"].sum() == pytest.approx(1.0)
    with pytest.raises(ValueError):
        opsmv.call("gray_histo", im * 255.0)


def test_gray_projections_are_the_row_and_column_means():
    im = np.arange(12.0).reshape(3, 4)
    res = opsmv.call("gray_projections", im)
    assert np.allclose(res["horizontal"], im.mean(axis=1))
    assert np.allclose(res["vertical"], im.mean(axis=0))
    reg = np.zeros((3, 4), bool)
    reg[1, 1:3] = True
    res2 = opsmv.call("gray_projections", im, reg)
    assert res2["horizontal"].tolist() == [0.0, 5.5, 0.0]


def test_get_grayval_contour_reads_a_ramp_exactly_and_refuses_the_outside():
    rr, cc = np.mgrid[0:20, 0:20].astype(float)
    ramp = 2.0 * rr + 3.0 * cc
    pts = np.array([[1.5, 2.25], [10.0, 10.75], [18.5, 3.0]])
    out = opsmv.call("get_grayval_contour_xld", ramp, pts)
    assert np.allclose(out, 2.0 * pts[:, 0] + 3.0 * pts[:, 1])
    xld = {"shape": (20, 20), "cs": [pts]}
    assert np.allclose(opsmv.call("get_grayval_contour_xld", ramp, xld), out)
    with pytest.raises(ValueError):
        opsmv.call("get_grayval_contour_xld", ramp, np.array([[25.0, 1.0]]))


# ---- 検出 ----------------------------------------------------------------- #
def test_lepetit_ignores_a_straight_edge_and_flat_ground():
    rr, cc = np.mgrid[0:64, 0:64].astype(float)
    for edge in (cc > 31.5, rr > 31.5, (rr - cc) > 0.5, (rr + cc) > 63.5):
        assert opsmv.call("points_lepetit", edge.astype(float)).shape == (0, 2)
    assert opsmv.call("points_lepetit", np.full((64, 64), 0.5)).shape == (0, 2)


def test_lepetit_finds_blobs_at_their_true_subpixel_position():
    rr, cc = np.mgrid[0:80, 0:80].astype(float)
    truth = np.array([[20.3, 25.6], [55.5, 18.2], [40.7, 60.4]])
    im = np.zeros((80, 80))
    for r, c in truth:
        im += np.exp(-((rr - r) ** 2 + (cc - c) ** 2) / (2 * 2.2 ** 2))
    pts = opsmv.call("points_lepetit", im, 4, 1, 0.05, 0.05)
    assert pts.shape == (3, 2)
    nearest = np.sqrt(((pts[:, None] - truth[None]) ** 2).sum(-1)).min(axis=0)
    assert nearest.shape == (3,) and nearest.max() < 0.25


def test_find_ncc_models_tells_the_models_apart():
    img = _smooth_texture((120, 120), 7, 1.0)
    a = img[20:40, 30:50].copy()
    b = img[80:100, 70:90].copy()
    res = opsmv.call("find_ncc_models", [matching.create_ncc_model(a), matching.create_ncc_model(b)],
                     img, 0.95, 5, 8)
    assert res["num"] == 2
    got = {m["model"]: (m["row"], m["col"]) for m in res["matches"]}
    assert np.hypot(got[0][0] - 30, got[0][1] - 40) <= 2.0 or np.hypot(got[0][0] - 20, got[0][1] - 30) <= 2.0
    assert np.hypot(got[1][0] - 90, got[1][1] - 80) <= 2.0 or np.hypot(got[1][0] - 80, got[1][1] - 70) <= 2.0
    noise = np.random.default_rng(1).random((60, 60))
    assert opsmv.call("find_ncc_models", [matching.create_ncc_model(a)], noise, 0.99)["num"] == 0


# ---- 姿勢 ----------------------------------------------------------------- #
def _circle_image(center, normal, radius, cam, n=90):
    nz = np.asarray(normal, float) / np.linalg.norm(normal)
    e1 = np.cross(nz, [1.0, 0.0, 0.0])
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(nz, e1)
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    p = np.asarray(center) + radius * (np.cos(t)[:, None] * e1 + np.sin(t)[:, None] * e2)
    return np.column_stack([cam["fy"] * p[:, 1] / p[:, 2] + cam["cy"], cam["fx"] * p[:, 0] / p[:, 2] + cam["cx"]])


@pytest.mark.parametrize("center,normal", [
    ((0.1, -0.05, 1.0), (0.3, 0.2, -1.0)),
    ((-0.2, 0.1, 2.0), (-0.5, 0.1, -1.0)),
    ((0.0, 0.3, 1.5), (0.1, 0.6, -1.0)),
])
def test_circle_pose_returns_the_true_circle_among_two_exact_solutions(center, normal):
    pts = _circle_image(center, normal, 0.05, CAM)
    res = opsmv.call("get_circle_pose", pts, 0.05, CAM)
    assert res["center"].shape == (2, 3)
    assert (res["rms_px"] < 1e-4).all()
    n_true = np.asarray(normal) / np.linalg.norm(normal)
    errs = [np.linalg.norm(res["center"][i] - center) + np.linalg.norm(res["normal"][i] - n_true) for i in range(2)]
    assert min(errs) < 1e-5


def test_circle_pose_refuses_points_on_a_line():
    pts = np.column_stack([np.arange(10.0), np.arange(10.0)])
    with pytest.raises(ValueError):
        opsmv.call("get_circle_pose", pts, 0.05, CAM)


# ---- 形態学 --------------------------------------------------------------- #
def _hmt_brute(a, hit, miss):
    H, W = a.shape
    out = np.zeros((H, W), bool)
    for r in range(H):
        for c in range(W):
            ok = True
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    rr, cc = r + dr, c + dc
                    v = bool(a[rr, cc]) if 0 <= rr < H and 0 <= cc < W else False
                    if hit[dr + 1, dc + 1] and not v:
                        ok = False
                    if miss[dr + 1, dc + 1] and v:
                        ok = False
            out[r, c] = ok
    return out


@pytest.mark.parametrize("letter", ["l", "m", "e", "i", "c"])
def test_hit_or_miss_matches_a_brute_force_loop(letter):
    a = np.random.default_rng(3).random((24, 24)) > 0.55
    total = 0
    for rot in range(8):
        pair = opsmv.call("golay_elements", letter, rot)
        got = opsmv.call("hit_or_miss_golay", a, letter, rot)
        want = _hmt_brute(a, pair["hit"], pair["miss"])
        assert (got == want).all()
        total += int(got.sum())
    assert total > 0


def test_golay_rotation_by_90_degrees_is_rot90():
    p0 = opsmv.call("golay_elements", "l", 0)
    p2 = opsmv.call("golay_elements", "l", 2)
    assert (np.rot90(p0["hit"], -1) == p2["hit"]).all()
    assert (np.rot90(p0["miss"], -1) == p2["miss"]).all()
    assert (opsmv.call("golay_elements", "l", 8)["hit"] == p0["hit"]).all()
    with pytest.raises(ValueError):
        opsmv.call("golay_elements", "q")


def test_hit_or_miss_seq_is_the_union_of_the_eight_rotations():
    a = np.random.default_rng(5).random((20, 20)) > 0.5
    want = np.zeros(a.shape, bool)
    for rot in range(8):
        want |= opsmv.call("hit_or_miss_golay", a, "e", rot)
    got = opsmv.call("hit_or_miss_seq", a, "e")
    assert got.sum() > 0 and (got == want).all()


def test_isolated_point_letter_finds_exactly_the_isolated_points():
    a = np.zeros((16, 16), bool)
    a[3, 3] = a[8, 12] = True
    a[12:14, 4:6] = True
    assert opsmv.call("hit_or_miss_seq", a, "i").sum() == 2


def test_thickening_seq_with_the_corner_letter_fills_a_notch():
    a = np.zeros((30, 30), bool)
    a[5:25, 5:25] = True
    solid = a.copy()
    a[5:14, 12:18] = False                         # 上辺からの切り欠き
    assert (solid & ~a).sum() == 54
    hull = opsmv.call("thickening_seq", a, "c")
    assert (hull == solid).all()


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_thickening_seq_with_the_corner_letter_converges_to_the_bounding_box(seed):
    rng = np.random.default_rng(seed)
    a = ndimage.binary_opening(ndimage.gaussian_filter(rng.random((48, 48)), 3.0) > 0.52, np.ones((3, 3)))
    lab, n = ndimage.label(a)
    assert n >= 1
    one = lab == 1 + int(np.argmax(ndimage.sum(a, lab, range(1, n + 1))))
    assert one.sum() > 30
    box = ndimage.find_objects(one.astype(int))[0]
    want = np.zeros(one.shape, bool)
    want[box] = True
    hull = opsmv.call("thickening_seq", one, "c")
    assert (hull == want).all()
    assert hull.sum() > one.sum()


def test_thickening_adds_only_the_hmt_pixels():
    a = np.zeros((9, 9), bool)
    a[4, 2:7] = True
    hit = np.array([[0, 0, 0], [1, 0, 1], [0, 0, 0]], bool)
    miss = np.array([[0, 0, 0], [0, 1, 0], [0, 0, 0]], bool)
    a[4, 4] = False
    out = opsmv.call("thickening_hit_miss", a, hit, miss, 1)
    assert out[4, 4] and out.sum() == a.sum() + 1
    p = opsmv.call("golay_elements", "c", 0)
    assert (opsmv.call("thickening_golay", a, "c", 0, 3) == opsmv.call("thickening_hit_miss", a, p["hit"], p["miss"], 3)).all()


def test_morph_hat_returns_the_spur_and_the_hole():
    a = np.zeros((20, 20), bool)
    a[5:15, 5:15] = True
    a[4, 9] = True                                 # 開放で消える突起
    a[9, 9] = False                                # 閉鎖で埋まる穴
    out = opsmv.call("morph_hat", a, np.ones((3, 3), bool))
    assert out[4, 9] and out[9, 9]
    assert out.sum() >= 2


def test_skiz_is_equidistant_from_the_two_objects():
    a = np.zeros((60, 100), bool)
    rr, cc = np.mgrid[0:60, 0:100]
    disc1 = (rr - 30) ** 2 + (cc - 20) ** 2 <= 8 ** 2
    disc2 = (rr - 30) ** 2 + (cc - 80) ** 2 <= 8 ** 2
    a = disc1 | disc2
    out = opsmv.call("morph_skiz", a)
    assert out.sum() >= 60                         # 中身を数える
    assert np.abs(np.nonzero(out)[1] - 49.5).max() <= 1.0
    d1 = ndimage.distance_transform_edt(~disc1)
    d2 = ndimage.distance_transform_edt(~disc2)
    assert np.abs(d1[out] - d2[out]).max() <= 1.5
    assert opsmv.call("morph_skiz", disc1).sum() == 0


def test_opening_seg_splits_two_squares_joined_by_a_thin_bridge():
    a = np.zeros((40, 80), bool)
    a[10:30, 10:30] = True
    a[10:30, 50:70] = True
    a[19:21, 30:50] = True
    lab = opsmv.call("opening_seg", a, np.ones((5, 5), bool))
    assert lab.max() == 2
    assert (lab[a] > 0).all() and (lab[~a] == 0).all()
    assert lab[20, 20] != lab[20, 60]
    assert opsmv.call("opening_seg", np.eye(9, dtype=bool), np.ones((3, 3), bool)).max() == 0


# ---- 曲線 ----------------------------------------------------------------- #
def test_nurbs_interpolation_passes_through_every_point():
    t = np.linspace(0, 3, 12)
    Q = np.column_stack([np.cos(t) * 30, np.sin(t) * 20 + t * 5])
    res = opsmv.call("gen_nurbs_interp", Q, 3)
    assert res["control_points"].shape == (12, 2)
    # 独立の実装(scipy の BSpline)で評価する。
    spl = interpolate.BSpline(res["knots"], res["control_points"], 3)
    assert np.allclose(spl(res["u"]), Q, atol=1e-9)
    curve = mathgeometry.nurbs_curve(res["control_points"], res["weights"], degree=3, knots=res["knots"], n=50)
    assert np.allclose(curve["points"][0], Q[0]) and np.allclose(curve["points"][-1], Q[-1], atol=1e-9)
    assert np.allclose(curve["points"], spl(np.linspace(0, 1, 50)), atol=1e-9)


def test_nurbs_interpolation_reproduces_a_straight_line():
    x = np.array([0.0, 1.0, 2.5, 3.0, 5.0, 8.0])
    Q = np.column_stack([x, 2.0 * x + 1.0])
    res = opsmv.call("gen_nurbs_interp", Q, 3)
    spl = interpolate.BSpline(res["knots"], res["control_points"], 3)
    mid = spl(np.linspace(0, 1, 41))
    assert np.allclose(mid[:, 1], 2.0 * mid[:, 0] + 1.0, atol=1e-9)
    with pytest.raises(ValueError):
        opsmv.call("gen_nurbs_interp", np.zeros((5, 2)), 3)


# ---- 追跡 ----------------------------------------------------------------- #
def test_kalman_gain_converges_to_the_riccati_closed_form():
    Q, R = 0.02, 0.5
    x, P = np.zeros(1), np.eye(1)
    for _ in range(200):
        r = opsmv.call("filter_kalman", x, P, [0.3], 1.0, 1.0, Q, R)
        x, P = r["x"], r["P"]
    Pm = (Q + math.sqrt(Q * Q + 4 * Q * R)) / 2.0
    assert r["gain"][0, 0] == pytest.approx(Pm / (Pm + R), rel=1e-9)
    assert x[0] == pytest.approx(0.3, abs=1e-3)


def test_kalman_without_process_noise_is_the_running_mean():
    z = np.random.default_rng(0).normal(2.0, 1.0, 50)
    x, P = np.array([0.0]), np.array([[1e12]])
    for zk in z:
        r = opsmv.call("filter_kalman", x, P, [zk], 1.0, 1.0, 0.0, 1.0)
        x, P = r["x"], r["P"]
    assert x[0] == pytest.approx(z.mean(), abs=1e-6)
    assert P[0, 0] == pytest.approx(1.0 / 50.0, abs=1e-6)


def test_kalman_tracks_constant_velocity_and_skips_missing_frames():
    F = np.array([[1.0, 1.0], [0.0, 1.0]])
    H = np.array([[1.0, 0.0]])
    x, P = np.zeros(2), np.eye(2) * 100.0
    for k in range(1, 41):
        r = opsmv.call("filter_kalman", x, P, None if k == 20 else [3.0 * k], F, H, 1e-6, 1e-4)
        x, P = r["x"], r["P"]
        if k == 20:
            assert math.isnan(r["nis"])
    assert x[1] == pytest.approx(3.0, abs=1e-3)
    assert x[0] == pytest.approx(120.0, abs=1e-2)


def test_bg_esti_step_response_follows_the_scalar_recursion():
    q, r = 1e-3, 1e-2
    bg = np.zeros((6, 6))
    m = opsmv.call("create_bg_esti", bg, q, r, 10.0, 0.0)
    want, p = 0.0, r
    for _ in range(30):
        out = opsmv.call("run_bg_esti", m, np.full((6, 6), 0.5))
        m = out["model"]
        pp = p + q
        k = pp / (pp + r)
        want += k * (0.5 - want)
        p = (1 - k) ** 2 * pp + k * k * r
    assert m["frames"] == 30
    assert np.allclose(opsmv.call("give_bg_esti", m), want)


def test_bg_esti_keeps_a_passing_object_out_of_the_background():
    rng = np.random.default_rng(1)
    base = _smooth_texture((40, 40), 8, 2.0) * 0.5 + 0.2
    m = opsmv.call("create_bg_esti", base, 1e-4, 1e-3, 0.12, 0.0)
    for k in range(17):
        frame = base + rng.normal(0, 0.005, base.shape)
        frame[10:20, 2 * k:2 * k + 6] = 0.95
        out = opsmv.call("run_bg_esti", m, frame)
        m = out["model"]
        assert 40 <= out["foreground"].sum() <= 90        # 物体の 60 画素の付近
    assert np.abs(opsmv.call("give_bg_esti", m) - base).max() < 0.05


def test_update_bg_esti_touches_only_the_region_and_does_not_mutate():
    m = opsmv.call("create_bg_esti", np.zeros((4, 4)))
    reg = np.zeros((4, 4), bool)
    reg[0, :] = True
    new = opsmv.call("update_bg_esti", m, np.ones((4, 4)), reg)
    assert (new["background"][0] > 0).all() and (new["background"][1:] == 0).all()
    assert (m["background"] == 0).all()
    view = opsmv.call("give_bg_esti", new)
    view[:] = 9.0
    assert new["background"].max() < 9.0


# ---- 分類 ----------------------------------------------------------------- #
def _blobs(n=300, seed=0):
    rng = np.random.default_rng(seed)
    X = np.vstack([rng.normal([0, 0], 1.0, (n, 2)), rng.normal([6, 1], 1.0, (n, 2)), rng.normal([1, 7], 1.0, (n, 2))])
    return X, np.repeat([0, 1, 2], n)


def test_gmm_recovers_the_class_means_and_covariances():
    X, y = _blobs(2000)
    model = opsmv.call("train_class_gmm", X, y)
    assert np.allclose(model["components"][1]["means"][0], [6, 1], atol=0.1)
    assert np.allclose(model["components"][1]["covs"][0], np.eye(2), atol=0.1)
    assert np.allclose(model["priors"], 1.0 / 3.0)


def test_gmm_posterior_matches_bayes_with_hand_written_parameters():
    q = np.array([[0.5, 0.2], [3.0, -1.0], [-2.0, 2.0]])
    s1 = np.array([[1.0, 0.3], [0.3, 2.0]])
    s2 = np.eye(2) * 0.5
    model = {"classes": np.array([0, 1]), "priors": np.array([0.3, 0.7]),
             "components": [{"weights": np.array([1.0]), "means": np.array([[0.0, 0.0]]), "covs": s1[None]},
                            {"weights": np.array([0.4, 0.6]), "means": np.array([[2.0, 0.0], [-1.0, 1.0]]),
                             "covs": np.stack([s2, s2])}]}
    p0 = 0.3 * stats.multivariate_normal([0, 0], s1).pdf(q)
    p1 = 0.7 * (0.4 * stats.multivariate_normal([2, 0], s2).pdf(q) + 0.6 * stats.multivariate_normal([-1, 1], s2).pdf(q))
    res = opsmv.call("evaluate_class_gmm", model, q)
    assert np.allclose(res["posterior"][:, 0], p0 / (p0 + p1))
    assert np.allclose(res["log_density"], np.log(p0 + p1))


def test_gmm_with_two_centers_learns_a_bimodal_class():
    rng = np.random.default_rng(2)
    a = np.vstack([rng.normal([-5, 0], 0.5, (300, 2)), rng.normal([5, 0], 0.5, (300, 2))])
    b = rng.normal([0, 0], 0.5, (600, 2))
    X, y = np.vstack([a, b]), np.repeat([0, 1], 600)
    two = opsmv.call("classify_class_gmm", opsmv.call("train_class_gmm", X, y, 2), X)
    assert (two["labels"] == y).mean() > 0.99
    assert two["confidence"].min() >= 0.5 - 1e-9


def test_knn_matches_a_brute_force_vote():
    X, y = _blobs(60, 3)
    q = np.random.default_rng(4).normal([3, 3], 3.0, (40, 2))
    model = opsmv.call("train_class_knn", X, y)
    res = opsmv.call("classify_class_knn", model, q, 7)
    z = (X - model["mu"]) / model["sd"]
    zq = (q - model["mu"]) / model["sd"]
    for i in range(len(q)):
        d = np.linalg.norm(z - zq[i], axis=1)
        near = y[np.argsort(d, kind="stable")[:7]]
        counts = np.bincount(near, minlength=3)
        if (counts == counts.max()).sum() == 1:
            assert res["labels"][i] == counts.argmax()
    assert (opsmv.call("classify_class_knn", model, X, 1)["labels"] == y).all()


def test_mlp_and_svm_vector_entries_agree_with_the_pixel_entries():
    X, y = _blobs(100, 6)
    mlp = final_genuine2.train_class_mlp(X, y, hidden=8, epochs=400)
    svm = final_genuine2.train_class_svm(X, y, epochs=300)
    a = opsmv.call("classify_class_mlp", mlp, X)
    b = opsmv.call("classify_class_svm", svm, X)
    assert (a["labels"] == y).mean() > 0.95 and (b["labels"] == y).mean() > 0.9
    image = X[:, :, None].transpose(0, 2, 1)
    assert (final_genuine2.classify_image_class_mlp(image, mlp).ravel() == a["labels"]).all()
    assert (final_genuine2.classify_image_class_svm(image, svm).ravel() == b["labels"]).all()


def test_lexicon_lookup_and_known_edit_distances():
    lex = opsmv.call("create_lexicon", ["sitting", "flaw", "kitten", "kitten"])
    assert lex["words"] == ["flaw", "kitten", "sitting"]
    assert opsmv.call("lookup_lexicon", lex, "flaw") == 1.0
    assert opsmv.call("lookup_lexicon", lex, "flow") == 0.0
    assert opsmv.call("suggest_lexicon", lex, "flow") == {"suggestion": "flaw", "distance": 1}
    assert mvclass._levenshtein("kitten", "sitting") == 3
    assert mvclass._levenshtein("lawn", "flaw") == 2
    assert mvclass._levenshtein("", "abc") == 3


# ---- 文字 ----------------------------------------------------------------- #
def _text_ink(angle=0.0, slant=0.0, seed=0):
    """縦の字画の並ぶ行を、座標を写して描く(画像の回転を経由しない)。"""
    rng = np.random.default_rng(seed)
    H, W = 260, 420
    out = np.zeros((H, W), bool)
    c0, r0 = W / 2.0, H / 2.0
    for line in range(5):
        base = 50 + line * 40
        x = 40
        while x < W - 40:
            w = int(rng.integers(3, 6))
            h = int(rng.integers(14, 22))
            for rr in range(base, base + h):
                for cc in range(x, x + w):
                    sx = cc - c0 - (rr - r0) * math.tan(math.radians(slant))
                    ra, ca = math.radians(angle) * 1.0, sx
                    rn = (rr - r0) * math.cos(ra) + ca * math.sin(ra) + r0
                    cn = ca * math.cos(ra) - (rr - r0) * math.sin(ra) + c0
                    ir, ic = int(round(rn)), int(round(cn))
                    if 0 <= ir < H and 0 <= ic < W:
                        out[ir, ic] = True
            x += w + int(rng.integers(5, 12))
    return out


@pytest.mark.parametrize("angle", [-15.0, -4.0, 0.0, 7.0, 20.0])
def test_text_line_orientation_recovers_the_rotation(angle):
    ink = _text_ink(angle=angle)
    assert ink.sum() > 2000
    assert opsmv.call("text_line_orientation", ink) == pytest.approx(angle, abs=0.5)


@pytest.mark.parametrize("slant", [-20.0, 0.0, 12.0, 30.0])
def test_text_line_slant_recovers_the_shear(slant):
    ink = _text_ink(slant=slant)
    assert ink.sum() > 2000
    assert opsmv.call("text_line_slant", ink) == pytest.approx(slant, abs=1.5)


def test_text_ops_return_zero_without_ink():
    blank = np.ones((32, 32))
    assert opsmv.call("text_line_orientation", blank) == 0.0
    assert opsmv.call("text_line_slant", blank) == 0.0
    assert opsmv.call("segment_characters", blank).max() == 0


def test_segment_and_select_characters_count_known_glyphs():
    im = np.ones((30, 120))
    for x in range(10, 90, 12):
        im[8:22, x:x + 6] = 0.0                    # 7 字
    im[6:9, 100:106] = 0.0
    im[12:22, 100:106] = 0.0                       # 点つきの字
    lab = opsmv.call("segment_characters", im)
    assert lab.max() == 8
    assert (lab[:, 100:106] > 0).sum() == 18 + 60
    assert len(np.unique(lab[:, 100:106])) == 2
    lab2 = lab.copy()
    lab2[0:2, 112:114] = 9                         # 高さの外れた塵
    kept = opsmv.call("select_characters", lab2)
    assert kept.max() == 8
    assert kept[0, 112] == 0


# ---- 空の入力と登録 ------------------------------------------------------- #
_EMPTY = np.zeros((0, 0))
_MASK0 = np.zeros((0, 0), bool)
_EMPTY_CALLS = {
    "binocular_disparity_ms": (_EMPTY, _EMPTY), "binocular_distance_ms": (_EMPTY, _EMPTY, 1.0, 1.0),
    "reconstruct_surface_stereo": (_EMPTY,), "map_image": (_EMPTY, {"row_map": _EMPTY, "col_map": _EMPTY}),
    "rectify_to_world_plane": (_EMPTY, CAM, np.eye(4), 4, 4, 1.0),
    "change_radial_distortion_image": (_EMPTY, CAM, CAM), "crop_rectangle2": (_EMPTY, 1.0, 1.0, 0.0, 2.0, 2.0),
    "atan2_image": (_EMPTY, _EMPTY), "area_center_gray": (_EMPTY,), "gray_histo": (_EMPTY,),
    "gray_projections": (_EMPTY,), "get_grayval_contour_xld": (_EMPTY, np.zeros((1, 2))),
    "points_lepetit": (_EMPTY,), "find_ncc_models": ([], np.zeros((4, 4))),
    "get_circle_pose": (np.zeros((0, 2)), 1.0, CAM), "hit_or_miss_golay": (_MASK0, "l"),
    "hit_or_miss_seq": (_MASK0, "l"), "thickening_hit_miss": (_MASK0, np.ones((3, 3), bool), np.zeros((3, 3), bool)),
    "thickening_golay": (_MASK0, "c"), "thickening_seq": (_MASK0, "c"), "morph_hat": (_MASK0, np.ones((3, 3), bool)),
    "morph_skiz": (_MASK0,), "opening_seg": (_MASK0, np.ones((3, 3), bool)), "gen_nurbs_interp": (np.zeros((0, 2)),),
    "filter_kalman": (np.zeros(0), np.zeros((0, 0)), None, 1.0, 1.0, 1.0, 1.0), "create_bg_esti": (_EMPTY,),
    "train_class_mlp": (np.zeros((0, 2)), np.zeros(0)), "train_class_svm": (np.zeros((0, 2)), np.zeros(0)),
    "create_ncc_model": (_EMPTY,),
    "train_class_gmm": (np.zeros((0, 2)), np.zeros(0)), "train_class_knn": (np.zeros((0, 2)), np.zeros(0)),
    "create_lexicon": ([],), "text_line_orientation": (_EMPTY,), "text_line_slant": (_EMPTY,),
    "segment_characters": (_EMPTY,), "select_characters": (np.zeros((0, 0), int),),
}


@pytest.mark.parametrize("name", sorted(_EMPTY_CALLS))
def test_empty_input_is_refused(name):
    with pytest.raises(ValueError):
        opsmv.call(name, *_EMPTY_CALLS[name])


def test_ledger_has_no_missing_implementation():
    assert opsmv.missing() == []
    assert len(opsmv.OPSMV) == 47


def test_module_doc_example_runs():
    doc = opsmv.__doc__
    code = doc.split("呼び出し例::")[1].split("出力は")[0]
    import textwrap
    env = {}
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(textwrap.dedent(code), env)  # noqa: S102 - 文書の例を実行する
    assert buf.getvalue().splitlines() == ["median disparity: 6.0", "zones meet at col: 39"]


def test_every_op_is_on_the_public_surfaces_with_its_halcon_name():
    import fullseye as fs
    with open(os.path.join(ROOT, "docs", "OP_INDEX.json"), encoding="utf-8") as fh:
        rows = {r["name"]: r for r in json.load(fh)["ops"]}
    import halcon_names_data as HN
    names = set(HN.HALCON_NAMES)
    assert len(names) == 2313
    assert len(opsmv.OPSMV) == 47
    bad = [n for n in opsmv.OPSMV if not callable(getattr(fs.ledger, n))
           or rows[n]["tier"] != "ledger" or rows[n]["halcon"] not in names]
    assert bad == []


def test_halcon_map_points_at_real_ledger_ops_and_real_names():
    import api
    import halcon_names_data as HN
    with open(os.path.join(ROOT, "fullseye", "data", "halcon_ledger_map.json"), encoding="utf-8") as fh:
        table = {k: v for k, v in json.load(fh).items() if not k.startswith("_")}
    assert len(table) >= 100
    rows = {r["name"]: r for r in api.ledger_rows()}
    assert sorted(set(table) - set(rows)) == []
    assert sorted(set(table.values()) - set(HN.HALCON_NAMES)) == []
    assert len(set(table.values())) == len(table)        # 1 op が 1 名を名乗る


def test_facade_map_targets_exist():
    import importlib
    with open(os.path.join(ROOT, "fullseye", "data", "halcon_facade_map.json"), encoding="utf-8") as fh:
        table = {k: v for k, v in json.load(fh).items() if not k.startswith("_")}
    assert len(table) > 600
    bad = [ref for ref in table.values()
           if not callable(getattr(importlib.import_module(ref.rsplit(".", 1)[0]), ref.rsplit(".", 1)[1], None))]
    assert bad == []
