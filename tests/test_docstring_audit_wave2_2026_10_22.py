"""Executable witnesses for the completed wave-2 contract corrections."""
import inspect
import importlib

import numpy as np
import pytest

import flyvision
import lightfield
import materials
import mathops
import photoncount
import raytrace
import render3d
import ultrasound


@pytest.mark.parametrize(
    ("op", "statement"),
    [
        (flyvision.traj_tau_dot, '"mode"'),
        (lightfield.lf_disparity_to_depth, "one-element ``(1,)``"),
        (materials.material_optical_constants, "``epsilon_re`` / ``epsilon_im``"),
        (materials.material_transmittance, "``T=(1-R)/(1+R)``"),
        (mathops.cplx_rational_field, "sampled zero is returned as zero"),
        (mathops.curve_locality, "otherwise the minimum mean distance"),
        (photoncount.photon_sample, "optional non-negative integer (default 0)"),
        (photoncount.anscombe_inverse, "values below"),
        (raytrace.lens_system, "smallest non-null"),
        (render3d.gyroid_isosurface, "or a level outside"),
        (ultrasound.echo_phase_polarity, "tol_deg が (0, 90)"),
    ],
)
def test_corrected_contract_is_public(op, statement):
    assert statement in inspect.getdoc(op)


def test_corrected_contracts_match_behavior():
    trajectory = flyvision.traj_tau_dot(
        [[3, 0, 0], [2, 0, 0], [1, 0, 0]], [0, 1, 2]
    )
    assert trajectory["mode"] == "point"

    assert lightfield.lf_disparity_to_depth(2.0).shape == (1,)
    assert lightfield.lf_disparity_to_depth([2.0], far_depth=-1).shape == (1,)
    with pytest.raises(ValueError, match="far_depth must be >= 0"):
        lightfield.lf_disparity_to_depth([0.0], far_depth=-1)

    optical = materials.material_optical_constants("SI", 1000)
    assert "epsilon" not in optical and {"epsilon_re", "epsilon_im"} <= optical.keys()
    t0 = materials.material_transmittance("SI", 0, wl_min_nm=1000, wl_max_nm=1001, n_points=2)
    assert t0[0, 1] < 1

    field = mathops.cplx_rational_field([0j], [], shape=(5, 5))
    assert field[2, 2] == 0j
    locality = mathops.curve_locality([[0, 0], [1, 0], [2, 0], [3, 0], [4, 0]], gaps=(2, 1))
    assert locality["ratio"][0] == 2 and locality["ratio"][1] == 1

    image = np.ones((2, 2))
    np.testing.assert_array_equal(photoncount.photon_sample(image), photoncount.photon_sample(image))
    assert photoncount.anscombe_inverse([[1.2]], mode="unbiased")[0, 0] == 0

    system = raytrace.lens_system(
        [{"R": 10, "t": 1, "n": 1.5, "ap": 4}, {"R": -10, "t": 0, "n": 1, "ap": None}],
        stop=1,
    )
    assert system["surfaces"][1]["ap"] == 4
    assert "thickness" not in inspect.signature(render3d.gyroid_isosurface).parameters
    with pytest.raises(ValueError, match="tol_deg"):
        ultrasound.echo_phase_polarity(np.ones(9), tol_deg=0)


_WAVE2_MORE = [
    ("roverslip", "bekker_wheel_sinkage", "約 32 %"), ("pxrd", "detector_calibrate", "4 回"),
    ("seggraph", "graph_cut_binary", "max_p |D_p(0)-D_p(1)|"), ("gsplatnp", "gs_update", "末尾に面が追加"),
    ("kendama", "kendama_params", "けん先と穴の太さは比較しない"), ("printpath", "mesh_slice_contours", "2*tol + 1e-12"),
    ("acoustics", "octave_spectrum", "0.999*rate/2"), ("pegsim", "peg_scene_mjcf", "約 0.03 %"),
    ("pivops", "piv_peak_locking", "2*bins - 1"), ("driveenv", "sun_events", "1e-7 日未満"),
    ("colortransport", "transport_cost", "質量の合計は制限しない"), ("driveterrain", "tree_mesh", "0.6675·height"),
    ("volcolor", "vol_label_shape_stats", "10 回"), ("volops", "vol_local_std", "6.4%"),
    ("backends_aug", "aug_rolling_shutter", "0.125*W*a"), ("backends_filters2", "f2_gray_inside", "0.02 + 0.98*a"),
    ("backends_texture", "fractal_dimension", "必須の閾値"), ("annotate", "annotate_leader", "0 の cap_size"),
    ("blob2d", "blob_label", "既定は 4 連結"), ("geocam", "camera_orientation_from_sun", "最大の特異値の比"),
    ("ballworld", "camera_rig", '"width", "height"'), ("fourierdesc", "contour_fourier_complex", "(2K, 3)"),
    ("render3d", "curve3d_tube_mesh", "single repeated interior pair"), ("match3d", "cylinder_unwrap", "0 除算は生じない"),
    ("demops", "dem_flow_direction", "境界外へ向かう 0-7"), ("diabolo", "diabolo_axis_from_image", '"hub_px", "rim_px"'),
    ("printpath", "engrave_lines", "max_width * d"), ("match3d", "icp_point2point_3d", "CPU 上の NumPy"),
    ("imgforensics", "jpeg_quality_estimate", "n_coeff - 1"), ("optscene", "linescan_capture", "段間平均"),
    ("match3d", "match_chamfer_3d", "有効範囲の先頭"), ("fiberoptics", "material_gvd", "長い波長が遅い"),
    ("imgmetrics", "metrics_table", "ここに無い指標を落とし"), ("match3d", "moment_axes", "明示的に ValueError"),
    ("spc", "msa_anova_table", "部品と測定者"), ("mathspectral", "music_doa", "角度の昇順"),
    ("pegsim", "peg_measure_overlay", "2*crop"), ("perpetual", "perpetual_flow_field", "正規化後の場は厳密な非圧縮場ではない"),
    ("drivelateral", "pure_pursuit_circle_offset", "v < 0.5"), ("pcseg", "region_growing", "expanded further only"),
    ("feat_fpfh", "register_fpfh", "0 で無効化"), ("carlabridge", "scene_pair_table", '"view"'),
    ("sdf_ops", "sdf_intersect", "距離の下界"), ("emproof", "seg_membrane_chord_score", "距離 ≤ band + 3"),
    ("segcompare", "seg_synapse_nri", "n_lost"), ("roadjp", "signal_jp_mesh", "見て右から青・黄・赤"),
    ("geocam", "skyline_extract", "平均の境界応答"), ("pegsym", "spiral_search_points", "worst_gap"),
    ("driveinf", "tile_stream", "全区画を読み込み"), ("driveplateau", "triangulate_polygon", "有効頂点数を m"),
    ("volops", "vol_granulometry", "median"), ("agvfleet", "warehouse_grid", "格子の ``shape``"),
    ("imgforensics", "watermark_capacity", "ll_shape"), ("backends_filters2", "f2_bit_slice", "0..1"),
    ("backends_regions2", "r2_union1", "2-D 化した形"), ("imgmetrics", "measure_with", "ms"),
    ("pivops", "piv_multipass", "normalize"),
]


@pytest.mark.parametrize(("module", "name", "fragment"), _WAVE2_MORE)
def test_more_corrected_contracts_are_public(module, name, fragment):
    assert fragment in inspect.getdoc(getattr(importlib.import_module(module), name))


def test_more_corrected_contracts_match_behavior():
    import agvfleet, backends_regions2, driveplateau, pegsym, sdf_ops
    assert sdf_ops.sdf_intersect(1.0, 2.0) == 2.0
    assert pegsym.spiral_search_points(2, 2, 3)["worst_gap"] == pytest.approx(2 ** 0.5)
    assert driveplateau.triangulate_polygon([[0, 0], [1, 0], [2, 0], [2, 1], [0, 1]]).shape == (2, 3)
    grid, info = agvfleet.warehouse_grid(1, 1, 1, 1, 1)
    assert info.keys() == {"racks", "shape"} and info["shape"] == grid.shape
    assert backends_regions2.r2_union1([0, 1], 0, 0).shape == (1, 2)
