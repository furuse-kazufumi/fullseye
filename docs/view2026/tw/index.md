<div class="vlang" markdown="1">

[日本語](../index.md) · [English](../en/index.md) · [简体中文](../zh/index.md) · **繁體中文** · [한국어](../ko/index.md) · [Deutsch](../de/index.md) · [हिन्दी](../hi/index.md)

</div>

# Fullseye — ViEW2026

把物理模擬與影像處理交給 AI 組合,並以真值驗證。

點按圖塊即可開啟影片或圖(▶ = 動態)。

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
</div>

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
- [桌球彈跳](../../articles/assets/poc/poc_table_tennis_bounce/01_drop_test.mp4) (影片): ITTF 球桌測試:從 30 cm 落球,從影片讀取彈起高度。 **從影片讀出的彈起高度 23.0 cm(真值 23.0 cm)。** [原始碼](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_table_tennis_bounce.py)

**機器人與空間感知**

- [複眼光場](../../articles/assets/poc/poc_compound_eye/02_compound_eye_superposition.png) (圖): 把小眼陣列合成為光場感測器,以 N 個小眼疊加同一點。 **SNR 增益:N=5 時 2.25(√5 = 2.24),N=49 時 5.33(√49 = 7.00)。** [原始碼](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_compound_eye.py)
- [插銷入孔](../../articles/assets/poc/poc_pegsim_insertion/04_pegsim_insert_corrected.gif) (GIF): 以腕部相機量出孔的位置並靠近,再以柔性手腕插入插銷(MuJoCo)。 **伺服 7 次後真實偏差 2.24 → 0.03 mm。有校正的插入 12 / 12 成功。** [原始碼](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pegsim_insertion.py)
- [空氣曲棍球](../../articles/assets/poc/poc_air_hockey_intercept/02_airhockey_prediction_cone_narrows.gif) (GIF): 以低解析度相機追蹤冰球,預測它與防守線的交點。影格越多,預測帶越窄。 **交點的 95 % 帶:N = 3 影格時 145 mm → N = 16 影格時 7 mm。** [原始碼](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_air_hockey_intercept.py)
- [視觸覺感測器](../../articles/assets/poc/poc_tacsim_elastic_membrane/03_tacsim_force_sweep.gif) (GIF): 以球壓彈性膜並增大載荷,從膜的影像讀取接觸半徑。 **相對 Hertz 閉合式:接觸半徑誤差 0.05〜0.26 %,載荷誤差 0.14〜0.79 %(0.02〜0.12 N)。** [原始碼](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_tacsim_elastic_membrane.py)

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
