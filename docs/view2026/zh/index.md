<div class="vlang" markdown="1">

[日本語](../index.md) · [English](../en/index.md) · **简体中文** · [繁體中文](../tw/index.md) · [한국어](../ko/index.md) · [Deutsch](../de/index.md) · [हिन्दी](../hi/index.md)

</div>

# Fullseye — ViEW2026

把物理仿真与图像处理交给 AI 组合,并用真值验证。

点按图块即可打开视频或图(▶ = 动态)。

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

## 精选

<div class="vg">
<a href="../../articles/assets/poc/poc_real_defect_floor/02_defect_floor_sweep.gif"><img src="../thumbs/poc_real_defect_floor.jpg" alt="薄缺陷检出极限" loading="lazy" width="320" height="320"><b>&#9654;</b><span>薄缺陷检出极限</span></a>
<a href="../../articles/assets/poc/poc_active_contours/06_u_shape_snakes.mp4"><img src="../thumbs/poc_active_contours.jpg" alt="主动轮廓" loading="lazy" width="320" height="320"><b>&#9654;</b><span>主动轮廓</span></a>
<a href="../../articles/assets/poc/poc_dic_strain/05_tensile_ramp.mp4"><img src="../thumbs/poc_dic_strain.jpg" alt="DIC 应变" loading="lazy" width="320" height="320"><b>&#9654;</b><span>DIC 应变</span></a>
<a href="../../articles/assets/poc/poc_focus_stacking/05_focus_sweep.mp4"><img src="../thumbs/poc_focus_stacking.jpg" alt="景深合成" loading="lazy" width="320" height="320"><b>&#9654;</b><span>景深合成</span></a>
<a href="../../articles/assets/poc/poc_registration_basin/05_icp_basin_iterations.mp4"><img src="../thumbs/poc_registration_basin.jpg" alt="点云配准" loading="lazy" width="320" height="320"><b>&#9654;</b><span>点云配准</span></a>
<a href="../../articles/assets/poc/poc_stockpile_volume/07_scan_orbit.mp4"><img src="../thumbs/poc_stockpile_volume.jpg" alt="料堆体积" loading="lazy" width="320" height="320"><b>&#9654;</b><span>料堆体积</span></a>
<a href="../../articles/assets/poc/poc_ct_fidelity/01_recon_sweep.png"><img src="../thumbs/poc_ct_fidelity.jpg" alt="CT 重建" loading="lazy" width="320" height="320"><span>CT 重建</span></a>
<a href="../../articles/assets/poc/poc_ct_void_morphology/13_section_sweep.mp4"><img src="../thumbs/poc_ct_void_morphology.jpg" alt="CT 空洞" loading="lazy" width="320" height="320"><b>&#9654;</b><span>CT 空洞</span></a>
<a href="../../articles/assets/poc/poc_interferometry_step/05_step_sweep.mp4"><img src="../thumbs/poc_interferometry_step.jpg" alt="白光干涉台阶" loading="lazy" width="320" height="320"><b>&#9654;</b><span>白光干涉台阶</span></a>
<a href="../../articles/assets/poc/poc_polarization_specular/03_separation.png"><img src="../thumbs/poc_polarization_specular.jpg" alt="偏振去镜面反射" loading="lazy" width="320" height="320"><span>偏振去镜面反射</span></a>
<a href="../../articles/assets/poc/poc_photoelasticity/03_load_and_isoclinics.mp4"><img src="../thumbs/poc_photoelasticity.jpg" alt="光弹性应力" loading="lazy" width="320" height="320"><b>&#9654;</b><span>光弹性应力</span></a>
<a href="../../articles/assets/poc/poc_thermography_ndt/02_depth_map.png"><img src="../thumbs/poc_thermography_ndt.jpg" alt="热成像缺陷深度" loading="lazy" width="320" height="320"><span>热成像缺陷深度</span></a>
<a href="../../articles/assets/poc/poc_motion_magnification/05_magnify_video.mp4"><img src="../thumbs/poc_motion_magnification.jpg" alt="微振动放大" loading="lazy" width="320" height="320"><b>&#9654;</b><span>微振动放大</span></a>
<a href="../../articles/assets/poc/poc_table_tennis_bounce/01_drop_test.mp4"><img src="../thumbs/poc_table_tennis_bounce.jpg" alt="乒乓球弹跳" loading="lazy" width="320" height="320"><b>&#9654;</b><span>乒乓球弹跳</span></a>
<a href="../../articles/assets/poc/poc_compound_eye/02_compound_eye_superposition.png"><img src="../thumbs/poc_compound_eye.jpg" alt="复眼光场" loading="lazy" width="320" height="320"><span>复眼光场</span></a>
<a href="../../articles/assets/poc/poc_pegsim_insertion/04_pegsim_insert_corrected.gif"><img src="../thumbs/poc_pegsim_insertion.jpg" alt="轴孔装配" loading="lazy" width="320" height="320"><b>&#9654;</b><span>轴孔装配</span></a>
<a href="../../articles/assets/poc/poc_air_hockey_intercept/02_airhockey_prediction_cone_narrows.gif"><img src="../thumbs/poc_air_hockey_intercept.jpg" alt="空气曲棍球" loading="lazy" width="320" height="320"><b>&#9654;</b><span>空气曲棍球</span></a>
<a href="../../articles/assets/poc/poc_tacsim_elastic_membrane/03_tacsim_force_sweep.gif"><img src="../thumbs/poc_tacsim_elastic_membrane.jpg" alt="视触觉传感器" loading="lazy" width="320" height="320"><b>&#9654;</b><span>视触觉传感器</span></a>
<a href="../../articles/assets/poc/poc_table_tennis_spin/01_side_three_serves.mp4"><img src="../thumbs/poc_table_tennis_spin.jpg" alt="乒乓球旋转" loading="lazy" width="320" height="320"><b>&#9654;</b><span>乒乓球旋转</span></a>
<a href="../../articles/assets/poc/poc_table_tennis_rally_loop/02_height_misread.mp4"><img src="../thumbs/poc_table_tennis_rally_loop.jpg" alt="回合与读取误差" loading="lazy" width="320" height="320"><b>&#9654;</b><span>回合与读取误差</span></a>
<a href="../../articles/assets/poc/poc_driving_traffic/01_dashcam_occlusion.mp4"><img src="../thumbs/poc_driving_traffic.jpg" alt="交通与盲区" loading="lazy" width="320" height="320"><b>&#9654;</b><span>交通与盲区</span></a>
<a href="../../articles/assets/poc/poc_driving_crossing/01_crossing_dashcam.mp4"><img src="../thumbs/poc_driving_crossing.jpg" alt="道口与路口" loading="lazy" width="320" height="320"><b>&#9654;</b><span>道口与路口</span></a>
<a href="../../articles/assets/poc/poc_driving_pass/03_mirror_tjunction.mp4"><img src="../thumbs/poc_driving_pass.jpg" alt="道路反射镜" loading="lazy" width="320" height="320"><b>&#9654;</b><span>道路反射镜</span></a>
<a href="../../articles/assets/poc/poc_ttc_rss/06_approach_gif.gif"><img src="../thumbs/poc_ttc_rss.jpg" alt="碰撞时间与 RSS" loading="lazy" width="320" height="320"><b>&#9654;</b><span>碰撞时间与 RSS</span></a>
<a href="../../articles/assets/poc/poc_eye_to_brain/01_eye_sweep.gif"><img src="../thumbs/poc_eye_to_brain.jpg" alt="复眼到大脑" loading="lazy" width="320" height="320"><b>&#9654;</b><span>复眼到大脑</span></a>
<a href="../../articles/assets/poc/poc_malecns_activity_wave/01_activity_wave_connectome_vs_shuffle.gif"><img src="../thumbs/poc_malecns_activity_wave.jpg" alt="苍蝇脑电波" loading="lazy" width="320" height="320"><b>&#9654;</b><span>苍蝇脑电波</span></a>
<a href="../../articles/assets/poc/poc_microns_brain_wave/04_wave_on_wiring.gif"><img src="../thumbs/poc_microns_brain_wave.jpg" alt="小鼠视皮层波" loading="lazy" width="320" height="320"><b>&#9654;</b><span>小鼠视皮层波</span></a>
<a href="../../articles/assets/media/evis_stereo_fullseye.mp4"><img src="../thumbs/evis_stereo_depth.jpg" alt="人形机器人双眼" loading="lazy" width="320" height="320"><b>&#9654;</b><span>人形机器人双眼</span></a>
<a href="../../articles/assets/media/evis_bean_track_fullseye.mp4"><img src="../thumbs/evis_bean_track.jpg" alt="筷尖相机追踪豆子" loading="lazy" width="320" height="320"><b>&#9654;</b><span>筷尖相机追踪豆子</span></a>
</div>

## 系列文章 (Qiita 上的英文文章)

<div class="vser">
<a href="https://qiita.com/furuse-kazufumi/items/8a8f23e53b19ee8cdc10"><img src="../thumbs/series_museum.gif" alt="纸上的测量馆" loading="lazy" width="480" height="270"><strong>纸上的测量馆</strong><span>自己植入真值的 PoC 展馆</span></a>
<a href="https://qiita.com/furuse-kazufumi/items/a82bf9f341cc4f04ca75"><img src="../thumbs/series_table_tennis.gif" alt="乒乓球" loading="lazy" width="480" height="270"><strong>乒乓球</strong><span>从视频测量弹跳与摩擦</span></a>
<a href="https://qiita.com/furuse-kazufumi/items/05de90f4d316cd7c681c"><img src="../thumbs/series_driving.gif" alt="自动驾驶" loading="lazy" width="480" height="270"><strong>自动驾驶</strong><span>用定理与第二实现评分</span></a>
<a href="https://qiita.com/furuse-kazufumi/items/638f0b0aa7865e17c67c"><img src="../thumbs/series_connectome.gif" alt="连接组(脑接线图)" loading="lazy" width="480" height="270"><strong>连接组(脑接线图)</strong><span>把苍蝇视觉模型装到身体上测量</span></a>
<a href="https://qiita.com/furuse-kazufumi/items/569720dbae0c6471c96e"><img src="../thumbs/series_humanoid.gif" alt="人形机器人运动会" loading="lazy" width="480" height="270"><strong>人形机器人运动会</strong><span>由图像处理担任裁判的家庭运动会</span></a>
</div>

## 全部看

PoC 218 个,另有机器人之眼 4 个。展开分组即可加载缩略图。

<noscript><p><a href="../../GALLERY.en.html">(没有 JavaScript 时,可在图库页面查看全部图。)</a></p></noscript>

<details class="vall"><summary><b>机器人之眼(由 Fullseye 负责感知)</b> (4)</summary>
<div class="vg vs">
<a href="../../articles/assets/media/evis_stereo_fullseye.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/evis_stereo_depth.jpg" alt="人形机器人双眼" width="200" height="200"><b>&#9654;</b><span>人形机器人双眼</span></a>
<a href="../../articles/assets/media/evis_bean_track_fullseye.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/evis_bean_track.jpg" alt="筷尖相机追踪豆子" width="200" height="200"><b>&#9654;</b><span>筷尖相机追踪豆子</span></a>
<a href="../../view2026/media/evis_fullseye_walk.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/evis_walk_rgb_depth_dvs.jpg" alt="以 RGB、深度、DVS 看步行" width="200" height="200"><b>&#9654;</b><span>以 RGB、深度、DVS 看步行</span></a>
<a href="../../view2026/media/vision_adaptive_walk.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/walker2d_terrain_vision.jpg" alt="看台阶选步态" width="200" height="200"><span>看台阶选步态</span></a>
</div>
</details>

<details class="vall"><summary><b>工业检测</b> (32)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_barcode_1d/01_misread_split.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_barcode_1d.jpg" alt="一维条码" width="200" height="200"><span>一维条码</span></a>
<a href="../../articles/assets/poc/poc_battery_electrode_tortuosity/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_battery_electrode_tortuosity.jpg" alt="电极曲折度" width="200" height="200"><span>电极曲折度</span></a>
<a href="../../articles/assets/poc/poc_bearing_diagnosis/01_envelope_vs_raw.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_bearing_diagnosis.jpg" alt="轴承故障诊断" width="200" height="200"><span>轴承故障诊断</span></a>
<a href="../../articles/assets/poc/poc_bump_coplanarity/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_bump_coplanarity.jpg" alt="凸点共面度" width="200" height="200"><span>凸点共面度</span></a>
<a href="../../articles/assets/poc/poc_crack_width/01_width_sweep.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_crack_width.jpg" alt="裂缝宽度" width="200" height="200"><span>裂缝宽度</span></a>
<a href="../../articles/assets/poc/poc_fabric_defect/01_auc_by_type.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_fabric_defect.jpg" alt="织物缺陷" width="200" height="200"><span>织物缺陷</span></a>
<a href="../../articles/assets/poc/poc_leak_localization/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_leak_localization.jpg" alt="声学漏水定位" width="200" height="200"><span>声学漏水定位</span></a>
<a href="../../articles/assets/poc/poc_machine_condition_fusion/01_scene_machine.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_machine_condition_fusion.jpg" alt="设备维护融合" width="200" height="200"><span>设备维护融合</span></a>
<a href="../../articles/assets/poc/poc_matrix_code_reading/01_symbol_and_errors.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_matrix_code_reading.jpg" alt="矩阵码读取" width="200" height="200"><span>矩阵码读取</span></a>
<a href="../../articles/assets/poc/poc_moire_screen/01_failure_split_plot.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_moire_screen.jpg" alt="显示屏摩尔纹" width="200" height="200"><span>显示屏摩尔纹</span></a>
<a href="../../articles/assets/poc/poc_print_registration/01_plates.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_print_registration.jpg" alt="印刷套准" width="200" height="200"><span>印刷套准</span></a>
<a href="../../articles/assets/poc/poc_real_defect_floor/02_defect_floor_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_defect_floor.jpg" alt="薄缺陷极限" width="200" height="200"><b>&#9654;</b><span>薄缺陷极限</span></a>
<a href="../../articles/assets/poc/poc_real_texture_invariance/01_textures.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_texture_invariance.jpg" alt="实拍纹理旋转" width="200" height="200"><span>实拍纹理旋转</span></a>
<a href="../../articles/assets/poc/poc_recycling_sorting/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_recycling_sorting.jpg" alt="废弃物分选" width="200" height="200"><span>废弃物分选</span></a>
<a href="../../articles/assets/poc/poc_solar_el_inspection/01_zero_point_map.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_solar_el_inspection.jpg" alt="太阳能 EL" width="200" height="200"><span>太阳能 EL</span></a>
<a href="../../articles/assets/poc/poc_solder_fillet_aoi/01_ring_lut.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_solder_fillet_aoi.jpg" alt="焊锡 AOI" width="200" height="200"><span>焊锡 AOI</span></a>
<a href="../../articles/assets/poc/poc_spc/01_spc_xbar_chart.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_spc.jpg" alt="统计过程控制" width="200" height="200"><span>统计过程控制</span></a>
<a href="../../articles/assets/poc/poc_mt_hidden_fault/01_mt_hidden_cloud.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_mt_hidden_fault.jpg" alt="MT 法异常检测" width="200" height="200"><span>MT 法异常检测</span></a>
<a href="../../articles/assets/poc/poc_text_region_truth/01_text_region_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_text_region_truth.jpg" alt="文字区域检测" width="200" height="200"><span>文字区域检测</span></a>
<a href="../../articles/assets/poc/poc_thermal_drift_metrology/01_separate_drifts.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_thermal_drift_metrology.jpg" alt="相机热漂移" width="200" height="200"><span>相机热漂移</span></a>
<a href="../../articles/assets/poc/poc_thermal_radiometry/01_floor.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_thermal_radiometry.jpg" alt="热像与温度" width="200" height="200"><span>热像与温度</span></a>
<a href="../../articles/assets/poc/poc_thermography_ndt/01_depth_table.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_thermography_ndt.jpg" alt="热成像缺陷深度" width="200" height="200"><span>热成像缺陷深度</span></a>
<a href="../../articles/assets/poc/poc_veiling_glare/01_verdict.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_veiling_glare.jpg" alt="杂散光" width="200" height="200"><span>杂散光</span></a>
<a href="../../articles/assets/poc/poc_emva1288_sensor/01_photon_transfer.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_emva1288_sensor.jpg" alt="EMVA 1288 测量" width="200" height="200"><b>&#9654;</b><span>EMVA 1288 测量</span></a>
<a href="../../articles/assets/poc/poc_web_roll_periodicity/01_scene_web.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_web_roll_periodicity.jpg" alt="传送辊缺陷" width="200" height="200"><span>传送辊缺陷</span></a>
<a href="../../articles/assets/poc/poc_weld_bead_profile/01_laser_images.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_weld_bead_profile.jpg" alt="焊道截面" width="200" height="200"><span>焊道截面</span></a>
<a href="../../articles/assets/poc/poc_weld_bead_scan_angle/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_weld_bead_scan_angle.jpg" alt="焊道扫描" width="200" height="200"><span>焊道扫描</span></a>
<a href="../../articles/assets/poc/poc_weld_radiograph_porosity/01_scene_radiograph.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_weld_radiograph_porosity.jpg" alt="焊缝气孔" width="200" height="200"><span>焊缝气孔</span></a>
<a href="../../articles/assets/poc/poc_glyph_typo_detection/01_sign_before_after.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_glyph_typo_detection.jpg" alt="图像错字检测" width="200" height="200"><span>图像错字检测</span></a>
<a href="../../articles/assets/poc/poc_print_layer_inspection/01_slice_stack.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_print_layer_inspection.jpg" alt="3D 打印层检测" width="200" height="200"><span>3D 打印层检测</span></a>
<a href="../../articles/assets/poc/poc_agv_fleet/01_agv_naive_vs_adg.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_agv_fleet.jpg" alt="AGV 仓库" width="200" height="200"><b>&#9654;</b><span>AGV 仓库</span></a>
<a href="../../articles/assets/poc/poc_am_thermal_to_ct/01_melt_pool_frames.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_am_thermal_to_ct.jpg" alt="增材制造与 CT" width="200" height="200"><b>&#9654;</b><span>增材制造与 CT</span></a>
</div>
</details>

<details class="vall"><summary><b>尺寸与形状测量</b> (36)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_aoi_ct_traceability/01_aoi_and_ct.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_aoi_ct_traceability.jpg" alt="AOI 与 CT 对应" width="200" height="200"><span>AOI 与 CT 对应</span></a>
<a href="../../articles/assets/poc/poc_asbuilt_wall_deviation/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_asbuilt_wall_deviation.jpg" alt="竣工墙面偏差" width="200" height="200"><span>竣工墙面偏差</span></a>
<a href="../../articles/assets/poc/poc_battery_electrode_breathing/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_battery_electrode_breathing.jpg" alt="电极呼吸" width="200" height="200"><span>电极呼吸</span></a>
<a href="../../articles/assets/poc/poc_bilateral_asymmetry/01_floor_vs_spacing.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_bilateral_asymmetry.jpg" alt="左右不对称" width="200" height="200"><span>左右不对称</span></a>
<a href="../../articles/assets/poc/poc_dic_strain/05_tensile_ramp.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dic_strain.jpg" alt="DIC 应变" width="200" height="200"><b>&#9654;</b><span>DIC 应变</span></a>
<a href="../../articles/assets/poc/poc_die_tilt_tsv_overlay/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_die_tilt_tsv_overlay.jpg" alt="芯片倾斜与 TSV" width="200" height="200"><span>芯片倾斜与 TSV</span></a>
<a href="../../articles/assets/poc/poc_dimensional_inspection/01_slot_bias.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dimensional_inspection.jpg" alt="零件尺寸检测" width="200" height="200"><span>零件尺寸检测</span></a>
<a href="../../articles/assets/poc/poc_fiber_orientation/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_fiber_orientation.jpg" alt="纤维取向" width="200" height="200"><span>纤维取向</span></a>
<a href="../../articles/assets/poc/poc_gear_tooth_metrology/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_gear_tooth_metrology.jpg" alt="齿轮齿形" width="200" height="200"><span>齿轮齿形</span></a>
<a href="../../articles/assets/poc/poc_interferometry_step/05_step_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_interferometry_step.jpg" alt="白光干涉台阶" width="200" height="200"><b>&#9654;</b><span>白光干涉台阶</span></a>
<a href="../../articles/assets/poc/poc_metal_grain_size/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_metal_grain_size.jpg" alt="晶粒度" width="200" height="200"><span>晶粒度</span></a>
<a href="../../articles/assets/poc/poc_multibeam_bathymetry/17_survey.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_multibeam_bathymetry.jpg" alt="多波束测深" width="200" height="200"><b>&#9654;</b><span>多波束测深</span></a>
<a href="../../articles/assets/poc/poc_particle_sizing/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_particle_sizing.jpg" alt="粒度分布" width="200" height="200"><span>粒度分布</span></a>
<a href="../../articles/assets/poc/poc_photoelasticity/03_load_and_isoclinics.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_photoelasticity.jpg" alt="光弹性应力" width="200" height="200"><b>&#9654;</b><span>光弹性应力</span></a>
<a href="../../articles/assets/poc/poc_rail_corrugation/01_planted_components.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_rail_corrugation.jpg" alt="钢轨波磨" width="200" height="200"><span>钢轨波磨</span></a>
<a href="../../articles/assets/poc/poc_real_coin_metrology/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_coin_metrology.jpg" alt="实拍硬币" width="200" height="200"><span>实拍硬币</span></a>
<a href="../../articles/assets/poc/poc_screw_thread_metrology/01_zero_spectrum.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_screw_thread_metrology.jpg" alt="螺纹轮廓" width="200" height="200"><span>螺纹轮廓</span></a>
<a href="../../articles/assets/poc/poc_stockpile_volume/07_scan_orbit.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_stockpile_volume.jpg" alt="料堆体积" width="200" height="200"><b>&#9654;</b><span>料堆体积</span></a>
<a href="../../articles/assets/poc/poc_strain_history/05_history_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_strain_history.jpg" alt="蠕变应变" width="200" height="200"><b>&#9654;</b><span>蠕变应变</span></a>
<a href="../../articles/assets/poc/poc_surface_roughness/01_surface_components.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_surface_roughness.jpg" alt="表面粗糙度" width="200" height="200"><span>表面粗糙度</span></a>
<a href="../../articles/assets/poc/poc_tacsim_elastic_membrane/03_tacsim_force_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_tacsim_elastic_membrane.jpg" alt="视触觉传感器" width="200" height="200"><b>&#9654;</b><span>视触觉传感器</span></a>
<a href="../../articles/assets/poc/poc_tacsim_marker_shear/02_tacslip_stick_circle_shrinks.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_tacsim_marker_shear.jpg" alt="触觉剪切" width="200" height="200"><b>&#9654;</b><span>触觉剪切</span></a>
<a href="../../articles/assets/poc/poc_tactile_dipole_torque/02_tactorque_dipole_grows_with_M.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_tactile_dipole_torque.jpg" alt="触觉偶极子" width="200" height="200"><b>&#9654;</b><span>触觉偶极子</span></a>
<a href="../../articles/assets/poc/poc_granular_heap_repose/11_granular_datum_tilt_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_granular_heap_repose.jpg" alt="粉体堆" width="200" height="200"><b>&#9654;</b><span>粉体堆</span></a>
<a href="../../articles/assets/poc/poc_food_cutting_measure/01_cutting_track_force.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_food_cutting_measure.jpg" alt="食材切割" width="200" height="200"><b>&#9654;</b><span>食材切割</span></a>
<a href="../../articles/assets/poc/poc_tacdome_large_deformation/01_tacdome_press_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_tacdome_large_deformation.jpg" alt="穹顶指尖接触" width="200" height="200"><b>&#9654;</b><span>穹顶指尖接触</span></a>
<a href="../../articles/assets/poc/poc_polish_wipe_measure/01_polish_raster_wipe_coat.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_polish_wipe_measure.jpg" alt="研磨与擦拭" width="200" height="200"><b>&#9654;</b><span>研磨与擦拭</span></a>
<a href="../../articles/assets/poc/poc_powder_scoop_pour/03_scoop_stream_synthetic_frames.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_powder_scoop_pour.jpg" alt="粉体舀取与倾倒" width="200" height="200"><b>&#9654;</b><span>粉体舀取与倾倒</span></a>
<a href="../../articles/assets/poc/poc_powder_grinding_ae/07_psd_fining_during_grinding.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_powder_grinding_ae.jpg" alt="研钵粉碎" width="200" height="200"><b>&#9654;</b><span>研钵粉碎</span></a>
<a href="../../articles/assets/poc/poc_pxrd_phase_peel/01_phase_peel.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_pxrd_phase_peel.jpg" alt="X 射线衍射分相" width="200" height="200"><b>&#9654;</b><span>X 射线衍射分相</span></a>
<a href="../../articles/assets/poc/poc_dose_uniformity_from_grinding/01_cv_bias_decomposition.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dose_uniformity_from_grinding.jpg" alt="药量均匀性" width="200" height="200"><span>药量均匀性</span></a>
<a href="../../articles/assets/poc/poc_knife_tactile_toughness/06_cut_with_fingertip_pads.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_knife_tactile_toughness.jpg" alt="指尖握刀" width="200" height="200"><b>&#9654;</b><span>指尖握刀</span></a>
<a href="../../articles/assets/poc/poc_measurement_system_analysis/16_breakdown_movie.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_measurement_system_analysis.jpg" alt="量具 R&R" width="200" height="200"><b>&#9654;</b><span>量具 R&R</span></a>
<a href="../../articles/assets/poc/poc_zernike_aberrations/06_through_focus.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_zernike_aberrations.jpg" alt="泽尼克像差" width="200" height="200"><b>&#9654;</b><span>泽尼克像差</span></a>
<a href="../../articles/assets/poc/poc_attention_identities/01_attention_masks.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_attention_identities.jpg" alt="注意力恒等式" width="200" height="200"><span>注意力恒等式</span></a>
<a href="../../articles/assets/poc/poc_residue_crt/03_residue_rotation_needle.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_residue_crt.jpg" alt="中国剩余定理相位" width="200" height="200"><b>&#9654;</b><span>中国剩余定理相位</span></a>
</div>
</details>

<details class="vall"><summary><b>三维形状</b> (18)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_battery_ct_degradation/01_xray_projection.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_battery_ct_degradation.jpg" alt="电池 CT 劣化" width="200" height="200"><span>电池 CT 劣化</span></a>
<a href="../../articles/assets/poc/poc_bev_sensor_fusion/01_scene_bev.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_bev_sensor_fusion.jpg" alt="鸟瞰图融合" width="200" height="200"><span>鸟瞰图融合</span></a>
<a href="../../articles/assets/poc/poc_cad_scan_deviation/14_align_orbit.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_cad_scan_deviation.jpg" alt="CAD 与点云偏差" width="200" height="200"><b>&#9654;</b><span>CAD 与点云偏差</span></a>
<a href="../../articles/assets/poc/poc_crop_phenotyping/01_capsule_calibration.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_crop_phenotyping.jpg" alt="作物叶面积" width="200" height="200"><span>作物叶面积</span></a>
<a href="../../articles/assets/poc/poc_ct_void_morphology/13_section_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_ct_void_morphology.jpg" alt="接合层空洞" width="200" height="200"><b>&#9654;</b><span>接合层空洞</span></a>
<a href="../../articles/assets/poc/poc_dfm_thickness_overhang/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dfm_thickness_overhang.jpg" alt="可制造性" width="200" height="200"><span>可制造性</span></a>
<a href="../../articles/assets/poc/poc_lidar_terrain_change/12_flight.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_lidar_terrain_change.jpg" alt="斜坡土方量" width="200" height="200"><b>&#9654;</b><span>斜坡土方量</span></a>
<a href="../../articles/assets/poc/poc_livestock_body_volume/14_hull_orbit.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_livestock_body_volume.jpg" alt="牲畜体重" width="200" height="200"><b>&#9654;</b><span>牲畜体重</span></a>
<a href="../../articles/assets/poc/poc_mesh_quality_repair/14_decimate_orbit.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_mesh_quality_repair.jpg" alt="网格修复" width="200" height="200"><b>&#9654;</b><span>网格修复</span></a>
<a href="../../articles/assets/poc/poc_pallet_load_utilization/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_pallet_load_utilization.jpg" alt="托盘装载率" width="200" height="200"><span>托盘装载率</span></a>
<a href="../../articles/assets/poc/poc_pipe_wall_loss/01_scene_pipe.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_pipe_wall_loss.jpg" alt="管道减薄" width="200" height="200"><span>管道减薄</span></a>
<a href="../../articles/assets/poc/poc_print_warpage_risk/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_print_warpage_risk.jpg" alt="层叠翘曲" width="200" height="200"><span>层叠翘曲</span></a>
<a href="../../articles/assets/poc/poc_safety_clearance/01_conditions.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_safety_clearance.jpg" alt="人机安全距离" width="200" height="200"><span>人机安全距离</span></a>
<a href="../../articles/assets/poc/poc_scan_to_bim_asbuilt/01_scene_plan_section.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_scan_to_bim_asbuilt.jpg" alt="设计与实物偏差" width="200" height="200"><span>设计与实物偏差</span></a>
<a href="../../articles/assets/poc/poc_structure_4d_deterioration/12_years_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_structure_4d_deterioration.jpg" alt="结构年度复测" width="200" height="200"><b>&#9654;</b><span>结构年度复测</span></a>
<a href="../../articles/assets/poc/poc_symmetry_restoration/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_symmetry_restoration.jpg" alt="对称性补全" width="200" height="200"><span>对称性补全</span></a>
<a href="../../articles/assets/poc/poc_endless_zoom_and_turning_solids/03_zoom_loop.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_endless_zoom_and_turning_solids.jpg" alt="无限缩放" width="200" height="200"><b>&#9654;</b><span>无限缩放</span></a>
<a href="../../articles/assets/poc/poc_four_dimensions_by_three_d_tools/03_hopf_turn.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_four_dimensions_by_three_d_tools.jpg" alt="用三维工具测四维" width="200" height="200"><b>&#9654;</b><span>用三维工具测四维</span></a>
</div>
</details>

<details class="vall"><summary><b>几何与标定</b> (18)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_camera_calibration/05_calibration_convergence.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_camera_calibration.jpg" alt="相机标定" width="200" height="200"><b>&#9654;</b><span>相机标定</span></a>
<a href="../../articles/assets/poc/poc_panorama_drift/05_chain_drift_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_panorama_drift.jpg" alt="全景漂移" width="200" height="200"><b>&#9654;</b><span>全景漂移</span></a>
<a href="../../articles/assets/poc/poc_real_stereo_depth/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_stereo_depth.jpg" alt="实拍立体视觉" width="200" height="200"><span>实拍立体视觉</span></a>
<a href="../../articles/assets/poc/poc_registration_basin/05_icp_basin_iterations.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_registration_basin.jpg" alt="点云配准" width="200" height="200"><b>&#9654;</b><span>点云配准</span></a>
<a href="../../articles/assets/poc/poc_rotation_invariance_audit/02_rotating_coin.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_rotation_invariance_audit.jpg" alt="旋转不变审查" width="200" height="200"><b>&#9654;</b><span>旋转不变审查</span></a>
<a href="../../articles/assets/poc/poc_carla_bridge/01_carla_two_worlds.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_carla_bridge.jpg" alt="两个世界拍摄" width="200" height="200"><span>两个世界拍摄</span></a>
<a href="../../articles/assets/poc/poc_driving_town/04_town_drive_through.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_town.jpg" alt="组装城镇" width="200" height="200"><b>&#9654;</b><span>组装城镇</span></a>
<a href="../../articles/assets/poc/poc_driving_japan_town/03_japan_town_drive.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_japan_town.jpg" alt="真实日本城镇" width="200" height="200"><b>&#9654;</b><span>真实日本城镇</span></a>
<a href="../../articles/assets/poc/poc_driving_commonroad/01_commonroad_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_commonroad.jpg" alt="CommonRoad 评分" width="200" height="200"><span>CommonRoad 评分</span></a>
<a href="../../articles/assets/poc/poc_pegsim_insertion/04_pegsim_insert_corrected.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_pegsim_insertion.jpg" alt="轴孔装配" width="200" height="200"><b>&#9654;</b><span>轴孔装配</span></a>
<a href="../../articles/assets/poc/poc_air_hockey_intercept/02_airhockey_prediction_cone_narrows.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_air_hockey_intercept.jpg" alt="空气曲棍球" width="200" height="200"><b>&#9654;</b><span>空气曲棍球</span></a>
<a href="../../articles/assets/poc/poc_peg_failure_recovery/05_pegfail_wrist_camera_wedging_detect_recover.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_peg_failure_recovery.jpg" alt="插入失败恢复" width="200" height="200"><b>&#9654;</b><span>插入失败恢复</span></a>
<a href="../../articles/assets/poc/poc_tacscalib_sphere_lut/02_tacscalib_synthetic_relight.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_tacscalib_sphere_lut.jpg" alt="触觉传感器标定" width="200" height="200"><b>&#9654;</b><span>触觉传感器标定</span></a>
<a href="../../articles/assets/poc/poc_peg_insertion_tactile/03_pegtactile_whitney_insertion_through_membranes.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_peg_insertion_tactile.jpg" alt="触觉轴孔装配" width="200" height="200"><b>&#9654;</b><span>触觉轴孔装配</span></a>
<a href="../../articles/assets/poc/poc_peg_symmetry_search/01_pegsym_rotating_shapes_read_mod_2pi_over_n.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_peg_symmetry_search.jpg" alt="销钉对称性" width="200" height="200"><b>&#9654;</b><span>销钉对称性</span></a>
<a href="../../articles/assets/poc/poc_reproducible_icp/01_error_staircase_ozaki1.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_reproducible_icp.jpg" alt="可复现 ICP" width="200" height="200"><span>可复现 ICP</span></a>
<a href="../../articles/assets/poc/poc_public_camera_heading/02_yaw_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_public_camera_heading.jpg" alt="公共摄像头朝向" width="200" height="200"><b>&#9654;</b><span>公共摄像头朝向</span></a>
<a href="../../articles/assets/poc/poc_public_camera_heading_real/02_sunset_follow.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_public_camera_heading_real.jpg" alt="摄像头朝向(实拍)" width="200" height="200"><b>&#9654;</b><span>摄像头朝向(实拍)</span></a>
</div>
</details>

<details class="vall"><summary><b>成像质量与复原</b> (16)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_camera_shake_deblur/05_kernel_angle_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_camera_shake_deblur.jpg" alt="手抖去模糊" width="200" height="200"><b>&#9654;</b><span>手抖去模糊</span></a>
<a href="../../articles/assets/poc/poc_colormap_readability/01_gain_profile.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_colormap_readability.jpg" alt="伪彩色可读性" width="200" height="200"><span>伪彩色可读性</span></a>
<a href="../../articles/assets/poc/poc_compound_eye/01_compound_eye_scaling.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_compound_eye.jpg" alt="苍蝇复眼" width="200" height="200"><span>苍蝇复眼</span></a>
<a href="../../articles/assets/poc/poc_ct_fidelity/01_recon_sweep.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_ct_fidelity.jpg" alt="CT 重建极限" width="200" height="200"><span>CT 重建极限</span></a>
<a href="../../articles/assets/poc/poc_dehazing/05_haze_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dehazing.jpg" alt="去雾" width="200" height="200"><b>&#9654;</b><span>去雾</span></a>
<a href="../../articles/assets/poc/poc_dtof_ranging/01_histograms.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dtof_ranging.jpg" alt="光子测距" width="200" height="200"><span>光子测距</span></a>
<a href="../../articles/assets/poc/poc_focus_stacking/05_focus_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_focus_stacking.jpg" alt="景深合成" width="200" height="200"><b>&#9654;</b><span>景深合成</span></a>
<a href="../../articles/assets/poc/poc_lightfield_depth/01_scene_and_depth.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_lightfield_depth.jpg" alt="光场深度" width="200" height="200"><span>光场深度</span></a>
<a href="../../articles/assets/poc/poc_real_deblur_honesty/01_restore.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_deblur_honesty.jpg" alt="实拍去模糊" width="200" height="200"><span>实拍去模糊</span></a>
<a href="../../articles/assets/poc/poc_superresolution_limits/05_growth.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_superresolution_limits.jpg" alt="超分辨率极限" width="200" height="200"><b>&#9654;</b><span>超分辨率极限</span></a>
<a href="../../articles/assets/poc/poc_iqa_tid2013/01_tid2013_mos_vs_psnr.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_iqa_tid2013.jpg" alt="画质指标与 TID2013" width="200" height="200"><span>画质指标与 TID2013</span></a>
<a href="../../articles/assets/poc/poc_iqa_fsim_gmsd_vif/01_iqa_tid2013_mos_vs_fsim.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_iqa_fsim_gmsd_vif.jpg" alt="感知指标一致" width="200" height="200"><span>感知指标一致</span></a>
<a href="../../articles/assets/poc/poc_vanishing_detail_and_morphing_area/06_morph_loop.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_vanishing_detail_and_morphing_area.jpg" alt="消失的细节" width="200" height="200"><b>&#9654;</b><span>消失的细节</span></a>
<a href="../../articles/assets/poc/poc_segmentation_gauntlet/08_gauntlet_blobs.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_segmentation_gauntlet.jpg" alt="分割关卡" width="200" height="200"><b>&#9654;</b><span>分割关卡</span></a>
<a href="../../articles/assets/poc/poc_active_contours/06_u_shape_snakes.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_active_contours.jpg" alt="主动轮廓" width="200" height="200"><b>&#9654;</b><span>主动轮廓</span></a>
<a href="../../articles/assets/poc/poc_graph_hierarchy_segmentation/08_watershed_theta_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_graph_hierarchy_segmentation.jpg" alt="图分割" width="200" height="200"><b>&#9654;</b><span>图分割</span></a>
</div>
</details>

<details class="vall"><summary><b>颜色与分离</b> (4)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_pigment_unmixing/01_per_field_auc.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_pigment_unmixing.jpg" alt="颜料分层" width="200" height="200"><span>颜料分层</span></a>
<a href="../../articles/assets/poc/poc_polarization_specular/01_fresnel.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_polarization_specular.jpg" alt="偏振去镜面反射" width="200" height="200"><span>偏振去镜面反射</span></a>
<a href="../../articles/assets/poc/poc_real_stain_unmix/01_separation.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_stain_unmix.jpg" alt="实拍染色分离" width="200" height="200"><span>实拍染色分离</span></a>
<a href="../../articles/assets/poc/poc_white_balance/01_casts.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_white_balance.jpg" alt="白平衡" width="200" height="200"><span>白平衡</span></a>
</div>
</details>

<details class="vall"><summary><b>把时间序列当作三维测量</b> (21)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_beam_modal_video/14_beam_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_beam_modal_video.jpg" alt="视频模态识别" width="200" height="200"><b>&#9654;</b><span>视频模态识别</span></a>
<a href="../../articles/assets/poc/poc_cold_chain_excursion/01_scene_slices.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_cold_chain_excursion.jpg" alt="冷链温度" width="200" height="200"><span>冷链温度</span></a>
<a href="../../articles/assets/poc/poc_crack_width_timeseries/11_series_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_crack_width_timeseries.jpg" alt="裂缝扩展" width="200" height="200"><b>&#9654;</b><span>裂缝扩展</span></a>
<a href="../../articles/assets/poc/poc_motion_magnification/05_magnify_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_motion_magnification.jpg" alt="微振动放大" width="200" height="200"><b>&#9654;</b><span>微振动放大</span></a>
<a href="../../articles/assets/poc/poc_particle_tracking/05_tracking_links.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_particle_tracking.jpg" alt="粒子跟踪" width="200" height="200"><b>&#9654;</b><span>粒子跟踪</span></a>
<a href="../../articles/assets/poc/poc_settlement_significance/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_settlement_significance.jpg" alt="沉降判定" width="200" height="200"><span>沉降判定</span></a>
<a href="../../articles/assets/poc/poc_template_tracking/05_twin_vs_flat_occluder.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_template_tracking.jpg" alt="模板跟踪" width="200" height="200"><b>&#9654;</b><span>模板跟踪</span></a>
<a href="../../articles/assets/poc/poc_timelapse_growth/05_growth_merge.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_timelapse_growth.jpg" alt="生长延时摄影" width="200" height="200"><b>&#9654;</b><span>生长延时摄影</span></a>
<a href="../../articles/assets/poc/poc_traffic_counting/05_counting_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_traffic_counting.jpg" alt="交通量计数" width="200" height="200"><b>&#9654;</b><span>交通量计数</span></a>
<a href="../../articles/assets/poc/poc_warehouse_flow/01_heat_ambiguity.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_warehouse_flow.jpg" alt="仓库滞留" width="200" height="200"><span>仓库滞留</span></a>
<a href="../../articles/assets/poc/poc_xyt_event_surface/05_arrival_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_xyt_event_surface.jpg" alt="到达时间面" width="200" height="200"><b>&#9654;</b><span>到达时间面</span></a>
<a href="../../articles/assets/poc/poc_video_cube/02_cube_orbit.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_video_cube.jpg" alt="视频时空立方体" width="200" height="200"><b>&#9654;</b><span>视频时空立方体</span></a>
<a href="../../articles/assets/poc/poc_live4d/01_beating_orbit.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_live4d.jpg" alt="活体 3D+t" width="200" height="200"><b>&#9654;</b><span>活体 3D+t</span></a>
<a href="../../articles/assets/poc/poc_diabolo_model_and_vision/01_diabolo_throw_axis_from_image.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_diabolo_model_and_vision.jpg" alt="扯铃" width="200" height="200"><b>&#9654;</b><span>扯铃</span></a>
<a href="../../articles/assets/poc/poc_swarm_obstacle_from_flow/01_swarmflow_hidden_obstacle_emerges.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_swarm_obstacle_from_flow.jpg" alt="群体感知障碍" width="200" height="200"><b>&#9654;</b><span>群体感知障碍</span></a>
<a href="../../articles/assets/poc/poc_ball_bounce/06_rally_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_ball_bounce.jpg" alt="乒乓球跟踪" width="200" height="200"><b>&#9654;</b><span>乒乓球跟踪</span></a>
<a href="../../articles/assets/poc/poc_kendama/05_catch_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_kendama.jpg" alt="剑玉" width="200" height="200"><b>&#9654;</b><span>剑玉</span></a>
<a href="../../articles/assets/poc/poc_table_tennis_spin/01_side_three_serves.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_table_tennis_spin.jpg" alt="乒乓球旋转" width="200" height="200"><b>&#9654;</b><span>乒乓球旋转</span></a>
<a href="../../articles/assets/poc/poc_table_tennis_bounce/01_drop_test.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_table_tennis_bounce.jpg" alt="乒乓球弹跳" width="200" height="200"><b>&#9654;</b><span>乒乓球弹跳</span></a>
<a href="../../articles/assets/poc/poc_table_tennis_rally_loop/01_landing_cloud.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_table_tennis_rally_loop.jpg" alt="回合与读取误差" width="200" height="200"><b>&#9654;</b><span>回合与读取误差</span></a>
<a href="../../articles/assets/poc/poc_periodic_video_boundary/02_loop.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_periodic_video_boundary.jpg" alt="周期视频" width="200" height="200"><b>&#9654;</b><span>周期视频</span></a>
</div>
</details>

<details class="vall"><summary><b>连接组与神经</b> (19)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_fly_vision/01_fly_vision_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_fly_vision.jpg" alt="苍蝇视觉前端" width="200" height="200"><span>苍蝇视觉前端</span></a>
<a href="../../articles/assets/poc/poc_larval_connectome_reservoir/01_adjacency_binned_connectome_vs_shuffle.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_larval_connectome_reservoir.jpg" alt="幼虫连接组" width="200" height="200"><span>幼虫连接组</span></a>
<a href="../../articles/assets/poc/poc_malecns_activity_wave/01_activity_wave_connectome_vs_shuffle.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_malecns_activity_wave.jpg" alt="苍蝇脑电波" width="200" height="200"><b>&#9654;</b><span>苍蝇脑电波</span></a>
<a href="../../articles/assets/poc/poc_eye_to_brain/01_eye_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_eye_to_brain.jpg" alt="复眼到大脑" width="200" height="200"><b>&#9654;</b><span>复眼到大脑</span></a>
<a href="../../articles/assets/poc/poc_em_second_opinion/02_suspects_on_the_cube.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_em_second_opinion.jpg" alt="EM 校对复核" width="200" height="200"><b>&#9654;</b><span>EM 校对复核</span></a>
<a href="../../articles/assets/poc/poc_connectome_motor_bottleneck/03_activity_flow.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_connectome_motor_bottleneck.jpg" alt="运动量化" width="200" height="200"><b>&#9654;</b><span>运动量化</span></a>
<a href="../../articles/assets/poc/poc_microns_brain_wave/01_brain_wave.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_microns_brain_wave.jpg" alt="MICrONS 脑波" width="200" height="200"><b>&#9654;</b><span>MICrONS 脑波</span></a>
<a href="../../articles/assets/poc/poc_em_branch_territory/02_territory_turning.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_em_branch_territory.jpg" alt="分支领域" width="200" height="200"><b>&#9654;</b><span>分支领域</span></a>
<a href="../../articles/assets/poc/poc_connectome_lr_symmetry/01_lr_jaccard_closed_form.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_connectome_lr_symmetry.jpg" alt="线虫左右对称" width="200" height="200"><span>线虫左右对称</span></a>
<a href="../../articles/assets/poc/poc_connectome_across_worms/02_wiring_across_development.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_connectome_across_worms.jpg" alt="线虫个体差异" width="200" height="200"><b>&#9654;</b><span>线虫个体差异</span></a>
<a href="../../articles/assets/poc/poc_connectome_across_decades/01_jaccard_across_decades.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_connectome_across_decades.jpg" alt="40 年前的接线图" width="200" height="200"><span>40 年前的接线图</span></a>
<a href="../../articles/assets/poc/poc_worm_neurites_grow/01_neurite_length_growth.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_worm_neurites_grow.jpg" alt="神经突起生长" width="200" height="200"><span>神经突起生长</span></a>
<a href="../../articles/assets/poc/poc_em_split_merge_score/01_split_vs_merge_by_threshold.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_em_split_merge_score.jpg" alt="EM 分割评分" width="200" height="200"><span>EM 分割评分</span></a>
<a href="../../articles/assets/poc/poc_em_wiring_errors/01_proofreading_order.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_em_wiring_errors.jpg" alt="分割错误与连线" width="200" height="200"><span>分割错误与连线</span></a>
<a href="../../articles/assets/poc/poc_worm_synapses_vs_neurites/01_density_by_stage.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_worm_synapses_vs_neurites.jpg" alt="突触与神经突起" width="200" height="200"><span>突触与神经突起</span></a>
<a href="../../articles/assets/poc/poc_skeleton_run_length_vs_voi/01_merge_size_erl_vs_voi.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_skeleton_run_length_vs_voi.jpg" alt="走行长度与 VOI" width="200" height="200"><span>走行长度与 VOI</span></a>
<a href="../../articles/assets/poc/poc_swc_tree_truth/01_swc_projection.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_swc_tree_truth.jpg" alt="真实树骨架" width="200" height="200"><span>真实树骨架</span></a>
<a href="../../articles/assets/poc/poc_fly_optomotor_steering/06_follow.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_fly_optomotor_steering.jpg" alt="苍蝇航向控制" width="200" height="200"><b>&#9654;</b><span>苍蝇航向控制</span></a>
<a href="../../articles/assets/poc/poc_worm_core_persists/04_core_map_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_worm_core_persists.jpg" alt="线虫脑核心" width="200" height="200"><b>&#9654;</b><span>线虫脑核心</span></a>
</div>
</details>

<details class="vall"><summary><b>医学与生物</b> (9)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_bone_trabecular_thickness/01_scene_truth.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_bone_trabecular_thickness.jpg" alt="骨小梁厚度" width="200" height="200"><span>骨小梁厚度</span></a>
<a href="../../articles/assets/poc/poc_cell_counting/01_scene_dense.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_cell_counting.jpg" alt="重叠细胞计数" width="200" height="200"><span>重叠细胞计数</span></a>
<a href="../../articles/assets/poc/poc_colocalization_crosstalk/01_scene_channels.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_colocalization_crosstalk.jpg" alt="荧光共定位" width="200" height="200"><span>荧光共定位</span></a>
<a href="../../articles/assets/poc/poc_mri_bias_field/01_controls.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_mri_bias_field.jpg" alt="MRI 偏置场" width="200" height="200"><span>MRI 偏置场</span></a>
<a href="../../articles/assets/poc/poc_nuclei_ploidy/01_histograms.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_nuclei_ploidy.jpg" alt="细胞核倍性" width="200" height="200"><span>细胞核倍性</span></a>
<a href="../../articles/assets/poc/poc_vessel_network/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_vessel_network.jpg" alt="血管网络" width="200" height="200"><span>血管网络</span></a>
<a href="../../articles/assets/poc/poc_wound_area_tracking/06_healing_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_wound_area_tracking.jpg" alt="创面面积" width="200" height="200"><b>&#9654;</b><span>创面面积</span></a>
<a href="../../articles/assets/poc/poc_physarum_maze/02_maze_tubes_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_physarum_maze.jpg" alt="黏菌迷宫" width="200" height="200"><b>&#9654;</b><span>黏菌迷宫</span></a>
<a href="../../articles/assets/poc/poc_physarum_transport/01_transport_tubes_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_physarum_transport.jpg" alt="黏菌最优传输" width="200" height="200"><b>&#9654;</b><span>黏菌最优传输</span></a>
</div>
</details>

<details class="vall"><summary><b>天文与环境</b> (21)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_allsky_cloud_cover/01_jacobian.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_allsky_cloud_cover.jpg" alt="全天相机云量" width="200" height="200"><span>全天相机云量</span></a>
<a href="../../articles/assets/poc/poc_astro_photometry/01_stack_scaling.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_astro_photometry.jpg" alt="恒星测光精度" width="200" height="200"><span>恒星测光精度</span></a>
<a href="../../articles/assets/poc/poc_change_detection_misreg/01_plot_fp_vs_shift.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_change_detection_misreg.jpg" alt="变化检测" width="200" height="200"><span>变化检测</span></a>
<a href="../../articles/assets/poc/poc_datacenter_thermal_field/01_scene_truth.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_datacenter_thermal_field.jpg" alt="三维热场重建" width="200" height="200"><span>三维热场重建</span></a>
<a href="../../articles/assets/poc/poc_dem_terrain/05_terrain_flight.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dem_terrain.jpg" alt="地形测量" width="200" height="200"><b>&#9654;</b><span>地形测量</span></a>
<a href="../../articles/assets/poc/poc_exoplanet_transit/01_scene_starfield.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_exoplanet_transit.jpg" alt="系外行星凌星" width="200" height="200"><span>系外行星凌星</span></a>
<a href="../../articles/assets/poc/poc_geodetic_height_frames/01_geoid_frames.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_geodetic_height_frames.jpg" alt="坐标高程陷阱" width="200" height="200"><span>坐标高程陷阱</span></a>
<a href="../../articles/assets/poc/poc_leaf_disease_area/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_leaf_disease_area.jpg" alt="叶片病斑" width="200" height="200"><span>叶片病斑</span></a>
<a href="../../articles/assets/poc/poc_pv_thermal_survey/01_norm_table.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_pv_thermal_survey.jpg" alt="光伏热成像" width="200" height="200"><span>光伏热成像</span></a>
<a href="../../articles/assets/poc/poc_real_sky_photometry/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_sky_photometry.jpg" alt="实拍深空" width="200" height="200"><span>实拍深空</span></a>
<a href="../../articles/assets/poc/poc_river_surface_velocity/13_accumulate_pairs.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_river_surface_velocity.jpg" alt="河流表面流速" width="200" height="200"><b>&#9654;</b><span>河流表面流速</span></a>
<a href="../../articles/assets/poc/poc_sea_ice_concentration/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_sea_ice_concentration.jpg" alt="海冰密集度" width="200" height="200"><span>海冰密集度</span></a>
<a href="../../articles/assets/poc/poc_search_sweep_width/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_search_sweep_width.jpg" alt="搜索扫描宽度" width="200" height="200"><span>搜索扫描宽度</span></a>
<a href="../../articles/assets/poc/poc_solar_limb_darkening/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_solar_limb_darkening.jpg" alt="临边昏暗" width="200" height="200"><span>临边昏暗</span></a>
<a href="../../articles/assets/poc/poc_star_astrometry/01_snr_sweep.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_star_astrometry.jpg" alt="恒星位置精度" width="200" height="200"><span>恒星位置精度</span></a>
<a href="../../articles/assets/poc/poc_tree_ring_dendro/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_tree_ring_dendro.jpg" alt="年轮宽度" width="200" height="200"><span>年轮宽度</span></a>
<a href="../../articles/assets/poc/poc_vegetation_cover/01_mixed_pixel_response.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_vegetation_cover.jpg" alt="植被覆盖率" width="200" height="200"><span>植被覆盖率</span></a>
<a href="../../articles/assets/poc/poc_water_level/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_water_level.jpg" alt="河流水位" width="200" height="200"><span>河流水位</span></a>
<a href="../../articles/assets/poc/poc_rover_slip_risk_path/03_rover_slip_update.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_rover_slip_risk_path.jpg" alt="火星车轮打滑" width="200" height="200"><b>&#9654;</b><span>火星车轮打滑</span></a>
<a href="../../articles/assets/poc/poc_geodetic_benchmarks_real/01_residual_sorted.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_geodetic_benchmarks_real.jpg" alt="两种高程(实测)" width="200" height="200"><span>两种高程(实测)</span></a>
<a href="../../articles/assets/poc/poc_gravitational_lens_invariants/10_source_crossing.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_gravitational_lens_invariants.jpg" alt="引力透镜" width="200" height="200"><b>&#9654;</b><span>引力透镜</span></a>
</div>
</details>

<details class="vall"><summary><b>法证与文档</b> (4)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_document_scan/01_rectify_zero_points.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_document_scan.jpg" alt="文档矫正" width="200" height="200"><span>文档矫正</span></a>
<a href="../../articles/assets/poc/poc_forensics_roc/01_score_maps.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_forensics_roc.jpg" alt="篡改检测 ROC" width="200" height="200"><span>篡改检测 ROC</span></a>
<a href="../../articles/assets/poc/poc_fresco_craquelure/01_ridge_ops.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_fresco_craquelure.jpg" alt="画作龟裂网" width="200" height="200"><span>画作龟裂网</span></a>
<a href="../../articles/assets/poc/poc_prnu_camera_fingerprint/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_prnu_camera_fingerprint.jpg" alt="相机指纹" width="200" height="200"><span>相机指纹</span></a>
</div>
</details>

<details class="vall"><summary><b>自动驾驶</b> (13)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_car_parking/04_parking_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_car_parking.jpg" alt="最短转弯泊车" width="200" height="200"><b>&#9654;</b><span>最短转弯泊车</span></a>
<a href="../../articles/assets/poc/poc_driving_school/05_drive_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_school.jpg" alt="驾校" width="200" height="200"><b>&#9654;</b><span>驾校</span></a>
<a href="../../articles/assets/poc/poc_ttc_rss/06_approach_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_ttc_rss.jpg" alt="碰撞时间与 RSS" width="200" height="200"><b>&#9654;</b><span>碰撞时间与 RSS</span></a>
<a href="../../articles/assets/poc/poc_world_terrain/06_drive_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_world_terrain.jpg" alt="扩展世界" width="200" height="200"><b>&#9654;</b><span>扩展世界</span></a>
<a href="../../articles/assets/poc/poc_driving_longitudinal/01_drive_with_time.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_longitudinal.jpg" alt="惯性与坡道" width="200" height="200"><b>&#9654;</b><span>惯性与坡道</span></a>
<a href="../../articles/assets/poc/poc_driving_weather/01_sun_day.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_weather.jpg" alt="太阳与天气" width="200" height="200"><b>&#9654;</b><span>太阳与天气</span></a>
<a href="../../articles/assets/poc/poc_driving_endless_map/01_minimap_stream.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_endless_map.jpg" alt="无尽地图" width="200" height="200"><b>&#9654;</b><span>无尽地图</span></a>
<a href="../../articles/assets/poc/poc_driving_traffic/01_dashcam_occlusion.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_traffic.jpg" alt="交通与盲区" width="200" height="200"><b>&#9654;</b><span>交通与盲区</span></a>
<a href="../../articles/assets/poc/poc_driving_decisions/01_decisions_mirrors_ambulance.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_decisions.jpg" alt="判断场景" width="200" height="200"><b>&#9654;</b><span>判断场景</span></a>
<a href="../../articles/assets/poc/poc_driving_lateral/01_lateral_dashcam.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_lateral.jpg" alt="横向运动" width="200" height="200"><b>&#9654;</b><span>横向运动</span></a>
<a href="../../articles/assets/poc/poc_driving_humanoids/03_humanoids_crossing.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_humanoids.jpg" alt="人形机器人过马路" width="200" height="200"><b>&#9654;</b><span>人形机器人过马路</span></a>
<a href="../../articles/assets/poc/poc_driving_crossing/01_crossing_dashcam.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_crossing.jpg" alt="道口与路口" width="200" height="200"><b>&#9654;</b><span>道口与路口</span></a>
<a href="../../articles/assets/poc/poc_driving_pass/01_overtake_dashcam.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_pass.jpg" alt="超车与盲区" width="200" height="200"><b>&#9654;</b><span>超车与盲区</span></a>
</div>
</details>

<details class="vall"><summary><b>数学图像</b> (7)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_one_stroke_epicycles/07_epicycles.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_one_stroke_epicycles.jpg" alt="一笔画与周转圆" width="200" height="200"><b>&#9654;</b><span>一笔画与周转圆</span></a>
<a href="../../articles/assets/poc/poc_complex_plane_fields/01_rational.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_complex_plane_fields.jpg" alt="复平面" width="200" height="200"><span>复平面</span></a>
<a href="../../articles/assets/poc/poc_theorems_as_pictures/01_apollonian.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_theorems_as_pictures.jpg" alt="定理即检验" width="200" height="200"><span>定理即检验</span></a>
<a href="../../articles/assets/poc/poc_beats_fringes_and_screens/01_membrane.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_beats_fringes_and_screens.jpg" alt="拍频只有一个" width="200" height="200"><span>拍频只有一个</span></a>
<a href="../../articles/assets/poc/poc_what_a_picture_cannot_check/01_rk4.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_what_a_picture_cannot_check.jpg" alt="图无法验证的" width="200" height="200"><span>图无法验证的</span></a>
<a href="../../articles/assets/poc/poc_illusions_and_perpetual_drawing/14_loop.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_illusions_and_perpetual_drawing.jpg" alt="无限绘图" width="200" height="200"><b>&#9654;</b><span>无限绘图</span></a>
<a href="../../articles/assets/poc/poc_calipers_under_illusion/01_caliper_on_cafe_wall.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_calipers_under_illusion.jpg" alt="错觉检验量具" width="200" height="200"><span>错觉检验量具</span></a>
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

## 能看到什么/测得的数字

所有数字都是相对各 PoC 自己植入的真值(闭式、解析解或公开值)的实测;运行 PoC 会打印出相同的值。

<div class="vl" markdown="1">

**图像检测与外观测量**

- [薄缺陷检出极限](../../articles/assets/poc/poc_real_defect_floor/02_defect_floor_sweep.gif) (GIF): 在实拍背景(砖墙)和噪声量相同的合成背景上,逐渐加深同一个植入缺陷。 **即使噪声量相同,实拍背景的检出极限也是合成背景的 2.03〜3.47 倍(针对位置和振幅已知的缺陷)。** [源码](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_defect_floor.py)
- [主动轮廓](../../articles/assets/poc/poc_active_contours/06_u_shape_snakes.mp4) (视频): 经典 snake(红)进不了 U 形凹槽,GVF(蓝)能深入到底。绿色是真实边缘。 **只把外力换成 GVF,Dice 达到 0.993(相对真实边缘)。** [源码](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_active_contours.py)
- [DIC 应变](../../articles/assets/poc/poc_dic_strain/05_tensile_ramp.mp4) (视频): 拉伸试验加载过程中,从散斑图像读取应变图(试验机同时转动 2 度)。 **真实应变 3000 µε。小应变因转动只读到 2341 µε,Green-Lagrange 为 2961 µε(理论 3005 µε)。** [源码](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dic_strain.py)

**三维测量与几何处理**

- [景深合成](../../articles/assets/poc/poc_focus_stacking/05_focus_sweep.mp4) (视频): 对焦扫描 17 帧,全焦图像和深度图逐步形成。 **全焦 PSNR 33.69 dB(中间 1 帧 28.52 dB),深度误差 0.467 mm(有纹理区域)。** [源码](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_focus_stacking.py)
- [点云配准](../../articles/assets/poc/poc_registration_basin/05_icp_basin_iterations.mp4) (视频): 从初始旋转偏差 30 / 90 / 150 度开始,ICP 每次迭代 1 步。 **60 次迭代后的旋转误差:30 度和 90 度为 0.6 度(成功),150 度为 179.5 度(失败)。** [源码](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_registration_basin.py)
- [料堆体积](../../articles/assets/poc/poc_stockpile_volume/07_scan_orbit.mp4) (视频): 绕料堆一周,把 3-D 扫描位置从 1 处增加到 3 处。颜色为插值面与真实面之差。 **库存量误差 +17.20 % → +0.05 %(真实底面;体积真值为闭式 3572.6089 m³)。** [源码](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_stockpile_volume.py)

**X 射线 CT 与体数据处理**

- [CT 重建](../../articles/assets/poc/poc_ct_fidelity/01_recon_sweep.png) (图): 用 180 → 12 个投影重新拍摄 Shepp-Logan 体模并重建。 **12 个投影的 FBP(RMSE 0.2576)甚至不如空白图像(0.2420)。质量校验发现 -3.34 % 的缺损,修正为 -0.0099 %。** [源码](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_fidelity.py)
- [CT 空洞](../../articles/assets/poc/poc_ct_void_morphology/13_section_sweep.mp4) (视频): 空洞率几乎相同的 2 种接合层,一边扫描断面一边旋转 3-D 空洞(视频 4.3 MB)。 **空洞率为 2.46 % 对 2.63 %,但到界面距离的中位数为 60.0 µm 对 10.0 µm。** [源码](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_void_morphology.py)

**光学、干涉、偏振**

- [白光干涉台阶](../../articles/assets/poc/poc_interferometry_step/05_step_sweep.mp4) (视频): 植入的台阶从 0 增加到 0.90 µm,用包络线法和相移法测量。 **噪声 1 % 时偏差在 2.4 nm 以内(台阶 50〜500 nm)。相移法在 0.153 µm 处跳变 λ/2。** [源码](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_interferometry_step.py)
- [偏振去镜面反射](../../articles/assets/poc/poc_polarization_specular/03_separation.png) (图): 用偏振去除镜面反射的结果,以及残留误差的形状。 **漫反射分量的误差与闭式 R_p·E 一致,在布儒斯特角 56.31 度处为 0。** [源码](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_polarization_specular.py)
- [光弹性应力](../../articles/assets/poc/poc_photoelasticity/03_load_and_isoclinics.mp4) (视频): 圆盘加载时条纹不断涌出,旋转偏振片时等倾线随之移动。 **中心条纹级数 2.38(与闭式一致)。op 的偏振系统与教科书公式最大差 2.2e-16。** [源码](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_photoelasticity.py)

**热、声学、时间序列**

- [热成像缺陷深度](../../articles/assets/poc/poc_thermography_ndt/02_depth_map.png) (图): 根据闪光加热后的表面温度读出 16 个剥离缺陷深度的地图。 **深 0.5 mm、直径 2 mm 的缺陷:拟合时间窗 25 秒时为 +612 %,缩到 4 秒时为 -9 %。** [源码](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_thermography_ndt.py)
- [微振动放大](../../articles/assets/poc/poc_motion_magnification/05_magnify_video.mp4) (视频): 以 0.1 px 振动的表面。左为原始视频,右为放大 10 倍的视频。 **真实振幅 0.1000 px,原始视频测得 0.10012,放大后测得 0.10013 px。放大帮助观看,不提高测量。** [源码](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_motion_magnification.py)

**机器人与空间感知**

- [复眼光场](../../articles/assets/poc/poc_compound_eye/02_compound_eye_superposition.png) (图): 把小眼阵列合成为光场传感器,用 N 个小眼叠加同一个点。 下一步是用苍蝇的接线图(连接组)处理这个光场 —— 见下方的连接组展品。 **SNR 增益:N=5 时 2.25(√5 = 2.24),N=49 时 5.33(√49 = 7.00)。** [源码](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_compound_eye.py)
- [轴孔装配](../../articles/assets/poc/poc_pegsim_insertion/04_pegsim_insert_corrected.gif) (GIF): 用腕部相机测出孔的位置并靠近,再以柔性手腕插入销钉(MuJoCo)。 **伺服 7 次后真实偏差 2.24 → 0.03 mm。有校正的插入 12 / 12 成功。** [源码](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pegsim_insertion.py)
- [空气曲棍球](../../articles/assets/poc/poc_air_hockey_intercept/02_airhockey_prediction_cone_narrows.gif) (GIF): 用低分辨率相机跟踪冰球,预测它与防守线的交点。帧越多,预测带越窄。 **交点的 95 % 带:N = 3 帧时 145 mm → N = 16 帧时 7 mm。** [源码](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_air_hockey_intercept.py)
- [视触觉传感器](../../articles/assets/poc/poc_tacsim_elastic_membrane/03_tacsim_force_sweep.gif) (GIF): 用球压弹性膜并增大载荷,从膜的图像读取接触半径。 **相对 Hertz 闭式:接触半径误差 0.05〜0.26 %,载荷误差 0.14〜0.79 %(0.02〜0.12 N)。** [源码](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_tacsim_elastic_membrane.py)

**乒乓球与运动测量**

- [乒乓球弹跳](../../articles/assets/poc/poc_table_tennis_bounce/01_drop_test.mp4) (视频): ITTF 球台测试:从 30 cm 落球,从视频读取弹起高度。 **从视频读出的弹起高度 23.0 cm(真值 23.0 cm)。** [源码](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_table_tennis_bounce.py)
- [乒乓球旋转](../../articles/assets/poc/poc_table_tennis_spin/01_side_three_serves.mp4) (视频): 以相同速度和方向击出的 3 球:上旋下沉,下旋上浮。 **落点 x = 0.49 / 0.75 / 1.12 m。用从弧线读出的旋转预测的落点,4 球都与真值相差 2 cm 以内。** [源码](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_table_tennis_spin.py)
- [回合与读取误差](../../articles/assets/poc/poc_table_tennis_rally_loop/02_height_misread.mp4) (视频): 把球高读高 5 cm,瞄准计算会选更低的弹道,球落得更近。 **比目标近 10.2 cm。击球前的一阶预测 2.06 × 5 cm = 10.3 cm。** [源码](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_table_tennis_rally_loop.py)

**自动驾驶**

- [交通与盲区](../../articles/assets/poc/poc_driving_traffic/01_dashcam_occlusion.mp4) (视频): 孩子从路边停车后跑出。用与背景的差(无学习)检测并停车。 **在 t = 7.30 s 检出(比真值晚 0.133 s),在孩子路线前 7.09 m 停车。** [源码](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_driving_traffic.py)
- [道口与路口](../../articles/assets/poc/poc_driving_crossing/01_crossing_dashcam.mp4) (视频): 在道口前停车,警报期间等待,左右确认后通过(驾驶员视角)。 **守规则的 240 人违规 0、列车到达时轨道上 0 人。警报中进入的版本 157 人违规,其中 23 人在轨道上。** [源码](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_driving_crossing.py)
- [道路反射镜](../../articles/assets/poc/poc_driving_pass/03_mirror_tjunction.mp4) (视频): 在视线差的丁字路口,用光线追迹绘制凸面反射镜中的车并读取距离。 **距镜子 29 m 的车,按像的大小读成 139 m 外(闭式纵向读数 140 m)。** [源码](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_driving_pass.py)
- [碰撞时间与 RSS](../../articles/assets/poc/poc_ttc_rss/06_approach_gif.gif) (GIF): 由对向车的光流求出碰撞时间 τ,遇停止车辆按 RSS 安全距离停车。 **在 RSS 判为危险的 t = 6.0 s 制动,于 10.25 m 前停车。** [源码](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ttc_rss.py)

**连接组与神经**

- [复眼到大脑](../../articles/assets/poc/poc_eye_to_brain/01_eye_sweep.gif) (GIF): 把苍蝇右眼 1 个小眼的刺激沿眼的一行移动,输入大脑接线图(连接组)(GIF 4.4 MB)。 **刺激柱位置与响应重心的相关:连接组 -0.92,保度随机重连 +0.01。** [源码](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_eye_to_brain.py)
- [苍蝇脑电波](../../articles/assets/poc/poc_malecns_activity_wave/01_activity_wave_connectome_vs_shuffle.gif) (GIF): 右视叶的刺激沿真实接线(左)与保度重连的接线(右)传播。 **真实接线中活动平均距离用 17 步从 88 → 230 µm 扩展;重连后 3 步就散到 300 µm。** [源码](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_malecns_activity_wave.py)
- [小鼠视皮层波](../../articles/assets/poc/poc_microns_brain_wave/04_wave_on_wiring.gif) (GIF): 把 148 根已校对轴突的实测响应,送入小鼠视皮层 1 mm³ 的真实接线(MICrONS)。 **与实测的相关:真实接线 0.085,保度随机重连 0.048。** [源码](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_microns_brain_wave.py)

**机器人之眼(由 Fullseye 负责感知)**

- [人形机器人双眼](../../articles/assets/media/evis_stereo_fullseye.mp4) (视频): 肌肉骨骼人形机器人用筷子击豆,以自己的双眼(瞳距 64 mm)拍摄,Fullseye 每帧计算立体视差 → 深度。 **到豆距离误差:中位数 0.66 %,最大 1.91 %(可读 229 / 241 帧)。** [源码](https://github.com/furuse-kazufumi/fullseye/blob/master/tools/gen_evis_media.py)
- [筷尖相机追踪豆子](../../articles/assets/media/evis_bean_track_fullseye.mp4) (视频): 在同一场景的筷尖相机画面中,Fullseye 检测并追踪豆子。 **可见的 163 帧全部检出(163 / 163),重心误差相对真值中位数 0.10 px。** [源码](https://github.com/furuse-kazufumi/fullseye/blob/master/tools/gen_evis_media.py)

</div>

## Fullseye 是什么

通过 MCP 和 RAG,把包含光学设计、三维测量等传感在内的物理仿真与经典图像处理交给 AI,让它针对每个课题考虑组合方式,并在类型一致性检查和带真值的评估下以对话方式解决课题的平台。开源(Apache-2.0)。

<details markdown="1">
<summary><b>试一试</b> (Python 3.11)</summary>

```
pip install fullseye
git clone https://github.com/furuse-kazufumi/fullseye
cd fullseye
python examples/poc_focus_stacking.py
```

景深合成 PoC 约 20 秒跑完,打印相对真值的数字和 `PASS`。图写入 `out/figures/poc_focus_stacking/`。

</details>

<details markdown="1">
<summary><b>链接</b></summary>

- [GitHub(源代码)](https://github.com/furuse-kazufumi/fullseye)
- [图库(全部图)](../../GALLERY.en.md)
- [查找算子 / 从 AI(RAG)使用](../../AI_RAG_GUIDE.zh.md) · [从 MCP 使用](../../MCP.md) _(ja)_
- [文档索引](../../README.zh.md)

</details>

<details markdown="1">
<summary><b>论文信息</b></summary>

- **题目**: Fullseye：型付き演算子と物理シミュレーションに基づく画像検査・三次元計測基盤 _(ja)_ (基于类型化算子与物理仿真的图像检测与三维测量平台)
- **作者**: 古瀬 和文(个人研究者)
- **发表**: ViEW2026 视觉技术实际应用研讨会
- **论文 PDF**: 2026-11-26 起发布

**摘要(由日文翻译)**: 本文提出开源平台 Fullseye:把图像检测与三维测量的处理组装成声明了输入输出数据类型的算子链,以物理与成像仿真生成的真值进行定量评估,并记录处理流程、评估和失败条件以便复用。它由约 3,000 个类型化算子、在执行前拒绝类型不一致的检查、多语言算子检索(RAG)以及 200 多个带真值的验证程序组成。本文报告代表例的定量评估,以及合成、实测、实机三个验证阶段的区分。

</details>
