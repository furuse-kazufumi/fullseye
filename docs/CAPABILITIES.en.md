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

**Currently 21 capabilities**

## Measure (4)

### [Put measurements on the Earth (ECEF and geodetic)](capabilities/geodetic-frames.md)

Convert between geodetic (latitude, longitude, height) and Earth-centred Cartesian (ECEF) coordinates. The round-trip floor measures 6.4e-12 degrees in latitude and 8.5e-07 m in height (worst case over 4000 points).

Operators: `dem_geodetic_to_ecef`, `dem_ecef_to_geodetic`

Runnable: `poc_geodetic_height_frames`, `dem_geodesy_tour`

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

## Shape (2)

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

## Waves and signals (2)

### [Beamform for direction, separate range from velocity](capabilities/beamforming-and-range-doppler.md)

Form beams from an array snapshot to get directions of arrival, and build a range-Doppler map from an FMCW return, mapping detections back to metres and metres per second.

Operators: `beamform_delay_sum`, `beamform_doa`, `range_doppler_map`, `range_doppler_peaks`

Runnable: `poc_multibeam_bathymetry`, `poc_bev_sensor_fusion`

### [Diagnose faults from vibration and sound](capabilities/vibration-and-acoustics.md)

Envelope spectra, cepstra, octave bands and the characteristic frequencies of a rolling-element bearing. The frequencies follow from the geometry, so which peak to look at is decided before measuring, not after.

Operators: `signal_features`, `envelope_spectrum`, `bearing_defect_frequencies`, `octave_spectrum`, `spectrum`

Runnable: `poc_bearing_diagnosis`, `poc_rail_corrugation`

## Compose (3)

### [Align and stack](capabilities/align-and-stack.md)

Align a sequence by voting for the translation, resample sub-pixel, and stack. Point clouds are aligned with ICP.

Operators: `frame_align`, `drizzle_resample`, `icp_point2point_3d`, `interp_scattered`

Runnable: `poc_astro_photometry`, `poc_registration_basin`

### [Write typed op results as JSON and read them back bit-for-bit](capabilities/typed-results-as-json.md)

One JSON form per sort and one way back: a self-describing envelope, float arrays as base64 little-endian float64 (bit-exact round trips, tested with the same probes the op gates use), run-length regions, contours as shape plus point lists, tables as plain JSON. Thin conveniences ride along — `save_json` / `load_json` for a file, `to_json_lines` / `from_json_lines` for a growing ledger as JSON Lines. Unknown sorts, shapes that do not fit the sort and wrong envelope versions are refused — nothing is guessed from an array's shape.

Operators: `to_json`, `from_json`, `to_jsonable`, `from_jsonable`, `save_json`, `load_json`, `to_json_lines`, `from_json_lines`, `as_value`, `apply_json`, `is_envelope`

Runnable: `typed_results_json`

### [Render typed op results as Markdown, with an exact JSON block to read back](capabilities/typed-results-as-markdown.md)

The Markdown companion of jsonio. `to_markdown` renders a typed value as GFM — real tables for tabular and small numeric sorts (capped, with a truncation note), a one-line summary for things that are not text (an image is its shape and range). `json_block` wraps the exact JSON envelope in a ```` ```json ```` fence so a value survives inside prose and round-trips bit-for-bit through `extract_json`, which pulls every fullseye envelope out of a Markdown string and ignores foreign fences. `report` folds a list of sections into one document that is both readable and, with `with_json=True`, machine-recoverable. Fail-closed on an unknown sort, exact wherever a machine reads it back.

Operators: `to_markdown`, `json_block`, `extract_json`, `report`

Runnable: `typed_results_markdown`

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
