"""Executable witnesses for the completed wave-3 contract corrections."""
import inspect

import numpy as np
import pytest

import colortransport
import acoustics
import annotate
import annotate3d
import backends_regions3
import carpath
import driveenv
import drivecommonroad
import drivepass
import gfx2d
import grind
import conngraph
import demops
import interferometry
import optics
import optscene
import pcl_augment
import pegsim
import profileops
import pxrd
import roadjp
import mathtransforms
import kendama
import mathnumerics
import mathops
import match3d
import measuring1d
import meshres
import driveplateau
import funct1d
import lightfield
import photoncount
import reprconv
import raytrace
import agvfleet
import pegsym
import quatimage
import racket
import seggraph
import driveinf
import drivetown
import render_beauty
import drivelateral
import sensorgeneral
import spc
import telecentric
import ultrasound
import segcontour


@pytest.mark.parametrize(
    ("op", "statement"),
    [
        (optics.abcd_trace, "1 + |A| + |B| + |C| + |D|"),
        (roadjp.add_sign, "pole_radius + 1.2 cm"),
        (interferometry.csi_height_map, "centroid lose about three decades"),
        (demops.dem_cell_size_webmercator, "約 19 % 過小"),
        (segcontour.gvf_field, "2/(8μ + max b)"),
        (optscene.interface_budget, "42.5 Gbit/s = 5.3125 GB/s"),
        (optics.mueller_element, 'kind="retarder"'),
        (pegsim.peg_params, "カメラ像は px、画角は deg"),
        (profileops.profile_perturb, "contour の座標と同じ単位"),
        (render_beauty.render_beauty, "既定では 13 段"),
        (kendama.swing_up_lift, "2√(2·0.035/g)"),
        (acoustics.weighting_response, "0.23 Hz"),
        (backends_regions3.r3_select_region_point, "round(a*(H-1))"),
        (mathtransforms.abel_inverse_image, "(H, R+1)"),
        (roadjp.add_sign, '"front_faces"'),
        (grind.ae_size_correspondence, '"groups": 群 → 結果'),
        (annotate.annotate_leader_layout, '"label"'),
        (annotate.annotate_legend, "ceil(2r)"),
        (gfx2d.color_lut, "result is clipped once"),
        (drivecommonroad.cr_synthetic, "4 本すべて"),
        (interferometry.csi_peak_position, "carrier-frequency checks"),
        (optics.defocus_from_shift, "2.9 % above"),
        (mathops.dynsys_bifurcation_map, "negative burn-in"),
        (mathops.dynsys_poincare_section, "two-column ``pairs``"),
        (ultrasound.echo_phase_polarity, "参照エコーに対する相対符号"),
        (sensorgeneral.emva_general_sensitivity, "負の μ_p は ValueError"),
        (measuring1d.gen_measure_rectangle2, "max(2, round(2*length1)+1)"),
        (conngraph.graph_layer_propagate, "平均が ``gain``"),
        (spc.gum_expanded, "floor(nu_eff)"),
        (match3d.hough_plane_3d, "半 voxel ずらした"),
        (mathnumerics.integrate_hamiltonian, '"method","system"'),
        (telecentric.lens_equivalent_pinhole, "``width`` / ``height``"),
        (gfx2d.lens_shading_gain, "flat-field response mean"),
        (lightfield.lf_aperture_mask, "for an annulus"),
        (photoncount.lifetime_fit, "centre time of the first usable bin"),
        (meshres.mesh_select_lod, '"pixel_tolerance"'),
        (spc.msa_anova_table, "``n_replicates``"),
        (funct1d.num_points_funct_1d, "returns integer ``0``"),
        (drivepass.overtaken_conduct_check, "対象条件 ``applies``"),
        (reprconv.pairs_to_table, "最大値と最小値の開き"),
        (raytrace.paraxial_trace, "``|efl| / (2·ep_radius)``"),
        (agvfleet.plan_conflicts, "t には v から出た"),
        (pegsym.plane_topview, "(H, W, 3/4)"),
        (pegsym.polygon_peg, "``cut``"),
        (quatimage.riesz_displacement, "closed-form monogenic identities"),
        (pegsym.rotation_window, "``phi_eff``"),
        (raytrace.seidel_coefficients, "``per_surface``"),
        (spc.spc_hotelling_t2, "boolean ``in_control``"),
        (spc.spc_mt_unit_space, "full-rank non-flat"),
        (seggraph.statistical_region_merging, "``q``、``g``"),
        (racket.strategy_attacker, "3 打ごとに flat"),
        (acoustics.synthesize_bearing_signal, "in impulse mode"),
        (driveinf.tile_mesh, '"ij"'),
        (drivetown.town_chain, "2 番目以降の overlap"),
        (acoustics.transfer_function, "``rate``, ``ref``"),
        (annotate3d.annotate3d_scale_bar, "``scheme``: 色名の配色"),
        (annotate.annotate_table_layout, "font_path : str or None"),
        (annotate.annotate_table_layout, "line_spacing : float"),
        (render_beauty.render_beauty, "``albedo_variation``"),
    ],
)
def test_corrected_contract_is_public(op, statement):
    assert statement in inspect.getdoc(op)


def test_corrected_contracts_match_behavior():
    assert '(length, cost)。' in inspect.getsource(carpath.car_hybrid_astar)
    geometry = {"cx": 0, "cy": 0, "distance": 100, "pixel": 0.1, "wavelength": 0.5}
    with pytest.raises(ValueError, match="positive integers"):
        pxrd.detector_two_theta((2.5, 3), geometry)
    source = np.array([[0, 0], [1, 0], [0, 1.0]])
    reference = np.array([[0, 0], [1, 0], [2, 0.0]])
    with pytest.raises(ValueError, match="reference covariance is singular"):
        colortransport.gaussian_transport_map(source, reference)
    with pytest.raises(ValueError, match="clip must be > 0"):
        pcl_augment.jitter(np.empty((0, 3)), 1, clip=0)
    with pytest.raises(ValueError, match="real and unmasked"):
        optics.mueller_checks(np.eye(4, dtype=complex))
    with pytest.raises(ValueError, match="rows is empty"):
        driveenv.road_row_distance(np.empty((0, 4)), 10, 100, 1.5)
    with pytest.raises(ValueError, match="step_divisor must be > 4"):
        interferometry.csi_design(step_divisor=4)
    assert pcl_augment.jitter([], 1).shape == (0, 3)
    assert pcl_augment.random_dropout([], 0.5)[0].shape == (0, 3)
    assert pcl_augment.random_rotation([])[0].shape == (0, 3)
    with pytest.raises(ValueError, match="start_index out of range"):
        drivelateral.lateral_offset([[0, 0]], [[0, 0], [1, 0]], start_index=1)
    points = np.array([[0.0, 0.0, 0.0], [1, 0, 0]])
    lod = meshres.pc_lod_chain(points, 0.5, levels=1)
    assert not np.shares_memory(lod["levels"][0], points)


def test_plateau_parse_max_buildings_limit_is_a_ceiling_including_zero():
    """監査(第 3 波)のコード修正: ``max_buildings=0`` が 1 棟を通していた(上限判定の前に append していた)。"""
    import driveplateau as pp

    origin = (35.681, 139.767)
    xml = pp.citygml_synthetic(3, origin=origin, size=12.0, heights=[8.0, 15.5, 31.0])
    assert len(pp.plateau_parse(xml, origin=origin, max_buildings=0)["buildings"]) == 0
    assert len(pp.plateau_parse(xml, origin=origin, max_buildings=2)["buildings"]) == 2
    assert len(pp.plateau_parse(xml, origin=origin)["buildings"]) == 3
