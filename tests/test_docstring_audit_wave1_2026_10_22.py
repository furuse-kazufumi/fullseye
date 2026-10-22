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


@pytest.mark.parametrize(
    ("op", "statement"),
    [
        (flyvision.fly_onoff_split, "twice the low-passed input"),
        (agvfleet.vda5050_check, "足りない必須キーの一覧"),
        (mathops.wave_membrane_mode, "``free_edge=True`` combined"),
        (pxrd.cubic_index, "追い込みを 4 回"),
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


def test_frame_align_refuses_too_few_ransac_inliers(monkeypatch):
    frames, _ = astrostack.synth_frame_series(
        shape=(64, 64), n_frames=2, n_stars=12, dither_px=1.0, seed=17
    )
    monkeypatch.setattr(
        astrostack.mosaic,
        "proj_match_points_ransac",
        lambda *args, **kwargs: {"inliers": np.zeros(args[0].shape[0], dtype=bool)},
    )
    with pytest.raises(ValueError, match="RANSAC kept only"):
        astrostack.frame_align(frames[0], frames[1], min_inliers=3)


def test_radius_zero_rounded_rect_draws_only_the_requested_border():
    out = annotate.rounded_rect(
        np.zeros((12, 12)), (2, 2, 8, 8), radius=0, color=(1, 1, 1), width=2
    )
    assert out[2, 2] == 1.0
    assert out[5, 5] == 0.0
    assert np.count_nonzero(out) < 64
