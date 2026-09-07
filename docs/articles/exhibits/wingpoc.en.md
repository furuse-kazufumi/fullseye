<!-- generated -->

### The Industrial Inspection Wing — A Passing Number and a Failing Number Can Coexist

Numbers on an inspection line decide pass or fail, so there is a strong pull toward collapsing them into a single figure. The ten exhibits in this room show what disappears the moment you do: a pooled ROC that hides one defect class's blind spot in woven fabric, veiling glare that leaves the MTF passing while the black level fails, a barcode decoder that looks better by read rate alone because it never says 'unreadable'.

Every ground truth is planted: a closed-form periodic background, the laser-profile h(x), the analytic 1-D heat-conduction solution, closed-form bearing defect frequencies. That is what lets each exhibit measure 'where detection stops working' instead of 'detection worked', without fitting the threshold afterwards.

The other shared feature is that failure arrives as a cliff, not a slope: 15 versus 16 degrees of tilt, a 25-second versus a 4-second fitting window, ΔT of 1.6 K. Most of those positions can be predicted from geometry or physics first, and wherever they could be, the prediction is checked against the measurement.

## 1. Defects Buried in a Periodic Background — What a Pooled ROC Hides

[![Defects Buried in a Periodic Background — What a Pooled ROC Hides](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fabric_defect/04_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fabric_defect/04_scene.png)

*↑ **Defects Buried in a Periodic Background — What a Pooled ROC Hides** ―― Three defect classes (thread break, stain, dim patch) buried in a weave of period 8 px, with the detector's score map and per-class ROC curves side by side. The everyday recipe 'notch out the grid, remove low frequencies' pools to an AUC of 0.8113 and looks like a pass, but the dim-patch class alone scores 0.4746, worse than chance. The one line that removes low frequencies was deleting the defect along with the lighting; drop it and the class recovers to 0.9998.*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fabric_defect/01_auc_by_type_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fabric_defect/01_auc_by_type.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_fabric_defect.py
```

Source: [examples/poc_fabric_defect.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_fabric_defect.py)



## 2. Weld Bead From a Laser-Triangulation Profile — The Sin of Writing 0 Where Nothing Was Measured

[![Weld Bead From a Laser-Triangulation Profile — The Sin of Writing 0 Where Nothing Was Measured](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_profile/01_laser_images_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_profile/01_laser_images.png)

*↑ **Weld Bead From a Laser-Triangulation Profile — The Sin of Writing 0 Where Nothing Was Measured** ―― The profile h(x) recovered from the row position of a single laser line, with reinforcement height, width and undercut read off it. The centroid beats the null (integer argmax per column) by 9.3x, and with zero noise the log-parabola is exact to machine precision, 12 orders better than a plain parabola; at 1 % noise the two are 0.00272 versus 0.00260 mm, indistinguishable. Five spatter points break all three estimators together to 0.11 mm (40x); what matters is not refinement but which peak you pick.*

[![0 で埋めた線は影の区間で h=0 に張り付き、左のアンダーカットが消えて偽のつま先ができる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_profile/02_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_profile/02_profile.png)

*↑ The measurement ―― 0 で埋めた線は影の区間で h=0 に張り付き、左のアンダーカットが消えて偽のつま先ができる。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_weld_bead_profile.py
```

Source: [examples/poc_weld_bead_profile.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_weld_bead_profile.py)

Ops used (notes): [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`median`](https://furuse.work/ops/2d/rank/median.html)

## 3. Concrete Crack Width Is Thinner Than a Pixel — Counting Width Versus Integrating Width

[![Concrete Crack Width Is Thinner Than a Pixel — Counting Width Versus Integrating Width](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width/02_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width/02_scene.png)

*↑ **Concrete Crack Width Is Thinner Than a Pixel — Counting Width Versus Integrating Width** ―― Cracks from 0.05 to 2.0 mm wide in a field where 1 px = 0.20 mm, measured by thresholding-and-counting and by integrating the intensity deficit across the crack. Thresholding returns nothing at or below 0.20 mm and reports 0.200 mm for all four true widths between 0.25 and 0.40 mm. Integration tracks continuously down to 0.05 mm (0.25 px), but curved illumination adds a +0.1741 mm offset under a first-order baseline (+0.0062 mm with second order).*

[![2 値化の 2 本は階段。0.20 mm(1 px)以下ではマスクが空になり 0(= 未検出)へ落ちる。積分法は 0.05 mm (0.25 px)まで直線 y=x に乗る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width/01_width_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width/01_width_sweep.png)

*↑ The measurement ―― 2 値化の 2 本は階段。0.20 mm(1 px)以下ではマスクが空になり 0(= 未検出)へ落ちる。積分法は 0.05 mm (0.25 px)まで直線 y=x に乗る。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_crack_width.py
```

Source: [examples/poc_crack_width.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_crack_width.py)

Ops used (notes): [`distance_transform`](https://furuse.work/ops/2d/region/distance_transform.html) · [`sk_medial`](https://furuse.work/ops/2d/region/sk_medial.html) · [`skeleton`](https://furuse.work/ops/2d/region/skeleton.html) · [`thinning`](https://furuse.work/ops/2d/region/thinning.html) · [`vol_distance_transform`](https://furuse.work/ops/3d/medial/vol_distance_transform.html)

## 4. Veiling Glare Breaks Contrast Measurement — MTF Passes While Black Level Fails

[![Veiling Glare Breaks Contrast Measurement — MTF Passes While Black Level Fails](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_veiling_glare/04_glare_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_veiling_glare/04_glare_scene.png)

*↑ **Veiling Glare Breaks Contrast Measurement — MTF Passes While Black Level Fails** ―― A PSF whose core stays sharp while only its tail is made heavier, with the slanted-edge MTF and the black level of a dark square measured on the same image. Raising the tail fraction from 0 to 0.20 moves MTF50 from 0.2347 to 0.2249 cyc/px (-4.2 %, still passing) while the black level goes from 0.0 to 15.7 % (failing). A ±16 px measurement window captures only 6 % of the tail's energy; a glare figure means nothing until the measurement extent is declared.*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_veiling_glare/01_verdict_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_veiling_glare/01_verdict.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_veiling_glare.py
```

Source: [examples/poc_veiling_glare.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_veiling_glare.py)

Ops used (notes): [`airy_pattern`](https://furuse.work/ops/optics/wave/airy_pattern.html) · [`mtf_diffraction`](https://furuse.work/ops/optics/imaging/mtf_diffraction.html) · [`psf_to_mtf`](https://furuse.work/ops/optics/imaging/psf_to_mtf.html)

## 5. Can Display-Inspection Moire Be Told From Real Non-Uniformity?

[![Can Display-Inspection Moire Be Told From Real Non-Uniformity?](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_moire_screen/04_moire_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_moire_screen/04_moire_scene.png)

*↑ **Can Display-Inspection Moire Be Told From Real Non-Uniformity?** ―― Moire from the interference of the display's stripes with the camera's pixel grid, overlaid on genuine luminance non-uniformity in one image. At a smoothing σ of 8 px the total error is +0.9 %, made of +8.3 % moire leakage cancelling -7.4 % attenuation of the real defect. At k = 0.67 the fundamental beat looks safe, yet the third harmonic lands in the defect band and the leakage reaches +202.6 % of the true value.*

[![σ≈8 px で漏れと減衰が釣り合う。合計だけ見ると「良い測り方」に見える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_moire_screen/01_failure_split_plot_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_moire_screen/01_failure_split_plot.png)

*↑ The measurement ―― σ≈8 px で漏れと減衰が釣り合う。合計だけ見ると「良い測り方」に見える。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_moire_screen.py
```

Source: [examples/poc_moire_screen.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_moire_screen.py)

Ops used (notes): [`background_flatten`](https://furuse.work/ops/3d/surface_fit/background_flatten.html) · [`fft_image`](https://furuse.work/ops/2d/frequency/fft_image.html) · [`gauss_image`](https://furuse.work/ops/2d/smoothing/gauss_image.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html)

## 6. Rolling-Bearing Diagnosis — How Deep in Noise Can It Still Be Caught?

[![Rolling-Bearing Diagnosis — How Deep in Noise Can It Still Be Caught?](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bearing_diagnosis/01_envelope_vs_raw_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bearing_diagnosis/01_envelope_vs_raw.png)

*↑ **Rolling-Bearing Diagnosis — How Deep in Noise Can It Still Be Caught?** ―― An impulse train synthesised at the closed-form defect frequency (BPFO 104.556 Hz), sunk into noise, with detection rates of the raw spectrum and the envelope spectrum side by side. The worst SNR at which 10 of 10 seeds still detect is -0.9 dB for the raw spectrum and -18.4 dB for the envelope, a 17.5 dB gap. But a record with no defect at all still produces a global prominence of 43; had the threshold not been set from the null recording, this PoC would have been its own false positive.*

[![どちらも最悪条件では 0 に落ちる。包絡線は万能ではなく、崖が悪い SNR 側へ動くだけ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bearing_diagnosis/02_detection_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bearing_diagnosis/02_detection_sweep.png)

*↑ The measurement ―― どちらも最悪条件では 0 に落ちる。包絡線は万能ではなく、崖が悪い SNR 側へ動くだけ。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_bearing_diagnosis.py
```

Source: [examples/poc_bearing_diagnosis.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bearing_diagnosis.py)

Ops used (notes): [`bearing_defect_frequencies`](https://furuse.work/ops/acoustics/bearing/bearing_defect_frequencies.html) · [`envelope_spectrum`](https://furuse.work/ops/acoustics/bearing/envelope_spectrum.html) · [`spectral_kurtosis`](https://furuse.work/ops/acoustics/bearing/spectral_kurtosis.html) · [`synthesize_bearing_signal`](https://furuse.work/ops/acoustics/synthesis/synthesize_bearing_signal.html)

## 7. Depth of a Subsurface Defect by Pulsed Thermography

[![Depth of a Subsurface Defect by Pulsed Thermography](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/02_depth_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/02_depth_map.png)

*↑ **Depth of a Subsurface Defect by Pulsed Thermography** ―― Surface temperature after a flash, generated from the exact 1-D heat-conduction solution, with delamination depth estimated from the image sequence. Where the diameter is at least four times the depth the estimate lands within a few percent; at 0.5 mm deep and 2 mm across it is off by +627 %. The cause is not lateral diffusion but the fitting window: shortening it from 25 s to 4 s brings that case back to -9 %.*

[![右下三角(直径が深さの 4 倍以上)は数 %。左上は横拡散で壊れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/01_depth_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/01_depth_table.png)

*↑ The measurement ―― 右下三角(直径が深さの 4 倍以上)は数 %。左上は横拡散で壊れる。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_thermography_ndt.py
```

Source: [examples/poc_thermography_ndt.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_thermography_ndt.py)



## 8. How Much Camera Thermal Drift Costs a Dimensional Measurement

[![How Much Camera Thermal Drift Costs a Dimensional Measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_drift_metrology/04_error_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_drift_metrology/04_error_maps.png)

*↑ **How Much Camera Thermal Drift Costs a Dimensional Measurement** ―― A 40 mm square measured by a camera whose focal length, mount and principal point drift with temperature ΔT, the error split into a + b·R in image radius. At ΔT = 15 K the constant term is +224.5 ppm (the single-cause control gives +225.3 ppm). Drift rises above the noise floor (23 ppm for a 25-frame average) only from ΔT = 1.6 K; below that, the honest report is that no temperature effect is visible.*

[![焦点距離ドリフトは R に依らない。主点ドリフトは R に比例(歪みを外す中心がずれるため)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_drift_metrology/01_separate_drifts_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_drift_metrology/01_separate_drifts.png)

*↑ The measurement ―― 焦点距離ドリフトは R に依らない。主点ドリフトは R に比例(歪みを外す中心がずれるため)。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_thermal_drift_metrology.py
```

Source: [examples/poc_thermal_drift_metrology.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_thermal_drift_metrology.py)



## 9. Where a 1-D Barcode Stops Reading — Counting Misreads and Unreadables Separately

[![Where a 1-D Barcode Stops Reading — Counting Misreads and Unreadables Separately](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_barcode_1d/01_misread_split_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_barcode_1d/01_misread_split.png)

*↑ **Where a 1-D Barcode Stops Reading — Counting Misreads and Unreadables Separately** ―― A home-made simple code (not a real standard) damaged four ways, with success, misread and unreadable counted as three separate outcomes. Over the 384 images past the onset of damage, the strict decoder that checks run structure misreads 7.3 %, while the lenient decoder that always returns nine digits misreads 46.1 % — and has the higher success rate (47.7 % versus 40.1 %). The tilt cliff is pure geometry (predicted 15.95 degrees) and lands between 15 and 16 degrees.*

[![小さい汚れは行が「読めてしまう」ので誤った票を投じる。大きい汚れは棄権するので多数決が効く。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_barcode_1d/02_smudge_nonmonotone_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_barcode_1d/02_smudge_nonmonotone.png)

*↑ The measurement ―― 小さい汚れは行が「読めてしまう」ので誤った票を投じる。大きい汚れは棄権するので多数決が効く。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_barcode_1d.py
```

Source: [examples/poc_barcode_1d.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_barcode_1d.py)

Ops used (notes): [`decode_barcode`](https://furuse.work/ops/2d/barcode/decode_barcode.html) · [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`vol_edge_probe`](https://furuse.work/ops/3d/probe/vol_edge_probe.html)

## 10. Reading a Binary Matrix Code — Geometry Always Dies First

[![Reading a Binary Matrix Code — Geometry Always Dies First](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_matrix_code_reading/01_symbol_and_errors_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_matrix_code_reading/01_symbol_and_errors.png)

*↑ **Reading a Binary Matrix Code — Geometry Always Dies First** ―― A code with QR-style layout and random data bits (no error correction), damaged by blur, tilt and occlusion, with the raw bit error rate counted directly. The nulls sit at chance (0.526 / 0.507) while the reader scores 0.0000. Cliffs: 78 degrees of tilt, two modules of finder-pattern occlusion; run beside the condition that receives the true homography, localisation is always the stage that fails first.*

[![自力検出の線は sigma/m 0.50 を最後に途切れる(0.60 では位置検出パターンが見つからない)。標本化はそこでまだ BER 0.07 で読めている。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_matrix_code_reading/02_blur_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_matrix_code_reading/02_blur_cliff.png)

*↑ The measurement ―― 自力検出の線は sigma/m 0.50 を最後に途切れる(0.60 では位置検出パターンが見つからない)。標本化はそこでまだ BER 0.07 で読めている。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_matrix_code_reading.py
```

Source: [examples/poc_matrix_code_reading.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_matrix_code_reading.py)

Ops used (notes): [`adaptive_gauss_thresh`](https://furuse.work/ops/2d/segmentation/adaptive_gauss_thresh.html) · [`corner_response`](https://furuse.work/ops/2d/edges/corner_response.html) · [`illuminate`](https://furuse.work/ops/2d/gray/illuminate.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`sk_sauvola`](https://furuse.work/ops/2d/segmentation/sk_sauvola.html)

## 11. Porosity in Weld Radiographs — Closing With the Share of Images Misgraded by One Class

[![Porosity in Weld Radiographs — Closing With the Share of Images Misgraded by One Class](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/01_scene_radiograph_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/01_scene_radiograph.png)

*↑ **Porosity in Weld Radiographs — Closing With the Share of Images Misgraded by One Class** ―― A radiograph drawn in closed form with Beer–Lambert: 10 mm plate, arc-shaped reinforcement, spherical pores, plus scatter, unsharpness and film grain. The fixed-threshold baseline counts the weld toe as pores (124 blobs, total area 15.19 mm² against 7.93 true). The detection cliff is predictable from CNR = 16.12·d²: Rose's CNR = 4 misses (0.50 mm), while the prediction that includes smoothing and the 3 px minimum area gives 0.58 mm against 0.57 mm measured. The 9 px window cap of the background-estimation op (rectangular opening) becomes a cliff: detection drops below 50 % from 2.0 mm and reaches 0 % at 2.5 mm — choosing the op chooses the measuring range. Scatter at SPR = 1 shrinks the volumetric diameter by (1+SPR)^(-1/3): -22.6 % measured against -20.6 % predicted. Images misgraded by one class: 90 % for the baseline, 23 % with the volumetric diameter.*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/02_map_detections_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/02_map_detections.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_weld_radiograph_porosity.py
```

Source: [examples/poc_weld_radiograph_porosity.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_weld_radiograph_porosity.py)

Ops used (notes): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`blob_select`](https://furuse.work/ops/blob/select/blob_select.html) · [`estimate_noise`](https://furuse.work/ops/2d/features/estimate_noise.html) · [`gauss_image`](https://furuse.work/ops/2d/smoothing/gauss_image.html) · [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`gray_opening_rect`](https://furuse.work/ops/2d/morphology/gray_opening_rect.html) · [`identity`](https://furuse.work/ops/2d/misc/identity.html) · [`log_image`](https://furuse.work/ops/2d/arithmetic/log_image.html) · [`measure_pairs`](https://furuse.work/ops/measure1d/caliper/measure_pairs.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`median_rect`](https://furuse.work/ops/2d/rank/median_rect.html) · [`sk_rolling_ball`](https://furuse.work/ops/2d/smoothing/sk_rolling_ball.html) · [`xsitk_grayscale_grindpeak`](https://furuse.work/ops/2d/extra/xsitk_grayscale_grindpeak.html)

## 12. Power loss from solar-cell EL images — dark is not the same as inactive

[![Power loss from solar-cell EL images — dark is not the same as inactive](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_el_inspection/01_zero_point_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_el_inspection/01_zero_point_map.png)

*↑ **Power loss from solar-cell EL images — dark is not the same as inactive** ―― A crystalline-silicon cell (100 fingers, 3 busbars, 70 grains) is rendered in closed form as an EL image with two electrically isolated regions (true inactive area 4.77 %), 5 cracks and 8 finger interruptions, then imaged through cos^4 vignetting and photon noise. The zero-point global threshold reports a dark-pixel fraction of 21.7 % as the inactive area, but 42 % of those pixels are fingers and busbars and 33 % are grains and vignetting; only 20 % are truly inactive. Dividing out the grid with row/column profiles and gating each defect type separately gives 4.61 % (-0.15 points), crack recall 0.88–1.00 and 8/8 interruptions. Because sk_frangi normalises by the per-image maximum, a calibration line only fixes the scale if it is the strongest ridge in the image (a line like the real cracks responds 0.69, a 3 px black line 1.00); without calibration the defect-free cell produces 147 px of false cracks. From grain contrast c=0.24 false cracks and swallowed interruption bands start together, and the crack-width cliff at 1.25 px follows the linear width-times-depth rule (predicted 1.38 px).*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_el_inspection/02_by_type_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_el_inspection/02_by_type.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_solar_el_inspection.py
```

Source: [examples/poc_solar_el_inspection.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_solar_el_inspection.py)

Ops used (notes): [`aug_vignette`](https://furuse.work/ops/2d/augmentation/aug_vignette.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_select`](https://furuse.work/ops/blob/select/blob_select.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`gray_closing`](https://furuse.work/ops/2d/morphology/gray_closing.html) · [`hysteresis_threshold`](https://furuse.work/ops/2d/segmentation/hysteresis_threshold.html) · [`lines_gauss`](https://furuse.work/ops/2d/contour/lines_gauss.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`sk_frangi`](https://furuse.work/ops/2d/texture/sk_frangi.html) · [`sk_skeleton`](https://furuse.work/ops/2d/region/sk_skeleton.html) · [`total_length`](https://furuse.work/ops/2d/features/total_length.html) · [`vignette`](https://furuse.work/ops/gfx2d/post/vignette.html)

## 13. Solder fillet AOI — three ring lights are a 3-level tilt quantiser, and 70 % of the fillet height sits in the dark

[![Solder fillet AOI — three ring lights are a 3-level tilt quantiser, and 70 % of the fillet height sits in the dark](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solder_fillet_aoi/02_scene_grid_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solder_fillet_aoi/02_scene_grid.png)

*↑ **Solder fillet AOI — three ring lights are a 3-level tilt quantiser, and 70 % of the fillet height sits in the dark** ―― A 1608 chip's pads and terminations carry circular-arc fillets fixed by contact angle and cross-section area; three ring lights at different elevations (red 30-40°, green 15-30°, blue 0-15° of surface tilt) are integrated over a GGX lobe to synthesise the AOI image, and joints are graded good / insufficient / bridge / tombstone. With an 18° contact angle the concave arc rises to 72° at the wall, so even the lowest ring sees only 28.8 % of the height (predicted): naively integrating the band tilts recovers 0.284 of the true height. Extrapolating the arc to the wall from the positions where the colour changes lands at +1.7 % ± 5.3 % for free arcs, but once extra solder pins the toe at the pad edge it drifts to -42.3 %. A 0.16 mm placement offset steepens the toe past 30°, the green band vanishes and a good joint is called insufficient although its true height has risen (predicted 0.16 mm; the truth only fails at 0.28 mm). Surface roughness, against expectation, does not move the dark edge; it breaks at roughness 0.5 together with the loss of the red band and at 0.6 the whole fillet drops below the dark threshold. The zero point (Lab distance of the pad mean colour) is 100 % right under reference conditions yet flags 56 % of good joints and 68 % of bridges once offset, roughness and lighting vary — no discrimination — while the arc-based grading scores good 98 % / insufficient 98 % / bridge 100 % / tombstone 88 %, the misses all being lifts of 8.7-11.0°.*

[![鏡面なら窓の端が階段になる。傾き 40° を超えるとどのリングも届かない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solder_fillet_aoi/01_ring_lut_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solder_fillet_aoi/01_ring_lut.png)

*↑ The measurement ―― 鏡面なら窓の端が階段になる。傾き 40° を超えるとどのリングも届かない。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_solder_fillet_aoi.py
```

Source: [examples/poc_solder_fillet_aoi.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_solder_fillet_aoi.py)

Ops used (notes): [`access_channel`](https://furuse.work/ops/2d/color/access_channel.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_select_largest`](https://furuse.work/ops/blob/select/blob_select_largest.html) · [`brdf_microfacet`](https://furuse.work/ops/specular/reflectance/brdf_microfacet.html) · [`illumination_design`](https://furuse.work/ops/optics/illumination/illumination_design.html) · [`intensity`](https://furuse.work/ops/2d/features/intensity.html) · [`rgb_to_lab`](https://furuse.work/ops/imgmetrics/colorspace/rgb_to_lab.html) · [`trans_from_rgb`](https://furuse.work/ops/2d/color/trans_from_rgb.html)

## 14. Sorting mixed waste by material — what a preprocessor can erase is decided by algebra

[![Sorting mixed waste by material — what a preprocessor can erase is decided by algebra](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_recycling_sorting/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_recycling_sorting/01_scene.png)

*↑ **Sorting mixed waste by material — what a preprocessor can erase is decided by algebra** ―― Fragments on a belt carry material, dirt, wetness, tilt and occlusion in known amounts, imaged in 64 SWIR bands. Per-fragment degradation is closed form, s(l)=g*R(l)*exp(-w*A_w(l))+(a*u(l)+c), so invariance can be predicted before measuring: the spectral angle is invariant to the multiplicative g (0.995 to 0.990 as dirt goes 0 to 0.8; 0.993 at 70 degrees of tilt), and a second derivative annihilates the linear baseline (raw SAM falls 0.995 to 0.827 under an additive baseline while the derivative stays at 0.995 at every level). Two predictions failed: wetness is largely removed by the second derivative (0.818 against 0.282 for raw SAM) because a second derivative weights Gaussian bands by 1/sigma^2 ((43/70)^2 = 0.37), and continuum removal beats raw SAM while the baseline is weak (0.983 vs 0.865) but loses once it is strong (0.736 vs 0.827). Featureless metal vanishes under differentiation (recall 0.06) and a flatness gate restores it to 0.98.*

[![PP と PE は骨格が同じ(-CH2-)なのでわざと似せてある。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_recycling_sorting/02_library_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_recycling_sorting/02_library.png)

*↑ The measurement ―― PP と PE は骨格が同じ(-CH2-)なのでわざと似せてある。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_recycling_sorting.py
```

Source: [examples/poc_recycling_sorting.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_recycling_sorting.py)

Ops used (notes): [`overlay_labels`](https://furuse.work/ops/annotate/overlay/overlay_labels.html)

## 15. Fusing thermal, vibration and geometry for machine health — three sensors, one fact

[![Fusing thermal, vibration and geometry for machine health — three sensors, one fact](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_machine_condition_fusion/01_scene_machine_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_machine_condition_fusion/01_scene_machine.png)

*↑ **Fusing thermal, vibration and geometry for machine health — three sensors, one fact** ―― Six states of a rotating machine (healthy, misalignment, unbalance, outer-race spall, poor lubrication, looseness) are built from closed-form bearing defect frequencies, the exact steady fin-equation solution for the casing temperature, and a planted shaft offset, then classified from three sensors. Fused accuracy is 100.0 % — but vibration alone is also 100.0 %: thermal and geometry add nothing. Misalignment reaches 100.0 % from any single sensor (correlations with the true severity 0.843 / 0.841 / 0.978 — three faces of one number), while thermal alone can never separate healthy, unbalance and looseness (48/48 confusions inside that trio) and dropping vibration takes them from 100.0 % to 50.0 % / 31.2 %. Fusion only earns its keep once vibration breaks: at noise sigma 1.6 it lifts 45.8 % to 78.1 %. The cliffs were predicted on single features: the 0.5X order bin needs T > 2/f_r = 68.6 ms (measured d' 2.45 -> 4.32 across the 50 -> 70 ms step), the thermal spread dies past the 66 mm half-diameter (d' 0.00 at 96 mm pitch). The sideband prediction 1/T < FTF = 86.1 ms was wrong; the peak-reading window condition 1.2/FTF = 103 ms is the right one.*

[![軸受外輪傷は狭く熱く、潤滑不良は広く熱い。最高温度だけ見ると同じ顔になる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_machine_condition_fusion/02_thermal_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_machine_condition_fusion/02_thermal_maps.png)

*↑ The measurement ―― 軸受外輪傷は狭く熱く、潤滑不良は広く熱い。最高温度だけ見ると同じ顔になる。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_machine_condition_fusion.py
```

Source: [examples/poc_machine_condition_fusion.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_machine_condition_fusion.py)

Ops used (notes): [`angle_between_lines`](https://furuse.work/ops/3d/geometry/angle_between_lines.html) · [`arrow`](https://furuse.work/ops/annotate/pointer/arrow.html) · [`bearing_defect_frequencies`](https://furuse.work/ops/acoustics/bearing/bearing_defect_frequencies.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`distance_point_line`](https://furuse.work/ops/3d/geometry/distance_point_line.html) · [`ellipse`](https://furuse.work/ops/annotate/shape/ellipse.html) · [`fuse`](https://furuse.work/ops/3d/tsdf_fusion/fuse.html) · [`jitter`](https://furuse.work/ops/3d/augment/jitter.html) · [`mat_pinv`](https://furuse.work/ops/math/linalg/mat_pinv.html) · [`rounded_rect`](https://furuse.work/ops/annotate/shape/rounded_rect.html) · [`stat_correlation`](https://furuse.work/ops/math/stats/stat_correlation.html) · [`synthesize_bearing_signal`](https://furuse.work/ops/acoustics/synthesis/synthesize_bearing_signal.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html)

### The Dimensional and Shape Metrology Wing — Keep Bias and Scatter Apart

To state that a part is 50.50 pixels wide, you need bias (the part that always shifts the same way) and scatter (the part that changes from shot to shot) as two separate numbers. Pass/fail is decided by bias; repeatability by scatter. Merge them into one 'error' and you no longer know which countermeasure to take.

The ten exhibits here hold their ground truth in closed form or analytic rendering — a signed-distance-function part, an involute gear, a roughness surface synthesised from a prescribed PSD, a white-light interferometry stack, analytic speckle, Frocht's stress field, a perfectly symmetric synthetic skull — and then score caliper, correlation and phase readings against it.

The recurring finding is that a number without its definition cannot be compared: crack widths that differ by 0.20 mm between two distance-transform conventions, a D50 that differs by 1.66x between number- and area-weighting, an Sz that never plateaus as the evaluation area grows, an orientation index that moves 5 % depending on whether the truth is counted by fibre or by length. These are not instrument errors; they are questions of what you are comparing against.

## 16. Dimensional Inspection of a Machined Part — Bias and Scatter as Two Numbers

[![Dimensional Inspection of a Machined Part — Bias and Scatter as Two Numbers](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dimensional_inspection/01_slot_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dimensional_inspection/01_slot_bias.png)

*↑ **Dimensional Inspection of a Machined Part — Bias and Scatter as Two Numbers** ―― A part defined by a signed distance function (slot width 50.50 px, 1 px = 12.5 µm), imaged through a known PSF and noise and measured by four caliper systems. Otsu's integer width (the null) has an RMS error of 0.464 px = 5.8 µm; the buried 1-D measuring implementation is biased by -0.0113 px = -0.14 µm, 41x better. Once the edge spacing drops below 3.09 PSF widths the width comes out systematically large, and the API keeps returning success.*

[![偏りはどちらも正(対が互いを押し広げる)。符号が一定なので繰り返し測っても消えない。下端 -4 は表示の打ち切り(|偏り| < 1e-4 px)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dimensional_inspection/02_blur_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dimensional_inspection/02_blur_cliff.png)

*↑ The measurement ―― 偏りはどちらも正(対が互いを押し広げる)。符号が一定なので繰り返し測っても消えない。下端 -4 は表示の打ち切り(|偏り| < 1e-4 px)。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_dimensional_inspection.py
```

Source: [examples/poc_dimensional_inspection.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dimensional_inspection.py)

Ops used (notes): [`add_metrology_object_circle_measure`](https://furuse.work/ops/measure1d/model/add_metrology_object_circle_measure.html) · [`add_metrology_object_ellipse_measure`](https://furuse.work/ops/measure1d/model/add_metrology_object_ellipse_measure.html) · [`add_metrology_object_generic`](https://furuse.work/ops/measure1d/model/add_metrology_object_generic.html) · [`add_metrology_object_line_measure`](https://furuse.work/ops/measure1d/model/add_metrology_object_line_measure.html) · [`add_metrology_object_rectangle2_measure`](https://furuse.work/ops/measure1d/model/add_metrology_object_rectangle2_measure.html) · [`align_metrology_model`](https://furuse.work/ops/measure1d/apply/align_metrology_model.html) · [`apply_metrology_model`](https://furuse.work/ops/measure1d/apply/apply_metrology_model.html) · [`create_metrology_model`](https://furuse.work/ops/measure1d/model/create_metrology_model.html) · [`edge_points`](https://furuse.work/ops/3d/edges/edge_points.html) · [`ellipse`](https://furuse.work/ops/annotate/shape/ellipse.html) · [`fuzzy_measure_pairing`](https://furuse.work/ops/measure1d/caliper/fuzzy_measure_pairing.html) · [`gen_measure_arc`](https://furuse.work/ops/measure1d/caliper/gen_measure_arc.html) · [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`m1_measure_pairs`](https://furuse.work/ops/2d/measure1d/m1_measure_pairs.html) · [`m1_measure_pos`](https://furuse.work/ops/2d/measure1d/m1_measure_pos.html) · [`measure_pairs`](https://furuse.work/ops/measure1d/caliper/measure_pairs.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`translate_measure`](https://furuse.work/ops/measure1d/caliper/translate_measure.html)

## 17. Gear Tooth Metrology — Eccentricity Is Order 1, Teeth Are Order z

[![Gear Tooth Metrology — Eccentricity Is Order 1, Teeth Are Order z](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/01_scene.png)

*↑ **Gear Tooth Metrology — Eccentricity Is Order 1, Teeth Are Order z** ―― Eccentricity and tooth profile read from a gear drawn with the closed-form involute. The null's least-squares circle has a diameter of 47.278 mm, which is neither the pitch (48), tip (52) nor root (43) circle. One missing tooth turns an eccentricity of 0.050 mm into 0.1285 mm (+157 %); the traditional method of one sample per tooth returns 0.0501 mm (+0.2 %).*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/02_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/02_profile.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_gear_tooth_metrology.py
```

Source: [examples/poc_gear_tooth_metrology.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_gear_tooth_metrology.py)

Ops used (notes): [`blob_boundaries`](https://furuse.work/ops/blob/extract/blob_boundaries.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`blob_region`](https://furuse.work/ops/blob/extract/blob_region.html) · [`blob_select_largest`](https://furuse.work/ops/blob/select/blob_select_largest.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`polar_trans_image`](https://furuse.work/ops/2d/geometry/polar_trans_image.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html)

## 18. How Far Sa / Sq / Sz Survive Sampling and Cutoff

[![How Far Sa / Sq / Sz Survive Sampling and Cutoff](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_surface_roughness/01_surface_components_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_surface_roughness/01_surface_components.png)

*↑ **How Far Sa / Sq / Sz Survive Sampling and Cutoff** ―― A surface synthesised from a prescribed PSD (so the true Sq follows analytically from Parseval), with tilt, waviness, lay and scratches added before the roughness parameters are measured. Calling the raw rms 'Sq' overstates it 20x; removing only the plane still leaves 1.8x. At 8 µm sampling Sa is -3.5 % (pass) while Sz is -19.8 % (fail); Sz keeps growing with evaluation area and never plateaus, so there is no such thing as the true Sz.*

[![dx=8 µm では Sa が ±5 % 合格で Sz が不合格。同じデータでも見るパラメータで結論が反転する。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_surface_roughness/02_sampling_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_surface_roughness/02_sampling_cliff.png)

*↑ The measurement ―― dx=8 µm では Sa が ±5 % 合格で Sz が不合格。同じデータでも見るパラメータで結論が反転する。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_surface_roughness.py
```

Source: [examples/poc_surface_roughness.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_surface_roughness.py)

Ops used (notes): [`profile_params`](https://furuse.work/ops/roughness/measure/profile_params.html) · [`surface_filter`](https://furuse.work/ops/roughness/prepare/surface_filter.html) · [`surface_form_remove`](https://furuse.work/ops/roughness/prepare/surface_form_remove.html) · [`surface_params`](https://furuse.work/ops/roughness/measure/surface_params.html) · [`surface_psd`](https://furuse.work/ops/roughness/measure/surface_psd.html) · [`surface_synth_psd`](https://furuse.work/ops/roughness/synth/surface_synth_psd.html)

## 19. How Accurately a White-Light Interferometer Measures a Nanometre Step

[![How Accurately a White-Light Interferometer Measures a Nanometre Step](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/01_interferogram_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/01_interferogram.png)

*↑ **How Accurately a White-Light Interferometer Measures a Nanometre Step** ―― A synthesised coherence-scanning stack with steps of 50 to 500 nm measured back. At 1 % noise the bias stays within 2.4 nm and the standard deviation within 14.1 nm, almost independent of step height. The null (envelope's maximum sample) errs by exactly half the scan step, and at 0.14 µm, just inside the Nyquist ceiling of 0.15 µm, the noise-free error is already +14.1 nm.*

[![0.02〜0.12 µm は 0.05 nm 以内で平ら。Nyquist 上限 0.15 µm の手前 0.14 µm で崖。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/02_zstep_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/02_zstep_sweep.png)

*↑ The measurement ―― 0.02〜0.12 µm は 0.05 nm 以内で平ら。Nyquist 上限 0.15 µm の手前 0.14 µm で崖。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_interferometry_step.py
```

Source: [examples/poc_interferometry_step.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_interferometry_step.py)

Ops used (notes): [`csi_design`](https://furuse.work/ops/interferometry/design/csi_design.html) · [`csi_height_map`](https://furuse.work/ops/interferometry/surface/csi_height_map.html) · [`csi_stack_simulate`](https://furuse.work/ops/interferometry/simulate/csi_stack_simulate.html) · [`decode_fringe`](https://furuse.work/ops/3d/structured_light/decode_fringe.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`synthesize_fringes`](https://furuse.work/ops/3d/structured_light/synthesize_fringes.html)

## 20. Strain From Speckle Images (DIC)

[![Strain From Speckle Images (DIC)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dic_strain/04_strain_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dic_strain/04_strain_map.png)

*↑ **Strain From Speckle Images (DIC)** ―― Displacement and strain read from a speckle pair in which 3000 Gaussian spots were moved by the deformation map and redrawn, not interpolated. For a true shift of 0.37 px the window-correlation estimator (piv) is biased by 0.0002 px with 0.0022 px scatter, 167x better than the null that answers 'no motion'. A rigid rotation manufactures several hundred µε of false strain under the small-strain definition; Green-Lagrange gives exactly 0.*

[![変形は補間ではなく斑点の再描画。だから真値が厳密。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dic_strain/01_speckle_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dic_strain/01_speckle.png)

*↑ The measurement ―― 変形は補間ではなく斑点の再描画。だから真値が厳密。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_dic_strain.py
```

Source: [examples/poc_dic_strain.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dic_strain.py)

Ops used (notes): [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`strain_from_displacement`](https://furuse.work/ops/piv/solid/strain_from_displacement.html)

## 21. Strain History in a Creep Test — Cumulative or Direct?

[![Strain History in a Creep Test — Cumulative or Direct?](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/01_speckle_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/01_speckle.png)

*↑ **Strain History in a Creep Test — Cumulative or Direct?** ―― One hour of creep in 25 frames, with strain history from accumulating adjacent-frame displacements versus comparing each frame directly with the reference. At the end, cumulative errs by 61 µε and direct by 1878 µε — cumulative wins 31x and the textbook crossover in time never appears (it lives on the noise axis instead). Thinning from 24 to 4 steps worsens cumulative from -60 to -606 µε; what matters is the deformation per step, not the number of steps.*

[![直接の偏りだけが伸びる。累積は偏りも散らばりも頭打ちで、しかも散らばりより偏りのほうが大きい ——ランダムウォークではない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/02_errors_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/02_errors.png)

*↑ The measurement ―― 直接の偏りだけが伸びる。累積は偏りも散らばりも頭打ちで、しかも散らばりより偏りのほうが大きい ——ランダムウォークではない。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_strain_history.py
```

Source: [examples/poc_strain_history.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_strain_history.py)

Ops used (notes): [`moving_average_window`](https://furuse.work/ops/videostream/window/moving_average_window.html) · [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`piv_error_stats`](https://furuse.work/ops/piv/assess/piv_error_stats.html) · [`piv_multipass`](https://furuse.work/ops/piv/estimate/piv_multipass.html) · [`piv_sample_at_windows`](https://furuse.work/ops/piv/assess/piv_sample_at_windows.html) · [`piv_synth_pair`](https://furuse.work/ops/piv/synth/piv_synth_pair.html) · [`poly_fit`](https://furuse.work/ops/math/interp_poly/poly_fit.html)

## 22. Stress by Photoelasticity — Unwrapping Fails First at the Isotropic Point

[![Stress by Photoelasticity — Unwrapping Fails First at the Isotropic Point](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_photoelasticity/01_polariscope_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_photoelasticity/01_polariscope.png)

*↑ **Stress by Photoelasticity — Unwrapping Fails First at the Isotropic Point** ―― The closed-form stress field of a diametrally loaded disc (4.2441 MPa at the centre, fringe order 2.380) turned into polariscope images by the Mueller-matrix ops and read back to stress. The op-built polariscope matches the textbook formula to 2.2e-16 across 125 cases. Phase wraps in the 84.2 % of pixels above fringe order 0.5, and unwrapping breaks first not where stress is highest but at the isotropic point, where modulation vanishes.*

[![左下 2 枚が「壊れる予報」。どちらもマスクで外せる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_photoelasticity/02_unwrap_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_photoelasticity/02_unwrap.png)

*↑ The measurement ―― 左下 2 枚が「壊れる予報」。どちらもマスクで外せる。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_photoelasticity.py
```

Source: [examples/poc_photoelasticity.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_photoelasticity.py)

Ops used (notes): [`mueller_apply`](https://furuse.work/ops/optics/polarization/mueller_apply.html) · [`mueller_element`](https://furuse.work/ops/optics/polarization/mueller_element.html) · [`unwrap_phase_2d`](https://furuse.work/ops/3d/structured_light/unwrap_phase_2d.html)

## 23. Measuring Bilateral Asymmetry — The Symmetry Plane Gets Dragged by the Deformation

[![Measuring Bilateral Asymmetry — The Symmetry Plane Gets Dragged by the Deformation](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bilateral_asymmetry/03_deviation_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bilateral_asymmetry/03_deviation_map.png)

*↑ **Measuring Bilateral Asymmetry — The Symmetry Plane Gets Dragged by the Deformation** ―― A perfectly symmetric synthetic skull with a known bulge added on one side, mirrored and overlaid. Even a perfectly symmetric specimen never scores 0: the floor drops from 1.33 mm (point-to-point) to 0.030 mm (point-to-plane) to 0.012 mm (neighbourhood smoothing). The residual-minimising plane is dragged 2.92 mm / 1.72 degrees by a 6.33 mm bulge, and 46 % of the asymmetry disappears.*

[![完全対称な標本を測った残差。点対点は点間隔がそのまま床になる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bilateral_asymmetry/01_floor_vs_spacing_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bilateral_asymmetry/01_floor_vs_spacing.png)

*↑ The measurement ―― 完全対称な標本を測った残差。点対点は点間隔がそのまま床になる。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_bilateral_asymmetry.py
```

Source: [examples/poc_bilateral_asymmetry.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bilateral_asymmetry.py)

Ops used (notes): [`chamfer_distance`](https://furuse.work/ops/3d/metrics/chamfer_distance.html) · [`detect_reflection_symmetry`](https://furuse.work/ops/3d/symmetry/detect_reflection_symmetry.html) · [`detect_rotational_symmetry`](https://furuse.work/ops/3d/symmetry/detect_rotational_symmetry.html) · [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`hausdorff_distance`](https://furuse.work/ops/3d/metrics/hausdorff_distance.html) · [`reflect_points`](https://furuse.work/ops/3d/symmetry/reflect_points.html) · [`reflection_symmetry_score`](https://furuse.work/ops/3d/symmetry/reflection_symmetry_score.html) · [`sample_surface`](https://furuse.work/ops/3d/superquadric/sample_surface.html) · [`vertex_normals`](https://furuse.work/ops/3d/mesh_process/vertex_normals.html)

## 24. Particle Size Distribution From Images — Merging and Edge Cuts Pull Opposite Ways and Cancel

[![Particle Size Distribution From Images — Merging and Edge Cuts Pull Opposite Ways and Cancel](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/01_scene.png)

*↑ **Particle Size Distribution From Images — Merging and Edge Cuts Pull Opposite Ways and Cancel** ―― D10 / D50 / D90 from a synthetic scatter of particles, with merges (pulling large) and edge cuts (pulling small) counted separately. At an area fraction of 13.8 % the D50 error is +0.55 % — because 28 merges and 19 edge cuts happen to balance. Number- and area-weighting give D50 values of 26.9 and 44.7 µm (1.66x) from the same blobs.*

[![薄いところで 0 なのは正確だから。濃いところで 0 をまたぐのは融合と縁切れが釣り合っただけ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/02_density_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/02_density_sweep.png)

*↑ The measurement ―― 薄いところで 0 なのは正確だから。濃いところで 0 をまたぐのは融合と縁切れが釣り合っただけ。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_particle_sizing.py
```

Source: [examples/poc_particle_sizing.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_particle_sizing.py)

Ops used (notes): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`blob_region`](https://furuse.work/ops/blob/extract/blob_region.html) · [`blob_select`](https://furuse.work/ops/blob/select/blob_select.html) · [`circularity`](https://furuse.work/ops/2d/features/circularity.html) · [`distance_transform`](https://furuse.work/ops/2d/region/distance_transform.html)

## 25. Fibre Orientation Distribution — Angles Repeat Every 180 Degrees, and a Naive Mean Is 90 Degrees Off

[![Fibre Orientation Distribution — Angles Repeat Every 180 Degrees, and a Naive Mean Is 90 Degrees Off](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/01_scene.png)

*↑ **Fibre Orientation Distribution — Angles Repeat Every 180 Degrees, and a Naive Mean Is 90 Degrees Off** ―― Orientation of 140 fibres drawn from a von Mises distribution, read with a structure tensor. For a true mean of 177.9 degrees the arithmetic mean reports 105.55 degrees (-72.33), while the doubled-angle circular mean is off by +0.17 degrees — with not one bit of the image or the measurement changed. Weighting every pixel equally drops the orientation index by -31.3 %.*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/02_wrap_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/02_wrap.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_fiber_orientation.py
```

Source: [examples/poc_fiber_orientation.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_fiber_orientation.py)

Ops used (notes): [`coherence`](https://furuse.work/ops/acoustics/dual/coherence.html) · [`dc_structure_texture`](https://furuse.work/ops/2d/decomposition/dc_structure_texture.html) · [`moment_axes`](https://furuse.work/ops/3d/match_pose/moment_axes.html) · [`principal_moments`](https://furuse.work/ops/3d/moment_invariant/principal_moments.html) · [`sobel_amp`](https://furuse.work/ops/2d/edges/sobel_amp.html) · [`sobel_dir`](https://furuse.work/ops/2d/edges/sobel_dir.html)

## 26. Metallographic Grain Size — The Planimetric and Intercept Methods Fall Off Different Cliffs

[![Metallographic Grain Size — The Planimetric and Intercept Methods Fall Off Different Cliffs](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/01_scene.png)

*↑ **Metallographic Grain Size — The Planimetric and Intercept Methods Fall Off Different Cliffs** ―― Grains are synthesized as a 2-D Voronoi tessellation with 2-px boundaries, then etching unevenness, noise and boundary gaps are added; ASTM E112 grain size G is measured by the planimetric method (Otsu + connected components) and the lineal-intercept method (local threshold + test lines in 4 directions). The planimetric method survives noise alone (-0.02) and etching unevenness alone (-0.40) but dies under both (+3.82), and loses one G step at 7.2 % boundary gaps; the intercept method holds to 40.7 % — the predicted 29.3 % was wrong because only 0.76 f of the boundary actually disappears in the mask. A duplex structure gives a whole-field G of 7.82 that matches neither the fine (9.01) nor the coarse (6.15) population; only 4 of 64 tiles fall within ±0.5 of it.*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/02_controls_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/02_controls.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_metal_grain_size.py
```

Source: [examples/poc_metal_grain_size.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_metal_grain_size.py)

Ops used (notes): [`bin_threshold`](https://furuse.work/ops/2d/segmentation/bin_threshold.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`bothat`](https://furuse.work/ops/2d/morphology/bothat.html) · [`dyn_threshold`](https://furuse.work/ops/2d/segmentation/dyn_threshold.html) · [`gray_bothat`](https://furuse.work/ops/2d/morphology/gray_bothat.html) · [`hx_close_edges`](https://furuse.work/ops/2d/halcon_ext/hx_close_edges.html) · [`invert_image`](https://furuse.work/ops/2d/gray/invert_image.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html)

## 27. Pitch, Flank Angle and Pitch Diameter From a Thread Silhouette — Tilt Shows Up With Opposite Signs on the Two Flanks

[![Pitch, Flank Angle and Pitch Diameter From a Thread Silhouette — Tilt Shows Up With Opposite Signs on the Two Flanks](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/07_sampling_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/07_sampling_frames.png)

*↑ **Pitch, Flank Angle and Pitch Diameter From a Thread Silhouette — Tilt Shows Up With Opposite Signs on the Two Flanks** ―― An M6-like silhouette drawn from the ISO 68-1 basic triangle in closed form (1 px = 25 µm). An FFT of the binarised column widths reports half the true pitch, 20 px, because the two profiles are offset by P/2 and their sum is constant. Tilting the axis by 3 degrees splits the flank angles into 33.18 / 26.74 degrees: their half-sum 29.81 is the true flank angle and their half-difference 3.19 estimates the tilt. Pitch measured on one flank drifts at first order (+3.28 / -2.79 %) while the crest spacing drifts at second order (-0.12 %); undoing the tilt leaves P -0.009 % and d2 +0.033 %.*

[![幅の系列は上下輪郭(P/2 ずれ)の和なので基本波が消える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/01_zero_spectrum_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/01_zero_spectrum.png)

*↑ The measurement ―― 幅の系列は上下輪郭(P/2 ずれ)の和なので基本波が消える。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_screw_thread_metrology.py
```

Source: [examples/poc_screw_thread_metrology.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_screw_thread_metrology.py)

Ops used (notes): [`fit_line_contours`](https://furuse.work/ops/2d/contour/fit_line_contours.html) · [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`hx_split_contours`](https://furuse.work/ops/2d/halcon_ext/hx_split_contours.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html) · [`threshold_sub_pix`](https://furuse.work/ops/2d/contour/threshold_sub_pix.html) · [`xg_regress_contours`](https://furuse.work/ops/2d/xldgeom/xg_regress_contours.html)

### The Medical and Biological Wing — The Count Is Right and the Contents Are Wrong

Counting cells, reading a nucleus's DNA content, measuring vessel branching, tracking a wound's area: all of these tend to be reported as one number, and there are situations in which that number is right anyway. Cell counting where over- and under-segmentation balance to a +0.3-cell bias; ploidy classification that survives a forgotten background subtraction; a calibration that returns the most stable and most wrong healing constant.

The four exhibits carry ground truth that a label image alone cannot hold — which cells overlap which, area and DNA content varying independently, a tree that satisfies the branching law exactly. Each docstring warns that calling a label image 'the truth' on real data erases the very thing being tested.

The thing to watch for is a method that appears to improve while the quantity it measures quietly swaps: the area classifier gets better with more blur because 'area' is leaking DNA content. Unless the reason for every improvement is traced, this kind of lie gets carried home as a result.

## 28. Counting Overlapping Cells — Count, Over-Segmentation and Under-Segmentation as Three Numbers

[![Counting Overlapping Cells — Count, Over-Segmentation and Under-Segmentation as Three Numbers](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cell_counting/01_scene_dense_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cell_counting/01_scene_dense.png)

*↑ **Counting Overlapping Cells — Count, Over-Segmentation and Under-Segmentation as Three Numbers** ―― Synthetic overlapping cells with the count, over-segmentation and under-segmentation tallied separately. In the densest condition the null misses 25 of 78 cells, every one of them an under-segmentation. Sweeping the seed suppression finds a balance point where the count bias is +0.3 cells while 13.3 segmentation errors remain; report the count alone and it passes as the best setting.*

[![誤り合計の谷と |偏り| の谷は同じ場所に来ない。どちらを最適と呼ぶかで答えが変わる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cell_counting/02_h_tradeoff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cell_counting/02_h_tradeoff.png)

*↑ The measurement ―― 誤り合計の谷と |偏り| の谷は同じ場所に来ない。どちらを最適と呼ぶかで答えが変わる。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_cell_counting.py
```

Source: [examples/poc_cell_counting.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_cell_counting.py)

Ops used (notes): [`circularity`](https://furuse.work/ops/2d/features/circularity.html) · [`distance_transform`](https://furuse.work/ops/2d/region/distance_transform.html) · [`fill_holes`](https://furuse.work/ops/2d/region/fill_holes.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`sk_otsu`](https://furuse.work/ops/2d/segmentation/sk_otsu.html) · [`vol_distance_transform`](https://furuse.work/ops/3d/medial/vol_distance_transform.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_local_maxima`](https://furuse.work/ops/3d/feature/vol_local_maxima.html) · [`vol_watershed`](https://furuse.work/ops/3d/segment/vol_watershed.html) · [`xsk2_h_maxima`](https://furuse.work/ops/2d/segmentation/xsk2_h_maxima.html)

## 29. Ploidy From Integrated Nuclear Intensity — Area Cannot Separate It

[![Ploidy From Integrated Nuclear Intensity — Area Cannot Separate It](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_nuclei_ploidy/04_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_nuclei_ploidy/04_scene.png)

*↑ **Ploidy From Integrated Nuclear Intensity — Area Cannot Separate It** ―― Fluorescent nuclei whose DNA content D and area A were drawn with independent spread, classified by area and by integrated intensity. Even the true area misclassifies 15.4 %; integrated intensity misclassifies 0 %. Forgetting to subtract background leaves the classification intact while the DNA index alone breaks from 2.115 to 1.702 (-20 %) — invisible if you only watch the classification.*

[![累積分布。積分輝度の 4n は 2.1 付近に固まり、面積の 2 本は大きく重なる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_nuclei_ploidy/01_histograms_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_nuclei_ploidy/01_histograms.png)

*↑ The measurement ―― 累積分布。積分輝度の 4n は 2.1 付近に固まり、面積の 2 本は大きく重なる。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_nuclei_ploidy.py
```

Source: [examples/poc_nuclei_ploidy.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_nuclei_ploidy.py)

Ops used (notes): [`aperture_photometry`](https://furuse.work/ops/astrostack/photometry/aperture_photometry.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`sg_gmm_segment`](https://furuse.work/ops/2d/segment/sg_gmm_segment.html) · [`sk_otsu`](https://furuse.work/ops/2d/segmentation/sk_otsu.html)

## 30. Extracting a Vessel Network — Spurs, Overestimated Radii Near Branches, and a Fragile Exponent

[![Extracting a Vessel Network — Spurs, Overestimated Radii Near Branches, and a Fragile Exponent](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vessel_network/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vessel_network/01_scene.png)

*↑ **Extracting a Vessel Network — Spurs, Overestimated Radii Near Branches, and a Fragile Exponent** ―― A synthetic vessel tree obeying Murray's law exactly, skeletonised and measured for branch points, radii and the exponent. Counting branch pixels directly gives 47 pixels for 25 branches; grouping them into connected components gives exactly 25. Spurs come not from the skeletonisation but from boundary roughness (spurious branches 0 → 72), and radii within 3 px of a branch are overestimated by +26.2 %.*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vessel_network/02_prune_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vessel_network/02_prune.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_vessel_network.py
```

Source: [examples/poc_vessel_network.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_vessel_network.py)

Ops used (notes): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`distance_transform`](https://furuse.work/ops/2d/region/distance_transform.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`medial_axis_points`](https://furuse.work/ops/3d/medial/medial_axis_points.html) · [`r2_split_skeleton_lines`](https://furuse.work/ops/2d/region/r2_split_skeleton_lines.html) · [`sk_medial`](https://furuse.work/ops/2d/region/sk_medial.html) · [`skeleton`](https://furuse.work/ops/2d/region/skeleton.html) · [`skeleton_branches3d`](https://furuse.work/ops/3d/medial/skeleton_branches3d.html) · [`skeleton_endpoints3d`](https://furuse.work/ops/3d/medial/skeleton_endpoints3d.html) · [`skeleton_junctions3d`](https://furuse.work/ops/3d/medial/skeleton_junctions3d.html) · [`skeleton_prune3d`](https://furuse.work/ops/3d/medial/skeleton_prune3d.html) · [`skeletonize_vol`](https://furuse.work/ops/3d/medial/skeletonize_vol.html) · [`thinning`](https://furuse.work/ops/2d/region/thinning.html) · [`vol_distance_transform`](https://furuse.work/ops/3d/medial/vol_distance_transform.html)

## 31. Wound Area Over Time — Calibration Error Enters the Area Squared

[![Wound Area Over Time — Calibration Error Enters the Area Squared](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_wound_area_tracking/02_scenes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_wound_area_tracking/02_scenes.png)

*↑ **Wound Area Over Time — Calibration Error Enters the Area Squared** ―― A star-shaped wound on a millimetre plane (closed-form area), photographed day by day through a pinhole camera to estimate the healing constant k. A 4 % change in distance moves the area by 7.7 %; with the distance drifting 1.2 % per day the null reports k = 0.1424 against a true 0.1200 (+18.7 %). Its standard deviation, 0.0049, is smaller than the 0.0059 of recalibrating every time — the most stable and the most wrong answer.*

[![ゼロ点の面積誤差。実測は閉形式の 2 乗則に乗り、線形近似からは外れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_wound_area_tracking/01_dist_square_law_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_wound_area_tracking/01_dist_square_law.png)

*↑ The measurement ―― ゼロ点の面積誤差。実測は閉形式の 2 乗則に乗り、線形近似からは外れる。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_wound_area_tracking.py
```

Source: [examples/poc_wound_area_tracking.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_wound_area_tracking.py)

Ops used (notes): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_select_largest`](https://furuse.work/ops/blob/select/blob_select_largest.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`warp_by_plane`](https://furuse.work/ops/3d/plane_sweep_stereo/warp_by_plane.html)

## 32. Colocalization lies under bleed-through — Pearson and Manders break in different places

[![Colocalization lies under bleed-through — Pearson and Manders break in different places](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/01_scene_channels_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/01_scene_channels.png)

*↑ **Colocalization lies under bleed-through — Pearson and Manders break in different places** ―― Two channels of vesicle-like puncta are scattered over a synthetic cell body, with 0 / 25 / 50 / 100 % of the B puncta placed exactly on A puncta so the true colocalization is known. After the bleed-through matrix [[1, α], [β, 1]], cytoplasm, PSF and photon noise, two unrelated channels give Pearson r=0.203 and Otsu-Manders M1=0.133 at α=β=10 %. Estimating α=0.0996 (truth 0.10) from single-stain controls and unmixing linearly restores r to 0.007, but Manders stays at 0.705 even for 100 % (the Gaussian tails below the Otsu threshold are lost; closed-form prediction 0.756). Pearson crosses 0.5 at symmetric α=0.282 (predicted 2−√3=0.268); blur only breaks Manders, with a step at σ=2.5 px where Otsu's foreground jumps from puncta to the whole cell. The Costes shuffle test calls pure bleed-through 'significant' at p=0.000.*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/02_scene_unmixed_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/02_scene_unmixed.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_colocalization_crosstalk.py
```

Source: [examples/poc_colocalization_crosstalk.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_colocalization_crosstalk.py)

Ops used (notes): [`gauss_image`](https://furuse.work/ops/2d/smoothing/gauss_image.html) · [`mat_lstsq`](https://furuse.work/ops/math/linalg/mat_lstsq.html) · [`mat_solve`](https://furuse.work/ops/math/linalg/mat_solve.html) · [`noise_sigma`](https://furuse.work/ops/astrostack/quality/noise_sigma.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`photon_sample`](https://furuse.work/ops/photon/counting/photon_sample.html) · [`reg_erode`](https://furuse.work/ops/2d/region/reg_erode.html) · [`stat_correlation`](https://furuse.work/ops/math/stats/stat_correlation.html)

## 33. MRI Bias Field and Tissue Area — Grey and White Matter Fail in Opposite Directions, and the Sum Hides It

[![MRI Bias Field and Tissue Area — Grey and White Matter Fail in Opposite Directions, and the Sum Hides It](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/02_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/02_scene.png)

*↑ **MRI Bias Field and Tissue Area — Grey and White Matter Fail in Opposite Directions, and the Sum Hides It** ―― A brain-slice phantom of elliptical shells (skull / CSF / wrinkled cortex / WM, areas known from geometry) is multiplied by a surface-coil bias field and Rician noise, and the three tissue areas are measured with global three-class Otsu (xsk2_multiotsu). At 30 % amplitude GM is +20.2 % and WM -7.7 % while GM+WM is +0.0 % — the sum hides the error — and removing the noise flips the sign (GM -11.8 %). The geometric cliff prediction was 30 %; the measured cliff is 17.5 %. Naively smoothing log I damages a field-free image by GM +81.8 %; iterating on the segmentation residual (Wells-type) holds +1.8 % even at 40 %. Every corrector fails once the field is as fine as 4 px, and at SNR 15 GM is +8.5 % even without a field (WM is 2.6× larger, so the error lands on the smaller tissue).*

[![雑音だけでは壊れず、場だけで GM と WM が逆向きに動く。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/01_controls_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/01_controls.png)

*↑ The measurement ―― 雑音だけでは壊れず、場だけで GM と WM が逆向きに動く。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_mri_bias_field.py
```

Source: [examples/poc_mri_bias_field.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_mri_bias_field.py)

Ops used (notes): [`dc_homomorphic`](https://furuse.work/ops/2d/decomposition/dc_homomorphic.html) · [`eval_bspline_surface`](https://furuse.work/ops/3d/freeform/eval_bspline_surface.html) · [`eval_poly_surface`](https://furuse.work/ops/3d/surface_fit/eval_poly_surface.html) · [`fit_bspline_surface`](https://furuse.work/ops/3d/freeform/fit_bspline_surface.html) · [`fit_poly_surface`](https://furuse.work/ops/3d/surface_fit/fit_poly_surface.html) · [`overlay_labels`](https://furuse.work/ops/annotate/overlay/overlay_labels.html) · [`xsk2_multiotsu`](https://furuse.work/ops/2d/segmentation/xsk2_multiotsu.html)

## 34. Trabecular Thickness, Separation and Bone Volume Fraction — The Plate Model and the Direct Method Disagree on the Same Image

[![Trabecular Thickness, Separation and Bone Volume Fraction — The Plate Model and the Direct Method Disagree on the Same Image](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bone_trabecular_thickness/01_scene_truth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bone_trabecular_thickness/01_scene_truth.png)

*↑ **Trabecular Thickness, Separation and Bone Volume Fraction — The Plate Model and the Direct Method Disagree on the Same Image** ―― A 2-D trabecular network drawn in closed form as a set of segments (median width 120 µm), observed through partial-volume blur, CT noise and a cupping bias. There is more than one ground truth: the length-weighted mean width is 104.8 µm, the largest-inscribed-circle definition gives 121.6 µm and the plate model 118.4 µm — the choice of truth moves the answer by 9–16 % before any threshold does. The resolution cliff hits the distribution, not the mean (overlap with truth 0.83 → 0.09 at 60 µm pixels; the mean survives because quantisation at -29.5 % and Otsu thickening at +27.1 % cancel). Noise breaks from two sides, speckles from σ 0.10 and gaps from σ 0.15, and an area opening removes only the speckles.*

[![Tb.Th の平均は 2 px/骨梁でも持つが、BV/TV と分布は壊れている。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bone_trabecular_thickness/02_resolution_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bone_trabecular_thickness/02_resolution_sweep.png)

*↑ The measurement ―― Tb.Th の平均は 2 px/骨梁でも持つが、BV/TV と分布は壊れている。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_bone_trabecular_thickness.py
```

Source: [examples/poc_bone_trabecular_thickness.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bone_trabecular_thickness.py)

Ops used (notes): [`blob_distance`](https://furuse.work/ops/blob/split/blob_distance.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`dc_retinex`](https://furuse.work/ops/2d/decomposition/dc_retinex.html) · [`dist_transform`](https://furuse.work/ops/2d/region/dist_transform.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`get_region_thickness`](https://furuse.work/ops/2d/features/get_region_thickness.html) · [`opening_circle`](https://furuse.work/ops/2d/region/opening_circle.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`sk_area_opening`](https://furuse.work/ops/2d/morphology/sk_area_opening.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html)

### The Astronomy and Environment Wing — Biased by Position, Flipped by the Definition of Truth

Stellar brightness and position, the solar limb, all-sky cloud cover, sea-ice concentration, crop cover, terrain, river stage. The subjects are far away and ground truth is normally out of reach. The eight exhibits here turn that around, placing their truth in closed forms and public data: celestial coordinates, the solid angle of a spherical cap, Eddington limb darkening, elevation tiles from the Geospatial Information Authority of Japan.

The shared finding is that the same object reads differently depending on where it is: the same cloud counts 1.45x more at the horizon than at the zenith; clouds of equal optical thickness are detected or not depending on their angular distance from the sun; the same reflection makes one detector read quietly low and another stop silently.

The other is that the definition of truth decides the conclusion. Counting thin ice as 'ice' or not sends the same estimate to -4.4 or +2.7 points; a cloud fraction reported without its horizon-mask angle can legitimately claim anything from 0.18 to 0.23. What you call the truth has to be written down before the instrument is.

## 35. How Many Frames for What Photometric Precision?

[![How Many Frames for What Photometric Precision?](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_astro_photometry/01_stack_scaling_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_astro_photometry/01_stack_scaling.png)

*↑ **How Many Frames for What Photometric Precision?** ―― A star field placed to specification and stacked N deep, to see whether aperture-photometry error falls as 1/√N. From N = 1 to 16 the median error drops from 0.6350 % to 0.1616 %, within 4.6 % of theory in all eight cases. One cosmic ray pushes the plain mean to +5.89 % while κ-σ clipping holds +0.30 %; the rejection rate does not move, so 'the rejection rate went up, therefore it worked' is not an available argument.*

[![単純平均だけが 5.9 % 残る。κ-σ は汚染なしと区別できないところまで戻すが、棄却率はほとんど動かない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_astro_photometry/02_cosmic_ray_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_astro_photometry/02_cosmic_ray.png)

*↑ The measurement ―― 単純平均だけが 5.9 % 残る。κ-σ は汚染なしと区別できないところまで戻すが、棄却率はほとんど動かない。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_astro_photometry.py
```

Source: [examples/poc_astro_photometry.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_astro_photometry.py)

Ops used (notes): [`aperture_photometry`](https://furuse.work/ops/astrostack/photometry/aperture_photometry.html) · [`drizzle_resample`](https://furuse.work/ops/astrostack/stack/drizzle_resample.html) · [`lucky_select`](https://furuse.work/ops/astrostack/quality/lucky_select.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`sigma_clip_stack`](https://furuse.work/ops/astrostack/stack/sigma_clip_stack.html) · [`synth_frame_series`](https://furuse.work/ops/astrostack/synth/synth_frame_series.html) · [`synth_starfield`](https://furuse.work/ops/astrostack/synth/synth_starfield.html)

## 36. To What Fraction of a Pixel Can a Star Be Located, and Where Is the Cliff?

[![To What Fraction of a Pixel Can a Star Be Located, and Where Is the Cliff?](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_star_astrometry/03_starfield_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_star_astrometry/03_starfield.png)

*↑ **To What Fraction of a Pixel Can a Star Be Located, and Where Is the Cliff?** ―― Stars rendered from known celestial coordinates, located by four methods and compared with the Fisher-information bound. At S/N 298 the centroid (null) sits at 5.56x the bound and the background-subtracted centroid at 1.03x; no method beats the bound. At the faint end the null appears to beat it (0.2790 px versus 0.3471 px), but with a sensitivity of 0.038 it is merely returning the rounded initial guess.*

[![暗い端で素の重心が下限を割って見えるのは「動かない推定器」だから(感度 0.038)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_star_astrometry/01_snr_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_star_astrometry/01_snr_sweep.png)

*↑ The measurement ―― 暗い端で素の重心が下限を割って見えるのは「動かない推定器」だから(感度 0.038)。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_star_astrometry.py
```

Source: [examples/poc_star_astrometry.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_star_astrometry.py)

Ops used (notes): [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`noise_sigma`](https://furuse.work/ops/astrostack/quality/noise_sigma.html) · [`psf_fit`](https://furuse.work/ops/astrostack/photometry/psf_fit.html) · [`star_detect`](https://furuse.work/ops/astrostack/photometry/star_detect.html)

## 37. Where Is the Edge of a Limb-Darkened Disc? The 50 % Rule Reads the Radius Small

[![Where Is the Edge of a Limb-Darkened Disc? The 50 % Rule Reads the Radius Small](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_limb_darkening/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_limb_darkening/01_scene.png)

*↑ **Where Is the Edge of a Limb-Darkened Disc? The 50 % Rule Reads the Radius Small** ―― A limb-darkened solar disc seen through seeing, its radius measured by the 50 % rule, by gradient maximum and by model fitting. The prediction 'bias scales with the darkening coefficient' failed: at u = 0.8 the bias is -12.76 px (pure geometry predicts -13.14 px). The cancellation point near threshold 0.26, where blur appears to have no effect, moves to 0.38 when u changes.*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_limb_darkening/02_bias_vs_u_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_limb_darkening/02_bias_vs_u.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_solar_limb_darkening.py
```

Source: [examples/poc_solar_limb_darkening.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_solar_limb_darkening.py)

Ops used (notes): [`edge_points`](https://furuse.work/ops/3d/edges/edge_points.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`mat_lstsq`](https://furuse.work/ops/math/linalg/mat_lstsq.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html)

## 38. All-Sky Cloud Cover — Counting Pixels Is Biased by Position

[![All-Sky Cloud Cover — Counting Pixels Is Biased by Position](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_allsky_cloud_cover/03_mask_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_allsky_cloud_cover/03_mask_sweep.png)

*↑ **All-Sky Cloud Cover — Counting Pixels Is Biased by Position** ―― Spherical-cap clouds (closed-form solid angle) placed in an equidistant fisheye sky, with cloud fraction counted by pixel ratio and by solid-angle weight. The same cloud reads 0.00789 at the zenith and 0.01142 at 82 degrees (1.45x). Geometry alone errs by -5.02 %, detection alone by +37.95 %, and the naive count cancels them to +29.73 %.*

[![画素数比は天頂で 0.81、地平線側で 1.17。重みを掛けると 1 に張り付く。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_allsky_cloud_cover/01_jacobian_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_allsky_cloud_cover/01_jacobian.png)

*↑ The measurement ―― 画素数比は天頂で 0.81、地平線側で 1.17。重みを掛けると 1 に張り付く。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_allsky_cloud_cover.py
```

Source: [examples/poc_allsky_cloud_cover.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_allsky_cloud_cover.py)

Ops used (notes): [`polar_trans_image`](https://furuse.work/ops/2d/geometry/polar_trans_image.html)

## 39. Sea-Ice Concentration — The Answer Depends on How Mixed Pixels Are Counted

[![Sea-Ice Concentration — The Answer Depends on How Mixed Pixels Are Counted](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sea_ice_concentration/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sea_ice_concentration/01_scene.png)

*↑ **Sea-Ice Concentration — The Answer Depends on How Mixed Pixels Are Counted** ―― Ice concentration from a PSF-blurred two-band ice/water image, by hard classification and by linear unmixing. Hard classification is off by -4.2 points, unmixing by +0.02. The bias is explained by the perimeter fraction (R² = 0.984) and crosses zero near a concentration of 0.49 — validate only there and it passes.*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sea_ice_concentration/02_bias_vs_threshold_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sea_ice_concentration/02_bias_vs_threshold.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_sea_ice_concentration.py
```

Source: [examples/poc_sea_ice_concentration.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_sea_ice_concentration.py)

Ops used (notes): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`mat_lstsq`](https://furuse.work/ops/math/linalg/mat_lstsq.html)

## 40. Counting Crop Green — Ground Truth as Per-Pixel Leaf Area Fraction

[![Counting Crop Green — Ground Truth as Per-Pixel Leaf Area Fraction](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vegetation_cover/01_mixed_pixel_response_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vegetation_cover/01_mixed_pixel_response.png)

*↑ **Counting Crop Green — Ground Truth as Per-Pixel Leaf Area Fraction** ―― Cover fraction from a four-band field image, scored against the per-pixel leaf area fraction. The null (Otsu on the green channel) overshoots by +16.3 pp at mid-season, and since every method scatters by under 0.5 pp, nearly all of the difference is bias. At emergence on wet soil the null's cover bias is -0.2 pp while precision and recall are both 0.000 — the number is right and not a single pixel is.*

[![影ゼロならゼロ点も悪くない。影は『暗さ』を手掛かりにする手法に直接刺さる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vegetation_cover/02_shadow_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vegetation_cover/02_shadow_sweep.png)

*↑ The measurement ―― 影ゼロならゼロ点も悪くない。影は『暗さ』を手掛かりにする手法に直接刺さる。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_vegetation_cover.py
```

Source: [examples/poc_vegetation_cover.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_vegetation_cover.py)

Ops used (notes): [`cv_otsu`](https://furuse.work/ops/2d/segmentation/cv_otsu.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`sk_otsu`](https://furuse.work/ops/2d/segmentation/sk_otsu.html)

## 41. Measuring Terrain — Slope, Flow and Insolation Against Closed Forms

[![Measuring Terrain — Slope, Flow and Insolation Against Closed Forms](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dem_terrain/01_cone_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dem_terrain/01_cone.png)

*↑ **Measuring Terrain — Slope, Flow and Insolation Against Closed Forms** ―― Slope, curvature and sky-view factor checked against closed forms on a plane, a cone and a Gaussian hill. Halving the cell size cuts the hill's curvature error by about four — a discretisation error, not a wrong formula. The sky-view factor takes 2.03 s on a 513×513 grid with 8 directions; before the rewrite it took 41.9 s, and the tests had only ever checked that it runs.*

[![参照線と平行 = 2 次収束 = 離散化の誤差。式が違えばセルを細かくしても誤差は下げ止まる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dem_terrain/02_curvature_convergence_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dem_terrain/02_curvature_convergence.png)

*↑ The measurement ―― 参照線と平行 = 2 次収束 = 離散化の誤差。式が違えばセルを細かくしても誤差は下げ止まる。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_dem_terrain.py
```

Source: [examples/poc_dem_terrain.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dem_terrain.py)

Ops used (notes): [`dem_aspect`](https://furuse.work/ops/dem/surface/dem_aspect.html) · [`dem_curvature`](https://furuse.work/ops/dem/surface/dem_curvature.html) · [`dem_fill_sinks`](https://furuse.work/ops/dem/hydrology/dem_fill_sinks.html) · [`dem_flow_accumulation`](https://furuse.work/ops/dem/hydrology/dem_flow_accumulation.html) · [`dem_hillshade`](https://furuse.work/ops/dem/shading/dem_hillshade.html) · [`dem_sky_view_factor`](https://furuse.work/ops/dem/visibility/dem_sky_view_factor.html) · [`dem_slope`](https://furuse.work/ops/dem/surface/dem_slope.html)

## 42. River Stage From an Oblique Photo — Ignoring Perspective Bends the Row-Number Error Into an Arc

[![River Stage From an Oblique Photo — Ignoring Perspective Bends the Row-Number Error Into an Arc](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_water_level/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_water_level/01_scene.png)

*↑ **River Stage From an Oblique Photo — Ignoring Perspective Bends the Row-Number Error Into an Arc** ―― The waterline detected on an obliquely photographed staff gauge and converted to stage. Linear conversion from two gauge marks bends off by up to -6.4 cm (at 1.00 m), and the sign is decided not by the stage but by whether the reading interpolates (-6.6 cm) or extrapolates (+16.3 cm). A four-point homography brings it under 0.2 cm; what remains is waterline detection, not perspective.*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_water_level/02_bias_vs_level_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_water_level/02_bias_vs_level.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_water_level.py
```

Source: [examples/poc_water_level.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_water_level.py)

Ops used (notes): [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`mat_svd`](https://furuse.work/ops/math/linalg/mat_svd.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`projective_trans_image`](https://furuse.work/ops/2d/geometry/projective_trans_image.html) · [`ransac_line`](https://furuse.work/ops/3d/robust_fit/ransac_line.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html)

## 43. Exoplanet transit from aperture photometry — depth and duration fail separately

[![Exoplanet transit from aperture photometry — depth and duration fail separately](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/01_scene_starfield_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/01_scene_starfield.png)

*↑ **Exoplanet transit from aperture photometry — depth and duration fail separately** ―― A synthetic star field (240 frames) carries a 10 ppt limb-darkened transit on the target only, with transparency variation, sub-pixel drift, flat-field non-uniformity and photon noise injected from separate random streams; fullseye's star_detect → frame_align → aperture_photometry extracts the light curve. The zero point (target aperture sum alone) breaks under clouds to a depth error of +72 ppt; the ratio to comparison stars gives -0.13 ppt / T14 -0.9 fr. Comparison-star choice moves the residual rms from 1.91 to 11.43 ppt (6.0x), and inverse-variance weights computed from raw variance are fooled by clouds into 1.52x worse than a plain sum. The small-aperture cliff at 1σ was not the predicted centroid error but the op's aperture-mask staircase (supersample=8: a static star sits 1.69x above theory, 0.93x at 32). The SNR=5 detection limit is 1.48 ppt measured vs 1.45 ppt theory with a known ephemeris, 2.0 ppt blind, where the duration breaks before the depth. Drift 2 px and a 3 % flat are harmless alone (0.16 / 0.08 ppt) but multiply into a 0.94 ppt false depth, 2.97 ppt (30 % of truth) at 4 px.*

[![前/入/最深部/出/後の各段階で平均した画像からトランジット外の平均を引いた [e-)。4 倍拡大](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/02_frames_transit_phases_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/02_frames_transit_phases.png)

*↑ The measurement ―― 前/入/最深部/出/後の各段階で平均した画像からトランジット外の平均を引いた [e-]。4 倍拡大 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_exoplanet_transit.py
```

Source: [examples/poc_exoplanet_transit.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_exoplanet_transit.py)

Ops used (notes): [`aperture_photometry`](https://furuse.work/ops/astrostack/photometry/aperture_photometry.html) · [`frame_align`](https://furuse.work/ops/astrostack/align/frame_align.html) · [`normalize`](https://furuse.work/ops/shape2d/descriptor/normalize.html) · [`sigma_clip_stack`](https://furuse.work/ops/astrostack/stack/sigma_clip_stack.html) · [`star_detect`](https://furuse.work/ops/astrostack/photometry/star_detect.html)

## 44. River surface velocity from an oblique video (LSPIV) — velocity error and discharge error are different numbers

[![River surface velocity from an oblique video (LSPIV) — velocity error and discharge error are different numbers](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/01_scene.png)

*↑ **River surface velocity from an oblique video (LSPIV) — velocity error and discharge error are different numbers** ―― A power-law surface velocity profile (8 m wide, 1.5 m/s peak) is the ground truth; foam tracers are advected frame by frame and imaged for 60 frames by an oblique bank camera with a known homography, with sky reflection, ripples and noise injected separately. fullseye's piv_cross_correlate → warp_by_plane (orthorectification) → piv_to_velocity yields u(y) and discharge Q = h∫u dy. The zero point (correlate the oblique frames, convert with one scale) errs +0.31 m/s near bank and -0.28 m/s far bank, the apparent width collapses to 3.3 m and Q is -57 %. Orthorectification gives 0.074 m/s RMS and Q -7.8 %, yet even the control group's Q -3.0 % is mostly (-2.5 %) the bank trapezoid rule, unrelated to velocity. The tracer-density cliff arrives as outliers, not NaNs (44 % flagged at 0.05 %; ensemble correlation does not rescue the lost windows). Widening the window smears the bank velocity by only -0.008 m/s, orders below the predicted window x gradient, while Q drifts from -1.1 to -7.0 %. Static reflections matter only when fine-grained: the estimate is first pulled (ratio 0.70) then pinned to zero (0.03), and a temporal median restores 0.998. The dt cliff is pair loss, not the quarter rule: removing the search limit leaves the cliff at the same k=4.*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/02_frames_oblique_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/02_frames_oblique.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_river_surface_velocity.py
```

Source: [examples/poc_river_surface_velocity.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_river_surface_velocity.py)

Ops used (notes): [`highpass_image`](https://furuse.work/ops/2d/frequency/highpass_image.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`piv_ensemble_correlate`](https://furuse.work/ops/piv/estimate/piv_ensemble_correlate.html) · [`piv_error_stats`](https://furuse.work/ops/piv/assess/piv_error_stats.html) · [`piv_outlier_mask`](https://furuse.work/ops/piv/validate/piv_outlier_mask.html) · [`piv_replace_outliers`](https://furuse.work/ops/piv/validate/piv_replace_outliers.html) · [`piv_sample_at_windows`](https://furuse.work/ops/piv/assess/piv_sample_at_windows.html) · [`piv_to_velocity`](https://furuse.work/ops/piv/field/piv_to_velocity.html) · [`sigma_clip_stack`](https://furuse.work/ops/astrostack/stack/sigma_clip_stack.html) · [`warp_by_plane`](https://furuse.work/ops/3d/plane_sweep_stereo/warp_by_plane.html)

## 45. Change detection under misregistration — false positives are edge bands, with a cliff

[![Change detection under misregistration — false positives are edge bands, with a cliff](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/03_map_fp_shift_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/03_map_fp_shift.png)

*↑ **Change detection under misregistration — false positives are edge bands, with a cliff** ―― A two-date synthetic land surface (fields, roads, buildings, forest, lake) with planted changes (new buildings, clear-cut, lake expansion); date 2 is degraded by sub-pixel shift, small rotation and an illumination change, and the false-positive area of plain differencing is measured. False positives stay at the noise floor up to 0.3 px and jump at 0.5 px (matching the PSF-derived onset δ*=τσ√2π/C=0.351 px), reaching 7175 px at 3 px. The edge-length × shift rule gives 0.78× at 3 px but cannot explain the cliff; the PSF+noise edge-ledger prediction is within 0.84–1.07×. Three registration paths (PIV, keypoints, LK) bring the residual down to 0.02–0.13 px, but the only phase-correlation path is 3-D and integer-valued (residual 0.72 px), and its 995 px of false positives lands on the shift-only sweep read at the same residual (915 px). Clear-cut recall is 0.33 even with perfect alignment; the illumination-only 17198 px vanish with radiometric normalisation while the 3497 px from shift do not.*

[![0.35 px までゼロ、そこから立ち上がる。比例則は崖を説明しない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/01_plot_fp_vs_shift_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/01_plot_fp_vs_shift.png)

*↑ The measurement ―― 0.35 px までゼロ、そこから立ち上がる。比例則は崖を説明しない。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_change_detection_misreg.py
```

Source: [examples/poc_change_detection_misreg.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_change_detection_misreg.py)

Ops used (notes): [`affine_trans_image`](https://furuse.work/ops/2d/geometry/affine_trans_image.html) · [`histogram_match`](https://furuse.work/ops/colortransport/matching/histogram_match.html) · [`match_phase_3d`](https://furuse.work/ops/3d/match_pose/match_phase_3d.html) · [`opening_circle`](https://furuse.work/ops/2d/region/opening_circle.html) · [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`piv_outlier_mask`](https://furuse.work/ops/piv/validate/piv_outlier_mask.html) · [`procrustes_fit`](https://furuse.work/ops/shapestat/procrustes/procrustes_fit.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html) · [`voxel_iou`](https://furuse.work/ops/3d/metrics/voxel_iou.html)

## 46. Leaf disease severity — colour axes survive the lighting; the grade is decided by the leaf mask and the edge convention

[![Leaf disease severity — colour axes survive the lighting; the grade is decided by the leaf mask and the edge convention](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/01_scene.png)

*↑ **Leaf disease severity — colour axes survive the lighting; the grade is decided by the leaf mask and the edge convention** ―― A closed-form leaf outline with lesions of known area, over soil, side lighting, clipped highlights and a shadow, gives ground truth for disease severity (lesion pixels / leaf pixels). A fixed threshold on the green channel (the zero point) is off by +65.2 pt with soil alone; cutting the leaf with the illuminant-projected G and the lesions with Lab a* lands at -0.8 pt on the standard scene. Illumination falloff up to 50 % does not move a*, but clipped highlights produce only false positives for a* (+12.6 pt at 20 % coverage, 0.0 false negatives) versus +2.0 pt for hue, which is invariant to added white. With a 4 px soft lesion edge, choosing the 25 % or 75 % opacity contour as the boundary alone shifts the severity by ±3.5 pt (predicted within 0.4 pt by Steiner's formula), and of 40 images placed within ±3 pt of a grade boundary, 19-35 are misgraded on soil by every method — on black cloth with a brightness leaf mask, a fixed hue threshold misgrades 8.*

[![FN(青)の大きな塊は影と鏡面反射が重なった病斑(葉マスクごと落ちる)。FP(赤)は鏡面反射の下と病斑の縁。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/02_error_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/02_error_map.png)

*↑ The measurement ―― FN(青)の大きな塊は影と鏡面反射が重なった病斑(葉マスクごと落ちる)。FP(赤)は鏡面反射の下と病斑の縁。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_leaf_disease_area.py
```

Source: [examples/poc_leaf_disease_area.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_leaf_disease_area.py)

Ops used (notes): [`access_channel`](https://furuse.work/ops/2d/color/access_channel.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`fill_holes`](https://furuse.work/ops/2d/region/fill_holes.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`linear_to_srgb`](https://furuse.work/ops/gfx2d/colorspace/linear_to_srgb.html) · [`reg_close`](https://furuse.work/ops/2d/region/reg_close.html) · [`reg_erode`](https://furuse.work/ops/2d/region/reg_erode.html) · [`rgb_to_lab`](https://furuse.work/ops/imgmetrics/colorspace/rgb_to_lab.html) · [`select_largest`](https://furuse.work/ops/2d/region/select_largest.html) · [`sk_otsu`](https://furuse.work/ops/2d/segmentation/sk_otsu.html) · [`specular_free_transform`](https://furuse.work/ops/specular/dichromatic/specular_free_transform.html) · [`srgb_to_linear`](https://furuse.work/ops/gfx2d/colorspace/srgb_to_linear.html) · [`trans_from_rgb`](https://furuse.work/ops/2d/color/trans_from_rgb.html)

## 47. Counting tree rings and extracting the width series — ring count and width correlation fail separately

[![Counting tree rings and extracting the width series — ring count and width correlation fail separately](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/01_scene.png)

*↑ **Counting tree rings and extracting the width series — ring count and width correlation fail separately** ―― A 36-ring disc is synthesised in closed form with an off-centre pith, eccentric growth, circumferential wobble, wandering cracks, decay spots, grain texture and blur. A single-ray peak count (baseline) gets the ring count right in only 18 of 24 directions, yet the 6 wrong directions still give a width-series correlation of median 0.900. The consensus method (pith-centred polar unwrap, radius normalised by the disc edge, theta-median, 24 sector measure lines, median) returns exactly 36 rings, 0 missing, width correlation 0.996 (mean error 0.13 px). A 20 px pith error leaves the width correlation at 0.994: the cosine modulation lands on the radii (slope -14.9 px), not on the widths (-0.02 px); what it removes is the innermost rings (predicted 2 / measured 2). The thinnest ring is lost at 2.5 px (consensus) and 3.0 px (baseline), and at blur sigma 4 px the baseline counts 13 false rings.*

[![偏心成長で境界が θ とともに斜めに走るので、正規化しないとθ 窓の中で外側の年輪がにじむ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/02_polar_stages_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/02_polar_stages.png)

*↑ The measurement ―― 偏心成長で境界が θ とともに斜めに走るので、正規化しないとθ 窓の中で外側の年輪がにじむ。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_tree_ring_dendro.py
```

Source: [examples/poc_tree_ring_dendro.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_tree_ring_dendro.py)

Ops used (notes): [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`median_rect`](https://furuse.work/ops/2d/rank/median_rect.html) · [`polar_unwrap`](https://furuse.work/ops/3d/curvilinear/polar_unwrap.html)

### The Image Quality and Restoration Wing — Looking Better and Getting Closer to the Truth Are Different Things

Deblurring, upscaling, dehazing, focus stacking, reconstructing from projections, ranging by counting photons. Restoration is where 'it looks better' and 'it is closer to the truth' are most easily confused. The seven exhibits here synthesise the kernel, the depth, the airlight, the PSD, the projections and the arrival time themselves, so the two can be scored separately.

Appearance metrics do not peak at the truth: a hazy input has higher contrast than the true scene; unsharp masking matches the true gradient energy while PSNR drops; adding noise raises PSNR. Conversely, a method can restore stripes finer than Nyquist while PSNR moves by only -0.01 dB.

The null baseline placed throughout is 'do nothing'. Deblurring with the kernel angle off by 19.4 degrees, FBP from 12 projections, dehazing at visibility above 782 m, depth in textureless regions: each loses to that baseline. Stating the losing conditions in numbers is what this room is for.

## 48. How Much Camera Shake Can Be Undone — Make the Kernel, Apply It, Invert It, Compare

[![How Much Camera Shake Can Be Undone — Make the Kernel, Apply It, Invert It, Compare](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/01_noise_ceiling_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/01_noise_ceiling.png)

*↑ **How Much Camera Shake Can Be Undone — Make the Kernel, Apply It, Invert It, Compare** ―― A known linear blur kernel applied and inverted, with the ceiling set by noise and by kernel estimation error. Without noise the image recovers from 22.38 to 56.41 dB; at 20 dB SNR the gain is 1.82 dB. A kernel angle off by 19.4 degrees is beaten by doing nothing, and undoing rotational blur with a single kernel makes the centre of rotation worse by -49.41 dB.*

[![4 枚目は「復元した」形をしているが、ゼロ点(観測そのもの)より悪い。絵の見た目では区別できない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/02_deblur_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/02_deblur.png)

*↑ The measurement ―― 4 枚目は「復元した」形をしているが、ゼロ点(観測そのもの)より悪い。絵の見た目では区別できない。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_camera_shake_deblur.py
```

Source: [examples/poc_camera_shake_deblur.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_camera_shake_deblur.py)

Ops used (notes): [`psnr`](https://furuse.work/ops/imgmetrics/fidelity/psnr.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`ssim`](https://furuse.work/ops/imgmetrics/fidelity/ssim.html) · [`unsharp`](https://furuse.work/ops/2d/smoothing/unsharp.html) · [`vol_richardson_lucy`](https://furuse.work/ops/3d/restoration/vol_richardson_lucy.html)

## 49. Does Super-Resolution Add Information? Downsample With the Truth in Hand, Restore, Count

[![Does Super-Resolution Add Information? Downsample With the Truth in Hand, Restore, Count](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/03_multiframe_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/03_multiframe.png)

*↑ **Does Super-Resolution Add Information? Downsample With the Truth in Hand, Restore, Count** ―― Observations made by downsampling the truth, with single-image upscaling, iterative back-projection and drizzle scored on a resolution table. No single-image upscaler beats the bicubic null by more than +0.036 dB. Drizzling 16 sub-pixel-shifted frames gains +13.96 dB in the undersampled condition, and the modulation of a period-6 pattern beyond Nyquist rises from 0.03 to 0.38.*

[![鮮鋭化だけがナイキスト(周期 8)より細かい列にも縞を作る。それは分解能ではなく**無い縞**。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/01_upscale_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/01_upscale.png)

*↑ The measurement ―― 鮮鋭化だけがナイキスト(周期 8)より細かい列にも縞を作る。それは分解能ではなく**無い縞**。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_superresolution_limits.py
```

Source: [examples/poc_superresolution_limits.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_superresolution_limits.py)

Ops used (notes): [`drizzle_resample`](https://furuse.work/ops/astrostack/stack/drizzle_resample.html) · [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`psnr`](https://furuse.work/ops/imgmetrics/fidelity/psnr.html) · [`ssim`](https://furuse.work/ops/imgmetrics/fidelity/ssim.html) · [`unsharp`](https://furuse.work/ops/2d/smoothing/unsharp.html) · [`vol_fft_lowpass`](https://furuse.work/ops/3d/frequency/vol_fft_lowpass.html) · [`vol_resize`](https://furuse.work/ops/3d/geom_transform/vol_resize.html) · [`volume_downsample`](https://furuse.work/ops/3d/preprocess/volume_downsample.html)

## 50. Removing Haze — Ground Truth From the Scattering Model, Transmission and Airlight Scored Apart

[![Removing Haze — Ground Truth From the Scattering Model, Transmission and Airlight Scored Apart](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/01_scene.png)

*↑ **Removing Haze — Ground Truth From the Scattering Model, Transmission and Airlight Scored Apart** ―― A hazy image built from depth, airlight and extinction so that the true transmission and the true scene are both known, then dehazed and scored. The overall +4.04 dB hides a -1.49 dB degradation of the near field covered by +4.03 dB mid and +11.28 dB far. Above 782 m visibility dehazing does harm, and adding noise raises PSNR (an accidental cancellation).*

[![空では過大評価(明るい側)、近景では過小評価(暗い側)。全体の平均バイアスでは打ち消し合って見えない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/02_transmission_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/02_transmission.png)

*↑ The measurement ―― 空では過大評価(明るい側)、近景では過小評価(暗い側)。全体の平均バイアスでは打ち消し合って見えない。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_dehazing.py
```

Source: [examples/poc_dehazing.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dehazing.py)

Ops used (notes): [`clahe`](https://furuse.work/ops/2d/gray/clahe.html) · [`equalize`](https://furuse.work/ops/2d/gray/equalize.html) · [`image_entropy`](https://furuse.work/ops/imgmetrics/information/image_entropy.html) · [`joint_bilateral`](https://furuse.work/ops/3d/depth_denoise/joint_bilateral.html) · [`psnr`](https://furuse.work/ops/imgmetrics/fidelity/psnr.html) · [`rank_image`](https://furuse.work/ops/2d/rank/rank_image.html) · [`ssim`](https://furuse.work/ops/imgmetrics/fidelity/ssim.html)

## 51. Focus Stacking — The All-in-Focus Image and the Depth Map Are Different Things

[![Focus Stacking — The All-in-Focus Image and the Depth Map Are Different Things](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/01_stack_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/01_stack.png)

*↑ **Focus Stacking — The All-in-Focus Image and the Depth Map Are Different Things** ―― An all-in-focus image and a depth map pulled from 15 frames blurred by the closed-form circle of confusion. The all-in-focus image reaches 35.89 dB (null 20.98 dB), yet the depth from the same fusion loses to the null by 8x (0.13x) in textureless regions. A relative confidence scores 0.9923 there, higher than the 0.9630 of textured regions; rejecting by absolute value (23600x apart) brings the RMS from 1.505 to 0.878 mm.*

[![左下の無テクスチャの四角だけ、誤差が掃引全域にばらけた乱数になっている(段差帯のハローも見える)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/02_depth_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/02_depth_map.png)

*↑ The measurement ―― 左下の無テクスチャの四角だけ、誤差が掃引全域にばらけた乱数になっている(段差帯のハローも見える)。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_focus_stacking.py
```

Source: [examples/poc_focus_stacking.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_focus_stacking.py)

Ops used (notes): [`csi_height_map`](https://furuse.work/ops/interferometry/surface/csi_height_map.html) · [`defocus_blur`](https://furuse.work/ops/optics/scene/defocus_blur.html) · [`dilation_circle`](https://furuse.work/ops/2d/region/dilation_circle.html) · [`fuse`](https://furuse.work/ops/3d/tsdf_fusion/fuse.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`laplace`](https://furuse.work/ops/2d/edges/laplace.html) · [`mean_image`](https://furuse.work/ops/2d/smoothing/mean_image.html) · [`optical_camera`](https://furuse.work/ops/optics/scene/optical_camera.html) · [`psnr`](https://furuse.work/ops/imgmetrics/fidelity/psnr.html) · [`sobel_amp`](https://furuse.work/ops/2d/edges/sobel_amp.html) · [`xcv2_lap_var`](https://furuse.work/ops/2d/features/xcv2_lap_var.html)

## 52. Where CT Reconstruction Starts to Break as Projections Are Removed

[![Where CT Reconstruction Starts to Break as Projections Are Removed](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_fidelity/01_recon_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_fidelity/01_recon_sweep.png)

*↑ **Where CT Reconstruction Starts to Break as Projections Are Removed** ―― Shepp-Logan re-imaged with 180 down to 12 projections, FBP placed beside two nulls: a blank image and unfiltered back-projection. With 12 projections FBP (RMSE 0.2576) is worse than the blank image (0.2420). A check that never looks at the reconstruction — the row sums of the sinogram — caught a -3.34 % mass loss that RMSE could not see; fixing the ramp filter's DC bin brought it to -0.0099 %.*

[![RMSE で見ると 12 本は空白画像 0.2420 より悪い。相関とストリークは別のことを言う。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_fidelity/02_fidelity_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_fidelity/02_fidelity_table.png)

*↑ The measurement ―― RMSE で見ると 12 本は空白画像 0.2420 より悪い。相関とストリークは別のことを言う。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_ct_fidelity.py
```

Source: [examples/poc_ct_fidelity.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_fidelity.py)

Ops used (notes): [`backproject_sinogram`](https://furuse.work/ops/tomography/reconstruct/backproject_sinogram.html) · [`ellipse_phantom`](https://furuse.work/ops/tomography/forward/ellipse_phantom.html) · [`ellipse_sinogram`](https://furuse.work/ops/tomography/forward/ellipse_sinogram.html) · [`filtered_backprojection`](https://furuse.work/ops/tomography/reconstruct/filtered_backprojection.html) · [`projection_angles`](https://furuse.work/ops/tomography/layout/projection_angles.html) · [`radon_transform`](https://furuse.work/ops/tomography/forward/radon_transform.html) · [`rmse`](https://furuse.work/ops/imgmetrics/fidelity/rmse.html) · [`ssim`](https://furuse.work/ops/imgmetrics/fidelity/ssim.html) · [`stat_correlation`](https://furuse.work/ops/math/stats/stat_correlation.html)

## 53. Depth From a Light Field — A Light Field of Known Depth, Confronted With Its Nulls

[![Depth From a Light Field — A Light Field of Known Depth, Confronted With Its Nulls](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/01_scene_and_depth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/01_scene_and_depth.png)

*↑ **Depth From a Light Field — A Light Field of Known Depth, Confronted With Its Nulls** ―― A 9×9 light field rendered by analytic inverse mapping, with focus-measure, EPI-slope and two-view block matching scored against the true slope map. The winner beats the constant null by 22x, but beats two-view matching — which uses only 2 of the 81 views — by just 1.6x, and only with cubic interpolation. The default linear interpolation snaps to integer slopes, reading a true 1.30 as 1.4750 (11.9 % in depth).*

[![linear は 1.08/1.15 を 1.0 へ、1.85 を 2.0 側へ引く。cubic は恒等線に乗る。生成側の補間はゼロ(Fourier シフト)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/02_focus_snapping_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/02_focus_snapping.png)

*↑ The measurement ―― linear は 1.08/1.15 を 1.0 へ、1.85 を 2.0 側へ引く。cubic は恒等線に乗る。生成側の補間はゼロ(Fourier シフト)。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_lightfield_depth.py
```

Source: [examples/poc_lightfield_depth.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_lightfield_depth.py)

Ops used (notes): [`lf_depth_from_focus`](https://furuse.work/ops/lightfield/depth/lf_depth_from_focus.html) · [`lf_disparity_to_depth`](https://furuse.work/ops/lightfield/depth/lf_disparity_to_depth.html) · [`lf_epi`](https://furuse.work/ops/lightfield/views/lf_epi.html) · [`lf_epi_slope`](https://furuse.work/ops/lightfield/depth/lf_epi_slope.html) · [`lf_refocus`](https://furuse.work/ops/lightfield/refocus/lf_refocus.html)

## 54. Ranging by Counting Photons — How Many for How Many Millimetres?

[![Ranging by Counting Photons — How Many for How Many Millimetres?](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/01_histograms_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/01_histograms.png)

*↑ **Ranging by Counting Photons — How Many for How Many Millimetres?** ―― Range read from an arrival-time histogram built by bin-integrating a Gaussian at the round-trip time and drawing Poisson samples. With 200 photons the raw peak position errs by 11.02 mm and the gated centroid by 2.29 mm, riding the 31.83 mm/√N bound at 1.00 to 1.07x. With background the plain centroid collapses by two orders (564 mm at SBR 0.031), and the family's recommended Gaussian fit at 8.82 mm loses to a gated centroid a user can write in six lines.*

[![背景が無ければ素の重心で足りる。背景が入ると 2 桁崩れ、docstring が勧める背景減算でも戻らない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/02_methods_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/02_methods.png)

*↑ The measurement ―― 背景が無ければ素の重心で足りる。背景が入ると 2 桁崩れ、docstring が勧める背景減算でも戻らない。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_dtof_ranging.py
```

Source: [examples/poc_dtof_ranging.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dtof_ranging.py)

Ops used (notes): [`dtof_cube_depth`](https://furuse.work/ops/photon/dtof/dtof_cube_depth.html) · [`dtof_cube_simulate`](https://furuse.work/ops/photon/dtof/dtof_cube_simulate.html) · [`dtof_depth`](https://furuse.work/ops/photon/dtof/dtof_depth.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`tcspc_background_subtract`](https://furuse.work/ops/photon/tcspc/tcspc_background_subtract.html) · [`tcspc_coates_correct`](https://furuse.work/ops/photon/spad/tcspc_coates_correct.html) · [`tcspc_simulate`](https://furuse.work/ops/photon/tcspc/tcspc_simulate.html)

### The Time-as-3-D Wing — A Video Is One Volume

Treat a 2-D video as one (t, y, x) volume and the 3-D ops — connected components, isosurfaces, region properties — work along time unchanged. Merging colonies become a Y in space-time, passing vehicles become bands in a (t, x) image, a wavefront's arrival time becomes an isosurface. The six exhibits here demonstrate exactly that.

The time axis also brings its own traps. Rounding onto the frame grid always delays; pixel area makes merging look early. Mislinks come in two opposite kinds, so a single error rate cannot say which way the diffusion coefficient is wrong. Template tracking drifts quietly before it ever loses the target, and all 152 drifted frames report 'found'.

The motion-magnification exhibit carries the most candid conclusion in the room: exact to machine precision up to a magnification of 200, and of no help for measurement. Magnification is a tool for showing people, not for measuring.

## 55. A Growth Time-Lapse as Space-Time Connected Components

[![A Growth Time-Lapse as Space-Time Connected Components](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/01_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/01_frames.png)

*↑ **A Growth Time-Lapse as Space-Time Connected Components** ―― A video of colonies spreading and merging, read as a (t, y, x) volume with 3-D connected components. Pixel area makes merging look early (-1.16 frames for pair 0-1) while rounding onto the frame grid makes it look late (+0.94); the two oppose, so the sum looks small. The default 26-connectivity of `vol_label` merged a near miss with a gap of 0.92.*

[![縦が時間(下向き、4 倍に拡大)、横が列。2 本の管が合わさる高さがそのまま合体時刻。色は 3-D ラベル。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/02_ystructure_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/02_ystructure.png)

*↑ The measurement ―― 縦が時間(下向き、4 倍に拡大)、横が列。2 本の管が合わさる高さがそのまま合体時刻。色は 3-D ラベル。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_timelapse_growth.py
```

Source: [examples/poc_timelapse_growth.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_timelapse_growth.py)

Ops used (notes): [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_region_props`](https://furuse.work/ops/3d/regionprops/vol_region_props.html)

## 56. Counting in (x, y, t) — Vehicles Passed, Occlusion, and One Constant: L/V

[![Counting in (x, y, t) — Vehicles Passed, Occlusion, and One Constant: L/V](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/01_per_frame_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/01_per_frame.png)

*↑ **Counting in (x, y, t) — Vehicles Passed, Occlusion, and One Constant: L/V** ―― A synthetic traffic video counted per frame, by a virtual loop, and by connected components in a (t, x) slit image. The per-frame maximum reports 7 for 10 vehicles passed — it measures a different quantity. All three failure conditions are written with one constant, vehicle length over speed = L/V (9.0 frames); at a frame interval of 16 the bands fragment and 10 vehicles become 49.*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/02_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/02_scene.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_traffic_counting.py
```

Source: [examples/poc_traffic_counting.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_traffic_counting.py)

Ops used (notes): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html)

## 57. The Arrival-Time Surface as an Isosurface in (x, y, t)

[![The Arrival-Time Surface as an Isosurface in (x, y, t)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/01_dt_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/01_dt_sweep.png)

*↑ **The Arrival-Time Surface as an Isosurface in (x, y, t)** ―― The arrival-time surface of wavefronts spreading from point sources, extracted as an isosurface of the (x, y, t) volume. The null (first frame above threshold) is biased by Δt/2, which more frames cannot remove; linear sub-frame interpolation is 27x better (0.0209 ms). Parabolic interpolation loses to linear, and linear is at its best (a 3.8x margin) when the threshold sits at the Gaussian's inflection point θ = 0.6065.*

[![変曲点 θ=0.6065 では線形が 3.8 倍勝ち、θ=0.2 では放物線が 3.6 倍勝つ。交点は θ≈0.35 と θ≈0.75。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/02_threshold_crossover_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/02_threshold_crossover.png)

*↑ The measurement ―― 変曲点 θ=0.6065 では線形が 3.8 倍勝ち、θ=0.2 では放物線が 3.6 倍勝つ。交点は θ≈0.35 と θ≈0.75。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_xyt_event_surface.py
```

Source: [examples/poc_xyt_event_surface.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_xyt_event_surface.py)

Ops used (notes): [`vertex_normals`](https://furuse.work/ops/3d/mesh_process/vertex_normals.html) · [`vol_edge_probe`](https://furuse.work/ops/3d/probe/vol_edge_probe.html)

## 58. Particle Tracking as a (row, column, time) Volume — Mislinks Come in Two Directions

[![Particle Tracking as a (row, column, time) Volume — Mislinks Come in Two Directions](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/01_spacetime_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/01_spacetime.png)

*↑ **Particle Tracking as a (row, column, time) Volume — Mislinks Come in Two Directions** ―― A video of 400 particles tracked, with the diffusion coefficient D read from the trajectories. Ambiguous mislinks pull D down to 0.925x; mislinks caused by missing targets push it up to 3.429x in the same video — one error rate cannot tell you the direction. What helps is not a one-to-one constraint but a single line imposing a maximum link distance (3.429 → 1.304).*

[![縦軸は常用対数(0 が真値)。欠測は遠い他人を掴んで D を上げ、曖昧は近い相手を選んで D を下げる。上限距離のゲート 1 行で上向きの暴走が 1/2.6 に。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/02_density_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/02_density_bias.png)

*↑ The measurement ―― 縦軸は常用対数(0 が真値)。欠測は遠い他人を掴んで D を上げ、曖昧は近い相手を選んで D を下げる。上限距離のゲート 1 行で上向きの暴走が 1/2.6 に。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_particle_tracking.py
```

Source: [examples/poc_particle_tracking.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_particle_tracking.py)

Ops used (notes): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_local_maxima`](https://furuse.work/ops/3d/feature/vol_local_maxima.html)

## 59. Template Tracking Drifts Quietly Before It Ever Loses the Target

[![Template Tracking Drifts Quietly Before It Ever Loses the Target](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/01_ncc_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/01_ncc_maps.png)

*↑ **Template Tracking Drifts Quietly Before It Ever Loses the Target** ―― A camera moved by a known similarity transform, exposing the three ways template tracking fails: losing the target, drifting quietly, and being confidently wrong. All 152 of the 152 drifted frames passed the peak threshold calibrated without occlusion and reported 'found'. The only absolute quantity measurable without ground truth is forward-backward inconsistency.*

[![同じ遮蔽率でも、そっくりな別物体が視野に居るだけで崖がはるかに手前へ来る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/02_occlusion_vs_twin_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/02_occlusion_vs_twin.png)

*↑ The measurement ―― 同じ遮蔽率でも、そっくりな別物体が視野に居るだけで崖がはるかに手前へ来る。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_template_tracking.py
```

Source: [examples/poc_template_tracking.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_template_tracking.py)

Ops used (notes): [`ncc_locate`](https://furuse.work/ops/2d/matching/ncc_locate.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`shape_locate`](https://furuse.work/ops/2d/matching/shape_locate.html)

## 60. Micro-Vibration of a Structure From Video — Does Motion Magnification Help You Measure?

[![Micro-Vibration of a Structure From Video — Does Motion Magnification Help You Measure?](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/01_slit_scan_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/01_slit_scan.png)

*↑ **Micro-Vibration of a Structure From Video — Does Motion Magnification Help You Measure?** ―― A vibration of known amplitude 0.02 px at 3.7 Hz, synthesised to test whether motion magnification helps measurement. Exact to machine precision up to α = 200. But magnification does not improve measurement precision — multiplying the phase by α multiplies the noise by α. On a cantilever, phase correlation returns 0.15 px, the area average of 0.30 and 0.00 px, a number that exists nowhere.*

[![剛体を仮定する位相相関が返す 0.150 px は 0.30 と 0.00 の面積平均で、どの列の真値とも違う。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/02_beam_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/02_beam_profile.png)

*↑ The measurement ―― 剛体を仮定する位相相関が返す 0.150 px は 0.30 と 0.00 の面積平均で、どの列の真値とも違う。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_motion_magnification.py
```

Source: [examples/poc_motion_magnification.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_motion_magnification.py)

Ops used (notes): [`band_snr`](https://furuse.work/ops/motionmag/temporal/band_snr.html) · [`displacement_series`](https://furuse.work/ops/motionmag/measure/displacement_series.html) · [`motion_magnify`](https://furuse.work/ops/motionmag/magnify/motion_magnify.html) · [`phase_displacement`](https://furuse.work/ops/motionmag/measure/phase_displacement.html) · [`synthesize_translation`](https://furuse.work/ops/motionmag/synthesis/synthesize_translation.html) · [`temporal_band_power`](https://furuse.work/ops/motionmag/temporal/temporal_band_power.html) · [`temporal_bandpass`](https://furuse.work/ops/motionmag/temporal/temporal_bandpass.html)

## 61. Modal identification from video — frequency survives to the end, damping lies first

[![Modal identification from video — frequency survives to the end, damping lies first](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/01_scene.png)

*↑ **Modal identification from video — frequency survives to the end, damping lies first** ―― A cantilever beam (closed-form Euler–Bernoulli modes) decaying freely in three modes is rendered into video with sensor noise, 100 Hz lighting flicker, camera shake and rolling shutter, then identified with phase-based displacement (phase_displacement) and PIV (piv_cross_correlate). All three natural frequencies come out within 0.06 Hz, but the damping ratio of mode 1 from the very same series is 0.0778 (half-power), 0.0188 (envelope) or 0.0181 (fit) against a true 0.02. Sweeping the amplitude from 0.02 to 2 px, the quantities break in the order f → ζ → MAC_2 → MAC_3: at 0.02 px the phase method still has f_1 within +0.030 Hz while ζ_1 is 0.23 of the truth. At 48.5 fps the flicker alias lands exactly on f_1 = 3.00 Hz; a single-pixel brightness zero-point cannot report ζ at all, while the phase method survives at 0.0191.*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/02_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/02_frames.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_beam_modal_video.py
```

Source: [examples/poc_beam_modal_video.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_beam_modal_video.py)

Ops used (notes): [`phase_displacement`](https://furuse.work/ops/motionmag/measure/phase_displacement.html) · [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`temporal_bandpass`](https://furuse.work/ops/motionmag/temporal/temporal_bandpass.html)

## 62. Where the Warehouse Dwell Came From — Count Waiting Without Its Kind and Everything Is Just Congestion

[![Where the Warehouse Dwell Came From — Count Waiting Without Its Kind and Everything Is Just Congestion](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/09_scene_layout_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/09_scene_layout.png)

*↑ **Where the Warehouse Dwell Came From — Count Waiting Without Its Kind and Everything Is Just Congestion** ―― A synthetic warehouse floor plan with 26 tracked workers and AGVs, in which replenishment waits, queueing, aisle interference, system waits and stockouts were planted with known times and durations, then read as one (t, y, x) volume. Of the naive 321.5 s of "total dwell", only 198.0 s (61.6 %) is real waiting; the rest is productive work and creep. Removing all queueing or all aisle interference moves that single number by -39.0 s versus -38.0 s, so it cannot say which to fix, while the per-kind counts drop to zero only for the kind that was removed. A stockout moves dwell by -17.0 s but adds 94.6 m of walking, and the three degradation axes each kill a different kind: sampling interval kills the short waits, occlusion kills the waits pressed against racks, and ID merging kills the two kinds defined by a relation between two people.*

[![ヒートマップは場所を当てるが、「1 人が長く待った」と「何人も短く止まった」を分けない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/01_heat_ambiguity_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/01_heat_ambiguity.png)

*↑ The measurement ―― ヒートマップは場所を当てるが、「1 人が長く待った」と「何人も短く止まった」を分けない。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_warehouse_flow.py
```

Source: [examples/poc_warehouse_flow.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_warehouse_flow.py)

Ops used (notes): [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`face_areas`](https://furuse.work/ops/3d/mesh_process/face_areas.html) · [`mesh_volume`](https://furuse.work/ops/3d/mesh_process/mesh_volume.html) · [`occupancy_grid`](https://furuse.work/ops/3d/occupancy/occupancy_grid.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`vol_dilate`](https://furuse.work/ops/2d/3d/vol_dilate.html) · [`vol_erode`](https://furuse.work/ops/2d/3d/vol_erode.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_opening_ball`](https://furuse.work/ops/2d/3d/vol_opening_ball.html) · [`vol_region_props`](https://furuse.work/ops/3d/regionprops/vol_region_props.html)

### The Geometry and Calibration Wing — A Small Residual Is Not Proof of Correctness

Reprojection error in camera calibration, seam mismatch in a panorama, residual in point-cloud registration: all are read as 'smaller is better'. The three exhibits here, with ground truth in hand, show where that reading fails.

Reprojection RMS of 0.0688–0.0690 px alongside focal-length errors of 0.026–7.334 %. Adjacent seams at 0.12 px while the single closing seam opens by 1.5 px. Spheres and cylinders converging to the same residual with an arbitrary pose. Least squares drives the residual down to the noise; whether it lands on the truth is a separate question.

A trap in the measuring procedure itself is kept on display: fix one point cloud and sweep only the pose, and you still have a sample of one — the random seed alone produced both '0 % quadrant errors' and '100 %'. About the only absolute quantity measurable without ground truth is the loop-closure error of a full 360-degree sweep.

## 63. A Reprojection Error of 0.05 px Guarantees Nothing

[![A Reprojection Error of 0.05 px Guarantees Nothing](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/03_frame_fill_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/03_frame_fill.png)

*↑ **A Reprojection Error of 0.05 px Guarantees Nothing** ―― Grid points projected with known intrinsics and poses, re-calibrated, and the error split by component. With the board tilted 32 / 8 / 2 degrees the reprojection RMS spans 0.0688 to 0.0690 px (ratio 1.00) while the focal-length error spans 0.026 to 7.334 % (281x). With a distorting camera the degeneracy gate never fires, and the non-linear optimiser returns an answer even for a fronto-parallel board.*

[![RMS は 1.00 倍しか動かないのに fx 誤差は 281 倍動く。配置の良し悪しを映すのは sigma_fx のほう。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/01_reproj_vs_truth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/01_reproj_vs_truth.png)

*↑ The measurement ―― RMS は 1.00 倍しか動かないのに fx 誤差は 281 倍動く。配置の良し悪しを映すのは sigma_fx のほう。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_camera_calibration.py
```

Source: [examples/poc_camera_calibration.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_camera_calibration.py)

Ops used (notes): [`project_points`](https://furuse.work/ops/3d/render/project_points.html) · [`reprojection_error`](https://furuse.work/ops/3d/pose_estimation/reprojection_error.html)

## 64. Chain the Neighbours Together and You Cannot Get Back Where You Started

[![Chain the Neighbours Together and You Cannot Get Back Where You Started](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/01_seams_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/01_seams.png)

*↑ **Chain the Neighbours Together and You Cannot Get Back Where You Started** ―― 36 frames cut from a cylindrical panorama by a known rotation sequence and chained pairwise around a full turn. Adjacent seams agree to 0.12 px, yet the one closing seam opens by 1.5 px (13x). The buried `bundle_adjust_mosaic` did not beat the chain (30 of 36 frames were left as the identity); the worst pose error goes from 1.65 px for the chain to 0.56 px with global optimisation.*

[![系 2(等分)は閉ループ誤差を下げるのに姿勢はかえって悪化する。新しい観測を足さずに効くのは系 3。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/02_pose_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/02_pose_error.png)

*↑ The measurement ―― 系 2(等分)は閉ループ誤差を下げるのに姿勢はかえって悪化する。新しい観測を足さずに効くのは系 3。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_panorama_drift.py
```

Source: [examples/poc_panorama_drift.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_panorama_drift.py)

Ops used (notes): [`pose_error`](https://furuse.work/ops/3d/metrics/pose_error.html) · [`warp_by_plane`](https://furuse.work/ops/3d/plane_sweep_stereo/warp_by_plane.html)

## 65. The Convergence Basin of Point-Cloud Registration — How Far Off Can the Initial Pose Be?

[![The Convergence Basin of Point-Cloud Registration — How Far Off Can the Initial Pose Be?](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/01_basin_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/01_basin.png)

*↑ **The Convergence Basin of Point-Cloud Registration — How Far Off Can the Initial Pose Be?** ―― ICP success rate contoured against the initial pose error, with the point cloud re-sampled on every trial. With no translation offset, success drops below 50 % at 90 degrees for point-to-point and 120 degrees for point-to-plane. Spheres and cylinders converge to the same residual with an arbitrary pose; with the global method all 16 of 16 trials appear converged and the pose is wrong — undetectable from the residual.*

[![非対称性が消えると 4 候補が形として区別できず、選択が崩れる(選ばれた解が第 1 候補から離れる)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/02_pca_quadrant_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/02_pca_quadrant.png)

*↑ The measurement ―― 非対称性が消えると 4 候補が形として区別できず、選択が崩れる(選ばれた解が第 1 候補から離れる)。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_registration_basin.py
```

Source: [examples/poc_registration_basin.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_registration_basin.py)

Ops used (notes): [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`farthest_point_sampling`](https://furuse.work/ops/3d/geodesic/farthest_point_sampling.html) · [`rmse`](https://furuse.work/ops/imgmetrics/fidelity/rmse.html)

### The Colour and Separation Wing — There Is No Method That Works, Only Conditions Under Which One Does

Estimating the illuminant to restore colour, peeling the layers of a painting with multiple wavelengths, separating specular reflection with polarisation. The three exhibits here synthesise linear radiance from known spectral reflectances, known illuminants and the Fresnel equations, then compare the separation against that truth.

The conclusion in every case was that the failure axes are orthogonal. Max-RGB is best when a white patch is present and gets 8x worse when the single brightest patch is removed; grey-world shrugs off saturation but loses once chromatic content exceeds 20 %; under a reference illuminant every method loses to doing nothing; adding bands does not win, adding near-infrared does.

The shared warning is to convert to linear radiance before calling anything. Pass sRGB-gamma values and no exception is raised; the separation simply degrades in silence. Failure without an exception is the most common pattern in the whole museum.

## 66. Colour Constancy (White Balance) — No Method Works, Only Conditions Do

[![Colour Constancy (White Balance) — No Method Works, Only Conditions Do](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/01_casts_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/01_casts.png)

*↑ **Colour Constancy (White Balance) — No Method Works, Only Conditions Do** ―― Linear RGB synthesised from 24 known spectral reflectances and known illuminants, with illuminant estimation scored by recovery angular error. Max-RGB is best at a median of 1.06 degrees over 11 illuminants, but removing the single brightest patch takes it to 8.45 degrees, and tripling exposure to saturate 43 % of pixels takes it to 13.61 degrees, identical to doing nothing. Even a diagonal correction with the true illuminant leaves a mean ΔE00 of 5.07 at 2500 K.*

[![灰色世界はゼロ点(何もしない)の線を 0.1〜0.2 の間で上抜けする = そこから先は回すだけ損。白パッチ法には崖が無い。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/02_bias_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/02_bias_cliff.png)

*↑ The measurement ―― 灰色世界はゼロ点(何もしない)の線を 0.1〜0.2 の間で上抜けする = そこから先は回すだけ損。白パッチ法には崖が無い。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_white_balance.py
```

Source: [examples/poc_white_balance.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_white_balance.py)

Ops used (notes): [`delta_e_map`](https://furuse.work/ops/imgmetrics/colordiff/delta_e_map.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`illuminant_from_dichromatic_planes`](https://furuse.work/ops/specular/dichromatic/illuminant_from_dichromatic_planes.html) · [`laplace`](https://furuse.work/ops/2d/edges/laplace.html) · [`linear_to_srgb`](https://furuse.work/ops/gfx2d/colorspace/linear_to_srgb.html) · [`mean_image`](https://furuse.work/ops/2d/smoothing/mean_image.html) · [`prewitt_amp`](https://furuse.work/ops/2d/edges/prewitt_amp.html) · [`roberts`](https://furuse.work/ops/2d/edges/roberts.html) · [`sobel_amp`](https://furuse.work/ops/2d/edges/sobel_amp.html) · [`spectrum_to_srgb`](https://furuse.work/ops/optics/appearance/spectrum_to_srgb.html)

## 67. Peeling Layers With Many Wavelengths — Underdrawing, Ground, Glaze and Fading, Truth in Hand

[![Peeling Layers With Many Wavelengths — Underdrawing, Ground, Glaze and Fading, Truth in Hand](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/01_per_field_auc_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/01_per_field_auc.png)

*↑ **Peeling Layers With Many Wavelengths — Underdrawing, Ground, Glaze and Fading, Truth in Hand** ―― A spectral cube of ground, underdrawing, glaze and fading stacked in layers, then unmixed. Splitting the visible range into 16 bands does no better than RGB (recall 0.118 versus 0.119); what won was adding near-infrared. The same detector scores an AUC of 1.000 on ultramarine, 0.630 on azurite and 0.013 on losses — averaged, all of that vanishes. Restoring the unfaded colour barely beat the null, ΔE00 16.79 → 16.46.*

[![近赤外の差分は剥落部(楕円)で消え、近赤外 1 枚は面ごとに水準が違う。塗り分けは 1–99 分位でクリップした表示のみ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/02_detector_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/02_detector_maps.png)

*↑ The measurement ―― 近赤外の差分は剥落部(楕円)で消え、近赤外 1 枚は面ごとに水準が違う。塗り分けは 1–99 分位でクリップした表示のみ。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_pigment_unmixing.py
```

Source: [examples/poc_pigment_unmixing.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pigment_unmixing.py)

Ops used (notes): [`delta_e_map`](https://furuse.work/ops/imgmetrics/colordiff/delta_e_map.html) · [`linear_to_srgb`](https://furuse.work/ops/gfx2d/colorspace/linear_to_srgb.html) · [`spectrum_to_srgb`](https://furuse.work/ops/optics/appearance/spectrum_to_srgb.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html)

## 68. Stripping Specular Reflection With Polarisation — Truth From the Fresnel Equations

[![Stripping Specular Reflection With Polarisation — Truth From the Fresnel Equations](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/01_fresnel_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/01_fresnel.png)

*↑ **Stripping Specular Reflection With Polarisation — Truth From the Fresnel Equations** ―― Diffuse and specular components synthesised as s/p terms with the degree of polarisation from the Fresnel equations, and the separation scored against them. At 20 degrees of incidence the polarisation method wins by only 1.2x. The diffuse error matches the closed form R_p·E exactly and vanishes at the Brewster angle of 56.31 degrees — the diffuse term of `polarization_separate` is systematically high by that amount.*

[![実測と閉形式が重なる。70 度の絶対誤差は 20 度より悪いのに、ゼロ点比では 70 度が最良 —— 最適角は評価軸で割れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/02_angle_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/02_angle_error.png)

*↑ The measurement ―― 実測と閉形式が重なる。70 度の絶対誤差は 20 度より悪いのに、ゼロ点比では 70 度が最良 —— 最適角は評価軸で割れる。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_polarization_specular.py
```

Source: [examples/poc_polarization_specular.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_polarization_specular.py)

Ops used (notes): [`fresnel_reflectance`](https://furuse.work/ops/3d/optics/fresnel_reflectance.html) · [`polarization_dolp_map`](https://furuse.work/ops/specular/polarization/polarization_dolp_map.html) · [`polarization_render`](https://furuse.work/ops/specular/polarization/polarization_render.html) · [`polarization_separate`](https://furuse.work/ops/specular/polarization/polarization_separate.html) · [`polarization_stokes`](https://furuse.work/ops/specular/polarization/polarization_stokes.html) · [`rmse`](https://furuse.work/ops/imgmetrics/fidelity/rmse.html)

### The Forensics and Documents Wing — One Successful Image Is Not Evidence

Forgery detection and document rectification. Both tend to be presented through 'the one image where it was found' or 'the one page that came out straight'. The two exhibits here fix the paste location and quality, the homography and the lighting themselves, then score with a per-pixel ROC and pixel-level geometric error.

The forgery exhibit is on the detection (defensive) side. Forgeries are generated only because scoring a detector needs ground truth, and the generator is kept to the crudest form possible. What the exhibit shows most strongly is the fact that works against the detector: one press of the save button weakens every cue.

The document exhibit puts a number on a hole: two functions with the same name and different models can be swapped without an exception, returning a plausible picture with the keystone still in it. Shadow removal has no free lunch; the flatter the paper, the more of the faint text disappears.

## 69. Forgery Detection as an ROC — Not the One Image Found, but Detection at a Fixed False-Positive Rate

[![Forgery Detection as an ROC — Not the One Image Found, but Detection at a Fixed False-Positive Rate](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/01_score_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/01_score_maps.png)

*↑ **Forgery Detection as an ROC — Not the One Image Found, but Detection at a Fixed False-Positive Rate** ―― Ten forgeries made by pasting a JPEG q60 patch onto a q92 background and saving at q95, scored with a per-pixel ROC. ELA's single number points the opposite way from the textbook (paste / background = 0.58x), and an untouched image still yields an AUC of 0.797 from position bias alone. The ghost-valley depth reaches an AUC of 0.997, which falls to 0.975 after one whole-image recompression at q75.*

[![凡例の数字は AUC。乱数が対角線に乗ることで測り方に偏りが無いと言える。ゴーストA は乱数と重なる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/02_roc_tampered_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/02_roc_tampered.png)

*↑ The measurement ―― 凡例の数字は AUC。乱数が対角線に乗ることで測り方に偏りが無いと言える。ゴーストA は乱数と重なる。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_forensics_roc.py
```

Source: [examples/poc_forensics_roc.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_forensics_roc.py)

Ops used (notes): [`copy_move_regions`](https://furuse.work/ops/imgforensics/copy_move/copy_move_regions.html) · [`error_level_map`](https://furuse.work/ops/imgforensics/compression/error_level_map.html) · [`jpeg_ghost_map`](https://furuse.work/ops/imgforensics/compression/jpeg_ghost_map.html) · [`jpeg_ghost_quality`](https://furuse.work/ops/imgforensics/compression/jpeg_ghost_quality.html) · [`noise_inconsistency_map`](https://furuse.work/ops/imgforensics/noise/noise_inconsistency_map.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html)

## 70. Straightening a Hand-Held Document Photo — Keystone Correction and Shadow Removal Against Ground Truth

[![Straightening a Hand-Held Document Photo — Keystone Correction and Shadow Removal Against Ground Truth](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/01_rectify_zero_points_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/01_rectify_zero_points.png)

*↑ **Straightening a Hand-Held Document Photo — Keystone Correction and Shadow Removal Against Ground Truth** ―― A document imaged under a known homography and lighting, rectified, and scored by corner and grid error in pixels. The estimate reaches a grid RMS of 1.070 px (doing nothing: 37.376 px), but swapping in the same-named function with a different model (affine) is 32x worse and raises no exception. Shadow strength 0.45 gives a corner RMS of 5.72 px; 0.55 gives 65.10 px — a cliff.*

[![平坦・薄字・誤検出なしを同時に満たす行は 1 つも無い。窓 9 が fs.op で届く上限、窓 61 は自前。図の階調は真値で 217 段。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/02_shadow_tradeoff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/02_shadow_tradeoff.png)

*↑ The measurement ―― 平坦・薄字・誤検出なしを同時に満たす行は 1 つも無い。窓 9 が fs.op で届く上限、窓 61 は自前。図の階調は真値で 217 段。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_document_scan.py
```

Source: [examples/poc_document_scan.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_document_scan.py)

Ops used (notes): [`corner_response`](https://furuse.work/ops/2d/edges/corner_response.html) · [`dc_homomorphic`](https://furuse.work/ops/2d/decomposition/dc_homomorphic.html) · [`fill_holes`](https://furuse.work/ops/2d/region/fill_holes.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`get_region_contour`](https://furuse.work/ops/2d/region/get_region_contour.html) · [`gray_tophat`](https://furuse.work/ops/2d/morphology/gray_tophat.html) · [`illuminate`](https://furuse.work/ops/2d/gray/illuminate.html) · [`mean_image`](https://furuse.work/ops/2d/smoothing/mean_image.html) · [`opening_circle`](https://furuse.work/ops/2d/region/opening_circle.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`project_points`](https://furuse.work/ops/3d/render/project_points.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`select_largest`](https://furuse.work/ops/2d/region/select_largest.html) · [`sobel_dir`](https://furuse.work/ops/2d/edges/sobel_dir.html) · [`var_threshold`](https://furuse.work/ops/2d/segmentation/var_threshold.html)

## 71. Camera Fingerprints (PRNU): Which Camera Took This? — The Fingerprint Grows With Frame Count and Dies at the Save Button

[![Camera Fingerprints (PRNU): Which Camera Took This? — The Fingerprint Grows With Frame Count and Dies at the Save Button](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/01_estimators_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/01_estimators.png)

*↑ **Camera Fingerprints (PRNU): Which Camera Took This? — The Fingerprint Grows With Frame Count and Dies at the Save Button** ―― Two virtual cameras carry a fixed sensitivity pattern K; the fingerprint is estimated from 30 residuals and matched. Under clean conditions the same camera scores a median PCE of 2192 against 15.7 for the other (AUC 1.000), but JPEG-like quantisation at quality 50 cuts PCE to 3.6 % and a 0.5x downscale to 1.5 % — and what killed it was the residual extractor, not the geometry. A camera with K = 0 still yields a 'fingerprint' with PCE 1706 if the same background is shot 30 times: the scene turns into a fingerprint.*

[![別カメラのピークは毎回別の位置に立つ((0,0) は 0/30)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/02_match_pce_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/02_match_pce.png)

*↑ The measurement ―― 別カメラのピークは毎回別の位置に立つ((0,0) は 0/30)。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_prnu_camera_fingerprint.py
```

Source: [examples/poc_prnu_camera_fingerprint.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_prnu_camera_fingerprint.py)

Ops used (notes): [`aug_jpeg_blocks`](https://furuse.work/ops/2d/augmentation/aug_jpeg_blocks.html) · [`evidence_quantile`](https://furuse.work/ops/imgforensics/calibration/evidence_quantile.html) · [`fingerprint_correlate`](https://furuse.work/ops/imgforensics/sensor/fingerprint_correlate.html) · [`gauss_image`](https://furuse.work/ops/2d/smoothing/gauss_image.html) · [`median_image`](https://furuse.work/ops/2d/rank/median_image.html) · [`null_distribution`](https://furuse.work/ops/imgforensics/calibration/null_distribution.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`sensor_fingerprint`](https://furuse.work/ops/imgforensics/sensor/sensor_fingerprint.html) · [`sk_nlm`](https://furuse.work/ops/2d/smoothing/sk_nlm.html) · [`sk_tv`](https://furuse.work/ops/2d/smoothing/sk_tv.html) · [`sk_wavelet`](https://furuse.work/ops/2d/smoothing/sk_wavelet.html) · [`xsp_dct_denoise`](https://furuse.work/ops/2d/smoothing/xsp_dct_denoise.html) · [`xsp_wiener`](https://furuse.work/ops/2d/smoothing/xsp_wiener.html)

## 72. Craquelure networks — of three indicators, only junction degree breaks under imaging conditions

[![Craquelure networks — of three indicators, only junction degree breaks under imaging conditions](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/07_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/07_scene.png)

*↑ **Craquelure networks — of three indicators, only junction degree breaks under imaging conditions** ―― A Voronoi crack network is drawn in closed form for two ground-truth types — drying cracks (small tortuous cells) and age cracks (large grid-like cells) — with paint blotches, varnish gloss, raking light, blur and noise, then measured with a ridge op → skeleton → junction chain. Truth separates the types on all three indicators (cell diameter 18.0 vs 45.2 px, straightness 0.960 vs 1.000, degree-4 fraction 0.20 vs 0.83), yet the age type's degree-4 fraction drifts toward the drying value under texture (0.87 → 0.64) and raking light (0.70) while diameter and straightness stay put. Both predicted cliffs failed to appear: recall is still 0.696 at 0.15 px width and false positives only 0.382 at texture contrast 0.64. Raking light widens cracks one-sidedly by +0.37 px and shifts the centreline 0.75 px toward the light.*

[![Frangi は分岐点で応答が落ち、斜光でセルが崩れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/01_ridge_ops_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/01_ridge_ops.png)

*↑ The measurement ―― Frangi は分岐点で応答が落ち、斜光でセルが崩れる。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_fresco_craquelure.py
```

Source: [examples/poc_fresco_craquelure.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_fresco_craquelure.py)

Ops used (notes): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`cv_blackhat`](https://furuse.work/ops/2d/morphology/cv_blackhat.html) · [`distance_transform`](https://furuse.work/ops/2d/region/distance_transform.html) · [`hx_split_skeleton_region`](https://furuse.work/ops/2d/halcon_ext/hx_split_skeleton_region.html) · [`hysteresis_threshold`](https://furuse.work/ops/2d/segmentation/hysteresis_threshold.html) · [`junctions_skeleton`](https://furuse.work/ops/2d/region/junctions_skeleton.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`pruning`](https://furuse.work/ops/2d/region/pruning.html) · [`r2_endpoints_skeleton`](https://furuse.work/ops/2d/region/r2_endpoints_skeleton.html) · [`sk_area_opening`](https://furuse.work/ops/2d/morphology/sk_area_opening.html) · [`sk_frangi`](https://furuse.work/ops/2d/texture/sk_frangi.html) · [`sk_otsu`](https://furuse.work/ops/2d/segmentation/sk_otsu.html) · [`skeleton`](https://furuse.work/ops/2d/region/skeleton.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html) · [`xsk_meijering`](https://furuse.work/ops/2d/texture/xsk_meijering.html) · [`xsk_sato`](https://furuse.work/ops/2d/texture/xsk_sato.html)

### The 3-D Shape Wing — Align First, and the Alignment Eats the Defect

Work on point clouds and meshes differs from 2-D work in one decisive way: a pose-alignment step comes before the measurement. That step rotates the shape into whatever orientation makes the discrepancy smallest, so the larger the defect, the more of it the alignment absorbs, leaving a small residual and a part that looks in tolerance. The exhibits in this room try to count what the alignment ate.

Every ground truth here is written as a formula. Solids are built from analytic surfaces combined with boolean operations, chosen so that volume, surface area, wall thickness and curvature are known in closed form. Deformations are known fields (a local dent, a warp, a constant wear along the surface normal), poses are known rotations and translations, and the scan is a uniform sample of the surface with a known density, noise level and occlusion pattern. That is what makes it possible to hold the alignment error and the shape error apart.

The pitfalls specific to 3-D also get counted separately here. A nearest-neighbour distance is biased upward whenever there is noise, because it only ever counts one side. Normal signs are decided by whatever helper computed them. Changing the point density changes the scale of the distance itself. A symmetric shape has no unique pose. Each of these disappears the moment the numbers are folded into one.

## 73. Repair the mesh, then measure — the defect count clears, the quantity does not

[![Repair the mesh, then measure — the defect count clears, the quantity does not](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/01_scene.png)

*↑ **Repair the mesh, then measure — the defect count clears, the quantity does not** ―― A closed triangle mesh is built from the boolean union of a sphere, a torus and a box, then seeded with a known count of each defect class — holes, flipped faces, non-manifold edges, degenerate slivers, duplicated vertices and self-intersection — and tracked with both the topological counts and the volume/area. The Euler characteristic does not move at all for 5 of the 6 classes, and 6 holes plus 6 duplicated faces leave the vertex, edge, face and chi counts identical to the healthy part. Repair does not bring the quantities back: filling a 45-degree cap hole on a sphere changes the surface area by +6.868 % where the closed form predicts -2.145 % (the rim is a staircase, not a circle), and pushing just 6 vertices inward passes all three topological checks while the area is +4.414 % and the volume -0.332 % — a 13-fold disagreement.*

[![健全な部品の χ は 0(種数 1)。χ=2 を合格条件にすると健全品が落ちる。最終行は打ち消し。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/02_euler_blindspots_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/02_euler_blindspots.png)

*↑ The measurement ―― 健全な部品の χ は 0(種数 1)。χ=2 を合格条件にすると健全品が落ちる。最終行は打ち消し。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_mesh_quality_repair.py
```

Source: [examples/poc_mesh_quality_repair.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_mesh_quality_repair.py)

Ops used (notes): [`decimate_qem`](https://furuse.work/ops/3d/mesh_process/decimate_qem.html) · [`face_normals`](https://furuse.work/ops/3d/mesh_process/face_normals.html) · [`fill_holes`](https://furuse.work/ops/2d/region/fill_holes.html) · [`inertia_tensor`](https://furuse.work/ops/3d/moment_invariant/inertia_tensor.html) · [`mesh_area`](https://furuse.work/ops/3d/mesh_process/mesh_area.html) · [`mesh_edge_lengths`](https://furuse.work/ops/3d/terrain/mesh_edge_lengths.html) · [`mesh_edge_stats`](https://furuse.work/ops/3d/resolution/mesh_edge_stats.html) · [`sdf_subtract`](https://furuse.work/ops/3d/sdf_csg/sdf_subtract.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`vertex_curvature`](https://furuse.work/ops/3d/mesh_process/vertex_curvature.html) · [`vertex_normals`](https://furuse.work/ops/3d/mesh_process/vertex_normals.html) · [`voxel_to_mesh`](https://furuse.work/ops/3d/transform/voxel_to_mesh.html)

## 74. Earthwork on a slope — align first and the scar gets shallower

[![Earthwork on a slope — align first and the scar gets shallower](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/09_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/09_scene.png)

*↑ **Earthwork on a slope — align first and the scar gets shallower** ―― A synthetic slope carries an excavation and a deposit of known volume; two epochs of airborne points are differenced both vertically (DoD) and along the local surface normal (M3C2). The expected "cos-θ shrinkage on a slope" never appears — integrating vertical differences over horizontal area cancels the cosine, and the excavated volume stays within -0.011 % from 0 to 40 degrees. What breaks is the registration: when the changed area covers 33 % of the scene, ICP absorbs the change itself and the net volume collapses from a true -30.4 m3 to -3.8 m3, while a no-change control alone already fabricates 83.8 m3 of phantom excavation.*

[![傾斜を 0 から 40 度まで振っても体積の誤差に傾向が無い。cos は積分で約分する。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/01_geometry_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/01_geometry.png)

*↑ The measurement ―― 傾斜を 0 から 40 度まで振っても体積の誤差に傾向が無い。cos は積分で約分する。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_lidar_terrain_change.py
```

Source: [examples/poc_lidar_terrain_change.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_lidar_terrain_change.py)

Ops used (notes): [`chamfer_distance`](https://furuse.work/ops/3d/metrics/chamfer_distance.html) · [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`estimate_oriented_normals`](https://furuse.work/ops/3d/normals_orient/estimate_oriented_normals.html) · [`fit_plane_3d`](https://furuse.work/ops/3d/geometry/fit_plane_3d.html) · [`icp_point2point_3d`](https://furuse.work/ops/3d/refine/icp_point2point_3d.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`ransac_plane`](https://furuse.work/ops/3d/robust_fit/ransac_plane.html) · [`voxel_grid_downsample`](https://furuse.work/ops/3d/preprocess/voxel_grid_downsample.html)

## 75. CAD-to-scan deviation inspection — the fit absorbs the defect and invents a dent

[![CAD-to-scan deviation inspection — the fit absorbs the defect and invents a dent](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/01_scene.png)

*↑ **CAD-to-scan deviation inspection — the fit absorbs the defect and invents a dent** ―― An analytic machined part carries a known local dent, a bow and a wear band, all applied as exact displacements along the surface normal, and the scan is synthesized with a known pose, noise and one-sided occlusion. After alignment the signed deviation and the out-of-tolerance area show that the local dent is diluted by only 3.7 %, while a 121 um dent appears at the centre of the part where the truth is just 1.2 um (closed form predicts -120 um). What survives depends on how much the defect resembles the six rigid-body degrees of freedom; along the edges the nearest neighbour jumps to the adjacent face, producing 66.5 mm^2 of false out-of-tolerance area even in a defect-free control.*

[![真の姿勢を与えた最終行が推定器そのものの床。点-面 ICP との差は姿勢ではなく datum の取り方の差。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/02_methods_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/02_methods.png)

*↑ The measurement ―― 真の姿勢を与えた最終行が推定器そのものの床。点-面 ICP との差は姿勢ではなく datum の取り方の差。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_cad_scan_deviation.py
```

Source: [examples/poc_cad_scan_deviation.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_cad_scan_deviation.py)

Ops used (notes): [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`chamfer_distance`](https://furuse.work/ops/3d/metrics/chamfer_distance.html) · [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`estimate_oriented_normals`](https://furuse.work/ops/3d/normals_orient/estimate_oriented_normals.html) · [`face_areas`](https://furuse.work/ops/3d/mesh_process/face_areas.html) · [`gicp`](https://furuse.work/ops/3d/gicp/gicp.html) · [`hausdorff_distance`](https://furuse.work/ops/3d/metrics/hausdorff_distance.html) · [`icp_point2plane`](https://furuse.work/ops/3d/refine/icp_point2plane.html) · [`icp_point2point_3d`](https://furuse.work/ops/3d/refine/icp_point2point_3d.html) · [`query_distance`](https://furuse.work/ops/3d/occupancy/query_distance.html) · [`register_fpfh`](https://furuse.work/ops/3d/feature_register/register_fpfh.html) · [`sphere_sdf`](https://furuse.work/ops/3d/sdf_csg/sphere_sdf.html) · [`voxel_grid_downsample`](https://furuse.work/ops/3d/preprocess/voxel_grid_downsample.html)

## 76. Manufacturability from geometry alone — faces that sit on the threshold flip when you smooth them

[![Manufacturability from geometry alone — faces that sit on the threshold flip when you smooth them](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/01_scene.png)

*↑ **Manufacturability from geometry alone — faces that sit on the threshold flip when you smooth them** ―― A synthetic part with known design values (thin walls, a slot, ribs near 45 deg, holes) is voxelised, then wall thickness, support area and tool clearance are measured. Across the 45 deg threshold the support area jumps 185.22 -> 576.10 mm^2 — 3.11x for 0.2 deg — and that step vanishes entirely when the isosurface is taken from a distance field, and loses 12 % under smoothing. Thickness collapses onto a 2-voxel lattice (the inscribed sphere does not help), and clearance errors go both ways: at 0.500 mm voxels the slot appears 2.000 mm wide and admits a tool that does not fit.*

[![上: 左端の 2 本が薄壁(1.500 mm)とそのあいだのスロット(1.500 mm)、右の三角が補強。下: リブと薄壁の footprint。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/02_sections_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/02_sections.png)

*↑ The measurement ―― 上: 左端の 2 本が薄壁(1.500 mm)とそのあいだのスロット(1.500 mm)、右の三角が補強。下: リブと薄壁の footprint。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_dfm_thickness_overhang.py
```

Source: [examples/poc_dfm_thickness_overhang.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dfm_thickness_overhang.py)

Ops used (notes): [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`face_areas`](https://furuse.work/ops/3d/mesh_process/face_areas.html) · [`face_normals`](https://furuse.work/ops/3d/mesh_process/face_normals.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`morph_erode3d`](https://furuse.work/ops/3d/morphology/morph_erode3d.html) · [`render_shaded`](https://furuse.work/ops/3d/render/render_shaded.html) · [`sdf_intersect`](https://furuse.work/ops/3d/sdf_csg/sdf_intersect.html) · [`sdf_subtract`](https://furuse.work/ops/3d/sdf_csg/sdf_subtract.html) · [`sdf_to_occupancy`](https://furuse.work/ops/3d/transform/sdf_to_occupancy.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`vol_wall_thickness`](https://furuse.work/ops/3d/probe/vol_wall_thickness.html) · [`voxel_to_mesh`](https://furuse.work/ops/3d/transform/voxel_to_mesh.html)

## 77. Restoring what is missing by symmetry — the plane you assume is the lie you get

[![Restoring what is missing by symmetry — the plane you assume is the lie you get](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/01_scene.png)

*↑ **Restoring what is missing by symmetry — the plane you assume is the lie you get** ―― A bilaterally symmetric mask is synthesised so that both the complete shape and the true mirror plane are known, then one side is broken off with a sphere. With the true plane, symmetric restoration reaches 0.81 mm RMS and beats harmonic hole filling (1.60 mm) — but it loses the moment the plane is off by 1.39 deg (84 arcmin) or 1.41 mm. The error is predicted by the surface-normal component of the mirror displacement (4.6 % relative error; the naive 2d sin a misses by 50.6 %), so the cliff follows from geometry alone. Losing 3.1 % of the points already flips the PCA candidate ranking onto a 90-degree-wrong axis, and on a shape that is not truly symmetric the restoration fabricates 3436 mm3 of ornament or erases 3495 mm3 — even with the exact plane.*

[![失われた真値の点から復元点群までの距離(符号なし、6 mm で頭打ち)。対称復元だけが眼窩の形を取り戻す。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/02_restore_error_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/02_restore_error_maps.png)

*↑ The measurement ―― 失われた真値の点から復元点群までの距離(符号なし、6 mm で頭打ち)。対称復元だけが眼窩の形を取り戻す。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_symmetry_restoration.py
```

Source: [examples/poc_symmetry_restoration.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_symmetry_restoration.py)

Ops used (notes): [`detect_reflection_symmetry`](https://furuse.work/ops/3d/symmetry/detect_reflection_symmetry.html) · [`fill_holes`](https://furuse.work/ops/2d/region/fill_holes.html) · [`fit_plane_3d`](https://furuse.work/ops/3d/geometry/fit_plane_3d.html) · [`icp_point2point_3d`](https://furuse.work/ops/3d/refine/icp_point2point_3d.html) · [`normalize`](https://furuse.work/ops/shape2d/descriptor/normalize.html) · [`reflect_points`](https://furuse.work/ops/3d/symmetry/reflect_points.html) · [`reflection_symmetry_score`](https://furuse.work/ops/3d/symmetry/reflection_symmetry_score.html)

## 78. Warpage lives in the layer history — averaging the area throws the placement away

[![Warpage lives in the layer history — averaging the area throws the placement away](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/01_scene.png)

*↑ **Warpage lives in the layer history — averaging the area throws the placement away** ―― Seven synthetic parts are sliced into layers with a known constant per-layer shrinkage strain; warpage is first predicted in closed form from the layer-area history alone, then measured with an incremental layer-birth finite-element solve. A predictor that looks only at the final shape returns exactly zero (2.712e-21), and the history-based closed form lands within 0.4 % on 4 of the 7 shapes — but the moment the area is averaged along the length, where the material sits is lost. Three parts whose layer-area histories match to the last square millimetre bow by 0.4109 / 0.3809 / 0.3271 mm (a 26 % spread), and the force peeling them off the build plate differs by 48x (11.8 vs 573.5 N), flipping the pass/fail verdict.*

[![この断面の面積の列だけが、閉形式の入力になる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/02_layer_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/02_layer_frames.png)

*↑ The measurement ―― この断面の面積の列だけが、閉形式の入力になる。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_print_warpage_risk.py
```

Source: [examples/poc_print_warpage_risk.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_print_warpage_risk.py)

Ops used (notes): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`sdf_to_occupancy`](https://furuse.work/ops/3d/transform/sdf_to_occupancy.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html)

## 79. Fusing two sensors into a bird's-eye grid — a calibration that passes in pixels turns into metres at range

[![Fusing two sensors into a bird's-eye grid — a calibration that passes in pixels turns into metres at range](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/01_scene_bev_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/01_scene_bev.png)

*↑ **Fusing two sensors into a bird's-eye grid — a calibration that passes in pixels turns into metres at range** ―― An analytic street scene (a tall lead truck, plus two distant cars each hidden in the other sensor's shadow) is fused from a left-mirror LiDAR and a right-mirror depth camera into one bird's-eye grid, then swept over rotation, translation and timing errors in the extrinsics. Fusion reaches an occupancy IoU of 0.7033 against 0.5417 for the best single sensor — and every bit of that gain comes from complementary visibility, not accuracy. One pixel of reprojection error becomes 0.083 m at 22 m; the cliff is set by the object width, not the 0.2 m cell (IoU drops only 5.8 % when 68 % of the points have already crossed a cell); by 3 deg of yaw the fusion has fallen below the single sensor.*

[![横に 1.80 m 離した 2 センサの「自由と言い切れた領域」。青い帯が LiDAR にしか見えない所、橙の帯がカメラにしか見えない所、灰色は両方。白は真値の障害物。22 m の 2 台は**互いの影に 1 台ずつ入っている**。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/02_shadow_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/02_shadow_map.png)

*↑ The measurement ―― 横に 1.80 m 離した 2 センサの「自由と言い切れた領域」。青い帯が LiDAR にしか見えない所、橙の帯がカメラにしか見えない所、灰色は両方。白は真値の障害物。22 m の 2 台は**互いの影に 1 台ずつ入っている**。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_bev_sensor_fusion.py
```

Source: [examples/poc_bev_sensor_fusion.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bev_sensor_fusion.py)

Ops used (notes): [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`closing_circle`](https://furuse.work/ops/2d/region/closing_circle.html) · [`depth_to_points`](https://furuse.work/ops/3d/transform/depth_to_points.html) · [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`fill_up`](https://furuse.work/ops/2d/region/fill_up.html) · [`fuse`](https://furuse.work/ops/3d/tsdf_fusion/fuse.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`occupancy_grid`](https://furuse.work/ops/3d/occupancy/occupancy_grid.html) · [`project_points`](https://furuse.work/ops/3d/render/project_points.html) · [`sdf_to_occupancy`](https://furuse.work/ops/3d/transform/sdf_to_occupancy.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`voxel_grid_downsample`](https://furuse.work/ops/3d/preprocess/voxel_grid_downsample.html) · [`voxel_iou`](https://furuse.work/ops/3d/metrics/voxel_iou.html)

## 80. Collapsing joint voids into one number — what the number drops is the shape that matters

[![Collapsing joint voids into one number — what the number drops is the shape that matters](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/01_scene_sections_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/01_scene_sections.png)

*↑ **Collapsing joint voids into one number — what the number drops is the shape that matters** ―― A synthetic die-attach bond line carries five void populations whose volume fraction is held exactly at 3.000 % while only their depth, shape and proximity change, re-imaged as an X-ray CT with a PSF, noise and beam-hardening cupping. The naive zero point — threshold, then report void fraction — separates the five conditions by only 0.17 points (2.46 to 2.63 %), yet the interface area shadowed by flat voids is 2.09x that of volume-matched spheres (14.49 vs 6.92 %) and the largest cluster spans 13.1x further when the voids are chained (80.0 vs 6.1 %). The predicted cliff never arrives: at 60 um voxels the void fraction still reads 3.21 % (it only wobbles by 1.36 points with the grid phase), while flatness becomes unmeasurable and the interface-deficit metric drops from 14.16 to 9.78 % — the degradation runs toward 'pass', which is the worst possible direction.*

[![疑似カラーはラベル番号を並べ替えたもの。側面図で界面(上端)に貼りついているのが見える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/02_void_label_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/02_void_label_map.png)

*↑ The measurement ―― 疑似カラーはラベル番号を並べ替えたもの。側面図で界面(上端)に貼りついているのが見える。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_ct_void_morphology.py
```

Source: [examples/poc_ct_void_morphology.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_void_morphology.py)

Ops used (notes): [`boundary_vertices`](https://furuse.work/ops/3d/mesh_process/boundary_vertices.html) · [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`cylinder_sdf`](https://furuse.work/ops/3d/sdf_csg/cylinder_sdf.html) · [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`face_areas`](https://furuse.work/ops/3d/mesh_process/face_areas.html) · [`mesh_volume`](https://furuse.work/ops/3d/mesh_process/mesh_volume.html) · [`morph_dilate3d`](https://furuse.work/ops/3d/morphology/morph_dilate3d.html) · [`plane_sdf`](https://furuse.work/ops/3d/sdf_csg/plane_sdf.html) · [`query_distance`](https://furuse.work/ops/3d/occupancy/query_distance.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`sphere_sdf`](https://furuse.work/ops/3d/sdf_csg/sphere_sdf.html) · [`vol_boundary_points`](https://furuse.work/ops/3d/boundary/vol_boundary_points.html) · [`vol_gaussian_psf`](https://furuse.work/ops/3d/restoration/vol_gaussian_psf.html) · [`voxel_to_mips`](https://furuse.work/ops/3d/transform/voxel_to_mips.html)

## 81. Battery cell degradation by CT — the swelling shows outside, the cause stays inside

[![Battery cell degradation by CT — the swelling shows outside, the cause stays inside](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/02_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/02_scene.png)

*↑ **Battery cell degradation by CT — the swelling shows outside, the cause stays inside** ―― A prismatic lithium-ion cell — stacked electrodes inside an aluminium can — is built with ground truth, degraded by known fields (uniform swelling, local swelling, inter-layer gas voids, electrode misalignment), and then imaged for real: forward projection, beam hardening, photon noise and FBP reconstruction. Only 29.4 % of a 10 % electrode swelling reaches the outside, and a caliper across the centre reads 3.6 times the volume-equivalent mean (+0.235 vs +0.066 mm). Three cells tuned to the same external bulge differ by 0.000 mm in can height yet separate internally (void fraction 0.00 vs 5.20 %, layer flatness 0.0156 vs 0.0784 mm), and the resolution cliff for those internal numbers is set by the 0.120 mm inter-layer gap, not the 0.200 mm electrode — voxel/thickness = 0.30, where the sampling-theorem prediction said 0.80.*

[![真正面(0 度)なら空隙の影までは見える。ただし奥行きに積算されているので厚みも深さも出ない。22 度傾けると層の縞そのものが重なって消える —— 投影では姿勢が結果を決めてしまう。だから断層に落とす。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/01_xray_projection_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/01_xray_projection.png)

*↑ The measurement ―― 真正面(0 度)なら空隙の影までは見える。ただし奥行きに積算されているので厚みも深さも出ない。22 度傾けると層の縞そのものが重なって消える —— 投影では姿勢が結果を決めてしまう。だから断層に落とす。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_battery_ct_degradation.py
```

Source: [examples/poc_battery_ct_degradation.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_battery_ct_degradation.py)

Ops used (notes): [`beam_hardening_apply`](https://furuse.work/ops/tomography/artifact/beam_hardening_apply.html) · [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`fbp_volume`](https://furuse.work/ops/tomography/volume/fbp_volume.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`plane_sdf`](https://furuse.work/ops/3d/sdf_csg/plane_sdf.html) · [`projection_angles`](https://furuse.work/ops/tomography/layout/projection_angles.html) · [`radon_volume`](https://furuse.work/ops/tomography/volume/radon_volume.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`ring_artifact_apply`](https://furuse.work/ops/tomography/artifact/ring_artifact_apply.html) · [`sdf_intersect`](https://furuse.work/ops/3d/sdf_csg/sdf_intersect.html) · [`sdf_subtract`](https://furuse.work/ops/3d/sdf_csg/sdf_subtract.html) · [`sdf_to_occupancy`](https://furuse.work/ops/3d/transform/sdf_to_occupancy.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`vol_bounding_box`](https://furuse.work/ops/3d/domain/vol_bounding_box.html) · [`vol_edge_probe`](https://furuse.work/ops/3d/probe/vol_edge_probe.html) · [`vol_fft_lowpass`](https://furuse.work/ops/3d/frequency/vol_fft_lowpass.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_profile_line`](https://furuse.work/ops/3d/probe/vol_profile_line.html) · [`vol_region_props`](https://furuse.work/ops/3d/regionprops/vol_region_props.html) · [`vol_resize`](https://furuse.work/ops/3d/geom_transform/vol_resize.html) · [`vol_wall_thickness`](https://furuse.work/ops/3d/probe/vol_wall_thickness.html)

## 82. Re-surveying a structure year by year — when the vantage moves, decay appears to advance

[![Re-surveying a structure year by year — when the vantage moves, decay appears to advance](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/01_scene.png)

*↑ **Re-surveying a structure year by year — when the vantage moves, decay appears to advance** ―― A bridge girder (7 planes + 2 cylinders) carries known deflection, section loss, bearing settlement and a crack across three epochs, re-scanned each time from different positions, densities and poses. Re-measuring with zero deterioration already yields a nearest-neighbour "change" of 21.07 mm median and 42.64 mm max, and the false repair volume above a 1 mm threshold (5.098 L) reaches 87 % of the real one (5.882 L). Registering on all points absorbs 0.689 of the mid-span deflection (closed form 2/3) and invents a -1.737 mm uplift at the supports, while the undetermined along-span direction shows up not on the girder planes but only on the bearing cylinder, as a spurious 41.2 mm horizontal shift.*

[![下フランジの暗い窪みが断面欠損、面全体の淡い変化がたわみ。腹板(法線が水平)にはたわみが出ない ——同じ劣化でも面の向きで見え方が変わる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/02_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/02_frames.png)

*↑ The measurement ―― 下フランジの暗い窪みが断面欠損、面全体の淡い変化がたわみ。腹板(法線が水平)にはたわみが出ない ——同じ劣化でも面の向きで見え方が変わる。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_structure_4d_deterioration.py
```

Source: [examples/poc_structure_4d_deterioration.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_structure_4d_deterioration.py)

Ops used (notes): [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`chamfer_distance`](https://furuse.work/ops/3d/metrics/chamfer_distance.html) · [`cylinder_sdf`](https://furuse.work/ops/3d/sdf_csg/cylinder_sdf.html) · [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`euclidean_cluster`](https://furuse.work/ops/3d/segment/euclidean_cluster.html) · [`fit_circle_3d`](https://furuse.work/ops/3d/geometry/fit_circle_3d.html) · [`fit_plane_3d`](https://furuse.work/ops/3d/geometry/fit_plane_3d.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`hausdorff_distance`](https://furuse.work/ops/3d/metrics/hausdorff_distance.html) · [`plane_sdf`](https://furuse.work/ops/3d/sdf_csg/plane_sdf.html) · [`rmse`](https://furuse.work/ops/imgmetrics/fidelity/rmse.html) · [`sdf_intersect`](https://furuse.work/ops/3d/sdf_csg/sdf_intersect.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`voxel_grid_downsample`](https://furuse.work/ops/3d/preprocess/voxel_grid_downsample.html)

## 83. As-built deviation of a room — the compromise pose is handed to the innocent element

[![As-built deviation of a room — the compromise pose is handed to the innocent element](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/01_scene_plan_section_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/01_scene_plan_section.png)

*↑ **As-built deviation of a room — the compromise pose is handed to the innocent element** ―― A synthetic room carries known construction errors — leaning walls, a sloping and sagging floor, off-size columns, displaced openings — and is re-measured by a simulated scan from three stations with column shadows, incidence-dependent noise, mixed pixels and registration error. One number for the whole building (mean distance to the design model) moves by only 1.41 mm between a perfect building and a defective one; aligning the cloud in one piece shrinks the wall lean to 69 % of truth and hands 0.89 mrad of tilt to a ceiling that is perfectly level (a closed-form prediction of what the fit absorbs matches the measurement to 0.05 mrad). The cliff is set by the height of the surviving surface rather than by the dropout rate: at the same 90 % loss, dropping points at random costs 0.098 mrad while keeping only the lower band costs 1.234 mrad — 12.6 times worse.*

[![いちばん暗い所は 1 か所も見ていない。柱の影はスキャン位置から放射状に伸びる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/02_station_coverage_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/02_station_coverage.png)

*↑ The measurement ―― いちばん暗い所は 1 か所も見ていない。柱の影はスキャン位置から放射状に伸びる。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_scan_to_bim_asbuilt.py
```

Source: [examples/poc_scan_to_bim_asbuilt.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_scan_to_bim_asbuilt.py)

Ops used (notes): [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`chamfer_distance`](https://furuse.work/ops/3d/metrics/chamfer_distance.html) · [`cylinder_sdf`](https://furuse.work/ops/3d/sdf_csg/cylinder_sdf.html) · [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`euclidean_cluster`](https://furuse.work/ops/3d/segment/euclidean_cluster.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`plane_sdf`](https://furuse.work/ops/3d/sdf_csg/plane_sdf.html) · [`plane_segmentation`](https://furuse.work/ops/3d/segment/plane_segmentation.html) · [`sdf_intersect`](https://furuse.work/ops/3d/sdf_csg/sdf_intersect.html) · [`sdf_subtract`](https://furuse.work/ops/3d/sdf_csg/sdf_subtract.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`voxel_grid_downsample`](https://furuse.work/ops/3d/preprocess/voxel_grid_downsample.html)

## 84. Pipe Wall Loss on the Unwrapped Map — The Axis You Choose Eats the Invert Corrosion

[![Pipe Wall Loss on the Unwrapped Map — The Axis You Choose Eats the Invert Corrosion](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/01_scene_pipe_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/01_scene_pipe.png)

*↑ **Pipe Wall Loss on the Unwrapped Map — The Axis You Choose Eats the Invert Corrosion** ―― A synthetic pipe carries a pit, a full-circumference thinning band, invert corrosion, a weld bead, ovality and a sagging axis, all at known depths; the in-pipe range sensor is then deliberately run off-axis before the bore is unwrapped. A 4.0 mm axis offset alone flags 44.8 % of a corrosion-free round pipe as wall loss — within 1.84 points of the geometric prediction that an offset e appears as a one-cycle sinusoid of amplitude e — and the fictitious loss volume is 149.9 times the real pit. Removing the one-cycle term removes the fiction, but 79 % of invert corrosion (the commonest defect in sewers) lives in that same harmonic, so its detection falls from 100.0 % to 34.4 %; only constraining the axis the way physics does (a straight line plus a sag) keeps both.*

[![下の帯の細くなっている所が管底腐食。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/02_scene_polar_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/02_scene_polar.png)

*↑ The measurement ―― 下の帯の細くなっている所が管底腐食。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_pipe_wall_loss.py
```

Source: [examples/poc_pipe_wall_loss.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pipe_wall_loss.py)

Ops used (notes): [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_select`](https://furuse.work/ops/blob/select/blob_select.html) · [`cylinder_sdf`](https://furuse.work/ops/3d/sdf_csg/cylinder_sdf.html) · [`cylinder_unwrap`](https://furuse.work/ops/3d/curvilinear/cylinder_unwrap.html) · [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`polar_unwrap`](https://furuse.work/ops/3d/curvilinear/polar_unwrap.html) · [`ransac_cylinder`](https://furuse.work/ops/3d/robust_fit/ransac_cylinder.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`sdf_subtract`](https://furuse.work/ops/3d/sdf_csg/sdf_subtract.html) · [`sdf_to_occupancy`](https://furuse.work/ops/3d/transform/sdf_to_occupancy.html) · [`vol_wall_thickness`](https://furuse.work/ops/3d/probe/vol_wall_thickness.html)

