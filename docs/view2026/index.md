<div class="vlang" markdown="1">

**日本語** · [English](en/index.md) · [简体中文](zh/index.md) · [繁體中文](tw/index.md) · [한국어](ko/index.md) · [Deutsch](de/index.md) · [हिन्दी](hi/index.md)

</div>

# Fullseye — ViEW2026

物理シミュレーションと画像処理を AI と組み合わせて、真値で確かめる。

タイルを押すと動画・図が開きます(▶ = 動く)。

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

<script>
(function () {
  try {
    var k = "fullseye_view2026_lang";
    if (localStorage.getItem(k)) return;
    localStorage.setItem(k, "seen");
    if (document.referrer && document.referrer.indexOf(location.host) >= 0) return;
    var n = (navigator.language || "").toLowerCase(), t = "";
    if (n.indexOf("zh") === 0) t = /tw|hk|mo|hant/.test(n) ? "tw" : "zh";
    else if (/^(en|ko|de|hi)/.test(n)) t = n.slice(0, 2);
    if (t) location.replace(t + "/");
  } catch (e) {}
})();
</script>

## 見どころ

<div class="vg">
<a href="../articles/assets/poc/poc_real_defect_floor/02_defect_floor_sweep.gif"><img src="thumbs/poc_real_defect_floor.jpg" alt="薄い傷の検出限界" loading="lazy" width="320" height="320"><b>&#9654;</b><span>薄い傷の検出限界</span></a>
<a href="../articles/assets/poc/poc_active_contours/06_u_shape_snakes.mp4"><img src="thumbs/poc_active_contours.jpg" alt="動的輪郭" loading="lazy" width="320" height="320"><b>&#9654;</b><span>動的輪郭</span></a>
<a href="../articles/assets/poc/poc_dic_strain/05_tensile_ramp.mp4"><img src="thumbs/poc_dic_strain.jpg" alt="DIC ひずみ" loading="lazy" width="320" height="320"><b>&#9654;</b><span>DIC ひずみ</span></a>
<a href="../articles/assets/poc/poc_focus_stacking/05_focus_sweep.mp4"><img src="thumbs/poc_focus_stacking.jpg" alt="焦点合成" loading="lazy" width="320" height="320"><b>&#9654;</b><span>焦点合成</span></a>
<a href="../articles/assets/poc/poc_registration_basin/05_icp_basin_iterations.mp4"><img src="thumbs/poc_registration_basin.jpg" alt="点群の位置合わせ" loading="lazy" width="320" height="320"><b>&#9654;</b><span>点群の位置合わせ</span></a>
<a href="../articles/assets/poc/poc_stockpile_volume/07_scan_orbit.mp4"><img src="thumbs/poc_stockpile_volume.jpg" alt="堆積物の体積" loading="lazy" width="320" height="320"><b>&#9654;</b><span>堆積物の体積</span></a>
<a href="../articles/assets/poc/poc_ct_fidelity/01_recon_sweep.png"><img src="thumbs/poc_ct_fidelity.jpg" alt="CT 再構成" loading="lazy" width="320" height="320"><span>CT 再構成</span></a>
<a href="../articles/assets/poc/poc_ct_void_morphology/13_section_sweep.mp4"><img src="thumbs/poc_ct_void_morphology.jpg" alt="CT のボイド" loading="lazy" width="320" height="320"><b>&#9654;</b><span>CT のボイド</span></a>
<a href="../articles/assets/poc/poc_interferometry_step/05_step_sweep.mp4"><img src="thumbs/poc_interferometry_step.jpg" alt="白色干渉の段差" loading="lazy" width="320" height="320"><b>&#9654;</b><span>白色干渉の段差</span></a>
<a href="../articles/assets/poc/poc_polarization_specular/03_separation.png"><img src="thumbs/poc_polarization_specular.jpg" alt="偏光で鏡面除去" loading="lazy" width="320" height="320"><span>偏光で鏡面除去</span></a>
<a href="../articles/assets/poc/poc_photoelasticity/03_load_and_isoclinics.mp4"><img src="thumbs/poc_photoelasticity.jpg" alt="光弾性の応力" loading="lazy" width="320" height="320"><b>&#9654;</b><span>光弾性の応力</span></a>
<a href="../articles/assets/poc/poc_thermography_ndt/02_depth_map.png"><img src="thumbs/poc_thermography_ndt.jpg" alt="熱画像の欠陥深さ" loading="lazy" width="320" height="320"><span>熱画像の欠陥深さ</span></a>
<a href="../articles/assets/poc/poc_motion_magnification/05_magnify_video.mp4"><img src="thumbs/poc_motion_magnification.jpg" alt="微小振動の拡大" loading="lazy" width="320" height="320"><b>&#9654;</b><span>微小振動の拡大</span></a>
<a href="../articles/assets/poc/poc_table_tennis_bounce/01_drop_test.mp4"><img src="thumbs/poc_table_tennis_bounce.jpg" alt="卓球の跳ね" loading="lazy" width="320" height="320"><b>&#9654;</b><span>卓球の跳ね</span></a>
<a href="../articles/assets/poc/poc_compound_eye/02_compound_eye_superposition.png"><img src="thumbs/poc_compound_eye.jpg" alt="複眼の光場" loading="lazy" width="320" height="320"><span>複眼の光場</span></a>
<a href="../articles/assets/poc/poc_pegsim_insertion/04_pegsim_insert_corrected.gif"><img src="thumbs/poc_pegsim_insertion.jpg" alt="ペグ挿入" loading="lazy" width="320" height="320"><b>&#9654;</b><span>ペグ挿入</span></a>
<a href="../articles/assets/poc/poc_air_hockey_intercept/02_airhockey_prediction_cone_narrows.gif"><img src="thumbs/poc_air_hockey_intercept.jpg" alt="エアホッケー" loading="lazy" width="320" height="320"><b>&#9654;</b><span>エアホッケー</span></a>
<a href="../articles/assets/poc/poc_tacsim_elastic_membrane/03_tacsim_force_sweep.gif"><img src="thumbs/poc_tacsim_elastic_membrane.jpg" alt="視触覚センサ" loading="lazy" width="320" height="320"><b>&#9654;</b><span>視触覚センサ</span></a>
<a href="../articles/assets/poc/poc_table_tennis_spin/01_side_three_serves.mp4"><img src="thumbs/poc_table_tennis_spin.jpg" alt="卓球の回転" loading="lazy" width="320" height="320"><b>&#9654;</b><span>卓球の回転</span></a>
<a href="../articles/assets/poc/poc_table_tennis_rally_loop/02_height_misread.mp4"><img src="thumbs/poc_table_tennis_rally_loop.jpg" alt="ラリーと読み誤差" loading="lazy" width="320" height="320"><b>&#9654;</b><span>ラリーと読み誤差</span></a>
<a href="../articles/assets/poc/poc_driving_traffic/01_dashcam_occlusion.mp4"><img src="thumbs/poc_driving_traffic.jpg" alt="交通と死角" loading="lazy" width="320" height="320"><b>&#9654;</b><span>交通と死角</span></a>
<a href="../articles/assets/poc/poc_driving_crossing/01_crossing_dashcam.mp4"><img src="thumbs/poc_driving_crossing.jpg" alt="踏切と交差点" loading="lazy" width="320" height="320"><b>&#9654;</b><span>踏切と交差点</span></a>
<a href="../articles/assets/poc/poc_driving_pass/03_mirror_tjunction.mp4"><img src="thumbs/poc_driving_pass.jpg" alt="カーブミラー" loading="lazy" width="320" height="320"><b>&#9654;</b><span>カーブミラー</span></a>
<a href="../articles/assets/poc/poc_ttc_rss/06_approach_gif.gif"><img src="thumbs/poc_ttc_rss.jpg" alt="衝突時間と RSS" loading="lazy" width="320" height="320"><b>&#9654;</b><span>衝突時間と RSS</span></a>
<a href="../articles/assets/poc/poc_eye_to_brain/01_eye_sweep.gif"><img src="thumbs/poc_eye_to_brain.jpg" alt="複眼から脳へ" loading="lazy" width="320" height="320"><b>&#9654;</b><span>複眼から脳へ</span></a>
<a href="../articles/assets/poc/poc_malecns_activity_wave/01_activity_wave_connectome_vs_shuffle.gif"><img src="thumbs/poc_malecns_activity_wave.jpg" alt="ハエの脳の波" loading="lazy" width="320" height="320"><b>&#9654;</b><span>ハエの脳の波</span></a>
<a href="../articles/assets/poc/poc_microns_brain_wave/04_wave_on_wiring.gif"><img src="thumbs/poc_microns_brain_wave.jpg" alt="マウス視覚野の波" loading="lazy" width="320" height="320"><b>&#9654;</b><span>マウス視覚野の波</span></a>
<a href="../articles/assets/media/evis_stereo_fullseye.mp4"><img src="thumbs/evis_stereo_depth.jpg" alt="ヒューマノイドの両眼" loading="lazy" width="320" height="320"><b>&#9654;</b><span>ヒューマノイドの両眼</span></a>
<a href="../articles/assets/media/evis_bean_track_fullseye.mp4"><img src="thumbs/evis_bean_track.jpg" alt="箸先カメラの豆追跡" loading="lazy" width="320" height="320"><b>&#9654;</b><span>箸先カメラの豆追跡</span></a>
</div>

## シリーズ記事

<div class="vser">
<a href="https://qiita.com/furuse-kazufumi/items/c1606bcfa2085d204ad6"><img src="thumbs/series_museum.gif" alt="紙面の計測館" loading="lazy" width="480" height="270"><strong>紙面の計測館</strong><span>真値を自分で仕込んだ PoC の展示館</span></a>
<a href="https://qiita.com/furuse-kazufumi/items/b6498dc822bf9eed100f"><img src="thumbs/series_table_tennis.gif" alt="卓球" loading="lazy" width="480" height="270"><strong>卓球</strong><span>跳ねと摩擦を映像から測る</span></a>
<a href="https://qiita.com/furuse-kazufumi/items/1f128b8a36df373c11c7"><img src="thumbs/series_driving.gif" alt="自動運転" loading="lazy" width="480" height="270"><strong>自動運転</strong><span>定理と第 2 実装で採点する</span></a>
<a href="https://qiita.com/furuse-kazufumi/items/331af639c2b9a1493576"><img src="thumbs/series_connectome.gif" alt="コネクトーム(脳の配線図)" loading="lazy" width="480" height="270"><strong>コネクトーム(脳の配線図)</strong><span>ハエの視覚モデルを体に載せて測る</span></a>
<a href="https://qiita.com/furuse-kazufumi/items/57e2f1e5a09165e58b65"><img src="thumbs/series_humanoid.gif" alt="ヒューマノイド運動会" loading="lazy" width="480" height="270"><strong>ヒューマノイド運動会</strong><span>画像処理が審判をする自宅の運動会</span></a>
</div>

## ぜんぶ見る

PoC 218 本と、ロボットの目 4 本。グループを開くとサムネイルが出ます。

<noscript><p><a href="../GALLERY.html">(JavaScript が無い環境では、ギャラリーのページで全部の図を見られます)</a></p></noscript>

<details class="vall"><summary><b>ロボットの目(Fullseye が知覚を担当)</b> (4)</summary>
<div class="vg vs">
<a href="../articles/assets/media/evis_stereo_fullseye.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/evis_stereo_depth.jpg" alt="ヒューマノイドの両眼" width="200" height="200"><b>&#9654;</b><span>ヒューマノイドの両眼</span></a>
<a href="../articles/assets/media/evis_bean_track_fullseye.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/evis_bean_track.jpg" alt="箸先カメラの豆追跡" width="200" height="200"><b>&#9654;</b><span>箸先カメラの豆追跡</span></a>
<a href="../view2026/media/evis_fullseye_walk.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/evis_walk_rgb_depth_dvs.jpg" alt="歩行を RGB・深度・DVS で" width="200" height="200"><b>&#9654;</b><span>歩行を RGB・深度・DVS で</span></a>
<a href="../view2026/media/vision_adaptive_walk.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/walker2d_terrain_vision.jpg" alt="段差を見て歩き方を選ぶ" width="200" height="200"><span>段差を見て歩き方を選ぶ</span></a>
</div>
</details>

<details class="vall"><summary><b>産業検査</b> (32)</summary>
<div class="vg vs">
<a href="../articles/assets/poc/poc_barcode_1d/01_misread_split.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_barcode_1d.jpg" alt="1 次元バーコード" width="200" height="200"><span>1 次元バーコード</span></a>
<a href="../articles/assets/poc/poc_battery_electrode_tortuosity/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_battery_electrode_tortuosity.jpg" alt="電極の屈曲度" width="200" height="200"><span>電極の屈曲度</span></a>
<a href="../articles/assets/poc/poc_bearing_diagnosis/01_envelope_vs_raw.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_bearing_diagnosis.jpg" alt="軸受の異常診断" width="200" height="200"><span>軸受の異常診断</span></a>
<a href="../articles/assets/poc/poc_bump_coplanarity/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_bump_coplanarity.jpg" alt="バンプ共平面性" width="200" height="200"><span>バンプ共平面性</span></a>
<a href="../articles/assets/poc/poc_crack_width/01_width_sweep.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_crack_width.jpg" alt="ひび割れ幅" width="200" height="200"><span>ひび割れ幅</span></a>
<a href="../articles/assets/poc/poc_fabric_defect/01_auc_by_type.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_fabric_defect.jpg" alt="織物の欠陥" width="200" height="200"><span>織物の欠陥</span></a>
<a href="../articles/assets/poc/poc_leak_localization/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_leak_localization.jpg" alt="音で漏水探知" width="200" height="200"><span>音で漏水探知</span></a>
<a href="../articles/assets/poc/poc_machine_condition_fusion/01_scene_machine.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_machine_condition_fusion.jpg" alt="設備保全の融合" width="200" height="200"><span>設備保全の融合</span></a>
<a href="../articles/assets/poc/poc_matrix_code_reading/01_symbol_and_errors.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_matrix_code_reading.jpg" alt="2 値コードを読む" width="200" height="200"><span>2 値コードを読む</span></a>
<a href="../articles/assets/poc/poc_moire_screen/01_failure_split_plot.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_moire_screen.jpg" alt="モアレとムラ" width="200" height="200"><span>モアレとムラ</span></a>
<a href="../articles/assets/poc/poc_print_registration/01_plates.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_print_registration.jpg" alt="印刷の版ずれ" width="200" height="200"><span>印刷の版ずれ</span></a>
<a href="../articles/assets/poc/poc_real_defect_floor/02_defect_floor_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_real_defect_floor.jpg" alt="薄い欠陥の限界" width="200" height="200"><b>&#9654;</b><span>薄い欠陥の限界</span></a>
<a href="../articles/assets/poc/poc_real_texture_invariance/01_textures.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_real_texture_invariance.jpg" alt="実写テクスチャ回転" width="200" height="200"><span>実写テクスチャ回転</span></a>
<a href="../articles/assets/poc/poc_recycling_sorting/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_recycling_sorting.jpg" alt="廃棄物の材質選別" width="200" height="200"><span>廃棄物の材質選別</span></a>
<a href="../articles/assets/poc/poc_solar_el_inspection/01_zero_point_map.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_solar_el_inspection.jpg" alt="太陽電池の EL" width="200" height="200"><span>太陽電池の EL</span></a>
<a href="../articles/assets/poc/poc_solder_fillet_aoi/01_ring_lut.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_solder_fillet_aoi.jpg" alt="はんだの AOI" width="200" height="200"><span>はんだの AOI</span></a>
<a href="../articles/assets/poc/poc_spc/01_spc_xbar_chart.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_spc.jpg" alt="統計的工程管理" width="200" height="200"><span>統計的工程管理</span></a>
<a href="../articles/assets/poc/poc_mt_hidden_fault/01_mt_hidden_cloud.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_mt_hidden_fault.jpg" alt="MT 法の異常検知" width="200" height="200"><span>MT 法の異常検知</span></a>
<a href="../articles/assets/poc/poc_text_region_truth/01_text_region_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_text_region_truth.jpg" alt="文字領域の検出" width="200" height="200"><span>文字領域の検出</span></a>
<a href="../articles/assets/poc/poc_thermal_drift_metrology/01_separate_drifts.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_thermal_drift_metrology.jpg" alt="カメラの熱ドリフト" width="200" height="200"><span>カメラの熱ドリフト</span></a>
<a href="../articles/assets/poc/poc_thermal_radiometry/01_floor.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_thermal_radiometry.jpg" alt="熱画像と温度" width="200" height="200"><span>熱画像と温度</span></a>
<a href="../articles/assets/poc/poc_thermography_ndt/01_depth_table.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_thermography_ndt.jpg" alt="熱画像の欠陥深さ" width="200" height="200"><span>熱画像の欠陥深さ</span></a>
<a href="../articles/assets/poc/poc_veiling_glare/01_verdict.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_veiling_glare.jpg" alt="迷光とコントラスト" width="200" height="200"><span>迷光とコントラスト</span></a>
<a href="../articles/assets/poc/poc_emva1288_sensor/01_photon_transfer.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_emva1288_sensor.jpg" alt="EMVA 1288 測定" width="200" height="200"><b>&#9654;</b><span>EMVA 1288 測定</span></a>
<a href="../articles/assets/poc/poc_web_roll_periodicity/01_scene_web.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_web_roll_periodicity.jpg" alt="搬送ロールの傷" width="200" height="200"><span>搬送ロールの傷</span></a>
<a href="../articles/assets/poc/poc_weld_bead_profile/01_laser_images.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_weld_bead_profile.jpg" alt="溶接ビード断面" width="200" height="200"><span>溶接ビード断面</span></a>
<a href="../articles/assets/poc/poc_weld_bead_scan_angle/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_weld_bead_scan_angle.jpg" alt="溶接ビード走査" width="200" height="200"><span>溶接ビード走査</span></a>
<a href="../articles/assets/poc/poc_weld_radiograph_porosity/01_scene_radiograph.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_weld_radiograph_porosity.jpg" alt="溶接の気孔" width="200" height="200"><span>溶接の気孔</span></a>
<a href="../articles/assets/poc/poc_glyph_typo_detection/01_sign_before_after.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_glyph_typo_detection.jpg" alt="画像の誤字検出" width="200" height="200"><span>画像の誤字検出</span></a>
<a href="../articles/assets/poc/poc_print_layer_inspection/01_slice_stack.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_print_layer_inspection.jpg" alt="3D プリント層検査" width="200" height="200"><span>3D プリント層検査</span></a>
<a href="../articles/assets/poc/poc_agv_fleet/01_agv_naive_vs_adg.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_agv_fleet.jpg" alt="AGV の倉庫" width="200" height="200"><b>&#9654;</b><span>AGV の倉庫</span></a>
<a href="../articles/assets/poc/poc_am_thermal_to_ct/01_melt_pool_frames.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_am_thermal_to_ct.jpg" alt="積層造形と CT" width="200" height="200"><b>&#9654;</b><span>積層造形と CT</span></a>
</div>
</details>

<details class="vall"><summary><b>寸法・形状計測</b> (36)</summary>
<div class="vg vs">
<a href="../articles/assets/poc/poc_aoi_ct_traceability/01_aoi_and_ct.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_aoi_ct_traceability.jpg" alt="AOI と CT の対応" width="200" height="200"><span>AOI と CT の対応</span></a>
<a href="../articles/assets/poc/poc_asbuilt_wall_deviation/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_asbuilt_wall_deviation.jpg" alt="竣工した壁の歪み" width="200" height="200"><span>竣工した壁の歪み</span></a>
<a href="../articles/assets/poc/poc_battery_electrode_breathing/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_battery_electrode_breathing.jpg" alt="電極の呼吸" width="200" height="200"><span>電極の呼吸</span></a>
<a href="../articles/assets/poc/poc_bilateral_asymmetry/01_floor_vs_spacing.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_bilateral_asymmetry.jpg" alt="左右非対称性" width="200" height="200"><span>左右非対称性</span></a>
<a href="../articles/assets/poc/poc_dic_strain/05_tensile_ramp.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_dic_strain.jpg" alt="DIC ひずみ" width="200" height="200"><b>&#9654;</b><span>DIC ひずみ</span></a>
<a href="../articles/assets/poc/poc_die_tilt_tsv_overlay/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_die_tilt_tsv_overlay.jpg" alt="ダイ傾きと TSV" width="200" height="200"><span>ダイ傾きと TSV</span></a>
<a href="../articles/assets/poc/poc_dimensional_inspection/01_slot_bias.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_dimensional_inspection.jpg" alt="部品の寸法検査" width="200" height="200"><span>部品の寸法検査</span></a>
<a href="../articles/assets/poc/poc_fiber_orientation/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_fiber_orientation.jpg" alt="繊維の配向" width="200" height="200"><span>繊維の配向</span></a>
<a href="../articles/assets/poc/poc_gear_tooth_metrology/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_gear_tooth_metrology.jpg" alt="歯車の歯形" width="200" height="200"><span>歯車の歯形</span></a>
<a href="../articles/assets/poc/poc_interferometry_step/05_step_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_interferometry_step.jpg" alt="白色干渉の段差" width="200" height="200"><b>&#9654;</b><span>白色干渉の段差</span></a>
<a href="../articles/assets/poc/poc_metal_grain_size/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_metal_grain_size.jpg" alt="結晶粒度" width="200" height="200"><span>結晶粒度</span></a>
<a href="../articles/assets/poc/poc_multibeam_bathymetry/17_survey.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_multibeam_bathymetry.jpg" alt="多ビーム測深" width="200" height="200"><b>&#9654;</b><span>多ビーム測深</span></a>
<a href="../articles/assets/poc/poc_particle_sizing/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_particle_sizing.jpg" alt="粒度分布" width="200" height="200"><span>粒度分布</span></a>
<a href="../articles/assets/poc/poc_photoelasticity/03_load_and_isoclinics.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_photoelasticity.jpg" alt="光弾性の応力" width="200" height="200"><b>&#9654;</b><span>光弾性の応力</span></a>
<a href="../articles/assets/poc/poc_rail_corrugation/01_planted_components.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_rail_corrugation.jpg" alt="レールの波状摩耗" width="200" height="200"><span>レールの波状摩耗</span></a>
<a href="../articles/assets/poc/poc_real_coin_metrology/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_real_coin_metrology.jpg" alt="実写のコイン" width="200" height="200"><span>実写のコイン</span></a>
<a href="../articles/assets/poc/poc_screw_thread_metrology/01_zero_spectrum.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_screw_thread_metrology.jpg" alt="ねじの輪郭" width="200" height="200"><span>ねじの輪郭</span></a>
<a href="../articles/assets/poc/poc_stockpile_volume/07_scan_orbit.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_stockpile_volume.jpg" alt="堆積物の体積" width="200" height="200"><b>&#9654;</b><span>堆積物の体積</span></a>
<a href="../articles/assets/poc/poc_strain_history/05_history_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_strain_history.jpg" alt="クリープひずみ" width="200" height="200"><b>&#9654;</b><span>クリープひずみ</span></a>
<a href="../articles/assets/poc/poc_surface_roughness/01_surface_components.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_surface_roughness.jpg" alt="表面粗さ" width="200" height="200"><span>表面粗さ</span></a>
<a href="../articles/assets/poc/poc_tacsim_elastic_membrane/03_tacsim_force_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_tacsim_elastic_membrane.jpg" alt="視触覚センサ" width="200" height="200"><b>&#9654;</b><span>視触覚センサ</span></a>
<a href="../articles/assets/poc/poc_tacsim_marker_shear/02_tacslip_stick_circle_shrinks.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_tacsim_marker_shear.jpg" alt="触覚のせん断" width="200" height="200"><b>&#9654;</b><span>触覚のせん断</span></a>
<a href="../articles/assets/poc/poc_tactile_dipole_torque/02_tactorque_dipole_grows_with_M.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_tactile_dipole_torque.jpg" alt="触覚双極子" width="200" height="200"><b>&#9654;</b><span>触覚双極子</span></a>
<a href="../articles/assets/poc/poc_granular_heap_repose/11_granular_datum_tilt_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_granular_heap_repose.jpg" alt="粉体の山" width="200" height="200"><b>&#9654;</b><span>粉体の山</span></a>
<a href="../articles/assets/poc/poc_food_cutting_measure/01_cutting_track_force.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_food_cutting_measure.jpg" alt="食材の切断" width="200" height="200"><b>&#9654;</b><span>食材の切断</span></a>
<a href="../articles/assets/poc/poc_tacdome_large_deformation/01_tacdome_press_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_tacdome_large_deformation.jpg" alt="ドーム指先の接触" width="200" height="200"><b>&#9654;</b><span>ドーム指先の接触</span></a>
<a href="../articles/assets/poc/poc_polish_wipe_measure/01_polish_raster_wipe_coat.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_polish_wipe_measure.jpg" alt="研磨と拭き取り" width="200" height="200"><b>&#9654;</b><span>研磨と拭き取り</span></a>
<a href="../articles/assets/poc/poc_powder_scoop_pour/03_scoop_stream_synthetic_frames.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_powder_scoop_pour.jpg" alt="粉体のすくい注ぎ" width="200" height="200"><b>&#9654;</b><span>粉体のすくい注ぎ</span></a>
<a href="../articles/assets/poc/poc_powder_grinding_ae/07_psd_fining_during_grinding.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_powder_grinding_ae.jpg" alt="乳鉢の粉砕" width="200" height="200"><b>&#9654;</b><span>乳鉢の粉砕</span></a>
<a href="../articles/assets/poc/poc_pxrd_phase_peel/01_phase_peel.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_pxrd_phase_peel.jpg" alt="X 線回折の相分離" width="200" height="200"><b>&#9654;</b><span>X 線回折の相分離</span></a>
<a href="../articles/assets/poc/poc_dose_uniformity_from_grinding/01_cv_bias_decomposition.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_dose_uniformity_from_grinding.jpg" alt="薬の量の均一性" width="200" height="200"><span>薬の量の均一性</span></a>
<a href="../articles/assets/poc/poc_knife_tactile_toughness/06_cut_with_fingertip_pads.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_knife_tactile_toughness.jpg" alt="指先で包丁を持つ" width="200" height="200"><b>&#9654;</b><span>指先で包丁を持つ</span></a>
<a href="../articles/assets/poc/poc_measurement_system_analysis/16_breakdown_movie.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_measurement_system_analysis.jpg" alt="ゲージ R&R" width="200" height="200"><b>&#9654;</b><span>ゲージ R&R</span></a>
<a href="../articles/assets/poc/poc_zernike_aberrations/06_through_focus.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_zernike_aberrations.jpg" alt="ゼルニケ収差" width="200" height="200"><b>&#9654;</b><span>ゼルニケ収差</span></a>
<a href="../articles/assets/poc/poc_attention_identities/01_attention_masks.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_attention_identities.jpg" alt="注意機構の恒等式" width="200" height="200"><span>注意機構の恒等式</span></a>
<a href="../articles/assets/poc/poc_residue_crt/03_residue_rotation_needle.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_residue_crt.jpg" alt="剰余定理で位相" width="200" height="200"><b>&#9654;</b><span>剰余定理で位相</span></a>
</div>
</details>

<details class="vall"><summary><b>3-D 形状</b> (18)</summary>
<div class="vg vs">
<a href="../articles/assets/poc/poc_battery_ct_degradation/01_xray_projection.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_battery_ct_degradation.jpg" alt="電池の CT 劣化" width="200" height="200"><span>電池の CT 劣化</span></a>
<a href="../articles/assets/poc/poc_bev_sensor_fusion/01_scene_bev.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_bev_sensor_fusion.jpg" alt="鳥瞰図の融合" width="200" height="200"><span>鳥瞰図の融合</span></a>
<a href="../articles/assets/poc/poc_cad_scan_deviation/14_align_orbit.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_cad_scan_deviation.jpg" alt="CAD と点群の差" width="200" height="200"><b>&#9654;</b><span>CAD と点群の差</span></a>
<a href="../articles/assets/poc/poc_crop_phenotyping/01_capsule_calibration.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_crop_phenotyping.jpg" alt="作物の葉面積" width="200" height="200"><span>作物の葉面積</span></a>
<a href="../articles/assets/poc/poc_ct_void_morphology/13_section_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_ct_void_morphology.jpg" alt="接合層のボイド" width="200" height="200"><b>&#9654;</b><span>接合層のボイド</span></a>
<a href="../articles/assets/poc/poc_dfm_thickness_overhang/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_dfm_thickness_overhang.jpg" alt="造形しやすさ" width="200" height="200"><span>造形しやすさ</span></a>
<a href="../articles/assets/poc/poc_lidar_terrain_change/12_flight.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_lidar_terrain_change.jpg" alt="斜面の土量" width="200" height="200"><b>&#9654;</b><span>斜面の土量</span></a>
<a href="../articles/assets/poc/poc_livestock_body_volume/14_hull_orbit.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_livestock_body_volume.jpg" alt="家畜の体重" width="200" height="200"><b>&#9654;</b><span>家畜の体重</span></a>
<a href="../articles/assets/poc/poc_mesh_quality_repair/14_decimate_orbit.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_mesh_quality_repair.jpg" alt="メッシュ修復" width="200" height="200"><b>&#9654;</b><span>メッシュ修復</span></a>
<a href="../articles/assets/poc/poc_pallet_load_utilization/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_pallet_load_utilization.jpg" alt="パレット積載率" width="200" height="200"><span>パレット積載率</span></a>
<a href="../articles/assets/poc/poc_pipe_wall_loss/01_scene_pipe.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_pipe_wall_loss.jpg" alt="配管の減肉" width="200" height="200"><span>配管の減肉</span></a>
<a href="../articles/assets/poc/poc_print_warpage_risk/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_print_warpage_risk.jpg" alt="積層の反り" width="200" height="200"><span>積層の反り</span></a>
<a href="../articles/assets/poc/poc_safety_clearance/01_conditions.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_safety_clearance.jpg" alt="人と機械の距離" width="200" height="200"><span>人と機械の距離</span></a>
<a href="../articles/assets/poc/poc_scan_to_bim_asbuilt/01_scene_plan_section.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_scan_to_bim_asbuilt.jpg" alt="設計と実物の差" width="200" height="200"><span>設計と実物の差</span></a>
<a href="../articles/assets/poc/poc_structure_4d_deterioration/12_years_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_structure_4d_deterioration.jpg" alt="構造物の経年" width="200" height="200"><b>&#9654;</b><span>構造物の経年</span></a>
<a href="../articles/assets/poc/poc_symmetry_restoration/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_symmetry_restoration.jpg" alt="対称性で補う" width="200" height="200"><span>対称性で補う</span></a>
<a href="../articles/assets/poc/poc_endless_zoom_and_turning_solids/03_zoom_loop.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_endless_zoom_and_turning_solids.jpg" alt="無限ズーム" width="200" height="200"><b>&#9654;</b><span>無限ズーム</span></a>
<a href="../articles/assets/poc/poc_four_dimensions_by_three_d_tools/03_hopf_turn.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_four_dimensions_by_three_d_tools.jpg" alt="4 次元を 3-D で" width="200" height="200"><b>&#9654;</b><span>4 次元を 3-D で</span></a>
</div>
</details>

<details class="vall"><summary><b>幾何・校正</b> (18)</summary>
<div class="vg vs">
<a href="../articles/assets/poc/poc_camera_calibration/05_calibration_convergence.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_camera_calibration.jpg" alt="カメラ校正" width="200" height="200"><b>&#9654;</b><span>カメラ校正</span></a>
<a href="../articles/assets/poc/poc_panorama_drift/05_chain_drift_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_panorama_drift.jpg" alt="パノラマのずれ" width="200" height="200"><b>&#9654;</b><span>パノラマのずれ</span></a>
<a href="../articles/assets/poc/poc_real_stereo_depth/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_real_stereo_depth.jpg" alt="実写のステレオ" width="200" height="200"><span>実写のステレオ</span></a>
<a href="../articles/assets/poc/poc_registration_basin/05_icp_basin_iterations.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_registration_basin.jpg" alt="点群位置合わせ" width="200" height="200"><b>&#9654;</b><span>点群位置合わせ</span></a>
<a href="../articles/assets/poc/poc_rotation_invariance_audit/02_rotating_coin.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_rotation_invariance_audit.jpg" alt="回転不変の監査" width="200" height="200"><b>&#9654;</b><span>回転不変の監査</span></a>
<a href="../articles/assets/poc/poc_carla_bridge/01_carla_two_worlds.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_carla_bridge.jpg" alt="2 つの世界で撮る" width="200" height="200"><span>2 つの世界で撮る</span></a>
<a href="../articles/assets/poc/poc_driving_town/04_town_drive_through.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_driving_town.jpg" alt="町を組む" width="200" height="200"><b>&#9654;</b><span>町を組む</span></a>
<a href="../articles/assets/poc/poc_driving_japan_town/03_japan_town_drive.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_driving_japan_town.jpg" alt="実在の日本の町" width="200" height="200"><b>&#9654;</b><span>実在の日本の町</span></a>
<a href="../articles/assets/poc/poc_driving_commonroad/01_commonroad_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_driving_commonroad.jpg" alt="CommonRoad で採点" width="200" height="200"><span>CommonRoad で採点</span></a>
<a href="../articles/assets/poc/poc_pegsim_insertion/04_pegsim_insert_corrected.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_pegsim_insertion.jpg" alt="ペグ挿入" width="200" height="200"><b>&#9654;</b><span>ペグ挿入</span></a>
<a href="../articles/assets/poc/poc_air_hockey_intercept/02_airhockey_prediction_cone_narrows.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_air_hockey_intercept.jpg" alt="エアホッケー" width="200" height="200"><b>&#9654;</b><span>エアホッケー</span></a>
<a href="../articles/assets/poc/poc_peg_failure_recovery/05_pegfail_wrist_camera_wedging_detect_recover.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_peg_failure_recovery.jpg" alt="挿入失敗の回復" width="200" height="200"><b>&#9654;</b><span>挿入失敗の回復</span></a>
<a href="../articles/assets/poc/poc_tacscalib_sphere_lut/02_tacscalib_synthetic_relight.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_tacscalib_sphere_lut.jpg" alt="触覚センサ較正" width="200" height="200"><b>&#9654;</b><span>触覚センサ較正</span></a>
<a href="../articles/assets/poc/poc_peg_insertion_tactile/03_pegtactile_whitney_insertion_through_membranes.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_peg_insertion_tactile.jpg" alt="指の膜でペグ挿入" width="200" height="200"><b>&#9654;</b><span>指の膜でペグ挿入</span></a>
<a href="../articles/assets/poc/poc_peg_symmetry_search/01_pegsym_rotating_shapes_read_mod_2pi_over_n.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_peg_symmetry_search.jpg" alt="ペグの対称性" width="200" height="200"><b>&#9654;</b><span>ペグの対称性</span></a>
<a href="../articles/assets/poc/poc_reproducible_icp/01_error_staircase_ozaki1.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_reproducible_icp.jpg" alt="ビット再現 ICP" width="200" height="200"><span>ビット再現 ICP</span></a>
<a href="../articles/assets/poc/poc_public_camera_heading/02_yaw_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_public_camera_heading.jpg" alt="公共カメラの向き" width="200" height="200"><b>&#9654;</b><span>公共カメラの向き</span></a>
<a href="../articles/assets/poc/poc_public_camera_heading_real/02_sunset_follow.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_public_camera_heading_real.jpg" alt="カメラの向き(実写)" width="200" height="200"><b>&#9654;</b><span>カメラの向き(実写)</span></a>
</div>
</details>

<details class="vall"><summary><b>撮像品質・復元</b> (16)</summary>
<div class="vg vs">
<a href="../articles/assets/poc/poc_camera_shake_deblur/05_kernel_angle_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_camera_shake_deblur.jpg" alt="手ブレ補正" width="200" height="200"><b>&#9654;</b><span>手ブレ補正</span></a>
<a href="../articles/assets/poc/poc_colormap_readability/01_gain_profile.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_colormap_readability.jpg" alt="疑似カラーの読み" width="200" height="200"><span>疑似カラーの読み</span></a>
<a href="../articles/assets/poc/poc_compound_eye/01_compound_eye_scaling.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_compound_eye.jpg" alt="ハエの複眼" width="200" height="200"><span>ハエの複眼</span></a>
<a href="../articles/assets/poc/poc_ct_fidelity/01_recon_sweep.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_ct_fidelity.jpg" alt="CT 再構成の限界" width="200" height="200"><span>CT 再構成の限界</span></a>
<a href="../articles/assets/poc/poc_dehazing/05_haze_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_dehazing.jpg" alt="霞を剥がす" width="200" height="200"><b>&#9654;</b><span>霞を剥がす</span></a>
<a href="../articles/assets/poc/poc_dtof_ranging/01_histograms.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_dtof_ranging.jpg" alt="光子で測距" width="200" height="200"><span>光子で測距</span></a>
<a href="../articles/assets/poc/poc_focus_stacking/05_focus_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_focus_stacking.jpg" alt="焦点合成" width="200" height="200"><b>&#9654;</b><span>焦点合成</span></a>
<a href="../articles/assets/poc/poc_lightfield_depth/01_scene_and_depth.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_lightfield_depth.jpg" alt="光場から深度" width="200" height="200"><span>光場から深度</span></a>
<a href="../articles/assets/poc/poc_real_deblur_honesty/01_restore.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_real_deblur_honesty.jpg" alt="実写のブレ補正" width="200" height="200"><span>実写のブレ補正</span></a>
<a href="../articles/assets/poc/poc_superresolution_limits/05_growth.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_superresolution_limits.jpg" alt="超解像の限界" width="200" height="200"><b>&#9654;</b><span>超解像の限界</span></a>
<a href="../articles/assets/poc/poc_iqa_tid2013/01_tid2013_mos_vs_psnr.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_iqa_tid2013.jpg" alt="画質指標と TID2013" width="200" height="200"><span>画質指標と TID2013</span></a>
<a href="../articles/assets/poc/poc_iqa_fsim_gmsd_vif/01_iqa_tid2013_mos_vs_fsim.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_iqa_fsim_gmsd_vif.jpg" alt="知覚指標の一致" width="200" height="200"><span>知覚指標の一致</span></a>
<a href="../articles/assets/poc/poc_vanishing_detail_and_morphing_area/06_morph_loop.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_vanishing_detail_and_morphing_area.jpg" alt="消える細部と面積" width="200" height="200"><b>&#9654;</b><span>消える細部と面積</span></a>
<a href="../articles/assets/poc/poc_segmentation_gauntlet/08_gauntlet_blobs.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_segmentation_gauntlet.jpg" alt="分割の関門" width="200" height="200"><b>&#9654;</b><span>分割の関門</span></a>
<a href="../articles/assets/poc/poc_active_contours/06_u_shape_snakes.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_active_contours.jpg" alt="動的輪郭" width="200" height="200"><b>&#9654;</b><span>動的輪郭</span></a>
<a href="../articles/assets/poc/poc_graph_hierarchy_segmentation/08_watershed_theta_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_graph_hierarchy_segmentation.jpg" alt="グラフ分割" width="200" height="200"><b>&#9654;</b><span>グラフ分割</span></a>
</div>
</details>

<details class="vall"><summary><b>色・分離</b> (4)</summary>
<div class="vg vs">
<a href="../articles/assets/poc/poc_pigment_unmixing/01_per_field_auc.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_pigment_unmixing.jpg" alt="顔料の層を分離" width="200" height="200"><span>顔料の層を分離</span></a>
<a href="../articles/assets/poc/poc_polarization_specular/01_fresnel.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_polarization_specular.jpg" alt="偏光で鏡面除去" width="200" height="200"><span>偏光で鏡面除去</span></a>
<a href="../articles/assets/poc/poc_real_stain_unmix/01_separation.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_real_stain_unmix.jpg" alt="実写の染色分離" width="200" height="200"><span>実写の染色分離</span></a>
<a href="../articles/assets/poc/poc_white_balance/01_casts.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_white_balance.jpg" alt="ホワイトバランス" width="200" height="200"><span>ホワイトバランス</span></a>
</div>
</details>

<details class="vall"><summary><b>時系列を 3-D として測る</b> (21)</summary>
<div class="vg vs">
<a href="../articles/assets/poc/poc_beam_modal_video/14_beam_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_beam_modal_video.jpg" alt="動画でモード同定" width="200" height="200"><b>&#9654;</b><span>動画でモード同定</span></a>
<a href="../articles/assets/poc/poc_cold_chain_excursion/01_scene_slices.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_cold_chain_excursion.jpg" alt="冷蔵輸送の温度" width="200" height="200"><span>冷蔵輸送の温度</span></a>
<a href="../articles/assets/poc/poc_crack_width_timeseries/11_series_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_crack_width_timeseries.jpg" alt="ひび割れの伸び" width="200" height="200"><b>&#9654;</b><span>ひび割れの伸び</span></a>
<a href="../articles/assets/poc/poc_motion_magnification/05_magnify_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_motion_magnification.jpg" alt="微小振動の拡大" width="200" height="200"><b>&#9654;</b><span>微小振動の拡大</span></a>
<a href="../articles/assets/poc/poc_particle_tracking/05_tracking_links.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_particle_tracking.jpg" alt="粒子追跡" width="200" height="200"><b>&#9654;</b><span>粒子追跡</span></a>
<a href="../articles/assets/poc/poc_settlement_significance/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_settlement_significance.jpg" alt="沈下か測り直しか" width="200" height="200"><span>沈下か測り直しか</span></a>
<a href="../articles/assets/poc/poc_template_tracking/05_twin_vs_flat_occluder.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_template_tracking.jpg" alt="テンプレート追跡" width="200" height="200"><b>&#9654;</b><span>テンプレート追跡</span></a>
<a href="../articles/assets/poc/poc_timelapse_growth/05_growth_merge.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_timelapse_growth.jpg" alt="成長のタイムラプス" width="200" height="200"><b>&#9654;</b><span>成長のタイムラプス</span></a>
<a href="../articles/assets/poc/poc_traffic_counting/05_counting_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_traffic_counting.jpg" alt="交通量の計数" width="200" height="200"><b>&#9654;</b><span>交通量の計数</span></a>
<a href="../articles/assets/poc/poc_warehouse_flow/01_heat_ambiguity.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_warehouse_flow.jpg" alt="庫内の滞留" width="200" height="200"><span>庫内の滞留</span></a>
<a href="../articles/assets/poc/poc_xyt_event_surface/05_arrival_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_xyt_event_surface.jpg" alt="到達時刻面" width="200" height="200"><b>&#9654;</b><span>到達時刻面</span></a>
<a href="../articles/assets/poc/poc_video_cube/02_cube_orbit.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_video_cube.jpg" alt="動画の時空立方体" width="200" height="200"><b>&#9654;</b><span>動画の時空立方体</span></a>
<a href="../articles/assets/poc/poc_live4d/01_beating_orbit.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_live4d.jpg" alt="生体の 3D+t" width="200" height="200"><b>&#9654;</b><span>生体の 3D+t</span></a>
<a href="../articles/assets/poc/poc_diabolo_model_and_vision/01_diabolo_throw_axis_from_image.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_diabolo_model_and_vision.jpg" alt="ディアボロ" width="200" height="200"><b>&#9654;</b><span>ディアボロ</span></a>
<a href="../articles/assets/poc/poc_swarm_obstacle_from_flow/01_swarmflow_hidden_obstacle_emerges.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_swarm_obstacle_from_flow.jpg" alt="群れで障害物察知" width="200" height="200"><b>&#9654;</b><span>群れで障害物察知</span></a>
<a href="../articles/assets/poc/poc_ball_bounce/06_rally_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_ball_bounce.jpg" alt="卓球の球を追う" width="200" height="200"><b>&#9654;</b><span>卓球の球を追う</span></a>
<a href="../articles/assets/poc/poc_kendama/05_catch_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_kendama.jpg" alt="けん玉" width="200" height="200"><b>&#9654;</b><span>けん玉</span></a>
<a href="../articles/assets/poc/poc_table_tennis_spin/01_side_three_serves.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_table_tennis_spin.jpg" alt="卓球の回転" width="200" height="200"><b>&#9654;</b><span>卓球の回転</span></a>
<a href="../articles/assets/poc/poc_table_tennis_bounce/01_drop_test.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_table_tennis_bounce.jpg" alt="卓球の跳ね" width="200" height="200"><b>&#9654;</b><span>卓球の跳ね</span></a>
<a href="../articles/assets/poc/poc_table_tennis_rally_loop/01_landing_cloud.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_table_tennis_rally_loop.jpg" alt="ラリーと読み誤差" width="200" height="200"><b>&#9654;</b><span>ラリーと読み誤差</span></a>
<a href="../articles/assets/poc/poc_periodic_video_boundary/02_loop.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_periodic_video_boundary.jpg" alt="周期的な動画" width="200" height="200"><b>&#9654;</b><span>周期的な動画</span></a>
</div>
</details>

<details class="vall"><summary><b>コネクトーム・神経</b> (19)</summary>
<div class="vg vs">
<a href="../articles/assets/poc/poc_fly_vision/01_fly_vision_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_fly_vision.jpg" alt="ハエの視覚前段" width="200" height="200"><span>ハエの視覚前段</span></a>
<a href="../articles/assets/poc/poc_larval_connectome_reservoir/01_adjacency_binned_connectome_vs_shuffle.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_larval_connectome_reservoir.jpg" alt="幼虫の配線で計算" width="200" height="200"><span>幼虫の配線で計算</span></a>
<a href="../articles/assets/poc/poc_malecns_activity_wave/01_activity_wave_connectome_vs_shuffle.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_malecns_activity_wave.jpg" alt="ハエの脳の波" width="200" height="200"><b>&#9654;</b><span>ハエの脳の波</span></a>
<a href="../articles/assets/poc/poc_eye_to_brain/01_eye_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_eye_to_brain.jpg" alt="複眼から脳へ" width="200" height="200"><b>&#9654;</b><span>複眼から脳へ</span></a>
<a href="../articles/assets/poc/poc_em_second_opinion/02_suspects_on_the_cube.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_em_second_opinion.jpg" alt="EM 校正の検算" width="200" height="200"><b>&#9654;</b><span>EM 校正の検算</span></a>
<a href="../articles/assets/poc/poc_connectome_motor_bottleneck/03_activity_flow.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_connectome_motor_bottleneck.jpg" alt="動きの量子化" width="200" height="200"><b>&#9654;</b><span>動きの量子化</span></a>
<a href="../articles/assets/poc/poc_microns_brain_wave/01_brain_wave.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_microns_brain_wave.jpg" alt="MICrONS の波" width="200" height="200"><b>&#9654;</b><span>MICrONS の波</span></a>
<a href="../articles/assets/poc/poc_em_branch_territory/02_territory_turning.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_em_branch_territory.jpg" alt="枝の縄張り" width="200" height="200"><b>&#9654;</b><span>枝の縄張り</span></a>
<a href="../articles/assets/poc/poc_connectome_lr_symmetry/01_lr_jaccard_closed_form.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_connectome_lr_symmetry.jpg" alt="線虫の左右対称" width="200" height="200"><span>線虫の左右対称</span></a>
<a href="../articles/assets/poc/poc_connectome_across_worms/02_wiring_across_development.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_connectome_across_worms.jpg" alt="線虫の個体差" width="200" height="200"><b>&#9654;</b><span>線虫の個体差</span></a>
<a href="../articles/assets/poc/poc_connectome_across_decades/01_jaccard_across_decades.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_connectome_across_decades.jpg" alt="40 年前の配線図" width="200" height="200"><span>40 年前の配線図</span></a>
<a href="../articles/assets/poc/poc_worm_neurites_grow/01_neurite_length_growth.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_worm_neurites_grow.jpg" alt="神経突起の成長" width="200" height="200"><span>神経突起の成長</span></a>
<a href="../articles/assets/poc/poc_em_split_merge_score/01_split_vs_merge_by_threshold.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_em_split_merge_score.jpg" alt="EM 分割の採点" width="200" height="200"><span>EM 分割の採点</span></a>
<a href="../articles/assets/poc/poc_em_wiring_errors/01_proofreading_order.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_em_wiring_errors.jpg" alt="分割誤りと配線" width="200" height="200"><span>分割誤りと配線</span></a>
<a href="../articles/assets/poc/poc_worm_synapses_vs_neurites/01_density_by_stage.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_worm_synapses_vs_neurites.jpg" alt="シナプスと突起" width="200" height="200"><span>シナプスと突起</span></a>
<a href="../articles/assets/poc/poc_skeleton_run_length_vs_voi/01_merge_size_erl_vs_voi.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_skeleton_run_length_vs_voi.jpg" alt="走行長と VOI" width="200" height="200"><span>走行長と VOI</span></a>
<a href="../articles/assets/poc/poc_swc_tree_truth/01_swc_projection.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_swc_tree_truth.jpg" alt="本物の木で骨格" width="200" height="200"><span>本物の木で骨格</span></a>
<a href="../articles/assets/poc/poc_fly_optomotor_steering/06_follow.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_fly_optomotor_steering.jpg" alt="ハエの進路制御" width="200" height="200"><b>&#9654;</b><span>ハエの進路制御</span></a>
<a href="../articles/assets/poc/poc_worm_core_persists/04_core_map_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_worm_core_persists.jpg" alt="線虫の脳の核" width="200" height="200"><b>&#9654;</b><span>線虫の脳の核</span></a>
</div>
</details>

<details class="vall"><summary><b>医用・生物</b> (9)</summary>
<div class="vg vs">
<a href="../articles/assets/poc/poc_bone_trabecular_thickness/01_scene_truth.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_bone_trabecular_thickness.jpg" alt="骨梁の厚さ" width="200" height="200"><span>骨梁の厚さ</span></a>
<a href="../articles/assets/poc/poc_cell_counting/01_scene_dense.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_cell_counting.jpg" alt="重なる細胞の計数" width="200" height="200"><span>重なる細胞の計数</span></a>
<a href="../articles/assets/poc/poc_colocalization_crosstalk/01_scene_channels.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_colocalization_crosstalk.jpg" alt="蛍光の共局在" width="200" height="200"><span>蛍光の共局在</span></a>
<a href="../articles/assets/poc/poc_mri_bias_field/01_controls.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_mri_bias_field.jpg" alt="MRI バイアス場" width="200" height="200"><span>MRI バイアス場</span></a>
<a href="../articles/assets/poc/poc_nuclei_ploidy/01_histograms.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_nuclei_ploidy.jpg" alt="核の倍数性" width="200" height="200"><span>核の倍数性</span></a>
<a href="../articles/assets/poc/poc_vessel_network/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_vessel_network.jpg" alt="血管網の分岐" width="200" height="200"><span>血管網の分岐</span></a>
<a href="../articles/assets/poc/poc_wound_area_tracking/06_healing_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_wound_area_tracking.jpg" alt="創傷面積の変化" width="200" height="200"><b>&#9654;</b><span>創傷面積の変化</span></a>
<a href="../articles/assets/poc/poc_physarum_maze/02_maze_tubes_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_physarum_maze.jpg" alt="粘菌の迷路" width="200" height="200"><b>&#9654;</b><span>粘菌の迷路</span></a>
<a href="../articles/assets/poc/poc_physarum_transport/01_transport_tubes_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_physarum_transport.jpg" alt="粘菌の最適輸送" width="200" height="200"><b>&#9654;</b><span>粘菌の最適輸送</span></a>
</div>
</details>

<details class="vall"><summary><b>天文・環境</b> (21)</summary>
<div class="vg vs">
<a href="../articles/assets/poc/poc_allsky_cloud_cover/01_jacobian.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_allsky_cloud_cover.jpg" alt="全天カメラの雲量" width="200" height="200"><span>全天カメラの雲量</span></a>
<a href="../articles/assets/poc/poc_astro_photometry/01_stack_scaling.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_astro_photometry.jpg" alt="星の測光精度" width="200" height="200"><span>星の測光精度</span></a>
<a href="../articles/assets/poc/poc_change_detection_misreg/01_plot_fp_vs_shift.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_change_detection_misreg.jpg" alt="変化検出" width="200" height="200"><span>変化検出</span></a>
<a href="../articles/assets/poc/poc_datacenter_thermal_field/01_scene_truth.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_datacenter_thermal_field.jpg" alt="3-D 熱場の復元" width="200" height="200"><span>3-D 熱場の復元</span></a>
<a href="../articles/assets/poc/poc_dem_terrain/05_terrain_flight.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_dem_terrain.jpg" alt="地形を測る" width="200" height="200"><b>&#9654;</b><span>地形を測る</span></a>
<a href="../articles/assets/poc/poc_exoplanet_transit/01_scene_starfield.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_exoplanet_transit.jpg" alt="系外惑星の通過" width="200" height="200"><span>系外惑星の通過</span></a>
<a href="../articles/assets/poc/poc_geodetic_height_frames/01_geoid_frames.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_geodetic_height_frames.jpg" alt="座標の高さの罠" width="200" height="200"><span>座標の高さの罠</span></a>
<a href="../articles/assets/poc/poc_leaf_disease_area/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_leaf_disease_area.jpg" alt="葉の病斑" width="200" height="200"><span>葉の病斑</span></a>
<a href="../articles/assets/poc/poc_pv_thermal_survey/01_norm_table.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_pv_thermal_survey.jpg" alt="太陽光の熱画像" width="200" height="200"><span>太陽光の熱画像</span></a>
<a href="../articles/assets/poc/poc_real_sky_photometry/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_real_sky_photometry.jpg" alt="実写の深宇宙" width="200" height="200"><span>実写の深宇宙</span></a>
<a href="../articles/assets/poc/poc_river_surface_velocity/13_accumulate_pairs.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_river_surface_velocity.jpg" alt="河川の表面流速" width="200" height="200"><b>&#9654;</b><span>河川の表面流速</span></a>
<a href="../articles/assets/poc/poc_sea_ice_concentration/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_sea_ice_concentration.jpg" alt="海氷密接度" width="200" height="200"><span>海氷密接度</span></a>
<a href="../articles/assets/poc/poc_search_sweep_width/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_search_sweep_width.jpg" alt="捜索の走査幅" width="200" height="200"><span>捜索の走査幅</span></a>
<a href="../articles/assets/poc/poc_solar_limb_darkening/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_solar_limb_darkening.jpg" alt="周辺減光と輪郭" width="200" height="200"><span>周辺減光と輪郭</span></a>
<a href="../articles/assets/poc/poc_star_astrometry/01_snr_sweep.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_star_astrometry.jpg" alt="星の位置精度" width="200" height="200"><span>星の位置精度</span></a>
<a href="../articles/assets/poc/poc_tree_ring_dendro/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_tree_ring_dendro.jpg" alt="年輪の幅" width="200" height="200"><span>年輪の幅</span></a>
<a href="../articles/assets/poc/poc_vegetation_cover/01_mixed_pixel_response.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_vegetation_cover.jpg" alt="畑の緑の被覆率" width="200" height="200"><span>畑の緑の被覆率</span></a>
<a href="../articles/assets/poc/poc_water_level/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_water_level.jpg" alt="河川の水位" width="200" height="200"><span>河川の水位</span></a>
<a href="../articles/assets/poc/poc_rover_slip_risk_path/03_rover_slip_update.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_rover_slip_risk_path.jpg" alt="火星の車輪滑り" width="200" height="200"><b>&#9654;</b><span>火星の車輪滑り</span></a>
<a href="../articles/assets/poc/poc_geodetic_benchmarks_real/01_residual_sorted.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_geodetic_benchmarks_real.jpg" alt="2 つの高さ(実データ)" width="200" height="200"><span>2 つの高さ(実データ)</span></a>
<a href="../articles/assets/poc/poc_gravitational_lens_invariants/10_source_crossing.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_gravitational_lens_invariants.jpg" alt="重力レンズ" width="200" height="200"><b>&#9654;</b><span>重力レンズ</span></a>
</div>
</details>

<details class="vall"><summary><b>法科学・文書</b> (4)</summary>
<div class="vg vs">
<a href="../articles/assets/poc/poc_document_scan/01_rectify_zero_points.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_document_scan.jpg" alt="書類をまっすぐに" width="200" height="200"><span>書類をまっすぐに</span></a>
<a href="../articles/assets/poc/poc_forensics_roc/01_score_maps.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_forensics_roc.jpg" alt="改竄検出の ROC" width="200" height="200"><span>改竄検出の ROC</span></a>
<a href="../articles/assets/poc/poc_fresco_craquelure/01_ridge_ops.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_fresco_craquelure.jpg" alt="絵画のひび割れ網" width="200" height="200"><span>絵画のひび割れ網</span></a>
<a href="../articles/assets/poc/poc_prnu_camera_fingerprint/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_prnu_camera_fingerprint.jpg" alt="カメラ指紋" width="200" height="200"><span>カメラ指紋</span></a>
</div>
</details>

<details class="vall"><summary><b>自動運転</b> (13)</summary>
<div class="vg vs">
<a href="../articles/assets/poc/poc_car_parking/04_parking_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_car_parking.jpg" alt="最短の曲がり方" width="200" height="200"><b>&#9654;</b><span>最短の曲がり方</span></a>
<a href="../articles/assets/poc/poc_driving_school/05_drive_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_driving_school.jpg" alt="教習所" width="200" height="200"><b>&#9654;</b><span>教習所</span></a>
<a href="../articles/assets/poc/poc_ttc_rss/06_approach_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_ttc_rss.jpg" alt="衝突時間と安全距離" width="200" height="200"><b>&#9654;</b><span>衝突時間と安全距離</span></a>
<a href="../articles/assets/poc/poc_world_terrain/06_drive_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_world_terrain.jpg" alt="世界を広げる" width="200" height="200"><b>&#9654;</b><span>世界を広げる</span></a>
<a href="../articles/assets/poc/poc_driving_longitudinal/01_drive_with_time.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_driving_longitudinal.jpg" alt="慣性と坂" width="200" height="200"><b>&#9654;</b><span>慣性と坂</span></a>
<a href="../articles/assets/poc/poc_driving_weather/01_sun_day.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_driving_weather.jpg" alt="太陽と天気" width="200" height="200"><b>&#9654;</b><span>太陽と天気</span></a>
<a href="../articles/assets/poc/poc_driving_endless_map/01_minimap_stream.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_driving_endless_map.jpg" alt="終わらない地図" width="200" height="200"><b>&#9654;</b><span>終わらない地図</span></a>
<a href="../articles/assets/poc/poc_driving_traffic/01_dashcam_occlusion.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_driving_traffic.jpg" alt="交通と死角" width="200" height="200"><b>&#9654;</b><span>交通と死角</span></a>
<a href="../articles/assets/poc/poc_driving_decisions/01_decisions_mirrors_ambulance.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_driving_decisions.jpg" alt="判断の場面" width="200" height="200"><b>&#9654;</b><span>判断の場面</span></a>
<a href="../articles/assets/poc/poc_driving_lateral/01_lateral_dashcam.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_driving_lateral.jpg" alt="横の運動" width="200" height="200"><b>&#9654;</b><span>横の運動</span></a>
<a href="../articles/assets/poc/poc_driving_humanoids/03_humanoids_crossing.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_driving_humanoids.jpg" alt="横断歩道の人型" width="200" height="200"><b>&#9654;</b><span>横断歩道の人型</span></a>
<a href="../articles/assets/poc/poc_driving_crossing/01_crossing_dashcam.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_driving_crossing.jpg" alt="踏切と交差点" width="200" height="200"><b>&#9654;</b><span>踏切と交差点</span></a>
<a href="../articles/assets/poc/poc_driving_pass/01_overtake_dashcam.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_driving_pass.jpg" alt="追越しと死角" width="200" height="200"><b>&#9654;</b><span>追越しと死角</span></a>
</div>
</details>

<details class="vall"><summary><b>数学の絵</b> (7)</summary>
<div class="vg vs">
<a href="../articles/assets/poc/poc_one_stroke_epicycles/07_epicycles.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_one_stroke_epicycles.jpg" alt="一筆書きと周転円" width="200" height="200"><b>&#9654;</b><span>一筆書きと周転円</span></a>
<a href="../articles/assets/poc/poc_complex_plane_fields/01_rational.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_complex_plane_fields.jpg" alt="複素平面を面で" width="200" height="200"><span>複素平面を面で</span></a>
<a href="../articles/assets/poc/poc_theorems_as_pictures/01_apollonian.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_theorems_as_pictures.jpg" alt="定理が門になる図" width="200" height="200"><span>定理が門になる図</span></a>
<a href="../articles/assets/poc/poc_beats_fringes_and_screens/01_membrane.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_beats_fringes_and_screens.jpg" alt="うなりは一つ" width="200" height="200"><span>うなりは一つ</span></a>
<a href="../articles/assets/poc/poc_what_a_picture_cannot_check/01_rk4.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_what_a_picture_cannot_check.jpg" alt="絵で確かめられない" width="200" height="200"><span>絵で確かめられない</span></a>
<a href="../articles/assets/poc/poc_illusions_and_perpetual_drawing/14_loop.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_illusions_and_perpetual_drawing.jpg" alt="無限に描く絵" width="200" height="200"><b>&#9654;</b><span>無限に描く絵</span></a>
<a href="../articles/assets/poc/poc_calipers_under_illusion/01_caliper_on_cafe_wall.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="thumbs/all/poc_calipers_under_illusion.jpg" alt="錯視で測定器診断" width="200" height="200"><span>錯視で測定器診断</span></a>
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

## 何が見えるか・測った数字

数字はどれも、各 PoC が仕込んだ真値(閉形式・解析解・公表値)に対する実測で、PoC を実行すると同じ値が印字されます。

<div class="vl" markdown="1">

**画像検査・外観計測**

- [薄い傷の検出限界](../articles/assets/poc/poc_real_defect_floor/02_defect_floor_sweep.gif) (GIF): 実写の地(レンガ)と、雑音の量をそろえた合成の地に、同じ欠陥を濃くしながら仕込む。 **雑音の量をそろえても、実写の地の検出限界は合成の 2.03〜3.47 倍(位置・振幅が既知の欠陥に対して)。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_defect_floor.py)
- [動的輪郭](../articles/assets/poc/poc_active_contours/06_u_shape_snakes.mp4) (動画): U 字の凹部に、古典の snake(赤)は入れず、GVF(青)は奥まで入る。緑が真の縁。 **外力だけを GVF に替えると Dice 0.993(真の縁に対して)。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_active_contours.py)
- [DIC ひずみ](../articles/assets/poc/poc_dic_strain/05_tensile_ramp.mp4) (動画): 引張試験の荷重を上げながら、スペックル画像からひずみ地図を読む(試験機は同時に 2 度回る)。 **真のひずみ 3000 µε。微小ひずみは回転で 2341 µε と過小、Green-Lagrange は 2961 µε(理論 3005 µε)。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dic_strain.py)

**三次元計測・幾何処理**

- [焦点合成](../articles/assets/poc/poc_focus_stacking/05_focus_sweep.mp4) (動画): 焦点を 17 枚掃引しながら、全焦点画像と距離画像が育っていく。 **全焦点 PSNR 33.69 dB(中央の 1 枚は 28.52 dB)、深度誤差 0.467 mm(テクスチャあり)。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_focus_stacking.py)
- [点群の位置合わせ](../articles/assets/poc/poc_registration_basin/05_icp_basin_iterations.mp4) (動画): 初期の回転ずれ 30 / 90 / 150 度から、ICP を 1 反復ずつ動かす。 **60 反復後の回転誤差: 30 度と 90 度は 0.6 度(成功)、150 度は 179.5 度(失敗)。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_registration_basin.py)
- [堆積物の体積](../articles/assets/poc/poc_stockpile_volume/07_scan_orbit.mp4) (動画): 山の周りを回りながら、3-D スキャンの位置を 1 → 3 か所に増やす。色は補間面と真の面の差。 **在庫量の誤差は +17.20 % → +0.05 %(真の底面、体積の真値は閉形式 3572.6089 m³)。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_stockpile_volume.py)

**X線CT・ボリューム処理**

- [CT 再構成](../articles/assets/poc/poc_ct_fidelity/01_recon_sweep.png) (図): Shepp-Logan ファントムを投影 180 本 → 12 本で撮り直して再構成する。 **12 本の FBP は RMSE 0.2576 で空白画像 0.2420 にも負ける。質量の検算で −3.34 % の欠損を見つけ、−0.0099 % に直した。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_fidelity.py)
- [CT のボイド](../articles/assets/poc/poc_ct_void_morphology/13_section_sweep.mp4) (動画): ボイド率がほぼ同じ 2 条件の接合層を、断面を掃引しながら 3-D で回す(動画 4.3 MB)。 **ボイド率は 2.46 % 対 2.63 % なのに、界面からの距離の中央値は 60.0 µm 対 10.0 µm。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_void_morphology.py)

**光学・干渉・偏光**

- [白色干渉の段差](../articles/assets/poc/poc_interferometry_step/05_step_sweep.mp4) (動画): 仕込む段差を 0 → 0.90 µm に増やし、包絡線法と位相シフト法で測る。 **雑音 1 % で偏り 2.4 nm 以内(段差 50〜500 nm)。位相シフト法は 0.153 µm で λ/2 跳ぶ。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_interferometry_step.py)
- [偏光で鏡面除去](../articles/assets/poc/poc_polarization_specular/03_separation.png) (図): 偏光で鏡面反射を剥がした結果と、残った誤差の形。 **拡散成分の誤差は閉形式 R_p·E と一致し、ブリュースター角 56.31 度で 0。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_polarization_specular.py)
- [光弾性の応力](../articles/assets/poc/poc_photoelasticity/03_load_and_isoclinics.mp4) (動画): 円板に荷重をかけると縞が湧き出し、偏光子を回すと等傾線が動く。 **中心の縞次数 2.38(閉形式どおり)。op の偏光系は教科書の式と最大差 2.2e-16。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_photoelasticity.py)

**熱・音響・時系列**

- [熱画像の欠陥深さ](../articles/assets/poc/poc_thermography_ndt/02_depth_map.png) (図): フラッシュ加熱後の表面温度から、16 個の剥離の深さを読んだ地図。 **深さ 0.5 mm・直径 2 mm の欠陥は、当てはめの時間窓 25 秒で +612 %、4 秒に切ると −9 %。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_thermography_ndt.py)
- [微小振動の拡大](../articles/assets/poc/poc_motion_magnification/05_magnify_video.mp4) (動画): 0.1 px で揺れる表面。左が生の映像、右が 10 倍に拡大した映像。 **真の振幅 0.1000 px に対し、生から 0.10012、拡大後から 0.10013 px。拡大は見せる道具で、測定は良くならない。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_motion_magnification.py)

**ロボット・空間知覚**

- [複眼の光場](../articles/assets/poc/poc_compound_eye/02_compound_eye_superposition.png) (図): 個眼アレイを光場センサとして合成し、同じ点を N 個眼で重ねる。 この光場の後段をハエの配線図(コネクトーム)で処理するのが次の課題 —— 下のコネクトームの展示へ続く。 **SNR 利得は N=5 で 2.25(√5 = 2.24)、N=49 で 5.33(√49 = 7.00)。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_compound_eye.py)
- [ペグ挿入](../articles/assets/poc/poc_pegsim_insertion/04_pegsim_insert_corrected.gif) (GIF): 手首カメラで穴の位置を測って寄せ、柔らかい手首でペグを入れる(MuJoCo)。 **サーボ 7 回で真のずれ 2.24 → 0.03 mm。補正ありの挿入は 12 / 12 成功。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pegsim_insertion.py)
- [エアホッケー](../articles/assets/poc/poc_air_hockey_intercept/02_airhockey_prediction_cone_narrows.gif) (GIF): 粗いカメラでパックを追い、守備線との交点を予測する。コマが増えるほど予測の帯が細る。 **交点の 95 % 帯は N = 3 コマで 145 mm → N = 16 コマで 7 mm。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_air_hockey_intercept.py)
- [視触覚センサ](../articles/assets/poc/poc_tacsim_elastic_membrane/03_tacsim_force_sweep.gif) (GIF): 弾性膜を球で押す荷重を上げ、膜の画像から接触半径を読む。 **Hertz の閉形式に対し、接触半径の誤差 0.05〜0.26 %、荷重の誤差 0.14〜0.79 %(0.02〜0.12 N)。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_tacsim_elastic_membrane.py)

**卓球・運動計測**

- [卓球の跳ね](../articles/assets/poc/poc_table_tennis_bounce/01_drop_test.mp4) (動画): ITTF の台の試験: 30 cm から球を落とし、跳ねた高さを動画から読む。 **動画から読んだ跳ねの高さ 23.0 cm(世界の真値 23.0 cm)。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_table_tennis_bounce.py)
- [卓球の回転](../articles/assets/poc/poc_table_tennis_spin/01_side_three_serves.mp4) (動画): 同じ速さ・向きで打った 3 本: トップスピンは沈み、バックスピンは浮く。 **着地点 x = 0.49 / 0.75 / 1.12 m。曲がり方から読んだ回転で先読みした着地点は 4 本とも真値と 2 cm 以内。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_table_tennis_spin.py)
- [ラリーと読み誤差](../articles/assets/poc/poc_table_tennis_rally_loop/02_height_misread.mp4) (動画): 球の高さを 5 cm 高く読むと、狙いの計算は低い弾道を選び、球は手前に落ちる。 **狙いより 10.2 cm 手前に落ちる。打つ前の一次予測 2.06 × 5 cm = 10.3 cm。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_table_tennis_rally_loop.py)

**自動運転**

- [交通と死角](../articles/assets/poc/poc_driving_traffic/01_dashcam_occlusion.mp4) (動画): 路肩駐車の陰から子どもが走り出る。背景との差(学習なし)で検知して止まる。 **真値 t = 7.30 s に検知(遅れ 0.133 s)、子どもの線の 7.09 m 手前で停止。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_driving_traffic.py)
- [踏切と交差点](../articles/assets/poc/poc_driving_crossing/01_crossing_dashcam.mp4) (動画): 踏切の直前で止まり、警報の間は待ち、左右を見て渡る(運転者の目)。 **規則どおりの 240 人は違反 0、列車到着時に線路の上 0 人。警報中に入る版は 157 人が違反、うち 23 人が線路の上。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_driving_crossing.py)
- [カーブミラー](../articles/assets/poc/poc_driving_pass/03_mirror_tjunction.mp4) (動画): 見通しの悪い T 字路で、凸面のカーブミラーに映る車を光線追跡で描き、距離を読む。 **鏡から 29 m の車が、像の大きさで読むと 139 m 先に見える(閉形式の縦の読み 140 m)。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_driving_pass.py)
- [衝突時間と RSS](../articles/assets/poc/poc_ttc_rss/06_approach_gif.gif) (GIF): 対向車の光学流から衝突までの時間 τ を出し、停車車両には RSS の安全距離で止まる。 **RSS が「危険」を出した t = 6.0 s に制動し、10.25 m 手前で停止。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ttc_rss.py)

**コネクトーム・神経**

- [複眼から脳へ](../articles/assets/poc/poc_eye_to_brain/01_eye_sweep.gif) (GIF): ハエの右眼の個眼 1 つ分の刺激を眼の一行に沿って動かし、脳の配線図(コネクトーム)に入れる(GIF 4.4 MB)。 **刺激した柱の位置と応答の重心の相関: コネクトーム −0.92、次数保存シャッフル +0.01。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_eye_to_brain.py)
- [ハエの脳の波](../articles/assets/poc/poc_malecns_activity_wave/01_activity_wave_connectome_vs_shuffle.gif) (GIF): 右の視葉への刺激が、実際の配線(左)と、次数を保って繋ぎ替えた配線(右)を伝わる。 **実配線では活動の平均距離が 88 → 230 µm と 17 步かけて伸びる。繋ぎ替えでは 3 步で 300 µm に散る。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_malecns_activity_wave.py)
- [マウス視覚野の波](../articles/assets/poc/poc_microns_brain_wave/04_wave_on_wiring.gif) (GIF): 校正済みの軸索 148 本の実測応答を、マウス視覚野 1 mm³ の実配線に流す(MICrONS)。 **実測との相関は実配線 0.085、次数保存シャッフル 0.048。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_microns_brain_wave.py)

**ロボットの目(Fullseye が知覚を担当)**

- [ヒューマノイドの両眼](../articles/assets/media/evis_stereo_fullseye.mp4) (動画): 筋骨格ヒューマノイドが箸で豆を打つ場面を、自分の両眼(瞳孔間距離 64 mm)で撮り、Fullseye がステレオ視差 → 深度を毎コマ計算する。 **豆までの距離の誤差は中央値 0.66 %・最大 1.91 %(読める 229 / 241 コマ)。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/tools/gen_evis_media.py)
- [箸先カメラの豆追跡](../articles/assets/media/evis_bean_track_fullseye.mp4) (動画): 同じ場面の箸先カメラの映像で、Fullseye が豆を検出して追う。 **見えている 163 コマすべてで検出(163 / 163)、重心の誤差は真値比で中央値 0.10 px。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/tools/gen_evis_media.py)

</div>

## Fullseye とは

光学設計や三次元計測などのセンシングを含む物理シミュレーションと古典画像処理を、MCP と RAG で AI に渡し、課題ごとに組み合わせを考えさせ、型整合性と真値つき評価で確かめながら対話的に課題を解く基盤です。オープンソース(Apache-2.0)。

<details markdown="1">
<summary><b>試してみる</b> (Python 3.11)</summary>

```
pip install fullseye
git clone https://github.com/furuse-kazufumi/fullseye
cd fullseye
python examples/poc_focus_stacking.py
```

焦点合成の PoC が約 20 秒で走り、真値に対する数字と `PASS` を印字します。図は `out/figures/poc_focus_stacking/` に書かれます。

</details>

<details markdown="1">
<summary><b>リンク</b></summary>

- [GitHub(ソースコード)](https://github.com/furuse-kazufumi/fullseye)
- [ギャラリー(全部の図)](../GALLERY.md)
- [演算子を探す・AI(RAG)から使う](../AI_RAG_GUIDE.md) · [MCP から使う](../MCP.md)
- [ドキュメント索引](../README.md)

</details>

<details markdown="1">
<summary><b>論文情報</b></summary>

- **題目**: Fullseye：型付き演算子と物理シミュレーションに基づく画像検査・三次元計測基盤
- **著者**: 古瀬 和文(個人研究者)
- **発表**: ViEW2026 ビジョン技術の実利用ワークショップ
- **論文 PDF**: 2026-11-26 以降に掲載

**概要**: 画像検査・三次元計測の処理を，入出力のデータ型を宣言した演算子の連鎖として組み立て，物理・撮像シミュレーションで作った真値に対して定量評価し，処理手順・評価・失敗条件を記録して再利用できるオープンソース基盤Fullseyeを提案する．約3,000の型付き演算子，型の不整合を実行前に退ける検査，多言語の演算子検索（RAG），真値つきの200本超の実証プログラムからなり，代表例の定量評価と，合成・実測・実機の検証段階の区別について報告する．

</details>
