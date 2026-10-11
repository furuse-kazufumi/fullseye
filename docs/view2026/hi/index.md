<div class="vlang" markdown="1">

[日本語](../index.md) · [English](../en/index.md) · [简体中文](../zh/index.md) · [繁體中文](../tw/index.md) · [한국어](../ko/index.md) · [Deutsch](../de/index.md) · **हिन्दी**

</div>

# Fullseye — ViEW2026

physics simulation और image processing को AI के साथ जोड़कर ground truth से जाँचना।

tile पर tap करने से video या figure खुलता है (▶ = चलता हुआ)।

<style>
.vlang { font-size: 14px; line-height: 2; }
.vg { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin: 12px 0 20px; }
.vg.vs { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; }
@media (min-width: 600px) { .vg { grid-template-columns: repeat(3, minmax(0, 1fr)); } .vg.vs { grid-template-columns: repeat(5, minmax(0, 1fr)); } }
@media (min-width: 900px) { .vg { grid-template-columns: repeat(4, minmax(0, 1fr)); } .vg.vs { grid-template-columns: repeat(7, minmax(0, 1fr)); } }
.vg a, .vser a { display: block; position: relative; text-decoration: none; color: inherit; }
.vg img { display: block; width: 100%; max-width: 100%; height: auto; aspect-ratio: 1 / 1; object-fit: cover; border-radius: 6px; background: #222; }
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
</style>

## मुख्य झलकियाँ

<div class="vg">
<a href="../../articles/assets/poc/poc_real_defect_floor/02_defect_floor_sweep.gif"><img src="../thumbs/poc_real_defect_floor.jpg" alt="Faint defect सीमा" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Faint defect सीमा</span></a>
<a href="../../articles/assets/poc/poc_active_contours/06_u_shape_snakes.mp4"><img src="../thumbs/poc_active_contours.jpg" alt="Active contours" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Active contours</span></a>
<a href="../../articles/assets/poc/poc_dic_strain/05_tensile_ramp.mp4"><img src="../thumbs/poc_dic_strain.jpg" alt="DIC strain" loading="lazy" width="320" height="320"><b>&#9654;</b><span>DIC strain</span></a>
<a href="../../articles/assets/poc/poc_focus_stacking/05_focus_sweep.mp4"><img src="../thumbs/poc_focus_stacking.jpg" alt="Focus stacking" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Focus stacking</span></a>
<a href="../../articles/assets/poc/poc_registration_basin/05_icp_basin_iterations.mp4"><img src="../thumbs/poc_registration_basin.jpg" alt="Point cloud ICP" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Point cloud ICP</span></a>
<a href="../../articles/assets/poc/poc_stockpile_volume/07_scan_orbit.mp4"><img src="../thumbs/poc_stockpile_volume.jpg" alt="Stockpile आयतन" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Stockpile आयतन</span></a>
<a href="../../articles/assets/poc/poc_ct_fidelity/01_recon_sweep.png"><img src="../thumbs/poc_ct_fidelity.jpg" alt="CT reconstruction" loading="lazy" width="320" height="320"><span>CT reconstruction</span></a>
<a href="../../articles/assets/poc/poc_ct_void_morphology/13_section_sweep.mp4"><img src="../thumbs/poc_ct_void_morphology.jpg" alt="CT voids" loading="lazy" width="320" height="320"><b>&#9654;</b><span>CT voids</span></a>
<a href="../../articles/assets/poc/poc_interferometry_step/05_step_sweep.mp4"><img src="../thumbs/poc_interferometry_step.jpg" alt="White-light step" loading="lazy" width="320" height="320"><b>&#9654;</b><span>White-light step</span></a>
<a href="../../articles/assets/poc/poc_polarization_specular/03_separation.png"><img src="../thumbs/poc_polarization_specular.jpg" alt="Polarization" loading="lazy" width="320" height="320"><span>Polarization</span></a>
<a href="../../articles/assets/poc/poc_photoelasticity/03_load_and_isoclinics.mp4"><img src="../thumbs/poc_photoelasticity.jpg" alt="Photoelasticity" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Photoelasticity</span></a>
<a href="../../articles/assets/poc/poc_thermography_ndt/02_depth_map.png"><img src="../thumbs/poc_thermography_ndt.jpg" alt="Thermography NDT" loading="lazy" width="320" height="320"><span>Thermography NDT</span></a>
<a href="../../articles/assets/poc/poc_motion_magnification/05_magnify_video.mp4"><img src="../thumbs/poc_motion_magnification.jpg" alt="Motion magnification" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Motion magnification</span></a>
<a href="../../articles/assets/poc/poc_table_tennis_bounce/01_drop_test.mp4"><img src="../thumbs/poc_table_tennis_bounce.jpg" alt="Table tennis bounce" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Table tennis bounce</span></a>
<a href="../../articles/assets/poc/poc_compound_eye/02_compound_eye_superposition.png"><img src="../thumbs/poc_compound_eye.jpg" alt="Compound eye" loading="lazy" width="320" height="320"><span>Compound eye</span></a>
<a href="../../articles/assets/poc/poc_pegsim_insertion/04_pegsim_insert_corrected.gif"><img src="../thumbs/poc_pegsim_insertion.jpg" alt="Peg-in-hole" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Peg-in-hole</span></a>
<a href="../../articles/assets/poc/poc_air_hockey_intercept/02_airhockey_prediction_cone_narrows.gif"><img src="../thumbs/poc_air_hockey_intercept.jpg" alt="Air hockey" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Air hockey</span></a>
<a href="../../articles/assets/poc/poc_tacsim_elastic_membrane/03_tacsim_force_sweep.gif"><img src="../thumbs/poc_tacsim_elastic_membrane.jpg" alt="Tactile sensor" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Tactile sensor</span></a>
<a href="../../articles/assets/poc/poc_table_tennis_spin/01_side_three_serves.mp4"><img src="../thumbs/poc_table_tennis_spin.jpg" alt="Table tennis spin" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Table tennis spin</span></a>
<a href="../../articles/assets/poc/poc_table_tennis_rally_loop/02_height_misread.mp4"><img src="../thumbs/poc_table_tennis_rally_loop.jpg" alt="Rally misreads" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Rally misreads</span></a>
<a href="../../articles/assets/poc/poc_driving_traffic/01_dashcam_occlusion.mp4"><img src="../thumbs/poc_driving_traffic.jpg" alt="Traffic, blind spots" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Traffic, blind spots</span></a>
<a href="../../articles/assets/poc/poc_driving_crossing/01_crossing_dashcam.mp4"><img src="../thumbs/poc_driving_crossing.jpg" alt="Level crossings" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Level crossings</span></a>
<a href="../../articles/assets/poc/poc_driving_pass/03_mirror_tjunction.mp4"><img src="../thumbs/poc_driving_pass.jpg" alt="Curve mirror" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Curve mirror</span></a>
<a href="../../articles/assets/poc/poc_ttc_rss/06_approach_gif.gif"><img src="../thumbs/poc_ttc_rss.jpg" alt="TTC और RSS" loading="lazy" width="320" height="320"><b>&#9654;</b><span>TTC और RSS</span></a>
<a href="../../articles/assets/poc/poc_eye_to_brain/01_eye_sweep.gif"><img src="../thumbs/poc_eye_to_brain.jpg" alt="Eye से brain" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Eye से brain</span></a>
<a href="../../articles/assets/poc/poc_malecns_activity_wave/01_activity_wave_connectome_vs_shuffle.gif"><img src="../thumbs/poc_malecns_activity_wave.jpg" alt="Fly brain wave" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Fly brain wave</span></a>
<a href="../../articles/assets/poc/poc_microns_brain_wave/04_wave_on_wiring.gif"><img src="../thumbs/poc_microns_brain_wave.jpg" alt="Mouse cortex wave" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Mouse cortex wave</span></a>
<a href="../../articles/assets/media/evis_stereo_fullseye.mp4"><img src="../thumbs/evis_stereo_depth.jpg" alt="Humanoid stereo eyes" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Humanoid stereo eyes</span></a>
<a href="../../articles/assets/media/evis_bean_track_fullseye.mp4"><img src="../thumbs/evis_bean_track.jpg" alt="Chopstick-cam tracking" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Chopstick-cam tracking</span></a>
</div>

## Article series (Qiita पर English articles)

<div class="vser">
<a href="https://qiita.com/furuse-kazufumi/items/8a8f23e53b19ee8cdc10"><img src="../thumbs/series_museum.gif" alt="कागज़ पर Metrology Museum" loading="lazy" width="480" height="270"><strong>कागज़ पर Metrology Museum</strong><span>खुद रखे ground truth वाले PoCs</span></a>
<a href="https://qiita.com/furuse-kazufumi/items/a82bf9f341cc4f04ca75"><img src="../thumbs/series_table_tennis.gif" alt="Table tennis" loading="lazy" width="480" height="270"><strong>Table tennis</strong><span>video से bounce और friction</span></a>
<a href="https://qiita.com/furuse-kazufumi/items/05de90f4d316cd7c681c"><img src="../thumbs/series_driving.gif" alt="Autonomous driving" loading="lazy" width="480" height="270"><strong>Autonomous driving</strong><span>theorems और second implementations से scoring</span></a>
<a href="https://qiita.com/furuse-kazufumi/items/638f0b0aa7865e17c67c"><img src="../thumbs/series_connectome.gif" alt="Connectome (brain wiring)" loading="lazy" width="480" height="270"><strong>Connectome (brain wiring)</strong><span>मक्खी का visual model शरीर पर, मापा गया</span></a>
<a href="https://qiita.com/furuse-kazufumi/items/569720dbae0c6471c96e"><img src="../thumbs/series_humanoid.gif" alt="Humanoid sports day" loading="lazy" width="480" height="270"><strong>Humanoid sports day</strong><span>घर का sports day, जिसमें referee image processing है</span></a>
</div>

## यह क्या कर सकता है

35 विषय, हर एक के साथ explanation page (उपयोग और सीमाएँ) और चलने वाले examples।

<div class="vl" markdown="1">

**ढूँढना**

- Regions को segment, select और count करना: [explanation](../../capabilities/blob-and-region.md) _(ja)_ · examples [poc_cell_counting](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_cell_counting.py) · [poc_particle_sizing](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_particle_sizing.py) · [poc_real_coin_metrology](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_coin_metrology.py)
- Image के अंदर के text को सही string के अनुसार ठीक करना: [explanation](../../capabilities/fix-text-in-images.md) _(ja)_ · examples [fix_text_in_image](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/fix_text_in_image.py) · [poc_glyph_typo_detection](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_glyph_typo_detection.py)
- छोटे point-like targets ढूँढना और sub-pixel position निकालना: [explanation](../../capabilities/point-target-detection.md) _(ja)_ · examples [poc_search_sweep_width](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_search_sweep_width.py) · [poc_astro_photometry](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_astro_photometry.py)

**मापना**

- Planar target के कई views से intrinsic matrix K का अनुमान (Zhang): [explanation](../../capabilities/camera-intrinsics-calibration.md) _(ja)_ · examples [camera_intrinsics_calibration](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/camera_intrinsics_calibration.py)
- Complex plane को area की तरह देखना (domain colouring, basins, escape time, flow): [explanation](../../capabilities/complex-plane-fields.md) _(ja)_ · examples [poc_complex_plane_fields](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_complex_plane_fields.py)
- सीधी रेखाओं से lens distortion coefficients का अनुमान (plumb-line, board की ज़रूरत नहीं): [explanation](../../capabilities/estimate-lens-distortion.md) _(ja)_ · examples [estimate_lens_distortion](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/estimate_lens_distortion.py)
- Measurements को पृथ्वी पर रखना (ECEF, height frames, local ENU): [explanation](../../capabilities/geodetic-frames.md) _(ja)_ · examples [poc_geodetic_height_frames](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_geodetic_height_frames.py) · [poc_geodetic_benchmarks_real](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_geodetic_benchmarks_real.py) · [dem_geodesy_tour](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/dem_geodesy_tour.py)
- उस संख्या में कितना हिस्सा measurement का है, process का नहीं (gauge R&R और uncertainty): [explanation](../../capabilities/measurement-system-and-uncertainty.md) _(ja)_ · examples [poc_measurement_system_analysis](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_measurement_system_analysis.py)
- Image से dimensions को sub-pixel तक मापना: [explanation](../../capabilities/subpixel-2d-metrology.md) _(ja)_ · examples [poc_dimensional_inspection](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dimensional_inspection.py) · [poc_screw_thread_metrology](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_screw_thread_metrology.py) · [poc_calipers_under_illusion](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_calipers_under_illusion.py)
- Terrain पर slope, flow और line of sight: [explanation](../../capabilities/terrain-and-visibility.md) _(ja)_ · examples [poc_dem_terrain](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dem_terrain.py) · [dem_terrain_analysis_tour](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/dem_terrain_analysis_tour.py)
- 3-D scan से volume निकालना: [explanation](../../capabilities/volume-from-3d-scan.md) _(ja)_ · examples [poc_stockpile_volume](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_stockpile_volume.py) · [poc_lidar_terrain_change](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_lidar_terrain_change.py)
- जो तस्वीर से जाँचा नहीं जा सकता (integrator order, Lyapunov spectrum, bifurcations, correlation dimension, minimal surfaces): [explanation](../../capabilities/what-a-picture-cannot-check.md) _(ja)_ · examples [poc_what_a_picture_cannot_check](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_what_a_picture_cannot_check.py)

**Light और colour**

- रंग मापना (XYZ / Lab / colour difference): [explanation](../../capabilities/colour-and-delta-e.md) _(ja)_ · examples [poc_white_balance](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_white_balance.py) · [poc_pigment_unmixing](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pigment_unmixing.py)
- Reflection, refraction और interference की गणना: [explanation](../../capabilities/optics-and-materials.md) _(ja)_ · examples [glass_and_mirror_optics](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/glass_and_mirror_optics.py) · [appearance_structural_colour](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/appearance_structural_colour.py)
- Polarisation camera के raw frame को Stokes, DoLP और Mueller में पढ़ना: [explanation](../../capabilities/polarization-imaging.md) _(ja)_ · examples [polarization_camera_pipeline](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/polarization_camera_pipeline.py) · [poc_polarization_specular](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_polarization_specular.py)
- Bayer raw frame को हर stage समझाने लायक formula से display image में बदलना: [explanation](../../capabilities/raw-to-display-isp.md) _(ja)_ · examples [raw_to_display_isp](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/raw_to_display_isp.py)

**Waves और signals**

- Array से दिशा मापना, range और velocity अलग करना: [explanation](../../capabilities/beamforming-and-range-doppler.md) _(ja)_ · examples [poc_multibeam_bathymetry](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_multibeam_bathymetry.py) · [poc_bev_sensor_fusion](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bev_sensor_fusion.py)
- एक ही beat (membrane modes, fringes, diffraction orders, print moiré, tone से ink): [explanation](../../capabilities/beats-fringes-and-screens.md) _(ja)_ · examples [poc_beats_fringes_and_screens](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_beats_fringes_and_screens.py)
- Vibration और आवाज़ से faults का निदान: [explanation](../../capabilities/vibration-and-acoustics.md) _(ja)_ · examples [poc_bearing_diagnosis](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bearing_diagnosis.py) · [poc_rail_corrugation](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_rail_corrugation.py)

**Reconstruct और correct करना**

- पूरी image में lens distortion ठीक करना (barrel, pincushion, tangential): [explanation](../../capabilities/lens-distortion-correction.md) _(ja)_ · examples [lens_undistort](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/lens_undistort.py)
- Projections से slices का reconstruction (CT): [explanation](../../capabilities/tomography-reconstruction.md) _(ja)_ · examples [poc_ct_fidelity](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_fidelity.py) · [poc_ct_void_morphology](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_void_morphology.py)
- Silhouettes से solid तराशना (visual hull): [explanation](../../capabilities/visual-hull-from-silhouettes.md) _(ja)_ · examples [space_carving](https://github.com/furuse-kazufumi/fullseye/blob/master/examples_3d/space_carving.py) · [poc_livestock_body_volume](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_livestock_body_volume.py)

**Workflow बनाना**

- Align करके stack करना: [explanation](../../capabilities/align-and-stack.md) _(ja)_ · examples [poc_astro_photometry](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_astro_photometry.py) · [poc_registration_basin](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_registration_basin.py)
- Golden image से तुलना, defects मापना, lot का निर्णय: [explanation](../../capabilities/golden-compare.md) _(ja)_ · examples [golden_compare](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/golden_compare.py)
- Deploy से पहले known good/bad sets पर recipe और spec जाँचना, margins मापना: [explanation](../../capabilities/inspection-fixture.md) _(ja)_ · examples [inspection_fixture](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/inspection_fixture.py)
- एक call में पूरा folder inspect करना (batch, spec, aggregate, SPC, report, audit log): [explanation](../../capabilities/inspection-workflow.md) _(ja)_ · examples [inspection_workflow](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/inspection_workflow.py)
- Typed op results को JSON में लिखना और bit-for-bit वापस पढ़ना: [explanation](../../capabilities/typed-results-as-json.md) _(ja)_ · examples [typed_results_json](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/typed_results_json.py)
- Typed op results को Markdown में दिखाना, वापस पढ़ने के लिए JSON block के साथ: [explanation](../../capabilities/typed-results-as-markdown.md) _(ja)_ · examples [typed_results_markdown](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/typed_results_markdown.py)
- Typed inspection results को Excel (.xlsx) report में लिखना: [explanation](../../capabilities/xlsx-report.md) _(ja)_ · examples [xlsx_report](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/xlsx_report.py)

**दिखाना**

- नतीजों को पढ़ने लायक figures में बदलना: [explanation](../../capabilities/figures-and-annotation.md) _(ja)_ · examples [poc_colormap_readability](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_colormap_readability.py) · [poc_dem_terrain](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dem_terrain.py)
- Background का रंग जाने बिना lines और regions बनाना (inverted colour): [explanation](../../capabilities/inverted-colour-overlays.md) _(ja)_ · examples [annotate_paper_tour](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/annotate_paper_tour.py)
- Image पर text और tables ठीक मनचाही जगह रखना: [explanation](../../capabilities/text-and-tables-on-images.md) _(ja)_ · examples [annotate_paper_tour](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/annotate_paper_tour.py)

**चित्र बनाना**

- Photo को एक ही line में बदलना (stipple → tour → घूमते circles): [explanation](../../capabilities/one-stroke-drawing.md) _(ja)_ · examples [poc_one_stroke_epicycles](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_one_stroke_epicycles.py)
- आँख को धोखा देने वाली तस्वीरें बनाकर measurement को अंक देना (illusions, endless drawing, loops): [explanation](../../capabilities/pictures-that-carry-their-own-truth.md) _(ja)_ · examples [poc_illusions_and_perpetual_drawing](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_illusions_and_perpetual_drawing.py)
- Theorems तस्वीरों के रूप में (Apollonian, Ford, geodesic dome, phyllotaxis, IFS, space-filling curves): [explanation](../../capabilities/theorems-as-pictures.md) _(ja)_ · examples [poc_theorems_as_pictures](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_theorems_as_pictures.py)

</div>

[PoC के अलावा 115 usage examples की सूची](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/README.md)

## सब कुछ देखें

218 PoCs और 4 robot-eye demos। group खोलने पर thumbnails load होते हैं।

<noscript><p><a href="../../GALLERY.en.html">(JavaScript के बिना सभी figures gallery page पर हैं।)</a></p></noscript>

<details class="vall"><summary><b>Robot की आँखें (perception Fullseye करता है)</b> (4)</summary>
<div class="vg vs">
<a href="../../articles/assets/media/evis_stereo_fullseye.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/evis_stereo_depth.jpg" alt="Humanoid stereo eyes" width="200" height="200"><b>&#9654;</b><span>Humanoid stereo eyes</span></a>
<a href="../../articles/assets/media/evis_bean_track_fullseye.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/evis_bean_track.jpg" alt="Chopstick-cam tracking" width="200" height="200"><b>&#9654;</b><span>Chopstick-cam tracking</span></a>
<a href="../../view2026/media/evis_fullseye_walk.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/evis_walk_rgb_depth_dvs.jpg" alt="RGB, depth, DVS में walk" width="200" height="200"><b>&#9654;</b><span>RGB, depth, DVS में walk</span></a>
<a href="../../view2026/media/vision_adaptive_walk.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/walker2d_terrain_vision.jpg" alt="steps देखकर gait चुनना" width="200" height="200"><span>steps देखकर gait चुनना</span></a>
</div>
</details>

<details class="vall"><summary><b>Industrial inspection</b> (32)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_barcode_1d/01_misread_split.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_barcode_1d.jpg" alt="1-D barcode" width="200" height="200"><span>1-D barcode</span></a>
<a href="../../articles/assets/poc/poc_battery_electrode_tortuosity/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_battery_electrode_tortuosity.jpg" alt="Electrode tortuosity" width="200" height="200"><span>Electrode tortuosity</span></a>
<a href="../../articles/assets/poc/poc_bearing_diagnosis/01_envelope_vs_raw.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_bearing_diagnosis.jpg" alt="Bearing diagnosis" width="200" height="200"><span>Bearing diagnosis</span></a>
<a href="../../articles/assets/poc/poc_bump_coplanarity/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_bump_coplanarity.jpg" alt="Bump coplanarity" width="200" height="200"><span>Bump coplanarity</span></a>
<a href="../../articles/assets/poc/poc_crack_width/01_width_sweep.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_crack_width.jpg" alt="Crack width" width="200" height="200"><span>Crack width</span></a>
<a href="../../articles/assets/poc/poc_fabric_defect/01_auc_by_type.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_fabric_defect.jpg" alt="Fabric defects" width="200" height="200"><span>Fabric defects</span></a>
<a href="../../articles/assets/poc/poc_leak_localization/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_leak_localization.jpg" alt="Sound से leak" width="200" height="200"><span>Sound से leak</span></a>
<a href="../../articles/assets/poc/poc_machine_condition_fusion/01_scene_machine.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_machine_condition_fusion.jpg" alt="Machine health" width="200" height="200"><span>Machine health</span></a>
<a href="../../articles/assets/poc/poc_matrix_code_reading/01_symbol_and_errors.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_matrix_code_reading.jpg" alt="Matrix code" width="200" height="200"><span>Matrix code</span></a>
<a href="../../articles/assets/poc/poc_moire_screen/01_failure_split_plot.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_moire_screen.jpg" alt="Display moiré" width="200" height="200"><span>Display moiré</span></a>
<a href="../../articles/assets/poc/poc_print_registration/01_plates.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_print_registration.jpg" alt="Print registration" width="200" height="200"><span>Print registration</span></a>
<a href="../../articles/assets/poc/poc_real_defect_floor/02_defect_floor_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_defect_floor.jpg" alt="Faint defect सीमा" width="200" height="200"><b>&#9654;</b><span>Faint defect सीमा</span></a>
<a href="../../articles/assets/poc/poc_real_texture_invariance/01_textures.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_texture_invariance.jpg" alt="Texture rotation" width="200" height="200"><span>Texture rotation</span></a>
<a href="../../articles/assets/poc/poc_recycling_sorting/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_recycling_sorting.jpg" alt="Waste sorting" width="200" height="200"><span>Waste sorting</span></a>
<a href="../../articles/assets/poc/poc_solar_el_inspection/01_zero_point_map.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_solar_el_inspection.jpg" alt="Solar EL" width="200" height="200"><span>Solar EL</span></a>
<a href="../../articles/assets/poc/poc_solder_fillet_aoi/01_ring_lut.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_solder_fillet_aoi.jpg" alt="Solder AOI" width="200" height="200"><span>Solder AOI</span></a>
<a href="../../articles/assets/poc/poc_spc/01_spc_xbar_chart.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_spc.jpg" alt="SPC" width="200" height="200"><span>SPC</span></a>
<a href="../../articles/assets/poc/poc_mt_hidden_fault/01_mt_hidden_cloud.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_mt_hidden_fault.jpg" alt="MT hidden fault" width="200" height="200"><span>MT hidden fault</span></a>
<a href="../../articles/assets/poc/poc_text_region_truth/01_text_region_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_text_region_truth.jpg" alt="Text regions" width="200" height="200"><span>Text regions</span></a>
<a href="../../articles/assets/poc/poc_thermal_drift_metrology/01_separate_drifts.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_thermal_drift_metrology.jpg" alt="Thermal drift" width="200" height="200"><span>Thermal drift</span></a>
<a href="../../articles/assets/poc/poc_thermal_radiometry/01_floor.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_thermal_radiometry.jpg" alt="Thermal radiometry" width="200" height="200"><span>Thermal radiometry</span></a>
<a href="../../articles/assets/poc/poc_thermography_ndt/01_depth_table.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_thermography_ndt.jpg" alt="Thermography NDT" width="200" height="200"><span>Thermography NDT</span></a>
<a href="../../articles/assets/poc/poc_veiling_glare/01_verdict.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_veiling_glare.jpg" alt="Veiling glare" width="200" height="200"><span>Veiling glare</span></a>
<a href="../../articles/assets/poc/poc_emva1288_sensor/01_photon_transfer.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_emva1288_sensor.jpg" alt="EMVA 1288 sensor" width="200" height="200"><b>&#9654;</b><span>EMVA 1288 sensor</span></a>
<a href="../../articles/assets/poc/poc_web_roll_periodicity/01_scene_web.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_web_roll_periodicity.jpg" alt="Roller defects" width="200" height="200"><span>Roller defects</span></a>
<a href="../../articles/assets/poc/poc_weld_bead_profile/01_laser_images.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_weld_bead_profile.jpg" alt="Weld bead profile" width="200" height="200"><span>Weld bead profile</span></a>
<a href="../../articles/assets/poc/poc_weld_bead_scan_angle/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_weld_bead_scan_angle.jpg" alt="Weld bead scan" width="200" height="200"><span>Weld bead scan</span></a>
<a href="../../articles/assets/poc/poc_weld_radiograph_porosity/01_scene_radiograph.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_weld_radiograph_porosity.jpg" alt="Weld porosity" width="200" height="200"><span>Weld porosity</span></a>
<a href="../../articles/assets/poc/poc_glyph_typo_detection/01_sign_before_after.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_glyph_typo_detection.jpg" alt="Glyph typos" width="200" height="200"><span>Glyph typos</span></a>
<a href="../../articles/assets/poc/poc_print_layer_inspection/01_slice_stack.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_print_layer_inspection.jpg" alt="Print layers" width="200" height="200"><span>Print layers</span></a>
<a href="../../articles/assets/poc/poc_agv_fleet/01_agv_naive_vs_adg.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_agv_fleet.jpg" alt="AGV fleet" width="200" height="200"><b>&#9654;</b><span>AGV fleet</span></a>
<a href="../../articles/assets/poc/poc_am_thermal_to_ct/01_melt_pool_frames.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_am_thermal_to_ct.jpg" alt="AM thermal से CT" width="200" height="200"><b>&#9654;</b><span>AM thermal से CT</span></a>
</div>
</details>

<details class="vall"><summary><b>Dimensional और shape metrology</b> (36)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_aoi_ct_traceability/01_aoi_and_ct.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_aoi_ct_traceability.jpg" alt="AOI-CT matching" width="200" height="200"><span>AOI-CT matching</span></a>
<a href="../../articles/assets/poc/poc_asbuilt_wall_deviation/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_asbuilt_wall_deviation.jpg" alt="As-built दीवारें" width="200" height="200"><span>As-built दीवारें</span></a>
<a href="../../articles/assets/poc/poc_battery_electrode_breathing/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_battery_electrode_breathing.jpg" alt="Electrode breathing" width="200" height="200"><span>Electrode breathing</span></a>
<a href="../../articles/assets/poc/poc_bilateral_asymmetry/01_floor_vs_spacing.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_bilateral_asymmetry.jpg" alt="Bilateral asymmetry" width="200" height="200"><span>Bilateral asymmetry</span></a>
<a href="../../articles/assets/poc/poc_dic_strain/05_tensile_ramp.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dic_strain.jpg" alt="DIC strain" width="200" height="200"><b>&#9654;</b><span>DIC strain</span></a>
<a href="../../articles/assets/poc/poc_die_tilt_tsv_overlay/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_die_tilt_tsv_overlay.jpg" alt="Die tilt और TSV" width="200" height="200"><span>Die tilt और TSV</span></a>
<a href="../../articles/assets/poc/poc_dimensional_inspection/01_slot_bias.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dimensional_inspection.jpg" alt="Dimensional check" width="200" height="200"><span>Dimensional check</span></a>
<a href="../../articles/assets/poc/poc_fiber_orientation/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_fiber_orientation.jpg" alt="Fibre orientation" width="200" height="200"><span>Fibre orientation</span></a>
<a href="../../articles/assets/poc/poc_gear_tooth_metrology/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_gear_tooth_metrology.jpg" alt="Gear teeth" width="200" height="200"><span>Gear teeth</span></a>
<a href="../../articles/assets/poc/poc_interferometry_step/05_step_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_interferometry_step.jpg" alt="White-light step" width="200" height="200"><b>&#9654;</b><span>White-light step</span></a>
<a href="../../articles/assets/poc/poc_metal_grain_size/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_metal_grain_size.jpg" alt="Grain size" width="200" height="200"><span>Grain size</span></a>
<a href="../../articles/assets/poc/poc_multibeam_bathymetry/17_survey.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_multibeam_bathymetry.jpg" alt="Multibeam sonar" width="200" height="200"><b>&#9654;</b><span>Multibeam sonar</span></a>
<a href="../../articles/assets/poc/poc_particle_sizing/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_particle_sizing.jpg" alt="Particle sizing" width="200" height="200"><span>Particle sizing</span></a>
<a href="../../articles/assets/poc/poc_photoelasticity/03_load_and_isoclinics.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_photoelasticity.jpg" alt="Photoelasticity" width="200" height="200"><b>&#9654;</b><span>Photoelasticity</span></a>
<a href="../../articles/assets/poc/poc_rail_corrugation/01_planted_components.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_rail_corrugation.jpg" alt="Rail corrugation" width="200" height="200"><span>Rail corrugation</span></a>
<a href="../../articles/assets/poc/poc_real_coin_metrology/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_coin_metrology.jpg" alt="Real coins" width="200" height="200"><span>Real coins</span></a>
<a href="../../articles/assets/poc/poc_screw_thread_metrology/01_zero_spectrum.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_screw_thread_metrology.jpg" alt="Screw threads" width="200" height="200"><span>Screw threads</span></a>
<a href="../../articles/assets/poc/poc_stockpile_volume/07_scan_orbit.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_stockpile_volume.jpg" alt="Stockpile आयतन" width="200" height="200"><b>&#9654;</b><span>Stockpile आयतन</span></a>
<a href="../../articles/assets/poc/poc_strain_history/05_history_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_strain_history.jpg" alt="Creep strain" width="200" height="200"><b>&#9654;</b><span>Creep strain</span></a>
<a href="../../articles/assets/poc/poc_surface_roughness/01_surface_components.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_surface_roughness.jpg" alt="Surface roughness" width="200" height="200"><span>Surface roughness</span></a>
<a href="../../articles/assets/poc/poc_tacsim_elastic_membrane/03_tacsim_force_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_tacsim_elastic_membrane.jpg" alt="Tactile sensor" width="200" height="200"><b>&#9654;</b><span>Tactile sensor</span></a>
<a href="../../articles/assets/poc/poc_tacsim_marker_shear/02_tacslip_stick_circle_shrinks.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_tacsim_marker_shear.jpg" alt="Tactile shear" width="200" height="200"><b>&#9654;</b><span>Tactile shear</span></a>
<a href="../../articles/assets/poc/poc_tactile_dipole_torque/02_tactorque_dipole_grows_with_M.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_tactile_dipole_torque.jpg" alt="Tactile dipole" width="200" height="200"><b>&#9654;</b><span>Tactile dipole</span></a>
<a href="../../articles/assets/poc/poc_granular_heap_repose/11_granular_datum_tilt_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_granular_heap_repose.jpg" alt="Powder heap" width="200" height="200"><b>&#9654;</b><span>Powder heap</span></a>
<a href="../../articles/assets/poc/poc_food_cutting_measure/01_cutting_track_force.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_food_cutting_measure.jpg" alt="Food cutting" width="200" height="200"><b>&#9654;</b><span>Food cutting</span></a>
<a href="../../articles/assets/poc/poc_tacdome_large_deformation/01_tacdome_press_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_tacdome_large_deformation.jpg" alt="Soft dome contact" width="200" height="200"><b>&#9654;</b><span>Soft dome contact</span></a>
<a href="../../articles/assets/poc/poc_polish_wipe_measure/01_polish_raster_wipe_coat.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_polish_wipe_measure.jpg" alt="Polish और wipe" width="200" height="200"><b>&#9654;</b><span>Polish और wipe</span></a>
<a href="../../articles/assets/poc/poc_powder_scoop_pour/03_scoop_stream_synthetic_frames.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_powder_scoop_pour.jpg" alt="Powder scoop/pour" width="200" height="200"><b>&#9654;</b><span>Powder scoop/pour</span></a>
<a href="../../articles/assets/poc/poc_powder_grinding_ae/07_psd_fining_during_grinding.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_powder_grinding_ae.jpg" alt="Mortar grinding" width="200" height="200"><b>&#9654;</b><span>Mortar grinding</span></a>
<a href="../../articles/assets/poc/poc_pxrd_phase_peel/01_phase_peel.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_pxrd_phase_peel.jpg" alt="PXRD phases" width="200" height="200"><b>&#9654;</b><span>PXRD phases</span></a>
<a href="../../articles/assets/poc/poc_dose_uniformity_from_grinding/01_cv_bias_decomposition.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dose_uniformity_from_grinding.jpg" alt="Dose uniformity" width="200" height="200"><span>Dose uniformity</span></a>
<a href="../../articles/assets/poc/poc_knife_tactile_toughness/06_cut_with_fingertip_pads.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_knife_tactile_toughness.jpg" alt="Tactile knife" width="200" height="200"><b>&#9654;</b><span>Tactile knife</span></a>
<a href="../../articles/assets/poc/poc_measurement_system_analysis/16_breakdown_movie.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_measurement_system_analysis.jpg" alt="Gauge R&R" width="200" height="200"><b>&#9654;</b><span>Gauge R&R</span></a>
<a href="../../articles/assets/poc/poc_zernike_aberrations/06_through_focus.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_zernike_aberrations.jpg" alt="Zernike aberrations" width="200" height="200"><b>&#9654;</b><span>Zernike aberrations</span></a>
<a href="../../articles/assets/poc/poc_attention_identities/01_attention_masks.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_attention_identities.jpg" alt="Attention identities" width="200" height="200"><span>Attention identities</span></a>
<a href="../../articles/assets/poc/poc_residue_crt/03_residue_rotation_needle.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_residue_crt.jpg" alt="Phase CRT" width="200" height="200"><b>&#9654;</b><span>Phase CRT</span></a>
</div>
</details>

<details class="vall"><summary><b>3-D shape</b> (18)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_battery_ct_degradation/01_xray_projection.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_battery_ct_degradation.jpg" alt="Battery CT" width="200" height="200"><span>Battery CT</span></a>
<a href="../../articles/assets/poc/poc_bev_sensor_fusion/01_scene_bev.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_bev_sensor_fusion.jpg" alt="BEV sensor fusion" width="200" height="200"><span>BEV sensor fusion</span></a>
<a href="../../articles/assets/poc/poc_cad_scan_deviation/14_align_orbit.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_cad_scan_deviation.jpg" alt="CAD-to-scan" width="200" height="200"><b>&#9654;</b><span>CAD-to-scan</span></a>
<a href="../../articles/assets/poc/poc_crop_phenotyping/01_capsule_calibration.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_crop_phenotyping.jpg" alt="Crop leaf area" width="200" height="200"><span>Crop leaf area</span></a>
<a href="../../articles/assets/poc/poc_ct_void_morphology/13_section_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_ct_void_morphology.jpg" alt="Joint voids (CT)" width="200" height="200"><b>&#9654;</b><span>Joint voids (CT)</span></a>
<a href="../../articles/assets/poc/poc_dfm_thickness_overhang/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dfm_thickness_overhang.jpg" alt="Manufacturability" width="200" height="200"><span>Manufacturability</span></a>
<a href="../../articles/assets/poc/poc_lidar_terrain_change/12_flight.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_lidar_terrain_change.jpg" alt="Slope earthwork" width="200" height="200"><b>&#9654;</b><span>Slope earthwork</span></a>
<a href="../../articles/assets/poc/poc_livestock_body_volume/14_hull_orbit.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_livestock_body_volume.jpg" alt="Livestock weight" width="200" height="200"><b>&#9654;</b><span>Livestock weight</span></a>
<a href="../../articles/assets/poc/poc_mesh_quality_repair/14_decimate_orbit.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_mesh_quality_repair.jpg" alt="Mesh repair" width="200" height="200"><b>&#9654;</b><span>Mesh repair</span></a>
<a href="../../articles/assets/poc/poc_pallet_load_utilization/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_pallet_load_utilization.jpg" alt="Pallet load" width="200" height="200"><span>Pallet load</span></a>
<a href="../../articles/assets/poc/poc_pipe_wall_loss/01_scene_pipe.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_pipe_wall_loss.jpg" alt="Pipe wall loss" width="200" height="200"><span>Pipe wall loss</span></a>
<a href="../../articles/assets/poc/poc_print_warpage_risk/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_print_warpage_risk.jpg" alt="Print warpage" width="200" height="200"><span>Print warpage</span></a>
<a href="../../articles/assets/poc/poc_safety_clearance/01_conditions.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_safety_clearance.jpg" alt="Human-machine दूरी" width="200" height="200"><span>Human-machine दूरी</span></a>
<a href="../../articles/assets/poc/poc_scan_to_bim_asbuilt/01_scene_plan_section.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_scan_to_bim_asbuilt.jpg" alt="Scan-to-BIM" width="200" height="200"><span>Scan-to-BIM</span></a>
<a href="../../articles/assets/poc/poc_structure_4d_deterioration/12_years_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_structure_4d_deterioration.jpg" alt="Yearly re-survey" width="200" height="200"><b>&#9654;</b><span>Yearly re-survey</span></a>
<a href="../../articles/assets/poc/poc_symmetry_restoration/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_symmetry_restoration.jpg" alt="Symmetry repair" width="200" height="200"><span>Symmetry repair</span></a>
<a href="../../articles/assets/poc/poc_endless_zoom_and_turning_solids/03_zoom_loop.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_endless_zoom_and_turning_solids.jpg" alt="Endless zoom" width="200" height="200"><b>&#9654;</b><span>Endless zoom</span></a>
<a href="../../articles/assets/poc/poc_four_dimensions_by_three_d_tools/03_hopf_turn.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_four_dimensions_by_three_d_tools.jpg" alt="3-D tools से 4-D" width="200" height="200"><b>&#9654;</b><span>3-D tools से 4-D</span></a>
</div>
</details>

<details class="vall"><summary><b>Geometry और calibration</b> (18)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_camera_calibration/05_calibration_convergence.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_camera_calibration.jpg" alt="Camera calibration" width="200" height="200"><b>&#9654;</b><span>Camera calibration</span></a>
<a href="../../articles/assets/poc/poc_panorama_drift/05_chain_drift_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_panorama_drift.jpg" alt="Panorama drift" width="200" height="200"><b>&#9654;</b><span>Panorama drift</span></a>
<a href="../../articles/assets/poc/poc_real_stereo_depth/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_stereo_depth.jpg" alt="Real stereo" width="200" height="200"><span>Real stereo</span></a>
<a href="../../articles/assets/poc/poc_registration_basin/05_icp_basin_iterations.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_registration_basin.jpg" alt="Point cloud ICP" width="200" height="200"><b>&#9654;</b><span>Point cloud ICP</span></a>
<a href="../../articles/assets/poc/poc_rotation_invariance_audit/02_rotating_coin.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_rotation_invariance_audit.jpg" alt="Rotation audit" width="200" height="200"><b>&#9654;</b><span>Rotation audit</span></a>
<a href="../../articles/assets/poc/poc_carla_bridge/01_carla_two_worlds.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_carla_bridge.jpg" alt="Two worlds (CARLA)" width="200" height="200"><span>Two worlds (CARLA)</span></a>
<a href="../../articles/assets/poc/poc_driving_town/04_town_drive_through.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_town.jpg" alt="Town assembly" width="200" height="200"><b>&#9654;</b><span>Town assembly</span></a>
<a href="../../articles/assets/poc/poc_driving_japan_town/03_japan_town_drive.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_japan_town.jpg" alt="Real Japanese town" width="200" height="200"><b>&#9654;</b><span>Real Japanese town</span></a>
<a href="../../articles/assets/poc/poc_driving_commonroad/01_commonroad_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_commonroad.jpg" alt="CommonRoad scoring" width="200" height="200"><span>CommonRoad scoring</span></a>
<a href="../../articles/assets/poc/poc_pegsim_insertion/04_pegsim_insert_corrected.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_pegsim_insertion.jpg" alt="Peg-in-hole" width="200" height="200"><b>&#9654;</b><span>Peg-in-hole</span></a>
<a href="../../articles/assets/poc/poc_air_hockey_intercept/02_airhockey_prediction_cone_narrows.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_air_hockey_intercept.jpg" alt="Air hockey" width="200" height="200"><b>&#9654;</b><span>Air hockey</span></a>
<a href="../../articles/assets/poc/poc_peg_failure_recovery/05_pegfail_wrist_camera_wedging_detect_recover.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_peg_failure_recovery.jpg" alt="Peg failure recovery" width="200" height="200"><b>&#9654;</b><span>Peg failure recovery</span></a>
<a href="../../articles/assets/poc/poc_tacscalib_sphere_lut/02_tacscalib_synthetic_relight.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_tacscalib_sphere_lut.jpg" alt="Tactile calibration" width="200" height="200"><b>&#9654;</b><span>Tactile calibration</span></a>
<a href="../../articles/assets/poc/poc_peg_insertion_tactile/03_pegtactile_whitney_insertion_through_membranes.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_peg_insertion_tactile.jpg" alt="Tactile peg insertion" width="200" height="200"><b>&#9654;</b><span>Tactile peg insertion</span></a>
<a href="../../articles/assets/poc/poc_peg_symmetry_search/01_pegsym_rotating_shapes_read_mod_2pi_over_n.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_peg_symmetry_search.jpg" alt="Peg symmetry" width="200" height="200"><b>&#9654;</b><span>Peg symmetry</span></a>
<a href="../../articles/assets/poc/poc_reproducible_icp/01_error_staircase_ozaki1.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_reproducible_icp.jpg" alt="Reproducible ICP" width="200" height="200"><span>Reproducible ICP</span></a>
<a href="../../articles/assets/poc/poc_public_camera_heading/02_yaw_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_public_camera_heading.jpg" alt="Camera heading" width="200" height="200"><b>&#9654;</b><span>Camera heading</span></a>
<a href="../../articles/assets/poc/poc_public_camera_heading_real/02_sunset_follow.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_public_camera_heading_real.jpg" alt="Camera heading (real)" width="200" height="200"><b>&#9654;</b><span>Camera heading (real)</span></a>
</div>
</details>

<details class="vall"><summary><b>Image quality और restoration</b> (16)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_camera_shake_deblur/05_kernel_angle_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_camera_shake_deblur.jpg" alt="Shake deblurring" width="200" height="200"><b>&#9654;</b><span>Shake deblurring</span></a>
<a href="../../articles/assets/poc/poc_colormap_readability/01_gain_profile.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_colormap_readability.jpg" alt="Colormap पढ़ना" width="200" height="200"><span>Colormap पढ़ना</span></a>
<a href="../../articles/assets/poc/poc_compound_eye/01_compound_eye_scaling.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_compound_eye.jpg" alt="Fly compound eye" width="200" height="200"><span>Fly compound eye</span></a>
<a href="../../articles/assets/poc/poc_ct_fidelity/01_recon_sweep.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_ct_fidelity.jpg" alt="CT reconstruction" width="200" height="200"><span>CT reconstruction</span></a>
<a href="../../articles/assets/poc/poc_dehazing/05_haze_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dehazing.jpg" alt="Dehazing" width="200" height="200"><b>&#9654;</b><span>Dehazing</span></a>
<a href="../../articles/assets/poc/poc_dtof_ranging/01_histograms.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dtof_ranging.jpg" alt="Photon ranging" width="200" height="200"><span>Photon ranging</span></a>
<a href="../../articles/assets/poc/poc_focus_stacking/05_focus_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_focus_stacking.jpg" alt="Focus stacking" width="200" height="200"><b>&#9654;</b><span>Focus stacking</span></a>
<a href="../../articles/assets/poc/poc_lightfield_depth/01_scene_and_depth.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_lightfield_depth.jpg" alt="Light-field depth" width="200" height="200"><span>Light-field depth</span></a>
<a href="../../articles/assets/poc/poc_real_deblur_honesty/01_restore.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_deblur_honesty.jpg" alt="Real deblurring" width="200" height="200"><span>Real deblurring</span></a>
<a href="../../articles/assets/poc/poc_superresolution_limits/05_growth.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_superresolution_limits.jpg" alt="Super-resolution" width="200" height="200"><b>&#9654;</b><span>Super-resolution</span></a>
<a href="../../articles/assets/poc/poc_iqa_tid2013/01_tid2013_mos_vs_psnr.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_iqa_tid2013.jpg" alt="IQA vs TID2013" width="200" height="200"><span>IQA vs TID2013</span></a>
<a href="../../articles/assets/poc/poc_iqa_fsim_gmsd_vif/01_iqa_tid2013_mos_vs_fsim.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_iqa_fsim_gmsd_vif.jpg" alt="FSIM/GMSD/VIF" width="200" height="200"><span>FSIM/GMSD/VIF</span></a>
<a href="../../articles/assets/poc/poc_vanishing_detail_and_morphing_area/06_morph_loop.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_vanishing_detail_and_morphing_area.jpg" alt="Vanishing detail" width="200" height="200"><b>&#9654;</b><span>Vanishing detail</span></a>
<a href="../../articles/assets/poc/poc_segmentation_gauntlet/08_gauntlet_blobs.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_segmentation_gauntlet.jpg" alt="Segmentation gauntlet" width="200" height="200"><b>&#9654;</b><span>Segmentation gauntlet</span></a>
<a href="../../articles/assets/poc/poc_active_contours/06_u_shape_snakes.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_active_contours.jpg" alt="Active contours" width="200" height="200"><b>&#9654;</b><span>Active contours</span></a>
<a href="../../articles/assets/poc/poc_graph_hierarchy_segmentation/08_watershed_theta_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_graph_hierarchy_segmentation.jpg" alt="Graph segmentation" width="200" height="200"><b>&#9654;</b><span>Graph segmentation</span></a>
</div>
</details>

<details class="vall"><summary><b>Colour और separation</b> (4)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_pigment_unmixing/01_per_field_auc.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_pigment_unmixing.jpg" alt="Pigment layers" width="200" height="200"><span>Pigment layers</span></a>
<a href="../../articles/assets/poc/poc_polarization_specular/01_fresnel.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_polarization_specular.jpg" alt="Polarization" width="200" height="200"><span>Polarization</span></a>
<a href="../../articles/assets/poc/poc_real_stain_unmix/01_separation.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_stain_unmix.jpg" alt="Real stain unmixing" width="200" height="200"><span>Real stain unmixing</span></a>
<a href="../../articles/assets/poc/poc_white_balance/01_casts.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_white_balance.jpg" alt="White balance" width="200" height="200"><span>White balance</span></a>
</div>
</details>

<details class="vall"><summary><b>Time को 3-D की तरह</b> (21)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_beam_modal_video/14_beam_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_beam_modal_video.jpg" alt="Video से modal ID" width="200" height="200"><b>&#9654;</b><span>Video से modal ID</span></a>
<a href="../../articles/assets/poc/poc_cold_chain_excursion/01_scene_slices.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_cold_chain_excursion.jpg" alt="Cold-chain तापमान" width="200" height="200"><span>Cold-chain तापमान</span></a>
<a href="../../articles/assets/poc/poc_crack_width_timeseries/11_series_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_crack_width_timeseries.jpg" alt="Crack growth" width="200" height="200"><b>&#9654;</b><span>Crack growth</span></a>
<a href="../../articles/assets/poc/poc_motion_magnification/05_magnify_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_motion_magnification.jpg" alt="Motion magnification" width="200" height="200"><b>&#9654;</b><span>Motion magnification</span></a>
<a href="../../articles/assets/poc/poc_particle_tracking/05_tracking_links.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_particle_tracking.jpg" alt="Particle tracking" width="200" height="200"><b>&#9654;</b><span>Particle tracking</span></a>
<a href="../../articles/assets/poc/poc_settlement_significance/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_settlement_significance.jpg" alt="Settlement test" width="200" height="200"><span>Settlement test</span></a>
<a href="../../articles/assets/poc/poc_template_tracking/05_twin_vs_flat_occluder.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_template_tracking.jpg" alt="Template tracking" width="200" height="200"><b>&#9654;</b><span>Template tracking</span></a>
<a href="../../articles/assets/poc/poc_timelapse_growth/05_growth_merge.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_timelapse_growth.jpg" alt="Growth time-lapse" width="200" height="200"><b>&#9654;</b><span>Growth time-lapse</span></a>
<a href="../../articles/assets/poc/poc_traffic_counting/05_counting_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_traffic_counting.jpg" alt="Traffic counting" width="200" height="200"><b>&#9654;</b><span>Traffic counting</span></a>
<a href="../../articles/assets/poc/poc_warehouse_flow/01_heat_ambiguity.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_warehouse_flow.jpg" alt="Warehouse dwell" width="200" height="200"><span>Warehouse dwell</span></a>
<a href="../../articles/assets/poc/poc_xyt_event_surface/05_arrival_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_xyt_event_surface.jpg" alt="Arrival-time surface" width="200" height="200"><b>&#9654;</b><span>Arrival-time surface</span></a>
<a href="../../articles/assets/poc/poc_video_cube/02_cube_orbit.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_video_cube.jpg" alt="Video cube" width="200" height="200"><b>&#9654;</b><span>Video cube</span></a>
<a href="../../articles/assets/poc/poc_live4d/01_beating_orbit.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_live4d.jpg" alt="Live 3D+t" width="200" height="200"><b>&#9654;</b><span>Live 3D+t</span></a>
<a href="../../articles/assets/poc/poc_diabolo_model_and_vision/01_diabolo_throw_axis_from_image.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_diabolo_model_and_vision.jpg" alt="Diabolo" width="200" height="200"><b>&#9654;</b><span>Diabolo</span></a>
<a href="../../articles/assets/poc/poc_swarm_obstacle_from_flow/01_swarmflow_hidden_obstacle_emerges.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_swarm_obstacle_from_flow.jpg" alt="Swarm obstacle" width="200" height="200"><b>&#9654;</b><span>Swarm obstacle</span></a>
<a href="../../articles/assets/poc/poc_ball_bounce/06_rally_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_ball_bounce.jpg" alt="Table tennis tracking" width="200" height="200"><b>&#9654;</b><span>Table tennis tracking</span></a>
<a href="../../articles/assets/poc/poc_kendama/05_catch_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_kendama.jpg" alt="Kendama" width="200" height="200"><b>&#9654;</b><span>Kendama</span></a>
<a href="../../articles/assets/poc/poc_table_tennis_spin/01_side_three_serves.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_table_tennis_spin.jpg" alt="Table tennis spin" width="200" height="200"><b>&#9654;</b><span>Table tennis spin</span></a>
<a href="../../articles/assets/poc/poc_table_tennis_bounce/01_drop_test.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_table_tennis_bounce.jpg" alt="Table tennis bounce" width="200" height="200"><b>&#9654;</b><span>Table tennis bounce</span></a>
<a href="../../articles/assets/poc/poc_table_tennis_rally_loop/01_landing_cloud.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_table_tennis_rally_loop.jpg" alt="Rally misreads" width="200" height="200"><b>&#9654;</b><span>Rally misreads</span></a>
<a href="../../articles/assets/poc/poc_periodic_video_boundary/02_loop.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_periodic_video_boundary.jpg" alt="Periodic video" width="200" height="200"><b>&#9654;</b><span>Periodic video</span></a>
</div>
</details>

<details class="vall"><summary><b>Connectome और neurons</b> (19)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_fly_vision/01_fly_vision_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_fly_vision.jpg" alt="Fly vision" width="200" height="200"><span>Fly vision</span></a>
<a href="../../articles/assets/poc/poc_larval_connectome_reservoir/01_adjacency_binned_connectome_vs_shuffle.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_larval_connectome_reservoir.jpg" alt="Larval connectome" width="200" height="200"><span>Larval connectome</span></a>
<a href="../../articles/assets/poc/poc_malecns_activity_wave/01_activity_wave_connectome_vs_shuffle.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_malecns_activity_wave.jpg" alt="Fly brain wave" width="200" height="200"><b>&#9654;</b><span>Fly brain wave</span></a>
<a href="../../articles/assets/poc/poc_eye_to_brain/01_eye_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_eye_to_brain.jpg" alt="Eye से brain" width="200" height="200"><b>&#9654;</b><span>Eye से brain</span></a>
<a href="../../articles/assets/poc/poc_em_second_opinion/02_suspects_on_the_cube.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_em_second_opinion.jpg" alt="EM second opinion" width="200" height="200"><b>&#9654;</b><span>EM second opinion</span></a>
<a href="../../articles/assets/poc/poc_connectome_motor_bottleneck/03_activity_flow.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_connectome_motor_bottleneck.jpg" alt="Motor quantisation" width="200" height="200"><b>&#9654;</b><span>Motor quantisation</span></a>
<a href="../../articles/assets/poc/poc_microns_brain_wave/01_brain_wave.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_microns_brain_wave.jpg" alt="MICrONS wave" width="200" height="200"><b>&#9654;</b><span>MICrONS wave</span></a>
<a href="../../articles/assets/poc/poc_em_branch_territory/02_territory_turning.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_em_branch_territory.jpg" alt="Branch territories" width="200" height="200"><b>&#9654;</b><span>Branch territories</span></a>
<a href="../../articles/assets/poc/poc_connectome_lr_symmetry/01_lr_jaccard_closed_form.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_connectome_lr_symmetry.jpg" alt="Worm L/R symmetry" width="200" height="200"><span>Worm L/R symmetry</span></a>
<a href="../../articles/assets/poc/poc_connectome_across_worms/02_wiring_across_development.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_connectome_across_worms.jpg" alt="Worm-to-worm wiring" width="200" height="200"><b>&#9654;</b><span>Worm-to-worm wiring</span></a>
<a href="../../articles/assets/poc/poc_connectome_across_decades/01_jaccard_across_decades.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_connectome_across_decades.jpg" alt="Decades पार wiring" width="200" height="200"><span>Decades पार wiring</span></a>
<a href="../../articles/assets/poc/poc_worm_neurites_grow/01_neurite_length_growth.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_worm_neurites_grow.jpg" alt="Neurite growth" width="200" height="200"><span>Neurite growth</span></a>
<a href="../../articles/assets/poc/poc_em_split_merge_score/01_split_vs_merge_by_threshold.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_em_split_merge_score.jpg" alt="EM split/merge" width="200" height="200"><span>EM split/merge</span></a>
<a href="../../articles/assets/poc/poc_em_wiring_errors/01_proofreading_order.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_em_wiring_errors.jpg" alt="Wiring errors" width="200" height="200"><span>Wiring errors</span></a>
<a href="../../articles/assets/poc/poc_worm_synapses_vs_neurites/01_density_by_stage.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_worm_synapses_vs_neurites.jpg" alt="Synapses vs neurites" width="200" height="200"><span>Synapses vs neurites</span></a>
<a href="../../articles/assets/poc/poc_skeleton_run_length_vs_voi/01_merge_size_erl_vs_voi.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_skeleton_run_length_vs_voi.jpg" alt="ERL vs VOI" width="200" height="200"><span>ERL vs VOI</span></a>
<a href="../../articles/assets/poc/poc_swc_tree_truth/01_swc_projection.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_swc_tree_truth.jpg" alt="SWC skeletons" width="200" height="200"><span>SWC skeletons</span></a>
<a href="../../articles/assets/poc/poc_fly_optomotor_steering/06_follow.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_fly_optomotor_steering.jpg" alt="Fly steering" width="200" height="200"><b>&#9654;</b><span>Fly steering</span></a>
<a href="../../articles/assets/poc/poc_worm_core_persists/04_core_map_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_worm_core_persists.jpg" alt="Worm brain core" width="200" height="200"><b>&#9654;</b><span>Worm brain core</span></a>
</div>
</details>

<details class="vall"><summary><b>Medical और biological</b> (9)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_bone_trabecular_thickness/01_scene_truth.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_bone_trabecular_thickness.jpg" alt="Trabecular bone" width="200" height="200"><span>Trabecular bone</span></a>
<a href="../../articles/assets/poc/poc_cell_counting/01_scene_dense.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_cell_counting.jpg" alt="Cell counting" width="200" height="200"><span>Cell counting</span></a>
<a href="../../articles/assets/poc/poc_colocalization_crosstalk/01_scene_channels.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_colocalization_crosstalk.jpg" alt="Colocalization" width="200" height="200"><span>Colocalization</span></a>
<a href="../../articles/assets/poc/poc_mri_bias_field/01_controls.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_mri_bias_field.jpg" alt="MRI bias field" width="200" height="200"><span>MRI bias field</span></a>
<a href="../../articles/assets/poc/poc_nuclei_ploidy/01_histograms.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_nuclei_ploidy.jpg" alt="Nuclear ploidy" width="200" height="200"><span>Nuclear ploidy</span></a>
<a href="../../articles/assets/poc/poc_vessel_network/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_vessel_network.jpg" alt="Vessel network" width="200" height="200"><span>Vessel network</span></a>
<a href="../../articles/assets/poc/poc_wound_area_tracking/06_healing_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_wound_area_tracking.jpg" alt="Wound area" width="200" height="200"><b>&#9654;</b><span>Wound area</span></a>
<a href="../../articles/assets/poc/poc_physarum_maze/02_maze_tubes_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_physarum_maze.jpg" alt="Slime-mould maze" width="200" height="200"><b>&#9654;</b><span>Slime-mould maze</span></a>
<a href="../../articles/assets/poc/poc_physarum_transport/01_transport_tubes_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_physarum_transport.jpg" alt="Slime-mould transport" width="200" height="200"><b>&#9654;</b><span>Slime-mould transport</span></a>
</div>
</details>

<details class="vall"><summary><b>Astronomy और environment</b> (21)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_allsky_cloud_cover/01_jacobian.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_allsky_cloud_cover.jpg" alt="All-sky cloud cover" width="200" height="200"><span>All-sky cloud cover</span></a>
<a href="../../articles/assets/poc/poc_astro_photometry/01_stack_scaling.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_astro_photometry.jpg" alt="Star photometry" width="200" height="200"><span>Star photometry</span></a>
<a href="../../articles/assets/poc/poc_change_detection_misreg/01_plot_fp_vs_shift.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_change_detection_misreg.jpg" alt="Change detection" width="200" height="200"><span>Change detection</span></a>
<a href="../../articles/assets/poc/poc_datacenter_thermal_field/01_scene_truth.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_datacenter_thermal_field.jpg" alt="3-D thermal field" width="200" height="200"><span>3-D thermal field</span></a>
<a href="../../articles/assets/poc/poc_dem_terrain/05_terrain_flight.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dem_terrain.jpg" alt="Terrain (DEM)" width="200" height="200"><b>&#9654;</b><span>Terrain (DEM)</span></a>
<a href="../../articles/assets/poc/poc_exoplanet_transit/01_scene_starfield.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_exoplanet_transit.jpg" alt="Exoplanet transit" width="200" height="200"><span>Exoplanet transit</span></a>
<a href="../../articles/assets/poc/poc_geodetic_height_frames/01_geoid_frames.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_geodetic_height_frames.jpg" alt="Height datums" width="200" height="200"><span>Height datums</span></a>
<a href="../../articles/assets/poc/poc_leaf_disease_area/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_leaf_disease_area.jpg" alt="Leaf disease" width="200" height="200"><span>Leaf disease</span></a>
<a href="../../articles/assets/poc/poc_pv_thermal_survey/01_norm_table.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_pv_thermal_survey.jpg" alt="PV thermal survey" width="200" height="200"><span>PV thermal survey</span></a>
<a href="../../articles/assets/poc/poc_real_sky_photometry/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_sky_photometry.jpg" alt="Real deep sky" width="200" height="200"><span>Real deep sky</span></a>
<a href="../../articles/assets/poc/poc_river_surface_velocity/13_accumulate_pairs.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_river_surface_velocity.jpg" alt="River velocity" width="200" height="200"><b>&#9654;</b><span>River velocity</span></a>
<a href="../../articles/assets/poc/poc_sea_ice_concentration/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_sea_ice_concentration.jpg" alt="Sea-ice cover" width="200" height="200"><span>Sea-ice cover</span></a>
<a href="../../articles/assets/poc/poc_search_sweep_width/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_search_sweep_width.jpg" alt="Sweep width" width="200" height="200"><span>Sweep width</span></a>
<a href="../../articles/assets/poc/poc_solar_limb_darkening/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_solar_limb_darkening.jpg" alt="Limb darkening" width="200" height="200"><span>Limb darkening</span></a>
<a href="../../articles/assets/poc/poc_star_astrometry/01_snr_sweep.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_star_astrometry.jpg" alt="Star astrometry" width="200" height="200"><span>Star astrometry</span></a>
<a href="../../articles/assets/poc/poc_tree_ring_dendro/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_tree_ring_dendro.jpg" alt="Tree rings" width="200" height="200"><span>Tree rings</span></a>
<a href="../../articles/assets/poc/poc_vegetation_cover/01_mixed_pixel_response.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_vegetation_cover.jpg" alt="Vegetation cover" width="200" height="200"><span>Vegetation cover</span></a>
<a href="../../articles/assets/poc/poc_water_level/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_water_level.jpg" alt="River stage" width="200" height="200"><span>River stage</span></a>
<a href="../../articles/assets/poc/poc_rover_slip_risk_path/03_rover_slip_update.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_rover_slip_risk_path.jpg" alt="Mars rover slip" width="200" height="200"><b>&#9654;</b><span>Mars rover slip</span></a>
<a href="../../articles/assets/poc/poc_geodetic_benchmarks_real/01_residual_sorted.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_geodetic_benchmarks_real.jpg" alt="Two heights (real)" width="200" height="200"><span>Two heights (real)</span></a>
<a href="../../articles/assets/poc/poc_gravitational_lens_invariants/10_source_crossing.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_gravitational_lens_invariants.jpg" alt="Gravitational lens" width="200" height="200"><b>&#9654;</b><span>Gravitational lens</span></a>
</div>
</details>

<details class="vall"><summary><b>Forensics और documents</b> (4)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_document_scan/01_rectify_zero_points.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_document_scan.jpg" alt="Document scan" width="200" height="200"><span>Document scan</span></a>
<a href="../../articles/assets/poc/poc_forensics_roc/01_score_maps.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_forensics_roc.jpg" alt="Forgery ROC" width="200" height="200"><span>Forgery ROC</span></a>
<a href="../../articles/assets/poc/poc_fresco_craquelure/01_ridge_ops.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_fresco_craquelure.jpg" alt="Craquelure" width="200" height="200"><span>Craquelure</span></a>
<a href="../../articles/assets/poc/poc_prnu_camera_fingerprint/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_prnu_camera_fingerprint.jpg" alt="Camera fingerprint" width="200" height="200"><span>Camera fingerprint</span></a>
</div>
</details>

<details class="vall"><summary><b>Autonomous driving</b> (13)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_car_parking/04_parking_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_car_parking.jpg" alt="Car parking" width="200" height="200"><b>&#9654;</b><span>Car parking</span></a>
<a href="../../articles/assets/poc/poc_driving_school/05_drive_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_school.jpg" alt="Driving school" width="200" height="200"><b>&#9654;</b><span>Driving school</span></a>
<a href="../../articles/assets/poc/poc_ttc_rss/06_approach_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_ttc_rss.jpg" alt="TTC और RSS" width="200" height="200"><b>&#9654;</b><span>TTC और RSS</span></a>
<a href="../../articles/assets/poc/poc_world_terrain/06_drive_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_world_terrain.jpg" alt="World विस्तार" width="200" height="200"><b>&#9654;</b><span>World विस्तार</span></a>
<a href="../../articles/assets/poc/poc_driving_longitudinal/01_drive_with_time.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_longitudinal.jpg" alt="Inertia और slope" width="200" height="200"><b>&#9654;</b><span>Inertia और slope</span></a>
<a href="../../articles/assets/poc/poc_driving_weather/01_sun_day.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_weather.jpg" alt="Sun और weather" width="200" height="200"><b>&#9654;</b><span>Sun और weather</span></a>
<a href="../../articles/assets/poc/poc_driving_endless_map/01_minimap_stream.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_endless_map.jpg" alt="Endless map" width="200" height="200"><b>&#9654;</b><span>Endless map</span></a>
<a href="../../articles/assets/poc/poc_driving_traffic/01_dashcam_occlusion.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_traffic.jpg" alt="Traffic, blind spots" width="200" height="200"><b>&#9654;</b><span>Traffic, blind spots</span></a>
<a href="../../articles/assets/poc/poc_driving_decisions/01_decisions_mirrors_ambulance.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_decisions.jpg" alt="Decision scenes" width="200" height="200"><b>&#9654;</b><span>Decision scenes</span></a>
<a href="../../articles/assets/poc/poc_driving_lateral/01_lateral_dashcam.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_lateral.jpg" alt="Lateral motion" width="200" height="200"><b>&#9654;</b><span>Lateral motion</span></a>
<a href="../../articles/assets/poc/poc_driving_humanoids/03_humanoids_crossing.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_humanoids.jpg" alt="Humanoid crossing" width="200" height="200"><b>&#9654;</b><span>Humanoid crossing</span></a>
<a href="../../articles/assets/poc/poc_driving_crossing/01_crossing_dashcam.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_crossing.jpg" alt="Level crossings" width="200" height="200"><b>&#9654;</b><span>Level crossings</span></a>
<a href="../../articles/assets/poc/poc_driving_pass/01_overtake_dashcam.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_pass.jpg" alt="Overtaking" width="200" height="200"><b>&#9654;</b><span>Overtaking</span></a>
</div>
</details>

<details class="vall"><summary><b>Mathematical pictures</b> (7)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_one_stroke_epicycles/07_epicycles.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_one_stroke_epicycles.jpg" alt="Epicycle drawing" width="200" height="200"><b>&#9654;</b><span>Epicycle drawing</span></a>
<a href="../../articles/assets/poc/poc_complex_plane_fields/01_rational.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_complex_plane_fields.jpg" alt="Complex plane" width="200" height="200"><span>Complex plane</span></a>
<a href="../../articles/assets/poc/poc_theorems_as_pictures/01_apollonian.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_theorems_as_pictures.jpg" alt="Theorems as gates" width="200" height="200"><span>Theorems as gates</span></a>
<a href="../../articles/assets/poc/poc_beats_fringes_and_screens/01_membrane.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_beats_fringes_and_screens.jpg" alt="One beat" width="200" height="200"><span>One beat</span></a>
<a href="../../articles/assets/poc/poc_what_a_picture_cannot_check/01_rk4.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_what_a_picture_cannot_check.jpg" alt="Beyond pictures" width="200" height="200"><span>Beyond pictures</span></a>
<a href="../../articles/assets/poc/poc_illusions_and_perpetual_drawing/14_loop.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_illusions_and_perpetual_drawing.jpg" alt="Endless drawing" width="200" height="200"><b>&#9654;</b><span>Endless drawing</span></a>
<a href="../../articles/assets/poc/poc_calipers_under_illusion/01_caliper_on_cafe_wall.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_calipers_under_illusion.jpg" alt="Calipers vs illusions" width="200" height="200"><span>Calipers vs illusions</span></a>
</div>
</details>

<script>
document.querySelectorAll("details.vall").forEach(function (d) {
  d.addEventListener("toggle", function () {
    if (!d.open) return;
    d.querySelectorAll("img[data-src]").forEach(function (i) {
      i.src = i.getAttribute("data-src"); i.removeAttribute("data-src");
    });
  });
});
</script>

## क्या दिखता है, और मापी गई संख्या

हर संख्या उस ground truth (closed form, analytic solution या published value) के सापेक्ष measured है जिसे PoC ने खुद रखा है; PoC चलाने पर वही मान print होता है।

<div class="vl" markdown="1">

**Image inspection और appearance**

- [Faint defect सीमा](../../articles/assets/poc/poc_real_defect_floor/02_defect_floor_sweep.gif) (GIF): एक ही planted defect को असली brick texture पर और उतने ही noise वाले synthetic background पर धीरे-धीरे गहरा किया जाता है। **noise बराबर करने पर भी असली texture पर detection limit synthetic की 2.03-3.47 गुना है (ज्ञात position और amplitude वाले defect पर)।** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_defect_floor.py)
- [Active contours](../../articles/assets/poc/poc_active_contours/06_u_shape_snakes.mp4) (video): U-आकार के खांचे में classic snake (लाल) अंदर नहीं जा पाता, GVF (नीला) तल तक पहुँचता है। हरा = असली edge। **सिर्फ external force को GVF में बदलने पर Dice 0.993 (असली edge के सापेक्ष)।** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_active_contours.py)
- [DIC strain](../../articles/assets/poc/poc_dic_strain/05_tensile_ramp.mp4) (video): tensile load बढ़ाते हुए speckle image से strain map पढ़ा जाता है (मशीन साथ में 2 degree घूमती है)। **असली strain 3000 µε। small strain rotation के कारण 2341 µε (कम), Green-Lagrange 2961 µε (theory 3005 µε)।** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dic_strain.py)

**3-D measurement और geometry**

- [Focus stacking](../../articles/assets/poc/poc_focus_stacking/05_focus_sweep.mp4) (video): focus को 17 frames में sweep करते हुए all-in-focus image और depth map बनते जाते हैं। **all-in-focus PSNR 33.69 dB (बीच का 1 frame 28.52 dB), depth error 0.467 mm (texture वाले हिस्से में)।** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_focus_stacking.py)
- [Point cloud ICP](../../articles/assets/poc/poc_registration_basin/05_icp_basin_iterations.mp4) (video): शुरुआती rotation error 30 / 90 / 150 degree से ICP को हर बार 1 iteration चलाया जाता है। **60 iterations के बाद rotation error: 30 और 90 degree से 0.6 degree (सफल), 150 से 179.5 degree (असफल)।** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_registration_basin.py)
- [Stockpile आयतन](../../articles/assets/poc/poc_stockpile_volume/07_scan_orbit.mp4) (video): ढेर के चारों ओर घूमते हुए 3-D scan की जगहें 1 से 3 की जाती हैं। रंग = interpolated surface और असली surface का अंतर। **volume error +17.20 % -> +0.05 % (असली base; ground truth volume closed form से 3572.6089 m³)।** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_stockpile_volume.py)

**X-ray CT और volume**

- [CT reconstruction](../../articles/assets/poc/poc_ct_fidelity/01_recon_sweep.png) (figure): Shepp-Logan phantom को 180 से घटाकर 12 projections तक लेकर reconstruct किया जाता है। **12 projections वाला FBP (RMSE 0.2576) खाली image (0.2420) से भी हारता है। mass check ने -3.34 % की कमी पकड़ी, जिसे -0.0099 % तक ठीक किया गया।** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_fidelity.py)
- [CT voids](../../articles/assets/poc/poc_ct_void_morphology/13_section_sweep.mp4) (video): लगभग बराबर void fraction वाली 2 bond layers, section sweep और घूमते 3-D voids के साथ (video 4.3 MB)। **void fraction 2.46 % बनाम 2.63 %, फिर भी interface से दूरी का median 60.0 µm बनाम 10.0 µm।** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_void_morphology.py)

**Optics, interferometry, polarization**

- [White-light step](../../articles/assets/poc/poc_interferometry_step/05_step_sweep.mp4) (video): planted step को 0 से 0.90 µm तक बढ़ाकर coherence envelope और phase shifting से मापा जाता है। **1 % noise पर bias 2.4 nm के भीतर (step 50-500 nm)। phase shifting 0.153 µm पर λ/2 कूदता है।** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_interferometry_step.py)
- [Polarization](../../articles/assets/poc/poc_polarization_specular/03_separation.png) (figure): polarization से specular reflection हटाने का नतीजा, और बचे error का आकार। **diffuse घटक का error closed form R_p·E से मेल खाता है और Brewster angle 56.31 degree पर 0 होता है।** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_polarization_specular.py)
- [Photoelasticity](../../articles/assets/poc/poc_photoelasticity/03_load_and_isoclinics.mp4) (video): disc पर load देने से fringes उभरती हैं; polarizer घुमाने पर isoclinics खिसकती हैं। **केंद्र का fringe order 2.38 (closed form के अनुसार)। op का polariscope textbook सूत्र से अधिकतम 2.2e-16 अलग।** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_photoelasticity.py)

**Thermal, acoustic, time series**

- [Thermography NDT](../../articles/assets/poc/poc_thermography_ndt/02_depth_map.png) (figure): flash heating के बाद surface temperature से 16 delaminations की गहराई का map। **0.5 mm गहरा, 2 mm चौड़ा defect: 25 s fitting window पर +612 %, 4 s पर -9 %।** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_thermography_ndt.py)
- [Motion magnification](../../articles/assets/poc/poc_motion_magnification/05_magnify_video.mp4) (video): 0.1 px से कंपित surface: बाईं ओर raw video, दाईं ओर 10 गुना magnified video। **असली amplitude 0.1000 px; raw से 0.10012, magnification के बाद 0.10013 px। magnification देखने में मदद करता है, measurement नहीं सुधारता।** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_motion_magnification.py)

**Robotics और spatial perception**

- [Compound eye](../../articles/assets/poc/poc_compound_eye/02_compound_eye_superposition.png) (figure): compound-eye array को light-field sensor की तरह simulate करके एक ही point के N views जोड़े जाते हैं। अगला कदम इस light field को मक्खी के wiring diagram (connectome) से process करना है; नीचे connectome exhibits देखें। **SNR gain N=5 पर 2.25 (√5 = 2.24), N=49 पर 5.33 (√49 = 7.00)।** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_compound_eye.py)
- [Peg-in-hole](../../articles/assets/poc/poc_pegsim_insertion/04_pegsim_insert_corrected.gif) (GIF): wrist camera hole की position मापता है, arm उसके ऊपर जाता है, और compliant wrist peg डालता है (MuJoCo)। **7 servo steps में असली offset 2.24 -> 0.03 mm; correction के साथ insertion 12 / 12 सफल।** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pegsim_insertion.py)
- [Air hockey](../../articles/assets/poc/poc_air_hockey_intercept/02_airhockey_prediction_cone_narrows.gif) (GIF): coarse camera से puck को track करके defence line से crossing point का अनुमान; frames बढ़ने पर band पतला होता है। **crossing point का 95 % band N = 3 frames पर 145 mm से N = 16 पर 7 mm।** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_air_hockey_intercept.py)
- [Tactile sensor](../../articles/assets/poc/poc_tacsim_elastic_membrane/03_tacsim_force_sweep.gif) (GIF): sphere से elastic membrane पर load बढ़ाया जाता है; membrane image से contact radius पढ़ा जाता है। **Hertz closed form के सापेक्ष: contact radius error 0.05-0.26 %, force error 0.14-0.79 % (0.02-0.12 N)।** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_tacsim_elastic_membrane.py)

**Table tennis और motion**

- [Table tennis bounce](../../articles/assets/poc/poc_table_tennis_bounce/01_drop_test.mp4) (video): ITTF table test: ball को 30 cm से गिराकर video से उछाल की ऊँचाई पढ़ी जाती है। **video से पढ़ी उछाल की ऊँचाई 23.0 cm (ground truth 23.0 cm)।** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_table_tennis_bounce.py)
- [Table tennis spin](../../articles/assets/poc/poc_table_tennis_spin/01_side_three_serves.mp4) (video): एक जैसे मारे गए 3 balls: topspin नीचे जाता है, backspin ऊपर तैरता है। **landing x = 0.49 / 0.75 / 1.12 m। curve से पढ़े spin से अनुमानित landing point चारों 4 balls में ground truth से 2 cm के भीतर।** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_table_tennis_spin.py)
- [Rally misreads](../../articles/assets/poc/poc_table_tennis_rally_loop/02_height_misread.mp4) (video): ball की ऊँचाई 5 cm ज़्यादा पढ़ने पर planner नीचा arc चुनता है और ball पहले गिरती है। **target से 10.2 cm पहले गिरती है; shot से पहले first-order अनुमान 2.06 × 5 cm = 10.3 cm।** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_table_tennis_rally_loop.py)

**Autonomous driving**

- [Traffic, blind spots](../../articles/assets/poc/poc_driving_traffic/01_dashcam_occlusion.mp4) (video): parked car के पीछे से बच्चा दौड़कर निकलता है; background difference (बिना learning) से detect करके car रुकती है। **t = 7.30 s पर detect (ground truth से 0.133 s देर), बच्चे के रास्ते से 7.09 m पहले रुकती है।** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_driving_traffic.py)
- [Level crossings](../../articles/assets/poc/poc_driving_crossing/01_crossing_dashcam.mp4) (video): level crossing से पहले रुकना, alarm के दौरान इंतज़ार, दोनों ओर देखकर पार करना (driver का view)। **नियम मानने वाले 240 drivers: 0 violations, train आने पर track पर 0। alarm में घुसने वाले version में 157 violations, जिनमें 23 track पर।** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_driving_crossing.py)
- [Curve mirror](../../articles/assets/poc/poc_driving_pass/03_mirror_tjunction.mp4) (video): blind T-junction पर convex curve mirror में दिखती car को ray tracing से बनाकर दूरी पढ़ी जाती है। **mirror से 29 m दूर की car image size से 139 m दूर पढ़ी जाती है (closed form vertical reading 140 m)।** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_driving_pass.py)
- [TTC और RSS](../../articles/assets/poc/poc_ttc_rss/06_approach_gif.gif) (GIF): सामने से आती car के optical flow से time to collision τ; खड़ी car के लिए RSS safe distance से braking। **RSS के danger बताने पर t = 6.0 s पर braking, 10.25 m पहले रुकती है।** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ttc_rss.py)

**Connectome और neurons**

- [Eye से brain](../../articles/assets/poc/poc_eye_to_brain/01_eye_sweep.gif) (GIF): मक्खी की दाईं आँख के 1 ommatidium का stimulus आँख की एक पंक्ति पर चलाकर brain के wiring diagram (connectome) में दिया जाता है (GIF 4.4 MB)। **stimulated column और response centroid का correlation: connectome -0.92, degree-preserving shuffle +0.01।** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_eye_to_brain.py)
- [Fly brain wave](../../articles/assets/poc/poc_malecns_activity_wave/01_activity_wave_connectome_vs_shuffle.gif) (GIF): right optic lobe में दिया pulse असली wiring (बाएँ) और degree-preserving rewired wiring (दाएँ) से फैलता है। **असली wiring में activity की औसत दूरी 17 steps में 88 -> 230 µm बढ़ती है; rewired में 3 steps में 300 µm तक बिखर जाती है।** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_malecns_activity_wave.py)
- [Mouse cortex wave](../../articles/assets/poc/poc_microns_brain_wave/04_wave_on_wiring.gif) (GIF): 148 proofread axons के measured responses को mouse visual cortex के 1 mm³ की असली wiring में चलाया जाता है (MICrONS)। **measurement से correlation: असली wiring 0.085, degree-preserving shuffle 0.048।** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_microns_brain_wave.py)

**Robot की आँखें (perception Fullseye करता है)**

- [Humanoid stereo eyes](../../articles/assets/media/evis_stereo_fullseye.mp4) (video): musculoskeletal humanoid chopsticks से bean मारता है, अपनी दोनों आँखों (64 mm दूरी) से filmed; Fullseye हर frame में stereo disparity -> depth निकालता है। **bean तक दूरी का error: median 0.66 %, max 1.91 % (229 / 241 frames पढ़ने योग्य)।** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/tools/gen_evis_media.py)
- [Chopstick-cam tracking](../../articles/assets/media/evis_bean_track_fullseye.mp4) (video): उसी scene के chopstick-tip camera में Fullseye bean को detect और track करता है। **दिखने वाले सभी 163 frames में detect (163 / 163); centroid error ground truth से median 0.10 px।** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/tools/gen_evis_media.py)

</div>

## Fullseye क्या है

एक foundation जो physics simulation (optical design और 3-D measurement जैसी sensing सहित) और classic image processing को MCP और RAG के ज़रिए AI को देता है, हर task के लिए combination सोचने देता है, और type consistency तथा ground truth evaluation से जाँचते हुए task को interactive तरीके से हल करता है। Open source (Apache-2.0)।

<details markdown="1">
<summary><b>आज़माएँ</b> (Python 3.11)</summary>

```
pip install fullseye
git clone https://github.com/furuse-kazufumi/fullseye
cd fullseye
python examples/poc_focus_stacking.py
```

focus stacking PoC लगभग 20 सेकंड में चलता है और ground truth के सापेक्ष संख्याएँ तथा `PASS` print करता है। figures `out/figures/poc_focus_stacking/` में लिखे जाते हैं।

</details>

<details markdown="1">
<summary><b>Links</b></summary>

- [GitHub (source code)](https://github.com/furuse-kazufumi/fullseye)
- [Gallery (सभी figures)](../../GALLERY.en.md)
- [operators खोजें / AI (RAG) से उपयोग करें](../../AI_RAG_GUIDE.hi.md) · [MCP से उपयोग करें](../../MCP.md) _(ja)_
- [Documentation index](../../README.en.md)

</details>

<details markdown="1">
<summary><b>Paper</b></summary>

- **शीर्षक**: Fullseye：型付き演算子と物理シミュレーションに基づく画像検査・三次元計測基盤 _(ja)_ (typed operators और physics simulation पर आधारित image inspection और 3-D measurement foundation)
- **लेखक**: Kazufumi Furuse (स्वतंत्र शोधकर्ता)
- **प्रस्तुति**: ViEW2026, Workshop on Practical Use of Vision Technology
- **Paper PDF**: 2026-11-26 से उपलब्ध

**सार (जापानी से अनुवाद)**: हम Fullseye प्रस्तुत करते हैं: एक open-source foundation जो image inspection और 3-D measurement processing को घोषित input/output data types वाले operators की chain के रूप में बनाता है, physics और imaging simulation से बने ground truth के सापेक्ष उसका quantitative evaluation करता है, और processing procedure, evaluation तथा failure conditions को दोबारा उपयोग के लिए दर्ज करता है। इसमें लगभग 3,000 typed operators, execution से पहले type mismatch को अस्वीकार करने वाला check, multilingual operator search (RAG), और ground truth वाले 200 से अधिक proof-of-concept programs हैं। हम प्रतिनिधि उदाहरणों का quantitative evaluation और synthetic, measured और real-hardware validation stages के अंतर पर रिपोर्ट करते हैं।

</details>
