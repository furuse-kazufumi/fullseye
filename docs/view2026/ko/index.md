<div class="vlang" markdown="1">

[日本語](../index.md) · [English](../en/index.md) · [简体中文](../zh/index.md) · [繁體中文](../tw/index.md) · **한국어** · [Deutsch](../de/index.md) · [हिन्दी](../hi/index.md)

</div>

# Fullseye — ViEW2026

물리 시뮬레이션과 영상 처리를 AI와 조합하고 참값으로 확인한다.

타일을 누르면 동영상·그림이 열립니다(▶ = 움직임).

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

## 하이라이트

<div class="vg">
<a href="../../articles/assets/poc/poc_real_defect_floor/02_defect_floor_sweep.gif"><img src="../thumbs/poc_real_defect_floor.jpg" alt="얇은 결함 검출 한계" loading="lazy" width="320" height="320"><b>&#9654;</b><span>얇은 결함 검출 한계</span></a>
<a href="../../articles/assets/poc/poc_active_contours/06_u_shape_snakes.mp4"><img src="../thumbs/poc_active_contours.jpg" alt="능동 윤곽" loading="lazy" width="320" height="320"><b>&#9654;</b><span>능동 윤곽</span></a>
<a href="../../articles/assets/poc/poc_dic_strain/05_tensile_ramp.mp4"><img src="../thumbs/poc_dic_strain.jpg" alt="DIC 변형률" loading="lazy" width="320" height="320"><b>&#9654;</b><span>DIC 변형률</span></a>
<a href="../../articles/assets/poc/poc_focus_stacking/05_focus_sweep.mp4"><img src="../thumbs/poc_focus_stacking.jpg" alt="초점 합성" loading="lazy" width="320" height="320"><b>&#9654;</b><span>초점 합성</span></a>
<a href="../../articles/assets/poc/poc_registration_basin/05_icp_basin_iterations.mp4"><img src="../thumbs/poc_registration_basin.jpg" alt="점군 정합" loading="lazy" width="320" height="320"><b>&#9654;</b><span>점군 정합</span></a>
<a href="../../articles/assets/poc/poc_stockpile_volume/07_scan_orbit.mp4"><img src="../thumbs/poc_stockpile_volume.jpg" alt="적치물 부피" loading="lazy" width="320" height="320"><b>&#9654;</b><span>적치물 부피</span></a>
<a href="../../articles/assets/poc/poc_ct_fidelity/01_recon_sweep.png"><img src="../thumbs/poc_ct_fidelity.jpg" alt="CT 재구성" loading="lazy" width="320" height="320"><span>CT 재구성</span></a>
<a href="../../articles/assets/poc/poc_ct_void_morphology/13_section_sweep.mp4"><img src="../thumbs/poc_ct_void_morphology.jpg" alt="CT 보이드" loading="lazy" width="320" height="320"><b>&#9654;</b><span>CT 보이드</span></a>
<a href="../../articles/assets/poc/poc_interferometry_step/05_step_sweep.mp4"><img src="../thumbs/poc_interferometry_step.jpg" alt="백색광 간섭 단차" loading="lazy" width="320" height="320"><b>&#9654;</b><span>백색광 간섭 단차</span></a>
<a href="../../articles/assets/poc/poc_polarization_specular/03_separation.png"><img src="../thumbs/poc_polarization_specular.jpg" alt="편광 정반사 제거" loading="lazy" width="320" height="320"><span>편광 정반사 제거</span></a>
<a href="../../articles/assets/poc/poc_photoelasticity/03_load_and_isoclinics.mp4"><img src="../thumbs/poc_photoelasticity.jpg" alt="광탄성 응력" loading="lazy" width="320" height="320"><b>&#9654;</b><span>광탄성 응력</span></a>
<a href="../../articles/assets/poc/poc_thermography_ndt/02_depth_map.png"><img src="../thumbs/poc_thermography_ndt.jpg" alt="열화상 결함 깊이" loading="lazy" width="320" height="320"><span>열화상 결함 깊이</span></a>
<a href="../../articles/assets/poc/poc_motion_magnification/05_magnify_video.mp4"><img src="../thumbs/poc_motion_magnification.jpg" alt="미세 진동 확대" loading="lazy" width="320" height="320"><b>&#9654;</b><span>미세 진동 확대</span></a>
<a href="../../articles/assets/poc/poc_table_tennis_bounce/01_drop_test.mp4"><img src="../thumbs/poc_table_tennis_bounce.jpg" alt="탁구공 바운드" loading="lazy" width="320" height="320"><b>&#9654;</b><span>탁구공 바운드</span></a>
<a href="../../articles/assets/poc/poc_compound_eye/02_compound_eye_superposition.png"><img src="../thumbs/poc_compound_eye.jpg" alt="겹눈 라이트 필드" loading="lazy" width="320" height="320"><span>겹눈 라이트 필드</span></a>
<a href="../../articles/assets/poc/poc_pegsim_insertion/04_pegsim_insert_corrected.gif"><img src="../thumbs/poc_pegsim_insertion.jpg" alt="펙 삽입" loading="lazy" width="320" height="320"><b>&#9654;</b><span>펙 삽입</span></a>
<a href="../../articles/assets/poc/poc_air_hockey_intercept/02_airhockey_prediction_cone_narrows.gif"><img src="../thumbs/poc_air_hockey_intercept.jpg" alt="에어하키" loading="lazy" width="320" height="320"><b>&#9654;</b><span>에어하키</span></a>
<a href="../../articles/assets/poc/poc_tacsim_elastic_membrane/03_tacsim_force_sweep.gif"><img src="../thumbs/poc_tacsim_elastic_membrane.jpg" alt="시각 촉각 센서" loading="lazy" width="320" height="320"><b>&#9654;</b><span>시각 촉각 센서</span></a>
<a href="../../articles/assets/poc/poc_table_tennis_spin/01_side_three_serves.mp4"><img src="../thumbs/poc_table_tennis_spin.jpg" alt="탁구공 회전" loading="lazy" width="320" height="320"><b>&#9654;</b><span>탁구공 회전</span></a>
<a href="../../articles/assets/poc/poc_table_tennis_rally_loop/02_height_misread.mp4"><img src="../thumbs/poc_table_tennis_rally_loop.jpg" alt="랠리와 판독 오차" loading="lazy" width="320" height="320"><b>&#9654;</b><span>랠리와 판독 오차</span></a>
<a href="../../articles/assets/poc/poc_driving_traffic/01_dashcam_occlusion.mp4"><img src="../thumbs/poc_driving_traffic.jpg" alt="교통과 사각" loading="lazy" width="320" height="320"><b>&#9654;</b><span>교통과 사각</span></a>
<a href="../../articles/assets/poc/poc_driving_crossing/01_crossing_dashcam.mp4"><img src="../thumbs/poc_driving_crossing.jpg" alt="건널목과 교차로" loading="lazy" width="320" height="320"><b>&#9654;</b><span>건널목과 교차로</span></a>
<a href="../../articles/assets/poc/poc_driving_pass/03_mirror_tjunction.mp4"><img src="../thumbs/poc_driving_pass.jpg" alt="커브 미러" loading="lazy" width="320" height="320"><b>&#9654;</b><span>커브 미러</span></a>
<a href="../../articles/assets/poc/poc_ttc_rss/06_approach_gif.gif"><img src="../thumbs/poc_ttc_rss.jpg" alt="충돌 시간과 RSS" loading="lazy" width="320" height="320"><b>&#9654;</b><span>충돌 시간과 RSS</span></a>
<a href="../../articles/assets/poc/poc_eye_to_brain/01_eye_sweep.gif"><img src="../thumbs/poc_eye_to_brain.jpg" alt="겹눈에서 뇌로" loading="lazy" width="320" height="320"><b>&#9654;</b><span>겹눈에서 뇌로</span></a>
<a href="../../articles/assets/poc/poc_malecns_activity_wave/01_activity_wave_connectome_vs_shuffle.gif"><img src="../thumbs/poc_malecns_activity_wave.jpg" alt="파리 뇌의 파동" loading="lazy" width="320" height="320"><b>&#9654;</b><span>파리 뇌의 파동</span></a>
<a href="../../articles/assets/poc/poc_microns_brain_wave/04_wave_on_wiring.gif"><img src="../thumbs/poc_microns_brain_wave.jpg" alt="마우스 시각피질 파동" loading="lazy" width="320" height="320"><b>&#9654;</b><span>마우스 시각피질 파동</span></a>
<a href="../../articles/assets/media/evis_stereo_fullseye.mp4"><img src="../thumbs/evis_stereo_depth.jpg" alt="휴머노이드 두 눈" loading="lazy" width="320" height="320"><b>&#9654;</b><span>휴머노이드 두 눈</span></a>
<a href="../../articles/assets/media/evis_bean_track_fullseye.mp4"><img src="../thumbs/evis_bean_track.jpg" alt="젓가락 끝 카메라 추적" loading="lazy" width="320" height="320"><b>&#9654;</b><span>젓가락 끝 카메라 추적</span></a>
</div>

## 시리즈 기사 (Qiita의 영어 기사)

<div class="vser">
<a href="https://qiita.com/furuse-kazufumi/items/8a8f23e53b19ee8cdc10"><img src="../thumbs/series_museum.gif" alt="지면의 계측관" loading="lazy" width="480" height="270"><strong>지면의 계측관</strong><span>참값을 직접 심은 PoC 전시관</span></a>
<a href="https://qiita.com/furuse-kazufumi/items/a82bf9f341cc4f04ca75"><img src="../thumbs/series_table_tennis.gif" alt="탁구" loading="lazy" width="480" height="270"><strong>탁구</strong><span>바운드와 마찰을 영상으로 측정</span></a>
<a href="https://qiita.com/furuse-kazufumi/items/05de90f4d316cd7c681c"><img src="../thumbs/series_driving.gif" alt="자율주행" loading="lazy" width="480" height="270"><strong>자율주행</strong><span>정리와 두 번째 구현으로 채점</span></a>
<a href="https://qiita.com/furuse-kazufumi/items/638f0b0aa7865e17c67c"><img src="../thumbs/series_connectome.gif" alt="커넥톰(뇌 배선도)" loading="lazy" width="480" height="270"><strong>커넥톰(뇌 배선도)</strong><span>파리 시각 모델을 몸에 얹어 측정</span></a>
<a href="https://qiita.com/furuse-kazufumi/items/569720dbae0c6471c96e"><img src="../thumbs/series_humanoid.gif" alt="휴머노이드 운동회" loading="lazy" width="480" height="270"><strong>휴머노이드 운동회</strong><span>영상 처리가 심판을 보는 집 운동회</span></a>
</div>

## 전부 보기

PoC 218개와 로봇의 눈 4개. 그룹을 펼치면 썸네일이 나옵니다.

<noscript><p><a href="../../GALLERY.en.html">(JavaScript가 없으면 갤러리 페이지에서 모든 그림을 볼 수 있습니다.)</a></p></noscript>

<details class="vall"><summary><b>로봇의 눈(Fullseye가 지각 담당)</b> (4)</summary>
<div class="vg vs">
<a href="../../articles/assets/media/evis_stereo_fullseye.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/evis_stereo_depth.jpg" alt="휴머노이드 두 눈" width="200" height="200"><b>&#9654;</b><span>휴머노이드 두 눈</span></a>
<a href="../../articles/assets/media/evis_bean_track_fullseye.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/evis_bean_track.jpg" alt="젓가락 끝 카메라 추적" width="200" height="200"><b>&#9654;</b><span>젓가락 끝 카메라 추적</span></a>
<a href="../../view2026/media/evis_fullseye_walk.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/evis_walk_rgb_depth_dvs.jpg" alt="보행을 RGB·깊이·DVS로" width="200" height="200"><b>&#9654;</b><span>보행을 RGB·깊이·DVS로</span></a>
<a href="../../view2026/media/vision_adaptive_walk.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/walker2d_terrain_vision.jpg" alt="단차를 보고 보행 선택" width="200" height="200"><span>단차를 보고 보행 선택</span></a>
</div>
</details>

<details class="vall"><summary><b>산업 검사</b> (32)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_barcode_1d/01_misread_split.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_barcode_1d.jpg" alt="1차원 바코드" width="200" height="200"><span>1차원 바코드</span></a>
<a href="../../articles/assets/poc/poc_battery_electrode_tortuosity/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_battery_electrode_tortuosity.jpg" alt="전극 굴곡도" width="200" height="200"><span>전극 굴곡도</span></a>
<a href="../../articles/assets/poc/poc_bearing_diagnosis/01_envelope_vs_raw.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_bearing_diagnosis.jpg" alt="베어링 이상 진단" width="200" height="200"><span>베어링 이상 진단</span></a>
<a href="../../articles/assets/poc/poc_bump_coplanarity/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_bump_coplanarity.jpg" alt="범프 공평면성" width="200" height="200"><span>범프 공평면성</span></a>
<a href="../../articles/assets/poc/poc_crack_width/01_width_sweep.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_crack_width.jpg" alt="균열 폭" width="200" height="200"><span>균열 폭</span></a>
<a href="../../articles/assets/poc/poc_fabric_defect/01_auc_by_type.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_fabric_defect.jpg" alt="직물 결함" width="200" height="200"><span>직물 결함</span></a>
<a href="../../articles/assets/poc/poc_leak_localization/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_leak_localization.jpg" alt="소리로 누수 탐지" width="200" height="200"><span>소리로 누수 탐지</span></a>
<a href="../../articles/assets/poc/poc_machine_condition_fusion/01_scene_machine.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_machine_condition_fusion.jpg" alt="설비 보전 융합" width="200" height="200"><span>설비 보전 융합</span></a>
<a href="../../articles/assets/poc/poc_matrix_code_reading/01_symbol_and_errors.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_matrix_code_reading.jpg" alt="매트릭스 코드" width="200" height="200"><span>매트릭스 코드</span></a>
<a href="../../articles/assets/poc/poc_moire_screen/01_failure_split_plot.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_moire_screen.jpg" alt="디스플레이 모아레" width="200" height="200"><span>디스플레이 모아레</span></a>
<a href="../../articles/assets/poc/poc_print_registration/01_plates.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_print_registration.jpg" alt="인쇄 판 어긋남" width="200" height="200"><span>인쇄 판 어긋남</span></a>
<a href="../../articles/assets/poc/poc_real_defect_floor/02_defect_floor_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_defect_floor.jpg" alt="얇은 결함 한계" width="200" height="200"><b>&#9654;</b><span>얇은 결함 한계</span></a>
<a href="../../articles/assets/poc/poc_real_texture_invariance/01_textures.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_texture_invariance.jpg" alt="실사 텍스처 회전" width="200" height="200"><span>실사 텍스처 회전</span></a>
<a href="../../articles/assets/poc/poc_recycling_sorting/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_recycling_sorting.jpg" alt="폐기물 선별" width="200" height="200"><span>폐기물 선별</span></a>
<a href="../../articles/assets/poc/poc_solar_el_inspection/01_zero_point_map.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_solar_el_inspection.jpg" alt="태양전지 EL" width="200" height="200"><span>태양전지 EL</span></a>
<a href="../../articles/assets/poc/poc_solder_fillet_aoi/01_ring_lut.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_solder_fillet_aoi.jpg" alt="솔더 AOI" width="200" height="200"><span>솔더 AOI</span></a>
<a href="../../articles/assets/poc/poc_spc/01_spc_xbar_chart.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_spc.jpg" alt="통계적 공정 관리" width="200" height="200"><span>통계적 공정 관리</span></a>
<a href="../../articles/assets/poc/poc_mt_hidden_fault/01_mt_hidden_cloud.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_mt_hidden_fault.jpg" alt="MT법 이상 탐지" width="200" height="200"><span>MT법 이상 탐지</span></a>
<a href="../../articles/assets/poc/poc_text_region_truth/01_text_region_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_text_region_truth.jpg" alt="문자 영역 검출" width="200" height="200"><span>문자 영역 검출</span></a>
<a href="../../articles/assets/poc/poc_thermal_drift_metrology/01_separate_drifts.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_thermal_drift_metrology.jpg" alt="카메라 열 드리프트" width="200" height="200"><span>카메라 열 드리프트</span></a>
<a href="../../articles/assets/poc/poc_thermal_radiometry/01_floor.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_thermal_radiometry.jpg" alt="열화상과 온도" width="200" height="200"><span>열화상과 온도</span></a>
<a href="../../articles/assets/poc/poc_thermography_ndt/01_depth_table.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_thermography_ndt.jpg" alt="열화상 결함 깊이" width="200" height="200"><span>열화상 결함 깊이</span></a>
<a href="../../articles/assets/poc/poc_veiling_glare/01_verdict.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_veiling_glare.jpg" alt="미광" width="200" height="200"><span>미광</span></a>
<a href="../../articles/assets/poc/poc_emva1288_sensor/01_photon_transfer.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_emva1288_sensor.jpg" alt="EMVA 1288 측정" width="200" height="200"><b>&#9654;</b><span>EMVA 1288 측정</span></a>
<a href="../../articles/assets/poc/poc_web_roll_periodicity/01_scene_web.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_web_roll_periodicity.jpg" alt="반송 롤 결함" width="200" height="200"><span>반송 롤 결함</span></a>
<a href="../../articles/assets/poc/poc_weld_bead_profile/01_laser_images.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_weld_bead_profile.jpg" alt="용접 비드 단면" width="200" height="200"><span>용접 비드 단면</span></a>
<a href="../../articles/assets/poc/poc_weld_bead_scan_angle/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_weld_bead_scan_angle.jpg" alt="용접 비드 주사" width="200" height="200"><span>용접 비드 주사</span></a>
<a href="../../articles/assets/poc/poc_weld_radiograph_porosity/01_scene_radiograph.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_weld_radiograph_porosity.jpg" alt="용접 기공" width="200" height="200"><span>용접 기공</span></a>
<a href="../../articles/assets/poc/poc_glyph_typo_detection/01_sign_before_after.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_glyph_typo_detection.jpg" alt="이미지 오자 검출" width="200" height="200"><span>이미지 오자 검출</span></a>
<a href="../../articles/assets/poc/poc_print_layer_inspection/01_slice_stack.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_print_layer_inspection.jpg" alt="3D 프린트 층 검사" width="200" height="200"><span>3D 프린트 층 검사</span></a>
<a href="../../articles/assets/poc/poc_agv_fleet/01_agv_naive_vs_adg.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_agv_fleet.jpg" alt="AGV 창고" width="200" height="200"><b>&#9654;</b><span>AGV 창고</span></a>
<a href="../../articles/assets/poc/poc_am_thermal_to_ct/01_melt_pool_frames.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_am_thermal_to_ct.jpg" alt="적층 제조와 CT" width="200" height="200"><b>&#9654;</b><span>적층 제조와 CT</span></a>
</div>
</details>

<details class="vall"><summary><b>치수·형상 계측</b> (36)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_aoi_ct_traceability/01_aoi_and_ct.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_aoi_ct_traceability.jpg" alt="AOI·CT 대응" width="200" height="200"><span>AOI·CT 대응</span></a>
<a href="../../articles/assets/poc/poc_asbuilt_wall_deviation/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_asbuilt_wall_deviation.jpg" alt="준공 벽면 편차" width="200" height="200"><span>준공 벽면 편차</span></a>
<a href="../../articles/assets/poc/poc_battery_electrode_breathing/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_battery_electrode_breathing.jpg" alt="전극 호흡" width="200" height="200"><span>전극 호흡</span></a>
<a href="../../articles/assets/poc/poc_bilateral_asymmetry/01_floor_vs_spacing.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_bilateral_asymmetry.jpg" alt="좌우 비대칭" width="200" height="200"><span>좌우 비대칭</span></a>
<a href="../../articles/assets/poc/poc_dic_strain/05_tensile_ramp.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dic_strain.jpg" alt="DIC 변형률" width="200" height="200"><b>&#9654;</b><span>DIC 변형률</span></a>
<a href="../../articles/assets/poc/poc_die_tilt_tsv_overlay/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_die_tilt_tsv_overlay.jpg" alt="다이 기울기·TSV" width="200" height="200"><span>다이 기울기·TSV</span></a>
<a href="../../articles/assets/poc/poc_dimensional_inspection/01_slot_bias.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dimensional_inspection.jpg" alt="부품 치수 검사" width="200" height="200"><span>부품 치수 검사</span></a>
<a href="../../articles/assets/poc/poc_fiber_orientation/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_fiber_orientation.jpg" alt="섬유 배향" width="200" height="200"><span>섬유 배향</span></a>
<a href="../../articles/assets/poc/poc_gear_tooth_metrology/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_gear_tooth_metrology.jpg" alt="기어 치형" width="200" height="200"><span>기어 치형</span></a>
<a href="../../articles/assets/poc/poc_interferometry_step/05_step_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_interferometry_step.jpg" alt="백색광 간섭 단차" width="200" height="200"><b>&#9654;</b><span>백색광 간섭 단차</span></a>
<a href="../../articles/assets/poc/poc_metal_grain_size/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_metal_grain_size.jpg" alt="결정 입도" width="200" height="200"><span>결정 입도</span></a>
<a href="../../articles/assets/poc/poc_multibeam_bathymetry/17_survey.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_multibeam_bathymetry.jpg" alt="다중빔 측심" width="200" height="200"><b>&#9654;</b><span>다중빔 측심</span></a>
<a href="../../articles/assets/poc/poc_particle_sizing/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_particle_sizing.jpg" alt="입도 분포" width="200" height="200"><span>입도 분포</span></a>
<a href="../../articles/assets/poc/poc_photoelasticity/03_load_and_isoclinics.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_photoelasticity.jpg" alt="광탄성 응력" width="200" height="200"><b>&#9654;</b><span>광탄성 응력</span></a>
<a href="../../articles/assets/poc/poc_rail_corrugation/01_planted_components.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_rail_corrugation.jpg" alt="레일 파상 마모" width="200" height="200"><span>레일 파상 마모</span></a>
<a href="../../articles/assets/poc/poc_real_coin_metrology/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_coin_metrology.jpg" alt="실사 동전" width="200" height="200"><span>실사 동전</span></a>
<a href="../../articles/assets/poc/poc_screw_thread_metrology/01_zero_spectrum.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_screw_thread_metrology.jpg" alt="나사 윤곽" width="200" height="200"><span>나사 윤곽</span></a>
<a href="../../articles/assets/poc/poc_stockpile_volume/07_scan_orbit.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_stockpile_volume.jpg" alt="적치물 부피" width="200" height="200"><b>&#9654;</b><span>적치물 부피</span></a>
<a href="../../articles/assets/poc/poc_strain_history/05_history_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_strain_history.jpg" alt="크리프 변형률" width="200" height="200"><b>&#9654;</b><span>크리프 변형률</span></a>
<a href="../../articles/assets/poc/poc_surface_roughness/01_surface_components.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_surface_roughness.jpg" alt="표면 거칠기" width="200" height="200"><span>표면 거칠기</span></a>
<a href="../../articles/assets/poc/poc_tacsim_elastic_membrane/03_tacsim_force_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_tacsim_elastic_membrane.jpg" alt="시각 촉각 센서" width="200" height="200"><b>&#9654;</b><span>시각 촉각 센서</span></a>
<a href="../../articles/assets/poc/poc_tacsim_marker_shear/02_tacslip_stick_circle_shrinks.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_tacsim_marker_shear.jpg" alt="촉각 전단" width="200" height="200"><b>&#9654;</b><span>촉각 전단</span></a>
<a href="../../articles/assets/poc/poc_tactile_dipole_torque/02_tactorque_dipole_grows_with_M.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_tactile_dipole_torque.jpg" alt="촉각 쌍극자" width="200" height="200"><b>&#9654;</b><span>촉각 쌍극자</span></a>
<a href="../../articles/assets/poc/poc_granular_heap_repose/11_granular_datum_tilt_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_granular_heap_repose.jpg" alt="분체 더미" width="200" height="200"><b>&#9654;</b><span>분체 더미</span></a>
<a href="../../articles/assets/poc/poc_food_cutting_measure/01_cutting_track_force.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_food_cutting_measure.jpg" alt="식재료 절단" width="200" height="200"><b>&#9654;</b><span>식재료 절단</span></a>
<a href="../../articles/assets/poc/poc_tacdome_large_deformation/01_tacdome_press_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_tacdome_large_deformation.jpg" alt="돔 손끝 접촉" width="200" height="200"><b>&#9654;</b><span>돔 손끝 접촉</span></a>
<a href="../../articles/assets/poc/poc_polish_wipe_measure/01_polish_raster_wipe_coat.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_polish_wipe_measure.jpg" alt="연마와 닦기" width="200" height="200"><b>&#9654;</b><span>연마와 닦기</span></a>
<a href="../../articles/assets/poc/poc_powder_scoop_pour/03_scoop_stream_synthetic_frames.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_powder_scoop_pour.jpg" alt="분체 뜨기·붓기" width="200" height="200"><b>&#9654;</b><span>분체 뜨기·붓기</span></a>
<a href="../../articles/assets/poc/poc_powder_grinding_ae/07_psd_fining_during_grinding.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_powder_grinding_ae.jpg" alt="막자사발 분쇄" width="200" height="200"><b>&#9654;</b><span>막자사발 분쇄</span></a>
<a href="../../articles/assets/poc/poc_pxrd_phase_peel/01_phase_peel.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_pxrd_phase_peel.jpg" alt="X선 회절 상 분리" width="200" height="200"><b>&#9654;</b><span>X선 회절 상 분리</span></a>
<a href="../../articles/assets/poc/poc_dose_uniformity_from_grinding/01_cv_bias_decomposition.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dose_uniformity_from_grinding.jpg" alt="약 용량 균일성" width="200" height="200"><span>약 용량 균일성</span></a>
<a href="../../articles/assets/poc/poc_knife_tactile_toughness/06_cut_with_fingertip_pads.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_knife_tactile_toughness.jpg" alt="손끝으로 칼 잡기" width="200" height="200"><b>&#9654;</b><span>손끝으로 칼 잡기</span></a>
<a href="../../articles/assets/poc/poc_measurement_system_analysis/16_breakdown_movie.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_measurement_system_analysis.jpg" alt="게이지 R&R" width="200" height="200"><b>&#9654;</b><span>게이지 R&R</span></a>
<a href="../../articles/assets/poc/poc_zernike_aberrations/06_through_focus.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_zernike_aberrations.jpg" alt="제르니케 수차" width="200" height="200"><b>&#9654;</b><span>제르니케 수차</span></a>
<a href="../../articles/assets/poc/poc_attention_identities/01_attention_masks.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_attention_identities.jpg" alt="어텐션 항등식" width="200" height="200"><span>어텐션 항등식</span></a>
<a href="../../articles/assets/poc/poc_residue_crt/03_residue_rotation_needle.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_residue_crt.jpg" alt="잉여 정리 위상" width="200" height="200"><b>&#9654;</b><span>잉여 정리 위상</span></a>
</div>
</details>

<details class="vall"><summary><b>3-D 형상</b> (18)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_battery_ct_degradation/01_xray_projection.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_battery_ct_degradation.jpg" alt="배터리 CT 열화" width="200" height="200"><span>배터리 CT 열화</span></a>
<a href="../../articles/assets/poc/poc_bev_sensor_fusion/01_scene_bev.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_bev_sensor_fusion.jpg" alt="BEV 센서 융합" width="200" height="200"><span>BEV 센서 융합</span></a>
<a href="../../articles/assets/poc/poc_cad_scan_deviation/14_align_orbit.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_cad_scan_deviation.jpg" alt="CAD·스캔 편차" width="200" height="200"><b>&#9654;</b><span>CAD·스캔 편차</span></a>
<a href="../../articles/assets/poc/poc_crop_phenotyping/01_capsule_calibration.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_crop_phenotyping.jpg" alt="작물 잎 면적" width="200" height="200"><span>작물 잎 면적</span></a>
<a href="../../articles/assets/poc/poc_ct_void_morphology/13_section_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_ct_void_morphology.jpg" alt="접합층 보이드" width="200" height="200"><b>&#9654;</b><span>접합층 보이드</span></a>
<a href="../../articles/assets/poc/poc_dfm_thickness_overhang/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dfm_thickness_overhang.jpg" alt="제조 용이성" width="200" height="200"><span>제조 용이성</span></a>
<a href="../../articles/assets/poc/poc_lidar_terrain_change/12_flight.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_lidar_terrain_change.jpg" alt="경사면 토량" width="200" height="200"><b>&#9654;</b><span>경사면 토량</span></a>
<a href="../../articles/assets/poc/poc_livestock_body_volume/14_hull_orbit.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_livestock_body_volume.jpg" alt="가축 체중" width="200" height="200"><b>&#9654;</b><span>가축 체중</span></a>
<a href="../../articles/assets/poc/poc_mesh_quality_repair/14_decimate_orbit.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_mesh_quality_repair.jpg" alt="메시 복구" width="200" height="200"><b>&#9654;</b><span>메시 복구</span></a>
<a href="../../articles/assets/poc/poc_pallet_load_utilization/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_pallet_load_utilization.jpg" alt="팔레트 적재율" width="200" height="200"><span>팔레트 적재율</span></a>
<a href="../../articles/assets/poc/poc_pipe_wall_loss/01_scene_pipe.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_pipe_wall_loss.jpg" alt="배관 감육" width="200" height="200"><span>배관 감육</span></a>
<a href="../../articles/assets/poc/poc_print_warpage_risk/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_print_warpage_risk.jpg" alt="적층 휨" width="200" height="200"><span>적층 휨</span></a>
<a href="../../articles/assets/poc/poc_safety_clearance/01_conditions.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_safety_clearance.jpg" alt="사람·기계 거리" width="200" height="200"><span>사람·기계 거리</span></a>
<a href="../../articles/assets/poc/poc_scan_to_bim_asbuilt/01_scene_plan_section.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_scan_to_bim_asbuilt.jpg" alt="설계·실물 차이" width="200" height="200"><span>설계·실물 차이</span></a>
<a href="../../articles/assets/poc/poc_structure_4d_deterioration/12_years_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_structure_4d_deterioration.jpg" alt="구조물 경년 측정" width="200" height="200"><b>&#9654;</b><span>구조물 경년 측정</span></a>
<a href="../../articles/assets/poc/poc_symmetry_restoration/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_symmetry_restoration.jpg" alt="대칭으로 보완" width="200" height="200"><span>대칭으로 보완</span></a>
<a href="../../articles/assets/poc/poc_endless_zoom_and_turning_solids/03_zoom_loop.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_endless_zoom_and_turning_solids.jpg" alt="무한 줌" width="200" height="200"><b>&#9654;</b><span>무한 줌</span></a>
<a href="../../articles/assets/poc/poc_four_dimensions_by_three_d_tools/03_hopf_turn.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_four_dimensions_by_three_d_tools.jpg" alt="3-D로 4차원" width="200" height="200"><b>&#9654;</b><span>3-D로 4차원</span></a>
</div>
</details>

<details class="vall"><summary><b>기하·보정</b> (18)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_camera_calibration/05_calibration_convergence.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_camera_calibration.jpg" alt="카메라 보정" width="200" height="200"><b>&#9654;</b><span>카메라 보정</span></a>
<a href="../../articles/assets/poc/poc_panorama_drift/05_chain_drift_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_panorama_drift.jpg" alt="파노라마 드리프트" width="200" height="200"><b>&#9654;</b><span>파노라마 드리프트</span></a>
<a href="../../articles/assets/poc/poc_real_stereo_depth/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_stereo_depth.jpg" alt="실사 스테레오" width="200" height="200"><span>실사 스테레오</span></a>
<a href="../../articles/assets/poc/poc_registration_basin/05_icp_basin_iterations.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_registration_basin.jpg" alt="점군 정합" width="200" height="200"><b>&#9654;</b><span>점군 정합</span></a>
<a href="../../articles/assets/poc/poc_rotation_invariance_audit/02_rotating_coin.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_rotation_invariance_audit.jpg" alt="회전 불변 감사" width="200" height="200"><b>&#9654;</b><span>회전 불변 감사</span></a>
<a href="../../articles/assets/poc/poc_carla_bridge/01_carla_two_worlds.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_carla_bridge.jpg" alt="두 세계 촬영" width="200" height="200"><span>두 세계 촬영</span></a>
<a href="../../articles/assets/poc/poc_driving_town/04_town_drive_through.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_town.jpg" alt="마을 조립" width="200" height="200"><b>&#9654;</b><span>마을 조립</span></a>
<a href="../../articles/assets/poc/poc_driving_japan_town/03_japan_town_drive.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_japan_town.jpg" alt="실제 일본 마을" width="200" height="200"><b>&#9654;</b><span>실제 일본 마을</span></a>
<a href="../../articles/assets/poc/poc_driving_commonroad/01_commonroad_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_commonroad.jpg" alt="CommonRoad 채점" width="200" height="200"><span>CommonRoad 채점</span></a>
<a href="../../articles/assets/poc/poc_pegsim_insertion/04_pegsim_insert_corrected.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_pegsim_insertion.jpg" alt="펙 삽입" width="200" height="200"><b>&#9654;</b><span>펙 삽입</span></a>
<a href="../../articles/assets/poc/poc_air_hockey_intercept/02_airhockey_prediction_cone_narrows.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_air_hockey_intercept.jpg" alt="에어하키" width="200" height="200"><b>&#9654;</b><span>에어하키</span></a>
<a href="../../articles/assets/poc/poc_peg_failure_recovery/05_pegfail_wrist_camera_wedging_detect_recover.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_peg_failure_recovery.jpg" alt="삽입 실패 복구" width="200" height="200"><b>&#9654;</b><span>삽입 실패 복구</span></a>
<a href="../../articles/assets/poc/poc_tacscalib_sphere_lut/02_tacscalib_synthetic_relight.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_tacscalib_sphere_lut.jpg" alt="촉각 센서 보정" width="200" height="200"><b>&#9654;</b><span>촉각 센서 보정</span></a>
<a href="../../articles/assets/poc/poc_peg_insertion_tactile/03_pegtactile_whitney_insertion_through_membranes.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_peg_insertion_tactile.jpg" alt="촉각 펙 삽입" width="200" height="200"><b>&#9654;</b><span>촉각 펙 삽입</span></a>
<a href="../../articles/assets/poc/poc_peg_symmetry_search/01_pegsym_rotating_shapes_read_mod_2pi_over_n.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_peg_symmetry_search.jpg" alt="펙 대칭성" width="200" height="200"><b>&#9654;</b><span>펙 대칭성</span></a>
<a href="../../articles/assets/poc/poc_reproducible_icp/01_error_staircase_ozaki1.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_reproducible_icp.jpg" alt="재현 가능 ICP" width="200" height="200"><span>재현 가능 ICP</span></a>
<a href="../../articles/assets/poc/poc_public_camera_heading/02_yaw_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_public_camera_heading.jpg" alt="공공 카메라 방향" width="200" height="200"><b>&#9654;</b><span>공공 카메라 방향</span></a>
<a href="../../articles/assets/poc/poc_public_camera_heading_real/02_sunset_follow.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_public_camera_heading_real.jpg" alt="카메라 방향(실사)" width="200" height="200"><b>&#9654;</b><span>카메라 방향(실사)</span></a>
</div>
</details>

<details class="vall"><summary><b>촬상 품질·복원</b> (16)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_camera_shake_deblur/05_kernel_angle_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_camera_shake_deblur.jpg" alt="손떨림 복원" width="200" height="200"><b>&#9654;</b><span>손떨림 복원</span></a>
<a href="../../articles/assets/poc/poc_colormap_readability/01_gain_profile.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_colormap_readability.jpg" alt="의사 색상 가독성" width="200" height="200"><span>의사 색상 가독성</span></a>
<a href="../../articles/assets/poc/poc_compound_eye/01_compound_eye_scaling.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_compound_eye.jpg" alt="파리 겹눈" width="200" height="200"><span>파리 겹눈</span></a>
<a href="../../articles/assets/poc/poc_ct_fidelity/01_recon_sweep.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_ct_fidelity.jpg" alt="CT 재구성 한계" width="200" height="200"><span>CT 재구성 한계</span></a>
<a href="../../articles/assets/poc/poc_dehazing/05_haze_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dehazing.jpg" alt="안개 제거" width="200" height="200"><b>&#9654;</b><span>안개 제거</span></a>
<a href="../../articles/assets/poc/poc_dtof_ranging/01_histograms.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dtof_ranging.jpg" alt="광자 거리 측정" width="200" height="200"><span>광자 거리 측정</span></a>
<a href="../../articles/assets/poc/poc_focus_stacking/05_focus_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_focus_stacking.jpg" alt="초점 합성" width="200" height="200"><b>&#9654;</b><span>초점 합성</span></a>
<a href="../../articles/assets/poc/poc_lightfield_depth/01_scene_and_depth.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_lightfield_depth.jpg" alt="라이트 필드 깊이" width="200" height="200"><span>라이트 필드 깊이</span></a>
<a href="../../articles/assets/poc/poc_real_deblur_honesty/01_restore.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_deblur_honesty.jpg" alt="실사 블러 복원" width="200" height="200"><span>실사 블러 복원</span></a>
<a href="../../articles/assets/poc/poc_superresolution_limits/05_growth.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_superresolution_limits.jpg" alt="초해상 한계" width="200" height="200"><b>&#9654;</b><span>초해상 한계</span></a>
<a href="../../articles/assets/poc/poc_iqa_tid2013/01_tid2013_mos_vs_psnr.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_iqa_tid2013.jpg" alt="화질 지표·TID2013" width="200" height="200"><span>화질 지표·TID2013</span></a>
<a href="../../articles/assets/poc/poc_iqa_fsim_gmsd_vif/01_iqa_tid2013_mos_vs_fsim.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_iqa_fsim_gmsd_vif.jpg" alt="지각 지표 일치" width="200" height="200"><span>지각 지표 일치</span></a>
<a href="../../articles/assets/poc/poc_vanishing_detail_and_morphing_area/06_morph_loop.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_vanishing_detail_and_morphing_area.jpg" alt="사라지는 디테일" width="200" height="200"><b>&#9654;</b><span>사라지는 디테일</span></a>
<a href="../../articles/assets/poc/poc_segmentation_gauntlet/08_gauntlet_blobs.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_segmentation_gauntlet.jpg" alt="분할의 관문" width="200" height="200"><b>&#9654;</b><span>분할의 관문</span></a>
<a href="../../articles/assets/poc/poc_active_contours/06_u_shape_snakes.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_active_contours.jpg" alt="능동 윤곽" width="200" height="200"><b>&#9654;</b><span>능동 윤곽</span></a>
<a href="../../articles/assets/poc/poc_graph_hierarchy_segmentation/08_watershed_theta_sweep.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_graph_hierarchy_segmentation.jpg" alt="그래프 분할" width="200" height="200"><b>&#9654;</b><span>그래프 분할</span></a>
</div>
</details>

<details class="vall"><summary><b>색·분리</b> (4)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_pigment_unmixing/01_per_field_auc.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_pigment_unmixing.jpg" alt="안료 층 분리" width="200" height="200"><span>안료 층 분리</span></a>
<a href="../../articles/assets/poc/poc_polarization_specular/01_fresnel.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_polarization_specular.jpg" alt="편광 정반사 제거" width="200" height="200"><span>편광 정반사 제거</span></a>
<a href="../../articles/assets/poc/poc_real_stain_unmix/01_separation.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_stain_unmix.jpg" alt="실사 염색 분리" width="200" height="200"><span>실사 염색 분리</span></a>
<a href="../../articles/assets/poc/poc_white_balance/01_casts.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_white_balance.jpg" alt="화이트 밸런스" width="200" height="200"><span>화이트 밸런스</span></a>
</div>
</details>

<details class="vall"><summary><b>시계열을 3-D로 측정</b> (21)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_beam_modal_video/14_beam_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_beam_modal_video.jpg" alt="영상 모드 식별" width="200" height="200"><b>&#9654;</b><span>영상 모드 식별</span></a>
<a href="../../articles/assets/poc/poc_cold_chain_excursion/01_scene_slices.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_cold_chain_excursion.jpg" alt="콜드체인 온도" width="200" height="200"><span>콜드체인 온도</span></a>
<a href="../../articles/assets/poc/poc_crack_width_timeseries/11_series_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_crack_width_timeseries.jpg" alt="균열 성장" width="200" height="200"><b>&#9654;</b><span>균열 성장</span></a>
<a href="../../articles/assets/poc/poc_motion_magnification/05_magnify_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_motion_magnification.jpg" alt="미세 진동 확대" width="200" height="200"><b>&#9654;</b><span>미세 진동 확대</span></a>
<a href="../../articles/assets/poc/poc_particle_tracking/05_tracking_links.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_particle_tracking.jpg" alt="입자 추적" width="200" height="200"><b>&#9654;</b><span>입자 추적</span></a>
<a href="../../articles/assets/poc/poc_settlement_significance/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_settlement_significance.jpg" alt="침하 판정" width="200" height="200"><span>침하 판정</span></a>
<a href="../../articles/assets/poc/poc_template_tracking/05_twin_vs_flat_occluder.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_template_tracking.jpg" alt="템플릿 추적" width="200" height="200"><b>&#9654;</b><span>템플릿 추적</span></a>
<a href="../../articles/assets/poc/poc_timelapse_growth/05_growth_merge.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_timelapse_growth.jpg" alt="성장 타임랩스" width="200" height="200"><b>&#9654;</b><span>성장 타임랩스</span></a>
<a href="../../articles/assets/poc/poc_traffic_counting/05_counting_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_traffic_counting.jpg" alt="교통량 계수" width="200" height="200"><b>&#9654;</b><span>교통량 계수</span></a>
<a href="../../articles/assets/poc/poc_warehouse_flow/01_heat_ambiguity.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_warehouse_flow.jpg" alt="창고 체류" width="200" height="200"><span>창고 체류</span></a>
<a href="../../articles/assets/poc/poc_xyt_event_surface/05_arrival_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_xyt_event_surface.jpg" alt="도달 시각면" width="200" height="200"><b>&#9654;</b><span>도달 시각면</span></a>
<a href="../../articles/assets/poc/poc_video_cube/02_cube_orbit.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_video_cube.jpg" alt="영상 시공간 큐브" width="200" height="200"><b>&#9654;</b><span>영상 시공간 큐브</span></a>
<a href="../../articles/assets/poc/poc_live4d/01_beating_orbit.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_live4d.jpg" alt="생체 3D+t" width="200" height="200"><b>&#9654;</b><span>생체 3D+t</span></a>
<a href="../../articles/assets/poc/poc_diabolo_model_and_vision/01_diabolo_throw_axis_from_image.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_diabolo_model_and_vision.jpg" alt="디아볼로" width="200" height="200"><b>&#9654;</b><span>디아볼로</span></a>
<a href="../../articles/assets/poc/poc_swarm_obstacle_from_flow/01_swarmflow_hidden_obstacle_emerges.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_swarm_obstacle_from_flow.jpg" alt="군집 장애물 감지" width="200" height="200"><b>&#9654;</b><span>군집 장애물 감지</span></a>
<a href="../../articles/assets/poc/poc_ball_bounce/06_rally_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_ball_bounce.jpg" alt="탁구공 추적" width="200" height="200"><b>&#9654;</b><span>탁구공 추적</span></a>
<a href="../../articles/assets/poc/poc_kendama/05_catch_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_kendama.jpg" alt="켄다마" width="200" height="200"><b>&#9654;</b><span>켄다마</span></a>
<a href="../../articles/assets/poc/poc_table_tennis_spin/01_side_three_serves.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_table_tennis_spin.jpg" alt="탁구공 회전" width="200" height="200"><b>&#9654;</b><span>탁구공 회전</span></a>
<a href="../../articles/assets/poc/poc_table_tennis_bounce/01_drop_test.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_table_tennis_bounce.jpg" alt="탁구공 바운드" width="200" height="200"><b>&#9654;</b><span>탁구공 바운드</span></a>
<a href="../../articles/assets/poc/poc_table_tennis_rally_loop/01_landing_cloud.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_table_tennis_rally_loop.jpg" alt="랠리와 판독 오차" width="200" height="200"><b>&#9654;</b><span>랠리와 판독 오차</span></a>
<a href="../../articles/assets/poc/poc_periodic_video_boundary/02_loop.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_periodic_video_boundary.jpg" alt="주기 동영상" width="200" height="200"><b>&#9654;</b><span>주기 동영상</span></a>
</div>
</details>

<details class="vall"><summary><b>커넥톰·신경</b> (19)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_fly_vision/01_fly_vision_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_fly_vision.jpg" alt="파리 시각 전단" width="200" height="200"><span>파리 시각 전단</span></a>
<a href="../../articles/assets/poc/poc_larval_connectome_reservoir/01_adjacency_binned_connectome_vs_shuffle.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_larval_connectome_reservoir.jpg" alt="유충 커넥톰" width="200" height="200"><span>유충 커넥톰</span></a>
<a href="../../articles/assets/poc/poc_malecns_activity_wave/01_activity_wave_connectome_vs_shuffle.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_malecns_activity_wave.jpg" alt="파리 뇌의 파동" width="200" height="200"><b>&#9654;</b><span>파리 뇌의 파동</span></a>
<a href="../../articles/assets/poc/poc_eye_to_brain/01_eye_sweep.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_eye_to_brain.jpg" alt="겹눈에서 뇌로" width="200" height="200"><b>&#9654;</b><span>겹눈에서 뇌로</span></a>
<a href="../../articles/assets/poc/poc_em_second_opinion/02_suspects_on_the_cube.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_em_second_opinion.jpg" alt="EM 교정 재검" width="200" height="200"><b>&#9654;</b><span>EM 교정 재검</span></a>
<a href="../../articles/assets/poc/poc_connectome_motor_bottleneck/03_activity_flow.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_connectome_motor_bottleneck.jpg" alt="움직임 양자화" width="200" height="200"><b>&#9654;</b><span>움직임 양자화</span></a>
<a href="../../articles/assets/poc/poc_microns_brain_wave/01_brain_wave.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_microns_brain_wave.jpg" alt="MICrONS 파동" width="200" height="200"><b>&#9654;</b><span>MICrONS 파동</span></a>
<a href="../../articles/assets/poc/poc_em_branch_territory/02_territory_turning.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_em_branch_territory.jpg" alt="가지 영역" width="200" height="200"><b>&#9654;</b><span>가지 영역</span></a>
<a href="../../articles/assets/poc/poc_connectome_lr_symmetry/01_lr_jaccard_closed_form.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_connectome_lr_symmetry.jpg" alt="선충 좌우 대칭" width="200" height="200"><span>선충 좌우 대칭</span></a>
<a href="../../articles/assets/poc/poc_connectome_across_worms/02_wiring_across_development.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_connectome_across_worms.jpg" alt="선충 개체 차" width="200" height="200"><b>&#9654;</b><span>선충 개체 차</span></a>
<a href="../../articles/assets/poc/poc_connectome_across_decades/01_jaccard_across_decades.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_connectome_across_decades.jpg" alt="40년 전 배선도" width="200" height="200"><span>40년 전 배선도</span></a>
<a href="../../articles/assets/poc/poc_worm_neurites_grow/01_neurite_length_growth.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_worm_neurites_grow.jpg" alt="신경 돌기 성장" width="200" height="200"><span>신경 돌기 성장</span></a>
<a href="../../articles/assets/poc/poc_em_split_merge_score/01_split_vs_merge_by_threshold.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_em_split_merge_score.jpg" alt="EM 분할 채점" width="200" height="200"><span>EM 분할 채점</span></a>
<a href="../../articles/assets/poc/poc_em_wiring_errors/01_proofreading_order.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_em_wiring_errors.jpg" alt="분할 오류와 배선" width="200" height="200"><span>분할 오류와 배선</span></a>
<a href="../../articles/assets/poc/poc_worm_synapses_vs_neurites/01_density_by_stage.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_worm_synapses_vs_neurites.jpg" alt="시냅스와 돌기" width="200" height="200"><span>시냅스와 돌기</span></a>
<a href="../../articles/assets/poc/poc_skeleton_run_length_vs_voi/01_merge_size_erl_vs_voi.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_skeleton_run_length_vs_voi.jpg" alt="주행 길이와 VOI" width="200" height="200"><span>주행 길이와 VOI</span></a>
<a href="../../articles/assets/poc/poc_swc_tree_truth/01_swc_projection.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_swc_tree_truth.jpg" alt="실제 나무 골격" width="200" height="200"><span>실제 나무 골격</span></a>
<a href="../../articles/assets/poc/poc_fly_optomotor_steering/06_follow.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_fly_optomotor_steering.jpg" alt="파리 진로 제어" width="200" height="200"><b>&#9654;</b><span>파리 진로 제어</span></a>
<a href="../../articles/assets/poc/poc_worm_core_persists/04_core_map_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_worm_core_persists.jpg" alt="선충 뇌의 핵" width="200" height="200"><b>&#9654;</b><span>선충 뇌의 핵</span></a>
</div>
</details>

<details class="vall"><summary><b>의료·생물</b> (9)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_bone_trabecular_thickness/01_scene_truth.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_bone_trabecular_thickness.jpg" alt="골소주 두께" width="200" height="200"><span>골소주 두께</span></a>
<a href="../../articles/assets/poc/poc_cell_counting/01_scene_dense.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_cell_counting.jpg" alt="겹친 세포 계수" width="200" height="200"><span>겹친 세포 계수</span></a>
<a href="../../articles/assets/poc/poc_colocalization_crosstalk/01_scene_channels.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_colocalization_crosstalk.jpg" alt="형광 공국재" width="200" height="200"><span>형광 공국재</span></a>
<a href="../../articles/assets/poc/poc_mri_bias_field/01_controls.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_mri_bias_field.jpg" alt="MRI 바이어스장" width="200" height="200"><span>MRI 바이어스장</span></a>
<a href="../../articles/assets/poc/poc_nuclei_ploidy/01_histograms.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_nuclei_ploidy.jpg" alt="핵 배수성" width="200" height="200"><span>핵 배수성</span></a>
<a href="../../articles/assets/poc/poc_vessel_network/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_vessel_network.jpg" alt="혈관망 분기" width="200" height="200"><span>혈관망 분기</span></a>
<a href="../../articles/assets/poc/poc_wound_area_tracking/06_healing_video.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_wound_area_tracking.jpg" alt="창상 면적" width="200" height="200"><b>&#9654;</b><span>창상 면적</span></a>
<a href="../../articles/assets/poc/poc_physarum_maze/02_maze_tubes_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_physarum_maze.jpg" alt="점균 미로" width="200" height="200"><b>&#9654;</b><span>점균 미로</span></a>
<a href="../../articles/assets/poc/poc_physarum_transport/01_transport_tubes_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_physarum_transport.jpg" alt="점균 최적 수송" width="200" height="200"><b>&#9654;</b><span>점균 최적 수송</span></a>
</div>
</details>

<details class="vall"><summary><b>천문·환경</b> (21)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_allsky_cloud_cover/01_jacobian.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_allsky_cloud_cover.jpg" alt="전천 카메라 운량" width="200" height="200"><span>전천 카메라 운량</span></a>
<a href="../../articles/assets/poc/poc_astro_photometry/01_stack_scaling.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_astro_photometry.jpg" alt="별 측광 정밀도" width="200" height="200"><span>별 측광 정밀도</span></a>
<a href="../../articles/assets/poc/poc_change_detection_misreg/01_plot_fp_vs_shift.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_change_detection_misreg.jpg" alt="변화 검출" width="200" height="200"><span>변화 검출</span></a>
<a href="../../articles/assets/poc/poc_datacenter_thermal_field/01_scene_truth.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_datacenter_thermal_field.jpg" alt="3-D 열장 복원" width="200" height="200"><span>3-D 열장 복원</span></a>
<a href="../../articles/assets/poc/poc_dem_terrain/05_terrain_flight.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_dem_terrain.jpg" alt="지형 측정" width="200" height="200"><b>&#9654;</b><span>지형 측정</span></a>
<a href="../../articles/assets/poc/poc_exoplanet_transit/01_scene_starfield.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_exoplanet_transit.jpg" alt="외계행성 통과" width="200" height="200"><span>외계행성 통과</span></a>
<a href="../../articles/assets/poc/poc_geodetic_height_frames/01_geoid_frames.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_geodetic_height_frames.jpg" alt="좌표 높이 함정" width="200" height="200"><span>좌표 높이 함정</span></a>
<a href="../../articles/assets/poc/poc_leaf_disease_area/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_leaf_disease_area.jpg" alt="잎 병반" width="200" height="200"><span>잎 병반</span></a>
<a href="../../articles/assets/poc/poc_pv_thermal_survey/01_norm_table.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_pv_thermal_survey.jpg" alt="태양광 열화상" width="200" height="200"><span>태양광 열화상</span></a>
<a href="../../articles/assets/poc/poc_real_sky_photometry/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_real_sky_photometry.jpg" alt="실사 심우주" width="200" height="200"><span>실사 심우주</span></a>
<a href="../../articles/assets/poc/poc_river_surface_velocity/13_accumulate_pairs.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_river_surface_velocity.jpg" alt="하천 표면 유속" width="200" height="200"><b>&#9654;</b><span>하천 표면 유속</span></a>
<a href="../../articles/assets/poc/poc_sea_ice_concentration/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_sea_ice_concentration.jpg" alt="해빙 밀접도" width="200" height="200"><span>해빙 밀접도</span></a>
<a href="../../articles/assets/poc/poc_search_sweep_width/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_search_sweep_width.jpg" alt="수색 탐지 폭" width="200" height="200"><span>수색 탐지 폭</span></a>
<a href="../../articles/assets/poc/poc_solar_limb_darkening/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_solar_limb_darkening.jpg" alt="주연 감광" width="200" height="200"><span>주연 감광</span></a>
<a href="../../articles/assets/poc/poc_star_astrometry/01_snr_sweep.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_star_astrometry.jpg" alt="별 위치 정밀도" width="200" height="200"><span>별 위치 정밀도</span></a>
<a href="../../articles/assets/poc/poc_tree_ring_dendro/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_tree_ring_dendro.jpg" alt="나이테 폭" width="200" height="200"><span>나이테 폭</span></a>
<a href="../../articles/assets/poc/poc_vegetation_cover/01_mixed_pixel_response.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_vegetation_cover.jpg" alt="식생 피복률" width="200" height="200"><span>식생 피복률</span></a>
<a href="../../articles/assets/poc/poc_water_level/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_water_level.jpg" alt="하천 수위" width="200" height="200"><span>하천 수위</span></a>
<a href="../../articles/assets/poc/poc_rover_slip_risk_path/03_rover_slip_update.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_rover_slip_risk_path.jpg" alt="화성 바퀴 미끄럼" width="200" height="200"><b>&#9654;</b><span>화성 바퀴 미끄럼</span></a>
<a href="../../articles/assets/poc/poc_geodetic_benchmarks_real/01_residual_sorted.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_geodetic_benchmarks_real.jpg" alt="두 높이(실데이터)" width="200" height="200"><span>두 높이(실데이터)</span></a>
<a href="../../articles/assets/poc/poc_gravitational_lens_invariants/10_source_crossing.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_gravitational_lens_invariants.jpg" alt="중력 렌즈" width="200" height="200"><b>&#9654;</b><span>중력 렌즈</span></a>
</div>
</details>

<details class="vall"><summary><b>법과학·문서</b> (4)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_document_scan/01_rectify_zero_points.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_document_scan.jpg" alt="문서 바로잡기" width="200" height="200"><span>문서 바로잡기</span></a>
<a href="../../articles/assets/poc/poc_forensics_roc/01_score_maps.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_forensics_roc.jpg" alt="위변조 검출 ROC" width="200" height="200"><span>위변조 검출 ROC</span></a>
<a href="../../articles/assets/poc/poc_fresco_craquelure/01_ridge_ops.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_fresco_craquelure.jpg" alt="그림 균열망" width="200" height="200"><span>그림 균열망</span></a>
<a href="../../articles/assets/poc/poc_prnu_camera_fingerprint/01_scene.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_prnu_camera_fingerprint.jpg" alt="카메라 지문" width="200" height="200"><span>카메라 지문</span></a>
</div>
</details>

<details class="vall"><summary><b>자율주행</b> (13)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_car_parking/04_parking_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_car_parking.jpg" alt="최단 회전 주차" width="200" height="200"><b>&#9654;</b><span>최단 회전 주차</span></a>
<a href="../../articles/assets/poc/poc_driving_school/05_drive_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_school.jpg" alt="운전 학원" width="200" height="200"><b>&#9654;</b><span>운전 학원</span></a>
<a href="../../articles/assets/poc/poc_ttc_rss/06_approach_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_ttc_rss.jpg" alt="충돌 시간과 RSS" width="200" height="200"><b>&#9654;</b><span>충돌 시간과 RSS</span></a>
<a href="../../articles/assets/poc/poc_world_terrain/06_drive_gif.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_world_terrain.jpg" alt="세계 넓히기" width="200" height="200"><b>&#9654;</b><span>세계 넓히기</span></a>
<a href="../../articles/assets/poc/poc_driving_longitudinal/01_drive_with_time.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_longitudinal.jpg" alt="관성과 경사" width="200" height="200"><b>&#9654;</b><span>관성과 경사</span></a>
<a href="../../articles/assets/poc/poc_driving_weather/01_sun_day.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_weather.jpg" alt="태양과 날씨" width="200" height="200"><b>&#9654;</b><span>태양과 날씨</span></a>
<a href="../../articles/assets/poc/poc_driving_endless_map/01_minimap_stream.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_endless_map.jpg" alt="끝없는 지도" width="200" height="200"><b>&#9654;</b><span>끝없는 지도</span></a>
<a href="../../articles/assets/poc/poc_driving_traffic/01_dashcam_occlusion.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_traffic.jpg" alt="교통과 사각" width="200" height="200"><b>&#9654;</b><span>교통과 사각</span></a>
<a href="../../articles/assets/poc/poc_driving_decisions/01_decisions_mirrors_ambulance.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_decisions.jpg" alt="판단 장면" width="200" height="200"><b>&#9654;</b><span>판단 장면</span></a>
<a href="../../articles/assets/poc/poc_driving_lateral/01_lateral_dashcam.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_lateral.jpg" alt="횡방향 운동" width="200" height="200"><b>&#9654;</b><span>횡방향 운동</span></a>
<a href="../../articles/assets/poc/poc_driving_humanoids/03_humanoids_crossing.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_humanoids.jpg" alt="횡단보도 휴머노이드" width="200" height="200"><b>&#9654;</b><span>횡단보도 휴머노이드</span></a>
<a href="../../articles/assets/poc/poc_driving_crossing/01_crossing_dashcam.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_crossing.jpg" alt="건널목과 교차로" width="200" height="200"><b>&#9654;</b><span>건널목과 교차로</span></a>
<a href="../../articles/assets/poc/poc_driving_pass/01_overtake_dashcam.mp4"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_driving_pass.jpg" alt="추월과 사각" width="200" height="200"><b>&#9654;</b><span>추월과 사각</span></a>
</div>
</details>

<details class="vall"><summary><b>수학 그림</b> (7)</summary>
<div class="vg vs">
<a href="../../articles/assets/poc/poc_one_stroke_epicycles/07_epicycles.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_one_stroke_epicycles.jpg" alt="한붓그리기 주전원" width="200" height="200"><b>&#9654;</b><span>한붓그리기 주전원</span></a>
<a href="../../articles/assets/poc/poc_complex_plane_fields/01_rational.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_complex_plane_fields.jpg" alt="복소평면" width="200" height="200"><span>복소평면</span></a>
<a href="../../articles/assets/poc/poc_theorems_as_pictures/01_apollonian.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_theorems_as_pictures.jpg" alt="정리가 관문인 그림" width="200" height="200"><span>정리가 관문인 그림</span></a>
<a href="../../articles/assets/poc/poc_beats_fringes_and_screens/01_membrane.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_beats_fringes_and_screens.jpg" alt="맥놀이는 하나" width="200" height="200"><span>맥놀이는 하나</span></a>
<a href="../../articles/assets/poc/poc_what_a_picture_cannot_check/01_rk4.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_what_a_picture_cannot_check.jpg" alt="그림으로 못 하는 것" width="200" height="200"><span>그림으로 못 하는 것</span></a>
<a href="../../articles/assets/poc/poc_illusions_and_perpetual_drawing/14_loop.gif"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_illusions_and_perpetual_drawing.jpg" alt="끝없는 그림" width="200" height="200"><b>&#9654;</b><span>끝없는 그림</span></a>
<a href="../../articles/assets/poc/poc_calipers_under_illusion/01_caliper_on_cafe_wall.png"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-src="../thumbs/all/poc_calipers_under_illusion.jpg" alt="착시로 측정기 진단" width="200" height="200"><span>착시로 측정기 진단</span></a>
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

## 무엇이 보이나·측정한 숫자

모든 숫자는 각 PoC가 직접 심은 참값(닫힌 식·해석해·공표값)에 대한 실측이며, PoC를 실행하면 같은 값이 출력됩니다.

<div class="vl" markdown="1">

**영상 검사·외관 계측**

- [얇은 결함 검출 한계](../../articles/assets/poc/poc_real_defect_floor/02_defect_floor_sweep.gif) (GIF): 실사 배경(벽돌)과 잡음량을 맞춘 합성 배경에 같은 결함을 점점 진하게 심는다. **잡음량을 맞춰도 실사 배경의 검출 한계는 합성의 2.03〜3.47배(위치·진폭이 알려진 결함 기준).** [소스](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_defect_floor.py)
- [능동 윤곽](../../articles/assets/poc/poc_active_contours/06_u_shape_snakes.mp4) (동영상): 고전 snake(빨강)는 U자 오목부에 들어가지 못하고, GVF(파랑)는 바닥까지 들어간다. 초록이 참 경계. **외력만 GVF로 바꾸면 Dice 0.993(참 경계 기준).** [소스](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_active_contours.py)
- [DIC 변형률](../../articles/assets/poc/poc_dic_strain/05_tensile_ramp.mp4) (동영상): 인장 시험 하중을 올리며 스페클 영상에서 변형률 지도를 읽는다(시험기는 동시에 2도 회전). **참 변형률 3000 µε. 미소 변형률은 회전 때문에 2341 µε로 과소, Green-Lagrange는 2961 µε(이론 3005 µε).** [소스](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dic_strain.py)

**3차원 계측·기하 처리**

- [초점 합성](../../articles/assets/poc/poc_focus_stacking/05_focus_sweep.mp4) (동영상): 초점을 17장 스윕하면서 전초점 영상과 깊이 지도가 만들어진다. **전초점 PSNR 33.69 dB(중앙 1장 28.52 dB), 깊이 오차 0.467 mm(텍스처 있는 영역).** [소스](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_focus_stacking.py)
- [점군 정합](../../articles/assets/poc/poc_registration_basin/05_icp_basin_iterations.mp4) (동영상): 초기 회전 오차 30 / 90 / 150도에서 ICP를 1회씩 반복한다. **60회 반복 후 회전 오차: 30도·90도는 0.6도(성공), 150도는 179.5도(실패).** [소스](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_registration_basin.py)
- [적치물 부피](../../articles/assets/poc/poc_stockpile_volume/07_scan_orbit.mp4) (동영상): 더미 주위를 돌며 3-D 스캔 위치를 1곳에서 3곳으로 늘린다. 색은 보간면과 참 표면의 차이. **재고량 오차 +17.20 % → +0.05 %(참 바닥면 기준, 부피 참값은 닫힌 식 3572.6089 m³).** [소스](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_stockpile_volume.py)

**X선 CT·볼륨 처리**

- [CT 재구성](../../articles/assets/poc/poc_ct_fidelity/01_recon_sweep.png) (그림): Shepp-Logan 팬텀을 투영 180개 → 12개로 다시 찍어 재구성한다. **12개 투영의 FBP(RMSE 0.2576)는 빈 영상(0.2420)에도 진다. 질량 검산으로 -3.34 % 손실을 찾아 -0.0099 %로 고쳤다.** [소스](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_fidelity.py)
- [CT 보이드](../../articles/assets/poc/poc_ct_void_morphology/13_section_sweep.mp4) (동영상): 보이드율이 거의 같은 2가지 접합층을 단면을 스윕하며 3-D로 회전한다(동영상 4.3 MB). **보이드율은 2.46 % 대 2.63 %인데, 계면까지 거리의 중앙값은 60.0 µm 대 10.0 µm.** [소스](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_void_morphology.py)

**광학·간섭·편광**

- [백색광 간섭 단차](../../articles/assets/poc/poc_interferometry_step/05_step_sweep.mp4) (동영상): 심은 단차를 0 → 0.90 µm로 늘리며 포락선법과 위상 이동법으로 잰다. **잡음 1 %에서 편향 2.4 nm 이내(단차 50〜500 nm). 위상 이동법은 0.153 µm에서 λ/2 튄다.** [소스](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_interferometry_step.py)
- [편광 정반사 제거](../../articles/assets/poc/poc_polarization_specular/03_separation.png) (그림): 편광으로 정반사를 걷어낸 결과와 남은 오차의 모양. **확산 성분의 오차는 닫힌 식 R_p·E와 일치하고 브루스터 각 56.31도에서 0.** [소스](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_polarization_specular.py)
- [광탄성 응력](../../articles/assets/poc/poc_photoelasticity/03_load_and_isoclinics.mp4) (동영상): 원판에 하중을 가하면 줄무늬가 솟아나고, 편광자를 돌리면 등경선이 움직인다. **중심 줄무늬 차수 2.38(닫힌 식대로). op의 편광계는 교과서 식과 최대 차 2.2e-16.** [소스](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_photoelasticity.py)

**열·음향·시계열**

- [열화상 결함 깊이](../../articles/assets/poc/poc_thermography_ndt/02_depth_map.png) (그림): 플래시 가열 후 표면 온도로 16개 박리의 깊이를 읽은 지도. **깊이 0.5 mm·지름 2 mm 결함은 피팅 시간창 25초에서 +612 %, 4초로 줄이면 -9 %.** [소스](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_thermography_ndt.py)
- [미세 진동 확대](../../articles/assets/poc/poc_motion_magnification/05_magnify_video.mp4) (동영상): 0.1 px로 흔들리는 표면. 왼쪽이 원본 영상, 오른쪽이 10배 확대 영상. **참 진폭 0.1000 px에 대해 원본에서 0.10012, 확대 후 0.10013 px. 확대는 보여 주는 도구이고 측정은 좋아지지 않는다.** [소스](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_motion_magnification.py)

**로봇·공간 지각**

- [겹눈 라이트 필드](../../articles/assets/poc/poc_compound_eye/02_compound_eye_superposition.png) (그림): 낱눈 배열을 라이트 필드 센서로 합성하고 같은 점을 N개 낱눈으로 겹친다. 이 라이트 필드를 파리의 배선도(커넥톰)로 처리하는 것이 다음 과제 —— 아래 커넥톰 전시로 이어진다. **SNR 이득은 N=5에서 2.25(√5 = 2.24), N=49에서 5.33(√49 = 7.00).** [소스](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_compound_eye.py)
- [펙 삽입](../../articles/assets/poc/poc_pegsim_insertion/04_pegsim_insert_corrected.gif) (GIF): 손목 카메라로 구멍 위치를 재서 다가가고, 유연한 손목으로 펙을 넣는다(MuJoCo). **서보 7회로 참 오차 2.24 → 0.03 mm. 보정한 삽입은 12 / 12 성공.** [소스](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pegsim_insertion.py)
- [에어하키](../../articles/assets/poc/poc_air_hockey_intercept/02_airhockey_prediction_cone_narrows.gif) (GIF): 거친 카메라로 퍽을 추적해 수비선과의 교점을 예측한다. 프레임이 늘수록 예측 띠가 좁아진다. **교점의 95 % 띠는 N = 3 프레임에서 145 mm → N = 16 프레임에서 7 mm.** [소스](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_air_hockey_intercept.py)
- [시각 촉각 센서](../../articles/assets/poc/poc_tacsim_elastic_membrane/03_tacsim_force_sweep.gif) (GIF): 구로 탄성막을 누르는 하중을 올리며 막 영상에서 접촉 반경을 읽는다. **Hertz 닫힌 식 대비 접촉 반경 오차 0.05〜0.26 %, 하중 오차 0.14〜0.79 %(0.02〜0.12 N).** [소스](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_tacsim_elastic_membrane.py)

**탁구·운동 계측**

- [탁구공 바운드](../../articles/assets/poc/poc_table_tennis_bounce/01_drop_test.mp4) (동영상): ITTF 탁구대 시험: 30 cm에서 공을 떨어뜨려 튀어 오른 높이를 영상에서 읽는다. **영상에서 읽은 바운드 높이 23.0 cm(참값 23.0 cm).** [소스](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_table_tennis_bounce.py)
- [탁구공 회전](../../articles/assets/poc/poc_table_tennis_spin/01_side_three_serves.mp4) (동영상): 같은 속도·방향으로 친 3개: 톱스핀은 가라앉고 백스핀은 뜬다. **착지점 x = 0.49 / 0.75 / 1.12 m. 휘는 모양에서 읽은 회전으로 예측한 착지점은 4개 모두 참값과 2 cm 이내.** [소스](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_table_tennis_spin.py)
- [랠리와 판독 오차](../../articles/assets/poc/poc_table_tennis_rally_loop/02_height_misread.mp4) (동영상): 공 높이를 5 cm 높게 읽으면 조준 계산이 낮은 궤도를 골라 공이 짧게 떨어진다. **목표보다 10.2 cm 짧게 떨어진다. 치기 전 일차 예측 2.06 × 5 cm = 10.3 cm.** [소스](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_table_tennis_rally_loop.py)

**자율주행**

- [교통과 사각](../../articles/assets/poc/poc_driving_traffic/01_dashcam_occlusion.mp4) (동영상): 노상 주차 차량 뒤에서 아이가 뛰어나온다. 배경과의 차이(학습 없음)로 검지해 멈춘다. **t = 7.30 s에 검지(참값 대비 지연 0.133 s), 아이의 선 7.09 m 앞에서 정지.** [소스](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_driving_traffic.py)
- [건널목과 교차로](../../articles/assets/poc/poc_driving_crossing/01_crossing_dashcam.mp4) (동영상): 건널목 앞에서 멈추고, 경보 중에는 기다리고, 좌우를 보고 건넌다(운전자 시점). **규칙대로인 240명은 위반 0, 열차 도착 시 선로 위 0명. 경보 중 진입 버전은 157명 위반, 그중 23명이 선로 위.** [소스](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_driving_crossing.py)
- [커브 미러](../../articles/assets/poc/poc_driving_pass/03_mirror_tjunction.mp4) (동영상): 시야가 나쁜 T자 교차로에서 볼록 커브 미러에 비친 차를 광선 추적으로 그려 거리를 읽는다. **거울에서 29 m인 차가 상의 크기로 읽으면 139 m 앞으로 보인다(닫힌 식 세로 읽기 140 m).** [소스](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_driving_pass.py)
- [충돌 시간과 RSS](../../articles/assets/poc/poc_ttc_rss/06_approach_gif.gif) (GIF): 대향차의 광학 흐름으로 충돌까지의 시간 τ를 구하고, 정차 차량에는 RSS 안전거리로 멈춘다. **RSS가 '위험'을 낸 t = 6.0 s에 제동해 10.25 m 앞에서 정지.** [소스](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ttc_rss.py)

**커넥톰·신경**

- [겹눈에서 뇌로](../../articles/assets/poc/poc_eye_to_brain/01_eye_sweep.gif) (GIF): 파리 오른쪽 눈의 낱눈 1개 자극을 눈의 한 줄을 따라 움직여 뇌의 배선도(커넥톰)에 넣는다(GIF 4.4 MB). **자극한 기둥 위치와 응답 중심의 상관: 커넥톰 -0.92, 차수 보존 셔플 +0.01.** [소스](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_eye_to_brain.py)
- [파리 뇌의 파동](../../articles/assets/poc/poc_malecns_activity_wave/01_activity_wave_connectome_vs_shuffle.gif) (GIF): 오른쪽 시엽에 준 자극이 실제 배선(왼쪽)과 차수를 보존해 다시 연결한 배선(오른쪽)을 타고 퍼진다. **실제 배선에서는 활동의 평균 거리가 17스텝에 걸쳐 88 → 230 µm로 늘어난다. 재연결은 3스텝 만에 300 µm로 흩어진다.** [소스](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_malecns_activity_wave.py)
- [마우스 시각피질 파동](../../articles/assets/poc/poc_microns_brain_wave/04_wave_on_wiring.gif) (GIF): 교정된 축삭 148개의 실측 응답을 마우스 시각피질 1 mm³의 실제 배선에 흘린다(MICrONS). **실측과의 상관: 실제 배선 0.085, 차수 보존 셔플 0.048.** [소스](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_microns_brain_wave.py)

**로봇의 눈(Fullseye가 지각 담당)**

- [휴머노이드 두 눈](../../articles/assets/media/evis_stereo_fullseye.mp4) (동영상): 근골격 휴머노이드가 젓가락으로 콩을 치는 장면을 자기 두 눈(동공 간 거리 64 mm)으로 찍고, Fullseye가 매 프레임 스테레오 시차 → 깊이를 계산한다. **콩까지 거리 오차: 중앙값 0.66 %, 최대 1.91 %(판독 가능 229 / 241 프레임).** [소스](https://github.com/furuse-kazufumi/fullseye/blob/master/tools/gen_evis_media.py)
- [젓가락 끝 카메라 추적](../../articles/assets/media/evis_bean_track_fullseye.mp4) (동영상): 같은 장면의 젓가락 끝 카메라 영상에서 Fullseye가 콩을 검출해 추적한다. **보이는 163 프레임 모두 검출(163 / 163), 중심 오차는 참값 대비 중앙값 0.10 px.** [소스](https://github.com/furuse-kazufumi/fullseye/blob/master/tools/gen_evis_media.py)

</div>

## Fullseye란

광학 설계·3차원 계측 등 센싱을 포함한 물리 시뮬레이션과 고전 영상 처리를 MCP와 RAG로 AI에 넘겨, 과제마다 조합을 생각하게 하고, 타입 정합성과 참값 평가로 확인하면서 대화형으로 과제를 푸는 기반입니다. 오픈 소스(Apache-2.0).

<details markdown="1">
<summary><b>직접 해 보기</b> (Python 3.11)</summary>

```
pip install fullseye
git clone https://github.com/furuse-kazufumi/fullseye
cd fullseye
python examples/poc_focus_stacking.py
```

초점 합성 PoC가 약 20초 동안 실행되며 참값 대비 숫자와 `PASS`를 출력합니다. 그림은 `out/figures/poc_focus_stacking/`에 저장됩니다.

</details>

<details markdown="1">
<summary><b>링크</b></summary>

- [GitHub(소스 코드)](https://github.com/furuse-kazufumi/fullseye)
- [갤러리(모든 그림)](../../GALLERY.en.md)
- [연산자 찾기·AI(RAG)에서 쓰기](../../AI_RAG_GUIDE.ko.md) · [MCP에서 쓰기](../../MCP.md) _(ja)_
- [문서 색인](../../README.ko.md)

</details>

<details markdown="1">
<summary><b>논문 정보</b></summary>

- **제목**: Fullseye：型付き演算子と物理シミュレーションに基づく画像検査・三次元計測基盤 _(ja)_ (타입 연산자와 물리 시뮬레이션에 기반한 영상 검사·3차원 계측 기반)
- **저자**: Kazufumi Furuse(개인 연구자)
- **발표**: ViEW2026 비전 기술 실용 워크숍
- **논문 PDF**: 2026-11-26 이후 게재

**초록(일본어에서 번역)**: 영상 검사·3차원 계측 처리를 입출력 데이터 타입을 선언한 연산자의 연쇄로 구성하고, 물리·촬상 시뮬레이션으로 만든 참값에 대해 정량 평가하며, 처리 절차·평가·실패 조건을 기록해 재사용할 수 있는 오픈 소스 기반 Fullseye를 제안한다. 약 3,000개의 타입 연산자, 타입 불일치를 실행 전에 거부하는 검사, 다국어 연산자 검색(RAG), 참값을 갖춘 200개 이상의 실증 프로그램으로 이루어지며, 대표 사례의 정량 평가와 합성·실측·실기 검증 단계의 구분에 대해 보고한다.

</details>
