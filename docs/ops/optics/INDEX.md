# OPTICS operator help — 118 ops in 16 categories

自動生成(`tools/opdocs.py toc`)。フォルダ階層 `docs/ops/optics/<category>/<op>.md` を走査。

## ファミリ使い方ガイド(用途→op の教材)

- [optics_imaging](guides/optics_imaging.md) — 光学(レンズ・回折・偏光) — 使い方ガイド
- [virtual_machine_vision](guides/virtual_machine_vision.md) — 仮想マシンビジョン — パラメータの洗い出しとオブジェクト模型

## カテゴリ

### appearance (7)

[cie_xyz_from_wavelength](appearance/cie_xyz_from_wavelength.md) · [grating_rgb](appearance/grating_rgb.md) · [grating_wavelengths](appearance/grating_wavelengths.md) · [spectrum_to_srgb](appearance/spectrum_to_srgb.md) · [thin_film_reflectance](appearance/thin_film_reflectance.md) · [thin_film_rgb](appearance/thin_film_rgb.md) · [ward_anisotropic](appearance/ward_anisotropic.md)

### design (15)

[chromatic_shift](design/chromatic_shift.md) · [example_system](design/example_system.md) · [glass](design/glass.md) · [glass_catalog](design/glass_catalog.md) · [lens_system](design/lens_system.md) · [opd_map](design/opd_map.md) · [paraxial_trace](design/paraxial_trace.md) · [ray_fan](design/ray_fan.md) · [seidel_coefficients](design/seidel_coefficients.md) · [sellmeier](design/sellmeier.md) · [spot_diagram](design/spot_diagram.md) · [spot_stats](design/spot_stats.md) · [thick_lens](design/thick_lens.md) · [tolerance_analysis](design/tolerance_analysis.md) · [wavefront_from_opd](design/wavefront_from_opd.md)

### finish (5)

[blast_normals](finish/blast_normals.md) · [finish_catalog](finish/finish_catalog.md) · [finish_shade](finish/finish_shade.md) · [micro_normals](finish/micro_normals.md) · [tangent_field](finish/tangent_field.md)

### geometric (5)

[abcd_matrix](geometric/abcd_matrix.md) · [abcd_trace](geometric/abcd_trace.md) · [depth_of_field](geometric/depth_of_field.md) · [relative_illumination](geometric/relative_illumination.md) · [thin_lens](geometric/thin_lens.md)

### glassbody (4)

[beer_lambert_transmittance](glassbody/beer_lambert_transmittance.md) · [prism_min_deviation_deg](glassbody/prism_min_deviation_deg.md) · [refract_rays](glassbody/refract_rays.md) · [slab_transmittance](glassbody/slab_transmittance.md)

### illumination (6)

[defect_contrast](illumination/defect_contrast.md) · [illumination_design](illumination/illumination_design.md) · [illumination_uniformity](illumination/illumination_uniformity.md) · [irradiance_map](illumination/irradiance_map.md) · [light_source](illumination/light_source.md) · [lighting_sweep](illumination/lighting_sweep.md)

### imaging (3)

[mtf_diffraction](imaging/mtf_diffraction.md) · [psf_to_mtf](imaging/psf_to_mtf.md) · [wavefront_stats](imaging/wavefront_stats.md)

### imaging_sim (5)

[calibration_views](imaging_sim/calibration_views.md) · [defect_dataset](imaging_sim/defect_dataset.md) · [distortion_map](imaging_sim/distortion_map.md) · [psf_from_opd](imaging_sim/psf_from_opd.md) · [render_through_lens](imaging_sim/render_through_lens.md)

### interface (4)

[brewster_angle_deg](interface/brewster_angle_deg.md) · [critical_angle_deg](interface/critical_angle_deg.md) · [fresnel_conductor](interface/fresnel_conductor.md) · [fresnel_dielectric](interface/fresnel_dielectric.md)

### material (6)

[clearcoat_shade](material/clearcoat_shade.md) · [material_catalog](material/material_catalog.md) · [oren_nayar](material/oren_nayar.md) · [sheen_shade](material/sheen_shade.md) · [subsurface_approx](material/subsurface_approx.md) · [wetness](material/wetness.md)

### mirror (2)

[metal_mirror_rgb](mirror/metal_mirror_rgb.md) · [metal_optical_constants](mirror/metal_optical_constants.md)

### optimization (3)

[bend_singlet](optimization/bend_singlet.md) · [merit_function](optimization/merit_function.md) · [optimize_lens](optimization/optimize_lens.md)

### polarization (6)

[jones_apply](polarization/jones_apply.md) · [jones_element](polarization/jones_element.md) · [mueller_apply](polarization/mueller_apply.md) · [mueller_element](polarization/mueller_element.md) · [stokes_analyze](polarization/stokes_analyze.md) · [stokes_from_jones](polarization/stokes_from_jones.md)

### scene (38)

[airy_radius_um](scene/airy_radius_um.md) · [camera_rays](scene/camera_rays.md) · [dataset_throughput](scene/dataset_throughput.md) · [defocus_blur](scene/defocus_blur.md) · [diffraction_blur](scene/diffraction_blur.md) · [env_lightbox](scene/env_lightbox.md) · [env_studio](scene/env_studio.md) · [illumination_visibility](scene/illumination_visibility.md) · [inspection_dataset](scene/inspection_dataset.md) · [interface_budget](scene/interface_budget.md) · [layout_capture](scene/layout_capture.md) · [lens_spec](scene/lens_spec.md) · [light_spec](scene/light_spec.md) · [light_wavelengths](scene/light_wavelengths.md) · [observe_surface](scene/observe_surface.md) · [optical_budget](scene/optical_budget.md) · [optical_camera](scene/optical_camera.md) · [optscene_defect_mask](scene/optscene_defect_mask.md) · [optscene_depth](scene/optscene_depth.md) · [optscene_instances](scene/optscene_instances.md) · [optscene_mask](scene/optscene_mask.md) · [random_defects](scene/random_defects.md) · [reflect_rays](scene/reflect_rays.md) · [render_optscene](scene/render_optscene.md) · [render_studio](scene/render_studio.md) · [scene_box](scene/scene_box.md) · [scene_cylinder](scene/scene_cylinder.md) · [scene_difference](scene/scene_difference.md) · [scene_material](scene/scene_material.md) · [scene_plane](scene/scene_plane.md) · [scene_sphere](scene/scene_sphere.md) · [sensor_capture](scene/sensor_capture.md) · [sensor_catalog](scene/sensor_catalog.md) · [sensor_spec](scene/sensor_spec.md) · [surface_defect](scene/surface_defect.md) · [surface_finish](scene/surface_finish.md) · [trace_rays](scene/trace_rays.md) · [vision_layout](scene/vision_layout.md)

### surface (5)

[corrosion_mask](surface/corrosion_mask.md) · [metallic_flake_normals](surface/metallic_flake_normals.md) · [rough_transmission](surface/rough_transmission.md) · [weave_normals](surface/weave_normals.md) · [wood_grain](surface/wood_grain.md)

### wave (4)

[airy_pattern](wave/airy_pattern.md) · [angular_spectrum_propagate](wave/angular_spectrum_propagate.md) · [fraunhofer_pattern](wave/fraunhofer_pattern.md) · [gaussian_beam](wave/gaussian_beam.md)

---
© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
