"""2026-10-18 docstring/code audit, wave 1 regression tests."""
import inspect

import numpy as np
import pytest

import agvfleet
import annotate
import astrostack
import backends_inverse
import cavityoptics
import colortransport
import demops
import drivecommonroad
import drivecrossing
import driveworld
import flyvision
import gwsearch
import kendama
import lensimage
import lightfield
import mathops
import mathspectral
import mesh_props
import pegsym
import polish
import printpath
import profileops
import pxrd
import raytrace
import render3d
import render_beauty
import roadjp
import scoop
import sensorgeneral
import spc
import volops


@pytest.mark.parametrize(
    ("op", "statement"),
    [
        (flyvision.fly_onoff_split, "twice the low-passed input"),
        (agvfleet.vda5050_check, "足りない必須キーの一覧"),
        (mathops.wave_membrane_mode, "``free_edge=True`` combined"),
        (pxrd.cubic_index, "収束は保証しない"),
        (annotate.annotate_invert, "``max(1, round(width / 2))``"),
        (astrostack.cosmic_ray_reject, "汚染判定画素も含む"),
        (sensorgeneral.emva_general_nonuniformity, '"dark", "bright"'),
        (printpath.halftone_screen, "scaled sum"),
        (lensimage.calibration_views, "default: six poses"),
        (lightfield.lf_synthesize, "[2, MAX_SPATIAL]"),
        (gwsearch.matched_filter_snr, "len(template) − ref − 1"),
        pytest.param(annotate.annotate_dimension_layout, "sign(offset)*extension", id="dimension-extension"),
        pytest.param(annotate.annotate_dimension_layout, "sign(offset)*n*text_gap", id="dimension-text-side"),
        (annotate.annotate_scale_bar_layout, "(W - 2*margin)"),
        (mathops.cplx_rational_field, "poles-only field"),
        (drivecommonroad.cr_synthetic, "v0 が負"),
        (demops.dem_geodetic_to_ecef, "``(N, 3)``"),
        (cavityoptics.fabry_perot_response, "``mode_number``"),
        (flyvision.fly_tau_from_expansion, '``"sphere"`` as the default'),
        (colortransport.gaussian_transport_map, "``A`` と平均 ``m1, m2``"),
        (printpath.gcode_layer_image, "移動を描く場合 0.5"),
        (drivecrossing.legal_stop_intervals, "道路全体から車長を引いた区間"),
        (mathops.ode_flow_states, "named ``x0``, ``x1``"),
        (polish.polish_scene_mjcf, "楕円(elliptic)"),
        (profileops.profile_chord_frame, "厚み(girth)"),
        (raytrace.spot_diagram, "obtained separately"),
        (driveworld.world_camera, "|n·l|"),
        (kendama.catch_success_rate, '"lift"'),
        (kendama.hole_detect, "area は 0"),
        (mathspectral.music_doa, '"n_sources", "n_sources_estimated"'),
        (pegsym.polygon_two_point_depth, "傾けた状態で最狭部"),
        (roadjp.signal_jp_mesh, '"lens", "state"'),
        (render3d.terrain_region_mask, "重みなし SVD"),
        (scoop.tilted_surface_read, "L_px + 1"),
        (backends_inverse.iv_wiener_deconv_spatial, "[0.4,"),
        (render_beauty.render_beauty, "``surface`` / ``surface_params``"),
    ],
)
def test_rewritten_contract_is_in_public_docstring(op, statement):
    assert statement in inspect.getdoc(op)


def test_spc_mt_distance_rejects_empty_data_with_complete_unit_space():
    with pytest.raises(ValueError, match="must not be empty"):
        spc.spc_mt_distance(np.empty((0, 2)), mean=np.zeros(2), std=np.ones(2), inv_corr=np.eye(2))


def test_selected_rewritten_contracts_have_behavior_checks():
    """Keep cheap executable witnesses beside the wording checks above."""
    movie = np.array([[0.0], [1.0], [0.0]])
    split = flyvision.fly_onoff_split(movie, 1.0, tau_on_s=0.1, tau_off_s=0.1, rectify=False)
    assert split.shape == (3, 2)
    np.testing.assert_allclose(split[:, 0] - split[:, 1], 2 * split[:, 0])

    missing = agvfleet.vda5050_check({})
    assert "missing key nodes" in missing and "missing key edges" in missing

    with pytest.raises(ValueError, match="vanishes identically"):
        mathops.wave_membrane_mode(m=2, n=2, shape=(8, 8), free_edge=True)

    with pytest.raises(ValueError, match=r"shape\[0\].*\[2, 4096\]"):
        lightfield.lf_synthesize(shape=(0, 4))

    pole = 0.25 + 0.25j
    poles_only = mathops.cplx_rational_field([], [pole], shape=(5, 5))
    assert poles_only.shape == (5, 5)
    np.testing.assert_allclose(poles_only[2, 2], 1 / -pole)

    ecef = demops.dem_geodetic_to_ecef([0.0, 10.0], [[0.0], [90.0]])
    assert ecef.shape == (4, 3)

    src = np.array([[0, 0], [1, 0], [0, 1], [2, 2]], dtype=float)
    ref = np.array([[1, 2], [3, 2], [1, 4], [5, 6]], dtype=float)
    A, m1, m2 = colortransport.gaussian_transport_map(src, ref)
    assert A.shape == (2, 2)
    np.testing.assert_allclose(m1, src.mean(axis=0))
    np.testing.assert_allclose(m2, ref.mean(axis=0))

    stops = drivecrossing.legal_stop_intervals(np.empty((0, 2)), 0.0, 10.0, 2.0)
    np.testing.assert_array_equal(stops, [[0.0, 8.0]])

    states = mathops.ode_flow_states(t_end=0.02, dt=0.01)
    assert {"t", "x0", "x1", "x2"} <= states.keys()
    assert all(states[key].shape == states["t"].shape for key in ("x0", "x1", "x2"))

    hole = kendama.hole_detect(np.ones((16, 16, 3)), (8, 8), 5)
    assert hole["found"] is False and hole["area"] == 0
    assert all(np.isnan(hole[key]) for key in ("col", "row", "angle", "offset", "ellipticity"))

    X = np.random.default_rng(0).normal(size=(4, 32))
    doa = mathspectral.music_doa(X, n_sources=1, grid_deg=np.linspace(-90, 90, 19))
    assert {"grid_deg", "pseudo_spectrum_db", "doa_deg", "eigenvalues",
            "n_sources", "n_sources_estimated"} <= doa.keys()

    signal = roadjp.signal_jp_mesh(n=1)
    assert {"V", "F", "color", "label", "lamp_faces", "width", "height",
            "depth", "lens"} <= signal.keys()
    assert signal["label"] == 3

    degenerate = (np.array([[0, 0, 0], [1, 0, 0], [2, 0, 0.0]]),
                  np.array([[0, 1, 2]]))
    np.testing.assert_array_equal(mesh_props.face_areas(degenerate), [0.0])

    down = volops.volume_downsample(np.arange(5 * 7 * 9).reshape(5, 7, 9), (2, 3, 4))
    assert down.shape == (2, 2, 2)

    with pytest.raises(ValueError, match="two_theta must be in"):
        pxrd.cubic_index([0.0, 20.0], wavelength=1.54)

    dimension = annotate.annotate_dimension_layout(
        (0, 0), (10, 0), offset=5, extension=2, text_gap=3
    )
    assert dimension["ext0"] == ((0.0, 0.0), (0.0, 7.0))
    assert dimension["text_xy"] == (5.0, 8.0)

    scale_bar = annotate.annotate_scale_bar_layout(
        (100, 200), 1.0, target_fraction=0.2, margin=10
    )
    assert scale_bar["length"] == 20.0
    assert scale_bar["rect"] == (170, 85, 20, 5)


@pytest.mark.parametrize(("n_inliers", "raises"), [(3, False), (2, True)])
def test_frame_align_minimum_ransac_inliers_is_inclusive(monkeypatch, n_inliers, raises):
    frames, _ = astrostack.synth_frame_series(
        shape=(64, 64), n_frames=2, n_stars=12, dither_px=1.0, seed=17
    )
    def ransac(points, *args, **kwargs):
        inliers = np.zeros(points.shape[0], dtype=np.bool_)
        inliers[:n_inliers] = True
        return {"inliers": inliers}

    monkeypatch.setattr(astrostack.mosaic, "proj_match_points_ransac", ransac)
    if raises:
        with pytest.raises(ValueError, match="RANSAC kept only 2 inlier"):
            astrostack.frame_align(frames[0], frames[1], min_inliers=3)
    else:
        matrix, info = astrostack.frame_align(frames[0], frames[1], min_inliers=3)
        assert matrix.shape == (3, 3)
        assert matrix.dtype == np.float64
        assert info["n_inliers"] == 3


_ROUNDED_RECT_ROWS = {
    (0, 1): ["#######", "#.....#", "#.....#", "#.....#", "#.....#", "#.....#", "#######"],
    (0, 2): ["#######", "#######", "##...##", "##...##", "##...##", "#######", "#######"],
    (1, 1): [".#####.", "#.....#", "#.....#", "#.....#", "#.....#", "#.....#", ".#####."],
    (1, 2): [".#####.", "#######", "##...##", "##...##", "##...##", "#######", ".#####."],
    (2, 1): ["..###..", ".#...#.", "#.....#", "#.....#", "#.....#", ".#...#.", "..###.."],
    (2, 2): ["..###..", ".#####.", "##...##", "##...##", "##...##", ".#####.", "..###.."],
}


@pytest.mark.parametrize(("radius", "width"), _ROUNDED_RECT_ROWS)
def test_rounded_rect_exact_hollow_pixel_sets(radius, width):
    expected = {
        (row, col)
        for row, pattern in enumerate(_ROUNDED_RECT_ROWS[radius, width])
        for col, value in enumerate(pattern) if value == "#"
    }
    out = annotate.rounded_rect(
        np.zeros((8, 8)), (0, 0, 7, 7), radius=radius,
        color=(1, 1, 1), width=width,
    )
    actual = set(map(tuple, np.argwhere(out != 0)))
    assert actual == expected
    assert out[3, 3] == 0.0


@pytest.mark.parametrize("radius", [-1, np.nan])
def test_rounded_rect_rejects_invalid_radius(radius):
    with pytest.raises(ValueError, match="radius must be >= 0"):
        annotate.rounded_rect(np.zeros((8, 8)), (0, 0, 7, 7), radius=radius)
