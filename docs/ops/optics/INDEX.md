# OPTICS operator help — 242 ops in 28 categories

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

### design (15)

[chromatic_shift](design/chromatic_shift.md) · [example_system](design/example_system.md) · [glass](design/glass.md) · [glass_catalog](design/glass_catalog.md) · [lens_system](design/lens_system.md) · [opd_map](design/opd_map.md) · [paraxial_trace](design/paraxial_trace.md) · [ray_fan](design/ray_fan.md) · [seidel_coefficients](design/seidel_coefficients.md) · [sellmeier](design/sellmeier.md) · [spot_diagram](design/spot_diagram.md) · [spot_stats](design/spot_stats.md) · [thick_lens](design/thick_lens.md) · [tolerance_analysis](design/tolerance_analysis.md) · [wavefront_from_opd](design/wavefront_from_opd.md)

### fiber (7)

[fiber_bundle_coupling](fiber/fiber_bundle_coupling.md) · [fiber_lp_modes](fiber/fiber_lp_modes.md) · [fiber_mode_field_diameter](fiber/fiber_mode_field_diameter.md) · [fiber_numerical_aperture](fiber/fiber_numerical_aperture.md) · [fiber_v_number](fiber/fiber_v_number.md) · [material_group_index](fiber/material_group_index.md) · [material_gvd](fiber/material_gvd.md)

### finish (5)

[blast_normals](finish/blast_normals.md) · [finish_catalog](finish/finish_catalog.md) · [finish_shade](finish/finish_shade.md) · [micro_normals](finish/micro_normals.md) · [tangent_field](finish/tangent_field.md)

### geometric (5)

[abcd_matrix](geometric/abcd_matrix.md) · [abcd_trace](geometric/abcd_trace.md) · [depth_of_field](geometric/depth_of_field.md) · [relative_illumination](geometric/relative_illumination.md) · [thin_lens](geometric/thin_lens.md)

### glassbody (4)

[beer_lambert_transmittance](glassbody/beer_lambert_transmittance.md) · [prism_min_deviation_deg](glassbody/prism_min_deviation_deg.md) · [refract_rays](glassbody/refract_rays.md) · [slab_transmittance](glassbody/slab_transmittance.md)

### illumination (6)

[defect_contrast](illumination/defect_contrast.md) · [illumination_design](illumination/illumination_design.md) · [illumination_uniformity](illumination/illumination_uniformity.md) · [irradiance_map](illumination/irradiance_map.md) · [light_source](illumination/light_source.md) · [lighting_sweep](illumination/lighting_sweep.md)

### imaging (7)

[edge_spread](imaging/edge_spread.md) · [mtf50](imaging/mtf50.md) · [mtf_diffraction](imaging/mtf_diffraction.md) · [psf_to_mtf](imaging/psf_to_mtf.md) · [sfr_from_edge](imaging/sfr_from_edge.md) · [veiling_glare_index](imaging/veiling_glare_index.md) · [wavefront_stats](imaging/wavefront_stats.md)

### imaging_sim (5)

[calibration_views](imaging_sim/calibration_views.md) · [defect_dataset](imaging_sim/defect_dataset.md) · [distortion_map](imaging_sim/distortion_map.md) · [psf_from_opd](imaging_sim/psf_from_opd.md) · [render_through_lens](imaging_sim/render_through_lens.md)

### interface (4)

[brewster_angle_deg](interface/brewster_angle_deg.md) · [critical_angle_deg](interface/critical_angle_deg.md) · [fresnel_conductor](interface/fresnel_conductor.md) · [fresnel_dielectric](interface/fresnel_dielectric.md)

### light_transport (11)

[form_factors_2d](light_transport/form_factors_2d.md) · [fringe_multipath_phase_error](light_transport/fringe_multipath_phase_error.md) · [groove_profile](light_transport/groove_profile.md) · [high_frequency_patterns](light_transport/high_frequency_patterns.md) · [micro_phase_decode](light_transport/micro_phase_decode.md) · [predict_fringe_phase_error](light_transport/predict_fringe_phase_error.md) · [render_transport](light_transport/render_transport.md) · [separate_direct_global](light_transport/separate_direct_global.md) · [tof_multipath_phase](light_transport/tof_multipath_phase.md) · [tof_transport_depth](light_transport/tof_transport_depth.md) · [transport_matrix_radiosity](light_transport/transport_matrix_radiosity.md)

### linescan (6)

[lens_field_profile](linescan/lens_field_profile.md) · [linescan_acquire](linescan/linescan_acquire.md) · [linescan_lens_columns](linescan/linescan_lens_columns.md) · [linescan_lens_example](linescan/linescan_lens_example.md) · [tdi_snr](linescan/tdi_snr.md) · [tdi_sync_mtf](linescan/tdi_sync_mtf.md)

### material (6)

[clearcoat_shade](material/clearcoat_shade.md) · [material_catalog](material/material_catalog.md) · [oren_nayar](material/oren_nayar.md) · [sheen_shade](material/sheen_shade.md) · [subsurface_approx](material/subsurface_approx.md) · [wetness](material/wetness.md)

### matprop (16)

[abbe_number](matprop/abbe_number.md) · [glass_map](matprop/glass_map.md) · [material_absorption](matprop/material_absorption.md) · [material_dispersion](matprop/material_dispersion.md) · [material_extinction](matprop/material_extinction.md) · [material_from_curves](matprop/material_from_curves.md) · [material_from_sellmeier](matprop/material_from_sellmeier.md) · [material_optical_constants](matprop/material_optical_constants.md) · [material_record](matprop/material_record.md) · [material_reflectance](matprop/material_reflectance.md) · [material_table](matprop/material_table.md) · [material_transmittance](matprop/material_transmittance.md) · [plate_focus_shift](matprop/plate_focus_shift.md) · [read_glass_catalog_agf](matprop/read_glass_catalog_agf.md) · [silicon_free_carrier_absorption](matprop/silicon_free_carrier_absorption.md) · [thermo_optic_coefficient](matprop/thermo_optic_coefficient.md)

### mirror (2)

[metal_mirror_rgb](mirror/metal_mirror_rgb.md) · [metal_optical_constants](mirror/metal_optical_constants.md)

### moire_align (8)

[moire_differential_shift](moire_align/moire_differential_shift.md) · [moire_magnification](moire_align/moire_magnification.md) · [moire_mark_read](moire_align/moire_mark_read.md) · [moire_overlay_image](moire_align/moire_overlay_image.md) · [moire_phase](moire_align/moire_phase.md) · [moire_phase_crlb](moire_align/moire_phase_crlb.md) · [moire_phase_to_shift](moire_align/moire_phase_to_shift.md) · [moire_talbot_gap](moire_align/moire_talbot_gap.md)

### optimization (3)

[bend_singlet](optimization/bend_singlet.md) · [merit_function](optimization/merit_function.md) · [optimize_lens](optimization/optimize_lens.md)

### polarization (10)

[jones_apply](polarization/jones_apply.md) · [jones_element](polarization/jones_element.md) · [mueller_apply](polarization/mueller_apply.md) · [mueller_checks](polarization/mueller_checks.md) · [mueller_element](polarization/mueller_element.md) · [mueller_from_intensities](polarization/mueller_from_intensities.md) · [polarization_demosaic](polarization/polarization_demosaic.md) · [polarization_demosaic_color](polarization/polarization_demosaic_color.md) · [stokes_analyze](polarization/stokes_analyze.md) · [stokes_from_jones](polarization/stokes_from_jones.md)

### scene (44)

[airy_radius_um](scene/airy_radius_um.md) · [camera_rays](scene/camera_rays.md) · [covers_sensor](scene/covers_sensor.md) · [dataset_throughput](scene/dataset_throughput.md) · [defocus_blur](scene/defocus_blur.md) · [diffraction_blur](scene/diffraction_blur.md) · [env_lightbox](scene/env_lightbox.md) · [env_studio](scene/env_studio.md) · [illumination_visibility](scene/illumination_visibility.md) · [inspection_dataset](scene/inspection_dataset.md) · [interface_budget](scene/interface_budget.md) · [layout_capture](scene/layout_capture.md) · [lens_catalog](scene/lens_catalog.md) · [lens_spec](scene/lens_spec.md) · [light_catalog](scene/light_catalog.md) · [light_spec](scene/light_spec.md) · [light_wavelengths](scene/light_wavelengths.md) · [linescan_capture](scene/linescan_capture.md) · [observe_surface](scene/observe_surface.md) · [optical_budget](scene/optical_budget.md) · [optical_camera](scene/optical_camera.md) · [optscene_defect_mask](scene/optscene_defect_mask.md) · [optscene_depth](scene/optscene_depth.md) · [optscene_instances](scene/optscene_instances.md) · [optscene_mask](scene/optscene_mask.md) · [random_defects](scene/random_defects.md) · [reflect_rays](scene/reflect_rays.md) · [register_light](scene/register_light.md) · [render_optscene](scene/render_optscene.md) · [render_studio](scene/render_studio.md) · [scene_box](scene/scene_box.md) · [scene_cylinder](scene/scene_cylinder.md) · [scene_difference](scene/scene_difference.md) · [scene_material](scene/scene_material.md) · [scene_plane](scene/scene_plane.md) · [scene_sphere](scene/scene_sphere.md) · [sensor_capture](scene/sensor_capture.md) · [sensor_catalog](scene/sensor_catalog.md) · [sensor_diagonal_mm](scene/sensor_diagonal_mm.md) · [sensor_spec](scene/sensor_spec.md) · [surface_defect](scene/surface_defect.md) · [surface_finish](scene/surface_finish.md) · [trace_rays](scene/trace_rays.md) · [vision_layout](scene/vision_layout.md)

### sensorchar (19)

[emva_bspline_regression](sensorchar/emva_bspline_regression.md) · [emva_dark_current](sensorchar/emva_dark_current.md) · [emva_defect_pixels](sensorchar/emva_defect_pixels.md) · [emva_dynamic_range](sensorchar/emva_dynamic_range.md) · [emva_exposure_for_snr](sensorchar/emva_exposure_for_snr.md) · [emva_filter_distortion](sensorchar/emva_filter_distortion.md) · [emva_highpass](sensorchar/emva_highpass.md) · [emva_linearity_error](sensorchar/emva_linearity_error.md) · [emva_noise_whiteness](sensorchar/emva_noise_whiteness.md) · [emva_pair_statistics](sensorchar/emva_pair_statistics.md) · [emva_photon_exposure](sensorchar/emva_photon_exposure.md) · [emva_photon_transfer](sensorchar/emva_photon_transfer.md) · [emva_ptc_linearity_check](sensorchar/emva_ptc_linearity_check.md) · [emva_quantum_efficiency](sensorchar/emva_quantum_efficiency.md) · [emva_sensitivity_threshold](sensorchar/emva_sensitivity_threshold.md) · [emva_snr_curve](sensorchar/emva_snr_curve.md) · [emva_spatial_nonuniformity](sensorchar/emva_spatial_nonuniformity.md) · [emva_spectrogram](sensorchar/emva_spectrogram.md) · [emva_total_snr](sensorchar/emva_total_snr.md)

### sensorgeneral (3)

[emva_general_nonuniformity](sensorgeneral/emva_general_nonuniformity.md) · [emva_general_relative_qe](sensorgeneral/emva_general_relative_qe.md) · [emva_general_sensitivity](sensorgeneral/emva_general_sensitivity.md)

### shape_from_polarization (8)

[aolp_to_azimuth](shape_from_polarization/aolp_to_azimuth.md) · [dolp_to_zenith](shape_from_polarization/dolp_to_zenith.md) · [sfp_disambiguate](shape_from_polarization/sfp_disambiguate.md) · [sfp_dolp_model](shape_from_polarization/sfp_dolp_model.md) · [sfp_estimate_index](shape_from_polarization/sfp_estimate_index.md) · [sfp_height](shape_from_polarization/sfp_height.md) · [sfp_normals](shape_from_polarization/sfp_normals.md) · [sfp_render](shape_from_polarization/sfp_render.md)

### spectral (9)

[bandpass_spectrum](spectral/bandpass_spectrum.md) · [blackbody_spectrum](spectral/blackbody_spectrum.md) · [cie_illuminant_a](spectral/cie_illuminant_a.md) · [energy_to_photons](spectral/energy_to_photons.md) · [led_spectrum](spectral/led_spectrum.md) · [silicon_photodiode_qe](spectral/silicon_photodiode_qe.md) · [spectral_integral](spectral/spectral_integral.md) · [spectral_product](spectral/spectral_product.md) · [spectral_stats](spectral/spectral_stats.md)

### surface (5)

[corrosion_mask](surface/corrosion_mask.md) · [metallic_flake_normals](surface/metallic_flake_normals.md) · [rough_transmission](surface/rough_transmission.md) · [weave_normals](surface/weave_normals.md) · [wood_grain](surface/wood_grain.md)

### telecentric (7)

[chief_ray_angle](telecentric/chief_ray_angle.md) · [defocus_spot_vs_depth](telecentric/defocus_spot_vs_depth.md) · [lens_equivalent_pinhole](telecentric/lens_equivalent_pinhole.md) · [magnification_vs_depth](telecentric/magnification_vs_depth.md) · [telecentric_lens](telecentric/telecentric_lens.md) · [telecentricity_error](telecentric/telecentricity_error.md) · [vignetting_vs_field](telecentric/vignetting_vs_field.md)

### wave (9)

[airy_pattern](wave/airy_pattern.md) · [angular_spectrum_propagate](wave/angular_spectrum_propagate.md) · [defocus_from_shift](wave/defocus_from_shift.md) · [four_f_filter](wave/four_f_filter.md) · [fourier_plane_filter](wave/fourier_plane_filter.md) · [fraunhofer_pattern](wave/fraunhofer_pattern.md) · [gaussian_beam](wave/gaussian_beam.md) · [pupil_blur](wave/pupil_blur.md) · [pupil_psf](wave/pupil_psf.md)

---
© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
