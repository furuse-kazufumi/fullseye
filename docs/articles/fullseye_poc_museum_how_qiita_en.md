> **Language**: [日本語](https://qiita.com/furuse-kazufumi/items/75ada244f3d93a7156b7) · **English**

# A Metrology Museum on Paper — The How-It-Is-Measured Wing (restoration, space-time, calibration, colour, forensics, 3-D shape)

> One wing of **[A Metrology Museum on Paper — the entrance](https://qiita.com/furuse-kazufumi/items/8a8f23e53b19ee8cdc10)**, where the other wings, the glossary and the thesis live.

**81 exhibits** hang in this wing. The numbers are accession numbers: they do not change when an exhibit moves or when an article is split.

> The "Ops used" line under each exhibit links to that op's note (type contract, pitfalls, figures, a runnable Studio program): [Operator catalogue](https://furuse.work/OP_CATALOG.html) / [Op notes index](https://furuse.work/ops/INDEX.html).

### The Image Quality and Restoration Wing — Looking Better and Getting Closer to the Truth Are Different Things

Deblurring, upscaling, dehazing, focus stacking, reconstructing from projections, ranging by counting photons. Restoration is where 'it looks better' and 'it is closer to the truth' are most easily confused. The 18 exhibits here synthesise the kernel, the depth, the airlight, the PSD, the projections and the arrival time themselves, so the two can be scored separately.

Appearance metrics do not peak at the truth: a hazy input has higher contrast than the true scene; unsharp masking matches the true gradient energy while PSNR drops; adding noise raises PSNR. Conversely, a method can restore stripes finer than Nyquist while PSNR moves by only -0.01 dB.

The null baseline placed throughout is 'do nothing'. Deblurring with the kernel angle off by 19.4 degrees, FBP from 12 projections, dehazing at visibility above 782 m, depth in textureless regions: each loses to that baseline. Stating the losing conditions in numbers is what this room is for.

## No.2026.007 —— How Much Camera Shake Can Be Undone — Make the Kernel, Apply It, Invert It, Compare

[![How Much Camera Shake Can Be Undone — Make the Kernel, Apply It, Invert It, Compare](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/01_noise_ceiling_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/01_noise_ceiling.png)

*↑ **How Much Camera Shake Can Be Undone — Make the Kernel, Apply It, Invert It, Compare** ―― A known linear blur kernel applied and inverted, with the ceiling set by noise and by kernel estimation error. Without noise the image recovers from 22.38 to 56.41 dB; at 20 dB SNR the gain is 1.82 dB. A kernel angle off by 19.4 degrees is beaten by doing nothing, and undoing rotational blur with a single kernel makes the centre of rotation worse by -49.41 dB.*

[![4 枚目は「復元した」形をしているが、ゼロ点(観測そのもの)より悪い。絵の見た目では区別できない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/02_deblur_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/02_deblur.png)

*↑ The measurement ―― 4 枚目は「復元した」形をしているが、ゼロ点(観測そのもの)より悪い。絵の見た目では区別できない。 (figure labels are in Japanese; the numbers are the same)*

[![交点が現場で効く数字。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/03_kernel_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/03_kernel_error.png)

*↑ 交点が現場で効く数字。*

[![核を作った右側だけが正。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/04_rotational_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/04_rotational.png)

*↑ 核を作った右側だけが正。*

[![15 px・20 度の直線ブレに SNR 40 dB の雑音を載せた観測を、角度を 0〜30 度ずらした核で Wiener 復元し直していく(正則化量は毎回神託で最良化)。ずれ 0 度で 28.87 dB、20 度で 22.31 dB。0.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/05_kernel_angle_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/05_kernel_angle_sweep.gif)

*↑ The animation ―― 15 px・20 度の直線ブレに SNR 40 dB の雑音を載せた観測を、角度を 0〜30 度ずらした核で Wiener 復元し直していく(正則化量は毎回神託で最良化)。ずれ 0 度で 28.87 dB、20 度で 22.31 dB。0.5 度刻みで追うと 19.2 度でアンシャープマスク(22.40 dB)に、19.4 度で「何もしない」(22.38 dB)に抜かれる(本文の表の補間では 19.2 / 19.4 度)。抜かれた後の復元も「復元した」形をしている —— 右の誤差地図でだけ、縞状のリンギングが真値からのずれとして見える。*

```
py -3.11 examples/poc_camera_shake_deblur.py
```

Source: [examples/poc_camera_shake_deblur.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_camera_shake_deblur.py)

This run produced **5 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_camera_shake_deblur)

Ops used (notes): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`psnr`](https://furuse.work/ops/imgmetrics/fidelity/psnr.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`ssim`](https://furuse.work/ops/imgmetrics/fidelity/ssim.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html) · [`unsharp`](https://furuse.work/ops/2d/smoothing/unsharp.html) · [`vol_richardson_lucy`](https://furuse.work/ops/3d/restoration/vol_richardson_lucy.html)

## No.2026.062 —— Pseudo-colour changes what the reader decides — counting edges that are not there

[![Pseudo-colour changes what the reader decides — counting edges that are not there](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colormap_readability/05_scene_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colormap_readability/05_scene_maps.png)

*↑ **Pseudo-colour changes what the reader decides — counting edges that are not there** ―― A smooth field with provably zero steps was painted and the false edges counted in CIE L* and CIEDE2000: jet raises 3, hsv 4, while viridis and gray raise none. Their positions follow in closed form from the sRGB transfer function and the CIE Y weights — jet's lightness reversals are predicted at 0.3750 / 0.4490 / 0.6250 and measured at 0.3750 / 0.4492 / 0.6250 (max error 0.0002). A real step only out-shouts the false edges above 0.296 %FS with jet versus 0.050 %FS with viridis, matching a prediction made from the colormap LUT alone: jet demands a 5.9x taller step. The value-to-colour mapping matters more than the palette — over a 4.3-decade 1/r^2 field the effective number of distinguishable levels goes from 1.4 (linear) to 76.0 (rank) — and a single outlier costs log 41 % of them (27.4 to 16.3) while percentile and rank are untouched.*

[![平らなら偽の境目は立たない。jet と hsv の山がそのまま『見えてしまう帯』になる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colormap_readability/01_gain_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colormap_readability/01_gain_profile.png)

*↑ The measurement ―― 平らなら偽の境目は立たない。jet と hsv の山がそのまま『見えてしまう帯』になる。 (figure labels are in Japanese; the numbers are the same)*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colormap_readability/02_lightness_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colormap_readability/02_lightness_profile.png)

*↑ この回の図*

[![jet の**輪**が偽の境目。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colormap_readability/06_false_edge_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colormap_readability/06_false_edge_map.png)

*↑ jet の**輪**が偽の境目。*

[![左は範囲外と『ちょうど端』が同じ色。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colormap_readability/09_range_sentinel_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colormap_readability/09_range_sentinel.png)

*↑ 左は範囲外と『ちょうど端』が同じ色。*

[![番号の大小に意味は無いのに、連続マップは『近い番号 = 近い領域』と読ませる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colormap_readability/12_categorical_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colormap_readability/12_categorical.png)

*↑ 番号の大小に意味は無いのに、連続マップは『近い番号 = 近い領域』と読ませる。*

```
py -3.11 examples/poc_colormap_readability.py
```

Source: [examples/poc_colormap_readability.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_colormap_readability.py)

This run produced **14 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_colormap_readability)

Ops used (notes): [`delta_e_map`](https://furuse.work/ops/imgmetrics/colordiff/delta_e_map.html) · [`percentile`](https://furuse.work/ops/2d/rank/percentile.html) · [`rgb_to_lab`](https://furuse.work/ops/imgmetrics/colorspace/rgb_to_lab.html)

## No.2026.118 —— The Fly's Compound Eye Is a Light-Field Sensor — Neural Superposition Pays Only Up to the Knee

[![The Fly's Compound Eye Is a Light-Field Sensor — Neural Superposition Pays Only Up to the Knee](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_compound_eye/01_compound_eye_scaling_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_compound_eye/01_compound_eye_scaling.png)

*↑ **The Fly's Compound Eye Is a Light-Field Sensor — Neural Superposition Pays Only Up to the Knee** ―― A 9×9 plenoptic synthesis of the ommatidial array, measuring the SNR gain when the same point is pooled over N ommatidia. For small apertures √N holds almost exactly (N=5: 2.25 vs 2.24), but for large ones the interpolation error does not average out and the gain saturates (N=49: 5.33 vs 7.00). The fly's six-fold pooling of R1–R6 sits below the knee. Depth comes from the array (near +1.998, far +0.499 against true 2.00 / 0.50), and a minority occluder is seen through by median pooling (RMS on hidden pixels: single view 0.237 → mean 0.065 → median 0.025).*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_compound_eye/02_compound_eye_superposition_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_compound_eye/02_compound_eye_superposition.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_compound_eye/03_compound_eye_depth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_compound_eye/03_compound_eye_depth.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_compound_eye/04_compound_eye_occlusion_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_compound_eye/04_compound_eye_occlusion.png)

*↑ この回の図*

```
py -3.11 examples/poc_compound_eye.py
```

Source: [examples/poc_compound_eye.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_compound_eye.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_compound_eye)

Ops used (notes): [`lf_all_in_focus`](https://furuse.work/ops/lightfield/depth/lf_all_in_focus.html) · [`lf_aperture_mask`](https://furuse.work/ops/lightfield/refocus/lf_aperture_mask.html) · [`lf_depth_from_focus`](https://furuse.work/ops/lightfield/depth/lf_depth_from_focus.html) · [`lf_plenoptic_design`](https://furuse.work/ops/lightfield/depth/lf_plenoptic_design.html) · [`lf_subaperture`](https://furuse.work/ops/lightfield/views/lf_subaperture.html) · [`lf_synthesize`](https://furuse.work/ops/lightfield/synthesis/lf_synthesize.html) · [`lf_synthetic_aperture`](https://furuse.work/ops/lightfield/refocus/lf_synthetic_aperture.html) · [`median`](https://furuse.work/ops/2d/rank/median.html)

## No.2026.010 —— Where CT Reconstruction Starts to Break as Projections Are Removed

[![Where CT Reconstruction Starts to Break as Projections Are Removed](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_fidelity/01_recon_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_fidelity/01_recon_sweep.png)

*↑ **Where CT Reconstruction Starts to Break as Projections Are Removed** ―― Shepp-Logan re-imaged with 180 down to 12 projections, FBP placed beside two nulls: a blank image and unfiltered back-projection. With 12 projections FBP (RMSE 0.2576) is worse than the blank image (0.2420). A check that never looks at the reconstruction — the row sums of the sinogram — caught a -3.34 % mass loss that RMSE could not see; fixing the ramp filter's DC bin brought it to -0.0099 %.*

[![RMSE で見ると 12 本は空白画像 0.2420 より悪い。相関とストリークは別のことを言う。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_fidelity/02_fidelity_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_fidelity/02_fidelity_table.png)

*↑ The measurement ―― RMSE で見ると 12 本は空白画像 0.2420 より悪い。相関とストリークは別のことを言う。 (figure labels are in Japanese; the numbers are the same)*

[![零点 A = 空白画像、零点 B = 無フィルタ逆投影(どちらも水平・ほぼ水平)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_fidelity/03_rmse_vs_views_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_fidelity/03_rmse_vs_views.png)

*↑ 零点 A = 空白画像、零点 B = 無フィルタ逆投影(どちらも水平・ほぼ水平)。*

```
py -3.11 examples/poc_ct_fidelity.py
```

Source: [examples/poc_ct_fidelity.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_fidelity.py)

This run produced **3 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_ct_fidelity)

Ops used (notes): [`backproject_sinogram`](https://furuse.work/ops/tomography/reconstruct/backproject_sinogram.html) · [`ellipse_phantom`](https://furuse.work/ops/tomography/forward/ellipse_phantom.html) · [`ellipse_sinogram`](https://furuse.work/ops/tomography/forward/ellipse_sinogram.html) · [`filtered_backprojection`](https://furuse.work/ops/tomography/reconstruct/filtered_backprojection.html) · [`projection_angles`](https://furuse.work/ops/tomography/layout/projection_angles.html) · [`radon_transform`](https://furuse.work/ops/tomography/forward/radon_transform.html) · [`rmse`](https://furuse.work/ops/imgmetrics/fidelity/rmse.html) · [`ssim`](https://furuse.work/ops/imgmetrics/fidelity/ssim.html) · [`stat_correlation`](https://furuse.work/ops/math/stats/stat_correlation.html)

## No.2026.011 —— Removing Haze — Ground Truth From the Scattering Model, Transmission and Airlight Scored Apart

[![Removing Haze — Ground Truth From the Scattering Model, Transmission and Airlight Scored Apart](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/01_scene.png)

*↑ **Removing Haze — Ground Truth From the Scattering Model, Transmission and Airlight Scored Apart** ―― A hazy image built from depth, airlight and extinction so that the true transmission and the true scene are both known, then dehazed and scored. The overall +4.04 dB hides a -1.49 dB degradation of the near field covered by +4.03 dB mid and +11.28 dB far. Above 782 m visibility dehazing does harm, and adding noise raises PSNR (an accidental cancellation).*

[![空では過大評価(明るい側)、近景では過小評価(暗い側)。全体の平均バイアスでは打ち消し合って見えない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/02_transmission_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/02_transmission.png)

*↑ The measurement ―― 空では過大評価(明るい側)、近景では過小評価(暗い側)。全体の平均バイアスでは打ち消し合って見えない。 (figure labels are in Japanese; the numbers are the same)*

[![全体 +4.04 dB の正体。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/03_bands_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/03_bands.png)

*↑ 全体 +4.04 dB の正体。*

[![左端(薄い霞 = 視程が長い側)で利得が 0 を割る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/04_haze_density_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/04_haze_density.png)

*↑ 左端(薄い霞 = 視程が長い側)で利得が 0 を割る。*

[![動画(110 コマ、120 × 160 px を 2 倍で表示): 消散係数 beta を 0.0025(視程 1565 m)から 0.08(視程 49 m)まで連続に振る。上段は霞んだ観測・暗チャネル除霞・真値、下段は推定した透過率・真の](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/05_haze_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/05_haze_sweep.gif)

*↑ The animation ―― 動画(110 コマ、120 × 160 px を 2 倍で表示): 消散係数 beta を 0.0025(視程 1565 m)から 0.08(視程 49 m)まで連続に振る。上段は霞んだ観測・暗チャネル除霞・真値、下段は推定した透過率・真の透過率と、暗チャネル除霞の PSNR 利得(対 何もしない)の曲線。利得は beta ≦ 0.0065(視程 606 m 以上)で負 = 薄い霞では除霞が害になる(5 節の 7 点の表では 0.0050 と 0.0075 の間)。濃霧の端では +2.98 dB。真の A と t を与えたオラクルの PSNR は中央上の板に併記。表示は 8 bit に丸めた観測をそのまま使っている。*

```
py -3.11 examples/poc_dehazing.py
```

Source: [examples/poc_dehazing.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dehazing.py)

This run produced **5 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_dehazing)

Ops used (notes): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`clahe`](https://furuse.work/ops/2d/gray/clahe.html) · [`equalize`](https://furuse.work/ops/2d/gray/equalize.html) · [`image_entropy`](https://furuse.work/ops/imgmetrics/information/image_entropy.html) · [`joint_bilateral`](https://furuse.work/ops/3d/depth_denoise/joint_bilateral.html) · [`nice_ticks`](https://furuse.work/ops/annotate/plot/nice_ticks.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`psnr`](https://furuse.work/ops/imgmetrics/fidelity/psnr.html) · [`rank_image`](https://furuse.work/ops/2d/rank/rank_image.html) · [`ssim`](https://furuse.work/ops/imgmetrics/fidelity/ssim.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html)

## No.2026.016 —— Ranging by Counting Photons — How Many for How Many Millimetres?

[![Ranging by Counting Photons — How Many for How Many Millimetres?](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/01_histograms_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/01_histograms.png)

*↑ **Ranging by Counting Photons — How Many for How Many Millimetres?** ―― Range read from an arrival-time histogram built by bin-integrating a Gaussian at the round-trip time and drawing Poisson samples. With 200 photons the raw peak position errs by 11.02 mm and the gated centroid by 2.29 mm, riding the 31.83 mm/√N bound at 1.00 to 1.07x. With background the plain centroid collapses by two orders (564 mm at SBR 0.031), and the family's recommended Gaussian fit at 8.82 mm loses to a gated centroid a user can write in six lines.*

[![背景が無ければ素の重心で足りる。背景が入ると 2 桁崩れ、docstring が勧める背景減算でも戻らない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/02_methods_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/02_methods.png)

*↑ The measurement ―― 背景が無ければ素の重心で足りる。背景が入ると 2 桁崩れ、docstring が勧める背景減算でも戻らない。 (figure labels are in Japanese; the numbers are the same)*

[![ゲート重心は CRB に寄り添って落ちる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/03_crb_scaling_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/03_crb_scaling.png)

*↑ ゲート重心は CRB に寄り添って落ちる。*

[![素の推定は μ にほぼ比例して手前へずれる(5 光子/サイクルで -34.5 mm)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/04_pileup_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/04_pileup.png)

*↑ 素の推定は μ にほぼ比例して手前へずれる(5 光子/サイクルで -34.5 mm)。*

```
py -3.11 examples/poc_dtof_ranging.py
```

Source: [examples/poc_dtof_ranging.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dtof_ranging.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_dtof_ranging)

Ops used (notes): [`dtof_cube_depth`](https://furuse.work/ops/photon/dtof/dtof_cube_depth.html) · [`dtof_cube_simulate`](https://furuse.work/ops/photon/dtof/dtof_cube_simulate.html) · [`dtof_depth`](https://furuse.work/ops/photon/dtof/dtof_depth.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`tcspc_background_subtract`](https://furuse.work/ops/photon/tcspc/tcspc_background_subtract.html) · [`tcspc_coates_correct`](https://furuse.work/ops/photon/spad/tcspc_coates_correct.html) · [`tcspc_simulate`](https://furuse.work/ops/photon/tcspc/tcspc_simulate.html)

## No.2026.119 —— The Fly's Visual Front End as a Chain of Operators — Turning and Walking Through a Synthetic Sky, What Can and Cannot Be Read

[![The Fly's Visual Front End as a Chain of Operators — Turning and Walking Through a Synthetic Sky, What Can and Cannot Be Read](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_vision/01_fly_vision_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_vision/01_fly_vision_scene.png)

*↑ **The Fly's Visual Front End as a Chain of Operators — Turning and Walking Through a Synthetic Sky, What Can and Cannot Be Read** ―― One eye assembled from a 721-ommatidium hexagonal lattice → acceptance function → lamina DC removal → Hassenstein-Reichardt correlators → HS opponent sum, turning under a 1/f banded sky. The direction and waveform of self-rotation are readable (correlation with the true yaw rate +0.785, +0.880 with a membrane low-pass, sign agreement 0.92), but skipping the lamina DC removal makes the correlator emit a DC × high-pass ripple and the correlation drops to +0.504. Walking forward without turning, the full-field readout turns into a −0.689 'rotation'; restricting to the upper field still leaks −0.221 because acceptance functions straddle the horizon (0.000 above el = 2Δρ). The opponent ratio discards speed, so a 1.4°/s flow from a dome 20 m away reads −0.612. The LGMD η peak comes α·l/|v| before collision (−0.1570 s, predicted −0.1567 s) at θ = 23.97° (predicted 24.02°; 24.6° for the exact subtense of a sphere, a quartic root), the sphere τ rides d/|v| with RMS 1e-5 s, and the disk formula misapplied to a sphere reads cos²(θ/2) = 0.75× at 60°. Twelve grating directions give DSI 0.798 with preferred direction 0°.*

[![相関 +0.785(膜 LP つき +0.880、ラミナ段なし +0.504)。対向比は符号の一致度なので、尺度 k は最小二乗で合わせてある。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_vision/02_fly_vision_rotation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_vision/02_fly_vision_rotation.png)

*↑ The measurement ―― 相関 +0.785(膜 LP つき +0.880、ラミナ段なし +0.504)。対向比は符号の一致度なので、尺度 k は最小二乗で合わせてある。 (figure labels are in Japanese; the numbers are the same)*

[![偏り: 全視野 -0.689 / 上半 el>0 -0.221 / el>2Δρ +0.000 / ドーム -0.612](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_vision/03_fly_vision_forward_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_vision/03_fly_vision_forward.png)

*↑ 偏り: 全視野 -0.689 / 上半 el>0 -0.221 / el>2Δρ +0.000 / ドーム -0.612*

[![ピーク -0.157 s(予測 -0.157 s)、θ_peak 24.0°(予測 24.0°)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_vision/04_fly_vision_looming_eta_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_vision/04_fly_vision_looming_eta.png)

*↑ ピーク -0.157 s(予測 -0.157 s)、θ_peak 24.0°(予測 24.0°)。*

[![球式は RMS 0.00001 s で真値に乗る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_vision/05_fly_vision_looming_tau_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_vision/05_fly_vision_looming_tau.png)

*↑ 球式は RMS 0.00001 s で真値に乗る。*

[![負の応答(逆向き)は fly_dsi が 0 に切る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_vision/06_fly_vision_dsi_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_vision/06_fly_vision_dsi.png)

*↑ 負の応答(逆向き)は fly_dsi が 0 に切る。*

```
py -3.11 examples/poc_fly_vision.py
```

Source: [examples/poc_fly_vision.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_fly_vision.py)

This run produced **6 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_fly_vision)

Ops used (notes): [`fly_dsi`](https://furuse.work/ops/flyvision/tuning/fly_dsi.html) · [`fly_emd_response`](https://furuse.work/ops/flyvision/motion/fly_emd_response.html) · [`fly_hex_lattice`](https://furuse.work/ops/flyvision/lattice/fly_hex_lattice.html) · [`fly_hex_resample`](https://furuse.work/ops/flyvision/sample/fly_hex_resample.html) · [`fly_hs_readout`](https://furuse.work/ops/flyvision/integrate/fly_hs_readout.html) · [`fly_lgmd_eta`](https://furuse.work/ops/flyvision/looming/fly_lgmd_eta.html) · [`fly_sky_1f`](https://furuse.work/ops/flyvision/stimulus/fly_sky_1f.html) · [`fly_tau_from_expansion`](https://furuse.work/ops/flyvision/looming/fly_tau_from_expansion.html)

## No.2026.019 —— Focus Stacking — The All-in-Focus Image and the Depth Map Are Different Things

[![Focus Stacking — The All-in-Focus Image and the Depth Map Are Different Things](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/01_stack_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/01_stack.png)

*↑ **Focus Stacking — The All-in-Focus Image and the Depth Map Are Different Things** ―― An all-in-focus image and a depth map pulled from 15 frames blurred by the closed-form circle of confusion. The all-in-focus image reaches 35.89 dB (null 20.98 dB), yet the depth from the same fusion loses to the null by 8x (0.13x) in textureless regions. A relative confidence scores 0.9923 there, higher than the 0.9630 of textured regions; rejecting by absolute value (23600x apart) brings the RMS from 1.505 to 0.878 mm.*

[![合焦点法は全焦点画像と同時に距離画像も出す。ただし左下の無テクスチャの四角だけ、誤差が掃引全域にばらけた乱数になっている(段差帯のハローも見える)—— 絵ほど距離は当てにならない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/02_depth_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/02_depth_map.png)

*↑ The measurement ―― 合焦点法は全焦点画像と同時に距離画像も出す。ただし左下の無テクスチャの四角だけ、誤差が掃引全域にばらけた乱数になっている(段差帯のハローも見える)—— 絵ほど距離は当てにならない。 (figure labels are in Japanese; the numbers are the same)*

[![左下の無テクスチャの四角が、相対量(0.90-1.00 に切って表示)では最も明るい = 自信ありに見え、絶対量(対数)でだけ「何も見えていない」と出る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/03_confidence_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/03_confidence.png)

*↑ 左下の無テクスチャの四角が、相対量(0.90-1.00 に切って表示)では最も明るい = 自信ありに見え、絶対量(対数)でだけ「何も見えていない」と出る。*

[![2 本が離れていく = 残りの誤差は標本化ではなく焦点評価が持っている。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/04_frames_floor_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/04_frames_floor.png)

*↑ 2 本が離れていく = 残りの誤差は標本化ではなく焦点評価が持っている。*

[![焦点を 196.23〜203.00 mm で 17 枚掃引し、1 枚進むたびに「ここまでで焦点評価が最大のフレーム」を画素ごとに選び直す。左 = いまの 1 枚(橙 = この 1 枚で最良が更新された画素)、中 = ここまでの全焦点画像、右](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/05_focus_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/05_focus_sweep.gif)

*↑ The animation ―― 焦点を 196.23〜203.00 mm で 17 枚掃引し、1 枚進むたびに「ここまでで焦点評価が最大のフレーム」を画素ごとに選び直す。左 = いまの 1 枚(橙 = この 1 枚で最良が更新された画素)、中 = ここまでの全焦点画像、右 = ここまでの距離画像。全焦点画像の PSNR は 22.17 dB から 33.69 dB へ育ち、中央の 1 枚(28.52 dB)を上回る。一方、左下の無地の四角は最後まで掃引のたびに塗り替わり(最後の 1 枚でも無地の 12 % が入れ替わる。テクスチャ有は 4 %)、距離誤差は 2.203 mm(テクスチャ有 0.467 mm)で終わる。*

```
py -3.11 examples/poc_focus_stacking.py
```

Source: [examples/poc_focus_stacking.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_focus_stacking.py)

This run produced **5 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_focus_stacking)

Ops used (notes): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`csi_height_map`](https://furuse.work/ops/interferometry/surface/csi_height_map.html) · [`defocus_blur`](https://furuse.work/ops/optics/scene/defocus_blur.html) · [`dilation_circle`](https://furuse.work/ops/2d/region/dilation_circle.html) · [`fuse`](https://furuse.work/ops/3d/tsdf_fusion/fuse.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`laplace`](https://furuse.work/ops/2d/edges/laplace.html) · [`mean_image`](https://furuse.work/ops/2d/smoothing/mean_image.html) · [`optical_camera`](https://furuse.work/ops/optics/scene/optical_camera.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`psnr`](https://furuse.work/ops/imgmetrics/fidelity/psnr.html) · [`sobel_amp`](https://furuse.work/ops/2d/edges/sobel_amp.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html) · [`xcv2_lap_var`](https://furuse.work/ops/2d/features/xcv2_lap_var.html)

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

## No.2026.105 —— Deblurring a Real Photograph — Three Rulers, Three Different Winners

[![Deblurring a Real Photograph — Three Rulers, Three Different Winners](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_deblur_honesty/01_restore_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_deblur_honesty/01_restore.png)

*↑ **Deblurring a Real Photograph — Three Rulers, Three Different Winners** ―― The truth here is a real photograph (scikit-image camera, CC0) and only the degradation is planted: a straight 11-pixel blur at 20 degrees plus noise of sigma 0.004. Doing nothing scores 24.04 dB, and a Wiener filter at the commonly used nsr of 0.005 scores 23.66 — it loses to the null. Stopping there would be misrepresenting the method: sweeping nsr gives 19.18 dB at 0.0005 and 25.40 dB at 0.02, so a fixed knob is not a comparison at all. The knob moves the result by 6.22 dB while deconvolving at all is worth 1.36 dB, a factor of 4.6 — the setting matters more than the method. Applying three rulers to the same seven results puts three different methods first: PSNR picks the correct-PSF Wiener at 25.40 dB, gradient energy picks motion_deblur at 0.2986, which is 1.54 times the truth's own 0.1936 — an image sharper than the truth wins — and blur_effect picks unsharp. The methods those reference-free rulers choose cost 4.98 dB and 3.26 dB against the best. In fairness, blur_effect does rank the truth itself above every method: it measures blur correctly and still loses you three decibels when used to choose. Mistaking the blur length as 21 instead of 11 costs 5.48 dB against doing nothing while raising the gradient energy to 1.37 times the truth, so it looks like it worked. The cliffs: at sigma 0.016 the gain falls to 0.05 dB, and the gain over blur length peaks at 5 pixels, falling at both ends because a short blur has little to remove and a long one has destroyed the information.*

[![固定した nsr で比べると、正しい PSF でもゼロ点に負ける。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_deblur_honesty/02_nsr_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_deblur_honesty/02_nsr.png)

*↑ The measurement ―― 固定した nsr で比べると、正しい PSF でもゼロ点に負ける。 (figure labels are in Japanese; the numbers are the same)*

[![σ=0 で +1.52 dB、σ=0.016 で +0.05 dB。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_deblur_honesty/03_cliffs_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_deblur_honesty/03_cliffs.png)

*↑ σ=0 で +1.52 dB、σ=0.016 で +0.05 dB。*

[![参照なし指標が選ぶ手法は PSNR で 3〜5 dB 劣る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_deblur_honesty/04_metrics_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_deblur_honesty/04_metrics.png)

*↑ 参照なし指標が選ぶ手法は PSNR で 3〜5 dB 劣る。*

```
py -3.11 examples/poc_real_deblur_honesty.py
```

Source: [examples/poc_real_deblur_honesty.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_deblur_honesty.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_real_deblur_honesty)

Ops used (notes): [`iv_motion_deblur`](https://furuse.work/ops/2d/restoration/iv_motion_deblur.html) · [`iv_richardson_lucy`](https://furuse.work/ops/2d/restoration/iv_richardson_lucy.html) · [`iv_unsharp_deblur`](https://furuse.work/ops/2d/restoration/iv_unsharp_deblur.html) · [`psnr`](https://furuse.work/ops/imgmetrics/fidelity/psnr.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`sk_blur_effect`](https://furuse.work/ops/2d/features/sk_blur_effect.html) · [`unsharp`](https://furuse.work/ops/2d/smoothing/unsharp.html)

## No.2026.039 —— Does Super-Resolution Add Information? Downsample With the Truth in Hand, Restore, Count

[![Does Super-Resolution Add Information? Downsample With the Truth in Hand, Restore, Count](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/03_multiframe_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/03_multiframe.png)

*↑ **Does Super-Resolution Add Information? Downsample With the Truth in Hand, Restore, Count** ―― Observations made by downsampling the truth, with single-image upscaling, iterative back-projection and drizzle scored on a resolution table. No single-image upscaler beats the bicubic null by more than +0.036 dB. Drizzling 16 sub-pixel-shifted frames gains +13.96 dB in the undersampled condition, and the modulation of a period-6 pattern beyond Nyquist rises from 0.03 to 0.38.*

[![鮮鋭化だけがナイキスト(周期 8)より細かい列にも縞を作る。それは分解能ではなく**無い縞**。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/01_upscale_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/01_upscale.png)

*↑ The measurement ―― 鮮鋭化だけがナイキスト(周期 8)より細かい列にも縞を作る。それは分解能ではなく**無い縞**。 (figure labels are in Japanese; the numbers are the same)*

[![IBP は周期 12 以上の落ちた変調を戻すが、8 より細かい列は1 本も戻らない(順モデルの零空間)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/02_modulation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/02_modulation.png)

*↑ IBP は周期 12 以上の落ちた変調を戻すが、8 より細かい列は1 本も戻らない(順モデルの零空間)。*

[![上限の線がレンズの許す限界。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/04_multiframe_modulation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/04_multiframe_modulation.png)

*↑ 上限の線がレンズの許す限界。*

[![動画(61 コマ、縞の群を 2 倍で表示): 前半は単一画像の IBP を 0 → 24 回。周期 12 の変調度は 0.78 → 0.96 と戻るが、ナイキスト(周期 8)より細かい列の最大は 0.03 → 0.04 にとどまる —— 順](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/05_growth.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/05_growth.gif)

*↑ The animation ―― 動画(61 コマ、縞の群を 2 倍で表示): 前半は単一画像の IBP を 0 → 24 回。周期 12 の変調度は 0.78 → 0.96 と戻るが、ナイキスト(周期 8)より細かい列の最大は 0.03 → 0.04 にとどまる —— 順モデルの零空間に落ちた縞は何回回しても立たない(PSNR も 21.10 → 21.09 dB で動かない)。後半は標本化不足(σ = 0.30)の 16 枚を 1 枚ずつ drizzle に足す(ずれは相互相関で推定、pixfrac は枚数に合わせて 1.0 → 0.4、被覆の穴は単一画像の bicubic で埋めて割合を表示)。周期 6 の変調度は単一画像の 0.03 から 16 枚で 0.38 まで立ち上がる(レンズの上限 0.46)。PSNR は 28.27 → 42.24 dB。*

```
py -3.11 examples/poc_superresolution_limits.py
```

Source: [examples/poc_superresolution_limits.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_superresolution_limits.py)

This run produced **5 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_superresolution_limits)

Ops used (notes): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`data_to_pixel`](https://furuse.work/ops/annotate/plot/data_to_pixel.html) · [`drizzle_resample`](https://furuse.work/ops/astrostack/stack/drizzle_resample.html) · [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`psnr`](https://furuse.work/ops/imgmetrics/fidelity/psnr.html) · [`ssim`](https://furuse.work/ops/imgmetrics/fidelity/ssim.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html) · [`unsharp`](https://furuse.work/ops/2d/smoothing/unsharp.html) · [`vol_fft_lowpass`](https://furuse.work/ops/3d/frequency/vol_fft_lowpass.html) · [`vol_resize`](https://furuse.work/ops/3d/geom_transform/vol_resize.html) · [`volume_downsample`](https://furuse.work/ops/3d/preprocess/volume_downsample.html)

## No.2026.194 —— Measuring Image-Quality Metrics Against a Public Ground Truth — TID2013's 3,000 Images × 971 Observers and the Authors' Published Values as the Gate

[![Measuring Image-Quality Metrics Against a Public Ground Truth — TID2013's 3,000 Images × 971 Observers and the Authors' Published Values as the Gate](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_iqa_tid2013/06_tid2013_pair_ssim_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_iqa_tid2013/06_tid2013_pair_ssim_map.png)

*↑ **Measuring Image-Quality Metrics Against a Public Ground Truth — TID2013's 3,000 Images × 971 Observers and the Authors' Published Values as the Gate** ―― The first image-side PoC under the new rule of bringing the truth in from outside. Truth = TID2013 (Ponomarenko et al., 25 references × 24 distortions × 5 levels = 3,000 images, MOS from 971 observers); reference = the 14 metric value files the authors ship with the data (psnr.txt, ssim.txt, …) and their published rank-correlation table. The new module iqatid (11 ops): the authors' luminance convention (BT.601 limited-range integer Y′, not stated on the page and found by measurement; full-range Y is 1.321 dB off), Spearman with average ranks and Kendall τ_b (these two reproduce all 14 published rows), the published table, the index reader with validation (3,000 rows, the name set must match the files on disk, case-insensitive), evaluation, comparison with the authors' values and per-distortion correlation. Figures: MOS vs PSNR / SSIM scatter, SROCC per distortion type (local block distortion 0.15 / 0.63, contrast 0.44 / 0.45 and saturation 0.22 / 0.22 are weak), histograms of the differences to the authors' values, a table of published / reproduced / Fullseye values for 14 metrics, and one reference–distorted pair with its SSIM map. 21 gates: closed forms for the rank correlations (monotone 1, reversed −1, hand-computed ties ρ = 8.5/√95 and τ_b = 7/√90, 1e-12 against the second implementation in graphinv), Y′ endpoints 16 / 235, PSNR of a 1-LSB shift = 48.13 dB, SSIM identity 1, the 14-row published table. Real data, 3,000 pairs in 110 s: Fullseye's RGB PSNR matches the authors' PSNRc to four decimals (max 0.00005 dB), luminance PSNR matches to 0.00017 dB on the 2,774 pairs outside reference I12 (I12's 115 pairs have 28 pixels whose luminance lands exactly on .5 and round the other way, 0.00058 dB; reported as a separate gate rather than silently dropped), SSIM on Y′ to 0.000051, rank correlations PSNR 0.6395 / 0.4699 (published 0.640 / 0.470) and SSIM 0.6370 / 0.4635 (0.637 / 0.464), and the 14 authors' rows reproduced to 0.00048. The authors write exact matches of luminance PSNR as 100000.0 (111 rows, all saturation changes). Honestly: the four-decimal agreement comes from following the same original implementation's conventions (the old ssim_index.m: 11×11 Gaussian σ 1.5, borders cropped, no downsampling), not from SSIM being good (it ranks 10th of 14). FSIM / FSIMc / VIF / GMSD are not implemented; only their published values are tabulated. Images and MOS are not committed (research-and-education-only terms, FULLSEYE_TID2013_DATA). CI runs the synthetic gates only.*

[![971 人の MOS と Fullseye の PSNR(作者の輝度規約 Y′、psnr.txt と 4 桁一致)。順位相関は公表値どおり低い —— PSNR は歪み種が混ざると主観に合わない。 彩度変化で Y′ が変わらない 106 組(](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_iqa_tid2013/01_tid2013_mos_vs_psnr_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_iqa_tid2013/01_tid2013_mos_vs_psnr.png)

*↑ The measurement ―― 971 人の MOS と Fullseye の PSNR(作者の輝度規約 Y′、psnr.txt と 4 桁一致)。順位相関は公表値どおり低い —— PSNR は歪み種が混ざると主観に合わない。 彩度変化で Y′ が変わらない 106 組(PSNR = inf、MOS 3.4〜6.0)は図に載らない(順位相関には最大の順位で入れてある)。 (figure labels are in Japanese; the numbers are the same)*

[![同じ 3,000 組と Fullseye の SSIM(Wang 2004 の既定、ssim.txt と 4 桁一致)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_iqa_tid2013/02_tid2013_mos_vs_ssim_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_iqa_tid2013/02_tid2013_mos_vs_ssim.png)

*↑ 同じ 3,000 組と Fullseye の SSIM(Wang 2004 の既定、ssim.txt と 4 桁一致)。*

[![歪み種ごとの順位相関(各 25 参照 × 5 段)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_iqa_tid2013/03_tid2013_srocc_by_distortion_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_iqa_tid2013/03_tid2013_srocc_by_distortion.png)

*↑ 歪み種ごとの順位相関(各 25 参照 × 5 段)。*

[![作者値との行ごとの差。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_iqa_tid2013/04_tid2013_author_diff_hist_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_iqa_tid2013/04_tid2013_author_diff_hist.png)

*↑ 作者値との行ごとの差。*

[![公表表(ページ / readme TABLE III・IV)と、同梱の作者値 + mos.txt から平均順位・τ_b で再現した値、Fullseye 実装がある 3 本の自前値。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_iqa_tid2013/05_tid2013_published_vs_reproduced_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_iqa_tid2013/05_tid2013_published_vs_reproduced.png)

*↑ 公表表(ページ / readme TABLE III・IV)と、同梱の作者値 + mos.txt から平均順位・τ_b で再現した値、Fullseye 実装がある 3 本の自前値。*

```
py -3.11 examples/poc_iqa_tid2013.py
```

Source: [examples/poc_iqa_tid2013.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_iqa_tid2013.py)

This run produced **6 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_iqa_tid2013)

Ops used (notes): [`luma_limited_u8`](https://furuse.work/ops/imgmetrics/iqa/luma_limited_u8.html) · [`psnr`](https://furuse.work/ops/imgmetrics/fidelity/psnr.html) · [`rank_data`](https://furuse.work/ops/imgmetrics/iqa/rank_data.html) · [`rank_kendall_b`](https://furuse.work/ops/imgmetrics/iqa/rank_kendall_b.html) · [`rank_spearman`](https://furuse.work/ops/imgmetrics/iqa/rank_spearman.html) · [`ssim`](https://furuse.work/ops/imgmetrics/fidelity/ssim.html) · [`ssim_map`](https://furuse.work/ops/imgmetrics/fidelity/ssim_map.html) · [`tid2013_by_distortion`](https://furuse.work/ops/imgmetrics/iqa/tid2013_by_distortion.html) · [`tid2013_compare`](https://furuse.work/ops/imgmetrics/iqa/tid2013_compare.html) · [`tid2013_evaluate`](https://furuse.work/ops/imgmetrics/iqa/tid2013_evaluate.html) · [`tid2013_index`](https://furuse.work/ops/imgmetrics/iqa/tid2013_index.html) · [`tid2013_metric_values`](https://furuse.work/ops/imgmetrics/iqa/tid2013_metric_values.html) · [`tid2013_published`](https://furuse.work/ops/imgmetrics/iqa/tid2013_published.html) · [`tid2013_root`](https://furuse.work/ops/imgmetrics/iqa/tid2013_root.html)

## No.2026.197 —— Perceptual Indices FSIM / FSIMc / GMSD / VIF Matched to Four Digits Against an External Truth — TID2013's Three Author-Value Files and the Published Rank-Correlation Tables

[![Perceptual Indices FSIM / FSIMc / GMSD / VIF Matched to Four Digits Against an External Truth — TID2013's Three Author-Value Files and the Published Rank-Correlation Tables](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_iqa_fsim_gmsd_vif/01_iqa_tid2013_mos_vs_fsim_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_iqa_fsim_gmsd_vif/01_iqa_tid2013_mos_vs_fsim.png)

*↑ **Perceptual Indices FSIM / FSIMc / GMSD / VIF Matched to Four Digits Against an External Truth — TID2013's Three Author-Value Files and the Published Rank-Correlation Tables** ―― The second exhibit of the IQA series (the first covered PSNR / SSIM). The first exhibit had listed FSIM / FSIMc / VIFP as 'not implemented, published values only'; here they are implemented in numpy + scipy alone (new module iqafsim, 7 ops: fsim / fsimc / fsim_pair / gmsd / gmsd_map / vifp / phase_congruency_pc) and GMSD, absent from the distribution, is added. Primary sources are four papers: FSIM = Zhang, Zhang, Mou & Zhang, IEEE TIP 2011 (phase congruency after Kovesi 1999; his public code is MIT, so the noise-threshold heuristics come from there), GMSD = Xue, Zhang, Mou & Bovik, IEEE TIP 2014, VIF = Sheikh & Bovik, IEEE TIP 2006 in its pixel-domain form (the 'VIFP' row of the TID2013 paper; the steerable 'VIF' row is a different implementation and is not reproduced). The FSIM authors' code is for research and education only, so nothing was ported: the index was written from the paper's equations and only the constants were checked against §IV-A. The truth comes in three grades. (1) The author-value files FSIMc.txt / FSIM.txt / VIFP.txt (3,000 rows, four decimals), row by row: max |difference| 5.0e-5 / 5.0e-5 / 6.8e-5 — inside the rounding width. (2) The four-digit rank correlations of Tables 4/5 of the TID2013 paper: unrounded values give FSIM 0.8008 / 0.6295 (paper 0.8007 / 0.6300), FSIMc 0.8510 / 0.6665 (0.8510 / 0.6669), VIFP 0.6080 / 0.4560 (0.6084 / 0.4567); rounding our values to four decimals as the authors did reproduces all three on the full set and on the seven subsets (Noise / Actual / Simple / Exotic / New / Color / Full) with Δ 0.0000. (3) GMSD has no author file (the distribution is from 2013, GMSD from 2014); it is checked against a secondary source (Nafchi et al. 2016), |ρ| 0.8044 / 0.6339, to 0.0006 / 0.0005 — stated in the table as a grade lower. The input conventions were found by measurement (no page states them): FSIM.txt and VIFP.txt are computed on the same limited-range integer luma Y′ (16–235) as PSNR / SSIM, while FSIMc.txt is computed on the colour bitmaps via full-range YIQ. So FSIM.txt is not the FSIM component inside the FSIMc computation (measuring FSIM on the colour image's Y misses FSIM.txt by up to 0.0318 — kept as a counter-example gate). Figures: four MOS scatter plots (SROCC and published value in the title), SROCC per distortion type for 24 types (under 18, colour saturation, the three luma-only indices collapse and only FSIMc survives), and a table with the grade of the truth as a column. 26 gates (10 synthetic, 6 on the default real subset, 10 more with --full): identities FSIM = FSIMc = 1, GMSD = 0, VIF = 1; monotonic in noise σ (rank correlation ∓1); FSIM / GMSD symmetric and VIF asymmetric (it divides by the reference's information); phase-congruency gain invariance (1e-10 with ε = 1e-12; the 2.8e-5 residual at the default ε = 1e-4 scales exactly with ε); the even-kernel 'same' convention; round(1.5) = 2; correlation 0.66 with the existing monogenic phase congruency as a second implementation; GMS range and VIF > 1 under contrast enhancement (the authors' maximum 1.1379 is also distortion 17); fail-closed; agreement of the four-digit and three-digit published tables; on real data the three row-wise gates, the counter-example, GMSD's negative correlation and the per-type table. Default is the first 120 pairs (reference I01, 24 types × 5 levels) in 30 s; --full runs all 3,000 pairs in 11 minutes. Honestly: four-digit agreement comes from following the same conventions, not from the indices' merit (FSIMc 0.851 ranks first, VIFP 0.608 thirteenth); GMSD is checked only against a secondary source; steerable VIF is not implemented; distortions 16–18 are weak for all four. Traps: scipy's even-kernel 'same' is half a pixel off (a 2×2 average gives a different answer), round(1.5) goes away from zero, ε belongs in the unit-vector normalisation only (in the denominator it breaks gain invariance by 3e-5), GMSD's sign (the published tables list |ρ|; the first run failed by −1.6), and the paper's four-digit tables are computed from the authors' four-decimal text files (rounding ties 106–122 pairs of distortion 18 and moves the New / Color columns in the fourth digit).*

[![FSIMC と 971 人の MOS(3,000 組)。作者値 FSIMc.txt と 4 桁一致(色画像 → YIQ full range)。TID2013 全体で 1 位の指標。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_iqa_fsim_gmsd_vif/02_iqa_tid2013_mos_vs_fsimc_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_iqa_fsim_gmsd_vif/02_iqa_tid2013_mos_vs_fsimc.png)

*↑ The measurement ―― FSIMC と 971 人の MOS(3,000 組)。作者値 FSIMc.txt と 4 桁一致(色画像 → YIQ full range)。TID2013 全体で 1 位の指標。 (figure labels are in Japanese; the numbers are the same)*

[![VIFP と 971 人の MOS(3,000 組)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_iqa_fsim_gmsd_vif/03_iqa_tid2013_mos_vs_vifp_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_iqa_fsim_gmsd_vif/03_iqa_tid2013_mos_vs_vifp.png)

*↑ VIFP と 971 人の MOS(3,000 組)。*

[![GMSD と 971 人の MOS(3,000 組)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_iqa_fsim_gmsd_vif/04_iqa_tid2013_mos_vs_gmsd_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_iqa_fsim_gmsd_vif/04_iqa_tid2013_mos_vs_gmsd.png)

*↑ GMSD と 971 人の MOS(3,000 組)。*

[![歪み種ごとの順位相関。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_iqa_fsim_gmsd_vif/05_iqa_tid2013_srocc_by_distortion_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_iqa_fsim_gmsd_vif/05_iqa_tid2013_srocc_by_distortion.png)

*↑ 歪み種ごとの順位相関。*

[![真値の等級を列にした: FSIM / FSIMc / VIFP は作者値ファイル(4 桁)と行ごとに比べられる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_iqa_fsim_gmsd_vif/06_iqa_tid2013_published_vs_reproduced_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_iqa_fsim_gmsd_vif/06_iqa_tid2013_published_vs_reproduced.png)

*↑ 真値の等級を列にした: FSIM / FSIMc / VIFP は作者値ファイル(4 桁)と行ごとに比べられる。*

```
py -3.11 examples/poc_iqa_fsim_gmsd_vif.py
```

Source: [examples/poc_iqa_fsim_gmsd_vif.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_iqa_fsim_gmsd_vif.py)

This run produced **6 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_iqa_fsim_gmsd_vif)

Ops used (notes): [`fsim`](https://furuse.work/ops/imgmetrics/perceptual/fsim.html) · [`fsim_pair`](https://furuse.work/ops/imgmetrics/perceptual/fsim_pair.html) · [`fsimc`](https://furuse.work/ops/imgmetrics/perceptual/fsimc.html) · [`gmsd`](https://furuse.work/ops/imgmetrics/perceptual/gmsd.html) · [`gmsd_map`](https://furuse.work/ops/imgmetrics/perceptual/gmsd_map.html) · [`phase_congruency_pc`](https://furuse.work/ops/imgmetrics/perceptual/phase_congruency_pc.html) · [`rank_kendall_b`](https://furuse.work/ops/imgmetrics/iqa/rank_kendall_b.html) · [`rank_spearman`](https://furuse.work/ops/imgmetrics/iqa/rank_spearman.html) · [`tf_phase_congruency`](https://furuse.work/ops/2d/edges/tf_phase_congruency.html) · [`tid2013_by_distortion`](https://furuse.work/ops/imgmetrics/iqa/tid2013_by_distortion.html) · [`tid2013_compare`](https://furuse.work/ops/imgmetrics/iqa/tid2013_compare.html) · [`tid2013_evaluate`](https://furuse.work/ops/imgmetrics/iqa/tid2013_evaluate.html) · [`tid2013_index`](https://furuse.work/ops/imgmetrics/iqa/tid2013_index.html) · [`tid2013_metric_values`](https://furuse.work/ops/imgmetrics/iqa/tid2013_metric_values.html) · [`tid2013_published`](https://furuse.work/ops/imgmetrics/iqa/tid2013_published.html) · [`tid2013_root`](https://furuse.work/ops/imgmetrics/iqa/tid2013_root.html) · [`vifp`](https://furuse.work/ops/imgmetrics/perceptual/vifp.html)

## No.2026.135 —— Holding a Course with a Fly's Optic Lobe Alone — From the Lamina to the Steering, Without Learning

[![Holding a Course with a Fly's Optic Lobe Alone — From the Lamina to the Steering, Without Learning](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_optomotor_steering/06_follow.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_optomotor_steering/06_follow.gif)

*↑ **Holding a Course with a Fly's Optic Lobe Alone — From the Lamina to the Steering, Without Learning** ―― A vehicle whose heading drifts under a disturbance, carrying nothing but a compound eye and closed-form circuitry, holds its course: the fly's optomotor response built out of fullseye operators alone and measured next to a ground-truth gyro. Every stage is a closed form and nothing is trained: hexagonal sampling (fly_hex_resample), lamina adaptation and band-pass (fly_lamina_filter), the ON/OFF split (fly_onoff_split), direction selectivity in all six lattice directions (fly_t4t5_field), the local flow (fly_flow_from_directions), a linear fit against the matched filter (fly_matched_filter / fly_egomotion_from_flow), and a six-neuron, eight-synapse steering circuit run as conductances (graph_conductance_states). Each stage has an exact identity: brightening the whole scene ten thousand times leaves the lamina output unchanged (Weber, 7e-16), the three-arm T4 model with Haag et al. 2016's verbatim constants (tau = 250 ms, k = 5/5/10) returns the paper's 24.9636 and 0.8195 on its two-column stimulus, and the paper's claim that the two mechanisms are complementary becomes a product identity (4.161 x 7.321 = 30.461 = the whole model) that holds to machine precision; the matched filter's 1.7 rad/s comes back to nine digits. The limits are measured too: on the classical striped drum the estimate tracks a time-varying rotation at 0.976 correlation, in a natural 1/f scene at 0.897, and the single calibration gain it needs is 2.64 on the drum against 6.76 and 7.88 in natural scenes - 3.0x between kinds of scene and 1.16x between two scenes of identical statistics, because a correlation detector reports contrast-weighted motion rather than velocity. A single 80-degree eye measuring the same +0.5 rad/s across twelve scenes scatters by 1.05 of its mean and gets the sign of the rotation wrong in four of them; merging three eyes into 250 degrees with fly_eye_merge drops the scatter to 0.44 and the sign errors to zero - the width of a compound eye is not decoration. In closed loop (calibrated in scene A, flown in an unseen scene B) the open loop drifts 51 degrees, the visual reflex 33, and the ground-truth gyro 23: a reflex has no absolute heading and cannot null the drift, which is where the central complex would come in. Writing the steering on the connectome side gives the same 33 degrees, and the membrane potential is a convex combination of the reversal potentials so it cannot diverge. No data ships; the scenes are generated from seeds by fly_sky_1f.*

[![left to right, top to bottom: what the ommatidia see, the lamina's contrast (brightness thrown away), the ON and OFF cha](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_optomotor_steering/01_pathway_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_optomotor_steering/01_pathway.png)

*↑ The measurement ―― left to right, top to bottom: what the ommatidia see, the lamina's contrast (brightness thrown away), the ON and OFF channels, and the direction-selective field read as a local flow. The eye is turning at 0.5 rad/s in a 1/f panorama; nothing here was trained. (figure labels are in Japanese; the numbers are the same)*

[![each scene is fitted with its own single gain; the striped drum is nearly linear, and a natural 1/f ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_optomotor_steering/02_tuning_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_optomotor_steering/02_tuning.png)

*↑ each scene is fitted with its own single gain; the striped drum is nearly linear, and a natural 1/f scene needs a gain 3.0x larger — a correlation det…*

[![a narrow eye is at the mercy of whichever few large features are in front of it: over eight scenes o](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_optomotor_steering/03_wide_eye_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_optomotor_steering/03_wide_eye.png)

*↑ a narrow eye is at the mercy of whichever few large features are in front of it: over eight scenes of identical statistics it scatters and gets the si…*

[![the disturbance has a steady bias, so the open loop drifts away; the optomotor reflex cuts the drift](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_optomotor_steering/04_closed_loop_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_optomotor_steering/04_closed_loop.png)

*↑ the disturbance has a steady bias, so the open loop drifts away; the optomotor reflex cuts the drift but cannot null it — a reflex has no absolute hea…*

[![the wiring is written by hand as a synapse table and run as a conductance circuit; the state is a co](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_optomotor_steering/05_circuit_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_optomotor_steering/05_circuit.png)

*↑ the wiring is written by hand as a synapse table and run as a conductance circuit; the state is a convex combination of the reversal potentials, so it…*

```
py -3.11 examples/poc_fly_optomotor_steering.py
```

Source: [examples/poc_fly_optomotor_steering.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_fly_optomotor_steering.py)

This run produced **7 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_fly_optomotor_steering)

Ops used (notes): [`fly_egomotion_from_flow`](https://furuse.work/ops/flyvision/selfmotion/fly_egomotion_from_flow.html) · [`fly_eye_merge`](https://furuse.work/ops/flyvision/selfmotion/fly_eye_merge.html) · [`fly_flow_from_directions`](https://furuse.work/ops/flyvision/direction/fly_flow_from_directions.html) · [`fly_hex_lattice`](https://furuse.work/ops/flyvision/lattice/fly_hex_lattice.html) · [`fly_hex_resample`](https://furuse.work/ops/flyvision/sample/fly_hex_resample.html) · [`fly_lamina_filter`](https://furuse.work/ops/flyvision/lamina/fly_lamina_filter.html) · [`fly_matched_filter`](https://furuse.work/ops/flyvision/selfmotion/fly_matched_filter.html) · [`fly_onoff_split`](https://furuse.work/ops/flyvision/lamina/fly_onoff_split.html) · [`fly_sky_1f`](https://furuse.work/ops/flyvision/stimulus/fly_sky_1f.html) · [`fly_t4t5_field`](https://furuse.work/ops/flyvision/direction/fly_t4t5_field.html) · [`graph_conductance_states`](https://furuse.work/ops/conngraph/circuit/graph_conductance_states.html) · [`graph_from_synapses`](https://furuse.work/ops/conngraph/construct/graph_from_synapses.html)

## No.2026.148 —— The Exact Distance at Which Detail Vanishes, and the Area of a Changing Shape

[![The Exact Distance at Which Detail Vanishes, and the Area of a Changing Shape](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/04_vanish_at_p_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/04_vanish_at_p.png)

*↑ **The Exact Distance at Which Detail Vanishes, and the Area of a Changing Shape** ―― Both a picture that mixes high and low frequencies and a shape that morphs smoothly carry exact truths that can be measured straight off the image - and the customary way of making them is the one that misses those truths. The first concerns orthogonality. Splitting an image into low and high parts with an ideal frequency mask makes the two exactly orthogonal, so the energies add: across four cut-off frequencies the relative discrepancy in E(low) + E(high) - E(original) is 1.9e-16. The textbook construction - blur with a Gaussian, call the remainder the high part - misses by 0.53 % to 3.10 %, even though both reconstruct the original exactly when added back: being invertible and being orthogonal are different properties. The discrepancy is also not monotone in the blur: the worst case is the weakest blur and the best is in the middle of the range, so neither strengthening nor weakening it fixes the problem. The second concerns distance. Binning k pixels - what moving away does - has the transfer function sin(pi f k)/(k sin(pi f)), which is exactly zero when f times k is an integer, so a pattern of period p pixels vanishes exactly when binned at p pixels (1.4e-14 over five periods). More strongly, the binned picture can be written pixel by pixel in closed form - the amplitude and the fact that the binned pixel's centre shifts by (k-1)/2 - agreeing to 2.8e-14 over every pixel for bin widths 1 through 48. The third concerns shape. Interpolating polygon vertices linearly makes the enclosed area an exact quadratic in t, so three frames predict all of them (2.4e-15 across three shapes), and this survives measurement from the picture: rasterising the polygon and counting brings the deviation from 1.10 % on a 128 grid down to 0.053 % on a 512 grid with each pixel split four ways - and splitting a pixel into 4x4 gives exactly the same number as using a four times finer grid. The fourth is where measurement from a picture breaks. Morphing to the same polygon with its vertices reversed makes the signed area linear in t, vanishing at t = 0.5 where the polygon collapses to a line, and the quadratic prediction holds to 3.4e-15; but a picture only yields positive area, so the parabola folds and the three-frame prediction is off by exactly one quarter of the maximum - measured at 25.0 % for two different shapes. Even the size of the error has a closed form. The fifth pairs two exact spline properties: Catmull-Rom passes through its control points at distance 0.0e+00, while a Bezier curve does not pass through them but never leaves their convex hull (401 of 401 points across four sets) - exactly complementary guarantees. Three predictions were wrong and have been left in: that the bin width at which a hybrid image switches could be predicted from the cut-off frequency as 1/(2 fc), when in fact tripling the cut-off barely moves the measured switch because what governs it is the period the high-frequency picture actually contains; that the Gaussian discrepancy would grow with the blur; and that reading amplitude off the picture's maximum and minimum would match the closed form, when at a bin width of six it reads 20.7 % low because the pixels never land on the crest - the formula is right even where no pixel sits. No new operator was added.*

[![低い周波数に粗い模様、高い周波数に細かい模様を入れた 1 枚を、束ねながら見たもの。**束ねるのは「遠ざかる」こと**で、細かいほうが先に消える。ただし ★**いつ消えるかは遮断周波数では決まらない** —— 下の数表の「外した予言」を参照](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/01_hybrid_near_far_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/01_hybrid_near_far.png)

*↑ The measurement ―― 低い周波数に粗い模様、高い周波数に細かい模様を入れた 1 枚を、束ねながら見たもの。**束ねるのは「遠ざかる」こと**で、細かいほうが先に消える。ただし ★**いつ消えるかは遮断周波数では決まらない** —— 下の数表の「外した予言」を参照。 (figure labels are in Japanese; the numbers are the same)*

[![**どちらも足せば元に戻る**(再構成の誤差は両方 1e-13 未満)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/02_orthogonal_split_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/02_orthogonal_split.png)

*↑ **どちらも足せば元に戻る**(再構成の誤差は両方 1e-13 未満)。*

[![k = 24 と k = 48(f·k が整数)で **厳密に 0**、その間では戻る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/05_transfer_curve_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/05_transfer_curve.png)

*↑ k = 24 と k = 48(f·k が整数)で **厳密に 0**、その間では戻る。*

[![閉形式なら 2.4e-15。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/09_area_from_picture_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/09_area_from_picture.png)

*↑ 閉形式なら 2.4e-15。*

[![薄い折れ線が制御点をつないだもの、濃い線が Catmull-Rom。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/12_catmull_through_points_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/12_catmull_through_points.png)

*↑ 薄い折れ線が制御点をつないだもの、濃い線が Catmull-Rom。*

[![6 角形が別の 6 角形へ変わって戻るところ。★見た目は連続に変わるが、**囲む面積は t の 厳密な 2 次式**に乗っている(次の図)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/06_morph_loop.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/06_morph_loop.gif)

*↑ The animation ―― 6 角形が別の 6 角形へ変わって戻るところ。★見た目は連続に変わるが、**囲む面積は t の 厳密な 2 次式**に乗っている(次の図)。*

```
py -3.11 examples/poc_vanishing_detail_and_morphing_area.py
```

Source: [examples/poc_vanishing_detail_and_morphing_area.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_vanishing_detail_and_morphing_area.py)

This run produced **14 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area)

Ops used (notes): [`convex_hull`](https://furuse.work/ops/3d/bounds/convex_hull.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`morph`](https://furuse.work/ops/shape2d/morph/morph.html)

## No.2026.184 —— The Segmentation Gauntlet — Ten Methods Across Six Worlds With Ground Truth, and Which Measure Is Blind to Which Failure

[![The Segmentation Gauntlet — Ten Methods Across Six Worlds With Ground Truth, and Which Measure Is Blind to Which Failure](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/01_worlds_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/01_worlds.png)

*↑ **The Segmentation Gauntlet — Ten Methods Across Six Worlds With Ground Truth, and Which Measure Is Blind to Which Failure** ―― Before adding segmentation methods, the measures and the ground truth come first — new modules segeval (contingency table, Dice/Jaccard, boundary F, Hausdorff/ASSD, over/under-segmentation, object-count matching, a score card; each op gated by an identity or a second implementation) and segworld (six synthetic worlds with ground truth: touching equal-radius blobs with the closed-form lens area, Voronoi grains whose boundary length matches scipy's ridges to 1e-9, parts with shadows, same-mean regions differing only in texture, an illumination gradient, and 1–3 px thin structures). Ten existing methods (Otsu, local threshold, Niblack, Sauvola, Chan–Vese, random walker, two watersheds, Felzenszwalb, SLIC) run with default knobs across every world. Gates: truth vs truth scores perfectly on every measure in all six worlds / mask measures are blind to merging (Otsu scores J=0.95 while 9 of 10 blobs are merged) / boundary measures are blind to over-segmentation (gradient watershed BF=1.00 with 339 over-segmented) / Sauvola gets every grain count right but drops the boundary band, J=0.91 / on parts with shadows every method scores J < 0.3, and even a threshold oracle that sees the truth only J=0.29 / textures: mask methods ARI < 0.3, local-σ k-means ARI=0.92 / illumination gradient: global Otsu J=0.21, flat-fielded J=1.00 / thin structures: Otsu's boundary F is 1.00 yet noise grains over-segment 29. Honestly: method knobs are fixed at defaults (some would recover if tuned), boundary F is the distance-transform BF rather than Martin 2004's bipartite matching, and the edge condition in count matching is our own definition. 10 gates, 2.0 s.*

[![Jaccard は物体マスク(格子を返す手法は —)。VI = Meilă の情報の変分(0 が一致)、ARI = 補正 Rand、境界 F は τ = 2 px、HD95 = 境界の Hausdorff の 95 % 点。過分割/未分割は](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/02_scores_blobs_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/02_scores_blobs.png)

*↑ The measurement ―― Jaccard は物体マスク(格子を返す手法は —)。VI = Meilă の情報の変分(0 が一致)、ARI = 補正 Rand、境界 F は τ = 2 px、HD95 = 境界の Hausdorff の 95 % 点。過分割/未分割は分割表の多数決の多重度、一致/分裂/融合/欠落/偽は主に重なる辺の次数。最後の行はルールの直し方。 (figure labels are in Japanese; the numbers are the same)*

[![Jaccard は物体マスク(格子を返す手法は —)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/03_scores_voronoi_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/03_scores_voronoi.png)

*↑ Jaccard は物体マスク(格子を返す手法は —)。*

[![Jaccard は物体マスク(格子を返す手法は —)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/04_scores_parts_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/04_scores_parts.png)

*↑ Jaccard は物体マスク(格子を返す手法は —)。*

[![Jaccard は物体マスク(格子を返す手法は —)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/05_scores_texture_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/05_scores_texture.png)

*↑ Jaccard は物体マスク(格子を返す手法は —)。*

[![Jaccard は物体マスク(格子を返す手法は —)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/06_scores_gradient_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/06_scores_gradient.png)

*↑ Jaccard は物体マスク(格子を返す手法は —)。*

[![触れ合う粒: 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_random_wa](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/08_gauntlet_blobs.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/08_gauntlet_blobs.gif)

*↑ The animation ―― 触れ合う粒: 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_random_walker, watersheds, sg_watershed_gradient, sk_felzenszwalb, sk_slic, edt_watershed)。*

[![結晶粒(ボロノイ): 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_rando](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/09_gauntlet_voronoi.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/09_gauntlet_voronoi.gif)

*↑ The animation ―― 結晶粒(ボロノイ): 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_random_walker, watersheds, sg_watershed_gradient, sk_felzenszwalb, sk_slic)。*

[![影のある部品: 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_random_w](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/10_gauntlet_parts.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/10_gauntlet_parts.gif)

*↑ The animation ―― 影のある部品: 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_random_walker, watersheds, sg_watershed_gradient, sk_felzenszwalb, sk_slic)。*

[![質感だけ違う領域: 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_random](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/11_gauntlet_texture.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/11_gauntlet_texture.gif)

*↑ The animation ―― 質感だけ違う領域: 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_random_walker, watersheds, sg_watershed_gradient, sk_felzenszwalb, sk_slic, texture_kmeans)。*

[![照明の勾配: 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_random_wa](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/12_gauntlet_gradient.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/12_gauntlet_gradient.gif)

*↑ The animation ―― 照明の勾配: 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_random_walker, watersheds, sg_watershed_gradient, sk_felzenszwalb, sk_slic, flat_field_otsu)。*

[![細い構造: 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_random_wal](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/13_gauntlet_thin.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/13_gauntlet_thin.gif)

*↑ The animation ―― 細い構造: 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_random_walker, watersheds, sg_watershed_gradient, sk_felzenszwalb, sk_slic)。*

```
py -3.11 examples/poc_segmentation_gauntlet.py
```

Source: [examples/poc_segmentation_gauntlet.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_segmentation_gauntlet.py)

This run produced **13 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_segmentation_gauntlet)

Ops used (notes): [`blob_distance`](https://furuse.work/ops/blob/split/blob_distance.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`local_threshold`](https://furuse.work/ops/2d/segmentation/local_threshold.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`seg_dice_jaccard`](https://furuse.work/ops/segmentation/score/seg_dice_jaccard.html) · [`seg_score_card`](https://furuse.work/ops/segmentation/score/seg_score_card.html) · [`sg_watershed_gradient`](https://furuse.work/ops/2d/segment/sg_watershed_gradient.html) · [`sk_chan_vese`](https://furuse.work/ops/2d/segmentation/sk_chan_vese.html) · [`sk_felzenszwalb`](https://furuse.work/ops/2d/segmentation/sk_felzenszwalb.html) · [`sk_niblack`](https://furuse.work/ops/2d/segmentation/sk_niblack.html) · [`sk_sauvola`](https://furuse.work/ops/2d/segmentation/sk_sauvola.html) · [`sk_slic`](https://furuse.work/ops/2d/segmentation/sk_slic.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`watersheds`](https://furuse.work/ops/2d/segmentation/watersheds.html) · [`world_blobs_touching`](https://furuse.work/ops/segmentation/world/world_blobs_touching.html) · [`world_gradient_illumination`](https://furuse.work/ops/segmentation/world/world_gradient_illumination.html) · [`world_grains_voronoi`](https://furuse.work/ops/segmentation/world/world_grains_voronoi.html) · [`world_parts_with_shadow`](https://furuse.work/ops/segmentation/world/world_parts_with_shadow.html) · [`world_texture_regions`](https://furuse.work/ops/segmentation/world/world_texture_regions.html) · [`world_thin_structures`](https://furuse.work/ops/segmentation/world/world_thin_structures.html) · [`xsk_random_walker`](https://furuse.work/ops/2d/segmentation/xsk_random_walker.html)

## No.2026.186 —— Active Contours and Level Sets — Checking With Closed Forms How a Contour Shrinks, Enters a Concavity and Stops at an Edge

[![Active Contours and Level Sets — Checking With Closed Forms How a Contour Shrinks, Enters a Concavity and Stops at an Edge](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_active_contours/01_inputs_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_active_contours/01_inputs.png)

*↑ **Active Contours and Level Sets — Checking With Closed Forms How a Contour Shrinks, Enters a Concavity and Stops at an Edge** ―― Segmentation expansion, batch 2 — new module segcontour, 10 ops (snake, gradient vector flow, Chan–Vese energy and evolution, morphological Chan–Vese, morphological geodesic active contour with the edge-stopping function, signed-distance reinitialisation, DRLSE, mean curvature flow). Each op is gated by a closed form or a second implementation: with no external force a circular snake shrinks exactly as the circulant-matrix eigenvalues say (error 3e-14) and matches skimage's active_contour to 1e-13 / curvature flow loses area at dA/dt = −2π (circle −6.2767, a concave star −6.2822) / after reinitialisation |∇φ| sits at 0.987–1.012 (10–90 %) and the zero level set does not move / the classical snake's energy never rises (γ ≥ L, 0 increases), and Chan–Vese (alternating minimisation of the convex relaxation) is monotone in all four worlds / Dice 0.995 against the existing op sk_chan_vese. Scored with batch 1's segeval and segworld: the classical snake cannot enter a U-shaped concavity (it bridges it completely and also floats off the flat sides — the edge-gradient force only reaches near edges), while the same α, β, γ with a GVF external force goes in (1.0 % bridged, Dice 0.993) / under an illumination gradient global two-mean Chan–Vese loses (J = 0.187) and edge-stopping local methods win (geodesic AC 0.960, DRLSE 0.938) / touching blobs score Dice 0.97 as a mask yet all 10 merge into one / on shadowed parts every contour method stays below J 0.7. Honestly: Chan–Vese 2001 does not claim monotone descent (the gate is on the convex side); the GVF, morphological-snake, DRLSE and Sussman equations were not checked against the original papers; DRLSE's energy rose 247 times on the gradient world (explicit steps, not gated). 12 gates, 6.4 s.*

[![c の更新(内外の平均)と、c を固定した凸緩和(Chan–Esedoglu–Nikolova)の交互最小化。どの世界でも1 度も増えず、分割が変わらなくなった所で止まる(門 5)。止まった所が真値に近いかは別(表を見る)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_active_contours/02_cv_energy_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_active_contours/02_cv_energy.png)

*↑ The measurement ―― c の更新(内外の平均)と、c を固定した凸緩和(Chan–Esedoglu–Nikolova)の交互最小化。どの世界でも1 度も増えず、分割が変わらなくなった所で止まる(門 5)。止まった所が真値に近いかは別(表を見る)。 (figure labels are in Japanese; the numbers are the same)*

[![γ = 1 ≥ L = 0.463(外力の勾配の Lipschitz 定数)なので降下補題により全体は増えない(実測 増加 0 回)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_active_contours/03_snake_energy_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_active_contours/03_snake_energy.png)

*↑ γ = 1 ≥ L = 0.463(外力の勾配の Lipschitz 定数)なので降下補題により全体は増えない(実測 増加 0 回)。*

[![dA/dt = −∮κ ds = −2π。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_active_contours/04_curvature_area_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_active_contours/04_curvature_area.png)

*↑ dA/dt = −∮κ ds = −2π。*

[![Jaccard/Dice は物体マスク、境界 F は τ = 2 px。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_active_contours/05_scores_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_active_contours/05_scores.png)

*↑ Jaccard/Dice は物体マスク、境界 F は τ = 2 px。*

[![U 字の凹部: 同じ α・β・γ で外力だけ違う。古典(赤)は凹部の口に橋を架けて止まり、辺の途中も外に浮いたまま(エッジの勾配の力は辺の近くにしか届かない)、GVF(青)は奥まで入る。緑 = 真の縁。1 コマ = 20 反復。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_active_contours/06_u_shape_snakes.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_active_contours/06_u_shape_snakes.gif)

*↑ The animation ―― U 字の凹部: 同じ α・β・γ で外力だけ違う。古典(赤)は凹部の口に橋を架けて止まり、辺の途中も外に浮いたまま(エッジの勾配の力は辺の近くにしか届かない)、GVF(青)は奥まで入る。緑 = 真の縁。1 コマ = 20 反復。*

[![照明の勾配の上の暗い物体(反転して渡す)。全画面の矩形から 4 手法の輪郭が動く。大域の 2 平均(Chan–Vese・形態学的 CV)は明るい側の背景ごと切り、エッジで止まる GAC・DRLSE は物体に貼り付く(GAC は雑音の粒を数十](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_active_contours/07_gradient_world_contours.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_active_contours/07_gradient_world_contours.gif)

*↑ The animation ―― 照明の勾配の上の暗い物体(反転して渡す)。全画面の矩形から 4 手法の輪郭が動く。大域の 2 平均(Chan–Vese・形態学的 CV)は明るい側の背景ごと切り、エッジで止まる GAC・DRLSE は物体に貼り付く(GAC は雑音の粒を数十個残す = 表の予測の個数)。緑 = 真の縁、各手法のコマは反復数に比例して間引いて 40 コマに揃えた。*

[![凹んだ星形の平均曲率流。凹部は外へ、凸部は内へ動き、丸くなりながら面積は毎時間 2π ずつ減る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_active_contours/08_curvature_flow_star.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_active_contours/08_curvature_flow_star.gif)

*↑ The animation ―― 凹んだ星形の平均曲率流。凹部は外へ、凸部は内へ動き、丸くなりながら面積は毎時間 2π ずつ減る。*

```
py -3.11 examples/poc_active_contours.py
```

Source: [examples/poc_active_contours.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_active_contours.py)

This run produced **8 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_active_contours)

Ops used (notes): [`chan_vese_evolve`](https://furuse.work/ops/segmentation/contour/chan_vese_evolve.html) · [`curvature_flow`](https://furuse.work/ops/segmentation/contour/curvature_flow.html) · [`drle_evolve`](https://furuse.work/ops/segmentation/contour/drle_evolve.html) · [`edge_stop_g`](https://furuse.work/ops/segmentation/contour/edge_stop_g.html) · [`gvf_field`](https://furuse.work/ops/segmentation/contour/gvf_field.html) · [`level_set_reinit`](https://furuse.work/ops/segmentation/contour/level_set_reinit.html) · [`morph_chan_vese`](https://furuse.work/ops/segmentation/contour/morph_chan_vese.html) · [`morph_geodesic_ac`](https://furuse.work/ops/segmentation/contour/morph_geodesic_ac.html) · [`seg_dice_jaccard`](https://furuse.work/ops/segmentation/score/seg_dice_jaccard.html) · [`seg_score_card`](https://furuse.work/ops/segmentation/score/seg_score_card.html) · [`sk_chan_vese`](https://furuse.work/ops/2d/segmentation/sk_chan_vese.html) · [`snake_evolve`](https://furuse.work/ops/segmentation/contour/snake_evolve.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`world_blobs_touching`](https://furuse.work/ops/segmentation/world/world_blobs_touching.html) · [`world_gradient_illumination`](https://furuse.work/ops/segmentation/world/world_gradient_illumination.html) · [`world_parts_with_shadow`](https://furuse.work/ops/segmentation/world/world_parts_with_shadow.html) · [`world_thin_structures`](https://furuse.work/ops/segmentation/world/world_thin_structures.html)

## No.2026.187 —— Graph, Hierarchical and Threshold Segmentation — Max Flow = Min Cut, Ultrametrics, and Turning a Knob From Coarse to Fine

[![Graph, Hierarchical and Threshold Segmentation — Max Flow = Min Cut, Ultrametrics, and Turning a Knob From Coarse to Fine](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/01_inputs_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/01_inputs.png)

*↑ **Graph, Hierarchical and Threshold Segmentation — Max Flow = Min Cut, Ultrametrics, and Turning a Knob From Coarse to Fine** ―― Segmentation expansion, batch 3 — new module seggraph, 16 ops. Gates: graph cut matches the brute-force minimum on 40 problems of 3×4 pixels, and max flow = min cut (exactly, in integers, even at 160×160) / α-expansion stays within E ≤ 2c·E* on all 80 problems (Boykov–Veksler–Zabih 2001, Theorem 6.1), and a 3×3 trap shows it can stop at a local optimum / area opening on the component tree is idempotent and anti-extensive and matches skimage pixel for pixel / quasi-flat zones = connected components of the minimum spanning tree cut at α (six values of α), nested as α grows / the hierarchical watershed has 0 ultrametric violations over all triples of 107 basins, and the surviving basins are those with dynamics > θ / every SNIC superpixel is 4-connected and its boundary recall is within 0.05 of SLIC / isodata is a fixed point, triangle matches skimage, Kapur is the brute-force maximum. Which method wins where: on touching blobs the hierarchical watershed gives 19 regions at θ = 0 (over-segmented), exactly 10 blobs for θ = 0.5–3.5, and one region at large θ / graph cut at λ = 0.1 raises Dice on noisy blobs by +0.13 and lowers it on 1–3 px lines by −0.13 at the same λ / SRM gets down to 0.74–0.90 bit of VI on grains but on same-mean texture regions never beats a single region at any q / under an illumination gradient Kittler scores Dice 0.93–0.99 and isodata 0.29–0.41. Three sweep videos (θ, q, λ). Honestly: SRM's predicate constants, the original conventions of Kittler, Kapur and the triangle method, and SNIC's equation (1) were not checked against the papers. 13 gates, 6.4 s.*

[![−距離変換の地形の 1 本の最小全域森を、dynamics ≤ θ の辺で結ぶ。θ = 0 は雑音の凹みまで盆地にして過分割、θ = 0.5〜3 px で粒の数ちょうど、くびれの深さ(重なり 20 %)を超えると隣の粒と融合する。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/02_watershed_theta_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/02_watershed_theta.png)

*↑ The measurement ―― −距離変換の地形の 1 本の最小全域森を、dynamics ≤ θ の辺で結ぶ。θ = 0 は雑音の凹みまで盆地にして過分割、θ = 0.5〜3 px で粒の数ちょうど、くびれの深さ(重なり 20 %)を超えると隣の粒と融合する。 (figure labels are in Japanese; the numbers are the same)*

[![エネルギーは毎回厳密に最小(最大フロー = 最小カット)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/03_graph_cut_lambda_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/03_graph_cut_lambda.png)

*↑ エネルギーは毎回厳密に最小(最大フロー = 最小カット)。*

[![結晶粒は q = 256 付近で VI が 1 bit を切る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/04_srm_q_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/04_srm_q.png)

*↑ 結晶粒は q = 256 付近で VI が 1 bit を切る。*

[![Kittler は 2 クラスの分散を別々に持つので Bayes の最小誤差の閾値(2 次方程式の根)に乗る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/05_thresholds_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/05_thresholds.png)

*↑ Kittler は 2 クラスの分散を別々に持つので Bayes の最小誤差の閾値(2 次方程式の根)に乗る。*

[![照明の勾配では背景の裾が長く、2 平均の中点(isodata)は背景の中に落ちる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/06_scores_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/06_scores.png)

*↑ 照明の勾配では背景の裾が長く、2 平均の中点(isodata)は背景の中に落ちる。*

[![触れ合う粒の階層分水嶺。θ を大 → 小 → 大に振る: 1 領域から粒の数ちょうどを経て雑音の凹みで過分割へ、そして戻る。どのコマも同じ 1 本の木の切り方(入れ子)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/08_watershed_theta_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/08_watershed_theta_sweep.gif)

*↑ The animation ―― 触れ合う粒の階層分水嶺。θ を大 → 小 → 大に振る: 1 領域から粒の数ちょうどを経て雑音の凹みで過分割へ、そして戻る。どのコマも同じ 1 本の木の切り方(入れ子)。*

[![結晶粒の SRM。q = 1(全部 1 領域)から 1024(細切れ)へ。q = 256 前後で粒界に沿う。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/09_srm_q_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/09_srm_q_sweep.gif)

*↑ The animation ―― 結晶粒の SRM。q = 1(全部 1 領域)から 1024(細切れ)へ。q = 256 前後で粒界に沿う。*

[![graph cut の λ を 0 → 0.3。黄 = 正解の物体、赤 = 余計、青 = 取り逃し。左の雑音の点は消え、右の細い線も同じ λ で途切れて消える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/10_graph_cut_lambda_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/10_graph_cut_lambda_sweep.gif)

*↑ The animation ―― graph cut の λ を 0 → 0.3。黄 = 正解の物体、赤 = 余計、青 = 取り逃し。左の雑音の点は消え、右の細い線も同じ λ で途切れて消える。*

```
py -3.11 examples/poc_graph_hierarchy_segmentation.py
```

Source: [examples/poc_graph_hierarchy_segmentation.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_graph_hierarchy_segmentation.py)

This run produced **10 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation)

Ops used (notes): [`alpha_expansion`](https://furuse.work/ops/segmentation/graph/alpha_expansion.html) · [`alpha_tree`](https://furuse.work/ops/segmentation/graph/alpha_tree.html) · [`area_opening_attr`](https://furuse.work/ops/segmentation/graph/area_opening_attr.html) · [`graph_cut_binary`](https://furuse.work/ops/segmentation/graph/graph_cut_binary.html) · [`hierarchical_watershed`](https://furuse.work/ops/segmentation/graph/hierarchical_watershed.html) · [`quasi_flat_zones`](https://furuse.work/ops/segmentation/graph/quasi_flat_zones.html) · [`quickshift`](https://furuse.work/ops/segmentation/graph/quickshift.html) · [`seg_boundary_f`](https://furuse.work/ops/segmentation/score/seg_boundary_f.html) · [`seg_dice_jaccard`](https://furuse.work/ops/segmentation/score/seg_dice_jaccard.html) · [`seg_object_counts_match`](https://furuse.work/ops/segmentation/score/seg_object_counts_match.html) · [`seg_score_card`](https://furuse.work/ops/segmentation/score/seg_score_card.html) · [`seg_under_over_segmentation`](https://furuse.work/ops/segmentation/score/seg_under_over_segmentation.html) · [`snic_superpixels`](https://furuse.work/ops/segmentation/graph/snic_superpixels.html) · [`statistical_region_merging`](https://furuse.work/ops/segmentation/graph/statistical_region_merging.html) · [`superpixel_quality`](https://furuse.work/ops/segmentation/graph/superpixel_quality.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`threshold_isodata`](https://furuse.work/ops/segmentation/threshold/threshold_isodata.html) · [`threshold_kapur`](https://furuse.work/ops/segmentation/threshold/threshold_kapur.html) · [`threshold_kittler`](https://furuse.work/ops/segmentation/threshold/threshold_kittler.html) · [`threshold_triangle`](https://furuse.work/ops/segmentation/threshold/threshold_triangle.html) · [`ultrametric_contour_map`](https://furuse.work/ops/segmentation/graph/ultrametric_contour_map.html) · [`world_blobs_touching`](https://furuse.work/ops/segmentation/world/world_blobs_touching.html) · [`world_gradient_illumination`](https://furuse.work/ops/segmentation/world/world_gradient_illumination.html) · [`world_grains_voronoi`](https://furuse.work/ops/segmentation/world/world_grains_voronoi.html) … (+3)

### The Time-as-3-D Wing — A Video Is One Volume

Treat a 2-D video as one (t, y, x) volume and the 3-D ops — connected components, isosurfaces, region properties — work along time unchanged. Merging colonies become a Y in space-time, passing vehicles become bands in a (t, x) image, a wavefront's arrival time becomes an isosurface. The 20 exhibits here demonstrate exactly that.

The time axis also brings its own traps. Rounding onto the frame grid always delays; pixel area makes merging look early. Mislinks come in two opposite kinds, so a single error rate cannot say which way the diffusion coefficient is wrong. Template tracking drifts quietly before it ever loses the target, and all 152 drifted frames report 'found'.

The motion-magnification exhibit carries the most candid conclusion in the room: exact to machine precision up to a magnification of 200, and of no help for measurement. Magnification is a tool for showing people, not for measuring.

## No.2026.055 —— Modal identification from video — frequency survives to the end, damping lies first

[![Modal identification from video — frequency survives to the end, damping lies first](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/01_scene.png)

*↑ **Modal identification from video — frequency survives to the end, damping lies first** ―― A cantilever beam (closed-form Euler–Bernoulli modes) decaying freely in three modes is rendered into video with sensor noise, 100 Hz lighting flicker, camera shake and rolling shutter, then identified with phase-based displacement (phase_displacement) and PIV (piv_cross_correlate). All three natural frequencies come out within 0.06 Hz, but the damping ratio of mode 1 from the very same series is 0.0778 (half-power), 0.0188 (envelope) or 0.0181 (fit) against a true 0.02. Sweeping the amplitude from 0.02 to 2 px, the quantities break in the order f → ζ → MAC_2 → MAC_3: at 0.02 px the phase method still has f_1 within +0.030 Hz while ζ_1 is 0.23 of the truth. At 48.5 fps the flicker alias lands exactly on f_1 = 3.00 Hz; a single-pixel brightness zero-point cannot report ζ at all, while the phase method survives at 0.0191.*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/02_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/02_frames.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/03_zero_point_spectrum_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/03_zero_point_spectrum.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/05_tip_waveform_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/05_tip_waveform.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/08_cliff_frequency_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/08_cliff_frequency.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/11_fps_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/11_fps_sweep.png)

*↑ この回の図*

[![動画(640 × 502、24 fps、292 コマ): 片持ち梁の自由減衰(A_1 = 0.2 px、雑音・照明ちらつき・手ぶれ・ローリングシャッター入り、撮影 128 fps を 5.3 倍のスローで再生)。画面のままでは梁は動いて見え](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/14_beam_video.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/14_beam_video.gif)

*↑ The animation ―― 動画(640 × 502、24 fps、292 コマ): 片持ち梁の自由減衰(A_1 = 0.2 px、雑音・照明ちらつき・手ぶれ・ローリングシャッター入り、撮影 128 fps を 5.3 倍のスローで再生)。画面のままでは梁は動いて見えないので、12 測点のたわみを 50 倍に誇張して重ねた(白 = 真値、青 = 位相法の測定)。下段は先端の変位が時刻とともに伸びる(白 = 真値、青 = 位相法、朱 = PIV)。最後のコマが同定結果: f_1 は 3.013 Hz(真 3.000)と当たるが、同じ時系列から出した ζ_1 は 半値幅 0.0778 / 包絡線 0.0188 / 当てはめ 0.0181(真 0.020)と方法で 3 通りに割れる。*

```
py -3.11 examples/poc_beam_modal_video.py
```

Source: [examples/poc_beam_modal_video.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_beam_modal_video.py)

This run produced **14 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_beam_modal_video)

Ops used (notes): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`data_to_pixel`](https://furuse.work/ops/annotate/plot/data_to_pixel.html) · [`envelope`](https://furuse.work/ops/oned/signal/envelope.html) · [`phase_displacement`](https://furuse.work/ops/motionmag/measure/phase_displacement.html) · [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`temporal_bandpass`](https://furuse.work/ops/motionmag/temporal/temporal_bandpass.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html)

## No.2026.060 —— The Cold-Chain Temperature Record — Where You Taped the Logger Is the Verdict

[![The Cold-Chain Temperature Record — Where You Taped the Logger Is the Verdict](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cold_chain_excursion/01_scene_slices_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cold_chain_excursion/01_scene_slices.png)

*↑ **The Cold-Chain Temperature Record — Where You Taped the Logger Is the Verdict** ―― Twelve hours of a 12.0 m x 2.4 m reefer hold, built as a single (t, y, x) volume of 720 min x 60 x 12 cells with known closed-form physics: distance from the supply vent, infiltration from each of the four walls, five door-opening pulses, and first-order thermal lag (5 min for air, 64-91 min for product). 108 of 490 product cells (22.0 %) truly fail, yet a single logger taped in the product reports PASS for 82.4 % of the placements. Turning the causes off one at a time separates the failure modes: walls alone give 95.5 % false passes and 0.0 % false alarms, while walls off and doors on drop true failures to 2.0 % but raise false alarms to 3.5 % — and a logger in the product then passes 100 % of the time, because short pulses never enter the product. The cliffs can be predicted on paper: the time-constant cliff measured at 19-138 min matches a two-stage (hold air + logger) model within 18 % relative, and the sampling-interval and 0.5 K quantisation cliffs match their predictions exactly. Converted to "minutes allowed at 12 °C", the three metrics computed from the same record differ by 4.6x (60 / 276 / 197 min) and disagree on the verdict at 82 of 720 placements (11.4 %).*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cold_chain_excursion/02_layout_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cold_chain_excursion/02_layout_maps.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

[![扉前の空気は跳ねるが製品には届かない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cold_chain_excursion/03_traces_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cold_chain_excursion/03_traces.png)

*↑ 扉前の空気は跳ねるが製品には届かない。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cold_chain_excursion/06_sweep_tau_positions_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cold_chain_excursion/06_sweep_tau_positions.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cold_chain_excursion/10_control_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cold_chain_excursion/10_control_maps.png)

*↑ この回の図*

[![1 枚目は render_volume_projection を幅方向から掛けた xray 投影(明るいほど幅方向に厚い)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cold_chain_excursion/13_excursion_body_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cold_chain_excursion/13_excursion_body.png)

*↑ 1 枚目は render_volume_projection を幅方向から掛けた xray 投影(明るいほど幅方向に厚い)。*

```
py -3.11 examples/poc_cold_chain_excursion.py
```

Source: [examples/poc_cold_chain_excursion.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_cold_chain_excursion.py)

This run produced **16 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_cold_chain_excursion)

Ops used (notes): [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`integrate_funct_1d`](https://furuse.work/ops/oned/function/integrate_funct_1d.html) · [`quantize`](https://furuse.work/ops/oned/signal/quantize.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`sample_funct_1d`](https://furuse.work/ops/oned/function/sample_funct_1d.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_label_shape_stats`](https://furuse.work/ops/volcolor/measure/vol_label_shape_stats.html) · [`vol_mip`](https://furuse.work/ops/2d/3d/vol_mip.html) · [`vol_profile_line`](https://furuse.work/ops/3d/probe/vol_profile_line.html) · [`vol_region_props`](https://furuse.work/ops/3d/regionprops/vol_region_props.html)

## No.2026.095 —— Measuring the Growth, Not the Width — Rephotographing the Same Wall Changes What the Error Is

[![Measuring the Growth, Not the Width — Rephotographing the Same Wall Changes What the Error Is](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/01_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/01_frames.png)

*↑ **Measuring the Growth, Not the Width — Rephotographing the Same Wall Changes What the Error Is** ―― A wall at 1 px = 0.15 mm, rephotographed for twelve epochs over three years, with a crack opening at a true 0.040 mm/yr. Thresholding and counting pixels understates the width by 25.0 % yet overstates the growth rate by +153.0 %, and invents +0.0117 mm/yr of growth in a control where the width is frozen (the culprit is blur, isolated by switching one nuisance at a time). Integrating the intensity deficit gives +3.1 % on the rate and +0.0005 mm/yr on the control. The thresholded rate swings from 0.0241 to 0.1038 mm/yr on initial width alone — it depends on whether a one-pixel step happens to fall inside the observation window.*

[![2 値化は幅の偏りより**期ごとの跳ね**が問題。跳ねの正体はぼけと画素位相で、4 節と 3 節で分けて数える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/02_timeseries_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/02_timeseries.png)

*↑ The measurement ―― 2 値化は幅の偏りより**期ごとの跳ね**が問題。跳ねの正体はぼけと画素位相で、4 節と 3 節で分けて数える。 (figure labels are in Japanese; the numbers are the same)*

[![ここに出る傾きはすべて『見かけの成長』。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/03_control_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/03_control.png)

*↑ ここに出る傾きはすべて『見かけの成長』。*

[![傾きが 0 に近いほど列方向の画素位相が揃い、2 値化は画面ごと 1 画素単位で跳ぶ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/05_phase_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/05_phase.png)

*↑ 傾きが 0 に近いほど列方向の画素位相が揃い、2 値化は画面ごと 1 画素単位で跳ぶ。*

[![横線を下回った時点で 0.040 mm/年 を 2σ で言える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/07_cliff_epochs_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/07_cliff_epochs.png)

*↑ 横線を下回った時点で 0.040 mm/年 を 2σ で言える。*

[![2 値化は臨界幅より細いと 0(未検出)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/09_cliff_width_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/09_cliff_width.png)

*↑ 2 値化は臨界幅より細いと 0(未検出)。*

[![動画(576 × 456、12 fps、378 コマ): 同じ壁を 3 年 12 期撮り返す。各期で中心線に直交する断面を 24 本、左から順に切り(橙 = いま切っている断面、右下が拡大)、下段左がその断面の輝度欠損 —— その面積が幅そ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/11_series_video.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/11_series_video.gif)

*↑ The animation ―― 動画(576 × 456、12 fps、378 コマ): 同じ壁を 3 年 12 期撮り返す。各期で中心線に直交する断面を 24 本、左から順に切り(橙 = いま切っている断面、右下が拡大)、下段左がその断面の輝度欠損 —— その面積が幅そのもの。24 本の平均が積分法の幅(青、測りかけの期は橙の輪で途中平均)、朱のマスクの画素を数えたのが 2 値化(朱)。真の幅は 1 期 0.010 mm ずつ伸びる(0.067 画素)。最後の当てはめで成長率は 真値 0.0400 / 積分法 0.0412 / 2 値化 0.1012 mm/年。2 値化は期ごとに跳ね(0.0185〜0.3386 mm)、跳ねの正体はぼけ(PSF σ 0.75〜1.24 px)と据え直しの画素位相。*

```
py -3.11 examples/poc_crack_width_timeseries.py
```

Source: [examples/poc_crack_width_timeseries.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_crack_width_timeseries.py)

This run produced **11 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_crack_width_timeseries)

Ops used (notes): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`data_to_pixel`](https://furuse.work/ops/annotate/plot/data_to_pixel.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html)

## No.2026.026 —— Micro-Vibration of a Structure From Video — Does Motion Magnification Help You Measure?

[![Micro-Vibration of a Structure From Video — Does Motion Magnification Help You Measure?](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/01_slit_scan_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/01_slit_scan.png)

*↑ **Micro-Vibration of a Structure From Video — Does Motion Magnification Help You Measure?** ―― A vibration of known amplitude 0.02 px at 3.7 Hz, synthesised to test whether motion magnification helps measurement. Exact to machine precision up to α = 200. But magnification does not improve measurement precision — multiplying the phase by α multiplies the noise by α. On a cantilever, phase correlation returns 0.15 px, the area average of 0.30 and 0.00 px, a number that exists nowhere.*

[![剛体を仮定する位相相関が返す 0.150 px は 0.30 と 0.00 の面積平均で、どの列の真値とも違う。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/02_beam_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/02_beam_profile.png)

*↑ The measurement ―― 剛体を仮定する位相相関が返す 0.150 px は 0.30 と 0.00 の面積平均で、どの列の真値とも違う。 (figure labels are in Japanese; the numbers are the same)*

[![3.7 Hz を含む帯だけが 0 dB。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/03_band_selectivity_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/03_band_selectivity.png)

*↑ 3.7 Hz を含む帯だけが 0 dB。*

[![3.05 px までは機械精度、3.10 px で崩壊。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/04_amplitude_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/04_amplitude_cliff.png)

*↑ 3.05 px までは機械精度、3.10 px で崩壊。*

[![動画(480 × 480、12 fps、124 コマ): 3.7 Hz・0.1 px で揺れる表面(雑音 σ 0.01)。左が生の映像、右が 10 倍に拡大した映像で、朱の細い縦線は静止時の縞の山。生では揺れが表示 0.3 px で目に見え](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/05_magnify_video.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/05_magnify_video.gif)

*↑ The animation ―― 動画(480 × 480、12 fps、124 コマ): 3.7 Hz・0.1 px で揺れる表面(雑音 σ 0.01)。左が生の映像、右が 10 倍に拡大した映像で、朱の細い縦線は静止時の縞の山。生では揺れが表示 0.3 px で目に見えず、拡大後は 1 px 相当で見える。下段は変位の時系列: 白 = 真値、青 = 生の映像から測った値、橙 = 拡大後に測って 10 で割った値。振幅は 真 0.1000 / 生から 0.10012 / 拡大後 0.10013 px で、拡大しても測定は良くならない(見せるための道具)。*

```
py -3.11 examples/poc_motion_magnification.py
```

Source: [examples/poc_motion_magnification.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_motion_magnification.py)

This run produced **5 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_motion_magnification)

Ops used (notes): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`band_snr`](https://furuse.work/ops/motionmag/temporal/band_snr.html) · [`data_to_pixel`](https://furuse.work/ops/annotate/plot/data_to_pixel.html) · [`displacement_series`](https://furuse.work/ops/motionmag/measure/displacement_series.html) · [`motion_magnify`](https://furuse.work/ops/motionmag/magnify/motion_magnify.html) · [`phase_displacement`](https://furuse.work/ops/motionmag/measure/phase_displacement.html) · [`synthesize_translation`](https://furuse.work/ops/motionmag/synthesis/synthesize_translation.html) · [`temporal_band_power`](https://furuse.work/ops/motionmag/temporal/temporal_band_power.html) · [`temporal_bandpass`](https://furuse.work/ops/motionmag/temporal/temporal_bandpass.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html)

## No.2026.030 —— Particle Tracking as a (row, column, time) Volume — Mislinks Come in Two Directions

[![Particle Tracking as a (row, column, time) Volume — Mislinks Come in Two Directions](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/05_tracking_links.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/05_tracking_links.gif)

*↑ **Particle Tracking as a (row, column, time) Volume — Mislinks Come in Two Directions** ―― A video of 400 particles tracked, with the diffusion coefficient D read from the trajectories. Ambiguous mislinks pull D down to 0.925x; mislinks caused by missing targets push it up to 3.429x in the same video — one error rate cannot tell you the direction. What helps is not a one-to-one constraint but a single line imposing a maximum link distance (3.429 → 1.304).*

[![時間最大投影では粒子が尾を引く(= 軌跡)。kymograph は行 90-101 の帯を縦(時間)へ積んだもので、筋の傾きがそのまま列方向の速度。縦は 5 倍に拡大。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/01_spacetime_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/01_spacetime.png)

*↑ The measurement ―― 時間最大投影では粒子が尾を引く(= 軌跡)。kymograph は行 90-101 の帯を縦(時間)へ積んだもので、筋の傾きがそのまま列方向の速度。縦は 5 倍に拡大。 (figure labels are in Japanese; the numbers are the same)*

[![縦軸は常用対数(0 が真値)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/02_density_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/02_density_bias.png)

*↑ 縦軸は常用対数(0 が真値)。*

[![真値で割った比。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/03_msd_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/03_msd.png)

*↑ 真値で割った比。*

[![曖昧と欠測を分けて数えると、D の外れる向きが説明できる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/04_density_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/04_density_table.png)

*↑ 曖昧と欠測を分けて数えると、D の外れる向きが説明できる。*

```
py -3.11 examples/poc_particle_tracking.py
```

Source: [examples/poc_particle_tracking.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_particle_tracking.py)

This run produced **5 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_particle_tracking)

Ops used (notes): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_local_maxima`](https://furuse.work/ops/3d/feature/vol_local_maxima.html)

## No.2026.111 —— Did It Settle, or Did We Just Scan It Again — What Changes When You Cut at the Detection Limit

[![Did It Settle, or Did We Just Scan It Again — What Changes When You Cut at the Detection Limit](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_settlement_significance/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_settlement_significance/01_scene.png)

*↑ **Did It Settle, or Did We Just Scan It Again — What Changes When You Cut at the Detection Limit** ―― A 24 x 16 m road surface settling above a tunnel drive, measured from two epochs of point cloud. The nearest-neighbour baseline (C2C) returns a median of 47.74 mm even with zero change — that is just the point spacing — and carries no sign. M3C2 averages -2.43 mm, matching the truth, but only 275 of 551 cores (49.9 %) exceed their level of detection, and those average -4.34 mm: the single averaged number agrees with neither. LoD is a map of the surface, not of the settlement, ranging 0.51 to 3.58 mm across zones. Summing only the significant cores shrinks the volume from 0.8569 to 0.7643 m3, and that shortfall is predictable in advance from the per-core LoD (0.867 predicted versus 0.892 measured).*

[![有意の地図は真値の地図をよく復元する(TPR 88.7 % / FPR 3.6 %)。ただし縁が痩せる —— そこが 7 節の体積の話。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_settlement_significance/02_map_change_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_settlement_significance/02_map_change.png)

*↑ The measurement ―― 有意の地図は真値の地図をよく復元する(TPR 88.7 % / FPR 3.6 %)。ただし縁が痩せる —— そこが 7 節の体積の話。 (figure labels are in Japanese; the numbers are the same)*

[![上の帯(砂利の路肩)は粗さ 15 mm・密度半分なので LoD が跳ね上がる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_settlement_significance/03_map_lod_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_settlement_significance/03_map_lod.png)

*↑ 上の帯(砂利の路肩)は粗さ 15 mm・密度半分なので LoD が跳ね上がる。*

[![予測は 1.96·σ·sqrt(1/na+1/nb)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_settlement_significance/04_lod_by_zone_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_settlement_significance/04_lod_by_zone.png)

*↑ 予測は 1.96·σ·sqrt(1/na+1/nb)。*

[![LoD は雑音しか見ていないので、系統誤差はそのまま「有意な沈下」として通る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_settlement_significance/05_map_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_settlement_significance/05_map_bias.png)

*↑ LoD は雑音しか見ていないので、系統誤差はそのまま「有意な沈下」として通る。*

[![崖の位置はそのゾーンの LoD で決まる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_settlement_significance/06_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_settlement_significance/06_cliff.png)

*↑ 崖の位置はそのゾーンの LoD で決まる。*

```
py -3.11 examples/poc_settlement_significance.py
```

Source: [examples/poc_settlement_significance.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_settlement_significance.py)

This run produced **7 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_settlement_significance)



## No.2026.041 —— Template Tracking Drifts Quietly Before It Ever Loses the Target

[![Template Tracking Drifts Quietly Before It Ever Loses the Target](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/01_ncc_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/01_ncc_maps.png)

*↑ **Template Tracking Drifts Quietly Before It Ever Loses the Target** ―― A camera moved by a known similarity transform, exposing the three ways template tracking fails: losing the target, drifting quietly, and being confidently wrong. All 152 of the 152 drifted frames passed the peak threshold calibrated without occlusion and reported 'found'. The only absolute quantity measurable without ground truth is forward-backward inconsistency.*

[![同じ遮蔽率でも、そっくりな別物体が視野に居るだけで崖がはるかに手前へ来る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/02_occlusion_vs_twin_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/02_occlusion_vs_twin.png)

*↑ The measurement ―― 同じ遮蔽率でも、そっくりな別物体が視野に居るだけで崖がはるかに手前へ来る。 (figure labels are in Japanese; the numbers are the same)*

[![更新なしは平らなまま。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/03_drift_curves_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/03_drift_curves.png)

*↑ 更新なしは平らなまま。*

[![得意な崖が逆。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/04_confidence_auc_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/04_confidence_auc.png)

*↑ 得意な崖が逆。*

[![動画(30 フレーム + 最後で 2 秒止め、5 fps): 同じ 1 枚目のテンプレートを更新なし全域探索で追う(ゼロ点)。3 フレーム目から真の対象の 70 % を左から隠す。左 = 平坦な遮蔽物: ピークは平均 0.745 まで下がっ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/05_twin_vs_flat_occluder.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/05_twin_vs_flat_occluder.gif)

*↑ The animation ―― 動画(30 フレーム + 最後で 2 秒止め、5 fps): 同じ 1 枚目のテンプレートを更新なし全域探索で追う(ゼロ点)。3 フレーム目から真の対象の 70 % を左から隠す。左 = 平坦な遮蔽物: ピークは平均 0.745 まで下がってしきい値 0.843 を割る(「見失った?」と正直に言う)が、位置は平均 0.78 px で追えている(見失い 0 / 27)。右 = そっくりな別物体が 51 px 離れて一緒に流れる: 最初の遮蔽フレームで複製に乗り換え、平均誤差 46.13 px、見失い 27 / 27 —— それなのにピークは平均 0.856 でしきい値を超え、27 / 27 フレームで「見つけた」と報告する。下段の紫(突出度)は右で平均 0.111 としきい値 0.304 を割って取り違えを疑うが、追えている左でも平均 0.203 で同じく割る —— 突出度が測っているのは曖昧さで、正しさではない*

```
py -3.11 examples/poc_template_tracking.py
```

Source: [examples/poc_template_tracking.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_template_tracking.py)

This run produced **5 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_template_tracking)

Ops used (notes): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`ncc_locate`](https://furuse.work/ops/2d/matching/ncc_locate.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`shape_locate`](https://furuse.work/ops/2d/matching/shape_locate.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html)

## No.2026.044 —— A Growth Time-Lapse as Space-Time Connected Components

[![A Growth Time-Lapse as Space-Time Connected Components](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/01_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/01_frames.png)

*↑ **A Growth Time-Lapse as Space-Time Connected Components** ―― A video of colonies spreading and merging, read as a (t, y, x) volume with 3-D connected components. Pixel area makes merging look early (-1.16 frames for pair 0-1) while rounding onto the frame grid makes it look late (+0.94); the two oppose, so the sum looks small. The default 26-connectivity of `vol_label` merged a near miss with a gap of 0.92.*

[![縦が時間(下向き、4 倍に拡大)、横が列。2 本の管が合わさる高さがそのまま合体時刻。色は 3-D ラベル。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/02_ystructure_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/02_ystructure.png)

*↑ The measurement ―― 縦が時間(下向き、4 倍に拡大)、横が列。2 本の管が合わさる高さがそのまま合体時刻。色は 3-D ラベル。 (figure labels are in Japanese; the numbers are the same)*

[![横軸はどちらも『何倍粗くしたか』。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/03_sampling_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/03_sampling.png)

*↑ 横軸はどちらも『何倍粗くしたか』。*

[![空間側は格子の位相でこれだけ動く(偏りより大きい)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/04_sampling_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/04_sampling_table.png)

*↑ 空間側は格子の位相でこれだけ動く(偏りより大きい)。*

[![動画(48 フレーム): 左は二値のフレームを 3-D の家族ラベルで塗ったもの(白の細線 = 真の連続円。色は体積全体で決まる家族なので、合体する 2 個は合体の前から同じ色)。右は合体する 2 組の中心を通る行の時空間断面が時刻とともに](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/05_growth_merge.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/05_growth_merge.gif)

*↑ The animation ―― 動画(48 フレーム): 左は二値のフレームを 3-D の家族ラベルで塗ったもの(白の細線 = 真の連続円。色は体積全体で決まる家族なので、合体する 2 個は合体の前から同じ色)。右は合体する 2 組の中心を通る行の時空間断面が時刻とともに現れ、Y 字の分かれ目が合体時刻になる(白の点線 = 閉形式の真値 7.99 / 30.09、橙 = 観測 7 / 31)。下はフレームを独立に数えた塊の数で、減ったのは t = 7, 31, 47。最後の t = 47 の減少はニアミス 4-5(最終フレームでも隙間 0.92)を 8 近傍が繋いだ偽の合体で、真の個数は 5 のまま。*

```
py -3.11 examples/poc_timelapse_growth.py
```

Source: [examples/poc_timelapse_growth.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_timelapse_growth.py)

This run produced **5 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_timelapse_growth)

Ops used (notes): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_region_props`](https://furuse.work/ops/3d/regionprops/vol_region_props.html)

## No.2026.045 —— Counting in (x, y, t) — Vehicles Passed, Occlusion, and One Constant: L/V

[![Counting in (x, y, t) — Vehicles Passed, Occlusion, and One Constant: L/V](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/01_per_frame_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/01_per_frame.png)

*↑ **Counting in (x, y, t) — Vehicles Passed, Occlusion, and One Constant: L/V** ―― A synthetic traffic video counted per frame, by a virtual loop, and by connected components in a (t, x) slit image. The per-frame maximum reports 7 for 10 vehicles passed — it measures a different quantity. All three failure conditions are written with one constant, vehicle length over speed = L/V (9.0 frames); at a frame interval of 16 the bands fragment and 10 vehicles become 49.*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/02_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/02_scene.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

[![トラックは画像の 50 行から 99 行を占めるので、遠い車線の計数行 63 を横切る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/03_tall_vehicles_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/03_tall_vehicles.png)

*↑ トラックは画像の 50 行から 99 行を占めるので、遠い車線の計数行 63 を横切る。*

[![全部の帯を数えると千切れて過大に(実測は最大 67 だが、他の系列が潰れるので 20 で頭打ちにして描いている)、計数列と交わる帯だけなら見逃しだけ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/04_framerate_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/04_framerate.png)

*↑ 全部の帯を数えると千切れて過大に(実測は最大 67 だが、他の系列が潰れるので 20 で頭打ちにして描いている)、計数列と交わる帯だけなら見逃しだけ。*

[![動画(768 × 422、10 fps、210 コマ = 撮った速さ): 2 車線の道路を 18 秒。上段はカメラの画に前景マスク(橙)と計数列(黄の縦線)を重ねたもの、下段は 2 車線の計数行を時間方向に積んだスリット画像 (t, x) ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/05_counting_video.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/05_counting_video.gif)

*↑ The animation ―― 動画(768 × 422、10 fps、210 コマ = 撮った速さ): 2 車線の道路を 18 秒。上段はカメラの画に前景マスク(橙)と計数列(黄の縦線)を重ねたもの、下段は 2 車線の計数行を時間方向に積んだスリット画像 (t, x) が上から伸びていく —— 車 1 台が斜めの帯 1 本になり、傾きが速度。見出しの数字は時刻までの累積で、最後は 真値 10 / 仮想ループ 10 / スリット法 10 台と同点(途中で真値が遅れて見えるのは、真値を車体の中心で、ループとスリットを車体の先端で数えるため)。フレームごとに連結成分を数えるゼロ点は最大 7 で、「いま写っている数」を数えているだけ。*

```
py -3.11 examples/poc_traffic_counting.py
```

Source: [examples/poc_traffic_counting.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_traffic_counting.py)

This run produced **5 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_traffic_counting)

Ops used (notes): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`data_to_pixel`](https://furuse.work/ops/annotate/plot/data_to_pixel.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html)

## No.2026.089 —— Where the Warehouse Dwell Came From — Count Waiting Without Its Kind and Everything Is Just Congestion

[![Where the Warehouse Dwell Came From — Count Waiting Without Its Kind and Everything Is Just Congestion](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/09_scene_layout_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/09_scene_layout.png)

*↑ **Where the Warehouse Dwell Came From — Count Waiting Without Its Kind and Everything Is Just Congestion** ―― A synthetic warehouse floor plan with 26 tracked workers and AGVs, in which replenishment waits, queueing, aisle interference, system waits and stockouts were planted with known times and durations, then read as one (t, y, x) volume. Of the naive 321.5 s of "total dwell", only 198.0 s (61.6 %) is real waiting; the rest is productive work and creep. Removing all queueing or all aisle interference moves that single number by -39.0 s versus -38.0 s, so it cannot say which to fix, while the per-kind counts drop to zero only for the kind that was removed. A stockout moves dwell by -17.0 s but adds 94.6 m of walking, and the three degradation axes each kill a different kind: sampling interval kills the short waits, occlusion kills the waits pressed against racks, and ID merging kills the two kinds defined by a relation between two people.*

[![ヒートマップは場所を当てるが、「1 人が長く待った」と「何人も短く止まった」を分けない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/01_heat_ambiguity_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/01_heat_ambiguity.png)

*↑ The measurement ―― ヒートマップは場所を当てるが、「1 人が長く待った」と「何人も短く止まった」を分けない。 (figure labels are in Japanese; the numbers are the same)*

[![ゼロ点はこの表を 1 つの数字に畳む。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/02_types_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/02_types.png)

*↑ ゼロ点はこの表を 1 つの数字に畳む。*

[![短い待ち(通路の干渉・欠品)から先に消える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/04_sweep_interval_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/04_sweep_interval.png)

*↑ 短い待ち(通路の干渉・欠品)から先に消える。*

[![天井カメラ 2 台。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/07_sweep_occlusion_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/07_sweep_occlusion.png)

*↑ 天井カメラ 2 台。*

[![上段は通路が明るい(人が通っただけ)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/10_xyt_projection_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/10_xyt_projection.png)

*↑ 上段は通路が明るい(人が通っただけ)。*

```
py -3.11 examples/poc_warehouse_flow.py
```

Source: [examples/poc_warehouse_flow.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_warehouse_flow.py)

This run produced **12 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_warehouse_flow)

Ops used (notes): [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`face_areas`](https://furuse.work/ops/3d/mesh_process/face_areas.html) · [`mesh_volume`](https://furuse.work/ops/3d/mesh_process/mesh_volume.html) · [`occupancy_grid`](https://furuse.work/ops/3d/occupancy/occupancy_grid.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`vol_dilate`](https://furuse.work/ops/2d/3d/vol_dilate.html) · [`vol_erode`](https://furuse.work/ops/2d/3d/vol_erode.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_opening_ball`](https://furuse.work/ops/2d/3d/vol_opening_ball.html) · [`vol_region_props`](https://furuse.work/ops/3d/regionprops/vol_region_props.html)

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

## No.2026.127 —— A Clip as a Space-Time Cube — What Passed Where, and When, in One Solid

[![A Clip as a Space-Time Cube — What Passed Where, and When, in One Solid](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/02_cube_orbit.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/02_cube_orbit.gif)

*↑ **A Clip as a Space-Time Cube — What Passed Where, and When, in One Solid** ―― Video Summagator (Nguyen, Niu and Liu, ACM CHI 2012) turns a clip into an (x, y, t) cube, renders the static background faintly and moving objects densely, and lets you cut and rotate the cube to jump to a scene. The new family videocube re-implements it in 6 ops (numpy + scipy only, no new types): frame-difference magnitude as opacity (video_spacetime_cube), front-to-back alpha compositing from any viewpoint with trails coloured by time (blue = start, red = end; vol_render_transfer), cuts (video_cube_cut: x-t slit scans), orbits (video_cube_orbit), keyframes (video_summary_keyframes) and animated GIF export (video_write_gif, the reusable exit). On a synthetic surveillance clip with three objects of known row, onset and speed, the onset read from the first row of each slit-scan streak and the speed read from its slope match the truth exactly (±0 frames; +2.00 / −1.50 / +1.00 px/frame), and the keyframes catch all three onsets (a random choice of 4 frames catches 0.21 on average). The same operators applied to a z-stack of fly-brain EM sections (CREMI sample A, 32 sections, raw data never committed) turn membranes into depth-coloured tubes with neurites running through the stack. In Studio, Tools ▸ Video cube runs it interactively (drag to orbit, slide the cut plane, click the slit scan to jump to that frame, open .npy / GIF / video / .hdf stacks, Save GIF).*

[![the clip as a space-time cube (time = depth to the right): moving objects leave trails coloured by time (blue = start, r](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/01_cube_time_coloured_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/01_cube_time_coloured.png)

*↑ The measurement ―― the clip as a space-time cube (time = depth to the right): moving objects leave trails coloured by time (blue = start, red = end); the static background is a faint grey (figure labels are in Japanese; the numbers are the same)*

[![x-t slit scans of the three rows: a streak's first row is the onset, its slope is the speed (yellow ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/03_slit_scans_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/03_slit_scans.png)

*↑ x-t slit scans of the three rows: a streak's first row is the onset, its slope is the speed (yellow line = injected onset)*

[![video_summary_keyframes picks the frames right after each object appears; the head-on cube is the wh](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/04_keyframes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/04_keyframes.png)

*↑ video_summary_keyframes picks the frames right after each object appears; the head-on cube is the whole clip in one image*

[![a real clip from this repo (a turntable GIF, 40 frames of 160x160): a rotating object becomes a heli](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/05_turntable_cube_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/05_turntable_cube.png)

*↑ a real clip from this repo (a turntable GIF, 40 frames of 160x160): a rotating object becomes a helix in the space-time cube*

[![the same cube operators on a z-stack of EM sections (CREMI sample A, 32 sections of 256^2 (adult Dro](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/06_em_stack_cube_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/06_em_stack_cube.png)

*↑ the same cube operators on a z-stack of EM sections (CREMI sample A, 32 sections of 256^2 (adult Drosophila FAFB)): membranes become tubes running thr…*

[![the EM stack rotating: neurites are the tubes, coloured by depth; the same operator that rotated the surveillance clip](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/07_em_stack_orbit.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/07_em_stack_orbit.gif)

*↑ The animation ―― the EM stack rotating: neurites are the tubes, coloured by depth; the same operator that rotated the surveillance clip*

```
py -3.11 examples/poc_video_cube.py
```

Source: [examples/poc_video_cube.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_video_cube.py)

This run produced **7 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_video_cube)

Ops used (notes): [`intensity`](https://furuse.work/ops/2d/features/intensity.html) · [`video_cube_cut`](https://furuse.work/ops/videocube/cube/video_cube_cut.html) · [`video_cube_orbit`](https://furuse.work/ops/videocube/render/video_cube_orbit.html) · [`video_spacetime_cube`](https://furuse.work/ops/videocube/cube/video_spacetime_cube.html) · [`video_summary_keyframes`](https://furuse.work/ops/videocube/summary/video_summary_keyframes.html) · [`video_write_gif`](https://furuse.work/ops/videocube/export/video_write_gif.html) · [`vol_render_transfer`](https://furuse.work/ops/videocube/render/vol_render_transfer.html)

## No.2026.128 —— Living Tissue in 3D+t Without a Generator — Magnify, Flow, Interpolate, Height, All Against Truth

[![Living Tissue in 3D+t Without a Generator — Magnify, Flow, Interpolate, Height, All Against Truth](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/01_beating_orbit.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/01_beating_orbit.gif)

*↑ **Living Tissue in 3D+t Without a Generator — Magnify, Flow, Interpolate, Height, All Against Truth** ―― A video generator invents plausible motion. The new family live4d (14 ops, numpy + scipy only, one new word: volseq = a volume series (T, Z, Y, X)) invents nothing; instead it offers four ways to make real motion visible, each pinned to numbers on synthetic series with known truth. (1) Magnify: a shell whose radius beats by 0.1 voxel (invisible) is magnified x8 by volseq_magnify_motion (a 3-D version of Wu et al.'s linear Eulerian magnification); the radius amplitude read back is 7.89 x and the period is unchanged. (2) Flow: the displacement field of two blobs separating at a known ±0.75 voxel/frame (vol_flow_3d, 3-D Lucas–Kanade) reads +0.776 / −0.776 where there is gradient, and the pathlines (volseq_pathline_render) become one solid coloured by time. (3) Interpolate: a series made at twice the rate, halved and refilled by volseq_interpolate_flow, matches the removed frames with RMSE 0.0016 when the motion per step is twice the blob size (a linear blend: 0.0207) — while below about 0.8 sigma per step the blend is as good and the warp's resampling costs a little (plotted honestly). (4) Height: from a focus-sweep series (a moving bump) focus_sweep_height_video recovers the height field with RMSE 0.31 planes. Live cells in 3D+t from the Cell Tracking Challenge (Fluo-N3DH-CHO, raw data never committed) run through the same path.*

[![radius of the shell read from each volume: the measured beat (0.10 voxel) is below one voxel; after magnification it fol](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/02_radius_trace_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/02_radius_trace.png)

*↑ The measurement ―― radius of the shell read from each volume: the measured beat (0.10 voxel) is below one voxel; after magnification it follows alpha x truth (figure labels are in Japanese; the numbers are the same)*

[![pathlines of particles carried by the 3-D flow of the dividing blob, coloured by time (blue = start,](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/03_pathlines_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/03_pathlines.png)

*↑ pathlines of particles carried by the 3-D flow of the dividing blob, coloured by time (blue = start, red = end); the faint grey is the first volume*

[![a frame removed from a 2x-rate series (motion 5 voxel = 2 sigma per step) re-created two ways (max p](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/05_interpolation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/05_interpolation.png)

*↑ a frame removed from a 2x-rate series (motion 5 voxel = 2 sigma per step) re-created two ways (max projections): the linear blend shows two ghosts per…*

[![error of the re-created frames against the removed ones, as the motion per step grows: below about o](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/06_interpolation_regimes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/06_interpolation_regimes.png)

*↑ error of the re-created frames against the removed ones, as the motion per step grows: below about one blob width a linear blend is as good (the warp'…*

[![Fluo-N3DH-CHO/01 (12 volumes of (5, 111, 128), y/x 1/4): pathlines of the 3-D flow between consecuti](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/09_ctc_pathlines_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/09_ctc_pathlines.png)

*↑ Fluo-N3DH-CHO/01 (12 volumes of (5, 111, 128), y/x 1/4): pathlines of the 3-D flow between consecutive volumes, coloured by time*

[![the same pathlines orbited: two straight bundles leaving the split point at +/-0.75 voxel/frame](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/04_pathlines_orbit.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/04_pathlines_orbit.gif)

*↑ The animation ―― the same pathlines orbited: two straight bundles leaving the split point at +/-0.75 voxel/frame*

[![height field recovered from a focus sweep series (a moving bump, 11 planes), shaded and coloured by height (blue = low, ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/07_focus_surface.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/07_focus_surface.gif)

*↑ The animation ―― height field recovered from a focus sweep series (a moving bump, 11 planes), shaded and coloured by height (blue = low, red = high); RMSE 0.31 planes*

[![Fluo-N3DH-CHO/01 (12 volumes of (5, 111, 128), y/x 1/4): the live volumes orbited while time advances (intensity as opac](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/08_ctc_orbit.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/08_ctc_orbit.gif)

*↑ The animation ―― Fluo-N3DH-CHO/01 (12 volumes of (5, 111, 128), y/x 1/4): the live volumes orbited while time advances (intensity as opacity)*

```
py -3.11 examples/poc_live4d.py
```

Source: [examples/poc_live4d.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_live4d.py)

This run produced **10 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_live4d)

Ops used (notes): [`blend`](https://furuse.work/ops/shape2d/morph/blend.html) · [`focus_sweep_height_video`](https://furuse.work/ops/live4d/render/focus_sweep_height_video.html) · [`focus_sweep_surface_video`](https://furuse.work/ops/live4d/render/focus_sweep_surface_video.html) · [`vol_flow_3d`](https://furuse.work/ops/live4d/flow/vol_flow_3d.html) · [`volseq_interpolate_flow`](https://furuse.work/ops/live4d/time/volseq_interpolate_flow.html) · [`volseq_magnify_motion`](https://furuse.work/ops/live4d/time/volseq_magnify_motion.html) · [`volseq_pathline_orbit`](https://furuse.work/ops/live4d/flow/volseq_pathline_orbit.html) · [`volseq_pathline_render`](https://furuse.work/ops/live4d/flow/volseq_pathline_render.html) · [`volseq_render_orbit`](https://furuse.work/ops/live4d/render/volseq_render_orbit.html) · [`volseq_synth_beating`](https://furuse.work/ops/live4d/synth/volseq_synth_beating.html) · [`volseq_synth_dividing`](https://furuse.work/ops/live4d/synth/volseq_synth_dividing.html)

## No.2026.206 —— Transcribing a Diabolo Model from the Paper and Checking It, then Reading Axis, Spin and Tension from Synthetic Video — Eq. (1b) as Printed Is Dimensionally Wrong and Gives NaN at the Real Dimensions; Closed Forms, an Exact String and MuJoCo as the Truth

[![Transcribing a Diabolo Model from the Paper and Checking It, then Reading Axis, Spin and Tension from Synthetic Video — Eq. (1b) as Printed Is Dimensionally Wrong and Gives NaN at the Real Dimensions; Closed Forms, an Exact String and MuJoCo as the Truth](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_diabolo_model_and_vision/01_diabolo_throw_axis_from_image.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_diabolo_model_and_vision/01_diabolo_throw_axis_from_image.gif)

*↑ **Transcribing a Diabolo Model from the Paper and Checking It, then Reading Axis, Spin and Tension from Synthetic Video — Eq. (1b) as Printed Is Dimensionally Wrong and Gives NaN at the Real Dimensions; Closed Forms, an Exact String and MuJoCo as the Truth** ―― The physics-simulation × Fullseye series. The primary source is the LaTeX source of an analytic diabolo model for robot learning (von Drigalski et al., ICRA 2021, arXiv:2011.09068; the state-transition conditions exist only in a figure, which was read as an image). The public implementation (BSD-3) was read for comparison only; no code was copied. The model is a point mass + an auxiliary spheroid formed by the string + gravity; one step = forward Euler → project back if outside the spheroid → spin by eq. (2) ω_t = ω_{t−1} + μ Δ_string. Learning-free, all rules. New module diabolo, 16 ops plus 1 mujoco facade. ★Where the paper as printed does not hold (found by transcribing it and putting gates on it): (1) eq. (1b) b = √(a² − |x_L − x_R|/2) subtracts a length from a squared length; at the paper's real dimensions (string 1.45 m, stick gap 1.10 m) the radicand is negative = NaN. Fixed with the ellipse identity a² = b² + c² (at 0.3 m the printed form gives 0.613 m, the correct value is 0.709 m). (2) LOOSE → ON with s < c_F as drawn overlaps the ON → LOOSE band and flips every step → read as s ≤ c_L. (3) Eq. (2) telescopes and is step-independent (16.57 → 16.59 rad/s for 2 → 1 ms steps), whereas the public implementation's spin rule scales inversely with the step (ratio 2.02); with μ = 1/r, eq. (2) equals rolling without slipping. (4) The public implementation's normal is not the gradient and is off by up to 12.2° — here the nearest point and the true normal are used, as in the text. Ground truth comes from outside on three fronts. (1) Closed forms: the focal identity d_L + d_R = l (7.5e-16), the forward-Euler drift g t dt/2 in flight, pendulum periods 2π√(b/g) = 1.379 s sideways and 2π√(a²/(bg)) = 2.116 s lengthwise, the static tension m g a/(2b), and the catch time of parabola × spheroid × the plane through the sticks (closed form 0.7214 s, paper model 0.7230 s). (2) An exact string model (our addition): the unilateral constraint d_L + d_R ≤ l of an inextensible string by RATTLE, with an energy spread of 5.3e-6, a power balance of 1.1e-4 and the tension multiplier matching the closed form to 3.6e-11. (3) A second implementation = MuJoCo spatial tendons (--full): within 0.62 / 1.15 / 3.10 mm of the exact string for linear acceleration / swing / throw (excluding 0.3 s after the catch — MuJoCo's soft constraint bounces 40 mm), static tension 3.5e-7. Vision is learning-free (ray-traced synthetic video): the axis and centre come from fitting the exact perspective polygon moments of two circles — the near cup rim and the bottom plate — to the mask moments (42 poses, 0–38° from the line of sight × 6 azimuths: max 0.295°, median 0.059°, centre 0.7 mm); at 45° the bottom plate is hidden by the wall and a 2.80 px residual raises the alarm. Spin comes from the phase of markers on the inner surface plus the width of the motion-blur arc to pick the branch (120 fps, 2 ms exposure: 10–110 rev/s within 0.81 %; phase alone folds 70 / 90 / 110 rev/s, beyond the 60 rev/s Nyquist, to −50 / −30 / −10 = the wagon-wheel illusion). Tension comes from the V of stick-tip markers and the axle (0.46 % from the closed form). Tracking a throw (3 m away, 41 frames) gives a centre RMS of 8.9 mm and a median axis error of 1.71°, and the state machine run on the tracked positions agrees 100 % with the true states. Figures: a GIF of the throw with the axis read from the image, the true axis, the state and a 3× inset; the sag (fixed vs printed equation, the NaN boundary); tension (closed form, exact string, image, MuJoCo); heights and differences of the three models; the step dependence of the spin rules; with --full: a GIF of the spin illusion (phase only vs branch picked by the blur arc), a table of axis errors (tilt × azimuth) and a table of where it breaks. 18 gates (default, 3.1 s) plus 7 with --full (42 s). Honestly: the outside truths are the paper's equations, closed forms and MuJoCo only; nothing is matched against real footage or public data (errors in the equations were found, but whether the model fits a real diabolo is not checked). The μ and damping of eq. (2) and the attitude (tilt and precession) are in neither the paper nor the model; the axis read from the image is the pose given at render time, not a result of the dynamics. Rendering is idealised (flat colours, Lambert shading, plain background), and the axis estimate needs the inside of the near cup to be visible (up to 38°). The string is a point; wrapping on the axle, string mass and stretch are not modelled. Traps we hit: the throw-tracking centre error was printed in metres labelled as mm (100× better than at close range was the giveaway), threshold-based marker detection dropped to zero above 30 rev/s under motion blur, and the exact model and MuJoCo were first built as a bead threaded on the string, which bounced at the apex.*

[![式 (1b) の原文 √(a² − d/2) は長さと長さの 2 乗の差で次元が合わず、d > 2a² = 1.051 m で NaN(論文の実機の間隔 1.10 m は NaN の側)。直した √(a² − c²)(楕円の恒等式)が実線。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_diabolo_model_and_vision/02_diabolo_sag_corrected_vs_printed_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_diabolo_model_and_vision/02_diabolo_sag_corrected_vs_printed.png)

*↑ The measurement ―― 式 (1b) の原文 √(a² − d/2) は長さと長さの 2 乗の差で次元が合わず、d > 2a² = 1.051 m で NaN(論文の実機の間隔 1.10 m は NaN の側)。直した √(a² − c²)(楕円の恒等式)が実線。 (figure labels are in Japanese; the numbers are the same)*

[![閉形式 T = m g a/(2b)(破線)に、厳密な糸の模型の乗数と、合成映像の棒の先と軸の V 字から読んだ張力(最大 0.46 % 差)を重ねる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_diabolo_model_and_vision/03_diabolo_tension_closed_form_vs_image_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_diabolo_model_and_vision/03_diabolo_tension_closed_form_vs_image.png)

*↑ 閉形式 T = m g a/(2b)(破線)に、厳密な糸の模型の乗数と、合成映像の棒の先と軸の V 字から読んだ張力(最大 0.46 % 差)を重ねる。*

[![同じ棒の動き(0.30〜0.50 s で開いて持ち上げ、張りつめたまま受ける)での高さ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_diabolo_model_and_vision/04_diabolo_throw_height_three_models_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_diabolo_model_and_vision/04_diabolo_throw_height_three_models.png)

*↑ 同じ棒の動き(0.30〜0.50 s で開いて持ち上げ、張りつめたまま受ける)での高さ。*

[![式 (2) は望遠鏡和なので刻み 1 ms と 0.5 ms の線が重なる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_diabolo_model_and_vision/06_diabolo_spin_law_step_dependence_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_diabolo_model_and_vision/06_diabolo_spin_law_step_dependence.png)

*↑ 式 (2) は望遠鏡和なので刻み 1 ms と 0.5 ms の線が重なる。*

[![視線からの傾き × 像の上の方位で、画像だけから読んだ軸と描いた時の軸の角(縁の半径 ≈ 48 px)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_diabolo_model_and_vision/08_diabolo_axis_error_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_diabolo_model_and_vision/08_diabolo_axis_error_table.png)

*↑ 視線からの傾き × 像の上の方位で、画像だけから読んだ軸と描いた時の軸の角(縁の半径 ≈ 48 px)。*

[![回転を上げると 120 fps の像ではマーカーが止まり、逆に回って見える(車輪の錯視)。位相だけの読みはナイキスト 60 rev/s で折り返し、回転ぶれの弧の幅で枝を選んだ読みは真値に付いていく(320 × 240、等倍)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_diabolo_model_and_vision/07_diabolo_spin_aliasing_and_smear.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_diabolo_model_and_vision/07_diabolo_spin_aliasing_and_smear.gif)

*↑ The animation ―― 回転を上げると 120 fps の像ではマーカーが止まり、逆に回って見える(車輪の錯視)。位相だけの読みはナイキスト 60 rev/s で折り返し、回転ぶれの弧の幅で枝を選んだ読みは真値に付いていく(320 × 240、等倍)。*

```
py -3.11 examples/poc_diabolo_model_and_vision.py
```

Source: [examples/poc_diabolo_model_and_vision.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_diabolo_model_and_vision.py)

This run produced **9 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_diabolo_model_and_vision)

Ops used (notes): [`arrow`](https://furuse.work/ops/annotate/pointer/arrow.html) · [`diabolo_axis_from_image`](https://furuse.work/ops/drive/diabolo/diabolo_axis_from_image.html) · [`diabolo_camera`](https://furuse.work/ops/drive/diabolo/diabolo_camera.html) · [`diabolo_dynamics_step`](https://furuse.work/ops/drive/diabolo/diabolo_dynamics_step.html) · [`diabolo_marker_phase`](https://furuse.work/ops/drive/diabolo/diabolo_marker_phase.html) · [`diabolo_params`](https://furuse.work/ops/drive/diabolo/diabolo_params.html) · [`diabolo_render`](https://furuse.work/ops/drive/diabolo/diabolo_render.html) · [`diabolo_scene_mjcf`](https://furuse.work/ops/drive/diabolo/diabolo_scene_mjcf.html) · [`diabolo_simulate`](https://furuse.work/ops/drive/diabolo/diabolo_simulate.html) · [`diabolo_spheroid`](https://furuse.work/ops/drive/diabolo/diabolo_spheroid.html) · [`diabolo_spin_from_markers`](https://furuse.work/ops/drive/diabolo/diabolo_spin_from_markers.html) · [`diabolo_state_sequence`](https://furuse.work/ops/drive/diabolo/diabolo_state_sequence.html) · [`diabolo_throw_catch_truth`](https://furuse.work/ops/drive/diabolo/diabolo_throw_catch_truth.html) · [`diabolo_track`](https://furuse.work/ops/drive/diabolo/diabolo_track.html) · [`measure_text`](https://furuse.work/ops/annotate/text/measure_text.html) · [`spheroid_closest`](https://furuse.work/ops/drive/diabolo/spheroid_closest.html) · [`string_tension_from_sag`](https://furuse.work/ops/drive/diabolo/string_tension_from_sag.html) · [`string_tension_static`](https://furuse.work/ops/drive/diabolo/string_tension_static.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`zoom_inset`](https://furuse.work/ops/annotate/compose/zoom_inset.html)

## No.2026.170 —— Measuring a Table-Tennis Ball the Way the Pioneers Did — Multi-Camera Tracking, Triangulation, Trajectory Prediction, Bounce and Spin, Scored by Theorems on a Table with Ground Truth

[![Measuring a Table-Tennis Ball the Way the Pioneers Did — Multi-Camera Tracking, Triangulation, Trajectory Prediction, Bounce and Spin, Scored by Theorems on a Table with Ground Truth](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/01_rig_view_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/01_rig_view.png)

*↑ **Measuring a Table-Tennis Ball the Way the Pioneers Did — Multi-Camera Tracking, Triangulation, Trajectory Prediction, Bounce and Spin, Scored by Theorems on a Table with Ground Truth** ―― Robot table tennis has had the same visual stance since 1988: find the ball in several cameras, triangulate it into a 3-D point, look ahead with an equation of motion that includes drag and Magnus lift, predict across the bounce and, if you can, measure spin from the markings. This exhibit builds that whole chain from numpy ops and scores it against a truth the world itself holds (ball centre, pose, contact time and angular velocity are formulas fixed at generation). First the theorems of mechanics: with drag and Magnus set to zero the RK4 flight matches the closed-form parabola to 1e-12, and the least-squares parabola returns g = 9.81 to 4.0e-15. Over 500 random impacts (e ∈ [0.3, 1], μ ∈ [0, 0.6]) the angular momentum about the contact point is conserved to a relative 4.9e-16 at worst, 136 impacts reach rolling and 364 keep sliding. Dropped from 30.5 cm with e = 0.90 the apexes are 24.7, 20.0, 16.2 and 13.1 cm, within 3.0e-07 of the closed form e^{2k}h₀; the first bounce of 24.7 cm sits inside the ITTF 24–26 cm rule, both the apex list and the contact intervals give back e = 0.900000, and the total time to rest, 4.736 s, sits beside the closed-form 4.738 s. Then a 40 mm ball with 14 markings is placed on an ITTF table and a topspin shot (ω = 240 rad/s) is filmed at 100 fps for 0.6 s by two cameras plus one close-up (rendering 61 frames × 2 cameras took 22.0 s). The true contact is at t = 0.3094 s, point (0.507, 0.052), v [5.15, −0.28, −2.65] → [5.01, −0.17, 2.39], ω [0, 240, 0] → [8.5, 250.6, 0] (grip). Chromaticity detection finds the ball in 122 / 122 frames with a centre error of 0.152 px at the median, 0.299 px at the 90th percentile and 2.094 px at worst (image radius ≈ 4.3 px). DLT triangulation is 3.8e-15 m from the truth's own projections and, from the detections, 1.61 mm at the median, 4.25 mm at the 90th percentile and 23.56 mm at worst (median reprojection rms 0.094 px). The constant-acceleration Kalman filter is exact for a parabola, so its innovation on the parabolic truth is at most 8.2e-09 m (2.3e-03 m on the drag-plus-Magnus truth, which lies outside the model), and its velocity from the detections is off by 0.074 m/s at the median (|v| ≈ 5.9 m/s). The local minimum of z lands at t = 0.31, 0.6 ms from the truth. Fitting the initial state by a 6-parameter Gauss–Newton to the 15 frames (0.15 s) before the bounce (the true trajectory comes back to 3.2e-13) and predicting across the bounce puts the landing point 0.4 cm off (0.5 ms in time) when the true spin is known, 20.2 cm off when spin is ignored, and 6.6 cm off with a parabola even given the true spin — the difference is the Magnus term. On the close-up camera at the bounce (1000 fps, strobe) 19 / 19 frame pairs pair at least two markings, and the Kabsch rotation gives a median angular velocity of [1.7, 256.6, −2.1] rad/s against the truth [8.5, 250.6, 0] (|ω| 2394 rpm), a relative error of 3.7 %. The coefficient of restitution from equation-of-motion fits to 12 frames on each side gives v_z −2.637 → 2.403, e = 0.9114 (truth 0.90). Honestly: a parabolic fit gives 0.9398, 4.4 % off, because it absorbs drag and Magnus into g; the ball detection runs on synthetic footage with a known colour and no real lighting, blur or background; and the aerodynamic coefficients are textbook values with the truth built from the same formula (this is not a test of aerodynamics). 10 gates, 42.0 s. Finally two freely moving rackets (15 × 16 cm blades, ≤ 6 m/s) rally against each other: a feeder that returns near its previous target keeps the rally to the 12-hit cap, while an attacker aiming fast at the far corners ends it after 9 hits (a rewind mechanism previews each shot with the true physics and retries a miss; the attacker still misses after 99 rewinds). Gaussian noise on the perceived position leaves the rally length unchanged up to 5 cm (the blade's margin) and cuts it to 2 hits at 10 cm — the rally length scores perception, prediction and control as one number.*

[![カメラ 1 の像での球の軌跡: 真値の投影(線)と検出(点)。中心の誤差の中央値 0.15 px。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/02_tracks_2d_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/02_tracks_2d.png)

*↑ The measurement ―― カメラ 1 の像での球の軌跡: 真値の投影(線)と検出(点)。中心の誤差の中央値 0.15 px。 (figure labels are in Japanese; the numbers are the same)*

[![x–z 面の軌跡。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/03_trajectory_xz_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/03_trajectory_xz.png)

*↑ x–z 面の軌跡。*

[![30.5 cm から落とした球(e = 0.90)の頂点: 閉形式 e^{2k}h₀ と 1e-6 で一致し、最初の跳ね 24.7 cm は ITTF の規格 24〜26 cm の中。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/04_drop_apexes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/04_drop_apexes.png)

*↑ 30.5 cm から落とした球(e = 0.90)の頂点: 閉形式 e^{2k}h₀ と 1e-6 で一致し、最初の跳ね 24.7 cm は ITTF の規格 24〜26 cm の中。*

[![跳ね際の近接カメラ(1000 fps、256 × 256、20°)の 4 コマ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/05_spin_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/05_spin_frames.png)

*↑ 跳ね際の近接カメラ(1000 fps、256 × 256、20°)の 4 コマ。*

[![知覚(球の位置)にガウス雑音を足したときのラリーの本数(送り合い、上限 8 本): 0 mm → 8 本、50 mm → 8 本、100 mm → 2 本。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/08_rally_vs_noise_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/08_rally_vs_noise.png)

*↑ 知覚(球の位置)にガウス雑音を足したときのラリーの本数(送り合い、上限 8 本): 0 mm → 8 本、50 mm → 8 本、100 mm → 2 本。*

[![追跡カメラ 1(2 × 2 平均で 512 × 400)、100 fps を 1/10 速で。橙の十字は検出、緑は Kalman の状態の投影、赤は跳ねる前の 15 コマから予測した着地点。球は 2291 rpm のトップスピンで、台で 1](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/06_rally_gif.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/06_rally_gif.gif)

*↑ The animation ―― 追跡カメラ 1(2 × 2 平均で 512 × 400)、100 fps を 1/10 速で。橙の十字は検出、緑は Kalman の状態の投影、赤は跳ねる前の 15 コマから予測した着地点。球は 2291 rpm のトップスピンで、台で 1 度跳ねる(e = 0.90)。*

[![自由に動く 2 本のラケット(板 15 × 16 cm、速さ ≤ 6 m/s、加速度 ≤ 60 m/s²)の送り合い(前回に近い少しずらした位置へ返す)、最初の 3 秒を 1/5 速で。相手コートに 1 度跳ねた球を面 x = ±1.55 ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/07_rally_two_rackets.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/07_rally_two_rackets.gif)

*↑ The animation ―― 自由に動く 2 本のラケット(板 15 × 16 cm、速さ ≤ 6 m/s、加速度 ≤ 60 m/s²)の送り合い(前回に近い少しずらした位置へ返す)、最初の 3 秒を 1/5 速で。相手コートに 1 度跳ねた球を面 x = ±1.55 m で迎え撃ち、狙った点へ運動方程式で返す。この設定では上限 12 本まで続く。攻める側(遠い隅を速く)が入ると 9 本で終わる(out)。*

```
py -3.11 examples/poc_ball_bounce.py
```

Source: [examples/poc_ball_bounce.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ball_bounce.py)

This run produced **8 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_ball_bounce)

Ops used (notes): [`add_ball`](https://furuse.work/ops/drive/ballworld/add_ball.html) · [`apex_sequence`](https://furuse.work/ops/drive/ball/apex_sequence.html) · [`ball_detect`](https://furuse.work/ops/drive/balltrack/ball_detect.html) · [`ball_mesh`](https://furuse.work/ops/drive/ballworld/ball_mesh.html) · [`ball_params`](https://furuse.work/ops/drive/ball/ball_params.html) · [`ball_set_pose`](https://furuse.work/ops/drive/ballworld/ball_set_pose.html) · [`ball_track`](https://furuse.work/ops/drive/balltrack/ball_track.html) · [`ball_truth`](https://furuse.work/ops/drive/ballworld/ball_truth.html) · [`bounce`](https://furuse.work/ops/drive/ball/bounce.html) · [`bounce_detect`](https://furuse.work/ops/drive/balltrack/bounce_detect.html) · [`bounce_total_time`](https://furuse.work/ops/drive/ball/bounce_total_time.html) · [`camera_rig`](https://furuse.work/ops/drive/ballworld/camera_rig.html) · [`contact_angular_momentum`](https://furuse.work/ops/drive/ball/contact_angular_momentum.html) · [`crosshair`](https://furuse.work/ops/annotate/pointer/crosshair.html) · [`fit_parabola`](https://furuse.work/ops/drive/ball/fit_parabola.html) · [`flight_fit`](https://furuse.work/ops/drive/ball/flight_fit.html) · [`flight_ode`](https://furuse.work/ops/drive/ball/flight_ode.html) · [`flight_simulate`](https://furuse.work/ops/drive/ball/flight_simulate.html) · [`flight_state_at`](https://furuse.work/ops/drive/ball/flight_state_at.html) · [`flight_vacuum`](https://furuse.work/ops/drive/ball/flight_vacuum.html) · [`impact_params`](https://furuse.work/ops/drive/ball/impact_params.html) · [`kalman_ca`](https://furuse.work/ops/drive/balltrack/kalman_ca.html) · [`marker_direction`](https://furuse.work/ops/drive/balltrack/marker_direction.html) · [`racket_params`](https://furuse.work/ops/drive/racket/racket_params.html) … (+12)

## No.2026.171 —— Kendama the Way the Pioneers Did It — A True-to-Shape Kendama Filmed by Two Cameras, the Ball's Flight Predicted from Images Alone and Caught in the Big, Small and Base Cups

[![Kendama the Way the Pioneers Did It — A True-to-Shape Kendama Filmed by Two Cameras, the Ball's Flight Predicted from Images Alone and Caught in the Big, Small and Base Cups](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/01_rig_view_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/01_rig_view.png)

*↑ **Kendama the Way the Pioneers Did It — A True-to-Shape Kendama Filmed by Two Cameras, the Ball's Flight Predicted from Images Alone and Caught in the Big, Small and Base Cups** ―― Robots have played kendama for thirty years (via-points from a human demonstration in 1996, DMPs plus reinforcement learning for ball-in-a-cup in 2009, the 2020 split into offline swing-up and online catching). This exhibit rebuilds that stance from numpy ops. Shape: from the Japan Kendama Association's published values (60 mm ball, 70 mm across the cups, 180 mm assembled) and a user-supplied description of the JKA 16-2 model (160 mm ken, cups of 42 / 38 / 35 mm, string from the cross-piece hole; primary source not checked), the ken (spike, neck, shaft through the cross piece, stepped and ringed grip, base cup) and the cross piece (flaring like trumpets into the big and small cups) are built as solids of revolution, plus a ball with a 17 mm hole; every dimension measured from the vertices matches to 1e-9, and with the spike pushed to the bottom of the hole the assembly is 180 mm long (the 40 mm hole depth is derived as 160 + 60 − 180). Theorems: the AGM returns K(0.5) = 1.685750354812596 to 1e-12; the period 4√(L/g)K(sin θ₀/2) is recovered to 3.0e-4 by the string (effective length 0.42 m) and 8.9e-11 by a rod; tension matches its closed form to 0.26 %; the slack angle is 125.04° (closed form 125.26°); the projection's dissipation is first order in dt (ratio 9.7); the snap loss equals ½mv_r² to 0.2 %. The closed loop acts on images only: two cameras (480 × 360, 100 fps) render the world, the ball is found by chromaticity and triangulated (median error 0.51 mm), slack is declared when the ball is 5 mm closer to the cross-piece hole than the string length for two frames in a row (truth 0.077 s, images 0.100 s), and a gravity-known parabola (6 unknowns) fitted to the frames after that gives the landing point. The true (p, v) is used only to render the world. The controller's stages are explicit: lift straight up (4.9 g, the ken dodges 10 cm towards the string hole) → wait for slack → wait until the ball's underside clears the kendama → carry the cup horizontally under the ball → lower it at touchdown. Only gravity and string tension move the ball; if the kendama touches it the trial fails (a lift without the dodge hits the cross piece at 0.260 s). The same plan with only the trick's pose switched gives, over 20 trials, big cup truth 1.00 / images 1.00 (lateral 2.40 mm), small cup 1.00 / 1.00, base cup 0.95 / 0.95, candle (truth) 0.95; lowering at touchdown cuts the mean relative speed from 0.91 to 0.61 m/s (big cup). The landing-point error falls with the number of post-slack frames, 10.51 mm (3 frames) → 0.98 mm (44). Pixel noise of 0 / 0.5 / 1 / 2 / 8 / 16 px gives 1.00 / 1.00 / 1.00 / 1.00 / 0.90 / 0.40 — flat up to 2 px because the 21 mm cup rim absorbs it, while the lateral offset grows 2.40 → 4.12 → 12.05 mm. The recommended model (49 mm big cup) also scores 1.00. For a stationary ball the hole direction from two views is off by 1.8° at the median and 4.7° at worst. The world was also turned into 3D Gaussian Splatting before recognition (gsplatnp: Gaussians attached to the world's faces, rendered by EWA projection, front-to-back alpha compositing and Mip-Splatting's opacity compensation; the Gaussians are built from the true shape rather than learned from photos, and reconstruction imperfections are imitated with spacing and error knobs): on 3DGS images at 4 mm spacing the closed loop caught 1 + 2 trials out of 1 + 2 (median triangulation error 0.30 mm); spacing from 2 to 64 mm leaves ball detection at 1.00 (the curvature cap keeps at least 146 Gaussians on the ball), while position error (0.25 at 20 mm) and colour error (0.00 at 0.3) break it. At 480 × 360 the ball's hole is smeared away by the 3DGS blur (1 of 40 poses, mesh 14); at twice the resolution and 2 mm spacing it is read in 16 (median error 2.3°), at 4 mm in none — reading the hole needs pixels on the ball and Gaussians inside the hole. The hole is built as a 40 mm deep cavity, not a disc on the surface (as a disc it vanished under the ball's own Gaussians in 3DGS). Consecutive tricks were added too (the user: "after a catch, carry on from that state and catch in another cup", "10 successes is enough"): the ball is tossed from the cup it sits in (accelerate the cup up and stop it harder than g, and the ball leaves; the apex matches v²/2g to 2e-6 m), the kendama is turned in flight (wrist ≤ 30 rad/s, assumed) to bring the next cup under the landing point, and a hand controller that targets position and velocity matches the ball's speed at the catch (a position-only controller catches nothing with a 20 cm apex). On images alone, moshikame (big ↔ base cup) and the three-cup sequence (big → small → base) both run 10 in a row (grade 5 on the association's moshikame table), relative speed at touchdown 0.41–0.48 m/s, every flight start found from images. Honestly: without noise, 100 in a row is the same cycle repeated; with 2 px of pixel noise moshikame breaks after 3 and the three cups after 6. Honestly: synthetic footage with ground truth, not real video; ball rotation is not simulated (it keeps its last pose once slack); a catch is a geometric test at the moment the ball touches the rim (lateral ≤ rim radius, relative speed ≤ 1 m/s as an assumed threshold, descending) with no bounce or rolling; the 15° tilt of the cup grip, cup depths and the 75 g ball are assumptions. In flight the hole faces down and is almost never seen by both eye-level cameras (0 of 54 frames). Why the candle is harder than the base cup cannot be expressed by a rigid, translating hand. 16 gates, 171.0 s.*

[![近接カメラ(図のためだけ、けん玉から 0.36 m)で見た 4 技の持ち方の姿勢(けんと皿胴は 1 つの剛体、持つ所だけが違う)。けん(けん先 → 細い首 → 皿胴を貫く胴 → 段と輪のある握り → 中皿)、皿胴の両端がラッパのように開いた](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/02_kendama_closeup_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/02_kendama_closeup.png)

*↑ The measurement ―― 近接カメラ(図のためだけ、けん玉から 0.36 m)で見た 4 技の持ち方の姿勢(けんと皿胴は 1 つの剛体、持つ所だけが違う)。けん(けん先 → 細い首 → 皿胴を貫く胴 → 段と輪のある握り → 中皿)、皿胴の両端がラッパのように開いた大皿(赤)・小皿(紫)、中皿(青)、直径 17 mm・深さ 40 mm の穴(くぼみ)のある玉、皿胴の糸穴から出る糸。寸法は JKA 16-2 型(けん 160 mm、横幅 70 mm、皿 42 / 38 / 35 mm)。玉の位置と向きは見せるために置いたもの。 (figure labels are in Japanese; the numbers are the same)*

[![真下から 150° 相当の速さ(3.92 m/s)で打ち出した玉のひも(有効長 0.42 m)の張力。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/03_tension_closed_form_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/03_tension_closed_form.png)

*↑ 真下から 150° 相当の速さ(3.92 m/s)で打ち出した玉のひも(有効長 0.42 m)の張力。*

[![y–z 面(手元を逃がす向き)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/04_catch_yz_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/04_catch_yz.png)

*↑ y–z 面(手元を逃がす向き)。*

[![画像だけの閉ループの成功率(大皿、各 20 試行): 0 px → 1.00、0.5 px → 1.00、1 px → 1.00、2 px → 1.00、8 px → 0.90、16 px → 0.4](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/07_success_vs_pixel_noise_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/07_success_vs_pixel_noise.png)

*↑ 画像だけの閉ループの成功率(大皿、各 20 試行): 0 px → 1.00、0.5 px → 1.00、1 px → 1.00、2 px → 1.00、8 px → 0.90、16 px → 0.40。*

[![3DGS の世界の捕球の試行(弛み → 捕球の 12 コマ)を、つまみを振った 3DGS で描き直して色度の検出(balltrack.ball_detect)にかけた。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/09_gs_noise_knobs_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/09_gs_noise_knobs.png)

*↑ 3DGS の世界の捕球の試行(弛み → 捕球の 12 コマ)を、つまみを振った 3DGS で描き直して色度の検出(balltrack.ball_detect)にかけた。*

[![カメラ 2、100 fps を 1/10 速で(最後のコマで 1 秒止める)。振り上げ → t = 0.077 s にひもが弛む(画像での検出 0.100 s)→ 玉がけんを越えるまで待つ → 皿を水平に運ぶ → 着地で下げる → t = ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/05_catch_gif.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/05_catch_gif.gif)

*↑ The animation ―― カメラ 2、100 fps を 1/10 速で(最後のコマで 1 秒止める)。振り上げ → t = 0.077 s にひもが弛む(画像での検出 0.100 s)→ 玉がけんを越えるまで待つ → 皿を水平に運ぶ → 着地で下げる → t = 0.540 s に大皿で受ける。十字は画像の予測(弛んだ後のコマに当てた重力つきの放物線)から読んだ着地点、枠の中は同じカメラでけん玉のまわりを 3 倍の解像度に描き直した窓。t ≈ 0.3 s に玉がけんに重なって見えるのはカメラから見た重なりで、けんは糸穴の側へ 10 cm 逃げて玉の奥にある(その間の隙間の最小 41 mm)。正直に: 捕球は「縁に触れた瞬間に横ずれ ≤ 21 mm・相対速さ ≤ 1 m/s・下降中」の判定で、縁での跳ねと転がりは描いていない。*

[![右 = 閉ループの知覚が実際に見た画像(世界を 3DGS にして描いたもの、カメラ 2、100 fps を 1/10 速)、左 = 同じ瞬間のメッシュ(真の形)。右上の窓 = 同じカメラでけん玉のまわりを 3 倍の解像度に描き直したもの(左](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/10_gs_catch_gif.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/10_gs_catch_gif.gif)

*↑ The animation ―― 右 = 閉ループの知覚が実際に見た画像(世界を 3DGS にして描いたもの、カメラ 2、100 fps を 1/10 速)、左 = 同じ瞬間のメッシュ(真の形)。右上の窓 = 同じカメラでけん玉のまわりを 3 倍の解像度に描き直したもの(左はメッシュ、右は同じ 3DGS)。青の輪 = 色度で検出した玉、十字 = 弛んだ後のコマに当てた重力つきの放物線から読んだ着地点。t = 0.541 s に大皿で受ける(横ずれ 4.34 mm、推定 391 回は全部 3DGS の画像から)。*

```
py -3.11 examples/poc_kendama.py
```

Source: [examples/poc_kendama.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_kendama.py)

This run produced **11 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_kendama)

Ops used (notes): [`ball_detect`](https://furuse.work/ops/drive/balltrack/ball_detect.html) · [`camera_perceiver`](https://furuse.work/ops/drive/kendamaworld/camera_perceiver.html) · [`catch_plan_staged`](https://furuse.work/ops/drive/kendama/catch_plan_staged.html) · [`catch_success_rate`](https://furuse.work/ops/drive/kendama/catch_success_rate.html) · [`crosshair`](https://furuse.work/ops/annotate/pointer/crosshair.html) · [`elliptic_k_agm`](https://furuse.work/ops/drive/kendama/elliptic_k_agm.html) · [`gs_from_world`](https://furuse.work/ops/drive/gsplat/gs_from_world.html) · [`gs_render`](https://furuse.work/ops/drive/gsplat/gs_render.html) · [`gs_render_fn`](https://furuse.work/ops/drive/gsplat/gs_render_fn.html) · [`gs_update`](https://furuse.work/ops/drive/gsplat/gs_update.html) · [`hole_detect`](https://furuse.work/ops/drive/kendama/hole_detect.html) · [`ken_mesh`](https://furuse.work/ops/drive/kendamaworld/ken_mesh.html) · [`kendama_clearance`](https://furuse.work/ops/drive/kendamaworld/kendama_clearance.html) · [`kendama_combo_simulate`](https://furuse.work/ops/drive/kendama/kendama_combo_simulate.html) · [`kendama_params`](https://furuse.work/ops/drive/kendama/kendama_params.html) · [`kendama_pose`](https://furuse.work/ops/drive/kendamaworld/kendama_pose.html) · [`kendama_rig`](https://furuse.work/ops/drive/kendamaworld/kendama_rig.html) · [`kendama_simulate`](https://furuse.work/ops/drive/kendama/kendama_simulate.html) · [`kendama_world`](https://furuse.work/ops/drive/kendamaworld/kendama_world.html) · [`leader_line`](https://furuse.work/ops/annotate/pointer/leader_line.html) · [`overlay_mask`](https://furuse.work/ops/annotate/overlay/overlay_mask.html) · [`pendulum_launch_speed`](https://furuse.work/ops/drive/kendama/pendulum_launch_speed.html) · [`pendulum_period_exact`](https://furuse.work/ops/drive/kendama/pendulum_period_exact.html) · [`pendulum_rod_simulate`](https://furuse.work/ops/drive/kendama/pendulum_rod_simulate.html) … (+10)

## No.2026.174 —— Filming a Spinning Table-Tennis Ball and Reading Its Spin Two Ways — From the Curve and From the Markings

[![Filming a Spinning Table-Tennis Ball and Reading Its Spin Two Ways — From the Curve and From the Markings](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/03_top_view_sidespin.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/03_top_view_sidespin.gif)

*↑ **Filming a Spinning Table-Tennis Ball and Reading Its Spin Two Ways — From the Curve and From the Markings** ―― Two table-tennis balls launched at the same speed and angle land in different places if they spin differently: topspin dips and lands short, backspin floats and lands long, sidespin curves sideways (the Magnus effect, force along ω × v). This exhibit films four balls that differ only in spin (150 rad/s ≈ 1,430 rpm) with two 240 fps cameras and **reads the spin in two ways**. From the curve: fit the drag + Magnus equation of motion to the triangulated pre-bounce track with 9 parameters (position, velocity, spin) — the new op fit_spin, a damped least-squares fit. The perpendicular-spin error is 3.9 % (top), 0.9 % (back), 1.7 % (side), and the landing point predicted from the read spin is within 2 cm of the truth for all four (x = [0.488, 0.754, 1.124] m; top < none < back). From the markings: film the same ball with a 1000 fps close-up camera (20 frames) and fit the motion of the 14 black marks with Kabsch — 4.8 %, 3.2 %, 0.9 %. The two readings are independent (one sees only the track, the other only the marks) and agree within 10 % (a second-implementation gate). Theorem gate: Magnus force is ω × v, so spin parallel to the direction of travel produces no force — the instantaneous acceleration differs by less than 1e-12, and after 0.25 s of flight the track moves 7.1 mm (versus 5.4 cm for perpendicular spin). fit_spin therefore returns this component separately, and the 22 rad/s the fit reports for the no-spin ball lies almost entirely along that unreadable direction. With a short track the curve is buried in detection error and the spin cannot be read (400.3 % → 4.0 %). Found on the way: from the server-side camera the net's white band hides the top half of a low ball beyond the net and shifts the detected centre (up to 26 mm after triangulation) — detections whose radius is under 0.8× their neighbours' are dropped. The op that turns a mark into a direction (marker_direction) assumed the ball sits on the optical axis, so for a ball crossing the frame the change of line of sight showed up as apparent spin (0.01 rad per ms, 7 % of one frame's rotation) — given the camera K it now solves the perspective exactly. Honestly: synthetic video (known colour, no real lighting or blur); the aerodynamic coefficients (C_d = 0.4, spin-ratio C_L) are the same in truth and fit; spin is constant in flight. 8 gates, 34.4 s.*

[![同じ速さ・同じ向き(v₀ = (6.0, 0, 1.3) m/s)で打ち出した 3 本を横から: トップスピン(橙)は沈んで x = 0.49 m、無回転(黄)は 0.75 m、バックスピン(青)は浮いて 1.12 m に落ちる(台の中心か](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/01_side_three_serves.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/01_side_three_serves.gif)

*↑ The measurement ―― 同じ速さ・同じ向き(v₀ = (6.0, 0, 1.3) m/s)で打ち出した 3 本を横から: トップスピン(橙)は沈んで x = 0.49 m、無回転(黄)は 0.75 m、バックスピン(青)は浮いて 1.12 m に落ちる(台の中心から)。球は見やすさのため 1.6 倍で描いた。MP4 = 240 fps の全コマ(1/8 スロー)。 (figure labels are in Japanese; the numbers are the same)*

[![曲がり方(軌跡に運動方程式を当てる)と模様(近接カメラの Kabsch)は独立。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/04_two_readings_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/04_two_readings.png)

*↑ 曲がり方(軌跡に運動方程式を当てる)と模様(近接カメラの Kabsch)は独立。*

[![跳ねる前の先頭 n コマだけで回転を読む。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/05_error_vs_length_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/05_error_vs_length.png)

*↑ 跳ねる前の先頭 n コマだけで回転を読む。*

[![近接カメラ(1000 fps、20 コマ = 20 ms)のトップスピン。黒い模様(14 個、見えるのは 4〜6 個)を前のコマと向きで対応づけ、Kabsch で回転を当てる: ω = [-0.7, 150.1, -7.2) rad/s(真](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/02_spin_closeup.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/02_spin_closeup.gif)

*↑ The animation ―― 近接カメラ(1000 fps、20 コマ = 20 ms)のトップスピン。黒い模様(14 個、見えるのは 4〜6 個)を前のコマと向きで対応づけ、Kabsch で回転を当てる: ω = [-0.7, 150.1, -7.2] rad/s(真値 (0, 150, 0))。1/100 スロー、3 回繰り返し。*

```
py -3.11 examples/poc_table_tennis_spin.py
```

Source: [examples/poc_table_tennis_spin.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_table_tennis_spin.py)

This run produced **5 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_table_tennis_spin)

Ops used (notes): [`add_ball`](https://furuse.work/ops/drive/ballworld/add_ball.html) · [`ball_detect`](https://furuse.work/ops/drive/balltrack/ball_detect.html) · [`ball_mesh`](https://furuse.work/ops/drive/ballworld/ball_mesh.html) · [`ball_params`](https://furuse.work/ops/drive/ball/ball_params.html) · [`ball_set_pose`](https://furuse.work/ops/drive/ballworld/ball_set_pose.html) · [`ball_track`](https://furuse.work/ops/drive/balltrack/ball_track.html) · [`bounce_detect`](https://furuse.work/ops/drive/balltrack/bounce_detect.html) · [`camera_rig`](https://furuse.work/ops/drive/ballworld/camera_rig.html) · [`fit_spin`](https://furuse.work/ops/drive/ball/fit_spin.html) · [`flight_ode`](https://furuse.work/ops/drive/ball/flight_ode.html) · [`flight_simulate`](https://furuse.work/ops/drive/ball/flight_simulate.html) · [`impact_params`](https://furuse.work/ops/drive/ball/impact_params.html) · [`marker_direction`](https://furuse.work/ops/drive/balltrack/marker_direction.html) · [`reproject`](https://furuse.work/ops/drive/balltrack/reproject.html) · [`rotation_from_omega`](https://furuse.work/ops/drive/ballworld/rotation_from_omega.html) · [`spin_from_marker_sequence`](https://furuse.work/ops/drive/balltrack/spin_from_marker_sequence.html) · [`table_params`](https://furuse.work/ops/drive/ballworld/table_params.html) · [`table_world`](https://furuse.work/ops/drive/ballworld/table_world.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`track_triangulate`](https://furuse.work/ops/drive/balltrack/track_triangulate.html) · [`world_camera`](https://furuse.work/ops/drive/world/world_camera.html)

## No.2026.175 —— Filming a Bouncing Table-Tennis Ball with a High-Speed Camera and Reading Restitution and Friction — Checked Against Published Values

[![Filming a Bouncing Table-Tennis Ball with a High-Speed Camera and Reading Restitution and Friction — Checked Against Published Values](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_bounce/05_regime_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_bounce/05_regime_map.png)

*↑ **Filming a Bouncing Table-Tennis Ball with a High-Speed Camera and Reading Restitution and Friction — Checked Against Published Values** ―― When a table-tennis ball bounces on the table, restitution e decides how much vertical speed survives and friction trades horizontal speed against spin. If the contact point slides only a little the sliding stops during the bounce and the ball **leaves rolling**; if it slides a lot it **leaves still sliding**. This exhibit films 22 bounces with one high-speed camera from the side (1000 fps, ROI readout) and reads e, the friction coefficient μ and the kind of bounce **from the images alone**, checking them against published values. The plane of motion is known, so one camera gives positions (the centre pixel's line of sight meets that plane). The drag + Magnus equation of motion is fitted before and after the bounce to get the velocities at contact, and the spin is read from the ball's marks in two stages (the new op spin_from_marker_sequence). Gates: the closed forms of Cross 2002 (thin shell: a bounce ending rolling has v_x' = 0.6 v_x + 0.4 rω, one still sliding has Δv_t = μ(1+e)|v_z|, the boundary is (2/5)|s| = μ(1+e)|v_z|) agree with the impulse implementation over 300 random impacts / the ITTF table bounce (Laws 2.1.3: 30 cm → about 23 cm) is 23.0 cm from the video / the slope of e against impact speed, -0.00572 per km/h, is within 1.4 % of the −0.0058 measured by Inaba et al. 2017 / sliding bounces give μ = 0.2500 (truth 0.25) / the kind of bounce agrees with the closed-form boundary (15 / 15) / bounces that end rolling have rω' within 3 % of v_x' / on a frictionless table neither horizontal speed nor spin changes. Found on the way: reading 30 → 23 cm as e = √(23/30) = 0.876 drops the air drag — that table bounces only 21.7 cm, and the e that gives about 23 cm with drag is 0.9019. The formula of Inaba et al. itself (intercept 1.0002) makes a table that bounces 25.5 cm from 30 cm, so the two published values disagree (lab table versus standard, or method, not checked). The apparent μ of a bounce that ends rolling is only a lower bound. Honestly: synthetic video; the table's e(v) joins the ITTF intercept and the slope of Inaba et al.; μ is constant (their measurements rise with contact-point speed); the ball does not deform (buckling from 5.5 m/s). 7 gates, 21.6 s.*

[![ITTF の台の跳ねの試験(Laws 2.1.3: 30 cm から落として約 23 cm)。球の下端を 30 cm から落とし、動画から読んだ跳ねの高さは 23.0 cm(世界の真値 23.0 cm)。物差しは 1 cm 刻み。MP4 =](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_bounce/01_drop_test.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_bounce/01_drop_test.gif)

*↑ The measurement ―― ITTF の台の跳ねの試験(Laws 2.1.3: 30 cm から落として約 23 cm)。球の下端を 30 cm から落とし、動画から読んだ跳ねの高さは 23.0 cm(世界の真値 23.0 cm)。物差しは 1 cm 刻み。MP4 = 240 fps の全コマ(1/8 スロー)。 (figure labels are in Japanese; the numbers are the same)*

[![動画から読んだ e(22 本)と公表値。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_bounce/04_restitution_vs_speed_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_bounce/04_restitution_vs_speed.png)

*↑ 動画から読んだ e(22 本)と公表値。*

[![バックスピン(ω = −150 rad/s)の跳ね(当たる瞬間 v = (4.9, −4.3) m/s)、1000 fps を 1/40 スローで。接地点が大きく滑ったまま離れる(滑り +7.89 → +2.89 m/s)。模様から読んだ回](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_bounce/02_backspin_bounce.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_bounce/02_backspin_bounce.gif)

*↑ The animation ―― バックスピン(ω = −150 rad/s)の跳ね(当たる瞬間 v = (4.9, −4.3) m/s)、1000 fps を 1/40 スローで。接地点が大きく滑ったまま離れる(滑り +7.89 → +2.89 m/s)。模様から読んだ回転 -150 → +0 rad/s、横の速さの減り 1.997 m/s → 見かけの μ 0.250。*

[![トップスピン(ω = +200 rad/s)の跳ね(当たる瞬間 v = (2.9, −3.1) m/s)。接地点の滑りが小さいので跳ねの途中で止まり、転がりに移って離れる(滑り -1.17 → -0.01 m/s、跳ねた後の rω' = 3](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_bounce/03_topspin_bounce.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_bounce/03_topspin_bounce.gif)

*↑ The animation ―― トップスピン(ω = +200 rad/s)の跳ね(当たる瞬間 v = (2.9, −3.1) m/s)。接地点の滑りが小さいので跳ねの途中で止まり、転がりに移って離れる(滑り -1.17 → -0.01 m/s、跳ねた後の rω' = 3.320 m/s と v_x' = 3.312 m/s)。*

```
py -3.11 examples/poc_table_tennis_bounce.py
```

Source: [examples/poc_table_tennis_bounce.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_table_tennis_bounce.py)

This run produced **5 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_table_tennis_bounce)

Ops used (notes): [`add_ball`](https://furuse.work/ops/drive/ballworld/add_ball.html) · [`ball_detect`](https://furuse.work/ops/drive/balltrack/ball_detect.html) · [`ball_mesh`](https://furuse.work/ops/drive/ballworld/ball_mesh.html) · [`ball_params`](https://furuse.work/ops/drive/ball/ball_params.html) · [`ball_set_pose`](https://furuse.work/ops/drive/ballworld/ball_set_pose.html) · [`bounce`](https://furuse.work/ops/drive/ball/bounce.html) · [`bounce_detect`](https://furuse.work/ops/drive/balltrack/bounce_detect.html) · [`crosshair`](https://furuse.work/ops/annotate/pointer/crosshair.html) · [`flight_fit`](https://furuse.work/ops/drive/ball/flight_fit.html) · [`flight_ode`](https://furuse.work/ops/drive/ball/flight_ode.html) · [`flight_simulate`](https://furuse.work/ops/drive/ball/flight_simulate.html) · [`flight_state_at`](https://furuse.work/ops/drive/ball/flight_state_at.html) · [`impact_params`](https://furuse.work/ops/drive/ball/impact_params.html) · [`marker_direction`](https://furuse.work/ops/drive/balltrack/marker_direction.html) · [`ray_plane_range`](https://furuse.work/ops/drive/lidar/ray_plane_range.html) · [`reproject`](https://furuse.work/ops/drive/balltrack/reproject.html) · [`rotation_from_omega`](https://furuse.work/ops/drive/ballworld/rotation_from_omega.html) · [`spin_from_marker_sequence`](https://furuse.work/ops/drive/balltrack/spin_from_marker_sequence.html) · [`table_params`](https://furuse.work/ops/drive/ballworld/table_params.html) · [`table_world`](https://furuse.work/ops/drive/ballworld/table_world.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`world_camera`](https://furuse.work/ops/drive/world/world_camera.html)

## No.2026.177 —— Reading Errors End the Table-Tennis Rally — How Much Noise and Latency Move the Landing Point, in Closed Form Before the Shot

[![Reading Errors End the Table-Tennis Rally — How Much Noise and Latency Move the Landing Point, in Closed Form Before the Shot](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_rally_loop/01_landing_cloud.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_rally_loop/01_landing_cloud.gif)

*↑ **Reading Errors End the Table-Tennis Rally — How Much Noise and Latency Move the Landing Point, in Closed Form Before the Shot** ―― A table-tennis robot reads where the ball is, then computes a return that lands on a chosen point of the opponent's half. If the reading is off by δ, the shot is computed **from the misread position** but the ball leaves **from the true one**, so the landing point moves; past the margin to the edge the ball is out and the rally ends. This exhibit works out, before the shot, how a reading error becomes a landing error (the Jacobian J, 2 × 3) and checks whether noise, latency and broken rallies are explained by it. Gates: without air, the numerical J through aiming, racket planning, impact and flight differs from the closed form ΔL_xy = −δ_xy − (v_xy/|v_z(T)|)δ_z by 2.5e-06 (a 1 cm height error moves the landing 2.1 cm along the table) / with drag and Magnus, the spread of 300 shots with σ = 2 cm readings (along 4.6, across 2.0 cm) is within 1.0 and 0.8 % of J Σ Jᵀ / aiming 6 cm from the edge with σ = 3 cm, the out probability is predicted 0.043 and 300 shots give 0.060 (1.5 σ binomial) / the landing error for latency τ = 5, 10, 20 ms matches J · (−vτ − ½gτ² ẑ) within 0.2–0.6 % / noise-free rallies reach the cap of 10 shots all 4 times, while σ = 6 cm (1.2 × the bound σ* = 5.2 cm from the margin) ends after 9, 8, 2, 7 shots, all out / with no error the ball lands 0.52 mm from the target. Found on the way: the height of the "reading τ old" was written with + ½gτ² (it is −). The gate puts the same reading error on both sides, so the mistake passed; a numerical integral caught it. With large noise (12 cm from the edge, σ = 5 cm) the prediction is 0.017 and the shots give 0.003; an earlier seed missed by 2.7 σ the other way, so 300 shots cannot tell which way the linearisation errs. Honestly: only the ball position is misread (velocity and spin are true), the noise is independent Gaussian per frame, the racket hits exactly as planned, and an out is judged only by the edge margin. 6 gates, 289 s.*

[![高さを 5 cm 高く読むと、狙いの計算(灰)は低い弾道を選び、本当の位置から打った球(赤)は狙いより 10.2 cm 手前に落ちる。J の前後の増幅 2.06 × 5 cm = 10.3 cm(一次の予測)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_rally_loop/02_height_misread.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_rally_loop/02_height_misread.gif)

*↑ The measurement ―― 高さを 5 cm 高く読むと、狙いの計算(灰)は低い弾道を選び、本当の位置から打った球(赤)は狙いより 10.2 cm 手前に落ちる。J の前後の増幅 2.06 × 5 cm = 10.3 cm(一次の予測)。 (figure labels are in Japanese; the numbers are the same)*

[![読みの雑音は 3 方向に同じ大きさでも、着地点のずれは前後に 2.2 倍伸びる(高さの読み違いが落ちる角の分だけ増える)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_rally_loop/04_spread_vs_prediction_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_rally_loop/04_spread_vs_prediction.png)

*↑ 読みの雑音は 3 方向に同じ大きさでも、着地点のずれは前後に 2.2 倍伸びる(高さの読み違いが落ちる角の分だけ増える)。*

[![上から見た送り合い(1/2 速)。上 = 読みの雑音 0 で上限の 10 本、下 = 毎コマの読みに σ = 6 cm で 9 本(アウト)。ラケットは届いている —— 途切れる理由は空振りでなく、読み違いから狙った打球のアウト。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_rally_loop/03_rally_compare.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_rally_loop/03_rally_compare.gif)

*↑ The animation ―― 上から見た送り合い(1/2 速)。上 = 読みの雑音 0 で上限の 10 本、下 = 毎コマの読みに σ = 6 cm で 9 本(アウト)。ラケットは届いている —— 途切れる理由は空振りでなく、読み違いから狙った打球のアウト。*

```
py -3.11 examples/poc_table_tennis_rally_loop.py
```

Source: [examples/poc_table_tennis_rally_loop.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_table_tennis_rally_loop.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_table_tennis_rally_loop)

Ops used (notes): [`aim_velocity`](https://furuse.work/ops/drive/racket/aim_velocity.html) · [`ball_params`](https://furuse.work/ops/drive/ball/ball_params.html) · [`flight_simulate`](https://furuse.work/ops/drive/ball/flight_simulate.html) · [`impact_params`](https://furuse.work/ops/drive/ball/impact_params.html) · [`racket_impact`](https://furuse.work/ops/drive/racket/racket_impact.html) · [`racket_params`](https://furuse.work/ops/drive/racket/racket_params.html) · [`racket_plan`](https://furuse.work/ops/drive/racket/racket_plan.html) · [`rally_simulate`](https://furuse.work/ops/drive/racket/rally_simulate.html) · [`table_params`](https://furuse.work/ops/drive/ballworld/table_params.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html)

## No.2026.145 —— Testing the Periodic Boundary of Temporal Operators with a Seamless Loop

[![Testing the Periodic Boundary of Temporal Operators with a Seamless Loop](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/05_contamination_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/05_contamination_map.png)

*↑ **Testing the Periodic Boundary of Temporal Operators with a Seamless Loop** ―― Periodic material carries an exact invariant that any temporal operator must satisfy: for a video of period T, an operator that handles the periodic boundary correctly obeys op(roll(v,k)) == roll(op(v),k) exactly, and any implementation that pads the ends by replication, clamping or truncation breaks it. Because perpetual_loop makes every time-dependent quantity a function of theta, the seam is never created rather than removed (seam ratio 1.0509, where 1 and not 0 is the correct answer), so the truth for that equality is exactly zero difference. No new operator was added. The core finding is that a perfect score came out of an empty output: run with its defaults, three_frame_difference reports a maximum difference of 0.0e+00 and zero contaminated frames, yet only 0 of 32 frames carry any content - the default threshold of 0.1 exceeds the material's largest frame-to-frame change of 0.0841, so nothing is detected at all, and an empty output shifts to another empty output, agreeing trivially. Lowering the threshold to 0.03 gives the same operator 30 of 32 frames of content, 4 contaminated frames and a maximum difference of 1.000 - the perfect score was a lie. Scanning all sixteen single-input video-to-video operators in the ledger splits them into three groups: windowed operators contaminate only the ends (2 frames for causal frame differencing and optical-flow magnitude, 4 for the moving average, 8 for windowed background subtraction, temporal bilateral and temporal median), so trimming that many frames leaves the rest exactly equivariant; recursive or globally normalising operators contaminate all 32 frames and trimming does not help; and three operators return almost nothing, which reads as zero contamination but is not a pass. The contaminated frames are predictable not merely in count but as a set: a window of width w contaminates roll(B,k) union B, and across w = 3, 5, 7, 9, 11 and 13 the predicted set matched exactly (4, 8, 12, 16, 19, 21). The naive prediction of w-1 frames fails in all six cases and 2(w-1) fails at w = 11, where the two bands overlap by exactly one frame at T = 32 with a shift of 9. The first prediction assumed a centred window and was wrong; subtracting the mismatched sets showed contamination only at the head with the tail untouched, which means the window is trailing rather than centred - the orientation of a window can be read off the shape of the contaminated set without reading the implementation.*

[![`perpetual_loop("plasma_orbit")` の 4 コマ。時間に依る量をすべて θ の関数にしてあるので、**t = T は t = 0 と同じ式**です ---- 継ぎ目は消したのではなく最初から作られていません(継](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/01_loop_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/01_loop_frames.png)

*↑ The measurement ―― `perpetual_loop("plasma_orbit")` の 4 コマ。時間に依る量をすべて θ の関数にしてあるので、**t = T は t = 0 と同じ式**です ---- 継ぎ目は消したのではなく最初から作られていません(継ぎ目の比 1.0509、**0 ではなく 1 が正解**)。★だから「巡回シフトしても同じ動画」という**厳密な真値**が素材の側に立ちます。 (figure labels are in Japanese; the numbers are the same)*

[![`three_frame_difference` の同じコマです。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/03_empty_output_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/03_empty_output.png)

*↑ `three_frame_difference` の同じコマです。*

[![継ぎ目の無い動画 32 コマを巡回シフトして測った全数走査です。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/04_scan_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/04_scan.png)

*↑ 継ぎ目の無い動画 32 コマを巡回シフトして測った全数走査です。*

[![窓幅 7 のときに汚れたフレームの位置。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/07_bad_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/07_bad_frames.png)

*↑ 窓幅 7 のときに汚れたフレームの位置。*

[![端だけが汚れる 6 本について、汚れたフレーム数を少ない順に並べたもの。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/08_trim_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/08_trim.png)

*↑ 端だけが汚れる 6 本について、汚れたフレーム数を少ない順に並べたもの。*

[![同じ動画を実際に回したもの(32 コマ)。**最後のコマから最初のコマへ戻るところに継ぎ目が見えません** ---- 消したのではなく、時間に依る量をすべて θ の関数にしてあるので**最初から存在しない**からです。★この性質があるので「](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/02_loop.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/02_loop.gif)

*↑ The animation ―― 同じ動画を実際に回したもの(32 コマ)。**最後のコマから最初のコマへ戻るところに継ぎ目が見えません** ---- 消したのではなく、時間に依る量をすべて θ の関数にしてあるので**最初から存在しない**からです。★この性質があるので「巡回シフトしても同じ動画」が**厳密な真値**になり、時間方向 op の周期境界を数で採点できます。*

```
py -3.11 examples/poc_periodic_video_boundary.py
```

Source: [examples/poc_periodic_video_boundary.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_periodic_video_boundary.py)

This run produced **9 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_periodic_video_boundary)

Ops used (notes): [`moving_average_window`](https://furuse.work/ops/videostream/window/moving_average_window.html) · [`perpetual_loop`](https://furuse.work/ops/generative/loop/perpetual_loop.html) · [`perpetual_loop_seam`](https://furuse.work/ops/generative/loop/perpetual_loop_seam.html) · [`three_frame_difference`](https://furuse.work/ops/videostream/motion/three_frame_difference.html)

### The Geometry and Calibration Wing — A Small Residual Is Not Proof of Correctness

Reprojection error in camera calibration, seam mismatch in a panorama, residual in point-cloud registration: all are read as 'smaller is better'. The 17 exhibits here, with ground truth in hand, show where that reading fails.

Reprojection RMS of 0.0688–0.0690 px alongside focal-length errors of 0.026–7.334 %. Adjacent seams at 0.12 px while the single closing seam opens by 1.5 px. Spheres and cylinders converging to the same residual with an arbitrary pose. Least squares drives the residual down to the noise; whether it lands on the truth is a separate question.

A trap in the measuring procedure itself is kept on display: fix one point cloud and sweep only the pose, and you still have a sample of one — the random seed alone produced both '0 % quadrant errors' and '100 %'. About the only absolute quantity measurable without ground truth is the loop-closure error of a full 360-degree sweep.

## No.2026.006 —— A Reprojection Error of 0.05 px Guarantees Nothing

[![A Reprojection Error of 0.05 px Guarantees Nothing](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/03_frame_fill_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/03_frame_fill.png)

*↑ **A Reprojection Error of 0.05 px Guarantees Nothing** ―― Grid points projected with known intrinsics and poses, re-calibrated, and the error split by component. With the board tilted 32 / 8 / 2 degrees the reprojection RMS spans 0.0688 to 0.0690 px (ratio 1.00) while the focal-length error spans 0.026 to 7.334 % (281x). With a distorting camera the degeneracy gate never fires, and the non-linear optimiser returns an answer even for a fronto-parallel board.*

[![RMS は 1.00 倍しか動かないのに fx 誤差は 281 倍動く。配置の良し悪しを映すのは sigma_fx のほう。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/01_reproj_vs_truth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/01_reproj_vs_truth.png)

*↑ The measurement ―― RMS は 1.00 倍しか動かないのに fx 誤差は 281 倍動く。配置の良し悪しを映すのは sigma_fx のほう。 (figure labels are in Japanese; the numbers are the same)*

[![2 本は重なる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/02_fx_z_coupling_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/02_fx_z_coupling.png)

*↑ 2 本は重なる。*

[![どちらも雑音 0 では真値。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/04_noise_amplification_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/04_noise_amplification.png)

*↑ どちらも雑音 0 では真値。*

[![第 1 部: 同じ雑音 0.05 px の観測を、傾き 32 度(左)と 2 度(右)の配置で解く反復。再投影 RMS はどちらも 0.069 / 0.069 px まで下がるが、fx は左が 1199.7(誤差 0.026 %)、右が 1](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/05_calibration_convergence.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/05_calibration_convergence.gif)

*↑ The animation ―― 第 1 部: 同じ雑音 0.05 px の観測を、傾き 32 度(左)と 2 度(右)の配置で解く反復。再投影 RMS はどちらも 0.069 / 0.069 px まで下がるが、fx は左が 1199.7(誤差 0.026 %)、右が 1112.0(誤差 7.33 %)で止まる。第 2 部: fx を真値の 0.92〜1.08 倍に固定して残りを解き直すと、左は RMS が 0.54 / 0.45 px(両端)まで跳ね上がるのに、右は 0.069 / 0.069 px とほとんど動かない —— 板までの距離 Z が fx と同じ比で動いて(Z 比 0.920 / 1.080)、画素の位置を保つため。右の配置では再投影誤差が焦点距離について何も言っていない。*

```
py -3.11 examples/poc_camera_calibration.py
```

Source: [examples/poc_camera_calibration.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_camera_calibration.py)

This run produced **5 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_camera_calibration)

Ops used (notes): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`data_to_pixel`](https://furuse.work/ops/annotate/plot/data_to_pixel.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`project_points`](https://furuse.work/ops/3d/render/project_points.html) · [`reprojection_error`](https://furuse.work/ops/3d/pose_estimation/reprojection_error.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html)

## No.2026.028 —— Chain the Neighbours Together and You Cannot Get Back Where You Started

[![Chain the Neighbours Together and You Cannot Get Back Where You Started](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/01_seams_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/01_seams.png)

*↑ **Chain the Neighbours Together and You Cannot Get Back Where You Started** ―― 36 frames cut from a cylindrical panorama by a known rotation sequence and chained pairwise around a full turn. Adjacent seams agree to 0.12 px, yet the one closing seam opens by 1.5 px (13x). The buried `bundle_adjust_mosaic` did not beat the chain (30 of 36 frames were left as the identity); the worst pose error goes from 1.65 px for the chain to 0.56 px with global optimisation.*

[![系 2(等分)は閉ループ誤差を下げるのに姿勢はかえって悪化する。新しい観測を足さずに効くのは系 3。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/02_pose_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/02_pose_error.png)

*↑ The measurement ―― 系 2(等分)は閉ループ誤差を下げるのに姿勢はかえって悪化する。新しい観測を足さずに効くのは系 3。 (figure labels are in Japanese; the numbers are the same)*

[![上 2 枚はどちらも継ぎ目が綺麗に見える(後勝ちの上書きで混合しないため)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/03_mosaic_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/03_mosaic.png)

*↑ 上 2 枚はどちらも継ぎ目が綺麗に見える(後勝ちの上書きで混合しないため)。*

[![実測 log-log 傾き 0.89。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/04_drift_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/04_drift.png)

*↑ 実測 log-log 傾き 0.89。*

[![鎖(隣どうしの相対回転を掛けるだけ)で 36 枚を円筒に 1 枚ずつ貼る過程。白い枠が真の位置、橙の枠が鎖の推定位置(ずれを 20 倍に誇張)。隣どうしの継ぎ目は平均 0.119 px で合っているのに、真の姿勢からのずれ(右下の曲線)は積](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/05_chain_drift_video.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/05_chain_drift_video.gif)

*↑ The animation ―― 鎖(隣どうしの相対回転を掛けるだけ)で 36 枚を円筒に 1 枚ずつ貼る過程。白い枠が真の位置、橙の枠が鎖の推定位置(ずれを 20 倍に誇張)。隣どうしの継ぎ目は平均 0.119 px で合っているのに、真の姿勢からのずれ(右下の曲線)は積み上がって最悪 1.65 px(フレーム 16)。一周して 0 枚目(赤紫)と35 枚目(緑)を重ねると閉じる継ぎ目が 1.50 px 開き、縁に色の縞(二重像)が出る(左下、4 倍拡大)。最後に同じ 36 本の辺を閉ループ拘束で解き直すと(水色)、姿勢のずれは最悪 1.18 px、閉じる継ぎ目は 0.11 px。*

```
py -3.11 examples/poc_panorama_drift.py
```

Source: [examples/poc_panorama_drift.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_panorama_drift.py)

This run produced **5 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_panorama_drift)

Ops used (notes): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`pose_error`](https://furuse.work/ops/3d/metrics/pose_error.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html) · [`warp_by_plane`](https://furuse.work/ops/3d/plane_sweep_stereo/warp_by_plane.html)

## No.2026.108 —— Measuring on a Real Stereo Photograph — Three Stumbles Synthesis Never Produces

[![Measuring on a Real Stereo Photograph — Three Stumbles Synthesis Never Produces](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stereo_depth/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stereo_depth/01_scene.png)

*↑ **Measuring on a Real Stereo Photograph — Three Stumbles Synthesis Never Produces** ―― The first exhibit in this museum measured on a **real photograph** (Middlebury 2014 motorcycle, with ground-truth disparity). The distributor's own note says the holes in the truth are NaN; they are +inf, so np.nanmedian reports a median disparity of 44.97 px instead of 42.55 px, while fill_disparity and apply_cmap — which test with isfinite — handle them correctly. The default max_disp=16 scores bad2 95.06 %: any search range below the true maximum of 59.91 px loses the whole foreground, so the cliff sits between 48 and 64, which geometry predicts before any measurement. Against a 94.04 % null, SGM scores 15.81 %, and discarding the least confident 40 % takes it to 6.80 %. Converting to metric depth bends the scene: depth_from_disparity had no principal-point offset, and ignoring the real doffs of 31.086 px puts points 1.519 to 5.243 times too far — no single scale repairs it, since the best factor of 0.3733 still leaves 958.3 mm RMS over a 2889 mm range, pushing far surfaces +1676 mm out and pulling near ones -926 mm in. The argument was added here, and it reproduces the closed form exactly.*

[![下位 4 割を捨てると bad2 は 26.75 % -> 6.80 %。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stereo_depth/02_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stereo_depth/02_error.png)

*↑ The measurement ―― 下位 4 割を捨てると bad2 は 26.75 % -> 6.80 %。 (figure labels are in Japanese; the numbers are the same)*

[![真の最大視差を下回る設定は前景を丸ごと失う。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stereo_depth/03_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stereo_depth/03_cliff.png)

*↑ 真の最大視差を下回る設定は前景を丸ごと失う。*

[![単一のスケールでは直らない(最良でも残差 958 mm RMS)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stereo_depth/04_depth_bend_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stereo_depth/04_depth_bend.png)

*↑ 単一のスケールでは直らない(最良でも残差 958 mm RMS)。*

[![census が最下位なのは窓が 64 bit で頭打ちだから。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stereo_depth/05_methods_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stereo_depth/05_methods.png)

*↑ census が最下位なのは窓が 64 bit で頭打ちだから。*

```
py -3.11 examples/poc_real_stereo_depth.py
```

Source: [examples/poc_real_stereo_depth.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_stereo_depth.py)

This run produced **5 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_real_stereo_depth)



## No.2026.034 —— The Convergence Basin of Point-Cloud Registration — How Far Off Can the Initial Pose Be?

[![The Convergence Basin of Point-Cloud Registration — How Far Off Can the Initial Pose Be?](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/01_basin_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/01_basin.png)

*↑ **The Convergence Basin of Point-Cloud Registration — How Far Off Can the Initial Pose Be?** ―― ICP success rate contoured against the initial pose error, with the point cloud re-sampled on every trial. With no translation offset, success drops below 50 % at 90 degrees for point-to-point and 120 degrees for point-to-plane. Spheres and cylinders converge to the same residual with an arbitrary pose; with the global method all 16 of 16 trials appear converged and the pose is wrong — undetectable from the residual.*

[![非対称性が消えると 4 候補が形として区別できず、選択が崩れる(選ばれた解が第 1 候補から離れる)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/02_pca_quadrant_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/02_pca_quadrant.png)

*↑ The measurement ―― 非対称性が消えると 4 候補が形として区別できず、選択が崩れる(選ばれた解が第 1 候補から離れる)。 (figure labels are in Japanese; the numbers are the same)*

[![平らな線ほど「広い」。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/03_width_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/03_width.png)

*↑ 平らな線ほど「広い」。*

[![球・円柱は残差が小さいまま姿勢が任意。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/04_symmetry_lies_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/04_symmetry_lies.png)

*↑ 球・円柱は残差が小さいまま姿勢が任意。*

[![点対点 ICP を 1 反復ずつ動かす(fs.icp(max_iter=1) を前回の姿勢から連鎖)。灰 = 目標の点群、色 = 動かしている点群(斜めから見た正射影)。同じ回転軸で初期回転ずれだけを 30 / 90 / 150 度と変え、](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/05_icp_basin_iterations.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/05_icp_basin_iterations.gif)

*↑ The animation ―― 点対点 ICP を 1 反復ずつ動かす(fs.icp(max_iter=1) を前回の姿勢から連鎖)。灰 = 目標の点群、色 = 動かしている点群(斜めから見た正射影)。同じ回転軸で初期回転ずれだけを 30 / 90 / 150 度と変え、並進ずれは直径の 10 %。反復予算は本文の点対点 ICP と同じ 60 回で、その後の回転誤差: 30 度 → 0.6 度(成功)、90 度 → 0.6 度(成功)、150 度 → 179.5 度(失敗)。下の曲線は回転誤差の推移(対数、灰線 = 成功のしきい値 3 度)。動画専用に取り直した 1 組の点群での 1 試行の軌跡で、成功率は第 2 章の表。*

```
py -3.11 examples/poc_registration_basin.py
```

Source: [examples/poc_registration_basin.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_registration_basin.py)

This run produced **5 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_registration_basin)

Ops used (notes): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`farthest_point_sampling`](https://furuse.work/ops/3d/geodesic/farthest_point_sampling.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html)

## No.2026.117 —— Which Quantities Really Survive a Rotation — Auditing Invariance on a Real Coin

[![Which Quantities Really Survive a Rotation — Auditing Invariance on a Real Coin](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rotation_invariance_audit/01_rotation_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rotation_invariance_audit/01_rotation_frames.png)

*↑ **Which Quantities Really Survive a Rotation — Auditing Invariance on a Real Coin** ―― Shape features are routinely called rotation-invariant, but the pixel grid is not invariant under rotation, so the claim usually breaks at a helper — how the boundary is counted, how the image is interpolated, where the threshold lands. A real photograph (scikit-image `coins`, Greek coins from Pompeii, British Museum) is turned through a full circle in 5-degree steps and the wobble is split into three arms: **A** rotate the greyscale and re-threshold (what people actually do), **B** rotate the 0-degree binary mask with nearest neighbour (re-rasterisation only), **C** multiples of 90 degrees via `np.rot90` (exact). The rotation itself is done with scipy, not with fullseye — measuring your own invariance with your own rotation hides errors that lean the same way. **Arm C is exactly 0.00 % for all seven quantities**: the measurements carry no orientation bias at all, so every bit of the wobble is the cost of re-laying the boundary on the grid. **The prediction was wrong**: rotating the *binary mask* turns out to be far worse than interpolating the grey — perimeter 2.52 % (A) vs 9.47 % (B), circularity 4.82 % vs 20.45 %. Nearest-neighbour rotation re-lays a staircase; interpolating the grey re-derives the boundary from the underlying continuous signal. **Rotate the greyscale, never the mask.** A synthetic square anchors the closed form: the 4-connected staircase perimeter of a square rotated 45 degrees is bounded by `4L → 4L√2` (+41.4 %), but the measured swing is 7.91 % because `regionprops` applies a Crofton-style correction — the closed form is a ceiling, not a prediction. Finally, check the denominator: Hu[1] is ~0 for a near-circular blob (3.9e-04), so its 29.6 % relative spread means nothing at all.*

[![実写の硬貨を 5 度ずつ 1 周。地がモノクロなので輪郭は彩度のある色で描いている(灰色には彩度が無いので、どの階調とも色相で区別がつく)。右の表の数字がどれだけ揺れるかが見える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rotation_invariance_audit/02_rotating_coin.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rotation_invariance_audit/02_rotating_coin.gif)

*↑ The measurement ―― 実写の硬貨を 5 度ずつ 1 周。地がモノクロなので輪郭は彩度のある色で描いている(灰色には彩度が無いので、どの階調とも色相で区別がつく)。右の表の数字がどれだけ揺れるかが見える。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_rotation_invariance_audit.py
```

Source: [examples/poc_rotation_invariance_audit.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_rotation_invariance_audit.py)

This run produced **2 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_rotation_invariance_audit)

Ops used (notes): [`annotate_outline`](https://furuse.work/ops/annotate/paper/annotate_outline.html) · [`annotate_table`](https://furuse.work/ops/annotate/paper/annotate_table.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`circularity`](https://furuse.work/ops/2d/features/circularity.html) · [`eccentricity`](https://furuse.work/ops/2d/features/eccentricity.html) · [`moments_region_2nd_invar`](https://furuse.work/ops/2d/features/moments_region_2nd_invar.html) · [`moments_region_central_invar`](https://furuse.work/ops/2d/features/moments_region_central_invar.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html)

## No.2026.190 —— One Scene, Two Worlds — Scoring a Photoreal Simulator's Depth Against a Closed-Form Truth, Side by Side with Our Own World

[![One Scene, Two Worlds — Scoring a Photoreal Simulator's Depth Against a Closed-Form Truth, Side by Side with Our Own World](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_carla_bridge/01_carla_two_worlds_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_carla_bridge/01_carla_two_worlds.png)

*↑ **One Scene, Two Worlds — Scoring a Photoreal Simulator's Depth Against a Closed-Form Truth, Side by Side with Our Own World** ―― The author's wish: "put the finished form of everything we built into the most realistic environment there is" — so, both environments. Our own world (all ground truth, not photoreal) and the external photoreal simulator CARLA 0.9.16 (code MIT, assets CC-BY; photoreal, but its formulas are hidden) are joined by a bridge, carlabridge (25 ops, numpy only). On a straight in Town04 a lead car is placed 8–64 m ahead and RGB, depth and semantic images are captured; the recorded poses (left-handed, degrees) are mapped to our right-handed frame and the image-plane distance to the rear face is computed in closed form; the same rule-based perception (median depth over car-labelled pixels) is applied to CARLA's image and to our own world re-rendered with the same intrinsics and mounting. CARLA's depth sits +0.10 m from the truth in every frame (bounding-box origin offset), our re-render within ±0.3 m, the car pixel count follows 1/d² in both (log-log slopes −1.94 / −1.99) with pixel ratios 0.90–1.08. Gates: rotation matrices equal CARLA's own get_matrix, camera pose equals look_at, depth round-trips within one quantisation step, world → record → re-render is pixel-identical. Honestly: CARLA's truth itself cannot be verified — what is verified is that the conventions are invertible and agree with the closed form; agreement is not proof of correctness. CARLA imagery uses CC-BY assets (CARLA team).*

[![先行車の後ろ面までの像面距離の真値は記録の姿勢から閉形式で出す。車のラベルの画素の深度の中央値は CARLA で全コマ +0.1 m、自前の描き直しで ±0.3 m。最下行から平らな路面の式で出す距離は後輪の接地を見るのでバンパーより 0.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_carla_bridge/02_carla_depth_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_carla_bridge/02_carla_depth_error.png)

*↑ The measurement ―― 先行車の後ろ面までの像面距離の真値は記録の姿勢から閉形式で出す。車のラベルの画素の深度の中央値は CARLA で全コマ +0.1 m、自前の描き直しで ±0.3 m。最下行から平らな路面の式で出す距離は後輪の接地を見るのでバンパーより 0.5 m ほど先を指す。 (figure labels are in Japanese; the numbers are the same)*

[![像面に平行な後ろ面の面積は距離の 2 乗に反比例する。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_carla_bridge/03_carla_pixels_inverse_square_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_carla_bridge/03_carla_pixels_inverse_square.png)

*↑ 像面に平行な後ろ面の面積は距離の 2 乗に反比例する。*

[![コマごとの数字。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_carla_bridge/04_carla_pair_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_carla_bridge/04_carla_pair_table.png)

*↑ コマごとの数字。*

```
py -3.11 examples/poc_carla_bridge.py
```

Source: [examples/poc_carla_bridge.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_carla_bridge.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_carla_bridge)

Ops used (notes): [`camera_pose_to_carla`](https://furuse.work/ops/drive/carla/camera_pose_to_carla.html) · [`carla_camera_pose`](https://furuse.work/ops/drive/carla/carla_camera_pose.html) · [`carla_depth_decode`](https://furuse.work/ops/drive/carla/carla_depth_decode.html) · [`carla_depth_encode`](https://furuse.work/ops/drive/carla/carla_depth_encode.html) · [`carla_label_map`](https://furuse.work/ops/drive/carla/carla_label_map.html) · [`carla_label_unmap`](https://furuse.work/ops/drive/carla/carla_label_unmap.html) · [`carla_labels`](https://furuse.work/ops/drive/carla/carla_labels.html) · [`carla_rotation_angles`](https://furuse.work/ops/drive/carla/carla_rotation_angles.html) · [`carla_scene_load`](https://furuse.work/ops/drive/carla/carla_scene_load.html) · [`carla_scene_save`](https://furuse.work/ops/drive/carla/carla_scene_save.html) · [`carla_scene_synthetic`](https://furuse.work/ops/drive/carla/carla_scene_synthetic.html) · [`carla_transform_matrix`](https://furuse.work/ops/drive/carla/carla_transform_matrix.html) · [`intrinsics_to_fullseye`](https://furuse.work/ops/drive/carla/intrinsics_to_fullseye.html) · [`lead_truth_depth`](https://furuse.work/ops/drive/carla/lead_truth_depth.html) · [`scene_pair_table`](https://furuse.work/ops/drive/carla/scene_pair_table.html)

## No.2026.191 —— Assembling One Town — Auto-Joining Driving-School Elements, Driving Through from Entry to Exit, and Scoring Every Stop Line on the Way

[![Assembling One Town — Auto-Joining Driving-School Elements, Driving Through from Entry to Exit, and Scoring Every Stop Line on the Way](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_town/01_town_overview_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_town/01_town_overview.png)

*↑ **Assembling One Town — Auto-Joining Driving-School Elements, Driving Through from Entry to Exit, and Scoring Every Stop Line on the Way** ―― The foundation for the author's plan "one capstone per PoC series, driving first". The intersection, railway crossing, slope and parallel-parking bay that earlier PoCs placed and scored one at a time are joined into a single road by the new module drivetown (10 ops): element k+1's entry is placed onto element k's exit in closed form with a 0.05 m overlap. The default town has 9 elements over 235.1 m. A longitudinal-only driver follows the centreline, treats the next stop line as a stationary lead vehicle for IDM braking, waits 2 s at the intersection and looks left and right at the crossing before moving on, and if the warning is active it waits until the barrier is up (the crossing carries gated warning posts, booms and a train driven by the interpretation-standard state machine). The rule pack town_rules gives JP = left-hand traffic with a mandatory stop and look at crossings, US and DE = right-hand traffic stopping only while the warning is active; packs other than JP are marked verified False because their primary sources have not been checked. Figures: the town from above (polygons, centreline, stop lines, stopping positions, signals), speed and acceleration over time, an on-board drive-through (stopped at red → moving on green → booms down → train passing → booms up and moving → before the slope), and a table of 9 rule-pack runs, and the 159-scene curriculum ledger. 38 gates: with a train warning at 20 s the car leaves the crossing at 65.50 s ≥ booms fully up at 65.45 s with zero time on the crossing while forbidden, JP stops twice while US/DE stop once without a train, the right-hand stop line mirrors about the intersection centre (s 40.95 ↔ 65.95), the boom covers 1078 pixels and the train 46,129 pixels in the on-board frames, joint position error minus overlap 1.1e-14 at all 8 joints with zero heading error, total length equals Σ centerline_length − 0.05 × 8 exactly, stop-line positions in closed form from the regulation dimensions, stops 0.537 / 0.536 m short of the lines, |a| at most 1.877 ≤ 3, trapezoidal ∫v dt matches s to 3.9e-11 m, braking distance ≥ v²/2b, the existing crossing_stop_check passes, and the same commands fed to long_simulate (RK4) stop within 0.002 m. Honestly: lateral motion is pinned to the centreline, the signal is "green after 2 s" without reading the lamp, there are no other vehicles or pedestrians, and the US/DE hold times reuse the JP values.*

[![IDM(a_max 1.5、b_max 3.0、v_max 8)で停止線の手前に止まる。交差点は 2 秒。踏切は左右確認 4 秒の後、警報 20 s に始まった状態機械(降下 → 遮断 → 列車 → 上昇)が idle に戻る 65.5 s](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_town/02_town_speed_time_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_town/02_town_speed_time.png)

*↑ The measurement ―― IDM(a_max 1.5、b_max 3.0、v_max 8)で停止線の手前に止まる。交差点は 2 秒。踏切は左右確認 4 秒の後、警報 20 s に始まった状態機械(降下 → 遮断 → 列車 → 上昇)が idle に戻る 65.5 s まで待って発進。下の帯 = 警報中の区間と列車が踏切に居る区間。|a| の最大 1.88 m/s²。 (figure labels are in Japanese; the numbers are the same)*

[![止まった位置は停止線の 0.54, 0.54 m 手前。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_town/03_town_speed_distance_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_town/03_town_speed_distance.png)

*↑ 止まった位置は停止線の 0.54, 0.54 m 手前。*

[![GIF の 6 コマ(静止画)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_town/05_town_camera_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_town/05_town_camera_frames.png)

*↑ GIF の 6 コマ(静止画)。*

[![JP = 左側通行・踏切は常に停止 + 左右確認(道路交通法 33 条 1 項、本文で確認)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_town/06_town_rules_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_town/06_town_rules_table.png)

*↑ JP = 左側通行・踏切は常に停止 + 左右確認(道路交通法 33 条 1 項、本文で確認)。*

[![docs/drive/kyosoku_scenarios.json の件数。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_town/07_town_kyosoku_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_town/07_town_kyosoku_table.png)

*↑ docs/drive/kyosoku_scenarios.json の件数。*

[![車載カメラ(640×400、13 コマ)で町を通し走行。赤信号で止まり、青で発進、踏切で止まって左右を見て、下りた遮断かんと点滅する警報灯の前で列車が過ぎて上がるまで待ってから渡り、坂を越えて縦列駐車の前を抜ける。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_town/04_town_drive_through.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_town/04_town_drive_through.gif)

*↑ The animation ―― 車載カメラ(640×400、13 コマ)で町を通し走行。赤信号で止まり、青で発進、踏切で止まって左右を見て、下りた遮断かんと点滅する警報灯の前で列車が過ぎて上がるまで待ってから渡り、坂を越えて縦列駐車の前を抜ける。*

```
py -3.11 examples/poc_driving_town.py
```

Source: [examples/poc_driving_town.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_driving_town.py)

This run produced **7 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_driving_town)

Ops used (notes): [`course_crank`](https://furuse.work/ops/drive/course/course_crank.html) · [`course_loop_bend`](https://furuse.work/ops/drive/course/course_loop_bend.html) · [`course_road`](https://furuse.work/ops/drive/course/course_road.html) · [`course_s_curve`](https://furuse.work/ops/drive/course/course_s_curve.html) · [`crossing_stop_check`](https://furuse.work/ops/drive/crossing/crossing_stop_check.html) · [`idm_accel`](https://furuse.work/ops/drive/traffic/idm_accel.html) · [`intersection`](https://furuse.work/ops/2d/nary/intersection.html) · [`kyosoku_summary`](https://furuse.work/ops/drive/town/kyosoku_summary.html) · [`long_params`](https://furuse.work/ops/drive/long/long_params.html) · [`long_simulate`](https://furuse.work/ops/drive/long/long_simulate.html) · [`town_centerline`](https://furuse.work/ops/drive/town/town_centerline.html) · [`town_chain`](https://furuse.work/ops/drive/town/town_chain.html) · [`town_checks`](https://furuse.work/ops/drive/town/town_checks.html) · [`town_crossing_state`](https://furuse.work/ops/drive/town/town_crossing_state.html) · [`town_layout`](https://furuse.work/ops/drive/town/town_layout.html) · [`town_rules`](https://furuse.work/ops/drive/town/town_rules.html) · [`town_run`](https://furuse.work/ops/drive/town/town_run.html) · [`town_stop_lines`](https://furuse.work/ops/drive/town/town_stop_lines.html) · [`town_world`](https://furuse.work/ops/drive/town/town_world.html) · [`world_camera`](https://furuse.work/ops/drive/world/world_camera.html)

## No.2026.192 —— Building a Real Japanese Town in Our Own World and Driving It — Roads from OpenStreetMap, Buildings from PLATEAU, Japanese Furniture and Rules

[![Building a Real Japanese Town in Our Own World and Driving It — Roads from OpenStreetMap, Buildings from PLATEAU, Japanese Furniture and Rules](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_japan_town/04_japan_town_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_japan_town/04_japan_town_frames.png)

*↑ **Building a Real Japanese Town in Our Own World and Driving It — Roads from OpenStreetMap, Buildings from PLATEAU, Japanese Furniture and Rules** ―― The author's wish: "if possible, do it on a Japanese map". The bundled maps of external photoreal simulators are European or American towns with right-hand traffic, and adding a Japanese town would need an editor build and Japanese assets, so we build Japan in our own world instead. The road network is an OpenStreetMap extract (equirectangular projection; widths from OSM tags or the Road Structure Ordinance lane widths as defaults). The road shape is the raster union of edges drawn as width-carrying segments, traced into boundary loops by Fullseye's own contour tracer (contours_xld, whose area equals the pixel count exactly); the holes are city blocks, given pavements and kerbs. Buildings come from MLIT's Project PLATEAU CityGML (LOD1 footprint and height → extruded prisms, driveplateau). The street furniture follows the regulation dimensions: the stop sign (330-A, 80 cm side), the stop line (45 cm), the road lettering 止まれ (Traffic Regulation Standard figure (1): 240 × 80 cm per character, 1 m apart, vertical), Japanese crosswalks with 45 cm stripes parallel to travel, crossbucks, utility poles and curve mirrors. The route is the shortest path (respecting one-way streets) shifted to the left-hand lane centre, with signals, stop signs and level crossings as stop lines, driven by drivetown's through-run under the JP rule pack. Figures: Ginza 0.7 × 0.6 km from above, a bird's-eye view with 852 PLATEAU buildings, an on-board drive-through (stop at red → go on green → stop sign), the same run's frames, the furniture before a stop sign with its label image, the road-network table and the speed profile. 24 gates: 0.001° of latitude = 111.3195 m and agreement with a second implementation to 1e-9, straight-road union area = L w + π(w/2)² within 0.04 %, loop area = pixel count × step² within 1.5e-11 m², 4 holes in the 3 × 3 grid, shortest path 160 m with stop lines at 76.25 / 156.25 m in closed form, right-hand route mirrored, a 320 m detour around a reversed one-way street, two stops 0.54 m short of their lines with town_checks ok, the stop-sign plate 0.8 m on a side with its top at 2.5 m, the 止まれ column 9.2 m long, sign and lettering visible in the frame before the stop sign, and a 30 m synthetic CityGML prism. On real data: 586 OSM edges, 122 blocks, 852 buildings, area gate 5e-8 m², and a 461 m route to a signalled junction driven with 7 stops, ok. Honestly: 60 % of widths are class defaults where OSM has no tag; no lane assignment, signal phases, other vehicles or pedestrians; the 止まれ glyphs are polyline approximations (official dimensions); crossbuck plate sizes are assumed; slivers under 4 m² are not built; PLATEAU ground relief is ignored. Figure credits: roads © OpenStreetMap contributors (ODbL), buildings: MLIT Project PLATEAU. The data themselves are not committed.*

[![銀座 0.7 × 0.6 km の俯瞰: OSM の道路網を幅つきでラスタ化した和集合の穴 = 街区(歩道 + 縁石)、信号・横断歩道・電柱。 道路: © OpenStreetMap contributors (ODbL) / 建物: 出典](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_japan_town/01_japan_town_topdown_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_japan_town/01_japan_town_topdown.png)

*↑ The measurement ―― 銀座 0.7 × 0.6 km の俯瞰: OSM の道路網を幅つきでラスタ化した和集合の穴 = 街区(歩道 + 縁石)、信号・横断歩道・電柱。 道路: © OpenStreetMap contributors (ODbL) / 建物: 出典 国土交通省 Project PLATEAU (figure labels are in Japanese; the numbers are the same)*

[![PLATEAU(国交省 3D 都市モデル、LOD1 の足元と高さ)の建物 852 棟を押し出し柱で立てた銀座。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_japan_town/02_japan_town_bird_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_japan_town/02_japan_town_bird.png)

*↑ PLATEAU(国交省 3D 都市モデル、LOD1 の足元と高さ)の建物 852 棟を押し出し柱で立てた銀座。*

[![日本の道具立て(寸法は道路標識令 別表第二 / 交通規制基準 第 46 図例(1))。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_japan_town/05_japan_furniture_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_japan_town/05_japan_furniture.png)

*↑ 日本の道具立て(寸法は道路標識令 別表第二 / 交通規制基準 第 46 図例(1))。*

[![幅の由来: {'lanes': 192, 'default': 375, 'width': 19}(width タグ / lanes × 車線幅 / 種別の既定)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_japan_town/06_japan_road_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_japan_town/06_japan_road_table.png)

*↑ 幅の由来: {'lanes': 192, 'default': 375, 'width': 19}(width タグ / lanes × 車線幅 / 種別の既定)。*

[![停止線: [(3.3, 'intersection'), (15.2, 'intersection'), (133.1, 'intersection'), (396.4, 'intersection'](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_japan_town/07_japan_speed_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_japan_town/07_japan_speed.png)

*↑ 停止線: [(3.3, 'intersection'), (15.2, 'intersection'), (133.1, 'intersection'), (396.4, 'intersection'), (419.3, 'intersection'), (432.1, 'intersection'…*

[![左の車線中心を通して走る車載カメラ(JP 法規パック): 赤で停止 → 2 秒で青 → 発進、一時停止では止まって確認。道路: © OpenStreetMap contributors (ODbL) / 建物: 出典 国土交通省 Proje](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_japan_town/03_japan_town_drive.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_japan_town/03_japan_town_drive.gif)

*↑ The animation ―― 左の車線中心を通して走る車載カメラ(JP 法規パック): 赤で停止 → 2 秒で青 → 発進、一時停止では止まって確認。道路: © OpenStreetMap contributors (ODbL) / 建物: 出典 国土交通省 Project PLATEAU*

```
py -3.11 examples/poc_driving_japan_town.py
```

Source: [examples/poc_driving_japan_town.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_driving_japan_town.py)

This run produced **7 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_driving_japan_town)

Ops used (notes): [`citygml_synthetic`](https://furuse.work/ops/drive/japan/citygml_synthetic.html) · [`intersection`](https://furuse.work/ops/2d/nary/intersection.html) · [`japan_stats`](https://furuse.work/ops/drive/japan/japan_stats.html) · [`japan_world`](https://furuse.work/ops/drive/japan/japan_world.html) · [`jp_sign_stop_mesh`](https://furuse.work/ops/drive/japan/jp_sign_stop_mesh.html) · [`jp_stop_marking_mesh`](https://furuse.work/ops/drive/japan/jp_stop_marking_mesh.html) · [`latlon_to_local`](https://furuse.work/ops/drive/japan/latlon_to_local.html) · [`osm_parse`](https://furuse.work/ops/drive/japan/osm_parse.html) · [`osm_road_graph`](https://furuse.work/ops/drive/japan/osm_road_graph.html) · [`osm_road_loops`](https://furuse.work/ops/drive/japan/osm_road_loops.html) · [`osm_road_mask`](https://furuse.work/ops/drive/japan/osm_road_mask.html) · [`osm_route`](https://furuse.work/ops/drive/japan/osm_route.html) · [`osm_synthetic`](https://furuse.work/ops/drive/japan/osm_synthetic.html) · [`plateau_parse`](https://furuse.work/ops/drive/japan/plateau_parse.html) · [`town_checks`](https://furuse.work/ops/drive/town/town_checks.html) · [`town_run`](https://furuse.work/ops/drive/town/town_run.html) · [`world_camera`](https://furuse.work/ops/drive/world/world_camera.html)

## No.2026.193 —— Driving Our Own Driver Through Someone Else's Scenario and Submitting to Someone Else's Judge — CommonRoad Public Scenarios and TUM's Official Checker

[![Driving Our Own Driver Through Someone Else's Scenario and Submitting to Someone Else's Judge — CommonRoad Public Scenarios and TUM's Official Checker](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_commonroad/01_commonroad_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_commonroad/01_commonroad_scene.png)

*↑ **Driving Our Own Driver Through Someone Else's Scenario and Submitting to Someone Else's Judge — CommonRoad Public Scenarios and TUM's Official Checker** ―― The user's remark "setting your own traps and clearing them yourself has its limits" led to a new rule: bring at least one of the truth, the gate or the subject in from outside. Earlier driving PoCs planted their own ground truth in a synthetic world, wrote their own gates and scored their own driver. Here the scenario is a public CommonRoad (TUM) scenario (BSD-3), the judge is TUM's drivability-checker (it does not install on Windows, so it runs in WSL and tools/check_solution_json.py writes the verdict as JSON), and only the driver is ours. The new module drivecommonroad (10 ops) reads 2020a XML itself (lanelet boundaries, dynamic obstacles, planning problem, sign 274 speed limits, stopLine), chains lanelets by successor, drives with IDM longitudinally and pure pursuit laterally under kinematic single-track (KS) dynamics (rear-axle reference, RK4, BMW_320i parameters copied from commonroad-vehicle-models' parameters_vehicle2), stops at stop lines and writes the official solution XML (ksTrajectory). It also carries a second implementation of the judge (feasibility by re-integrating the recorded inputs to 2 cm / 0.03 rad, collision by separating axes, road boundary by point-in-polygon) to set beside the official JSON. Figures: a bird's-eye view (lanelets, obstacle tracks, ego, goal lanelet), speed and acceleration, gaps to each obstacle, six frames (start, before the junction, turning left, closest to oncoming, entering the goal lanelet, stopped), a table of our verdicts against the official ones, and the sweep table. 22 gates: on the synthetic T-junction the reader (4 lanelets, 1 obstacle, 274 → 13.89 m/s), route 98.84 m = Σ centrelines (1e-6), KS straight line to 1e-9 and circle radius l_wb/tan δ (1e-6), goal reached with |a| ≤ 3 and v ≤ limit, stop 0.90 m short of the stop line, feasible (max_pos_err 0), no collision, a driver that ignores the car ahead collides at (step 52, obstacle 2), the blocked scene stops short, 201 ksStates = steps with positions = rear axle + b (1e-12). On the real ZAM_Tjunction-1_1_T-1 (12 lanelets, 5 obstacles, limit 14.0, route 347.6 m) the default IDM hits oncoming car 1; the 14th gap-acceptance setting (a_lat 8.0, lookahead 5.0) yields a 148-state run (v_max 9.82 m/s, 0.83 m lateral error) that the official checker accepts: valid, goal reached, feasible, no collision, n_states 148. The negative control (the gentle default driver) collides at (68, 1) in our check and the official checker also reports obstacle_collision true and valid false (feasible true), so our five verdicts agree with the official ones for both runs. Honestly: ZAM is not solvable by IDM alone and was solved by the sweep (no yielding behaviour; waiting would miss the goal time window); 8 m/s² lateral is uncomfortable though inside the checker's friction circle (8.1 < 11.5); the public 2020a scenarios contain no traffic lights, stop lines or stop signs 206, so rule scoring is synthetic only; the official verdict is the WSL JSON (our feasibility re-integrates the recorded inputs with the same RK4, hence zero error); a longitudinal-only driver still collides in Speyer and Moabit. Source: CommonRoad scenarios (TUM, BSD-3). The data are not committed (FULLSEYE_COMMONROAD_DATA).*

[![IDM の希望速度 v₀ = min(制限, 曲率の許容 √(a_lat/|κ|))。a は区分一定(RK4 の 1 step ごと)。|a| ≤ max(a_max 1.5, b_max 3.0)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_commonroad/02_commonroad_speed_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_commonroad/02_commonroad_speed.png)

*↑ The measurement ―― IDM の希望速度 v₀ = min(制限, 曲率の許容 √(a_lat/|κ|))。a は区分一定(RK4 の 1 step ごと)。|a| ≤ max(a_max 1.5, b_max 3.0)。 (figure labels are in Japanese; the numbers are the same)*

[![近似(中心間距離 − 両車の半長)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_commonroad/03_commonroad_gap_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_commonroad/03_commonroad_gap.png)

*↑ 近似(中心間距離 − 両車の半長)。*

[![俯瞰の 6 コマ(matplotlib で描いた PNG)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_commonroad/04_commonroad_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_commonroad/04_commonroad_frames.png)

*↑ 俯瞰の 6 コマ(matplotlib で描いた PNG)。*

[![公式 = commonroad-drivability-checker 2025.4.0。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_commonroad/05_commonroad_checks_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_commonroad/05_commonroad_checks.png)

*↑ 公式 = commonroad-drivability-checker 2025.4.0。*

[![IDM だけでは対向車 obs 1 より先に左折できず、曲がりの許容横加速度と見通しを順に上げた。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_commonroad/06_commonroad_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_commonroad/06_commonroad_sweep.png)

*↑ IDM だけでは対向車 obs 1 より先に左折できず、曲がりの許容横加速度と見通しを順に上げた。*

```
py -3.11 examples/poc_driving_commonroad.py
```

Source: [examples/poc_driving_commonroad.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_driving_commonroad.py)

This run produced **6 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_driving_commonroad)

Ops used (notes): [`boundary`](https://furuse.work/ops/2d/region/boundary.html) · [`cr_checker_result`](https://furuse.work/ops/drive/commonroad/cr_checker_result.html) · [`cr_collision`](https://furuse.work/ops/drive/commonroad/cr_collision.html) · [`cr_drive`](https://furuse.work/ops/drive/commonroad/cr_drive.html) · [`cr_drive_sweep`](https://furuse.work/ops/drive/commonroad/cr_drive_sweep.html) · [`cr_feasible`](https://furuse.work/ops/drive/commonroad/cr_feasible.html) · [`cr_read`](https://furuse.work/ops/drive/commonroad/cr_read.html) · [`cr_route`](https://furuse.work/ops/drive/commonroad/cr_route.html) · [`cr_solution_xml`](https://furuse.work/ops/drive/commonroad/cr_solution_xml.html) · [`cr_synthetic`](https://furuse.work/ops/drive/commonroad/cr_synthetic.html) · [`ks_step`](https://furuse.work/ops/drive/commonroad/ks_step.html)

## No.2026.195 —— Peg-in-Hole with a Compliant Wrist — Whitney's Quasi-Static Geometry as the Gate, a Wrist Camera to Centre the Peg, MuJoCo Contacts to Check It

[![Peg-in-Hole with a Compliant Wrist — Whitney's Quasi-Static Geometry as the Gate, a Wrist Camera to Centre the Peg, MuJoCo Contacts to Check It](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pegsim_insertion/03_pegsim_wrist_overlay_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pegsim_insertion/03_pegsim_wrist_overlay.png)

*↑ **Peg-in-Hole with a Compliant Wrist — Whitney's Quasi-Static Geometry as the Gate, a Wrist Camera to Centre the Peg, MuJoCo Contacts to Check It** ―― The first exhibit of the physics-simulation × Fullseye series (the physics side of the rule 'home-made traps have a ceiling: bring in the truth, the gate or the subject from outside'). Two things come from outside. The theorem: Whitney 1982 (ASME J. Dyn. Sys. Meas. Control 104(1), DOI 10.1115/1.3149634; the paper itself is paywalled and was not read — the formulas are taken from the author's own MIT OCW 2.875 Class 3 slides: two-point contact depth l/d = c/θ, θ_m = √(2c), wedging if θ > c/μ, the jamming parallelogram with λ = l/(2rμ)). The contact physics: MuJoCo (contact points, normal forces, mj_geomDistance). No learning — only the rule measure → correct → descend → slow down on force. Three things are our own: the two-point depth made exact for a 3-D cylinder, l tan θ = 2R − r(cos θ + sec θ) (derived; l sin θ ≈ 2c_r to fourth order), a second implementation that predicts the number of contact points from the true pose by geometry alone, and a measurement that reads the hole centre (anti-aliased edge lifted onto the plate plane, then a circle fit) and the peg tip (known-radius cylinder on the depth points, the tip from the silhouette end matched against the projected rim circle) in 3-D from one wrist RGB-D frame. New module pegsim, 18 ops (plus 9 facade functions that need mujoco). Figures: wrist-camera overlay (green = truth, red = estimate, yellow = edge points, 3× inset), insertion GIF with correction, GIF of the peg sliding down the chamfer without correction, three theoretical l₂ curves with the MuJoCo measurements, the jamming diagram at l = 2 / 8 mm, and the success table. 23 gates: Whitney's quantities by hand (c = 0.0385, θ_m = 15.9°, chamfer tolerance 1.2 mm, c/μ = 7.35°), l₂ sin θ = 0.3977–0.3999 mm (2c_r = 0.400), the 2-D rectangle approximation is 0.52 mm off at 6° (counter-example), the second implementation switches from one to two points at l₂ ∓ 0.05 mm, PnP identity to 1e-9, the known-radius circle fit agrees with measure.fit_circle to 1e-9 on a full circle and has a median centre error of 0.15 px on a 25° arc (free fit 3.3 px), the synthetic RGB-D (analytic ray cast, no mujoco) gives the hole centre to 0.004 px and the offset to 0.0004 mm, and the image-plane ellipse centre is 0.80 px away from the projected circle centre (why we fit in 3-D). MuJoCo gates: the depth buffer under MSAA holds sample 0 at (−0.125, +0.375) px (pixel centre with offsamples=0); over 8 poses (|ε| ≤ 3 mm, |θ| ≤ 3°) the hole centre is within 0.18 px (free circle) / 0.045 px (drawing radius R + W), the offset within 0.024 / 0.010 mm, the tip's lateral error 0.003 px; l₂ measured by bisection on mj_geomDistance matches the closed form to 0.017–0.070 mm (1.5–6°) with l₂ sin θ = 0.396–0.398 mm; the contact state switches one-point / two-point at l₂ ∓ 0.3 mm; the insertion with ε = (2, 1) mm and θ = 2° succeeds and the first two-point tick has l sin θ = 0.400 mm; 7 servo iterations take the true offset from 2.24 to 0.03 mm; without correction ε₀ = 1 mm is pushed in by the chamfer; the grid ε₀ {0, 1, 2, 3} mm × θ₀ {0, 1.5, 3}° succeeds up to 1 mm without correction (2 mm and more stop at the mouth — the chamfer tolerance is 1.2 mm) and 12 / 12 with it. Honestly: the tip's axial position comes from the coverage of one silhouette pixel and is off by up to 0.50 px (the 0.3 px target is not met); the raw agreement between predicted and simulated contact counts is 0.69 (0.96 within ±1 — soft contacts flicker between 0/1 and 1/2 points); the wrist is a rigid body on springs with no actuator lag, flex or calibration error; wedging cannot occur at θ ≤ 3° with μ = 0.3 and was not provoked; the original paper was not read. Traps: MuJoCo's 4× MSAA depth is the depth at sample 0, not at the pixel centre (measured on a tilted plane; depth is rendered from a second compile with offsamples=0), the default 28 slices of a cylinder pull the radius 0.04 mm inwards (numslices=128), and the first 2-D rectangle approximation D = d/cos θ + l tan θ is 0.5 mm wrong at θ = 6°. Without mujoco the MuJoCo gates are skipped and the 12 numpy gates decide. 37 s.*

[![傾き θ で二点接触が始まる深さ l₂(最狭部から)。3-D の円柱で厳密にした (1′) と小角の式 l₂ sin θ = 2c_r は重なり、2-D の長方形近似は θ = 6° で 0.5 mm 浅い。点は MuJoCo の mj_g](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pegsim_insertion/01_pegsim_two_point_depth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pegsim_insertion/01_pegsim_two_point_depth.png)

*↑ The measurement ―― 傾き θ で二点接触が始まる深さ l₂(最狭部から)。3-D の円柱で厳密にした (1′) と小角の式 l₂ sin θ = 2c_r は重なり、2-D の長方形近似は θ = 6° で 0.5 mm 浅い。点は MuJoCo の mj_geomDistance の二分法で測った値(閉形式と 0.07 mm 以内)。1° では 22.9 mm と穴の深さ 20 mm を超え、二点接触は起きない。 (figure labels are in Japanese; the numbers are the same)*

[![Whitney のかじりの図(OCW p.34): 二点接触中にペグが進むのは加える力の比がこの平行四辺形の内側にあるとき。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pegsim_insertion/02_pegsim_jamming_diagram_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pegsim_insertion/02_pegsim_jamming_diagram.png)

*↑ Whitney のかじりの図(OCW p.34): 二点接触中にペグが進むのは加える力の比がこの平行四辺形の内側にあるとき。*

[![初期横ずれ ε₀ × 傾き θ₀ の成功 / 失敗(各 1 走行、ずれの向きは 30°)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pegsim_insertion/06_pegsim_success_grid_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pegsim_insertion/06_pegsim_success_grid.png)

*↑ 初期横ずれ ε₀ × 傾き θ₀ の成功 / 失敗(各 1 走行、ずれの向きは 30°)。*

[![補正ありの挿入(ε₀ = (2, 1) mm、θ₀ = 2°、側面カメラ、0.15 s ごと): サーボで穴の上に寄せ、下げ、一点 → 二点接触を経て 15 mm。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pegsim_insertion/04_pegsim_insert_corrected.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pegsim_insertion/04_pegsim_insert_corrected.gif)

*↑ The animation ―― 補正ありの挿入(ε₀ = (2, 1) mm、θ₀ = 2°、側面カメラ、0.15 s ごと): サーボで穴の上に寄せ、下げ、一点 → 二点接触を経て 15 mm。*

[![補正なし(ε₀ = 1 mm < 面取りの許容 1.2 mm、θ₀ = 2°): 面取りが柔らかい手首を横へ押し、ペグが滑り込む。2 mm では入口で止まる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pegsim_insertion/05_pegsim_chamfer_slide_no_correction.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pegsim_insertion/05_pegsim_chamfer_slide_no_correction.gif)

*↑ The animation ―― 補正なし(ε₀ = 1 mm < 面取りの許容 1.2 mm、θ₀ = 2°): 面取りが柔らかい手首を横へ押し、ペグが滑り込む。2 mm では入口で止まる。*

```
py -3.11 examples/poc_pegsim_insertion.py
```

Source: [examples/poc_pegsim_insertion.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pegsim_insertion.py)

This run produced **6 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_pegsim_insertion)

Ops used (notes): [`camera_world_to_cv`](https://furuse.work/ops/drive/pegsim/camera_world_to_cv.html) · [`chamfer_capture`](https://furuse.work/ops/drive/pegsim/chamfer_capture.html) · [`circle_fit_known_radius`](https://furuse.work/ops/drive/pegsim/circle_fit_known_radius.html) · [`contact_state_predict`](https://furuse.work/ops/drive/pegsim/contact_state_predict.html) · [`jamming_diagram`](https://furuse.work/ops/drive/pegsim/jamming_diagram.html) · [`peg_measure_overlay`](https://furuse.work/ops/drive/pegsim/peg_measure_overlay.html) · [`peg_offset_from_rgbd`](https://furuse.work/ops/drive/pegsim/peg_offset_from_rgbd.html) · [`peg_params`](https://furuse.work/ops/drive/pegsim/peg_params.html) · [`peg_scene_mjcf`](https://furuse.work/ops/drive/pegsim/peg_scene_mjcf.html) · [`peg_synthetic_rgbd`](https://furuse.work/ops/drive/pegsim/peg_synthetic_rgbd.html) · [`project_points`](https://furuse.work/ops/3d/render/project_points.html) · [`two_point_depth`](https://furuse.work/ops/drive/pegsim/two_point_depth.html) · [`wedging_check`](https://furuse.work/ops/drive/pegsim/wedging_check.html) · [`whitney_clearance`](https://furuse.work/ops/drive/pegsim/whitney_clearance.html)

## No.2026.200 —— Tracking, Predicting and Returning an Air-Hockey Puck with a Five-Bar Linkage — No Learning, Closed Forms and an External Simulator as the Gates

[![Tracking, Predicting and Returning an Air-Hockey Puck with a Five-Bar Linkage — No Learning, Closed Forms and an External Simulator as the Gates](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_air_hockey_intercept/01_airhockey_frame_detect_predict_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_air_hockey_intercept/01_airhockey_frame_detect_predict.png)

*↑ **Tracking, Predicting and Returning an Air-Hockey Puck with a Five-Bar Linkage — No Learning, Closed Forms and an External Simulator as the Gates** ―― The third exhibit of the physics-simulation × Fullseye series (the first was peg-in-hole, the second the three visuotactile exhibits). The subject is a low-cost air-hockey robot (Shinjo, Beltran-Hernandez, Hamaya, Tanaka, IROS 2024, doi 10.1109/iros58592.2024.10801458): a five-bar linkage driven by position-control servos, with the chain camera → puck detection → velocity estimation → trajectory prediction → motion planning. The chain is rebuilt with existing Fullseye parts (balltrack.ball_detect / ball_track / kalman_ca, ballistics.slide_stop_distance, calib.image_to_world_plane) and the new module puck (26 ops), learning-free and rule-based throughout, with ground truth brought in from outside on three fronts. (1) Closed forms: sliding on the air cushion is Coulomb's uniform deceleration a = μg (stopping distance v₀²/(2μg)); a wall flips the normal component by −e and keeps kₜ of the tangential one (two coefficients of restitution; the notation follows Cross 2022, Eur. J. Phys., doi 10.1088/1361-6404/ac4b47, oblique impact of a disc; the Spong 2001 impact model could not be read and is unverified); between walls the path is stitched from per-segment closed forms (a quadratic or a logarithm) — against the mirror method as a second implementation (no friction, e = kₜ = 1) it agrees to 3e-15 m over 200 launches with up to 17 reflections, and to 1.5e-5 m against semi-implicit Euler at dt = 1e-5. (2) Five-bar kinematics: the closed form of two two-link arms meeting at the striker (circle–circle intersections); FK∘IK returns to 2e-15 m on 400 workspace points and the reach circle l₁ + l₂ separates inside from outside at ±1e-6 m. (3) An external simulator: the table MJCF of the Robot Air Hockey Challenge (Liu et al., arXiv 2411.05718, MIT; the file is not bundled, it lives under the environment variable FULLSEYE_AIRHOCKEY_DATA and is used only with --full). ★The second implementation exposed a model difference: this table excludes the puck–surface contact and slows the puck through joint viscous damping c = 0.005 N·s/m (m = 0.01 kg → c/m = 0.5 /s, a 2 s time constant). It is not Coulomb deceleration (measured log-speed slope −0.4999 /s). The rims are soft contacts, so e and kₜ are not parameters but measured outcomes (e_n = 0.739, kₜ = 0.852). Adding model="viscous" to the predictor matches MuJoCo to 0.110 mm before the first wall and, with the measured e and kₜ, to 0.4 mm 0.4 s after one bounce. Our own Coulomb MJCF (a cylinder on a frictional plane) decelerates 3.3 % away from μg (whether MuJoCo's soft-contact friction or our MJCF settings is not resolved). The synthetic top-down camera draws the puck with coverage anti-aliasing and adds motion during the exposure as the mean of sub-exposures: the blurred centroid advances by v·τ/2 (closed form, matched to 0.004 px — it vanishes if the frame is stamped at mid-exposure). Detection is a facade over ball_detect with the threshold just below the table value, 0.85 — the weight is (threshold − pixel), so at 0.5 the edge pixels are cut and a phase-dependent bias of 0.08 px appears (measured; 0.005 px at 0.85). Velocity is a least-squares fit of the uniform-deceleration model with the direction û fixed (û iterated three times; the viscous case is linear in the basis (1 − e^{−kτ})/k) and σ_v comes from σ²(AᵀA)⁻¹. The striker plan is a rule: IK to the crossing point, each servo at a constant rate ≤ 6 rad/s, too_late if it cannot arrive first, unreachable outside the workspace, no_crossing if the path never crosses (fail-closed). Figures: a 343 px/m frame with the 16 detections, the predicted path and the crossing point (0.0 mm from the truth, 756 ms ahead) next to a 1:1 crop of the puck (nearest neighbour ×8) with the sub-pixel centroid (0.004 px from the truth); a GIF where the 95 % band of the crossing narrows as frames accumulate on a coarse camera (100 px/m, noise σ 0.06); velocity error vs N inside 3σ; a GIF of the five-bar linkage arriving first (move 256 ms, crossing 883 ms); where it breaks (blur, an unknown wall kₜ fans the prediction after a bounce, 45 px per frame breaks ball_track's association); MuJoCo vs the viscous closed form vs Coulomb (three curves with --full). 16 gates (numpy only, 1.6 s, 7 s with figures) plus 6 with --full (MuJoCo, 13 s): stopping distance = ballistics (0), wall energy ratio e², mirror method 3e-15 m, self-consistency + Euler 1.5e-5 m, FK∘IK 2e-15 m, the reach boundary and the reachable interval |y| ≤ 0.369 on the defence line x = −0.75 (the puck can be at |y| ≤ 0.487, so the corners are out of reach — stated honestly), detection centroids over 50 positions max 0.0059 px / rms 0.0024 px (0.012 mm), velocity from exact positions 7e-16 and from detections at N = 12 0.01 % (σ_v 0.2 mm/s), crossing points from noisy detections over 20 launches rms 0.2 mm / max 0.5 mm (threshold 3σ_mc + a 2 mm floor because the 60-sample Monte-Carlo σ itself wobbles by ±10 %), the plan E = (−0.750, 0.350) with a 0.256 s move, 8 m/s → too_late, y = 0.47 → unreachable, blur 0.004 px, six spelling-breaks plus None without a crossing, μ to 0.7 % (the 0.3 s bend is 0.8 px), e 0.7999 and kₜ 0.9001, fast puck 10/10 at 20 and 35 px per frame but 1/10 at 45 and 80 (max_jump 40 px, 27 m/s at 120 fps), kalman_ca innovation 2.7e-13 m; --full: viscous slope −0.4999 /s, closed form 0.110 mm, 0.4 mm after the bounce, Coulomb MJCF 3.3 %, render → colour detection → pinhole bias (−2.6, 2.3) mm and scatter 0.35 mm (0.12 px; the bias comes from the site height and render quantisation and is subtracted in the chain), the full chain over 20 launches: 14 crossed the defence line, all 12 within reach were intercepted, 2 in the corners were declined, crossing error median 1.2 mm / max 14.9 mm (inside the 71.65 mm puck + mallet radius), timing max 21 ms. Honestly: the linkage dimensions (d 0.30, l₁ 0.25, l₂ 0.35 m), the 6 rad/s servo rate, the 40 mm mallet, the defence line x = −0.75 and the closed-form defaults μ 0.02 / e 0.8 / kₜ 0.9 are all assumptions (the paper's hardware numbers could not be read); no real footage is used (synthetic + MuJoCo, no lighting, lens distortion or rolling shutter; the synthetic detection error of 0.006 px is more than an order of magnitude better than reality); the slip/grip regimes and spin of a wall impact are not implemented; e and kₜ are estimated by splitting the track at the frame where the heading changes most (a single bounce only).*

[![粗いカメラ(100 px/m、雑音 σ 0.06)でも、コマが増えるほど守備線上の交点の 95 % 帯(赤)が細る: N = 3 で 145 mm → N = 16 で 7 mm。緑の十字 = 真の交点。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_air_hockey_intercept/02_airhockey_prediction_cone_narrows.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_air_hockey_intercept/02_airhockey_prediction_cone_narrows.gif)

*↑ The measurement ―― 粗いカメラ(100 px/m、雑音 σ 0.06)でも、コマが増えるほど守備線上の交点の 95 % 帯(赤)が細る: N = 3 で 145 mm → N = 16 で 7 mm。緑の十字 = 真の交点。 (figure labels are in Japanese; the numbers are the same)*

[![検出から最小二乗で出した速度の誤差は N とともに縮み、最小二乗の分散の 3σ(破線)の内側に収まる(N = 12 で 0.01 %、N = 24 で 0.01 %)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_air_hockey_intercept/03_airhockey_velocity_error_vs_N_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_air_hockey_intercept/03_airhockey_velocity_error_vs_N.png)

*↑ 検出から最小二乗で出した速度の誤差は N とともに縮み、最小二乗の分散の 3σ(破線)の内側に収まる(N = 12 で 0.01 %、N = 24 で 0.01 %)。*

[![どこで壊れるか。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_air_hockey_intercept/05_airhockey_where_it_breaks_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_air_hockey_intercept/05_airhockey_where_it_breaks.png)

*↑ どこで壊れるか。*

[![Challenge の台では速さが指数で落ちる(粘性減衰 c/m = 0.5 /s、実測の傾き -0.4999 /s)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_air_hockey_intercept/06_airhockey_mujoco_vs_closed_form_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_air_hockey_intercept/06_airhockey_mujoco_vs_closed_form.png)

*↑ Challenge の台では速さが指数で落ちる(粘性減衰 c/m = 0.5 /s、実測の傾き -0.4999 /s)。*

[![8 コマで予測した交点へ、5 節リンク(一定角速度 ≤ 6 rad/s、寸法は仮定)が 191 ms で先回りして打具(緑の円、半径 40 mm は仮定)を置く。交点の到着は 823 ms 先。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_air_hockey_intercept/04_airhockey_fivebar_intercept.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_air_hockey_intercept/04_airhockey_fivebar_intercept.gif)

*↑ The animation ―― 8 コマで予測した交点へ、5 節リンク(一定角速度 ≤ 6 rad/s、寸法は仮定)が 191 ms で先回りして打具(緑の円、半径 40 mm は仮定)を置く。交点の到着は 823 ms 先。*

```
py -3.11 examples/poc_air_hockey_intercept.py
```

Source: [examples/poc_air_hockey_intercept.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_air_hockey_intercept.py)

This run produced **6 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_air_hockey_intercept)

Ops used (notes): [`crosshair`](https://furuse.work/ops/annotate/pointer/crosshair.html) · [`fivebar_fk`](https://furuse.work/ops/drive/puck/fivebar_fk.html) · [`fivebar_ik`](https://furuse.work/ops/drive/puck/fivebar_ik.html) · [`fivebar_link`](https://furuse.work/ops/drive/puck/fivebar_link.html) · [`fivebar_reach_interval`](https://furuse.work/ops/drive/puck/fivebar_reach_interval.html) · [`fivebar_trajectory`](https://furuse.work/ops/drive/puck/fivebar_trajectory.html) · [`fivebar_workspace`](https://furuse.work/ops/drive/puck/fivebar_workspace.html) · [`kalman_ca`](https://furuse.work/ops/drive/balltrack/kalman_ca.html) · [`puck_camera`](https://furuse.work/ops/drive/puck/puck_camera.html) · [`puck_crossing_point`](https://furuse.work/ops/drive/puck/puck_crossing_point.html) · [`puck_detect`](https://furuse.work/ops/drive/puck/puck_detect.html) · [`puck_mirror_path`](https://furuse.work/ops/drive/puck/puck_mirror_path.html) · [`puck_mu_from_decel`](https://furuse.work/ops/drive/puck/puck_mu_from_decel.html) · [`puck_pinhole_camera`](https://furuse.work/ops/drive/puck/puck_pinhole_camera.html) · [`puck_render_frame`](https://furuse.work/ops/drive/puck/puck_render_frame.html) · [`puck_restitution_from_wall`](https://furuse.work/ops/drive/puck/puck_restitution_from_wall.html) · [`puck_scene_mjcf`](https://furuse.work/ops/drive/puck/puck_scene_mjcf.html) · [`puck_slide_predict`](https://furuse.work/ops/drive/puck/puck_slide_predict.html) · [`puck_state_at`](https://furuse.work/ops/drive/puck/puck_state_at.html) · [`puck_stop_distance`](https://furuse.work/ops/drive/puck/puck_stop_distance.html) · [`puck_synth_frames`](https://furuse.work/ops/drive/puck/puck_synth_frames.html) · [`puck_table`](https://furuse.work/ops/drive/puck/puck_table.html) · [`puck_track`](https://furuse.work/ops/drive/puck/puck_track.html) · [`puck_velocity_estimate`](https://furuse.work/ops/drive/puck/puck_velocity_estimate.html) … (+5)

## No.2026.201 —— Detecting and Recovering Peg-Insertion Failures with a Rule Table — Whitney's Contact States Instead of a VLM, MuJoCo as the Truth

[![Detecting and Recovering Peg-Insertion Failures with a Rule Table — Whitney's Contact States Instead of a VLM, MuJoCo as the Truth](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_failure_recovery/01_pegfail_where_it_breaks_offset_flip_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_failure_recovery/01_pegfail_where_it_breaks_offset_flip.png)

*↑ **Detecting and Recovering Peg-Insertion Failures with a Rule Table — Whitney's Contact States Instead of a VLM, MuJoCo as the Truth** ―― The capstone of the peg-in-hole thread of the physics-simulation × Fullseye series (pegsim, soft-wrist insertion, 2026.195). The prior work (Shirasaka, Beltran-Hernandez, Hamaya, Ushiku, arXiv:2509.17666, ICRA 2026, code unpublished) structures soft-wrist insertion as contact formation — a sequence of contact states that constrain the degrees of freedom one by one — and lets a VLM judge the failure mode from the final pose and an image before picking a recovery skill. Here the VLM is replaced by a rule table: the observation (contact kind none / plate / chamfer / one_point / two_point / floor, depth band above / mouth / hole / bottom, stall, whether the tilt at the onset of two-point contact is above c/μ, whether the force ratio lies inside the jamming parallelogram, whether the tip offset from the hole centre is within W + c_r) is discretised into a six-field signature and looked up in a 12-row table. At most one row matches (a validator first checks pairwise exclusivity and that all 8 classes are reachable); if none does the answer is unknown (the table decides 362 of the 576 signatures in the vocabulary and never guesses the rest: fail-closed). Ground truth comes from outside on two fronts. (1) The theorem: Whitney 1982 (the original is paywalled and unread; the equations are from the author's own MIT OCW 2.875 Class 3 slides): wedging θ > c/μ (p.28), the jamming parallelogram λ = l/(2rμ) (p.34). The four vertices are re-derived from the planar statics of two-point contact (both points sliding down with Coulomb friction: F_x = f₂ − f₁, F_z = μ(f₁ + f₂), M = μrf₁ − (μr + l)f₂) and agree with pegsim's vertices (the OCW values) to 2.2e-16 — this derivation fixes the sign convention of the force ratios (e_x from the wall the tip touches towards the opposite mouth edge, F_z positive when pushing, M = M⃗·(e_x × ẑ)). (2) The physics engine: MuJoCo's contact points, normal forces and the wrist force sensor (--full). The tip load (F⃗, M⃗_tip) is read from the deflection of the wrist springs (a rule that needs no external F/T sensor): over the 3,458 quasi-static ticks spent stalled, the estimated load plus gravity balances the sum of the contact forces to 0.35 N, and agrees with the wrist force sensor (site frame → world) to 0.026 N. Failures are injected on purpose: an offset of 2.5 mm the chamfer cannot catch (> W + c_r = 1.2 mm), wedging with μ 0.8 and θ₀ 4.5° (> c/μ = 2.76°), jamming with θ₀ 3° and a +3 mm lateral target shift towards the tilt once the tip is 4 mm in, a plug at 6 mm depth, a decoy hole 26 mm away. The chain is descend (slow at 2.5 N, 12 N cap) → stall (advance < 0.05 mm over a 30-tick window, armed after 0.5 mm of progress) → signature → table → recovery primitive (lift 6 mm and re-centre with the wrist RGB-D / lift 10 mm and return to the fixture target / retract 4 mm and undo the measured tilt / pick the 0.5 mm carriage × 0.5° wrist step that maximises the parallelogram margin in a linear model / lift and abort). Figures: the flip probability of the offset field when σ = 0.05 mm noise is added at the W + c_r = 1.2 mm boundary (0.508 at the boundary, 0.168 / 0.157 at ±1σ, within 0.03 of Φ(−1); dashed = theory), the confusion matrix of the 6 injected classes (6 / 6 from truth signatures, 6 / 6 from the vision signatures), the jamming diagram with the trajectory of force ratios estimated from the wrist load (the tick where the jam stall is detected lies outside its own-depth parallelogram at l = 5.3 mm with margin −0.50, the 321 ticks of nominal two-point sliding lie inside with min 0.18 / median 0.20 — the diagram widens with depth, so two parallelograms are drawn), depth vs tick for the wedge (stall → wedging in the same tick → retract + tilt reset → re-descend and succeed), a 48-frame wrist-camera GIF ('detected: wedging -> retract_reduce_tilt' appears, then the re-descent), and the release-probe table. ★The release probe shows Whitney's distinction physically: the wedge (μ 0.8, θ 4.7°) stays at 5.90 mm when the push is removed (F_z 2.03 → 0.64 N) and even when pulled by 2 mm (F_z −0.39 N) — compression is stored inside; the jam (μ 0.3, θ 4.4°, F_x 1.3 N) advances under its own weight from 6.25 to 7.21 mm once the lateral force is also removed and comes back to 5.30 mm when pulled — a matter of force direction. 12 gates (numpy only, 0.6 s) plus 8 with --full (MuJoCo, 14 s, 35 s with figures): table completeness and exclusivity, parallelogram vertices 2.2e-16, the wedging boundary at c/μ ∓ 1e-9 rad (7.353° at μ 0.3, 2.755° at 0.8), stall detection (no false alarm on three monotone descents plus a hover, onset 27 ticks after the true stop, armed at tick 17), all 362 row signatures classify to their row, three unknown signatures and four spelling breaks, the closed-form wrist load to 1e-12, flip probability = Φ(−|z|), synthetic RGB-D (analytic ray cast, no mujoco) offsets at four poses to 0.002 mm → field → class = truth, discretisation boundaries, the summary latency of 30 ticks and the confusion matrix, the MJCF (two force/torque sensors, the plug, 109 decoy geoms plus a 4-box frame, ValueError for a plug outside the hole or an overlapping decoy); --full: force closure, the injection grid 6 classes × {no recovery, recovery} with 6 / 6 from truth and from vision signatures and 0/5 → 5/5 (the blocked hole is correctly aborted = success), detection latencies of 32–33 ticks (= 30-tick window + ≤ 10 confirmation), 9 for the plug and 18 for the decoy, the release probe, the jamming-diagram margin (the "inside" threshold 0.15 sits between the stalled −0.50 and the sliding 0.18 — MuJoCo's sliding boundary is ≈ 0.15 inside Whitney's line: a 36-gon wall and soft contact), wedging only above the boundary (μ 0.8 at θ₀ 2.0° inserts, μ 0.3 at θ₀ 4.5° jams instead), the vision anchor (0.016 mm with one hole, perturbed to 0.47 mm by the decoy — stated honestly), and the recorded run. Honestly: no VLM baseline is built (nothing is lined up against something that does not exist). The 5/5 is one condition per class and is not comparable with the paper's real-robot success rate. The "vision signature" is the hover-time wrist RGB-D anchor plus encoder integration (the tip is invisible once inside the hole). The jam test is valid only while stalled with F_z ≥ 1 N (while moving the ratios are ill-conditioned and the margin reaches −1.6 although the peg advances). A +1.6 mm shift stalls at the force cap with the ratio inside — unknown, and the table stays silent. The recovery primitives are scripted (lifts of 4 / 6 / 10 mm, ≤ 6 iterations, ≤ 3 recoveries per run). Only one jam direction (the opposite side slides in). The compliant-support condition for avoiding wedging (S = L_g/(L_g² + K_θ/K_x)) is not used because the inequality cannot be read from the slides. No tactile sensing (tacslip).*

[![注入した失敗 6 クラスと表の分類(真値署名): 対角 6 / 6。右列は視覚のずれ(構え時の RGB-D + エンコーダ積分)で作った署名の正答 6 / 6。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_failure_recovery/02_pegfail_failure_confusion_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_failure_recovery/02_pegfail_failure_confusion.png)

*↑ The measurement ―― 注入した失敗 6 クラスと表の分類(真値署名): 対角 6 / 6。右列は視覚のずれ(構え時の RGB-D + エンコーダ積分)で作った署名の正答 6 / 6。 (figure labels are in Japanese; the numbers are the same)*

[![手首ばねのたわみから推定した先端の力の比。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_failure_recovery/03_pegfail_jamming_diagram_measured_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_failure_recovery/03_pegfail_jamming_diagram_measured.png)

*↑ 手首ばねのたわみから推定した先端の力の比。*

[![μ = 0.8・θ₀ = 4.5° のくさび。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_failure_recovery/04_pegfail_depth_vs_tick_stall_detection_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_failure_recovery/04_pegfail_depth_vs_tick_stall_detection.png)

*↑ μ = 0.8・θ₀ = 4.5° のくさび。*

[![くさびは力を抜いても引いても動かない(深さ 5.90 → 5.90 mm、内部圧縮)、詰まりは横の力を抜くと自重で進み(6.25 → 7.21 mm)引けば戻る(5.30 mm、力の向きの問題)—— ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_failure_recovery/06_pegfail_release_probe_wedge_vs_jam_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_failure_recovery/06_pegfail_release_probe_wedge_vs_jam.png)

*↑ くさびは力を抜いても引いても動かない(深さ 5.90 → 5.90 mm、内部圧縮)、詰まりは横の力を抜くと自重で進み(6.25 → 7.21 mm)引けば戻る(5.30 mm、力の向きの問題)—— Whitney の区別を MuJoCo で。*

[![手首カメラ(640×480、0.1 s ごと、48 コマ): 降下 → くさびで止まる → 'detected: wedging' → 退避して傾きを戻す → 再降下で成功。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_failure_recovery/05_pegfail_wrist_camera_wedging_detect_recover.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_failure_recovery/05_pegfail_wrist_camera_wedging_detect_recover.gif)

*↑ The animation ―― 手首カメラ(640×480、0.1 s ごと、48 コマ): 降下 → くさびで止まる → 'detected: wedging' → 退避して傾きを戻す → 再降下で成功。*

```
py -3.11 examples/poc_peg_failure_recovery.py
```

Source: [examples/poc_peg_failure_recovery.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_peg_failure_recovery.py)

This run produced **6 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_peg_failure_recovery)

Ops used (notes): [`chamfer_capture`](https://furuse.work/ops/drive/pegsim/chamfer_capture.html) · [`failure_confusion`](https://furuse.work/ops/drive/pegfail/failure_confusion.html) · [`insertion_episode_summary`](https://furuse.work/ops/drive/pegfail/insertion_episode_summary.html) · [`insertion_failure_classify`](https://furuse.work/ops/drive/pegfail/insertion_failure_classify.html) · [`insertion_failure_presets`](https://furuse.work/ops/drive/pegfail/insertion_failure_presets.html) · [`insertion_failure_table`](https://furuse.work/ops/drive/pegfail/insertion_failure_table.html) · [`insertion_failure_validate`](https://furuse.work/ops/drive/pegfail/insertion_failure_validate.html) · [`insertion_recovery_primitive`](https://furuse.work/ops/drive/pegfail/insertion_recovery_primitive.html) · [`insertion_signature`](https://furuse.work/ops/drive/pegfail/insertion_signature.html) · [`insertion_stall_detect`](https://furuse.work/ops/drive/pegfail/insertion_stall_detect.html) · [`jamming_diagram`](https://furuse.work/ops/drive/pegsim/jamming_diagram.html) · [`jamming_force_check`](https://furuse.work/ops/drive/pegfail/jamming_force_check.html) · [`jamming_parallelogram_planar`](https://furuse.work/ops/drive/pegfail/jamming_parallelogram_planar.html) · [`peg_offset_from_rgbd`](https://furuse.work/ops/drive/pegsim/peg_offset_from_rgbd.html) · [`peg_params`](https://furuse.work/ops/drive/pegsim/peg_params.html) · [`peg_synthetic_rgbd`](https://furuse.work/ops/drive/pegsim/peg_synthetic_rgbd.html) · [`pegfail_scene_mjcf`](https://furuse.work/ops/drive/pegfail/pegfail_scene_mjcf.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`tip_force_ratios`](https://furuse.work/ops/drive/pegfail/tip_force_ratios.html) · [`vision_boundary_flip`](https://furuse.work/ops/drive/pegfail/vision_boundary_flip.html) · [`wedging_risk`](https://furuse.work/ops/drive/pegfail/wedging_risk.html) · [`whitney_clearance`](https://furuse.work/ops/drive/pegsim/whitney_clearance.html) · [`wrist_load_from_deflection`](https://furuse.work/ops/drive/pegfail/wrist_load_from_deflection.html)

## No.2026.203 —— Calibrating a Vision-Based Tactile Sensor's Illumination on Real Calibration Spheres, with a Gradient LUT as the Second Implementation — the Ball Radius and Hand-Marked Circles as the Truth

[![Calibrating a Vision-Based Tactile Sensor's Illumination on Real Calibration Spheres, with a Gradient LUT as the Second Implementation — the Ball Radius and Hand-Marked Circles as the Truth](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacscalib_sphere_lut/01_tacscalib_synthetic_error_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacscalib_sphere_lut/01_tacscalib_synthetic_error_maps.png)

*↑ **Calibrating a Vision-Based Tactile Sensor's Illumination on Real Calibration Spheres, with a Gradient LUT as the Second Implementation — the Ball Radius and Hand-Marked Circles as the Truth** ―― The physics-simulation × Fullseye series continues from tacsim (elastic membrane + camera, 2026.196). tacsim synthesised its own three-colour Lambertian images and inverted them itself — the truth and the subject were both home-made. This exhibit brings in real images (the calibration packs published under the MIT licence by the authors of arXiv:2109.04027), calibrates the forward map (normal → colour) and solves the inverse along two independent routes: a linear 12-parameter illumination I_c = a_c + l_c · n (inverted by photometric_stereo = the subject) and an example-based gradient LUT (tilt θ and azimuth φ cut into 125 × 125 bins, mean colour per bin, also a version with a quadratic in position). New module tacscalib, 10 ops, numpy only. Two truths come from outside: the known ball radius (inside the contact circle the membrane follows the sphere, so the normal is the closed form n = (−x, −y, √(R² − r²))/R) and hand-marked contact circles (integer pixels, radii in 2 px steps = a weak truth). R enters both calibration and evaluation, so the gates test whether the calibration generalises to other images, not R itself — calibrate on the 24 even frames, measure on the 24 odd ones. ★A dead band in the prototype was fixed: fitting the position quadratic only to well-populated bins dropped every low-tilt bin, and pixels with tilt 0–15° snapped to 0 or 15° (barely visible in the median angular error; only the profile plot showed it). Sparse bins now borrow the position terms of the angularly nearest polynomial bin and fit only their own constant — on the real hold-out, the median |Δθ| for true tilt < 15° drops from 4.84° to 1.89°. The price: the tilt floor on flat ground rises from 0.4° to 3.3° (the colour difference between a small tilt and flat sinks into the 3.6 DN background noise = a resolution limit). Single-row bins carry pure noise and bias the depth by +18.5 %; a minimum of 10 rows gives +6.0 %. ★The inverse lookup rewrites the distance as one feature inner product (|k|² = AᵀQA) and runs coarse → fine (pick the top two 3 × 3-bin blocks by their representatives): the same bin as brute force for 90.0 % of pixels, median angular error within 0.10°, 2.4× faster. 9 gates (synthetic, 1.3 s) plus 10 with --full (real data, 42 s): illumination round trip 4.8e-15, quantisation floor 0.430°, with ±40 % position gain 0.726° with position terms vs 4.600° without, dead band 13.24° → 0.58°, coefficients mapped in closed form to an external quadratic-LUT format agree to 7.1e-15 DN; real hold-out of 24 frames: RGB residual linear 7.92 DN (72-parameter position model 4.63, background noise 3.60), median angular error linear 10.71° / LUT without position 8.58° / LUT with position 4.17° / the external pre-calibrated LUT 3.57°*, contact_radius_ring (the subject) radius −0.25 px (−12.9 px with its default search radius), depth +4.7 % against 595 µm with a profile RMS of 7.1 µm, 7.59 / 8.83 / 3.70° for the position LUT with 1 / 4 / 24 calibration frames, and the second sensor's linear residual 30.8 DN = 3.9× the first. Figures: a synthetic press with the error maps of three routes, a GIF circling the light (reconstruction vs the true spherical cap), the dead band before and after; with --full: a real frame → reconstruction → true cap, a real-data GIF, profiles, residual maps, error maps, the sensor-plane error map, the position scatter, the calibration-count curve and the radial tilt. All at 1:1. Honestly: there is no truth for force or indentation depth. Angular errors are for the nearest-bin LUT (no interpolation). *The external LUT was built from the same 48 frames, so it is a reference, not a hold-out. The second pack has no primary source for ball diameter or pixel pitch (only a code comment giving 0.0266 mm/px), so only radius-independent quantities (the ratio of linear residuals) are gated and the angular errors are ranked only. The position LUT breaks in the image corners (extrapolation where few calibration balls landed). Trap we hit: with all centres on integer pixels the synthetic data never produces sparse bins, so the dead band is invisible in principle (reproduced with sub-pixel offsets). Two issues in existing ops (contact_radius_ring's default search radius cuts the circle at a quarter of the window; photometric.angular_error_deg's 1.15e-4° floor) are left unfixed.*

[![位置つき LUT の法線を Frankot–Chellappa で積分した面に光を 1 周させる(中央)、右は真の球冠。等倍 89×89、24 コマ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacscalib_sphere_lut/02_tacscalib_synthetic_relight.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacscalib_sphere_lut/02_tacscalib_synthetic_relight.gif)

*↑ The measurement ―― 位置つき LUT の法線を Frankot–Chellappa で積分した面に光を 1 周させる(中央)、右は真の球冠。等倍 89×89、24 コマ。 (figure labels are in Japanese; the numbers are the same)*

[![合成の 1 球、真の傾き < 15° の画素。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacscalib_sphere_lut/03_tacscalib_deadband_before_after_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacscalib_sphere_lut/03_tacscalib_deadband_before_after.png)

*↑ 合成の 1 球、真の傾き < 15° の画素。*

[![法線の半径スロープを方位平均して 1D 積分した断面と真の球冠(破線)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacscalib_sphere_lut/06_tacscalib_height_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacscalib_sphere_lut/06_tacscalib_height_profile.png)

*↑ 法線の半径スロープを方位平均して 1D 積分した断面と真の球冠(破線)。*

[![法線の角誤差 0〜20°(同じ hold-out 1 枚、等倍)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacscalib_sphere_lut/08_tacscalib_angle_error_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacscalib_sphere_lut/08_tacscalib_angle_error_maps.png)

*↑ 法線の角誤差 0〜20°(同じ hold-out 1 枚、等倍)。*

[![接触中心の画像中心からの距離 vs 角誤差の中央値(hold-out 各 1 点)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacscalib_sphere_lut/10_tacscalib_position_scatter_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacscalib_sphere_lut/10_tacscalib_position_scatter.png)

*↑ 接触中心の画像中心からの距離 vs 角誤差の中央値(hold-out 各 1 点)。*

[![実機の 1 枚から復元した面に光を 1 周させる(中央)、右は真の球冠。等倍 201×201、24 コマ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacscalib_sphere_lut/05_tacscalib_real_relight.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacscalib_sphere_lut/05_tacscalib_real_relight.gif)

*↑ The animation ―― 実機の 1 枚から復元した面に光を 1 周させる(中央)、右は真の球冠。等倍 201×201、24 コマ。*

```
py -3.11 examples/poc_tacscalib_sphere_lut.py
```

Source: [examples/poc_tacscalib_sphere_lut.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_tacscalib_sphere_lut.py)

This run produced **12 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_tacscalib_sphere_lut)

Ops used (notes): [`calib_pack_load`](https://furuse.work/ops/drive/tacscalib/calib_pack_load.html) · [`contact_radius_ring`](https://furuse.work/ops/drive/tacsim/contact_radius_ring.html) · [`field_position_sweep`](https://furuse.work/ops/drive/tacscalib/field_position_sweep.html) · [`gradient_lut_build`](https://furuse.work/ops/drive/tacscalib/gradient_lut_build.html) · [`gradient_lut_invert`](https://furuse.work/ops/drive/tacscalib/gradient_lut_invert.html) · [`integrate_normals`](https://furuse.work/ops/3d/photometric/integrate_normals.html) · [`invert`](https://furuse.work/ops/2d/gray/invert.html) · [`lights_fit_from_sphere`](https://furuse.work/ops/drive/tacscalib/lights_fit_from_sphere.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`membrane_predict_rgb`](https://furuse.work/ops/drive/tacscalib/membrane_predict_rgb.html) · [`normal_error_map`](https://furuse.work/ops/drive/tacscalib/normal_error_map.html) · [`normals_to_angles`](https://furuse.work/ops/reprconv/direction/normals_to_angles.html) · [`poly_lut_invert`](https://furuse.work/ops/drive/tacscalib/poly_lut_invert.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`sphere_cap_height`](https://furuse.work/ops/drive/tacscalib/sphere_cap_height.html) · [`sphere_normals_known`](https://furuse.work/ops/drive/tacscalib/sphere_normals_known.html) · [`surface_normals`](https://furuse.work/ops/3d/photometric/surface_normals.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html)

## No.2026.204 —— Reading Peg-in-Hole Insertion through Two Fingertip Membranes — Contact Wrench, Whitney's Contact States, Wall Friction and Wrist Stiffness from Shear Images; at the Wedging Boundary the Wrench Alone Is Blind

[![Reading Peg-in-Hole Insertion through Two Fingertip Membranes — Contact Wrench, Whitney's Contact States, Wall Friction and Wrist Stiffness from Shear Images; at the Wedging Boundary the Wrench Alone Is Blind](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_insertion_tactile/12_pegtactile_wrist_stiffness_from_images_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_insertion_tactile/12_pegtactile_wrist_stiffness_from_images.png)

*↑ **Reading Peg-in-Hole Insertion through Two Fingertip Membranes — Contact Wrench, Whitney's Contact States, Wall Friction and Wrist Stiffness from Shear Images; at the Wedging Boundary the Wrench Alone Is Blind** ―― The capstone of the physics-simulation × Fullseye series (pegsim 2026.195, pegfail 2026.201) and of the three vision-based tactile exhibits (tacsim, tacslip, tactorque). Elastic membranes are mounted on the two fingertips; the contact wrench the peg receives from the hole is recovered from the two membrane images alone, and Whitney's contact states (none / chamfer / one point / two points, and wedging or jamming once stalled) are called by learning-free rules. In the same insertion the wrist stiffness k is identified from wrist-camera deflection × tactile force, and the symmetry of the peg shape (n-fold) and of the apparatus (two fingers are not rotationally symmetric) is measured by equivariance gates. New module pegtactile, 19 ops, plus 2 added to existing modules (tacsim.contact_radius_fit_pixelwise = contact radius without radial bins; tacslip.mindlin_fit_vector = a two-coefficient Mindlin fit for directed shear) and 4 mujoco facades. Ground truth comes from outside on four fronts. (1) The theorem: Whitney 1982 (paywalled and unread; the equations are from the author's own MIT OCW 2.875 Class 3 slides): the two-point depth l₂(θ) = (2R − r(cosθ + secθ))/tanθ and the wedging boundary θ = c/μ. (2) Contact-mechanics closed forms (Johnson 1985): Hertz, Cattaneo–Mindlin, Cerruti, no-slip torsion. (3) Group actions (rotate the shape or the scene and the answer rotates by the same amount). (4) MuJoCo's contact points and forces, the wrist force/torque sensor and the set wrist-spring values (--full). MuJoCo has no membrane, so the pad loads are a statics map that distributes the exposure-averaged contact wrench plus gravity to the two pads. ★The wedging boundary is the blind spot of a wrench-only rule: where the slope c/θ of the line from mouth to tip equals μ, the edge of the tip's friction cone passes through the mouth contact and a two-point wrench is indistinguishable from a single mouth contact (2 of 36 closed-form cases, θ 3°, μ 0.8). Adding Whitney's geometry (force two-point when depth ≥ W + l₂(θ)) gives 36/36. ★Rotating the scene by 90° moves the tilting moment from a shear couple to pad torsion: reading torsion keeps the agreement at 97.6 → 96.8 %; dropping it gives 47.6 %. Figures: the two membrane images and their readings, a GIF of Whitney's closed-form insertion read through the membranes, the radial-bin trap, the wrench-only blind spot, shape orientation (Fourier phase vs second moments); with --full: an insertion GIF (hole cross-section, wrist camera, both membranes, state band), time series of four runs, wrist stiffness F = kΔx, the two-point onset, and the agreement after a 90° rotation. 10 gates (numpy, 2.4 s) plus 12 with --full (3 heavy numpy + 9 MuJoCo): statics round trip 4.4e-16; membrane round trip P 0.011 %, q 2.8 mN (4.4 mN over 20 cases), torsion 0.010 mN·m, direction 0.12°; false shear at zero load 12.1 mN on a regular marker grid → 0.7 mN with jitter; slope error of P̂ 8.5 % with bins → 0.018 % per pixel; Whitney's 36 cases 34 with the wrench only → 36 with geometry; two-point μ within 0.0008 (normal force 0.6 N); n-fold symmetry 0/3/4/6/1; Fourier-phase orientation 0.001–0.018° (keyed 0.59°) vs second moments off by 10–59°; wrist RGB-D equivariance 3.2 µm (0.000 µm under the mirror); MuJoCo: map vs force sensor 0.41 mN and 0.023 mN·m, tactile wrench |ΔF| median 2.7 / max 6.8 mN, state agreement 97.5 % (98.0 % with the true wrench), two-point onset within 0.04 mm of the closed form, wall μ 0.292 from one-point and 0.2998 from two-point sliding (set 0.3), wedging / jamming 2/2, wrist camera 1.2 µm, k_t 599.9–601.1 N/m (set 600), k_r 1.496–1.512 N·m/rad (set 1.5). Honestly: MuJoCo has no membrane, so the pad loads come from a statics map (symmetric left/right split assumed, peg inertia ignored — 11.7 mN vertical lies outside it). Synthesis and inversion use the same closed-form family, so errors of the membrane model (finite thickness, large deformation) are invisible to these gates (tacslip's finite-element comparison covers that). k is identified only in two-point intervals. Each condition is run once. There is no MuJoCo insertion of square or hexagonal pegs (symmetry is gated on the perception ops only). Traps we hit: pixel locking of a regular marker grid, radial-bin contact radii that skew the slope of P̂ by 40 % and k by +3.7 % through the two-pad difference, instantaneous contact forces are impulses (averaged over the exposure), and without pruning the candidate points a two-point line of action reads as one point.*

[![Whitney の二点接触(θ 3°、μ 0.8 = くさびの境目の近く)を 2 本の指の膜で見た像(等倍 256 px = 16 mm)。矢印はマーカーの変位 ×12、円は読んだ接触円。真値の荷重 L: P 4.093 N・q (-0.0](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_insertion_tactile/01_pegtactile_two_membranes_read_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_insertion_tactile/01_pegtactile_two_membranes_read.png)

*↑ The measurement ―― Whitney の二点接触(θ 3°、μ 0.8 = くさびの境目の近く)を 2 本の指の膜で見た像(等倍 256 px = 16 mm)。矢印はマーカーの変位 ×12、円は読んだ接触円。真値の荷重 L: P 4.093 N・q (-0.000, 0.344) N、R: P 3.907 N・q (-0.000, 0.398) N。左右でせん断の v 成分が逆向き = モーメントは偶力で運ばれる。 (figure labels are in Japanese; the numbers are the same)*

[![同じ二点接触の接触レンチ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_insertion_tactile/02_pegtactile_wrench_truth_vs_membranes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_insertion_tactile/02_pegtactile_wrench_truth_vs_membranes.png)

*↑ 同じ二点接触の接触レンチ。*

[![二点接触(閉形式)をレンチだけの規則に通すと、口と先端を結ぶ線の傾き c/θ が μ に等しい線(破線、Whitney のくさびの境目そのもの)の近くでだけ口の一点と読む(12 組中 2 組)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_insertion_tactile/05_pegtactile_wrench_only_blind_band_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_insertion_tactile/05_pegtactile_wrench_only_blind_band.png)

*↑ 二点接触(閉形式)をレンチだけの規則に通すと、口と先端を結ぶ線の傾き c/θ が μ に等しい線(破線、Whitney のくさびの境目そのもの)の近くでだけ口の一点と読む(12 組中 2 組)。*

[![走行 B の接触力の大きさと把持点まわりの M_y(破線 = MuJoCo の露光平均、実線 = 膜 2 枚から)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_insertion_tactile/09_pegtactile_timeline_run_B_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_insertion_tactile/09_pegtactile_timeline_run_B.png)

*↑ 走行 B の接触力の大きさと把持点まわりの M_y(破線 = MuJoCo の露光平均、実線 = 膜 2 枚から)。*

[![走行 D の接触力の大きさと把持点まわりの M_y(破線 = MuJoCo の露光平均、実線 = 膜 2 枚から)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_insertion_tactile/11_pegtactile_timeline_run_D_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_insertion_tactile/11_pegtactile_timeline_run_D.png)

*↑ 走行 D の接触力の大きさと把持点まわりの M_y(破線 = MuJoCo の露光平均、実線 = 膜 2 枚から)。*

[![Whitney の閉形式の挿入(θ 3°、μ 0.3)を膜 2 枚で読む動く図: 先端が壁に一点で触れたまま深くなり、深さ W + l₂(θ) = 8.63 mm で胴が口の縁にも触れて二点へ。上の文字の色 = 膜からの判定が真値と一致(全](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_insertion_tactile/03_pegtactile_whitney_insertion_through_membranes.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_insertion_tactile/03_pegtactile_whitney_insertion_through_membranes.gif)

*↑ The animation ―― Whitney の閉形式の挿入(θ 3°、μ 0.3)を膜 2 枚で読む動く図: 先端が壁に一点で触れたまま深くなり、深さ W + l₂(θ) = 8.63 mm で胴が口の縁にも触れて二点へ。上の文字の色 = 膜からの判定が真値と一致(全 14 コマ)。*

[![挿入の動く図(θ 3°、横ずれ 0.6 mm、48 コマ = 0.08 s ごと): 左 = 穴の断面(板を半透明、緑の円 = MuJoCo の接触点、大きさ ∝ 力、桃の × = 膜 2 枚から読んだ接触点)、中 = 手首カメラ、右 = ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_insertion_tactile/07_pegtactile_insertion_section_wrist_membranes.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_insertion_tactile/07_pegtactile_insertion_section_wrist_membranes.gif)

*↑ The animation ―― 挿入の動く図(θ 3°、横ずれ 0.6 mm、48 コマ = 0.08 s ごと): 左 = 穴の断面(板を半透明、緑の円 = MuJoCo の接触点、大きさ ∝ 力、桃の × = 膜 2 枚から読んだ接触点)、中 = 手首カメラ、右 = 2 本の指の膜(矢印 ×12)。下の帯 = 状態(灰 無接触・青 面取り・橙 一点・赤 二点)の MuJoCo と触覚。*

```
py -3.11 examples/poc_peg_insertion_tactile.py
```

Source: [examples/poc_peg_insertion_tactile.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_peg_insertion_tactile.py)

This run produced **14 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_peg_insertion_tactile)

Ops used (notes): [`arrow`](https://furuse.work/ops/annotate/pointer/arrow.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`contact_radius_fit`](https://furuse.work/ops/drive/tacsim/contact_radius_fit.html) · [`contact_radius_fit_pixelwise`](https://furuse.work/ops/drive/tacsim/contact_radius_fit_pixelwise.html) · [`contact_state_from_wrench`](https://furuse.work/ops/drive/pegtactile/contact_state_from_wrench.html) · [`ellipse`](https://furuse.work/ops/annotate/shape/ellipse.html) · [`equivariance_check`](https://furuse.work/ops/drive/pegtactile/equivariance_check.html) · [`friction_from_single_contact`](https://furuse.work/ops/drive/pegtactile/friction_from_single_contact.html) · [`hertz_force`](https://furuse.work/ops/drive/tacsim/hertz_force.html) · [`membrane_recover`](https://furuse.work/ops/drive/tacsim/membrane_recover.html) · [`pad_context`](https://furuse.work/ops/drive/pegtactile/pad_context.html) · [`pad_loads_to_peg_wrench`](https://furuse.work/ops/drive/pegtactile/pad_loads_to_peg_wrench.html) · [`pad_params`](https://furuse.work/ops/drive/pegtactile/pad_params.html) · [`pad_tactile_frame`](https://furuse.work/ops/drive/pegtactile/pad_tactile_frame.html) · [`pad_tactile_read`](https://furuse.work/ops/drive/pegtactile/pad_tactile_read.html) · [`peg_offset_from_rgbd`](https://furuse.work/ops/drive/pegsim/peg_offset_from_rgbd.html) · [`peg_params`](https://furuse.work/ops/drive/pegsim/peg_params.html) · [`peg_synthetic_rgbd`](https://furuse.work/ops/drive/pegsim/peg_synthetic_rgbd.html) · [`peg_wrench_to_pad_loads`](https://furuse.work/ops/drive/pegtactile/peg_wrench_to_pad_loads.html) · [`project_points`](https://furuse.work/ops/3d/render/project_points.html) · [`stall_verdict`](https://furuse.work/ops/drive/pegtactile/stall_verdict.html) · [`symmetric_peg_shape`](https://furuse.work/ops/drive/pegtactile/symmetric_peg_shape.html) · [`symmetry_order_contour`](https://furuse.work/ops/drive/pegtactile/symmetry_order_contour.html) … (+7)

## No.2026.208 —— Cutting a Peg's Rotation Search to 1/n with Its Symmetry — Inserting Square, Hexagonal and Keyed Pegs Checked by Group Identities, Closed Forms and MuJoCo; Friction Shrinks the Hexagon's Chamfer Window from 20.9° to 6.8°

[![Cutting a Peg's Rotation Search to 1/n with Its Symmetry — Inserting Square, Hexagonal and Keyed Pegs Checked by Group Identities, Closed Forms and MuJoCo; Friction Shrinks the Hexagon's Chamfer Window from 20.9° to 6.8°](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_symmetry_search/01_pegsym_rotating_shapes_read_mod_2pi_over_n.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_symmetry_search/01_pegsym_rotating_shapes_read_mod_2pi_over_n.gif)

*↑ **Cutting a Peg's Rotation Search to 1/n with Its Symmetry — Inserting Square, Hexagonal and Keyed Pegs Checked by Group Identities, Closed Forms and MuJoCo; Friction Shrinks the Hexagon's Chamfer Window from 20.9° to 6.8°** ―― The physics-simulation × Fullseye series continues (soft-wrist peg insertion, failure classification, two-finger membranes). The subject is research that uses symmetry for learning (Symmetry-aware RL, ICRA 2024, arXiv:2402.18002; the abstract was read as the primary source); here the group identities themselves are the gates, building the parts that remain without learning. Regular n-gon prisms (n = 3, 4, 6) and a keyed square with one corner cut by 1.8 mm (symmetry n = 1) are inserted into holes of the same shape offset outward by 0.2 mm (45° chamfer, 0.5 mm). New module pegsym, 15 ops plus 6 mujoco facades. (1) Reading orientation: images are rectified to a top view of the plane (the hole mouth from the wrist camera, the peg end face from an upward camera), and the complex Fourier phase of the contour gives the angle modulo 2π/n. Second moments are isotropic for n ≥ 3 and carry no orientation (a trap). Synthetic equivariance over 40 angles per period: 0.054° for regular polygons, 0.19° keyed; from MuJoCo images the relative angle is within 0.05° (regular) and 0.70° keyed (bias from a hole that is not similar). (2) Rotation window (derived): φ = π/n − arccos((A + δ + W)cos(π/n)/A) (written with atan2) matches a linear program with free translation (second implementation) to 2.8e-11 rad; windows are 4.75° triangle, 8.72° square, 20.85° hexagon. (3) The friction limit (derived, found in MuJoCo): only the hexagon captured just 7.25° in MuJoCo. For a vertex resting on the mouth to slide down the chamfer the peg must turn, and the moment balance about the axis says it turns only if sin²β > (√(1 + 8μ²) − 1)/2. Within 0.5° of MuJoCo at six points μ = 0–0.5 (μ = 0.3: closed form 6.76°, MuJoCo 7.25°). (4) Number of tries: the closed-form expectation of sweeping one period with steps at most twice the window agrees within 3 % with an error grid judged by a linear program on the mouth (triangle 6.97 / 6.96, square 3.36 / 3.29, hexagon 1.31 / 1.29, keyed 10.98 / 11.02). Blind searches in MuJoCo (12 hole orientations × 4 shapes) match the predicted tries in 47 / 48, with means of 3.50 (square) and 11.00 (keyed). Using the image reading as the estimate inserts 16 / 16 on the first try; rebuilding the hole rotated by an extra 2πk/n gives the same tries (6 / 6). (5) Two-point contact of polygons: no closed form was found, so an exact solution was built from a linear program on convex-hull vertices plus bisection. A square tilted about an axis parallel to a face matches Whitney's cylinder formula to 3.4e-11 m and the small-angle limit of eq. (2.28) of Goli et al. 2024 (R. Soc. Open Sci.) to 1.00000; a second implementation with MuJoCo's distance function agrees within 6.5 µm of lateral clearance. (6) Spiral: at first the search skipped turns near the centre and left 64 / 11,285 holes in the cover → arc length is now accumulated on a fine grid. With steps meeting the sufficient condition there are no holes, and the expected count is within 3.6 % of the swept-area approximation. Figures: a GIF of three rotating shapes and their readings, tries vs symmetry, window margin, two-point depth vs tilt direction, spiral cover; with --full: a GIF of the MuJoCo blind search, window vs friction, and the rectified wrist and upward views. 10 gates (default, 1.8 s) plus 7 with --full (42 s with figures). Honestly: the peg orientation is read by a fixed upward camera mid-process (the wrist camera alone cannot see the end face). The friction limit is derived for a 45° chamfer, quasi-statics and a weak spring about the axis; for the square at μ ≥ 0.5 MuJoCo is 0.7° wider (shown as a breakdown, not gated). Sturges's square-peg wedging was not read. The nested count for searching translation and rotation together is an independence approximation and is not gated.*

[![線 = 窓 5° を共通にした時の閉形式 E(n)、破線 = 対称を知らない探索の E を n で割ったもの。点 = この装置(窓は形ごとに違う)の閉形式と、一様な誤差の格子で口への線形計画が判定した平均。キー付きは n = 1。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_symmetry_search/02_pegsym_expected_tries_vs_symmetry_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_symmetry_search/02_pegsym_expected_tries_vs_symmetry.png)

*↑ The measurement ―― 線 = 窓 5° を共通にした時の閉形式 E(n)、破線 = 対称を知らない探索の E を n で割ったもの。点 = この装置(窓は形ごとに違う)の閉形式と、一様な誤差の格子で口への線形計画が判定した平均。キー付きは n = 1。 (figure labels are in Japanese; the numbers are the same)*

[![平行移動も自由にした時の口の中の最良の余裕(線形計画)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_symmetry_search/03_pegsym_rotation_window_margin_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_symmetry_search/03_pegsym_rotation_window_margin.png)

*↑ 平行移動も自由にした時の口の中の最良の余裕(線形計画)。*

[![傾き 3° の二点接触の深さ(厳密、凸包の頂点の線形計画)を内接円の円柱の Whitney の式で割ったもの。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_symmetry_search/04_pegsym_two_point_depth_vs_tilt_direction_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_symmetry_search/04_pegsym_two_point_depth_vs_tilt_direction.png)

*↑ 傾き 3° の二点接触の深さ(厳密、凸包の頂点の線形計画)を内接円の円柱の Whitney の式で割ったもの。*

[![Archimedes のらせん。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_symmetry_search/05_pegsym_spiral_search_cover_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_symmetry_search/05_pegsym_spiral_search_cover.png)

*↑ Archimedes のらせん。*

[![面取りが回して入れる最大の向きの誤差。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_symmetry_search/07_pegsym_capture_window_vs_friction_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_symmetry_search/07_pegsym_capture_window_vs_friction.png)

*↑ 面取りが回して入れる最大の向きの誤差。*

[![正方形のペグの盲目の回転探索(MuJoCo、斜め上の固定カメラ)。候補は 90° の 1 周期を 6 等分(刻み 15.0°、面取りの窓 ±8.72°)。下の帯 = 試行(赤 = 面取りか襟で止まった、緑 = 入った)。6 回目で入り、予言](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_symmetry_search/06_pegsym_mujoco_blind_rotation_search.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_peg_symmetry_search/06_pegsym_mujoco_blind_rotation_search.gif)

*↑ The animation ―― 正方形のペグの盲目の回転探索(MuJoCo、斜め上の固定カメラ)。候補は 90° の 1 周期を 6 等分(刻み 15.0°、面取りの窓 ±8.72°)。下の帯 = 試行(赤 = 面取りか襟で止まった、緑 = 入った)。6 回目で入り、予言も 6 回。*

```
py -3.11 examples/poc_peg_symmetry_search.py
```

Source: [examples/poc_peg_symmetry_search.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_peg_symmetry_search.py)

This run produced **8 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_peg_symmetry_search)

Ops used (notes): [`pegsym_scene_mjcf`](https://furuse.work/ops/drive/pegsym/pegsym_scene_mjcf.html) · [`plane_topview`](https://furuse.work/ops/drive/pegsym/plane_topview.html) · [`polygon_coverage_image`](https://furuse.work/ops/drive/pegsym/polygon_coverage_image.html) · [`polygon_fit_check`](https://furuse.work/ops/drive/pegsym/polygon_fit_check.html) · [`polygon_offset`](https://furuse.work/ops/drive/pegsym/polygon_offset.html) · [`polygon_peg`](https://furuse.work/ops/drive/pegsym/polygon_peg.html) · [`polygon_two_point_depth`](https://furuse.work/ops/drive/pegsym/polygon_two_point_depth.html) · [`polygon_yaw_read`](https://furuse.work/ops/drive/pegsym/polygon_yaw_read.html) · [`relative_yaw_from_images`](https://furuse.work/ops/drive/pegsym/relative_yaw_from_images.html) · [`rotation_search_plan`](https://furuse.work/ops/drive/pegsym/rotation_search_plan.html) · [`rotation_window`](https://furuse.work/ops/drive/pegsym/rotation_window.html) · [`search_expected_tries`](https://furuse.work/ops/drive/pegsym/search_expected_tries.html) · [`spiral_expected_tries`](https://furuse.work/ops/drive/pegsym/spiral_expected_tries.html) · [`spiral_search_points`](https://furuse.work/ops/drive/pegsym/spiral_search_points.html) · [`symmetry_fold`](https://furuse.work/ops/drive/pegsym/symmetry_fold.html)

## No.2026.133 —— Where Is the Public Camera Looking — The Orientation of a Fixed Camera Whose Only Published Fact Is Its Position, from the Picture Itself

[![Where Is the Public Camera Looking — The Orientation of a Fixed Camera Whose Only Published Fact Is Its Position, from the Picture Itself](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading/02_yaw_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading/02_yaw_sweep.gif)

*↑ **Where Is the Public Camera Looking — The Orientation of a Fixed Camera Whose Only Published Fact Is Its Position, from the Picture Itself** ―― Public fixed cameras (road, weather, tourism) publish their position but not their orientation, or only a coarse one (a road direction code, an id hash, a manual gizmo); without the orientation a frame cannot be placed on a map, a DEM or a 3-D city. The new geocam family (7 ops, numpy + scipy) recovers the (yaw, pitch, roll) of a camera at a known position from the picture itself, with no learning, from two independent cues that check each other. (1) Skyline: the 360-degree ridge rendered from a DEM at the camera position (dem_skyline, with earth curvature and refraction and the horizon dip as the floor outside the DEM) is matched against the sky/terrain boundary extracted by dynamic programming (skyline_extract, Lie et al. 2005); camera_orientation_from_skyline returns the whole residual curve over yaw and the margin to the runner-up valley. (2) Sun: the apparent sun position is a closed form of time and place (sun_position, NOAA, checked against equinox and solstice values); two or more saturated sun discs picked from time-stamped frames (sun_pixel_position, which refuses clouds and sky bands by their fill ratio) fix the rotation exactly as the SVD solution of Wahba's problem (camera_orientation_from_sun). On a synthetic camera with a known pose (synthetic DEM, sky, a cloud, a foreground pole, noise, known intrinsics) the skyline route errs by 0.11 / 0.06 / 0.06 deg, the sun route by 0.02 / 0.04 / 0.05 deg (6 frames; the morning and evening frame alone give 0.004 deg), and the two routes agree to 0.09 deg. Controls: a road-direction prior of the kind public metadata gives is off by 7.5 deg, and on a flat DEM the ridge is the same in every direction so the op returns ambiguous instead of being silently 137 deg wrong. Prior work: Lalonde et al. IJCV 2010 (sun and sky, 3 deg on 22 webcams) and Baatz et al. ECCV 2012 (skylines, the large-scale position-unknown version). Honest breakdown: synthetic only (real data - Fintraffic weather cameras + NLS elevation in Finland, Statens vegvesen + Kartverket DTM10 in Norway - is the next step and raw frames are never committed), the intrinsics K are required (an error in K turns into pitch and roll), skylines need mountains and the sun needs to be in the picture.*

[![the DEM ridge drawn at the estimated yaw / pitch / roll lies on the extracted skyline; errors 0.06 / 0.03 / 0.01 deg](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading/01_skyline_lock_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading/01_skyline_lock.png)

*↑ The measurement ―― the DEM ridge drawn at the estimated yaw / pitch / roll lies on the extracted skyline; errors 0.06 / 0.03 / 0.01 deg (figure labels are in Japanese; the numbers are the same)*

[![the op returns the whole residual curve so that the ambiguity is visible: a runner-up valley at 15 d](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading/03_yaw_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading/03_yaw_profile.png)

*↑ the op returns the whole residual curve so that the ambiguity is visible: a runner-up valley at 15 deg is 1.28 deg worse; the flat DEM curve is level*

[![the sun's path over the day where it is above the ridge (yellow, projected with the pose estimated f](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading/04_sun_track_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading/04_sun_track.png)

*↑ the sun's path over the day where it is above the ridge (yellow, projected with the pose estimated from the sun) and the 5 sun discs picked by sun_pix…*

[![both routes recover the pose to well under a degree and agree with each other; the public-metadata p](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading/05_numbers_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading/05_numbers.png)

*↑ both routes recover the pose to well under a degree and agree with each other; the public-metadata prior is off by ten degrees and the flat-ground cas…*

```
py -3.11 examples/poc_public_camera_heading.py
```

Source: [examples/poc_public_camera_heading.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_public_camera_heading.py)

This run produced **5 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_public_camera_heading)

Ops used (notes): [`camera_orientation_from_skyline`](https://furuse.work/ops/geocam/orientation/camera_orientation_from_skyline.html) · [`camera_orientation_from_sun`](https://furuse.work/ops/geocam/sun/camera_orientation_from_sun.html) · [`dem_skyline`](https://furuse.work/ops/geocam/skyline/dem_skyline.html) · [`project`](https://furuse.work/ops/3d/bundle_adjust/project.html) · [`render_skyline_view`](https://furuse.work/ops/geocam/skyline/render_skyline_view.html) · [`skyline_extract`](https://furuse.work/ops/geocam/skyline/skyline_extract.html) · [`sun_pixel_position`](https://furuse.work/ops/geocam/sun/sun_pixel_position.html) · [`sun_position`](https://furuse.work/ops/geocam/sun/sun_position.html)

## No.2026.134 —— Where Is the Public Camera Looking, for Real — Hunting the Sun in 807 Road Cameras, Fixing the Heading from One Sunset and Checking It Against the Road

[![Where Is the Public Camera Looking, for Real — Hunting the Sun in 807 Road Cameras, Fixing the Heading from One Sunset and Checking It Against the Road](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading_real/02_sunset_follow.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading_real/02_sunset_follow.gif)

*↑ **Where Is the Public Camera Looking, for Real — Hunting the Sun in 807 Road Cameras, Fixing the Heading from One Sunset and Checking It Against the Road** ―― The synthetic PoC (poc_public_camera_heading) got away with 'the sun is a small saturated disc'; real road cameras did not. Probing the 24 hours of 20-21 September from Finland's 807 Fintraffic weather cameras (CC BY 4.0, no key) at sun elevations of 2-12 degrees, the look-alone gate (sun_pixel_position) called station-name text, signs, white cars and lens droplets the sun (24/24 wrong on the first probe), the sun is not a disc but a bloom whose size depends on exposure and which the station-name band clips, and the cameras look down at the road with sky in the top third only. Two ops were added to geocam: sun_bloom_fit (a Kasa circle fitted to the unclipped rim of the largest saturated blob; the centroid sits 12 px off on average, away from the cut) and camera_orientation_from_sun_candidates (RANSAC over per-frame candidates for the one blob that moves at the sun's rate in a fixed camera, with road-camera priors |roll| <= 12 deg, pitch -40..0 deg, HFOV 25-120 deg rejecting unphysical hypotheses, the focal length searched at the same time, and no votes from below-horizon times). Over 807 stations x 24 h exactly one sunset could be tracked (E18, Hamina; official metadata says direction UNKNOWN): from 5 frames (15:01-16:01 UTC) yaw 267.9, pitch -4.6, roll 0.9 deg, f 1439 px (HFOV 48 deg), residual 0.34 deg. Independent check: the lane vanishing point (medoid over several daytime frames) turned into a world bearing with the same pose is 272.7 deg against 275.3 deg for the E18 segment in OpenStreetMap - 2.5 deg apart. The weak degrees of freedom are not hidden: under leave-one-out yaw moves 1.3 deg but roll 10 deg and f 2 % (the limit of a one-hour low-elevation arc). On the same frames the look-alone gate said 'sun' 22 times: 3 exact, 2 on the sun but off-centre, 17 something else. Raw frames are never committed; only the aggregate (times, circle fits, vanishing point, road bearing) ships. Sources: Fintraffic / Digitraffic (CC BY 4.0), OpenStreetMap (ODbL).*

[![the sunset seen by C0362200 (E18, Hamina, Finland; metadata says direction UNKNOWN): the sun's path for the evening draw](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading_real/01_sunset_track_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading_real/01_sunset_track.png)

*↑ The measurement ―― the sunset seen by C0362200 (E18, Hamina, Finland; metadata says direction UNKNOWN): the sun's path for the evening drawn from the fitted pose (magenta) and the 5 blooms fitted with a circle (cyan); yaw 267.9, pitch -4.6, roll 0.9, HFOV 48 (figure labels are in Japanese; the numbers are the same)*

[![what the look-alone detector (sun_pixel_position, built for synthetic discs) called the sun in the s](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading_real/03_naive_picks_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading_real/03_naive_picks.png)

*↑ what the look-alone detector (sun_pixel_position, built for synthetic discs) called the sun in the same camera: 22 picks, 3 exactly the sun, 2 on the…*

[![refit with each sun frame removed: yaw barely moves, roll and the focal length are the weak directio](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading_real/04_jackknife_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading_real/04_jackknife.png)

*↑ refit with each sun frame removed: yaw barely moves, roll and the focal length are the weak directions of a 1-hour low-elevation arc — this is why the…*

[![for blooms cut by the station-name band the centroid sits 12.4 px (mean) away from the circle fitted](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading_real/05_bloom_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading_real/05_bloom_bias.png)

*↑ for blooms cut by the station-name band the centroid sits 12.4 px (mean) away from the circle fitted to the unclipped rim; the fit uses the circle*

[![one camera out of 807 stations gave a sun track of 4 or more frames on 2026-09-20/21 (2 more had 3 f](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading_real/06_numbers_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading_real/06_numbers.png)

*↑ one camera out of 807 stations gave a sun track of 4 or more frames on 2026-09-20/21 (2 more had 3 frames and were left out); the vanishing point of i…*

```
py -3.11 examples/poc_public_camera_heading_real.py
```

Source: [examples/poc_public_camera_heading_real.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_public_camera_heading_real.py)

This run produced **6 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_public_camera_heading_real)

Ops used (notes): [`bloom`](https://furuse.work/ops/gfx2d/post/bloom.html) · [`camera_orientation_from_sun_candidates`](https://furuse.work/ops/geocam/sun/camera_orientation_from_sun_candidates.html) · [`ellipse`](https://furuse.work/ops/annotate/shape/ellipse.html) · [`project`](https://furuse.work/ops/3d/bundle_adjust/project.html) · [`sun_position`](https://furuse.work/ops/geocam/sun/sun_position.html)

### The Colour and Separation Wing — There Is No Method That Works, Only Conditions Under Which One Does

Estimating the illuminant to restore colour, peeling the layers of a painting with multiple wavelengths, separating specular reflection with polarisation. The 4 exhibits here synthesise linear radiance from known spectral reflectances, known illuminants and the Fresnel equations, then compare the separation against that truth.

The conclusion in every case was that the failure axes are orthogonal. Max-RGB is best when a white patch is present and gets 8x worse when the single brightest patch is removed; grey-world shrugs off saturation but loses once chromatic content exceeds 20 %; under a reference illuminant every method loses to doing nothing; adding bands does not win, adding near-infrared does.

The shared warning is to convert to linear radiance before calling anything. Pass sRGB-gamma values and no exception is raised; the separation simply degrades in silence. Failure without an exception is the most common pattern in the whole museum.

## No.2026.032 —— Peeling Layers With Many Wavelengths — Underdrawing, Ground, Glaze and Fading, Truth in Hand

[![Peeling Layers With Many Wavelengths — Underdrawing, Ground, Glaze and Fading, Truth in Hand](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/01_per_field_auc_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/01_per_field_auc.png)

*↑ **Peeling Layers With Many Wavelengths — Underdrawing, Ground, Glaze and Fading, Truth in Hand** ―― A spectral cube of ground, underdrawing, glaze and fading stacked in layers, then unmixed. Splitting the visible range into 16 bands does no better than RGB (recall 0.118 versus 0.119); what won was adding near-infrared. The same detector scores an AUC of 1.000 on ultramarine, 0.630 on azurite and 0.013 on losses — averaged, all of that vanishes. Restoring the unfaded colour barely beat the null, ΔE00 16.79 → 16.46.*

[![近赤外の差分は剥落部(楕円)で消え、近赤外 1 枚は面ごとに水準が違う。塗り分けは 1–99 分位でクリップした表示のみ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/02_detector_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/02_detector_maps.png)

*↑ The measurement ―― 近赤外の差分は剥落部(楕円)で消え、近赤外 1 枚は面ごとに水準が違う。塗り分けは 1–99 分位でクリップした表示のみ。 (figure labels are in Japanese; the numbers are the same)*

[![半分を割るのは tau 0.30–0.60 のあいだ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/03_thickness_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/03_thickness_cliff.png)

*↑ 半分を割るのは tau 0.30–0.60 のあいだ。*

[![ゼロ点の線より下に来た復元が 1 本も無い。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/04_restoration_vs_null_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/04_restoration_vs_null.png)

*↑ ゼロ点の線より下に来た復元が 1 本も無い。*

```
py -3.11 examples/poc_pigment_unmixing.py
```

Source: [examples/poc_pigment_unmixing.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pigment_unmixing.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_pigment_unmixing)

Ops used (notes): [`delta_e_map`](https://furuse.work/ops/imgmetrics/colordiff/delta_e_map.html) · [`linear_to_srgb`](https://furuse.work/ops/gfx2d/colorspace/linear_to_srgb.html) · [`spectrum_to_srgb`](https://furuse.work/ops/optics/appearance/spectrum_to_srgb.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html)

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

## No.2026.107 —— Separating a Real Immunostain by Colour — The Watchdog Was Blind to Exactly the Error It Should Catch

[![Separating a Real Immunostain by Colour — The Watchdog Was Blind to Exactly the Error It Should Catch](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stain_unmix/01_separation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stain_unmix/01_separation.png)

*↑ **Separating a Real Immunostain by Colour — The Watchdog Was Blind to Exactly the Error It Should Catch** ―― Colour deconvolution of a real immunostain (haematoxylin plus DAB). On synthetic data it separates perfectly — recompose one stain at unit concentration, solve again, and recovery is 1.0000 with 0.0000 crosstalk — so anyone looking only at synthesis concludes the problem is solved. On the real slide the haematoxylin concentration runs down to -4.446 and 11.51 % of pixels are negative, which is physically impossible: a negative concentration means the dye emitted light. Rotating the stain vectors within their plane by plus or minus twenty degrees moves the haematoxylin median from 0.0471 to 0.1348, a factor of 2.86, and DAB from 0.3590 to 0.1836 — while the residual channel, the quantity everyone reads as goodness of fit, stays at 0.0345 with a total spread of 3.3e-16. The geometry says why: the plane the two stains span is unchanged by a rotation inside it, so the component orthogonal to that plane cannot move. The negative fraction of the rotated stain is equally blind, fixed at 11.51 %, because its dual vector changes length but not direction. Only the partner moves, from 0.00 % at minus twenty degrees to 30.38 % at plus twenty: the watchdog has to watch the other stain, not itself, and being monotone it bounds the error from one side only. The round trip through recompose closes to 1e-06, which refutes none of this.*

[![H の中央値は 0.0656 -> 0.1348。残差の絶対中央値は 0.0345 のまま。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stain_unmix/02_blind_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stain_unmix/02_blind.png)

*↑ The measurement ―― H の中央値は 0.0656 -> 0.1348。残差の絶対中央値は 0.0345 のまま。 (figure labels are in Japanese; the numbers are the same)*

[![残差と自分の負率は平坦。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stain_unmix/03_diagnostics_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stain_unmix/03_diagnostics.png)

*↑ 残差と自分の負率は平坦。*

[![濃度は 2.9 倍動くのに残差は 4 桁目まで同じ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stain_unmix/04_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stain_unmix/04_sweep.png)

*↑ 濃度は 2.9 倍動くのに残差は 4 桁目まで同じ。*

```
py -3.11 examples/poc_real_stain_unmix.py
```

Source: [examples/poc_real_stain_unmix.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_stain_unmix.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_real_stain_unmix)



## No.2026.051 —— Colour Constancy (White Balance) — No Method Works, Only Conditions Do

[![Colour Constancy (White Balance) — No Method Works, Only Conditions Do](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/01_casts_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/01_casts.png)

*↑ **Colour Constancy (White Balance) — No Method Works, Only Conditions Do** ―― Linear RGB synthesised from 24 known spectral reflectances and known illuminants, with illuminant estimation scored by recovery angular error. Max-RGB is best at a median of 1.06 degrees over 11 illuminants, but removing the single brightest patch takes it to 8.45 degrees, and tripling exposure to saturate 43 % of pixels takes it to 13.61 degrees, identical to doing nothing. Even a diagonal correction with the true illuminant leaves a mean ΔE00 of 5.07 at 2500 K.*

[![灰色世界はゼロ点(何もしない)の線を 0.1〜0.2 の間で上抜けする = そこから先は回すだけ損。白パッチ法には崖が無い。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/02_bias_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/02_bias_cliff.png)

*↑ The measurement ―― 灰色世界はゼロ点(何もしない)の線を 0.1〜0.2 の間で上抜けする = そこから先は回すだけ損。白パッチ法には崖が無い。 (figure labels are in Japanese; the numbers are the same)*

[![露出 3 以上で白パッチ法の線が「何もしない」に重なる(max が (1,1,1) に張り付く)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/03_saturation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/03_saturation.png)

*↑ 露出 3 以上で白パッチ法の線が「何もしない」に重なる(max が (1,1,1) に張り付く)。*

[![最右列が推定誤差の実費。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/04_angle_to_de_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/04_angle_to_de.png)

*↑ 最右列が推定誤差の実費。*

```
py -3.11 examples/poc_white_balance.py
```

Source: [examples/poc_white_balance.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_white_balance.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_white_balance)

Ops used (notes): [`delta_e_map`](https://furuse.work/ops/imgmetrics/colordiff/delta_e_map.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`illuminant_from_dichromatic_planes`](https://furuse.work/ops/specular/dichromatic/illuminant_from_dichromatic_planes.html) · [`laplace`](https://furuse.work/ops/2d/edges/laplace.html) · [`linear_to_srgb`](https://furuse.work/ops/gfx2d/colorspace/linear_to_srgb.html) · [`mean_image`](https://furuse.work/ops/2d/smoothing/mean_image.html) · [`prewitt_amp`](https://furuse.work/ops/2d/edges/prewitt_amp.html) · [`roberts`](https://furuse.work/ops/2d/edges/roberts.html) · [`sobel_amp`](https://furuse.work/ops/2d/edges/sobel_amp.html) · [`spectrum_to_srgb`](https://furuse.work/ops/optics/appearance/spectrum_to_srgb.html)

### The Forensics and Documents Wing — One Successful Image Is Not Evidence

Forgery detection and document rectification. Both tend to be presented through 'the one image where it was found' or 'the one page that came out straight'. The 4 exhibits here fix the paste location and quality, the homography and the lighting themselves, then score with a per-pixel ROC and pixel-level geometric error.

The forgery exhibit is on the detection (defensive) side. Forgeries are generated only because scoring a detector needs ground truth, and the generator is kept to the crudest form possible. What the exhibit shows most strongly is the fact that works against the detector: one press of the save button weakens every cue.

The document exhibit puts a number on a hole: two functions with the same name and different models can be swapped without an exception, returning a plausible picture with the keystone still in it. Shadow removal has no free lunch; the flatter the paper, the more of the faint text disappears.

## No.2026.015 —— Straightening a Hand-Held Document Photo — Keystone Correction and Shadow Removal Against Ground Truth

[![Straightening a Hand-Held Document Photo — Keystone Correction and Shadow Removal Against Ground Truth](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/01_rectify_zero_points_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/01_rectify_zero_points.png)

*↑ **Straightening a Hand-Held Document Photo — Keystone Correction and Shadow Removal Against Ground Truth** ―― A document imaged under a known homography and lighting, rectified, and scored by corner and grid error in pixels. The estimate reaches a grid RMS of 1.070 px (doing nothing: 37.376 px), but swapping in the same-named function with a different model (affine) is 32x worse and raises no exception. Shadow strength 0.45 gives a corner RMS of 5.72 px; 0.55 gives 65.10 px — a cliff.*

[![平坦・薄字・誤検出なしを同時に満たす行は 1 つも無い。窓 9 が fs.op で届く上限、窓 61 は自前。図の階調は真値で 217 段。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/02_shadow_tradeoff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/02_shadow_tradeoff.png)

*↑ The measurement ―― 平坦・薄字・誤検出なしを同時に満たす行は 1 つも無い。窓 9 が fs.op で届く上限、窓 61 は自前。図の階調は真値で 217 段。 (figure labels are in Japanese; the numbers are the same)*

[![下寄りの横長の帯が図の階調。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/03_shadow_removal_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/03_shadow_removal.png)

*↑ 下寄りの横長の帯が図の階調。*

[![60 度でも 2 px 台。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/04_tilt_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/04_tilt_cliff.png)

*↑ 60 度でも 2 px 台。*

```
py -3.11 examples/poc_document_scan.py
```

Source: [examples/poc_document_scan.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_document_scan.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_document_scan)

Ops used (notes): [`corner_response`](https://furuse.work/ops/2d/edges/corner_response.html) · [`dc_homomorphic`](https://furuse.work/ops/2d/decomposition/dc_homomorphic.html) · [`fill_holes`](https://furuse.work/ops/2d/region/fill_holes.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`get_region_contour`](https://furuse.work/ops/2d/region/get_region_contour.html) · [`gray_tophat`](https://furuse.work/ops/2d/morphology/gray_tophat.html) · [`illuminate`](https://furuse.work/ops/2d/gray/illuminate.html) · [`mean_image`](https://furuse.work/ops/2d/smoothing/mean_image.html) · [`opening_circle`](https://furuse.work/ops/2d/region/opening_circle.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`project_points`](https://furuse.work/ops/3d/render/project_points.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`select_largest`](https://furuse.work/ops/2d/region/select_largest.html) · [`sobel_dir`](https://furuse.work/ops/2d/edges/sobel_dir.html) · [`var_threshold`](https://furuse.work/ops/2d/segmentation/var_threshold.html)

## No.2026.020 —— Forgery Detection as an ROC — Not the One Image Found, but Detection at a Fixed False-Positive Rate

[![Forgery Detection as an ROC — Not the One Image Found, but Detection at a Fixed False-Positive Rate](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/01_score_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/01_score_maps.png)

*↑ **Forgery Detection as an ROC — Not the One Image Found, but Detection at a Fixed False-Positive Rate** ―― Ten forgeries made by pasting a JPEG q60 patch onto a q92 background and saving at q95, scored with a per-pixel ROC. ELA's single number points the opposite way from the textbook (paste / background = 0.58x), and an untouched image still yields an AUC of 0.797 from position bias alone. The ghost-valley depth reaches an AUC of 0.997, which falls to 0.975 after one whole-image recompression at q75.*

[![凡例の数字は AUC。乱数が対角線に乗ることで測り方に偏りが無いと言える。ゴーストA は乱数と重なる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/02_roc_tampered_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/02_roc_tampered.png)

*↑ The measurement ―― 凡例の数字は AUC。乱数が対角線に乗ることで測り方に偏りが無いと言える。ゴーストA は乱数と重なる。 (figure labels are in Japanese; the numbers are the same)*

[![凡例の数字は AUC。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/03_roc_postprocess_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/03_roc_postprocess.png)

*↑ 凡例の数字は AUC。*

[![保存ボタン 1 回(q60 再圧縮)で ゴーストV は乱数以下。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/04_breaking_conditions_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/04_breaking_conditions.png)

*↑ 保存ボタン 1 回(q60 再圧縮)で ゴーストV は乱数以下。*

```
py -3.11 examples/poc_forensics_roc.py
```

Source: [examples/poc_forensics_roc.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_forensics_roc.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_forensics_roc)

Ops used (notes): [`copy_move_regions`](https://furuse.work/ops/imgforensics/copy_move/copy_move_regions.html) · [`error_level_map`](https://furuse.work/ops/imgforensics/compression/error_level_map.html) · [`jpeg_ghost_map`](https://furuse.work/ops/imgforensics/compression/jpeg_ghost_map.html) · [`jpeg_ghost_quality`](https://furuse.work/ops/imgforensics/compression/jpeg_ghost_quality.html) · [`noise_inconsistency_map`](https://furuse.work/ops/imgforensics/noise/noise_inconsistency_map.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html)

## No.2026.067 —— Craquelure networks — of three indicators, only junction degree breaks under imaging conditions

[![Craquelure networks — of three indicators, only junction degree breaks under imaging conditions](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/07_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/07_scene.png)

*↑ **Craquelure networks — of three indicators, only junction degree breaks under imaging conditions** ―― A Voronoi crack network is drawn in closed form for two ground-truth types — drying cracks (small tortuous cells) and age cracks (large grid-like cells) — with paint blotches, varnish gloss, raking light, blur and noise, then measured with a ridge op → skeleton → junction chain. Truth separates the types on all three indicators (cell diameter 18.0 vs 45.2 px, straightness 0.960 vs 1.000, degree-4 fraction 0.20 vs 0.83), yet the age type's degree-4 fraction drifts toward the drying value under texture (0.87 → 0.64) and raking light (0.70) while diameter and straightness stay put. Both predicted cliffs failed to appear: recall is still 0.696 at 0.15 px width and false positives only 0.382 at texture contrast 0.64. Raking light widens cracks one-sidedly by +0.37 px and shifts the centreline 0.75 px toward the light.*

[![Frangi は分岐点で応答が落ち、斜光でセルが崩れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/01_ridge_ops_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/01_ridge_ops.png)

*↑ The measurement ―― Frangi は分岐点で応答が落ち、斜光でセルが崩れる。 (figure labels are in Japanese; the numbers are the same)*

[![真値は幾何(ボロノイの頂点・辺)から。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/02_indicators_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/02_indicators.png)

*↑ 真値は幾何(ボロノイの頂点・辺)から。*

[![ひびの深さ 0.55。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/04_texture_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/04_texture_cliff.png)

*↑ ひびの深さ 0.55。*

[![ぼけが大きいほど小さいセルから消える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/06_blur_cell_limit_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/06_blur_cell_limit.png)

*↑ ぼけが大きいほど小さいセルから消える。*

[![縁に触れるセルは統計から外す(真値も同じ規約)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/09_map_cells_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/09_map_cells.png)

*↑ 縁に触れるセルは統計から外す(真値も同じ規約)。*

```
py -3.11 examples/poc_fresco_craquelure.py
```

Source: [examples/poc_fresco_craquelure.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_fresco_craquelure.py)

This run produced **11 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_fresco_craquelure)

Ops used (notes): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`cv_blackhat`](https://furuse.work/ops/2d/morphology/cv_blackhat.html) · [`distance_transform`](https://furuse.work/ops/2d/region/distance_transform.html) · [`hx_split_skeleton_region`](https://furuse.work/ops/2d/halcon_ext/hx_split_skeleton_region.html) · [`hysteresis_threshold`](https://furuse.work/ops/2d/segmentation/hysteresis_threshold.html) · [`junctions_skeleton`](https://furuse.work/ops/2d/region/junctions_skeleton.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`pruning`](https://furuse.work/ops/2d/region/pruning.html) · [`r2_endpoints_skeleton`](https://furuse.work/ops/2d/region/r2_endpoints_skeleton.html) · [`sk_area_opening`](https://furuse.work/ops/2d/morphology/sk_area_opening.html) · [`sk_frangi`](https://furuse.work/ops/2d/texture/sk_frangi.html) · [`sk_otsu`](https://furuse.work/ops/2d/segmentation/sk_otsu.html) · [`skeleton`](https://furuse.work/ops/2d/region/skeleton.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html) · [`xsk_meijering`](https://furuse.work/ops/2d/texture/xsk_meijering.html) · [`xsk_sato`](https://furuse.work/ops/2d/texture/xsk_sato.html)

## No.2026.077 —— Camera Fingerprints (PRNU): Which Camera Took This? — The Fingerprint Grows With Frame Count and Dies at the Save Button

[![Camera Fingerprints (PRNU): Which Camera Took This? — The Fingerprint Grows With Frame Count and Dies at the Save Button](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/01_estimators_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/01_estimators.png)

*↑ **Camera Fingerprints (PRNU): Which Camera Took This? — The Fingerprint Grows With Frame Count and Dies at the Save Button** ―― Two virtual cameras carry a fixed sensitivity pattern K; the fingerprint is estimated from 30 residuals and matched. Under clean conditions the same camera scores a median PCE of 2192 against 15.7 for the other (AUC 1.000), but JPEG-like quantisation at quality 50 cuts PCE to 3.6 % and a 0.5x downscale to 1.5 % — and what killed it was the residual extractor, not the geometry. A camera with K = 0 still yields a 'fingerprint' with PCE 1706 if the same background is shot 30 times: the scene turns into a fingerprint.*

[![別カメラのピークは毎回別の位置に立つ((0,0) は 0/30)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/02_match_pce_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/02_match_pce.png)

*↑ The measurement ―― 別カメラのピークは毎回別の位置に立つ((0,0) は 0/30)。 (figure labels are in Japanese; the numbers are the same)*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/03_n_sweep_corr_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/03_n_sweep_corr.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/05_jpeg_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/05_jpeg_sweep.png)

*↑ この回の図*

[![幾何の上限 = K 自身を同じ往復に通した相関²。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/07_resize_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/07_resize_sweep.png)

*↑ 幾何の上限 = K 自身を同じ往復に通した相関²。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/09_controls_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/09_controls.png)

*↑ この回の図*

```
py -3.11 examples/poc_prnu_camera_fingerprint.py
```

Source: [examples/poc_prnu_camera_fingerprint.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_prnu_camera_fingerprint.py)

This run produced **10 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint)

Ops used (notes): [`aug_jpeg_blocks`](https://furuse.work/ops/2d/augmentation/aug_jpeg_blocks.html) · [`evidence_quantile`](https://furuse.work/ops/imgforensics/calibration/evidence_quantile.html) · [`fingerprint_correlate`](https://furuse.work/ops/imgforensics/sensor/fingerprint_correlate.html) · [`gauss_image`](https://furuse.work/ops/2d/smoothing/gauss_image.html) · [`median_image`](https://furuse.work/ops/2d/rank/median_image.html) · [`null_distribution`](https://furuse.work/ops/imgforensics/calibration/null_distribution.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`sensor_fingerprint`](https://furuse.work/ops/imgforensics/sensor/sensor_fingerprint.html) · [`sk_nlm`](https://furuse.work/ops/2d/smoothing/sk_nlm.html) · [`sk_tv`](https://furuse.work/ops/2d/smoothing/sk_tv.html) · [`sk_wavelet`](https://furuse.work/ops/2d/smoothing/sk_wavelet.html) · [`xsp_dct_denoise`](https://furuse.work/ops/2d/smoothing/xsp_dct_denoise.html) · [`xsp_wiener`](https://furuse.work/ops/2d/smoothing/xsp_wiener.html)

### The 3-D Shape Wing — Align First, and the Alignment Eats the Defect

Work on point clouds and meshes differs from 2-D work in one decisive way: a pose-alignment step comes before the measurement. That step rotates the shape into whatever orientation makes the discrepancy smallest, so the larger the defect, the more of it the alignment absorbs, leaving a small residual and a part that looks in tolerance. The exhibits in this room try to count what the alignment ate.

Every ground truth here is written as a formula. Solids are built from analytic surfaces combined with boolean operations, chosen so that volume, surface area, wall thickness and curvature are known in closed form. Deformations are known fields (a local dent, a warp, a constant wear along the surface normal), poses are known rotations and translations, and the scan is a uniform sample of the surface with a known density, noise level and occlusion pattern. That is what makes it possible to hold the alignment error and the shape error apart.

The pitfalls specific to 3-D also get counted separately here. A nearest-neighbour distance is biased upward whenever there is noise, because it only ever counts one side. Normal signs are decided by whatever helper computed them. Changing the point density changes the scale of the distance itself. A symmetric shape has no unique pose. Each of these disappears the moment the numbers are folded into one.

## No.2026.054 —— Battery cell degradation by CT — the swelling shows outside, the cause stays inside

[![Battery cell degradation by CT — the swelling shows outside, the cause stays inside](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/02_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/02_scene.png)

*↑ **Battery cell degradation by CT — the swelling shows outside, the cause stays inside** ―― A prismatic lithium-ion cell — stacked electrodes inside an aluminium can — is built with ground truth, degraded by known fields (uniform swelling, local swelling, inter-layer gas voids, electrode misalignment), and then imaged for real: forward projection, beam hardening, photon noise and FBP reconstruction. Only 29.4 % of a 10 % electrode swelling reaches the outside, and a caliper across the centre reads 3.6 times the volume-equivalent mean (+0.235 vs +0.066 mm). Three cells tuned to the same external bulge differ by 0.000 mm in can height yet separate internally (void fraction 0.00 vs 5.20 %, layer flatness 0.0156 vs 0.0784 mm), and the resolution cliff for those internal numbers is set by the 0.120 mm inter-layer gap, not the 0.200 mm electrode — voxel/thickness = 0.30, where the sampling-theorem prediction said 0.80.*

[![真正面(0 度)なら空隙の影までは見える。ただし奥行きに積算されているので厚みも深さも出ない。22 度傾けると層の縞そのものが重なって消える —— 投影では姿勢が結果を決めてしまう。だから断層に落とす。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/01_xray_projection_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/01_xray_projection.png)

*↑ The measurement ―― 真正面(0 度)なら空隙の影までは見える。ただし奥行きに積算されているので厚みも深さも出ない。22 度傾けると層の縞そのものが重なって消える —— 投影では姿勢が結果を決めてしまう。だから断層に落とす。 (figure labels are in Japanese; the numbers are the same)*

[![端板は周辺で固定なので中央だけが出る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/03_outer_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/03_outer_profile.png)

*↑ 端板は周辺で固定なので中央だけが出る。*

[![一様膨れは平らなまま上がる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/06_flatness_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/06_flatness.png)

*↑ 一様膨れは平らなまま上がる。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/10_void_slices_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/10_void_slices.png)

*↑ この回の図*

[![空隙体積は崖の手前から単調に痩せる(部分体積効果)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/13_sweep_resolution_err_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/13_sweep_resolution_err.png)

*↑ 空隙体積は崖の手前から単調に痩せる(部分体積効果)。*

```
py -3.11 examples/poc_battery_ct_degradation.py
```

Source: [examples/poc_battery_ct_degradation.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_battery_ct_degradation.py)

This run produced **16 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_battery_ct_degradation)

Ops used (notes): [`beam_hardening_apply`](https://furuse.work/ops/tomography/artifact/beam_hardening_apply.html) · [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`fbp_volume`](https://furuse.work/ops/tomography/volume/fbp_volume.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`plane_sdf`](https://furuse.work/ops/3d/sdf_csg/plane_sdf.html) · [`projection_angles`](https://furuse.work/ops/tomography/layout/projection_angles.html) · [`radon_volume`](https://furuse.work/ops/tomography/volume/radon_volume.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`ring_artifact_apply`](https://furuse.work/ops/tomography/artifact/ring_artifact_apply.html) · [`sdf_intersect`](https://furuse.work/ops/3d/sdf_csg/sdf_intersect.html) · [`sdf_subtract`](https://furuse.work/ops/3d/sdf_csg/sdf_subtract.html) · [`sdf_to_occupancy`](https://furuse.work/ops/3d/transform/sdf_to_occupancy.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`vol_bounding_box`](https://furuse.work/ops/3d/domain/vol_bounding_box.html) · [`vol_edge_probe`](https://furuse.work/ops/3d/probe/vol_edge_probe.html) · [`vol_fft_lowpass`](https://furuse.work/ops/3d/frequency/vol_fft_lowpass.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_profile_line`](https://furuse.work/ops/3d/probe/vol_profile_line.html) · [`vol_region_props`](https://furuse.work/ops/3d/regionprops/vol_region_props.html) · [`vol_resize`](https://furuse.work/ops/3d/geom_transform/vol_resize.html) · [`vol_wall_thickness`](https://furuse.work/ops/3d/probe/vol_wall_thickness.html)

## No.2026.056 —— Fusing two sensors into a bird's-eye grid — a calibration that passes in pixels turns into metres at range

[![Fusing two sensors into a bird's-eye grid — a calibration that passes in pixels turns into metres at range](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/01_scene_bev_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/01_scene_bev.png)

*↑ **Fusing two sensors into a bird's-eye grid — a calibration that passes in pixels turns into metres at range** ―― An analytic street scene (a tall lead truck, plus two distant cars each hidden in the other sensor's shadow) is fused from a left-mirror LiDAR and a right-mirror depth camera into one bird's-eye grid, then swept over rotation, translation and timing errors in the extrinsics. Fusion reaches an occupancy IoU of 0.7033 against 0.5417 for the best single sensor — and every bit of that gain comes from complementary visibility, not accuracy. One pixel of reprojection error becomes 0.083 m at 22 m; the cliff is set by the object width, not the 0.2 m cell (IoU drops only 5.8 % when 68 % of the points have already crossed a cell); by 3 deg of yaw the fusion has fallen below the single sensor.*

[![横に 1.80 m 離した 2 センサの「自由と言い切れた領域」。青い帯が LiDAR にしか見えない所、橙の帯がカメラにしか見えない所、灰色は両方。白は真値の障害物。22 m の 2 台は**互いの影に 1 台ずつ入っている**。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/02_shadow_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/02_shadow_map.png)

*↑ The measurement ―― 横に 1.80 m 離した 2 センサの「自由と言い切れた領域」。青い帯が LiDAR にしか見えない所、橙の帯がカメラにしか見えない所、灰色は両方。白は真値の障害物。22 m の 2 台は**互いの影に 1 台ずつ入っている**。 (figure labels are in Japanese; the numbers are the same)*

[![画像 320 x 240 px、焦点距離 265 px。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/03_reprojection_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/03_reprojection.png)

*↑ 画像 320 x 240 px、焦点距離 265 px。*

[![誤差はカメラ側の外部パラメータにだけ入れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/04_conditions_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/04_conditions.png)

*↑ 誤差はカメラ側の外部パラメータにだけ入れる。*

[![LiDAR は 22 m の車を 1 セルも返せない(先行車の陰)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/06_fusion_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/06_fusion_map.png)

*↑ LiDAR は 22 m の車を 1 セルも返せない(先行車の陰)。*

[![水平の 2 本は単センサのゼロ点。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/08_cliff_rotation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/08_cliff_rotation.png)

*↑ 水平の 2 本は単センサのゼロ点。*

```
py -3.11 examples/poc_bev_sensor_fusion.py
```

Source: [examples/poc_bev_sensor_fusion.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bev_sensor_fusion.py)

This run produced **9 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_bev_sensor_fusion)

Ops used (notes): [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`closing_circle`](https://furuse.work/ops/2d/region/closing_circle.html) · [`depth_to_points`](https://furuse.work/ops/3d/transform/depth_to_points.html) · [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`fill_up`](https://furuse.work/ops/2d/region/fill_up.html) · [`fuse`](https://furuse.work/ops/3d/tsdf_fusion/fuse.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`occupancy_grid`](https://furuse.work/ops/3d/occupancy/occupancy_grid.html) · [`project_points`](https://furuse.work/ops/3d/render/project_points.html) · [`sdf_to_occupancy`](https://furuse.work/ops/3d/transform/sdf_to_occupancy.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`voxel_grid_downsample`](https://furuse.work/ops/3d/preprocess/voxel_grid_downsample.html) · [`voxel_iou`](https://furuse.work/ops/3d/metrics/voxel_iou.html)

## No.2026.058 —— CAD-to-scan deviation inspection — the fit absorbs the defect and invents a dent

[![CAD-to-scan deviation inspection — the fit absorbs the defect and invents a dent](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/01_scene.png)

*↑ **CAD-to-scan deviation inspection — the fit absorbs the defect and invents a dent** ―― An analytic machined part carries a known local dent, a bow and a wear band, all applied as exact displacements along the surface normal, and the scan is synthesized with a known pose, noise and one-sided occlusion. After alignment the signed deviation and the out-of-tolerance area show that the local dent is diluted by only 3.7 %, while a 121 um dent appears at the centre of the part where the truth is just 1.2 um (closed form predicts -120 um). What survives depends on how much the defect resembles the six rigid-body degrees of freedom; along the edges the nearest neighbour jumps to the adjacent face, producing 66.5 mm^2 of false out-of-tolerance area even in a defect-free control.*

[![真の姿勢を与えた最終行が推定器そのものの床。点-面 ICP との差は姿勢ではなく datum の取り方の差。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/02_methods_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/02_methods.png)

*↑ The measurement ―― 真の姿勢を与えた最終行が推定器そのものの床。点-面 ICP との差は姿勢ではなく datum の取り方の差。 (figure labels are in Japanese; the numbers are the same)*

[![3 枚目が一様に色づくのが第 6 章の主張 —— 位置合わせが反りの平均を吸って、部品全体が下へずれて読める。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/03_deviation_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/03_deviation_maps.png)

*↑ 3 枚目が一様に色づくのが第 6 章の主張 —— 位置合わせが反りの平均を吸って、部品全体が下へずれて読める。*

[![2 次元 Poisson 点過程の最近傍距離の平均 = 0.5/√ρ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/05_density_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/05_density_bias.png)

*↑ 2 次元 Poisson 点過程の最近傍距離の平均 = 0.5/√ρ。*

[![深さを 30 倍にしても割合は動かないが、広がりを変えると比例して増える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/08_dent_area_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/08_dent_area.png)

*↑ 深さを 30 倍にしても割合は動かないが、広がりを変えると比例して増える。*

[![上面だけを見ている。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/11_warp_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/11_warp_maps.png)

*↑ 上面だけを見ている。*

[![主図(動画、640 × 360・30 fps・12 秒): 前半は実測点群(だいだい)が CAD の参照点(灰)に重なるまで —— 位置合わせなし → FPFH 粗合わせ → 点-面 ICP の推定姿勢の間を補間して動かす(偏差 RMS 1](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/14_align_orbit.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/14_align_orbit.gif)

*↑ The animation ―― 主図(動画、640 × 360・30 fps・12 秒): 前半は実測点群(だいだい)が CAD の参照点(灰)に重なるまで —— 位置合わせなし → FPFH 粗合わせ → 点-面 ICP の推定姿勢の間を補間して動かす(偏差 RMS 18285.3 → 105.4 → 81.7 µm)。後半は重なった点群を一周し、符号付き偏差(±0.40 mm、だいだい = 足りない / 青 = 余る)で塗る(形が読めるよう陰影を薄く足した)。公差 ±0.10 mm を外れた面積は推定 2300.6 mm²、真値 2514.5 mm²。左手前の 3 本の線は CAD の x・y・z 軸。*

```
py -3.11 examples/poc_cad_scan_deviation.py
```

Source: [examples/poc_cad_scan_deviation.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_cad_scan_deviation.py)

This run produced **14 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_cad_scan_deviation)

Ops used (notes): [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`chamfer_distance`](https://furuse.work/ops/3d/metrics/chamfer_distance.html) · [`color_bar`](https://furuse.work/ops/annotate/furniture/color_bar.html) · [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`estimate_oriented_normals`](https://furuse.work/ops/3d/normals_orient/estimate_oriented_normals.html) · [`face_areas`](https://furuse.work/ops/3d/mesh_process/face_areas.html) · [`gicp`](https://furuse.work/ops/3d/gicp/gicp.html) · [`hausdorff_distance`](https://furuse.work/ops/3d/metrics/hausdorff_distance.html) · [`icp_point2plane`](https://furuse.work/ops/3d/refine/icp_point2plane.html) · [`icp_point2point_3d`](https://furuse.work/ops/3d/refine/icp_point2point_3d.html) · [`query_distance`](https://furuse.work/ops/3d/occupancy/query_distance.html) · [`register_fpfh`](https://furuse.work/ops/3d/feature_register/register_fpfh.html) · [`sphere_sdf`](https://furuse.work/ops/3d/sdf_csg/sphere_sdf.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`voxel_grid_downsample`](https://furuse.work/ops/3d/preprocess/voxel_grid_downsample.html)

## No.2026.063 —— Crop leaf area from above — folded by projection before it is ever hidden

[![Crop leaf area from above — folded by projection before it is ever hidden](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crop_phenotyping/08_scene_nadir_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crop_phenotyping/08_scene_nadir.png)

*↑ **Crop leaf area from above — folded by projection before it is ever hidden** ―― A maize canopy built from analytic leaf surfaces (one-sided area pi/4·L·W, leaf angle and projection coefficient both closed-form) is viewed through an exact nadir z-buffer to measure cover, occlusion and leaf angle. Inverting cover with Beer-Lambert underestimates a true leaf area index of 4.85 by 52.2 % even with the exact extinction coefficient, and stalls just above the ceiling of 2.26 predicted from two-scale clumping (measured 2.70). Occlusion changes nadir cover by not one bit; what breaks the estimate is the folding of projection — an average of 3.49 leaves cover a cell yet are counted once — and quadrupling point density buys only +1.92 in the largest resolvable index.*

[![閉形式 2 pi r h + 4 pi r^2 / pi r^2 h + 4/3 pi r^3 と比べる。2 値化を挟むと面積だけが一方向に膨らむ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crop_phenotyping/01_capsule_calibration_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crop_phenotyping/01_capsule_calibration.png)

*↑ The measurement ―― 閉形式 2 pi r h + 4 pi r^2 / pi r^2 h + 4/3 pi r^3 と比べる。2 値化を挟むと面積だけが一方向に膨らむ。 (figure labels are in Japanese; the numbers are the same)*

[![稈カプセルの符号付き距離場(縦断面、中心が内側 = 負)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crop_phenotyping/02_capsule_sdf_slice_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crop_phenotyping/02_capsule_sdf_slice.png)

*↑ 稈カプセルの符号付き距離場(縦断面、中心が内側 = 負)*

[![重なりの枚数(遮蔽を無視して全部数えた場合)は真値に乗る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crop_phenotyping/05_cliff_estimators_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crop_phenotyping/05_cliff_estimators.png)

*↑ 重なりの枚数(遮蔽を無視して全部数えた場合)は真値に乗る。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crop_phenotyping/10_sweep_beta_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crop_phenotyping/10_sweep_beta.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crop_phenotyping/14_wind_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crop_phenotyping/14_wind.png)

*↑ この回の図*

```
py -3.11 examples/poc_crop_phenotyping.py
```

Source: [examples/poc_crop_phenotyping.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_crop_phenotyping.py)

This run produced **17 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_crop_phenotyping)

Ops used (notes): [`boundary_vertices`](https://furuse.work/ops/3d/mesh_process/boundary_vertices.html) · [`capsule_sdf`](https://furuse.work/ops/3d/sdf_csg/capsule_sdf.html) · [`dem_slope`](https://furuse.work/ops/dem/surface/dem_slope.html) · [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`face_areas`](https://furuse.work/ops/3d/mesh_process/face_areas.html) · [`face_normals`](https://furuse.work/ops/3d/mesh_process/face_normals.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`mesh_area`](https://furuse.work/ops/3d/mesh_process/mesh_area.html) · [`mesh_sample_points`](https://furuse.work/ops/3d/resolution/mesh_sample_points.html) · [`mesh_volume`](https://furuse.work/ops/3d/mesh_process/mesh_volume.html) · [`occupancy_grid`](https://furuse.work/ops/3d/occupancy/occupancy_grid.html) · [`plane_segmentation`](https://furuse.work/ops/3d/segment/plane_segmentation.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`sdf_to_occupancy`](https://furuse.work/ops/3d/transform/sdf_to_occupancy.html)

## No.2026.064 —— Collapsing joint voids into one number — what the number drops is the shape that matters

[![Collapsing joint voids into one number — what the number drops is the shape that matters](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/01_scene_sections_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/01_scene_sections.png)

*↑ **Collapsing joint voids into one number — what the number drops is the shape that matters** ―― A synthetic die-attach bond line carries five void populations whose volume fraction is held exactly at 3.000 % while only their depth, shape and proximity change, re-imaged as an X-ray CT with a PSF, noise and beam-hardening cupping. The naive zero point — threshold, then report void fraction — separates the five conditions by only 0.17 points (2.46 to 2.63 %), yet the interface area shadowed by flat voids is 2.09x that of volume-matched spheres (14.49 vs 6.92 %) and the largest cluster spans 13.1x further when the voids are chained (80.0 vs 6.1 %). The predicted cliff never arrives: at 60 um voxels the void fraction still reads 3.21 % (it only wobbles by 1.36 points with the grid phase), while flatness becomes unmeasurable and the interface-deficit metric drops from 14.16 to 9.78 % — the degradation runs toward 'pass', which is the worst possible direction.*

[![疑似カラーはラベル番号を並べ替えたもの。側面図で界面(上端)に貼りついているのが見える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/02_void_label_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/02_void_label_map.png)

*↑ The measurement ―― 疑似カラーはラベル番号を並べ替えたもの。側面図で界面(上端)に貼りついているのが見える。 (figure labels are in Japanese; the numbers are the same)*

[![ボイド率の列だけを見ると 5 条件は区別できない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/03_controls_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/03_controls_table.png)

*↑ ボイド率の列だけを見ると 5 条件は区別できない。*

[![界面欠損率は 球/中央/散 0.0 % / 球/界面/散 6.9 % / 扁平/界面/散 14.5 % / 球/中央/連 0.0 % / 扁平/界面/連 14.7 % —— 体積率が同じでも 0 から](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/05_controls_section_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/05_controls_section.png)

*↑ 界面欠損率は 球/中央/散 0.0 % / 球/界面/散 6.9 % / 扁平/界面/散 14.5 % / 球/中央/連 0.0 % / 扁平/界面/連 14.7 % —— 体積率が同じでも 0 から 14.7 % まで動く。*

[![60 µm では扁平度が測れない(nan なので描けない)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/08_voxel_cliff_shape_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/08_voxel_cliff_shape.png)

*↑ 60 µm では扁平度が測れない(nan なので描けない)。*

[![塊の数が 24 から落ちた瞬間、最近接間隔は『隣のボイドまで』から『隣の鎖まで』に黙って入れ替わる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/10_threshold_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/10_threshold_sweep.png)

*↑ 塊の数が 24 から落ちた瞬間、最近接間隔は『隣のボイドまで』から『隣の鎖まで』に黙って入れ替わる。*

[![主図(動画、640 × 360・30 fps・11 秒): 同じボイド率の 2 条件(球・散在・層中央 2.46 % / 扁平・連なり・界面接触 2.63 %)で、xz 断面(橙の枠)を y 方向に掃引しながら 3-D のボイド(2 値化の](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/13_section_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/13_section_sweep.gif)

*↑ The animation ―― 主図(動画、640 × 360・30 fps・11 秒): 同じボイド率の 2 条件(球・散在・層中央 2.46 % / 扁平・連なり・界面接触 2.63 %)で、xz 断面(橙の枠)を y 方向に掃引しながら 3-D のボイド(2 値化の結果を marching cubes で面に)を回す。色はダイ側界面までの距離 —— 前者は層の中ほど(界面離隔の中央値 60.0 µm)、後者は界面に貼りつく(10.0 µm)。下は同じ断面の観測 CT(上 = ダイ)。合否の 1 個の数字(ボイド率)は 2 つを分けない。z は画面上だけ 2 倍。*

```
py -3.11 examples/poc_ct_void_morphology.py
```

Source: [examples/poc_ct_void_morphology.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_void_morphology.py)

This run produced **13 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_ct_void_morphology)

Ops used (notes): [`boundary_vertices`](https://furuse.work/ops/3d/mesh_process/boundary_vertices.html) · [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`color_bar`](https://furuse.work/ops/annotate/furniture/color_bar.html) · [`cylinder_sdf`](https://furuse.work/ops/3d/sdf_csg/cylinder_sdf.html) · [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`face_areas`](https://furuse.work/ops/3d/mesh_process/face_areas.html) · [`mesh_volume`](https://furuse.work/ops/3d/mesh_process/mesh_volume.html) · [`morph_dilate3d`](https://furuse.work/ops/3d/morphology/morph_dilate3d.html) · [`plane_sdf`](https://furuse.work/ops/3d/sdf_csg/plane_sdf.html) · [`query_distance`](https://furuse.work/ops/3d/occupancy/query_distance.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`sphere_sdf`](https://furuse.work/ops/3d/sdf_csg/sphere_sdf.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`vol_boundary_points`](https://furuse.work/ops/3d/boundary/vol_boundary_points.html) · [`vol_gaussian_psf`](https://furuse.work/ops/3d/restoration/vol_gaussian_psf.html) · [`voxel_to_mips`](https://furuse.work/ops/3d/transform/voxel_to_mips.html)

## No.2026.065 —— Manufacturability from geometry alone — faces that sit on the threshold flip when you smooth them

[![Manufacturability from geometry alone — faces that sit on the threshold flip when you smooth them](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/01_scene.png)

*↑ **Manufacturability from geometry alone — faces that sit on the threshold flip when you smooth them** ―― A synthetic part with known design values (thin walls, a slot, ribs near 45 deg, holes) is voxelised, then wall thickness, support area and tool clearance are measured. Across the 45 deg threshold the support area jumps 185.22 -> 576.10 mm^2 — 3.11x for 0.2 deg — and that step vanishes entirely when the isosurface is taken from a distance field, and loses 12 % under smoothing. Thickness collapses onto a 2-voxel lattice (the inscribed sphere does not help), and clearance errors go both ways: at 0.500 mm voxels the slot appears 2.000 mm wide and admits a tool that does not fit.*

[![上: 左端の 2 本が薄壁(1.500 mm)とそのあいだのスロット(1.500 mm)、右の三角が補強。下: リブと薄壁の footprint。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/02_sections_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/02_sections.png)

*↑ The measurement ―― 上: 左端の 2 本が薄壁(1.500 mm)とそのあいだのスロット(1.500 mm)、右の三角が補強。下: リブと薄壁の footprint。 (figure labels are in Japanese; the numbers are the same)*

[![右ほど粗い。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/03_thickness_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/03_thickness_cliff.png)

*↑ 右ほど粗い。*

[![解析は階段。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/04_threshold_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/04_threshold_cliff.png)

*↑ 解析は階段。*

[![左 = 水平からの傾き(暗い = 0 度 = 最悪、明るい = 90 度 = 垂直)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/06_overhang_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/06_overhang_map.png)

*↑ 左 = 水平からの傾き(暗い = 0 度 = 最悪、明るい = 90 度 = 垂直)。*

[![1.600 mm を超えると入らない工具を通し、1.200 mm を切ると入る工具を落とす。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/08_reach_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/08_reach_cliff.png)

*↑ 1.600 mm を超えると入らない工具を通し、1.200 mm を切ると入る工具を落とす。*

```
py -3.11 examples/poc_dfm_thickness_overhang.py
```

Source: [examples/poc_dfm_thickness_overhang.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dfm_thickness_overhang.py)

This run produced **9 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_dfm_thickness_overhang)

Ops used (notes): [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`erfc`](https://furuse.work/ops/math/numerics/erfc.html) · [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`face_areas`](https://furuse.work/ops/3d/mesh_process/face_areas.html) · [`face_normals`](https://furuse.work/ops/3d/mesh_process/face_normals.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`morph_erode3d`](https://furuse.work/ops/3d/morphology/morph_erode3d.html) · [`render_shaded`](https://furuse.work/ops/3d/render/render_shaded.html) · [`sdf_intersect`](https://furuse.work/ops/3d/sdf_csg/sdf_intersect.html) · [`sdf_subtract`](https://furuse.work/ops/3d/sdf_csg/sdf_subtract.html) · [`sdf_to_occupancy`](https://furuse.work/ops/3d/transform/sdf_to_occupancy.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`vol_wall_thickness`](https://furuse.work/ops/3d/probe/vol_wall_thickness.html) · [`voxel_to_mesh`](https://furuse.work/ops/3d/transform/voxel_to_mesh.html)

## No.2026.070 —— Earthwork on a slope — align first and the scar gets shallower

[![Earthwork on a slope — align first and the scar gets shallower](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/09_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/09_scene.png)

*↑ **Earthwork on a slope — align first and the scar gets shallower** ―― A synthetic slope carries an excavation and a deposit of known volume; two epochs of airborne points are differenced both vertically (DoD) and along the local surface normal (M3C2). The expected "cos-θ shrinkage on a slope" never appears — integrating vertical differences over horizontal area cancels the cosine, and the excavated volume stays within -0.011 % from 0 to 40 degrees. What breaks is the registration: when the changed area covers 33 % of the scene, ICP absorbs the change itself and the net volume collapses from a true -30.4 m3 to -3.8 m3, while a no-change control alone already fabricates 83.8 m3 of phantom excavation.*

[![傾斜を 0 から 40 度まで振っても体積の誤差に傾向が無い。cos は積分で約分する。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/01_geometry_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/01_geometry.png)

*↑ The measurement ―― 傾斜を 0 から 40 度まで振っても体積の誤差に傾向が無い。cos は積分で約分する。 (figure labels are in Japanese; the numbers are the same)*

[![真の掘削は 164.2 m3。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/02_controls_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/02_controls.png)

*↑ 真の掘削は 164.2 m3。*

[![予測式は先に立ててから測った。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/04_slope_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/04_slope_table.png)

*↑ 予測式は先に立ててから測った。*

[![誤差はそのしきい値以上の真値に対する値。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/07_occlusion_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/07_occlusion.png)

*↑ 誤差はそのしきい値以上の真値に対する値。*

[![M3C2 の L は法線方向なので cos 25 度 = 0.906 倍だけ浅く出る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/11_scar_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/11_scar_profile.png)

*↑ M3C2 の L は法線方向なので cos 25 度 = 0.906 倍だけ浅く出る。*

[![主図(動画、640 × 360・30 fps・12 秒): 前半は傾斜 25 度の斜面を北の上空から横切り、時期 1 の点群(8 pt/m²、樹冠に当たった点 = 緑)を見せる(動画専用の乱数で作った別の標本)。後半は時期 2 の地形の周り](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/12_flight.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/12_flight.gif)

*↑ The animation ―― 主図(動画、640 × 360・30 fps・12 秒): 前半は傾斜 25 度の斜面を北の上空から横切り、時期 1 の点群(8 pt/m²、樹冠に当たった点 = 緑)を見せる(動画専用の乱数で作った別の標本)。後半は時期 2 の地形の周りを回り、色を DoD の鉛直差から M3C2 の法線距離へ塗り替える(同じ尺度 ±1.2 m、青 = 下がった)。崩壊中心の深さは DoD 1.212 m / M3C2 1.096 m で比 1.105(sec 25 度 = 1.103)。有意な core の M3C2 土量は掘削 142.3 / 堆積 107.7 m³(真値 164.2 / 133.7)。黒っぽい所は測れなかった core。*

```
py -3.11 examples/poc_lidar_terrain_change.py
```

Source: [examples/poc_lidar_terrain_change.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_lidar_terrain_change.py)

This run produced **14 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_lidar_terrain_change)

Ops used (notes): [`chamfer_distance`](https://furuse.work/ops/3d/metrics/chamfer_distance.html) · [`color_bar`](https://furuse.work/ops/annotate/furniture/color_bar.html) · [`dem_hillshade`](https://furuse.work/ops/dem/shading/dem_hillshade.html) · [`dem_slope`](https://furuse.work/ops/dem/surface/dem_slope.html) · [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`estimate_oriented_normals`](https://furuse.work/ops/3d/normals_orient/estimate_oriented_normals.html) · [`fit_plane_3d`](https://furuse.work/ops/3d/geometry/fit_plane_3d.html) · [`icp_point2point_3d`](https://furuse.work/ops/3d/refine/icp_point2point_3d.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`ransac_plane`](https://furuse.work/ops/3d/robust_fit/ransac_plane.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`voxel_grid_downsample`](https://furuse.work/ops/3d/preprocess/voxel_grid_downsample.html)

## No.2026.099 —— Weighing an Animal from Silhouettes — The Error You Can Buy Down, and the One You Cannot

[![Weighing an Animal from Silhouettes — The Error You Can Buy Down, and the One You Cannot](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/10_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/10_scene.png)

*↑ **Weighing an Animal from Silhouettes — The Error You Can Buy Down, and the One You Cannot** ―― Estimate an animal's volume from the intersection of multi-view silhouettes (the visual hull) and convert it to weight. A visual hull is always an upper bound, so the question is not whether it is good but that it is always high. The closed form corrected the field rule of thumb: K cameras do not give a K-gon. Under parallel projection each camera contributes two support lines perpendicular to its line of sight, and two opposing cameras contribute the same pair, so the number of distinct tangents is K for even K and 2K for odd K. Three cameras and six cameras are therefore geometrically identical (closed form 1.16772 both times, the measured 0.013 difference being discretisation only), half of an even rig is wasted, and 13 cameras (1.03056) beat 16 (1.04768). Requiring 2 % on weight needs 13 cameras if odd counts are allowed and 24 if not — the naive circular reading of (K/pi)tan(pi/K) says 13, so a team building an even-numbered rig is short by 11. Against the exact ellipse (a/b = 2.76) the measurements sit just above the closed form at every K, confirming it as a lower bound. The centre of this exhibit is separating the error you can buy down from the one you cannot: the phantom between the legs falls from 7.13 % to 1.37 % going from 4 to 48 cameras, while the hollow of the back falls only 3.8 points (56.4 % to 52.6 %) for the same twelvefold increase, because a concavity that never reaches the outline leaves no trace in any silhouette. One pixel of segmentation error is likewise unbuyable, worth +3.21 % per pixel (23.7 kg), matching Steiner's dV/V = (S/V)delta to a ratio of 1.04 — though the text records that two opposing effects happened to cancel there. The rulers disagree on the winner: volume-derived and allometric weight both prefer 24 cameras with a two-pixel erosion, while the height of the centroid prefers no erosion at all, since the thin legs disappear first. One prediction was wrong: a tape measure wraps the body, so the 3-D convex hull was expected to be the strong method for heart girth, but it measured +55.2 % — the hull of the whole body fills in under the belly and drags the cross-section down to the ground. The convex hull of a section and the section of a convex hull are not the same object. A tooling hole was found and closed on the way: the OpenCV-convention pose helper that space carving requires was unreachable from every public tier, while the name look_at in the public API belonged to the OpenGL-convention version, so grabbing the wrong one returned an empty hull with no exception at all.*

[![真値 0.7238 m^3 / 738 kg。外接直方体と OBB は上界の中でもいちばん粗い。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/01_null_baseline_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/01_null_baseline.png)

*↑ The measurement ―― 真値 0.7238 m^3 / 738 kg。外接直方体と OBB は上界の中でもいちばん粗い。 (figure labels are in Japanese; the numbers are the same)*

[![法線は方位 ± 90 度。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/02_closed_form_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/02_closed_form.png)

*↑ 法線は方位 ± 90 度。*

[![くぼみ(輪郭に出ない凹み)は台数に鈍感、脚の間(輪郭に出る凹み)は台数に敏感。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/04_persistent_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/04_persistent.png)

*↑ くぼみ(輪郭に出ない凹み)は台数に鈍感、脚の間(輪郭に出る凹み)は台数に敏感。*

[![K=12・4.0 mm/px。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/07_controls_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/07_controls.png)

*↑ K=12・4.0 mm/px。*

[![脚の間の空隙はどの 1 枚にも写っている(だから彫れる)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/11_silhouettes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/11_silhouettes.png)

*↑ 脚の間の空隙はどの 1 枚にも写っている(だから彫れる)。*

[![動画(270 コマ、560 × 420 px): 牛の周りを 1 周しながら、彫刻に使うカメラの台数を 4 → 48 台(軸周り等間隔、8 m 先)へ増やす。表示は §4 で数えた視体積交差の占有の表面で、真の体に接する面は灰、真に空の所に](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/14_hull_orbit.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/14_hull_orbit.gif)

*↑ The animation ―― 動画(270 コマ、560 × 420 px): 牛の周りを 1 周しながら、彫刻に使うカメラの台数を 4 → 48 台(軸周り等間隔、8 m 先)へ増やす。表示は §4 で数えた視体積交差の占有の表面で、真の体に接する面は灰、真に空の所に立つ面(余分)はだいだい。最初の段は真の占有。横腹の帯と脚の間の幽霊(7.13 % → 1.37 %)は台数とともに消えるが、背中のくぼみに被さる蓋は K = 48 でも 52.6 % 埋まったまま(K = 4 で 56.4 %)—— 輪郭に出ない凹みはシルエットに情報が無い。体積は真値の 1.2255 → 1.0339 倍。カメラの仰角は 20 → 46 度へ上げていき、台数の多い段ほど背中の蓋が見える。左下の 3 本は x(体長)・y(体幅)・z(上)、灰の細線は地面の x 軸・y 軸。*

```
py -3.11 examples/poc_livestock_body_volume.py
```

Source: [examples/poc_livestock_body_volume.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_livestock_body_volume.py)

This run produced **14 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_livestock_body_volume)

Ops used (notes): [`carve`](https://furuse.work/ops/3d/space_carving/carve.html) · [`carve_look_at`](https://furuse.work/ops/3d/space_carving/carve_look_at.html) · [`convex_hull`](https://furuse.work/ops/3d/bounds/convex_hull.html) · [`erosion_circle`](https://furuse.work/ops/2d/region/erosion_circle.html) · [`mesh_volume`](https://furuse.work/ops/3d/mesh_process/mesh_volume.html) · [`synthesize_silhouette`](https://furuse.work/ops/3d/space_carving/synthesize_silhouette.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`vol_rle_bbox`](https://furuse.work/ops/3d/rle_region/vol_rle_bbox.html) · [`vol_rle_centroid`](https://furuse.work/ops/3d/rle_region/vol_rle_centroid.html) · [`vol_rle_encode`](https://furuse.work/ops/3d/rle_region/vol_rle_encode.html) · [`vol_rle_volume`](https://furuse.work/ops/3d/rle_region/vol_rle_volume.html) · [`voxel_to_mesh`](https://furuse.work/ops/3d/transform/voxel_to_mesh.html)

## No.2026.072 —— Repair the mesh, then measure — the defect count clears, the quantity does not

[![Repair the mesh, then measure — the defect count clears, the quantity does not](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/01_scene.png)

*↑ **Repair the mesh, then measure — the defect count clears, the quantity does not** ―― A closed triangle mesh is built from the boolean union of a sphere, a torus and a box, then seeded with a known count of each defect class — holes, flipped faces, non-manifold edges, degenerate slivers, duplicated vertices and self-intersection — and tracked with both the topological counts and the volume/area. The Euler characteristic does not move at all for 5 of the 6 classes, and 6 holes plus 6 duplicated faces leave the vertex, edge, face and chi counts identical to the healthy part. Repair does not bring the quantities back: filling a 45-degree cap hole on a sphere changes the surface area by +6.868 % where the closed form predicts -2.145 % (the rim is a staircase, not a circle), and pushing just 6 vertices inward passes all three topological checks while the area is +4.414 % and the volume -0.332 % — a 13-fold disagreement.*

[![健全な部品の χ は 0(種数 1)。χ=2 を合格条件にすると健全品が落ちる。最終行は打ち消し。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/02_euler_blindspots_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/02_euler_blindspots.png)

*↑ The measurement ―― 健全な部品の χ は 0(種数 1)。χ=2 を合格条件にすると健全品が落ちる。最終行は打ち消し。 (figure labels are in Japanese; the numbers are the same)*

[![ただし順番が両向きに効く —— 溶接前は割れの境界を穴として数え、溶接後は退化三角形を数え損ねる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/03_defect_counts_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/03_defect_counts.png)

*↑ ただし順番が両向きに効く —— 溶接前は割れの境界を穴として数え、溶接後は退化三角形を数え損ねる。*

[![幅ゼロの割れ(重複頂点 18 個)を直した結果。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/05_repair_vs_restore_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/05_repair_vs_restore.png)

*↑ 幅ゼロの割れ(重複頂点 18 個)を直した結果。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/08_hole_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/08_hole_frames.png)

*↑ この回の図*

[![面積 0 の判定に引っかかるずっと手前で、潰れ面の法線は使いものにならなくなる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/11_sliver_threshold_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/11_sliver_threshold.png)

*↑ 面積 0 の判定に引っかかるずっと手前で、潰れ面の法線は使いものにならなくなる。*

[![動画(272 コマ、480 × 480 px): 健全な部品(面 11208 枚)の周りを 1.5 周しながら、QEM 簡略化の削減率を 0 → 98 % へ 8 段で上げる。面は平らに塗り、色は面の 3 頂点の平均曲率 |H|(尺度は削減](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/14_decimate_orbit.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/14_decimate_orbit.gif)

*↑ The animation ―― 動画(272 コマ、480 × 480 px): 健全な部品(面 11208 枚)の周りを 1.5 周しながら、QEM 簡略化の削減率を 0 → 98 % へ 8 段で上げる。面は平らに塗り、色は面の 3 頂点の平均曲率 |H|(尺度は削減前の 99 パーセンタイル 12.6 /mm で固定)。50 % 削減で体積の誤差は -0.019 % しかないのに曲率の 95 パーセンタイルは 5.89 → 7.72(+31 %)—— 明るい(尖った)面が先に増える。98 % 削減でようやく体積 -4.199 %。左下の 3 本は配列の軸(0 = 貫通穴の軸 = 画面の上、2 = 角柱ボスの側)。*

```
py -3.11 examples/poc_mesh_quality_repair.py
```

Source: [examples/poc_mesh_quality_repair.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_mesh_quality_repair.py)

This run produced **14 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_mesh_quality_repair)

Ops used (notes): [`decimate_qem`](https://furuse.work/ops/3d/mesh_process/decimate_qem.html) · [`face_normals`](https://furuse.work/ops/3d/mesh_process/face_normals.html) · [`fill_holes`](https://furuse.work/ops/2d/region/fill_holes.html) · [`inertia_tensor`](https://furuse.work/ops/3d/moment_invariant/inertia_tensor.html) · [`mesh_area`](https://furuse.work/ops/3d/mesh_process/mesh_area.html) · [`mesh_edge_lengths`](https://furuse.work/ops/3d/terrain/mesh_edge_lengths.html) · [`mesh_edge_stats`](https://furuse.work/ops/3d/resolution/mesh_edge_stats.html) · [`sdf_subtract`](https://furuse.work/ops/3d/sdf_csg/sdf_subtract.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`vertex_curvature`](https://furuse.work/ops/3d/mesh_process/vertex_curvature.html) · [`vertex_normals`](https://furuse.work/ops/3d/mesh_process/vertex_normals.html) · [`voxel_to_mesh`](https://furuse.work/ops/3d/transform/voxel_to_mesh.html)

## No.2026.101 —— Pallet load utilization — one number gives voids and overhang the same value

[![Pallet load utilization — one number gives voids and overhang the same value](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pallet_load_utilization/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pallet_load_utilization/01_scene.png)

*↑ **Pallet load utilization — one number gives voids and overhang the same value** ―― Two loads with opposite defects sit on a 1200 x 1000 mm pallet: load A hides a 400 x 400 x 420 mm cavity under a bridging layer plus 20 / 50 / 120 mm slots, while load B is solid but overhangs by 90 mm and tops out 100 mm above the 1800 mm limit. Solving the middle-layer height in closed form (995.0 mm) makes their apparent utilization identical — 62.65 % vs 62.67 %, a 0.02 pt gap — yet A's 3.11 pt is invisible void and B's is 2.10 pt overhang plus 0.58 pt over-height, so one load gets restacked and the other gets rejected. Treating the load as one envelope reports 113.90 % (AABB) and 166.44 % (PCA box) for load B, and the IoU between the true solid and the top-down extrusion is 0.9493 / 1.0000 — both read as 'good agreement'. One knob, the height-map cell size, breaks the answer in two opposite directions: a slot of width w survives only as max(0, 1 - g/w) (a 20 mm slot is gone at g = 40 mm, and at g = w exactly the grid phase decides all-or-nothing — 1 alignment in 5 sees everything), while a load that overhangs by nothing acquires a false overhang of perimeter x g/2 x height that overtakes load B's genuine 0.0450 m3 from g = 40 mm on.*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pallet_load_utilization/02_hidden_void_section_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pallet_load_utilization/02_hidden_void_section.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pallet_load_utilization/03_zero_points_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pallet_load_utilization/03_zero_points.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pallet_load_utilization/04_breakdown_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pallet_load_utilization/04_breakdown.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pallet_load_utilization/06_heightmap_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pallet_load_utilization/06_heightmap_frames.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pallet_load_utilization/07_gsd_false_overhang_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pallet_load_utilization/07_gsd_false_overhang.png)

*↑ この回の図*

```
py -3.11 examples/poc_pallet_load_utilization.py
```

Source: [examples/poc_pallet_load_utilization.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pallet_load_utilization.py)

This run produced **8 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_pallet_load_utilization)

Ops used (notes): [`aabb`](https://furuse.work/ops/3d/bounds/aabb.html) · [`convex_hull`](https://furuse.work/ops/3d/bounds/convex_hull.html) · [`euclidean_cluster`](https://furuse.work/ops/3d/segment/euclidean_cluster.html) · [`inner_box3`](https://furuse.work/ops/3d/regionprops/inner_box3.html) · [`mesh_volume`](https://furuse.work/ops/3d/mesh_process/mesh_volume.html) · [`voxel_iou`](https://furuse.work/ops/3d/metrics/voxel_iou.html)

## No.2026.075 —— Pipe Wall Loss on the Unwrapped Map — The Axis You Choose Eats the Invert Corrosion

[![Pipe Wall Loss on the Unwrapped Map — The Axis You Choose Eats the Invert Corrosion](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/01_scene_pipe_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/01_scene_pipe.png)

*↑ **Pipe Wall Loss on the Unwrapped Map — The Axis You Choose Eats the Invert Corrosion** ―― A synthetic pipe carries a pit, a full-circumference thinning band, invert corrosion, a weld bead, ovality and a sagging axis, all at known depths; the in-pipe range sensor is then deliberately run off-axis before the bore is unwrapped. A 4.0 mm axis offset alone flags 44.8 % of a corrosion-free round pipe as wall loss — within 1.84 points of the geometric prediction that an offset e appears as a one-cycle sinusoid of amplitude e — and the fictitious loss volume is 149.9 times the real pit. Removing the one-cycle term removes the fiction, but 79 % of invert corrosion (the commonest defect in sewers) lives in that same harmonic, so its detection falls from 100.0 % to 34.4 %; only constraining the axis the way physics does (a straight line plus a sag) keeps both.*

[![下の帯の細くなっている所が管底腐食。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/02_scene_polar_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/02_scene_polar.png)

*↑ The measurement ―― 下の帯の細くなっている所が管底腐食。 (figure labels are in Japanese; the numbers are the same)*

[![真の減肉 [mm)(縦 = z 0..300 mm、横 = θ 0..360 度。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/03_map_truth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/03_map_truth.png)

*↑ 真の減肉 [mm](縦 = z 0..300 mm、横 = θ 0..360 度。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/07_map_false_flag_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/07_map_false_flag.png)

*↑ この回の図*

[![楕円化は k=2 に立つので分離できる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/11_spectrum_defects_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/11_spectrum_defects.png)

*↑ 楕円化は k=2 に立つので分離できる。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/15_defect_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/15_defect_table.png)

*↑ この回の図*

```
py -3.11 examples/poc_pipe_wall_loss.py
```

Source: [examples/poc_pipe_wall_loss.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pipe_wall_loss.py)

This run produced **19 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_pipe_wall_loss)

Ops used (notes): [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_select`](https://furuse.work/ops/blob/select/blob_select.html) · [`cylinder_sdf`](https://furuse.work/ops/3d/sdf_csg/cylinder_sdf.html) · [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`polar_unwrap`](https://furuse.work/ops/3d/curvilinear/polar_unwrap.html) · [`ransac_cylinder`](https://furuse.work/ops/3d/robust_fit/ransac_cylinder.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`sdf_subtract`](https://furuse.work/ops/3d/sdf_csg/sdf_subtract.html) · [`sdf_to_occupancy`](https://furuse.work/ops/3d/transform/sdf_to_occupancy.html) · [`spectrum`](https://furuse.work/ops/oned/signal/spectrum.html) · [`vol_wall_thickness`](https://furuse.work/ops/3d/probe/vol_wall_thickness.html)

## No.2026.076 —— Warpage lives in the layer history — averaging the area throws the placement away

[![Warpage lives in the layer history — averaging the area throws the placement away](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/01_scene.png)

*↑ **Warpage lives in the layer history — averaging the area throws the placement away** ―― Seven synthetic parts are sliced into layers with a known constant per-layer shrinkage strain; warpage is first predicted in closed form from the layer-area history alone, then measured with an incremental layer-birth finite-element solve. A predictor that looks only at the final shape returns exactly zero (2.712e-21), and the history-based closed form lands within 0.4 % on 4 of the 7 shapes — but the moment the area is averaged along the length, where the material sits is lost. Three parts whose layer-area histories match to the last square millimetre bow by 0.4109 / 0.3809 / 0.3271 mm (a 26 % spread), and the force peeling them off the build plate differs by 48x (11.8 vs 573.5 N), flipping the pass/fail verdict.*

[![この断面の面積の列だけが、閉形式の入力になる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/02_layer_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/02_layer_frames.png)

*↑ The measurement ―― この断面の面積の列だけが、閉形式の入力になる。 (figure labels are in Japanese; the numbers are the same)*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/03_shapes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/03_shapes.png)

*↑ この回の図*

[![断面 2 次モーメントが層数の 3 乗で増えるのに、腕は 1 乗でしか伸びないため。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/07_saturation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/07_saturation.png)

*↑ 断面 2 次モーメントが層数の 3 乗で増えるのに、腕は 1 乗でしか伸びないため。*

[![首の細さでは崩れない(別図)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/12_cliff_aspect_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/12_cliff_aspect.png)

*↑ 首の細さでは崩れない(別図)。*

[![正 = 接着剤が引っ張られる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/16_peel_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/16_peel_profile.png)

*↑ 正 = 接着剤が引っ張られる。*

```
py -3.11 examples/poc_print_warpage_risk.py
```

Source: [examples/poc_print_warpage_risk.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_print_warpage_risk.py)

This run produced **20 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_print_warpage_risk)

Ops used (notes): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`sdf_to_occupancy`](https://furuse.work/ops/3d/transform/sdf_to_occupancy.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html)

## No.2026.081 —— Human-machine clearance — swap the body for a point, and the hazard vanishes with it

[![Human-machine clearance — swap the body for a point, and the hazard vanishes with it](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_safety_clearance/02_frames_clearance_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_safety_clearance/02_frames_clearance.png)

*↑ **Human-machine clearance — swap the body for a point, and the hazard vanishes with it** ―― A ten-capsule articulated body and a moving arm are synthesised so that the true surface-to-surface minimum separation is known in closed form at every instant, and the speed-and-separation-monitoring verdict is then scored against it. Representing the person by one centroid inside a 0.30 m sphere reports the distance +0.166 m too far while a hazard is present and misses 14.3 % of the dangerous frames (28.6 % for a foot-level scanner) — with almost no false alarms, so the failure is strictly one-sided. With a single camera behind the person, 48.6 % of the dangerous frames have the estimate decided by a body part that is not the true nearest one, and 18.1 % are missed; a second camera restores 0 %, but the uncertainty claimed from repeatability, 0.036 m, is only one fifth of the 0.178 m bias that occlusion actually produces.*

[![危険 = 真の距離 < 0.640 m、停止判定 = 推定 < 0.690 m。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_safety_clearance/01_conditions_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_safety_clearance/01_conditions.png)

*↑ The measurement ―― 危険 = 真の距離 < 0.640 m、停止判定 = 推定 < 0.690 m。 (figure labels are in Japanese; the numbers are the same)*

[![疎にするほど推定は遠くなるので、誤検知が減って見落としが増える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_safety_clearance/03_sweep_density_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_safety_clearance/03_sweep_density.png)

*↑ 疎にするほど推定は遠くなるので、誤検知が減って見落としが増える。*

[![横 = x [-0.2, 2.2) m、縦 = y [-1.1, 1.1) m。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_safety_clearance/06_map_miss_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_safety_clearance/06_map_miss.png)

*↑ 横 = x [-0.2, 2.2] m、縦 = y [-1.1, 1.1] m。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_safety_clearance/09_grid_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_safety_clearance/09_grid_bias.png)

*↑ この回の図*

[![人は 10 本のカプセル、機械は 2 本のリンク + 基台、手前は治具台。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_safety_clearance/12_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_safety_clearance/12_scene.png)

*↑ 人は 10 本のカプセル、機械は 2 本のリンク + 基台、手前は治具台。*

```
py -3.11 examples/poc_safety_clearance.py
```

Source: [examples/poc_safety_clearance.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_safety_clearance.py)

This run produced **14 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_safety_clearance)

Ops used (notes): [`annotate3d_label`](https://furuse.work/ops/3d/annotate3d/annotate3d_label.html) · [`annotate3d_measure`](https://furuse.work/ops/3d/annotate3d/annotate3d_measure.html) · [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`capsule_sdf`](https://furuse.work/ops/3d/sdf_csg/capsule_sdf.html) · [`chamfer_distance`](https://furuse.work/ops/3d/metrics/chamfer_distance.html) · [`distance_line_line`](https://furuse.work/ops/3d/geometry/distance_line_line.html) · [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`face_areas`](https://furuse.work/ops/3d/mesh_process/face_areas.html) · [`hausdorff_distance`](https://furuse.work/ops/3d/metrics/hausdorff_distance.html) · [`query_distance`](https://furuse.work/ops/3d/occupancy/query_distance.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`sdf_to_occupancy`](https://furuse.work/ops/3d/transform/sdf_to_occupancy.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html)

## No.2026.082 —— As-built deviation of a room — the compromise pose is handed to the innocent element

[![As-built deviation of a room — the compromise pose is handed to the innocent element](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/01_scene_plan_section_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/01_scene_plan_section.png)

*↑ **As-built deviation of a room — the compromise pose is handed to the innocent element** ―― A synthetic room carries known construction errors — leaning walls, a sloping and sagging floor, off-size columns, displaced openings — and is re-measured by a simulated scan from three stations with column shadows, incidence-dependent noise, mixed pixels and registration error. One number for the whole building (mean distance to the design model) moves by only 1.41 mm between a perfect building and a defective one; aligning the cloud in one piece shrinks the wall lean to 69 % of truth and hands 0.89 mrad of tilt to a ceiling that is perfectly level (a closed-form prediction of what the fit absorbs matches the measurement to 0.05 mrad). The cliff is set by the height of the surviving surface rather than by the dropout rate: at the same 90 % loss, dropping points at random costs 0.098 mrad while keeping only the lower band costs 1.234 mrad — 12.6 times worse.*

[![いちばん暗い所は 1 か所も見ていない。柱の影はスキャン位置から放射状に伸びる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/02_station_coverage_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/02_station_coverage.png)

*↑ The measurement ―― いちばん暗い所は 1 か所も見ていない。柱の影はスキャン位置から放射状に伸びる。 (figure labels are in Japanese; the numbers are the same)*

[![(a) と (c) の差は平均で 1.41 mm、Chamfer で 0.50 mm。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/03_one_number_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/03_one_number.png)

*↑ (a) と (c) の差は平均で 1.41 mm、Chamfer で 0.50 mm。*

[![左端の帯が色目盛り(上 +12 mm / 下 -12 mm)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/06_deviation_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/06_deviation_map.png)

*↑ 左端の帯が色目盛り(上 +12 mm / 下 -12 mm)。*

[![「偽の誤差」列は設計どおりに建った建物を同じ手順で測った値。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/09_element_verdicts_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/09_element_verdicts.png)

*↑ 「偽の誤差」列は設計どおりに建った建物を同じ手順で測った値。*

[![点を増やしても系統誤差は薄まらない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/12_cliff_registration_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/12_cliff_registration.png)

*↑ 点を増やしても系統誤差は薄まらない。*

```
py -3.11 examples/poc_scan_to_bim_asbuilt.py
```

Source: [examples/poc_scan_to_bim_asbuilt.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_scan_to_bim_asbuilt.py)

This run produced **15 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt)

Ops used (notes): [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`chamfer_distance`](https://furuse.work/ops/3d/metrics/chamfer_distance.html) · [`cylinder_sdf`](https://furuse.work/ops/3d/sdf_csg/cylinder_sdf.html) · [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`euclidean_cluster`](https://furuse.work/ops/3d/segment/euclidean_cluster.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`plane_sdf`](https://furuse.work/ops/3d/sdf_csg/plane_sdf.html) · [`plane_segmentation`](https://furuse.work/ops/3d/segment/plane_segmentation.html) · [`sdf_intersect`](https://furuse.work/ops/3d/sdf_csg/sdf_intersect.html) · [`sdf_subtract`](https://furuse.work/ops/3d/sdf_csg/sdf_subtract.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`voxel_grid_downsample`](https://furuse.work/ops/3d/preprocess/voxel_grid_downsample.html)

## No.2026.086 —— Re-surveying a structure year by year — when the vantage moves, decay appears to advance

[![Re-surveying a structure year by year — when the vantage moves, decay appears to advance](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/01_scene.png)

*↑ **Re-surveying a structure year by year — when the vantage moves, decay appears to advance** ―― A bridge girder (7 planes + 2 cylinders) carries known deflection, section loss, bearing settlement and a crack across three epochs, re-scanned each time from different positions, densities and poses. Re-measuring with zero deterioration already yields a nearest-neighbour "change" of 21.07 mm median and 42.64 mm max, and the false repair volume above a 1 mm threshold (5.098 L) reaches 87 % of the real one (5.882 L). Registering on all points absorbs 0.689 of the mid-span deflection (closed form 2/3) and invents a -1.737 mm uplift at the supports, while the undetermined along-span direction shows up not on the girder planes but only on the bearing cylinder, as a spurious 41.2 mm horizontal shift.*

[![下フランジの暗い窪みが断面欠損、面全体の淡い変化がたわみ。腹板(法線が水平)にはたわみが出ない ——同じ劣化でも面の向きで見え方が変わる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/02_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/02_frames.png)

*↑ The measurement ―― 下フランジの暗い窪みが断面欠損、面全体の淡い変化がたわみ。腹板(法線が水平)にはたわみが出ない ——同じ劣化でも面の向きで見え方が変わる。 (figure labels are in Japanese; the numbers are the same)*

[![同じ構造物を 3 回測る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/03_conditions_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/03_conditions.png)

*↑ 同じ構造物を 3 回測る。*

[![真のたわみは中央 3.00 mm。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/05_scope_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/05_scope.png)

*↑ 真のたわみは中央 3.00 mm。*

[![予測は (ω×(p-c))·n を core 上で積んだだけ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/07_cliff_angle_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/07_cliff_angle.png)

*↑ 予測は (ω×(p-c))·n を core 上で積んだだけ。*

[![押し出し形状の平面は法線に x 成分を持たない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/09_prism_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/09_prism.png)

*↑ 押し出し形状の平面は法線に x 成分を持たない。*

[![動画(640 × 530、15 fps、135 コマ): 橋桁を 2 年で 3 回点検する。左は真の法線方向変化(展開図、真値は 3 時点だけ定義なので点検の間は直線で補間して描いた)、右は法線方向に測った変化で、点検(1 年・2 年)が来](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/12_years_video.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/12_years_video.gif)

*↑ The animation ―― 動画(640 × 530、15 fps、135 コマ): 橋桁を 2 年で 3 回点検する。左は真の法線方向変化(展開図、真値は 3 時点だけ定義なので点検の間は直線で補間して描いた)、右は法線方向に測った変化で、点検(1 年・2 年)が来たときだけ更新される。下段は代表 3 点の時系列(線 = 真値、点 = 測定)。灰の帯は t2 の差の誤差 RMS の ±2 倍(±3.45 mm)で、代表 3 点のうち欠損の谷(真 -21.4 mm)だけが帯を大きく越える。速度の誤差 RMS は 0.863 mm/年 で、1 mm/年 の進行は 2σ = 1.726 mm/年 の下に沈む。*

```
py -3.11 examples/poc_structure_4d_deterioration.py
```

Source: [examples/poc_structure_4d_deterioration.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_structure_4d_deterioration.py)

This run produced **12 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_structure_4d_deterioration)

Ops used (notes): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`chamfer_distance`](https://furuse.work/ops/3d/metrics/chamfer_distance.html) · [`cylinder_sdf`](https://furuse.work/ops/3d/sdf_csg/cylinder_sdf.html) · [`data_to_pixel`](https://furuse.work/ops/annotate/plot/data_to_pixel.html) · [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`euclidean_cluster`](https://furuse.work/ops/3d/segment/euclidean_cluster.html) · [`fit_circle_3d`](https://furuse.work/ops/3d/geometry/fit_circle_3d.html) · [`fit_plane_3d`](https://furuse.work/ops/3d/geometry/fit_plane_3d.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`hausdorff_distance`](https://furuse.work/ops/3d/metrics/hausdorff_distance.html) · [`plane_sdf`](https://furuse.work/ops/3d/sdf_csg/plane_sdf.html) · [`rmse`](https://furuse.work/ops/imgmetrics/fidelity/rmse.html) · [`sdf_intersect`](https://furuse.work/ops/3d/sdf_csg/sdf_intersect.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html) · [`voxel_grid_downsample`](https://furuse.work/ops/3d/preprocess/voxel_grid_downsample.html)

## No.2026.087 —— Restoring what is missing by symmetry — the plane you assume is the lie you get

[![Restoring what is missing by symmetry — the plane you assume is the lie you get](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/01_scene.png)

*↑ **Restoring what is missing by symmetry — the plane you assume is the lie you get** ―― A bilaterally symmetric mask is synthesised so that both the complete shape and the true mirror plane are known, then one side is broken off with a sphere. With the true plane, symmetric restoration reaches 0.81 mm RMS and beats harmonic hole filling (1.60 mm) — but it loses the moment the plane is off by 1.39 deg (84 arcmin) or 1.41 mm. The error is predicted by the surface-normal component of the mirror displacement (4.6 % relative error; the naive 2d sin a misses by 50.6 %), so the cliff follows from geometry alone. Losing 3.1 % of the points already flips the PCA candidate ranking onto a 90-degree-wrong axis, and on a shape that is not truly symmetric the restoration fabricates 3436 mm3 of ornament or erases 3495 mm3 — even with the exact plane.*

[![失われた真値の点から復元点群までの距離(符号なし、6 mm で頭打ち)。対称復元だけが眼窩の形を取り戻す。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/02_restore_error_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/02_restore_error_maps.png)

*↑ The measurement ―― 失われた真値の点から復元点群までの距離(符号なし、6 mm で頭打ち)。対称復元だけが眼窩の形を取り戻す。 (figure labels are in Japanese; the numbers are the same)*

[![崖は alpha = 1.39 deg(84 分角)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/03_angle_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/03_angle_cliff.png)

*↑ 崖は alpha = 1.39 deg(84 分角)。*

[![鏡像点は厳密に 2t 動くが、表面誤差になるのはその法線成分(|n.x| の RMS = 0.50)だけ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/05_offset_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/05_offset_cliff.png)

*↑ 鏡像点は厳密に 2t 動くが、表面誤差になるのはその法線成分(|n.x| の RMS = 0.50)だけ。*

[![欠損のまま推定した面で復元すると、欠損部の全体が一様にずれる(位置ずれの署名)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/07_controls_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/07_controls_maps.png)

*↑ 欠損のまま推定した面で復元すると、欠損部の全体が一様にずれる(位置ずれの署名)。*

[![色は「鏡像 - 真値」。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/09_false_symmetry_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/09_false_symmetry.png)

*↑ 色は「鏡像 - 真値」。*

```
py -3.11 examples/poc_symmetry_restoration.py
```

Source: [examples/poc_symmetry_restoration.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_symmetry_restoration.py)

This run produced **10 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_symmetry_restoration)

Ops used (notes): [`detect_reflection_symmetry`](https://furuse.work/ops/3d/symmetry/detect_reflection_symmetry.html) · [`fill_holes`](https://furuse.work/ops/2d/region/fill_holes.html) · [`fit_plane_3d`](https://furuse.work/ops/3d/geometry/fit_plane_3d.html) · [`icp_point2point_3d`](https://furuse.work/ops/3d/refine/icp_point2point_3d.html) · [`normalize`](https://furuse.work/ops/shape2d/descriptor/normalize.html) · [`reflect_points`](https://furuse.work/ops/3d/symmetry/reflect_points.html) · [`reflection_symmetry_score`](https://furuse.work/ops/3d/symmetry/reflection_symmetry_score.html)

## No.2026.146 —— Endless Zooms and Turning Solids: Making the Return Itself the Ground Truth

[![Endless Zooms and Turning Solids: Making the Return Itself the Ground Truth](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/01_zoom_steps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/01_zoom_steps.png)

*↑ **Endless Zooms and Turning Solids: Making the Return Itself the Ground Truth** ―― Motion that never ends still carries equations you can score without watching it end: an infinite zoom returns to the identical picture once you have zoomed by the self-similarity ratio, and a rotating solid returns after 2 pi. Neither loop is made by cutting back to the first frame; both follow from the construction, so the truth is exactly zero difference. The material is Pascal's triangle mod 2 - the same truth that rule 90 satisfies - and the hierarchy of its gaps has a closed form: with I = floor(u*2^D), J = floor(v*2^D) and b the position of the highest set bit of I & J, the depth is d = D - b. Halving u shifts I right by one, so b drops by one and d rises by exactly one, which is why zooming never costs resolution: every pixel is decided by an integer bit test rather than by magnifying a raster. Over a loop that zooms eight-fold, frame(T) and frame(0) differ by 0.0e+00. The first core finding is that the measured dimension does not move at all under zoom: the existing fractal_dimension operator returns the same value across six zoom levels with a standard deviation of exactly zero, and where the depth of the approximant matches the pixel grid it equals log2(3) = 1.584962500721 to within 8.9e-16 - an agreement, not an approximation. The second is that the same operator returns 0.0 when handed an approximant finer than the pixels; that zero does not mean there is no structure, it means the structure is finer than the sampling, and indeed the level-9 approximant has zero foreground pixels out of 262,144. The third is that 2 pi does not close in floating point: building the rotation from the angle 2*pi*i/T leaves 1.40e-12 in the normals at i = T because sin(2 pi) is -2.45e-16, while closing the period on the integer index instead gives exactly zero. The fourth is a prediction that was wrong and has been left in: the silhouette area of a cube under orthographic projection is a^2(|cos| + |sin|), and the measured two per cent residual was read as the bevel that marching cubes puts on the corners - but pushing the camera from a distance of 6 to 96 dropped the residual from 0.128 to 0.004 for the exact cube and the marching-cubes cube alike, so the floor was perspective, not the mesh. The bevel shows up instead in a quantity that distance does not fix: the ratio of maximum to minimum silhouette area converges to sqrt(2) = 1.4142 for the exact cube but stops at 1.3958 for the extracted surface. Separating one residual into two causes came from sweeping the distance. Two smaller findings: the four-fold symmetry of the depth field is exact while the rendered image breaks it by 1.1e-16, which is the order of summation in a 2x2 average rather than any mathematics; and the two labyrinths of the gyroid have a volume ratio of 0.500000000000, which follows from the odd symmetry. No new operator was added.*

[![右は 2 枚の差をそのまま出したもので、**全画素が 0**(最大差 0.0e+00)。倍率を 8 倍にしたのに同じ絵になるのは、色の巡回(周期 3)が深さの巡回とちょうど噛み合うから。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/02_zoom_seam_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/02_zoom_seam.png)

*↑ The measurement ―― 右は 2 枚の差をそのまま出したもので、**全画素が 0**(最大差 0.0e+00)。倍率を 8 倍にしたのに同じ絵になるのは、色の巡回(周期 3)が深さの巡回とちょうど噛み合うから。 (figure labels are in Japanese; the numbers are the same)*

[![**空隙の深さ(色 = 深さ、深いほど濃い)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/04_zoom_depth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/04_zoom_depth.png)

*↑ **空隙の深さ(色 = 深さ、深いほど濃い)。*

[![左から深さ 5..9。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/06_dimension_vs_level_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/06_dimension_vs_level.png)

*↑ 左から深さ 5..9。*

[![正射影ならシルエット面積は `a²(|cosθ| + |sinθ|)` で、45 度が最大(√2 倍)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/10_cube_steps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/10_cube_steps.png)

*↑ 正射影ならシルエット面積は `a²(|cosθ| + |sinθ|)` で、45 度が最大(√2 倍)。*

[![厳密な立方体は √2 = 1.4142 に収束する(1.4167)のに、marching cubes で取り出した面は **1.3958 で止まる**。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/13_mesh_is_not_a_cube_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/13_mesh_is_not_a_cube.png)

*↑ 厳密な立方体は √2 = 1.4142 に収束する(1.4167)のに、marching cubes で取り出した面は **1.3958 で止まる**。*

[![止めどきは呼んだ側が決める。24 コマで 1 周(8 倍)、そこから先は同じ絵が続く。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/03_zoom_loop.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/03_zoom_loop.gif)

*↑ The animation ―― 止めどきは呼んだ側が決める。24 コマで 1 周(8 倍)、そこから先は同じ絵が続く。*

[![1 周 18 コマ。添字の剰余で角度を作っているので、18 コマ目は 0 コマ目と画素単位で同じ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/08_solid_loop.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/08_solid_loop.gif)

*↑ The animation ―― 1 周 18 コマ。添字の剰余で角度を作っているので、18 コマ目は 0 コマ目と画素単位で同じ。*

```
py -3.11 examples/poc_endless_zoom_and_turning_solids.py
```

Source: [examples/poc_endless_zoom_and_turning_solids.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_endless_zoom_and_turning_solids.py)

This run produced **15 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids)

Ops used (notes): [`fractal_dimension`](https://furuse.work/ops/2d/features/fractal_dimension.html) · [`gyroid_isosurface`](https://furuse.work/ops/3d/surface/gyroid_isosurface.html) · [`mesh_volume`](https://furuse.work/ops/3d/mesh_process/mesh_volume.html) · [`perpetual_loop_seam`](https://furuse.work/ops/generative/loop/perpetual_loop_seam.html) · [`phong_shade`](https://furuse.work/ops/3d/render/phong_shade.html)

## No.2026.149 —— Scoring Four-Dimensional Claims with Ordinary Three-Dimensional Operators

[![Scoring Four-Dimensional Claims with Ordinary Three-Dimensional Operators](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/02_nested_tori_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/02_nested_tori.png)

*↑ **Scoring Four-Dimensional Claims with Ordinary Three-Dimensional Operators** ―― The topology and algebra of four dimensions can be scored exactly by ordinary three-dimensional operators already in the box: fitting a circle to a point cloud, the signed volume of a closed mesh, tube meshing and rasterising. The Hopf fibration splits the three-sphere into circles indexed by points of the two-sphere: viewing a point of S^3 as a pair of complex numbers, the fibre over a point of S^2 is the circle q(t) = (cos(theta/2) e^{it}, sin(theta/2) e^{i(t+phi)}), and stereographic projection carries it to an exact circle in space - a Villarceau circle. The first finding is that a four-dimensional circle becomes a two-dimensional point: pushing one fibre through the Hopf map leaves a spread of 8.9e-16 on the sphere, so all 256 sampled points collapse onto one. The second is that the circle-fitting operator recognises it: the projected radius ranges from 0.70 to 7.34 across latitudes, yet the fit residual and the departure from a single plane both stay in the 1e-14 range - a theorem, not an approximation. The third is that two distinct fibres always link exactly once, that the integer emerges from the Gauss integral, and that even the rate of convergence is predictable: doubling the discretisation divides the error by exactly four, measured at 4.01, 4.00, 4.00 and 4.00, confirming the predicted second order. The fourth concerns rotation: in four dimensions a rotation acts in two planes at once, and the motion closes only for rational ratios. A tesseract - 16 vertices, 32 edges, 24 faces, 8 cells, Euler characteristic exactly 0, hypervolume exactly 16 for edge 2 - turned simultaneously in the xy and zw planes returns after sixty steps for ratios 1:2, 2:3 and 3:4 with a difference of 0.0e+00, while the minimum separation along the way stays above 0.23, so it is not the trivial case of nothing having moved. For the golden ratio, refining the step to 400 and running twenty thousand steps still leaves a minimum separation of 0.0257. The period closes because the angle is built from an integer remainder rather than accumulated arithmetic. The fifth finding separates two sources of error in the volume of a tube. Writing two closed forms - one for a circular cross-section on a circular centreline, one for a regular m-gon cross-section on a circular centreline - makes the discrepancy against the second completely independent of m: for a fixed centreline the three cross-sections agree to 7.8e-16. The cross-section's own contribution then vanishes as 1/m^2 exactly as its closed form says, with ratios 3.99 and 4.00. One prediction was wrong and has been left in: the centreline's contribution was expected to vanish as 1/n^2, but doubling and quadrupling the sample count divides it by only 2.09 and 4.15, that is as 1/n - and since the perimeter of the inscribed polygon converges as 1/n^2, the residue cannot come from the perimeter but from the thickness at the joints. Consequently neither knob alone suffices: 96 sides alone stalls at -0.001588 and 1600 centreline points alone at -0.003064, while turning both reaches -0.000925. No new operator was added.*

[![ホップ束の繊維 4 本を立体射影して管にしたもの。★**4 次元では 4 本とも同じ大きさの円**なのに、3 次元へ写すと大きさが変わる —— それでも `fit_circle_3d` は 4 本すべてを **残差 1.4e-14** で円](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/01_hopf_fibers_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/01_hopf_fibers.png)

*↑ The measurement ―― ホップ束の繊維 4 本を立体射影して管にしたもの。★**4 次元では 4 本とも同じ大きさの円**なのに、3 次元へ写すと大きさが変わる —— それでも `fit_circle_3d` は 4 本すべてを **残差 1.4e-14** で円と認める。どの 2 本も**必ず 1 回だけ絡む**。 (figure labels are in Japanese; the numbers are the same)*

[![`fit_circle_3d` に 200 点を食わせた残差。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/04_circle_fit_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/04_circle_fit.png)

*↑ `fit_circle_3d` に 200 点を食わせた残差。*

[![ガウスの積分で求めた絡み数の、**整数 1** からの差。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/05_linking_vs_n_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/05_linking_vs_n.png)

*↑ ガウスの積分で求めた絡み数の、**整数 1** からの差。*

[![真値 B は「**正 m 角形**断面・円中心線」の体積。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/08_tube_error_split_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/08_tube_error_split.png)

*↑ 真値 B は「**正 m 角形**断面・円中心線」の体積。*

[![断面の効果は閉形式どおり **1/m²**(比 3.99 / 4.00)で消えるのに、中心線の効果は **1/n**(比 2.09 / 4.15)でしか消えない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/09_tube_two_knobs_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/09_tube_two_knobs.png)

*↑ 断面の効果は閉形式どおり **1/m²**(比 3.99 / 4.00)で消えるのに、中心線の効果は **1/n**(比 2.09 / 4.15)でしか消えない。*

[![同じ 4 本を視点だけ回して見たもの。★**視点の周期は角度でなく整数の剰余で閉じている**(24 コマ目が 0 コマ目と同じ式になる)ので、継ぎ目が出ない。絡み方は視点を変えても変わらない —— 絡み数は**位相の量**だから。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/03_hopf_turn.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/03_hopf_turn.gif)

*↑ The animation ―― 同じ 4 本を視点だけ回して見たもの。★**視点の周期は角度でなく整数の剰余で閉じている**(24 コマ目が 0 コマ目と同じ式になる)ので、継ぎ目が出ない。絡み方は視点を変えても変わらない —— 絡み数は**位相の量**だから。*

[![比 **1 : 2**(有理)。60 コマでちょうど元に戻る —— 戻ったときの差は **0.0e+00**。★角度は**整数の剰余**で作っているので、有理な比なら継ぎ目が出ない。描いているのは 4 次元の超立方体を**2 枚の面で同時に](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/06_tesseract_rational.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/06_tesseract_rational.gif)

*↑ The animation ―― 比 **1 : 2**(有理)。60 コマでちょうど元に戻る —— 戻ったときの差は **0.0e+00**。★角度は**整数の剰余**で作っているので、有理な比なら継ぎ目が出ない。描いているのは 4 次元の超立方体を**2 枚の面で同時に回して**から w を落とした影。辺は 32 本とも同じ長さなのに、影では伸び縮みする。*

[![比 **1 : φ**(無理、黄金比)。この 60 コマでは戻らない。別に**刻みを 400 に細かくして 20,000 歩**まで回しても、最小の隔たりは **0.0257** で 0 に落ちない。★角度は**整数の剰余**で作っているの](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/07_tesseract_irrational.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/07_tesseract_irrational.gif)

*↑ The animation ―― 比 **1 : φ**(無理、黄金比)。この 60 コマでは戻らない。別に**刻みを 400 に細かくして 20,000 歩**まで回しても、最小の隔たりは **0.0257** で 0 に落ちない。★角度は**整数の剰余**で作っているので、有理な比なら継ぎ目が出ない。描いているのは 4 次元の超立方体を**2 枚の面で同時に回して**から w を落とした影。辺は 32 本とも同じ長さなのに、影では伸び縮みする。*

```
py -3.11 examples/poc_four_dimensions_by_three_d_tools.py
```

Source: [examples/poc_four_dimensions_by_three_d_tools.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_four_dimensions_by_three_d_tools.py)

This run produced **10 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools)

Ops used (notes): [`curve3d_tube_mesh`](https://furuse.work/ops/3d/surface/curve3d_tube_mesh.html) · [`fit_circle_3d`](https://furuse.work/ops/3d/geometry/fit_circle_3d.html) · [`mesh_volume`](https://furuse.work/ops/3d/mesh_process/mesh_volume.html)




---

**This museum was built together with Claude Code.** I set the questions and the direction; Claude Code did the implementation, the sweeps, the control groups and the adversarial checks. That division of labour is what made it possible to run 53 PoCs and collect their figures in two days. If you want to try it, this invitation link gives you a **one-week free trial**: [claude.ai/referral/0sqPw8E_lw](https://claude.ai/referral/0sqPw8E_lw)

If even one exhibit was worth your time, a **like or a stock** helps: the reactions decide which wing grows next, so tell me in the comments which measurement from your own field you would want to see. And if you swapped in real data and the cliff moved, that is the story I most want to hear.
