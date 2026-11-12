<div class="vlang" markdown="1">

[日本語](../index.md) · **English** · [简体中文](../zh/index.md) · [繁體中文](../tw/index.md) · [한국어](../ko/index.md) · [Deutsch](../de/index.md) · [हिन्दी](../hi/index.md) · [Français](../fr/index.md)

</div>

# Fullseye — ViEW2026

**Presenting: Thu 3 Dec 2026, 14:40–15:50 JST, Interactive Session 2, IS2-19** (Pacifico Yokohama)

<div class="vintro"><img src="../thumbs/fullseye_intro.jpg" alt="One 3-D scene turned into picture, depth, normals, shadow mask and edges, each processed further" width="640" height="468"><div class="vt"><p>A foundation that hands physics simulation (including sensing such as optical design and 3-D measurement) and classic image processing to an AI through MCP and RAG, lets it work out a combination for each task, and solves the task interactively while checking type consistency and evaluating against ground truth. Open source (Apache-2.0).</p><p><a href="about.md">About Fullseye (reading)</a></p></div></div>

Tap a tile to open the video or figure (▶ = moving).

This page shows only 20 exhibits. The other 294 are on the [Extras page](more.md).

<style>
.vlang { font-size: 14px; line-height: 2; }
.vg { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin: 12px 0 20px; }
.vg.vs { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; }
@media (min-width: 600px) { .vg { grid-template-columns: repeat(3, minmax(0, 1fr)); } .vg.vs { grid-template-columns: repeat(5, minmax(0, 1fr)); } }
@media (min-width: 900px) { .vg { grid-template-columns: repeat(4, minmax(0, 1fr)); } .vg.vs { grid-template-columns: repeat(7, minmax(0, 1fr)); } }
.vg a, .vser a { display: block; position: relative; text-decoration: none; color: inherit; }
.vg img { display: block; width: 100%; max-width: 100%; height: auto; aspect-ratio: 1 / 1; object-fit: cover; border-radius: 6px; background: #222; }
.vg picture { display: block; width: 100%; aspect-ratio: 1 / 1; overflow: hidden; border-radius: 6px; background: #fff; }
.vg picture img { height: 100%; aspect-ratio: auto; object-fit: contain; border-radius: 0; background: #fff; }
.vg b { position: absolute; top: 6px; right: 6px; background: rgba(0,0,0,.6); color: #fff; font-size: 12px; padding: 1px 6px; border-radius: 9px; }
.vg span { display: block; font-size: 13px; line-height: 1.3; margin-top: 3px; }
.vg.vs span { font-size: 11px; }
.vser { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin: 12px 0 20px; }
@media (min-width: 600px) { .vser { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
.vser img { display: block; width: 100%; max-width: 100%; height: auto; aspect-ratio: 16 / 9; object-fit: cover; border-radius: 8px; background: #222; }
.vser strong { display: block; font-size: 14px; margin-top: 3px; line-height: 1.3; }
.vser span { display: block; font-size: 12px; line-height: 1.3; }
details.vall { margin: 6px 0; }
details.vall > summary { font-size: 15px; padding: 6px 0; cursor: pointer; }
.vl li { margin-bottom: 8px; }
.vintro { display: flex; gap: 20px; align-items: flex-start; margin: 14px 0; }
.vintro img { flex: 0 0 300px; width: 300px; max-width: 100%; height: auto; border-radius: 6px; }
.vintro .vt p { margin: 0 0 8px; }
.vc { display: flex; gap: 16px; align-items: flex-start; margin: 18px 0; }
.vc > a:first-child { flex: 0 0 260px; position: relative; display: block; text-decoration: none; color: inherit; }
.vc > a img { display: block; width: 100%; max-width: 100%; height: auto; aspect-ratio: 1 / 1; object-fit: cover; border-radius: 6px; background: #222; }
.vc > a picture { display: block; width: 100%; aspect-ratio: 1 / 1; overflow: hidden; border-radius: 6px; background: #fff; }
.vc > a picture img { height: 100%; aspect-ratio: auto; object-fit: contain; border-radius: 0; background: #fff; }
.vc > a b { position: absolute; top: 6px; right: 6px; background: rgba(0,0,0,.6); color: #fff; font-size: 12px; padding: 1px 6px; border-radius: 9px; }
.vt { flex: 1 1 auto; min-width: 0; }
.vt .vh { font-size: 17px; font-weight: 600; line-height: 1.4; margin: 0 0 6px; }
.vt p { margin: 0 0 6px; }
.vt .vm { font-size: 14px; color: #57606a; }
.vt details { font-size: 14px; margin: 4px 0; }
.vt summary { cursor: pointer; }
.vc.vv { margin: 10px 0; }
.vc.vv > a:first-child { flex-basis: 96px; }
@media (max-width: 600px) {
  .vintro { flex-direction: column-reverse; gap: 8px; }
  .vintro img { flex: 0 0 auto; width: 100%; max-width: 240px; }
  .vc { flex-direction: column; gap: 8px; }
  .vc > a:first-child { flex: 0 0 auto; width: 150px; }
  .vc.vv { flex-direction: row; gap: 12px; }
  .vc.vv > a:first-child { width: 80px; flex: 0 0 80px; }
}
</style>

## Try it yourself

Run the paper's figures yourself, on a phone too. Switch methods with the tabs and drag the 3-D views to rotate them.

<div class="vc vv"><a class="vvi" href="../viewers/industrial_oct_anim3d.html?lang=en"><img src="../thumbs/poc_industrial_oct.jpg" alt="Layer structure in industrial OCT" loading="lazy" width="96" height="96"></a><div class="vt"><div class="vh"><a href="../viewers/industrial_oct_anim3d.html?lang=en">Layer structure in industrial OCT</a></div><p>Sweep through depth and explore a coating B-scan and its layer-thickness measurement. (4.0 MB)</p></div></div>

<div class="vc vv"><a class="vvi" href="../viewers/phase_measuring_deflectometry_anim3d.html?lang=en"><img src="../thumbs/poc_phase_measuring_deflectometry.jpg" alt="Surface shape by deflectometry" loading="lazy" width="96" height="96"></a><div class="vt"><div class="vh"><a href="../viewers/phase_measuring_deflectometry_anim3d.html?lang=en">Surface shape by deflectometry</a></div><p>Sweep the fringe phase and watch a surface dent invisible in a photograph emerge. (14.9 MB)</p></div></div>

<div class="vc vv"><a class="vvi" href="../viewers/poc_cad_scan_deviation.html?lang=en"><img src="../thumbs/poc_cad_scan_deviation.jpg" alt="CAD versus a scanned point cloud" loading="lazy" width="96" height="96"></a><div class="vt"><div class="vh"><a href="../viewers/poc_cad_scan_deviation.html?lang=en">CAD versus a scanned point cloud</a></div><p>Alignment absorbs defects: a part whose true value is 1.2 µm shows a 121 µm dent that does not exist.</p></div></div>

<div class="vc vv"><a class="vvi" href="../viewers/poc_photoelasticity.html?lang=en"><img src="../thumbs/poc_photoelasticity.jpg" alt="Photoelasticity" loading="lazy" width="96" height="96"></a><div class="vt"><div class="vh"><a href="../viewers/poc_photoelasticity.html?lang=en">Photoelasticity</a></div><p>Rotating the analyser moves the photoelastic fringes and changes the mean intensity inside the disc (over 0–135°)</p></div></div>

<div class="vc vv"><a class="vvi" href="../viewers/poc_polarization_specular.html?lang=en"><img src="../thumbs/poc_polarization_specular.jpg" alt="Polarization" loading="lazy" width="96" height="96"></a><div class="vt"><div class="vh"><a href="../viewers/poc_polarization_specular.html?lang=en">Polarization</a></div><p>Polarisation strips specular glare; what remains changes with incidence angle and is smallest near the Brewster angle (swept on a synthetic fringe scene)</p></div></div>

<div class="vc vv"><a class="vvi" href="../viewers/poc_thermography_ndt.html?lang=en"><img src="../thumbs/poc_thermography_ndt.jpg" alt="Pulse thermography depth" loading="lazy" width="96" height="96"></a><div class="vt"><div class="vh"><a href="../viewers/poc_thermography_ndt.html?lang=en">Pulse thermography depth</a></div><p>Cutting the fit window from 25 s to 4 s shrinks the worst depth error of small flaws from +627% to ±14%. The cause was the choice of window, not the physics.</p></div></div>

## Showcase

Some PoC descriptions are in English.

<div class="vc"><a href="../../articles/assets/poc/poc_phase_measuring_deflectometry/03_photo_vs_pmd.png"><picture><source media="(prefers-reduced-motion: reduce)" srcset="../../articles/assets/poc/poc_phase_measuring_deflectometry/03_photo_vs_pmd.png"><img src="../../articles/assets/poc/poc_phase_measuring_deflectometry/story.en.gif" alt="A dent invisible in photos appears in a fringe mirror image" loading="lazy" width="260" height="260"></picture></a><div class="vt"><div class="vh"><a href="../../articles/assets/poc/poc_phase_measuring_deflectometry/03_photo_vs_pmd.png">A dent invisible in photos appears in a fringe mirror image</a></div><p>A very shallow dent in glossy paint is practically invisible in an ordinary photograph. Projecting fringes on a screen in front of the surface and reading how their mirror image bends gives curvature, and a dent 3 µm deep stands out clearly. The flat-looking photo sits next to curvature maps in which the dents appear.</p><p class="vm">Ground truth: Synthetic · <a href="more.md#d-poc-phase-measuring-deflectometry">Details</a></p></div></div>

<div class="vc"><a href="../../articles/assets/poc/poc_industrial_oct/01_real_paint_bscans.png"><picture><source media="(prefers-reduced-motion: reduce)" srcset="../../articles/assets/poc/poc_industrial_oct/01_real_paint_bscans.png"><img src="../../articles/assets/poc/poc_industrial_oct/story.en.gif" alt="Paint layer thickness without cutting (industrial OCT)" loading="lazy" width="260" height="260"></picture></a><div class="vt"><div class="vh"><a href="../../articles/assets/poc/poc_industrial_oct/01_real_paint_bscans.png">Paint layer thickness without cutting (industrial OCT)</a></div><p>We want to see the layers of paint and multilayer film in depth without cutting them. Clear-coat thicknesses computed from public raw interference spectra of automotive paint agree with the paper's OCT values within 1.5 µm. Layers too thin to separate are reported as unmeasurable instead of guessed.</p><p class="vm">Ground truth: Real data · <a href="more.md#d-poc-industrial-oct">Details</a></p></div></div>

<div class="vc"><a href="../../articles/assets/poc/poc_hyperspectral_foreign_matter/04_real_pork_belly.png"><picture><source media="(prefers-reduced-motion: reduce)" srcset="../../articles/assets/poc/poc_hyperspectral_foreign_matter/01_real_polymer_flakes.png"><img src="../../articles/assets/poc/poc_hyperspectral_foreign_matter/story.en.gif" alt="Finding meat-coloured foreign matter with spectral imaging" loading="lazy" width="260" height="260"></picture></a><div class="vt"><div class="vh"><a href="../../articles/assets/poc/poc_hyperspectral_foreign_matter/04_real_pork_belly.png">Finding meat-coloured foreign matter with spectral imaging</a></div><p>Foreign matter the same colour as meat or kernels cannot be told apart by a colour camera. Classifying public real images as spectral data detected debris on pork belly with 1.1 % false alarms. With fewer bands the false alarms grew, so a band set that sufficed on synthetic data did not suffice on real data.</p><p class="vm">Ground truth: Real data · <a href="more.md#d-poc-hyperspectral-foreign-matter">Details</a></p></div></div>

<div class="vc"><a href="../../articles/assets/poc/poc_thin_film_reflectometry/01_real_micrograph_thickness.png"><picture><source media="(prefers-reduced-motion: reduce)" srcset="../../articles/assets/poc/poc_thin_film_reflectometry/01_real_micrograph_thickness.png"><img src="../../articles/assets/poc/poc_thin_film_reflectometry/story.en.gif" alt="Oxide thickness mapped from micrograph colours" loading="lazy" width="260" height="260"></picture></a><div class="vt"><div class="vh"><a href="../../articles/assets/poc/poc_thin_film_reflectometry/01_real_micrograph_thickness.png">Oxide thickness mapped from micrograph colours</a></div><p>Oxide thickness on silicon can be read from interference fringes and colours in reflected light. From a real micrograph published by other researchers, a per-pixel thickness map was drawn, centred on 87.4 nm. It stays below the reference value, and the camera's colour sensitivity is unknown.</p><p class="vm">Ground truth: Real data · <a href="more.md#d-poc-thin-film-reflectometry">Details</a></p></div></div>

<div class="vc"><a href="../../articles/assets/poc/poc_telecentric_metrology/08_real_alignment_plate.png"><picture><source media="(prefers-reduced-motion: reduce)" srcset="../../articles/assets/poc/poc_telecentric_metrology/08_real_alignment_plate.png"><img src="../../articles/assets/poc/poc_telecentric_metrology/story.en.gif" alt="Magnification checked to 0.05 % on public telecentric images" loading="lazy" width="260" height="260"></picture></a><div class="vt"><div class="vh"><a href="../../articles/assets/poc/poc_telecentric_metrology/08_real_alignment_plate.png">Magnification checked to 0.05 % on public telecentric images</a></div><p>Measured in one image, a stepped part looks larger where it is nearer, so an ordinary lens misreads its dimensions. On the published real images from a telecentric lens, the magnification matched the paper within 0.05 %. In the synthetic chapter, telecentric magnification barely moves with object height.</p><p class="vm">Ground truth: Real data · <a href="more.md#d-poc-telecentric-metrology">Details</a></p></div></div>

<div class="vc"><a href="../../articles/assets/poc/poc_virtual_sem_kv_cd_bse/05_sem_same_part_3kv_3detectors.png"><picture><source media="(prefers-reduced-motion: reduce)" srcset="../../articles/assets/poc/poc_virtual_sem_kv_cd_bse/05_sem_same_part_3kv_3detectors.png"><img src="../../articles/assets/poc/poc_virtual_sem_kv_cd_bse/story.en.gif" alt="Virtual SEM: voltage changes both image and line width" loading="lazy" width="260" height="260"></picture></a><div class="vt"><div class="vh"><a href="../../articles/assets/poc/poc_virtual_sem_kv_cd_bse/05_sem_same_part_3kv_3detectors.png">Virtual SEM: voltage changes both image and line width</a></div><p>An SEM image is not a photo of the surface but a tally of electrons escaping after scattering inside the solid. A model that tracks each electron was checked against measured backscatter data for 7 elements. On the same line, the beam energy decides which sidewall height is read as the linewidth.</p><p class="vm">Ground truth: Published values · <a href="more.md#d-poc-virtual-sem-kv-cd-bse">Details</a></p></div></div>

<div class="vc"><a href="../../articles/assets/poc/poc_cad_scan_deviation/14_align_orbit.gif"><picture><source media="(prefers-reduced-motion: reduce)" srcset="../../articles/assets/poc/poc_cad_scan_deviation/01_scene.png"><img src="../../articles/assets/poc/poc_cad_scan_deviation/story.en.gif" alt="Alignment hides defects: CAD versus scan" loading="lazy" width="260" height="260"></picture><b>&#9654;</b></a><div class="vt"><div class="vh"><a href="../../articles/assets/poc/poc_cad_scan_deviation/14_align_orbit.gif">Alignment hides defects: CAD versus scan</a></div><p>Aligning a scan to its design can absorb a defect or move it elsewhere. Known dents and warps were added to a part; even the defect-free control produced 66.5 square mm of false rejected area. Rigid-like deviations shrink, while nearest points jump across edges and create a fictitious dent.</p><p class="vm">Ground truth: Synthetic · <a href="more.md#d-poc-cad-scan-deviation">Details</a></p></div></div>

<div class="vc"><a href="../../articles/assets/poc/poc_good_sample_variation_model/04_visa_explanation.png"><picture><source media="(prefers-reduced-motion: reduce)" srcset="../../articles/assets/poc/poc_good_sample_variation_model/01_band_width_alignment.png"><img src="../../articles/assets/poc/poc_good_sample_variation_model/story.en.gif" alt="Flagging defects from good-part variation: the declared false-alarm rate fails on real images" loading="lazy" width="260" height="260"></picture></a><div class="vt"><div class="vh"><a href="../../articles/assets/poc/poc_good_sample_variation_model/04_visa_explanation.png">Flagging defects from good-part variation: the declared false-alarm rate fails on real images</a></div><p>A classic inspection learns the usual per-pixel variation from good parts and flags what falls outside. Here the band is set by a false-alarm rate declared in advance and scored on 200 public real images. Alignment mattered more than the number of good parts, and the declared rate was not kept.</p><p class="vm">Ground truth: Real data · <a href="more.md#d-poc-good-sample-variation-model">Details</a></p></div></div>

<div class="vc"><a href="../../articles/assets/poc/poc_ct_casting_sparse_views/04_dual_energy.png"><picture><source media="(prefers-reduced-motion: reduce)" srcset="../../articles/assets/poc/poc_ct_casting_sparse_views/01_slices.png"><img src="../../articles/assets/poc/poc_ct_casting_sparse_views/story.en.gif" alt="CT of Casting Voids: The Reconstruction That Wins on RMSE Does Not Always Win on Void Volume" loading="lazy" width="260" height="260"></picture></a><div class="vt"><div class="vh"><a href="../../articles/assets/poc/poc_ct_casting_sparse_views/04_dual_energy.png">CT of Casting Voids: The Reconstruction That Wins on RMSE Does Not Always Win on Void Volume</a></div><p>Voids in a synthetic aluminium casting were scanned with cone-beam CT, rebuilt by several methods, and scored on exact ellipsoids. With 12 views, the classic method that ranks last by image error sized the voids better than the best iterative one. The best-looking reconstruction is not always the best measurement.</p><p class="vm">Ground truth: Synthetic · <a href="more.md#d-poc-ct-casting-sparse-views">Details</a></p></div></div>

<div class="vc"><a href="../../articles/assets/poc/poc_ai_built_inspection_scored/01_crack_real.png"><picture><source media="(prefers-reduced-motion: reduce)" srcset="../../articles/assets/poc/poc_ai_built_inspection_scored/01_crack_real.png"><img src="../../articles/assets/poc/poc_ai_built_inspection_scored/story.en.gif" alt="Scoring inspections built by an AI on real data" loading="lazy" width="260" height="260"></picture></a><div class="vt"><div class="vh"><a href="../../articles/assets/poc/poc_ai_built_inspection_scored/01_crack_real.png">Scoring inspections built by an AI on real data</a></div><p>We gave an AI a task in natural language and let it assemble the inspection recipe. It was scored on 400 public crack images against the labels from their source, and each failure was sorted into tool, MCP or model. Cloud LLMs beat chance but did not reach the existing recipes.</p><p class="vm">Ground truth: Real data · <a href="more.md#d-poc-ai-built-inspection-scored">Details</a></p></div></div>

<div class="vc"><a href="../../articles/assets/poc/poc_bottle_pattern_inverse/01_checker_through_bottle.png"><picture><source media="(prefers-reduced-motion: reduce)" srcset="../../articles/assets/poc/poc_bottle_pattern_inverse/01_checker_through_bottle.png"><img src="../../articles/assets/poc/poc_bottle_pattern_inverse/story.en.gif" alt="Reading a glass bottle back from background stripes (simulation): recovery under shared assumptions, what cannot be separated or detected" loading="lazy" width="260" height="260"></picture></a><div class="vt"><div class="vh"><a href="../../articles/assets/poc/poc_bottle_pattern_inverse/01_checker_through_bottle.png">Reading a glass bottle back from background stripes (simulation): recovery under shared assumptions, what cannot be separated or detected</a></div><p>A transparent bottle distorts the stripes behind it. For each pixel we find where the background is seen, fit the bottle geometry and indices backwards, and score 5 fill states against the true values of the simulation. Quantities that are inseparable and errors that stay undetectable are reported too.</p><p class="vm">Ground truth: Synthetic · <a href="more.md#d-poc-bottle-pattern-inverse">Details</a></p></div></div>

<div class="vc"><a href="../../articles/assets/poc/poc_real_tum_rgbd_slam/02_trajectory.png"><picture><source media="(prefers-reduced-motion: reduce)" srcset="../../articles/assets/poc/poc_real_tum_rgbd_slam/02_trajectory.png"><img src="../../articles/assets/poc/poc_real_tum_rgbd_slam/story.en.gif" alt="Scoring Frame-to-Frame Alignment on Public RGB-D Data: The Error Falls to 0.42 Times, About Level With a Constant-Velocity Guess" loading="lazy" width="260" height="260"></picture></a><div class="vt"><div class="vh"><a href="../../articles/assets/poc/poc_real_tum_rgbd_slam/02_trajectory.png">Scoring Frame-to-Frame Alignment on Public RGB-D Data: The Error Falls to 0.42 Times, About Level With a Constant-Velocity Guess</a></div><p>On public depth images of a desk, frame-to-frame alignment was checked against motion-capture truth. Error fell to 0.42 of no alignment, yet it was no better than assuming steady speed. Small-window plane residuals grew with distance, but quantisation and window size blur whether the law is a square.</p><p class="vm">Ground truth: Real data · <a href="more.md#d-poc-real-tum-rgbd-slam">Details</a></p></div></div>

<div class="vc"><a href="../../articles/assets/poc/poc_real_walnut_cbct/07_geometry_mistakes.png"><picture><source media="(prefers-reduced-motion: reduce)" srcset="../../articles/assets/poc/poc_real_walnut_cbct/07_geometry_mistakes.png"><img src="../../articles/assets/poc/poc_real_walnut_cbct/story.en.gif" alt="Measured CT: ignoring the vertical offset lands 2.6x farther from the reference, yet the residual cannot tell" loading="lazy" width="260" height="260"></picture></a><div class="vt"><div class="vh"><a href="../../articles/assets/poc/poc_real_walnut_cbct/07_geometry_mistakes.png">Measured CT: ignoring the vertical offset lands 2.6x farther from the reference, yet the residual cannot tell</a></div><p>A walnut was really scanned in a cone beam, and the data were reconstructed with FDK and iterative methods. Using 300 projections and scoring against the reference from its authors, the result that ignores the vertical shift ends up much more distant. But the residual after reprojection cannot reveal the gap.</p><p class="vm">Ground truth: Real data · <a href="more.md#d-poc-real-walnut-cbct">Details</a></p></div></div>

<div class="vc"><a href="../../articles/assets/poc/poc_3d_sensor_modalities/01_map.png"><picture><source media="(prefers-reduced-motion: reduce)" srcset="../../articles/assets/poc/poc_3d_sensor_modalities/01_map.png"><img src="../../articles/assets/poc/poc_3d_sensor_modalities/story.en.gif" alt="One part, five 3-D sensing methods" loading="lazy" width="260" height="260"></picture></a><div class="vt"><div class="vh"><a href="../../articles/assets/poc/poc_3d_sensor_modalities/01_map.png">One part, five 3-D sensing methods</a></div><p>The same part was measured by several depth-sensing methods in matte, glossy metal, translucent and black materials. Shape errors were counted with a common 0.1 mm yardstick and compared with the dimension table. Which material breaks which method, and where, differs from method to method.</p><p class="vm">Ground truth: Synthetic · <a href="more.md#d-poc-3d-sensor-modalities">Details</a></p></div></div>

## Featured

Some PoC descriptions are in English.

<div class="vc"><a href="../../articles/assets/poc/poc_equipment_selection_map/02_equipment_at_a_glance.png"><picture><source media="(prefers-reduced-motion: reduce)" srcset="../../articles/assets/poc/poc_equipment_selection_map/02_equipment_at_a_glance.png"><img src="../../articles/assets/poc/poc_equipment_selection_map/story.en.gif" alt="Equipment map: the same flaws through 60 light, camera and lens sets" loading="lazy" width="260" height="260"></picture></a><div class="vt"><div class="vh"><a href="../../articles/assets/poc/poc_equipment_selection_map/02_equipment_at_a_glance.png">Equipment map: the same flaws through 60 light, camera and lens sets</a></div><p>We pre-tested visual inspection equipment on the same flaw. With 60 combinations of lighting, camera and lens we mapped how small a flaw is found, with the spread across repeats. It is a synthetic test, not the performance of real equipment.</p><p class="vm">Ground truth: Synthetic · <a href="more.md#d-poc-equipment-selection-map">Details</a></p></div></div>

<div class="vc"><a href="../../articles/assets/poc/poc_real_stereo_multiscanline/02_failure_map.png"><picture><source media="(prefers-reduced-motion: reduce)" srcset="../../articles/assets/poc/poc_real_stereo_multiscanline/02_failure_map.png"><img src="../../articles/assets/poc/poc_real_stereo_multiscanline/story.en.gif" alt="Disparity, surface and circle pose from real stereo" loading="lazy" width="260" height="260"></picture></a><div class="vt"><div class="vh"><a href="../../articles/assets/poc/poc_real_stereo_multiscanline/02_failure_map.png">Disparity, surface and circle pose from real stereo</a></div><p>Using a real pair of stereo images, we compute disparity, distance, surfaces and even the pose of a circle. The result is scored with the true disparity that Middlebury 2014 supplies and compared with OpenCV. Where it breaks is shown on a map.</p><p class="vm">Ground truth: Real data · <a href="more.md#d-poc-real-stereo-multiscanline">Details</a></p></div></div>

<div class="vc"><a href="../../articles/assets/poc/poc_real_defect_floor/03_defect_floor_explained.mp4"><img src="../thumbs/poc_real_defect_floor.jpg" alt="Matched noise, yet faint flaws hide on real backgrounds" loading="lazy" width="260" height="260"><b>&#9654;</b></a><div class="vt"><div class="vh"><a href="../../articles/assets/poc/poc_real_defect_floor/03_defect_floor_explained.mp4">Matched noise, yet faint flaws hide on real backgrounds</a></div><p>Inspection teams often estimate how faint a scratch they can catch on a synthetic image of a flat field plus noise. With the noise level matched, a real brick background raised the detection limit by up to 3.47 times. The limit was set not by noise but by structure in the background, such as mortar joints.</p><p class="vm">Ground truth: Real background · <a href="more.md#d-poc-real-defect-floor">Details</a></p></div></div>

<div class="vc"><a href="../../articles/assets/poc/poc_sam_hybrid_bonding_voids/03_amplitude_vs_phase.png"><picture><source media="(prefers-reduced-motion: reduce)" srcset="../../articles/assets/poc/poc_sam_hybrid_bonding_voids/03_amplitude_vs_phase.png"><img src="../../articles/assets/poc/poc_sam_hybrid_bonding_voids/story.en.gif" alt="Finding bond-plane voids by ultrasonic echo phase" loading="lazy" width="260" height="260"></picture></a><div class="vt"><div class="vh"><a href="../../articles/assets/poc/poc_sam_hybrid_bonding_voids/03_amplitude_vs_phase.png">Finding bond-plane voids by ultrasonic echo phase</a></div><p>Small voids in the bonding plane of stacked chips are searched for with a scanning acoustic microscope. Every void of 16 um or more appeared inverted and bright in the echo-phase image. In the brightness image many small voids hide among good pixels.</p><p class="vm">Ground truth: Synthetic · <a href="more.md#d-poc-sam-hybrid-bonding-voids">Details</a></p></div></div>

<div class="vc"><a href="../../articles/assets/poc/poc_photoelasticity/03_load_and_isoclinics.mp4"><picture><source media="(prefers-reduced-motion: reduce)" srcset="../../articles/assets/poc/poc_photoelasticity/01_polariscope.png"><img src="../../articles/assets/poc/poc_photoelasticity/story.en.gif" alt="Stress in a squeezed disc shows as fringes (photoelasticity)" loading="lazy" width="260" height="260"></picture><b>&#9654;</b></a><div class="vt"><div class="vh"><a href="../../articles/assets/poc/poc_photoelasticity/03_load_and_isoclinics.mp4">Stress in a squeezed disc shows as fringes (photoelasticity)</a></div><p>Viewed through polarisers, a loaded transparent plastic shows its internal stress as fringes. Stress in a squeezed disc was recovered from polarisation images, including pixels where the fringe order exceeds 0.5 and the phase wraps. Most errors left after unwrapping came from the sign ambiguity, not the wrapping.</p><p class="vm">Ground truth: Synthetic · <a href="more.md#d-poc-photoelasticity">Details</a></p></div></div>

<div class="vc"><a href="../../articles/assets/poc/poc_mixed_case_depalletizing/08_depal_robot_video.mp4"><picture><source media="(prefers-reduced-motion: reduce)" srcset="../../articles/assets/poc/poc_mixed_case_depalletizing/01_overview_same_pattern.png"><img src="../../articles/assets/poc/poc_mixed_case_depalletizing/story.en.gif" alt="Mixed cartons: depth step, V-groove or colour groove" loading="lazy" width="260" height="260"></picture><b>&#9654;</b></a><div class="vt"><div class="vh"><a href="../../articles/assets/poc/poc_mixed_case_depalletizing/08_depal_robot_video.mp4">Mixed cartons: depth step, V-groove or colour groove</a></div><p>Packed cartons with identical prints are told apart from overhead depth and colour, then unloaded. A depth step splits none, and whether depth dips or dark colour lines win flips across 28 flap-seam builds. With identical prints, deep grooves favour colour; only wide, untaped cuts over shallow grooves favour depth.</p><p class="vm">Ground truth: Synthetic · <a href="more.md#d-poc-mixed-case-depalletizing">Details</a></p></div></div>

## Article series (articles on Qiita)

<div class="vser">
<a href="https://qiita.com/furuse-kazufumi/items/8a8f23e53b19ee8cdc10"><img src="../thumbs/series_museum.gif" alt="A Metrology Museum on Paper" loading="lazy" width="480" height="270"><strong>A Metrology Museum on Paper</strong><span>Every PoC with its own planted ground truth</span></a>
<a href="https://qiita.com/furuse-kazufumi/items/a82bf9f341cc4f04ca75"><img src="../thumbs/series_table_tennis.gif" alt="Table tennis" loading="lazy" width="480" height="270"><strong>Table tennis</strong><span>Bounce and friction measured from video</span></a>
<a href="https://qiita.com/furuse-kazufumi/items/05de90f4d316cd7c681c"><img src="../thumbs/series_driving.gif" alt="Autonomous driving" loading="lazy" width="480" height="270"><strong>Autonomous driving</strong><span>Scored by theorems and second implementations</span></a>
<a href="https://qiita.com/furuse-kazufumi/items/638f0b0aa7865e17c67c"><img src="../thumbs/series_connectome.gif" alt="Connectome (brain wiring)" loading="lazy" width="480" height="270"><strong>Connectome (brain wiring)</strong><span>A fly visual model on a body, measured</span></a>
<a href="https://qiita.com/furuse-kazufumi/items/569720dbae0c6471c96e"><img src="../thumbs/series_humanoid.gif" alt="Humanoid sports day" loading="lazy" width="480" height="270"><strong>Humanoid sports day</strong><span>A home sports day refereed by image processing</span></a>
</div>

See [Extras: more PoCs](more.md), too.

<details markdown="1">
<summary><b>Try it</b> (Python 3.11)</summary>

```
pip install fullseye
git clone https://github.com/furuse-kazufumi/fullseye
cd fullseye
python examples/poc_focus_stacking.py
```

The focus-stacking PoC runs in about 20 seconds and prints its numbers against ground truth and `PASS`. Figures go to `out/figures/poc_focus_stacking/`.

</details>

<details markdown="1">
<summary><b>Links</b></summary>

- [GitHub (source code)](https://github.com/furuse-kazufumi/fullseye)
- [Gallery (all figures)](../../GALLERY.en.md)
- [Find operators / use them from an AI (RAG)](../../AI_RAG_GUIDE.en.md) · [Use from MCP](../../MCP.md) _(ja)_
- [Documentation index](../../README.en.md)

</details>

<details markdown="1">
<summary><b>Paper</b></summary>

- **Title**: Fullseye：型付き演算子と物理シミュレーションに基づく画像検査・三次元計測基盤 _(ja)_ (an image-inspection and 3-D measurement foundation built on typed operators and physics simulation)
- **Author**: Kazufumi Furuse (independent researcher)
- **Venue**: ViEW2026, Workshop on Practical Use of Vision Technology
- **Paper PDF**: [English](../paper/101_en.pdf) · [简体中文](../paper/101_zh.pdf)(日本語: available from 2026-11-26)

**Abstract (translated from Japanese)**: We propose Fullseye, an open-source foundation that builds image-inspection and 3-D measurement processing as chains of operators with declared input and output data types, evaluates it quantitatively against ground truth produced by physics and imaging simulation, and records the procedure, the evaluation and the failure conditions so they can be reused. It consists of about 3,000 typed operators, a check that rejects type mismatches before execution, multilingual operator search (RAG), and more than 200 proof-of-concept programs with ground truth. We report quantitative evaluation of representative examples and the distinction between synthetic, measured and real-hardware validation stages.

</details>
