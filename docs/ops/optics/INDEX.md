# OPTICS operator help — 470 ops in 52 categories

自動生成(`tools/opdocs.py toc`)。フォルダ階層 `docs/ops/optics/<category>/<op>.md` を走査。

## ファミリ使い方ガイド(用途→op の教材)

- [optics_imaging](guides/optics_imaging.md) — 光学(レンズ・回折・偏光) — 使い方ガイド

## 背景知識ガイド(op の手前にある物理・規約)

- [mv_cables](guides/mv_cables.md) — ケーブル（規格・速度・給電・ロボットケーブル）
- [mv_cameras](guides/mv_cameras.md) — 産業用カメラメーカー（センサとの紐付け・ラインスキャン / TDI）
- [mv_frame_grabbers](guides/mv_frame_grabbers.md) — フレームグラバーボード（光学系ではないが、撮れるかを決める）
- [mv_illumination_practice](guides/mv_illumination_practice.md) — 照明の実務知識 — 波長・偏光・点灯方式・外光・安全
- [mv_image_sensors](guides/mv_image_sensors.md) — 産業用イメージセンサ（現行品中心）
- [mv_standards](guides/mv_standards.md) — カメラインターフェースの規格と団体
- [virtual_machine_vision](guides/virtual_machine_vision.md) — 仮想マシンビジョン — パラメータの洗い出しとオブジェクト模型

## カテゴリ

### appearance (7)

[cie_xyz_from_wavelength](appearance/cie_xyz_from_wavelength.md) · [grating_rgb](appearance/grating_rgb.md) · [grating_wavelengths](appearance/grating_wavelengths.md) · [spectrum_to_srgb](appearance/spectrum_to_srgb.md) · [thin_film_reflectance](appearance/thin_film_reflectance.md) · [thin_film_rgb](appearance/thin_film_rgb.md) · [ward_anisotropic](appearance/ward_anisotropic.md)

### cavity (5)

[cavity_strain_transfer](cavity/cavity_strain_transfer.md) · [fabry_perot_response](cavity/fabry_perot_response.md) · [michelson_dc_readout](cavity/michelson_dc_readout.md) · [pdh_error_signal](cavity/pdh_error_signal.md) · [quantum_noise_budget](cavity/quantum_noise_budget.md)

### coherent (6)

[coherent_image](coherent/coherent_image.md) · [laser_line_coherent](coherent/laser_line_coherent.md) · [speckle_field](coherent/speckle_field.md) · [speckle_reduction](coherent/speckle_reduction.md) · [speckle_statistics](coherent/speckle_statistics.md) · [triangulation_speckle_limit](coherent/triangulation_speckle_limit.md)

### confocal (6)

[chromatic_confocal_limits](confocal/chromatic_confocal_limits.md) · [chromatic_confocal_peaks](confocal/chromatic_confocal_peaks.md) · [chromatic_confocal_probe](confocal/chromatic_confocal_probe.md) · [chromatic_confocal_readout](confocal/chromatic_confocal_readout.md) · [chromatic_confocal_spectrum](confocal/chromatic_confocal_spectrum.md) · [confocal_axial_response](confocal/confocal_axial_response.md)

### design (22)

[chief_ray](design/chief_ray.md) · [chromatic_shift](design/chromatic_shift.md) · [example_system](design/example_system.md) · [glass](design/glass.md) · [glass_catalog](design/glass_catalog.md) · [lens_system](design/lens_system.md) · [opd_map](design/opd_map.md) · [opd_samples](design/opd_samples.md) · [paraxial_trace](design/paraxial_trace.md) · [ray_aiming](design/ray_aiming.md) · [ray_bundle](design/ray_bundle.md) · [ray_fan](design/ray_fan.md) · [seidel_coefficients](design/seidel_coefficients.md) · [sellmeier](design/sellmeier.md) · [set_vignetting](design/set_vignetting.md) · [spot_diagram](design/spot_diagram.md) · [spot_stats](design/spot_stats.md) · [thick_lens](design/thick_lens.md) · [tolerance_analysis](design/tolerance_analysis.md) · [wavefront_from_opd](design/wavefront_from_opd.md) · [with_aiming](design/with_aiming.md) · [with_wavelength](design/with_wavelength.md)

### drawing (9)

[drawing_dxf](drawing/drawing_dxf.md) · [drawing_raster](drawing/drawing_raster.md) · [drawing_svg](drawing/drawing_svg.md) · [dxf_entities](drawing/dxf_entities.md) · [lens_element_drawing](drawing/lens_element_drawing.md) · [lens_section_drawing](drawing/lens_section_drawing.md) · [noncoaxial_drawing](drawing/noncoaxial_drawing.md) · [svg_entities](drawing/svg_entities.md) · [vision_setup_drawing](drawing/vision_setup_drawing.md)

### fiber (7)

[fiber_bundle_coupling](fiber/fiber_bundle_coupling.md) · [fiber_lp_modes](fiber/fiber_lp_modes.md) · [fiber_mode_field_diameter](fiber/fiber_mode_field_diameter.md) · [fiber_numerical_aperture](fiber/fiber_numerical_aperture.md) · [fiber_v_number](fiber/fiber_v_number.md) · [material_group_index](fiber/material_group_index.md) · [material_gvd](fiber/material_gvd.md)

### film (5)

[film_color](film/film_color.md) · [film_thickness_fft](film/film_thickness_fft.md) · [film_thickness_fit](film/film_thickness_fit.md) · [film_thickness_map](film/film_thickness_map.md) · [multilayer_reflectance](film/multilayer_reflectance.md)

### finish (5)

[blast_normals](finish/blast_normals.md) · [finish_catalog](finish/finish_catalog.md) · [finish_shade](finish/finish_shade.md) · [micro_normals](finish/micro_normals.md) · [tangent_field](finish/tangent_field.md)

### fpm (6)

[fp_capture](fpm/fp_capture.md) · [fp_design](fpm/fp_design.md) · [fp_element_contrast](fpm/fp_element_contrast.md) · [fp_reconstruct](fpm/fp_reconstruct.md) · [fp_stack_from_images](fpm/fp_stack_from_images.md) · [fp_usaf_target](fpm/fp_usaf_target.md)

### geometric (5)

[abcd_matrix](geometric/abcd_matrix.md) · [abcd_trace](geometric/abcd_trace.md) · [depth_of_field](geometric/depth_of_field.md) · [relative_illumination](geometric/relative_illumination.md) · [thin_lens](geometric/thin_lens.md)

### glassbody (4)

[beer_lambert_transmittance](glassbody/beer_lambert_transmittance.md) · [prism_min_deviation_deg](glassbody/prism_min_deviation_deg.md) · [refract_rays](glassbody/refract_rays.md) · [slab_transmittance](glassbody/slab_transmittance.md)

### grating_interf (8)

[darkfield_scatter_relation](grating_interf/darkfield_scatter_relation.md) · [dpc_integrate](grating_interf/dpc_integrate.md) · [grating_step_period_estimate](grating_interf/grating_step_period_estimate.md) · [grating_stepping_simulate](grating_interf/grating_stepping_simulate.md) · [grating_three_image_retrieve](grating_interf/grating_three_image_retrieve.md) · [talbot_carpet](grating_interf/talbot_carpet.md) · [talbot_grating_design](grating_interf/talbot_grating_design.md) · [talbot_source_visibility](grating_interf/talbot_source_visibility.md)

### illumination (14)

[coaxial_illumination](illumination/coaxial_illumination.md) · [defect_contrast](illumination/defect_contrast.md) · [illumination_design](illumination/illumination_design.md) · [illumination_field](illumination/illumination_field.md) · [illumination_train](illumination/illumination_train.md) · [illumination_uniformity](illumination/illumination_uniformity.md) · [irradiance_map](illumination/irradiance_map.md) · [light_source](illumination/light_source.md) · [lighting_sweep](illumination/lighting_sweep.md) · [solid_angle_boundaries](illumination/solid_angle_boundaries.md) · [solid_angle_brightness](illumination/solid_angle_brightness.md) · [solid_angle_light](illumination/solid_angle_light.md) · [solid_angle_render](illumination/solid_angle_render.md) · [solid_angle_sweep](illumination/solid_angle_sweep.md)

### imaging (11)

[edge_spread](imaging/edge_spread.md) · [encircled_energy](imaging/encircled_energy.md) · [energy_radii](imaging/energy_radii.md) · [ensquared_energy](imaging/ensquared_energy.md) · [mtf50](imaging/mtf50.md) · [mtf_diffraction](imaging/mtf_diffraction.md) · [mtf_tangential_sagittal](imaging/mtf_tangential_sagittal.md) · [psf_to_mtf](imaging/psf_to_mtf.md) · [sfr_from_edge](imaging/sfr_from_edge.md) · [veiling_glare_index](imaging/veiling_glare_index.md) · [wavefront_stats](imaging/wavefront_stats.md)

### imaging_sim (6)

[calibration_views](imaging_sim/calibration_views.md) · [defect_dataset](imaging_sim/defect_dataset.md) · [distortion_map](imaging_sim/distortion_map.md) · [psf_from_opd](imaging_sim/psf_from_opd.md) · [render_through_lens](imaging_sim/render_through_lens.md) · [through_focus_mtf](imaging_sim/through_focus_mtf.md)

### interface (4)

[brewster_angle_deg](interface/brewster_angle_deg.md) · [critical_angle_deg](interface/critical_angle_deg.md) · [fresnel_conductor](interface/fresnel_conductor.md) · [fresnel_dielectric](interface/fresnel_dielectric.md)

### itof (8)

[itof_capture](itof/itof_capture.md) · [itof_flying_pixel_mask](itof/itof_flying_pixel_mask.md) · [itof_multipath_separate](itof/itof_multipath_separate.md) · [itof_noise_budget](itof/itof_noise_budget.md) · [itof_phase_amplitude](itof/itof_phase_amplitude.md) · [itof_unwrap_error_rate](itof/itof_unwrap_error_rate.md) · [itof_unwrap_multifreq](itof/itof_unwrap_multifreq.md) · [itof_wiggling_correct](itof/itof_wiggling_correct.md)

### lensconfig (5)

[lens_add_configuration](lensconfig/lens_add_configuration.md) · [lens_configuration_metrics](lensconfig/lens_configuration_metrics.md) · [lens_configuration_table](lensconfig/lens_configuration_table.md) · [lens_configurations](lensconfig/lens_configurations.md) · [lens_with_configuration](lensconfig/lens_with_configuration.md)

### lensfile (4)

[lens_file_read](lensfile/lens_file_read.md) · [lens_file_report](lensfile/lens_file_report.md) · [lens_file_system](lensfile/lens_file_system.md) · [lens_file_write](lensfile/lens_file_write.md)

### lensglobal (3)

[glass_nearest](lensglobal/glass_nearest.md) · [lens_global_search](lensglobal/lens_global_search.md) · [lens_substitute_glasses](lensglobal/lens_substitute_glasses.md)

### lensmerit (6)

[merit_boundary_operands](lensmerit/merit_boundary_operands.md) · [merit_contributions](lensmerit/merit_contributions.md) · [merit_default](lensmerit/merit_default.md) · [merit_evaluate](lensmerit/merit_evaluate.md) · [merit_operands_list](lensmerit/merit_operands_list.md) · [optimize_lens_operands](lensmerit/optimize_lens_operands.md)

### lensrender (8)

[bokeh_shape](lensrender/bokeh_shape.md) · [exit_pupil_samples](lensrender/exit_pupil_samples.md) · [lens_scene](lensrender/lens_scene.md) · [render_compare_prescriptions](lensrender/render_compare_prescriptions.md) · [render_ghost_overlay](lensrender/render_ghost_overlay.md) · [render_scene_through_lens](lensrender/render_scene_through_lens.md) · [scene_radiance](lensrender/scene_radiance.md) · [trace_sensor_rays](lensrender/trace_sensor_rays.md)

### lenssolve (9)

[afocal_system](lenssolve/afocal_system.md) · [lens_afocal_report](lenssolve/lens_afocal_report.md) · [lens_apply_solves](lenssolve/lens_apply_solves.md) · [lens_image_surface](lenssolve/lens_image_surface.md) · [lens_petzval_radius](lenssolve/lens_petzval_radius.md) · [lens_solve_clear](lenssolve/lens_solve_clear.md) · [lens_solve_set](lenssolve/lens_solve_set.md) · [lens_solves_list](lenssolve/lens_solves_list.md) · [lens_zmx_solves_roundtrip](lenssolve/lens_zmx_solves_roundtrip.md)

### light_transport (11)

[form_factors_2d](light_transport/form_factors_2d.md) · [fringe_multipath_phase_error](light_transport/fringe_multipath_phase_error.md) · [groove_profile](light_transport/groove_profile.md) · [high_frequency_patterns](light_transport/high_frequency_patterns.md) · [micro_phase_decode](light_transport/micro_phase_decode.md) · [predict_fringe_phase_error](light_transport/predict_fringe_phase_error.md) · [render_transport](light_transport/render_transport.md) · [separate_direct_global](light_transport/separate_direct_global.md) · [tof_multipath_phase](light_transport/tof_multipath_phase.md) · [tof_transport_depth](light_transport/tof_transport_depth.md) · [transport_matrix_radiosity](light_transport/transport_matrix_radiosity.md)

### linescan (6)

[lens_field_profile](linescan/lens_field_profile.md) · [linescan_acquire](linescan/linescan_acquire.md) · [linescan_lens_columns](linescan/linescan_lens_columns.md) · [linescan_lens_example](linescan/linescan_lens_example.md) · [tdi_snr](linescan/tdi_snr.md) · [tdi_sync_mtf](linescan/tdi_sync_mtf.md)

### lockin (9)

[lockin_amplitude](lockin/lockin_amplitude.md) · [lockin_demodulate](lockin/lockin_demodulate.md) · [lockin_noise_floor](lockin/lockin_noise_floor.md) · [lockin_phase](lockin/lockin_phase.md) · [lockin_ring_normals](lockin/lockin_ring_normals.md) · [lockin_ring_synthesize](lockin/lockin_ring_synthesize.md) · [lockin_separate](lockin/lockin_separate.md) · [lockin_thermal_wave](lockin/lockin_thermal_wave.md) · [lockin_walsh_codes](lockin/lockin_walsh_codes.md)

### material (6)

[clearcoat_shade](material/clearcoat_shade.md) · [material_catalog](material/material_catalog.md) · [oren_nayar](material/oren_nayar.md) · [sheen_shade](material/sheen_shade.md) · [subsurface_approx](material/subsurface_approx.md) · [wetness](material/wetness.md)

### matprop (22)

[abbe_number](matprop/abbe_number.md) · [acoustic_impedance_mismatch](matprop/acoustic_impedance_mismatch.md) · [carbon_black_absorption](matprop/carbon_black_absorption.md) · [glass_map](matprop/glass_map.md) · [material_absorption](matprop/material_absorption.md) · [material_acoustic](matprop/material_acoustic.md) · [material_dispersion](matprop/material_dispersion.md) · [material_electron_properties](matprop/material_electron_properties.md) · [material_extinction](matprop/material_extinction.md) · [material_from_curves](matprop/material_from_curves.md) · [material_from_sellmeier](matprop/material_from_sellmeier.md) · [material_nir_absorption](matprop/material_nir_absorption.md) · [material_optical_constants](matprop/material_optical_constants.md) · [material_record](matprop/material_record.md) · [material_reflectance](matprop/material_reflectance.md) · [material_table](matprop/material_table.md) · [material_transmittance](matprop/material_transmittance.md) · [nir_model_info](matprop/nir_model_info.md) · [plate_focus_shift](matprop/plate_focus_shift.md) · [read_glass_catalog_agf](matprop/read_glass_catalog_agf.md) · [silicon_free_carrier_absorption](matprop/silicon_free_carrier_absorption.md) · [thermo_optic_coefficient](matprop/thermo_optic_coefficient.md)

### mirror (2)

[metal_mirror_rgb](mirror/metal_mirror_rgb.md) · [metal_optical_constants](mirror/metal_optical_constants.md)

### moire_align (8)

[moire_differential_shift](moire_align/moire_differential_shift.md) · [moire_magnification](moire_align/moire_magnification.md) · [moire_mark_read](moire_align/moire_mark_read.md) · [moire_overlay_image](moire_align/moire_overlay_image.md) · [moire_phase](moire_align/moire_phase.md) · [moire_phase_crlb](moire_align/moire_phase_crlb.md) · [moire_phase_to_shift](moire_align/moire_phase_to_shift.md) · [moire_talbot_gap](moire_align/moire_talbot_gap.md)

### noncoaxial (13)

[beamsplitter_branches](noncoaxial/beamsplitter_branches.md) · [ghost_analysis](noncoaxial/ghost_analysis.md) · [ghost_image](noncoaxial/ghost_image.md) · [ghost_path](noncoaxial/ghost_path.md) · [image_orientation](noncoaxial/image_orientation.md) · [noncoaxial_example](noncoaxial/noncoaxial_example.md) · [noncoaxial_layout](noncoaxial/noncoaxial_layout.md) · [noncoaxial_spot](noncoaxial/noncoaxial_spot.md) · [noncoaxial_system](noncoaxial/noncoaxial_system.md) · [noncoaxial_trace](noncoaxial/noncoaxial_trace.md) · [scheimpflug_tilt](noncoaxial/scheimpflug_tilt.md) · [surface_reflectance](noncoaxial/surface_reflectance.md) · [tilted_plate_shift](noncoaxial/tilted_plate_shift.md)

### oct (13)

[oct_ascan](oct/oct_ascan.md) · [oct_bscan](oct/oct_bscan.md) · [oct_bscan_boundaries](oct/oct_bscan_boundaries.md) · [oct_bscan_flatten](oct/oct_bscan_flatten.md) · [oct_bscan_simulate](oct/oct_bscan_simulate.md) · [oct_design](oct/oct_design.md) · [oct_dispersion_broadening](oct/oct_dispersion_broadening.md) · [oct_dispersion_compensate](oct/oct_dispersion_compensate.md) · [oct_dispersion_estimate](oct/oct_dispersion_estimate.md) · [oct_from_spectra](oct/oct_from_spectra.md) · [oct_interferogram](oct/oct_interferogram.md) · [oct_k_linearize](oct/oct_k_linearize.md) · [oct_layer_thickness](oct/oct_layer_thickness.md)

### omni360 (24)

[anaglyph_crosstalk](omni360/anaglyph_crosstalk.md) · [anaglyph_from_ods](omni360/anaglyph_from_ods.md) · [cubemap_from_equirect](omni360/cubemap_from_equirect.md) · [equirect_defect_unwrap_pipe](omni360/equirect_defect_unwrap_pipe.md) · [equirect_filter_gaussian](omni360/equirect_filter_gaussian.md) · [equirect_from_cubemap](omni360/equirect_from_cubemap.md) · [equirect_from_fisheye_pair](omni360/equirect_from_fisheye_pair.md) · [equirect_from_perspectives](omni360/equirect_from_perspectives.md) · [equirect_rotate](omni360/equirect_rotate.md) · [equirect_stabilize](omni360/equirect_stabilize.md) · [equirect_weight_map](omni360/equirect_weight_map.md) · [ods_depth_to_disparity](omni360/ods_depth_to_disparity.md) · [ods_disparity_to_depth](omni360/ods_disparity_to_depth.md) · [ods_render](omni360/ods_render.md) · [omni_anaglyph_compose](omni360/omni_anaglyph_compose.md) · [s_psnr](omni360/s_psnr.md) · [stereo360_sbs](omni360/stereo360_sbs.md) · [stereo360_top_bottom](omni360/stereo360_top_bottom.md) · [stereo_pack](omni360/stereo_pack.md) · [stereo_parallax_budget](omni360/stereo_parallax_budget.md) · [video360_tile_coverage](omni360/video360_tile_coverage.md) · [video360_viewport_track](omni360/video360_viewport_track.md) · [viewport_from_equirect](omni360/viewport_from_equirect.md) · [ws_psnr](omni360/ws_psnr.md)

### optimization (3)

[bend_singlet](optimization/bend_singlet.md) · [merit_function](optimization/merit_function.md) · [optimize_lens](optimization/optimize_lens.md)

### pixelshift (6)

[false_color_metric](pixelshift/false_color_metric.md) · [pixel_shift_capture](pixelshift/pixel_shift_capture.md) · [pixel_shift_merge](pixelshift/pixel_shift_merge.md) · [pixel_shift_motion_mask](pixelshift/pixel_shift_motion_mask.md) · [pixel_shift_pattern](pixelshift/pixel_shift_pattern.md) · [pixel_shift_resolution_budget](pixelshift/pixel_shift_resolution_budget.md)

### plenoptic (6)

[mla_surface](plenoptic/mla_surface.md) · [plenoptic_capture](plenoptic/plenoptic_capture.md) · [plenoptic_decode](plenoptic/plenoptic_decode.md) · [plenoptic_mla_calibrate](plenoptic/plenoptic_mla_calibrate.md) · [plenoptic_refocus_depth](plenoptic/plenoptic_refocus_depth.md) · [plenoptic_system](plenoptic/plenoptic_system.md)

### polarization (10)

[jones_apply](polarization/jones_apply.md) · [jones_element](polarization/jones_element.md) · [mueller_apply](polarization/mueller_apply.md) · [mueller_checks](polarization/mueller_checks.md) · [mueller_element](polarization/mueller_element.md) · [mueller_from_intensities](polarization/mueller_from_intensities.md) · [polarization_demosaic](polarization/polarization_demosaic.md) · [polarization_demosaic_color](polarization/polarization_demosaic_color.md) · [stokes_analyze](polarization/stokes_analyze.md) · [stokes_from_jones](polarization/stokes_from_jones.md)

### radiosity (7)

[form_factor_matrix](radiosity/form_factor_matrix.md) · [form_factor_parallel_rects](radiosity/form_factor_parallel_rects.md) · [form_factor_perpendicular_rects](radiosity/form_factor_perpendicular_rects.md) · [form_factor_polygons](radiosity/form_factor_polygons.md) · [radiosity_patches](radiosity/radiosity_patches.md) · [radiosity_progressive_3d](radiosity/radiosity_progressive_3d.md) · [render_optscene_gi](radiosity/render_optscene_gi.md)

### scene (44)

[airy_radius_um](scene/airy_radius_um.md) · [camera_rays](scene/camera_rays.md) · [covers_sensor](scene/covers_sensor.md) · [dataset_throughput](scene/dataset_throughput.md) · [defocus_blur](scene/defocus_blur.md) · [diffraction_blur](scene/diffraction_blur.md) · [env_lightbox](scene/env_lightbox.md) · [env_studio](scene/env_studio.md) · [illumination_visibility](scene/illumination_visibility.md) · [inspection_dataset](scene/inspection_dataset.md) · [interface_budget](scene/interface_budget.md) · [layout_capture](scene/layout_capture.md) · [lens_catalog](scene/lens_catalog.md) · [lens_spec](scene/lens_spec.md) · [light_catalog](scene/light_catalog.md) · [light_spec](scene/light_spec.md) · [light_wavelengths](scene/light_wavelengths.md) · [linescan_capture](scene/linescan_capture.md) · [observe_surface](scene/observe_surface.md) · [optical_budget](scene/optical_budget.md) · [optical_camera](scene/optical_camera.md) · [optscene_defect_mask](scene/optscene_defect_mask.md) · [optscene_depth](scene/optscene_depth.md) · [optscene_instances](scene/optscene_instances.md) · [optscene_mask](scene/optscene_mask.md) · [random_defects](scene/random_defects.md) · [reflect_rays](scene/reflect_rays.md) · [register_light](scene/register_light.md) · [render_optscene](scene/render_optscene.md) · [render_studio](scene/render_studio.md) · [scene_box](scene/scene_box.md) · [scene_cylinder](scene/scene_cylinder.md) · [scene_difference](scene/scene_difference.md) · [scene_material](scene/scene_material.md) · [scene_plane](scene/scene_plane.md) · [scene_sphere](scene/scene_sphere.md) · [sensor_capture](scene/sensor_capture.md) · [sensor_catalog](scene/sensor_catalog.md) · [sensor_diagonal_mm](scene/sensor_diagonal_mm.md) · [sensor_spec](scene/sensor_spec.md) · [surface_defect](scene/surface_defect.md) · [surface_finish](scene/surface_finish.md) · [trace_rays](scene/trace_rays.md) · [vision_layout](scene/vision_layout.md)

### sensorchar (19)

[emva_bspline_regression](sensorchar/emva_bspline_regression.md) · [emva_dark_current](sensorchar/emva_dark_current.md) · [emva_defect_pixels](sensorchar/emva_defect_pixels.md) · [emva_dynamic_range](sensorchar/emva_dynamic_range.md) · [emva_exposure_for_snr](sensorchar/emva_exposure_for_snr.md) · [emva_filter_distortion](sensorchar/emva_filter_distortion.md) · [emva_highpass](sensorchar/emva_highpass.md) · [emva_linearity_error](sensorchar/emva_linearity_error.md) · [emva_noise_whiteness](sensorchar/emva_noise_whiteness.md) · [emva_pair_statistics](sensorchar/emva_pair_statistics.md) · [emva_photon_exposure](sensorchar/emva_photon_exposure.md) · [emva_photon_transfer](sensorchar/emva_photon_transfer.md) · [emva_ptc_linearity_check](sensorchar/emva_ptc_linearity_check.md) · [emva_quantum_efficiency](sensorchar/emva_quantum_efficiency.md) · [emva_sensitivity_threshold](sensorchar/emva_sensitivity_threshold.md) · [emva_snr_curve](sensorchar/emva_snr_curve.md) · [emva_spatial_nonuniformity](sensorchar/emva_spatial_nonuniformity.md) · [emva_spectrogram](sensorchar/emva_spectrogram.md) · [emva_total_snr](sensorchar/emva_total_snr.md)

### sensorgeneral (3)

[emva_general_nonuniformity](sensorgeneral/emva_general_nonuniformity.md) · [emva_general_relative_qe](sensorgeneral/emva_general_relative_qe.md) · [emva_general_sensitivity](sensorgeneral/emva_general_sensitivity.md)

### shape_from_polarization (8)

[aolp_to_azimuth](shape_from_polarization/aolp_to_azimuth.md) · [dolp_to_zenith](shape_from_polarization/dolp_to_zenith.md) · [sfp_disambiguate](shape_from_polarization/sfp_disambiguate.md) · [sfp_dolp_model](shape_from_polarization/sfp_dolp_model.md) · [sfp_estimate_index](shape_from_polarization/sfp_estimate_index.md) · [sfp_height](shape_from_polarization/sfp_height.md) · [sfp_normals](shape_from_polarization/sfp_normals.md) · [sfp_render](shape_from_polarization/sfp_render.md)

### spectral (15)

[bandpass_spectrum](spectral/bandpass_spectrum.md) · [blackbody_spectrum](spectral/blackbody_spectrum.md) · [cie_illuminant_a](spectral/cie_illuminant_a.md) · [energy_to_photons](spectral/energy_to_photons.md) · [hyperspectral_band_weights](spectral/hyperspectral_band_weights.md) · [hyperspectral_capture](spectral/hyperspectral_capture.md) · [ingaas_photodiode_qe](spectral/ingaas_photodiode_qe.md) · [kubelka_munk_reflectance](spectral/kubelka_munk_reflectance.md) · [led_spectrum](spectral/led_spectrum.md) · [silicon_photodiode_qe](spectral/silicon_photodiode_qe.md) · [spectral_integral](spectral/spectral_integral.md) · [spectral_integral_table](spectral/spectral_integral_table.md) · [spectral_product](spectral/spectral_product.md) · [spectral_reflectance_from_material](spectral/spectral_reflectance_from_material.md) · [spectral_stats](spectral/spectral_stats.md)

### spectrometer (5)

[czerny_turner_design](spectrometer/czerny_turner_design.md) · [grating_dispersion](spectrometer/grating_dispersion.md) · [spectrometer_bandpass](spectrometer/spectrometer_bandpass.md) · [spectrometer_slit_image](spectrometer/spectrometer_slit_image.md) · [spectrometer_spectrum](spectrometer/spectrometer_spectrum.md)

### surface (5)

[corrosion_mask](surface/corrosion_mask.md) · [metallic_flake_normals](surface/metallic_flake_normals.md) · [rough_transmission](surface/rough_transmission.md) · [weave_normals](surface/weave_normals.md) · [wood_grain](surface/wood_grain.md)

### telecentric (7)

[chief_ray_angle](telecentric/chief_ray_angle.md) · [defocus_spot_vs_depth](telecentric/defocus_spot_vs_depth.md) · [lens_equivalent_pinhole](telecentric/lens_equivalent_pinhole.md) · [magnification_vs_depth](telecentric/magnification_vs_depth.md) · [telecentric_lens](telecentric/telecentric_lens.md) · [telecentricity_error](telecentric/telecentricity_error.md) · [vignetting_vs_field](telecentric/vignetting_vs_field.md)

### tem (11)

[tem_amorphous_film](tem/tem_amorphous_film.md) · [tem_ctf](tem/tem_ctf.md) · [tem_ctf_correct](tem/tem_ctf_correct.md) · [tem_ctf_estimate](tem/tem_ctf_estimate.md) · [tem_ctf_profile](tem/tem_ctf_profile.md) · [tem_image_weak_phase](tem/tem_image_weak_phase.md) · [tem_multislice](tem/tem_multislice.md) · [tem_power_spectrum](tem/tem_power_spectrum.md) · [tem_projected_potential](tem/tem_projected_potential.md) · [tem_scherzer](tem/tem_scherzer.md) · [tem_wavelength](tem/tem_wavelength.md)

### tolerancing (8)

[tolerance_compensators](tolerancing/tolerance_compensators.md) · [tolerance_criteria](tolerancing/tolerance_criteria.md) · [tolerance_monte_carlo](tolerancing/tolerance_monte_carlo.md) · [tolerance_report](tolerancing/tolerance_report.md) · [tolerance_sensitivity](tolerancing/tolerance_sensitivity.md) · [tolerance_table](tolerancing/tolerance_table.md) · [tolerance_table_from_zmx](tolerancing/tolerance_table_from_zmx.md) · [tolerance_table_zmx](tolerancing/tolerance_table_zmx.md)

### watermedia (10)

[cylinder_lens_caustic](watermedia/cylinder_lens_caustic.md) · [fresnel_water_air](watermedia/fresnel_water_air.md) · [ocean_height_field](watermedia/ocean_height_field.md) · [ocean_spectrum](watermedia/ocean_spectrum.md) · [phase_function_hg](watermedia/phase_function_hg.md) · [refracted_view](watermedia/refracted_view.md) · [scattering_phase_petzold](watermedia/scattering_phase_petzold.md) · [snell_window](watermedia/snell_window.md) · [underwater_image](watermedia/underwater_image.md) · [water_attenuation](watermedia/water_attenuation.md)

### watervision (7)

[bottle_image](watervision/bottle_image.md) · [caustic_floor_segmentation](watervision/caustic_floor_segmentation.md) · [caustic_irradiance](watervision/caustic_irradiance.md) · [fill_level_from_image](watervision/fill_level_from_image.md) · [underwater_inspection_image](watervision/underwater_inspection_image.md) · [wet_dry_inspection_pair](watervision/wet_dry_inspection_pair.md) · [wet_surface_appearance](watervision/wet_surface_appearance.md)

### wave (9)

[airy_pattern](wave/airy_pattern.md) · [angular_spectrum_propagate](wave/angular_spectrum_propagate.md) · [defocus_from_shift](wave/defocus_from_shift.md) · [four_f_filter](wave/four_f_filter.md) · [fourier_plane_filter](wave/fourier_plane_filter.md) · [fraunhofer_pattern](wave/fraunhofer_pattern.md) · [gaussian_beam](wave/gaussian_beam.md) · [pupil_blur](wave/pupil_blur.md) · [pupil_psf](wave/pupil_psf.md)

---
© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
