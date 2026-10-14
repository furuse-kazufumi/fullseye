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

**Currently 49 capabilities**

## Measure (16)

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

Runnable: `poc_geodetic_height_frames`, `poc_geodetic_benchmarks_real`, `dem_geodesy_tour`

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

### [Which flaw size will you actually find (probability of detection and a90/95, MIL-HDBK-1823A)](capabilities/probability-of-detection.md)

Probability of detection per MIL-HDBK-1823A: â-vs-a regression with left and right censoring (a Tobit-type maximum likelihood, concave in Olsen's coordinates, reducing exactly to least squares when nothing is censored), the POD(a) curve with a50 / a90 / a90/95 by the delta method, the hit/miss generalised linear model with both Wald and likelihood-ratio a90/95, false-call probability from unflawed sites (binomial one-sided bounds that reproduce the handbook's PFP table to 7.2e-05), and the decision-threshold trade-off. Estimates agree with an independently written likelihood minimised by a different algorithm to 6.6e-08. The delta-method a90/95 covers the true a90 in 94.3 % of large-sample replicates but only 89.2 % at n=60 — reported, not hidden. A slope that cannot be told from zero is refused rather than turned into an absurd a90, and an a90/95 beyond the largest size tested carries a flag.

Operators: `pod_ahat_fit`, `pod_from_ahat`, `pod_hitmiss_fit`, `pod_false_call`, `pod_decision_tradeoff`, `light_source`, `detectability_limit`

Runnable: `poc_pod_lighting`

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

Runnable: `poc_dimensional_inspection`, `poc_screw_thread_metrology`, `poc_calipers_under_illusion`

### [Slope, flow and line of sight on a terrain](capabilities/terrain-and-visibility.md)

From a height grid: slope, aspect, viewshed and flow direction. Each has a closed form to check against, so an implementation error shows up as a number.

Operators: `dem_slope`, `dem_aspect`, `dem_viewshed`, `dem_flow_direction`

Runnable: `poc_dem_terrain`, `dem_terrain_analysis_tour`

### [Turn a 3-D scan into a volume](capabilities/volume-from-3d-scan.md)

Compute a signed volume from a closed mesh, a voxel count from a labelled region, or the material between two surfaces from a height grid. Gaps can be filled by interpolation, and how far that interpolation reached is reported separately.

Operators: `mesh_volume`, `vol_rle_volume`, `interp_scattered`, `dem_slope`

Runnable: `poc_stockpile_volume`, `poc_lidar_terrain_change`

### [What a picture cannot check (integrator order, Lyapunov spectrum, bifurcations, correlation dimension, minimal surfaces)](capabilities/what-a-picture-cannot-check.md)

Integrate named dynamical systems (Lorenz, Rossler, harmonic, arbitrary linear `A`), sample their fields, take Poincare sections, compute Lyapunov spectra, bifurcation maps and correlation dimensions; build minimal surfaces (catenoid, helicoid, Enneper, Scherk, gyroid) and sweep a curve into a tube mesh — and score all of it with identities and definitions rather than by eye, because a Lorenz plot looks the same whether the integrator is 1st or 4th order and a surface looks smooth whether or not its mean curvature vanishes. RK4's error falls by exactly 16 per halving against `expm(At)x0` (Euler, the control, falls by 2); the *sum* of the Lyapunov exponents equals the trace identity `-(sigma+1+beta)` to 2.6e-06, independently of the tangent-flow/QR procedure that produced them; the logistic period-doubling points are the exact 3 and `1+sqrt(6)`, and the residual is attributed — the gate is not "the error is small" but "lengthening the burn-in shrinks it by 10.9x", because convergence at a bifurcation is algebraic; the correlation-dimension bias on a bounded set is traced to the **radius window**, not the sample count (400 to 3,000 points does not move it; narrowing `r_lo`/`r_hi` moves 1.887 to 2.050); the field's divergence equals `tr(A)` and its vorticity `A10 - A01` as measured by the **existing PIV ops**, which know nothing about this family; a tube swept along a circle is a torus whose analytic volume `2*pi^2*R*r^2` and area `4*pi^2*R*r` the existing `mesh_volume` / `mesh_area` confirm to 0.3 %; and the minimal surfaces have `|H|` medians of 1e-4 against controls of 1.00004 (unit sphere) and 0.50000 (unit cylinder), with the gyroid's nodal-approximation residual reported rather than hidden.

Operators: `ode_flow_states`, `ode_vector_field_grid`, `dynsys_poincare_section`, `dynsys_lyapunov_spectrum`, `dynsys_bifurcation_map`, `dynsys_correlation_dimension`, `minimal_surface`, `minimal_surface_bend`, `gyroid_isosurface`, `gyroid_solid_mask`, `curve3d_tube_mesh`

Runnable: `poc_what_a_picture_cannot_check`

## Detect (5)

### [Segment regions, select them, and count](capabilities/blob-and-region.md)

Label connected components, select them by area, shape or position, and count them. Touching objects can be separated with a watershed.

Operators: `blob_label`, `blob_select`, `blob_count`, `watersheds`

Runnable: `poc_cell_counting`, `poc_particle_sizing`, `poc_real_coin_metrology`

### [Fix the text inside an image against the string it should read](capabilities/fix-text-in-images.md)

Fix the text inside an image against the string it should read, without regenerating the image: pass `{"items": [{"text": "...", "bbox": [x, y, w, h]}]}` to `glyph_correct_spec` (Python) or `fullseye_fix_text` (MCP). Nothing is recognised — the intended string is given, so each cell is verified one-to-one against one character, and the threshold comes from the typeface noise floor measured on the fonts of the environment. `repair_flagged` replaces only the glyphs above the floor and rolls back any replacement that does not verify; `rewrite_line` redraws the whole line in one typeface. The report carries a per-line `status`, a machine-readable `reason_code` for refusals, and `mismatch` (`typo` / `unrelated`) so that a caller notices when the original text has nothing to do with the intended one.

Operators: `glyph_correct_spec`, `glyph_make_spec`, `glyph_find_text_lines`, `glyph_rewrite_line`, `glyph_find_plate`, `glyph_typeface_noise_floor`, `glyph_rendering_noise_floor`, `glyph_distance`, `glyph_replace`, `glyph_split_cells`, `glyph_fonts`

Runnable: `fix_text_in_image`, `poc_glyph_typo_detection`

### [Why a thin groove disappears in a PL image — the carrier-diffusion PSF and the kind of defect decide the visibility (PL/EL inspection of wafers and solar cells)](capabilities/pl-carrier-diffusion-visibility.md)

A PL image glows only after the excess carriers have diffused, so a second PSF — the 2-D Green function K₀(r/L)/2πL², L = √(Dτ) — sits on top of the optical one. `pl_diffusion_psf` returns that kernel (sum 1); `pl_image_simulate` solves the steady-state diffusion equation exactly on the grid from an excitation map and an extra-recombination map (optional optical PSF and noise); `pl_groove_visibility` gives the closed-form contrast, CNR and visibility boundary L* of a shadow groove (missing excitation, 1 − e^{−w/2L}) and a sink groove (a recombination line, Donolato's SL/(SL+2D)). The two move in opposite directions with L: a longer diffusion length hides shadows and reveals sinks. Embedded-groove detection feeds `pod_hitmiss_fit` for a90/95.

Operators: `pl_diffusion_psf`, `pl_image_simulate`, `pl_groove_visibility`, `pod_hitmiss_fit`

Runnable: `poc_si_wafer_pl_defect_visibility`

### [Find small point-like targets and locate them below the pixel](capabilities/point-target-detection.md)

Pick local maxima above a robustly estimated background plus k sigma, and return sub-pixel centroids. The name is astronomical but the method is domain-neutral: drifting objects, small defects, fluorescent puncta, particles.

Operators: `star_detect`, `peak_subbin`, `find_peaks`, `noise_sigma`

Runnable: `poc_search_sweep_width`, `poc_astro_photometry`

### [Find hybrid-bond voids by the phase of the ultrasonic echo, not its brightness (scanning acoustic microscope C-scans, the frequency trade-off, POD)](capabilities/sam-bond-voids.md)

Pulse-echo ultrasound in layered stacks and scanning-acoustic-microscope C-scans, built from first principles: a material table that carries a source and a verified flag per value (unverified placeholders are refused unless asked for), interface coefficients with the energy check R² + (Z1/Z2)T² = 1 and the sign flip exactly where Z drops, a normal-incidence longitudinal transfer-matrix A-scan with water path and power-law attenuation (checked against a bottom-up Airy recursion, a time-domain ray sum and the optical thin-film formula to 1e-12), and a focused C-scan with a per-frequency Gaussian lateral PSF (FWHM 1.02 λ_water F#) that returns amplitude, phase, in-phase and single-sample-polarity images. Phase is read at the expected time of the bond plane relative to the front-surface echo: thin Cu and SiO2 layers give quadrature echoes, voids are inverted, so a small void adds at right angles to the background and barely changes the amplitude. A closed-form optimal frequency balances lateral resolution against water attenuation, with the front-echo time floor and the critical-angle F-number floor alongside; C-scan statistics feed the existing POD operators.

Operators: `acoustic_material_table`, `acoustic_layer_stack`, `acoustic_interface_coefficients`, `pulse_echo_ascan`, `sam_cscan`, `echo_phase_polarity`, `sam_frequency_tradeoff`

Runnable: `poc_sam_hybrid_bonding_voids`

## Shape (3)

### [Correct lens distortion over a whole image (barrel, pincushion, tangential)](capabilities/lens-distortion-correction.md)

Whole-image Brown–Conrady undistortion and its inverse, built as a backward map over this repo's own point model plus a bilinear, edge-clamped remap — so a corrected image is hole-free and a synthetic distorted image is exact to the resampling. `dist` is `[k1, k2, p1, p2(, k3)]` (OpenCV order); `K`'s principal point is the distortion centre. Grey or colour, in `[0, 1]`. On a smooth scene the round trip `distort_image` → `undistort_image` recovers the interior to a few times 1e-4 (only the double bilinear blur remains); the remap field equals `distort_points` to machine precision.

Operators: `undistort_image`, `distort_image`, `distort_points`, `undistort_points`

Runnable: `lens_undistort`

### [Reconstruct slices from projections (CT)](capabilities/tomography-reconstruction.md)

Forward parallel-beam projection to a sinogram, filtered back-projection to a slice or a volume, and the injection and correction of ring artefacts and beam hardening. The reconstructed volume can be turned straight into a mesh.

Operators: `radon_transform`, `fbp_volume`, `ring_artifact_remove`, `marching_cubes`

Runnable: `poc_ct_fidelity`, `poc_ct_void_morphology`

### [Carve a solid out of silhouettes (visual hull)](capabilities/visual-hull-from-silhouettes.md)

From the foreground masks of several calibrated cameras, carve out a voxel volume that always contains the object. No learned model, no depth sensor.

Operators: `synthesize_silhouette`, `carve`, `visual_hull`, `carve_look_at`

Runnable: `space_carving`, `poc_livestock_body_volume`

## Light and colour (8)

### [Measure colour (XYZ / Lab / colour difference)](capabilities/colour-and-delta-e.md)

From spectral reflectance or RGB, compute CIE XYZ and Lab, then colour differences under CIE76 or CIEDE2000. The difference can also be returned as a per-pixel map.

Operators: `rgb_to_lab`, `xyz_to_lab`, `delta_e_2000`, `cie_xyz_from_wavelength`

Runnable: `poc_white_balance`, `poc_pigment_unmixing`

### [Optical fibres and light guides (glass dispersion, LP modes, mode field diameter, illumination efficiency)](capabilities/fiber-and-light-guide.md)

Seven ops in `fiberoptics` (category `fiber`): group index and material dispersion D(λ) from the material table, numerical aperture, V number and cutoff wavelength, LP_lm modes by solving the weakly guiding characteristic equation, the mode field diameter of LP01 (best-overlap Gaussian, with the Marcuse fit and the second-moment definition alongside), and the efficiency of a light guide (packing fraction, end-face Fresnel, NA acceptance, attenuation). Gates: Bessel-zero cutoffs, V²/2 mode count, the Rudolph–Neumann b(V) and Marcuse MFD fits, the 1.27 µm zero of silica's material dispersion, and the ITU-T G.652 MFD range.

Operators: `material_group_index`, `material_gvd`, `fiber_numerical_aperture`, `fiber_v_number`, `fiber_lp_modes`, `fiber_mode_field_diameter`, `fiber_bundle_coupling`

Runnable: `poc_fiber_light_guide`

### [One table of material optical constants (83 glasses, crystals, semiconductors, metals, liquids and plastics from primary literature, with a glass-catalogue importer)](capabilities/material-optical-property-library.md)

Sixteen ops in the new `matprop` category of `opsoptics`, backed by one record per material in `materials_data.py` (generated from the refractiveindex.info database, CC0: primary-literature coefficients and tables with their citation on every wavelength segment). 46 catalogue glasses from four makers, 12 crystals and IR materials, 6 semiconductors (Si with Green 2008 n,k and the Salzberg IR Sellmeier), 4 films, 10 metals, water and 4 plastics. Every curve comes back as `pairs` (λ nm, value) so sources, optics, targets and sensor QE share one shape. `read_glass_catalog_agf` reads the user's own .agf catalogues (all 13 Zemax dispersion formulas, k from internal-transmittance lines); vendor catalogues are not bundled. Gates: catalogue n_d / V_d of all 46 glasses within 4e-6 / 0.005, the published Green 2008 and Johnson & Christy points, slab transmittance against the closed form, and optiland 0.6.3 as a second implementation at 23 points.

Operators: `material_table`, `material_record`, `material_optical_constants`, `material_dispersion`, `material_extinction`, `material_absorption`, `material_transmittance`, `material_reflectance`, `abbe_number`, `glass_map`, `thermo_optic_coefficient`, `plate_focus_shift`, `silicon_free_carrier_absorption`, `material_from_sellmeier`, `material_from_curves`, `read_glass_catalog_agf`

Runnable: `poc_material_optical_library`

### [Sorting look-alike foreign matter with NIR hyperspectral imaging (material absorption bands, scattering-layer reflectance, InGaAs band electrons)](capabilities/nir-hyperspectral-sorting.md)

Eight ops build the NIR sorting chain with the object and the optics reading the same material table: absorption bands for polymers, lipids, proteins, carbohydrates and lignin (and nut kernels, shells and wood as mixtures; water from the table's n,k), carbon black, the Kubelka–Munk reflectance of a scattering layer, reflectance from a material name with grain-size scattering and the Saunderson surface correction, an InGaAs QE from the direct-gap absorption edges, and the linear map from reflectance to electrons per band through a halogen lamp, the lens glass, the band filters and the QE. Gates: the Kubelka–Munk limits and inverse, measured polymer trough positions within 5 nm, water absorption within 10 % of Kou 1993, linearity and the EMVA variance of the captured cube, and the Fisher ratio's two-class closed form.

Operators: `material_nir_absorption`, `carbon_black_absorption`, `nir_model_info`, `ingaas_photodiode_qe`, `kubelka_munk_reflectance`, `spectral_reflectance_from_material`, `hyperspectral_band_weights`, `hyperspectral_capture`

Runnable: `poc_hyperspectral_foreign_matter`

### [Compute reflection, refraction and interference](capabilities/optics-and-materials.md)

Fresnel reflectance, thin-film interference colour, grating colour, and vector-form refraction with a per-ray total-internal-reflection mask — with the dispersion of real glasses.

Operators: `fresnel_dielectric`, `thin_film_reflectance`, `grating_rgb`, `refract_rays`

Runnable: `glass_and_mirror_optics`, `appearance_structural_colour`

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

## Waves and signals (4)

### [Beamform for direction, separate range from velocity](capabilities/beamforming-and-range-doppler.md)

Form beams from an array snapshot to get directions of arrival, and build a range-Doppler map from an FMCW return, mapping detections back to metres and metres per second.

Operators: `beamform_delay_sum`, `beamform_doa`, `range_doppler_map`, `range_doppler_peaks`

Runnable: `poc_multibeam_bathymetry`, `poc_bev_sensor_fusion`

### [One beat (membrane modes, fringes, diffraction orders, print moire, and turning tone into ink)](capabilities/beats-fringes-and-screens.md)

Build membrane eigenmodes and nodal lines, two-slit fringes, grating orders, and the printing side (halftone screens, moire, engraving lines, structure-following hatching, mosaic tiles) — and score every one of them against a truth that lives outside the picture. The thesis: a two-slit fringe and the moire of two superposed halftone screens are **the same beat**, the difference of two frequency vectors, so one formula is checked from both ends. Rectangular membrane eigenvalues match `pi^2 (m^2/a^2 + n^2/b^2)` to 0.00e+00 including the degeneracies (the widely quoted `mn*pi` is a *product* and is a different sequence); circular nodal circles sit at the zeros of `J0` (the zeros of `J'0` are the antinodes); the fringe period `lambda*D/d` is measured back by a *different* op (ratio 0.998-1.003); grating orders round-trip through the existing `grating_wavelengths` to 550.000000 nm and agree with the existing `fraunhofer_pattern`, where a 50 % duty grating drops the even orders and the 3rd/1st intensity ratio is `sinc(m/2)^2` = 1/9; the moire period is predicted before drawing and confirmed by FFT (0.948-0.986); halftoning discards tone but preserves local mean density (0.0517 mean absolute error through a 4-period window); engraving ink coverage matches the closed form `w/d` to 0.0000; hatch direction comes from the existing `structure_tensor_orientation` and lands within 0.3 degrees of a grating whose angle is known by construction; and Lloyd's energy, measured by the existing `stipple_energy`, decreases monotonically with the cell mean being the exact L2 optimum.

Operators: `wave_membrane_mode`, `wave_mode_frequencies`, `wave_nodal_lines`, `wave_two_slit`, `wave_fringe_period`, `wave_grating_orders`, `halftone_screen`, `halftone_moire_period`, `engrave_lines`, `hatch_field`, `mosaic_tiles_sites`, `mosaic_tiles_render`

Runnable: `poc_beats_fringes_and_screens`

### [Cavity optics, the quantum-noise budget and a known waveform in coloured noise, in closed form (the gravitational-wave detector's equations for inspection interferometers, vibrometers and AE)](capabilities/gw-interferometer-quantum-noise-and-matched-filter.md)

Twelve ops in two ledgers. Optics (`opsoptics`, category `cavity`): `fabry_perot_response` (FSR, finesse, linewidth, pole and power gain from mirror transmittances; the public aLIGO design values give F ≈ 445 and a 42 Hz pole), `cavity_strain_transfer` (single pole times the round-trip sinc), `michelson_dc_readout` (DC-readout power, strain slope and the shot-noise limit (1/2L)√(ħcλ/πP)), `pdh_error_signal` (Pound-Drever-Hall, antisymmetric, slope of Black 2001 eq. 15) and `quantum_noise_budget` (Kimble et al. 2001: shot, radiation pressure and the SQL, with the identity shot × rp = SQL²/2). Signals (`ops1d`, category `matched`): `psd_welch`, `whiten_by_psd`, `matched_filter_snr`, `optimal_snr`, `chirp_newtonian`, `chirp_mass_from_track`, `coincidence_delay`. The PoC runs the pipeline on the public GW150914 data and reproduces the published figure (correlation 0.96 / 0.94), the SNRs 19.0 / 13.1 against ≈ 20 / 13 and the 7 ms arrival delay; the second implementation gwinc agrees within 4–12 %.

Operators: `fabry_perot_response`, `cavity_strain_transfer`, `michelson_dc_readout`, `pdh_error_signal`, `quantum_noise_budget`, `psd_welch`, `whiten_by_psd`, `chirp_newtonian`, `chirp_mass_from_track`, `matched_filter_snr`, `optimal_snr`, `coincidence_delay`

Runnable: `poc_gw_detector_pseudo_simulation`

### [Diagnose faults from vibration and sound](capabilities/vibration-and-acoustics.md)

Envelope spectra, cepstra, octave bands and the characteristic frequencies of a rolling-element bearing. The frequencies follow from the geometry, so which peak to look at is decided before measuring, not after.

Operators: `signal_features`, `envelope_spectrum`, `bearing_defect_frequencies`, `octave_spectrum`, `spectrum`

Runnable: `poc_bearing_diagnosis`, `poc_rail_corrugation`

## Compose (7)

### [Align and stack](capabilities/align-and-stack.md)

Align a sequence by voting for the translation, resample sub-pixel, and stack. Point clouds are aligned with ICP.

Operators: `frame_align`, `drizzle_resample`, `icp_point2point_3d`, `interp_scattered`

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

Runnable: `poc_colormap_readability`, `poc_dem_terrain`

### [Draw lines and regions without knowing the background colour](capabilities/inverted-colour-overlays.md)

Draw a polyline or a region in the inverse of whatever is underneath, so the overlay stays visible without knowing the background. `draw="margin"` outlines instead of filling. The one real failure mode — mid-grey, where the complement equals the original — is measured rather than assumed: `annotate_invert_visibility` reports the per-pixel WCAG contrast, and the drawing ops warn (or refuse) when the mark would be invisible.

Operators: `annotate_invert`, `annotate_invert_path`, `annotate_invert_visibility`

Runnable: `annotate_paper_tour`

### [Put text and tables exactly where you want them on an image](capabilities/text-and-tables-on-images.md)

Place text on an image where you actually want it: nine-way anchors, translucent plates, wrapping, and — along a polyline — slanted, vertical (`upright=True`), multi-line (`\n`), start/centre/end alignment and a perpendicular offset. Colour, plus synthetic bold and italic. `annotate_table` turns a tab-separated string into a table whose column widths are **measured with the real font at the requested size**, with a font-size-proportional column gap, automatic right-alignment for numeric columns and a translucent plate. Every one has a `*_layout` twin that returns the geometry so you can check the placement before drawing.

Operators: `text_box`, `annotate_text_path`, `annotate_text_path_layout`, `annotate_table`, `annotate_table_layout`, `measure_text`

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
