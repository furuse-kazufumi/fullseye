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

**Currently 91 capabilities**

## Look up by task (recommended pipeline)

Every operator exists in the registry and the types connect from one step to the next (`tests/test_capabilities.py` checks both; only four sort names are treated as synonyms: `image2d`=`image`, `mask`=`region`, `measurement`=`feature`=`scalar`). Values passed as arguments are outside the type chain. Alternatives, limits and calibration are in each entry.

| Task | Recommended pipeline (in order) | Runnable |
|---|---|---|
| [Align and stack](capabilities/align-and-stack.md) | `align_frames` → `drizzle_resample` → `frame_quality` | `poc_astro_photometry` |
| [Beamform for direction, separate range from velocity](capabilities/beamforming-and-range-doppler.md) | `beamform_doa` → `range_doppler_map` → `range_doppler_peaks` | `poc_multibeam_bathymetry` |
| [Segment regions, select them, and count](capabilities/blob-and-region.md) | `auto_threshold` → `blob_label` → `blob_select` → `blob_features` | `poc_cell_counting` |
| [Chromatic confocal displacement sensor (glass dispersion, calibration table, return spectrum, height and thickness)](capabilities/chromatic-confocal-sensor.md) | `chromatic_confocal_probe` → `chromatic_confocal_spectrum` → `chromatic_confocal_peaks` → `chromatic_confocal_readout` | `poc_chromatic_confocal` |
| [Measure colour (XYZ / Lab / colour difference)](capabilities/colour-and-delta-e.md) | `rgb_to_lab` → `delta_e_2000` | `poc_white_balance` |
| [Run inter-reflections, multiple scattering and iterations to convergence — return the evidence and the remaining error, and no value when it did not converge](capabilities/convergent-forward-models.md) | `iterate_fixed_point` → `conv_gci` | `converge_tour` |
| [Separating crop from weeds in field RGB by colour and texture, and grading weed cover at declared edges (no learned network)](capabilities/crop-weed-cover-grade.md) | `superpixel_color_texture_features` → `fisher_lda_fit` → `fisher_lda_score` → `cover_ratio_grade` | `poc_weed_rice_ratio` |
| [Separate thickness from material with two X-ray energies (dual-energy and photon-counting X-ray: spectrum, energy windows, basis decomposition, effective Z)](capabilities/dual-energy-xray-material-discrimination.md) | `xray_tube_spectrum` → `photon_counting_channels` → `basis_decomposition_crlb` → `basis_material_decompose` → `effective_z_map` | `poc_dual_energy_xray` |
| [Turn results into figures people can read](capabilities/figures-and-annotation.md) | `annotate_figure_grid` → `annotate_panel_label` → `annotate_scale_bar` → `annotate_colorbar` | `poc_colormap_readability` |
| [Put measurements on the Earth (ECEF, height frames, local ENU)](capabilities/geodetic-frames.md) | `dem_geodetic_to_ecef` → `dem_ecef_to_geodetic` | `poc_geodetic_height_frames` |
| [Flag what differs from aligned good samples (a per-pixel variation model with a declared false-alarm rate)](capabilities/good-sample-variation-model.md) | `varmodel_alignment` → `varmodel_fit` → `varmodel_calibrate` → `varmodel_score` | `poc_good_sample_variation_model` |
| [Grating interferometry (Talbot / Talbot-Lau): transmission, differential phase and dark field from one phase-stepping scan](capabilities/grating-interferometry.md) | `talbot_grating_design` → `talbot_source_visibility` → `grating_step_period_estimate` → `grating_three_image_retrieve` → `darkfield_scatter_relation` → `dpc_integrate` | `poc_grating_interferometry` |
| [Grating spectrometer and microscope illumination (bandwidth, smile and keystone, Koehler and critical illumination, coaxial half mirror)](capabilities/grating-spectrometer-and-illumination.md) | `czerny_turner_design` → `spectrometer_bandpass` → `spectrometer_spectrum` | `poc_spectrometer_illumination` |
| [Illumination cone versus imaging NA on specular parts (cap intersection, slope bands, dents, scratches and satin)](capabilities/illumination-cone-vs-na.md) | `solid_angle_light` → `solid_angle_boundaries` → `solid_angle_sweep` → `solid_angle_brightness` → `solid_angle_render` | `poc_illumination_cone_vs_na` |
| [Industrial OCT (spectral interferogram, k-linearisation, dispersion compensation, A/B-scans, layer thickness via the group index)](capabilities/industrial-oct.md) | `oct_design` → `oct_from_spectra` → `oct_bscan` → `oct_bscan_boundaries` → `oct_bscan_flatten` → `oct_layer_thickness` | `poc_industrial_oct` |
| [Inner diameter of a round part, all the way to millimetres](capabilities/inner-diameter-in-mm.md) | `gaussian` → `otsu` → `area_center` → `create_metrology_model` → `add_metrology_object_circle_measure` → `apply_metrology_model` → `mm_per_px_from_reference` → `pixel_to_world` | `example_inner_diameter_mm` |
| [Count interreflection in concave parts to convergence without losing the photometric truth (3-D view factors, progressive radiosity, an inspection render with bounces)](capabilities/interreflection-to-convergence.md) | `radiosity_patches` → `form_factor_matrix` | `poc_pocket_interreflection` |
| [Draw lines and regions without knowing the background colour](capabilities/inverted-colour-overlays.md) | `annotate_invert_visibility` → `annotate_invert` → `annotate_invert_path` | `annotate_paper_tour` |
| [Indirect time-of-flight (phase-based): multi-frequency unwrapping and how it breaks (wrapping, multipath, flying pixels, harmonics, ambient light)](capabilities/itof-multifreq.md) | `itof_noise_budget` → `itof_capture` → `itof_phase_amplitude` → `itof_unwrap_multifreq` | `poc_itof_multifreq` |
| [Lens design files (read, write and triage sequential .zmx prescriptions)](capabilities/lens-prescription-files.md) | `lens_file_read` → `lens_file_system` → `paraxial_trace` → `spot_stats` → `lens_file_write` | `poc_lens_file_roundtrip` |
| [Per-pixel lock-in demodulation (time-correlation imaging: amplitude, phase and DC; ring-light normals, coded-light separation, thermal waves)](capabilities/lockin-demodulation.md) | `lockin_ring_synthesize` → `lockin_demodulate` → `lockin_ring_normals` | `poc_lockin_imaging` |
| [Moiré alignment (two gratings of slightly different pitch, fringe phase, nanometre shift, differential pairs and the Talbot gap)](capabilities/moire-alignment.md) | `moire_magnification` → `moire_mark_read` → `moire_phase_crlb` | `poc_moire_alignment` |
| [Sorting look-alike foreign matter with NIR hyperspectral imaging (material absorption bands, scattering-layer reflectance, InGaAs band electrons)](capabilities/nir-hyperspectral-sorting.md) | `material_nir_absorption` → `kubelka_munk_reflectance` → `hyperspectral_capture` | `poc_hyperspectral_foreign_matter` |
| [Non-coaxial optics (fold mirrors, beamsplitters, tilted plates, Scheimpflug and ghosts)](capabilities/noncoaxial-optics.md) | `noncoaxial_system` → `noncoaxial_trace` → `image_orientation` → `ghost_analysis` → `noncoaxial_drawing` | `poc_noncoaxial_optics` |
| [OCR pre-processing (deskew, local binarisation, line extraction)](capabilities/ocr-preprocessing.md) | `median` → `rotate_image` → `sk_sauvola` → `invert_region` → `remove_small` → `select_shape` → `dilation_rectangle1` | `gallery2d_segmentation` |
| [Compute reflection, refraction and interference](capabilities/optics-and-materials.md) | `fresnel_dielectric` → `thin_film_reflectance` → `thin_film_rgb` | `glass_and_mirror_optics` |
| [Optical drawings (lens layouts, vision-setup drawings and ISO 10110 element drawings as SVG / DXF)](capabilities/optics-drawings.md) | `lens_section_drawing` → `drawing_svg` → `drawing_dxf` → `svg_entities` → `dxf_entities` | `poc_optics_drawings` |
| [Flag patches that leave what good samples look like (classical features, a normal distribution per position or a memory bank, and a recall-guaranteeing operating point)](capabilities/patch-feature-anomaly-detection.md) | `patchbank_fit` → `patchbank_score` | `poc_patch_anomaly` |
| [Periodic defects in a 1-D signal](capabilities/periodic-defects-in-1d-signals.md) | `smooth_funct_1d_gauss` → `bandpass` → `spectrum` → `find_peaks` → `peak_subbin` → `envelope` → `local_min_max_funct_1d` | `poc_web_roll_periodicity` |
| [Find micrometre dents on glossy surfaces from the mirror image of a fringe screen (phase-measuring deflectometry)](capabilities/phase-measuring-deflectometry.md) | `deflectometry_rig` → `deflectometry_sensitivity` → `wrapped_phase` → `absolute_phase` → `deflectometry_phase_to_slope` → `slope_to_curvature` | `poc_phase_measuring_deflectometry` |
| [Photographing a 3-D scene through the actual lens prescription (depth of field, cat's-eye bokeh, corner illumination, colour fringes, ghosts)](capabilities/photograph-through-prescription.md) | `lens_system` → `lens_scene` → `render_scene_through_lens` → `render_compare_prescriptions` | `poc_photograph_through_prescription` |
| [Pixel-shift imaging (full colour from 1-pixel shifts, no aliasing from half-pixel shifts, and where it breaks)](capabilities/pixel-shift-imaging.md) | `pixel_shift_resolution_budget` → `pixel_shift_pattern` → `pixel_shift_capture` → `pixel_shift_motion_mask` → `pixel_shift_merge` → `false_color_metric` | `poc_pixel_shift` |
| [Flatness of a surface from a 3-D point cloud](capabilities/planarity-from-point-cloud.md) | `statistical_outlier_removal` → `ransac_plane` → `fit_plane_3d` → `distance_point_plane` | `geometry_metrology` |
| [Draw a point cloud as a colour picture](capabilities/point-cloud-to-picture.md) | `points_render` | `points_render_basics` |
| [Find small point-like targets and locate them below the pixel](capabilities/point-target-detection.md) | `noise_sigma` → `star_detect` → `find_peaks` → `peak_subbin` | `poc_search_sweep_width` |
| [Remove specular reflection from a four-angle polariser sweep (dielectrics vs metals)](capabilities/polarisation-specular-removal.md) | `polarization_dolp_map` → `polarization_separate` → `polarization_stokes` → `stokes_analyze` → `specular_diffuse_split` | `example_polarization_metal` |
| [Template matching that survives uneven light, highlights and occlusion (compare the direction of brightness change as codes, and refuse templates that cannot fix a position)](capabilities/robust-code-matching.md) | `isc_match` → `ocm_match` | `poc_code_matching_breakdown` |
| [A mean line that deep scratches and spikes cannot drag (robust Gaussian-regression and spline filters, for profiles and surfaces)](capabilities/robust-gaussian-spline-profile-filter.md) | `robust_gaussian_profile` → `profile_params` | `poc_robust_profile_filter` |
| [Detect fine scratches and measure their width](capabilities/scratch-detection-and-width.md) | `gaussian` → `lines_gauss` → `select_contours` → `fit_line_contours` → `gen_measure_rectangle2` → `measure_pairs` → `table_px_to_mm` | `example_scratch_width` |
| [Measure the same particles in scanning and transmission images and compare both size biases](capabilities/sem-tem-same-particle.md) | `sem_render` → `tem_power_spectrum` | `poc_sem_tem_same_particle` |
| [Sequential lens-design metrics (ideal lens surface, encircled energy, tangential / sagittal MTF, through-focus MTF)](capabilities/sequential-lens-design-metrics.md) | `lens_system` → `psf_from_opd` → `encircled_energy` → `energy_radii` → `mtf_tangential_sagittal` → `through_focus_mtf` | `optical_design_metrics` |
| [Fit a physical model's coefficients to real images (sim-to-real calibration) — no number for a coefficient the images do not determine, the determined combination and the reason instead](capabilities/sim-to-real-calibration.md) | `simcal_model` → `simcal_observe` → `simcal_fit` → `simcal_identifiability` → `simcal_report` | `simcal_tour` |
| [Measure dimensions from an image, below the pixel](capabilities/subpixel-2d-metrology.md) | `gen_measure_rectangle2` → `measure_pos` → `measure_pairs` → `table_px_to_mm` | `poc_dimensional_inspection` |
| [Surface relief defects, from lighting design to detection](capabilities/surface-defects-with-lighting.md) | `illumination_design` → `lighting_sweep` → `light_source` → `defect_contrast` → `irradiance_map` → `illumination_uniformity` → `photometric_stereo` → `integrate_normals` → `surface_form_error` → `bothat` → `auto_threshold` → `remove_small` | `illumination_design_demo` |
| [TDI line-scan cameras and line-scan lenses (stages and SNR, synchronisation MTF, illumination and MTF across the image height)](capabilities/tdi-linescan-and-lens.md) | `tdi_snr` → `tdi_sync_mtf` → `linescan_lens_example` → `lens_field_profile` → `linescan_lens_columns` → `linescan_acquire` | `poc_tdi_linescan` |
| [Telecentric lenses for dimensional metrology (chief-ray angle, magnification versus height, vignetting and blur)](capabilities/telecentric-metrology.md) | `telecentric_lens` → `chief_ray_angle` → `telecentricity_error` → `magnification_vs_depth` → `defocus_spot_vs_depth` → `vignetting_vs_field` | `poc_telecentric_metrology` |
| [A virtual transmission electron microscope (electron wavelength, CTF, phase-contrast images, defocus from Thon rings, correction)](capabilities/tem-phase-contrast-and-ctf.md) | `tem_power_spectrum` → `tem_ctf_estimate` → `tem_ctf_correct` | `poc_tem_ctf_thon_rings` |
| [Locate a part by template matching and move the measurement model with it](capabilities/template-alignment.md) | `gaussian` → `ncc_locate` → `shape_locate` → `create_metrology_model` → `add_metrology_object_circle_measure` → `align_metrology_model` → `apply_metrology_model` | `poc_template_tracking` |
| [Slope, flow and line of sight on a terrain](capabilities/terrain-and-visibility.md) | `dem_fill_sinks` → `dem_slope` → `dem_aspect` → `dem_flow_direction` → `dem_viewshed` | `poc_dem_terrain` |
| [Put text and tables exactly where you want them on an image](capabilities/text-and-tables-on-images.md) | `measure_text` → `annotate_text_path_layout` → `annotate_text_path` → `annotate_table_layout` → `annotate_table` | `annotate_paper_tour` |
| [Thin-film thickness by spectral reflectometry (transfer matrix, interference colour, FFT, model fit, thickness maps)](capabilities/thin-film-reflectometry.md) | `multilayer_reflectance` → `film_thickness_fft` → `film_thickness_fit` → `film_thickness_map` | `poc_thin_film_reflectometry` |
| [Reconstruct slices from projections (CT)](capabilities/tomography-reconstruction.md) | `radon_transform` → `ring_artifact_remove` → `beam_hardening_correct` → `fbp_volume` → `vol_rle_components` → `vol_rle_volume` | `poc_ct_fidelity` |
| [Diagnose faults from vibration and sound](capabilities/vibration-and-acoustics.md) | `bandpass` → `envelope` → `envelope_spectrum` → `find_peaks` → `bearing_defect_frequencies` | `poc_bearing_diagnosis` |
| [A virtual SEM — solve the electron-solid interaction by Monte Carlo and see, scored against measured data, how voltage, detector and charging change the image and the measured line width](capabilities/virtual-sem-monte-carlo.md) | `material_electron_properties` → `sem_electron_mc` → `sem_line_profile` → `sem_cd_measure` → `sem_image` | `poc_virtual_sem_kv_cd_bse` |
| [Carve a solid out of silhouettes (visual hull)](capabilities/visual-hull-from-silhouettes.md) | `synthesize_silhouette` → `visual_hull` → `vol_rle_components` → `vol_rle_volume` | `space_carving` |
| [Turn a 3-D scan into a volume](capabilities/volume-from-3d-scan.md) | `vol_rle_components` → `vol_rle_volume` → `mesh_volume` | `poc_stockpile_volume` |
| [How water looks in inspection images (caustics on a pool floor, a bottle seen from the side with its fill line, a wet surface, a hull seen through water)](capabilities/water-inspection-images.md) | `caustic_irradiance` → `caustic_floor_segmentation` | `poc_water_inspection_images` |
| [Water and transparent media (ocean waves, Fresnel and refraction at the surface, colour and scattering under water, a bottle as a lens)](capabilities/water-transparent-media.md) | `ocean_height_field` → `refracted_view` → `water_attenuation` → `underwater_image` | `poc_water_transparent_media` |

33 entries do not have the recipe fields (pipeline / alternatives / limits / calibration) yet — see each entry below; they are named in `gen_capabilities_index.NO_RECIPE_YET`.

## Measure (32)

### [Estimate the camera intrinsic matrix K from multiple planar views (Zhang)](capabilities/camera-intrinsics-calibration.md)

`camera_calibration(object_points, image_points_list)` estimates the intrinsic matrix `K` (fx, fy, cx, cy, skew) from several views of a planar target seen at different tilts, by Zhang's method (two constraints per view collected from the plane homographies). `object_points` are `(x, y)` on the plane; `image_points_list` are the `(row, col)` correspondences per view. It returns `K` plus the per-view homographies, per-view reprojection RMS, and `orientation_rank_ratio` — how strongly the view orientations constrain `K`. The recovered `K` feeds `estimate_distortion`, `undistort_image`, PnP and triangulation. Two honest caveats it carries: the plane must be **tilted** between views or the intrinsics are unconstrained (a degeneracy the code detects and refuses), and **reprojection error does not reveal a bad view geometry** — focal length and target distance trade off almost invisibly in the image (the `poc_camera_calibration` example quantifies this). fail-closed on fewer than three views, mismatched point counts, degenerate orientation, or a non-finite / non-positive `K`.

Operators: `camera_calibration`, `estimate_distortion`, `intrinsic_matrix`, `decompose_intrinsics`

Runnable: `camera_intrinsics_calibration`

### [Seeing the complex plane as an area (domain colouring, basins, escape time, flow)](capabilities/complex-plane-fields.md)

Draw complex analysis as an area rather than a curve: the value field of a rational function, its domain colouring, Newton's basins, escape time, and potential flow past a Joukowski aerofoil. None of the pictures is judged by eye. The winding of the field is counted by this family's existing `cplx_winding_number` (+3, +1, -2 as the zeros and poles say); the hue winding in the *rendered image* recovers the order of a zero from pixels alone; Cayley's 1879 theorem gives the degree-2 basins in closed form and all 262,144 pixels agree; the main cardioid and period-2 bulb prove interiority without iterating (zero counterexamples, and honestly only 90.1 % of what actually stays); the flow field is holomorphic so `cplx_cr_residual` reads 2.06e-04; and the lift exceeds thin-aerofoil theory by exactly the thickness ratio a/b.

Operators: `cplx_plane_grid`, `cplx_rational_field`, `cplx_domain_colour`, `cplx_newton_basins`, `cplx_escape_time`, `mandelbrot_interior`, `potential_flow_joukowski`, `joukowski_circulation`

Runnable: `poc_complex_plane_fields`

### [The distance at which a periodic pattern aliases on a sampling lattice, and the time-to-contact that stripes corrupt — in closed form (compound eyes and inspection cameras)](capabilities/compound-eye-aliasing-and-ttc.md)

`sampling_alias_distance` gives the closed-form distance beyond which a period P aliases on a lattice of pitch Δφ (P cos²θ/(√3 Δφ) for hexagonal, 2Δφ for square) and the contrast left at Nyquist — the working-distance rule of an inspection camera once Δφ is read as the pixel IFOV. `fly_view_plane_texture` integrates a periodic frontal surface analytically under the hexagonal ommatidial lattice and a Gaussian acceptance function (no resampling); fed to the HR correlator it shows where the sign flips. `fly_expansion_readout` reads τ from the flow over the whole eye and shows the aperture effect of vertical stripes returns exactly 2τ. `traj_tau_dot` gives distance, closing speed, τ and τ̇ along a measured 3-D trajectory. `fly_vogel_lattice` and `lattice_moire_peak` compare a Fibonacci (Vogel-spiral) eye with the hexagonal one at the same count and mean spacing: sharp moire versus diffuse noise, best sub-Nyquist resolution for the hexagon, and false flow set by pair spacing rather than by lattice regularity.

Operators: `sampling_alias_distance`, `fly_view_plane_texture`, `fly_expansion_readout`, `fly_vogel_lattice`, `lattice_moire_peak`, `traj_tau_dot`, `fly_t4t5_field`, `fly_tau_from_expansion`

Runnable: `poc_zebra_stripes_fly_eye`

### [Re-measure a camera's datasheet numbers with the EMVA 1288 procedure, and see how much in-camera processing moves them (Linear and General)](capabilities/emva1288-camera-datasheets.md)

The EMVA 1288 Release 4.0 procedure behind camera datasheet numbers, as operators: the Linear model (photon transfer, responsivity, dark noise, dark current, column/row/pixel nonuniformity, defect-pixel histograms, the section 8.1 highpass filter, the section 8.6 spectrograms, total SNR, the inverse SNR, photon counts and the equation 51 linearity check) and the General model for non-linear cameras (a cubic B-spline of the characteristic curve whose slope refers output noise back to the input, giving input SNR, sensitivity threshold, dynamic range, dark noise in photons, DSNU / PRNU and relative quantum efficiency, while reporting η and K as not measurable). Closed forms predict how linear in-camera processing (digital gain, denoising, sharpening, recursive temporal filtering) moves the Linear numbers, and a whiteness check tests assumption 3 directly; the check is this library's, not a number defined by the standard.

Operators: `emva_pair_statistics`, `emva_photon_transfer`, `emva_quantum_efficiency`, `emva_spatial_nonuniformity`, `emva_highpass`, `emva_spectrogram`, `emva_ptc_linearity_check`, `emva_bspline_regression`, `emva_noise_whiteness`, `emva_filter_distortion`, `emva_general_sensitivity`, `emva_general_nonuniformity`, `emva_general_relative_qe`

Runnable: `poc_emva1288_sensor`, `poc_emva1288_in_camera_processing`

### [Estimate lens distortion coefficients from straight lines (plumb-line, no board)](capabilities/estimate-lens-distortion.md)

The upstream of `undistort_image`: it *measures* the Brown–Conrady coefficients instead of taking them as given. From point lists sampled along features that are straight in the world (`lines`, each `(N_i, 2)` in `(x=col, y=row)`) plus the intrinsics `K`, `estimate_distortion` returns `dist = [k1, k2, p1, p2, k3]` ready for `undistort_image` / `undistort_points`. It is the plumb-line method (Brown 1971; Devernay–Faugeras 2001): minimize, over the coefficients, the summed perpendicular scatter of the *undistorted* lines, so lines that are straight in the world become straight once distortion is removed. No correspondences, no calibration board, no known spacing — only that each line is straight (the line-pattern idea Discorpy uses). The principal point of `K` is the distortion centre and is held fixed (the method cannot separate it from `p1, p2`). `radial` in `{1, 2, 3}` frees `k1`; `k1, k2`; or `k1, k2, k3`; `tangential` frees `p1, p2`. On clean synthetic lines the coefficients come back to machine precision; with pixel noise they degrade gracefully. Requires SciPy. fail-closed on fewer than two lines or a line with fewer than three points.

Operators: `estimate_distortion`, `undistort_image`, `distort_points`, `undistort_points`

Runnable: `estimate_lens_distortion`

### [Put measurements on the Earth (ECEF, height frames, local ENU)](capabilities/geodetic-frames.md)

Convert geodetic coordinates to Earth-centred Cartesian (ECEF), to a local ENU frame, and between datums; convert between the two kinds of height (ellipsoidal h from GNSS and orthometric H used by maps) through a published geoid grid, and measure the residual `h - H - N` that exposes a height-frame mix-up. Checked against 523 published NGS survey marks: ECEF agrees with the published Cartesian coordinates to 0.5 mm rms, bilinear interpolation of a 0.25-degree GEOID18 grid lands within 11.1 cm rms of the published point values, and using h as if it were H shifts the answer by 16.75 m (median) in that region.

Operators: `dem_geodetic_to_ecef`, `dem_ecef_to_geodetic`, `dem_geoid_height`, `dem_height_frame_convert`, `dem_height_frame_residual`, `dem_datum_shift_3param`, `dem_enu_from_geodetic`, `dem_geodetic_from_enu`

Pipeline: [`dem_geodetic_to_ecef`](ops/dem/geodesy/dem_geodetic_to_ecef.md) → [`dem_ecef_to_geodetic`](ops/dem/geodesy/dem_ecef_to_geodetic.md)

Alternatives: [`dem_geoid_height`](ops/dem/geodesy/dem_geoid_height.md), [`dem_height_frame_convert`](ops/dem/geodesy/dem_height_frame_convert.md), [`dem_height_frame_residual`](ops/dem/geodesy/dem_height_frame_residual.md), [`dem_enu_from_geodetic`](ops/dem/geodesy/dem_enu_from_geodetic.md), [`dem_geodetic_from_enu`](ops/dem/geodesy/dem_geodetic_from_enu.md), [`dem_datum_shift_3param`](ops/dem/geodesy/dem_datum_shift_3param.md), [`dem_geodetic_slope`](ops/dem/geodesy/dem_geodetic_slope.md)

Runnable: `poc_geodetic_height_frames`, `poc_geodetic_benchmarks_real`, `dem_geodesy_tour`

### [Grating interferometry (Talbot / Talbot-Lau): transmission, differential phase and dark field from one phase-stepping scan](capabilities/grating-interferometry.md)

Eight ops in `gratinginterf` for grating-based phase-contrast and dark-field imaging: closed-form geometry (fractional Talbot distances for π, π/2 and absorption gratings, cone-beam distance and analyser period, the Lau source-grating period), the Talbot carpet behind a binary grating as a sum over diffraction orders, the visibility loss from source size and source gratings, a forward model of phase-stepping stacks with Poisson noise, estimation of the number of steps per period from the sine-fit residual, retrieval of transmission, differential phase and dark field from sample and reference stacks, conversion of dark field to a Gaussian scattering width, and integration of the differential phase into the wavefront phase and projected thickness (refusing wrapped input). The PoC finds a 2 µm crack in a short-fibre composite plate in the dark field (CNR 13.5 against 1.34 in absorption), recovers fibre orientation from four grating directions, and separates the three images of a public CC BY 4.0 Talbot-Lau dataset.

Operators: `talbot_grating_design`, `talbot_carpet`, `talbot_source_visibility`, `grating_stepping_simulate`, `grating_step_period_estimate`, `grating_three_image_retrieve`, `darkfield_scatter_relation`, `dpc_integrate`

Pipeline: [`talbot_grating_design`](ops/optics/grating_interf/talbot_grating_design.md) → [`talbot_source_visibility`](ops/optics/grating_interf/talbot_source_visibility.md) → [`grating_step_period_estimate`](ops/optics/grating_interf/grating_step_period_estimate.md) → [`grating_three_image_retrieve`](ops/optics/grating_interf/grating_three_image_retrieve.md) → [`darkfield_scatter_relation`](ops/optics/grating_interf/darkfield_scatter_relation.md) → [`dpc_integrate`](ops/optics/grating_interf/dpc_integrate.md)

Alternatives: [`talbot_carpet`](ops/optics/grating_interf/talbot_carpet.md), [`grating_stepping_simulate`](ops/optics/grating_interf/grating_stepping_simulate.md), [`wrapped_phase`](ops/3d/structured_light/wrapped_phase.md), [`moire_talbot_gap`](ops/optics/moire_align/moire_talbot_gap.md), [`angular_spectrum_propagate`](ops/optics/wave/angular_spectrum_propagate.md)

Runnable: `poc_grating_interferometry`

### [Industrial OCT (spectral interferogram, k-linearisation, dispersion compensation, A/B-scans, layer thickness via the group index)](capabilities/industrial-oct.md)

Thirteen ops in `octscan` for optical coherence tomography of coatings, conformal coats, adhesive layers and multilayer films: closed-form design numbers before measuring (axial resolution, depth range, sensitivity roll-off, shot-noise-limited SNR, lateral resolution and depth of focus), a simulator of spectral interferograms from a layer stack whose indices and dispersion come from the material table (field sum, so cross-correlation, autocorrelation and DC terms are all present; spectrometer or swept source), k-linearisation, numerical dispersion compensation with closed-form or estimated coefficients, A-scans with windowing, DC removal and full-range quadrature, B-scans, and measurement: interface peaks to optical and physical thickness through the group index (refusing layers that cannot be separated or seen), dynamic-programming boundary tracing on cross-section images, surface flattening, and an entry point for raw spectra from instruments and public data. The PoC processes public raw spectra of automotive paint panels (CC BY 4.0) and compares the layer thicknesses with the paper's ultrasonic and microscope values.

Operators: `oct_design`, `oct_dispersion_broadening`, `oct_interferogram`, `oct_bscan_simulate`, `oct_from_spectra`, `oct_k_linearize`, `oct_dispersion_estimate`, `oct_dispersion_compensate`, `oct_ascan`, `oct_bscan`, `oct_layer_thickness`, `oct_bscan_boundaries`, `oct_bscan_flatten`

Pipeline: [`oct_design`](ops/optics/oct/oct_design.md) → [`oct_from_spectra`](ops/optics/oct/oct_from_spectra.md) → [`oct_bscan`](ops/optics/oct/oct_bscan.md) → [`oct_bscan_boundaries`](ops/optics/oct/oct_bscan_boundaries.md) → [`oct_bscan_flatten`](ops/optics/oct/oct_bscan_flatten.md) → [`oct_layer_thickness`](ops/optics/oct/oct_layer_thickness.md)

Alternatives: [`oct_interferogram`](ops/optics/oct/oct_interferogram.md), [`oct_bscan_simulate`](ops/optics/oct/oct_bscan_simulate.md), [`oct_ascan`](ops/optics/oct/oct_ascan.md), [`oct_dispersion_estimate`](ops/optics/oct/oct_dispersion_estimate.md), [`material_group_index`](ops/optics/fiber/material_group_index.md), [`csi_design`](ops/interferometry/design/csi_design.md)

Runnable: `poc_industrial_oct`

### [Inner diameter of a round part, all the way to millimetres](capabilities/inner-diameter-in-mm.md)

Bore, ring and pin diameters end to end: a coarse centre, a sub-pixel circle fit on radial measurement lines, a calibration from a reference of known size, and the result in millimetres. The last two steps exist as typed operators because an assistant working from the notes alone stopped at pixels.

Operators: `add_metrology_object_circle_measure`, `apply_metrology_model`, `mm_per_px_from_reference`, `pixel_to_world`

Pipeline: [`gaussian`](ops/2d/smoothing/gaussian.md) → [`otsu`](ops/2d/segmentation/otsu.md) → [`area_center`](ops/2d/features/area_center.md) → [`create_metrology_model`](ops/measure1d/model/create_metrology_model.md) → [`add_metrology_object_circle_measure`](ops/measure1d/model/add_metrology_object_circle_measure.md) → [`apply_metrology_model`](ops/measure1d/apply/apply_metrology_model.md) → [`mm_per_px_from_reference`](ops/measure1d/scale/mm_per_px_from_reference.md) → [`pixel_to_world`](ops/measure1d/scale/pixel_to_world.md)

Alternatives: [`gen_measure_arc`](ops/measure1d/caliper/gen_measure_arc.md), [`measure_pos`](ops/measure1d/caliper/measure_pos.md), [`hx_fit_circle_contour`](ops/2d/halcon_ext/hx_fit_circle_contour.md), [`cv_hough_circles`](ops/2d/features/cv_hough_circles.md), [`hough_circle_trans`](ops/2d/features/hough_circle_trans.md), [`table_px_to_mm`](ops/measure1d/scale/table_px_to_mm.md)

Runnable: `example_inner_diameter_mm`, `poc_dimensional_inspection`, `poc_real_coin_metrology`

### [Indirect time-of-flight (phase-based): multi-frequency unwrapping and how it breaks (wrapping, multipath, flying pixels, harmonics, ambient light)](capabilities/itof-multifreq.md)

Eight ops in `itof` (category `itof` of `opsoptics`) take continuous-wave indirect time of flight from raw phase-step buckets to depth and into its failure modes: a capture model with shot and read noise, sine or square modulation, extra light paths and pixel-aperture mixing; K-step phase, amplitude and offset with a per-pixel noise estimate; the closed-form depth noise; multi-frequency unwrapping by exhaustive maximum-likelihood hypotheses, by `residue.residue_crt` or by the two-frequency beat, plus an upper bound on the wrong-order probability; two-path separation from equally spaced frequencies (matrix pencil); a flying-pixel mask; and correction of the square-wave cyclic error. The PoC scores noise, unwrapping, aliasing beyond the unambiguous range, a translucent film over a box, a room corner (matching `lighttransport`), flying pixels, the cyclic error and sunlight against closed forms and existing ops, compares the same scene with direct ToF from `photoncount`, and, when the public raw multi-frequency data (CC BY 4.0) is present, checks the unwrapping against its ground truth.

Operators: `itof_capture`, `itof_phase_amplitude`, `itof_noise_budget`, `itof_unwrap_multifreq`, `itof_unwrap_error_rate`, `itof_multipath_separate`, `itof_flying_pixel_mask`, `itof_wiggling_correct`

Pipeline: [`itof_noise_budget`](ops/optics/itof/itof_noise_budget.md) → [`itof_capture`](ops/optics/itof/itof_capture.md) → [`itof_phase_amplitude`](ops/optics/itof/itof_phase_amplitude.md) → [`itof_unwrap_multifreq`](ops/optics/itof/itof_unwrap_multifreq.md)

Alternatives: [`dtof_cube_simulate`](ops/photon/dtof/dtof_cube_simulate.md), [`dtof_cube_depth`](ops/photon/dtof/dtof_cube_depth.md), [`tof_transport_depth`](ops/optics/light_transport/tof_transport_depth.md), [`residue_crt`](ops/residue/robust/residue_crt.md)

Runnable: `poc_itof_multifreq`

### [Speckle sets the error floor of laser sheet-of-light (coherent imaging, speckle statistics and triangulation uncertainty)](capabilities/laser-speckle-floor.md)

Coherent imaging of rough surfaces under laser light: an amplitude/phase object through the coherent transfer function (verified against Bessel closed forms to 1e-12), laser speckle from a random phase screen with finite roughness, polarisation and pattern diversity and pixel integration, speckle statistics (contrast, Kolmogorov–Smirnov against the exponential and gamma laws, autocorrelation width compared with the Airy pattern), a speckled sheet-of-light laser line, and the speckle-limited height uncertainty of triangulation, δz = C·λ/(2π sin u sin θ). The exponents (+1 in wavelength, −1 in the observation aperture and the triangulation angle) are gated against centroids measured on rendered lines; the constant is disclosed (measured / formula = 0.84–0.91), because the primary paper's text was not available to check its 2π factor. Static speckle does not average away over frames; a moving part does, as 1/√N.

Operators: `coherent_image`, `speckle_field`, `speckle_statistics`, `laser_line_coherent`, `triangulation_speckle_limit`, `speckle_reduction`

Runnable: `poc_laser_line_speckle_floor`

### [Predict how far interreflection in concave parts throws fringe projection and ToF off, before measuring (global light transport, direct/global separation, micro phase shifting)](capabilities/light-transport.md)

Global light transport for concave Lambertian parts and its effect on active 3-D: an explicit light-transport matrix for an extruded concave cross-section (Hottel's crossed-strings form factors, checked against the V-groove closed form 1 − sin(θ/2) and against quadrature of the 2-D kernel to 1e-14; radiosity T = (I − diag(ρ)F)^-1 diag(ρ), or its Neumann partial sum by bounce count); shifted high-frequency patterns and the Nayar et al. (2006) L_max / L_min separation into direct and global images (general fill α, black level b, pattern-plus-complement); the fringe phase as the argument of the direct-plus-global phasor sum, predicted per pixel from the transport matrix and matching the phase decoded from rendered fringes by `fringe.wrapped_phase` to 1e-15 rad; a micro phase-shifting decoder (Gupta & Nayar 2012) that orders narrow-band high-frequency fringes by their beat; and AMCW time-of-flight multipath, both as a phasor sum and as complex radiosity with per-bounce path delay. On a white 1 mm, 0.5 mm deep 90° V-groove, one fringe across a 4 mm field misreads height by 282 µm RMS; the micro set brings it to 0.76 µm.

Operators: `groove_profile`, `form_factors_2d`, `transport_matrix_radiosity`, `high_frequency_patterns`, `render_transport`, `separate_direct_global`, `fringe_multipath_phase_error`, `predict_fringe_phase_error`, `micro_phase_decode`, `tof_multipath_phase`, `tof_transport_depth`

Runnable: `poc_interreflection_fringe_error`

### [Per-pixel lock-in demodulation (time-correlation imaging: amplitude, phase and DC; ring-light normals, coded-light separation, thermal waves)](capabilities/lockin-demodulation.md)

Nine ops in `lockin` (category `lockin` of `opsoptics`): per-pixel quadrature demodulation of an image sequence against a sinusoidal reference, returning amplitude, phase, DC, in-phase, quadrature and the window leakage; the window is declared (rectangular only for a whole number of periods, otherwise refused; hann reports its leakage). Closed-form amplitude and phase noise from the SNR (Rice phase distribution), a multipole-modulated ring of sources on a Lambertian relief and the normals recovered from its first-harmonic response with the albedo cancelled, Walsh codes and a least-squares separation of coded lights from daylight, and the exact surface temperature of a periodically heated plate for lock-in thermography.

Operators: `lockin_demodulate`, `lockin_amplitude`, `lockin_phase`, `lockin_noise_floor`, `lockin_walsh_codes`, `lockin_separate`, `lockin_ring_synthesize`, `lockin_ring_normals`, `lockin_thermal_wave`

Pipeline: [`lockin_ring_synthesize`](ops/optics/lockin/lockin_ring_synthesize.md) → [`lockin_demodulate`](ops/optics/lockin/lockin_demodulate.md) → [`lockin_ring_normals`](ops/optics/lockin/lockin_ring_normals.md)

Alternatives: [`lockin_amplitude`](ops/optics/lockin/lockin_amplitude.md), [`lockin_phase`](ops/optics/lockin/lockin_phase.md), [`lockin_separate`](ops/optics/lockin/lockin_separate.md), [`lockin_walsh_codes`](ops/optics/lockin/lockin_walsh_codes.md), [`lockin_noise_floor`](ops/optics/lockin/lockin_noise_floor.md), [`lockin_thermal_wave`](ops/optics/lockin/lockin_thermal_wave.md)

Runnable: `poc_lockin_imaging`

### [How much of that number is your measuring, not your process (gauge R&R and measurement uncertainty)](capabilities/measurement-system-and-uncertainty.md)

Separate how much of a number comes from the parts and how much from the act of measuring, then combine the components of a single measurement into a reportable uncertainty. Every operator is a closed-form standards model with an exact identity to check it against. The analysis-of-variance decomposition closes algebraically (`SS_total = SS_part + SS_operator + SS_interaction + SS_error`, relative difference 1e-16); repeatability equals the mean of the per-cell `np.var(ddof=1)` that numpy computes independently; the published worked example (10 parts x 3 operators x 3 trials) is reproduced to 1.5e-06 on EV/AV/GRR/PV with contribution percentages 3.4/4.4/7.8/92.2 exactly. Whether the interaction is kept or pooled into error moves EV by **7.3 %**, so the model actually used is reported (`interaction_pooled`, `interaction_p`), and a negative variance component — which happens in **31 of 40** synthetic runs when the true component is zero — is clamped to zero but declared rather than hidden. On the uncertainty side: the divisors that turn a distribution shape into a standard uncertainty are exact (`a/sqrt(3)`, `a/sqrt(6)`, `a/sqrt(2)`); ignoring correlation errs in **both directions on the same data** (u_c of resistance 0.0702 -> 0.1945, a 2.8x overestimate, while reactance goes the other way); the effective degrees of freedom are truncated immediately before the t lookup as the standard requires (16.64 -> 16 gives k = 2.1199, matching the published 2.12); and the propagation law's breakdown at a stationary point is returned as structure (`guf_valid`, `invalid_reasons`) rather than as a silent `u_c = 0`. A sum of four rectangular distributions has an exact coverage interval via Irwin-Hall, `sqrt(3)(2 x 0.6^(1/4) - 4) = -3.879407`, against which the propagation law is structurally 0.040521 too wide.

Operators: `msa_anova_table`, `msa_gauge_rr`, `msa_bias_linearity`, `msa_attribute_agreement`, `gum_standard_uncertainty`, `gum_propagate`, `gum_expanded`, `gum_monte_carlo`, `gum_validate`, `spc_capability`, `spc_xbar_r`

Runnable: `poc_measurement_system_analysis`

### [Moiré alignment (two gratings of slightly different pitch, fringe phase, nanometre shift, differential pairs and the Talbot gap)](capabilities/moire-alignment.md)

Eight ops in `moirealign` (category `moire_align` of `opsoptics`) for alignment by moiré: two gratings with slightly different pitches (mask p_m, wafer p_w) form fringes of period p_m p_w / |Δp| that move M = p_m / |Δp| times further than the wafer (p_w / |Δp| if the mask moves). Design (magnification, capture range, the Talbot effect of a proximity gap), a closed-form camera image of single, differential and four-quadrant marks, fringe phase by lock-in or Takeda's FFT method, phase to shift with order resolution, differential pairs that cancel drift, illumination and camera-scale errors, and the white-noise lower bound. The PoC measures both magnifications from images, reads 1 nm steps with 0.08 nm RMS, matches the lower bound with a ratio of 1.00, and breaks the gain over a cross-correlation baseline into its bias and random parts.

Operators: `moire_magnification`, `moire_talbot_gap`, `moire_overlay_image`, `moire_phase`, `moire_phase_to_shift`, `moire_differential_shift`, `moire_mark_read`, `moire_phase_crlb`

Pipeline: [`moire_magnification`](ops/optics/moire_align/moire_magnification.md) → [`moire_mark_read`](ops/optics/moire_align/moire_mark_read.md) → [`moire_phase_crlb`](ops/optics/moire_align/moire_phase_crlb.md)

Alternatives: [`moire_phase`](ops/optics/moire_align/moire_phase.md), [`moire_phase_to_shift`](ops/optics/moire_align/moire_phase_to_shift.md), [`moire_differential_shift`](ops/optics/moire_align/moire_differential_shift.md), [`moire_overlay_image`](ops/optics/moire_align/moire_overlay_image.md), [`moire_talbot_gap`](ops/optics/moire_align/moire_talbot_gap.md), [`absolute_phase`](ops/3d/structured_light/absolute_phase.md)

Runnable: `poc_moire_alignment`

### [Find micrometre dents on glossy surfaces from the mirror image of a fringe screen (phase-measuring deflectometry)](capabilities/phase-measuring-deflectometry.md)

Phase-measuring deflectometry for glossy surfaces: a rig table, the screen patterns, a forward renderer from a height field to the camera's image of the screen's mirror reflection (diffuse fraction, specular-lobe scatter, the back reflection of a transparent plate, thin-lens focus by aperture integration, noise and quantisation), absolute screen phases to a normal map on the surface grid, slopes to mean or Gaussian curvature without integrating, and the closed-form sensitivity before measuring (slope noise σ_u/(2d), the height-slope coupling sin θ / d, focus blur). The PoC finds 3 µm and 1 µm dents on a painted panel that a lit photograph cannot show and scores every number against the analytic surface.

Operators: `deflectometry_rig`, `deflectometry_screen_pattern`, `deflectometry_render`, `deflectometry_phase_to_slope`, `slope_to_curvature`, `deflectometry_sensitivity`

Pipeline: [`deflectometry_rig`](ops/specular/deflectometry/deflectometry_rig.md) → [`deflectometry_sensitivity`](ops/specular/deflectometry/deflectometry_sensitivity.md) → [`wrapped_phase`](ops/3d/structured_light/wrapped_phase.md) → [`absolute_phase`](ops/3d/structured_light/absolute_phase.md) → [`deflectometry_phase_to_slope`](ops/specular/deflectometry/deflectometry_phase_to_slope.md) → [`slope_to_curvature`](ops/specular/deflectometry/slope_to_curvature.md)

Alternatives: [`deflectometry_render`](ops/specular/deflectometry/deflectometry_render.md), [`deflectometry_screen_pattern`](ops/specular/deflectometry/deflectometry_screen_pattern.md), [`sfp_height`](ops/optics/shape_from_polarization/sfp_height.md), [`integrate_normals`](ops/3d/photometric/integrate_normals.md)

Runnable: `poc_phase_measuring_deflectometry`

### [Flatness of a surface from a 3-D point cloud](capabilities/planarity-from-point-cloud.md)

From the point cloud of a nominally flat surface: remove outliers, fit a plane robustly, and read flatness (peak-to-valley and RMS) from the signed point-to-plane distances — so warp (low order) and local relief (high order) can be told apart.

Operators: `ransac_plane`, `fit_plane_3d`, `distance_point_plane`, `statistical_outlier_removal`

Pipeline: [`statistical_outlier_removal`](ops/3d/preprocess/statistical_outlier_removal.md) → [`ransac_plane`](ops/3d/robust_fit/ransac_plane.md) → [`fit_plane_3d`](ops/3d/geometry/fit_plane_3d.md) → [`distance_point_plane`](ops/3d/geometry/distance_point_plane.md)

Alternatives: [`fit_plane3`](ops/3d/geometry/fit_plane3.md), [`plane_segmentation`](ops/3d/segment/plane_segmentation.md), [`radius_outlier_removal`](ops/3d/preprocess/radius_outlier_removal.md), [`estimate_normals`](ops/3d/curvature/estimate_normals.md), [`surface_form_error`](ops/3d/surface_fit/surface_form_error.md)

Runnable: `geometry_metrology`, `poc_bump_coplanarity`, `poc_scan_to_bim_asbuilt`

### [Which flaw size will you actually find (probability of detection and a90/95, MIL-HDBK-1823A)](capabilities/probability-of-detection.md)

Probability of detection per MIL-HDBK-1823A: â-vs-a regression with left and right censoring (a Tobit-type maximum likelihood, concave in Olsen's coordinates, reducing exactly to least squares when nothing is censored), the POD(a) curve with a50 / a90 / a90/95 by the delta method, the hit/miss generalised linear model with both Wald and likelihood-ratio a90/95, false-call probability from unflawed sites (binomial one-sided bounds that reproduce the handbook's PFP table to 7.2e-05), and the decision-threshold trade-off. Estimates agree with an independently written likelihood minimised by a different algorithm to 6.6e-08. The delta-method a90/95 covers the true a90 in 94.3 % of large-sample replicates but only 89.2 % at n=60 — reported, not hidden. A slope that cannot be told from zero is refused rather than turned into an absurd a90, and an a90/95 beyond the largest size tested carries a flag.

Operators: `pod_ahat_fit`, `pod_from_ahat`, `pod_hitmiss_fit`, `pod_false_call`, `pod_decision_tradeoff`, `light_source`, `detectability_limit`

Runnable: `poc_pod_lighting`

### [A mean line that deep scratches and spikes cannot drag (robust Gaussian-regression and spline filters, for profiles and surfaces)](capabilities/robust-gaussian-spline-profile-filter.md)

Three ops in the `roughness` ledger (category `prepare`). `robust_gaussian_profile` is a Gaussian-weighted local regression (order 0 or 1) iterated with Tukey's biweight at `c · median|r|`; its transmission is exactly 50 % at λc (closed form `exp(-π(αλc/λ)²)`, α² = ln2/π), measured to 3e-8. `robust_spline_profile` solves a second-difference penalised least squares (a discrete cubic smoothing spline) with the same reweighting; its transfer function `1/(1+(sin(π dx/λ)/sin(π dx/λc))⁴)` is matched to 1e-11. `robust_gaussian_surface` is the areal version. On a synthetic profile with a known waviness, scratches covering up to 20 % of the samples drag the robust mean line 0.06 times as far as the linear one; at 40 % it breaks down, and a non-converging iteration is refused rather than returned.

Operators: `robust_gaussian_profile`, `robust_spline_profile`, `robust_gaussian_surface`, `surface_filter`

Pipeline: [`robust_gaussian_profile`](ops/roughness/prepare/robust_gaussian_profile.md) → [`profile_params`](ops/roughness/measure/profile_params.md)

Alternatives: [`robust_spline_profile`](ops/roughness/prepare/robust_spline_profile.md), [`surface_filter`](ops/roughness/prepare/surface_filter.md), [`robust_gaussian_surface`](ops/roughness/prepare/robust_gaussian_surface.md)

Runnable: `poc_robust_profile_filter`, `example_robust_profile_filter`

### [Detect fine scratches and measure their width](capabilities/scratch-detection-and-width.md)

Two stages: *where* (ridge response `lines_gauss`, or the black-top-hat `bothat` that lifts only dark fine detail) and *how wide* (a measurement line across the detected line, `measure_pairs` for the two sub-pixel edges, `table_px_to_mm` for millimetres).

Operators: `lines_gauss`, `bothat`, `measure_pairs`, `table_px_to_mm`

Pipeline: [`gaussian`](ops/2d/smoothing/gaussian.md) → [`lines_gauss`](ops/2d/contour/lines_gauss.md) → [`select_contours`](ops/2d/contour/select_contours.md) → [`fit_line_contours`](ops/2d/contour/fit_line_contours.md) → [`gen_measure_rectangle2`](ops/measure1d/caliper/gen_measure_rectangle2.md) → [`measure_pairs`](ops/measure1d/caliper/measure_pairs.md) → [`table_px_to_mm`](ops/measure1d/scale/table_px_to_mm.md)

Alternatives: [`bothat`](ops/2d/morphology/bothat.md), [`tophat`](ops/2d/morphology/tophat.md), [`sk_frangi`](ops/2d/texture/sk_frangi.md), [`laplace_of_gauss`](ops/2d/edges/laplace_of_gauss.md), [`fuzzy_measure_pairing`](ops/measure1d/caliper/fuzzy_measure_pairing.md), [`mm_per_px_from_reference`](ops/measure1d/scale/mm_per_px_from_reference.md)

Runnable: `example_scratch_width`, `poc_crack_width`, `poc_solar_el_inspection`

### [Measure how much the bright SEM edge inflates a dimension, with ground truth](capabilities/sem-edge-effect-metrology.md)

Render a ground-truth SEM image from a height field with `sem_render` (secondary-electron edge effect sec θ + Gaussian beam PSF + Poisson shot noise), then segment it with the classic chain and show that the bright edge inflates the measured area by about perimeter × PSF width — and that subtracting the known beam PSF width removes the bias. Score against expert masks with `seg_dice_jaccard` / `seg_boundary_f`, and fit the probability of detection (a90/95) of embedded defects with `pod_hitmiss_fit`.

Operators: `sem_render`, `blob_label`, `blob_features`, `seg_dice_jaccard`, `seg_boundary_f`, `pod_hitmiss_fit`

Runnable: `poc_sem_wafer_defect_edge_bias`

### [Measure the same particles in scanning and transmission images and compare both size biases](capabilities/sem-tem-same-particle.md)

One truth ledger of fourteen 20–80 nm spherical and faceted particles drives both scanning and transmission images. Area-equivalent diameter, maximum-slope edges, distance-transform watershed splitting, stereo height and limited-angle reconstruction are compared against that shared truth.

Operators: `sem_render`, `sem_image`, `tem_projected_potential`, `tem_image_weak_phase`, `tem_multislice`, `tem_power_spectrum`, `watersheds_marker`, `radon_transform`, `filtered_backprojection`

Pipeline: [`sem_render`](ops/generative/sem/sem_render.md) → [`tem_power_spectrum`](ops/optics/tem/tem_power_spectrum.md)

Alternatives: [`sem_image`](ops/generative/sem/sem_image.md), [`tem_image_weak_phase`](ops/optics/tem/tem_image_weak_phase.md), [`watersheds_marker`](ops/segmentation/watershed/watersheds_marker.md), [`radon_transform`](ops/tomography/forward/radon_transform.md), [`filtered_backprojection`](ops/tomography/reconstruct/filtered_backprojection.md)

Runnable: `poc_sem_tem_same_particle`

### [Sequential lens-design metrics (ideal lens surface, encircled energy, tangential / sagittal MTF, through-focus MTF)](capabilities/sequential-lens-design-metrics.md)

### Independent verification of public `.zmx` prescriptions (2026-10-20)

Operators: `lens_system`, `encircled_energy`, `ensquared_energy`, `energy_radii`, `mtf_tangential_sagittal`, `through_focus_mtf`, `with_aiming`, `ray_aiming`, `set_vignetting`, `lens_configurations`, `lens_with_configuration`, `lens_configuration_table`, `lens_configuration_metrics`, `lens_add_configuration`, `glass_nearest`, `lens_substitute_glasses`, `lens_global_search`, `merit_operands_list`, `merit_evaluate`, `merit_default`, `merit_boundary_operands`, `optimize_lens_operands`, `merit_contributions`, `lens_apply_solves`, `lens_solve_set`, `lens_solve_clear`, `lens_solves_list`, `afocal_system`, `lens_afocal_report`, `lens_image_surface`, `lens_petzval_radius`, `lens_zmx_solves_roundtrip`

Pipeline: [`lens_system`](ops/optics/design/lens_system.md) → [`psf_from_opd`](ops/optics/imaging_sim/psf_from_opd.md) → [`encircled_energy`](ops/optics/imaging/encircled_energy.md) → [`energy_radii`](ops/optics/imaging/energy_radii.md) → [`mtf_tangential_sagittal`](ops/optics/imaging/mtf_tangential_sagittal.md) → [`through_focus_mtf`](ops/optics/imaging_sim/through_focus_mtf.md)

Alternatives: [`psf_to_mtf`](ops/optics/imaging/psf_to_mtf.md), [`mtf_diffraction`](ops/optics/imaging/mtf_diffraction.md), [`spot_stats`](ops/optics/design/spot_stats.md), [`opd_map`](ops/optics/design/opd_map.md), [`wavefront_from_opd`](ops/optics/design/wavefront_from_opd.md), [`lens_section_drawing`](ops/optics/drawing/lens_section_drawing.md)

Runnable: `optical_design_metrics`, `poc_zoom_configurations`, `poc_lens_global_search`, `poc_lens_merit_operands`, `poc_lens_solves_afocal`

### [Measure the shape of black-glossy and glass parts from polarisation (shape from polarisation, the ambiguity set, refractive index)](capabilities/shape-from-polarization.md)

Shape from polarisation for a 4-direction on-chip polariser sensor: the Fresnel DoLP of specular reflection (exactly 1 at Brewster's angle, two zenith solutions straddling it) and of diffuse emission (monotone, one solution), checked against the s/p reflectances of `glassmirror` written in a different form to 1e-14; AoLP to the two candidate azimuths (diffuse and specular 90° apart, the π ambiguity kept); the explicit candidate set of normals per pixel; disambiguation by a stated prior (convexity with Brewster-ridge segmentation, or a coarse depth / normal map); refractive-index estimation from DoLP at known zenith angles; and integration to height with a mirror-extended Frankot–Chellappa. Round trips through an independent Mueller-matrix forward path (`optics.mueller_element` / `mueller_apply`) recover analytic spheres, cylinders and rotated ellipsoids to 1e-9° (diffuse) and to 0.1° on the discrete Brewster ridge (specular). Where it breaks is measured: a wrong index, noise concentrated on the Brewster ring and at the apex, and a diffuse component mixed into a specular pixel.

Operators: `sfp_dolp_model`, `dolp_to_zenith`, `aolp_to_azimuth`, `sfp_render`, `sfp_normals`, `sfp_disambiguate`, `sfp_estimate_index`, `sfp_height`

Runnable: `poc_shape_from_polarization`

### [Fit a physical model's coefficients to real images (sim-to-real calibration) — no number for a coefficient the images do not determine, the determined combination and the reason instead](capabilities/sim-to-real-calibration.md)

Ten ops (`simcal` / `simcalcheck`) fit the physical coefficients of a forward model built from fullseye ops (knobs with units, ranges and linear/log scales) to real images by noise-weighted least squares, and refuse to give a number for a coefficient the images do not determine: confounded knobs (illumination x gain, n x d at one wavelength) are reported as the determined combination, knobs without influence or pinned to a range end are refused, a profile likelihood that closes on one side only withdraws the estimate. Over-fitting gates on held-out images reject an 8th-order vignetting polynomial, and residual PCA against the Tracy-Widom edge of white noise detects a model discrepancy (a decentred lens).

Operators: `simcal_model`, `simcal_simulate`, `simcal_observe`, `simcal_screen`, `simcal_fit`, `simcal_identifiability`, `simcal_uncertainty`, `simcal_validate`, `simcal_discrepancy`, `simcal_report`

Pipeline: [`simcal_model`](ops/simcal/model/simcal_model.md) → [`simcal_observe`](ops/simcal/model/simcal_observe.md) → [`simcal_fit`](ops/simcal/fit/simcal_fit.md) → [`simcal_identifiability`](ops/simcal/check/simcal_identifiability.md) → [`simcal_report`](ops/simcal/report/simcal_report.md)

Alternatives: [`simcal_screen`](ops/simcal/fit/simcal_screen.md), [`simcal_uncertainty`](ops/simcal/check/simcal_uncertainty.md), [`simcal_validate`](ops/simcal/check/simcal_validate.md), [`simcal_discrepancy`](ops/simcal/check/simcal_discrepancy.md), [`simcal_simulate`](ops/simcal/model/simcal_simulate.md), [`mv_confounding`](ops/multivar/identifiability/mv_confounding.md), [`mv_residual_pca`](ops/multivar/identifiability/mv_residual_pca.md), [`sens_morris`](ops/multivar/sensitivity/sens_morris.md)

Runnable: `simcal_tour`, `simcal_checks_tour`

### [Measure dimensions from an image, below the pixel](capabilities/subpixel-2d-metrology.md)

Locate edges along a measurement line from the intensity gradient, at sub-pixel resolution, and read a dimension as the distance between paired edges. Unlike counting thresholded pixels, the answer does not move when the threshold does.

Operators: `measure_pos`, `measure_pairs`, `blob_label`, `blob_select`

Pipeline: [`gen_measure_rectangle2`](ops/measure1d/caliper/gen_measure_rectangle2.md) → [`measure_pos`](ops/measure1d/caliper/measure_pos.md) → [`measure_pairs`](ops/measure1d/caliper/measure_pairs.md) → [`table_px_to_mm`](ops/measure1d/scale/table_px_to_mm.md)

Alternatives: [`fuzzy_measure_pairing`](ops/measure1d/caliper/fuzzy_measure_pairing.md), [`gen_measure_arc`](ops/measure1d/caliper/gen_measure_arc.md), [`create_metrology_model`](ops/measure1d/model/create_metrology_model.md), [`blob_label`](ops/blob/connect/blob_label.md), [`blob_select`](ops/blob/select/blob_select.md), [`mm_per_px_from_reference`](ops/measure1d/scale/mm_per_px_from_reference.md)

Runnable: `poc_dimensional_inspection`, `poc_screw_thread_metrology`, `poc_calipers_under_illusion`

### [Telecentric lenses for dimensional metrology (chief-ray angle, magnification versus height, vignetting and blur)](capabilities/telecentric-metrology.md)

Seven ops in `telecentric` (category `telecentric` of `opsoptics`) on top of the `raytrace` prescriptions: a generator of the same singlet with the stop moved (entocentric, object-side telecentric, bi-telecentric, plus a stop shift that spoils telecentricity), the real chief ray found by aiming at the stop itself rather than at the entrance pupil (so it works with the pupil at infinity), the magnification versus object height on a fixed image plane, the dimensional error across a step, the RMS defocus blur from a brute-force pupil bundle, the vignetting set by the front lens, and a pinhole camera at the entrance pupil for `render3d`. The PoC gates the magnification against L/(L − Δz), the stop shift against Newton's equation, the blur slope against |m|·NA/√2, and measurements taken from rendered images against circle-overlap closed forms. The lead chapter measures the paper's raw telecentric images (Stark et al., Sci. Rep. 15, 28690, 2025, CC BY 4.0) with Fullseye's metrology ops and checks them against the paper: a family of ellipses sharing one centre and shape, fitted to the eight rings of an alignment plate (1 mm spacing) tilted by 29.5°, gives 252.13 ± 0.04 px/mm along the major axis, +0.05 % from the paper's K1 = 252.0 px/mm (the paper's own K1 and K2 spread by ±0.25 %, so the match is not read as finer than that). The telecentric signature: the centres of the concentric rings on the tilted plate do not drift with r² (β = 0.0035 ± 0.0034 px/mm², where a 25 mm entocentric lens would give 1.40 and move the outer centre by 101 px), so the entrance pupil lies beyond 10.5 m. Fitting a free ellipse to each ring instead fails on the outer rings whose arcs are shadowed down to 36–180°. A 3D-printed resin sphere (nominal radius 2.5 mm) is not a usable reference: its outline radius moves 8 % with the threshold.

Operators: `telecentric_lens`, `chief_ray_angle`, `magnification_vs_depth`, `telecentricity_error`, `defocus_spot_vs_depth`, `vignetting_vs_field`, `lens_equivalent_pinhole`

Pipeline: [`telecentric_lens`](ops/optics/telecentric/telecentric_lens.md) → [`chief_ray_angle`](ops/optics/telecentric/chief_ray_angle.md) → [`telecentricity_error`](ops/optics/telecentric/telecentricity_error.md) → [`magnification_vs_depth`](ops/optics/telecentric/magnification_vs_depth.md) → [`defocus_spot_vs_depth`](ops/optics/telecentric/defocus_spot_vs_depth.md) → [`vignetting_vs_field`](ops/optics/telecentric/vignetting_vs_field.md)

Alternatives: [`lens_system`](ops/optics/design/lens_system.md), [`paraxial_trace`](ops/optics/design/paraxial_trace.md), [`lens_equivalent_pinhole`](ops/optics/telecentric/lens_equivalent_pinhole.md), [`relative_illumination`](ops/optics/geometric/relative_illumination.md)

Runnable: `poc_telecentric_metrology`

### [A virtual transmission electron microscope (electron wavelength, CTF, phase-contrast images, defocus from Thon rings, correction)](capabilities/tem-phase-contrast-and-ctf.md)

Eleven ops in `temsim` (category `tem` of `opsoptics`): relativistic electron wavelength and interaction constant, Scherzer defocus and point resolution, the 2-D CTF with astigmatism and spatial/temporal envelopes, the 1-D CTF with closed-form zeros, projected potentials from atom positions (electron scattering factors from the X-ray factors of `pxrd` via Mott–Bethe), an amorphous film, weak-phase or nonlinear (`coherent_image`) bright-field images with dose noise, a simple multislice, the tiled power spectrum, defocus and astigmatism estimation from Thon rings (with a jackknife uncertainty and an explicit refusal when the rings are not visible), and phase-flip or Wiener correction. Conventions follow CTFFIND4/RELION (Å, positive defocus = underfocus). The PoC grades against published wavelengths, closed-form CTF zeros, the Scherzer point resolution, Raman–Nath diffraction, synthetic ground truth, and three EMPIAR-10028 micrographs whose defocus it reproduces within 0.2 % of the authors' CTFFIND3 values.

Operators: `tem_wavelength`, `tem_scherzer`, `tem_ctf`, `tem_ctf_profile`, `tem_projected_potential`, `tem_amorphous_film`, `tem_image_weak_phase`, `tem_multislice`, `tem_power_spectrum`, `tem_ctf_estimate`, `tem_ctf_correct`

Pipeline: [`tem_power_spectrum`](ops/optics/tem/tem_power_spectrum.md) → [`tem_ctf_estimate`](ops/optics/tem/tem_ctf_estimate.md) → [`tem_ctf_correct`](ops/optics/tem/tem_ctf_correct.md)

Alternatives: [`tem_ctf_profile`](ops/optics/tem/tem_ctf_profile.md), [`tem_scherzer`](ops/optics/tem/tem_scherzer.md), [`tem_image_weak_phase`](ops/optics/tem/tem_image_weak_phase.md), [`tem_amorphous_film`](ops/optics/tem/tem_amorphous_film.md), [`tem_multislice`](ops/optics/tem/tem_multislice.md)

Runnable: `poc_tem_ctf_thon_rings`

### [Slope, flow and line of sight on a terrain](capabilities/terrain-and-visibility.md)

From a height grid: slope, aspect, viewshed and flow direction. Each has a closed form to check against, so an implementation error shows up as a number.

Operators: `dem_slope`, `dem_aspect`, `dem_viewshed`, `dem_flow_direction`

Pipeline: [`dem_fill_sinks`](ops/dem/hydrology/dem_fill_sinks.md) → [`dem_slope`](ops/dem/surface/dem_slope.md) → [`dem_aspect`](ops/dem/surface/dem_aspect.md) → [`dem_flow_direction`](ops/dem/hydrology/dem_flow_direction.md) → [`dem_viewshed`](ops/dem/visibility/dem_viewshed.md)

Alternatives: [`dem_hillshade`](ops/dem/shading/dem_hillshade.md), [`dem_flow_accumulation`](ops/dem/hydrology/dem_flow_accumulation.md), [`dem_geodetic_slope`](ops/dem/geodesy/dem_geodetic_slope.md)

Runnable: `poc_dem_terrain`, `dem_terrain_analysis_tour`

### [A virtual SEM — solve the electron-solid interaction by Monte Carlo and see, scored against measured data, how voltage, detector and charging change the image and the measured line width](capabilities/virtual-sem-monte-carlo.md)

A Monte Carlo that tracks primary electrons one by one in the solid (Joy's single-scattering model with Browning's 1994 Mott-fit elastic cross-section and the Joy-Luo stopping power). `sem_electron_mc` returns the backscatter coefficient, the secondary-electron yield and the penetration depth; `sem_yield_curve` sweeps the voltage. Material Z, A, density and secondary-electron constants come from the same material table the optics use (`material_electron_properties`). `sem_line_profile` scans a line with a trapezoidal cross-section (buried rectangles allowed) and `sem_cd_measure` measures its width by threshold or maximum slope. `sem_image` fires electrons into every pixel of a height field with a material map (in-lens SE, side SE, backscatter detector) and `sem_charging_series` steps insulator charging frame by frame. Four external-truth gates: backscatter coefficients inside measured bands, Arnal's tilt law, the Kanaya-Okayama range, and the Lin & Joy 2005 universal yield curve and Emax.

Operators: `sem_electron_mc`, `sem_yield_curve`, `sem_se_universal_curve`, `sem_line_profile`, `sem_cd_measure`, `sem_image`, `sem_charging_series`, `sem_se_escape_fraction`, `material_electron_properties`

Pipeline: [`material_electron_properties`](ops/optics/matprop/material_electron_properties.md) → [`sem_electron_mc`](ops/generative/sem/sem_electron_mc.md) → [`sem_line_profile`](ops/generative/sem/sem_line_profile.md) → [`sem_cd_measure`](ops/generative/sem/sem_cd_measure.md) → [`sem_image`](ops/generative/sem/sem_image.md)

Alternatives: [`sem_render`](ops/generative/sem/sem_render.md), [`sem_yield_curve`](ops/generative/sem/sem_yield_curve.md), [`sem_charging_series`](ops/generative/sem/sem_charging_series.md)

Runnable: `poc_virtual_sem_kv_cd_bse`

### [Turn a 3-D scan into a volume](capabilities/volume-from-3d-scan.md)

Compute a signed volume from a closed mesh, a voxel count from a labelled region, or the material between two surfaces from a height grid. Gaps can be filled by interpolation, and how far that interpolation reached is reported separately.

Operators: `mesh_volume`, `vol_rle_volume`, `interp_scattered`, `dem_slope`

Pipeline: [`vol_rle_components`](ops/3d/rle_region/vol_rle_components.md) → [`vol_rle_volume`](ops/3d/rle_region/vol_rle_volume.md) → [`mesh_volume`](ops/3d/mesh_process/mesh_volume.md)

Alternatives: [`interp_scattered`](ops/math/interp_poly/interp_scattered.md), [`dem_slope`](ops/dem/surface/dem_slope.md), [`dem_fill_sinks`](ops/dem/hydrology/dem_fill_sinks.md), `marching_cubes`

Runnable: `poc_stockpile_volume`, `poc_lidar_terrain_change`

### [What a picture cannot check (integrator order, Lyapunov spectrum, bifurcations, correlation dimension, minimal surfaces)](capabilities/what-a-picture-cannot-check.md)

Integrate named dynamical systems (Lorenz, Rossler, harmonic, arbitrary linear `A`), sample their fields, take Poincare sections, compute Lyapunov spectra, bifurcation maps and correlation dimensions; build minimal surfaces (catenoid, helicoid, Enneper, Scherk, gyroid) and sweep a curve into a tube mesh — and score all of it with identities and definitions rather than by eye, because a Lorenz plot looks the same whether the integrator is 1st or 4th order and a surface looks smooth whether or not its mean curvature vanishes. RK4's error falls by exactly 16 per halving against `expm(At)x0` (Euler, the control, falls by 2); the *sum* of the Lyapunov exponents equals the trace identity `-(sigma+1+beta)` to 2.6e-06, independently of the tangent-flow/QR procedure that produced them; the logistic period-doubling points are the exact 3 and `1+sqrt(6)`, and the residual is attributed — the gate is not "the error is small" but "lengthening the burn-in shrinks it by 10.9x", because convergence at a bifurcation is algebraic; the correlation-dimension bias on a bounded set is traced to the **radius window**, not the sample count (400 to 3,000 points does not move it; narrowing `r_lo`/`r_hi` moves 1.887 to 2.050); the field's divergence equals `tr(A)` and its vorticity `A10 - A01` as measured by the **existing PIV ops**, which know nothing about this family; a tube swept along a circle is a torus whose analytic volume `2*pi^2*R*r^2` and area `4*pi^2*R*r` the existing `mesh_volume` / `mesh_area` confirm to 0.3 %; and the minimal surfaces have `|H|` medians of 1e-4 against controls of 1.00004 (unit sphere) and 0.50000 (unit cylinder), with the gyroid's nodal-approximation residual reported rather than hidden.

Operators: `ode_flow_states`, `ode_vector_field_grid`, `dynsys_poincare_section`, `dynsys_lyapunov_spectrum`, `dynsys_bifurcation_map`, `dynsys_correlation_dimension`, `minimal_surface`, `minimal_surface_bend`, `gyroid_isosurface`, `gyroid_solid_mask`, `curve3d_tube_mesh`

Runnable: `poc_what_a_picture_cannot_check`

## Detect (13)

### [Segment regions, select them, and count](capabilities/blob-and-region.md)

Label connected components, select them by area, shape or position, and count them. Touching objects can be separated with a watershed.

Operators: `blob_label`, `blob_select`, `blob_count`, `watersheds`, `blob_count_interval`

Pipeline: [`auto_threshold`](ops/2d/segmentation/auto_threshold.md) → [`blob_label`](ops/blob/connect/blob_label.md) → [`blob_select`](ops/blob/select/blob_select.md) → [`blob_features`](ops/blob/measure/blob_features.md)

Alternatives: [`watersheds`](ops/2d/segmentation/watersheds.md), [`blob_seeds`](ops/blob/split/blob_seeds.md), [`blob_count`](ops/2d/features/blob_count.md), [`blob_count_interval`](ops/blob/split/blob_count_interval.md), [`remove_small`](ops/2d/region/remove_small.md), [`select_shape`](ops/2d/region/select_shape.md), [`otsu`](ops/2d/segmentation/otsu.md)

Runnable: `poc_cell_counting`, `poc_particle_sizing`, `poc_real_coin_metrology`, `poc_dense_bubble_count`

### [Separating crop from weeds in field RGB by colour and texture, and grading weed cover at declared edges (no learned network)](capabilities/crop-weed-cover-grade.md)

Five ops for field RGB: six visible-band plant colour indices (ExG, ExR, ExGR, CIVE, NGRDI, VEG; dark pixels are left undefined rather than set to zero), ten colour and texture features per region of a label image (including structure-tensor orientation coherence, which separates aligned crop leaves from isotropic weed patches), a closed-form two-class Fisher discriminant (fit and score), and a grader that splits a cover fraction at edges declared before evaluation (default 5 / 25 / 50 %, the Braun-Blanquet cover classes). The PoC scores them on a public UAV dataset of weedy rice with pixel masks (CC BY 4.0): grade agreement kappa 0.424 on the held-out test split (permutation p = 0.0005), cover correlation 0.826, and an honest leave-one-date-out check where one late-season flight drops to r = 0.14.

Operators: `plant_color_index`, `superpixel_color_texture_features`, `fisher_lda_fit`, `fisher_lda_score`, `cover_ratio_grade`

Pipeline: [`superpixel_color_texture_features`](ops/segmentation/plant/superpixel_color_texture_features.md) → [`fisher_lda_fit`](ops/segmentation/classify/fisher_lda_fit.md) → [`fisher_lda_score`](ops/segmentation/classify/fisher_lda_score.md) → [`cover_ratio_grade`](ops/segmentation/plant/cover_ratio_grade.md)

Alternatives: [`plant_color_index`](ops/segmentation/plant/plant_color_index.md), [`snic_superpixels`](ops/segmentation/graph/snic_superpixels.md), [`class_ndim_norm`](ops/segmentation/classify/class_ndim_norm.md)

Runnable: `poc_weed_rice_ratio`

### [Separate thickness from material with two X-ray energies (dual-energy and photon-counting X-ray: spectrum, energy windows, basis decomposition, effective Z)](capabilities/dual-energy-xray-material-discrimination.md)

Dual-energy and photon-counting X-ray material discrimination. The material table gains an X-ray column: mass attenuation coefficients from a bundled subset of NIST SRD 126 (Hubbell and Seltzer; 49 elements, 21 materials, 1 keV to 1 MeV) and the mixture rule for anything with a known composition, under the same names as the optical column. On top of it: a tungsten-anode tube spectrum and its half-value layer, photon-counting energy windows (absorption efficiency, energy resolution, charge-sharing tail) and dual-kVp channels, a noisy channel projection, a per-pixel polychromatic basis-material decomposition that rejects pixels it cannot solve, its Cramér-Rao bound, the R value, an effective-Z map and the closed-form separability of two materials. The PoC finds bone and glass fragments that a single X-ray image buries under the thickness variation of meat.

Operators: `material_xray_table`, `material_xray_attenuation`, `material_xray_constants`, `material_effective_z`, `xray_tube_spectrum`, `xray_beam_quality`, `photon_counting_channels`, `dual_kvp_channels`, `xray_channel_projection`, `basis_material_decompose`, `basis_decomposition_crlb`, `r_value_map`, `effective_z_map`, `dual_energy_separability`

Pipeline: [`xray_tube_spectrum`](ops/tomography/spectral_xray/xray_tube_spectrum.md) → [`photon_counting_channels`](ops/tomography/spectral_xray/photon_counting_channels.md) → [`basis_decomposition_crlb`](ops/tomography/spectral_xray/basis_decomposition_crlb.md) → [`basis_material_decompose`](ops/tomography/spectral_xray/basis_material_decompose.md) → [`effective_z_map`](ops/tomography/spectral_xray/effective_z_map.md)

Alternatives: [`dual_kvp_channels`](ops/tomography/spectral_xray/dual_kvp_channels.md), [`r_value_map`](ops/tomography/spectral_xray/r_value_map.md), [`dual_energy_separability`](ops/tomography/spectral_xray/dual_energy_separability.md), [`xray_channel_projection`](ops/tomography/spectral_xray/xray_channel_projection.md), [`material_xray_attenuation`](ops/tomography/spectral_xray/material_xray_attenuation.md)

Runnable: `poc_dual_energy_xray`

### [Fix the text inside an image against the string it should read](capabilities/fix-text-in-images.md)

Fix the text inside an image against the string it should read, without regenerating the image: pass `{"items": [{"text": "...", "bbox": [x, y, w, h]}]}` to `glyph_correct_spec` (Python) or `fullseye_fix_text` (MCP). Nothing is recognised — the intended string is given, so each cell is verified one-to-one against one character, and the threshold comes from the typeface noise floor measured on the fonts of the environment. `repair_flagged` replaces only the glyphs above the floor and rolls back any replacement that does not verify; `rewrite_line` redraws the whole line in one typeface. The report carries a per-line `status`, a machine-readable `reason_code` for refusals, and `mismatch` (`typo` / `unrelated`) so that a caller notices when the original text has nothing to do with the intended one.

Operators: `glyph_correct_spec`, `glyph_make_spec`, `glyph_find_text_lines`, `glyph_rewrite_line`, `glyph_find_plate`, `glyph_typeface_noise_floor`, `glyph_rendering_noise_floor`, `glyph_distance`, `glyph_replace`, `glyph_split_cells`, `glyph_fonts`

Runnable: `fix_text_in_image`, `poc_glyph_typo_detection`

### [Flag what differs from aligned good samples (a per-pixel variation model with a declared false-alarm rate)](capabilities/good-sample-variation-model.md)

A per-pixel variation model learned from aligned good samples, with the band half-width derived from a declared per-pixel false-alarm rate rather than tuned by hand: a t prediction interval for mean/std, an empirical-Bayes moderated t (Smyth 2004) for few samples, and a Monte-Carlo pivot for the robust median/MAD variant. Measured false-alarm rates on synthetic normal good samples fall inside the binomial 4-sigma band for all four estimators. The stack's alignment is measured to 1/20 px and a misaligned stack is refused (or registered by an all-pass Fourier shift); forcing a 1-2 px misaligned stack fattens the band on edges 22-fold and misses every edge defect. Held-out calibration re-derives k from good images when real data break the model, and every out-of-band region is explained by area, sign and peak sigma. Method-independent metrics (pixel AUROC, AUPRO to FPR 0.3, image AUROC, per-region overlap) compare it with RPCA and golden comparison.

Operators: `varmodel_alignment`, `varmodel_band_k`, `varmodel_fit`, `varmodel_calibrate`, `varmodel_score`, `anomaly_pixel_auroc`, `anomaly_pro`, `anomaly_image_auroc`, `anomaly_region_overlap`, `compare_to_golden`

Pipeline: [`varmodel_alignment`](ops/spc/variation/varmodel_alignment.md) → [`varmodel_fit`](ops/spc/variation/varmodel_fit.md) → [`varmodel_calibrate`](ops/spc/variation/varmodel_calibrate.md) → [`varmodel_score`](ops/spc/variation/varmodel_score.md)

Alternatives: `compare_to_golden`, [`dc_rpca_sparse`](ops/2d/decomposition/dc_rpca_sparse.md), [`anomaly_pro`](ops/spc/anomaly_eval/anomaly_pro.md)

Runnable: `poc_good_sample_variation_model`, `anomaly_eval_metrics`

### [OCR pre-processing (deskew, local binarisation, line extraction)](capabilities/ocr-preprocessing.md)

Everything before the recogniser: deskew, local (Sauvola) binarisation, speck removal and merging characters into lines, all from registry operators. Recognition itself is out of scope.

Operators: `sk_sauvola`, `rotate_image`, `remove_small`, `dilation_rectangle1`

Pipeline: [`median`](ops/2d/rank/median.md) → [`rotate_image`](ops/2d/geometry/rotate_image.md) → [`sk_sauvola`](ops/2d/segmentation/sk_sauvola.md) → [`invert_region`](ops/2d/region/invert_region.md) → [`remove_small`](ops/2d/region/remove_small.md) → [`select_shape`](ops/2d/region/select_shape.md) → [`dilation_rectangle1`](ops/2d/region/dilation_rectangle1.md)

Alternatives: [`sk_niblack`](ops/2d/segmentation/sk_niblack.md), [`adaptive_gauss_thresh`](ops/2d/segmentation/adaptive_gauss_thresh.md), [`otsu`](ops/2d/segmentation/otsu.md), [`gray_bothat`](ops/2d/morphology/gray_bothat.md), [`unsharp`](ops/2d/smoothing/unsharp.md), [`zoom_image_factor`](ops/2d/geometry/zoom_image_factor.md), [`affine_trans_image`](ops/2d/geometry/affine_trans_image.md)

Runnable: `gallery2d_segmentation`, `poc_matrix_code_reading`, `gallery2d_region`

### [Flag patches that leave what good samples look like (classical features, a normal distribution per position or a memory bank, and a recall-guaranteeing operating point)](capabilities/patch-feature-anomaly-detection.md)

Anomaly detection from good samples only, with classical, deterministic patch features instead of a pretrained network. `patchdist_*` fits a multivariate normal per grid position and scores by Mahalanobis distance; since n good images give a singular covariance when n <= D, the shrinkage is declared (Ledoit–Wolf analytic intensity, or a number) and `shrinkage="none"` is refused for a singular covariance. `pool="global"` fits one distribution to all patches for stationary textures. `patchbank_*` keeps a memory bank thinned by greedy k-centre covering, reports the covering radius, and optionally appends the grid position to find a correct pattern in the wrong place. Evaluation uses the method-independent `anomeval` family (pixel / image AUROC, AUPRO, F1 max) and `anomaly_operating_point`, which picks the highest threshold whose defect recall is guaranteed at a stated confidence with an exact Clopper–Pearson limit and refuses when there are too few defective images. On a stochastic texture the per-position normal distribution loses to the pooled distribution and the memory bank at 5, 20 and 80 good images; a memory bank at 10 % keeps its accuracy at about a tenth of the scoring time; the guaranteed operating point keeps its declared confidence in 95.7 % of 300 repetitions against 50.3 % for the unguaranteed quantile.

Operators: `patch_features`, `patchdist_fit`, `patchdist_score`, `patchbank_fit`, `patchbank_score`, `anomaly_pixel_auroc`, `anomaly_pro`, `anomaly_image_auroc`, `anomaly_pixel_f1_max`, `anomaly_image_f1_max`, `anomaly_operating_point`, `anomaly_region_overlap`

Pipeline: [`patchbank_fit`](ops/spc/anomaly_patch/patchbank_fit.md) → [`patchbank_score`](ops/spc/anomaly_patch/patchbank_score.md)

Alternatives: [`varmodel_fit`](ops/spc/variation/varmodel_fit.md), `compare_to_golden`, [`dc_rpca_sparse`](ops/2d/decomposition/dc_rpca_sparse.md)

Runnable: `poc_patch_anomaly`, `anomaly_eval_metrics`

### [Why a thin groove disappears in a PL image — the carrier-diffusion PSF and the kind of defect decide the visibility (PL/EL inspection of wafers and solar cells)](capabilities/pl-carrier-diffusion-visibility.md)

A PL image glows only after the excess carriers have diffused, so a second PSF — the 2-D Green function K₀(r/L)/2πL², L = √(Dτ) — sits on top of the optical one. `pl_diffusion_psf` returns that kernel (sum 1); `pl_image_simulate` solves the steady-state diffusion equation exactly on the grid from an excitation map and an extra-recombination map (optional optical PSF and noise); `pl_groove_visibility` gives the closed-form contrast, CNR and visibility boundary L* of a shadow groove (missing excitation, 1 − e^{−w/2L}) and a sink groove (a recombination line, Donolato's SL/(SL+2D)). The two move in opposite directions with L: a longer diffusion length hides shadows and reveals sinks. Embedded-groove detection feeds `pod_hitmiss_fit` for a90/95.

Operators: `pl_diffusion_psf`, `pl_image_simulate`, `pl_groove_visibility`, `pod_hitmiss_fit`

Runnable: `poc_si_wafer_pl_defect_visibility`

### [Find small point-like targets and locate them below the pixel](capabilities/point-target-detection.md)

Pick local maxima above a robustly estimated background plus k sigma, and return sub-pixel centroids. The name is astronomical but the method is domain-neutral: drifting objects, small defects, fluorescent puncta, particles.

Operators: `star_detect`, `peak_subbin`, `find_peaks`, `noise_sigma`

Pipeline: [`noise_sigma`](ops/astrostack/quality/noise_sigma.md) → [`star_detect`](ops/astrostack/photometry/star_detect.md) → [`find_peaks`](ops/oned/signal/find_peaks.md) → [`peak_subbin`](ops/oned/signal/peak_subbin.md)

Alternatives: [`xsk3_peak_local_max`](ops/2d/segmentation/xsk3_peak_local_max.md), [`blob_seeds`](ops/blob/split/blob_seeds.md), [`blob_label`](ops/blob/connect/blob_label.md)

Runnable: `poc_search_sweep_width`, `poc_astro_photometry`

### [Template matching that survives uneven light, highlights and occlusion (compare the direction of brightness change as codes, and refuse templates that cannot fix a position)](capabilities/robust-code-matching.md)

Six ops (`codematch`) match on the direction of brightness change instead of its value: orientation code matching (OCM), increment sign correlation (ISC, exactly invariant to any strictly monotone brightness map), the selective correlation coefficient (SCC, with the extended mask) and the Radial Reach Filter for background comparison. Templates whose codes cannot fix a position are refused with ValueError, where NCC still returns a confident wrong answer. On real CC0 photographs with 40 templates per level, NCC drops below half its hits at 10 % occlusion and 6 % saturated highlight; OCM and ISC hold until 63-67 % occlusion and 44-53 % highlight. None of the four is rotation invariant (half the hits are lost at 7-9 degrees).

Operators: `ocm_match`, `isc_match`, `scc_match`, `orientation_code`, `increment_sign`, `radial_reach_filter`

Pipeline: [`isc_match`](ops/codematch/match/isc_match.md) → [`ocm_match`](ops/codematch/match/ocm_match.md)

Alternatives: [`scc_match`](ops/codematch/match/scc_match.md), [`ncc_locate`](ops/2d/matching/ncc_locate.md), [`radial_reach_filter`](ops/codematch/change/radial_reach_filter.md)

Runnable: `poc_code_matching_breakdown`

### [Find hybrid-bond voids by the phase of the ultrasonic echo, not its brightness (scanning acoustic microscope C-scans, the frequency trade-off, POD)](capabilities/sam-bond-voids.md)

Pulse-echo ultrasound in layered stacks and scanning-acoustic-microscope C-scans, built from first principles: a material table that carries a source and a verified flag per value (unverified placeholders are refused unless asked for), interface coefficients with the energy check R² + (Z1/Z2)T² = 1 and the sign flip exactly where Z drops, a normal-incidence longitudinal transfer-matrix A-scan with water path and power-law attenuation (checked against a bottom-up Airy recursion, a time-domain ray sum and the optical thin-film formula to 1e-12), and a focused C-scan with a per-frequency Gaussian lateral PSF (FWHM 1.02 λ_water F#) that returns amplitude, phase, in-phase and single-sample-polarity images. Phase is read at the expected time of the bond plane relative to the front-surface echo: thin Cu and SiO2 layers give quadrature echoes, voids are inverted, so a small void adds at right angles to the background and barely changes the amplitude. A closed-form optimal frequency balances lateral resolution against water attenuation, with the front-echo time floor and the critical-angle F-number floor alongside; C-scan statistics feed the existing POD operators.

Operators: `acoustic_material_table`, `acoustic_layer_stack`, `acoustic_interface_coefficients`, `pulse_echo_ascan`, `sam_cscan`, `echo_phase_polarity`, `sam_frequency_tradeoff`

Runnable: `poc_sam_hybrid_bonding_voids`

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

## Shape (3)

### [Correct lens distortion over a whole image (barrel, pincushion, tangential)](capabilities/lens-distortion-correction.md)

Whole-image Brown–Conrady undistortion and its inverse, built as a backward map over this repo's own point model plus a bilinear, edge-clamped remap — so a corrected image is hole-free and a synthetic distorted image is exact to the resampling. `dist` is `[k1, k2, p1, p2(, k3)]` (OpenCV order); `K`'s principal point is the distortion centre. Grey or colour, in `[0, 1]`. On a smooth scene the round trip `distort_image` → `undistort_image` recovers the interior to a few times 1e-4 (only the double bilinear blur remains); the remap field equals `distort_points` to machine precision.

Operators: `undistort_image`, `distort_image`, `distort_points`, `undistort_points`

Runnable: `lens_undistort`

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

## Light and colour (21)

### [Chromatic confocal displacement sensor (glass dispersion, calibration table, return spectrum, height and thickness)](capabilities/chromatic-confocal-sensor.md)

Six ops in `chromconf` (category `confocal`): the probe calibration from a lens prescription and the glass dispersion of the material table (paraxial focus, image-side NA and longitudinal spherical aberration per wavelength, and the mirror-peak calibration), the confocal axial response (mirror and point, with spherical aberration), the return spectrum of a surface and a layer stack (Fresnel reflectance from the material table, tilt, roughness, source, spectrometer, noise), peak picking with white-reference correction, readout of heights and transparent-plate thickness with an NA correction, and closed-form limits (range, resolution, tilt, minimum film). Gates: thick-lens focus, sinc² width ∝ λ/NA², pupil-overlap Monte Carlo for tilt, plate thickness to 0.1 %, and the gold bias predicted by the reflectance slope over the response curvature.

Operators: `chromatic_confocal_probe`, `confocal_axial_response`, `chromatic_confocal_spectrum`, `chromatic_confocal_peaks`, `chromatic_confocal_readout`, `chromatic_confocal_limits`

Pipeline: [`chromatic_confocal_probe`](ops/optics/confocal/chromatic_confocal_probe.md) → [`chromatic_confocal_spectrum`](ops/optics/confocal/chromatic_confocal_spectrum.md) → [`chromatic_confocal_peaks`](ops/optics/confocal/chromatic_confocal_peaks.md) → [`chromatic_confocal_readout`](ops/optics/confocal/chromatic_confocal_readout.md)

Alternatives: [`confocal_axial_response`](ops/optics/confocal/confocal_axial_response.md), [`chromatic_confocal_limits`](ops/optics/confocal/chromatic_confocal_limits.md)

Runnable: `poc_chromatic_confocal`

### [Measure colour (XYZ / Lab / colour difference)](capabilities/colour-and-delta-e.md)

From spectral reflectance or RGB, compute CIE XYZ and Lab, then colour differences under CIE76 or CIEDE2000. The difference can also be returned as a per-pixel map.

Operators: `rgb_to_lab`, `xyz_to_lab`, `delta_e_2000`, `cie_xyz_from_wavelength`

Pipeline: [`rgb_to_lab`](ops/imgmetrics/colorspace/rgb_to_lab.md) → [`delta_e_2000`](ops/imgmetrics/colordiff/delta_e_2000.md)

Alternatives: [`rgb_to_xyz`](ops/imgmetrics/colorspace/rgb_to_xyz.md), [`xyz_to_lab`](ops/imgmetrics/colorspace/xyz_to_lab.md), [`delta_e_76`](ops/imgmetrics/colordiff/delta_e_76.md), [`delta_e_map`](ops/imgmetrics/colordiff/delta_e_map.md), [`cie_xyz_from_wavelength`](ops/optics/appearance/cie_xyz_from_wavelength.md), [`srgb_to_linear`](ops/gfx2d/colorspace/srgb_to_linear.md)

Runnable: `poc_white_balance`, `poc_pigment_unmixing`

### [Run inter-reflections, multiple scattering and iterations to convergence — return the evidence and the remaining error, and no value when it did not converge](capabilities/convergent-forward-models.md)

Six ops (`converge`) run a forward model to convergence and return the evidence: a fixed-point driver with Aitken and Anderson acceleration (Walker & Ni 2011 eq. 3.1; it reproduces GMRES on linear maps, checked) that refuses divergent or oscillating runs; the observed order and grid convergence index of Celik et al. 2008 (Table 1 reproduced); sequential Monte Carlo to a tolerance; MCML-type photon transport in layered turbid slabs with confidence intervals that contain the MCML manual's Table 6.1 / 6.2 values; and Richardson-Lucy stopped by the Poisson discrepancy principle (tau = 1) or Morozov's, refusing data outside the model's range.

Operators: `iterate_fixed_point`, `conv_observed_order`, `conv_gci`, `mc_sequential_mean`, `mc_photon_slab`, `iv_richardson_lucy_until`

Pipeline: [`iterate_fixed_point`](ops/converge/iterate/iterate_fixed_point.md) → [`conv_gci`](ops/converge/verification/conv_gci.md)

Alternatives: [`conv_observed_order`](ops/converge/verification/conv_observed_order.md), [`mc_sequential_mean`](ops/converge/montecarlo/mc_sequential_mean.md), [`mc_photon_slab`](ops/converge/montecarlo/mc_photon_slab.md), [`iv_richardson_lucy_until`](ops/converge/stopping/iv_richardson_lucy_until.md), [`iv_richardson_lucy`](ops/2d/restoration/iv_richardson_lucy.md)

Runnable: `converge_tour`

### [Optical fibres and light guides (glass dispersion, LP modes, mode field diameter, illumination efficiency)](capabilities/fiber-and-light-guide.md)

Seven ops in `fiberoptics` (category `fiber`): group index and material dispersion D(λ) from the material table, numerical aperture, V number and cutoff wavelength, LP_lm modes by solving the weakly guiding characteristic equation, the mode field diameter of LP01 (best-overlap Gaussian, with the Marcuse fit and the second-moment definition alongside), and the efficiency of a light guide (packing fraction, end-face Fresnel, NA acceptance, attenuation). Gates: Bessel-zero cutoffs, V²/2 mode count, the Rudolph–Neumann b(V) and Marcuse MFD fits, the 1.27 µm zero of silica's material dispersion, and the ITU-T G.652 MFD range.

Operators: `material_group_index`, `material_gvd`, `fiber_numerical_aperture`, `fiber_v_number`, `fiber_lp_modes`, `fiber_mode_field_diameter`, `fiber_bundle_coupling`

Runnable: `poc_fiber_light_guide`

### [Grating spectrometer and microscope illumination (bandwidth, smile and keystone, Koehler and critical illumination, coaxial half mirror)](capabilities/grating-spectrometer-and-illumination.md)

Five ops in `gratingspec` (category `spectrometer`): the grating equation with angular and reciprocal linear dispersion, resolving power mN, free spectral range and overlapping orders; a first-order Czerny-Turner design with Shafer's coma condition; the bandpass as the FWHM of the slit image, pixel and diffraction convolved, with the etendue; smile and keystone of a long slit from the 3-D grating equation; and the detector reading of an input spectrum including higher-order overlap and a long-pass filter. Three in `illumdesign`: Koehler and critical illumination trains with their conjugates, the specimen irradiance by paraxial backward tracing to a source radiance map, and the coaxial half mirror (round trip R·T, ghost, the image of a mirror-like or matte part).

Operators: `grating_dispersion`, `czerny_turner_design`, `spectrometer_bandpass`, `spectrometer_slit_image`, `spectrometer_spectrum`, `illumination_train`, `illumination_field`, `coaxial_illumination`

Pipeline: [`czerny_turner_design`](ops/optics/spectrometer/czerny_turner_design.md) → [`spectrometer_bandpass`](ops/optics/spectrometer/spectrometer_bandpass.md) → [`spectrometer_spectrum`](ops/optics/spectrometer/spectrometer_spectrum.md)

Alternatives: [`grating_dispersion`](ops/optics/spectrometer/grating_dispersion.md), [`spectrometer_slit_image`](ops/optics/spectrometer/spectrometer_slit_image.md), [`illumination_train`](ops/optics/illumination/illumination_train.md), [`illumination_field`](ops/optics/illumination/illumination_field.md), [`coaxial_illumination`](ops/optics/illumination/coaxial_illumination.md)

Runnable: `poc_spectrometer_illumination`

### [Illumination cone versus imaging NA on specular parts (cap intersection, slope bands, dents, scratches and satin)](capabilities/illumination-cone-vs-na.md)

Five ops in `illumdesign` (category `illumination`) for lights defined by the cone of directions they deliver to every point (the far-field / Koehler limit), against a camera of object-side NA. On a specular facet the reflection moves the cone by 2θ without changing it, so the brightness is the intersection of two spherical caps, a closed form: slopes below |α − β|/2 do not show, slopes beyond (α + β)/2 go dark. The ops return the light, the closed-form slope thresholds, the brightness per slope (closed form and a projected-solid-angle pupil integral, with Gaussian micro-facet roughness), the contrast versus the cone half-angle, and an image of a normal map under the light. The PoC checks the closed form against the pupil integral (0.002) and against contrasts measured from rendered images (0.0004), chooses a cone that hides hairline marks while blackening a 4° scratch, reads the slope sign with a tilted cone, and shows waviness and roughness defeating the design.

Operators: `solid_angle_light`, `solid_angle_boundaries`, `solid_angle_brightness`, `solid_angle_sweep`, `solid_angle_render`

Pipeline: [`solid_angle_light`](ops/optics/illumination/solid_angle_light.md) → [`solid_angle_boundaries`](ops/optics/illumination/solid_angle_boundaries.md) → [`solid_angle_sweep`](ops/optics/illumination/solid_angle_sweep.md) → [`solid_angle_brightness`](ops/optics/illumination/solid_angle_brightness.md) → [`solid_angle_render`](ops/optics/illumination/solid_angle_render.md)

Alternatives: [`light_source`](ops/optics/illumination/light_source.md), [`defect_contrast`](ops/optics/illumination/defect_contrast.md), [`lighting_sweep`](ops/optics/illumination/lighting_sweep.md), [`illumination_design`](ops/optics/illumination/illumination_design.md), [`micro_normals`](ops/optics/finish/micro_normals.md), [`blast_normals`](ops/optics/finish/blast_normals.md)

Runnable: `poc_illumination_cone_vs_na`

### [Count interreflection in concave parts to convergence without losing the photometric truth (3-D view factors, progressive radiosity, an inspection render with bounces)](capabilities/interreflection-to-convergence.md)

Seven ops in `radiosity3d` (category `radiosity` of `opsoptics`). `render_optscene_gi` takes the scene, camera and lights of `render_optscene`, keeps its direct photometry exactly (zero bounces reproduce `render_optscene`), and adds Lambertian interreflection — `k` bounces as a Neumann partial sum or the converged sum by progressive radiosity (Cohen et al. 1988) — returning the image, the direct image, their difference (the interreflection map), the convergence evidence (residual unshot energy, shots, converged) and a bounce study (observed ratio of successive increments, a GCI-style estimate trusted in the asymptotic range, the bounce count that brings the remainder under a tolerance). The building blocks: Howell's closed forms C-11 and C-14, numerical view factors between flat convex polygons, patch sets from a scene or from polygons, the all-pairs view-factor matrix with occlusion, and the progressive solver whose stopping rule (residual energy below `tol` of the initial) is stated as our choice.

Operators: `form_factor_parallel_rects`, `form_factor_perpendicular_rects`, `form_factor_polygons`, `radiosity_patches`, `form_factor_matrix`, `radiosity_progressive_3d`, `render_optscene_gi`

Pipeline: [`radiosity_patches`](ops/optics/radiosity/radiosity_patches.md) → [`form_factor_matrix`](ops/optics/radiosity/form_factor_matrix.md)

Alternatives: [`render_optscene_gi`](ops/optics/radiosity/render_optscene_gi.md), [`radiosity_progressive_3d`](ops/optics/radiosity/radiosity_progressive_3d.md), [`render_optscene`](ops/optics/scene/render_optscene.md), [`render_studio`](ops/optics/scene/render_studio.md), [`transport_matrix_radiosity`](ops/optics/light_transport/transport_matrix_radiosity.md), [`form_factors_2d`](ops/optics/light_transport/form_factors_2d.md)

Runnable: `poc_pocket_interreflection`

### [Lens design files (read, write and triage sequential .zmx prescriptions)](capabilities/lens-prescription-files.md)

`lens_file_read` turns the plain-text sequential prescription that commercial lens-design programs save (`.zmx`) into a `raytrace.lens_system` (or, when the file has `COORDBRK` coordinate breaks — tilts, decentres, fold mirrors — into a `raytrace3d.noncoaxial_system`, with the order flag, the frame flip at mirrors, returns and `PPAR` pickups handled), so every Fullseye optics op (real rays, Seidel sums, OPD / PSF / MTF, colour, tolerances, DLS optimisation, section drawings) runs on it unchanged. Fields and wavelengths are kept as listed in the file; `lens_file_system` picks one. `lens_file_write` writes a prescription (optionally the geometry of an edited system) back, and `lens_file_report` classifies every keyword as read, ignored (with a reason) or unsupported without importing. Glasses come from the material table or your own `.agf` catalogues, matched by exact name. The PoC checks first-order data, Seidel sums and real rays against what two independent readers (ray-optics, optiland) computed from the same files.

Operators: `lens_file_read`, `lens_file_system`, `lens_file_write`, `lens_file_report`

Pipeline: [`lens_file_read`](ops/optics/lensfile/lens_file_read.md) → [`lens_file_system`](ops/optics/lensfile/lens_file_system.md) → [`paraxial_trace`](ops/optics/design/paraxial_trace.md) → [`spot_stats`](ops/optics/design/spot_stats.md) → [`lens_file_write`](ops/optics/lensfile/lens_file_write.md)

Alternatives: [`lens_file_report`](ops/optics/lensfile/lens_file_report.md), [`read_glass_catalog_agf`](ops/optics/matprop/read_glass_catalog_agf.md), [`lens_system`](ops/optics/design/lens_system.md), [`optimize_lens`](ops/optics/optimization/optimize_lens.md), [`lens_section_drawing`](ops/optics/drawing/lens_section_drawing.md)

Runnable: `poc_lens_file_roundtrip`

### [One table of material optical constants (86 glasses, crystals, semiconductors, metals, liquids and plastics from primary literature, with a glass-catalogue importer)](capabilities/material-optical-property-library.md)

Sixteen ops in the new `matprop` category of `opsoptics`, backed by one record per material in `materials_data.py` (generated from the refractiveindex.info database, CC0: primary-literature coefficients and tables with their citation on every wavelength segment). 46 catalogue glasses from four makers, 12 crystals and IR materials, 6 semiconductors (Si with Green 2008 n,k and the Salzberg IR Sellmeier), 4 films, 10 metals, water and 4 plastics. Every curve comes back as `pairs` (λ nm, value) so sources, optics, targets and sensor QE share one shape. `read_glass_catalog_agf` reads the user's own .agf catalogues (all 13 .agf dispersion formulas, k from internal-transmittance lines); vendor catalogues are not bundled. Gates: catalogue n_d / V_d of all 46 glasses within 4e-6 / 0.005, the published Green 2008 and Johnson & Christy points, slab transmittance against the closed form, and optiland 0.6.3 as a second implementation at 23 points.

Operators: `material_table`, `material_record`, `material_optical_constants`, `material_dispersion`, `material_extinction`, `material_absorption`, `material_transmittance`, `material_reflectance`, `abbe_number`, `glass_map`, `thermo_optic_coefficient`, `plate_focus_shift`, `silicon_free_carrier_absorption`, `material_from_sellmeier`, `material_from_curves`, `read_glass_catalog_agf`

Runnable: `poc_material_optical_library`

### [Sorting look-alike foreign matter with NIR hyperspectral imaging (material absorption bands, scattering-layer reflectance, InGaAs band electrons)](capabilities/nir-hyperspectral-sorting.md)

Eight ops build the NIR sorting chain with the object and the optics reading the same material table: absorption bands for polymers, lipids, proteins, carbohydrates and lignin (and nut kernels, shells and wood as mixtures; water from the table's n,k), carbon black, the Kubelka–Munk reflectance of a scattering layer, reflectance from a material name with grain-size scattering and the Saunderson surface correction, an InGaAs QE from the direct-gap absorption edges, and the linear map from reflectance to electrons per band through a halogen lamp, the lens glass, the band filters and the QE. Gates: the Kubelka–Munk limits and inverse, measured polymer trough positions within 5 nm, water absorption within 10 % of Kou 1993, linearity and the EMVA variance of the captured cube, and the Fisher ratio's two-class closed form.

Operators: `material_nir_absorption`, `carbon_black_absorption`, `nir_model_info`, `ingaas_photodiode_qe`, `kubelka_munk_reflectance`, `spectral_reflectance_from_material`, `hyperspectral_band_weights`, `hyperspectral_capture`

Pipeline: [`material_nir_absorption`](ops/optics/matprop/material_nir_absorption.md) → [`kubelka_munk_reflectance`](ops/optics/spectral/kubelka_munk_reflectance.md) → [`hyperspectral_capture`](ops/optics/spectral/hyperspectral_capture.md)

Alternatives: [`spectral_reflectance_from_material`](ops/optics/spectral/spectral_reflectance_from_material.md), [`hyperspectral_band_weights`](ops/optics/spectral/hyperspectral_band_weights.md), [`ingaas_photodiode_qe`](ops/optics/spectral/ingaas_photodiode_qe.md), [`carbon_black_absorption`](ops/optics/matprop/carbon_black_absorption.md)

Runnable: `poc_hyperspectral_foreign_matter`

### [Non-coaxial optics (fold mirrors, beamsplitters, tilted plates, Scheimpflug and ghosts)](capabilities/noncoaxial-optics.md)

Thirteen ops in `raytrace3d` (category `noncoaxial` of `opsoptics`) give every surface of a sequential system a 3-D pose: coordinate breaks (decenter, then rotate about x, the new y, the new z; `undo` reverses one), returns to an earlier frame, fold mirrors, tilted or wedged plates and plate beamsplitters with a transmit and a reflect branch. Surfaces and the refraction / reflection law are `raytrace`'s own, so a coaxial prescription traces identically (1e-12). Ops report image orientation (reflections, handedness), both beamsplitter branches, closed-form tilted-plate shift and astigmatism, the Scheimpflug image tilt with a real-ray check, residual surface reflectance from the material table and thin-film stacks, and every two-reflection ghost (focus, size on the sensor, energy and irradiance ratios) as a table and an image. `optdraw.noncoaxial_drawing` draws folded systems to scale.

Operators: `noncoaxial_system`, `noncoaxial_example`, `noncoaxial_layout`, `noncoaxial_trace`, `noncoaxial_spot`, `image_orientation`, `beamsplitter_branches`, `tilted_plate_shift`, `scheimpflug_tilt`, `surface_reflectance`, `ghost_analysis`, `ghost_image`, `ghost_path`, `noncoaxial_drawing`

Pipeline: [`noncoaxial_system`](ops/optics/noncoaxial/noncoaxial_system.md) → [`noncoaxial_trace`](ops/optics/noncoaxial/noncoaxial_trace.md) → [`image_orientation`](ops/optics/noncoaxial/image_orientation.md) → [`ghost_analysis`](ops/optics/noncoaxial/ghost_analysis.md) → [`noncoaxial_drawing`](ops/optics/drawing/noncoaxial_drawing.md)

Alternatives: [`lens_system`](ops/optics/design/lens_system.md), [`spot_stats`](ops/optics/design/spot_stats.md), [`tilted_plate_shift`](ops/optics/noncoaxial/tilted_plate_shift.md), [`scheimpflug_tilt`](ops/optics/noncoaxial/scheimpflug_tilt.md), [`surface_reflectance`](ops/optics/noncoaxial/surface_reflectance.md), [`lens_section_drawing`](ops/optics/drawing/lens_section_drawing.md)

Runnable: `poc_noncoaxial_optics`

### [Compute reflection, refraction and interference](capabilities/optics-and-materials.md)

Fresnel reflectance, thin-film interference colour, grating colour, and vector-form refraction with a per-ray total-internal-reflection mask — with the dispersion of real glasses.

Operators: `fresnel_dielectric`, `thin_film_reflectance`, `grating_rgb`, `refract_rays`

Pipeline: [`fresnel_dielectric`](ops/optics/interface/fresnel_dielectric.md) → [`thin_film_reflectance`](ops/optics/appearance/thin_film_reflectance.md) → [`thin_film_rgb`](ops/optics/appearance/thin_film_rgb.md)

Alternatives: [`fresnel_conductor`](ops/optics/interface/fresnel_conductor.md), [`brewster_angle_deg`](ops/optics/interface/brewster_angle_deg.md), [`grating_rgb`](ops/optics/appearance/grating_rgb.md), [`refract_rays`](ops/optics/glassbody/refract_rays.md), [`fresnel_reflectance`](ops/3d/optics/fresnel_reflectance.md)

Runnable: `glass_and_mirror_optics`, `appearance_structural_colour`

### [Pixel-shift imaging (full colour from 1-pixel shifts, no aliasing from half-pixel shifts, and where it breaks)](capabilities/pixel-shift-imaging.md)

Six ops in `pixelshift` (category `pixelshift` of `opsoptics`): nominal shift sequences with actuator error, an exact box-aperture capture of a finely drawn scene through a shifted Bayer or monochrome sensor (optionally a different scene per frame for moving objects), a grid merge with the nominal shifts that refuses sequences that cannot fill the grid, a motion mask from disagreeing green samples with fallback to a single-frame demosaic, a false-colour metric, and the closed-form resolution budget (pixel-aperture sinc times diffraction MTF, Nyquist, Q = λN/p). The PoC shows false colour vanishing with 1-pixel shifts, aliasing vanishing with half-pixel shifts while the slanted-edge MTF50 stays put, the lens-limited regime where nothing is gained, and the failure modes: shift error, moving parts and stacking more frames. The lead chapter runs on real raw data (four pixel-shift frames from a 35 mm full-frame mirrorless camera with sensor shift, PixelShift200 by Qian et al., ICCP 2022, CC BY 4.0, a crop of a resolution chart): the camera cycles (0,0)→(1,0)→(1,−1)→(0,−1), and passing the op's default order instead flags 23.2 % of a static scene as moving (0.09 % with the right order); the merge matches the authors' own merged RGGB to a correlation of 0.99999996; false colour on the achromatic chart drops from 0.054 (single frame, bilinear) to 0.025; and a good demosaic (AHD in rawpy) comes within 1 % of the four-frame contrast on this chart, whose finest bars stop at 0.31 cyc/px.

Operators: `pixel_shift_pattern`, `pixel_shift_capture`, `pixel_shift_merge`, `pixel_shift_motion_mask`, `false_color_metric`, `pixel_shift_resolution_budget`

Pipeline: [`pixel_shift_resolution_budget`](ops/optics/pixelshift/pixel_shift_resolution_budget.md) → [`pixel_shift_pattern`](ops/optics/pixelshift/pixel_shift_pattern.md) → [`pixel_shift_capture`](ops/optics/pixelshift/pixel_shift_capture.md) → [`pixel_shift_motion_mask`](ops/optics/pixelshift/pixel_shift_motion_mask.md) → [`pixel_shift_merge`](ops/optics/pixelshift/pixel_shift_merge.md) → [`false_color_metric`](ops/optics/pixelshift/false_color_metric.md)

Alternatives: [`drizzle_resample`](ops/astrostack/stack/drizzle_resample.md), [`align_frames`](ops/astrostack/align/align_frames.md), [`raw_demosaic_bilinear`](ops/gfx2d/isp/raw_demosaic_bilinear.md)

Runnable: `poc_pixel_shift`

### [Remove specular reflection from a four-angle polariser sweep (dielectrics vs metals)](capabilities/polarisation-specular-removal.md)

Fit Malus's law per pixel to a 0/45/90/135° polariser sweep and split the radiance into its unpolarised part (2·I_min) and its linearly polarised part (I_max − I_min). Calling those "diffuse" and "specular" is a physical assumption that holds for dielectrics near Brewster's angle and fails for metals; this entry keeps the two cases apart.

Operators: `polarization_dolp_map`, `polarization_separate`, `polarization_stokes`, `specular_diffuse_split`

Pipeline: [`polarization_dolp_map`](ops/specular/polarization/polarization_dolp_map.md) → [`polarization_separate`](ops/specular/polarization/polarization_separate.md) → [`polarization_stokes`](ops/specular/polarization/polarization_stokes.md) → [`stokes_analyze`](ops/optics/polarization/stokes_analyze.md) → [`specular_diffuse_split`](ops/specular/dichromatic/specular_diffuse_split.md)

Alternatives: [`fresnel_conductor`](ops/optics/interface/fresnel_conductor.md), [`fresnel_dielectric`](ops/optics/interface/fresnel_dielectric.md), [`brewster_angle_deg`](ops/optics/interface/brewster_angle_deg.md), [`specular_free_transform`](ops/specular/dichromatic/specular_free_transform.md), [`specular_coefficient_map`](ops/specular/dichromatic/specular_coefficient_map.md)

Runnable: `example_polarization_metal`, `poc_polarization_specular`, `specular_photometric`

### [Read a polarisation camera's raw frame into Stokes, DoLP and Mueller](capabilities/polarization-imaging.md)

Turn a polarisation camera's mosaic (a 2×2 block of 0/45/90/135° analysers, as on commercial on-chip polarisation sensors) into four full-resolution images with `polarization_demosaic` (bilinear, exact on affine fields, phase-preserving mirrored border) that chain straight into `polarization_stokes` / `polarization_dolp_map`. Recover a sample's Mueller matrix from intensities measured through known generator/analyser states with `mueller_from_intensities` (linear least squares on `outer(a_i, g_i)`; refuses rank-deficient designs with the rank instead of returning a pseudo-inverse guess). Check any 4×4 matrix with `mueller_checks`: Cloude coherency eigenvalues (physical), purity, the Gil–Bernabeu depolarisation index and passivity.

Operators: `polarization_demosaic`, `polarization_demosaic_color`, `polarization_stokes`, `polarization_dolp_map`, `polarization_separate`, `stokes_analyze`, `mueller_from_intensities`, `mueller_checks`, `mueller_element`, `mueller_apply`

Runnable: `polarization_camera_pipeline`, `poc_polarization_specular`

### [Turn a Bayer raw frame into a display image, one explainable stage at a time](capabilities/raw-to-display-isp.md)

The classic ISP stages, each a closed form you can state: black level, dead-pixel detection/correction (a pixel that departs from all eight same-colour neighbours in the same direction), lens-shading gain from a flat field (per colour channel), white-balance gains (gray-world / white-patch) applied on the mosaic or on RGB, a NumPy-only bilinear demosaic (exact on affine fields, phase-preserving mirrored border), a row-normalised colour-correction matrix (white stays white), hue/saturation in BT.601 YCbCr, and brightness/contrast about mid-grey. For inspection work, explainability and repeatability matter more than the polish of a learned ISP.

Operators: `raw_black_level`, `raw_dead_pixel_mask`, `raw_dead_pixel_correct`, `lens_shading_gain`, `lens_shading_correct`, `awb_gains`, `raw_apply_gains`, `rgb_apply_gains`, `raw_demosaic_bilinear`, `color_correction_matrix`, `hue_saturation`, `brightness_contrast`, `cfa_to_rgb`, `gamma`

Runnable: `raw_to_display_isp`

### [The spectral chain source × object × sensor (Planck, CIE A, LEDs, filters, Si QE, curve products and integrals)](capabilities/spectral-radiometry-chain.md)

Nine ops in `spectralrad` complete the spectral chain image = source × optics/object × sensor QE, all as `pairs` (λ nm, value) like the material curves: Planck blackbody (SI 2019 constants), CIE illuminant A (the defining formula), LED spectra (Ohno 2005 or Gaussian, width solved to the requested FWHM), a super-Gaussian band-pass filter, the Si photodiode QE from the material table's Si n,k, the energy-to-photon conversion, and curve product, integral and summary. Gates: the CIE A table, Wien and Stefan–Boltzmann, the QE closed form and its thick-detector limit, and Poisson statistics in the rendered images.

Operators: `blackbody_spectrum`, `cie_illuminant_a`, `led_spectrum`, `bandpass_spectrum`, `silicon_photodiode_qe`, `energy_to_photons`, `spectral_product`, `spectral_integral`, `spectral_stats`

Runnable: `poc_nir_silicon_transmission`

### [TDI line-scan cameras and line-scan lenses (stages and SNR, synchronisation MTF, illumination and MTF across the image height)](capabilities/tdi-linescan-and-lens.md)

Six ops in `linescan`: the SNR of an N-stage TDI sensor from the EMVA 1288 linear model (charge-domain and digital-domain summation), the closed-form MTF of a synchronisation error and of a yawed web, an acquisition that transports a reflectance map past a TDI line sensor (speed error, yaw, weave, encoder sync, per-column lens illumination and blur, EMVA 1288 noise), and a ray-traced profile of a finite-conjugate lens across the image height whose relative illumination splits exactly into cos⁴ × pupil × distortion, with sagittal and tangential MTF. Two example lenses (the same triplet optimised for a 57 mm line and for a 2/3-inch format) show why a C-mount lens on a long line sensor goes dark and soft at the ends, and that flat-field correction restores the brightness but not the MTF.

Operators: `tdi_snr`, `tdi_sync_mtf`, `linescan_acquire`, `lens_field_profile`, `linescan_lens_columns`, `linescan_lens_example`

Pipeline: [`tdi_snr`](ops/optics/linescan/tdi_snr.md) → [`tdi_sync_mtf`](ops/optics/linescan/tdi_sync_mtf.md) → [`linescan_lens_example`](ops/optics/linescan/linescan_lens_example.md) → [`lens_field_profile`](ops/optics/linescan/lens_field_profile.md) → [`linescan_lens_columns`](ops/optics/linescan/linescan_lens_columns.md) → [`linescan_acquire`](ops/optics/linescan/linescan_acquire.md)

Alternatives: [`lens_system`](ops/optics/design/lens_system.md), [`emva_snr_curve`](ops/optics/sensorchar/emva_snr_curve.md), [`relative_illumination`](ops/optics/geometric/relative_illumination.md)

Runnable: `poc_tdi_linescan`

### [Thin-film thickness by spectral reflectometry (transfer matrix, interference colour, FFT, model fit, thickness maps)](capabilities/thin-film-reflectometry.md)

Five ops in `filmoptics` (category `film`), with every film and substrate given by its key in the material table: the transfer-matrix reflectance, transmittance and absorptance of a multilayer stack (oblique incidence, s/p, the angular average of a focusing NA, conformal roughness), the interference colour against thickness (the wafer colour chart, in sRGB and CIELAB under D65 or any illuminant), thickness from the fringe period by FFT (dispersion-corrected, with the closed-form lower limit 2/Δx), thickness by a non-linear least-squares fit of the transfer-matrix model (global grid then golden-section refinement, all local candidates returned), and per-pixel thickness maps from a spectral or an RGB image together with a map of how many thicknesses fit equally well.

Operators: `multilayer_reflectance`, `film_color`, `film_thickness_fft`, `film_thickness_fit`, `film_thickness_map`

Pipeline: [`multilayer_reflectance`](ops/optics/film/multilayer_reflectance.md) → [`film_thickness_fft`](ops/optics/film/film_thickness_fft.md) → [`film_thickness_fit`](ops/optics/film/film_thickness_fit.md) → [`film_thickness_map`](ops/optics/film/film_thickness_map.md)

Alternatives: [`thin_film_reflectance`](ops/optics/appearance/thin_film_reflectance.md), [`film_color`](ops/optics/film/film_color.md)

Runnable: `poc_thin_film_reflectometry`

### [How water looks in inspection images (caustics on a pool floor, a bottle seen from the side with its fill line, a wet surface, a hull seen through water)](capabilities/water-inspection-images.md)

Seven ops in `watervision` (category `watervision` of `opsoptics`) turn the water physics of `watermedia` into the pictures an inspection camera records. `caustic_irradiance` gives the irradiance a collimated light leaves on a floor below a wavy surface by a photon count (vector Snell refraction, bilinear splatting, energy conserved) or by the Jacobian of the surface-to-floor map (inf and a flag at the folds); `caustic_floor_segmentation` cuts the bright web out of it so that a crack detector is not fooled. `bottle_image` ray-casts the horizontal section of every image row of a bottle (glass wall, liquid with a meniscus, bubbles; Snell, Fresnel, total internal reflection) backlit or frontlit, and `fill_level_from_image` reads the fill line back. `wet_surface_appearance` is the Lekner and Dorf (1988) model of why a wet surface is darker (trapped light: a (1 - R_s)(1 - r) / (1 - a r)) and glossier; `wet_dry_inspection_pair` renders one textured plate dry and wet and returns the defect contrast; `underwater_inspection_image` is a lamp-at-the-camera hull view with the backscatter veil and the per-pixel SNR.

Operators: `caustic_irradiance`, `bottle_image`, `fill_level_from_image`, `wet_surface_appearance`, `wet_dry_inspection_pair`, `underwater_inspection_image`, `caustic_floor_segmentation`

Pipeline: [`caustic_irradiance`](ops/optics/watervision/caustic_irradiance.md) → [`caustic_floor_segmentation`](ops/optics/watervision/caustic_floor_segmentation.md)

Alternatives: [`bottle_image`](ops/optics/watervision/bottle_image.md), [`fill_level_from_image`](ops/optics/watervision/fill_level_from_image.md), [`wet_surface_appearance`](ops/optics/watervision/wet_surface_appearance.md), [`wet_dry_inspection_pair`](ops/optics/watervision/wet_dry_inspection_pair.md), [`underwater_inspection_image`](ops/optics/watervision/underwater_inspection_image.md)

Runnable: `poc_water_inspection_images`

### [Water and transparent media (ocean waves, Fresnel and refraction at the surface, colour and scattering under water, a bottle as a lens)](capabilities/water-transparent-media.md)

Ten ops in `watermedia` (category `watermedia` of `opsoptics`): the wave spectrum of a wind sea (Pierson-Moskowitz, JONSWAP) and a Tessendorf FFT sea with slopes, normals, choppiness and finite depth; Fresnel reflectance and transmittance of the air-water interface with the dispersive index of the material table; Snell's window and the apparent depth; the apparent position of an underwater point as a stationary point of the optical path (bisection on a flat surface, Newton iteration with the vector Snell law verified on a wavy one); pure-water absorption (Pope & Fry 1997), scattering (Smith & Baker 1981) and the diffuse attenuation of the Jerlov water types (Solonenko & Mobley 2015); underwater image formation (Akkaynak & Treibitz 2018); the Henyey-Greenstein and Petzold phase functions; and the paraxial focus and real-ray caustic of a cylinder. Inputs outside a table, unknown water types, |g| >= 1 and n <= 1 are refused; a path that does not satisfy Snell's law is returned as NaN.

Operators: `ocean_spectrum`, `ocean_height_field`, `fresnel_water_air`, `snell_window`, `refracted_view`, `water_attenuation`, `underwater_image`, `phase_function_hg`, `scattering_phase_petzold`, `cylinder_lens_caustic`

Pipeline: [`ocean_height_field`](ops/optics/watermedia/ocean_height_field.md) → [`refracted_view`](ops/optics/watermedia/refracted_view.md) → [`water_attenuation`](ops/optics/watermedia/water_attenuation.md) → [`underwater_image`](ops/optics/watermedia/underwater_image.md)

Alternatives: [`ocean_spectrum`](ops/optics/watermedia/ocean_spectrum.md), [`fresnel_water_air`](ops/optics/watermedia/fresnel_water_air.md), [`snell_window`](ops/optics/watermedia/snell_window.md), [`phase_function_hg`](ops/optics/watermedia/phase_function_hg.md), [`scattering_phase_petzold`](ops/optics/watermedia/scattering_phase_petzold.md), [`cylinder_lens_caustic`](ops/optics/watermedia/cylinder_lens_caustic.md)

Runnable: `poc_water_transparent_media`

## Waves and signals (5)

### [Beamform for direction, separate range from velocity](capabilities/beamforming-and-range-doppler.md)

Form beams from an array snapshot to get directions of arrival, and build a range-Doppler map from an FMCW return, mapping detections back to metres and metres per second.

Operators: `beamform_delay_sum`, `beamform_doa`, `range_doppler_map`, `range_doppler_peaks`

Pipeline: [`beamform_doa`](ops/rangedoppler/beamform/beamform_doa.md) → [`range_doppler_map`](ops/rangedoppler/process/range_doppler_map.md) → [`range_doppler_peaks`](ops/rangedoppler/process/range_doppler_peaks.md)

Alternatives: [`beamform_delay_sum`](ops/rangedoppler/beamform/beamform_delay_sum.md)

Runnable: `poc_multibeam_bathymetry`, `poc_bev_sensor_fusion`

### [One beat (membrane modes, fringes, diffraction orders, print moire, and turning tone into ink)](capabilities/beats-fringes-and-screens.md)

Build membrane eigenmodes and nodal lines, two-slit fringes, grating orders, and the printing side (halftone screens, moire, engraving lines, structure-following hatching, mosaic tiles) — and score every one of them against a truth that lives outside the picture. The thesis: a two-slit fringe and the moire of two superposed halftone screens are **the same beat**, the difference of two frequency vectors, so one formula is checked from both ends. Rectangular membrane eigenvalues match `pi^2 (m^2/a^2 + n^2/b^2)` to 0.00e+00 including the degeneracies (the widely quoted `mn*pi` is a *product* and is a different sequence); circular nodal circles sit at the zeros of `J0` (the zeros of `J'0` are the antinodes); the fringe period `lambda*D/d` is measured back by a *different* op (ratio 0.998-1.003); grating orders round-trip through the existing `grating_wavelengths` to 550.000000 nm and agree with the existing `fraunhofer_pattern`, where a 50 % duty grating drops the even orders and the 3rd/1st intensity ratio is `sinc(m/2)^2` = 1/9; the moire period is predicted before drawing and confirmed by FFT (0.948-0.986); halftoning discards tone but preserves local mean density (0.0517 mean absolute error through a 4-period window); engraving ink coverage matches the closed form `w/d` to 0.0000; hatch direction comes from the existing `structure_tensor_orientation` and lands within 0.3 degrees of a grating whose angle is known by construction; and Lloyd's energy, measured by the existing `stipple_energy`, decreases monotonically with the cell mean being the exact L2 optimum.

Operators: `wave_membrane_mode`, `wave_mode_frequencies`, `wave_nodal_lines`, `wave_two_slit`, `wave_fringe_period`, `wave_grating_orders`, `halftone_screen`, `halftone_moire_period`, `engrave_lines`, `hatch_field`, `mosaic_tiles_sites`, `mosaic_tiles_render`

Runnable: `poc_beats_fringes_and_screens`

### [Cavity optics, the quantum-noise budget and a known waveform in coloured noise, in closed form (the gravitational-wave detector's equations for inspection interferometers, vibrometers and AE)](capabilities/gw-interferometer-quantum-noise-and-matched-filter.md)

Twelve ops in two ledgers. Optics (`opsoptics`, category `cavity`): `fabry_perot_response` (FSR, finesse, linewidth, pole and power gain from mirror transmittances; the public aLIGO design values give F ≈ 445 and a 42 Hz pole), `cavity_strain_transfer` (single pole times the round-trip sinc), `michelson_dc_readout` (DC-readout power, strain slope and the shot-noise limit (1/2L)√(ħcλ/πP)), `pdh_error_signal` (Pound-Drever-Hall, antisymmetric, slope of Black 2001 eq. 15) and `quantum_noise_budget` (Kimble et al. 2001: shot, radiation pressure and the SQL, with the identity shot × rp = SQL²/2). Signals (`ops1d`, category `matched`): `psd_welch`, `whiten_by_psd`, `matched_filter_snr`, `optimal_snr`, `chirp_newtonian`, `chirp_mass_from_track`, `coincidence_delay`. The PoC runs the pipeline on the public GW150914 data and reproduces the published figure (correlation 0.96 / 0.94), the SNRs 19.0 / 13.1 against ≈ 20 / 13 and the 7 ms arrival delay; the second implementation gwinc agrees within 4–12 %.

Operators: `fabry_perot_response`, `cavity_strain_transfer`, `michelson_dc_readout`, `pdh_error_signal`, `quantum_noise_budget`, `psd_welch`, `whiten_by_psd`, `chirp_newtonian`, `chirp_mass_from_track`, `matched_filter_snr`, `optimal_snr`, `coincidence_delay`

Runnable: `poc_gw_detector_pseudo_simulation`

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

## Compose (7)

### [Align and stack](capabilities/align-and-stack.md)

Align a sequence by voting for the translation, resample sub-pixel, and stack. Point clouds are aligned with ICP.

Operators: `frame_align`, `drizzle_resample`, `icp_point2point_3d`, `interp_scattered`

Pipeline: [`align_frames`](ops/astrostack/align/align_frames.md) → [`drizzle_resample`](ops/astrostack/stack/drizzle_resample.md) → [`frame_quality`](ops/astrostack/quality/frame_quality.md)

Alternatives: [`frame_align`](ops/astrostack/align/frame_align.md), [`icp_point2point_3d`](ops/3d/refine/icp_point2point_3d.md), [`register_cross`](ops/3d/fusion/register_cross.md), [`interp_scattered`](ops/math/interp_poly/interp_scattered.md)

Runnable: `poc_astro_photometry`, `poc_registration_basin`

### [Compare against a golden image — align, diff, count defects, judge the lot](capabilities/golden-compare.md)

`compare_to_golden(image, golden)` turns "find what differs from a known-good part" into one call: estimate the integer translation by phase correlation (estimates beyond `max_shift` are not applied and flagged `align_ok=0`), optionally Gaussian-smooth both images, take `|image − golden|`, threshold it inside the inspection `mask`, label the connected components and drop those under `min_area`. It returns a measurement dict (`shift_row`, `shift_col`, `align_ok`, `ssim`, `psnr`, `max_diff`, `mean_diff`, `defect_area`, `defect_count`, `defect_area_max`, `valid_fraction`) plus the pictures (`diff`, `defect_mask`, `labels`, `valid`). Border pixels wrapped in by the alignment are excluded from every count. `golden_measure(golden, ...)` makes the `measure` callable for `inspect_batch` and `golden_spec(...)` the matching `judge` spec, so pointing at a folder inspects the whole lot against the golden. Mismatched shapes, non-2-D or non-finite images, a mask of the wrong shape and `min_area < 1` raise `ValueError` — never a silent zero-defect result.

Operators: `compare_to_golden`, `golden_measure`, `golden_spec`, `inspect_batch`, `judge`, `ssim`, `psnr`

Runnable: `golden_compare`

### [Validate a recipe and spec on known good/bad sets before deployment, and measure the margins](capabilities/inspection-fixture.md)

`inspection_fixture(good, bad, recipe, measure=..., spec=...)` runs the known-good and known-bad sets through `inspect_batch` and returns `passed=True` only when every good part is `ok` and every bad part is `ng`. It lists the confusion counts, the escaped bad parts (`escapes`), the falsely rejected good parts (`false_rejects`) and unreadable rows (`errors`), and `spec_margins` reports per spec key how close the good measurements come to the limits (`min_margin` in spec units, negative when exceeded; `min_margin_norm` normalised by the tolerance or half the min–max width, so 1.0 means one limit-width of headroom). An empty set raises `ValueError`, an unreadable file becomes an `error` that fails the fixture, and a misspelled spec raises. With `report_path` the two sets are written to separate `_good` / `_bad` reports.

Operators: `inspection_fixture`, `spec_margins`, `inspect_batch`, `judge`

Runnable: `inspection_fixture`

### [Inspect a folder in one call — batch, judge against a spec, aggregate, SPC, report, audit log](capabilities/inspection-workflow.md)

`inspect_batch(folder, recipe, measure=..., spec=...)` is the one call a line operator reaches for first: every image in the folder (or path list, in deterministic order) is loaded, run through the `recipe` (the same stages `run_pipeline` takes), measured by your `measure` callable (any bundle of measurement ops returning a dict) and judged against `spec`. Each row carries the input file's sha256, the measurements, an evidence-carrying `Verdict` and the elapsed time; numeric columns become series and, with two or more points, an EWMA control-chart summary; `report_path` writes `.xlsx` / `.md` / `.jsonl` by extension and `audit_path` appends one JSON line per row. `judge(measurements, spec)` is the entry that turns measurements into the PLC vocabulary (`ok` / `ng` / `error`) with the list of violations and a one-line reason — rules are `min`/`max`, `nominal`±`tol` (inclusive), `eq` and `in`. It never passes silently: missing keys, NaN/inf and non-numeric values are `error`, a misspelled rule is a `ValueError`, a broken image becomes an `error` row without stopping the batch, and an empty batch is refused.

Operators: `inspect_batch`, `judge`, `as_verdict`, `run_pipeline`, `spc_ewma`, `save_xlsx_report`, `report`, `to_json_lines`

Runnable: `inspection_workflow`

### [Write typed op results as JSON and read them back bit-for-bit](capabilities/typed-results-as-json.md)

One JSON form per sort and one way back: a self-describing envelope, float arrays as base64 little-endian float64 (bit-exact round trips, tested with the same probes the op gates use), run-length regions, contours as shape plus point lists, tables as plain JSON. Thin conveniences ride along — `save_json` / `load_json` for a file, `to_json_lines` / `from_json_lines` for a growing ledger as JSON Lines. Unknown sorts, shapes that do not fit the sort and wrong envelope versions are refused — nothing is guessed from an array's shape.

Operators: `to_json`, `from_json`, `to_jsonable`, `from_jsonable`, `save_json`, `load_json`, `to_json_lines`, `from_json_lines`, `as_value`, `apply_json`, `is_envelope`

Runnable: `typed_results_json`

### [Render typed op results as Markdown, with an exact JSON block to read back](capabilities/typed-results-as-markdown.md)

The Markdown companion of jsonio. `to_markdown` renders a typed value as GFM — real tables for tabular and small numeric sorts (capped, with a truncation note), a one-line summary for things that are not text (an image is its shape and range). `json_block` wraps the exact JSON envelope in a ```` ```json ```` fence so a value survives inside prose and round-trips bit-for-bit through `extract_json`, which pulls every fullseye envelope out of a Markdown string and ignores foreign fences. `report` folds a list of sections into one document that is both readable and, with `with_json=True`, machine-recoverable. Fail-closed on an unknown sort, exact wherever a machine reads it back.

Operators: `to_markdown`, `json_block`, `extract_json`, `report`

Runnable: `typed_results_markdown`

### [Write typed inspection results to an Excel (.xlsx) report](capabilities/xlsx-report.md)

`save_xlsx_report(sections, path)` writes the same `(heading, value, sort)` sections that `mdio.report` renders as Markdown, but as a real Excel workbook: tabular sorts (`table`, `points`, `matrix`, `signal`, `vector`, `keypoints`, `counts`) become spreadsheet cells, `feature` / `scalar` a single cell, and image-like sorts (`image`, `color`, `region` …) an embedded thumbnail. jsonio is the machine-exact JSON, mdio the human-readable Markdown, and xlsxio the shop-floor Excel — the same one `sections` list feeds all three, only the destination differs. It uses openpyxl (the optional `xlsx` extra) and raises a clear `ImportError` when it is missing rather than silently degrading; an image that cannot be embedded falls back to a one-line shape/range cell so a thumbnail never breaks the report (fail-soft). Unknown sorts raise `ValueError`.

Operators: `save_xlsx_report`, `report`, `to_markdown`, `save_json`

Runnable: `xlsx_report`

## Show (5)

### [Turn results into figures people can read](capabilities/figures-and-annotation.md)

Panel grids, dimension and pointer annotations, height pseudo-colour, and a full SDF renderer — all from Fullseye operators, so a result becomes a figure without a plotting library in between.

Operators: `annotate_figure_grid`, `colorize_height`, `render_beauty`

Pipeline: [`annotate_figure_grid`](ops/annotate/paper/annotate_figure_grid.md) → [`annotate_panel_label`](ops/annotate/paper/annotate_panel_label.md) → [`annotate_scale_bar`](ops/annotate/paper/annotate_scale_bar.md) → [`annotate_colorbar`](ops/annotate/paper/annotate_colorbar.md)

Alternatives: `colorize_height`, [`render_beauty`](ops/3d/render/render_beauty.md), [`annotate_legend`](ops/annotate/paper/annotate_legend.md), [`annotate_inset`](ops/annotate/paper/annotate_inset.md)

Runnable: `poc_colormap_readability`, `poc_dem_terrain`

### [Turn results into one self-contained page you can touch (tabs, badges, 3-D, video, languages)](capabilities/interactive-poc-viewer.md)

`write_viewer(spec, path, lang=...)` writes one self-contained HTML page (dark theme, plain WebGL and 2-D canvas, no libraries, no external loads; works from `file://` and on iPhone Safari). Tabs hold the same task attempted by different methods; each carries an honest badge (`passed` / `limit` / `null`), a short text and measured numbers. Payloads: a triangle mesh with per-vertex scalar colour and a colour bar; a point cloud (scalar or RGB colour, optional grey ghost cloud); a 2-D frame sequence with overlaid boxes and a thresholded time-series plot; a before/after pair with a draggable split. `lang` is a code or a list (first is the default) from ja, en, zh, tw, ko, de, hi, fr; every requested language must be present for every string or `ValueError` names the missing keys (no silent fallback). Data is quantised, never decimated: positions as per-axis uint16, values as uint16 over the colour-bar range, images and indices lossless. Standard library and NumPy only. The same call is available as the MCP tool `fullseye_write_viewer`.

Operators: `write_viewer`, `viewer_spec`, `viewer_points_tab`, `viewer_mesh_tab`, `viewer_frames_tab`, `viewer_split_tab`

Runnable: `interactive_poc_viewer`

### [Draw lines and regions without knowing the background colour](capabilities/inverted-colour-overlays.md)

Draw a polyline or a region in the inverse of whatever is underneath, so the overlay stays visible without knowing the background. `draw="margin"` outlines instead of filling. The one real failure mode — mid-grey, where the complement equals the original — is measured rather than assumed: `annotate_invert_visibility` reports the per-pixel WCAG contrast, and the drawing ops warn (or refuse) when the mark would be invisible.

Operators: `annotate_invert`, `annotate_invert_path`, `annotate_invert_visibility`

Pipeline: [`annotate_invert_visibility`](ops/annotate/overlay/annotate_invert_visibility.md) → [`annotate_invert`](ops/annotate/overlay/annotate_invert.md) → [`annotate_invert_path`](ops/annotate/overlay/annotate_invert_path.md)

Alternatives: [`annotate_legend`](ops/annotate/paper/annotate_legend.md), [`text_box`](ops/annotate/text/text_box.md)

Runnable: `annotate_paper_tour`

### [Draw a point cloud as a colour picture](capabilities/point-cloud-to-picture.md)

Draws a point cloud that has no surface — cell positions, LiDAR returns, sparse SfM points, particles — as an RGB image. Each point drops a sub-pixel footprint (gaussian / disc / point) that is alpha-composited in depth order (over) or added with the total light conserved (add, a density map). The camera follows the OpenCV convention of `project_points` / `render_point_depth`; an orthographic render fits the cloud to the image when K is omitted.

Operators: `points_render`, `render_point_depth`, `project_points`

Pipeline: [`points_render`](ops/3d/render/points_render.md)

Alternatives: [`render_point_depth`](ops/3d/render/render_point_depth.md), [`points_activity_video`](ops/conngraph/activity/points_activity_video.md), [`gs_render`](ops/drive/gsplat/gs_render.md), `render_mesh`

Runnable: `points_render_basics`, `poc_flybrain_pointcloud`

### [Put text and tables exactly where you want them on an image](capabilities/text-and-tables-on-images.md)

Place text on an image where you actually want it: nine-way anchors, translucent plates, wrapping, and — along a polyline — slanted, vertical (`upright=True`), multi-line (`\n`), start/centre/end alignment and a perpendicular offset. Colour, plus synthetic bold and italic. `annotate_table` turns a tab-separated string into a table whose column widths are **measured with the real font at the requested size**, with a font-size-proportional column gap, automatic right-alignment for numeric columns and a translucent plate. Every one has a `*_layout` twin that returns the geometry so you can check the placement before drawing.

Operators: `text_box`, `annotate_text_path`, `annotate_text_path_layout`, `annotate_table`, `annotate_table_layout`, `measure_text`

Pipeline: [`measure_text`](ops/annotate/text/measure_text.md) → [`annotate_text_path_layout`](ops/annotate/paper/annotate_text_path_layout.md) → [`annotate_text_path`](ops/annotate/paper/annotate_text_path.md) → [`annotate_table_layout`](ops/annotate/paper/annotate_table_layout.md) → [`annotate_table`](ops/annotate/paper/annotate_table.md)

Alternatives: [`text_box`](ops/annotate/text/text_box.md), [`annotate_panel_label`](ops/annotate/paper/annotate_panel_label.md)

Runnable: `annotate_paper_tour`

## Draw (5)

### [Turn a photograph into a single line (stipple, tour, rotating circles)](capabilities/one-stroke-drawing.md)

Turn the tone of a picture into a single closed line a pen could draw without lifting: points are placed by darkness (weighted Lloyd), ordered into a closed tour, resampled at equal arc length, and rewritten as a chain of rotating circles via the complex Fourier series. Nothing is judged by eye. The stipple is checked against a ramp (correlation 0.9946) with a flat image as the control — and the *exponent* is measured too, because a centroidal Voronoi tessellation puts density at sqrt(rho), not rho (Gersho): 0.61 measured, 0.77 with the weight squared. The tour is checked against the minimum spanning tree, which no closed tour can beat (1.146, against 41.4 for coordinate order); the tone is measured (0.984, against +0.013 for random points); the pen width that reproduces the mean tone is solved in closed form and falls 11 % short, which *is* the stroke overlap; the resampling is checked against Nyquist (the error falls as 1/N: 6.5, 3.3, 1.6 % of the stroke length); and Parseval turns the number of circles into a prediction made before the drawing exists.

Operators: `stipple_points_from_image`, `stipple_energy`, `stroke_tour_closed`, `mst_length`, `stroke_resample_closed`, `stroke_tone_error`, `contour_fourier_complex`, `contour_epicycle_chain`, `contour_fourier_truncation_energy`

Runnable: `poc_one_stroke_epicycles`

### [Optical drawings (lens layouts, vision-setup drawings and ISO 10110 element drawings as SVG / DXF)](capabilities/optics-drawings.md)

Eight ops in `optdraw` (category `drawing` of `opsoptics`) that draw what the optics ops compute: a meridional lens layout from a `raytrace` prescription (conic + aspheric sags, edges, stop, image plane, real rays aimed at the stop and coloured by field, EFL / BFL / track / image-height dimensions, a prescription table), a side + top view of a machine-vision setup from `vision_layout` (field-of-view cone, working distance, depth-of-field band, five light families with positions and elevation angles), and an ISO 10110-style element drawing whose tolerances come from the `tolerance_analysis` dictionary. Writers for SVG and DXF R12 use only the standard library; readers bring coordinates and text back so the gates score the written file, not the picture.

Operators: `lens_section_drawing`, `vision_setup_drawing`, `lens_element_drawing`, `drawing_svg`, `drawing_dxf`, `drawing_raster`, `svg_entities`, `dxf_entities`

Pipeline: [`lens_section_drawing`](ops/optics/drawing/lens_section_drawing.md) → [`drawing_svg`](ops/optics/drawing/drawing_svg.md) → [`drawing_dxf`](ops/optics/drawing/drawing_dxf.md) → [`svg_entities`](ops/optics/drawing/svg_entities.md) → [`dxf_entities`](ops/optics/drawing/dxf_entities.md)

Alternatives: [`vision_setup_drawing`](ops/optics/drawing/vision_setup_drawing.md), [`lens_element_drawing`](ops/optics/drawing/lens_element_drawing.md), [`drawing_raster`](ops/optics/drawing/drawing_raster.md), [`paraxial_trace`](ops/optics/design/paraxial_trace.md), [`tolerance_analysis`](ops/optics/design/tolerance_analysis.md)

Runnable: `poc_optics_drawings`

### [Photographing a 3-D scene through the actual lens prescription (depth of field, cat's-eye bokeh, corner illumination, colour fringes, ghosts)](capabilities/photograph-through-prescription.md)

Eight ops in `lensrender` (category `lensrender` of `opsoptics`) photograph a 3-D scene through a `raytrace.lens_system` prescription by sensor-side ray tracing (Kolb, Mitchell & Hanrahan 1995): the exit pupil is sampled for every sensor point, each ray is traced backwards through every surface (Snell's law with dispersion, conics and aspheres, mirrors, semi-diameters as stops, total internal reflection) into object space, the scene is shaded there (textured planes, spheres, triangle meshes, Lambertian plus a Blinn-Phong lobe, shadows, point sources splatted by forward tracing) and the radiance is summed with the weight cos^2(theta)/d^2 of the pupil sample. The irradiance becomes electrons (E dlambda A t (lambda/hc) QE) and goes through shot noise, dark electrons, read noise and the quantiser. `bokeh_shape` gives the out-of-focus footprint (the cat's eye), `render_ghost_overlay` adds the two-reflection ghosts of a bright point and `render_compare_prescriptions` renders one scene through several prescriptions and tabulates RMS spots, corner illumination, distortion, lateral colour and the edge rise and MTF50. Geometric optics only: no diffraction.

Operators: `lens_scene`, `exit_pupil_samples`, `trace_sensor_rays`, `scene_radiance`, `render_scene_through_lens`, `bokeh_shape`, `render_ghost_overlay`, `render_compare_prescriptions`

Pipeline: [`lens_system`](ops/optics/design/lens_system.md) → [`lens_scene`](ops/optics/lensrender/lens_scene.md) → [`render_scene_through_lens`](ops/optics/lensrender/render_scene_through_lens.md) → [`render_compare_prescriptions`](ops/optics/lensrender/render_compare_prescriptions.md)

Alternatives: [`exit_pupil_samples`](ops/optics/lensrender/exit_pupil_samples.md), [`trace_sensor_rays`](ops/optics/lensrender/trace_sensor_rays.md), [`scene_radiance`](ops/optics/lensrender/scene_radiance.md), [`bokeh_shape`](ops/optics/lensrender/bokeh_shape.md), [`render_ghost_overlay`](ops/optics/lensrender/render_ghost_overlay.md), [`render_through_lens`](ops/optics/imaging_sim/render_through_lens.md), [`ghost_analysis`](ops/optics/noncoaxial/ghost_analysis.md)

Runnable: `poc_photograph_through_prescription`

### [Pictures that carry their own ground truth (illusions, endless drawing, seamless loops)](capabilities/pictures-that-carry-their-own-truth.md)

Generates pictures that ship with their own ground truth: optical illusions whose denied invariant is exact (parallel, equal-length, identical-valued), endless generative systems whose correctness is an identity rather than an appearance, and seamless loops where the seam is absent by construction rather than removed by editing.

Operators: `illusion_cafe_wall`, `illusion_muller_lyer`, `illusion_checker_shadow`, `illusion_kanizsa`, `illusion_fraser_spiral`, `illusion_ground_truth`, `perpetual_elementary_ca`, `perpetual_langtons_ant`, `perpetual_apollonian`, `perpetual_flow_field`, `perpetual_identities`, `perpetual_state`, `perpetual_step`, `perpetual_render`, `perpetual_loop`, `perpetual_loop_seam`

Runnable: `poc_illusions_and_perpetual_drawing`

### [Theorems as pictures (Apollonian, Ford, geodesic dome, phyllotaxis, IFS, space-filling curves)](capabilities/theorems-as-pictures.md)

Draw mathematically beautiful figures whose correctness is asserted by a theorem rather than by eye: an Apollonian gasket (every tangent quadruple satisfies Descartes' circle theorem to 1e-13, and an integral seed stays integral for ever), Ford circles (tangency agrees with `|ps - qr| = 1` on all 1,081 pairs, and the count matches `1 + sum of Euler's totient`), a geodesic dome (exactly 12 degree-5 vertices at every subdivision — counted by the existing `graph_degree_table`, not by this module), Vogel's phyllotactic spiral (neighbour index gaps land on Fibonacci numbers only at the golden angle: 7/7 against 2/7 for the controls), IFS attractors (Moran's closed-form dimension agrees with the existing box-counting `fractal_dimension`, and non-similarity maps are refused), and space-filling curves (a permutation of 4^n cells with unit steps; locality reported as a table, not a slogan).

Operators: `circle_packing_apollonian`, `ford_circles`, `phyllotaxis_pattern`, `neighbour_index_gaps`, `ifs_fractal`, `ifs_similarity_dimension`, `space_filling_curve`, `curve_locality`, `geodesic_dome`

Runnable: `poc_theorems_as_pictures`
