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

**Currently 34 capabilities**

## Measure (9)

### [Estimate the camera intrinsic matrix K from multiple planar views (Zhang)](capabilities/camera-intrinsics-calibration.md)

`camera_calibration(object_points, image_points_list)` estimates the intrinsic matrix `K` (fx, fy, cx, cy, skew) from several views of a planar target seen at different tilts, by Zhang's method (two constraints per view collected from the plane homographies). `object_points` are `(x, y)` on the plane; `image_points_list` are the `(row, col)` correspondences per view. It returns `K` plus the per-view homographies, per-view reprojection RMS, and `orientation_rank_ratio` — how strongly the view orientations constrain `K`. The recovered `K` feeds `estimate_distortion`, `undistort_image`, PnP and triangulation. Two honest caveats it carries: the plane must be **tilted** between views or the intrinsics are unconstrained (a degeneracy the code detects and refuses), and **reprojection error does not reveal a bad view geometry** — focal length and target distance trade off almost invisibly in the image (the `poc_camera_calibration` example quantifies this). fail-closed on fewer than three views, mismatched point counts, degenerate orientation, or a non-finite / non-positive `K`.

Operators: `camera_calibration`, `estimate_distortion`, `intrinsic_matrix`, `decompose_intrinsics`

Runnable: `camera_intrinsics_calibration`

### [Seeing the complex plane as an area (domain colouring, basins, escape time, flow)](capabilities/complex-plane-fields.md)

Draw complex analysis as an area rather than a curve: the value field of a rational function, its domain colouring, Newton's basins, escape time, and potential flow past a Joukowski aerofoil. None of the pictures is judged by eye. The winding of the field is counted by this family's existing `cplx_winding_number` (+3, +1, -2 as the zeros and poles say); the hue winding in the *rendered image* recovers the order of a zero from pixels alone; Cayley's 1879 theorem gives the degree-2 basins in closed form and all 262,144 pixels agree; the main cardioid and period-2 bulb prove interiority without iterating (zero counterexamples, and honestly only 90.1 % of what actually stays); the flow field is holomorphic so `cplx_cr_residual` reads 2.06e-04; and the lift exceeds thin-aerofoil theory by exactly the thickness ratio a/b.

Operators: `cplx_plane_grid`, `cplx_rational_field`, `cplx_domain_colour`, `cplx_newton_basins`, `cplx_escape_time`, `mandelbrot_interior`, `potential_flow_joukowski`, `joukowski_circulation`

Runnable: `poc_complex_plane_fields`

### [Estimate lens distortion coefficients from straight lines (plumb-line, no board)](capabilities/estimate-lens-distortion.md)

The upstream of `undistort_image`: it *measures* the Brown–Conrady coefficients instead of taking them as given. From point lists sampled along features that are straight in the world (`lines`, each `(N_i, 2)` in `(x=col, y=row)`) plus the intrinsics `K`, `estimate_distortion` returns `dist = [k1, k2, p1, p2, k3]` ready for `undistort_image` / `undistort_points`. It is the plumb-line method (Brown 1971; Devernay–Faugeras 2001): minimize, over the coefficients, the summed perpendicular scatter of the *undistorted* lines, so lines that are straight in the world become straight once distortion is removed. No correspondences, no calibration board, no known spacing — only that each line is straight (the line-pattern idea Discorpy uses). The principal point of `K` is the distortion centre and is held fixed (the method cannot separate it from `p1, p2`). `radial` in `{1, 2, 3}` frees `k1`; `k1, k2`; or `k1, k2, k3`; `tangential` frees `p1, p2`. On clean synthetic lines the coefficients come back to machine precision; with pixel noise they degrade gracefully. Requires SciPy. fail-closed on fewer than two lines or a line with fewer than three points.

Operators: `estimate_distortion`, `undistort_image`, `distort_points`, `undistort_points`

Runnable: `estimate_lens_distortion`

### [Put measurements on the Earth (ECEF, height frames, local ENU)](capabilities/geodetic-frames.md)

Convert geodetic coordinates to Earth-centred Cartesian (ECEF), to a local ENU frame, and between datums; convert between the two kinds of height (ellipsoidal h from GNSS and orthometric H used by maps) through a published geoid grid, and measure the residual `h - H - N` that exposes a height-frame mix-up. Checked against 523 published NGS survey marks: ECEF agrees with the published Cartesian coordinates to 0.5 mm rms, bilinear interpolation of a 0.25-degree GEOID18 grid lands within 11.1 cm rms of the published point values, and using h as if it were H shifts the answer by 16.75 m (median) in that region.

Operators: `dem_geodetic_to_ecef`, `dem_ecef_to_geodetic`, `dem_geoid_height`, `dem_height_frame_convert`, `dem_height_frame_residual`, `dem_datum_shift_3param`, `dem_enu_from_geodetic`, `dem_geodetic_from_enu`

Runnable: `poc_geodetic_height_frames`, `poc_geodetic_benchmarks_real`, `dem_geodesy_tour`

### [How much of that number is your measuring, not your process (gauge R&R and measurement uncertainty)](capabilities/measurement-system-and-uncertainty.md)

Separate how much of a number comes from the parts and how much from the act of measuring, then combine the components of a single measurement into a reportable uncertainty. Every operator is a closed-form standards model with an exact identity to check it against. The analysis-of-variance decomposition closes algebraically (`SS_total = SS_part + SS_operator + SS_interaction + SS_error`, relative difference 1e-16); repeatability equals the mean of the per-cell `np.var(ddof=1)` that numpy computes independently; the published worked example (10 parts x 3 operators x 3 trials) is reproduced to 1.5e-06 on EV/AV/GRR/PV with contribution percentages 3.4/4.4/7.8/92.2 exactly. Whether the interaction is kept or pooled into error moves EV by **7.3 %**, so the model actually used is reported (`interaction_pooled`, `interaction_p`), and a negative variance component — which happens in **31 of 40** synthetic runs when the true component is zero — is clamped to zero but declared rather than hidden. On the uncertainty side: the divisors that turn a distribution shape into a standard uncertainty are exact (`a/sqrt(3)`, `a/sqrt(6)`, `a/sqrt(2)`); ignoring correlation errs in **both directions on the same data** (u_c of resistance 0.0702 -> 0.1945, a 2.8x overestimate, while reactance goes the other way); the effective degrees of freedom are truncated immediately before the t lookup as the standard requires (16.64 -> 16 gives k = 2.1199, matching the published 2.12); and the propagation law's breakdown at a stationary point is returned as structure (`guf_valid`, `invalid_reasons`) rather than as a silent `u_c = 0`. A sum of four rectangular distributions has an exact coverage interval via Irwin-Hall, `sqrt(3)(2 x 0.6^(1/4) - 4) = -3.879407`, against which the propagation law is structurally 0.040521 too wide.

Operators: `msa_anova_table`, `msa_gauge_rr`, `msa_bias_linearity`, `msa_attribute_agreement`, `gum_standard_uncertainty`, `gum_propagate`, `gum_expanded`, `gum_monte_carlo`, `gum_validate`, `spc_capability`, `spc_xbar_r`

Runnable: `poc_measurement_system_analysis`

### [Measure dimensions from an image, below the pixel](capabilities/subpixel-2d-metrology.md)

Locate edges along a measurement line from the intensity gradient, at sub-pixel resolution, and read a dimension as the distance between paired edges. Unlike counting thresholded pixels, the answer does not move when the threshold does.

Operators: `measure_pos`, `measure_pairs`, `blob_label`, `blob_select`

Runnable: `poc_dimensional_inspection`, `poc_screw_thread_metrology`

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

## Detect (3)

### [Segment regions, select them, and count](capabilities/blob-and-region.md)

Label connected components, select them by area, shape or position, and count them. Touching objects can be separated with a watershed.

Operators: `blob_label`, `blob_select`, `blob_count`, `watersheds`

Runnable: `poc_cell_counting`, `poc_particle_sizing`, `poc_real_coin_metrology`

### [Fix the text inside an image against the string it should read](capabilities/fix-text-in-images.md)

Fix the text inside an image against the string it should read, without regenerating the image: pass `{"items": [{"text": "...", "bbox": [x, y, w, h]}]}` to `glyph_correct_spec` (Python) or `fullseye_fix_text` (MCP). Nothing is recognised — the intended string is given, so each cell is verified one-to-one against one character, and the threshold comes from the typeface noise floor measured on the fonts of the environment. `repair_flagged` replaces only the glyphs above the floor and rolls back any replacement that does not verify; `rewrite_line` redraws the whole line in one typeface. The report carries a per-line `status`, a machine-readable `reason_code` for refusals, and `mismatch` (`typo` / `unrelated`) so that a caller notices when the original text has nothing to do with the intended one.

Operators: `glyph_correct_spec`, `glyph_make_spec`, `glyph_find_text_lines`, `glyph_rewrite_line`, `glyph_find_plate`, `glyph_typeface_noise_floor`, `glyph_rendering_noise_floor`, `glyph_distance`, `glyph_replace`, `glyph_split_cells`, `glyph_fonts`

Runnable: `fix_text_in_image`, `poc_glyph_typo_detection`

### [Find small point-like targets and locate them below the pixel](capabilities/point-target-detection.md)

Pick local maxima above a robustly estimated background plus k sigma, and return sub-pixel centroids. The name is astronomical but the method is domain-neutral: drifting objects, small defects, fluorescent puncta, particles.

Operators: `star_detect`, `peak_subbin`, `find_peaks`, `noise_sigma`

Runnable: `poc_search_sweep_width`, `poc_astro_photometry`

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

## Light and colour (4)

### [Measure colour (XYZ / Lab / colour difference)](capabilities/colour-and-delta-e.md)

From spectral reflectance or RGB, compute CIE XYZ and Lab, then colour differences under CIE76 or CIEDE2000. The difference can also be returned as a per-pixel map.

Operators: `rgb_to_lab`, `xyz_to_lab`, `delta_e_2000`, `cie_xyz_from_wavelength`

Runnable: `poc_white_balance`, `poc_pigment_unmixing`

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

## Waves and signals (3)

### [Beamform for direction, separate range from velocity](capabilities/beamforming-and-range-doppler.md)

Form beams from an array snapshot to get directions of arrival, and build a range-Doppler map from an FMCW return, mapping detections back to metres and metres per second.

Operators: `beamform_delay_sum`, `beamform_doa`, `range_doppler_map`, `range_doppler_peaks`

Runnable: `poc_multibeam_bathymetry`, `poc_bev_sensor_fusion`

### [One beat (membrane modes, fringes, diffraction orders, print moire, and turning tone into ink)](capabilities/beats-fringes-and-screens.md)

Build membrane eigenmodes and nodal lines, two-slit fringes, grating orders, and the printing side (halftone screens, moire, engraving lines, structure-following hatching, mosaic tiles) — and score every one of them against a truth that lives outside the picture. The thesis: a two-slit fringe and the moire of two superposed halftone screens are **the same beat**, the difference of two frequency vectors, so one formula is checked from both ends. Rectangular membrane eigenvalues match `pi^2 (m^2/a^2 + n^2/b^2)` to 0.00e+00 including the degeneracies (the widely quoted `mn*pi` is a *product* and is a different sequence); circular nodal circles sit at the zeros of `J0` (the zeros of `J'0` are the antinodes); the fringe period `lambda*D/d` is measured back by a *different* op (ratio 0.998-1.003); grating orders round-trip through the existing `grating_wavelengths` to 550.000000 nm and agree with the existing `fraunhofer_pattern`, where a 50 % duty grating drops the even orders and the 3rd/1st intensity ratio is `sinc(m/2)^2` = 1/9; the moire period is predicted before drawing and confirmed by FFT (0.948-0.986); halftoning discards tone but preserves local mean density (0.0517 mean absolute error through a 4-period window); engraving ink coverage matches the closed form `w/d` to 0.0000; hatch direction comes from the existing `structure_tensor_orientation` and lands within 0.3 degrees of a grating whose angle is known by construction; and Lloyd's energy, measured by the existing `stipple_energy`, decreases monotonically with the cell mean being the exact L2 optimum.

Operators: `wave_membrane_mode`, `wave_mode_frequencies`, `wave_nodal_lines`, `wave_two_slit`, `wave_fringe_period`, `wave_grating_orders`, `halftone_screen`, `halftone_moire_period`, `engrave_lines`, `hatch_field`, `mosaic_tiles_sites`, `mosaic_tiles_render`

Runnable: `poc_beats_fringes_and_screens`

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

## Draw (2)

### [Turn a photograph into a single line (stipple, tour, rotating circles)](capabilities/one-stroke-drawing.md)

Turn the tone of a picture into a single closed line a pen could draw without lifting: points are placed by darkness (weighted Lloyd), ordered into a closed tour, resampled at equal arc length, and rewritten as a chain of rotating circles via the complex Fourier series. Nothing is judged by eye. The stipple is checked against a ramp (correlation 0.9946) with a flat image as the control — and the *exponent* is measured too, because a centroidal Voronoi tessellation puts density at sqrt(rho), not rho (Gersho): 0.61 measured, 0.77 with the weight squared. The tour is checked against the minimum spanning tree, which no closed tour can beat (1.146, against 41.4 for coordinate order); the tone is measured (0.984, against +0.013 for random points); the pen width that reproduces the mean tone is solved in closed form and falls 11 % short, which *is* the stroke overlap; the resampling is checked against Nyquist (the error falls as 1/N: 6.5, 3.3, 1.6 % of the stroke length); and Parseval turns the number of circles into a prediction made before the drawing exists.

Operators: `stipple_points_from_image`, `stipple_energy`, `stroke_tour_closed`, `mst_length`, `stroke_resample_closed`, `stroke_tone_error`, `contour_fourier_complex`, `contour_epicycle_chain`, `contour_fourier_truncation_energy`

Runnable: `poc_one_stroke_epicycles`

### [Theorems as pictures (Apollonian, Ford, geodesic dome, phyllotaxis, IFS, space-filling curves)](capabilities/theorems-as-pictures.md)

Draw mathematically beautiful figures whose correctness is asserted by a theorem rather than by eye: an Apollonian gasket (every tangent quadruple satisfies Descartes' circle theorem to 1e-13, and an integral seed stays integral for ever), Ford circles (tangency agrees with `|ps - qr| = 1` on all 1,081 pairs, and the count matches `1 + sum of Euler's totient`), a geodesic dome (exactly 12 degree-5 vertices at every subdivision — counted by the existing `graph_degree_table`, not by this module), Vogel's phyllotactic spiral (neighbour index gaps land on Fibonacci numbers only at the golden angle: 7/7 against 2/7 for the controls), IFS attractors (Moran's closed-form dimension agrees with the existing box-counting `fractal_dimension`, and non-similarity maps are refused), and space-filling curves (a permutation of 4^n cells with unit steps; locality reported as a table, not a slogan).

Operators: `circle_packing_apollonian`, `ford_circles`, `phyllotaxis_pattern`, `neighbour_index_gaps`, `ifs_fractal`, `ifs_similarity_dimension`, `space_filling_curve`, `curve_locality`, `geodesic_dome`

Runnable: `poc_theorems_as_pictures`
