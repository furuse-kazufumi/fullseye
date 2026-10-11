<div class="vlang" markdown="1">

[日本語](../index.md) · [English](../en/index.md) · [简体中文](../zh/index.md) · **繁體中文** · [한국어](../ko/index.md) · [Deutsch](../de/index.md) · [हिन्दी](../hi/index.md)

</div>

# Fullseye — ViEW2026

把物理模擬與影像處理交給 AI 組合,並以真值驗證。

點按圖塊即可開啟影片或圖(▶ = 動態)。

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

## 精選

<div class="vg">
<a href="../../articles/assets/poc/poc_real_defect_floor/02_defect_floor_sweep.gif"><img src="../thumbs/poc_real_defect_floor.jpg" alt="薄缺陷檢出極限" loading="lazy" width="320" height="320"><b>&#9654;</b><span>薄缺陷檢出極限</span></a>
<a href="../../articles/assets/poc/poc_active_contours/06_u_shape_snakes.mp4"><img src="../thumbs/poc_active_contours.jpg" alt="主動輪廓" loading="lazy" width="320" height="320"><b>&#9654;</b><span>主動輪廓</span></a>
<a href="../../articles/assets/poc/poc_dic_strain/05_tensile_ramp.mp4"><img src="../thumbs/poc_dic_strain.jpg" alt="DIC 應變" loading="lazy" width="320" height="320"><b>&#9654;</b><span>DIC 應變</span></a>
<a href="../../articles/assets/poc/poc_focus_stacking/05_focus_sweep.mp4"><img src="../thumbs/poc_focus_stacking.jpg" alt="景深合成" loading="lazy" width="320" height="320"><b>&#9654;</b><span>景深合成</span></a>
<a href="../../articles/assets/poc/poc_registration_basin/05_icp_basin_iterations.mp4"><img src="../thumbs/poc_registration_basin.jpg" alt="點雲對位" loading="lazy" width="320" height="320"><b>&#9654;</b><span>點雲對位</span></a>
<a href="../../articles/assets/poc/poc_stockpile_volume/07_scan_orbit.mp4"><img src="../thumbs/poc_stockpile_volume.jpg" alt="料堆體積" loading="lazy" width="320" height="320"><b>&#9654;</b><span>料堆體積</span></a>
<a href="../../articles/assets/poc/poc_ct_fidelity/01_recon_sweep.png"><img src="../thumbs/poc_ct_fidelity.jpg" alt="CT 重建" loading="lazy" width="320" height="320"><span>CT 重建</span></a>
<a href="../../articles/assets/poc/poc_ct_void_morphology/13_section_sweep.mp4"><img src="../thumbs/poc_ct_void_morphology.jpg" alt="CT 孔洞" loading="lazy" width="320" height="320"><b>&#9654;</b><span>CT 孔洞</span></a>
<a href="../../articles/assets/poc/poc_interferometry_step/05_step_sweep.mp4"><img src="../thumbs/poc_interferometry_step.jpg" alt="白光干涉段差" loading="lazy" width="320" height="320"><b>&#9654;</b><span>白光干涉段差</span></a>
<a href="../../articles/assets/poc/poc_polarization_specular/03_separation.png"><img src="../thumbs/poc_polarization_specular.jpg" alt="偏光去鏡面反射" loading="lazy" width="320" height="320"><span>偏光去鏡面反射</span></a>
<a href="../../articles/assets/poc/poc_photoelasticity/03_load_and_isoclinics.mp4"><img src="../thumbs/poc_photoelasticity.jpg" alt="光彈應力" loading="lazy" width="320" height="320"><b>&#9654;</b><span>光彈應力</span></a>
<a href="../../articles/assets/poc/poc_thermography_ndt/02_depth_map.png"><img src="../thumbs/poc_thermography_ndt.jpg" alt="熱影像缺陷深度" loading="lazy" width="320" height="320"><span>熱影像缺陷深度</span></a>
<a href="../../articles/assets/poc/poc_motion_magnification/05_magnify_video.mp4"><img src="../thumbs/poc_motion_magnification.jpg" alt="微振動放大" loading="lazy" width="320" height="320"><b>&#9654;</b><span>微振動放大</span></a>
<a href="../../articles/assets/poc/poc_table_tennis_bounce/01_drop_test.mp4"><img src="../thumbs/poc_table_tennis_bounce.jpg" alt="桌球彈跳" loading="lazy" width="320" height="320"><b>&#9654;</b><span>桌球彈跳</span></a>
<a href="../../articles/assets/poc/poc_compound_eye/02_compound_eye_superposition.png"><img src="../thumbs/poc_compound_eye.jpg" alt="複眼光場" loading="lazy" width="320" height="320"><span>複眼光場</span></a>
<a href="../../articles/assets/poc/poc_pegsim_insertion/04_pegsim_insert_corrected.gif"><img src="../thumbs/poc_pegsim_insertion.jpg" alt="插銷入孔" loading="lazy" width="320" height="320"><b>&#9654;</b><span>插銷入孔</span></a>
<a href="../../articles/assets/poc/poc_air_hockey_intercept/02_airhockey_prediction_cone_narrows.gif"><img src="../thumbs/poc_air_hockey_intercept.jpg" alt="空氣曲棍球" loading="lazy" width="320" height="320"><b>&#9654;</b><span>空氣曲棍球</span></a>
<a href="../../articles/assets/poc/poc_tacsim_elastic_membrane/03_tacsim_force_sweep.gif"><img src="../thumbs/poc_tacsim_elastic_membrane.jpg" alt="視觸覺感測器" loading="lazy" width="320" height="320"><b>&#9654;</b><span>視觸覺感測器</span></a>
<a href="../../articles/assets/poc/poc_table_tennis_spin/01_side_three_serves.mp4"><img src="../thumbs/poc_table_tennis_spin.jpg" alt="桌球旋轉" loading="lazy" width="320" height="320"><b>&#9654;</b><span>桌球旋轉</span></a>
<a href="../../articles/assets/poc/poc_table_tennis_rally_loop/02_height_misread.mp4"><img src="../thumbs/poc_table_tennis_rally_loop.jpg" alt="來回與讀取誤差" loading="lazy" width="320" height="320"><b>&#9654;</b><span>來回與讀取誤差</span></a>
<a href="../../articles/assets/poc/poc_driving_traffic/01_dashcam_occlusion.mp4"><img src="../thumbs/poc_driving_traffic.jpg" alt="交通與死角" loading="lazy" width="320" height="320"><b>&#9654;</b><span>交通與死角</span></a>
<a href="../../articles/assets/poc/poc_driving_crossing/01_crossing_dashcam.mp4"><img src="../thumbs/poc_driving_crossing.jpg" alt="平交道與路口" loading="lazy" width="320" height="320"><b>&#9654;</b><span>平交道與路口</span></a>
<a href="../../articles/assets/poc/poc_driving_pass/03_mirror_tjunction.mp4"><img src="../thumbs/poc_driving_pass.jpg" alt="道路反射鏡" loading="lazy" width="320" height="320"><b>&#9654;</b><span>道路反射鏡</span></a>
<a href="../../articles/assets/poc/poc_ttc_rss/06_approach_gif.gif"><img src="../thumbs/poc_ttc_rss.jpg" alt="碰撞時間與 RSS" loading="lazy" width="320" height="320"><b>&#9654;</b><span>碰撞時間與 RSS</span></a>
<a href="../../articles/assets/poc/poc_eye_to_brain/01_eye_sweep.gif"><img src="../thumbs/poc_eye_to_brain.jpg" alt="複眼到大腦" loading="lazy" width="320" height="320"><b>&#9654;</b><span>複眼到大腦</span></a>
<a href="../../articles/assets/poc/poc_malecns_activity_wave/01_activity_wave_connectome_vs_shuffle.gif"><img src="../thumbs/poc_malecns_activity_wave.jpg" alt="蒼蠅腦波" loading="lazy" width="320" height="320"><b>&#9654;</b><span>蒼蠅腦波</span></a>
<a href="../../articles/assets/poc/poc_microns_brain_wave/04_wave_on_wiring.gif"><img src="../thumbs/poc_microns_brain_wave.jpg" alt="小鼠視皮質波" loading="lazy" width="320" height="320"><b>&#9654;</b><span>小鼠視皮質波</span></a>
<a href="../../articles/assets/media/evis_stereo_fullseye.mp4"><img src="../thumbs/evis_stereo_depth.jpg" alt="人形機器人雙眼" loading="lazy" width="320" height="320"><b>&#9654;</b><span>人形機器人雙眼</span></a>
<a href="../../articles/assets/media/evis_bean_track_fullseye.mp4"><img src="../thumbs/evis_bean_track.jpg" alt="筷尖相機追蹤豆子" loading="lazy" width="320" height="320"><b>&#9654;</b><span>筷尖相機追蹤豆子</span></a>
</div>

## 系列文章 (Qiita 上的英文文章)

<div class="vser">
<a href="https://qiita.com/furuse-kazufumi/items/8a8f23e53b19ee8cdc10"><img src="../thumbs/series_museum.gif" alt="紙上的量測館" loading="lazy" width="480" height="270"><strong>紙上的量測館</strong><span>自行植入真值的 PoC 展館</span></a>
<a href="https://qiita.com/furuse-kazufumi/items/a82bf9f341cc4f04ca75"><img src="../thumbs/series_table_tennis.gif" alt="桌球" loading="lazy" width="480" height="270"><strong>桌球</strong><span>從影片量測彈跳與摩擦</span></a>
<a href="https://qiita.com/furuse-kazufumi/items/05de90f4d316cd7c681c"><img src="../thumbs/series_driving.gif" alt="自動駕駛" loading="lazy" width="480" height="270"><strong>自動駕駛</strong><span>以定理與第二實作評分</span></a>
<a href="https://qiita.com/furuse-kazufumi/items/638f0b0aa7865e17c67c"><img src="../thumbs/series_connectome.gif" alt="連接體(腦接線圖)" loading="lazy" width="480" height="270"><strong>連接體(腦接線圖)</strong><span>把蒼蠅視覺模型裝到身體上量測</span></a>
<a href="https://qiita.com/furuse-kazufumi/items/569720dbae0c6471c96e"><img src="../thumbs/series_humanoid.gif" alt="人形機器人運動會" loading="lazy" width="480" height="270"><strong>人形機器人運動會</strong><span>由影像處理擔任裁判的家庭運動會</span></a>
</div>

## 能做什麼

共 35 項,每項都有說明頁(用法與限制)與可執行的範例。

<div class="vl" markdown="1">

**尋找**

- 切出區域、篩選並計數: [說明](../../capabilities/blob-and-region.md) _(ja)_ · 範例 [poc_cell_counting](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_cell_counting.py) · [poc_particle_sizing](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_particle_sizing.py) · [poc_real_coin_metrology](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_coin_metrology.py)
- 依應有的字串修正影像中的文字: [說明](../../capabilities/fix-text-in-images.md) _(ja)_ · 範例 [fix_text_in_image](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/fix_text_in_image.py) · [poc_glyph_typo_detection](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_glyph_typo_detection.py)
- 找到小的點狀目標並以次像素定位: [說明](../../capabilities/point-target-detection.md) _(ja)_ · 範例 [poc_search_sweep_width](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_search_sweep_width.py) · [poc_astro_photometry](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_astro_photometry.py)

**量測**

- 從平面標定板的多視角估計內參矩陣 K(張正友法): [說明](../../capabilities/camera-intrinsics-calibration.md) _(ja)_ · 範例 [camera_intrinsics_calibration](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/camera_intrinsics_calibration.py)
- 把複數平面當作面來看(域著色、吸引域、逃逸時間、繞翼流動): [說明](../../capabilities/complex-plane-fields.md) _(ja)_ · 範例 [poc_complex_plane_fields](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_complex_plane_fields.py)
- 從本應筆直的線估計畸變係數(鉛垂線法,不需棋盤格): [說明](../../capabilities/estimate-lens-distortion.md) _(ja)_ · 範例 [estimate_lens_distortion](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/estimate_lens_distortion.py)
- 放到地球尺度座標上(ECEF、高程基準、局部 ENU): [說明](../../capabilities/geodetic-frames.md) _(ja)_ · 範例 [poc_geodetic_height_frames](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_geodetic_height_frames.py) · [poc_geodetic_benchmarks_real](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_geodetic_benchmarks_real.py) · [dem_geodesy_tour](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/dem_geodesy_tour.py)
- 這個數字有多少來自量測方式(量具 R&R 與量測不確定度): [說明](../../capabilities/measurement-system-and-uncertainty.md) _(ja)_ · 範例 [poc_measurement_system_analysis](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_measurement_system_analysis.py)
- 以次像素精度從影像量測尺寸: [說明](../../capabilities/subpixel-2d-metrology.md) _(ja)_ · 範例 [poc_dimensional_inspection](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dimensional_inspection.py) · [poc_screw_thread_metrology](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_screw_thread_metrology.py) · [poc_calipers_under_illusion](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_calipers_under_illusion.py)
- 量測地形的坡度、水流與通視: [說明](../../capabilities/terrain-and-visibility.md) _(ja)_ · 範例 [poc_dem_terrain](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dem_terrain.py) · [dem_terrain_analysis_tour](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/dem_terrain_analysis_tour.py)
- 從 3-D 掃描求體積與土方量: [說明](../../capabilities/volume-from-3d-scan.md) _(ja)_ · 範例 [poc_stockpile_volume](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_stockpile_volume.py) · [poc_lidar_terrain_change](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_lidar_terrain_change.py)
- 圖無法驗證的東西(積分器階數、李雅普諾夫指數、分岔、關聯維度、極小曲面): [說明](../../capabilities/what-a-picture-cannot-check.md) _(ja)_ · 範例 [poc_what_a_picture_cannot_check](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_what_a_picture_cannot_check.py)

**光與色**

- 量測顏色(XYZ / Lab / 色差): [說明](../../capabilities/colour-and-delta-e.md) _(ja)_ · 範例 [poc_white_balance](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_white_balance.py) · [poc_pigment_unmixing](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pigment_unmixing.py)
- 計算光的反射、折射與干涉: [說明](../../capabilities/optics-and-materials.md) _(ja)_ · 範例 [glass_and_mirror_optics](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/glass_and_mirror_optics.py) · [appearance_structural_colour](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/appearance_structural_colour.py)
- 把偏光相機的原始幀讀成 Stokes、DoLP、Mueller: [說明](../../capabilities/polarization-imaging.md) _(ja)_ · 範例 [polarization_camera_pipeline](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/polarization_camera_pipeline.py) · [poc_polarization_specular](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_polarization_specular.py)
- 用每一步都能解釋的公式把 Bayer 原始幀變成顯示影像: [說明](../../capabilities/raw-to-display-isp.md) _(ja)_ · 範例 [raw_to_display_isp](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/raw_to_display_isp.py)

**波與訊號**

- 用陣列測方向,分離距離與速度: [說明](../../capabilities/beamforming-and-range-doppler.md) _(ja)_ · 範例 [poc_multibeam_bathymetry](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_multibeam_bathymetry.py) · [poc_bev_sensor_fusion](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bev_sensor_fusion.py)
- 拍頻只有一個(膜的模態、干涉條紋、繞射級、印刷疊紋、落到墨上): [說明](../../capabilities/beats-fringes-and-screens.md) _(ja)_ · 範例 [poc_beats_fringes_and_screens](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_beats_fringes_and_screens.py)
- 從振動與聲音診斷異常: [說明](../../capabilities/vibration-and-acoustics.md) _(ja)_ · 範例 [poc_bearing_diagnosis](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bearing_diagnosis.py) · [poc_rail_corrugation](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_rail_corrugation.py)

**重建與校正**

- 對整張影像校正鏡頭畸變(桶形、枕形、切向): [說明](../../capabilities/lens-distortion-correction.md) _(ja)_ · 範例 [lens_undistort](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/lens_undistort.py)
- 從投影重建斷面(CT): [說明](../../capabilities/tomography-reconstruction.md) _(ja)_ · 範例 [poc_ct_fidelity](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_fidelity.py) · [poc_ct_void_morphology](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_void_morphology.py)
- 從剪影雕出立體(視覺外殼): [說明](../../capabilities/visual-hull-from-silhouettes.md) _(ja)_ · 範例 [space_carving](https://github.com/furuse-kazufumi/fullseye/blob/master/examples_3d/space_carving.py) · [poc_livestock_body_volume](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_livestock_body_volume.py)

**搭建流程**

- 對齊並疊加: [說明](../../capabilities/align-and-stack.md) _(ja)_ · 範例 [poc_astro_photometry](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_astro_photometry.py) · [poc_registration_basin](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_registration_basin.py)
- 與基準影像(黃金樣本)比較、量缺陷、按批判定: [說明](../../capabilities/golden-compare.md) _(ja)_ · 範例 [golden_compare](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/golden_compare.py)
- 用已知良品/不良品集在部署前檢定檢測配方與規格,並量測餘裕: [說明](../../capabilities/inspection-fixture.md) _(ja)_ · 範例 [inspection_fixture](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/inspection_fixture.py)
- 一次呼叫檢測整個資料夾(批次、依規格判定、彙總、SPC、報告、稽核日誌): [說明](../../capabilities/inspection-workflow.md) _(ja)_ · 範例 [inspection_workflow](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/inspection_workflow.py)
- 把 op 的回傳值(帶型別)寫成 JSON,並逐位元還原: [說明](../../capabilities/typed-results-as-json.md) _(ja)_ · 範例 [typed_results_json](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/typed_results_json.py)
- 把 op 的回傳值(帶型別)做成可讀的 Markdown,並內嵌 JSON 以便還原: [說明](../../capabilities/typed-results-as-markdown.md) _(ja)_ · 範例 [typed_results_markdown](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/typed_results_markdown.py)
- 把帶型別的檢測結果寫入 Excel(.xlsx)報告: [說明](../../capabilities/xlsx-report.md) _(ja)_ · 範例 [xlsx_report](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/xlsx_report.py)

**呈現**

- 把結果做成人能讀懂的圖: [說明](../../capabilities/figures-and-annotation.md) _(ja)_ · 範例 [poc_colormap_readability](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_colormap_readability.py) · [poc_dem_terrain](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dem_terrain.py)
- 不知道底色也能畫線與區域(反色): [說明](../../capabilities/inverted-colour-overlays.md) _(ja)_ · 範例 [annotate_paper_tour](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/annotate_paper_tour.py)
- 把文字與表格放到影像上想要的位置: [說明](../../capabilities/text-and-tables-on-images.md) _(ja)_ · 範例 [annotate_paper_tour](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/annotate_paper_tour.py)

**繪製**

- 把照片變成一條線(點描 → 巡迴路徑 → 旋轉的圓): [說明](../../capabilities/one-stroke-drawing.md) _(ja)_ · 範例 [poc_one_stroke_epicycles](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_one_stroke_epicycles.py)
- 製作會騙眼睛的圖來替量測方評分(錯覺、無限繪製、循環動畫): [說明](../../capabilities/pictures-that-carry-their-own-truth.md) _(ja)_ · 範例 [poc_illusions_and_perpetual_drawing](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_illusions_and_perpetual_drawing.py)
- 定理即檢驗門的圖(阿波羅尼奧斯、福特圓、測地穹頂、葉序、IFS、空間填充曲線): [說明](../../capabilities/theorems-as-pictures.md) _(ja)_ · 範例 [poc_theorems_as_pictures](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_theorems_as_pictures.py)

</div>

[其他 115 個使用範例(非 PoC)的列表](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/README.md)

## 全部看

PoC 218 個,另有機器人之眼 4 個。展開分組即可載入縮圖。

<noscript><p><a href="../../GALLERY.en.html">(沒有 JavaScript 時,可在圖庫頁面查看全部圖。)</a></p></noscript>

<details class="vall"><summary><b>機器人之眼(由 Fullseye 負責感知)</b> (4)</summary>
<div class="vg vs">
<a href="../../articles/assets/media/evis_stereo_fullseye.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/evis_stereo_depth.jpg" alt="人形機器人雙眼" width="200" height="200"><b>&#9654;</b><span>人形機器人雙眼</span></a>
<a href="../../articles/assets/media/evis_bean_track_fullseye.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/evis_bean_track.jpg" alt="筷尖相機追蹤豆子" width="200" height="200"><b>&#9654;</b><span>筷尖相機追蹤豆子</span></a>
<a href="../../view2026/media/evis_fullseye_walk.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/evis_walk_rgb_depth_dvs.jpg" alt="以 RGB、深度、DVS 看步行" width="200" height="200"><b>&#9654;</b><span>以 RGB、深度、DVS 看步行</span></a>
<a href="../../view2026/media/vision_adaptive_walk.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/walker2d_terrain_vision.jpg" alt="看台階選步態" width="200" height="200"><span>看台階選步態</span></a>
</div>
</details>

<details class="vall"><summary><b>工業檢測</b> (32)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_barcode_1d/01_misread_split.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_barcode_1d.jpg" alt="一維條碼" width="200" height="200"><span>一維條碼</span></a>
<a href="../../articles/assets/poc/poc_battery_electrode_tortuosity/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_battery_electrode_tortuosity.jpg" alt="電極曲折度" width="200" height="200"><span>電極曲折度</span></a>
<a href="../../articles/assets/poc/poc_bearing_diagnosis/01_envelope_vs_raw.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_bearing_diagnosis.jpg" alt="軸承故障診斷" width="200" height="200"><span>軸承故障診斷</span></a>
<a href="../../articles/assets/poc/poc_bump_coplanarity/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_bump_coplanarity.jpg" alt="凸塊共面度" width="200" height="200"><span>凸塊共面度</span></a>
<a href="../../articles/assets/poc/poc_crack_width/01_width_sweep.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_crack_width.jpg" alt="裂縫寬度" width="200" height="200"><span>裂縫寬度</span></a>
<a href="../../articles/assets/poc/poc_fabric_defect/01_auc_by_type.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_fabric_defect.jpg" alt="織物缺陷" width="200" height="200"><span>織物缺陷</span></a>
<a href="../../articles/assets/poc/poc_leak_localization/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_leak_localization.jpg" alt="聲學漏水定位" width="200" height="200"><span>聲學漏水定位</span></a>
<a href="../../articles/assets/poc/poc_machine_condition_fusion/01_scene_machine.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_machine_condition_fusion.jpg" alt="設備維護融合" width="200" height="200"><span>設備維護融合</span></a>
<a href="../../articles/assets/poc/poc_matrix_code_reading/01_symbol_and_errors.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_matrix_code_reading.jpg" alt="矩陣碼讀取" width="200" height="200"><span>矩陣碼讀取</span></a>
<a href="../../articles/assets/poc/poc_moire_screen/01_failure_split_plot.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_moire_screen.jpg" alt="顯示器摩爾紋" width="200" height="200"><span>顯示器摩爾紋</span></a>
<a href="../../articles/assets/poc/poc_print_registration/01_plates.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_print_registration.jpg" alt="印刷套準" width="200" height="200"><span>印刷套準</span></a>
<a href="../../articles/assets/poc/poc_real_defect_floor/02_defect_floor_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_defect_floor.jpg" alt="薄缺陷極限" width="200" height="200"><b>&#9654;</b><span>薄缺陷極限</span></a>
<a href="../../articles/assets/poc/poc_real_texture_invariance/01_textures.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_texture_invariance.jpg" alt="實拍紋理旋轉" width="200" height="200"><span>實拍紋理旋轉</span></a>
<a href="../../articles/assets/poc/poc_recycling_sorting/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_recycling_sorting.jpg" alt="廢棄物分選" width="200" height="200"><span>廢棄物分選</span></a>
<a href="../../articles/assets/poc/poc_solar_el_inspection/01_zero_point_map.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_solar_el_inspection.jpg" alt="太陽能 EL" width="200" height="200"><span>太陽能 EL</span></a>
<a href="../../articles/assets/poc/poc_solder_fillet_aoi/01_ring_lut.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_solder_fillet_aoi.jpg" alt="焊錫 AOI" width="200" height="200"><span>焊錫 AOI</span></a>
<a href="../../articles/assets/poc/poc_spc/01_spc_xbar_chart.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_spc.jpg" alt="統計製程管制" width="200" height="200"><span>統計製程管制</span></a>
<a href="../../articles/assets/poc/poc_mt_hidden_fault/01_mt_hidden_cloud.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_mt_hidden_fault.jpg" alt="MT 法異常偵測" width="200" height="200"><span>MT 法異常偵測</span></a>
<a href="../../articles/assets/poc/poc_text_region_truth/01_text_region_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_text_region_truth.jpg" alt="文字區域偵測" width="200" height="200"><span>文字區域偵測</span></a>
<a href="../../articles/assets/poc/poc_thermal_drift_metrology/01_separate_drifts.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_thermal_drift_metrology.jpg" alt="相機熱漂移" width="200" height="200"><span>相機熱漂移</span></a>
<a href="../../articles/assets/poc/poc_thermal_radiometry/01_floor.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_thermal_radiometry.jpg" alt="熱像與溫度" width="200" height="200"><span>熱像與溫度</span></a>
<a href="../../articles/assets/poc/poc_thermography_ndt/01_depth_table.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_thermography_ndt.jpg" alt="熱影像缺陷深度" width="200" height="200"><span>熱影像缺陷深度</span></a>
<a href="../../articles/assets/poc/poc_veiling_glare/01_verdict.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_veiling_glare.jpg" alt="雜散光" width="200" height="200"><span>雜散光</span></a>
<a href="../../articles/assets/poc/poc_emva1288_sensor/01_photon_transfer.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_emva1288_sensor.jpg" alt="EMVA 1288 量測" width="200" height="200"><b>&#9654;</b><span>EMVA 1288 量測</span></a>
<a href="../../articles/assets/poc/poc_web_roll_periodicity/01_scene_web.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_web_roll_periodicity.jpg" alt="傳送輥缺陷" width="200" height="200"><span>傳送輥缺陷</span></a>
<a href="../../articles/assets/poc/poc_weld_bead_profile/01_laser_images.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_weld_bead_profile.jpg" alt="焊道截面" width="200" height="200"><span>焊道截面</span></a>
<a href="../../articles/assets/poc/poc_weld_bead_scan_angle/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_weld_bead_scan_angle.jpg" alt="焊道掃描" width="200" height="200"><span>焊道掃描</span></a>
<a href="../../articles/assets/poc/poc_weld_radiograph_porosity/01_scene_radiograph.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_weld_radiograph_porosity.jpg" alt="焊縫氣孔" width="200" height="200"><span>焊縫氣孔</span></a>
<a href="../../articles/assets/poc/poc_glyph_typo_detection/01_sign_before_after.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_glyph_typo_detection.jpg" alt="影像錯字偵測" width="200" height="200"><span>影像錯字偵測</span></a>
<a href="../../articles/assets/poc/poc_print_layer_inspection/01_slice_stack.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_print_layer_inspection.jpg" alt="3D 列印層檢測" width="200" height="200"><span>3D 列印層檢測</span></a>
<a href="../../articles/assets/poc/poc_agv_fleet/01_agv_naive_vs_adg.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_agv_fleet.jpg" alt="AGV 倉庫" width="200" height="200"><b>&#9654;</b><span>AGV 倉庫</span></a>
<a href="../../articles/assets/poc/poc_am_thermal_to_ct/01_melt_pool_frames.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_am_thermal_to_ct.jpg" alt="積層製造與 CT" width="200" height="200"><b>&#9654;</b><span>積層製造與 CT</span></a>
</div>
</details>

<details class="vall"><summary><b>尺寸與形狀量測</b> (36)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_aoi_ct_traceability/01_aoi_and_ct.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_aoi_ct_traceability.jpg" alt="AOI 與 CT 對應" width="200" height="200"><span>AOI 與 CT 對應</span></a>
<a href="../../articles/assets/poc/poc_asbuilt_wall_deviation/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_asbuilt_wall_deviation.jpg" alt="竣工牆面偏差" width="200" height="200"><span>竣工牆面偏差</span></a>
<a href="../../articles/assets/poc/poc_battery_electrode_breathing/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_battery_electrode_breathing.jpg" alt="電極呼吸" width="200" height="200"><span>電極呼吸</span></a>
<a href="../../articles/assets/poc/poc_bilateral_asymmetry/01_floor_vs_spacing.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_bilateral_asymmetry.jpg" alt="左右不對稱" width="200" height="200"><span>左右不對稱</span></a>
<a href="../../articles/assets/poc/poc_dic_strain/05_tensile_ramp.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dic_strain.jpg" alt="DIC 應變" width="200" height="200"><b>&#9654;</b><span>DIC 應變</span></a>
<a href="../../articles/assets/poc/poc_die_tilt_tsv_overlay/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_die_tilt_tsv_overlay.jpg" alt="晶粒傾斜與 TSV" width="200" height="200"><span>晶粒傾斜與 TSV</span></a>
<a href="../../articles/assets/poc/poc_dimensional_inspection/01_slot_bias.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dimensional_inspection.jpg" alt="零件尺寸檢測" width="200" height="200"><span>零件尺寸檢測</span></a>
<a href="../../articles/assets/poc/poc_fiber_orientation/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_fiber_orientation.jpg" alt="纖維取向" width="200" height="200"><span>纖維取向</span></a>
<a href="../../articles/assets/poc/poc_gear_tooth_metrology/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_gear_tooth_metrology.jpg" alt="齒輪齒形" width="200" height="200"><span>齒輪齒形</span></a>
<a href="../../articles/assets/poc/poc_interferometry_step/05_step_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_interferometry_step.jpg" alt="白光干涉段差" width="200" height="200"><b>&#9654;</b><span>白光干涉段差</span></a>
<a href="../../articles/assets/poc/poc_metal_grain_size/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_metal_grain_size.jpg" alt="晶粒度" width="200" height="200"><span>晶粒度</span></a>
<a href="../../articles/assets/poc/poc_multibeam_bathymetry/17_survey.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_multibeam_bathymetry.jpg" alt="多波束測深" width="200" height="200"><b>&#9654;</b><span>多波束測深</span></a>
<a href="../../articles/assets/poc/poc_particle_sizing/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_particle_sizing.jpg" alt="粒度分布" width="200" height="200"><span>粒度分布</span></a>
<a href="../../articles/assets/poc/poc_photoelasticity/03_load_and_isoclinics.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_photoelasticity.jpg" alt="光彈應力" width="200" height="200"><b>&#9654;</b><span>光彈應力</span></a>
<a href="../../articles/assets/poc/poc_rail_corrugation/01_planted_components.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_rail_corrugation.jpg" alt="鋼軌波磨" width="200" height="200"><span>鋼軌波磨</span></a>
<a href="../../articles/assets/poc/poc_real_coin_metrology/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_coin_metrology.jpg" alt="實拍硬幣" width="200" height="200"><span>實拍硬幣</span></a>
<a href="../../articles/assets/poc/poc_screw_thread_metrology/01_zero_spectrum.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_screw_thread_metrology.jpg" alt="螺紋輪廓" width="200" height="200"><span>螺紋輪廓</span></a>
<a href="../../articles/assets/poc/poc_stockpile_volume/07_scan_orbit.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_stockpile_volume.jpg" alt="料堆體積" width="200" height="200"><b>&#9654;</b><span>料堆體積</span></a>
<a href="../../articles/assets/poc/poc_strain_history/05_history_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_strain_history.jpg" alt="潛變應變" width="200" height="200"><b>&#9654;</b><span>潛變應變</span></a>
<a href="../../articles/assets/poc/poc_surface_roughness/01_surface_components.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_surface_roughness.jpg" alt="表面粗糙度" width="200" height="200"><span>表面粗糙度</span></a>
<a href="../../articles/assets/poc/poc_tacsim_elastic_membrane/03_tacsim_force_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_tacsim_elastic_membrane.jpg" alt="視觸覺感測器" width="200" height="200"><b>&#9654;</b><span>視觸覺感測器</span></a>
<a href="../../articles/assets/poc/poc_tacsim_marker_shear/02_tacslip_stick_circle_shrinks.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_tacsim_marker_shear.jpg" alt="觸覺剪切" width="200" height="200"><b>&#9654;</b><span>觸覺剪切</span></a>
<a href="../../articles/assets/poc/poc_tactile_dipole_torque/02_tactorque_dipole_grows_with_M.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_tactile_dipole_torque.jpg" alt="觸覺偶極子" width="200" height="200"><b>&#9654;</b><span>觸覺偶極子</span></a>
<a href="../../articles/assets/poc/poc_granular_heap_repose/11_granular_datum_tilt_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_granular_heap_repose.jpg" alt="粉體堆" width="200" height="200"><b>&#9654;</b><span>粉體堆</span></a>
<a href="../../articles/assets/poc/poc_food_cutting_measure/01_cutting_track_force.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_food_cutting_measure.jpg" alt="食材切割" width="200" height="200"><b>&#9654;</b><span>食材切割</span></a>
<a href="../../articles/assets/poc/poc_tacdome_large_deformation/01_tacdome_press_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_tacdome_large_deformation.jpg" alt="穹頂指尖接觸" width="200" height="200"><b>&#9654;</b><span>穹頂指尖接觸</span></a>
<a href="../../articles/assets/poc/poc_polish_wipe_measure/01_polish_raster_wipe_coat.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_polish_wipe_measure.jpg" alt="研磨與擦拭" width="200" height="200"><b>&#9654;</b><span>研磨與擦拭</span></a>
<a href="../../articles/assets/poc/poc_powder_scoop_pour/03_scoop_stream_synthetic_frames.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_powder_scoop_pour.jpg" alt="粉體舀取與傾倒" width="200" height="200"><b>&#9654;</b><span>粉體舀取與傾倒</span></a>
<a href="../../articles/assets/poc/poc_powder_grinding_ae/07_psd_fining_during_grinding.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_powder_grinding_ae.jpg" alt="研缽粉碎" width="200" height="200"><b>&#9654;</b><span>研缽粉碎</span></a>
<a href="../../articles/assets/poc/poc_pxrd_phase_peel/01_phase_peel.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_pxrd_phase_peel.jpg" alt="X 光繞射分相" width="200" height="200"><b>&#9654;</b><span>X 光繞射分相</span></a>
<a href="../../articles/assets/poc/poc_dose_uniformity_from_grinding/01_cv_bias_decomposition.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dose_uniformity_from_grinding.jpg" alt="藥量均勻性" width="200" height="200"><span>藥量均勻性</span></a>
<a href="../../articles/assets/poc/poc_knife_tactile_toughness/06_cut_with_fingertip_pads.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_knife_tactile_toughness.jpg" alt="指尖握刀" width="200" height="200"><b>&#9654;</b><span>指尖握刀</span></a>
<a href="../../articles/assets/poc/poc_measurement_system_analysis/16_breakdown_movie.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_measurement_system_analysis.jpg" alt="量具 R&R" width="200" height="200"><b>&#9654;</b><span>量具 R&R</span></a>
<a href="../../articles/assets/poc/poc_zernike_aberrations/06_through_focus.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_zernike_aberrations.jpg" alt="澤尼克像差" width="200" height="200"><b>&#9654;</b><span>澤尼克像差</span></a>
<a href="../../articles/assets/poc/poc_attention_identities/01_attention_masks.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_attention_identities.jpg" alt="注意力恆等式" width="200" height="200"><span>注意力恆等式</span></a>
<a href="../../articles/assets/poc/poc_residue_crt/03_residue_rotation_needle.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_residue_crt.jpg" alt="中國剩餘定理相位" width="200" height="200"><b>&#9654;</b><span>中國剩餘定理相位</span></a>
</div>
</details>

<details class="vall"><summary><b>三維形狀</b> (18)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_battery_ct_degradation/01_xray_projection.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_battery_ct_degradation.jpg" alt="電池 CT 劣化" width="200" height="200"><span>電池 CT 劣化</span></a>
<a href="../../articles/assets/poc/poc_bev_sensor_fusion/01_scene_bev.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_bev_sensor_fusion.jpg" alt="鳥瞰圖融合" width="200" height="200"><span>鳥瞰圖融合</span></a>
<a href="../../articles/assets/poc/poc_cad_scan_deviation/14_align_orbit.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_cad_scan_deviation.jpg" alt="CAD 與點雲偏差" width="200" height="200"><b>&#9654;</b><span>CAD 與點雲偏差</span></a>
<a href="../../articles/assets/poc/poc_crop_phenotyping/01_capsule_calibration.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_crop_phenotyping.jpg" alt="作物葉面積" width="200" height="200"><span>作物葉面積</span></a>
<a href="../../articles/assets/poc/poc_ct_void_morphology/13_section_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_ct_void_morphology.jpg" alt="接合層孔洞" width="200" height="200"><b>&#9654;</b><span>接合層孔洞</span></a>
<a href="../../articles/assets/poc/poc_dfm_thickness_overhang/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dfm_thickness_overhang.jpg" alt="可製造性" width="200" height="200"><span>可製造性</span></a>
<a href="../../articles/assets/poc/poc_lidar_terrain_change/12_flight.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_lidar_terrain_change.jpg" alt="斜坡土方量" width="200" height="200"><b>&#9654;</b><span>斜坡土方量</span></a>
<a href="../../articles/assets/poc/poc_livestock_body_volume/14_hull_orbit.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_livestock_body_volume.jpg" alt="牲畜體重" width="200" height="200"><b>&#9654;</b><span>牲畜體重</span></a>
<a href="../../articles/assets/poc/poc_mesh_quality_repair/14_decimate_orbit.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_mesh_quality_repair.jpg" alt="網格修復" width="200" height="200"><b>&#9654;</b><span>網格修復</span></a>
<a href="../../articles/assets/poc/poc_pallet_load_utilization/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_pallet_load_utilization.jpg" alt="棧板裝載率" width="200" height="200"><span>棧板裝載率</span></a>
<a href="../../articles/assets/poc/poc_pipe_wall_loss/01_scene_pipe.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_pipe_wall_loss.jpg" alt="管道減薄" width="200" height="200"><span>管道減薄</span></a>
<a href="../../articles/assets/poc/poc_print_warpage_risk/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_print_warpage_risk.jpg" alt="層疊翹曲" width="200" height="200"><span>層疊翹曲</span></a>
<a href="../../articles/assets/poc/poc_safety_clearance/01_conditions.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_safety_clearance.jpg" alt="人機安全距離" width="200" height="200"><span>人機安全距離</span></a>
<a href="../../articles/assets/poc/poc_scan_to_bim_asbuilt/01_scene_plan_section.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_scan_to_bim_asbuilt.jpg" alt="設計與實物偏差" width="200" height="200"><span>設計與實物偏差</span></a>
<a href="../../articles/assets/poc/poc_structure_4d_deterioration/12_years_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_structure_4d_deterioration.jpg" alt="結構年度複測" width="200" height="200"><b>&#9654;</b><span>結構年度複測</span></a>
<a href="../../articles/assets/poc/poc_symmetry_restoration/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_symmetry_restoration.jpg" alt="對稱性補全" width="200" height="200"><span>對稱性補全</span></a>
<a href="../../articles/assets/poc/poc_endless_zoom_and_turning_solids/03_zoom_loop.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_endless_zoom_and_turning_solids.jpg" alt="無限縮放" width="200" height="200"><b>&#9654;</b><span>無限縮放</span></a>
<a href="../../articles/assets/poc/poc_four_dimensions_by_three_d_tools/03_hopf_turn.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_four_dimensions_by_three_d_tools.jpg" alt="以三維工具量四維" width="200" height="200"><b>&#9654;</b><span>以三維工具量四維</span></a>
</div>
</details>

<details class="vall"><summary><b>幾何與校正</b> (18)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_camera_calibration/05_calibration_convergence.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_camera_calibration.jpg" alt="相機校正" width="200" height="200"><b>&#9654;</b><span>相機校正</span></a>
<a href="../../articles/assets/poc/poc_panorama_drift/05_chain_drift_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_panorama_drift.jpg" alt="全景漂移" width="200" height="200"><b>&#9654;</b><span>全景漂移</span></a>
<a href="../../articles/assets/poc/poc_real_stereo_depth/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_stereo_depth.jpg" alt="實拍立體視覺" width="200" height="200"><span>實拍立體視覺</span></a>
<a href="../../articles/assets/poc/poc_registration_basin/05_icp_basin_iterations.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_registration_basin.jpg" alt="點雲對位" width="200" height="200"><b>&#9654;</b><span>點雲對位</span></a>
<a href="../../articles/assets/poc/poc_rotation_invariance_audit/02_rotating_coin.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_rotation_invariance_audit.jpg" alt="旋轉不變稽核" width="200" height="200"><b>&#9654;</b><span>旋轉不變稽核</span></a>
<a href="../../articles/assets/poc/poc_carla_bridge/01_carla_two_worlds.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_carla_bridge.jpg" alt="兩個世界拍攝" width="200" height="200"><span>兩個世界拍攝</span></a>
<a href="../../articles/assets/poc/poc_driving_town/04_town_drive_through.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_town.jpg" alt="組裝城鎮" width="200" height="200"><b>&#9654;</b><span>組裝城鎮</span></a>
<a href="../../articles/assets/poc/poc_driving_japan_town/03_japan_town_drive.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_japan_town.jpg" alt="真實日本城鎮" width="200" height="200"><b>&#9654;</b><span>真實日本城鎮</span></a>
<a href="../../articles/assets/poc/poc_driving_commonroad/01_commonroad_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_commonroad.jpg" alt="CommonRoad 評分" width="200" height="200"><span>CommonRoad 評分</span></a>
<a href="../../articles/assets/poc/poc_pegsim_insertion/04_pegsim_insert_corrected.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_pegsim_insertion.jpg" alt="插銷入孔" width="200" height="200"><b>&#9654;</b><span>插銷入孔</span></a>
<a href="../../articles/assets/poc/poc_air_hockey_intercept/02_airhockey_prediction_cone_narrows.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_air_hockey_intercept.jpg" alt="空氣曲棍球" width="200" height="200"><b>&#9654;</b><span>空氣曲棍球</span></a>
<a href="../../articles/assets/poc/poc_peg_failure_recovery/05_pegfail_wrist_camera_wedging_detect_recover.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_peg_failure_recovery.jpg" alt="插入失敗恢復" width="200" height="200"><b>&#9654;</b><span>插入失敗恢復</span></a>
<a href="../../articles/assets/poc/poc_tacscalib_sphere_lut/02_tacscalib_synthetic_relight.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_tacscalib_sphere_lut.jpg" alt="觸覺感測器校正" width="200" height="200"><b>&#9654;</b><span>觸覺感測器校正</span></a>
<a href="../../articles/assets/poc/poc_peg_insertion_tactile/03_pegtactile_whitney_insertion_through_membranes.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_peg_insertion_tactile.jpg" alt="觸覺插銷入孔" width="200" height="200"><b>&#9654;</b><span>觸覺插銷入孔</span></a>
<a href="../../articles/assets/poc/poc_peg_symmetry_search/01_pegsym_rotating_shapes_read_mod_2pi_over_n.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_peg_symmetry_search.jpg" alt="插銷對稱性" width="200" height="200"><b>&#9654;</b><span>插銷對稱性</span></a>
<a href="../../articles/assets/poc/poc_reproducible_icp/01_error_staircase_ozaki1.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_reproducible_icp.jpg" alt="可重現 ICP" width="200" height="200"><span>可重現 ICP</span></a>
<a href="../../articles/assets/poc/poc_public_camera_heading/02_yaw_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_public_camera_heading.jpg" alt="公共攝影機朝向" width="200" height="200"><b>&#9654;</b><span>公共攝影機朝向</span></a>
<a href="../../articles/assets/poc/poc_public_camera_heading_real/02_sunset_follow.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_public_camera_heading_real.jpg" alt="攝影機朝向(實拍)" width="200" height="200"><b>&#9654;</b><span>攝影機朝向(實拍)</span></a>
</div>
</details>

<details class="vall"><summary><b>成像品質與復原</b> (16)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_camera_shake_deblur/05_kernel_angle_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_camera_shake_deblur.jpg" alt="手震去模糊" width="200" height="200"><b>&#9654;</b><span>手震去模糊</span></a>
<a href="../../articles/assets/poc/poc_colormap_readability/01_gain_profile.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_colormap_readability.jpg" alt="偽色可讀性" width="200" height="200"><span>偽色可讀性</span></a>
<a href="../../articles/assets/poc/poc_compound_eye/01_compound_eye_scaling.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_compound_eye.jpg" alt="蒼蠅複眼" width="200" height="200"><span>蒼蠅複眼</span></a>
<a href="../../articles/assets/poc/poc_ct_fidelity/01_recon_sweep.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_ct_fidelity.jpg" alt="CT 重建極限" width="200" height="200"><span>CT 重建極限</span></a>
<a href="../../articles/assets/poc/poc_dehazing/05_haze_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dehazing.jpg" alt="去霧" width="200" height="200"><b>&#9654;</b><span>去霧</span></a>
<a href="../../articles/assets/poc/poc_dtof_ranging/01_histograms.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dtof_ranging.jpg" alt="光子測距" width="200" height="200"><span>光子測距</span></a>
<a href="../../articles/assets/poc/poc_focus_stacking/05_focus_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_focus_stacking.jpg" alt="景深合成" width="200" height="200"><b>&#9654;</b><span>景深合成</span></a>
<a href="../../articles/assets/poc/poc_lightfield_depth/01_scene_and_depth.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_lightfield_depth.jpg" alt="光場深度" width="200" height="200"><span>光場深度</span></a>
<a href="../../articles/assets/poc/poc_real_deblur_honesty/01_restore.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_deblur_honesty.jpg" alt="實拍去模糊" width="200" height="200"><span>實拍去模糊</span></a>
<a href="../../articles/assets/poc/poc_superresolution_limits/05_growth.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_superresolution_limits.jpg" alt="超解析度極限" width="200" height="200"><b>&#9654;</b><span>超解析度極限</span></a>
<a href="../../articles/assets/poc/poc_iqa_tid2013/01_tid2013_mos_vs_psnr.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_iqa_tid2013.jpg" alt="畫質指標與 TID2013" width="200" height="200"><span>畫質指標與 TID2013</span></a>
<a href="../../articles/assets/poc/poc_iqa_fsim_gmsd_vif/01_iqa_tid2013_mos_vs_fsim.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_iqa_fsim_gmsd_vif.jpg" alt="感知指標一致" width="200" height="200"><span>感知指標一致</span></a>
<a href="../../articles/assets/poc/poc_vanishing_detail_and_morphing_area/06_morph_loop.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_vanishing_detail_and_morphing_area.jpg" alt="消失的細節" width="200" height="200"><b>&#9654;</b><span>消失的細節</span></a>
<a href="../../articles/assets/poc/poc_segmentation_gauntlet/08_gauntlet_blobs.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_segmentation_gauntlet.jpg" alt="分割關卡" width="200" height="200"><b>&#9654;</b><span>分割關卡</span></a>
<a href="../../articles/assets/poc/poc_active_contours/06_u_shape_snakes.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_active_contours.jpg" alt="主動輪廓" width="200" height="200"><b>&#9654;</b><span>主動輪廓</span></a>
<a href="../../articles/assets/poc/poc_graph_hierarchy_segmentation/08_watershed_theta_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_graph_hierarchy_segmentation.jpg" alt="圖分割" width="200" height="200"><b>&#9654;</b><span>圖分割</span></a>
</div>
</details>

<details class="vall"><summary><b>顏色與分離</b> (4)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_pigment_unmixing/01_per_field_auc.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_pigment_unmixing.jpg" alt="顏料分層" width="200" height="200"><span>顏料分層</span></a>
<a href="../../articles/assets/poc/poc_polarization_specular/01_fresnel.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_polarization_specular.jpg" alt="偏光去鏡面反射" width="200" height="200"><span>偏光去鏡面反射</span></a>
<a href="../../articles/assets/poc/poc_real_stain_unmix/01_separation.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_stain_unmix.jpg" alt="實拍染色分離" width="200" height="200"><span>實拍染色分離</span></a>
<a href="../../articles/assets/poc/poc_white_balance/01_casts.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_white_balance.jpg" alt="白平衡" width="200" height="200"><span>白平衡</span></a>
</div>
</details>

<details class="vall"><summary><b>把時間序列當作三維量測</b> (21)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_beam_modal_video/14_beam_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_beam_modal_video.jpg" alt="影片模態識別" width="200" height="200"><b>&#9654;</b><span>影片模態識別</span></a>
<a href="../../articles/assets/poc/poc_cold_chain_excursion/01_scene_slices.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_cold_chain_excursion.jpg" alt="冷鏈溫度" width="200" height="200"><span>冷鏈溫度</span></a>
<a href="../../articles/assets/poc/poc_crack_width_timeseries/11_series_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_crack_width_timeseries.jpg" alt="裂縫擴展" width="200" height="200"><b>&#9654;</b><span>裂縫擴展</span></a>
<a href="../../articles/assets/poc/poc_motion_magnification/05_magnify_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_motion_magnification.jpg" alt="微振動放大" width="200" height="200"><b>&#9654;</b><span>微振動放大</span></a>
<a href="../../articles/assets/poc/poc_particle_tracking/05_tracking_links.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_particle_tracking.jpg" alt="粒子追蹤" width="200" height="200"><b>&#9654;</b><span>粒子追蹤</span></a>
<a href="../../articles/assets/poc/poc_settlement_significance/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_settlement_significance.jpg" alt="沉降判定" width="200" height="200"><span>沉降判定</span></a>
<a href="../../articles/assets/poc/poc_template_tracking/05_twin_vs_flat_occluder.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_template_tracking.jpg" alt="模板追蹤" width="200" height="200"><b>&#9654;</b><span>模板追蹤</span></a>
<a href="../../articles/assets/poc/poc_timelapse_growth/05_growth_merge.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_timelapse_growth.jpg" alt="生長縮時攝影" width="200" height="200"><b>&#9654;</b><span>生長縮時攝影</span></a>
<a href="../../articles/assets/poc/poc_traffic_counting/05_counting_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_traffic_counting.jpg" alt="交通量計數" width="200" height="200"><b>&#9654;</b><span>交通量計數</span></a>
<a href="../../articles/assets/poc/poc_warehouse_flow/01_heat_ambiguity.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_warehouse_flow.jpg" alt="倉庫滯留" width="200" height="200"><span>倉庫滯留</span></a>
<a href="../../articles/assets/poc/poc_xyt_event_surface/05_arrival_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_xyt_event_surface.jpg" alt="到達時間面" width="200" height="200"><b>&#9654;</b><span>到達時間面</span></a>
<a href="../../articles/assets/poc/poc_video_cube/02_cube_orbit.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_video_cube.jpg" alt="影片時空立方體" width="200" height="200"><b>&#9654;</b><span>影片時空立方體</span></a>
<a href="../../articles/assets/poc/poc_live4d/01_beating_orbit.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_live4d.jpg" alt="活體 3D+t" width="200" height="200"><b>&#9654;</b><span>活體 3D+t</span></a>
<a href="../../articles/assets/poc/poc_diabolo_model_and_vision/01_diabolo_throw_axis_from_image.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_diabolo_model_and_vision.jpg" alt="扯鈴" width="200" height="200"><b>&#9654;</b><span>扯鈴</span></a>
<a href="../../articles/assets/poc/poc_swarm_obstacle_from_flow/01_swarmflow_hidden_obstacle_emerges.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_swarm_obstacle_from_flow.jpg" alt="群體感知障礙" width="200" height="200"><b>&#9654;</b><span>群體感知障礙</span></a>
<a href="../../articles/assets/poc/poc_ball_bounce/06_rally_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_ball_bounce.jpg" alt="桌球追蹤" width="200" height="200"><b>&#9654;</b><span>桌球追蹤</span></a>
<a href="../../articles/assets/poc/poc_kendama/05_catch_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_kendama.jpg" alt="劍玉" width="200" height="200"><b>&#9654;</b><span>劍玉</span></a>
<a href="../../articles/assets/poc/poc_table_tennis_spin/01_side_three_serves.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_table_tennis_spin.jpg" alt="桌球旋轉" width="200" height="200"><b>&#9654;</b><span>桌球旋轉</span></a>
<a href="../../articles/assets/poc/poc_table_tennis_bounce/01_drop_test.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_table_tennis_bounce.jpg" alt="桌球彈跳" width="200" height="200"><b>&#9654;</b><span>桌球彈跳</span></a>
<a href="../../articles/assets/poc/poc_table_tennis_rally_loop/01_landing_cloud.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_table_tennis_rally_loop.jpg" alt="來回與讀取誤差" width="200" height="200"><b>&#9654;</b><span>來回與讀取誤差</span></a>
<a href="../../articles/assets/poc/poc_periodic_video_boundary/02_loop.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_periodic_video_boundary.jpg" alt="週期影片" width="200" height="200"><b>&#9654;</b><span>週期影片</span></a>
</div>
</details>

<details class="vall"><summary><b>連接體與神經</b> (19)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_fly_vision/01_fly_vision_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_fly_vision.jpg" alt="蒼蠅視覺前端" width="200" height="200"><span>蒼蠅視覺前端</span></a>
<a href="../../articles/assets/poc/poc_larval_connectome_reservoir/01_adjacency_binned_connectome_vs_shuffle.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_larval_connectome_reservoir.jpg" alt="幼蟲連接體" width="200" height="200"><span>幼蟲連接體</span></a>
<a href="../../articles/assets/poc/poc_malecns_activity_wave/01_activity_wave_connectome_vs_shuffle.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_malecns_activity_wave.jpg" alt="蒼蠅腦波" width="200" height="200"><b>&#9654;</b><span>蒼蠅腦波</span></a>
<a href="../../articles/assets/poc/poc_eye_to_brain/01_eye_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_eye_to_brain.jpg" alt="複眼到大腦" width="200" height="200"><b>&#9654;</b><span>複眼到大腦</span></a>
<a href="../../articles/assets/poc/poc_em_second_opinion/02_suspects_on_the_cube.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_em_second_opinion.jpg" alt="EM 校對複核" width="200" height="200"><b>&#9654;</b><span>EM 校對複核</span></a>
<a href="../../articles/assets/poc/poc_connectome_motor_bottleneck/03_activity_flow.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_connectome_motor_bottleneck.jpg" alt="運動量化" width="200" height="200"><b>&#9654;</b><span>運動量化</span></a>
<a href="../../articles/assets/poc/poc_microns_brain_wave/01_brain_wave.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_microns_brain_wave.jpg" alt="MICrONS 腦波" width="200" height="200"><b>&#9654;</b><span>MICrONS 腦波</span></a>
<a href="../../articles/assets/poc/poc_em_branch_territory/02_territory_turning.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_em_branch_territory.jpg" alt="分支領域" width="200" height="200"><b>&#9654;</b><span>分支領域</span></a>
<a href="../../articles/assets/poc/poc_connectome_lr_symmetry/01_lr_jaccard_closed_form.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_connectome_lr_symmetry.jpg" alt="線蟲左右對稱" width="200" height="200"><span>線蟲左右對稱</span></a>
<a href="../../articles/assets/poc/poc_connectome_across_worms/02_wiring_across_development.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_connectome_across_worms.jpg" alt="線蟲個體差異" width="200" height="200"><b>&#9654;</b><span>線蟲個體差異</span></a>
<a href="../../articles/assets/poc/poc_connectome_across_decades/01_jaccard_across_decades.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_connectome_across_decades.jpg" alt="40 年前的接線圖" width="200" height="200"><span>40 年前的接線圖</span></a>
<a href="../../articles/assets/poc/poc_worm_neurites_grow/01_neurite_length_growth.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_worm_neurites_grow.jpg" alt="神經突起生長" width="200" height="200"><span>神經突起生長</span></a>
<a href="../../articles/assets/poc/poc_em_split_merge_score/01_split_vs_merge_by_threshold.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_em_split_merge_score.jpg" alt="EM 分割評分" width="200" height="200"><span>EM 分割評分</span></a>
<a href="../../articles/assets/poc/poc_em_wiring_errors/01_proofreading_order.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_em_wiring_errors.jpg" alt="分割錯誤與連線" width="200" height="200"><span>分割錯誤與連線</span></a>
<a href="../../articles/assets/poc/poc_worm_synapses_vs_neurites/01_density_by_stage.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_worm_synapses_vs_neurites.jpg" alt="突觸與神經突起" width="200" height="200"><span>突觸與神經突起</span></a>
<a href="../../articles/assets/poc/poc_skeleton_run_length_vs_voi/01_merge_size_erl_vs_voi.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_skeleton_run_length_vs_voi.jpg" alt="走行長度與 VOI" width="200" height="200"><span>走行長度與 VOI</span></a>
<a href="../../articles/assets/poc/poc_swc_tree_truth/01_swc_projection.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_swc_tree_truth.jpg" alt="真實樹骨架" width="200" height="200"><span>真實樹骨架</span></a>
<a href="../../articles/assets/poc/poc_fly_optomotor_steering/06_follow.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_fly_optomotor_steering.jpg" alt="蒼蠅航向控制" width="200" height="200"><b>&#9654;</b><span>蒼蠅航向控制</span></a>
<a href="../../articles/assets/poc/poc_worm_core_persists/04_core_map_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_worm_core_persists.jpg" alt="線蟲腦核心" width="200" height="200"><b>&#9654;</b><span>線蟲腦核心</span></a>
</div>
</details>

<details class="vall"><summary><b>醫學與生物</b> (9)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_bone_trabecular_thickness/01_scene_truth.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_bone_trabecular_thickness.jpg" alt="骨小樑厚度" width="200" height="200"><span>骨小樑厚度</span></a>
<a href="../../articles/assets/poc/poc_cell_counting/01_scene_dense.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_cell_counting.jpg" alt="重疊細胞計數" width="200" height="200"><span>重疊細胞計數</span></a>
<a href="../../articles/assets/poc/poc_colocalization_crosstalk/01_scene_channels.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_colocalization_crosstalk.jpg" alt="螢光共定位" width="200" height="200"><span>螢光共定位</span></a>
<a href="../../articles/assets/poc/poc_mri_bias_field/01_controls.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_mri_bias_field.jpg" alt="MRI 偏置場" width="200" height="200"><span>MRI 偏置場</span></a>
<a href="../../articles/assets/poc/poc_nuclei_ploidy/01_histograms.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_nuclei_ploidy.jpg" alt="細胞核倍性" width="200" height="200"><span>細胞核倍性</span></a>
<a href="../../articles/assets/poc/poc_vessel_network/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_vessel_network.jpg" alt="血管網路" width="200" height="200"><span>血管網路</span></a>
<a href="../../articles/assets/poc/poc_wound_area_tracking/06_healing_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_wound_area_tracking.jpg" alt="創面面積" width="200" height="200"><b>&#9654;</b><span>創面面積</span></a>
<a href="../../articles/assets/poc/poc_physarum_maze/02_maze_tubes_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_physarum_maze.jpg" alt="黏菌迷宮" width="200" height="200"><b>&#9654;</b><span>黏菌迷宮</span></a>
<a href="../../articles/assets/poc/poc_physarum_transport/01_transport_tubes_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_physarum_transport.jpg" alt="黏菌最佳傳輸" width="200" height="200"><b>&#9654;</b><span>黏菌最佳傳輸</span></a>
</div>
</details>

<details class="vall"><summary><b>天文與環境</b> (21)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_allsky_cloud_cover/01_jacobian.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_allsky_cloud_cover.jpg" alt="全天相機雲量" width="200" height="200"><span>全天相機雲量</span></a>
<a href="../../articles/assets/poc/poc_astro_photometry/01_stack_scaling.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_astro_photometry.jpg" alt="恆星測光精度" width="200" height="200"><span>恆星測光精度</span></a>
<a href="../../articles/assets/poc/poc_change_detection_misreg/01_plot_fp_vs_shift.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_change_detection_misreg.jpg" alt="變化偵測" width="200" height="200"><span>變化偵測</span></a>
<a href="../../articles/assets/poc/poc_datacenter_thermal_field/01_scene_truth.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_datacenter_thermal_field.jpg" alt="三維熱場重建" width="200" height="200"><span>三維熱場重建</span></a>
<a href="../../articles/assets/poc/poc_dem_terrain/05_terrain_flight.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dem_terrain.jpg" alt="地形量測" width="200" height="200"><b>&#9654;</b><span>地形量測</span></a>
<a href="../../articles/assets/poc/poc_exoplanet_transit/01_scene_starfield.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_exoplanet_transit.jpg" alt="系外行星凌星" width="200" height="200"><span>系外行星凌星</span></a>
<a href="../../articles/assets/poc/poc_geodetic_height_frames/01_geoid_frames.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_geodetic_height_frames.jpg" alt="座標高程陷阱" width="200" height="200"><span>座標高程陷阱</span></a>
<a href="../../articles/assets/poc/poc_leaf_disease_area/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_leaf_disease_area.jpg" alt="葉片病斑" width="200" height="200"><span>葉片病斑</span></a>
<a href="../../articles/assets/poc/poc_pv_thermal_survey/01_norm_table.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_pv_thermal_survey.jpg" alt="光電熱影像" width="200" height="200"><span>光電熱影像</span></a>
<a href="../../articles/assets/poc/poc_real_sky_photometry/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_sky_photometry.jpg" alt="實拍深空" width="200" height="200"><span>實拍深空</span></a>
<a href="../../articles/assets/poc/poc_river_surface_velocity/13_accumulate_pairs.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_river_surface_velocity.jpg" alt="河川表面流速" width="200" height="200"><b>&#9654;</b><span>河川表面流速</span></a>
<a href="../../articles/assets/poc/poc_sea_ice_concentration/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_sea_ice_concentration.jpg" alt="海冰密集度" width="200" height="200"><span>海冰密集度</span></a>
<a href="../../articles/assets/poc/poc_search_sweep_width/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_search_sweep_width.jpg" alt="搜索掃描寬度" width="200" height="200"><span>搜索掃描寬度</span></a>
<a href="../../articles/assets/poc/poc_solar_limb_darkening/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_solar_limb_darkening.jpg" alt="臨邊昏暗" width="200" height="200"><span>臨邊昏暗</span></a>
<a href="../../articles/assets/poc/poc_star_astrometry/01_snr_sweep.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_star_astrometry.jpg" alt="恆星位置精度" width="200" height="200"><span>恆星位置精度</span></a>
<a href="../../articles/assets/poc/poc_tree_ring_dendro/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_tree_ring_dendro.jpg" alt="年輪寬度" width="200" height="200"><span>年輪寬度</span></a>
<a href="../../articles/assets/poc/poc_vegetation_cover/01_mixed_pixel_response.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_vegetation_cover.jpg" alt="植被覆蓋率" width="200" height="200"><span>植被覆蓋率</span></a>
<a href="../../articles/assets/poc/poc_water_level/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_water_level.jpg" alt="河川水位" width="200" height="200"><span>河川水位</span></a>
<a href="../../articles/assets/poc/poc_rover_slip_risk_path/03_rover_slip_update.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_rover_slip_risk_path.jpg" alt="火星車輪打滑" width="200" height="200"><b>&#9654;</b><span>火星車輪打滑</span></a>
<a href="../../articles/assets/poc/poc_geodetic_benchmarks_real/01_residual_sorted.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_geodetic_benchmarks_real.jpg" alt="兩種高程(實測)" width="200" height="200"><span>兩種高程(實測)</span></a>
<a href="../../articles/assets/poc/poc_gravitational_lens_invariants/10_source_crossing.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_gravitational_lens_invariants.jpg" alt="重力透鏡" width="200" height="200"><b>&#9654;</b><span>重力透鏡</span></a>
</div>
</details>

<details class="vall"><summary><b>鑑識與文件</b> (4)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_document_scan/01_rectify_zero_points.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_document_scan.jpg" alt="文件校正" width="200" height="200"><span>文件校正</span></a>
<a href="../../articles/assets/poc/poc_forensics_roc/01_score_maps.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_forensics_roc.jpg" alt="竄改偵測 ROC" width="200" height="200"><span>竄改偵測 ROC</span></a>
<a href="../../articles/assets/poc/poc_fresco_craquelure/01_ridge_ops.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_fresco_craquelure.jpg" alt="畫作龜裂網" width="200" height="200"><span>畫作龜裂網</span></a>
<a href="../../articles/assets/poc/poc_prnu_camera_fingerprint/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_prnu_camera_fingerprint.jpg" alt="相機指紋" width="200" height="200"><span>相機指紋</span></a>
</div>
</details>

<details class="vall"><summary><b>自動駕駛</b> (13)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_car_parking/04_parking_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_car_parking.jpg" alt="最短轉彎停車" width="200" height="200"><b>&#9654;</b><span>最短轉彎停車</span></a>
<a href="../../articles/assets/poc/poc_driving_school/05_drive_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_school.jpg" alt="駕訓班" width="200" height="200"><b>&#9654;</b><span>駕訓班</span></a>
<a href="../../articles/assets/poc/poc_ttc_rss/06_approach_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_ttc_rss.jpg" alt="碰撞時間與 RSS" width="200" height="200"><b>&#9654;</b><span>碰撞時間與 RSS</span></a>
<a href="../../articles/assets/poc/poc_world_terrain/06_drive_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_world_terrain.jpg" alt="擴展世界" width="200" height="200"><b>&#9654;</b><span>擴展世界</span></a>
<a href="../../articles/assets/poc/poc_driving_longitudinal/01_drive_with_time.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_longitudinal.jpg" alt="慣性與坡道" width="200" height="200"><b>&#9654;</b><span>慣性與坡道</span></a>
<a href="../../articles/assets/poc/poc_driving_weather/01_sun_day.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_weather.jpg" alt="太陽與天氣" width="200" height="200"><b>&#9654;</b><span>太陽與天氣</span></a>
<a href="../../articles/assets/poc/poc_driving_endless_map/01_minimap_stream.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_endless_map.jpg" alt="無盡地圖" width="200" height="200"><b>&#9654;</b><span>無盡地圖</span></a>
<a href="../../articles/assets/poc/poc_driving_traffic/01_dashcam_occlusion.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_traffic.jpg" alt="交通與死角" width="200" height="200"><b>&#9654;</b><span>交通與死角</span></a>
<a href="../../articles/assets/poc/poc_driving_decisions/01_decisions_mirrors_ambulance.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_decisions.jpg" alt="判斷場景" width="200" height="200"><b>&#9654;</b><span>判斷場景</span></a>
<a href="../../articles/assets/poc/poc_driving_lateral/01_lateral_dashcam.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_lateral.jpg" alt="橫向運動" width="200" height="200"><b>&#9654;</b><span>橫向運動</span></a>
<a href="../../articles/assets/poc/poc_driving_humanoids/03_humanoids_crossing.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_humanoids.jpg" alt="人形機器人過馬路" width="200" height="200"><b>&#9654;</b><span>人形機器人過馬路</span></a>
<a href="../../articles/assets/poc/poc_driving_crossing/01_crossing_dashcam.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_crossing.jpg" alt="平交道與路口" width="200" height="200"><b>&#9654;</b><span>平交道與路口</span></a>
<a href="../../articles/assets/poc/poc_driving_pass/01_overtake_dashcam.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_pass.jpg" alt="超車與死角" width="200" height="200"><b>&#9654;</b><span>超車與死角</span></a>
</div>
</details>

<details class="vall"><summary><b>數學圖像</b> (7)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_one_stroke_epicycles/07_epicycles.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_one_stroke_epicycles.jpg" alt="一筆畫與周轉圓" width="200" height="200"><b>&#9654;</b><span>一筆畫與周轉圓</span></a>
<a href="../../articles/assets/poc/poc_complex_plane_fields/01_rational.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_complex_plane_fields.jpg" alt="複數平面" width="200" height="200"><span>複數平面</span></a>
<a href="../../articles/assets/poc/poc_theorems_as_pictures/01_apollonian.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_theorems_as_pictures.jpg" alt="定理即檢驗" width="200" height="200"><span>定理即檢驗</span></a>
<a href="../../articles/assets/poc/poc_beats_fringes_and_screens/01_membrane.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_beats_fringes_and_screens.jpg" alt="拍頻只有一個" width="200" height="200"><span>拍頻只有一個</span></a>
<a href="../../articles/assets/poc/poc_what_a_picture_cannot_check/01_rk4.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_what_a_picture_cannot_check.jpg" alt="圖無法驗證的" width="200" height="200"><span>圖無法驗證的</span></a>
<a href="../../articles/assets/poc/poc_illusions_and_perpetual_drawing/14_loop.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_illusions_and_perpetual_drawing.jpg" alt="無限繪圖" width="200" height="200"><b>&#9654;</b><span>無限繪圖</span></a>
<a href="../../articles/assets/poc/poc_calipers_under_illusion/01_caliper_on_cafe_wall.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_calipers_under_illusion.jpg" alt="錯覺檢驗量具" width="200" height="200"><span>錯覺檢驗量具</span></a>
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

## 能看到什麼/測得的數字

所有數字都是相對各 PoC 自行植入的真值(閉合式、解析解或公開值)的實測;執行 PoC 會印出相同的值。

<div class="vl" markdown="1">

**影像檢測與外觀量測**

- [薄缺陷檢出極限](../../articles/assets/poc/poc_real_defect_floor/02_defect_floor_sweep.gif) (GIF): 在實拍背景(磚牆)與雜訊量相同的合成背景上,逐漸加深同一個植入缺陷。 **即使雜訊量相同,實拍背景的檢出極限也是合成背景的 2.03〜3.47 倍(針對位置與振幅已知的缺陷)。** [原始碼](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_defect_floor.py)
- [主動輪廓](../../articles/assets/poc/poc_active_contours/06_u_shape_snakes.mp4) (影片): 古典 snake(紅)進不了 U 形凹槽,GVF(藍)能深入到底。綠色是真實邊緣。 **只把外力換成 GVF,Dice 達到 0.993(相對真實邊緣)。** [原始碼](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_active_contours.py)
- [DIC 應變](../../articles/assets/poc/poc_dic_strain/05_tensile_ramp.mp4) (影片): 拉伸試驗加載過程中,從散斑影像讀取應變圖(試驗機同時轉動 2 度)。 **真實應變 3000 µε。小應變因轉動只讀到 2341 µε,Green-Lagrange 為 2961 µε(理論 3005 µε)。** [原始碼](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dic_strain.py)

**三維量測與幾何處理**

- [景深合成](../../articles/assets/poc/poc_focus_stacking/05_focus_sweep.mp4) (影片): 對焦掃描 17 影格,全焦影像與深度圖逐步形成。 **全焦 PSNR 33.69 dB(中間 1 影格 28.52 dB),深度誤差 0.467 mm(有紋理區域)。** [原始碼](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_focus_stacking.py)
- [點雲對位](../../articles/assets/poc/poc_registration_basin/05_icp_basin_iterations.mp4) (影片): 從初始旋轉偏差 30 / 90 / 150 度開始,ICP 每次迭代 1 步。 **60 次迭代後的旋轉誤差:30 度與 90 度為 0.6 度(成功),150 度為 179.5 度(失敗)。** [原始碼](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_registration_basin.py)
- [料堆體積](../../articles/assets/poc/poc_stockpile_volume/07_scan_orbit.mp4) (影片): 繞料堆一周,把 3-D 掃描位置從 1 處增加到 3 處。顏色為內插面與真實面之差。 **庫存量誤差 +17.20 % → +0.05 %(真實底面;體積真值為閉合式 3572.6089 m³)。** [原始碼](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_stockpile_volume.py)

**X 光 CT 與體積資料處理**

- [CT 重建](../../articles/assets/poc/poc_ct_fidelity/01_recon_sweep.png) (圖): 以 180 → 12 個投影重新拍攝 Shepp-Logan 假體並重建。 **12 個投影的 FBP(RMSE 0.2576)甚至不如空白影像(0.2420)。質量檢算發現 -3.34 % 的缺損,修正為 -0.0099 %。** [原始碼](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_fidelity.py)
- [CT 孔洞](../../articles/assets/poc/poc_ct_void_morphology/13_section_sweep.mp4) (影片): 孔洞率幾乎相同的 2 種接合層,一邊掃描斷面一邊旋轉 3-D 孔洞(影片 4.3 MB)。 **孔洞率為 2.46 % 對 2.63 %,但到界面距離的中位數為 60.0 µm 對 10.0 µm。** [原始碼](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_void_morphology.py)

**光學、干涉、偏光**

- [白光干涉段差](../../articles/assets/poc/poc_interferometry_step/05_step_sweep.mp4) (影片): 植入的段差從 0 增加到 0.90 µm,以包絡線法與相移法量測。 **雜訊 1 % 時偏差在 2.4 nm 以內(段差 50〜500 nm)。相移法在 0.153 µm 處跳變 λ/2。** [原始碼](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_interferometry_step.py)
- [偏光去鏡面反射](../../articles/assets/poc/poc_polarization_specular/03_separation.png) (圖): 以偏光去除鏡面反射的結果,以及殘留誤差的形狀。 **漫反射分量的誤差與閉合式 R_p·E 一致,在布魯斯特角 56.31 度處為 0。** [原始碼](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_polarization_specular.py)
- [光彈應力](../../articles/assets/poc/poc_photoelasticity/03_load_and_isoclinics.mp4) (影片): 圓盤加載時條紋不斷湧出,旋轉偏光片時等傾線隨之移動。 **中心條紋級數 2.38(與閉合式一致)。op 的偏光系統與教科書公式最大差 2.2e-16。** [原始碼](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_photoelasticity.py)

**熱、聲學、時間序列**

- [熱影像缺陷深度](../../articles/assets/poc/poc_thermography_ndt/02_depth_map.png) (圖): 根據閃光加熱後的表面溫度讀出 16 個剝離缺陷深度的地圖。 **深 0.5 mm、直徑 2 mm 的缺陷:擬合時間窗 25 秒時為 +612 %,縮到 4 秒時為 -9 %。** [原始碼](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_thermography_ndt.py)
- [微振動放大](../../articles/assets/poc/poc_motion_magnification/05_magnify_video.mp4) (影片): 以 0.1 px 振動的表面。左為原始影片,右為放大 10 倍的影片。 **真實振幅 0.1000 px,原始影片測得 0.10012,放大後測得 0.10013 px。放大幫助觀看,不提升量測。** [原始碼](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_motion_magnification.py)

**機器人與空間感知**

- [複眼光場](../../articles/assets/poc/poc_compound_eye/02_compound_eye_superposition.png) (圖): 把小眼陣列合成為光場感測器,以 N 個小眼疊加同一點。 下一步是以蒼蠅的接線圖(連接體)處理這個光場 —— 見下方的連接體展品。 **SNR 增益:N=5 時 2.25(√5 = 2.24),N=49 時 5.33(√49 = 7.00)。** [原始碼](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_compound_eye.py)
- [插銷入孔](../../articles/assets/poc/poc_pegsim_insertion/04_pegsim_insert_corrected.gif) (GIF): 以腕部相機量出孔的位置並靠近,再以柔性手腕插入插銷(MuJoCo)。 **伺服 7 次後真實偏差 2.24 → 0.03 mm。有校正的插入 12 / 12 成功。** [原始碼](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pegsim_insertion.py)
- [空氣曲棍球](../../articles/assets/poc/poc_air_hockey_intercept/02_airhockey_prediction_cone_narrows.gif) (GIF): 以低解析度相機追蹤冰球,預測它與防守線的交點。影格越多,預測帶越窄。 **交點的 95 % 帶:N = 3 影格時 145 mm → N = 16 影格時 7 mm。** [原始碼](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_air_hockey_intercept.py)
- [視觸覺感測器](../../articles/assets/poc/poc_tacsim_elastic_membrane/03_tacsim_force_sweep.gif) (GIF): 以球壓彈性膜並增大載荷,從膜的影像讀取接觸半徑。 **相對 Hertz 閉合式:接觸半徑誤差 0.05〜0.26 %,載荷誤差 0.14〜0.79 %(0.02〜0.12 N)。** [原始碼](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_tacsim_elastic_membrane.py)

**桌球與運動量測**

- [桌球彈跳](../../articles/assets/poc/poc_table_tennis_bounce/01_drop_test.mp4) (影片): ITTF 球桌測試:從 30 cm 落球,從影片讀取彈起高度。 **從影片讀出的彈起高度 23.0 cm(真值 23.0 cm)。** [原始碼](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_table_tennis_bounce.py)
- [桌球旋轉](../../articles/assets/poc/poc_table_tennis_spin/01_side_three_serves.mp4) (影片): 以相同速度與方向擊出的 3 球:上旋下沉,下旋上浮。 **落點 x = 0.49 / 0.75 / 1.12 m。以從弧線讀出的旋轉預測的落點,4 球都與真值相差 2 cm 以內。** [原始碼](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_table_tennis_spin.py)
- [來回與讀取誤差](../../articles/assets/poc/poc_table_tennis_rally_loop/02_height_misread.mp4) (影片): 把球高讀高 5 cm,瞄準計算會選更低的彈道,球落得更近。 **比目標近 10.2 cm。擊球前的一階預測 2.06 × 5 cm = 10.3 cm。** [原始碼](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_table_tennis_rally_loop.py)

**自動駕駛**

- [交通與死角](../../articles/assets/poc/poc_driving_traffic/01_dashcam_occlusion.mp4) (影片): 孩子從路邊停車後跑出。以與背景的差(無學習)偵測並停車。 **在 t = 7.30 s 偵測到(比真值晚 0.133 s),在孩子路線前 7.09 m 停車。** [原始碼](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_driving_traffic.py)
- [平交道與路口](../../articles/assets/poc/poc_driving_crossing/01_crossing_dashcam.mp4) (影片): 在平交道前停車,警報期間等待,左右確認後通過(駕駛視角)。 **守規則的 240 人違規 0、列車到達時軌道上 0 人。警報中進入的版本 157 人違規,其中 23 人在軌道上。** [原始碼](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_driving_crossing.py)
- [道路反射鏡](../../articles/assets/poc/poc_driving_pass/03_mirror_tjunction.mp4) (影片): 在視線差的 T 字路口,以光線追蹤繪製凸面反射鏡中的車並讀取距離。 **距鏡子 29 m 的車,依像的大小讀成 139 m 外(閉合式縱向讀數 140 m)。** [原始碼](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_driving_pass.py)
- [碰撞時間與 RSS](../../articles/assets/poc/poc_ttc_rss/06_approach_gif.gif) (GIF): 由對向車的光流求出碰撞時間 τ,遇停止車輛依 RSS 安全距離停車。 **在 RSS 判為危險的 t = 6.0 s 制動,於 10.25 m 前停車。** [原始碼](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ttc_rss.py)

**連接體與神經**

- [複眼到大腦](../../articles/assets/poc/poc_eye_to_brain/01_eye_sweep.gif) (GIF): 把蒼蠅右眼 1 個小眼的刺激沿眼的一行移動,輸入大腦接線圖(連接體)(GIF 4.4 MB)。 **刺激柱位置與響應重心的相關:連接體 -0.92,保度隨機重連 +0.01。** [原始碼](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_eye_to_brain.py)
- [蒼蠅腦波](../../articles/assets/poc/poc_malecns_activity_wave/01_activity_wave_connectome_vs_shuffle.gif) (GIF): 右視葉的刺激沿真實接線(左)與保度重連的接線(右)傳播。 **真實接線中活動平均距離用 17 步從 88 → 230 µm 擴展;重連後 3 步就散到 300 µm。** [原始碼](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_malecns_activity_wave.py)
- [小鼠視皮質波](../../articles/assets/poc/poc_microns_brain_wave/04_wave_on_wiring.gif) (GIF): 把 148 根已校對軸突的實測響應,送入小鼠視皮質 1 mm³ 的真實接線(MICrONS)。 **與實測的相關:真實接線 0.085,保度隨機重連 0.048。** [原始碼](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_microns_brain_wave.py)

**機器人之眼(由 Fullseye 負責感知)**

- [人形機器人雙眼](../../articles/assets/media/evis_stereo_fullseye.mp4) (影片): 肌肉骨骼人形機器人用筷子擊豆,以自己的雙眼(瞳距 64 mm)拍攝,Fullseye 每影格計算立體視差 → 深度。 **到豆距離誤差:中位數 0.66 %,最大 1.91 %(可讀 229 / 241 影格)。** [原始碼](https://github.com/furuse-kazufumi/fullseye/blob/master/tools/gen_evis_media.py)
- [筷尖相機追蹤豆子](../../articles/assets/media/evis_bean_track_fullseye.mp4) (影片): 在同一場景的筷尖相機畫面中,Fullseye 偵測並追蹤豆子。 **可見的 163 影格全部偵測到(163 / 163),重心誤差相對真值中位數 0.10 px。** [原始碼](https://github.com/furuse-kazufumi/fullseye/blob/master/tools/gen_evis_media.py)

</div>

## Fullseye 是什麼

透過 MCP 與 RAG,把包含光學設計、三維量測等感測在內的物理模擬與古典影像處理交給 AI,讓它針對每個課題思考組合方式,並在型別一致性檢查與帶真值的評估下以對話方式解決課題的平台。開放原始碼(Apache-2.0)。

<details markdown="1">
<summary><b>試試看</b> (Python 3.11)</summary>

```
pip install fullseye
git clone https://github.com/furuse-kazufumi/fullseye
cd fullseye
python examples/poc_focus_stacking.py
```

景深合成 PoC 約 20 秒跑完,印出相對真值的數字與 `PASS`。圖寫入 `out/figures/poc_focus_stacking/`。

</details>

<details markdown="1">
<summary><b>連結</b></summary>

- [GitHub(原始碼)](https://github.com/furuse-kazufumi/fullseye)
- [圖庫(全部圖)](../../GALLERY.en.md)
- [尋找運算子 / 從 AI(RAG)使用](../../AI_RAG_GUIDE.tw.md) · [從 MCP 使用](../../MCP.md) _(ja)_
- [文件索引](../../README.tw.md)

</details>

<details markdown="1">
<summary><b>論文資訊</b></summary>

- **題目**: Fullseye：型付き演算子と物理シミュレーションに基づく画像検査・三次元計測基盤 _(ja)_ (基於型別化運算子與物理模擬的影像檢測與三維量測平台)
- **作者**: 古瀬 和文(個人研究者)
- **發表**: ViEW2026 視覺技術實際應用研討會
- **論文 PDF**: 2026-11-26 起公開

**摘要(由日文翻譯)**: 本文提出開放原始碼平台 Fullseye:把影像檢測與三維量測的處理組裝成宣告了輸入輸出資料型別的運算子鏈,以物理與成像模擬產生的真值進行定量評估,並記錄處理流程、評估與失敗條件以便重複使用。它由約 3,000 個型別化運算子、在執行前拒絕型別不一致的檢查、多語言運算子檢索(RAG)以及 200 多個帶真值的驗證程式組成。本文報告代表例的定量評估,以及合成、實測、實機三個驗證階段的區分。

</details>
