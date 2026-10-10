<div class="vlang" markdown="1">

[日本語](../index.md) · [English](../en/index.md) · [简体中文](../zh/index.md) · [繁體中文](../tw/index.md) · [한국어](../ko/index.md) · [Deutsch](../de/index.md) · **हिन्दी**

</div>

# Fullseye — ViEW2026

physics simulation और image processing को AI के साथ जोड़कर ground truth से जाँचना।

tile पर tap करने से video या figure खुलता है (▶ = चलता हुआ)।

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
</div>

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
- [Table tennis bounce](../../articles/assets/poc/poc_table_tennis_bounce/01_drop_test.mp4) (video): ITTF table test: ball को 30 cm से गिराकर video से उछाल की ऊँचाई पढ़ी जाती है। **video से पढ़ी उछाल की ऊँचाई 23.0 cm (ground truth 23.0 cm)।** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_table_tennis_bounce.py)

**Robotics और spatial perception**

- [Compound eye](../../articles/assets/poc/poc_compound_eye/02_compound_eye_superposition.png) (figure): compound-eye array को light-field sensor की तरह simulate करके एक ही point के N views जोड़े जाते हैं। **SNR gain N=5 पर 2.25 (√5 = 2.24), N=49 पर 5.33 (√49 = 7.00)।** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_compound_eye.py)
- [Peg-in-hole](../../articles/assets/poc/poc_pegsim_insertion/04_pegsim_insert_corrected.gif) (GIF): wrist camera hole की position मापता है, arm उसके ऊपर जाता है, और compliant wrist peg डालता है (MuJoCo)। **7 servo steps में असली offset 2.24 -> 0.03 mm; correction के साथ insertion 12 / 12 सफल।** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pegsim_insertion.py)
- [Air hockey](../../articles/assets/poc/poc_air_hockey_intercept/02_airhockey_prediction_cone_narrows.gif) (GIF): coarse camera से puck को track करके defence line से crossing point का अनुमान; frames बढ़ने पर band पतला होता है। **crossing point का 95 % band N = 3 frames पर 145 mm से N = 16 पर 7 mm।** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_air_hockey_intercept.py)
- [Tactile sensor](../../articles/assets/poc/poc_tacsim_elastic_membrane/03_tacsim_force_sweep.gif) (GIF): sphere से elastic membrane पर load बढ़ाया जाता है; membrane image से contact radius पढ़ा जाता है। **Hertz closed form के सापेक्ष: contact radius error 0.05-0.26 %, force error 0.14-0.79 % (0.02-0.12 N)।** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_tacsim_elastic_membrane.py)

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
