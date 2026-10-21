> **Language**: [日本語](https://github.com/furuse-kazufumi/fullseye/blob/master/docs/articles/fullseye_poc_museum_device_qiita_ja.md) · **English**

# A Metrology Museum on Paper — The Instrument Wing (sensors and instruments reproduced from physics)

> One wing of **[A Metrology Museum on Paper — the entrance](https://qiita.com/furuse-kazufumi/items/8a8f23e53b19ee8cdc10)**, where the other wings, the glossary and the thesis live.

**14 exhibits** hang in this wing. The numbers are accession numbers: they do not change when an exhibit moves or when an article is split.

> The "Ops used" line under each exhibit links to that op's note (type contract, pitfalls, figures, a runnable Studio program): [Operator catalogue](https://furuse.work/OP_CATALOG.html) / [Op notes index](https://furuse.work/ops/INDEX.html).

### The Instrument Wing — From Raw Output to Instrument-Specific Failure

It is easy to borrow an instrument's name and produce a convenient image. The 14 exhibits in this room instead build raw output from photons, electrons, interference, heat diffusion, scanning and ray tracing, then carry that output through to the quantity normally reported.

The same range fails differently in iToF and dToF through multipath and pile-up; the same particles read at different diameters in SEM and TEM. More TDI stages reveal dark defects while accumulating each synchronisation error across all stages. A model that omits the instrument physics cannot reproduce where the instrument breaks.

Every exhibit is gated by a closed form, public measurement or independent implementation. The aim is not to claim a complete substitute for hardware. It is to state which physics is present and which is still absent, then find when the reported measurement stops being trustworthy before touching the instrument.

## No.2026.120 —— Matching Full 2-D Inspection to Sampled 3-D Inspection — A Grid Overlaps Itself

[![Matching Full 2-D Inspection to Sampled 3-D Inspection — A Grid Overlaps Itself](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_aoi_ct_traceability/01_aoi_and_ct_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_aoi_ct_traceability/01_aoi_and_ct.png)

*↑ **Matching Full 2-D Inspection to Sampled 3-D Inspection — A Grid Overlaps Itself** ―― The real line has two stages: AOI images every unit from above, X-ray CT samples a few and images the inside. What the floor wants to know is how far the CT numbers follow from the AOI numbers — which is not a question about one instrument's accuracy but about whether two instruments' indices point at the same joint. A regular array does not match one-to-one on point positions alone: all 30 pads of a 6x5 grid have degenerate distance signatures (9 distinct ones), because the grid maps onto itself and the orientation cannot be read. Fiducials with three distinct side lengths (3600/5200/6325 um) pin rotation and reflection uniquely, and the correspondence is recovered exactly under translation, rotation and re-indexing. With that closed, AOI's apparent void fraction correlates 0.973 with CT volume fraction and the worst five agree 5/5 — yet of the 27 parts carrying an interface-touching void (the kind that shortens life), those five catch only 19 %. Agreeing on the ranking does not mean catching the dangerous ones. The failed first attempt (Kabsch alone) is kept.*

[![直線は「面積率に比例する」という素朴な仮定。点はそこから両側へ離れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_aoi_ct_traceability/02_area_vs_volume_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_aoi_ct_traceability/02_area_vs_volume.png)

*↑ The measurement ―― 直線は「面積率に比例する」という素朴な仮定。点はそこから両側へ離れる。 (figure labels are in Japanese; the numbers are the same)*

[![AOI の面積率が大きい接合部が、界面に接するボイドを持つとは限らない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_aoi_ct_traceability/03_interface_voids_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_aoi_ct_traceability/03_interface_voids.png)

*↑ AOI の面積率が大きい接合部が、界面に接するボイドを持つとは限らない。*

[![同じロットを同じ「悪い順」で並べても、順位は一致しない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_aoi_ct_traceability/04_worst_first_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_aoi_ct_traceability/04_worst_first.png)

*↑ 同じロットを同じ「悪い順」で並べても、順位は一致しない。*

```
py -3.11 examples/poc_aoi_ct_traceability.py
```

Source: [examples/poc_aoi_ct_traceability.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_aoi_ct_traceability.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_aoi_ct_traceability)

Ops used (notes): [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html)

## No.2026.022 —— How Accurately a White-Light Interferometer Measures a Nanometre Step

[![How Accurately a White-Light Interferometer Measures a Nanometre Step](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/01_interferogram_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/01_interferogram.png)

*↑ **How Accurately a White-Light Interferometer Measures a Nanometre Step** ―― A synthesised coherence-scanning stack with steps of 50 to 500 nm measured back. At 1 % noise the bias stays within 2.4 nm and the standard deviation within 14.1 nm, almost independent of step height. The null (envelope's maximum sample) errs by exactly half the scan step, and at 0.14 µm, just inside the Nyquist ceiling of 0.15 µm, the noise-free error is already +14.1 nm.*

[![0.02〜0.12 µm は 0.05 nm 以内で平ら。Nyquist 上限 0.15 µm の手前 0.14 µm で崖。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/02_zstep_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/02_zstep_sweep.png)

*↑ The measurement ―― 0.02〜0.12 µm は 0.05 nm 以内で平ら。Nyquist 上限 0.15 µm の手前 0.14 µm で崖。 (figure labels are in Japanese; the numbers are the same)*

[![centroid は散らばりが gaussian の 1/3〜1/5 なのに総合誤差では上に来る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/03_noise_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/03_noise_sweep.png)

*↑ centroid は散らばりが gaussian の 1/3〜1/5 なのに総合誤差では上に来る。*

[![4 種の段差でゲインが揃う = オフセットではなく倍率の誤差。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/04_centroid_gain_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/04_centroid_gain.png)

*↑ 4 種の段差でゲインが揃う = オフセットではなく倍率の誤差。*

[![動画(148 コマ): 仕込む段差を 0 → 0.90 µm へ連続に増やし、同じ表面を 2 つの方法で測る(雑音なし)。左は低い側・高い側 1 画素ずつのコヒーレンス走査の信号で、縦線は csi_height_map(gaussian)が](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/05_step_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/05_step_sweep.gif)

*↑ The animation ―― 動画(148 コマ): 仕込む段差を 0 → 0.90 µm へ連続に増やし、同じ表面を 2 つの方法で測る(雑音なし)。左は低い側・高い側 1 画素ずつのコヒーレンス走査の信号で、縦線は csi_height_map(gaussian)が包絡線から読んだ高さ。右は測った段差 vs 仕込んだ段差。包絡線(だいだい)は全域で対角線に乗り、誤差は最大 8.5e-11 nm —— 包絡線には周期が無いので巻き戻らない。位相シフト法(水色、4 段)は段差 0.153 µm(λ/4 = 0.150 µm の直後)で初めて λ/2 ぶん飛び、以後 λ/2 ごとに鋸の歯になる。*

```
py -3.11 examples/poc_interferometry_step.py
```

Source: [examples/poc_interferometry_step.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_interferometry_step.py)

This run produced **5 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_interferometry_step)

Ops used (notes): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`csi_design`](https://furuse.work/ops/interferometry/design/csi_design.html) · [`csi_height_map`](https://furuse.work/ops/interferometry/surface/csi_height_map.html) · [`csi_stack_simulate`](https://furuse.work/ops/interferometry/simulate/csi_stack_simulate.html) · [`decode_fringe`](https://furuse.work/ops/3d/structured_light/decode_fringe.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`synthesize_fringes`](https://furuse.work/ops/3d/structured_light/synthesize_fringes.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html)

## No.2026.023 —— Depth From a Light Field — A Light Field of Known Depth, Confronted With Its Nulls

[![Depth From a Light Field — A Light Field of Known Depth, Confronted With Its Nulls](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/01_scene_and_depth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/01_scene_and_depth.png)

*↑ **Depth From a Light Field — A Light Field of Known Depth, Confronted With Its Nulls** ―― A 9×9 light field rendered by analytic inverse mapping, with focus-measure, EPI-slope and two-view block matching scored against the true slope map. The winner beats the constant null by 22x, but beats two-view matching — which uses only 2 of the 81 views — by just 1.6x, and only with cubic interpolation. The default linear interpolation snaps to integer slopes, reading a true 1.30 as 1.4750 (11.9 % in depth).*

[![linear は 1.08/1.15 を 1.0 へ、1.85 を 2.0 側へ引く。cubic は恒等線に乗る。生成側の補間はゼロ(Fourier シフト)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/02_focus_snapping_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/02_focus_snapping.png)

*↑ The measurement ―― linear は 1.08/1.15 を 1.0 へ、1.85 を 2.0 側へ引く。cubic は恒等線に乗る。生成側の補間はゼロ(Fourier シフト)。 (figure labels are in Japanese; the numbers are the same)*

[![EPI は SNR 20 で既に -35 %。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/03_texture_breakdown_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/03_texture_breakdown.png)

*↑ EPI は SNR 20 で既に -35 %。*

[![境界から 5 px 離れれば内側の水準に戻る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/04_occlusion_bands_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/04_occlusion_bands.png)

*↑ 境界から 5 px 離れれば内側の水準に戻る。*

```
py -3.11 examples/poc_lightfield_depth.py
```

Source: [examples/poc_lightfield_depth.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_lightfield_depth.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_lightfield_depth)

Ops used (notes): [`lf_depth_from_focus`](https://furuse.work/ops/lightfield/depth/lf_depth_from_focus.html) · [`lf_disparity_to_depth`](https://furuse.work/ops/lightfield/depth/lf_disparity_to_depth.html) · [`lf_epi`](https://furuse.work/ops/lightfield/views/lf_epi.html) · [`lf_epi_slope`](https://furuse.work/ops/lightfield/depth/lf_epi_slope.html) · [`lf_refocus`](https://furuse.work/ops/lightfield/refocus/lf_refocus.html)

## No.2026.033 —— Stripping Specular Reflection With Polarisation — Truth From the Fresnel Equations

[![Stripping Specular Reflection With Polarisation — Truth From the Fresnel Equations](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/01_fresnel_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/01_fresnel.png)

*↑ **Stripping Specular Reflection With Polarisation — Truth From the Fresnel Equations** ―― Diffuse and specular components synthesised as s/p terms with the degree of polarisation from the Fresnel equations, and the separation scored against them. At 20 degrees of incidence the polarisation method wins by only 1.2x. The diffuse error matches the closed form R_p·E exactly and vanishes at the Brewster angle of 56.31 degrees — the diffuse term of `polarization_separate` is systematically high by that amount.*

[![実測と閉形式が重なる。70 度の絶対誤差は 20 度より悪いのに、ゼロ点比では 70 度が最良 —— 最適角は評価軸で割れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/02_angle_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/02_angle_error.png)

*↑ The measurement ―― 実測と閉形式が重なる。70 度の絶対誤差は 20 度より悪いのに、ゼロ点比では 70 度が最良 —— 最適角は評価軸で割れる。 (figure labels are in Japanese; the numbers are the same)*

[![残差はローブと同じ形。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/03_separation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/03_separation.png)

*↑ 残差はローブと同じ形。*

[![画素率 1.8 倍で誤差 2.8 倍 —— 雑音(σ に比例)や較正誤差(δ に比例)と違い、飽和は超線形に効く。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/04_saturation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/04_saturation.png)

*↑ 画素率 1.8 倍で誤差 2.8 倍 —— 雑音(σ に比例)や較正誤差(δ に比例)と違い、飽和は超線形に効く。*

```
py -3.11 examples/poc_polarization_specular.py
```

Source: [examples/poc_polarization_specular.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_polarization_specular.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_polarization_specular)

Ops used (notes): [`fresnel_reflectance`](https://furuse.work/ops/3d/optics/fresnel_reflectance.html) · [`polarization_dolp_map`](https://furuse.work/ops/specular/polarization/polarization_dolp_map.html) · [`polarization_render`](https://furuse.work/ops/specular/polarization/polarization_render.html) · [`polarization_separate`](https://furuse.work/ops/specular/polarization/polarization_separate.html) · [`polarization_stokes`](https://furuse.work/ops/specular/polarization/polarization_stokes.html) · [`rmse`](https://furuse.work/ops/imgmetrics/fidelity/rmse.html)

## No.2026.043 —— Depth of a Subsurface Defect by Pulsed Thermography

[![Depth of a Subsurface Defect by Pulsed Thermography](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/02_depth_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/02_depth_map.png)

*↑ **Depth of a Subsurface Defect by Pulsed Thermography** ―― Surface temperature after a flash, generated from the exact 1-D heat-conduction solution, with delamination depth estimated from the image sequence. Where the diameter is at least four times the depth the estimate lands within a few percent; at 0.5 mm deep and 2 mm across it is off by +627 %. The cause is not lateral diffusion but the fitting window: shortening it from 25 s to 4 s brings that case back to -9 %.*

[![右下三角(直径が深さの 4 倍以上)は数 %。左上は横拡散で壊れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/01_depth_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/01_depth_table.png)

*↑ The measurement ―― 右下三角(直径が深さの 4 倍以上)は数 %。左上は横拡散で壊れる。 (figure labels are in Japanese; the numbers are the same)*

[![早期の勾配は -1/2。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/03_tsr_curves_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/03_tsr_curves.png)

*↑ 早期の勾配は -1/2。*

```
py -3.11 examples/poc_thermography_ndt.py
```

Source: [examples/poc_thermography_ndt.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_thermography_ndt.py)

This run produced **3 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_thermography_ndt)



## No.2026.178 —— Measuring a Camera Without Buying One — Recovering Quantum Efficiency, Gain and Dark Noise from a Planted Sensor with the EMVA 1288 Procedure

[![Measuring a Camera Without Buying One — Recovering Quantum Efficiency, Gain and Dark Noise from a Planted Sensor with the EMVA 1288 Procedure](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/01_photon_transfer.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/01_photon_transfer.gif)

*↑ **Measuring a Camera Without Buying One — Recovering Quantum Efficiency, Gain and Dark Noise from a Planted Sensor with the EMVA 1288 Procedure** ―― The quantum efficiency η, system gain K, dark noise σ_d, saturation, SNR, dynamic range, DSNU and PRNU on a camera datasheet are numbers produced by the procedure of EMVA 1288 Release 4.0 Linear. This exhibit **synthesises a sensor from a physical model** (Poisson photons → electrons → dark noise and dark current → gain K → quantisation and saturation, with column, row and pixel DSNU and a PRNU pattern) and recovers the planted values with **the standard's estimators**, the new op family sensorchar (10 ops). Synthesis and estimation use different equations. Gates: recovery — from the photon transfer (eq. 50) of mean and temporal variance of image pairs at equal exposure (eqs. 16, 18) K to -0.66 %, from dark images σ_d to +0.13 % (eq. 53), from the response slope η to +0.67 % (eq. 52), dark current to +0.6 %, the column/row/pixel spatial variances (eq. 42) and DSNU +0.6 %, PRNU -0.1 % / identities — SNR(μ_p.min) = 1 (eqs. 26 and 21 are written independently) and the ideal sensor = √μ_p (eq. 23) to machine precision, slope 1 → 1/2 (eq. 22) / validity — below a dark variance of 0.24 DN² σ_d is not estimated (eqs. 53, 54), and for a flat sensor that is where the estimate really breaks / published values — on manufacturers' published EMVA 1288 data for 38 models the maximum SNR = √μ_e.sat (eq. 55) holds within 0.49 dB for all / linearity — the closed form of the linearity error (eqs. 58–63) matches an independent weighted least-squares fit to 3.9e-13 / defect pixels — the 9 planted ones are counted back. Found on the way: taking σ_d from the photon-transfer **intercept** is off by +53.5 % (the standard measures it directly from dark images). A DSNU pattern dithers the quantiser, so even at K = 0.10, which the standard calls unmeasurable, σ_d comes out within 0.7 % (flat: 29.8 %) — the standard's limit is conservative. Ledger entry no. 8 gives a DR of 68.9 dB from its 21.0 ke⁻ saturation and 7 e⁻ dark noise, but lists 74 dB — one of the two columns seems to come from other conditions (not checked; the ledger is left as is and the gate names it). The rest of the standard (added 2026-10-13): on the simulated camera described in section 5 of the standard (640 x 480, two 1.5 DN sinusoids in the DSNU, illumination falling 3 % towards the corners) the PRNU reads 0.831 % without the section 8.1 highpass filter (planted 0.5 %, +66 %) and 0.497 % with it (lower by the filter's white gain 0.9885); the DSNU drops from 21.25 to 18.83 e- because the 25-pixel sinusoid passes at 38 %, as the transfer function predicts; the section 8.6 spectrogram recovers the sinusoid amplitudes as 1.46 / 1.50 DN with equation 72; the factor 0.92 printed in equation 86 of appendix C.5 disagrees with the measured 0.960 (Parseval, 1 - 1/25). The equation 51 linearity check (mean relative deviation of the local slope < 3 %) needs pixels: a linear 128 x 160 sensor failed it once in six runs, a 512 x 640 one never. Honestly: a synthetic sensor, uniform illumination in sections 1-7, and the published values are rounded integers without K, so the DR check treats the quantisation noise as zero. How in-camera processing moves the numbers is the sequel poc_emva1288_in_camera_processing. 14 gates, about 4 s.*

[![SNR は暗い側で傾き 1(暗雑音が支配)、明るい側で傾き 1/2(光子雑音が支配)。SNR = 1 になる露光が絶対感度しきい値 μ_p.min = 6.8 光子。量子化雑音の分だけ μ_e.min = 4.20 e⁻ は暗雑音 3.4 ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/02_snr_curve_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/02_snr_curve.png)

*↑ The measurement ―― SNR は暗い側で傾き 1(暗雑音が支配)、明るい側で傾き 1/2(光子雑音が支配)。SNR = 1 になる露光が絶対感度しきい値 μ_p.min = 6.8 光子。量子化雑音の分だけ μ_e.min = 4.20 e⁻ は暗雑音 3.4 e⁻ より大きい。 (figure labels are in Japanese; the numbers are the same)*

[![暗画像の分散が 0.24 DN² より小さいと、規格は σ_d を推定しない(式 53・54)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/03_validity_boundary_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/03_validity_boundary.png)

*↑ 暗画像の分散が 0.24 DN² より小さいと、規格は σ_d を推定しない(式 53・54)。*

[![メーカーが公表した EMVA 1288 データ 38 型番の飽和容量・暗雑音・量子効率から式 (28) で DR を出し直す。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/04_datasheet_dynamic_range_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/04_datasheet_dynamic_range.png)

*↑ メーカーが公表した EMVA 1288 データ 38 型番の飽和容量・暗雑音・量子効率から式 (28) で DR を出し直す。*

[![白い DSNU は平らな床(高さ = 標準偏差 1.5 DN)、正弦は鋭い山(横 0.04・縦 0.2 c/px)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/06_spectrogram_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/06_spectrogram.png)

*↑ 白い DSNU は平らな床(高さ = 標準偏差 1.5 DN)、正弦は鋭い山(横 0.04・縦 0.2 c/px)。*

[![Release 4.0 のフィルタは高域でほぼ 1(付録 E.3)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/07_highpass_transfer_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/07_highpass_transfer.png)

*↑ Release 4.0 のフィルタは高域でほぼ 1(付録 E.3)。*

```
py -3.11 examples/poc_emva1288_sensor.py
```

Source: [examples/poc_emva1288_sensor.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_emva1288_sensor.py)

This run produced **8 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_emva1288_sensor)

Ops used (notes): [`emva_dark_current`](https://furuse.work/ops/optics/sensorchar/emva_dark_current.html) · [`emva_defect_pixels`](https://furuse.work/ops/optics/sensorchar/emva_defect_pixels.html) · [`emva_dynamic_range`](https://furuse.work/ops/optics/sensorchar/emva_dynamic_range.html) · [`emva_exposure_for_snr`](https://furuse.work/ops/optics/sensorchar/emva_exposure_for_snr.html) · [`emva_highpass`](https://furuse.work/ops/optics/sensorchar/emva_highpass.html) · [`emva_linearity_error`](https://furuse.work/ops/optics/sensorchar/emva_linearity_error.html) · [`emva_pair_statistics`](https://furuse.work/ops/optics/sensorchar/emva_pair_statistics.html) · [`emva_photon_exposure`](https://furuse.work/ops/optics/sensorchar/emva_photon_exposure.html) · [`emva_photon_transfer`](https://furuse.work/ops/optics/sensorchar/emva_photon_transfer.html) · [`emva_ptc_linearity_check`](https://furuse.work/ops/optics/sensorchar/emva_ptc_linearity_check.html) · [`emva_quantum_efficiency`](https://furuse.work/ops/optics/sensorchar/emva_quantum_efficiency.html) · [`emva_sensitivity_threshold`](https://furuse.work/ops/optics/sensorchar/emva_sensitivity_threshold.html) · [`emva_snr_curve`](https://furuse.work/ops/optics/sensorchar/emva_snr_curve.html) · [`emva_spatial_nonuniformity`](https://furuse.work/ops/optics/sensorchar/emva_spatial_nonuniformity.html) · [`emva_spectrogram`](https://furuse.work/ops/optics/sensorchar/emva_spectrogram.html) · [`emva_total_snr`](https://furuse.work/ops/optics/sensorchar/emva_total_snr.html) · [`spectrogram`](https://furuse.work/ops/oned/signal/spectrogram.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html)

## No.2026.053 —— The Arrival-Time Surface as an Isosurface in (x, y, t)

[![The Arrival-Time Surface as an Isosurface in (x, y, t)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/01_dt_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/01_dt_sweep.png)

*↑ **The Arrival-Time Surface as an Isosurface in (x, y, t)** ―― The arrival-time surface of wavefronts spreading from point sources, extracted as an isosurface of the (x, y, t) volume. The null (first frame above threshold) is biased by Δt/2, which more frames cannot remove; linear sub-frame interpolation is 27x better (0.0209 ms). Parabolic interpolation loses to linear, and linear is at its best (a 3.8x margin) when the threshold sits at the Gaussian's inflection point θ = 0.6065.*

[![変曲点 θ=0.6065 では線形が 3.8 倍勝ち、θ=0.2 では放物線が 3.6 倍勝つ。交点は θ≈0.35 と θ≈0.75。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/02_threshold_crossover_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/02_threshold_crossover.png)

*↑ The measurement ―― 変曲点 θ=0.6065 では線形が 3.8 倍勝ち、θ=0.2 では放物線が 3.6 倍勝つ。交点は θ≈0.35 と θ≈0.75。 (figure labels are in Japanese; the numbers are the same)*

[![各帯の中央値。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/03_merge_line_speed_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/03_merge_line_speed.png)

*↑ 各帯の中央値。*

[![差は上下 99 % 分位(±0.0327 ms)で切った。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/04_arrival_surface_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/04_arrival_surface.png)

*↑ 差は上下 99 % 分位(±0.0327 ms)で切った。*

[![動画(624 × 586、20 fps、171 コマ): 2 つの点源から波面が広がる(源 B は 4 ms 遅れて点火)。左が波面の強度、右は線形補間で出した到達時刻を、波面が通り過ぎた画素から順に塗ったもの —— 動画 (t, y, x](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/05_arrival_video.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/05_arrival_video.gif)

*↑ The animation ―― 動画(624 × 586、20 fps、171 コマ): 2 つの点源から波面が広がる(源 B は 4 ms 遅れて点火)。左が波面の強度、右は線形補間で出した到達時刻を、波面が通り過ぎた画素から順に塗ったもの —— 動画 (t, y, x) を1 つの体積とみなしたときの等値面が、こうして 1 枚の面になる。点線は撮る前に閉形式で予測した合流線。下段は行 72 の断面で、白 = 真値、橙 = ゼロ点(初めてしきい値を超えたコマの時刻、1 ms の階段)、青 = 線形補間。最後に全画素の誤差: ゼロ点 RMS 0.568 ms(偏り +0.489)、線形補間 RMS 0.0209 ms(27 倍)。*

```
py -3.11 examples/poc_xyt_event_surface.py
```

Source: [examples/poc_xyt_event_surface.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_xyt_event_surface.py)

This run produced **5 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_xyt_event_surface)

Ops used (notes): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`data_to_pixel`](https://furuse.work/ops/annotate/plot/data_to_pixel.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html) · [`vertex_normals`](https://furuse.work/ops/3d/mesh_process/vertex_normals.html) · [`vol_edge_probe`](https://furuse.work/ops/3d/probe/vol_edge_probe.html)

## No.2026.234 —— Finding Micrometre Dents a Photograph Cannot Show, in the Mirror Image of a Fringe Screen — Phase-Measuring Deflectometry

[![Finding Micrometre Dents a Photograph Cannot Show, in the Mirror Image of a Fringe Screen — Phase-Measuring Deflectometry](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/03_photo_vs_pmd_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/03_photo_vs_pmd.png)

*↑ **Finding Micrometre Dents a Photograph Cannot Show, in the Mirror Image of a Fringe Screen — Phase-Measuring Deflectometry** ―― A dent a few micrometres deep in a glossy surface (a painted car panel, a cover glass) is all but invisible in a lit photograph, because a mirror only shows the light. Put a screen in front of the surface, show phase-shifted fringes and photograph their mirror image: a tilt of 1e-3 rad moves the reflected point 0.6 mm on a screen 30 cm away. Six new ops (`deflectometry`, category `deflectometry` of `opsspecular`): the rig, the screen pattern, the forward render (height field to fringe mirror image, with a diffuse fraction, scatter, the back reflection of glass, aperture-integrated focus and noise), phase to normals (via `match3d.normal_from_reflection`), slope to curvature (one derivative, no integration) and the closed-form sensitivity. On a painted panel with 3 µm and 1 µm dents, 0.8 µm waviness and 0.12 µm polishing marks the photograph's defect signal peaks at 0.00066 (0.17 of one 8-bit step) while the curvature map shows the dents at SNR 110 and 57, and the integrated depth is within 0.5 % of the truth. Phase noise matches sqrt(2/N) sigma/b at 1.00 and slope noise is 0.67 of sigma_u/(2d), the sqrt(4/9) of bilinear resampling. Where it breaks: lifting the part by 0.3 mm adds the apparent tilt dz sin(theta)/d (to 0.1 %) and a 388 m bowl while the dent depth moves 0.7 %; a 2 % screen-distance error makes dents 2.3 % shallower; a 1 µm dent survives a diffuse fraction of 0.85 and fringe orders start to jump at 0.9; on uncoated cover glass the back-surface light is bent the other way by the dent's wedge, so the slope sensitivity shrinks to the closed-form 0.246 (measured 0.246) and dents look a quarter as deep; with an 8 mm aperture, focusing on the surface leaves 0.60 of the fringe amplitude and focusing on the screen leaves 0.52 of the depth. Nothing learned, nothing calibrated, 22 gates.*

[![面の前の画面(520 × 320 mm)にこの 4 枚を順に出し、面に映った鏡像を撮る。縦縞は画面の u(入射面内)を、同じ 4 枚を横縞にしたものが v を符号化する。粗い縞(周期 160 mm)の 4 枚で次数を決める。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/01_screen_patterns_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/01_screen_patterns.png)

*↑ The measurement ―― 面の前の画面(520 × 320 mm)にこの 4 枚を順に出し、面に映った鏡像を撮る。縦縞は画面の u(入射面内)を、同じ 4 枚を横縞にしたものが v を符号化する。粗い縞(周期 160 mm)の 4 枚で次数を決める。 (figure labels are in Japanese; the numbers are the same)*

[![左が真値の高さ(視野 40 mm、青 = 高い・橙 = 低い)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/02_sample_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/02_sample.png)

*↑ 左が真値の高さ(視野 40 mm、青 = 高い・橙 = 低い)。*

[![真値(破線)と復元(実線)はほぼ重なるので、差を 10 倍にして点線で重ねた。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/05_dimple_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/05_dimple_profile.png)

*↑ 真値(破線)と復元(実線)はほぼ重なるので、差を 10 倍にして点線で重ねた。*

[![平らな板を 0.3 mm 浮かせただけで、測った高さは 40 mm で約 14 µm 傾く(左、視野の中心で 3.4e-4 rad)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/08_ambiguity_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/08_ambiguity_map.png)

*↑ 平らな板を 0.3 mm 浮かせただけで、測った高さは 40 mm で約 14 µm 傾く(左、視野の中心で 3.4e-4 rad)。*

[![表と裏の反射率はほぼ同じ(R1 0.043、R2 0.039)なので、2 つの縞の和の位相は上限 1.16 rad までずれ得る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/12_glass_back_reflection_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/12_glass_back_reflection.png)

*↑ 表と裏の反射率はほぼ同じ(R1 0.043、R2 0.039)なので、2 つの縞の和の位相は上限 1.16 rad までずれ得る。*

[![拡散成分 k_d = 0, 0.5, 0.8, 0.85, 0.9, 0.95, 0.98, 0.99, 0.995 と上げていったときの平均曲率(±2.5e-3 /mm)。雑音が 1/(1 − k_d) で増え、浅い凹み B が先に沈み、](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/09_diffuse_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/09_diffuse_sweep.gif)

*↑ The animation ―― 拡散成分 k_d = 0, 0.5, 0.8, 0.85, 0.9, 0.95, 0.98, 0.99, 0.995 と上げていったときの平均曲率(±2.5e-3 /mm)。雑音が 1/(1 − k_d) で増え、浅い凹み B が先に沈み、最後は粗い縞の次数が飛ぶ。*

```
py -3.11 examples/poc_phase_measuring_deflectometry.py
```

Source: [examples/poc_phase_measuring_deflectometry.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_phase_measuring_deflectometry.py)

This run produced **14 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry)

Ops used (notes): [`absolute_phase`](https://furuse.work/ops/3d/structured_light/absolute_phase.html) · [`deflectometry_phase_to_slope`](https://furuse.work/ops/specular/deflectometry/deflectometry_phase_to_slope.html) · [`deflectometry_render`](https://furuse.work/ops/specular/deflectometry/deflectometry_render.html) · [`deflectometry_rig`](https://furuse.work/ops/specular/deflectometry/deflectometry_rig.html) · [`deflectometry_screen_pattern`](https://furuse.work/ops/specular/deflectometry/deflectometry_screen_pattern.html) · [`deflectometry_sensitivity`](https://furuse.work/ops/specular/deflectometry/deflectometry_sensitivity.html) · [`fresnel_dielectric`](https://furuse.work/ops/optics/interface/fresnel_dielectric.html) · [`integrate`](https://furuse.work/ops/3d/tsdf_fusion/integrate.html) · [`sfp_height`](https://furuse.work/ops/optics/shape_from_polarization/sfp_height.html) · [`slope_to_curvature`](https://furuse.work/ops/specular/deflectometry/slope_to_curvature.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`wrapped_phase`](https://furuse.work/ops/3d/structured_light/wrapped_phase.html)

## No.2026.235 —— TDI Line Scan and Line-Scan Lenses — Stages Reveal the Defects, a Sync Error Smears Them, and a C-Mount Lens Loses the Ends of a Long Sensor

[![TDI Line Scan and Line-Scan Lenses — Stages Reveal the Defects, a Sync Error Smears Them, and a C-Mount Lens Loses the Ends of a Long Sensor](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tdi_linescan/01_tdi_stages_defects_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tdi_linescan/01_tdi_stages_defects.png)

*↑ **TDI Line Scan and Line-Scan Lenses — Stages Reveal the Defects, a Sync Error Smears Them, and a C-Mount Lens Loses the Ends of a Long Sensor** ―― Moving material (film, steel strip, wafers) is imaged with line sensors, and on a dark line TDI adds N stages of exposure. Six new ops (`linescan`, category `linescan` of `opsoptics`): TDI SNR from the EMVA 1288 linear model (charge-domain and digital summation), the closed-form MTF of a synchronisation error and of yaw, an acquisition that transports a reflectance map past the sensor (speed error, yaw, weave, encoder sync, lens, noise), a ray-traced profile of illumination and MTF across the image height, per-column lens maps and two example lenses. On a dark cold-rolled steel strip at 40 photons per stage, the SNR measured from the temporal noise of image pairs matches equation 21 within 1.2 % at every stage count. Digital summation gains exactly √N (×8.09 at 64 stages), charge summation pays the read noise once and gains ×26.9. Detection of a faint scratch, pinholes and an inclusion goes from 0 of 3 at one stage to 3 of 3 at 64 stages with no false alarms. A speed error ε smears the image by N·ε pixels and the scan MTF follows |sinc(f N ε)|, printed first and then measured on a sine chart: largest difference 0.0035 over 45 conditions. A ±3 % speed ripple drops the local MTF to 0.64 when free-running and is fully removed by encoder sync; the cross-direction blur of yaw, |sinc(f N sin θ)|, is not (largest difference 0.0017). The same triplet optimised for a 57 mm line (f 90) and for a 2/3-inch format (f 35, a C-mount lens reused) was ray-traced: illumination splits exactly into cos⁴ × pupil × distortion (2e-16), the line-scan lens keeps 0.976 at the end of the sensor (cos⁴ alone gives 0.855; barrel distortion of −2.9 % adds ×1.111), and the C-mount lens delivers no light beyond 19.7 mm. Flat-field correction evens the brightness (0.961 to 1.000) but leaves the sine modulation unchanged (difference 0.0006), and the CNR of an inclusion at 14 mm stays at 1.52 to 1.54 with the C-mount lens against 2.49 with the line-scan lens. Nothing learned, nothing calibrated, 19 gates.*

[![EMVA 1288 の 2 枚撮り(時間雑音)で測った SNR と、式 21 を段数倍した閉形式。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tdi_linescan/02_snr_vs_stages_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tdi_linescan/02_snr_vs_stages.png)

*↑ The measurement ―― EMVA 1288 の 2 枚撮り(時間雑音)で測った SNR と、式 21 を段数倍した閉形式。 (figure labels are in Japanese; the numbers are the same)*

[![ε は搬送速度とラインレートの相対誤差。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tdi_linescan/03_sync_error_mtf_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tdi_linescan/03_sync_error_mtf.png)

*↑ ε は搬送速度とラインレートの相対誤差。*

[![web が走査軸から θ 傾くと、64 段の間に幅方向へ 64·sin θ 画素ずれる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tdi_linescan/05_yaw_cross_mtf_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tdi_linescan/05_yaw_cross_mtf.png)

*↑ web が走査軸から θ 傾くと、64 段の間に幅方向へ 64·sin θ 画素ずれる。*

[![光線追跡(射影立体角の一様格子)で数えた照度。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tdi_linescan/07_lens_relative_illumination_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tdi_linescan/07_lens_relative_illumination.png)

*↑ 光線追跡(射影立体角の一様格子)で数えた照度。*

[![同じ明るさの尺度で表示。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tdi_linescan/09_full_width_shading_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tdi_linescan/09_full_width_shading.png)

*↑ 同じ明るさの尺度で表示。*

```
py -3.11 examples/poc_tdi_linescan.py
```

Source: [examples/poc_tdi_linescan.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_tdi_linescan.py)

This run produced **10 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_tdi_linescan)

Ops used (notes): [`emva_pair_statistics`](https://furuse.work/ops/optics/sensorchar/emva_pair_statistics.html) · [`lens_field_profile`](https://furuse.work/ops/optics/linescan/lens_field_profile.html) · [`lens_shading_correct`](https://furuse.work/ops/gfx2d/isp/lens_shading_correct.html) · [`lens_shading_gain`](https://furuse.work/ops/gfx2d/isp/lens_shading_gain.html) · [`lens_system`](https://furuse.work/ops/optics/design/lens_system.html) · [`linescan_acquire`](https://furuse.work/ops/optics/linescan/linescan_acquire.html) · [`linescan_lens_columns`](https://furuse.work/ops/optics/linescan/linescan_lens_columns.html) · [`linescan_lens_example`](https://furuse.work/ops/optics/linescan/linescan_lens_example.html) · [`paraxial_trace`](https://furuse.work/ops/optics/design/paraxial_trace.html) · [`relative_illumination`](https://furuse.work/ops/optics/geometric/relative_illumination.html) · [`tdi_snr`](https://furuse.work/ops/optics/linescan/tdi_snr.html) · [`tdi_sync_mtf`](https://furuse.work/ops/optics/linescan/tdi_sync_mtf.html)

## No.2026.241 —— Industrial OCT — Layer Thickness and Hidden Defects of Paints, Coatings and Multilayer Films, Seen in Depth by the FFT of One Spectral Interferogram

[![Industrial OCT — Layer Thickness and Hidden Defects of Paints, Coatings and Multilayer Films, Seen in Depth by the FFT of One Spectral Interferogram](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/01_real_paint_bscans_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/01_real_paint_bscans.png)

*↑ **Industrial OCT — Layer Thickness and Hidden Defects of Paints, Coatings and Multilayer Films, Seen in Depth by the FFT of One Spectral Interferogram** ―― Optical coherence tomography sees the layer stack of paints, conformal coatings, adhesive layers and multilayer films, and voids and delaminations inside them, without cutting. Thirteen new ops (`octscan`, category `oct` of `opsoptics`): closed-form design numbers before measuring, interferogram simulators driven by the material table, k-linearisation, dispersion compensation and estimation, A- and B-scans, layer thickness through the group index (refusing layers that cannot be separated), boundary tracing, surface flattening and an entry point for raw spectra. Real data: public raw spectra of automotive paint panels (CC BY 4.0) processed with Fullseye ops alone give clear-coat thicknesses within 1.5 µm of the paper's OCT and 3.6 µm of the microscope, base coats within 2.3 µm of the microscope for three of four panels (one is 7.6 µm off and unresolved), a refusal under the white base coat, and an autocorrelation ghost lying flat at the clear coat's optical thickness. Synthetic: thickness through the group index within 0.04 µm of the truth, SNR, roll-off and dispersion broadening matching the closed forms, refusal below 1.4 point-spread widths, a coating-thickness map and void/delamination detection.*

[![屈折率は論文と同じ 1.56(透明層)・1.64(着色層)。表のどの行がどのファイルかは論文に無く、透明層の厚さで決めた(推定)。着色層はその対応と独立の突き合わせ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/02_real_thickness_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/02_real_thickness_table.png)

*↑ The measurement ―― 屈折率は論文と同じ 1.56(透明層)・1.64(着色層)。表のどの行がどのファイルかは論文に無く、透明層の厚さで決めた(推定)。着色層はその対応と独立の突き合わせ。 (figure labels are in Japanese; the numbers are the same)*

[![黒・濃色は透明層の下の面と着色層の下の面の 2 つの山。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/03_real_flattened_profiles_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/03_real_flattened_profiles.png)

*↑ 黒・濃色は透明層の下の面と着色層の下の面の 2 つの山。*

[![SD 840/50 nm 2048 画素(深さ範囲 2.26 mm)、SS 1310/100 nm・瞬時線幅 0.1 nm。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/06_rolloff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/06_rolloff.png)

*↑ SD 840/50 nm 2048 画素(深さ範囲 2.26 mm)、SS 1310/100 nm・瞬時線幅 0.1 nm。*

[![試料腕が参照光と同じ桁に強いと、層の上下の面どうしの干渉が 0 の近くに立つ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/09_autocorrelation_ghost_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/09_autocorrelation_ghost.png)

*↑ 試料腕が参照光と同じ桁に強いと、層の上下の面どうしの干渉が 0 の近くに立つ。*

[![横 1.2 mm、縦は光路 25〜440 µm。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/12_coat_bscan_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/12_coat_bscan.png)

*↑ 横 1.2 mm、縦は光路 25〜440 µm。*

[![試料腕に溶融石英 12 mm の分散の不一致。補償の係数 a2 を 0 から 35.6 µm² まで動かすと、PMMA / PC / PS の 3 層の界面がにじみから線に締まる(横 0.6 mm、光路 130〜380 µm)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/15_dispersion_compensation.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/15_dispersion_compensation.gif)

*↑ The animation ―― 試料腕に溶融石英 12 mm の分散の不一致。補償の係数 a2 を 0 から 35.6 µm² まで動かすと、PMMA / PC / PS の 3 層の界面がにじみから線に締まる(横 0.6 mm、光路 130〜380 µm)。*

```
py -3.11 examples/poc_industrial_oct.py
```

Source: [examples/poc_industrial_oct.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_industrial_oct.py)

This run produced **15 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_industrial_oct)

Ops used (notes): [`glass`](https://furuse.work/ops/optics/design/glass.html) · [`material_optical_constants`](https://furuse.work/ops/optics/matprop/material_optical_constants.html) · [`oct_ascan`](https://furuse.work/ops/optics/oct/oct_ascan.html) · [`oct_bscan`](https://furuse.work/ops/optics/oct/oct_bscan.html) · [`oct_bscan_boundaries`](https://furuse.work/ops/optics/oct/oct_bscan_boundaries.html) · [`oct_bscan_flatten`](https://furuse.work/ops/optics/oct/oct_bscan_flatten.html) · [`oct_bscan_simulate`](https://furuse.work/ops/optics/oct/oct_bscan_simulate.html) · [`oct_design`](https://furuse.work/ops/optics/oct/oct_design.html) · [`oct_dispersion_broadening`](https://furuse.work/ops/optics/oct/oct_dispersion_broadening.html) · [`oct_dispersion_compensate`](https://furuse.work/ops/optics/oct/oct_dispersion_compensate.html) · [`oct_dispersion_estimate`](https://furuse.work/ops/optics/oct/oct_dispersion_estimate.html) · [`oct_from_spectra`](https://furuse.work/ops/optics/oct/oct_from_spectra.html) · [`oct_interferogram`](https://furuse.work/ops/optics/oct/oct_interferogram.html) · [`oct_k_linearize`](https://furuse.work/ops/optics/oct/oct_k_linearize.html) · [`oct_layer_thickness`](https://furuse.work/ops/optics/oct/oct_layer_thickness.html)

## No.2026.255 —— Bone and Glass in Meat, Separated by Material with Two X-ray Energies (Dual-Energy and Photon-Counting X-ray)

[![Bone and Glass in Meat, Separated by Material with Two X-ray Energies (Dual-Energy and Photon-Counting X-ray)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dual_energy_xray/04_tray_single_vs_basis_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dual_energy_xray/04_tray_single_vs_basis.png)

*↑ **Bone and Glass in Meat, Separated by Material with Two X-ray Energies (Dual-Energy and Photon-Counting X-ray)** ―― A single X-ray transmission image of food measures one number per pixel, L = -ln(I/I0), so a thick piece of meat and a thin hard foreign body cannot be told apart. A detector that counts photons in two energy windows can: the shape of mu(E) differs by material, so thickness and material separate in every pixel (the Alvarez and Macovski 1976 basis decomposition). Fourteen new ops (`spectral_xray` in `opstomography`): the X-ray columns of the material table (`material_xray_attenuation` and three more, a subset of NIST SRD 126 plus a mixture rule) and ten `dualxray` ops (tube spectrum, beam quality, detector channels, projection, basis decomposition, CRLB, R value, effective Z, discrimination error rate). mu/rho matches the NIST published values (Cu at 8 keV 52.55; across the K edge 38.4 to 278.4), and the tube model's half-value layers agree with the eight IEC 61267 qualities to within 5.8 % (the model was shaped on a public spectrum calculator (MIT); the IEC values were not used to fit it). On a meat tray 25 to 60 mm thick the bone-and-glass step is 0.9 times the meat unevenness, one threshold flags 86 % of the meat, and even the high band shows two false lumps at the edge of a meat overlap, whereas the Al image from a lean-meat plus Al decomposition has 0 false lumps. A confounded pair of thick PE and thin Al gives d' = 0 in one window; the two-window error rate Phi(-d'/2) agrees with Monte Carlo to 0.004, and the Al thickness below which they cannot be separated (5 % error) is 0.125 mm in closed form and 0.126 mm measured, 0.364 mm under 40 mm of meat. The decomposition noise reaches 0.995 and 0.997 times the Cramer-Rao bound. How it breaks: decomposing without knowing 25 % charge sharing turns meat into Al, and a monochromatic approximation biases Al by -1.5 mm under 6 cm of meat; the apparent Z of a buried foreign body also moves with density (PVC at 13.9 reads as 18.7). Learning 0, calibration 0, 21 gates.*

[![W 陽極の管(Kramers の厚い陽極 + 自己吸収 + K 線 59 / 67 keV)を Al 2.5 mm で濾した光子スペクトル(半価層 2.74 mm Al、平均 42.6 keV)。CdTe 2 mm の吸収効率をかけ、堆積エ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dual_energy_xray/01_spectrum_and_windows_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dual_energy_xray/01_spectrum_and_windows.png)

*↑ The measurement ―― W 陽極の管(Kramers の厚い陽極 + 自己吸収 + K 線 59 / 67 keV)を Al 2.5 mm で濾した光子スペクトル(半価層 2.74 mm Al、平均 42.6 keV)。CdTe 2 mm の吸収効率をかけ、堆積エネルギーで 2 つの窓に分ける。 (figure labels are in Japanese; the numbers are the same)*

[![低いエネルギーでは光電効果(≈ Z³/E³)で Z の大きい材料ほど急に増え、高いエネルギーではコンプトン散乱で電子密度に揃う。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dual_energy_xray/02_mass_attenuation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dual_energy_xray/02_mass_attenuation.png)

*↑ 低いエネルギーでは光電効果(≈ Z³/E³)で Z の大きい材料ほど急に増え、高いエネルギーではコンプトン散乱で電子密度に揃う。*

[![1 枚の透過像(灰色)の上に、Al の像で浮いた画素だけ、基底の向きから読んだ見かけの Z を色で重ねた(緑 ≈ 12〜14、黄〜橙 ≈ 15〜20、赤 ≈ 25 以上)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dual_energy_xray/05_material_colour_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dual_energy_xray/05_material_colour.png)

*↑ 1 枚の透過像(灰色)の上に、Al の像で浮いた画素だけ、基底の向きから読んだ見かけの Z を色で重ねた(緑 ≈ 12〜14、黄〜橙 ≈ 15〜20、赤 ≈ 25 以上)。*

[![高い窓だけでは同じ L(1 枚の像の d′ = 0)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dual_energy_xray/08_confound_boundary_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dual_energy_xray/08_confound_boundary.png)

*↑ 高い窓だけでは同じ L(1 枚の像の d′ = 0)。*

[![肉 4 cm の下の Al の厚さの雑音(下限)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dual_energy_xray/10_threshold_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dual_energy_xray/10_threshold_sweep.png)

*↑ 肉 4 cm の下の Al の厚さの雑音(下限)。*

```
py -3.11 examples/poc_dual_energy_xray.py
```

Source: [examples/poc_dual_energy_xray.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dual_energy_xray.py)

This run produced **12 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_dual_energy_xray)

Ops used (notes): [`basis_decomposition_crlb`](https://furuse.work/ops/tomography/spectral_xray/basis_decomposition_crlb.html) · [`basis_material_decompose`](https://furuse.work/ops/tomography/spectral_xray/basis_material_decompose.html) · [`dual_energy_separability`](https://furuse.work/ops/tomography/spectral_xray/dual_energy_separability.html) · [`dual_kvp_channels`](https://furuse.work/ops/tomography/spectral_xray/dual_kvp_channels.html) · [`ellipse`](https://furuse.work/ops/annotate/shape/ellipse.html) · [`material_effective_z`](https://furuse.work/ops/tomography/spectral_xray/material_effective_z.html) · [`material_from_sellmeier`](https://furuse.work/ops/optics/matprop/material_from_sellmeier.html) · [`material_xray_attenuation`](https://furuse.work/ops/tomography/spectral_xray/material_xray_attenuation.html) · [`material_xray_constants`](https://furuse.work/ops/tomography/spectral_xray/material_xray_constants.html) · [`photon_counting_channels`](https://furuse.work/ops/tomography/spectral_xray/photon_counting_channels.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`xray_beam_quality`](https://furuse.work/ops/tomography/spectral_xray/xray_beam_quality.html) · [`xray_channel_projection`](https://furuse.work/ops/tomography/spectral_xray/xray_channel_projection.html) · [`xray_tube_spectrum`](https://furuse.work/ops/tomography/spectral_xray/xray_tube_spectrum.html)

## No.2026.271 —— Budgeting Lens Manufacturing Tolerances through MTF, Yield, and Compensator Travel

[![Budgeting Lens Manufacturing Tolerances through MTF, Yield, and Compensator Travel](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/01_sensitivity_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/01_sensitivity.png)

*↑ **Budgeting Lens Manufacturing Tolerances through MTF, Yield, and Compensator Travel** ―― A public triplet prescription receives explicit rows for curvature, thickness, refractive index, Abbe number, decentre, tilt, astigmatic surface irregularity, wedge, and group decentre. Eight new operations combine distributions, central-difference sensitivity, Monte Carlo, a Wilson 95% yield interval, multiple compensators, and assembly travel. The weak-wedge image shift agrees with f(n-1)alpha to 6e-8; the real-ray OPD RMS of one fringe of astigmatic irregularity agrees with the closed form to 1.3%. In the 16-trial CI run yield is 0.688 and becomes 1.000 with inner-gap and image-plane compensation. Uniform, normal, and truncated-normal distributions at the same plus/minus tolerance yield 0.750 / 1.000 / 1.000; tightening the leading row while loosening low-sensitivity rows gives 0.833. Learning 0, calibration 0.*

[![同じ試行から得た MTF と RMS spot。赤線は合否限界。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/02_histograms_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/02_histograms.png)

*↑ The measurement ―― 同じ試行から得た MTF と RMS spot。赤線は合否限界。 (figure labels are in Japanese; the numbers are the same)*

[![像面だけの場合と内部間隔を加えた場合を比較。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/03_compensation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/03_compensation.png)

*↑ 像面だけの場合と内部間隔を加えた場合を比較。*

[![一様・正規・±公差で切った正規分布の歩留まり。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/04_distributions_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/04_distributions.png)

*↑ 一様・正規・±公差で切った正規分布の歩留まり。*

[![線形予測と Monte-Carlo 実測を明示。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/05_rebudget_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/05_rebudget.png)

*↑ 線形予測と Monte-Carlo 実測を明示。*

[![同じ処方の基準像と、1 arcmin のくさびを入れた像。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/06_wedge_probe_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/06_wedge_probe.png)

*↑ 同じ処方の基準像と、1 arcmin のくさびを入れた像。*

[![感度首行を -tol から +tol へ掃引した点像。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/07_tolerance_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/07_tolerance_sweep.gif)

*↑ The animation ―― 感度首行を -tol から +tol へ掃引した点像。*

```
py -3.11 examples/poc_lens_tolerancing.py
```

Source: [examples/poc_lens_tolerancing.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_lens_tolerancing.py)

This run produced **7 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_lens_tolerancing)

Ops used (notes): [`chief_ray`](https://furuse.work/ops/optics/design/chief_ray.html) · [`lens_system`](https://furuse.work/ops/optics/design/lens_system.html) · [`opd_samples`](https://furuse.work/ops/optics/design/opd_samples.html) · [`ray_bundle`](https://furuse.work/ops/optics/design/ray_bundle.html) · [`tolerance_compensators`](https://furuse.work/ops/optics/tolerancing/tolerance_compensators.html) · [`tolerance_criteria`](https://furuse.work/ops/optics/tolerancing/tolerance_criteria.html) · [`tolerance_monte_carlo`](https://furuse.work/ops/optics/tolerancing/tolerance_monte_carlo.html) · [`tolerance_report`](https://furuse.work/ops/optics/tolerancing/tolerance_report.html) · [`tolerance_sensitivity`](https://furuse.work/ops/optics/tolerancing/tolerance_sensitivity.html) · [`tolerance_table`](https://furuse.work/ops/optics/tolerancing/tolerance_table.html) · [`tolerance_table_from_zmx`](https://furuse.work/ops/optics/tolerancing/tolerance_table_from_zmx.html) · [`tolerance_table_zmx`](https://furuse.work/ops/optics/tolerancing/tolerance_table_zmx.html)

## No.2026.273 —— Measuring the Same Particles in Scanning and Transmission Images — Which Is Right, 52 nm or 48 nm?

[![Measuring the Same Particles in Scanning and Transmission Images — Which Is Right, 52 nm or 48 nm?](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/02_same_specimen_sem_tem_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/02_same_specimen_sem_tem.png)

*↑ **Measuring the Same Particles in Scanning and Transmission Images — Which Is Right, 52 nm or 48 nm?** ―― One ledger of fourteen spherical and faceted particles drives both images. Area-equivalent diameter, maximum slope, watershed splitting of touching pairs, stereo height and limited-angle reconstruction are scored against the shared truth. For a 52 nm particle the scanning-image threshold is +4.16 nm, the transmission image is -0.18 nm at focus and +9.82 nm at 12000 nm defocus. The scanning bias follows the closed-form Gaussian rim width 2 sqrt(2 ln 2) sigma, while the dark transmission fringe follows sqrt(lambda defocus) within ten per cent. Material contrast is checked against published backscatter coefficients; 3-D measurements are checked against parallel-projection geometry and a full-angle reconstruction. No new operators, no learning and no calibration.*

[![Truth height only: turbo-like pseudo-colour with a nanometre colour bar in the margin.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/01_truth_height_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/01_truth_height.png)

*↑ The measurement ―― Truth height only: turbo-like pseudo-colour with a nanometre colour bar in the margin. (figure labels are in Japanese; the numbers are the same)*

[![Bright-field in-focus and under-focus output | derived diameters | absolute residual.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/03_tem_raw_overlay_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/03_tem_raw_overlay_error.png)

*↑ Bright-field in-focus and under-focus output | derived diameters | absolute residual.*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/04_diameter_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/04_diameter_bias.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/05_touching_watershed_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/05_touching_watershed.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/06_missing_wedge_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/06_missing_wedge.png)

*↑ この回の図*

[![24 greyscale bright-field frames with data bar; first and last defocus differ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/08_tem_focus_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/08_tem_focus_sweep.gif)

*↑ The animation ―― 24 greyscale bright-field frames with data bar; first and last defocus differ*

```
py -3.11 examples/poc_sem_tem_same_particle.py
```

Source: [examples/poc_sem_tem_same_particle.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_sem_tem_same_particle.py)

This run produced **8 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_sem_tem_same_particle)

Ops used (notes): [`color_bar`](https://furuse.work/ops/annotate/furniture/color_bar.html) · [`filtered_backprojection`](https://furuse.work/ops/tomography/reconstruct/filtered_backprojection.html) · [`radon_transform`](https://furuse.work/ops/tomography/forward/radon_transform.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`scale_bar`](https://furuse.work/ops/annotate/furniture/scale_bar.html) · [`sem_electron_mc`](https://furuse.work/ops/generative/sem/sem_electron_mc.html) · [`sem_image`](https://furuse.work/ops/generative/sem/sem_image.html) · [`sem_render`](https://furuse.work/ops/generative/sem/sem_render.html) · [`tem_image_weak_phase`](https://furuse.work/ops/optics/tem/tem_image_weak_phase.html) · [`tem_multislice`](https://furuse.work/ops/optics/tem/tem_multislice.html) · [`tem_projected_potential`](https://furuse.work/ops/optics/tem/tem_projected_potential.html) · [`tem_wavelength`](https://furuse.work/ops/optics/tem/tem_wavelength.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`watersheds_marker`](https://furuse.work/ops/segmentation/watershed/watersheds_marker.html)

## No.2026.274 —— Indirect and Direct Time of Flight on One 3-D Scene — Multipath, Mixed Pixels, Pile-up and Volume Error

[![Indirect and Direct Time of Flight on One 3-D Scene — Multipath, Mixed Pixels, Pile-up and Volume Error](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/01_scene_viewer_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/01_scene_viewer.png)

*↑ **Indirect and Direct Time of Flight on One 3-D Scene — Multipath, Mixed Pixels, Pile-up and Volume Error** ―― The same 320 by 240 scene is shown as IR amplitude, colour-coded distance over 1.5–6.0 m, and a point cloud. The amplitude-distribution W1 distance between synthesis and measurement is 0.145 (gate 0.594). The remaining figures add physical effects one at a time; compare amplitude with range noise (log slope -0.878 in measurements and -1.027 in synthesis); reproduce wall-junction bowing (-551 mm measured and +75 mm synthetic, with matching signs after aligning profile direction); separate transparent-pane returns 1.35 m apart; expose mixed pixels around a thin pole; show direct time-of-flight histograms and decoded depth; and tabulate three box-volume errors (+0.16, +0.47 and +0.29 percent). The final animation is a 48-frame, 576 by 432, 8 fps light front moving from 1.4 to 6.2 m. Real frames are not redistributed: only curves and aggregate measurements are shown. No new ops, no learning, no calibration, 13 gates.*

[![全パネル同じ距離範囲。暗部の荒れと隅の湾曲が順に現れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/02_effects_added_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/02_effects_added.png)

*↑ The measurement ―― 全パネル同じ距離範囲。暗部の荒れと隅の湾曲が順に現れる。 (figure labels are in Japanese; the numbers are the same)*

[![対数傾きは実測 -0.878、合成 -1.027。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/03_noise_vs_amplitude_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/03_noise_vs_amplitude.png)

*↑ 対数傾きは実測 -0.878、合成 -1.027。*

[![実測は曲線だけを掲載し、フレームを再配布しない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/04_corner_bow_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/04_corner_bow.png)

*↑ 実測は曲線だけを掲載し、フレームを再配布しない。*

[![手描きマスクではなく3×3サブ光線のフェーザ和。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/06_pole_flying_pixels_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/06_pole_flying_pixels.png)

*↑ 手描きマスクではなく3×3サブ光線のフェーザ和。*

[![強い画素では最初の光子が早い側へ偏る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/07_dtof_histograms_depth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/07_dtof_histograms_depth.png)

*↑ 強い画素では最初の光子が早い側へ偏る。*

[![48枚、576×432。各時刻を99パーセンタイル・γ=0.5で階調化。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/09_dtof_light_front.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/09_dtof_light_front.gif)

*↑ The animation ―― 48枚、576×432。各時刻を99パーセンタイル・γ=0.5で階調化。*

```
py -3.11 examples/poc_tof_camera.py
```

Source: [examples/poc_tof_camera.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_tof_camera.py)

This run produced **9 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_tof_camera)

Ops used (notes): [`bilateral_filter_depth`](https://furuse.work/ops/3d/depth_denoise/bilateral_filter_depth.html) · [`depth_to_points`](https://furuse.work/ops/3d/transform/depth_to_points.html) · [`dtof_cube_depth`](https://furuse.work/ops/photon/dtof/dtof_cube_depth.html) · [`dtof_cube_simulate`](https://furuse.work/ops/photon/dtof/dtof_cube_simulate.html) · [`points_render`](https://furuse.work/ops/3d/render/points_render.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html)




---

**This museum was built together with Claude Code.** I set the questions and the direction; Claude Code did the implementation, the sweeps, the control groups and the adversarial checks. That division of labour is what made it possible to run 53 PoCs and collect their figures in two days. If you want to try it, this invitation link gives you a **one-week free trial**: [claude.ai/referral/0sqPw8E_lw](https://claude.ai/referral/0sqPw8E_lw)

If even one exhibit was worth your time, a **like or a stock** helps: the reactions decide which wing grows next, so tell me in the comments which measurement from your own field you would want to see. And if you swapped in real data and the cliff moved, that is the story I most want to hear.
