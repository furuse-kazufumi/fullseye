"""Independent numerical gates for omnidirectional imaging."""
import numpy as np
import pytest

import omni360 as O


def _dirs(n=10000):
    rng = np.random.default_rng(275)
    x = rng.normal(size=(n, 3))
    return x / np.linalg.norm(x, axis=1, keepdims=True)


def test_equirectangular_direction_round_trip():
    d = _dirs()
    uv = O.dir_to_equirect(d, 640, 1280)
    got = O.equirect_to_dir(640, 1280, uv)
    assert np.max(np.linalg.norm(got - d, axis=1)) < 1e-12


def test_cubemap_direction_round_trip():
    d = _dirs()
    face, uv = O.dir_to_cubemap(d, 512)
    got = O.cubemap_to_dir(face, uv, 512)
    assert np.max(np.linalg.norm(got - d, axis=1)) < 1e-12
    assert set(face) == set(range(6))


@pytest.mark.parametrize("model", ["equidistant", "equisolid", "stereographic", "orthographic"])
def test_fisheye_closed_forms_and_inverse(model):
    theta = np.linspace(0, np.deg2rad(89), 500)
    d = np.column_stack((np.sin(theta), np.zeros_like(theta), np.cos(theta)))
    uv = O.fisheye_project(d, model=model, f_px=100, centre=(0, 0))
    r = uv[:, 0]
    formulas = {
        "equidistant": 100 * theta,
        "equisolid": 200 * np.sin(theta / 2),
        "stereographic": 200 * np.tan(theta / 2),
        "orthographic": 100 * np.sin(theta),
    }
    assert np.max(np.abs(r - formulas[model])) < 1e-12
    got = O.fisheye_unproject(uv, model=model, f_px=100, centre=(0, 0))
    assert np.max(np.linalg.norm(got - d, axis=1)) < 1e-11


def test_fisheye_rejects_back_and_nonmonotone_polynomial():
    with pytest.raises(ValueError):
        O.fisheye_project([[0, 0, -1]], f_px=100, centre=(0, 0))
    with pytest.raises(ValueError):
        O.fisheye_unproject([[80, 0]], model="polynomial", f_px=100,
                            centre=(0, 0), k=(1, -1))


def test_weight_map_is_four_pi_and_ws_psnr_is_independent_definition():
    h, w = 64, 128
    weights = O.equirect_weight_map(h, w, solid_angle=True)
    assert abs(weights.sum() - 4 * np.pi) < 1e-12
    a = np.zeros((4, 8)); b = np.zeros_like(a); b[0, :] = 0.25
    lat = np.pi / 2 - (np.arange(4) + 0.5) * np.pi / 4
    mse = np.sum((a - b) ** 2 * np.cos(lat)[:, None]) / np.sum(np.cos(lat)[:, None] * np.ones((4, 8)))
    expected = 10 * np.log10(1 / mse)
    assert abs(O.ws_psnr(a, b) - expected) < 1e-12
    assert abs(O.ws_psnr(a, b) - 10 * np.log10(1 / np.mean((a-b)**2))) > 1


def test_constant_resampling_has_no_seam():
    e = np.full((64, 128, 3), 0.375)
    cube = O.cubemap_from_equirect(e, 32)
    back = O.equirect_from_cubemap(cube, (64, 128))
    assert np.ptp(back) == 0
    assert back[0, 0, 0] == 0.375


def test_ods_depth_disparity_closed_form():
    depth = np.array([0.5, 1.0, 3.0, 20.0])
    disp = O.ods_depth_to_disparity(depth, 0.064, 2048)
    angle = 2 * np.arcsin(0.064 / (2 * depth))
    assert np.max(np.abs(disp * 2 * np.pi / 2048 - angle)) < 1e-12
    assert np.max(np.abs(O.ods_disparity_to_depth(disp, 0.064, 2048) - depth)) < 1e-12


def test_pack_roundtrip_and_parallax_budget():
    a = np.arange(24).reshape(4, 6); b = a + 100
    for layout in ("sbs", "tb", "interlaced"):
        packed = O.stereo_pack(a, b, layout)
        aa, bb = O.stereo_unpack(packed, layout)
        assert np.array_equal(aa, a) and np.array_equal(bb, b)
    r = O.stereo_parallax_budget(24, 1920, .6, .531, .064)
    assert r["parallax_mm"] == pytest.approx(24 / 1920 * 531)


def test_true_anaglyph_ideal_filters_have_zero_crosstalk():
    left = np.full((8, 9, 3), .25); right = np.full((8, 9, 3), .75)
    ana = O.anaglyph(left, right, "true")
    seen = O.anaglyph_crosstalk(left, right, method="true")
    assert np.allclose(ana[..., 0], .25) and np.allclose(ana[..., 1:], .75)
    assert seen["ghosting_left"] == 0 and seen["ghosting_right"] == 0

