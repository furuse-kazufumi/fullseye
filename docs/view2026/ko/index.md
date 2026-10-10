<div class="vlang" markdown="1">

[日本語](../index.md) · [English](../en/index.md) · [简体中文](../zh/index.md) · [繁體中文](../tw/index.md) · **한국어** · [Deutsch](../de/index.md) · [हिन्दी](../hi/index.md)

</div>

# Fullseye — ViEW2026

물리 시뮬레이션과 영상 처리를 AI와 조합하고 참값으로 확인한다.

타일을 누르면 동영상·그림이 열립니다(▶ = 움직임).

<style>
.vlang { font-size: 14px; line-height: 2; }
.vg { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin: 12px 0 20px; }
@media (min-width: 600px) { .vg { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
@media (min-width: 900px) { .vg { grid-template-columns: repeat(4, minmax(0, 1fr)); } }
.vg a { display: block; position: relative; text-decoration: none; color: inherit; }
.vg img { display: block; width: 100%; max-width: 100%; height: auto; aspect-ratio: 1 / 1; object-fit: cover; border-radius: 6px; background: #222; }
.vg b { position: absolute; top: 6px; right: 6px; background: rgba(0,0,0,.6); color: #fff; font-size: 12px; padding: 1px 6px; border-radius: 9px; }
.vg span { display: block; font-size: 13px; line-height: 1.3; margin-top: 3px; }
.vl li { margin-bottom: 8px; }
</style>

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
</div>

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
- [탁구공 바운드](../../articles/assets/poc/poc_table_tennis_bounce/01_drop_test.mp4) (동영상): ITTF 탁구대 시험: 30 cm에서 공을 떨어뜨려 튀어 오른 높이를 영상에서 읽는다. **영상에서 읽은 바운드 높이 23.0 cm(참값 23.0 cm).** [소스](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_table_tennis_bounce.py)

**로봇·공간 지각**

- [겹눈 라이트 필드](../../articles/assets/poc/poc_compound_eye/02_compound_eye_superposition.png) (그림): 낱눈 배열을 라이트 필드 센서로 합성하고 같은 점을 N개 낱눈으로 겹친다. **SNR 이득은 N=5에서 2.25(√5 = 2.24), N=49에서 5.33(√49 = 7.00).** [소스](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_compound_eye.py)
- [펙 삽입](../../articles/assets/poc/poc_pegsim_insertion/04_pegsim_insert_corrected.gif) (GIF): 손목 카메라로 구멍 위치를 재서 다가가고, 유연한 손목으로 펙을 넣는다(MuJoCo). **서보 7회로 참 오차 2.24 → 0.03 mm. 보정한 삽입은 12 / 12 성공.** [소스](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pegsim_insertion.py)
- [에어하키](../../articles/assets/poc/poc_air_hockey_intercept/02_airhockey_prediction_cone_narrows.gif) (GIF): 거친 카메라로 퍽을 추적해 수비선과의 교점을 예측한다. 프레임이 늘수록 예측 띠가 좁아진다. **교점의 95 % 띠는 N = 3 프레임에서 145 mm → N = 16 프레임에서 7 mm.** [소스](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_air_hockey_intercept.py)
- [시각 촉각 센서](../../articles/assets/poc/poc_tacsim_elastic_membrane/03_tacsim_force_sweep.gif) (GIF): 구로 탄성막을 누르는 하중을 올리며 막 영상에서 접촉 반경을 읽는다. **Hertz 닫힌 식 대비 접촉 반경 오차 0.05〜0.26 %, 하중 오차 0.14〜0.79 %(0.02〜0.12 N).** [소스](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_tacsim_elastic_membrane.py)

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
