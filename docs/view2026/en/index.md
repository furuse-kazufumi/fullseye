<div class="vlang" markdown="1">

[日本語](../index.md) · **English** · [简体中文](../zh/index.md) · [繁體中文](../tw/index.md) · [한국어](../ko/index.md) · [Deutsch](../de/index.md) · [हिन्दी](../hi/index.md)

</div>

# Fullseye — ViEW2026

Physics simulation and image processing, combined with AI and checked against ground truth.

Tap a tile to open the video or figure (▶ = moving).

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
<a href="../../articles/assets/poc/poc_real_defect_floor/02_defect_floor_sweep.gif"><img src="../thumbs/poc_real_defect_floor.jpg" alt="Faint-defect limit" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Faint-defect limit</span></a>
<a href="../../articles/assets/poc/poc_active_contours/06_u_shape_snakes.mp4"><img src="../thumbs/poc_active_contours.jpg" alt="Active contours" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Active contours</span></a>
<a href="../../articles/assets/poc/poc_dic_strain/05_tensile_ramp.mp4"><img src="../thumbs/poc_dic_strain.jpg" alt="DIC strain" loading="lazy" width="320" height="320"><b>&#9654;</b><span>DIC strain</span></a>
<a href="../../articles/assets/poc/poc_focus_stacking/05_focus_sweep.mp4"><img src="../thumbs/poc_focus_stacking.jpg" alt="Focus stacking" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Focus stacking</span></a>
<a href="../../articles/assets/poc/poc_registration_basin/05_icp_basin_iterations.mp4"><img src="../thumbs/poc_registration_basin.jpg" alt="Point-cloud ICP" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Point-cloud ICP</span></a>
<a href="../../articles/assets/poc/poc_stockpile_volume/07_scan_orbit.mp4"><img src="../thumbs/poc_stockpile_volume.jpg" alt="Stockpile volume" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Stockpile volume</span></a>
<a href="../../articles/assets/poc/poc_ct_fidelity/01_recon_sweep.png"><img src="../thumbs/poc_ct_fidelity.jpg" alt="CT reconstruction" loading="lazy" width="320" height="320"><span>CT reconstruction</span></a>
<a href="../../articles/assets/poc/poc_ct_void_morphology/13_section_sweep.mp4"><img src="../thumbs/poc_ct_void_morphology.jpg" alt="CT voids" loading="lazy" width="320" height="320"><b>&#9654;</b><span>CT voids</span></a>
<a href="../../articles/assets/poc/poc_interferometry_step/05_step_sweep.mp4"><img src="../thumbs/poc_interferometry_step.jpg" alt="White-light steps" loading="lazy" width="320" height="320"><b>&#9654;</b><span>White-light steps</span></a>
<a href="../../articles/assets/poc/poc_polarization_specular/03_separation.png"><img src="../thumbs/poc_polarization_specular.jpg" alt="Polarization" loading="lazy" width="320" height="320"><span>Polarization</span></a>
<a href="../../articles/assets/poc/poc_photoelasticity/03_load_and_isoclinics.mp4"><img src="../thumbs/poc_photoelasticity.jpg" alt="Photoelasticity" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Photoelasticity</span></a>
<a href="../../articles/assets/poc/poc_thermography_ndt/02_depth_map.png"><img src="../thumbs/poc_thermography_ndt.jpg" alt="Thermography NDT" loading="lazy" width="320" height="320"><span>Thermography NDT</span></a>
<a href="../../articles/assets/poc/poc_motion_magnification/05_magnify_video.mp4"><img src="../thumbs/poc_motion_magnification.jpg" alt="Motion magnification" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Motion magnification</span></a>
<a href="../../articles/assets/poc/poc_table_tennis_bounce/01_drop_test.mp4"><img src="../thumbs/poc_table_tennis_bounce.jpg" alt="Ping-pong bounce" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Ping-pong bounce</span></a>
<a href="../../articles/assets/poc/poc_compound_eye/02_compound_eye_superposition.png"><img src="../thumbs/poc_compound_eye.jpg" alt="Compound eye" loading="lazy" width="320" height="320"><span>Compound eye</span></a>
<a href="../../articles/assets/poc/poc_pegsim_insertion/04_pegsim_insert_corrected.gif"><img src="../thumbs/poc_pegsim_insertion.jpg" alt="Peg-in-hole" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Peg-in-hole</span></a>
<a href="../../articles/assets/poc/poc_air_hockey_intercept/02_airhockey_prediction_cone_narrows.gif"><img src="../thumbs/poc_air_hockey_intercept.jpg" alt="Air hockey" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Air hockey</span></a>
<a href="../../articles/assets/poc/poc_tacsim_elastic_membrane/03_tacsim_force_sweep.gif"><img src="../thumbs/poc_tacsim_elastic_membrane.jpg" alt="Tactile sensor" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Tactile sensor</span></a>
</div>

## What you see, and the measured number

Every number is measured against ground truth the PoC planted itself (closed form, analytic solution or published value); running the PoC prints the same value.

<div class="vl" markdown="1">

**Inspection and appearance**

- [Faint-defect limit](../../articles/assets/poc/poc_real_defect_floor/02_defect_floor_sweep.gif) (GIF): The same planted defect grows on a real brick texture and on a synthetic background with matched noise. **Even with matched noise, the detection limit on real textures is 2.03-3.47x the synthetic one (defects of known position and amplitude).** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_defect_floor.py)
- [Active contours](../../articles/assets/poc/poc_active_contours/06_u_shape_snakes.mp4) (video): Classic snake (red) bridges the U-shaped notch; GVF (blue) reaches the bottom. Green is the true edge. **Swapping only the external force to GVF gives Dice 0.993 against the true edge.** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_active_contours.py)
- [DIC strain](../../articles/assets/poc/poc_dic_strain/05_tensile_ramp.mp4) (video): Strain maps read from speckle images as the tensile load ramps up (the machine also rotates by 2 degrees). **True strain 3000 µε. Small-strain reads 2341 µε (rotation hides it); Green-Lagrange reads 2961 µε (theory 3005 µε).** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dic_strain.py)

**3-D measurement and geometry**

- [Focus stacking](../../articles/assets/poc/poc_focus_stacking/05_focus_sweep.mp4) (video): Sweeping focus through 17 frames, the all-in-focus image and the depth map build up. **All-in-focus PSNR 33.69 dB (central 1 frame 28.52 dB); depth error 0.467 mm on textured areas.** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_focus_stacking.py)
- [Point-cloud ICP](../../articles/assets/poc/poc_registration_basin/05_icp_basin_iterations.mp4) (video): ICP stepped 1 iteration at a time from initial rotation errors of 30, 90 and 150 degrees. **Rotation error after 60 iterations: 0.6 degrees from 30 and 90 (success), 179.5 degrees from 150 (failure).** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_registration_basin.py)
- [Stockpile volume](../../articles/assets/poc/poc_stockpile_volume/07_scan_orbit.mp4) (video): Orbiting a stockpile while adding 3-D scan positions from 1 to 3; colour is interpolated minus true surface. **Volume error +17.20 % -> +0.05 % (true base; ground-truth volume is closed-form 3572.6089 m³).** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_stockpile_volume.py)

**X-ray CT and volumes**

- [CT reconstruction](../../articles/assets/poc/poc_ct_fidelity/01_recon_sweep.png) (figure): The Shepp-Logan phantom re-imaged with 180 down to 12 projections and reconstructed. **12-view FBP (RMSE 0.2576) loses even to a blank image (0.2420). A mass check caught a -3.34 % loss, fixed to -0.0099 %.** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_fidelity.py)
- [CT voids](../../articles/assets/poc/poc_ct_void_morphology/13_section_sweep.mp4) (video): 2 bond layers with nearly equal void fraction, shown as a section sweep with rotating 3-D voids (4.3 MB video). **Void fraction 2.46 % vs 2.63 %, yet median distance to the interface is 60.0 µm vs 10.0 µm.** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_void_morphology.py)

**Optics, interferometry, polarization**

- [White-light steps](../../articles/assets/poc/poc_interferometry_step/05_step_sweep.mp4) (video): The planted step grows from 0 to 0.90 µm, measured by the coherence envelope and by phase shifting. **Bias within 2.4 nm at 1 % noise (steps of 50-500 nm). Phase shifting jumps by λ/2 at 0.153 µm.** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_interferometry_step.py)
- [Polarization](../../articles/assets/poc/poc_polarization_specular/03_separation.png) (figure): Specular reflection removed by polarization, and the shape of what remains. **The diffuse error matches the closed form R_p·E and is 0 at the Brewster angle, 56.31 degrees.** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_polarization_specular.py)
- [Photoelasticity](../../articles/assets/poc/poc_photoelasticity/03_load_and_isoclinics.mp4) (video): Fringes emerge as a disc is loaded; rotating the polarizers moves the isoclinics. **Centre fringe order 2.38, as the closed form says. The op's polariscope matches the textbook to 2.2e-16.** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_photoelasticity.py)

**Thermal, acoustic, time series**

- [Thermography NDT](../../articles/assets/poc/poc_thermography_ndt/02_depth_map.png) (figure): Depth map of 16 delaminations read from surface temperature after a flash. **A 0.5 mm deep, 2 mm wide defect reads +612 % with a 25 s fitting window and -9 % with a 4 s window.** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_thermography_ndt.py)
- [Motion magnification](../../articles/assets/poc/poc_motion_magnification/05_magnify_video.mp4) (video): A surface vibrating by 0.1 px: raw video on the left, 10x magnified on the right. **True amplitude 0.1000 px; measured 0.10012 raw and 0.10013 after magnification. It helps the eye, not the measurement.** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_motion_magnification.py)
- [Ping-pong bounce](../../articles/assets/poc/poc_table_tennis_bounce/01_drop_test.mp4) (video): ITTF table test: drop a ball from 30 cm and read the rebound height from video. **Rebound read from video: 23.0 cm (ground truth 23.0 cm).** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_table_tennis_bounce.py)

**Robotics and spatial perception**

- [Compound eye](../../articles/assets/poc/poc_compound_eye/02_compound_eye_superposition.png) (figure): A compound-eye array simulated as a light-field sensor, superposing N views of the same point. **SNR gain 2.25 at N=5 (√5 = 2.24) and 5.33 at N=49 (√49 = 7.00).** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_compound_eye.py)
- [Peg-in-hole](../../articles/assets/poc/poc_pegsim_insertion/04_pegsim_insert_corrected.gif) (GIF): A wrist camera measures the hole, the arm servos over it, and a compliant wrist inserts the peg (MuJoCo). **7 servo steps cut the true offset from 2.24 to 0.03 mm; corrected insertion succeeds 12 / 12.** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pegsim_insertion.py)
- [Air hockey](../../articles/assets/poc/poc_air_hockey_intercept/02_airhockey_prediction_cone_narrows.gif) (GIF): Tracking a puck with a coarse camera and predicting where it crosses the defence line; the band narrows with more frames. **The 95 % band of the crossing point shrinks from 145 mm at N = 3 frames to 7 mm at N = 16.** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_air_hockey_intercept.py)
- [Tactile sensor](../../articles/assets/poc/poc_tacsim_elastic_membrane/03_tacsim_force_sweep.gif) (GIF): A sphere presses an elastic membrane harder; contact radius is read from the membrane image. **Against the Hertz closed form: contact radius within 0.05-0.26 %, force within 0.14-0.79 % (0.02-0.12 N).** [source](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_tacsim_elastic_membrane.py)

</div>

## What Fullseye is

A foundation that hands physics simulation (including sensing such as optical design and 3-D measurement) and classic image processing to an AI through MCP and RAG, lets it work out a combination for each task, and solves the task interactively while checking type consistency and evaluating against ground truth. Open source (Apache-2.0).

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
- **Paper PDF**: available from 2026-11-26

**Abstract (translated from Japanese)**: We propose Fullseye, an open-source foundation that builds image-inspection and 3-D measurement processing as chains of operators with declared input and output data types, evaluates it quantitatively against ground truth produced by physics and imaging simulation, and records the procedure, the evaluation and the failure conditions so they can be reused. It consists of about 3,000 typed operators, a check that rejects type mismatches before execution, multilingual operator search (RAG), and more than 200 proof-of-concept programs with ground truth. We report quantitative evaluation of representative examples and the distinction between synthetic, measured and real-hardware validation stages.

</details>
