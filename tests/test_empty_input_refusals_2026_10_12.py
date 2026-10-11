# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""空の入力の方針 A(2026-10-12): 黙って値を返さず、何が空かを名指しの ValueError で言う。

台帳の空入力の探針(``tools/ledger_gaps.py``)で、第 1 引数を空にしても**黙って値を返す**台帳 op が
213 本、生の例外(KeyError 75・torch の RuntimeError 23・FileNotFoundError 5)で落ちる op が 103 本
あった。持ち主の方針 A で、

* 273 本は入口で ``ValueError("<op>: <引数> is empty — …")`` を投げ、docstring に
  「空の入力(``引数`` が 0 要素)は ValueError」と書いた(台帳の門が約束として読む)。
* 43 本は「空は値の範囲の内側」で、空を返すのが正しい答え(点群フィルタの連鎖・funct_1d・
  施設の無い道路 …)。拒否せず、docstring に「空の入力(``引数`` …)は空を返す(理由: …)」と
  名指し・理由つきで書いた。

以後は ``tests/test_ledger_contracts.py`` の門が、どちらの文も無いまま値を返す op
(``silent_on_empty``)と生の例外(``raw_*``)を新規の違反として落とす。ここは同じ 2 群を
個別に固定する回帰試験。入力はその門と同じ探針(``ledger_contracts.bind``)で組み、第 1 引数だけを
空にする。空でない元の入力での実行は台帳の門(契約: 例外を投げない)が見ている。
"""
from __future__ import annotations

import inspect
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (ROOT, os.path.join(ROOT, "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

lc = pytest.importorskip("ledger_contracts")
lg = pytest.importorskip("ledger_gaps")

#: 空の第 1 引数を名指しの ValueError で断るようにした op(黙って値を返していた・生の例外だった)。
REFUSED = (
    "ackermann_steer_angles", "add_ball", "add_frame_corners", "add_ken", "add_mesh_object",
    "add_metrology_object_circle_measure", "add_metrology_object_ellipse_measure",
    "add_metrology_object_generic", "add_metrology_object_line_measure",
    "add_metrology_object_rectangle2_measure", "add_sign", "add_signal_jp", "add_string",
    "adg_execute", "align_metrology_model", "antialias", "apply_metrology_model",
    "apply_transport", "arc_length", "ball_set_pose", "ball_track", "ball_truth",
    "beer_lambert_transmittance", "bessel", "blast_normals", "box_sdf", "bus_stop_rate",
    "calib_pack_load", "camera_rig", "capsule_sdf", "carla_depth_decode", "carla_depth_encode",
    "carla_label_map", "carla_label_unmap", "catch_plan_ballistic", "catch_plan_staged",
    "catch_success_rate", "classify_image_class_lut", "color_transfer", "compressed_size",
    "cone_profile_px", "convex_mirror_image", "course_distance", "crossing_gate_state",
    "curvature_maps", "curve_speed_limit", "cylinder_sdf", "cylinder_unwrap", "data_to_pixel",
    "dem_ecef_to_geodetic", "depth_to_organized_points", "depth_to_points",
    "descriptor_distance", "design_min_radius", "displace_markers", "distance_peaks",
    "drag_coefficient_sphere", "dtof_cube_depth", "edge_alias_energy", "edge_points", "edt_jfa",
    "env_lightbox", "env_render", "env_studio", "erf", "erfc", "esdf", "events_to_frames",
    "exit_room_check", "farthest_point_sampling", "fem_nodes_load", "fem_vs_halfspace",
    "filter_by_volume", "find_peaks", "fivebar_reach_interval", "fivebar_workspace",
    "flow_from_depth_motion", "fresnel_conductor", "fresnel_dielectric", "fresnel_integrals",
    "fuzzy_measure_pairing", "grating_rgb", "gs_from_world", "gs_render", "gs_update",
    "harris3d_keypoints", "hertz_pressure", "hertz_surface_ur", "hertz_surface_uz", "hessian3d",
    "hole_detect", "hough_plane_3d", "hough_sphere_3d", "humanoid_clip_mesh",
    "humanoid_impostors", "idm_equilibrium_gap", "inflate", "inside_outside", "invariants",
    "iss_keypoints", "japan_stats", "japan_world", "ken_set_pose", "ken_truth",
    "kendama_catch_check", "kendama_combo_simulate", "kendama_simulate", "lab_to_rgb",
    "label_extent", "laplace_inverse_talbot", "largest_component", "lateral_offset",
    "lf_disparity_to_depth", "light_wavelengths", "linear_to_srgb", "link_edges",
    "long_energy_residual", "luma_limited_u8", "magnus_lift_coefficient", "mandelbrot_interior",
    "marker_match_grow", "match_chamfer_3d", "match_curvature_3d", "match_hough_3d",
    "match_pca", "match_points_ncc", "match_sh_descriptor", "match_shape_3d", "measure_pairs",
    "measure_pos", "membrane_predict_rgb", "membrane_render_markers", "membrane_render_rgb",
    "membrane_shear_field", "mindlin_fit", "mindlin_fit_vector", "mindlin_model",
    "mindlin_traction", "moment_axes", "morph_blackhat3d", "morph_close3d", "morph_dilate3d",
    "morph_erode3d", "morph_gradient3d", "morph_open3d", "morph_tophat3d", "naive_execute",
    "normalize", "occlusion_edges", "occlusion_safe_speed", "occupancy_grid", "oren_nayar",
    "osm_road_graph", "osm_road_loops", "osm_road_mask", "osm_route", "peg_tip_from_rgbd",
    "plan_command", "plan_cost", "plane_sdf", "potential_flow_cylinder",
    "preston_track_profile", "prism_min_deviation_deg", "project", "project_points",
    "puck_camera", "puck_crossing_point", "puck_pinhole_camera", "puck_pixel_to_world",
    "puck_render_frame", "puck_scene_mjcf", "puck_state_at", "puck_synth_frames",
    "puck_world_to_pixel", "punch_surface_uz", "quantize", "radon_volume", "rally_simulate",
    "read_audio", "read_wav", "reconstruct", "refine_lm", "refine_peak_newton",
    "refine_translation_lk", "reflect_points", "render_lambertian", "render_point_depth",
    "render_shaded", "render_volume_projection", "reproject", "resample_uniform", "rgb_to_lab",
    "rgb_to_xyz", "ritter_dam_break", "rms", "road_eval", "road_row_distance",
    "rough_transmission", "scatter_offroad", "sdf_offset", "sdf_to_occupancy", "sensor_capture",
    "separate_touching", "sh_descriptor", "sheen_shade", "signal_features",
    "signed_distance_field", "slab_transmittance", "sobel3d", "spectrogram", "sph_kernel",
    "sphere_sdf", "spheres_render_shaded", "spheres_to_heightmap", "spheres_to_silhouette",
    "spin_from_marker_sequence", "srgb_to_linear", "string_set", "subsurface_approx",
    "surface_divergence_closed_form", "swing_up_apex", "swing_up_lift", "swing_up_plan",
    "synthesize_fringes", "synthesize_silhouette", "table_world", "terrain_mesh", "tf_bilinear",
    "tf_freq_response", "tf_impulse_response", "tf_poles_zeros", "tf_step_response",
    "thin_film_rgb", "tile_digest", "to_points", "tone_map", "torus_sdf", "track_triangulate",
    "translate_measure", "triangulate_column", "ttc_truth", "unwrap_phase_2d", "vol_affine",
    "vol_boundary", "vol_boundary_points", "vol_distance_transform", "vol_gradient_magnitude",
    "vol_granulometry", "vol_hessian_blobness", "vol_label", "vol_local_maxima",
    "vol_local_std", "vol_local_thickness", "vol_rle_components", "vol_rle_encode",
    "vol_rotate", "vol_tiled_map", "vol_uncrop", "vol_window_level", "ward_anisotropic",
    "watershed_vol", "watersheds_marker", "wave_fringe_period", "wetness", "world_build",
    "world_camera", "world_camera_impostors", "world_materials", "world_move",
    "world_pose_humanoid", "write_wav", "xyz_to_lab", "zero_crossing_rate",
)

#: 空を返すのが正しい答えの op(理由の区分ごと。理由の本文は各 docstring に書いてある)。
ACCEPTED = {
    "build": (
        "building_prisms",
    ),
    "cache": (
        "tile_stream",
    ),
    "cplx": (
        "cplx_rational_field",
    ),
    "f1d": (
        "abs_funct_1d", "create_funct_1d_array", "funct_1d_to_pairs", "invert_funct_1d",
        "local_min_max_funct_1d", "negate_funct_1d", "num_points_funct_1d", "sample_funct_1d",
        "scale_y_funct_1d", "transform_funct_1d", "zero_crossings_funct_1d",
    ),
    "flow": (
        "estimate_flow", "nearest_neighbor_flow", "smooth_flow",
    ),
    "knn": (
        "knn_graph",
    ),
    "legal": (
        "legal_stop_intervals",
    ),
    "pcl": (
        "cutout", "elastic_deform", "jitter", "mls_smooth", "radius_outlier_removal",
        "random_dropout", "random_rotation", "random_scale", "statistical_outlier_removal",
        "voxel_grid_downsample",
    ),
    "region": (
        "label_components", "region_props",
    ),
    "scan": (
        "project_cylindrical", "project_spherical",
    ),
    "seg": (
        "euclidean_cluster", "plane_segmentation", "region_growing", "segment_rigid_motions",
    ),
    "skill": (
        "skill_test_score",
    ),
    "swarm": (
        "swarm_render_overhead",
    ),
    "text": (
        "measure_text",
    ),
    "vda": (
        "vda5050_check",
    ),
    "zones": (
        "no_overtaking_zones", "no_stopping_zones",
    ),
}
ACCEPTED_NAMES = tuple(sorted(n for v in ACCEPTED.values() for n in v))


@pytest.fixture(scope="module")
def bound():
    cf = lc._cf()
    ops = {o[0]: o for o in lc.ledger_ops()}
    extra = dict(lc._io_builders(), **lc.probe_builders())
    out = {}
    with cf._scratch_cwd():
        rng = np.random.default_rng(lc._SEED)
        gens = cf.make_generators()
        pool = {t: [g(rng)] for t, g in sorted(gens.items())}
        recipe = cf.type_recipes(list(ops.values()), gens)

        def ensure(sort, depth=0):
            # a sort without a generator (``metrologymodel`` …) comes from its DECLARED producer,
            # as in ``ledger_contracts.run``
            if sort == "any" or pool.get(sort) or depth > 8:
                return
            if not recipe.get(sort):
                return
            pname = recipe[sort][-1]             # the sort's producer, exactly as in the probe
            _pn, _pl, pins, _pout, pfn = ops[pname]
            for u in pins:
                ensure(u, depth + 1)
            pargs, pkw = lc.bind(pname, pfn, pins, pool, cf, extra)
            res = lc._call(pfn, pargs, pkw)
            adapter = cf.ADAPTERS.get(pname)     # the probe stores the ADAPTED result
            pool[sort] = [adapter(res) if adapter is not None else res]

        for name in REFUSED + ACCEPTED_NAMES:
            _n, _led, ins, _out, fn = ops[name]
            try:
                for t in ins:
                    ensure(t)
                args, kwargs = lc.bind(name, fn, ins, pool, cf, extra)
            except Exception as e:               # noqa: BLE001 - recorded, judged per test
                out[name] = (fn, None, e)
                continue
            out[name] = (fn, args, kwargs)
    return out


def _args(bound, name):
    fn, args, kwargs = bound[name]
    if args is None:
        if lc.optional_missing(kwargs):
            pytest.skip("optional backend missing while binding: %s" % kwargs)
        raise AssertionError("%s: the probe could not bind its arguments: %r" % (name, kwargs))
    if not args:
        pytest.skip("%s: the probe binds no positional argument" % name)
    return fn, args, kwargs


def _names(fn):
    names = list(inspect.signature(fn).parameters)
    return names[0], names[1:]


def test_the_two_lists_do_not_overlap_and_cover_the_count():
    assert not set(REFUSED) & set(ACCEPTED_NAMES)
    assert len(REFUSED) == 273 and len(ACCEPTED_NAMES) == 43


@pytest.mark.parametrize("name", REFUSED)
def test_empty_first_input_is_a_named_value_error(bound, name):
    fn, args, kwargs = _args(bound, name)
    empty = lg.empty_like(args[0])
    assert empty is not None
    first, others = _names(fn)
    with pytest.raises(ValueError, match="%s is empty" % first):
        lc._call(fn, [empty] + list(args[1:]), kwargs)
    # docstring の約束として読めること(台帳の門がこの op を見張る条件)
    assert lg.promises_empty_refusal(fn.__doc__ or "", first, others), name


@pytest.mark.parametrize("name", ACCEPTED_NAMES)
def test_empty_first_input_returns_with_a_stated_reason(bound, name):
    fn, args, kwargs = _args(bound, name)
    empty = lg.empty_like(args[0])
    assert empty is not None
    try:
        lc._call(fn, [empty] + list(args[1:]), kwargs)
    except Exception as e:                       # noqa: BLE001
        if lc.optional_missing(e):
            pytest.skip("optional backend missing: %s" % e)
        raise
    first, others = _names(fn)
    doc = fn.__doc__ or ""
    assert lg.documents_empty_result(doc, first), name
    assert not lg.promises_empty_refusal(doc, first, others), name
