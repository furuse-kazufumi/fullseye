<div class="vlang" markdown="1">

[日本語](../index.md) · [English](../en/index.md) · [简体中文](../zh/index.md) · [繁體中文](../tw/index.md) · [한국어](../ko/index.md) · **Deutsch** · [हिन्दी](../hi/index.md)

</div>

# Fullseye — ViEW2026

Physiksimulation und Bildverarbeitung, mit KI kombiniert und an Ground Truth geprüft.

Kachel antippen öffnet Video oder Abbildung (▶ = bewegt).

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

## Highlights

<div class="vg">
<a href="../../articles/assets/poc/poc_real_defect_floor/02_defect_floor_sweep.gif"><img src="../thumbs/poc_real_defect_floor.jpg" alt="Schwache Defekte" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Schwache Defekte</span></a>
<a href="../../articles/assets/poc/poc_active_contours/06_u_shape_snakes.mp4"><img src="../thumbs/poc_active_contours.jpg" alt="Aktive Konturen" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Aktive Konturen</span></a>
<a href="../../articles/assets/poc/poc_dic_strain/05_tensile_ramp.mp4"><img src="../thumbs/poc_dic_strain.jpg" alt="DIC-Dehnung" loading="lazy" width="320" height="320"><b>&#9654;</b><span>DIC-Dehnung</span></a>
<a href="../../articles/assets/poc/poc_focus_stacking/05_focus_sweep.mp4"><img src="../thumbs/poc_focus_stacking.jpg" alt="Fokus-Stacking" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Fokus-Stacking</span></a>
<a href="../../articles/assets/poc/poc_registration_basin/05_icp_basin_iterations.mp4"><img src="../thumbs/poc_registration_basin.jpg" alt="Punktwolken-ICP" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Punktwolken-ICP</span></a>
<a href="../../articles/assets/poc/poc_stockpile_volume/07_scan_orbit.mp4"><img src="../thumbs/poc_stockpile_volume.jpg" alt="Haldenvolumen" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Haldenvolumen</span></a>
<a href="../../articles/assets/poc/poc_ct_fidelity/01_recon_sweep.png"><img src="../thumbs/poc_ct_fidelity.jpg" alt="CT-Rekonstruktion" loading="lazy" width="320" height="320"><span>CT-Rekonstruktion</span></a>
<a href="../../articles/assets/poc/poc_ct_void_morphology/13_section_sweep.mp4"><img src="../thumbs/poc_ct_void_morphology.jpg" alt="CT-Poren" loading="lazy" width="320" height="320"><b>&#9654;</b><span>CT-Poren</span></a>
<a href="../../articles/assets/poc/poc_interferometry_step/05_step_sweep.mp4"><img src="../thumbs/poc_interferometry_step.jpg" alt="Weißlicht-Stufen" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Weißlicht-Stufen</span></a>
<a href="../../articles/assets/poc/poc_polarization_specular/03_separation.png"><img src="../thumbs/poc_polarization_specular.jpg" alt="Polarisation" loading="lazy" width="320" height="320"><span>Polarisation</span></a>
<a href="../../articles/assets/poc/poc_photoelasticity/03_load_and_isoclinics.mp4"><img src="../thumbs/poc_photoelasticity.jpg" alt="Spannungsoptik" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Spannungsoptik</span></a>
<a href="../../articles/assets/poc/poc_thermography_ndt/02_depth_map.png"><img src="../thumbs/poc_thermography_ndt.jpg" alt="Thermografie" loading="lazy" width="320" height="320"><span>Thermografie</span></a>
<a href="../../articles/assets/poc/poc_motion_magnification/05_magnify_video.mp4"><img src="../thumbs/poc_motion_magnification.jpg" alt="Bewegungsverstärkung" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Bewegungsverstärkung</span></a>
<a href="../../articles/assets/poc/poc_table_tennis_bounce/01_drop_test.mp4"><img src="../thumbs/poc_table_tennis_bounce.jpg" alt="Tischtennis-Absprung" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Tischtennis-Absprung</span></a>
<a href="../../articles/assets/poc/poc_compound_eye/02_compound_eye_superposition.png"><img src="../thumbs/poc_compound_eye.jpg" alt="Facettenauge" loading="lazy" width="320" height="320"><span>Facettenauge</span></a>
<a href="../../articles/assets/poc/poc_pegsim_insertion/04_pegsim_insert_corrected.gif"><img src="../thumbs/poc_pegsim_insertion.jpg" alt="Peg-in-Hole" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Peg-in-Hole</span></a>
<a href="../../articles/assets/poc/poc_air_hockey_intercept/02_airhockey_prediction_cone_narrows.gif"><img src="../thumbs/poc_air_hockey_intercept.jpg" alt="Airhockey" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Airhockey</span></a>
<a href="../../articles/assets/poc/poc_tacsim_elastic_membrane/03_tacsim_force_sweep.gif"><img src="../thumbs/poc_tacsim_elastic_membrane.jpg" alt="Taktiler Sensor" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Taktiler Sensor</span></a>
<a href="../../articles/assets/poc/poc_table_tennis_spin/01_side_three_serves.mp4"><img src="../thumbs/poc_table_tennis_spin.jpg" alt="Tischtennis-Spin" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Tischtennis-Spin</span></a>
<a href="../../articles/assets/poc/poc_table_tennis_rally_loop/02_height_misread.mp4"><img src="../thumbs/poc_table_tennis_rally_loop.jpg" alt="Ballwechsel" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Ballwechsel</span></a>
<a href="../../articles/assets/poc/poc_driving_traffic/01_dashcam_occlusion.mp4"><img src="../thumbs/poc_driving_traffic.jpg" alt="Verkehr, toter Winkel" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Verkehr, toter Winkel</span></a>
<a href="../../articles/assets/poc/poc_driving_crossing/01_crossing_dashcam.mp4"><img src="../thumbs/poc_driving_crossing.jpg" alt="Bahnübergänge" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Bahnübergänge</span></a>
<a href="../../articles/assets/poc/poc_driving_pass/03_mirror_tjunction.mp4"><img src="../thumbs/poc_driving_pass.jpg" alt="Verkehrsspiegel" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Verkehrsspiegel</span></a>
<a href="../../articles/assets/poc/poc_ttc_rss/06_approach_gif.gif"><img src="../thumbs/poc_ttc_rss.jpg" alt="TTC und RSS" loading="lazy" width="320" height="320"><b>&#9654;</b><span>TTC und RSS</span></a>
<a href="../../articles/assets/poc/poc_eye_to_brain/01_eye_sweep.gif"><img src="../thumbs/poc_eye_to_brain.jpg" alt="Auge zum Gehirn" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Auge zum Gehirn</span></a>
<a href="../../articles/assets/poc/poc_malecns_activity_wave/01_activity_wave_connectome_vs_shuffle.gif"><img src="../thumbs/poc_malecns_activity_wave.jpg" alt="Fliegenhirn-Welle" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Fliegenhirn-Welle</span></a>
<a href="../../articles/assets/poc/poc_microns_brain_wave/04_wave_on_wiring.gif"><img src="../thumbs/poc_microns_brain_wave.jpg" alt="Mauskortex-Welle" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Mauskortex-Welle</span></a>
<a href="../../articles/assets/media/evis_stereo_fullseye.mp4"><img src="../thumbs/evis_stereo_depth.jpg" alt="Stereoaugen" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Stereoaugen</span></a>
<a href="../../articles/assets/media/evis_bean_track_fullseye.mp4"><img src="../thumbs/evis_bean_track.jpg" alt="Stäbchenkamera-Tracking" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Stäbchenkamera-Tracking</span></a>
</div>

## Artikelserien (englische Artikel auf Qiita)

<div class="vser">
<a href="https://qiita.com/furuse-kazufumi/items/8a8f23e53b19ee8cdc10"><img src="../thumbs/series_museum.gif" alt="Ein Messmuseum auf Papier" loading="lazy" width="480" height="270"><strong>Ein Messmuseum auf Papier</strong><span>PoCs mit selbst gesetzter Ground Truth</span></a>
<a href="https://qiita.com/furuse-kazufumi/items/a82bf9f341cc4f04ca75"><img src="../thumbs/series_table_tennis.gif" alt="Tischtennis" loading="lazy" width="480" height="270"><strong>Tischtennis</strong><span>Absprung und Reibung aus Video</span></a>
<a href="https://qiita.com/furuse-kazufumi/items/05de90f4d316cd7c681c"><img src="../thumbs/series_driving.gif" alt="Autonomes Fahren" loading="lazy" width="480" height="270"><strong>Autonomes Fahren</strong><span>Bewertet mit Sätzen und Zweitimplementierungen</span></a>
<a href="https://qiita.com/furuse-kazufumi/items/638f0b0aa7865e17c67c"><img src="../thumbs/series_connectome.gif" alt="Konnektom (Gehirnverdrahtung)" loading="lazy" width="480" height="270"><strong>Konnektom (Gehirnverdrahtung)</strong><span>Ein Fliegen-Sehmodell im Körper, gemessen</span></a>
<a href="https://qiita.com/furuse-kazufumi/items/569720dbae0c6471c96e"><img src="../thumbs/series_humanoid.gif" alt="Humanoiden-Sportfest" loading="lazy" width="480" height="270"><strong>Humanoiden-Sportfest</strong><span>Ein Sportfest daheim, Schiedsrichter ist die Bildverarbeitung</span></a>
</div>

## Alles ansehen

218 PoCs und 4 Roboteraugen-Demos. Eine Gruppe aufklappen lädt ihre Vorschaubilder.

<noscript><p><a href="../../GALLERY.en.html">(Ohne JavaScript stehen alle Abbildungen auf der Galerieseite.)</a></p></noscript>

<details class="vall"><summary><b>Roboteraugen (Fullseye übernimmt die Wahrnehmung)</b> (4)</summary>
<div class="vg vs">
<a href="../../articles/assets/media/evis_stereo_fullseye.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/evis_stereo_depth.jpg" alt="Stereoaugen" width="200" height="200"><b>&#9654;</b><span>Stereoaugen</span></a>
<a href="../../articles/assets/media/evis_bean_track_fullseye.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/evis_bean_track.jpg" alt="Stäbchenkamera-Tracking" width="200" height="200"><b>&#9654;</b><span>Stäbchenkamera-Tracking</span></a>
<a href="../../view2026/media/evis_fullseye_walk.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/evis_walk_rgb_depth_dvs.jpg" alt="Gang in RGB, Tiefe, DVS" width="200" height="200"><b>&#9654;</b><span>Gang in RGB, Tiefe, DVS</span></a>
<a href="../../view2026/media/vision_adaptive_walk.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/walker2d_terrain_vision.jpg" alt="Stufen sehen, Gang wählen" width="200" height="200"><span>Stufen sehen, Gang wählen</span></a>
</div>
</details>

<details class="vall"><summary><b>Industrielle Prüfung</b> (32)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_barcode_1d/01_misread_split.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_barcode_1d.jpg" alt="1-D-Barcode" width="200" height="200"><span>1-D-Barcode</span></a>
<a href="../../articles/assets/poc/poc_battery_electrode_tortuosity/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_battery_electrode_tortuosity.jpg" alt="Elektroden-Tortuosität" width="200" height="200"><span>Elektroden-Tortuosität</span></a>
<a href="../../articles/assets/poc/poc_bearing_diagnosis/01_envelope_vs_raw.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_bearing_diagnosis.jpg" alt="Lagerdiagnose" width="200" height="200"><span>Lagerdiagnose</span></a>
<a href="../../articles/assets/poc/poc_bump_coplanarity/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_bump_coplanarity.jpg" alt="Bump-Koplanarität" width="200" height="200"><span>Bump-Koplanarität</span></a>
<a href="../../articles/assets/poc/poc_crack_width/01_width_sweep.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_crack_width.jpg" alt="Rissbreite" width="200" height="200"><span>Rissbreite</span></a>
<a href="../../articles/assets/poc/poc_fabric_defect/01_auc_by_type.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_fabric_defect.jpg" alt="Gewebefehler" width="200" height="200"><span>Gewebefehler</span></a>
<a href="../../articles/assets/poc/poc_leak_localization/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_leak_localization.jpg" alt="Leckortung" width="200" height="200"><span>Leckortung</span></a>
<a href="../../articles/assets/poc/poc_machine_condition_fusion/01_scene_machine.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_machine_condition_fusion.jpg" alt="Maschinenzustand" width="200" height="200"><span>Maschinenzustand</span></a>
<a href="../../articles/assets/poc/poc_matrix_code_reading/01_symbol_and_errors.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_matrix_code_reading.jpg" alt="Matrixcode" width="200" height="200"><span>Matrixcode</span></a>
<a href="../../articles/assets/poc/poc_moire_screen/01_failure_split_plot.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_moire_screen.jpg" alt="Display-Moiré" width="200" height="200"><span>Display-Moiré</span></a>
<a href="../../articles/assets/poc/poc_print_registration/01_plates.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_print_registration.jpg" alt="Passerfehler" width="200" height="200"><span>Passerfehler</span></a>
<a href="../../articles/assets/poc/poc_real_defect_floor/02_defect_floor_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_defect_floor.jpg" alt="Schwache Defekte" width="200" height="200"><b>&#9654;</b><span>Schwache Defekte</span></a>
<a href="../../articles/assets/poc/poc_real_texture_invariance/01_textures.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_texture_invariance.jpg" alt="Texturdrehung" width="200" height="200"><span>Texturdrehung</span></a>
<a href="../../articles/assets/poc/poc_recycling_sorting/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_recycling_sorting.jpg" alt="Abfallsortierung" width="200" height="200"><span>Abfallsortierung</span></a>
<a href="../../articles/assets/poc/poc_solar_el_inspection/01_zero_point_map.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_solar_el_inspection.jpg" alt="Solar-EL" width="200" height="200"><span>Solar-EL</span></a>
<a href="../../articles/assets/poc/poc_solder_fillet_aoi/01_ring_lut.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_solder_fillet_aoi.jpg" alt="Lötstellen-AOI" width="200" height="200"><span>Lötstellen-AOI</span></a>
<a href="../../articles/assets/poc/poc_spc/01_spc_xbar_chart.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_spc.jpg" alt="SPC" width="200" height="200"><span>SPC</span></a>
<a href="../../articles/assets/poc/poc_mt_hidden_fault/01_mt_hidden_cloud.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_mt_hidden_fault.jpg" alt="MT-Fehlererkennung" width="200" height="200"><span>MT-Fehlererkennung</span></a>
<a href="../../articles/assets/poc/poc_text_region_truth/01_text_region_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_text_region_truth.jpg" alt="Textbereiche" width="200" height="200"><span>Textbereiche</span></a>
<a href="../../articles/assets/poc/poc_thermal_drift_metrology/01_separate_drifts.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_thermal_drift_metrology.jpg" alt="Thermische Drift" width="200" height="200"><span>Thermische Drift</span></a>
<a href="../../articles/assets/poc/poc_thermal_radiometry/01_floor.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_thermal_radiometry.jpg" alt="Thermoradiometrie" width="200" height="200"><span>Thermoradiometrie</span></a>
<a href="../../articles/assets/poc/poc_thermography_ndt/01_depth_table.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_thermography_ndt.jpg" alt="Thermografie" width="200" height="200"><span>Thermografie</span></a>
<a href="../../articles/assets/poc/poc_veiling_glare/01_verdict.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_veiling_glare.jpg" alt="Streulicht" width="200" height="200"><span>Streulicht</span></a>
<a href="../../articles/assets/poc/poc_emva1288_sensor/01_photon_transfer.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_emva1288_sensor.jpg" alt="EMVA-1288-Sensor" width="200" height="200"><b>&#9654;</b><span>EMVA-1288-Sensor</span></a>
<a href="../../articles/assets/poc/poc_web_roll_periodicity/01_scene_web.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_web_roll_periodicity.jpg" alt="Walzenfehler" width="200" height="200"><span>Walzenfehler</span></a>
<a href="../../articles/assets/poc/poc_weld_bead_profile/01_laser_images.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_weld_bead_profile.jpg" alt="Schweißnahtprofil" width="200" height="200"><span>Schweißnahtprofil</span></a>
<a href="../../articles/assets/poc/poc_weld_bead_scan_angle/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_weld_bead_scan_angle.jpg" alt="Schweißnaht-Scan" width="200" height="200"><span>Schweißnaht-Scan</span></a>
<a href="../../articles/assets/poc/poc_weld_radiograph_porosity/01_scene_radiograph.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_weld_radiograph_porosity.jpg" alt="Schweißporen" width="200" height="200"><span>Schweißporen</span></a>
<a href="../../articles/assets/poc/poc_glyph_typo_detection/01_sign_before_after.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_glyph_typo_detection.jpg" alt="Glyphenfehler" width="200" height="200"><span>Glyphenfehler</span></a>
<a href="../../articles/assets/poc/poc_print_layer_inspection/01_slice_stack.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_print_layer_inspection.jpg" alt="Druckschichten" width="200" height="200"><span>Druckschichten</span></a>
<a href="../../articles/assets/poc/poc_agv_fleet/01_agv_naive_vs_adg.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_agv_fleet.jpg" alt="AGV-Flotte" width="200" height="200"><b>&#9654;</b><span>AGV-Flotte</span></a>
<a href="../../articles/assets/poc/poc_am_thermal_to_ct/01_melt_pool_frames.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_am_thermal_to_ct.jpg" alt="AM-Thermo zu CT" width="200" height="200"><b>&#9654;</b><span>AM-Thermo zu CT</span></a>
</div>
</details>

<details class="vall"><summary><b>Maß- und Formmessung</b> (36)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_aoi_ct_traceability/01_aoi_and_ct.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_aoi_ct_traceability.jpg" alt="AOI-CT-Zuordnung" width="200" height="200"><span>AOI-CT-Zuordnung</span></a>
<a href="../../articles/assets/poc/poc_asbuilt_wall_deviation/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_asbuilt_wall_deviation.jpg" alt="Ist-Wände" width="200" height="200"><span>Ist-Wände</span></a>
<a href="../../articles/assets/poc/poc_battery_electrode_breathing/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_battery_electrode_breathing.jpg" alt="Elektrodenatmung" width="200" height="200"><span>Elektrodenatmung</span></a>
<a href="../../articles/assets/poc/poc_bilateral_asymmetry/01_floor_vs_spacing.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_bilateral_asymmetry.jpg" alt="Seitenasymmetrie" width="200" height="200"><span>Seitenasymmetrie</span></a>
<a href="../../articles/assets/poc/poc_dic_strain/05_tensile_ramp.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dic_strain.jpg" alt="DIC-Dehnung" width="200" height="200"><b>&#9654;</b><span>DIC-Dehnung</span></a>
<a href="../../articles/assets/poc/poc_die_tilt_tsv_overlay/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_die_tilt_tsv_overlay.jpg" alt="Die-Kippung und TSV" width="200" height="200"><span>Die-Kippung und TSV</span></a>
<a href="../../articles/assets/poc/poc_dimensional_inspection/01_slot_bias.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dimensional_inspection.jpg" alt="Maßprüfung" width="200" height="200"><span>Maßprüfung</span></a>
<a href="../../articles/assets/poc/poc_fiber_orientation/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_fiber_orientation.jpg" alt="Faserorientierung" width="200" height="200"><span>Faserorientierung</span></a>
<a href="../../articles/assets/poc/poc_gear_tooth_metrology/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_gear_tooth_metrology.jpg" alt="Zahnradmessung" width="200" height="200"><span>Zahnradmessung</span></a>
<a href="../../articles/assets/poc/poc_interferometry_step/05_step_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_interferometry_step.jpg" alt="Weißlicht-Stufen" width="200" height="200"><b>&#9654;</b><span>Weißlicht-Stufen</span></a>
<a href="../../articles/assets/poc/poc_metal_grain_size/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_metal_grain_size.jpg" alt="Korngröße" width="200" height="200"><span>Korngröße</span></a>
<a href="../../articles/assets/poc/poc_multibeam_bathymetry/17_survey.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_multibeam_bathymetry.jpg" alt="Fächerecholot" width="200" height="200"><b>&#9654;</b><span>Fächerecholot</span></a>
<a href="../../articles/assets/poc/poc_particle_sizing/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_particle_sizing.jpg" alt="Partikelgrößen" width="200" height="200"><span>Partikelgrößen</span></a>
<a href="../../articles/assets/poc/poc_photoelasticity/03_load_and_isoclinics.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_photoelasticity.jpg" alt="Spannungsoptik" width="200" height="200"><b>&#9654;</b><span>Spannungsoptik</span></a>
<a href="../../articles/assets/poc/poc_rail_corrugation/01_planted_components.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_rail_corrugation.jpg" alt="Schienenriffel" width="200" height="200"><span>Schienenriffel</span></a>
<a href="../../articles/assets/poc/poc_real_coin_metrology/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_coin_metrology.jpg" alt="Echte Münzen" width="200" height="200"><span>Echte Münzen</span></a>
<a href="../../articles/assets/poc/poc_screw_thread_metrology/01_zero_spectrum.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_screw_thread_metrology.jpg" alt="Gewindemessung" width="200" height="200"><span>Gewindemessung</span></a>
<a href="../../articles/assets/poc/poc_stockpile_volume/07_scan_orbit.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_stockpile_volume.jpg" alt="Haldenvolumen" width="200" height="200"><b>&#9654;</b><span>Haldenvolumen</span></a>
<a href="../../articles/assets/poc/poc_strain_history/05_history_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_strain_history.jpg" alt="Kriechdehnung" width="200" height="200"><b>&#9654;</b><span>Kriechdehnung</span></a>
<a href="../../articles/assets/poc/poc_surface_roughness/01_surface_components.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_surface_roughness.jpg" alt="Oberflächenrauheit" width="200" height="200"><span>Oberflächenrauheit</span></a>
<a href="../../articles/assets/poc/poc_tacsim_elastic_membrane/03_tacsim_force_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_tacsim_elastic_membrane.jpg" alt="Taktiler Sensor" width="200" height="200"><b>&#9654;</b><span>Taktiler Sensor</span></a>
<a href="../../articles/assets/poc/poc_tacsim_marker_shear/02_tacslip_stick_circle_shrinks.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_tacsim_marker_shear.jpg" alt="Taktile Scherung" width="200" height="200"><b>&#9654;</b><span>Taktile Scherung</span></a>
<a href="../../articles/assets/poc/poc_tactile_dipole_torque/02_tactorque_dipole_grows_with_M.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_tactile_dipole_torque.jpg" alt="Taktiler Dipol" width="200" height="200"><b>&#9654;</b><span>Taktiler Dipol</span></a>
<a href="../../articles/assets/poc/poc_granular_heap_repose/11_granular_datum_tilt_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_granular_heap_repose.jpg" alt="Schüttgutkegel" width="200" height="200"><b>&#9654;</b><span>Schüttgutkegel</span></a>
<a href="../../articles/assets/poc/poc_food_cutting_measure/01_cutting_track_force.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_food_cutting_measure.jpg" alt="Lebensmittel schneiden" width="200" height="200"><b>&#9654;</b><span>Lebensmittel schneiden</span></a>
<a href="../../articles/assets/poc/poc_tacdome_large_deformation/01_tacdome_press_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_tacdome_large_deformation.jpg" alt="Weiche Kuppel" width="200" height="200"><b>&#9654;</b><span>Weiche Kuppel</span></a>
<a href="../../articles/assets/poc/poc_polish_wipe_measure/01_polish_raster_wipe_coat.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_polish_wipe_measure.jpg" alt="Polieren, Wischen" width="200" height="200"><b>&#9654;</b><span>Polieren, Wischen</span></a>
<a href="../../articles/assets/poc/poc_powder_scoop_pour/03_scoop_stream_synthetic_frames.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_powder_scoop_pour.jpg" alt="Pulver schöpfen" width="200" height="200"><b>&#9654;</b><span>Pulver schöpfen</span></a>
<a href="../../articles/assets/poc/poc_powder_grinding_ae/07_psd_fining_during_grinding.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_powder_grinding_ae.jpg" alt="Mörsermahlen" width="200" height="200"><b>&#9654;</b><span>Mörsermahlen</span></a>
<a href="../../articles/assets/poc/poc_pxrd_phase_peel/01_phase_peel.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_pxrd_phase_peel.jpg" alt="PXRD-Phasen" width="200" height="200"><b>&#9654;</b><span>PXRD-Phasen</span></a>
<a href="../../articles/assets/poc/poc_dose_uniformity_from_grinding/01_cv_bias_decomposition.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dose_uniformity_from_grinding.jpg" alt="Dosisgleichförmigkeit" width="200" height="200"><span>Dosisgleichförmigkeit</span></a>
<a href="../../articles/assets/poc/poc_knife_tactile_toughness/06_cut_with_fingertip_pads.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_knife_tactile_toughness.jpg" alt="Taktiles Messer" width="200" height="200"><b>&#9654;</b><span>Taktiles Messer</span></a>
<a href="../../articles/assets/poc/poc_measurement_system_analysis/16_breakdown_movie.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_measurement_system_analysis.jpg" alt="Gage R&R" width="200" height="200"><b>&#9654;</b><span>Gage R&R</span></a>
<a href="../../articles/assets/poc/poc_zernike_aberrations/06_through_focus.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_zernike_aberrations.jpg" alt="Zernike-Aberrationen" width="200" height="200"><b>&#9654;</b><span>Zernike-Aberrationen</span></a>
<a href="../../articles/assets/poc/poc_attention_identities/01_attention_masks.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_attention_identities.jpg" alt="Attention-Identitäten" width="200" height="200"><span>Attention-Identitäten</span></a>
<a href="../../articles/assets/poc/poc_residue_crt/03_residue_rotation_needle.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_residue_crt.jpg" alt="Phasen-CRT" width="200" height="200"><b>&#9654;</b><span>Phasen-CRT</span></a>
</div>
</details>

<details class="vall"><summary><b>3-D-Form</b> (18)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_battery_ct_degradation/01_xray_projection.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_battery_ct_degradation.jpg" alt="Batterie-CT" width="200" height="200"><span>Batterie-CT</span></a>
<a href="../../articles/assets/poc/poc_bev_sensor_fusion/01_scene_bev.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_bev_sensor_fusion.jpg" alt="BEV-Sensorfusion" width="200" height="200"><span>BEV-Sensorfusion</span></a>
<a href="../../articles/assets/poc/poc_cad_scan_deviation/14_align_orbit.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_cad_scan_deviation.jpg" alt="CAD-Scan-Abweichung" width="200" height="200"><b>&#9654;</b><span>CAD-Scan-Abweichung</span></a>
<a href="../../articles/assets/poc/poc_crop_phenotyping/01_capsule_calibration.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_crop_phenotyping.jpg" alt="Blattfläche" width="200" height="200"><span>Blattfläche</span></a>
<a href="../../articles/assets/poc/poc_ct_void_morphology/13_section_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_ct_void_morphology.jpg" alt="Poren in Fügeschicht" width="200" height="200"><b>&#9654;</b><span>Poren in Fügeschicht</span></a>
<a href="../../articles/assets/poc/poc_dfm_thickness_overhang/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dfm_thickness_overhang.jpg" alt="Fertigbarkeit" width="200" height="200"><span>Fertigbarkeit</span></a>
<a href="../../articles/assets/poc/poc_lidar_terrain_change/12_flight.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_lidar_terrain_change.jpg" alt="Böschungsvolumen" width="200" height="200"><b>&#9654;</b><span>Böschungsvolumen</span></a>
<a href="../../articles/assets/poc/poc_livestock_body_volume/14_hull_orbit.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_livestock_body_volume.jpg" alt="Tiergewicht" width="200" height="200"><b>&#9654;</b><span>Tiergewicht</span></a>
<a href="../../articles/assets/poc/poc_mesh_quality_repair/14_decimate_orbit.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_mesh_quality_repair.jpg" alt="Netzreparatur" width="200" height="200"><b>&#9654;</b><span>Netzreparatur</span></a>
<a href="../../articles/assets/poc/poc_pallet_load_utilization/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_pallet_load_utilization.jpg" alt="Palettenauslastung" width="200" height="200"><span>Palettenauslastung</span></a>
<a href="../../articles/assets/poc/poc_pipe_wall_loss/01_scene_pipe.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_pipe_wall_loss.jpg" alt="Rohrwandverlust" width="200" height="200"><span>Rohrwandverlust</span></a>
<a href="../../articles/assets/poc/poc_print_warpage_risk/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_print_warpage_risk.jpg" alt="Druckverzug" width="200" height="200"><span>Druckverzug</span></a>
<a href="../../articles/assets/poc/poc_safety_clearance/01_conditions.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_safety_clearance.jpg" alt="Sicherheitsabstand" width="200" height="200"><span>Sicherheitsabstand</span></a>
<a href="../../articles/assets/poc/poc_scan_to_bim_asbuilt/01_scene_plan_section.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_scan_to_bim_asbuilt.jpg" alt="Scan-to-BIM" width="200" height="200"><span>Scan-to-BIM</span></a>
<a href="../../articles/assets/poc/poc_structure_4d_deterioration/12_years_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_structure_4d_deterioration.jpg" alt="Jährliche Bauwerksmessung" width="200" height="200"><b>&#9654;</b><span>Jährliche Bauwerksmessung</span></a>
<a href="../../articles/assets/poc/poc_symmetry_restoration/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_symmetry_restoration.jpg" alt="Symmetrie-Ergänzung" width="200" height="200"><span>Symmetrie-Ergänzung</span></a>
<a href="../../articles/assets/poc/poc_endless_zoom_and_turning_solids/03_zoom_loop.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_endless_zoom_and_turning_solids.jpg" alt="Endloser Zoom" width="200" height="200"><b>&#9654;</b><span>Endloser Zoom</span></a>
<a href="../../articles/assets/poc/poc_four_dimensions_by_three_d_tools/03_hopf_turn.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_four_dimensions_by_three_d_tools.jpg" alt="4-D mit 3-D-Werkzeugen" width="200" height="200"><b>&#9654;</b><span>4-D mit 3-D-Werkzeugen</span></a>
</div>
</details>

<details class="vall"><summary><b>Geometrie und Kalibrierung</b> (18)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_camera_calibration/05_calibration_convergence.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_camera_calibration.jpg" alt="Kamerakalibrierung" width="200" height="200"><b>&#9654;</b><span>Kamerakalibrierung</span></a>
<a href="../../articles/assets/poc/poc_panorama_drift/05_chain_drift_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_panorama_drift.jpg" alt="Panoramadrift" width="200" height="200"><b>&#9654;</b><span>Panoramadrift</span></a>
<a href="../../articles/assets/poc/poc_real_stereo_depth/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_stereo_depth.jpg" alt="Echte Stereo" width="200" height="200"><span>Echte Stereo</span></a>
<a href="../../articles/assets/poc/poc_registration_basin/05_icp_basin_iterations.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_registration_basin.jpg" alt="Punktwolken-ICP" width="200" height="200"><b>&#9654;</b><span>Punktwolken-ICP</span></a>
<a href="../../articles/assets/poc/poc_rotation_invariance_audit/02_rotating_coin.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_rotation_invariance_audit.jpg" alt="Rotationsprüfung" width="200" height="200"><b>&#9654;</b><span>Rotationsprüfung</span></a>
<a href="../../articles/assets/poc/poc_carla_bridge/01_carla_two_worlds.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_carla_bridge.jpg" alt="Zwei Welten (CARLA)" width="200" height="200"><span>Zwei Welten (CARLA)</span></a>
<a href="../../articles/assets/poc/poc_driving_town/04_town_drive_through.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_town.jpg" alt="Eine Stadt bauen" width="200" height="200"><b>&#9654;</b><span>Eine Stadt bauen</span></a>
<a href="../../articles/assets/poc/poc_driving_japan_town/03_japan_town_drive.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_japan_town.jpg" alt="Echte japanische Stadt" width="200" height="200"><b>&#9654;</b><span>Echte japanische Stadt</span></a>
<a href="../../articles/assets/poc/poc_driving_commonroad/01_commonroad_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_commonroad.jpg" alt="CommonRoad-Bewertung" width="200" height="200"><span>CommonRoad-Bewertung</span></a>
<a href="../../articles/assets/poc/poc_pegsim_insertion/04_pegsim_insert_corrected.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_pegsim_insertion.jpg" alt="Peg-in-Hole" width="200" height="200"><b>&#9654;</b><span>Peg-in-Hole</span></a>
<a href="../../articles/assets/poc/poc_air_hockey_intercept/02_airhockey_prediction_cone_narrows.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_air_hockey_intercept.jpg" alt="Airhockey" width="200" height="200"><b>&#9654;</b><span>Airhockey</span></a>
<a href="../../articles/assets/poc/poc_peg_failure_recovery/05_pegfail_wrist_camera_wedging_detect_recover.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_peg_failure_recovery.jpg" alt="Fehler-Recovery" width="200" height="200"><b>&#9654;</b><span>Fehler-Recovery</span></a>
<a href="../../articles/assets/poc/poc_tacscalib_sphere_lut/02_tacscalib_synthetic_relight.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_tacscalib_sphere_lut.jpg" alt="Taktil-Kalibrierung" width="200" height="200"><b>&#9654;</b><span>Taktil-Kalibrierung</span></a>
<a href="../../articles/assets/poc/poc_peg_insertion_tactile/03_pegtactile_whitney_insertion_through_membranes.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_peg_insertion_tactile.jpg" alt="Taktiles Einsetzen" width="200" height="200"><b>&#9654;</b><span>Taktiles Einsetzen</span></a>
<a href="../../articles/assets/poc/poc_peg_symmetry_search/01_pegsym_rotating_shapes_read_mod_2pi_over_n.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_peg_symmetry_search.jpg" alt="Stift-Symmetrie" width="200" height="200"><b>&#9654;</b><span>Stift-Symmetrie</span></a>
<a href="../../articles/assets/poc/poc_reproducible_icp/01_error_staircase_ozaki1.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_reproducible_icp.jpg" alt="Reproduzierbares ICP" width="200" height="200"><span>Reproduzierbares ICP</span></a>
<a href="../../articles/assets/poc/poc_public_camera_heading/02_yaw_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_public_camera_heading.jpg" alt="Kamerarichtung" width="200" height="200"><b>&#9654;</b><span>Kamerarichtung</span></a>
<a href="../../articles/assets/poc/poc_public_camera_heading_real/02_sunset_follow.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_public_camera_heading_real.jpg" alt="Kamerarichtung (echt)" width="200" height="200"><b>&#9654;</b><span>Kamerarichtung (echt)</span></a>
</div>
</details>

<details class="vall"><summary><b>Bildqualität und Restaurierung</b> (16)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_camera_shake_deblur/05_kernel_angle_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_camera_shake_deblur.jpg" alt="Verwacklung entfernen" width="200" height="200"><b>&#9654;</b><span>Verwacklung entfernen</span></a>
<a href="../../articles/assets/poc/poc_colormap_readability/01_gain_profile.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_colormap_readability.jpg" alt="Farbskalen-Lesbarkeit" width="200" height="200"><span>Farbskalen-Lesbarkeit</span></a>
<a href="../../articles/assets/poc/poc_compound_eye/01_compound_eye_scaling.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_compound_eye.jpg" alt="Fliegen-Facettenauge" width="200" height="200"><span>Fliegen-Facettenauge</span></a>
<a href="../../articles/assets/poc/poc_ct_fidelity/01_recon_sweep.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_ct_fidelity.jpg" alt="CT-Rekonstruktion" width="200" height="200"><span>CT-Rekonstruktion</span></a>
<a href="../../articles/assets/poc/poc_dehazing/05_haze_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dehazing.jpg" alt="Dunstentfernung" width="200" height="200"><b>&#9654;</b><span>Dunstentfernung</span></a>
<a href="../../articles/assets/poc/poc_dtof_ranging/01_histograms.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dtof_ranging.jpg" alt="Photonen-Entfernung" width="200" height="200"><span>Photonen-Entfernung</span></a>
<a href="../../articles/assets/poc/poc_focus_stacking/05_focus_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_focus_stacking.jpg" alt="Fokus-Stacking" width="200" height="200"><b>&#9654;</b><span>Fokus-Stacking</span></a>
<a href="../../articles/assets/poc/poc_lightfield_depth/01_scene_and_depth.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_lightfield_depth.jpg" alt="Lichtfeld-Tiefe" width="200" height="200"><span>Lichtfeld-Tiefe</span></a>
<a href="../../articles/assets/poc/poc_real_deblur_honesty/01_restore.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_deblur_honesty.jpg" alt="Echtes Entschärfen" width="200" height="200"><span>Echtes Entschärfen</span></a>
<a href="../../articles/assets/poc/poc_superresolution_limits/05_growth.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_superresolution_limits.jpg" alt="Superauflösung" width="200" height="200"><b>&#9654;</b><span>Superauflösung</span></a>
<a href="../../articles/assets/poc/poc_iqa_tid2013/01_tid2013_mos_vs_psnr.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_iqa_tid2013.jpg" alt="IQA mit TID2013" width="200" height="200"><span>IQA mit TID2013</span></a>
<a href="../../articles/assets/poc/poc_iqa_fsim_gmsd_vif/01_iqa_tid2013_mos_vs_fsim.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_iqa_fsim_gmsd_vif.jpg" alt="FSIM/GMSD/VIF" width="200" height="200"><span>FSIM/GMSD/VIF</span></a>
<a href="../../articles/assets/poc/poc_vanishing_detail_and_morphing_area/06_morph_loop.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_vanishing_detail_and_morphing_area.jpg" alt="Verschwindende Details" width="200" height="200"><b>&#9654;</b><span>Verschwindende Details</span></a>
<a href="../../articles/assets/poc/poc_segmentation_gauntlet/08_gauntlet_blobs.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_segmentation_gauntlet.jpg" alt="Segmentierungs-Parcours" width="200" height="200"><b>&#9654;</b><span>Segmentierungs-Parcours</span></a>
<a href="../../articles/assets/poc/poc_active_contours/06_u_shape_snakes.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_active_contours.jpg" alt="Aktive Konturen" width="200" height="200"><b>&#9654;</b><span>Aktive Konturen</span></a>
<a href="../../articles/assets/poc/poc_graph_hierarchy_segmentation/08_watershed_theta_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_graph_hierarchy_segmentation.jpg" alt="Graph-Segmentierung" width="200" height="200"><b>&#9654;</b><span>Graph-Segmentierung</span></a>
</div>
</details>

<details class="vall"><summary><b>Farbe und Trennung</b> (4)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_pigment_unmixing/01_per_field_auc.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_pigment_unmixing.jpg" alt="Pigmentschichten" width="200" height="200"><span>Pigmentschichten</span></a>
<a href="../../articles/assets/poc/poc_polarization_specular/01_fresnel.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_polarization_specular.jpg" alt="Polarisation" width="200" height="200"><span>Polarisation</span></a>
<a href="../../articles/assets/poc/poc_real_stain_unmix/01_separation.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_stain_unmix.jpg" alt="Färbungstrennung" width="200" height="200"><span>Färbungstrennung</span></a>
<a href="../../articles/assets/poc/poc_white_balance/01_casts.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_white_balance.jpg" alt="Weißabgleich" width="200" height="200"><span>Weißabgleich</span></a>
</div>
</details>

<details class="vall"><summary><b>Zeit als 3-D</b> (21)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_beam_modal_video/14_beam_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_beam_modal_video.jpg" alt="Modalanalyse per Video" width="200" height="200"><b>&#9654;</b><span>Modalanalyse per Video</span></a>
<a href="../../articles/assets/poc/poc_cold_chain_excursion/01_scene_slices.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_cold_chain_excursion.jpg" alt="Kühlkette" width="200" height="200"><span>Kühlkette</span></a>
<a href="../../articles/assets/poc/poc_crack_width_timeseries/11_series_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_crack_width_timeseries.jpg" alt="Risswachstum" width="200" height="200"><b>&#9654;</b><span>Risswachstum</span></a>
<a href="../../articles/assets/poc/poc_motion_magnification/05_magnify_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_motion_magnification.jpg" alt="Bewegungsverstärkung" width="200" height="200"><b>&#9654;</b><span>Bewegungsverstärkung</span></a>
<a href="../../articles/assets/poc/poc_particle_tracking/05_tracking_links.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_particle_tracking.jpg" alt="Partikelverfolgung" width="200" height="200"><b>&#9654;</b><span>Partikelverfolgung</span></a>
<a href="../../articles/assets/poc/poc_settlement_significance/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_settlement_significance.jpg" alt="Setzungsprüfung" width="200" height="200"><span>Setzungsprüfung</span></a>
<a href="../../articles/assets/poc/poc_template_tracking/05_twin_vs_flat_occluder.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_template_tracking.jpg" alt="Template-Tracking" width="200" height="200"><b>&#9654;</b><span>Template-Tracking</span></a>
<a href="../../articles/assets/poc/poc_timelapse_growth/05_growth_merge.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_timelapse_growth.jpg" alt="Wachstums-Zeitraffer" width="200" height="200"><b>&#9654;</b><span>Wachstums-Zeitraffer</span></a>
<a href="../../articles/assets/poc/poc_traffic_counting/05_counting_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_traffic_counting.jpg" alt="Verkehrszählung" width="200" height="200"><b>&#9654;</b><span>Verkehrszählung</span></a>
<a href="../../articles/assets/poc/poc_warehouse_flow/01_heat_ambiguity.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_warehouse_flow.jpg" alt="Lager-Verweilzeit" width="200" height="200"><span>Lager-Verweilzeit</span></a>
<a href="../../articles/assets/poc/poc_xyt_event_surface/05_arrival_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_xyt_event_surface.jpg" alt="Ankunftszeitfläche" width="200" height="200"><b>&#9654;</b><span>Ankunftszeitfläche</span></a>
<a href="../../articles/assets/poc/poc_video_cube/02_cube_orbit.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_video_cube.jpg" alt="Videowürfel" width="200" height="200"><b>&#9654;</b><span>Videowürfel</span></a>
<a href="../../articles/assets/poc/poc_live4d/01_beating_orbit.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_live4d.jpg" alt="Lebend-3D+t" width="200" height="200"><b>&#9654;</b><span>Lebend-3D+t</span></a>
<a href="../../articles/assets/poc/poc_diabolo_model_and_vision/01_diabolo_throw_axis_from_image.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_diabolo_model_and_vision.jpg" alt="Diabolo" width="200" height="200"><b>&#9654;</b><span>Diabolo</span></a>
<a href="../../articles/assets/poc/poc_swarm_obstacle_from_flow/01_swarmflow_hidden_obstacle_emerges.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_swarm_obstacle_from_flow.jpg" alt="Schwarm-Hindernis" width="200" height="200"><b>&#9654;</b><span>Schwarm-Hindernis</span></a>
<a href="../../articles/assets/poc/poc_ball_bounce/06_rally_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_ball_bounce.jpg" alt="Tischtennis-Tracking" width="200" height="200"><b>&#9654;</b><span>Tischtennis-Tracking</span></a>
<a href="../../articles/assets/poc/poc_kendama/05_catch_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_kendama.jpg" alt="Kendama" width="200" height="200"><b>&#9654;</b><span>Kendama</span></a>
<a href="../../articles/assets/poc/poc_table_tennis_spin/01_side_three_serves.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_table_tennis_spin.jpg" alt="Tischtennis-Spin" width="200" height="200"><b>&#9654;</b><span>Tischtennis-Spin</span></a>
<a href="../../articles/assets/poc/poc_table_tennis_bounce/01_drop_test.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_table_tennis_bounce.jpg" alt="Tischtennis-Absprung" width="200" height="200"><b>&#9654;</b><span>Tischtennis-Absprung</span></a>
<a href="../../articles/assets/poc/poc_table_tennis_rally_loop/01_landing_cloud.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_table_tennis_rally_loop.jpg" alt="Ballwechsel" width="200" height="200"><b>&#9654;</b><span>Ballwechsel</span></a>
<a href="../../articles/assets/poc/poc_periodic_video_boundary/02_loop.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_periodic_video_boundary.jpg" alt="Periodisches Video" width="200" height="200"><b>&#9654;</b><span>Periodisches Video</span></a>
</div>
</details>

<details class="vall"><summary><b>Konnektom und Neuronen</b> (19)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_fly_vision/01_fly_vision_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_fly_vision.jpg" alt="Fliegensehen" width="200" height="200"><span>Fliegensehen</span></a>
<a href="../../articles/assets/poc/poc_larval_connectome_reservoir/01_adjacency_binned_connectome_vs_shuffle.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_larval_connectome_reservoir.jpg" alt="Larven-Konnektom" width="200" height="200"><span>Larven-Konnektom</span></a>
<a href="../../articles/assets/poc/poc_malecns_activity_wave/01_activity_wave_connectome_vs_shuffle.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_malecns_activity_wave.jpg" alt="Fliegenhirn-Welle" width="200" height="200"><b>&#9654;</b><span>Fliegenhirn-Welle</span></a>
<a href="../../articles/assets/poc/poc_eye_to_brain/01_eye_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_eye_to_brain.jpg" alt="Auge zum Gehirn" width="200" height="200"><b>&#9654;</b><span>Auge zum Gehirn</span></a>
<a href="../../articles/assets/poc/poc_em_second_opinion/02_suspects_on_the_cube.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_em_second_opinion.jpg" alt="EM-Zweitmeinung" width="200" height="200"><b>&#9654;</b><span>EM-Zweitmeinung</span></a>
<a href="../../articles/assets/poc/poc_connectome_motor_bottleneck/03_activity_flow.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_connectome_motor_bottleneck.jpg" alt="Motorische Quantisierung" width="200" height="200"><b>&#9654;</b><span>Motorische Quantisierung</span></a>
<a href="../../articles/assets/poc/poc_microns_brain_wave/01_brain_wave.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_microns_brain_wave.jpg" alt="MICrONS-Welle" width="200" height="200"><b>&#9654;</b><span>MICrONS-Welle</span></a>
<a href="../../articles/assets/poc/poc_em_branch_territory/02_territory_turning.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_em_branch_territory.jpg" alt="Astterritorien" width="200" height="200"><b>&#9654;</b><span>Astterritorien</span></a>
<a href="../../articles/assets/poc/poc_connectome_lr_symmetry/01_lr_jaccard_closed_form.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_connectome_lr_symmetry.jpg" alt="Wurm-L/R-Symmetrie" width="200" height="200"><span>Wurm-L/R-Symmetrie</span></a>
<a href="../../articles/assets/poc/poc_connectome_across_worms/02_wiring_across_development.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_connectome_across_worms.jpg" alt="Wurm-Vergleich" width="200" height="200"><b>&#9654;</b><span>Wurm-Vergleich</span></a>
<a href="../../articles/assets/poc/poc_connectome_across_decades/01_jaccard_across_decades.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_connectome_across_decades.jpg" alt="Schaltplan im Wandel" width="200" height="200"><span>Schaltplan im Wandel</span></a>
<a href="../../articles/assets/poc/poc_worm_neurites_grow/01_neurite_length_growth.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_worm_neurites_grow.jpg" alt="Neuritenwachstum" width="200" height="200"><span>Neuritenwachstum</span></a>
<a href="../../articles/assets/poc/poc_em_split_merge_score/01_split_vs_merge_by_threshold.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_em_split_merge_score.jpg" alt="EM-Split/Merge" width="200" height="200"><span>EM-Split/Merge</span></a>
<a href="../../articles/assets/poc/poc_em_wiring_errors/01_proofreading_order.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_em_wiring_errors.jpg" alt="Verdrahtungsfehler" width="200" height="200"><span>Verdrahtungsfehler</span></a>
<a href="../../articles/assets/poc/poc_worm_synapses_vs_neurites/01_density_by_stage.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_worm_synapses_vs_neurites.jpg" alt="Synapsen vs. Neuriten" width="200" height="200"><span>Synapsen vs. Neuriten</span></a>
<a href="../../articles/assets/poc/poc_skeleton_run_length_vs_voi/01_merge_size_erl_vs_voi.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_skeleton_run_length_vs_voi.jpg" alt="ERL vs. VOI" width="200" height="200"><span>ERL vs. VOI</span></a>
<a href="../../articles/assets/poc/poc_swc_tree_truth/01_swc_projection.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_swc_tree_truth.jpg" alt="SWC-Skelette" width="200" height="200"><span>SWC-Skelette</span></a>
<a href="../../articles/assets/poc/poc_fly_optomotor_steering/06_follow.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_fly_optomotor_steering.jpg" alt="Fliegensteuerung" width="200" height="200"><b>&#9654;</b><span>Fliegensteuerung</span></a>
<a href="../../articles/assets/poc/poc_worm_core_persists/04_core_map_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_worm_core_persists.jpg" alt="Wurmhirn-Kern" width="200" height="200"><b>&#9654;</b><span>Wurmhirn-Kern</span></a>
</div>
</details>

<details class="vall"><summary><b>Medizin und Biologie</b> (9)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_bone_trabecular_thickness/01_scene_truth.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_bone_trabecular_thickness.jpg" alt="Trabekeldicke" width="200" height="200"><span>Trabekeldicke</span></a>
<a href="../../articles/assets/poc/poc_cell_counting/01_scene_dense.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_cell_counting.jpg" alt="Zellzählung" width="200" height="200"><span>Zellzählung</span></a>
<a href="../../articles/assets/poc/poc_colocalization_crosstalk/01_scene_channels.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_colocalization_crosstalk.jpg" alt="Kolokalisation" width="200" height="200"><span>Kolokalisation</span></a>
<a href="../../articles/assets/poc/poc_mri_bias_field/01_controls.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_mri_bias_field.jpg" alt="MRI-Biasfeld" width="200" height="200"><span>MRI-Biasfeld</span></a>
<a href="../../articles/assets/poc/poc_nuclei_ploidy/01_histograms.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_nuclei_ploidy.jpg" alt="Kernploidie" width="200" height="200"><span>Kernploidie</span></a>
<a href="../../articles/assets/poc/poc_vessel_network/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_vessel_network.jpg" alt="Gefäßnetz" width="200" height="200"><span>Gefäßnetz</span></a>
<a href="../../articles/assets/poc/poc_wound_area_tracking/06_healing_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_wound_area_tracking.jpg" alt="Wundfläche" width="200" height="200"><b>&#9654;</b><span>Wundfläche</span></a>
<a href="../../articles/assets/poc/poc_physarum_maze/02_maze_tubes_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_physarum_maze.jpg" alt="Schleimpilz-Labyrinth" width="200" height="200"><b>&#9654;</b><span>Schleimpilz-Labyrinth</span></a>
<a href="../../articles/assets/poc/poc_physarum_transport/01_transport_tubes_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_physarum_transport.jpg" alt="Schleimpilz-Transport" width="200" height="200"><b>&#9654;</b><span>Schleimpilz-Transport</span></a>
</div>
</details>

<details class="vall"><summary><b>Astronomie und Umwelt</b> (21)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_allsky_cloud_cover/01_jacobian.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_allsky_cloud_cover.jpg" alt="Bewölkung Allsky" width="200" height="200"><span>Bewölkung Allsky</span></a>
<a href="../../articles/assets/poc/poc_astro_photometry/01_stack_scaling.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_astro_photometry.jpg" alt="Sternphotometrie" width="200" height="200"><span>Sternphotometrie</span></a>
<a href="../../articles/assets/poc/poc_change_detection_misreg/01_plot_fp_vs_shift.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_change_detection_misreg.jpg" alt="Änderungserkennung" width="200" height="200"><span>Änderungserkennung</span></a>
<a href="../../articles/assets/poc/poc_datacenter_thermal_field/01_scene_truth.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_datacenter_thermal_field.jpg" alt="3-D-Wärmefeld" width="200" height="200"><span>3-D-Wärmefeld</span></a>
<a href="../../articles/assets/poc/poc_dem_terrain/05_terrain_flight.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dem_terrain.jpg" alt="Geländemessung" width="200" height="200"><b>&#9654;</b><span>Geländemessung</span></a>
<a href="../../articles/assets/poc/poc_exoplanet_transit/01_scene_starfield.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_exoplanet_transit.jpg" alt="Exoplanetentransit" width="200" height="200"><span>Exoplanetentransit</span></a>
<a href="../../articles/assets/poc/poc_geodetic_height_frames/01_geoid_frames.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_geodetic_height_frames.jpg" alt="Höhenbezüge" width="200" height="200"><span>Höhenbezüge</span></a>
<a href="../../articles/assets/poc/poc_leaf_disease_area/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_leaf_disease_area.jpg" alt="Blattkrankheit" width="200" height="200"><span>Blattkrankheit</span></a>
<a href="../../articles/assets/poc/poc_pv_thermal_survey/01_norm_table.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_pv_thermal_survey.jpg" alt="PV-Thermografie" width="200" height="200"><span>PV-Thermografie</span></a>
<a href="../../articles/assets/poc/poc_real_sky_photometry/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_sky_photometry.jpg" alt="Echter Sternhimmel" width="200" height="200"><span>Echter Sternhimmel</span></a>
<a href="../../articles/assets/poc/poc_river_surface_velocity/13_accumulate_pairs.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_river_surface_velocity.jpg" alt="Flussgeschwindigkeit" width="200" height="200"><b>&#9654;</b><span>Flussgeschwindigkeit</span></a>
<a href="../../articles/assets/poc/poc_sea_ice_concentration/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_sea_ice_concentration.jpg" alt="Meereisbedeckung" width="200" height="200"><span>Meereisbedeckung</span></a>
<a href="../../articles/assets/poc/poc_search_sweep_width/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_search_sweep_width.jpg" alt="Suchbreite" width="200" height="200"><span>Suchbreite</span></a>
<a href="../../articles/assets/poc/poc_solar_limb_darkening/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_solar_limb_darkening.jpg" alt="Randverdunkelung" width="200" height="200"><span>Randverdunkelung</span></a>
<a href="../../articles/assets/poc/poc_star_astrometry/01_snr_sweep.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_star_astrometry.jpg" alt="Sternastrometrie" width="200" height="200"><span>Sternastrometrie</span></a>
<a href="../../articles/assets/poc/poc_tree_ring_dendro/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_tree_ring_dendro.jpg" alt="Jahresringe" width="200" height="200"><span>Jahresringe</span></a>
<a href="../../articles/assets/poc/poc_vegetation_cover/01_mixed_pixel_response.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_vegetation_cover.jpg" alt="Vegetationsbedeckung" width="200" height="200"><span>Vegetationsbedeckung</span></a>
<a href="../../articles/assets/poc/poc_water_level/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_water_level.jpg" alt="Pegelstand" width="200" height="200"><span>Pegelstand</span></a>
<a href="../../articles/assets/poc/poc_rover_slip_risk_path/03_rover_slip_update.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_rover_slip_risk_path.jpg" alt="Mars-Rover-Schlupf" width="200" height="200"><b>&#9654;</b><span>Mars-Rover-Schlupf</span></a>
<a href="../../articles/assets/poc/poc_geodetic_benchmarks_real/01_residual_sorted.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_geodetic_benchmarks_real.jpg" alt="Zwei Höhen (echt)" width="200" height="200"><span>Zwei Höhen (echt)</span></a>
<a href="../../articles/assets/poc/poc_gravitational_lens_invariants/10_source_crossing.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_gravitational_lens_invariants.jpg" alt="Gravitationslinse" width="200" height="200"><b>&#9654;</b><span>Gravitationslinse</span></a>
</div>
</details>

<details class="vall"><summary><b>Forensik und Dokumente</b> (4)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_document_scan/01_rectify_zero_points.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_document_scan.jpg" alt="Dokumentscan" width="200" height="200"><span>Dokumentscan</span></a>
<a href="../../articles/assets/poc/poc_forensics_roc/01_score_maps.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_forensics_roc.jpg" alt="Fälschungs-ROC" width="200" height="200"><span>Fälschungs-ROC</span></a>
<a href="../../articles/assets/poc/poc_fresco_craquelure/01_ridge_ops.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_fresco_craquelure.jpg" alt="Krakelee" width="200" height="200"><span>Krakelee</span></a>
<a href="../../articles/assets/poc/poc_prnu_camera_fingerprint/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_prnu_camera_fingerprint.jpg" alt="Kamera-Fingerabdruck" width="200" height="200"><span>Kamera-Fingerabdruck</span></a>
</div>
</details>

<details class="vall"><summary><b>Autonomes Fahren</b> (13)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_car_parking/04_parking_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_car_parking.jpg" alt="Einparken" width="200" height="200"><b>&#9654;</b><span>Einparken</span></a>
<a href="../../articles/assets/poc/poc_driving_school/05_drive_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_school.jpg" alt="Fahrschule" width="200" height="200"><b>&#9654;</b><span>Fahrschule</span></a>
<a href="../../articles/assets/poc/poc_ttc_rss/06_approach_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_ttc_rss.jpg" alt="TTC und RSS" width="200" height="200"><b>&#9654;</b><span>TTC und RSS</span></a>
<a href="../../articles/assets/poc/poc_world_terrain/06_drive_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_world_terrain.jpg" alt="Welt erweitern" width="200" height="200"><b>&#9654;</b><span>Welt erweitern</span></a>
<a href="../../articles/assets/poc/poc_driving_longitudinal/01_drive_with_time.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_longitudinal.jpg" alt="Trägheit und Steigung" width="200" height="200"><b>&#9654;</b><span>Trägheit und Steigung</span></a>
<a href="../../articles/assets/poc/poc_driving_weather/01_sun_day.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_weather.jpg" alt="Sonne und Wetter" width="200" height="200"><b>&#9654;</b><span>Sonne und Wetter</span></a>
<a href="../../articles/assets/poc/poc_driving_endless_map/01_minimap_stream.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_endless_map.jpg" alt="Endlose Karte" width="200" height="200"><b>&#9654;</b><span>Endlose Karte</span></a>
<a href="../../articles/assets/poc/poc_driving_traffic/01_dashcam_occlusion.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_traffic.jpg" alt="Verkehr, toter Winkel" width="200" height="200"><b>&#9654;</b><span>Verkehr, toter Winkel</span></a>
<a href="../../articles/assets/poc/poc_driving_decisions/01_decisions_mirrors_ambulance.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_decisions.jpg" alt="Entscheidungsszenen" width="200" height="200"><b>&#9654;</b><span>Entscheidungsszenen</span></a>
<a href="../../articles/assets/poc/poc_driving_lateral/01_lateral_dashcam.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_lateral.jpg" alt="Querbewegung" width="200" height="200"><b>&#9654;</b><span>Querbewegung</span></a>
<a href="../../articles/assets/poc/poc_driving_humanoids/03_humanoids_crossing.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_humanoids.jpg" alt="Humanoiden am Zebrastreifen" width="200" height="200"><b>&#9654;</b><span>Humanoiden am Zebrastreifen</span></a>
<a href="../../articles/assets/poc/poc_driving_crossing/01_crossing_dashcam.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_crossing.jpg" alt="Bahnübergänge" width="200" height="200"><b>&#9654;</b><span>Bahnübergänge</span></a>
<a href="../../articles/assets/poc/poc_driving_pass/01_overtake_dashcam.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_pass.jpg" alt="Überholen" width="200" height="200"><b>&#9654;</b><span>Überholen</span></a>
</div>
</details>

<details class="vall"><summary><b>Mathematische Bilder</b> (7)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_one_stroke_epicycles/07_epicycles.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_one_stroke_epicycles.jpg" alt="Epizykel-Zeichnung" width="200" height="200"><b>&#9654;</b><span>Epizykel-Zeichnung</span></a>
<a href="../../articles/assets/poc/poc_complex_plane_fields/01_rational.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_complex_plane_fields.jpg" alt="Komplexe Ebene" width="200" height="200"><span>Komplexe Ebene</span></a>
<a href="../../articles/assets/poc/poc_theorems_as_pictures/01_apollonian.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_theorems_as_pictures.jpg" alt="Sätze als Gates" width="200" height="200"><span>Sätze als Gates</span></a>
<a href="../../articles/assets/poc/poc_beats_fringes_and_screens/01_membrane.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_beats_fringes_and_screens.jpg" alt="Eine Schwebung" width="200" height="200"><span>Eine Schwebung</span></a>
<a href="../../articles/assets/poc/poc_what_a_picture_cannot_check/01_rk4.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_what_a_picture_cannot_check.jpg" alt="Jenseits des Bildes" width="200" height="200"><span>Jenseits des Bildes</span></a>
<a href="../../articles/assets/poc/poc_illusions_and_perpetual_drawing/14_loop.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_illusions_and_perpetual_drawing.jpg" alt="Endloses Zeichnen" width="200" height="200"><b>&#9654;</b><span>Endloses Zeichnen</span></a>
<a href="../../articles/assets/poc/poc_calipers_under_illusion/01_caliper_on_cafe_wall.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_calipers_under_illusion.jpg" alt="Messschieber-Illusion" width="200" height="200"><span>Messschieber-Illusion</span></a>
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

## Was zu sehen ist, und die gemessene Zahl

Jede Zahl ist gegen eine Ground Truth gemessen, die der PoC selbst eingesetzt hat (geschlossene Form, analytische Lösung oder veröffentlichter Wert); der PoC gibt beim Ausführen denselben Wert aus.

<div class="vl" markdown="1">

**Bildprüfung und Oberfläche**

- [Schwache Defekte](../../articles/assets/poc/poc_real_defect_floor/02_defect_floor_sweep.gif) (GIF): Derselbe eingesetzte Defekt wird auf einer echten Ziegeltextur und auf einem synthetischen Hintergrund mit gleichem Rauschen stärker. **Selbst bei gleichem Rauschen liegt die Nachweisgrenze auf echten Texturen beim 2.03- bis 3.47-Fachen der synthetischen (Defekte mit bekannter Position und Amplitude).** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_defect_floor.py)
- [Aktive Konturen](../../articles/assets/poc/poc_active_contours/06_u_shape_snakes.mp4) (Video): Die klassische Snake (rot) überbrückt die U-Kerbe, GVF (blau) erreicht den Grund. Grün ist die wahre Kante. **Nur die äußere Kraft auf GVF umgestellt: Dice 0.993 gegenüber der wahren Kante.** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_active_contours.py)
- [DIC-Dehnung](../../articles/assets/poc/poc_dic_strain/05_tensile_ramp.mp4) (Video): Dehnungskarten aus Speckle-Bildern, während die Zuglast steigt (die Maschine dreht sich zugleich um 2 Grad). **Wahre Dehnung 3000 µε. Die kleine Dehnung liest wegen der Drehung nur 2341 µε, Green-Lagrange 2961 µε (Theorie 3005 µε).** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dic_strain.py)

**3-D-Messung und Geometrie**

- [Fokus-Stacking](../../articles/assets/poc/poc_focus_stacking/05_focus_sweep.mp4) (Video): Beim Fokusdurchlauf über 17 Frames entstehen das durchgehend scharfe Bild und die Tiefenkarte. **Scharfes Gesamtbild PSNR 33.69 dB (das 1 mittlere Einzelbild 28.52 dB), Tiefenfehler 0.467 mm (texturierte Bereiche).** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_focus_stacking.py)
- [Punktwolken-ICP](../../articles/assets/poc/poc_registration_basin/05_icp_basin_iterations.mp4) (Video): ICP, je 1 Iteration pro Schritt, ab anfänglichen Drehfehlern von 30, 90 und 150 Grad. **Drehfehler nach 60 Iterationen: 0.6 Grad ab 30 und 90 (Erfolg), 179.5 Grad ab 150 (Fehlschlag).** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_registration_basin.py)
- [Haldenvolumen](../../articles/assets/poc/poc_stockpile_volume/07_scan_orbit.mp4) (Video): Umlauf um eine Halde, die 3-D-Scanpositionen steigen von 1 auf 3; Farbe = interpolierte minus wahre Oberfläche. **Volumenfehler +17.20 % -> +0.05 % (wahre Basis; Sollvolumen in geschlossener Form 3572.6089 m³).** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_stockpile_volume.py)

**Röntgen-CT und Volumen**

- [CT-Rekonstruktion](../../articles/assets/poc/poc_ct_fidelity/01_recon_sweep.png) (Abbildung): Das Shepp-Logan-Phantom wird mit 180 bis hinab zu 12 Projektionen aufgenommen und rekonstruiert. **FBP mit 12 Projektionen (RMSE 0.2576) unterliegt sogar einem leeren Bild (0.2420). Eine Massenprüfung fand -3.34 % Verlust, korrigiert auf -0.0099 %.** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_fidelity.py)
- [CT-Poren](../../articles/assets/poc/poc_ct_void_morphology/13_section_sweep.mp4) (Video): 2 Fügeschichten mit fast gleichem Porenanteil: Schnittdurchlauf mit rotierenden 3-D-Poren (Video 4.3 MB). **Porenanteil 2.46 % zu 2.63 %, aber der Median des Abstands zur Grenzfläche beträgt 60.0 µm zu 10.0 µm.** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_void_morphology.py)

**Optik, Interferometrie, Polarisation**

- [Weißlicht-Stufen](../../articles/assets/poc/poc_interferometry_step/05_step_sweep.mp4) (Video): Die eingesetzte Stufe wächst von 0 auf 0.90 µm, gemessen über die Kohärenz-Einhüllende und per Phasenschieben. **Bias unter 2.4 nm bei 1 % Rauschen (Stufen 50-500 nm). Phasenschieben springt bei 0.153 µm um λ/2.** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_interferometry_step.py)
- [Polarisation](../../articles/assets/poc/poc_polarization_specular/03_separation.png) (Abbildung): Mit Polarisation entfernte Spiegelreflexion und die Form des Restfehlers. **Der Fehler des diffusen Anteils folgt der geschlossenen Form R_p·E und ist beim Brewster-Winkel 56.31 Grad gleich 0.** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_polarization_specular.py)
- [Spannungsoptik](../../articles/assets/poc/poc_photoelasticity/03_load_and_isoclinics.mp4) (Video): Unter Last quellen Streifen aus der Scheibe; drehen der Polarisatoren verschiebt die Isoklinen. **Streifenordnung in der Mitte 2.38, wie die geschlossene Form sagt. Das Polariskop des op stimmt mit dem Lehrbuch auf 2.2e-16 überein.** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_photoelasticity.py)

**Wärme, Akustik, Zeitreihen**

- [Thermografie](../../articles/assets/poc/poc_thermography_ndt/02_depth_map.png) (Abbildung): Tiefenkarte von 16 Delaminationen aus der Oberflächentemperatur nach einem Blitz. **Ein 0.5 mm tiefer, 2 mm breiter Defekt: +612 % mit 25 s Anpassungsfenster, -9 % mit 4 s.** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_thermography_ndt.py)
- [Bewegungsverstärkung](../../articles/assets/poc/poc_motion_magnification/05_magnify_video.mp4) (Video): Eine Oberfläche schwingt um 0.1 px: links das Rohvideo, rechts 10-fach verstärkt. **Wahre Amplitude 0.1000 px; gemessen roh 0.10012, nach Verstärkung 0.10013 px. Sie hilft dem Auge, nicht der Messung.** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_motion_magnification.py)

**Robotik und räumliche Wahrnehmung**

- [Facettenauge](../../articles/assets/poc/poc_compound_eye/02_compound_eye_superposition.png) (Abbildung): Ein Facettenaugen-Array als Lichtfeldsensor simuliert; derselbe Punkt wird aus N Ommatidien überlagert. Der nächste Schritt: dieses Lichtfeld mit dem Schaltplan der Fliege (Konnektom) verarbeiten; siehe die Konnektom-Exponate unten. **SNR-Gewinn 2.25 bei N=5 (√5 = 2.24) und 5.33 bei N=49 (√49 = 7.00).** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_compound_eye.py)
- [Peg-in-Hole](../../articles/assets/poc/poc_pegsim_insertion/04_pegsim_insert_corrected.gif) (GIF): Eine Handgelenkkamera misst das Loch, der Arm fährt darüber, ein nachgiebiges Handgelenk setzt den Stift ein (MuJoCo). **7 Servoschritte verringern den wahren Versatz von 2.24 auf 0.03 mm; korrigiertes Einsetzen gelingt 12 / 12.** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pegsim_insertion.py)
- [Airhockey](../../articles/assets/poc/poc_air_hockey_intercept/02_airhockey_prediction_cone_narrows.gif) (GIF): Ein Puck wird mit einer groben Kamera verfolgt und sein Schnittpunkt mit der Abwehrlinie vorhergesagt; mit mehr Frames wird das Band schmaler. **Das 95-%-Band des Schnittpunkts schrumpft von 145 mm bei N = 3 Frames auf 7 mm bei N = 16.** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_air_hockey_intercept.py)
- [Taktiler Sensor](../../articles/assets/poc/poc_tacsim_elastic_membrane/03_tacsim_force_sweep.gif) (GIF): Eine Kugel drückt stärker auf eine elastische Membran; der Kontaktradius wird aus dem Membranbild gelesen. **Gegenüber der geschlossenen Hertz-Form: Kontaktradius 0.05-0.26 %, Kraft 0.14-0.79 % (0.02-0.12 N).** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_tacsim_elastic_membrane.py)

**Tischtennis und Bewegung**

- [Tischtennis-Absprung](../../articles/assets/poc/poc_table_tennis_bounce/01_drop_test.mp4) (Video): ITTF-Tischtest: Ball aus 30 cm fallen lassen und die Sprunghöhe aus dem Video lesen. **Aus dem Video gelesene Sprunghöhe 23.0 cm (Ground Truth 23.0 cm).** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_table_tennis_bounce.py)
- [Tischtennis-Spin](../../articles/assets/poc/poc_table_tennis_spin/01_side_three_serves.mp4) (Video): 3 gleich geschlagene Bälle: Topspin taucht ab, Unterschnitt schwebt. **Aufprall bei x = 0.49 / 0.75 / 1.12 m. Aus der Kurve gelesener Spin sagt den Aufprall aller 4 Bälle auf 2 cm genau voraus.** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_table_tennis_spin.py)
- [Ballwechsel](../../articles/assets/poc/poc_table_tennis_rally_loop/02_height_misread.mp4) (Video): Wird der Ball 5 cm zu hoch gelesen, wählt die Planung eine flachere Bahn und der Ball landet zu kurz. **Er landet 10.2 cm zu kurz; die Vorhersage erster Ordnung vor dem Schlag: 2.06 × 5 cm = 10.3 cm.** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_table_tennis_rally_loop.py)

**Autonomes Fahren**

- [Verkehr, toter Winkel](../../articles/assets/poc/poc_driving_traffic/01_dashcam_occlusion.mp4) (Video): Ein Kind läuft hinter einem parkenden Auto hervor; erkannt per Hintergrunddifferenz (ohne Lernen), das Auto hält. **Erkannt bei t = 7.30 s (0.133 s Verzögerung), Halt 7.09 m vor dem Weg des Kindes.** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_driving_traffic.py)
- [Bahnübergänge](../../articles/assets/poc/poc_driving_crossing/01_crossing_dashcam.mp4) (Video): Vor dem Bahnübergang halten, den Alarm abwarten, nach beiden Seiten sehen, queren (Fahrersicht). **240 regeltreue Fahrer: 0 Verstöße, 0 auf dem Gleis bei Zugankunft. Einfahren während des Alarms: 157 Verstöße, 23 davon auf dem Gleis.** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_driving_crossing.py)
- [Verkehrsspiegel](../../articles/assets/poc/poc_driving_pass/03_mirror_tjunction.mp4) (Video): An einer unübersichtlichen T-Kreuzung wird ein Auto im konvexen Spiegel per Raytracing gezeichnet und seine Entfernung gelesen. **Ein Auto 29 m vor dem Spiegel wirkt nach Bildgröße 139 m entfernt (geschlossene Form, vertikal: 140 m).** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_driving_pass.py)
- [TTC und RSS](../../articles/assets/poc/poc_ttc_rss/06_approach_gif.gif) (GIF): Zeit bis zur Kollision τ aus dem optischen Fluss eines Gegenfahrzeugs; vor einem stehenden Auto Bremsen nach RSS-Sicherheitsabstand. **Bremsen, als RSS bei t = 6.0 s Gefahr meldet; Halt 10.25 m davor.** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ttc_rss.py)

**Konnektom und Neuronen**

- [Auge zum Gehirn](../../articles/assets/poc/poc_eye_to_brain/01_eye_sweep.gif) (GIF): Ein Reiz von 1 Ommatidium wandert eine Reihe des rechten Fliegenauges entlang und speist den Schaltplan des Gehirns (Konnektom) (GIF 4.4 MB). **Korrelation von gereizter Säule und Antwortschwerpunkt: Konnektom -0.92, gradtreu gemischt +0.01.** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_eye_to_brain.py)
- [Fliegenhirn-Welle](../../articles/assets/poc/poc_malecns_activity_wave/01_activity_wave_connectome_vs_shuffle.gif) (GIF): Ein Reiz im rechten optischen Lobus läuft durch die echte Verdrahtung (links) und durch gradtreu neu verdrahtete (rechts). **In der echten Verdrahtung wächst der mittlere Abstand der Aktivität in 17 Schritten von 88 auf 230 µm; neu verdrahtet streut er in 3 Schritten auf 300 µm.** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_malecns_activity_wave.py)
- [Mauskortex-Welle](../../articles/assets/poc/poc_microns_brain_wave/04_wave_on_wiring.gif) (GIF): Gemessene Antworten von 148 geprüften Axonen, eingespeist in die echte Verdrahtung von 1 mm³ Mäuse-Sehrinde (MICrONS). **Korrelation mit der Messung: echte Verdrahtung 0.085, gradtreu gemischt 0.048.** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_microns_brain_wave.py)

**Roboteraugen (Fullseye übernimmt die Wahrnehmung)**

- [Stereoaugen](../../articles/assets/media/evis_stereo_fullseye.mp4) (Video): Ein Muskel-Skelett-Humanoid schlägt mit Stäbchen eine Bohne, gefilmt mit den eigenen Augen (64 mm Abstand); Fullseye berechnet je Frame Stereo-Disparität -> Tiefe. **Fehler der Bohnenentfernung: Median 0.66 %, max. 1.91 % (229 / 241 Frames lesbar).** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/tools/gen_evis_media.py)
- [Stäbchenkamera-Tracking](../../articles/assets/media/evis_bean_track_fullseye.mp4) (Video): Im Video der Stäbchenspitzen-Kamera derselben Szene erkennt und verfolgt Fullseye die Bohne. **In allen 163 sichtbaren Frames erkannt (163 / 163); Schwerpunktfehler gegenüber der Wahrheit im Median 0.10 px.** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/tools/gen_evis_media.py)

</div>

## Was Fullseye ist

Eine Plattform, die Physiksimulation (einschließlich Sensorik wie Optikdesign und 3-D-Messung) und klassische Bildverarbeitung über MCP und RAG an eine KI übergibt, sie für jede Aufgabe eine Kombination ausarbeiten lässt und die Aufgabe interaktiv löst, geprüft durch Typkonsistenz und Bewertung gegen Ground Truth. Open Source (Apache-2.0).

<details markdown="1">
<summary><b>Ausprobieren</b> (Python 3.11)</summary>

```
pip install fullseye
git clone https://github.com/furuse-kazufumi/fullseye
cd fullseye
python examples/poc_focus_stacking.py
```

Der Fokus-Stacking-PoC läuft etwa 20 Sekunden und gibt seine Zahlen gegen Ground Truth sowie `PASS` aus. Abbildungen landen in `out/figures/poc_focus_stacking/`.

</details>

<details markdown="1">
<summary><b>Links</b></summary>

- [GitHub (Quellcode)](https://github.com/furuse-kazufumi/fullseye)
- [Galerie (alle Abbildungen)](../../GALLERY.en.md)
- [Operatoren finden / aus einer KI nutzen (RAG)](../../AI_RAG_GUIDE.de.md) · [Über MCP nutzen](../../MCP.md) _(ja)_
- [Dokumentationsindex](../../README.de.md)

</details>

<details markdown="1">
<summary><b>Paper</b></summary>

- **Titel**: Fullseye：型付き演算子と物理シミュレーションに基づく画像検査・三次元計測基盤 _(ja)_ (eine Plattform für Bildprüfung und 3-D-Messung auf Basis typisierter Operatoren und Physiksimulation)
- **Autor**: Kazufumi Furuse (unabhängiger Forscher)
- **Veranstaltung**: ViEW2026, Workshop zur praktischen Anwendung von Bildverarbeitung
- **Paper-PDF**: ab 2026-11-26 verfügbar

**Zusammenfassung (aus dem Japanischen übersetzt)**: Wir stellen Fullseye vor, eine Open-Source-Plattform, die Verarbeitungen für Bildprüfung und 3-D-Messung als Ketten von Operatoren mit deklarierten Ein- und Ausgabedatentypen aufbaut, sie quantitativ gegen eine durch Physik- und Abbildungssimulation erzeugte Ground Truth bewertet und Ablauf, Bewertung und Fehlerbedingungen zur Wiederverwendung festhält. Sie besteht aus rund 3,000 typisierten Operatoren, einer Prüfung, die Typfehler vor der Ausführung ablehnt, einer mehrsprachigen Operatorsuche (RAG) und über 200 Machbarkeitsprogrammen mit Ground Truth. Berichtet werden die quantitative Bewertung repräsentativer Beispiele und die Unterscheidung zwischen synthetischer, gemessener und Hardware-Validierung.

</details>
