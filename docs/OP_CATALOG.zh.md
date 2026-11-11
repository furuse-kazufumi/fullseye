# Fullseye Operator Catalog — AI capability ledger

Fullseye 是一个可解释的经典/几何视觉 Physical-AI 工具包。本台账是一份清单，**只要告知用途，AI 就能据此提出该组合哪些 op、如何组合**。

## 本台账的使用方法(面向 assistant)

1. 确定用户的**用途(输入数据、想要的输出)**。
2. 先在 **Worked examples**(用途→op 的实例)中找到最接近的一个，以其 op 链为基础。
3. 组链时让 **in → out 的数据种类**首尾相接(例: `image → region → feature`、`points → voxel → mesh`)。2D 流水线 op 采用“1 幅图像 + 2 个标量旋钮”的模型；点云/体数据的 3D op 以及取 2 幅图像的 op(morph 等)作为函数调用。
4. 务必确认每个 op 的**前提与失败条件**(退化输入、所需点数等)，并按 fail-closed 处理。
5. 提案中给出**具体的 op 名**，并尽可能附上对应的 worked example / References。
6. 若对实现没有把握，运行对应的 `examples*/`，用 ground-truth 输出加以确认。

## Worked examples(用途 → 所用 op 的实例 = 推荐组合的范例)

_Worked examples 的标题与说明只有日文。本版不假装已翻译，只按 id 列出每个示例、它调用的 op(取自 op 笔记中的示例链接；最多 12 个，其余只给个数)以及运行它的命令。说明见日文版目录 `OP_CATALOG.md`。_

### 2-D 图像/信号/几何(492 例)

**fileio**
- `fileio_scientific_roundtrip` — op: `astro_fits_read`, `astro_fits_write`, `em_mrc_read`, `em_mrc_write`, `nifti_read`, `nifti_write`, `nrrd_read`, `nrrd_write`, `ome_tiff_read`, `ome_tiff_write` `py -3.11 examples/fileio_scientific_roundtrip.py`
- `archive_roundtrip` — op: `archive_create`, `archive_extract`, `archive_list`, `archive_probe` `py -3.11 examples/archive_roundtrip.py`
- `fileio_roundtrip` — op: `e57_read`, `e57_write`, `mesh_read_ply`, `mesh_write_ply`, `points_read_xyz`, `points_write_xyz`, `table_read_csv`, `table_write_csv` `py -3.11 examples/fileio_roundtrip.py`
- `poc_real_file_formats` — op: `aperture_photometry`, `astro_fits_read`, `e57_read`, `ellipse`, `em_mrc_read`, `nifti_read`, `ome_tiff_read`, `otsu`, `star_detect` `py -3.11 examples/poc_real_file_formats.py`

**workflow**
- `mcp_usability` — op: `gaussian`, `ncc_locate` `py -3.11 examples/mcp_usability.py`
- `mcp_task_score` — op: `blob_count`, `count_obj`, `gaussian`, `invert_image`, `m1_measure_pos`, `mean_box_wh`, `otsu`, `select_largest`, `threshold_sub_pix`, `tophat`, `xsitk_maxentropy_thresh` `py -3.11 examples/mcp_task_score.py`
- `typed_results_markdown` — op:(没有 op 笔记链接到此例) `py -3.11 examples/typed_results_markdown.py`
- `inspection_fixture` — op:(没有 op 笔记链接到此例) `py -3.11 examples/inspection_fixture.py`
- `degenerate_inputs` — op: `add_image`, `fft_image`, `gaussian`, `lowpass`, `median_image`, `otsu`, `reg_erode`, `sobel_amp`, `structure_tensor_orientation`, `tophat` `py -3.11 examples/degenerate_inputs.py`
- `genspark_external_review` — op: `abs_image`, `access_channel`, `add_image`, `blend_mode`, `color_lut`, `cv_cc_count`, `gaussian`, `invert`, `median`, `median_image`, `otsu`, `read_wav`(另有 6 个) `py -3.11 examples/genspark_external_review.py`
- `golden_compare` — op:(没有 op 笔记链接到此例) `py -3.11 examples/golden_compare.py`
- `inspection_workflow` — op: `gaussian` `py -3.11 examples/inspection_workflow.py`
- `line_handshake` — op: `otsu` `py -3.11 examples/line_handshake.py`
- `xlsx_report` — op:(没有 op 笔记链接到此例) `py -3.11 examples/xlsx_report.py`
- `typed_results_json` — op: `gaussian`, `otsu` `py -3.11 examples/typed_results_json.py`
- `precision_union_volume` — op:(没有 op 笔记链接到此例) `py -3.11 examples/precision_union_volume.py`
- `quickstart` — op: `bilateral`, `blob_count`, `contours_to_region`, `edges_sub_pix`, `gaussian`, `median`, `otsu`, `remove_small`, `select_contours` `py -3.11 examples/quickstart.py`
- `find_ops_by_meaning` — op: `cv_median`, `cv_nlmeans`, `edges_image`, `gray_opening_rect`, `hx_detect_edge_segments`, `median_image`, `otsu`, `ph_total_variation_flow`, `prewitt_mag`, `remove_noise_region`, `roberts`, `roberts_mag`(另有 15 个) `py -3.11 examples/find_ops_by_meaning.py`
- `aoi_frontend_tour` — op: `flat_field_correct`, `register_image`, `tiled_map` `py -3.11 examples/aoi_frontend_tour.py`

**metrology**
- `fit_ops_from_knowhow` — op: `fit_circle_geometric`, `fit_curve_principal_axis`, `phase_correlation_shift` `py -3.11 examples/fit_ops_from_knowhow.py`
- `poc_aoi_ct_traceability` — op: `filtered_backprojection`, `radon_transform` `py -3.11 examples/poc_aoi_ct_traceability.py`
- `poc_interferometry_step` — op: `axes_frame`, `axes_transform`, `color_bar`, `csi_contrast_map`, `csi_design`, `csi_height_map`, `csi_stack_simulate`, `ellipse`, `gaussian`, `measure_text`, `plot_series`, `text_box`(另有 1 个) `py -3.11 examples/poc_interferometry_step.py`
- `poc_tacsim_marker_shear` — op: `cerruti_kernel`, `cerruti_surface_displacement`, `combined_modulus`, `displace_markers`, `fem_nodes_load`, `fem_vs_halfspace`, `hertz_pressure`, `hertz_sphere`, `hertz_surface_ur`, `hertzian_tangential_inner`, `marker_detect`, `marker_image`(另有 17 个) `py -3.11 examples/poc_tacsim_marker_shear.py`
- `poc_tactile_dipole_torque` — op: `boussinesq_kernel`, `boussinesq_surface_displacement`, `cerruti_kernel`, `combined_modulus`, `dipole_to_torque_fit`, `dipole_torque_resolution`, `displace_markers`, `ellipse_pressure_shifted`, `fem_nodes_load`, `grasp_torque_frame`, `hertz_pressure`, `hertz_pressure_shifted`(另有 24 个) `py -3.11 examples/poc_tactile_dipole_torque.py`
- `poc_granular_heap_repose` — op: `beverloo_fit`, `beverloo_rate`, `container_fill_level`, `container_synth`, `datum_tilt_check`, `difference`, `discharge_synth`, `dispense_mass_from_video`, `heap_mass`, `heap_scene_mjcf`, `heap_spheres_select`, `heap_synth_cone`(另有 12 个) `py -3.11 examples/poc_granular_heap_repose.py`
- `poc_tacscalib_sphere_lut` — op: `calib_pack_load`, `contact_radius_ring`, `field_position_sweep`, `gradient_lut_build`, `gradient_lut_invert`, `invert`, `lights_fit_from_sphere`, `median`, `membrane_predict_rgb`, `normal_error_map`, `normals_to_angles`, `poly_lut_invert`(另有 4 个) `py -3.11 examples/poc_tacscalib_sphere_lut.py`
- `poc_peg_insertion_tactile` — op: `arrow`, `blob_features`, `blob_label`, `contact_radius_fit`, `contact_radius_fit_pixelwise`, `contact_state_from_wrench`, `ellipse`, `equivariance_check`, `friction_from_single_contact`, `hertz_force`, `hertz_sphere`, `membrane_recover`(另有 19 个) `py -3.11 examples/poc_peg_insertion_tactile.py`
- `poc_knife_tactile_toughness` — op: `combined_modulus`, `cutting_episode_synth`, `cutting_scene`, `food_cut_width`, `hertz_sphere`, `knife_load_from_pads`, `membrane_indent_sphere`, `membrane_render_markers`, `membrane_render_rgb`, `pad_context`, `pad_marker_displacement`, `pad_params`(另有 5 个) `py -3.11 examples/poc_knife_tactile_toughness.py`
- `poc_rover_slip_risk_path` — op: `bekker_wheel_sinkage`, `cvar_cost_map`, `fbm_height`, `fbm_params`, `ground_shift_track`, `odometry_slip`, `path_slip_risk`, `risk_aware_path`, `slip_gp_fit`, `slip_predict`, `slip_quantile_fit`, `slope_slip_curve`(另有 4 个) `py -3.11 examples/poc_rover_slip_risk_path.py`
- `poc_braid_homotopy_classes` — op: `braid_class_representatives`, `braid_equivalent`, `braid_from_trajectories`, `braid_reduce`, `dynnikov_act`, `dynnikov_coordinates`, `grid_distances`, `grid_hole_points`, `grid_paths_to_xy`, `homotopy_class_compare`, `homotopy_shortest_paths`, `mapf_cbs`(另有 4 个) `py -3.11 examples/poc_braid_homotopy_classes.py`
- `poc_diabolo_model_and_vision` — op: `arrow`, `diabolo_axis_from_image`, `diabolo_camera`, `diabolo_dynamics_step`, `diabolo_marker_phase`, `diabolo_params`, `diabolo_render`, `diabolo_scene_mjcf`, `diabolo_simulate`, `diabolo_spheroid`, `diabolo_spin_from_markers`, `diabolo_state_sequence`(另有 8 个) `py -3.11 examples/poc_diabolo_model_and_vision.py`
- `poc_tacdome_large_deformation` — op: `contact_patch_radius`, `dome_contact_image`, `hertz_force`, `hertz_small_strain_error`, `hertz_sphere`, `large_deformation_contact`, `large_deformation_inverse`, `largedef_correction`, `largedef_radius_ratio`, `largedef_universal_correction`, `mdr_spring_bed`, `neohookean_cylinder_exact`(另有 1 个) `py -3.11 examples/poc_tacdome_large_deformation.py`
- `poc_peg_symmetry_search` — op: `pegsym_scene_mjcf`, `plane_topview`, `polygon_coverage_image`, `polygon_fit_check`, `polygon_offset`, `polygon_peg`, `polygon_two_point_depth`, `polygon_yaw_read`, `relative_yaw_from_images`, `rotation_search_plan`, `rotation_window`, `search_expected_tries`(另有 3 个) `py -3.11 examples/poc_peg_symmetry_search.py`
- `poc_polish_wipe_measure` — op: `arc`, `band_width_profile`, `coat_image`, `coat_thickness_from_image`, `polish_scene_mjcf`, `preston_coefficient_fit`, `preston_pressure_kernel`, `preston_removal_map`, `preston_track_profile`, `raster_wipe_area`, `removal_depth_from_heights`, `surface_form_remove`(另有 5 个) `py -3.11 examples/poc_polish_wipe_measure.py`
- `poc_powder_scoop_pour` — op: `beverloo_rate`, `difference`, `heap_volume_cone`, `pour_scene_mjcf`, `revolution_volume_side`, `scoop_count`, `scoop_image_limit`, `scoop_scene_mjcf`, `scoop_synth_side`, `scoop_volume_read`, `spheres_render_shaded`, `spheres_to_silhouette`(另有 8 个) `py -3.11 examples/poc_powder_scoop_pour.py`
- `poc_powder_grinding_ae` — op: `ae_band_power`, `ae_read_csv`, `ae_size_correspondence`, `blob_label`, `blob_overlay`, `breakage_first_order_fit`, `comminution_energy`, `comminution_law_fit`, `log`, `particle_image_d50`, `particle_image_synth`, `particle_size_dx`(另有 4 个) `py -3.11 examples/poc_powder_grinding_ae.py`
- `poc_dose_uniformity_from_grinding` — op: `comminution_energy`, `dose_cv_from_sizes`, `dose_cv_lognormal`, `grind_time_for_dose_cv`, `particle_image_d50`, `particle_image_synth`, `particle_size_read`, `particle_size_synth` `py -3.11 examples/poc_dose_uniformity_from_grinding.py`
- `poc_tacsim_elastic_membrane` — op: `combined_modulus`, `contact_radius_fit`, `contact_radius_ring`, `hertz_cylinder`, `hertz_force`, `hertz_pressure`, `hertz_sphere`, `hertz_surface_uz`, `membrane_delta_from_normals`, `membrane_indent_shape`, `membrane_indent_sphere`, `membrane_lights`(另有 4 个) `py -3.11 examples/poc_tacsim_elastic_membrane.py`
- `poc_plateau_venue_lod2` — op: `plateau_lod2_mesh` `py -3.11 examples/poc_plateau_venue_lod2.py`
- `poc_swarm_obstacle_from_flow` — op: `obstacle_fit_doublet`, `potential_flow_cylinder`, `ritter_dam_break`, `sph_dam_break_1d`, `sph_kernel`, `stagnation_from_centerline`, `swarm_field_from_piv`, `swarm_field_from_tracks`, `swarm_render_overhead`, `swarm_simulate`, `text_box`, `velocity_deficit_map` `py -3.11 examples/poc_swarm_obstacle_from_flow.py`
- `poc_pxrd_phase_peel` — op: `axes_frame`, `axes_transform`, `azimuthal_integrate`, `cif_read`, `cubic_index`, `cubic_prototype`, `debye_ring_image`, `detector_calibrate`, `detector_two_theta`, `difference`, `diffraction_peaks`, `grid_lines`(另有 12 个) `py -3.11 examples/poc_pxrd_phase_peel.py`
- `example_inner_diameter_mm` — op: `add_metrology_object_circle_measure`, `apply_metrology_model`, `area_center`, `create_metrology_model`, `gaussian`, `mm_per_px_from_reference`, `otsu`, `pixel_to_world`, `table_px_to_mm` `py -3.11 examples/example_inner_diameter_mm.py`
- `example_scratch_width` — op: `bothat`, `gen_measure_rectangle2`, `lines_gauss`, `measure_pairs`, `mm_per_px_from_reference`, `table_px_to_mm`, `tophat` `py -3.11 examples/example_scratch_width.py`
- `poc_dimensional_inspection` — op: `add_metrology_object_circle_measure`, `add_metrology_object_ellipse_measure`, `add_metrology_object_generic`, `add_metrology_object_line_measure`, `add_metrology_object_rectangle2_measure`, `align_metrology_model`, `apply_metrology_model`, `create_metrology_model`, `ellipse`, `erf`, `fuzzy_measure_pairing`, `gen_measure_arc`(另有 8 个) `py -3.11 examples/poc_dimensional_inspection.py`
- `poc_star_astrometry` — op: `erf`, `gaussian`, `noise_sigma`, `psf_fit`, `star_detect`, `vector_to_similarity` `py -3.11 examples/poc_star_astrometry.py`
- `poc_surface_roughness` — op: `profile_params`, `rms`, `surface_filter`, `surface_form_remove`, `surface_params`, `surface_psd`, `surface_synth_psd` `py -3.11 examples/poc_surface_roughness.py`
- `poc_dic_strain` — op: `axes_frame`, `axes_transform`, `erf`, `piv_cross_correlate`, `plot_series`, `strain_from_displacement`, `text_box`, `ticks` `py -3.11 examples/poc_dic_strain.py`
- `poc_particle_sizing` — op: `blob_features`, `blob_label`, `blob_overlay`, `blob_region`, `blob_select`, `circularity`, `distance_transform` `py -3.11 examples/poc_particle_sizing.py`
- `poc_crack_width` — op: `distance_transform`, `sk_medial`, `skeleton`, `thinning` `py -3.11 examples/poc_crack_width.py`
- `poc_fiber_orientation` — op: `dc_structure_texture`, `smooth_funct_1d_gauss`, `sobel_amp`, `sobel_dir` `py -3.11 examples/poc_fiber_orientation.py`
- `poc_gear_tooth_metrology` — op: `blob_boundaries`, `blob_features`, `blob_label`, `blob_overlay`, `blob_region`, `blob_select_largest`, `gauss_filter`, `polar_trans_image`, `spectrum`, `threshold` `py -3.11 examples/poc_gear_tooth_metrology.py`
- `poc_strain_history` — op: `axes_frame`, `axes_transform`, `data_to_pixel`, `moving_average_window`, `piv_cross_correlate`, `piv_error_stats`, `piv_multipass`, `piv_sample_at_windows`, `piv_synth_pair`, `poly_fit`, `rms`, `text_box`(另有 1 个) `py -3.11 examples/poc_strain_history.py`
- `poc_water_level` — op: `gen_measure_rectangle2`, `mat_svd`, `measure_pos`, `projective_trans_image`, `threshold` `py -3.11 examples/poc_water_level.py`
- `poc_weld_bead_profile` — op: `gen_measure_rectangle2`, `laser_line_center_centroid`, `laser_line_coherent`, `measure_pos`, `median`, `rms`, `smooth_funct_1d_mean`, `triangulation_speckle_limit` `py -3.11 examples/poc_weld_bead_profile.py`
- `poc_wound_area_tracking` — op: `axes_frame`, `axes_transform`, `blob_features`, `blob_label`, `blob_select_largest`, `contour_to_world_plane_xld`, `data_to_pixel`, `gaussian`, `hom_vector_to_proj_hom_mat2d`, `image_to_world_plane`, `log`, `plot_series`(另有 2 个) `py -3.11 examples/poc_wound_area_tracking.py`
- `poc_photoelasticity` — op: `axes_frame`, `axes_transform`, `brazilian_disc_stress`, `mueller_apply`, `mueller_element`, `photoelastic_phase_estimate`, `photoelastic_polarization_images`, `photoelastic_retardation`, `plot_series`, `polariscope_intensity`, `principal_stress`, `retardation_convert`(另有 2 个) `py -3.11 examples/poc_photoelasticity.py`
- `profile_shape_inspection` — op: `profile_camber`, `profile_chord_frame`, `profile_deviation`, `profile_leading_edge_radius`, `profile_perturb`, `profile_synth_naca4`, `profile_thickness`, `profile_trailing_edge_gap`, `rms` `py -3.11 examples/profile_shape_inspection.py`
- `profile_frame_tour` — op: `profile_align`, `profile_chord_frame`, `profile_normalise`, `profile_resample`, `profile_sides`, `profile_synth_naca4` `py -3.11 examples/profile_frame_tour.py`
- `poc_industrial_oct` — op: `glass`, `material_optical_constants`, `oct_ascan`, `oct_bscan`, `oct_bscan_boundaries`, `oct_bscan_flatten`, `oct_bscan_simulate`, `oct_design`, `oct_dispersion_broadening`, `oct_dispersion_compensate`, `oct_dispersion_estimate`, `oct_from_spectra`(另有 3 个) `py -3.11 examples/poc_industrial_oct.py`
- `grating_interferometry` — op: `darkfield_scatter_relation`, `dpc_integrate`, `grating_step_period_estimate`, `grating_stepping_simulate`, `grating_three_image_retrieve`, `talbot_carpet`, `talbot_grating_design`, `talbot_source_visibility` `py -3.11 examples/grating_interferometry.py`
- `poc_grating_interferometry` — op: `angular_spectrum_propagate`, `dpc_integrate`, `grating_step_period_estimate`, `grating_stepping_simulate`, `grating_three_image_retrieve`, `talbot_carpet`, `talbot_grating_design`, `talbot_source_visibility` `py -3.11 examples/poc_grating_interferometry.py`
- `poc_virtual_acceptance_3d` — op: `acceptance_error_budget`, `acceptance_layout`, `acceptance_scan`, `virtual_acceptance_test` `py -3.11 examples/poc_virtual_acceptance_3d.py`
- `poc_moire_alignment` — op: `arrow`, `axes_frame`, `axes_transform`, `data_to_pixel`, `grid_lines`, `legend_box`, `moire_differential_shift`, `moire_magnification`, `moire_mark_read`, `moire_overlay_image`, `moire_phase`, `moire_phase_crlb`(另有 6 个) `py -3.11 examples/poc_moire_alignment.py`
- `poc_telecentric_metrology` — op: `add_metrology_object_circle_measure`, `annotate_scale_bar`, `apply_metrology_model`, `blast_normals`, `chief_ray`, `chief_ray_angle`, `clearcoat_shade`, `create_metrology_model`, `defocus_spot_vs_depth`, `finish_shade`, `gen_measure_rectangle2`, `glass_catalog`(另有 12 个) `py -3.11 examples/poc_telecentric_metrology.py`
- `poc_simcal_telecentric` — op: `chief_ray_angle`, `gaussian`, `simcal_discrepancy`, `simcal_fit`, `simcal_identifiability`, `simcal_model`, `simcal_observe`, `simcal_screen`, `simcal_validate`, `text_box` `py -3.11 examples/poc_simcal_telecentric.py`
- `poc_gw_detector_pseudo_simulation` — op: `bandpass`, `cavity_strain_transfer`, `chirp_mass_from_track`, `chirp_newtonian`, `coincidence_delay`, `fabry_perot_response`, `matched_filter_snr`, `michelson_dc_readout`, `optimal_snr`, `pdh_error_signal`, `psd_welch`, `quantum_noise_budget`(另有 2 个) `py -3.11 examples/poc_gw_detector_pseudo_simulation.py`
- `poc_robust_profile_filter` — op: `robust_gaussian_profile`, `robust_gaussian_surface`, `robust_spline_profile`, `surface_filter` `py -3.11 examples/poc_robust_profile_filter.py`
- `example_robust_profile_filter` — op: `robust_gaussian_profile` `py -3.11 examples/example_robust_profile_filter.py`
- `poc_tem_ctf_thon_rings` — op: `tem_amorphous_film`, `tem_ctf`, `tem_ctf_correct`, `tem_ctf_estimate`, `tem_ctf_profile`, `tem_image_weak_phase`, `tem_multislice`, `tem_power_spectrum`, `tem_projected_potential`, `tem_scherzer`, `tem_wavelength` `py -3.11 examples/poc_tem_ctf_thon_rings.py`
- `poc_sem_wafer_defect_edge_bias` — op: `blob_features`, `blob_label`, `pod_hitmiss_fit`, `seg_boundary_f`, `seg_dice_jaccard`, `sem_image`, `sem_render` `py -3.11 examples/poc_sem_wafer_defect_edge_bias.py`
- `poc_real_sem_metal_layer` — op: `axes_frame`, `axes_transform`, `blob_boundaries`, `blob_distance`, `blob_features`, `blob_label`, `closing_circle`, `data_to_pixel`, `ellipse`, `fill_holes`, `grid_lines`, `intersection`(另有 14 个) `py -3.11 examples/poc_real_sem_metal_layer.py`
- `poc_virtual_sem_kv_cd_bse` — op: `material_electron_properties`, `sem_cd_measure`, `sem_charging_series`, `sem_electron_mc`, `sem_image`, `sem_line_profile`, `sem_se_escape_fraction`, `sem_se_universal_curve`, `sem_yield_curve`, `threshold` `py -3.11 examples/poc_virtual_sem_kv_cd_bse.py`
- `poc_sem_tem_same_particle` — op: `color_bar`, `filtered_backprojection`, `radon_transform`, `scale_bar`, `sem_electron_mc`, `sem_image`, `sem_render`, `tem_image_weak_phase`, `tem_multislice`, `tem_projected_potential`, `tem_wavelength`, `text_box`(另有 1 个) `py -3.11 examples/poc_sem_tem_same_particle.py`
- `poc_metal_grain_size` — op: `bin_threshold`, `blob_features`, `blob_label`, `blob_overlay`, `bothat`, `dyn_threshold`, `gray_bothat`, `hx_close_edges`, `invert_image`, `otsu`, `rgb_to_lab`, `thinning`(另有 1 个) `py -3.11 examples/poc_metal_grain_size.py`
- `poc_screw_thread_metrology` — op: `fit_line_contours`, `gen_measure_rectangle2`, `hx_split_contours`, `measure_pos`, `rms`, `threshold`, `threshold_sub_pix`, `xg_regress_contours` `py -3.11 examples/poc_screw_thread_metrology.py`
- `poc_bone_trabecular_thickness` — op: `blob_distance`, `blob_features`, `blob_label`, `dc_retinex`, `dist_transform`, `gaussian`, `get_region_thickness`, `local_thickness`, `opening_circle`, `otsu`, `sk_area_opening`, `threshold` `py -3.11 examples/poc_bone_trabecular_thickness.py`
- `poc_tree_ring_dendro` — op: `derivate_funct_1d`, `find_peaks`, `gen_measure_rectangle2`, `measure_pos`, `median_rect`, `smooth_funct_1d_gauss` `py -3.11 examples/poc_tree_ring_dendro.py`
- `poc_cad_scan_deviation` — op: `color_bar`, `rms`, `text_box` `py -3.11 examples/poc_cad_scan_deviation.py`
- `poc_structure_4d_deterioration` — op: `axes_frame`, `axes_transform`, `data_to_pixel`, `rmse`, `text_box`, `ticks` `py -3.11 examples/poc_structure_4d_deterioration.py`
- `poc_scan_to_bim_asbuilt` — op:(没有 op 笔记链接到此例) `py -3.11 examples/poc_scan_to_bim_asbuilt.py`
- `poc_pipe_wall_loss` — op: `blob_label`, `blob_select`, `spectrum` `py -3.11 examples/poc_pipe_wall_loss.py`
- `poc_weld_bead_scan_angle` — op: `lines_gauss` `py -3.11 examples/poc_weld_bead_scan_angle.py`
- `poc_laser_line_speckle_floor` — op: `coherent_image`, `laser_line_coherent`, `speckle_field`, `speckle_reduction`, `speckle_statistics`, `triangulation_speckle_limit` `py -3.11 examples/poc_laser_line_speckle_floor.py`
- `poc_light_section_step_weld_floor` — op: `gum_expanded`, `laser_line_center_gauss`, `laser_line_center_steger`, `laser_line_coherent`, `light_plane_calibrate`, `light_section_floor_sweep`, `light_section_height_map`, `light_section_profile`, `light_section_render`, `light_section_rig`, `light_section_scan`, `light_section_speckle_floor`(另有 2 个) `py -3.11 examples/poc_light_section_step_weld_floor.py`
- `poc_interreflection_fringe_error` — op: `form_factors_2d`, `fringe_multipath_phase_error`, `groove_profile`, `high_frequency_patterns`, `micro_phase_decode`, `predict_fringe_phase_error`, `render_transport`, `separate_direct_global`, `tof_multipath_phase`, `tof_transport_depth`, `transport_matrix_radiosity` `py -3.11 examples/poc_interreflection_fringe_error.py`
- `poc_shape_from_polarization` — op: `aolp_to_azimuth`, `brdf_blinn_phong`, `dolp_to_zenith`, `fresnel_dielectric`, `measure_text`, `photometric_stereo_robust`, `polarization_demosaic`, `rms`, `sfp_disambiguate`, `sfp_dolp_model`, `sfp_estimate_index`, `sfp_height`(另有 2 个) `py -3.11 examples/poc_shape_from_polarization.py`
- `poc_phase_measuring_deflectometry` — op: `deflectometry_phase_to_slope`, `deflectometry_render`, `deflectometry_rig`, `deflectometry_screen_pattern`, `deflectometry_sensitivity`, `fresnel_dielectric`, `sfp_height`, `slope_to_curvature`, `text_box` `py -3.11 examples/poc_phase_measuring_deflectometry.py`
- `poc_asbuilt_wall_deviation` — op:(没有 op 笔记链接到此例) `py -3.11 examples/poc_asbuilt_wall_deviation.py`
- `poc_battery_electrode_breathing` — op: `auto_threshold`, `erf`, `gen_measure_rectangle2`, `measure_pos`, `piv_peak_locking`, `rms` `py -3.11 examples/poc_battery_electrode_breathing.py`
- `poc_bump_coplanarity` — op: `auto_threshold`, `blob_features`, `blob_label`, `blob_overlay`, `rms` `py -3.11 examples/poc_bump_coplanarity.py`
- `poc_crack_width_timeseries` — op: `axes_frame`, `axes_transform`, `data_to_pixel`, `erf`, `plot_series`, `text_box`, `ticks` `py -3.11 examples/poc_crack_width_timeseries.py`
- `poc_settlement_significance` — op: `erf` `py -3.11 examples/poc_settlement_significance.py`
- `poc_real_coin_metrology` — op: `blob_count`, `blob_features`, `blob_label`, `canny`, `fill_holes`, `gray_tophat`, `hough_circle_trans`, `otsu`, `sobel_amp` `py -3.11 examples/poc_real_coin_metrology.py`
- `poc_datacenter_thermal_field` — op: `interp_scattered`, `log`, `rmse` `py -3.11 examples/poc_datacenter_thermal_field.py`
- `poc_stockpile_volume` — op: `color_bar`, `dem_hillshade`, `dem_slope`, `dem_viewshed`, `interp_scattered`, `text_box` `py -3.11 examples/poc_stockpile_volume.py`
- `poc_multibeam_bathymetry` — op: `beamform_delay_sum`, `beamform_doa`, `color_bar`, `dem_slope`, `find_peaks`, `intensity`, `interp_scattered`, `peak_subbin`, `text_box` `py -3.11 examples/poc_multibeam_bathymetry.py`
- `poc_livestock_body_volume` — op: `erosion_circle`, `text_box` `py -3.11 examples/poc_livestock_body_volume.py`
- `poc_thermal_radiometry` — op: `beer_lambert_transmittance`, `interp_linear`, `mat_eigh`, `noise_sigma`, `photon_uncertainty`, `poly_fit`, `rms`, `stat_correlation`, `stat_covariance`, `stat_describe`, `stat_histogram` `py -3.11 examples/poc_thermal_radiometry.py`
- `poc_geodetic_height_frames` — op: `datum_tilt_check`, `dem_aspect`, `dem_datum_shift_3param`, `dem_earth_curvature_drop`, `dem_ecef_to_geodetic`, `dem_enu_from_geodetic`, `dem_flow_direction`, `dem_geodetic_from_enu`, `dem_geodetic_to_ecef`, `dem_geoid_height`, `dem_height_frame_convert`, `dem_slope`(另有 3 个) `py -3.11 examples/poc_geodetic_height_frames.py`

**morphing**
- `image_morph` — op: `blend`, `morph`, `morph_sequence` `py -3.11 examples/image_morph.py`

**math**
- `blas_thread_budget` — op: `dc_rpca_lowrank`, `median` `py -3.11 examples/blas_thread_budget.py`
- `perf_pointcloud_descriptors` — op: `gaussian` `py -3.11 examples/perf_pointcloud_descriptors.py`
- `perf_monogenic_metrics` — op: `monogenic_amplitude`, `monogenic_orientation`, `monogenic_phase`, `monogenic_signal` `py -3.11 examples/perf_monogenic_metrics.py`
- `perf_prepared_volume_probe` — op:(没有 op 笔记链接到此例) `py -3.11 examples/perf_prepared_volume_probe.py`
- `perf_polarization_analyze` — op: `polarization_dolp_map`, `polarization_separate`, `polarization_stokes` `py -3.11 examples/perf_polarization_analyze.py`
- `perf_hankel_plan_and_piv_stream` — op: `hankel_transform`, `piv_outlier_mask` `py -3.11 examples/perf_hankel_plan_and_piv_stream.py`
- `geometry_tour` — op: `angle_defect`, `delaunay_triangulate`, `geodesic_heat`, `geodesic_heat_grid`, `mesh_euler_characteristic`, `mesh_torus`, `nurbs_circle`, `nurbs_curve`, `nurbs_revolve` `py -3.11 examples/geometry_tour.py`
- `estimation_tour` — op: `assign_hungarian`, `crlb_gaussian`, `kalman_smooth`, `se3_exp`, `se3_log`, `stat_ttest_welch` `py -3.11 examples/estimation_tour.py`
- `spectral_tour` — op: `esprit_doa`, `hilbert_analytic`, `lomb_scargle`, `music_doa`, `ula_snapshots` `py -3.11 examples/spectral_tour.py`
- `numerics_tour` — op: `chebyshev_coeffs_nd`, `chebyshev_eval_nd`, `chebyshev_nodes`, `erf`, `gauss_quadrature`, `integrate_hamiltonian`, `interp_barycentric`, `low_discrepancy`, `mat_qr` `py -3.11 examples/numerics_tour.py`
- `transforms_tour` — op: `abel_inverse`, `abel_inverse_image`, `abel_revolve`, `abel_transform`, `dct_transform`, `dwt_inverse`, `dwt_transform`, `hankel_image`, `hankel_transform`, `laplace_inverse_talbot`, `tf_freq_response`, `tf_impulse_response`(另有 2 个) `py -3.11 examples/transforms_tour.py`
- `math_metrology` — op: `interp_cubic`, `interp_linear`, `mat_cond`, `mat_eigh`, `mat_lstsq`, `mat_pinv`, `mat_solve`, `mat_svd`, `poly_eval`, `poly_fit`, `poly_roots`, `stat_correlation`(另有 4 个) `py -3.11 examples/math_metrology.py`
- `math_complex` — op: `cplx_argument_principle`, `cplx_cauchy_value`, `cplx_contour_circle`, `cplx_contour_integral`, `cplx_cr_residual`, `cplx_joukowski`, `cplx_laurent_coeffs`, `cplx_mobius`, `cplx_poly_eval`, `cplx_winding_number` `py -3.11 examples/math_complex.py`

**segmentation**
- `poc_threshold_transfer_after_normalization` — op: `axes_transform`, `ptile_threshold`, `sigma_threshold`, `text_box` `py -3.11 examples/poc_threshold_transfer_after_normalization.py`
- `poc_graph_hierarchy_segmentation` — op: `alpha_expansion`, `alpha_tree`, `area_opening_attr`, `graph_cut_binary`, `hierarchical_watershed`, `quasi_flat_zones`, `quickshift`, `seg_boundary_f`, `seg_dice_jaccard`, `seg_object_counts_match`, `seg_score_card`, `seg_under_over_segmentation`(另有 15 个) `py -3.11 examples/poc_graph_hierarchy_segmentation.py`
- `poc_active_contours` — op: `chan_vese_evolve`, `curvature_flow`, `drle_evolve`, `edge_stop_g`, `gvf_field`, `level_set_reinit`, `morph_chan_vese`, `morph_geodesic_ac`, `seg_dice_jaccard`, `seg_score_card`, `sk_chan_vese`, `snake_evolve`(另有 5 个) `py -3.11 examples/poc_active_contours.py`
- `watershed3d_tour` — op: `distance_peaks`, `separate_touching`, `watershed_vol` `py -3.11 examples/watershed3d_tour.py`
- `halcon_segmentation_tour` — op: `check_difference`, `class_2dim_sup`, `class_2dim_unsup`, `class_ndim_norm`, `classify_image_class_lut`, `expand_gray`, `learn_ndim_norm`, `regiongrowing_n`, `watersheds_marker` `py -3.11 examples/halcon_segmentation_tour.py`
- `threshold_family_agreement` — op: `area_frac`, `auto_threshold`, `binary_threshold`, `cv_otsu`, `otsu`, `sk_li`, `sk_niblack`, `sk_otsu`, `sk_sauvola`, `sk_yen`, `xmh_bernsen`, `xsitk_huang_thresh`(另有 3 个) `py -3.11 examples/threshold_family_agreement.py`
- `poc_cell_counting` — op: `circularity`, `distance_transform`, `fill_holes`, `gauss_filter`, `sk_otsu`, `xsk2_h_maxima` `py -3.11 examples/poc_cell_counting.py`
- `poc_dense_bubble_count` — op: `blob_count_interval`, `blob_distance`, `blob_features`, `blob_label`, `blob_seeds`, `blob_split`, `text_box`, `world_blobs_touching` `py -3.11 examples/poc_dense_bubble_count.py`
- `poc_timelapse_growth` — op: `axes_frame`, `axes_transform`, `blob_label`, `plot_series`, `text_box`, `ticks` `py -3.11 examples/poc_timelapse_growth.py`
- `poc_vegetation_cover` — op: `cv_otsu`, `otsu`, `sk_otsu` `py -3.11 examples/poc_vegetation_cover.py`
- `poc_weed_rice_ratio` — op: `cover_ratio_grade`, `fisher_lda_fit`, `fisher_lda_score`, `msa_attribute_agreement`, `plant_color_index`, `snic_superpixels`, `superpixel_color_texture_features` `py -3.11 examples/poc_weed_rice_ratio.py`
- `poc_mri_bias_field` — op: `dc_homomorphic`, `erf`, `overlay_labels`, `xsk2_multiotsu` `py -3.11 examples/poc_mri_bias_field.py`
- `poc_leaf_disease_area` — op: `access_channel`, `blob_features`, `blob_label`, `blob_overlay`, `fill_holes`, `gaussian`, `linear_to_srgb`, `plant_color_index`, `reg_close`, `reg_erode`, `rgb_to_lab`, `select_largest`(另有 4 个) `py -3.11 examples/poc_leaf_disease_area.py`
- `poc_mixed_case_depalletizing` — op: `arc`, `crop_rectangle2`, `ellipse`, `fill_holes`, `median`, `srgb_to_linear`, `watersheds_marker` `py -3.11 examples/poc_mixed_case_depalletizing.py`

**terrain**
- `poc_dem_terrain` — op: `color_bar`, `dem_aspect`, `dem_curvature`, `dem_fill_sinks`, `dem_flow_accumulation`, `dem_hillshade`, `dem_sky_view_factor`, `dem_slope`, `text_box` `py -3.11 examples/poc_dem_terrain.py`
- `dem_geodesy_tour` — op: `dem_cell_size_webmercator`, `dem_earth_curvature_drop`, `dem_ecef_to_geodetic`, `dem_geocentric_grid`, `dem_geodetic_slope`, `dem_geodetic_to_ecef`, `dem_slope` `py -3.11 examples/dem_geodesy_tour.py`
- `dem_terrain_analysis_tour` — op: `dem_flow_accumulation`, `dem_flow_direction`, `dem_horizon_angle`, `dem_roughness`, `dem_stream_network`, `dem_tpi`, `dem_viewshed` `py -3.11 examples/dem_terrain_analysis_tour.py`
- `poc_lidar_terrain_change` — op: `color_bar`, `dem_hillshade`, `dem_slope`, `median`, `text_box` `py -3.11 examples/poc_lidar_terrain_change.py`
- `poc_crop_phenotyping` — op: `dem_slope` `py -3.11 examples/poc_crop_phenotyping.py`

**photometry**
- `poc_astro_photometry` — op: `aperture_photometry`, `drizzle_resample`, `lucky_select`, `median`, `sigma_clip_stack`, `synth_frame_series`, `synth_starfield` `py -3.11 examples/poc_astro_photometry.py`
- `poc_allsky_cloud_cover` — op: `equirect_from_fisheye_pair`, `polar_trans_image` `py -3.11 examples/poc_allsky_cloud_cover.py`
- `poc_nuclei_ploidy` — op: `aperture_photometry`, `blob_features`, `blob_label`, `blob_overlay`, `gaussian`, `median`, `sg_gmm_segment`, `sk_otsu` `py -3.11 examples/poc_nuclei_ploidy.py`
- `poc_solar_limb_darkening` — op: `gauss_filter`, `gaussian`, `gen_measure_rectangle2`, `mat_lstsq`, `measure_pos`, `rms` `py -3.11 examples/poc_solar_limb_darkening.py`
- `poc_exoplanet_transit` — op: `aperture_photometry`, `erf`, `frame_align`, `normalize`, `rms`, `sigma_clip_stack`, `star_detect` `py -3.11 examples/poc_exoplanet_transit.py`
- `poc_real_sky_photometry` — op: `aperture_photometry` `py -3.11 examples/poc_real_sky_photometry.py`

**tomography**
- `poc_ct_fidelity` — op: `backproject_sinogram`, `ellipse_phantom`, `ellipse_sinogram`, `filtered_backprojection`, `projection_angles`, `radon_transform`, `rmse`, `ssim`, `stat_correlation` `py -3.11 examples/poc_ct_fidelity.py`

**diagnostics**
- `poc_bearing_diagnosis` — op: `bearing_defect_frequencies`, `envelope_spectrum`, `spectral_kurtosis`, `spectrum`, `synthesize_bearing_signal` `py -3.11 examples/poc_bearing_diagnosis.py`
- `poc_fabric_defect` — op: `rms`, `thinning` `py -3.11 examples/poc_fabric_defect.py`
- `poc_thermography_ndt` — op: `color_bar` `py -3.11 examples/poc_thermography_ndt.py`
- `poc_prnu_camera_fingerprint` — op: `aug_jpeg_blocks`, `evidence_quantile`, `fingerprint_correlate`, `gauss_image`, `median_image`, `null_distribution`, `sensor_fingerprint`, `sk_nlm`, `sk_tv`, `sk_wavelet`, `xsp_dct_denoise`, `xsp_wiener` `py -3.11 examples/poc_prnu_camera_fingerprint.py`
- `poc_weld_radiograph_porosity` — op: `arc`, `blob_features`, `blob_label`, `blob_overlay`, `blob_select`, `estimate_noise`, `gauss_image`, `gen_measure_rectangle2`, `gray_opening_rect`, `log_image`, `measure_pairs`, `measure_pos`(另有 3 个) `py -3.11 examples/poc_weld_radiograph_porosity.py`
- `poc_solar_el_inspection` — op: `aug_vignette`, `blob_features`, `blob_label`, `blob_select`, `gaussian`, `gray_closing`, `hysteresis_threshold`, `lines_gauss`, `median`, `otsu`, `sk_frangi`, `sk_skeleton`(另有 2 个) `py -3.11 examples/poc_solar_el_inspection.py`
- `poc_solder_fillet_aoi` — op: `access_channel`, `blob_features`, `blob_label`, `blob_select_largest`, `brdf_microfacet`, `illumination_design`, `intensity`, `rgb_to_lab`, `trans_from_rgb` `py -3.11 examples/poc_solder_fillet_aoi.py`
- `poc_machine_condition_fusion` — op: `arrow`, `bearing_defect_frequencies`, `blob_label`, `ellipse`, `mat_pinv`, `rounded_rect`, `spectrum`, `stat_correlation`, `synthesize_bearing_signal`, `text_box` `py -3.11 examples/poc_machine_condition_fusion.py`
- `poc_pv_thermal_survey` — op: `beer_lambert_transmittance`, `blob_features`, `blob_label`, `blob_select`, `color_bar`, `fresnel_dielectric`, `gauss_filter`, `median`, `overlay_mask`, `surface_form_remove`, `zoom_image_factor` `py -3.11 examples/poc_pv_thermal_survey.py`
- `poc_cold_chain_excursion` — op: `integrate_funct_1d`, `quantize`, `sample_funct_1d`, `vol_label_shape_stats`, `vol_mip` `py -3.11 examples/poc_cold_chain_excursion.py`

**ranging**
- `poc_dtof_ranging` — op: `dtof_cube_depth`, `dtof_cube_simulate`, `dtof_depth`, `gaussian`, `median`, `spad_deadtime_apply`, `tcspc_background_subtract`, `tcspc_coates_correct`, `tcspc_simulate` `py -3.11 examples/poc_dtof_ranging.py`
- `poc_leak_localization` — op: `arrow`, `bandpass`, `correlation_score`, `text_box`, `transfer_function` `py -3.11 examples/poc_leak_localization.py`

**depth**
- `poc_lightfield_depth` — op: `color_bar`, `lf_depth_from_focus`, `lf_disparity_to_depth`, `lf_epi`, `lf_epi_slope`, `lf_refocus`, `lf_to_mla` `py -3.11 examples/poc_lightfield_depth.py`
- `poc_focus_stacking` — op: `axes_frame`, `axes_transform`, `csi_height_map`, `defocus_blur`, `dilation_circle`, `gauss_filter`, `laplace`, `mean_image`, `optical_camera`, `plot_series`, `psnr`, `rms`(另有 4 个) `py -3.11 examples/poc_focus_stacking.py`
- `poc_real_stereo_depth` — op:(没有 op 笔记链接到此例) `py -3.11 examples/poc_real_stereo_depth.py`
- `poc_real_stereo_multiscanline` — op: `binocular_disparity_ms`, `binocular_distance_ms`, `create_ncc_model`, `crop_rectangle2`, `ellipse`, `find_ncc_models`, `get_circle_pose`, `points_lepetit`, `reconstruct_surface_stereo` `py -3.11 examples/poc_real_stereo_multiscanline.py`
- `poc_3d_sensor_modalities` — op: `binocular_disparity_ms`, `form_factors_2d`, `groove_profile`, `itof_capture`, `itof_flying_pixel_mask`, `itof_noise_budget`, `itof_phase_amplitude`, `laser_line_center_centroid`, `light_section_speckle_floor`, `photometric_stereo_robust`, `plane_flatness_error`, `sphere_probing_error`(另有 1 个) `py -3.11 examples/poc_3d_sensor_modalities.py`

**optics**
- `poc_compound_eye` — op: `lf_all_in_focus`, `lf_aperture_mask`, `lf_depth_from_focus`, `lf_plenoptic_design`, `lf_subaperture`, `lf_synthesize`, `lf_synthetic_aperture`, `median` `py -3.11 examples/poc_compound_eye.py`
- `poc_fly_vision` — op: `fly_dsi`, `fly_emd_response`, `fly_hex_lattice`, `fly_hex_resample`, `fly_hs_readout`, `fly_lgmd_eta`, `fly_sky_1f`, `fly_tau_from_expansion` `py -3.11 examples/poc_fly_vision.py`
- `polarization_camera_pipeline` — op: `mueller_apply`, `mueller_checks`, `mueller_element`, `mueller_from_intensities`, `mueller_partial_polarizer`, `polarization_demosaic`, `polarization_demosaic_color`, `polarization_dolp_map`, `polarization_stokes`, `polarization_stokes_map`, `stokes_analyze` `py -3.11 examples/polarization_camera_pipeline.py`
- `virtual_machine_vision` — op: `dataset_throughput`, `defocus_blur`, `inspection_dataset`, `light_source`, `optical_camera`, `optscene_defect_mask`, `optscene_depth`, `optscene_instances`, `optscene_mask`, `random_defects`, `render_optscene`, `scene_cylinder`(另有 4 个) `py -3.11 examples/virtual_machine_vision.py`
- `glass_and_mirror_optics` — op: `beer_lambert_transmittance`, `brewster_angle_deg`, `critical_angle_deg`, `fresnel_conductor`, `fresnel_dielectric`, `metal_mirror_rgb`, `metal_optical_constants`, `prism_min_deviation_deg`, `refract_rays`, `slab_transmittance` `py -3.11 examples/glass_and_mirror_optics.py`

**imgmetrics**
- `poc_spc` — op: `spc_capability`, `spc_cusum`, `spc_ewma`, `spc_hotelling_t2`, `spc_mt_distance`, `spc_mt_sn_ratio`, `spc_mt_unit_space`, `spc_xbar_r` `py -3.11 examples/poc_spc.py`
- `poc_mt_hidden_fault` — op: `spc_mt_distance`, `spc_mt_unit_space` `py -3.11 examples/poc_mt_hidden_fault.py`
- `poc_connectome_across_worms` — op: `graph_edge_consensus`, `intersection`, `text_box` `py -3.11 examples/poc_connectome_across_worms.py`
- `poc_physarum_maze` — op: `graph_physarum_path`, `physarum_route` `py -3.11 examples/poc_physarum_maze.py`
- `poc_car_parking` — op: `arrow`, `car_dubins_path`, `car_hybrid_astar`, `car_reeds_shepp_path` `py -3.11 examples/poc_car_parking.py`
- `poc_driving_school` — op: `add_sign`, `ball_detect`, `car_dubins_path`, `car_hybrid_astar`, `course_contains`, `course_crank`, `course_crossing`, `course_intersection`, `course_layout`, `course_loop`, `course_loop_bend`, `course_occupancy`(另有 14 个) `py -3.11 examples/poc_driving_school.py`
- `poc_ttc_rss` — op: `arrow`, `course_layout`, `course_loop`, `crosshair`, `flow_from_depth_motion`, `foe_from_motion`, `label_extent`, `load_asset`, `relative_motion`, `rss_lateral`, `rss_lateral_check`, `rss_longitudinal_check`(另有 13 个) `py -3.11 examples/poc_ttc_rss.py`
- `poc_world_terrain` — op: `add_mesh_object`, `add_sign`, `course_contains`, `course_distance`, `course_layout`, `course_loop`, `crosshair`, `crosswalk_mesh`, `fbm_gradient`, `fbm_height`, `flow_from_depth_motion`, `foe_from_flow`(另有 19 个) `py -3.11 examples/poc_world_terrain.py`
- `poc_ball_bounce` — op: `add_ball`, `apex_sequence`, `ball_detect`, `ball_mesh`, `ball_params`, `ball_set_pose`, `ball_track`, `ball_truth`, `bounce`, `bounce_detect`, `bounce_total_time`, `camera_rig`(另有 24 个) `py -3.11 examples/poc_ball_bounce.py`
- `poc_am_thermal_to_ct` — op: `blob_features`, `blob_label`, `blob_select_largest`, `median`, `mesh_slice_stack`, `seg_boundary_f`, `seg_dice_jaccard`, `signed_surface_distance`, `sk_otsu`, `vol_gaussian` `py -3.11 examples/poc_am_thermal_to_ct.py`
- `poc_segmentation_gauntlet` — op: `blob_distance`, `blob_label`, `local_threshold`, `otsu`, `seg_dice_jaccard`, `seg_score_card`, `sg_watershed_gradient`, `sk_chan_vese`, `sk_felzenszwalb`, `sk_niblack`, `sk_sauvola`, `sk_slic`(另有 9 个) `py -3.11 examples/poc_segmentation_gauntlet.py`
- `poc_driving_pass` — op: `convex_mirror_image`, `convex_mirror_misjudge`, `crest_safe_speed`, `crest_sight_distance`, `ellipse`, `intersection`, `lane_change_follower_decel`, `lane_change_permitted`, `load_asset`, `mirror_aim_normal`, `mirror_road_coverage`, `no_overtaking_zones`(另有 9 个) `py -3.11 examples/poc_driving_pass.py`
- `poc_air_hockey_intercept` — op: `crosshair`, `fivebar_fk`, `fivebar_ik`, `fivebar_link`, `fivebar_reach_interval`, `fivebar_trajectory`, `fivebar_workspace`, `kalman_ca`, `puck_camera`, `puck_crossing_point`, `puck_detect`, `puck_mirror_path`(另有 17 个) `py -3.11 examples/poc_air_hockey_intercept.py`
- `poc_peg_failure_recovery` — op: `chamfer_capture`, `failure_confusion`, `insertion_episode_summary`, `insertion_failure_classify`, `insertion_failure_presets`, `insertion_failure_table`, `insertion_failure_validate`, `insertion_recovery_primitive`, `insertion_signature`, `insertion_stall_detect`, `jamming_diagram`, `jamming_force_check`(另有 11 个) `py -3.11 examples/poc_peg_failure_recovery.py`
- `poc_food_cutting_measure` — op: `cut_depth_from_side`, `cut_force_atkins`, `cut_force_csv_load`, `cut_force_fit`, `cut_surface_roughness`, `cutting_edge_render`, `cutting_episode_synth`, `cutting_face_render`, `cutting_scene`, `cutting_wrist_mjcf`, `food_cut_width`, `force_from_wrist_displacement`(另有 8 个) `py -3.11 examples/poc_food_cutting_measure.py`
- `poc_pegsim_insertion` — op: `camera_world_to_cv`, `chamfer_capture`, `circle_fit_known_radius`, `contact_state_predict`, `jamming_diagram`, `peg_measure_overlay`, `peg_offset_from_rgbd`, `peg_params`, `peg_scene_mjcf`, `peg_synthetic_rgbd`, `two_point_depth`, `wedging_check`(另有 1 个) `py -3.11 examples/poc_pegsim_insertion.py`
- `poc_iqa_fsim_gmsd_vif` — op: `fsim`, `fsim_pair`, `fsimc`, `gmsd`, `gmsd_map`, `phase_congruency_pc`, `rank_kendall_b`, `rank_spearman`, `tf_phase_congruency`, `tid2013_by_distortion`, `tid2013_compare`, `tid2013_evaluate`(另有 5 个) `py -3.11 examples/poc_iqa_fsim_gmsd_vif.py`
- `poc_iqa_tid2013` — op: `luma_limited_u8`, `psnr`, `rank_data`, `rank_kendall_b`, `rank_spearman`, `ssim`, `ssim_map`, `tid2013_by_distortion`, `tid2013_compare`, `tid2013_evaluate`, `tid2013_index`, `tid2013_metric_values`(另有 2 个) `py -3.11 examples/poc_iqa_tid2013.py`
- `poc_driving_commonroad` — op: `boundary`, `cr_checker_result`, `cr_collision`, `cr_drive`, `cr_drive_sweep`, `cr_feasible`, `cr_read`, `cr_route`, `cr_solution_xml`, `cr_synthetic`, `ks_step` `py -3.11 examples/poc_driving_commonroad.py`
- `poc_driving_japan_town` — op: `citygml_synthetic`, `intersection`, `japan_stats`, `japan_world`, `jp_sign_stop_mesh`, `jp_stop_marking_mesh`, `latlon_to_local`, `osm_parse`, `osm_road_graph`, `osm_road_loops`, `osm_road_mask`, `osm_route`(另有 5 个) `py -3.11 examples/poc_driving_japan_town.py`
- `poc_driving_town` — op: `course_crank`, `course_loop_bend`, `course_road`, `course_s_curve`, `crossing_stop_check`, `idm_accel`, `intersection`, `kyosoku_summary`, `long_params`, `long_simulate`, `town_centerline`, `town_chain`(另有 8 个) `py -3.11 examples/poc_driving_town.py`
- `poc_carla_bridge` — op: `camera_pose_to_carla`, `carla_camera_pose`, `carla_depth_decode`, `carla_depth_encode`, `carla_label_map`, `carla_label_unmap`, `carla_labels`, `carla_rotation_angles`, `carla_scene_load`, `carla_scene_save`, `carla_scene_synthetic`, `carla_transform_matrix`(另有 3 个) `py -3.11 examples/poc_carla_bridge.py`
- `poc_agv_fleet` — op: `adg_build`, `adg_execute`, `arrow`, `mapf_cbs`, `mapf_ecbs`, `mapf_joint_astar`, `mapf_prioritized`, `naive_execute`, `plan_conflicts`, `text_box`, `vda5050_check`, `vda5050_order`(另有 1 个) `py -3.11 examples/poc_agv_fleet.py`
- `poc_driving_humanoids` — op: `add_mesh_object`, `crosswalk_mesh`, `humanoid_clip_mesh`, `humanoid_impostors`, `pedestrian_mesh`, `world_camera`, `world_camera_impostors` `py -3.11 examples/poc_driving_humanoids.py`
- `poc_driving_crossing` — op: `add_mesh_object`, `aliased_frequency`, `conflict_zone_intervals`, `crossing_clear_time`, `crossing_gate_state`, `crossing_lamp_signal`, `crossing_stop_check`, `crossing_timing_check`, `crosswalk_mesh`, `crosswalk_overtake_check`, `crosswalk_stopped_vehicle_check`, `ellipse`(另有 15 个) `py -3.11 examples/poc_driving_crossing.py`
- `poc_driving_lateral` — op: `ackermann_steer_angles`, `add_mesh_object`, `bicycle_model_step`, `clothoid_design`, `clothoid_points`, `curvature_speed_plan`, `ellipse`, `friction_circle_usage`, `lateral_offset`, `offtracking_circle`, `pure_pursuit_circle_offset`, `pure_pursuit_curvature`(另有 7 个) `py -3.11 examples/poc_driving_lateral.py`
- `poc_driving_decisions` — op: `add_mesh_object`, `aliased_frequency`, `axes_frame`, `axes_transform`, `bus_departure_yield_check`, `check_sequence_score`, `convex_mirror_fov`, `dilemma_zone`, `doppler_shift`, `doppler_track`, `filled_polygon`, `flash_frequency`(另有 18 个) `py -3.11 examples/poc_driving_decisions.py`
- `poc_driving_traffic` — op: `add_mesh_object`, `axes_frame`, `axes_transform`, `bus_stop_rate`, `driver_style`, `grid_lines`, `idm_accel`, `idm_equilibrium_gap`, `idm_platoon_simulate`, `importance_risk_estimate`, `lateral_wobble`, `long_params`(另有 17 个) `py -3.11 examples/poc_driving_traffic.py`
- `poc_driving_endless_map` — op: `pose_normalize`, `text_box`, `tile_digest`, `tile_edge_crossing`, `tile_height`, `tile_mesh`, `tile_params`, `tile_road_distance`, `tile_roads`, `tile_stream`, `world_camera` `py -3.11 examples/poc_driving_endless_map.py`
- `poc_driving_weather` — op: `ball_detect`, `beta_from_mor`, `course_intersection`, `course_layout`, `course_road`, `env_params`, `env_render`, `fog_beta_from_profile`, `load_asset`, `long_params`, `long_simulate`, `pedestrian_mesh`(另有 13 个) `py -3.11 examples/poc_driving_weather.py`
- `poc_driving_longitudinal` — op: `ball_detect`, `course_intersection`, `course_layout`, `course_road`, `course_slope`, `hill_hold_brake_min`, `hill_start_command`, `hill_start_rollback`, `load_asset`, `log`, `long_energy_residual`, `long_params`(另有 11 个) `py -3.11 examples/poc_driving_longitudinal.py`
- `poc_table_tennis_rally_loop` — op: `aim_velocity`, `ball_params`, `flight_simulate`, `impact_params`, `racket_impact`, `racket_params`, `racket_plan`, `rally_simulate`, `table_params`, `text_box` `py -3.11 examples/poc_table_tennis_rally_loop.py`
- `poc_table_tennis_bounce` — op: `add_ball`, `ball_detect`, `ball_mesh`, `ball_params`, `ball_set_pose`, `bounce`, `bounce_detect`, `crosshair`, `flight_fit`, `flight_ode`, `flight_simulate`, `flight_state_at`(另有 11 个) `py -3.11 examples/poc_table_tennis_bounce.py`
- `poc_table_tennis_spin` — op: `add_ball`, `ball_detect`, `ball_mesh`, `ball_params`, `ball_set_pose`, `ball_track`, `bounce_detect`, `camera_rig`, `fit_spin`, `flight_ode`, `flight_simulate`, `impact_params`(另有 9 个) `py -3.11 examples/poc_table_tennis_spin.py`
- `poc_cd_spin_joint` — op: `add_ball`, `ball_mesh`, `ball_params`, `drag_coefficient_sphere`, `fit_aero`, `fit_spin`, `fit_spin_aero`, `flight_ode`, `magnus_lift_coefficient`, `rms`, `table_params`, `table_world` `py -3.11 examples/poc_cd_spin_joint.py`
- `poc_kendama` — op: `ball_detect`, `camera_perceiver`, `catch_plan_staged`, `catch_success_rate`, `crosshair`, `elliptic_k_agm`, `gs_from_world`, `gs_render`, `gs_render_fn`, `gs_update`, `hole_detect`, `ken_mesh`(另有 22 个) `py -3.11 examples/poc_kendama.py`
- `poc_physarum_transport` — op: `graph_physarum_transport`, `physarum_transport_image`, `wasserstein_1d` `py -3.11 examples/poc_physarum_transport.py`
- `poc_worm_core_persists` — op: `graph_core_persistence`, `graph_kcore`, `graph_rich_club`, `graph_rich_club_curve` `py -3.11 examples/poc_worm_core_persists.py`
- `poc_skeleton_run_length_vs_voi` — op: `seg_variation_of_information`, `tree_from_swc`, `tree_run_length` `py -3.11 examples/poc_skeleton_run_length_vs_voi.py`
- `poc_worm_synapses_vs_neurites` — op: `graph_strength_growth`, `tree_from_swc`, `tree_morphometry` `py -3.11 examples/poc_worm_synapses_vs_neurites.py`
- `poc_em_split_merge_score` — op: `blob_label`, `seg_inject_merge`, `seg_inject_split`, `seg_label_changes`, `seg_membrane_response`, `seg_rand`, `seg_variation_of_information` `py -3.11 examples/poc_em_split_merge_score.py`
- `poc_em_wiring_errors` — op: `seg_synapse_nri`, `seg_synapse_partners`, `seg_variation_of_information`, `seg_wiring_exposure`, `seg_wiring_variation` `py -3.11 examples/poc_em_wiring_errors.py`
- `poc_worm_neurites_grow` — op: `intersection`, `tree_from_swc`, `tree_morphometry`, `tree_sholl` `py -3.11 examples/poc_worm_neurites_grow.py`
- `poc_connectome_across_decades` — op: `graph_edge_consensus`, `intersection` `py -3.11 examples/poc_connectome_across_decades.py`
- `poc_connectome_lr_symmetry` — op: `graph_degree_summary`, `graph_swap_symmetry` `py -3.11 examples/poc_connectome_lr_symmetry.py`
- `poc_swc_tree_truth` — op: `skeleton`, `tree_from_swc`, `tree_morphometry`, `tree_sholl` `py -3.11 examples/poc_swc_tree_truth.py`
- `poc_residue_crt` — op: `crt_displacement`, `harmonic_rotation`, `residue_crt`, `residue_fault_locate`, `residue_integer_crt` `py -3.11 examples/poc_residue_crt.py`
- `poc_text_region_truth` — op: `swt_map`, `text_candidates`, `text_lines` `py -3.11 examples/poc_text_region_truth.py`
- `graphinv_three_phyla` — op: `graph_cycle3`, `graph_degree_preserving_null`, `graph_degree_summary`, `graph_swap_symmetry` `py -3.11 examples/graphinv_three_phyla.py`
- `hidden_ops_tour` — op:(没有 op 笔记链接到此例) `py -3.11 examples/hidden_ops_tour.py`

**analysis**
- `anomaly_eval_metrics` — op: `anomaly_image_auroc`, `anomaly_pixel_auroc`, `anomaly_pro`, `anomaly_region_overlap` `py -3.11 examples/anomaly_eval_metrics.py`
- `doe_plan_tour` — op: `doe_box_behnken`, `doe_central_composite`, `doe_decode`, `doe_fractional_factorial`, `doe_lhs`, `doe_orthogonal_array` `py -3.11 examples/doe_plan_tour.py`
- `multivar_inspection_tour` — op: `doe_central_composite`, `doe_decode`, `doe_encode`, `doe_lhs`, `doe_main_effects`, `doe_orthogonal_array`, `feat_image_vector`, `mv_pca`, `mv_pls`, `rsm_fit` `py -3.11 examples/multivar_inspection_tour.py`
- `sensitivity_tour` — op: `doe_decode`, `doe_lhs`, `doe_morris`, `doe_saltelli`, `mv_confounding`, `mv_residual_pca`, `sens_morris`, `sens_sobol` `py -3.11 examples/sensitivity_tour.py`
- `simcal_tour` — op: `log`, `simcal_fit`, `simcal_model`, `simcal_observe`, `simcal_screen`, `simcal_simulate`, `thin_film_reflectance` `py -3.11 examples/simcal_tour.py`
- `simcal_checks_tour` — op: `doe_lhs`, `log`, `simcal_discrepancy`, `simcal_fit`, `simcal_identifiability`, `simcal_model`, `simcal_observe`, `simcal_report`, `simcal_simulate`, `simcal_validate` `py -3.11 examples/simcal_checks_tour.py`
- `converge_tour` — op: `conv_gci`, `groove_profile`, `iterate_fixed_point`, `iv_richardson_lucy_until`, `mc_photon_slab` `py -3.11 examples/converge_tour.py`
- `poc_microns_brain_wave` — op: `graph_activity_spread`, `graph_degree_preserving_shuffle`, `graph_from_synapses`, `points_activity_video`, `reservoir_states` `py -3.11 examples/poc_microns_brain_wave.py`
- `poc_connectome_motor_bottleneck` — op: `graph_block_shuffle`, `graph_layer_propagate`, `points_activity_video`, `states_layer_dimension`, `states_participation_ratio` `py -3.11 examples/poc_connectome_motor_bottleneck.py`
- `poc_theorems_as_pictures` — op: `circle_packing_apollonian`, `curve_locality`, `ford_circles`, `fractal_dimension`, `graph_degree_table`, `ifs_fractal`, `ifs_similarity_dimension`, `neighbour_index_gaps`, `phyllotaxis_pattern`, `space_filling_curve` `py -3.11 examples/poc_theorems_as_pictures.py`
- `poc_beats_fringes_and_screens` — op: `engrave_lines`, `fraunhofer_pattern`, `grating_wavelengths`, `halftone_moire_period`, `halftone_screen`, `hatch_field`, `mosaic_tiles_render`, `mosaic_tiles_sites`, `stipple_energy`, `wave_fringe_period`, `wave_grating_orders`, `wave_membrane_mode`(另有 3 个) `py -3.11 examples/poc_beats_fringes_and_screens.py`
- `poc_what_a_picture_cannot_check` — op: `dynsys_bifurcation_map`, `dynsys_correlation_dimension`, `dynsys_lyapunov_spectrum`, `dynsys_poincare_section`, `ode_flow_states`, `ode_vector_field_grid`, `piv_divergence`, `piv_flow_magnitude`, `piv_vorticity` `py -3.11 examples/poc_what_a_picture_cannot_check.py`
- `poc_measurement_system_analysis` — op: `axes_frame`, `axes_transform`, `grid_lines`, `gum_expanded`, `gum_monte_carlo`, `gum_propagate`, `gum_standard_uncertainty`, `gum_validate`, `legend_box`, `msa_anova_table`, `msa_attribute_agreement`, `msa_bias_linearity`(另有 5 个) `py -3.11 examples/poc_measurement_system_analysis.py`
- `poc_pod_lighting` — op: `light_source`, `pod_ahat_fit`, `pod_decision_tradeoff`, `pod_false_call`, `pod_from_ahat`, `pod_hitmiss_fit` `py -3.11 examples/poc_pod_lighting.py`
- `fit_circle_xld_bore` — op: `fit_circle_xld`, `threshold_sub_pix` `py -3.11 examples/fit_circle_xld_bore.py`
- `wave_dominant_frequency_grating` — op: `wave_dominant_frequency`, `wave_fringe_period` `py -3.11 examples/wave_dominant_frequency_grating.py`
- `proportion_interval_audit` — op: `proportion_interval`, `trials_for_all_success` `py -3.11 examples/proportion_interval_audit.py`
- `poc_illusions_and_perpetual_drawing` — op: `illusion_muller_lyer`, `perpetual_apollonian`, `perpetual_chaos_game`, `perpetual_elementary_ca`, `perpetual_flow_field`, `perpetual_identities`, `perpetual_ifs_attractor`, `perpetual_loop`, `perpetual_loop_seam`, `perpetual_plasma`, `perpetual_reaction_diffusion`, `perpetual_render`(另有 4 个) `py -3.11 examples/poc_illusions_and_perpetual_drawing.py`
- `poc_calipers_under_illusion` — op: `add_metrology_object_circle_measure`, `add_metrology_object_line_measure`, `apply_metrology_model`, `create_metrology_model`, `fuzzy_measure_pairing`, `gen_measure_rectangle2`, `illusion_cafe_wall`, `illusion_ebbinghaus`, `illusion_ground_truth`, `illusion_muller_lyer`, `illusion_poggendorff`, `illusion_zollner`(另有 3 个) `py -3.11 examples/poc_calipers_under_illusion.py`
- `poc_attention_identities` — op: `attention_apply`, `attention_grouped`, `attention_linear`, `attention_scores`, `attention_softmax`, `attention_tiled`, `attention_weights`, `kv_cache_decode`, `rms_norm`, `rope_rotate` `py -3.11 examples/poc_attention_identities.py`
- `poc_zernike_aberrations` — op: `wavefront_stats` `py -3.11 examples/poc_zernike_aberrations.py`
- `poc_four_dimensions_by_three_d_tools` — op:(没有 op 笔记链接到此例) `py -3.11 examples/poc_four_dimensions_by_three_d_tools.py`
- `poc_vanishing_detail_and_morphing_area` — op: `gauss_filter`, `morph` `py -3.11 examples/poc_vanishing_detail_and_morphing_area.py`
- `poc_gravitational_lens_invariants` — op: `blob_label` `py -3.11 examples/poc_gravitational_lens_invariants.py`
- `poc_endless_zoom_and_turning_solids` — op: `fractal_dimension`, `perpetual_loop_seam` `py -3.11 examples/poc_endless_zoom_and_turning_solids.py`
- `poc_periodic_video_boundary` — op: `moving_average_window`, `perpetual_loop`, `perpetual_loop_seam`, `three_frame_difference` `py -3.11 examples/poc_periodic_video_boundary.py`
- `poc_complex_plane_fields` — op: `boundary`, `cplx_cr_residual`, `cplx_domain_colour`, `cplx_escape_time`, `cplx_newton_basins`, `cplx_plane_grid`, `cplx_rational_field`, `cplx_winding_number`, `joukowski_circulation`, `mandelbrot_interior`, `potential_flow_joukowski` `py -3.11 examples/poc_complex_plane_fields.py`
- `poc_one_stroke_epicycles` — op: `contour_epicycle_chain`, `contour_fourier_complex`, `contour_fourier_truncation_energy`, `contours_to_gcode`, `gcode_time_estimate`, `mst_length`, `stipple_energy`, `stipple_points_from_image`, `stroke_resample_closed`, `stroke_tone_error`, `stroke_tour_closed` `py -3.11 examples/poc_one_stroke_epicycles.py`
- `poc_geodetic_benchmarks_real` — op: `dem_datum_shift_3param`, `dem_ecef_to_geodetic`, `dem_enu_from_geodetic`, `dem_geodetic_from_enu`, `dem_geodetic_to_ecef`, `dem_geoid_height`, `dem_height_frame_convert`, `dem_height_frame_residual` `py -3.11 examples/poc_geodetic_benchmarks_real.py`
- `poc_em_branch_territory` — op: `identity`, `points_activity_video`, `skeleton` `py -3.11 examples/poc_em_branch_territory.py`

**measurement**
- `optics_four_f_processor` — op: `four_f_filter`, `fourier_plane_filter`, `highpass`, `identity`, `lowpass` `py -3.11 examples/optics_four_f_processor.py`
- `scale_law_of_features` — op: `contlength`, `moments_region_2nd`, `moments_region_3rd`, `moments_region_central` `py -3.11 examples/scale_law_of_features.py`
- `shape_factors_closed_form` — op: `area_frac`, `circularity`, `compactness`, `convexity`, `rectangularity`, `roundness` `py -3.11 examples/shape_factors_closed_form.py`
- `walking_ops_tour` — op: `capture_margin`, `com_from_silhouette`, `com_support_margin`, `contact_points`, `detect_obstacles`, `elevation_map`, `elevation_normals`, `elevation_step_edges`, `elevation_traversability`, `fill_gaps`, `foot_slip_metrics`, `foothold_candidates`(另有 12 个) `py -3.11 examples/walking_ops_tour.py`
- `itokawa_gravity_tour` — op: `mesh_slice_contours`, `polyhedron_clip_halfspace`, `polyhedron_gravity` `py -3.11 examples/itokawa_gravity_tour.py`

**color**
- `raw_to_display_isp` — op: `awb_gains`, `brightness_contrast`, `color_correction_matrix`, `hue_saturation`, `lens_shading_correct`, `lens_shading_gain`, `raw_apply_gains`, `raw_black_level`, `raw_dead_pixel_correct`, `raw_dead_pixel_mask`, `raw_demosaic_bilinear` `py -3.11 examples/raw_to_display_isp.py`
- `poc_white_balance` — op: `delta_e_map`, `gauss_filter`, `illuminant_from_dichromatic_planes`, `laplace`, `linear_to_srgb`, `mean_image`, `prewitt_amp`, `roberts`, `sobel_amp`, `spectrum_to_srgb` `py -3.11 examples/poc_white_balance.py`

**separation**
- `poc_polarization_specular` — op: `ellipse`, `fresnel_conductor`, `fresnel_dielectric`, `measure_text`, `polarization_dolp_map`, `polarization_render`, `polarization_separate`, `polarization_stokes`, `rmse` `py -3.11 examples/poc_polarization_specular.py`
- `example_polarization_metal` — op: `brewster_angle_deg`, `fresnel_conductor`, `fresnel_dielectric`, `polarization_dolp_map`, `polarization_render` `py -3.11 examples/example_polarization_metal.py`
- `poc_pigment_unmixing` — op: `delta_e_map`, `linear_to_srgb`, `spectrum_to_srgb` `py -3.11 examples/poc_pigment_unmixing.py`
- `poc_sea_ice_concentration` — op: `blob_features`, `blob_label`, `gauss_filter`, `mat_lstsq` `py -3.11 examples/poc_sea_ice_concentration.py`
- `poc_colocalization_crosstalk` — op: `gauss_image`, `mat_lstsq`, `mat_solve`, `noise_sigma`, `otsu`, `photon_sample`, `reg_erode`, `stat_correlation` `py -3.11 examples/poc_colocalization_crosstalk.py`
- `poc_recycling_sorting` — op: `overlay_labels`, `spectrum` `py -3.11 examples/poc_recycling_sorting.py`
- `poc_real_stain_unmix` — op:(没有 op 笔记链接到此例) `py -3.11 examples/poc_real_stain_unmix.py`

**vibration**
- `poc_motion_magnification` — op: `axes_frame`, `axes_transform`, `band_snr`, `data_to_pixel`, `displacement_series`, `motion_magnify`, `phase_displacement`, `synthesize_translation`, `temporal_band_power`, `temporal_bandpass`, `text_box`, `ticks` `py -3.11 examples/poc_motion_magnification.py`
- `poc_beam_modal_video` — op: `axes_frame`, `axes_transform`, `data_to_pixel`, `envelope`, `phase_displacement`, `piv_cross_correlate`, `temporal_bandpass`, `text_box`, `ticks` `py -3.11 examples/poc_beam_modal_video.py`

**rectification**
- `lens_undistort` — op:(没有 op 笔记链接到此例) `py -3.11 examples/lens_undistort.py`
- `poc_document_scan` — op: `corner_response`, `dc_homomorphic`, `fill_holes`, `gauss_filter`, `get_region_contour`, `gray_tophat`, `illuminate`, `illumination_field`, `image_to_world_plane`, `mean_image`, `opening_circle`, `otsu`(另有 4 个) `py -3.11 examples/poc_document_scan.py`

**calibration**
- `estimate_lens_distortion` — op:(没有 op 笔记链接到此例) `py -3.11 examples/estimate_lens_distortion.py`
- `poc_camera_calibration` — op: `axes_frame`, `axes_transform`, `camera_calibration`, `data_to_pixel`, `ellipse`, `plot_series`, `rms`, `text_box`, `ticks` `py -3.11 examples/poc_camera_calibration.py`
- `machine_vision_tour` — op: `area_center_gray`, `atan2_image`, `binocular_disparity_ms`, `binocular_distance_ms`, `change_radial_distortion_image`, `classify_class_gmm`, `classify_class_knn`, `classify_class_mlp`, `classify_class_svm`, `create_bg_esti`, `create_lexicon`, `create_ncc_model`(另有 36 个) `py -3.11 examples/machine_vision_tour.py`
- `camera_intrinsics_calibration` — op: `camera_calibration` `py -3.11 examples/camera_intrinsics_calibration.py`
- `poc_fly_optomotor_steering` — op: `fly_egomotion_from_flow`, `fly_eye_merge`, `fly_flow_from_directions`, `fly_hex_lattice`, `fly_hex_resample`, `fly_lamina_filter`, `fly_matched_filter`, `fly_onoff_split`, `fly_sky_1f`, `fly_t4t5_field`, `graph_conductance_states`, `graph_from_synapses` `py -3.11 examples/poc_fly_optomotor_steering.py`
- `poc_public_camera_heading_real` — op: `bloom`, `camera_orientation_from_sun_candidates`, `ellipse`, `sun_position` `py -3.11 examples/poc_public_camera_heading_real.py`
- `poc_public_camera_heading` — op: `camera_orientation_from_skyline`, `camera_orientation_from_sun`, `dem_skyline`, `render_skyline_view`, `skyline_extract`, `sun_pixel_position`, `sun_position` `py -3.11 examples/poc_public_camera_heading.py`
- `poc_thermal_drift_metrology` — op: `lockin_thermal_wave`, `polygon_area`, `thermo_optic_coefficient` `py -3.11 examples/poc_thermal_drift_metrology.py`
- `poc_caltab_chain_truth` — op: `camera_calibration_lm`, `create_caltab`, `find_caltab`, `find_marks_and_pose`, `gaussian` `py -3.11 examples/poc_caltab_chain_truth.py`
- `poc_calibration_truth_map` — op: `calibration_error_map`, `calibration_next_pose`, `calibration_uncertainty_map`, `camera_calibration`, `camera_calibration_lm`, `checkerboard_points`, `find_checkerboard_corners`, `sim_checkerboard` `py -3.11 examples/poc_calibration_truth_map.py`
- `poc_real_chessboard_undistort` — op: `camera_calibration_lm`, `change_radial_distortion_image`, `ellipse`, `map_image`, `points_lepetit`, `rectify_to_world_plane` `py -3.11 examples/poc_real_chessboard_undistort.py`

**visualization**
- `interactive_poc_viewer` — op:(没有 op 笔记链接到此例) `py -3.11 examples/interactive_poc_viewer.py`
- `interactive_anim3d_viewer` — op:(没有 op 笔记链接到此例) `py -3.11 examples/interactive_anim3d_viewer.py`
- `anim3d_lens_aberrations` — op: `abbe_number`, `airy_pattern`, `example_system`, `lens_system`, `opd_samples`, `paraxial_trace`, `ray_bundle`, `ray_fan`, `seidel_coefficients`, `spectrum`, `spot_stats`, `text_box`(另有 3 个) `py -3.11 examples/anim3d_lens_aberrations.py`
- `gsplat_product_viewer` — op: `gs_catalog_html`, `gs_from_world`, `gs_viewer_html` `py -3.11 examples/gsplat_product_viewer.py`
- `poc_flybrain_pointcloud` — op: `annotate_figure_grid`, `annotate_scale_bar`, `gaussian`, `text_box` `py -3.11 examples/poc_flybrain_pointcloud.py`
- `poc_malecns_activity_wave` — op: `graph_activation_latency`, `graph_activity_spread`, `graph_degree_preserving_shuffle`, `points_activity_video`, `reservoir_from_graph`, `reservoir_states`, `text_box` `py -3.11 examples/poc_malecns_activity_wave.py`
- `poc_live4d` — op: `blend`, `focus_sweep_height_video`, `focus_sweep_surface_video`, `vol_flow_3d`, `volseq_interpolate_flow`, `volseq_magnify_motion`, `volseq_pathline_orbit`, `volseq_pathline_render`, `volseq_render_orbit`, `volseq_synth_beating`, `volseq_synth_dividing` `py -3.11 examples/poc_live4d.py`
- `poc_video_cube` — op: `intensity`, `video_cube_cut`, `video_cube_orbit`, `video_spacetime_cube`, `video_summary_keyframes`, `video_write_gif`, `vol_render_transfer` `py -3.11 examples/poc_video_cube.py`
- `poc_eye_to_brain` — op: `fly_hex_quantize`, `log`, `points_activity_video`, `text_box` `py -3.11 examples/poc_eye_to_brain.py`

**forensics**
- `poc_forensics_roc` — op: `copy_move_regions`, `error_level_map`, `jpeg_ghost_map`, `jpeg_ghost_quality`, `noise_inconsistency_map` `py -3.11 examples/poc_forensics_roc.py`
- `poc_video_physics_consistency` — op: `aic_from_rss`, `ball_params`, `ballistic_vs_thrust`, `drag_fit`, `evidence_quantile`, `fit_parabola`, `flight_ode`, `label_extent`, `null_distribution`, `text_box`, `thrust_fit`, `thrust_ode`(另有 1 个) `py -3.11 examples/poc_video_physics_consistency.py`
- `poc_fresco_craquelure` — op: `blob_features`, `blob_label`, `blob_overlay`, `cv_blackhat`, `distance_transform`, `erf`, `hx_split_skeleton_region`, `hysteresis_threshold`, `junctions_skeleton`, `otsu`, `pruning`, `r2_endpoints_skeleton`(另有 7 个) `py -3.11 examples/poc_fresco_craquelure.py`

**morphology**
- `poc_bilateral_asymmetry` — op: `rms` `py -3.11 examples/poc_bilateral_asymmetry.py`
- `poc_vessel_network` — op: `blob_features`, `blob_label`, `distance_transform`, `gauss_filter`, `r2_split_skeleton_lines`, `sk_medial`, `skeleton`, `thinning` `py -3.11 examples/poc_vessel_network.py`
- `poc_real_grain_skiz` — op: `hit_or_miss_golay`, `hit_or_miss_seq`, `morph_skiz`, `opening_seg`, `percentile`, `thinning` `py -3.11 examples/poc_real_grain_skiz.py`

**inspection**
- `poc_symmetry_self_reference_inspection` — op: `center_from_symmetric_edges`, `rotational_symmetry`, `symmetry_difference_map`, `symmetry_score` `py -3.11 examples/poc_symmetry_self_reference_inspection.py`
- `poc_print_layer_inspection` — op: `contours_to_gcode`, `gcode_extrusion_volume`, `gcode_layer_image`, `gcode_read`, `gcode_time_estimate`, `gcode_write`, `mesh_slice_contours`, `mesh_slice_stack`, `print_layer_defect_map`, `prism_mesh`, `read_3mf`, `vol_render_transfer`(另有 1 个) `py -3.11 examples/poc_print_layer_inspection.py`
- `poc_em_second_opinion` — op: `holdout_threshold`, `points_activity_video`, `seg_boundary_membrane_gap`, `seg_inject_merge`, `seg_inject_split`, `seg_label_changes`, `seg_membrane_chord_score`, `seg_membrane_response` `py -3.11 examples/poc_em_second_opinion.py`
- `poc_surface_defect_classifiers` — op: `class_2dim_sup`, `class_2dim_unsup`, `class_ndim_norm`, `classify_class_gmm`, `classify_class_knn`, `classify_class_mlp`, `classify_class_svm`, `classify_image_class_lut`, `evaluate_class_gmm`, `learn_ndim_norm`, `train_class_gmm`, `train_class_knn`(另有 2 个) `py -3.11 examples/poc_surface_defect_classifiers.py`
- `poc_equipment_selection_map` — op: `bandpass_spectrum`, `blackbody_spectrum`, `carbon_black_absorption`, `hyperspectral_band_weights`, `ingaas_photodiode_qe`, `material_nir_absorption`, `nir_model_info`, `pod_ahat_fit`, `pod_false_call`, `pod_from_ahat`, `silicon_photodiode_qe`, `spectral_integral` `py -3.11 examples/poc_equipment_selection_map.py`
- `poc_illumination_cone_vs_na` — op: `blast_normals`, `metal_mirror_rgb`, `micro_normals`, `solid_angle_boundaries`, `solid_angle_brightness`, `solid_angle_light`, `solid_angle_render`, `solid_angle_sweep`, `text_box` `py -3.11 examples/poc_illumination_cone_vs_na.py`
- `poc_hdr_glossy_metal_inspection` — op: `camera_response_debevec`, `camera_response_linear`, `camera_response_robertson`, `exposure_fusion_mertens`, `hdr_dynamic_range`, `hdr_exposure_series_simulate`, `hdr_merge`, `hdr_radiance_error` `py -3.11 examples/poc_hdr_glossy_metal_inspection.py`
- `poc_sam_hybrid_bonding_voids` — op: `acoustic_interface_coefficients`, `acoustic_material_table`, `echo_phase_polarity`, `pod_ahat_fit`, `pod_false_call`, `pod_from_ahat`, `pulse_echo_ascan`, `sam_cscan`, `sam_frequency_tradeoff` `py -3.11 examples/poc_sam_hybrid_bonding_voids.py`

**registration**
- `poc_reproducible_icp` — op: `cross_covariance_reproducible`, `fp64_emulation_probe`, `kabsch_reproducible`, `matmul_ozaki`, `matmul_reproducible`, `ozaki_error_bound` `py -3.11 examples/poc_reproducible_icp.py`
- `poc_registration_basin` — op: `axes_frame`, `axes_transform`, `log`, `plot_series`, `text_box`, `ticks` `py -3.11 examples/poc_registration_basin.py`
- `poc_template_tracking` — op: `axes_frame`, `axes_transform`, `ncc_locate`, `plot_series`, `shape_locate`, `text_box`, `ticks` `py -3.11 examples/poc_template_tracking.py`
- `poc_change_detection_misreg` — op: `affine_trans_image`, `erf`, `histogram_match`, `opening_circle`, `piv_cross_correlate`, `piv_outlier_mask`, `procrustes_fit`, `threshold` `py -3.11 examples/poc_change_detection_misreg.py`
- `poc_real_tless_6dof` — op: `axes_frame`, `axes_transform`, `data_to_pixel`, `ellipse`, `grid_lines`, `legend_box`, `plot_series`, `rmse`, `text_box`, `ticks` `py -3.11 examples/poc_real_tless_6dof.py`
- `poc_real_tum_rgbd_slam` — op:(没有 op 笔记链接到此例) `py -3.11 examples/poc_real_tum_rgbd_slam.py`
- `poc_print_registration` — op: `fly_hex_lattice`, `fly_vogel_lattice`, `frame_align`, `halftone_moire_period`, `halftone_screen`, `lattice_moire_peak`, `peak_subbin`, `piv_cross_correlate`, `rms` `py -3.11 examples/poc_print_registration.py`
- `poc_part_locate_features` — op: `features_accuracy_table`, `features_match`, `features_orb`, `features_sift`, `identity`, `ransac_homography` `py -3.11 examples/poc_part_locate_features.py`
- `poc_multimodal_mi_registration` — op: `register_ecc`, `register_image`, `register_mi` `py -3.11 examples/poc_multimodal_mi_registration.py`
- `poc_sheet_deformation_ffd` — op: `median`, `piv_flow_magnitude`, `register_accuracy_map`, `register_ffd`, `registration_to_flow2d` `py -3.11 examples/poc_sheet_deformation_ffd.py`

**decoding**
- `poc_matrix_code_reading` — op: `adaptive_gauss_thresh`, `corner_response`, `illuminate`, `image_to_world_plane`, `otsu`, `sk_sauvola` `py -3.11 examples/poc_matrix_code_reading.py`
- `poc_symbol_package_1d` — op: `barcode_scan_profiles`, `capture_degrade`, `decode_barcode_profile`, `ean_check_digit`, `encode_barcode1d`, `grade_barcode1d`, `grade_barcode_profile`, `read_barcode1d`, `read_symbols_zxing`, `render_symbol`, `symbol_read`, `symbol_read_pod`(另有 1 个) `py -3.11 examples/poc_symbol_package_1d.py`
- `poc_symbol_part_dpm` — op: `capture_degrade`, `dm_decode_modules`, `dm_encode`, `dm_locate`, `dm_read`, `dm_sample`, `grade_datacode2d`, `qr_decode_modules`, `qr_encode`, `qr_locate`, `qr_read`, `qr_sample`(另有 4 个) `py -3.11 examples/poc_symbol_part_dpm.py`
- `poc_symbol_lot_ocr` — op: `capture_degrade`, `ocr_classify`, `ocr_features`, `ocr_font`, `ocr_read_line`, `ocr_read_trials`, `ocr_render_text`, `ocr_score`, `ocr_segment_line`, `ocr_train`, `symbol_read_pod` `py -3.11 examples/poc_symbol_lot_ocr.py`
- `poc_real_typewritten_ocr` — op: `area_center_gray`, `classify_class_gmm`, `classify_class_knn`, `classify_class_mlp`, `classify_class_svm`, `create_lexicon`, `evaluate_class_gmm`, `gray_histo`, `gray_projections`, `lookup_lexicon`, `segment_characters`, `select_characters`(另有 7 个) `py -3.11 examples/poc_real_typewritten_ocr.py`
- `poc_barcode_1d` — op: `decode_barcode`, `gen_measure_rectangle2`, `measure_pos` `py -3.11 examples/poc_barcode_1d.py`

**restoration**
- `poc_camera_shake_deblur` — op: `axes_frame`, `axes_transform`, `plot_series`, `psnr`, `ssim`, `text_box`, `ticks`, `unsharp` `py -3.11 examples/poc_camera_shake_deblur.py`
- `poc_dehazing` — op: `axes_frame`, `axes_transform`, `clahe`, `equalize`, `image_entropy`, `log`, `nice_ticks`, `plot_series`, `psnr`, `rank_image`, `scene_radiance`, `ssim`(另有 2 个) `py -3.11 examples/poc_dehazing.py`
- `poc_real_deblur_honesty` — op: `iv_motion_deblur`, `iv_richardson_lucy`, `iv_unsharp_deblur`, `psnr`, `sk_blur_effect`, `unsharp` `py -3.11 examples/poc_real_deblur_honesty.py`

**upscaling**
- `poc_superresolution_limits` — op: `axes_frame`, `axes_transform`, `data_to_pixel`, `drizzle_resample`, `piv_cross_correlate`, `plot_series`, `psnr`, `ssim`, `text_box`, `ticks`, `unsharp` `py -3.11 examples/poc_superresolution_limits.py`

**geometry**
- `poc_panorama_drift` — op: `axes_frame`, `axes_transform`, `hom_vector_to_proj_hom_mat2d`, `plot_series`, `rms`, `text_box`, `ticks` `py -3.11 examples/poc_panorama_drift.py`
- `poc_xyt_event_surface` — op: `axes_frame`, `axes_transform`, `data_to_pixel`, `text_box`, `ticks` `py -3.11 examples/poc_xyt_event_surface.py`
- `poc_mesh_quality_repair` — op: `fill_holes`, `text_box` `py -3.11 examples/poc_mesh_quality_repair.py`
- `poc_dfm_thickness_overhang` — op: `erfc` `py -3.11 examples/poc_dfm_thickness_overhang.py`
- `poc_symmetry_restoration` — op: `fill_holes`, `rms` `py -3.11 examples/poc_symmetry_restoration.py`
- `poc_print_warpage_risk` — op: `blob_features`, `blob_label`, `text_box` `py -3.11 examples/poc_print_warpage_risk.py`
- `poc_pallet_load_utilization` — op:(没有 op 笔记链接到此例) `py -3.11 examples/poc_pallet_load_utilization.py`

**verification**
- `fix_text_in_image` — op:(没有 op 笔记链接到此例) `py -3.11 examples/fix_text_in_image.py`
- `poc_glyph_typo_detection` — op:(没有 op 笔记链接到此例) `py -3.11 examples/poc_glyph_typo_detection.py`
- `poc_larval_connectome_reservoir` — op: `graph_degree_preserving_shuffle`, `graph_degree_table`, `graph_spectral_radius`, `reservoir_encode`, `reservoir_from_graph`, `ridge_predict`, `ridge_readout` `py -3.11 examples/poc_larval_connectome_reservoir.py`

**imaging_quality**
- `poc_moire_screen` — op: `fft_image`, `gauss_image`, `halftone_moire_period`, `lattice_moire_peak`, `moire_differential_shift`, `moire_magnification`, `moire_mark_read`, `moire_overlay_image`, `moire_phase`, `moire_phase_crlb`, `moire_phase_to_shift`, `moire_talbot_gap` `py -3.11 examples/poc_moire_screen.py`
- `poc_emva1288_sensor` — op: `emva_dark_current`, `emva_defect_pixels`, `emva_dynamic_range`, `emva_exposure_for_snr`, `emva_highpass`, `emva_linearity_error`, `emva_pair_statistics`, `emva_photon_exposure`, `emva_photon_transfer`, `emva_ptc_linearity_check`, `emva_quantum_efficiency`, `emva_sensitivity_threshold`(另有 6 个) `py -3.11 examples/poc_emva1288_sensor.py`
- `poc_emva1288_in_camera_processing` — op: `emva_bspline_regression`, `emva_defect_pixels`, `emva_dynamic_range`, `emva_filter_distortion`, `emva_general_nonuniformity`, `emva_general_relative_qe`, `emva_general_sensitivity`, `emva_highpass`, `emva_linearity_error`, `emva_noise_whiteness`, `emva_pair_statistics`, `emva_photon_transfer`(另有 6 个) `py -3.11 examples/poc_emva1288_in_camera_processing.py`
- `poc_veiling_glare` — op: `airy_pattern`, `create_funct_1d_pairs`, `derivate_funct_1d`, `edge_spread`, `get_y_value_funct_1d`, `invert_funct_1d`, `mtf50`, `mtf_diffraction`, `psf_to_mtf`, `sfr_from_edge`, `veiling_glare_index` `py -3.11 examples/poc_veiling_glare.py`
- `image_quality_metrics` — op: `compare_images`, `compressed_size`, `data_range_of`, `delta_e_2000`, `delta_e_76`, `delta_e_map`, `image_entropy`, `joint_entropy`, `joint_histogram`, `lab_to_rgb`, `measure_with`, `metrics_table`(另有 12 个) `py -3.11 examples/image_quality_metrics.py`
- `image_forensics_audit` — op: `copy_move_regions`, `error_level_map`, `evidence_quantile`, `fingerprint_correlate`, `fingerprint_strength_map`, `hash_distance`, `jpeg_ghost_map`, `jpeg_ghost_quality`, `jpeg_quality_estimate`, `noise_inconsistency_map`, `null_distribution`, `perceptual_hash`(另有 4 个) `py -3.11 examples/image_forensics_audit.py`
- `color_transport` — op: `apply_transport`, `color_transfer`, `delta_e_map`, `gaussian`, `gaussian_transport_map`, `histogram_match`, `poisson_blend`, `sinkhorn`, `sinkhorn_distance`, `sinkhorn_divergence`, `transport_cost`, `transport_plan_1d`(另有 1 个) `py -3.11 examples/color_transport.py`
- `astro_stacking` — op: `align_frames`, `aperture_photometry`, `cosmic_ray_reject`, `cosmic_ray_reject_stack`, `drizzle_resample`, `frame_align`, `frame_quality`, `lucky_select`, `median`, `noise_sigma`, `psf_fit`, `sigma_clip_stack`(另有 3 个) `py -3.11 examples/astro_stacking.py`
- `motion_magnification` — op: `band_snr`, `complex_steerable_decompose`, `complex_steerable_reconstruct`, `displacement_series`, `motion_magnify`, `phase_displacement`, `synthesize_translation`, `temporal_band_power`, `temporal_bandpass` `py -3.11 examples/motion_magnification.py`
- `video_streaming` — op: `background_subtraction_window`, `deflicker`, `exponential_background`, `exponential_foreground`, `frame_difference_causal`, `gaussian`, `motion_energy_image`, `motion_history_image`, `moving_average_window`, `optical_flow_magnitude_stream`, `running_gaussian_background`, `running_gaussian_foreground`(另有 6 个) `py -3.11 examples/video_streaming.py`
- `quaternion_monogenic` — op: `displacement_series`, `iqft2`, `monogenic_amplitude`, `monogenic_orientation`, `monogenic_phase`, `monogenic_signal`, `motion_magnify`, `phase_displacement`, `qft2`, `quat_color_filter`, `quat_color_rotate`, `quat_conjugate_image`(另有 11 个) `py -3.11 examples/quaternion_monogenic.py`
- `poc_zebra_stripes_fly_eye` — op: `coherence`, `fly_emd_response`, `fly_expansion_readout`, `fly_flow_from_directions`, `fly_hex_lattice`, `fly_t4t5_field`, `fly_tau_from_expansion`, `fly_view_plane_texture`, `fly_vogel_lattice`, `lattice_moire_peak`, `sampling_alias_distance`, `text_box`(另有 1 个) `py -3.11 examples/poc_zebra_stripes_fly_eye.py`
- `poc_colormap_readability` — op: `delta_e_map`, `log`, `percentile`, `rgb_to_lab` `py -3.11 examples/poc_colormap_readability.py`

**flow**
- `poc_particle_tracking` — op: `axes_frame`, `axes_transform`, `blob_features`, `blob_label`, `plot_series`, `text_box`, `ticks` `py -3.11 examples/poc_particle_tracking.py`
- `poc_traffic_counting` — op: `axes_frame`, `blob_features`, `blob_label`, `data_to_pixel`, `text_box`, `threshold`, `ticks` `py -3.11 examples/poc_traffic_counting.py`
- `piv_flow_from_particles` — op: `median`, `normalize`, `piv_cross_correlate`, `piv_divergence`, `piv_error_stats`, `piv_multipass`, `piv_outlier_mask`, `piv_replace_outliers`, `piv_sample_at_windows`, `piv_synth_pair`, `piv_to_velocity`, `piv_vorticity` `py -3.11 examples/piv_flow_from_particles.py`
- `piv_field_analysis_tour` — op: `correlation_quality`, `piv_cross_correlate`, `piv_deform_pass`, `piv_ensemble_correlate`, `piv_error_stats`, `piv_flow_magnitude`, `piv_flow_to_rgbimage`, `piv_line_integral_convolution`, `piv_multipass`, `piv_peak_locking`, `piv_q_criterion`, `piv_quiver`(另有 11 个) `py -3.11 examples/piv_field_analysis_tour.py`
- `poc_river_surface_velocity` — op: `arrow`, `axes_frame`, `axes_transform`, `highpass_image`, `median`, `piv_cross_correlate`, `piv_ensemble_correlate`, `piv_error_stats`, `piv_outlier_mask`, `piv_replace_outliers`, `piv_sample_at_windows`, `piv_to_velocity`(另有 5 个) `py -3.11 examples/poc_river_surface_velocity.py`
- `poc_warehouse_flow` — op: `vol_dilate`, `vol_erode`, `vol_opening_ball` `py -3.11 examples/poc_warehouse_flow.py`

**shape_descriptors**
- `contour_fourier` — op: `descriptor_distance`, `elliptic_fourier`, `fourier_smooth`, `reconstruct` `py -3.11 examples/contour_fourier.py`
- `shape2d_morph_descriptor_tour` — op: `add_frame_corners`, `descriptor_distance`, `elliptic_fourier`, `from_xld`, `invariants`, `warp_piecewise_affine`, `warp_tps_image` `py -3.11 examples/shape2d_morph_descriptor_tour.py`
- `poc_rotation_invariance_audit` — op: `annotate_outline`, `annotate_table`, `blob_features`, `blob_label`, `circularity`, `eccentricity`, `moments_region_2nd_invar`, `moments_region_central_invar`, `text_box` `py -3.11 examples/poc_rotation_invariance_audit.py`
- `poc_real_texture_invariance` — op: `cooc_feature_matrix`, `sk_lbp` `py -3.11 examples/poc_real_texture_invariance.py`

**drawing**
- `draw_annotate` — op:(没有 op 笔记链接到此例) `py -3.11 examples/draw_annotate.py`
- `drawlist_deferred` — op: `text_box` `py -3.11 examples/drawlist_deferred.py`
- `annotate_gallery` — op: `arc`, `arrow`, `axes_frame`, `axes_transform`, `color_bar`, `compare_frame`, `crosshair`, `data_to_pixel`, `ellipse`, `filled_polygon`, `grid_lines`, `label_points`(另有 13 个) `py -3.11 examples/annotate_gallery.py`
- `paper_figure` — op: `annotate_angle`, `annotate_angle_layout`, `annotate_colorbar`, `annotate_dimension`, `annotate_dimension_layout`, `annotate_figure_grid`, `annotate_figure_grid_layout`, `annotate_inset`, `annotate_inset_layout`, `annotate_leader`, `annotate_leader_layout`, `annotate_legend`(另有 7 个) `py -3.11 examples/paper_figure.py`
- `gfx2d_scene` — op: `alpha_composite`, `alpha_composite_premul`, `blend_mode`, `bloom`, `chromatic_aberration`, `color_grade`, `color_lut`, `difference`, `dither`, `film_grain`, `layer_stack`, `light_mask`(另有 21 个) `py -3.11 examples/gfx2d_scene.py`
- `annotate_paper_tour` — op: `annotate_invert`, `annotate_invert_path`, `annotate_invert_visibility`, `annotate_panel_label`, `annotate_table`, `annotate_table_layout`, `annotate_text_path`, `annotate_text_path_layout`, `axes_frame`, `axes_transform`, `measure_text`, `panel_grid`(另有 2 个) `py -3.11 examples/annotate_paper_tour.py`

**signal_processing**
- `signal_filter` — op: `highpass`, `lowpass`, `poly_eval`, `poly_fit` `py -3.11 examples/signal_filter.py`
- `signal_funct1d` — op: `abs_funct_1d`, `create_funct_1d_array`, `derivate_funct_1d`, `distance_funct_1d`, `funct_1d_to_pairs`, `get_pair_funct_1d`, `get_y_value_funct_1d`, `integrate_funct_1d`, `local_min_max_funct_1d`, `match_funct_1d_trans`, `num_points_funct_1d`, `sample_funct_1d`(另有 6 个) `py -3.11 examples/signal_funct1d.py`
- `acoustic_condition_monitoring` — op: `angular_resample`, `apply_weighting`, `bearing_defect_frequencies`, `cepstrum`, `coherence`, `envelope_spectrum`, `equivalent_level`, `gcc_delay`, `istft`, `octave_bands`, `octave_spectrum`, `order_spectrum`(另有 10 个) `py -3.11 examples/acoustic_condition_monitoring.py`
- `poc_rail_corrugation` — op: `octave_bands`, `octave_spectrum` `py -3.11 examples/poc_rail_corrugation.py`
- `poc_web_roll_periodicity` — op: `cepstrum`, `find_peaks`, `local_min_max_funct_1d`, `median`, `peak_subbin`, `point_spectrum`, `smooth_funct_1d_gauss`, `spectrum` `py -3.11 examples/poc_web_roll_periodicity.py`

**interpolation**
- `spline_curve` — op:(没有 op 笔记链接到此例) `py -3.11 examples/spline_curve.py`

**family_coverage**
- `gallery2d_smoothing_rank` — op: `add_noise_distribution`, `add_noise_white`, `anisotropic_diffusion`, `bilateral`, `bilateral_filter`, `binomial_filter`, `coherence_enhancing_diff`, `cv_bilateral`, `cv_box`, `cv_gaussian`, `cv_median`, `cv_nlmeans`(另有 76 个) `py -3.11 examples/gallery2d_smoothing_rank.py`
- `gallery2d_edges` — op: `corner_response`, `cv_corner_harris`, `cv_laplacian`, `cv_min_eigen`, `cv_precorner`, `cv_scharr`, `derivate_gauss`, `diff_of_gauss`, `dog`, `dots_image`, `edge_transition_width`, `edges_color`(另有 47 个) `py -3.11 examples/gallery2d_edges.py`
- `gallery2d_morphology` — op: `bothat`, `cv_blackhat`, `cv_close`, `cv_dilate`, `cv_erode`, `cv_gradient`, `cv_open`, `cv_tophat`, `f2_gray_inside`, `f2_gray_skeleton`, `gclose`, `gdilate`(另有 24 个) `py -3.11 examples/gallery2d_morphology.py`
- `gallery2d_region` — op: `boundary`, `closest_point_transform`, `closing_circle`, `closing_golay`, `closing_rectangle1`, `convex_fill`, `cv_dist`, `dilation_circle`, `dilation_golay`, `dilation_rectangle1`, `dilation_seq`, `dist_transform`(另有 69 个) `py -3.11 examples/gallery2d_region.py`
- `gallery2d_segmentation` — op: `adaptive_gauss_thresh`, `auto_threshold`, `bin_threshold`, `binary_threshold`, `canny`, `cv_adaptive_gauss`, `cv_adaptive_mean`, `cv_canny`, `cv_otsu`, `dual_threshold`, `dyn_threshold`, `edges_image`(另有 50 个) `py -3.11 examples/gallery2d_segmentation.py`
- `gallery2d_features` — op: `area_center`, `area_center_xld`, `area_frac`, `area_holes`, `blob_count`, `circularity`, `circularity_xld`, `classify_shape`, `compactness`, `compactness_xld`, `connect_and_holes`, `contlength`(另有 65 个) `py -3.11 examples/gallery2d_features.py`
- `gallery2d_geometry` — op: `affine_trans_image`, `affine_trans_image_size`, `affine_trans_region`, `affine_warp`, `deform_ffd`, `deform_mls`, `deform_tps`, `deskew`, `it_add_image_border`, `it_change_format`, `it_crop_part`, `it_crop_rectangle1`(另有 39 个) `py -3.11 examples/gallery2d_geometry.py`
- `gallery2d_gray_arith` — op: `abs_image`, `acos_image`, `asin_image`, `atan_image`, `banding_map`, `bit_not`, `clahe`, `companding_mu_law`, `cos_image`, `cv_clahe`, `cv_trunc`, `dither_floyd_steinberg`(另有 50 个) `py -3.11 examples/gallery2d_gray_arith.py`
- `gallery2d_contour_measure` — op: `affine_trans_contour_xld`, `affine_trans_polygon_xld`, `close_contours_xld`, `contour_point_num_xld`, `contours_to_region`, `edges_color_sub_pix`, `edges_sub_pix`, `fit_line_contours`, `gen_contour_region_xld`, `gen_region_contour_xld`, `gen_region_polygon_xld`, `lines_color`(另有 20 个) `py -3.11 examples/gallery2d_contour_measure.py`
- `gallery2d_texture_freq` — op: `bandpass_image`, `bootstrap_std_error`, `cooc_feature_matrix`, `dc_homomorphic`, `dc_local_contrast_norm`, `dc_retinex`, `dc_rpca_lowrank`, `dc_rpca_sparse`, `dc_structure_texture`, `dc_texture_residual`, `deviation_image`, `entropy_image`(另有 42 个) `py -3.11 examples/gallery2d_texture_freq.py`
- `gallery2d_color_artistic` — op: `access_channel`, `aug_barrel`, `aug_chromatic`, `aug_cutout`, `aug_fixed_pattern`, `aug_jpeg_blocks`, `aug_motion_blur`, `aug_read_noise`, `aug_rolling_shutter`, `aug_shot_noise`, `aug_vignette`, `cfa_to_rgb`(另有 23 个) `py -3.11 examples/gallery2d_color_artistic.py`
- `gallery2d_halcon_ext` — op: `hx_add_noise_contour`, `hx_char_threshold`, `hx_clip_contours`, `hx_clip_end_points`, `hx_clip_region_rel`, `hx_close_edges`, `hx_close_edges_length`, `hx_closing`, `hx_cooc_feature`, `hx_crop_contours`, `hx_detect_edge_segments`, `hx_dilation1`(另有 69 个) `py -3.11 examples/gallery2d_halcon_ext.py`
- `gallery2d_physics_alife_3d` — op: `alife_curvature_flow`, `alife_cyclic_ca`, `alife_dla`, `alife_gray_scott`, `alife_langton_ant`, `alife_lenia`, `alife_life_step`, `alife_perona_malik`, `alife_reaction_bz`, `alife_sandpile`, `alife_turing`, `alife_wolfram1d`(另有 28 个) `py -3.11 examples/gallery2d_physics_alife_3d.py`
- `gallery2d_bridge` — op: `contour_to_img`, `counts_to_img`, `feature_to_img`, `img_to_beatcube`, `img_to_cimage`, `img_to_counts`, `img_to_keypoints`, `img_to_lightfield`, `img_to_matrix`, `img_to_monogenic`, `img_to_points`, `img_to_projection_profile`(另有 8 个) `py -3.11 examples/gallery2d_bridge.py`
- `gallery_drive_ballistics` — op: `ball_params`, `bounce`, `cup_catch_check`, `drag_coefficient_sphere`, `fit_aero`, `fit_bounce`, `flight_ode`, `impact_params`, `incline_slip_angle`, `magnus_lift_coefficient`, `mu_from_stop_distance`, `pendulum_period`(另有 7 个) `py -3.11 examples/gallery_drive_ballistics.py`
- `gallery_drive_kendama_racket` — op: `aim_velocity`, `ball_params`, `catch_plan_ballistic`, `flight_ode`, `flight_vacuum`, `impact_params`, `kendama_catch_check`, `kendama_params`, `noisy_perceiver`, `parabola_fit_g`, `racket_hit_check`, `racket_move`(另有 5 个) `py -3.11 examples/gallery_drive_kendama_racket.py`
- `gallery_drive_lateral_env` — op: `curve_speed_limit`, `design_min_radius`, `fresnel_integrals`, `julian_day`, `koschmieder`, `mor_from_beta`, `rss_lateral`, `rss_params`, `rss_worst_case_gap_lateral`, `skill_test_score`, `skill_test_thresholds`, `stanley_steer`(另有 4 个) `py -3.11 examples/gallery_drive_lateral_env.py`
- `gallery_drive_soil_tactile` — op: `bekker_pressure`, `cone_profile_px`, `hertz_surface_ur`, `largedef_c1_coefficient`, `marker_match_grow`, `membrane_markers`, `mindlin_fit_vector`, `mindlin_model`, `pad_context`, `pad_marker_displacement`, `pad_params`, `slip_cvar`(另有 4 个) `py -3.11 examples/gallery_drive_soil_tactile.py`
- `gallery_drive_peg` — op: `contact_candidates`, `coverage_edge_points`, `cylinder_fit_known_radius`, `hole_centre_from_rgbd`, `insertion_grid_summary`, `pad_shear_asymmetry`, `peg_params`, `peg_synthetic_rgbd`, `peg_tip_from_rgbd`, `two_point_depth`, `whitney_wrench`, `wrist_deflection_from_rgbd` `py -3.11 examples/gallery_drive_peg.py`
- `gallery_drive_carla_bridge` — op: `carla_intrinsics`, `carla_pose_to_world`, `carla_rotation_matrix`, `carla_scene_check`, `carla_scene_render`, `carla_scene_synthetic`, `carla_scene_world`, `carla_xy_yaw`, `intrinsics_to_carla`, `intrinsics_to_fullseye`, `lead_from_depth`, `lead_truth_depth`(另有 1 个) `py -3.11 examples/gallery_drive_carla_bridge.py`
- `gallery_drive_japan_roads` — op: `add_signal_jp`, `course_road`, `jp_crossbuck_mesh`, `jp_mirror_mesh`, `jp_pole_mesh`, `jp_stop_marking_length`, `plate_mesh_from_image`, `sign_image`, `sign_mesh`, `sign_params`, `signal_jp_mesh`, `world_build` `py -3.11 examples/gallery_drive_japan_roads.py`
- `gallery_drive_world_io` — op: `events_to_frames`, `global_to_tile`, `gs_read_file`, `read_bvh`, `read_events`, `sigmoid`, `tile_hash`, `tile_uniform` `py -3.11 examples/gallery_drive_world_io.py`
- `gallery_drive_world_objects` — op: `add_ken`, `add_mesh_object`, `add_string`, `course_road`, `humanoid_clip_mesh`, `ken_mesh`, `ken_set_pose`, `ken_truth`, `kendama_params`, `kendama_rig`, `kendama_world`, `pedestrian_mesh`(另有 4 个) `py -3.11 examples/gallery_drive_world_objects.py`
- `gallery_drive_city_terrain` — op: `building_prisms`, `buildings_in_box`, `citygml_synthetic`, `course_road`, `grid_distances`, `plan_cost`, `plateau_parse`, `ray_box_ranges`, `terrain_mesh`, `terrain_params`, `triangulate_polygon` `py -3.11 examples/gallery_drive_city_terrain.py`
- `gallery_drive_mirrors_crowds` — op: `hill_meeting_yield`, `mirror_image_side`, `mirror_reflection_matrix`, `social_force_step` `py -3.11 examples/gallery_drive_mirrors_crowds.py`
- `gallery_nary_image_algebra` — op: `abs_diff_image`, `add_image`, `bit_and`, `bit_or`, `convol_image`, `difference`, `div_image`, `identity`, `intersection`, `max_image`, `min_image`, `mult_image`(另有 6 个) `py -3.11 examples/gallery_nary_image_algebra.py`
- `gallery_spectrum_signal_bridge` — op: `log`, `negate_funct_1d`, `tb_cx_apply_transfer_function`, `tb_cx_ifft`, `tb_cx_imag`, `tb_cx_log_magnitude`, `tb_cx_magnitude`, `tb_cx_phase`, `tb_cx_real`, `zero_crossing_rate` `py -3.11 examples/gallery_spectrum_signal_bridge.py`
- `gallery_mesh_seg_sun_gains` — op: `icosphere`, `rgb_apply_gains`, `seg_contingency`, `sun_bloom_fit` `py -3.11 examples/gallery_mesh_seg_sun_gains.py`
- `gallery_math_stats_linalg` — op: `hist_distance`, `mat_cholesky`, `mat_eig`, `mat_expm`, `mat_logm`, `mat_lu`, `stat_chi2_gof`, `stat_ks_test`, `stat_ttest_paired` `py -3.11 examples/gallery_math_stats_linalg.py`
- `gallery_math_numerics_filters` — op: `bessel`, `gauss_cubature`, `n_sources_mdl`, `nurbs_surface`, `tf_bilinear`, `wavelet_filters` `py -3.11 examples/gallery_math_numerics_filters.py`
- `gallery_oned_audio_funct` — op: `compose_funct_1d`, `negate_funct_1d`, `read_audio`, `signal_features`, `transform_funct_1d`, `zero_crossing_rate` `py -3.11 examples/gallery_oned_audio_funct.py`
- `gallery_seg_measures` — op: `chan_vese_energy`, `lens_area`, `max_tree`, `seg_confusion_table`, `seg_hausdorff`, `seg_mean_surface_distance`, `voronoi_cells` `py -3.11 examples/gallery_seg_measures.py`
- `gallery_conngraph_closed_forms` — op: `graph_adjacency_image`, `graph_betweenness`, `graph_binarize`, `graph_clustering_coefficient`, `graph_components`, `graph_edges_as_lines`, `graph_laplacian_spectrum`, `graph_layout_spectral`, `graph_modularity`, `graph_motif_count` `py -3.11 examples/gallery_conngraph_closed_forms.py`
- `gallery_illusion_invariants` — op: `illusion_checker_shadow`, `illusion_fraser_spiral`, `illusion_hermann_grid`, `illusion_kanizsa`, `illusion_ponzo`, `illusion_scintillating_grid`, `illusion_simultaneous_contrast`, `perpetual_harmonograph`, `perpetual_langtons_ant` `py -3.11 examples/gallery_illusion_invariants.py`
- `gallery_live4d_volseq_truth` — op: `video_interpolate_flow`, `volseq_cut_video`, `volseq_mip_video`, `volseq_speed` `py -3.11 examples/gallery_live4d_volseq_truth.py`
- `gallery_openvx_spec_values` — op: `vx_histogram`, `vx_magnitude`, `vx_nonlinear_filter`, `vx_nonmax_suppression`, `vx_phase`, `vx_remap`, `vx_sobel3x3`, `vx_table_lookup`, `vx_warp_affine`, `vx_warp_perspective` `py -3.11 examples/gallery_openvx_spec_values.py`

**optics_sensing**
- `optics_imaging` — op: `abcd_matrix`, `abcd_trace`, `airy_pattern`, `angular_spectrum_propagate`, `defocus_from_shift`, `depth_of_field`, `fraunhofer_pattern`, `gaussian_beam`, `jones_apply`, `jones_element`, `mtf_diffraction`, `mueller_apply`(另有 9 个) `py -3.11 examples/optics_imaging.py`
- `scintillator_sensor_tour` — op: `scintillator_sensor_qe`, `silicon_photodiode_qe` `py -3.11 examples/scintillator_sensor_tour.py`
- `optical_design_metrics` — op: `encircled_energy`, `energy_radii`, `ensquared_energy`, `lens_file_read`, `lens_system`, `mtf_tangential_sagittal`, `paraxial_trace`, `psf_from_opd`, `ray_aiming`, `set_vignetting`, `spot_stats`, `through_focus_mtf`(另有 1 个) `py -3.11 examples/optical_design_metrics.py`
- `lens_design_demo` — op: `example_system`, `glass`, `lens_system`, `opd_map`, `paraxial_trace`, `ray_fan`, `rms`, `seidel_coefficients`, `spot_diagram`, `spot_stats`, `thick_lens`, `tolerance_analysis`(另有 1 个) `py -3.11 examples/lens_design_demo.py`
- `lens_optimize_demo` — op: `bend_singlet`, `chief_ray`, `chromatic_shift`, `example_system`, `glass`, `glass_catalog`, `lens_system`, `merit_function`, `optimize_lens`, `sellmeier`, `spot_stats` `py -3.11 examples/lens_optimize_demo.py`
- `illumination_design_demo` — op: `defect_contrast`, `illumination_design`, `illumination_uniformity`, `irradiance_map`, `light_source`, `lighting_sweep` `py -3.11 examples/illumination_design_demo.py`
- `lens_calibration_loop_demo` — op: `calibration_views`, `camera_calibration`, `example_system`, `lens_system` `py -3.11 examples/lens_calibration_loop_demo.py`
- `lens_defect_dataset_demo` — op: `defect_dataset`, `distortion_map`, `example_system`, `lens_system`, `paraxial_trace`, `psf_from_opd`, `render_through_lens` `py -3.11 examples/lens_defect_dataset_demo.py`
- `lightfield_depth` — op: `depth_of_field`, `lf_all_in_focus`, `lf_aperture_mask`, `lf_center_view`, `lf_depth_from_focus`, `lf_disparity_to_depth`, `lf_epi`, `lf_epi_slope`, `lf_focal_stack`, `lf_from_mla`, `lf_plenoptic_design`, `lf_refocus`(另有 9 个) `py -3.11 examples/lightfield_depth.py`
- `photon_timeresolved` — op: `anscombe_inverse`, `anscombe_transform`, `dtof_cube_depth`, `dtof_cube_simulate`, `dtof_depth`, `gaussian`, `lifetime_fit`, `lifetime_phasor`, `median`, `photon_sample`, `photon_statistics`, `photon_uncertainty`(另有 7 个) `py -3.11 examples/photon_timeresolved.py`
- `coherence_scanning` — op: `chromatic_confocal_height`, `chromatic_confocal_simulate`, `csi_contrast_map`, `csi_design`, `csi_envelope`, `csi_height_map`, `csi_peak_position`, `csi_signal_simulate`, `csi_stack_simulate`, `envelope`, `gaussian` `py -3.11 examples/coherence_scanning.py`
- `specular_photometric` — op: `brdf_blinn_phong`, `brdf_microfacet`, `dichromatic_render`, `illuminant_from_dichromatic_planes`, `median`, `photometric_residual`, `photometric_stereo_robust`, `polarization_dolp_map`, `polarization_render`, `polarization_separate`, `polarization_stokes`, `specular_coefficient_map`(另有 3 个) `py -3.11 examples/specular_photometric.py`
- `fmcw_range_doppler` — op: `beamform_delay_sum`, `beamform_doa`, `fmcw_beat_simulate`, `fmcw_design`, `fmcw_range_profile`, `fmcw_window_apply`, `range_doppler_map`, `range_doppler_peaks` `py -3.11 examples/fmcw_range_doppler.py`
- `events_from_frames` — op:(没有 op 笔记链接到此例) `py -3.11 examples/events_from_frames.py`
- `poc_tdi_linescan` — op: `emva_pair_statistics`, `lens_field_profile`, `lens_shading_correct`, `lens_shading_gain`, `lens_system`, `linescan_acquire`, `linescan_lens_columns`, `linescan_lens_example`, `paraxial_trace`, `relative_illumination`, `tdi_snr`, `tdi_sync_mtf` `py -3.11 examples/poc_tdi_linescan.py`
- `poc_fourier_ptychography` — op: `coherent_image`, `fp_capture`, `fp_design`, `fp_element_contrast`, `fp_reconstruct`, `fp_stack_from_images`, `fp_usaf_target`, `rms` `py -3.11 examples/poc_fourier_ptychography.py`
- `poc_wavefront_aberration_limits` — op: `pupil_psf` `py -3.11 examples/poc_wavefront_aberration_limits.py`
- `poc_mueller_dofp_observability` — op: `mueller_element` `py -3.11 examples/poc_mueller_dofp_observability.py`
- `poc_slanted_edge_sfr_limits` — op: `mtf_diffraction` `py -3.11 examples/poc_slanted_edge_sfr_limits.py`
- `poc_pixel_shift` — op: `airy_pattern`, `annotate_figure_grid`, `drizzle_resample`, `edge_spread`, `false_color_metric`, `halftone_screen`, `mtf50`, `mtf_diffraction`, `pixel_shift_capture`, `pixel_shift_merge`, `pixel_shift_motion_mask`, `pixel_shift_pattern`(另有 6 个) `py -3.11 examples/poc_pixel_shift.py`
- `poc_itof_multifreq` — op: `annotate_figure_grid`, `camera_rays`, `dtof_cube_depth`, `dtof_cube_simulate`, `erfc`, `form_factors_2d`, `gamma`, `gaussian`, `groove_profile`, `itof_capture`, `itof_flying_pixel_mask`, `itof_multipath_separate`(另有 9 个) `py -3.11 examples/poc_itof_multifreq.py`
- `poc_fiber_light_guide` — op: `energy_to_photons`, `fiber_bundle_coupling`, `fiber_lp_modes`, `fiber_mode_field_diameter`, `fiber_numerical_aperture`, `fiber_v_number`, `led_spectrum`, `material_dispersion`, `material_group_index`, `material_gvd`, `material_transmittance`, `silicon_photodiode_qe`(另有 2 个) `py -3.11 examples/poc_fiber_light_guide.py`
- `poc_lens_file_roundtrip` — op: `drawing_raster`, `lens_file_read`, `lens_file_report`, `lens_file_system`, `lens_file_write`, `lens_section_drawing`, `lens_system`, `merit_function`, `mtf50`, `mtf_diffraction`, `noncoaxial_example`, `noncoaxial_layout`(另有 9 个) `py -3.11 examples/poc_lens_file_roundtrip.py`
- `poc_zoom_configurations` — op: `encircled_energy`, `lens_add_configuration`, `lens_configuration_metrics`, `lens_configuration_table`, `lens_configurations`, `lens_file_read`, `lens_file_write`, `lens_system`, `lens_with_configuration`, `paraxial_trace` `py -3.11 examples/poc_zoom_configurations.py`
- `poc_lockin_imaging` — op: `lockin_amplitude`, `lockin_demodulate`, `lockin_noise_floor`, `lockin_phase`, `lockin_ring_normals`, `lockin_ring_synthesize`, `lockin_separate`, `lockin_thermal_wave`, `lockin_walsh_codes` `py -3.11 examples/poc_lockin_imaging.py`
- `poc_lens_global_search` — op: `glass`, `glass_map`, `glass_nearest`, `lens_global_search`, `lens_substitute_glasses`, `lens_system`, `paraxial_trace`, `with_wavelength` `py -3.11 examples/poc_lens_global_search.py`
- `poc_lens_merit_operands` — op: `lens_system`, `merit_boundary_operands`, `merit_contributions`, `merit_default`, `merit_evaluate`, `merit_function`, `merit_operands_list`, `optimize_lens_operands`, `paraxial_trace`, `ray_bundle`, `text_box`, `with_wavelength` `py -3.11 examples/poc_lens_merit_operands.py`
- `poc_lens_tolerancing` — op: `chief_ray`, `lens_system`, `opd_samples`, `ray_bundle`, `tolerance_compensators`, `tolerance_criteria`, `tolerance_monte_carlo`, `tolerance_report`, `tolerance_sensitivity`, `tolerance_table`, `tolerance_table_from_zmx`, `tolerance_table_zmx` `py -3.11 examples/poc_lens_tolerancing.py`
- `poc_plenoptic_camera` — op: `arc`, `lens_scene`, `lens_system`, `lf_depth_from_focus`, `lf_refocus`, `mla_surface`, `paraxial_trace`, `plenoptic_capture`, `plenoptic_decode`, `plenoptic_mla_calibrate`, `plenoptic_refocus_depth`, `plenoptic_system`(另有 1 个) `py -3.11 examples/poc_plenoptic_camera.py`
- `plenoptic_capture_pipeline` — op: `lens_scene`, `lens_system`, `mla_surface`, `plenoptic_capture`, `plenoptic_system` `py -3.11 examples/plenoptic_capture_pipeline.py`
- `plenoptic_decode_pipeline` — op: `lf_depth_from_focus`, `lf_refocus`, `lf_synthesize`, `lf_to_mla`, `plenoptic_decode` `py -3.11 examples/plenoptic_decode_pipeline.py`
- `poc_photograph_through_prescription` — op: `bokeh_shape`, `chief_ray`, `chromatic_shift`, `depth_of_field`, `distortion_map`, `exit_pupil_samples`, `ghost_analysis`, `lens_scene`, `lens_system`, `noncoaxial_system`, `paraxial_trace`, `ray_bundle`(另有 7 个) `py -3.11 examples/poc_photograph_through_prescription.py`
- `poc_tof_camera` — op: `dtof_cube_depth`, `dtof_cube_simulate`, `threshold` `py -3.11 examples/poc_tof_camera.py`
- `poc_zmx_public_verify` — op: `chromatic_shift`, `distortion_map`, `lens_file_read`, `paraxial_trace`, `psf_from_opd`, `psf_to_mtf`, `ray_bundle`, `render_through_lens`, `spot_stats` `py -3.11 examples/poc_zmx_public_verify.py`
- `poc_omni360_inspection` — op: `anaglyph_crosstalk`, `equirect_defect_unwrap_pipe`, `equirect_filter_gaussian`, `equirect_from_fisheye_pair`, `equirect_rotate`, `equirect_stabilize`, `equirect_weight_map`, `ods_depth_to_disparity`, `ods_disparity_to_depth`, `omni_anaglyph_compose`, `stereo_parallax_budget`, `video360_tile_coverage`(另有 3 个) `py -3.11 examples/poc_omni360_inspection.py`
- `photoelastic_roundtrip` — op: `brazilian_disc_stress`, `cubic_photoelastic_birefringence`, `kirsch_plate_stress`, `photoelastic_phase_estimate`, `photoelastic_polarization_images`, `photoelastic_retardation`, `polariscope_intensity`, `principal_stress`, `retardation_convert`, `retardation_from_birefringence`, `retardation_unwrap_multiwavelength`, `silicon_piezo_optic_coefficients` `py -3.11 examples/photoelastic_roundtrip.py`
- `omni360_roundtrip` — op: `anaglyph_from_ods`, `cubemap_from_equirect`, `equirect_from_cubemap`, `equirect_from_perspectives`, `ods_render`, `s_psnr`, `stereo360_sbs`, `stereo360_top_bottom`, `stereo_pack`, `viewport`, `viewport_from_equirect`, `ws_psnr` `py -3.11 examples/omni360_roundtrip.py`
- `poc_water_transparent_media` — op: `beer_lambert_transmittance`, `cylinder_lens_caustic`, `fresnel_water_air`, `ocean_height_field`, `ocean_spectrum`, `phase_function_hg`, `refract_rays`, `refracted_view`, `scattering_phase_petzold`, `snell_window`, `underwater_image`, `water_attenuation` `py -3.11 examples/poc_water_transparent_media.py`
- `poc_water_inspection_images` — op: `bottle_image`, `canny`, `caustic_floor_segmentation`, `caustic_irradiance`, `fill_level_from_image`, `fresnel_water_air`, `ocean_height_field`, `otsu`, `underwater_inspection_image`, `water_attenuation`, `wet_dry_inspection_pair`, `wet_surface_appearance` `py -3.11 examples/poc_water_inspection_images.py`
- `poc_bottle_pattern_inverse` — op: `bottle_background_map`, `bottle_fit_from_pattern`, `bottle_image`, `fill_level_from_image` `py -3.11 examples/poc_bottle_pattern_inverse.py`
- `poc_lens_solves_afocal` — op: `afocal_system`, `chief_ray`, `lens_afocal_report`, `lens_apply_solves`, `lens_file_read`, `lens_file_write`, `lens_image_surface`, `lens_petzval_radius`, `lens_solve_clear`, `lens_solve_set`, `lens_solves_list`, `lens_system`(另有 8 个) `py -3.11 examples/poc_lens_solves_afocal.py`
- `poc_pocket_interreflection` — op: `camera_rays`, `form_factor_matrix`, `form_factor_parallel_rects`, `form_factor_perpendicular_rects`, `form_factor_polygons`, `intensity`, `light_source`, `log`, `optical_camera`, `radiosity_patches`, `radiosity_progressive_3d`, `render_optscene`(另有 12 个) `py -3.11 examples/poc_pocket_interreflection.py`
- `poc_optics_drawings` — op: `arc`, `chief_ray`, `chief_ray_angle`, `drawing_dxf`, `drawing_raster`, `drawing_svg`, `dxf_entities`, `glass`, `glass_map`, `layout_capture`, `lens_element_drawing`, `lens_section_drawing`(另有 11 个) `py -3.11 examples/poc_optics_drawings.py`
- `poc_noncoaxial_optics` — op: `beamsplitter_branches`, `drawing_raster`, `ghost_analysis`, `ghost_image`, `ghost_path`, `image_orientation`, `lens_system`, `noncoaxial_drawing`, `noncoaxial_example`, `noncoaxial_layout`, `noncoaxial_spot`, `noncoaxial_system`(另有 9 个) `py -3.11 examples/poc_noncoaxial_optics.py`
- `poc_simcal_pixel_shift` — op: `log`, `pixel_shift_capture`, `pixel_shift_merge`, `pixel_shift_resolution_budget`, `simcal_discrepancy`, `simcal_fit`, `simcal_identifiability`, `simcal_model`, `simcal_observe`, `simcal_screen`, `simcal_simulate`, `simcal_validate`(另有 1 个) `py -3.11 examples/poc_simcal_pixel_shift.py`
- `poc_thin_film_reflectometry` — op: `annotate_colorbar`, `blackbody_spectrum`, `film_color`, `film_thickness_fft`, `film_thickness_fit`, `film_thickness_map`, `multilayer_reflectance`, `spectrum`, `text_box` `py -3.11 examples/poc_thin_film_reflectometry.py`
- `poc_simcal_thin_film` — op: `axes_frame`, `axes_transform`, `blackbody_spectrum`, `color_bar`, `doe_decode`, `doe_orthogonal_array`, `gamma`, `gaussian`, `log`, `multilayer_reflectance`, `mv_confounding`, `mv_pca`(另有 15 个) `py -3.11 examples/poc_simcal_thin_film.py`
- `poc_spectrometer_illumination` — op: `chromatic_confocal_peaks`, `chromatic_confocal_probe`, `chromatic_confocal_readout`, `chromatic_confocal_spectrum`, `coaxial_illumination`, `czerny_turner_design`, `grating_dispersion`, `illumination_field`, `illumination_train`, `spectrometer_bandpass`, `spectrometer_slit_image`, `spectrometer_spectrum`(另有 2 个) `py -3.11 examples/poc_spectrometer_illumination.py`
- `poc_chromatic_confocal` — op: `abbe_number`, `chromatic_confocal_limits`, `chromatic_confocal_peaks`, `chromatic_confocal_probe`, `chromatic_confocal_readout`, `chromatic_confocal_spectrum`, `cie_xyz_from_wavelength`, `confocal_axial_response`, `gaussian`, `led_spectrum`, `lens_system`, `material_optical_constants`(另有 6 个) `py -3.11 examples/poc_chromatic_confocal.py`
- `poc_hyperspectral_foreign_matter` — op: `carbon_black_absorption`, `hyperspectral_band_weights`, `hyperspectral_capture`, `ingaas_photodiode_qe`, `kubelka_munk_reflectance`, `material_nir_absorption`, `median`, `nir_model_info`, `spectral_reflectance_from_material`, `text_box` `py -3.11 examples/poc_hyperspectral_foreign_matter.py`
- `poc_nir_silicon_transmission` — op: `bandpass_spectrum`, `blackbody_spectrum`, `camera_rays`, `cie_illuminant_a`, `defocus_from_shift`, `energy_to_photons`, `gaussian`, `layout_capture`, `led_spectrum`, `lens_spec`, `light_spec`, `material_optical_constants`(另有 15 个) `py -3.11 examples/poc_nir_silicon_transmission.py`
- `poc_material_optical_library` — op: `abbe_number`, `acoustic_impedance_mismatch`, `chromatic_shift`, `fresnel_conductor`, `glass`, `glass_catalog`, `glass_map`, `lens_system`, `material_absorption`, `material_acoustic`, `material_dispersion`, `material_extinction`(另有 19 个) `py -3.11 examples/poc_material_optical_library.py`
- `poc_dual_energy_xray` — op: `basis_decomposition_crlb`, `basis_material_decompose`, `dual_energy_separability`, `dual_kvp_channels`, `ellipse`, `material_effective_z`, `material_from_sellmeier`, `material_xray_attenuation`, `material_xray_constants`, `photon_counting_channels`, `xray_beam_quality`, `xray_channel_projection`(另有 1 个) `py -3.11 examples/poc_dual_energy_xray.py`

**appearance**
- `appearance_structural_colour` — op: `cie_xyz_from_wavelength`, `grating_rgb`, `grating_wavelengths`, `spectrum_to_srgb`, `thin_film_reflectance`, `thin_film_rgb`, `ward_anisotropic` `py -3.11 examples/appearance_structural_colour.py`
- `machined_metal_and_materials` — op: `blast_normals`, `clearcoat_shade`, `corrosion_mask`, `finish_catalog`, `finish_shade`, `material_catalog`, `metallic_flake_normals`, `micro_normals`, `oren_nayar`, `rough_transmission`, `sheen_shade`, `slab_transmittance`(另有 5 个) `py -3.11 examples/machined_metal_and_materials.py`

**tomography_3d**
- `ct_reconstruction` — op: `backproject_sinogram`, `beam_hardening_apply`, `beam_hardening_correct`, `ellipse_phantom`, `ellipse_sinogram`, `filtered_backprojection`, `median`, `metal_trace_interpolate`, `projection_angles`, `radon_transform`, `ring_artifact_apply`, `ring_artifact_remove`(另有 4 个) `py -3.11 examples/ct_reconstruction.py`
- `ct_scan_modes` — op: `ct_adjoint_project`, `ct_forward_project`, `ct_scan_geometry`, `ellipsoid_phantom`, `ellipsoid_projections`, `fdk_reconstruct`, `os_sart_reconstruct`, `rmse`, `shepp_logan_3d`, `sirt_reconstruct`, `tv_reconstruct` `py -3.11 examples/ct_scan_modes.py`
- `tomography_reconstruct` — op: `ellipse_phantom`, `fbp_volume`, `projection_angles`, `radon_volume`, `sinogram_design` `py -3.11 examples/tomography_reconstruct.py`
- `ct_inspection` — op: `gaussian`, `otsu` `py -3.11 examples/ct_inspection.py`
- `voxel_labels_color` — op: `boundary`, `vol_colorize_labels`, `vol_label_color_flicker`, `vol_label_legend`, `vol_label_mpr_rgb`, `vol_label_overlay`, `vol_label_palette`, `vol_label_shape_stats`, `vol_label_slice_rgb`, `vol_label_volume_render`, `vol_labels_to_meshes`, `vol_select_labels` `py -3.11 examples/voxel_labels_color.py`
- `defect_to_cad` — op: `cad_defect_to_cad`, `cad_pixel_to_surface`, `cad_surface_to_pixel`, `cad_visible_faces` `py -3.11 examples/defect_to_cad.py`
- `representation_conversion` — op: `correlation_score`, `cplx_contour_integral`, `cscalar_to_polar`, `curvature_to_table`, `deformation_to_points`, `descriptor_to_matrix`, `descriptor_to_table`, `flow_apply`, `flow_speed`, `flow_to_rgbimage`, `indices_to_labels`, `labels_to_indices`(另有 15 个) `py -3.11 examples/representation_conversion.py`
- `representation_roundtrip` — op: `angle_to_matrix`, `angles_to_normals`, `correlation_score`, `countrate_to_counts`, `counts_to_countrate`, `curvature_to_shape_index`, `descriptor_to_matrix`, `erf`, `flow_magnitude`, `flow_speed`, `gaussians_to_points`, `gaussians_to_voxel`(另有 10 个) `py -3.11 examples/representation_roundtrip.py`
- `hessian_numpy_chain` — op: `hessian_determinant`, `hessian_vesselness`, `voxel_to_hessian` `py -3.11 examples/hessian_numpy_chain.py`
- `type_connectivity_tour` — op: `attention_softmax`, `find_peaks`, `frame_axis`, `gradient_coherence`, `gradient_magnitude`, `graph_components`, `graph_from_synapses`, `hessian_determinant`, `hessian_vesselness`, `indices_to_positions`, `jones_apply`, `jones_element`(另有 18 个) `py -3.11 examples/type_connectivity_tour.py`
- `poc_bga_ball_type_roundtrip` — op: `angles_to_normals`, `correlation_score`, `curvature_to_shape_index`, `curvature_to_table`, `erf`, `flow_apply`, `flow_speed`, `gaussians_to_points`, `gaussians_to_voxel`, `graph_components`, `graph_laplacian_spectrum`, `indices_to_labels`(另有 20 个) `py -3.11 examples/poc_bga_ball_type_roundtrip.py`
- `poc_ct_void_morphology` — op: `color_bar`, `text_box` `py -3.11 examples/poc_ct_void_morphology.py`
- `poc_ct_casting_sparse_views` — op: `ct_adjoint_project`, `ct_dual_energy_reconstruct`, `ct_forward_project`, `ct_scan_geometry`, `ellipsoid_phantom`, `ellipsoid_projections`, `fdk_reconstruct`, `os_sart_reconstruct`, `shepp_logan_3d`, `sirt_reconstruct`, `tv_reconstruct` `py -3.11 examples/poc_ct_casting_sparse_views.py`
- `poc_battery_ct_degradation` — op: `beam_hardening_apply`, `fbp_volume`, `projection_angles`, `radon_volume`, `ring_artifact_apply` `py -3.11 examples/poc_battery_ct_degradation.py`
- `poc_battery_electrode_tortuosity` — op: `intersection` `py -3.11 examples/poc_battery_electrode_tortuosity.py`
- `poc_die_tilt_tsv_overlay` — op: `erf`, `procrustes_fit` `py -3.11 examples/poc_die_tilt_tsv_overlay.py`
- `poc_real_walnut_cbct` — op: `arc`, `ct_adjoint_project`, `ct_dual_energy_reconstruct`, `ct_forward_project`, `ct_scan_geometry`, `fdk_reconstruct`, `os_sart_reconstruct`, `rmse`, `sirt_reconstruct`, `ssim`, `threshold`, `tv_reconstruct` `py -3.11 examples/poc_real_walnut_cbct.py`

**perception_templates**
- `perception_pipeline` — op: `elevation_map` `py -3.11 examples/perception_pipeline.py`
- `segment_and_classify` — op: `otsu` `py -3.11 examples/segment_and_classify.py`
- `motion_analysis` — op:(没有 op 笔记链接到此例) `py -3.11 examples/motion_analysis.py`
- `grasp_pose` — op: `rmse` `py -3.11 examples/grasp_pose.py`
- `perception_on_video` — op: `flow_magnitude` `py -3.11 examples/perception_on_video.py`
- `physical_ai_perception` — op: `com_support_margin`, `elevation_map`, `foothold_candidates`, `support_polygon` `py -3.11 examples/physical_ai_perception.py`
- `import_and_grasp` — op:(没有 op 笔记链接到此例) `py -3.11 examples/import_and_grasp.py`
- `gaussian_splat_cloud` — op:(没有 op 笔记链接到此例) `py -3.11 examples/gaussian_splat_cloud.py`
- `sim2real_and_alife` — op: `alife_cyclic_ca`, `alife_dla`, `alife_life_step`, `alife_reaction_bz`, `alife_turing`, `aug_barrel`, `aug_fixed_pattern`, `aug_jpeg_blocks`, `aug_rolling_shutter`, `aug_shot_noise`, `aug_vignette`, `macro_denoise`(另有 5 个) `py -3.11 examples/sim2real_and_alife.py`
- `poc_code_matching_breakdown` — op: `isc_match`, `ncc_locate`, `ocm_match`, `radial_reach_filter`, `scc_match`, `text_box` `py -3.11 examples/poc_code_matching_breakdown.py`
- `poc_bev_sensor_fusion` — op: `closing_circle`, `fill_up` `py -3.11 examples/poc_bev_sensor_fusion.py`
- `poc_safety_clearance` — op:(没有 op 笔记链接到此例) `py -3.11 examples/poc_safety_clearance.py`

**consumer**
- `consumer_hillco` — op: `com_from_silhouette`, `com_support_margin`, `foothold_candidates`, `gait_phase`, `support_polygon` `py -3.11 examples/consumer_hillco.py`
- `consumer_onocollo` — op: `com_support_margin`, `contact_points`, `gait_phase`, `support_polygon` `py -3.11 examples/consumer_onocollo.py`

**optics_layout**
- `vision_layout_from_catalog` — op: `airy_radius_um`, `covers_sensor`, `diffraction_blur`, `interface_budget`, `layout_capture`, `lens_catalog`, `lens_spec`, `light_catalog`, `light_spec`, `light_wavelengths`, `linescan_capture`, `observe_surface`(另有 10 个) `py -3.11 examples/vision_layout_from_catalog.py`
- `studio_raytrace_scene` — op: `camera_rays`, `env_lightbox`, `env_studio`, `illumination_visibility`, `light_spec`, `optical_camera`, `optscene_defect_mask`, `reflect_rays`, `render_studio`, `scene_box`, `scene_difference`, `scene_material`(另有 2 个) `py -3.11 examples/studio_raytrace_scene.py`

**shape_statistics**
- `shapestat_landmark_tour` — op: `generalized_procrustes`, `landmark_asymmetry`, `mirror_plane_from_pairs`, `procrustes_align`, `procrustes_distance`, `procrustes_fit`, `shape_explained_variance`, `shape_mahalanobis`, `shape_mean`, `shape_pca`, `shape_perturb`, `shape_project`(另有 4 个) `py -3.11 examples/shapestat_landmark_tour.py`

**blob_analysis**
- `blob_split_tour` — op: `blob_distance`, `blob_label`, `blob_seeds`, `blob_split` `py -3.11 examples/blob_split_tour.py`

**detection**
- `poc_good_sample_variation_model` — op: `anomaly_image_auroc`, `anomaly_pixel_auroc`, `anomaly_pro`, `anomaly_region_overlap`, `dc_rpca_sparse`, `varmodel_alignment`, `varmodel_calibrate`, `varmodel_fit`, `varmodel_score` `py -3.11 examples/poc_good_sample_variation_model.py`
- `poc_patch_anomaly` — op: `anomaly_image_auroc`, `anomaly_operating_point`, `anomaly_pixel_auroc`, `anomaly_pixel_f1_max`, `anomaly_pro`, `anomaly_region_overlap`, `gabor`, `intensity`, `patch_features`, `patchbank_fit`, `patchbank_score`, `patchdist_fit`(另有 2 个) `py -3.11 examples/poc_patch_anomaly.py`
- `poc_ai_built_inspection_scored` — op: `anomaly_image_auroc`, `anomaly_region_overlap`, `bothat`, `gaussian`, `hx_plane_deviation`, `invert`, `median`, `patchbank_fit`, `patchbank_score`, `select_shape`, `threshold` `py -3.11 examples/poc_ai_built_inspection_scored.py`
- `poc_si_wafer_pl_defect_visibility` — op: `pl_diffusion_psf`, `pl_groove_visibility`, `pl_image_simulate`, `pod_hitmiss_fit` `py -3.11 examples/poc_si_wafer_pl_defect_visibility.py`
- `poc_real_defect_floor` — op: `annotate_inset`, `annotate_legend`, `laplace_of_gauss` `py -3.11 examples/poc_real_defect_floor.py`
- `poc_search_sweep_width` — op: `erf`, `gauss_filter`, `gray_tophat`, `integrate_funct_1d`, `laplace`, `ncc_locate`, `noise_sigma`, `photon_sample`, `relative_illumination`, `star_detect`, `tophat`, `vignette`(另有 1 个) `py -3.11 examples/poc_search_sweep_width.py`

**tracking**
- `poc_real_bg_kalman_tracking` — op: `atan2_image`, `create_bg_esti`, `ellipse`, `filter_kalman`, `give_bg_esti`, `kalman_smooth`, `opening_seg`, `run_bg_esti`, `threshold`, `update_bg_esti` `py -3.11 examples/poc_real_bg_kalman_tracking.py`

**space**
- `poc_star_tracker` — op:(没有 op 笔记链接到此例) `py -3.11 examples/poc_star_tracker.py`

### 3-D 点云/体数据/曲面(124 例)

**registration**
- `cad_to_scan` — op:(没有 op 笔记链接到此例) `py -3.11 examples_3d/cad_to_scan.py`
- `find_surface_pose_bracket` — op: `find_surface_pose` `py -3.11 examples_3d/find_surface_pose_bracket.py`
- `auto_register` — op:(没有 op 笔记链接到此例) `py -3.11 examples_3d/auto_register.py`
- `reg_eval` — op: `inlier_ratio`, `registration_recall`, `rmse_inliers`, `rotation_translation_error` `py -3.11 examples_3d/reg_eval.py`
- `two_view_pose` — op: `fundamental_8point`, `recover_pose`, `sampson_distance` `py -3.11 examples_3d/two_view_pose.py`
- `bundle_adjust` — op: `bundle_adjust`, `mean_reprojection_error`, `project` `py -3.11 examples_3d/bundle_adjust.py`
- `pose_graph_slam` — op: `optimize_pose_graph`, `relative_pose` `py -3.11 examples_3d/pose_graph_slam.py`
- `vol_geometry_transform` — op: `vol_affine`, `vol_resize`, `vol_rotate` `py -3.11 examples_3d/vol_geometry_transform.py`
- `itokawa_pose_canonical` — op: `chamfer_distance`, `moment_axes` `py -3.11 examples_3d/itokawa_pose_canonical.py`
- `itokawa_self_register` — op: `icp_point2point_3d`, `pose_error` `py -3.11 examples_3d/itokawa_self_register.py`
- `gicp_register` — op: `estimate_covariances`, `gicp`, `icp_point2point_3d` `py -3.11 examples_3d/gicp_register.py`
- `feature_register` — op: `estimate_normals`, `harris3d_keypoints`, `iss_keypoints`, `register_fpfh`, `register_shot`, `register_spin`, `shot_descriptor` `py -3.11 examples_3d/feature_register.py`
- `partial_overlap_icp` — op: `icp_point2point_3d` `py -3.11 examples_3d/partial_overlap_icp.py`

**metrology**
- `plane_flatness` — op:(没有 op 笔记链接到此例) `py -3.11 examples_3d/plane_flatness.py`
- `geodesic_dome` — op: `geodesic_dome` `py -3.11 examples_3d/geodesic_dome.py`
- `minimal_surfaces` — op: `curve3d_tube_mesh`, `gyroid_isosurface`, `gyroid_solid_mask`, `mean_curvature`, `mesh_area`, `mesh_volume`, `minimal_surface`, `minimal_surface_bend`, `principal_curvatures`, `vertex_curvature` `py -3.11 examples_3d/minimal_surfaces.py`
- `roundness` — op:(没有 op 笔记链接到此例) `py -3.11 examples_3d/roundness.py`
- `ransac_prim` — op: `ransac_cylinder`, `ransac_plane`, `ransac_sphere` `py -3.11 examples_3d/ransac_prim.py`
- `roi_domain_boundary` — op: `fit_sphere3`, `vol_boundary`, `vol_boundary_points`, `vol_bounding_box`, `vol_crop_domain`, `vol_reduce_domain`, `vol_uncrop` `py -3.11 examples_3d/roi_domain_boundary.py`
- `rle_region_efficiency` — op: `vol_bounding_box`, `vol_rle_bbox`, `vol_rle_centroid`, `vol_rle_components`, `vol_rle_decode`, `vol_rle_difference`, `vol_rle_encode`, `vol_rle_intersect`, `vol_rle_union`, `vol_rle_volume`, `vol_tiled_map` `py -3.11 examples_3d/rle_region_efficiency.py`
- `wall_thickness_probe` — op: `vol_edge_probe`, `vol_profile_line`, `vol_wall_thickness` `py -3.11 examples_3d/wall_thickness_probe.py`
- `curvilinear_proj` — op: `cylinder_unwrap`, `fit_zernike`, `polar_unwrap`, `project_cylindrical` `py -3.11 examples_3d/curvilinear_proj.py`
- `geometry_metrology` — op: `angle_3points`, `angle_between_lines`, `angle_between_planes`, `angle_line_plane`, `background_flatten`, `distance_line_line`, `distance_point_line`, `distance_point_plane`, `distance_segment_segment`, `fit_circle_3d`, `fit_line_3d`, `fit_plane_3d`(另有 7 个) `py -3.11 examples_3d/geometry_metrology.py`
- `primitive_fitting_3d` — op: `fit_circle3`, `fit_line3`, `fit_plane3`, `fit_sphere3`, `fit_surface_principal_axes`, `smallest_sphere3` `py -3.11 examples_3d/primitive_fitting_3d.py`
- `inner_box_inspection` — op: `inner_box3` `py -3.11 examples_3d/inner_box_inspection.py`
- `oriented_bounding_box` — op: `fit_box3`, `smallest_box3`, `smallest_box3_axis` `py -3.11 examples_3d/oriented_bounding_box.py`
- `hull_bounds` — op: `aabb`, `convex_hull`, `mesh_volume`, `min_enclosing_sphere`, `obb` `py -3.11 examples_3d/hull_bounds.py`
- `gear_metrology` — op: `box_sdf`, `grid_coords`, `sdf_intersect`, `sdf_union`, `sphere_sdf` `py -3.11 examples_3d/gear_metrology.py`
- `cylinder_axis_metrology` — op: `estimate_normals` `py -3.11 examples_3d/cylinder_axis_metrology.py`

**segmentation**
- `gray_window_level` — op: `vol_equalize`, `vol_gamma`, `vol_stretch`, `vol_window_level` `py -3.11 examples_3d/gray_window_level.py`
- `object_segmentation` — op: `euclidean_cluster`, `plane_segmentation` `py -3.11 examples_3d/object_segmentation.py`
- `region_props_3d` — op: `filter_by_volume`, `label_components`, `largest_component`, `region_props` `py -3.11 examples_3d/region_props_3d.py`
- `sensor_seg` — op: `bearing_angle_image`, `cutout`, `elastic_deform`, `inflate`, `joint_bilateral`, `link_edges`, `normal_from_reflection`, `reflect`, `region_growing` `py -3.11 examples_3d/sensor_seg.py`
- `watershed3d` — op: `label_components` `py -3.11 examples_3d/watershed3d.py`
- `molecule_atom_count` — op: `grid_coords`, `sphere_sdf`, `vol_distance_transform`, `vol_label`, `vol_local_maxima`, `vol_watershed` `py -3.11 examples_3d/molecule_atom_count.py`
- `lidar_scene_segmentation` — op:(没有 op 笔记链接到此例) `py -3.11 examples_3d/lidar_scene_segmentation.py`

**reconstruction**
- `deconv_fft_restore` — op: `vol_fft_bandpass`, `vol_fft_highpass`, `vol_fft_lowpass`, `vol_gaussian_psf`, `vol_richardson_lucy` `py -3.11 examples_3d/deconv_fft_restore.py`
- `denoise_evolution` — op: `describe` `py -3.11 examples_3d/denoise_evolution.py`
- `tsdf_fusion_demo` — op: `extract_surface_points`, `fuse` `py -3.11 examples_3d/tsdf_fusion_demo.py`
- `contours_to_surface` — op:(没有 op 笔记链接到此例) `py -3.11 examples_3d/contours_to_surface.py`
- `contours_to_terrain` — op: `eval_poly_surface`, `fit_poly_surface` `py -3.11 examples_3d/contours_to_terrain.py`
- `space_carving` — op: `carve`, `carve_look_at`, `synthesize_silhouette`, `visual_hull` `py -3.11 examples_3d/space_carving.py`
- `metrics_eval` — op: `chamfer_distance`, `fscore`, `m3c2_distance`, `normal_consistency`, `rmse_correspondence`, `voxel_iou` `py -3.11 examples_3d/metrics_eval.py`
- `sfm_recon` — op: `alpha_shape_boundary`, `essential_8point`, `estimate_alpha`, `grid_coords`, `mean_edge_error`, `relative_pose`, `render_point_depth`, `sdf_offset`, `sphere_sdf`, `triangulate` `py -3.11 examples_3d/sfm_recon.py`
- `alpha_shape_topology` — op: `alpha_shape_mesh`, `estimate_alpha` `py -3.11 examples_3d/alpha_shape_topology.py`
- `poisson_surface_recon` — op: `chamfer_distance`, `hausdorff_distance`, `poisson_lite` `py -3.11 examples_3d/poisson_surface_recon.py`

**depth**
- `plane_sweep_depth` — op: `plane_sweep_depth` `py -3.11 examples_3d/plane_sweep_depth.py`
- `depth_denoise` — op: `bilateral_filter_depth`, `fill_holes` `py -3.11 examples_3d/depth_denoise.py`
- `ct_hand_radiograph` — op: `render_volume_projection` `py -3.11 examples_3d/ct_hand_radiograph.py`
- `ct_sparse_view_recon` — op:(没有 op 笔记链接到此例) `py -3.11 examples_3d/ct_sparse_view_recon.py`
- `stereo_depth_scene` — op:(没有 op 笔记链接到此例) `py -3.11 examples_3d/stereo_depth_scene.py`

**modeling**
- `sdf_csg` — op: `box_sdf`, `capsule_sdf`, `cylinder_sdf`, `grid_coords`, `plane_sdf`, `sdf_intersect`, `sdf_subtract`, `sdf_union`, `sphere_sdf`, `torus_sdf` `py -3.11 examples_3d/sdf_csg.py`
- `ct_bone_segmentation` — op: `vol_label` `py -3.11 examples_3d/ct_bone_segmentation.py`
- `ct_surface_extraction` — op:(没有 op 笔记链接到此例) `py -3.11 examples_3d/ct_surface_extraction.py`
- `morphology_3d` — op: `morph_close3d`, `morph_dilate3d`, `morph_erode3d`, `morph_gradient3d`, `morph_open3d`, `morph_tophat3d` `py -3.11 examples_3d/morphology_3d.py`
- `procedural_hand` — op: `capsule_sdf`, `grid_coords`, `sphere_sdf` `py -3.11 examples_3d/procedural_hand.py`

**features**
- `curvature_grasp` — op: `gaussian_curvature`, `principal_curvatures`, `shape_index` `py -3.11 examples_3d/curvature_grasp.py`
- `symmetry` — op: `detect_reflection_symmetry`, `detect_rotational_symmetry` `py -3.11 examples_3d/symmetry.py`
- `shape_retrieval` — op: `describe`, `random_rotation`, `shape_distance` `py -3.11 examples_3d/shape_retrieval.py`
- `itokawa_curvature` — op: `principal_curvatures`, `shape_index` `py -3.11 examples_3d/itokawa_curvature.py`
- `itokawa_shape_match` — op: `chamfer_distance`, `icp_point2point_3d` `py -3.11 examples_3d/itokawa_shape_match.py`
- `itokawa_symmetry_honest` — op: `detect_reflection_symmetry` `py -3.11 examples_3d/itokawa_symmetry_honest.py`
- `oriented_normals` — op: `estimate_normals`, `estimate_oriented_normals`, `orient_normals` `py -3.11 examples_3d/oriented_normals.py`
- `shape_descriptor` — op: `match_sh_descriptor`, `sh_descriptor` `py -3.11 examples_3d/shape_descriptor.py`
- `edges_3d` — op: `canny3d`, `edge_points`, `gradient3d`, `log_zero_crossings` `py -3.11 examples_3d/edges_3d.py`
- `diff_features` — op: `curvature_maps`, `edt_jfa`, `hessian3d`, `morph_blackhat3d`, `morph_tophat3d`, `sobel3d` `py -3.11 examples_3d/diff_features.py`
- `dl_mesh_curvature` — op: `mesh_area`, `vertex_curvature` `py -3.11 examples_3d/dl_mesh_curvature.py`
- `fpfh_correspondence` — op: `compute_fpfh`, `estimate_point_normals` `py -3.11 examples_3d/fpfh_correspondence.py`

**motion**
- `motion_seg` — op: `segment_rigid_motions` `py -3.11 examples_3d/motion_seg.py`
- `scene_flow_rigid` — op: `nearest_neighbor_flow`, `rigid_flow`, `smooth_flow` `py -3.11 examples_3d/scene_flow_rigid.py`

**measurement**
- `ct_porosity_and_fibre_morphometry` — op: `vol_euler_number`, `vol_granulometry`, `vol_local_std`, `vol_local_thickness`, `vol_orientation_coherence` `py -3.11 examples_3d/ct_porosity_and_fibre_morphometry.py`

**pose_estimation**
- `pose_estimation` — op: `dlt_pose`, `pnp_ransac`, `project_points`, `reprojection_error` `py -3.11 examples_3d/pose_estimation.py`
- `pnp_pose_outliers` — op: `dlt_pose`, `pnp_ransac`, `project_points`, `reprojection_error` `py -3.11 examples_3d/pnp_pose_outliers.py`

**mapping**
- `occupancy_esdf` — op: `esdf`, `occupancy_grid`, `query_distance` `py -3.11 examples_3d/occupancy_esdf.py`
- `terrain_traversability` — op:(没有 op 笔记链接到此例) `py -3.11 examples_3d/terrain_traversability.py`

**shape_fitting**
- `superquadric_fit` — op: `fit_superquadric`, `inside_outside`, `sample_surface`, `superquadric_residual` `py -3.11 examples_3d/superquadric_fit.py`
- `detect_primitives_3d` — op: `hough_plane_3d`, `hough_sphere_3d` `py -3.11 examples_3d/detect_primitives_3d.py`
- `fit_primitives_ext` — op: `fit_cone`, `fit_ellipsoid`, `fit_torus` `py -3.11 examples_3d/fit_primitives_ext.py`

**shape_descriptors**
- `moment_invariants` — op: `central_moments`, `inertia_tensor`, `moment_invariants`, `shape_distance` `py -3.11 examples_3d/moment_invariants.py`
- `shape_desc_pose` — op: `a3_distribution`, `d2_distribution`, `describe`, `extent_signature`, `match_logpolar_z`, `match_pca`, `match_phase_3d`, `points_to_voxel`, `principal_moments`, `shape_distance` `py -3.11 examples_3d/shape_desc_pose.py`
- `sh_descriptor_retrieval` — op: `match_sh_descriptor`, `points_to_voxel`, `random_rotation`, `sh_descriptor` `py -3.11 examples_3d/sh_descriptor_retrieval.py`

**shape_analysis**
- `vessel_metrology` — op: `vol_distance_transform`, `vol_frangi`, `vol_gradient_magnitude`, `vol_hessian_blobness`, `vol_label`, `vol_local_maxima`, `vol_region_props`, `vol_sato` `py -3.11 examples_3d/vessel_metrology.py`
- `nearest_seed_partition` — op: `edt_jfa_vector`, `vol_distance_transform`, `vol_nearest_label`, `vol_nearest_seed_vector` `py -3.11 examples_3d/nearest_seed_partition.py`
- `medial_topology` — op: `medial_axis_points`, `medial_match`, `skeleton_branches3d`, `skeleton_endpoints3d`, `skeleton_graph3d`, `skeleton_junctions3d`, `skeleton_prune3d`, `skeletonize_vol`, `topology_signature`, `vol_distance_transform` `py -3.11 examples_3d/medial_topology.py`
- `geodesic_distance` — op: `farthest_point_sampling`, `geodesic_distances` `py -3.11 examples_3d/geodesic_distance.py`
- `space_curve` — op: `arc_length`, `curvature_torsion`, `frenet_frame` `py -3.11 examples_3d/space_curve.py`
- `pcl_geodesic` — op: `distance_ridge`, `geodesic_mesh`, `knn_graph`, `mls_smooth`, `radius_outlier_removal`, `statistical_outlier_removal` `py -3.11 examples_3d/pcl_geodesic.py`
- `reflection_symmetry` — op: `detect_reflection_symmetry`, `reflect_points`, `reflection_symmetry_score` `py -3.11 examples_3d/reflection_symmetry.py`
- `torus_knot_curve` — op: `arc_length`, `curvature_torsion`, `frenet_frame` `py -3.11 examples_3d/torus_knot_curve.py`
- `dl_mesh_symmetry` — op: `detect_reflection_symmetry`, `reflection_symmetry_score` `py -3.11 examples_3d/dl_mesh_symmetry.py`
- `rotational_symmetry_fold` — op: `detect_rotational_symmetry` `py -3.11 examples_3d/rotational_symmetry_fold.py`
- `curvature_shape_index` — op: `gaussian_curvature`, `mean_curvature` `py -3.11 examples_3d/curvature_shape_index.py`

**range_sensing**
- `lidar_projection` — op: `project_spherical`, `unproject_spherical` `py -3.11 examples_3d/lidar_projection.py`
- `range_image` — op: `depth_to_organized_points`, `normals_from_depth`, `occlusion_edges` `py -3.11 examples_3d/range_image.py`

**shape_from_shading**
- `photometric_stereo` — op: `integrate_normals`, `photometric_stereo`, `render_lambertian`, `surface_normals` `py -3.11 examples_3d/photometric_stereo.py`

**structured_light**
- `structured_light` — op: `decode_fringe`, `synthesize_fringes`, `unwrap_phase_2d`, `wrapped_phase` `py -3.11 examples_3d/structured_light.py`
- `ftp_and_focus_depth` — op: `depth_from_focus`, `fringe_ftp_phase`, `synthesize_fringes` `py -3.11 examples_3d/ftp_and_focus_depth.py`
- `structured_light_scan` — op: `absolute_phase`, `depth_to_points`, `graycode_decode`, `triangulate_column`, `wrapped_phase` `py -3.11 examples_3d/structured_light_scan.py`
- `graycode_structured_light` — op: `graycode_decode` `py -3.11 examples_3d/graycode_structured_light.py`

**deformable_registration**
- `nonrigid_deform` — op: `register_nonrigid`, `tps_fit`, `tps_warp` `py -3.11 examples_3d/nonrigid_deform.py`

**augmentation**
- `augment_pointcloud` — op: `jitter`, `random_dropout`, `random_rotation`, `random_scale` `py -3.11 examples_3d/augment_pointcloud.py`

**freeform_geometry**
- `bspline_freeform` — op: `eval_bspline_curve`, `eval_bspline_surface`, `fit_bspline_curve`, `fit_bspline_surface`, `fit_spline_curve`, `resample_uniform`, `surface_residual` `py -3.11 examples_3d/bspline_freeform.py`

**match_localize**
- `matching_localize` — op: `match_chamfer_3d`, `match_curvature_3d`, `match_hough_3d`, `match_mip_2d`, `match_points_ncc`, `match_shape_3d` `py -3.11 examples_3d/matching_localize.py`

**scene_flow**
- `motion_scene` — op: `estimate_flow`, `fit_rigid`, `register_cpd_rigid`, `scene_flow_lk`, `warp_by_plane` `py -3.11 examples_3d/motion_scene.py`

**pose_refinement**
- `refinement` — op: `icp_point2plane`, `refine_lm`, `refine_peak_newton`, `refine_rotation_z`, `refine_translation_lk` `py -3.11 examples_3d/refinement.py`

**representation**
- `transforms_repr` — op: `depth_to_points`, `extract_surface_points`, `fuse_to_voxel`, `gaussians_to_voxel`, `integrate`, `mesh_to_voxel`, `register_cross`, `sdf_to_occupancy`, `signed_distance_field`, `to_points`, `tsdf_from_depth`, `voxel_to_mips` `py -3.11 examples_3d/transforms_repr.py`

**mesh_process**
- `mesh_smooth` — op: `laplacian_smooth`, `taubin_smooth`, `voxel_to_mesh` `py -3.11 examples_3d/mesh_smooth.py`
- `mesh_decimate` — op: `boundary_vertices`, `decimate_qem`, `mesh_to_points` `py -3.11 examples_3d/mesh_decimate.py`
- `mesh_props` — op: `boundary_vertices`, `face_areas`, `face_normals`, `mesh_area`, `mesh_volume`, `vertex_curvature`, `vertex_normals` `py -3.11 examples_3d/mesh_props.py`
- `mesh_lod_download` — op: `chamfer_distance`, `decimate_qem`, `hausdorff_distance`, `sample_surface` `py -3.11 examples_3d/mesh_lod_download.py`

**decimation**
- `pointcloud_downsampling` — op: `farthest_point_sampling`, `hausdorff_distance`, `voxel_grid_downsample` `py -3.11 examples_3d/pointcloud_downsampling.py`
- `volume_downsampling` — op: `vol_frangi`, `volume_downsample` `py -3.11 examples_3d/volume_downsampling.py`

**optics**
- `snell_refraction` — op: `fresnel_reflectance`, `reflect`, `refract`, `snell_angle` `py -3.11 examples_3d/snell_refraction.py`

**rendering**
- `points_render_basics` — op: `points_render` `py -3.11 examples_3d/points_render_basics.py`
- `render_ao` — op: `ambient_occlusion`, `render_shaded` `py -3.11 examples_3d/render_ao.py`
- `render_shadow` — op: `cast_shadow` `py -3.11 examples_3d/render_shadow.py`
- `render_shade` — op: `matcap_shade`, `phong_shade`, `render_lambertian` `py -3.11 examples_3d/render_shade.py`
- `render_ssaa` — op: `antialias`, `edge_alias_energy`, `supersample_mesh` `py -3.11 examples_3d/render_ssaa.py`
- `render_tonemap` — op: `tonemap_aces`, `tonemap_reinhard` `py -3.11 examples_3d/render_tonemap.py`
- `itokawa_regolith_hero` — op: `brdf_hapke`, `brdf_lommel_seeliger`, `bump_normals_fbm`, `displacement_band_weights`, `mesh_displace_fbm`, `mesh_displace_spectrum`, `mesh_edge_lengths`, `mesh_scatter_boulders`, `mesh_subdivide`, `render_regolith`, `shadow_raycast`, `terrain_region_mask` `py -3.11 examples_3d/itokawa_regolith_hero.py`
- `render_beauty` — op: `box_sdf`, `cast_shadow`, `edge_alias_energy`, `grid_coords`, `phong_shade`, `render_beauty`, `sdf_intersect`, `sdf_smooth_union`, `sdf_union`, `sphere_sdf`, `tonemap_reinhard` `py -3.11 examples_3d/render_beauty.py`
- `anatomical_hand` — op: `render_beauty` `py -3.11 examples_3d/anatomical_hand.py`
- `annotate3d_figure` — op: `annotate3d_arrow`, `annotate3d_axes`, `annotate3d_bbox`, `annotate3d_label`, `annotate3d_measure`, `annotate3d_project`, `annotate3d_scale_bar`, `sphere_sdf` `py -3.11 examples_3d/annotate3d_figure.py`

**mesh_processing**
- `mesh_resolution_demo` — op: `decimate_qem`, `mesh_decimate_preserving`, `mesh_detail_map`, `mesh_edge_stats`, `mesh_isotropic_remesh`, `mesh_lod_chain`, `mesh_reduction_report`, `mesh_sample_points`, `mesh_select_lod`, `mesh_split_long_edges`, `pc_density`, `pc_density_equalize`(另有 4 个) `py -3.11 examples_3d/mesh_resolution_demo.py`

## 独立的几何/数学模块(函数 API)

不适用于单图像流水线的 op(2 幅图像、点列、可变参数)。作为函数调用。

### `imagemorph` — imagemorph —— 由对应点(地标)驱动的 2D 图像变形(warp)与形变(morph)。

- `warp_piecewise_affine(img, src_pts, dst_pts, order=1)` — 分段仿射变形，把 img 中位于 src_pts 的内容移到 dst_pts。
- `warp_tps_image(img, src_pts, dst_pts, lam=0.0, order=1)` — 用薄板样条把 img 的 src_pts 移到 dst_pts 的平滑变形。
- `blend(a, b, alpha)` — 交叉溶解 (1-alpha)·a + alpha·b(a,b 形状相同，取值 [0,1])。
- `morph(imgA, imgB, ptsA, ptsB, alpha, method='affine', lam=0.0, with_corners=True)` — 按对应点对 2 幅图像 A、B 进行形变，生成比例为 alpha 的中间图像。
- `morph_sequence(imgA, imgB, ptsA, ptsB, n=7, method='affine', lam=0.0, with_corners=True)` — alpha 以 n 级从 0→1 变化的形变序列(从 A 平滑变到 B 的各帧)。
- `add_frame_corners(pts, shape)` — 把图像的四个角(+各边中点)作为固定点加入点集。

### `fourierdesc` — fourierdesc —— 闭合轮廓的椭圆傅里叶描述子(EFD)与复傅里叶平滑。

- `elliptic_fourier(points, n_harmonics=10)` — 以 Kuhl–Giardina 闭式求闭合轮廓的椭圆傅里叶系数。
- `reconstruct(model, n_points=300, n_harmonics=None)` — 由 EFD 系数重建轮廓((M,2))。
- `normalize(model, size_invariant=True)` — 把 EFD 系数变换为“标准位姿”的系数(以第1谐波为基准对齐)。
- `invariants(model, scale_invariant=True)` — 对旋转、平移、起点以及(可选)尺度不变的形状描述子((N,2))。
- `descriptor_distance(m1, m2, n_harmonics=None, scale_invariant=True)` — 2 个形状之间的距离(越小越相似)。对旋转/平移/起点/(可选)尺度不变。
- `fourier_smooth(points, keep)` — 用复 FFT 对轮廓做带限平滑。
- `from_xld(contour, i=0)` — 从 XLD 轮廓 dict(``{"shape", "cs":[Nx2,...]}``)中取出第 i 条轮廓。
- `fit_circle_xld(contour, method='geometric')` — 对每条 XLD 轮廓拟合圆，返回圆心的行、列与半径(``table``)。
- `contour_fourier_complex(points, n_harmonics=None, parametrisation='index')` — 把闭合轮廓变为复傅里叶级数的系数 —— ``z(t) = Σ c_k exp(2πi k t)``。
- `contour_epicycle_chain(spectrum, phase, order='frequency')` — 返回相位 ``t`` 处的**旋转摆链**(``pairs``)。
- `contour_fourier_truncation_energy(spectrum, orders=None)` — 每个截断阶数的**预测**误差(``table``)—— Parseval 的精确式。

### `imagedraw` — imagedraw —— 直接把标记/线/圆/轮廓画进图像数组的光栅绘制 op(numpy)。

- `draw_line(img, p0, p1, color=<from style>, width=<from style>, style=None)` — 从 (x,y)=p0 到 p1 画粗细为 width 的直线。
- `draw_polyline(img, points, color=<from style>, width=<from style>, closed=False, style=None)` — 画连接点列 (N,2) 的折线(closed=True 时回到起点 = 多边形)。
- `draw_circle(img, center, radius, color=<from style>, width=<from style>, fill=<from style>, style=None)` — 圆心 (x,y)、半径 radius 的圆(fill=True 时填充)。
- `draw_markers(img, points, color=<from style>, size=4, shape='cross', width=<from style>, style=None)` — 在点列 (N,2) 的每个点上画标记。shape='cross'|'square'|'dot'。
- `draw_contour(img, contour, color=<from style>, width=<from style>, style=None)` — 把 XLD 轮廓 ``{cs:[Nx2 (row,col),...]}`` 或 (N,2) 数组闭合后绘制。
- `new_canvas(shape, color=<from style>, style=None)` — 创建带背景色的空画布(相当于 HALCON 的 ``set_draw`` + 填充的底图)。

### `signal1d` — signal1d —— 点列(1D 信号)的多项式近似、傅里叶变换、低通/高通(简易 API)。

- `poly_fit(x, y, degree)` — 用 degree 次多项式对点列 (x, y) 做最小二乘近似，返回系数(从最高次开始)。
- `poly_eval(coef, x)` — 在点 x 处计算多项式系数 coef(从最高次开始)的值。
- `fft_spectrum(y, sample_spacing=1.0)` — 返回点列 y 的单边幅度谱 ``(freqs, magnitude)``。
- `lowpass(y, cutoff=0.2)` — 对点列 y 做低通(去掉高频 = 噪声/细节，即平滑)。cutoff = 奈奎斯特比例。
- `highpass(y, cutoff=0.2)` — 对点列 y 做高通(去掉趋势 = 低频，只保留细节、边缘与变动)。
- `bandpass(y, low=0.1, high=0.4)` — 点列 y 的带通(只通过 low..high 之间的频带)。low<high(奈奎斯特比例)。
- `smooth(y, window=5, method='exact')` — 移动平均平滑(window 为奇数窗宽，两端复制边缘)。
- `spline_fit(x, y, smooth=0.0)` — 用三次样条对点列 (x, y) 插值/平滑，返回可求值的 spline object。
- `spline_eval(spline, x)` — 在点 x 处计算 spline object 的值。
- `spline_resample(x, y, n, smooth=0.0)` — 把点列平滑地等间隔重采样为 n 点，返回 ``(x_new, y_new)``。
- `spline_curve_fit(points, closed=False, smooth=0.0)` — 用**弧长参数化三次样条**拟合点列(2D 轮廓 / 3D 空间曲线)。
- `spline_curve_eval(model, t)` — 在参数 t∈[0,1] 处计算曲线样条 model，返回 (M,D) 点(D=2 or 3)。
- `spline_curve_resample(points, n, closed=False, smooth=0.0)` — 把曲线点列平滑地重采样为 n 点并返回 (n,D)(2D/3D，闭合曲线的接缝不重复)。

## Operators by family(族 → 类别，全部 op)

_共 3844 ops / 60 families。排列顺序与笔记位置同 `docs/ops/INDEX.md`(笔记 = `docs/ops/<族>/<类别>/<op>.md`)。台账族的 op 用 `fs.ledger.<op>` 调用。_

族一览: **2d** 964 · **3d** 377 · **fit** 3 · **math** 115 · **optics** 506 · **lightfield** 17 · **photon** 17 · **specular** 20 · **motionmag** 9 · **quat** 19 · **rangedoppler** 8 · **acoustics** 27 · **interferometry** 9 · **flyvision** 22 · **spc** 41 · **graph** 20 · **text** 3 · **residue** 5 · **vx** 10 · **drive** 742 · **tomography** 43 · **volcolor** 11 · **reprconv** 63 · **fileio** 28 · **cadmap** 4 · **annotate** 51 · **gfx2d** 44 · **multivar** 18 · **simcal** 10 · **converge** 6 · **codematch** 6 · **aoi** 8 · **matchreg** 12 · **calib** 29 · **acceptance** 8 · **symbol** 33 · **mv** 47 · **generative** 42 · **imgmetrics** 42 · **oned** 49 · **colortransport** 11 · **imgforensics** 16 · **astrostack** 14 · **videostream** 16 · **profile** 12 · **shapestat** 16 · **measure1d** 17 · **roughness** 9 · **shape2d** 17 · **piv** 29 · **blob** 11 · **dem** 25 · **conngraph** 28 · **emproof** 14 · **videocube** 6 · **live4d** 14 · **printpath** 23 · **geocam** 9 · **llmcore** 10 · **segmentation** 59

### 2d (964 ops / 49 categories)

取 1 幅图像、返回 1 幅图像/区域/轮廓/特征的流水线 op(`ops.REGISTRY`)，以及取多幅图像的 n-ary op(`imgops_nary`)。按 `in → out` 的数据种类组链。HALCON 别名是用途的线索。

#### 2d / 3d (12)
- `vol_dilate` `volume → volume` GPU: 有(vol_dilate_g) — 3D 体数据的灰度膨胀。未指定对应的 HALCON op。 · 示例: `gallery2d_physics_alife_3d`, `poc_warehouse_flow`
- `vol_dilation_ball` `volume → volume` GPU: 有(vol_dilation_ball_g) — 使用球形结构元素的 3D 二值膨胀。未指定对应的 HALCON op。 · 示例: `gallery2d_physics_alife_3d`
- `vol_erode` `volume → volume` GPU: 有(vol_erode_g) — 3D 体数据的灰度腐蚀。未指定对应的 HALCON op。 · 示例: `gallery2d_physics_alife_3d`, `poc_warehouse_flow`
- `vol_erosion_ball` `volume → volume` GPU: 有(vol_erosion_ball_g) — 使用球形结构元素的 3D 二值腐蚀。未指定对应的 HALCON op。 · 示例: `gallery2d_physics_alife_3d`
- `vol_gaussian` `volume → volume` GPU: 有(vol_gaussian_g) — 3D 体数据的各向同性高斯平滑。未指定对应的 HALCON op。 · 示例: `gallery2d_physics_alife_3d`, `poc_am_thermal_to_ct`
- `vol_median` `volume → volume` GPU: 有(vol_median_g) — 3D 体数据的中值滤波。未指定对应的 HALCON op。 · 示例: `gallery2d_physics_alife_3d`
- `vol_mip` `volume → image` GPU: 无 — 通过最大值投影（Maximum Intensity Projection, MIP）将 3D 体数据压缩为 2D 图像。未指定对应的 HALCON op。 · 示例: `gallery2d_physics_alife_3d`, `poc_cold_chain_excursion`
- `vol_opening_ball` `volume → volume` GPU: 有(vol_opening_ball_g) — 使用球形结构元素的 3D 二值开运算（先腐蚀后以相同球体膨胀）。未指定对应的 HALCON op。 · 示例: `gallery2d_physics_alife_3d`, `poc_warehouse_flow`
- `vol_reg_dilate` `volume → volume` GPU: 有(vol_reg_dilate_g) — 3D 二值区域的膨胀（region 体数据的膨胀）。未指定对应的 HALCON op。 · 示例: `gallery2d_physics_alife_3d`
- `vol_reg_erode` `volume → volume` GPU: 有(vol_reg_erode_g) — 3D 二值区域的腐蚀（region 体数据的腐蚀）。未指定对应的 HALCON op。 · 示例: `gallery2d_physics_alife_3d`
- `vol_slice` `volume → image` GPU: 无 — 从 3D 体数据中取出一张 2D 切片。未指定对应的 HALCON op。 · 示例: `gallery2d_physics_alife_3d`
- `vol_threshold` `volume → volume` GPU: 有(vol_threshold_g) — 3D 体数据的全域阈值处理（2-D ``_threshold`` 的 3D 版本）。未指定对应的 HALCON op。 · 示例: `gallery2d_physics_alife_3d`

#### 2d / arithmetic (10)
- `abs_image` (halcon: `abs_image`) `image → image` GPU: 仅在链中(许可列表) — 取像素值的绝对值（``np.abs``）。由于 fullseye 的 ``image`` 已遵循 [0,1] 约定（非负），因此对普通图像而言，此操作是恒等映射，不会改变任何东西。只有在直接传入差分图像等带符号的中间结果时才有意义。用作 HALCON ``abs_image``（Calculate the absolute value (modulus) of an image.）的替代。 · 示例: `gallery2d_gray_arith`, `genspark_external_review`
- `acos_image` (halcon: `acos_image`) `image → image` GPU: 仅在链中(许可列表) — 通过 ``arccos(x) / π`` 将 [0,1] 映射到 [0,1] 的反余弦 LUT。是 ``asin_image`` 的反转形式（单调递减），在 x=0 处为最大值（1），在 x=1 处为最小值（0）。用作 HALCON ``acos_image``（Calculate the arccosine of an image.）的替代。 · 示例: `gallery2d_gray_arith`
- `asin_image` (halcon: `asin_image`) `image → image` GPU: 仅在链中(许可列表) — 通过 ``arcsin(x) / (π/2)`` 将 [0,1] 映射到 [0,1] 的反正弦 LUT。在 x=0 附近与 x=1 附近斜率会变得陡峭（导数在定义域端点发散），具有压缩中间阶调、强调两端对比度的效果。用作 HALCON ``asin_image``（Calculate the arcsine of an image.）的替代。 · 示例: `gallery2d_gray_arith`
- `atan_image` (halcon: `atan_image`) `image → image` GPU: 仅在链中(许可列表) — 通过 ``arctan(x) / (π/2)`` 将 [0,1] 映射到 [0,1] 的反正切 LUT。中心附近（x≈0.5）斜率最大，越靠近两端斜率越平缓 —— 与 ``asin_image`` 相反，这是一条强调中间而非两端对比度的 S 形曲线。用作 HALCON ``atan_image``（Calculate the arctangent of an image.）的替代。 · 示例: `gallery2d_gray_arith`
- `cos_image` (halcon: `cos_image`) `image → image` GPU: 有(cos_image) — 基于 ``(cos(2πx) + 1) / 2`` 的周期性 LUT。相对 ``sin_image`` 相位偏移了 π/2 的版本：在 x=0 处达到最大值（1），在 x=0.5 处达到最小值（0），之后再次上升。用作 HALCON ``cos_image``（Calculate the cosine of an image.）的替代。 · 示例: `gallery2d_gray_arith`
- `exp_image` (halcon: `exp_image`) `image → image` GPU: 仅在链中(许可列表) — 用指数映射 ``(exp(x) - 1) / (e - 1)`` 将 [0,1] 映射到 [0,1]（已归一化，使 x=1 时恰好等于 1）。这是一种压缩低阶调、强调高光的对比度增强，曲线方向与 ``log_image`` 相反。用作 HALCON ``exp_image``（Calculate the exponentiation of an image.）的替代。 · 示例: `gallery2d_gray_arith`
- `log_image` (halcon: `log_image`) `image → image` GPU: 仅在链中(许可列表) — 通过 ``log1p(x) / log(2)`` 将 [0,1] 映射到 [0,1] 的对数压缩（已归一化，使 x=1 时为 1）。这是一条压缩高光、提升暗部细节的色调曲线，与 ``exp_image`` 相反。用作 HALCON ``log_image``（Calculate the logarithm of an image.）的替代。 · 示例: `gallery2d_gray_arith`, `poc_weld_radiograph_porosity`
- `sin_image` (halcon: `sin_image`) `image → image` GPU: 仅在链中(许可列表) — 通过 ``(sin(2πx) + 1) / 2`` 以正弦波方式折叠阶调的周期性 LUT。在 x=0 和 x=1 处回到 0.5，在 x=0.25/0.75 附近分别达到 0/1 —— 它不是单调递增，而是一种多个不同输入阶调共享同一输出的不可逆变换。用作 HALCON ``sin_image``（Calculate the sine of an image.）的替代。 · 示例: `gallery2d_gray_arith`
- `sqrt_image` (halcon: `sqrt_image`) `image → image` GPU: 仅在链中(许可列表) — 对裁剪到 [0,1] 的像素值取平方根。这会形成一种提升暗部的类伽玛阶调压缩（平方根会把 x=0.25 提升到 0.5，把 x=0.04 提升到 0.2）。相当于 HALCON 的 ``sqrt_image``（Calculate the square root of an image.）。 · 示例: `gallery2d_gray_arith`
- `tan_image` (halcon: `tan_image`) `image → image` GPU: 有(tan_image) — 对像素值取正切（tangent）的逐点变换。相当于 HALCON 的 ``tan_image``（计算图像的正切），但归一化约定不同，属于一种近似。 · 示例: `gallery2d_gray_arith`

#### 2d / artificial-life (12)
- `alife_curvature_flow` `image → image` GPU: 有(许可列表) — 平均曲率运动(mean-curvature motion)/水平集(level-set)平滑(曲线缩短流,curve-shortening flow)。 · 示例: `gallery2d_physics_alife_3d`
- `alife_cyclic_ca` `image → image` GPU: 有(许可列表) — 循环细胞自动机(Fisch-Gravner-Griffeath)→ 螺旋波。 · 示例: `gallery2d_physics_alife_3d`, `sim2real_and_alife`
- `alife_dla` `image → image` GPU: 有(许可列表) — 确定性扩散限制凝聚(diffusion-limited aggregation, DLA)生长近似。 · 示例: `gallery2d_physics_alife_3d`, `sim2real_and_alife`
- `alife_gray_scott` `image → image` GPU: 有(许可列表) — 以图像为种子的 Gray-Scott 反应扩散(reaction-diffusion)。 · 示例: `gallery2d_physics_alife_3d`
- `alife_langton_ant` `image → image` GPU: 仅在链中(许可列表) — 在阈值化后的图像格点上行走的 Langton 蚂蚁(turmite)。 · 示例: `gallery2d_physics_alife_3d`
- `alife_lenia` `image → image` GPU: 有(许可列表) — Lenia 连续细胞自动机(Bert Chan,Complex Systems 2019)。 · 示例: `gallery2d_physics_alife_3d`
- `alife_life_step` `image → image` GPU: 有(许可列表) — 类生命(life-like)整体式细胞自动机(Conway 家族 B/S 规则)。 · 示例: `gallery2d_physics_alife_3d`, `sim2real_and_alife`
- `alife_perona_malik` `image → image` GPU: 有(许可列表) — Perona-Malik 各向异性(保边)扩散。 · 示例: `gallery2d_physics_alife_3d`
- `alife_reaction_bz` `image → image` GPU: 无 — 类 Belousov-Zhabotinsky 可激发介质(Greenberg-Hastings 自动机)。 · 示例: `gallery2d_physics_alife_3d`, `sim2real_and_alife`
- `alife_sandpile` `image → image` GPU: 有(许可列表) — 阿贝尔沙堆模型(Abelian sandpile)/自组织临界性(self-organised criticality,Bak-Tang-Wiesenfeld 1987)。 · 示例: `gallery2d_physics_alife_3d`
- `alife_turing` `image → image` GPU: 有(许可列表) — Gierer-Meinhardt 激活剂-抑制剂系统(图灵形态发生,Turing morphogenesis)。 · 示例: `gallery2d_physics_alife_3d`, `sim2real_and_alife`
- `alife_wolfram1d` `image → image` GPU: 无 — Wolfram 基本一维细胞自动机,以时空图(spacetime diagram)形式绘制。 · 示例: `gallery2d_physics_alife_3d`

#### 2d / artistic (3)
- `xcv_pencil_sketch` `image → image` GPU: 无 — OpenCV 的 pencilSketch（铅笔画风格渲染）。 · 示例: `gallery2d_color_artistic`
- `xcv_stylization` `image → image` GPU: 无 — OpenCV 的 stylization（绘画风/卡通风格的非真实感渲染）。 · 示例: `gallery2d_color_artistic`
- `xpil_emboss` `image → image` GPU: 无 — Pillow 的浮雕滤镜。套用 ``PIL.ImageFilter.EMBOSS`` 的固定 3x3 卷积核（检测斜向梯度、将平坦区域压成中间灰的经典 NPR 滤镜）。 · 示例: `gallery2d_color_artistic`

#### 2d / augmentation (10)
- `aug_barrel` `image → image` GPU: 有(许可列表) — 使用标准多项式模型 ``r_src = r*(1 + k*r^2)`` 对归一化半径 ``r``(1 = 图像角点)施加径向镜头畸变:当 ``b < 0.5`` 时为桶形畸变(直线向外弯曲),``b >= 0.5`` 时为枕形畸变,其中 ``k = 0.6*a``(a=0 时无畸变)。目标网格通过逆映射并用 ``ndimage.map_coordinates``(``mode="reflect"``)做双线性重采样,因此不会出现未定义的像素。输出保持 HxW。 · 示例: `gallery2d_color_artistic`, `sim2real_and_alife`
- `aug_chromatic` `image → image` GPU: 有(许可列表) — 灰度图像的侧向色差(lateral chromatic aberration)近似。真实的侧向色差会以不同倍率放大各颜色通道,使边缘产生彩色镶边;在单通道上,可观察到的特征是边缘(高通)能量的一份*偏移*副本叠加在图像上。这里将高通分量 ``v - gaussian(v, 1)`` 沿水平方向偏移 ``s = 1 + int(4*a)`` 像素,再以振幅 ``0.1 + 0.9*b`` 叠加回原图。平坦区域的高通值为零,因此只有边缘会出现镶边——这正是真实行为。 · 示例: `gallery2d_color_artistic`
- `aug_cutout` `image → image` GPU: 有(许可列表) — Cutout / 随机擦除(random-erasing)遮挡(DeVries & Taylor 2017;Zhong 等 2020):从图像中擦除一个边长为 ``max(1, a*min(H,W))`` 的正方形色块,迫使处理流程在部分遮挡下仍能存活,而不是依赖单一显著区块。``b`` 同时决定(以 b 为种子、确定性的)色块位置和填充值:b <= 0.5 时为黑色(0.0),b > 0.5 时为中灰(0.5)。色块始终完全位于画面内。 · 示例: `gallery2d_color_artistic`
- `aug_fixed_pattern` `image → image` GPU: 有(许可列表) — 固定图案噪声（FPN／光响应非均匀性）。与读出噪声不同，此图案在各帧间是静态的：由逐列偏移加逐行偏移构成，各自只抽取一次并保持不变。``a`` 设定幅度 ``0.02 + 0.2*a``；``b`` 选择使用哪一种固定图案（生成器仅由 b 播种，因此扫描 a 只会改变某一种图案的强度）。列方向的 FPN 占主导（权重 2/3），这与 CMOS 列并行 ADC 中的情形一致。 · 示例: `gallery2d_color_artistic`, `sim2real_and_alife`
- `aug_jpeg_blocks` `image → image` GPU: 无 — JPEG 分块(blocking)/振铃(ringing)伪影。图像(缩放到 0..255)被切分为 8x8 的块,每块经过正交归一化的二维 DCT-II(``scipy.fft.dctn``)变换,用标准 JPEG Annex-K 亮度量化表乘以 ``(1 + 40*a)/16`` 进行量化(a=0 时接近无损,a=1 时量化很重),再用逆 DCT 重建。``b`` 会在两个轴上将 8x8 分块网格的相位偏移 ``int(7*b)`` 像素,也就是移动分块接缝的位置。不是 8 的倍数的图像会先做边缘复制填充,再裁剪回 HxW(因此可以处理 4x4 的输入)。 · 示例: `gallery2d_color_artistic`, `poc_prnu_camera_fingerprint`, `sim2real_and_alife`
- `aug_motion_blur` `image → image` GPU: 有(许可列表) — 线性运动模糊：与归一化的直线（盒状）核卷积，即曝光期间恒速相机／场景平移所对应的点扩散函数。``a`` 设定拖影长度 ``L = 3 + 20*a`` px（强制为奇数，并进行钳制以使核尺寸不超过图像）；``b`` 设定拖影角度 ``b*180`` 度。边界处理方式为 ``reflect``，因此画面边缘不会变暗。能量守恒（核之和为 1）。 · 示例: `gallery2d_color_artistic`
- `aug_read_noise` `image → image` GPU: 无 — 加性高斯读出（READ）噪声（放大器 + ADC 噪声），其 sigma 与信号无关（不同于散粒噪声）。``sigma = 0.005 + 0.15*a``。``b`` 混入一个行相关分量：整行共享的、标准差为 ``0.5*b*sigma`` 的逐行偏置，这正是共享行放大器／逐行 ADC 所产生的效果（表现为水平条纹）。由 (a, b) 播种（seed）。 · 示例: `gallery2d_color_artistic`
- `aug_rolling_shutter` `image → image` GPU: 有(许可列表) — 卷帘快门倾斜。 CMOS 卷帘快门按顺序曝光行，因此场景（或摄像机）水平平移每行的量与其行索引成线性关系，即纯​​水平剪切。 ``a`` 设置任一边缘的峰值偏移 ``0.125*W*a`` px（剪力居中，因此中间行不移动），``b`` 设置平移方向（b < 0.5 -> 随着行的增加向右移动，否则向左移动）。使用反射边界进行双线性重采样。 · 示例: `gallery2d_color_artistic`, `sim2real_and_alife`
- `aug_shot_noise` `image → image` GPU: 无 — 光子（泊松）散粒噪声 —— 每个图像传感器固有的量子噪声底限。 · 示例: `gallery2d_color_artistic`, `sim2real_and_alife`
- `aug_vignette` `image → image` GPU: 有(许可列表) — 遵循自然 cos^4 衰减定律的径向镜头渐晕（暗角）。设 ``r`` 为到图像中心的归一化距离，``R = 0.35 + 1.15*b`` 为衰减半径，则透过率为 ``cos(atan(r/R))^4 = 1/(1 + (r/R)^2)^2`` —— 即教科书式的 cos^4 定律。``a`` 用于混合强度：``out = v * (1 - a + a*falloff)``，因此 a=0 时无操作，a=1 时为完全渐晕。中心始终最亮；效果严格为变暗，绝不放大。 · 示例: `gallery2d_color_artistic`, `poc_solar_el_inspection`, `sim2real_and_alife`

#### 2d / barcode (1)
- `decode_barcode` (halcon: `find_bar_code`) `image → feature` GPU: 无 — 统计中央扫描线上明暗切换次数的简易条码风格特征量。它与 HALCON 的 ``find_bar_code``（Detect and read bar code symbols in an image.）貌似而实不同，完全不进行符号体系判定或数据解码(只是数条码的「数量」)。 · 示例: `gallery2d_physics_alife_3d`, `poc_barcode_1d`

#### 2d / bridge (18)
- `contour_to_img` `contour → image` GPU: 无 — **在 XLD 轮廓自身的坐标系中把它画回去** —— 有 43 个 op 会生成轮廓，却没有 1 个 op 能把它落到图像上。 · 示例: `gallery2d_bridge`
- `counts_to_img` `counts → image` GPU: 无 — 把非负整数的1-D计数序列画成**柱状图**并转回图像。 · 示例: `gallery2d_bridge`
- `feature_to_img` `feature → image` GPU: 无 — 把标量 feature 画成**带刻度的条带**并转回图像 —— 在 2-D 台账中，这是**有 125 个 op 会生成、却没有 1 个 op 能落到图像上**的 sort。 · 示例: `gallery2d_bridge`
- `img_to_beatcube` `image → beatcube` GPU: 有(许可列表) — 把图像的亮点当作 FMCW 雷达目标(距离 = 列，速度 = 行)，合成复数拍频立方体 (A,C,S)。 · 示例: `gallery2d_bridge`
- `img_to_cimage` `image → cimage` GPU: 有(许可列表) — 以图像为振幅、以像素值和倾斜给出相位，生成复数场 (H,W) complex128。 · 示例: `gallery2d_bridge`
- `img_to_counts` `image → counts` GPU: 无 — 把图像的一行(或一列)当作光子期望值，生成 Poisson 采样的一维计数序列。 · 示例: `gallery2d_bridge`
- `img_to_keypoints` `image → keypoints` GPU: 有(许可列表) — 把图像的局部极大值变成像面点 (u, v) = (列, 行)，形状 (N,2)。 · 示例: `gallery2d_bridge`
- `img_to_lightfield` `image → lightfield` GPU: 有(许可列表) — 把图像分成前景/背景两层，生成带视差的 4-D 光场 (V,U,H,W)。 · 示例: `gallery2d_bridge`
- `img_to_matrix` `image → matrix` GPU: 无 — 把 (H,W) 图像直接当作 H×W 数值矩阵(sort ``matrix``)—— 纯粹的类型转换。 · 示例: `gallery2d_bridge`
- `img_to_monogenic` `image → qimage` GPU: 有(许可列表) — 生成图像的单尺度单演信号(四元数场 (H,W,4)，sort ``qimage``)。 · 示例: `gallery2d_bridge`
- `img_to_points` `image → points` GPU: 无 — 把图像当作高度场，转换为 (x, y, z) 点云 (N,3)。 · 示例: `gallery2d_bridge`
- `img_to_projection_profile` `image → signal` GPU: 有(许可列表) — 把沿 1 个方向压缩图像得到的**投影轮廓**变成1-D signal —— 版面分析的基本量。 · 示例: `gallery2d_bridge`
- `img_to_rgb` `image → rgbimage` GPU: 仅在链中(许可列表) — 给灰度图像加上色相和饱和度，生成 (H,W,3) RGB 图像(sort ``rgbimage``)。 · 示例: `gallery2d_bridge`
- `img_to_signal` `image → signal` GPU: 无 — 取图像一行(或一列)的灰度剖面作为一维信号。 · 示例: `gallery2d_bridge`
- `img_to_video` `image → video` GPU: 仅在链中(许可列表) — 把图像变成以恒定速度平移的 T 帧视频 (T,H,W)。 · 示例: `gallery2d_bridge`
- `img_to_volume` `image → volume` GPU: 仅在链中(许可列表) — 把图像当作高度场挤出为 (D,H,W) 体数据(z 在前)。 · 示例: `gallery2d_bridge`
- `matrix_to_img` `matrix → image` GPU: 无 — 把矩阵变成**供观看的灰度**并转回图像 —— 这不是类型转换。 · 示例: `gallery2d_bridge`
- `signal_to_img` `signal → image` GPU: 无 — 把1-D signal 画成**折线图**并转回图像 —— “查看生成的序列”的入口。 · 示例: `gallery2d_bridge`

#### 2d / classification (1)
- `classify_shape` `region → feature` GPU: 有(lbl_classify_shape) — 计算最大连通区域的圆形度（circularity）的形状分类基础特征量。未指定对应的单一 HALCON op。 · 示例: `gallery2d_features`

#### 2d / color (8)
- `access_channel` (halcon: `access_channel`) `color → image` GPU: 无 — 从多通道图像中提取一个通道。相当于 HALCON 的 ``access_channel``（访问多通道图像的一个通道）。 · 示例: `gallery2d_color_artistic`, `genspark_external_review`, `poc_leaf_disease_area`, `poc_solder_fillet_aoi`
- `cfa_to_rgb` (halcon: `cfa_to_rgb`) `image → color` GPU: 无 — 从拜耳阵列（CFA：Color Filter Array）到 RGB 图像的去马赛克（demosaic）处理。近似于 HALCON 的 ``cfa_to_rgb``（将单板彩色滤镜阵列图像转换为 RGB 图像）。 · 示例: `gallery2d_color_artistic`
- `linear_trans_color` (halcon: `linear_trans_color`) `color → color` GPU: 仅在链中(许可列表) — 使用 3x3 混合矩阵在通道之间进行线性变换（仿射色彩变换）。相当于 HALCON 的 ``linear_trans_color``（计算多通道图像色值的仿射变换）（本实现是不含偏移项的纯线性变换）。 · 示例: `gallery2d_color_artistic`
- `principal_comp` (halcon: `principal_comp`) `color → color` GPU: 有(principal_comp) — 对 3 通道执行主成分分析（PCA），按方差从大到小重新排列色彩空间。相当于 HALCON 的 ``principal_comp``（计算多通道图像的主成分）。 · 示例: `gallery2d_color_artistic`
- `rgb1_to_gray` (halcon: `rgb1_to_gray`) `color → image` GPU: 无 — 将 RGB 图像转换为亮度（灰度）。HALCON 的 ``rgb1_to_gray`` / ``rgb3_to_gray``（将 RGB 图像转换为灰度图像）两者都分配给了这同一个实现。 · 示例: `gallery2d_color_artistic`
- `rgb3_to_gray` (halcon: `rgb3_to_gray`) `color → image` GPU: 仅在链中(许可列表) — 将 RGB 图像转换为亮度（灰度）。HALCON 的 ``rgb1_to_gray`` / ``rgb3_to_gray``（将 RGB 图像转换为灰度图像）两者都分配给了这同一个实现。 · 示例: `gallery2d_color_artistic`
- `trans_from_rgb` (halcon: `trans_from_rgb`) `color → color` GPU: 无 — 将 RGB 图像转换为其他色彩空间（HSV / Lab / YUV / XYZ）。相当于 HALCON 的 ``trans_from_rgb``（从 RGB 色彩空间转换为任意色彩空间）。 · 示例: `gallery2d_color_artistic`, `poc_leaf_disease_area`, `poc_solder_fillet_aoi`
- `trans_to_rgb` (halcon: `trans_to_rgb`) `color → color` GPU: 无 — 从色彩空间转换回 RGB 的逆变换。据称相当于 HALCON 的 ``trans_to_rgb``（从任意色彩空间转换为 RGB 色彩空间），但**实现仅具有 HSV→RGB 这一个方向**。 · 示例: `gallery2d_color_artistic`

#### 2d / contour (25)
- `affine_trans_contour_xld` (halcon: `affine_trans_contour_xld`) `contour → contour` GPU: 无 — 以图像中心为轴，将轮廓上的各点旋转（-20°〜+20°，由 ``a`` 决定）。HALCON 的 ``affine_trans_contour_xld``（Apply an arbitrary affine 2D transformation to XLD contours.）可以接受任意仿射矩阵（包含平移、缩放、剪切），但此替代实现简化为仅有纯旋转（近似）。 · 示例: `gallery2d_contour_measure`
- `affine_trans_polygon_xld` (halcon: `affine_trans_polygon_xld`) `contour → contour` GPU: 无 — 对 XLD 轮廓（多边形/曲线的顶点序列）施加仿射旋转。以图像中心为基准，按角度 ``-20°+40a`` 旋转（不进行剪切、平移，仅旋转的局部仿射）。b 未使用。 · 示例: `gallery2d_contour_measure`
- `close_contours_xld` (halcon: `close_contours_xld`) `contour → contour` GPU: 无 — 将每条轮廓的起点复制后附加到末尾，把开放折线变成闭合回路（仅适用于点数在 2 以上的轮廓）。相当于 HALCON 的 ``close_contours_xld``（Close an XLD contour.）。 · 示例: `gallery2d_contour_measure`
- `contour_point_num_xld` (halcon: `contour_point_num_xld`) `contour → feature` GPU: 无 — 从一组 XLD 轮廓中选出点数最多的轮廓，将其顶点数以 500 点为基准归一化后以 [0,1] 返回（500 点以上饱和为 1.0）。a、b 未使用。若没有轮廓则返回 0。 · 示例: `gallery2d_contour_measure`
- `contours_to_region` (halcon: `gen_region_contour_xld`) `contour → region` GPU: 无 — 将 XLD 轮廓栅格化并转换为 region。相当于 HALCON 的 ``gen_region_contour_xld``（Create a region from an XLD contour.）。 · 示例: `gallery2d_contour_measure`, `quickstart`
- `edges_color_sub_pix` (halcon: `edges_color_sub_pix`) `color → contour` GPU: 有(许可列表) — 提取彩色边缘上的连通分量作为轮廓（contour）。据称相当于 HALCON 的 ``edges_color_sub_pix``（以 Deriche/Shen/Canny 提取亚像素精度的彩色边缘），但**实现并非亚像素精度**——将 ``_edges_color`` 的梯度强度阈值化为二值图像，用 8 连通标记（``scipy.ndimage.label``）连接后，将得到的像素坐标直接作为轮廓点返回（坐标全部位于整数网格上）。舍弃 3 像素以下的分量。 · 示例: `gallery2d_contour_measure`
- `edges_sub_pix` (halcon: `edges_sub_pix`) `image → contour` GPU: 有(许可列表) — 亚像素精度的边缘轮廓提取。求出梯度及其法线方向(``gradient_normals``),用非极大值抑制(与 Canny 相同,仅保留沿法线方向强于两侧的像素)细化为单像素宽,把超过阈值(``0.15+0.5*a``,按最大梯度归一化的强度)的像素连接成**沿曲线排序的轮廓**(在分支点处拆分为不同轮廓,闭合边缘在起点闭合),再用抛物线拟合沿法线把各点精细化到亚像素位置(``subpixel_refine_edges``,与 ``ops`` 侧同名 op 共享的实现 —— 经 2026-09-02 的修复才成为真正的亚像素;旧实现直接返回整数像素坐标)。相当于 HALCON 的 ``edges_sub_pix``(Extract sub-pixel precise edges using Deriche, Lanser, Shen, or Canny filters.)。 · 示例: `gallery2d_contour_measure`, `quickstart`
- `fit_line_contours` (halcon: `fit_line_contour_xld`) `contour → contour` GPU: 无 — 用一条直线近似每条 XLD 轮廓。相当于 HALCON 的 ``fit_line_contour_xld``（Approximate XLD contours by line segments.）。 · 示例: `gallery2d_contour_measure`, `poc_screw_thread_metrology`
- `gen_contour_region_xld` (halcon: `gen_contour_region_xld`) `region → contour` GPU: 无 — 将 region（像素掩膜）的外周作为保留追踪顺序（沿轮廓的顺序）的 XLD 轮廓提取出来。使用 ``find_contours``（通过 marching squares 实现的亚像素轮廓）。没有 scikit-image 时以 ``MissingDependencyError`` 停止（2026-10-25 之前会悄悄回退到自实现的 Moore 邻域追踪——像素分辨率、点数和坐标都不同的另一种轮廓；该追踪仍可按名称 ``backends_auto._moore_boundaries`` 调用）。a、b 未使用。 · 示例: `gallery2d_contour_measure`
- `gen_region_contour_xld` (halcon: `gen_region_contour_xld`) `contour → region` GPU: 无 — 将轮廓(点列)光栅化到像素网格上,再进行 ``1+2*a`` 次二值膨胀使其变粗,生成相连的区域掩码(这是一种加强处理,因为若保持细线状态,在 ``region`` 的 {0,1} 契约下可能出现"线看起来没有连接"的情况)。相当于 HALCON 的 ``gen_region_contour_xld``(Create a region from an XLD contour.)。 · 示例: `gallery2d_contour_measure`
- `gen_region_polygon_xld` (halcon: `gen_region_polygon_xld`) `contour → region` GPU: 无 — 将 XLD 轮廓（多边形的顶点序列）转换为 region（像素掩膜）。将轮廓点标记到最近的像素后，通过 ``1+2a`` 次二值膨胀（dilation）使线条变粗并连接起来。b 未使用。 · 示例: `gallery2d_contour_measure`
- `lines_color` (halcon: `lines_color`) `color → contour` GPU: 有(许可列表) — 检测彩色图像中的线（脊线）。据称相当于 HALCON 的 ``lines_color``（检测彩色线及其宽度），但**不估计线宽**——只是将亮度图像上的高斯拉普拉斯响应阈值化为二值图像，并将连通分量作为轮廓返回，没有相当于 HALCON 返回值中线宽的输出。 · 示例: `gallery2d_contour_measure`
- `lines_facet` (halcon: `lines_facet`) `image → contour` GPU: 无 — 检测线状结构（脊线）并作为轮廓（XLD contour）返回。实现通过 Frangi 滤波器（``skimage.filters.frangi``，多尺度 σ=1..3 的脊线增强）求出线状程度，将超过阈值 ``0.1+0.4a`` 的连通分量的像素坐标直接作为轮廓点序列输出。b 未使用。 · 示例: `gallery2d_contour_measure`
- `lines_gauss` (halcon: `lines_gauss`) `image → contour` GPU: 无 — 线状结构(脊线)检测。将 ``skimage.filters.frangi``(类血管脊线增强滤波器)的响应用阈值(``0.1+0.4*a``)二值化,并将连通成分作为轮廓点集返回。这是简化为对脊线增强图像做阈值化,而非 HALCON 的 ``lines_gauss``(Detect lines and their width.)本来所做的"线的中心线+宽度估计"(不返回线宽信息的近似)。 · 示例: `example_scratch_width`, `gallery2d_contour_measure`, `poc_solar_el_inspection`, `poc_weld_bead_scan_angle`
- `polar_trans_contour_xld` (halcon: `polar_trans_contour_xld`) `contour → contour` GPU: 无 — 将轮廓的各点从图像中心转换为极坐标（半径、角度），再重新打包为伪像素坐标（半径以 H、W 中较大者缩放，角度映射到 [0,1]）。是对应 HALCON ``polar_trans_contour_xld``（Transform a contour in an annular arc to polar coordinates.）的简化坐标变换。 · 示例: `gallery2d_contour_measure`
- `projective_trans_contour_xld` (halcon: `projective_trans_contour_xld`) `contour → contour` GPU: 无 — 对轮廓的各点施加依列位置而定的伪透视收缩（用 ``d = 1 + 0.3*a*(col - 中心)/宽度`` 去除以各点坐标）。注意这并非通过真正的 3x3 单应性矩阵实现的射影变换，而是用单方向的简易缩放来近似。用作 HALCON ``projective_trans_contour_xld``（Apply a projective transformation to an XLD contour.）的替代。 · 示例: `gallery2d_contour_measure`
- `select_contours` (halcon: `select_contours_xld`) `contour → contour` GPU: 无 — 按点数（长度）过滤以筛选 XLD 轮廓。相当于 HALCON 的 ``select_contours_xld``（Select XLD contours according to several features.）。 · 示例: `gallery2d_contour_measure`, `quickstart`
- `select_contours_xld` (halcon: `select_contours_xld`) `contour → contour` GPU: 无 — 从现有的轮廓(XLD contour)集合中,只保留点数达到阈值(``3+40*a``)以上的滤波器。HALCON 的 ``select_contours_xld``(Select XLD contours according to several features.)是可以用面积、圆形度等任意特征进行筛选的通用算子,但这个代替实现固定为按点数(作为长度的替代指标)截断这一种(近似)。 · 示例: `gallery2d_contour_measure`
- `select_shape_xld` (halcon: `select_shape_xld`) `contour → contour` GPU: 无 — 剔除点数过少的 XLD 轮廓的过滤器。去除顶点数少于 ``3+40a`` 点的轮廓。b 未使用。 · 示例: `gallery2d_contour_measure`
- `shape_trans_xld` (halcon: `shape_trans_xld`) `contour → contour` GPU: 无 — 计算轮廓的凸包（``cv2.convexHull``）并以轮廓形式返回（是 ``shape_trans`` 的轮廓版）。在 HALCON ``shape_trans_xld``（Transform the shape of contours or polygons.）所拥有的多种变形模式中，仅实现了凸包这一种（近似）。 · 示例: `gallery2d_contour_measure`
- `sk_find_contours` `image → contour` GPU: 无 — 等高线提取(marching squares)。在灰度图像上追踪与指定阶层值相交的曲线,并以子像素精度的轮廓坐标序列集合的形式返回 —— 与二值轮廓提取不同之处在于,它不仅能处理二值图像的外周,还能处理连续值的等高线。 · 示例: `gallery2d_bridge`, `gallery2d_contour_measure`
- `smooth_contours` (halcon: `smooth_contours_xld`) `contour → contour` GPU: 无 — 使用移动平均平滑 XLD 轮廓。相当于 HALCON 的 ``smooth_contours_xld``（Smooth an XLD contour.）。 · 示例: `gallery2d_contour_measure`
- `smooth_contours_xld` (halcon: `smooth_contours_xld`) `contour → contour` GPU: 无 — 以移动平均(窗宽 ``2*(1+3*a)+1``)平滑轮廓的坐标序列。使轮廓的锯齿(由像素边界产生的锯齿状)变得平滑。相当于 HALCON 的 ``smooth_contours_xld``(Smooth an XLD contour.)。 · 示例: `gallery2d_contour_measure`
- `threshold_sub_pix` (halcon: `threshold_sub_pix`) `image → contour` GPU: 无 — 用行进方块法（marching squares，``skimage.measure.find_contours``）提取水平交叉（等值线）。以子像素精度返回穿过指定灰阶等级（``0.2+0.5*a``）位置的轮廓。相当于 HALCON 的 ``threshold_sub_pix``（Extract level crossings from an image with subpixel accuracy.）。 · 示例: `fit_circle_xld_bore`, `gallery2d_contour_measure`, `mcp_task_score`, `poc_peg_insertion_tactile`, `poc_screw_thread_metrology`
- `zero_crossing_sub_pix` (halcon: `zero_crossing_sub_pix`) `image → contour` GPU: 无 — 用 ``find_contours`` 将 LoG（内含高斯平滑的拉普拉斯，sigma 为 ``0.5+2*a``）的过零点提取为具有子像素精度的轮廓。是区域版 ``zero_crossing``（像素级分辨率）的子像素精度版本。相当于 HALCON 的 ``zero_crossing_sub_pix``（Extract zero crossings from an image with subpixel accuracy.）。 · 示例: `gallery2d_contour_measure`

#### 2d / decomposition (7)
- `dc_homomorphic` `image → image` GPU: 有(许可列表) — 同态滤波：在傅里叶域对 log(I) 进行高频强调 -> [0,1]。 · 示例: `gallery2d_texture_freq`, `poc_document_scan`, `poc_mri_bias_field`
- `dc_local_contrast_norm` `image → image` GPU: 有(dc_local_contrast_norm) — 局部对比度归一化：(I - mean_w) / (std_w + eps)，以 0.5 为中心。 · 示例: `gallery2d_texture_freq`
- `dc_retinex` `image → image` GPU: 有(许可列表) — 单尺度 Retinex 反射率：log(I) - log(Gauss_sigma(I)) -> [0,1]。 · 示例: `gallery2d_texture_freq`, `poc_bone_trabecular_thickness`
- `dc_rpca_lowrank` `image → image` GPU: 无 — 鲁棒 PCA 的低秩（背景）部分。 · 示例: `blas_thread_budget`, `gallery2d_texture_freq`
- `dc_rpca_sparse` `image → image` GPU: 无 — 鲁棒 PCA 的稀疏（缺陷／异常）残差 = 输入 - 低秩，位于 0.5。 · 示例: `gallery2d_texture_freq`, `poc_good_sample_variation_model`
- `dc_structure_texture` `image → image` GPU: 有(许可列表) — 图像的结构／卡通部分（TV-L2，Chambolle）。 · 示例: `gallery2d_texture_freq`, `poc_fiber_orientation`
- `dc_texture_residual` `image → image` GPU: 有(许可列表) — 纹理／细节层 = 输入 - 结构，以 0.5 为中心。 · 示例: `gallery2d_texture_freq`

#### 2d / deformation (3)
- `deform_ffd` `image → image` GPU: 有(许可列表) — 三次 B 样条自由变形(free-form deformation,Rueckert 等,IEEE TMI 1999)。 · 示例: `gallery2d_geometry`
- `deform_mls` `image → image` GPU: 无 — 移动最小二乘(moving-least-squares)图像变形,仿射变体(Schaefer 2006)。 · 示例: `gallery2d_geometry`
- `deform_tps` `image → image` GPU: 有(许可列表) — 基于 5x5 控制网格的薄板样条(thin-plate spline)扭曲(Bookstein,TPAMI 1989)。 · 示例: `gallery2d_geometry`

#### 2d / domain (2)
- `it_crop_domain` (halcon: `crop_domain`) `image → image` GPU: 有(许可列表) — crop_domain:将图像定义域限制在居中的 ``a`` 窗口内,窗口外的所有像素置零(定义域之外的像素未定义 -> 0)。``a`` 设置保留窗口的比例;``b`` 被忽略。 · 示例: `gallery2d_gray_arith`
- `it_full_domain` `image → image` GPU: 仅在链中(许可列表) — full_domain:将图像的定义域扩展到完整矩形。普通的 numpy 数组本身就已具有完整定义域,因此这里就是恒等变换 —— 这正是 full_domain 对这类图像的真实、正确行为。``a``/``b`` 被忽略。 · 示例: `gallery2d_gray_arith`

#### 2d / edges (59)
- `corner_response` (halcon: `points_harris`) `image → image` GPU: 有(corner_response) — 以图像形式返回 Harris 角点检测的响应值（角点程度）。相当于 HALCON 的 ``points_harris``（Detect points of interest using the Harris operator.）。 · 示例: `gallery2d_edges`, `poc_document_scan`, `poc_matrix_code_reading`
- `cv_corner_harris` (halcon: `points_harris`) `image → image` GPU: 无 — Harris 角点响应（OpenCV 实现）。与 sk_corner_harris 相同的 Harris 思路，但 OpenCV 版本以固定参数（如梯度计算、平滑的区块大小等）来计算。 · 示例: `gallery2d_edges`
- `cv_laplacian` (halcon: `laplace`) `image → image` GPU: 无 — 拉普拉斯滤波器（OpenCV 实现）。基于二阶微分的各向同性边缘/斑点检测，不仅对轮廓，对孤立点也会有强烈反应（因此对噪声也很敏感）。 · 示例: `gallery2d_edges`
- `cv_min_eigen` (halcon: `points_harris`) `image → image` GPU: 无 — 基于最小特征值的角点强度（Shi-Tomasi 系列，OpenCV 实现）。返回梯度结构张量两个特征值中较小的一个 —— 不像 Harris 那样带有权重（依赖 k），能更直接地衡量「良好特征点」的程度（与 cv_good_features 内部使用的判断标准同类）。 · 示例: `gallery2d_edges`
- `cv_precorner` (halcon: `corner_response`) `image → image` GPU: 无 — 角点候选检测（preCornerDetect，OpenCV 实现）。用结合一阶和二阶微分的特殊公式，将角点程度打成带符号的分数 —— 原本是作为 ``cv2.cornerSubPix`` 亚像素精细化前置候选检测的函数。 · 示例: `gallery2d_edges`
- `cv_scharr` (halcon: `edges_image`) `image → image` GPU: 无 — Scharr 梯度幅值（OpenCV 实现）。将水平方向与垂直方向的 Scharr 微分的绝对值相加得到梯度强度 —— 与 sk_scharr（skimage 版本）属于同类边缘检测，但合成方式不同（是绝对值之和，而不是平方和的范数），因此结果不会完全一致。 · 示例: `gallery2d_edges`
- `derivate_gauss` (halcon: `derivate_gauss`) `image → image` GPU: 有(derivate_gauss) — 将高斯导数(``order=(1,0)`` 与 ``(0,1)``)的梯度强度(``hypot``)归一化到 [0,1]。由于先用高斯平滑再求导,因此可作为抗噪声的边缘检测器使用。相当于 HALCON 的 ``derivate_gauss``(Convolve an image with derivatives of the Gaussian.)。 · 示例: `gallery2d_edges`
- `diff_of_gauss` (halcon: `diff_of_gauss`) `image → image` GPU: 有(diff_of_gauss@twin) — 通过 DoG(Difference of Gaussians,即用两种不同 sigma 模糊后的图像之差)实现的带通边缘/斑点检测。这是一种作为 LoG 快速近似而广为人知的经典方法。相当于 HALCON 的 ``diff_of_gauss``(Approximate the LoG operator (Laplace of Gaussian).)。 · 示例: `gallery2d_edges`
- `dog` (halcon: `diff_of_gauss`) `image → image` GPU: 有(diff_of_gauss) — 高斯差分（Difference of Gaussians, DoG）。相当于 HALCON 的 ``diff_of_gauss``（Approximate the LoG operator (Laplace of Gaussian).）。 · 示例: `gallery2d_edges`
- `dots_image` (halcon: `dots_image`) `image → image` GPU: 有(许可列表) — 高斯拉普拉斯（Laplacian of Gaussian, LoG）滤波器。以 σ = 0.5+2.5a 的高斯核取拉普拉斯，并以 signed01（将带符号的值映射到 [0,1]，0.5 表示零响应）归一化。b 未使用。由于圆形点状图案（点）会因高斯核的各向同性而产生强烈的 LoG 响应，因此可用于增强圆形点。 · 示例: `gallery2d_edges`
- `edge_transition_width` `image → image` GPU: 有(许可列表) — 以像素为单位测量**边缘过渡宽度**(= 该处有效 PSF 的展宽)。 · 示例: `gallery2d_edges`
- `edges_color` (halcon: `edges_color`) `color → image` GPU: 有(许可列表) — 检测彩色边缘的强度。据称相当于 HALCON 的 ``edges_color``（用 Canny/Deriche/Shen 滤波器提取彩色边缘），但**实现固定为 Di Zenzo 的多通道梯度法，而非可选滤波器方式**。 · 示例: `gallery2d_edges`
- `f2_shock` (halcon: `shock_filter`) `image → image` GPU: 无 — Osher-Rudin 冲击滤波器：I_t = -sign(Lap I)*|grad I|，形态学形式。 · 示例: `gallery2d_edges`
- `f2_shock_diffuse` `image → image` GPU: 无 — 正则化的冲击滤波 —— 先扩散再冲击，如此反复（Alvarez–Mazorra）。 · 示例: `gallery2d_edges`
- `f2_topographic` (halcon: `topographic_sketch`) `image → image` GPU: 有(许可列表) — Haralick 地形基元素描：根据每个像素的梯度幅值和两个 Hessian 特征值的符号，将其分类为峰(peak)/坑(pit)/脊(ridge)/谷(ravine)/鞍(saddle)/平坦(flat)/坡(hillside)之一，并将该类别以灰度码形式输出。 · 示例: `gallery2d_edges`
- `frei_amp` (halcon: `frei_amp`) `image → image` GPU: 有(许可列表) — Frei-Chen 等向性边缘检测。由带权重 ``√2`` 的两个核对通过 ``hypot`` 求出振幅 —— 这是一种被认为比 Sobel 各方向灵敏度差异更小(即更具等向性)的经典核。相当于 HALCON 的 ``frei_amp``(Detect edges (amplitude) using the Frei-Chen operator.)。 · 示例: `gallery2d_edges`
- `frei_dir` (halcon: `frei_dir`) `image → image` GPU: 有(许可列表) — 使用 Frei-Chen 型核的边缘方向（角度）图。由水平核 ``_FREI[0]``（行/纵向梯度）与垂直核 ``_FREI[1]``（列/横向梯度）的卷积响应计算 ``arctan2(gy, gx)``，并按照与 ``sobel_dir``/``prewitt_dir`` 相同的约定映射到 [0,1]（0/1 对应 -180°，0.5 对应 0°）。a、b 未使用。 · 示例: `gallery2d_edges`
- `grad_dir` `image → image` GPU: 有(gradient_direction) — 以图像形式返回梯度方向（边缘朝向）。未指定对应的 HALCON 算子（fullseye 独有）。 · 示例: `gallery2d_edges`
- `kirsch_amp` (halcon: `kirsch_amp`) `image → image` GPU: 有(许可列表) — Kirsch 罗盘滤波器的振幅。用旋转至 8 个方向的一组核分别做卷积,取绝对值的最大值,从而获得与方向无关的强边缘响应。相当于 HALCON 的 ``kirsch_amp``(Detect edges (amplitude) using the Kirsch operator.)。 · 示例: `gallery2d_edges`
- `kirsch_dir` (halcon: `kirsch_dir`) `image → image` GPU: 无 — 返回 Kirsch 罗盘滤波器中响应最强方向的索引(8 个方向中的 ``argmax``),并归一化到 [0,1]。是与 ``kirsch_amp`` 成对的方向分量。相当于 HALCON 的 ``kirsch_dir``(Detect edges (amplitude and direction) using the Kirsch operator.)。 · 示例: `gallery2d_edges`
- `laplace` (halcon: `laplace`) `image → image` GPU: 有(laplace) — 拉普拉斯算子(``ndimage.laplace``,通过有限差分计算的二阶导数)的绝对值归一化结果。这是一种无方向性的二阶导数边缘检测,比Sobel系滤波器对高频噪声更敏感。相当于HALCON的``laplace``(Calculate the Laplace operator by using finite differences.)。 · 示例: `gallery2d_edges`, `poc_focus_stacking`, `poc_search_sweep_width`, `poc_white_balance`
- `laplace_of_gauss` (halcon: `laplace_of_gauss`) `image → image` GPU: 仅在链中(许可列表) — LoG(Laplacian of Gaussian,即高斯平滑后再施加拉普拉斯算子的二阶导数边缘检测)。通过 ``signed01`` 将带符号的响应映射到 [0,1] (0.5 对应零交叉),可作为零交叉检测或斑点检测的基础。相当于 HALCON 的 ``laplace_of_gauss``(LoG-Operator (Laplace of Gaussian).)。 · 示例: `gallery2d_edges`, `poc_real_defect_floor`
- `log` (halcon: `laplace_of_gauss`) `image → image` GPU: 有(许可列表) — 高斯拉普拉斯（Laplacian of Gaussian, LoG）滤波器。相当于 HALCON 的 ``laplace_of_gauss``（LoG-Operator (Laplace of Gaussian).）。 · 示例: `gallery2d_edges`, `gallery_spectrum_signal_bridge`, `poc_colormap_readability`, `poc_datacenter_thermal_field`, `poc_dehazing`, `poc_driving_longitudinal`, `poc_emva1288_in_camera_processing`, `poc_eye_to_brain`, `poc_pocket_interreflection`, `poc_powder_grinding_ae`, `poc_registration_basin`, `poc_simcal_pixel_shift`, `poc_simcal_thin_film`, `poc_wound_area_tracking`, `simcal_checks_tour`, `simcal_tour`
- `points_foerstner` (halcon: `points_foerstner`) `image → image` GPU: 无 — 基于 Förstner 算子的角点强度图（``skimage.feature.corner_foerstner`` 的权重 ``w`` 与稳健形状指标 ``q`` 之积，NaN 替换为 0）。通过组合误差椭圆的大小（w）与其圆度（q）来评估某位置的点特征程度。相当于 HALCON 的 ``points_foerstner``（Detect points of interest using the Förstner operator.）。 · 示例: `gallery2d_edges`
- `points_harris_binomial` (halcon: `points_harris_binomial`) `image → image` GPU: 无 — 在前段插入二项式（高斯）平滑的 Harris 角点响应。先用由 ``b`` 决定的 sigma 对图像平滑，再在此基础上求 Harris 响应（若有 skimage 则用 ``corner_harris``，否则手动计算结构张量，k=0.04）。相当于 HALCON 的 ``points_harris_binomial``（Detect points of interest using the binomial approximation of the Harris operator.）。 · 示例: `gallery2d_edges`
- `prewitt_amp` (halcon: `prewitt_amp`) `image → image` GPU: 有(prewitt_amp@twin) — Prewitt 梯度的振幅。与 Sobel 同为一阶微分,但使用权重均匀(``[1,1,1]``)的核 —— 比 Sobel 略易受噪声影响,但计算更简单。相当于 HALCON 的 ``prewitt_amp``(Detect edges (amplitude) using the Prewitt operator.)。 · 示例: `gallery2d_edges`, `poc_white_balance`
- `prewitt_dir` (halcon: `prewitt_dir`) `image → image` GPU: 无 — Prewitt 梯度的方向。是与 ``prewitt_amp`` 成对的方向分量(``arctan2`` 映射到 [0,1])。相当于 HALCON 的 ``prewitt_dir``(Detect edges (amplitude and direction) using the Prewitt operator.)。 · 示例: `gallery2d_edges`
- `prewitt_mag` (halcon: `prewitt_amp`) `image → image` GPU: 有(prewitt_amp) — 通过 Prewitt 滤波器计算梯度幅值（边缘检测）。相当于 HALCON 的 ``prewitt_amp``（Detect edges (amplitude) using the Prewitt operator.）。 · 示例: `find_ops_by_meaning`, `gallery2d_edges`
- `roberts` (halcon: `roberts`) `image → image` GPU: 有(roberts) — Roberts 交叉算子。这是尺寸最小的边缘检测核,通过 2x2 的对角差分(左上−右下、右上−左下)以 ``hypot`` 求出振幅。对斜向边缘敏感,但对噪声也敏感。相当于 HALCON 的 ``roberts``(Detect edges using the Roberts filter.)。 · 示例: `find_ops_by_meaning`, `gallery2d_edges`, `poc_white_balance`
- `roberts_mag` (halcon: `roberts`) `image → image` GPU: 有(roberts_amp) — 通过 Roberts 交叉梯度计算梯度幅值（边缘检测）。相当于 HALCON 的 ``roberts``（Detect edges using the Roberts filter.）。 · 示例: `find_ops_by_meaning`, `gallery2d_edges`
- `robinson_amp` (halcon: `robinson_amp`) `image → image` GPU: 有(许可列表) — Robinson 罗盘滤波器的振幅。将 2 个基础核各旋转 4 次,共计 8 个核分别做卷积,取绝对值的最大值(与 Kirsch 思路相同的罗盘法)。相当于 HALCON 的 ``robinson_amp``(Detect edges (amplitude) using the Robinson operator.)。 · 示例: `gallery2d_edges`
- `robinson_dir` (halcon: `robinson_dir`) `image → image` GPU: 有(许可列表) — 使用 Robinson 罗盘算子的边缘方向图。在 8 个方向（每 45° 旋转一次的 ``_ROBINSON[0]``/``_ROBINSON[1]`` 核，共 8 个）的卷积响应中选出最大者，并将该核的编号归一化到 0〜1 返回。a、b 未使用。 · 示例: `gallery2d_edges`
- `sk_corner_harris` (halcon: `points_harris`) `image → image` GPU: 无 — Harris 角点响应(skimage 实现)。这是一种经典的角点检测器,根据梯度的结构张量计算出用于区分平坦区域/边缘/角点的带符号分数。 · 示例: `gallery2d_edges`
- `sk_dog` (halcon: `diff_of_gauss`) `image → image` GPU: 无 — DoG（Difference of Gaussians，高斯差分）滤波器。取用两个不同 σ 模糊后的图像之差，以低成本获得接近 LoG（Laplacian of Gaussian）的带通响应（只强调特定空间频率带的边缘/斑点检测）。 · 示例: `gallery2d_edges`
- `sk_farid` (halcon: `edges_image`) `image → image` GPU: 无 — Farid-Simoncelli 梯度大小。直接调用 skimage 的 ``filters.farid``。这是通过经过优化的 5 抽头微分核得到的梯度强度，据称其旋转对称性（方向误差）比 Sobel/Scharr 更小。 · 示例: `gallery2d_edges`
- `sk_hessian_det` `image → image` GPU: 无 — 基于 Hessian 行列式的斑点(blob)检测响应。二阶导数矩阵(Hessian)的行列式是一种带符号的响应值,在斑点状结构处为正,在鞍点状结构处为负。 · 示例: `gallery2d_edges`
- `sk_scharr` (halcon: `edges_image`) `image → image` GPU: 无 — Scharr 梯度大小。直接调用 skimage 的 ``filters.scharr``，返回合成水平/垂直各自 Scharr 核（3x3）响应后得到的梯度强度。 · 示例: `gallery2d_edges`
- `sobel_amp` (halcon: `sobel_amp`) `image → image` GPU: 有(sobel_amp@twin) — Sobel 梯度的振幅(``hypot(sobel_x, sobel_y)`` 归一化)。由纵、横两个一阶微分核求出梯度向量大小,是最基本的边缘检测方法。相当于 HALCON 的 ``sobel_amp``(Detect edges (amplitude) using the Sobel operator.)。 · 示例: `degenerate_inputs`, `find_ops_by_meaning`, `gallery2d_edges`, `genspark_external_review`, `poc_fiber_orientation`, `poc_focus_stacking`, `poc_real_coin_metrology`, `poc_white_balance`
- `sobel_dir` (halcon: `sobel_dir`) `image → image` GPU: 有(sobel_dir) — Sobel 梯度的方向(``arctan2(dy, dx)`` 映射到 [0,1],0=-π,1=+π)。与返回振幅的 ``sobel_amp`` 成对,用于求边缘走向的运算。相当于 HALCON 的 ``sobel_dir``(Detect edges (amplitude and direction) using the Sobel operator.)(HALCON 同时返回振幅与方向,这里则将方向拆分为独立的 op)。 · 示例: `gallery2d_edges`, `poc_document_scan`, `poc_fiber_orientation`
- `sobel_mag` (halcon: `sobel_amp`) `image → image` GPU: 有(sobel_amp) — 通过 Sobel 滤波器计算梯度幅值（边缘检测）。相当于 HALCON 的 ``sobel_amp``（Detect edges (amplitude) using the Sobel operator.）。 · 示例: `find_ops_by_meaning`, `gallery2d_edges`, `poc_real_sem_metal_layer`
- `tf_phase_congruency` `image → image` GPU: 有(许可列表) — phase_congruency：简化版的单演（monogenic）相位一致性特征图。 · 示例: `gallery2d_edges`, `poc_iqa_fsim_gmsd_vif`
- `tf_steerable_filter` `image → image` GPU: 有(许可列表) — steerable_filter：方向可控的高斯一阶导数响应。 · 示例: `gallery2d_edges`
- `xdog` `image → image` GPU: 有(许可列表) — XDoG（扩展高斯差分，Winnemoller、Kyprianidis、Olsen 2012）：线稿、水墨风格的风格化。 · 示例: `gallery2d_edges`
- `xkor_dog` `image → image` GPU: 无 — DoG(Difference of Gaussians)斑点响应。以默认参数调用 ``kornia.feature.dog_response_single``(若不存在则回退到 ``dog_response``)，取绝对值后按最大绝对值归一化。 · 示例: `gallery2d_edges`
- `xkor_gftt` `image → image` GPU: 无 — GFTT(Good Features To Track，Shi-Tomasi)角点响应。以默认参数调用 ``kornia.feature.gftt_response``，取绝对值后按最大绝对值归一化。 · 示例: `gallery2d_edges`
- `xkor_harris` `image → image` GPU: 无 — Harris 角点响应。调用 ``kornia.feature.harris_response``，用 ``signed01`` 将带符号的响应映射到 [0,1] (在保留 Harris 响应符号信息——角点为正、边缘为负——的同时将其收入可视化范围)。 · 示例: `gallery2d_edges`
- `xkor_hessian` `image → image` GPU: 无 — 由 Hessian 矩阵的行列式 det H = Ixx·Iyy − Ixy² 得到的斑点/角点响应。以不归一化（``normalized=False``）的方式应用 ``kornia.filters.spatial_gradient`` 的 5x5 Sobel 二阶导数核并除以 64（在二次、三次曲面上恰好得到导数本身），边界复制，取绝对值后按最大绝对值归一化。 · 示例: `gallery2d_edges`
- `xkor_laplacian` `image → image` GPU: 无 — 基于拉普拉斯算子(二阶导数)的边缘/斑点响应。调用 ``kornia.filters.laplacian``，取绝对值后按最大绝对值归一化。 · 示例: `gallery2d_edges`
- `xpil_contour` `image → image` GPU: 无 — Pillow 的轮廓提取滤镜。使用 ``PIL.ImageFilter.CONTOUR`` 的固定卷积核，制造出仅在白色背景上留下黑色轮廓线的效果（钢笔画/线稿风格效果）。 · 示例: `gallery2d_edges`
- `xpil_find_edges` `image → image` GPU: 无 — Pillow 的边缘检测滤镜。使用 ``PIL.ImageFilter.FIND_EDGES`` 的固定卷积核（拉普拉斯系）来增强边缘。 · 示例: `find_ops_by_meaning`, `gallery2d_edges`
- `xsk2_corner_kr` `image → image` GPU: 无 — Kitchen-Rosenfeld 角点检测响应。调用 ``skimage.feature.corner_kitchen_rosenfeld``，将 NaN 替换为 0 后，通过 ``signed01`` 将带符号响应映射到 [0,1]。 · 示例: `gallery2d_edges`
- `xsk2_inv_gauss_grad` `image → image` GPU: 无 — 逆高斯梯度图像（用于主动轮廓 / GAC 的边缘停止函数）。调用``skimage.segmentation.inverse_gaussian_gradient``。 · 示例: `gallery2d_edges`
- `xsk3_corner_fast` `image → image` GPU: 无 — FAST 角点检测(skimage ``feature.corner_fast``)。一种与中心像素周围圆周上的像素进行比较、将连续更亮/更暗的像素达到一定数目以上的位置检测为角点的快速方法。结果为按最大绝对值归一化的响应图。 · 示例: `gallery2d_edges`
- `xsk3_corner_moravec` `image → image` GPU: 无 — Moravec 角点检测(skimage ``feature.corner_moravec``)。将以各像素为中心的小窗口在上下左右及对角方向平移时得到的像素值差异的最小值作为角点强度，是最经典的角点检测方法之一(Harris/Shi-Tomasi 的前身)。结果按最大绝对值归一化。 · 示例: `gallery2d_edges`
- `xsk_hessian_eig` `image → image` GPU: 无 — 基于 Hessian 矩阵最大特征值（绝对值）的斑点/脊线强度。 · 示例: `gallery2d_edges`
- `xsp_gauss_grad_mag` `image → image` GPU: 有(许可列表) — 通过高斯梯度幅值（``scipy.ndimage.gaussian_gradient_magnitude``）进行边缘检测。 · 示例: `find_ops_by_meaning`, `gallery2d_edges`
- `xsp_morph_laplace` `image → image` GPU: 有(许可列表) — 通过形态学拉普拉斯算子（``scipy.ndimage.morphological_laplace``）进行边缘增强。 · 示例: `gallery2d_edges`
- `xwt_directional_detail` `image → image` GPU: 无 — 方向性边缘检测。从单层``db2``分解中选取水平(cH)、垂直(cV)、对角(cD)三个细节子带之一，对其绝对值做归一化，再以块状放大（用``kron``做2x2复制）恢复到原始分辨率后返回。 · 示例: `gallery2d_edges`
- `xwt_hf_reconstruct` `image → image` GPU: 无 — 高频重建图像。用``db2``做2层分解，将近似系数（低频成分）归零后再逆变换重建 —— 结果类似经过高通滤波，只保留边缘与纹理。重建后做min-max归一化。 · 示例: `gallery2d_edges`

#### 2d / extra (14)
- `xsitk_closing_by_recon` `image → image` GPU: 无 — 重建闭运算（SimpleITK ``ClosingByReconstruction``，xsitk_opening_by_recon的对偶）。膨胀后的腐蚀改用带掩码的重建来进行，在保持轮廓的同时只填补小的暗色凹陷。 · 示例: `gallery2d_color_artistic`
- `xsitk_confidence_connected` `image → region` GPU: 无 — 置信区间连通区域生长（SimpleITK ``ConfidenceConnected``）。以图像中心为种子，根据当前区域内的均值与标准差构造「均值±multiplier*标准差」的区间，并在反复更新该区间的同时扩展连通区域（比xsitk_connected_threshold更统计化的阈值确定方式）。 · 示例: `gallery2d_color_artistic`
- `xsitk_connected_threshold` `image → region` GPU: 无 — 连通阈值区域生长（SimpleITK ``ConnectedThreshold``，region growing）。以图像中心像素为种子（seed），仅将落在以该像素值为中心的强度区间内且与中心相连通的像素扩展为区域。 · 示例: `gallery2d_color_artistic`
- `xsitk_curv_aniso_diff` `image → image` GPU: 无 — 曲率各向异性扩散（SimpleITK ``CurvatureAnisotropicDiffusion``）。属于Perona-Malik型各向异性扩散的一种，在边缘（梯度大的位置）抑制扩散，在平坦处充分扩散，从而在保留边缘的同时进行平滑。 · 示例: `gallery2d_color_artistic`
- `xsitk_curvature_flow` `image → image` GPU: 无 — 曲率流平滑（SimpleITK ``CurvatureFlow``）。一种以等高线曲率成比例的速度模糊图像的非线性扩散，直线状边缘容易被保留，而弯曲的细节会先消失。 · 示例: `gallery2d_color_artistic`
- `xsitk_grayscale_fillhole` `image → image` GPU: 无 — 灰度填洞（SimpleITK ``GrayscaleFillhole``）。通过形态学重建，将图像中的暗孔（比周围暗的局部凹陷）填补至周围亮度水平。是二值填洞的灰度版本，用于去斑或缺损补全等前处理。 · 示例: `gallery2d_color_artistic`
- `xsitk_grayscale_grindpeak` `image → image` GPU: 无 — 灰度削峰（SimpleITK ``GrayscaleGrindPeak``，xsitk_grayscale_fillhole的对偶）。通过形态学重建，将比周围亮的局部峰值削低到周围高度。用于去除高光尖峰。 · 示例: `gallery2d_color_artistic`, `poc_weld_radiograph_porosity`
- `xsitk_huang_thresh` `image → region` GPU: 无 — 基于 Huang 模糊熵法的二值化(SimpleITK ``HuangThreshold``)。将前景/背景视为模糊集合，选择使其模糊性(模糊熵)最小的阈值。 · 示例: `gallery2d_color_artistic`, `threshold_family_agreement`
- `xsitk_laplacian_sharpen` `image → image` GPU: 无 — 拉普拉斯锐化（SimpleITK ``LaplacianSharpening``）。通过从图像中减去拉普拉斯（二阶导数）来增强边缘的一种反锐化蒙版。返回结果前做min-max归一化。 · 示例: `gallery2d_color_artistic`
- `xsitk_maxentropy_thresh` `image → region` GPU: 无 — 最大熵法二值化（SimpleITK ``MaximumEntropyThreshold``，Kapur方法）。一种全局二值化方法，选取使直方图分为前景/背景两类时熵之和最大的阈值。 · 示例: `gallery2d_color_artistic`, `mcp_task_score`, `threshold_family_agreement`
- `xsitk_minmax_curv_flow` `image → image` GPU: 无 — Min/Max曲率流平滑（SimpleITK ``MinMaxCurvatureFlow``）。在与xsitk_curvature_flow相同的曲率流基础上，加入基于邻域最小值/最大值的判断，在平滑的同时填补小孔和斑点噪声的变体。 · 示例: `gallery2d_color_artistic`, `genspark_external_review`
- `xsitk_moments_thresh` `image → region` GPU: 无 — 矩保持法二值化（SimpleITK ``MomentsThreshold``，Tsai方法）。选取阈值使二值化后直方图的统计矩（均值、方差等）与原始直方图的统计矩一致。 · 示例: `gallery2d_color_artistic`, `threshold_family_agreement`
- `xsitk_opening_by_recon` `image → image` GPU: 无 — 重建开运算（SimpleITK ``OpeningByReconstruction``）。与普通灰度开运算（腐蚀→膨胀）不同，腐蚀后的膨胀改用带掩码的重建来进行，因此能够只去除小的明亮突起，而不扭曲保留区域的轮廓。 · 示例: `gallery2d_color_artistic`
- `xsitk_signed_maurer_dist` `region → image` GPU: 无 — 将符号距离图（SimpleITK ``SignedMaurerDistanceMap``）用tanh压缩到[0,1]所得的结果。将二值区域边界的距离（内侧、外侧皆含）表示为连续值图像，越靠近边界的位置越偏离0.5。 · 示例: `gallery2d_color_artistic`

#### 2d / features (73)
- `area_center` (halcon: `area_center`) `region → match` GPU: 仅在链中(lbl_area_center) — 以 3 分量向量 ``(面积 [像素数], 质心行 [px], 质心列 [px])`` 返回区域的面积与质心。与 HALCON 的 ``area_center``（Area and center of regions.）为相同的 3 个值、相同的单位。 · 示例: `example_inner_diameter_mm`, `gallery2d_features`
- `area_center_xld` (halcon: `area_center_xld`) `contour → match` GPU: 无 — 以 3 分量向量 ``(面积 [px²], 质心行 [px], 质心列 [px])`` 返回点数最多的那条轮廓所围多边形的面积与质心。为 HALCON 的 ``area_center_xld``（Area and center of gravity (centroid) of contours and polygons.）4 个值中去掉方向标记 PointOrder 的 3 个值。 · 示例: `gallery2d_features`
- `area_frac` (halcon: `area_center`) `region → feature` GPU: 仅在链中(lbl_area_frac) — 返回区域所占像素比例（面积占比）的特征量。与 HALCON 的 ``area_center``（Area and center of regions.）不同，只返回面积而不计算重心（仅对应其部分功能）。 · 示例: `gallery2d_features`, `shape_factors_closed_form`, `threshold_family_agreement`
- `area_holes` (halcon: `area_holes`) `region → feature` GPU: 仅在链中(lbl_area_holes) — 区域内孔洞所占的面积比 ``(填补孔洞后的面积 - 原始面积) / 填补孔洞后的面积``。越接近 0 表示孔洞越少,越接近 1 表示是大部分为孔洞的极端形状。相当于 HALCON 的 ``area_holes``(Compute the area of holes of regions.)。 · 示例: `gallery2d_features`
- `blob_count` (halcon: `count_obj`) `region → feature` GPU: 仅在链中(lbl_blob_count) — 区域中连通成分的个数(HALCON `count_obj`)。 · 示例: `gallery2d_features`, `mcp_task_score`, `poc_real_coin_metrology`, `quickstart`
- `circularity` (halcon: `circularity`) `region → feature` GPU: 仅在链中(lbl_circularity) — 圆形度 ``min(1, 面积 /(π·max²))``,``max`` 是**从重心到轮廓像素的最大距离**。圆为 1,越细长或有大的凸起/孔洞则越小。存在多个连通分量时只评估面积最大的一个。与 HALCON 的 ``circularity``(Shape factor for the circularity (similarity to a circle) of a region.)**是同一个公式**。 · 示例: `gallery2d_features`, `poc_cell_counting`, `poc_particle_sizing`, `poc_rotation_invariance_audit`, `shape_factors_closed_form`
- `circularity_xld` (halcon: `circularity_xld`) `contour → feature` GPU: 无 — 对最大的轮廓,用鞋带公式的面积 ``F`` 和从**所围面积的重心**到轮廓点的最大距离 ``max`` 计算 ``min(1, F/(π·max²))``(区域版 ``circularity`` 的轮廓版)。与 HALCON 的 ``circularity_xld``(Shape factor for the circularity (similarity to a circle) of contours or polygons.)**是同一个公式**。 · 示例: `gallery2d_features`
- `compactness` (halcon: `compactness`) `region → feature` GPU: 仅在链中(lbl_compactness) — 紧凑度 ``max(1, 周长² / (4π·面积))``。圆为 1，越细长/越粗糙/孔洞越多则越大，**没有上限**。与 HALCON 的 ``compactness``（Shape factor for the compactness of a region.）是同一个量。 · 示例: `gallery2d_features`, `shape_factors_closed_form`
- `compactness_xld` (halcon: `compactness_xld`) `contour → feature` GPU: 无 — 对最大的轮廓计算紧凑度 ``max(1, 周长²/(4π·面积))``(区域版 ``compactness`` 的轮廓版)。圆为 1,越细长/越粗糙则越大,**没有上限**。与 HALCON 的 ``compactness_xld``(Shape factor for the compactness of contours or polygons.)**是同一个公式**。 · 示例: `gallery2d_features`
- `connect_and_holes` (halcon: `connect_and_holes`) `region → feature` GPU: 仅在链中(lbl_connect_and_holes) — 计算区域的连通分量数（8 连通，与 ``count_obj`` 相同的 ``_sh_region_feat`` 的 ``count`` 分支）。a、b 未使用。 · 示例: `gallery2d_features`
- `contlength` (halcon: `contlength`) `region → feature` GPU: 有(lbl_contlength) — 区域的周长 [px] (``regionprops`` 的 ``perimeter``)。与 HALCON 的 ``contlength``（Contour length of a region.）为相同的量、相同的单位。 · 示例: `gallery2d_features`, `scale_law_of_features`
- `convexity` (halcon: `convexity`) `region → feature` GPU: 无 — 凸性 ``面积 / 凸包面积``(越接近 1 越接近凸形)。是 ``skimage.measure.regionprops`` 中 ``area`` 与 ``area_convex`` 的比值。相当于 HALCON 的 ``convexity``(Shape factor for the convexity of a region.)。 · 示例: `gallery2d_features`, `shape_factors_closed_form`
- `convexity_xld` (halcon: `convexity_xld`) `contour → feature` GPU: 无 — 针对最大的轮廓，计算凸性 ``轮廓面积 / 凸包面积``（``cv2.convexHull`` + ``cv2.contourArea``）。没有 cv2 时以 ``MissingDependencyError`` 停止（2026-10-25 之前会始终返回 1.0 = 完全凸）。相当于 HALCON 的 ``convexity_xld``（Shape factor for the convexity of contours or polygons.）。 · 示例: `gallery2d_features`
- `count_channels` (halcon: `count_channels`) `color → feature` GPU: 无 — 计算图像的通道数。相当于 HALCON 的 ``count_channels``（计算图像的通道数）。 · 示例: `gallery2d_features`
- `count_contours` (halcon: `count_obj`) `contour → feature` GPU: 无 — 返回轮廓（对象）数量的特征量。相当于 HALCON 的 ``count_obj``（Number of objects in a tuple.）。 · 示例: `gallery2d_features`
- `count_obj` (halcon: `count_obj`) `region → feature` GPU: 仅在链中(lbl_count_obj) — 统计连通成分的个数(``ndimage.label``,默认 8 连通)。采用与 HALCON 的 ``count_obj``/``connection`` 默认相同的 8 连通,因此对角相接的两个团块会被计为 1 个(若改为 4 连通会导致计数过多的例子——细胞计数实测为 342 个 vs 327 个,参见代码内注释)。相当于 HALCON 的 ``count_obj``(Number of objects in a tuple.)。 · 示例: `gallery2d_features`, `mcp_task_score`
- `cv_cc_count` (halcon: `connection`) `region → feature` GPU: 仅在链中(lbl_cv_cc_count) — 连通分量数量计数（单一标量特征，OpenCV 实现）。统计二值区域中连通分量（前景团块）的个数 —— 会先减去背景标签所占的 1，再返回结果。 · 示例: `gallery2d_features`, `genspark_external_review`
- `cv_good_features` `image → feature` GPU: 无 — 基于 Shi-Tomasi 方法的高品质角点检测（单一标量特征，OpenCV 实现）。以与 cv_min_eigen 相同的最小特征值标准评估角点程度，并以非极大值抑制与最小距离过滤筛选出排名靠前的角点 —— 这里只返回检测到的数量（若为 0 个则返回 0）。 · 示例: `gallery2d_features`
- `cv_hough_circles` (halcon: `hough_circles`) `image → feature` GPU: 无 — 基于霍夫变换的圆检测（单一标量特征，OpenCV 实现）。使用依赖边缘梯度信息的 HOUGH_GRADIENT 方法，以投票方式检测圆心与半径 —— 这里只返回检测到的圆的数量（若为 0 个则返回 0）。 · 示例: `gallery2d_features`
- `cv_hough_lines` (halcon: `hough_lines`) `image → feature` GPU: 无 — 基于概率霍夫变换的直线（线段）检测（单一标量特征，OpenCV 实现）。先用 Canny 生成边缘图，再以投票方式在其中寻找排成直线的边缘像素集合，将其检测为线段 —— 这里只返回检测到的线段数量（若为 0 条则返回 0）。 · 示例: `gallery2d_features`
- `diameter_region` (halcon: `diameter_region`) `region → feature` GPU: 无 — 区域的直径 [px] = 边界上两点间的最大距离(最长弦)。与 HALCON 的 ``diameter_region``（Maximal distance between two boundary points of a region.）为相同的量、相同的单位。 · 示例: `gallery2d_features`
- `diameter_xld` (halcon: `diameter_xld`) `contour → feature` GPU: 无 — 点数最多的那条轮廓的直径 [px] = 轮廓点两点间的最大距离(最长弦)。与 HALCON 的 ``diameter_xld``（Maximum distance between two contour or polygon points.）为相同的量、相同的单位。 · 示例: `gallery2d_features`
- `eccentricity` (halcon: `eccentricity`) `region → match` GPU: 仅在链中(lbl_eccentricity) — 以 ``match`` 排序的 3 分量向量返回三个由椭圆参数导出的形状特征 ``(Anisometry, Bulkiness, StructureFactor)``(单个标量无法表示三个值,与 ``area_center`` 形式相同)。 · 示例: `gallery2d_features`, `poc_rotation_invariance_audit`
- `eccentricity_xld` (halcon: `eccentricity_xld`) `contour → match` GPU: 无 — ``eccentricity`` 的轮廓版。对最大的轮廓以 ``match`` 排序的 3 分量向量返回 ``(Anisometry, Bulkiness, StructureFactor)``。与 HALCON 的 ``eccentricity_xld``(Shape features derived from the ellipse parameters of contours or polygons.)**是同样的三个值、同样的公式**。 · 示例: `gallery2d_features`
- `effective_bit_depth` `image → feature` GPU: 无 — 估计图像**实际**使用的位数，并映射到 ``[0,1]`` 后返回(feature)。 · 示例: `gallery2d_features`
- `elliptic_axis` (halcon: `elliptic_axis`) `region → match` GPU: 有(lbl_elliptic_axis) — 以 ``match`` 排序的 3 分量向量返回区域等价椭圆(惯性矩相同的椭圆)的 ``(Ra, Rb, Phi)``—— ``Ra``/``Rb`` 是长半轴与短半轴(**像素**),``Phi`` 是主轴的角度(弧度,从列轴逆时针)。与 HALCON 的 ``elliptic_axis``(Calculate the parameters of the equivalent ellipse.)是同样的三个值。 · 示例: `gallery2d_features`
- `elliptic_axis_xld` (halcon: `elliptic_axis_xld`) `contour → match` GPU: 无 — 对点数最多的那条轮廓拟合椭圆(``cv2.fitEllipse``),以 ``match`` 类型的 3 分量向量返回 ``(Ra, Rb, Phi)`` —— ``Ra``/``Rb`` 为长半轴、短半轴 [px],``Phi`` 为主轴角(弧度,从列轴起**在屏幕上逆时针**,行向下,大于 -π/2 且不超过 π/2)。与 HALCON 的 ``elliptic_axis_xld``(Parameters of the equivalent ellipse of contours or polygons.)为相同的 3 个值。 · 示例: `gallery2d_features`
- `entropy_gray` (halcon: `entropy_gray`) `image → feature` GPU: 无 — 灰度阶调的 Shannon 熵(由 64 个分箱的直方图计算,并以最大值 ``log2(64)=6`` 位进行归一化)。表示灰度分布的"离散程度/信息量"——图像越均匀数值越大,越偏向单一灰度级则越接近 0。HALCON 的 ``entropy_gray``(Determine the entropy and anisotropy of images.)返回熵和各向异性一对值,但这个代替实现只实现了熵。 · 示例: `gallery2d_features`
- `estimate_noise` (halcon: `estimate_noise`) `image → feature` GPU: 无 — 稳健地估计加性噪声的标准差 σ（``_noise_sigma``：把拉普拉斯响应的 MAD 换算为正态分布等效尺度，再除以 5 点拉普拉斯核的噪声增益 ``sqrt(20)``）。设计上对边缘产生的离群值不敏感，只拾取平坦区域的噪声（2026-09-02 已修复旧实现中“σ 没有单位、在 σ≈0.08 以上会饱和到 1.0”的缺陷，详见 ``_noise_sigma`` 的 docstring）。相当于 HALCON 的 ``estimate_noise``（Estimate the image noise from a single image.）。 · 示例: `gallery2d_features`, `poc_weld_radiograph_porosity`
- `euler_number` (halcon: `euler_number`) `region → feature` GPU: 无 — 欧拉数(``skimage.measure.euler_number``,是连通成分数减去孔洞数得到的拓扑不变量)。数值越小(越接近负值)表示孔洞越多。相当于 HALCON 的 ``euler_number``(Calculate the Euler number.)。 · 示例: `gallery2d_features`
- `fractal_dimension` `image → feature` GPU: 无 — 测量纹理复杂度的 Minkowski-Bouligand(盒计数)分形维数。 · 示例: `gallery2d_features`, `poc_endless_zoom_and_turning_solids`, `poc_theorems_as_pictures`
- `get_region_thickness` (halcon: `get_region_thickness`) `region → feature` GPU: 无 — 区域粗细 [px] 的近似值 ``2 × 最大内切圆半径``（``distance_transform_edt`` 最大值的 2 倍）。图像外视为背景（接触边缘的区域也与扩大图像时的粗细相同。全满的 60x80 为 60）。 · 示例: `gallery2d_features`, `poc_bone_trabecular_thickness`
- `gray_histo_abs` (halcon: `gray_histo_abs`) `image → feature` GPU: 无 — 返回图像灰度的标准差(``x.std()``)。HALCON 的 ``gray_histo_abs``(Calculate the gray value distribution.)本来是返回整个直方图(各灰度级的柱状计数)的算子,但这个代替实现并非直方图本身,而是概括为表示分布离散程度的标准差这一个标量(近似——这是因为该流水线中 ``feature`` 排序必须是单一标量这一契约上的限制)。 · 示例: `gallery2d_features`
- `height_width_ratio` (halcon: `height_width_ratio`) `region → feature` GPU: 仅在链中(lbl_height_width_ratio) — 轴平行外接矩形的纵横比 ``高 / 宽``。没有上限,纵长的区域会超过 1(160x4 为 40.0)。它与 HALCON 的 ``height_width_ratio``(Compute the width, height, and aspect ratio of the surrounding rectangle parallel to the coordinate axes.)所返回的三个值中的 **Ratio 是同一个量**(Height 与 Width 是像素长度,未返回 —— 见 docs/KNOWN_ISSUES.md §51)。 · 示例: `gallery2d_features`
- `hough_circle_trans` (halcon: `hough_circle_trans`) `image → image` GPU: 无 — 用于圆检测的 Hough 变换。对边缘掩膜使用半径 4〜19（步长 3）的一组圆模板计算 ``skimage.transform.hough_circle``，并把所有半径中的最大响应归一化到 [0,1] 后返回。相当于 HALCON 的 ``hough_circle_trans``（Return the Hough-Transform for circles with a given radius.）（HALCON 会明确指定半径，此处则用固定范围做穷举的近似）。 · 示例: `gallery2d_features`, `poc_real_coin_metrology`
- `hough_line_trans` (halcon: `hough_line_trans`) `image → image` GPU: 无 — 用于直线检测的 Hough 变换累加器。先由 Sobel 梯度生成边缘掩膜，用 ``skimage.transform.hough_line`` 计算累加器空间（角度×距离），归一化后再缩放到与输入相同的像素形状后返回（以图像的形式可视化，而非累加器本身的坐标系）。相当于 HALCON 的 ``hough_line_trans``（Produce the Hough transform for lines within regions.）。 · 示例: `gallery2d_features`
- `intensity` (halcon: `intensity`) `image → feature` GPU: 无 — 返回图像的平均亮度(``x.mean()``)。HALCON 的 ``intensity``(Calculate the mean and deviation of gray values.)是返回均值和标准差一对值的算子,但这个代替实现只返回均值(如需标准差,请与 ``gray_histo_abs``(返回标准差 std)配合使用)。 · 示例: `gallery2d_bridge`, `gallery2d_features`, `poc_multibeam_bathymetry`, `poc_patch_anomaly`, `poc_pocket_interreflection`, `poc_pxrd_phase_peel`, `poc_solder_fillet_aoi`, `poc_video_cube`
- `length_xld` (halcon: `length_xld`) `contour → feature` GPU: 无 — 将所有轮廓的线段长度(相邻点间的欧几里得距离)相加所得的总长。若存在多条轮廓,则统一相加。相当于 HALCON 的 ``length_xld``(Length of contours or polygons.)。 · 示例: `gallery2d_features`
- `min_max_gray` (halcon: `min_max_gray`) `image → feature` GPU: 无 — 只返回图像的最大灰度值(``x.max()``)。HALCON 的 ``min_max_gray``(Determine the minimum and maximum gray values within regions.)本来是同时返回最小值和最大值的算子,但这个代替实现只实现了最大值,最小值的信息因此丢失(数据缺失的近似——老实说,它只计算了名称'min_max'所暗示内容的一半)。 · 示例: `gallery2d_features`
- `moments_region_2nd` (halcon: `moments_region_2nd`) `region → feature` GPU: 有(lbl_moments_region_2nd) — 归一化中心二阶矩之和的绝对值 ``|μ20 + μ02|``(源自 ``skimage.measure.moments_normalized``)。HALCON 的 ``moments_region_2nd``(Calculate the geometric moments of regions.)本来会分别返回 M20/M02/M11,但这个代替实现为了简化为一个标量,用两个分量简单相加得到的合成值来近似(各方向分量的信息会丢失)。 · 示例: `gallery2d_features`, `scale_law_of_features`
- `moments_region_2nd_invar` (halcon: `moments_region_2nd_invar`) `region → feature` GPU: 有(lbl_moments_region_2nd_invar) — Hu 第一不变矩(``skimage.measure.moments_hu`` 的 ``hu[0]``)的绝对值。是对旋转、缩放、平移不变的形状描述符。相当于 HALCON 的 ``moments_region_2nd_invar``(Geometric moments of regions.)的近似(严格来说与 HALCON 独有的相对不变矩定义不同,而是用经典的 Hu 矩来代替)。 · 示例: `gallery2d_features`, `poc_rotation_invariance_audit`
- `moments_region_2nd_rel_invar` (halcon: `moments_region_2nd_rel_invar`) `region → feature` GPU: 有(lbl_moments_region_2nd_rel_invar) — Hu 第 3 个不变矩（``hu[2]``）的绝对值。注意名称（``2nd_rel_invar``）与实现（Hu 的第三个不变量）并不严格对应——这并非 HALCON 独有的“二阶相对不变矩”，只是从通用的 Hu 不变矩系列中挑出来的近似分配。用作 HALCON ``moments_region_2nd_rel_invar``（Geometric moments of regions.）的替代。 · 示例: `gallery2d_features`
- `moments_region_3rd` (halcon: `moments_region_3rd`) `region → feature` GPU: 仅在链中(lbl_moments_region_3rd) — 归一化中心三阶矩之和的绝对值 ``|μ30 + μ03|``。是 ``moments_region_2nd`` 的三阶版本，同样是把多个分量简单相加得到合成值的近似（各方向分量的信息会丢失）。相当于 HALCON 的 ``moments_region_3rd``（Geometric moments of regions.）。 · 示例: `gallery2d_features`, `scale_law_of_features`
- `moments_region_3rd_invar` (halcon: `moments_region_3rd_invar`) `region → feature` GPU: 有(lbl_moments_region_3rd_invar) — Hu 第 4 个不变矩（``hu[3]``）的绝对值。作为 ``moments_region_*_invar`` 系列之一，按顺序从 Hu 矩数组中分配（与 HALCON 独有定义并无严格对应的近似）。用作 HALCON ``moments_region_3rd_invar``（Geometric moments of regions.）的替代。 · 示例: `gallery2d_features`
- `moments_region_central` (halcon: `moments_region_central`) `region → feature` GPU: 仅在链中(lbl_moments_region_central) — 归一化中心矩（至二阶）之和的绝对值 ``|μ20+μ11+μ02|``。是对应 HALCON ``moments_region_central``（Geometric moments of regions.）的近似，将多个分量合成为单一标量。 · 示例: `gallery2d_features`, `scale_law_of_features`
- `moments_region_central_invar` (halcon: `moments_region_central_invar`) `region → feature` GPU: 仅在链中(lbl_moments_region_central_invar) — Hu 第 2 个不变矩（``hu[1]``）的绝对值。是对应 HALCON ``moments_region_central_invar``（Geometric moments of regions.）的近似（``moments_region_2nd_invar`` 使用 Hu[0]，而此处使用 Hu[1]——两者都不是 HALCON 独有的相对不变矩的严格替代）。 · 示例: `gallery2d_features`, `poc_rotation_invariance_audit`
- `moments_xld` (halcon: `moments_xld`) `contour → feature` GPU: 无 — 从轮廓的原始矩（``cv2.moments``）计算单一标量 ``(mu20+mu02)/面积²``——这是把 HALCON ``moments_xld``（Geometric moments M20, M02, and M11 of contours or polygons.）返回的 M20/M02/M11 三个分量合成为一个值的近似（各方向分量及 M11 会丢失）。 · 示例: `gallery2d_features`
- `orientation_region` (halcon: `orientation_region`) `region → feature` GPU: 有(lbl_orientation_region) — 区域主轴方向 θ / 180(θ 为等效椭圆长轴的角度,从列轴起**在屏幕上逆时针**测量,行向下,范围 [0, 180] 度;乘以 180 即为度;实现为将 ``regionprops`` 的 ``orientation`` 按 ``(orientation + π/2) / π`` 映射)。与 HALCON 的 ``orientation_region``(Orientation of a region.)方向相同 —— HALCON 用最远点确定朝向并以 -π..π 弧度返回,这里折叠到 180 度并归一化到 [0,1]。与 ``elliptic_axis`` 的 Phi(弧度)满足 θ ≡ Phi (mod π)。 · 示例: `gallery2d_features`
- `orientation_xld` (halcon: `orientation_xld`) `contour → feature` GPU: 无 — 对最大轮廓拟合椭圆(``cv2.fitEllipse``)所得的**主轴角 θ / 180**(θ 从列轴起**在屏幕上逆时针**测量,行向下,折叠到 [0, 180) 度)。与区域版 ``orientation_region`` 规约相同(乘以 180 即为度)。HALCON 的 ``orientation_xld``(Calculate the orientation of contours or polygons.)以 -π..π 弧度返回同方向的角(用最远点确定朝向),这里是折叠到 180 度并归一化到 [0,1) 的版本。 · 示例: `gallery2d_features`
- `rectangularity` (halcon: `rectangularity`) `region → feature` GPU: 无 — 矩形度。构造一个与区域具有**相同一阶、二阶矩**的矩形,把两者之差的面积用该矩形的面积归一化(``1 - |区域 XOR 矩形| / |矩形|``);矩形时为 1。与 HALCON 的 ``rectangularity``(Shape factor for the rectangularity of a region.)**定义相同**。 · 示例: `gallery2d_features`, `shape_factors_closed_form`
- `rectangularity_xld` (halcon: `rectangularity_xld`) `contour → feature` GPU: 无 — 矩形度的轮廓版。把轮廓填充后,用与其具有**相同一阶、二阶矩**的矩形之差的面积除以该矩形的面积;矩形时为 1。与 HALCON 的 ``rectangularity_xld``(Shape factor for the rectangularity of contours or polygons.)**定义相同**。 · 示例: `gallery2d_features`
- `roundness` (halcon: `roundness`) `region → feature` GPU: 仅在链中(lbl_roundness) — 真圆度 ``1 - σ/μ``,``μ`` 与 ``σ`` 是**从重心到轮廓像素的距离**的均值与标准差;距离越均匀(越接近正圆)越接近 1。与 HALCON 的 ``roundness``(Shape factors from contour.)**是同一个公式**。 · 示例: `gallery2d_features`, `shape_factors_closed_form`
- `sk_blur_effect` `image → feature` GPU: 无 — 模糊程度估计(1 个标量特征量)。有意地对图像再稍微模糊化,通过比较原图与再模糊化后边缘锐度的变化程度,返回一个 0(无模糊)〜1(最大程度模糊)的分数 —— 无需参考图像即可量化对焦/抖动情况。 · 示例: `gallery2d_features`, `poc_real_deblur_honesty`
- `sk_entropy_feat` (halcon: `entropy_gray`) `image → feature` GPU: 无 — 整幅图像的香农熵(1 个标量特征量)。用一个数值概括亮度直方图分布的离散程度、信息量 —— 数值越高,表示亮度分布越均匀分散(信息量越多/对比度越丰富)。 · 示例: `gallery2d_features`
- `sk_euler` (halcon: `euler_number`) `region → feature` GPU: 无 — 欧拉数(Euler number)。定义为「连通分量数 − 孔洞数」的拓扑学特征量,不表示区域的形状本身(位置、大小),而只是表示「连接方式」的整数值。 · 示例: `gallery2d_features`
- `total_length` (halcon: `length_xld`) `contour → feature` GPU: 无 — 返回全部 XLD 轮廓总弧长的特征量。相当于 HALCON 的 ``length_xld``（Length of contours or polygons.）。 · 示例: `gallery2d_features`, `poc_solar_el_inspection`
- `vol_count` `volume → feature` GPU: 无 — 返回 3D 体数据中连通成分（blob）个数的特征量。未指定对应的 HALCON op。 · 示例: `gallery2d_features`
- `xcv2_fast_count` `image → feature` GPU: 无 — FAST角点检测器检测到的关键点数量（``cv2.FastFeatureDetector``）。 · 示例: `gallery2d_features`
- `xcv2_lap_var` `image → feature` GPU: 无 — 基于拉普拉斯方差的对焦（模糊）指标（``cv2.Laplacian``的方差）。 · 示例: `gallery2d_features`, `poc_focus_stacking`
- `xcv3_agast_count` `image → feature` GPU: 无 — AGAST 特征点数(OpenCV AGAST 检测器，FAST 的自适应树结构版本)。将检测到的关键点数量作为 feature 返回。 · 示例: `gallery2d_features`
- `xcv3_brisk_count` `image → feature` GPU: 无 — BRISK 特征点数(OpenCV BRISK 检测器)。将基于二值描述符的高速特征点检测器所检测到的关键点数量作为 feature 返回。 · 示例: `gallery2d_features`
- `xcv3_gray_hu1` `image → feature` GPU: 无 — 灰度图像的第 1 个 Hu 不变矩(OpenCV ``cv2.HuMoments(cv2.moments(...))[0,0]``)。将灰度值本身(而非二值形状)视为质量分布时，表示旋转、缩放、平移不变的分布广度的特征量(基于二阶中心矩)。以 1.0 封顶。 · 示例: `gallery2d_features`
- `xcv3_lsd_count` `image → feature` GPU: 无 — 检测到的直线段数量(通过 OpenCV ``cv2.createLineSegmentDetector`` 实现的 Line Segment Detector，LSD)。将图像中检测到的直线段数量作为 feature 返回(由于该实现在检测数为 0 时返回 ``None``，此时按 0 处理)。 · 示例: `gallery2d_features`
- `xcv3_sift_count` `image → feature` GPU: 无 — SIFT 特征点数(OpenCV ``cv2.SIFT_create().detect``)。将图像中检测到的尺度不变特征点(SIFT keypoints)的数量作为 feature 返回——可作为纹理复杂度/可用于匹配的特征点丰富程度的指标。 · 示例: `gallery2d_features`
- `xcv_orb_count` `image → feature` GPU: 无 — OpenCV 版 ORB（Oriented FAST and Rotated BRIEF）检测到的关键点数量。 · 示例: `gallery2d_features`
- `xsk3_estimate_sigma` `image → feature` GPU: 无 — 噪声标准差估计(skimage ``restoration.estimate_sigma``，基于小波系数中位数绝对偏差(MAD)的 Donoho 估计量)。将估计值乘以 5 后以 1.0 封顶，作为 feature 返回。 · 示例: `gallery2d_features`
- `xsk3_is_low_contrast` `image → feature` GPU: 无 — 低对比度图像判定(skimage ``exposure.is_low_contrast``)。将判断图像亮度范围是否小于可能取值全范围的 ``fraction_threshold`` 的布尔值，以 0.0/1.0 的 feature 形式返回。 · 示例: `gallery2d_features`
- `xsk_blob_dog` `image → feature` GPU: 无 — 检测到的斑点（斑点状结构）数量（以 LoG/DoG/DoH 之一检测）。 · 示例: `gallery2d_features`
- `xsk_blob_doh` `image → feature` GPU: 无 — 检测到的斑点（斑点状结构）数量（以 LoG/DoG/DoH 之一检测）。 · 示例: `gallery2d_features`
- `xsk_blob_log` `image → feature` GPU: 无 — 检测到的斑点（斑点状结构）数量（以 LoG/DoG/DoH 之一检测）。 · 示例: `gallery2d_features`, `poc_search_sweep_width`
- `xsk_orb_count` `image → feature` GPU: 无 — ORB（Oriented FAST and Rotated BRIEF）关键点检测数量。 · 示例: `gallery2d_features`
- `xwt_detail_energy` `image → feature` GPU: 无 — 小波细节成分的能量比。用``db2``做3层分解，返回所有细节系数（各层的水平/垂直/对角）均方和，除以该值加上近似成分均方后的总能量 —— 用于衡量高频（纹理/噪声/边缘）在图像整体中所占比例的指标，取值范围大致为[0,1)。 · 示例: `gallery2d_features`
- `xwt_packet_entropy` `image → feature` GPU: 无 — 小波包能量分散度（香农熵）。用``db1``做深度为2的小波包分解，将16个叶子子带各自的能量（系数平方和）归一化后视为一个分布，计算其香农熵，再除以``log2(16)``归一化到[0,1]。 · 示例: `gallery2d_features`

#### 2d / filtering (1)
- `tf_gradient_domain_reintegrate` `image → image` GPU: 有(许可列表) — gradient_domain_reintegrate：对梯度进行阈值处理，然后进行泊松重积分。 · 示例: `gallery2d_smoothing_rank`

#### 2d / frequency (19)
- `bandpass_image` (halcon: `bandpass_image`) `image → image` GPU: 有(bandpass_image) — 在频域中只让指定频带通过的带通滤波器(截断低频与高频),再以逆FFT变换回实空间。与``highpass_image``相同,结果是零均值的带符号响应,因此用``signed01``映射到[0,1]。相当于HALCON的``bandpass_image``(Edge extraction using bandpass filters.)。 · 示例: `gallery2d_texture_freq`
- `fft_generic` (halcon: `fft_generic`) `image → image` GPU: 有(许可列表) — 返回图像傅里叶变换幅度谱的对数压缩结果（``log1p(|F|)`` 按最大值归一化）。中心对应低频分量，周边对应高频分量（已做 ``fftshift``）。a、b 未使用。 · 示例: `gallery2d_texture_freq`
- `fft_image` (halcon: `fft_image`) `image → image` GPU: 有(许可列表) — 将二维FFT的功率谱用``log1p(|F|)``压缩并归一化后得到的图像。已经过``fftshift``处理,使低频(直流)分量位于中心。用于可视化周期性噪声或纹理的空间频率。相当于HALCON的``fft_image``(Compute the fast Fourier transform of an image.)。 · 示例: `degenerate_inputs`, `gallery2d_texture_freq`, `poc_moire_screen`
- `fft_image_inv` (halcon: `fft_image_inv`) `image → image` GPU: 有(许可列表) — 直接把输入图像当作频域数组，施加逆 FFT，再用 ``signed01`` 把实部映射到 [0,1]（0.5 表示零）。HALCON 的 ``fft_image_inv``（Compute the inverse fast Fourier transform of an image.）本应是把 ``fft_image`` 生成的复数频谱（实部与虚部的组合）还原的运算，但此替代实现受限于只能处理单张灰度图的管线约定，因此成为把像素值原样当作（虚部为 0 的）复数数组做逆变换的近似（注意：即使把 ``fft_image`` 的输出原样传入，也不会构成语义上有效的往返）。 · 示例: `gallery2d_texture_freq`
- `highpass` (halcon: `highpass_image`) `image → image` GPU: 有(highpass_image) — 通过 FFT 实现的高通滤波器（提取轮廓与高频成分）。相当于 HALCON 的 ``highpass_image``（Extract high frequency components from an image.）。 · 示例: `gallery2d_texture_freq`, `optics_four_f_processor`, `signal_filter`
- `highpass_image` (halcon: `highpass_image`) `image → image` GPU: 有(许可列表) — 在频域中截断低频(半径``<= 0.02+0.3*a``),将剩余部分通过逆FFT变换回实空间的高通滤波器。由于结果是零均值的**带符号**响应,因此用``signed01``映射到[0,1] (0.5表示零,也就是说约有一半像素小于0.5属于正常现象)。相当于HALCON的``highpass_image``(Extract high frequency components from an image.)。 · 示例: `gallery2d_texture_freq`, `poc_river_surface_velocity`
- `lowpass` `image → image` GPU: 有(lowpass_image) — 通过 FFT 实现的低通滤波器（模糊）。未指定对应的 HALCON 单一算子。 · 示例: `degenerate_inputs`, `gallery2d_texture_freq`, `optics_four_f_processor`, `signal_filter`
- `phase_deg` (halcon: `phase_deg`) `image → image` GPU: 仅在链中(许可列表) — 复数图像的相位角图。将 ``np.angle(F)``（-π〜π）通过 ``(angle+π)/(2π)`` 线性映射到 [0,1]。a、b 未使用。 · 示例: `gallery2d_texture_freq`
- `phase_rad` (halcon: `phase_rad`) `image → image` GPU: 有(许可列表) — 将FFT的相位``angle(F)``从弧度线性映射到[0,1] (0=-π,1=+π)。用于可视化功率谱所丢失的相位信息(相位承载了结构大部分的空间位置信息)。相当于HALCON的``phase_rad``(Return the phase of a complex image in radians.)。 · 示例: `gallery2d_texture_freq`
- `power_byte` (halcon: `power_byte`) `image → image` GPU: 有(许可列表) — 实现与``fft_image``相同(``kind: "fft_power"``,log1p功率谱)。在HALCON中,``power_byte``指用于8位输出的字节量化功率谱,但此替代实现并未与``power_real``/``fft_image``区分,返回相同的处理结果(近似的局限)。是HALCON``power_byte``(Return the power spectrum of a complex image.)的代用。 · 示例: `gallery2d_texture_freq`
- `power_ln` (halcon: `power_ln`) `image → image` GPU: 有(许可列表) — 复数图像功率谱的替代实现。实现与 fft_generic 完全相同：对输入图像自行做 FFT，再取幅度的对数 ``log1p(|F|)`` 并按最大值归一化返回（共享 ``_sh_freq`` 的 ``fft_power`` 分支）。a、b 未使用。 · 示例: `gallery2d_texture_freq`
- `power_real` (halcon: `power_real`) `image → image` GPU: 有(许可列表) — 将FFT实部的绝对值``|Re(F)|``归一化后得到的图像(与``fft_image``的对数功率谱不同,这里不取对数,只观察实部)。是相当于HALCON``power_real``(Return the power spectrum of a complex image.)的近似(HALCON原本的定义是功率|F|²,但这里用实部绝对值代替)。 · 示例: `gallery2d_texture_freq`
- `rft_generic` (halcon: `rft_generic`) `image → image` GPU: 有(许可列表) — 实数傅里叶变换（real FFT, RFFT）的替代实现。实现是先计算普通的复数 FFT，再取实部绝对值 ``|Re F|`` 按最大值归一化返回，并非 HALCON 的 rft_generic 实际计算的那种利用对称性缩减数据量的半尺寸纯实数快速变换。a、b 未使用。 · 示例: `gallery2d_texture_freq`
- `sk_butterworth` `image → image` GPU: 无 — Butterworth 滤波器（频率域）。对图像做 FFT 后，作为只通过高于指定截止频率成分的高通滤波器工作（沿用默认的 ``high_pass=True`` 调用）。强调轮廓和纹理的高频成分。 · 示例: `gallery2d_texture_freq`
- `xsk2_radon` `image → image` GPU: 无 — 通过拉东变换（Radon transform）得到的正弦图（投影数据）。以与图像长边一致的角度数量（0~180度，用``linspace``等间隔）调用``skimage.transform.radon``，将结果缩放回原图尺寸后按最大值归一化。 · 示例: `gallery2d_texture_freq`
- `xsp_dct` `image → image` GPU: 无 — 对二维离散余弦变换（DCT-II，ortho 归一化）的功率谱进行对数压缩后显示。 · 示例: `gallery2d_texture_freq`
- `xsp_dct_lowpass` `image → image` GPU: 无 — 一种低通滤波器，仅保留 DCT 系数中低频的正方形区块后再做逆变换。 · 示例: `gallery2d_texture_freq`
- `xwt_mra_component` `image → image` GPU: 无 — 多分辨率分析（MRA、``pywt.mra2``）中某一层的细节成分。用``db2``做3层MRA分解时，各层的水平/垂直/对角成分都以与原图相同分辨率的图像形式得到（与普通小波分解不同，不会被缩小）。这里选取其中一层，将水平+垂直+对角相加得到的合成细节图像做min-max归一化后返回。 · 示例: `gallery2d_texture_freq`
- `xwt_subband_tile` `image → image` GPU: 无 — 将单层小波分解（``pywt.dwt2``，Haar）的4个子带（近似cA、水平cH、垂直cV、对角cD）以2x2排列拼成一幅图像，并做min-max归一化。就是小波金字塔的可视化。 · 示例: `gallery2d_texture_freq`

#### 2d / geometry (29)
- `affine_trans_image` (halcon: `affine_trans_image`) `image → image` GPU: 有(affine_trans_image) — 结合旋转(-20°〜+20°,由``a``决定)与剪切(由``b``决定)的一般性仿射变换。以中心为基准套用``ndimage.affine_transform``,超出边框以反射填补。相当于HALCON的``affine_trans_image``(Apply an arbitrary affine 2D transformation to images.)(HALCON可直接传入任意的2x3/3x3变换矩阵,此处则限定为旋转+剪切两个参数的近似)。 · 示例: `gallery2d_geometry`, `poc_change_detection_misreg`
- `affine_trans_image_size` (halcon: `affine_trans_image_size`) `image → image` GPU: 有(affine_trans_image_size) — 对图像施加仿射变换（旋转+剪切）。实现与 ``affine_trans_image`` 共享 ``_sh_geom`` 中的 ``affine`` 分支，由 a 将旋转角设为 -20°〜+20°，由 b 调节剪切量。超出边界的部分以镜像（reflect）方式填充。 · 示例: `gallery2d_geometry`
- `affine_trans_region` (halcon: `affine_trans_region`) `region → region` GPU: 有(许可列表) — 对区域施加仿射变换（旋转+剪切）。使用与 ``affine_trans_image`` 相同的 ``_sh_geom`` 中的 ``affine`` 分支将其作为连续值变换，再通过 ``_rebinarise`` 以 0.5 重新二值化，返回 {0,1} 的区域（以消除几何变换插值产生的中间值）。a 调节旋转角（-20°〜+20°），b 调节剪切量。 · 示例: `gallery2d_geometry`
- `affine_warp` (halcon: `affine_trans_image`) `image → image` GPU: 有(affine_warp) — 对图像应用任意仿射变换（旋转 + 剪切）。相当于 HALCON 的 ``affine_trans_image``（Apply an arbitrary affine 2D transformation to images.）。 · 示例: `gallery2d_geometry`
- `deskew` `image → image` GPU: 无 — **测量倾斜并将其扶正**(deskew)。角度不是通过旋钮给出，而是从图像中估计。 · 示例: `gallery2d_geometry`
- `it_add_image_border` (halcon: `add_image_border`) `image → image` GPU: 有(许可列表) — add_image_border:在图像四周填充宽度为 ``w`` 的反射边框,再将带边框的画布放回原始 HxW 尺寸内。``a`` 设置边框宽度 w = 1 + round(a*6);``b`` 被忽略。 · 示例: `gallery2d_geometry`
- `it_change_format` (halcon: `change_format`) `image → image` GPU: 有(许可列表) — change_format:通过在原点处裁剪/填充,将图像矩阵尺寸改为最大边长的正方形(不做重采样,与 HALCON 的 change_format 完全一致)。正方形图像原样返回;非正方形图像会以零值扩展为正方形。``a``/``b`` 被忽略。 · 示例: `gallery2d_geometry`
- `it_crop_part` (halcon: `crop_part`) `image → image` GPU: 有(it_crop_part) — crop_part:截取图像中心 a 比例的部分,再重新采样回 HxW —— 是对中心区域真正的放大。``b`` 被忽略。 · 示例: `gallery2d_geometry`
- `it_crop_rectangle1` (halcon: `crop_rectangle1`) `image → image` GPU: 有(it_crop_rectangle1) — crop_rectangle1:截取覆盖行/列范围 [a .. 1-a] 的居中矩形,再重新采样回 HxW。a=0 时(近似)恒等;a 越大放大程度越高。``b`` 被忽略。 · 示例: `gallery2d_geometry`
- `mirror_image` (halcon: `mirror_image`) `image → image` GPU: 无 — 依``a``的值切换3种镜像方式(``a<0.34``:上下翻转、``a<0.67``:左右翻转、其余:转置)。请注意这是离散的模式选择,而非连续的镜像变换。相当于HALCON的``mirror_image``(Mirror an image.)(HALCON以明确的模式参数选择上下/左右/对角,此处则是以``a``的值域伪选择的近似)。 · 示例: `gallery2d_geometry`
- `mirror_region` (halcon: `mirror_region`) `region → region` GPU: 无 — 翻转（镜像）区域。根据 a 的值切换轴：a<0.34 时上下翻转（``flipud``），0.34≤a<0.67 时左右翻转（``fliplr``），其他情况下转置（对角线翻转，``x.T``）。b 未使用。由于翻转不改变数值，``_rebinarise`` 实际上什么都不做。 · 示例: `gallery2d_geometry`
- `polar_trans_image` (halcon: `polar_trans_image`) `image → image` GPU: 无 — 直角坐标→极坐标变换(``cv2.warpPolar``)。以图像中心为极点、``min(H,W)/2``为最大半径,将环状内容转换为横向展开图。未映射的像素以0填补(先将``dst``清零,再读取cv2的返回值——若直接读取``dst``缓冲区本身有时会是空的,这一实作上的注意事项在代码注释中有详细说明)。相当于HALCON的``polar_trans_image``(Transform an image to polar coordinates)。 · 示例: `gallery2d_geometry`, `poc_allsky_cloud_cover`, `poc_gear_tooth_metrology`
- `polar_trans_image_ext` (halcon: `polar_trans_image_ext`) `image → image` GPU: 无 — 将整幅图像转换为极坐标（半径、角度）表示（``cv2.warpPolar``，正向、线性插值）。中心固定为图像中心，半径最大值为 ``min(h,w)/2``。a、b 未使用（与 ``polar_trans_image`` 共享 ``_sh_geom`` 中相同的 ``polar`` 分支）。 · 示例: `gallery2d_geometry`
- `polar_trans_image_inv` (halcon: `polar_trans_image_inv`) `image → image` GPU: 无 — 从极坐标到直角坐标的逆变换（``cv2.warpPolar`` + ``WARP_INVERSE_MAP``）。是 ``polar_trans_image`` 的逆映射，半径为 ``min(H,W)/2`` 的圆盘外侧以 0 填充。2026-09-02 已修复“cv2 未写入的像素以未初始化状态返回”的缺陷（原因是读取了传入的 ``dst`` 而非返回值，导致每次执行结果都不同——详见代码内注释）。相当于 HALCON 的 ``polar_trans_image_inv``（Transform an image in polar coordinates back to Cartesian coordinates）。 · 示例: `gallery2d_geometry`
- `polar_trans_region_inv` (halcon: `polar_trans_region_inv`) `region → region` GPU: 无 — 将极坐标表示逆变换为普通的直角坐标（笛卡尔坐标）（``cv2.warpPolar`` 的逆映射模式）。以中心为基准，半径 ``min(h,w)/2`` 的圆盘外部用 0 填充，然后通过 ``_rebinarise`` 以 0.5 阈值恢复为二值区域。a、b 未使用（与 ``polar_trans_image_inv`` 共享 ``_sh_geom`` 的 ``polar_inv`` 分支）。 · 示例: `gallery2d_geometry`
- `projective_trans_image` (halcon: `projective_trans_image`) `image → image` GPU: 有(projective_trans_image) — 透视（射影）变换（``cv2.warpPerspective``）。将四个角中的上方两个角按 ``d=0.06+0.12*a`` 的比例向内收拢，从而制造出梯形（带透视感）畸变。画面外的区域用反射填充。相当于 HALCON 的 ``projective_trans_image``（Apply a projective transformation to an image.）（HALCON 可以传入任意单应性矩阵，而此处近似为仅限于一种梯形畸变的模式）。 · 示例: `gallery2d_geometry`, `poc_water_level`
- `projective_trans_image_size` (halcon: `projective_trans_image_size`) `image → image` GPU: 有(projective_trans_image_size) — 实现与 ``projective_trans_image`` 完全相同（``kind: "projective"``）。名称暗示可以指定输出尺寸，但该后端并不改变输出画布大小，返回的梯形畸变与 ``projective_trans_image`` 完全一致（近似的局限，尺寸变更功能未被重现）。用作 HALCON ``projective_trans_image_size``（Apply a projective transformation to an image and specify the output image size.）的替代。 · 示例: `gallery2d_geometry`
- `projective_trans_region` (halcon: `projective_trans_region`) `region → region` GPU: 有(projective_trans_region) — 将与 ``projective_trans_image`` 相同的梯形畸变应用于区域（二值掩膜）。由于 ``out_sort`` 为 ``region``，``build()`` 会用 ``_rebinarise`` 包裹，将插值产生的小数值以 ``>0.5`` 转回二值后再返回（这是为了不破坏区域 {0,1} 约定所做的后处理）。相当于 HALCON 的 ``projective_trans_region``（Apply a projective transformation to a region.）。 · 示例: `gallery2d_geometry`
- `rescale_img` (halcon: `zoom_image_factor`) `image → image` GPU: 仅在链中(许可列表) — 保持中心的等向缩放 ``s = 0.7 + 0.6·a``,画布不变。 · 示例: `gallery2d_geometry`
- `rotate_image` (halcon: `rotate_image`) `image → image` GPU: 有(rotate_image) — 以中心为轴将图像旋转-45°〜+45°(由``a``决定)(``scipy.ndimage.rotate``,以``reshape=False``保持画布尺寸不变)。超出边框的部分以反射(``mode="reflect"``)方式填补,因此四个角落会出现原图折返映入的现象(这是已知的设计限制,像单据倾斜校正那种想以背景色填补边框外的用途并不适合直接使用)。相当于HALCON的``rotate_image``(Rotate an image about its center.)。 · 示例: `gallery2d_geometry`
- `rotate_img` (halcon: `rotate_image`) `image → image` GPU: 有(rotate_img) — 绕图像中心旋转 ``-45° + 90°·a``(a=0.5 → 0°)。``b`` 未使用。 · 示例: `gallery2d_geometry`
- `sk_swirl` (halcon: `polar_trans_image`) `image → image` GPU: 无 — 漩涡变形(swirl warp)。围绕图像中心,越靠近中心旋转幅度越大的非线性几何变换 —— 一种基于极坐标变换应用的扭曲效果。 · 示例: `gallery2d_geometry`
- `tf_log_polar` `image → image` GPU: 有(许可列表) — log_polar：以图像中心为基准，在对数极坐标网格上对图像重新采样。 · 示例: `gallery2d_geometry`
- `transpose_region` (halcon: `transpose_region`) `region → region` GPU: 无 — 将区域(二值掩码)转置(``x.T``,即关于对角线的镜像=行列互换)。类别为geometry,但输入/输出类型为``region``。作为几何变换的一种以``_sh_geom``实现,但由于转置不涉及插值,即使经过``build()``的``_rebinarise``,数值也不会改变(本来就已经是{0,1})。相当于HALCON的``transpose_region``(Reflect a region about a point.)(严格来说与HALCON「关于点的反转」是不同的变换,此处是以矩阵转置=关于对角线的反转来近似)。 · 示例: `gallery2d_geometry`
- `xcv2_warp_logpolar` `image → image` GPU: 无 — 使用对数极坐标变换（log-polar transform）将图像映射到（半径, 角度）平面。 · 示例: `gallery2d_geometry`
- `xpil_offset` `image → image` GPU: 无 — 以环状（wrap-around）方式平移图像。调用 ``PIL.ImageChops.offset``——这是一种循环平移，超出画面边缘的像素会出现在相对的另一端，与普通平移不同，图像边缘不会变黑。 · 示例: `gallery2d_geometry`
- `zoom_image_factor` (halcon: `zoom_image_factor`) `image → image` GPU: 有(zoom_image_factor) — 在高度方向与宽度方向拥有独立倍率(``0.7+0.6*a``、``0.7+0.6*b``)的非等向缩放。以中心为基准通过仿射变换进行缩放,画布尺寸保持不变(超出/剩余部分以反射填补)。相当于HALCON的``zoom_image_factor``(Zoom an image by a given factor.),并与HALCON相同,采用**两个倍率**(ScaleHeight/ScaleWidth)。 · 示例: `gallery2d_geometry`, `poc_pv_thermal_survey`
- `zoom_image_size` (halcon: `zoom_image_size`) `image → image` GPU: 仅在链中(许可列表) — 重新取样到目标尺寸(高度``H*(0.5+a)``、宽度``W*(0.5+b)``)的缩放。相较于``zoom_image_factor``采用两个倍率,此op则是分别独立指定高与宽的**尺寸**本身——在HALCON语义上是不同的东西。不过由于此流水线的``image``契约要求「以与输入相同的画布尺寸返回」,因此重新取样的结果会放置在原始解析度画布的左上角,空白处补0,超出部分则被裁切(实际上图像被缩小/放大在外观上可以看出,但阵列的shape本身不变)。相当于HALCON的``zoom_image_size``(Zoom an image to a given size.)。 · 示例: `gallery2d_geometry`
- `zoom_region` (halcon: `zoom_region`) `region → region` GPU: 有(许可列表) — 各向同性地缩放区域（横纵同倍率）。以倍率 ``s = 0.7+0.6a``（0.7〜1.3 倍）为准，以中心为基准放大缩小，边界外用镜像（reflect）填充，然后通过 ``_rebinarise`` 以 0.5 阈值恢复为二值区域。b 未使用。 · 示例: `gallery2d_geometry`

#### 2d / gray (49)
- `banding_map` `image → image` GPU: 有(许可列表) — 返回**可见色阶断层(色带)的位置**。``a`` 为位数，``b`` 为窗口。 · 示例: `gallery2d_gray_arith`
- `bit_not` (halcon: `bit_not`) `image → image` GPU: 有(bit_not) — 灰度反转（负片/正片反转）。实现为 ``1 - x``（作为 [0,1] 连续值的反转），a、b 未使用。 · 示例: `gallery2d_gray_arith`
- `clahe` `image → image` GPU: 有(许可列表) — 对比度受限的自适应直方图均衡(分块,双线性拼接)。 · 示例: `gallery2d_gray_arith`, `poc_dehazing`
- `companding_mu_law` `image → image` GPU: 有(companding_mu_law) — μ 律压扩(compand = compress + expand)。``a`` 为 μ，``b`` 为位数。 · 示例: `gallery2d_gray_arith`
- `cv_clahe` `image → image` GPU: 无 — CLAHE（对比度受限自适应直方图均衡化，OpenCV 实现）。与 sk_adapthist 思路相同的局部对比度增强，但使用 OpenCV 的实现方式和分块（tile）方案。 · 示例: `gallery2d_gray_arith`
- `cv_trunc` (halcon: `scale_image`) `image → image` GPU: 无 — 高光阶调截断（THRESH_TRUNC，OpenCV 实现）。所有比指定值更亮的像素都会被截断为该值，其余像素保持不变 —— 一种只压缩高光而不触及暗部的阶调操作。 · 示例: `gallery2d_gray_arith`
- `dither_floyd_steinberg` `image → image` GPU: 无 — 误差扩散抖动(Floyd–Steinberg)。``a`` 为位数 1〜8，``b`` 未使用。 · 示例: `gallery2d_gray_arith`
- `dither_ordered` `image → image` GPU: 无 — 用有序抖动(Bayer 矩阵)进行量化。``a`` 为位数 1〜8，``b`` 为矩阵大小。 · 示例: `gallery2d_gray_arith`
- `equ_histo_image` (halcon: `equ_histo_image`) `image → image` GPU: 有(equ_histo_image) — 对整幅图像做直方图均衡化(基于累积分布函数生成色调曲线,256 个直方图柱)。这是一种经典方法,通过拉平偏向暗部或亮部的灰阶分布来提升表观对比度。相当于 HALCON 的 ``equ_histo_image``(Histogram linearization of images)。 · 示例: `gallery2d_gray_arith`
- `equ_histo_image_rect` (halcon: `equ_histo_image_rect`) `image → image` GPU: 仅在链中(许可列表) — 分块直方图均衡化。将图像分割为 ``nb x nb``(``nb=2+4*a``)个区块,并对每个区块独立进行(64 分箱的)直方图均衡化——相较于一次性处理整幅图像的 ``equ_histo_image``,对局部光照不均更为稳健,但区块边界处可能出现阶跃(区块伪影)。相当于 HALCON 的 ``equ_histo_image_rect``(Histogram linearization within a rectangular mask.)。 · 示例: `gallery2d_gray_arith`
- `equalize` (halcon: `equ_histo_image`) `image → image` GPU: 有(equalize_image) — 直方图均衡化（线性化）。相当于 HALCON 的 ``equ_histo_image``（Histogram linearization of images）。 · 示例: `gallery2d_gray_arith`, `poc_dehazing`
- `f2_bit_slice` (halcon: `bit_slice`) `image → image` GPU: 有(许可列表) — 8 位量化后提取一个位平面。 0..1 中的归一化“a”选择平面“round(7*a)”（0 = LSB，1 = MSB）； ``b`` 被忽略。返回 {0,1}。 · 示例: `gallery2d_gray_arith`
- `f2_expand_domain` (halcon: `expand_domain_gray`) `image → image` GPU: 有(许可列表) — 将图像的定义域(非零区域)向外扩展一个边距,新增的像素设为最近的已有灰度值。``a`` 设置边距宽度(1..7 px);``b`` 被忽略。 · 示例: `gallery2d_gray_arith`
- `f2_lut_trans` (halcon: `lut_trans`) `image → image` GPU: 有(f2_lut_trans) — 通过单调(无 gamma)灰度值查找表对图像进行变换。该 256 项表是一条对比度 sigmoid 曲线，其增益由 ``a`` 设定、拐点由 ``b`` 设定，并按端点归一化使其覆盖 [0,1]；随后图像在其 8 位量化值上进行真正的查表操作。 · 示例: `gallery2d_gray_arith`
- `gamma` (halcon: `pow_image`) `image → image` GPU: 有(gamma_image) — 伽马校正（幂次变换）。相当于 HALCON 的 ``pow_image``（Raise an image to a power.）。 · 示例: `gallery2d_gray_arith`, `poc_itof_multifreq`, `poc_simcal_thin_film`
- `gamma_image` (halcon: `gamma_image`) `image → image` GPU: 无 — 伽玛校正 ``x ** (0.3 + 2.5*a)``。``a`` 越接近 0，指数越接近 0.3，会提升暗部；``a`` 越接近 1，指数越接近 2.8，会压暗暗部、增强对比度。用作 HALCON ``gamma_image``（Perform a gamma encoding or decoding of an image.）的替代。 · 示例: `gallery2d_gray_arith`
- `illuminate` (halcon: `illuminate`) `image → image` GPU: 有(illuminate) — 非锐化蒙版式的局部对比度增强。将高斯模糊(半径 ``3+12*a``)得到的 ``sm`` 与原图相减得到差分 ``x - sm``,再加回原图,从而在保留低频照明不均的同时提升局部边缘与纹理。是 HALCON 的 ``illuminate``(Illuminate image.)的替代实现。 · 示例: `gallery2d_gray_arith`, `poc_document_scan`, `poc_matrix_code_reading`
- `image_standardize` `image → image` GPU: 无 — 对图像进行标准化，并将带符号偏差映射为 ``[0,1]`` 强度图像。 · 示例: `gallery2d_gray_arith`
- `invert` (halcon: `invert_image`) `image → image` GPU: 有(invert_image) — 灰阶反转（负片/正片反转）。相当于 HALCON 的 ``invert_image``（Invert an image.）。 · 示例: `gallery2d_gray_arith`, `genspark_external_review`, `poc_ai_built_inspection_scored`, `poc_tacscalib_sphere_lut`
- `invert_image` (halcon: `invert_image`) `image → image` GPU: 有(invert_image@twin) — 通过 ``1.0 - x`` 反转阶调（负片/正片反转）。这与 HALCON 的 ``invert_image``（Invert an image.）直接对应，是严格等价的运算，而非近似。 · 示例: `gallery2d_gray_arith`, `mcp_task_score`, `poc_metal_grain_size`
- `it_bit_lshift` (halcon: `bit_lshift`) `image → image` GPU: 有(许可列表) — bit_lshift:先做 8 位量化,再将每个像素左移 round(a*7) 位,按 8 位掩码取回(如 HALCON 一样发生环绕),最后映射回 [0,1]。``b`` 被忽略。 · 示例: `gallery2d_gray_arith`
- `it_bit_mask` (halcon: `bit_mask`) `image → image` GPU: 有(许可列表) — bit_mask:将 8 位图像与常量位掩码 round(a*255) 做逻辑与运算。``b`` 被忽略。 · 示例: `gallery2d_gray_arith`
- `it_bit_rshift` (halcon: `bit_rshift`) `image → image` GPU: 有(许可列表) — bit_rshift:先做 8 位量化,再将每个像素右移 round(a*7) 位(相当于整数除以 2**shift,得到更粗糙、更暗的图像)。``b`` 被忽略。 · 示例: `gallery2d_gray_arith`
- `it_convert_image_type` (halcon: `convert_image_type`) `image → image` GPU: 有(许可列表) — convert_image_type:通过量化到 L = round(2 + a*254) 个均匀分布的等级来模拟向低精度像素类型的转换(位深度降低)。``b`` 被忽略。 · 示例: `gallery2d_gray_arith`
- `monotony` (halcon: `monotony`) `image → image` GPU: 有(许可列表) — 以 [0,1] 返回像素值在其 8 邻域中排第几大（单调性，monotony）。计算比中心小的邻居数量并除以 8，因此值为 1.0 表示中心大于所有邻居的局部最大值，0.0 表示接近局部最小值。a、b 未使用。 · 示例: `gallery2d_gray_arith`
- `pow_image` (halcon: `pow_image`) `image → image` GPU: 仅在链中(许可列表) — 该实现指向与 ``gamma_image`` 完全相同的函数（``_sh_lut`` 中 ``kind: "gamma"`` 的分支）。也就是说，``pow_image`` 与 ``gamma_image`` 在此后端上的计算结果是一致的 —— 在 HALCON 中它们是不同的算子（明确指定指数的 ``pow_image`` 与用于编码/解码的 ``gamma_image``），但在此处这两个替代实现的实体是重复的（明确记为近似的局限）。 · 示例: `gallery2d_gray_arith`
- `quantization_error` `image → image` GPU: 有(许可列表) — 将量化损失的量 ``|x - Q(x)|`` 除以 ``Δ/2`` 后变换到 ``[0,1]`` 的图。 · 示例: `gallery2d_gray_arith`
- `quantize_lloyd_max` `image → image` GPU: 有(许可列表) — 按输入分布进行的**最优**量化(Lloyd–Max，1-D k-means)。 · 示例: `gallery2d_gray_arith`
- `quantize_uniform` `image → image` GPU: 仅在链中(许可列表) — 均匀量化器(**舍入**)。``a`` 为位数 1〜8，``b`` 未使用。 · 示例: `gallery2d_gray_arith`
- `scale_clip` (halcon: `scale_image`) `image → image` GPU: 有(scale_image) — 通过增益和偏移进行线性灰阶变换。相当于 HALCON 的 ``scale_image``（Scale the gray values of an image.）。 · 示例: `gallery2d_gray_arith`
- `scale_image` (halcon: `scale_image`) `image → image` GPU: 有(scale_image@twin) — 线性灰度缩放 ``clip((0.5 + 1.5*a) * x + (b - 0.5), 0, 1)``。这是一个同时调整斜率(对比度)和偏移量(亮度)的线性 LUT,超出范围的值会被裁剪到 [0,1]。相当于 HALCON 的 ``scale_image``(Scale the gray values of an image.)。 · 示例: `gallery2d_gray_arith`
- `scale_image_max` (halcon: `scale_image_max`) `image → image` GPU: 仅在链中(许可列表) — 将图像的最小值到最大值拉伸至充满 [0,1] 区间的 min-max 归一化(``(x - min) / (max - min)``,常数图像则保持不变)。相当于 HALCON 的 ``scale_image_max``(Maximum gray value spreading in the value range 0 to 255.)(此处值域遵循 [0,1] 约定,而非 0~255)。 · 示例: `gallery2d_gray_arith`
- `sigmoid` (halcon: `scale_image_max`) `image → image` GPU: 有(sigmoid_image) — 使用逻辑（sigmoid）函数进行 S 形对比度增强。对应到 HALCON 的 ``scale_image_max``（Maximum gray value spreading in the value range 0 to 255.），但处理内容与将动态范围拉伸到最大的 ``scale_image_max`` 不同（与其说是近似，不如说是不同的处理）。 · 示例: `gallery2d_gray_arith`, `gallery_drive_world_io`
- `sk_adapthist` `image → image` GPU: 无 — CLAHE(对比度受限自适应直方图均衡化,Contrast Limited Adaptive Histogram Equalization)。将图像划分为若干小区域并对每个区域局部地进行直方图均衡化,即使在明暗差异较大的图像中也能提升局部对比度。 · 示例: `gallery2d_gray_arith`
- `sk_adjust_log` (halcon: `log_image`) `image → image` GPU: 有(许可列表) — 对数阶调变换(log transform)。使用 ``out = gain * log(1 + in)`` 型对数曲线来提亮暗部的阶调校正 —— 用途与伽马校正类似,但是一条只对暗部提亮更强的非线性曲线。 · 示例: `gallery2d_gray_arith`
- `sk_autolevel` (halcon: `scale_image_max`) `image → image` GPU: 无 — 局部自动色阶。将每个像素周围局部直方图的最小值〜最大值拉伸至完整的 0〜255 范围 —— 这是一种按位置(而非全局阶调)最大化对比度的自适应色阶校正。 · 示例: `gallery2d_gray_arith`
- `sk_enhance_contrast` `image → image` GPU: 无 — 局部对比度增强。判断每个像素更接近局部邻域内的最大值还是最小值,并替换为更接近的那一方 —— 具有中间值的像素被推向两个极端,从而提升表观对比度(有时会产生接近二值化的效果)。 · 示例: `gallery2d_gray_arith`
- `xcv_detail_enhance` `image → image` GPU: 无 — OpenCV 的 detailEnhance（细节增强）。 · 示例: `gallery2d_gray_arith`
- `xkor_clahe` `image → image` GPU: 无 — CLAHE(对比度受限自适应直方图均衡化)。调用 ``kornia.enhance.equalize_clahe``。 · 示例: `gallery2d_gray_arith`
- `xpil_autocontrast` `image → image` GPU: 无 — 自动对比度（裁切直方图两端并拉伸至全范围）。调用 ``PIL.ImageOps.autocontrast``。 · 示例: `gallery2d_gray_arith`
- `xpil_contrast` `image → image` GPU: 无 — 对比度调整（以图像的平均亮度为基准的线性拉伸）。调用 ``PIL.ImageEnhance.Contrast``。 · 示例: `gallery2d_gray_arith`
- `xpil_detail` `image → image` GPU: 无 — Pillow 的细节增强滤镜。使用 ``PIL.ImageFilter.DETAIL`` 的固定卷积核提升细节的对比度（接近锐化，但系数更偏向强调纹理而非边缘）。 · 示例: `gallery2d_gray_arith`
- `xpil_edge_enhance` `image → image` GPU: 无 — Pillow 的边缘增强滤镜（增强版）。使用 ``PIL.ImageFilter.EDGE_ENHANCE_MORE`` 的固定卷积核提升边缘附近的对比度（比 ``EDGE_ENHANCE`` 更强的版本）。 · 示例: `gallery2d_gray_arith`
- `xpil_posterize` `image → image` GPU: 无 — 色调分离（减少灰阶数）。调用 ``PIL.ImageOps.posterize``，通过减少各通道的有效位数来降低颜色数量。 · 示例: `gallery2d_gray_arith`
- `xpil_solarize` `image → image` GPU: 无 — 曝光过度效果（胶片显影中的中间调反转效果）。调用 ``PIL.ImageOps.solarize``，将超过阈值的像素值反转。 · 示例: `gallery2d_gray_arith`
- `xsk3_integral_image` `image → image` GPU: 有(许可列表) — 积分图(summed-area table，skimage ``transform.integral_image``)。存储从原点到各像素累计和的图像，使得任意矩形区域的总和只需参照 4 个点即可计算——用于加速 Haar 特征和矩形滤波器的经典预处理。为便于显示，按最大值归一化后压缩。 · 示例: `gallery2d_gray_arith`
- `xsk3_rank_equalize` `image → image` GPU: 无 — 局部直方图均衡化(skimage ``filters.rank.equalize``)。对每个圆盘邻域分别进行直方图均衡化的自适应对比度增强，相比全局的 ``equalize`` op，对局部明暗不均更具鲁棒性。 · 示例: `gallery2d_gray_arith`
- `xsk3_rank_subtract_mean` `image → image` GPU: 无 — 局部均值差分(skimage ``filters.rank.subtract_mean``)。返回每个像素减去其圆盘邻域平均亮度后得到的差值。skimage 的实现为防止下溢，将差值缩小为 1/2 并平移到取值范围的中央。用于抵消全局明暗不均并增强局部对比度。 · 示例: `gallery2d_gray_arith`
- `xsp_detrend_flatten` `image → image` GPU: 有(许可列表) — 一种展平滤镜，先分别去除图像整体在纵向与横向的一次趋势（倾斜），再进行归一化。 · 示例: `gallery2d_gray_arith`

#### 2d / halcon_ext (81)
- `hx_add_noise_contour` (halcon: `add_noise_white_contour_xld`) `contour → contour` GPU: 无 — 给 contour 点加白高斯噪声(std 由 a 给出,固定 seed 因而确定)。 · 示例: `gallery2d_halcon_ext`
- `hx_char_threshold` (halcon: `char_threshold`) `image → region` GPU: 无 — 从明亮背景中提取暗字符(region):以 thresh = mean − k*std(k 由 a)取下侧。 · 示例: `gallery2d_halcon_ext`
- `hx_clip_contours` (halcon: `clip_contours_xld`) `contour → contour` GPU: 无 — 把 contour 裁到图像域(保留中央 margin a/b 的矩形),去掉越界点。 · 示例: `gallery2d_halcon_ext`
- `hx_clip_end_points` (halcon: `clip_end_points_contours_xld`) `contour → contour` GPU: 无 — 把每条 contour 的两端各切掉 k 个点(k 由 a)。 · 示例: `gallery2d_halcon_ext`
- `hx_clip_region_rel` (halcon: `clip_region_rel`) `region → region` GPU: 仅在链中(许可列表) — 相对区域外接矩形裁剪(每边削去比例 a)。 · 示例: `gallery2d_halcon_ext`
- `hx_close_edges` (halcon: `close_edges`) `image → image` GPU: 仅在链中(许可列表) — 闭合边缘幅值图中的缺口:按阈值 a 二值化 → 形态学闭运算(半径 b)。 · 示例: `gallery2d_halcon_ext`, `poc_metal_grain_size`
- `hx_close_edges_length` (halcon: `close_edges_length`) `image → image` GPU: 有(许可列表) — 在 close_edges 之上,再去掉长度(像素数)低于阈值的短边缘碎片。 · 示例: `gallery2d_halcon_ext`
- `hx_closing` (halcon: `closing`) `region → region` GPU: 有(许可列表) — 用圆盘结构元素对 region 做闭运算(closing,先膨胀后腐蚀)。相当于 HALCON 的 ``closing``(对 region 做闭运算)。 · 示例: `gallery2d_halcon_ext`
- `hx_cooc_feature` (halcon: `cooc_feature_image`) `image → feature` GPU: 无 — 量化后构建距离 d 的水平共生矩阵,返回 Haralick 对比度(a=距离,b 选角度)。 · 示例: `gallery2d_halcon_ext`
- `hx_crop_contours` (halcon: `crop_contours_xld`) `contour → contour` GPU: 无 — 把 contour 裁到中央 a×b 比例的矩形内(只保留范围内的点)。 · 示例: `gallery2d_halcon_ext`
- `hx_detect_edge_segments` (halcon: `detect_edge_segments`) `image → region` GPU: 无 — 检测直线状边缘碎片:用 NMS 细化 → 在连通成分中保留 PCA 判定为细长(直线状)的。 · 示例: `find_ops_by_meaning`, `gallery2d_halcon_ext`
- `hx_dilation1` (halcon: `dilation1`) `region → region` GPU: 仅在链中(许可列表) — 用圆盘结构元素对 region 做膨胀(dilation)。相当于 HALCON 的 ``dilation1``(对 region 做膨胀)。 · 示例: `gallery2d_halcon_ext`
- `hx_dilation2` (halcon: `dilation2`) `region → region` GPU: 仅在链中(许可列表) — 带参考点的膨胀:膨胀后按参考点偏移(由 b 平移)。 · 示例: `gallery2d_halcon_ext`
- `hx_disparity_to_xyz` (halcon: `disparity_image_to_xyz`) `image → image` GPU: 仅在链中(许可列表) — 由视差图计算深度 Z = f*baseline/disparity(焦距/基线由 a,b 可变)。归一化 Z。 · 示例: `gallery2d_halcon_ext`
- `hx_dist_ellipse_contour` (halcon: `dist_ellipse_contour_xld`) `contour → feature` GPU: 无 — contour 点到拟合椭圆边界的平均距离(越小越接近椭圆;feature)。 · 示例: `gallery2d_halcon_ext`
- `hx_dist_ellipse_points` (halcon: `dist_ellipse_contour_points_xld`) `contour → feature` GPU: 无 — contour 各点到拟合椭圆边界的最大距离(逐点距离取 max 聚合;feature)。 · 示例: `gallery2d_halcon_ext`
- `hx_dist_rect2_points` (halcon: `dist_rectangle2_contour_points_xld`) `contour → feature` GPU: 无 — contour 各点到最小面积外接矩形各边的归一化距离的平均(feature)。 · 示例: `gallery2d_halcon_ext`
- `hx_distance_pc` (halcon: `distance_pc`) `contour → feature` GPU: 无 — 从查询点(归一化 a,b)到 contour 的最小距离(feature)。 · 示例: `gallery2d_halcon_ext`
- `hx_distance_pr` (halcon: `distance_pr`) `region → feature` GPU: 无 — 从查询点(归一化 a,b)到 region 的最小距离(feature),用距离变换。 · 示例: `gallery2d_halcon_ext`
- `hx_distance_sc` (halcon: `distance_sc`) `contour → feature` GPU: 无 — 从水平线段(行 a*H)到 contour 的最小距离(feature)。 · 示例: `gallery2d_halcon_ext`
- `hx_erosion1` (halcon: `erosion1`) `region → region` GPU: 仅在链中(许可列表) — 用圆盘结构元素对 region 做腐蚀(erosion)。相当于 HALCON 的 ``erosion1``(对 region 做腐蚀)。 · 示例: `gallery2d_halcon_ext`
- `hx_estimate_al_am` (halcon: `estimate_al_am`) `image → feature` GPU: 无 — 估计 albedo(反射率)与 ambient(环境光):albedo ~ 亮度范围,这里返回 albedo。 · 示例: `gallery2d_halcon_ext`
- `hx_estimate_sl_al_lr` (halcon: `estimate_sl_al_lr`) `image → feature` GPU: 无 — Lee-Rosenfeld:估计光源的 slant(天顶角,0=正面 ~ pi/2=侧向)。归一化到 [0,1]。 · 示例: `gallery2d_halcon_ext`
- `hx_estimate_sl_al_zc` (halcon: `estimate_sl_al_zc`) `image → feature` GPU: 无 — Zheng-Chellappa:用梯度能量修正后估计 slant。 · 示例: `gallery2d_halcon_ext`
- `hx_estimate_tilt_lr` (halcon: `estimate_tilt_lr`) `image → feature` GPU: 无 — Lee-Rosenfeld:光源方位角 tilt = atan2(<Ey>, <Ex>)(平均梯度方向)。归一化到 [0,1]。 · 示例: `gallery2d_halcon_ext`
- `hx_estimate_tilt_zc` (halcon: `estimate_tilt_zc`) `image → feature` GPU: 无 — Zheng-Chellappa:用归一化梯度的平均方向估计 tilt(与局部对比度无关)。 · 示例: `gallery2d_halcon_ext`
- `hx_expand_region` (halcon: `expand_region`) `region → region` GPU: 无 — 填补区域之间的缝隙(region -> region):用膨胀让二值区域连通起来。 · 示例: `gallery2d_halcon_ext`
- `hx_fill_interlace` (halcon: `fill_interlace`) `image → image` GPU: 仅在链中(许可列表) — 插补两场视频半帧(把奇数行换成相邻偶数行的平均 = 去隔行)。 · 示例: `gallery2d_halcon_ext`
- `hx_fit_circle_contour` (halcon: `fit_circle_contour_xld`) `contour → feature` GPU: 无 — 用 Kåsa 代数法对 contour 点拟合圆,返回拟合残差(RMS)(越小越接近圆)。 · 示例: `gallery2d_halcon_ext`
- `hx_fit_ellipse_contour` (halcon: `fit_ellipse_contour_xld`) `contour → feature` GPU: 无 — 由二阶矩拟合椭圆,返回轴比(短/长:正圆为 1,越细长越接近 0)。 · 示例: `gallery2d_halcon_ext`
- `hx_fit_rectangle2_contour` (halcon: `fit_rectangle2_contour_xld`) `contour → feature` GPU: 无 — 拟合最小面积有向矩形,返回其长宽比(短边/长边;feature)。 · 示例: `gallery2d_halcon_ext`
- `hx_fit_surface1` (halcon: `fit_surface_first_order`) `image → image` GPU: 有(许可列表) — 以最小二乘法将灰度值拟合为一次多项式曲面(平面)。相当于 HALCON 的 ``fit_surface_first_order``(计算灰度值矩并拟合一次曲面)。 · 示例: `gallery2d_halcon_ext`
- `hx_fit_surface2` (halcon: `fit_surface_second_order`) `image → image` GPU: 仅在链中(许可列表) — 以最小二乘法将灰度值拟合为二次多项式曲面。相当于 HALCON 的 ``fit_surface_second_order``(计算灰度值矩并拟合二次曲面)。 · 示例: `gallery2d_halcon_ext`
- `hx_full_domain` (halcon: `full_domain`) `image → region` GPU: 无 — 将图像的定义域(domain)扩展到整个图像范围。相当于 HALCON 的 ``full_domain``(将图像的定义域扩展到最大)。 · 示例: `gallery2d_halcon_ext`
- `hx_fuzzy_measure_pairs` (halcon: `fuzzy_measure_pairs`) `image → feature` GPU: 无 — 在中央水平剖面上数边缘对(亮条的上升边界 → 下降边界)(1D 计量)。 · 示例: `gallery2d_halcon_ext`
- `hx_gabor` (halcon: `convol_gabor`) `image → image` GPU: 无 — Gabor 滤波(方位 theta=a*pi,频率 freq=0.08+0.35b)。返回响应的幅度。 · 示例: `gallery2d_halcon_ext`
- `hx_gen_bandfilter` (halcon: `gen_bandfilter`) `image → image` GPU: 仅在链中(许可列表) — 理想带通滤波图像(频域圆环,中心半径 a、宽度 b)。与 gen_bandpass 是不同的算子。 · 示例: `gallery2d_halcon_ext`
- `hx_gen_bandpass` (halcon: `gen_bandpass`) `image → image` GPU: 无 — 理想带通(频域圆环掩码,内半径 a、带宽 b)。 · 示例: `gallery2d_halcon_ext`
- `hx_gen_checker_region` (halcon: `gen_checker_region`) `image → region` GPU: 仅在链中(许可列表) — 生成棋盘格(checkerboard)图案的 region。相当于 HALCON 的 ``gen_checker_region``(生成棋盘格区域)。 · 示例: `gallery2d_halcon_ext`
- `hx_gen_circle` (halcon: `gen_circle`) `image → region` GPU: 有(许可列表) — 生成圆形 region。相当于 HALCON 的 ``gen_circle``(生成一个圆)。 · 示例: `gallery2d_halcon_ext`
- `hx_gen_circle_sector` (halcon: `gen_circle_sector`) `image → region` GPU: 有(许可列表) — 圆扇形 region(起始角 b*2pi,扫过 a*2pi)。 · 示例: `gallery2d_halcon_ext`
- `hx_gen_derivative_filter` (halcon: `gen_derivative_filter`) `image → image` GPU: 有(许可列表) — 频域微分滤波器。``a`` 为微分阶数,``b`` 为方向。 · 示例: `gallery2d_halcon_ext`
- `hx_gen_disc_se` (halcon: `gen_disc_se`) `image → region` GPU: 有(许可列表) — 生成圆盘结构元素作为 region(半径 a)。 · 示例: `gallery2d_halcon_ext`
- `hx_gen_ellipse` (halcon: `gen_ellipse`) `image → region` GPU: 有(许可列表) — 生成轴对齐(axis-aligned)的椭圆 region。相当于 HALCON 的 ``gen_ellipse``(生成一个椭圆)——固定方向的近似,原版还接受旋转角参数。 · 示例: `gallery2d_halcon_ext`
- `hx_gen_ellipse_sector` (halcon: `gen_ellipse_sector`) `image → region` GPU: 有(许可列表) — 生成椭圆扇形(sector)region。相当于 HALCON 的 ``gen_ellipse_sector``(生成椭圆扇形)。 · 示例: `gallery2d_halcon_ext`
- `hx_gen_empty_region` (halcon: `gen_empty_region`) `image → region` GPU: 无 — 生成空(全部像素为 0)的 region。相当于 HALCON 的 ``gen_empty_region``(生成空 region)。 · 示例: `gallery2d_halcon_ext`
- `hx_gen_grid_region` (halcon: `gen_grid_region`) `image → region` GPU: 无 — 生成格线(grid-line)region。相当于 HALCON 的 ``gen_grid_region``(由直线或像素生成 region)中格子图案的简化版本。 · 示例: `gallery2d_halcon_ext`
- `hx_gen_highpass` (halcon: `gen_highpass`) `image → image` GPU: 仅在链中(许可列表) — 生成理想高通滤波器的频域掩膜。相当于 HALCON 的 ``gen_highpass``(生成理想高通滤波器)。 · 示例: `gallery2d_halcon_ext`
- `hx_gen_image_proto` (halcon: `gen_image_proto`) `image → image` GPU: 无 — 生成与输入同尺寸的常数灰度图(值 a)。 · 示例: `gallery2d_halcon_ext`
- `hx_gen_lowpass` (halcon: `gen_lowpass`) `image → image` GPU: 有(许可列表) — 理想低通滤波图像(频域中心圆盘掩码,截止半径 a)。 · 示例: `gallery2d_halcon_ext`
- `hx_gen_parallel_contour` (halcon: `gen_parallel_contour_xld`) `contour → contour` GPU: 无 — 生成每条 contour 的平行(法向偏移)contour(距离由 (a−0.5) 带符号给出)。 · 示例: `gallery2d_halcon_ext`
- `hx_gen_rectangle2` (halcon: `gen_rectangle2`) `image → region` GPU: 有(许可列表) — 生成任意角度的矩形 region。相当于 HALCON 的 ``gen_rectangle2``(生成任意方向的矩形)。 · 示例: `gallery2d_halcon_ext`
- `hx_get_domain` (halcon: `get_domain`) `image → region` GPU: 无 — 把图像的定义域取为 region(默认为整幅)。 · 示例: `gallery2d_halcon_ext`
- `hx_histo_to_thresh` (halcon: `histo_to_thresh`) `image → region` GPU: 仅在链中(许可列表) — 由直方图的谷确定阈值并二值化(谷检测,而非 Otsu 的方差准则 = 另一个算子)。 · 示例: `gallery2d_halcon_ext`
- `hx_lowlands` (halcon: `lowlands`) `image → region` GPU: 无 — 检测灰度的洼地(局部极小的平坦域):与邻域最小值相等的像素 region。 · 示例: `gallery2d_halcon_ext`
- `hx_mean_shape` (halcon: `mean_image_shape`) `image → image` GPU: 仅在链中(许可列表) — 用任意掩码(圆盘)做均值平滑。半径 r 由 a 可变(与矩形均值是不同算子)。 · 示例: `gallery2d_halcon_ext`
- `hx_moments_any_xld` (halcon: `moments_any_xld`) `contour → feature` GPU: 无 — 全部 contour 点的二阶中心矩(展布),归一化 feature。 · 示例: `gallery2d_halcon_ext`
- `hx_move_region` (halcon: `move_region`) `region → region` GPU: 无 — 平移 region(dy=a, dx=b,视为以 0 为中心的偏移)。 · 示例: `gallery2d_halcon_ext`
- `hx_nonmax_dir` (halcon: `nonmax_suppression_dir`) `image → image` GPU: 无 — 沿梯度方向的非极大值抑制(Canny 的 NMS 阶段)。把边缘细化到 1 像素。 · 示例: `gallery2d_halcon_ext`
- `hx_opening` (halcon: `opening`) `region → region` GPU: 有(许可列表) — 用圆盘结构元素对 region 做开运算(opening,先腐蚀后膨胀)。相当于 HALCON 的 ``opening``(对 region 做开运算)。 · 示例: `gallery2d_halcon_ext`
- `hx_plane_deviation` (halcon: `plane_deviation`) `image → image` GPU: 有(许可列表) — 灰度相对一次平面拟合的偏差 |v − plane|(平面度/缺陷检测)。 · 示例: `gallery2d_halcon_ext`, `poc_ai_built_inspection_scored`
- `hx_plateaus_center` (halcon: `plateaus_center`) `image → region` GPU: 无 — 检测灰度平坦域(梯度≈0)的中心:把平坦连通成分的重心像素作为 marker region。 · 示例: `gallery2d_halcon_ext`
- `hx_polar_trans_inv` (halcon: `polar_trans_contour_xld_inv`) `contour → contour` GPU: 无 — 把 contour 点视为 (radius, angle) 并逆变换回直角坐标(polar_trans 的逆)。 · 示例: `gallery2d_halcon_ext`
- `hx_radial_distort_contour` (halcon: `change_radial_distortion_contours_xld`) `contour → contour` GPU: 无 — 对 contour 施加径向畸变 r' = r(1 + k r^2)(k 由 (a−0.5) 给出:桶形/枕形)。 · 示例: `gallery2d_halcon_ext`
- `hx_rectangle1_domain` (halcon: `rectangle1_domain`) `image → region` GPU: 仅在链中(许可列表) — 把图像的定义域缩小为轴对齐矩形(中央 a×b 比例)的 region。 · 示例: `gallery2d_halcon_ext`
- `hx_region_to_label` (halcon: `region_to_label`) `image → image` GPU: 仅在链中(许可列表) — 把按阈值 a 二值化后区域的连通成分转成标签图(归一化)。 · 示例: `gallery2d_halcon_ext`
- `hx_region_to_mean` (halcon: `region_to_mean`) `image → image` GPU: 有(许可列表) — 把每个连通区域涂成其平均灰度(image -> image)。以阈值 a 分前景/背景后 label 化。 · 示例: `gallery2d_halcon_ext`
- `hx_regress_contours` (halcon: `regress_contours_xld`) `contour → feature` GPU: 无 — 对每条 contour 拟合回归直线,返回平均残差(偏离直线的程度;feature)。越小越直。 · 示例: `gallery2d_halcon_ext`
- `hx_select_xld_point` (halcon: `select_xld_point`) `contour → contour` GPU: 无 — 只保留外接矩形包含查询点(归一化 a,b)的 contour(filter)。 · 示例: `gallery2d_halcon_ext`
- `hx_shade_height_field` (halcon: `shade_height_field`) `image → image` GPU: 有(许可列表) — 用 Lambert 着色渲染高度场 v(法线×光源)。光源方位 a、仰角 b。 · 示例: `gallery2d_halcon_ext`
- `hx_smallest_circle_xld` (halcon: `smallest_circle_xld`) `contour → feature` GPU: 无 — 全部 contour 点最小包围圆(近似=以重心为心)的半径,归一化 feature。 · 示例: `gallery2d_halcon_ext`
- `hx_smallest_rect1_xld` (halcon: `smallest_rectangle1_xld`) `contour → feature` GPU: 无 — 全部 contour 点轴对齐外接矩形的面积比(feature)。 · 示例: `gallery2d_halcon_ext`
- `hx_smallest_rect2_xld` (halcon: `smallest_rectangle2_xld`) `contour → feature` GPU: 无 — 最小面积有向矩形的面积比(矩形面积 / 图像面积;feature)。 · 示例: `gallery2d_halcon_ext`
- `hx_sort_contours` (halcon: `sort_contours_xld`) `contour → contour` GPU: 无 — 按相对位置(重心 row→col)对 contour 排序。 · 示例: `gallery2d_halcon_ext`
- `hx_split_contours` (halcon: `split_contours_xld`) `contour → contour` GPU: 无 — 在支配点处(RDP)把每条 contour 分割成线段(容差 eps 由 a)。 · 示例: `gallery2d_halcon_ext`, `poc_screw_thread_metrology`
- `hx_split_skeleton_region` (halcon: `split_skeleton_region`) `region → region` GPU: 无 — 在分叉点处分割 1 像素宽骨架:去掉 junction(邻域>=3)后取连通成分。 · 示例: `gallery2d_halcon_ext`, `poc_fresco_craquelure`
- `hx_test_closed_xld` (halcon: `test_closed_xld`) `contour → feature` GPU: 无 — 闭合 contour 的比例(端点间距离低于阈值=闭合;feature)。 · 示例: `gallery2d_halcon_ext`
- `hx_test_region_point` (halcon: `test_region_point`) `region → feature` GPU: 无 — region 是否包含该点(归一化 a=行, b=列):1/0(test_region_point)。 · 示例: `gallery2d_halcon_ext`
- `hx_test_region_points` (halcon: `test_region_points`) `region → feature` GPU: 无 — 网格状多点中落在 region 内的比例(test_region_points)。 · 示例: `gallery2d_halcon_ext`
- `hx_test_self_intersect` (halcon: `test_self_intersection_xld`) `contour → feature` GPU: 无 — 自相交 contour 的比例(feature)。判定非相邻的线段对。 · 示例: `gallery2d_halcon_ext`
- `hx_union_adjacent` (halcon: `union_adjacent_contours_xld`) `contour → contour` GPU: 无 — 把端点相近(阈值 a)的 contour 贪心地连接起来。 · 示例: `gallery2d_halcon_ext`

#### 2d / intensity-transform (1)
- `xmh_soft` `image → image` GPU: 无 — 软阈值处理（``mahotas.thresholding.soft_threshold``，收缩）。将绝对值小于阈值的像素归零，其余像素则朝0方向平移阈值大小。把小波/稀疏信号去噪中常用的处理直接应用到像素值上。 · 示例: `gallery2d_gray_arith`

#### 2d / macro (4)
- `macro_binarize` `image → image` GPU: 有(许可列表) — 由进化搜索发现的固定流水线：``bilateral(a=0.06,b=0.89)`` → ``unsharp(a=0.51,b=0.34)`` → ``bilateral(a=0.04,b=0.24)`` → ``lowpass(a=0.75,b=0.59)`` → ``gopen(a=0.38,b=1.00)`` → ``unsharp(a=0.78,b=0.68)``（6 级：平滑与反锐化掩模交替叠加，再用低通滤波和灰度开运算整理，最后再次锐化）。 · 示例: `gallery2d_physics_alife_3d`
- `macro_denoise` `image → image` GPU: 有(许可列表) — 由进化搜索（``evolve.py`` / ``robust.py``）发现的固定流水线：``bilateral(a=0.10,b=0.76)`` → ``bilateral(a=0.12,b=0.27)`` → ``bilateral(a=0.73,b=0.11)``（将现有 op 的双边滤波器以不同强度参数串联 3 级）。 · 示例: `gallery2d_physics_alife_3d`, `sim2real_and_alife`
- `macro_edge` `image → region` GPU: 有(许可列表) — 由进化搜索发现的固定流水线：``gamma(a=0.39,b=0.94)`` → ``bilateral(a=0.22,b=0.08)`` → ``sobel_mag(a=0.81,b=0.80)`` → ``scale_clip(a=1.00,b=0.90)`` → ``otsu(a=0.78,b=0.93)``（5 级：伽马校正 → 平滑 → 梯度强度 → 缩放 → 基于大津判别分析法（Otsu's method）的二值化）。 · 示例: `gallery2d_physics_alife_3d`
- `macro_vol_denoise` `volume → volume` GPU: 有(许可列表) — 由进化搜索发现的固定流水线（3-D 体数据版）：``vol_threshold(a=0.52,b=0.76)`` → ``vol_gaussian(a=0.08,b=0.89)``（2 级：先做 3-D 阈值处理，再做高斯平滑）。 · 示例: `gallery2d_physics_alife_3d`

#### 2d / matching (2)
- `ncc_locate` (halcon: `find_ncc_model`) `image → match` GPU: 有(ncc_locate) — 通过基于归一化互相关（NCC）的模板匹配寻找最佳位置。相当于 HALCON 的 ``find_ncc_model``（Find the best matches of an NCC model in an image.）。 · 示例: `gallery2d_contour_measure`, `mcp_usability`, `poc_code_matching_breakdown`, `poc_search_sweep_width`, `poc_template_tracking`
- `shape_locate` (halcon: `find_shape_model`) `image → match` GPU: 无 — 考虑旋转的模板匹配（基于形状的匹配）。相当于 HALCON 的 ``find_shape_model``（Find the best matches of a shape model in an image.）。 · 示例: `gallery2d_contour_measure`, `poc_template_tracking`

#### 2d / measure1d (5)
- `m1_fuzzy_measure_pos` (halcon: `fuzzy_measure_pos`) `image → contour` GPU: 无 — 对穿过中心的卡尺线上的边缘按模糊隶属度分数进行筛选后返回(相当于 HALCON ``fuzzy_measure_pos``:以模糊判定检测垂直于矩形/圆弧的直线边缘)。 · 示例: `gallery2d_contour_measure`
- `m1_measure_pairs` (halcon: `measure_pairs`) `image → feature` GPU: 无 — 统计穿过中心的卡尺线上"上升沿→下降沿"边缘对(明亮物体的两端)的数量(相当于 HALCON ``measure_pairs``:提取垂直于矩形/圆弧的直线边缘对)。 · 示例: `gallery2d_contour_measure`, `poc_dimensional_inspection`
- `m1_measure_pos` (halcon: `measure_pos`) `image → contour` GPU: 无 — 提取穿过中心的卡尺线上的子像素边缘位置(相当于 HALCON ``measure_pos``:检测垂直于矩形/圆弧的直线边缘)。 · 示例: `gallery2d_contour_measure`, `mcp_task_score`, `poc_dimensional_inspection`
- `m1_measure_projection` (halcon: `measure_projection`) `image → feature` GPU: 无 — 在图像上放置测量用的卡尺线(直线),返回沿垂直方向平均后的亮度剖面的平均值(相当于 HALCON ``measure_projection``:提取垂直于矩形/圆弧的一维投影)。 · 示例: `gallery2d_contour_measure`
- `m1_measure_thresh` (halcon: `measure_thresh`) `image → feature` GPU: 无 — 统计穿过中心的卡尺线上亮度剖面越过指定电平的次数(相当于 HALCON ``measure_thresh``:沿矩形/圆弧提取具有特定灰度值的点)。 · 示例: `gallery2d_contour_measure`

#### 2d / misc (1)
- `identity` (halcon: `copy_image`) `any → any` GPU: 无 — 恒等映射。对应到 HALCON 的 ``copy_image``（Copy an image and allocate new memory for it.），但与分配新内存并复制图像的 ``copy_image`` 不同，本实现只是原样返回输入数组（不进行复制）。 · 示例: `gallery_nary_image_algebra`, `optics_four_f_processor`, `poc_em_branch_territory`, `poc_food_cutting_measure`, `poc_part_locate_features`

#### 2d / morphology (36)
- `bothat` (halcon: `gray_bothat`) `image → image` GPU: 有(gray_bothat) — 黑顶帽（闭运算 − 原图像）。相当于 HALCON 的 ``gray_bothat``（Perform a gray value bottom hat transformation on an image.）。 · 示例: `example_scratch_width`, `gallery2d_morphology`, `poc_ai_built_inspection_scored`, `poc_metal_grain_size`
- `cv_blackhat` (halcon: `gray_bothat`) `image → image` GPU: 无 — 黑帽变换（black-hat，OpenCV 实现）。计算「闭运算结果 − 原图」，只提取位于暗色背景之上、比结构元素更小的暗特征（cv_tophat 的暗版）。 · 示例: `gallery2d_morphology`, `poc_fresco_craquelure`
- `cv_close` (halcon: `gray_closing`) `image → image` GPU: 无 — 灰度形态学闭运算（closing，OpenCV 实现）。先膨胀后腐蚀，填补比结构元素更小的暗孔与缝隙（与 cv_open 的效果相反）。 · 示例: `gallery2d_morphology`
- `cv_dilate` (halcon: `gray_dilation`) `image → image` GPU: 无 — 灰度形态学膨胀（dilation，OpenCV 实现）。将像素替换为其邻域的最大值，从而扩大明亮区域、缩小暗色区域（与 cv_erode 相反）。 · 示例: `gallery2d_morphology`
- `cv_erode` (halcon: `gray_erosion`) `image → image` GPU: 无 — 灰度形态学腐蚀（erosion，OpenCV 实现）。将像素替换为其邻域的最小值，从而缩小明亮区域、扩大暗色区域。 · 示例: `gallery2d_morphology`
- `cv_gradient` (halcon: `gray_range_rect`) `image → image` GPU: 无 — 形态学梯度（OpenCV 实现）。以「膨胀结果 − 腐蚀结果」提取区域的轮廓（边界）—— 与常见的基于微分的边缘检测属于不同体系的轮廓提取方法。 · 示例: `gallery2d_morphology`
- `cv_open` (halcon: `gray_opening`) `image → image` GPU: 无 — 灰度形态学开运算（opening，OpenCV 实现）。先腐蚀后膨胀，消除比结构元素更小的明亮突起和孤立点。 · 示例: `gallery2d_morphology`
- `cv_tophat` (halcon: `gray_tophat`) `image → image` GPU: 无 — 顶帽变换（top-hat，OpenCV 实现）。计算「原图 − 开运算结果」，只提取位于明亮背景之上、比结构元素更小的明亮特征。 · 示例: `gallery2d_morphology`
- `f2_gray_inside` (halcon: `gray_inside`) `image → image` GPU: 无 — 灰度孔填充：对于每个像素，在到图像边界的任何路径上可达到的最低灰度值==通过边界锚定标记的侵蚀对图像进行形态学重建。较亮的墙壁围成的深色盆地向墙壁的高度升高；与边界相连的区域保持黑暗。 ``a`` 设置最大填充深度``h = 0.02 + 0.98*a``； ``b`` 被忽略。 · 示例: `gallery2d_morphology`
- `f2_gray_skeleton` (halcon: `gray_skeleton`) `image → image` GPU: 无 — 灰度图像的细化：对明亮区域(阈值由 ``a`` 设定)进行骨架化，并将 1 像素宽的中轴脊线还原为原始灰度值。``b`` 被忽略。 · 示例: `gallery2d_morphology`
- `gclose` (halcon: `gray_closing`) `image → image` GPU: 有(gray_closing_rect) — 灰度闭运算（先膨胀后腐蚀）。相当于 HALCON 的 ``gray_closing``（Perform a gray value closing on an image.）。 · 示例: `gallery2d_morphology`
- `gdilate` (halcon: `gray_dilation`) `image → image` GPU: 有(gdilate) — 灰度膨胀（向亮侧扩展）。相当于 HALCON 的 ``gray_dilation``（Perform a gray value dilation on an image.）。 · 示例: `gallery2d_morphology`
- `gerode` (halcon: `gray_erosion`) `image → image` GPU: 有(gerode) — 灰度腐蚀（向暗侧扩展）。相当于 HALCON 的 ``gray_erosion``（Perform a gray value erosion on an image.）。 · 示例: `gallery2d_morphology`
- `gopen` (halcon: `gray_opening`) `image → image` GPU: 有(gray_opening_rect) — 灰度开运算（先腐蚀后膨胀）。相当于 HALCON 的 ``gray_opening``（Perform a gray value opening on an image.）。 · 示例: `gallery2d_morphology`
- `gray_bothat` (halcon: `gray_bothat`) `image → image` GPU: 有(gray_bothat@twin) — 黑顶帽(闭运算 − 原图)。仅提取比周围更暗的小结构(孔洞、凹陷),是与 ``gray_tophat`` 明暗相反的运算。相当于 HALCON 的 ``gray_bothat``(Perform a gray value bottom hat transformation on an image.)。 · 示例: `gallery2d_morphology`, `poc_metal_grain_size`
- `gray_closing` (halcon: `gray_closing`) `image → image` GPU: 有(gray_closing) — 灰度闭运算(先膨胀,再以相同结构元素腐蚀)。可填补暗色的小孔洞、凹陷,是与 ``gray_opening`` 成对的运算。相当于 HALCON 的 ``gray_closing``(Perform a gray value closing on an image.)。 · 示例: `gallery2d_morphology`, `poc_solar_el_inspection`
- `gray_closing_rect` (halcon: `gray_closing_rect`) `image → image` GPU: 有(gray_closing_rect@twin) — 使用正方形窗口（边长 ``_k(a)``=3/5/7/9）的灰度闭运算（gray closing，先膨胀后腐蚀）。在填补小的暗孔、凹陷的同时保留大致明暗。b 未使用。 · 示例: `gallery2d_morphology`
- `gray_closing_shape` (halcon: `gray_closing_shape`) `image → image` GPU: 有(许可列表) — 使用圆盘形结构元素的灰度闭运算。与 ``gray_closing`` 的差异仅在于结构元素的形状。相当于 HALCON 的 ``gray_closing_shape``(Perform a gray value closing with a selected mask.)(固定为圆形的近似)。 · 示例: `gallery2d_morphology`
- `gray_dilation` (halcon: `gray_dilation`) `image → image` GPU: 有(gray_dilation) — 灰度膨胀(``ndimage.grey_dilation``)。用矩形结构元素内的最大值替换像素,填补暗色细节,是与 ``gray_erosion`` 成对的运算。相当于 HALCON 的 ``gray_dilation``(Perform a gray value dilation on an image.)。 · 示例: `gallery2d_morphology`
- `gray_dilation_shape` (halcon: `gray_dilation_shape`) `image → image` GPU: 仅在链中(许可列表) — 使用圆形（disk，半径 ``_rad(a)``=1〜4）结构元素的灰度膨胀（gray dilation）——将像素替换为窗口内的最大值。b 未使用。 · 示例: `gallery2d_morphology`
- `gray_erosion` (halcon: `gray_erosion`) `image → image` GPU: 有(gray_erosion) — 灰度腐蚀(``ndimage.grey_erosion``)。用矩形结构元素(默认 shape="rect")内的最小值替换像素,侵蚀明亮的细节。相当于 HALCON 的 ``gray_erosion``(Perform a gray value erosion on an image.)。 · 示例: `gallery2d_morphology`
- `gray_erosion_shape` (halcon: `gray_erosion_shape`) `image → image` GPU: 仅在链中(许可列表) — 使用圆形（disk，半径 ``_rad(a)``=1〜4）结构元素的灰度腐蚀（gray erosion）——将像素替换为窗口内的最小值。b 未使用。 · 示例: `gallery2d_morphology`
- `gray_opening` (halcon: `gray_opening`) `image → image` GPU: 有(gray_opening) — 灰度开运算(先腐蚀,再以相同结构元素膨胀)。可去除明亮的小突起、细线,同时大致保留整体的亮度分布。相当于 HALCON 的 ``gray_opening``(Perform a gray value opening on an image.)。 · 示例: `gallery2d_morphology`
- `gray_opening_rect` (halcon: `gray_opening_rect`) `image → image` GPU: 有(gray_opening_rect@twin) — 使用正方形窗口（边长 ``_k(a)``=3/5/7/9）的灰度开运算（gray opening，先腐蚀后膨胀）。在去除小的明亮突起、噪声的同时保留大致明暗。b 未使用。 · 示例: `find_ops_by_meaning`, `gallery2d_morphology`, `poc_weld_radiograph_porosity`
- `gray_opening_shape` (halcon: `gray_opening_shape`) `image → image` GPU: 有(许可列表) — 使用圆盘形(disk)结构元素的灰度开运算。与 ``gray_opening`` 的差异仅在于结构元素的形状,运算本身(先腐蚀后膨胀)相同。相当于 HALCON 的 ``gray_opening_shape``(Perform a gray value opening with a selected mask.)(HALCON 可从矩形/圆形/八边形等中选择,这里固定为圆形)。 · 示例: `gallery2d_morphology`
- `gray_tophat` (halcon: `gray_tophat`) `image → image` GPU: 有(gray_tophat@twin) — 白顶帽(原图 − 开运算)。仅提取比周围更亮的小结构(斑点、细线)。由于通过 ``_norm`` 归一化后返回,得到的是相对突出度而非绝对亮度。相当于 HALCON 的 ``gray_tophat``(Perform a gray value top hat transformation on an image.)。 · 示例: `gallery2d_morphology`, `poc_document_scan`, `poc_real_coin_metrology`, `poc_search_sweep_width`
- `local_thickness` `image → image` GPU: 有(许可列表) — 为每个前景像素填入“能覆盖该处的**最大圆的直径**”并返回(局部厚度)。 · 示例: `gallery2d_morphology`, `poc_bone_trabecular_thickness`
- `morph_grad` (halcon: `gray_range_rect`) `image → image` GPU: 有(gray_range_rect) — 形态学梯度（膨胀 − 腐蚀）。相当于 HALCON 的 ``gray_range_rect``（Determine the gray value range within a rectangle.）。 · 示例: `gallery2d_morphology`
- `persistence_map` `image → image` GPU: 无 — **不选取阈值**地测量“山峰的显著程度”(0 维持续性)。 · 示例: `gallery2d_morphology`
- `runlength_smear` `image → image` GPU: 有(许可列表) — **游程平滑(RLSA)**。填补行内字符之间的空隙，把字符合并成“行”的块。 · 示例: `gallery2d_morphology`
- `sk_area_opening` `image → image` GPU: 无 — 面积开运算(area opening)。普通的形态学开运算是根据结构元素的形状来削去小的亮部,而此运算仅根据面积(连通像素数)进行判定,消除面积小于指定值的亮连通分量 —— 可以不受形状限制地去除「小」的目标。 · 示例: `gallery2d_morphology`, `poc_bone_trabecular_thickness`, `poc_fresco_craquelure`
- `tophat` (halcon: `gray_tophat`) `image → image` GPU: 有(gray_tophat) — 白顶帽（原图像 − 开运算）。相当于 HALCON 的 ``gray_tophat``（Perform a gray value top hat transformation on an image.）。 · 示例: `degenerate_inputs`, `example_scratch_width`, `gallery2d_morphology`, `mcp_task_score`, `poc_search_sweep_width`
- `xsk2_diameter_opening` `image → image` GPU: 无 — 直径开运算（面积开运算的直径版本，用于去除微小的亮结构）。调用 ``skimage.morphology.diameter_opening``。 · 示例: `gallery2d_morphology`
- `xsk2_reconstruction` `image → image` GPU: 无 — 形态学重建（reconstruction by dilation，膨胀重建）。以 method="dilation" 调用 ``skimage.morphology.reconstruction``。 · 示例: `gallery2d_morphology`
- `xsk3_area_closing` `image → image` GPU: 无 — 面积闭运算(skimage ``morphology.area_closing``)。一种基于尺寸的形态学运算，仅填补面积小于阈值的暗区域(凹陷)——与普通闭运算不同，它以连通分量的面积而非结构元素的形状来选取对象。 · 示例: `gallery2d_morphology`
- `xsk3_diameter_closing` `image → image` GPU: 无 — 直径闭运算(skimage ``morphology.diameter_closing``)。与 xsk3_area_closing 使用面积不同，本运算以连通分量外接矩形的对角线长度(直径)来选取对象——细长结构适合用直径基准，圆形结构适合用面积基准，可视情况区分使用。 · 示例: `gallery2d_morphology`

#### 2d / morphology/markers (1)
- `xmh_regmin` `image → region` GPU: 无 — 区域极小值提取（``mahotas.regmin``）。对高斯平滑后的图像，将局部最暗的谷标记为区域。是分水岭分割（watershed）生成标记时常用的前处理。 · 示例: `gallery2d_segmentation`

#### 2d / nary (17)
- `abs_diff_image` (halcon: `abs_diff_image`) `image × image → image` GPU: 仅在链中(许可列表) — 2 幅图像之差的绝对值。相当于 HALCON 的 ``abs_diff_image``。``out = clip(|I1 - I2| * (0.5 + 1.5a), 0, 1)``。变化检测的基本形式，舍弃符号，换来的是变亮、变暗两种变化都能捕捉。``b`` 未使用。 · 示例: `gallery_nary_image_algebra`
- `add_image` (halcon: `add_image`) `image × image → image` GPU: 无 — 将 2 幅图像相加。相当于 HALCON 的 ``add_image``。``out = clip((I1 + I2) * (0.5 + a) + (b - 0.5), 0, 1)`` —— ``a`` 为增益(0.5〜1.5 倍)，``b`` 为偏移(-0.5〜+0.5)。饱和部分在 0/1 处截断。 · 示例: `degenerate_inputs`, `gallery_nary_image_algebra`, `genspark_external_review`
- `bit_and` (halcon: `bit_and`) `image × image → image` GPU: 有(许可列表) — 2 幅图像的按位 AND。相当于 HALCON 的 ``bit_and``。★先量化为 8bit 整数再运算，然后除以 255 还原，因此**浮点灰度会丢失**(0.501 与 0.503 变为同一值)。``a``, ``b`` 未使用。 · 示例: `gallery_nary_image_algebra`
- `bit_or` (halcon: `bit_or`) `image × image → image` GPU: 仅在链中(许可列表) — 2 幅图像的按位 OR。相当于 HALCON 的 ``bit_or``。★与 ``bit_and`` 一样先量化到 8bit 再运算，因此灰度会降级。``a``, ``b`` 未使用。 · 示例: `gallery_nary_image_algebra`
- `convol_image` (halcon: `convol_image`) `image × image → image` GPU: 无 — 以第 2 个输入作为滤波掩模进行卷积。相当于 HALCON 的 ``convol_image``。★与 HALCON 一样按**相关**(按掩模原样叠加)计算 —— scipy 的 ``convolve`` 会翻转掩模，因此若掩模不对称，图像会向相反方向偏移。掩模可以比图像小(不要求形状一致)，按绝对值之和 + 1e-8 相除归一化(避免总和为 0 的掩模使除法发散；因此输出相对小 1e-8)，边界用 ``reflect``。``a``, ``b`` 未使用。 · 示例: `gallery_nary_image_algebra`
- `difference` (halcon: `difference`) `region × region → region` GPU: 无 — 2 个区域的差集(属于第 1 个而不属于第 2 个的像素)。相当于 HALCON 的 ``difference``。**顺序有意义**(交换减数与被减数会得到不同结果)。``a``, ``b`` 未使用。 · 示例: `gallery_nary_image_algebra`, `gfx2d_scene`, `poc_granular_heap_repose`, `poc_powder_scoop_pour`, `poc_pxrd_phase_peel`
- `div_image` (halcon: `div_image`) `image × image → image` GPU: 仅在链中(许可列表) — 将 2 幅图像逐像素相除。相当于 HALCON 的 ``div_image``。``out = clip(I1 / max(I2, 1e-3) * (0.1 + 0.9a), 0, 1)`` —— 为避免除以零，分母设下限 ``1e-3``(在该处商最多变为 1000 倍并饱和)。``b`` 未使用。 · 示例: `gallery_nary_image_algebra`
- `intersection` (halcon: `intersection`) `region × region → region` GPU: 无 — 2 个区域的交集(同时属于两者的像素)。相当于 HALCON 的 ``intersection``。输入以 ``> 0.5`` 二值化。``a``, ``b`` 未使用。 · 示例: `gallery_nary_image_algebra`, `poc_battery_electrode_tortuosity`, `poc_connectome_across_decades`, `poc_connectome_across_worms`, `poc_driving_crossing`, `poc_driving_japan_town`, `poc_driving_pass`, `poc_driving_school`, `poc_driving_town`, `poc_real_sem_metal_layer`, `poc_worm_neurites_grow`
- `max_image` (halcon: `max_image`) `image × image → image` GPU: 无 — 2 幅图像的逐像素最大值。相当于 HALCON 的 ``max_image``。``a``, ``b`` 未使用。保留较亮者，因此用于多重曝光的合成或缺损的填补。 · 示例: `gallery_nary_image_algebra`
- `min_image` (halcon: `min_image`) `image × image → image` GPU: 仅在链中(许可列表) — 2 幅图像的逐像素最小值。相当于 HALCON 的 ``min_image``。``a``, ``b`` 未使用。保留较暗者，因此用于抑制反射高光。 · 示例: `gallery_nary_image_algebra`
- `mult_image` (halcon: `mult_image`) `image × image → image` GPU: 仅在链中(许可列表) — 将 2 幅图像逐像素相乘。相当于 HALCON 的 ``mult_image``。``out = clip(I1 * I2 * (0.5 + 1.5a) + (b - 0.5), 0, 1)``。由于乘积必然变暗，``a`` 的增益范围取得较宽。 · 示例: `gallery_nary_image_algebra`
- `overpaint_region` (halcon: `overpaint_region`) `image × region → image` GPU: 无 — 用常数值填充图像中区域的内部。相当于 HALCON 的 ``overpaint_region``。填充值为 ``a``(0〜1)。``b`` 未使用。 · 示例: `gallery_nary_image_algebra`
- `paint_gray` (halcon: `paint_gray`) `image × image → image` GPU: 无 — 把第 2 幅图像(source)的灰度涂入第 1 幅图像。相当于 HALCON 的 ``paint_gray``。★涂入范围是 source 的**所有非零像素**(与本层“定义域之外为 0”的约定一致)。直到 2026-09-03 为止只涂 ``> 0.5`` 的像素，因此**暗的 source 会消失**。``a``, ``b`` 未使用。 · 示例: `gallery_nary_image_algebra`
- `reduce_domain` (halcon: `reduce_domain`) `image × region → image` GPU: 无 — 用区域限定图像的定义域。相当于 HALCON 的 ``reduce_domain``。本层没有显式的定义域，因此通过**把区域外置为 0**(将图像乘以区域)来表示。``a``, ``b`` 未使用。 · 示例: `gallery_nary_image_algebra`
- `sub_image` (halcon: `sub_image`) `image × image → image` GPU: 仅在链中(许可列表) — 将 2 幅图像相减。相当于 HALCON 的 ``sub_image``。``out = clip((I1 - I2) * (0.5 + a) + b, 0, 1)`` —— 为负的差若不用 ``b`` 抬高就会被压成 0(默认 ``b=0.5`` 时中央值为灰色)。 · 示例: `gallery_nary_image_algebra`
- `symm_difference` (halcon: `symm_difference`) `region × region → region` GPU: 无 — 2 个区域的对称差(只属于其中一方的像素)。相当于 HALCON 的 ``symm_difference``。会消去重叠部分，因此用于查看 2 个掩模之间的偏差。``a``, ``b`` 未使用。 · 示例: `gallery_nary_image_algebra`
- `union2` (halcon: `union2`) `region × region → region` GPU: 无 — 2 个区域的并集(属于其中任一者的像素)。相当于 HALCON 的 ``union2``。输入以 ``> 0.5`` 二值化。``a``, ``b`` 未使用。 · 示例: `gallery_nary_image_algebra`

#### 2d / noise (2)
- `add_noise_distribution` (halcon: `add_noise_distribution`) `image → image` GPU: 无 — 向图像添加加性噪声。实现仅支持高斯（正态分布）噪声，与 ``add_noise_white`` 共享 ``_sh_noise`` 中的 ``gaussian`` 分支。随机数使用由 a 决定的固定种子（``int(a*997)+7``）生成，因此相同的 a 每次都会产生相同的噪声（确定性）。b 将噪声标准差调整为 0.02〜0.22。 · 示例: `gallery2d_smoothing_rank`
- `add_noise_white` (halcon: `add_noise_white`) `image → image` GPU: 无 — 添加高斯白噪声（用 ``np.random.default_rng`` 生成，标准差为 ``0.02+0.2*b``）。随机种子通过 ``int(a*997)+7`` 由 ``a`` 确定性地导出，因此相同的 ``a`` 总会重现相同的噪声模式（注意这并非真正随机，``a`` 被当作选择“噪声外观类型”的一个伪旋钮来使用）。相当于 HALCON 的 ``add_noise_white``（Add noise to an image.）。 · 示例: `gallery2d_smoothing_rank`

#### 2d / physics (6)
- `ph_coherence_enhancing_diffusion` `image → image` GPU: 有(许可列表) — Weickert 相干增强扩散(HALCON ``coherence_enhancing_diff``)。 · 示例: `gallery2d_physics_alife_3d`
- `ph_heat_flow` `image → image` GPU: 有(许可列表) — 线性热方程／各向同性扩散（HALCON ``isotropic_diffusion``）。 · 示例: `gallery2d_physics_alife_3d`
- `ph_mean_curvature_motion` `image → image` GPU: 有(许可列表) — 平均曲率流／曲线缩短流（HALCON ``mean_curvature_flow``）。 · 示例: `gallery2d_physics_alife_3d`
- `ph_perona_malik` `image → image` GPU: 有(许可列表) — Perona-Malik 各向异性扩散(HALCON ``anisotropic_diffusion``)。 · 示例: `gallery2d_physics_alife_3d`
- `ph_reaction_diffusion` `image → image` GPU: 有(许可列表) — Gray-Scott 反应扩散(无对应的 HALCON 算子,halcon="")。 · 示例: `gallery2d_physics_alife_3d`
- `ph_total_variation_flow` `image → image` GPU: 有(许可列表) — 全变分（Rudin-Osher-Fatemi）去噪流（无对应 HALCON 算子，``""``）。 · 示例: `find_ops_by_meaning`, `gallery2d_physics_alife_3d`

#### 2d / rank (23)
- `cv_median` (halcon: `median_image`) `image → image` GPU: 无 — 中值滤波器(OpenCV 实现)。用正方形邻域内的中位数进行替换的经典去噪方法(尤其对椒盐噪声效果好,边缘也相对能得到保留)。 · 示例: `find_ops_by_meaning`, `gallery2d_smoothing_rank`
- `dual_rank` (halcon: `dual_rank`) `image → image` GPU: 有(dual_rank) — 百分位数（顺序统计量）滤波器。将窗口内像素按升序排列，返回由 b 指定百分位（5〜95%，与 ``rank_image``/``rank_rect`` 共享 ``_sh_rank`` 中的 ``rank`` 分支）的值。a 将窗口大小分为 3/5/7/9。 · 示例: `gallery2d_smoothing_rank`
- `eliminate_min_max` (halcon: `eliminate_min_max`) `image → image` GPU: 有(eliminate_min_max) — 通过中值滤波器（median filter）实现平滑。实现与 ``median_image`` 等共享 ``_sh_rank`` 中的 median 分支，只是将窗口内像素替换为其中值。a 将窗口大小分为 3/5/7/9 四档（``_k(a)``）。b 未使用。 · 示例: `gallery2d_smoothing_rank`
- `eliminate_sp` (halcon: `eliminate_sp`) `image → image` GPU: 有(许可列表) — 通过西格玛滤波器（sigma filter，Lee 型）抑制噪声。仅使用窗口内与窗口均值之差低于阈值（0.05〜0.4，由 b 调节）的像素重新求平均，从而消除极端离群像素（如椒盐噪声）的影响。若窗口内没有符合条件的像素，则原样返回原值。a 将窗口大小分为 3/5/7/9。 · 示例: `gallery2d_smoothing_rank`
- `gray_dilation_rect` (halcon: `gray_dilation_rect`) `image → image` GPU: 有(gray_dilation_rect@twin) — 返回矩形窗口内最大值的灰度膨胀(``ndimage.maximum_filter``)。从明部一侧填补暗色细线、小孔并消除之,是与 ``gray_erosion_rect`` 成对的运算。相当于 HALCON 的 ``gray_dilation_rect``(Determine the maximum gray value within a rectangle.)。 · 示例: `gallery2d_smoothing_rank`
- `gray_erosion_rect` (halcon: `gray_erosion_rect`) `image → image` GPU: 有(gray_erosion_rect@twin) — 返回矩形窗口内最小值的灰度腐蚀(``ndimage.minimum_filter``)。从暗部一侧侵蚀明亮的细线、小突起,将其消除。相当于 HALCON 的 ``gray_erosion_rect``(Determine the minimum gray value within a rectangle.)。 · 示例: `gallery2d_smoothing_rank`
- `gray_range_rect` (halcon: `gray_range_rect`) `image → image` GPU: 有(gray_range_rect@twin) — 返回矩形窗口内最大值与最小值之差(局部范围)并归一化。可视化纹理局部起伏的剧烈程度(对比度量)。相当于 HALCON 的 ``gray_range_rect``(Determine the gray value range within a rectangle.)。 · 示例: `gallery2d_smoothing_rank`
- `max_filter` (halcon: `gray_dilation_rect`) `image → image` GPU: 有(gray_dilation_rect) — 矩形窗口内的最大值滤波器（相当于灰度膨胀）。相当于 HALCON 的 ``gray_dilation_rect``（Determine the maximum gray value within a rectangle.）。 · 示例: `gallery2d_smoothing_rank`
- `mean_sp` (halcon: `mean_sp`) `image → image` GPU: 有(许可列表) — 稳健平滑滤波器。返回窗口内 20 百分位与 80 百分位的平均值（截尾均值，trimmed mean），从而抑制极端明暗离群值（如椒盐噪声）的影响。a 将窗口大小分为 3/5/7/9（``_k(a)``）。b 未使用。 · 示例: `gallery2d_smoothing_rank`
- `median` (halcon: `median_image`) `image → image` GPU: 有(median_image) — 中值滤波器。相当于 HALCON 的 ``median_image``（Compute a median filter with various masks.）。 · 示例: `astro_stacking`, `blas_thread_budget`, `ct_reconstruction`, `gallery2d_smoothing_rank`, `genspark_external_review`, `lightfield_depth`, `photon_timeresolved`, `piv_flow_from_particles`, `poc_ai_built_inspection_scored`, `poc_am_thermal_to_ct`, `poc_astro_photometry`, `poc_compound_eye`, `poc_dtof_ranging`, `poc_geodetic_height_frames`, `poc_hyperspectral_foreign_matter`, `poc_lidar_terrain_change`, `poc_mixed_case_depalletizing`, `poc_nuclei_ploidy`, `poc_pv_thermal_survey`, `poc_river_surface_velocity`, `poc_sheet_deformation_ffd`, `poc_solar_el_inspection`, `poc_tacscalib_sphere_lut`, `poc_web_roll_periodicity`, `poc_weld_bead_profile`, `quickstart`, `specular_photometric`
- `median_image` (halcon: `median_image`) `image → image` GPU: 有(median_image@twin) — 中值滤波(``ndimage.median_filter``,方形窗)。这是一种以窗口内中位数替换像素的降噪方法,与均值滤波不同,它能在保留边缘的同时去除椒盐噪声。相当于 HALCON 的 ``median_image``(Compute a median filter with various masks.)(HALCON 可选择圆形、八边形等任意遮罩,这里固定为方形遮罩)。 · 示例: `degenerate_inputs`, `find_ops_by_meaning`, `gallery2d_smoothing_rank`, `genspark_external_review`, `poc_prnu_camera_fingerprint`
- `median_rect` (halcon: `median_rect`) `image → image` GPU: 有(median_rect) — 矩形中值滤波。与 ``median_image`` 使用相同的 ``scipy`` 实现,但可以独立指定高度和宽度(``size=(k_a, k_b)``)。相当于 HALCON 的 ``median_rect``(Compute a median filter with rectangular masks.)。 · 示例: `gallery2d_smoothing_rank`, `poc_tree_ring_dendro`, `poc_weld_radiograph_porosity`
- `median_separate` (halcon: `median_separate`) `image → image` GPU: 有(median_separate) — 实现与 ``median_image`` 相同(``kind: "median"``,方形窗的二维中值)。HALCON 的 ``median_separate``(Separated median filtering with rectangle masks.)是一种快速近似算子,将行方向和列方向分离的一维中值分两个通道执行,但此替代实现不作区分,直接返回普通的二维中值(结果多数情况下相近,但严格来说是不同的算法 —— 此近似的局限)。 · 示例: `gallery2d_smoothing_rank`
- `median_weighted` (halcon: `median_weighted`) `image → image` GPU: 有(median_weighted) — 中值滤波器（median filter）。实现与 eliminate_min_max/median_image 共享 ``_sh_rank`` 中的 median 分支，不按圆形、八边形等掩膜形状加权，只返回正方形窗口的简单中值。a 将窗口大小分为 3/5/7/9，b 未使用。 · 示例: `gallery2d_smoothing_rank`
- `min_filter` (halcon: `gray_erosion_rect`) `image → image` GPU: 有(gray_erosion_rect) — 矩形窗口内的最小值滤波器（相当于灰度腐蚀）。相当于 HALCON 的 ``gray_erosion_rect``（Determine the minimum gray value within a rectangle.）。 · 示例: `gallery2d_smoothing_rank`
- `percentile` (halcon: `rank_image`) `image → image` GPU: 有(rank_percentile) — 任意百分位数的秩序滤波器（rank filter）。相当于 HALCON 的 ``rank_image``（Compute a rank filter with arbitrary masks.）。 · 示例: `gallery2d_smoothing_rank`, `poc_colormap_readability`, `poc_real_grain_skiz`
- `rank_image` (halcon: `rank_image`) `image → image` GPU: 有(rank_image) — 通用秩滤波器(``ndimage.percentile_filter``),将窗口内像素值按升序排列,返回指定百分位位置的值。这是一种连续的推广:百分位为 0 相当于腐蚀,100 相当于膨胀,50 相当于中值。相当于 HALCON 的 ``rank_image``(Compute a rank filter with arbitrary masks.)(HALCON 可采用任意形状的遮罩,这里固定为方形遮罩)。 · 示例: `gallery2d_smoothing_rank`, `poc_dehazing`
- `rank_rect` (halcon: `rank_rect`) `image → image` GPU: 有(rank_rect) — 实现与 ``rank_image`` 完全相同(``kind: "rank"``,方形窗的百分位滤波器)。在 HALCON 中,``rank_image``(任意遮罩)与 ``rank_rect``(仅限矩形遮罩)是不同的算子,但此替代实现两者都指向同一个方形窗实现。是 HALCON 的 ``rank_rect``(Compute a rank filter with rectangular masks.)的替代实现。 · 示例: `gallery2d_smoothing_rank`
- `sk_median_disk` (halcon: `median_image`) `image → image` GPU: 无 — 使用圆盘(disk)形 footprint 的中值滤波。与普通的正方形核不同,得到的是接近圆形的各向同性平滑效果。 · 示例: `gallery2d_smoothing_rank`
- `trimmed_mean` (halcon: `trimmed_mean`) `image → image` GPU: 有(许可列表) — 通过返回 20 百分位与 80 百分位滤波结果的平均值来近似修剪均值。得到的值接近于排除了(最小、最大侧)离群值影响的平均值,但需注意,这与真正"对中间 60% 取平均"的修剪均值在计算方法上是不同的近似。是 HALCON 的 ``trimmed_mean``(Smooth an image with an arbitrary rank mask.)的替代实现。 · 示例: `gallery2d_smoothing_rank`
- `xkor_median` `image → image` GPU: 无 — 中值滤波器。调用 ``kornia.filters.median_blur``。 · 示例: `gallery2d_smoothing_rank`
- `xpil_mode_filter` `image → image` GPU: 无 — 众数滤镜。使用 ``PIL.ImageFilter.ModeFilter``，将每个像素替换为窗口内出现频率最高的像素值（取众数而非中值这一点与中值滤波不同）。 · 示例: `gallery2d_smoothing_rank`
- `xsk2_rank_geomean` `image → image` GPU: 无 — 一种秩滤波器，即几何平均滤波器。对转换为 8 位的图像使用圆形结构元素（``skimage.morphology.disk``）套用 ``skimage.filters.rank.geometric_mean``。 · 示例: `gallery2d_smoothing_rank`

#### 2d / region (79)
- `boundary` (halcon: `boundary`) `region → region` GPU: 仅在链中(许可列表) — 通过从区域中减去其收缩 1 个像素后的版本,提取外周边界线(轮廓内侧 1 像素宽的环)。将填充区域转换为轮廓线。相当于 HALCON 的 ``boundary``(Reduce a region to its boundary.)。 · 示例: `gallery2d_region`, `poc_complex_plane_fields`, `poc_driving_commonroad`, `voxel_labels_color`
- `closest_point_transform` (halcon: `closest_point_transform`) `region → image` GPU: 有(许可列表) — 返回区域**补集**的欧氏距离变换归一化结果——表示每个像素到最近的区域（前景）像素的距离，与 ``distance_transform`` 相比前景/背景是相反的距离场。输出类型为 ``image``。区域为空时一律为 1.0（没有最近的区域像素 = 到处都是最远）。相当于 HALCON 的 ``closest_point_transform``（Compute the closest-point transformation of a region.）。 · 示例: `gallery2d_region`
- `closing_circle` (halcon: `closing_circle`) `region → region` GPU: 仅在链中(许可列表) — 使用圆盘形结构元素的二值闭运算(先膨胀后侵蚀)。用于填补小孔洞或缩颈处,是与``opening_circle``成对的运算。相当于HALCON的``closing_circle``(Close a region with a circular structuring element.)。 · 示例: `gallery2d_region`, `poc_bev_sensor_fusion`, `poc_real_sem_metal_layer`
- `closing_golay` (halcon: `closing_golay`) `region → region` GPU: 仅在链中(许可列表) — 使用圆形结构元素（disk，半径 ``_rad(a)``=1〜4）进行二值闭运算（closing，先膨胀后腐蚀）。用于填补小孔洞和缩颈。b 未使用。 · 示例: `gallery2d_region`
- `closing_rectangle1` (halcon: `closing_rectangle1`) `region → region` GPU: 有(许可列表) — 使用正方形结构元素的二值闭运算。是 ``closing_circle`` 的矩形版本。相当于 HALCON 的 ``closing_rectangle1``(Close a region with a rectangular structuring element.)。 · 示例: `gallery2d_region`
- `convex_fill` (halcon: `shape_trans`) `region → region` GPU: 无 — 通过填补孔洞和凹陷来逼近凸包形状（以闭运算实现的近似）。意图对应 HALCON 的 ``shape_trans``（Transform the shape of a region.）中的凸包变换，但实现方式是迭代次数很多的闭运算，并非严格的凸包计算（近似）。 · 示例: `gallery2d_region`
- `cv_dist` (halcon: `distance_transform`) `region → image` GPU: 无 — 距离变换（distance transform，OpenCV 实现，L2／欧氏近似）。对前景区域中的每个像素，计算到最近背景像素的距离，并以图像形式返回 —— 用作提取区域「粗细」或中心线的前处理。 · 示例: `gallery2d_region`
- `dilation_circle` (halcon: `dilation_circle`) `region → region` GPU: 有(dilation_circle) — 使用圆盘形结构元素的二值膨胀(``ndimage.binary_dilation``)。将前景区域向外扩张,是与``erosion_circle``成对的运算。相当于HALCON的``dilation_circle``(Dilate a region with a circular structuring element.)。 · 示例: `gallery2d_region`, `poc_focus_stacking`
- `dilation_golay` (halcon: `dilation_golay`) `region → region` GPU: 仅在链中(许可列表) — 使用圆形结构元素（disk，半径 ``_rad(a)``=1〜4）进行二值膨胀（dilation）。b 未使用。 · 示例: `gallery2d_region`
- `dilation_rectangle1` (halcon: `dilation_rectangle1`) `region → region` GPU: 有(dilation_rectangle1) — 使用正方形结构元素的二值膨胀。是 ``dilation_circle`` 的矩形版本。相当于 HALCON 的 ``dilation_rectangle1``(Dilate a region with a rectangular structuring element.)。 · 示例: `gallery2d_region`
- `dilation_seq` (halcon: `dilation_seq`) `region → region` GPU: 有(dilation_seq) — 使用固定十字形结构元素（4 邻域），根据 a 重复 1〜4 次膨胀（dilation）的顺序膨胀。b 未使用。 · 示例: `gallery2d_region`
- `dist_transform` (halcon: `distance_transform`) `region → image` GPU: 有(许可列表) — 欧几里得距离变换。相当于 HALCON 的 ``distance_transform``（Compute the distance transformation of a region.）。 · 示例: `gallery2d_region`, `poc_bone_trabecular_thickness`
- `dist_transform_abs` (halcon: `distance_transform`) `region → image` GPU: 无 — 不归一化的绝对像素距离变换。相当于 HALCON 的 ``distance_transform``（Compute the distance transformation of a region.）。 · 示例: `gallery2d_region`
- `distance_transform` (halcon: `distance_transform`) `region → image` GPU: 有(许可列表) — 以最大值归一化后的欧几里得距离变换（``ndimage.distance_transform_edt``）图像。表示每个前景像素到最近背景像素的距离——（没有背景时一律为 1.0 = 到处都是最远）数值越大，说明该像素越处于区域的“深处”。请注意输出类型是 ``image`` 而不是 ``region``。相当于 HALCON 的 ``distance_transform``（Compute the distance transformation of a region.）。 · 示例: `gallery2d_region`, `poc_cell_counting`, `poc_crack_width`, `poc_fresco_craquelure`, `poc_particle_sizing`, `poc_vessel_network`
- `em_skeleton` `region → region` GPU: 无 — Eckhardt–Maderlechner 型的不变细化(与 HALCON `skeleton` 同族)。 · 示例: `gallery2d_region`
- `erosion_circle` (halcon: `erosion_circle`) `region → region` GPU: 有(erosion_circle) — 使用圆盘形结构元素的二值侵蚀(``ndimage.binary_erosion``)。从外周侵蚀前景区域使其缩小,是最基本的二值形态学运算。相当于HALCON的``erosion_circle``(Erode a region with a circular structuring element.)。 · 示例: `gallery2d_region`, `poc_livestock_body_volume`
- `erosion_golay` (halcon: `erosion_golay`) `region → region` GPU: 有(erosion_golay) — 使用圆形结构元素（disk，半径 ``_rad(a)``=1〜4）进行二值腐蚀（erosion）。b 未使用。 · 示例: `gallery2d_region`
- `erosion_rectangle1` (halcon: `erosion_rectangle1`) `region → region` GPU: 仅在链中(许可列表) — 使用正方形结构元素的二值侵蚀。与``erosion_circle``的差异仅在于结构元素的形状(正方形而非圆形)。相当于HALCON的``erosion_rectangle1``(Erode a region with a rectangular structuring element.)。 · 示例: `gallery2d_region`
- `erosion_seq` (halcon: `erosion_seq`) `region → region` GPU: 有(erosion_seq) — 使用固定十字形结构元素（4 邻域），根据 a 重复 1〜4 次收缩（erosion）的顺序腐蚀。b 未使用。迭代次数越多，腐蚀量越大（每次约相当于半径 1 像素）。 · 示例: `gallery2d_region`
- `fill_holes` (halcon: `fill_up`) `region → region` GPU: 有(fill_holes) — 填充区域内的孔洞。相当于 HALCON 的 ``fill_up``（Fill up holes in regions.）。 · 示例: `gallery2d_region`, `poc_cell_counting`, `poc_document_scan`, `poc_leaf_disease_area`, `poc_mesh_quality_repair`, `poc_mixed_case_depalletizing`, `poc_real_coin_metrology`, `poc_real_sem_metal_layer`, `poc_symmetry_restoration`
- `fill_up` (halcon: `fill_up`) `region → region` GPU: 有(fill_up) — 填补区域内部的孔洞(完全被背景包围的区域)(``ndimage.binary_fill_holes``)。只有未与外周相连的背景孔洞会被填补,与外周相连的凹陷不会被填补。相当于 HALCON 的 ``fill_up``(Fill up holes in regions.)。 · 示例: `gallery2d_region`, `poc_bev_sensor_fusion`
- `fill_up_shape` (halcon: `fill_up_shape`) `region → region` GPU: 仅在链中(lbl_fill_up_shape) — 填补区域内的小孔。仅填补面积在 ``area_threshold = 16+200a`` 像素以下的孔（skimage 的 ``remove_small_holes``）。b 未使用。 · 示例: `gallery2d_region`
- `get_region_contour` (halcon: `get_region_contour`) `region → region` GPU: 仅在链中(许可列表) — 提取区域的轮廓（边界线，1 像素宽）。通过从区域中减去其一次二值腐蚀版本来保留轮廓。**对于带孔的区域，除外周之外也会返回孔的轮廓**（实测 2026-09-16：在 8x8 的框上开 4x4 的孔，与孔相邻的 20 个前景像素中有 16 个成为轮廓）。「区域 − 腐蚀版」按定义会在外侧和孔侧各留下 1 个像素，因此若只需要外周，请先填孔。a、b 未使用。与 ``boundary`` seed op 实现相同。 · 示例: `gallery2d_region`, `poc_document_scan`
- `get_region_convex` (halcon: `get_region_convex`) `region → region` GPU: 无 — 将区域的凸包（convex hull）作为填充区域返回（``skimage.morphology.convex_hull_image``）。a、b 未使用。与 ``shape_trans``（转换为凸包形状的 seed op）实现相同。 · 示例: `gallery2d_region`
- `invert_region` (halcon: `complement`) `region → region` GPU: 有(invert_region) — 区域的补集（前景/背景反转）。相当于 HALCON 的 ``complement``（Return the complement of a region.）。 · 示例: `gallery2d_region`
- `junctions_skeleton` (halcon: `junctions_skeleton`) `region → region` GPU: 无 — 在骨架化后的区域中，只保留在 3x3 邻域内拥有 3 个以上骨架像素的像素（分支点/交叉点）。检测的是产生分支的节点，而不是骨架端点（``pruning`` 所删除的对象）。相当于 HALCON 的 ``junctions_skeleton``（Find junctions and end points in a skeleton.）——是一种近似：HALCON 会同时返回端点，而这里只检测分支点。 · 示例: `gallery2d_region`, `poc_fresco_craquelure`
- `morph_skeleton` (halcon: `morph_skeleton`) `region → region` GPU: 无 — 提取区域的骨架线（skeleton）。实现使用 skimage 的 ``skeletonize``（Zhang–Suen 型的迭代细化算法），a、b 未使用。 · 示例: `gallery2d_region`
- `opening_circle` (halcon: `opening_circle`) `region → region` GPU: 有(opening_circle) — 使用圆盘形结构元素的二值开运算(先侵蚀后膨胀)。在去除微小突起或细连接部的同时,保留大致的形状。相当于HALCON的``opening_circle``(Open a region with a circular structuring element.)。 · 示例: `gallery2d_region`, `poc_bone_trabecular_thickness`, `poc_change_detection_misreg`, `poc_document_scan`, `poc_real_sem_metal_layer`
- `opening_golay` (halcon: `opening_golay`) `region → region` GPU: 有(opening_golay) — 使用圆形结构元素（disk，半径 ``_rad(a)``=1〜4）进行二值开运算（opening，先腐蚀后膨胀）。用于去除小突起和孤立点。b 未使用。 · 示例: `gallery2d_region`
- `opening_rectangle1` (halcon: `opening_rectangle1`) `region → region` GPU: 有(许可列表) — 使用正方形结构元素的二值开运算。是 ``opening_circle`` 的矩形版本。相当于 HALCON 的 ``opening_rectangle1``(Open a region with a rectangular structuring element.)。 · 示例: `gallery2d_region`
- `pruning` (halcon: `pruning`) `region → region` GPU: 无 — 在骨架化（``skeletonize``，若不可用则直接使用输入）之后，反复（``1+4*a`` 次）削去邻居数为 1 以下的端点像素（毛刺=杂散分支），从骨架上去除短分支。相当于 HALCON 的 ``pruning``（Prune the branches of a region.）（HALCON 可指定分支长度，此处则用迭代次数做近似）。 · 示例: `gallery2d_region`, `poc_fresco_craquelure`
- `r2_endpoints_skeleton` `region → region` GPU: 无 — 提取骨架的端点(8 邻域中恰有 1 个骨架像素的点)。 · 示例: `gallery2d_region`, `poc_fresco_craquelure`
- `r2_inner_circle` (halcon: `inner_circle`) `region → region` GPU: 有(许可列表) — 把最大内接圆画成掩码(a 缩放所画半径;a=0.5 为精确)。 · 示例: `gallery2d_region`
- `r2_inner_rectangle1` (halcon: `inner_rectangle1`) `region → region` GPU: 无 — 最大的轴对齐内接矩形(a 收缩所画矩形;a=0 为精确)。 · 示例: `gallery2d_region`
- `r2_partition_rectangle` (halcon: `partition_rectangle`) `region → region` GPU: 仅在链中(许可列表) — 把区域外接矩形分成 NxN 网格,保留与区域重叠的单元。 · 示例: `gallery2d_region`
- `r2_runlength_features` (halcon: `runlength_features`) `region → feature` GPU: 无 — region → 特征量:水平前景游程的平均长度。 · 示例: `gallery2d_region`
- `r2_smallest_circle` (halcon: `smallest_circle`) `region → region` GPU: 无 — 最小包围圆作为掩码(Welzl);a 使半径膨胀(>=0)。 · 示例: `gallery2d_region`
- `r2_smallest_rectangle1` `region → region` GPU: 仅在链中(许可列表) — 轴对齐的外接矩形(smallest_rectangle1)。 · 示例: `gallery2d_region`
- `r2_smallest_rectangle2` (halcon: `smallest_rectangle2`) `region → region` GPU: 无 — 最小面积的**有向**外接矩形作为掩码(旋转卡壳)。 · 示例: `gallery2d_region`
- `r2_sort_region` (halcon: `sort_region`) `region → region` GPU: 仅在链中(lbl_sort_region) — 只保留第 k 大的连通成分;k = round(a*(n-1))。 · 示例: `gallery2d_region`
- `r2_split_skeleton_lines` (halcon: `split_skeleton_lines`) `region → region` GPU: 无 — 把区域细化为骨架,再在分叉点(>=3 邻域)处断开。 · 示例: `gallery2d_region`, `poc_vessel_network`
- `r2_union1` (halcon: `union1`) `region → region` GPU: 有(r2_union1) — 把所有连通成分并成一张掩码(标签的 OR)。 · 示例: `gallery2d_region`
- `r3_background_seg` (halcon: `background_seg`) `region → region` GPU: 有(lbl_background_seg) — 将区域的背景(前景的补集)分割为连通分量,丢弃过小的分量后返回(相当于 HALCON ``background_seg``)。 · 示例: `gallery2d_region`
- `r3_clip_region` (halcon: `clip_region`) `region → region` GPU: 有(许可列表) — 用以图像中心为基准的矩形窗口裁剪区域(相当于 HALCON ``clip_region``)。 · 示例: `gallery2d_region`
- `r3_eliminate_runs` (halcon: `eliminate_runs`) `region → region` GPU: 无 — 消除水平方向连通游程(连续前景像素序列)中长度小于指定值的部分(相当于 HALCON ``eliminate_runs``)。 · 示例: `gallery2d_region`
- `r3_label_to_region` (halcon: `label_to_region`) `region → region` GPU: 无 — 从标签图像中仅提取具有某一个灰度值(标签)的像素(相当于 HALCON ``label_to_region``)。 · 示例: `gallery2d_region`
- `r3_partition_dynamic` (halcon: `partition_dynamic`) `region → region` GPU: 无 — 在垂直方向宽度变窄的列(缩颈处)将区域水平分割(相当于 HALCON ``partition_dynamic``)。 · 示例: `gallery2d_region`
- `r3_polar_trans_region` (halcon: `polar_trans_region`) `region → region` GPU: 有(许可列表) — 将区域重映射到以其重心为中心的极坐标(相当于 HALCON ``polar_trans_region``)。 · 示例: `gallery2d_region`
- `r3_rank_region` (halcon: `rank_region`) `region → region` GPU: 仅在链中(许可列表) — 区域的形态学秩(rank)算子(HALCON 正宗的 ``rank_region``:既非纯腐蚀也非纯膨胀的一般化)。 · 示例: `gallery2d_region`
- `r3_region_features` (halcon: `region_features`) `region → feature` GPU: 无 — 返回区域的一个形状特征量(实现了 HALCON ``region_features`` 的一部分)。 · 示例: `gallery2d_region`
- `r3_runlength_distribution` (halcon: `runlength_distribution`) `region → feature` GPU: 无 — 返回水平方向游程长度分布的一个统计摘要量(相当于 HALCON ``runlength_distribution``)。 · 示例: `gallery2d_region`
- `r3_select_region_point` (halcon: `select_region_point`) `region → region` GPU: 仅在链中(lbl_select_region_point) — 只保留包含指定 1 个点的连通分量(相当于 HALCON ``select_region_point``)。 · 示例: `gallery2d_region`
- `reg_close` (halcon: `closing_circle`) `region → region` GPU: 无 — 区域（region）的二值闭运算（先膨胀后腐蚀）。相当于 HALCON 的 ``closing_circle``（Close a region with a circular structuring element.）。 · 示例: `gallery2d_region`, `poc_leaf_disease_area`
- `reg_dilate` (halcon: `dilation_circle`) `region → region` GPU: 有(reg_dilate) — 区域（region）的二值膨胀。相当于 HALCON 的 ``dilation_circle``（Dilate a region with a circular structuring element.）。 · 示例: `gallery2d_region`
- `reg_erode` (halcon: `erosion_circle`) `region → region` GPU: 有(reg_erode) — 区域（region）的二值腐蚀。相当于 HALCON 的 ``erosion_circle``（Erode a region with a circular structuring element.）。 · 示例: `degenerate_inputs`, `gallery2d_region`, `poc_colocalization_crosstalk`, `poc_leaf_disease_area`
- `reg_open` (halcon: `opening_circle`) `region → region` GPU: 无 — 区域（region）的二值开运算（先腐蚀后膨胀）。相当于 HALCON 的 ``opening_circle``（Open a region with a circular structuring element.）。 · 示例: `gallery2d_region`
- `region_boundary` (halcon: `boundary`) `region → region` GPU: 有(许可列表) — 提取 region 的轮廓（边界环）。相当于 HALCON 的 ``boundary``（Reduce a region to its boundary.）。 · 示例: `gallery2d_region`
- `remove_noise_region` (halcon: `remove_noise_region`) `region → region` GPU: 有(remove_noise_region) — 使用圆形结构元素（半径 ``_rad(a)``=1〜4）进行二值开运算（opening，先腐蚀后膨胀），去除孤立的小点状噪声。b 未使用。 · 示例: `find_ops_by_meaning`, `gallery2d_region`
- `remove_small` (halcon: `select_shape`) `region → region` GPU: 有(lbl_remove_small) — 根据面积去除较小的连通区域。相当于 HALCON 的 ``select_shape``（Choose regions with the aid of shape features.）。 · 示例: `gallery2d_region`, `quickstart`
- `select_largest` (halcon: `select_shape_std`) `region → region` GPU: 仅在链中(lbl_select_largest) — 只保留面积最大的连通区域。相当于 HALCON 的 ``select_shape_std``（Select regions of a given shape.）。 · 示例: `gallery2d_region`, `mcp_task_score`, `poc_document_scan`, `poc_leaf_disease_area`
- `select_shape` (halcon: `select_shape`) `region → region` GPU: 有(lbl_select_shape) — 去除面积低于阈值（``16+a*200`` 像素）的连通成分（前景为 8 连通）（去除类似噪声的小区域）。HALCON 的 ``select_shape``（Choose regions with the aid of shape features.）是可以用面积、圆形度、凸性等任意形状特征进行筛选的通用算子，但这里固定为按面积截断这一种（近似）。 · 示例: `gallery2d_region`, `poc_ai_built_inspection_scored`
- `select_shape_std` (halcon: `select_shape_std`) `region → region` GPU: 仅在链中(lbl_select_shape_std) — 只保留连通成分中面积最大的那一个（通过 ``_largest_label`` 选取，前景为 8 连通）。HALCON 的 ``select_shape_std``（Select regions of a given shape.）是可以选择包括 ``max_area`` 在内的多种标准基准的算子，但这里固定为“面积最大”这一种（近似）。 · 示例: `gallery2d_region`
- `shape_trans` (halcon: `shape_trans`) `region → region` GPU: 无 — 返回区域的凸包(``skimage.morphology.convex_hull_image``)。HALCON 的 ``shape_trans``(Transform the shape of a region.)本来是可以通过 ``Type`` 参数选择 convex/rectangle1/ellipse 等多种变形模式的算子,但这个代替实现固定为凸包这一种(近似的局限)。 · 示例: `gallery2d_region`
- `sk_clear_border` `region → region` GPU: 仅在链中(lbl_clear_border) — 去除接触图像边缘的连通分量。将前景区域中所有与图像外周相接触的连通分量全部归为背景 —— 这是排除在视野边缘被截断(未拍到完整图像)的物体使其不参与分析的常规前处理。 · 示例: `gallery2d_region`
- `sk_convex` (halcon: `shape_trans`) `region → region` GPU: 无 — 基于凸包(convex hull)的区域变形。求出包围前景区域的最小凸多边形,并返回其内部填充后的区域 —— 会填平所有的束缩与凹陷。 · 示例: `gallery2d_region`
- `sk_find_boundaries` (halcon: `boundary`) `region → region` GPU: 无 — 区域边界提取。在标签图像(此处为布尔值区域)中,只将不同标签(前景/背景)相接触的像素设为 True,返回这样一个边界掩膜。 · 示例: `gallery2d_region`
- `sk_medial` (halcon: `skeleton`) `region → region` GPU: 无 — 中心轴变换(medial axis transform)。这是一种与 sk_skeleton 不同的算法,通过提取距离变换的脊线来求得骨架,得到的骨架往往保留了距轮廓的距离信息。 · 示例: `gallery2d_region`, `poc_crack_width`, `poc_vessel_network`
- `sk_remove_holes` (halcon: `fill_up`) `region → region` GPU: 仅在链中(lbl_sk_remove_holes) — 小孔洞填充。仅将前景区域内部背景孔(洞)中面积小于阈值的部分填平 —— 较大的孔洞(有意的开口)则保留。 · 示例: `gallery2d_region`
- `sk_skeleton` (halcon: `skeleton`) `region → region` GPU: 无 — 区域骨架化(skeletonization)。在保持前景区域拓扑结构(连通关系、孔洞数量)不变的前提下,将其细化为宽度为 1 像素的线条。 · 示例: `gallery2d_region`, `poc_solar_el_inspection`
- `sk_thin` (halcon: `thinning`) `region → region` GPU: 无 — 形态学细化(thinning)。与 sk_skeleton 一样都是将其变为 1 像素宽,但算法不同,基于击中或击不中变换(hit-or-miss transform),生成骨架分支(毛刺)的倾向较少。 · 示例: `gallery2d_region`
- `skeleton` (halcon: `skeleton`) `region → region` GPU: 无 — 在保持拓扑结构的前提下,将区域细化为 1 像素宽的骨架线(``skimage.morphology.skeletonize``)。分支点和端点的位置得以保留,因此常用于分析带分支的形状(例如数手指的根数)。相当于 HALCON 的 ``skeleton``(Compute the skeleton of a region.)。 · 示例: `gallery2d_region`, `poc_crack_width`, `poc_em_branch_territory`, `poc_fresco_craquelure`, `poc_real_sem_metal_layer`, `poc_swc_tree_truth`, `poc_vessel_network`
- `smallest_rectangle1` (halcon: `smallest_rectangle1`) `region → region` GPU: 仅在链中(lbl_smallest_rectangle1) — 返回以包围区域的坐标轴对齐外接矩形（axis-aligned bounding box）填充的区域。a、b 未使用。若区域为空则返回全零。 · 示例: `gallery2d_region`
- `thinning` (halcon: `thinning`) `region → region` GPU: 无 — 使用 ``skimage.morphology.thin``(Zhang-Suen 系细化算法)将区域细化为 1 像素宽。目的与 ``skeleton`` 相似,但内部算法不同,因此在分支点附近等处结果可能略有差异。作为 HALCON 的 ``thinning``(Remove the result of a hit-or-miss operation from a region.)的代替。 · 示例: `gallery2d_region`, `poc_crack_width`, `poc_fabric_defect`, `poc_metal_grain_size`, `poc_real_grain_skiz`, `poc_vessel_network`
- `thinning_golay` (halcon: `thinning_golay`) `region → region` GPU: 无 — 对区域进行细化（thinning）。实现使用 skimage 的 ``thin``（Guo–Hall 型的迭代细化），反复处理直到完全变为 1 像素宽，a、b 未使用。 · 示例: `gallery2d_region`
- `thinning_seq` (halcon: `thinning_seq`) `region → region` GPU: 无 — 对区域进行细化（thinning）。实现与 thinning_golay 完全相同（skimage 的 ``thin``，反复迭代至收敛的 Guo–Hall 型细化），a、b 未使用。 · 示例: `gallery2d_region`
- `xcv2_hitmiss` `region → region` GPU: 无 — 使用击中击不中变换（hit-or-miss transform）检测「中心为背景、上下左右为前景」的十字形图案（``cv2.MORPH_HITMISS``）。 · 示例: `gallery2d_region`
- `xsk2_isotropic_close` `region → region` GPU: 无 — 等方闭运算（isotropic closing）。对二值区域套用 ``skimage.morphology.isotropic_closing``（专用于 `region` -> `region`，与普通形态学闭运算不同，它基于距离变换以等方方式工作）。 · 示例: `gallery2d_region`
- `xsk3_rank_majority` `region → region` GPU: 无 — 局部多数表决滤波(skimage ``filters.rank.majority``)。与 xmh_majority 相同的多数表决平滑的 skimage 版本，若圆盘邻域内过半数像素为 1，则置为 1。 · 示例: `gallery2d_region`
- `xsp_chamfer_dist` `region → image` GPU: 无 — 到最近背景像素的城市街区（倒角）距离，归一化到 [0,1]。 · 示例: `gallery2d_region`

#### 2d / region-morphology (1)
- `xmh_majority` `region → region` GPU: 无 — 多数表决滤波器（``mahotas.majority_filter``）。对二值区域进行平滑处理，仅在正方形邻域内1占多数时才将该像素保留为1。用于去除孤立噪声和平滑区域边界的锯齿。 · 示例: `find_ops_by_meaning`, `gallery2d_region`

#### 2d / region-transform (1)
- `xmh_bwperim` `region → region` GPU: 无 — 区域轮廓提取（``mahotas.bwperim``）。从二值区域中只保留与背景相邻的边界像素，形成宽度为1像素的轮廓。 · 示例: `gallery2d_region`

#### 2d / restoration (12)
- `iv_backproject_superres` `image → image` GPU: 有(许可列表) — 单幅图像的迭代反投影超分辨率（Irani-Peleg 方法）。先放大到更高分辨率网格，通过模糊与降采样模拟低分辨率观测，将残差反投影回高分辨率网格，再将得到的一致估计降采样回 HxW。净效果是高频细节被增强（通过一致性实现锐化）。``a`` 设定迭代次数 n = 1 + round(a*4)（1..5）；``b`` 设定反投影步长增益 g = 0.5 + b（0.5..1.5）。 · 示例: `gallery2d_smoothing_rank`
- `iv_gradient_inpaint` `image → image` GPU: 无 — 对中央被遮罩窗口进行调和（拉普拉斯）图像修复（inpainting）。以 ``a`` 决定边长比例的居中窗口，其内部被舍弃，并通过求解 nabla^2 u = 0（Dirichlet 边界条件等于周围已知像素）来重新填充（雅可比松弛法 = 反复用每个被遮罩像素的 4 邻域均值替换该像素）。恢复出的内部是该空洞的最平滑（最小梯度）填充。``a`` 设定窗口大小；``b`` 被忽略。 · 示例: `gallery2d_smoothing_rank`
- `iv_motion_deblur` `image → image` GPU: 有(许可列表) — 针对假设的线性运动模糊进行维纳反卷积。``a`` 设定模糊长度 L = 3 + round(a*10)（3..13 px）；``b`` 设定模糊角度 theta = b*180 度（b=0 -> 水平方向）。该 op 构建该运动 PSF 并对其求逆，使沿运动方向被拖散的条纹变窄。 · 示例: `gallery2d_smoothing_rank`, `poc_real_deblur_honesty`
- `iv_richardson_lucy` `image → image` GPU: 有(许可列表) — 假设点扩散函数（PSF）为小型高斯核（sigma = ``RL_SIGMA``）的 Richardson-Lucy 反卷积。``a`` 设定迭代次数 n = 1 + round(a*14)（1..15）；``b`` 被忽略。RL 以乘法方式驱动估计值 ``u``，使 ``u (*) psf`` 逼近模糊后的观测值，从而锐化真实边缘。 · 示例: `gallery2d_smoothing_rank`, `poc_real_deblur_honesty`
- `iv_unsharp_deblur` `image → image` GPU: 有(许可列表) — 以迭代反锐化蒙版（unsharp masking）作为近似去模糊方法。每一遍处理都会把按比例缩放的高通分量（图像减去其高斯模糊）加回图像。``a`` 设定迭代次数 n = 1 + round(a*5)（1..6）；``b`` 设定每遍的强度 amt = 0.4 + b（0.4..1.4）。迭代次数越多／强度越大，锐化效果越强。 · 示例: `gallery2d_smoothing_rank`, `poc_real_deblur_honesty`
- `iv_wiener_deconv_spatial` `image → image` GPU: 有(许可列表) — 针对假设的小型高斯 PSF 进行的自包含空间域维纳（Wiener）反卷积。``a`` 设定要反演的假设模糊 sigma，范围在 [0.4, ``WIENER_SIGMA_MAX``]（a 越大锐化越强）；``b`` 设定噪声信号比 nsr = 1e-3 + b*0.15（b 越大恢复越温和、正则化程度越高）。 · 示例: `gallery2d_smoothing_rank`
- `xcv3_inpaint_ns` `image → image` GPU: 无 — 基于 Navier-Stokes 方法的图像修复(OpenCV ``cv2.inpaint``，``INPAINT_NS``)。一种通过流体力学方式从周边像素传播信息来填补缺损区域的修复算法。 · 示例: `gallery2d_smoothing_rank`
- `xcv_inpaint` `image → image` GPU: 无 — 通过推测缺失区域并进行填补的修复（inpainting）。 · 示例: `gallery2d_smoothing_rank`
- `xsk2_wiener` `image → image` GPU: 无 — 维纳反卷积（使用已知点扩散函数的去模糊）。调用``skimage.restoration.wiener``。 · 示例: `gallery2d_smoothing_rank`
- `xsk_inpaint` `image → image` GPU: 无 — 通过估计并填补缺失区域进行修复（inpainting）。 · 示例: `gallery2d_smoothing_rank`
- `xsk_richardson_lucy` `image → image` GPU: 无 — Richardson-Lucy 反卷积。假设模糊为 3x3 均值核（box PSF），进行迭代锐化（直接调用 ``skimage.restoration.richardson_lucy``）。 · 示例: `gallery2d_smoothing_rank`
- `xsk_unwrap_phase` `image → image` GPU: 无 — 相位解卷绕（phase unwrapping）。将输入 [0,1] 视为相位 [-pi, pi]，用 ``skimage.restoration.unwrap_phase`` 去除 2*pi 的折返（wrap），然后通过 ``signed01`` 在保持符号的情况下转回 [0,1]（0 -> 0.5）。 · 示例: `gallery2d_smoothing_rank`

#### 2d / segment (7)
- `sg_felzenszwalb` `image → region` GPU: 无 — 返回 Felzenszwalb 基于图的区域分割边界（``skimage.segmentation.felzenszwalb``，HALCON 无对应算子）。 · 示例: `gallery2d_segmentation`
- `sg_gmm_segment` `image → region` GPU: 有(许可列表) — 对亮度值拟合 2 类高斯混合模型（EM 算法），并将较亮的簇作为区域返回（不依赖 ``skimage`` 的自实现 EM，HALCON 无对应算子）。 · 示例: `gallery2d_segmentation`, `poc_nuclei_ploidy`
- `sg_kmeans_intensity` `image → region` GPU: 有(许可列表) — 对亮度值进行 k-means 聚类，并将最亮的簇作为区域返回（自实现的 Lloyd 算法，HALCON 无对应算子）。 · 示例: `gallery2d_segmentation`
- `sg_normalized_cut_2` `image → region` GPU: 有(许可列表) — 通过对亮度图进行归一化割（Normalized Cut，谱聚类二分割，Shi & Malik）将图像划分为明暗两个区域（HALCON 无对应算子）。 · 示例: `gallery2d_segmentation`
- `sg_region_growing_seeded` `image → region` GPU: 有(许可列表) — 以图像中心为种子，连接亮度相近像素的种子区域生长（区域扩张）（HALCON ``regiongrowing`` 已由另一个 op 覆盖，为避免重复申报，此处使用 ``halcon=""``）。 · 示例: `gallery2d_segmentation`
- `sg_slic_superpixels` `image → region` GPU: 无 — 返回基于 SLIC 方法的超像素过分割边界网格（``skimage.segmentation.slic``，HALCON 无对应算子）。 · 示例: `gallery2d_segmentation`
- `sg_watershed_gradient` `image → region` GPU: 无 — 返回从梯度图像的 h-minima 标记出发进行分水岭分割的边界（``skimage``，HALCON 无对应算子）。 · 示例: `gallery2d_segmentation`, `poc_segmentation_gauntlet`

#### 2d / segmentation (56)
- `adaptive_gauss_thresh` (halcon: `local_threshold`) `image → region` GPU: 有(adaptive_gauss_thresh) — 以高斯平滑后的局部均值为基准进行自适应阈值处理。相当于 HALCON 的 ``local_threshold``（Segment an image using local thresholding.）。 · 示例: `gallery2d_segmentation`, `poc_matrix_code_reading`
- `auto_threshold` (halcon: `auto_threshold`) `image → region` GPU: 仅在链中(许可列表) — 实现与``binary_threshold``完全相同(以Otsu判别分析法进行自动阈值化)。HALCON的``auto_threshold``(Segment an image using thresholds determined from its histogram.)本来是从直方图的多个谷值中确定**多个阈值**(多类别分割)的运算符,但此替代实现简化为以单一Otsu阈值进行二值化(近似的局限)。 · 示例: `gallery2d_segmentation`, `poc_battery_electrode_breathing`, `poc_bump_coplanarity`, `threshold_family_agreement`
- `bin_threshold` (halcon: `bin_threshold`) `image → region` GPU: 无 — 使用大津判别分析法（Otsu's method）的自动阈值二值化。与 ``binary_threshold``/``auto_threshold`` 共享 ``_sh_threshold`` 中的 ``otsu`` 分支，a、b 未使用。比阈值更亮的像素作为前景(1)。经过与核心 ``otsu`` op 相同的函数(将数据的实际范围分成 256 个 bin，在 argmax bin 的上端切分)，因此答案与 ``otsu`` 一致，也不会裁剪 [0,1] 之外的值(2026-11-09 之前先裁剪到 [0,1] 再执行 scikit-image 的大津法，对 0..255 的 float 得到 0 % 前景，对常数图像得到与 ``otsu`` 相反的答案)。 · 示例: `gallery2d_segmentation`, `poc_metal_grain_size`
- `binary_threshold` (halcon: `binary_threshold`) `image → region` GPU: 有(许可列表) — 使用大津判别分析法(Otsu's method)进行自动阈值二值化(与核心的 ``otsu`` 为同一函数：将数据的实际范围分成 256 个 bin，在 argmax bin 的上端切分)。从图像直方图自动确定能使类间方差最大化的阈值。相当于HALCON的``binary_threshold``(Segment an image using binary thresholding.)(HALCON可在Otsu之外选择多种算法,此处固定使用Otsu)。 · 示例: `gallery2d_segmentation`, `threshold_family_agreement`
- `canny` (halcon: `edges_image`) `image → region` GPU: 有(canny) — 简化版 Canny 风格边缘检测（返回 region）。对应 HALCON 的 ``edges_image``（Extract edges using Deriche, Lanser, Shen, or Canny filters.），但这是一个不进行非极大值抑制和滞后阈值处理的简化版本(近似)。 · 示例: `gallery2d_segmentation`, `poc_real_coin_metrology`, `poc_water_inspection_images`
- `cv_adaptive_gauss` (halcon: `local_threshold`) `image → region` GPU: 无 — 基于局部高斯加权平均的阈值二值化（adaptive threshold，Gaussian 版本，OpenCV 实现）。与 cv_adaptive_mean 框架相同，但局部平均不是简单平均而是高斯加权平均，因此窗口边界附近不易出现剧烈变化。 · 示例: `gallery2d_segmentation`
- `cv_adaptive_mean` (halcon: `dyn_threshold`) `image → region` GPU: 无 — 基于局部均值的阈值二值化（adaptive threshold，mean 版本，OpenCV 实现）。以各像素邻域的简单平均值减去一个常数作为阈值 —— 在光照不均的图像上比全局阈值更稳定。 · 示例: `gallery2d_segmentation`
- `cv_canny` (halcon: `edges_image`) `image → region` GPU: 无 — Canny 边缘检测（区域版本，OpenCV 实现）。算法与 sk_canny 相同，但 OpenCV 版本的 API 是直接指定两个阈值，而不是高斯平滑的 σ。 · 示例: `gallery2d_segmentation`
- `cv_otsu` (halcon: `binary_threshold`) `image → region` GPU: 无 — 基于大津判别分析法的全局阈值二值化（OpenCV 实现）。算法与 sk_otsu 相同，但内部会先量化为 8 位再计算，因此结果可能略有偏差。 · 示例: `gallery2d_segmentation`, `poc_vegetation_cover`, `threshold_family_agreement`
- `dual_threshold` (halcon: `dual_threshold`) `image → region` GPU: 无 — 面向带符号图像的阈值处理。将中间值 0.5 视为“零”，把满足 ``|x - 0.5| > 0.1+0.35*a``（离 0.5 足够远）的像素判定为前景——对正负两侧都对称地作出反应。相当于 HALCON 的 ``dual_threshold``（Threshold operator for signed images.）（HALCON 可以为正负分别设置阈值，这里简化为以 0.5 为中心的对称带）。 · 示例: `gallery2d_segmentation`
- `dyn_threshold` (halcon: `dyn_threshold`) `image → region` GPU: 有(dyn_threshold) — 局部阈值处理。以局部平均值(窗口边长为``_k(a)``的``uniform_filter``)加上偏移量``(b-0.5)*0.4``作为阈值——即使是照明不均的图像,也能依据局部对比度提取前景。相当于HALCON的``dyn_threshold``(Segment an image using a local threshold.)。 · 示例: `gallery2d_segmentation`, `poc_metal_grain_size`
- `edges_image` (halcon: `edges_image`) `image → region` GPU: 无 — 以Canny边缘检测(``skimage.feature.canny``,sigma为``0.5+2*a``)进行区域提取。是将高斯平滑→梯度→非极大值抑制→滞后阈值这多个阶段整合在一起的广泛使用的边缘检测方法。相当于HALCON的``edges_image``(Detect edges using Deriche, Lanser, Shen, or Canny filters.)(HALCON可选择Deriche/Lanser/Shen/Canny,此处固定使用Canny)。 · 示例: `find_ops_by_meaning`, `gallery2d_segmentation`
- `fast_threshold` (halcon: `fast_threshold`) `image → region` GPU: 仅在链中(许可列表) — 使用固定阈值的二值化。``x`` 落在 ``(a, a+0.5+0.5b)`` 区间内的像素作为前景(1)（与 ``threshold`` seed op 共享 ``_sh_threshold`` 中的 ``fixed`` 分支）。a 调节下限，b 调节带宽（上限）。 · 示例: `gallery2d_segmentation`
- `h_threshold` (halcon: `threshold`) `image → region` GPU: 无 — 带状阈值处理(满足``a < x < a+0.5+0.5*b``的像素视为前景)。HALCON的``threshold``(Segment an image using global threshold.)是直接指定Min/Max两个数值的运算符,但此替代实现是从``a``推导下限、从``b``推导带宽的简化版,相当于1个参数。由于``threshold``在Python端被当作类似保留字处理,注册名称改为``h_threshold``(spec的``halcon``字段仍保持``threshold``)。 · 示例: `gallery2d_segmentation`
- `hysteresis_threshold` (halcon: `hysteresis_threshold`) `image → region` GPU: 无 — 滞后阈值处理(``skimage.filters.apply_hysteresis_threshold``)。在超过低阈值(``0.2+0.3*a``)的像素中,只保留与超过高阈值(``0.5+0.3*b``)的像素相连的部分作为前景——是也常作为Canny边缘检测后处理使用的、不易断裂的边缘提取方法。相当于HALCON的``hysteresis_threshold``(Perform a hysteresis threshold operation on an image.)。 · 示例: `gallery2d_segmentation`, `poc_fresco_craquelure`, `poc_solar_el_inspection`
- `it_region_to_bin` (halcon: `region_to_bin`) `image → image` GPU: 有(许可列表) — region_to_bin:以 ``a`` 为阈值对图像分割得到区域,再将该区域渲染为双灰度值的二值图像 —— 前景像素取高灰度值,背景像素取低灰度值。``b`` 设置这两个灰度值:lo = 0.5 - 0.5*b,hi = 0.5 + 0.5*b。 · 示例: `gallery2d_segmentation`
- `local_max` (halcon: `local_max`) `image → region` GPU: 有(local_max) — 局部极大点检测。仅将``x``与窗口内最大值(``_k(a)``)一致、且满足``x > 0.3+0.4*b``的像素视为前景——需注意在平坦的高原状区域中,可能有多个相邻像素同时被保留为“极大值”(无法保证只留下真正的孤立峰值点)。相当于HALCON的``local_max``(Detect all local maxima in an image.)。 · 示例: `gallery2d_segmentation`
- `local_min` (halcon: `local_min`) `image → region` GPU: 无 — 局部极小点（区域极小）检测。把满足 ``x`` 等于窗口内最小值（``_k(a)``）且同时满足 ``x < 0.7-0.4*b`` 的像素判定为前景——是 ``local_max`` 的暗部版本。相当于 HALCON 的 ``local_min``（Detect all local minima in an image.）。 · 示例: `gallery2d_segmentation`
- `local_threshold` (halcon: `local_threshold`) `image → region` GPU: 有(local_threshold) — 局部高斯平滑加偏移量的阈值处理(阈值为``gaussian_filter(x, 1+3*a)``加上偏移量``(b-0.5)*0.3``)。构想与``dyn_threshold``类似,不同之处在于局部平均值是以高斯而非矩形窗口求得。相当于HALCON的``local_threshold``(Segment an image using local thresholding.)。 · 示例: `gallery2d_segmentation`, `poc_segmentation_gauntlet`
- `nonmax_suppression_amp` (halcon: `nonmax_suppression_amp`) `image → region` GPU: 有(nonmax_suppression_amp) — 提取局部极大值（local maxima）的非极大值抑制。只保留与窗口内最大值一致、且超过阈值 ``0.3+0.4b`` 的像素作为前景。a 将窗口大小分为 3/5/7/9。 · 示例: `gallery2d_segmentation`
- `otsu` (halcon: `binary_threshold`) `image → region` GPU: 有(otsu) — 使用大津法（Otsu's method）进行的自动阈值处理。相当于 HALCON 的 ``binary_threshold``（Segment an image using binary thresholding.）。 · 示例: `ct_inspection`, `degenerate_inputs`, `example_inner_diameter_mm`, `find_ops_by_meaning`, `gallery2d_segmentation`, `genspark_external_review`, `line_handshake`, `mcp_task_score`, `poc_bone_trabecular_thickness`, `poc_colocalization_crosstalk`, `poc_dimensional_inspection`, `poc_document_scan`, `poc_fresco_craquelure`, `poc_matrix_code_reading`, `poc_metal_grain_size`, `poc_real_coin_metrology`, `poc_real_file_formats`, `poc_real_sem_metal_layer`, `poc_segmentation_gauntlet`, `poc_solar_el_inspection`, `poc_vegetation_cover`, `poc_water_inspection_images`, `quickstart`, `segment_and_classify`, `threshold_family_agreement`, `typed_results_json`
- `pouring` (halcon: `pouring`) `image → region` GPU: 无 — 通过分水岭法（watershed）进行区域分割的边界提取。将梯度图像（Sobel 振幅）视为地形，以暗区（``x < 0.2+0.3a``）作为种子（标记）计算分水岭，并用 ``skimage.segmentation.find_boundaries`` 将边界作为前景返回。b 未使用。 · 示例: `gallery2d_segmentation`
- `ptile_threshold` `image → feature` GPU: 无 — 将按面积比例选择的 P-tile 阈值作为特征返回。 · 示例: `poc_threshold_transfer_after_normalization`
- `regiongrowing` (halcon: `regiongrowing`) `image → region` GPU: 无 — 区域生长的简易近似。首先以高阈值(``x > 0.5+0.3*a``)建立种子区域,再对其进行``1+4*b``次二值膨胀以扩大——这并非真正的区域生长(依序判定与邻近像素的相似度而扩展),而是以阈值+膨胀这种轻量方式代替(近似的局限)。是HALCON``regiongrowing``(Segment an image using region growing.)的代用。 · 示例: `gallery2d_segmentation`
- `regiongrowing_mean` (halcon: `regiongrowing_mean`) `image → region` GPU: 无 — 实现与 ``regiongrowing`` 完全相同（基于阈值的种子生成 + 膨胀）。HALCON 的 ``regiongrowing_mean``（Perform a region growing using mean gray values.）本应是根据各区域平均亮度的接近程度来生长的运算子，但此替代实现不进行基于平均亮度的判定，返回与 ``regiongrowing`` 相同的处理（近似的局限）。 · 示例: `gallery2d_segmentation`
- `segment_image_mser` (halcon: `segment_image_mser`) `image → region` GPU: 无 — MSER（Maximally Stable Extremal Regions，最大稳定极值区域）检测（``cv2.MSER_create``）。检测即使连续改变阈值形状也保持稳定的区域，并返回其边界（用于检测文字、标志等对光照变化具有鲁棒性的区域）。相当于 HALCON 的 ``segment_image_mser``（Segment image using Maximally Stable Extremal Regions (MSER).）。 · 示例: `gallery2d_segmentation`
- `sigma_threshold` `image → region` GPU: 无 — 对图像进行稳健标准化，并以 ``k = 2 + 3*a`` 个标准差二值化。 · 示例: `poc_threshold_transfer_after_normalization`
- `sk_canny` (halcon: `edges_image`) `image → region` GPU: 无 — Canny 边缘检测(区域版)。通过高斯平滑 -> 梯度计算 -> 非极大值抑制 -> 滞后阈值这一经典多阶段流程求出边缘像素,并以布尔值区域的形式返回。 · 示例: `find_ops_by_meaning`, `gallery2d_segmentation`, `genspark_external_review`
- `sk_chan_vese` `image → region` GPU: 无 — Chan-Vese 分割。这是一种反复移动水平集(等值集合)以使区域内亮度方差最小化的主动轮廓模型,即使目标边缘不清晰也能检测出区域。 · 示例: `gallery2d_segmentation`, `poc_active_contours`, `poc_segmentation_gauntlet`
- `sk_felzenszwalb` `image → region` GPU: 无 — Felzenszwalb 基于图的区域分割。以像素为节点进行最小生成树聚类,是一种即使没有明确边界也能对图像进行过分割(过度分割)的高速方法。此处返回的是分割结果的边界线区域。 · 示例: `gallery2d_segmentation`, `poc_segmentation_gauntlet`
- `sk_hysteresis` (halcon: `hysteresis_threshold`) `image → region` GPU: 无 — 滞后阈值处理。使用两级阈值,先确定超过高阈值的像素,再追加采用超过低阈值且与已确定像素相连通的像素 —— 这是将 Canny 边缘连接步骤的相同思路应用于通用响应图像的方法。 · 示例: `gallery2d_segmentation`
- `sk_li` (halcon: `binary_threshold`) `image → region` GPU: 有(许可列表) — 基于 Li 的最小交叉熵法(Minimum Cross Entropy)的全局阈值二值化。通过反复最小化前景/背景分布之间的交叉熵来确定阈值,是与大津法不同系统的自动阈值法。 · 示例: `gallery2d_segmentation`, `threshold_family_agreement`
- `sk_local_maxima` (halcon: `local_max`) `image → region` GPU: 无 — 局部极大点检测。返回真正大于所有邻域像素(允许平台=数值相同的连通区域)的像素集合作为区域 —— 是峰值检测、特征点提取的前处理步骤。 · 示例: `gallery2d_segmentation`
- `sk_niblack` (halcon: `var_threshold`) `image → region` GPU: 无 — Niblack 局部自适应阈值法。与 Sauvola 一样根据局部均值、标准差确定阈值,但系数的给定方式更为简单(经典),相比 Sauvola 有将前景判定得偏宽(=更容易拾取噪声)的倾向。 · 示例: `gallery2d_segmentation`, `poc_segmentation_gauntlet`, `threshold_family_agreement`
- `sk_otsu` (halcon: `binary_threshold`) `image → region` GPU: 有(许可列表) — 基于大津判别分析法(Otsu's method)的全局阈值二值化。自动选择使类间方差最大化的阈值,将整幅图像二分为前景/背景。 · 示例: `gallery2d_segmentation`, `poc_am_thermal_to_ct`, `poc_cell_counting`, `poc_fresco_craquelure`, `poc_leaf_disease_area`, `poc_nuclei_ploidy`, `poc_vegetation_cover`, `threshold_family_agreement`
- `sk_sauvola` (halcon: `var_threshold`) `image → region` GPU: 无 — Sauvola 局部自适应阈值法。根据每个像素周围的局部均值与标准差来局部地确定阈值,专为存在照明不均的文档图像二值化(文字提取)而设计。 · 示例: `gallery2d_segmentation`, `poc_matrix_code_reading`, `poc_segmentation_gauntlet`, `threshold_family_agreement`
- `sk_slic` `image → region` GPU: 无 — 基于 SLIC(Simple Linear Iterative Clustering)的超像素分割。在结合了颜色(此处为灰度值)与坐标的空间中进行 k-means 聚类,将图像分割为大小大致均等的区域。此处返回的是分割结果的边界线区域。 · 示例: `gallery2d_segmentation`, `poc_segmentation_gauntlet`
- `sk_yen` (halcon: `binary_threshold`) `image → region` GPU: 有(许可列表) — 基于 Yen 的最大相关准则(maximum correlation criterion)的全局阈值二值化。通过最大化基于直方图熵的评价量来选择阈值,是不同于大津法、Li 法的又一种自动阈值法。 · 示例: `gallery2d_segmentation`, `threshold_family_agreement`
- `threshold` (halcon: `threshold`) `image → region` GPU: 有(threshold) — 全局阈值处理（global threshold）。相当于 HALCON 的 ``threshold``（Segment an image using global threshold.）。 · 示例: `gallery2d_segmentation`, `poc_ai_built_inspection_scored`, `poc_bone_trabecular_thickness`, `poc_change_detection_misreg`, `poc_fresco_craquelure`, `poc_gear_tooth_metrology`, `poc_metal_grain_size`, `poc_real_bg_kalman_tracking`, `poc_real_sem_metal_layer`, `poc_real_walnut_cbct`, `poc_screw_thread_metrology`, `poc_tof_camera`, `poc_traffic_counting`, `poc_virtual_sem_kv_cd_bse`, `poc_water_level`, `tof_realdata`, `video_streaming`
- `var_threshold` (halcon: `var_threshold`) `image → region` GPU: 无 — Sauvola局部自适应二值化(``skimage.filters.threshold_sauvola``,窗口大小为``2*int(a*6)+3``)。由于同时利用局部平均值与局部标准差来决定阈值,因此比``dyn_threshold``更能应对照明不均或低对比度的文档。相当于HALCON``var_threshold``(Threshold an image by local mean and standard deviation analysis.)的近似(公式化的构想相似,但Sauvola的公式与HALCON的公式系数不同——数值结果并不相同)。 · 示例: `gallery2d_segmentation`, `poc_document_scan`
- `watersheds` (halcon: `watersheds`) `image → region` GPU: 无 — 分水岭(watershed)分割。将梯度图像视为地形,以暗区(``x < 0.2+0.3*a``)作为标记求出分水岭线,并返回该边界线。相当于HALCON的``watersheds``(Extract watersheds and basins from an image.)。 · 示例: `gallery2d_segmentation`, `poc_segmentation_gauntlet`
- `watersheds_threshold` (halcon: `watersheds_threshold`) `image → region` GPU: 无 — 实现与``watersheds``完全相同(``kind: "watershed"``)。HALCON的``watersheds_threshold``(Extract watershed basins from an image using a threshold.)原本是带有合并相邻集水盆地的深度阈值的运算符,但此替代实现并未实现该合并阈值,而是返回与``watersheds``相同的结果(近似的局限)。 · 示例: `gallery2d_segmentation`
- `xcv2_meanshift` `image → image` GPU: 无 — 使用均值漂移（mean-shift）滤波按区域平滑颜色/亮度（``cv2.pyrMeanShiftFiltering``）。 · 示例: `gallery2d_segmentation`
- `xcv_grabcut` `image → region` GPU: 无 — 通过 GrabCut（迭代图割）自动分离前景/背景。 · 示例: `gallery2d_segmentation`
- `xcv_watershed_markers` (halcon: `watersheds`) `image → region` GPU: 无 — 通过标记控制分水岭算法提取边界线。 · 示例: `gallery2d_segmentation`
- `xkor_canny` `image → region` GPU: 无 — 基于 Canny 法的边缘(二值区域)检测。调用 ``kornia.filters.canny``，在返回值中采用二值边缘图(``edges``)(舍弃梯度强度一侧)。 · 示例: `find_ops_by_meaning`, `gallery2d_segmentation`
- `xmh_bernsen` `image → region` GPU: 无 — Bernsen局部二值化（``mahotas.thresholding.bernsen``）。以邻域最大亮度与最小亮度的中间值作为局部阈值，仅在对比度低的区域回退到全局阈值。 · 示例: `gallery2d_segmentation`, `threshold_family_agreement`
- `xsk2_h_maxima` `image → region` GPU: 无 — h-maxima 变换（去除高度小于 h 的局部极大值）。调用 ``skimage.morphology.h_maxima``。 · 示例: `gallery2d_segmentation`, `poc_cell_counting`
- `xsk2_multiotsu` `image → image` GPU: 无 — 使用将大津判别分析法（Otsu's method）扩展为多值的多值大津法对灰阶进行量化。使用 ``skimage.filters.threshold_multiotsu``。 · 示例: `gallery2d_segmentation`, `poc_mri_bias_field`
- `xsk3_h_minima` `image → region` GPU: 无 — h-极小值变换(skimage ``morphology.h_minima``)。先将深度小于 ``h`` 的浅谷(局部极小值)拉平，再对剩下的极小点做二值标记——与 xmh_regmin 类似的谷点拾取处理，但可通过深度明确排除源自噪声的浅谷。 · 示例: `gallery2d_segmentation`, `genspark_external_review`
- `xsk3_peak_local_max` `image → region` GPU: 无 — 局部极大值点图(skimage ``feature.peak_local_max``)。检测彼此相距 ``min_distance`` 像素以上的局部亮度极大值坐标，并返回仅将这些坐标置为 1 的稀疏二值图像(逐像素的点，而非作为面的区域)。 · 示例: `gallery2d_segmentation`
- `xsk3_rank_otsu` `image → region` GPU: 无 — 局部大津二值化(skimage ``filters.rank.otsu``)。仅在邻域圆盘内求取大津判别分析法(Otsu's method)的阈值，并根据像素值是否超过该局部阈值进行二值化——与全局大津不同，即使在光照不均的图像上也能选出局部上合适的阈值。 · 示例: `gallery2d_segmentation`, `threshold_family_agreement`
- `xsk3_threshold_local_median` `image → region` GPU: 无 — 局部中位数自适应二值化(skimage ``filters.threshold_local`` 的 ``method='median'``)。以每个区块的中位数作为局部阈值，按像素值是否超过该阈值进行二值化。相比使用局部均值的版本，对离群值(噪声像素)更具鲁棒性。 · 示例: `gallery2d_segmentation`
- `xsk_flood` `image → region` GPU: 无 — 通过泛洪填充（flood fill）提取区域。 · 示例: `gallery2d_segmentation`
- `xsk_random_walker` `image → region` GPU: 无 — 基于随机游走（random walker）法的图基区域分割。 · 示例: `gallery2d_segmentation`, `genspark_external_review`, `poc_segmentation_gauntlet`
- `zero_crossing` (halcon: `zero_crossing`) `image → region` GPU: 有(许可列表) — 检测拉普拉斯算子（内含高斯平滑，sigma 为 ``0.5+2*a``）符号翻转的像素（过零点）。LoG 过零点是以能高精度定位边缘而著称的经典检测方法。相当于 HALCON 的 ``zero_crossing``（Extract zero crossings from an image.）。 · 示例: `gallery2d_segmentation`

#### 2d / self-similarity (1)
- `xmh_selfmatch` `image → image` GPU: 无 — 自相似图（使用``mahotas.template_match``进行自模板匹配）。将从图像中心裁出的小图块对整幅图像做模板匹配，并归一化，使越相似于该图块的位置数值越接近1。 · 示例: `gallery2d_features`

#### 2d / smoothing (50)
- `anisotropic_diffusion` (halcon: `anisotropic_diffusion`) `image → image` GPU: 有(anisotropic_diffusion) — Perona-Malik型各向异性扩散。对上下左右4个方向的像素差乘以高斯型传导函数``exp(-(Δ/K)^2)``并反复累加——在差值大于阈值K(=边缘)的方向不进行扩散,只在差值小(=平坦)的方向上平滑,是一种保边平滑处理。相当于HALCON的``anisotropic_diffusion``(Perform an anisotropic diffusion of an image.)。 · 示例: `gallery2d_smoothing_rank`
- `bilateral` (halcon: `bilateral_filter`) `image → image` GPU: 有(bilateral) — 保边平滑（双边滤波器）。相当于 HALCON 的 ``bilateral_filter``（bilateral filtering of an image.）。 · 示例: `gallery2d_smoothing_rank`, `quickstart`
- `bilateral_filter` (halcon: `bilateral_filter`) `image → image` GPU: 无 — OpenCV的双边滤波器(``cv2.bilateralFilter``)。根据空间距离与亮度差两者对邻近像素加权平均,是一种在保留边缘的同时进行平滑的常用方法。相当于HALCON的``bilateral_filter``(bilateral filtering of an image.)。 · 示例: `gallery2d_smoothing_rank`
- `binomial_filter` (halcon: `binomial_filter`) `image → image` GPU: 有(binomial_filter) — 以二项式系数(帕斯卡三角)为权重的可分离平滑滤波器。通过依次沿纵、横方向应用 ``ndimage.correlate1d``,用离散二项核来近似高斯核 —— 这与 HALCON 的 ``binomial_filter``(Smooth an image using the binomial filter.)所用核的思路相同。 · 示例: `gallery2d_smoothing_rank`
- `coherence_enhancing_diff` (halcon: `coherence_enhancing_diff`) `image → image` GPU: 有(许可列表) — 实现与``anisotropic_diffusion``完全相同(``kind: "anisotropic"``)。真正的coherence-enhancing diffusion是沿结构张量特征向量方向控制扩散方向的方法(用于连接线状结构),但此替代实现并未进行结构张量计算,而是以简单的Perona-Malik各向异性扩散代替(近似的局限——无法重现线状结构的连接效果)。是HALCON``coherence_enhancing_diff``(Perform a coherence enhancing diffusion of an image.)的代用。 · 示例: `gallery2d_smoothing_rank`
- `cv_bilateral` (halcon: `bilateral_filter`) `image → image` GPU: 无 — 双边滤波器(OpenCV 实现)。这是一种同时以空间接近度与亮度值接近度为权重的高斯式平滑,能在不模糊边缘(亮度差较大的边界)的情况下,只平滑平坦区域。 · 示例: `gallery2d_smoothing_rank`
- `cv_box` (halcon: `mean_image`) `image → image` GPU: 无 — 简单平均化滤波器(box filter,OpenCV 实现)。仅对正方形邻域内取简单平均值的最基本平滑处理 —— 计算量比高斯平滑更轻,但容易产生环状伪影。 · 示例: `gallery2d_smoothing_rank`
- `cv_gaussian` (halcon: `gauss_filter`) `image → image` GPU: 无 — 高斯平滑（OpenCV 实现）。使用高斯核进行的标准模糊处理，比 box filter 更不容易产生振铃（ringing）。 · 示例: `gallery2d_smoothing_rank`
- `cv_nlmeans` `image → image` GPU: 无 — 非局部均值去噪（Non-local means，OpenCV 实现，灰度版本）。以 OpenCV 的高速实现方式，采用与 sk_nlm 相同的思路（在整幅图像中寻找相似的图块并取平均）。 · 示例: `find_ops_by_meaning`, `gallery2d_smoothing_rank`
- `cv_sharpen` (halcon: `emphasize`) `image → image` GPU: 有(cv_sharpen) — 类似非锐化蒙版的锐化滤波器（3x3 核卷积，OpenCV 实现）。以中心为 ``1+4a``、上下左右为 ``-a`` 的核（a=0 时为单位核＝不改变；a 越大，类离散拉普拉斯的高频增强越强）进行卷积，提升边缘附近的对比度。 · 示例: `gallery2d_smoothing_rank`
- `dl_aniso_diffusion` (halcon: `anisotropic_diffusion`) `image → image` GPU: 仅在链中(许可列表) — Perona-Malik 型各向异性扩散滤波器（torch 实现；若有 GPU 则在 GPU 上执行）。 · 示例: `gallery2d_smoothing_rank`
- `dl_guided_filter` (halcon: `guided_filter`) `image → image` GPU: 无 — 自引导滤波器（guided filter，引导图像＝输入自身，torch 实现）。 · 示例: `gallery2d_smoothing_rank`
- `f2_gauss_pyramid` (halcon: `gen_gauss_pyramid`) `image → image` GPU: 有(许可列表) — 返回图像高斯金字塔的某一层:先按 2 的 ``level`` 次幂降采样(模糊+抽取),再上采样回原始 HxW,得到分辨率降低的带限(低通)版本。``a`` 选择层级(1..4);``b`` 被忽略。 · 示例: `gallery2d_smoothing_rank`
- `gauss_filter` (halcon: `gauss_filter`) `image → image` GPU: 有(gauss_filter@twin) — 通过高斯模糊(``scipy.ndimage.gaussian_filter``,sigma 为 ``0.3+2.7*a``)实现的平滑处理。是 HALCON 的 ``gauss_filter``(Smooth using discrete Gauss functions.)的替代实现 —— HALCON 使用离散高斯核(整数运算),这里则是连续高斯核的 scipy 实现,虽是近似,但结果非常接近。 · 示例: `gallery2d_smoothing_rank`, `poc_cell_counting`, `poc_document_scan`, `poc_focus_stacking`, `poc_gear_tooth_metrology`, `poc_pv_thermal_survey`, `poc_sea_ice_concentration`, `poc_search_sweep_width`, `poc_solar_limb_darkening`, `poc_vanishing_detail_and_morphing_area`, `poc_vessel_network`, `poc_white_balance`
- `gauss_image` (halcon: `gauss_image`) `image → image` GPU: 有(gauss_image) — 实现与 ``gauss_filter`` 完全相同(同一个 ``kind: "gauss"`` 分支,sigma 为 ``0.3+2.7*a`` 的高斯模糊)。在 HALCON 中,``gauss_filter``(离散近似)与 ``gauss_image``(频域/连续高斯)是不同的算子,但此替代实现不作区分,指向同一函数。是 HALCON 的 ``gauss_image``(Smooth an image using discrete Gaussian functions.)的替代实现。 · 示例: `gallery2d_smoothing_rank`, `poc_colocalization_crosstalk`, `poc_moire_screen`, `poc_prnu_camera_fingerprint`, `poc_weld_radiograph_porosity`
- `gaussian` (halcon: `gauss_filter`) `image → image` GPU: 有(gauss_filter) — 各向同性高斯平滑。相当于 HALCON 的 ``gauss_filter``（Smooth using discrete Gauss functions.）。 · 示例: `coherence_scanning`, `color_transport`, `ct_inspection`, `degenerate_inputs`, `example_inner_diameter_mm`, `gallery2d_smoothing_rank`, `genspark_external_review`, `inspection_workflow`, `mcp_task_score`, `mcp_usability`, `perf_pointcloud_descriptors`, `photon_timeresolved`, `poc_ai_built_inspection_scored`, `poc_bone_trabecular_thickness`, `poc_caltab_chain_truth`, `poc_chromatic_confocal`, `poc_dtof_ranging`, `poc_flybrain_pointcloud`, `poc_interferometry_step`, `poc_itof_multifreq`, `poc_leaf_disease_area`, `poc_nir_silicon_transmission`, `poc_nuclei_ploidy`, `poc_simcal_telecentric`, `poc_simcal_thin_film`, `poc_solar_el_inspection`, `poc_solar_limb_darkening`, `poc_star_astrometry`, `poc_wound_area_tracking`, `quickstart`, `typed_results_json`, `video_streaming`
- `guided_filter` (halcon: `guided_filter`) `image → image` GPU: 无 — 实现与``bilateral_filter``完全相同(``kind: "bilateral"``)。真正的引导滤波(guided filter,基于局部线性模型的保边平滑)在数学上是不同的算法,但此替代实现以双边滤波代替(为满足相似用途=保边平滑的近似,结果数值并不一致)。是HALCON``guided_filter``(Guided filtering of an image.)的代用。 · 示例: `gallery2d_smoothing_rank`
- `isotropic_diffusion` (halcon: `isotropic_diffusion`) `image → image` GPU: 有(许可列表) — 实现是简单的高斯模糊(``gaussian_filter``,sigma为``0.5+2.5*a``)。由于各向同性扩散方程的解在数学上等价于高斯核卷积,此近似在理论上也是成立的(不具备各向异性扩散那样的保边效果,而是无论方向如何都均匀平滑)。相当于HALCON的``isotropic_diffusion``(Perform an isotropic diffusion of an image.)。 · 示例: `gallery2d_smoothing_rank`
- `kuwahara` `image → image` GPU: 有(许可列表) — Kuwahara 滤波（1976）。保边平滑：取四个相互重叠的窗口中方差最小者的均值作为输出。 · 示例: `gallery2d_smoothing_rank`
- `mean_box` (halcon: `mean_image`) `image → image` GPU: 有(mean_image) — 矩形窗口的简单平均（box）滤波器。相当于 HALCON 的 ``mean_image``（Smooth by averaging.）。 · 示例: `gallery2d_smoothing_rank`
- `mean_box_wh` (halcon: `mean_image`) `image → image` GPU: 有(许可列表) — 宽度与高度独立选择的平均（box）滤波。相当于 HALCON 的 ``mean_image``（Smooth by averaging.）。 · 示例: `gallery2d_smoothing_rank`, `mcp_task_score`
- `mean_curvature_flow` (halcon: `mean_curvature_flow`) `image → image` GPU: 有(许可列表) — 通过反复施加小 sigma(0.6)的高斯模糊来**近似**平均曲率流的平滑处理。它并非真正的平均曲率 PDE(``ops`` 侧的另一实现本应求解的扩散方程),而是用计算成本更低的反复模糊来替代 —— 这是此后端特有的近似局限。是 HALCON 的 ``mean_curvature_flow``(Apply the mean curvature flow to an image.)的替代实现。 · 示例: `gallery2d_smoothing_rank`
- `mean_image` (halcon: `mean_image`) `image → image` GPU: 有(mean_image@twin) — 矩形均值滤波(box filter)。这是相当于 HALCON 的 ``mean_image``(Smooth by averaging.)的一种近似,用边长为 k 的窗口的均值来替换目标像素。 · 示例: `gallery2d_smoothing_rank`, `poc_document_scan`, `poc_focus_stacking`, `poc_white_balance`
- `sigma_image` (halcon: `sigma_image`) `image → image` GPU: 有(许可列表) — 通过 sigma 滤波器实现的非线性平滑。仅对与中心像素值接近(``|x-mean|<σ``)的邻域像素取平均 —— 在边缘附近,对侧的灰阶不会混入平均值,因此比均值滤波更能在去噪的同时保留边缘。相当于 HALCON 的 ``sigma_image``(Non-linear smoothing with the sigma filter.)。 · 示例: `gallery2d_smoothing_rank`
- `simulate_defocus` (halcon: `simulate_defocus`) `image → image` GPU: 有(simulate_defocus) — 模拟均匀失焦（离焦）模糊的平滑化。实现为矩形窗口的均值滤波器（box filter，``ndimage.uniform_filter``），以正方形窗口近似，而非圆形光圈所形成的真实模糊形状（弥散圆，circle-of-confusion）。a 将窗口宽度分为 3/5/7/9 四档（``_k(a)``），b 未使用。 · 示例: `gallery2d_smoothing_rank`
- `simulate_motion` (halcon: `simulate_motion`) `image → image` GPU: 无 — 模拟线性运动模糊。在角度 ``π*a``(0〜180°)方向上生成长度为 ``5+10*b`` 像素的线段核并进行卷积。相当于 HALCON 的 ``simulate_motion``(Simulation of (linearly) motion blur.)。 · 示例: `gallery2d_smoothing_rank`
- `sk_nlm` `image → image` GPU: 无 — 非局部平均法(Non-local means)去噪。不仅在邻近像素中,而是在整幅图像范围内搜索相似的图块并取平均 —— 与单纯平滑化的区别在于,它能在保留重复图案与纹理的同时,只消除平坦区域的噪声。 · 示例: `find_ops_by_meaning`, `gallery2d_smoothing_rank`, `poc_prnu_camera_fingerprint`
- `sk_rolling_ball` `image → image` GPU: 有(sk_rolling_ball) — 基于滚球法(rolling ball)的背景扣除。将图像亮度视为地形,在其下方滚动指定半径的球体,以所得的包络面作为背景估计,并从原图像中减去 —— 用于去除照明不均(缓慢的亮度梯度)。 · 示例: `gallery2d_smoothing_rank`, `poc_weld_radiograph_porosity`
- `sk_tv` `image → image` GPU: 有(sk_tv) — 全变分去噪（TV denoising，Chambolle 方法）。在保留边缘的同时平滑平坦区域的噪声——与中值/高斯模糊不同，其特点是不易破坏轮廓的锐利度。 · 示例: `find_ops_by_meaning`, `gallery2d_smoothing_rank`, `poc_prnu_camera_fingerprint`
- `sk_tv_bregman` `image → image` GPU: 无 — 全变分去噪(TV denoising、Split-Bregman 法)。与 sk_tv 采用相同的 TV 正则化思路,但优化算法不同(Bregman 分裂法),据称收敛更快。 · 示例: `find_ops_by_meaning`, `gallery2d_smoothing_rank`
- `sk_wavelet` `image → image` GPU: 无 — 通过小波变换进行去噪。将图像分解到小波域，以 BayesShrink 准则的阈值处理去除较小(=可视为噪声)的系数，然后进行逆变换。 · 示例: `find_ops_by_meaning`, `gallery2d_smoothing_rank`, `poc_prnu_camera_fingerprint`
- `smooth_image` (halcon: `smooth_image`) `image → image` GPU: 有(许可列表) — 用单一高斯模糊(sigma 为 ``0.5+2.0*a``)近似的通用平滑处理。HALCON 的 ``smooth_image``(Smooth an image using various filters.)是可在 Deriche/Gauss/Mean 等多种滤波器类型中选择的万能算子,但这里简化为仅高斯一种(此近似的局限)。 · 示例: `gallery2d_smoothing_rank`
- `unsharp` (halcon: `emphasize`) `image → image` GPU: 有(unsharp_masking) — 非锐化掩蔽。★出口处 clip 到 [0,1] (2026-09-02)。 · 示例: `gallery2d_smoothing_rank`, `poc_camera_shake_deblur`, `poc_real_deblur_honesty`, `poc_superresolution_limits`
- `xcv3_denoise_tvl1` `image → image` GPU: 无 — 全变分 L1 去噪(OpenCV ``cv2.denoise_TVL1``，Primal-Dual 算法)。一种基于全变分最小化、在去除噪声的同时保留边缘的方法，相比普通高斯平滑，边缘保留得更锐利。 · 示例: `find_ops_by_meaning`, `gallery2d_smoothing_rank`
- `xcv3_pyr_laplacian` `image → image` GPU: 无 — 基于拉普拉斯金字塔的锐化。一种反锐化蒙版，先用 ``pyrDown`` 缩小再用 ``pyrUp`` 还原得到低频成分图像，将其从原图中减去得到差分(相当于拉普拉斯金字塔的一层、带通成分)，再将该差分加回原图以增强图像。 · 示例: `gallery2d_smoothing_rank`
- `xcv_edge_preserving` `image → image` GPU: 无 — OpenCV 的 edgePreservingFilter（保边平滑，``flags=1`` = RECURS_FILTER = 递归滤波方式）。 · 示例: `gallery2d_smoothing_rank`
- `xkor_bilateral` `image → image` GPU: 无 — 双边滤波器(保边平滑)。以 5x5 核调用 ``kornia.filters.bilateral_blur``。 · 示例: `gallery2d_smoothing_rank`
- `xkor_gaussian` `image → image` GPU: 无 — 高斯模糊(kornia 的 GPU 原生实现)。在 torch 张量上以与 sigma 匹配的窗口应用 ``kornia.filters.gaussian_blur2d``。 · 示例: `gallery2d_smoothing_rank`
- `xkor_motion_blur` `image → image` GPU: 无 — 运动模糊。调用 ``kornia.filters.motion_blur``。 · 示例: `gallery2d_smoothing_rank`
- `xkor_unsharp` `image → image` GPU: 无 — 反锐化蒙版(锐化)。以与 sigma 匹配的窗口调用 ``kornia.filters.unsharp_mask``(``v + (v - G_σ * v)``,强度固定为 1)。 · 示例: `gallery2d_smoothing_rank`
- `xpil_smooth_more` `image → image` GPU: 无 — Pillow 的平滑滤镜（增强版）。使用 ``PIL.ImageFilter.SMOOTH_MORE`` 的固定卷积核，比 ``SMOOTH`` 模糊得更强。 · 示例: `gallery2d_smoothing_rank`
- `xpil_unsharp_mask` `image → image` GPU: 无 — Pillow 的反锐化蒙版。调用 ``PIL.ImageFilter.UnsharpMask``（对应 kornia 版 ``xkor_unsharp`` 的 CPU 实现）。 · 示例: `gallery2d_smoothing_rank`
- `xsk3_rank_mean_bilateral` `image → image` GPU: 无 — 局部双边均值(skimage ``filters.rank.mean_bilateral``)。一种保边平滑，在圆盘邻域内仅对取值落在中心像素值下方 ``s0``、上方 ``s1`` 范围内的像素求平均。 · 示例: `gallery2d_smoothing_rank`
- `xsp_cspline_smooth` `image → image` GPU: 无 — 三次样条平滑滤波器（``scipy.signal.cspline2d``）。 · 示例: `gallery2d_smoothing_rank`
- `xsp_dct_denoise` `image → image` GPU: 无 — 通过对 DCT 系数进行硬阈值处理来去噪（小波收缩的 DCT 版本）。 · 示例: `find_ops_by_meaning`, `gallery2d_smoothing_rank`, `poc_prnu_camera_fingerprint`
- `xsp_savgol` `image → image` GPU: 有(许可列表) — 使用 Savitzky-Golay 滤波器平滑图像（按列方向→行方向的顺序进行一维处理）。 · 示例: `gallery2d_smoothing_rank`
- `xsp_wiener` `image → image` GPU: 有(许可列表) — 使用维纳自适应滤波器（``scipy.signal.wiener``）抑制噪声。 · 示例: `gallery2d_smoothing_rank`, `poc_prnu_camera_fingerprint`
- `xwt_firm_denoise` `image → image` GPU: 无 — 使用firm阈值处理（firm/semisoft thresholding、``pywt.threshold_firm``）的小波去噪。其特性介于软阈值与硬阈值之间，应用于``sym4``做2层分解后得到的各细节系数，再重建。 · 示例: `find_ops_by_meaning`, `gallery2d_smoothing_rank`
- `xwt_lf_reconstruct` `image → image` GPU: 无 — 低频重建图像。用``db2``分解，将所有细节系数归零，仅由近似成分逆变换重建 —— 结果是接近高斯模糊的多层小波平滑图像。 · 示例: `gallery2d_smoothing_rank`
- `xwt_visushrink` `image → image` GPU: 无 — VisuShrink风格的小波去噪。用``db4``做2层分解，对各层细节系数做软阈值处理后再逆变换重建（VisuShrink本是根据噪声量自动确定该阈值的方法，此处为直接以``a``给定阈值的简化版）。 · 示例: `gallery2d_smoothing_rank`

#### 2d / subpix (6)
- `sp_critical_points_sub_pix` (halcon: `critical_points_sub_pix`) `image → contour` GPU: 无 — 一并检测极大值、极小值与鞍点的子像素位置(相当于 HALCON ``critical_points_sub_pix``)。 · 示例: `gallery2d_geometry`
- `sp_local_max_sub_pix` (halcon: `local_max_sub_pix`) `image → contour` GPU: 无 — 以子像素精度检测灰度曲面的局部极大值(HALCON ``local_max_sub_pix`` 的替代实现。``halcon=""``:因为同名坐标已由现有的 core op 覆盖,故不重复申报)。 · 示例: `gallery2d_geometry`, `poc_tacsim_marker_shear`
- `sp_local_min_sub_pix` (halcon: `local_min_sub_pix`) `image → contour` GPU: 无 — 以子像素精度检测灰度曲面的局部极小值(相当于 HALCON ``local_min_sub_pix``)。 · 示例: `gallery2d_geometry`
- `sp_lowlands_center` (halcon: `lowlands_center`) `image → contour` GPU: 无 — 返回极小值"盆地"(比周围低的平坦区域)的重心(相当于 HALCON ``lowlands_center``)。 · 示例: `gallery2d_geometry`
- `sp_plateaus` (halcon: `plateaus`) `image → contour` GPU: 无 — 返回相同(量化后)灰度值相连而成的平坦区域(平台)的重心子像素位置(相当于 HALCON ``plateaus``)。 · 示例: `gallery2d_geometry`
- `sp_saddle_points_sub_pix` (halcon: `saddle_points_sub_pix`) `image → contour` GPU: 无 — 以子像素精度检测灰度曲面的鞍点(相当于 HALCON ``saddle_points_sub_pix``)。 · 示例: `gallery2d_geometry`

#### 2d / tactile (5)
- `tac_contact_mask` `image → region` GPU: 有(许可列表) — 通过伪参考背景减除来求触觉帧的接触区域:``dev = |v - G_sigma(v)|``,其中 ``sigma = max(2, min(H,W)/6)``(低频包络代替未形变的参考帧),以 ``thr = 0.005 + 0.145*a`` 灰度级阈值化,再经 ``round(3*b)`` 次二值开运算(opening)后接二值闭运算(closing)(3x3、8 连通)清理。``a`` = 偏差阈值(灵敏度),``b`` = 形态学清理强度。返回输入 HxW 大小的二值(BINARY)0/1 float64 区域;完全平坦(常数)的帧在各处偏差均为零,因此得到空掩膜。 · 示例: `poc_tacsim_elastic_membrane`, `sim2real_and_alife`
- `tac_height_from_shading` `image → image` GPU: 有(许可列表) — 对明暗梯度做泊松积分(Poisson integration)以求高度/浮雕图——这正是 GelSight 深度重建(以及光度立体视,photometric stereo)中的积分阶段:图像梯度被解读为表面斜率 ``p = gain*gx``、``q = gain*gy``,并以频谱方法求解泊松方程 ``lap(h) = div(p,q)``,即 ``h_hat = div_hat / lap_hat``,其中离散拉普拉斯算子的符号为 ``2cos(2*pi*u/W)+2cos(2*pi*v/H)-4``,(不确定的)直流(DC)分量被固定为零。``a`` = 梯度增益(0.25~4.25 倍),``b`` = 梯度场的预平滑 sigma(0~3)。输出经最小-最大归一化到 [0,1] 并重整回 HxW;常数帧积分后得到平坦(全零)的浮雕。 · 示例: `sim2real_and_alife`
- `tac_pressure_proxy` `image → image` GPU: 有(许可列表) — 接触压力近似图:对伪参考背景的整流偏差 ``dev = |v - G_sigma(v)|`` 只保留高偏差(接触)区域——相对门限为 ``0.15 * max(dev)`` 再加绝对底限 0.005——经灵敏度增益放大并做高斯平滑,这是触觉垫没有力传感器时常用的“压痕深度与法向力单调相关”的标准代理量。``a`` = 灵敏度(增益 1~10 倍),``b`` = 平滑半径(sigma 0.5~4.5)。输出裁剪到 [0,1],大小为 HxW;平坦帧得到全零的压力图(无接触、无力)。 · 示例: `sim2real_and_alife`
- `tac_shear_field` `image → image` GPU: 有(许可列表) — 由二维结构张量(Foerstner / Bigun-Granlund 方向一致性)求面内剪切(in-plane shear)近似。张量 ``J = G_sigma(grad v * grad v^T)`` 的特征值为 l1 >= l2,一致性 ``(l1-l2)/(l1+l2) = sqrt((J11-J22)^2 + 4*J12^2) / (J11+J22)`` 在凝胶纹理被拉伸成单一主方向时(如在切向/剪切载荷下)为 1,在各向同性时为 0。结果还会乘以张量迹(梯度能量)作为权重,以使无纹理、未接触的凝胶保持暗色,而不会放大噪声方向。``a`` = 张量积分 sigma(0.6~4.6),``b`` = 输出增益(0.5~2.5)。输出裁剪到 [0,1],大小为 HxW;常数帧的梯度能量为零,得到全零的剪切场。 · 示例: `poc_tacsim_marker_shear`, `sim2real_and_alife`
- `tac_surface_normal` `image → image` GPU: 仅在链中(许可列表) — 由明暗梯度求表面法线(surface normal)的 z 分量(斜率图),使用 Horn 的明暗恢复形状(shape-from-shading)法线参数化 ``n = (-p, -q, 1)/sqrt(1+p^2+q^2)``,因此 ``nz = 1/sqrt(1+p^2+q^2)``,其中 ``p = gain*gx``、``q = gain*gy``。平坦(未接触)的凝胶给出 nz = 1,陡峭的凹陷壁趋于 0,因此该图本身就已经是合法的 [0,1] 编码。``a`` = 梯度增益(1~21 倍——假定明暗有多陡),``b`` = 图像的预平滑 sigma(0~3),用于抑制传感器噪声。常数输入 → 全 1(完全平坦的凝胶)。 · 示例: `sim2real_and_alife`

#### 2d / texture (28)
- `bootstrap_std_error` `image → image` GPU: 有(许可列表) — 不假定分布地测量局部标准差的**标准误差**(自助法)。 · 示例: `gallery2d_texture_freq`
- `cooc_feature_matrix` (halcon: `cooc_feature_matrix`) `image → feature` GPU: 无 — 从灰度共生矩阵(GLCM,``skimage.feature.graycomatrix``,量化为 16 阶,距离 ``1+3*a``,角度 0°)计算 Haralick 纹理特征 ``energy``(角二阶矩,即矩阵值的集中程度=纹理均匀性)。相当于 HALCON 的 ``cooc_feature_matrix``(Calculate gray value features from a co-occurrence matrix.)(HALCON 可同时返回多个特征、多个角度,但这里简化为固定 energy、角度 0°)。 · 示例: `gallery2d_texture_freq`, `poc_real_texture_invariance`
- `deviation_image` (halcon: `deviation_image`) `image → image` GPU: 有(deviation_image) — 将矩形窗口内像素值的标准差(局部标准差,即``E[x^2]-E[x]^2``的平方根)归一化后得到的图像。用于可视化纹理的局部离散程度(粗糙度)。相当于HALCON的``deviation_image``(Calculate the standard deviation of gray values within rectangular windows.)。 · 示例: `gallery2d_texture_freq`
- `entropy_image` (halcon: `entropy_image`) `image → image` GPU: 无 — 将圆形窗口内灰度Shannon熵(``skimage.filters.rank.entropy``,8位量化)归一化后得到的图像。是衡量窗口内灰阶“离散程度”的纹理指标,在均匀区域较低,在灰阶混杂区域较高。相当于HALCON的``entropy_image``(Calculate the entropy of gray values within a rectangular window.)(HALCON使用矩形窗口,此处以圆形窗口作为近似)。 · 示例: `gallery2d_texture_freq`
- `f2_symmetry` (halcon: `symmetry`) `image → image` GPU: 有(许可列表) — 灰度值沿水平方向(逐行)的局部镜像对称性。对每个像素,测量加权非对称和 sum_d (1/d)|I(i,j-d) - I(i,j+d)|(d=1..r);响应值低表示该列邻域左右对称。``a`` 设置半径 r(1..6);``b`` 被忽略。输出为归一化到 [0,1] 的非对称响应。 · 示例: `gallery2d_texture_freq`
- `gabor` (halcon: `gen_gabor`) `image → image` GPU: 有(许可列表) — Gabor 能量 |v * g| —— 具方向性的带通纹理响应。 · 示例: `gallery2d_texture_freq`, `poc_patch_anomaly`
- `gen_gabor` (halcon: `gen_gabor`) `image → image` GPU: 有(许可列表) — 返回单一Gabor核(方向``θ=π*a``,频率``0.1+0.3*b``)卷积响应的绝对值,并以核的L1范数归一化。这是去除直流分量(减去均值)的纯实部核,对指定方向、频率的条纹图案有选择性反应的带通纹理滤波器。相当于HALCON的``gen_gabor``(Generate a Gabor filter.)(不含虚部/相位的纯实数核简化版)。 · 示例: `gallery2d_texture_freq`
- `local_bimodality` `image → image` GPU: 有(许可列表) — **局部双峰性**(bimodality coefficient)。连 1 个阈值都不选取，仅以 0〜1 的图返回“此处是否分成 2 个值”。 · 示例: `gallery2d_texture_freq`
- `local_std` `image → image` GPU: 有(许可列表) — 以**与输入相同的单位**返回局部窗口内的标准差(不做归一化)。相当于 HALCON 的 ``deviation_image``(Calculate the standard deviation of gray values within rectangular windows.)。 · 示例: `gallery2d_texture_freq`
- `scale_select_std` `image → image` GPU: 有(许可列表) — 逐像素**选择窗口大小**的局部标准差(Lepski / ICI 规则)。 · 示例: `gallery2d_texture_freq`
- `sk_entropy` (halcon: `entropy_image`) `image → image` GPU: 无 — 局部熵。计算每个像素周围(圆盘状邻域)灰度值分布的香农熵(以 2 为底的对数),并将其成像为编码该位置所需的最小比特数 —— 是纹理复杂度、信息量的度量指标。 · 示例: `gallery2d_texture_freq`
- `sk_frangi` (halcon: `lines_gauss`) `image → image` GPU: 无 — Frangi 管状结构检测滤波器（vesselness filter）。根据 Hessian 矩阵的特征值比来检测血管、皱纹、河流等细长的管状结构。 · 示例: `gallery2d_texture_freq`, `poc_fresco_craquelure`, `poc_solar_el_inspection`
- `sk_gabor` (halcon: `gen_gabor`) `image → image` GPU: 无 — Gabor 滤波器的响应强度。通过卷积以正弦波调制的高斯核，对具有特定空间频率和方向的纹理产生强烈响应的经典特征提取器。 · 示例: `gallery2d_texture_freq`
- `sk_hessian` (halcon: `lines_gauss`) `image → image` GPU: 无 — Hybrid Hessian 滤波器。与 Frangi 几乎相同的管状结构检测，但平滑方法不同（可近似作为 Frangi 的替代品使用）。 · 示例: `gallery2d_texture_freq`
- `sk_lbp` `image → image` GPU: 无 — LBP(局部二值模式,Local Binary Pattern)。以每个像素为中心,与其圆周上的邻域像素逐一比较大小生成二进制编码,是一种对光照变化具有鲁棒性的纹理描述符。 · 示例: `gallery2d_texture_freq`, `poc_real_texture_invariance`
- `sk_meijering` (halcon: `lines_gauss`) `image → image` GPU: 无 — Meijering 神经突起检测滤波器（neuriteness filter）。与 Frangi 一样根据 Hessian 的特征值计算与管状结构的相似度，但正规化方法不同（针对神经突起图像调优的公式）。 · 示例: `gallery2d_texture_freq`
- `sk_shape_index` `image → image` GPU: 无 — 形状指标(shape index)。根据 Hessian 矩阵的特征值,将局部曲面形状用一个从 -1(球状凹陷)经 0(鞍点)到 +1(球状凸起)的一维标量表示 —— 是概括曲率「方向」的描述符。 · 示例: `gallery2d_texture_freq`
- `std_filter` (halcon: `deviation_image`) `image → image` GPU: 有(std_image) — 局部窗口内的标准差（纹理粗糙度的指标）。相当于 HALCON 的 ``deviation_image``（Calculate the standard deviation of gray values within rectangular windows.）。 · 示例: `gallery2d_texture_freq`
- `structure_tensor_coherence` `image → image` GPU: 有(许可列表) — 以 ``[0,1]`` 返回局部**方向一致程度**(结构张量的各向异性)。 · 示例: `gallery2d_texture_freq`
- `structure_tensor_orientation` `image → image` GPU: 有(许可列表) — 返回局部**条纹走向**(结构张量的主轴)，并映射到 ``[0,1]``。 · 示例: `degenerate_inputs`, `gallery2d_texture_freq`
- `texture_laws` (halcon: `texture_laws`) `image → image` GPU: 有(texture_laws) — 实现为局部方差(``deviation_image``的方差版本,即窗口内的``E[x^2]-E[x]^2``)。真正的Laws纹理滤波器是由L5/E5/S5/W5/R5等一维核对组成的25种卷积组(捕捉能量/边缘/波状/斑点/波纹),但此替代实现并非使用全部卷积组,而是以单一的局部方差代替(近似的局限——方向别、频率别的信息会丢失)。是HALCON``texture_laws``(Filter an image using a Laws texture filter.)的代用。 · 示例: `gallery2d_texture_freq`
- `tf_census_transform` `image → image` GPU: 无 — census_transform：3x3 非参数化 census 位签名图像。 · 示例: `gallery2d_texture_freq`
- `tf_rank_transform` `image → image` GPU: 有(许可列表) — rank_transform：每个像素在其邻域中的局部秩（rank）。 · 示例: `gallery2d_texture_freq`
- `xsk2_hog` `image → image` GPU: 无 — HOG（Histogram of Oriented Gradients）特征量的可视化图像。以 ``visualize=True`` 调用 ``skimage.feature.hog``，返回可视化图像那一侧（丢弃特征向量本身）。 · 示例: `gallery2d_texture_freq`
- `xsk_meijering` `image → image` GPU: 无 — Meijering neuriteness 滤波器。以 sigma=1,2,3 三个尺度应用 ``skimage.filters.meijering``，增强细长曲线状结构（如血管、神经突起等）（与 Frangi 系相同，都是从 Hessian 矩阵的特征值计算脊线似然度，但 Meijering 对分支点也有很强的响应）。 · 示例: `gallery2d_texture_freq`, `poc_fresco_craquelure`
- `xsk_sato` `image → image` GPU: 无 — Sato tubeness 滤波器。以 sigma=1,2,3 三个尺度应用 ``skimage.filters.sato``，增强管状结构（如血管等）。从 Hessian 矩阵的特征值比计算线状/管状似然度这一点与 ``xsk_meijering`` 同系，但响应权重不同，对分支点的响应不如 Meijering 强烈。 · 示例: `gallery2d_texture_freq`, `poc_fresco_craquelure`
- `xsk_struct_coherence` `image → image` GPU: 无 — 结构张量的相干性（方向的一致性）。 · 示例: `gallery2d_texture_freq`
- `xsp_hilbert_env` `image → image` GPU: 有(许可列表) — 沿行方向提取解析信号（希尔伯特变换）的振幅包络。 · 示例: `gallery2d_texture_freq`

#### 2d / texture-feature (1)
- `xmh_pftas` `image → feature` GPU: 无 — PFTAS（parameter-free threshold adjacency statistics、``mahotas.features.pftas``）54维特征向量的方差。这是一种纹理特征，汇总了以无参数阈值统计相邻像素灰度关系所得的多组直方图。 · 示例: `gallery2d_features`

#### 2d / texture/shape-feature (1)
- `xmh_zernike` `image → feature` GPU: 无 — 泽尼克矩（Zernike moments、``mahotas.features.zernike_moments``）的总和。将映射到单位圆上的图像的旋转不变形状/灰度分布特征压缩为单个实数返回。 · 示例: `gallery2d_features`

#### 2d / tomography (5)
- `tm_backproject_unfiltered` `image → image` GPU: 无 — 对输入正弦图进行普通（未滤波）反投影 —— 经典的模糊重建。由于未应用斜坡滤波器，高频被抑制，每个点都会扩散出 1/r 形式的模糊：这是刻意展示为什么 FBP 需要滤波器。``a``／``b`` 均未被使用（这是固定的朴素基线）。若可用则使用带 ``filter_name=None`` 的 ``skimage.transform.iradon``，否则使用 NumPy 的普通反投影。输出重新拟合为 HxW。 · 示例: `gallery2d_physics_alife_3d`
- `tm_fbp_reconstruct` `image → image` GPU: 无 — 滤波反投影（FBP）：将 ``v`` 视为正弦图（行 = 角度，列 = 探测器，假定角度在 [0,180) 上均匀分布）并重建切片。``b`` 选择重建滤波器 —— b < 0.5 -> Ram-Lak（斜坡滤波器），b >= 0.5 -> Shepp-Logan。``a`` 未被使用（滤波器才是有意义的旋钮）。若可用则使用 ``skimage.transform.iradon``，否则使用 NumPy 的 FFT 斜坡滤波反投影。输出重新拟合为 HxW。 · 示例: `gallery2d_physics_alife_3d`
- `tm_radon_forward` `image → image` GPU: 无 — 正向 Radon 投影：将 ``v`` 视为切片图像，沿平行射线对其积分以构建正弦图（行 = 角度，列 = 探测器），再重新拟合回原始的 HxW。``a`` 设定采集的角度数量（``n = round(H*a)``，钳制在 8..360 —— 稀疏视角旋钮）；``b`` 设定角度跨度（``span = 180*min(1, 0.5+b)`` 度：b < 0.5 为有限角度 CT，b >= 0.5 —— 包括默认值 b = 0.5 —— 为 ``tm_fbp_reconstruct``／``tm_sart_reconstruct``／``tm_backproject_unfiltered`` 所假设的完整 [0,180) 跨度，因此在默认旋钮下，正向 -> 反向的自然链路可以往返一致）。若可用则使用 ``skimage.transform.radon``，否则使用 NumPy 的旋转求和 Radon 变换。 · 示例: `gallery2d_physics_alife_3d`
- `tm_sart_reconstruct` `image → image` GPU: 无 — 代数重建：对输入正弦图（行 = 角度）执行若干轮 SART/SIRT 扫描。``a`` 设定迭代次数（``round(1+a*4)`` -> 1..5），``b`` 设定松弛因子（``0.05 + b*0.35``）。若可用则使用 ``skimage.transform.iradon_sart``，否则使用自实现的 NumPy SIRT 循环（投影 -> 残差 -> 加权反投影）。输出重新拟合为 HxW。 · 示例: `gallery2d_physics_alife_3d`
- `tm_sinogram_denoise` `image → image` GPU: 有(许可列表) — 沿角度方向（行）对输入正弦图进行平滑。相邻投影角度所观察到的几乎是同一物体，因此角度方向的平滑是一种真正的一致性先验，能在保留正弦轨迹的同时抑制逐角度的探测器噪声。``a`` 设定角度轴的高斯 sigma（``a*4``），``b`` 附加一个温和的探测器轴 sigma（``b*1.5``）。输出仍为同形状、值域 [0,1] 的正弦图。 · 示例: `gallery2d_physics_alife_3d`

#### 2d / transform (3)
- `tf_radon_sinogram` `image → image` GPU: 无 — radon_sinogram：将 Radon 变换渲染为 HxW 大小的正弦图（sinogram）图像。 · 示例: `gallery2d_geometry`
- `xmh_daubechies` `image → image` GPU: 无 — Daubechies小波变换（``mahotas.daubechies``）。与xmh_haar采用相同的排列方式（单层，将系数塞入原图尺寸的数组后做min-max归一化），只是把基底换成了Daubechies系。 · 示例: `gallery2d_geometry`
- `xmh_haar` `image → image` GPU: 无 — Haar小波变换（``mahotas.haar``）。先将图像裁切为偶数尺寸再变换，然后直接对得到的系数数组（近似/水平/垂直/对角各子带被塞入与原图同尺寸的数组中，属于Matlab风格的原位排列）做min-max归一化后作为图像展示。 · 示例: `gallery2d_geometry`

#### 2d / typed (163)
- `tb_abs_funct_1d` `signal → signal` GPU: 仅在链中(许可列表) — y 值的绝对值(HALCON ``abs_funct_1d``)。 · 示例: 无
- `tb_alpha_shape_boundary` `points → signal` GPU: 无 — 通过 alpha shapes 返回**边界点索引**（点云 → 边界点）。 · 示例: 无
- `tb_angular_spectrum_propagate` `cimage → cimage` GPU: 有(许可列表) — 复数场的精确标量自由空间传播（角谱法）。 · 示例: 无
- `tb_apply_weighting` `signal → signal` GPU: 有(许可列表) — 对信号施加 A / C / Z 频率计权，零相位。 · 示例: 无
- `tb_arc_length` `points → feature` GPU: 无 — 曲线的累积弧长与总长。→ (cumulative (N,), total float)。 · 示例: 无
- `tb_background_subtraction_window` `video → video` GPU: 无 — 因果窗口中值背景 → 逐帧 0/1 前景掩膜 ``(T, H, W)``（``video``）。 · 示例: 无
- `tb_bandpass` `signal → signal` GPU: 无 — 在 *low* 与 *high* Hz 之间的巴特沃斯带通滤波。两个边界都必须在 ``(0, rate/2)`` 范围内;长度约束与 :func:`lowpass` 相同。 · 示例: 无
- `tb_beamform_delay_sum` `beatcube → signal` GPU: 无 — 针对单个距离-多普勒单元的延迟求和（Bartlett）角度谱。 · 示例: 无
- `tb_box_sdf` `points → volume` GPU: 无 — 轴对齐长方体的**精确**有符号距离场(内部为负,外部为正)。 · 示例: 无
- `tb_capsule_sdf` `points → volume` GPU: 无 — 将线段 ``a``–``b`` 以半径 ``radius`` 加粗所得胶囊体的**精确**有符号距离场。 · 示例: 无
- `tb_companding_mu_law` `signal → signal` GPU: 有(许可列表) — μ 律压扩 —— 把 G.711 的曲线用于任意一维信号。 · 示例: 无
- `tb_countrate_to_counts` `counts → counts` GPU: 无 — 计数率 ``[Hz]`` → 计数 ``counts``。``countrate`` 的出口（**可逆**）。 · 示例: 无
- `tb_counts_to_countrate` `counts → counts` GPU: 无 — 计数 → 计数率 ``[Hz]``。是 :func:`countrate_to_counts` 的逆运算。 · 示例: 无
- `tb_cplx_cr_residual` `cimage → feature` GPU: 无 — 采样复数场的 Cauchy-Riemann 残差——将“这个场是否全纯？”量化为一个数值。 · 示例: 无
- `tb_create_funct_1d_array` `signal → signal` GPU: 无 — 由等距采样点构建一维函数(HALCON ``create_funct_1d_array``)。 · 示例: 无
- `tb_cutout` `points → points` GPU: 无 — 移除一个空间上的轴对齐盒状区域，并返回 ``(kept, kept_idx)``（模拟局部数据缺失）。 · 示例: 无
- `tb_cx_apply_transfer_function` `cimage → cimage` GPU: 仅在链中(许可列表) — 将**已中心化**的频谱与滤波器 ``H`` 相乘 -> ``(H, W)`` complex128。 · 示例: `gallery_spectrum_signal_bridge`
- `tb_cx_ifft` `cimage → image` GPU: 有(许可列表) — :func:`cx_fft` 的逆运算: ``ifft2(ifftshift(cx))``。 · 示例: `gallery_spectrum_signal_bridge`
- `tb_cx_imag` `cimage → image` GPU: 无 — ``cx`` 的虚部 -> 实数 ``(H, W)`` float64(原始值,未做限幅)。 · 示例: `gallery_spectrum_signal_bridge`
- `tb_cx_log_magnitude` `cimage → image` GPU: 仅在链中(许可列表) — 用于**显示**的对数幅度谱 -> 实数 ``(H, W)`` float64,范围 ``[0, 1]``。 · 示例: `gallery_spectrum_signal_bridge`
- `tb_cx_magnitude` `cimage → image` GPU: 无 — 逐像素幅度 ``|cx|`` -> 实数 ``(H, W)`` float64。 · 示例: `gallery_spectrum_signal_bridge`
- `tb_cx_phase` `cimage → image` GPU: 仅在链中(许可列表) — ``cx`` 的(缠绕)相位 -> 实数 ``(H, W)`` float64。 · 示例: `gallery_spectrum_signal_bridge`
- `tb_cx_real` `cimage → image` GPU: 无 — ``cx`` 的实部 -> 实数 ``(H, W)`` float64(原始值,未做限幅)。 · 示例: `gallery_spectrum_signal_bridge`
- `tb_cylinder_sdf` `points → volume` GPU: 无 — 有限长圆柱(两端为平盖)的**精确**有符号距离场(内侧为负、外侧为正)。 · 示例: 无
- `tb_deflicker` `video → video` GPU: 无 — 逐帧亮度去闪烁 → ``(T, H, W)``（``video``）。 · 示例: 无
- `tb_dem_ecef_to_geodetic` `points → points` GPU: 无 — ECEF → 大地坐标。返回 ``(..., 3)`` 的 ``(纬度[度], 经度[度], 高度[m])``。 · 示例: 无
- `tb_derivate_funct_1d` `signal → signal` GPU: 仅在链中(许可列表) — 通过中心差分计算一阶导数(HALCON ``derivate_funct_1d``)。 · 示例: 无
- `tb_drag_coefficient_sphere` `signal → signal` GPU: 有(许可列表) — 光滑球体阻力系数的经验公式(Morrison 2013，Re ≲ 1e6)：24/Re + 2.6(Re/5)/(1 + (Re/5)^1.52) + 0.411(Re/263000)^−7.94/(1 + (Re/263000)^−8) + 0.25(Re/1e6)/(1 + Re/1e6)。对乒乓球(Re ≈ 1〜5 × 10⁴)为 0.39〜0.41(Re 1.6 × 10⁴ = 6 m/s 时为 0.392，5 × 10⁴ 时为 0.406，1 × 10⁵ 时为 0.426；在 Re ≈ 3 × 10⁵ 的阻力危机处降至 0.17)。 · 示例: 无
- `tb_dtof_depth` `counts → feature` GPU: 无 — 由光子到达时间直方图得到的距离：``d = c*t/2``。 · 示例: 无
- `tb_dynsys_correlation_dimension` `points → feature` GPU: 无 — Grassberger–Procaccia 关联维数 —— ``log C(r)`` 的斜率。 · 示例: 无
- `tb_elastic_deform` `points → points` GPU: 无 — 通过平滑随机位移场进行弹性变形（相关距离 ``sigma``，均方根振幅 ``alpha``）。 · 示例: 无
- `tb_env_lightbox` `points → signal` GPU: 无 — 摄影灯箱环境（大面积顶部光源 + 略微明亮的周围环境）。**无彩色**。 · 示例: 无
- `tb_env_studio` `points → signal` GPU: 无 — 摄影棚环境的辐射亮度（方向 -> 亮度）。**无彩色**。 · 示例: 无
- `tb_envelope` `signal → signal` GPU: 有(许可列表) — 通过解析信号(希尔伯特变换)得到振幅包络——即敲击/冲击/声发射脉冲的形状。 · 示例: 无
- `tb_equivalent_level` `signal → feature` GPU: 无 — 记录的能量等效级，单位为相对于 ``ref`` 的 dB。 · 示例: 无
- `tb_estimate_alpha` `points → feature` GPU: 无 — 根据点云的尺度返回推荐的 alpha（基于最近邻距离的中位数）。 · 示例: 无
- `tb_estimate_normals` `points → points` GPU: 无 — 统一朝外（远离邻域重心）方向的点云法线。→ (N,3)。 · 示例: 无
- `tb_estimate_oriented_normals` `points → points` GPU: 无 — PCA 法线估计与 Hoppe 全局定向传播的组合。→ (N,3) 的定向单位法线。 · 示例: 无
- `tb_estimate_point_normals` `points → points` GPU: 无 — 点云 (N,3) → 单位法线（局部 k 近邻协方差的最小特征向量 = PCA）。 · 示例: 无
- `tb_euclidean_cluster` `points → volume` GPU: 无 — 通过半径为 tol 的邻近图的连通分量进行距离聚类（-1 = 噪声）。 · 示例: 无
- `tb_exponential_background` `video → video` GPU: 仅在链中(许可列表) — 逐帧递归背景 ``bg ← (1−α)·bg + α·frame`` → ``(T, H, W)``（``video``）。 · 示例: 无
- `tb_exponential_foreground` `video → video` GPU: 无 — 前景掩膜 ``|frame − exponential background| > threshold`` → 0/1 ``(T, H, W)``（``video``）。 · 示例: 无
- `tb_farthest_point_sampling` `points → signal` GPU: 无 — 基于测地距离的最远点采样（均匀抽稀）。→ 所选索引数组 (n,) int。 · 示例: 无
- `tb_find_peaks` `signal → signal` GPU: 无 — 峰值索引(scipy.signal.find_peaks)——用于冲击/缺陷回波。 · 示例: 无
- `tb_fit_spline_curve` `points → points` GPU: 无 — 用 B 样条对有序 3D 点列进行平滑并重新采样。→ (M,3)。用于平滑带噪声的轨迹/边缘。 · 示例: 无
- `tb_fly_lgmd_eta` `signal → signal` GPU: 有(许可列表) — 由扩张的视张角得到的 LGMD/eta 逼近(looming)响应。 · 示例: 无
- `tb_fly_tau_from_expansion` `signal → signal` GPU: 有(许可列表) — 由光学扩张得到的碰撞时间——tau 余量。 · 示例: 无
- `tb_fmcw_range_profile` `beatcube → signal` GPU: 无 — 仅距离剖面：快时间 FFT 幅度，对其余维度取平均。 · 示例: 无
- `tb_fmcw_window_apply` `beatcube → beatcube` GPU: 无 — 沿差频立方体的距离和/或多普勒轴施加周期性窗函数。 · 示例: 无
- `tb_frame_difference_causal` `video → video` GPU: 无 — ``|frame t − frame t−1|``，首帧为零 → ``(T, H, W)``（``video``）。 · 示例: 无
- `tb_gaussian_curvature` `points → signal` GPU: 无 — 高斯曲率 K=k1·k2（对法线翻转不变）。→ (N,)。 · 示例: 无
- `tb_geodesic_distances` `points → signal` GPU: 无 — 从 source 到所有点的测地距离（在 kNN 图上运行 Dijkstra）。→ (N,) float（不可达为 inf）。 · 示例: 无
- `tb_get_y_value_funct_1d` `signal → feature` GPU: 无 — (可为小数的)位置 *x* 处的 y 值(HALCON ``get_y_value_funct_1d``)。 · 示例: 无
- `tb_highpass` `signal → signal` GPU: 无 — 巴特沃斯高通滤波。奈奎斯特频率与长度约束与 :func:`lowpass` 相同。 · 示例: 无
- `tb_inertia_tensor` `points → matrix` GPU: 无 — 点云的惯性张量 (3,3)（由中心二阶矩计算，假设质量相等、总质量为 1）。 · 示例: 无
- `tb_inside_outside` `points → signal` GPU: 无 — 超二次曲面的内外函数 F（表面 = 1，内部 < 1，外部 > 1）。 · 示例: 无
- `tb_integrate_funct_1d` `signal → signal` GPU: 仅在链中(许可列表) — 使用梯形法则计算累积积分(HALCON ``integrate_funct_1d``)。 · 示例: 无
- `tb_intrinsics_to_carla` `matrix → matrix` GPU: 无 — :func:`intrinsics_to_fullseye` 的逆变换(把主点移回 0.5)。 · 示例: 无
- `tb_intrinsics_to_fullseye` `matrix → matrix` GPU: 无 — CARLA 的 K(像素角点为整数，主点 W/2)→ Fullseye / render3d 的 K(像素中心为整数，主点 (W−1)/2)。只是把主点平移 0.5。 · 示例: 无
- `tb_iqft2` `qimage → qimage` GPU: 有(许可列表) — 对**居中**频谱做四元数逆傅里叶变换。→ (H, W, 4)。 · 示例: 无
- `tb_iss_keypoints` `points → signal` GPU: 无 — ISS（Intrinsic Shape Signatures，相当于 3D 版 Harris）关键点检测。以局部协方差的最小特征值 λ3 作为 saliency，仅将特征值 distinct（方向 well-defined）的点作为候选，再用 NMS 稀疏地选取。旋转不变。返回值 = 点的索引数组。 · 示例: 无
- `tb_jitter` `points → points` GPU: 无 — 为每个点添加各向同性高斯噪声 ``N(0, sigma)``（模拟传感器位置噪声）。 · 示例: 无
- `tb_keypoints_rowcol_to_uv` `keypoints → keypoints` GPU: 无 — 像面点 ``(row, col)`` → ``(u, v) = (col, row)``。``keypoints`` 类型两种约定之间的连接。 · 示例: 无
- `tb_keypoints_to_image2d` `keypoints → image` GPU: 无 — 图像坐标 ``(N,2) = (u, v)`` → 计数图像 ``(H, W)``。``keypoints`` 的第二个出口。 · 示例: 无
- `tb_keypoints_uv_to_points` `keypoints → points` GPU: 无 — 图像坐标 ``(N,2) = (u, v)`` → 点云 ``(N,3) = (z, y, x)``。``keypoints`` 的出口。 · 示例: 无
- `tb_keypoints_uv_to_rowcol` `keypoints → keypoints` GPU: 无 — 像面点 ``(u, v) = (col, row)`` → ``(row, col)``。:func:`keypoints_rowcol_to_uv` 的反向。 · 示例: 无
- `tb_landmark_asymmetry` `points → signal` GPU: 无 — 每个左右对的**带符号**非对称量。→ ``(M,)``。 · 示例: 无
- `tb_lf_center_view` `lightfield → image` GPU: 无 — 中心视点——全光相机同时给出的普通二维图像。 · 示例: 无
- `tb_lf_depth_from_focus` `lightfield → image` GPU: 无 — 在重聚焦扫描中根据**清晰度峰值**得到的逐像素斜率。 · 示例: 无
- `tb_lf_epi` `lightfield → image` GPU: 无 — 极平面图像——**直线斜率即视差**的切片。 · 示例: 无
- `tb_lf_epi_slope` `lightfield → image` GPU: 有(许可列表) — 由 **EPI 线的方向**得到逐像素斜率(结构张量,再用剪切细化)。 · 示例: 无
- `tb_lf_refocus` `lightfield → image` GPU: 无 — 位移叠加重聚焦：在指定 *slope* 处对焦的合成孔径图像。 · 示例: 无
- `tb_lf_subaperture` `lightfield → image` GPU: 无 — 一个子孔径视图——透过瞳孔上一个点所看到的图像。 · 示例: 无
- `tb_lf_synthetic_aperture` `lightfield → image` GPU: 无 — 通过成形光圈重新对焦——若使用 ``reduce="median"``，还能穿透遮挡物。 · 示例: 无
- `tb_lf_to_mla` `lightfield → image` GPU: 无 — 将光场重新交织为微透镜阵列原始帧（精确逆变换）。 · 示例: 无
- `tb_local_std` `signal → signal` GPU: 无 — 带误差界的滑动标准差。 · 示例: 无
- `tb_lowpass` `signal → signal` GPU: 无 — 巴特沃斯低通滤波(scipy,零相位 filtfilt)。*cutoff* 必须在 ``(0, rate/2)`` 范围内;超出奈奎斯特(Nyquist)频率的 cutoff 会抛出异常,而不是直接放行信号。信号长度不足以进行零相位 filtfilt 时同样会抛出异常(错误信息会给出确切的最小长度),而不是悄悄返回未滤波的原始信号。 · 示例: 无
- `tb_magnus_lift_coefficient` `signal → signal` GPU: 仅在链中(许可列表) — 由旋转比 S = rω/|v| 求升力系数 C_L = 1 / (2 + 1/S)(S → 0 时为 0，S → ∞ 时为 0.5。球体文献中广泛使用的经验公式)。 · 示例: 无
- `tb_mat_cond` `matrix → feature` GPU: 无 — 谱(2-范数)条件数 ``s_max / s_min``——整个线性代数(linalg)算子族的数值健康指标(canary)。 · 示例: 无
- `tb_mat_pinv` `matrix → matrix` GPU: 无 — 通过 SVD 计算 Moore-Penrose 伪逆,截断阈值**显式**给出。 · 示例: 无
- `tb_mean_curvature` `points → signal` GPU: 无 — 平均曲率 H=(k1+k2)/2。→ (N,)。依赖于方向的量。 · 示例: 无
- `tb_mirror_plane_from_pairs` `points → matrix` GPU: 无 — 由左右对应的特征点求出正中面。→ ``(2, 3)``(第 1 行 = 点，第 2 行 = 法线)。 · 示例: 无
- `tb_mls_smooth` `points → points` GPU: 无 — 将各点投影到局部多项式曲面上以去除噪声（移动最小二乘法 Moving Least Squares 平滑）。 · 示例: 无
- `tb_monogenic_amplitude` `qimage → image` GPU: 有(许可列表) — 单演信号的局部幅值 ``sqrt(f^2 + R1^2 + R2^2)``。→ (H, W)。 · 示例: 无
- `tb_monogenic_orientation` `qimage → image` GPU: 有(许可列表) — 单演信号的局部方向 ``atan2(R2, R1)``。→ (H, W)。 · 示例: 无
- `tb_monogenic_phase` `qimage → image` GPU: 有(许可列表) — 单演信号的局部相位 ``atan2(|R|, f)``。→ (H, W)。 · 示例: 无
- `tb_motion_energy_image` `video → video` GPU: 无 — 逐帧 Bobick–Davis 运动能量图像 → 0/1 ``(T, H, W)``（``video``）。 · 示例: 无
- `tb_motion_history_image` `video → video` GPU: 无 — 逐帧 Bobick–Davis 运动历史图像 → ``(T, H, W)``，取值 ``[0, 1]``（``video``）。 · 示例: 无
- `tb_moving_average_window` `video → video` GPU: 无 — 对最近 *window* 帧逐像素取因果均值 → ``(T, H, W)``（``video``）。 · 示例: 无
- `tb_negate_funct_1d` `signal → signal` GPU: 仅在链中(许可列表) — 符号取反后的 y 值(HALCON ``negate_funct_1d``)。 · 示例: 无
- `tb_normals_to_egi` `points → image` GPU: 无 — 法线 ``(N,3)`` → 扩展高斯图像 ``(n_el, n_az)`` 的 ``image2d``。 · 示例: 无
- `tb_num_points_funct_1d` `signal → feature` GPU: 无 — 采样点数量(HALCON ``num_points_funct_1d``)。 · 示例: 无
- `tb_occupancy_grid` `points → volume` GPU: 无 — 点云 (N,3) → 三维占据体素栅格,bool(点落入的体素记为占据)。 · 示例: 无
- `tb_optical_flow_magnitude_stream` `video → video` GPU: 无 — 逐帧相对于前一帧的稠密光流速度 → ``(T, H, W)``（``video``）。 · 示例: 无
- `tb_pc_density_equalize` `points → points` GPU: 无 — 先填充稀疏区域,再稀疏化密集区域:实现均匀间距(``points``)。 · 示例: 无
- `tb_pc_fill_sparse` `points → points` GPU: 无 — 在局部间距超过 *spacing* 的地方,于局部 PCA 平面上插入点(``points``)。 · 示例: 无
- `tb_pc_poisson_disk` `points → points` GPU: 无 — 蓝噪声稀疏化:贪心地保留点,使任意两点之间的距离不小于 *radius*(``points``)。 · 示例: 无
- `tb_plane_sdf` `points → volume` GPU: 无 — 半空间的精确有符号距离场。``fast`` 是可选路径，在 1e6 处实测相对差 1.5e-10；默认为 ``exact``。 · 示例: 无
- `tb_plane_segmentation` `points → volume` GPU: 无 — 通过迭代 RANSAC 依次提取最多 max_planes 个平面（剩余残差点标为 -1）。 · 示例: 无
- `tb_points_render` `points → rgbimage` GPU: 无 — 把 (N, 3) 点云渲染为 RGB 图像 (H, W, 3):抗锯齿的足迹、按深度排序、结果确定。 · 示例: 无
- `tb_points_to_voxel` `points → volume` GPU: 无 — 点云 (N,3) → 密度体素 (size³)。通过 scatter_add 进行 splat，可选高斯平滑。 · 示例: 无
- `tb_points_zyx_to_keypoints_uv` `points → keypoints` GPU: 无 — 点云 ``(N,3) = (z, y, x)`` → 图像坐标 ``(N,2) = (u, v)``。 · 示例: 无
- `tb_project` `points → keypoints` GPU: 无 — 通过相机 (rvec,t,K) 将 3D 点 (n,3) 投影到 2D (n,2)（透视除法）。 · 示例: 无
- `tb_project_cylindrical` `points → image` GPU: 无 — 投影到圆柱形距离图像 (`z_bins`, `h_res`)。方位角(列)× z(行),像素值 = 水平半径 ρ = hypot(x,y)。 · 示例: 无
- `tb_project_points` `points → keypoints` GPU: 无 — 3D 点云 (N,3) → 图像坐标 (u,v) 与深度。针孔模型（depth_to_points 的正方向）。 · 示例: 无
- `tb_project_spherical` `points → image` GPU: 无 — 投影到旋转式 LiDAR 的球面距离图像 (`v_res`, `h_res`)。空单元格 = 0,最近的点优先(取最小 range)。 · 示例: 无
- `tb_qft2` `qimage → qimage` GPU: 有(许可列表) — 四元数（超复数）二维傅里叶变换。→ (H, W, 4) 居中频谱。 · 示例: 无
- `tb_quantize` `signal → signal` GPU: 仅在链中(许可列表) — 给出误差模型的标量量化器(可选抖动)。 · 示例: 无
- `tb_quat_color_filter` `qimage → qimage` GPU: 无 — 精确地保留或去除某一颜色方向。→ (H, W, 4)。 · 示例: 无
- `tb_quat_color_rotate` `qimage → qimage` GPU: 无 — 绕某个 RGB 轴旋转每个像素的颜色：``q x conj(q)``。→ (H, W, 4)。 · 示例: 无
- `tb_quat_conjugate_image` `qimage → qimage` GPU: 无 — 逐像素四元数共轭：``(w, -x, -y, -z)``。→ (H, W, 4)。 · 示例: 无
- `tb_quat_norm` `qimage → image` GPU: 无 — 逐像素四元数模：``|q| = sqrt(w^2+x^2+y^2+z^2)``。→ (H, W)。 · 示例: 无
- `tb_quat_normalize_image` `qimage → qimage` GPU: 无 — 逐像素归一化为单位模。→ (H, W, 4)。 · 示例: 无
- `tb_quaternion_to_rgb` `qimage → rgbimage` GPU: 仅在链中(许可列表) — 四元数图像的向量部分，作为线性 RGB。→ (H, W, 3)。 · 示例: 无
- `tb_radius_outlier_removal` `points → points` GPU: 无 — 去除在半径 radius 内邻居数小于 min_neighbors 的点（孤立点去除）。 · 示例: 无
- `tb_random_dropout` `points → points` GPU: 无 — 随机移除 ``ratio`` 比例的点，并返回 ``(kept, kept_idx)``（模拟数据缺失）。 · 示例: 无
- `tb_random_rotation` `points → points` GPU: 无 — 应用随机旋转并返回 ``(rotated, R)``（模拟视点变化）。 · 示例: 无
- `tb_random_scale` `points → points` GPU: 无 — 围绕原点应用均匀缩放 ``s ~ U(lo, hi)``，并返回 ``(scaled, s)``。 · 示例: 无
- `tb_range_doppler_map` `beatcube → image` GPU: 无 — 拍频立方体的二维 FFT -> ``(n_doppler, n_range)`` 幅度图。 · 示例: 无
- `tb_reflect_points` `points → points` GPU: 无 — 将点云沿平面(点 `plane_point`、法向量 `plane_normal`)镜像。→ (N,3)。 · 示例: 无
- `tb_reflection_symmetry_score` `points → feature` GPU: 无 — 反射对称分数 = chamfer(镜像, 原始) / 中位数最近邻间距(数值越小越对称,与尺度无关)。→ float。 · 示例: 无
- `tb_region_growing` `points → volume` GPU: 无 — 依据法线相似度进行区域生长，为连通的平滑区域赋予相同标签（不带曲率门控的变体）。 · 示例: 无
- `tb_render_point_depth` `points → image` GPU: 无 — 点云 → 深度图像（z-buffer，每个像素取最近点的深度）。用于观测合成/外观检测的示例。 · 示例: 无
- `tb_resample` `signal → signal` GPU: 有(许可列表) — 将信号重采样为 *new_rate*(傅里叶方法)。 · 示例: 无
- `tb_resample_uniform` `points → points` GPU: 无 — 按弧长等间隔重新采样为 n 个点（线性插值）。→ (n,3)。 · 示例: 无
- `tb_rgb_to_quaternion` `rgbimage → qimage` GPU: 无 — 将彩色图像嵌入为纯四元数 ``0 + R i + G j + B k``。→ (H, W, 4)。 · 示例: 无
- `tb_rms` `signal → feature` GPU: 无 — RMS(均方根)电平。整段信号返回一个标量,给定 *frame* 时返回逐帧数组(即随时间变化的振动/能量包络)。 · 示例: 无
- `tb_running_gaussian_background` `video → video` GPU: 有(许可列表) — 逐帧自适应单高斯背景（滑动均值）→ ``(T, H, W)``（``video``）。 · 示例: 无
- `tb_running_gaussian_foreground` `video → video` GPU: 无 — 逐帧自适应单高斯前景掩膜 → 0/1 ``(T, H, W)``（``video``）。 · 示例: 无
- `tb_sample_funct_1d` `signal → signal` GPU: 无 — 每隔 *step* 个取一个采样点(HALCON ``sample_funct_1d``)。 · 示例: 无
- `tb_scale_y_funct_1d` `signal → signal` GPU: 仅在链中(许可列表) — 对 y 值进行线性映射,``mult * y + add``(HALCON ``scale_y_funct_1d``)。 · 示例: 无
- `tb_sensor_capture` `rgbimage → rgbimage` GPU: 无 — 辐射亮度 → 真实传感器输出（散粒噪声、读出噪声、饱和、量化）。 · 示例: 无
- `tb_shape_perturb` `points → points` GPU: 无 — 对形状施加 1 个**已知的**变形。→ ``(N, 3)``。 · 示例: 无
- `tb_smooth_funct_1d_gauss` `signal → signal` GPU: 仅在链中(许可列表) — 对一维函数进行高斯平滑(HALCON ``smooth_funct_1d_gauss``)。 · 示例: 无
- `tb_smooth_funct_1d_mean` `signal → signal` GPU: 仅在链中(许可列表) — 迭代式移动平均平滑(HALCON ``smooth_funct_1d_mean``)。 · 示例: 无
- `tb_spad_deadtime_apply` `counts → counts` GPU: 无 — 用探测器的死时间使真实光子速率发生畸变（计数丢失）。 · 示例: 无
- `tb_spad_deadtime_correct` `counts → counts` GPU: 仅在链中(许可列表) — 从受死时间畸变的测量速率中还原真实光子速率。 · 示例: 无
- `tb_spectrogram` `signal → image` GPU: 无 — STFT 幅度谱图 -> ``(freqs, times, S)``,其中 ``S`` 的形状为 ``(n_freqs, n_frames)``。使用汉宁窗(Hann window);*hop* 默认值为 ``win//2``。 · 示例: 无
- `tb_specular_coefficient_map` `rgbimage → image` GPU: 有(许可列表) — 双色反射模型中的标量界面（镜面）系数。→ (H, W)。 · 示例: 无
- `tb_specular_diffuse_split` `rgbimage → rgbimage` GPU: 有(许可列表) — 将线性 RGB 图像分离为漫反射（体色）和镜面反射（界面）两部分。→ (diffuse, specular)，均为 (H, W, 3)。 · 示例: 无
- `tb_specular_free_transform` `rgbimage → rgbimage` GPU: 仅在链中(许可列表) — 投影去除光源方向：图像中高光无法触及的部分。→ (H, W, 3)。 · 示例: 无
- `tb_sphere_sdf` `points → volume` GPU: 无 — 球体的有符号距离场: ``|p - center| - R``(内部为负,外部为正)。 · 示例: 无
- `tb_stat_correlation` `matrix → matrix` GPU: 无 — Pearson 相关系数矩阵，输入 ``(N, D)`` 观测 → 输出 ``(D, D)``。 · 示例: 无
- `tb_stat_covariance` `matrix → matrix` GPU: 无 — ``(N, D)`` 观测数据的样本协方差矩阵 → ``(D, D)``。 · 示例: 无
- `tb_stat_zscore` `signal → signal` GPU: 仅在链中(许可列表) — 对一维样本做标准化：``(x - mean) / std``（总体标准差，``ddof=0``）。 · 示例: 无
- `tb_statistical_outlier_removal` `points → points` GPU: 无 — 去除各点的 k 近邻平均距离在全局上偏离过大的点（统计离群点去除）。 · 示例: 无
- `tb_superquadric_residual` `points → feature` GPU: 无 — Gross-Boult 体积修正残差：mean( (sqrt(a1 a2 a3)(F^eps1 - 1))^2 )。 · 示例: 无
- `tb_synthesize_silhouette` `points → image` GPU: 无 — 将 3-D 点云投影到 (K,R,t) 相机上，返回被占据像素为 True 的轮廓图（H,W bool）。 · 示例: 无
- `tb_tcspc_background_subtract` `counts → counts` GPU: 无 — 从到达时间直方图中去除环境光/暗计数本底。 · 示例: 无
- `tb_tcspc_coates_correct` `counts → counts` GPU: 无 — 精确消除 TCSPC 堆积效应（Coates 估计量）——早到光子偏差。 · 示例: 无
- `tb_tcspc_irf_convolve` `counts → counts` GPU: 无 — 用仪器响应（时序抖动）对到达时间直方图进行模糊处理。 · 示例: 无
- `tb_temporal_band_power` `video → image` GPU: 有(许可列表) — 每个像素在某个时域频带内的均方功率 -> ``(H, W)`` 图。 · 示例: 无
- `tb_temporal_bandpass` `video → video` GPU: 有(许可列表) — 对每个像素的时间序列进行理想时域带通滤波 -> ``(T, H, W)``。 · 示例: 无
- `tb_temporal_bilateral` `video → video` GPU: 有(许可列表) — 逐帧因果时域双边降噪 → ``(T, H, W)``（``video``）。 · 示例: 无
- `tb_temporal_median_window` `video → video` GPU: 有(许可列表) — 对最近 *window* 帧逐像素取因果中值 → ``(T, H, W)``（``video``）。 · 示例: 无
- `tb_three_frame_difference` `video → video` GPU: 无 — 逐帧 Collins 三帧差分运动掩膜 → 0/1 ``(T, H, W)``（``video``）。 · 示例: 无
- `tb_torus_sdf` `points → volume` GPU: 无 — 圆环面(甜甜圈形)的**精确**有符号距离场(内侧为负、外侧为正)。 · 示例: 无
- `tb_viewport_from_equirect` `rgbimage → rgbimage` GPU: 无 — 从等距柱状图提取透视视口。 · 示例: 无
- `tb_voxel_grid_downsample` `points → points` GPU: 无 — 用边长为 voxel_size 的格子对点云进行抽稀，将每个格子聚合为一个重心点（确定性算法）。 · 示例: 无
- `tb_weighting_response` `signal → signal` GPU: 有(许可列表) — 在给定频率处的 A / C / Z 频率计权曲线，单位为 dB。 · 示例: 无
- `tb_wetness` `rgbimage → rgbimage` GPU: 有(许可列表) — 湿润表面的基底色。**漫反射变暗**（同时镜面反射增加）。 · 示例: 无
- `tb_zero_crossing_rate` `signal → feature` GPU: 无 — 相邻采样点中符号发生变化的比例——一种低成本的音高/噪声程度线索。 · 示例: 无
- `tb_zero_crossings_funct_1d` `signal → signal` GPU: 无 — 函数符号发生变化处的索引(HALCON ``zero_crossings_funct_1d``)。 · 示例: 无

#### 2d / xldgeom (10)
- `xg_area_center` (halcon: `area_center_points_xld`) `contour → feature` GPU: 无 — 用鞋带公式求 contour 的多边形面积(绝对值求和)。 · 示例: `gallery2d_geometry`
- `xg_clip_contours` `contour → contour` GPU: 无 — 丢弃折线长度低于 a × 最长的 contour(a 在 [0,1])。 · 示例: `gallery2d_geometry`
- `xg_crop_contours` `contour → contour` GPU: 无 — 只保留位于形状中央 a 比例窗口内的 contour 点。 · 示例: `gallery2d_geometry`
- `xg_eccentricity` (halcon: `eccentricity_points_xld`) `contour → feature` GPU: 无 — 由点集协方差求离心率 sqrt(1 - λ_min/λ_max)。 · 示例: `gallery2d_geometry`
- `xg_elliptic_axis` (halcon: `elliptic_axis_points_xld`) `contour → feature` GPU: 无 — 点集的长轴/短轴比 sqrt(λ_max/λ_min)。 · 示例: `gallery2d_geometry`
- `xg_gen_polygons` (halcon: `gen_polygons_xld`) `contour → contour` GPU: 无 — Douglas-Peucker 折线简化;eps = a × contour 外接矩形对角线。 · 示例: `gallery2d_geometry`
- `xg_height_width_ratio` (halcon: `height_width_ratio_xld`) `contour → feature` GPU: 无 — 点集轴对齐外接矩形的 高/宽 比。 · 示例: `gallery2d_geometry`
- `xg_moments` (halcon: `moments_points_xld`) `contour → feature` GPU: 无 — 点集的归一化二阶中心矩:mu20 + mu02。 · 示例: `gallery2d_geometry`
- `xg_orientation` (halcon: `orientation_points_xld`) `contour → feature` GPU: 无 — 主轴方向 [度],折叠到 [0,180) 并除以 180。 · 示例: `gallery2d_geometry`
- `xg_regress_contours` `contour → feature` GPU: 无 — 全最小二乘直线残差 RMS = sqrt(协方差较小的特征值)。 · 示例: `gallery2d_geometry`, `poc_screw_thread_metrology`

### 3d (377 ops / 68 categories)

点云、体数据、网格与深度的 op(`ops3d.OPS3D`)。作为函数调用。

#### 3d / annotate3d (7)
- `annotate3d_arrow` `image2d → image2d` GPU: 有(许可列表) — 返回图像(image2d):画出从 3-D ``p0`` 到 ``p1`` 的投影箭头。 · 示例: `annotate3d_figure`
- `annotate3d_axes` `image2d → image2d` GPU: 有(许可列表) — 返回图像(image2d):从 ``origin`` 投影绘制 object 坐标(``pose`` 的输入侧)的三轴(gnomon)。 · 示例: `annotate3d_figure`
- `annotate3d_bbox` `image2d → image2d` GPU: 有(许可列表) — 返回图像(image2d):投影绘制轴对齐 3-D 盒 ``((xmin,ymin,zmin),(xmax,ymax,zmax))`` 的 12 条棱。 · 示例: `annotate3d_figure`
- `annotate3d_label` `image2d × text → image2d` GPU: 有(许可列表) — 返回图像(image2d):给 3-D 锚点加上带引出线的文字。 · 示例: `annotate3d_figure`
- `annotate3d_measure` `image2d → image2d` GPU: 有(许可列表) — 返回图像(image2d):用投影的线与数值标出 3-D 两点间距离(网格单位)。 · 示例: `annotate3d_figure`
- `annotate3d_project` `points → table` GPU: 无 — 返回表(dict):3-D 点的像素坐标、前向距离,以及在画面内/被遮挡的判定(:func:`project_anchors`)。 · 示例: `annotate3d_figure`
- `annotate3d_scale_bar` `image2d → image2d` GPU: 有(许可列表) — 返回图像(image2d):把网格单位下长度为 ``length`` 的比例尺贴在面上并投影。 · 示例: `annotate3d_figure`

#### 3d / augment (6)
- `cutout` `points → points` GPU: 无 — 去除空间中一个轴对齐盒区域,返回 ``(kept, kept_idx)``(模拟局部缺失)。 · 示例: `sensor_seg`
- `elastic_deform` `points → points` GPU: 无 — 用平滑随机位移场做弹性形变(相关长度 ``sigma``,RMS 幅度 ``alpha``)。 · 示例: `sensor_seg`
- `jitter` `points → points` GPU: 无 — 给每个点加各向同性高斯噪声 ``N(0, sigma)``(模拟传感器位置噪声)。 · 示例: `augment_pointcloud`
- `random_dropout` `points → points` GPU: 无 — 随机移除 ``ratio`` 比例的点,返回 ``(kept, kept_idx)``(模拟缺失)。 · 示例: `augment_pointcloud`
- `random_rotation` `points → points` GPU: 无 — 施加随机旋转并返回 ``(rotated, R)``(模拟视点变化)。 · 示例: `augment_pointcloud`, `sh_descriptor_retrieval`, `shape_retrieval`
- `random_scale` `points → points` GPU: 无 — 绕原点施加均匀缩放 ``s ~ U(lo, hi)`` 并返回 ``(scaled, s)``。 · 示例: `augment_pointcloud`

#### 3d / boundary (2)
- `vol_boundary` `voxel → voxel` GPU: 仅在链中(许可列表) — 二值体的边界壳(3-D 版 ``region_boundary``)。 · 示例: `roi_domain_boundary`
- `vol_boundary_points` `voxel → points` GPU: 有(许可列表) — 把边界壳作为 ``(z, y, x)`` 顺序的 ``(N, 3)`` 点云。 · 示例: `roi_domain_boundary`

#### 3d / bounds (4)
- `aabb` `points → primitive` GPU: 无 — 轴对齐包围盒。返回 ``(min (3,), max (3,))``。 · 示例: `hull_bounds`
- `convex_hull` `points → mesh` GPU: 无 — 点集的凸包 -> ``(V, F)``,三角形朝外定向。 · 示例: `hull_bounds`
- `min_enclosing_sphere` `points → primitive` GPU: 无 — 点群 (N,3) → 包含全部点的(近似)最小包围球 {center(3), radius}。 · 示例: `hull_bounds`
- `obb` `points → primitive` GPU: 无 — 用 PCA 求有向包围盒。 · 示例: `hull_bounds`

#### 3d / bundle_adjust (3)
- `bundle_adjust` `pose × points → table` GPU: 无 — 以重投影误差最小同时优化相机位姿与 3D 点。→ dict{cameras, points, rmse, cost}。 · 示例: `bundle_adjust`
- `mean_reprojection_error` `pose × points → measurement` GPU: 无 — 返回光束法平差全部观测的重投影误差 RMS(像素)。 · 示例: `bundle_adjust`
- `project` `points → keypoints` GPU: 无 — 用相机 (rvec,t,K) 把 3D 点 (n,3) 投影到 2D (n,2)(透视除法)。 · 示例: `bundle_adjust`

#### 3d / curvature (5)
- `estimate_normals` `points → normals` GPU: 无 — 统一朝外(远离邻域重心)的点云法线。→ (N,3)。 · 示例: `cylinder_axis_metrology`, `feature_register`, `oriented_normals`
- `gaussian_curvature` `points → signal` GPU: 无 — 高斯曲率 K=k1·k2(对法线反向不变)。→ (N,)。 · 示例: `curvature_grasp`, `curvature_shape_index`
- `mean_curvature` `points → signal` GPU: 无 — 平均曲率 H=(k1+k2)/2。→ (N,)。依赖朝向的量。 · 示例: `curvature_shape_index`, `minimal_surfaces`
- `principal_curvatures` `points → curvature` GPU: 无 — 各点的主曲率 (k1>=k2)。→ (k1 (N,), k2 (N,))。 · 示例: `curvature_grasp`, `itokawa_curvature`, `minimal_surfaces`
- `shape_index` `points → descriptor` GPU: 无 — Koenderink 的 shape index s∈[-1,1] (凸球+1、圆柱+0.5、鞍点0、凹球-1)。→ (N,)。 · 示例: `curvature_grasp`, `itokawa_curvature`

#### 3d / curve (5)
- `arc_length` `points → measurement` GPU: 无 — 曲线的累积弧长与总长。→ (cumulative (N,), total float)。 · 示例: `space_curve`, `torus_knot_curve`
- `curvature_torsion` `points → pairs` GPU: 无 — 各点的曲率 κ 与挠率 τ(与重参数化无关的闭式)。→ (kappa (N,), tau (N,))。 · 示例: `space_curve`, `torus_knot_curve`
- `fit_spline_curve` `points → points` GPU: 无 — 用 B 样条平滑并重采样有序 3D 点列。→ (M,3)。用于平滑带噪的轨迹/边缘。 · 示例: `bspline_freeform`
- `frenet_frame` `points → frame` GPU: 无 — 各点的 Frenet 标架(切线 T,主法线 N,副法线 B)。→ (T, N, B),各为 (Npts,3) 单位向量。 · 示例: `space_curve`, `torus_knot_curve`
- `resample_uniform` `points → points` GPU: 无 — 按弧长等间隔重采样为 n 点(线性插值)。→ (n,3)。 · 示例: `bspline_freeform`

#### 3d / curvilinear (3)
- `cylinder_unwrap` `voxel → voxel` GPU: 有(许可列表) — 把体素的圆柱面展开为 (height×θ×r)(圆柱零件/管道的内外壁检测)。轴 = z(D 轴)。 · 示例: `curvilinear_proj`
- `fit_zernike` `image2d → table` GPU: 无 — 圆盘图像 → Zernike 系数(光学/波前计量的**极坐标曲面拟合**)。返回 {(n,m): coef}。 · 示例: `curvilinear_proj`
- `polar_unwrap` `image2d → image2d` GPU: 无 — 把图像的圆环/圆盘展开为 (θ×r) 矩形(工业:标签/环/回转体检测)。 · 示例: `curvilinear_proj`

#### 3d / deform (4)
- `register_cpd_rigid` `points × points → pose` GPU: 无 — 用 Coherent Point Drift(CPD)刚体版以 EM 估计旋转+平移。 · 示例: `motion_scene`
- `register_nonrigid` `points × points → points` GPU: 无 — 用非刚体 ICP 把 ``src`` 靠向 ``dst``。 · 示例: `nonrigid_deform`
- `tps_fit` `points × points → deformation` GPU: 无 — 由控制点对应拟合 3D Thin-Plate-Spline。 · 示例: `nonrigid_deform`
- `tps_warp` `deformation × points → points` GPU: 无 — 把 ``tps_fit`` 拟合的薄板样条(TPS)变形施加到点群上。 · 示例: `nonrigid_deform`

#### 3d / depth_denoise (3)
- `bilateral_filter_depth` `depth → depth` GPU: 有(许可列表) — 深度图像的双边滤波(保边去噪)。→ float64 (H,W)。 · 示例: `depth_denoise`
- `fill_holes` `depth → depth` GPU: 无 — 用调和(拉普拉斯)松弛由邻近有效像素插补无效像素(空洞)。→ float64 (H,W)。 · 示例: `depth_denoise`
- `joint_bilateral` `depth × image2d → depth` GPU: 有(许可列表) — joint / cross bilateral:被平滑的是 depth,而 range 权重由 guide 的差值给出。→ float64 (H,W)。 · 示例: `sensor_seg`

#### 3d / describe (2)
- `match_sh_descriptor` `voxel × voxel → measurement` GPU: 无 — 两个 SH 描述子的余弦相似度(旋转不变的形状比对)。越接近 1 形状越相似。voxel × SH 列。 · 示例: `sh_descriptor_retrieval`, `shape_descriptor`
- `sh_descriptor` `voxel → descriptor` GPU: 无 — 球谐描述子。以 (半径 × 频率) 返回同心球壳的 SH 频带能量 ‖f_l(r)‖。 · 示例: `sh_descriptor_retrieval`, `shape_descriptor`

#### 3d / detect (2)
- `hough_plane_3d` `voxel → primitive` GPU: native(device 参数) — 平面检测(2D Hough 直线的 3D 提升)。以梯度=法线,向 (法线 n, 距离 d) 空间投票。 · 示例: `detect_primitives_3d`
- `hough_sphere_3d` `voxel → primitive` GPU: 无 — 球检测(2D Hough 圆的 3D 提升)。对每个半径 r,投票中心 = p + sgn·r·n。 · 示例: `detect_primitives_3d`

#### 3d / domain (5)
- `vol_bounding_box` `voxel → primitive` GPU: 无 — 掩码前景的紧致轴对齐包围盒,以体素索引给出。 · 示例: `rle_region_efficiency`, `roi_domain_boundary`
- `vol_crop_domain` `voxel → voxel` GPU: 无 — 把体裁剪到 domain 的紧致包围盒(HALCON ``crop_domain``)。 · 示例: `roi_domain_boundary`
- `vol_reduce_domain` `voxel × voxel → voxel` GPU: 无 — 把体限制在 *domain* 掩码内(HALCON ``reduce_domain``,逐体素)。 · 示例: `roi_domain_boundary`
- `vol_tiled_map` `voxel → voxel` GPU: 仅在链中(许可列表) — 把形状不变的体算子分成重叠 z 板块施加,以压低峰值占用。 · 示例: `rle_region_efficiency`
- `vol_uncrop` `voxel → voxel` GPU: 无 — 把裁出的子体贴回完整框内(``vol_crop_domain`` 的逆)。 · 示例: `roi_domain_boundary`

#### 3d / edges (5)
- `canny3d` `voxel → voxel` GPU: 无 — 3D Canny 边缘检测(非极大值抑制 + 滞后阈值)。 · 示例: `edges_3d`
- `edge_points` `voxel → points` GPU: 仅在链中(许可列表) — 把边缘 mask 变成 (M,3) 的坐标点群(供下游 chamfer / Hough 使用)。 · 示例: `edges_3d`
- `gradient3d` `voxel → gradient` GPU: 有(许可列表) — 先对体数据做高斯平滑,再用中心差分求 3-D 梯度(大小与向量)。 · 示例: `edges_3d`
- `link_edges` `voxel → voxel` GPU: 无 — 用 26 邻域把边缘 mask 标记为连通成分。 · 示例: `sensor_seg`
- `log_zero_crossings` `voxel → voxel` GPU: 有(许可列表) — Laplacian-of-Gaussian 的零交叉边缘。 · 示例: `edges_3d`

#### 3d / feature (15)
- `curvature_maps` `voxel → curvature` GPU: native(device 参数) — level-set 的主曲率 → 形状指数 S(Koenderink)与弯曲度。闭式(Kindlmann 2003)。 · 示例: `diff_features`
- `edt_jfa` `voxel → sdf` GPU: native(device 参数) — 3D 欧氏距离变换 = Jump Flooding Algorithm(GPU)。每个体素 → 到最近 seed 的距离。 · 示例: `diff_features`
- `edt_jfa_vector` `voxel → flow_dense` GPU: native(device 参数) — 用 **GPU 的 JFA** 求每个 voxel 到最近 seed 的位移 ``(3, D, H, W)``(``flow_dense``，dz, dy, dx [voxel])。 · 示例: `nearest_seed_partition`
- `hessian3d` `voxel → hessian` GPU: native(device 参数) — 3D Hessian 的 6 个独立分量 (fzz,fyy,fxx,fzy,fzx,fyx)。可分离 conv3d(二阶/一阶×平滑)。 · 示例: `diff_features`
- `sobel3d` `voxel → gradient` GPU: native(device 参数，仅在链中) — 3D 梯度 (gz,gy,gx)。导数[-1,0,1]×平滑[1,2,1] 的可分离 conv3d。 · 示例: `diff_features`
- `vol_euler_number` `voxel → measurement` GPU: 无 — 二值体的欧拉示性数,并拆分为三个贝蒂数(物体、贯通孔、闭孔)。 · 示例: `ct_porosity_and_fibre_morphometry`
- `vol_frangi` `voxel → voxel` GPU: 有(许可列表) — 3-D Frangi 血管度 —— 多尺度管状结构增强。 · 示例: `vessel_metrology`, `volume_downsampling`
- `vol_gradient_magnitude` `voxel → voxel` GPU: 有(许可列表) — 3-D Sobel 梯度幅值 ``sqrt(gz**2 + gy**2 + gx**2)``。 · 示例: `vessel_metrology`
- `vol_granulometry` `voxel → measurement` GPU: 无 — 二值体的孔径、粒径**分布**(来自开运算序列)。 · 示例: `ct_porosity_and_fibre_morphometry`
- `vol_hessian_blobness` `voxel → voxel` GPU: 有(许可列表) — 由某 *scale* 下 Hessian 特征值得到的团块(球状)响应。 · 示例: `vessel_metrology`
- `vol_local_maxima` `voxel → points` GPU: 有(许可列表) — 3-D 局部极大(峰)检测。 · 示例: `molecule_atom_count`, `vessel_metrology`
- `vol_local_std` `voxel → voxel` GPU: 有(许可列表) — 立方窗口内的局部标准差(无偏)。 · 示例: `ct_porosity_and_fibre_morphometry`
- `vol_local_thickness` `voxel → voxel` GPU: 无 — 局部厚度图 —— 能覆盖每个体素的最大球的直径。 · 示例: `ct_porosity_and_fibre_morphometry`
- `vol_orientation_coherence` `voxel → voxel` GPU: 无 — 局部结构在多大程度上指向**同一方向**(3-D 结构张量)。 · 示例: `ct_porosity_and_fibre_morphometry`
- `vol_sato` `voxel → voxel` GPU: 有(许可列表) — 3-D Sato 管状度 —— 只用两个特征值的更简线状滤波。 · 示例: `vessel_metrology`

#### 3d / feature_register (7)
- `compute_fpfh` `points × normals → descriptor` GPU: 无 — 计算 FPFH 描述子 (N, 3*n_bins)(Rusu 2009)。 · 示例: `fpfh_correspondence`
- `harris3d_keypoints` `voxel → keypoints` GPU: native(device 参数) — 3D Harris 关键点检测(2D Harris 角点检测的 3D 版)。 · 示例: `feature_register`
- `iss_keypoints` `points → indices` GPU: 无 — ISS(Intrinsic Shape Signatures,相当于 3D Harris)关键点检测。 · 示例: `feature_register`
- `register_fpfh` `points × points → pose` GPU: 无 — 用 FPFH 描述子 + RANSAC 做 **无需初值** 的刚体配准 (R,t)。 · 示例: `feature_register`
- `register_shot` `points × points → pose` GPU: 无 — SHOT 描述子的稀疏特征匹配 + RANSAC 刚体位姿估计(完整流水线)。 · 示例: `feature_register`
- `register_spin` `points × points → pose` GPU: 无 — 用 Spin Image 描述子 + RANSAC 的无初值稀疏特征刚体配准。 · 示例: `feature_register`
- `shot_descriptor` `points × normals → descriptor` GPU: 无 — SHOT 描述子(Tombari 2010)。在每个关键点建立 LRF,取球形支撑域。 · 示例: `feature_register`

#### 3d / freeform (5)
- `eval_bspline_curve` `bspline_curve → points` GPU: 无 — 在参数 u∈[0,1] 上等间隔 n 点评估曲线 tck(splev)。 · 示例: `bspline_freeform`
- `eval_bspline_surface` `bspline_surface × image2d × image2d → image2d` GPU: 无 — 评估已拟合的曲面 tck(bisplev)。两种模式:散点(默认)或网格。 · 示例: `bspline_freeform`
- `fit_bspline_curve` `points → bspline_curve` GPU: 无 — 对有序点列 (M,D) 拟合 B 样条曲线(splprep,参数化)。 · 示例: `bspline_freeform`
- `fit_bspline_surface` `image2d × image2d × image2d → bspline_surface` GPU: 无 — 对散布 (x, y, z) 最小二乘拟合双三次(默认)B 样条曲面(bisplrep)。 · 示例: `bspline_freeform`
- `surface_residual` `image2d × image2d × image2d × bspline_surface → measurement` GPU: 无 — 返回散布数据与曲面 tck 的残差统计(形状误差=相对拟合的偏离)。 · 示例: `bspline_freeform`

#### 3d / frequency (3)
- `vol_fft_bandpass` `voxel → voxel` GPU: 仅在链中(许可列表) — 高斯带通 ``lowpass(high) - lowpass(low)``:保留两个尺度之间的结构。 · 示例: `deconv_fft_restore`
- `vol_fft_highpass` `voxel → voxel` GPU: 有(许可列表) — 高斯高通 —— ``1 - lowpass`` 的精确补(两者相加还原)。 · 示例: `deconv_fft_restore`
- `vol_fft_lowpass` `voxel → voxel` GPU: 有(许可列表) — 高斯低通:保留比 ``1/cutoff`` 更粗的结构(体素单位或实际尺寸)。 · 示例: `deconv_fft_restore`

#### 3d / fusion (2)
- `fuse_to_voxel` `any → voxel` GPU: 无 — 把多种结构融合到共同的密度体素(TRIZ 集成)。items=[(data,kind,params_dict), ...]。 · 示例: `transforms_repr`
- `register_cross` `any × any → pose` GPU: 无 — 异构结构间的刚体配准。二者转为点云 → 配准器(fpfh=大旋转 / icp=需 coarse init)。 · 示例: `transforms_repr`

#### 3d / geodesic (4)
- `farthest_point_sampling` `points → indices` GPU: 无 — 按测地距离的最远点采样(均匀抽稀)。→ 选中索引序列 (n,) int。 · 示例: `geodesic_distance`, `pointcloud_downsampling`
- `geodesic_distances` `points → signal` GPU: 无 — 从 source 到全部点的测地距离(kNN 图上 Dijkstra)。→ (N,) float(不可达为 inf)。 · 示例: `geodesic_distance`
- `geodesic_mesh` `mesh → signal` GPU: 无 — 在三角网格的边图上用 Dijkstra 求从 source 到各顶点的测地距离。→ (V,) float。 · 示例: `pcl_geodesic`
- `knn_graph` `points → graph` GPU: 无 — 每点的 k 近邻索引与欧氏距离(不含自身)。→ (idx (N,k) int, dist (N,k) float)。 · 示例: `pcl_geodesic`

#### 3d / geom_transform (3)
- `vol_affine` `voxel → voxel` GPU: 无 — 通用仿射重采样(``scipy.ndimage.affine_transform``)。 · 示例: `vol_geometry_transform`
- `vol_resize` `voxel → voxel` GPU: 无 — 把体重采样到新网格(``scipy.ndimage.zoom``,cell 语义)。 · 示例: `vol_geometry_transform`
- `vol_rotate` `voxel → voxel` GPU: 仅在链中(许可列表) — 在一对轴张成的平面内旋转体(``scipy.ndimage.rotate``)。 · 示例: `vol_geometry_transform`

#### 3d / geometry (25)
- `angle_3points` `points → measurement` GPU: 无 — 三点所成角(顶点 b,度)。∠ABC。 · 示例: `geometry_metrology`
- `angle_between_lines` `primitive → measurement` GPU: 无 — 返回两条直线方向向量所成的锐角(度,不区分方向,0〜90°)。 · 示例: `geometry_metrology`
- `angle_between_planes` `primitive → measurement` GPU: 无 — 两平面的二面角(法线 n1,n2;度)。 · 示例: `geometry_metrology`
- `angle_line_plane` `primitive → measurement` GPU: 无 — 直线(方向 d)与平面(法线 n)之间的角(度)。 · 示例: `geometry_metrology`
- `distance_line_line` `primitive → measurement` GPU: 无 — 两直线间距离(含异面/skew)。平行时退化为点-线距离。 · 示例: `geometry_metrology`
- `distance_point_line` (halcon: `distance_point_line`) `points × primitive → measurement` GPU: 无 — 返回点到直线(通过点与方向)的垂直距离(2-D / 3-D 通用)。 · 示例: `geometry_metrology`
- `distance_point_plane` `points × primitive → measurement` GPU: 无 — 返回点到平面的距离(无符号,单位与输入坐标相同)。 · 示例: `geometry_metrology`
- `distance_segment_segment` `primitive → measurement` GPU: 无 — **有限线段**之间的最短距离及其最近点对。→ ``(distance, cp, cq)``。 · 示例: `geometry_metrology`
- `fit_box3` `points → primitive` GPU: 无 — 用 PCA 拟合有向长方体(快速、抗噪;与 ``pcseg.obb`` 同一构造)。 · 示例: `oriented_bounding_box`
- `fit_circle3` `points → primitive` GPU: 无 — 对 ``(depth, row, col)`` 点做 3-D 圆拟合:先拟合支撑平面,再在面内拟合圆。 · 示例: `primitive_fitting_3d`
- `fit_circle_3d` `points → primitive` GPU: 无 — 点群 → 3D 圆(先平面拟合,再在面内做 2D 圆拟合)。返回 (center, radius, normal)。 · 示例: `geometry_metrology`
- `fit_line3` `points → primitive` GPU: 无 — 对 ``(depth, row, col)`` 点做全最小二乘 3-D 直线拟合。 · 示例: `primitive_fitting_3d`
- `fit_line_3d` `points → primitive` GPU: 无 — 点群 → 最小二乘直线(过重心,方向=最大主轴)。返回 (point, direction)。 · 示例: `geometry_metrology`
- `fit_plane3` `points → primitive` GPU: 无 — 对 ``(depth, row, col)`` 点做最小二乘 3-D 平面拟合。 · 示例: `primitive_fitting_3d`
- `fit_plane_3d` `points → primitive` GPU: 无 — 点群 → 最小二乘平面(过重心,法线=最小主轴,残差 RMS)。返回 (point, normal, resid)。 · 示例: `geometry_metrology`
- `fit_sphere3` `points → primitive` GPU: 无 — 对 ``(depth, row, col)`` 点做代数(Kåsa)最小二乘球拟合。 · 示例: `primitive_fitting_3d`, `roi_domain_boundary`
- `fit_sphere_3d` `points → primitive` GPU: 无 — 点群 → 最小二乘球(代数拟合)。返回 (center, radius)。用于管道/球体计量。 · 示例: `geometry_metrology`
- `fit_surface_principal_axes` `points → table` GPU: 无 — 将倾斜翘曲面旋转到 PCA 轴后拟合多项式 z'=f(x',y')。 · 示例: `primitive_fitting_3d`
- `intersect_line_plane` `primitive → position` GPU: 无 — 直线 ∩ 平面 → 点(平行时为 None)。 · 示例: `geometry_metrology`
- `intersect_planes` `primitive → primitive` GPU: 无 — 平面 ∩ 平面 → 直线(通过点, 方向)。平行时为 None。 · 示例: `geometry_metrology`
- `line_from_2points` `points → primitive` GPU: 无 — 两点 → 直线(通过点, 单位方向)。两个坐标即可确定直线(2D/3D 通用)。 · 示例: `geometry_metrology`
- `plane_from_3points` `points → primitive` GPU: 无 — 3 点 → 平面(通过点, 单位法线)。三个坐标即可确定平面(2D/3D 通用)。 · 示例: `geometry_metrology`
- `smallest_box3` `points → primitive` GPU: 无 — 近似最小体积的有向包围盒(3-D 版 ``smallest_rectangle2``)。 · 示例: `oriented_bounding_box`
- `smallest_box3_axis` `points → primitive` GPU: 无 — 轴对齐包围盒(3-D 版 ``smallest_rectangle1``)。 · 示例: `oriented_bounding_box`
- `smallest_sphere3` `points → primitive` GPU: 无 — ``(depth, row, col)`` 点的最小包围球(Welzl 精确解)。 · 示例: `primitive_fitting_3d`

#### 3d / gicp (2)
- `estimate_covariances` `points → descriptor` GPU: 无 — 把每点局部协方差的特征值替换为 (ε,1,1) 的 plane-to-plane 协方差 (N,3,3)。 · 示例: `gicp_register`
- `gicp` `points × points → pose` GPU: 无 — 用 Generalized-ICP(协方差加权马氏 ICP)估计刚体变换 (R,t)。 · 示例: `gicp_register`

#### 3d / gray (4)
- `vol_equalize` `voxel → voxel` GPU: 仅在链中(许可列表) — 体的直方图均衡(HALCON ``equ_histo_image``)。 · 示例: `gray_window_level`
- `vol_gamma` `voxel → voxel` GPU: 有(许可列表) — 在体自身值域上的伽马(幂律)校正(HALCON ``pow_image``)。 · 示例: `gray_window_level`
- `vol_stretch` `voxel → voxel` GPU: 无 — 按分位数把对比度拉伸到 ``[0, 1]``(稳健版 ``scale_image_max``)。 · 示例: `gray_window_level`
- `vol_window_level` `voxel → voxel` GPU: 仅在链中(许可列表) — CT 窗宽/窗位(HU 窗)—— 放射科医生每天用的线性重映射。 · 示例: `gray_window_level`

#### 3d / lidar_projection (3)
- `project_cylindrical` `points → image2d` GPU: 无 — 投影到圆柱距离图像 (z_bins, h_res)。方位角(列)× z(行),像素=水平半径 ρ=hypot(x,y)。 · 示例: `curvilinear_proj`
- `project_spherical` `points → image2d` GPU: 无 — 投影到旋转式 LiDAR 的球面距离图像 (v_res, h_res)。空格=0,近点优先(最小 range)。 · 示例: `lidar_projection`
- `unproject_spherical` `image2d → points` GPU: 有(许可列表) — 球面距离图像 → 3D 点 (M, 3)。只对 range>0 的格按 bin 中心角反投影。 · 示例: `lidar_projection`

#### 3d / match_localize (6)
- `match_chamfer_3d` `voxel × voxel → position` GPU: 无 — chamfer / 距离场匹配(对部分可见与遮挡稳健)。voxel × chamfer 列。 · 示例: `matching_localize`
- `match_curvature_3d` `voxel × voxel → position` GPU: 无 — 曲率(shape index)匹配。voxel × 曲率列(线→面提升的核心)。 · 示例: `matching_localize`
- `match_hough_3d` `voxel × voxel → position` GPU: 无 — generalized Hough 3D(Ballard R-table 投票)。voxel × Hough 列。 · 示例: `matching_localize`
- `match_mip_2d` `voxel × voxel → position` GPU: 无 — MIP 投影 → 2D NCC(结构=voxel → 2D、方法=NCC、变换=正交 MIP)。 · 示例: `matching_localize`
- `match_points_ncc` `points × points → position` GPU: 无 — 点群间匹配(结构=point cloud × 方法=NCC、变换=splat)。在 scene 中定位 model。 · 示例: `matching_localize`
- `match_shape_3d` `voxel × voxel → position` GPU: 无 — 3D 形状(梯度方向)匹配 = 2D shapematch_gpu 的 voxel 版(「轮廓匹配」)。 · 示例: `matching_localize`

#### 3d / match_pose (5)
- `find_surface_pose` `points × points → pose` GPU: 无 — 通过点对特征（PPF）投票和 ICP，求出已知物体（模型点云）在场景点云中的位置（``pose``）。 · 示例: `find_surface_pose_bracket`
- `match_logpolar_z` `voxel × voxel → rot_scale` GPU: 无 — 用 log-polar × 相位相关(Fourier-Mellin)恢复 **绕 z 旋转 + 各向同性缩放**。 · 示例: `shape_desc_pose`
- `match_pca` `points × points → pose` GPU: 无 — PCA 位姿匹配(结构=point cloud × 方法=主轴对齐)。 · 示例: `shape_desc_pose`
- `match_phase_3d` `voxel × voxel → shift` GPU: 无 — 3D 相位相关(FFT)。返回把 b 对齐到 a 的整数位移 (dz,dy,dx)。 · 示例: `shape_desc_pose`
- `moment_axes` `points → axes` GPU: 无 — 点群/加权点的 **重心 + 主轴**(惯性张量的特征向量)。位姿估计的基础。 · 示例: `itokawa_pose_canonical`

#### 3d / medial (13)
- `distance_ridge` `voxel → voxel` GPU: 有(许可列表) — 把 EDT 的脊(距离场的局部极大)提取为中轴。返回 (ridge_mask, edt)。 · 示例: `pcl_geodesic`
- `medial_axis_points` `voxel → points` GPU: 有(许可列表) — 把 medial 体素的坐标与局部半径(= 该点的 EDT 值)变成点群。返回 (points, radius)。 · 示例: `medial_topology`
- `medial_match` `voxel × voxel → measurement` GPU: 无 — 基于 medial(拓扑 + 半径分布)对两个体素形状的粗匹配得分。返回 [0,1]。 · 示例: `medial_topology`
- `skeleton_branches3d` `voxel → voxel` GPU: 无 — 把 3D 骨架在分叉点处切成枝(线段)。2D `r2_split_skeleton_lines` 的 3D 版。 · 示例: `medial_topology`
- `skeleton_endpoints3d` `voxel → voxel` GPU: 无 — 以体素掩码返回 3D 骨架的端点(26 邻域中骨架 voxel 不超过 1 个)。 · 示例: `medial_topology`
- `skeleton_graph3d` `voxel → table` GPU: 无 — 把 3D 骨架组装成**由节点(连接点、端点)和分支(长度、半径)构成的图**。 · 示例: `medial_topology`
- `skeleton_junctions3d` `voxel → voxel` GPU: 无 — 以体素掩码返回 3D 骨架的分叉点(joint,26 邻域中骨架 voxel 不少于 3 个)。 · 示例: `medial_topology`
- `skeleton_prune3d` `voxel → voxel` GPU: 无 — 修剪 3D 骨架的毛刺(短枝)。端点去除迭代 length 次 = 去除枝长 <=length 的枝。 · 示例: `medial_topology`
- `skeletonize_vol` `voxel → voxel` GPU: 无 — 把 3D 二值 voxel 细化为 1 voxel 宽的骨架。skimage 的 Lee(1994)法封装。 · 示例: `medial_topology`
- `topology_signature` `voxel → table` GPU: 无 — 由骨架的 26 邻域度数构造拓扑描述子。返回端点/分叉点/普通点/孤立点的个数。 · 示例: `medial_topology`
- `vol_distance_transform` `voxel → voxel` GPU: 有(许可列表) — 二值体的精确欧氏距离变换。 · 示例: `medial_topology`, `molecule_atom_count`, `nearest_seed_partition`, `vessel_metrology`
- `vol_nearest_label` `voxel → voxel` GPU: 无 — 把**最近的非零标签**分配给零 voxel 的标签体积 ``(D, H, W)``(标签的 Voronoi 划分，``voxel``)。 · 示例: `nearest_seed_partition`
- `vol_nearest_seed_vector` `voxel → flow_dense` GPU: 无 — **每个 voxel 到最近 seed voxel 的位移向量** ``(3, D, H, W)``(``flow_dense``，分量 dz, dy, dx [voxel])。 · 示例: `nearest_seed_partition`

#### 3d / mesh_process (10)
- `boundary_vertices` `mesh → indices` GPU: 无 — 位于开放边缘(边界)上的**顶点 index** → ``(K,)``。 · 示例: `mesh_decimate`, `mesh_props`
- `decimate_qem` `mesh → mesh` GPU: 无 — 面向 *target_faces* 的二次误差度量(QEM)边坍缩简化。 · 示例: `mesh_decimate`, `mesh_lod_download`, `mesh_resolution_demo`
- `face_areas` `mesh → signal` GPU: 无 — 三角形网格**每个面的面积** → ``(M,)``。 · 示例: `mesh_props`
- `face_normals` `mesh → normals` GPU: 无 — 三角网格的**面法线**(每个三角形的单位法向量)。→ (M,3)。 · 示例: `mesh_props`
- `laplacian_smooth` `mesh → mesh` GPU: 无 — 用 umbrella Laplacian 平滑三角网格。→ (verts, faces)。 · 示例: `mesh_smooth`
- `mesh_area` `mesh → measurement` GPU: 无 — 三角网格的**表面积**(全部三角形面积之和)。→ float。 · 示例: `dl_mesh_curvature`, `mesh_props`, `minimal_surfaces`
- `mesh_volume` `mesh → measurement` GPU: 无 — 闭合三角形网格所围的**有符号体积** → float。 · 示例: `hull_bounds`, `mesh_props`, `minimal_surfaces`
- `taubin_smooth` `mesh → mesh` GPU: 无 — Taubin λ|μ 滤波的**非收缩**平滑。→ (verts, faces)。 · 示例: `mesh_smooth`
- `vertex_curvature` `mesh → curvature` GPU: 无 — 三角网格各顶点的**平均曲率大小**(mean curvature magnitude)。→ (N,)。 · 示例: `dl_mesh_curvature`, `mesh_props`, `minimal_surfaces`
- `vertex_normals` `mesh → normals` GPU: 无 — 三角网格的**顶点法线**(按面积加权聚合的单位法线)。→ (N,3)。 · 示例: `mesh_props`

#### 3d / metrics (8)
- `chamfer_distance` `points × points → measurement` GPU: 无 — 对称 Chamfer 距离 = 0.5*(mean_a min_b + mean_b min_a)。→ scalar。越小越吻合。 · 示例: `itokawa_pose_canonical`, `itokawa_shape_match`, `mesh_lod_download`, `metrics_eval`, `poisson_surface_recon`
- `fscore` `points × points → measurement` GPU: 无 — F-score @ tau = precision 与 recall 的调和平均。→ (f, precision, recall)。重建的标准指标。 · 示例: `metrics_eval`
- `hausdorff_distance` `points × points → measurement` GPU: 无 — 对称 Hausdorff 距离 = max(max_a min_b, max_b min_a)。→ scalar。最坏情况的偏离。 · 示例: `mesh_lod_download`, `pointcloud_downsampling`, `poisson_surface_recon`
- `m3c2_distance` `points × points → signal` GPU: 无 — **沿法线方向**测量 2 个时间点点云之间的差异(M3C2)。→ ``(distance, lod)`` 这 2 个值。 · 示例: `metrics_eval`
- `normal_consistency` `points × normals → measurement` GPU: 无 — 最近邻对应下的法线一致度 = mean|cos(na, nb)|(忽略朝向)。→ [0,1]。1=完全一致。 · 示例: `metrics_eval`
- `pose_error` `pose × pose → table` GPU: 无 — 位姿误差 = (旋转角[度], 平移范数)。用于配准结果与 GT 的比较。→ (rot_deg, trans_err)。 · 示例: `itokawa_self_register`
- `rmse_correspondence` `points × points → measurement` GPU: 无 — 对应已知(同 index)的 RMSE = sqrt(mean |a_i - b_i|^2)。→ scalar。评估配准残差。 · 示例: `metrics_eval`
- `voxel_iou` `voxel × voxel → measurement` GPU: 无 — 体素占据的 IoU(intersection over union)。→ [0,1]。体积一致度。 · 示例: `metrics_eval`

#### 3d / moment_invariant (4)
- `central_moments` `points → table` GPU: 无 — 以重心为中心的中心矩 μ_{pqr}(平移不变,键为 (p,q,r))。 · 示例: `moment_invariants`
- `inertia_tensor` `points → matrix` GPU: 无 — 点群的惯性张量 (3,3)(由中心二阶矩,等质量、总质量 1)。 · 示例: `moment_invariants`
- `moment_invariants` `points → descriptor` GPU: 无 — 对平移+旋转+缩放不变的形状特征向量(Sadjadi–Hall 风格 + 高阶径向分布)。 · 示例: `moment_invariants`
- `principal_moments` `points → descriptor` GPU: 无 — 惯性张量的特征值(主惯性矩,降序排列,旋转不变)。 · 示例: `shape_desc_pose`

#### 3d / morphology (7)
- `morph_blackhat3d` `voxel → voxel` GPU: native(device 参数) — 3D black-hat = closing − vol。提取小于 SE 的**暗结构/孔洞**。 · 示例: `diff_features`
- `morph_close3d` `voxel → voxel` GPU: native(device 参数) — 3D closing = dilation → erosion。填补小于 SE 的**暗结构(缝隙、空腔)**。 · 示例: `morphology_3d`
- `morph_dilate3d` `voxel → voxel` GPU: native(device 参数) — 3D 灰度膨胀(SE 半径 r 的局部 max)。使亮区扩张。 · 示例: `morphology_3d`
- `morph_erode3d` `voxel → voxel` GPU: native(device 参数) — 3D 灰度腐蚀(SE 的局部 min)。使亮区收缩。se 与 dilate 相同。 · 示例: `morphology_3d`
- `morph_gradient3d` `voxel → voxel` GPU: native(device 参数) — 3D 形态学梯度 = dilation − erosion。提取**边界/表面**(可替代 sobel 的边缘源)。 · 示例: `morphology_3d`
- `morph_open3d` `voxel → voxel` GPU: native(device 参数) — 3D opening = erosion → dilation。去除小于 SE 的**亮结构(尖刺、颗粒)**。 · 示例: `morphology_3d`
- `morph_tophat3d` `voxel → voxel` GPU: native(device 参数) — 3D white top-hat = vol − opening。提取小于 SE 的 **亮结构**(keypoint 预处理)。 · 示例: `diff_features`, `morphology_3d`

#### 3d / motion (1)
- `scene_flow_lk` `voxel × voxel → flow_dense` GPU: 无 — Lucas-Kanade scene flow(2D 光流的 3D 版)。逐体素的运动场 d=(dz,dy,dx)。 · 示例: `motion_scene`

#### 3d / motion_segment (3)
- `estimate_flow` `points × points → flow_scattered` GPU: 无 — 从 pts0 各点到 pts1 最近邻的 3-D 位移向量场 (N, 3)(最近邻流)。 · 示例: `motion_scene`
- `fit_rigid` `points × points → pose` GPU: 无 — 用闭式 Kabsch 由对应点估计刚体变换 (R, t)(pts_from[i] -> pts_to[i])。 · 示例: `motion_scene`
- `segment_rigid_motions` `points × points → labels` GPU: 无 — 把两个点群按运动一致的刚体分割(迭代 RANSAC 的 multi-body 分割)。 · 示例: `motion_seg`

#### 3d / normals_orient (2)
- `estimate_oriented_normals` `points → normals` GPU: 无 — PCA 法线估计 + Hoppe 全局定向的组合。→ (N,3) 带朝向的单位法线。 · 示例: `oriented_normals`
- `orient_normals` `points × normals → normals` GPU: 无 — 用 Hoppe 法把法线定向为**全局一致**(MST 传播)。→ (N,3)。 · 示例: `oriented_normals`

#### 3d / occupancy (4)
- `esdf` `voxel → sdf` GPU: 有(许可列表) — 占据栅格 → 欧氏符号距离场(ESDF)(外=+ 到最近占据,内=− 到最近自由)。 · 示例: `occupancy_esdf`
- `inflate` `voxel → voxel` GPU: 无 — 把障碍膨胀 ``radius``(世界单位)后的占据栅格 bool(即 ESDF<=radius 视为占据)。 · 示例: `sensor_seg`
- `occupancy_grid` `points → voxel` GPU: 无 — 点云 (N,3) → 三维占据体素栅格,bool(点落入的体素记为占据)。 · 示例: `occupancy_esdf`
- `query_distance` `sdf × points → signal` GPU: 无 — 任意 world 坐标 (M,3) 处的 ESDF 值 (M,)(``mode``='trilinear' 插值或 'nearest')。 · 示例: `occupancy_esdf`

#### 3d / optics (5)
- `fresnel_reflectance` `measurement → measurement` GPU: 无 — Fresnel 反射率(非偏振=s/p 平均)。透明体界面上分成反射/透射的比例。 · 示例: `snell_refraction`
- `normal_from_reflection` `vector × vector → vector` GPU: 无 — 由入射+反射恢复镜面法线(deflectometry)。n ∝ (r − d),朝与入射相反的方向。 · 示例: `sensor_seg`
- `reflect` `vector × normals → normals` GPU: 无 — 把入射方向 d 在法线为 n 的面上镜面反射。r = d − 2(d·n)n。 · 示例: `sensor_seg`, `snell_refraction`
- `refract` `vector × normals → normals` GPU: 无 — Snell 折射(向量形式)。d=入射(朝向面),n=入射侧外法线,折射率 eta1→eta2。 · 示例: `snell_refraction`
- `snell_angle` `measurement → measurement` GPU: 无 — 入射角(度)→ 折射角(度)。n1 sinθi = n2 sinθt。超过临界角为 NaN(全反射)。 · 示例: `snell_refraction`

#### 3d / photometric (4)
- `integrate_normals` `normalmap → image2d` GPU: 无 — 法线场 → 高度场 z,用 Frankot-Chellappa 积分。→ z HxW(常数项自由,以均值 0 为基准)。 · 示例: `photometric_stereo`
- `photometric_stereo` (halcon: `photometric_stereo`) `images → normalmap` GPU: 有(许可列表) — Lambert 光度立体:由已知光源方向的 N 张图恢复法线与反照率。→ (normals HxWx3, albedo HxW)。 · 示例: `photometric_stereo`
- `render_lambertian` `normalmap → image2d` GPU: 无 — 法线 + 反照率 + 光源方向 → Lambert 图像(检测样本生成 / GT 验证 / 逆渲染的正向)。→ HxW。 · 示例: `photometric_stereo`, `render_shade`
- `surface_normals` `image2d → normalmap` GPU: 有(许可列表) — 高度场 z(HxW)→ 单位法线 (H,W,3)。n ∝ (-dz/dx, -dz/dy, 1)。深度→法线的正向变换。 · 示例: `photometric_stereo`

#### 3d / plane_sweep_stereo (2)
- `plane_sweep_depth` `image2d × image2d → depth` GPU: 无 — 用 plane-sweep stereo 估计稠密深度图。→ (H,W) depth。 · 示例: `plane_sweep_depth`
- `warp_by_plane` `image2d → image2d` GPU: 有(许可列表) — 用单应 H 对 img 做逆向 warp。→ out[y,x] = img(H·(x,y,1))(bilinear)。 · 示例: `motion_scene`

#### 3d / polyhedron (1)
- `geodesic_dome` `无输入 → mesh` GPU: 无 — 对正二十面体细分得到的测地球 —— 决定形状的是欧拉公式。 · 示例: `geodesic_dome`

#### 3d / pose_estimation (3)
- `dlt_pose` `points × keypoints → pose` GPU: 无 — 用 DLT 由 3D-2D 对应恢复相机位姿(K 已知)。→ (R (3,3), t (3,))。至少需要 6 点。 · 示例: `pnp_pose_outliers`, `pose_estimation`
- `pnp_ransac` `points × keypoints → pose` GPU: 无 — 对外点稳健的 PnP(RANSAC + 最终 DLT 重拟合)。→ (R, t, inlier_mask, info)。 · 示例: `pnp_pose_outliers`, `pose_estimation`
- `reprojection_error` `points × keypoints → measurement` GPU: 无 — 重投影误差(RMS 像素)。评估位姿的拟合程度。→ scalar。 · 示例: `pnp_pose_outliers`, `pose_estimation`

#### 3d / pose_graph (3)
- `mean_edge_error` `pose → measurement` GPU: 无 — 边残差的 RMS(位姿图的一致程度)。→ scalar。 · 示例: `sfm_recon`
- `optimize_pose_graph` `pose → table` GPU: 无 — 由相对位姿约束 + 回环闭合优化全局位姿。→ dict{poses, rmse, cost}。 · 示例: `pose_graph_slam`
- `relative_pose` `pose × pose → pose` GPU: 无 — T_i⁻¹ ∘ T_j = i←j 的相对位姿。pose_* = [rvec|t] (6,)。→ (rvec_ij (3,), t_ij (3,))。 · 示例: `pose_graph_slam`, `sfm_recon`

#### 3d / preprocess (5)
- `mls_smooth` `points → points` GPU: 无 — 把每个点投影到局部多项式曲面上以去噪(Moving Least Squares 平滑)。 · 示例: `pcl_geodesic`
- `radius_outlier_removal` `points → points` GPU: 无 — 去除半径 radius 内邻居数少于 min_neighbors 的点(孤立点去除)。 · 示例: `pcl_geodesic`
- `statistical_outlier_removal` `points → points` GPU: 无 — 去除 k 近邻平均距离在全局上离群的点(统计离群点去除)。 · 示例: `pcl_geodesic`
- `volume_downsample` `voxel → voxel` GPU: 仅在链中(许可列表) — 按每轴整数 *factor* 对 ``(D, H, W)`` 体做块池化(数据抽稀)。 · 示例: `volume_downsampling`
- `voxel_grid_downsample` `points → points` GPU: 无 — 用边长 voxel_size 的格子抽稀点群,把每个单元聚合为一个重心点(确定性)。 · 示例: `pointcloud_downsampling`

#### 3d / probe (3)
- `vol_edge_probe` `voxel → table` GPU: 无 — 沿探针 ``p0 -> p1`` 以亚采样精度定位边缘。 · 示例: `wall_thickness_probe`
- `vol_profile_line` `voxel → pairs` GPU: 无 — 沿直线探针 ``p0 -> p1`` 的灰度剖面。 · 示例: `wall_thickness_probe`
- `vol_wall_thickness` `voxel → signal` GPU: 无 — 沿探针 ``p0 -> p1`` 的壁厚 —— 工业 CT 计量本身。 · 示例: `wall_thickness_probe`

#### 3d / range_image (4)
- `bearing_angle_image` `depth → image2d` GPU: 有(许可列表) — bearing-angle 图像:沿扫描方向的视线与局部表面所成的角(range image 的经典描述子)。→ HxW(度)。 · 示例: `sensor_seg`
- `depth_to_organized_points` `depth → pointmap` GPU: 仅在链中(许可列表) — organized 深度图 → 网格对齐的 3D 点 (H,W,3)。 · 示例: `range_image`
- `normals_from_depth` `depth → normalmap` GPU: 有(许可列表) — organized 深度 → 带朝向的单位法线 (H,W,3)。相邻像素 3D 点的叉积(利用格点结构,O(HW))。 · 示例: `range_image`
- `occlusion_edges` `depth → image2d` GPU: 无 — 检测深度不连续(前景/背景边界 = 遮挡边缘)。→ bool HxW。 · 示例: `range_image`

#### 3d / reconstruct (4)
- `alpha_shape_boundary` `points → indices` GPU: 无 — 用 alpha shapes 给出**边界点索引**(点群 → 边界点)。 · 示例: `sfm_recon`
- `alpha_shape_mesh` `points → mesh` GPU: 无 — 用 alpha shapes 给出**表面三角网格**(点群 → (vertices, faces))。 · 示例: `alpha_shape_topology`
- `estimate_alpha` `points → measurement` GPU: 无 — 由点群的尺度给出推荐 alpha(基于最近邻距离的中位数)。 · 示例: `alpha_shape_topology`, `sfm_recon`
- `poisson_lite` `points → mesh` GPU: 无 — 点群 (N,3) → (vertices(V,3), faces(F,3)) 的表面网格(screened Poisson 的轻量近似)。 · 示例: `poisson_surface_recon`

#### 3d / refine (6)
- `icp_point2plane` `points × points × normals → pose` GPU: 无 — 用点-面 ICP(Gauss-Newton,小角近似)高精度精化刚体变换。 · 示例: `refinement`
- `icp_point2point_3d` `points × points → pose` GPU: 无 — 用 point-to-point ICP(Kabsch/SVD)精化点群。 · 示例: `gicp_register`, `itokawa_self_register`, `itokawa_shape_match`, `partial_overlap_icp`
- `refine_lm` `voxel × voxel × position → table` GPU: 无 — 用 Levenberg-Marquardt 做平移(+各向同性缩放/亮度增益)的亚体素精化。 · 示例: `refinement`
- `refine_peak_newton` `score × position → position` GPU: 无 — 用 3D Newton 把 score/相关体的整数峰精化到亚体素(迭代优化)。 · 示例: `refinement`
- `refine_rotation_z` `voxel × voxel × angle → angle` GPU: 无 — z 轴旋转角的 **Gauss-Newton 精化**(SSD 上的 Lucas-Kanade,单参数)。 · 示例: `refinement`
- `refine_translation_lk` `voxel × voxel × position → position` GPU: 无 — 用 Gauss-Newton 逆合成 Lucas-Kanade 做 3D 平移的亚体素精化。 · 示例: `refinement`

#### 3d / regionprops (7)
- `filter_by_volume` `voxel → voxel` GPU: 无 — 返回去除了小于 min_voxels 的连通成分后的 bool 掩码。 · 示例: `region_props_3d`
- `inner_box3` `voxel → primitive` GPU: 无 — 完全内接于二值体素区域的最大轴对齐盒(2-D ``inner_rectangle1`` 的 3-D 版)。 · 示例: `inner_box_inspection`
- `label_components` `voxel → labels` GPU: 无 — 把 3D 二值体标记为连通成分。 · 示例: `region_props_3d`, `watershed3d`
- `largest_component` `voxel → voxel` GPU: 无 — 返回最大(体素最多)连通成分的 bool 掩码。 · 示例: `region_props_3d`
- `region_props` `voxel → table` GPU: 无 — 返回各连通成分的区域属性列表。 · 示例: `region_props_3d`
- `vol_label` `voxel → labels` GPU: 仅在链中(许可列表) — 可选邻域的 3-D 连通成分标记。 · 示例: `ct_bone_segmentation`, `molecule_atom_count`, `vessel_metrology`
- `vol_region_props` `labels → table` GPU: 无 — 由标签体给出逐成分的定量描述量。 · 示例: `vessel_metrology`

#### 3d / registration_metrics (4)
- `inlier_ratio` `points × points → measurement` GPU: 无 — 对应集合的内点率 = ‖T·source[i] − target[i]‖ < thresh 的比例。→ [0,1]。 · 示例: `reg_eval`
- `registration_recall` `points × points → measurement` GPU: 无 — 3DMatch 风格的 per-pair 配准成败 = 1.0(成功)/ 0.0(失败)。 · 示例: `reg_eval`
- `rmse_inliers` `points × points → measurement` GPU: 无 — 内点对应(残差 < thresh)上的 RMSE 与内点数。→ (rmse, n_inliers)。 · 示例: `reg_eval`
- `rotation_translation_error` `pose × pose → table` GPU: 无 — 两个 4×4 变换之间的相对旋转误差(测地角[度], RRE)与相对平移误差(RTE)。 · 示例: `reg_eval`

#### 3d / render (19)
- `ambient_occlusion` `mesh → image2d` GPU: 无 — 把网格渲染成 AO 贴图 ``(H, W)``,取值 [0,1]。 · 示例: `render_ao`
- `antialias` `image2d → image2d` GPU: 无 — 按整数倍 ``ss`` 缩小高分辨率图像(面积平均抗锯齿)。 · 示例: `render_ssaa`
- `brdf_hapke` `normalmap → image2d` GPU: 无 — 用 Hapke 反射律(冲效应 + 多次散射 + 宏观粗糙度 θ̄)给法线图着色,返回 I/F ``(H, W)``。 · 示例: `itokawa_regolith_hero`
- `brdf_lommel_seeliger` `normalmap → image2d` GPU: 无 — 用 Lommel-Seeliger 反射律(边缘仍亮的风化层)给法线图着色,返回 I/F ``(H, W)``。 · 示例: `itokawa_regolith_hero`
- `cast_shadow` `mesh × vector → image2d` GPU: 无 — 计算网格的投影 / 软阴影,返回可见性图 (H,W) ∈ [0,1]。 · 示例: `render_beauty`, `render_shadow`
- `edge_alias_energy` `image2d → measurement` GPU: 无 — 边缘的锯齿能量 = 拉普拉斯的 RMS(越小越平滑)。 · 示例: `render_beauty`, `render_ssaa`
- `matcap_shade` `normalmap × image2d → image2d` GPU: 无 — MatCap:把视空间法线映射到 lit-sphere 贴图,转移材质外观。→ ``(H, W[, C])``。 · 示例: `render_shade`
- `phong_shade` `normalmap → image2d` GPU: 无 — 用 Phong 反射模型给法线图着色(环境光 + 漫反射 + **镜面**)。→ ``(H, W)``。 · 示例: `render_beauty`, `render_shade`
- `points_render` `points → rgbimage` GPU: 无 — 把 (N, 3) 点云渲染为 RGB 图像 (H, W, 3):抗锯齿的足迹、按深度排序、结果确定。 · 示例: `points_render_basics`
- `project_points` `points → keypoints` GPU: 无 — 3D 点群 (N,3) → 图像坐标 (u,v) 与深度。针孔(depth_to_points 的正向)。 · 示例: `pnp_pose_outliers`, `pose_estimation`
- `render_beauty` `mesh → rgbimage` GPU: 无 — 把网格以全品质层合成渲染成一张「好看的静态 3D」→ RGB ``(size, size, 3)`` float [0,1]。 · 示例: `anatomical_hand`, `render_beauty`
- `render_point_depth` `points → depth` GPU: 无 — 点群 → 深度图像(z-buffer,每像素取最近点的深度)。用于合成观测/外观检测样本。 · 示例: `sfm_recon`
- `render_regolith` `mesh → rgbimage` GPU: 无 — 以物理为基础渲染小行星风化层(Hapke + 太阳视直径的光线投射阴影 + 零环境光)→ RGB ``(size,size,3)``。 · 示例: `itokawa_regolith_hero`
- `render_shaded` `normalmap → image2d` GPU: 无 — 法线图 (H,W,3) + 光源方向 → Lambert 着色图像(外观样本生成,与光学衔接)。 · 示例: `render_ao`
- `render_volume_projection` `voxel → image2d` GPU: 有(许可列表) — 从任意视点把 voxel 投影为 2D(mode=xray=衰减积分 / mip=最大值)。用于 DRR(X 光)与世界模型观测。 · 示例: `ct_hand_radiograph`
- `shadow_raycast` `mesh × vector → image2d` GPU: 无 — 直接向网格投射光线,返回太阳光可见性 (H,W) ∈ [0,1] (不使用 shadow map)。 · 示例: `itokawa_regolith_hero`
- `supersample_mesh` `mesh → image2d` GPU: 无 — 用 SSAA 抗锯齿渲染网格 -> float 图像 ``(H, W)``(或 ``(H, W, C)``)。 · 示例: `render_ssaa`
- `tonemap_aces` `image2d → image2d` GPU: 有(许可列表) — 用 ACES filmic 近似(Narkowicz 2015)把 HDR 压缩到 ``[0, 1]`` 的 LDR。→ float64。 · 示例: `render_tonemap`
- `tonemap_reinhard` `image2d → image2d` GPU: 无 — 用 Reinhard 色调映射把 HDR 压缩到 ``[0, 1]`` 的 LDR。→ float64,与输入同形状。 · 示例: `render_beauty`, `render_tonemap`

#### 3d / resolution (15)
- `mesh_decimate_preserving` `mesh → table` GPU: 无 — 保留细节区域的简化,并报告失去了什么(``table``)。 · 示例: `mesh_resolution_demo`
- `mesh_detail_map` `mesh → table` GPU: 无 — 网格逐顶点的粗糙度与细节度(``table``)。 · 示例: `mesh_resolution_demo`
- `mesh_edge_stats` `mesh → table` GPU: 无 — 边长与面面积的分位数,以及不均匀比(``table``)。 · 示例: `mesh_resolution_demo`
- `mesh_isotropic_remesh` `mesh → mesh` GPU: 无 — 面向统一 *target_edge* 的渐进各向同性重网格化(``mesh``)。 · 示例: `mesh_resolution_demo`
- `mesh_lod_chain` `mesh → table` GPU: 无 — 简化层级序列,并给出各级的实测几何误差(``table``)。 · 示例: `mesh_resolution_demo`
- `mesh_reduction_report` `mesh × mesh → table` GPU: 无 — 一次削减(简化、重网格化、体素化)失去了什么,以数字给出(``table``)。 · 示例: `mesh_resolution_demo`
- `mesh_sample_points` `mesh → points` GPU: 无 — 按给定间距在表面采样 —— 面积加权随机或 Poisson-disk(``points``)。 · 示例: `mesh_resolution_demo`
- `mesh_select_lod` `table → table` GPU: 无 — 几何误差投影后低于 *pixel_tolerance* 的最粗 LOD 级(``table``)。 · 示例: `mesh_resolution_demo`
- `mesh_split_long_edges` `mesh → mesh` GPU: 无 — 把长于 *max_edge* 的边二分,直到不再有 —— 自适应细化(``mesh``)。 · 示例: `mesh_resolution_demo`
- `pc_density` `points → table` GPU: 无 — 逐点的局部间距与点云的不均匀性(``table``)。 · 示例: `mesh_resolution_demo`
- `pc_density_equalize` `points → points` GPU: 无 — 先填补稀疏区,再抽稀稠密区:间距均匀化(``points``)。 · 示例: `mesh_resolution_demo`
- `pc_fill_sparse` `points → points` GPU: 无 — 在局部间距超过 *spacing* 处、于局部 PCA 平面上插入点(``points``)。 · 示例: `mesh_resolution_demo`
- `pc_lod_chain` `points → table` GPU: 无 — 间距逐次加倍的 Poisson-disk 层级(``table``)。 · 示例: `mesh_resolution_demo`
- `pc_poisson_disk` `points → points` GPU: 无 — 蓝噪声抽稀:贪心保留点,使任意两点距离不小于 *radius*(``points``)。 · 示例: `mesh_resolution_demo`
- `pc_thinning_report` `points × points → table` GPU: 无 — 点云抽稀移除了什么,以及是否动到了稀有点(``table``)。 · 示例: `mesh_resolution_demo`

#### 3d / restoration (2)
- `vol_gaussian_psf` `measurement → voxel` GPU: 无 — 归一化(和为 1)的 3-D 高斯 PSF 核。*sigma* 为标量或逐轴。 · 示例: `deconv_fft_restore`
- `vol_richardson_lucy` `voxel × voxel → voxel` GPU: 无 — 用已知 PSF 对非负体做 Richardson–Lucy 反卷积。 · 示例: `deconv_fft_restore`

#### 3d / rle_region (9)
- `vol_rle_bbox` `rle_region → primitive` GPU: 无 — 由 run 求出紧致包围盒 ``(z0, y0, x0, z1, y1, x1)``(上界为开区间)。 · 示例: `rle_region_efficiency`
- `vol_rle_centroid` `rle_region → position` GPU: 无 — 在 run 上计算区域的重心 ``(z, y, x)``(不解码)。 · 示例: `rle_region_efficiency`
- `vol_rle_components` `voxel → rle_region` GPU: 无 — 把二值体拆成逐成分的 ``VolRLE`` 区域。 · 示例: `rle_region_efficiency`
- `vol_rle_decode` `rle_region → voxel` GPU: 无 — 把 ``VolRLE`` 解码回稠密的 ``(D, H, W)`` float64 ``{0, 1}`` 体数据。 · 示例: `rle_region_efficiency`
- `vol_rle_difference` `rle_region × rle_region → rle_region` GPU: 无 — 在 run 上的差集 ``a \ b``(不解码)。 · 示例: `rle_region_efficiency`
- `vol_rle_encode` `voxel → rle_region` GPU: 无 — 把二值体编码为 x 方向 run(3-D 的 HALCON region 表示)。 · 示例: `rle_region_efficiency`
- `vol_rle_intersect` `rle_region × rle_region → rle_region` GPU: 无 — 在 run 上求两个 RLE 区域的交(不解码)。 · 示例: `rle_region_efficiency`
- `vol_rle_union` `rle_region × rle_region → rle_region` GPU: 无 — 在 run 上求两个 RLE 区域的并(不解码)。 · 示例: `rle_region_efficiency`
- `vol_rle_volume` `rle_region → measurement` GPU: 无 — 在 run 上数出区域的体素数(不解码)。 · 示例: `rle_region_efficiency`

#### 3d / robust_fit (7)
- `fit_cone` `points → primitive` GPU: 无 — 对点群拟合无限圆锥,返回 ``{apex, axis, half_angle, residual}``。 · 示例: `fit_primitives_ext`
- `fit_ellipsoid` `points → primitive` GPU: 无 — 对点群代数拟合任意姿态的三轴椭球,返回 ``{center, axes, radii, residual}``。 · 示例: `fit_primitives_ext`
- `fit_torus` `points → primitive` GPU: 无 — 对点群拟合圆环面,返回 ``{center, axis, R, r, residual}``。 · 示例: `fit_primitives_ext`
- `ransac_cylinder` `points × normals → primitive` GPU: 无 — 对外点稳健的 RANSAC 圆柱拟合(需要点法线)。 · 示例: `ransac_prim`
- `ransac_line` `points → primitive` GPU: 无 — 对外点稳健的 RANSAC 直线拟合。 · 示例: `geometry_metrology`
- `ransac_plane` `points → primitive` GPU: 无 — 对外点稳健的 RANSAC 平面拟合。 · 示例: `ransac_prim`
- `ransac_sphere` `points → primitive` GPU: 无 — 用对外点稳健的 RANSAC 给点群拟合球(中心与半径)。 · 示例: `ransac_prim`

#### 3d / scene_flow3d (3)
- `nearest_neighbor_flow` `points × points → flow_scattered` GPU: 无 — 从 pts0 各点到 pts1 最近邻的 3-D 位移向量场 (N, 3)。 · 示例: `scene_flow_rigid`
- `rigid_flow` `points × points → pose` GPU: 无 — 用最近邻对应 + Kabsch(类 ICP)估计解释 pts0 -> pts1 的单一刚体运动。 · 示例: `scene_flow_rigid`
- `smooth_flow` `points × points → flow_scattered` GPU: 无 — 返回把最近邻流用邻域平均局部平滑后的正则化流 (N, 3)。 · 示例: `scene_flow_rigid`

#### 3d / sdf_csg (12)
- `box_sdf` `coordgrid → sdf` GPU: 无 — 轴对齐长方体的**精确**符号距离场(内负外正)。 · 示例: `gear_metrology`, `render_beauty`, `sdf_csg`
- `capsule_sdf` `coordgrid → sdf` GPU: 无 — 将线段 ``a``–``b`` 以半径 ``radius`` 加粗所得胶囊体的**精确**有符号距离场。 · 示例: `procedural_hand`, `sdf_csg`
- `cylinder_sdf` `coordgrid → sdf` GPU: 无 — 有限长圆柱(两端为平盖)的**精确**有符号距离场(内侧为负、外侧为正)。 · 示例: `sdf_csg`
- `grid_coords` `无输入 → coordgrid` GPU: 无 — 构建用于 CSG 求值的体素中心坐标网格(与 occupancy 相同的格点约定)。 · 示例: `gear_metrology`, `molecule_atom_count`, `procedural_hand`, `render_beauty`, `sdf_csg`, `sfm_recon`
- `plane_sdf` `coordgrid → sdf` GPU: 无 — 半空间的精确有符号距离场。``fast`` 是可选路径，在 1e6 处实测相对差 1.5e-10；默认为 ``exact``。 · 示例: `sdf_csg`
- `sdf_intersect` `sdf × sdf → sdf` GPU: 无 — 两个 SDF 的交集 A∩B = 逐元素 max(a, b)(只有两者都在内侧才在内侧)。 · 示例: `gear_metrology`, `render_beauty`, `sdf_csg`
- `sdf_offset` `sdf → sdf` GPU: 仅在链中(许可列表) — 把 SDF 的零等值面沿法线移动距离 ``r`` = ``sdf - r``(r>0 膨胀, r<0 收缩)。 · 示例: `sfm_recon`
- `sdf_smooth_union` `sdf × sdf → sdf` GPU: 有(许可列表) — 平滑圆化的并集(polynomial smooth-min)。``k>0`` 会以约 k 的半径圆化接缝。 · 示例: `render_beauty`
- `sdf_subtract` `sdf × sdf → sdf` GPU: 仅在链中(许可列表) — 差集 A\B = max(a, -b)(在 A 内侧 且 在 B 外侧 = 在 ``-b`` 内侧)。 · 示例: `sdf_csg`
- `sdf_union` `sdf × sdf → sdf` GPU: 无 — 两个 SDF 的并集 A∪B = 逐元素 min(a, b)(任一为负即在内侧)。 · 示例: `gear_metrology`, `render_beauty`, `sdf_csg`
- `sphere_sdf` `coordgrid → sdf` GPU: 无 — 球的符号距离场:``|p - center| - R``(内负外正)。 · 示例: `annotate3d_figure`, `gear_metrology`, `molecule_atom_count`, `procedural_hand`, `render_beauty`, `sdf_csg`, `sfm_recon`
- `torus_sdf` `coordgrid → sdf` GPU: 无 — 圆环面(甜甜圈形)的**精确**有符号距离场(内侧为负、外侧为正)。 · 示例: `sdf_csg`

#### 3d / segment (4)
- `euclidean_cluster` `points → labels` GPU: 无 — 按半径 tol 的邻接图连通成分做距离聚类(−1=噪声)。 · 示例: `object_segmentation`
- `plane_segmentation` `points → labels` GPU: 无 — 用迭代 RANSAC 依次提取最多 max_planes 个平面(残余点为 -1)。 · 示例: `object_segmentation`
- `region_growing` `points → labels` GPU: 无 — 按法线相似度做区域生长,给连通的平滑区域同一标签(无曲率门限的变体)。 · 示例: `sensor_seg`
- `vol_watershed` `voxel → labels` GPU: 无 — 标记控制的 3-D 分水岭分割(**可选 —— scikit-image**)。 · 示例: `molecule_atom_count`

#### 3d / shape_descriptor (5)
- `a3_distribution` `points → descriptor` GPU: 无 — 随机三点 (A, B, C) 在顶点 B 处所成角的分布(Osada 2002 的 A3)。 · 示例: `shape_desc_pose`
- `d2_distribution` `points → descriptor` GPU: 无 — 随机点对之间欧氏距离的分布(Osada 2002 的 D2)。 · 示例: `shape_desc_pose`
- `describe` `points → descriptor` GPU: 无 — 把 D2 + A3 + extent 串接成的全局形状描述子。 · 示例: `denoise_evolution`, `shape_desc_pose`, `shape_retrieval`
- `extent_signature` `points → descriptor` GPU: 无 — 沿 PCA 主轴(协方差特征向量)方向展布的比值。 · 示例: `shape_desc_pose`
- `shape_distance` `descriptor × descriptor → measurement` GPU: 无 — 两个描述子之间的距离。越小形状越相似。 · 示例: `moment_invariants`, `shape_desc_pose`, `shape_retrieval`

#### 3d / space_carving (4)
- `carve` `images → voxel` GPU: 无 — 把 bounds 离散成 res^3 体素,保留投影落在所有轮廓内的体素(空间雕刻)。 · 示例: `space_carving`
- `carve_look_at` `vector → pose` GPU: 无 — 生成可传给 ``carve`` / ``synthesize_silhouette`` 的相机位姿 ``(R, t)``。 · 示例: `space_carving`
- `synthesize_silhouette` `points → image2d` GPU: 无 — 把 3-D 点群投影到 (K,R,t) 相机,返回占据像素为 True 的轮廓(H,W bool)。 · 示例: `space_carving`
- `visual_hull` `images → voxel` GPU: 无 — 把多视角轮廓的 visual hull 作为体素占据返回(:func:`carve` 的别名)。 · 示例: `space_carving`

#### 3d / structured_light (9)
- `absolute_phase` `image2d × image2d → image2d` GPU: 仅在链中(许可列表) — 用粗糙但绝对的相位估计确定条纹级次,把卷绕相位变成绝对相位。 · 示例: `structured_light_scan`
- `decode_fringe` `images → depth` GPU: 无 — 一次性解码相移图像序列:wrapped → 解缠 →(减去参考得到)高度。 · 示例: `structured_light`
- `depth_from_focus` (halcon: `depth_from_focus`) `images → depth` GPU: 无 — 根据不同焦点的图像，以每个像素的最佳对焦位置估计高度/深度。 · 示例: `ftp_and_focus_depth`
- `fringe_ftp_phase` `image2d → depth` GPU: 无 — 使用 Takeda 傅里叶变换轮廓术从单幅条纹图像恢复高度/相位。 · 示例: `ftp_and_focus_depth`
- `graycode_decode` `images → image2d` GPU: 有(许可列表) — Gray code 位图像序列 → 整数条纹级次图(绝对级次)。 · 示例: `graycode_structured_light`, `structured_light_scan`
- `synthesize_fringes` `image2d → images` GPU: 仅在链中(许可列表) — 由已知 height map 合成 N 步相移条纹图像序列(用于测试/样例生成)。 · 示例: `ftp_and_focus_depth`, `structured_light`
- `triangulate_column` `image2d → depth` GPU: 有(许可列表) — 由每个相机像素的「投影仪列号」三角测量出深度 Z(结构光的最后一段)。 · 示例: `structured_light_scan`
- `unwrap_phase_2d` `image2d → image2d` GPU: 无 — 用 skimage.restoration.unwrap_phase 把卷绕相位展开为连续相位。 · 示例: `structured_light`
- `wrapped_phase` `images → image2d` GPU: 有(许可列表) — 由 N 步相移条纹图像序列求 wrapped phase (-π, π]。 · 示例: `structured_light`, `structured_light_scan`

#### 3d / superquadric (4)
- `fit_superquadric` `points → primitive` GPU: 无 — 用 least_squares 对点群拟合超二次曲面,返回 dict{a,eps,R,t,residual}。 · 示例: `superquadric_fit`
- `inside_outside` `points → signal` GPU: 无 — 超二次曲面的内外函数 F(表面=1,内部<1,外部>1)。 · 示例: `superquadric_fit`
- `sample_surface` `vector → points` GPU: 无 — 以 (eta, omega) 参数化采样超二次曲面的表面点。 · 示例: `mesh_lod_download`, `superquadric_fit`
- `superquadric_residual` `points → measurement` GPU: 无 — Gross-Boult 体积修正残差 mean( (sqrt(a1 a2 a3)(F^eps1 - 1))^2 )。 · 示例: `superquadric_fit`

#### 3d / surface (5)
- `curve3d_tube_mesh` `points → mesh` GPU: 无 — 把空间曲线做成管状网格 —— MATLAB 的 ``tubeplot``,但体积可以核对。 · 示例: `minimal_surfaces`
- `gyroid_isosurface` `无输入 → mesh` GPU: 无 — 螺旋二十四面体(gyroid)—— 由节面近似生成的三重周期曲面。 · 示例: `minimal_surfaces`
- `gyroid_solid_mask` `无输入 → voxel` GPU: 无 — 作为可打印**实体**的 gyroid —— 等值面 ±*thickness* 之内的壳。 · 示例: `minimal_surfaces`
- `minimal_surface` `无输入 → mesh` GPU: 无 — 由精确参数化生成的经典极小曲面。 · 示例: `minimal_surfaces`
- `minimal_surface_bend` `无输入 → mesh` GPU: 无 — 悬链面 ⇄ 螺旋面的弯折 —— 族中每一个仍然是极小曲面。 · 示例: `minimal_surfaces`

#### 3d / surface_fit (4)
- `background_flatten` `image2d → image2d` GPU: 仅在链中(许可列表) — 拟合并减去图像的低阶曲面(照明不均)= 阴影校正。→ flattened。 · 示例: `geometry_metrology`
- `eval_poly_surface` `poly_surface × image2d × image2d → image2d` GPU: 有(许可列表) — 在 (x,y) 处评估 model → z(按 x 的形状返回)。 · 示例: `contours_to_terrain`
- `fit_poly_surface` `image2d × image2d × image2d → poly_surface` GPU: 无 — 散布 (x,y,z) → z=f(x,y) 多项式最小二乘。返回 model(coef/powers/degree/rms/pv)。 · 示例: `contours_to_terrain`
- `surface_form_error` `image2d → measurement` GPU: 有(许可列表) — 高度场 grid → 相对理想曲面(多项式)的残差=形状误差(平面度 deg1/球面度 deg2)。→ (residual, rms, pv)。 · 示例: `geometry_metrology`

#### 3d / symmetry (4)
- `detect_reflection_symmetry` `points → primitive` GPU: 无 — 在以 PCA 主轴为法线(过重心)的候选平面中选出最佳镜像对称面。 · 示例: `dl_mesh_symmetry`, `itokawa_symmetry_honest`, `reflection_symmetry`, `symmetry`
- `detect_rotational_symmetry` `points → primitive` GPU: 无 — 以 PCA 主轴为候选轴,选出最佳旋转对称(轴 × 阶数)。 · 示例: `rotational_symmetry_fold`, `symmetry`
- `reflect_points` `points → points` GPU: 无 — 把点群关于平面(点 plane_point、法线 plane_normal)镜像。→ (N,3)。 · 示例: `reflection_symmetry`
- `reflection_symmetry_score` `points → measurement` GPU: 无 — 反射对称得分 = chamfer(镜像, 原) / 最近邻间距中位数(越小越对称,尺度不变)。→ float。 · 示例: `dl_mesh_symmetry`, `reflection_symmetry`

#### 3d / terrain (8)
- `bump_normals_fbm` `normalmap × pointmap → normalmap` GPU: 有(许可列表) — 用带 seed 的多倍频高度场的**梯度**扰动法线图。 · 示例: `itokawa_regolith_hero`
- `displacement_band_weights` `mesh → matrix` GPU: 无 — 逐倍频、逐顶点的频带门 ``(K, N)``,取值 [0,1]。 · 示例: `itokawa_regolith_hero`
- `mesh_displace_fbm` `mesh → mesh` GPU: 无 — 用带 seed 的 fBm 噪声沿法线位移顶点,使网格变粗糙 → ``(V, F)``。 · 示例: `itokawa_regolith_hero`
- `mesh_displace_spectrum` `mesh → mesh` GPU: 无 — 以**明确给出的振幅谱**、带限地沿法线位移顶点。 · 示例: `itokawa_regolith_hero`
- `mesh_edge_lengths` `mesh → signal` GPU: 无 — 三角网格的局部边长(逐顶点、逐面或逐唯一边)。 · 示例: `itokawa_regolith_hero`
- `mesh_scatter_boulders` `mesh → mesh` GPU: 无 — 在网格上散布半埋的岩块(幂律尺寸,带 seed)→ ``(V, F)``。 · 示例: `itokawa_regolith_hero`
- `mesh_subdivide` `mesh → mesh` GPU: 无 — 用中点细分或自适应细分细化三角网格 → ``(V, F)``。 · 示例: `itokawa_regolith_hero`
- `terrain_region_mask` `mesh → signal` GPU: 无 — 逐面的地形权重 (M,) ∈ [0,1]:0 = 平滑风化层「海」,1 = 粗糙高地。 · 示例: `itokawa_regolith_hero`

#### 3d / transform (12)
- `depth_to_points` `depth → points` GPU: 无 — 深度图(2.5D)→ 点云(针孔反投影)。把 depth 行接到所有方法。 · 示例: `structured_light_scan`, `transforms_repr`
- `estimate_point_normals` `points → normals` GPU: 无 — 点群 (N,3) → 单位法线(局部 k 近邻协方差的最小特征向量 = PCA)。 · 示例: `fpfh_correspondence`
- `gaussians_to_voxel` `points → voxel` GPU: 无 — 3DGS(各向异性高斯)→ 密度体素。把每个高斯按 opacity 置于 means,再用平均 scale 平滑。 · 示例: `transforms_repr`
- `mesh_to_points` `mesh → points` GPU: 无 — mesh(顶点+面)→ 表面点群(面积加权均匀采样)。mesh→point cloud 转换。 · 示例: `mesh_decimate`
- `mesh_to_voxel` `mesh → voxel` GPU: native(device 参数，仅在链中) — mesh(顶点+面)→ 密度 voxel。面上均匀采样 → splat(把 mesh 行接到所有方法)。 · 示例: `transforms_repr`
- `points_to_voxel` `points → voxel` GPU: 无 — 点群 (N,3) → 密度 voxel (size³)。用 scatter_add splat,可选高斯平滑。 · 示例: `sh_descriptor_retrieval`, `shape_desc_pose`
- `sdf_to_occupancy` `sdf → voxel` GPU: 无 — SDF → occupancy voxel(小于等于 iso=内侧=1)。从 SDF 回到 voxel。 · 示例: `transforms_repr`
- `signed_distance_field` `voxel → sdf` GPU: native(device 参数) — occupancy/密度 voxel → 符号距离场 SDF(内侧<0、外侧>0)。对两侧各做 edt_jfa。 · 示例: `transforms_repr`
- `to_points` `voxel × points × mesh × depth × gaussians → points` GPU: 无 — 任意 3D 结构 → 点群(共同表示)。把全部 5 种结构统一到一个入口。 · 示例: `transforms_repr`
- `tsdf_from_depth` `depth → sdf` GPU: 有(许可列表) — 深度图(2.5D)→ TSDF volume(RGB-D 重建的标准表示)。depth→TSDF 转换。 · 示例: `transforms_repr`
- `voxel_to_mesh` `voxel → mesh` GPU: 无 — voxel → mesh(marching cubes,skimage)。返回 (verts, faces, normals)。voxel→mesh 转换。 · 示例: `mesh_smooth`
- `voxel_to_mips` `voxel → images` GPU: 无 — 3D → 正交三方向的最大值投影(MIP)。应用 2D 方法(如 accel 的 2D NCC)的入口。 · 示例: `transforms_repr`

#### 3d / tsdf_fusion (3)
- `extract_surface_points` `sdf → points` GPU: 无 — 由 TSDF 零交叉提取表面点 (M,3)(无需 marching cubes,线性插值)。 · 示例: `transforms_repr`, `tsdf_fusion_demo`
- `fuse` `depth → sdf` GPU: 无 — 用 new_volume + integrate 把深度序列融合成一个 TSDF 体。返回 (tsdf, weight)。 · 示例: `tsdf_fusion_demo`
- `integrate` `sdf × depth → sdf` GPU: 无 — 用投影式 TSDF 把一张深度整合进 volume(原地,加权滑动平均)。 · 示例: `transforms_repr`

#### 3d / two_view (5)
- `essential_8point` `image2d × image2d → matrix` GPU: 无 — 由对应点 + K 直接求本质矩阵 E。→ E (3,3)。 · 示例: `sfm_recon`
- `fundamental_8point` `image2d × image2d → matrix` GPU: 无 — 用归一化八点法估计基础矩阵 F(强制 rank-2)。→ F (3,3)。至少需要 8 点。 · 示例: `two_view_pose`
- `recover_pose` `image2d × image2d → pose` GPU: 无 — 由对应点 + K 恢复相对位姿 (R,t) 与 3D 结构(用 cheirality 消歧)。→ (R, t_unit, points3d)。 · 示例: `two_view_pose`
- `sampson_distance` `image2d × image2d → signal` GPU: 无 — 对极约束的 Sampson 距离(一阶几何误差,逐对应)。→ (N,)。 · 示例: `two_view_pose`
- `triangulate` `image2d × image2d → points` GPU: 无 — DLT 三角化:两视图的对应点 + 投影矩阵 → 3D 点。→ (N,3)。 · 示例: `sfm_recon`

### fit (3 ops / 2 categories)

#### fit / fit (2)
- `fit_circle_geometric` `keypoints → table` GPU: 无 — 用几何最小二乘法对包括短圆弧的（行、列）点拟合圆和半径。 · 示例: `fit_ops_from_knowhow`
- `fit_curve_principal_axis` `keypoints → table` GPU: 无 — 将倾斜曲边旋转到主轴后拟合多项式 y'=f(x')。 · 示例: `fit_ops_from_knowhow`

#### fit / registration (1)
- `phase_correlation_shift` `image2d × image2d → table` GPU: 无 — 用相位限定相关估计两幅图像对齐所需的亚像素平移。 · 示例: `fit_ops_from_knowhow`

### math (115 ops / 12 categories)

支撑视觉测量的数学 op(线性代数/统计/插值、多项式)+ 复分析的可计算切入点(围道积分、Cauchy 积分公式、辐角原理、Laurent 系数/留数、共形映射、Cauchy-Riemann 残差)。FFT/复数图像见 complexops、volfreq，1-D 函数见 funct1d。

#### math / complex (18)
- `cplx_argument_principle` `cpoints × cpoints → measurement` GPU: 无 — 辐角原理:仅凭 ``f`` 的采样值,数出围道内零点数减去极点数。 · 示例: `math_complex`
- `cplx_cauchy_value` `cpoints × cpoints → cscalar` GPU: 无 — 柯西积分公式:由围道**上**的值还原围道**内**的 ``f(w)``。 · 示例: `math_complex`
- `cplx_contour_circle` `无输入 → cpoints` GPU: 无 — 把圆采样成闭合围道 —— 标准的积分路径。 · 示例: `math_complex`
- `cplx_contour_integral` `cpoints × cpoints → cscalar` GPU: 无 — 用弦梯形法计算闭合围道积分 ``∮ f(z) dz``。 · 示例: `math_complex`, `representation_conversion`
- `cplx_cr_residual` `cimage → measurement` GPU: 无 — 采样复场的柯西-黎曼残差 —— 把「这个场全纯吗?」变成一个数。 · 示例: `math_complex`, `poc_complex_plane_fields`
- `cplx_domain_colour` `cimage → rgbimage` GPU: 有(许可列表) — 定义域着色 —— 把复场变成可以读懂的 RGB 图像。 · 示例: `poc_complex_plane_fields`
- `cplx_escape_time` `无输入 → image2d` GPU: 无 — 迭代 ``z -> z**2 + c`` 多少步才离开逃逸圆盘。 · 示例: `poc_complex_plane_fields`
- `cplx_joukowski` `cpoints → cpoints` GPU: 无 — 儒可夫斯基共形映射 ``w = z + c^2 / z``。 · 示例: `math_complex`
- `cplx_laurent_coeffs` `cpoints × cpoints → table` GPU: 无 — **均匀采样圆周**上的 Laurent(以及 Taylor)系数 —— 含留数。 · 示例: `math_complex`
- `cplx_mobius` `cpoints → cpoints` GPU: 无 — 莫比乌斯(线性分式)变换 ``w = (a z + b) / (c z + d)``。 · 示例: `math_complex`
- `cplx_newton_basins` `signal → labels2d` GPU: 无 — 从每一点出发的牛顿法, 会落到多项式的哪一个根? · 示例: `poc_complex_plane_fields`
- `cplx_plane_grid` `无输入 → cimage` GPU: 无 — 把复平面的矩形窗口变成网格(排列与图像相同: 第 0 行在上, 即虚部较大的一侧)。 · 示例: `poc_complex_plane_fields`
- `cplx_poly_eval` `signal × cpoints → cpoints` GPU: 有(许可列表) — 在复平面上求多项式的值(Horner 法,支持复数)。 · 示例: `math_complex`
- `cplx_rational_field` `roots × roots → cimage` GPU: 无 — 对有理函数 ``R(z) = gain * prod(z - zeros) / prod(z - poles)`` 采样。 · 示例: `poc_complex_plane_fields`
- `cplx_winding_number` `cpoints → measurement` GPU: 无 — 闭合围道绕某点的卷绕数(回转数)。 · 示例: `math_complex`, `poc_complex_plane_fields`
- `joukowski_circulation` `无输入 → measurement` GPU: 无 — 该翼型的库塔环量 ``Gamma = 4*pi*a*U*sin(alpha + beta)``。 · 示例: `poc_complex_plane_fields`
- `mandelbrot_interior` `cimage → mask` GPU: 有(许可列表) — 对主心形线与周期 2 圆盘的内部判定, 以闭形式给出。 · 示例: `poc_complex_plane_fields`
- `potential_flow_joukowski` `无输入 → cimage` GPU: 无 — 儒可夫斯基翼型周围的无黏流, 以复速度场给出。 · 示例: `poc_complex_plane_fields`

#### math / construct (8)
- `circle_packing_apollonian` `无输入 → table` GPU: 无 — 由笛卡儿四元组生成的阿波罗尼奥斯圆填充 —— 每个圆都背着一条定理。 · 示例: `poc_theorems_as_pictures`
- `curve_locality` `pairs → table` GPU: 无 — 沿曲线编号相差 k 的两点, 在平面上相距多远? · 示例: `poc_theorems_as_pictures`
- `ford_circles` `无输入 → table` GPU: 无 — 法里分数的福特圆 —— 相切就是一个整数等式本身。 · 示例: `poc_theorems_as_pictures`
- `ifs_fractal` `无输入 → pairs` GPU: 无 — 迭代函数系统的混沌游戏 —— 维数有闭形式。 · 示例: `poc_theorems_as_pictures`
- `ifs_similarity_dimension` `无输入 → measurement` GPU: 无 — 对莫兰方程 ``sum(r_i**d) = 1`` 解出 d —— 只用映射本身。 · 示例: `poc_theorems_as_pictures`
- `neighbour_index_gaps` `pairs → signal` GPU: 无 — 最近邻之间在**编号上**相距多远 —— 把斜列(parastichy)变成数。 · 示例: `poc_theorems_as_pictures`
- `phyllotaxis_pattern` `无输入 → pairs` GPU: 无 — 沃格尔螺线 —— 堆积最紧的那个角度, 以及由它生出的螺旋。 · 示例: `poc_theorems_as_pictures`
- `space_filling_curve` `无输入 → pairs` GPU: 无 — ``2**order`` 方格上的希尔伯特/摩尔/扫描顺序 —— 并验证它确实是一个置换。 · 示例: `poc_theorems_as_pictures`

#### math / dynsys (6)
- `dynsys_bifurcation_map` `无输入 → pairs` GPU: 无 — 一维映射的轨道图 —— 把倍周期分岔化为可数的点。 · 示例: `poc_what_a_picture_cannot_check`
- `dynsys_correlation_dimension` `points → measurement` GPU: 无 — Grassberger–Procaccia 关联维数 —— ``log C(r)`` 的斜率。 · 示例: `poc_what_a_picture_cannot_check`
- `dynsys_lyapunov_spectrum` `无输入 → signal` GPU: 无 — 用切流 + QR 求出的李雅普诺夫谱 —— 以及可以核对的和。 · 示例: `poc_what_a_picture_cannot_check`
- `dynsys_poincare_section` `table → pairs` GPU: 无 — 轨道穿过平面之处 —— 交点经插值后返回。 · 示例: `poc_what_a_picture_cannot_check`
- `ode_flow_states` `无输入 → table` GPU: 无 — 对具名向量场做积分 —— 轨道,以及你所付出的阶数。 · 示例: `poc_what_a_picture_cannot_check`
- `ode_vector_field_grid` `无输入 → flow2d` GPU: 无 — 在网格上采样具名场 —— 现有查看器可直接接收的 ``flow2d``。 · 示例: `poc_what_a_picture_cannot_check`

#### math / estimation (12)
- `assign_hungarian` `matrix → table` GPU: 无 — 求解代价矩阵 (n, m) 的指派问题(Kuhn 1955 / Munkres 1957 的匈牙利算法，scipy 的实现)。 · 示例: `estimation_tour`
- `crlb_gaussian` `signal × signal → table` GPU: 无 — 白高斯噪声(标准差 sigma)下的 Cramér–Rao 下界。 · 示例: `estimation_tour`
- `hist_distance` `signal × signal → measurement` GPU: 无 — 2 个直方图(非负，按总和归一化)之间的距离与散度。 · 示例: `gallery_math_stats_linalg`
- `kalman_smooth` `matrix × matrix × matrix × matrix × matrix × signal × matrix → table` GPU: 无 — 线性高斯状态空间模型 x_{k+1} = F x_k + w(w ~ N(0,Q))、z_k = H x_k + v(v ~ N(0,R))的 Kalman 滤波(前向)与 Rauch–Tung–Striebel 平滑(后向)。 · 示例: `estimation_tour`, `poc_real_bg_kalman_tracking`
- `mat_expm` `matrix → matrix` GPU: 无 — 矩阵指数函数 e^A(Padé 近似 + scaling-and-squaring，scipy)。 · 示例: `gallery_math_stats_linalg`
- `mat_logm` `matrix → matrix` GPU: 无 — 矩阵的主对数 log A(满足 e^X = A 的 X 中，特征值虚部位于 (−π, π] 的那个，scipy)。 · 示例: `gallery_math_stats_linalg`
- `se3_exp` `signal → matrix` GPU: 无 — SE(3) 的指数映射：6 维旋量 ξ = (v, ω)(平移速度 v、旋转向量 ω)→ 4×4 刚体变换。 · 示例: `estimation_tour`
- `se3_log` `matrix → signal` GPU: 无 — SE(3) 的对数映射：4×4 刚体变换 → 6 维旋量 ξ = (v, ω)(旋转角 < π)。门禁：se3_log(se3_exp(ξ)) = ξ。 · 示例: `estimation_tour`
- `stat_chi2_gof` `signal → table` GPU: 无 — χ² 拟合优度检验：频数 ``observed`` 是否符合期望频数(默认为均匀)。自由度 = 分组数 − 1。 · 示例: `gallery_math_stats_linalg`
- `stat_ks_test` `signal → table` GPU: 无 — Kolmogorov–Smirnov 检验。给出 ``y`` 时为 2 样本检验(是否来自同一分布)，否则为与标准正态分布的拟合优度检验。 · 示例: `gallery_math_stats_linalg`
- `stat_ttest_paired` `signal × signal → table` GPU: 无 — 配对 t 检验：对同一对象测量 2 次所得差值 d = x − y 的均值是否为 0。 · 示例: `gallery_math_stats_linalg`
- `stat_ttest_welch` `signal × signal → table` GPU: 无 — Welch t 检验：不假定方差相等的 2 组均值之差(自由度按 Welch–Satterthwaite)。 · 示例: `estimation_tour`

#### math / geometry (10)
- `angle_defect` `mesh → table` GPU: 无 — 每个顶点的角亏(离散 Gauss 曲率)K_v = 2π − Σ(该顶点处各三角形的角)。边界顶点为 π − Σ(测地曲率)。 · 示例: `geometry_tour`
- `delaunay_triangulate` `matrix → table` GPU: 无 — 平面点 (N, 2) 的三角剖分，或空间点 (N, 3) 的四面体剖分(Delaunay，scipy.spatial = Qhull)。 · 示例: `geometry_tour`
- `geodesic_heat` `mesh → table` GPU: 无 — 用热方法求曲面上的测地距离(Crane et al. 2013)。``source`` 为顶点编号(或编号序列，默认为顶点 0)。网格可以是 ``(vertices, faces)``，也可以是1 个 mesh 元组。 · 示例: `geometry_tour`
- `geodesic_heat_grid` `image2d → table` GPU: 无 — 在 2-D 图像或 3-D 体数据的网格上，用热方法求避开障碍物的测地距离(Crane et al. 2013 的网格版)。 · 示例: `geometry_tour`
- `mesh_euler_characteristic` `mesh → table` GPU: 无 — 三角网格的 V − E + F，以及若为闭合可定向曲面时的亏格 g = (2 − χ)/2。 · 示例: `geometry_tour`
- `mesh_torus` `无输入 → mesh` GPU: 无 — 环面(甜甜圈)的闭合三角网格 (vertices, faces)。大半径 R、管半径 r(R > r > 0)。 · 示例: `geometry_tour`
- `nurbs_circle` `无输入 → table` GPU: 无 — 精确表示圆的 2 次 NURBS(Piegl & Tiller 例 7.1：正方形的 4 个角与 4 条边的中点，角点权重为 1/√2)。 · 示例: `geometry_tour`
- `nurbs_curve` (halcon: `gen_contour_nurbs_xld`) `matrix → table` GPU: 无 — 求 NURBS 曲线的值(带权重，一般不经过控制点)。 · 示例: `geometry_tour`, `machine_vision_tour`
- `nurbs_revolve` `matrix → table` GPU: 无 — 将平面 NURBS 曲线 (r, z) 绕 z 轴旋转 1 周得到的旋转面(Piegl & Tiller §8.5)。 · 示例: `geometry_tour`
- `nurbs_surface` `无输入 → table` GPU: 无 — 求 NURBS 曲面(张量积)的值。 · 示例: `gallery_math_numerics_filters`

#### math / interp_poly (6)
- `interp_cubic` `signal × signal × signal → signal` GPU: 无 — 三次样条插值(``scipy.interpolate.CubicSpline``)。 · 示例: `math_metrology`
- `interp_linear` `signal × signal × signal → signal` GPU: 无 — 对 ``(x, y)`` 样本在查询点 *xq* 处做分段线性插值。 · 示例: `math_metrology`, `poc_thermal_radiometry`
- `interp_scattered` `points × signal × points → table` GPU: 无 — 由**散乱**样本求 *query* 处的值——传感器网、钻孔、气象。 · 示例: `poc_datacenter_thermal_field`, `poc_multibeam_bathymetry`, `poc_stockpile_volume`
- `poly_eval` `signal × signal → signal` GPU: 无 — 在 *x* 处求多项式的值(系数按最高次在前)。 · 示例: `math_metrology`, `signal_filter`
- `poly_fit` `signal × signal → table` GPU: 无 — 最小二乘多项式拟合,并**记录其条件数**。 · 示例: `math_metrology`, `poc_strain_history`, `poc_thermal_radiometry`, `signal_filter`
- `poly_roots` `signal → roots` GPU: 无 — 多项式的全部根(系数按最高次在前)—— 含复根。 · 示例: `math_metrology`

#### math / linalg (10)
- `mat_cholesky` `matrix → table` GPU: 无 — 对称正定矩阵的 Cholesky 分解 ``A = L @ Lᵀ``。 · 示例: `gallery_math_stats_linalg`
- `mat_cond` `matrix → measurement` GPU: 无 — 谱(2-范数)条件数 ``s_max / s_min`` —— 整个线性代数族的数值警报器。 · 示例: `math_metrology`
- `mat_eig` `matrix → table` GPU: 无 — **一般**方阵的特征分解 ``A V = V diag(w)``(一般为复数)。 · 示例: `gallery_math_stats_linalg`
- `mat_eigh` `matrix → table` GPU: 无 — **对称**矩阵的特征分解(LAPACK ``syevd``)。 · 示例: `math_metrology`, `poc_thermal_radiometry`
- `mat_lstsq` `matrix × signal → table` GPU: 无 — 超定方程组 ``A x ≈ b`` 的最小二乘解(LAPACK ``gelsd``,基于 SVD)。 · 示例: `math_metrology`, `poc_colocalization_crosstalk`, `poc_sea_ice_concentration`, `poc_solar_limb_darkening`
- `mat_lu` `matrix → table` GPU: 无 — LU 分解 ``P @ A = L @ U``(``L`` 为单位下三角,``U`` 为上三角)。 · 示例: `gallery_math_stats_linalg`
- `mat_pinv` `matrix → matrix` GPU: 有(许可列表) — 基于 SVD 的 Moore-Penrose 伪逆,截断阈值**显式给出**。 · 示例: `math_metrology`, `poc_machine_condition_fusion`
- `mat_qr` `matrix → table` GPU: 无 — QR 分解 ``A = Q @ R``(``Q`` 的列为标准正交,``R`` 为上三角)。 · 示例: `numerics_tour`
- `mat_solve` `matrix × signal → signal` GPU: 无 — 解方阵线性方程组 ``A x = b``(LAPACK ``gesv``,部分选主元的 LU)。 · 示例: `math_metrology`, `poc_colocalization_crosstalk`
- `mat_svd` `matrix → table` GPU: 无 — 奇异值分解 ``A = U @ diag(s) @ Vt``(LAPACK ``gesdd``)。 · 示例: `math_metrology`, `poc_water_level`

#### math / numerics (11)
- `bessel` `signal → signal` GPU: 无 — Bessel 函数。``kind`` = ``"j"``(第 1 类 J)/ ``"y"``(第 2 类 Y)/ ``"i"``、``"k"``(修正)。 · 示例: `gallery_math_numerics_filters`
- `chebyshev_coeffs_nd` `image2d → table` GPU: 无 — 由在张量积 Chebyshev–Lobatto 网格上采样的值求 N 维 Chebyshev 系数(DCT-I)。 · 示例: `numerics_tour`
- `chebyshev_eval_nd` `table × matrix → signal` GPU: 无 — 在点 (M, d) 处计算 ``chebyshev_coeffs_nd`` 系数的值(各轴 T_k(t) = cos(k·arccos t))。 · 示例: `numerics_tour`
- `chebyshev_nodes` `无输入 → signal` GPU: 无 — 区间 [a, b] 上的 n 个 Chebyshev 点(升序)。 · 示例: `numerics_tour`
- `erf` `signal → signal` GPU: 无 — 误差函数 erf(x) = (2/√π) ∫_0^x e^{−t²} dt。 · 示例: `numerics_tour`, `poc_battery_electrode_breathing`, `poc_bga_ball_type_roundtrip`, `poc_change_detection_misreg`, `poc_crack_width_timeseries`, `poc_dic_strain`, `poc_die_tilt_tsv_overlay`, `poc_dimensional_inspection`, `poc_exoplanet_transit`, `poc_fresco_craquelure`, `poc_mri_bias_field`, `poc_search_sweep_width`, `poc_settlement_significance`, `poc_star_astrometry`, `representation_roundtrip`
- `erfc` `signal → signal` GPU: 无 — 互补误差函数 erfc(x) = 1 − erf(x)。在 x 较大时用减法计算 1 − erf 会发生有效数字丢失，因此单独提供(x = 10 时 1 − erf 为 0，而 erfc 为 2.1e−45)。 · 示例: `poc_dfm_thickness_overhang`, `poc_itof_multifreq`
- `gauss_cubature` `无输入 → table` GPU: 无 — 用 Gauss–Legendre 的张量积，求盒 [a, b]^dim(a, b 也可按轴分别指定)上求积的节点 (n^dim, dim) 与权重。 · 示例: `gallery_math_numerics_filters`
- `gauss_quadrature` `无输入 → table` GPU: 无 — n 点 Gauss 求积的节点与权重。∫ f ≈ Σ w_k f(x_k)。 · 示例: `numerics_tour`
- `integrate_hamiltonian` `signal × signal → table` GPU: 无 — 对带名称的哈密顿系统(质量 1)做时间积分。返回值 ``{"t","q","p","energy","energy_drift","method","system"}``。 · 示例: `numerics_tour`
- `interp_barycentric` `signal × signal × signal → signal` GPU: 无 — 用重心公式在 x 处计算通过点 (xk, yk) 的多项式(次数 len−1)的值(Berrut & Trefethen 2004)。 · 示例: `numerics_tour`
- `low_discrepancy` `无输入 → matrix` GPU: 无 — [0, 1)^dim 中的低差异点列 (n, dim)。 · 示例: `numerics_tour`

#### math / spectral (6)
- `esprit_doa` `matrix → table` GPU: 无 — ESPRIT(Roy & Kailath 1989)：利用阵列“平移 1 个阵元”的不变性，不使用网格直接解出方向。 · 示例: `spectral_tour`
- `hilbert_analytic` `signal → table` GPU: 有(许可列表) — 解析信号 z = x + i·H[x] (用 FFT 消去负频率)，以及从中读出的振幅、瞬时相位和瞬时频率。 · 示例: `spectral_tour`
- `lomb_scargle` `signal × signal × signal → table` GPU: 无 — 非等间隔时间序列 (t, y) 的 Lomb–Scargle 周期图(带 Scargle 1982 的时间平移 τ，先减去均值)。 · 示例: `spectral_tour`
- `music_doa` `matrix → table` GPU: 无 — MUSIC(Schmidt 1986)：搜索与协方差噪声子空间正交的方向。 · 示例: `spectral_tour`
- `n_sources_mdl` `matrix → table` GPU: 无 — 根据快拍数据，用 MDL 准则估计信号源的数量(Wax & Kailath 1985)。 · 示例: `gallery_math_numerics_filters`
- `ula_snapshots` `signal → matrix` GPU: 无 — 生成等间隔线阵接收的复数快拍 (M, K)(到达方向估计答案已确定的输入)。 · 示例: `spectral_tour`

#### math / stats (5)
- `stat_correlation` `matrix → matrix` GPU: 无 — ``(N, D)`` 观测的 Pearson 相关矩阵 → ``(D, D)``。 · 示例: `math_metrology`, `poc_colocalization_crosstalk`, `poc_ct_fidelity`, `poc_machine_condition_fusion`, `poc_thermal_radiometry`
- `stat_covariance` `matrix → matrix` GPU: 无 — ``(N, D)`` 观测的样本协方差矩阵 → ``(D, D)``。 · 示例: `math_metrology`, `poc_thermal_radiometry`
- `stat_describe` `signal → table` GPU: 无 — 一维样本的五数概括(及更多),以普通 dict 返回。 · 示例: `math_metrology`, `poc_thermal_radiometry`
- `stat_histogram` `signal → pairs` GPU: 无 — 一维样本的直方图,分箱方式**显式给出**。 · 示例: `math_metrology`, `poc_thermal_radiometry`
- `stat_zscore` `signal → signal` GPU: 仅在链中(许可列表) — 标准化一维样本:``(x - mean) / std``(总体 ``ddof=0``)。 · 示例: `math_metrology`

#### math / transform (16)
- `abel_inverse` `signal → signal` GPU: 无 — 由投影 A(y) 还原轴对称分布 f(r)(逆 Abel 变换 = 轴对称物体的断层成像)。 · 示例: `transforms_tour`
- `abel_inverse_image` `image2d → table` GPU: 无 — 对从侧面拍摄的轴对称物体**图像**(纵向 = 对称轴方向，横向 = 距轴的距离)逐行做逆 Abel 变换，得到截面图像。 · 示例: `transforms_tour`
- `abel_revolve` `image2d → voxel` GPU: 无 — 将截面 f(z, r)((H, R)，r = 0, dr, …)绕对称轴旋转，得到 3-D 体积 (H, 2R−1, 2R−1)。 · 示例: `transforms_tour`
- `abel_transform` `signal → signal` GPU: 无 — 把轴对称分布 f(r)(在 r = 0, dr, 2dr, … 处的采样)映射为投影 A(y)(正向 Abel 变换)。 · 示例: `transforms_tour`
- `dct_transform` `image2d → table` GPU: 无 — N 维的正交归一 DCT-II(``inverse=True`` 时为 DCT-III = 逆变换)。 · 示例: `transforms_tour`
- `dwt_inverse` `table → image2d` GPU: 无 — 由 ``dwt_transform`` 的结果还原原数组(因为是正交归一的，所以就是分析的转置)。 · 示例: `transforms_tour`
- `dwt_transform` `image2d → table` GPU: 有(许可列表) — Daubechies dbN 的多级、N 维离散小波变换(在周期边界下严格正交归一)。 · 示例: `transforms_tour`
- `hankel_image` `image2d → table` GPU: 有(许可列表) — 用径向 Hankel 变换求轴对称图像的二维傅里叶变换。``memory_budget`` 选择实测差在 1e-10 内的省内存路径。 · 示例: `transforms_tour`
- `hankel_transform` `signal × signal → table` GPU: 无 — 用 quasi-discrete 法计算 p 阶 Hankel 变换 F(ν) = 2π ∫_0^∞ f(r) J_p(2πνr) r dr。 · 示例: `perf_hankel_plan_and_piv_stream`, `transforms_tour`
- `laplace_inverse_talbot` `signal × signal × signal → signal` GPU: 无 — 有理函数 F(s) = num(s)/den(s) 的数值逆拉普拉斯变换(固定 Talbot 法)。 · 示例: `transforms_tour`
- `tf_bilinear` `signal × signal → table` GPU: 无 — 用 Tustin(双线性)变换 s = K (z − 1)/(z + 1) 把连续系统映射为离散系统。 · 示例: `gallery_math_numerics_filters`
- `tf_freq_response` `signal × signal × signal → table` GPU: 无 — 频率响应 H(jω)(Bode 图的内容)。ω 的单位为 rad/s。相位为连续 unwrap 后的度数。 · 示例: `transforms_tour`
- `tf_impulse_response` `signal × signal × signal → signal` GPU: 无 — 冲激响应 h(t) = L⁻¹[H(s)] (t)(严格真分式部分。不返回直通项的 delta)。 · 示例: `transforms_tour`
- `tf_poles_zeros` `signal × signal → table` GPU: 无 — H(s) = num/den 的极点、零点、直流增益与稳定性。 · 示例: `transforms_tour`
- `tf_step_response` `signal × signal × signal → signal` GPU: 无 — 单位阶跃响应 y(t) = L⁻¹[H(s)/s] (t)。 · 示例: `transforms_tour`
- `wavelet_filters` `无输入 → table` GPU: 无 — 按教科书的构造方法(谱分解)生成 Daubechies 正交归一小波 dbN 的滤波器。 · 示例: `gallery_math_numerics_filters`

#### math / wave (7)
- `wave_dominant_frequency` `image2d → table` GPU: 无 — 返回图像最强周期（二维 FFT 中除直流外的最大峰）的频率、周期和方向（``table``）。 · 示例: `wave_dominant_frequency_grating`
- `wave_fringe_period` `image2d → measurement` GPU: 无 — 从条纹图像中反过来测出周期(像素)。 · 示例: `poc_beats_fringes_and_screens`, `wave_dominant_frequency_grating`
- `wave_grating_orders` `无输入 → table` GPU: 无 — 光栅把各级次送往何处 —— 对角度求解 ``d (sin_out − sin_in) = m λ``。 · 示例: `poc_beats_fringes_and_screens`, `poc_spectrometer_illumination`
- `wave_membrane_mode` `无输入 → matrix` GPU: 无 — 振动**膜**的一个本征模态 —— 沙子画出的那个图形(不是板)。 · 示例: `poc_beats_fringes_and_screens`
- `wave_mode_frequencies` `无输入 → signal` GPU: 无 — 膜的本征值阶梯 —— 可用来核对的闭式解。 · 示例: `poc_beats_fringes_and_screens`
- `wave_nodal_lines` `matrix → mask` GPU: 无 — 带符号的场改变符号的位置 —— 以掩膜返回节集。 · 示例: `poc_beats_fringes_and_screens`
- `wave_two_slit` `无输入 → image2d` GPU: 无 — 屏幕上的双缝干涉 —— 由物理构建,而非套用条纹公式。 · 示例: `poc_beats_fringes_and_screens`

### optics (506 ops / 55 categories)

位于镜头之上、像素之下的层。几何光学(薄透镜成像、ABCD 光线传递、景深、cos⁴ 渐晕)/ 波动光学(Airy 图样、角谱传播、Fraunhofer 衍射、高斯光束)/ 成像质量(PSF→MTF、衍射极限 MTF、Zernike 波前统计)/ 偏振(Jones、Stokes、Mueller)/ 材料物性表(matprop)、光纤(fiber)、传感器特性(sensorchar)、全局光传输等。

#### optics / appearance (7)
- `cie_xyz_from_wavelength` `signal → points` GPU: 有(许可列表) — 波长 [nm] → CIE 1931 2° 配色函数 (x̄, ȳ, z̄)。返回输入形状加末尾 3 的数组。 · 示例: `appearance_structural_colour`, `poc_chromatic_confocal`
- `grating_rgb` `normalmap → rgbimage` GPU: 无 — 法线图 + 光源 + 视线 → **衍射产生的虹彩** (H, W, 3) 线性 sRGB。 · 示例: `appearance_structural_colour`
- `grating_wavelengths` `无输入 → vector` GPU: 无 — 对 λ 求解光栅方程 d(sinθ_out − sinθ_in) = mλ。 · 示例: `appearance_structural_colour`, `poc_beats_fringes_and_screens`
- `spectrum_to_srgb` `signal → vector` GPU: 无 — 分光反射率 → **线性 sRGB**(伽马前)。归一化使白面(反射率 1)成为 (1,1,1)。 · 示例: `appearance_structural_colour`, `poc_material_optical_library`, `poc_pigment_unmixing`, `poc_simcal_thin_film`, `poc_white_balance`
- `thin_film_reflectance` `signal → signal` GPU: 有(许可列表) — 薄膜(厚度 d,折射率 n_film)的分光反射率。特性矩阵法的严格解(包含全部多次反射)。 · 示例: `appearance_structural_colour`, `simcal_tour`
- `thin_film_rgb` `normalmap → rgbimage` GPU: 无 — 法线图 + 视线 → **薄膜干涉的颜色** (H, W, 3) 线性 sRGB。 · 示例: `appearance_structural_colour`
- `ward_anisotropic` `normalmap → image2d` GPU: 无 — Ward 各向异性反射(椭圆高斯微面元)。拉丝表面的**拉长高光**。 · 示例: `appearance_structural_colour`

#### optics / cavity (5)
- `cavity_strain_transfer` `无输入 → pairs` GPU: 无 — 臂腔把应变 h(f) 映射到输出相位的传递函数幅值 |H(f)|（pairs）。 · 示例: `poc_gw_detector_pseudo_simulation`
- `fabry_perot_response` `无输入 → table` GPU: 无 — 以闭式返回 Fabry-Perot 腔的设计量（自由光谱范围、精细度、线宽、极点、功率增益、储能时间）。 · 示例: `poc_gw_detector_pseudo_simulation`
- `michelson_dc_readout` `无输入 → table` GPU: 无 — 从暗条纹偏移 φ₀ 的 Michelson 干涉仪：反对称端口光功率、应变灵敏度与散粒噪声极限。 · 示例: `poc_gw_detector_pseudo_simulation`
- `pdh_error_signal` `无输入 → pairs` GPU: 无 — Pound-Drever-Hall 误差信号 ε(δ)，作为失谐 δ [Hz] 的函数（pairs）。 · 示例: `poc_gw_detector_pseudo_simulation`
- `quantum_noise_budget` `无输入 → table` GPU: 无 — 常规（无信号回收）Fabry-Perot Michelson 的量子噪声：散粒噪声、辐射压噪声与标准量子极限。 · 示例: `poc_gw_detector_pseudo_simulation`

#### optics / coherent (6)
- `coherent_image` `image2d × image2d → image2d` GPU: 有(许可列表) — 振幅/相位物体经光瞳成像的相干像强度(``image2d``)。 · 示例: `poc_fourier_ptychography`, `poc_laser_line_speckle_floor`
- `laser_line_coherent` `无输入 → image2d` GPU: 无 — 照在粗糙表面上的光切法激光线,连同散斑一起成像(``image2d``)。 · 示例: `poc_laser_line_speckle_floor`, `poc_light_section_step_weld_floor`, `poc_weld_bead_profile`
- `speckle_field` `无输入 → image2d` GPU: 无 — 透过圆形光瞳观察粗糙表面得到的激光散斑强度(``image2d``)。 · 示例: `poc_laser_line_speckle_floor`
- `speckle_reduction` `无输入 → table` GPU: 无 — 散斑抑制后预测的对比度(``table``)。 · 示例: `poc_laser_line_speckle_floor`
- `speckle_statistics` `image2d → table` GPU: 有(许可列表) — 散斑强度图像的一阶与二阶统计量(``table``)。 · 示例: `poc_laser_line_speckle_floor`
- `triangulation_speckle_limit` `无输入 → table` GPU: 无 — 激光三角测量的散斑下限(``table``): ``δz = C λ / (2π sin u_obs sin θ)``。 · 示例: `poc_laser_line_speckle_floor`, `poc_weld_bead_profile`

#### optics / confocal (6)
- `chromatic_confocal_limits` `table → table` GPU: 无 — 由标定表以闭式给出测量范围、轴向分辨率、仍能返回光的最大倾角和最小膜厚。 · 示例: `poc_chromatic_confocal`
- `chromatic_confocal_peaks` `pairs → table` GPU: 无 — 以优于一个采样间隔的精度提取返回光谱的峰值波长(一条,或透明体正反两面的两条)。 · 示例: `poc_chromatic_confocal`, `poc_spectrometer_illumination`
- `chromatic_confocal_probe` `无输入 → table` GPU: 无 — 由物镜的处方生成波长 → 焦点位置的标定表(彩虹标尺的刻度)。 · 示例: `poc_chromatic_confocal`, `poc_spectrometer_illumination`
- `chromatic_confocal_readout` `table × table → table` GPU: 无 — 通过标定表把峰值波长换算回高度(z),若有两个峰则给出透明层的厚度。 · 示例: `poc_chromatic_confocal`, `poc_spectrometer_illumination`
- `chromatic_confocal_spectrum` `table → pairs` GPU: 无 — 由表面位置和层结构合成彩色共焦的返回光谱(正向模型)。 · 示例: `poc_chromatic_confocal`, `poc_spectrometer_illumination`
- `confocal_axial_response` `无输入 → pairs` GPU: 无 — 以 pairs 返回共焦显微镜的轴向响应 I(z)(相对离焦量 z [µm] 的检测强度)。 · 示例: `poc_chromatic_confocal`

#### optics / design (22)
- `chief_ray` `table → table` GPU: 无 — 追迹某一视场的主光线(穿过光阑中心)(``table``)。 · 示例: `lens_optimize_demo`, `poc_lens_solves_afocal`, `poc_lens_tolerancing`, `poc_optics_drawings`, `poc_photograph_through_prescription`, `poc_telecentric_metrology`
- `chromatic_shift` `table → table` GPU: 无 — 随波长变化的焦点移动、像高移动与光斑尺寸(``table``)。 · 示例: `lens_optimize_demo`, `poc_material_optical_library`, `poc_photograph_through_prescription`, `poc_zmx_public_verify`
- `example_system` `无输入 → table` GPU: 无 — 具名示例:``"singlet"``(平凸 BK7,f≈100)、``"doublet"``(胶合消色差,BK7/SF2,f≈100)、``"paraboloid"``(f/2 抛物面镜 —— 轴上无像差)、``"sphere_mirror"``(同曲率半径的球面)、``"asphere"``(平-双曲面 N-BK7 单透镜,朝物侧为平面,出射面圆锥系数 ``k = −n²`` —— 笛卡儿的无像差透镜,f/4 时 f≈100)、``"catalog_doublet"``(用真实 N-BK7 / N-SF2 Sellmeier 硝材的双胶合)。 · 示例: `anim3d_lens_aberrations`, `lens_calibration_loop_demo`, `lens_defect_dataset_demo`, `lens_design_demo`, `lens_optimize_demo`, `optimized_lens_tolerance_sensitivity`
- `glass` `无输入 → table` GPU: 无 — 由 d 线折射率 *nd* 与阿贝数 *vd* 构造色散介质。 · 示例: `lens_design_demo`, `lens_optimize_demo`, `poc_industrial_oct`, `poc_lens_global_search`, `poc_material_optical_library`, `poc_optics_drawings`
- `glass_catalog` `无输入 → table` GPU: 无 — 按名称查目录硝材(``table``);*name* 为 None 时返回名称列表。 · 示例: `lens_optimize_demo`, `poc_material_optical_library`, `poc_telecentric_metrology`
- `lens_system` `无输入 → table` GPU: 无 — 构建经过校验的逐面处方(其他所有算子消费的那个 ``table``)。 · 示例: `anim3d_lens_aberrations`, `lens_calibration_loop_demo`, `lens_defect_dataset_demo`, `lens_design_demo`, `lens_optimize_demo`, `optical_design_metrics`, `plenoptic_capture_pipeline`, `poc_chromatic_confocal`, `poc_lens_file_roundtrip`, `poc_lens_global_search`, `poc_lens_merit_operands`, `poc_lens_solves_afocal`, `poc_lens_tolerancing`, `poc_material_optical_library`, `poc_noncoaxial_optics`, `poc_optics_drawings`, `poc_photograph_through_prescription`, `poc_plenoptic_camera`, `poc_tdi_linescan`, `poc_telecentric_metrology`, `poc_zoom_configurations`
- `opd_map` `table → image2d` GPU: 无 — 出瞳上的光程差,以波长为单位(``image2d``)。 · 示例: `lens_design_demo`
- `opd_samples` `table → table` GPU: 无 — 光瞳网格采样点上的 OPD(波长):返回 ``(px, py, opd, valid)``。 · 示例: `anim3d_lens_aberrations`, `poc_lens_tolerancing`, `poc_noncoaxial_optics`
- `paraxial_trace` `table → table` GPU: 无 — 处方的一阶量:焦距、光瞳、像。 · 示例: `anim3d_lens_aberrations`, `lens_defect_dataset_demo`, `lens_design_demo`, `optical_design_metrics`, `poc_chromatic_confocal`, `poc_lens_file_roundtrip`, `poc_lens_global_search`, `poc_lens_merit_operands`, `poc_lens_solves_afocal`, `poc_material_optical_library`, `poc_noncoaxial_optics`, `poc_optics_drawings`, `poc_photograph_through_prescription`, `poc_plenoptic_camera`, `poc_tdi_linescan`, `poc_telecentric_metrology`, `poc_zmx_public_verify`, `poc_zoom_configurations`
- `ray_aiming` `table → table` GPU: 无 — 单个视场下瞳面光线到达光阑的情况:光线数、残差与光瞳范围(``table``)。 · 示例: `optical_design_metrics`
- `ray_bundle` `table → table` GPU: 无 — 追迹某一视场充满光瞳的光束;返回原始追迹结果以及 ``image_xy`` (N,2)、``chief_xy`` (2,)、``pupil`` (N,2) 归一化坐标和 ``opl0``(光线起点的光程偏移)。 · 示例: `anim3d_lens_aberrations`, `poc_lens_file_roundtrip`, `poc_lens_merit_operands`, `poc_lens_solves_afocal`, `poc_lens_tolerancing`, `poc_noncoaxial_optics`, `poc_photograph_through_prescription`, `poc_zmx_public_verify`
- `ray_fan` `table → pairs` GPU: 无 — 沿光瞳一条直径的横向光线像差(``pairs``)。 · 示例: `anim3d_lens_aberrations`, `lens_design_demo`
- `seidel_coefficients` `table → table` GPU: 无 — 三阶(Seidel)像差和,逐面与总计(``per_surface`` / ``total``)。 · 示例: `anim3d_lens_aberrations`, `lens_design_demo`, `poc_lens_file_roundtrip`, `poc_lens_solves_afocal`
- `sellmeier` `无输入 → table` GPU: 无 — 由三项 Sellmeier 常数构造色散介质(``table``)。 · 示例: `lens_optimize_demo`
- `set_vignetting` `table → table` GPU: 无 — 与“set vignetting”相同,求出消除所有被口径截断光线的渐晕系数(``table``)。 · 示例: `optical_design_metrics`
- `spot_diagram` `table → pairs` GPU: 无 — 某个视场点在像面上的横向光线交点。 · 示例: `lens_design_demo`, `poc_lens_file_roundtrip`
- `spot_stats` `table → table` GPU: 无 — 某个视场点的 RMS / 几何光斑半径(mm)与重心(``table``)。 · 示例: `anim3d_lens_aberrations`, `lens_design_demo`, `lens_optimize_demo`, `optical_design_metrics`, `poc_lens_solves_afocal`, `poc_photograph_through_prescription`, `poc_zmx_public_verify`
- `thick_lens` `无输入 → table` GPU: 无 — 空气中厚透镜的闭式解:EFL、后/前焦距、主点。 · 示例: `lens_design_demo`, `poc_material_optical_library`
- `tolerance_analysis` `table → table` GPU: 无 — 制造公差的蒙特卡罗 + 逐参数灵敏度(``table``)。 · 示例: `lens_design_demo`, `poc_optics_drawings`
- `wavefront_from_opd` `table → table` GPU: 无 — OPD 图 → Zernike 系数(波)→ RMS / PV / Strehl,一次完成(``table``)。 · 示例: `anim3d_lens_aberrations`, `lens_design_demo`
- `with_aiming` `table → table` GPU: 无 — 返回设置了光线瞄准模式和/或渐晕系数的 *system* 副本(``table``)。 · 示例: `optical_design_metrics`
- `with_wavelength` `table → table` GPU: 无 — 在另一波长下评估的同一处方(重新解析折射率;默认 F 线)。 · 示例: `anim3d_lens_aberrations`, `poc_chromatic_confocal`, `poc_lens_file_roundtrip`, `poc_lens_global_search`, `poc_lens_merit_operands`, `poc_material_optical_library`, `poc_photograph_through_prescription`

#### optics / drawing (9)
- `drawing_dxf` `table → text` GPU: 无 — 把图写成 DXF R12(AC1009)的 ASCII(``text``)—— 只用标准库写出 CAD 可读入的最小完整结构。 · 示例: `poc_optics_drawings`
- `drawing_raster` `table → rgbimage` GPU: 无 — 把图渲染为 RGB 图像(uint8,(H, W, 3))(``rgbimage``)—— 使用 matplotlib(可选依赖),纸面大小 × *dpi*。 · 示例: `poc_lens_file_roundtrip`, `poc_noncoaxial_optics`, `poc_optics_drawings`
- `drawing_svg` `table → text` GPU: 无 — 把图写成 SVG 字符串(``text``)—— 只用标准库,坐标为实物毫米,纸面大小 = 图 × 比例。 · 示例: `poc_optics_drawings`
- `dxf_entities` `text → table` GPU: 无 — 把 DXF(R12 的 ASCII,也接受 R2000 以后的 ``LWPOLYLINE``)的 ENTITIES 读回为图的要素(``table``)。 · 示例: `poc_optics_drawings`
- `lens_element_drawing` `table → table` GPU: 无 — 单透镜的制造图(``table``,图的 dict)—— 采用 ISO 10110 的标注,含截面图、三栏数据表和标题栏。 · 示例: `poc_optics_drawings`
- `lens_section_drawing` `table → table` GPU: 无 — 透镜的子午截面图(``table``,图的 dict)—— 处方的各面、边缘、光阑、像面,按视场分色的实际光线和尺寸。 · 示例: `poc_lens_file_roundtrip`, `poc_optics_drawings`
- `noncoaxial_drawing` `table → table` GPU: 无 — 折转系统的截面图/安装图(``table``,图的 dict)——把 ``raytrace3d`` 系统的面、反射镜、分束器、像面与光线以全局坐标投影到子午面绘制。 · 示例: `poc_noncoaxial_optics`
- `svg_entities` `text → table` GPU: 无 — 把 SVG(``drawing_svg`` 写出的形式:``line`` / ``polyline`` / ``polygon`` / ``circle`` / M…A… 与 M…L… 的 ``path`` / ``text``)读回为图的要素(``table``),并把 y 的符号恢复为图模型的朝向(y 向上)。 · 示例: `poc_optics_drawings`, `poc_real_sem_metal_layer`
- `vision_setup_drawing` `table → table` GPU: 无 — 成像系统的布置图(``table``,图的 dict)—— 由 ``optscene.vision_layout`` 绘制侧视图和俯视图。 · 示例: `poc_optics_drawings`

#### optics / fiber (7)
- `fiber_bundle_coupling` `无输入 → table` GPU: 无 — 进入光导(光纤束)并射出的光的比例。 · 示例: `poc_fiber_light_guide`
- `fiber_lp_modes` `无输入 → table` GPU: 无 — 弱导波阶跃型光纤的 LP_lm 模:求解特征方程,返回各模的 u、w 与归一化传播常数 b(``table``)。 · 示例: `poc_fiber_light_guide`
- `fiber_mode_field_diameter` `无输入 → table` GPU: 无 — LP01 的模场直径(MFD,µm)—— 与精确场**重叠最大的高斯**的 1/e² 直径。 · 示例: `poc_fiber_light_guide`
- `fiber_numerical_aperture` `无输入 → table` GPU: 无 — 数值孔径 NA = √(n_core² − n_clad²)、接收半角(度)与相对折射率差 Δ。折射率为数值或材料名。 · 示例: `poc_fiber_light_guide`
- `fiber_v_number` `无输入 → table` GPU: 无 — 归一化频率 V = 2π a NA / λ,以及是否为单模(V < 2.4048 = J0 的第一个零点)。 · 示例: `poc_fiber_light_guide`
- `material_group_index` `无输入 → pairs` GPU: 无 — 群折射率 n_g(λ) = n − λ dn/dλ,以 ``pairs``(λ [nm],n_g)返回(材料为 ``materials`` 中的名称)。 · 示例: `poc_fiber_light_guide`
- `material_gvd` `无输入 → pairs` GPU: 无 — 材料色散参数 D(λ) = −(λ/c) d²n/dλ²,单位 ps/(nm·km),以 ``pairs``(λ [nm],D)返回。 · 示例: `poc_fiber_light_guide`

#### optics / film (5)
- `film_color` `无输入 → table` GPU: 无 — 膜厚变化时的干涉色(晶圆色卡),以 D65 照明和 CIE 1931 配色函数观察的颜色。 · 示例: `poc_thin_film_reflectometry`
- `film_thickness_fft` `pairs → table` GPU: 无 — 由反射光谱干涉条纹的周期求膜厚(FFT 法)。色散用材料表的 n(λ) 校正。 · 示例: `poc_thin_film_reflectometry`
- `film_thickness_fit` `pairs → table` GPU: 无 — 将传输矩阵模型拟合到反射光谱以求膜厚(非线性最小二乘:全局网格搜索后局部精化)。 · 示例: `poc_thin_film_reflectometry`
- `film_thickness_map` `images → table` GPU: 无 — 由光谱图像(各波段反射率)或 RGB 图像求逐像素膜厚(查找表 + 抛物线精化)。 · 示例: `poc_thin_film_reflectometry`
- `multilayer_reflectance` `无输入 → pairs` GPU: 无 — 多层膜的光谱反射率(或透射率、吸收率),以 pairs(λ nm, 值)返回。特性矩阵(传输矩阵)的精确解。 · 示例: `poc_simcal_thin_film`, `poc_thin_film_reflectometry`

#### optics / finish (5)
- `blast_normals` `normalmap → normalmap` GPU: 有(许可列表) — 把喷砂 / 哑光面的**无方向微观凹凸**写进法线。 · 示例: `machined_metal_and_materials`, `poc_illumination_cone_vs_na`, `poc_telecentric_metrology`
- `finish_catalog` `无输入 → table` GPU: 无 — 表面处理名 → 默认参数表(αx, αy, grain)。 · 示例: `machined_metal_and_materials`
- `finish_shade` `normalmap → rgbimage` GPU: 无 — 按**材质 × 表面处理**为金属面着色 → 线性 sRGB (H, W, 3)。 · 示例: `machined_metal_and_materials`, `poc_telecentric_metrology`
- `micro_normals` `normalmap → normalmap` GPU: 无 — 把加工痕迹本身**刻进法线**(车削进给纹、滚花的凸脊)。 · 示例: `machined_metal_and_materials`, `poc_illumination_cone_vs_na`, `poc_telecentric_metrology`
- `tangent_field` `无输入 → normalmap` GPU: 无 — 把**纹路的方向**做成 (H, W, 3) 的切向场。 · 示例: `machined_metal_and_materials`

#### optics / fpm (6)
- `fp_capture` `image2d × image2d → table` GPU: 有(许可列表) — 合成由 LED 阵列斜向照明拍摄的一组低分辨率图像(``table``,kind="fp_stack")。 · 示例: `poc_fourier_ptychography`
- `fp_design` `无输入 → table` GPU: 无 — 在**拍摄之前**用闭式求出傅里叶叠层成像的性能(``table``):合成 NA、截止周期、频谱重叠率、LED 数量与像素采样。 · 示例: `poc_fourier_ptychography`
- `fp_element_contrast` `image2d × table → table` GPU: 无 — 测量 USAF 每个要素三条条纹的调制度,读出图像分辨到哪一个要素(``table``)。 · 示例: `poc_fourier_ptychography`
- `fp_reconstruct` `table → table` GPU: 无 — 从一组低分辨率图像恢复高分辨率的振幅与相位(``table``,kind="fp_result")。不收敛则拒绝。 · 示例: `poc_fourier_ptychography`
- `fp_stack_from_images` `volume × signal × signal → table` GPU: 无 — 把装置或公开数据的一组图像转换为本族的表(``table``,kind="fp_stack")。 · 示例: `poc_fourier_ptychography`
- `fp_usaf_target` `无输入 → table` GPU: 无 — 由 USAF 1951 分辨率板元素排列而成的物体(``table``):振幅(条纹为暗)、相位(条纹相位为 ``phase_rad``)或两者兼有。 · 示例: `poc_fourier_ptychography`

#### optics / geometric (5)
- `abcd_matrix` `table → matrix` GPU: 无 — 把近轴系统合成为一个 2x2 光线传输(ABCD)矩阵。 · 示例: `optics_imaging`
- `abcd_trace` `matrix → table` GPU: 无 — 让一条近轴光线通过 ABCD 矩阵传播。 · 示例: `optics_imaging`
- `depth_of_field` `无输入 → table` GPU: 无 — 摄影景深:近界、远界与超焦距。 · 示例: `lightfield_depth`, `optics_imaging`, `poc_photograph_through_prescription`
- `relative_illumination` `无输入 → pairs` GPU: 无 — 自然渐晕:像面照度随视场角的相对值。 · 示例: `optics_imaging`, `poc_photograph_through_prescription`, `poc_search_sweep_width`, `poc_tdi_linescan`
- `thin_lens` `无输入 → table` GPU: 无 — 高斯薄透镜成像:像落在哪里、有多大。 · 示例: `lightfield_depth`, `optics_imaging`

#### optics / glassbody (4)
- `beer_lambert_transmittance` `signal → signal` GPU: 仅在链中(许可列表) — Beer–Lambert 内部透过率 T = exp(−σ·L)。有色玻璃与厚玻璃的偏绿。 · 示例: `glass_and_mirror_optics`, `poc_pv_thermal_survey`, `poc_thermal_radiometry`, `poc_water_transparent_media`
- `prism_min_deviation_deg` `signal → signal` GPU: 无 — 棱镜的最小偏向角 [deg]。因**实际硝材的色散**随波长变化 = 出现彩虹的原因。 · 示例: `glass_and_mirror_optics`
- `refract_rays` `points × points → points` GPU: 无 — Snell 折射的向量形式。**逐条光线判定全反射**,返回(方向, TIR 掩码)。 · 示例: `glass_and_mirror_optics`, `poc_water_transparent_media`
- `slab_transmittance` `signal → signal` GPU: 有(许可列表) — 平行平板(窗玻璃)的透过率。含**两面间的多次反射**与内部吸收。 · 示例: `glass_and_mirror_optics`, `machined_metal_and_materials`

#### optics / grating_interf (8)
- `darkfield_scatter_relation` `无输入 → table` GPU: 无 — 暗场 D(可见度之比)与散射角分布宽度 σ 之间的换算(高斯散射的公开公式)。 · 示例: `grating_interferometry`
- `dpc_integrate` `table → table` GPU: 无 — 将微分相位(条纹相位偏移 φ)沿光栅的灵敏方向积分,还原为波前相位 Φ [rad]。 · 示例: `grating_interferometry`, `poc_grating_interferometry`
- `grating_step_period_estimate` `images → table` GPU: 无 — 由相位步进图像序列估计「一个周期包含多少步」(P),取正弦拟合残差的最小值。 · 示例: `grating_interferometry`, `poc_grating_interferometry`
- `grating_stepping_simulate` `image2d → images` GPU: 仅在链中(许可列表) — 由透射、微分相位、暗场 3 幅图生成相位步进的图像序列 (N, H, W)(正向模型)。 · 示例: `grating_interferometry`, `poc_grating_interferometry`
- `grating_three_image_retrieve` `images × images → table` GPU: 有(许可列表) — 从两组相位步进序列(有样品、无样品)中分离出透射、微分相位、暗场 3 幅图。 · 示例: `grating_interferometry`, `poc_grating_interferometry`
- `talbot_carpet` `无输入 → table` GPU: 无 — 塔尔博特地毯:以衍射级次之和的闭式给出二值光栅(π 相位 / π/2 相位 / 吸收)后方的强度 I(x, z)。 · 示例: `grating_interferometry`, `poc_grating_interferometry`
- `talbot_grating_design` `无输入 → table` GPU: 无 — 光栅干涉仪的几何:第 1 光栅自成像的距离(分数塔尔博特距离)、条纹与分析光栅的周期、源光栅的周期(闭式)。 · 示例: `grating_interferometry`, `poc_grating_interferometry`
- `talbot_source_visibility` `无输入 → table` GPU: 无 — 光源尺寸与源光栅(Lau 条件)使条纹可见度降低为多少倍(闭式,非相干叠加)。 · 示例: `grating_interferometry`, `poc_grating_interferometry`

#### optics / hdr (8)
- `camera_response_debevec` `images → table` GPU: 无 — 用 Debevec 与 Malik 的最小二乘由曝光序列求相机的逆响应(``table``)。 · 示例: `poc_hdr_glossy_metal_inspection`
- `camera_response_linear` `无输入 → table` GPU: 无 — 线性传感器的逆响应:``X = (Z − offset) / gain``(``table``)。 · 示例: `poc_hdr_glossy_metal_inspection`
- `camera_response_robertson` `images → table` GPU: 无 — 用 Robertson、Borman 与 Stevenson 的交替估计求相机的逆响应(``table``)。 · 示例: `poc_hdr_glossy_metal_inspection`
- `exposure_fusion_mertens` `images → image2d` GPU: 无 — 把曝光序列直接融合为一张曝光良好的图像(``image2d``;也接受 RGB 序列)。 · 示例: `poc_hdr_glossy_metal_inspection`
- `hdr_dynamic_range` `无输入 → table` GPU: 无 — HDR 拍摄动态范围的实测值(EMVA 1288 定义)及其闭式解(``table``)。 · 示例: `poc_hdr_glossy_metal_inspection`
- `hdr_exposure_series_simulate` `image2d → images` GPU: 无 — 用 EMVA 1288 传感器模型把辐射亮度已知的场景拍成曝光序列(``images``)。 · 示例: `poc_hdr_glossy_metal_inspection`
- `hdr_merge` `images → image2d` GPU: 无 — 把曝光序列合成为相对辐射亮度图(``image2d``)。 · 示例: `poc_hdr_glossy_metal_inspection`
- `hdr_radiance_error` `image2d × image2d → table` GPU: 无 — 估计的辐射亮度图相对真值的误差(拟合一个比例因子后)(``table``)。 · 示例: `poc_hdr_glossy_metal_inspection`

#### optics / illumination (14)
- `coaxial_illumination` `无输入 → table` GPU: 无 — 同轴落射照明(半透半反镜):往返 T*R 的收支与相机看到的像(``table``)。 · 示例: `poc_spectrometer_illumination`
- `defect_contrast` `table → table` GPU: 无 — 某照明下形貌缺陷与色素缺陷的对比度(``table``)。 · 示例: `illumination_design_demo`
- `illumination_design` `无输入 → table` GPU: 无 — 针对某个「表面 / 缺陷」组合给标准照明族排序(``table``)。 · 示例: `illumination_design_demo`, `poc_solder_fillet_aoi`
- `illumination_field` `table → image2d` GPU: 无 — 通过近轴反向追迹到光源,求照明系统在标本上的辐照度(``image2d``)。 · 示例: `poc_document_scan`, `poc_spectrometer_illumination`
- `illumination_train` `无输入 → table` GPU: 无 — 以近轴方式排布显微镜照明系统(``kohler`` 或 ``critical``)(``table``)。 · 示例: `poc_spectrometer_illumination`
- `illumination_uniformity` `image2d → table` GPU: 无 — 辐照度图的均匀性指标(``table``)。 · 示例: `illumination_design_demo`
- `irradiance_map` `table → image2d` GPU: 无 — 零件平面上的辐照度(``image2d``,单位为 intensity / mm²)。 · 示例: `illumination_design_demo`
- `light_source` `无输入 → table` GPU: 无 — 标准机器视觉照明族的发光点集合(``table``)。 · 示例: `illumination_design_demo`, `poc_pocket_interreflection`, `poc_pod_lighting`, `virtual_machine_vision`
- `lighting_sweep` `无输入 → pairs` GPU: 无 — 缺陷对比度随环形照明仰角的变化(``pairs``)。 · 示例: `illumination_design_demo`
- `solid_angle_boundaries` `table → table` GPU: 无 — 光滑镜面小面明暗切换倾角的闭式边界(``table``)。 · 示例: `poc_illumination_cone_vs_na`
- `solid_angle_brightness` `table → table` GPU: 无 — 光滑或粗糙镜面小面的亮度随其倾角的变化(``table``)。 · 示例: `poc_illumination_cone_vs_na`
- `solid_angle_light` `无输入 → table` GPU: 无 — 由到达每一点的光锥(半角与方向)定义的照明(``table``)。 · 示例: `poc_illumination_cone_vs_na`
- `solid_angle_render` `normalmap × table → image2d` GPU: 无 — 在光锥照明下、经 NA 为 *view_na* 的镜头拍摄的法线图图像(``image2d``)。 · 示例: `poc_illumination_cone_vs_na`
- `solid_angle_sweep` `无输入 → pairs` GPU: 无 — 小面与平坦背景的对比度随照明光锥半角的变化(``pairs``)。 · 示例: `poc_illumination_cone_vs_na`

#### optics / imaging (11)
- `edge_spread` `image2d → table` GPU: 无 — 由倾斜边缘(ISO 12233)的 ROI 构建比像素更细的 ESF。 · 示例: `poc_pixel_shift`, `poc_veiling_glare`
- `encircled_energy` `image2d → pairs` GPU: 无 — 点扩散函数(PSF)的环围能量:半径为 r 的圆内所含能量的比例。 · 示例: `optical_design_metrics`, `poc_zoom_configurations`
- `energy_radii` `image2d → table` GPU: 无 — 包含点扩散函数(PSF)指定能量比例的半径(``table``)。 · 示例: `optical_design_metrics`
- `ensquared_energy` `image2d → pairs` GPU: 有(许可列表) — 点扩散函数(PSF)的方形能量:半宽为 w 的正方形内所含能量的比例。 · 示例: `optical_design_metrics`
- `mtf50` `pairs → measurement` GPU: 无 — SFR(pairs：频率，值)**首次**低于 0.5 时的频率(线性插值)。若从未低于 0.5，则 ``ValueError`` (不会把“直到可测范围上限都在 0.5 以上”默默当作最大值返回)。 · 示例: `poc_lens_file_roundtrip`, `poc_pixel_shift`, `poc_veiling_glare`
- `mtf_diffraction` `无输入 → pairs` GPU: 无 — 圆形光瞳的衍射极限 MTF(闭式)。 · 示例: `optics_imaging`, `poc_lens_file_roundtrip`, `poc_pixel_shift`, `poc_slanted_edge_sfr_limits`, `poc_veiling_glare`
- `mtf_tangential_sagittal` `image2d → table` GPU: 有(许可列表) — 由点扩散函数(PSF)的二维变换分别给出子午(切向)与弧矢 MTF(``table``)。 · 示例: `optical_design_metrics`
- `psf_to_mtf` `image2d → pairs` GPU: 有(许可列表) — 由实测点扩散函数得到径向平均的 MTF。 · 示例: `optics_imaging`, `poc_lens_file_roundtrip`, `poc_veiling_glare`, `poc_zmx_public_verify`
- `sfr_from_edge` `table → pairs` GPU: 无 — 由 ESF 求出 SFR(由边缘测得的 MTF)。 · 示例: `poc_pixel_shift`, `poc_veiling_glare`
- `veiling_glare_index` `image2d × image2d × image2d → table` GPU: 无 — 杂散光(遮蔽眩光)指数：黑点中心亮度的平均 / 白底亮度的平均(ISO 9358 的思路)。 · 示例: `poc_veiling_glare`
- `wavefront_stats` `table → table` GPU: 无 — 由 Zernike 展开得到的波前误差统计:RMS、PV 与 Strehl。 · 示例: `optics_imaging`, `poc_zernike_aberrations`

#### optics / imaging_sim (6)
- `calibration_views` `table → table` GPU: 无 — 透过所设计的镜头看到的平面标定靶合成视图(``table``)。 · 示例: `lens_calibration_loop_demo`
- `defect_dataset` `无输入 → table` GPU: 无 — 透过所设计镜头的合成缺陷图像,附对齐的掩码(``table``)。 · 示例: `lens_defect_dataset_demo`
- `distortion_map` `table → table` GPU: 无 — 实际主光线高与近轴主光线高的对照,以及重映射网格(``table``)。 · 示例: `lens_defect_dataset_demo`, `poc_photograph_through_prescription`, `poc_zmx_public_verify`
- `psf_from_opd` `table → image2d` GPU: 无 — 带真实像差的光瞳的衍射 PSF(``image2d``,总和为 1)。 · 示例: `lens_defect_dataset_demo`, `optical_design_metrics`, `poc_zmx_public_verify`
- `render_through_lens` `image2d × table → image2d` GPU: 无 — 把理想辐照度图像渲染成 *system* 背后的传感器会记录到的样子(``image2d``)。 · 示例: `lens_defect_dataset_demo`, `poc_zmx_public_verify`
- `through_focus_mtf` `table → table` GPU: 无 — 像面位置变化时,指定空间频率下的子午与弧矢 MTF(``table``)。 · 示例: `lensfile_tolerance_worst_mtf`, `optical_design_metrics`

#### optics / interface (4)
- `brewster_angle_deg` `无输入 → measurement` GPU: 无 — 布儒斯特角 [deg] = atan(n2/n1)。在该角度 p 偏振的反射严格为 0。 · 示例: `example_polarization_metal`, `glass_and_mirror_optics`
- `critical_angle_deg` `无输入 → measurement` GPU: 无 — 全反射临界角 [deg] = asin(n2/n1)。若非 n1 > n2 则 ValueError(不存在)。 · 示例: `glass_and_mirror_optics`
- `fresnel_conductor` `signal → signal` GPU: 有(许可列表) — 金属(复折射率 n + ik)界面的反射率。入射侧假设为真空/空气。 · 示例: `example_polarization_metal`, `glass_and_mirror_optics`, `poc_material_optical_library`, `poc_polarization_specular`
- `fresnel_dielectric` `signal → signal` GPU: 有(许可列表) — 介质界面的 Fresnel 反射率(支持数组,含全反射)。 · 示例: `example_polarization_metal`, `glass_and_mirror_optics`, `poc_phase_measuring_deflectometry`, `poc_polarization_specular`, `poc_pv_thermal_survey`, `poc_shape_from_polarization`

#### optics / itof (8)
- `itof_capture` `depth → table` GPU: 无 — 距离图 → 间接 ToF 的原始信号(每个调制频率 K 个相位步进的累积桶,单位为电子数)。返回 ``table``(``dict``)。 · 示例: `poc_3d_sensor_modalities`, `poc_itof_multifreq`
- `itof_flying_pixel_mask` `depth → image2d` GPU: 无 — 距离图 → 飞点像素(**悬浮在**前景与背景**之间**的像素)的标记 ``(H, W)``(1.0 = 悬浮)。 · 示例: `poc_3d_sensor_modalities`, `poc_itof_multifreq`, `tof_realdata`
- `itof_multipath_separate` `table → table` GPU: 无 — 在等间隔多频率下测得的相量 → 各路径的距离与强度(矩阵束法)。返回 ``table``。 · 示例: `poc_itof_multifreq`
- `itof_noise_budget` `无输入 → table` GPU: 无 — 间接 ToF 距离噪声的闭式解(单像素、单频率、等间隔 K 步)。返回 ``table``。 · 示例: `poc_3d_sensor_modalities`, `poc_itof_multifreq`
- `itof_phase_amplitude` `table → table` GPU: 无 — K 步原始信号 → 相位、振幅、偏移、折返距离以及逐像素的距离噪声估计(``table``)。 · 示例: `poc_3d_sensor_modalities`, `poc_itof_multifreq`
- `itof_unwrap_error_rate` `无输入 → table` GPU: 无 — 多频解包裹(最大似然解码)判错周期序号(第几周)的概率估计。返回 ``table``。 · 示例: `poc_itof_multifreq`
- `itof_unwrap_multifreq` `table → table` GPU: 无 — 多个频率的相位 → 距离(多频解包裹)。返回 ``table``。 · 示例: `poc_itof_multifreq`
- `itof_wiggling_correct` `table → table` GPU: 无 — 校正了谐波引起的周期误差(wiggling)后的相位与距离。返回 ``table``。 · 示例: `poc_itof_multifreq`

#### optics / lensconfig (5)
- `lens_add_configuration` `table → table` GPU: 无 — 返回追加了一个构型的 *system* 副本(``table``)。 · 示例: `poc_zoom_configurations`
- `lens_configuration_metrics` `table → table` GPU: 无 — 按构型逐个列出一项指标(EFL、后焦距、RMS 光斑、MTF、环围能量)(``table``)。 · 示例: `poc_zoom_configurations`
- `lens_configuration_table` `table → table` GPU: 无 — 返回多构型表(行 = 随构型变化的量,列 = 构型)(``table``)。 · 示例: `poc_zoom_configurations`
- `lens_configurations` `table → table` GPU: 无 — 将多构型处方解析为每个构型一个 ``lens_system`` 的列表(``table``)。 · 示例: `poc_zoom_configurations`
- `lens_with_configuration` `table → table` GPU: 无 — 返回多构型处方的第 k 个构型(从 0 起)解析后的 ``lens_system``(``table``)。 · 示例: `poc_zoom_configurations`

#### optics / lensfile (4)
- `lens_file_read` `无输入 → table` GPU: 无 — 将 ``.zmx`` 逐次透镜处方读入 Fullseye 的处方(``table``)。 · 示例: `lensfile_tolerance_worst_mtf`, `optical_design_metrics`, `poc_lens_file_roundtrip`, `poc_lens_solves_afocal`, `poc_zmx_public_verify`, `poc_zoom_configurations`
- `lens_file_report` `无输入 → table` GPU: 无 — 不导入就清点 ``.zmx`` 文件:哪些会被读取 / 忽略 / 拒绝(``table``)。 · 示例: `poc_lens_file_roundtrip`
- `lens_file_system` `table → table` GPU: 无 — 把导入的处方变成某一视场、某一波长下的 ``raytrace.lens_system``(``table``)。 · 示例: `poc_lens_file_roundtrip`
- `lens_file_write` `table → table` GPU: 无 — 把处方写成 :func:`lens_file_read` 和设计软件都能读的 ``.zmx`` 文本(``table``)。 · 示例: `poc_lens_file_roundtrip`, `poc_lens_solves_afocal`, `poc_zoom_configurations`

#### optics / lensglobal (3)
- `glass_nearest` `无输入 → table` GPU: 无 — 返回与 (n_d, V_d) 最接近的 k 种目录玻璃及其距离(``table``)。 · 示例: `poc_lens_global_search`
- `lens_global_search` `table → table` GPU: 无 — 用多起点局部优化(lensopt.optimize_lens)收集局部最优解,按 merit 顺序返回(``table``)。 · 示例: `poc_lens_global_search`
- `lens_substitute_glasses` `table → table` GPU: 无 — 将系统中的模型玻璃 (n_d, V_d) 替换为第 k 近的目录玻璃(``table``)。 · 示例: `poc_lens_global_search`

#### optics / lensmerit (6)
- `merit_boundary_operands` `table → table` GPU: 无 — 把制造上的边界变成表中的行:每块玻璃的边缘厚度、中心厚度和空气间隔的范围(``table``)。 · 示例: `poc_lens_merit_operands`
- `merit_contributions` `table → table` GPU: 无 — 显示哪些行主导评价函数:按贡献从大到小的百分比表(``table``)。 · 示例: `poc_lens_merit_operands`
- `merit_default` `table → table` GPU: 无 — 把默认评价函数组成操作数表:整个光瞳的光线行加上 EFL 的保持(``table``)。 · 示例: `optimized_lens_tolerance_sensitivity`, `poc_lens_merit_operands`
- `merit_evaluate` `table → table` GPU: 无 — 把操作数表应用到处方上,返回每一行的值、目标、权重、贡献及其占比(``table``)。 · 示例: `poc_lens_merit_operands`
- `merit_operands_list` `无输入 → table` GPU: 无 — 列出评价函数的操作数(operand):名称、含义、单位和参数(``table``)。 · 示例: `poc_lens_merit_operands`
- `optimize_lens_operands` `table → table` GPU: 无 — 用 LM 法最小化操作数表的评价函数,玻璃也可以作为变量(``table``)。 · 示例: `optimized_lens_tolerance_sensitivity`, `poc_lens_merit_operands`

#### optics / lensrender (8)
- `bokeh_shape` `table → table` GPU: 无 — 点光源失焦像(虚化)的形状——光瞳像的交集,即猫眼形 -> 字典。 · 示例: `poc_photograph_through_prescription`
- `exit_pupil_samples` `table → table` GPU: 无 — 在 *system* 的出瞳上取样点(位置与半径来自近轴追迹)-> 字典。 · 示例: `poc_photograph_through_prescription`
- `lens_scene` `无输入 → table` GPU: 无 — 构建并校验供 render_scene_through_lens 使用的简单三维场景(平面、球、网格、光源)-> 字典(``scene`` 表)。 · 示例: `plenoptic_capture_pipeline`, `poc_photograph_through_prescription`, `poc_plenoptic_camera`
- `render_compare_prescriptions` `无输入 → table` GPU: 无 — 用两个或更多处方拍摄同一场景,并把每张图像的质量列成表 -> 字典。 · 示例: `poc_photograph_through_prescription`
- `render_ghost_overlay` `table → table` GPU: 无 — 明亮点光源的二次反射鬼像,以传感器上的电子数表示 -> 字典。 · 示例: `poc_photograph_through_prescription`
- `render_scene_through_lens` `table → table` GPU: 无 — 透过处方 *system* 的镜头拍摄 ``lens_scene``:从传感器一侧的光线追迹 -> 字典。 · 示例: `poc_photograph_through_prescription`
- `scene_radiance` `无输入 → table` GPU: 无 — 物空间光线击中 ``lens_scene`` 时所带的辐亮度 -> 字典。 · 示例: `poc_dehazing`
- `trace_sensor_rays` `table → table` GPU: 无 — 从传感器上的点经出瞳上的点,把光线**逆向**追迹到物空间 -> 字典。 · 示例: `poc_photograph_through_prescription`

#### optics / lenssolve (9)
- `afocal_system` `table → table` GPU: 无 — 构造像空间为平行光的系统(望远镜、扩束器):给已有系统加上 afocal 标记,或生成由两片理想透镜构成的望远镜(``table``)。 · 示例: `poc_lens_solves_afocal`
- `lens_afocal_report` `table → table` GPU: 无 — afocal 系统的角放大率、出瞳和各视场的角度像差(角分)(``table``)。 · 示例: `poc_lens_solves_afocal`
- `lens_apply_solves` `table → table` GPU: 无 — 返回已解出所有解(solve)的处方副本:规则保留,R / t 变为解出的值(``table``)。 · 示例: `poc_lens_solves_afocal`
- `lens_image_surface` `table → table` GPU: 无 — 返回像面为曲面的处方:光线与该面相交,光斑、OPD 和 MTF 都在该面上测量(``table``)。 · 示例: `poc_lens_solves_afocal`
- `lens_petzval_radius` `table → table` GPU: 无 — 像空间的佩茨瓦尔半径:消除三阶场曲的像面曲率半径(``table``)。 · 示例: `poc_lens_solves_afocal`
- `lens_solve_clear` `table → table` GPU: 无 — 去掉某个面的解(solve)规则:解出的值作为普通数值保留(``table``)。 · 示例: `poc_lens_solves_afocal`
- `lens_solve_set` `table → table` GPU: 无 — 给某个面加上解(solve)的规则,并返回解出后的处方(``table``)。 · 示例: `poc_lens_solves_afocal`
- `lens_solves_list` `table → table` GPU: 无 — 列出现有的解(solve):规则、解出的值、达到的量及误差(``table``)。 · 示例: `poc_lens_solves_afocal`
- `lens_zmx_solves_roundtrip` `table → table` GPU: 无 — 把解(solve)写入 ``.zmx``,读回后再写一次:检查是否为不动点(``table``)。 · 示例: `poc_lens_solves_afocal`

#### optics / light_section (13)
- `laser_line_center_centroid` `image2d → table` GPU: 无 — 按列用亮度重心以亚像素精度求明亮激光条纹的中心(``table``)。 · 示例: `poc_3d_sensor_modalities`, `poc_weld_bead_profile`
- `laser_line_center_gauss` `image2d → table` GPU: 无 — 按列用高斯拟合(对 ``ln I`` 的加权抛物线)以亚像素精度求光条中心(``table``)。 · 示例: `poc_light_section_step_weld_floor`
- `laser_line_center_steger` `image2d → table` GPU: 无 — 用 Steger 的 Hessian 方法求线中心的亚像素位置(``table``)。 · 示例: `poc_light_section_step_weld_floor`
- `light_plane_calibrate` `table × table × matrix → table` GPU: 无 — 由照在已知平面上的光条拟合激光平面 ``n · X = d``(相机坐标)(``table``)。 · 示例: `poc_light_section_step_weld_floor`
- `light_section_floor_sweep` `无输入 → table` GPU: 无 — 扫描一个量,返回高度不确定度的仿真值与闭式解(``table``)。 · 示例: `poc_light_section_step_weld_floor`
- `light_section_height_map` `images × table → depth` GPU: 无 — 由扫描得到 (帧, 图像列) 的高度图(``depth``,NaN = 无法测量)。 · 示例: `poc_light_section_step_weld_floor`
- `light_section_profile` `table × table → points` GPU: 无 — 把光条中心三角测量为三维点:视线 ∩ 激光平面(``points``)。 · 示例: `poc_light_section_step_weld_floor`
- `light_section_render` `table × pairs → image2d` GPU: 无 — 装置的相机所见、照在表面截面上的激光条纹图像(``image2d``)。 · 示例: `poc_light_section_step_weld_floor`
- `light_section_rig` `无输入 → table` GPU: 无 — 几何已知的光切断装置(``table``):针孔相机 + 激光平面。 · 示例: `poc_light_section_step_weld_floor`
- `light_section_scan` `images × table → points` GPU: 无 — 扫描:第 ``k`` 帧时工件已移动 ``k · step_mm`` → 工件坐标系中的一个点云(``points``)。 · 示例: `poc_light_section_step_weld_floor`
- `light_section_speckle_floor` `无输入 → table` GPU: 无 — 并列给出光切断高度的散斑下限的仿真值与闭式解(``table``)。 · 示例: `poc_3d_sensor_modalities`, `poc_light_section_step_weld_floor`
- `light_section_targets` `table → table` GPU: 无 — 把已知的水平面 ``Z = h``(量块、台阶、基准面)表示为相机坐标系中的平面(``table``)。 · 示例: `poc_light_section_step_weld_floor`
- `light_section_uncertainty_budget` `无输入 → table` GPU: 无 — 以 GUM 表给出光切断高度的不确定度预算(``table``)。 · 示例: `poc_light_section_step_weld_floor`

#### optics / light_transport (11)
- `form_factors_2d` `table → matrix` GPU: 无 — 用 Hottel 交叉线法则的闭式解,求凹形二维(拉伸体)截面面片之间的角系数(``matrix``)。 · 示例: `poc_3d_sensor_modalities`, `poc_interreflection_fringe_error`, `poc_itof_multifreq`
- `fringe_multipath_phase_error` `无输入 → table` GPU: 无 — 直接条纹相量与全局相量相加时测得的相位 arg(a1 e^{iφ1} + a2 e^{iφ2})、相对 φ1 的偏差,以及最坏值 asin(a2/a1)(``table``)。 · 示例: `poc_interreflection_fringe_error`
- `groove_profile` `无输入 → table` GPU: 无 — 把凹形截面(V 形槽、圆弧槽、圆角焊脚或任意下凹折线)划分为面片,每个面片对应一列相机像素(``table``)。 · 示例: `converge_tour`, `poc_3d_sensor_modalities`, `poc_interreflection_fringe_error`, `poc_itof_multifreq`
- `high_frequency_patterns` `无输入 → images` GPU: 无 — 平移的高频投影图案:点亮率为 α 的二值条纹、棋盘格,或相移正弦(一个或多个周期)(``images``)。 · 示例: `poc_interreflection_fringe_error`
- `micro_phase_decode` `images → table` GPU: 有(许可列表) — 把窄带高频条纹组(微相移,Gupta & Nayar 2012)解码为绝对投影仪坐标,用前两个周期的拍频确定条纹级次(``table``)。 · 示例: `poc_interreflection_fringe_error`
- `predict_fringe_phase_error` `table → table` GPU: 无 — 由光传输矩阵逐像素预测相互反射在相移轮廓术中造成的条纹相位偏差与高度误差(``table``)。 · 示例: `poc_interreflection_fringe_error`
- `render_transport` `table × images → images` GPU: 有(许可列表) — 通过光传输矩阵(直接 + 相互反射)渲染投影图案下朗伯凹形截面的相机图像(``images``)。 · 示例: `poc_interreflection_fringe_error`
- `separate_direct_global` `images → table` GPU: 有(许可列表) — 由平移高频图案下的图像,用逐像素 L_max 与 L_min 分离直接分量与全局分量(相互反射)(Nayar 等 2006,``table``)。 · 示例: `poc_interreflection_fringe_error`
- `tof_multipath_phase` `无输入 → table` GPU: 无 — 多条光路到达同一像素时的连续波飞行时间距离:相量和的相位,以及相对直接路径的偏差(``table``)。 · 示例: `poc_interreflection_fringe_error`, `poc_itof_multifreq`
- `tof_transport_depth` `table → table` GPU: 无 — 用为每次相互反射计入路径长度延迟的复数辐射度,求凹形朗伯截面(房间墙角)的 AMCW 飞行时间距离及逐像素距离偏差(``table``)。 · 示例: `poc_interreflection_fringe_error`, `poc_itof_multifreq`
- `transport_matrix_radiosity` `table → table` GPU: 无 — 朗伯凹形截面的光传输矩阵:辐射度 B = T E,T = (I − diag(ρ)F)^-1 diag(ρ)(``table``)。 · 示例: `poc_interreflection_fringe_error`, `poc_itof_multifreq`

#### optics / linescan (6)
- `lens_field_profile` `table → table` GPU: 无 — 用光线追迹求每个像高的**相对照度**和 **MTF**(``table``,物体在有限距离 —— 线扫描的用法)。 · 示例: `poc_tdi_linescan`
- `linescan_acquire` `image2d → table` GPU: 无 — 一边输送反射率图 *web*,一边用 TDI 线扫描相机拍摄(``table``)。 · 示例: `poc_tdi_linescan`
- `linescan_lens_columns` `table → table` GPU: 无 — 把 ``lens_field_profile`` 的像高表换成线传感器**每一列像素**的照度和模糊(``table``)。 · 示例: `poc_tdi_linescan`
- `linescan_lens_example` `无输入 → table` GPU: 无 — 线扫描成像系统的两个模型(``raytrace.lens_system`` 的 ``table``)。 · 示例: `poc_tdi_linescan`
- `tdi_snr` `无输入 → table` GPU: 无 — TDI 每个级数 N 的信噪比(``table``)—— 把 EMVA 1288 的线性模型按级数放大。 · 示例: `poc_tdi_linescan`
- `tdi_sync_mtf` `无输入 → table` GPU: 无 — TDI 同步误差和偏航(斜行)造成的模糊的 MTF(闭式解,``table``)。 · 示例: `poc_tdi_linescan`

#### optics / lockin (9)
- `lockin_amplitude` `video → image2d` GPU: 无 — 每个像素中跟随参考信号的成分的幅值图 A -> (H, W) 图像。 · 示例: `poc_lockin_imaging`
- `lockin_demodulate` `video → table` GPU: 无 — 将图像序列对正弦参考逐像素进行正交解调 -> 映射字典。 · 示例: `poc_lockin_imaging`
- `lockin_noise_floor` `无输入 → table` GPU: 无 — 给出白噪声下锁相幅值与相位噪声的闭式解 -> 字典。 · 示例: `poc_lockin_imaging`
- `lockin_phase` `video → image2d` GPU: 无 — 每个像素中跟随参考信号的成分的相位图 phi(弧度,(-pi, pi])-> (H, W) 图像。 · 示例: `poc_lockin_imaging`
- `lockin_ring_normals` `table → table` GPU: 无 — 由偶极调制光环的基波响应求表面法线 -> 映射字典。 · 示例: `poc_lockin_imaging`
- `lockin_ring_synthesize` `image2d → video` GPU: 无 — 由一圈调制光源照明的朗伯起伏表面 -> 图像序列 (T, H, W)。 · 示例: `poc_lockin_imaging`
- `lockin_separate` `video → table` GPU: 无 — 通过对零均值码的最小二乘,分离编码光源与未编码的其余部分 -> 映射字典。 · 示例: `poc_lockin_imaging`
- `lockin_thermal_wave` `image2d → video` GPU: 无 — 逐像素给出受正弦热流加热的平板的稳态表面温度 -> 图像序列 (T, H, W)。 · 示例: `poc_lockin_imaging`, `poc_thermal_drift_metrology`
- `lockin_walsh_codes` `无输入 → matrix` GPU: 无 — 用于编码间歇照明的正交零均值开/关码 -> +-1 的 (n_codes, n_frames) 矩阵。 · 示例: `poc_lockin_imaging`

#### optics / material (6)
- `clearcoat_shade` `rgbimage × normalmap → rgbimage` GPU: 无 — 为表面覆一层透明面漆(汽车漆、陶瓷釉、亮面塑料)。 · 示例: `machined_metal_and_materials`, `poc_telecentric_metrology`
- `material_catalog` `无输入 → table` GPU: 无 — 材质名 → 默认参数(漫反射粗糙度 / 面漆强度与粗糙度 / 布料的边缘光泽)。 · 示例: `machined_metal_and_materials`
- `oren_nayar` `normalmap → image2d` GPU: 无 — 粗糙漫反射面的着色(Oren–Nayar)。纸、石膏、混凝土与月亮的样子。 · 示例: `machined_metal_and_materials`
- `sheen_shade` `normalmap → image2d` GPU: 无 — 布料的**边缘光泽**(天鹅绒、缎)。相对视线越掠射越亮。 · 示例: `machined_metal_and_materials`
- `subsurface_approx` `normalmap → image2d` GPU: 无 — 半透明绕射光的近似(树叶、皮肤、大理石、乳白塑料)。 · 示例: `machined_metal_and_materials`
- `wetness` `rgbimage → rgbimage` GPU: 有(许可列表) — 湿润表面的底色。**漫反射变暗**(而镜面反射增强)。 · 示例: `machined_metal_and_materials`

#### optics / matprop (22)
- `abbe_number` `无输入 → table` GPU: 无 — 夫琅禾费线处的折射率、Abbe 数（d 线系与 e 线系）以及部分色散 P_g,F。 · 示例: `anim3d_lens_aberrations`, `poc_chromatic_confocal`, `poc_material_optical_library`
- `acoustic_impedance_mismatch` `无输入 → table` GPU: 无 — 返回两种材料在垂直入射时的声阻抗失配。 · 示例: `poc_material_optical_library`
- `carbon_black_absorption` `无输入 → pairs` GPU: 无 — 炭黑(黑色塑料的颜料)增加的吸收系数 α [1/mm]。 · 示例: `poc_equipment_selection_map`, `poc_hyperspectral_foreign_matter`
- `glass_map` `无输入 → table` GPU: 无 — Abbe 图（V_d 对 n_d）的点列：每种可见光透明材料的 name / class / nd / vd / PgF。 · 示例: `poc_lens_global_search`, `poc_material_optical_library`, `poc_optics_drawings`
- `material_absorption` `无输入 → pairs` GPU: 无 — 吸收系数曲线 α(λ) = 4πk/λ [1/cm]，以 pairs（λ [nm]，α）返回。 · 示例: `poc_material_optical_library`
- `material_acoustic` `无输入 → table` GPU: 无 — 返回材料记录中保存的声学属性和来源。 · 示例: `poc_material_optical_library`
- `material_dispersion` `无输入 → pairs` GPU: 无 — 折射率色散曲线 n(λ)，以 pairs（λ [nm]，n）返回（等间隔 n_points 点）。 · 示例: `poc_fiber_light_guide`, `poc_material_optical_library`
- `material_electron_properties` `无输入 → table` GPU: 无 — 电子束物性(各元素的 Z、A 与质量分数,密度,二次电子逃逸深度与生成能量)。 · 示例: `poc_virtual_sem_kv_cd_bse`
- `material_extinction` `无输入 → pairs` GPU: 无 — 消光系数曲线 k(λ)，以 pairs（λ [nm]，k）返回；无 k 表的区间为 0。 · 示例: `poc_material_optical_library`
- `material_from_curves` `无输入 → table` GPU: 无 — 由测得的 n(λ)（以及 k(λ)）的 pairs（λ [nm]，值）建立材料记录。 · 示例: `poc_material_optical_library`
- `material_from_sellmeier` `无输入 → table` GPU: 无 — 由 Sellmeier 系数（n² − 1 = Σ Bᵢ λ²/(λ² − Cᵢ)，λ 为 µm，Cᵢ 为 µm²）建立材料记录。 · 示例: `poc_dual_energy_xray`, `poc_material_optical_library`
- `material_nir_absorption` `无输入 → pairs` GPU: 无 — 近红外(0.9〜2.5 µm)的吸收系数 α(λ) [1/mm] (自然对数),由吸收带叠加而成。 · 示例: `poc_equipment_selection_map`, `poc_hyperspectral_foreign_matter`
- `material_optical_constants` `无输入 → table` GPU: 无 — 单一波长的光学常数 n、k，以及由此得到的吸收系数、复介电常数与垂直入射反射率。 · 示例: `poc_chromatic_confocal`, `poc_industrial_oct`, `poc_material_optical_library`, `poc_nir_silicon_transmission`
- `material_record` `无输入 → table` GPU: 无 — 返回一种材料的记录（分类、别名、各波长区间的一次文献、目录公布值）。 · 示例: `poc_material_optical_library`
- `material_reflectance` `无输入 → pairs` GPU: 无 — 空气到材料界面的反射率 R(λ)，以 pairs（λ [nm]，R）返回（Fresnel，复折射率）。 · 示例: `poc_chromatic_confocal`, `poc_material_optical_library`
- `material_table` `无输入 → table` GPU: 无 — 列出同捆的材料表（名称、分类、波长范围、n_d、V_d、出处）。 · 示例: `poc_material_optical_library`
- `material_transmittance` `无输入 → pairs` GPU: 无 — 厚度 thickness_mm 的平行平板透射率 T(λ)，以 pairs（λ [nm]，T）返回。 · 示例: `poc_fiber_light_guide`, `poc_material_optical_library`, `poc_nir_silicon_transmission`
- `nir_model_info` `无输入 → table` GPU: 无 — 将 NIR_BAND_MODELS 中的一种材料连同出处标记以表格返回(吸收带、成分、水、散射、折射率)。 · 示例: `poc_equipment_selection_map`, `poc_hyperspectral_foreign_matter`
- `plate_focus_shift` `无输入 → table` GPU: 无 — 透过平行平板（晶圆、窗口、盖玻片）成像时的焦点偏移与球差，闭式。 · 示例: `poc_chromatic_confocal`, `poc_material_optical_library`, `poc_nir_silicon_transmission`
- `read_glass_catalog_agf` `无输入 → table` GPU: 无 — 读取玻璃目录（光学设计软件的 .agf 格式）为材料记录的列表（table）。 · 示例: `poc_material_optical_library`
- `silicon_free_carrier_absorption` `无输入 → pairs` GPU: 无 — 掺杂硅的自由载流子吸收 α_fc(λ) [1/cm]，以 pairs（λ [nm]，α）返回。 · 示例: `poc_material_optical_library`
- `thermo_optic_coefficient` `无输入 → table` GPU: 无 — 玻璃的 dn/dT（绝对、真空中）以及相对基准温度的折射率变化 Δn，按目录的公式 A。 · 示例: `poc_material_optical_library`, `poc_thermal_drift_metrology`

#### optics / mirror (2)
- `metal_mirror_rgb` `无输入 → vector` GPU: 无 — 金属镜的**颜色**(线性 sRGB)。n,k → 分光反射率 → CIE 配色函数 → sRGB。 · 示例: `glass_and_mirror_optics`, `poc_illumination_cone_vs_na`, `poc_material_optical_library`, `poc_telecentric_metrology`
- `metal_optical_constants` `signal → pairs` GPU: 无 — 按波长查金属的复折射率 (n, k)(可见光区,线性插值)。 · 示例: `glass_and_mirror_optics`, `poc_material_optical_library`

#### optics / moire_align (8)
- `moire_differential_shift` `无输入 → table` GPU: 无 — 由节距差方向相反的两对(A = (p_m, p_w)、B = (p_w, p_m))读取消除了共同误差的位移。 · 示例: `poc_moire_alignment`, `poc_moire_screen`
- `moire_magnification` `无输入 → table` GPU: 无 — 莫尔条纹的周期与方向、位移放大倍率 M 与捕获范围(闭式)。 · 示例: `poc_moire_alignment`, `poc_moire_screen`
- `moire_mark_read` `image2d × image2d → table` GPU: 无 — 由测量图像与参考图像(位移为 0 时拍摄)读取一个对准标记。 · 示例: `poc_moire_alignment`, `poc_moire_screen`
- `moire_overlay_image` `无输入 → image2d` GPU: 无 — 合成相机拍摄的两片重叠光栅的图像(对准标记)。 · 示例: `poc_moire_alignment`, `poc_moire_screen`
- `moire_phase` `image2d → table` GPU: 无 — 读取条纹的相位(以图像原点 x = 0 为基准)、振幅与条纹数。 · 示例: `poc_moire_alignment`, `poc_moire_screen`
- `moire_phase_crlb` `无输入 → table` GPU: 无 — 白高斯噪声下条纹相位与位移能读到多细(下界的闭式)。 · 示例: `poc_moire_alignment`, `poc_moire_screen`
- `moire_phase_to_shift` `无输入 → table` GPU: 无 — 条纹相位的变化 → 位移 δ(nm):δ = Δφ / (dφ/dδ),dφ/dδ = ±2π / 移动光栅的 p。 · 示例: `poc_moire_alignment`, `poc_moire_screen`
- `moire_talbot_gap` `无输入 → table` GPU: 无 — 接近间隙的 Talbot 效应:掩模光栅的像在间隙之后保留多少、符号为何。 · 示例: `poc_moire_alignment`, `poc_moire_screen`

#### optics / noncoaxial (13)
- `beamsplitter_branches` `无输入 → table` GPU: 无 — 会聚光束中平板分束器的两条支路(``table``)。 · 示例: `poc_noncoaxial_optics`
- `ghost_analysis` `table → table` GPU: 无 — 所有面对的两次反射鬼像(``table``):焦点、在传感器上的大小与相对强度。 · 示例: `poc_noncoaxial_optics`, `poc_photograph_through_prescription`
- `ghost_image` `table → image2d` GPU: 无 — 点光源的像加上全部两次反射鬼像在像面上的照度(``image2d``)。 · 示例: `poc_noncoaxial_optics`
- `ghost_path` `table → table` GPU: 无 — 单个两次反射鬼像的实际光线折线(``table``):路径 i < j、光线与能量。 · 示例: `poc_noncoaxial_optics`
- `image_orientation` `table → table` GPU: 无 — 经过折转后的像方向(``table``):反射次数、镜像翻转、旋转。 · 示例: `poc_noncoaxial_optics`
- `noncoaxial_example` `无输入 → table` GPU: 无 — 命名的非共轴示例系统(``table``):折转、潜望镜、分束器、倾斜平板、沙伊姆弗勒。 · 示例: `poc_lens_file_roundtrip`, `poc_noncoaxial_optics`
- `noncoaxial_layout` `table → table` GPU: 无 — 每条记录的全局位姿(``table``):面顶点、旋转矩阵、光轴折线。 · 示例: `poc_lens_file_roundtrip`, `poc_noncoaxial_optics`
- `noncoaxial_spot` `table → table` GPU: 无 — (可倾斜的)像面上的 RMS / 几何光斑半径(mm)与质心(``table``)。 · 示例: `poc_noncoaxial_optics`
- `noncoaxial_system` `无输入 → table` GPU: 无 — 构建经过校验的非共轴序列光学系统(``table``)——面、坐标断点、折转、平板。 · 示例: `poc_lens_file_roundtrip`, `poc_noncoaxial_optics`, `poc_photograph_through_prescription`
- `noncoaxial_trace` `table → table` GPU: 无 — 让充满光瞳的实际光线束穿过三维系统(``table``)。 · 示例: `poc_noncoaxial_optics`
- `scheimpflug_tilt` `无输入 → table` GPU: 无 — 倾斜物面的沙伊姆弗勒条件(``table``;闭式,可选实际光线)。 · 示例: `poc_noncoaxial_optics`
- `surface_reflectance` `无输入 → table` GPU: 无 — 由材料表与镀膜求得的单个面的残余反射率(``table``)。 · 示例: `poc_noncoaxial_optics`
- `tilted_plate_shift` `无输入 → table` GPU: 无 — 倾斜 θ 的平行平板:横向偏移、焦点移动与像散(``table``,闭式)。 · 示例: `poc_noncoaxial_optics`

#### optics / oct (13)
- `oct_ascan` `table → table` GPU: 无 — k 等间隔的干涉光谱 → **A 扫描**(沿深度方向的反射振幅,``table``)。 · 示例: `poc_industrial_oct`
- `oct_bscan` `table → image2d` GPU: 无 — B 扫描的干涉光谱组 → **断面图像**(深度 × 横向,``table``;台账中声明为 20 log10 的图像 image2d)。 · 示例: `poc_industrial_oct`
- `oct_bscan_boundaries` `image2d → table` GPU: 无 — 在 B 扫描**图像**上沿横向追踪界面(``image2d`` → ``table``)。也可用于仪器输出的图。 · 示例: `poc_industrial_oct`
- `oct_bscan_flatten` `table × signal → table` GPU: 无 — 沿某个面(如表面)把 B 扫描**排平**,返回**横向平均的深度剖面**(``table`` → ``table``)。 · 示例: `poc_industrial_oct`
- `oct_bscan_simulate` `无输入 → table` GPU: 无 — 在横截面(``sample2d``)上横向扫描得到的 **B 扫描干涉光谱组**(``table``)。 · 示例: `poc_industrial_oct`
- `oct_design` `无输入 → table` GPU: 无 — 在**测量之前**用闭式求出 OCT 的性能(``table``):轴向分辨率、深度范围、灵敏度衰减(roll-off)、信噪比、横向分辨率与焦深。 · 示例: `poc_industrial_oct`
- `oct_dispersion_broadening` `无输入 → table` GPU: 无 — 只在样品臂中存在的材料(长度 L,往返)造成的色散失配使 A 扫描的峰展宽多少倍(``table``,闭式解)。 · 示例: `poc_industrial_oct`
- `oct_dispersion_compensate` `table → table` GPU: 无 — 数值色散补偿(``table`` → ``table``):把去除直流的 k 等间隔光谱变成解析信号,乘以 exp(−i(a2Δk² + a3Δk³))。 · 示例: `poc_industrial_oct`
- `oct_dispersion_estimate` `table → table` GPU: 无 — 从测得的光谱估计色散补偿系数 a2、a3(``table`` → ``table``)。 · 示例: `poc_industrial_oct`
- `oct_from_spectra` `matrix × signal → table` GPU: 无 — 把仪器记录的原始光谱转成本族 op 读取的表(``matrix`` → ``table``),是实机与公开数据的入口。 · 示例: `poc_industrial_oct`
- `oct_interferogram` `无输入 → table` GPU: 无 — 用 OCT 对层结构(``sample``)测量一次得到的**干涉光谱**(``table``)。 · 示例: `poc_industrial_oct`
- `oct_k_linearize` `table → table` GPU: 无 — 把干涉光谱重新排列到 **k 等间隔**(``table`` → ``table``)。 · 示例: `poc_industrial_oct`
- `oct_layer_thickness` `table → table` GPU: 无 — A 扫描中界面的峰 → **层的光学厚度与物理厚度**(``table``)。无法分离或看不到时拒绝。 · 示例: `poc_industrial_oct`

#### optics / omni360 (24)
- `anaglyph_crosstalk` `rgbimage × rgbimage → table` GPU: 仅在链中(许可列表) — 返回双眼预览和串扰能量比。 · 示例: `poc_omni360_inspection`
- `anaglyph_from_ods` `rgbimage × rgbimage → rgbimage` GPU: 无 — 从全景立体对中提取视口并生成彩色滤镜图。 · 示例: `omni360_roundtrip`
- `cubemap_from_equirect` `rgbimage → rgbvideo` GPU: 无 — 将等距柱状图重采样为六个立方体面。 · 示例: `omni360_roundtrip`
- `equirect_defect_unwrap_pipe` `image2d → table` GPU: 无 — 将圆柱壁展开为平面检测条带。 · 示例: `poc_omni360_inspection`
- `equirect_filter_gaussian` `image2d → image2d` GPU: 无 — 按纬度调整尺度，对全景图进行高斯滤波。 · 示例: `poc_omni360_inspection`
- `equirect_from_cubemap` `rgbvideo → rgbimage` GPU: 无 — 将六个立方体面重采样为等距柱状图。 · 示例: `omni360_roundtrip`
- `equirect_from_fisheye_pair` `images → table` GPU: 无 — 拼接两个已标定鱼眼图并报告重叠、接缝误差和盲区。 · 示例: `poc_allsky_cloud_cover`, `poc_omni360_inspection`
- `equirect_from_perspectives` `images → table` GPU: 无 — 将已标定透视图组混合为全景图。 · 示例: `omni360_roundtrip`
- `equirect_rotate` `rgbimage × matrix → rgbimage` GPU: 有(许可列表) — 对全景图应用正规三维旋转。 · 示例: `poc_omni360_inspection`
- `equirect_stabilize` `images → table` GPU: 无 — 估计并消除全景序列的相机旋转。 · 示例: `poc_omni360_inspection`
- `equirect_weight_map` `无输入 → image2d` GPU: 无 — 返回余弦纬度权重图。 · 示例: `poc_omni360_inspection`
- `ods_depth_to_disparity` `image2d → image2d` GPU: 有(许可列表) — 将径向深度转换为全景立体水平视差。 · 示例: `poc_omni360_inspection`
- `ods_disparity_to_depth` `image2d → image2d` GPU: 有(许可列表) — 将全景立体水平视差转换为径向深度。 · 示例: `poc_omni360_inspection`
- `ods_render` `无输入 → images` GPU: 无 — 通过场景回调渲染全景立体射线。 · 示例: `omni360_roundtrip`
- `omni_anaglyph_compose` `rgbimage × rgbimage → rgbimage` GPU: 无 — 将左右图像合成为彩色滤镜立体图。 · 示例: `poc_omni360_inspection`
- `s_psnr` `image2d × image2d → measurement` GPU: 无 — 在球面确定性近均匀采样点上计算PSNR。 · 示例: `omni360_roundtrip`
- `stereo360_sbs` `rgbimage × rgbimage → rgbimage` GPU: 仅在链中(许可列表) — 将全景左右图并排打包。 · 示例: `omni360_roundtrip`
- `stereo360_top_bottom` `rgbimage × rgbimage → rgbimage` GPU: 无 — 将全景左右图上下打包。 · 示例: `omni360_roundtrip`
- `stereo_pack` `rgbimage × rgbimage → rgbimage` GPU: 无 — 按指定显示布局打包左右图。 · 示例: `omni360_roundtrip`
- `stereo_parallax_budget` `无输入 → table` GPU: 无 — 报告物理视差及屏宽1%和3%限值。 · 示例: `poc_omni360_inspection`
- `video360_tile_coverage` `pairs → table` GPU: 无 — 报告视线路径触及的经纬度分块。 · 示例: `poc_omni360_inspection`
- `video360_viewport_track` `rgbvideo → rgbvideo` GPU: 无 — 从全景帧序列提取移动视口。 · 示例: `poc_omni360_inspection`
- `viewport_from_equirect` `rgbimage → rgbimage` GPU: 无 — 从等距柱状图提取透视视口。 · 示例: `omni360_roundtrip`, `poc_omni360_inspection`
- `ws_psnr` `image2d × image2d → measurement` GPU: 无 — 计算余弦纬度加权的球面PSNR。 · 示例: `omni360_roundtrip`, `poc_omni360_inspection`

#### optics / optimization (3)
- `bend_singlet` `无输入 → table` GPU: 无 — 给定焦距的薄单透镜,按 Coddington 形状因子弯曲(``table``)。 · 示例: `lens_optimize_demo`
- `merit_function` `table → table` GPU: 无 — 某个处方的 DLS 优值 ``Σ residual²`` 及其分项(``table``)。 · 示例: `lens_optimize_demo`, `poc_lens_file_roundtrip`, `poc_lens_merit_operands`
- `optimize_lens` `table → table` GPU: 无 — 对处方做阻尼最小二乘(Levenberg–Marquardt)优化(``table``)。 · 示例: `lens_optimize_demo`, `poc_lens_file_roundtrip`

#### optics / photoelastic (12)
- `brazilian_disc_stress` `无输入 → table` GPU: 无 — 径向受压圆盘(巴西圆盘)平面应力 σx、σy、τxy 的闭式解 → dict。 · 示例: `photoelastic_roundtrip`, `poc_photoelasticity`
- `cubic_photoelastic_birefringence` `image2d × image2d × image2d → table` GPU: 无 — 立方晶体 {100} 面(如 Si 晶圆)的应力双折射 Δn 与慢轴 → dict。 · 示例: `photoelastic_roundtrip`
- `kirsch_plate_stress` `无输入 → table` GPU: 无 — 含孔无限大板单轴拉伸(Kirsch 解)的 σx、σy、τxy 及极坐标分量闭式解 → dict。 · 示例: `photoelastic_roundtrip`
- `photoelastic_phase_estimate` `polsweep → table` GPU: 无 — 由偏振图像以闭式反求相位延迟 δ 与主轴 θ → dict。 · 示例: `photoelastic_roundtrip`, `poc_photoelasticity`
- `photoelastic_polarization_images` `image2d → polsweep` GPU: 无 — 以偏振相机(0/45/90/135 度)或六强度偏振计拍摄圆偏振光照明下试样的图像 → (K, H, W)。 · 示例: `photoelastic_roundtrip`, `poc_photoelasticity`
- `photoelastic_retardation` `image2d → table` GPU: 无 — 各向同性材料的应力光学定律 δ = 2π t C (σ1−σ2)/λ → dict(rad、nm、条纹级数与材料条纹值)。 · 示例: `photoelastic_roundtrip`, `poc_photoelasticity`
- `polariscope_intensity` `image2d → image2d` GPU: 有(许可列表) — 平面与圆偏振仪暗场、明场强度(等色线、等倾线)的闭式解。 · 示例: `photoelastic_roundtrip`, `poc_photoelasticity`
- `principal_stress` `image2d × image2d × image2d → table` GPU: 无 — 平面应力的主应力 σ1 ≥ σ2、主应力差与 σ1 的方向(等倾角)→ dict。 · 示例: `photoelastic_roundtrip`, `poc_photoelasticity`
- `retardation_convert` `image2d → image2d` GPU: 仅在链中(许可列表) — 相位延迟的单位换算(rad / deg / nm / waves = 条纹级数)。 · 示例: `photoelastic_roundtrip`, `poc_photoelasticity`
- `retardation_from_birefringence` `image2d → table` GPU: 仅在链中(许可列表) — 由双折射 Δn 求相位延迟 → dict(并列返回 rad、nm 与条纹级数)。 · 示例: `photoelastic_roundtrip`
- `retardation_unwrap_multiwavelength` `images → table` GPU: 有(许可列表) — 由多个波长的折叠相位延迟确定绝对相位延迟(nm)(假定无色散)→ dict。 · 示例: `photoelastic_roundtrip`
- `silicon_piezo_optic_coefficients` `无输入 → table` GPU: 无 — 返回单晶硅的压光系数 π11−π12、π44 [Pa⁻¹] 及其出处 → dict。 · 示例: `photoelastic_roundtrip`

#### optics / pixelshift (6)
- `false_color_metric` `rgbimage → table` GPU: 无 — 伪色的量:色差(BT.601 的 Cb、Cr)大小的统计。 · 示例: `poc_pixel_shift`
- `pixel_shift_capture` `rgbimage × matrix → video` GPU: 无 — 用位移后的传感器拍摄:在像素开口(正方形箱)上**精确**积分场景,返回 Bayer 或黑白的原始图像。 · 示例: `poc_pixel_shift`, `poc_simcal_pixel_shift`
- `pixel_shift_merge` `video × matrix → rgbimage` GPU: 无 — 用**标称**位移把像素位移的各帧分配到网格上合成。不插值(只取同一网格点样本的平均)。 · 示例: `poc_pixel_shift`, `poc_simcal_pixel_shift`
- `pixel_shift_motion_mask` `video × matrix → image2d` GPU: 无 — 运动像素图 ``(H·scale, W·scale)``(1.0 = 运动,0.0 = 静止或无法判定)。 · 示例: `poc_pixel_shift`
- `pixel_shift_pattern` `无输入 → matrix` GPU: 无 — 像素位移的标称位移序列 ``(N, 2)``(dr, dc)[传感器像素],并加上执行器误差后返回。 · 示例: `poc_pixel_shift`
- `pixel_shift_resolution_budget` `无输入 → table` GPU: 无 — 像素位移能否提高分辨率的闭式预算(镜头受限还是像素受限)。 · 示例: `poc_pixel_shift`, `poc_simcal_pixel_shift`

#### optics / plenoptic (6)
- `mla_surface` `无输入 → table` GPU: 无 — 描述周期球冠微透镜阵列表面。 · 示例: `plenoptic_capture_pipeline`, `poc_plenoptic_camera`
- `plenoptic_capture` `table × table → table` GPU: 无 — 追迹生成光场原始帧及其白场校准图像。 · 示例: `plenoptic_capture_pipeline`, `poc_plenoptic_camera`
- `plenoptic_decode` `image2d × table → lightfield` GPU: 无 — 校正并重采样原始帧，返回光场 L[v,u,y,x]。 · 示例: `plenoptic_decode_pipeline`, `poc_plenoptic_camera`
- `plenoptic_mla_calibrate` `image2d → table` GPU: 无 — 对白场图像峰值拟合旋转矩形晶格以校准微透镜阵列。 · 示例: `poc_plenoptic_camera`
- `plenoptic_refocus_depth` `lightfield × table → table` GPU: 无 — 将光场重聚焦斜率转换为以米为单位的物距。 · 示例: `poc_plenoptic_camera`
- `plenoptic_system` `table × table × table → table` GPU: 无 — 组装主镜头、微透镜阵列和传感器，并报告 F 数匹配。 · 示例: `plenoptic_capture_pipeline`, `poc_plenoptic_camera`

#### optics / polarization (11)
- `jones_apply` `cimage × jones → jones` GPU: 无 — 让 Jones 矢量通过 Jones 矩阵:``[Ex', Ey'] = J @ [Ex, Ey]``。 · 示例: `optics_imaging`, `type_connectivity_tour`
- `jones_element` `无输入 → cimage` GPU: 无 — 单个偏振元件的 2x2 复 Jones 矩阵。 · 示例: `optics_imaging`, `type_connectivity_tour`
- `mueller_apply` `matrix × stokes → stokes` GPU: 无 — 让 Stokes 矢量通过 Mueller 矩阵:``S' = M @ S``。 · 示例: `optics_imaging`, `poc_photoelasticity`, `polarization_camera_pipeline`
- `mueller_checks` `matrix → table` GPU: 无 — 判断 4x4 矩阵是否为物理可实现的 Mueller 矩阵,以及退偏程度。 · 示例: `polarization_camera_pipeline`
- `mueller_element` `无输入 → matrix` GPU: 无 — 单个偏振元件的 4x4 实 Mueller 矩阵。 · 示例: `optics_imaging`, `poc_mueller_dofp_observability`, `poc_photoelasticity`, `polarization_camera_pipeline`
- `mueller_from_intensities` `signal → matrix` GPU: 无 — 从已知起偏器/检偏器状态下测得的强度恢复 Mueller 矩阵(偏振测量的最小二乘)。 · 示例: `polarization_camera_pipeline`
- `mueller_partial_polarizer` `无输入 → matrix` GPU: 无 — 消光比有限的线偏振器(线性二向衰减器)的 Mueller 矩阵。→ (4, 4),角度场则为 (*shape, 4, 4)。 · 示例: `polarization_camera_pipeline`
- `polarization_demosaic` `image2d → polsweep` GPU: 无 — 将偏振传感器的马赛克拆成四张检偏器图像(0/45/90/135 度)。 · 示例: `poc_shape_from_polarization`, `polarization_camera_pipeline`
- `polarization_demosaic_color` `image2d → rgbvolume` GPU: 有(许可列表) — 将彩色偏振传感器(IMX250MYR 系,4x4 块)的马赛克拆成四张 RGB 图像 (4, H, W, 3)。 · 示例: `polarization_camera_pipeline`
- `stokes_analyze` `stokes → table` GPU: 无 — 读取 Stokes 矢量:偏振度、方位角、椭圆率。 · 示例: `optics_imaging`, `polarization_camera_pipeline`, `specular_photometric`, `type_connectivity_tour`
- `stokes_from_jones` `jones → stokes` GPU: 无 — Jones 矢量 -> Stokes 矢量(四个可测强度)。 · 示例: `optics_imaging`, `type_connectivity_tour`

#### optics / radiosity (7)
- `form_factor_matrix` `table → matrix` GPU: 无 — ``radiosity_patches`` 面片组中所有面片对的角系数 F_ij(遮挡由场景光线判定)。 · 示例: `poc_pocket_interreflection`
- `form_factor_parallel_rects` `无输入 → measurement` GPU: 无 — 两个相同、平行且正对的矩形 a × b(间距 c)之间的角系数(Howell 目录 C-11 的闭式解)。 · 示例: `poc_pocket_interreflection`
- `form_factor_perpendicular_rects` `无输入 → measurement` GPU: 无 — 共用长度为 l 的边、成 90° 相交的矩形 w × l 到 h × l 的角系数(Howell 目录 C-14 的闭式解)。 · 示例: `poc_pocket_interreflection`
- `form_factor_polygons` `points × points → measurement` GPU: 无 — 以数值方法求三维中两个平面凸多边形(三角形或四边形)之间的角系数 F_ij。 · 示例: `poc_pocket_interreflection`
- `radiosity_patches` `无输入 → table` GPU: 无 — 由多边形或 optscene 场景构建一组平面辐射度面片(``rad_patches`` 表)。 · 示例: `poc_pocket_interreflection`
- `radiosity_progressive_3d` `table × signal → table` GPU: 无 — 三维面片组上的渐进细化辐射度(Cohen 等 1988,shooting,式 7–8)及其收敛的证据。 · 示例: `poc_pocket_interreflection`
- `render_optscene_gi` `table × table × table → table` GPU: 无 — 含相互反射的检测用渲染:在 ``render_optscene`` 的光度之上加上朗伯面片之间的 n 次反射(或收敛解)。 · 示例: `poc_pocket_interreflection`

#### optics / scene (44)
- `airy_radius_um` `无输入 → measurement` GPU: 无 — 到艾里斑第一暗环的半径 [µm] = 1.22 · λ · N(闭式)。 · 示例: `vision_layout_from_catalog`
- `camera_rays` `table → points` GPU: 无 — 相机 dict → 全部像素的光线:origins (H·W, 3)、directions (H·W, 3)。 · 示例: `poc_itof_multifreq`, `poc_nir_silicon_transmission`, `poc_pocket_interreflection`, `studio_raytrace_scene`
- `covers_sensor` `table × table → table` GPU: 无 — 镜头能否覆盖该传感器(像圈 对 对角线)。 · 示例: `vision_layout_from_catalog`
- `dataset_throughput` `table → table` GPU: 无 — :func:`inspection_dataset` 的结果 → 生成吞吐量的实测汇总。 · 示例: `virtual_machine_vision`
- `defocus_blur` `rgbimage × image2d × table → rgbimage` GPU: 无 — 依据深度真值施加**景深模糊**(理想针孔像 → 实际镜头的像)。 · 示例: `poc_focus_stacking`, `virtual_machine_vision`
- `diffraction_blur` `rgbimage × table → rgbimage` GPU: 无 — 施加由光阑决定的**衍射模糊**(用高斯近似艾里斑)。 · 示例: `vision_layout_from_catalog`
- `env_lightbox` `points → signal` GPU: 无 — 摄影灯箱的环境(宽大的顶光 + 略亮的周围)。**无彩色**。 · 示例: `studio_raytrace_scene`
- `env_studio` `points → signal` GPU: 无 — 影棚环境的辐亮度(方向 → 亮度)。**无彩色**。 · 示例: `studio_raytrace_scene`
- `illumination_visibility` `table × points × table → signal` GPU: 无 — 从各点看到的**发光点可见比例** [0, 1] (即落影)。 · 示例: `studio_raytrace_scene`
- `inspection_dataset` `table × table × table → table` GPU: 无 — 为外观检测 AI 生成 **n 张训练图**,带像素级完美标签。 · 示例: `virtual_machine_vision`
- `interface_budget` `table → table` GPU: 无 — 由传输带宽返回**受带宽限制的最大帧率 / 行频**。 · 示例: `vision_layout_from_catalog`
- `layout_capture` `table → table` GPU: 无 — 按布局如实拍摄(光谱 → 衍射 → 景深 → 传感器)。 · 示例: `poc_nir_silicon_transmission`, `poc_optics_drawings`, `vision_layout_from_catalog`
- `lens_catalog` `无输入 → table` GPU: 无 — 工业镜头的规格表(可按型号查)。可用 ``maker`` / ``mount`` 筛选。 · 示例: `vision_layout_from_catalog`
- `lens_spec` `无输入 → table` GPU: 无 — 镜头诸元。NA 与 F 值**给哪一个都行**(N = 1/(2·NA))。 · 示例: `poc_nir_silicon_transmission`, `poc_optics_drawings`, `vision_layout_from_catalog`
- `light_catalog` `无输入 → table` GPU: 无 — 照明的规格表(键为「厂商 型号」)。可用 ``maker`` / ``kind`` 筛选。 · 示例: `vision_layout_from_catalog`
- `light_spec` `无输入 → table` GPU: 无 — 照明诸元。**几何交给 illumdesign.light_source,光的性质在这里补上**。 · 示例: `poc_nir_silicon_transmission`, `poc_optics_drawings`, `studio_raytrace_scene`, `vision_layout_from_catalog`
- `light_wavelengths` `table → pairs` GPU: 无 — 把光源的光谱压缩为成像所用的少数波长与权重。 · 示例: `vision_layout_from_catalog`
- `linescan_capture` `table × table × table → table` GPU: 无 — 用**线扫描 / TDI** 拍摄(边输送边逐行累积)。 · 示例: `vision_layout_from_catalog`
- `observe_surface` `无输入 → table` GPU: 无 — **组好观察光学系统,拍摄指定材质的加工面**(一行即可使用的入口)。 · 示例: `vision_layout_from_catalog`
- `optical_budget` `无输入 → table` GPU: 无 — 以闭式给出观察光学系统的**分辨率预算**(拍之前先看能不能成立)。 · 示例: `vision_layout_from_catalog`
- `optical_camera` `无输入 → table` GPU: 无 — 由实际诸元(焦距、像元间距、分辨率、工作距离)组成理想针孔相机。 · 示例: `poc_focus_stacking`, `poc_pocket_interreflection`, `studio_raytrace_scene`, `virtual_machine_vision`, `vision_layout_from_catalog`
- `optscene_defect_mask` `table × table → image2d` GPU: 无 — **缺陷像素的真值掩码** (H, W)。训练与评测的标签用这个。 · 示例: `studio_raytrace_scene`, `virtual_machine_vision`
- `optscene_depth` `table × table → image2d` GPU: 无 — 深度的**真值** (H, W) [mm]。是**沿光轴的 z**,不是从视点算的斜距。 · 示例: `virtual_machine_vision`
- `optscene_instances` `table × table → table` GPU: 无 — 把缺陷按**个体**返回(类别、像素掩码、bounding box、面积)。 · 示例: `virtual_machine_vision`
- `optscene_mask` `table × table → image2d` GPU: 无 — 第 ``index`` 个基元可见像素的 **真值掩码** (H, W),bool。 · 示例: `virtual_machine_vision`
- `random_defects` `table → table` GPU: 无 — 在零件上制造**随机缺陷**(划痕、裂纹、凹坑、污渍、压痕、异物)。 · 示例: `virtual_machine_vision`
- `reflect_rays` `points × points → points` GPU: 无 — 镜面反射 d − 2(d·n)n。``glassmirror.refract_rays`` 的搭档(此前缺反射侧)。 · 示例: `studio_raytrace_scene`
- `register_light` `无输入 → text` GPU: 无 — 把手头的照明登记进目录(照数据手册的值原样填入)。 · 示例: `vision_layout_from_catalog`
- `render_optscene` `table × table × table → rgbimage` GPU: 无 — **为检测**而拍:按物理单位摆放真实灯具并计数直接光(带真值)。 · 示例: `poc_nir_silicon_transmission`, `poc_pocket_interreflection`, `virtual_machine_vision`
- `render_studio` `table × table → rgbimage` GPU: 无 — 画**用来展示的图**:含环境光、多次反射、折射与色散(没有测光真值)。 · 示例: `studio_raytrace_scene`
- `scene_box` `无输入 → table` GPU: 无 — 轴对齐长方体零件(AABB)。``half_size_mm`` 是各轴的半尺寸 [mm]。 · 示例: `poc_nir_silicon_transmission`, `poc_optics_drawings`, `poc_pocket_interreflection`, `studio_raytrace_scene`, `vision_layout_from_catalog`
- `scene_cylinder` `无输入 → table` GPU: 无 — 平行于 z 轴的有限圆柱(带端面)。**加工纹理真正会附着的形状**。 · 示例: `virtual_machine_vision`
- `scene_difference` `table × table → table` GPU: 无 — 从 ``solid`` 中挖去 ``cavity``(CSG 差集)。**制作中空零件的唯一手段**。 · 示例: `poc_pocket_interreflection`, `studio_raytrace_scene`
- `scene_material` `无输入 → table` GPU: 无 — 创建一种材质。``kind`` 为 lambert / conductor / dielectric 三选一。 · 示例: `poc_material_optical_library`, `poc_nir_silicon_transmission`, `poc_pocket_interreflection`, `studio_raytrace_scene`, `virtual_machine_vision`, `vision_layout_from_catalog`
- `scene_plane` `无输入 → table` GPU: 无 — z = ``z_mm`` 的水平面(载台/传送带)。用 ``half_size_mm`` 可做成有限的板。 · 示例: `poc_pocket_interreflection`, `virtual_machine_vision`
- `scene_sphere` `无输入 → table` GPU: 无 — 球体零件。``center_mm`` 为 (x, y, z) [mm],``radius_mm`` > 0。 · 示例: `virtual_machine_vision`
- `sensor_capture` `rgbimage → rgbimage` GPU: 无 — 辐亮度 → 真实传感器的输出(散粒噪声、读出噪声、饱和、量化)。 · 示例: `vision_layout_from_catalog`
- `sensor_catalog` `无输入 → table` GPU: 无 — 真实传感器的规格表(附 Basler 的 EMVA1288 实测)。 · 示例: `vision_layout_from_catalog`
- `sensor_diagonal_mm` `table → measurement` GPU: 无 — 传感器对角线 [mm]。与镜头像圈比较,看**能否覆盖**。 · 示例: `vision_layout_from_catalog`
- `sensor_spec` `无输入 → table` GPU: 无 — 图像传感器的诸元。只持有决定**电子数**那一侧的数值。 · 示例: `poc_nir_silicon_transmission`, `poc_optics_drawings`, `vision_layout_from_catalog`
- `surface_defect` `table × image2d → table` GPU: 无 — 把 2-D 缺陷图**贴到零件表面**(直接吃 ``defectgen`` 的输出)。 · 示例: `studio_raytrace_scene`
- `surface_finish` `table → table` GPU: 无 — 在零件表面刻出**加工纹路**(车纹、拉丝、滚花、喷砂、磨削纹)。 · 示例: `virtual_machine_vision`
- `trace_rays` `table × points × points → table` GPU: 无 — 发射一束光线并返回第一个交点(渲染器赖以构建的公开算子)。 · 示例: `anim3d_lens_aberrations`, `poc_chromatic_confocal`, `poc_lens_file_roundtrip`, `poc_lens_solves_afocal`, `poc_noncoaxial_optics`, `poc_plenoptic_camera`, `poc_pocket_interreflection`, `poc_telecentric_metrology`, `studio_raytrace_scene`
- `vision_layout` `table × table × table → table` GPU: 无 — 把传感器、镜头、照明、场景绑成一体,并以**闭式返回导出量**。 · 示例: `poc_nir_silicon_transmission`, `poc_optics_drawings`, `vision_layout_from_catalog`

#### optics / sensorchar (19)
- `emva_bspline_regression` `signal × signal → table` GPU: 有(许可列表) — 三次 B 样条的最小二乘拟合及其斜率(General 6.6 节,式 44〜49)。 · 示例: `poc_emva1288_in_camera_processing`
- `emva_dark_current` `signal × signal → table` GPU: 无 — 暗电流(7.1 节)：将暗图像的均值(及方差)对曝光时间作直线拟合所得的斜率。 · 示例: `poc_emva1288_sensor`
- `emva_defect_pixels` `image2d → table` GPU: 无 — 缺陷像素的表征(8.8 节)：对数直方图(式 73〜75)与累积直方图(式 77)，以及超过阈值的像素数。 · 示例: `poc_emva1288_in_camera_processing`, `poc_emva1288_sensor`
- `emva_dynamic_range` `无输入 → table` GPU: 无 — 动态范围 DR = μ_p.sat / μ_p.min(式 28)，以倍数、dB(20 log10)和 bit(log2)表示。 · 示例: `poc_emva1288_in_camera_processing`, `poc_emva1288_sensor`
- `emva_exposure_for_snr` `signal → signal` GPU: 无 — 达到给定 SNR 所需的曝光 μ_p(SNR) = SNR²/(2η) (1 + √(1 + 4(σ²_d + σ²_q/K²)/SNR²))(式 25,式 21 的逆)。 · 示例: `poc_emva1288_sensor`
- `emva_filter_distortion` `matrix → table` GPU: 无 — 相机内部的线性预处理使 EMVA 1288 Linear 的数值偏移多少——闭式(本族的推导,并非标准中的公式)。 · 示例: `poc_emva1288_in_camera_processing`
- `emva_highpass` `image2d → table` GPU: 无 — 去除照明不均的高通滤波器(8.1 节;旧版为附录 C.5 的式 84〜87)。 · 示例: `poc_emva1288_in_camera_processing`, `poc_emva1288_sensor`
- `emva_linearity_error` `signal × signal → table` GPU: 无 — 线性误差 LE(式 58〜63)。将 y = μ_y − μ_y.dark 对曝光 H 以**相对偏差的权重 1/y²**进行拟合(式 59〜61)，并在饱和的 5〜95 % 的点上，取相对偏差 δy[i] = 100 (y − (a0 + a1 H))/(a0 + a1 H) [%] 的绝对值的平均作为 LE。 · 示例: `poc_emva1288_in_camera_processing`, `poc_emva1288_sensor`
- `emva_noise_whiteness` `image2d × image2d → table` GPU: 无 — 时间噪声在像素之间是否独立(Linear 1.2 节前提 3),在连续拍摄的图像之间是否独立(Linear 与 General 的前提 3)。 · 示例: `poc_emva1288_in_camera_processing`
- `emva_pair_statistics` `image2d × image2d → table` GPU: 无 — 由同一曝光下拍摄的 2 张图像，求出均值、时间方差与空间方差(式 16、18、32)。 · 示例: `poc_emva1288_in_camera_processing`, `poc_emva1288_sensor`, `poc_tdi_linescan`
- `emva_photon_exposure` `signal → signal` GPU: 无 — 由传感器面辐照度求每像素平均光子数 μ_p = A E t_exp/(hc/λ)(式 3),采用标准的便捷单位(式 4)。 · 示例: `poc_emva1288_sensor`
- `emva_photon_transfer` `signal × signal → table` GPU: 无 — 由 photon transfer 曲线求出系统增益 K 与暗噪声 σ_d(式 50、53、54)。 · 示例: `poc_emva1288_in_camera_processing`, `poc_emva1288_sensor`
- `emva_ptc_linearity_check` `signal × signal → table` GPU: 有(许可列表) — 光子转移曲线是否为直线(6.6 节,式 51)——判断能否使用 Linear 的 K 的检查。 · 示例: `poc_emva1288_in_camera_processing`, `poc_emva1288_sensor`
- `emva_quantum_efficiency` `signal × signal → table` GPU: 无 — 由响应(特性曲线)的斜率求出量子效率 η(式 49、52)。 · 示例: `poc_emva1288_in_camera_processing`, `poc_emva1288_sensor`
- `emva_sensitivity_threshold` `无输入 → table` GPU: 无 — 绝对灵敏度阈值(使 SNR = 1 的曝光，式 26、27)。 · 示例: `poc_emva1288_in_camera_processing`, `poc_emva1288_sensor`
- `emva_snr_curve` `signal → matrix` GPU: 无 — 线性模型的 SNR(式 21)与理想传感器的 SNR(式 23)。 · 示例: `poc_emva1288_in_camera_processing`, `poc_emva1288_sensor`
- `emva_spatial_nonuniformity` `volume × volume → table` GPU: 无 — DSNU 与 PRNU(式 33〜42、65〜67)。 · 示例: `poc_emva1288_in_camera_processing`, `poc_emva1288_sensor`
- `emva_spectrogram` `image2d → table` GPU: 有(许可列表) — 水平与垂直频谱图(8.6 节,式 70〜72)。 · 示例: `poc_emva1288_sensor`
- `emva_total_snr` `signal → matrix` GPU: 无 — 包含空间不均匀性的总 SNR(8.5 节,式 68、69)。 · 示例: `poc_emva1288_sensor`

#### optics / sensorgeneral (3)
- `emva_general_nonuniformity` `volume × volume → table` GPU: 无 — 以输入(光子)为单位的 DSNU 与 PRNU(General 8 节,式 55、56、58、59)。 · 示例: `poc_emva1288_in_camera_processing`
- `emva_general_relative_qe` `signal × signal → table` GPU: 有(许可列表) — 相对于参考波长的相对量子效率 η(λ)/η(λ_ref)(General 9.4 节,式 73、74)。 · 示例: `poc_emva1288_in_camera_processing`
- `emva_general_sensitivity` `signal × signal × signal → table` GPU: 有(许可列表) — 特性曲线、输入 SNR、绝对灵敏度阈值、DR 与以光子为单位的暗噪声(General 2.1〜2.4、6.6〜6.8 节)。 · 示例: `poc_emva1288_in_camera_processing`

#### optics / shape_from_polarization (8)
- `aolp_to_azimuth` `image2d → table` GPU: 仅在链中(许可列表) — 把线偏振角(AoLP)变为表面法线方位角的 2 个候选(π 模糊);漫射与镜面相差 90°(``table``)。 · 示例: `poc_shape_from_polarization`
- `dolp_to_zenith` `image2d → table` GPU: 有(许可列表) — 由 DoLP 反求产生它的天顶角解集 —— 漫射 1 个解,镜面在 Brewster 角两侧 2 个解(``table``)。 · 示例: `poc_shape_from_polarization`
- `sfp_disambiguate` `table → normalmap` GPU: 无 — 用明确的先验从 ``sfp_normals`` 的候选中为每个像素选 1 个法线 —— 凸性 + Brewster 脊线分割,或粗略深度/法线(``normalmap``)。 · 示例: `poc_shape_from_polarization`
- `sfp_dolp_model` `image2d → image2d` GPU: 有(许可列表) — 镜面反射光(Fresnel 反射)或漫射光(Fresnel 透射)的线偏振度随天顶角的变化(``image2d``)。 · 示例: `poc_shape_from_polarization`
- `sfp_estimate_index` `image2d × image2d → table` GPU: 无 — 由已知天顶角处观测到的 DoLP 估计折射率 —— Fresnel 曲线最小二乘拟合,镜面时另给出 DoLP 最大处的 ``n = tan(theta_B)``(``table``)。 · 示例: `poc_shape_from_polarization`
- `sfp_height` `normalmap → image2d` GPU: 无 — 在镜像扩展的区域上用 Frankot–Chellappa 把法线图积分为高度图,FFT 的周期边界不会使结果弯曲(``image2d``)。 · 示例: `poc_phase_measuring_deflectometry`, `poc_shape_from_polarization`
- `sfp_normals` `polsweep → table` GPU: 无 — 由偏振扫描得到每个像素表面法线的显式候选集 —— 漫射 2 个,镜面 4 个(天顶 2 × 方位 2)(``table``)。 · 示例: `poc_shape_from_polarization`
- `sfp_render` `normalmap → polsweep` GPU: 无 — 渲染 4 方向偏振相机拍摄给定法线图的电介质表面所得的图像(偏振形状恢复的正向模型,``polsweep``)。 · 示例: `poc_shape_from_polarization`

#### optics / spectral (15)
- `bandpass_spectrum` `无输入 → pairs` GPU: 无 — 带通滤光片的透射率(超高斯)。 · 示例: `poc_equipment_selection_map`, `poc_nir_silicon_transmission`
- `blackbody_spectrum` `无输入 → pairs` GPU: 无 — 黑体的光谱辐亮度 L(λ, T),单位 W m⁻² sr⁻¹ nm⁻¹(普朗克公式,SI 2019 常数)。 · 示例: `poc_equipment_selection_map`, `poc_nir_silicon_transmission`, `poc_simcal_thin_film`, `poc_thin_film_reflectometry`
- `cie_illuminant_a` `无输入 → pairs` GPU: 无 — CIE 标准照明体 A 的相对光谱功率分布(CIE 15:2004 的定义式,560 nm 处为 100)。 · 示例: `poc_nir_silicon_transmission`
- `energy_to_photons` `pairs → pairs` GPU: 无 — 把能量光谱分布(W/nm)换成光子数分布(光子 s⁻¹ nm⁻¹):乘以 λ/(hc)。 · 示例: `poc_fiber_light_guide`, `poc_nir_silicon_transmission`
- `hyperspectral_band_weights` `无输入 → matrix` GPU: 无 — 从反射率到各波段电子数的线性映射 W(B × L)。电子数 = W @ R(λ)(加噪声前)。 · 示例: `poc_equipment_selection_map`, `poc_hyperspectral_foreign_matter`
- `hyperspectral_capture` `pairs → table` GPU: 无 — 一条反射光谱经卤素灯 × 光学系统 × 波段 × InGaAs 成像时各波段的电子数与噪声。 · 示例: `poc_hyperspectral_foreign_matter`
- `ingaas_photodiode_qe` `无输入 → pairs` GPU: 无 — 由吸收层与窗口层的直接跃迁吸收边计算 InGaAs 光电二极管的外量子效率(电子/光子)。 · 示例: `poc_equipment_selection_map`, `poc_hyperspectral_foreign_matter`
- `kubelka_munk_reflectance` `pairs → pairs` GPU: 无 — 用 Kubelka–Munk 闭式求散射层的漫反射率(由吸收系数曲线)。 · 示例: `poc_hyperspectral_foreign_matter`
- `led_spectrum` `无输入 → pairs` GPU: 无 — LED 的相对光谱分布(峰值处为 1)。 · 示例: `poc_chromatic_confocal`, `poc_fiber_light_guide`, `poc_nir_silicon_transmission`
- `silicon_photodiode_qe` `无输入 → pairs` GPU: 无 — 由 Si 的 n,k 求 Si 光电二极管的外量子效率(电子/光子)。 · 示例: `poc_equipment_selection_map`, `poc_fiber_light_guide`, `poc_nir_silicon_transmission`, `scintillator_sensor_tour`
- `spectral_integral` `pairs → measurement` GPU: 无 — 曲线的波长积分 ∫ s(λ) dλ(梯形法则,λ 以 nm 计)。给定区间时只积其内部(端点线性插值)。 · 示例: `poc_equipment_selection_map`, `poc_fiber_light_guide`, `poc_nir_silicon_transmission`
- `spectral_integral_table` `pairs → table` GPU: 无 — 为重复的波段积分构建可复用的累积梯形积分表。 · 示例: `poc_nir_silicon_transmission`
- `spectral_product` `pairs × pairs → pairs` GPU: 无 — 在 *a* 的波长上求两条曲线的积(*b* 线性插值)。把光源 × 透射率 × QE 逐条相乘。 · 示例: `poc_fiber_light_guide`, `poc_nir_silicon_transmission`
- `spectral_reflectance_from_material` `无输入 → pairs` GPU: 无 — 由材料表的近红外吸收带生成颗粒(碎片)的漫反射光谱(被观察对象一侧)。 · 示例: `poc_hyperspectral_foreign_matter`
- `spectral_stats` `pairs → table` GPU: 无 — 曲线的摘要:峰值波长与峰值、重心波长、半高全宽(用线性插值求交点)、积分。 · 示例: `poc_nir_silicon_transmission`

#### optics / spectrometer (5)
- `czerny_turner_design` `无输入 → table` GPU: 无 — Czerny–Turner 光谱仪(平面光栅 + 两块凹面镜)的一阶设计:相机焦距、消彗差的镜面角和波长映射。 · 示例: `poc_spectrometer_illumination`
- `grating_dispersion` `无输入 → table` GPU: 无 — 求解光栅方程 mλ = d(sin α + sin β),并列出角色散、倒线色散、分辨本领和重叠的衍射级。 · 示例: `poc_spectrometer_illumination`
- `spectrometer_bandpass` `table → table` GPU: 无 — 按波长由狭缝、像素和衍射给出光谱仪的带宽(仪器线型的半高全宽)。 · 示例: `poc_spectrometer_illumination`
- `spectrometer_slit_image` `table → table` GPU: 无 — 三维追迹长狭缝的像,给出 smile(谱线弯曲)和 keystone(空间放大率随波长的变化)。 · 示例: `poc_spectrometer_illumination`
- `spectrometer_spectrum` `table × pairs → pairs` GPU: 无 — 输入光谱 → 探测器像素的读数(高阶像与一阶像重叠)。 · 示例: `poc_spectrometer_illumination`

#### optics / surface (5)
- `corrosion_mask` `无输入 → image2d` GPU: 无 — 锈、铜绿与污渍的**斑驳**(0–1 掩码)。 · 示例: `machined_metal_and_materials`
- `metallic_flake_normals` `无输入 → normalmap` GPU: 无 — 生成金属漆中铝片(闪光片)的法线场。 · 示例: `machined_metal_and_materials`
- `rough_transmission` `signal → pairs` GPU: 有(许可列表) — 把毛玻璃的透射分成「直透分量」与「扩散分量」。 · 示例: `machined_metal_and_materials`
- `weave_normals` `无输入 → normalmap` GPU: 无 — 织纹的法线场(布、碳纤维、金属网)。两组正交周期的隆起。 · 示例: `machined_metal_and_materials`, `poc_pixel_shift`
- `wood_grain` `无输入 → image2d` GPU: 无 — 生成木纹(年轮)的**颜色调制**与**纤维方向**。 · 示例: `machined_metal_and_materials`

#### optics / telecentric (7)
- `chief_ray_angle` `table → table` GPU: 无 — 从物高 *field_mm* 的点出发、穿过光阑中心的真实主光线:物方倾角(即远心度)与像的位置。 · 示例: `poc_optics_drawings`, `poc_simcal_telecentric`, `poc_telecentric_metrology`
- `defocus_spot_vs_depth` `table → pairs` GPU: 无 — 物体移动 ±Δz 时固定像面上的 RMS 模糊半径(µm,用斜率网格穷举追迹光线束)。 · 示例: `poc_telecentric_metrology`
- `lens_equivalent_pinhole` `table → table` GPU: 无 — 把主光线的几何映射为 `render3d.render_mesh` 用的针孔相机(pose, K)。 · 示例: `poc_telecentric_metrology`
- `magnification_vs_depth` `table → pairs` GPU: 无 — 物体沿光轴移动时的放大率 m(Δz)(像面固定,真实主光线的像高 / 物高)。 · 示例: `poc_telecentric_metrology`
- `telecentric_lens` `无输入 → table` GPU: 无 — 用同一片单透镜、只改变光阑位置得到的三种成像镜头的处方(`raytrace.lens_system` 的 table)。 · 示例: `poc_optics_drawings`, `poc_telecentric_metrology`
- `telecentricity_error` `table → table` GPU: 无 — 同一尺寸分别位于高度差为 *step_height_mm* 的台阶上下两面时,在像上看起来相差多少。 · 示例: `poc_telecentric_metrology`
- `vignetting_vs_field` `table → pairs` GPU: 无 — 各物高下到达像面的光线束立体角(斜率空间的面积)相对于轴上的比例(渐晕)。 · 示例: `poc_telecentric_metrology`

#### optics / tem (11)
- `tem_amorphous_film` `无输入 → image2d` GPU: 无 — 非晶膜的投影势,单位 V Å(Thon 环的标准试样,``image2d``)。 · 示例: `poc_tem_ctf_thon_rings`
- `tem_ctf` `无输入 → image2d` GPU: 无 — 二维衬度传递函数(直流在中心,``fftshift`` 顺序,形状 ``shape``)。 · 示例: `poc_tem_ctf_thon_rings`
- `tem_ctf_correct` `image2d → image2d` GPU: 有(许可列表) — CTF 校正(``image2d``)。``method="phase_flip"``:F⁻¹[ F(I − ⟨I⟩) · sign(CTF) ] (相位翻转,振幅不变)/ ``"wiener"``:F⁻¹[ F(I − ⟨I⟩) · CTF / (CTF² + 1/snr) ]。 · 示例: `poc_tem_ctf_thon_rings`
- `tem_ctf_estimate` `image2d → table` GPU: 无 — 由显微照片功率谱中的 Thon 环估计欠焦量(及像散)(表)。 · 示例: `poc_tem_ctf_thon_rings`
- `tem_ctf_profile` `无输入 → table` GPU: 无 — 一维径向 CTF 曲线(含包络)及其零点表。 · 示例: `poc_tem_ctf_thon_rings`
- `tem_image_weak_phase` `image2d → image2d` GPU: 有(许可列表) — 由投影势 v_z(V Å)生成 TEM 明场像(平均为 1 的强度,``image2d``)。 · 示例: `poc_sem_tem_same_particle`, `poc_tem_ctf_thon_rings`
- `tem_multislice` `image2d → table` GPU: 有(许可列表) — 简易多层法(Cowley–Moodie,Kirkland 的形式):返回出射波(表)。 · 示例: `poc_sem_tem_same_particle`, `poc_tem_ctf_thon_rings`
- `tem_power_spectrum` `image2d → image2d` GPU: 有(许可列表) — 分块周期图的平均(Welch,Hann 窗),以 ``fftshift`` 顺序的二维数组返回(``image2d``)。 · 示例: `poc_tem_ctf_thon_rings`
- `tem_projected_potential` `无输入 → image2d` GPU: 无 — 由原子坐标得到沿 z 方向投影的势 v_z(x, y),单位 V Å(周期边界,``image2d``)。 · 示例: `poc_sem_tem_same_particle`, `poc_tem_ctf_thon_rings`
- `tem_scherzer` `无输入 → table` GPU: 无 — Scherzer 欠焦与点分辨率(表)。 · 示例: `poc_tem_ctf_thon_rings`
- `tem_wavelength` `无输入 → table` GPU: 无 — 返回加速电压 ``kv``(kV)下电子的波长(含相对论修正)和相互作用常数(表)。 · 示例: `poc_sem_tem_same_particle`, `poc_tem_ctf_thon_rings`

#### optics / tolerancing (8)
- `tolerance_compensators` `无输入 → table` GPU: 无 — 描述确定且有界的再优化变量 -> 字典。 · 示例: `poc_lens_tolerancing`
- `tolerance_criteria` `无输入 → table` GPU: 无 — 验证性能准则及可选上下限 -> 字典。 · 示例: `lensfile_tolerance_worst_mtf`, `optimized_lens_tolerance_sensitivity`, `poc_lens_tolerancing`
- `tolerance_monte_carlo` `table × table × table → table` GPU: 无 — 运行确定且失败封闭的蒙特卡洛并报告 Wilson 95% 良率区间 -> 字典。 · 示例: `lensfile_tolerance_worst_mtf`, `poc_lens_tolerancing`
- `tolerance_report` `table → text` GPU: 无 — 以字典或纯文本生成简洁装配报告 -> 字典。 · 示例: `poc_lens_tolerancing`
- `tolerance_sensitivity` `table × table × table → table` GPU: 无 — 计算中心差分、考虑分布的线性 RSS 和反向公差 -> 字典。 · 示例: `optimized_lens_tolerance_sensitivity`, `poc_lens_tolerancing`
- `tolerance_table` `table → table` GPU: 无 — 为每个独立制造变量建立并验证公差行 -> 字典。 · 示例: `lensfile_tolerance_worst_mtf`, `optimized_lens_tolerance_sensitivity`, `poc_lens_tolerancing`
- `tolerance_table_from_zmx` `table × text → table` GPU: 无 — 从写出的 NOTE 行读取公差表 -> 字典。 · 示例: `poc_lens_tolerancing`
- `tolerance_table_zmx` `table → text` GPU: 无 — 将公差行序列化为 NOTE 行 -> 文本。 · 示例: `poc_lens_tolerancing`

#### optics / watermedia (10)
- `cylinder_lens_caustic` `无输入 → table` GPU: 无 — 平行光束中圆柱(棒或瓶)的近轴焦点与实际光线的焦散线 -> 字典。 · 示例: `poc_water_transparent_media`
- `fresnel_water_air` `无输入 → table` GPU: 无 — 空气-水界面的菲涅耳反射率与透射率 -> 字典。 · 示例: `poc_water_inspection_images`, `poc_water_transparent_media`
- `ocean_height_field` `无输入 → table` GPU: 无 — 时刻 t 的 Tessendorf(2001)FFT 海面 -> 字典(高度、斜率、法线图、位移)。 · 示例: `poc_water_inspection_images`, `poc_water_transparent_media`
- `ocean_spectrum` `无输入 → table` GPU: 无 — 风浪的一维波谱 S(ω),及有效波高与峰值周期 -> 字典。 · 示例: `poc_water_transparent_media`
- `phase_function_hg` `无输入 → table` GPU: 无 — 在球面上归一化的 Henyey–Greenstein 相函数 -> 字典。 · 示例: `poc_water_transparent_media`
- `refracted_view` `无输入 → table` GPU: 无 — 水下的点在平坦或有波的水面上方的相机中出现在哪里(费马原理)-> 字典。 · 示例: `poc_water_transparent_media`
- `scattering_phase_petzold` `无输入 → table` GPU: 无 — 天然水体实测的体散射函数(Petzold 1972),以相函数形式给出 -> 字典。 · 示例: `poc_water_transparent_media`
- `snell_window` `无输入 → table` GPU: 无 — 从水面下一点看到的斯涅尔窗,以及平坦界面的视深度 -> 字典。 · 示例: `poc_water_transparent_media`
- `underwater_image` `rgbimage × image2d × image2d → table` GPU: 无 — 透过水记录的场景图像(修订版 Jaffe–McGlamery 模型)-> 字典。 · 示例: `poc_water_transparent_media`
- `water_attenuation` `无输入 → table` GPU: 无 — 水的吸收、散射与漫衰减系数,以及随深度的透过率 -> 字典。 · 示例: `poc_geodetic_height_frames`, `poc_water_inspection_images`, `poc_water_transparent_media`

#### optics / watervision (9)
- `bottle_background_map` `无输入 → table` GPU: 无 — 部分装有液体的瓶子的每个像素在带图案的平面背景上看向何处 -> 字典(背景坐标 u 的地图,单位 mm)。 · 示例: `poc_bottle_pattern_inverse`
- `bottle_fit_from_pattern` `无输入 → table` GPU: 无 — 从背景图案的畸变反推瓶子 -> 字典(半径、壁厚、折射率、液面,以及各量能确定到什么程度)。 · 示例: `poc_bottle_pattern_inverse`
- `bottle_image` `无输入 → table` GPU: 无 — 部分装有液体的圆柱形瓶子的侧视图,逐行进行光线追迹 -> 字典。 · 示例: `poc_bottle_pattern_inverse`, `poc_water_inspection_images`
- `caustic_floor_segmentation` `image2d → table` GPU: 仅在链中(许可列表) — 从地面照度图像中分割出焦散线 -> 字典(掩码、阈值、线的周期)。 · 示例: `poc_water_inspection_images`
- `caustic_irradiance` `image2d → table` GPU: 无 — 平行光在波动水面下方平坦底面上形成的照度 -> 字典。 · 示例: `poc_water_inspection_images`
- `fill_level_from_image` `image2d → table` GPU: 无 — 从瓶子侧视图像中测得的液面 -> 字典(距最下行的液位 mm、行号、置信度)。 · 示例: `poc_bottle_pattern_inverse`, `poc_water_inspection_images`
- `underwater_inspection_image` `rgbimage × image2d → table` GPU: 无 — 船体或管道检测图像:位于相机处的灯穿过水照亮墙面 -> 字典(图像、逐像素信噪比)。 · 示例: `poc_water_inspection_images`
- `wet_dry_inspection_pair` `image2d × image2d → table` GPU: 无 — 分别渲染同一块有纹理的板的干燥与湿润状态,并给出各自缺陷的对比度 -> 字典。 · 示例: `poc_water_inspection_images`
- `wet_surface_appearance` `无输入 → table` GPU: 无 — 薄水膜下表面的变暗与光泽(Lekner & Dorf 1988;Twomey 等 1986)-> 字典。 · 示例: `poc_water_inspection_images`

#### optics / wave (9)
- `airy_pattern` `无输入 → image2d` GPU: 无 — 圆形光瞳的衍射极限 PSF(艾里图样)。 · 示例: `anim3d_lens_aberrations`, `optics_imaging`, `poc_pixel_shift`, `poc_veiling_glare`
- `angular_spectrum_propagate` `cimage → cimage` GPU: 有(许可列表) — 复场的标量自由空间传播,精确解(角谱法)。 · 示例: `optics_imaging`, `poc_grating_interferometry`
- `defocus_from_shift` `无输入 → measurement` GPU: 无 — 把轴向焦点偏移换算为离焦波前误差(光瞳边缘处的波数)。 · 示例: `optics_imaging`, `poc_nir_silicon_transmission`
- `four_f_filter` `cimage × cimage → cimage` GPU: 有(许可列表) — 4f 光学处理器：经过 2 片透镜与傅里叶面滤波器后的输出。 · 示例: `optics_four_f_processor`
- `fourier_plane_filter` `无输入 → cimage` GPU: 无 — 放置于 4f 系统傅里叶面上的复透射函数 ``H(fx, fy)``。 · 示例: `optics_four_f_processor`
- `fraunhofer_pattern` `image2d → image2d` GPU: 有(许可列表) — 开口的远场(Fraunhofer)衍射强度。 · 示例: `optics_imaging`, `poc_beats_fringes_and_screens`
- `gaussian_beam` `无输入 → table` GPU: 无 — 高斯光束传播:光斑尺寸、波前曲率与 Gouy 相位。 · 示例: `optics_imaging`
- `pupil_blur` `image2d × image2d → image2d` GPU: 无 — 用某一波长带的光瞳形状 PSF 模糊图像。 · 示例: `optics_imaging`, `poc_nir_silicon_transmission`
- `pupil_psf` `image2d → image2d` GPU: 有(许可列表) — **任意形状光瞳**加离焦的衍射 PSF(总和为 1)。 · 示例: `optics_imaging`, `poc_wavefront_aberration_limits`

### lightfield (17 ops / 5 categories)

#### lightfield / decode (3)
- `lf_from_mla` `image2d → lightfield` GPU: 无 — 把微透镜阵列的原始帧解码成 ``(V, U, H, W)`` 光场。 · 示例: `lightfield_depth`
- `lf_stats` `lightfield → table` GPU: 无 — 描述一个光场:形状、角度中心,以及它能承载的斜率范围。 · 示例: `lightfield_depth`
- `lf_to_mla` `lightfield → image2d` GPU: 无 — 把光场重新交织成微透镜阵列的原始帧(精确逆变换)。 · 示例: `lightfield_depth`, `plenoptic_decode_pipeline`, `poc_lightfield_depth`

#### lightfield / depth (5)
- `lf_all_in_focus` `lightfield × image2d → image2d` GPU: 无 — 让每个像素按各自的斜率重聚焦,合成一张处处清晰的图。 · 示例: `lightfield_depth`, `poc_compound_eye`
- `lf_depth_from_focus` `lightfield → image2d` GPU: 无 — 由重聚焦扫描中的**锐度峰值**得到逐像素斜率。 · 示例: `lightfield_depth`, `plenoptic_decode_pipeline`, `poc_compound_eye`, `poc_lightfield_depth`, `poc_plenoptic_camera`
- `lf_disparity_to_depth` `image2d → depth` GPU: 有(许可列表) — 斜率(每角度步的像素数)-> 度量深度,相机阵列模型。 · 示例: `lightfield_depth`, `poc_lightfield_depth`
- `lf_epi_slope` `lightfield → image2d` GPU: 有(许可列表) — 由 **EPI 线的方向**得到逐像素斜率(结构张量,再用剪切细化)。 · 示例: `lightfield_depth`, `poc_lightfield_depth`
- `lf_plenoptic_design` `无输入 → table` GPU: 无 — 给全光相机定尺寸:能买到多少角度/空间分辨率与深度范围。 · 示例: `lightfield_depth`, `poc_compound_eye`

#### lightfield / refocus (4)
- `lf_aperture_mask` `无输入 → image2d` GPU: 无 — 角度方向的加权掩码 —— 你要收缩或塑形的合成孔径本身。 · 示例: `lightfield_depth`, `poc_compound_eye`
- `lf_focal_stack` `lightfield → images` GPU: 无 — 在 *slopes* 的每个斜率上重聚焦 —— 一次曝光得到一整叠焦点堆栈。 · 示例: `lightfield_depth`
- `lf_refocus` `lightfield → image2d` GPU: 无 — 移位相加重聚焦:聚焦在 *slope* 上的合成孔径图像。 · 示例: `lightfield_depth`, `plenoptic_decode_pipeline`, `poc_lightfield_depth`, `poc_plenoptic_camera`
- `lf_synthetic_aperture` `lightfield → image2d` GPU: 无 — 透过塑形孔径重聚焦 —— 用 ``reduce="median"`` 还能穿过遮挡物。 · 示例: `lightfield_depth`, `poc_compound_eye`

#### lightfield / synthesis (1)
- `lf_synthesize` `无输入 → lightfield` GPU: 无 — 用**已知**斜率的纹理层构建光场(试验台)。 · 示例: `lightfield_depth`, `plenoptic_decode_pipeline`, `poc_compound_eye`

#### lightfield / views (4)
- `lf_center_view` `lightfield → image2d` GPU: 无 — 中心视点 —— 全光相机同时给出的那张普通 2-D 图像。 · 示例: `lightfield_depth`
- `lf_epi` `lightfield → image2d` GPU: 仅在链中(许可列表) — 极平面图像 —— **线的斜率就是视差**的那个切片。 · 示例: `lightfield_depth`, `poc_lightfield_depth`
- `lf_subaperture` `lightfield → image2d` GPU: 无 — 一张子孔径视图 —— 透过瞳的一个点看到的图像。 · 示例: `lightfield_depth`, `poc_compound_eye`
- `lf_views` `lightfield → images` GPU: 无 — 把整个角度网格作为 2-D 图像的普通列表(按 ``(v, u)`` 行优先)。 · 示例: `lightfield_depth`

### photon (17 ops / 6 categories)

#### photon / counting (3)
- `photon_sample` `image2d → image2d` GPU: 无 — 把期望光子数图像做泊松采样,得到实际的光子计数图像。 · 示例: `photon_timeresolved`, `poc_colocalization_crosstalk`, `poc_search_sweep_width`
- `photon_statistics` `image2d → table` GPU: 无 — 光子计数帧的泊松统计:它真的是散粒噪声受限的吗? · 示例: `photon_timeresolved`
- `photon_uncertainty` `image2d → image2d` GPU: 仅在链中(许可列表) — 光子计数帧逐像素的泊松误差棒。 · 示例: `photon_timeresolved`, `poc_thermal_radiometry`

#### photon / dtof (3)
- `dtof_cube_depth` `histcube → depth` GPU: 无 — 由 ``(H, W, T)`` 光子直方图立方体得到深度图 —— dToF 的反演。 · 示例: `photon_timeresolved`, `poc_dtof_ranging`, `poc_itof_multifreq`, `poc_tof_camera`
- `dtof_cube_simulate` `depth → histcube` GPU: 无 — 合成 SPAD 阵列产生的 ``(H, W, T)`` 光子直方图立方体。 · 示例: `photon_timeresolved`, `poc_dtof_ranging`, `poc_itof_multifreq`, `poc_tof_camera`
- `dtof_depth` `counts → measurement` GPU: 无 — 由光子到达时间直方图求距离:``d = c*t/2``。 · 示例: `photon_timeresolved`, `poc_dtof_ranging`

#### photon / lifetime (2)
- `lifetime_fit` `counts → table` GPU: 无 — 由 TCSPC 衰减直方图求单指数荧光寿命。 · 示例: `photon_timeresolved`
- `lifetime_phasor` `counts → table` GPU: 无 — 衰减的相量(频域)表示 —— 不需拟合的视角。 · 示例: `photon_timeresolved`

#### photon / spad (3)
- `spad_deadtime_apply` `countrate → countrate` GPU: 无 — 用探测器的死时间扭曲真实光子率(计数丢失)。 · 示例: `photon_timeresolved`, `poc_dtof_ranging`
- `spad_deadtime_correct` `countrate → countrate` GPU: 无 — 由被死时间扭曲的测量率恢复真实光子率。 · 示例: `photon_timeresolved`
- `tcspc_coates_correct` `counts → counts` GPU: 无 — 精确消除 TCSPC 堆积效应(Coates 估计量)—— 早到光子偏差。 · 示例: `photon_timeresolved`, `poc_dtof_ranging`

#### photon / tcspc (4)
- `tcspc_background_subtract` `counts → counts` GPU: 无 — 从到达时间直方图中去掉环境光 / 暗计数的底噪。 · 示例: `photon_timeresolved`, `poc_dtof_ranging`
- `tcspc_irf_convolve` `counts → counts` GPU: 无 — 用仪器响应(定时抖动)模糊到达时间直方图。 · 示例: `photon_timeresolved`
- `tcspc_simulate` `无输入 → counts` GPU: 无 — 合成答案已知的单像素光子到达时间直方图。 · 示例: `photon_timeresolved`, `poc_dtof_ranging`
- `tcspc_stats` `counts → table` GPU: 无 — 到达时间直方图的描述量:峰、重心、宽度、背景。 · 示例: `photon_timeresolved`

#### photon / transform (2)
- `anscombe_inverse` `image2d → image2d` GPU: 有(许可列表) — 对 :func:`anscombe_transform` 求逆 —— 代数式的,或去偏的。 · 示例: `photon_timeresolved`
- `anscombe_transform` `image2d → image2d` GPU: 仅在链中(许可列表) — Anscombe 方差稳定化变换:泊松计数 -> 方差约为 1。 · 示例: `photon_timeresolved`

### specular (20 ops / 5 categories)

#### specular / deflectometry (6)
- `deflectometry_phase_to_slope` `image2d × image2d → normalmap` GPU: 有(许可列表) — 两张屏幕绝对相位(u 方向与 v 方向的条纹)→ 被测面网格上的法线图 (H, W, 3)。 · 示例: `poc_phase_measuring_deflectometry`
- `deflectometry_render` `image2d → images` GPU: 有(许可列表) — 高度场 → 相机拍到的“屏幕的镜像”(正向仿真)。→ 图像列表(每张 (H, W),[0, 1])。 · 示例: `poc_phase_measuring_deflectometry`
- `deflectometry_rig` `无输入 → table` GPU: 无 — 把偏折术装置(相机、屏幕、视野)的几何关系整理成一张表(dict)。 · 示例: `poc_phase_measuring_deflectometry`
- `deflectometry_screen_pattern` `无输入 → images` GPU: 无 — 在屏幕上显示的图案(屏幕像素网格)。→ 图像列表(每张 (行, 列),值 [0, 1])。 · 示例: `poc_phase_measuring_deflectometry`
- `deflectometry_sensitivity` `无输入 → table` GPU: 无 — 测量前以闭式给出最小可检测斜率、高度与斜率不定性的系数以及对焦模糊。→ dict。 · 示例: `poc_phase_measuring_deflectometry`
- `slope_to_curvature` `normalmap → image2d` GPU: 无 — 法线图 (H, W, 3) → 曲率图 (H, W)。只对斜率求一次导数,不积分成高度。 · 示例: `poc_phase_measuring_deflectometry`

#### specular / dichromatic (4)
- `illuminant_from_dichromatic_planes` `rgbimage × labels → vector` GPU: 无 — 由两种以上材质恢复光源颜色。→ 单位 3 向量。 · 示例: `poc_white_balance`, `specular_photometric`
- `specular_coefficient_map` `rgbimage → image2d` GPU: 有(许可列表) — 二色性模型中标量的界面(镜面)系数。→ (H, W)。 · 示例: `specular_photometric`
- `specular_diffuse_split` `rgbimage → rgbimage` GPU: 无 — 把线性 RGB 图像分成漫反射(体)与镜面(界面)两部分。→ (diffuse, specular),都是 (H, W, 3)。 · 示例: `specular_photometric`
- `specular_free_transform` `rgbimage → rgbimage` GPU: 仅在链中(许可列表) — 投影掉光源方向:高光碰不到的那部分图像。→ (H, W, 3)。 · 示例: `poc_leaf_disease_area`, `specular_photometric`

#### specular / photometric (2)
- `photometric_residual` `images → image2d` GPU: 有(许可列表) — Lambert 模型逐像素的失配程度。→ (H, W) 的 RMS 残差。 · 示例: `specular_photometric`
- `photometric_stereo_robust` `images → normalmap` GPU: 无 — 能扛住阴影与高光的光度立体。→ (法线, 反照率, 内点)。 · 示例: `poc_3d_sensor_modalities`, `poc_shape_from_polarization`, `specular_photometric`

#### specular / polarization (5)
- `polarization_dolp_map` `polsweep → image2d` GPU: 无 — 逐像素的线偏振度。→ [0, 1] 的 (H, W)。 · 示例: `example_polarization_metal`, `perf_polarization_analyze`, `poc_polarization_specular`, `polarization_camera_pipeline`, `specular_photometric`
- `polarization_render` `image2d × image2d → polsweep` GPU: 仅在链中(许可列表) — 偏振片旋转的正向模型:把已知的分离变成偏振相机会记录到的帧序列。→ (N, H, W)。 · 示例: `example_polarization_metal`, `poc_polarization_specular`, `specular_photometric`
- `polarization_separate` `polsweep → image2d` GPU: 无 — 把偏振片旋转序列分成非偏振与线偏振的辐亮度。→ (diffuse, specular),都是 (H, W)。 · 示例: `perf_polarization_analyze`, `poc_polarization_specular`, `specular_photometric`
- `polarization_stokes` `polsweep → stokes` GPU: 无 — 偏振片旋转序列的场景积分 Stokes 矢量。→ (4,),可直接交给 :func:`optics.stokes_analyze`。 · 示例: `perf_polarization_analyze`, `poc_polarization_specular`, `polarization_camera_pipeline`, `specular_photometric`
- `polarization_stokes_map` `polsweep → table` GPU: 无 — 由检偏器扫描(DoFP 的 4 个方位,或任意 N >= 3 个方位的最小二乘)得到逐像素线性 Stokes 图像以及 DoLP、AoLP 图。→ (H, W) 图的 dict。 · 示例: `polarization_camera_pipeline`

#### specular / reflectance (3)
- `brdf_blinn_phong` `normalmap → image2d` GPU: 无 — Blinn 的半向量镜面波瓣。→ [0, 1] 的 (H, W)。 · 示例: `poc_shape_from_polarization`, `specular_photometric`
- `brdf_microfacet` `normalmap → image2d` GPU: 无 — GGX / Trowbridge-Reitz 微面元镜面 BRDF。→ (H, W),单位 1/sr。 · 示例: `poc_solder_fillet_aoi`, `specular_photometric`
- `dichromatic_render` `normalmap → rgbimage` GPU: 无 — 二色性模型的正向:渲染一个已知高光,以便据此检验分离结果。→ (H, W, 3)。 · 示例: `specular_photometric`

### motionmag (9 ops / 5 categories)

#### motionmag / decompose (2)
- `complex_steerable_decompose` `image2d → table` GPU: 无 — 单帧的复数方向选择子带分解 -> ``dict``。 · 示例: `motion_magnification`
- `complex_steerable_reconstruct` `table → image2d` GPU: 无 — 对 :func:`complex_steerable_decompose` 求逆 -> ``(H, W)`` 实图像。 · 示例: `motion_magnification`

#### motionmag / magnify (1)
- `motion_magnify` `video → table` GPU: 有(许可列表) — 把片段带内的运动放大 *alpha* 倍 -> ``dict``。 · 示例: `motion_magnification`, `poc_motion_magnification`, `quaternion_monogenic`

#### motionmag / measure (2)
- `displacement_series` `video → pairs` GPU: 有(许可列表) — 整帧位移波形 -> ``(dx, dy)`` 的 ``(T, 2)`` 数组。 · 示例: `motion_magnification`, `poc_motion_magnification`, `quaternion_monogenic`
- `phase_displacement` `video → table` GPU: 有(许可列表) — 由局部相位得到的亚像素位移场 -> ``dict``。 · 示例: `motion_magnification`, `poc_beam_modal_video`, `poc_motion_magnification`, `quaternion_monogenic`

#### motionmag / synthesis (1)
- `synthesize_translation` `无输入 → video` GPU: 无 — 位移有闭式解的片段 -> ``(T, H, W)`` 视频。 · 示例: `motion_magnification`, `poc_motion_magnification`, `quaternion_monogenic`

#### motionmag / temporal (3)
- `band_snr` `video → table` GPU: 无 — 测量片段的时间频带里有什么、代价是什么 -> ``dict``。 · 示例: `motion_magnification`, `poc_motion_magnification`
- `temporal_band_power` `video → image2d` GPU: 有(许可列表) — 时间频带内逐像素的均方功率 -> ``(H, W)`` 图。 · 示例: `motion_magnification`, `poc_motion_magnification`
- `temporal_bandpass` `video → video` GPU: 有(许可列表) — 对每个像素时间序列的理想时间带通 -> ``(T, H, W)``。 · 示例: `motion_magnification`, `poc_beam_modal_video`, `poc_motion_magnification`

### quat (19 ops / 7 categories)

#### quat / algebra (3)
- `quat_conjugate_image` `qimage → qimage` GPU: 无 — 逐像素的四元数共轭 ``(w, -x, -y, -z)``。→ (H, W, 4)。 · 示例: `quaternion_monogenic`
- `quat_image_multiply` `qimage × qimage → qimage` GPU: 有(许可列表) — 四元数图像与一个四元数或一个场的 Hamilton 积。→ (H, W, 4)。 · 示例: `quaternion_monogenic`
- `quat_normalize_image` `qimage → qimage` GPU: 无 — 逐像素归一化到单位模。→ (H, W, 4)。 · 示例: `quaternion_monogenic`

#### quat / color (2)
- `quat_color_filter` `qimage → qimage` GPU: 无 — 精确地保留或去除某一个颜色方向。→ (H, W, 4)。 · 示例: `quaternion_monogenic`
- `quat_color_rotate` `qimage → qimage` GPU: 无 — 把每个像素的颜色绕 RGB 轴旋转:``q x conj(q)``。→ (H, W, 4)。 · 示例: `quaternion_monogenic`

#### quat / convert (3)
- `quat_norm` `qimage → image2d` GPU: 无 — 逐像素的四元数模 ``|q| = sqrt(w^2+x^2+y^2+z^2)``。→ (H, W)。 · 示例: `quaternion_monogenic`
- `quaternion_to_rgb` `qimage → rgbimage` GPU: 仅在链中(许可列表) — 取四元数图像的向量部,作为线性 RGB。→ (H, W, 3)。 · 示例: `quaternion_monogenic`
- `rgb_to_quaternion` `rgbimage → qimage` GPU: 无 — 把彩色图像嵌入为纯四元数 ``0 + R i + G j + B k``。→ (H, W, 4)。 · 示例: `quaternion_monogenic`

#### quat / fourier (2)
- `iqft2` `qimage → qimage` GPU: 有(许可列表) — **中心化**频谱的逆四元数傅里叶变换。→ (H, W, 4)。 · 示例: `quaternion_monogenic`
- `qft2` `qimage → qimage` GPU: 有(许可列表) — 四元数(超复数)2-D 傅里叶变换。→ 中心化的 (H, W, 4) 频谱。 · 示例: `quaternion_monogenic`

#### quat / match (1)
- `quat_correlate` `qimage × qimage → qimage` GPU: 有(许可列表) — 四元数互相关 ``sum_s conj(a(s)) * b(s+t)``。→ (H, W, 4)。 · 示例: `quaternion_monogenic`

#### quat / motion (3)
- `riesz_displacement` `video → table` GPU: 有(许可列表) — 由单演相位得到的亚像素位移场。→ dict。 · 示例: `quaternion_monogenic`
- `riesz_displacement_series` `video → pairs` GPU: 有(许可列表) — 由单演相位得到的整帧位移波形。→ (T, 2)。 · 示例: `quaternion_monogenic`
- `riesz_motion_magnify` `video → table` GPU: 有(许可列表) — 沿 Riesz 路线把片段带内的运动放大 *alpha* 倍。→ dict。 · 示例: `quaternion_monogenic`

#### quat / riesz (5)
- `monogenic_amplitude` `qimage → image2d` GPU: 仅在链中(许可列表) — 单演信号的局部幅度 ``sqrt(f^2 + R1^2 + R2^2)``。→ (H, W)。 · 示例: `perf_monogenic_metrics`, `quaternion_monogenic`
- `monogenic_orientation` `qimage → image2d` GPU: 无 — 单演信号的局部方向 ``atan2(R2, R1)``。→ (H, W)。 · 示例: `perf_monogenic_metrics`, `quaternion_monogenic`
- `monogenic_phase` `qimage → image2d` GPU: 有(许可列表) — 单演信号的局部相位 ``atan2(|R|, f)``。→ (H, W)。 · 示例: `perf_monogenic_metrics`, `quaternion_monogenic`
- `monogenic_signal` `image2d → qimage` GPU: 无 — 某一尺度下图像的单演信号。→ (H, W, 4)。 · 示例: `perf_monogenic_metrics`, `quaternion_monogenic`
- `riesz_transform` `image2d → qimage` GPU: 无 — 图像的 2-D Riesz 变换,作为纯四元数场。→ (H, W, 4)。 · 示例: `quaternion_monogenic`

### rangedoppler (8 ops / 4 categories)

#### rangedoppler / beamform (2)
- `beamform_delay_sum` `beatcube → signal` GPU: 无 — 单个距离-多普勒单元的延迟求和(Bartlett)角度谱。 · 示例: `fmcw_range_doppler`, `poc_multibeam_bathymetry`
- `beamform_doa` `beatcube → table` GPU: 无 — 单个距离-多普勒单元的到达方向 [deg]。 · 示例: `fmcw_range_doppler`, `poc_multibeam_bathymetry`

#### rangedoppler / design (1)
- `fmcw_design` `无输入 → table` GPU: 无 — FMCW 配置的 bin 宽度、分辨率与混叠极限。 · 示例: `fmcw_range_doppler`

#### rangedoppler / process (4)
- `fmcw_range_profile` `beatcube → signal` GPU: 无 — 仅距离的剖面:快时间 FFT 的幅度,在其余轴上平均。 · 示例: `fmcw_range_doppler`
- `fmcw_window_apply` `beatcube → beatcube` GPU: 无 — 沿拍频立方体的距离轴和/或多普勒轴施加周期窗。 · 示例: `fmcw_range_doppler`
- `range_doppler_map` `beatcube → image2d` GPU: 无 — 拍频立方体的 2-D FFT -> ``(n_doppler, n_range)`` 幅度图。 · 示例: `fmcw_range_doppler`
- `range_doppler_peaks` `image2d → table` GPU: 无 — 由距离-多普勒图得到检测:把 bin 索引换回米与 m/s。 · 示例: `fmcw_range_doppler`

#### rangedoppler / simulate (1)
- `fmcw_beat_simulate` `无输入 → beatcube` GPU: 无 — 为已知目标合成复数 ``(A, C, S)`` 拍频立方体。 · 示例: `fmcw_range_doppler`

### acoustics (27 ops / 7 categories)

#### acoustics / bearing (4)
- `bearing_defect_frequencies` `无输入 → table` GPU: 无 — 由几何求滚动轴承的四个特征频率。 · 示例: `acoustic_condition_monitoring`, `poc_bearing_diagnosis`, `poc_machine_condition_fusion`
- `cepstrum` `signal → table` GPU: 有(许可列表) — 对数谱的谱 —— 看**频率轴上**的周期结构。 · 示例: `acoustic_condition_monitoring`, `poc_web_roll_periodicity`
- `envelope_spectrum` `signal → table` GPU: 无 — 带通 → 解调 → 变换。轴承缺陷真正显现的地方。 · 示例: `acoustic_condition_monitoring`, `poc_bearing_diagnosis`
- `spectral_kurtosis` `signal → table` GPU: 无 — 哪个频带是冲击性的 —— 也就是该在哪里解调。 · 示例: `acoustic_condition_monitoring`, `poc_bearing_diagnosis`

#### acoustics / dual (3)
- `coherence` `signal × signal → table` GPU: 无 — 普通相干:``y`` 中能被 ``x`` 线性解释的比例。 · 示例: `acoustic_condition_monitoring`, `poc_zebra_stripes_fly_eye`
- `gcc_delay` `signal × signal → measurement` GPU: 无 — 用广义互相关(GCC)测量 2 个通道的**到达时间差**。→ ``(delay, table)``。 · 示例: `acoustic_condition_monitoring`
- `transfer_function` `signal × signal → table` GPU: 无 — 以 ``x`` 为输入、``y`` 为输出估计 ``H(f)``,并给出相干。 · 示例: `acoustic_condition_monitoring`, `poc_leak_localization`

#### acoustics / level (6)
- `apply_weighting` `signal → signal` GPU: 有(许可列表) — 对信号施加 A / C / Z 频率计权,零相位。 · 示例: `acoustic_condition_monitoring`
- `equivalent_level` `signal → measurement` GPU: 无 — 记录的能量等效级,以 ``ref`` 为基准的 dB。 · 示例: `acoustic_condition_monitoring`
- `octave_bands` `无输入 → table` GPU: 无 — 由定义的构造给出 1/N 倍频程的中心频率与带边。 · 示例: `acoustic_condition_monitoring`, `poc_rail_corrugation`
- `octave_spectrum` `signal → table` GPU: 无 — 按 Parseval 在 1/N 倍频程带内求和的 dB 带级。 · 示例: `acoustic_condition_monitoring`, `poc_rail_corrugation`
- `percentile_level` `signal → table` GPU: 有(许可列表) — 统计级:``L_N`` 是有 ``N`` % 的时间被超过的级。 · 示例: `acoustic_condition_monitoring`
- `weighting_response` `signal → signal` GPU: 有(许可列表) — 给定频率处的 A / C / Z 频率计权曲线 [dB]。 · 示例: `acoustic_condition_monitoring`

#### acoustics / order (2)
- `angular_resample` `signal → table` GPU: 无 — 把时间记录重采样到轴角轴上(计算阶次跟踪)。 · 示例: `acoustic_condition_monitoring`
- `order_spectrum` `signal → table` GPU: 无 — 对轴阶次的幅度 —— 升速过程本该用这张谱来读。 · 示例: `acoustic_condition_monitoring`

#### acoustics / synthesis (2)
- `synthesize_bearing_signal` `无输入 → signal` GPU: 无 — 以已知缺陷频率调幅的共振 —— 答案已知的真值。 · 示例: `acoustic_condition_monitoring`, `poc_bearing_diagnosis`, `poc_machine_condition_fusion`
- `synthesize_speed_ramp` `无输入 → table` GPU: 无 — 升速过程:成分锁定在轴**阶次**上(可选一条固定在 Hz)。 · 示例: `acoustic_condition_monitoring`

#### acoustics / transform (3)
- `istft` `table → signal` GPU: 无 — 用加权重叠相加精确地逆 :func:`stft`。 · 示例: `acoustic_condition_monitoring`
- `stft` `signal → table` GPU: 无 — 保留相位且可逆的短时傅里叶变换。 · 示例: `acoustic_condition_monitoring`
- `stft_cola_check` `无输入 → table` GPU: 无 — 这组(窗, 跳距)是否满足 COLA,以及满足得有多精确。 · 示例: `acoustic_condition_monitoring`

#### acoustics / ultrasonic (7)
- `acoustic_interface_coefficients` `table → table` GPU: 无 — 层叠结构每个界面的压力反射/透射系数、能量守恒 R² + (Z1/Z2)T² = 1 的校验,以及 Z2 < Z1 时的相位反转标记(``table``)。 · 示例: `poc_sam_hybrid_bonding_voids`
- `acoustic_layer_stack` `无输入 → table` GPU: 无 — 用于垂直入射脉冲回波的层叠结构:耦合液、自上而下的各层(材料, 厚度 [m])以及半无限基底(``table``)。
- `acoustic_material_table` `无输入 → table` GPU: 无 — 内置声学材料表:密度、纵波声速、声阻抗 Z = ρc、衰减 α0·f^n,每项附出处与是否已核实的标记(``table``)。 · 示例: `poc_sam_hybrid_bonding_voids`
- `echo_phase_polarity` `table → table` GPU: 无 — 按相对于表面回波的相位对界面回波分类:同相(Z 增大)、反相(Z 减小)或正交(薄层,符号无意义)(``table``)。 · 示例: `poc_sam_hybrid_bonding_voids`
- `pulse_echo_ascan` `table → table` GPU: 无 — 层叠结构对垂直入射宽带脉冲的射频 A 扫描:传递矩阵的层叠响应、水路程与幂律衰减(``table``)。 · 示例: `poc_sam_hybrid_bonding_voids`
- `sam_cscan` `labels2d × table → table` GPU: 无 — 对二维键合面图进行聚焦探头 C 扫描:逐频率的高斯横向 PSF、界面处的时间门,输出幅值、相位、同相(带符号)与带符号峰值图像(``table``)。 · 示例: `poc_sam_hybrid_bonding_voids`
- `sam_frequency_tradeoff` `table → table` GPU: 无 — 埋藏界面上给定尺寸空洞的最佳 SAM 频率:横向填充率 1 − 2^−(a/w)²(w = k_res·λ_w·F#)与往返衰减的权衡;衰减均按 f² 时有闭式解(``table``)。 · 示例: `poc_sam_hybrid_bonding_voids`

### interferometry (9 ops / 6 categories)

#### interferometry / chromatic (1)
- `chromatic_confocal_height` `sweep → measurement` GPU: 无 — 由一条共焦回光光谱求表面高度 —— 波长**就是**高度。 · 示例: `coherence_scanning`

#### interferometry / design (1)
- `csi_design` `无输入 → table` GPU: 无 — 由光源光谱决定的相干扫描系统的轴向极限。 · 示例: `coherence_scanning`, `poc_interferometry_step`

#### interferometry / envelope (1)
- `csi_envelope` `sweep → signal` GPU: 无 — z 扫描干涉图的相干包络(解析信号的模)。 · 示例: `coherence_scanning`

#### interferometry / locate (1)
- `csi_peak_position` `sweep → measurement` GPU: 无 — 由一次 z 扫描求表面高度:相干包络峰的位置。 · 示例: `coherence_scanning`

#### interferometry / simulate (3)
- `chromatic_confocal_simulate` `无输入 → sweep` GPU: 无 — 合成位于已知高度的表面的共焦回光光谱。 · 示例: `coherence_scanning`
- `csi_signal_simulate` `无输入 → sweep` GPU: 无 — 合成已知表面高度处一个像素的 z 扫描干涉图。 · 示例: `coherence_scanning`
- `csi_stack_simulate` `depth → zscan` GPU: 无 — 合成干涉显微镜记录的 ``(Z, H, W)`` 扫描堆栈。 · 示例: `coherence_scanning`, `poc_interferometry_step`

#### interferometry / surface (2)
- `csi_contrast_map` `zscan → image2d` GPU: 无 — 逐像素的条纹调制峰值 —— 对比度(以及有效性)图。 · 示例: `coherence_scanning`, `poc_interferometry_step`
- `csi_height_map` `zscan → depth` GPU: 无 — 由 ``(Z, H, W)`` 相干扫描堆栈得到高度图 —— CSI 的逆问题。 · 示例: `coherence_scanning`, `poc_focus_stacking`, `poc_interferometry_step`

### flyvision (22 ops / 12 categories)

#### flyvision / alias (2)
- `lattice_moire_peak` `signal × table → table` GPU: 无 — 采样信号中最强低频成分的尖锐程度——晶格对无法分辨的纹理所产生的莫尔条纹。 · 示例: `poc_moire_screen`, `poc_print_registration`, `poc_zebra_stripes_fly_eye`
- `sampling_alias_distance` `无输入 → table` GPU: 无 — 周期性目标在采样晶格上发生混叠的距离——检测相机工作距离的规则。 · 示例: `poc_zebra_stripes_fly_eye`

#### flyvision / direction (2)
- `fly_flow_from_directions` `matrix × table → matrix` GPU: 无 — 输入每个小眼的六个方向响应，输出一个局部光流向量。 · 示例: `poc_fly_optomotor_steering`, `poc_zebra_stripes_fly_eye`
- `fly_t4t5_field` `matrix × table → matrix` GPU: 无 — 全眼范围、六个六角方向上的方向选择性响应。 · 示例: `poc_fly_optomotor_steering`, `poc_zebra_stripes_fly_eye`

#### flyvision / integrate (1)
- `fly_hs_readout` `matrix × table → measurement` GPU: 无 — 水平系统(HS)宽视野读出：上半视野的对抗(opponent)求和。 · 示例: `poc_fly_vision`

#### flyvision / lamina (2)
- `fly_lamina_filter` `matrix → matrix` GPU: 无 — 光感受器适应 + 视叶板层(lamina)的带通：输入亮度，输出对比度。 · 示例: `poc_fly_optomotor_steering`
- `fly_onoff_split` `matrix → matrix` GPU: 无 — 把对比度影片拆分为髓质(medulla)所承载的 ON 与 OFF 通道。 · 示例: `poc_fly_optomotor_steering`

#### flyvision / lattice (2)
- `fly_hex_lattice` `无输入 → table` GPU: 无 — 六角形小眼晶格：复眼的视线方向。 · 示例: `poc_fly_optomotor_steering`, `poc_fly_vision`, `poc_print_registration`, `poc_zebra_stripes_fly_eye`
- `fly_vogel_lattice` `无输入 → table` GPU: 无 — 斐波那契（Vogel 螺旋）复眼：与六角眼相同的小眼数和平均间距，但没有晶格。 · 示例: `poc_print_registration`, `poc_zebra_stripes_fly_eye`

#### flyvision / looming (3)
- `fly_expansion_readout` `matrix × table → table` GPU: 无 — 由整个眼的光流读出碰撞时间——孔径效应给出恰好 2 倍。 · 示例: `poc_zebra_stripes_fly_eye`
- `fly_lgmd_eta` `signal → signal` GPU: 无 — 由扩张的视张角得到的 LGMD/eta 逼近(looming)响应。 · 示例: `poc_fly_vision`
- `fly_tau_from_expansion` `signal → signal` GPU: 有(许可列表) — 由光学扩张得到的碰撞时间——tau 余量。 · 示例: `poc_fly_vision`, `poc_zebra_stripes_fly_eye`

#### flyvision / motion (1)
- `fly_emd_response` `signal × signal → signal` GPU: 无 — 两个相邻小眼信号之间的 Hassenstein-Reichardt 相关器。 · 示例: `poc_fly_vision`, `poc_zebra_stripes_fly_eye`

#### flyvision / sample (2)
- `fly_hex_quantize` `signal → signal` GPU: 有(许可列表) — 以与眼睛相同的方式量化小眼信号：先做对数压缩，再对每个小眼取 n 位(``mode="onoff"`` 为 ON / OFF 2 个通道)。 · 示例: `poc_eye_to_brain`
- `fly_hex_resample` `image2d × table → signal` GPU: 无 — 把针孔图像重采样到小眼晶格上(眼所见之像)。 · 示例: `poc_fly_optomotor_steering`, `poc_fly_vision`

#### flyvision / selfmotion (3)
- `fly_egomotion_from_flow` `matrix × table → table` GPU: 无 — 由光流场以最小二乘求眼的旋转——以及眼自身的形状使该解的条件数变得多差。 · 示例: `poc_fly_optomotor_steering`
- `fly_eye_merge` `table × table → table` GPU: 无 — 把多个晶格视为一只宽视野的眼——合并它们全部的视线方向。 · 示例: `poc_fly_optomotor_steering`
- `fly_matched_filter` `table → matrix` GPU: 无 — 单位自运动在眼上写下的光流场——宽视野神经元所匹配的模板。 · 示例: `poc_fly_optomotor_steering`

#### flyvision / stimulus (2)
- `fly_sky_1f` `无输入 → image2d` GPU: 无 — 带有条带状 1/f 方位纹理的合成等距柱状天空全景。 · 示例: `poc_fly_optomotor_steering`, `poc_fly_vision`
- `fly_view_plane_texture` `table → signal` GPU: 无 — 每个小眼如何看到正面的周期性表面——解析积分（不重采样图像）。 · 示例: `poc_zebra_stripes_fly_eye`

#### flyvision / trajectory (1)
- `traj_tau_dot` `points × signal → table` GPU: 无 — 沿实测 3-D 轨迹的距离、接近速度、tau 与 tau 的导数。 · 示例: `poc_zebra_stripes_fly_eye`

#### flyvision / tuning (1)
- `fly_dsi` `signal → table` GPU: 无 — 由方向调谐响应求方向选择性指数与偏好方向。 · 示例: `poc_fly_vision`

### spc (41 ops / 11 categories)

#### spc / anomaly_eval (7)
- `anomaly_image_auroc` `signal × signal → table` GPU: 无 — 由每张图像的异常分数与良/不良标签计算图像级 AUROC(``table``)。 · 示例: `anomaly_eval_metrics`, `poc_ai_built_inspection_scored`, `poc_good_sample_variation_model`, `poc_patch_anomaly`
- `anomaly_image_f1_max` `signal × signal → table` GPU: 无 — 由每张图像的异常得分与良/不良标签,求遍历所有阈值的图像级 F1 最大值(``table``)。
- `anomaly_operating_point` `signal × signal → table` GPU: 无 — 选出能以 ``confidence`` 的置信水平保证缺陷召回率不低于 ``recall`` 的最高阈值(``table``)。 · 示例: `poc_patch_anomaly`
- `anomaly_pixel_auroc` `video × video → table` GPU: 无 — 由异常分数图与缺陷真值掩膜计算像素级 AUROC(``table``)。 · 示例: `anomaly_eval_metrics`, `poc_good_sample_variation_model`, `poc_patch_anomaly`
- `anomaly_pixel_f1_max` `video × video → table` GPU: 无 — 由异常得分图与缺陷掩膜,求遍历所有阈值的像素级 F1 最大值(``table``)。 · 示例: `poc_patch_anomaly`
- `anomaly_pro` `video × video → table` GPU: 有(许可列表) — 按缺陷连通区域计算的重叠率(PRO)曲线,及积分到 ``fpr_max`` 的归一化面积 AUPRO(``table``)。 · 示例: `anomaly_eval_metrics`, `poc_good_sample_variation_model`, `poc_patch_anomaly`
- `anomaly_region_overlap` `video × video → table` GPU: 仅在链中(许可列表) — 单一工作点下二值缺陷预测与真值各区域的重叠率(``table``)。 · 示例: `anomaly_eval_metrics`, `poc_ai_built_inspection_scored`, `poc_good_sample_variation_model`, `poc_patch_anomaly`

#### spc / anomaly_patch (5)
- `patch_features` `image2d → table` GPU: 有(许可列表) — 网格上的经典图块特征:每个图块一个 D 维向量(梯度、Gabor、LBP、频带、颜色)(``table``)。 · 示例: `poc_patch_anomaly`
- `patchbank_fit` `video → table` GPU: 无 — 建立良品图块特征的记忆库,并用贪心 k 中心覆盖进行稀疏化(``table``)。 · 示例: `poc_ai_built_inspection_scored`, `poc_patch_anomaly`
- `patchbank_score` `image2d × table → table` GPU: 无 — 将一张图像与记忆库比较:由各图块到最近 k 个良品图块的距离生成异常图(``table``)。 · 示例: `poc_ai_built_inspection_scored`, `poc_patch_anomaly`
- `patchdist_fit` `video → table` GPU: 无 — 从良品图像学习每个网格位置上图块特征的正态分布(声明收缩估计,协方差奇异则拒绝)(``table``)。 · 示例: `poc_patch_anomaly`
- `patchdist_score` `image2d × table → table` GPU: 无 — 将一张图像与逐位置的正态分布比较:由各图块的马氏距离生成异常图(``table``)。

#### spc / capability (1)
- `spc_capability` `signal → table` GPU: 无 — 由测量值与规格限求过程能力指数 Cp 与 Cpk。 · 示例: `poc_spc`

#### spc / change (2)
- `spc_cusum` `signal → table` GPU: 无 — 针对单值测量的表格式 CUSUM 控制图。 · 示例: `poc_spc`
- `spc_ewma` `signal → table` GPU: 无 — 针对单值测量的 EWMA 控制图(Roberts 1959)。 · 示例: `poc_spc`

#### spc / chart (1)
- `spc_xbar_r` `matrix → table` GPU: 无 — 由子组测量得到的 Shewhart Xbar-R 控制图。 · 示例: `poc_spc`

#### spc / msa (4)
- `msa_anova_table` `table → table` GPU: 无 — 交叉双因子设计(零件 x 测量者 x 重复)的方差分析表(``table``)。 · 示例: `poc_measurement_system_analysis`
- `msa_attribute_agreement` `table → table` GPU: 无 — 计数型(合格/不合格)检验中检验员之间的一致性(``table``)。 · 示例: `poc_measurement_system_analysis`, `poc_weed_rice_ratio`
- `msa_bias_linearity` `table → table` GPU: 无 — 相对于参考值的偏倚,以及该偏倚随参考值的变化(线性)(``table``)。 · 示例: `poc_measurement_system_analysis`
- `msa_gauge_rr` `table → table` GPU: 无 — 基于方差分析法的量具重复性与再现性(``table``)。 · 示例: `poc_measurement_system_analysis`

#### spc / mt (3)
- `spc_mt_distance` `matrix → table` GPU: 无 — 以 MT 法单位空间为基准给观测打分。 · 示例: `poc_mt_hidden_fault`, `poc_spc`
- `spc_mt_sn_ratio` `signal → table` GPU: 无 — 由异常样本距离求望大特性 SN 比，单位为分贝。 · 示例: `poc_spc`
- `spc_mt_unit_space` `matrix → table` GPU: 无 — 由已知良品的观测构建 MT 法单位空间。 · 示例: `poc_mt_hidden_fault`, `poc_spc`

#### spc / multivariate (1)
- `spc_hotelling_t2` `matrix → table` GPU: 无 — 基于 Hotelling T² 的多变量 SPC，控制限按所处阶段选取(第 I 阶段用 Beta 分布，参数已知时用 χ² 分布)。 · 示例: `poc_spc`

#### spc / pod (7)
- `pod_ahat_fit` `table → table` GPU: 无 — 以带左右删失的最大似然法拟合 â 对 a 的回归(``table``)。 · 示例: `poc_equipment_selection_map`, `poc_pod_lighting`, `poc_sam_hybrid_bonding_voids`
- `pod_decision_tradeoff` `table × signal → table` GPU: 无 — 改变判定阈值 ``a_dec`` 时 (a50, a90, a90/95, 误检概率) 的权衡表(``table``)。 · 示例: `poc_pod_lighting`
- `pod_false_call` `signal → table` GPU: 无 — 由无缺陷部位的响应 ``noise`` 与判定阈值 ``a_dec`` 求误检概率(``table``)。 · 示例: `poc_equipment_selection_map`, `poc_pod_lighting`, `poc_sam_hybrid_bonding_voids`
- `pod_from_ahat` `table → table` GPU: 无 — 由 â 对 a 的回归与判定阈值 ``a_dec`` 求 POD(a) 曲线及 a50 / a90 / a90/95(``table``)。 · 示例: `poc_equipment_selection_map`, `poc_pod_lighting`, `poc_sam_hybrid_bonding_voids`
- `pod_hitmiss_fit` `table → table` GPU: 无 — 用广义线性模型由“检出/漏检”二值数据拟合 POD(a)(``table``)。 · 示例: `poc_pod_lighting`, `poc_sem_wafer_defect_edge_bias`, `poc_si_wafer_pl_defect_visibility`
- `proportion_interval` `无输入 → table` GPU: 无 — 返回二项比例 ``k/n`` 的点估计和置信限（``table``）。 · 示例: `proportion_interval_audit`
- `trials_for_all_success` `无输入 → scalar` GPU: 无 — 返回在单侧 ``confidence`` 下以全数成功证明 ``p >= p_min`` 所需的最少试验数（``scalar``）。 · 示例: `proportion_interval_audit`

#### spc / uncertainty (5)
- `gum_expanded` `table → table` GPU: 无 — Welch-Satterthwaite 有效自由度、包含因子 k 与扩展不确定度 U(``table``)。 · 示例: `poc_light_section_step_weld_floor`, `poc_measurement_system_analysis`
- `gum_monte_carlo` `table → table` GPU: 无 — GUM 补充文件 1(JCGM 101)的蒙特卡罗分布传播(``table``)。 · 示例: `poc_measurement_system_analysis`
- `gum_propagate` `table → table` GPU: 无 — 不确定度传播律(GUM 5.2,含相关性)(``table``)。 · 示例: `poc_measurement_system_analysis`
- `gum_standard_uncertainty` `table → table` GPU: 无 — 依据**分布的形状**将不确定度分量换算为标准不确定度(``table``)。 · 示例: `poc_measurement_system_analysis`
- `gum_validate` `table × table → table` GPU: 无 — 用蒙特卡罗的结果**验证**传播律的结果(``table``)。 · 示例: `poc_measurement_system_analysis`

#### spc / variation (5)
- `varmodel_alignment` `video → table` GPU: 有(许可列表) — 每个良品相对于该组典型位置的平移偏差,以及距容许值的余量(``table``)。 · 示例: `poc_good_sample_variation_model`
- `varmodel_band_k` `无输入 → table` GPU: 无 — 对应所声明的每像素双侧误检率的容许带半宽 ``k``(以离散度为单位,``table``)。
- `varmodel_calibrate` `table × video → table` GPU: 无 — 用未参与拟合的良品重新求容许带半宽 ``k``(用于不满足正态假设的真实图像,``table``)。 · 示例: `poc_good_sample_variation_model`
- `varmodel_fit` (halcon: `train_variation_model`) `video → table` GPU: 有(许可列表) — 由良品图像堆叠学习逐像素的变动模型(中心、离散度、容许带半宽 k)(``table``)。 · 示例: `poc_good_sample_variation_model`, `poc_patch_anomaly`
- `varmodel_score` `image2d × table → table` GPU: 无 — 将一张图像与 ``varmodel_fit`` 的模型比较:以 σ 计的 z 图、带外图与逐区域说明(``table``)。 · 示例: `poc_good_sample_variation_model`, `poc_patch_anomaly`

### graph (20 ops / 9 categories)

#### graph / core (2)
- `graph_kcore` `matrix → table` GPU: 无 — 连接矩阵的 k-core(或加权 s-core)分解——每个节点的核指数。 · 示例: `poc_worm_core_persists`
- `graph_rich_club_curve` `matrix → table` GPU: 无 — 对每个 k 计算 rich-club 系数 φ(k)，并与保度零模型比较。 · 示例: `poc_worm_core_persists`

#### graph / degree (1)
- `graph_degree_summary` `matrix → table` GPU: 无 — 有向连接矩阵的度、密度与互惠性。 · 示例: `graphinv_three_phyla`, `poc_connectome_lr_symmetry`

#### graph / flow (4)
- `graph_physarum_path` `matrix → table` GPU: 无 — 在带权图上用黏菌的管道动力学求最短路(Tero et al. 2010)。 · 示例: `poc_physarum_maze`
- `graph_physarum_transport` `matrix × signal → table` GPU: 无 — 在带权图上用黏菌的管道动力学求 L1 最优传输(Beckmann 问题)。 · 示例: `poc_physarum_transport`
- `physarum_route` `image2d → table` GPU: 无 — 用黏菌的管道动力学求代价图像上的最小代价路线。 · 示例: `poc_physarum_maze`
- `physarum_transport_image` `image2d × image2d → table` GPU: 无 — 用黏菌的管道动力学求两幅质量图像之间的推土机距离(Earth mover's distance)。 · 示例: `poc_physarum_transport`

#### graph / motif (1)
- `graph_cycle3` `matrix → table` GPU: 无 — 有向 3 环 ``i -> j -> k -> i`` 的个数，按 ``tr(B^3) / 3`` 计算。 · 示例: `graphinv_three_phyla`

#### graph / null (1)
- `graph_degree_preserving_null` `matrix → table` GPU: 无 — 将 3 环与互惠边与保度零模型比较。 · 示例: `graphinv_three_phyla`

#### graph / path (3)
- `car_dubins_path` `matrix → table` GPU: 无 — 仅能前进的汽车在两个位姿之间的最短路(Dubins 1957)，由六个闭式词给出。 · 示例: `poc_car_parking`, `poc_driving_school`
- `car_hybrid_astar` `image2d × matrix → table` GPU: 无 — Hybrid A*(Dolgov、Thrun、Montemerlo 与 Diebel 2010)：汽车穿过占据栅格的路径。 · 示例: `poc_car_parking`, `poc_driving_school`
- `car_reeds_shepp_path` `matrix → table` GPU: 无 — 可倒车的汽车在两个位姿之间的最短路(Reeds 与 Shepp 1990)，以闭式求得。 · 示例: `poc_car_parking`

#### graph / population (3)
- `graph_core_persistence` `table → table` GPU: 无 — 哪些节点位于每个个体的最内核——同一节点顺序上的 K 个连接。 · 示例: `poc_worm_core_persists`
- `graph_edge_consensus` `table → table` GPU: 无 — 每条连接被多少个体共有——同一节点顺序上的 K 个连接矩阵。 · 示例: `poc_connectome_across_decades`, `poc_connectome_across_worms`
- `graph_strength_growth` `matrix × matrix → table` GPU: 无 — 新的突触去了哪里——连接矩阵 ``a``(较早)对 ``b``(较晚)。 · 示例: `poc_worm_synapses_vs_neurites`

#### graph / symmetry (1)
- `graph_swap_symmetry` `matrix → table` GPU: 无 — 交换节点对后连接还保留多少(左右对称检验)。 · 示例: `graphinv_three_phyla`, `poc_connectome_lr_symmetry`

#### graph / tree (4)
- `tree_from_swc` `text → table` GPU: 无 — 把 SWC 文本(或 ``.swc`` 文件的路径)解析为经过检查的树表。 · 示例: `poc_skeleton_run_length_vs_voi`, `poc_swc_tree_truth`, `poc_worm_neurites_grow`, `poc_worm_synapses_vs_neurites`
- `tree_morphometry` `table → table` GPU: 无 — 树表(来自 :func:`tree_from_swc`)的计数与长度。 · 示例: `poc_swc_tree_truth`, `poc_worm_neurites_grow`, `poc_worm_synapses_vs_neurites`
- `tree_run_length` `table × signal → table` GPU: 无 — 在候选节点标注下骨架的期望行程长度(ERL)。 · 示例: `poc_skeleton_run_length_vs_voi`
- `tree_sholl` `table → table` GPU: 无 — Sholl 分析：以根为中心的球(3-D)或圆(投影)与枝段的交点。 · 示例: `poc_swc_tree_truth`, `poc_worm_neurites_grow`

### text (3 ops / 3 categories)

#### text / detect (1)
- `text_candidates` `matrix → table` GPU: 无 — 把 SWT 的连通分量筛选为字符候选（宽度离散度、长宽比、大小）。 · 示例: `poc_text_region_truth`

#### text / layout (1)
- `text_lines` `table → table` GPU: 无 — 把字符候选矩形合并成文本行（纵向重叠、横向相近、笔画宽度相近）。 · 示例: `poc_text_region_truth`

#### text / stroke (1)
- `swt_map` `image2d → table` GPU: 无 — 笔画宽度变换——在每个像素写入包含该像素的笔画宽度。 · 示例: `poc_text_region_truth`

### residue (5 ops / 3 categories)

#### residue / image (2)
- `crt_displacement` `image2d × image2d → table` GPU: 无 — 由多个波长频带的相位求局部位移，并用中国剩余定理解除相位卷绕 -> ``dict``。 · 示例: `poc_residue_crt`
- `harmonic_rotation` `image2d × image2d → table` GPU: 无 — 求 ``image`` 相对于 ``reference`` 的平面内绝对旋转角（360° 范围）-> ``dict``。 · 示例: `poc_residue_crt`

#### residue / robust (2)
- `residue_crt` `matrix × signal → table` GPU: 无 — 针对实数周期的加权鲁棒中国剩余定理 -> ``dict``。 · 示例: `poc_itof_multifreq`, `poc_residue_crt`
- `residue_fault_locate` `matrix × signal → table` GPU: 无 — 哪个频带损坏了？（冗余剩余数系统）-> ``dict``。 · 示例: `poc_residue_crt`

#### residue / theorem (1)
- `residue_integer_crt` `signal × signal → table` GPU: 无 — 精确的整数中国剩余定理（Garner 混合基数算法）-> ``dict``。 · 示例: `poc_residue_crt`

### vx (10 ops / 5 categories)

#### vx / filter (1)
- `vx_nonlinear_filter` `image2d × matrix → image2d` GPU: 有(许可列表) — 非线性滤波(3.38 节)：掩模为真的像素值的中值 / 最小值(腐蚀)/ 最大值(膨胀)(REQ-0325、0330)。 · 示例: `gallery_openvx_spec_values`

#### vx / geometry (3)
- `vx_remap` `image2d × matrix × matrix → image2d` GPU: 无 — remap(3.44 节)：输出 (x, y) = 输入 (map_x[y, x], map_y[y, x])(REQ-0392)。表的形状与输出相同，坐标以输入像素中心为整数。 · 示例: `gallery_openvx_spec_values`
- `vx_warp_affine` `image2d × matrix → image2d` GPU: 有(许可列表) — 仿射变换(3.56 节)。**逆映射**：输出像素 (x, y) 取自输入的 (x0, y0)(REQ-0498)：``x0 = M[0,0]·x + M[0,1]·y + M[0,2]``、``y0 = M[1,0]·x + M[1,1]·y + M[1,2]``。 · 示例: `gallery_openvx_spec_values`
- `vx_warp_perspective` `image2d × matrix → image2d` GPU: 有(许可列表) — 射影变换(3.57 节)。逆映射：``x0 = M[0]·(x, y, 1)``、``y0 = M[1]·(x, y, 1)``、``z0 = M[2]·(x, y, 1)``， 输出 (x, y) = 输入 (x0/z0, y0/z0)(REQ-0508)。z0 = 0 的像素按外部填充。 · 示例: `gallery_openvx_spec_values`

#### vx / gradient (3)
- `vx_magnitude` `image2d × image2d → image2d` GPU: 有(许可列表) — 梯度幅值(3.31 节)。原样采用 REQ-0270 的概念定义：``z = uint16(sqrt(double(uint32(x·x) + uint32(y·y))) + 0.5)``、 ``mag = z > 32767 ? 32767 : z``。输入与输出均为 S16。 · 示例: `gallery_openvx_spec_values`, `type_connectivity_tour`
- `vx_phase` `image2d × image2d → image2d` GPU: 有(许可列表) — 梯度相位(3.41 节)：将 ϕ = atan2(gy, gx) 移到 0 ≤ ϕ < 2π，再映射到 0〜255(REQ-0364)。输出 U8。 · 示例: `gallery_openvx_spec_values`
- `vx_sobel3x3` `image2d → table` GPU: 有(许可列表) — Sobel 3×3(3.46 节)：将 G_x = [[−1,0,1],[−2,0,2],[−1,0,1]]、G_y = [[−1,−2,−1],[0,0,0],[1,2,1]] (REQ-0415)作为相关运算施加。 · 示例: `gallery_openvx_spec_values`, `type_connectivity_tour`

#### vx / pixel (2)
- `vx_histogram` `image2d → pairs` GPU: 有(许可列表) — 直方图(3.26 节)：像素值 I 落入区间(bin) ``i = (I − offset) × numBins / range`` (offset ≤ I < offset + range，REQ-0230)。范围外的像素不计数。区间由整数除法(截断)决定。 · 示例: `gallery_openvx_spec_values`
- `vx_table_lookup` `image2d × signal → image2d` GPU: 无 — 查表(3.47 节)：输出 = table[像素值 + offset] (REQ-0421)。接受 U8 与 S16(REQ-0422)。输出的 dtype 为表的 dtype。 · 示例: `gallery_openvx_spec_values`

#### vx / suppress (1)
- `vx_nonmax_suppression` `image2d → image2d` GPU: 无 — 非极大值抑制(3.39 节)。像素 (x, y) 仅当在窗口内**对前面的邻居(上方各行以及同一行左侧)≥、对后面的邻居 >** 时才保留(REQ-0337)。平坦峰顶只保留 1 个像素正是由于这种不对称。*mask* 的非零像素不参与比较，原样保留 (也不用于其他像素的比较，REQ-0336)。被抑制的像素在 U8 时为 0，S16 时为 INT16_MIN(REQ-0335)。超出窗口的邻居不比较。 · 示例: `gallery_openvx_spec_values`

### drive (742 ops / 55 categories)

名字是驾驶，内容却是**物理仿真与机器人 PoC 的台账**: 除驾驶(赛道、交通、决策、CARLA / CommonRoad)外，触觉(tac*)、peg-in-hole(peg*)、抛光(polish)、磨削(grind)、切削(cutting)、粉体(granular / scoop)、粉末 X 射线衍射(pxrd)、球类(ball / puck)等作为类别共存其中。请按类别名查找。

#### drive / agv (13)
- `adg_build` `table → table` GPU: 无 — 动作依赖图(Hönig, Kiesel, Tinka, Durham, Ayanian 2019)。 · 示例: `poc_agv_fleet`
- `adg_execute` `table → table` GPU: 无 — 按 ADG 执行。每个时刻，每辆车以概率 ``delay_prob`` 停下(打滑、人员、装卸延误)。 · 示例: `poc_agv_fleet`
- `grid_distances` `image2d → image2d` GPU: 无 — 网格上到 ``goal`` 的最短步数(BFS，障碍物不可通过)。无法到达的格子为 ``inf``。 · 示例: `gallery_drive_city_terrain`, `poc_braid_homotopy_classes`
- `mapf_cbs` `image2d → table` GPU: 无 — Conflict-Based Search(Sharon, Stern, Felner, Sturtevant 2015)。总代价最优的无冲突计划。 · 示例: `poc_agv_fleet`, `poc_braid_homotopy_classes`
- `mapf_ecbs` `image2d → table` GPU: 无 — 上层采用焦点搜索的 CBS(与 ECBS 上层的思路相同，Barer 等 2014)。总代价在**最优的 w 倍以内**。 · 示例: `poc_agv_fleet`
- `mapf_joint_astar` `image2d → table` GPU: 无 — 将所有车辆位置合为 1 个状态的 A*。**仅限小问题**的最优解(CBS 门禁的真值)。 · 示例: `poc_agv_fleet`
- `mapf_prioritized` `image2d → table` GPU: 无 — 带优先级的规划：按顺序每次 1 台，避开先确定车辆的通行路线(预约表)进行规划。 · 示例: `poc_agv_fleet`, `poc_braid_homotopy_classes`
- `naive_execute` `table → table` GPU: 无 — 用于对比的朴素执行：只使用计划的**格子序列**，下一个格子空着就前进(没有顺序约定)。 · 示例: `poc_agv_fleet`
- `plan_conflicts` `table → table` GPU: 无 — 冲突列表：同一时刻同一格子(vertex)、交错而过(edge)、跟随(follow)。 · 示例: `poc_agv_fleet`, `poc_braid_homotopy_classes`
- `plan_cost` `table → scalar` GPU: 无 — 总代价(sum of costs)：各车辆**最后**到达目的地时刻之和(到达后不再移动)。 · 示例: `gallery_drive_city_terrain`, `poc_braid_homotopy_classes`
- `vda5050_check` `table → table` GPU: 无 — 检查 VDA 5050 order 的**结构规则**(独立于官方 JSON 模式的自研第二实现(独立实现))。 · 示例: `poc_agv_fleet`
- `vda5050_order` `table → table` GPU: 无 — 将 1 台车的计划(格子序列)转换为 VDA 5050 的 order(dict)。去除等待，以格子中心为节点。 · 示例: `poc_agv_fleet`
- `warehouse_grid` `无输入 → any` GPU: 无 — 由货架行与通道构成的仓库网格(True = 可行驶)。 · 示例: `poc_agv_fleet`

#### drive / ball (33)
- `aic_from_rss` `无输入 → scalar` GPU: 无 — 由最小二乘残差平方和计算赤池信息量准则:AIC = n ln(RSS/n) + 2k(高斯噪声,方差按最大似然估计,常数项略去)。只有对同一数据拟合的模型之间的**差**才有意义(绝对值依赖尺度与 n)。n ≤ k、RSS ≤ 0、非有限值会引发 ValueError(RSS = 0 时 AIC = −∞,模型选择的问题不成立)。 · 示例: `poc_video_physics_consistency`
- `apex_sequence` `无输入 → signal` GPU: 无 — 落下并弹跳序列的最高点高度 h_k = e^{2k} h₀(k = 0..n)。 · 示例: `poc_ball_bounce`
- `ball_params` `无输入 → table` GPU: 无 — 球的参数表。默认为乒乓球(ITTF：直径 40 mm，2.7 g，薄壳)。 · 示例: `gallery_drive_ballistics`, `gallery_drive_kendama_racket`, `poc_ball_bounce`, `poc_cd_spin_joint`, `poc_table_tennis_bounce`, `poc_table_tennis_rally_loop`, `poc_table_tennis_spin`, `poc_video_physics_consistency`
- `ballistic_vs_thrust` `signal × points × table → table` GPU: 无 — 对同一条轨迹同时拟合"重力 + 阻力"(:func:`drag_fit`)与"重力 + 阻力 + 恒定比推力"(:func:`thrust_fit`),返回 AIC(:func:`aic_from_rss`)之差 ΔAIC = AIC_弹道 − AIC_推力。返回 ``{"ballistic", "thrust"}``(两个拟合)并附上 ``"aic_ballistic", "aic_thrust", "delta_aic", "thrust_norm"``。**不返回判定**(与 :mod:`imgforensics` 同一流派):按**简约原则**来读——推力模型多 3 个参数,即使只有噪声也会略微降低 RSS,除非赢过罚项 2Δk,否则取更简单的弹道模型。仅有噪声时 ΔAIC **以 −2Δk 为下界**、按 χ²(Δk) 近似的宽度散布(中位数约 −2Δk + 1;严格说是混合分布,因为有些拟合撞到 C_d = 0 的壁);推力侧从弹道侧的解出发,所以 ΔAIC ≥ −2Δk 成立。"决定性"的惯用值是 10(假阳性远低于 1 %),但不内置阈值,由调用方决定。当推力侧的 RSS 低于离散化下限 ``rss_floor`` 的 10 倍(无噪声、或比网格解得更细的轨迹)时引发 ValueError——AIC 比较的是噪声而不是舍入屑(无噪声真值在默认 dt 下曾得到 ΔAIC = +144,2026-10-23)。 · 示例: `poc_video_physics_consistency`
- `bounce` `table × table → table` GPU: 无 — 刚体球撞击平面瞬间的速度与角速度更新(库仑摩擦，Cross 2002 / Garwin 1969 的 2 种状态)。 · 示例: `gallery_drive_ballistics`, `poc_ball_bounce`, `poc_table_tennis_bounce`
- `bounce_total_time` `无输入 → scalar` GPU: 无 — 从高度 h₀ 落下至停止的总时间 = √(2h₀/g)·(1 + e)/(1 − e)(等比级数的闭式，e < 1)。 · 示例: `poc_ball_bounce`
- `contact_angular_momentum` `table → signal` GPU: 无 — 绕接触点的角动量 L_c = I ω + m (p − p_c) × v = I ω + m r (n × v)。弹跳前后不变(定理)。 · 示例: `poc_ball_bounce`
- `cup_catch_check` `无输入 → table` GPU: 无 — 球是否进入皿(中心、轴、半径)的几何判定：球心距皿轴在 (cup_radius − ball_radius) 以内，高度在距皿面球半径 1.5 倍以内(0 ≤ height ≤ 1.5 r)，速度 ≤ v_rel_max。``{"caught", "lateral", "height", "speed"}``。皿比球小时为 ValueError。 · 示例: `gallery_drive_ballistics`
- `drag_coefficient_sphere` `signal → signal` GPU: 无 — 光滑球阻力系数的经验式(Morrison 2013，Re ≲ 1e6)：24/Re + 2.6(Re/5)/(1 + (Re/5)^1.52) + 0.411(Re/263000)^−7.94/(1 + (Re/263000)^−8) + 0.25(Re/1e6)/(1 + Re/1e6)。乒乓球(Re ≈ 1–5 × 10⁴)为 0.39–0.41(Re 1.6 × 10⁴ = 6 m/s 时为 0.392，5 × 10⁴ 时为 0.406，1 × 10⁵ 时为 0.426；在 Re ≈ 3 × 10⁵ 的阻力危机处降至 0.17)。 · 示例: `gallery_drive_ballistics`, `poc_cd_spin_joint`
- `drag_fit` `signal × points × table → table` GPU: 无 — 以 **(p₀, v₀, C_d) 共 7 个参数**(平面输入则为 5 个)把"重力 + 阻力"模型拟合到轨迹 (t_i, p_i)——是 :func:`thrust_fit` 的无推力版本(:func:`flight_fit` 把 C_d 视为已知、6 个参数;这里连 C_d 一起辨识)。返回键与入口检查(``dt`` ≤ 采样间隔、``iters`` ≥ 1、拒绝真空)与 :func:`thrust_fit` 相同,``thrust`` 为零向量。真值轨迹可将 C_d 还原到 1e-4(门禁)。 · 示例: `poc_video_physics_consistency`
- `fit_aero` `signal × points × table → table` GPU: 无 — 从轨迹**连同空气动力系数一起**辨识：用 Gauss–Newton 求 (p₀, v₀, C_d, C_L) 的 8 个参数(ω 已知，C_L 作为常数拟合)。阻力与速度的 2 次方成比例，马格努斯与 ω × v 成比例，因此除非轨迹为非直线(有旋转、足够长)，否则 C_L 难以确定(与 ``rms`` 一起返回 ``cond`` = 雅可比的条件数，可据此判断)。返回值 ``{"p0", "v0", "cd", "cl", "rms", "cond", "iters"}``。对真值轨迹(以常数 C_L 生成)可在 1e-6 内还原(门禁)。 · 示例: `gallery_drive_ballistics`, `poc_cd_spin_joint`
- `fit_bounce` `table → table` GPU: 无 — 由弹跳前后的 (v, ω) 以闭式还原 (e, μ)(辨识)。e = −v_n'/v_n。切向冲量 J_t = m(v_t' − v_t) 的大小与 J_n = m(v_n' − v_n) 之比即 μ —— 在始终滑动的状态下为等号，在中途转为滚动(grip)的状态下为**下界**(μ ≥ |J_t|/J_n)。属于哪种，由弹跳后接触点的滑移速度是否为 0(grip)判断。返回值 ``{"e", "mu", "mu_is_lower_bound", "regime", "J_n", "J_t"}``。 · 示例: `gallery_drive_ballistics`
- `fit_parabola` `signal × points → table` GPU: 无 — 用最小二乘将 p = p₀ + v₀ t − ½ g t² ẑ 拟合到观测 (t_i, p_i)(线性，闭式)。``{"p0", "v0", "g", "rms"}``。真空真值可在 1e-9 内还原(门禁)。 · 示例: `poc_ball_bounce`, `poc_video_physics_consistency`
- `fit_spin` `signal × points × table → table` GPU: 无 — **从弯曲方式读出旋转**：以 (p₀, v₀, ω) 的 9 个参数，用 Gauss–Newton 将含阻力 + 马格努斯的运动方程拟合到轨迹 (t_i, p_i)(不含弹跳的区间)(空气动力系数取 ``bp`` 的值 = 视为已知)。 · 示例: `poc_cd_spin_joint`, `poc_table_tennis_spin`
- `fit_spin_aero` `signal × points × table → table` GPU: 无 — **同时读出阻力与旋转**(:func:`fit_spin` 的 C_d 自由版)：以 (p₀, v₀, ω, C_d) 的 10 个参数，用 Levenberg–Marquardt 将含阻力 + 马格努斯的运动方程拟合到轨迹 (t_i, p_i)(不含弹跳的区间)(``fit_cl=True`` 时连升力系数的比例 κ 也设为自由量，共 11 个参数)。 · 示例: `poc_cd_spin_joint`
- `flight_fit` `signal × points × table → table` GPU: 无 — 以 **初始状态 (p₀, v₀) 的 6 个参数**，用 Gauss–Newton(有限差分雅可比)将含阻力 + 马格努斯(ω 已知)的运动方程拟合到观测 (t_i, p_i)(不含弹跳的区间)。抛物线拟合会把阻力、马格努斯吸收进 g 与 v₀，使预测偏弯 —— 本函数相当于先行者的“带空气动力模型的追踪”。返回值 ``{"p0", "v0", "rms", "iters", "t0"}``(p₀、v₀ 为 t = t[0] 时的状态)。输入真值轨迹时可在 1e-9 内还原(门禁)。 · 示例: `poc_ball_bounce`, `poc_table_tennis_bounce`
- `flight_ode` `table → table` GPU: 无 — 重力 + 阻力 + 马格努斯(+ 旋转衰减)的 RK4。返回值 ``{"t" (N,), "p" (N, 3), "v" (N, 3), "omega" (N, 3)}``(t = 0, dt, …, ≤ t_end)。真空(rho = 0)时与 :func:`flight_vacuum` 一致(门禁)。 · 示例: `gallery_drive_ballistics`, `gallery_drive_kendama_racket`, `poc_ball_bounce`, `poc_cd_spin_joint`, `poc_table_tennis_bounce`, `poc_table_tennis_spin`, `poc_video_physics_consistency`
- `flight_simulate` `table × table → table` GPU: 无 — 将飞行与在球台上(平面 z = table_z，仅在 ``table_xy`` = (xmin, xmax, ymin, ymax) 范围内)的弹跳连接起来，接触时刻用二分法在区间内求出。返回值 ``{"t", "p", "v", "omega" (N, 3), "contacts": [{"t", "p", "v_in", "v_out", "omega_in", "omega_out", "regime"}], "rest_t"}``。球半径为 r，因此球心到达 table_z + r 处即为接触。弹跳会无限持续(Zeno)，所以当接触时 |v_n| < ``v_rest`` 时把球放在台面上(此后 z 固定，水平方向无摩擦继续运动；``rest_t`` = 该时刻，若无则为 None)。 · 示例: `poc_ball_bounce`, `poc_table_tennis_bounce`, `poc_table_tennis_rally_loop`, `poc_table_tennis_spin`
- `flight_state_at` `table → table` GPU: 无 — 用运动方程将状态 (p₀, v₀, ω) 推进 T 秒(T < 0 时**回退**：使 RK4 步长为负)。``{"p", "v", "omega"}``。 · 示例: `poc_ball_bounce`, `poc_table_tennis_bounce`
- `flight_vacuum` `signal → points` GPU: 无 — 真空中的抛物线(闭式)：p(t) = p₀ + v₀ t − ½ g t² ẑ。``t`` 为标量或 (N,)，返回值为 (3,) 或 (N, 3)。 · 示例: `gallery_drive_kendama_racket`, `poc_ball_bounce`
- `impact_params` `无输入 → table` GPU: 无 — 碰撞参数表：法向恢复系数 e ∈ [0, 1] (数值，或 |v_n| → e 的函数：以符合随碰撞速度下降的实测)，库仑摩擦系数 μ ≥ 0。 · 示例: `gallery_drive_ballistics`, `gallery_drive_kendama_racket`, `poc_ball_bounce`, `poc_table_tennis_bounce`, `poc_table_tennis_rally_loop`, `poc_table_tennis_spin`
- `incline_slip_angle` `无输入 → scalar` GPU: 无 — 在静摩擦系数 μ 的斜面上开始滑动的角度 θ = atan μ [rad]。 · 示例: `gallery_drive_ballistics`
- `magnus_lift_coefficient` `signal → signal` GPU: 无 — 由旋转比 S = rω/|v| 求升力系数 C_L = 1 / (2 + 1/S)(S → 0 时为 0，S → ∞ 时为 0.5；球类文献中广泛使用的经验式)。 · 示例: `gallery_drive_ballistics`, `poc_cd_spin_joint`
- `mu_from_stop_distance` `无输入 → scalar` GPU: 无 — 由停止距离求 μ = v₀² / (2 g d)。 · 示例: `gallery_drive_ballistics`
- `pendulum_period` `无输入 → scalar` GPU: 无 — 小振幅摆的周期 2π√(L/g)。 · 示例: `gallery_drive_ballistics`
- `restitution_from_apexes` `signal → table` GPU: 无 — 由最高点高度序列(≥ 2 个，正值)估计 e：log h_k 对 k 线性、斜率为 2 log e → 最小二乘。``{"e", "h0", "residual"}``。 · 示例: `poc_ball_bounce`
- `restitution_from_intervals` `signal → table` GPU: 无 — 由接触时刻序列(≥ 3 个，递增)估计 e：间隔 T_{k+1} = e T_k → log T_k 的斜率为 log e。``{"e", "residual"}``。 · 示例: `poc_ball_bounce`
- `roll_slide_state` `table → table` GPU: 无 — 平面上的球是在滚动还是滑动：接触点的滑移速度 s = v_t − r(ω × n)。``{"slip_speed", "rolling"}``(|s| < 1e-9 时为滚动)。 · 示例: `gallery_drive_ballistics`
- `slide_stop_distance` `无输入 → scalar` GPU: 无 — 以初速 v₀ 在水平面上滑动的物体的停止距离 = v₀² / (2μg)(μ > 0)。 · 示例: `gallery_drive_ballistics`, `poc_air_hockey_intercept`
- `tether_simulate` `无输入 → table` GPU: 无 — 由不可伸长的绳(长 L)连在手端 ``handle`` 上的质点的运动(剑玉的球)。 · 示例: `poc_kendama`
- `thrust_fit` `signal × points × table → table` GPU: 无 — 用 Levenberg–Marquardt(有限差分雅可比,C_d ≥ 0 由投影保持)以 **(p₀, v₀, C_d, a_T) 共 10 个参数** 把"重力 + 阻力 + 恒定比推力"模型拟合到轨迹 (t_i, p_i)。``p`` 可以是 (N, 3) 的世界坐标,也可以是从单目侧视图起出的 **(N, 2) 平面 (x, z)**(此时 y 分量既无观测也无未知数:7 个参数,``n`` = 2 × 点数)。``bp`` 是 :func:`ball_params` 的表(质量、迎风面积、空气密度、g;``radius`` 只用来给出迎风面积——对汽车请传入使 A = πr² 等于迎风面积的 r)。返回 ``{"p0", "v0", "cd", "thrust" (3,), "thrust_norm", "rms", "rss", "rss_floor", "n", "k", "dims", "cond", "iters", "t0"}``(``n`` 为残差个数,``k`` 为被移动的参数数;即 :func:`aic_from_rss` 的输入)。真值带推力的轨迹可将 a_T 还原到 1e-5 m/s²;零推力生成的轨迹 ``thrust_norm`` 不超过 1e-5(门禁)。``rss_floor`` 是把 RK4 网格线性插值到采样时刻的误差 ≤ a dt²/8 可能留在残差中的平方和上界。``dt`` 不得超过采样间隔(超过则模型在采样点之间成为分段线性),``iters`` ≥ 1,真空(rho = 0)下 C_d 不可辨识——均为 ValueError。 · 示例: `poc_video_physics_consistency`
- `thrust_ode` `table → table` GPU: 无 — 重力 + 阻力 + **恒定比推力**(单位质量的推力 [m/s²],在世界坐标中方向与大小都不变)的 RK4。无自旋(ω = 0)。返回 ``{"t" (N,), "p" (N, 3), "v" (N, 3)}``(t = 0, dt, …, ≤ t_end)。``thrust`` 为零向量时与 :func:`flight_ode`(ω = 0)在 1e-12 内一致;真空(rho = 0)时与闭式 p₀ + v₀ t + ½ (a_T − g ẑ) t² 在 1e-9 内一致(门禁)。这是处理"几乎是火箭"的影像的最小模型;推力固定在机体上并随之转向时只是近似(区间越短越好)。``t_end`` / ``dt`` 须为有限数,``bp`` 须为 :func:`ball_params` 的表(缺键、非有限、质量为 0 均为 ValueError),步数 t_end / dt 上限为 5×10⁶(以此拦住以 ms 而非秒传入的 t)。 · 示例: `poc_video_physics_consistency`
- `time_stretch_from_gravity` `无输入 → table` GPU: 无 — 由拟合得到的重力加速度闭式反算影像的时间拉伸倍率。把时间轴拉伸 k 倍(慢动作或改写帧率)的影像里,轨迹形状不变而 g 看起来是 g/k²,于是 k = √(g_ref / g_fit)。返回 ``{"k", "g_fit", "g_ref", "log_k"}``(``log_k`` = ln k 在未篡改时为 0,符号表示变快/变慢;交给 :func:`imgforensics.evidence_quantile` 时用 |log_k| 作为"越大越强"的证据)。g_fit ≤ 0、非有限值、g_ref ≤ 0 会引发 ValueError(重力向上或不存在的轨迹无法定义倍率)。 · 示例: `poc_video_physics_consistency`

#### drive / balltrack (10)
- `ball_detect` `image2d → table` GPU: 无 — 从图像中提取球的候选：阈值 → 连通分量 → 亮度加权的亚像素重心、等效半径、填充率。 · 示例: `poc_ball_bounce`, `poc_driving_longitudinal`, `poc_driving_school`, `poc_driving_weather`, `poc_kendama`, `poc_table_tennis_bounce`, `poc_table_tennis_spin`
- `ball_track` `table → table` GPU: 无 — 将逐帧候选列表 ``detections[k] = ball_detect(frame_k)`` 连成 1 条轨迹(取最接近等速预测的候选，且在 ``max_jump`` px 以内)。 · 示例: `poc_ball_bounce`, `poc_table_tennis_spin`
- `bounce_detect` `signal × signal → table` GPU: 无 — 从高度序列 z(t) 中提取接触候选：向下速度转为向上的局部最小(在前后 ``min_gap`` 个样本中最小)。返回值 ``{"index" (M,), "t" (M,), "z" (M,)}``。 · 示例: `poc_ball_bounce`, `poc_table_tennis_bounce`, `poc_table_tennis_spin`
- `kalman_ca` `points → table` GPU: 无 — 等加速度模型的 Kalman 滤波(位置观测 (N, D)，状态 = 位置、速度、加速度 × D)。 · 示例: `poc_air_hockey_intercept`, `poc_ball_bounce`
- `marker_direction` `无输入 → signal` GPU: 无 — 图像中标记的位置 (col, row) → 球面上的方向(相机坐标系的单位向量，前半球：x 右，y 上，z 朝向观察者)。 · 示例: `poc_ball_bounce`, `poc_table_tennis_bounce`, `poc_table_tennis_spin`
- `reproject` `points × matrix × matrix → matrix` GPU: 无 — 世界点 (N, 3) → (N, 2) 的 (col, row)(深度 ≤ 0 为 NaN)。 · 示例: `poc_ball_bounce`, `poc_kendama`, `poc_table_tennis_bounce`, `poc_table_tennis_spin`
- `spin_from_marker_sequence` `any → table` GPU: 无 — 由帧序列的标记方向 ``dirs[k]``((M_k, 3) 的单位向量，未找到的帧为 None)读出角速度(2 段)。 · 示例: `poc_table_tennis_bounce`, `poc_table_tennis_spin`
- `spin_from_markers` `points × points → table` GPU: 无 — 由标记方向对(前 (M, 3)、后 (M, 3)，单位向量)求角速度向量 ω [rad/s]。 · 示例: `poc_ball_bounce`
- `track_triangulate` `table × any × any → table` GPU: 无 — 对各相机的轨迹(:func:`ball_track` 的返回值)做三角测量，得到 3-D 轨迹：``{"frame", "p" (N, 3), "reproj_rms" (N,)}``(仅限在 2 个以上视角中可见的帧)。 · 示例: `poc_ball_bounce`, `poc_table_tennis_spin`
- `triangulate_dlt` `matrix × any × any → table` GPU: 无 — 1 个点的多视角三角测量(线性 DLT，SVD)：``uvs`` (C, 2)、``poses`` (C, 4, 4)、``Ks`` (C, 3, 3)。返回值 ``{"p" (3,), "reproj_rms" px, "n_views"}``。跳过含 NaN 的视角。少于 2 个视角时为 ValueError。 · 示例: `poc_ball_bounce`, `poc_kendama`

#### drive / ballworld (9)
- `add_ball` `table × table → scalar` GPU: 无 — 以位姿 (p, R) 将球加入世界。逐面标签(球 23 / 标记 24)保持不变。返回值 = objects 的索引。 · 示例: `poc_ball_bounce`, `poc_cd_spin_joint`, `poc_table_tennis_bounce`, `poc_table_tennis_spin`
- `ball_mesh` `无输入 → table` GPU: 无 — 球的网格(原点 = 中心)与标记。用 ``markers`` = [(dir, angle_deg), …] 设置多个标记(None 时为 marker_dir 1 个)。返回值 ``{"V", "F", "color" (M,3), "label" (M,) (23 or 24), "radius", "markers": [单位向量 …]}``。 · 示例: `poc_ball_bounce`, `poc_cd_spin_joint`, `poc_table_tennis_bounce`, `poc_table_tennis_spin`
- `ball_set_pose` `table × matrix → any` GPU: 无 — 将球 i 的位姿设为 (p, R)(只改写顶点)。 · 示例: `poc_ball_bounce`, `poc_table_tennis_bounce`, `poc_table_tennis_spin`
- `ball_truth` `table × table → table` GPU: 无 — 球 i 的真值投影：中心的 (col, row)、像半径 [px] (≈ f·r/深度)、标记中心的 (col, row)(位于背面时为 NaN)。 · 示例: `poc_ball_bounce`
- `camera_rig` `table → table` GPU: 无 — 平台周围的摄像机（n = 2：两端对角线上方，n = 4：4 个角）。返回``[{"pose", "K", "eye", "width", "height"}, …]``，全部看着平台的中心。 · 示例: `poc_ball_bounce`, `poc_table_tennis_spin`
- `icosphere` `无输入 → any` GPU: 无 — 将正 20 面体做 ``subdiv`` 次 4 分细分并投影到球面所得的网格 (V, F)(朝外)。 · 示例: `gallery_mesh_seg_sun_gains`
- `rotation_from_omega` `无输入 → matrix` GPU: 无 — 以角速度 ω [rad/s] 旋转 dt 秒的旋转矩阵(Rodrigues)。R_{k+1} = R(ω dt) R_k。 · 示例: `poc_ball_bounce`, `poc_table_tennis_bounce`, `poc_table_tennis_spin`
- `table_params` `无输入 → table` GPU: 无 — 乒乓球台的参数表(默认 = ITTF 规格)。 · 示例: `gallery_drive_kendama_racket`, `poc_ball_bounce`, `poc_cd_spin_joint`, `poc_table_tennis_bounce`, `poc_table_tennis_rally_loop`, `poc_table_tennis_spin`
- `table_world` `table → table` GPU: 无 — 球台(台面 + 白线 + 球网)与地面的世界。原点 = 台面中心，x = 长边方向(±1.37)，y = 宽度方向(±0.7625)，z 向上。台面上表面 z = height。 · 示例: `poc_ball_bounce`, `poc_cd_spin_joint`, `poc_table_tennis_bounce`, `poc_table_tennis_spin`

#### drive / braidpath (12)
- `braid_artin_images` `signal × scalar → table` GPU: 无 — 辫的 Artin 表示:自由群 F_n 的生成元 x₁..xₙ 的像(自由约化后的字)。
- `braid_class_representatives` `any → table` GPU: 无 — 将多个规划(任何规划器的输出均可)按同伦类划分,并在每类中选费用最小的规划作为代表。 · 示例: `poc_braid_homotopy_classes`
- `braid_equivalent` `signal × signal × scalar → table` GPU: 无 — 两个辫字是否为同一辫(能否仅通过关系式互相变换)。 · 示例: `poc_braid_homotopy_classes`
- `braid_from_trajectories` `any → table` GPU: 无 — 由平面轨迹组(以及静止障碍物的点)构造辫字(交叉符号的序列)。 · 示例: `poc_braid_homotopy_classes`
- `braid_reduce` `signal × scalar → signal` GPU: 无 — 用 Dehornoy 柄约化来约化辫字。**返回空字 ⇔ 平凡辫**(同一类)。 · 示例: `poc_braid_homotopy_classes`
- `dynnikov_act` `any × signal → table` GPU: 无 — 将辫字作用于任意 Dynnikov 坐标 (a; b)(整数或实数均可 —— 公式是分段线性的)。 · 示例: `poc_braid_homotopy_classes`
- `dynnikov_coordinates` `signal × scalar → table` GPU: 无 — 辫作用于标准曲线图 E = (0, …, 0; −1, …, −1) 所得的 Dynnikov 坐标(整数,不溢出)。 · 示例: `poc_braid_homotopy_classes`
- `grid_hole_points` `image2d → matrix` GPU: 无 — 为每个网格孔(不接触外周的阻塞单元格连通分量)取 1 个代表点:离重心最近的阻塞单元格的中心 [x, y]。 · 示例: `poc_braid_homotopy_classes`
- `grid_paths_to_xy` `any → any` GPU: 无 — 将网格路径(各台的 (row, col) 序列)转为 (K, T, 2) 的 [x, y] = [col, −row] (较短的路径用最后一个点补齐)。 · 示例: `poc_braid_homotopy_classes`
- `homotopy_class_compare` `any × any → table` GPU: 无 — 起点与终点相同的两个路径族(多智能体的规划)是否属于同一同伦类。 · 示例: `poc_braid_homotopy_classes`
- `homotopy_shortest_paths` `image2d × any × any → table` GPU: 无 — 在网格(True = 可通行,4 邻域)上,按从短到长给出从 start 到 goal 的、同伦类各不相同的 k 条最短路径。 · 示例: `poc_braid_homotopy_classes`
- `pairwise_winding` `any → matrix` GPU: 无 — 每对股之间的相对绕数 [圈] (相对向量辐角的总变化 / 2π)。对称矩阵,对角为 0。 · 示例: `poc_braid_homotopy_classes`

#### drive / carla (25)
- `camera_pose_to_carla` `matrix → any` GPU: 无 — render3d 的 world → camera 4×4 → CARLA 相机的 [x, y, z, roll, pitch, yaw]。:func:`carla_camera_pose` 的逆。 · 示例: `poc_carla_bridge`
- `carla_camera_pose` `any → matrix` GPU: 无 — CARLA 相机的世界位姿 → render3d / driveworld 的 **world → camera** 4×4(与 :func:`driveworld.camera_pose` 同型)。CARLA 相机朝局部 +x 看，右 = +y、上 = +z；render3d 朝 −z 看，右 = +x、上 = +y。 · 示例: `poc_carla_bridge`
- `carla_depth_decode` `rgb → image2d` GPU: 有(许可列表) — CARLA 深度相机的原始图像(R 低位、G、B 高位的 24 bit)→ 到像平面的距离 [m]。d = code / (2²⁴ − 1) · 1000。 · 示例: `poc_carla_bridge`
- `carla_depth_encode` `image2d → rgb` GPU: 有(许可列表) — 到像平面的距离 [m] → CARLA 原始深度图像(uint8 (H,W,3))。inf 与超过 1000 m 的值取最大值，负值与 NaN 则 ValueError。 · 示例: `poc_carla_bridge`
- `carla_intrinsics` `无输入 → matrix` GPU: 无 — CARLA 相机的 K(**水平**视场角 fov，f = W / (2 tan(fov/2))，主点 (W/2, H/2))。 · 示例: `gallery_drive_carla_bridge`
- `carla_label_map` `image2d → image2d` GPU: 仅在链中(许可列表) — CARLA 语义分割(标签的 uint8 图像)→ Fullseye 标签图像(int，−1 = 空、未标注)。未知标签则 ValueError。 · 示例: `poc_carla_bridge`
- `carla_label_unmap` `image2d → image2d` GPU: 有(许可列表) — Fullseye 标签图像 → CARLA 标签图像(uint8，代表标签)。:func:`carla_label_map` 的逆(在标签侧为恒等)。 · 示例: `poc_carla_bridge`
- `carla_labels` `无输入 → table` GPU: 无 — CARLA 0.9.16 语义标签表：``[{"tag", "carla", "label", "fullseye"}, …]``(29 行，按标签顺序)。 · 示例: `poc_carla_bridge`
- `carla_pose_to_world` `any → matrix` GPU: 无 — CARLA 的 [x, y, z, roll, pitch, yaw] → Fullseye 的 4×4(world ← object，右手系：y 与 yaw 的符号取反)。R_f = M R_c M，t_f = M t_c(M = diag(1, −1, 1))。物体的局部坐标系为 x 前、y 左、z 上(与 driveworld 的车相同)。 · 示例: `gallery_drive_carla_bridge`
- `carla_rotation_angles` `matrix → any` GPU: 无 — 3×3(CARLA 的公式)→ (roll, pitch, yaw)[度]。pitch = asin(R₂₀)，yaw = atan2(R₁₀, R₀₀)，roll = atan2(−R₂₁, R₂₂)。|pitch| = 90° 的退化情形则 ValueError。 · 示例: `poc_carla_bridge`
- `carla_rotation_matrix` `无输入 → matrix` GPU: 无 — CARLA / UE4 的 (roll, pitch, yaw)[度] → 3×3(与 ``carla.Transform.get_matrix()`` 旋转部分的公式相同，保持左手系)。 · 示例: `gallery_drive_carla_bridge`
- `carla_scene_check` `table → table` GPU: 无 — 检查场景记录的键、形状与类型并返回摘要(不通过则 ValueError)。返回值 = ``{"width", "height", "has_lead", "has_instance", "meta"(dict), "n_tags"}``。 · 示例: `gallery_drive_carla_bridge`
- `carla_scene_load` `any → table` GPU: 无 — 读取场景记录(npz)→ dict(``meta`` 转为 dict，``depth`` [m] 解码后加入)。缺失或损坏的项则 ValueError。 · 示例: `poc_carla_bridge`
- `carla_scene_render` `table → table` GPU: 无 — 在自建世界中重新拍摄场景记录(相同 K、相同安装高度、相同视场角)→ driveworld.world_camera 的图像 (``color`` / ``label`` / ``depth`` …) + ``pose`` + ``K``。用于与 CARLA 图像**并排**查看的另一半。 · 示例: `gallery_drive_carla_bridge`
- `carla_scene_save` `table → any` GPU: 无 — 将场景记录写入 npz(先检验)。返回值 = 写入的路径。 · 示例: `poc_carla_bridge`
- `carla_scene_synthetic` `无输入 → table` GPU: 无 — 把自建世界(直路 + 前车)转换为**符合 CARLA 约定的场景记录**(键和类型与拍摄记录相同)。 · 示例: `gallery_drive_carla_bridge`, `poc_carla_bridge`
- `carla_scene_world` `table → table` GPU: 无 — 场景记录 → 自建世界(直路 + 按记录位姿放置的前车)。保持相机与前车的相对配置，将相机归一化到 (20, 0)、朝向 +x(不使用 CARLA 地图坐标)。无前车时只有道路。 · 示例: `gallery_drive_carla_bridge`
- `carla_transform_matrix` `any → matrix` GPU: 无 — CARLA 的 [x, y, z, roll, pitch, yaw] → 4×4(world ← object，保持 CARLA 坐标)= ``Transform.get_matrix()``。 · 示例: `poc_carla_bridge`
- `carla_xy_yaw` `any → any` GPU: 无 — CARLA 的位姿 → carpath / driveworld 的 (x, y, yaw)(y 与 yaw 的符号取反，yaw 为弧度)。 · 示例: `gallery_drive_carla_bridge`
- `intrinsics_to_carla` `matrix → matrix` GPU: 无 — :func:`intrinsics_to_fullseye` 的逆(将主点移回 0.5)。 · 示例: `gallery_drive_carla_bridge`
- `intrinsics_to_fullseye` `matrix → matrix` GPU: 无 — CARLA 的 K(像素角点为整数，主点 W/2)→ Fullseye / render3d 的 K(像素中心为整数，主点 (W−1)/2)。只把主点平移 0.5。 · 示例: `gallery_drive_carla_bridge`, `poc_carla_bridge`
- `lead_from_depth` `image2d × image2d × matrix → table` GPU: 无 — 基于规则的前车距离(两个世界使用同一公式): ``depth_median`` = 图像中央带(宽 band × W)内车辆像素深度的中位数(后表面平行于像平面，故恒定)，``row_distance`` = 由车辆最下行按平坦路面公式(driveenv.road_row_distance)求出的水平距离，``bbox`` = (top, bottom, left, right)，``n_pixels``，``found``。无车辆像素时 found = False(距离为 inf)。 · 示例: `gallery_drive_carla_bridge`
- `lead_truth_depth` `table → scalar` GPU: 无 — 由记录位姿得到的闭式: 到前车后表面中心的**像平面距离** [m]。后表面 = 中心 − 半长 × 前车前进方向，像平面距离 = (后表面 − 相机)·相机前向。无前车时为 inf。 · 示例: `gallery_drive_carla_bridge`, `poc_carla_bridge`
- `scene_pair_table` `table → table` GPU: 无 — 使用 **CARLA 的图像** 和 **您自己的世界图像** 对一个场景录音进行评分和排列。返回值 = ``{"truth", "carla": {...lead_from_depth}, "fullseye": {...}, "carla_error", "fullseye_error", "width", "height", "view"}`` (error = depth_median − true value, true value is :func:`lead_truth_depth`)。 · 示例: `poc_carla_bridge`
- `world_pose_to_carla` `matrix → any` GPU: 无 — Fullseye 的 4×4(world ← object)→ CARLA 的 [x, y, z, roll, pitch, yaw]。:func:`carla_pose_to_world` 的逆。 · 示例: `gallery_drive_carla_bridge`

#### drive / commonroad (10)
- `cr_checker_result` `any → table` GPU: 无 — 读取 WSL 中官方检查器(tools/check_solution_json.py)写出的 JSON。 · 示例: `poc_driving_commonroad`
- `cr_collision` `table × table → table` GPU: 无 — 与障碍物的碰撞(矩形间的 SAT，逐 time_step)及道路边界(车辆 4 个角是否位于 lanelet 多边形的并集内)。 · 示例: `poc_driving_commonroad`
- `cr_drive` `table → table` GPU: 无 — 让自研驾驶员(纵向 IDM + pure pursuit)在 CommonRoad 的 planning problem 上行驶。 · 示例: `poc_driving_commonroad`
- `cr_drive_sweep` `table → table` GPU: 无 — 基于规则的 gap acceptance: 按由温和开始的顺序尝试驾驶员参数网格，返回**第一个通过所有门禁的行驶**。 · 示例: `poc_driving_commonroad`
- `cr_feasible` `table → table` GPU: 无 — 运动学可行性(与评分器 ``solution_feasible`` 思路相同的第二实现(独立实现))。 · 示例: `poc_driving_commonroad`
- `cr_read` `any → table` GPU: 无 — 读取 CommonRoad 2020a XML(字符串或路径)。 · 示例: `poc_driving_commonroad`
- `cr_route` `table → table` GPU: 无 — 通过 successor 的 BFS(跳数最少)得到 lanelet 序列，拼接中心线并按每 ``step`` m 重新采样。 · 示例: `poc_driving_commonroad`
- `cr_solution_xml` `table × table → any` GPU: 无 — 以字符串返回官方 solution XML(与 commonroad-io ``CommonRoadSolutionWriter`` 相同的形式)。 · 示例: `poc_driving_commonroad`
- `cr_synthetic` `无输入 → any` GPU: 无 — 以字符串返回用于测试和 CI 的最小 CommonRoad 2020a XML。 · 示例: `poc_driving_commonroad`
- `ks_step` `any × any → any` GPU: 无 — 在分段常值输入 u = (δ̇, a) 下用 RK4 将运动学单轨(KS)模型推进 dt。参考点 = 后轴中心。 · 示例: `poc_driving_commonroad`

#### drive / course (13)
- `course_contains` `table × points → signal` GPU: 无 — 以奇偶规则判定点是否位于**可行驶区域**(要素的多边形；若为布局则为各要素之并)内侧的 bool 数组。 · 示例: `poc_driving_school`, `poc_world_terrain`
- `course_crank` `无输入 → table` GPU: 无 — 曲折路线(曲柄弯，Z 形)：进入 → 左 90° → B → 右 90° → 驶出。 · 示例: `poc_driving_school`, `poc_driving_town`
- `course_crossing` `无输入 → table` GPU: 无 — 铁路道口：铁轨以直角横穿宽 w 的道路(沿 x 轴)。道口面(轨距 + 2 条钢轨外侧 = 2.6 m)两侧为长 ``approach`` 的直线。``rails`` (2, 2, 2) 是 2 条钢轨的线段(x = L/2 ± gauge/2，横贯整个路宽)，``crossing_zone`` = (x0, x1) 为道口面，``stop_lines`` (1, 2, 2) 位于道口面前方 ``stop_setback`` 处的左车道。多边形为矩形(钢轨为元数据)。规格：轨距 1.1，钢轨外侧 0.75 → ``params["regulation"]``。面积 = w·(2(rail_outer + gauge/2) + 2·approach)。 · 示例: `poc_driving_school`
- `course_intersection` `无输入 → table` GPU: 无 — 干线路线的十字交叉口：2 条宽 w 的道路在原点正交，各臂长 ``arm``(从交叉区边缘算起)，4 个凹顶点以半径 ``corner_radius`` 削圆。 · 示例: `poc_driving_longitudinal`, `poc_driving_school`, `poc_driving_weather`
- `course_layout` `table × table → table` GPU: 无 — 以刚体运动 ``(x, y, yaw)`` 放置多个要素，合成 1 个 dict。 · 示例: `poc_driving_longitudinal`, `poc_driving_school`, `poc_driving_weather`, `poc_ttc_rss`, `poc_world_terrain`
- `course_loop` `无输入 → table` GPU: 无 — 环形路线(长圆形)：返回以原点为中心放置 2 条直线 + 2 个半圆的 ``{"elements": [...], "placements": [...]}``(可直接传给 :func:`course_layout`)。按逆时针：南侧直线(向东，y = −R)→ 东侧半圆 → 北侧直线(向西，y = +R)→ 西侧半圆。直线两端各以 ``overlap`` 嵌入半圆(为 3-D 化时接缝处不立起路缘石而设的重叠；面积之和对该部分重复计算)。规格(普通驾照)：80 m 以上的直线行驶部分，宽 8 m 以上。 · 示例: `poc_driving_school`, `poc_ttc_rss`, `poc_world_terrain`
- `course_loop_bend` `无输入 → table` GPU: 无 — 环形路线端部的半圆(向左转 180°)：进入 (0, 0, 0) → 绕中心 (0, R) 转 → 驶出 (0, 2R, π)。多边形是由外弧(半径 R + w/2)与内弧(R − w/2)围成的半个圆环。面积 = π R w(闭式)，因弧以折线近似而相应偏小，增大 arc_pts 即收敛。规格(环形路线)：宽 8 m 以上，大致为长圆形。 · 示例: `poc_driving_school`, `poc_driving_town`
- `course_occupancy` `table → image2d` GPU: 无 — 将路线(要素或布局)落到占据栅格 ``(occ bool [row = y, col = x], extent)`` 上。 · 示例: `poc_driving_school`
- `course_parallel_parking` `无输入 → table` GPU: 无 — 侧方停车：在宽 ``road_width`` 的道路(x ∈ [0, 2·approach + bay_length])路侧设长 car_length + extra(默认 7.5 m)× 宽 car_width 的车位。**法规中无数值(通知的附件为图)** —— 默认值为惯例值。 · 示例: `poc_driving_school`
- `course_road` `无输入 → table` GPU: 无 — 连接路(干线的一部分)：宽 w、长 L 的直线。用于把课题路线的出口接回环形路线、或延长干线的要素。规格(干线路线)：宽 7 m 以上，须与环形路线相连。面积 = w·L。 · 示例: `gallery_drive_city_terrain`, `gallery_drive_japan_roads`, `gallery_drive_world_objects`, `poc_driving_longitudinal`, `poc_driving_school`, `poc_driving_town`, `poc_driving_weather`
- `course_s_curve` `无输入 → table` GPU: 无 — 曲线路线(S 形)：直线 E → 左弧(圆心角 2π·f)→ 右弧(相同)→ 直线 E。 · 示例: `poc_driving_school`, `poc_driving_town`
- `course_slope` `无输入 → table` GPU: 无 — 坡道路线：以缓坡上升到高度 ``height``、顶部平坦段 ``top``、再以陡坡下行的矩形道路(沿 x 轴)。 · 示例: `poc_driving_longitudinal`, `poc_driving_school`
- `course_turnaround` `无输入 → table` GPU: 无 — 方向转换路线(T 形)：在宽 w 的道路(x ∈ [0, 2E + bay_width])侧面中央设车位(沿道路的宽 bay_width，进深 depth)，车位口两侧各有出入口段 E。 · 示例: `poc_driving_school`

#### drive / crossing (17)
- `conflict_zone_intervals` `any → table` GPU: 无 — 车辆占据冲突区域(交叉口内 2 条行进路线重叠处)的时刻 [t_in, t_out] (闭式，可用数组)。 · 示例: `poc_driving_crossing`
- `crossing_clear_time` `无输入 → table` GPU: 无 — 从停止线起步，到车尾越过铁路道口对面边缘 + ``beyond`` 为止的时间(闭式)。 · 示例: `poc_driving_crossing`
- `crossing_gate_state` `signal → table` GPU: 有(许可列表) — 在时刻 t(数组)上评估铁路道口的状态机(道口报警器 + 栏杆)。 · 示例: `poc_driving_crossing`
- `crossing_lamp_signal` `无输入 → any` GPU: 无 — 返回 2 盏红色闪光灯在时刻 t(数组)的亮度(0..1)：形状 (n, 2)，列 0 = 左，列 1 = 右。 · 示例: `poc_driving_crossing`
- `crossing_stop_check` `table → table` GPU: 无 — 对铁路道口的通行方式评分(第33条第1、2款，第50条第2款，交通教则 6-1-1(1)(3)(4)(5))。 · 示例: `poc_driving_crossing`, `poc_driving_town`
- `crossing_timing_check` `无输入 → table` GPU: 无 — 将铁路道口的 3 个时刻(报警开始、栏杆动作结束、列车到达)与解释基准的标准值和最小值对照(数组 = 按列车)。 · 示例: `poc_driving_crossing`
- `crosswalk_overtake_check` `table → table` GPU: 无 — 在人行横道等及其前方 ``zone`` m 范围内，是否超到了前方行驶车辆的前面(第38条第3款)。 · 示例: `poc_driving_crossing`
- `crosswalk_stopped_vehicle_check` `table → table` GPU: 无 — 在从停在人行横道等(或其紧前方)的车辆侧方通过并超到其前方之前，是否先停车让行(第38条第2款)。 · 示例: `poc_driving_crossing`
- `exit_room_check` `any → table` GPU: 无 — 铁路道口(人行横道、交叉口同理)的对面是否有本车能停下的空间(第50条第2款)。可用数组。 · 示例: `poc_driving_crossing`
- `lamp_pair_phase` `signal × signal → table` GPU: 无 — 由 2 条亮度时间序列(2 盏灯的像素)，用互谱估计共同的闪烁频率与相位差。 · 示例: `poc_driving_crossing`
- `legal_stop_intervals` `any → any` GPU: 无 — 避开禁止停车区间(合并后的 (k, 2))、使车身 [rear, rear + car_length] 完整容纳的**车尾位置**区间 (m, 2)。 · 示例: `poc_driving_crossing`
- `no_stopping_zones` `table → table` GPU: 无 — 根据道路沿线设施生成第44条第1款的禁止停车区间。 · 示例: `poc_driving_crossing`
- `obstruction_decel` `any → table` GPU: 无 — 交叉道路上的车辆(到区域距离 dist，速度 speed)为了不在 t_free 之前进入区域所需的恒定减速度(闭式，可用数组)。 · 示例: `poc_driving_crossing`
- `parking_position_check` `无输入 → table` GPU: 无 — 车身 [rear, front] 是否与禁止停车区间重叠。``zones_result`` = ``no_stopping_zones`` 的返回值。 · 示例: `poc_driving_crossing`
- `priority_rule` `table → table` GPU: 无 — 在无交通管制的交叉口，本车(own)是否应让行交叉道路(cross)上的车辆(第36条第1至3款)。 · 示例: `poc_driving_crossing`
- `sight_triangle_distance` `无输入 → scalar` GPU: 无 — 转角有建筑物时，在线路上能看到多远(视距三角形)。 · 示例: `poc_driving_crossing`
- `track_sight_distance` `any → any` GPU: 无 — 为避免在通过前列车到达，必须在线路上可见的距离 = v_train · (clear_time + margin)。 · 示例: `poc_driving_crossing`

#### drive / cutting (16)
- `cut_depth_from_side` `rgb × table × scalar × scalar → table` GPU: 无 — 由正面图像中食材的上表面(饱和度边缘，逐列亚像素 → 中位数)和刃口直线求切入深度(mm)。 · 示例: `poc_food_cutting_measure`
- `cut_force_atkins` `scalar × scalar → table` GPU: 无 — 软固体切割力的闭式(尺度 = 韧性 R × 正在切割的宽度 w，R 与 w 的 1 次式)。返回值为 dict(N)。 · 示例: `poc_food_cutting_measure`
- `cut_force_csv_load` `any × any → table` GPU: 无 — 读取有限元切割仿真输出的刀刃力 CSV(第 1 行为 ``Rcforc``，第 2 行为列名，列 = 时刻与力的 3 个分量交替)。 · 示例: `poc_food_cutting_measure`
- `cut_force_fit` `signal × signal × scalar → table` GPU: 无 — 由切割过程中的力序列 F(N)和正在切割的宽度 w_eff(mm)，用过原点的最小二乘求韧性 R(J/m²)。 · 示例: `poc_food_cutting_measure`
- `cut_surface_roughness` `rgb × scalar × scalar × signal → table` GPU: 无 — 将切割后端面的轮廓(逐行亚像素)视为截面，拟合最小二乘直线，输出 ISO 4287 参数(µm)。 · 示例: `poc_food_cutting_measure`
- `cutting_edge_render` `table × any × scalar × scalar × scalar → rgb` GPU: 无 — 沿刃口方向的图像(RGB)。暗背景、食材(右侧为主体)、刀刃(单刃，平面朝切片一侧)。 · 示例: `poc_food_cutting_measure`
- `cutting_episode_synth` `无输入 → table` GPU: 无 — 用闭式运动生成 1 次切割(准静态，刚塑性食材 + 仅竖直方向柔软的腕部)。返回值为 dict(各列为 numpy 数组)。 · 示例: `poc_food_cutting_measure`, `poc_knife_tactile_toughness`
- `cutting_face_render` `table × scalar × scalar × scalar → rgb` GPU: 无 — 正面图像(RGB，(H, W, 3) float)。按墙 → 砧板 → 刀刃 → 食材(前方)的顺序，以覆盖率的解析绘制叠加。 · 示例: `poc_food_cutting_measure`
- `cutting_scene` `any → table` GPU: 无 — 合成场景的参数(dict)。``kind="face"`` = 正面图像(相机沿刀刃面的法线方向)，``"edge"`` = 沿刃口方向的图像。 · 示例: `poc_food_cutting_measure`, `poc_knife_tactile_toughness`
- `cutting_wrist_mjcf` `table × scalar → any` GPU: 无 — 柔顺腕部的刀刃场景(MJCF 字符串，不需要 mujoco)。刀刃有 1 个竖直滑动关节(弹簧 ``k``、阻尼)，食材和砧板仅用于显示。 · 示例: `poc_food_cutting_measure`
- `food_cut_width` `scalar × scalar × scalar × scalar → scalar` GPU: 无 — 刃口直线(在食材中央的高度 ``edge_z_at_xc``，倾角 θ)位于食材上表面以下的 x 长度 = 正在切割的宽度(mm，闭式)。 · 示例: `poc_food_cutting_measure`, `poc_knife_tactile_toughness`
- `force_from_wrist_displacement` `signal × signal × scalar → signal` GPU: 无 — 柔顺腕部(竖直弹簧 k，N/mm)时，压力 F = k (z_meas − z_cmd)：刀刃高于指令的部分即为力(N 的数组)。 · 示例: `poc_food_cutting_measure`
- `knife_edge_track` `rgb → table` GPU: 无 — 从正面图像求出刃口直线、刀背和刀尖(仅基于规则)。 · 示例: `poc_food_cutting_measure`
- `slice_push_from_track` `scalar × signal × signal → scalar` GPU: 无 — 由刀刃上 1 点的轨迹 (x, z)(来自图像)和刃口倾角 θ(来自图像)求 ξ。速度取轨迹直线拟合的方向(ξ 是比值)。 · 示例: `poc_food_cutting_measure`
- `slice_push_ratio` `scalar × scalar × scalar → scalar` GPU: 无 — 由刃口倾角 θ(x-z，逆时针)和刀刃速度 (vx, −vz)(vz > 0 为向下)求 slice/push 比 ξ。 · 示例: `poc_food_cutting_measure`
- `slice_thickness_profile` `rgb × scalar × scalar → table` GPU: 无 — 在沿刃口方向的图像中，逐行求出“食材端面”和“刀刃平面”的亚像素位置，差 = 切片厚度(mm)。 · 示例: `poc_food_cutting_measure`

#### drive / cuttouch (3)
- `knife_load_from_pads` `table × table × table × scalar → table` GPU: 无 — 2 块垫的读数(:func:`pegtactile.pad_tactile_read`)→ 刀刃从食材受到的推力 V、拉力 H、力矩 M_x，以及刀刃的接触位置 Ly。 · 示例: `poc_knife_tactile_toughness`
- `torsion_partial_slip` `scalar × scalar × table → table` GPU: 无 — 对球面垫(Hertz，法向力 ``P``)施加绕法线的扭转 ``M`` [N·m] 时的部分滑移：粘着半径 c、扭转角 β 以及到完全滑移的比值。 · 示例: `poc_knife_tactile_toughness`, `poc_tactile_dipole_torque`
- `toughness_from_pads` `any × signal → table` GPU: 无 — :func:`knife_load_from_pads` 的序列与切割宽度 w_eff [mm] (来自图像，:func:`cutting.food_cut_width`)→ 韧性 R 与接触位置的汇总。 · 示例: `poc_knife_tactile_toughness`

#### drive / decide (18)
- `aliased_frequency` `any → any` GPU: 无 — 以帧率 ``fps`` 采样频率 ``f`` [Hz] 的明灭时的**表观**频率(闭式)。 · 示例: `poc_driving_crossing`, `poc_driving_decisions`
- `bus_departure_yield_check` `table → table` GPU: 无 — 评分后方本车是否妨碍了已打灯示意从公交车站起步的公交车变更车道(道路交通法第31条之2)。 · 示例: `poc_driving_decisions`
- `check_sequence_score` `table → table` GPU: 无 — 对变更车道、左右转弯之前的 "安全确认 → 打灯示意 → (约 3 秒 / 30 m)→ 动作 → 关闭示意" 进行评分。 · 示例: `poc_driving_decisions`
- `convex_mirror_fov` `无输入 → table` GPU: 无 — 从轴上距离 ``eye_distance``(自顶点)处的眼睛观看凸面镜(球面，半径 ``radius``，口径 ``aperture``)时的视场角。 · 示例: `poc_driving_decisions`
- `dilemma_zone` `any → table` GPU: 无 — 黄灯的两难区(Gazis, Herman, Maradudin 1960)。 · 示例: `poc_driving_decisions`
- `doppler_shift` `any → any` GPU: 无 — 声源运动、听者静止时听到的频率(闭式)。 · 示例: `poc_driving_decisions`
- `doppler_track` `signal → table` GPU: 无 — 从警笛声估计瞬时频率，判断其正在接近还是远离。 · 示例: `poc_driving_decisions`
- `flash_frequency` `signal → table` GPU: 无 — 由像素(或区域平均)亮度的时间序列估计闪烁频率(FFT 的最高峰)。 · 示例: `poc_driving_crossing`, `poc_driving_decisions`
- `mirror_aim_normal` `无输入 → any` GPU: 无 — 使从眼睛 ``eye`` 射向镜面中心 ``mirror_center`` 的光线反射到方向 ``look_dir`` 的镜面法线(2D 和 3D 均可)。 · 示例: `poc_driving_decisions`, `poc_driving_pass`
- `mirror_blind_zone` `无输入 → table` GPU: 无 — 本车左后方既不在左外后视镜中、也不在直接视野内的区域(2D，俯视图)。 · 示例: `poc_driving_decisions`
- `mirror_reflection_matrix` `无输入 → any` GPU: 无 — 关于平面 ``mirror_plane`` = (n_x, n_y, n_z, d)(点 X 在镜面上 ⇔ n·X = d，n 会被归一化)的反射的 4×4 齐次矩阵。 · 示例: `gallery_drive_mirrors_crowds`
- `mirror_virtual_camera` `any → table` GPU: 无 — 拍摄平面镜中映像的**虚拟相机**。 · 示例: `poc_driving_decisions`
- `predict_amber_onset` `table → table` GPU: 无 — 由并行行人信号灯的观测(按时间顺序的 ``(t, state)``，state ∈ green / flash / red)估计车辆黄灯的开始。 · 示例: `poc_driving_decisions`
- `signal_phase_plan` `无输入 → table` GPU: 无 — 2 相位信号灯的时间表(主路 A 及与其**并行的行人信号灯**，交叉道路 B)。时刻 0 = A 绿灯开始。 · 示例: `poc_driving_decisions`
- `signal_state` `table → any` GPU: 无 — 按 ``signal_phase_plan`` 时间表求时刻 ``t``(按周期折回)的状态(字符串数组)。区间为 [始, 终)。 · 示例: `poc_driving_decisions`
- `siren_signal` `无输入 → table` GPU: 无 — 合成静止麦克风听到的移动救护车警笛(双音交替)的声音。 · 示例: `poc_driving_decisions`
- `tdoa_bearing` `signal × signal → table` GPU: 无 — 由 2 个麦克风(左 = +y，右 = −y，间距 ``mic_spacing``)的到达时间差求声源方位(远场近似)。 · 示例: `poc_driving_decisions`
- `yield_maneuver_check` `table → table` GPU: 无 — 按道路交通法第40条对紧急车辆接近时本车的动作进行评分。 · 示例: `poc_driving_decisions`

#### drive / diabolo (16)
- `diabolo_axis_from_image` `rgb × table × table → table` GPU: 无 — 从 1 帧求出近侧杯口边缘的中心 ``center_rim`` 和轴 ``axis``(朝向相机)。空竹中心 ``center`` = center_rim − (L/2) axis。无学习。 · 示例: `poc_diabolo_model_and_vision`
- `diabolo_camera` `无输入 → table` GPU: 无 — 透视相机(默认 = 从前方 1.4 m 处朝 −x 看，世界的 z 朝上)。返回 ``{"C", "R"(行 = 右、下、前), "K", "shape", "look_at"}``。**Raises** ``ValueError``：位置与注视点重合、视线竖直、图像尺寸或视场角不合法。 · 示例: `poc_diabolo_model_and_vision`
- `diabolo_dynamics_step` `table × matrix × matrix × scalar × table → table` GPU: 无 — 将论文的解析模型推进 1 步(空竹 = 质点 + 辅助旋转椭球 + 重力)。 · 示例: `poc_diabolo_model_and_vision`
- `diabolo_marker_phase` `rgb × table × table × table → table` GPU: 无 — 从 1 帧中的标记读取旋转相位 ψ(从本体系 e1 起，右手螺旋)和旋转模糊的弧宽 |ω|·曝光 [rad]。 · 示例: `poc_diabolo_model_and_vision`
- `diabolo_params` `无输入 → table` GPU: 无 — 空竹与绳的尺寸字典。``kind`` = red / blue / patterned / green(论文表 I 的质量、直径、长度、轴承)。 · 示例: `poc_diabolo_model_and_vision`
- `diabolo_render` `table × table → rgb` GPU: 无 — 用光线追踪绘制空竹的 1 帧(RGB float (H, W, 3)，[0, 1])。 · 示例: `poc_diabolo_model_and_vision`
- `diabolo_scene_mjcf` `table → any` GPU: 无 — 第二实现(独立实现)场景的 MJCF 字符串(不需要 mujoco)：空间肌腱 棍端 → 空竹 → 棍端，长度上限 = 绳(单侧约束 = 仅在拉伸时拉 = 与无摩擦滑轮的精确模型相同的物理，用软约束和隐式速度更新这一不同解法求解)。棍端为 mocap(每步写入位置)。空竹为自由关节刚体(质量 = 论文表 I，惯性为假定。旋转不与绳耦合)。``wrap_axle`` = True 时，肌腱缠绕在轴(半径 r)的圆柱上(从下侧通过，未验证)。**Raises** ``ValueError``：params 的形式、timestep ≤ 0、solref 不是 2 个正数。 · 示例: `poc_diabolo_model_and_vision`
- `diabolo_simulate` `signal × signal × any × scalar × scalar × table → table` GPU: 无 — 在棍的运动 ``sticks`` 下，以步长 ``dt`` 将空竹推进到 ``t_end``。 · 示例: `poc_diabolo_model_and_vision`
- `diabolo_spheroid` `signal × signal × scalar → table` GPU: 无 — 棍端 2 点(焦点)与绳长 → 辅助旋转椭球：a = l/2，c = |x_L − x_R|/2，b = √(a² − c²)(式 1 的正确形式)。 · 示例: `poc_diabolo_model_and_vision`
- `diabolo_spin_from_markers` `signal × signal × scalar × scalar → table` GPU: 无 — 每帧的相位 ψ_k(mod 2π)与模糊弧宽 → 旋转速度 ω，单位 rad/s(绕轴，右手螺旋)。 · 示例: `poc_diabolo_model_and_vision`
- `diabolo_state_sequence` `matrix × any × table → signal` GPU: 无 — 由位置序列 X (N, 3) 和棍 (N, 2, 3) 只运行论文的状态转移(用于对观测轨迹分类，不求解动力学)。非有限的行保持前一状态(跟踪丢失的帧)。返回 (N,) 的状态名。**Raises** ``ValueError``：形状、长度、拼写。 · 示例: `poc_diabolo_model_and_vision`
- `diabolo_throw_catch_truth` `signal × signal × matrix × table → table` GPU: 无 — 从放开状态 (p0, v0) 出发的抛物线(闭式)在过了最高点之后，相对接球的棍 ``sticks``(固定的 (2, 3))首次进入“低于连接两棍的平面 且 s < c_F”的时刻(论文的 FLYING → ON_STRING 条件 + 平面规则。绳是否张紧由调用方确认)。 · 示例: `poc_diabolo_model_and_vision`
- `diabolo_track` `any × table × table → table` GPU: 无 — 帧序列 → 空竹中心 (N, 3)、轴 (N, 3)、警报 ``ok`` (N,)、残差 (N,)。逐帧调用 :func:`diabolo_axis_from_image`(无学习，不依赖前一帧)。无法估计的帧为 NaN 且 ``ok = False``。**Raises** ``ValueError``：帧序列为空或不是序列。 · 示例: `poc_diabolo_model_and_vision`
- `spheroid_closest` `signal × table → table` GPU: 无 — 点 x → 旋转椭球面上的最近点 ``point``、带符号距离 ``s``(内侧 > 0，论文中 s 的定义)、向外的单位法线 ``normal``(最近点处梯度的方向)。 · 示例: `poc_diabolo_model_and_vision`
- `string_tension_from_sag` `signal × signal × signal × scalar → table` GPU: 无 — 由绳的 V 字形(棍端 2 点与轴的位置)求张力(无摩擦滑轮 = 两侧张力相等)。 · 示例: `poc_diabolo_model_and_vision`
- `string_tension_static` `scalar × table → table` GPU: 无 — 两棍停在同一高度、间距 2c，空竹静止于最低点：下垂 b = √(a² − c²)，张力 T = m g a / (2b)，绳与水平的夹角 atan2(b, c)。**Raises** ``ValueError``：间距在 (0, 绳长) 之外。 · 示例: `poc_diabolo_model_and_vision`

#### drive / doseunif (3)
- `dose_cv_from_sizes` `any × scalar × scalar → table` GPU: 无 — 由实测粒径求 1 剂含量的 CV(仅考虑颗粒数的涨落，Poisson)及其偏差与区间。 · 示例: `poc_dose_uniformity_from_grinding`
- `dose_cv_lognormal` `scalar × scalar × scalar × scalar → table` GPU: 无 — 从粒径呈对数正态分布的粉体中取 1 剂(药物 ``dose_mg``)时含量的 CV(仅考虑颗粒数的涨落)。 · 示例: `poc_dose_uniformity_from_grinding`
- `grind_time_for_dose_cv` `signal × signal × scalar × scalar → table` GPU: 无 — 对矩径 D63 随时间的变化拟合粉碎定律，反算含量 CV 降到目标值所需的粉碎时间。 · 示例: `poc_dose_uniformity_from_grinding`

#### drive / env (16)
- `beta_from_mor` `scalar → scalar` GPU: 无 — 能见度 → 消光系数 β = −ln(contrast)/能见度(:func:`mor_from_beta` 的逆)。 · 示例: `poc_driving_weather`
- `env_params` `无输入 → table` GPU: 无 — 汇总渲染条件(传给 :func:`env_render`)。 · 示例: `poc_driving_weather`
- `env_render` `table × matrix × matrix → table` GPU: 无 — 以物理单位渲染太阳、天空、阴影、灯光、前照灯、雾、雨和眩光。 · 示例: `poc_driving_weather`
- `fog_beta_from_profile` `any × any × scalar × scalar × scalar → table` GPU: 无 — 由路面纵向亮度曲线测定雾的消光系数 β(Hautière 等 2006 的思路)。 · 示例: `poc_driving_weather`
- `julian_day` `any → scalar` GPU: 无 — 儒略日(UT)。``when`` = 带时区的 datetime(转换为 UTC)，或数值(直接作为儒略日)。 · 示例: `gallery_drive_lateral_env`
- `koschmieder` `any × any × scalar × any → any` GPU: 无 — Koschmieder 定律: 距离 d 处物体的视亮度 L = L₀ e^{−βd} + L_h (1 − e^{−βd})(可用数组)。 · 示例: `gallery_drive_lateral_env`
- `mor_from_beta` `scalar → scalar` GPU: 无 — 消光系数 β [1/m] → 能见度 = −ln(contrast)/β。默认 0.05 = WMO 的气象光学视程(MOR ≈ 2.996/β)，0.02 = Koschmieder(3.912/β)。 · 示例: `gallery_drive_lateral_env`
- `road_row_distance` `any × scalar × scalar × scalar → any` GPU: 无 — 平坦路面上的图像行 → 相机到路面点的水平距离(精确)。地平线以上的行为 ``inf``。 · 示例: `poc_driving_weather`
- `sight_stop_speed` `scalar × scalar × scalar → scalar` GPU: 无 — 能在可见距离 ``sight`` 内停下的最大速度 v*: drivelong.stopping_distance_grade(v*) = sight。 · 示例: `poc_driving_weather`
- `sun_at` `any × scalar × scalar → table` GPU: 无 — 给定日期时间(带时区的 datetime 或儒略日)的太阳高度角与方位角。公式直接使用 :func:`geocam.sun_position`(NOAA 太阳位置公式 = Meeus "Astronomical Algorithms" 第 25 章的低精度版，NOAA 大气折射)，另加日期时间的接收方式和日地距离。 · 示例: `poc_driving_weather`
- `sun_events` `scalar × scalar × scalar × scalar × scalar → table` GPU: 无 — 当日(当地日历日)的日出、正午(中天)、日落时刻，以及日出日落的方位角和中天高度。 · 示例: `poc_driving_weather`
- `sun_illuminance` `scalar → table` GPU: 无 — 晴天(云量 ``cloud`` ∈ [0, 1])的太阳照度 [lx]: ``direct_normal``(正对太阳的面)、``diffuse``(水平面上的散射)、``air_mass``。 · 示例: `poc_driving_weather`
- `sun_vector` `scalar × scalar → any` GPU: 无 — 太阳方向的单位向量(世界坐标系，由地面指向太阳)。 · 示例: `poc_driving_weather`
- `tone_map` `any × scalar → any` GPU: 无 — 保持颜色的 HDR 相机阶调压缩: m = 各像素最大通道 × exposure，显示 = 亮度 × exposure × (1 + m/4)/(1 + m) —— m ≪ 1 时为线性，最大通道在 m = 2 时恰好达到 1，更亮的像素整体相除使最大通道为 1(颜色比 = 色度不变。灯光不会因饱和而变白，假定: 车载 HDR 相机)。 · 示例: `gallery_drive_lateral_env`
- `veil_chroma_limit` `any × scalar → scalar` GPU: 无 — 对颜色 ``color``(RGB 比)、亮度 ``luminance`` 的灯光叠加白光 W(光幕、雾的大气光)时，色度距离 |(c L + W·1)/|c L + W·1| − c/|c||(与 balltrack.ball_detect 的 chroma 相同的量)达到 ``tol`` 的 W* [cd/m²]。 · 示例: `poc_driving_weather`
- `veiling_luminance` `any × any → any` GPU: 无 — 失能眩光的光幕亮度 L_v [cd/m²] (可用数组)。E_glare = 眼睛位置处光源的照度 [lx]，θ = 光源与视线的夹角 [度]。 · 示例: `gallery_drive_lateral_env`

#### drive / granular (23)
- `beverloo_fit` `signal × signal × scalar × scalar → table` GPU: 无 — 用最小二乘将 ``log W = log(C ρ_b √g) + n log(D₀ − k d)`` 拟合到排出速率序列 ``W_i(D0_i)``，返回指数 ``n`` 与系数 ``C``(真值 n = 2.5、C ≈ 0.58)。返回：``n``、``C``、``rms_log``(对数残差)。**Raises** ``ValueError``：点少于 3 个 / 存在 ``D0 ≤ k d`` 的点 / W ≤ 0。 · 示例: `poc_granular_heap_repose`
- `beverloo_rate` `scalar × scalar × scalar → scalar` GPU: 无 — Beverloo 排出定律 ``W = C ρ_b √g (D₀ − k d)^{5/2}`` [kg/s] (Beverloo 等 1961；系数 C ≈ 0.58、k ≈ 1.4 采用 Nedderman 1992 的整理)。``D0`` = 圆孔直径 [m]，``d`` = 粒径 [m]，``bulk_density`` = 堆积密度。 · 示例: `poc_granular_heap_repose`, `poc_powder_scoop_pour`
- `cone_profile_px` `signal × scalar × scalar → signal` GPU: 无 — 圆锥母线的截面 ``c(u)`` [px] (``u`` = 到轴的距离 [px])。 · 示例: `gallery_drive_soil_tactile`
- `container_fill_level` `image2d → table` GPU: 无 — 从容器内部的侧视图像(粉体覆盖率，容器内尺寸 = 图像)读取填充率与粉面倾斜。 · 示例: `poc_granular_heap_repose`
- `container_synth` `scalar → table` GPU: 无 — 合成从侧面看透明容器内部的粉体覆盖率(表面为平面，可倾斜)。真值 = ``fill_frac``。 · 示例: `poc_granular_heap_repose`
- `datum_tilt_check` `table → table` GPU: 无 — 根据 :func:`repose_angle_silhouette` 的返回值(左右斜面角与地面倾斜)判定**基准面是否倾斜**。 · 示例: `poc_geodetic_height_frames`, `poc_granular_heap_repose`
- `discharge_synth` `scalar × scalar × scalar × scalar × scalar × scalar → table` GPU: 无 — 合成高度图序列：粉体以 Beverloo 速率从圆孔 ``D0`` 落下，在下方堆积成休止角为 φ 的圆锥。 · 示例: `poc_granular_heap_repose`
- `dispense_mass_from_video` `any × scalar × scalar × signal → table` GPU: 无 — 由高度图序列求出料质量与排出速率 —— 各帧料堆体积 × ρ_b，对时间做直线拟合(最小二乘)。 · 示例: `poc_granular_heap_repose`
- `heap_mass` `scalar × scalar → scalar` GPU: 无 — ``m = ρ_b V`` [kg]。``bulk_density`` 为堆积密度 [kg/m³] (不是颗粒密度 —— 由 2500 kg/m³ 的玻璃球堆成的料堆，填充率 ≈ 0.6，ρ_b ≈ 1500 kg/m³)。**Raises** ``ValueError``：体积 < 0、密度 ≤ 0。 · 示例: `poc_granular_heap_repose`
- `heap_scene_mjcf` `scalar × scalar → table` GPU: 无 — 在平底料斗(正方形孔口，边长 ``orifice_d``)中堆放刚体球的场景的 MJCF 字符串(**无需 mujoco**，登记在台账中)。 · 示例: `poc_granular_heap_repose`
- `heap_spheres_select` `matrix × scalar × scalar × scalar → table` GPU: 无 — 只选出属于料堆的球：位于料仓底板以下(``z < floor_height − r``)且在料仓半径 3 倍以内。残留在料仓中的球(平底的滞留层)与滚走的球不属于料堆。返回：``pos``(选出的中心)、``n_in_bin``、``n_runaway``、``radius_95``(料堆半径的估计)。**Raises** ``ValueError``：剩余少于 ``keep_min``(未形成料堆 —— 避免在光滑台面上 1,200 个中有 600 个逃逸时仍默默测量)。 · 示例: `poc_granular_heap_repose`
- `heap_synth_cone` `scalar × scalar → table` GPU: 无 — 合成已知休止角的圆锥料堆(侧视图像 = 抗锯齿的覆盖率，高度图 = 格子单元中心的高度)。 · 示例: `poc_granular_heap_repose`
- `heap_volume_cone` `scalar × scalar → table` GPU: 无 — 圆锥料堆的闭式 —— 给定 ``R``、``H``、``phi_deg`` 中的**恰好 2 个**，返回其余一个及体积。 · 示例: `poc_granular_heap_repose`, `poc_powder_scoop_pour`
- `heap_volume_heightmap` `image2d × scalar → scalar` GPU: 无 — 高度图中料堆的体积 ``Σ (z − z_ground) pitch²`` [m³]。``ground`` 为同形状的地面高度(None = 0)。负高度(低于地面)截为 0 —— 不从料堆中减去坑洞。**Raises** ``ValueError``：形状、pitch。 · 示例: `poc_granular_heap_repose`
- `hopper_discharge_rate` `signal × signal × scalar → table` GPU: 无 — 由底板以下的质量序列 ``m(t)`` 求排出速率 [kg/s] —— 只对总质量 ``lo`` 至 ``hi`` 的区段做直线拟合(排除起始段与即将停止段；Beverloo 稳态流的假定)。返回：``rate``、``n_frames``(区段内帧数)、``t_range``、``rms`` [kg]。**Raises** ``ValueError``：区段内少于 3 帧(排出过快以致没有帧 —— 不会默默返回 2 点的斜率)/ 时刻非单调。 · 示例: `poc_granular_heap_repose`
- `powder_flowability_class` `scalar → table` GPU: 无 — 休止角 → 流动性等级(USP <1174> Table 1，原始出处 Carr 1965)。 · 示例: `poc_granular_heap_repose`
- `repose_angle_heightmap` `image2d × scalar → table` GPU: 无 — 由高度图求休止角 φ —— ``demops.dem_slope`` 坡度直方图的众数。 · 示例: `poc_granular_heap_repose`
- `repose_angle_silhouette` `image2d → table` GPU: 无 — 从侧视图像(粉体覆盖率)读取休止角 φ —— 分别对左右斜面做直线拟合，排除坡脚与顶部。 · 示例: `poc_granular_heap_repose`
- `spheres_render_shaded` `matrix × scalar × scalar × scalar × scalar → rgb` GPU: 无 — 带阴影绘制侧面正交投影(numpy 的 z 缓冲，Lambert)。用于 GIF。返回 ``(rows, cols, 3)`` [0, 1]。 · 示例: `poc_granular_heap_repose`, `poc_powder_scoop_pour`
- `spheres_to_heightmap` `matrix × scalar × scalar × scalar → image2d` GPU: 无 — 由球心序列 ``pos (n, 3)`` [m] 与半径生成俯视高度图(每个格子单元取球面的最大高度，没有则为 0)。网格以 ``pitch`` 为步长划分 ``[-extent, extent]²``。 · 示例: `poc_granular_heap_repose`
- `spheres_to_silhouette` `matrix × scalar × scalar × scalar × scalar → image2d` GPU: 无 — 由球心序列生成从侧面(y 方向)看的正交投影覆盖率图像(圆盘之并，抗锯齿)。第 0 行在最上方。 · 示例: `poc_granular_heap_repose`, `poc_powder_scoop_pour`
- `spoon_tilt_critical` `scalar × scalar × scalar → scalar` GPU: 无 — 粉体开始从勺子洒出的倾角 θ_c [度] (2 维截面、准静态、无壁面摩擦 —— **自行推导**)。 · 示例: `poc_granular_heap_repose`
- `spoon_tilt_dispense` `scalar × scalar × scalar × scalar → table` GPU: 无 — 倾角 θ 下洒出的粉体比例(与 :func:`spoon_tilt_critical` 相同的 2 维模型，严格的 ``tan(φ − θ)``)。 · 示例: `poc_granular_heap_repose`

#### drive / grind (13)
- `ae_band_power` `signal × scalar → table` GPU: 无 — 以 2 种方式计算 AE 的频带功率(一种按公开分析代码的定义，另一种用 ``acoustics.stft`` 的密度谱)。 · 示例: `poc_powder_grinding_ae`
- `ae_read_csv` `any → signal` GPU: 无 — 将 AE 的原始 CSV(表头 ``header_lines`` 行 + 每 1 行 1 个样本的 ADC 值)转换为电压 [V] 信号。 · 示例: `poc_powder_grinding_ae`
- `ae_size_correspondence` `signal × signal → table` GPU: 无 — AE 频带功率与 D50 的对应关系(单调性、相关性、log–log 斜率 α，``P ∝ D50^α``)。 · 示例: `poc_powder_grinding_ae`
- `breakage_first_order_fit` `signal × signal → table` GPU: 无 — 拟合一阶破碎速率 ``w(t) = w₀ exp(−S t)``(Deniz 2004 的式 (2)，出处 Austin)。 · 示例: `poc_powder_grinding_ae`
- `comminution_energy` `scalar × scalar → table` GPU: 无 — 粉碎定律的闭式(Reddy 式 (1)、(5)〜(7))。``x_product`` 与 ``energy`` **恰好给出其一**。 · 示例: `poc_dose_uniformity_from_grinding`, `poc_powder_grinding_ae`
- `comminution_law_fit` `signal × signal → table` GPU: 无 — 对粒径随时间的变化 ``d(t)`` 拟合粉碎定律(假定能量 ∝ ``t``，见模块开头)。误差以 **log(粒径)** 衡量。 · 示例: `poc_powder_grinding_ae`
- `particle_image_d50` `image2d × scalar → table` GPU: 有(许可列表) — 由覆盖率图像中的颗粒求 D10 / D50 / D90 [µm]。面积为 **标签内覆盖率之和**(计入边缘的部分像素，不会因阈值而变粗)。 · 示例: `poc_dose_uniformity_from_grinding`, `poc_powder_grinding_ae`
- `particle_image_synth` `scalar × scalar × scalar → table` GPU: 无 — 撒布互不重叠圆盘(颗粒投影)的覆盖率图像及真值(直径 [µm] 为对数正态，``pitch`` µm/px)。 · 示例: `poc_dose_uniformity_from_grinding`, `poc_powder_grinding_ae`
- `particle_size_dx` `table × scalar → scalar` GPU: 无 — 体积累积 ``q`` % 处的粒径 Dq [µm] (D10 / D50 / D90 对应 ``q`` = 10 / 50 / 90)。 · 示例: `poc_powder_grinding_ae`
- `particle_size_oversize` `table × scalar → scalar` GPU: 无 — 粒径 ``x`` [µm] 以上的体积比例(筛上 R(x)，0〜1)。端部累积按 log(粒径) 插值(与 :func:`particle_size_dx` 的默认约定相同)。 · 示例: `poc_powder_grinding_ae`
- `particle_size_read` `any → table` GPU: 无 — 读取激光衍射粒度分布 CSV(表头的 ``key,value`` 行 + 以 ``SizeClasses`` 开头的表)。 · 示例: `poc_dose_uniformity_from_grinding`, `poc_powder_grinding_ae`
- `particle_size_synth` `scalar × scalar → table` GPU: 无 — 将对数正态的 **体积** 分布分配到与仪器相同区间的粒度分布(附真值)。 · 示例: `poc_dose_uniformity_from_grinding`, `poc_powder_grinding_ae`
- `replicate_compare` `any → table` GPU: 无 — 用同一标尺并列独立试验间的离散与各组(材料)之间的差异。 · 示例: `poc_powder_grinding_ae`

#### drive / gsplat (7)
- `gs_catalog_html` `table → table` GPU: 无 — 写出单个自包含的目录 HTML:从缩略图列表中选择多个 3DGS 并查看。 · 示例: `gsplat_product_viewer`
- `gs_from_world` `table → table` GPU: 无 — 返回在世界的面上贴附高斯的 3DGS(``world`` = driveworld 的世界 dict：V, F, face_color, objects)。 · 示例: `gsplat_product_viewer`, `poc_kendama`
- `gs_read_file` `无输入 → table` GPU: 无 — 读取 3D Gaussian Splatting 文件，返回高斯的中心、颜色、不透明度、尺度和朝向。 · 示例: `gallery_drive_world_io`
- `gs_render` `table × matrix → table` GPU: 无 — 用相机渲染 3DGS(``pose`` = world→camera 4×4，``K`` 3×3，与 driveworld.world_camera 相同的约定：朝 −Z 看，行号上小下大)。 · 示例: `poc_kendama`
- `gs_render_fn` `table → any` GPU: 无 — 返回 ``render_fn(world, cam) → (H, W, 3)``(:func:`kendamaworld.camera_perceiver` 渲染的替换接口)：每次调用时用 :func:`gs_update` 将高斯重新附着到世界当前的顶点，再以 ``cam``(dict：pose, K, width, height)执行 :func:`gs_render`。``render_kw`` 原样传给 gs_render。具有属性 ``n_calls``、``n_pairs``(累计)。 · 示例: `poc_kendama`
- `gs_update` `table × table → table` GPU: 无 — 根据世界**当前的**顶点重新计算高斯的中心与朝向(原地修改并返回同一个 dict)。 · 示例: `poc_kendama`
- `gs_viewer_html` `table → table` GPU: 无 — 把 3DGS 做成可在浏览器中旋转查看的单个自包含 HTML(无外部 URL、无 CDN、可离线运行)。 · 示例: `gsplat_product_viewer`, `gsplat_trained_product`

#### drive / humanoid (4)
- `humanoid_clip_mesh` `table → table` GPU: 无 — 步行距离 ``distance`` [m] 处的网格(``{"V","F","color","label","dims"}``，原点 = 腰部正下方，+x = 前方)。 · 示例: `gallery_drive_world_objects`, `poc_driving_humanoids`
- `humanoid_impostors` `table → table` GPU: 无 — 预先从 **n_yaw 个方位 × n_phase 个相位** 的方向渲染剪辑(:func:`humanoid_walk_clip`)。 · 示例: `poc_driving_humanoids`
- `world_camera_impostors` `table × matrix × matrix → table` GPU: 无 — 用 :func:`driveworld.world_camera` 拍摄世界，并将 ``actors`` 的替身(impostor)**按深度比较前后**后贴上。 · 示例: `poc_driving_humanoids`
- `world_pose_humanoid` `table → any` GPU: 无 — 将世界中的物体 ``i``(用 :func:`driveterrain.add_mesh_object` 放置的 ``humanoid_clip_mesh``)设为步行距离 ``distance`` 时的姿态，并重新放到 ``(x, y, yaw)``(只改写顶点。面、颜色、标签、``dims`` 不变)。 · 示例: `gallery_drive_world_objects`

#### drive / inf (12)
- `global_to_tile` `无输入 → any` GPU: 无 — 全局坐标 → (i, j, x, y)(用于比较。远处的坐标已被浮点数的步长舍入)。 · 示例: `gallery_drive_world_io`
- `pose_normalize` `无输入 → any` GPU: 无 — 对 (区块, 区块内坐标) 进位或借位区块编号，使坐标落入 [0, tile)。返回值 (i, j, x, y)。★不是加到全局坐标后再重新除，而只移动区块内坐标 —— 步长与距离无关。 · 示例: `poc_driving_endless_map`
- `tile_digest` `table → any` GPU: 无 — 区块网格(mesh)的指纹(SHA-256，基于顶点、面、标签、颜色的字节序列)。用于重建按位一致的门禁。 · 示例: `poc_driving_endless_map`
- `tile_edge_crossing` `table → scalar` GPU: 无 — 道路穿过区块 (i, j) 某条边的位置(区块内坐标，沿边 0..tile)。没有则为 None。``side`` ∈ {"E", "W", "N", "S"}。★由边的编号决定: 区块 (i, j) 的 E 与区块 (i+1, j) 的 W 是同一条边(同一哈希)。 · 示例: `poc_driving_endless_map`
- `tile_hash` `无输入 → scalar` GPU: 无 — 由区块(或格点、边)的编号 (i, j)、世界种子和用途盐值得到 64 位整数(SplitMix64 4 次，仅用整数)。也处理负编号(按 2 的补码折入 64 位)。相同输入在任何环境下得到相同的值。 · 示例: `gallery_drive_world_io`
- `tile_height` `any × any × table → any` GPU: 无 — 区块 (i, j) 内点 (x, y) 的地面高度 [m]: 全局整数网格上的 Perlin 噪声 × relief，道路周围平坦 (``flat`` m 内为 0，``blend`` m 内 smoothstep)。网格编号 = 区块编号 × cells + 单元编号(整数精确)，插值只用单元内的小数部分 —— 接缝处连续，远处也不丢失有效数字。 · 示例: `poc_driving_endless_map`
- `tile_mesh` `table → table` GPU: 无 — 区块 (i, j) 的地面网格(mesh)(区块内坐标)与道路面。返回值 ``{"V" (N, 3), "F" (M, 3), "label" (M,), "color" (M, 3), "roads", "ij" (tile_roads 的返回值)}``。地面 = 标签 0，道路 = 标签 1(道路是略高于地面的带)。 · 示例: `poc_driving_endless_map`
- `tile_params` `无输入 → table` GPU: 无 — 区块参数表。``tile`` = 边长 [m]，``cells`` = 每个区块的网格单元数(起伏波长 ≈ tile/cells)，``relief`` = 起伏振幅 [m]，``road_width`` [m]，距道路 ``flat`` m 内平坦，再用 ``blend`` m 过渡回起伏(★flat 是即使地面网格三角形跨到道路上，地面也不会高出道路的宽度: 路宽的一半 + 网格对角线 —— 10 m 网格为 3.5 + 14.1 ≈ 18 m。取 6 m 时道路被埋进地面)，``p_road`` = 道路穿过边的概率，``jitter`` = 区块内分岔点的偏移(相对区块边长的比例)，``seed`` = 世界种子。 · 示例: `poc_driving_endless_map`
- `tile_road_distance` `any × any × table → any` GPU: 无 — 区块 (i, j) 内的点 (x, y)(区块内坐标)到最近道路中心线的距离。★也查看相邻 8 个区块的道路 (把相邻道路平移到区块内坐标)—— 使接缝附近两侧区块给出相同的距离。 · 示例: `poc_driving_endless_map`
- `tile_roads` `table → table` GPU: 无 — 区块内的道路: 穿越点(区块内坐标)与分岔点，以及从分岔点到各点的线段。返回值 ``{"hub" (2,), "ends" [(side, (x, y))], "segments" (K, 2, 2)}``(无穿越点时为空)。 · 示例: `poc_driving_endless_map`
- `tile_stream` `table × table → table` GPU: 无 — 保持车辆所在区块 (i, j) 周围的 (2·radius + 1)² 个区块，丢弃移出范围的区块(原地修改 ``cache``)。返回值 ``{"loaded": [(i, j)], "evicted": [(i, j)], "n": 持有的区块数}``。 · 示例: `poc_driving_endless_map`
- `tile_uniform` `无输入 → scalar` GPU: 无 — 把 :func:`tile_hash` 的高 53 位映射为 [0, 1) 内的均匀实数(可用双精度精确表示)。 · 示例: `gallery_drive_world_io`

#### drive / japan (23)
- `building_prisms` `any → any` GPU: 无 — 把建筑的占地轮廓(footprint)挤出到高度,合并为一个三角网格。 · 示例: `gallery_drive_city_terrain`
- `buildings_in_box` `table → any` GPU: 无 — 只返回重心(底面顶点的平均)落在框 [xmin,xmax]×[ymin,ymax] 内的建筑。 · 示例: `gallery_drive_city_terrain`
- `citygml_synthetic` `无输入 → any` GPU: 无 — 生成与真实数据结构相同的最小 CityGML 2.0 字符串(用于测试和演示)。 · 示例: `gallery_drive_city_terrain`, `poc_driving_japan_town`
- `japan_stats` `table → table` GPU: 无 — 道路网的明细表: 各类型的边数、总长、平均宽度，宽度来源的明细，以及特征节点的数量。 · 示例: `poc_driving_japan_town`
- `japan_world` `table → table` GPU: 无 — 由道路网构建日本城镇的 3-D 世界(driveworld 格式)。 · 示例: `poc_driving_japan_town`
- `jp_crossbuck_mesh` `无输入 → any` GPU: 无 — 铁路道口警告标志(× 形，黄底黑边)+ 立柱。标志板朝 +x。 · 示例: `gallery_drive_japan_roads`
- `jp_mirror_mesh` `无输入 → any` GPU: 无 — 道路凸面镜(橙色立柱 + 圆形镜面，镜面朝 +x)。 · 示例: `gallery_drive_japan_roads`
- `jp_pole_mesh` `无输入 → any` GPU: 无 — 生成日本电线杆(混凝土杆 + 横担)的三角网格。 · 示例: `gallery_drive_japan_roads`
- `jp_sign_stop_mesh` `无输入 → any` GPU: 无 — 停车让行(规制标志 330-A)标志: 红底倒正三角形(边长 side = 80 cm，边线和文字为白色，边缘与底为红色 —— 附表第二 备考一(三)3(8))+ 立柱。标志板朝 +x(来车一侧)。省略圆角(R 5 cm)和 "Tomare"(停)文字(字高 13 cm)(文字由路面文字 :func:`jp_stop_marking_mesh` 呈现)。返回值 (V, F, colors)，带面颜色。 · 示例: `poc_driving_japan_town`
- `jp_stop_marking_length` `无输入 → scalar` GPU: 无 — "Tomare"(停)3 字文字列的全长 [m] (= 3 × 字高 + 2 × 字间距 = 9.2 m)。 · 示例: `gallery_drive_japan_roads`
- `jp_stop_marking_mesh` `无输入 → any` GPU: 无 — 路面文字 "Tomare"(停)(法定外标示，白色)。局部坐标: 原点 = 文字列近端(靠近车辆的一侧)的车道中心，+x = 行进方向，+y = 左。 · 示例: `poc_driving_japan_town`
- `latlon_to_local` `any × any → any` GPU: 无 — 经纬度 [deg] → 以原点 origin = (lat0, lon0) 为中心的等距圆柱近似平面坐标 (x 东, y 北) [m]。 · 示例: `poc_driving_japan_town`
- `osm_parse` `any → table` GPU: 无 — 读取 OSM XML(字符串或文件路径)，把节点转换到局部平面坐标 [m]。 · 示例: `poc_driving_japan_town`
- `osm_road_graph` `table → table` GPU: 无 — 由 OSM 的读取结果构建道路网。 · 示例: `poc_driving_japan_town`
- `osm_road_loops` `table → table` GPU: 无 — 道路并集的边界环。分为外环(道路边缘)与孔(街区)，并用 Douglas–Peucker 抽稀。 · 示例: `poc_driving_japan_town`
- `osm_road_mask` `table → table` GPU: 无 — 将边画成带宽度的线段(端部为圆)得到的**道路并集**二值(2 值)图像。 · 示例: `poc_driving_japan_town`
- `osm_route` `table → table` GPU: 无 — 把 2 个节点间的最短路(Dijkstra，遵守单行)转为车道中心的折线，并按弧长列出停止线。 · 示例: `poc_driving_japan_town`
- `osm_synthetic` `无输入 → any` GPU: 无 — 用于测试和 fuzz 的最小 OSM XML(与真实数据相同的元素: bounds / node / way / tag)。 · 示例: `poc_driving_japan_town`
- `plateau_lod2_mesh` `any → table` GPU: 无 — 从 PLATEAU 的 CityGML 读取 LOD2 建筑,返回局部米制坐标的三角网格 (V, F) 以及每栋建筑的属性。 · 示例: `poc_plateau_venue_lod2`
- `plateau_parse` `any → table` GPU: 无 — 从 PLATEAU CityGML 流式读取建筑的底面多边形、高度和底面标高。 · 示例: `gallery_drive_city_terrain`, `poc_driving_japan_town`
- `polygon_area` `any → scalar` GPU: 无 — 简单多边形的有符号面积(鞋带公式)。逆时针为正。 · 示例: `poc_driving_school`, `poc_real_sem_metal_layer`, `poc_thermal_drift_metrology`
- `prism_mesh` `any → any` GPU: 无 — 将底面多边形挤出为高 ``height`` 的柱体(无底面)。 · 示例: `poc_print_layer_inspection`
- `triangulate_polygon` `any → any` GPU: 无 — 用耳切法对简单多边形(凸或凹均可，无自交)进行三角剖分。 · 示例: `gallery_drive_city_terrain`

#### drive / kendama (19)
- `catch_plan_ballistic` `table → any` GPU: 无 — 由松弛球的 (p, v) 用抛物线闭式求出皿的到达点的计划。返回 ``plan(t, p, v, cup_state) → dict``。 · 示例: `gallery_drive_kendama_racket`
- `catch_plan_staged` `table → any` GPU: 无 — 显式分阶段的接球控制(大皿、小皿、中皿、蜡烛使用同一计划：皿的朝向取自 kp 中招式的姿态)。返回 ``plan(t, p, v, cup_state) → dict``(:func:`kendama_simulate` 的 ``catch_plan``)。 · 示例: `poc_kendama`
- `catch_success_rate` `table → table` GPU: 无 — 大皿的成功率：将初始状态散布 n 次(球挂在支点(皿胴的穿绳孔)下方 L 处，横向加 σ = jitter_pos、速度加 σ = jitter_vel(切向分量)的高斯扰动)，用 :func:`swing_up_plan`(手端出发点 ``origin``)上摆，用 :func:`catch_plan_ballistic` 移动皿。 · 示例: `poc_kendama`
- `elliptic_k_agm` `无输入 → scalar` GPU: 无 — 用算术几何平均计算第 1 类完全椭圆积分 K(k) = ∫₀^{π/2} dφ / √(1 − k² sin² φ)：K(k) = π / (2·AGM(1, √(1 − k²)))。|k| < 1(否则 ValueError)。门禁：K(0) = π/2，K(0.5) = 1.685750354812596(公开值，参数 m = k² = 0.25)。 · 示例: `poc_kendama`
- `hole_detect` `image2d → table` GPU: 无 — 在球的图像中寻找暗圆盘(剑尖的孔)：在球心 ``ball_center`` (col, row)、图像半径 ``ball_radius`` [px] 的圆内，亮度(RGB 平均)低于球亮度中位数的 ``dark_ratio`` 倍、饱和度 (max − min)/max ≥ ``min_sat``(排除灰色的绳)、且色度(RGB / |RGB|)与球色度中位数相差 ``min_chroma`` 以上(处于阴影中的球面只是亮度降低而色度不变 —— 仅凭亮度提取会把阴影误认为孔，经实测后排除)的像素的连通分量中最大者。返回 ``{"found", "col", "row", "angle" (球心 → 孔重心的图像角度 [rad], atan2(Δrow, Δcol)), "offset" (距离 / ball_radius: 0 = 正面, → 1 = 边缘), "ellipticity" (短轴 / 长轴, 由 2 阶矩求得: 1 = 正面的圆, → 0 = 正侧面), "area" [px]}``。找不到则 found 为 False、area 为 0，其余为 NaN。从正面看，孔的中心与球心重合，越转向侧面越靠近边缘并被压扁(offset ≈ sin φ，ellipticity ≈ cos φ，φ = 孔轴与视线的夹角)。若 img 不是 (H, W, 3) 或 ball_radius > 0 不成立则 ValueError。 · 示例: `poc_kendama`
- `kendama_catch_check` `table → table` GPU: 无 — 判定球(半径 r_b)能否落在皿上(边缘半径 r_c < r_b，边缘中心 cup_center，轴 cup_axis，速度 v_cup)的几何判定。 · 示例: `gallery_drive_kendama_racket`
- `kendama_combo_simulate` `table → table` GPU: 无 — 连续技：从球停在 ``sequence[0]`` 皿上的状态开始，重复"放出 → 在飞行中换持 → 把下一个皿移到落点正下方，匹配速度接住" ``n_catch`` 次或直到首次失败(moshikame = ("ozara", "chuzara")，3 皿 = ("ozara", "kozara", "chuzara"))。手端 ``hand0`` = 皿胴中心(换持只用手腕改变朝向，不重新握持：假定)。第一个皿用 :func:`kendama_simulate` 的上摆接住，并以 ``hand0`` / ``hand_v0`` 传入该手端的位置与速度。 · 示例: `poc_kendama`
- `kendama_params` `无输入 → table` GPU: 无 — 剑玉参数表。默认 = ``preset="jka_16_2"``(球 60 mm、横宽 70 mm、全长 180 mm 为日本剑玉协会(JKA)的公开值；剑高 160 mm 与皿 42 / 38 / 35 mm 来自用户提供的 JKA 16-2 型说明(一手资料未核实))。``"recommended_large_cup"`` = 大皿 49 mm、孔 24 mm。 · 示例: `gallery_drive_kendama_racket`, `gallery_drive_world_objects`, `poc_kendama`
- `kendama_simulate` `table → table` GPU: 无 — 剑玉的 2 阶段仿真：绳张紧时，球系在支点(**皿胴的穿绳孔** = 手端 + kp["tie_offset"])上(投影法，与 :func:`ballistics.tether_simulate` 相同：支点固定、真空时轨迹相同，绳长 = kp["pendulum_length"])；松弛后自由落体(重力 + 阻力，kp["bp"]；rho = 0 为真空)。每个 step 用 :func:`kendama_catch_check`(大皿 = 手端 + kp["cup_offset"]，轴 kp["cup_axis"])判定接球，接住即结束。 · 示例: `poc_kendama`
- `noisy_perceiver` `无输入 → any` GPU: 无 — 在感知上加各向同性高斯噪声 ``perceive(t, p, v) → (p̂, v̂)``(位置 σ = noise_pos [m]，速度 σ = noise_vel [m/s])。σ 为负则 ValueError。rng = numpy.random.Generator。 · 示例: `gallery_drive_kendama_racket`
- `parabola_fit_g` `无输入 → table` GPU: 无 — 在重力 g(−z)已知的前提下，用最小二乘拟合抛物线 p(t) = p_r + v_r (t − t_ref) − ½ g (t − t_ref)² ẑ(未知数 6 个 = 位置与速度)。 · 示例: `gallery_drive_kendama_racket`
- `pendulum_launch_speed` `无输入 → scalar` GPU: 无 — 在最低点给予此速度即得振幅 θ₀(能量守恒)：v₀ = √(2gL(1 − cos θ₀))。θ₀ ∈ [0, π]。 · 示例: `poc_kendama`
- `pendulum_period_exact` `无输入 → scalar` GPU: 无 — 振幅 θ₀ ∈ (0, π) 的摆(杆，或在不松弛范围内的绳)的周期 4√(L/g)·K(sin(θ₀/2))。θ₀ → 0 时为 2π√(L/g)。 · 示例: `poc_kendama`
- `pendulum_rod_simulate` `无输入 → table` GPU: 无 — 用 RK4 积分杆摆(约束双向作用：不会松弛)θ̈ = −(g/L) sin θ。返回 ``{"t", "theta", "omega", "energy"}``(energy = ½L²ω² − gL cos θ，单位质量)。用于对比，以验证绳会松弛的 θ₀ > π/2 时的周期定理。 · 示例: `poc_kendama`
- `swing_up_apex` `table → table` GPU: 无 — 用 :func:`swing_up_plan` 时，垂直悬挂的球(位于支点下方 L 处，静止)能升到多高的闭式。若减速加速度 a > g，则在进入减速的瞬间(bang: T/2，trap: 2T/3)绳松弛，球以此时手端高度 z_s 与速度 v_s 自由下落 → 最高点 z = tie_z + z_s − L + v_s²/(2g)(从手端出发点量起的球心；L = 绳的有效长度，tie_z = 支点相对手端的高度)。若 a ≤ g 则不松弛，球停在支点下方 L 处。返回 ``{"accel", "flies", "slack_t", "z_slack", "v_slack", "apex", "apex_above_handle", "apex_above_cup"}``(apex_above_handle = apex − lift；apex_above_cup = 再减去大皿边缘高度的量：到达皿需 ≥ h_c，进入皿的窗口需 h_c ≤ … ≤ h_c + 1.5 r_b)。 · 示例: `poc_kendama`
- `swing_up_lift` `table → scalar` GPU: 无 — 用闭式求上摆(bang)的提升量：使球的最高点位于接球皿中心上方 ``apex_above_cup`` 处的 lift(:func:`swing_up_apex` 的逆)。将 最高点 − lift − cup_z = tie_z + lift/2 − L + 2 lift²/(g T²) − lift − cup_z = A 视为 lift 的 2 次方程，取正根。默认 A = max(h_c + 0.9 r_b, (top_offset − cup_z) + r_b + 0.035)：球的下端越过剑玉最高处 35 mm 的最高点(:func:`catch_plan_staged` 的 hold 在球越过该处之前不靠近皿；越过的时间 ≈ 2√(2·0.035/g) = 0.17 s 内将皿横向退回 10 cm)。减速加速度 4·lift/T² 不超过 g 时球不会飞起(ValueError)。 · 示例: `poc_kendama`
- `swing_up_plan` `table → any` GPU: 无 — 手端(皿胴中心；绳的支点和大皿相对它偏移 kp 的 offset 并随之一起运动)的开环轨迹：从 ``origin`` 竖直向上以 ``T_lift`` 秒提升 ``lift``，之后静止。返回值为函数 t → (3,)(t ≤ 0 时为 origin，t ≥ T_lift 时静止于 origin + lift·ẑ)。 · 示例: `poc_kendama`
- `tether_slack_angle` `无输入 → any` GPU: 无 — 在最低点速度为 v₀ = √(2gL(1 − cos θ₀)) 的球(若为杆则在 θ₀ 处停止的能量)的绳开始松弛的角度 θ_s(自正下方起算)。 · 示例: `poc_kendama`
- `tether_tension_fixed` `无输入 → scalar` GPU: 无 — 手端固定、不可伸长的绳的张力 T = m(v²/L + g cos θ)(v = 速度，θ = 与正下方的夹角)。为负则"绳不能推" = 松弛。 · 示例: `poc_kendama`

#### drive / kendamaworld (12)
- `add_ken` `table × table → scalar` GPU: 无 — 以位姿 (p = 皿胴中心, R) 将剑加入世界(面标签 27/28/30/31 保持不变)。返回值 = objects 的索引。 · 示例: `gallery_drive_world_objects`
- `add_string` `table → scalar` GPU: 无 — 将绳(标签 29，深灰)加入世界。返回值 = objects 的索引。 · 示例: `gallery_drive_world_objects`
- `camera_perceiver` `table → any` GPU: 无 — 仅从图像求出球的 (p̂, v̂) 的感知 ``perceive(t, p, v, scene) → (p̂, v̂) | None``(用于 :func:`kendama.kendama_simulate`，属性 ``observe_all = True`` 时每个 step 都会调用)。**真值 (p, v) 只用于绘制世界，不读取 v。** · 示例: `poc_kendama`
- `ken_mesh` `table → table` GPU: 无 — 剑 + 皿胴(大皿、小皿)+ 中皿的网格(mesh)。原点 = 皿胴中心(手端)，剑 = +x(剑尖朝 +x)，皿胴轴 = +z(大皿在上)。 · 示例: `gallery_drive_world_objects`, `poc_kendama`
- `ken_set_pose` `table × matrix → any` GPU: 无 — 将剑 i 的位姿设为 (p, R)(只改写顶点)。不是剑的物体则 ValueError。 · 示例: `gallery_drive_world_objects`
- `ken_truth` `table × table → table` GPU: 无 — 剑 i_ken 的真值投影：接球皿边缘中心(将 anchors[kp["catch_cup"] + "_rim"] 按位姿移动后的点)的 (col, row)、深度、图像中皿的半径 [px] (按大皿半径)、``visible``(位于相机前方且像素在图像内)。与 ballworld.ball_truth 同型。 · 示例: `gallery_drive_world_objects`
- `kendama_clearance` `table → table` GPU: 无 — 从球表面到剑玉(剑、皿胴的回转体)的间隙 [m] (负 = 球陷入剑玉)。使用 kp 中招式的姿态(R_ken，握持处 grip)、手端 ``hand``、球心 ``p_ball``(均为 (3,) 或 (N, 3))。到回转体的距离严格等于到子午面轮廓的 2-D 距离，因此与网格离散化无关。返回 ``{"gap" (N,), "ken" (N,), "cross" (N,)}``(ken / cross = 到各部件的间隙)。物理不求解剑玉与球的碰撞，因此用此量统计"球穿透剑玉"的 step(用于门禁与诚实报告)。``R_ken``(第 19 轮，连续技的换持)：以 (3, 3) 或逐时刻的 (N, 3, 3) 代替 kp["R_ken"] 传入姿态。``grip`` = 握持处(局部)的覆盖。两者都为 None 则与以前相同。 · 示例: `poc_kendama`
- `kendama_pose` `table → table` GPU: 无 — 设置剑玉世界的状态：剑(1 个刚体。握持处 kp["grip"] 位于手端 ``hand``，姿态 ``R_ken`` 默认 = kp 中招式的姿态 kp["R_ken"]：皿胴中心 = hand − R·grip)、球(中心 ``p_ball``)、绳(皿胴穿绳孔 → 球的穿绳孔)。``R_ball`` 默认 = 使球的穿绳孔(−HOLE_AXIS_LOCAL)朝向皿胴穿绳孔的旋转(不求解球的旋转：张紧时正确，飞行中为近似)。返回 ``{"tie", "cup" (接球皿边缘的中心), "cup_axis", "cross" (皿胴的中心), "string_hole", "hole_axis" (大孔的朝向, 世界), "R_ball"}``。``world`` 为 :func:`kendama_world` 的世界(需要 world["kendama"])。 · 示例: `poc_kendama`
- `kendama_rig` `table → table` GPU: 无 — 观察上摆空间(x, y ∈ ±0.4 m，z ∈ 0.55〜1.45 m：手端 1.0 m，绳 0.42 m，提升 0.265 m)的一组相机。n = 2：方位 0° 与 90°；n = 4：每 90°。全部朝向 ``target``(默认 (0, 0, 1.0))。返回 ``[{"pose", "K", "eye", "width", "height"}, …]``(与 ballworld.camera_rig 同型)。 · 示例: `gallery_drive_world_objects`, `poc_kendama`
- `kendama_world` `table → table` GPU: 无 — 地面 + 剑(kp 中招式的姿态 R_ken，握持处 kp["grip"] 位于 ``hand``)+ 带孔的球 + 绳的世界。原点在地面，z 朝上。球位于皿胴穿绳孔下方绳的有效长度(kp["pendulum_length"])处(自正下方向 ``hang_dir`` 一侧摆开 ``hang_deg`` 的位置 —— 若为斜向 (1, −1)，则从方位 0° 与 90° 的两台相机都能看到横向偏移)。若传入 ``p_ball`` 则放在该处。地面分割为 0.25 m 的格子单元(若为 1 张大四边形，跨到相机背后的三角形会整个被丢弃，地面消失)。返回值的 world["kendama"] = ``{"ken", "ball", "string"}``(objects 的索引)+ ``"kp"``。 · 示例: `gallery_drive_world_objects`, `poc_kendama`
- `string_mesh` `无输入 → any` GPU: 无 — 连接 2 点(球的穿绳孔 p_ball 与皿胴的穿绳孔 p_cup)的细棱柱(4 个侧面 + 两端，8 个顶点 12 个面，朝外)。截面为边长 2·radius 的正方形。两点重合则 ValueError。 · 示例: `gallery_drive_world_objects`
- `string_set` `table → any` GPU: 无 — 将绳 i 的两端重新放到 (p_ball, p_cup)(只改写顶点)。不是绳的物体则 ValueError。 · 示例: `gallery_drive_world_objects`

#### drive / lateral (20)
- `ackermann_steer_angles` `any → table` GPU: 无 — 阿克曼转向的内外轮转向角(后轴中心的转弯半径 R，轴距 L，轮距 t)。 · 示例: `poc_driving_lateral`
- `bicycle_model_step` `any → any` GPU: 无 — 线性 2 轮等效模型的 1 步(经典 4 阶 Runge–Kutta，步内 δ 与 u 恒定)。 · 示例: `poc_driving_lateral`
- `clothoid_design` `无输入 → table` GPU: 无 — 用长度 L 的回旋曲线连接直线 → 圆(半径 R)时的各项量。 · 示例: `poc_driving_lateral`
- `clothoid_points` `无输入 → table` GPU: 无 — 曲率随弧长线性变化 κ(s) = κ₀ + (κ₁ − κ₀) s / length 的曲线(回旋曲线的一部分；κ₀ = κ₁ 时为圆弧或直线)上的点。 · 示例: `poc_driving_lateral`
- `curvature_speed_plan` `any → table` GPU: 无 — 由曲率序列构造速度上限，并通过前向、后向 2 遍处理满足加减速上限的速度规划(经典方法)。 · 示例: `poc_driving_lateral`
- `curve_speed_limit` `any → any` GPU: 无 — 在超高 i、横向滑动摩擦系数 f 的曲线(半径 R)上不向外侧滑出的上限速度 v = √(g R (i + f)/(1 − i f)) [m/s]。 · 示例: `gallery_drive_lateral_env`
- `design_min_radius` `any → any` GPU: 无 — 道路构造令解说 (3) 式的最小曲线半径 R = V² / (127 (i + f)) [m] (V 单位为 km/h)。 · 示例: `gallery_drive_lateral_env`
- `fresnel_integrals` `any → any` GPU: 无 — 菲涅耳积分 C(x) = ∫₀ˣ cos(π t²/2) dt、S(x) = ∫₀ˣ sin(π t²/2) dt(奇函数)。 · 示例: `gallery_drive_lateral_env`
- `friction_circle_usage` `any → any` GPU: 无 — 摩擦圆使用率 √(a_x² + a_y²) / (μ g)(超过 1 即在摩擦圆之外 = 超出轮胎能从路面获得的力)。 · 示例: `poc_driving_lateral`
- `lateral_offset` `any → table` GPU: 无 — 点沿折线路径的弧长 s 与横向偏差 n(行进方向左侧为正)。投影到最近的区段。 · 示例: `poc_driving_lateral`
- `offtracking_circle` `无输入 → table` GPU: 无 — 内轮差的过渡过程(闭式)：前轴中心进入半径 R 的圆后行进弧长 s 时的车辆位姿和内侧车轮的半径。 · 示例: `poc_driving_lateral`
- `pure_pursuit_circle_offset` `无输入 → table` GPU: 无 — 用 pure pursuit(以后轴中心为基准)跟踪定常圆(半径 R)时的稳态圆半径 ρ 与横向偏差 ρ − R(向外为正)。 · 示例: `poc_driving_lateral`
- `pure_pursuit_curvature` `any → table` GPU: 无 — pure pursuit：从后轴中心(``pose`` = (x, y, ψ)，可为 (N, 3))瞄准路径上前方距离 L_d 处的点的曲率 κ = 2 sin α / L_d。 · 示例: `poc_driving_lateral`
- `rear_axle_path` `any → table` GPU: 无 — 由前轴中心的折线轨迹，求无滑动牵引出的后轴中心轨迹(每个区段为精确的追踪曲线)。 · 示例: `poc_driving_lateral`
- `stanley_steer` `any → table` GPU: 无 — Stanley 转向角 δ = ψ_e + atan2(−k e, k_s + v)(前轴中心的横向偏差 e 以路径左侧为正，ψ_e = 路径方向 − ψ)。 · 示例: `gallery_drive_lateral_env`
- `stanley_straight_decay` `无输入 → signal` GPU: 无 — 直线路径上 Stanley(不限幅)的前轴横向偏差 e(t) 的闭式。 · 示例: `gallery_drive_lateral_env`
- `steady_cornering` `无输入 → table` GPU: 无 — 线性 2 轮等效模型的稳态圆周转向(速度 u，转弯半径 R = u/r，左转为正)。 · 示例: `gallery_drive_lateral_env`
- `time_to_line_crossing` `无输入 → scalar` GPU: 无 — TLC：假定车辆(的基准点)以当前曲率沿圆(或直线)行驶，到达车道边界所需的时间 [s]。 · 示例: `poc_driving_lateral`
- `turn_maneuver_check` `table → table` GPU: 无 — 判定左转、右转的通行方式(道路交通法第34条第1、2款 / 交通教则 5-7-2)。数值幅度均为假定(``SOURCES``)。 · 示例: `poc_driving_lateral`
- `understeer_gradient` `无输入 → table` GPU: 无 — 不足转向梯度 K = (m/L)(l_r/C_f − l_f/C_r) [rad/(m/s²)]，以及特征速度 / 临界速度。 · 示例: `poc_driving_lateral`

#### drive / lidar (4)
- `lidar_scan` `mesh × table × matrix → table` GPU: 无 — 以位姿 ``T_sensor``(world ← sensor)的 LiDAR 对网格世界 ``(V, F)`` 发射 1 次扫描。 · 示例: `poc_driving_school`
- `lidar_spec` `无输入 → table` GPU: 无 — 生成旋转式 LiDAR 的规格 dict(默认 32 beam、仰角 −25…+15°、方位 0.2° = 1800 列)。 · 示例: `poc_driving_school`
- `ray_box_ranges` `points × points → signal` GPU: 无 — 从原点 ``origin`` 沿方向 ``dirs (...,3)`` 的射线进入轴对齐盒为止的距离(slab 法)。 · 示例: `gallery_drive_city_terrain`
- `ray_plane_range` `points × points → signal` GPU: 无 — 从原点 ``origin`` 沿方向 ``dirs (...,3)`` 的射线到达平面 ``ax+by+cz+d=0`` 为止的距离。 · 示例: `poc_table_tennis_bounce`

#### drive / locomotion (12)
- `capture_margin` `vector × vector × scalar × points → measurement` GPU: 无 — LIPM 捕获点到支撑集合的有符号距离(0 步可捕获性)。 · 示例: `walking_ops_tour`
- `com_from_silhouette` `mask → keypoints` GPU: 无 — 二值轮廓的质心(形心),以图像坐标 ``(row, col)`` 表示。在没有完整质量模型时作为身体 COM 投影的廉价代理(evis/hillco 姿态)。空掩码返回 ``(nan, nan)``。 · 示例: `consumer_hillco`, `walking_ops_tour`
- `com_support_margin` `vector × points → measurement` GPU: 无 — 静态稳定裕度:COM 的地面投影到支撑多边形边界的有符号距离(McGhee & Frank 1968)。 · 示例: `consumer_hillco`, `consumer_onocollo`, `physical_ai_perception`, `walking_ops_tour`
- `contact_points` `points × any → points` GPU: 无 — 位于地面平面 ``[a,b,c,d]`` 的 *tol* 以内的点 = 地面接触点。 · 示例: `consumer_onocollo`, `walking_ops_tour`
- `foot_slip_metrics` `any × mask × points → table` GPU: 无 — 支撑相中足部的水平滑移、由足测得的前进量,以及“只有躯干前进”的闸门。 · 示例: `walking_ops_tour`
- `footstep_plan` `mask → table` GPU: 无 — 在落脚点掩码上的左右交替脚步序列(精确最短路径)。 · 示例: `walking_ops_tour`
- `gait_phase` `matrix → table` GPU: 无 — 根据高度逐帧把每只脚分类为支撑相(着地)或摆动相。 · 示例: `consumer_hillco`, `consumer_onocollo`, `walking_ops_tour`
- `gait_step_events` `any × scalar × scalar × scalar → table` GPU: 无 — 用滞回从足部轨迹中提取行走的步(离地 -> 摆动 -> 着地)。 · 示例: `walking_ops_tour`
- `lipm_capture_point` `points × points × scalar → points` GPU: 无 — 线性倒立摆的瞬时捕获点,``xi = c + c_dot / omega``。 · 示例: `walking_ops_tour`
- `static_contact_force_lp` `points × normals × vector × scalar × scalar → table` GPU: 无 — 线性化摩擦锥下的静态接触力分配(``scipy.optimize.linprog``)。 · 示例: `walking_ops_tour`
- `support_line_margin` `vector × points → measurement` GPU: 无 — 对任何支撑集合都有定义的支撑裕度,包括双足(线段)支撑。 · 示例: `walking_ops_tour`
- `support_polygon` `points → table` GPU: 无 — 地面接触点的凸支撑多边形(地面 x, y 平面)。 · 示例: `consumer_hillco`, `consumer_onocollo`, `physical_ai_perception`, `walking_ops_tour`

#### drive / long (13)
- `hill_hold_brake_min` `scalar → scalar` GPU: 无 — 能在坡上保持静止的最小制动 [m/s²] = max(0, |a_creep − g sin θ| − c_rr g cos θ)(静摩擦平衡)。 · 示例: `poc_driving_longitudinal`
- `hill_start_command` `scalar × scalar × scalar × scalar → any` GPU: 无 — 坡道起步的指令。在 t_release 之前保持(蠕行 + 制动 b_hold)。 · 示例: `poc_driving_longitudinal`
- `hill_start_rollback` `scalar × scalar × scalar → table` GPU: 无 — 停在上坡(θ > 0)的车辆松开制动、τ 秒后施加驱动 a_drive 时的溜车量(不计空气阻力的闭式)。 · 示例: `poc_driving_longitudinal`
- `long_energy_residual` `table → any` GPU: 无 — 能量收支的残差(单位质量 [J/kg]): (½ v² + g z) − (½ v₀² + g z₀ + W_drive − W_brake − W_rr − W_drag)。 · 示例: `poc_driving_longitudinal`
- `long_params` `无输入 → table` GPU: 无 — 纵向运动的参数(默认值全部为**假定**；出处见模块的 docstring)。 · 示例: `poc_driving_longitudinal`, `poc_driving_town`, `poc_driving_traffic`, `poc_driving_weather`
- `long_simulate` `scalar × scalar × any → table` GPU: 无 — 用 RK4 积分纵向运动方程(在事件时刻切分步长；见模块的 docstring)。 · 示例: `poc_driving_longitudinal`, `poc_driving_town`, `poc_driving_traffic`, `poc_driving_weather`
- `plan_command` `table → any` GPU: 无 — 把 :func:`stop_line_plan` 转为 ``command(t, s, v)``。t0 之前为 ``before``(None = 保持速度)，react / cruise 保持速度(驱动 = 抵消坡度 + 滚动阻力 + 空气阻力，下坡为负时改为制动)，brake1 / brake2 为计划值，停下后保持 (制动 ``hold_brake``(None = 上限)+ 蠕行驱动)。 · 示例: `poc_driving_longitudinal`, `poc_driving_weather`
- `road_eval` `table × scalar → any` GPU: 无 — 按弧长 l 查询道路纵断面: (z, sin θ, cos θ)。``road`` = None(平坦)/ 数值(恒定坡度角 θ [rad]，z = l sin θ)/ :func:`road_profile` 的 dict。在折点上取其后区段的值(右连续)。 · 示例: `poc_driving_longitudinal`
- `road_profile` `table → table` GPU: 无 — 把水平距离与高度的折线 (x, z)(与 drivecourse.course_slope 的 ``profile`` 形式相同)转换为以**沿路面的弧长 l** 表示的纵断面。 · 示例: `poc_driving_longitudinal`
- `skill_test_score` `table → table` GPU: 无 — 汇总驾驶技能考试的扣分(警察厅 丙运发第 12 号 令和 4 年的扣分细目)。 · 示例: `gallery_drive_lateral_env`, `poc_driving_longitudinal`, `poc_driving_weather`
- `skill_test_thresholds` `无输入 → table` GPU: 无 — 评分所用的数值(通知中没有距离和时间的数字；每个值都附出处)。 · 示例: `gallery_drive_lateral_env`
- `stop_line_plan` `scalar × scalar → table` GPU: 无 — 从感知瞬间(时刻 t0，前端到停止线的距离 ``dist_to_line``，速度 v)出发，规划在停止线前 ``margin`` 处停下的**2 段制动**。 · 示例: `poc_driving_longitudinal`, `poc_driving_weather`
- `stopping_distance_grade` `scalar × scalar × scalar → scalar` GPU: 无 — 停车距离的闭式 = 空走距离 v ρ + 制动距离 (1/(2k)) ln(1 + k v²/A)，A = brake + g sin θ + c_rr g cos θ(k = 0 时为 v²/(2A))。 · 示例: `poc_driving_longitudinal`, `poc_driving_weather`

#### drive / motion_io (3)
- `events_to_frames` `table → voxel` GPU: 无 — 将事件按时间等分为 n_frames，逐像素累加极性得到帧 (T, H, W)(ON = +1，OFF = −1)。 · 示例: `gallery_drive_world_io`
- `read_bvh` `无输入 → table` GPU: 无 — 读取 BVH，返回骨架以及所有帧中关节的世界坐标。 · 示例: `gallery_drive_world_io`
- `read_events` `无输入 → table` GPU: 无 — 读取事件相机的事件序列(.txt / .csv / .npy / .npz)。 · 示例: `gallery_drive_world_io`

#### drive / ozaki (6)
- `cross_covariance_reproducible` `points × points → matrix` GPU: 无 — 以与点顺序无关的比特返回 Kabsch / ICP 的互协方差 ``H = (P − P̄)ᵀ (Q − Q̄)``(3×3)。 · 示例: `poc_reproducible_icp`
- `fp64_emulation_probe` `无输入 → table` GPU: 无 — 以表的形式返回 cuBLAS 的 FP64 仿真(CUDA 13.0 Update 2 及以后)在本机上是否可用。 · 示例: `poc_reproducible_icp`
- `kabsch_reproducible` `points × points → table` GPU: 无 — 以与点顺序无关的比特返回使 ``|R p + t − q|`` 最小的刚体 ``R``、``t``(Kabsch 1976)。 · 示例: `poc_reproducible_icp`
- `matmul_ozaki` `matrix × matrix → matrix` GPU: 无 — 由精确的低精度部分积组装 FP64 精度的矩阵乘积 ``A @ B``(Ozaki-I / Ozaki-II)。 · 示例: `poc_reproducible_icp`
- `matmul_reproducible` `matrix × matrix → matrix` GPU: 无 — 按位可复现的 FP64 精度 ``A @ B``(无法保证时抛出 ``ValueError`` = fail-closed)。 · 示例: `poc_reproducible_icp`
- `ozaki_error_bound` `matrix × matrix × scalar → matrix` GPU: 无 — ``matmul_ozaki(A, B, n_slices)``(Ozaki-I)截断误差的逐元素保证上界(矩阵)。 · 示例: `poc_reproducible_icp`

#### drive / pass (17)
- `convex_mirror_image` `any → table` GPU: 无 — 凸面镜的虚像(近轴，可用数组)。场景 S064、S130。 · 示例: `poc_driving_pass`
- `convex_mirror_misjudge` `any × any → table` GPU: 无 — 把凸面镜中车辆的距离和速度当作平面镜来读时的误判(近轴闭式，可用数组)。场景 S064、S130。 · 示例: `poc_driving_pass`
- `crest_safe_speed` `any → table` GPU: 无 — 能在可见距离内停下的速度上限(停车距离的反函数，闭式，可用数组)。场景 S065。 · 示例: `poc_driving_pass`
- `crest_sight_distance` `无输入 → table` GPU: 无 — 越过凸形竖曲线(抛物线)的最小视距(闭式)。场景 S065、S081(上坡顶点附近)。 · 示例: `poc_driving_pass`
- `hill_meeting_yield` `无输入 → table` GPU: 无 — 坡道狭窄处的会车：哪一方让行(交通教则 6-2-1(6)。**法律无明文规定**)。场景 S128。 · 示例: `gallery_drive_mirrors_crowds`
- `lane_change_follower_decel` `any → table` GPU: 无 — 变更车道后，目标车道的跟随车为了不比 min_gap 更接近本车所需的恒定减速度(闭式，可用数组)。场景 S072。 · 示例: `poc_driving_pass`
- `lane_change_permitted` `table → table` GPU: 无 — 是否可以变更车道(依条文判定)。场景 S067、S072、S073。 · 示例: `poc_driving_pass`
- `mirror_image_side` `points → table` GPU: 无 — 道路凸面镜中映出的点看起来位于镜面中心的左侧还是右侧、看起来向哪边移动(平面镜闭式)。场景 S064、S130。 · 示例: `gallery_drive_mirrors_crowds`
- `mirror_road_coverage` `无输入 → table` GPU: 无 — 道路凸面镜(凸面圆弧或平面)中映出的道路范围(俯视 2D，闭式)。场景 S064、S130。 · 示例: `poc_driving_pass`
- `no_overtaking_zones` `table → table` GPU: 无 — 根据道路沿线设施生成第30条禁止超车(为超车而变更车道、从侧方通过)的区间。场景 S081、S009、S130。 · 示例: `poc_driving_pass`
- `overtake_permitted` `table → table` GPU: 无 — 是否可以开始超车(依条文与交通教则判定)。场景 S077、S078、S079、S080、S081、S083。 · 示例: `poc_driving_pass`
- `overtake_requirement` `无输入 → table` GPU: 无 — 超越前车所需的时间、距离，以及对向来车不会到来的临界距离(闭式)。场景 S079、S086、S145(第28条第4款)。 · 示例: `poc_driving_pass`
- `overtake_return_gap` `无输入 → table` GPU: 无 — 被超越的前车**整体映入车内后视镜**时的车距(本车车尾与前车车头之间)。场景 S086、S145。 · 示例: `poc_driving_pass`
- `overtaken_conduct_check` `table → table` GPU: 无 — 被超车一方的义务(第27条)。场景 S085。 · 示例: `poc_driving_pass`
- `roundabout_entry_check` `table → table` GPU: 无 — 是否可以进入环形交叉口(第37条之2第1、2款，第35条之2)。场景 S102。 · 示例: `poc_driving_pass`
- `roundabout_signal_check` `signal × signal → table` GPU: 无 — 对环形交叉口内的打灯示意评分(第53条第2、4款，交通教则 5-5-1(2))。场景 S069。 · 示例: `poc_driving_pass`
- `roundabout_signal_point` `any → table` GPU: 无 — 驶出环形交叉口时开始打左转灯的位置(沿顺时针行进的角度)。场景 S069。 · 示例: `poc_driving_pass`

#### drive / pegfail (16)
- `failure_confusion` `any × any → table` GPU: 无 — 混淆矩阵与正确率：行 = 注入(真实)类别，列 = 分类结果。``classes`` 之外的名称引发 ValueError(拼写错误)。返回：``matrix``(n, n) int、``classes``、``accuracy``、``n``、``per_class_recall``(各真实类别的召回率，缺失的行为 nan)。 · 示例: `poc_peg_failure_recovery`
- `insertion_episode_summary` `table → table` GPU: 无 — 汇总 1 次运行的记录(:func:`pegfail_episode_run` 的返回值，或具有相同键的 dict)：注入类别、最先**检测到**的失败类别、检测延迟(真实失败的起点 ``failing_onset_tick`` → 检测时间步，时间步 = 10 ms)、恢复次数与成败、最终深度与最大力。 · 示例: `poc_peg_failure_recovery`
- `insertion_failure_classify` `table → table` GPU: 无 — 用表查签名(fail-closed)：命中 1 行则返回其类与恢复，0 行则为 ``"unknown"``(不做推测)，2 行以上则视为表的缺陷抛出 ``ValueError``(通过 :func:`insertion_failure_validate` 的表不会发生)。 · 示例: `poc_peg_failure_recovery`
- `insertion_failure_presets` `table → table` GPU: 无 — 要注入的失败的默认设置(各类别 → :func:`pegfail_episode_run` 的参数)。数值来自 Whitney 的边界：missed_hole = ε₀ 2.5 mm(> W + c_r = 1.2 mm)/ wedging = μ 0.8、θ₀ 4.5°(c/μ = 2.76°)/ jamming = θ₀ 3°(低于 7.35°，因此 μ = 0.3 时不会楔住)，末端插入 4 mm 后将滑台的横向目标向倾斜一侧偏移 +3.0 mm 并保持(腕部弹簧 600 N/m → F_x ≤ 1.8 N，铰链距末端 40 mm，因此 M/(rF_z) 越过平行四边形的斜边。实测：−3.0 mm(反侧)时滑入，+1.6 mm 时停住但比值在内侧 = unknown)/ blocked_hole = 深度 6 mm 处有塞子 / wrong_hole = 朝向侧方 26 mm 处的诱饵孔 / nominal = ε₀ 0.5 mm、θ₀ 1.5°。 · 示例: `poc_peg_failure_recovery`
- `insertion_failure_table` `无输入 → table` GPU: 无 — 失败分类表(数据)：每行 = {``cls``, ``when``(字段 → 允许值的集合，``"*"`` = 任意), ``recovery``, ``basis``}。 · 示例: `poc_peg_failure_recovery`
- `insertion_failure_validate` `table → table` GPU: 无 — 校验表(fail-closed)：字段词汇、类名、恢复名的拼写，**所有对的互斥**(不存在 2 行可能命中同一签名 = 没有在所有字段上允许集合都相交的行对)，**可达性**(unknown 以外的所有类都有 ≥ 1 行)。 · 示例: `poc_peg_failure_recovery`
- `insertion_recovery_primitive` `any → table` GPU: 无 — 恢复原语表(类 → 动作的描述)。``name`` 是表中 ``recovery`` 的词。 · 示例: `poc_peg_failure_recovery`
- `insertion_signature` `table × table → table` GPU: 无 — 将连续的观测离散化为表词汇的签名。 · 示例: `poc_peg_failure_recovery`
- `insertion_stall_detect` `signal → table` GPU: 无 — 从深度时间序列 [m] 检测停滞(在每个时间步 i，若 depth[i] − depth[i − window] < min_advance 则为 stalled)。 · 示例: `poc_peg_failure_recovery`
- `jamming_force_check` `table × scalar × scalar × scalar → table` GPU: 无 — 测得的末端力之比 (F_x/F_z, M/(rF_z)) 是否位于 Whitney 平行四边形内部(封装 pegsim.jamming_diagram，并补充最接近哪条边、哪条斜边对当前接触配置起作用)。 · 示例: `poc_peg_failure_recovery`
- `jamming_parallelogram_planar` `table × scalar → table` GPU: 无 — **由两点接触的平面静力学推导**卡死(jamming)平行四边形(与 pegsim.jamming_diagram 的顶点 = OCW p.34 的值相互核对的第 2 路径)。 · 示例: `poc_peg_failure_recovery`
- `pegfail_scene_mjcf` `table → any` GPU: 无 — 带失败注入的场景的 MJCF 字符串(无需 mujoco)：用 ElementTree 读取 pegsim.peg_scene_mjcf，并添加 (i) 腕部力/扭矩传感器(site ``peg_top`` = 腕部原点，子 body 与父级之间的相互作用力)，(ii) 若给定 ``blocked_depth`` [m]，在孔内放置以该深度为上表面的塞子(圆柱)，(iii) 若给定 ``decoy_xy``，则添加诱饵孔(复制壁、倒角、凸缘(collar)并平移，名称加上 ``decoy_`` 前缀；方框与诱饵重叠，因此移除)。**Raises** ``ValueError``：塞子深度在孔外、诱饵与目标孔重叠(中心距离 < 2(R + W) + 1 mm)。 · 示例: `poc_peg_failure_recovery`
- `tip_force_ratios` `table × signal × signal × signal → table` GPU: 无 — 将末端载荷 (F⃗, M⃗) 换算为 Whitney 比：x = F⃗·e_x / F_z，y = M⃗·(e_x × ẑ) / (r F_z)，F_z = −F⃗·ẑ(压入为正)。若 F_z ≤ 1e-6 N 则比值为 None(无法相除)。``e_x`` 为水平单位向量(:func:`jamming_force_check` 的约定)。**Raises** ``ValueError``：e_x 没有水平分量。 · 示例: `poc_peg_failure_recovery`
- `vision_boundary_flip` `table × signal × scalar → table` GPU: 无 — “在哪里失效”：在真实偏移 ε 上叠加标准差为 σ 的测量噪声时，按各 ε 统计 offset 栏(small/large，边界 W + c_r)与真值**相反**的概率(仅用 numpy)。还返回距边界有几倍 σ(``z``)以及理论值 Φ(−|z|)(噪声为正态时二者一致的门禁)。 · 示例: `poc_peg_failure_recovery`
- `wedging_risk` `table × scalar → table` GPU: 无 — 倾角 θ [rad] 的楔住风险：相对边界 c/μ(OCW p.28)的比值 θ/(c/μ)，以及考虑余量 ``margin_deg`` 的 3 级(``safe`` / ``near`` / ``over``)。封装 pegsim.wedging_check，并以度为单位补充 ``theta_limit_deg``、``headroom_deg`` = c/μ − θ。μ = 0 时边界为 inf，始终为 safe。**Raises** ``ValueError``：θ < 0、margin_deg < 0。 · 示例: `poc_peg_failure_recovery`
- `wrist_load_from_deflection` `table × signal × signal × signal × signal × signal → table` GPU: 无 — 由腕部弹簧的挠度求支撑(+ 重力)施加于销的载荷，以末端为矩心(仅用 numpy)：F⃗ = −k_t q_slide − m g ẑ，M⃗_tip = −k_r (q_hinge − rest) + (p_hinge − p_tip) × F⃗_spring + (p_com − p_tip) × F⃗_g。 · 示例: `poc_peg_failure_recovery`

#### drive / pegsim (18)
- `camera_world_to_cv` `matrix → table` GPU: 无 — 将 MuJoCo 的相机位姿(``d.cam_xmat`` 3×3 = 世界中的相机轴，``d.cam_xpos``)转换为 OpenCV / Fullseye 的外参：X_cv = R X_w + t，R = diag(1, −1, −1) Rwcᵀ，t = −R p(MuJoCo 朝 −Z 看、+Y 向上，OpenCV 为 +Z 向前、+Y 向下)。 · 示例: `poc_pegsim_insertion`
- `chamfer_capture` `table → table` GPU: 无 — 倒角能否在不校正的情况下吸收初始横向偏差 ε₀ [m]：|ε₀| ≤ W + c_r(末端边缘落在倒角面上的条件，推导所得)。 · 示例: `poc_peg_failure_recovery`, `poc_pegsim_insertion`
- `circle_fit_known_radius` `matrix → table` GPU: 无 — 将已知半径 r 的圆拟合到 2-D 点列 (row, col)(只用 Gauss-Newton 求解圆心；部分圆弧也稳定)。 · 示例: `poc_pegsim_insertion`
- `contact_state_predict` `table → table` GPU: 无 — 由真实的销位姿(末端中心与轴向)**仅凭几何**预测接触点的个数与位置(独立于接触计算的第 2 实现)。 · 示例: `poc_pegsim_insertion`
- `coverage_edge_points` `image2d × image2d × image2d → matrix` GPU: 有(许可列表) — 由抗锯齿边界的亮度(覆盖率)返回亚像素边缘点 (u, v)：对 inside 侧像素 p 与前方 2 像素处为 outside 的像素对，边缘位置 = 距 p (−0.5 + f_p + f_q) 像素(f = 该像素 inside 侧的覆盖率 = (I − I_out) / (I_in − I_out))。 · 示例: `gallery_drive_peg`
- `cylinder_fit_known_radius` `points → table` GPU: 无 — 将已知半径 r 的圆柱拟合到 3-D 点云 (N, 3)：用 Gauss-Newton 求轴上的点(垂直于轴的 2 个自由度)与轴向(2 个自由度)。 · 示例: `gallery_drive_peg`
- `hole_centre_from_rgbd` `rgb × image2d × matrix → table` GPU: 无 — 从 1 帧腕部 RGB-D 求孔(暗圆盘)的 3-D 中心(相机坐标)：用 depth 拟合板平面，将抗锯齿边缘提升到平面上，在平面内拟合圆(:func:`measure.fit_circle`)。 · 示例: `gallery_drive_peg`
- `insertion_grid_summary` `table → table` GPU: 无 — 汇总成功率网格：由行 = {eps_mm, tilt_deg, correct, success} 的序列，得到 有/无校正 × ε₀ × θ₀ 的成功率表，以及“无校正时全部成功的最大 ε₀”和“有校正时的成功数 / 总数”。 · 示例: `gallery_drive_peg`
- `jamming_diagram` `table → table` GPU: 无 — 卡死(jamming)图(OCW p.34)：在两点接触深度 l [m] 下，施加力之比 (F_x/F_z, M/(rF_z)) 能使插入推进的区域(平行四边形)。 · 示例: `poc_peg_failure_recovery`, `poc_pegsim_insertion`
- `peg_measure_overlay` `rgb × matrix × matrix → rgb` GPU: 有(许可列表) — 测量值叠加图（仅限 numpy）：真实值 = 大绿色十字，估计值 = 小红色十字，用于圆形拟合的边缘点 = 黄点（imagedraw）。在右下角，围绕真实值的重心粘贴“2*crop”像素正方形的放大图（“crop”是半宽），乘以“zoom”（以直观地看到子像素的重合度）。 · 示例: `poc_pegsim_insertion`
- `peg_offset_from_rgbd` `rgb × image2d × matrix × matrix → table` GPU: 无 — 从 1 帧腕部 RGB-D 求销末端相对孔中心的偏差 (dx, dy) [m] (世界(滑台)坐标) —— 视觉伺服的观测量。 · 示例: `poc_peg_failure_recovery`, `poc_peg_insertion_tactile`, `poc_pegsim_insertion`
- `peg_params` `无输入 → table` GPU: 无 — 销与孔的尺寸表：长度单位为 m，旋转刚度为 N m/rad，相机图像为 px，视场角为 deg。 · 示例: `gallery_drive_peg`, `poc_peg_failure_recovery`, `poc_peg_insertion_tactile`, `poc_pegsim_insertion`
- `peg_scene_mjcf` `table → any` GPU: 无 — 场景的 MJCF 字符串(无需 mujoco)：孔 = 内切面半径为 R 的 n_seg 个箱体组成的环 + 45° 倒角的环 + 孔口面的环圈 + 方框；位置控制的滑台(x, y, z 滑动)上装有由 6 个弹簧关节构成的柔顺腕部，其末端为销(圆柱)。腕部相机位于滑台后方 60 mm、上方 20 mm，向下 45°；侧面相机固定。 · 示例: `poc_pegsim_insertion`
- `peg_synthetic_rgbd` `table → table` GPU: 无 — 带真值的合成 RGB-D(仅用 numpy，无需 mujoco)：从腕部相机(向下 45°，与 MJCF 同向)解析地对板 z = 0(灰)、孔的圆盘(半径 R + W，黑，面低 4 mm)、销(半径 r 的圆柱 + 末端圆盘，橙)进行光线投射。 · 示例: `gallery_drive_peg`, `poc_peg_failure_recovery`, `poc_peg_insertion_tactile`, `poc_pegsim_insertion`
- `peg_tip_from_rgbd` `rgb × image2d × matrix → table` GPU: 有(许可列表) — 从 1 帧腕部 RGB-D 求销末端中心的 3-D 坐标(相机坐标)：销的像素 → depth 点云 → PCA 轴 → 已知半径圆柱拟合；末端在轴向上的位置由一个模型确定，该模型使阴影的端部(亚像素、覆盖率)与投影边缘圆的端部一致。 · 示例: `gallery_drive_peg`
- `two_point_depth` `table → scalar` GPU: 无 — 倾角 θ [rad] 下开始两点接触的插入深度 l₂ [m] (从最窄处到末端中心)。按名称选择 3 种模型之一。 · 示例: `gallery_drive_peg`, `poc_peg_insertion_tactile`, `poc_pegsim_insertion`
- `wedging_check` `table → table` GPU: 无 — 在开始两点接触时的倾角 θ [rad] 下，是否可能发生楔住(wedging)(OCW p.28：θ > c/μ)。 · 示例: `poc_peg_insertion_tactile`, `poc_pegsim_insertion`
- `whitney_clearance` `table → table` GPU: 无 — Whitney 的无量纲间隙(clearance)及由此决定的临界值：c = (D − d)/D、c_r = R − r、θ_m = √(2c)、倒角的容许偏移、楔住角。 · 示例: `poc_peg_failure_recovery`, `poc_pegsim_insertion`

#### drive / pegsym (15)
- `pegsym_scene_mjcf` `matrix × matrix → any` GPU: 无 — 多边形销场景的 MJCF 字符串(无需 mujoco)：孔 = 每条边一个墙体盒(位于最窄处以下)、45° 倒角板和明亮的颈圈(口部平面 z = 0)；销 = 凸网格(mesh)棱柱(截面 ``peg_vertices``，销坐标系，轴位于原点)。滑台具有 x、y、z 滑动关节和 yaw 铰链(位置控制)，其后是 6 自由度的弹簧腕部(倾斜 ``k_rot`` 与扭转 ``k_yaw`` [N m/rad] 分开设定；抓握在扭转方向上较柔软)。相机为腕部相机(位于滑台侧方 30 mm，垂直向下)、距孔 ``station`` [m] 的朝上相机(位于地面平面，从下方观察销的端面)，以及用于绘图的斜上方固定相机 ``side``。每个盒子只位于自身边外侧的半平面内，因此越过角部延伸也不会进入孔内(凸孔无论何种形状都用同样的构造)。**Raises** ValueError：多边形非凸、倒角 < 0、孔深 ≤ 倒角、摩擦 < 0、刚度 ≤ 0。 · 示例: `poc_peg_symmetry_search`
- `plane_topview` `image2d × matrix × matrix × signal → image2d` GPU: 无 — 将斜视或从下方拍摄的图像重采样为从正上方看世界平面 z = ``z`` 的图(单应性 = 投影各网格点并双线性取样)。相机由世界 → OpenCV 相机的 ``R``、``t``(x_c = R X + t)和内参 ``K``(像素中心为整数的约定)给出。网格以 ``centre`` = (x, y) 为中心，边长 ``extent`` [m]，像素 ``res`` [m]。列 = +x，行 = −y(北朝上)。从下方拍摄的图像(镜像)在此图中也为相同朝向。相机后方或图像外的网格点为 ``fill``。返回 (S, S) 的灰度图(彩色转为亮度)。**Raises** ValueError：图像不是 2-D 灰度或 (H, W, 3/4)、K 或 R 不是 3×3、t 不是 3 个分量、extent ≤ 0、res ≤ 0、S > 4096。 · 示例: `poc_peg_symmetry_search`
- `polygon_coverage_image` `matrix → image2d` GPU: 无 — 凸多边形(像素坐标 (col, row) 的顶点列)的覆盖率图像 0..1((size, width)，抗锯齿为 ``ss`` × ``ss`` 的子采样)。带真值的合成的部件。**Raises** ValueError：非凸、size < 8、ss < 1。 · 示例: `poc_peg_symmetry_search`
- `polygon_fit_check` `matrix × matrix → table` GPU: 无 — 点群(销的顶点，或倾斜销投影后的顶点)能否**仅靠平移**放入凸多边形的孔 —— 通过枚举 3 个约束取等号的顶点，精确求解使余量 m 最大的线性规划 max m s.t. n_j·(p + t) ≤ h_j − m(所有点、所有边)(边至多十几条，组合一并求解)。返回 ``fit``(m ≥ 0)、``margin`` [m] (为负时是最小的嵌入量)、``t``(最优平移 (2,))、``active``(取等号的边的编号)。**Raises** ValueError：点群不是 (N ≥ 1, 2) 或非有限、孔不是凸多边形、孔的法线不能包围所有方向(无界)。 · 示例: `poc_peg_symmetry_search`
- `polygon_offset` `matrix × scalar → table` GPU: 无 — 将凸多边形的各边向外平移 ``clearance`` [m] 得到的多边形(角保持尖锐 = 孔图纸的画法)。正多边形则为相似放大，朝向和对称不变。返回 ``vertices``、``normals``、``offsets``(n·x ≤ h)。**Raises** ValueError：非凸、clearance < 0 或非有限、平移后边消失(由于没有凹角，此处只放行不会发生这种情况的形状)。 · 示例: `poc_peg_symmetry_search`
- `polygon_peg` `scalar → table` GPU: 无 — 销的截面(逆时针的顶点列)：正 n 边形(边心距 ``apothem`` [m]，面 0 的法线朝 ``yaw`` [rad])。若 ``cut`` > 0，则用以该顶点方向为法线的直线，在外接圆内侧 ``cut`` [m] 处切掉顶点 0(面 0 与面 1 之间)—— 带键(对称为 n = 1)。返回 ``vertices``(V, 2)、``n``(形状名义上的 n 重对称：带键时为 1)、``apothem``、``circumradius``、``yaw``、``cut``。**Raises** ValueError：n < 3、apothem ≤ 0、cut < 0 或不小于外接圆与内切圆之差(边消失)。 · 示例: `poc_peg_symmetry_search`
- `polygon_two_point_depth` `matrix × matrix × scalar → table` GPU: 无 — 精确求倾斜多边形销的两点接触深度 l₂ [m] (从最窄处 z = 0 到先端中心)：深度 l 时位于 z ≤ 0 的销部分，是先端面顶点与侧面棱线穿过 z = 0 的点的凸包。孔是竖直的棱柱，因此只要这些顶点的水平投影能通过平移放入孔(:func:`polygon_fit_check`)就能进入，l 加深后便放不进 —— 用二分法求其边界。``tilt_dir`` = 倾斜的水平方向 [rad] (世界坐标系，与销截面相同的坐标系)。用于比较的圆的公式(Whitney，pegsim 的 3-D 圆柱精确式 (2R − r(cos θ + sec θ))/tan θ)以内切圆(r = A，R = A + δ)和外接圆(r = A/cos(π/n)，R = (A + δ)/cos(π/n))返回(``circle_in``、``circle_out``)。正方形绕平行于面的轴倾斜时的小角极限为 Goli 等 2024 的式 (2.28) φ = (v − v′)/h，即 l₂ tan θ → 2δ(``goli_small_angle`` = 2δ/tan θ)。奇数 n(三角形)面的对面是顶点，因此在任何方向都比内切圆公式更深。偶数 n 在面法线方向与内切圆公式一致(正方形为 1e-11 m)。有的组合会超出内切圆一侧达 0.03 %(倾斜 6°、距面 15°)。返回 ``l2``、``circle_in``、``circle_out``、``goli_small_angle``(δ 为边心距之差的平均，n 为顶点数)。**Raises** ValueError：θ ≤ 0 或 ≥ 30°、倾斜状态下无法进入最窄处、直到 depth_max 都不发生两点接触。 · 示例: `poc_peg_symmetry_search`
- `polygon_yaw_read` `image2d → table` GPU: 无 — 从俯视图(:func:`plane_topview`，列 = +x、行 = −y)中物体轮廓(亚像素等值线，与 :mod:`pegtactile` 相同的 ``threshold_sub_pix``)的复傅里叶系数，**以周期 2π/n 为模**读取朝向。若为 n 重对称，非零系数只有 k ≡ 1 (mod n)，且 arg(c₁₋ₙ c₁ⁿ⁻¹)/n 与起点无关(:func:`pegtactile.symmetry_order_contour`)。传入 ``n`` 时，使用该 n 的相位而非检测到的 n(图纸已知 n 时。即使实际图像边缘抖动使多余系数变得显著，也能读出相位)。``polarity`` = 物体是暗("dark"，孔)还是亮("bright"，销的端面)。灰度先用 2 % 与 98 % 分位数拉伸到 0..1，再取 0.5 的等值线。返回 ``n_detected``、``n_used``、``yaw``(世界的朝向，因图像的行是 −y 而恢复符号，取周期 2π/n_used 的代表值 [0, P))、``centroid_px`` (row, col)、``amps``。n_used = 0(圆)时 yaw = nan。**Raises** ValueError：polarity 未知、图像平坦、无轮廓、n < 0。 · 示例: `poc_peg_symmetry_search`
- `relative_yaw_from_images` `image2d × image2d × scalar → table` GPU: 无 — 以 n 重对称的商求销(朝上相机 → 重采样到先端面平面的图)与孔(腕部相机 → 孔口平面的图)的朝向差：Δ = symmetry_fold(yaw_peg − yaw_hole, n)。两者都用 :func:`polygon_yaw_read` 读取，因形状而异的相位常数(顶点方向与面方向之差)在相同形状之间相减时抵消(孔是将销向外平移得到的相似形)。带键(n = 1)不相似，因此会残留小的偏差(由门禁测量)。返回 ``delta``(将销旋转 −delta 即对齐)、``peg``、``hole``(读数)、``n``。**Raises** ValueError：n < 1、读取失败(:func:`polygon_yaw_read` 的异常)。 · 示例: `poc_peg_symmetry_search`
- `rotation_search_plan` `scalar × scalar → table` GPU: 无 — 旋转搜索的候选(施加给销的 yaw 修正)：将 1 个周期 P = 2π/n_sym 等分为 M = ⌈P/(2 phi_cap)⌉ 份的步长 s = P/M(≤ 2 phi_cap，因此捕获窗口无缝覆盖)。``order`` = "alternate"(从估计值起 0, +s, −s, +2s, …)或 "sweep"(0, s, 2s, …)。n_sym = 0(圆)为 1 个候选。返回 ``angles``(M,)、``step``、``period``、``M``。**Raises** ValueError：n_sym < 0、phi_cap ≤ 0、order 未知。 · 示例: `poc_peg_symmetry_search`
- `rotation_window` `scalar × scalar × scalar → table` GPU: 无 — 销进入孔(有倒角时为孔口)的旋转窗口。正 n 边形的闭式(推导)：中心对齐时，顶点位于距面法线 π/n ∓ φ 的方向，最向外突出的顶点在法线方向的长度 a cos(π/n − |φ|) 不超过 A + δ(+ W)即可进入：φ = π/n − arccos(x)，x = (A + δ + W) cos(π/n)/A(若 x ≥ 1，窗口占满半周期 π/n)。arccos 在 1 附近有舍入下限，故写成 atan2(√(1 − x²), x)。若传入 ``peg_vertices``、``hole_vertices``，还通过对线性规划(:func:`polygon_fit_check`，平移也自由)的二分法测量正、负方向的窗口(第二实现。带键形状只能用这个)。返回 ``phi_fit``(最窄处而非孔口)、``phi_cap``(倒角的孔口)、``period`` = 2π/n、``M`` = ⌈period/(2 cap)⌉、``lp``(``plus``/``minus``：传入顶点时，进入孔口的窗口两端 = 包含 0 的连通区间。扫描将半周期分成 360 步，端点用二分法)。 其中 cap 在给出 mu 时为 phi_eff，否则为有限的 phi_cap 或最小 lp 窗口。 · 示例: `poc_peg_symmetry_search`
- `search_expected_tries` `scalar × scalar → table` GPU: 无 — 旋转搜索的期望尝试次数(未知朝向误差 e 在 1 个周期内均匀时，精确)。对候选 c_k(:func:`rotation_search_plan`)，第 k 次成功是在 e 首次落入 [c_k − φ, c_k + φ] (周期 P)时，因此 E = Σ_k (1 − |∪_{i<k} I_i|/P)。计算时在区间端点处分割圆周，对每个小区间统计最先覆盖它的候选编号(相同的值，O(M²) 的向量运算)。若步长恰为 2φ，则 E = (M + 1)/2(``closed``)。与不知道对称性的搜索(周期 2π，M₁ = ⌈π/φ⌉)之比 ``ratio_vs_blind`` → 1/n。传入 ``estimate_sigma`` [rad] 时，假设 e 在估计值周围服从标准差 σ 的正态分布(卷绕到周期)，并返回 "alternate" 顺序的期望次数(``expected_with_estimate``，数值积分 4,096 点)。返回 ``expected``、``closed``、``M``、``blind_expected``、``ratio_vs_blind``。**Raises** ValueError：n_sym < 1、phi_cap ≤ 0、sigma ≤ 0。 · 示例: `poc_peg_symmetry_search`
- `spiral_expected_tries` `matrix × scalar × scalar → table` GPU: 无 — 横向偏差在半径 ``rho`` 的圆盘内均匀时，依次尝试点列 ``points`` 直到首次捕获(距离 ≤ ``capture``)的期望尝试次数。``measured`` = 圆盘内网格(grid × grid，舍弃圆外)的平均。``closed`` = 扫过面积的近似：k 个点扫过面积 k·p·s，因此到达半径 r 时 k = πr²/(ps)，若 r 在圆盘内均匀则 E = πρ²/(2ps) + 1/2(p、s 由点列估计：s = 相邻点距离的中位数，p = 外圈点半径每圈的增量)。若有任何点都捕获不到的网格点，则 ``uncovered`` > 0(覆盖的漏洞)。**Raises** ValueError：点不是 (N ≥ 3, 2)、capture、rho ≤ 0、grid < 11。 · 示例: `poc_peg_symmetry_search`
- `spiral_search_points` `scalar × scalar × scalar → table` GPU: 无 — 走滑搜索点：阿基米德螺旋线 r = p φ/(2π) 在每个弧长``step`` [m]（从中心）到半径``r_max`` 处。相邻匝之间的间距=“节距”。如果倒角要捕获的半径为c，则相邻匝之间的最差距离``sqrt((pitch/2)^2 + (step/2)^2)``小于或等于c，则可以覆盖倒角。将此值作为“worst_gap”返回。返回“points”(N, 2)、“worst_gap”、“n”。 **引发** ValueError：pitch·step·r_max ≤ 0，点数超过200,000。 · 示例: `poc_peg_symmetry_search`
- `symmetry_fold` `scalar × scalar → scalar` GPU: 无 — 将角折叠到 n 重对称的商 SO(2)/C_n 的代表区间 (−π/n, π/n] (n = 1 时为 (−π, π]，n = 0 = 圆时为 0)。群恒等式 symmetry_fold(α + 2πk/n, n) = symmetry_fold(α, n) 即为门禁。**Raises** ValueError：n < 0、角非有限。 · 示例: `poc_peg_symmetry_search`

#### drive / pegtactile (19)
- `contact_candidates` `table × signal × signal → table` GPU: 无 — 单一接触的候选点(世界坐标系)以及该点**在几何上能否接触**的标志。``tip_rim`` = 末端边缘的圆(半径 r，垂直于轴)，仅当边缘点能触及壁面(比最窄处更深：半径 ≥ R − tol)或倒角面(半径 ≥ R + (W − 深度) − tol)时有效。``mouth`` = 孔最窄处边缘的圆(半径 R，z = −W)，仅当销身表面经过该点(到轴线的距离为 r ± tol，且末端比最窄处更深)时有效。若不筛选候选，两点接触合力的作用线恰好经过“未接触壁面一侧的末端边缘”的巧合会被误读为一点接触(在试制的楔住中实测)。``tol`` 涵盖 MuJoCo 软接触的穿透量与 36 边形壁面(顶点处 +0.02 mm)。返回 ``tip_rim``、``rim_ok``、``mouth``、``mouth_ok``、``depth``。**Raises** ValueError：tip 或 axis 不是有限的 3 个分量、n_az < 8、tol < 0。 · 示例: `gallery_drive_peg`
- `contact_state_from_wrench` `table × signal × signal × signal × signal × signal → table` GPU: 无 — 接触力旋量(销从孔受到的 F 与绕抓握点 g 的 M，世界坐标系)→ 接触状态(无学习的规则)。 · 示例: `poc_peg_insertion_tactile`
- `equivariance_check` `any × any × signal × scalar × signal → table` GPU: 无 — 等变性门禁的部件：将形状旋转角 θ 后绘制(``render(θ)`` → 图像)，检查感知 op(``op(画像)`` → (row, col, 朝向))的答案是否按群作用变化。期望：位置绕 ``centre`` = (row, col) 旋转 θ，朝向前进 θ(mod 2π/n，n = 0 时不比较朝向)。返回 ``pos_err_px``(最大值)、``ang_err_deg``(最大值，mod 2π/n 的最短距离，不比较时为 nan)、``rows``(每个角度)。**Raises** ValueError：render 或 op 不可调用、连 1 个角度都没有或角度非有限、n < 0、centre 不是 2 个分量。 · 示例: `poc_peg_insertion_tactile`
- `friction_from_single_contact` `signal × text × any × signal → table` GPU: 无 — 由一点接触滑动期间的接触力求壁面摩擦系数(仅在滑动期间贴在 Coulomb 极限上，粘着时为下限)。末端边缘在壁上(``where="tip"``)时，法向 = 水平(指向孔中心)，摩擦 = 竖直 → μ̂ = |F_z|/|F_水平|。销身在最窄处边缘(``"mouth"``)时，法向 = 垂直于轴，摩擦 = 轴向 → μ̂ = |F·a|/|F_⊥|。``chamfer`` 时位于 45° 倒角面上(法向 = (−r̂, 1)/√2，需要 ``c`` = 接触点)。``"none"`` 为 None。返回 ``mu``(可为 None)。**Raises** ValueError：where 不在词汇表内、F 或 axis 不是有限的 3 个分量、倒角时缺少 c。 · 示例: `poc_peg_insertion_tactile`
- `pad_context` `table → table` GPU: 无 — 在膜的合成与读取中只构建 1 次的工具：像素中心网格 (X, Y)、Cerruti 核、3 色光源、无载荷膜的背景与标记基准图像。 · 示例: `gallery_drive_soil_tactile`, `poc_knife_tactile_toughness`, `poc_peg_insertion_tactile`, `poc_tactile_dipole_torque`
- `pad_loads_to_peg_wrench` `scalar × signal × scalar × signal × table → table` GPU: 无 — :func:`peg_wrench_to_pad_loads` 的逆运算：2 个垫的 (P, q) 与膜承受的扭转(每 1 个垫，绕夹爪 x 轴)→ 垫施加于销的力旋量(夹爪坐标系，以抓握点为矩心)与抓握力。施加于销的扭转 = −2·torsion。返回 ``F``、``M``(3,)、``grip`` = (N_R + N_L)/2。**Raises** ValueError：q 不是有限的 2 个分量、P 或 torsion 非有限。 · 示例: `poc_peg_insertion_tactile`
- `pad_marker_displacement` `scalar × signal × table → table` GPU: 无 — 在标记位置求膜表面位移(闭式 + Cerruti 卷积)：方向 φ 的剪切 |q| 是将 x 向 Mindlin 场旋转 φ 所得，u(p) = R(φ) u_x(R(−φ)p)(核为各向同性半空间，因此对旋转封闭)，再加上法向载荷的径向位移 ūr(Johnson 式 3.41b)与扭转场。扭转场在 ``torsion_model="partial_slip"``(默认，自 2026-10-06 起)时为部分滑移(:func:`cuttouch.torsion_partial_slip` 的数值解，从边缘环开始滑移)，在 ``"no_slip"`` 时为 0.4.0 及之前的无滑移场(:func:`tactorque.torsion_stick_field`)。扭转超过全滑移时，膜无法再传递更多扭转，因此用表中最后一行(粘着圆仅剩 1 个环)的场绘制，并设置 ``torsion_slipping`` 标志。``pts`` 为标记中心(px，省略时为 ``ctx`` 的基准位置)。返回 ``u_m``(N, 2)[m]、``hz``、``mp``(Hertz 与 Mindlin 的表)、``phi``、``Q``、``torsion``、``torsion_model``、``torsion_ratio``、``torsion_slipping``。全滑移(|q| ≥ μP)以 ``mp['slipping']`` 标志表示(场取 c = 0)。**Raises** ValueError：P ≤ 0(垫已脱离)、q 不是有限的 2 个分量、torsion_model 拼写错误。 · 示例: `gallery_drive_soil_tactile`, `poc_knife_tactile_toughness`
- `pad_params` `无输入 → table` GPU: 无 — 指尖垫参数表：圆顶半径 R、凝胶的 E 与 ν、垫与销之间的摩擦 μ、抓握力 G₀ [N]、手指半间距 w(销平削面的半宽)、抓握点到销上端的距离、膜相机的视场与像素数、标记(间距、半径 [px]、浓度)、销的质量与重心(与 pegfail 的默认值相同)。 · 示例: `gallery_drive_soil_tactile`, `poc_knife_tactile_toughness`, `poc_peg_insertion_tactile`, `poc_tactile_dipole_torque`
- `pad_shear_asymmetry` `signal × signal → table` GPU: 无 — 将 2 个垫的膜剪切分为共同分量(= 轴向力，F_z/2 的方向)与差分量(= 力偶，M/(2w))：共同 = (q_R + q_L)/2，差分 = (q_R − q_L)/2。``ratio_v`` = |差分_v| / (|共同_v| + |差分_v|)(0 = 同向，1 = 纯力偶)，``opposite_v`` = 左右 v 分量的符号是否相反。**Raises** ValueError：不是有限的 2 个分量。 · 示例: `gallery_drive_peg`
- `pad_tactile_frame` `scalar × signal × table → table` GPU: 无 — 1 个垫的合成图像：Hertz 压入的明暗(:func:`tacsim.membrane_render_rgb`)+ 中心按位移移动的标记(:func:`tacslip.membrane_render_markers`，不通过插值扭曲)。``noise`` 为像素正态噪声的 σ。返回 ``rgb``(含标记，(n, n, 3))、``shading``(无标记 = 用于读取力，实机需要去除标记)、``pts``(标记中心的真值 [px])、``truth``(P、q、φ、Q、c/a、滑移标志、a、扭转、扭转模型与全滑移标志)。扭转场模型为 ``torsion_model``(默认 ``"partial_slip"``，:func:`pad_marker_displacement`)。**Raises** ValueError：P ≤ 0、noise < 0、拼写错误。 · 示例: `poc_peg_insertion_tactile`
- `pad_tactile_read` `table × table → table` GPU: 无 — 1 个垫的图像 → (P̂, q̂, 扭转)。 · 示例: `poc_knife_tactile_toughness`, `poc_peg_insertion_tactile`
- `peg_wrench_to_pad_loads` `signal × signal × table → table` GPU: 无 — 2 个垫施加于销的力旋量(夹爪坐标系，以抓握点为矩心)→ 各垫的 (法向力 P，膜承受的剪切 q = (q_u, q_v))。 · 示例: `poc_knife_tactile_toughness`, `poc_peg_insertion_tactile`
- `stall_verdict` `table × scalar × any → table` GPU: 无 — 两点接触停住时的 Whitney 判定(OCW p.28)：θ > c/μ̂ 为楔住(即使撤去力也拔不出的一侧)，否则为卡死(可通过力的方向解开)。c = (R − r)/R。μ̂ 是在同一次插入的滑动区间由触觉读出的值(:func:`friction_from_single_contact`)，若为 None 或 ≤ 0 则不作推测，返回 ``"unknown"``。返回 ``verdict``("wedging" / "jamming" / "unknown")、``theta_limit``。**Raises** ValueError：θ 非有限或为负。 · 示例: `poc_peg_insertion_tactile`
- `symmetric_peg_shape` `text → image2d` GPU: 无 — 销的截面(带真值的合成，抗锯齿覆盖率 0..1，(size, size))：圆、正三角形、正方形、正六边形(外接圆半径 ``radius`` [px])、带键的圆(D 形切口：用弦切去圆的一部分，n = 1)。按 ``angle`` [rad] **旋转形状本身来绘制**(旋转图像会引入插值)。``centre`` = (col, row)，``ss`` = 每像素沿 1 条边的子采样数。**Raises** ValueError：未知形状、size < 16、radius ≤ 0、ss < 1。 · 示例: `poc_peg_insertion_tactile`
- `symmetry_order_contour` `matrix → table` GPU: 无 — 从闭合轮廓 (N, 2) = (row, col) 的复傅里叶系数(:func:`fourierdesc.contour_fourier_complex`，按弧长重采样，±K 阶)读取 n 重对称的阶数：若为 n 重对称，非零系数只有 k ≡ 1 (mod n)。显著(|c_k| > rel·|c_1|，k ≠ 0, 1)的 k 的 (k − 1) 的最大公约数即为 n。若没有显著的 k，则为圆(``n`` = 0 = 连续)。朝向 α̂ = arg(c₁₋ₙ c₁ⁿ⁻¹)/n(与起点选取无关的不变量，mod 2π/n)。n = 1 时由 c₂ c₁⁻² 得 α̂ = −arg(·) —— k = −1(振幅为 3 倍)的常数相位因形状而异，无法在没有参照的情况下确定分支(α / α + π)(试作时弄错了 180°)。返回 ``n``、``angle``(rad，n = 0 时为 nan)、``amps``(k → |c_k|/|c_1|)、``sig``、``centroid``(c₀ = (row, col))。2 阶矩的朝向在 n ≥ 3 时惯性各向同性而不可用(PoC 的陷阱门禁)。**Raises** ValueError：轮廓不是 (N ≥ 8, 2)、K < 6。 · 示例: `poc_peg_insertion_tactile`
- `two_point_forces` `table × signal × signal × signal × signal × signal → table` GPU: 无 — 将两点接触(Whitney)的力旋量分解为 2 个接触力与壁面摩擦 μ(平面，两点均向下滑动的 Coulomb 假定)。 · 示例: `poc_peg_insertion_tactile`
- `whitney_wrench` `table × text × scalar × scalar × scalar × scalar → table` GPU: 无 — 闭式接触力旋量(Whitney 的准静态平面，带真值的合成)：对倾角为 θ(轴上端朝 +x)、末端深度为 ``depth``(从口部平面起)的销，按 ``state`` = ``"one_point"``(末端边缘在 −x 壁)/ ``"mouth"``(销身在 +x 最窄处边缘)/ ``"two_point"``(两者)施加法向力 ``fn_tip``、``fn_mouth`` 与向下滑动的 Coulomb 摩擦 μ。两点接触时在 depth = W + l₂(θ) 处销身也接触边缘(闭式)。``g`` 为抓握点(省略时为从末端沿轴的销长 − 8 mm 处)。返回 ``F``、``M_g``(绕抓握点)、``g``、``tip``、``axis``、``points``。**Raises** ValueError：state 不在词汇表内、θ 不在 (0, π/2) 内、depth、μ、法向力非有限或为负。 · 示例: `gallery_drive_peg`, `poc_peg_insertion_tactile`
- `wrist_deflection_from_rgbd` `rgb × image2d × matrix × matrix × signal × signal × scalar → table` GPU: 仅在链中(许可列表) — 由 1 张腕部 RGB-D 求腕部的平移挠度与倾斜：销的像素(pegsim 的颜色分类)→ depth 点云 → PCA 轴 → 已知半径的圆柱拟合(:func:`pegsim.cylinder_fit_known_radius`)→ 世界坐标系中的轴线 → 在滑台坐标系(减去由编码器已知的位置 ``carriage_pos``)中通过铰链高度 z = ``hinge_z`` 的点 = (Δx, Δy)。由轴的方向用 atan2 求倾斜 (θ_x, θ_y)。圆柱的轴向位置不可见，因此不输出 Δz(如实说明：腕部的 z 向压缩由 k̂ 与触觉的 F_z 补足，:func:`pegtactile_process_episode`)。返回 ``dx``、``dy``、``axis``、``tilt_x``、``tilt_y``、``rms_cyl``、``n_pts``。**Raises** ValueError：形状不匹配、销的像素少于 50(不可见)。 · 示例: `gallery_drive_peg`
- `wrist_stiffness_fit` `signal × signal → table` GPU: 无 — 由腕部挠度 Δx(腕部相机)与销所受接触力的同一分量 F 求 k = Σ FΔx / ΣΔx²(过原点的最小二乘，准静态平衡 F_contact + F_spring ≈ 0 ⇒ F_contact = kΔx)。同一公式也可用于旋转(角度与力矩)。返回 ``k``、``r2``、``rms_N``、``n``、``span``。**Raises** ValueError：点少于 3 个、形状不同、非有限、Δx 的范围小于 ``min_span``(病态：不动的弹簧无法确定 k)。 · 示例: `poc_peg_insertion_tactile`

#### drive / polish (13)
- `band_width_profile` `image2d × scalar × scalar → table` GPU: 无 — 对直线单次行程(方向 ``along``)擦出的带，在与带正交的每条线上以亚像素精度读取宽度：用与相邻像素的线性插值求出首次与最后一次越过阈值的位置，其差 × res 即为宽度。返回 ``widths``(逐线，无法读取的线为 NaN)、``centres``(带中心位置 [m]，图的坐标)、``valid``、``median``。前提是只有 1 条带(多条带时得到最外侧之间的宽度)。**Raises** ValueError：图像检查，res ≤ 0，along 不是 x / y，阈值非有限。 · 示例: `poc_polish_wipe_measure`
- `coat_image` `image2d × scalar → image2d` GPU: 无 — 去除深度图 → 从正上方拍摄的残留污垢(膜)板的图像 [0, 1]。残留厚度 t = clip(h0 − h, 0, h0)，亮度 I = bare · exp(−τ t/h0)(Beer–Lambert，τ = ``optical_depth`` 为整个膜的光学厚度)+ 高斯噪声 ``noise``。**Raises** ValueError：图不是 2-D 或非有限，coat ≤ 0，τ ≤ 0，bare 在 (0, 1] 之外，noise < 0。 · 示例: `poc_polish_wipe_measure`
- `coat_thickness_from_image` `image2d × scalar → image2d` GPU: 仅在链中(许可列表) — :func:`coat_image` 的逆运算：t = h0 ln(bare/I)/τ，截断到 [0, h0]。**Raises** ValueError：图像检查，数值检查。 · 示例: `poc_polish_wipe_measure`
- `polish_scene_mjcf` `scalar → any` GPU: 无 — 在平板(z = 0 平面)上用 x、y、z 3 个移动关节驱动圆柱工具(半径 ``radius``、厚度 ``thickness``、质量 ``mass``)的 MJCF。z 为位置伺服(增益 ``k_z`` [N/m] = 腕部的压紧弹簧)，x、y 为硬伺服 ``k_xy``。有重力。弹簧的闭式：工具底面落在板上时的法向力 N = m g + k_z (q_surface − q_cmd)(q_surface = 底面到达 z = 0 的关节值)。接触设得较硬(solref 时间常数 = 4 × timestep，solimp 0.99)，使穿透远小于弹簧压缩量(默认的软接触下，质量 0.05 kg、5 N 时穿透 0.7 mm，与腕部弹簧串联后力偏小 6 % —— 实测)。摩擦锥为椭圆锥(elliptic)。在此设置下，硬腕部(20 kN/m)穿透 0.1〜0.36 mm，力偏小 17 %(摩擦为 0 时也一样，实测)。**Raises** ValueError：数值检查。 · 示例: `poc_polish_wipe_measure`
- `preston_coefficient_fit` `image2d × image2d → table` GPU: 无 — 用最小二乘求解 深度图 = k_p × 驻留图(``dwell_map`` = 以 k_p = 1 积分的 ∫ p |v_rel| dt [Pa·m])，返回 Preston 系数：过原点的拟合 ``k_p``，以及带截距的 ``k_p_affine`` / ``offset``、``r2``、``rms_residual``、``n``。未给出 ``mask`` 时取驻留超过最大值 5 % 的像素。**Raises** ValueError：形状不同或非有限，像素少于 3，驻留为 0。 · 示例: `poc_polish_wipe_measure`
- `preston_pressure_kernel` `scalar × scalar × scalar → image2d` GPU: 无 — 在像素中心采样的工具下方压力 [Pa] 窗口(奇数 × 奇数，中心像素为工具中心)。平板：圆内均匀 F/(πa²)；Hertz：p0 √(1 − r²/a²)(``radius`` = 球半径 R，需要 ``estar``)。``normalize=True`` 时缩放使 Σ p · res² = F(消除按像素计数的圆面积误差，以便 FFT 卷积保持体积)。**Raises** ValueError：力、半径或像素不为正，kind 未知，Hertz 缺少 estar，接触半径小于 1 像素。 · 示例: `poc_polish_wipe_measure`
- `preston_removal_map` `matrix × scalar × scalar × scalar → image2d` GPU: 无 — 由轨迹和压紧力积分 Preston 方程 dh/dt = k_p p |v_rel| 得到的去除深度图 [m] (形状 ``shape``，像素 ``res``)。 · 示例: `poc_polish_wipe_measure`
- `preston_track_profile` `signal × scalar × scalar × scalar → signal` GPU: 无 — 长直单次行程(朝 +x 前进)截面的去除深度 h(y) [m] (y = 横向偏差，前进方向左侧为正；形状与 ``y`` 相同)。闭式：平板 2 k_p p √(a² − y²)；Hertz k_p (E*/R)(a² − y²)(a 由力按 Hertz 求得)；旋转平板(需要 ``spin`` = ω、``speed`` = v) (k_p p / v)[c √(b² + ω²c²) + (b²/ω) asinh(ωc/|b|)] (c = √(a² − y²)，b = v − ωy)。|y| ≥ a 时为 0。**Raises** ValueError：数值检查，旋转时缺少速度，Hertz 加旋转(无闭式)。 · 示例: `poc_polish_wipe_measure`
- `raster_wipe_area` `scalar × scalar × scalar × scalar → table` GPU: 无 — 半径为 ``radius`` 的工具画 ``n_strokes`` 条长度为 ``length`` 的平行单次行程(朝 +x，以间距 ``pitch`` 向 +y 排列，每次行程后抬起返回)时，工具接触面积的闭式：(2a + (N − 1) min(s, 2a)) L + N π a² − (N − 1) lens(s)。返回 ``area``、``rect_area``、``disc_union_area``、``lens``、``overlap_saving``(N 条之和 − 面积)、``path``((M, 2)，以 NaN 分隔的轨迹；给出 ``step`` 时每次行程为按该步长排列的点列)。**Raises** ValueError：数值检查，n_strokes < 1，面积溢出，单次行程的点数超过 1e6。 · 示例: `poc_polish_wipe_measure`
- `removal_depth_from_heights` `image2d × image2d → image2d` GPU: 有(许可列表) — 由抛光前后的高度图(须位于同一网格)求出的去除深度 [高度单位，正 = 被去除]。由于重新装夹会改变抛光后图的倾斜和高度，对差值 z_before − z_after 在“未接触区域”(``ref_mask``，未给出时为外周比例 ``frame`` 的边框)上用最小二乘拟合平面并减去。**Raises** ValueError：形状不同、非 2-D 或非有限，参考像素少于 3，frame 在 (0, 0.5) 之外。 · 示例: `poc_polish_wipe_measure`
- `winkler_polish_run` `image2d × scalar × scalar × scalar × scalar × scalar → table` GPU: 有(许可列表) — 以平均压力 ``pressure`` 压住弹性地基(Winkler)垫、以相对速度 ``speed`` 抛光时，表面高度图 ``z`` 的时间演化。每一步由 Σ k_w max(0, z − z_t) = N p̄ 求出垫面高度 z_t(只有接触处承受压力)，再按 Preston 方程 z ← z − k_p v k_w max(0, z − z_t) Δt(显式格式，c Δt ≤ 0.01，c = k_p k_w v)。返回 ``z``(最终)，``n_record`` 个点上的 ``t``、``rms``(相对平均值偏差的 rms，不去除形状)、``mean``、``contact``(接触比例)，``rate_full_contact`` = c(全面接触期间 rms 按 exp(−c t) 衰减 —— 推导所得，本函数不使用)，``dt``，``steps``。**Raises** ValueError：z 检查，数值检查，c Δt > 0.01。 · 示例: `poc_polish_wipe_measure`
- `wipe_band_width` `scalar × scalar × scalar × scalar → table` GPU: 无 — 非旋转工具以一次直线单次行程擦拭厚度为 ``coat`` 的膜时，膜被除净的带宽(闭式)。返回 ``width``(为 0 表示擦不掉)、``half_width``、``force_min``(开始形成带的力)、``centre_depth``(中心的去除深度)、``a``(接触半径)。平板：D = 2 a k_p p，半宽 a √(1 − (h0/D)²)，F_min = π a h0/(2 k_p)。Hertz：D = k_p E* a²/R，半宽 √(a² − h0 R/(k_p E*))，F_min = (4E*/3R)(h0 R/(k_p E*))^{3/2}。与速度无关(不旋转时)。**Raises** ValueError：数值检查。 · 示例: `poc_polish_wipe_measure`
- `wipe_coverage` `image2d × scalar → table` GPU: 有(许可列表) — 从图像读取擦净区域(明亮 = 膜已消失处)的面积。二值化与连通分量用 detect.segment_objects(默认 Otsu)。返回 ``area``(擦净像素 × res² [m²])、``fraction``、``largest_area``、``n_regions``、``mask``、``threshold``(Otsu 阈值，按擦净侧最小值与残留侧最大值的中点估计)，给出 ``coat`` 时还返回 ``residual_at_threshold``(阈值亮度所对应的残留膜厚 —— 读出的带是“去除 ≥ h0 − 该厚度”之处)。**Raises** ValueError：图像检查，res ≤ 0，既无擦净区也无残留区(无法确定阈值)。 · 示例: `poc_polish_wipe_measure`

#### drive / polygrav (2)
- `polyhedron_clip_halfspace` `any × any × any → any` GPU: 无 — 用平面切开闭合网格,把 ``(x − point)·normal ≥ 0`` 一侧作为闭合实体返回 → (vertices, faces)。 · 示例: `itokawa_gravity_tour`
- `polyhedron_gravity` `any × points → table` GPU: 无 — 均匀密度的闭合多面体在观测点产生的引力(Werner & Scheeres 1997 的精确公式)。 · 示例: `itokawa_gravity_tour`

#### drive / puck (26)
- `fivebar_fk` `signal × table → any` GPU: 无 — 正运动学：关节角 (q₁, q₂)(各臂近端连杆相对 x 轴的角度)→ 末端 E。肘 Bᵢ = Aᵢ + l₁(cos qᵢ, sin qᵢ)，E = 圆(B₁, l₂) ∩ 圆(B₂, l₂) 的 "forward"(x 较大的一侧)或 "back"。返回值 ``{"E", "B1", "B2"}``，不相交时为 ``None``。 · 示例: `poc_air_hockey_intercept`
- `fivebar_ik` `signal × table → any` GPU: 无 — 逆运动学：末端 E → (q₁, q₂)。臂 i 的肘 = 圆(Aᵢ, l₁) ∩ 圆(E, l₂)，"out" 为肘在外侧(臂 1 在 −y 侧，臂 2 在 +y 侧)，"in" 则相反。够不到时为 ``None``(fail-closed)。FK∘IK = 恒等的区域即工作空间(:func:`fivebar_workspace`)。 · 示例: `poc_air_hockey_intercept`
- `fivebar_link` `无输入 → table` GPU: 无 — 平面五连杆机构(5 个连杆；2 根 2 连杆臂的末端在 1 点相连)：根部 A₁ = base + (0, −d/2)，A₂ = base + (0, +d/2)，近端 l₁、远端 l₂，前方 = +x。数值为**假定**(尚未读到 IROS 2024 实机尺寸的原文)。返回值为 dict(``table`` sort)。 · 示例: `poc_air_hockey_intercept`
- `fivebar_reach_interval` `table × scalar → table` GPU: 无 — 防守线 x = x_line 上可达的 y 区间(按网格，含 FK∘IK 往返)。``{"y_lo","y_hi","ok"}``。 · 示例: `poc_air_hockey_intercept`
- `fivebar_trajectory` `signal × table × signal → matrix` GPU: 无 — 规划的关节轨迹 q(t)：从 t_now 起 t_move 期间以恒定角速度运动，到达后停止。(N,2)。 · 示例: `poc_air_hockey_intercept`
- `fivebar_workspace` `table → table` GPU: 无 — 工作空间：网格各点中 IK 可解且 FK∘IK 在 tol 内回到原处的点(只把在分支 out/forward 上不矛盾的点视为"可达")。返回值 ``{"xs","ys","mask","area","x_max","x_min"}``(x_max = 可达的最前方 x)。 · 示例: `poc_air_hockey_intercept`
- `puck_camera` `table → table` GPU: 无 — 从正上方观察的合成相机：以等倍率将球台映射到像素的单应性(仿射)。col = (x + x_half + margin)·s，row = (y_half + margin − y)·s。返回值 ``{"H" world→(col,row), "Hinv", "shape", "px_per_m", "margin", "table"}``。 · 示例: `gallery_drive_ballistics`, `poc_air_hockey_intercept`
- `puck_crossing_point` `table × scalar → any` GPU: 无 — 预测路径首次穿过防守线 x = ``x_line`` 的时刻与位置(闭式：逐区间求解 d(τ)·uₓ = 所需距离)。 · 示例: `poc_air_hockey_intercept`
- `puck_detect` `image2d × table → any` GPU: 无 — :func:`balltrack.ball_detect` 的 facade：从正上方的帧中取出 1 个圆盘，并用单应性映射到球台平面 (x, y) [m]。 · 示例: `poc_air_hockey_intercept`
- `puck_mirror_path` `signal × signal × table × scalar → signal` GPU: 无 — 镜像法(仅限无摩擦、e = kₜ = 1)：返回直线 p₀ + v₀ t 在壁的网格中折返后的位置(第 2 实现，门禁的比对对象)。忽略球门(当作壁)。返回值 = 终点位置 (2,)。 · 示例: `poc_air_hockey_intercept`
- `puck_mu_from_decel` `signal × matrix → table` GPU: 无 — 对沿方向的距离 s(t) 拟合二次式，由 a = 2c₂ 得 μ = −a/g(Coulomb 匀减速)。``{"mu", "a", "v0", "resid_rms"}``。N < 4 时为 ValueError。 · 示例: `poc_air_hockey_intercept`
- `puck_pinhole_camera` `table × scalar × scalar × signal → table` GPU: 无 — 将正上方的针孔相机(位置 (0, 0, h)，朝向 −z，up = +y，MuJoCo 的相机约定)转为单应性：col = W/2 + f x/h，row = H/2 − f y/h，f = (H/2)/tan(fovy/2)。忽略冰球上表面的高度(≈ 0.02 m)(相对 h 的视差略高于 1 %，残差由门禁测量)。``shape`` = (H, W)。返回值与 :func:`puck_camera` 形式相同。 · 示例: `gallery_drive_ballistics`, `poc_air_hockey_intercept`
- `puck_pixel_to_world` `table × matrix → matrix` GPU: 无 — 像素 (col, row) (N,2) → world (N,2)(将逆矩阵传给 :func:`calib.image_to_world_plane`)。 · 示例: `gallery_drive_ballistics`
- `puck_render_frame` `table × signal → image2d` GPU: 无 — 合成 1 帧正上方视图(float (H,W)，0〜1)：白色球台、灰色的壁、深色冰球(1 阶抗锯齿)。 · 示例: `poc_air_hockey_intercept`
- `puck_restitution_from_wall` `signal × matrix × table → table` GPU: 无 — 由在壁上弹跳的轨迹求 e(法向)与 kₜ(切向)：在方向变化最大的帧处分成前后两段，两侧都用 :func:`puck_velocity_estimate` 外推到碰撞时刻。壁取距碰撞点最近的壁。``{"e", "kt", "t_hit", "wall", "n_before", "n_after", "v_in", "v_out"}``。任一侧少于 3 点时为 ValueError。 · 示例: `poc_air_hockey_intercept`
- `puck_scene_mjcf` `table → any` GPU: 无 — 自制的最小 MJCF(Coulomb 版，不需要 mujoco)：有摩擦的平面上的圆柱冰球(自由关节)、4 面壁(箱体)、正上方相机。Challenge 的球台是黏性阻尼，因此要在 MuJoCo 中验证 Coulomb 匀减速请用这个。壁的反弹为软接触，e 需测量。 · 示例: `poc_air_hockey_intercept`
- `puck_slide_predict` `signal × signal × table × scalar → table` GPU: 无 — 以闭式连接冰球的路径：每个区间(壁到壁)方向恒定、匀减速，在壁处调用 :func:`puck_wall_bounce`。 · 示例: `poc_air_hockey_intercept`
- `puck_state_at` `table × signal → table` GPU: 无 — :func:`puck_slide_predict` 路径上时刻 t(标量或 (N,))的位置与速度。终点之后保持终点状态(位置不动，速度为终点值 = 若已停止则为 0)。返回值 ``{"p" (N,2), "v" (N,2)}``。 · 示例: `poc_air_hockey_intercept`
- `puck_stop_distance` `scalar × table → scalar` GPU: 无 — 停止距离 v₀²/(2μg)(与 :func:`ballistics.slide_stop_distance` 公式相同，本函数从 table 取 μ、g)。 · 示例: `poc_air_hockey_intercept`
- `puck_synth_frames` `table × table × signal × signal → table` GPU: 无 — 合成的连续帧与真值：按 fps 对闭式路径(:func:`puck_slide_predict`)采样，并用 :func:`puck_render_frame` 绘制。 · 示例: `poc_air_hockey_intercept`
- `puck_table` `无输入 → table` GPU: 无 — 球台与冰球(puck)的数值(默认值读自 Robot Air Hockey Challenge 的 ``table.xml``，MIT，arXiv 2411.05718)。 · 示例: `gallery_drive_ballistics`, `poc_air_hockey_intercept`
- `puck_track` `any × table → table` GPU: 无 — 帧序列 → 每帧的候选 → :func:`balltrack.ball_track`(用匀速预测连接，超过 ``max_jump_px`` 的丢弃)→ world 坐标。 · 示例: `poc_air_hockey_intercept`
- `puck_velocity_estimate` `signal × matrix × table → table` GPU: 无 — 由 N 个点的位置以最小二乘求速度：固定方向 û 的匀减速模型 p(τ) = p_ref + v_ref τ − ½ μg τ² û(τ = t − t_ref)。 · 示例: `poc_air_hockey_intercept`
- `puck_wall_bounce` `signal × signal × scalar × scalar → table` GPU: 无 — 与壁的碰撞：法向分量 vₙ' = −e vₙ，切向分量 vₜ' = kₜ vₜ(e = 法向恢复系数，kₜ = 切向保持率 = 切向恢复系数)。 · 示例: `poc_air_hockey_intercept`
- `puck_world_to_pixel` `table × matrix → matrix` GPU: 无 — world (N,2) → 像素 (col, row) (N,2)(将 H 传给 :func:`calib.image_to_world_plane`)。 · 示例: `gallery_drive_ballistics`, `poc_air_hockey_intercept`
- `striker_plan` `any × signal × table → table` GPU: 无 — 击球规划(基于规则)：对预测的交点用 IK 求关节角，各伺服以恒定角速度 ≤ ω_max 运动。所需时间 = max|Δq|/ω_max。若在到达交点之前就位则为 feasible。返回值 ``{"feasible","reason","q_target","dq","t_move","t_arrive","t_cross","E"}``，reason ∈ {"ok","no_crossing","unreachable","too_late"}。``crossing`` = :func:`puck_crossing_point` 的返回值(可为 None)。ω_max = 6 rad/s 的默认值为假定。 · 示例: `poc_air_hockey_intercept`

#### drive / pxrd (14)
- `azimuthal_integrate` `image2d × table → table` GPU: 有(许可列表) — 将 2 维探测器图像归约为 2θ 的 1 维剖面(方位角积分，含掩膜与校正)。 · 示例: `poc_pxrd_phase_peel`
- `cif_read` `any → table` GPU: 无 — 读取 CIF(晶体结构的标准格式)，返回展开到晶胞内全部原子的“物相”。 · 示例: `poc_pxrd_phase_peel`
- `cubic_index` `signal × scalar → table` GPU: 无 — 按立方晶系为峰标定指数，确定晶格(P / I / F / diamond)与晶格常数 a [Å]。 · 示例: `poc_pxrd_phase_peel`
- `cubic_prototype` `any × scalar × any → table` GPU: 无 — 由立方晶系原型(``sc``、``bcc``、``fcc``、``diamond``、``rocksalt``、``cscl``、``zincblende``、``fluorite``)构建物相。 · 示例: `poc_pxrd_phase_peel`
- `debye_ring_image` `any × signal × table → table` GPU: 无 — 合成德拜环的 2 维探测器图像(附各物相的贡献)。 · 示例: `poc_pxrd_phase_peel`
- `detector_calibrate` `image2d × signal × table → table` GPU: 无 — 由已知标准样品(如 Si)的衍射环标定探测器的中心、距离与倾斜。 · 示例: `poc_pxrd_phase_peel`
- `detector_two_theta` `any × table → table` GPU: 无 — 探测器各像素的 2θ、方位角 χ 与相对立体角(含倾斜、距离和中心)。 · 示例: `poc_pxrd_phase_peel`
- `diffraction_peaks` `signal × signal → table` GPU: 无 — 从 1 维衍射剖面中拾取峰，用高斯 + 直线的局部拟合给出位置、高度、FWHM 与面积。 · 示例: `poc_pxrd_phase_peel`
- `phase_dictionary` `any × signal × scalar → table` GPU: 无 — 物相参考图谱字典：在 2θ 网格上按物相排列每单位体积分数 1 的 1 维强度。 · 示例: `poc_pxrd_phase_peel`
- `phase_fractions` `signal × signal × table → table` GPU: 无 — 用非负最小二乘(NNLS)求混合物的物相分数(背景用 Chebyshev 多项式同时拟合)。 · 示例: `poc_pxrd_phase_peel`
- `phase_peel` `signal × signal × table → table` GPU: 无 — 从混合物中逐个(每次 1 个)剥离物相(贪心前向选择)。 · 示例: `poc_pxrd_phase_peel`
- `powder_reflections` `table × scalar → table` GPU: 无 — 物相的粉末衍射峰列表：晶面间距 d、Bragg 2θ、多重度、|F|²、强度(含 Lorentz 因子，不含偏振)。 · 示例: `poc_pxrd_phase_peel`
- `scherrer_size` `scalar × scalar × scalar → scalar` GPU: 无 — 用 Scherrer 公式求微晶尺寸 [Å] (``L = K λ / (β cos θ)``)。 · 示例: `poc_pxrd_phase_peel`
- `unexplained_peaks` `table → table` GPU: 无 — 从物相分数拟合的残差中提取字典中任何物相都无法解释的峰(未知物相的线索)。 · 示例: `poc_pxrd_phase_peel`

#### drive / racket (10)
- `aim_velocity` `table → table` GPU: 无 — 从点 p 在时间 T 内到达 target 的初速度。以真空闭式 v = (Δxy/T, (Δz + ½gT²)/T) 为初值，在阻力 + 马格努斯(ω)的运动方程上进行 ``refine`` 次 Gauss–Newton(有限差分)。``{"v", "residual"}``(residual = 到达点的偏差 [m])。 · 示例: `gallery_drive_kendama_racket`, `poc_table_tennis_rally_loop`
- `racket_hit_check` `table → table` GPU: 无 — 球心是否在距拍面 ``radius`` 以内，且在拍板框(宽 × 高 + 半径)之内。``{"hit", "dist", "u", "v"}``(u = 宽度方向、v = 高度方向相对拍板中心的偏移)。 · 示例: `gallery_drive_kendama_racket`
- `racket_impact` `table × table → table` GPU: 无 — 球撞上运动中的球拍(法线 n，速度 v_r)：在球拍坐标系中以相对速度调用 :func:`ballistics.bounce` → 变换回去。返回值 = 与 bounce 相同 + ``"v_rel_in"``。n 朝向球的一侧(球沿与 n 相反的方向接近)。 · 示例: `poc_table_tennis_rally_loop`
- `racket_move` `table → any` GPU: 无 — 将球拍移向 target(带速度、加速度上限的 bang-bang：根据可停止的距离减速)。返回值 (pos, vel)。 · 示例: `gallery_drive_kendama_racket`
- `racket_params` `无输入 → table` GPU: 无 — 球拍参数表：拍板的宽、高 [m]，胶皮的恢复系数 e 与摩擦系数 μ，运动上限(速度 v_max [m/s]，加速度 a_max [m/s²])。 · 示例: `gallery_drive_kendama_racket`, `poc_ball_bounce`, `poc_table_tennis_rally_loop`
- `racket_plan` `table × table → table` GPU: 无 — 产生期望 v_out 的球拍法线 n 与速度 v_r(法线方向)。以摩擦为 0 的闭式 n ∝ v_out − v_in、v_r·n = |Δv|/(1+e) + v_in·n 为初值，用实际碰撞(含摩擦、旋转)迭代 ``refine`` 次。返回值 ``{"normal", "v_racket", "v_out_actual", "omega_out", "residual"}``。Δv ≈ 0 时为 ValueError。 · 示例: `poc_table_tennis_rally_loop`
- `rally_simulate` `table × table × table → table` GPU: 无 — 2 支球拍(位于 x = −x_r 与 +x_r，拍面朝向对方)相互对打。 · 示例: `poc_ball_bounce`, `poc_table_tennis_rally_loop`
- `shot_is_legal` `table × table × table → table` GPU: 无 — 用真实物理预测击球 (p, v, ω)，判定其是否越过球网、只在对方台面落 1 次，并以对方击球面 x = ∓x_r 处可击打的高度到达。``{"legal", "reason", "p_arrive", "t_arrive"}``。 · 示例: `gallery_drive_kendama_racket`
- `strategy_attacker` `table → table` GPU: 无 — 旋转每 3 球为 flat，其余为 topspin。 旋转的意图也交替变化。``ctx`` = {"opp_pos" (3,), "shot_index", "tp"}。返回值 {"target" (x, y), "T", "spin"}。 · 示例: `gallery_drive_kendama_racket`
- `strategy_feeder` `table → table` GPU: 无 — 回球到与上一次接近但略有偏移的位置(对手容易接的球)：将自己上一次的瞄准点按 ±step 的均匀随机数移动，并限制在球台内侧(距边缘 12 cm)。滞空时间为较慢的 0.42 s。 · 示例: `gallery_drive_kendama_racket`

#### drive / roadjp (7)
- `add_sign` `table → scalar` GPU: 无 — 竖立路侧式交通标志：立柱(圆柱，灰色，标签 6)+ 标志板(下端 = ``mount_height``，默认 1.8 m，标签 4)。 · 示例: `poc_driving_school`, `poc_world_terrain`
- `add_signal_jp` `table → scalar` GPU: 无 — 竖立日本式信号灯：立柱 + 水平悬臂 + 灯具(横置 3 灯，显示面朝向沿 yaw 方向驶来的车辆)。 · 示例: `gallery_drive_japan_roads`
- `plate_mesh_from_image` `rgba → table` GPU: 无 — 将 RGBA 图像转换为带面颜色的薄板网格(mesh)。 · 示例: `gallery_drive_japan_roads`
- `sign_image` `无输入 → rgba` GPU: 无 — 以 RGBA float (H, W, 4) ∈ [0,1] 返回交通标志的图像(标志板外 = alpha 0)。宽 = ``size_px``，高按形状的比例。 · 示例: `gallery_drive_japan_roads`
- `sign_mesh` `无输入 → table` GPU: 无 — :func:`sign_image` + :func:`sign_params` + :func:`plate_mesh_from_image`。在返回值中加入 ``width``、``height``、``params``。 · 示例: `gallery_drive_japan_roads`
- `sign_params` `无输入 → table` GPU: 无 — 返回交通标志 ``kind`` 的形状、尺寸和颜色(公开值，需以一手资料核实)。 · 示例: `gallery_drive_japan_roads`
- `signal_jp_mesh` `无输入 → table` GPU: 无 — 横置的车辆用信号灯具(日本式)。原点 = 灯具底面中心，显示面朝向 −x。 · 示例: `gallery_drive_japan_roads`

#### drive / roverslip (15)
- `bekker_pressure` `signal × scalar × any → signal` GPU: 无 — Bekker 压力–沉陷关系 ``p = (k_c / b + k_φ) zⁿ`` [kPa]。``sinkage`` [m] 为标量或数组(≥ 0)，``width`` = b [m]。 · 示例: `gallery_drive_soil_tactile`
- `bekker_wheel_sinkage` `scalar × table × any → scalar` GPU: 无 — Bekker 刚性车轮沉陷的近似式 [m]。以抛物线 ``z(x) = z₀ − x²/D`` 近似接地，不计剪切。 · 示例: `poc_rover_slip_risk_path`
- `cvar_cost_map` `image2d × scalar × any → table` GPU: 无 — 由数字高程(DTM)构建 8 邻域各边的所需时间 [s]，并按边的坡度(带行进方向符号)下滑移的 CVaR_α 折算。 · 示例: `poc_rover_slip_risk_path`
- `ground_shift_track` `any → table` GPU: 无 — 从俯视地面的相机帧序列中，用加窗互相关(整数)和平移 Lucas–Kanade(亚像素)测量相邻帧之间的平移并累积。 · 示例: `poc_rover_slip_risk_path`
- `odometry_slip` `any × signal × scalar → table` GPU: 无 — 由视觉里程计的位置序列与车轮累积转角求实际滑移率 ``s = 1 − Δx / (r Δφ)``。 · 示例: `poc_rover_slip_risk_path`
- `path_slip_risk` `matrix × image2d × scalar × table → table` GPU: 无 — 逐边评估路径：坡度、平均滑移、CVaR_α 滑移、超过 ``s_max`` 的概率(高斯过程用正态分布，分位数回归用分位曲线插值)，以及平均滑移下与 CVaR 下的所需时间。 · 示例: `poc_rover_slip_risk_path`
- `risk_aware_path` `table × any × any → table` GPU: 无 — 在 :func:`cvar_cost_map` 的边所需时间上进行 8 邻域 Dijkstra(有向边 —— 上坡与下坡不同)。 · 示例: `poc_rover_slip_risk_path`
- `slip_cvar` `table × signal × scalar → signal` GPU: 无 — 滑移率的 CVaR_α(上侧 1 − α 尾部的条件期望)。``sign = −1`` 时为 −s 的 CVaR(下坡空走、侧滑的大小)。 · 示例: `gallery_drive_soil_tactile`
- `slip_gp_fit` `signal × signal → table` GPU: 无 — 坡角 → 滑移率的高斯过程(RBF 核 + 均匀的观测噪声)。超参数通过对数边际似然的网格搜索确定。 · 示例: `gallery_drive_soil_tactile`, `poc_rover_slip_risk_path`
- `slip_predict` `table × signal → table` GPU: 无 — 滑移率的预测与双侧 ``level`` 区间带。高斯过程为观测的预测分布(潜在方差 + 噪声)，分位数回归则为曲线本身。 · 示例: `gallery_drive_soil_tactile`, `poc_rover_slip_risk_path`
- `slip_quantile_fit` `signal × signal → table` GPU: 无 — 坡角 → 滑移率的分位数回归(分段线性基，用 IRLS 求解 pinball 损失，对 2 阶差分加弱惩罚)。 · 示例: `poc_rover_slip_risk_path`
- `slope_slip_curve` `signal × table × any × scalar → table` GPU: 无 — 对每个坡角(度，上坡为正)，在支撑车体重量的同时以牵引力平衡沿坡方向重力分量的稳态滑移率。 · 示例: `poc_rover_slip_risk_path`
- `wheel_forces` `signal × signal × table × any → table` GPU: 无 — 在沉陷 z [m] 与滑移率 s 下刚性车轮从土壤受到的力(Wong–Reece 应力分布的数值积分)。 · 示例: `poc_rover_slip_risk_path`
- `wheel_sinkage` `signal × table × any → signal` GPU: 无 — 1 个车轮在滑移率 ``slip`` 下支撑垂直载荷 ``load`` [N] 时的沉陷 z [m] (对 F_z(z, s) = load 用二分法)。 · 示例: `poc_rover_slip_risk_path`
- `wheel_traction_curve` `scalar × table × any → table` GPU: 无 — 保持 1 个车轮的载荷 ``load`` [N] 不变时，各滑移率下的沉陷、牵引力与扭矩(牵引力–滑移曲线)。 · 示例: `poc_rover_slip_risk_path`

#### drive / rss (10)
- `rss_lateral` `table → scalar` GPU: 无 — 横向(论文 Lemma lateral / lib ``calculateSafeLateralDistance``)的最小安全距离 [m]。c_1 在左侧。 · 示例: `gallery_drive_lateral_env`, `poc_ttc_rss`
- `rss_lateral_check` `table → table` GPU: 无 — 横向间距 d_lat(左车右侧面 ~ 右车左侧面，≥ 0)是否安全。Returns 与 ``rss_longitudinal_check`` 形式相同。 · 示例: `poc_ttc_rss`
- `rss_longitudinal_check` `table → table` GPU: 无 — 同向的纵向间距 d(跟随车前端 ~ 前车后端，≥ 0)是否安全。 · 示例: `poc_ttc_rss`
- `rss_longitudinal_opposite` `table → scalar` GPU: 无 — 对向(论文 Lemma two_way / lib ``calculateSafeLongitudinalDistanceOppositeDirection``)的最小安全距离 [m]。 · 示例: `poc_ttc_rss`
- `rss_longitudinal_same` `table → scalar` GPU: 无 — 同向(论文 Lemma 2 / lib ``calculateSafeLongitudinalDistanceSameDirection``)的最小安全距离 [m]。 · 示例: `poc_ttc_rss`
- `rss_params` `无输入 → table` GPU: 无 — 生成 RSS 参数 dict(默认 = ad-rss-lib 的公开表，ρ 为 ego 的 1 s)。 · 示例: `gallery_drive_lateral_env`, `poc_ttc_rss`
- `rss_stopping_distance` `无输入 → scalar` GPU: 无 — 按 ad-rss-lib 的 stated braking pattern 得到的**带符号位置偏移**(纵向、横向共用的 1 个公式)。 · 示例: `poc_driving_longitudinal`
- `rss_worst_case_gap` `table → table` GPU: 无 — 按时间追踪同向的最坏情况(论文 Definition 4)。 · 示例: `poc_ttc_rss`
- `rss_worst_case_gap_lateral` `table → table` GPU: 无 — 横向的最坏情况：ρ 期间以 ``lat_accel_max`` 相互靠近加速 → 以 ``lat_brake_min`` 减速至横向速度为 0。 · 示例: `gallery_drive_lateral_env`
- `rss_worst_case_gap_opposite` `table → table` GPU: 无 — 对向的最坏情况：两车在 ρ 期间以 ``accel_max`` 加速 → c_1 以 ``brake_min_correct``、c_2 以 ``brake_min`` 停止。 · 示例: `poc_ttc_rss`

#### drive / scoop (15)
- `pour_scene_mjcf` `scalar × scalar × scalar × scalar → table` GPU: 无 — 在开口槽(底长 ``L``、宽 ``B``、后壁与侧壁高 ``wall``)中按网格填充刚体球至深度 ``h0`` 的场景 MJCF(**无需 mujoco**)。槽是 mocap body(``name="trough"``，原点 = 口部底面的边缘，高度 ``lip_height``)，由 :func:`scoop_mujoco_pour` 每步写入 ``mocap_quat`` 使其向口部朝下的方向(绕 y 轴 −θ)旋转。底面粗糙(滑动摩擦 ``floor_mu``，底层不会随底面整体滑出 —— 作用与 granular 的粗糙台相同)，侧壁为 ``wall_mu``。底面的口部一侧(x < 0)敞开，洒出的球会落到地面(高度 0)。返回：``xml``、``positions``、``info``(L, B, h0, wall, radius, lip_height, mass_each, n, timestep, A_fill = L·h0)。**Raises** ``ValueError``：``h0 ≥ wall`` / ``contact_tc < 2 timestep`` / 连 1 层球都放不下 / 拼写错误。 · 示例: `poc_powder_scoop_pour`
- `revolution_volume_side` `image2d × scalar → table` GPU: 有(许可列表) — 由 1 张侧视图像在假定轴对称下求体积 —— Pappus 形式 ``V = π Σ |x − x_axis| c(x, z) pitch³``(``c`` = 覆盖率，``x`` = 像素中心所在列)。 · 示例: `poc_powder_scoop_pour`
- `scoop_count` `scalar × scalar × scalar → table` GPU: 无 — 由体积和填充率求颗粒数 ``N = V ν / ((4/3) π r³)``(给出 ``density`` 时还求质量 ``N m_p`` 和堆积密度 ``ν ρ_p``)。 · 示例: `poc_powder_scoop_pour`
- `scoop_image_limit` `scalar × scalar × scalar × scalar → table` GPU: 无 — 用侧视图像称量堆尖勺子时的不确定度参考，以及“图像是否够用，还是要用秤”(**基于规则**，仅供参考)。 · 示例: `poc_powder_scoop_pour`
- `scoop_scene_mjcf` `scalar × scalar → table` GPU: 无 — 用薄板瓦片铺成球冠碗(缘半径 ``a``、深度 ``h``、缘高 ``rim_height``)，并在碗内按网格堆放 ``n_spheres`` 个刚体球、从正上方释放的场景 MJCF 字符串(**无需 mujoco**，登记于台账)。 · 示例: `poc_powder_scoop_pour`
- `scoop_synth_side` `scalar × scalar → table` GPU: 无 — 合成球冠碗中粉体的侧视覆盖率(轴对称，真值为闭式)。 · 示例: `poc_powder_scoop_pour`
- `scoop_volume_read` `image2d × scalar × scalar × scalar × scalar → table` GPU: 无 — 从勺子的侧视图像读取舀取的体积。 · 示例: `poc_powder_scoop_pour`
- `spoon_bowl_volume` `scalar × scalar → table` GPU: 无 — 球冠碗(缘半径 ``a``、深度 ``h``)的闭式 —— 平勺、部分装填与堆尖。 · 示例: `poc_powder_scoop_pour`
- `stream_areal_density` `image2d × scalar → image2d` GPU: 无 — 由覆盖率按 Boolean 模型反解颗粒中心的面密度 [个 / px²]：``n = −ln(1 − c) / (π r²)``。 · 示例: `gallery_drive_soil_tactile`
- `stream_flux_read` `any × scalar × scalar → table` GPU: 无 — 从流的帧序列读取流量 [个/s] (及质量流量) —— 速度用 PIV(``pivops.piv_cross_correlate`` 全部帧对的中位数)，颗粒线密度 ``λ`` 为对时间平均覆盖率做 Boolean 模型反解(:func:`stream_areal_density`)后横向积分所得，流量为 ``λ v``。 · 示例: `poc_powder_scoop_pour`
- `stream_synth` `scalar × scalar × scalar → table` GPU: 无 — 合成从口部落下的粉体流(侧视的细带)的覆盖率帧序列。 · 示例: `poc_powder_scoop_pour`
- `tilt_pour_rate` `scalar × scalar × scalar × scalar × scalar × scalar × scalar → table` GPU: 无 — 以角速度 ω 倾斜 :func:`tilt_wedge_retained` 的容器时的准静态流量 ``W = ρ_b B (−dA/dθ) ω`` [kg/s] (由供给决定的流量：只要倾斜得比口部的通过能力慢，流量就由倾斜速度决定)。 · 示例: `poc_powder_scoop_pour`
- `tilt_wedge_retained` `scalar × scalar × scalar × scalar → table` GPU: 无 — 在口部无壁的容器(底长 ``L``，后壁垂直于底面且足够高)中以深度 ``h0`` 平铺的粉体，口部朝下倾斜 θ 时残留的量(2 维截面，准静态，**自行推导**)。 · 示例: `poc_powder_scoop_pour`
- `tilted_surface_read` `image2d × scalar × scalar × scalar × scalar → table` GPU: 无 — 从倾斜容器的侧视图像(覆盖率)读取容器内残留粉体的截面积及后部平坦面的高度。 · 示例: `poc_powder_scoop_pour`
- `two_view_volume` `image2d × image2d × scalar → table` GPU: 无 — 由 2 个正交方向的侧视图像求体积 —— 以每行的 2 条弦 ``W_a``、``W_b`` 为轴的椭圆之和 ``V = Σ f π (W_a/2)(W_b/2) pitch³``。 · 示例: `poc_powder_scoop_pour`

#### drive / swarmflow (12)
- `obstacle_fit_doublet` `table → table` GPU: 无 — 将圆柱绕流的势流 u − i v = U (1 − R²/(z − z_c)²) 拟合到速度场(实现 2，2 维非线性最小二乘)。 · 示例: `poc_swarm_obstacle_from_flow`
- `potential_flow_cylinder` `signal × signal × any → table` GPU: 有(许可列表) — 圆柱绕流的势流(闭式)。u − i v = U (1 − R²/(z − z_c)²)，圆内为 NaN。 · 示例: `poc_swarm_obstacle_from_flow`
- `ritter_dam_break` `signal × scalar × scalar → table` GPU: 仅在链中(许可列表) — Ritter 溃坝解(浅水方程，干河床，坝位于 x = 0，水位于 x < 0)。 · 示例: `poc_swarm_obstacle_from_flow`
- `sph_dam_break_1d` `无输入 → table` GPU: 无 — 用 1 维 SPH 浅水方程求解溃坝(干河床)(作为打开群体闸门时扩散的模型)。 · 示例: `poc_swarm_obstacle_from_flow`
- `sph_density_pressure` `matrix × scalar → table` GPU: 无 — 点集的 SPH 密度 ρ_i = Σ_j m W(|x_i − x_j|, h)(包含自身)以及弱可压缩状态方程 p = c² (ρ − ρ₀)。 · 示例: `gallery_drive_soil_tactile`
- `sph_kernel` `signal × scalar → signal` GPU: 有(许可列表) — 3 次样条核 W(r, h)(M4，支撑半径 2h)。``derivative=True`` 时为 dW/dr(沿 r 方向的导数，≤ 0)。 · 示例: `poc_swarm_obstacle_from_flow`
- `stagnation_from_centerline` `table → table` GPU: 无 — 将中心线上的亏损线性化，读取上游的撞击点(驻点)、障碍物中心与半径(实现 1，只用上游的点)。 · 示例: `poc_swarm_obstacle_from_flow`
- `swarm_field_from_piv` `any × scalar × scalar → table` GPU: 无 — 俯视帧序列 → 相邻帧之间的互相关 PIV(pivops.piv_cross_correlate)→ 所有帧对取平均 → 世界的速度场。 · 示例: `poc_swarm_obstacle_from_flow`
- `swarm_field_from_tracks` `any × scalar × scalar → table` GPU: 无 — 俯视帧序列 → 检测个体(blob2d 的连通分量 + 亮度质心)→ 与相邻帧按互为最近邻连接 → 用 SPH 核将速度映射到网格。 · 示例: `poc_swarm_obstacle_from_flow`
- `swarm_render_overhead` `matrix × any × scalar → image2d` GPU: 无 — 个体位置 → 俯视的 1 帧(高斯亮点，直径 = 标准差的 2 倍 = PIV 惯例，与 pivops 相同)。 · 示例: `poc_swarm_obstacle_from_flow`
- `swarm_simulate` `无输入 → table` GPU: 无 — 在带障碍物的周期性流道中流动的群体(个体按 SPH 弱可压缩流体运动)。障碍物对个体只起“会撞上的墙”的作用。 · 示例: `poc_swarm_obstacle_from_flow`
- `velocity_deficit_map` `table → table` GPU: 无 — 速度场 → 相对自由流的亏损 1 − u/U、横向偏摆 v/U、速率亏损 1 − |v|/U。U 由用户给出，或取上游端 15 % 处 u 的中位数。 · 示例: `poc_swarm_obstacle_from_flow`

#### drive / tacdome (12)
- `contact_patch_radius` `image2d × scalar → table` GPU: 有(许可列表) — 从接触图像(:func:`dome_contact_image` 的类型)读取接触半径。通过覆盖率的线性和(面积法)利用到边缘的亚像素。 · 示例: `poc_tacdome_large_deformation`
- `dome_contact_image` `scalar × scalar → image2d` GPU: 无 — 从穹顶内侧拍摄的接触图像(接触区域明亮，受抑全反射式照明的理想化)。(n, n) 的 float。 · 示例: `poc_tacdome_large_deformation`
- `hertz_small_strain_error` `signal × scalar → table` GPU: 无 — 将小变形线性解(Hertz)用于大变形时的误差 [%] (仅由 d 决定，与 L、尺寸、弹性模量无关)。 · 示例: `poc_tacdome_large_deformation`
- `large_deformation_contact` `any × scalar × table → table` GPU: 无 — 由压入量 δ(标量或数组)求大变形的力与接触半径(式 2、4)，以及与相同 δ 下线性解(Hertz)的差。 · 示例: `poc_tacdome_large_deformation`
- `large_deformation_inverse` `scalar × scalar × table → table` GPU: 无 — 由测得的接触半径 a 反求压入量与力(对 d 求解式 4，再由式 2 求力)。传感器读出的核心。 · 示例: `poc_tacdome_large_deformation`
- `largedef_c1_coefficient` `scalar → scalar` GPU: 无 — 式 (3) 的 1 次系数 c₁：``"derived"`` = 2n/(1+n)(推导)，``"printed"`` = (4+2n)/(1+n)(原文的印刷)，``"memo"`` = 2/(1+n)。 · 示例: `gallery_drive_soil_tactile`
- `largedef_correction` `signal × scalar → signal` GPU: 无 — 大变形修正 κₙ(d) = [1 − c₁·d + n/(2+n)·d²]/(1 − d)²(式 3，c₁ 由 :func:`largedef_c1_coefficient` 给出)。F = κₙ·F_L。 · 示例: `poc_tacdome_large_deformation`
- `largedef_radius_ratio` `signal × scalar → signal` GPU: 无 — 大变形接触半径之比 a/a_L(式 4)= (1/p)·B_d(1/p, 3/2)·d^{−1/p}/√(1 − d) = ∫₀¹ √((1 − d·uᵖ)/(1 − d)) du。 · 示例: `poc_tacdome_large_deformation`
- `largedef_universal_correction` `signal → signal` GPU: 无 — 普适形式的修正 κ(d) = (1 − k·d)⁻¹(式 6，k = 10/9)。**Raises** ``ValueError``：d 在 [0, 1) 之外、k·d ≥ 1、k ≤ 0。 · 示例: `poc_tacdome_large_deformation`
- `mdr_spring_bed` `scalar × scalar × table → table` GPU: 无 — 用中点法则直接积分 1D 非线性弹簧列(闭式 :func:`largedef_correction` / :func:`largedef_radius_ratio` 的第二实现)。 · 示例: `poc_tacdome_large_deformation`
- `neohookean_cylinder_exact` `signal → table` GPU: 无 — 不可压缩 neo-Hookean 圆柱无摩擦单轴压缩的精确解(连续介质教科书的结果，与模型独立)。 · 示例: `poc_tacdome_large_deformation`
- `powerlaw_linear_contact` `text × scalar × scalar → table` GPU: 无 — 用平板压幂律截面 f(r) = c·rᵖ 的线性解(式 1、5)：F_L = C·δⁿ，a_L = D·δ^{1/p}，n = 1 + 1/p。 · 示例: `poc_tacdome_large_deformation`

#### drive / tacscalib (10)
- `calib_pack_load` `text × scalar × scalar → table` GPU: 无 — 标定包(npz)→ dict。必需键为 ``f0``(背景 (H, W, 3) uint8)、``imgs``((N, H, W, 3))、``touch_center``((N, 2) = (列 x, 行 y))、``touch_radius``((N,) px)；中心重排为 (行, 列) 并以 ``centers`` 返回。 · 示例: `poc_tacscalib_sphere_lut`
- `field_position_sweep` `matrix × signal × any → table` GPU: 无 — 误差的位置依赖：将各图像的接触中心 (行, 列) 与误差(中位数等)按到图像中心的距离排列，返回最小二乘斜率 [误差 / 100 px] 与 Spearman 秩相关(并列取平均秩)(仅用 numpy)。返回：``dist_px``、``err``、``slope_per_100px``、``intercept``、``spearman``、``n``。**Raises** ``ValueError``：少于 3 组 / 形状不一致 / 非有限 / image_shape 的形状。 · 示例: `poc_tacscalib_sphere_lut`
- `gradient_lut_build` `matrix × matrix → table` GPU: 无 — example-based 梯度 LUT：将法线的(倾角 θ，方位 φ)划分为 bins × bins，在每个 bin 中存入落入其中的像素 RGB 的**平均值**(用 ``np.add.at`` 把重复的下标也全部累加)。``rgb_rows`` (P, 3)、``normal_rows`` (P, 3)。 · 示例: `poc_tacscalib_sphere_lut`
- `gradient_lut_invert` `rgb × table × image2d → normalmap` GPU: 无 — RGB (H, W, 3) → 法线 (H, W, 3)：在非空 bin(count ≥ ``min_count``)中取颜色最接近者的中心法线。位置相关版的表(向 :func:`gradient_lut_build` 传入 positions 所得)先按像素位置预测各 bin 的颜色，再进行比较。 · 示例: `poc_tacscalib_sphere_lut`
- `lights_fit_from_sphere` `rgb × normalmap × image2d → table` GPU: 仅在链中(许可列表) — 由背景差分图像(1 张或序列)与已知法线，用最小二乘求解逐通道的线性 Lambertian 模型。 · 示例: `poc_tacscalib_sphere_lut`
- `membrane_predict_rgb` `normalmap × table → rgb` GPU: 仅在链中(许可列表) — 法线 (H, W, 3) + :func:`lights_fit_from_sphere` 的结果 → 背景差分 RGB 的预测 (H, W, 3)(线性，不裁剪)。order 2 的结果按像素生成 a(x, y)、L(x, y)(图像尺寸须与标定时相同)。**Raises** ``ValueError``：法线形状 / order 2 时图像尺寸不同。 · 示例: `poc_tacscalib_sphere_lut`
- `normal_error_map` `normalmap × normalmap → image2d` GPU: 有(许可列表) — 2 个法线场逐像素的夹角 [度] = atan2(|a × b|, a · b)(不归一化 —— 长度在 atan2 的比值中消去)。acos(a · b) 在单位向量彼此接近时存在舍入下限(把 1e-7° 答成 1e-4°)，因此不使用。**Raises** ``ValueError``：形状不同 / 最后一个轴不是 3。 · 示例: `poc_tacscalib_sphere_lut`
- `poly_lut_invert` `rgb × table × image2d → normalmap` GPU: 无 — 适配器：将外部的**位置相关**多项式 LUT(``bins`` 与 ``grad_r`` / ``grad_g`` / ``grad_b`` = (bins, bins, 6)；每个 bin 用 6 个系数 [x², y², xy, x, y, 1]、x = 列、y = 行**直接以像素为单位**表示背景差分各通道的格式)送入与 :func:`gradient_lut_invert` 相同的反查(相同的 bin 划分、相同的粗 → 细)。``rgb`` 是经过与外部流程相同背景处理的差分。外部表的所有 bin 均已填满，因此使用全部 bin。**Raises** ``ValueError``：缺少键 / 系数形状不是 (bins, bins, 6) / 非有限。 · 示例: `poc_tacscalib_sphere_lut`
- `sphere_cap_height` `any × any × scalar × scalar × scalar → table` GPU: 无 — 几何压入(无弹性边缘过渡)的真实高度：接触圆内 h(r) = −(√(R² − r²) − √(R² − a²))，圆外为 0(a 取 min(a, R))。 · 示例: `poc_tacscalib_sphere_lut`
- `sphere_normals_known` `any × any × scalar × scalar → table` GPU: 无 — 已知球体压入：在接触圆(中心 ``centre`` = (行, 列)，半径 ``a_px``)内以闭式返回法线。 · 示例: `poc_tacscalib_sphere_lut`

#### drive / tacsim (15)
- `combined_modulus` `scalar × scalar → scalar` GPU: 无 — 复合弹性模量 E*：1/E* = (1 − ν1²)/E1 + (1 − ν2²)/E2(Johnson 1985 式 4.9)。``E2=None`` 表示刚体压头(第 2 项为 0)。 · 示例: `poc_knife_tactile_toughness`, `poc_tacsim_elastic_membrane`, `poc_tacsim_marker_shear`, `poc_tactile_dipole_torque`
- `contact_radius_fit` `normalmap × matrix × matrix × scalar × scalar → table` GPU: 无 — 将 Hertz 斜率模型 dh/dr(r; a) 以 1 个参数 a 拟合到法线场的**径向斜率分布**，读取接触半径。 · 示例: `poc_peg_insertion_tactile`, `poc_tacsim_elastic_membrane`
- `contact_radius_fit_pixelwise` `normalmap × matrix × matrix × scalar × scalar → table` GPU: 无 — 将 Hertz 斜率模型 dh/dr(r; a) 以连续的 a 拟合到**逐像素**的径向斜率，读取接触半径(不使用分箱的 :func:`contact_radius_fit` 版本；``a0`` 为其粗略值)。 · 示例: `poc_peg_insertion_tactile`
- `contact_radius_ring` `image2d × scalar → table` GPU: 无 — 从高度场**无模型**读取接触半径 a：接触边缘 r = a 是径向斜率 |∂h/∂r| 最大的圆环(Hertz 中内侧按 r/R 增大，外侧按 √ 急剧下降，形成尖点)。沿方位角方向 ``n_az`` 条径向线以 ``step_px`` 步长双线性插值 |∇h|，用抛物线插值将各线的峰值细化到亚像素 → 对 72 个点调用 :func:`measure.fit_circle`(第 2 实现)并取半径的中位数。 · 示例: `poc_tacscalib_sphere_lut`, `poc_tacsim_elastic_membrane`
- `hertz_cylinder` `scalar × scalar × scalar → table` GPU: 无 — 圆柱(半径 R)以线载荷 F/L 压在弹性半空间上的线接触(Johnson 1985 §4.2)：接触半宽 b = √(4(F/L)R/(πE*))，p0 = 2(F/L)/(πb)。 · 示例: `poc_tacsim_elastic_membrane`
- `hertz_force` `scalar × scalar → scalar` GPU: 无 — Hertz 的反算：由接触半径 a 或压入量 δ 中的任意一个求载荷 F。F = 4E*a³/(3R) = (4/3) E* √R δ^{3/2}。 · 示例: `poc_peg_insertion_tactile`, `poc_tacdome_large_deformation`, `poc_tacsim_elastic_membrane`
- `hertz_pressure` `matrix × scalar × scalar → matrix` GPU: 无 — Hertz 接触压力 p(r) = p0 √(1 − r²/a²)(r < a)，外部为 0。与 r 同形状。**Raises** ``ValueError``：a, p0 ≤ 0。 · 示例: `poc_tacsim_elastic_membrane`, `poc_tacsim_marker_shear`, `poc_tactile_dipole_torque`
- `hertz_sphere` `scalar × scalar × scalar → table` GPU: 无 — 刚体球(半径 R)以载荷 F 压入弹性半空间(复合弹性模量 E*)的 Hertz 接触闭式(Johnson 1985 §3)。 · 示例: `poc_knife_tactile_toughness`, `poc_peg_insertion_tactile`, `poc_tacdome_large_deformation`, `poc_tacsim_elastic_membrane`, `poc_tacsim_marker_shear`, `poc_tactile_dipole_torque`
- `hertz_surface_uz` `matrix × scalar × scalar × scalar → matrix` GPU: 有(许可列表) — Hertz 球接触中半空间表面的法向位移 ū_z(r)(下沉量 ≥ 0，与 r 同形状的数组)。 · 示例: `poc_tacsim_elastic_membrane`, `poc_tactile_dipole_torque`
- `membrane_delta_from_normals` `normalmap × matrix × matrix × scalar → scalar` GPU: 无 — 由法线场求中心沉陷 δ：将径向斜率 s̄(r) 从中心到窗口边缘做 1D 积分(∫ s̄ dr = ū_z(0) − ū_z(r_max))，``tail="boussinesq"`` 时由远场 ū_z ≈ C/r(点载荷的 Boussinesq 解，Johnson §3.2)加上剩余尾部 ū_z(r_max) = r_max · s̄(r_max)(取窗口边缘最后 3 个分箱的中位数)。``tail="none"`` 不加尾部(直接返回有限窗口的低估值 —— 用于测量误差的大小)。 · 示例: `poc_tacsim_elastic_membrane`
- `membrane_indent_shape` `text × scalar → table` GPU: 无 — 以**几何贴合**生成已知形状刚体压入 ``depth`` 深度后的凝胶膜高度场：h = −max(0, depth − z_ind(x, y))。 · 示例: `poc_tacsim_elastic_membrane`
- `membrane_indent_sphere` `table → table` GPU: 无 — 球压入时凝胶膜的高度场 h(x, y) = −ū_z(r) [m] (来自 :func:`hertz_sphere` 的参数表)与解析法线。 · 示例: `poc_knife_tactile_toughness`, `poc_tacsim_elastic_membrane`, `poc_tacsim_marker_shear`
- `membrane_lights` `scalar → matrix` GPU: 无 — 多方向彩色照明的单位方向向量 (N, 3)(第 k 行为颜色通道 k 的光源，默认为方位角 90/210/330°、仰角 55° 的 3 盏灯)。 · 示例: `poc_tacsim_elastic_membrane`, `poc_tacsim_marker_shear`, `poc_tactile_dipole_torque`
- `membrane_recover` `rgb × matrix × scalar → table` GPU: 有(许可列表) — 视触觉 RGB (H, W, 3) → 将 3 个通道视为 3 个光源下的图像，用 :func:`photometric.photometric_stereo`(lit_only)求法线 → 用 :func:`photometric.integrate_normals`(Frankot-Chellappa)求高度(像素单位 × pitch = m)。 · 示例: `poc_peg_insertion_tactile`, `poc_tacsim_elastic_membrane`
- `membrane_render_rgb` `normalmap × matrix → rgb` GPU: 无 — 法线场 (H, W, 3) + 光源 (3, 3) → 视触觉传感器风格的 RGB (H, W, 3) float。通道 k = 光源 k 的 Lambertian 图像 albedo·(max(N·L_k, 0) + ambient)(调用 3 次 :func:`photometric.render_lambertian`，第 2 实现)。``noise`` > 0 时加上正态随机数。 · 示例: `poc_knife_tactile_toughness`, `poc_tacsim_elastic_membrane`, `poc_tacsim_marker_shear`, `poc_tactile_dipole_torque`

#### drive / tacslip (21)
- `cerruti_kernel` `scalar × scalar × scalar × scalar → table` GPU: 无 — 在 2n 网格上(用于补零的线性卷积)构造 x 向切向面力(1 像素 = pitch² 上均匀 1 Pa)产生的表面位移离散核，并以 rfft2 变换后的形式返回。 · 示例: `poc_tacsim_marker_shear`, `poc_tactile_dipole_torque`
- `cerruti_surface_displacement` `matrix × table → table` GPU: 无 — 切向面力分布 qx (n, n) [Pa] → 表面位移 ``ux``、``uy``(核中有 ``Kzx`` 时还有 ``uz``)(n, n) [m]。补零 2n 的线性卷积(无回绕)。**Raises** ValueError：qx 不是 (n, n)，kern 不是 :func:`cerruti_kernel` 的参数表。 · 示例: `poc_tacsim_marker_shear`
- `displace_markers` `matrix × matrix × matrix × scalar → matrix` GPU: 无 — 用位移场 fx, fy (n, n) [m] 移动标记中心 (N, 2) [px] (在中心位置双线性采样场，换算为像素后相加)。**Raises** ValueError：pts 不是 (N, 2)，fx 与 fy 形状不同，pitch ≤ 0。 · 示例: `poc_tacsim_marker_shear`, `poc_tactile_dipole_torque`
- `fem_nodes_load` `text × text → table` GPU: 无 — 读取 3 个有限元表面节点文本文件(随 Robo-Touch/Taxim 仓库附带，MIT 许可证)：``<dirpath>/<name>_{x,y,z}.txt``，制表符分隔、1 行表头 ``Node Number / X Location (m) / Y Location (m) / Z Location (m) / Directional Deformation (m)``，单位 m。3 个文件的节点集合相同，只有最后一列为该方向的位移。返回 ``id``、``X``、``Y``、``Z``、``dx``、``dy``、``dz``(各 (N,))、``n``、``name``。**Raises** FileNotFoundError：文件不存在。ValueError：表头不符、列数不是 5、3 个文件的节点坐标不一致(fail-closed)。 · 示例: `poc_tacsim_marker_shear`, `poc_tactile_dipole_torque`
- `fem_vs_halfspace` `table × table → table` GPU: 无 — 将同一节点集合上的法向压入 ``fz`` 与斜向压入 ``fxz``(:func:`fem_nodes_load`)与半空间解**仅按形状**比较(载荷大小未知)。(1) 在 0.5〜0.8 mm 处将 r·dz 归一化为 1(``mids``、``rdz_n``)：半空间 Boussinesq 在 r ≫ 接触时为常数，有限厚度则会下降。偏离 1/r 达 2 倍的半径 ``r_half``(没有则为 None)。(2) 在 r = 1/1.5/2/3 mm 的环上将斜向压入的 dx(θ) 拟合为 A + B cos²θ(``ang``：若为 Cerruti 则 B/A = ν/(1−ν) → ``nu``、``ratio`` = (A+B)/A、``R2``)，将 dy 拟合为 A + B sin2θ(``dy_fit``)。还返回 ``R_dome``(将表面 r–z 拟合为球冠所得的半径)、``dy_over_dz0``(仅有法向载荷时也出现的切向分量 = 非对称量)、``rdx_n``、``dz0``、``dx_min_spacing``、``r``、``th``(相对中心)。**Raises** ValueError：2 个表的节点数不同，节点少于 10 个。 · 示例: `poc_tacsim_marker_shear`
- `hertz_surface_ur` `matrix × scalar × scalar × scalar × scalar → matrix` GPU: 有(许可列表) — 法向载荷(Hertz 压力 p0√(1−r²/a²))在半空间表面产生的**径向**位移 ūr [m] (将 Johnson 1985 式 3.41b 用 E = 2G(1+ν) 改写)。负 = 指向中心。内侧 −(1−2ν)p0a²/(6Gr)[1 − (1−r²/a²)^{3/2}]，外侧 −(1−2ν)p0a²/(6Gr)(= 点载荷 −(1−2ν)P/(4πGr))，r → 0 时为 0。最大值不在边缘而在 r ≈ 0.93a(为 ūr(a) 的 1.022 倍)。ūr(a)/δ = 2(1−2ν)/(3π(1−ν))(ν 0.48 时 1.6 %，ν 0.3 时 12 %) —— 在近乎不可压缩的凝胶中，法向载荷几乎不会使标记移动。**Raises** ValueError：a, p0, G ≤ 0。 · 示例: `gallery_drive_soil_tactile`, `poc_tacsim_marker_shear`, `poc_tactile_dipole_torque`
- `hertzian_tangential_inner` `matrix × matrix × scalar × scalar × scalar × scalar → table` GPU: 仅在链中(许可列表) — Hertz 型切向面力 q0√(1−r²/a²) 在圆内 r ≤ a 产生的表面位移闭式(Johnson 1985 式 3.91)。``ux`` = (πq0/32Ga)[4(2−ν)a² − (4−3ν)x² − (4−ν)y²]，``uy`` = (πq0/32Ga)·2νxy [m]。在圆外不成立(圆外用卷积)。**Raises** ValueError：a, G ≤ 0，x 与 y 形状不同。 · 示例: `poc_tacsim_marker_shear`
- `marker_detect` `image2d × scalar × scalar → table` GPU: 有(许可列表) — 标记图像 m(:func:`marker_image`)→ 标记中心。``weighted``(主输出，(N, 2) 的 (x, y) [px])：以高阈值 0.5·dark 的连通分量(:func:`blob2d.blob_label`)为本体，将低阈值 0.08·dark 的像素(边缘晕)用距离变换分配给最近的本体，并用迭代高斯加权(σ = r_px)细化以 m 为权重的重心。``weighted_plain`` = 细化前。``binary=True`` 时 ``binary`` = :func:`blob2d.blob_features` 的 row/col(二值重心；还会计算周长和凸包，因此 1，000 个需 0.4 s)。接触边界的分量被舍弃。``n`` = 本体数。将边缘晕与本体切开，是因为在滑移环中相邻间距从 8 → 6 px 缩小时，低阈值的边缘晕会相连并合并成 1 个分量(实测)。**Raises** ValueError：m 不是 2 维，dark 在 (0, 1] 之外，r_px ≤ 0。 · 示例: `poc_tacsim_marker_shear`
- `marker_image` `rgb × rgb → image2d` GPU: 仅在链中(许可列表) — 仅含标记的图像 m = 1 − gray/gray_bg ∈ [0, 1] (H, W)。bg = 相同照明下无标记的图像 = 相当于实机上的参考帧标定。**Raises** ValueError：2 张图像形状不同，或不是 (H, W, 3)。 · 示例: `poc_tacsim_marker_shear`, `poc_tactile_dipole_torque`
- `marker_match_grow` `matrix × matrix × scalar → table` GPU: 无 — 通过**利用连续性逐步扩展**来求基准标记 p0 与加载后标记 p1(各 (N, 2) [px])的对应关系。返回 ``i0``、``i1``(对应的 index 数组)和 ``matched``。 · 示例: `gallery_drive_soil_tactile`
- `marker_track` `image2d × image2d × scalar × scalar × scalar → table` GPU: 无 — 由基准、加载后的标记图像(:func:`marker_image`)求位移向量场：检测(:func:`marker_detect`，2 张)→ 依连续性求对应(:func:`marker_match_grow`)→ ``u`` = p1 − p0 [px]。返回 ``p0``、``p1``、``u``(各 (M, 2))、``matched``、``n0``、``n1``。``piv=True`` 时附加 :func:`pivops.piv_cross_correlate` 的场(第 2 实现，搜索 ±0.12 窗口)作为 ``piv_flow``、``piv_info``、``piv_at``(在点列上采样的函数)。**Raises** ValueError：2 张图像形状不同。 · 示例: `poc_tacsim_marker_shear`
- `membrane_markers` `scalar × scalar → matrix` GPU: 无 — 在 n×n 像素视野中布置的标记中心 (N, 2) = (x, y) [px] 的规则网格(间距 pitch_px，亚像素相位 (ox, oy))。视野外也只多布置 1 圈(对应因位移而进入的部分)。**Raises** ValueError：n < 8，pitch_px < 2。 · 示例: `gallery_drive_soil_tactile`, `poc_tacsim_marker_shear`, `poc_tactile_dipole_torque`
- `membrane_render_markers` `rgb × matrix × scalar × scalar → rgb` GPU: 无 — 在 RGB (H, W, 3) 上绘制黑色圆盘标记(中心 pts (N, 2) [px]，半径 r_px)：按像素覆盖率 rgb *= 1 − dark·coverage。覆盖率只对圆盘边缘的像素做 sub² 的子采样(内侧 1、外侧 0)。不对图像插值变形，因此真值严格。**Raises** ValueError：rgb 不是 (H, W, 3)，pts 不是 (N, 2)，r_px ≤ 0，dark 在 [0, 1] 之外。 · 示例: `poc_knife_tactile_toughness`, `poc_tacsim_marker_shear`, `poc_tactile_dipole_torque`
- `membrane_shear_field` `table × table × matrix × matrix × table → table` GPU: 无 — 膜表面的位移场：用 Cerruti 核对 Mindlin 面力 q(r) 卷积得到的切向位移 ``ux``、``uy``，法向载荷的径向位移 ``urx``、``ury``(将 :func:`hertz_surface_ur` 分解为 x、y)[m]，``q``，粘着/滑移掩膜 ``mask_stick``(r ≤ c)、``mask_slip``(c < r ≤ a)，以及 ``r``。X、Y 为网格坐标 [m] (中心为原点)。**Raises** ValueError：X 与 Y 形状不同，与 kern 的 n 不符。 · 示例: `poc_tacsim_marker_shear`, `poc_tactile_dipole_torque`
- `mindlin_fit` `table × matrix × matrix → table` GPU: 无 — 将 (c/a, μP) 拟合到标记位置 pts_px (M, 2) [px] 与位移 u_m (M, 2) [m]：先粗扫 c/a → 在最佳值附近细搜，μP 对每个 c 用线性最小二乘求解。返回 ``c_over_a``、``q_ratio`` = 1 − (c/a)³、``muP``、``Q``、``mu``(= μP/P)、``rms_m``、``shift_m``。``rigid=True`` 还会放开刚体平移 (tx, ty) —— 在试作中**适得其反**(与外侧 900 个点的 1/r 尾部退化，使 c/a 偏差 0.028)，因此默认关闭。实机的漂移应另行用接触区外的远处标记扣除。用真实位移拟合时 c/a 误差为 0.001，用图像追踪时为 0.011(重心的 pixel-locking 以共模形式叠加)。**Raises** ValueError：形状不一致，点少于 3 个。 · 示例: `poc_tacsim_marker_shear`
- `mindlin_fit_vector` `table × matrix × matrix → table` GPU: 无 — 带方向的剪切的 Mindlin 拟合(:func:`mindlin_fit` 的 2 分量版)：一次读出 (c/a, μP, 方向 φ)。 · 示例: `gallery_drive_soil_tactile`
- `mindlin_model` `table × matrix × matrix × table × scalar × scalar → table` GPU: 无 — 以**相似律**给出任意 c/a 的 Mindlin 位移场的反算模型(卷积只做 1 次)。 · 示例: `gallery_drive_soil_tactile`, `poc_tacsim_marker_shear`
- `mindlin_partial_slip` `scalar × table × scalar × scalar × scalar → table` GPU: 无 — Cattaneo–Mindlin 部分滑移(Johnson 1985 §7.2)：在以法向力 P 压住球的同时施加切向力 Q。 · 示例: `poc_tacsim_marker_shear`, `poc_tactile_dipole_torque`
- `mindlin_traction` `matrix × table → matrix` GPU: 有(许可列表) — 切向面力 q(r) = q′ − q″ [Pa]：q′ = μp0√(1−r²/a²)(r < a)，q″ = μp0(c/a)√(1−r²/c²)(r < c)。在滑移环 c ≤ r < a 中 q = μp(r)(贴在 Coulomb 极限上)，在粘着圆中 q < μp。``mp`` 为 :func:`mindlin_partial_slip` 的参数表。与 r 同形状。**Raises** ValueError：mp 中缺少 a/c/mu/p0。 · 示例: `poc_tacsim_marker_shear`
- `slip_entropy` `signal → scalar` GPU: 无 — 位移大小 |u| 序列的直方图(bins 个箱，范围 [0, vmax] —— 省略时为最大值)的 Shannon 熵，以 ln(bins) 归一化(0..1)。Yuan 2017 的滑移指标：粘着核缩小、位于滑移环梯度上的标记增多时上升。**Raises** ValueError：没有点，bins < 2。 · 示例: `poc_tacsim_marker_shear`
- `stick_radius_modelfree` `matrix × matrix → table` GPU: 无 — 无模型的粘着半径：按到中心的距离排序，以内侧 6 个点的中位数 δ̂ 为基准，取 |ux − δ̂| 首次超过 rel·|δ̂| + abs_px 的点与其前一点的中点的半径 ``c_px``(分辨率 = 标记间距)。``core_px`` = δ̂。pts_c 为相对中心的 (M, 2) [px]，u_px 为 (M, 2) [px]。**Raises** ValueError：点少于 6 个。 · 示例: `poc_tacsim_marker_shear`

#### drive / tactorque (17)
- `boussinesq_kernel` `scalar × scalar × scalar × scalar → table` GPU: 无 — 法向压力(1 像素 = pitch² 上均匀 1 Pa)产生的表面位移的离散核(2n 网格，已做 rfft2)：``Kx`` = ū_x、``Ky`` = ū_y(切向，−(1−2ν)/(4πG) · x/r² 与 y/r²，Johnson 1985 §3.2 的点载荷解)，若 ``with_uz`` 则还有 ``Kz`` = ū_z((1−ν)/(2πGr))。按像素平均(sub² 的子样本)。中心像素：∫□ x/r² dA = 0(奇函数)，∫□ 1/r dA = 4h ln(1+√2)(解析值)。与 :func:`tacslip.cerruti_kernel`(切向 → 切向)同样构造的法向版本。**Raises** ValueError：n < 8，pitch, G ≤ 0，ν 在 [0, 0.5] 之外。 · 示例: `poc_tactile_dipole_torque`
- `boussinesq_surface_displacement` `matrix × table → table` GPU: 无 — 法向压力 p (n, n) [Pa] → 表面位移 ``ux``、``uy``(核中有 ``Kz`` 时还有 ``uz``，下沉方向为正)(n, n) [m]。补零到 2n 的线性卷积。**Raises** ValueError：p 不是 (n, n)，kern 不是 :func:`boussinesq_kernel` 的表。 · 示例: `poc_tactile_dipole_torque`
- `dipole_to_torque_fit` `signal × signal → table` GPU: 无 — 偶极子 1 个分量的序列 D (K,) 与已知力矩 M (K,) [N·m] 的线性标定：D ≈ k M(过原点)与 D ≈ k₁ M + b(带截距)。返回 ``k``、``R2``(过原点的决定系数 = 1 − SS_res/SS_tot)、``k1``、``b``、``R2_affine``、``rmse_M``(换算为 M 的残差 RMS)。相当于论文的标定系数 c = 1/k。**Raises** ValueError：K < 2，形状不同，M 全部相同。 · 示例: `poc_tactile_dipole_torque`
- `dipole_torque_resolution` `matrix × matrix × scalar × scalar × scalar × scalar × scalar → table` GPU: 无 — 把标记重心噪声 σ [px] 加到位移上，重复求偶极子 ``trials`` 次，测量扭矩分辨率 σ_M = σ_D/|coef| [N·m]。返回 ``sigma_D`` (2,)、``sigma_M`` (2,)、``D0``(无噪声)、``snr`` = |D0|/σ_D、``trials``。σ_M ∝ σ(实测)。**Raises** ValueError：σ < 0，trials < 2，coef = 0。 · 示例: `poc_tactile_dipole_torque`
- `ellipse_pressure_shifted` `matrix × matrix × scalar × scalar × scalar → matrix` GPU: 有(许可列表) — 半轴为 a(x)、b(y) [m] 的椭圆 Hertz 压力 p0 √(1 − x′²/a² − y′²/b²) [Pa]，P = 2πab p0/3(Johnson 1985 式 4.24)，中心移到 d。b ≫ a 时形状接近圆柱(棱、楔状)的压入 —— 形状不变门禁的第 3 个。**Raises** ValueError：a, b, P ≤ 0，X 与 Y 形状不同。 · 示例: `poc_tactile_dipole_torque`
- `grasp_torque_frame` `image2d × image2d × scalar × scalar × scalar × scalar × scalar × scalar → table` GPU: 无 — 从图像 1 次完成：基准与当前的标记图像(:func:`tacslip.marker_image`)→ :func:`tacslip.marker_track` → 以 m 为单位的场 → :func:`torque_decompose`。``pitch_px``、``r_px`` = 标记网格间距与半径 [px]，``pitch`` = m/px，``window`` 为以 [px] 计的 (cx, cy, R)。每 1 个标记的面积 = (pitch_px·pitch)²，散度的邻域半径 = 1.5 个间距。``P``、``mu``、``torsion_model`` 用于扭转的换算(:func:`torque_decompose`，默认为 Hertz 接触的部分滑移，需要 P 与 mu；平头压头用 ``"no_slip"``)。返回 = torque_decompose 的表 + ``track``(matched、n0、n1、p0、u [px])。**Raises** ValueError：跟踪对应少于 9 个(不足以求偶极子)，pitch ≤ 0，torque_decompose 的 ValueError。 · 示例: `poc_tactile_dipole_torque`
- `hertz_pressure_shifted` `matrix × matrix × table → matrix` GPU: 有(许可列表) — 中心移到 d = (dx, dy) [m] 的 Hertz 压力 p0 √(1 − r′²/a²) [Pa] (``hz`` = :func:`tacsim.hertz_sphere` 的表)。受到小倾斜扭矩 τ 的被抓握球，其压力中心偏移 d = τ/P(准静态力矩平衡)，因此平移后的 Hertz 压力绕原中心的 1 阶矩为 P·d = τ(严格线性)。**Raises** ValueError：hz 中没有 a/p0，X 与 Y 形状不同。 · 示例: `poc_tactile_dipole_torque`
- `marker_divergence` `matrix × matrix × scalar → table` GPU: 无 — 由散布的标记 pts (N, 2) 与位移 u (N, 2) 求各点的散度 ``div`` = ∂ux/∂x + ∂uy/∂y 与旋度 ``curl`` = ∂uy/∂x − ∂ux/∂y(单位为 u 的单位 ÷ pts 的单位)。对邻域半径 ``radius`` 内(最多 ``k_max`` 个)的点用最小二乘拟合平面 c0 + c1 x + c2 y(规则网格 + 半径 1.01 个间距时等价于 5 点中心差分，与 :func:`sceneflow.flow_divergence` 相差 1e-15；半径 1.5 个间距的 9 点为行平均差分，在边缘相差 11 %，实测)。对所有点一次性批量求解正规方程。邻域点数少于 ``min_neighbors``，或正规方程奇异(共线)的点，``valid`` = False，div/curl = nan(fail-closed：不会悄悄置 0)。FEM 的散布节点也用同一 op。**Raises** ValueError：pts/u 不是 (N, 2)，形状不同，radius ≤ 0，N < min_neighbors。 · 示例: `poc_tactile_dipole_torque`
- `pressure_first_moment` `matrix × matrix × matrix × scalar → table` GPU: 无 — 网格上压力 p (n, n) [Pa] 的 0 阶、1 阶矩：``P`` = Σ p h² [N]、``M1`` = Σ (x, y) p h² [N·m]、``tau`` = (−M1_y, M1_x)(z 由凝胶指向物体，为物体压凝胶之力 −ẑ p 的力矩)。**Raises** ValueError：形状不同，pitch ≤ 0。 · 示例: `poc_tactile_dipole_torque`
- `punch_pressure` `matrix × matrix × scalar × scalar → matrix` GPU: 有(许可列表) — 平头圆形压头(半径 a [m])的压力 [Pa]：p = P/(2πa√(a²−r²)) + 3(M1_x x + M1_y y)/(2πa³√(a²−r²))(r < a，外部为 0)。第 1 项 = Johnson 1985 式 3.34，第 2 项 = 满足 ∫ (x, y) p dA = M1 的反对称项(推导见模块 docstring，由门禁做数值确认)。传入 ``pitch`` 时，以 sub×sub 的子样本对像素取平均(减小边缘 1/√ 奇点的网格误差；4×4 时 Σ p h² 与 P 相差 0.6 %，实测)。**Raises** ValueError：a ≤ 0、P < 0、X 与 Y 形状不同、|M1| > Pa/3(接触脱离：线性公式不成立，fail-closed)。 · 示例: `poc_tactile_dipole_torque`
- `punch_surface_uz` `matrix × scalar × scalar × scalar × scalar → matrix` GPU: 有(许可列表) — 平头圆形压头(法向力 P)作用下半空间表面的法向位移 [m] (下沉方向为正)：圆内为均匀的 δ = P(1−ν)/(4Ga)，圆外为 (2δ/π) arcsin(a/r)(Johnson 1985 §3.4 的平头压头。正文中未能确认式号，**unverified** —— 通过与 Boussinesq 核 ``Kz`` 的卷积在 0.35 % 内一致做了数值验证)。**Raises** ValueError：a, P, G ≤ 0。 · 示例: `poc_tactile_dipole_torque`
- `rigid_rotation_fit` `matrix × matrix → table` GPU: 无 — 用最小二乘对窗口内的标记场拟合刚体位移 u ≈ t + ω ẑ×r：``t`` = 平均位移，``omega`` = Σ (x′u′_y − y′u′_x)/Σ r′²(′ 表示减去窗口内平均值)，``resid_rms`` = 残差 RMS，``n``。无滑移扭转中圆内为刚体转动(u_θ = βr)，因此 ω = β 是真值(平均 curl/2 因拟合在圆的边缘漏到外侧而偏低 —— 实测 11 %)。``window`` = (cx, cy, R)。**Raises** ValueError：点少于 3 个。 · 示例: `poc_knife_tactile_toughness`, `poc_tactile_dipole_torque`
- `surface_divergence_closed_form` `matrix × scalar × scalar → matrix` GPU: 无 — 半空间表面切向位移散度的闭式 ∇·ū = −(1−2ν) p/(2G)(本模块的推导：Boussinesq 点载荷 ū_r = −(1−2ν)P/(4πGr) 与 2 维的 ∇·(r̂/r) = 2πδ²)。与卷积的数值散度比较的门禁(r < 0.8a 时 0.2 %，实测)。**Raises** ValueError：G ≤ 0。 · 示例: `poc_tactile_dipole_torque`
- `tactile_dipole_moment` `matrix × matrix → table` GPU: 无 — 触觉偶极矩 D = Σ_i w ρ_i r_i(2 个分量)。``form``：* ``"divergence"`` —— 论文(arXiv 2404.15626)式 4–8：ρ_i = (∇·u)_i(传入 ``rho``，或用 ``radius`` 调用 :func:`marker_divergence`)。* ``"norm_cross"`` —— 论文的基线(式 10–11，Yamaguchi & Atkeson 式)：ρ_i = |u_i|(以向量的范数代替法向力)。l_i × f_i 的倾斜分量为 (l_y|u|, −l_x|u|)，即把 D 旋转 90°，因此放在同一个"1 阶矩"的格子里返回。取零点后的对称倾斜下 |u| 是 M 的偶函数，因此恒为 0(不知道符号，门禁)。* ``"radial"`` —— 本模块的变体：ρ_i = u_i · r̂_i(径向分量)。``origin``：``"midpoint"``(式 6–7，正负重心的中点)/ ``"centre"``(pts 的平均，基线的做法)/ (x0, y0)。``weight``：``"area"`` = 乘以每 1 点的面积 ``area`` [m²] (可与闭式系数 −(1−2ν)/(2G) 比较，单位 m³)/ ``"mean"`` = 1/N(论文)。若 ``window`` = (cx, cy, R)，只用半径 R 内的点(切掉剪切泄漏的窗口，依据见模块 docstring)。排除非 valid 的点(nan)。返回 ``D`` (2,)、``tau_dir`` = (−D_y, D_x)(式 9 的方向，不含系数)、``origin``、``n``、``rho``、``form``、``keep``。**Raises** ValueError：form/origin/weight 未知(拼写错误按 fail-closed 处理)，pts/u 的形状，"area" 却没有 area，可用点少于 3 个。 · 示例: `poc_tactile_dipole_torque`
- `tilt_shear_field` `matrix × matrix × table → table` GPU: 无 — 完全照搬论文"抓握后取零点"的步骤：将抓握刚完成时的压力 p_before 与施加扭矩后的压力 p_after 之差 Δp 用 Boussinesq 核卷积，返回取零点后的标记位移 ``ux``、``uy``(、``uz``)和 ``dp``。若 Δp 的 0 阶矩为 0(法向力不变)，偶极子与原点无关。**Raises** ValueError：2 个数组形状不同。 · 示例: `poc_tactile_dipole_torque`
- `torque_decompose` `matrix × matrix × scalar × scalar × scalar → table` GPU: 无 — 将标记场分解为 3 个力学量：``translation`` = 窗口内的平均位移(剪切 Q，单向分量)，``omega`` = 刚体转角(:func:`rigid_rotation_fit`)→ 扭转 ``Mz``(需要 a；``omega_curl`` = 平均 curl/2 仅供参考)，``D`` = 散度偶极子(面积加权)→ 倾斜 ``M1`` = D / coef(coef 默认 = 半空间闭式 −(1−2ν)/(2G)，实机传入标定值)，``tau`` = (−M1_y, M1_x)。散度和 curl 在减去平均位移后不变(常数的导数为 0)，因此与顺序无关。窗口 (cx, cy, R) 限于接触圆(因为在半空间中纯剪切会在整个窗口产生散度偶极子，参见模块 docstring)。``radius`` = 散度的邻域半径(必填)。 · 示例: `poc_tactile_dipole_torque`
- `torsion_stick_field` `matrix × matrix × scalar × scalar × table × scalar → table` GPU: 无 — 无滑移扭转(Reissner–Sagoci，相当于 Johnson 1985 §3.9，式号未确认 → 用卷积做数值验证)的表面位移场：用 :func:`tacslip.cerruti_kernel` 的核卷积面力 q_θ = 3M_z r/(4πa³√(a²−r²)) 得到的 ``ux``、``uy`` [m]，以及闭式 ``beta`` = 3M_z/(16Ga³)、圆内的刚体转动 ``ux_cf`` = −βy、``uy_cf`` = βx(r < a)、面力 ``qx``、``qy``。卷积在圆内返回均匀的 u_θ/r = β，以此用独立实现验证 β 的公式(−0.5 %，均匀性 0.14 %，实测)。这是无滑移的场：对平头压头直到全滑移的 8/(3π) 倍都严格成立，但 Hertz 接触必然从边缘开始滑移 —— Hertz 接触的部分滑移场见 :func:`cuttouch.torsion_partial_slip` 的 ``field=True``(参见模块 docstring)。**Raises** ValueError：G ≤ 0，a ≤ 0，X 与 Y 形状不同，核的网格不匹配。 · 示例: `poc_tactile_dipole_torque`

#### drive / terrain (20)
- `add_mesh_object` `table × table → scalar` GPU: 无 — 将程序化网格(tree_mesh / pedestrian_mesh …，原点 = 底面中心)按位姿放置并加入世界。 · 示例: `gallery_drive_world_objects`, `poc_driving_crossing`, `poc_driving_decisions`, `poc_driving_humanoids`, `poc_driving_lateral`, `poc_driving_traffic`, `poc_world_terrain`
- `course_distance` `table × points → table` GPU: 无 — 点 (N, 2) 到路线(可行驶多边形之并)的距离，以及从最近点指向外侧的单位向量。 · 示例: `poc_world_terrain`
- `crosswalk_mesh` `无输入 → table` GPU: 无 — 人行横道(斑马线)：沿横穿道路的线段 a→b，以宽 ``stripe``、间隔 ``gap`` 排列条纹，并沿与 a→b 正交的方向延伸 ``length``(在 a→b 的左手侧)。``{"V", "F", "color", "label" (12), "n_stripes", "area"}``。 · 示例: `poc_driving_crossing`, `poc_driving_humanoids`, `poc_world_terrain`
- `fbm_gradient` `image2d × image2d × table → any` GPU: 有(许可列表) — (∂h/∂x, ∂h/∂y) 的闭式。 · 示例: `poc_world_terrain`
- `fbm_height` `image2d × image2d × table → image2d` GPU: 有(许可列表) — fBm 高度的闭式：h(x, y) = Σ_k A_k cos(2π f_k (x cosθ_k + y sinθ_k) + φ_k)(参数表来自 :func:`fbm_params`)。 · 示例: `poc_rover_slip_risk_path`, `poc_world_terrain`
- `fbm_params` `无输入 → table` GPU: 无 — 用随机相位正弦之和构造 fBm 曲面的参数表(Saupe 1988 频谱合成的连续版)。 · 示例: `poc_rover_slip_risk_path`
- `material_params` `无输入 → table` GPU: 无 — 材质参数表。puddle = Perlin(puddle_freq) > puddle_level 之处(仅道路内侧，标签 11，颜色 = 反射 refl·天空 + (1−refl)·带阴影的路面)，stain = 同样方式的暗色污渍(标签仍为道路，保留在真值场 "stain" 中)，wear = 白线磨损率 clip(wear·(Perlin(wear_freq)·0.5+0.5)·2, 0, 1)。 · 示例: `poc_world_terrain`
- `mesh_signed_volume` `points × matrix → scalar` GPU: 无 — 闭合网格的带符号体积(散度定理：Σ v₀·(v₁×v₂)/6，朝外为正)。 · 示例: `poc_world_terrain`
- `pedestrian_mesh` `无输入 → table` GPU: 无 — 程序化行人：2 条腿(盒)、躯干(盒)、头(旋转体)。原点 = 脚下中心，+x 为前方。用 ``stride`` [m] 前后分开双腿。 · 示例: `gallery_drive_world_objects`, `poc_driving_crossing`, `poc_driving_humanoids`, `poc_driving_traffic`, `poc_driving_weather`, `poc_world_terrain`
- `perlin2` `image2d × image2d → table` GPU: 有(许可列表) — 在世界坐标 (x, y) 处计算 Perlin(2002，improved noise)的 2 维梯度噪声。 · 示例: `poc_world_terrain`
- `radial_periodogram` `image2d → table` GPU: 有(许可列表) — 将网格上高度场 (H, W) 的周期图沿径向平均：``{"f", "power", "count"}``(f 单位为 周期/m)。 · 示例: `poc_world_terrain`
- `scatter_offroad` `table → points` GPU: 无 — 在道路外撒放物体(dart throwing)：各点距路线至少 ``margin``，彼此至少相距 ``r_min``。 · 示例: `poc_world_terrain`
- `spectral_slope` `image2d → table` GPU: 无 — 对径向周期图做 log–log 直线拟合：``{"beta", "intercept", "n"}``(power ∝ f^{−beta})。 · 示例: `poc_world_terrain`
- `terrain_gradient` `image2d × image2d × table → any` GPU: 有(许可列表) — (∂z/∂x, ∂z/∂y) 的闭式：∇(h·w) = w∇h + h·w′(d)·∇d，∇d = 从最近点指向外侧的单位向量。 · 示例: `poc_world_terrain`
- `terrain_height` `image2d × image2d × table → image2d` GPU: 有(许可列表) — z = fbm(x, y)·w(d(x, y)) + 波动(x, y)。无 course 时 w = 1(仅起伏)。 · 示例: `poc_world_terrain`
- `terrain_mesh` `table × table → table` GPU: 无 — 将 (xmin, xmax, ymin, ymax) 按 step 划分为格子单元、z = terrain_height 的网格 mesh。 · 示例: `gallery_drive_city_terrain`
- `terrain_params` `无输入 → table` GPU: 无 — 地形参数表：fBm 起伏(距道路 ``flat`` m 内为 0，其后在 ``blend`` m 内 smoothstep)+ 路面波动 ``road_amp·½[sin(2πx/L₁+φ₁) + sin(2πy/L₂+φ₂)]``(也作用于道路，梯度上限 = road_amp·π/min(L))。 · 示例: `gallery_drive_city_terrain`, `poc_world_terrain`
- `tree_mesh` `无输入 → table` GPU: 无 — 程序化树木：树干 = 正 n 棱柱(高 0.35·height)，树冠 = 圆锥(conifer)或旋转椭球(broadleaf，上下 0.65·height)。 · 示例: `poc_world_terrain`
- `world_apply_terrain` `table × table → table` GPU: 无 — 对 world_build 的输出(平坦的世界)施加地形(原地修改，返回同一个 dict)。 · 示例: `poc_world_terrain`
- `world_materials` `table × table × matrix × matrix × table → table` GPU: 无 — 对渲染结果 ``view``(world_camera 的输出，含 "shade")逐像素施加路面材质。 · 示例: `poc_world_terrain`

#### drive / town (10)
- `kyosoku_summary` `无输入 → table` GPU: 无 — 读取交通教则场景的再现台账(docs/drive/kyosoku_scenarios.json)，生成 category × status 的计数表。 · 示例: `poc_driving_town`
- `town_centerline` `table → any` GPU: 无 — 按弧长每 ``step`` 对拼接后的中心线采样 → ``(N, 4) = (s, x, y, yaw)``(终点一定包含在内)。 · 示例: `poc_driving_town`
- `town_chain` `any → table` GPU: 无 — 按顺序拼接并放置各要素: 以闭式求出使要素 k+1 的 entry 对齐要素 k 的 exit(其前方 ``overlap`` 处)的刚体配置，并传给 :func:`drivecourse.course_layout`。 · 示例: `poc_driving_town`
- `town_checks` `table × table → table` GPU: 无 — 全程行驶的评分(闭式门禁 + 现有的铁路道口评分 op)。 · 示例: `poc_driving_japan_town`, `poc_driving_town`
- `town_crossing_state` `table → table` GPU: 无 — 把时刻 t 的铁路道口设备状态写入世界(所有道口使用同一列车时刻)。 · 示例: `poc_driving_town`
- `town_layout` `无输入 → table` GPU: 无 — 默认城镇。``"default"`` = road(30) → intersection → road(20) → crossing(铁路道口) → road(20) → slope → road(20) → parallel_parking → road(30)(全部宽 7 m，停止线为交叉口 1 条、铁路道口 1 条)。``"short"`` = road(20) → crossing → road(20) (用于测试的快速门禁)。 · 示例: `poc_driving_town`
- `town_rules` `无输入 → table` GPU: 无 — 法规包(:data:`RULE_PACKS` 的副本)。``{"jurisdiction", "side": "left"|"right", "crossing_stop": "always"|"when_active", "intersection_stop": "signal", "hold_s", "look_required", "look_hold_s", "sources": [...], "verified", "notes"}``。 · 示例: `poc_driving_town`
- `town_run` `table → table` GPU: 无 — 沿中心线的仅纵向全程行驶(基于规则)。 · 示例: `poc_driving_japan_town`, `poc_driving_town`
- `town_stop_lines` `table → table` GPU: 无 — 按弧长顺序列出城镇的停止线: ``[{"s", "x", "y", "yaw", "kind", "element", "crossing_zone": (s0, s1) | None, "drawn": bool}, ...]``。 · 示例: `poc_driving_town`
- `town_world` `table → table` GPU: 无 — :func:`driveworld.world_build` 的薄封装(``props`` 及其余参数原样传递)，把停止线、信号灯、铁路道口位置表作为 ``world["town"]`` 加入，并在每个道口要素处放置**带栏杆的道口报警器 2 台、栏木(抬起)、道口铺板、列车(在远处待机)**。 · 示例: `poc_driving_town`

#### drive / traffic (18)
- `bus_stop_rate` `any → any` GPU: 无 — 在停靠公交车前后较高的出现率 λ(x) = base + peak [exp(−½((x − rear)/spread)²) + exp(−½((x − front)/spread)²)] [次/m]。表示行人从公交车的阴影(前端之前)和后方走出的模式示例(值为调用方的假定)。上限为 base + 2·peak。 · 示例: `poc_driving_traffic`
- `driver_style` `无输入 → table` GPU: 无 — 返回 3 种驾驶风格("careful" / "normal" / "sloppy")的参数。**所有值均为假定**(无出处)。 · 示例: `poc_driving_traffic`
- `idm_accel` `any → any` GPU: 无 — Intelligent Driver Model 的加速度(Treiber, Hennecke, Helbing 2000)。 · 示例: `poc_driving_decisions`, `poc_driving_town`, `poc_driving_traffic`
- `idm_equilibrium_gap` `any → any` GPU: 无 — IDM 的平衡车距 s_e(v) = (s0 + v T) / sqrt(1 − (v/v0)^δ)(0 ≤ v < v0)。 · 示例: `poc_driving_traffic`
- `idm_platoon_simulate` `any → table` GPU: 无 — 在头车速度曲线之后积分 IDM 跟随车队(车 0 = 头车，1..n = 跟随车)。 · 示例: `poc_driving_traffic`
- `importance_risk_estimate` `any → table` GPU: 无 — 以提高出现率的试验(速率 λ')使事故更容易发生，再用似然比权重换算回原速率 λ 下的事故概率。 · 示例: `poc_driving_traffic`
- `lateral_wobble` `无输入 → signal` GPU: 无 — Ornstein–Uhlenbeck 过程 dX = −θ X dt + σ dW 的精确离散化(长度 n 的序列，步长 dt)。 · 示例: `poc_driving_traffic`
- `occlusion_reveal_distance` `any → scalar` GPU: 无 — 路边停放车辆(有朝向的盒子)背后的点 ``emerge_xy`` 从本车视点**首次可见**时的纵向距离。 · 示例: `poc_driving_traffic`
- `occlusion_safe_speed` `any → any` GPU: 无 — 从可见瞬间起能在距离 d 内停下的最大速度 v = b(−ρ + sqrt(ρ² + 2d/b))。 · 示例: `poc_driving_traffic`
- `occlusion_visible_intervals` `any → any` GPU: 无 — 本车视点沿 p(s) = ego_xy + s h 前进 0 ≤ s ≤ s_max 期间，点 ``emerge_xy`` **可见**的前进量区间列表。 · 示例: `poc_driving_traffic`
- `ou_estimate` `signal → table` GPU: 无 — 从等间隔 dt 的观测序列读出横向摆动(均值 0 的 OU 过程 dX = −θX dt + σ dW)的参数。 · 示例: `poc_driving_traffic`
- `passing_decision` `无输入 → any` GPU: 无 — 根据到对向来车的距离 ``dist_oncoming``(判断时，本车位于 x_in 时)返回 "go" 或 "wait"。 · 示例: `poc_driving_traffic`
- `passing_gap_required` `无输入 → table` GPU: 无 — 为避让停放车辆而驶入对向车道的区段的通过时间，以及对向来车在此之前不会到达的临界距离(闭式)。 · 示例: `poc_driving_traffic`
- `passing_simulate` `无输入 → table` GPU: 无 — 按时间推进模拟 "go" 的情形，返回 PET(本车完全驶回本车道的时刻与对向来车到达该地点时刻之差)。 · 示例: `poc_driving_traffic`
- `pedestrian_crossing` `无输入 → table` GPU: 无 — 以横穿意图为真值的行人轨迹(分段闭式，不做积分)。 · 示例: `poc_driving_traffic`
- `poisson_events` `any → signal` GPU: 无 — 用 thinning(Lewis & Shedler 1979)在 [0, x_max] 上抽取 1 条非齐次泊松过程样本(按升序排列的位置数组)。 · 示例: `poc_driving_traffic`
- `poisson_events_xt` `any → any` GPU: 无 — 用 thinning 在 [0, x_max] × [0, t_max] 上抽取 1 条时空非齐次泊松过程样本(速率 λ(x, t) [次/(m·s)])。 · 示例: `poc_driving_traffic`
- `social_force_step` `points × points × points → any` GPU: 无 — social force 的 1 步(单位质量。Helbing & Molnár 1995 / Helbing, Farkas, Vicsek 2000 的形式)。 · 示例: `gallery_drive_mirrors_crowds`

#### drive / ttc (9)
- `flow_from_depth_motion` `image2d × matrix × matrix → table` GPU: 有(许可列表) — 由深度图像与刚体运动得到**真实光流**：``{"u", "v", "valid", "depth1"}``(各为 (H, W))。 · 示例: `poc_ttc_rss`, `poc_world_terrain`
- `foe_from_flow` `image2d × image2d → table` GPU: 无 — 由光流估计扩张焦点(FoE)：``{"foe": (col, row), "n", "residual"}``。 · 示例: `poc_world_terrain`
- `foe_from_motion` `matrix × matrix → signal` GPU: 无 — 扩张焦点(FoE)的像素 ``(col, row)``：将相对运动的平移 ``t`` 在无穷远处投影所得的点。 · 示例: `poc_ttc_rss`, `poc_world_terrain`
- `label_extent` `labels2d → table` GPU: 无 — 标签图像中值为 ``value`` 的像素的包围盒：``{"col0", "col1", "row0", "row1", "width", "height", "n"}``。 · 示例: `poc_ttc_rss`, `poc_video_physics_consistency`
- `relative_motion` `matrix × matrix → matrix` GPU: 无 — 2 帧之间、在相机坐标中看到的点的刚体运动 ``T_rel``(``P_c1 = T_rel · P_c0``)。 · 示例: `poc_ttc_rss`, `poc_world_terrain`
- `ttc_from_flow` `image2d × image2d → table` GPU: 有(许可列表) — 由光流求 τ(秒)：``{"tau_map", "tau", "n", "foe"}``。 · 示例: `poc_ttc_rss`
- `ttc_from_range` `无输入 → scalar` GPU: 无 — 由距离与接近速度求 τ = d / v(秒)。由世界位姿给出的真值(v ≤ 0 时为 ``inf``，d < 0 时为 ``ValueError``)。 · 示例: `poc_ttc_rss`
- `ttc_from_scale` `无输入 → scalar` GPU: 无 — 由视在大小的变化求 τ(秒，以第一帧的时刻计)：``τ₀ = Δt · w₁ / (w₁ − w₀)``。 · 示例: `poc_ttc_rss`
- `ttc_truth` `image2d × matrix × matrix → table` GPU: 有(许可列表) — 逐像素的**真实 τ**(秒，以第一帧的时刻计)与接近速度：``{"tau", "closing_speed", "depth1", "valid"}``。 · 示例: `poc_ttc_rss`

#### drive / walkterrain (12)
- `detect_obstacles` `depth → mask` GPU: 无 — 分割出高出可行走地面超过 *clearance* 的单元。 · 示例: `walking_ops_tour`
- `elevation_map` `points → depth` GPU: 无 — 将点云分箱为 2.5-D 高程栅格。 · 示例: `perception_pipeline`, `physical_ai_perception`, `walking_ops_tour`
- `elevation_normals` `depth → normalmap` GPU: 无 — 高程图的朝上单位法线 (H, W, 3) —— :func:`surface_normals` 的台账入口。 · 示例: `walking_ops_tour`
- `elevation_step_edges` `depth → mask` GPU: 无 — 高程图的台阶边缘(路缘 / 台阶前缘)-> ``(edge_mask, signed_rise)``(台账入口)。 · 示例: `walking_ops_tour`
- `elevation_traversability` `depth → mask` GPU: 无 — 高程图中可通行的单元(True = 在台阶与坡度上限之内)—— :func:`traversability` 的台账入口。 · 示例: `walking_ops_tour`
- `fill_gaps` `depth → depth` GPU: 无 — 用最近的有限高度填充 ``nan`` 单元(最近邻)。 · 示例: `walking_ops_tour`
- `foothold_candidates` `depth → table` GPU: 无 — 从地形中挑选离散的安全落脚目标。 · 示例: `consumer_hillco`, `physical_ai_perception`, `walking_ops_tour`
- `foothold_score` `depth → image2d` GPU: 无 — 每个单元的平坦度得分 [0, 1] (1 = 平坦且水平 = 好的落脚点)。 · 示例: `walking_ops_tour`
- `fuse_elevation` `images → depth` GPU: 无 — 将多个对齐的高程栅格融合为一张以机器人为中心的地图。 · 示例: `walking_ops_tour`
- `ground_plane` `depth → depth` GPU: 无 — 每个单元的稳健最小二乘地面平面 ``z = a·x + b·y + c``。 · 示例: `walking_ops_tour`
- `ground_surface` `depth → depth` GPU: 无 — 通过灰度开运算(先最小滤波再最大滤波)得到平滑的可行走地面包络。 · 示例: `walking_ops_tour`
- `roughness_map` `depth → image2d` GPU: 无 — 每个单元的表面粗糙度 = ``window`` 邻域内高度的局部标准差。碎石 / 植被上高,平滑地面上约为 0。 · 示例: `walking_ops_tour`

#### drive / world (4)
- `load_asset` `无输入 → table` GPU: 无 — 将内置资产读成网格(mesh) dict：``{"V", "F", "color", "label", "name", "dims"}``。 · 示例: `poc_driving_longitudinal`, `poc_driving_pass`, `poc_driving_school`, `poc_driving_weather`, `poc_ttc_rss`
- `world_build` `table → table` GPU: 无 — 由路线(要素或 layout)构建世界。 · 示例: `gallery_drive_japan_roads`, `gallery_drive_world_objects`, `poc_driving_longitudinal`, `poc_driving_school`, `poc_driving_weather`, `poc_ttc_rss`, `poc_world_terrain`
- `world_camera` `table × matrix × matrix → table` GPU: 无 — 用相机拍摄世界：``{"color" (H,W,3), "label" (H,W) int(−1 = 空), "depth" (H,W), "face" (H,W), "shade" (H,W)}``。 · 示例: `gsplat_trained_product`, `poc_ball_bounce`, `poc_driving_crossing`, `poc_driving_decisions`, `poc_driving_endless_map`, `poc_driving_humanoids`, `poc_driving_japan_town`, `poc_driving_lateral`, `poc_driving_longitudinal`, `poc_driving_pass`, `poc_driving_school`, `poc_driving_town`, `poc_driving_traffic`, `poc_kendama`, `poc_table_tennis_bounce`, `poc_table_tennis_spin`, `poc_ttc_rss`, `poc_world_terrain`
- `world_move` `table → any` GPU: 无 — 将物体 i(由资产放置的物体)移到新位姿 (x, y, yaw)(只改写顶点；面、标签、颜色不变)。 · 示例: `poc_driving_crossing`, `poc_driving_decisions`, `poc_driving_lateral`, `poc_ttc_rss`, `poc_world_terrain`

### tomography (43 ops / 8 categories)

#### tomography / artifact (5)
- `beam_hardening_apply` `sinogram → sinogram` GPU: 有(许可列表) — 把单色正弦图变成**多色**的 —— 杯状伪影的来源。 · 示例: `ct_reconstruction`, `poc_battery_ct_degradation`
- `beam_hardening_correct` `sinogram → sinogram` GPU: 无 — 消除杯状伪影 —— 用模型的精确逆,或用标定过的多项式。 · 示例: `ct_reconstruction`
- `metal_trace_interpolate` `sinogram → sinogram` GPU: 无 — 线性插值的金属伪影抑制(LI-MAR)。 · 示例: `ct_reconstruction`
- `ring_artifact_apply` `sinogram → sinogram` GPU: 无 — 给探测器加上逐 bin 的增益误差 —— 环状伪影之源。 · 示例: `ct_reconstruction`, `poc_battery_ct_degradation`
- `ring_artifact_remove` `sinogram → sinogram` GPU: 无 — 通过压平角度平均剖面来去掉逐探测器 bin 的偏移。 · 示例: `ct_reconstruction`

#### tomography / ct_scan (11)
- `ct_adjoint_project` `projstack × ctgeometry → voxel` GPU: 无 — :func:`ct_forward_project` 的精确转置 ``A^T``。 · 示例: `ct_scan_modes`, `poc_ct_casting_sparse_views`, `poc_real_walnut_cbct`
- `ct_dual_energy_reconstruct` `projstack × projstack × ctgeometry → table` GPU: 无 — 由同一几何的两次扫描得到两个基材料体数据。 · 示例: `poc_ct_casting_sparse_views`, `poc_real_walnut_cbct`
- `ct_forward_project` `voxel × ctgeometry → projstack` GPU: 无 — 沿 *geometry* 的每条射线投影体数据：离散算子 ``A``。 · 示例: `ct_scan_modes`, `poc_ct_casting_sparse_views`, `poc_real_walnut_cbct`
- `ct_scan_geometry` `无输入 → ctgeometry` GPU: 无 — 描述一次 CT 扫描：每个视角下射线源和探测器的位置。 · 示例: `ct_scan_modes`, `poc_ct_casting_sparse_views`, `poc_real_walnut_cbct`
- `ellipsoid_phantom` `无输入 → voxel` GPU: 无 — 将若干均匀椭球之和栅格化到 ``(Z, Y, X)`` 网格上。 · 示例: `ct_scan_modes`, `poc_ct_casting_sparse_views`
- `ellipsoid_projections` `ctgeometry → projstack` GPU: 无 — 椭球之和的精确线积分，适用于本族的任意扫描。 · 示例: `ct_scan_modes`, `poc_ct_casting_sparse_views`
- `fdk_reconstruct` `projstack × ctgeometry → voxel` GPU: 无 — 适用于所有具备重建公式的扫描的滤波反投影：FDK 及其同类方法。 · 示例: `ct_scan_modes`, `poc_ct_casting_sparse_views`, `poc_real_walnut_cbct`
- `os_sart_reconstruct` `projstack × ctgeometry → voxel` GPU: 无 — OS-SART：将 SIRT 更新逐个应用于有序视角子集。 · 示例: `ct_scan_modes`, `poc_ct_casting_sparse_views`, `poc_real_walnut_cbct`
- `shepp_logan_3d` `无输入 → voxel` GPU: 无 — ``size`` 立方网格上的改进型三维 Shepp-Logan 头部体模。 · 示例: `ct_scan_modes`, `poc_ct_casting_sparse_views`
- `sirt_reconstruct` `projstack × ctgeometry → voxel` GPU: 无 — SIRT：同时使用全部视角，``x <- x + lam C A^T R (p - A x)``。 · 示例: `ct_scan_modes`, `poc_ct_casting_sparse_views`, `poc_real_walnut_cbct`
- `tv_reconstruct` `projstack × ctgeometry → voxel` GPU: 无 — 基于 Chambolle-Pock 原始对偶法的全变分重建。 · 示例: `ct_scan_modes`, `poc_ct_casting_sparse_views`, `poc_real_walnut_cbct`

#### tomography / forward (3)
- `ellipse_phantom` `无输入 → image2d` GPU: 无 — 把若干均匀椭圆之和栅格化到 *size* x *size* 的切片上。 · 示例: `ct_reconstruction`, `poc_ct_fidelity`, `tomography_reconstruct`
- `ellipse_sinogram` `无输入 → sinogram` GPU: 无 — 若干均匀椭圆之和的**闭式** Radon 变换。 · 示例: `ct_reconstruction`, `poc_ct_fidelity`
- `radon_transform` `image2d → sinogram` GPU: 无 — 平行束正向投影:输入一张切片,输出**正弦图**。 · 示例: `ct_reconstruction`, `poc_aoi_ct_traceability`, `poc_ct_fidelity`, `poc_sem_tem_same_particle`

#### tomography / geometry (2)
- `sinogram_center_of_rotation` `sinogram → measurement` GPU: 无 — 旋转轴实际在哪里(距中心多少个探测器 bin)。 · 示例: `ct_reconstruction`
- `sinogram_center_shift` `sinogram → sinogram` GPU: 无 — 把正弦图重新对中到它的旋转轴上。 · 示例: `ct_reconstruction`

#### tomography / layout (2)
- `projection_angles` `无输入 → signal` GPU: 无 — 扫描的角度序列,以**度**为单位的一维 float64 数组。 · 示例: `ct_reconstruction`, `poc_battery_ct_degradation`, `poc_ct_fidelity`, `tomography_reconstruct`
- `sinogram_design` `无输入 → table` GPU: 无 — 这套扫描几何能解析什么、不能解析什么 —— **在动手之前**。 · 示例: `ct_reconstruction`, `tomography_reconstruct`

#### tomography / reconstruct (3)
- `backproject_sinogram` `sinogram → image2d` GPU: 有(许可列表) — **未滤波**的朴素反投影 —— 模糊的基线。 · 示例: `ct_reconstruction`, `poc_ct_fidelity`
- `filtered_backprojection` `sinogram → image2d` GPU: 有(许可列表) — 滤波反投影(FBP)—— CT 重建的标准方法。 · 示例: `ct_reconstruction`, `poc_aoi_ct_traceability`, `poc_ct_fidelity`, `poc_sem_tem_same_particle`
- `sart_reconstruct` `sinogram → image2d` GPU: 无 — SART —— 同时代数重建,一次一个角度。 · 示例: `ct_reconstruction`

#### tomography / spectral_xray (15)
- `basis_decomposition_crlb` `无输入 → table` GPU: 无 — 以闭式返回基厚度 b 处分解方差的下限(Cramér–Rao)。 · 示例: `poc_dual_energy_xray`
- `basis_material_decompose` `images → images` GPU: 无 — 通道信号 → 基材料的厚度图(Alvarez–Macovski / Lehmann 基分解)。 · 示例: `poc_dual_energy_xray`
- `dual_energy_separability` `无输入 → table` GPU: 无 — 两种材料(厚度)能被通道的对数衰减区分到什么程度(d′ 与错误率的闭式)。 · 示例: `poc_dual_energy_xray`
- `dual_kvp_channels` `pairs × pairs → table` GPU: 无 — 以两种管电压拍摄的能量积分型(闪烁体)探测器的两个通道。 · 示例: `poc_dual_energy_xray`
- `effective_z_map` `images → image2d` GPU: 无 — 由双能图像估计有效原子序数图像(将 R 与元素的曲线对照)。
- `material_effective_z` `无输入 → table` GPU: 无 — 由组成返回有效原子序数(Mayneord / Spiers 幂律式)和电子密度。 · 示例: `poc_dual_energy_xray`
- `material_xray_attenuation` `无输入 → pairs` GPU: 无 — 以 ``pairs``(E [keV], 值)返回材料的 X 射线衰减(默认为质量衰减系数 μ/ρ [cm²/g])。 · 示例: `poc_dual_energy_xray`, `poc_geodetic_height_frames`
- `material_xray_constants` `无输入 → table` GPU: 无 — 返回单一能量下的 X 射线常数(μ/ρ、μ_en/ρ、μ、半值层、平均自由程)及其出处。 · 示例: `poc_dual_energy_xray`
- `material_xray_table` `无输入 → table` GPU: 无 — 返回可以查询 X 射线列(质量衰减系数 μ/ρ)的材料一览。
- `photon_counting_channels` `pairs → table` GPU: 无 — 光子计数探测器的能量窗 → 通道(一个光子计一次)。 · 示例: `poc_dual_energy_xray`
- `r_value_map` `images → image2d` GPU: 无 — 返回 R = L_low / L_high(低能与高能对数衰减之比)的图像。
- `scintillator_sensor_qe` `无输入 → table` GPU: 无 — 闪烁体耦合传感器的量子效率:1 个 X 射线光子 → 闪烁体吸收 → 发光 → 光探测器中的电子数。 · 示例: `scintillator_sensor_tour`
- `xray_beam_quality` `pairs → table` GPU: 无 — 能谱的线质:第一、第二半值层、均匀系数、平均能量和有效能量。 · 示例: `poc_dual_energy_xray`
- `xray_channel_projection` `images → images` GPU: 无 — 每种材料的厚度图 → 每个通道的信号图像 (C, H, W)。 · 示例: `poc_dual_energy_xray`
- `xray_tube_spectrum` `无输入 → pairs` GPU: 无 — 以 ``pairs``(E [keV], 光子数 / keV)返回 X 射线管的光子能谱(归一化为 Σ φ ΔE = 1)。 · 示例: `poc_dual_energy_xray`

#### tomography / volume (2)
- `fbp_volume` `sinostack → voxel` GPU: 无 — 重建 ``(Z, A, D)`` 堆栈的全部正弦图 -> ``(Z, S, S)`` 体。 · 示例: `poc_battery_ct_degradation`, `tomography_reconstruct`
- `radon_volume` `voxel → sinostack` GPU: 无 — 投影 ``(Z, H, W)`` 体的每一张切片 -> ``(Z, A, D)`` 堆栈。 · 示例: `poc_battery_ct_degradation`, `tomography_reconstruct`

### volcolor (11 ops / 7 categories)

#### volcolor / colorize (2)
- `vol_colorize_labels` `labels → rgbvolume` GPU: 无 — 3-D 标签体 -> ``(D, H, W, 3)`` float64 的 RGB 体。 · 示例: `voxel_labels_color`
- `vol_label_overlay` `voxel × labels → rgbvolume` GPU: 无 — 在原灰度体上叠加彩色标签,返回 ``(D, H, W, 3)``。 · 示例: `voxel_labels_color`

#### volcolor / diagnose (1)
- `vol_label_color_flicker` `voxel → table` GPU: 无 — **数出**「先分割再上色」与「先上色再分割」的差异。 · 示例: `voxel_labels_color`

#### volcolor / measure (2)
- `vol_label_legend` `labels → table` GPU: 无 — 图例表:哪个颜色对应哪个成分,以及它的测量值。 · 示例: `voxel_labels_color`
- `vol_label_shape_stats` `labels → table` GPU: 无 — 每个成分**线性时间可得**的定量值(体积、重心、包围盒、主成分形状指标)。 · 示例: `poc_cold_chain_excursion`, `voxel_labels_color`

#### volcolor / palette (1)
- `vol_label_palette` `无输入 → matrix` GPU: 无 — 标签 ``0..n_labels`` 的 RGB 调色板 ``(n_labels + 1, 3)`` float64。 · 示例: `voxel_labels_color`

#### volcolor / render (2)
- `vol_label_volume_render` `labels → rgbimage` GPU: 无 — 彩色标签的**合成投影** ``(H, W, 3)``,仅用 numpy 生成。 · 示例: `voxel_labels_color`
- `vol_labels_to_meshes` `labels → table` GPU: 无 — 对每个成分做 marching cubes,得到**一组彩色网格**。 · 示例: `voxel_labels_color`

#### volcolor / select (1)
- `vol_select_labels` `labels → labels` GPU: 无 — 按 3-D 特征筛选成分(2-D 斑点筛选的 3-D 版)。 · 示例: `voxel_labels_color`

#### volcolor / slice (2)
- `vol_label_mpr_rgb` `rgbvolume → rgbimage` GPU: 有(许可列表) — 把彩色体的三个正交断面排成**一张 RGB 图**。 · 示例: `voxel_labels_color`
- `vol_label_slice_rgb` `rgbvolume → rgbimage` GPU: 仅在链中(许可列表) — 从彩色体中取出一张断面 RGB(轴位 / 冠状 / 矢状)。 · 示例: `voxel_labels_color`

### reprconv (63 ops / 15 categories)

#### reprconv / algebra (11)
- `angle_to_matrix` `angle → matrix` GPU: 无 — 角度 **[度]** → 绕 z 轴的旋转矩阵 ``matrix (3,3)``。``angle`` 的出口。 · 示例: `representation_roundtrip`
- `countrate_to_counts` `countrate → counts` GPU: 无 — 计数率 ``[Hz]`` → 计数 ``counts``。``countrate`` 的出口(**可逆**)。 · 示例: `representation_roundtrip`
- `counts_to_countrate` `counts → countrate` GPU: 无 — 计数 → 计数率 ``[Hz]``。:func:`countrate_to_counts` 的逆。 · 示例: `representation_roundtrip`
- `cscalar_to_polar` `cscalar → pairs` GPU: 无 — 复标量 → 极形式 ``pairs (1,2) = [|z|, arg z[度]]``。``cscalar`` 的出口。 · 示例: `representation_conversion`
- `deformation_to_points` `deformation → points` GPU: 无 — TPS 变形 ``deformation`` → 控制点 ``points (N,3)``。``deformation`` 的出口。 · 示例: `representation_conversion`
- `matrix_to_angle` `matrix → angle` GPU: 无 — 绕 z 轴的旋转矩阵 → 角度 **[度]**。:func:`angle_to_matrix` 的逆。 · 示例: `representation_roundtrip`
- `matrix_to_rot_scale` `matrix → rot_scale` GPU: 无 — 2-D 相似变换 ``(2,2)`` → ``(角度[度], 倍率)``。:func:`rot_scale_to_matrix` 的逆。 · 示例: `representation_conversion`
- `polar_to_cscalar` `pairs → cscalar` GPU: 无 — 极形式 ``pairs (1,2) = [r, theta[度]]`` → 复标量。:func:`cscalar_to_polar` 的逆。 · 示例: `representation_conversion`
- `rot_scale_to_matrix` `rot_scale → matrix` GPU: 无 — ``(角度[度], 倍率)`` → 2-D 相似变换 ``matrix (2,2)``。``rot_scale`` 的出口。 · 示例: `representation_conversion`
- `shift_to_vector` `shift → vector` GPU: 无 — 整数位移 ``(dz, dy, dx)`` → ``vector (3,)``。``shift`` 的出口(**可逆**)。 · 示例: `poc_bga_ball_type_roundtrip`, `representation_conversion`
- `vector_to_shift` `vector → shift` GPU: 无 — ``vector (3,)`` → 整数位移 ``(dz, dy, dx)``。:func:`shift_to_vector` 的反向。 · 示例: `poc_bga_ball_type_roundtrip`, `representation_conversion`

#### reprconv / curvature (3)
- `curvature_to_shape_index` `curvature → pairs` GPU: 无 — 主曲率 ``(N,2)`` → 形状指数与弯曲度 ``(N,2)`` 的 ``pairs``。``curvature`` 的出口。 · 示例: `poc_bga_ball_type_roundtrip`, `representation_roundtrip`
- `curvature_to_table` `curvature → table` GPU: 无 — 曲率 → 分布的汇总 ``table``。**单向**(统计的职责就是丢弃信息)。 · 示例: `poc_bga_ball_type_roundtrip`, `representation_conversion`
- `shape_index_to_curvature` `pairs → curvature` GPU: 无 — 形状指数与弯曲度 ``(N,2)`` → 主曲率 ``(N,2)``。:func:`curvature_to_shape_index` 的逆。 · 示例: `poc_bga_ball_type_roundtrip`, `representation_roundtrip`

#### reprconv / derivative (5)
- `gradient_coherence` `gradient → voxel` GPU: 无 — 3-D 梯度 → 结构张量的**面状程度**(相干性)``voxel``,值域 [0, 1]。 · 示例: `type_connectivity_tour`
- `gradient_magnitude` `gradient → voxel` GPU: 无 — 3-D 梯度 ``gradient`` → 梯度幅值体 ``voxel``。``gradient`` 类型的出口。 · 示例: `type_connectivity_tour`
- `hessian_determinant` `hessian → voxel` GPU: 无 — 3-D Hessian ``hessian`` → 行列式 ``det H`` 的体 ``voxel``(带符号)。``hessian`` 类型的出口。 · 示例: `hessian_numpy_chain`, `type_connectivity_tour`
- `hessian_vesselness` `hessian → voxel` GPU: 无 — 3-D Hessian → Frangi 管状度(vesselness)``voxel``,值域 [0, 1]。 · 示例: `hessian_numpy_chain`, `type_connectivity_tour`
- `voxel_to_hessian` `voxel → hessian` GPU: 无 — 体 ``voxel`` → 3-D Hessian ``hessian`` 的 6 个分量 (zz, yy, xx, zy, zx, yx)。仅用 numpy 与 scipy 构建的 ``hessian`` 类型的入口。 · 示例: `hessian_numpy_chain`

#### reprconv / descriptor (3)
- `descriptor_to_matrix` `descriptor → matrix` GPU: 无 — 描述子 → ``matrix``。``descriptor`` 的出口(**可逆**)。 · 示例: `representation_conversion`, `representation_roundtrip`
- `descriptor_to_table` `descriptor → table` GPU: 无 — 描述子 → 汇总 ``table``。**单向**。 · 示例: `representation_conversion`
- `matrix_to_descriptor` `matrix → descriptor` GPU: 无 — ``matrix`` → 描述子。:func:`descriptor_to_matrix` 的逆。 · 示例: `representation_conversion`

#### reprconv / direction (3)
- `angles_to_normals` `pairs → normals` GPU: 无 — 方位、仰角对 ``(N,2)`` **[度]** → 单位法线 ``(N,3)``。``pairs`` 的出口。 · 示例: `poc_bga_ball_type_roundtrip`, `representation_roundtrip`
- `normals_to_angles` `normals → pairs` GPU: 无 — 法线 ``(N,3)`` → 方位、仰角对 ``(N,2)`` **[度]**。``normals`` 的出口。 · 示例: `poc_bga_ball_type_roundtrip`, `poc_tacscalib_sphere_lut`, `representation_roundtrip`, `type_connectivity_tour`
- `normals_to_egi` `normals → image2d` GPU: 无 — 法线 ``(N,3)`` → 扩展高斯像 ``(n_el, n_az)`` 的 ``image2d``。 · 示例: `poc_bga_ball_type_roundtrip`, `representation_conversion`

#### reprconv / entry (3)
- `indices_to_positions` `indices → positions` GPU: 无 — 下标 ``indices`` → 事件位置 ``positions``(物理单位)。``positions`` 类型的入口。 · 示例: `type_connectivity_tour`
- `jones_state` `无输入 → jones` GPU: 无 — 偏振方位与椭圆率 → Jones 向量 ``jones``(Ex, Ey)。``jones`` 类型的入口。 · 示例: `type_connectivity_tour`
- `synapse_table_from_table` `table → synapse_table` GPU: 无 — 表 ``table``(列名 → 数组)→ 突触表 ``synapse_table (m, 3)``。``synapse_table`` 类型的入口。 · 示例: `type_connectivity_tour`

#### reprconv / exit (3)
- `pairs_peak_x` `pairs → measurement` GPU: 无 — 对 ``pairs (x, y)`` → y 最大处的 x(用抛物线插值到采样之间)``measurement``。 · 示例: `type_connectivity_tour`
- `pose_to_matrix` `pose → matrix` GPU: 无 — 刚体位姿 ``pose (R, t)`` → 4×4 齐次变换 ``matrix``。 · 示例: `type_connectivity_tour`
- `tokens_to_matrix` `tokens → matrix` GPU: 无 — token 序列 ``tokens (T, d)`` → 一般矩阵 ``matrix (T, d)``。``tokens`` 类型的出口。 · 示例: `type_connectivity_tour`

#### reprconv / field (4)
- `table_field_image2d` `table → image2d` GPU: 无 — 表 ``table`` 的一栏 → 2-D 图像 ``image2d``。从返回 ``table`` 的 op 到接收图像的 op 的连接。 · 示例: `type_connectivity_tour`
- `table_field_matrix` `table → matrix` GPU: 无 — 表 ``table`` 的一栏 → 一般矩阵 ``matrix``。例: ``swt_map`` 的 ``swt`` 栏 → ``text_candidates``。
- `table_field_measurement` `table → measurement` GPU: 无 — 表 ``table`` 的一栏 → 一个数 ``measurement``。例: ``label_extent`` 的 ``width``。
- `table_field_signal` `table → signal` GPU: 无 — 表 ``table`` 的一栏 → 1-D 数组 ``signal``。把 CSV 的一列或 dict 的序列交给信号 op。

#### reprconv / flow (4)
- `flow_apply` `points × flow_scattered → points` GPU: 无 — 把散在流 ``(N,3)`` 加到点群 ``(N,3)`` 上 → ``points``。``flow`` 的消费侧。 · 示例: `poc_bga_ball_type_roundtrip`, `representation_conversion`
- `flow_magnitude` `flow_dense → voxel` GPU: 仅在链中(许可列表) — 稠密场景流 ``(3,D,H,W)`` → 速度体 ``voxel (D,H,W)``。``flow`` 的出口。 · 示例: `perception_on_video`, `representation_roundtrip`
- `flow_speed` `flow_scattered → signal` GPU: 无 — 散在流 ``(N,3)`` → 速度 ``signal (N,)``。散在 ``flow`` 的出口。 · 示例: `poc_bga_ball_type_roundtrip`, `representation_conversion`, `representation_roundtrip`
- `flow_to_rgbimage` `flow_dense → rgbimage` GPU: 无 — 稠密场景流的一个切片 → 色相=方向、明度=速度的 ``rgbimage``。 · 示例: `representation_conversion`

#### reprconv / gaussians (3)
- `gaussians_to_points` `gaussians → points` GPU: 无 — ``gaussians`` → 中心的点群 ``(N,3)``。``gaussians`` 的出口(**中心可逆**)。 · 示例: `poc_bga_ball_type_roundtrip`, `representation_roundtrip`
- `gaussians_to_voxel` `gaussians → voxel` GPU: 无 — ``gaussians`` → 密度 ``voxel (D,H,W)``。``gaussians`` 的第二个出口。 · 示例: `poc_bga_ball_type_roundtrip`, `representation_roundtrip`
- `points_to_gaussians` `points → gaussians` GPU: 无 — 点群 ``(N,3)`` → 各向同性的 ``gaussians``。**该类型的唯一入口**。 · 示例: `poc_bga_ball_type_roundtrip`, `representation_roundtrip`

#### reprconv / index (3)
- `indices_to_labels` `indices → labels` GPU: 无 — 索引 ``(N,)`` → 选择掩码 ``labels``。``indices`` 的出口(**可逆**)。 · 示例: `poc_bga_ball_type_roundtrip`, `representation_conversion`
- `labels_to_indices` `labels → indices` GPU: 无 — ``labels`` → 非背景的索引 ``(N,)``。:func:`indices_to_labels` 的反向。 · 示例: `poc_bga_ball_type_roundtrip`, `representation_conversion`
- `select_points` `points × indices → points` GPU: 无 — 点群 ``(N,3)`` 与索引 ``(M,)`` → 子点群 ``(M,3)``。``indices`` 的消费侧。 · 示例: `poc_bga_ball_type_roundtrip`, `representation_conversion`

#### reprconv / keypoint (8)
- `keypoints_from_image2d` `image2d → keypoints` GPU: 有(许可列表) — 计数/响应图像 ``(H, W)`` → 图像坐标 ``(N,2) = (u, v)``。往返的回程。 · 示例: `poc_bga_ball_type_roundtrip`, `representation_roundtrip`
- `keypoints_rowcol_to_uv` `keypoints → keypoints` GPU: 无 — 像面点 ``(row, col)`` → ``(u, v) = (col, row)``。``keypoints`` 类型两种约定之间的连接。 · 示例: `poc_bga_ball_type_roundtrip`, `type_connectivity_tour`
- `keypoints_to_image2d` `keypoints → image2d` GPU: 无 — 图像坐标 ``(N,2) = (u, v)`` → 计数图像 ``(H, W)``。``keypoints`` 的第二个出口。 · 示例: `poc_bga_ball_type_roundtrip`, `representation_roundtrip`
- `keypoints_uv_to_points` `keypoints → points` GPU: 无 — 图像坐标 ``(N,2) = (u, v)`` → 点群 ``(N,3) = (z, y, x)``。``keypoints`` 的出口。 · 示例: `poc_bga_ball_type_roundtrip`, `representation_roundtrip`
- `keypoints_uv_to_rowcol` `keypoints → keypoints` GPU: 无 — 像面点 ``(u, v) = (col, row)`` → ``(row, col)``。:func:`keypoints_rowcol_to_uv` 的反向。 · 示例: `poc_bga_ball_type_roundtrip`
- `points_to_position` `points → position` GPU: 无 — 点群 ``(N,3)`` → 重心 ``(z, y, x)``。**不可逆**(丢弃了分布)。 · 示例: `poc_bga_ball_type_roundtrip`, `representation_conversion`, `representation_roundtrip`
- `points_zyx_to_keypoints_uv` `points → keypoints` GPU: 无 — 点群 ``(N,3) = (z, y, x)`` → 图像坐标 ``(N,2) = (u, v)``。 · 示例: `poc_bga_ball_type_roundtrip`, `representation_roundtrip`
- `position_to_points` `position → points` GPU: 无 — 位置 ``(z, y, x)`` → 单点点群 ``(1, 3)``。``position`` 的出口(**可逆**)。 · 示例: `poc_bga_ball_type_roundtrip`, `representation_conversion`

#### reprconv / pairs (3)
- `pairs_to_image2d` `pairs → image2d` GPU: 无 — 对 ``(N,2)`` → 散点密度图像 ``(H, W)``。``pairs`` 的第三个出口。 · 示例: `representation_conversion`
- `pairs_to_signal` `pairs → signal` GPU: 无 — 对 ``(N,2)`` → 因变量的 ``signal (N,)``。``pairs`` 的第二个出口。 · 示例: `representation_conversion`, `representation_roundtrip`
- `pairs_to_table` `pairs → table` GPU: 无 — 对 ``(N,2)`` → 汇总 ``table``。**单向**。 · 示例: `representation_conversion`

#### reprconv / score (3)
- `correlation_score` `voxel × voxel → score` GPU: 有(许可列表) — 两个 ``voxel`` → 归一化互相关的 ``score`` 体。**该类型的唯一入口**。 · 示例: `poc_bga_ball_type_roundtrip`, `poc_leak_localization`, `representation_conversion`, `representation_roundtrip`
- `score_to_image2d` `score → image2d` GPU: 无 — ``score`` 体 → 最大值投影 ``image2d``。``score`` 的第二个出口。 · 示例: `poc_bga_ball_type_roundtrip`, `representation_conversion`
- `score_to_position` `score → position` GPU: 无 — ``score`` 体 → 最大值的位置 ``position (z, y, x)``。``score`` 的出口。 · 示例: `poc_bga_ball_type_roundtrip`, `representation_conversion`

#### reprconv / structure (4)
- `frame_axis` `frame → normals` GPU: 无 — Frenet 标架 ``frame`` → 一根轴的单位向量列 ``normals (N,3)``。``frame`` 类型的出口。 · 示例: `type_connectivity_tour`
- `knn_graph_to_conn_graph` `graph → conn_graph` GPU: 无 — k 近邻图 ``graph`` → 加权邻接矩阵 ``conn_graph (n, n)``。``graph`` 类型的出口。 · 示例: `poc_bga_ball_type_roundtrip`, `type_connectivity_tour`
- `match_component` `match → measurement` GPU: 无 — ``match`` 类型(1-D 结果向量)→ 其中一个分量的 ``measurement``。``match`` 类型的出口。 · 示例: `type_connectivity_tour`
- `pointmap_to_points` `pointmap → points` GPU: 无 — 网格排列的 3-D 点 ``pointmap (H,W,3)`` → 点云 ``points (N,3)``。``pointmap`` 类型的出口。 · 示例: `poc_bga_ball_type_roundtrip`, `type_connectivity_tour`

### fileio (28 ops / 10 categories)

#### fileio / archive (4)
- `archive_create` `any × text → any` GPU: 无 — 从路径或命名内容创建确定性的归档 `bytes`。 · 示例: `archive_roundtrip`
- `archive_extract` `any × text → any` GPU: 无 — 将归档安全地解压到空目标目录，并返回相对路径。 · 示例: `archive_roundtrip`
- `archive_list` `any → table` GPU: 无 — 列出归档成员的名称、解压前后大小、修改时间和目录标志。 · 示例: `archive_roundtrip`
- `archive_probe` `any → text` GPU: 无 — 检查归档文件的魔数并返回格式名称。 · 示例: `archive_roundtrip`

#### fileio / e57 (2)
- `e57_read` `any → table` GPU: 无 — 读取 ASTM E57 `bytes`，返回带坐标、强度、颜色和位姿的点云 `table`。 · 示例: `fileio_roundtrip`, `poc_real_file_formats`
- `e57_write` `table → any` GPU: 无 — 将带坐标、强度、颜色和位姿的点云 `table` 写成 ASTM E57 `bytes`。 · 示例: `fileio_roundtrip`

#### fileio / fits (2)
- `astro_fits_read` `any → any` GPU: 无 — 读取主 HDU 的二维/三维 FITS 图像，返回 `(image_or_volume, meta)`。 · 示例: `fileio_scientific_roundtrip`, `poc_real_file_formats`
- `astro_fits_write` `any → any` GPU: 无 — 将二维/三维天文图像和基本 WCS 写成主 HDU FITS `bytes`。 · 示例: `fileio_scientific_roundtrip`

#### fileio / mesh (8)
- `mesh_read_obj` `text → mesh` GPU: 无 — 读取 Wavefront OBJ 的 `v` 和 `f` 记录（包括 `v//vn`），返回三角 `mesh`。
- `mesh_read_off` `text → mesh` GPU: 无 — 读取 Geomview OFF，返回三角 `mesh` `(vertices, faces)`。
- `mesh_read_ply` `any → table` GPU: 无 — 读取 ASCII 或二进制 PLY，返回包含顶点、面、颜色、法线和标量属性的 `table`。 · 示例: `fileio_roundtrip`
- `mesh_read_stl` `any → mesh` GPU: 无 — 读取 ASCII 或小端二进制 STL，返回共享顶点的 `mesh` `(vertices, faces)`。
- `mesh_write_obj` `mesh → text` GPU: 无 — 将三角网格写成包含 `v`、`vn` 和 `f` 的 Wavefront OBJ 字符串（`text`）。
- `mesh_write_off` `mesh → text` GPU: 无 — 将三角网格写成 Geomview OFF 字符串（`text`）。
- `mesh_write_ply` `table → any` GPU: 无 — 将顶点、面、颜色、法线和任意标量属性写成 ASCII 或小端 PLY（`text` / `bytes`）。 · 示例: `fileio_roundtrip`
- `mesh_write_stl` `mesh → any` GPU: 无 — 将三角网格写成 ASCII 或小端二进制 STL（`text` / `bytes`）。

#### fileio / mrc (2)
- `em_mrc_read` `any → any` GPU: 无 — 读取 MRC2014/CCP4 的 mode 0/1/2/6，返回 `(image_or_volume, meta)`。 · 示例: `fileio_scientific_roundtrip`, `poc_real_file_formats`
- `em_mrc_write` `any → any` GPU: 无 — 将二维/三维电镜数据写成 MRC2014/CCP4 `bytes`。 · 示例: `fileio_scientific_roundtrip`

#### fileio / nifti (2)
- `nifti_read` `any → any` GPU: 无 — 读取单文件 NIfTI-1（`.nii` / `.nii.gz`），返回 `(array, meta)`。 · 示例: `fileio_scientific_roundtrip`, `poc_real_file_formats`
- `nifti_write` `any → any` GPU: 无 — 将带 affine/pixdim 的三维/四维数组写成单文件 NIfTI-1 `bytes`。 · 示例: `fileio_scientific_roundtrip`

#### fileio / nrrd (2)
- `nrrd_read` `any → any` GPU: 无 — 读取 raw/gzip NRRD，返回带明确空间单位的 `(array, meta)`。 · 示例: `fileio_scientific_roundtrip`
- `nrrd_write` `any → any` GPU: 无 — 将多维数组和 `space directions` 写成 raw/gzip NRRD `bytes`。 · 示例: `fileio_scientific_roundtrip`

#### fileio / ome_tiff (2)
- `ome_tiff_read` `any → any` GPU: 无 — 读取 OME-TIFF 为 `(stack, meta)`，并交叉核对 OME-XML 与数组。 · 示例: `fileio_scientific_roundtrip`, `poc_real_file_formats`
- `ome_tiff_write` `any → any` GPU: 无 — 将带物理尺寸和通道名的 TCZYX 多维数组写成 OME-TIFF `bytes`。 · 示例: `fileio_scientific_roundtrip`

#### fileio / points (2)
- `points_read_xyz` `text → points` GPU: 无 — 读取空白分隔的 XYZ 文本，返回 `(N,3)` `points`。 · 示例: `fileio_roundtrip`
- `points_write_xyz` `points → text` GPU: 无 — 将有限的 `(N,3)` 点写成 17 位精度的 XYZ 文本（`text`）。 · 示例: `fileio_roundtrip`

#### fileio / table (2)
- `table_read_csv` `text → table` GPU: 无 — 读取 :func:`table_write_csv` 生成的带单位 CSV，返回包含列、单位与元数据的 ``table``。 · 示例: `fileio_roundtrip`, `type_connectivity_tour`
- `table_write_csv` `table → text` GPU: 无 — 把带单位和来源信息的表写成 pandas 与 MATLAB 均可读取的 CSV 字符串(``text``)。 · 示例: `fileio_roundtrip`

### cadmap (4 ops / 4 categories)

#### cadmap / defect (1)
- `cad_defect_to_cad` `mesh × labels → table` GPU: 无 — 2-D 缺陷标签图 → **CAD 面上的表**(面 ID / 面上面积 / 3-D 重心)。 · 示例: `defect_to_cad`

#### cadmap / project (1)
- `cad_surface_to_pixel` `mesh × points → table` GPU: 无 — 3-D 点 (N,3) → 像素 + **可见性**(遮挡、背面、出画分别返回)。 · 示例: `defect_to_cad`

#### cadmap / raycast (1)
- `cad_pixel_to_surface` `mesh × keypoints → table` GPU: 无 — 像素 (N,2) → CAD 面上的 ``(face_id, 重心坐标, 3-D 点)``(闭式)。 · 示例: `defect_to_cad`

#### cadmap / visibility (1)
- `cad_visible_faces` `mesh → indices` GPU: 无 — 从该相机**实际可见**的面 ID(升序,``indices`` sort)。 · 示例: `defect_to_cad`

### annotate (51 ops / 8 categories)

#### annotate / compose (3)
- `compare_frame` `image2d × image2d → image2d` GPU: 有(许可列表) — 把两张图并排,在交界处放**分隔线**与**标签**。 · 示例: `annotate_gallery`
- `panel_grid` `image2d → image2d` GPU: 仅在链中(许可列表) — 把面板排成网格,并在每个框下铺一条标签带(montage / 印相表)。 · 示例: `annotate_gallery`, `annotate_paper_tour`
- `zoom_inset` `image2d → image2d` GPU: 有(许可列表) — 放大嵌入图 —— 在原图上加**框**与**引出线**。 · 示例: `annotate_gallery`, `poc_diabolo_model_and_vision`, `poc_food_cutting_measure`

#### annotate / furniture (3)
- `color_bar` `image2d × lut → image2d` GPU: 有(许可列表) — LUT 的图例(色条),带最小值、最大值、单位标注。 · 示例: `annotate_gallery`, `poc_cad_scan_deviation`, `poc_ct_void_morphology`, `poc_dem_terrain`, `poc_interferometry_step`, `poc_lidar_terrain_change`, `poc_lightfield_depth`, `poc_multibeam_bathymetry`, `poc_pv_thermal_survey`, `poc_sem_tem_same_particle`, `poc_simcal_thin_film`, `poc_stockpile_volume`, `poc_thermography_ndt`
- `legend_box` `image2d × entries → image2d` GPU: 仅在链中(许可列表) — 颜色 × 说明的图例。**框高由条目数以闭式确定**。 · 示例: `annotate_gallery`, `poc_driving_decisions`, `poc_measurement_system_analysis`, `poc_moire_alignment`, `poc_pxrd_phase_peel`, `poc_real_tless_6dof`
- `scale_bar` `image2d → image2d` GPU: 有(许可列表) — 物理长度的比例尺。**像素↔物理的换算由参数给出**(不自行假定)。 · 示例: `annotate_gallery`, `poc_sem_tem_same_particle`

#### annotate / overlay (5)
- `annotate_invert` `image2d × mask → image2d` GPU: 有(许可列表) — 用**反色**填充/描边区域(region)。 · 示例: `annotate_paper_tour`
- `annotate_invert_path` `image2d × pairs → image2d` GPU: 有(许可列表) — 用**反色**绘制折线(line)。带抗锯齿。 · 示例: `annotate_paper_tour`
- `annotate_invert_visibility` `image2d × mask → table` GPU: 无 — 在绘制之前测量反色**在该底色上是否真的看得见**。 · 示例: `annotate_paper_tour`
- `overlay_labels` `image2d × labels → image2d` GPU: 有(许可列表) — 以 α 叠加彩色标签图。**同一标签号始终是同一颜色**。 · 示例: `annotate_gallery`, `poc_mri_bias_field`, `poc_recycling_sorting`
- `overlay_mask` `image2d × mask → image2d` GPU: 有(许可列表) — 以 α 叠加二值掩码。**严格为 ``a*f + (1-a)*b``**。 · 示例: `annotate_gallery`, `poc_kendama`, `poc_pv_thermal_survey`, `poc_real_sem_metal_layer`

#### annotate / paper (23)
- `annotate_angle` `image2d → image2d` GPU: 有(许可列表) — 返回图像(image2d):用圆弧和数值标出三点所成的角(需要时连两条边)。 · 示例: `paper_figure`
- `annotate_angle_layout` `无输入 → table` GPU: 无 — 返回表(dict):``a, vertex, b`` 三点所成(较小)角的圆弧与文字位置。 · 示例: `paper_figure`
- `annotate_colorbar` `image2d × image2d → image2d` GPU: 有(许可列表) — 返回图像(image2d):用 LUT 给标量场上色并叠加,附上色条。 · 示例: `paper_figure`, `poc_thin_film_reflectometry`
- `annotate_dimension` `image2d → image2d` GPU: 有(许可列表) — 返回图像(image2d):尺寸线(两端箭头 + 尺寸界线 + 数值与单位)。 · 示例: `paper_figure`
- `annotate_dimension_layout` `无输入 → table` GPU: 无 — 返回表(dict):以闭式确定尺寸线的几何(尺寸线、界线、文字位置)。 · 示例: `paper_figure`
- `annotate_figure_grid` `images → image2d` GPU: 有(许可列表) — 返回图像(image2d):把图像 + 标题排成一张图(边距一致,带面板字母)。 · 示例: `paper_figure`, `poc_flybrain_pointcloud`, `poc_itof_multifreq`, `poc_pixel_shift`
- `annotate_figure_grid_layout` `无输入 → table` GPU: 无 — 返回表(dict):以闭式给出多面板图的排版(单元格、面板、标题带的矩形)。 · 示例: `paper_figure`
- `annotate_inset` `image2d → image2d` GPU: 无 — 返回图像(image2d):在角落嵌入原框的放大图,并用线连接对应的角。 · 示例: `paper_figure`, `poc_real_defect_floor`
- `annotate_inset_layout` `无输入 → table` GPU: 无 — 返回表(dict):以闭式确定放大嵌入图的位置与倍率。 · 示例: `paper_figure`
- `annotate_leader` `image2d → image2d` GPU: 有(许可列表) — 返回图像(image2d):带折点的引出线 + 文字(多点时自动避让)。 · 示例: `paper_figure`
- `annotate_leader_layout` `无输入 → table` GPU: 无 — 返回表(dict):以闭式确定引出线的布置(折点、文字位置、衬板矩形)。 · 示例: `paper_figure`
- `annotate_legend` `image2d → image2d` GPU: 有(许可列表) — 返回图像(image2d):带编号圆形标记 × 说明的图例(:func:`annotate_markers` 的搭档)。 · 示例: `paper_figure`, `poc_real_defect_floor`
- `annotate_markers` `image2d → image2d` GPU: 有(许可列表) — 返回图像(image2d):在每个点放置带编号(或短字符串)的圆形标记。 · 示例: `paper_figure`
- `annotate_orientation` `image2d → image2d` GPU: 有(许可列表) — 返回图像(image2d):表示方位(北)或朝向的箭头 + 文字。 · 示例: `paper_figure`
- `annotate_outline` `image2d × mask → image2d` GPU: 无 — 返回图像(image2d):把掩码轮廓画成(抗锯齿的)闭合折线,并在重心处放文字。 · 示例: `paper_figure`, `poc_rotation_invariance_audit`
- `annotate_outline_layout` `mask → table` GPU: 无 — 返回表(dict):二值掩码的边界回路(沿像素边的闭合多边形)与重心。 · 示例: `paper_figure`
- `annotate_panel_label` `image2d → image2d` GPU: 仅在链中(许可列表) — 返回图像(image2d):在角落放置面板字母 ``(a)``/``(b)``。 · 示例: `annotate_paper_tour`
- `annotate_scale_bar` `image2d → image2d` GPU: 仅在链中(许可列表) — 返回图像(image2d):在角落放置取整长度的比例尺(带数值与单位)。 · 示例: `paper_figure`, `poc_flybrain_pointcloud`, `poc_telecentric_metrology`
- `annotate_scale_bar_layout` `无输入 → table` GPU: 无 — 返回表(dict):不超过图像宽度 ``target_fraction`` 的**取整**长度比例尺。 · 示例: `paper_figure`
- `annotate_table` `image2d × text → image2d` GPU: 无 — 返回图像(image2d)：将制表符分隔的字符串绘制成**表格**(带半透明底板)。 · 示例: `annotate_paper_tour`, `poc_rotation_invariance_audit`
- `annotate_table_layout` `text → table` GPU: 无 — 返回 table(dict)：将制表符分隔的字符串作为**表格**放置时的列与行位置。 · 示例: `annotate_paper_tour`
- `annotate_text_path` `image2d × text → image2d` GPU: 有(许可列表) — 返回图像(image2d):沿折线排布文字(每个字按切线角旋转)。 · 示例: `annotate_paper_tour`, `paper_figure`
- `annotate_text_path_layout` `text → table` GPU: 无 — 返回表(dict):沿折线逐字的位置与倾角(按弧长确定)。 · 示例: `annotate_paper_tour`

#### annotate / plot (7)
- `axes_frame` `image2d × axes → image2d` GPU: 仅在链中(许可列表) — 坐标轴框(``box=True`` 为四边,False 时只有左边与下边)。 · 示例: `annotate_gallery`, `annotate_paper_tour`, `poc_beam_modal_video`, `poc_camera_calibration`, `poc_camera_shake_deblur`, `poc_crack_width_timeseries`, `poc_dehazing`, `poc_dic_strain`, `poc_driving_decisions`, `poc_driving_traffic`, `poc_focus_stacking`, `poc_interferometry_step`, `poc_measurement_system_analysis`, `poc_moire_alignment`, `poc_motion_magnification`, `poc_panorama_drift`, `poc_particle_tracking`, `poc_photoelasticity`, `poc_pxrd_phase_peel`, `poc_real_sem_metal_layer`, `poc_real_tless_6dof`, `poc_registration_basin`, `poc_river_surface_velocity`, `poc_simcal_thin_film`, `poc_strain_history`, `poc_structure_4d_deterioration`, `poc_superresolution_limits`, `poc_template_tracking`, `poc_timelapse_growth`, `poc_traffic_counting`, `poc_wound_area_tracking`, `poc_xyt_event_surface`
- `axes_transform` `无输入 → axes` GPU: 无 — 构建数据坐标 → 像素坐标的(**闭式**)映射。 · 示例: `annotate_gallery`, `annotate_paper_tour`, `poc_beam_modal_video`, `poc_camera_calibration`, `poc_camera_shake_deblur`, `poc_crack_width_timeseries`, `poc_dehazing`, `poc_dic_strain`, `poc_driving_decisions`, `poc_driving_traffic`, `poc_focus_stacking`, `poc_interferometry_step`, `poc_measurement_system_analysis`, `poc_moire_alignment`, `poc_motion_magnification`, `poc_panorama_drift`, `poc_particle_tracking`, `poc_photoelasticity`, `poc_pxrd_phase_peel`, `poc_real_sem_metal_layer`, `poc_real_tless_6dof`, `poc_registration_basin`, `poc_river_surface_velocity`, `poc_simcal_thin_film`, `poc_strain_history`, `poc_structure_4d_deterioration`, `poc_superresolution_limits`, `poc_template_tracking`, `poc_threshold_transfer_after_normalization`, `poc_timelapse_growth`, `poc_wound_area_tracking`, `poc_xyt_event_surface`
- `data_to_pixel` `axes × signal × signal → pairs` GPU: 仅在链中(许可列表) — 用 :func:`axes_transform` 的映射把数据点映到像素 ``(x, y)``。 · 示例: `annotate_gallery`, `poc_beam_modal_video`, `poc_camera_calibration`, `poc_crack_width_timeseries`, `poc_moire_alignment`, `poc_motion_magnification`, `poc_real_sem_metal_layer`, `poc_real_tless_6dof`, `poc_strain_history`, `poc_structure_4d_deterioration`, `poc_superresolution_limits`, `poc_traffic_counting`, `poc_wound_area_tracking`, `poc_xyt_event_surface`
- `grid_lines` `image2d × axes → image2d` GPU: 有(许可列表) — 网格线。未给出刻度值时由 :func:`nice_ticks` 决定。 · 示例: `annotate_gallery`, `poc_driving_decisions`, `poc_driving_traffic`, `poc_measurement_system_analysis`, `poc_moire_alignment`, `poc_pxrd_phase_peel`, `poc_real_sem_metal_layer`, `poc_real_tless_6dof`
- `nice_ticks` `无输入 → signal` GPU: 无 — 覆盖 [lo, hi] 的「取整」刻度值(1/2/5 × 10^k,**闭式**)。 · 示例: `annotate_gallery`, `poc_dehazing`, `poc_driving_decisions`, `poc_driving_traffic`, `poc_measurement_system_analysis`, `poc_moire_alignment`, `poc_pxrd_phase_peel`, `poc_real_sem_metal_layer`, `poc_simcal_thin_film`
- `plot_series` `image2d × axes × signal × signal → image2d` GPU: 无 — 画折线、散点、柱状。以**数据坐标**接收(像素由 axes 决定)。 · 示例: `annotate_gallery`, `poc_camera_calibration`, `poc_camera_shake_deblur`, `poc_crack_width_timeseries`, `poc_dehazing`, `poc_dic_strain`, `poc_driving_decisions`, `poc_driving_traffic`, `poc_focus_stacking`, `poc_interferometry_step`, `poc_measurement_system_analysis`, `poc_moire_alignment`, `poc_panorama_drift`, `poc_particle_tracking`, `poc_photoelasticity`, `poc_pxrd_phase_peel`, `poc_real_sem_metal_layer`, `poc_real_tless_6dof`, `poc_registration_basin`, `poc_river_surface_velocity`, `poc_simcal_thin_film`, `poc_superresolution_limits`, `poc_template_tracking`, `poc_timelapse_growth`, `poc_wound_area_tracking`
- `ticks` `image2d × axes → image2d` GPU: 无 — 刻度与其数值。**位置为闭式**(就是 :func:`data_to_pixel`)。 · 示例: `annotate_gallery`, `annotate_paper_tour`, `poc_beam_modal_video`, `poc_camera_calibration`, `poc_camera_shake_deblur`, `poc_crack_width_timeseries`, `poc_dehazing`, `poc_dic_strain`, `poc_driving_decisions`, `poc_driving_traffic`, `poc_focus_stacking`, `poc_interferometry_step`, `poc_measurement_system_analysis`, `poc_moire_alignment`, `poc_motion_magnification`, `poc_panorama_drift`, `poc_particle_tracking`, `poc_photoelasticity`, `poc_pxrd_phase_peel`, `poc_real_sem_metal_layer`, `poc_real_tless_6dof`, `poc_registration_basin`, `poc_river_surface_velocity`, `poc_simcal_thin_film`, `poc_strain_history`, `poc_structure_4d_deterioration`, `poc_superresolution_limits`, `poc_template_tracking`, `poc_timelapse_growth`, `poc_traffic_counting`, `poc_wound_area_tracking`, `poc_xyt_event_surface`

#### annotate / pointer (4)
- `arrow` `image2d → image2d` GPU: 有(许可列表) — 从 ``p0`` 到 ``p1`` 的箭头(轴用 :func:`imagedraw.draw_line`,箭头为填充)。 · 示例: `annotate_gallery`, `poc_agv_fleet`, `poc_car_parking`, `poc_diabolo_model_and_vision`, `poc_leak_localization`, `poc_machine_condition_fusion`, `poc_moire_alignment`, `poc_peg_insertion_tactile`, `poc_river_surface_velocity`, `poc_ttc_rss`
- `crosshair` `image2d → image2d` GPU: 有(许可列表) — 断面的交叉线(用于 MPR)。留出 ``gap`` 让中心空出,不遮挡视点。 · 示例: `annotate_gallery`, `poc_air_hockey_intercept`, `poc_ball_bounce`, `poc_kendama`, `poc_table_tennis_bounce`, `poc_ttc_rss`, `poc_world_terrain`
- `label_points` `image2d × pairs → image2d` GPU: 有(许可列表) — 给点群编号或标注。**避开重叠放置**(避不开则抛异常)。 · 示例: `annotate_gallery`
- `leader_line` `image2d × text → image2d` GPU: 无 — 引出线 —— 从注记位置(``anchor_xy``)指向对象(``target_xy``)。 · 示例: `annotate_gallery`, `poc_kendama`

#### annotate / shape (4)
- `arc` `image2d → image2d` GPU: 有(许可列表) — 圆弧。角度以度计,**从屏幕 x 轴顺时针**(因为 row 朝下)。 · 示例: `annotate_gallery`, `poc_mixed_case_depalletizing`, `poc_optics_drawings`, `poc_plenoptic_camera`, `poc_polish_wipe_measure`, `poc_real_walnut_cbct`, `poc_weld_radiograph_porosity`
- `ellipse` `image2d → image2d` GPU: 无 — 椭圆(用 ``angle_deg`` 旋转,``fill=True`` 时填充)。 · 示例: `annotate_gallery`, `poc_camera_calibration`, `poc_dimensional_inspection`, `poc_driving_crossing`, `poc_driving_lateral`, `poc_driving_pass`, `poc_dual_energy_xray`, `poc_interferometry_step`, `poc_machine_condition_fusion`, `poc_mixed_case_depalletizing`, `poc_peg_insertion_tactile`, `poc_polarization_specular`, `poc_public_camera_heading_real`, `poc_real_bg_kalman_tracking`, `poc_real_chessboard_undistort`, `poc_real_file_formats`, `poc_real_sem_metal_layer`, `poc_real_stereo_multiscanline`, `poc_real_tless_6dof`
- `filled_polygon` `image2d × pairs → image2d` GPU: 有(许可列表) — 多边形填充(奇偶交叉规则 —— :mod:`imagedraw` 只画轮廓)。 · 示例: `annotate_gallery`, `poc_driving_decisions`
- `rounded_rect` `image2d → image2d` GPU: 有(许可列表) — 圆角矩形(``fill=True`` 时填充)。用作衬底或外框。 · 示例: `annotate_gallery`, `poc_machine_condition_fusion`

#### annotate / text (2)
- `measure_text` `text → table` GPU: 无 — 在**画之前**先测量文字。放不下就折行或缩小,再不行就抛异常。 · 示例: `annotate_gallery`, `annotate_paper_tour`, `poc_diabolo_model_and_vision`, `poc_interferometry_step`, `poc_nir_silicon_transmission`, `poc_polarization_specular`, `poc_shape_from_polarization`
- `text_box` `image2d × text → image2d` GPU: 仅在链中(许可列表) — 带衬底(半透明板)的文字。**溢出不静默裁切,而是抛异常**。 · 示例: `anim3d_lens_aberrations`, `annotate_gallery`, `annotate_paper_tour`, `drawlist_deferred`, `poc_active_contours`, `poc_agv_fleet`, `poc_air_hockey_intercept`, `poc_ball_bounce`, `poc_beam_modal_video`, `poc_cad_scan_deviation`, `poc_camera_calibration`, `poc_camera_shake_deblur`, `poc_chromatic_confocal`, `poc_code_matching_breakdown`, `poc_connectome_across_worms`, `poc_crack_width_timeseries`, `poc_ct_void_morphology`, `poc_dehazing`, `poc_dem_terrain`, `poc_dense_bubble_count`, `poc_diabolo_model_and_vision`, `poc_dic_strain`, `poc_driving_crossing`, `poc_driving_decisions`, `poc_driving_endless_map`, `poc_driving_lateral`, `poc_driving_longitudinal`, `poc_driving_pass`, `poc_driving_school`, `poc_driving_traffic`, `poc_driving_weather`, `poc_emva1288_sensor`, `poc_eye_to_brain`, `poc_flybrain_pointcloud`, `poc_focus_stacking`, `poc_food_cutting_measure`, `poc_granular_heap_repose`, `poc_graph_hierarchy_segmentation`, `poc_hyperspectral_foreign_matter`, `poc_illumination_cone_vs_na`, `poc_interferometry_step`, `poc_kendama`, `poc_leak_localization`, `poc_lens_merit_operands`, `poc_lens_solves_afocal`, `poc_lidar_terrain_change`, `poc_livestock_body_volume`, `poc_machine_condition_fusion`, `poc_malecns_activity_wave`, `poc_material_optical_library`, `poc_measurement_system_analysis`, `poc_mesh_quality_repair`, `poc_moire_alignment`, `poc_motion_magnification`, `poc_multibeam_bathymetry`, `poc_nir_silicon_transmission`, `poc_noncoaxial_optics`, `poc_panorama_drift`, `poc_particle_tracking`, `poc_peg_failure_recovery`, `poc_peg_insertion_tactile`, `poc_phase_measuring_deflectometry`, `poc_photoelasticity`, `poc_pixel_shift`, `poc_powder_scoop_pour`, `poc_print_warpage_risk`, `poc_pxrd_phase_peel`, `poc_real_sem_metal_layer`, `poc_real_tless_6dof`, `poc_registration_basin`, `poc_river_surface_velocity`, `poc_rotation_invariance_audit`, `poc_rover_slip_risk_path`, `poc_segmentation_gauntlet`, `poc_sem_tem_same_particle`, `poc_simcal_pixel_shift`, `poc_simcal_telecentric`, `poc_simcal_thin_film`, `poc_spectrometer_illumination`, `poc_stockpile_volume`, `poc_strain_history`, `poc_structure_4d_deterioration`, `poc_superresolution_limits`, `poc_swarm_obstacle_from_flow`, `poc_table_tennis_bounce`, `poc_table_tennis_rally_loop`, `poc_table_tennis_spin`, `poc_tacscalib_sphere_lut`, `poc_telecentric_metrology`, `poc_template_tracking`, `poc_thin_film_reflectometry`, `poc_threshold_transfer_after_normalization`, `poc_timelapse_growth`, `poc_traffic_counting`, `poc_ttc_rss`, `poc_video_physics_consistency`, `poc_world_terrain`, `poc_wound_area_tracking`, `poc_xyt_event_surface`, `poc_zebra_stripes_fly_eye`

### gfx2d (44 ops / 9 categories)

#### gfx2d / camera (1)
- `viewport` `rgb → rgb` GPU: 无 — 裁出 ``(x, y, width, height)`` 的矩形并按 ``scale`` 重采样。 · 示例: `gfx2d_scene`, `omni360_roundtrip`

#### gfx2d / colorspace (2)
- `linear_to_srgb` `rgb → rgb` GPU: 有(许可列表) — 把线性光转回 sRGB 编码。:func:`srgb_to_linear` 的精确逆。 · 示例: `gfx2d_scene`, `poc_leaf_disease_area`, `poc_pigment_unmixing`, `poc_white_balance`
- `srgb_to_linear` `rgb → rgb` GPU: 有(许可列表) — 把 sRGB 编码的值转为线性光(IEC 61966-2-1)。 · 示例: `gfx2d_scene`, `poc_leaf_disease_area`, `poc_mixed_case_depalletizing`

#### gfx2d / composite (6)
- `alpha_composite` `rgba × rgba → rgba` GPU: 有(许可列表) — 对直通 alpha 的 ``rgba`` 施加 Porter–Duff 的 **over**(Porter & Duff 1984)。 · 示例: `gfx2d_scene`
- `alpha_composite_premul` `rgba_premul × rgba_premul → rgba_premul` GPU: 仅在链中(许可列表) — 预乘颜色上的 Porter–Duff **over**:``src + dst*(1 - src.a)``。 · 示例: `gfx2d_scene`
- `blend_mode` `rgb × rgb → rgb` GPU: 有(许可列表) — 用指定的混合模式合成两张不透明 ``rgb`` 图(W3C Level 1)。 · 示例: `genspark_external_review`, `gfx2d_scene`
- `layer_stack` `table → rgba` GPU: 无 — 按 z 序合成一列 ``rgba`` 图层,自下而上。 · 示例: `gfx2d_scene`
- `premultiply` `rgba → rgba_premul` GPU: 仅在链中(许可列表) — 直通 alpha 的 ``rgba`` → **预乘** ``rgba``:``(C*A, A)``。 · 示例: `gfx2d_scene`
- `unpremultiply` `rgba_premul → rgba` GPU: 无 — **预乘**的 ``rgba`` → 直通 alpha:``(C/A, A)``。 · 示例: `gfx2d_scene`

#### gfx2d / isp (12)
- `awb_gains` `rgb → vector` GPU: 仅在链中(许可列表) — 估计白平衡增益 (g_R, g_G, g_B)(gray-world / white-patch,g_G = 1)。 · 示例: `raw_to_display_isp`
- `brightness_contrast` `rgb → rgb` GPU: 仅在链中(许可列表) — out = (rgb − 0.5) · contrast + 0.5 + brightness,裁剪到 [0, 1]。 · 示例: `raw_to_display_isp`
- `color_correction_matrix` `rgb × matrix → rgb` GPU: 无 — 逐像素应用 3x3 色彩校正矩阵(默认行归一化为 1,白保持白)。 · 示例: `raw_to_display_isp`
- `hue_saturation` `rgb → rgb` GPU: 有(许可列表) — 旋转色相并缩放饱和度(BT.601 YCbCr,保持亮度)。 · 示例: `raw_to_display_isp`
- `lens_shading_correct` `image2d × image2d → image2d` GPU: 无 — 将增益图乘到帧上并裁剪到 [0, 1]。 · 示例: `poc_tdi_linescan`, `raw_to_display_isp`
- `lens_shading_gain` `image2d → image2d` GPU: 仅在链中(许可列表) — 由平场(白板)生成抵消暗角的增益图:逐通道 mean / flat。 · 示例: `poc_tdi_linescan`, `raw_to_display_isp`
- `raw_apply_gains` `image2d × vector → image2d` GPU: 仅在链中(许可列表) — 对 Bayer 帧逐通道乘以增益(去马赛克前的白平衡)。 · 示例: `raw_to_display_isp`
- `raw_black_level` `image2d → image2d` GPU: 无 — Bayer 帧的黑电平校正:逐通道 (raw − offset) / (white − offset)。 · 示例: `raw_to_display_isp`
- `raw_dead_pixel_correct` `image2d → image2d` GPU: 有(许可列表) — 用同色 8 邻域的中位数替换坏点,其余像素原样保留。 · 示例: `raw_to_display_isp`
- `raw_dead_pixel_mask` `image2d → image2d` GPU: 无 — 坏点图:与全部 8 个同色邻域朝同一方向偏离超过阈值的像素。 · 示例: `raw_to_display_isp`
- `raw_demosaic_bilinear` `image2d → rgb` GPU: 有(许可列表) — 用纯 NumPy 的双线性插值把 Bayer 马赛克变成 (H, W, 3) RGB。 · 示例: `poc_pixel_shift`, `raw_to_display_isp`
- `rgb_apply_gains` `rgb × vector → rgb` GPU: 仅在链中(许可列表) — 对 R、G、B 各通道乘以增益并裁剪到 [0, 1]。 · 示例: `gallery_mesh_seg_sun_gains`

#### gfx2d / light (5)
- `light_mask` `rgb × rgb → rgb` GPU: 仅在链中(许可列表) — 用 ``rgb`` 光照图调制 ``rgb`` 图像:``base * (ambient + light)``。 · 示例: `gfx2d_scene`
- `normal_map_decode` `rgb → normalmap` GPU: 有(许可列表) — 把 ``[0, 1]`` 的切空间法线贴图 ``rgb`` 转为单位向量 ``(H, W, 3)``。 · 示例: `gfx2d_scene`
- `normal_map_shade` `normalmap → rgb` GPU: 无 — 用一盏平行光给 2-D 法线贴图着色(Lambert + Blinn 1977)。 · 示例: `gfx2d_scene`
- `radial_light` `无输入 → rgb` GPU: 无 — 以 ``(x, y)`` 为中心的放射状光照图 ``rgb`` ``(H, W, 3)``。 · 示例: `gfx2d_scene`
- `shadow_cast_2d` `image2d → image2d` GPU: 无 — 每个像素相对 ``(x, y)`` 点光源的可见性,作为 ``image2d``。 · 示例: `gfx2d_scene`

#### gfx2d / particle (3)
- `particle_emit` `无输入 → table` GPU: 无 — 从 ``origin`` 发射 ``count`` 个粒子,由 ``seed`` 决定性生成。 · 示例: `gfx2d_scene`
- `particle_render` `table → rgba` GPU: 无 — 把粒子状态 splat 到 ``rgba`` 图像上。 · 示例: `gfx2d_scene`
- `particle_step` `table → table` GPU: 无 — 把粒子状态推进 ``dt`` 秒。返回**新的** dict。 · 示例: `gfx2d_scene`

#### gfx2d / post (8)
- `bloom` `rgb → rgb` GPU: 有(许可列表) — 让图像的明亮部分向周围渗出。 · 示例: `gfx2d_scene`, `poc_public_camera_heading_real`
- `chromatic_aberration` `rgb → rgb` GPU: 有(许可列表) — 以图像中心为基准缩放红、蓝通道,绿通道保持不变。 · 示例: `gfx2d_scene`
- `color_grade` `rgb × lut → rgb` GPU: 有(许可列表) — 用三线性插值把 3-D 色彩 LUT 应用到 ``rgb`` 图像。 · 示例: `gfx2d_scene`
- `color_lut` `无输入 → lut` GPU: 无 — 构建 3-D 色彩 LUT ``(n, n, n, 3)``,索引为 ``[r, g, b]``。 · 示例: `genspark_external_review`, `gfx2d_scene`
- `dither` `image2d → image2d` GPU: 有(许可列表) — 在保持局部均值的前提下,把每通道量化到 ``levels`` 个取值。 · 示例: `gfx2d_scene`
- `film_grain` `rgb → rgb` GPU: 无 — 加入零均值的高斯颗粒,由 ``seed`` 决定性生成。 · 示例: `gfx2d_scene`
- `palette_quantize` `rgb → rgb` GPU: 有(许可列表) — 把每个像素映射到 RGB 欧氏距离最近的调色板颜色。 · 示例: `gfx2d_scene`
- `vignette` `rgb → rgb` GPU: 有(许可列表) — 向四角变暗:``out = rgb * (1 - strength * t**power)``。 · 示例: `gfx2d_scene`, `poc_search_sweep_width`, `poc_solar_el_inspection`

#### gfx2d / sprite (5)
- `nine_slice` `rgba → rgba` GPU: 有(许可列表) — 把边框拉伸到新尺寸而不变形四角。 · 示例: `gfx2d_scene`
- `sprite_blit` `rgba × rgba → rgba` GPU: 有(许可列表) — 在 ``dst`` 的副本上于整数 ``(x, y)`` 处合成 ``sprite``。 · 示例: `gfx2d_scene`
- `sprite_sheet_slice` `rgba → sprites` GPU: 无 — 把精灵图集切成等大的 ``rgba`` 帧列表,行优先。 · 示例: `gfx2d_scene`
- `sprite_synthesize` `无输入 → rgba` GPU: 无 — 确定性的抗锯齿测试精灵 ``rgba`` ``(size, size, 4)``。 · 示例: `gfx2d_scene`
- `sprite_transform` `rgba → rgba` GPU: 无 — 绕中心旋转和/或缩放 ``rgba`` 精灵。 · 示例: `gfx2d_scene`

#### gfx2d / tile (2)
- `parallax_layers` `sprites → rgba` GPU: 无 — 让一组 ``rgba`` 图层以不同速度滚动并合成。 · 示例: `gfx2d_scene`
- `tilemap_render` `sprites → rgba` GPU: 无 — 把一张瓦片索引网格绘制成一幅 ``rgba`` 图像。 · 示例: `gfx2d_scene`

### multivar (18 ops / 6 categories)

#### multivar / analysis (4)
- `doe_main_effects` `design × signal → table` GPU: 无 — 各因子的水平均值（设计实验的响应表），附离散度与 SN 比。 · 示例: `multivar_inspection_tour`
- `mv_pca` `matrix → table` GPU: 无 — 表（样本 x 变量）的主成分，以及数据所支持的成分个数。 · 示例: `multivar_inspection_tour`, `poc_simcal_thin_film`
- `mv_pls` `matrix × signal → table` GPU: 无 — Y 对 X 的偏最小二乘回归，附交叉验证 Q^2、Q^2 成分数规则与 VIP。 · 示例: `multivar_inspection_tour`
- `rsm_fit` `design × signal → table` GPU: 无 — 在 ``design``（编码单位）上拟合响应曲面：方差分析、失拟检验、驻点。 · 示例: `multivar_inspection_tour`

#### multivar / coding (2)
- `doe_decode` `design → matrix` GPU: 无 — ``design`` -> 自然单位矩阵 (n, k)；也可用其范围将任意编码点还原。 · 示例: `doe_plan_tour`, `multivar_inspection_tour`, `poc_simcal_thin_film`, `sensitivity_tour`
- `doe_encode` `matrix → design` GPU: 无 — 自然单位的设定值 (n, k) -> 带编码值（−1..+1 = lo..hi）的 ``design``。 · 示例: `multivar_inspection_tour`

#### multivar / features (1)
- `feat_image_vector` `images → table` GPU: 有(许可列表) — 图像 -> 特征表 ``{"matrix" (N, F), "names", "units", ...}``，每幅图像一行。 · 示例: `multivar_inspection_tour`

#### multivar / identifiability (2)
- `mv_confounding` `matrix → table` GPU: 无 — 共线性指数 gamma_K（Brun、Reichert 与 Künsch 2001）：数据能确定哪些参数。 · 示例: `poc_simcal_thin_film`, `sensitivity_tour`
- `mv_residual_pca` `matrix → table` GPU: 无 — 拟合模型的残差中是否仍有结构？残差矩阵的 PCA 与噪声比较。 · 示例: `sensitivity_tour`

#### multivar / plan (5)
- `doe_box_behnken` `无输入 → design` GPU: 无 — Box-Behnken 设计（Box 与 Behnken 1960，3、4 或 5 个因子）-> ``design``。 · 示例: `doe_plan_tour`
- `doe_central_composite` `无输入 → design` GPU: 无 — 中心复合设计（Box 与 Wilson 1951）-> ``design``。 · 示例: `doe_plan_tour`, `multivar_inspection_tour`
- `doe_fractional_factorial` `无输入 → design` GPU: 无 — 由生成元构造的二水平正则部分因子设计 2^(k-p)（Box 与 Hunter 1961）-> ``design``。 · 示例: `doe_plan_tour`
- `doe_lhs` `无输入 → design` GPU: 无 — 拉丁超立方设计（McKay、Beckman 与 Conover 1979）-> ``design``。 · 示例: `doe_plan_tour`, `multivar_inspection_tour`, `sensitivity_tour`, `simcal_checks_tour`
- `doe_orthogonal_array` `无输入 → design` GPU: 无 — 正交表 L4 / L8 / L9 / L12 / L16 / L18 / L27（照录自公开发表的表）-> ``design``。 · 示例: `doe_plan_tour`, `multivar_inspection_tour`, `poc_simcal_thin_film`

#### multivar / sensitivity (4)
- `doe_morris` `无输入 → design` GPU: 无 — Morris 一次一因子筛选设计：``r`` 条各含 k+1 次运行的轨迹 -> ``design``。 · 示例: `sensitivity_tour`
- `doe_saltelli` `无输入 → design` GPU: 无 — 用于 Sobol' 指数的样本矩阵（Saltelli 等 2010）-> 共 n (k + 2) 次运行的 ``design``。 · 示例: `sensitivity_tour`
- `sens_morris` `design × signal → table` GPU: 无 — Morris 基本效应 -> 各因子的 mu、mu*、sigma（Morris 1991；mu* 见 Campolongo 等 2007）。 · 示例: `sensitivity_tour`
- `sens_sobol` `design × signal → table` GPU: 无 — 一阶与总效应 Sobol' 指数，附自助法置信区间。 · 示例: `sensitivity_tour`

### simcal (10 ops / 4 categories)

#### simcal / check (4)
- `simcal_discrepancy` `calresult → calresult` GPU: 无 — 噪声归一化的残差中是否存在模型无法产生的结构（模型偏差）？ · 示例: `poc_pocket_interreflection`, `poc_simcal_pixel_shift`, `poc_simcal_telecentric`, `poc_simcal_thin_film`, `simcal_checks_tour`
- `simcal_identifiability` `calresult → calresult` GPU: 无 — 每个已拟合旋钮的 Fisher 信息、Cramér-Rao 下界、相关性、共线性与剖面似然。 · 示例: `poc_simcal_pixel_shift`, `poc_simcal_telecentric`, `poc_simcal_thin_film`, `simcal_checks_tour`
- `simcal_uncertainty` `calresult → calresult` GPU: 无 — 已确定旋钮的标准差与区间：Laplace（Fisher 信息之逆）或参数自助法。 · 示例: `poc_simcal_thin_film`
- `simcal_validate` `calresult × simmodel → calresult` GPU: 无 — 在保留图像上的过拟合闸门；任一失败即拒绝该标定（撤回估计值）。 · 示例: `poc_pocket_interreflection`, `poc_simcal_pixel_shift`, `poc_simcal_telecentric`, `poc_simcal_thin_film`, `simcal_checks_tour`

#### simcal / fit (2)
- `simcal_fit` `simmodel → calresult` GPU: 无 — 将带观测的 simmodel 的自由旋钮拟合到其图像（加权最小二乘）-> ``calresult``。 · 示例: `poc_pocket_interreflection`, `poc_simcal_pixel_shift`, `poc_simcal_telecentric`, `poc_simcal_thin_film`, `simcal_checks_tour`, `simcal_tour`
- `simcal_screen` `simmodel → table` GPU: 无 — 哪些旋钮能使图像变化超过相机噪声、哪些相互混杂、输出有多少个独立方向。 · 示例: `poc_simcal_pixel_shift`, `poc_simcal_telecentric`, `poc_simcal_thin_film`, `simcal_tour`

#### simcal / model (3)
- `simcal_model` `无输入 → simmodel` GPU: 无 — 构建 ``simmodel``：参数为旋钮（带单位与范围）的算子正向链，以及噪声模型。 · 示例: `poc_pocket_interreflection`, `poc_simcal_pixel_shift`, `poc_simcal_telecentric`, `poc_simcal_thin_film`, `simcal_checks_tour`, `simcal_tour`
- `simcal_observe` `simmodel × images → simmodel` GPU: 无 — 将实测图像附加到 simmodel：配准、感兴趣区域与曝光归一化。 · 示例: `poc_pocket_interreflection`, `poc_simcal_pixel_shift`, `poc_simcal_telecentric`, `poc_simcal_thin_film`, `simcal_checks_tour`, `simcal_tour`
- `simcal_simulate` `simmodel → images` GPU: 无 — 按给定旋钮值运行 simmodel 的链 -> 每个条件一个二维数组（``images``）。 · 示例: `poc_pocket_interreflection`, `poc_simcal_pixel_shift`, `poc_simcal_thin_film`, `simcal_checks_tour`, `simcal_tour`

#### simcal / report (1)
- `simcal_report` `calresult → table` GPU: 无 — 标定一览表：各旋钮的值、单位、区间与类别，各闸门，以及拒绝理由。 · 示例: `poc_simcal_thin_film`, `simcal_checks_tour`

### converge (6 ops / 4 categories)

#### converge / iterate (1)
- `iterate_fixed_point` `无输入 → table` GPU: 无 — 用不动点迭代（普通迭代 / Aitken / Anderson）求解 x = g(x)，不收敛时拒绝而不返回值。 · 示例: `converge_tour`

#### converge / montecarlo (2)
- `mc_photon_slab` `无输入 → table` GPU: 无 — 用 MCML 型蒙特卡罗计算多层浑浊平板的漫反射、总透射和吸收，并给出置信区间。 · 示例: `converge_tour`
- `mc_sequential_mean` `无输入 → table` GPU: 无 — 序贯蒙特卡罗均值：不断加样本，直到置信区间窄于容许值。

#### converge / stopping (1)
- `iv_richardson_lucy_until` `image2d → table` GPU: 无 — 按偏差原理停止的 Richardson-Lucy 反卷积（泊松：Bertero 2010，τ = 1；高斯：Morozov）；拒绝模型值域之外的数据。 · 示例: `converge_tour`

#### converge / verification (2)
- `conv_gci` `无输入 → table` GPU: 无 — 最细解的网格收敛指数 GCI：Celik 等 2008 的步骤（式 1–7）。 · 示例: `converge_tour`
- `conv_observed_order` `无输入 → table` GPU: 无 — 由三个系统加密的解求表观收敛阶 p（Celik 等 2008，式 3）。

### codematch (6 ops / 3 categories)

#### codematch / change (1)
- `radial_reach_filter` `image2d × image2d → table` GPU: 有(许可列表) — Radial Reach Filter（RRF）：用 8 个方向的 reach 符号比较背景与当前图像。 · 示例: `poc_code_matching_breakdown`

#### codematch / code (2)
- `increment_sign` `image2d → image2d` GPU: 无 — 与相邻像素的增量符号 ``b = [I(下一个) >= I(当前)]``（1 / 0 的 uint8）。
- `orientation_code` `image2d → image2d` GPU: 有(许可列表) — 将梯度方向量化为 ``n_codes`` 级的方向码图像（OCM 的编码）。

#### codematch / match (3)
- `isc_match` `image2d × image2d → table` GPU: 无 — 增量符号相关（ISC）：返回增量符号一致比例最大的位置。 · 示例: `poc_code_matching_breakdown`
- `ocm_match` `image2d × image2d → table` GPU: 无 — 方向码匹配（OCM）：返回码的循环差平均值最小的位置。 · 示例: `poc_code_matching_breakdown`
- `scc_match` `image2d × image2d → table` GPU: 无 — 选择性相关系数（SCC）：只用增量符号一致的像素计算归一化相关。 · 示例: `poc_code_matching_breakdown`

### aoi (8 ops / 4 categories)

#### aoi / aggregate (1)
- `tiled_map` `image2d → table` GPU: 无 — 将图像划分为图块，把每个图块的统计量做成一张小地图。→ dict。 · 示例: `aoi_frontend_tour`

#### aoi / geometric (1)
- `register_image` `image2d × image2d → table` GPU: 无 — 返回将检测图像对齐到基准图像的平移量，并附带能看出对不上的指标。→ dict。 · 示例: `aoi_frontend_tour`, `poc_multimodal_mi_registration`

#### aoi / photometric (1)
- `flat_field_correct` `image2d × image2d → image2d` GPU: 无 — 通过扣除暗电流后的除法，校正照明不均与传感器灵敏度的差异。→ 校正后的图像。 · 示例: `aoi_frontend_tour`

#### aoi / symmetry (5)
- `center_from_symmetric_edges` `image2d → table` GPU: 无 — 稳健汇总对称外缘对的中点，返回二维中心。 · 示例: `poc_symmetry_self_reference_inspection`
- `reflection_axis` `image2d → table` GPU: 无 — 估计线对称二维图像的反射轴角度与偏移。
- `rotational_symmetry` `image2d → table` GPU: 无 — 返回180度点对称中心及由极坐标自相关得到的旋转对称阶数。 · 示例: `poc_symmetry_self_reference_inspection`
- `symmetry_difference_map` `image2d × table → image2d` GPU: 无 — 返回相对于估计反射轴或旋转中心的自参考差分图。 · 示例: `poc_symmetry_self_reference_inspection`
- `symmetry_score` `image2d × table → measurement` GPU: 无 — 以图像动态范围归一化自参考差分，返回到对称状态的距离。 · 示例: `poc_symmetry_self_reference_inspection`

### matchreg (12 ops / 2 categories)

#### matchreg / featmatch (6)
- `features_accuracy_table` `image2d → table` GPU: 无 — 在用已知变换合成的图像对上,按条件以表格返回特征点重复率、匹配精度与单应误差。→ table。 · 示例: `poc_part_locate_features`
- `features_match` `table × table → table` GPU: 无 — 用最近邻 + 比率检验(+ 互为最近邻)匹配两个特征表。→ table(``kind="feature_matches"``)。 · 示例: `poc_part_locate_features`
- `features_orb` `image2d → table` GPU: 无 — ORB 特征点与 256 位二值描述子(Rublee et al. 2011)。→ table(``kind="features"``)。 · 示例: `poc_part_locate_features`
- `features_sift` `image2d → table` GPU: 无 — SIFT 特征点与 128 维描述子(DoG 极值,Lowe 2004)。→ table(``kind="features"``)。 · 示例: `poc_part_locate_features`
- `ransac_fundamental` `table → table` GPU: 无 — 从匹配对稳健地估计基础矩阵 F(``x2ᵀ F x1 = 0``)。→ table(``kind="fundamental"``)。
- `ransac_homography` `table → table` GPU: 无 — 从匹配对稳健地估计单应矩阵(pts1 → pts2,(x, y) 的齐次坐标)。→ table(``kind="homography"``)。 · 示例: `poc_part_locate_features`

#### matchreg / intensityreg (6)
- `register_accuracy_map` `image2d × flow2d → table` GPU: 无 — 在用已知形变场合成的图像对上,逐像素返回估计形变场的误差(精度图)。→ table。 · 示例: `poc_sheet_deformation_ffd`
- `register_capture_range` `image2d → table` GPU: 无 — 按初始偏移的大小,返回从恒等变换出发的配准回到真值的比例(收敛范围)。→ table。
- `register_ecc` `image2d × image2d → table` GPU: 无 — 用使增强相关系数(ECC)最大的参数变换将 moving 对齐到 fixed。→ table(``kind="registration"``)。 · 示例: `poc_multimodal_mi_registration`
- `register_ffd` `image2d × image2d → table` GPU: 无 — 用三次 B 样条自由形变(FFD)将 moving 非刚性地对齐到 fixed。→ table(``kind="registration"``)。 · 示例: `poc_sheet_deformation_ffd`
- `register_mi` `image2d × image2d → table` GPU: 无 — 用使(归一化)互信息最大的刚体 / 相似 / 仿射变换将 moving 对齐到 fixed。→ table(``kind="registration"``)。 · 示例: `poc_multimodal_mi_registration`
- `registration_to_flow2d` `table → flow2d` GPU: 无 — 从配准结果表中取出形变场 ``flow2d``((2,H,W) 的 ``(dy, dx)``)。→ flow2d。 · 示例: `poc_sheet_deformation_ffd`

### calib (29 ops / 7 categories)

#### calib / calib_truth (3)
- `calibration_error_map` `table → table` GPU: 无 — 比较真实的 K、畸变与估计值,返回图像中重投影误差(px)与 3D 误差(mm)较大位置的分布图(``table``)。 · 示例: `poc_calibration_truth_map`
- `calibration_next_pose` `table → table` GPU: 无 — 在候选的板位姿中推荐加入后最能降低标定不确定度(全图平均)的一张(``table``)。 · 示例: `poc_calibration_truth_map`
- `calibration_uncertainty_map` `table → table` GPU: 无 — 将标定估计的协方差映射到图像上,返回每个像素的预测不确定度(px,给定深度 Z 时为 mm)的分布图(``table``)。 · 示例: `poc_calibration_truth_map`

#### calib / calibrate (5)
- `camera_calibration` (halcon: `camera_calibration`) `keypoints → table` GPU: 无 — [部分对应] 用 Zhang 法从平面靶标的多个视角只估计内参矩阵 K(camera_calibration)。 · 示例: `camera_intrinsics_calibration`, `lens_calibration_loop_demo`, `poc_calibration_truth_map`, `poc_camera_calibration`
- `camera_calibration_lm` `keypoints → table` GPU: 无 — 从 Zhang 法的初值出发,用 LM 同时优化内参、畸变与全部位姿,并连同协方差一起返回(``table``)。 · 示例: `poc_calibration_truth_map`, `poc_caltab_chain_truth`, `poc_real_chessboard_undistort`
- `find_marks_and_pose` (halcon: `find_marks_and_pose`) `image2d → table` GPU: 无 — 标记检测 + 标定板位姿估计(平面单应 → 位姿)(find_marks_and_pose)。 · 示例: `poc_caltab_chain_truth`
- `hand_eye_calibration` (halcon: `hand_eye_calibration`) `无输入 → matrix` GPU: 无 — 由一系列运动对求解 AX=XB，估计 X(4x4)(hand_eye_calibration)。
- `stereo_calibration_lm` `keypoints → table` GPU: 无 — 用 LM 同时优化左右相机的内参与畸变、板的位姿以及右相机的相对位姿 (R, T)(``table``)。

#### calib / checkerboard (3)
- `checkerboard_points` `无输入 → keypoints` GPU: 无 — 按行优先顺序返回棋盘格内角点的板坐标 (x, y)(``keypoints``)。 · 示例: `poc_calibration_truth_map`
- `find_checkerboard_corners` `image2d → keypoints` GPU: 无 — 以亚像素精度检测棋盘格图像的内角点,并按板的行优先顺序返回(``keypoints``)。 · 示例: `poc_calibration_truth_map`
- `sim_checkerboard` `无输入 → table` GPU: 无 — 用已知的 K、畸变与位姿合成棋盘格图像,并连同各角点的真实像素一起返回(``table``)。 · 示例: `poc_calibration_truth_map`

#### calib / fit (4)
- `hom_vector_to_proj_hom_mat2d` (halcon: `hom_vector_to_proj_hom_mat2d`) `keypoints → matrix` GPU: 无 — 由 4 个以上对应求射影变换(单应, DLT)3x3(hom_vector_to_proj_hom_mat2d)。 · 示例: `poc_panorama_drift`, `poc_wound_area_tracking`
- `vector_angle_to_rigid` (halcon: `vector_angle_to_rigid`) `无输入 → matrix` GPU: 无 — 由一组 (点, 角度) 求 2D 刚体变换(vector_angle_to_rigid)。
- `vector_to_rigid` (halcon: `vector_to_rigid`) `keypoints → matrix` GPU: 无 — 由对应点求 2D 刚体变换(旋转+平移, Kabsch)(vector_to_rigid)。
- `vector_to_similarity` (halcon: `vector_to_similarity`) `keypoints → matrix` GPU: 无 — 由对应点求 2D 相似变换(旋转+尺度+平移, Umeyama)(vector_to_similarity)。 · 示例: `poc_document_scan`, `poc_star_astrometry`

#### calib / plane (5)
- `contour_to_world_plane_xld` (halcon: `contour_to_world_plane_xld`) `table → table` GPU: 无 — 把 XLD 轮廓(dict {cs:[Nx2]})映射到世界平面(contour_to_world_plane_xld)。 · 示例: `poc_wound_area_tracking`
- `gen_image_to_world_plane_map` (halcon: `gen_image_to_world_plane_map`) `无输入 → table` GPU: 无 — 生成 图像→世界平面(z=0)的映射表(gen_image_to_world_plane_map)。
- `gen_radial_distortion_map` (halcon: `gen_radial_distortion_map`) `无输入 → table` GPU: 无 — 生成径向畸变的逆映射(row_map, col_map)(gen_radial_distortion_map)。
- `image_points_to_world_plane` (halcon: `image_points_to_world_plane`) `table → keypoints` GPU: 无 — 由相机内参/外参将像素反投影到世界平面 z=0(image_points_to_world_plane)。
- `image_to_world_plane` `keypoints → keypoints` GPU: 无 — 用平面单应把图像点映射到世界平面(z=0)(image_to_world_plane)。 · 示例: `poc_document_scan`, `poc_matrix_code_reading`, `poc_wound_area_tracking`

#### calib / project (3)
- `project_3d_point` (halcon: `project_3d_point`) `points → keypoints` GPU: 无 — 将 3D 点透视投影到相机，返回像素 (row, col)(project_3d_point)。
- `project_hom_point_hom_mat3d` (halcon: `project_hom_point_hom_mat3d`) `matrix → keypoints` GPU: 无 — 用 3x4/4x4 投影矩阵投影齐次 3D 点 (4,)，返回像素 (row, col)(project_hom_point_hom_mat3d)。
- `project_point_hom_mat3d` (halcon: `project_point_hom_mat3d`) `points → keypoints` GPU: 无 — 用 4x4 或 3x4 投影矩阵 P=K[R|t] 投影 3D 点，返回像素 (row, col)(project_point_hom_mat3d)。

#### calib / target (6)
- `caltab_points` (halcon: `caltab_points`) `无输入 → keypoints` GPU: 无 — 以 (y, x) 返回标定板的理想标记坐标(世界坐标, mm; 原点=第一个标记)(caltab_points)。
- `create_caltab` (halcon: `create_caltab`) `无输入 → table` GPU: 无 — 生成标定板的描述(理想点，原点在板中心)(create_caltab)。 · 示例: `poc_caltab_chain_truth`
- `disp_caltab` (halcon: `disp_caltab`) `table → image2d` GPU: 无 — 返回标定板图像(用于显示)(disp_caltab)。
- `find_caltab` (halcon: `find_caltab`) `image2d → keypoints` GPU: 无 — 从图像中检测标定板圆形标记的中心(连通域的重心)(find_caltab)。 · 示例: `poc_caltab_chain_truth`
- `gen_caltab` (halcon: `gen_caltab`) `无输入 → table` GPU: 无 — 生成圆形标记网格的标定板图像(gen_caltab)。
- `sim_caltab` (halcon: `sim_caltab`) `table → table` GPU: 无 — 模拟按指定相机位姿投影的标定板图像(sim_caltab)。

### acceptance (8 ops / 4 categories)

#### acceptance / budget (1)
- `acceptance_error_budget` `table × table × table → table` GPU: 无 — 每次只加入一个误差因素运行虚拟验收试验,返回哪个因素决定了合格与否(``table``)。 · 示例: `poc_virtual_acceptance_3d`

#### acceptance / evaluate (4)
- `acceptance_verdict` `table × table → table` GPU: 无 — 将评价量的表与 MPE(最大允许误差)比较并给出合格与否(``table``)。
- `plane_flatness_error` `points → table` GPU: 无 — 由平面的点云计算平面度误差 F(到最小二乘平面的带符号距离的极差)(``table``)。 · 示例: `poc_3d_sensor_modalities`
- `sphere_probing_error` `points → table` GPU: 无 — 由球的点云计算探测误差的形状 PF 与尺寸 PS(``table``)。 · 示例: `poc_3d_sensor_modalities`
- `sphere_spacing_error` `points × points → table` GPU: 无 — 由球杆(两个球)的点云计算球间距误差 SD(``table``)。 · 示例: `poc_3d_sensor_modalities`

#### acceptance / layout (1)
- `acceptance_layout` `无输入 → table` GPU: 无 — 在测量体积中生成试验件的布置(1 个探测球、7 个姿态的球杆、7 个姿态的平面)(``table``)。 · 示例: `poc_virtual_acceptance_3d`

#### acceptance / simulate (2)
- `acceptance_scan` `table × table → points` GPU: 无 — 用仿真传感器拍摄一个试验件并返回其点云 ``(N, 3)``(``points``)。 · 示例: `poc_virtual_acceptance_3d`
- `virtual_acceptance_test` `table → table` GPU: 无 — 用仿真传感器拍摄试验件的全部布置,返回 PF、PS、SD、F 与合格与否(``table``)。 · 示例: `poc_virtual_acceptance_3d`

### symbol (33 ops / 7 categories)

#### symbol / barcode1d (5)
- `barcode_scan_profiles` `image2d → table` GPU: 无 — 从图像中提取 ``n_lines`` 条垂直于条的平行扫描线(`table`)。 · 示例: `poc_symbol_package_1d`
- `decode_barcode_profile` `signal → table` GPU: 无 — 从一条扫描线(反射率的一维序列)解码一个符号(`table`)。 · 示例: `poc_symbol_package_1d`
- `ean_check_digit` `无输入 → scalar` GPU: 无 — EAN/UPC 校验位(从最右位起权重 3、1、3…,使总和为 10 的倍数)。 · 示例: `poc_symbol_package_1d`
- `encode_barcode1d` `无输入 → table` GPU: 无 — 将字符串编码为一维条码的元素宽度(以模块为单位)(`table`)。 · 示例: `poc_symbol_package_1d`
- `read_barcode1d` `image2d → table` GPU: 无 — 从图像读取一维条码(`table`)。 · 示例: `poc_symbol_package_1d`

#### symbol / datacode2d (10)
- `dm_decode_modules` `matrix → table` GPU: 无 — 解码 Data Matrix 模块网格(含 L 形寻像图形和时钟轨,0/1)并返回纠正码字数(`table`)。 · 示例: `poc_symbol_part_dpm`
- `dm_encode` `无输入 → table` GPU: 无 — 将字符串编码为 Data Matrix ECC200 的模块网格及模块到码字的对应(`table`)。 · 示例: `poc_symbol_part_dpm`
- `dm_locate` `image2d → table` GPU: 无 — 在图像中找到 Data Matrix 并估计模块空间到图像的单应变换(`table`)。 · 示例: `poc_symbol_part_dpm`
- `dm_read` `image2d → table` GPU: 无 — 从图像读取 Data Matrix:定位 → 采样 → 解码,反转明暗重试(`table`)。 · 示例: `poc_symbol_part_dpm`
- `dm_sample` `image2d → table` GPU: 无 — 用双线性插值采样 Data Matrix 模块中心的反射率,并以全局阈值二值化(`table`)。 · 示例: `poc_symbol_part_dpm`
- `qr_decode_modules` `matrix → table` GPU: 无 — 解码 QR 模块网格(无静区,1 = 暗)并返回每个块的纠正码字数(`table`)。 · 示例: `poc_symbol_part_dpm`
- `qr_encode` `无输入 → table` GPU: 无 — 将字符串编码为 QR Code(Model 2)的模块网格及模块到码字的对应(`table`)。 · 示例: `poc_symbol_part_dpm`
- `qr_locate` `image2d → table` GPU: 无 — 在图像中找到 QR 码并估计模块空间到图像的单应变换(`table`)。 · 示例: `poc_symbol_part_dpm`
- `qr_read` `image2d → table` GPU: 无 — 从图像读取 QR 码:定位 → 采样 → 解码,失败时反转明暗重试(`table`)。 · 示例: `poc_symbol_part_dpm`
- `qr_sample` `image2d → table` GPU: 无 — 用双线性插值采样 QR 模块中心的反射率,并以全局阈值二值化(`table`)。 · 示例: `poc_symbol_part_dpm`

#### symbol / ocr (9)
- `ocr_classify` `matrix × table → table` GPU: 无 — 用 k 近邻识别特征,并按距离与距离比拒识(`table`)。 · 示例: `poc_symbol_lot_ocr`
- `ocr_features` `image2d → signal` GPU: 无 — 由单个字的墨迹图生成 88 维特征(分区密度 + 投影)(`signal`)。 · 示例: `poc_symbol_lot_ocr`
- `ocr_font` `无输入 → table` GPU: 无 — 返回内置字体(5x7 点阵 / 笔画)的字符集与字形设计(`table`)。 · 示例: `poc_symbol_lot_ocr`
- `ocr_read_line` `image2d × table → table` GPU: 无 — 读取图像中的一行:切分 + 识别,拒识的字符记为 ``?``(`table`)。 · 示例: `poc_symbol_lot_ocr`
- `ocr_read_trials` `table → table` GPU: 无 — 在每个退化水平下对印刷字符串拍摄 ``trials`` 次并用 OCR 读取,返回每次一行的表(`table`)。 · 示例: `poc_symbol_lot_ocr`
- `ocr_render_text` `无输入 → table` GPU: 无 — 用内置字体绘制字符串,并连同每个字符的真实外接框一起返回(`table`)。 · 示例: `poc_symbol_lot_ocr`
- `ocr_score` `无输入 → table` GPU: 无 — 用 Levenshtein 对齐将读取结果与真值评分,误读与拒识分别计数(`table`)。 · 示例: `poc_symbol_lot_ocr`
- `ocr_segment_line` `image2d → table` GPU: 无 — 将一行文字切分为每个字符的外接框(`table`)。 · 示例: `poc_symbol_lot_ocr`
- `ocr_train` `无输入 → table` GPU: 无 — 在扰动下绘制字体,收集模板(特征 + 标签)与拒识阈值(`table`)。 · 示例: `poc_symbol_lot_ocr`

#### symbol / print_quality (3)
- `grade_barcode1d` `image2d → table` GPU: 无 — 返回图像中一维符号的印刷质量等级(``n_scans`` 条扫描线的平均)(`table`)。 · 示例: `poc_symbol_package_1d`
- `grade_barcode_profile` `signal → table` GPU: 无 — 返回一条扫描线(反射率的一维序列)的印刷质量参数与等级(`table`)。 · 示例: `poc_symbol_package_1d`
- `grade_datacode2d` `image2d → table` GPU: 无 — 返回图像中二维符号(QR / Data Matrix)的印刷质量等级(`table`)。 · 示例: `poc_symbol_part_dpm`

#### symbol / read_pod (3)
- `symbol_read` `image2d → table` GPU: 无 — 用指定的读取器读取图像并返回 ``{"ok", "text", "error"}``(`table`)。 · 示例: `poc_symbol_package_1d`
- `symbol_read_pod` `table → table` GPU: 无 — 由读取试验表返回 POD(命中 = 读出真实字符串)及误读率上限(`table`)。 · 示例: `poc_symbol_lot_ocr`, `poc_symbol_package_1d`, `poc_symbol_part_dpm`
- `symbol_read_trials` `table → table` GPU: 无 — 在每个退化水平下对符号拍摄并读取 ``trials`` 次,返回每次一行的结果表(`table`)。 · 示例: `poc_symbol_package_1d`, `poc_symbol_part_dpm`

#### symbol / symbol_bridge (1)
- `read_symbols_zxing` `image2d → table` GPU: 无 — 用 zxing-cpp 读取图像中的全部符号(一维 / 二维)(`table`)。 · 示例: `poc_symbol_package_1d`, `poc_symbol_part_dpm`

#### symbol / symbol_capture (2)
- `capture_degrade` `image2d → image2d` GPU: 无 — 对反射率图像施加成像退化(照明、模糊、传感器噪声)(`image2d`)。 · 示例: `poc_symbol_lot_ocr`, `poc_symbol_package_1d`, `poc_symbol_part_dpm`
- `render_symbol` `table → image2d` GPU: 无 — 将符号(一维宽度或二维模块网格)绘制为平面的反射率图像(`image2d`)。 · 示例: `poc_symbol_package_1d`, `poc_symbol_part_dpm`

### mv (47 ops / 10 categories)

#### mv / classify (12)
- `classify_class_gmm` (halcon: `classify_class_gmm`) `table × matrix → table` GPU: 无 — 按高斯混合模型逐行返回后验最大的类。 · 示例: `machine_vision_tour`, `poc_real_typewritten_ocr`, `poc_surface_defect_classifiers`
- `classify_class_knn` (halcon: `classify_class_knn`) `table × matrix → table` GPU: 无 — 以 k 近邻多数表决逐行返回类（平票取距离和较小者）。 · 示例: `machine_vision_tour`, `poc_real_typewritten_ocr`, `poc_surface_defect_classifiers`
- `classify_class_mlp` (halcon: `classify_class_mlp`) `table × matrix → table` GPU: 无 — 用 `train_class_mlp` 的多层感知机分类特征行。 · 示例: `machine_vision_tour`, `poc_real_typewritten_ocr`, `poc_surface_defect_classifiers`
- `classify_class_svm` (halcon: `classify_class_svm`) `table × matrix → table` GPU: 无 — 用 `train_class_svm` 的线性 SVM 分类特征行（一对多取最大间隔）。 · 示例: `machine_vision_tour`, `poc_real_typewritten_ocr`, `poc_surface_defect_classifiers`
- `create_lexicon` (halcon: `create_lexicon`) `无输入 → table` GPU: 无 — 创建用于匹配的词表（去重并固定顺序）。 · 示例: `machine_vision_tour`, `poc_real_typewritten_ocr`
- `evaluate_class_gmm` (halcon: `evaluate_class_gmm`) `table × matrix → table` GPU: 无 — 逐行返回各类后验与模型整体的对数密度。 · 示例: `machine_vision_tour`, `poc_real_typewritten_ocr`, `poc_surface_defect_classifiers`
- `lookup_lexicon` (halcon: `lookup_lexicon`) `table → scalar` GPU: 无 — 以完全匹配检查词是否在表中，在则返回 1.0，否则返回 0.0。 · 示例: `machine_vision_tour`, `poc_real_typewritten_ocr`
- `suggest_lexicon` (halcon: `suggest_lexicon`) `table → table` GPU: 无 — 返回编辑距离最小的词及其距离。 · 示例: `machine_vision_tour`, `poc_real_typewritten_ocr`
- `train_class_gmm` (halcon: `train_class_gmm`) `matrix → table` GPU: 无 — 用 EM 为每个类学习高斯混合模型。 · 示例: `machine_vision_tour`, `poc_real_typewritten_ocr`, `poc_surface_defect_classifiers`
- `train_class_knn` (halcon: `train_class_knn`) `matrix → table` GPU: 无 — 构建 k-NN 分类器（特征标准化后保存）。 · 示例: `machine_vision_tour`, `poc_real_typewritten_ocr`, `poc_surface_defect_classifiers`
- `train_class_mlp` (halcon: `train_class_mlp`) `matrix → table` GPU: 无 — 训练 MLP 分类器。 · 示例: `machine_vision_tour`, `poc_real_typewritten_ocr`, `poc_surface_defect_classifiers`
- `train_class_svm` (halcon: `train_class_svm`) `matrix → table` GPU: 无 — 训练线性 SVM（hinge 损失，一对多）。 · 示例: `machine_vision_tour`, `poc_real_typewritten_ocr`, `poc_surface_defect_classifiers`

#### mv / curve (1)
- `gen_nurbs_interp` (halcon: `gen_nurbs_interp`) `keypoints → table` GPU: 无 — 求经过全部点的非有理 B 样条控制点（全局插值）。 · 示例: `machine_vision_tour`

#### mv / detect (3)
- `create_ncc_model` (halcon: `create_ncc_model`) `image2d → table` GPU: 无 — 准备 NCC 模型（归一化模板）。 · 示例: `machine_vision_tour`, `poc_real_stereo_multiscanline`
- `find_ncc_models` (halcon: `find_ncc_models`) `table × image2d → table` GPU: 无 — 在一幅图像中查找一个或多个 NCC 模型。 · 示例: `machine_vision_tour`, `poc_real_stereo_multiscanline`
- `points_lepetit` (halcon: `points_lepetit`) `image2d → keypoints` GPU: 无 — 比较圆周上相对的两点来检测关注点（Lepetit–Fua 检测器）。 · 示例: `machine_vision_tour`, `poc_real_chessboard_undistort`, `poc_real_stereo_multiscanline`

#### mv / gray (5)
- `area_center_gray` (halcon: `area_center_gray`) `image2d → table` GPU: 无 — 返回以灰度为权的质量与重心 `(row, col)`。 · 示例: `machine_vision_tour`, `poc_real_typewritten_ocr`
- `atan2_image` (halcon: `atan2_image`) `image2d × image2d → image2d` GPU: 无 — 以弧度返回两幅图像逐像素的 `atan2(image1, image2)`。 · 示例: `machine_vision_tour`, `poc_real_bg_kalman_tracking`
- `get_grayval_contour_xld` (halcon: `get_grayval_contour_xld`) `image2d × keypoints → signal` GPU: 无 — 沿轮廓点列插值读取灰度，得到一条信号。 · 示例: `machine_vision_tour`
- `gray_histo` (halcon: `gray_histo`) `image2d → table` GPU: 无 — 以绝对频数与相对频率返回灰度直方图。 · 示例: `machine_vision_tour`, `poc_real_typewritten_ocr`
- `gray_projections` (halcon: `gray_projections`) `image2d → table` GPU: 无 — 返回每行与每列的灰度平均值。 · 示例: `machine_vision_tour`, `poc_real_typewritten_ocr`

#### mv / morphology (9)
- `golay_elements` (halcon: `golay_elements`) `无输入 → table` GPU: 无 — 生成 Golay 字母的 3x3 击中与击不中结构元（45 度步进旋转）。 · 示例: `machine_vision_tour`
- `hit_or_miss_golay` (halcon: `hit_or_miss_golay`) `mask → mask` GPU: 无 — 用一个 Golay 字母做击中击不中变换（返回匹配的中心像素）。 · 示例: `machine_vision_tour`, `poc_real_grain_skiz`
- `hit_or_miss_seq` (halcon: `hit_or_miss_seq`) `mask → mask` GPU: 无 — 返回 Golay 字母 8 个旋转的击中击不中变换的并集。 · 示例: `machine_vision_tour`, `poc_real_grain_skiz`
- `morph_hat` (halcon: `morph_hat`) `mask × mask → mask` GPU: 无 — 返回开运算去掉的像素与闭运算增加的像素的并集。 · 示例: `machine_vision_tour`
- `morph_skiz` (halcon: `morph_skiz`) `mask → mask` GPU: 无 — 用欧氏距离求连通分量影响区的边界（SKIZ）。 · 示例: `machine_vision_tour`, `poc_real_grain_skiz`
- `opening_seg` (halcon: `opening_seg`) `mask × mask → labels2d` GPU: 无 — 用腐蚀分开由细颈相连的物体，并在区域内重新扩展为标签。 · 示例: `machine_vision_tour`, `poc_real_bg_kalman_tracking`, `poc_real_grain_skiz`
- `thickening_golay` (halcon: `thickening_golay`) `mask → mask` GPU: 无 — 用一个 Golay 字母加厚区域。 · 示例: `machine_vision_tour`
- `thickening_hit_miss` (halcon: `thickening`) `mask × mask × mask → mask` GPU: 无 — 用任意结构元对加厚区域（`A ∪ HMT(A)`，重复 `iterations` 次）。 · 示例: `machine_vision_tour`
- `thickening_seq` (halcon: `thickening_seq`) `mask → mask` GPU: 无 — 依次使用 Golay 字母的各旋转加厚，直到不再变化。 · 示例: `machine_vision_tour`

#### mv / pose (1)
- `get_circle_pose` (halcon: `get_circle_pose`) `keypoints → table` GPU: 无 — 由已知半径圆的图像椭圆点列，在相机坐标系中求圆心与法线。 · 示例: `machine_vision_tour`, `poc_real_stereo_multiscanline`

#### mv / resample (4)
- `change_radial_distortion_image` (halcon: `change_radial_distortion_image`) `image2d × table × table → image2d` GPU: 无 — 把除法模型相机的图像重绘为另一组畸变与内参的图像。 · 示例: `machine_vision_tour`, `poc_real_chessboard_undistort`
- `crop_rectangle2` (halcon: `crop_rectangle2`) `image2d → image2d` GPU: 无 — 用线性插值读取旋转矩形内部，并裁剪为轴对齐图像。 · 示例: `machine_vision_tour`, `poc_mixed_case_depalletizing`, `poc_real_stereo_multiscanline`
- `map_image` (halcon: `map_image`) `image2d × table → image2d` GPU: 无 — 用逆映射表对图像重采样（每个输出像素读取一个输入坐标）。 · 示例: `machine_vision_tour`, `poc_real_chessboard_undistort`
- `rectify_to_world_plane` (halcon: `image_to_world_plane`) `image2d × table × matrix → image2d` GPU: 无 — 把图像校正为世界平面 z=0 的正视图（1 像素 = `scale` 世界单位）。 · 示例: `machine_vision_tour`, `poc_real_chessboard_undistort`

#### mv / stereo (3)
- `binocular_disparity_ms` (halcon: `binocular_disparity_ms`) `image2d × image2d → table` GPU: 无 — 用半全局匹配计算校正立体的视差，做左右一致检查并插值到亚像素。 · 示例: `machine_vision_tour`, `poc_3d_sensor_modalities`, `poc_real_stereo_multiscanline`
- `binocular_distance_ms` (halcon: `binocular_distance_ms`) `image2d × image2d → table` GPU: 无 — 计算校正立体的距离图（`Z = focal * baseline / (disparity + doffs)`）。 · 示例: `machine_vision_tour`, `poc_real_stereo_multiscanline`
- `reconstruct_surface_stereo` (halcon: `reconstruct_surface_stereo`) `image2d → points` GPU: 无 — 把视差图的有效像素映射为三维点。 · 示例: `machine_vision_tour`, `poc_real_stereo_multiscanline`

#### mv / text (4)
- `segment_characters` (halcon: `segment_characters`) `image2d → labels2d` GPU: 无 — 把文字行图像切分为按字符列分块的标签图。 · 示例: `machine_vision_tour`, `poc_real_typewritten_ocr`
- `select_characters` (halcon: `select_characters`) `labels2d → labels2d` GPU: 无 — 从字符标签图中去掉高度或宽度偏离中位数的块，并从左重新编号。 · 示例: `machine_vision_tour`, `poc_real_typewritten_ocr`
- `text_line_orientation` (halcon: `text_line_orientation`) `image2d → scalar` GPU: 无 — 通过使投影最锐利求文字行的倾角（度）。 · 示例: `machine_vision_tour`, `poc_real_typewritten_ocr`
- `text_line_slant` (halcon: `text_line_slant`) `image2d → scalar` GPU: 无 — 通过使列投影最锐利求水平文字行的字符倾斜角（度）。 · 示例: `machine_vision_tour`, `poc_real_typewritten_ocr`

#### mv / tracking (5)
- `create_bg_esti` (halcon: `create_bg_esti`) `image2d → table` GPU: 无 — 由第一幅图像创建逐像素卡尔曼背景模型。 · 示例: `machine_vision_tour`, `poc_real_bg_kalman_tracking`
- `filter_kalman` (halcon: `filter_kalman`) `无输入 → table` GPU: 无 — 执行线性卡尔曼滤波的一次预测与更新。 · 示例: `machine_vision_tour`, `poc_real_bg_kalman_tracking`
- `give_bg_esti` (halcon: `give_bg_esti`) `table → image2d` GPU: 无 — 返回模型当前背景图像的副本。 · 示例: `machine_vision_tour`, `poc_real_bg_kalman_tracking`
- `run_bg_esti` (halcon: `run_bg_esti`) `table × image2d → table` GPU: 无 — 用一幅图像更新背景并返回前景区域。 · 示例: `machine_vision_tour`, `poc_real_bg_kalman_tracking`
- `update_bg_esti` (halcon: `update_bg_esti`) `table × image2d × mask → table` GPU: 无 — 只在给定区域内更新背景。 · 示例: `machine_vision_tour`, `poc_real_bg_kalman_tracking`

### generative (42 ops / 6 categories)

#### generative / illusion (13)
- `illusion_cafe_wall` `无输入 → rgb` GPU: 无 — 咖啡墙错觉。**砖缝明明是严格的水平线**，看起来却是倾斜的。 · 示例: `poc_calipers_under_illusion`
- `illusion_checker_shadow` `无输入 → rgb` GPU: 无 — 棋盘阴影错觉。**标记的 2 个方格像素值严格相同**。 · 示例: `gallery_illusion_invariants`
- `illusion_ebbinghaus` `无输入 → rgb` GPU: 无 — 艾宾浩斯错觉。**中央的 2 个圆半径严格相同**。 · 示例: `poc_calipers_under_illusion`
- `illusion_fraser_spiral` `无输入 → rgb` GPU: 无 — 弗雷泽错觉。**看起来是漩涡，实际上是同心圆**。 · 示例: `gallery_illusion_invariants`
- `illusion_ground_truth` `无输入 → table` GPU: 无 — 以表格返回错觉所遵守的**严格不变量**(``name`` 为空时返回全部)。 · 示例: `poc_calipers_under_illusion`
- `illusion_hermann_grid` `无输入 → rgb` GPU: 无 — 赫尔曼栅格。**交点与其他地方是严格相同的白色**(黑点是眼睛产生的)。 · 示例: `gallery_illusion_invariants`
- `illusion_kanizsa` `无输入 → rgb` GPU: 无 — 卡尼莎三角形。**连 1 条轮廓线都没有画**，却能看到三角形。 · 示例: `gallery_illusion_invariants`
- `illusion_muller_lyer` `无输入 → rgb` GPU: 无 — 缪勒-莱尔错觉。**2 条主线严格等长**。 · 示例: `poc_calipers_under_illusion`, `poc_illusions_and_perpetual_drawing`
- `illusion_poggendorff` `无输入 → rgb` GPU: 无 — 波根多夫错觉。**斜线严格地是 1 条直线**(只是被条带遮住了)。 · 示例: `poc_calipers_under_illusion`
- `illusion_ponzo` `无输入 → rgb` GPU: 无 — 庞佐错觉。**2 条横杠严格等长**(透视线索改变了长度)。 · 示例: `gallery_illusion_invariants`
- `illusion_scintillating_grid` `无输入 → rgb` GPU: 无 — 闪烁栅格。在赫尔曼栅格的交点处放置白色圆点而成。 · 示例: `gallery_illusion_invariants`
- `illusion_simultaneous_contrast` `无输入 → rgb` GPU: 无 — 同时对比。**2 块灰色色块的值严格相同**(只有周围不同)。 · 示例: `gallery_illusion_invariants`
- `illusion_zollner` `无输入 → rgb` GPU: 无 — 策尔纳错觉。**长线明明严格平行**，看起来却在汇聚。 · 示例: `poc_calipers_under_illusion`

#### generative / loop (2)
- `perpetual_loop` `无输入 → rgbvideo` GPU: 无 — 生成**无接缝的循环视频** → ``rgbvideo`` (T,H,W,3)。 · 示例: `poc_illusions_and_perpetual_drawing`, `poc_periodic_video_boundary`
- `perpetual_loop_seam` `rgbvideo → table` GPU: 无 — 以数值给出循环视频的**接缝**(``table``)。 · 示例: `poc_endless_zoom_and_turning_solids`, `poc_illusions_and_perpetual_drawing`, `poc_periodic_video_boundary`

#### generative / perpetual (12)
- `perpetual_apollonian` `无输入 → rgb` GPU: 无 — 阿波罗尼奥斯圆填充 —— 不断向空隙中放入与之相切的圆(没有尽头)。 · 示例: `poc_illusions_and_perpetual_drawing`
- `perpetual_chaos_game` `无输入 → rgb` GPU: 无 — 混沌游戏 —— 只是掷骰子并每次靠近一半，就会出现谢尔宾斯基三角形。 · 示例: `poc_illusions_and_perpetual_drawing`
- `perpetual_elementary_ca` `无输入 → rgb` GPU: 无 — 初等元胞自动机(Wolfram 的 256 条规则)，从上向下无限延伸。 · 示例: `poc_illusions_and_perpetual_drawing`
- `perpetual_flow_field` `无输入 → rgb` GPU: 无 — 流场 —— 让粒子随场持续流动(不停止就不会结束)。 · 示例: `poc_illusions_and_perpetual_drawing`
- `perpetual_harmonograph` `无输入 → rgb` GPU: 无 — 谐波记录仪 —— 2 个衰减的摆持续画出不闭合的曲线。 · 示例: `gallery_illusion_invariants`
- `perpetual_identities` `无输入 → table` GPU: 无 — 返回各系统应满足的**严格断言**，并附实测值(``table``)。 · 示例: `poc_illusions_and_perpetual_drawing`
- `perpetual_ifs_attractor` `无输入 → rgb` GPU: 无 — 迭代函数系统的吸引子(巴恩斯利蕨)—— 只需无限地迭代 4 个公式。 · 示例: `poc_illusions_and_perpetual_drawing`
- `perpetual_langtons_ant` `无输入 → rgb` GPU: 无 — 兰顿蚂蚁 —— 仅凭 2 条规则，在 1 万步之后不断建造“高速公路”。 · 示例: `gallery_illusion_invariants`
- `perpetual_plasma` `无输入 → rgb` GPU: 无 — 菱形–方形算法(1980 年代的“等离子”)—— 不断细分就会无限精细。 · 示例: `poc_illusions_and_perpetual_drawing`
- `perpetual_reaction_diffusion` `无输入 → rgb` GPU: 无 — 格雷–斯科特反应扩散 —— 花纹生成、分裂并不断增多。 · 示例: `poc_illusions_and_perpetual_drawing`
- `perpetual_ten_print` `无输入 → rgb` GPU: 无 — ``10 PRINT CHR$(205.5+RND(1)); : GOTO 10`` —— 无限延伸的迷宫。 · 示例: `poc_illusions_and_perpetual_drawing`
- `perpetual_truchet` `无输入 → rgb` GPU: 无 — 特吕谢瓷砖 —— 只需随机改变 2 段四分之一圆弧的朝向，就能形成连绵不断的曲线网。 · 示例: `poc_illusions_and_perpetual_drawing`

#### generative / pl (3)
- `pl_diffusion_psf` `无输入 → image2d` GPU: 无 — 以图像形式返回载流子扩散 PSF（二维格林函数 K0(r/L)/2πL²，总和为 1）。 · 示例: `poc_si_wafer_pl_defect_visibility`
- `pl_groove_visibility` `无输入 → table` GPU: 无 — 由沟槽宽度、扩散长度与噪声，以闭式给出阴影沟槽与复合沟槽的对比度和 CNR（table）。 · 示例: `poc_si_wafer_pl_defect_visibility`
- `pl_image_simulate` `image2d → image2d` GPU: 无 — 由激发场和复合场生成 PL 图像（稳态扩散方程的精确解 + 光学 PSF + 噪声）。 · 示例: `poc_si_wafer_pl_defect_visibility`

#### generative / sem (9)
- `sem_cd_measure` `pairs → table` GPU: 无 — 用 CD-SEM 的两种方法从线轮廓(``pairs``:x 与信号)求线宽。 · 示例: `poc_real_sem_metal_layer`, `poc_virtual_sem_kv_cd_bse`
- `sem_charging_series` `image2d → video` GPU: 无 — 按扫描帧推进绝缘体的带电,返回图像随时间的变化(``video``,(T, H, W))。 · 示例: `poc_virtual_sem_kv_cd_bse`
- `sem_electron_mc` `无输入 → table` GPU: 无 — 向平整试样发射电子的蒙特卡罗:背散射系数 η、二次电子产额 δ 与相互作用体积。 · 示例: `poc_sem_tem_same_particle`, `poc_virtual_sem_kv_cd_bse`
- `sem_image` `image2d → image2d` GPU: 无 — 由高度场与材料图生成 SEM 像:向每个像素发射电子(直接蒙特卡罗)。 · 示例: `poc_sem_tem_same_particle`, `poc_sem_wafer_defect_edge_bias`, `poc_virtual_sem_kv_cd_bse`
- `sem_line_profile` `无输入 → table` GPU: 无 — 用蒙特卡罗求电子束横扫一条梯形截面线条的线轮廓(CD-SEM)。 · 示例: `poc_real_sem_metal_layer`, `poc_virtual_sem_kv_cd_bse`
- `sem_render` `image2d → image2d` GPU: 有(许可列表) — 从高度场生成 SEM 图像：二次电子边缘效应（sec θ）+ 高斯束斑 PSF + 泊松散粒噪声。 · 示例: `poc_sem_tem_same_particle`, `poc_sem_wafer_defect_edge_bias`
- `sem_se_escape_fraction` `无输入 → signal` GPU: 无 — 二次电子能离开正带电表面(电位 V > 0)的比例 F(V)。 · 示例: `poc_virtual_sem_kv_cd_bse`
- `sem_se_universal_curve` `无输入 → signal` GPU: 无 — 二次电子产额的普适曲线 δ/δmax = 1.28 (E/Emax)^−0.67 [1 − exp(−1.614 (E/Emax)^1.67)]。 · 示例: `poc_virtual_sem_kv_cd_bse`
- `sem_yield_curve` `无输入 → table` GPU: 无 — 扫描加速电压,用蒙特卡罗求 η(E) 与 δ(E),并把 δ 的形状与普适曲线比较。 · 示例: `poc_virtual_sem_kv_cd_bse`

#### generative / stream (3)
- `perpetual_render` `table → rgb` GPU: 无 — 将状态绘制成图(``rgb``)。在第几步绘制都可以。 · 示例: `poc_illusions_and_perpetual_drawing`
- `perpetual_state` `无输入 → table` GPU: 无 — 创建可以无限运行的**状态**(``table``)。何时停止由调用方决定。 · 示例: `poc_illusions_and_perpetual_drawing`
- `perpetual_step` `table → table` GPU: 无 — 将状态推进 ``steps`` 步(返回同一个 dict —— 不复制大数组)。 · 示例: `poc_illusions_and_perpetual_drawing`

### imgmetrics (42 ops / 8 categories)

#### imgmetrics / colordiff (3)
- `delta_e_2000` `lab × lab → image2d` GPU: 无 — CIEDE2000 色差(CIE 142-2001)。 · 示例: `image_quality_metrics`
- `delta_e_76` `lab × lab → image2d` GPU: 无 — CIE76 色差 —— Lab 空间中的欧几里得距离。 · 示例: `image_quality_metrics`
- `delta_e_map` `rgbimage × rgbimage → image2d` GPU: 无 — 两张 **sRGB 图像**逐像素的色差图。 · 示例: `color_transport`, `image_quality_metrics`, `poc_colormap_readability`, `poc_pigment_unmixing`, `poc_white_balance`

#### imgmetrics / colorspace (4)
- `lab_to_rgb` `lab → rgbimage` GPU: 有(许可列表) — CIE L\*a\*b\* → sRGB ``[0, 1]``。**超出色域的颜色会被截断**,因此与 ``rgb_to_lab`` 的往返只在色域内一致(有测试固定)。 · 示例: `image_quality_metrics`
- `rgb_to_lab` `rgbimage → lab` GPU: 无 — sRGB → CIE L\*a\*b\*(D65)。测 ΔE 之前的一步。 · 示例: `image_quality_metrics`, `poc_colormap_readability`, `poc_leaf_disease_area`, `poc_metal_grain_size`, `poc_solder_fillet_aoi`
- `rgb_to_xyz` `rgbimage → rgb` GPU: 无 — sRGB(``(..., 3)``)→ CIE XYZ。先去掉传递函数,再乘矩阵。 · 示例: `image_quality_metrics`
- `xyz_to_lab` `rgb → lab` GPU: 有(许可列表) — CIE XYZ → CIE 1976 L\*a\*b\*。默认白点为 D65 2°。 · 示例: `image_quality_metrics`

#### imgmetrics / compression (2)
- `compressed_size` `image2d → scalar` GPU: 无 — 数组无损压缩后的字节数。``ncd`` 的原料。 · 示例: `image_quality_metrics`
- `ncd` `image2d × image2d → scalar` GPU: 无 — 归一化压缩距离(Li, Chen, Li, Ma & Vitányi, IEEE TIT 50(12), 2004)。 · 示例: `image_quality_metrics`

#### imgmetrics / fidelity (6)
- `ms_ssim` `image2d × image2d → scalar` GPU: 无 — 多尺度 SSIM(Wang, Simoncelli & Bovik, Asilomar Conf. 2003)。 · 示例: `image_quality_metrics`
- `mse` `image2d × image2d → scalar` GPU: 无 — 均方误差。不依赖 ``data_range`` 的原始量。 · 示例: `image_quality_metrics`
- `psnr` `image2d × image2d → scalar` GPU: 无 — 返回两幅图像的峰值信噪比(PSNR,单位 dB)。 · 示例: `image_quality_metrics`, `poc_camera_shake_deblur`, `poc_dehazing`, `poc_focus_stacking`, `poc_iqa_tid2013`, `poc_pixel_shift`, `poc_real_deblur_honesty`, `poc_superresolution_limits`
- `rmse` `image2d × image2d → scalar` GPU: 无 — 均方根误差(与像素值同单位)。 · 示例: `ct_scan_modes`, `grasp_pose`, `image_quality_metrics`, `poc_ct_fidelity`, `poc_datacenter_thermal_field`, `poc_polarization_specular`, `poc_real_tless_6dof`, `poc_real_walnut_cbct`, `poc_structure_4d_deterioration`
- `ssim` `image2d × image2d → scalar` GPU: 无 — 结构相似性(Wang, Bovik, Sheikh & Simoncelli, IEEE TIP 13(4), 2004)。 · 示例: `image_quality_metrics`, `poc_camera_shake_deblur`, `poc_ct_fidelity`, `poc_dehazing`, `poc_iqa_tid2013`, `poc_real_walnut_cbct`, `poc_superresolution_limits`
- `ssim_map` `image2d × image2d → image2d` GPU: 无 — SSIM 的**图**(取平均之前)。用来看清哪里不像。 · 示例: `image_quality_metrics`, `poc_iqa_tid2013`

#### imgmetrics / information (5)
- `image_entropy` `image2d → scalar` GPU: 无 — 单张图像的香农熵 [bit]。 · 示例: `image_quality_metrics`, `poc_dehazing`
- `joint_entropy` `image2d × image2d → scalar` GPU: 无 — 联合熵 H(A, B) [bit]。 · 示例: `image_quality_metrics`
- `joint_histogram` `image2d × image2d → image2d` GPU: 有(许可列表) — 两张图像的联合直方图(归一化后的联合概率)。 · 示例: `image_quality_metrics`
- `mutual_information` `image2d × image2d → scalar` GPU: 无 — 互信息 I(A; B) [bit] = H(A) + H(B) - H(A, B)。 · 示例: `image_quality_metrics`
- `normalized_mutual_information` `image2d × image2d → scalar` GPU: 无 — 归一化互信息 2*I(A;B) / (H(A) + H(B))。同一张图为 1.0。 · 示例: `image_quality_metrics`

#### imgmetrics / iqa (11)
- `luma_limited_u8` `any → any` GPU: 有(许可列表) — RGB (H, W, 3) uint8 → Y′ = round(16 + (65.481 R + 128.553 G + 24.966 B) / 255) 的 uint8 (H, W)。 · 示例: `poc_iqa_tid2013`
- `rank_data` `any → any` GPU: 无 — 平均秩(从 1 开始)。并列者取其秩的平均(与 scipy.stats.rankdata 的 'average' 定义相同)。 · 示例: `poc_iqa_tid2013`
- `rank_kendall_b` `any × any → scalar` GPU: 无 — Kendall 的 τ_b(含并列校正)= (C − D) / sqrt((n0 − n1)(n0 − n2))。 · 示例: `poc_iqa_fsim_gmsd_vif`, `poc_iqa_tid2013`
- `rank_spearman` `any × any → scalar` GPU: 无 — Spearman 秩相关 ρ = 平均秩之间的 Pearson 相关(即使有并列也正确的形式。经典公式 1 − 6Σd²/(n(n²−1)) 仅在无并列时一致)。单调递增为 1，反转为 −1。任一方为常数时为 ``nan``(秩的方差为 0，相关无定义)。 ±inf 只使用其顺序(不丢弃完全一致时的 PSNR = inf)。**Raises** ``ValueError``：长度不一致、少于 2、nan。 · 示例: `poc_iqa_fsim_gmsd_vif`, `poc_iqa_tid2013`
- `tid2013_by_distortion` `any × table → table` GPU: 无 — 按失真类型(24 种)分别计算的指标与 MOS 的秩相关。 · 示例: `poc_iqa_fsim_gmsd_vif`, `poc_iqa_tid2013`
- `tid2013_compare` `any × any × any → table` GPU: 无 — 比较自己的值与作者的值(同一图像对、同一顺序)：逐行差值以及与 MOS 的秩相关。 · 示例: `poc_iqa_fsim_gmsd_vif`, `poc_iqa_tid2013`
- `tid2013_evaluate` `any × any → table` GPU: 无 — 将自己的指标 ``fn(ref, dist) -> float`` 应用于 TID2013 的图像对，返回与 MOS 的秩相关。 · 示例: `poc_iqa_fsim_gmsd_vif`, `poc_iqa_tid2013`
- `tid2013_index` `any → table` GPU: 无 — 读取 ``mos_with_names.txt``，返回图像对的台账。 · 示例: `poc_iqa_fsim_gmsd_vif`, `poc_iqa_tid2013`
- `tid2013_metric_values` `any × any → any` GPU: 无 — 将作者的计算值 ``metrics_values/<metric>.txt``(不区分大小写，3000 行，无名称)以 (3000,) float 返回。 行的顺序与 :func:`tid2013_index` 的 ``names`` 相同。``metric`` 为 :func:`tid2013_published` 的键(psnr / psnrc / ssim / mssim …)。 **Raises** ``ValueError``：文件不存在、行数 ≠ 3000、非数值。 · 示例: `poc_iqa_fsim_gmsd_vif`, `poc_iqa_tid2013`
- `tid2013_published` `无输入 → table` GPU: 无 — 公开的秩相关表 {metric: (SROCC, KROCC)}(14 个)。 · 示例: `poc_iqa_fsim_gmsd_vif`, `poc_iqa_tid2013`
- `tid2013_root` `无输入 → any` GPU: 无 — 分发包的解压位置。若无 ``root``，则用环境变量 ``FULLSEYE_TID2013_DATA``。两者都没有、或没有 ``mos_with_names.txt`` 时返回 ``None`` (调用方会 skip —— 数据不在 repo 中)。 · 示例: `poc_iqa_fsim_gmsd_vif`, `poc_iqa_tid2013`

#### imgmetrics / perceptual (7)
- `fsim` `image2d × image2d → scalar` GPU: 无 — FSIM(基于特征相似度的全参考图像质量指标。仅亮度，1 = 相同，**higher is better**)。传入 **Y′ limited 的灰度图像**时，与 TID2013 的 FSIM.txt 在 4 位上一致 (``iqatid.tid2013_evaluate(root, fsim, luma="limited_u8")``，3,000 对，max |差| 5.0e-5)。详见 :func:`fsim_pair`。 · 示例: `poc_iqa_fsim_gmsd_vif`
- `fsim_pair` `rgbimage × rgbimage → table` GPU: 无 — 一次性计算 FSIM 和 FSIMc(每张图像的相位一致性只计算 1 次 —— 评估器和 PoC 调用的是这个函数)。 · 示例: `poc_iqa_fsim_gmsd_vif`
- `fsimc` `rgbimage × rgbimage → scalar` GPU: 无 — FSIMc(基于特征相似度的全参考图像质量指标。含色度 I / Q，1 = 相同，**higher is better**)。传入彩色图像(RGB → YIQ full range)时，与 TID2013 的 FSIMc.txt 在 4 位上一致 (``iqatid.tid2013_evaluate(root, fsimc, luma="rgb")``，3,000 对，max |差| 5.0e-5)。(H, W) 输入时与 FSIM 值相同。详见 :func:`fsim_pair`。 · 示例: `poc_iqa_fsim_gmsd_vif`
- `gmsd` `image2d × image2d → scalar` GPU: 无 — GMSD = GMS 图的标准差(N−1，原实现的 ``std2``，论文式 5)。0 = 相同，越大表示劣化越严重(**越低越好** —— 与 MOS 的秩相关为负，公开表格给出的是 |ρ|：TID2013 整体 |SROCC| 0.8038，二手资料 0.8044)。输入为 (H, W) 或 (H, W, 3)(3 通道时取 Y)。``iqatid.tid2013_evaluate(root, gmsd, luma="rgb")``。**Raises** ``ValueError``：与 :func:`gmsd_map` 相同，或图只有 1 个像素(方差无定义)。 · 示例: `poc_iqa_fsim_gmsd_vif`
- `gmsd_map` `image2d × image2d → image2d` GPU: 有(许可列表) — GMS 图 (2 m_r m_d + c)/(m_r² + m_d² + c) ∈ (0, 1] (论文式 3)。m = Prewitt([1 0 −1]×3 /3)梯度的幅值，预处理为 2×2 均值 + 2 倍抽取 (:func:`_average_downsample`，原实现的 'same' 约定)。输入为 (H, W) 或 (H, W, 3)(3 通道时取 Y = 0.299R+0.587G+0.114B，作者的惯例)。**Raises** ``ValueError``：形状不同、c ≤ 0、down_step < 1。 · 示例: `poc_iqa_fsim_gmsd_vif`
- `phase_congruency_pc` `image2d → image2d` GPU: 有(许可列表) — 相位一致性 PC(x) = Σ_o E_o(x) / Σ_o Σ_s A_{s,o}(x) ∈ [0, 1] (Kovesi 1999，FSIM 论文式 4 的约定：log-Gabor 4 个尺度 × 4 个方向)。 · 示例: `poc_iqa_fsim_gmsd_vif`
- `vifp` `image2d × image2d → scalar` GPU: 无 — VIF 的像素域版本(Sheikh & Bovik 2006 §V 的 scalar GSM，沿用公开的 vifp_mscale 的约定)。1 = 相同，**越高越好**。 · 示例: `poc_iqa_fsim_gmsd_vif`

#### imgmetrics / report (4)
- `compare_images` `image2d × image2d → metrics` GPU: 无 — 一次测量多个指标,并**把「测了什么、怎么测的」与数值一起返回**。 · 示例: `image_quality_metrics`
- `data_range_of` `image2d → scalar` GPU: 无 — 确定像素值可取的范围。**不做猜测。** · 示例: `image_quality_metrics`
- `measure_with` `metrics × image2d × image2d → metrics` GPU: 无 — **在与上一次完全相同的条件下**测量另一组。 · 示例: `image_quality_metrics`
- `metrics_table` `metrics → table` GPU: 无 — 把报告整理成 ``(名称, 数值)`` 的表 —— 描述测量条件的行**必定一并列出**。 · 示例: `image_quality_metrics`

### oned (49 ops / 4 categories)

剖面/信号的 1-D op。来源是 2-D 的 measure1d、3-D 的 probe 以及音频/传感器序列(dsp)—— 用 funct1d/dsp 加工取出的 (x, y) 序列并进行测量。

#### oned / function (23)
- `abs_funct_1d` (halcon: `abs_funct_1d`) `signal → signal` GPU: 仅在链中(许可列表) — y 值的绝对值(HALCON ``abs_funct_1d``)。 · 示例: `signal_funct1d`
- `compose_funct_1d` (halcon: `compose_funct_1d`) `signal × signal → signal` GPU: 仅在链中(许可列表) — 复合 ``y1(y2)``：把 *y2* 的值用作 *y1* 中的位置(HALCON ``compose_funct_1d``)。 · 示例: `gallery_oned_audio_funct`
- `create_funct_1d_array` (halcon: `create_funct_1d_array`) `signal → signal` GPU: 无 — 由等间距样本构成的一维函数(HALCON ``create_funct_1d_array``)。 · 示例: `signal_funct1d`
- `create_funct_1d_pairs` (halcon: `create_funct_1d_pairs`) `signal × signal → signal` GPU: 有(许可列表) — 由任意 ``(x, y)`` 对构成并重采样到等间距网格的一维函数(HALCON ``create_funct_1d_pairs``)。 · 示例: `poc_veiling_glare`
- `derivate_funct_1d` (halcon: `derivate_funct_1d`) `signal → signal` GPU: 仅在链中(许可列表) — 用中心差分求一阶导数(HALCON ``derivate_funct_1d``)。 · 示例: `poc_tree_ring_dendro`, `poc_veiling_glare`, `signal_funct1d`
- `distance_funct_1d` (halcon: `distance_funct_1d`) `signal × signal → measurement` GPU: 无 — 同一网格上两个函数之间的距离(HALCON ``distance_funct_1d``)。 · 示例: `signal_funct1d`
- `funct_1d_to_pairs` (halcon: `funct_1d_to_pairs`) `signal → pairs` GPU: 无 — 以显式 ``(x, y)`` 对的形式取出函数(HALCON ``funct_1d_to_pairs``)。 · 示例: `signal_funct1d`
- `get_pair_funct_1d` (halcon: `get_pair_funct_1d`) `signal → pairs` GPU: 无 — *index* 处的 ``(x, y)`` 对(HALCON ``get_pair_funct_1d``)。 · 示例: `signal_funct1d`
- `get_y_value_funct_1d` (halcon: `get_y_value_funct_1d`) `signal → measurement` GPU: 无 — (可含小数的)位置 *x* 处的 y 值(HALCON ``get_y_value_funct_1d``)。 · 示例: `poc_veiling_glare`, `signal_funct1d`
- `integrate_funct_1d` (halcon: `integrate_funct_1d`) `signal → signal` GPU: 仅在链中(许可列表) — 用梯形法则求累积积分(HALCON ``integrate_funct_1d``)。 · 示例: `poc_cold_chain_excursion`, `poc_search_sweep_width`, `signal_funct1d`
- `invert_funct_1d` (halcon: `invert_funct_1d`) `signal → pairs` GPU: 有(许可列表) — 交换 x 与 y 的角色：``x = f^-1(y)``(HALCON ``invert_funct_1d``)。 · 示例: `poc_veiling_glare`
- `local_min_max_funct_1d` (halcon: `local_min_max_funct_1d`) `signal → table` GPU: 无 — 严格局部极大/极小的索引(HALCON ``local_min_max_funct_1d``)。 · 示例: `poc_web_roll_periodicity`, `signal_funct1d`
- `match_funct_1d_trans` (halcon: `match_funct_1d_trans`) `signal × signal → table` GPU: 无 — 通过相关求两个函数之间的最佳整数平移(HALCON ``match_funct_1d_trans``，仅平移)。 · 示例: `signal_funct1d`
- `negate_funct_1d` (halcon: `negate_funct_1d`) `signal → signal` GPU: 无 — 符号取反的 y 值(HALCON ``negate_funct_1d``)。 · 示例: `gallery_oned_audio_funct`, `gallery_spectrum_signal_bridge`
- `num_points_funct_1d` (halcon: `num_points_funct_1d`) `signal → measurement` GPU: 无 — 样本个数(HALCON ``num_points_funct_1d``)。 · 示例: `signal_funct1d`
- `sample_funct_1d` (halcon: `sample_funct_1d`) `signal → signal` GPU: 无 — 每隔 *step* 个取一个样本(HALCON ``sample_funct_1d``)。 · 示例: `poc_cold_chain_excursion`, `signal_funct1d`
- `scale_y_funct_1d` (halcon: `scale_y_funct_1d`) `signal → signal` GPU: 无 — y 值的线性映射 ``mult * y + add``(HALCON ``scale_y_funct_1d``)。 · 示例: `signal_funct1d`
- `smooth_funct_1d_gauss` (halcon: `smooth_funct_1d_gauss`) `signal → signal` GPU: 仅在链中(许可列表) — 一维函数的高斯平滑(HALCON ``smooth_funct_1d_gauss``)。 · 示例: `poc_fiber_orientation`, `poc_tree_ring_dendro`, `poc_web_roll_periodicity`, `signal_funct1d`
- `smooth_funct_1d_mean` (halcon: `smooth_funct_1d_mean`) `signal → signal` GPU: 无 — 迭代滑动平均平滑(HALCON ``smooth_funct_1d_mean``)。 · 示例: `poc_weld_bead_profile`, `signal_funct1d`
- `transform_funct_1d` (halcon: `transform_funct_1d`) `signal → pairs` GPU: 仅在链中(许可列表) — 对 x 与 y 分别独立做仿射变换(HALCON ``transform_funct_1d``)。 · 示例: `gallery_oned_audio_funct`
- `x_range_funct_1d` (halcon: `x_range_funct_1d`) `signal → pairs` GPU: 无 — x 的定义域 ``(0.0, n - 1.0)``(HALCON ``x_range_funct_1d``)。 · 示例: `signal_funct1d`
- `y_range_funct_1d` (halcon: `y_range_funct_1d`) `signal → pairs` GPU: 无 — 值域 ``(min(y), max(y))``(HALCON ``y_range_funct_1d``)。 · 示例: `signal_funct1d`
- `zero_crossings_funct_1d` (halcon: `zero_crossings_funct_1d`) `signal → indices` GPU: 无 — 函数改变符号处的索引(HALCON ``zero_crossings_funct_1d``)。 · 示例: `signal_funct1d`

#### oned / io (3)
- `read_audio` `file → signal` GPU: 无 — 读取任意音频格式 -> ``(x, rate)``。可用时使用 ``soundfile``(mp3/flac/ogg/…)，否则回退到标准库的 WAV 读取器。 · 示例: `gallery_oned_audio_funct`
- `read_wav` `file → signal` GPU: 无 — 读取 WAV 文件(标准库) -> ``(x float64 [-1,1], rate)``。多声道取平均为单声道。支持 8/16/32-bit PCM。 · 示例: `genspark_external_review`
- `write_wav` `signal → file` GPU: 无 — 把 float ``[-1,1]`` 单声道信号写成 16-bit PCM WAV(标准库)。非有限样本会抛出异常(否则会变成损坏的 PCM)。 · 示例: `genspark_external_review`

#### oned / matched (7)
- `chirp_mass_from_track` `pairs → table` GPU: 无 — 由引力波频率轨迹 (t, f) 最小二乘求啁啾质量与并合时刻。 · 示例: `poc_gw_detector_pseudo_simulation`
- `chirp_newtonian` `无输入 → signal` GPU: 无 — 牛顿近似（0PN）旋近波形 h₊(t)，以 signal 返回（并合在数组末尾）。 · 示例: `poc_gw_detector_pseudo_simulation`
- `coincidence_delay` `signal × signal → table` GPU: 无 — 两条信噪比时间序列峰值的时刻差（b − a），亚采样精度。 · 示例: `poc_gw_detector_pseudo_simulation`
- `matched_filter_snr` `signal × signal × pairs → signal` GPU: 无 — 匹配滤波的信噪比时间序列 |ρ(t)|（对相位取最大），以 signal 返回。 · 示例: `poc_gw_detector_pseudo_simulation`
- `optimal_snr` `signal × pairs → measurement` GPU: 无 — 模板的最优信噪比 σ = √(4∫|h̃|²/S df)（measurement）。 · 示例: `poc_gw_detector_pseudo_simulation`
- `psd_welch` `signal → pairs` GPU: 有(许可列表) — Welch 法单边功率谱密度，以 pairs（频率 [Hz]，S [1/Hz]）返回。 · 示例: `poc_gw_detector_pseudo_simulation`
- `whiten_by_psd` `signal × pairs → signal` GPU: 有(许可列表) — 用噪声 PSD 做白化（x_w = irfft(rfft(x)·√(2Δt/S(f)))）。 · 示例: `poc_gw_detector_pseudo_simulation`

#### oned / signal (16)
- `bandpass` `signal → signal` GPU: 无 — *low* 与 *high* Hz 之间的巴特沃斯带通。两端都必须在 ``(0, rate/2)`` 之内；长度约定与 :func:`lowpass` 相同。 · 示例: `poc_gw_detector_pseudo_simulation`, `poc_leak_localization`
- `companding_mu_law` `signal → signal` GPU: 无 — μ 律压扩 —— 把 G.711 的曲线用于任意一维信号。 · 示例: `gallery2d_gray_arith`
- `envelope` `signal → signal` GPU: 有(许可列表) — 经解析(希尔伯特)信号求振幅包络——敲击/冲击/声发射猝发的形状。 · 示例: `coherence_scanning`, `poc_beam_modal_video`
- `find_peaks` `signal → indices` GPU: 无 — 峰的索引(scipy.signal.find_peaks)——冲击/缺陷回波。 · 示例: `poc_multibeam_bathymetry`, `poc_tree_ring_dendro`, `poc_web_roll_periodicity`, `type_connectivity_tour`
- `highpass` `signal → signal` GPU: 无 — 巴特沃斯高通。奈奎斯特与长度约定与 :func:`lowpass` 相同。 · 示例: `gallery2d_texture_freq`, `optics_four_f_processor`, `signal_filter`
- `local_std` `signal → signal` GPU: 无 — 带误差界的滑动标准差。 · 示例: `gallery2d_texture_freq`
- `lowpass` `signal → signal` GPU: 无 — 巴特沃斯低通(scipy，零相位 filtfilt)。*cutoff* 必须在 ``(0, rate/2)`` 之内；超出奈奎斯特的截止频率会抛出异常，而不是让信号直接通过。对零相位 filtfilt 而言过短的信号同样抛出异常(消息中写明确切的最小长度)，而不是悄悄返回未滤波的信号。 · 示例: `degenerate_inputs`, `gallery2d_texture_freq`, `optics_four_f_processor`, `signal_filter`
- `peak_subbin` `signal × indices → signal` GPU: 无 — 样本**之间**的峰位置——过 3 点拟合曲线的顶点。 · 示例: `poc_multibeam_bathymetry`, `poc_print_registration`, `poc_web_roll_periodicity`
- `point_spectrum` `positions → table` GPU: 无 — **事件位置**的周期图——缺陷、冲击、计数、到达。 · 示例: `poc_web_roll_periodicity`, `type_connectivity_tour`
- `quantize` `signal → signal` GPU: 无 — 给出误差模型的标量量化器(可选抖动)。 · 示例: `poc_cold_chain_excursion`
- `resample` `signal → signal` GPU: 有(许可列表) — 把信号重采样到 *new_rate*(傅里叶法)。 · 示例: `poc_driving_school`
- `rms` `signal → measurement` GPU: 无 — RMS 电平。对整个信号为标量；给定 *frame* 时为逐帧数组(随时间变化的振动/能量包络)。 · 示例: `lens_design_demo`, `lightfield_depth`, `poc_battery_electrode_breathing`, `poc_bilateral_asymmetry`, `poc_bump_coplanarity`, `poc_cad_scan_deviation`, `poc_calipers_under_illusion`, `poc_camera_calibration`, `poc_cd_spin_joint`, `poc_dimensional_inspection`, `poc_exoplanet_transit`, `poc_fabric_defect`, `poc_focus_stacking`, `poc_fourier_ptychography`, `poc_lens_solves_afocal`, `poc_panorama_drift`, `poc_print_registration`, `poc_river_surface_velocity`, `poc_screw_thread_metrology`, `poc_shape_from_polarization`, `poc_solar_limb_darkening`, `poc_strain_history`, `poc_surface_roughness`, `poc_symmetry_restoration`, `poc_table_tennis_bounce`, `poc_tacscalib_sphere_lut`, `poc_tacsim_elastic_membrane`, `poc_tacsim_marker_shear`, `poc_thermal_radiometry`, `poc_weld_bead_profile`, `profile_shape_inspection`
- `signal_features` `signal → table` GPU: 无 — 用于异常检测的紧凑声学/振动特征向量：``rms``、``peak``、``crest_factor``、``zcr``、``spectral_centroid``(Hz)、``peak_freq``(Hz)、``bandwidth``(Hz)。全部有限——含 NaN / Inf 的样本会抛出 ``ValueError``，而不是产生 NaN 特征(自 2026-10-12 起空信号亦然；此前返回零)。 · 示例: `gallery_oned_audio_funct`
- `spectrogram` `signal → image2d` GPU: 无 — STFT 幅度谱图 -> ``(freqs, times, S)``，``S`` 的形状为 ``(n_freqs, n_frames)``。加汉宁窗；*hop* 默认为 ``win//2``。 · 示例: `acoustic_condition_monitoring`, `poc_emva1288_sensor`, `poc_gw_detector_pseudo_simulation`
- `spectrum` `signal → pairs` GPU: 有(许可列表) — 原始单边幅度谱 -> ``(freqs, magnitude)``(``np.fft.rfft``)。 · 示例: `acoustic_condition_monitoring`, `anim3d_lens_aberrations`, `poc_bearing_diagnosis`, `poc_gear_tooth_metrology`, `poc_machine_condition_fusion`, `poc_pipe_wall_loss`, `poc_recycling_sorting`, `poc_thin_film_reflectometry`, `poc_web_roll_periodicity`, `type_connectivity_tour`
- `zero_crossing_rate` `signal → measurement` GPU: 无 — 相邻样本中符号改变的比例——廉价的音高/噪声程度线索。 · 示例: `gallery_oned_audio_funct`, `gallery_spectrum_signal_bridge`

### colortransport (11 ops / 4 categories)

#### colortransport / blend (1)
- `poisson_blend` `image2d × image2d × mask → image2d` GPU: 无 — 搬运梯度场的无缝合成(Pérez, Gangnet & Blake, SIGGRAPH 2003)。 · 示例: `color_transport`

#### colortransport / matching (3)
- `color_transfer` `rgbimage × rgbimage → rgbimage` GPU: 无 — 把 ``src`` 的色调向 ``ref`` 靠拢。 · 示例: `color_transport`
- `gaussian_transport_map` `points × points → matrix` GPU: 无 — 把两个点集视为正态分布时的 Monge 映射的线性部分 ``A`` 和均值 ``m1, m2``。 · 示例: `color_transport`
- `histogram_match` `image2d × image2d → image2d` GPU: 有(许可列表) — 把 ``src`` 的取值分布匹配到 ``ref``(一维精确最优输运)。 · 示例: `color_transport`, `poc_change_detection_misreg`

#### colortransport / plan_use (2)
- `apply_transport` `transport_plan × signal → signal` GPU: 无 — 用输运计划把 ``target_values`` 拉回到源点上(重心映射)。 · 示例: `color_transport`
- `transport_cost` `transport_plan × matrix → scalar` GPU: 无 — 输运计划的总代价 ``<plan, cost>``。**消费计划**的那一侧算子。 · 示例: `color_transport`

#### colortransport / transport (5)
- `sinkhorn` `signal × signal × matrix → transport_plan` GPU: 无 — 带熵正则化的最优输运计划(Cuturi, NIPS 2013)。 · 示例: `color_transport`
- `sinkhorn_distance` `signal × signal × matrix → scalar` GPU: 无 — 正则化输运代价 ``<plan, cost>``。**不是严格意义的距离**。 · 示例: `color_transport`
- `sinkhorn_divergence` `signal × signal × matrix → scalar` GPU: 无 — **去偏**的 Sinkhorn 距离(Genevay, Peyré & Cuturi, AISTATS 2018)。 · 示例: `color_transport`
- `transport_plan_1d` `signal × signal → transport_plan` GPU: 无 — 一维精确输运计划(西北角法则)。返回 ``(n, m)`` 质量矩阵。 · 示例: `color_transport`
- `wasserstein_1d` `signal × signal → scalar` GPU: 无 — 一维 p-Wasserstein 距离。**精确解**。 · 示例: `color_transport`, `poc_physarum_transport`

### imgforensics (16 ops / 7 categories)

#### imgforensics / calibration (2)
- `evidence_quantile` `measurement × table → table` GPU: 无 — 证据量落在清洁分布的**什么位置**。不给出判定。 · 示例: `image_forensics_audit`, `poc_prnu_camera_fingerprint`, `poc_video_physics_consistency`
- `null_distribution` `signal → table` GPU: 无 — 由已知**未被篡改**的样本汇总证据量的零分布。 · 示例: `image_forensics_audit`, `poc_prnu_camera_fingerprint`, `poc_video_physics_consistency`

#### imgforensics / compression (4)
- `error_level_map` `image2d → image2d` GPU: 无 — ELA(误差水平分析)。给出按指定质量**重压缩后差分**的地图。``image2d``。 · 示例: `image_forensics_audit`, `poc_forensics_roc`
- `jpeg_ghost_map` `image2d → images` GPU: 无 — JPEG 幽灵(Farid 2009)。扫描质量得到的**重压缩残差图序列**。``images``。 · 示例: `image_forensics_audit`, `poc_forensics_roc`
- `jpeg_ghost_quality` `images → image2d` GPU: 无 — 幽灵图序列 → 逐像素**残差最小的质量**的地图。``image2d``。 · 示例: `image_forensics_audit`, `poc_forensics_roc`
- `jpeg_quality_estimate` `image2d → table` GPU: 无 — 由已解码图像**盲估量化表与 JPEG 质量**。``table``。 · 示例: `image_forensics_audit`

#### imgforensics / copy_move (1)
- `copy_move_regions` `image2d → table` GPU: 无 — 单张图像内 **复制-粘贴**(自我复制)区域的配对。``table``。 · 示例: `image_forensics_audit`, `poc_forensics_roc`

#### imgforensics / hash (2)
- `hash_distance` `phash × phash → measurement` GPU: 无 — 两个感知哈希的汉明距离(不同比特数)。 · 示例: `image_forensics_audit`
- `perceptual_hash` `image2d → phash` GPU: 有(许可列表) — 感知哈希。返回 **bool 的一维比特串**。 · 示例: `image_forensics_audit`

#### imgforensics / noise (1)
- `noise_inconsistency_map` `image2d → image2d` GPU: 仅在链中(许可列表) — **逐块噪声标准差**的地图。``image2d``。 · 示例: `image_forensics_audit`, `poc_forensics_roc`

#### imgforensics / sensor (3)
- `fingerprint_correlate` `image2d × fingerprint → table` GPU: 无 — 把一张图像与指纹比对。**不给出判定** —— 返回证据量与注意事项。 · 示例: `image_forensics_audit`, `poc_prnu_camera_fingerprint`
- `fingerprint_strength_map` `fingerprint → image2d` GPU: 无 — 指纹**逐块有效强度**(标准差)的地图。``image2d``。 · 示例: `image_forensics_audit`
- `sensor_fingerprint` `images → fingerprint` GPU: 有(许可列表) — 由多帧最大似然估计 **PRNU 传感器指纹** K(Chen et al. 2008)。 · 示例: `image_forensics_audit`, `poc_prnu_camera_fingerprint`

#### imgforensics / watermark (3)
- `watermark_capacity` `image2d × phash → table` GPU: 无 — 扫描嵌入强度与 **PSNR / BER** 之间的取舍。``table``。 · 示例: `image_forensics_audit`
- `watermark_embed` `image2d × phash → image2d` GPU: 无 — DWT-DCT **数字水印**嵌入。返回含水印图像 ``(H, W)``。``image2d``。 · 示例: `image_forensics_audit`
- `watermark_extract` `image2d → phash` GPU: 无 — 水印的**盲提取**。返回一维 bool(``phash`` 词汇)。 · 示例: `image_forensics_audit`

### astrostack (14 ops / 6 categories)

#### astrostack / align (2)
- `align_frames` `images → images` GPU: 无 — 把一串帧对齐到一张基准帧上。 · 示例: `astro_stacking`
- `frame_align` `image2d × image2d → matrix` GPU: 无 — 由恒星对应估计 ``frame`` → ``reference`` 的 2-D 变换。 · 示例: `astro_stacking`, `poc_exoplanet_transit`, `poc_print_registration`

#### astrostack / cosmic (2)
- `cosmic_ray_reject` `image2d → image2d` GPU: 有(许可列表) — 单帧的宇宙线剔除(拉普拉斯锐度)。 · 示例: `astro_stacking`
- `cosmic_ray_reject_stack` `images → images` GPU: 有(许可列表) — 通过帧间比较剔除宇宙线 —— **同一处不会被击中两次**。 · 示例: `astro_stacking`

#### astrostack / photometry (3)
- `aperture_photometry` `image2d × keypoints → table` GPU: 无 — 圆形孔径 + 环形背景的测光(经典 CCD 测光)。 · 示例: `astro_stacking`, `poc_astro_photometry`, `poc_exoplanet_transit`, `poc_nuclei_ploidy`, `poc_real_file_formats`, `poc_real_sky_photometry`
- `psf_fit` `image2d × keypoints → table` GPU: 无 — 对星像拟合 PSF,得到中心与 FWHM。 · 示例: `astro_stacking`, `poc_star_astrometry`
- `star_detect` `image2d → keypoints` GPU: 无 — 检测恒星并返回 ``(row, col)`` 重心列表。 · 示例: `astro_stacking`, `poc_exoplanet_transit`, `poc_real_file_formats`, `poc_search_sweep_width`, `poc_star_astrometry`

#### astrostack / quality (3)
- `frame_quality` `image2d → table` GPU: 无 — 给单帧打分 —— 锐度、FWHM、背景、圆度,以及用于筛选的分数。 · 示例: `astro_stacking`
- `lucky_select` `images → indices` GPU: 有(许可列表) — 只保留质量分前 ``keep_fraction`` 的帧 —— lucky imaging 的筛选。 · 示例: `astro_stacking`, `poc_astro_photometry`
- `noise_sigma` `image2d → measurement` GPU: 无 — 稳健估计背景噪声 sigma(一个不被恒星污染的实数)。 · 示例: `astro_stacking`, `poc_colocalization_crosstalk`, `poc_search_sweep_width`, `poc_star_astrometry`, `poc_thermal_radiometry`

#### astrostack / stack (2)
- `drizzle_resample` `images → image2d` GPU: 无 — Drizzle —— 由若干亚像素错位的帧构建更细的网格(保面积)。 · 示例: `astro_stacking`, `poc_astro_photometry`, `poc_pixel_shift`, `poc_superresolution_limits`
- `sigma_clip_stack` `images → image2d` GPU: 有(许可列表) — 合成一串帧(均值 / 中位数 / κ-σ 剪裁),并给出采纳掩码。 · 示例: `astro_stacking`, `poc_astro_photometry`, `poc_exoplanet_transit`, `poc_river_surface_velocity`

#### astrostack / synth (2)
- `synth_frame_series` `无输入 → images` GPU: 无 — 把同一星场重拍 ``n_frames`` 次,**各自带不同噪声与不同抖动**。 · 示例: `astro_stacking`, `poc_astro_photometry`
- `synth_starfield` `无输入 → image2d` GPU: 无 — 合成一张已知的星场 —— **这一族真值的来源**。 · 示例: `astro_stacking`, `poc_astro_photometry`

### videostream (16 ops / 8 categories)

#### videostream / analysis (1)
- `scene_cut_detection` `video → table` GPU: 仅在链中(许可列表) — 整段片段的镜头边界:直方图卡方距离 → ``{"distance", "cut", "n"}``(``table``)。 · 示例: `video_streaming`

#### videostream / background (2)
- `running_gaussian_background` `video → video` GPU: 有(许可列表) — 自适应单高斯背景(滑动均值)逐帧 → ``(T, H, W)``(``video``)。 · 示例: `video_streaming`
- `running_gaussian_foreground` `video → video` GPU: 无 — 自适应单高斯前景掩码逐帧 → 0/1 ``(T, H, W)``(``video``)。 · 示例: `video_streaming`

#### videostream / denoise (1)
- `temporal_bilateral` `video → video` GPU: 有(许可列表) — 因果的时间双边去噪,逐帧 → ``(T, H, W)``(``video``)。 · 示例: `find_ops_by_meaning`, `video_streaming`

#### videostream / flow (1)
- `optical_flow_magnitude_stream` `video → video` GPU: 无 — 相对前一帧的稠密光流速度,逐帧 → ``(T, H, W)``(``video``)。 · 示例: `video_streaming`

#### videostream / motion (3)
- `motion_energy_image` `video → video` GPU: 无 — Bobick–Davis 的 Motion Energy Image 逐帧 → 0/1 ``(T, H, W)``(``video``)。 · 示例: `video_streaming`
- `motion_history_image` `video → video` GPU: 无 — Bobick–Davis 的 Motion History Image 逐帧 → ``[0, 1]`` 的 ``(T, H, W)``(``video``)。 · 示例: `video_streaming`
- `three_frame_difference` `video → video` GPU: 无 — Collins 三帧差分运动掩码,逐帧 → 0/1 ``(T, H, W)``(``video``)。 · 示例: `poc_periodic_video_boundary`, `video_streaming`

#### videostream / recursive (4)
- `exponential_background` `video → video` GPU: 无 — 递归背景 ``bg ← (1−α)·bg + α·frame`` 逐帧 → ``(T, H, W)``(``video``)。 · 示例: `video_streaming`
- `exponential_foreground` `video → video` GPU: 无 — 前景掩码 ``|frame − 指数背景| > threshold`` → 0/1 ``(T, H, W)``(``video``)。 · 示例: `video_streaming`
- `frame_difference_causal` `video → video` GPU: 无 — ``|frame t − frame t−1|``,首帧为零 → ``(T, H, W)``(``video``)。 · 示例: `video_streaming`
- `running_mean_std` `video → table` GPU: 有(许可列表) — 整段片段的 Welford 逐像素均值 / 总体标准差 → ``{"mean", "std", "n"}``(``table``)。 · 示例: `video_streaming`

#### videostream / restore (1)
- `deflicker` `video → video` GPU: 仅在链中(许可列表) — 逐帧的亮度去闪烁 → ``(T, H, W)``(``video``)。 · 示例: `video_streaming`

#### videostream / window (3)
- `background_subtraction_window` `video → video` GPU: 无 — 因果窗口中位数背景 → 逐帧 0/1 前景掩码 ``(T, H, W)``(``video``)。 · 示例: `video_streaming`
- `moving_average_window` `video → video` GPU: 无 — 最近 *window* 帧的逐像素因果均值 → ``(T, H, W)``(``video``)。 · 示例: `poc_periodic_video_boundary`, `poc_strain_history`, `video_streaming`
- `temporal_median_window` `video → video` GPU: 有(许可列表) — 最近 *window* 帧的逐像素因果中位数 → ``(T, H, W)``(``video``)。 · 示例: `video_streaming`

### profile (12 ops / 4 categories)

#### profile / compare (2)
- `profile_align` `pairs × pairs → pairs` GPU: 无 — 将实测轮廓对准设计轮廓。返回 ``(aligned, info)``。 · 示例: `profile_frame_tour`
- `profile_deviation` `pairs × pairs → table` GPU: 无 — 相对设计形状的**带符号法向偏差**。返回 dict。 · 示例: `profile_shape_inspection`

#### profile / frame (3)
- `profile_chord_frame` `pairs → table` GPU: 无 — 求弦(相距最远的 2 个点)。返回 dict。 · 示例: `profile_frame_tour`, `profile_shape_inspection`
- `profile_normalise` `pairs → pairs` GPU: 无 — 通过旋转和平移进行归一化，使弦长为 1、前缘位于原点、弦朝向 +x。 · 示例: `profile_frame_tour`
- `profile_resample` `pairs → pairs` GPU: 无 — 以等间距重新采样轮廓。``kind`` 目前只有 ``"arclength"``。 · 示例: `profile_frame_tour`

#### profile / measure (5)
- `profile_camber` `pairs → pairs` GPU: 无 — 中弧线(上下表面的中线)。返回 ``(n, 2)`` 的 ``(x, yc)``。 · 示例: `profile_shape_inspection`
- `profile_leading_edge_radius` `pairs → measurement` GPU: 无 — 前缘半径(与弦长之比)。对前缘附近的点拟合圆。 · 示例: `profile_shape_inspection`
- `profile_sides` `pairs → table` GPU: 无 — 将上表面和下表面提取为沿弦向坐标的函数。返回 dict。 · 示例: `profile_frame_tour`
- `profile_thickness` `pairs → pairs` GPU: 无 — 厚度分布 ``t(x)``。返回 ``(n, 2)`` 的 ``(x, t)``。 · 示例: `profile_shape_inspection`
- `profile_trailing_edge_gap` `pairs → measurement` GPU: 无 — 后缘开口(与弦长之比)。上表面与下表面后缘端点之间的距离。 · 示例: `profile_shape_inspection`

#### profile / synth (2)
- `profile_perturb` `pairs → pairs` GPU: 无 — 返回植入了已知量缺陷的轮廓。:data:`PERTURB_KINDS`。 · 示例: `profile_shape_inspection`
- `profile_synth_naca4` `无输入 → pairs` GPU: 无 — 以闭式生成 NACA 4 位数翼型。返回 ``(N, 2)`` 的一笔画轮廓。 · 示例: `profile_frame_tour`, `profile_shape_inspection`

### shapestat (16 ops / 5 categories)

#### shapestat / deviation (1)
- `signed_surface_distance` `points × points → signal` GPU: 无 — 查询点到曲面的**带符号**距离。→ ``(N,)``。 · 示例: `poc_am_thermal_to_ct`, `shapestat_landmark_tour`

#### shapestat / model (6)
- `shape_explained_variance` `shapemodel → signal` GPU: 无 — 各主成分的贡献率(合计为 1)。→ ``(k,)``。 · 示例: `shapestat_landmark_tour`
- `shape_mahalanobis` `shapemodel × points → measurement` GPU: 无 — 从模型来看该形状有多**异常**。→ float。 · 示例: `shapestat_landmark_tour`
- `shape_pca` `shapeset → shapemodel` GPU: 无 — 形态 PCA(统计形状模型)。→ dict(``shapemodel``)。 · 示例: `shapestat_landmark_tour`
- `shape_project` `shapemodel × points → signal` GPU: 无 — 将形状映射到模型坐标(主成分得分)。→ ``(k,)``。 · 示例: `shapestat_landmark_tour`
- `shape_reconstruct` `shapemodel × signal → points` GPU: 无 — 由得分还原形状。→ ``(N, 3)``。 · 示例: `shapestat_landmark_tour`
- `shape_synthesize` `shapemodel → points` GPU: 无 — 由模型生成 1 个**合理可信的新形状**。→ ``(N, 3)``。 · 示例: `shapestat_landmark_tour`

#### shapestat / procrustes (5)
- `generalized_procrustes` `shapeset → shapeset` GPU: 无 — 广义 Procrustes 分析(GPA)。把所有个体放入共同的坐标框架。→ ``(K, N, 3)``。 · 示例: `shapestat_landmark_tour`
- `procrustes_align` `points × points → points` GPU: 无 — 将 *source* 叠合到 *target* 上之后的点。→ ``(N, 3)``(应用 :func:`procrustes_fit`)。 · 示例: `shapestat_landmark_tour`
- `procrustes_distance` `points × points → measurement` GPU: 无 — Procrustes 距离 = 叠合之后逐点的 RMS。→ float。 · 示例: `shapestat_landmark_tour`
- `procrustes_fit` `points × points → matrix` GPU: 无 — 将 *source* 叠合到 *target* 上的相似变换。→ ``(4, 4)`` 的齐次矩阵。 · 示例: `poc_change_detection_misreg`, `poc_die_tilt_tsv_overlay`, `shapestat_landmark_tour`
- `shape_mean` `shapeset → points` GPU: 无 — 经 GPA 对齐之后的平均形状。→ ``(N, 3)``。 · 示例: `shapestat_landmark_tour`

#### shapestat / symmetry (2)
- `landmark_asymmetry` `points → signal` GPU: 无 — 每对左右标志点的**带符号**非对称量。→ ``(M,)``。 · 示例: `shapestat_landmark_tour`
- `mirror_plane_from_pairs` `points → matrix` GPU: 无 — 由左右对应的标志点求出正中面。→ ``(2, 3)``(第 1 行 = 点，第 2 行 = 法线)。 · 示例: `shapestat_landmark_tour`

#### shapestat / synth (2)
- `shape_perturb` `points → points` GPU: 无 — 对形状施加 1 个**已知的**变形。→ ``(N, 3)``。 · 示例: `shapestat_landmark_tour`
- `shape_synth_family` `无输入 → shapeset` GPU: 无 — 生成具有已知变形模式的形状族。→ ``(n_shapes, n_points, 3)``。 · 示例: `shapestat_landmark_tour`

### measure1d (17 ops / 4 categories)

#### measure1d / apply (2)
- `align_metrology_model` (halcon: `align_metrology_model`) `metrologymodel → metrologymodel` GPU: 无 — 平移计量模型的所有对象以进行对齐(align_metrology_model)。 · 示例: `poc_dimensional_inspection`
- `apply_metrology_model` (halcon: `apply_metrology_model`) `metrologymodel × image2d → table` GPU: 无 — 沿各计量对象参考形状的法线测量亚像素边缘，重新拟合形状并返回结果(apply_metrology_model)。 · 示例: `example_inner_diameter_mm`, `poc_calipers_under_illusion`, `poc_dimensional_inspection`, `poc_telecentric_metrology`

#### measure1d / caliper (6)
- `fuzzy_measure_pairing` (halcon: `fuzzy_measure_pairing`) `image2d × measurehandle → table` GPU: 无 — 选择最符合模糊准则(预期宽度 pair_size)的边缘对(fuzzy_measure_pairing)。 · 示例: `poc_calipers_under_illusion`, `poc_dimensional_inspection`
- `gen_measure_arc` (halcon: `gen_measure_arc`) `无输入 → measurehandle` GPU: 无 — 定义测量弧(沿圆周方向以 ≈1 px 间隔取剖面)(gen_measure_arc)。采样数 n = round(|angle_extent|*radius)+1，``spacing`` = 弧长/(n-1)。 · 示例: `poc_dimensional_inspection`
- `gen_measure_rectangle2` (halcon: `gen_measure_rectangle2`) `无输入 → measurehandle` GPU: 无 — 定义旋转测量矩形(沿长轴 ``phi`` 方向以 1 px 间隔取剖面)(gen_measure_rectangle2)。采样数 n = max(2, round(2*length1)+1)，起点位于距中心 -(n-1)/2 px 处。``length2`` 为宽度方向的平均宽度 [px]。 · 示例: `example_scratch_width`, `poc_barcode_1d`, `poc_battery_electrode_breathing`, `poc_calipers_under_illusion`, `poc_dimensional_inspection`, `poc_screw_thread_metrology`, `poc_solar_limb_darkening`, `poc_telecentric_metrology`, `poc_tree_ring_dendro`, `poc_water_level`, `poc_weld_bead_profile`, `poc_weld_radiograph_porosity`
- `measure_pairs` (halcon: `measure_pairs`) `image2d × measurehandle → table` GPU: 无 — 提取上升/下降边缘对(结构的宽度)(measure_pairs)。``first``/``second`` = 各边缘的 ``pos``，``width`` = 宽度 [px]，``first_point``/``second_point`` = (row, col)。 · 示例: `example_scratch_width`, `poc_calipers_under_illusion`, `poc_dimensional_inspection`, `poc_weld_radiograph_porosity`
- `measure_pos` (halcon: `measure_pos`) `image2d × measurehandle → table` GPU: 无 — 提取测量线上的边缘位置(亚像素)和幅值(measure_pos)。 · 示例: `poc_barcode_1d`, `poc_battery_electrode_breathing`, `poc_calipers_under_illusion`, `poc_dimensional_inspection`, `poc_screw_thread_metrology`, `poc_solar_limb_darkening`, `poc_telecentric_metrology`, `poc_tree_ring_dendro`, `poc_water_level`, `poc_weld_bead_profile`, `poc_weld_radiograph_porosity`
- `translate_measure` (halcon: `translate_measure`) `measurehandle → measurehandle` GPU: 无 — 平移测量对象(translate_measure)。 · 示例: `poc_dimensional_inspection`

#### measure1d / model (6)
- `add_metrology_object_circle_measure` (halcon: `add_metrology_object_circle_measure`) `metrologymodel → scalar` GPU: 无 — 添加圆计量对象(add_metrology_object_circle_measure)。 · 示例: `example_inner_diameter_mm`, `poc_calipers_under_illusion`, `poc_dimensional_inspection`, `poc_telecentric_metrology`
- `add_metrology_object_ellipse_measure` (halcon: `add_metrology_object_ellipse_measure`) `metrologymodel → scalar` GPU: 无 — 添加椭圆计量对象(add_metrology_object_ellipse_measure)。``phi`` = ``ra`` 轴的方向(从 col 轴起算，弧度)。 · 示例: `poc_dimensional_inspection`
- `add_metrology_object_generic` (halcon: `add_metrology_object_generic`) `metrologymodel → scalar` GPU: 无 — 添加通用计量对象(add_metrology_object_generic)。 · 示例: `poc_dimensional_inspection`
- `add_metrology_object_line_measure` (halcon: `add_metrology_object_line_measure`) `metrologymodel → scalar` GPU: 无 — 添加直线计量对象(add_metrology_object_line_measure)。返回 index。 · 示例: `poc_calipers_under_illusion`, `poc_dimensional_inspection`
- `add_metrology_object_rectangle2_measure` (halcon: `add_metrology_object_rectangle2_measure`) `metrologymodel → scalar` GPU: 无 — 添加矩形计量对象(add_metrology_object_rectangle2_measure)。``phi`` = ``l1`` 边的方向(从 col 轴起算，弧度)，``l1``/``l2`` = 半边长。 · 示例: `poc_dimensional_inspection`
- `create_metrology_model` (halcon: `create_metrology_model`) `无输入 → metrologymodel` GPU: 无 — 创建空的计量模型(create_metrology_model)。 · 示例: `example_inner_diameter_mm`, `poc_calipers_under_illusion`, `poc_dimensional_inspection`, `poc_telecentric_metrology`

#### measure1d / scale (3)
- `mm_per_px_from_reference` `measurement → measurement` GPU: 无 — 由已知尺寸的标准物(比例尺、基准孔、量规)求出像素间距 mm/px(标定)。 · 示例: `example_inner_diameter_mm`, `example_scratch_width`
- `pixel_to_world` `measurement → measurement` GPU: 无 — 把以像素测得的一个长度换算为实际尺寸 mm(``value_px * mm_per_px``)。 · 示例: `example_inner_diameter_mm`
- `table_px_to_mm` `table → table` GPU: 无 — 给测量结果表(``measure_pairs`` / ``apply_metrology_model`` 的返回值)添加 mm 列。 · 示例: `example_inner_diameter_mm`, `example_scratch_width`

### roughness (9 ops / 3 categories)

#### roughness / measure (3)
- `profile_params` `signal → table` GPU: 无 — 截面粗糙度参数 Ra/Rq/Rz/Rt/Rp/Rv/Rsk/Rku(ISO 4287)。 · 示例: `poc_food_cutting_measure`, `poc_surface_roughness`
- `surface_params` `depth → table` GPU: 无 — 面粗糙度参数 Sa/Sq/Sp/Sv/Sz/Ssk/Sku/Sdq/Sdr(ISO 25178-2)。 · 示例: `poc_polish_wipe_measure`, `poc_surface_roughness`
- `surface_psd` `depth → pairs` GPU: 有(许可列表) — 高度场的功率谱密度。返回 ``(q, C)``。**约定通过参数明确指定。** · 示例: `poc_surface_roughness`

#### roughness / prepare (5)
- `robust_gaussian_profile` `signal → signal` GPU: 无 — 稳健高斯回归滤波器(截面):不被离群点和划痕拖动的平均线与粗糙度。 · 示例: `example_robust_profile_filter`, `poc_robust_profile_filter`
- `robust_gaussian_surface` `depth → depth` GPU: 无 — 稳健高斯回归滤波器(曲面):不被划痕和突起拖动的曲面波纹度与粗糙度。 · 示例: `poc_robust_profile_filter`
- `robust_spline_profile` `signal → signal` GPU: 无 — 稳健样条滤波器(截面):不被离群点拖动的平均线与粗糙度。 · 示例: `poc_robust_profile_filter`
- `surface_filter` `depth → depth` GPU: 仅在链中(许可列表) — 将高度场分解为粗糙度和波纹度(ISO 16610-21 的高斯滤波器)。 · 示例: `poc_robust_profile_filter`, `poc_surface_roughness`
- `surface_form_remove` `depth → depth` GPU: 仅在链中(许可列表) — 直接在网格上去除平面 / 二次曲面。返回 ``(residual, coeffs)``。 · 示例: `poc_polish_wipe_measure`, `poc_pv_thermal_survey`, `poc_surface_roughness`

#### roughness / synth (1)
- `surface_synth_psd` `无输入 → depth` GPU: 无 — 由指定的 PSD 合成高度场。返回 ``(z, sq_analytic)``。 · 示例: `poc_polish_wipe_measure`, `poc_surface_roughness`

### shape2d (17 ops / 2 categories)

#### shape2d / descriptor (11)
- `contour_epicycle_chain` `matrix → pairs` GPU: 无 — 返回相位 ``t`` 处的**旋转摆臂链**(``pairs``)。 · 示例: `poc_one_stroke_epicycles`
- `contour_fourier_complex` `pairs → matrix` GPU: 无 — 将闭合轮廓转换为复傅里叶级数的系数 —— ``z(t) = Σ c_k exp(2πi k t)``。 · 示例: `poc_one_stroke_epicycles`
- `contour_fourier_truncation_energy` `matrix → table` GPU: 无 — 每个截断阶数**预测的**误差(``table``)—— 帕塞瓦尔的精确式。 · 示例: `poc_one_stroke_epicycles`
- `descriptor_distance` `efdmodel × efdmodel → measurement` GPU: 无 — 2 个形状之间的距离(越小形状越相似)。对旋转/平移/起点/(可选)尺度不变。 · 示例: `contour_fourier`, `shape2d_morph_descriptor_tour`
- `elliptic_fourier` `pairs → efdmodel` GPU: 无 — 以 Kuhl–Giardina 闭式求闭合轮廓的椭圆傅里叶系数。 · 示例: `contour_fourier`, `shape2d_morph_descriptor_tour`
- `fit_circle_xld` `contour → table` GPU: 无 — 对每条 XLD 轮廓拟合圆，返回圆心的行、列和半径（``table``）。 · 示例: `fit_circle_xld_bore`
- `fourier_smooth` `pairs → pairs` GPU: 无 — 用复数 FFT 对轮廓进行带限处理以实现平滑。 · 示例: `contour_fourier`
- `from_xld` `table → pairs` GPU: 无 — 从 XLD 轮廓 dict(``{"shape", "cs":[Nx2,...]}``)中取出第 i 个轮廓。 · 示例: `shape2d_morph_descriptor_tour`
- `invariants` `efdmodel → pairs` GPU: 无 — 对旋转、平移、起点以及(可选)尺度不变的形状描述子((N,2))。 · 示例: `shape2d_morph_descriptor_tour`
- `normalize` `efdmodel → matrix` GPU: 无 — 将 EFD 系数变换为“规范姿态”的系数(以第 1 谐波为基准对齐)。 · 示例: `piv_flow_from_particles`, `poc_exoplanet_transit`
- `reconstruct` `efdmodel → pairs` GPU: 无 — 由 EFD 系数重建轮廓((M,2))。 · 示例: `contour_fourier`

#### shape2d / morph (6)
- `add_frame_corners` `pairs → pairs` GPU: 无 — 将图像的四个角(+各边中点)作为固定点加入点集。 · 示例: `shape2d_morph_descriptor_tour`
- `blend` `image2d × image2d → image2d` GPU: 无 — 交叉溶解 (1-alpha)·a + alpha·b(a、b 形状相同，取值 [0,1])。 · 示例: `image_morph`, `poc_live4d`
- `morph` `image2d × image2d × pairs × pairs → image2d` GPU: 有(许可列表) — 通过对应点对 2 张图像 A、B 进行变形(morph)，生成比例 alpha 的中间图像。 · 示例: `image_morph`, `poc_vanishing_detail_and_morphing_area`
- `morph_sequence` `image2d × image2d × pairs × pairs → images` GPU: 无 — 将 alpha 以 n 步从 0→1 变化得到的变形序列(从 A 平滑变化到 B 的各帧)。 · 示例: `image_morph`
- `warp_piecewise_affine` `image2d × pairs × pairs → image2d` GPU: 无 — 将 img 中 src_pts 处的内容移动到 dst_pts 的分段仿射变形。 · 示例: `shape2d_morph_descriptor_tour`
- `warp_tps_image` `image2d × pairs × pairs → image2d` GPU: 有(许可列表) — 用薄板样条将 img 的 src_pts 移动到 dst_pts 的平滑变形。 · 示例: `shape2d_morph_descriptor_tour`

### piv (29 ops / 7 categories)

#### piv / assess (4)
- `piv_error_stats` `flow2d × flow2d → table` GPU: 无 — 与真值之差的分解。**将偏差与离散分开**返回。 · 示例: `piv_field_analysis_tour`, `piv_flow_from_particles`, `poc_river_surface_velocity`, `poc_strain_history`
- `piv_peak_locking` `flow2d → table` GPU: 无 — 峰值锁定的强度：小数部分的分布偏离均匀分布的程度。 · 示例: `piv_field_analysis_tour`, `poc_battery_electrode_breathing`
- `piv_sample_at_windows` `flow2d → flow2d` GPU: 无 — 将逐像素的场 ``(2, H, W)`` 落到窗口中心的网格上(最近邻)。 · 示例: `piv_field_analysis_tour`, `piv_flow_from_particles`, `poc_river_surface_velocity`, `poc_strain_history`
- `piv_time_statistics` `images → table` GPU: 无 — 图像序列 → 时间平均、脉动的 RMS、雷诺应力。 · 示例: `piv_field_analysis_tour`

#### piv / estimate (4)
- `piv_cross_correlate` `image2d × image2d → flow2d` GPU: 无 — 通过逐窗口的互相关求出位移场。返回 ``(flow, info)``。 · 示例: `piv_field_analysis_tour`, `piv_flow_from_particles`, `poc_beam_modal_video`, `poc_change_detection_misreg`, `poc_dic_strain`, `poc_print_registration`, `poc_river_surface_velocity`, `poc_strain_history`, `poc_superresolution_limits`, `poc_tacsim_marker_shear`
- `piv_deform_pass` `image2d × image2d × flow2d → flow2d` GPU: 无 — 带窗口变形的 1 级。先用预测位移**使图像本身变形之后**再求相关。 · 示例: `piv_field_analysis_tour`
- `piv_ensemble_correlate` `images → flow2d` GPU: 无 — 将相关图**相加之后**再寻找峰值(集成相关)。 · 示例: `piv_field_analysis_tour`, `poc_river_surface_velocity`
- `piv_multipass` `image2d × image2d → flow2d` GPU: 无 — 从粗窗口逐级降到细窗口的多级 PIV。返回 ``(flow, info)``。 · 示例: `piv_field_analysis_tour`, `piv_flow_from_particles`, `poc_strain_history`

#### piv / field (8)
- `piv_divergence` `flow2d → image2d` GPU: 无 — 散度 ``d(dy)/dy + d(dx)/dx``。**不可压缩时为 0** —— 可用作独立的验算。 · 示例: `piv_flow_from_particles`, `poc_what_a_picture_cannot_check`
- `piv_flow_magnitude` `flow2d → image2d` GPU: 无 — ``sqrt(dy^2 + dx^2)``。舍弃方向的**单向**变换。 · 示例: `piv_field_analysis_tour`, `poc_sheet_deformation_ffd`, `poc_what_a_picture_cannot_check`
- `piv_q_criterion` `flow2d → image2d` GPU: 无 — Q 判据 ``-tr(J^2)/2``。在**旋转超过应变**的位置为正。 · 示例: `piv_field_analysis_tour`
- `piv_strain_rate` `flow2d → image2d` GPU: 无 — 应变率的大小 ``sqrt(2 e_ij e_ij)``。刚体旋转时为 0。 · 示例: `piv_field_analysis_tour`
- `piv_swirling_strength` `flow2d → image2d` GPU: 无 — 旋涡强度 λ_ci —— 速度梯度张量复特征值虚部的大小。 · 示例: `piv_field_analysis_tour`
- `piv_to_velocity` `flow2d → flow2d` GPU: 无 — 像素/帧 → m/s。**两者都是必需参数**(不设默认值)。 · 示例: `piv_flow_from_particles`, `poc_river_surface_velocity`
- `piv_velocity_gradient` `flow2d → table` GPU: 无 — 一并返回速度梯度张量的各分量及由其导出的量。 · 示例: `piv_field_analysis_tour`
- `piv_vorticity` `flow2d → image2d` GPU: 无 — 涡量 ``d(dx)/dy - d(dy)/dx``。**逆时针为正**(在图像坐标中的定义)。 · 示例: `piv_flow_from_particles`, `poc_tactile_dipole_torque`, `poc_what_a_picture_cannot_check`

#### piv / solid (3)
- `correlation_quality` `image2d × image2d × flow2d → image2d` GPU: 无 — 逐点返回给定位移场**吻合程度**的 ZNCC 图。 · 示例: `piv_field_analysis_tour`
- `speckle_quality` `image2d → table` GPU: 无 — 用 4 个数字返回所拍摄的散斑是否适合 DIC。 · 示例: `piv_field_analysis_tour`
- `strain_from_displacement` `image2d × image2d → image2d` GPU: 有(许可列表) — 由位移场求应变场。返回 ``(exx, eyy, exy)``。 · 示例: `poc_dic_strain`

#### piv / synth (3)
- `piv_synth_pair` `无输入 → image2d` GPU: 无 — 生成具有已知位移场的图像对。返回 ``(image_a, image_b, truth)``。 · 示例: `piv_field_analysis_tour`, `piv_flow_from_particles`, `poc_strain_history`
- `piv_synth_particles` `无输入 → image2d` GPU: 无 — 生成 1 张撒布了示踪粒子的图像。返回 ``(image, positions)``。 · 示例: `piv_field_analysis_tour`
- `piv_synth_sequence` `无输入 → images` GPU: 无 — 同一批粒子被反复移动而得到的图像序列。返回 ``(frames, truth)``。 · 示例: `piv_field_analysis_tour`

#### piv / validate (2)
- `piv_outlier_mask` `flow2d → mask` GPU: 无 — 用归一化中值检验(Westerweel & Scarano 2005)找出离群矢量。 · 示例: `perf_hankel_plan_and_piv_stream`, `piv_flow_from_particles`, `poc_change_detection_misreg`, `poc_river_surface_velocity`
- `piv_replace_outliers` `flow2d × mask → flow2d` GPU: 无 — 用邻域填补离群值。若 ``method="nan"`` 则**不填补而记为缺测**。 · 示例: `piv_flow_from_particles`, `poc_river_surface_velocity`

#### piv / visualise (5)
- `piv_flow_to_rgbimage` `flow2d → rgb` GPU: 无 — 色相 = 方向、明度 = 速度的标准流场可视化。返回 ``(h, w, 3)``。 · 示例: `piv_field_analysis_tour`
- `piv_line_integral_convolution` `flow2d → image2d` GPU: 无 — 线积分卷积(LIC)—— 沿流动方向模糊白噪声而得的纹理图像。 · 示例: `piv_field_analysis_tour`
- `piv_quiver` `flow2d → rgb` GPU: 无 — 箭头图(MATLAB 的 ``quiver``)。返回 ``(h*upsample, w*upsample, 3)``。 · 示例: `piv_field_analysis_tour`
- `piv_streamline_image` `flow2d → rgb` GPU: 无 — 流线图(MATLAB 的 ``streamslice``)。返回 ``(h*upsample, w*upsample, 3)``。 · 示例: `piv_field_analysis_tour`
- `piv_streamlines` `flow2d → table` GPU: 无 — 用 RK4 追踪流线(相当于 MATLAB 的 ``stream2`` / ``streamslice``)。 · 示例: `piv_field_analysis_tour`

### blob (11 ops / 5 categories)

#### blob / connect (1)
- `blob_label` `mask → labels2d` GPU: 仅在链中(许可列表) — 将二值区域划分为连通分量，返回 ``int32`` 的标签图像(背景 0，物体 1..n)。 · 示例: `blob_split_tour`, `poc_am_thermal_to_ct`, `poc_bone_trabecular_thickness`, `poc_bump_coplanarity`, `poc_dense_bubble_count`, `poc_em_split_merge_score`, `poc_fresco_craquelure`, `poc_gear_tooth_metrology`, `poc_gravitational_lens_invariants`, `poc_leaf_disease_area`, `poc_machine_condition_fusion`, `poc_metal_grain_size`, `poc_nuclei_ploidy`, `poc_particle_sizing`, `poc_particle_tracking`, `poc_peg_insertion_tactile`, `poc_pipe_wall_loss`, `poc_powder_grinding_ae`, `poc_print_warpage_risk`, `poc_pv_thermal_survey`, `poc_real_coin_metrology`, `poc_real_sem_metal_layer`, `poc_rotation_invariance_audit`, `poc_sea_ice_concentration`, `poc_segmentation_gauntlet`, `poc_sem_wafer_defect_edge_bias`, `poc_solar_el_inspection`, `poc_solder_fillet_aoi`, `poc_timelapse_growth`, `poc_traffic_counting`, `poc_vessel_network`, `poc_weld_radiograph_porosity`, `poc_wound_area_tracking`

#### blob / extract (3)
- `blob_boundaries` `labels2d → mask` GPU: 无 — 物体的轮廓(1 像素宽，bool)。**相邻物体之间的分界也会保留**。 · 示例: `poc_gear_tooth_metrology`, `poc_real_sem_metal_layer`
- `blob_overlay` `image2d × labels2d → rgb` GPU: 有(许可列表) — 在原图像上按颜色区分叠加物体，返回 ``(H, W, 3)`` 的 float RGB。 · 示例: `poc_bump_coplanarity`, `poc_fresco_craquelure`, `poc_gear_tooth_metrology`, `poc_leaf_disease_area`, `poc_metal_grain_size`, `poc_nuclei_ploidy`, `poc_particle_sizing`, `poc_powder_grinding_ae`, `poc_weld_radiograph_porosity`
- `blob_region` `labels2d → mask` GPU: 无 — 将 1 个物体提取为二值区域(bool)。``index`` **从 1 开始**。 · 示例: `poc_gear_tooth_metrology`, `poc_particle_sizing`

#### blob / measure (1)
- `blob_features` `labels2d → table` GPU: 无 — 将每个物体的形状特征量以**每个键 1 个数组**的形式返回。 · 示例: `poc_am_thermal_to_ct`, `poc_bone_trabecular_thickness`, `poc_bump_coplanarity`, `poc_dense_bubble_count`, `poc_fresco_craquelure`, `poc_gear_tooth_metrology`, `poc_leaf_disease_area`, `poc_metal_grain_size`, `poc_nuclei_ploidy`, `poc_particle_sizing`, `poc_particle_tracking`, `poc_peg_insertion_tactile`, `poc_print_warpage_risk`, `poc_pv_thermal_survey`, `poc_real_coin_metrology`, `poc_real_sem_metal_layer`, `poc_rotation_invariance_audit`, `poc_sea_ice_concentration`, `poc_sem_wafer_defect_edge_bias`, `poc_solar_el_inspection`, `poc_solder_fillet_aoi`, `poc_traffic_counting`, `poc_vessel_network`, `poc_weld_radiograph_porosity`, `poc_wound_area_tracking`

#### blob / select (2)
- `blob_select` `labels2d → labels2d` GPU: 无 — 只保留特征量落在 ``[vmin, vmax]`` 内的物体(**编号从 1 开始重新分配**)。 · 示例: `poc_particle_sizing`, `poc_pipe_wall_loss`, `poc_pv_thermal_survey`, `poc_solar_el_inspection`, `poc_weld_radiograph_porosity`
- `blob_select_largest` `labels2d → labels2d` GPU: 无 — 按面积从大到小只保留 ``count`` 个(**编号按面积降序重新分配**)。 · 示例: `poc_am_thermal_to_ct`, `poc_gear_tooth_metrology`, `poc_solder_fillet_aoi`, `poc_wound_area_tracking`

#### blob / split (4)
- `blob_count_interval` `mask → table` GPU: 无 — 对重叠的物体计数。**无法确定时返回区间而不是个数**(fail-closed)。 · 示例: `poc_dense_bubble_count`
- `blob_distance` `mask → image2d` GPU: 有(许可列表) — 前景各像素到**最近背景**的距离。单位为 ``spacing`` 的倍数。 · 示例: `blob_split_tour`, `poc_bone_trabecular_thickness`, `poc_dense_bubble_count`, `poc_real_sem_metal_layer`, `poc_segmentation_gauntlet`
- `blob_seeds` `image2d → labels2d` GPU: 无 — h-maxima 种子。**``h`` 是与 ``distance`` 同单位的绝对值**。 · 示例: `blob_split_tour`, `poc_dense_bubble_count`
- `blob_split` `labels2d × labels2d × image2d → labels2d` GPU: 无 — 从种子出发**按从高到低的顺序**扩展区域，分割融合在一起的团块(分水岭)。 · 示例: `blob_split_tour`, `poc_dense_bubble_count`

### dem (25 ops / 5 categories)

#### dem / geodesy (12)
- `dem_cell_size_webmercator` `无输入 → measurement` GPU: 无 — Web 墨卡托瓦片的地面分辨率 [m/px]。**随纬度变化**。 · 示例: `dem_geodesy_tour`
- `dem_datum_shift_3param` `无输入 → points` GPU: 无 — 大地基准(datum)的转换 —— 地心 3 参数平移(``points``)。 · 示例: `poc_geodetic_benchmarks_real`, `poc_geodetic_height_frames`
- `dem_earth_curvature_drop` `无输入 → measurement` GPU: 无 — 视线计算中的**地球曲率下降量** [m]。``(1 - k) d^2 / (2 R)``。 · 示例: `dem_geodesy_tour`, `poc_geodetic_height_frames`
- `dem_ecef_to_geodetic` `points → points` GPU: 无 — ECEF → 大地坐标。返回 ``(..., 3)`` 的 ``(纬度[度], 经度[度], 高度[m])``。 · 示例: `dem_geodesy_tour`, `poc_geodetic_benchmarks_real`, `poc_geodetic_height_frames`
- `dem_enu_from_geodetic` `无输入 → points` GPU: 无 — 大地坐标 → 参考点周围的**局部 ENU**(东、北、上)[m] (``points``)。 · 示例: `poc_geodetic_benchmarks_real`, `poc_geodetic_height_frames`
- `dem_geocentric_grid` `depth → pointmap` GPU: 有(许可列表) — 将 DEM 的各格子单元转换为**从地球中心看到的坐标**。 · 示例: `dem_geodesy_tour`
- `dem_geodetic_from_enu` `points → points` GPU: 无 — 局部 ENU → 大地坐标(:func:`dem_enu_from_geodetic` 的逆变换)。``points``。 · 示例: `poc_geodetic_benchmarks_real`, `poc_geodetic_height_frames`
- `dem_geodetic_slope` `depth → image2d` GPU: 有(许可列表) — **经纬度网格**(等角度间隔)DEM 的坡度。格子单元尺寸随纬度变化。 · 示例: `dem_geodesy_tour`
- `dem_geodetic_to_ecef` `无输入 → points` GPU: 无 — 大地坐标(纬度、经度、椭球高)→ **地心直角坐标 ECEF** [m]。 · 示例: `dem_geodesy_tour`, `poc_geodetic_benchmarks_real`, `poc_geodetic_height_frames`
- `dem_geoid_height` `depth → signal` GPU: 无 — 按纬度、经度对大地水准面高网格做**双线性插值**，返回 ``N`` [m] (``signal``)。 · 示例: `poc_geodetic_benchmarks_real`, `poc_geodetic_height_frames`
- `dem_height_frame_convert` `signal × signal → signal` GPU: 无 — 转换高度的**基准**：椭球高 ``h`` ↔ 海拔高 ``H``(``H = h - N``)。``signal``。 · 示例: `poc_geodetic_benchmarks_real`, `poc_geodetic_height_frames`
- `dem_height_frame_residual` `signal × signal × signal → table` GPU: 仅在链中(许可列表) — ``h - H - N`` 的残差 —— **不让高度混淆悄无声息地通过**的检测器(``table``)。 · 示例: `poc_geodetic_benchmarks_real`

#### dem / hydrology (4)
- `dem_fill_sinks` `depth → depth` GPU: 无 — 填平洼地后的 DEM。Barnes, Lehman & Mulla (2014) 的 priority-flood。 · 示例: `poc_dem_terrain`
- `dem_flow_accumulation` `depth → image2d` GPU: 无 — 汇水格子单元数：流入各格子单元的上游格子单元个数(本格子单元计为 1)。 · 示例: `dem_terrain_analysis_tour`, `poc_dem_terrain`
- `dem_flow_direction` `depth → labels` GPU: 有(许可列表) — D8 流向。O'Callaghan & Mark (1984)。 · 示例: `dem_terrain_analysis_tour`, `poc_geodetic_height_frames`
- `dem_stream_network` `depth → image2d` GPU: 无 — 将汇水量超过阈值的格子单元视为河道的二值掩膜。 · 示例: `dem_terrain_analysis_tour`

#### dem / shading (1)
- `dem_hillshade` `depth → image2d` GPU: 有(许可列表) — 地形晕渲 [0,1]。``azimuth_deg`` 为光源方位(北为 0 度，向东旋转)。 · 示例: `poc_dem_terrain`, `poc_lidar_terrain_change`, `poc_stockpile_volume`

#### dem / surface (5)
- `dem_aspect` `depth → image2d` GPU: 有(许可列表) — 坡向 [度]。**北为 0 度，向东旋转**。平坦的格子单元为 :data:`ASPECT_FLAT`。 · 示例: `poc_dem_terrain`, `poc_geodetic_height_frames`
- `dem_curvature` `depth → image2d` GPU: 有(许可列表) — 曲率 [1/m]。``kind`` 为 ``"profile"``(剖面) / ``"planform"``(平面) / ``"total"``。 · 示例: `poc_dem_terrain`
- `dem_roughness` `depth → image2d` GPU: 有(许可列表) — 地形起伏指数 TRI —— 与 8 邻域高程差的均方根 [m]。 · 示例: `dem_terrain_analysis_tour`
- `dem_slope` `depth → image2d` GPU: 有(许可列表) — 坡度角。``units`` 为 ``"degrees"`` / ``"radians"`` / ``"percent"``。 · 示例: `dem_geodesy_tour`, `poc_crop_phenotyping`, `poc_dem_terrain`, `poc_geodetic_height_frames`, `poc_lidar_terrain_change`, `poc_multibeam_bathymetry`, `poc_stockpile_volume`
- `dem_tpi` `depth → image2d` GPU: 有(许可列表) — 地形位置指数 TPI —— 本格子单元与 8 邻域均值之差 [m]。正为山脊，负为山谷。 · 示例: `dem_terrain_analysis_tour`

#### dem / visibility (3)
- `dem_horizon_angle` `depth → image2d` GPU: 无 — 指定方位的地平线仰角 [度]。0 为水平，90 表示正上方被遮挡。 · 示例: `dem_terrain_analysis_tour`
- `dem_sky_view_factor` `depth → image2d` GPU: 无 — 天空可视因子 [0,1]。能看到多少天空。 · 示例: `poc_dem_terrain`
- `dem_viewshed` `depth → image2d` GPU: 无 — 从 1 个点出发的可视区域(1 = 可见)。判定视线是否被地形遮挡。 · 示例: `dem_terrain_analysis_tour`, `poc_stockpile_volume`

### conngraph (28 ops / 7 categories)

#### conngraph / activity (3)
- `graph_activation_latency` `matrix → labels` GPU: 仅在链中(许可列表) — 各节点首次“点亮”的步(从 0 开始)组成的序列 (n,)，整数。从未点亮的节点为 −1。 · 示例: `poc_malecns_activity_wave`
- `graph_activity_spread` `matrix × points × labels → table` GPU: 无 — 活动扩散范围的时间序列表：列 step / mean_distance / active_fraction / source_fraction。 · 示例: `poc_malecns_activity_wave`, `poc_microns_brain_wave`
- `points_activity_video` `points × matrix → rgbvideo` GPU: 无 — 将活动叠加到点云上并旋转的彩色视频 (F, H, W, 3)，值 [0, 1]。F = T × substeps、H = size、W = size × aspect。 · 示例: `poc_connectome_motor_bottleneck`, `poc_em_branch_territory`, `poc_em_second_opinion`, `poc_eye_to_brain`, `poc_malecns_activity_wave`, `poc_microns_brain_wave`

#### conngraph / circuit (1)
- `graph_conductance_states` `conn_graph × matrix → matrix` GPU: 无 — 把连线 ``W`` **直接当作电路运行**得到的膜电位时间序列 ``(T, n)``(``matrix``，无学习)。 · 示例: `poc_fly_optomotor_steering`

#### conngraph / construct (3)
- `graph_binarize` `conn_graph → conn_graph` GPU: 无 — 将 |W| > thresh 的边设为 1.0、其余设为 0.0 的 conn_graph(对角线也遵循同一规则)。 · 示例: `gallery_conngraph_closed_forms`
- `graph_degree_preserving_shuffle` `conn_graph → conn_graph` GPU: 无 — 保度洗牌(零模型)：保持各节点的入度、出度及权重的多重集合不变，重新连接边。 · 示例: `poc_larval_connectome_reservoir`, `poc_malecns_activity_wave`, `poc_microns_brain_wave`
- `graph_from_synapses` `synapse_table → conn_graph` GPU: 无 — 将突触表 (m, 3) = (pre_id, post_id, count) 转换为 n×n 的加权有向邻接矩阵。 · 示例: `poc_fly_optomotor_steering`, `poc_microns_brain_wave`, `type_connectivity_tour`

#### conngraph / dimension (4)
- `graph_block_shuffle` `conn_graph × labels → conn_graph` GPU: 无 — 按层(标签)的每个区块**打乱发送方**的对照 ``conn_graph``：保持每个接收方所接收权重的多重集合与层间的总连线量不变，只破坏“来自谁”。 · 示例: `poc_connectome_motor_bottleneck`
- `graph_layer_propagate` `conn_graph × labels × matrix → matrix` GPU: 无 — 将层 0 的状态 ``U`` (N, n_0) 经由区块 ``W[layer a → layer a+1]`` **逐级向前**传递，得到全部层的状态 ``(N, n)``(``matrix``，列按节点顺序，层 0 的列就是 ``U`` 本身)。 · 示例: `poc_connectome_motor_bottleneck`
- `states_layer_dimension` `matrix × labels → table` GPU: 无 — 每层有效维数的表：列 layer / n / participation_ratio / ratio(= PR / n)。 · 示例: `poc_connectome_motor_bottleneck`
- `states_participation_ratio` `matrix → measurement` GPU: 无 — 状态序列 ``X`` (N, n) 的**有效维数** = participation ratio ``PR = (Σλ)² / Σλ²``(λ 为协方差的特征值，Gao et al. 2017)。若所有列独立且方差相同则为 n，若落在 1 个方向上则为 1。 · 示例: `poc_connectome_motor_bottleneck`

#### conngraph / reservoir (5)
- `reservoir_encode` `conn_graph × matrix → matrix` GPU: 无 — 静态输入的批量 reservoir 编码(用于分类)：将 X 的每一行从零状态运行 steps 次后的最终状态 (N, n)。 · 示例: `poc_larval_connectome_reservoir`
- `reservoir_from_graph` `conn_graph → conn_graph` GPU: 无 — 将 W 乘以常数使其谱半径为 rho 的 conn_graph(echo state 的预处理)。半径为 0 时拒绝。 · 示例: `poc_larval_connectome_reservoir`, `poc_malecns_activity_wave`
- `reservoir_states` `conn_graph × matrix → matrix` GPU: 无 — reservoir 的状态序列：x_{t+1} = (1−leak) x_t + leak · f(Wᵀ x_t + W_in u_t)。返回 (T − washout, n)。 · 示例: `poc_malecns_activity_wave`, `poc_microns_brain_wave`
- `ridge_predict` `matrix × matrix → matrix` GPU: 无 — 用读出权重进行预测 (T, k) = [X, 1] · Wout。Wout 为 ridge_readout 的 (d+1, k)。 · 示例: `poc_larval_connectome_reservoir`
- `ridge_readout` `matrix × matrix → matrix` GPU: 有(许可列表) — 岭回归的读出权重 (d+1, k) = (X̃ᵀX̃ + αI)⁻¹ X̃ᵀY，X̃ = [X, 1] (附加偏置列)。 · 示例: `poc_larval_connectome_reservoir`

#### conngraph / stats (9)
- `graph_betweenness` `conn_graph → signal` GPU: 无 — 介数中心性(Brandes 2001，二值有向，不归一化)。每个节点一个值、长度为 n 的数组。 · 示例: `gallery_conngraph_closed_forms`
- `graph_clustering_coefficient` `conn_graph → measurement` GPU: 无 — 平均局部聚类系数(折叠方向后的二值图，Watts–Strogatz)。度 < 2 的节点计为 0。 · 示例: `gallery_conngraph_closed_forms`
- `graph_components` `conn_graph → labels` GPU: 无 — 弱连通分量的标签(从 0 开始，按节点编号顺序首次出现编号)。长度为 n 的 int64。 · 示例: `gallery_conngraph_closed_forms`, `poc_bga_ball_type_roundtrip`, `type_connectivity_tour`
- `graph_degree_table` `conn_graph → table` GPU: 无 — 每个节点的 in_degree / out_degree(二值)与 in_strength / out_strength(权重和)的表。 · 示例: `poc_larval_connectome_reservoir`, `poc_theorems_as_pictures`
- `graph_laplacian_spectrum` `conn_graph → signal` GPU: 无 — 折叠方向后的二值图的 Laplacian L = D − A 的特征值(升序，长度 n)。 · 示例: `gallery_conngraph_closed_forms`, `poc_bga_ball_type_roundtrip`
- `graph_modularity` `conn_graph × labels → measurement` GPU: 无 — 有向、加权的模块度 Q(Leicht–Newman 2008)。 · 示例: `gallery_conngraph_closed_forms`
- `graph_motif_count` `conn_graph → measurement` GPU: 无 — 3 点模体的个数(二值有向，排除对角线)：reciprocal / ffl / cycle3。 · 示例: `gallery_conngraph_closed_forms`
- `graph_rich_club` `conn_graph → measurement` GPU: 无 — rich club 系数 φ(k)：由总度 (in+out，二值) > k 的节点张成的子图的有向密度。 · 示例: `poc_worm_core_persists`
- `graph_spectral_radius` `conn_graph → measurement` GPU: 无 — 加权邻接矩阵 W 特征值的最大绝对值(谱半径)。 · 示例: `poc_larval_connectome_reservoir`

#### conngraph / view (3)
- `graph_adjacency_image` `conn_graph → image2d` GPU: 无 — 将邻接矩阵转换为 [0, 1] 的图像 (n, n)。order = none / degree(按总度降序)/ component(按分量顺序)。 · 示例: `gallery_conngraph_closed_forms`
- `graph_edges_as_lines` `conn_graph × points → table` GPU: 无 — 将边转换为线段表(在 Studio 中叠加到点云上的出口)：列 pre / post / x0 y0 z0 / x1 y1 z1 / weight。 · 示例: `gallery_conngraph_closed_forms`
- `graph_layout_spectral` `conn_graph → points` GPU: 无 — 谱布局：以折叠方向后的 Laplacian 的 Fiedler 向量(第 2..dim+1 特征向量)为坐标的点云 (n, 3)，各轴 [0, 1]。 · 示例: `gallery_conngraph_closed_forms`

### emproof (14 ops / 6 categories)

#### emproof / evaluate (1)
- `holdout_threshold` `signal × signal × signal × signal → table` GPU: 无 — **在训练侧选定阈值，在另一侧**测量评估(score 越高越“可疑”)。 · 示例: `poc_em_second_opinion`

#### emproof / inject (3)
- `seg_inject_merge` `labels2d → labels2d` GPU: 无 — 为评估**植入融合**：选出 ``n`` 组相邻的大标签对，把其中一方的 id 改写为另一方。 · 示例: `poc_em_second_opinion`, `poc_em_split_merge_score`
- `seg_inject_split` `labels2d → labels2d` GPU: 无 — 为评估**植入分割**：选出 ``n`` 个大标签，在像素中位数所在的行(``axis="row"``)或列(``"col"``)处切成两半，给其中一侧赋予新的 id(现有最大值 + 1, +2, …)。 · 示例: `poc_em_second_opinion`, `poc_em_split_merge_score`
- `seg_label_changes` `labels2d × labels2d → table` GPU: 无 — 把两张标签图像的差异**作为融合与分割的对**返回(校正前后对比，或核对植入的错误)。 · 示例: `poc_em_second_opinion`, `poc_em_split_merge_score`

#### emproof / response (1)
- `seg_membrane_response` `image2d → image2d` GPU: 有(许可列表) — EM 切片中**暗线**(细胞膜)的响应 [0, ∞)。由高斯平滑后的 Hessian 的特征值 λ1 ≥ λ2 计算 ``max(λ1 − |λ2|, 0)`` (Steger 线检测的闭式，用 σ² 做尺度归一化)。 · 示例: `poc_em_second_opinion`, `poc_em_split_merge_score`

#### emproof / score (3)
- `seg_contingency` `labels2d × labels2d → table` GPU: 无 — 真值 ``a`` 对候选 ``b`` 的列联表(稀疏)。 · 示例: `gallery_mesh_seg_sun_gains`
- `seg_rand` `labels2d × labels2d → table` GPU: 无 — Rand 指数、调整 Rand 指数与 adapted Rand error(CREMI / SNEMI)。 · 示例: `poc_em_split_merge_score`
- `seg_variation_of_information` `labels2d × labels2d → table` GPU: 无 — 真值 ``a`` 与候选 ``b`` 之间的信息变差(VOI)，以比特计。 · 示例: `poc_em_split_merge_score`, `poc_em_wiring_errors`, `poc_skeleton_run_length_vs_voi`

#### emproof / suspect (2)
- `seg_boundary_membrane_gap` `labels2d × image2d → table` GPU: 无 — **疑似分割**：相邻两个标签的边界像素中，膜响应低于 ``tau`` 的比例。每个相邻对一行。 · 示例: `poc_em_second_opinion`
- `seg_membrane_chord_score` `labels2d × image2d → table` GPU: 无 — **疑似融合**：横穿标签内部的膜的“弦”长 / 标签的直径。每个标签(连通分量)一行。 · 示例: `poc_em_second_opinion`

#### emproof / wiring (4)
- `seg_synapse_nri` `labels2d × labels2d × table → table` GPU: 无 — 候选 ``b`` 相对真值 ``a`` 的神经重建完整性(NRI，Reilly et al. 2018)。 · 示例: `poc_em_wiring_errors`
- `seg_synapse_partners` `labels2d × table → table` GPU: 无 — 读出分割所隐含的连接图：每个突触连接哪些对象。 · 示例: `poc_em_wiring_errors`
- `seg_wiring_exposure` `labels2d × table → table` GPU: 无 — 每个对象因保持为一整块而押上了多少连接——仅由突触端点数得出。 · 示例: `poc_em_wiring_errors`
- `seg_wiring_variation` `labels2d × labels2d × table → table` GPU: 无 — 候选分割 ``b`` 如何破坏真值 ``a`` 的连接图，以比特计。 · 示例: `poc_em_wiring_errors`

### videocube (6 ops / 4 categories)

#### videocube / cube (2)
- `video_cube_cut` `video → image2d` GPU: 无 — 立方体的一张截面(``image2d``)。``"xt"`` = 行 ``position`` 的狭缝扫描 (T, W)，``"yt"`` = 列的 (T, H)，``"xy"`` = 时刻 ``position`` 的帧 (H, W)。``position`` 是 [0, 1] 的比例(位于行、列、时刻的几成处)。 · 示例: `poc_video_cube`
- `video_spacetime_cube` `video → voxel` GPU: 无 — 把视频 (T, H, W) 变成空间 × 时间的立方体 ``(T, H, W)`` float [0, 1] (``voxel``)。 · 示例: `poc_video_cube`

#### videocube / export (1)
- `video_write_gif` `rgbvideo → text` GPU: 无 — 把帧序列写成动画 GIF(``text`` = 写入的路径)。可复用的出口。 · 示例: `poc_video_cube`

#### videocube / render (2)
- `video_cube_orbit` `video → rgbvideo` GPU: 无 — 旋转立方体的彩色视频 ``(n_frames, size, size, 3)`` float [0, 1] (``rgbvideo``)。 · 示例: `poc_video_cube`
- `vol_render_transfer` `voxel → rgb` GPU: 无 — 以**从前到后的 α 合成**从任意视点绘制立方体 ``(size, size, 3)`` float [0, 1] (``rgb``)。 · 示例: `poc_print_layer_inspection`, `poc_video_cube`

#### videocube / summary (1)
- `video_summary_keyframes` `video → indices` GPU: 有(许可列表) — 代表帧的下标 ``(k,)`` int64，升序(``indices``)。 · 示例: `poc_video_cube`

### live4d (14 ops / 5 categories)

#### live4d / flow (4)
- `vol_flow_3d` `voxel × voxel → flow_dense` GPU: 无 — 两个体积之间的稠密位移场 ``(3, Z, Y, X)``(``flow_dense``，分量 dz, dy, dx [voxel])。 · 示例: `poc_live4d`
- `volseq_pathline_orbit` `volseq → rgbvideo` GPU: 无 — 旋转观看 ``volseq_pathline_render`` 的轨迹立体 ``(n_frames, size, size, 3)``(``rgbvideo``)。 · 示例: `poc_live4d`
- `volseq_pathline_render` `volseq → rgb` GPU: 无 — 让粒子随流动而绘出的**轨迹立体** ``(size, size, 3)``(``rgb``)——用一张静止图像展示运动。 · 示例: `poc_live4d`
- `volseq_speed` `volseq → volseq` GPU: 无 — 以 ``(T − 1, Z, Y, X)`` 返回体积时间序列相邻帧之间的**速率** ``|d|`` [voxel/frame] (``volseq``)。 · 示例: `gallery_live4d_volseq_truth`

#### live4d / render (3)
- `focus_sweep_height_video` `volseq → video` GPU: 无 — 由焦点扫描(每帧是 z 方向的对焦堆栈)的时间序列生成**高度场视频** ``(T, Y, X)``(``video``， 单位为 z 的张数)。 · 示例: `poc_live4d`
- `focus_sweep_surface_video` `volseq → rgbvideo` GPU: 无 — 由焦点扫描(每帧是 z 方向的对焦堆栈)的时间序列生成**带阴影的高度场视频** ``(T, Y, X, 3)``(``rgbvideo``)。 · 示例: `poc_live4d`
- `volseq_render_orbit` `volseq → rgbvideo` GPU: 无 — **一边推进时间一边旋转视点**来绘制体积时间序列 ``(n_frames, size, size, 3)``(``rgbvideo``)。 · 示例: `poc_live4d`

#### live4d / series (2)
- `volseq_cut_video` `volseq → video` GPU: 无 — 用一张截面切开体积时间序列得到的视频 ``(T, H, W)``(``video``)。 · 示例: `gallery_live4d_volseq_truth`
- `volseq_mip_video` `volseq → video` GPU: 无 — 沿轴 ``axis``(1 = z, 2 = y, 3 = x)做最大值投影，把体积时间序列压成视频 ``(T, H, W)``(``video``)。 · 示例: `gallery_live4d_volseq_truth`

#### live4d / synth (2)
- `volseq_synth_beating` `无输入 → volseq` GPU: 无 — 按已知半径规律搏动的壳的体积时间序列 ``(T, Z, Y, X)``(``volseq``，值为 [0, 1] + 噪声)。 · 示例: `poc_live4d`
- `volseq_synth_dividing` `无输入 → volseq` GPU: 无 — 以已知速度一分为二的团块的体积时间序列 ``(T, Z, Y, X)``(``volseq``)。 · 示例: `poc_live4d`

#### live4d / time (3)
- `video_interpolate_flow` `video → video` GPU: 有(许可列表) — 沿流动对视频 ``(T, H, W)`` 插值，得到 ``(T + (T − 1)(factor − 1), H, W)``(``video``，时间超分辨率)。 · 示例: `gallery_live4d_volseq_truth`
- `volseq_interpolate_flow` `volseq → volseq` GPU: 无 — 沿3 维流动对体积时间序列 ``(T, Z, Y, X)`` 插值，得到 ``(T + (T − 1)(factor − 1), Z, Y, X)``(``volseq``)。 · 示例: `poc_live4d`
- `volseq_magnify_motion` `volseq → volseq` GPU: 无 — 把体积时间序列中**频带内的微小运动放大 alpha 倍**(``volseq``，Eulerian 线性放大的3 维版)。 · 示例: `poc_live4d`

### printpath (23 ops / 6 categories)

#### printpath / format (2)
- `read_3mf` `text → mesh` GPU: 无 — 把 3MF(zip 中的 ``3D/3dmodel.model``，3MF Core Specification)读成三角形网格 ``mesh`` = (V, F)。 · 示例: `poc_print_layer_inspection`
- `write_3mf` `text × mesh → text` GPU: 无 — 把三角形网格写成 3MF(最小构成：``[Content_Types].xml`` / ``_rels/.rels`` / ``3D/3dmodel.model``，单位 mm)。返回路径(``text``)。 · 示例: `poc_print_layer_inspection`

#### printpath / gcode (5)
- `gcode_extrusion_volume` `table → measurement` GPU: 无 — 挤出耗材的体积 [mm³] = Σe × π (d / 2)²(``measurement``)。重量为密度 × 体积(PLA ≈ 1.24 g/cm³)。 · 示例: `poc_print_layer_inspection`
- `gcode_layer_image` `table → image2d` GPU: 无 — 把一层的路径绘成**带线宽的栅格** ``image2d``(造型 1、背景 0、绘制移动时为 0.5，y 向下 = 行)。 · 示例: `poc_print_layer_inspection`
- `gcode_read` `text → table` GPU: 无 — 把 G-code(RepRap / Marlin 系)读成**线段表** ``table``：列 ``x0 y0 z0 x1 y1 z1``(mm)、``e``(该线段 挤出的耗材长度 mm，仅移动则为 0)、``f``(进给 mm/min)、``layer``(层号)。 · 示例: `poc_print_layer_inspection`
- `gcode_time_estimate` `table → measurement` GPU: 无 — 所需时间的下限 [s] = Σ(线段长度 / 进给)(忽略加速度与加加速度，``measurement``)。进给为 0 的线段不计入。 · 示例: `poc_one_stroke_epicycles`, `poc_print_layer_inspection`
- `gcode_write` `table × text → text` GPU: 无 — 把线段表写成 G-code(G21 / G90 / M82，G1 的绝对坐标与绝对 E)。返回写入的路径(``text``)。 · 示例: `poc_print_layer_inspection`

#### printpath / inspect (1)
- `print_layer_defect_map` `image2d × image2d → image2d` GPU: 无 — 比较观测到的层图像与期望的层图像(``gcode_layer_image``)得到的**带符号缺陷图** ``image2d``：+1 = 应有处却没有(缺料、堵塞)，−1 = 不应有处却有(拉丝、溢出、spaghetti)，0 = 一致。 · 示例: `poc_print_layer_inspection`

#### printpath / npr (6)
- `engrave_lines` `image2d → image2d` GPU: 有(许可列表) — 铜版雕刻 —— 平行线的**宽度**承载灰阶。 · 示例: `poc_beats_fringes_and_screens`
- `halftone_moire_period` `无输入 → table` GPU: 无 — 两张半色调网屏之间的拍频 —— 周期与方向的闭式解。 · 示例: `poc_beats_fringes_and_screens`, `poc_moire_screen`, `poc_print_registration`
- `halftone_screen` `image2d → image2d` GPU: 有(许可列表) — 经典的旋转半色调网屏 —— 网点面积承载灰阶。 · 示例: `poc_beats_fringes_and_screens`, `poc_pixel_shift`, `poc_print_registration`
- `hatch_field` `image2d → image2d` GPU: 有(许可列表) — **顺着画面**的交叉排线 —— 方向来自结构张量。 · 示例: `poc_beats_fringes_and_screens`
- `mosaic_tiles_render` `image2d × pairs → image2d` GPU: 无 — 用各 Voronoi 单元所辖像素的**均值**来填色。 · 示例: `poc_beats_fringes_and_screens`
- `mosaic_tiles_sites` `image2d → pairs` GPU: 无 — 在图像上运行的 Lloyd 迭代 —— 马赛克的瓷砖中心。 · 示例: `poc_beats_fringes_and_screens`

#### printpath / slice (3)
- `contours_to_gcode` `table → table` GPU: 无 — 把轮廓(``mesh_slice_contours`` 的表)转换为**环绕一周的路径表**(与 ``gcode_read`` 相同的列)。 · 示例: `poc_one_stroke_epicycles`, `poc_print_layer_inspection`
- `mesh_slice_contours` `mesh → table` GPU: 无 — 用平面 ``z`` 切割三角形网格得到的**轮廓表** ``table``：列 ``ring``(环编号)、``x``、``y``(mm)。 · 示例: `itokawa_gravity_tour`, `poc_print_layer_inspection`
- `mesh_slice_stack` `mesh → voxel` GPU: 无 — 以 ``layer_mm`` 为步长切割网格得到的**层掩膜堆叠** ``voxel`` (Z, Y, X)(0 / 1，Z 自下而上)。 · 示例: `poc_am_thermal_to_ct`, `poc_print_layer_inspection`

#### printpath / stroke (6)
- `mst_length` `pairs → measurement` GPU: 无 — 最小生成树的长度(Prim)。**闭合巡回路径不可能比它更短**(下界)。 · 示例: `poc_one_stroke_epicycles`
- `stipple_energy` `image2d × pairs → measurement` GPU: 无 — 加权 Lloyd 的能量 ``Σ w(x) |x - c(x)|^2``(用于检验单调递减)。 · 示例: `poc_beats_fringes_and_screens`, `poc_one_stroke_epicycles`
- `stipple_points_from_image` `image2d → pairs` GPU: 无 — 把浓淡映射为**点的密度**(加权 Lloyd = 重心 Voronoi)。→ ``pairs`` · 示例: `poc_one_stroke_epicycles`
- `stroke_resample_closed` `pairs → pairs` GPU: 无 — 把闭合的线按**等弧长**重新采样。→ ``pairs`` · 示例: `poc_one_stroke_epicycles`
- `stroke_tone_error` `image2d × pairs → table` GPU: 无 — 画线所得的**浓淡**与目标相差多少。→ ``table`` · 示例: `poc_one_stroke_epicycles`
- `stroke_tour_closed` `pairs → pairs` GPU: 无 — 把点重新排列成**闭合巡回路径**，每个点经过 1 次后回到起点。→ ``pairs`` · 示例: `poc_one_stroke_epicycles`

### geocam (9 ops / 3 categories)

#### geocam / orientation (1)
- `camera_orientation_from_skyline` `signal × table → table` GPU: 无 — 由照片的天际线(每列的行)与 DEM 的天际线确定 (yaw, pitch, roll) → table。 · 示例: `poc_public_camera_heading`

#### geocam / skyline (3)
- `dem_skyline` `depth → table` GPU: 无 — 从 DEM 的 1 个点看到的**全方位天际线**(各方位的地平线仰角)→ table。 · 示例: `poc_public_camera_heading`
- `render_skyline_view` `table → image2d` GPU: 无 — 根据天际线 table 与姿态，绘制该朝向的相机所看到的**天空掩膜**(H, W)→ image2d(0/1)。 · 示例: `poc_public_camera_heading`
- `skyline_extract` `image2d → signal` GPU: 无 — 用动态规划从照片中提取 1 条**每列的天空与地形分界所在行** → signal (W,)。 · 示例: `poc_public_camera_heading`

#### geocam / sun (5)
- `camera_orientation_from_sun` `keypoints × signal → table` GPU: 无 — 带时刻的太阳像素位置 ≥ 2 点 → 相机的 (yaw, pitch, roll)(Wahba 问题的 SVD 解 = Kabsch)。 · 示例: `poc_public_camera_heading`
- `camera_orientation_from_sun_candidates` `keypoints × signal × signal → table` GPU: 无 — 从每帧中多个“亮团块”候选(混有太阳、白色汽车、标志、文字)中，用 RANSAC 选出**按时刻规律运动的 1 条**，同时确定 (yaw, pitch, roll) 与焦距 → table。固定相机中只有太阳以太阳的速度运动， 因此不凭外观、而凭运动来认定太阳(在 Fintraffic 天气相机上，基于外观的门禁曾 24/24 误检，2026-09-21)。 · 示例: `poc_public_camera_heading_real`
- `sun_bloom_fit` `image2d → table` GPU: 无 — 实拍中的太阳 = 使传感器饱和的**光晕(bloom)**(比圆盘大，大小随曝光变化，会被图像边缘或文字带截断)。 对最大的饱和团块的**边缘**拟合圆并返回圆心 → table。团块被截断时重心会偏向截断侧的反方向(实测 15 px)，因此 舍弃被截断的边缘(接触图像外周和 ``ignore_top_rows`` 带的像素)，对剩余的弧用代数最小二乘(Kåsa 1976)拟合圆。 · 示例: `gallery_mesh_seg_sun_gains`
- `sun_pixel_position` `image2d → keypoints` GPU: 无 — 图像中太阳(使传感器**饱和**的圆盘)的重心 → keypoints (1, 2) = (u, v)。 · 示例: `poc_public_camera_heading`
- `sun_position` `signal → table` GPU: 无 — 纬度、经度、时刻(UNIX 秒，UTC)→ 太阳的方位角、仰角 [度] (NOAA 太阳位置算法，Meeus 1998 的低精度公式)。 · 示例: `poc_public_camera_heading`, `poc_public_camera_heading_real`

### llmcore (10 ops / 4 categories)

#### llmcore / attend (4)
- `attention_grouped` `tokens × tokens × tokens → tokens` GPU: 无 — 把头分组共享的注意力(GQA)→ tokens。**n_kv_heads == n_heads 时与 MHA、== 1 时与 MQA 严格一致**。 · 示例: `poc_attention_identities`
- `attention_linear` `tokens × tokens × tokens → tokens` GPU: 无 — 去掉 softmax 的注意力 → tokens。**(QKᵀ)V == Q(KᵀV)——正是结合律本身**。 · 示例: `poc_attention_identities`
- `attention_softmax` `tokens × tokens × tokens → tokens` GPU: 无 — 一次性计算的注意力(参考实现)→ tokens。**本族核对答案的基准**。 · 示例: `poc_attention_identities`, `type_connectivity_tour`
- `attention_tiled` `tokens × tokens × tokens → tokens` GPU: 无 — 分块 + online softmax 的注意力(FlashAttention 的核心)→ tokens。**不是近似**。 · 示例: `poc_attention_identities`

#### llmcore / decode (1)
- `kv_cache_decode` `tokens × tokens × tokens → tokens` GPU: 无 — 只前进 1 个 token 的推理(KV Cache)→ tokens (1, dv)。 · 示例: `poc_attention_identities`

#### llmcore / prepare (2)
- `rms_norm` `tokens → tokens` GPU: 无 — RMS 归一化 → tokens。**默认(eps=0，无 weight)时输出的 RMS 严格为 1**。 · 示例: `poc_attention_identities`
- `rope_rotate` `tokens → tokens` GPU: 无 — 基于旋转的位置编码(RoPE)→ tokens。**由于是旋转，所以保持范数**。 · 示例: `poc_attention_identities`

#### llmcore / score (3)
- `attention_apply` `attnmap × tokens → tokens` GPU: 无 — 用注意力权重混合值 → tokens。**由于行和为 1，输出是输入的凸组合**。 · 示例: `poc_attention_identities`
- `attention_scores` `tokens × tokens → attnmap` GPU: 无 — 原始注意力分数 QKᵀ/√d → attnmap (T, S)。 · 示例: `poc_attention_identities`
- `attention_weights` `attnmap → attnmap` GPU: 无 — 逐行 softmax(带掩码)→ attnmap。**行和为 1，mask 位置严格为 0**。 · 示例: `poc_attention_identities`

### segmentation (59 ops / 11 categories)

#### segmentation / classify (7)
- `class_2dim_sup` (halcon: `class_2dim_sup`) `image2d × image2d × mask → mask` GPU: 无 — 二通道特征空间的监督分类：落入 ref_region 分布内的像素(class_2dim_sup)。 · 示例: `halcon_segmentation_tour`, `poc_surface_defect_classifiers`
- `class_2dim_unsup` (halcon: `class_2dim_unsup`) `image2d × image2d → labels2d` GPU: 有(许可列表) — 二通道特征空间的 k-means 无监督分类，返回标签图像(class_2dim_unsup)。 · 示例: `halcon_segmentation_tour`, `poc_surface_defect_classifiers`
- `class_ndim_norm` (halcon: `class_ndim_norm`) `images × table → mask` GPU: 有(许可列表) — 用学习到的正态分布类对 N 维特征图像分类(马氏距离 < thresh)(class_ndim_norm)。 · 示例: `halcon_segmentation_tour`, `poc_surface_defect_classifiers`
- `classify_image_class_lut` (halcon: `classify_image_class_lut`) `image2d × signal → labels2d` GPU: 有(许可列表) — 按灰度 LUT(阈值/标签表)对像素分类(classify_image_class_lut)。 · 示例: `halcon_segmentation_tour`, `poc_surface_defect_classifiers`
- `fisher_lda_fit` `matrix × signal → table` GPU: 无 — 学习两类 Fisher 线性判别（闭式解，无迭代）。 · 示例: `poc_weed_rice_ratio`
- `fisher_lda_score` `table × matrix → table` GPU: 无 — 用 ``fisher_lda_fit`` 学到的判别对特征打分（score > 0 为类 1）。 · 示例: `poc_weed_rice_ratio`
- `learn_ndim_norm` (halcon: `learn_ndim_norm`) `matrix → table` GPU: 无 — 从特征向量集合学习正态分布类(均值与协方差)(learn_ndim_norm)。 · 示例: `halcon_segmentation_tour`, `poc_surface_defect_classifiers`

#### segmentation / compare (1)
- `check_difference` (halcon: `check_difference`) `image2d × image2d → mask` GPU: 有(许可列表) — 与参考图像之差超过 tol 的像素，作为区域返回(check_difference)。 · 示例: `halcon_segmentation_tour`

#### segmentation / contour (10)
- `chan_vese_energy` `image2d × mask → table` GPU: 无 — Chan–Vese 2001 的能量 F = μ Length + ν Area(inside) + λ1 ∫_in |I − c1|² + λ2 ∫_out |I − c2|²（两相）（chan_vese_energy）。 · 示例: `gallery_seg_measures`
- `chan_vese_evolve` `image2d × mask → table` GPU: 无 — 最小化 Chan–Vese 2001 的两相能量（默认是凸松弛的交替最小化，也可选择水平集梯度下降）（chan_vese_evolve）。 · 示例: `poc_active_contours`
- `curvature_flow` `mask → table` GPU: 有(许可列表) — 平均曲率流（曲线缩短流）的水平集形式 φ_t = |∇φ| div(∇φ/|∇φ|)（φ < 0 为内侧，从凸处开始收缩）（curvature_flow）。 · 示例: `poc_active_contours`
- `drle_evolve` `image2d × mask → table` GPU: 无 — 距离正则化水平集 DRLSE（Li–Xu–Gui–Fox 2010）的边缘版。不做重新初始化（drle_evolve）。 · 示例: `poc_active_contours`
- `edge_stop_g` `image2d → table` GPU: 无 — 边缘停止函数 g = 1 / (1 + |∇(G_σ * I)|² / k²)（Caselles–Kimmel–Sapiro 1997 中 p = 2 的形式）（edge_stop_g）。 · 示例: `poc_active_contours`
- `gvf_field` `image2d → table` GPU: 无 — 梯度矢量流（Xu–Prince 1998）：把边缘图 f 的梯度平滑地扩散到远离边缘处的场 (u, v)（gvf_field）。 · 示例: `poc_active_contours`
- `level_set_reinit` `mask → table` GPU: 有(许可列表) — 把 φ（φ < 0 为内侧）改写为同一零等值线的符号距离函数（level_set_reinit）。 · 示例: `poc_active_contours`
- `morph_chan_vese` `image2d × mask → table` GPU: 无 — 形态学 Chan–Vese（Márquez-Neila–Baumela–Álvarez 2014 的 MorphACWE）。1 次迭代 = 数据步 + 平滑步（morph_chan_vese）。 · 示例: `poc_active_contours`
- `morph_geodesic_ac` `image2d × mask → table` GPU: 无 — 形态学测地主动轮廓（Márquez-Neila 等 2014 的 MorphGAC）。gimage = 在边缘处取小值的图像（edge_stop_g 的 g）（morph_geodesic_ac）。 · 示例: `poc_active_contours`
- `snake_evolve` `image2d × pairs → table` GPU: 无 — 离散 snake（Kass–Witkin–Terzopoulos 1988）的半隐式更新 x_t = (A + γI)^(-1)(γ x_(t-1) − f_x)（式 (19)(20)）（snake_evolve）。 · 示例: `poc_active_contours`

#### segmentation / graph (12)
- `alpha_expansion` `image2d → table` GPU: 无 — 多标签 α-expansion（Boykov–Veksler–Zabih 2001）：E(f) = Σ (I_p − μ_(f_p))² + λ Σ w_pq V(f_p, f_q)，V 为度量（alpha_expansion）。 · 示例: `poc_graph_hierarchy_segmentation`
- `alpha_tree` `image2d → table` GPU: 无 — α-tree：构建以相邻差为权重的网格最小生成树（scipy 的 Kruskal），仅用权重 ≤ α 的树边给出每个 α 的划分（alpha_tree）。 · 示例: `poc_graph_hierarchy_segmentation`
- `area_opening_attr` `image2d → table` GPU: 无 — 属性开运算（Salembier 等 1998）：删除成分树中属性 < ``threshold`` 的节点，并使每个像素取“属性 ≥ 阈值的最近祖先”的值（area_opening_attr）。 · 示例: `poc_graph_hierarchy_segmentation`
- `graph_cut_binary` `image2d → table` GPU: 无 — 二值 graph cut（Boykov–Jolly 2001）：用最大流 / 最小割精确地最小化 E = Σ_p D_p(x_p) + λ Σ w_pq [x_p ≠ x_q]（graph_cut_binary）。 · 示例: `poc_graph_hierarchy_segmentation`
- `hierarchical_watershed` `image2d → table` GPU: 无 — 基于 dynamics 的层次分水岭：为地形 ``image``（低处为盆地）的最小生成森林的边赋予 dynamics 显著度，返回由显著度 ≤ ``threshold`` 的边连接的分量（给定 ``n_regions`` 时，使用得到该区域数的最小阈值）（hierarchical_watershed）。 · 示例: `poc_graph_hierarchy_segmentation`
- `max_tree` `image2d → table` GPU: 无 — 成分树（max-tree）：用 Union-Find 构建上水平集 {f ≥ h} 的连通分量树（按像素值降序处理）（max_tree）。 · 示例: `gallery_seg_measures`
- `quasi_flat_zones` `image2d → table` GPU: 无 — α-准平坦区域（Soille 2008）：仅用 |f_p − f_q| ≤ α 的相邻边连接而成的连通分量。返回：``labels``（1..k）、``n_zones``（quasi_flat_zones）。 · 示例: `poc_graph_hierarchy_segmentation`
- `quickshift` `image2d → table` GPU: 无 — quick shift（Vedaldi–Soatto 2008）：在特征 (y, x, ratio · I) 上估计 Parzen 密度 P_i = Σ_j exp(−D_ij²/(2σ²))（窗 3σ，σ = ``kernel_size``），把每个像素连到“密度更高的点中最近的点”（半径 ``search_radius`` 的窗内），剪去长度 > ``max_dist`` 的枝后，以树的分量作为区域（quickshift）。 · 示例: `poc_graph_hierarchy_segmentation`
- `snic_superpixels` `image2d → table` GPU: 无 — SNIC（Achanta–Süsstrunk 2017 的 Algorithm 1）：从网格种子出发、用优先队列生长的非迭代超像素（snic_superpixels）。 · 示例: `poc_graph_hierarchy_segmentation`, `poc_weed_rice_ratio`
- `statistical_region_merging` `image2d → table` GPU: 无 — 统计区域合并 SRM（Nock–Nielsen 2004）：按 |I_p − I_q| 的升序处理相邻像素对，谓词 P(R, R') 为真则合并（statistical_region_merging）。 · 示例: `poc_graph_hierarchy_segmentation`
- `superpixel_quality` `labels2d × labels2d → table` GPU: 无 — 超像素评分：边界召回率（``segeval.seg_boundary_f`` 的 recall，容差 τ）、校正欠分割误差 CUSE = (1/N) Σ_k |S_k − G_max(S_k)|（Neubert–Protzel 2012，SNIC 论文的式 (2)）、ASA = 1 − CUSE、Neubert–Protzel 的欠分割误差 UE = (1/N) Σ_G Σ_(S∩G≠∅) min(|S∩G|, |S − G|)、超像素的数量。真值的 0 也算作一个区域（背景也是覆盖的对象）（superpixel_quality）。 · 示例: `poc_graph_hierarchy_segmentation`
- `ultrametric_contour_map` `image2d → table` GPU: 无 — dynamics 层次的超度量轮廓图（UCM）：相邻像素 p、q 的值 =“p 与 q 成为同一区域的最小阈值”（ultrametric_contour_map）。 · 示例: `poc_graph_hierarchy_segmentation`

#### segmentation / grow (2)
- `expand_gray` (halcon: `expand_gray`) `image2d × mask → mask` GPU: 有(许可列表) — 从种子按灰度相似性(|Δ| < tol)扩张区域(expand_gray)。 · 示例: `halcon_segmentation_tour`
- `regiongrowing_n` (halcon: `regiongrowing_n`) `images → labels2d` GPU: 无 — 按多通道特征的相似性分割整幅图像，返回标签图像(regiongrowing_n)。 · 示例: `halcon_segmentation_tour`

#### segmentation / plant (3)
- `cover_ratio_grade` `signal → table` GPU: 无 — 用**事先声明的边界** ``edges`` 把覆盖度（面积比例 0..1）分为 0..len(edges) 级。 · 示例: `poc_weed_rice_ratio`
- `plant_color_index` `rgbimage → table` GPU: 有(许可列表) — 逐像素计算可见光三波段的植物颜色指数（ExG、ExR、ExGR、CIVE、NGRDI、VEG）。 · 示例: `poc_leaf_disease_area`, `poc_weed_rice_ratio`
- `superpixel_color_texture_features` `rgbimage × labels2d → table` GPU: 有(许可列表) — 为标签图像的每个区域输出 10 个颜色（植物颜色指数、色度）与纹理（梯度、方向一致性）特征。 · 示例: `poc_weed_rice_ratio`

#### segmentation / score (8)
- `seg_boundary_f` `labels2d × labels2d → table` GPU: 无 — 容差 tau 下的边界 F 值：precision = 预测边界像素中落在真边界 tau 距离内的比例，recall 反之（seg_boundary_f）。 · 示例: `poc_am_thermal_to_ct`, `poc_graph_hierarchy_segmentation`, `poc_sem_wafer_defect_edge_bias`
- `seg_confusion_table` `labels2d × labels2d → table` GPU: 无 — 标签对应的混淆表（行 = 真值，列 = 预测），并给出最大重叠匹配与一一对应（唯一性）标志（seg_confusion_table）。 · 示例: `gallery_seg_measures`
- `seg_dice_jaccard` `labels2d × labels2d → table` GPU: 无 — Dice 与 Jaccard —— 对掩膜（非背景像素的并集）算一组，或按真值标签与其最大重叠对象逐一计算（seg_dice_jaccard）。 · 示例: `poc_active_contours`, `poc_am_thermal_to_ct`, `poc_graph_hierarchy_segmentation`, `poc_segmentation_gauntlet`, `poc_sem_wafer_defect_edge_bias`
- `seg_hausdorff` `labels2d × labels2d → table` GPU: 无 — 两组边界像素集合之间的 Hausdorff 距离，并给出其分位数版本（如 HD95）（seg_hausdorff）。 · 示例: `gallery_seg_measures`
- `seg_mean_surface_distance` `labels2d × labels2d → table` GPU: 无 — 平均对称表面距离（ASSD）：双向边界距离合并后的均值，另给 RMS（seg_mean_surface_distance）。 · 示例: `gallery_seg_measures`
- `seg_object_counts_match` `labels2d × labels2d → table` GPU: 无 — 物体个数一致性：由“主要重叠”边的二部图次数来计数分裂/融合/漏检/误检/匹配（seg_object_counts_match）。 · 示例: `poc_graph_hierarchy_segmentation`
- `seg_score_card` `labels2d × labels2d → table` GPU: 无 — 把所有度量汇成一张表：Dice/Jaccard、VI/split/merge、Rand/ARI、边界 F、Hausdorff/HD95/ASSD、过/欠分割、分裂/融合/漏检/误检/匹配与个数（seg_score_card）。 · 示例: `poc_active_contours`, `poc_graph_hierarchy_segmentation`, `poc_segmentation_gauntlet`
- `seg_under_over_segmentation` `labels2d × labels2d → table` GPU: 无 — 以混淆表多数表决的重数来计数过分割与欠分割（Levine & Nazif 风格）（seg_under_over_segmentation）。 · 示例: `poc_graph_hierarchy_segmentation`

#### segmentation / threshold (4)
- `threshold_isodata` `image2d → table` GPU: 无 — isodata（Ridler–Calvard 1978）：**在像素值上**反复执行 t ← (μ_≤t + μ_>t)/2，直到划分不再变化（初值 = 平均值）（threshold_isodata）。 · 示例: `poc_graph_hierarchy_segmentation`
- `threshold_kapur` `image2d → table` GPU: 无 — 最大熵阈值（Kapur–Sahoo–Wong 1985）：使 H(t) = −Σ_(i ≤ t) (p_i/P1) ln(p_i/P1) − Σ_(i > t) (p_i/P2) ln(p_i/P2) 最大的箱 t（仅限两侧概率均为正的箱）。返回：``threshold`` = 该箱的上端、``mask``（箱号 > t）、``bin``、``entropy``（H，被排除的箱为 nan）（threshold_kapur）。 · 示例: `poc_graph_hierarchy_segmentation`
- `threshold_kittler` `image2d → table` GPU: 无 — 最小误差阈值（Kittler–Illingworth 1986）：在每个箱 t 处分为低侧（箱 ≤ t）与高侧，最小化 J(t) = 1 + 2(P1 ln σ1 + P2 ln σ2) − 2(P1 ln P1 + P2 ln P2)（σ 为各侧箱中心的标准差；任一侧 σ 为 0 的箱除外）。返回：``threshold`` = 该箱的上端（mask 按箱号 > t 决定 = 端点上的值也不矛盾）、``mask``、``bin``、``criterion``（J，被排除的箱为 nan）（threshold_kittler）。 · 示例: `poc_graph_hierarchy_segmentation`
- `threshold_triangle` `image2d → table` GPU: 无 — 三角法（Zack–Rogers–Latt 1977）：连接峰顶 (b_p, h_p) 与长尾一侧端点的箱 (b_e, 0)，取其间各箱 (b, h_b) 到该线的有符号垂直距离最大的箱为阈值（线的下侧为正）。返回：``threshold``（该箱的中心）、``mask`` = image > threshold、``bin``、``distance``（各箱的距离，范围外为 nan）。端点高度为 0、尾侧的选法与 skimage / ImageJ 的约定相同（原文待确认）（threshold_triangle）。 · 示例: `poc_graph_hierarchy_segmentation`

#### segmentation / watershed (1)
- `watersheds_marker` (halcon: `watersheds_marker`) `image2d × labels2d → labels2d` GPU: 无 — 标记控制的分水岭分割；markers 为整数标签图像(0 = 未分配)(watersheds_marker)。 · 示例: `halcon_segmentation_tour`, `poc_mixed_case_depalletizing`, `poc_sem_tem_same_particle`

#### segmentation / watershed3d (3)
- `distance_peaks` `voxel → labels` GPU: 无 — 返回前景距离变换的局部极大值经 ``min_distance`` NMS 稀疏化后的 int 标记数组。 · 示例: `watershed3d_tour`
- `separate_touching` `voxel → labels` GPU: 无 — genuinely-new (B)：用 1 次调用自动分离接触物体的常用封装。 · 示例: `watershed3d_tour`
- `watershed_vol` `voxel → labels` GPU: 无 — 以距离变换为种子的分水岭把 3D 前景分割为每个物体的标签(公开 op 的轻量组合)。 · 示例: `watershed3d_tour`

#### segmentation / world (8)
- `lens_area` `无输入 → scalar` GPU: 无 — 等半径 r 的两圆在中心距 d 处重叠（透镜）面积的闭式解；当 d >= 2r 时为 0（lens_area）。 · 示例: `gallery_seg_measures`
- `voronoi_cells` `points → table` GPU: 无 — 矩形内种子的 Voronoi 分割，以多边形返回（含面积与内部边长；半平面暴力法，O(n^2)）（voronoi_cells）。 · 示例: `gallery_seg_measures`
- `world_blobs_touching` `无输入 → table` GPU: 无 — 重叠圆盘（细胞/颗粒）世界：等半径圆排成链，每个只与前一个在中心距 2r(1 - overlap) 处重叠（world_blobs_touching）。 · 示例: `poc_active_contours`, `poc_dense_bubble_count`, `poc_graph_hierarchy_segmentation`, `poc_segmentation_gauntlet`
- `world_gradient_illumination` `无输入 → table` GPU: 无 — 照明梯度加噪声之上的暗物体世界（全局阈值失效，局部阈值/平场校正可切开）（world_gradient_illumination）。 · 示例: `poc_active_contours`, `poc_graph_hierarchy_segmentation`, `poc_segmentation_gauntlet`
- `world_grains_voronoi` `无输入 → table` GPU: 无 — Voronoi 晶粒世界：格点上 n 个带抖动的种子，标签 = 最近种子的编号（1..n）（world_grains_voronoi）。 · 示例: `poc_graph_hierarchy_segmentation`, `poc_segmentation_gauntlet`
- `world_parts_with_shadow` `无输入 → table` GPU: 无 — 工业零件世界（带圆孔的旋转矩形）：斜向照明的阴影、表面明暗与高光（world_parts_with_shadow）。 · 示例: `poc_active_contours`, `poc_graph_hierarchy_segmentation`, `poc_segmentation_gauntlet`
- `world_texture_regions` `无输入 → table` GPU: 无 — 2-4 个区域的世界：均值相同、仅方差与周期不同（阈值切不开）（world_texture_regions）。 · 示例: `poc_graph_hierarchy_segmentation`, `poc_segmentation_gauntlet`
- `world_thin_structures` `无输入 → table` GPU: 无 — 宽 1-3 px 的线（直线）与裂纹（折线）世界；真值 = 中心线与宽度（world_thin_structures）。 · 示例: `poc_active_contours`, `poc_graph_hierarchy_segmentation`, `poc_segmentation_gauntlet`

## References(算法的一手资料、further reading)

各 op 的原理也在模块 docstring 中注明了一手文献名。以下为主要技术族的外部参考。

- Marching cubes(voxel→mesh) — <https://en.wikipedia.org/wiki/Marching_cubes>
- Elliptic Fourier descriptors — <https://en.wikipedia.org/wiki/Elliptic_Fourier_descriptor>
- Thin plate spline(TPS 变形) — <https://en.wikipedia.org/wiki/Thin_plate_spline>
- Image morphing(feature-based) — <https://en.wikipedia.org/wiki/Morphing>
- Perspective-n-Point(PnP 位姿) — <https://en.wikipedia.org/wiki/Perspective-n-Point>
- RANSAC(鲁棒估计) — <https://en.wikipedia.org/wiki/Random_sample_consensus>
- Iterative closest point(ICP/GICP) — <https://en.wikipedia.org/wiki/Iterative_closest_point>
- Superquadrics — <https://en.wikipedia.org/wiki/Superquadrics>
- Signed distance function(ESDF) — <https://en.wikipedia.org/wiki/Signed_distance_function>
- Photometric stereo — <https://en.wikipedia.org/wiki/Photometric_stereo>
- Phase unwrapping(structured light) — <https://en.wikipedia.org/wiki/Phase_unwrapping>
- Medial axis / skeleton — <https://en.wikipedia.org/wiki/Medial_axis>
- Geodesic(距离) — <https://en.wikipedia.org/wiki/Geodesic>
- Digital elevation model(DEM) — <https://en.wikipedia.org/wiki/Digital_elevation_model>
- Spline interpolation — <https://en.wikipedia.org/wiki/Spline_interpolation>
- Delaunay triangulation — <https://en.wikipedia.org/wiki/Delaunay_triangulation>
- Fourier transform — <https://en.wikipedia.org/wiki/Fourier_transform>
- Image moment(invariants) — <https://en.wikipedia.org/wiki/Image_moment>

