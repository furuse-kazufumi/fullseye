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

**Currently 61 capabilities**

## Look up by task (recommended pipeline)

Every operator exists in the registry and the types connect from one step to the next (`tests/test_capabilities.py` checks both; only four sort names are treated as synonyms: `image2d`=`image`, `mask`=`region`, `measurement`=`feature`=`scalar`). Values passed as arguments are outside the type chain. Alternatives, limits and calibration are in each entry.

| Task | Recommended pipeline (in order) | Runnable |
|---|---|---|
| [Align and stack](capabilities/align-and-stack.md) | `align_frames` → `drizzle_resample` → `frame_quality` | `poc_astro_photometry` |
| [Beamform for direction, separate range from velocity](capabilities/beamforming-and-range-doppler.md) | `beamform_doa` → `range_doppler_map` → `range_doppler_peaks` | `poc_multibeam_bathymetry` |
| [Segment regions, select them, and count](capabilities/blob-and-region.md) | `auto_threshold` → `blob_label` → `blob_select` → `blob_features` | `poc_cell_counting` |
| [Measure colour (XYZ / Lab / colour difference)](capabilities/colour-and-delta-e.md) | `rgb_to_lab` → `delta_e_2000` | `poc_white_balance` |
| [Turn results into figures people can read](capabilities/figures-and-annotation.md) | `annotate_figure_grid` → `annotate_panel_label` → `annotate_scale_bar` → `annotate_colorbar` | `poc_colormap_readability` |
| [Put measurements on the Earth (ECEF, height frames, local ENU)](capabilities/geodetic-frames.md) | `dem_geodetic_to_ecef` → `dem_ecef_to_geodetic` | `poc_geodetic_height_frames` |
| [Inner diameter of a round part, all the way to millimetres](capabilities/inner-diameter-in-mm.md) | `gaussian` → `otsu` → `area_center` → `create_metrology_model` → `add_metrology_object_circle_measure` → `apply_metrology_model` → `mm_per_px_from_reference` → `pixel_to_world` | `example_inner_diameter_mm` |
| [Draw lines and regions without knowing the background colour](capabilities/inverted-colour-overlays.md) | `annotate_invert_visibility` → `annotate_invert` → `annotate_invert_path` | `annotate_paper_tour` |
| [Moiré alignment (two gratings of slightly different pitch, fringe phase, nanometre shift, differential pairs and the Talbot gap)](capabilities/moire-alignment.md) | `moire_magnification` → `moire_mark_read` → `moire_phase_crlb` | `poc_moire_alignment` |
| [OCR pre-processing (deskew, local binarisation, line extraction)](capabilities/ocr-preprocessing.md) | `median` → `rotate_image` → `sk_sauvola` → `invert_region` → `remove_small` → `select_shape` → `dilation_rectangle1` | `gallery2d_segmentation` |
| [Compute reflection, refraction and interference](capabilities/optics-and-materials.md) | `fresnel_dielectric` → `thin_film_reflectance` → `thin_film_rgb` | `glass_and_mirror_optics` |
| [Periodic defects in a 1-D signal](capabilities/periodic-defects-in-1d-signals.md) | `smooth_funct_1d_gauss` → `bandpass` → `spectrum` → `find_peaks` → `peak_subbin` → `envelope` → `local_min_max_funct_1d` | `poc_web_roll_periodicity` |
| [Find micrometre dents on glossy surfaces from the mirror image of a fringe screen (phase-measuring deflectometry)](capabilities/phase-measuring-deflectometry.md) | `deflectometry_rig` → `deflectometry_sensitivity` → `wrapped_phase` → `absolute_phase` → `deflectometry_phase_to_slope` → `slope_to_curvature` | `poc_phase_measuring_deflectometry` |
| [Pixel-shift imaging (full colour from 1-pixel shifts, no aliasing from half-pixel shifts, and where it breaks)](capabilities/pixel-shift-imaging.md) | `pixel_shift_resolution_budget` → `pixel_shift_pattern` → `pixel_shift_capture` → `pixel_shift_motion_mask` → `pixel_shift_merge` → `false_color_metric` | `poc_pixel_shift` |
| [Flatness of a surface from a 3-D point cloud](capabilities/planarity-from-point-cloud.md) | `statistical_outlier_removal` → `ransac_plane` → `fit_plane_3d` → `distance_point_plane` | `geometry_metrology` |
| [Find small point-like targets and locate them below the pixel](capabilities/point-target-detection.md) | `noise_sigma` → `star_detect` → `find_peaks` → `peak_subbin` | `poc_search_sweep_width` |
| [Remove specular reflection from a four-angle polariser sweep (dielectrics vs metals)](capabilities/polarisation-specular-removal.md) | `polarization_dolp_map` → `polarization_separate` → `polarization_stokes` → `stokes_analyze` → `specular_diffuse_split` | `example_polarization_metal` |
| [Detect fine scratches and measure their width](capabilities/scratch-detection-and-width.md) | `gaussian` → `lines_gauss` → `select_contours` → `fit_line_contours` → `gen_measure_rectangle2` → `measure_pairs` → `table_px_to_mm` | `example_scratch_width` |
| [Measure dimensions from an image, below the pixel](capabilities/subpixel-2d-metrology.md) | `gen_measure_rectangle2` → `measure_pos` → `measure_pairs` → `table_px_to_mm` | `poc_dimensional_inspection` |
| [Surface relief defects, from lighting design to detection](capabilities/surface-defects-with-lighting.md) | `illumination_design` → `lighting_sweep` → `light_source` → `defect_contrast` → `irradiance_map` → `illumination_uniformity` → `photometric_stereo` → `integrate_normals` → `surface_form_error` → `bothat` → `auto_threshold` → `remove_small` | `illumination_design_demo` |
| [TDI line-scan cameras and line-scan lenses (stages and SNR, synchronisation MTF, illumination and MTF across the image height)](capabilities/tdi-linescan-and-lens.md) | `tdi_snr` → `tdi_sync_mtf` → `linescan_lens_example` → `lens_field_profile` → `linescan_lens_columns` → `linescan_acquire` | `poc_tdi_linescan` |
| [Telecentric lenses for dimensional metrology (chief-ray angle, magnification versus height, vignetting and blur)](capabilities/telecentric-metrology.md) | `telecentric_lens` → `chief_ray_angle` → `telecentricity_error` → `magnification_vs_depth` → `defocus_spot_vs_depth` → `vignetting_vs_field` | `poc_telecentric_metrology` |
| [Locate a part by template matching and move the measurement model with it](capabilities/template-alignment.md) | `gaussian` → `ncc_locate` → `shape_locate` → `create_metrology_model` → `add_metrology_object_circle_measure` → `align_metrology_model` → `apply_metrology_model` | `poc_template_tracking` |
| [Slope, flow and line of sight on a terrain](capabilities/terrain-and-visibility.md) | `dem_fill_sinks` → `dem_slope` → `dem_aspect` → `dem_flow_direction` → `dem_viewshed` | `poc_dem_terrain` |
| [Put text and tables exactly where you want them on an image](capabilities/text-and-tables-on-images.md) | `measure_text` → `annotate_text_path_layout` → `annotate_text_path` → `annotate_table_layout` → `annotate_table` | `annotate_paper_tour` |
| [Reconstruct slices from projections (CT)](capabilities/tomography-reconstruction.md) | `radon_transform` → `ring_artifact_remove` → `beam_hardening_correct` → `fbp_volume` → `vol_rle_components` → `vol_rle_volume` | `poc_ct_fidelity` |
| [Diagnose faults from vibration and sound](capabilities/vibration-and-acoustics.md) | `bandpass` → `envelope` → `envelope_spectrum` → `find_peaks` → `bearing_defect_frequencies` | `poc_bearing_diagnosis` |
| [Carve a solid out of silhouettes (visual hull)](capabilities/visual-hull-from-silhouettes.md) | `synthesize_silhouette` → `visual_hull` → `vol_rle_components` → `vol_rle_volume` | `space_carving` |
| [Turn a 3-D scan into a volume](capabilities/volume-from-3d-scan.md) | `vol_rle_components` → `vol_rle_volume` → `mesh_volume` | `poc_stockpile_volume` |

32 entries do not have the recipe fields (pipeline / alternatives / limits / calibration) yet — see each entry below; they are named in `gen_capabilities_index.NO_RECIPE_YET`.

## Measure (22)

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

### [Inner diameter of a round part, all the way to millimetres](capabilities/inner-diameter-in-mm.md)

Bore, ring and pin diameters end to end: a coarse centre, a sub-pixel circle fit on radial measurement lines, a calibration from a reference of known size, and the result in millimetres. The last two steps exist as typed operators because an assistant working from the notes alone stopped at pixels.

Operators: `add_metrology_object_circle_measure`, `apply_metrology_model`, `mm_per_px_from_reference`, `pixel_to_world`

Pipeline: [`gaussian`](ops/2d/smoothing/gaussian.md) → [`otsu`](ops/2d/segmentation/otsu.md) → [`area_center`](ops/2d/features/area_center.md) → [`create_metrology_model`](ops/measure1d/model/create_metrology_model.md) → [`add_metrology_object_circle_measure`](ops/measure1d/model/add_metrology_object_circle_measure.md) → [`apply_metrology_model`](ops/measure1d/apply/apply_metrology_model.md) → [`mm_per_px_from_reference`](ops/measure1d/scale/mm_per_px_from_reference.md) → [`pixel_to_world`](ops/measure1d/scale/pixel_to_world.md)

Alternatives: [`gen_measure_arc`](ops/measure1d/caliper/gen_measure_arc.md), [`measure_pos`](ops/measure1d/caliper/measure_pos.md), [`hx_fit_circle_contour`](ops/2d/halcon_ext/hx_fit_circle_contour.md), [`cv_hough_circles`](ops/2d/features/cv_hough_circles.md), [`hough_circle_trans`](ops/2d/features/hough_circle_trans.md), [`table_px_to_mm`](ops/measure1d/scale/table_px_to_mm.md)

Runnable: `example_inner_diameter_mm`, `poc_dimensional_inspection`, `poc_real_coin_metrology`

### [Speckle sets the error floor of laser sheet-of-light (coherent imaging, speckle statistics and triangulation uncertainty)](capabilities/laser-speckle-floor.md)

Coherent imaging of rough surfaces under laser light: an amplitude/phase object through the coherent transfer function (verified against Bessel closed forms to 1e-12), laser speckle from a random phase screen with finite roughness, polarisation and pattern diversity and pixel integration, speckle statistics (contrast, Kolmogorov–Smirnov against the exponential and gamma laws, autocorrelation width compared with the Airy pattern), a speckled sheet-of-light laser line, and the speckle-limited height uncertainty of triangulation, δz = C·λ/(2π sin u sin θ). The exponents (+1 in wavelength, −1 in the observation aperture and the triangulation angle) are gated against centroids measured on rendered lines; the constant is disclosed (measured / formula = 0.84–0.91), because the primary paper's text was not available to check its 2π factor. Static speckle does not average away over frames; a moving part does, as 1/√N.

Operators: `coherent_image`, `speckle_field`, `speckle_statistics`, `laser_line_coherent`, `triangulation_speckle_limit`, `speckle_reduction`

Runnable: `poc_laser_line_speckle_floor`

### [Predict how far interreflection in concave parts throws fringe projection and ToF off, before measuring (global light transport, direct/global separation, micro phase shifting)](capabilities/light-transport.md)

Global light transport for concave Lambertian parts and its effect on active 3-D: an explicit light-transport matrix for an extruded concave cross-section (Hottel's crossed-strings form factors, checked against the V-groove closed form 1 − sin(θ/2) and against quadrature of the 2-D kernel to 1e-14; radiosity T = (I − diag(ρ)F)^-1 diag(ρ), or its Neumann partial sum by bounce count); shifted high-frequency patterns and the Nayar et al. (2006) L_max / L_min separation into direct and global images (general fill α, black level b, pattern-plus-complement); the fringe phase as the argument of the direct-plus-global phasor sum, predicted per pixel from the transport matrix and matching the phase decoded from rendered fringes by `fringe.wrapped_phase` to 1e-15 rad; a micro phase-shifting decoder (Gupta & Nayar 2012) that orders narrow-band high-frequency fringes by their beat; and AMCW time-of-flight multipath, both as a phasor sum and as complex radiosity with per-bounce path delay. On a white 1 mm, 0.5 mm deep 90° V-groove, one fringe across a 4 mm field misreads height by 282 µm RMS; the micro set brings it to 0.76 µm.

Operators: `groove_profile`, `form_factors_2d`, `transport_matrix_radiosity`, `high_frequency_patterns`, `render_transport`, `separate_direct_global`, `fringe_multipath_phase_error`, `predict_fringe_phase_error`, `micro_phase_decode`, `tof_multipath_phase`, `tof_transport_depth`

Runnable: `poc_interreflection_fringe_error`

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

### [Measure the shape of black-glossy and glass parts from polarisation (shape from polarisation, the ambiguity set, refractive index)](capabilities/shape-from-polarization.md)

Shape from polarisation for a 4-direction on-chip polariser sensor: the Fresnel DoLP of specular reflection (exactly 1 at Brewster's angle, two zenith solutions straddling it) and of diffuse emission (monotone, one solution), checked against the s/p reflectances of `glassmirror` written in a different form to 1e-14; AoLP to the two candidate azimuths (diffuse and specular 90° apart, the π ambiguity kept); the explicit candidate set of normals per pixel; disambiguation by a stated prior (convexity with Brewster-ridge segmentation, or a coarse depth / normal map); refractive-index estimation from DoLP at known zenith angles; and integration to height with a mirror-extended Frankot–Chellappa. Round trips through an independent Mueller-matrix forward path (`optics.mueller_element` / `mueller_apply`) recover analytic spheres, cylinders and rotated ellipsoids to 1e-9° (diffuse) and to 0.1° on the discrete Brewster ridge (specular). Where it breaks is measured: a wrong index, noise concentrated on the Brewster ring and at the apex, and a diffuse component mixed into a specular pixel.

Operators: `sfp_dolp_model`, `dolp_to_zenith`, `aolp_to_azimuth`, `sfp_render`, `sfp_normals`, `sfp_disambiguate`, `sfp_estimate_index`, `sfp_height`

Runnable: `poc_shape_from_polarization`

### [Measure dimensions from an image, below the pixel](capabilities/subpixel-2d-metrology.md)

Locate edges along a measurement line from the intensity gradient, at sub-pixel resolution, and read a dimension as the distance between paired edges. Unlike counting thresholded pixels, the answer does not move when the threshold does.

Operators: `measure_pos`, `measure_pairs`, `blob_label`, `blob_select`

Pipeline: [`gen_measure_rectangle2`](ops/measure1d/caliper/gen_measure_rectangle2.md) → [`measure_pos`](ops/measure1d/caliper/measure_pos.md) → [`measure_pairs`](ops/measure1d/caliper/measure_pairs.md) → [`table_px_to_mm`](ops/measure1d/scale/table_px_to_mm.md)

Alternatives: [`fuzzy_measure_pairing`](ops/measure1d/caliper/fuzzy_measure_pairing.md), [`gen_measure_arc`](ops/measure1d/caliper/gen_measure_arc.md), [`create_metrology_model`](ops/measure1d/model/create_metrology_model.md), [`blob_label`](ops/blob/connect/blob_label.md), [`blob_select`](ops/blob/select/blob_select.md), [`mm_per_px_from_reference`](ops/measure1d/scale/mm_per_px_from_reference.md)

Runnable: `poc_dimensional_inspection`, `poc_screw_thread_metrology`, `poc_calipers_under_illusion`

### [Telecentric lenses for dimensional metrology (chief-ray angle, magnification versus height, vignetting and blur)](capabilities/telecentric-metrology.md)

Seven ops in `telecentric` (category `telecentric` of `opsoptics`) on top of the `raytrace` prescriptions: a generator of the same singlet with the stop moved (entocentric, object-side telecentric, bi-telecentric, plus a stop shift that spoils telecentricity), the real chief ray found by aiming at the stop itself rather than at the entrance pupil (so it works with the pupil at infinity), the magnification versus object height on a fixed image plane, the dimensional error across a step, the RMS defocus blur from a brute-force pupil bundle, the vignetting set by the front lens, and a pinhole camera at the entrance pupil for `render3d`. The PoC gates the magnification against L/(L − Δz), the stop shift against Newton's equation, the blur slope against |m|·NA/√2, and measurements taken from rendered images against circle-overlap closed forms. The lead chapter measures the paper's raw telecentric images (Stark et al., Sci. Rep. 15, 28690, 2025, CC BY 4.0) with Fullseye's metrology ops and checks them against the paper: ellipses fitted to the six rings of an alignment plate (1 mm spacing) tilted by 29.7° give 250.73 ± 0.79 px/mm along the major axis, −0.50 % from the paper's K1 = 252.0 px/mm. The telecentric signature: the centres of the concentric rings on the tilted plate do not drift with r² (β = −0.050 ± 0.095 px/mm², where a 25 mm entocentric lens would give 1.39 and move the outer centre by 59 px), so the entrance pupil lies beyond 451 mm. A 3D-printed resin sphere (nominal radius 2.5 mm) is not a usable reference: its outline radius moves 8 % with the threshold.

Operators: `telecentric_lens`, `chief_ray_angle`, `magnification_vs_depth`, `telecentricity_error`, `defocus_spot_vs_depth`, `vignetting_vs_field`, `lens_equivalent_pinhole`

Pipeline: [`telecentric_lens`](ops/optics/telecentric/telecentric_lens.md) → [`chief_ray_angle`](ops/optics/telecentric/chief_ray_angle.md) → [`telecentricity_error`](ops/optics/telecentric/telecentricity_error.md) → [`magnification_vs_depth`](ops/optics/telecentric/magnification_vs_depth.md) → [`defocus_spot_vs_depth`](ops/optics/telecentric/defocus_spot_vs_depth.md) → [`vignetting_vs_field`](ops/optics/telecentric/vignetting_vs_field.md)

Alternatives: [`lens_system`](ops/optics/design/lens_system.md), [`paraxial_trace`](ops/optics/design/paraxial_trace.md), [`lens_equivalent_pinhole`](ops/optics/telecentric/lens_equivalent_pinhole.md), [`relative_illumination`](ops/optics/geometric/relative_illumination.md)

Runnable: `poc_telecentric_metrology`

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

### [What a picture cannot check (integrator order, Lyapunov spectrum, bifurcations, correlation dimension, minimal surfaces)](capabilities/what-a-picture-cannot-check.md)

Integrate named dynamical systems (Lorenz, Rossler, harmonic, arbitrary linear `A`), sample their fields, take Poincare sections, compute Lyapunov spectra, bifurcation maps and correlation dimensions; build minimal surfaces (catenoid, helicoid, Enneper, Scherk, gyroid) and sweep a curve into a tube mesh — and score all of it with identities and definitions rather than by eye, because a Lorenz plot looks the same whether the integrator is 1st or 4th order and a surface looks smooth whether or not its mean curvature vanishes. RK4's error falls by exactly 16 per halving against `expm(At)x0` (Euler, the control, falls by 2); the *sum* of the Lyapunov exponents equals the trace identity `-(sigma+1+beta)` to 2.6e-06, independently of the tangent-flow/QR procedure that produced them; the logistic period-doubling points are the exact 3 and `1+sqrt(6)`, and the residual is attributed — the gate is not "the error is small" but "lengthening the burn-in shrinks it by 10.9x", because convergence at a bifurcation is algebraic; the correlation-dimension bias on a bounded set is traced to the **radius window**, not the sample count (400 to 3,000 points does not move it; narrowing `r_lo`/`r_hi` moves 1.887 to 2.050); the field's divergence equals `tr(A)` and its vorticity `A10 - A01` as measured by the **existing PIV ops**, which know nothing about this family; a tube swept along a circle is a torus whose analytic volume `2*pi^2*R*r^2` and area `4*pi^2*R*r` the existing `mesh_volume` / `mesh_area` confirm to 0.3 %; and the minimal surfaces have `|H|` medians of 1e-4 against controls of 1.00004 (unit sphere) and 0.50000 (unit cylinder), with the gyroid's nodal-approximation residual reported rather than hidden.

Operators: `ode_flow_states`, `ode_vector_field_grid`, `dynsys_poincare_section`, `dynsys_lyapunov_spectrum`, `dynsys_bifurcation_map`, `dynsys_correlation_dimension`, `minimal_surface`, `minimal_surface_bend`, `gyroid_isosurface`, `gyroid_solid_mask`, `curve3d_tube_mesh`

Runnable: `poc_what_a_picture_cannot_check`

## Detect (8)

### [Segment regions, select them, and count](capabilities/blob-and-region.md)

Label connected components, select them by area, shape or position, and count them. Touching objects can be separated with a watershed.

Operators: `blob_label`, `blob_select`, `blob_count`, `watersheds`

Pipeline: [`auto_threshold`](ops/2d/segmentation/auto_threshold.md) → [`blob_label`](ops/blob/connect/blob_label.md) → [`blob_select`](ops/blob/select/blob_select.md) → [`blob_features`](ops/blob/measure/blob_features.md)

Alternatives: [`watersheds`](ops/2d/segmentation/watersheds.md), [`blob_seeds`](ops/blob/split/blob_seeds.md), [`blob_count`](ops/2d/features/blob_count.md), [`remove_small`](ops/2d/region/remove_small.md), [`select_shape`](ops/2d/region/select_shape.md), [`otsu`](ops/2d/segmentation/otsu.md)

Runnable: `poc_cell_counting`, `poc_particle_sizing`, `poc_real_coin_metrology`

### [Fix the text inside an image against the string it should read](capabilities/fix-text-in-images.md)

Fix the text inside an image against the string it should read, without regenerating the image: pass `{"items": [{"text": "...", "bbox": [x, y, w, h]}]}` to `glyph_correct_spec` (Python) or `fullseye_fix_text` (MCP). Nothing is recognised — the intended string is given, so each cell is verified one-to-one against one character, and the threshold comes from the typeface noise floor measured on the fonts of the environment. `repair_flagged` replaces only the glyphs above the floor and rolls back any replacement that does not verify; `rewrite_line` redraws the whole line in one typeface. The report carries a per-line `status`, a machine-readable `reason_code` for refusals, and `mismatch` (`typo` / `unrelated`) so that a caller notices when the original text has nothing to do with the intended one.

Operators: `glyph_correct_spec`, `glyph_make_spec`, `glyph_find_text_lines`, `glyph_rewrite_line`, `glyph_find_plate`, `glyph_typeface_noise_floor`, `glyph_rendering_noise_floor`, `glyph_distance`, `glyph_replace`, `glyph_split_cells`, `glyph_fonts`

Runnable: `fix_text_in_image`, `poc_glyph_typo_detection`

### [OCR pre-processing (deskew, local binarisation, line extraction)](capabilities/ocr-preprocessing.md)

Everything before the recogniser: deskew, local (Sauvola) binarisation, speck removal and merging characters into lines, all from registry operators. Recognition itself is out of scope.

Operators: `sk_sauvola`, `rotate_image`, `remove_small`, `dilation_rectangle1`

Pipeline: [`median`](ops/2d/rank/median.md) → [`rotate_image`](ops/2d/geometry/rotate_image.md) → [`sk_sauvola`](ops/2d/segmentation/sk_sauvola.md) → [`invert_region`](ops/2d/region/invert_region.md) → [`remove_small`](ops/2d/region/remove_small.md) → [`select_shape`](ops/2d/region/select_shape.md) → [`dilation_rectangle1`](ops/2d/region/dilation_rectangle1.md)

Alternatives: [`sk_niblack`](ops/2d/segmentation/sk_niblack.md), [`adaptive_gauss_thresh`](ops/2d/segmentation/adaptive_gauss_thresh.md), [`otsu`](ops/2d/segmentation/otsu.md), [`gray_bothat`](ops/2d/morphology/gray_bothat.md), [`unsharp`](ops/2d/smoothing/unsharp.md), [`zoom_image_factor`](ops/2d/geometry/zoom_image_factor.md), [`affine_trans_image`](ops/2d/geometry/affine_trans_image.md)

Runnable: `gallery2d_segmentation`, `poc_matrix_code_reading`, `gallery2d_region`

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

## Light and colour (10)

### [Measure colour (XYZ / Lab / colour difference)](capabilities/colour-and-delta-e.md)

From spectral reflectance or RGB, compute CIE XYZ and Lab, then colour differences under CIE76 or CIEDE2000. The difference can also be returned as a per-pixel map.

Operators: `rgb_to_lab`, `xyz_to_lab`, `delta_e_2000`, `cie_xyz_from_wavelength`

Pipeline: [`rgb_to_lab`](ops/imgmetrics/colorspace/rgb_to_lab.md) → [`delta_e_2000`](ops/imgmetrics/colordiff/delta_e_2000.md)

Alternatives: [`rgb_to_xyz`](ops/imgmetrics/colorspace/rgb_to_xyz.md), [`xyz_to_lab`](ops/imgmetrics/colorspace/xyz_to_lab.md), [`delta_e_76`](ops/imgmetrics/colordiff/delta_e_76.md), [`delta_e_map`](ops/imgmetrics/colordiff/delta_e_map.md), [`cie_xyz_from_wavelength`](ops/optics/appearance/cie_xyz_from_wavelength.md), [`srgb_to_linear`](ops/gfx2d/colorspace/srgb_to_linear.md)

Runnable: `poc_white_balance`, `poc_pigment_unmixing`

### [Optical fibres and light guides (glass dispersion, LP modes, mode field diameter, illumination efficiency)](capabilities/fiber-and-light-guide.md)

Seven ops in `fiberoptics` (category `fiber`): group index and material dispersion D(λ) from the material table, numerical aperture, V number and cutoff wavelength, LP_lm modes by solving the weakly guiding characteristic equation, the mode field diameter of LP01 (best-overlap Gaussian, with the Marcuse fit and the second-moment definition alongside), and the efficiency of a light guide (packing fraction, end-face Fresnel, NA acceptance, attenuation). Gates: Bessel-zero cutoffs, V²/2 mode count, the Rudolph–Neumann b(V) and Marcuse MFD fits, the 1.27 µm zero of silica's material dispersion, and the ITU-T G.652 MFD range.

Operators: `material_group_index`, `material_gvd`, `fiber_numerical_aperture`, `fiber_v_number`, `fiber_lp_modes`, `fiber_mode_field_diameter`, `fiber_bundle_coupling`

Runnable: `poc_fiber_light_guide`

### [One table of material optical constants (83 glasses, crystals, semiconductors, metals, liquids and plastics from primary literature, with a glass-catalogue importer)](capabilities/material-optical-property-library.md)

Sixteen ops in the new `matprop` category of `opsoptics`, backed by one record per material in `materials_data.py` (generated from the refractiveindex.info database, CC0: primary-literature coefficients and tables with their citation on every wavelength segment). 46 catalogue glasses from four makers, 12 crystals and IR materials, 6 semiconductors (Si with Green 2008 n,k and the Salzberg IR Sellmeier), 4 films, 10 metals, water and 4 plastics. Every curve comes back as `pairs` (λ nm, value) so sources, optics, targets and sensor QE share one shape. `read_glass_catalog_agf` reads the user's own .agf catalogues (all 13 Zemax dispersion formulas, k from internal-transmittance lines); vendor catalogues are not bundled. Gates: catalogue n_d / V_d of all 46 glasses within 4e-6 / 0.005, the published Green 2008 and Johnson & Christy points, slab transmittance against the closed form, and optiland 0.6.3 as a second implementation at 23 points.

Operators: `material_table`, `material_record`, `material_optical_constants`, `material_dispersion`, `material_extinction`, `material_absorption`, `material_transmittance`, `material_reflectance`, `abbe_number`, `glass_map`, `thermo_optic_coefficient`, `plate_focus_shift`, `silicon_free_carrier_absorption`, `material_from_sellmeier`, `material_from_curves`, `read_glass_catalog_agf`

Runnable: `poc_material_optical_library`

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

Turn a polarisation camera's mosaic (a 2×2 block of 0/45/90/135° analysers, Sony IMX250MZR family) into four full-resolution images with `polarization_demosaic` (bilinear, exact on affine fields, phase-preserving mirrored border) that chain straight into `polarization_stokes` / `polarization_dolp_map`. Recover a sample's Mueller matrix from intensities measured through known generator/analyser states with `mueller_from_intensities` (linear least squares on `outer(a_i, g_i)`; refuses rank-deficient designs with the rank instead of returning a pseudo-inverse guess). Check any 4×4 matrix with `mueller_checks`: Cloude coherency eigenvalues (physical), purity, the Gil–Bernabeu depolarisation index and passivity.

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

## Draw (3)

### [Turn a photograph into a single line (stipple, tour, rotating circles)](capabilities/one-stroke-drawing.md)

Turn the tone of a picture into a single closed line a pen could draw without lifting: points are placed by darkness (weighted Lloyd), ordered into a closed tour, resampled at equal arc length, and rewritten as a chain of rotating circles via the complex Fourier series. Nothing is judged by eye. The stipple is checked against a ramp (correlation 0.9946) with a flat image as the control — and the *exponent* is measured too, because a centroidal Voronoi tessellation puts density at sqrt(rho), not rho (Gersho): 0.61 measured, 0.77 with the weight squared. The tour is checked against the minimum spanning tree, which no closed tour can beat (1.146, against 41.4 for coordinate order); the tone is measured (0.984, against +0.013 for random points); the pen width that reproduces the mean tone is solved in closed form and falls 11 % short, which *is* the stroke overlap; the resampling is checked against Nyquist (the error falls as 1/N: 6.5, 3.3, 1.6 % of the stroke length); and Parseval turns the number of circles into a prediction made before the drawing exists.

Operators: `stipple_points_from_image`, `stipple_energy`, `stroke_tour_closed`, `mst_length`, `stroke_resample_closed`, `stroke_tone_error`, `contour_fourier_complex`, `contour_epicycle_chain`, `contour_fourier_truncation_energy`

Runnable: `poc_one_stroke_epicycles`

### [Pictures that carry their own ground truth (illusions, endless drawing, seamless loops)](capabilities/pictures-that-carry-their-own-truth.md)

Generates pictures that ship with their own ground truth: optical illusions whose denied invariant is exact (parallel, equal-length, identical-valued), endless generative systems whose correctness is an identity rather than an appearance, and seamless loops where the seam is absent by construction rather than removed by editing.

Operators: `illusion_cafe_wall`, `illusion_muller_lyer`, `illusion_checker_shadow`, `illusion_kanizsa`, `illusion_fraser_spiral`, `illusion_ground_truth`, `perpetual_elementary_ca`, `perpetual_langtons_ant`, `perpetual_apollonian`, `perpetual_flow_field`, `perpetual_identities`, `perpetual_state`, `perpetual_step`, `perpetual_render`, `perpetual_loop`, `perpetual_loop_seam`

Runnable: `poc_illusions_and_perpetual_drawing`

### [Theorems as pictures (Apollonian, Ford, geodesic dome, phyllotaxis, IFS, space-filling curves)](capabilities/theorems-as-pictures.md)

Draw mathematically beautiful figures whose correctness is asserted by a theorem rather than by eye: an Apollonian gasket (every tangent quadruple satisfies Descartes' circle theorem to 1e-13, and an integral seed stays integral for ever), Ford circles (tangency agrees with `|ps - qr| = 1` on all 1,081 pairs, and the count matches `1 + sum of Euler's totient`), a geodesic dome (exactly 12 degree-5 vertices at every subdivision — counted by the existing `graph_degree_table`, not by this module), Vogel's phyllotactic spiral (neighbour index gaps land on Fibonacci numbers only at the golden angle: 7/7 against 2/7 for the controls), IFS attractors (Moran's closed-form dimension agrees with the existing box-counting `fractal_dimension`, and non-similarity maps are refused), and space-filling curves (a permutation of 4^n cells with unit steps; locality reported as a table, not a slogan).

Operators: `circle_packing_apollonian`, `ford_circles`, `phyllotaxis_pattern`, `neighbour_index_gaps`, `ifs_fractal`, `ifs_similarity_dimension`, `space_filling_curve`, `curve_locality`, `geodesic_dome`

Runnable: `poc_theorems_as_pictures`
