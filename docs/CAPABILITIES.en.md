# What Fullseye can do

**Language:** [日本語](CAPABILITIES.md) · [English](CAPABILITIES.en.md)

An index organised by *what you want to do*, not by operator name.
One entry is one file under `docs/capabilities/`, and every entry is tied
to operators that exist and to an example that actually runs —
`tests/test_capabilities.py` checks each operator name against all four
public tiers and each example against the files on disk, so a capability
claim with nothing behind it cannot survive.

* Looking for an operator by name → [operator index](README.en.md)
* Worked problems with planted ground truth → [the PoC museum](README.en.md)
* Five-minute start → [GETTING_STARTED.md](GETTING_STARTED.md)

**To add one**: write `docs/capabilities/<id>.md` and run
`py -3.11 tools/gen_capabilities_index.py` (this index is generated —
do not edit it by hand).

**Currently 24 capabilities**

## Look up by task (recommended pipeline)

Every operator exists in the registry and the types connect from one step to the next (`tests/test_capabilities.py` checks both; only four sort names are treated as synonyms: `image2d`=`image`, `mask`=`region`, `measurement`=`feature`=`scalar`). Values passed as arguments are outside the type chain. Alternatives, limits and calibration are in each entry.

| Task | Recommended pipeline (in order) | Runnable |
|---|---|---|
| [Align and stack](capabilities/align-and-stack.md) | `align_frames` → `drizzle_resample` → `frame_quality` | `poc_astro_photometry` |
| [Beamform for direction, separate range from velocity](capabilities/beamforming-and-range-doppler.md) | `beamform_doa` → `range_doppler_map` → `range_doppler_peaks` | `poc_multibeam_bathymetry` |
| [Segment regions, select them, and count](capabilities/blob-and-region.md) | `auto_threshold` → `blob_label` → `blob_select` → `blob_features` | `poc_cell_counting` |
| [Measure colour (XYZ / Lab / colour difference)](capabilities/colour-and-delta-e.md) | `rgb_to_lab` → `delta_e_2000` | `poc_white_balance` |
| [Turn results into figures people can read](capabilities/figures-and-annotation.md) | `annotate_figure_grid` → `annotate_panel_label` → `annotate_scale_bar` → `annotate_colorbar` | `poc_colormap_readability` |
| [Put measurements on the Earth (ECEF and geodetic)](capabilities/geodetic-frames.md) | `dem_geodetic_to_ecef` → `dem_ecef_to_geodetic` | `poc_geodetic_height_frames` |
| [Inner diameter of a round part, all the way to millimetres](capabilities/inner-diameter-in-mm.md) | `gaussian` → `otsu` → `area_center` → `create_metrology_model` → `add_metrology_object_circle_measure` → `apply_metrology_model` → `mm_per_px_from_reference` → `pixel_to_world` | `example_inner_diameter_mm` |
| [Draw lines and regions without knowing the background colour](capabilities/inverted-colour-overlays.md) | `annotate_invert_visibility` → `annotate_invert` → `annotate_invert_path` | `annotate_paper_tour` |
| [OCR pre-processing (deskew, local binarisation, line extraction)](capabilities/ocr-preprocessing.md) | `median` → `rotate_image` → `sk_sauvola` → `invert_region` → `remove_small` → `select_shape` → `dilation_rectangle1` | `gallery2d_segmentation` |
| [Compute reflection, refraction and interference](capabilities/optics-and-materials.md) | `fresnel_dielectric` → `thin_film_reflectance` → `thin_film_rgb` | `glass_and_mirror_optics` |
| [Periodic defects in a 1-D signal](capabilities/periodic-defects-in-1d-signals.md) | `smooth_funct_1d_gauss` → `bandpass` → `spectrum` → `find_peaks` → `peak_subbin` → `envelope` → `local_min_max_funct_1d` | `poc_web_roll_periodicity` |
| [Flatness of a surface from a 3-D point cloud](capabilities/planarity-from-point-cloud.md) | `statistical_outlier_removal` → `ransac_plane` → `fit_plane_3d` → `distance_point_plane` | `geometry_metrology` |
| [Find small point-like targets and locate them below the pixel](capabilities/point-target-detection.md) | `noise_sigma` → `star_detect` → `find_peaks` → `peak_subbin` | `poc_search_sweep_width` |
| [Remove specular reflection from a four-angle polariser sweep (dielectrics vs metals)](capabilities/polarisation-specular-removal.md) | `polarization_dolp_map` → `polarization_separate` → `polarization_stokes` → `stokes_analyze` → `specular_diffuse_split` | `example_polarization_metal` |
| [Detect fine scratches and measure their width](capabilities/scratch-detection-and-width.md) | `gaussian` → `lines_gauss` → `select_contours` → `fit_line_contours` → `gen_measure_rectangle2` → `measure_pairs` → `table_px_to_mm` | `example_scratch_width` |
| [Measure dimensions from an image, below the pixel](capabilities/subpixel-2d-metrology.md) | `gen_measure_rectangle2` → `measure_pos` → `measure_pairs` → `table_px_to_mm` | `poc_dimensional_inspection` |
| [Surface relief defects, from lighting design to detection](capabilities/surface-defects-with-lighting.md) | `illumination_design` → `lighting_sweep` → `light_source` → `defect_contrast` → `irradiance_map` → `illumination_uniformity` → `photometric_stereo` → `integrate_normals` → `surface_form_error` → `bothat` → `auto_threshold` → `remove_small` | `illumination_design_demo` |
| [Locate a part by template matching and move the measurement model with it](capabilities/template-alignment.md) | `gaussian` → `ncc_locate` → `shape_locate` → `create_metrology_model` → `add_metrology_object_circle_measure` → `align_metrology_model` → `apply_metrology_model` | `poc_template_tracking` |
| [Slope, flow and line of sight on a terrain](capabilities/terrain-and-visibility.md) | `dem_fill_sinks` → `dem_slope` → `dem_aspect` → `dem_flow_direction` → `dem_viewshed` | `poc_dem_terrain` |
| [Put text and tables exactly where you want them on an image](capabilities/text-and-tables-on-images.md) | `measure_text` → `annotate_text_path_layout` → `annotate_text_path` → `annotate_table_layout` → `annotate_table` | `annotate_paper_tour` |
| [Reconstruct slices from projections (CT)](capabilities/tomography-reconstruction.md) | `radon_transform` → `ring_artifact_remove` → `beam_hardening_correct` → `fbp_volume` → `vol_rle_components` → `vol_rle_volume` | `poc_ct_fidelity` |
| [Diagnose faults from vibration and sound](capabilities/vibration-and-acoustics.md) | `bandpass` → `envelope` → `envelope_spectrum` → `find_peaks` → `bearing_defect_frequencies` | `poc_bearing_diagnosis` |
| [Carve a solid out of silhouettes (visual hull)](capabilities/visual-hull-from-silhouettes.md) | `synthesize_silhouette` → `visual_hull` → `vol_rle_components` → `vol_rle_volume` | `space_carving` |
| [Turn a 3-D scan into a volume](capabilities/volume-from-3d-scan.md) | `vol_rle_components` → `vol_rle_volume` → `mesh_volume` | `poc_stockpile_volume` |

## Measure (7)

### [Put measurements on the Earth (ECEF and geodetic)](capabilities/geodetic-frames.md)

Convert between geodetic (latitude, longitude, height) and Earth-centred Cartesian (ECEF) coordinates. The round-trip floor measures 6.4e-12 degrees in latitude and 8.5e-07 m in height (worst case over 4000 points).

Operators: `dem_geodetic_to_ecef`, `dem_ecef_to_geodetic`

Pipeline: [`dem_geodetic_to_ecef`](ops/dem/geodesy/dem_geodetic_to_ecef.md) → [`dem_ecef_to_geodetic`](ops/dem/geodesy/dem_ecef_to_geodetic.md)

Alternatives: [`dem_geodetic_slope`](ops/dem/geodesy/dem_geodetic_slope.md)

Runnable: `poc_geodetic_height_frames`, `dem_geodesy_tour`

### [Inner diameter of a round part, all the way to millimetres](capabilities/inner-diameter-in-mm.md)

Bore, ring and pin diameters end to end: a coarse centre, a sub-pixel circle fit on radial measurement lines, a calibration from a reference of known size, and the result in millimetres. The last two steps exist as typed operators because an assistant working from the notes alone stopped at pixels.

Operators: `add_metrology_object_circle_measure`, `apply_metrology_model`, `mm_per_px_from_reference`, `pixel_to_world`

Pipeline: [`gaussian`](ops/2d/smoothing/gaussian.md) → [`otsu`](ops/2d/segmentation/otsu.md) → [`area_center`](ops/2d/features/area_center.md) → [`create_metrology_model`](ops/measure1d/model/create_metrology_model.md) → [`add_metrology_object_circle_measure`](ops/measure1d/model/add_metrology_object_circle_measure.md) → [`apply_metrology_model`](ops/measure1d/apply/apply_metrology_model.md) → [`mm_per_px_from_reference`](ops/measure1d/scale/mm_per_px_from_reference.md) → [`pixel_to_world`](ops/measure1d/scale/pixel_to_world.md)

Alternatives: [`gen_measure_arc`](ops/measure1d/caliper/gen_measure_arc.md), [`measure_pos`](ops/measure1d/caliper/measure_pos.md), [`hx_fit_circle_contour`](ops/2d/halcon_ext/hx_fit_circle_contour.md), [`cv_hough_circles`](ops/2d/features/cv_hough_circles.md), [`hough_circle_trans`](ops/2d/features/hough_circle_trans.md), [`table_px_to_mm`](ops/measure1d/scale/table_px_to_mm.md)

Runnable: `example_inner_diameter_mm`, `poc_dimensional_inspection`, `poc_real_coin_metrology`

### [Flatness of a surface from a 3-D point cloud](capabilities/planarity-from-point-cloud.md)

From the point cloud of a nominally flat surface: remove outliers, fit a plane robustly, and read flatness (peak-to-valley and RMS) from the signed point-to-plane distances — so warp (low order) and local relief (high order) can be told apart.

Operators: `ransac_plane`, `fit_plane_3d`, `distance_point_plane`, `statistical_outlier_removal`

Pipeline: [`statistical_outlier_removal`](ops/3d/preprocess/statistical_outlier_removal.md) → [`ransac_plane`](ops/3d/robust_fit/ransac_plane.md) → [`fit_plane_3d`](ops/3d/geometry/fit_plane_3d.md) → [`distance_point_plane`](ops/3d/geometry/distance_point_plane.md)

Alternatives: [`fit_plane3`](ops/3d/geometry/fit_plane3.md), [`plane_segmentation`](ops/3d/segment/plane_segmentation.md), [`radius_outlier_removal`](ops/3d/preprocess/radius_outlier_removal.md), [`estimate_normals`](ops/3d/curvature/estimate_normals.md), [`surface_form_error`](ops/3d/surface_fit/surface_form_error.md)

Runnable: `geometry_metrology`, `poc_bump_coplanarity`, `poc_scan_to_bim_asbuilt`

### [Detect fine scratches and measure their width](capabilities/scratch-detection-and-width.md)

Two stages: *where* (ridge response `lines_gauss`, or the black-top-hat `bothat` that lifts only dark fine detail) and *how wide* (a measurement line across the detected line, `measure_pairs` for the two sub-pixel edges, `table_px_to_mm` for millimetres).

Operators: `lines_gauss`, `bothat`, `measure_pairs`, `table_px_to_mm`

Pipeline: [`gaussian`](ops/2d/smoothing/gaussian.md) → [`lines_gauss`](ops/2d/contour/lines_gauss.md) → [`select_contours`](ops/2d/contour/select_contours.md) → [`fit_line_contours`](ops/2d/contour/fit_line_contours.md) → [`gen_measure_rectangle2`](ops/measure1d/caliper/gen_measure_rectangle2.md) → [`measure_pairs`](ops/measure1d/caliper/measure_pairs.md) → [`table_px_to_mm`](ops/measure1d/scale/table_px_to_mm.md)

Alternatives: [`bothat`](ops/2d/morphology/bothat.md), [`tophat`](ops/2d/morphology/tophat.md), [`sk_frangi`](ops/2d/texture/sk_frangi.md), [`laplace_of_gauss`](ops/2d/edges/laplace_of_gauss.md), [`fuzzy_measure_pairing`](ops/measure1d/caliper/fuzzy_measure_pairing.md), [`mm_per_px_from_reference`](ops/measure1d/scale/mm_per_px_from_reference.md)

Runnable: `example_scratch_width`, `poc_crack_width`, `poc_solar_el_inspection`

### [Measure dimensions from an image, below the pixel](capabilities/subpixel-2d-metrology.md)

Locate edges along a measurement line from the intensity gradient, at sub-pixel resolution, and read a dimension as the distance between paired edges. Unlike counting thresholded pixels, the answer does not move when the threshold does.

Operators: `measure_pos`, `measure_pairs`, `blob_label`, `blob_select`

Pipeline: [`gen_measure_rectangle2`](ops/measure1d/caliper/gen_measure_rectangle2.md) → [`measure_pos`](ops/measure1d/caliper/measure_pos.md) → [`measure_pairs`](ops/measure1d/caliper/measure_pairs.md) → [`table_px_to_mm`](ops/measure1d/scale/table_px_to_mm.md)

Alternatives: [`fuzzy_measure_pairing`](ops/measure1d/caliper/fuzzy_measure_pairing.md), [`gen_measure_arc`](ops/measure1d/caliper/gen_measure_arc.md), [`create_metrology_model`](ops/measure1d/model/create_metrology_model.md), [`blob_label`](ops/blob/connect/blob_label.md), [`blob_select`](ops/blob/select/blob_select.md), [`mm_per_px_from_reference`](ops/measure1d/scale/mm_per_px_from_reference.md)

Runnable: `poc_dimensional_inspection`, `poc_screw_thread_metrology`

### [Slope, flow and line of sight on a terrain](capabilities/terrain-and-visibility.md)

From a height grid: slope, aspect, viewshed and flow direction. Each has a closed form to check against, so an implementation error shows up as a number.

Operators: `dem_slope`, `dem_aspect`, `dem_viewshed`, `dem_flow_direction`

Pipeline: [`dem_fill_sinks`](ops/dem/hydrology/dem_fill_sinks.md) → [`dem_slope`](ops/dem/surface/dem_slope.md) → [`dem_aspect`](ops/dem/surface/dem_aspect.md) → [`dem_flow_direction`](ops/dem/hydrology/dem_flow_direction.md) → [`dem_viewshed`](ops/dem/visibility/dem_viewshed.md)

Alternatives: [`dem_hillshade`](ops/dem/shading/dem_hillshade.md), [`dem_flow_accumulation`](ops/dem/hydrology/dem_flow_accumulation.md), [`dem_geodetic_slope`](ops/dem/geodesy/dem_geodetic_slope.md)

Runnable: `poc_dem_terrain`, `dem_terrain_analysis_tour`

### [Turn a 3-D scan into a volume](capabilities/volume-from-3d-scan.md)

Compute a signed volume from a closed mesh, a voxel count from a labelled region, or the material between two surfaces from a height grid. Gaps can be filled by interpolation, and how far that interpolation reached is reported separately.

Operators: `mesh_volume`, `vol_rle_volume`, `interp_scattered`, `dem_slope`

Pipeline: [`vol_rle_components`](ops/3d/rle_region/vol_rle_components.md) → [`vol_rle_volume`](ops/3d/rle_region/vol_rle_volume.md) → [`mesh_volume`](ops/3d/mesh_process/mesh_volume.md)

Alternatives: [`interp_scattered`](ops/math/interp_poly/interp_scattered.md), [`dem_slope`](ops/dem/surface/dem_slope.md), [`dem_fill_sinks`](ops/dem/hydrology/dem_fill_sinks.md), `marching_cubes`

Runnable: `poc_stockpile_volume`, `poc_lidar_terrain_change`

## Detect (5)

### [Segment regions, select them, and count](capabilities/blob-and-region.md)

Label connected components, select them by area, shape or position, and count them. Touching objects can be separated with a watershed.

Operators: `blob_label`, `blob_select`, `blob_count`, `watersheds`

Pipeline: [`auto_threshold`](ops/2d/segmentation/auto_threshold.md) → [`blob_label`](ops/blob/connect/blob_label.md) → [`blob_select`](ops/blob/select/blob_select.md) → [`blob_features`](ops/blob/measure/blob_features.md)

Alternatives: [`watersheds`](ops/2d/segmentation/watersheds.md), [`blob_seeds`](ops/blob/split/blob_seeds.md), [`blob_count`](ops/2d/features/blob_count.md), [`remove_small`](ops/2d/region/remove_small.md), [`select_shape`](ops/2d/region/select_shape.md), [`otsu`](ops/2d/segmentation/otsu.md)

Runnable: `poc_cell_counting`, `poc_particle_sizing`, `poc_real_coin_metrology`

### [OCR pre-processing (deskew, local binarisation, line extraction)](capabilities/ocr-preprocessing.md)

Everything before the recogniser: deskew, local (Sauvola) binarisation, speck removal and merging characters into lines, all from registry operators. Recognition itself is out of scope.

Operators: `sk_sauvola`, `rotate_image`, `remove_small`, `dilation_rectangle1`

Pipeline: [`median`](ops/2d/rank/median.md) → [`rotate_image`](ops/2d/geometry/rotate_image.md) → [`sk_sauvola`](ops/2d/segmentation/sk_sauvola.md) → [`invert_region`](ops/2d/region/invert_region.md) → [`remove_small`](ops/2d/region/remove_small.md) → [`select_shape`](ops/2d/region/select_shape.md) → [`dilation_rectangle1`](ops/2d/region/dilation_rectangle1.md)

Alternatives: [`sk_niblack`](ops/2d/segmentation/sk_niblack.md), [`adaptive_gauss_thresh`](ops/2d/segmentation/adaptive_gauss_thresh.md), [`otsu`](ops/2d/segmentation/otsu.md), [`gray_bothat`](ops/2d/morphology/gray_bothat.md), [`unsharp`](ops/2d/smoothing/unsharp.md), [`zoom_image_factor`](ops/2d/geometry/zoom_image_factor.md), [`affine_trans_image`](ops/2d/geometry/affine_trans_image.md)

Runnable: `gallery2d_segmentation`, `poc_matrix_code_reading`, `gallery2d_region`

### [Find small point-like targets and locate them below the pixel](capabilities/point-target-detection.md)

Pick local maxima above a robustly estimated background plus k sigma, and return sub-pixel centroids. The name is astronomical but the method is domain-neutral: drifting objects, small defects, fluorescent puncta, particles.

Operators: `star_detect`, `peak_subbin`, `find_peaks`, `noise_sigma`

Pipeline: [`noise_sigma`](ops/astrostack/quality/noise_sigma.md) → [`star_detect`](ops/astrostack/photometry/star_detect.md) → [`find_peaks`](ops/oned/signal/find_peaks.md) → [`peak_subbin`](ops/oned/signal/peak_subbin.md)

Alternatives: [`xsk3_peak_local_max`](ops/2d/segmentation/xsk3_peak_local_max.md), [`blob_seeds`](ops/blob/split/blob_seeds.md), [`blob_label`](ops/blob/connect/blob_label.md)

Runnable: `poc_search_sweep_width`, `poc_astro_photometry`

### [Surface relief defects, from lighting design to detection](capabilities/surface-defects-with-lighting.md)

Relief defects (dents, bumps, grinding marks) show as surface slope, not colour. Design the light first (which ring elevation gives the most contrast for that slope), recover normals from several lights (photometric stereo), integrate to height, then segment the defects — one chain.

Operators: `illumination_design`, `lighting_sweep`, `photometric_stereo`, `integrate_normals`, `bothat`

Pipeline: [`illumination_design`](ops/optics/illumination/illumination_design.md) → [`lighting_sweep`](ops/optics/illumination/lighting_sweep.md) → [`light_source`](ops/optics/illumination/light_source.md) → [`defect_contrast`](ops/optics/illumination/defect_contrast.md) → [`irradiance_map`](ops/optics/illumination/irradiance_map.md) → [`illumination_uniformity`](ops/optics/illumination/illumination_uniformity.md) → [`photometric_stereo`](ops/3d/photometric/photometric_stereo.md) → [`integrate_normals`](ops/3d/photometric/integrate_normals.md) → [`surface_form_error`](ops/3d/surface_fit/surface_form_error.md) → [`bothat`](ops/2d/morphology/bothat.md) → [`auto_threshold`](ops/2d/segmentation/auto_threshold.md) → [`remove_small`](ops/2d/region/remove_small.md)

Alternatives: [`photometric_stereo_robust`](ops/specular/photometric/photometric_stereo_robust.md), [`normals_from_depth`](ops/3d/range_image/normals_from_depth.md), [`background_flatten`](ops/3d/surface_fit/background_flatten.md), [`tophat`](ops/2d/morphology/tophat.md), [`laplace_of_gauss`](ops/2d/edges/laplace_of_gauss.md), [`dem_slope`](ops/dem/surface/dem_slope.md)

Runnable: `illumination_design_demo`, `photometric_stereo`, `poc_bump_coplanarity`

### [Locate a part by template matching and move the measurement model with it](capabilities/template-alignment.md)

Find the part with template matching (translation, or rotation in 30° steps), then shift the measurement model by that offset before applying it — so the same feature is measured wherever the part landed.

Operators: `ncc_locate`, `shape_locate`, `align_metrology_model`, `translate_measure`

Pipeline: [`gaussian`](ops/2d/smoothing/gaussian.md) → [`ncc_locate`](ops/2d/matching/ncc_locate.md) → [`shape_locate`](ops/2d/matching/shape_locate.md) → [`create_metrology_model`](ops/measure1d/model/create_metrology_model.md) → [`add_metrology_object_circle_measure`](ops/measure1d/model/add_metrology_object_circle_measure.md) → [`align_metrology_model`](ops/measure1d/apply/align_metrology_model.md) → [`apply_metrology_model`](ops/measure1d/apply/apply_metrology_model.md)

Alternatives: [`edges_sub_pix`](ops/2d/contour/edges_sub_pix.md), [`fit_line_contours`](ops/2d/contour/fit_line_contours.md), [`translate_measure`](ops/measure1d/caliper/translate_measure.md), [`gen_measure_rectangle2`](ops/measure1d/caliper/gen_measure_rectangle2.md), [`rotate_image`](ops/2d/geometry/rotate_image.md), [`affine_trans_image`](ops/2d/geometry/affine_trans_image.md)

Runnable: `poc_template_tracking`, `gallery2d_contour_measure`, `poc_search_sweep_width`

## Shape (2)

### [Reconstruct slices from projections (CT)](capabilities/tomography-reconstruction.md)

Forward parallel-beam projection to a sinogram, filtered back-projection to a slice or a volume, and the injection and correction of ring artefacts and beam hardening. The reconstructed volume can be turned straight into a mesh.

Operators: `radon_transform`, `fbp_volume`, `ring_artifact_remove`, `marching_cubes`

Pipeline: [`radon_transform`](ops/tomography/forward/radon_transform.md) → [`ring_artifact_remove`](ops/tomography/artifact/ring_artifact_remove.md) → [`beam_hardening_correct`](ops/tomography/artifact/beam_hardening_correct.md) → [`fbp_volume`](ops/tomography/volume/fbp_volume.md) → [`vol_rle_components`](ops/3d/rle_region/vol_rle_components.md) → [`vol_rle_volume`](ops/3d/rle_region/vol_rle_volume.md)

Alternatives: `marching_cubes`, [`radon_volume`](ops/tomography/volume/radon_volume.md), [`sinogram_center_of_rotation`](ops/tomography/geometry/sinogram_center_of_rotation.md), [`ring_artifact_apply`](ops/tomography/artifact/ring_artifact_apply.md)

Runnable: `poc_ct_fidelity`, `poc_ct_void_morphology`

### [Carve a solid out of silhouettes (visual hull)](capabilities/visual-hull-from-silhouettes.md)

From the foreground masks of several calibrated cameras, carve out a voxel volume that always contains the object. No learned model, no depth sensor.

Operators: `synthesize_silhouette`, `carve`, `visual_hull`, `carve_look_at`

Pipeline: [`synthesize_silhouette`](ops/3d/space_carving/synthesize_silhouette.md) → [`visual_hull`](ops/3d/space_carving/visual_hull.md) → [`vol_rle_components`](ops/3d/rle_region/vol_rle_components.md) → [`vol_rle_volume`](ops/3d/rle_region/vol_rle_volume.md)

Alternatives: [`carve`](ops/3d/space_carving/carve.md), [`carve_look_at`](ops/3d/space_carving/carve_look_at.md), [`mesh_volume`](ops/3d/mesh_process/mesh_volume.md)

Runnable: `space_carving`, `poc_livestock_body_volume`

## Light and colour (3)

### [Measure colour (XYZ / Lab / colour difference)](capabilities/colour-and-delta-e.md)

From spectral reflectance or RGB, compute CIE XYZ and Lab, then colour differences under CIE76 or CIEDE2000. The difference can also be returned as a per-pixel map.

Operators: `rgb_to_lab`, `xyz_to_lab`, `delta_e_2000`, `cie_xyz_from_wavelength`

Pipeline: [`rgb_to_lab`](ops/imgmetrics/colorspace/rgb_to_lab.md) → [`delta_e_2000`](ops/imgmetrics/colordiff/delta_e_2000.md)

Alternatives: [`rgb_to_xyz`](ops/imgmetrics/colorspace/rgb_to_xyz.md), [`xyz_to_lab`](ops/imgmetrics/colorspace/xyz_to_lab.md), [`delta_e_76`](ops/imgmetrics/colordiff/delta_e_76.md), [`delta_e_map`](ops/imgmetrics/colordiff/delta_e_map.md), [`cie_xyz_from_wavelength`](ops/optics/appearance/cie_xyz_from_wavelength.md), [`srgb_to_linear`](ops/gfx2d/colorspace/srgb_to_linear.md)

Runnable: `poc_white_balance`, `poc_pigment_unmixing`

### [Compute reflection, refraction and interference](capabilities/optics-and-materials.md)

Fresnel reflectance, thin-film interference colour, grating colour, and vector-form refraction with a per-ray total-internal-reflection mask — with the dispersion of real glasses.

Operators: `fresnel_dielectric`, `thin_film_reflectance`, `grating_rgb`, `refract_rays`

Pipeline: [`fresnel_dielectric`](ops/optics/interface/fresnel_dielectric.md) → [`thin_film_reflectance`](ops/optics/appearance/thin_film_reflectance.md) → [`thin_film_rgb`](ops/optics/appearance/thin_film_rgb.md)

Alternatives: [`fresnel_conductor`](ops/optics/interface/fresnel_conductor.md), [`brewster_angle_deg`](ops/optics/interface/brewster_angle_deg.md), [`grating_rgb`](ops/optics/appearance/grating_rgb.md), [`refract_rays`](ops/optics/glassbody/refract_rays.md), [`fresnel_reflectance`](ops/3d/optics/fresnel_reflectance.md)

Runnable: `glass_and_mirror_optics`, `appearance_structural_colour`

### [Remove specular reflection from a four-angle polariser sweep (dielectrics vs metals)](capabilities/polarisation-specular-removal.md)

Fit Malus's law per pixel to a 0/45/90/135° polariser sweep and split the radiance into its unpolarised part (2·I_min) and its linearly polarised part (I_max − I_min). Calling those "diffuse" and "specular" is a physical assumption that holds for dielectrics near Brewster's angle and fails for metals; this entry keeps the two cases apart.

Operators: `polarization_dolp_map`, `polarization_separate`, `polarization_stokes`, `specular_diffuse_split`

Pipeline: [`polarization_dolp_map`](ops/specular/polarization/polarization_dolp_map.md) → [`polarization_separate`](ops/specular/polarization/polarization_separate.md) → [`polarization_stokes`](ops/specular/polarization/polarization_stokes.md) → [`stokes_analyze`](ops/optics/polarization/stokes_analyze.md) → [`specular_diffuse_split`](ops/specular/dichromatic/specular_diffuse_split.md)

Alternatives: [`fresnel_conductor`](ops/optics/interface/fresnel_conductor.md), [`fresnel_dielectric`](ops/optics/interface/fresnel_dielectric.md), [`brewster_angle_deg`](ops/optics/interface/brewster_angle_deg.md), [`specular_free_transform`](ops/specular/dichromatic/specular_free_transform.md), [`specular_coefficient_map`](ops/specular/dichromatic/specular_coefficient_map.md)

Runnable: `example_polarization_metal`, `poc_polarization_specular`, `specular_photometric`

## Waves and signals (3)

### [Beamform for direction, separate range from velocity](capabilities/beamforming-and-range-doppler.md)

Form beams from an array snapshot to get directions of arrival, and build a range-Doppler map from an FMCW return, mapping detections back to metres and metres per second.

Operators: `beamform_delay_sum`, `beamform_doa`, `range_doppler_map`, `range_doppler_peaks`

Pipeline: [`beamform_doa`](ops/rangedoppler/beamform/beamform_doa.md) → [`range_doppler_map`](ops/rangedoppler/process/range_doppler_map.md) → [`range_doppler_peaks`](ops/rangedoppler/process/range_doppler_peaks.md)

Alternatives: [`beamform_delay_sum`](ops/rangedoppler/beamform/beamform_delay_sum.md)

Runnable: `poc_multibeam_bathymetry`, `poc_bev_sensor_fusion`

### [Periodic defects in a 1-D signal](capabilities/periodic-defects-in-1d-signals.md)

Roll-driven periodic marks, rail corrugation, bearing faults: defects that repeat at a fixed interval in a 1-D series. `spectrum` says *whether* there is a period, `peak_subbin` refines *which*, and the extrema of `envelope` say *where*.

Operators: `spectrum`, `find_peaks`, `peak_subbin`, `envelope`, `cepstrum`

Pipeline: [`smooth_funct_1d_gauss`](ops/oned/function/smooth_funct_1d_gauss.md) → [`bandpass`](ops/oned/signal/bandpass.md) → [`spectrum`](ops/oned/signal/spectrum.md) → [`find_peaks`](ops/oned/signal/find_peaks.md) → [`peak_subbin`](ops/oned/signal/peak_subbin.md) → [`envelope`](ops/oned/signal/envelope.md) → [`local_min_max_funct_1d`](ops/oned/function/local_min_max_funct_1d.md)

Alternatives: [`cepstrum`](ops/acoustics/bearing/cepstrum.md), [`envelope_spectrum`](ops/acoustics/bearing/envelope_spectrum.md), [`order_spectrum`](ops/acoustics/order/order_spectrum.md), [`signal_features`](ops/oned/signal/signal_features.md), [`zero_crossings_funct_1d`](ops/oned/function/zero_crossings_funct_1d.md), [`point_spectrum`](ops/oned/signal/point_spectrum.md)

Runnable: `poc_web_roll_periodicity`, `poc_rail_corrugation`, `poc_bearing_diagnosis`

### [Diagnose faults from vibration and sound](capabilities/vibration-and-acoustics.md)

Envelope spectra, cepstra, octave bands and the characteristic frequencies of a rolling-element bearing. The frequencies follow from the geometry, so which peak to look at is decided before measuring, not after.

Operators: `signal_features`, `envelope_spectrum`, `bearing_defect_frequencies`, `octave_spectrum`, `spectrum`

Pipeline: [`bandpass`](ops/oned/signal/bandpass.md) → [`envelope`](ops/oned/signal/envelope.md) → [`envelope_spectrum`](ops/acoustics/bearing/envelope_spectrum.md) → [`find_peaks`](ops/oned/signal/find_peaks.md) → [`bearing_defect_frequencies`](ops/acoustics/bearing/bearing_defect_frequencies.md)

Alternatives: [`signal_features`](ops/oned/signal/signal_features.md), [`octave_spectrum`](ops/acoustics/level/octave_spectrum.md), [`spectrum`](ops/oned/signal/spectrum.md), [`cepstrum`](ops/acoustics/bearing/cepstrum.md), [`order_spectrum`](ops/acoustics/order/order_spectrum.md), [`rms`](ops/oned/signal/rms.md)

Runnable: `poc_bearing_diagnosis`, `poc_rail_corrugation`

## Compose (1)

### [Align and stack](capabilities/align-and-stack.md)

Align a sequence by voting for the translation, resample sub-pixel, and stack. Point clouds are aligned with ICP.

Operators: `frame_align`, `drizzle_resample`, `icp_point2point_3d`, `interp_scattered`

Pipeline: [`align_frames`](ops/astrostack/align/align_frames.md) → [`drizzle_resample`](ops/astrostack/stack/drizzle_resample.md) → [`frame_quality`](ops/astrostack/quality/frame_quality.md)

Alternatives: [`frame_align`](ops/astrostack/align/frame_align.md), [`icp_point2point_3d`](ops/3d/refine/icp_point2point_3d.md), [`register_cross`](ops/3d/fusion/register_cross.md), [`interp_scattered`](ops/math/interp_poly/interp_scattered.md)

Runnable: `poc_astro_photometry`, `poc_registration_basin`

## Show (3)

### [Turn results into figures people can read](capabilities/figures-and-annotation.md)

Panel grids, dimension and pointer annotations, height pseudo-colour, and a full SDF renderer — all from Fullseye operators, so a result becomes a figure without a plotting library in between.

Operators: `annotate_figure_grid`, `colorize_height`, `render_beauty`

Pipeline: [`annotate_figure_grid`](ops/annotate/paper/annotate_figure_grid.md) → [`annotate_panel_label`](ops/annotate/paper/annotate_panel_label.md) → [`annotate_scale_bar`](ops/annotate/paper/annotate_scale_bar.md) → [`annotate_colorbar`](ops/annotate/paper/annotate_colorbar.md)

Alternatives: `colorize_height`, [`render_beauty`](ops/3d/render/render_beauty.md), [`annotate_legend`](ops/annotate/paper/annotate_legend.md), [`annotate_inset`](ops/annotate/paper/annotate_inset.md)

Runnable: `poc_colormap_readability`, `poc_dem_terrain`

### [Draw lines and regions without knowing the background colour](capabilities/inverted-colour-overlays.md)

Draw a polyline or a region in the inverse of whatever is underneath, so the overlay stays visible without knowing the background. `draw="margin"` outlines instead of filling. The one real failure mode — mid-grey, where the complement equals the original — is measured rather than assumed: `annotate_invert_visibility` reports the per-pixel WCAG contrast, and the drawing ops warn (or refuse) when the mark would be invisible.

Operators: `annotate_invert`, `annotate_invert_path`, `annotate_invert_visibility`

Pipeline: [`annotate_invert_visibility`](ops/annotate/overlay/annotate_invert_visibility.md) → [`annotate_invert`](ops/annotate/overlay/annotate_invert.md) → [`annotate_invert_path`](ops/annotate/overlay/annotate_invert_path.md)

Alternatives: [`annotate_legend`](ops/annotate/paper/annotate_legend.md), [`text_box`](ops/annotate/text/text_box.md)

Runnable: `annotate_paper_tour`

### [Put text and tables exactly where you want them on an image](capabilities/text-and-tables-on-images.md)

Place text on an image where you actually want it: nine-way anchors, translucent plates, wrapping, and — along a polyline — slanted, vertical (`upright=True`), multi-line (`\n`), start/centre/end alignment and a perpendicular offset. Colour, plus synthetic bold and italic. `annotate_table` turns a tab-separated string into a table whose column widths are **measured with the real font at the requested size**, with a font-size-proportional column gap, automatic right-alignment for numeric columns and a translucent plate. Every one has a `*_layout` twin that returns the geometry so you can check the placement before drawing.

Operators: `text_box`, `annotate_text_path`, `annotate_text_path_layout`, `annotate_table`, `annotate_table_layout`, `measure_text`

Pipeline: [`measure_text`](ops/annotate/text/measure_text.md) → [`annotate_text_path_layout`](ops/annotate/paper/annotate_text_path_layout.md) → [`annotate_text_path`](ops/annotate/paper/annotate_text_path.md) → [`annotate_table_layout`](ops/annotate/paper/annotate_table_layout.md) → [`annotate_table`](ops/annotate/paper/annotate_table.md)

Alternatives: [`text_box`](ops/annotate/text/text_box.md), [`annotate_panel_label`](ops/annotate/paper/annotate_panel_label.md)

Runnable: `annotate_paper_tour`
