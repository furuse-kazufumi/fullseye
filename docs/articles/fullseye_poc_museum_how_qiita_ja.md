> **言語 / Language**: **日本語** · [English](https://qiita.com/furuse-kazufumi/items/9468b213793e3f6b1dc8)

# 紙面の計測館 —— どう測るかの棟(撮像品質・時系列・幾何校正・色・法科学・3-D 形状)

> **[紙面の計測館 総合案内](https://qiita.com/furuse-kazufumi/items/c1606bcfa2085d204ad6)** の一棟です。ほかの棟・用語・テーゼは案内にあります。

この棟には **75 点**を掛けています。番号は**収蔵番号**で、棟を移しても分けても変わりません。

> 各展示の「使用 op」から、その op のノート(型契約・罠・図・Studio で走るプログラム)へ飛べます: [オペレータ目録](https://furuse.work/OP_CATALOG.html) / [op ノートの索引](https://furuse.work/ops/INDEX.html)。

### 撮像品質・復元ウィング ―― 絵が良くなることと真値に近づくことは別

手ブレを戻す、拡大する、霞を剥がす、深度合成する、投影から再構成する、光子を数えて距離を出す。復元の分野は「見た目が良くなった」と「真値に近づいた」が最も混ざりやすい場所です。この部屋の 18 点は、核・深度・大気光・PSD・投影・到達時刻をこちらが決めた合成で、その 2 つを分けて採点しています。

見た目の指標は真値を最大値としません。霞んだ入力の対比が真値より高い、アンシャープで勾配は真値に一致するのに PSNR は落ちる、雑音を足すと PSNR が上がる。逆に、ナイキストより細かい縞を戻したのに PSNR が -0.01 dB しか動かない場面もあります。

共通して置いたゼロ点は「何もしない」です。核の角度が 19.4 度ずれた復元、投影 12 本の FBP、視程 782 m 以上の除霞、無テクスチャ領域の深度。いずれもそのゼロ点に負けます。負ける条件を数字で置くことが、この部屋の展示の中身です。

## No.2026.007 —— 手ブレはどこまで戻せるか ―― 核を自分で作り、掛けて、戻して、元と比べる

[![手ブレはどこまで戻せるか ―― 核を自分で作り、掛けて、戻して、元と比べる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/01_noise_ceiling_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/01_noise_ceiling.png)

*↑ **手ブレはどこまで戻せるか ―― 核を自分で作り、掛けて、戻して、元と比べる** ―― 既知の直線ブレ核を掛けて戻し、雑音と核の推定誤差で上限を測った図。無雑音なら 22.38 → 56.41 dB、SNR 20 dB では取り分 1.82 dB。核の角度が 19.4 度ずれると「何もしない」に抜かれ、回転ブレを 1 枚の核で戻すと回転中心が -49.41 dB 悪化する。*

[![4 枚目は「復元した」形をしているが、ゼロ点(観測そのもの)より悪い。絵の見た目では区別できない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/02_deblur_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/02_deblur.png)

*↑ 測定の図 ―― 4 枚目は「復元した」形をしているが、ゼロ点(観測そのもの)より悪い。絵の見た目では区別できない。*

[![交点が現場で効く数字。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/03_kernel_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/03_kernel_error.png)

*↑ 交点が現場で効く数字。*

[![核を作った右側だけが正。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/04_rotational_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/04_rotational.png)

*↑ 核を作った右側だけが正。*

[![15 px・20 度の直線ブレに SNR 40 dB の雑音を載せた観測を、角度を 0〜30 度ずらした核で Wiener 復元し直していく(正則化量は毎回神託で最良化)。ずれ 0 度で 28.87 dB、20 度で 22.31 dB。0.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/05_kernel_angle_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/05_kernel_angle_sweep.gif)

*↑ 動く図 ―― 15 px・20 度の直線ブレに SNR 40 dB の雑音を載せた観測を、角度を 0〜30 度ずらした核で Wiener 復元し直していく(正則化量は毎回神託で最良化)。ずれ 0 度で 28.87 dB、20 度で 22.31 dB。0.5 度刻みで追うと 19.2 度でアンシャープマスク(22.40 dB)に、19.4 度で「何もしない」(22.38 dB)に抜かれる(本文の表の補間では 19.2 / 19.4 度)。抜かれた後の復元も「復元した」形をしている —— 右の誤差地図でだけ、縞状のリンギングが真値からのずれとして見える。*

```
py -3.11 examples/poc_camera_shake_deblur.py
```

ソース: [examples/poc_camera_shake_deblur.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_camera_shake_deblur.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_camera_shake_deblur)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`psnr`](https://furuse.work/ops/imgmetrics/fidelity/psnr.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`ssim`](https://furuse.work/ops/imgmetrics/fidelity/ssim.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html) · [`unsharp`](https://furuse.work/ops/2d/smoothing/unsharp.html) · [`vol_richardson_lucy`](https://furuse.work/ops/3d/restoration/vol_richardson_lucy.html)

## No.2026.062 —— 疑似カラーは読み手の判断を変える —— 無い境目を数え、位置を先に当てる

[![疑似カラーは読み手の判断を変える —— 無い境目を数え、位置を先に当てる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colormap_readability/05_scene_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colormap_readability/05_scene_maps.png)

*↑ **疑似カラーは読み手の判断を変える —— 無い境目を数え、位置を先に当てる** ―― 段差がゼロと分かっているなめらかな場を塗り、CIE L* と CIEDE2000 で「無い境目」を数えた。jet は 3 本・hsv は 4 本立ち、viridis と gray は 0 本。★立つ位置は sRGB の伝達関数と CIE の Y 係数から解けて、jet の明度折返し予測 0.3750 / 0.4490 / 0.6250 に対し実測 0.3750 / 0.4492 / 0.6250(最大ずれ 0.0002)。本物の段差が偽の境目を追い越すのは jet で 0.296 %FS・viridis で 0.050 %FS(配色の LUT だけからの予測と一致)——jet を選ぶと段差に 5.9 倍の高さが要る。配色より効くのは写し方で、4.3 桁の 1/r² 場では区別できる階調の実効数が linear 1.4 → rank 76.0。★★外れ値を 1 個混ぜると log が 27.4 → 16.3(-41 %)落ち、percentile と rank だけが不変。*

[![平らなら偽の境目は立たない。jet と hsv の山がそのまま『見えてしまう帯』になる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colormap_readability/01_gain_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colormap_readability/01_gain_profile.png)

*↑ 測定の図 ―― 平らなら偽の境目は立たない。jet と hsv の山がそのまま『見えてしまう帯』になる。*

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

ソース: [examples/poc_colormap_readability.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_colormap_readability.py)

この回が作った図は全部で **14 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_colormap_readability)

使用 op(ノートへ): [`delta_e_map`](https://furuse.work/ops/imgmetrics/colordiff/delta_e_map.html) · [`percentile`](https://furuse.work/ops/2d/rank/percentile.html) · [`rgb_to_lab`](https://furuse.work/ops/imgmetrics/colorspace/rgb_to_lab.html)

## No.2026.118 —— ハエの複眼は光場センサ ―― 神経重ね合わせの「重ねると頑健」は膝の手前まで

[![ハエの複眼は光場センサ ―― 神経重ね合わせの「重ねると頑健」は膝の手前まで](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_compound_eye/01_compound_eye_scaling_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_compound_eye/01_compound_eye_scaling.png)

*↑ **ハエの複眼は光場センサ ―― 神経重ね合わせの「重ねると頑健」は膝の手前まで** ―― 個眼アレイを 9×9 のプレノプティック系として合成し、同じ点を N 個眼で重ねたときの SNR 利得を測った図。小開口では √N がほぼ厳密(N=5 で 2.25 対 2.24)だが、大開口では補間誤差が平均で消えず飽和する(N=49 で 5.33 対 7.00)。ハエの R1–R6 の 6 重の重ね合わせは膝の手前にある。距離はアレイでこそ出て(手前 +1.998・奥 +0.499、真値 2.00 / 0.50)、少数派の遮蔽者は median 重ねなら貫ける(隠れ画素の RMS: 中心 1 枚 0.237 → mean 0.065 → median 0.025)。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_compound_eye/02_compound_eye_superposition_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_compound_eye/02_compound_eye_superposition.png)

*↑ 測定の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_compound_eye/03_compound_eye_depth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_compound_eye/03_compound_eye_depth.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_compound_eye/04_compound_eye_occlusion_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_compound_eye/04_compound_eye_occlusion.png)

*↑ この回の図*

```
py -3.11 examples/poc_compound_eye.py
```

ソース: [examples/poc_compound_eye.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_compound_eye.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_compound_eye)

使用 op(ノートへ): [`lf_all_in_focus`](https://furuse.work/ops/lightfield/depth/lf_all_in_focus.html) · [`lf_aperture_mask`](https://furuse.work/ops/lightfield/refocus/lf_aperture_mask.html) · [`lf_depth_from_focus`](https://furuse.work/ops/lightfield/depth/lf_depth_from_focus.html) · [`lf_plenoptic_design`](https://furuse.work/ops/lightfield/depth/lf_plenoptic_design.html) · [`lf_subaperture`](https://furuse.work/ops/lightfield/views/lf_subaperture.html) · [`lf_synthesize`](https://furuse.work/ops/lightfield/synthesis/lf_synthesize.html) · [`lf_synthetic_aperture`](https://furuse.work/ops/lightfield/refocus/lf_synthetic_aperture.html) · [`median`](https://furuse.work/ops/2d/rank/median.html)

## No.2026.010 —— 投影数を減らすと CT 再構成はどこから壊れるか

[![投影数を減らすと CT 再構成はどこから壊れるか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_fidelity/01_recon_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_fidelity/01_recon_sweep.png)

*↑ **投影数を減らすと CT 再構成はどこから壊れるか** ―― Shepp-Logan を 180 → 12 本で撮り直し、FBP を空白画像と無フィルタ逆投影の 2 つの零点と並べた図。12 本の FBP(RMSE 0.2576)は空白画像(0.2420)より悪い。サイノグラムの行和という再構成を見ない検算が、RMSE では見えない質量欠損 -3.34 % を捕まえ、ランプフィルタの DC ビンを直して -0.0099 % に。*

[![RMSE で見ると 12 本は空白画像 0.2420 より悪い。相関とストリークは別のことを言う。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_fidelity/02_fidelity_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_fidelity/02_fidelity_table.png)

*↑ 測定の図 ―― RMSE で見ると 12 本は空白画像 0.2420 より悪い。相関とストリークは別のことを言う。*

[![零点 A = 空白画像、零点 B = 無フィルタ逆投影(どちらも水平・ほぼ水平)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_fidelity/03_rmse_vs_views_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_fidelity/03_rmse_vs_views.png)

*↑ 零点 A = 空白画像、零点 B = 無フィルタ逆投影(どちらも水平・ほぼ水平)。*

```
py -3.11 examples/poc_ct_fidelity.py
```

ソース: [examples/poc_ct_fidelity.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_fidelity.py)

この回が作った図は全部で **3 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_ct_fidelity)

使用 op(ノートへ): [`backproject_sinogram`](https://furuse.work/ops/tomography/reconstruct/backproject_sinogram.html) · [`ellipse_phantom`](https://furuse.work/ops/tomography/forward/ellipse_phantom.html) · [`ellipse_sinogram`](https://furuse.work/ops/tomography/forward/ellipse_sinogram.html) · [`filtered_backprojection`](https://furuse.work/ops/tomography/reconstruct/filtered_backprojection.html) · [`projection_angles`](https://furuse.work/ops/tomography/layout/projection_angles.html) · [`radon_transform`](https://furuse.work/ops/tomography/forward/radon_transform.html) · [`rmse`](https://furuse.work/ops/imgmetrics/fidelity/rmse.html) · [`ssim`](https://furuse.work/ops/imgmetrics/fidelity/ssim.html) · [`stat_correlation`](https://furuse.work/ops/math/stats/stat_correlation.html)

## No.2026.011 —— 霞を剥がす ―― 大気散乱モデルで真値を作り、透過率と大気光を別々に採点する

[![霞を剥がす ―― 大気散乱モデルで真値を作り、透過率と大気光を別々に採点する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/01_scene.png)

*↑ **霞を剥がす ―― 大気散乱モデルで真値を作り、透過率と大気光を別々に採点する** ―― 深度・大気光・消散係数から真の透過率とシーンを持った霞画像を作り、除霞を採点した図。全体 +4.04 dB の中身は近景 -1.49 dB の劣化を中景 +4.03 / 遠景 +11.28 dB が覆ったもの。視程 782 m 以上では除霞が害になり、雑音を足すと PSNR が上がる(偶然の打ち消し)。*

[![空では過大評価(明るい側)、近景では過小評価(暗い側)。全体の平均バイアスでは打ち消し合って見えない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/02_transmission_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/02_transmission.png)

*↑ 測定の図 ―― 空では過大評価(明るい側)、近景では過小評価(暗い側)。全体の平均バイアスでは打ち消し合って見えない。*

[![全体 +4.04 dB の正体。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/03_bands_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/03_bands.png)

*↑ 全体 +4.04 dB の正体。*

[![左端(薄い霞 = 視程が長い側)で利得が 0 を割る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/04_haze_density_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/04_haze_density.png)

*↑ 左端(薄い霞 = 視程が長い側)で利得が 0 を割る。*

[![動画(110 コマ、120 × 160 px を 2 倍で表示): 消散係数 beta を 0.0025(視程 1565 m)から 0.08(視程 49 m)まで連続に振る。上段は霞んだ観測・暗チャネル除霞・真値、下段は推定した透過率・真の](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/05_haze_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/05_haze_sweep.gif)

*↑ 動く図 ―― 動画(110 コマ、120 × 160 px を 2 倍で表示): 消散係数 beta を 0.0025(視程 1565 m)から 0.08(視程 49 m)まで連続に振る。上段は霞んだ観測・暗チャネル除霞・真値、下段は推定した透過率・真の透過率と、暗チャネル除霞の PSNR 利得(対 何もしない)の曲線。利得は beta ≦ 0.0065(視程 606 m 以上)で負 = 薄い霞では除霞が害になる(5 節の 7 点の表では 0.0050 と 0.0075 の間)。濃霧の端では +2.98 dB。真の A と t を与えたオラクルの PSNR は中央上の板に併記。表示は 8 bit に丸めた観測をそのまま使っている。*

```
py -3.11 examples/poc_dehazing.py
```

ソース: [examples/poc_dehazing.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dehazing.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_dehazing)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`clahe`](https://furuse.work/ops/2d/gray/clahe.html) · [`equalize`](https://furuse.work/ops/2d/gray/equalize.html) · [`image_entropy`](https://furuse.work/ops/imgmetrics/information/image_entropy.html) · [`joint_bilateral`](https://furuse.work/ops/3d/depth_denoise/joint_bilateral.html) · [`nice_ticks`](https://furuse.work/ops/annotate/plot/nice_ticks.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`psnr`](https://furuse.work/ops/imgmetrics/fidelity/psnr.html) · [`rank_image`](https://furuse.work/ops/2d/rank/rank_image.html) · [`ssim`](https://furuse.work/ops/imgmetrics/fidelity/ssim.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html)

## No.2026.016 —— 光子を数えて距離を測る ―― 何個数えれば何ミリまで出るのか

[![光子を数えて距離を測る ―― 何個数えれば何ミリまで出るのか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/01_histograms_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/01_histograms.png)

*↑ **光子を数えて距離を測る ―― 何個数えれば何ミリまで出るのか** ―― 往復時刻にガウシアンをビン積分で置き Poisson 標本を引いた到達時刻ヒストグラムから距離を読む図。N = 200 光子でピーク位置そのまま 11.02 mm、ゲート重心 2.29 mm、理論限界 31.83 mm/√N に 1.00〜1.07 倍で乗る。背景が入ると素の重心は 2 桁崩れ(SBR 0.031 で 564 mm)、族が推すガウス当てはめ 8.82 mm は利用者が 6 行で書くゲート重心に負ける。*

[![背景が無ければ素の重心で足りる。背景が入ると 2 桁崩れ、docstring が勧める背景減算でも戻らない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/02_methods_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/02_methods.png)

*↑ 測定の図 ―― 背景が無ければ素の重心で足りる。背景が入ると 2 桁崩れ、docstring が勧める背景減算でも戻らない。*

[![ゲート重心は CRB に寄り添って落ちる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/03_crb_scaling_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/03_crb_scaling.png)

*↑ ゲート重心は CRB に寄り添って落ちる。*

[![素の推定は μ にほぼ比例して手前へずれる(5 光子/サイクルで -34.5 mm)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/04_pileup_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/04_pileup.png)

*↑ 素の推定は μ にほぼ比例して手前へずれる(5 光子/サイクルで -34.5 mm)。*

```
py -3.11 examples/poc_dtof_ranging.py
```

ソース: [examples/poc_dtof_ranging.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dtof_ranging.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_dtof_ranging)

使用 op(ノートへ): [`dtof_cube_depth`](https://furuse.work/ops/photon/dtof/dtof_cube_depth.html) · [`dtof_cube_simulate`](https://furuse.work/ops/photon/dtof/dtof_cube_simulate.html) · [`dtof_depth`](https://furuse.work/ops/photon/dtof/dtof_depth.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`tcspc_background_subtract`](https://furuse.work/ops/photon/tcspc/tcspc_background_subtract.html) · [`tcspc_coates_correct`](https://furuse.work/ops/photon/spad/tcspc_coates_correct.html) · [`tcspc_simulate`](https://furuse.work/ops/photon/tcspc/tcspc_simulate.html)

## No.2026.119 —— ハエの視覚前段を op の連鎖で ―― 合成の空を回る/前進すると、何が読めて何が読めないか

[![ハエの視覚前段を op の連鎖で ―― 合成の空を回る/前進すると、何が読めて何が読めないか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_vision/01_fly_vision_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_vision/01_fly_vision_scene.png)

*↑ **ハエの視覚前段を op の連鎖で ―― 合成の空を回る/前進すると、何が読めて何が読めないか** ―― 六角格子 721 個眼 → 受容野 → ラミナの DC 落とし → Hassenstein-Reichardt 相関器 → HS 対向和を繋いだ 1 匹の眼で、1/f の帯つき空を回る図。自己回転の向きと波形は読める(真の角速度との相関 +0.785、膜 LP つき +0.880、符号一致 0.92)が、ラミナ段の DC 落としを省くと相関器は DC × 高域通過の揺れを出して +0.504 に落ちる。回転せずに前進すると全視野の読み出しは −0.689 の「回転」に化け、上半視野に限っても受容野が地平線をまたぐぶん −0.221 が漏れる(el>2Δρ で 0.000)。対向比は速さを落とすので、20 m 先のドームの 1.4°/s の流れも −0.612 に読む。LGMD η のピークは衝突の α·l/|v| 前(−0.1570 s、予測 −0.1567 s)で θ=23.97°(予測 24.02°、球の厳密な見込み角なら 4 次式の根で 24.6°)、τ 球式は d/|v| に RMS 1e-5 s で乗り、円板式の誤用は θ=60° で cos²(θ/2)=0.75 倍。12 方位の縞で DSI 0.798、好む向き 0°。*

[![相関 +0.785(膜 LP つき +0.880、ラミナ段なし +0.504)。対向比は符号の一致度なので、尺度 k は最小二乗で合わせてある。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_vision/02_fly_vision_rotation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_vision/02_fly_vision_rotation.png)

*↑ 測定の図 ―― 相関 +0.785(膜 LP つき +0.880、ラミナ段なし +0.504)。対向比は符号の一致度なので、尺度 k は最小二乗で合わせてある。*

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

ソース: [examples/poc_fly_vision.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_fly_vision.py)

この回が作った図は全部で **6 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_fly_vision)

使用 op(ノートへ): [`fly_dsi`](https://furuse.work/ops/flyvision/tuning/fly_dsi.html) · [`fly_emd_response`](https://furuse.work/ops/flyvision/motion/fly_emd_response.html) · [`fly_hex_lattice`](https://furuse.work/ops/flyvision/lattice/fly_hex_lattice.html) · [`fly_hex_resample`](https://furuse.work/ops/flyvision/sample/fly_hex_resample.html) · [`fly_hs_readout`](https://furuse.work/ops/flyvision/integrate/fly_hs_readout.html) · [`fly_lgmd_eta`](https://furuse.work/ops/flyvision/looming/fly_lgmd_eta.html) · [`fly_sky_1f`](https://furuse.work/ops/flyvision/stimulus/fly_sky_1f.html) · [`fly_tau_from_expansion`](https://furuse.work/ops/flyvision/looming/fly_tau_from_expansion.html)

## No.2026.019 —— 深度合成 ―― 全焦点画像と深度地図は別物

[![深度合成 ―― 全焦点画像と深度地図は別物](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/01_stack_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/01_stack.png)

*↑ **深度合成 ―― 全焦点画像と深度地図は別物** ―― 錯乱円の閉形式で深さに応じたぼけを掛けた 15 枚から、全焦点画像と深度地図を取り出した図。全焦点は 35.89 dB(ゼロ点 20.98 dB)なのに、同じ融合の深度は無テクスチャ領域でゼロ点に 8 倍負ける(0.13 倍)。相対量の信頼度は無テクスチャで 0.9923 と有テクスチャの 0.9630 より高く出る ―― 絶対値(23600 倍差)で棄却すると RMS 1.505 → 0.878 mm。*

[![合焦点法は全焦点画像と同時に距離画像も出す。ただし左下の無テクスチャの四角だけ、誤差が掃引全域にばらけた乱数になっている(段差帯のハローも見える)—— 絵ほど距離は当てにならない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/02_depth_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/02_depth_map.png)

*↑ 測定の図 ―― 合焦点法は全焦点画像と同時に距離画像も出す。ただし左下の無テクスチャの四角だけ、誤差が掃引全域にばらけた乱数になっている(段差帯のハローも見える)—— 絵ほど距離は当てにならない。*

[![左下の無テクスチャの四角が、相対量(0.90-1.00 に切って表示)では最も明るい = 自信ありに見え、絶対量(対数)でだけ「何も見えていない」と出る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/03_confidence_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/03_confidence.png)

*↑ 左下の無テクスチャの四角が、相対量(0.90-1.00 に切って表示)では最も明るい = 自信ありに見え、絶対量(対数)でだけ「何も見えていない」と出る。*

[![2 本が離れていく = 残りの誤差は標本化ではなく焦点評価が持っている。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/04_frames_floor_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/04_frames_floor.png)

*↑ 2 本が離れていく = 残りの誤差は標本化ではなく焦点評価が持っている。*

[![焦点を 196.23〜203.00 mm で 17 枚掃引し、1 枚進むたびに「ここまでで焦点評価が最大のフレーム」を画素ごとに選び直す。左 = いまの 1 枚(橙 = この 1 枚で最良が更新された画素)、中 = ここまでの全焦点画像、右](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/05_focus_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/05_focus_sweep.gif)

*↑ 動く図 ―― 焦点を 196.23〜203.00 mm で 17 枚掃引し、1 枚進むたびに「ここまでで焦点評価が最大のフレーム」を画素ごとに選び直す。左 = いまの 1 枚(橙 = この 1 枚で最良が更新された画素)、中 = ここまでの全焦点画像、右 = ここまでの距離画像。全焦点画像の PSNR は 22.17 dB から 33.69 dB へ育ち、中央の 1 枚(28.52 dB)を上回る。一方、左下の無地の四角は最後まで掃引のたびに塗り替わり(最後の 1 枚でも無地の 12 % が入れ替わる。テクスチャ有は 4 %)、距離誤差は 2.203 mm(テクスチャ有 0.467 mm)で終わる。*

```
py -3.11 examples/poc_focus_stacking.py
```

ソース: [examples/poc_focus_stacking.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_focus_stacking.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_focus_stacking)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`csi_height_map`](https://furuse.work/ops/interferometry/surface/csi_height_map.html) · [`defocus_blur`](https://furuse.work/ops/optics/scene/defocus_blur.html) · [`dilation_circle`](https://furuse.work/ops/2d/region/dilation_circle.html) · [`fuse`](https://furuse.work/ops/3d/tsdf_fusion/fuse.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`laplace`](https://furuse.work/ops/2d/edges/laplace.html) · [`mean_image`](https://furuse.work/ops/2d/smoothing/mean_image.html) · [`optical_camera`](https://furuse.work/ops/optics/scene/optical_camera.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`psnr`](https://furuse.work/ops/imgmetrics/fidelity/psnr.html) · [`sobel_amp`](https://furuse.work/ops/2d/edges/sobel_amp.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html) · [`xcv2_lap_var`](https://furuse.work/ops/2d/features/xcv2_lap_var.html)

## No.2026.023 —— ライトフィールドから深度を出す ―― 既知の深度で作った光場に、ゼロ点を並べて突きつける

[![ライトフィールドから深度を出す ―― 既知の深度で作った光場に、ゼロ点を並べて突きつける](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/01_scene_and_depth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/01_scene_and_depth.png)

*↑ **ライトフィールドから深度を出す ―― 既知の深度で作った光場に、ゼロ点を並べて突きつける** ―― 9×9 の光場を解析的な逆写像で描き、真値スロープ地図に対して焦点度・EPI・2 眼ブロックマッチングを採点した図。定数ゼロ点には 22 倍勝つが、視点 2 枚だけ使う 2 眼に対しては cubic でようやく 1.6 倍。既定の linear 補間は整数スロープに吸着し、真値 1.30 を 1.4750 と読む(深度で 11.9 %)。*

[![linear は 1.08/1.15 を 1.0 へ、1.85 を 2.0 側へ引く。cubic は恒等線に乗る。生成側の補間はゼロ(Fourier シフト)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/02_focus_snapping_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/02_focus_snapping.png)

*↑ 測定の図 ―― linear は 1.08/1.15 を 1.0 へ、1.85 を 2.0 側へ引く。cubic は恒等線に乗る。生成側の補間はゼロ(Fourier シフト)。*

[![EPI は SNR 20 で既に -35 %。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/03_texture_breakdown_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/03_texture_breakdown.png)

*↑ EPI は SNR 20 で既に -35 %。*

[![境界から 5 px 離れれば内側の水準に戻る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/04_occlusion_bands_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/04_occlusion_bands.png)

*↑ 境界から 5 px 離れれば内側の水準に戻る。*

```
py -3.11 examples/poc_lightfield_depth.py
```

ソース: [examples/poc_lightfield_depth.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_lightfield_depth.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_lightfield_depth)

使用 op(ノートへ): [`lf_depth_from_focus`](https://furuse.work/ops/lightfield/depth/lf_depth_from_focus.html) · [`lf_disparity_to_depth`](https://furuse.work/ops/lightfield/depth/lf_disparity_to_depth.html) · [`lf_epi`](https://furuse.work/ops/lightfield/views/lf_epi.html) · [`lf_epi_slope`](https://furuse.work/ops/lightfield/depth/lf_epi_slope.html) · [`lf_refocus`](https://furuse.work/ops/lightfield/refocus/lf_refocus.html)

## No.2026.105 —— 実写のブレを取る ―― 3 つの物差しに、3 人の勝者

[![実写のブレを取る ―― 3 つの物差しに、3 人の勝者](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_deblur_honesty/01_restore_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_deblur_honesty/01_restore.png)

*↑ **実写のブレを取る ―― 3 つの物差しに、3 人の勝者** ―― 真値を実写そのもの(scikit-image camera、CC0)にして、劣化だけ自分で作る(直線ブレ 11 px・20 度 + 雑音 σ=0.004)。★ゼロ点(何もしない)が 24.04 dB と強く、よく使われる nsr=0.005 の Wiener は 23.66 dB で**負ける**。★★ただしそこで止めると相手を弱く見せたことになる ―― nsr を振ると 0.0005 で 19.18 dB、0.02 で 25.40 dB。**ノブを固定した比較は比較ではない**。★★しかもノブで動く幅 6.22 dB は、脱畳み込みをするかしないかの差 1.36 dB の **4.6 倍** ―― 手法よりノブが効く。★★同じ 7 通りの結果に 3 つの物差しを当てると、**別々の手法が 1 位**になる: PSNR は正しい PSF の Wiener(25.40 dB)、勾配エネルギーは motion_deblur(0.2986 = 真値 0.1936 の 1.54 倍、**真値より鋭い絵が選ばれる**)、blur_effect は unsharp。参照なし指標が選ぶ手法は PSNR で **4.98 dB / 3.26 dB 損**をする(なお blur_effect は真値そのものは正しく最良と判定する ―― 「ぼけているか」は測れていて、それでも選ばせると損をする)。★長さを 11→21 px と間違えた PSF は 18.56 dB(ゼロ点より -5.48 dB)なのに勾配は真値の 1.37 倍で「よく効いた」ように見える。★崖: 雑音 σ=0.016 で利得は +0.05 dB(1.6 % の雑音で脱畳み込みは何も買わない)、ブレ長の利得は L=5 が山で両端で落ちる(小さいブレは取るものが無く、大きいブレは情報が消えている)。*

[![固定した nsr で比べると、正しい PSF でもゼロ点に負ける。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_deblur_honesty/02_nsr_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_deblur_honesty/02_nsr.png)

*↑ 測定の図 ―― 固定した nsr で比べると、正しい PSF でもゼロ点に負ける。*

[![σ=0 で +1.52 dB、σ=0.016 で +0.05 dB。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_deblur_honesty/03_cliffs_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_deblur_honesty/03_cliffs.png)

*↑ σ=0 で +1.52 dB、σ=0.016 で +0.05 dB。*

[![参照なし指標が選ぶ手法は PSNR で 3〜5 dB 劣る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_deblur_honesty/04_metrics_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_deblur_honesty/04_metrics.png)

*↑ 参照なし指標が選ぶ手法は PSNR で 3〜5 dB 劣る。*

```
py -3.11 examples/poc_real_deblur_honesty.py
```

ソース: [examples/poc_real_deblur_honesty.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_deblur_honesty.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_real_deblur_honesty)

使用 op(ノートへ): [`iv_motion_deblur`](https://furuse.work/ops/2d/restoration/iv_motion_deblur.html) · [`iv_richardson_lucy`](https://furuse.work/ops/2d/restoration/iv_richardson_lucy.html) · [`iv_unsharp_deblur`](https://furuse.work/ops/2d/restoration/iv_unsharp_deblur.html) · [`psnr`](https://furuse.work/ops/imgmetrics/fidelity/psnr.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`sk_blur_effect`](https://furuse.work/ops/2d/features/sk_blur_effect.html) · [`unsharp`](https://furuse.work/ops/2d/smoothing/unsharp.html)

## No.2026.039 —— 超解像は情報を増やすのか ―― 真値を持ったまま縮小して、戻して、数える

[![超解像は情報を増やすのか ―― 真値を持ったまま縮小して、戻して、数える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/03_multiframe_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/03_multiframe.png)

*↑ **超解像は情報を増やすのか ―― 真値を持ったまま縮小して、戻して、数える** ―― 真値を縮小して観測を作り、単一画像拡大・逆投影・drizzle を分解能の列で採点した図。単一画像の拡大は bicubic のゼロ点を最大 +0.036 dB しか上回れない。副画素ずれのある 16 枚の drizzle は標本化不足の条件で +13.96 dB、ナイキスト超えの周期 6 の変調度が 0.03 → 0.38 に立ち上がる。*

[![鮮鋭化だけがナイキスト(周期 8)より細かい列にも縞を作る。それは分解能ではなく**無い縞**。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/01_upscale_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/01_upscale.png)

*↑ 測定の図 ―― 鮮鋭化だけがナイキスト(周期 8)より細かい列にも縞を作る。それは分解能ではなく**無い縞**。*

[![IBP は周期 12 以上の落ちた変調を戻すが、8 より細かい列は1 本も戻らない(順モデルの零空間)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/02_modulation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/02_modulation.png)

*↑ IBP は周期 12 以上の落ちた変調を戻すが、8 より細かい列は1 本も戻らない(順モデルの零空間)。*

[![上限の線がレンズの許す限界。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/04_multiframe_modulation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/04_multiframe_modulation.png)

*↑ 上限の線がレンズの許す限界。*

[![動画(61 コマ、縞の群を 2 倍で表示): 前半は単一画像の IBP を 0 → 24 回。周期 12 の変調度は 0.78 → 0.96 と戻るが、ナイキスト(周期 8)より細かい列の最大は 0.03 → 0.04 にとどまる —— 順](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/05_growth.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/05_growth.gif)

*↑ 動く図 ―― 動画(61 コマ、縞の群を 2 倍で表示): 前半は単一画像の IBP を 0 → 24 回。周期 12 の変調度は 0.78 → 0.96 と戻るが、ナイキスト(周期 8)より細かい列の最大は 0.03 → 0.04 にとどまる —— 順モデルの零空間に落ちた縞は何回回しても立たない(PSNR も 21.10 → 21.09 dB で動かない)。後半は標本化不足(σ = 0.30)の 16 枚を 1 枚ずつ drizzle に足す(ずれは相互相関で推定、pixfrac は枚数に合わせて 1.0 → 0.4、被覆の穴は単一画像の bicubic で埋めて割合を表示)。周期 6 の変調度は単一画像の 0.03 から 16 枚で 0.38 まで立ち上がる(レンズの上限 0.46)。PSNR は 28.27 → 42.24 dB。*

```
py -3.11 examples/poc_superresolution_limits.py
```

ソース: [examples/poc_superresolution_limits.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_superresolution_limits.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_superresolution_limits)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`data_to_pixel`](https://furuse.work/ops/annotate/plot/data_to_pixel.html) · [`drizzle_resample`](https://furuse.work/ops/astrostack/stack/drizzle_resample.html) · [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`psnr`](https://furuse.work/ops/imgmetrics/fidelity/psnr.html) · [`ssim`](https://furuse.work/ops/imgmetrics/fidelity/ssim.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html) · [`unsharp`](https://furuse.work/ops/2d/smoothing/unsharp.html) · [`vol_fft_lowpass`](https://furuse.work/ops/3d/frequency/vol_fft_lowpass.html) · [`vol_resize`](https://furuse.work/ops/3d/geom_transform/vol_resize.html) · [`volume_downsample`](https://furuse.work/ops/3d/preprocess/volume_downsample.html)

## No.2026.194 —— 公開の正解で画質指標を測る ―― TID2013 の 3,000 枚 × 971 人の MOS と作者の公表値を門にする

[![公開の正解で画質指標を測る ―― TID2013 の 3,000 枚 × 971 人の MOS と作者の公表値を門にする](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_iqa_tid2013/06_tid2013_pair_ssim_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_iqa_tid2013/06_tid2013_pair_ssim_map.png)

*↑ **公開の正解で画質指標を測る ―― TID2013 の 3,000 枚 × 971 人の MOS と作者の公表値を門にする** ―― 「自作の罠を自分で解くのは限界」を受けて、真値を外から持ち込む画像側の第 1 弾。真値 = TID2013(Ponomarenko ほか、25 参照 × 24 歪み × 5 水準 = 3,000 枚、971 人の MOS)、基準 = 作者が配布物に同梱した 14 指標の値(psnr.txt / ssim.txt …)と公表の順位相関表。新モジュール iqatid(11 op): 作者の輝度規約 = BT.601 limited-range の整数 Y′(ページに明記が無く、実測で特定。full-range だと 1.321 dB ずれる)、平均順位の Spearman と τ_b の Kendall(公表 14 本の表はこの 2 つで再現できる)、公表表、台帳の読みと検証(3,000 行・名前の集合がディスクと一致・大文字小文字無視)、評価・作者値との比較・歪み種 24 ごとの相関。図は MOS vs PSNR / SSIM の散布、歪み種ごとの SROCC(局所ブロック歪み 0.15 / 0.63、コントラスト 0.44 / 0.45、彩度 0.22 / 0.22 が弱い)、作者値との差のヒストグラム、14 指標の公表・再現・Fullseye 値の表、1 組の参照・歪み・SSIM マップ。門 21 本: 順位相関の閉形式(単調 1・反転 −1・同順位の手計算 ρ = 8.5/√95・τ_b = 7/√90、graphinv の第 2 実装と 1e-12)、Y′ の端点 16 / 235、PSNR の +1 LSB = 48.13 dB、SSIM 恒等 1、公表表 14 本。実データ 3,000 組(110 s): Fullseye の PSNR(RGB)は作者の PSNRc と 4 桁一致(max 0.00005 dB)、輝度 PSNR は参照 I12 以外の 2,774 組で max 0.00017 dB(I12 の 115 組は 28 画素の輝度が丁度 .5 で丸めの向きが食い違い 0.00058 dB —— 黙って除外せず 2 つの門に分けた)、SSIM(Y′)は max 0.000051、順位相関 PSNR 0.6395 / 0.4699(公表 0.640 / 0.470)・SSIM 0.6370 / 0.4635(0.637 / 0.464)、作者値 14 本の再現の最大差 0.00048。作者は輝度 PSNR の完全一致を 100000.0 と書く(111 行、全部 彩度変化)。正直に: 4 桁一致は作者と同じ原実装(旧 ssim_index.m 相当、11×11 ガウス σ1.5、縁を落とす、ダウンサンプル無し)の規約を踏んだからで、SSIM の性能(14 本中 10 位)の話ではない。FSIM / FSIMc / VIF / GMSD は未実装で公表値だけ表に出す。画像と MOS は repo に入れない(研究・教育目的のみの配布条件、FULLSEYE_TID2013_DATA)。CI では合成の門だけ走る。*

[![971 人の MOS と Fullseye の PSNR(作者の輝度規約 Y′、psnr.txt と 4 桁一致)。順位相関は公表値どおり低い —— PSNR は歪み種が混ざると主観に合わない。 彩度変化で Y′ が変わらない 106 組(](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_iqa_tid2013/01_tid2013_mos_vs_psnr_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_iqa_tid2013/01_tid2013_mos_vs_psnr.png)

*↑ 測定の図 ―― 971 人の MOS と Fullseye の PSNR(作者の輝度規約 Y′、psnr.txt と 4 桁一致)。順位相関は公表値どおり低い —— PSNR は歪み種が混ざると主観に合わない。 彩度変化で Y′ が変わらない 106 組(PSNR = inf、MOS 3.4〜6.0)は図に載らない(順位相関には最大の順位で入れてある)。*

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

ソース: [examples/poc_iqa_tid2013.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_iqa_tid2013.py)

この回が作った図は全部で **6 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_iqa_tid2013)

使用 op(ノートへ): [`luma_limited_u8`](https://furuse.work/ops/imgmetrics/iqa/luma_limited_u8.html) · [`psnr`](https://furuse.work/ops/imgmetrics/fidelity/psnr.html) · [`rank_data`](https://furuse.work/ops/imgmetrics/iqa/rank_data.html) · [`rank_kendall_b`](https://furuse.work/ops/imgmetrics/iqa/rank_kendall_b.html) · [`rank_spearman`](https://furuse.work/ops/imgmetrics/iqa/rank_spearman.html) · [`ssim`](https://furuse.work/ops/imgmetrics/fidelity/ssim.html) · [`ssim_map`](https://furuse.work/ops/imgmetrics/fidelity/ssim_map.html) · [`tid2013_by_distortion`](https://furuse.work/ops/imgmetrics/iqa/tid2013_by_distortion.html) · [`tid2013_compare`](https://furuse.work/ops/imgmetrics/iqa/tid2013_compare.html) · [`tid2013_evaluate`](https://furuse.work/ops/imgmetrics/iqa/tid2013_evaluate.html) · [`tid2013_index`](https://furuse.work/ops/imgmetrics/iqa/tid2013_index.html) · [`tid2013_metric_values`](https://furuse.work/ops/imgmetrics/iqa/tid2013_metric_values.html) · [`tid2013_published`](https://furuse.work/ops/imgmetrics/iqa/tid2013_published.html) · [`tid2013_root`](https://furuse.work/ops/imgmetrics/iqa/tid2013_root.html)

## No.2026.197 —— 知覚指標 FSIM / FSIMc / GMSD / VIF を外から来た真値で 4 桁一致させる ―― TID2013 の作者値ファイル 3 本と公表の順位相関表

[![知覚指標 FSIM / FSIMc / GMSD / VIF を外から来た真値で 4 桁一致させる ―― TID2013 の作者値ファイル 3 本と公表の順位相関表](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_iqa_fsim_gmsd_vif/01_iqa_tid2013_mos_vs_fsim_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_iqa_fsim_gmsd_vif/01_iqa_tid2013_mos_vs_fsim.png)

*↑ **知覚指標 FSIM / FSIMc / GMSD / VIF を外から来た真値で 4 桁一致させる ―― TID2013 の作者値ファイル 3 本と公表の順位相関表** ―― IQA 系列の第 2 弾(第 1 弾 = PSNR / SSIM)。第 1 弾が「未実装で公表値だけ表に」していた FSIM / FSIMc / VIFP を numpy + scipy だけで実装し(新モジュール iqafsim 7 op: fsim / fsimc / fsim_pair / gmsd / gmsd_map / vifp / phase_congruency_pc)、配布物に無い GMSD も足した。一次情報は論文 4 本: FSIM = Zhang, Zhang, Mou, Zhang, IEEE TIP 2011(位相一致は Kovesi 1999、公開コードは MIT なので雑音しきい値の経験則はそこから)、GMSD = Xue, Zhang, Mou, Bovik, IEEE TIP 2014、VIF = Sheikh & Bovik, IEEE TIP 2006 の画素領域版(TID2013 論文の「VIFP」。steerable 版の「VIF」は別行で未実装)。FSIM 作者コードは研究・教育目的のみなので移植せず、論文の式から書いて定数が §IV-A と同じことだけ確かめた。真値は 3 段。(1) 作者値ファイル FSIMc.txt / FSIM.txt / VIFP.txt(3,000 行 × 4 桁)と行ごと: max |差| 5.0e-5 / 5.0e-5 / 6.8e-5 ―― 4 桁の丸め幅の中。(2) TID2013 論文 Table 4/5 の順位相関 4 桁: 丸めない自前の値で FSIM 0.8008 / 0.6295(論文 0.8007 / 0.6300)、FSIMc 0.8510 / 0.6665(0.8510 / 0.6669)、VIFP 0.6080 / 0.4560(0.6084 / 0.4567)、作者と同じ 4 桁丸めをすると 3 本とも Full と 7 部分集合(Noise / Actual / Simple / Exotic / New / Color / Full)で Δ 0.0000。(3) GMSD は作者値が無く(配布物 2013 年、GMSD 2014 年)、二次資料(Nafchi ほか 2016)の |ρ| 0.8044 / 0.6339 に 0.0006 / 0.0005 ―― 1 段低い等級として表に明記。入力の規約は実測で特定(どのページにも書かれていない): FSIM.txt と VIFP.txt は PSNR / SSIM と同じ Y′ limited(16–235 の整数)の灰色画像、FSIMc.txt は色 BMP → YIQ full range。つまり FSIM.txt は FSIMc 計算の中の FSIM 成分ではない(色画像の Y で FSIM を測ると max 0.0318 ずれる ―― 反例を門に)。図は MOS 散布 4 枚(題に SROCC と公表値)、歪み種 24 の SROCC の棒(18 彩度変化で輝度だけの 3 指標が崩れ FSIMc だけ残る)、真値の等級を列にした表。門 26 本(合成 10 + 既定の実データ 6 + --full の 10): 恒等 FSIM = FSIMc = 1・GMSD = 0・VIF = 1、雑音 σ で単調(順位相関 ∓1)、FSIM / GMSD の対称と VIF の非対称(参照の情報量で割る)、位相一致の利得不変(ε = 1e-12 で 1e-10、既定 ε = 1e-4 の残差 2.8e-5 は ε に厳密比例)、偶数核の 'same' の規約、round(1.5) = 2、第 2 実装(既存のモノジェニック位相一致)との相関 0.66、GMS 値域と VIF > 1(コントラスト強調、作者値の最大 1.1379 も歪み 17)、fail-closed、公表表の 4 桁と 3 桁の整合、実データの行ごと 3 本・反例・GMSD の負の相関・歪み種別。既定は先頭 120 組(参照 I01 の 24 種 × 5 段)30 s、--full で 3,000 組 11 分。正直に: 4 桁一致は規約を同じにしたからで性能の話ではない(FSIMc 0.851 が 1 位、VIFP 0.608 は 13 位)、GMSD は二次資料との照合だけ、steerable 版 VIF は未実装、歪み 16–18 は 4 指標とも弱い。踏んだ罠: scipy の偶数核 'same' は半画素ずれる(2×2 平均が別の答え)、round(1.5) は 0 から遠い側、ε は単位ベクトル化だけ(分母に足すと利得不変が 3e-5 崩れる)、GMSD の符号(公表表は |ρ|、1 回目は −1.6 の FAIL)、論文の 4 桁表は作者の 4 桁丸めの txt から計算されている(丸めで歪み 18 の 106〜122 組が同順位になり New / Color が 4 桁目で動く)。*

[![FSIMC と 971 人の MOS(3,000 組)。作者値 FSIMc.txt と 4 桁一致(色画像 → YIQ full range)。TID2013 全体で 1 位の指標。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_iqa_fsim_gmsd_vif/02_iqa_tid2013_mos_vs_fsimc_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_iqa_fsim_gmsd_vif/02_iqa_tid2013_mos_vs_fsimc.png)

*↑ 測定の図 ―― FSIMC と 971 人の MOS(3,000 組)。作者値 FSIMc.txt と 4 桁一致(色画像 → YIQ full range)。TID2013 全体で 1 位の指標。*

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

ソース: [examples/poc_iqa_fsim_gmsd_vif.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_iqa_fsim_gmsd_vif.py)

この回が作った図は全部で **6 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_iqa_fsim_gmsd_vif)

使用 op(ノートへ): [`fsim`](https://furuse.work/ops/imgmetrics/perceptual/fsim.html) · [`fsim_pair`](https://furuse.work/ops/imgmetrics/perceptual/fsim_pair.html) · [`fsimc`](https://furuse.work/ops/imgmetrics/perceptual/fsimc.html) · [`gmsd`](https://furuse.work/ops/imgmetrics/perceptual/gmsd.html) · [`gmsd_map`](https://furuse.work/ops/imgmetrics/perceptual/gmsd_map.html) · [`phase_congruency_pc`](https://furuse.work/ops/imgmetrics/perceptual/phase_congruency_pc.html) · [`rank_kendall_b`](https://furuse.work/ops/imgmetrics/iqa/rank_kendall_b.html) · [`rank_spearman`](https://furuse.work/ops/imgmetrics/iqa/rank_spearman.html) · [`tf_phase_congruency`](https://furuse.work/ops/2d/edges/tf_phase_congruency.html) · [`tid2013_by_distortion`](https://furuse.work/ops/imgmetrics/iqa/tid2013_by_distortion.html) · [`tid2013_compare`](https://furuse.work/ops/imgmetrics/iqa/tid2013_compare.html) · [`tid2013_evaluate`](https://furuse.work/ops/imgmetrics/iqa/tid2013_evaluate.html) · [`tid2013_index`](https://furuse.work/ops/imgmetrics/iqa/tid2013_index.html) · [`tid2013_metric_values`](https://furuse.work/ops/imgmetrics/iqa/tid2013_metric_values.html) · [`tid2013_published`](https://furuse.work/ops/imgmetrics/iqa/tid2013_published.html) · [`tid2013_root`](https://furuse.work/ops/imgmetrics/iqa/tid2013_root.html) · [`vifp`](https://furuse.work/ops/imgmetrics/perceptual/vifp.html)

## No.2026.135 —— ハエの視葉だけで進路を立て直す ―― ラミナから操舵まで、学習なしで

[![ハエの視葉だけで進路を立て直す ―― ラミナから操舵まで、学習なしで](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_optomotor_steering/06_follow.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_optomotor_steering/06_follow.gif)

*↑ **ハエの視葉だけで進路を立て直す ―― ラミナから操舵まで、学習なしで** ―― 外乱で向きが流れていく機体に、複眼と閉じた式の回路しか積まずに進路を立て直す —— ハエの optomotor 反応を fullseye の op だけで組み、真値のジャイロと並べて測った。経路は全段が学習なしの閉形式で、勾配で決めた数は 1 つも無い: 複眼で標本化(fly_hex_resample)→ ラミナの順応と帯域通過(fly_lamina_filter)→ ON / OFF に分ける(fly_onoff_split)→ 六角格子の 6 方向すべてで方向選択(fly_t4t5_field)→ 局所フロー(fly_flow_from_directions)→ 整合フィルタへの線形当てはめ(fly_matched_filter / fly_egomotion_from_flow)→ ヨー角速度 → 6 ニューロン 8 シナプスの操舵回路(graph_conductance_states)→ 舵。段ごとに厳密な恒等式がある: 景色を 1 万倍明るくしてもラミナの出力は変わらない(Weber、差 7e-16)、T4 の三腕モデル(Haag ら 2016 の逐語の定数 τ=250 ms・k=5/5/10)は論文の 2 柱刺激で 24.9636 / 0.8195 をそのまま返し、「増強と抑制は相補的」という主張は比の積の恒等式(4.161 × 7.321 = 30.461 = 三腕)として機械精度で成り立つ、整合フィルタの 1.7 rad/s は 9 桁一致で戻る。測った限界も隠さない: 古典の縞ドラムでは動き続ける回転との相関 0.976 だが自然な 1/f の景色では 0.897 に落ち、必要な較正利得は縞 2.64 に対し自然な景色 6.76 / 7.88 —— 種類が変われば 3.0 倍、同じ統計の別の景色どうしでも 1.16 倍ちがう(相関器は速度計ではなく対比つきの運動計)。視野 80° の 1 つの眼で同じ +0.5 rad/s を 12 枚の景色で測ると散らばり 1.05 で 12 枚中 4 枚は回転の符号すら間違えるが、fly_eye_merge で 3 つの眼を 250° に束ねると散らばり 0.44・符号の誤り 0 枚になる —— 複眼が広いことは飾りではない。閉ループ(較正は景色 A、飛ぶのは見たことのない景色 B)では、舵を切らなければ進路は 51 度流れ、視葉の反射は 33 度に、真値のジャイロは 23 度にする。反射は絶対の方位を知らないので流れをゼロにはできない —— そこから先は中枢複合体(コンパス)の仕事。操舵をコネクトームの側で書いても同じ 33 度で、膜電位は反転電位の凸結合なのでどんな入力でも発散しない。データは同梱しない(景色は fly_sky_1f が種から作る)。*

[![left to right, top to bottom: what the ommatidia see, the lamina's contrast (brightness thrown away), the ON and OFF cha](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_optomotor_steering/01_pathway_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_optomotor_steering/01_pathway.png)

*↑ 測定の図 ―― left to right, top to bottom: what the ommatidia see, the lamina's contrast (brightness thrown away), the ON and OFF channels, and the direction-selective field read as a local flow. The eye is turning at 0.5 rad/s in a 1/f panorama; nothing here was trained.*

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

ソース: [examples/poc_fly_optomotor_steering.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_fly_optomotor_steering.py)

この回が作った図は全部で **7 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_fly_optomotor_steering)

使用 op(ノートへ): [`fly_egomotion_from_flow`](https://furuse.work/ops/flyvision/selfmotion/fly_egomotion_from_flow.html) · [`fly_eye_merge`](https://furuse.work/ops/flyvision/selfmotion/fly_eye_merge.html) · [`fly_flow_from_directions`](https://furuse.work/ops/flyvision/direction/fly_flow_from_directions.html) · [`fly_hex_lattice`](https://furuse.work/ops/flyvision/lattice/fly_hex_lattice.html) · [`fly_hex_resample`](https://furuse.work/ops/flyvision/sample/fly_hex_resample.html) · [`fly_lamina_filter`](https://furuse.work/ops/flyvision/lamina/fly_lamina_filter.html) · [`fly_matched_filter`](https://furuse.work/ops/flyvision/selfmotion/fly_matched_filter.html) · [`fly_onoff_split`](https://furuse.work/ops/flyvision/lamina/fly_onoff_split.html) · [`fly_sky_1f`](https://furuse.work/ops/flyvision/stimulus/fly_sky_1f.html) · [`fly_t4t5_field`](https://furuse.work/ops/flyvision/direction/fly_t4t5_field.html) · [`graph_conductance_states`](https://furuse.work/ops/conngraph/circuit/graph_conductance_states.html) · [`graph_from_synapses`](https://furuse.work/ops/conngraph/construct/graph_from_synapses.html)

## No.2026.148 —— 遠ざかると消える距離と、形が変わるときの面積

[![遠ざかると消える距離と、形が変わるときの面積](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/04_vanish_at_p_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/04_vanish_at_p.png)

*↑ **遠ざかると消える距離と、形が変わるときの面積** ―― **「高周波と低周波を混ぜた絵」にも「滑らかに形が変わる絵」にも、絵から直接測れる厳密な真値がある** —— そして **よく使われている作り方のほうが、その真値を外す**。★★芯 1: **分解の直交性。** 理想的な周波数マスクで低域と高域に分けると 2 枚は厳密に直交するので `E(低) + E(高) = E(元)` が成り立つ(4 通りの遮断で帳尻の相対値 **1.9e-16**)。ところが教科書どおりの作り方(ガウシアンでぼかし、残りを高域にする)では **0.53 %〜3.10 %** ずれる。**どちらも足せば元に戻る** —— **可逆であることと直交であることは別**。しかもずれは **単調でない**: いちばん悪いのはぼかしが最も弱い a = 0.1 で、いちばん小さいのは途中の a = 0.7。**強くしても弱くしても直らない。**★★芯 2: **遠ざかると消える距離は整数。** k 画素を束ねる操作の伝達関数は `sin(πfk)/(k sin(πf))` で、f·k が整数のとき厳密に 0。つまり **周期 p 画素の模様は p 画素に束ねるとちょうど消える**(5 通りの周期で **1.4e-14**)。さらに強く、**束ねたあとの絵は 1 画素ずつ閉形式で書ける** —— 振幅だけでなく **束ねた画素の中心が (k−1)/2 ずれること**まで式に入っていて、束ね幅 1〜48 の全画素で **2.8e-14**。★★芯 3: **形の面積は t の厳密な 2 次式。** 多角形の頂点を線形補間すると囲む面積は `a t² + b t + c` に乗るので、**3 コマ測れば全コマを予言できる**(3 通りの形で **2.4e-15**)。それが**絵からも出る**: 多角形を画素に塗って数えた面積でも、格子 128 で 1.10 % だったずれが格子 512・1 画素を 4×4 に分けて **0.053 %** まで縮む。しかも **「1 画素を 4×4 に分ける」のは「格子を 4 倍細かくする」と厳密に同じ数字**(0.00e+00 で一致)。★★芯 4: **絵から測ると符号が消える。そこで予言はちょうど 25 % 外れる。** 頂点順を逆にした多角形へモーフすると、符号つき面積は t の 1 次式になり (t = 0.5 で多角形が線に潰れる)2 次式の予言は 3.4e-15 で当たる。しかし**絵から測れるのは正の面積だけ**なので放物線は折り返し、3 コマから当てた予言は最大値の **ちょうど 1/4** 外れる —— 2 つの形で **25.0 %** と **25.0 %**。**外れ方まで閉形式で出る。** ★★芯 5: **スプラインの 2 つの厳密な性質。** Catmull-Rom は制御点を **距離 0.0e+00** で通り、ベジエは制御点を通らない代わりに **凸包から出ない**(4 通り × 401 点すべて)—— ちょうど裏返しの性質。★★**外した予言を 3 つ残してある。** (a)「切り替わる束ね幅は遮断周波数 fc から 1/(2 fc) で予言できる」は**外れ**で、fc を 3 倍振っても実測は 3.4〜3.9 画素から動かない —— 決めているのは遮断周波数ではなく **高域側の絵が実際に持つ周期**。(b) 上の「ぼかしのずれは単調」も外れ。(c)「絵の最大と最小で振幅を測れば閉形式と一致する」も**外れ**で、k = 6 では **20.7 % 小さく**出る —— **画素が山の頂上を踏まないから**。**式は踏まなくても正しい。****新しい op は 1 つも足していない。** 検査 20 件・図 13 枚(動く図 1 枚を含む)。*

[![低い周波数に粗い模様、高い周波数に細かい模様を入れた 1 枚を、束ねながら見たもの。**束ねるのは「遠ざかる」こと**で、細かいほうが先に消える。ただし ★**いつ消えるかは遮断周波数では決まらない** —— 下の数表の「外した予言」を参照](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/01_hybrid_near_far_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/01_hybrid_near_far.png)

*↑ 測定の図 ―― 低い周波数に粗い模様、高い周波数に細かい模様を入れた 1 枚を、束ねながら見たもの。**束ねるのは「遠ざかる」こと**で、細かいほうが先に消える。ただし ★**いつ消えるかは遮断周波数では決まらない** —— 下の数表の「外した予言」を参照。*

[![**どちらも足せば元に戻る**(再構成の誤差は両方 1e-13 未満)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/02_orthogonal_split_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/02_orthogonal_split.png)

*↑ **どちらも足せば元に戻る**(再構成の誤差は両方 1e-13 未満)。*

[![k = 24 と k = 48(f·k が整数)で **厳密に 0**、その間では戻る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/05_transfer_curve_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/05_transfer_curve.png)

*↑ k = 24 と k = 48(f·k が整数)で **厳密に 0**、その間では戻る。*

[![閉形式なら 2.4e-15。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/09_area_from_picture_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/09_area_from_picture.png)

*↑ 閉形式なら 2.4e-15。*

[![薄い折れ線が制御点をつないだもの、濃い線が Catmull-Rom。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/12_catmull_through_points_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/12_catmull_through_points.png)

*↑ 薄い折れ線が制御点をつないだもの、濃い線が Catmull-Rom。*

[![6 角形が別の 6 角形へ変わって戻るところ。★見た目は連続に変わるが、**囲む面積は t の 厳密な 2 次式**に乗っている(次の図)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/06_morph_loop.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/06_morph_loop.gif)

*↑ 動く図 ―― 6 角形が別の 6 角形へ変わって戻るところ。★見た目は連続に変わるが、**囲む面積は t の 厳密な 2 次式**に乗っている(次の図)。*

```
py -3.11 examples/poc_vanishing_detail_and_morphing_area.py
```

ソース: [examples/poc_vanishing_detail_and_morphing_area.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_vanishing_detail_and_morphing_area.py)

この回が作った図は全部で **14 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area)

使用 op(ノートへ): [`convex_hull`](https://furuse.work/ops/3d/bounds/convex_hull.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`morph`](https://furuse.work/ops/shape2d/morph/morph.html)

## No.2026.184 —— セグメンテーションの関門 ―― 真値つきの 6 つの世界に 10 手法を当て、どの物差しがどの壊れ方に盲目かを測る

[![セグメンテーションの関門 ―― 真値つきの 6 つの世界に 10 手法を当て、どの物差しがどの壊れ方に盲目かを測る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/01_worlds_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/01_worlds.png)

*↑ **セグメンテーションの関門 ―― 真値つきの 6 つの世界に 10 手法を当て、どの物差しがどの壊れ方に盲目かを測る** ―― セグメンテーションを増やす前に、採点の物差しと真値を先に置いた —— 新モジュール segeval(分割表・Dice/Jaccard・境界 F・Hausdorff/ASSD・過分割/未分割・個数の一致・採点表、各 op に恒等式か第 2 実装の門)と segworld(真値つきの合成世界 6 種: 等半径の触れ合う粒はレンズ面積の閉形式、ボロノイ結晶粒は粒界長が scipy の稜線と 1e-9 で一致、影のある部品、平均が同じで質感だけ違う領域、照明の勾配、幅 1〜3 px の細い構造)。既存 10 手法(Otsu・局所閾値・Niblack・Sauvola・Chan–Vese・random walker・分水嶺 2 種・Felzenszwalb・SLIC)を既定のノブで総当たり。門: 6 世界すべてで真 vs 真が全部の物差しで満点 / マスクの物差しは融合に盲目(Otsu は J=0.95 なのに 9/10 が未分割)/ 境界の物差しは過分割に盲目(勾配の分水嶺は BF=1.00 なのに過分割 339)/ Sauvola は結晶粒の個数を全部当てるが粒界の帯を落とし J=0.91 / 影のある部品はどの手法も J < 0.3、真値を見る閾値のオラクルでも J=0.29 / 質感はマスク手法 ARI < 0.3、局所 σ の k-means は ARI=0.92 / 照明の勾配は大域 Otsu J=0.21、フラットフィールド後 J=1.00 / 細い構造は Otsu の境界 F が 1.00 でも雑音の粒で過分割 29。正直に: 手法のノブは既定固定(合わせれば直るものがある)、境界 F は距離変換の BF(Martin 2004 の 2 部マッチングではない)、個数の一致の辺の条件は自前の定義。10 門、2.0 s。*

[![Jaccard は物体マスク(格子を返す手法は —)。VI = Meilă の情報の変分(0 が一致)、ARI = 補正 Rand、境界 F は τ = 2 px、HD95 = 境界の Hausdorff の 95 % 点。過分割/未分割は](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/02_scores_blobs_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/02_scores_blobs.png)

*↑ 測定の図 ―― Jaccard は物体マスク(格子を返す手法は —)。VI = Meilă の情報の変分(0 が一致)、ARI = 補正 Rand、境界 F は τ = 2 px、HD95 = 境界の Hausdorff の 95 % 点。過分割/未分割は分割表の多数決の多重度、一致/分裂/融合/欠落/偽は主に重なる辺の次数。最後の行はルールの直し方。*

[![Jaccard は物体マスク(格子を返す手法は —)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/03_scores_voronoi_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/03_scores_voronoi.png)

*↑ Jaccard は物体マスク(格子を返す手法は —)。*

[![Jaccard は物体マスク(格子を返す手法は —)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/04_scores_parts_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/04_scores_parts.png)

*↑ Jaccard は物体マスク(格子を返す手法は —)。*

[![Jaccard は物体マスク(格子を返す手法は —)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/05_scores_texture_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/05_scores_texture.png)

*↑ Jaccard は物体マスク(格子を返す手法は —)。*

[![Jaccard は物体マスク(格子を返す手法は —)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/06_scores_gradient_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/06_scores_gradient.png)

*↑ Jaccard は物体マスク(格子を返す手法は —)。*

[![触れ合う粒: 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_random_wa](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/08_gauntlet_blobs.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/08_gauntlet_blobs.gif)

*↑ 動く図 ―― 触れ合う粒: 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_random_walker, watersheds, sg_watershed_gradient, sk_felzenszwalb, sk_slic, edt_watershed)。*

[![結晶粒(ボロノイ): 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_rando](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/09_gauntlet_voronoi.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/09_gauntlet_voronoi.gif)

*↑ 動く図 ―― 結晶粒(ボロノイ): 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_random_walker, watersheds, sg_watershed_gradient, sk_felzenszwalb, sk_slic)。*

[![影のある部品: 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_random_w](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/10_gauntlet_parts.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/10_gauntlet_parts.gif)

*↑ 動く図 ―― 影のある部品: 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_random_walker, watersheds, sg_watershed_gradient, sk_felzenszwalb, sk_slic)。*

[![質感だけ違う領域: 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_random](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/11_gauntlet_texture.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/11_gauntlet_texture.gif)

*↑ 動く図 ―― 質感だけ違う領域: 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_random_walker, watersheds, sg_watershed_gradient, sk_felzenszwalb, sk_slic, texture_kmeans)。*

[![照明の勾配: 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_random_wa](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/12_gauntlet_gradient.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/12_gauntlet_gradient.gif)

*↑ 動く図 ―― 照明の勾配: 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_random_walker, watersheds, sg_watershed_gradient, sk_felzenszwalb, sk_slic, flat_field_otsu)。*

[![細い構造: 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_random_wal](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/13_gauntlet_thin.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/13_gauntlet_thin.gif)

*↑ 動く図 ―― 細い構造: 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_random_walker, watersheds, sg_watershed_gradient, sk_felzenszwalb, sk_slic)。*

```
py -3.11 examples/poc_segmentation_gauntlet.py
```

ソース: [examples/poc_segmentation_gauntlet.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_segmentation_gauntlet.py)

この回が作った図は全部で **13 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_segmentation_gauntlet)

使用 op(ノートへ): [`blob_distance`](https://furuse.work/ops/blob/split/blob_distance.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`local_threshold`](https://furuse.work/ops/2d/segmentation/local_threshold.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`seg_dice_jaccard`](https://furuse.work/ops/segmentation/score/seg_dice_jaccard.html) · [`seg_score_card`](https://furuse.work/ops/segmentation/score/seg_score_card.html) · [`sg_watershed_gradient`](https://furuse.work/ops/2d/segment/sg_watershed_gradient.html) · [`sk_chan_vese`](https://furuse.work/ops/2d/segmentation/sk_chan_vese.html) · [`sk_felzenszwalb`](https://furuse.work/ops/2d/segmentation/sk_felzenszwalb.html) · [`sk_niblack`](https://furuse.work/ops/2d/segmentation/sk_niblack.html) · [`sk_sauvola`](https://furuse.work/ops/2d/segmentation/sk_sauvola.html) · [`sk_slic`](https://furuse.work/ops/2d/segmentation/sk_slic.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`watersheds`](https://furuse.work/ops/2d/segmentation/watersheds.html) · [`world_blobs_touching`](https://furuse.work/ops/segmentation/world/world_blobs_touching.html) · [`world_gradient_illumination`](https://furuse.work/ops/segmentation/world/world_gradient_illumination.html) · [`world_grains_voronoi`](https://furuse.work/ops/segmentation/world/world_grains_voronoi.html) · [`world_parts_with_shadow`](https://furuse.work/ops/segmentation/world/world_parts_with_shadow.html) · [`world_texture_regions`](https://furuse.work/ops/segmentation/world/world_texture_regions.html) · [`world_thin_structures`](https://furuse.work/ops/segmentation/world/world_thin_structures.html) · [`xsk_random_walker`](https://furuse.work/ops/2d/segmentation/xsk_random_walker.html)

## No.2026.186 —— 動的輪郭とレベルセット ―― 輪郭が縮み、凹みに入り、エッジで止まるまでを閉形式で確かめる

[![動的輪郭とレベルセット ―― 輪郭が縮み、凹みに入り、エッジで止まるまでを閉形式で確かめる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_active_contours/01_inputs_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_active_contours/01_inputs.png)

*↑ **動的輪郭とレベルセット ―― 輪郭が縮み、凹みに入り、エッジで止まるまでを閉形式で確かめる** ―― セグメンテーション拡充の第 2 陣 —— 新モジュール segcontour 10 op(snake・勾配ベクトル流 GVF・Chan–Vese のエネルギーと発展・形態学的 Chan–Vese・形態学的測地的 active contour とエッジ停止関数・符号付き距離への再初期化・DRLSE・平均曲率流)。各 op に閉形式か第 2 実装の門: 外力 0 の円の snake は巡回行列の固有値の閉形式どおり縮む(誤差 3e-14)、skimage の active_contour と 1e-13 で一致 / 曲率流の面積は dA/dt = −2π(円 −6.2767、凹んだ星形も −6.2822)/ 再初期化後の |∇φ| の 10〜90 % 点 0.987〜1.012、零等高線は動かない / 古典の snake のエネルギーは増えない(γ ≥ L、増加 0 回)、Chan–Vese(凸緩和の交互最小化)も 4 世界で単調非増加 / 既存 op sk_chan_vese と Dice 0.995。採点は第 1 陣の segeval と segworld: U 字の凹部に古典の snake は入れず(凹部を 100 % 覆ったまま、辺の途中も外に浮く —— エッジの勾配の力は辺の近くにしか届かない)、同じ α・β・γ で外力だけ GVF に替えると入る(被覆 1.0 %、Dice 0.993)/ 照明の勾配では大域の 2 平均の Chan–Vese が J=0.187 で負け、エッジで止まる局所の手法(測地的 AC 0.960・DRLSE 0.938)が勝つ / 触れ合う粒はマスクとしては Dice 0.97 でも 10 粒が 1 つ / 影のある部品はどの輪郭法も J < 0.7。正直に: Chan–Vese 2001 は単調減少を主張していない(門は凸緩和の側で立てた)、GVF・形態学的 snake・DRLSE・Sussman の式は原論文を未照合(要確認)、DRLSE は照明の勾配でエネルギーが 247 回増えた(陽的な刻み、門にしない)。12 門、6.4 s。*

[![c の更新(内外の平均)と、c を固定した凸緩和(Chan–Esedoglu–Nikolova)の交互最小化。どの世界でも1 度も増えず、分割が変わらなくなった所で止まる(門 5)。止まった所が真値に近いかは別(表を見る)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_active_contours/02_cv_energy_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_active_contours/02_cv_energy.png)

*↑ 測定の図 ―― c の更新(内外の平均)と、c を固定した凸緩和(Chan–Esedoglu–Nikolova)の交互最小化。どの世界でも1 度も増えず、分割が変わらなくなった所で止まる(門 5)。止まった所が真値に近いかは別(表を見る)。*

[![γ = 1 ≥ L = 0.463(外力の勾配の Lipschitz 定数)なので降下補題により全体は増えない(実測 増加 0 回)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_active_contours/03_snake_energy_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_active_contours/03_snake_energy.png)

*↑ γ = 1 ≥ L = 0.463(外力の勾配の Lipschitz 定数)なので降下補題により全体は増えない(実測 増加 0 回)。*

[![dA/dt = −∮κ ds = −2π。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_active_contours/04_curvature_area_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_active_contours/04_curvature_area.png)

*↑ dA/dt = −∮κ ds = −2π。*

[![Jaccard/Dice は物体マスク、境界 F は τ = 2 px。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_active_contours/05_scores_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_active_contours/05_scores.png)

*↑ Jaccard/Dice は物体マスク、境界 F は τ = 2 px。*

[![U 字の凹部: 同じ α・β・γ で外力だけ違う。古典(赤)は凹部の口に橋を架けて止まり、辺の途中も外に浮いたまま(エッジの勾配の力は辺の近くにしか届かない)、GVF(青)は奥まで入る。緑 = 真の縁。1 コマ = 20 反復。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_active_contours/06_u_shape_snakes.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_active_contours/06_u_shape_snakes.gif)

*↑ 動く図 ―― U 字の凹部: 同じ α・β・γ で外力だけ違う。古典(赤)は凹部の口に橋を架けて止まり、辺の途中も外に浮いたまま(エッジの勾配の力は辺の近くにしか届かない)、GVF(青)は奥まで入る。緑 = 真の縁。1 コマ = 20 反復。*

[![照明の勾配の上の暗い物体(反転して渡す)。全画面の矩形から 4 手法の輪郭が動く。大域の 2 平均(Chan–Vese・形態学的 CV)は明るい側の背景ごと切り、エッジで止まる GAC・DRLSE は物体に貼り付く(GAC は雑音の粒を数十](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_active_contours/07_gradient_world_contours.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_active_contours/07_gradient_world_contours.gif)

*↑ 動く図 ―― 照明の勾配の上の暗い物体(反転して渡す)。全画面の矩形から 4 手法の輪郭が動く。大域の 2 平均(Chan–Vese・形態学的 CV)は明るい側の背景ごと切り、エッジで止まる GAC・DRLSE は物体に貼り付く(GAC は雑音の粒を数十個残す = 表の予測の個数)。緑 = 真の縁、各手法のコマは反復数に比例して間引いて 40 コマに揃えた。*

[![凹んだ星形の平均曲率流。凹部は外へ、凸部は内へ動き、丸くなりながら面積は毎時間 2π ずつ減る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_active_contours/08_curvature_flow_star.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_active_contours/08_curvature_flow_star.gif)

*↑ 動く図 ―― 凹んだ星形の平均曲率流。凹部は外へ、凸部は内へ動き、丸くなりながら面積は毎時間 2π ずつ減る。*

```
py -3.11 examples/poc_active_contours.py
```

ソース: [examples/poc_active_contours.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_active_contours.py)

この回が作った図は全部で **8 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_active_contours)

使用 op(ノートへ): [`chan_vese_evolve`](https://furuse.work/ops/segmentation/contour/chan_vese_evolve.html) · [`curvature_flow`](https://furuse.work/ops/segmentation/contour/curvature_flow.html) · [`drle_evolve`](https://furuse.work/ops/segmentation/contour/drle_evolve.html) · [`edge_stop_g`](https://furuse.work/ops/segmentation/contour/edge_stop_g.html) · [`gvf_field`](https://furuse.work/ops/segmentation/contour/gvf_field.html) · [`level_set_reinit`](https://furuse.work/ops/segmentation/contour/level_set_reinit.html) · [`morph_chan_vese`](https://furuse.work/ops/segmentation/contour/morph_chan_vese.html) · [`morph_geodesic_ac`](https://furuse.work/ops/segmentation/contour/morph_geodesic_ac.html) · [`seg_dice_jaccard`](https://furuse.work/ops/segmentation/score/seg_dice_jaccard.html) · [`seg_score_card`](https://furuse.work/ops/segmentation/score/seg_score_card.html) · [`sk_chan_vese`](https://furuse.work/ops/2d/segmentation/sk_chan_vese.html) · [`snake_evolve`](https://furuse.work/ops/segmentation/contour/snake_evolve.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`world_blobs_touching`](https://furuse.work/ops/segmentation/world/world_blobs_touching.html) · [`world_gradient_illumination`](https://furuse.work/ops/segmentation/world/world_gradient_illumination.html) · [`world_parts_with_shadow`](https://furuse.work/ops/segmentation/world/world_parts_with_shadow.html) · [`world_thin_structures`](https://furuse.work/ops/segmentation/world/world_thin_structures.html)

## No.2026.187 —— グラフ・階層・閾値のセグメンテーション ―― 最大フロー = 最小カット、ultrametric、つまみを回すと粗から細へ

[![グラフ・階層・閾値のセグメンテーション ―― 最大フロー = 最小カット、ultrametric、つまみを回すと粗から細へ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/01_inputs_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/01_inputs.png)

*↑ **グラフ・階層・閾値のセグメンテーション ―― 最大フロー = 最小カット、ultrametric、つまみを回すと粗から細へ** ―― セグメンテーション拡充の第 3 陣 —— 新モジュール seggraph 16 op。門: graph cut は 3×4 の 40 問で総当たりの最小と一致、最大フロー = 最小カット(160×160 でも整数で厳密)/ α-expansion は 80 問すべて E ≤ 2c·E*(Boykov–Veksler–Zabih 2001 Theorem 6.1)、局所解に留まる 3×3 の罠も示す / 成分木の面積開放は冪等・反拡大で skimage と画素一致 / 準平坦領域 = 最小全域木を α で切った連結成分(6 つの α)、α を増やすと入れ子 / 階層分水嶺は盆地 107 個の全 3 つ組で ultrametric の違反 0、生き残る盆地 = dynamics > θ / SNIC の超画素は全部 4-連結、境界の再現率は SLIC と 0.05 以内 / isodata は不動点、三角法は skimage と一致、Kapur は総当たりの最大。どの世界でどれが勝つか: 触れ合う粒の階層分水嶺は θ = 0 で 19 領域の過分割、θ = 0.5〜3.5 で 10 粒ちょうど、大きな θ で 1 領域 / graph cut の λ = 0.1 は雑音の粒の Dice を +0.13 上げ、同じ λ で幅 1〜3 px の線を −0.13 下げる / SRM は結晶粒で VI 0.74〜0.90 bit まで下がるが、平均が同じで質感だけ違う世界ではどの q でも 1 領域より良くならない / 照明の勾配で Kittler は Dice 0.93〜0.99、isodata は 0.29〜0.41。掃引の動画 3 本(θ・q・λ)。正直に: SRM の述語の係数、Kittler・Kapur・三角法の原典の規約、SNIC の式 (1) は原論文を未照合(要確認)。13 門、6.4 s。*

[![−距離変換の地形の 1 本の最小全域森を、dynamics ≤ θ の辺で結ぶ。θ = 0 は雑音の凹みまで盆地にして過分割、θ = 0.5〜3 px で粒の数ちょうど、くびれの深さ(重なり 20 %)を超えると隣の粒と融合する。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/02_watershed_theta_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/02_watershed_theta.png)

*↑ 測定の図 ―― −距離変換の地形の 1 本の最小全域森を、dynamics ≤ θ の辺で結ぶ。θ = 0 は雑音の凹みまで盆地にして過分割、θ = 0.5〜3 px で粒の数ちょうど、くびれの深さ(重なり 20 %)を超えると隣の粒と融合する。*

[![エネルギーは毎回厳密に最小(最大フロー = 最小カット)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/03_graph_cut_lambda_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/03_graph_cut_lambda.png)

*↑ エネルギーは毎回厳密に最小(最大フロー = 最小カット)。*

[![結晶粒は q = 256 付近で VI が 1 bit を切る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/04_srm_q_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/04_srm_q.png)

*↑ 結晶粒は q = 256 付近で VI が 1 bit を切る。*

[![Kittler は 2 クラスの分散を別々に持つので Bayes の最小誤差の閾値(2 次方程式の根)に乗る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/05_thresholds_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/05_thresholds.png)

*↑ Kittler は 2 クラスの分散を別々に持つので Bayes の最小誤差の閾値(2 次方程式の根)に乗る。*

[![照明の勾配では背景の裾が長く、2 平均の中点(isodata)は背景の中に落ちる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/06_scores_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/06_scores.png)

*↑ 照明の勾配では背景の裾が長く、2 平均の中点(isodata)は背景の中に落ちる。*

[![触れ合う粒の階層分水嶺。θ を大 → 小 → 大に振る: 1 領域から粒の数ちょうどを経て雑音の凹みで過分割へ、そして戻る。どのコマも同じ 1 本の木の切り方(入れ子)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/08_watershed_theta_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/08_watershed_theta_sweep.gif)

*↑ 動く図 ―― 触れ合う粒の階層分水嶺。θ を大 → 小 → 大に振る: 1 領域から粒の数ちょうどを経て雑音の凹みで過分割へ、そして戻る。どのコマも同じ 1 本の木の切り方(入れ子)。*

[![結晶粒の SRM。q = 1(全部 1 領域)から 1024(細切れ)へ。q = 256 前後で粒界に沿う。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/09_srm_q_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/09_srm_q_sweep.gif)

*↑ 動く図 ―― 結晶粒の SRM。q = 1(全部 1 領域)から 1024(細切れ)へ。q = 256 前後で粒界に沿う。*

[![graph cut の λ を 0 → 0.3。黄 = 正解の物体、赤 = 余計、青 = 取り逃し。左の雑音の点は消え、右の細い線も同じ λ で途切れて消える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/10_graph_cut_lambda_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation/10_graph_cut_lambda_sweep.gif)

*↑ 動く図 ―― graph cut の λ を 0 → 0.3。黄 = 正解の物体、赤 = 余計、青 = 取り逃し。左の雑音の点は消え、右の細い線も同じ λ で途切れて消える。*

```
py -3.11 examples/poc_graph_hierarchy_segmentation.py
```

ソース: [examples/poc_graph_hierarchy_segmentation.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_graph_hierarchy_segmentation.py)

この回が作った図は全部で **10 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_graph_hierarchy_segmentation)

使用 op(ノートへ): [`alpha_expansion`](https://furuse.work/ops/segmentation/graph/alpha_expansion.html) · [`alpha_tree`](https://furuse.work/ops/segmentation/graph/alpha_tree.html) · [`area_opening_attr`](https://furuse.work/ops/segmentation/graph/area_opening_attr.html) · [`graph_cut_binary`](https://furuse.work/ops/segmentation/graph/graph_cut_binary.html) · [`hierarchical_watershed`](https://furuse.work/ops/segmentation/graph/hierarchical_watershed.html) · [`quasi_flat_zones`](https://furuse.work/ops/segmentation/graph/quasi_flat_zones.html) · [`quickshift`](https://furuse.work/ops/segmentation/graph/quickshift.html) · [`seg_boundary_f`](https://furuse.work/ops/segmentation/score/seg_boundary_f.html) · [`seg_dice_jaccard`](https://furuse.work/ops/segmentation/score/seg_dice_jaccard.html) · [`seg_object_counts_match`](https://furuse.work/ops/segmentation/score/seg_object_counts_match.html) · [`seg_score_card`](https://furuse.work/ops/segmentation/score/seg_score_card.html) · [`seg_under_over_segmentation`](https://furuse.work/ops/segmentation/score/seg_under_over_segmentation.html) · [`snic_superpixels`](https://furuse.work/ops/segmentation/graph/snic_superpixels.html) · [`statistical_region_merging`](https://furuse.work/ops/segmentation/graph/statistical_region_merging.html) · [`superpixel_quality`](https://furuse.work/ops/segmentation/graph/superpixel_quality.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`threshold_isodata`](https://furuse.work/ops/segmentation/threshold/threshold_isodata.html) · [`threshold_kapur`](https://furuse.work/ops/segmentation/threshold/threshold_kapur.html) · [`threshold_kittler`](https://furuse.work/ops/segmentation/threshold/threshold_kittler.html) · [`threshold_triangle`](https://furuse.work/ops/segmentation/threshold/threshold_triangle.html) · [`ultrametric_contour_map`](https://furuse.work/ops/segmentation/graph/ultrametric_contour_map.html) · [`world_blobs_touching`](https://furuse.work/ops/segmentation/world/world_blobs_touching.html) · [`world_gradient_illumination`](https://furuse.work/ops/segmentation/world/world_gradient_illumination.html) · [`world_grains_voronoi`](https://furuse.work/ops/segmentation/world/world_grains_voronoi.html) …(他 3)

### 時系列を 3-D として測るウィング ―― 動画は 1 つの体積

2-D の動画を (t, y, x) の 1 つの体積とみなすと、3-D の op ―― 連結成分、等値面、領域特徴 ―― がそのまま時間方向に効きます。合体したコロニーは時空間で Y 字になり、通過する車は (t, x) 画像の帯になり、波面の到達時刻は等値面になります。この部屋の 19 点はその実演です。

同時に、時間方向ならではの罠も出ました。フレーム格子への丸めは必ず遅らせ、画素の面積は合体を早める。誤リンクには向きの逆な 2 種類があり、誤り率 1 本では拡散係数がどちらへ外れるか決まらない。テンプレート追跡は見失うより先に静かにずれ、ずれた 152 フレーム全部が「見つけた」と報告する。

モーション拡大の展示は、この部屋でいちばん正直な結論を持っています。拡大率 200 まで機械精度で厳密に動くのに、測定の役には立たない ―― 拡大は人間に見せるための道具です。

## No.2026.055 —— 動画から固有振動数・減衰比・モード形状を同定する ―― f は最後まで生き残り、ζ が先に嘘をつく

[![動画から固有振動数・減衰比・モード形状を同定する ―― f は最後まで生き残り、ζ が先に嘘をつく](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/01_scene.png)

*↑ **動画から固有振動数・減衰比・モード形状を同定する ―― f は最後まで生き残り、ζ が先に嘘をつく** ―― 片持ち梁(Euler–Bernoulli 閉形式)の 3 モード自由減衰を、雑音・照明ちらつき 100 Hz・手ぶれ・ローリングシャッター入りの動画に合成し、位相法(phase_displacement)と PIV(piv_cross_correlate)で f_n / ζ_n / MAC を測る。f_n は 3 モードとも 0.06 Hz 以内で当たるが、同じ時系列から出した ζ_1 は半値幅 0.0778 / 包絡線 0.0188 / 当てはめ 0.0181(真値 0.02)と方法で 3 通り。振幅を 0.02→2 px で掃引すると壊れる順番は f → ζ → MAC_2 → MAC_3 で、位相法は 0.02 px で f_1 誤差 +0.030 Hz のまま ζ_1 が真値の 0.23 倍になる。fps 48.5 では照明の折り返しがちょうど 3.00 Hz = f_1 に乗り、輝度のゼロ点は ζ を出せず位相法は 0.0191 で生き残る。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/02_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/02_frames.png)

*↑ 測定の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/03_zero_point_spectrum_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/03_zero_point_spectrum.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/05_tip_waveform_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/05_tip_waveform.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/08_cliff_frequency_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/08_cliff_frequency.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/11_fps_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/11_fps_sweep.png)

*↑ この回の図*

[![動画(640 × 502、24 fps、292 コマ): 片持ち梁の自由減衰(A_1 = 0.2 px、雑音・照明ちらつき・手ぶれ・ローリングシャッター入り、撮影 128 fps を 5.3 倍のスローで再生)。画面のままでは梁は動いて見え](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/14_beam_video.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/14_beam_video.gif)

*↑ 動く図 ―― 動画(640 × 502、24 fps、292 コマ): 片持ち梁の自由減衰(A_1 = 0.2 px、雑音・照明ちらつき・手ぶれ・ローリングシャッター入り、撮影 128 fps を 5.3 倍のスローで再生)。画面のままでは梁は動いて見えないので、12 測点のたわみを 50 倍に誇張して重ねた(白 = 真値、青 = 位相法の測定)。下段は先端の変位が時刻とともに伸びる(白 = 真値、青 = 位相法、朱 = PIV)。最後のコマが同定結果: f_1 は 3.013 Hz(真 3.000)と当たるが、同じ時系列から出した ζ_1 は 半値幅 0.0778 / 包絡線 0.0188 / 当てはめ 0.0181(真 0.020)と方法で 3 通りに割れる。*

```
py -3.11 examples/poc_beam_modal_video.py
```

ソース: [examples/poc_beam_modal_video.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_beam_modal_video.py)

この回が作った図は全部で **14 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_beam_modal_video)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`data_to_pixel`](https://furuse.work/ops/annotate/plot/data_to_pixel.html) · [`envelope`](https://furuse.work/ops/oned/signal/envelope.html) · [`phase_displacement`](https://furuse.work/ops/motionmag/measure/phase_displacement.html) · [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`temporal_bandpass`](https://furuse.work/ops/motionmag/temporal/temporal_bandpass.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html)

## No.2026.060 —— 冷蔵輸送の温度記録 ―― ロガーを置いた場所が合否を決めている

[![冷蔵輸送の温度記録 ―― ロガーを置いた場所が合否を決めている](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cold_chain_excursion/01_scene_slices_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cold_chain_excursion/01_scene_slices.png)

*↑ **冷蔵輸送の温度記録 ―― ロガーを置いた場所が合否を決めている** ―― 12.0 m x 2.4 m のリーファー荷室の 12 時間を (t, y, x) の 1 つの体積(720 分 x 60 x 12 セル)として組み立て、吹き出し口からの距離・4 枚の壁からの侵入・扉開閉 5 回のパルス・荷の 1 次遅れ(空気 5 分 / 製品 64〜91 分)を既知の閉形式で仕込んだ図。真に不合格な製品セルは 108 / 490(22.0 %)なのに、製品にロガーを 1 個貼ると 82.4 % の置き方が「合格」と言う。要因を 1 つずつ止めると壊れ方が分かれる ―― 壁だけなら偽合格 95.5 %・偽不合格 0.0 %、壁を止めて扉だけ残すと偽不合格が 3.5 % 現れ、しかも製品に貼ったロガーは 100 % 合格と言う(短いパルスは製品に入らない)。崖は紙の上で予測できて、時定数の崖は「空気 + ロガー」の 2 段モデルで実測 19〜138 分に対し相対 18 % 以内、サンプリング間隔と 0.5 K 量子化の崖は予測と完全一致。同じ記録から出した 3 指標は「12 °C に許す時間」に直すと 60 / 276 / 197 分と 4.6 倍ずれ、720 セル中 82 セル(11.4 %)で合否が揃わない。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cold_chain_excursion/02_layout_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cold_chain_excursion/02_layout_maps.png)

*↑ 測定の図*

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

ソース: [examples/poc_cold_chain_excursion.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_cold_chain_excursion.py)

この回が作った図は全部で **16 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_cold_chain_excursion)

使用 op(ノートへ): [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`integrate_funct_1d`](https://furuse.work/ops/oned/function/integrate_funct_1d.html) · [`quantize`](https://furuse.work/ops/oned/signal/quantize.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`sample_funct_1d`](https://furuse.work/ops/oned/function/sample_funct_1d.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_label_shape_stats`](https://furuse.work/ops/volcolor/measure/vol_label_shape_stats.html) · [`vol_mip`](https://furuse.work/ops/2d/3d/vol_mip.html) · [`vol_profile_line`](https://furuse.work/ops/3d/probe/vol_profile_line.html) · [`vol_region_props`](https://furuse.work/ops/3d/regionprops/vol_region_props.html)

## No.2026.095 —— ひび割れの「幅」ではなく「伸び」を測る ―― 同じ壁を撮り返すと誤差の性質が変わる

[![ひび割れの「幅」ではなく「伸び」を測る ―― 同じ壁を撮り返すと誤差の性質が変わる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/01_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/01_frames.png)

*↑ **ひび割れの「幅」ではなく「伸び」を測る ―― 同じ壁を撮り返すと誤差の性質が変わる** ―― 1 px = 0.15 mm の壁を 3 年 12 期にわたり撮り返し、ひび割れの成長率 0.040 mm/年 を測る。2 値化して画素を数えるやり方は幅を 25.0 % 過小に言いながら成長率は +153.0 % 過大に言い、幅を凍結した対照群でも +0.0117 mm/年 の「成長」を出す(犯人はぼけ。要因を 1 つずつ止めて分けた)。輝度欠損を積分するやり方は成長率 +3.1 %、対照群では +0.0005 mm/年。★2 値化の成長率は初期の幅だけで 0.0241〜0.1038 mm/年 と動く ―― 1 画素の段差が観測窓に来たかどうかで決まる。*

[![2 値化は幅の偏りより**期ごとの跳ね**が問題。跳ねの正体はぼけと画素位相で、4 節と 3 節で分けて数える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/02_timeseries_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/02_timeseries.png)

*↑ 測定の図 ―― 2 値化は幅の偏りより**期ごとの跳ね**が問題。跳ねの正体はぼけと画素位相で、4 節と 3 節で分けて数える。*

[![ここに出る傾きはすべて『見かけの成長』。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/03_control_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/03_control.png)

*↑ ここに出る傾きはすべて『見かけの成長』。*

[![傾きが 0 に近いほど列方向の画素位相が揃い、2 値化は画面ごと 1 画素単位で跳ぶ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/05_phase_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/05_phase.png)

*↑ 傾きが 0 に近いほど列方向の画素位相が揃い、2 値化は画面ごと 1 画素単位で跳ぶ。*

[![横線を下回った時点で 0.040 mm/年 を 2σ で言える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/07_cliff_epochs_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/07_cliff_epochs.png)

*↑ 横線を下回った時点で 0.040 mm/年 を 2σ で言える。*

[![2 値化は臨界幅より細いと 0(未検出)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/09_cliff_width_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/09_cliff_width.png)

*↑ 2 値化は臨界幅より細いと 0(未検出)。*

[![動画(576 × 456、12 fps、378 コマ): 同じ壁を 3 年 12 期撮り返す。各期で中心線に直交する断面を 24 本、左から順に切り(橙 = いま切っている断面、右下が拡大)、下段左がその断面の輝度欠損 —— その面積が幅そ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/11_series_video.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/11_series_video.gif)

*↑ 動く図 ―― 動画(576 × 456、12 fps、378 コマ): 同じ壁を 3 年 12 期撮り返す。各期で中心線に直交する断面を 24 本、左から順に切り(橙 = いま切っている断面、右下が拡大)、下段左がその断面の輝度欠損 —— その面積が幅そのもの。24 本の平均が積分法の幅(青、測りかけの期は橙の輪で途中平均)、朱のマスクの画素を数えたのが 2 値化(朱)。真の幅は 1 期 0.010 mm ずつ伸びる(0.067 画素)。最後の当てはめで成長率は 真値 0.0400 / 積分法 0.0412 / 2 値化 0.1012 mm/年。2 値化は期ごとに跳ね(0.0185〜0.3386 mm)、跳ねの正体はぼけ(PSF σ 0.75〜1.24 px)と据え直しの画素位相。*

```
py -3.11 examples/poc_crack_width_timeseries.py
```

ソース: [examples/poc_crack_width_timeseries.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_crack_width_timeseries.py)

この回が作った図は全部で **11 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_crack_width_timeseries)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`data_to_pixel`](https://furuse.work/ops/annotate/plot/data_to_pixel.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html)

## No.2026.026 —— 構造物の微小振動を映像から測る ―― モーション拡大は「測る」役に立つのか

[![構造物の微小振動を映像から測る ―― モーション拡大は「測る」役に立つのか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/01_slit_scan_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/01_slit_scan.png)

*↑ **構造物の微小振動を映像から測る ―― モーション拡大は「測る」役に立つのか** ―― 既知振幅 0.02 px・3.7 Hz の振動を合成し、モーション拡大が測定に効くかを見た図。拡大率 α = 200 まで機械精度で厳密。だが拡大は測定精度を良くしない ―― 位相を α 倍すると雑音も α 倍。片持ち梁では位相相関が 0.30 と 0.00 px の面積平均 0.15 px という、どこにも存在しない数を返す。*

[![剛体を仮定する位相相関が返す 0.150 px は 0.30 と 0.00 の面積平均で、どの列の真値とも違う。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/02_beam_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/02_beam_profile.png)

*↑ 測定の図 ―― 剛体を仮定する位相相関が返す 0.150 px は 0.30 と 0.00 の面積平均で、どの列の真値とも違う。*

[![3.7 Hz を含む帯だけが 0 dB。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/03_band_selectivity_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/03_band_selectivity.png)

*↑ 3.7 Hz を含む帯だけが 0 dB。*

[![3.05 px までは機械精度、3.10 px で崩壊。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/04_amplitude_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/04_amplitude_cliff.png)

*↑ 3.05 px までは機械精度、3.10 px で崩壊。*

[![動画(480 × 480、12 fps、124 コマ): 3.7 Hz・0.1 px で揺れる表面(雑音 σ 0.01)。左が生の映像、右が 10 倍に拡大した映像で、朱の細い縦線は静止時の縞の山。生では揺れが表示 0.3 px で目に見え](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/05_magnify_video.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/05_magnify_video.gif)

*↑ 動く図 ―― 動画(480 × 480、12 fps、124 コマ): 3.7 Hz・0.1 px で揺れる表面(雑音 σ 0.01)。左が生の映像、右が 10 倍に拡大した映像で、朱の細い縦線は静止時の縞の山。生では揺れが表示 0.3 px で目に見えず、拡大後は 1 px 相当で見える。下段は変位の時系列: 白 = 真値、青 = 生の映像から測った値、橙 = 拡大後に測って 10 で割った値。振幅は 真 0.1000 / 生から 0.10012 / 拡大後 0.10013 px で、拡大しても測定は良くならない(見せるための道具)。*

```
py -3.11 examples/poc_motion_magnification.py
```

ソース: [examples/poc_motion_magnification.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_motion_magnification.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_motion_magnification)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`band_snr`](https://furuse.work/ops/motionmag/temporal/band_snr.html) · [`data_to_pixel`](https://furuse.work/ops/annotate/plot/data_to_pixel.html) · [`displacement_series`](https://furuse.work/ops/motionmag/measure/displacement_series.html) · [`motion_magnify`](https://furuse.work/ops/motionmag/magnify/motion_magnify.html) · [`phase_displacement`](https://furuse.work/ops/motionmag/measure/phase_displacement.html) · [`synthesize_translation`](https://furuse.work/ops/motionmag/synthesis/synthesize_translation.html) · [`temporal_band_power`](https://furuse.work/ops/motionmag/temporal/temporal_band_power.html) · [`temporal_bandpass`](https://furuse.work/ops/motionmag/temporal/temporal_bandpass.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html)

## No.2026.030 —— 粒子追跡を (行, 列, 時刻) の体積として測る ―― 誤リンクの向きは 1 種類ではない

[![粒子追跡を (行, 列, 時刻) の体積として測る ―― 誤リンクの向きは 1 種類ではない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/05_tracking_links.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/05_tracking_links.gif)

*↑ **粒子追跡を (行, 列, 時刻) の体積として測る ―― 誤リンクの向きは 1 種類ではない** ―― 400 個の粒子の動画を追跡し、軌跡から拡散係数 D を読んだ図。曖昧な誤リンクは D を 0.925 倍に下げ、欠測による誤リンクは同じ動画で 3.429 倍に上げる ―― 誤り率 1 本では向きが決まらない。効くのは 1 対 1 制約ではなく、上限距離のゲート 1 行(3.429 → 1.304)。*

[![時間最大投影では粒子が尾を引く(= 軌跡)。kymograph は行 90-101 の帯を縦(時間)へ積んだもので、筋の傾きがそのまま列方向の速度。縦は 5 倍に拡大。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/01_spacetime_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/01_spacetime.png)

*↑ 測定の図 ―― 時間最大投影では粒子が尾を引く(= 軌跡)。kymograph は行 90-101 の帯を縦(時間)へ積んだもので、筋の傾きがそのまま列方向の速度。縦は 5 倍に拡大。*

[![縦軸は常用対数(0 が真値)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/02_density_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/02_density_bias.png)

*↑ 縦軸は常用対数(0 が真値)。*

[![真値で割った比。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/03_msd_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/03_msd.png)

*↑ 真値で割った比。*

[![曖昧と欠測を分けて数えると、D の外れる向きが説明できる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/04_density_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/04_density_table.png)

*↑ 曖昧と欠測を分けて数えると、D の外れる向きが説明できる。*

```
py -3.11 examples/poc_particle_tracking.py
```

ソース: [examples/poc_particle_tracking.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_particle_tracking.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_particle_tracking)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_local_maxima`](https://furuse.work/ops/3d/feature/vol_local_maxima.html)

## No.2026.111 —— 沈下したのか、測り直しただけなのか ―― 検出限界で切ると景色が変わる

[![沈下したのか、測り直しただけなのか ―― 検出限界で切ると景色が変わる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_settlement_significance/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_settlement_significance/01_scene.png)

*↑ **沈下したのか、測り直しただけなのか ―― 検出限界で切ると景色が変わる** ―― トンネル掘進で沈んだ 24 x 16 m の路面を 2 時期の点群で測る。ゼロ点の最近傍距離(C2C)は変化ゼロでも中央値 47.74 mm を返し(正体は点間隔)、符号も持たない。M3C2 の平均は -2.43 mm で真値と一致するが、LoD を超えて有意なのは 275/551 core(49.9 %)でその平均は -4.34 mm ―― 1 行の平均はどちらとも一致しない。LoD は沈下ではなく面の地図で、ゾーンごとに 0.51〜3.58 mm。有意なものだけ足すと体積は 0.8569 → 0.7643 m3 に痩せ、その欠け量は core ごとの LoD から先に計算できる(予測 0.867 / 実測 0.892)。*

[![有意の地図は真値の地図をよく復元する(TPR 88.7 % / FPR 3.6 %)。ただし縁が痩せる —— そこが 7 節の体積の話。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_settlement_significance/02_map_change_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_settlement_significance/02_map_change.png)

*↑ 測定の図 ―― 有意の地図は真値の地図をよく復元する(TPR 88.7 % / FPR 3.6 %)。ただし縁が痩せる —— そこが 7 節の体積の話。*

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

ソース: [examples/poc_settlement_significance.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_settlement_significance.py)

この回が作った図は全部で **7 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_settlement_significance)



## No.2026.041 —— テンプレート追跡は「見失う」より先に「静かにずれる」

[![テンプレート追跡は「見失う」より先に「静かにずれる」](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/01_ncc_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/01_ncc_maps.png)

*↑ **テンプレート追跡は「見失う」より先に「静かにずれる」** ―― 既知の相似変換でカメラを動かし、テンプレート追跡が「見失う」「静かにずれる」「自信満々で間違える」の 3 通りで壊れるのを見た図。ずれていた 152 フレームの 152 フレーム全部が、遮蔽なしで校正したピークのしきい値を通って「見つけた」と報告した。真値なしで測れる絶対量は往復追跡の不一致だけ。*

[![同じ遮蔽率でも、そっくりな別物体が視野に居るだけで崖がはるかに手前へ来る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/02_occlusion_vs_twin_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/02_occlusion_vs_twin.png)

*↑ 測定の図 ―― 同じ遮蔽率でも、そっくりな別物体が視野に居るだけで崖がはるかに手前へ来る。*

[![更新なしは平らなまま。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/03_drift_curves_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/03_drift_curves.png)

*↑ 更新なしは平らなまま。*

[![得意な崖が逆。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/04_confidence_auc_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/04_confidence_auc.png)

*↑ 得意な崖が逆。*

[![動画(30 フレーム + 最後で 2 秒止め、5 fps): 同じ 1 枚目のテンプレートを更新なし全域探索で追う(ゼロ点)。3 フレーム目から真の対象の 70 % を左から隠す。左 = 平坦な遮蔽物: ピークは平均 0.745 まで下がっ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/05_twin_vs_flat_occluder.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/05_twin_vs_flat_occluder.gif)

*↑ 動く図 ―― 動画(30 フレーム + 最後で 2 秒止め、5 fps): 同じ 1 枚目のテンプレートを更新なし全域探索で追う(ゼロ点)。3 フレーム目から真の対象の 70 % を左から隠す。左 = 平坦な遮蔽物: ピークは平均 0.745 まで下がってしきい値 0.843 を割る(「見失った?」と正直に言う)が、位置は平均 0.78 px で追えている(見失い 0 / 27)。右 = そっくりな別物体が 51 px 離れて一緒に流れる: 最初の遮蔽フレームで複製に乗り換え、平均誤差 46.13 px、見失い 27 / 27 —— それなのにピークは平均 0.856 でしきい値を超え、27 / 27 フレームで「見つけた」と報告する。下段の紫(突出度)は右で平均 0.111 としきい値 0.304 を割って取り違えを疑うが、追えている左でも平均 0.203 で同じく割る —— 突出度が測っているのは曖昧さで、正しさではない*

```
py -3.11 examples/poc_template_tracking.py
```

ソース: [examples/poc_template_tracking.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_template_tracking.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_template_tracking)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`ncc_locate`](https://furuse.work/ops/2d/matching/ncc_locate.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`shape_locate`](https://furuse.work/ops/2d/matching/shape_locate.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html)

## No.2026.044 —— 成長のタイムラプスを時空間の連結成分として測る

[![成長のタイムラプスを時空間の連結成分として測る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/01_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/01_frames.png)

*↑ **成長のタイムラプスを時空間の連結成分として測る** ―― 広がって合体するコロニーの動画を (t, y, x) の体積として 3-D 連結成分で読んだ図。画素が面積を持つせいで合体は早く見え(組 0-1 で -1.16 フレーム)、フレーム格子への丸めは遅らせる(+0.94) ―― 逆向きなので合計は小さく見える。`vol_label` の既定 26 近傍は、隙間 0.92 のニアミスを合体させた。*

[![縦が時間(下向き、4 倍に拡大)、横が列。2 本の管が合わさる高さがそのまま合体時刻。色は 3-D ラベル。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/02_ystructure_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/02_ystructure.png)

*↑ 測定の図 ―― 縦が時間(下向き、4 倍に拡大)、横が列。2 本の管が合わさる高さがそのまま合体時刻。色は 3-D ラベル。*

[![横軸はどちらも『何倍粗くしたか』。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/03_sampling_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/03_sampling.png)

*↑ 横軸はどちらも『何倍粗くしたか』。*

[![空間側は格子の位相でこれだけ動く(偏りより大きい)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/04_sampling_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/04_sampling_table.png)

*↑ 空間側は格子の位相でこれだけ動く(偏りより大きい)。*

[![動画(48 フレーム): 左は二値のフレームを 3-D の家族ラベルで塗ったもの(白の細線 = 真の連続円。色は体積全体で決まる家族なので、合体する 2 個は合体の前から同じ色)。右は合体する 2 組の中心を通る行の時空間断面が時刻とともに](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/05_growth_merge.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/05_growth_merge.gif)

*↑ 動く図 ―― 動画(48 フレーム): 左は二値のフレームを 3-D の家族ラベルで塗ったもの(白の細線 = 真の連続円。色は体積全体で決まる家族なので、合体する 2 個は合体の前から同じ色)。右は合体する 2 組の中心を通る行の時空間断面が時刻とともに現れ、Y 字の分かれ目が合体時刻になる(白の点線 = 閉形式の真値 7.99 / 30.09、橙 = 観測 7 / 31)。下はフレームを独立に数えた塊の数で、減ったのは t = 7, 31, 47。最後の t = 47 の減少はニアミス 4-5(最終フレームでも隙間 0.92)を 8 近傍が繋いだ偽の合体で、真の個数は 5 のまま。*

```
py -3.11 examples/poc_timelapse_growth.py
```

ソース: [examples/poc_timelapse_growth.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_timelapse_growth.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_timelapse_growth)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_region_props`](https://furuse.work/ops/3d/regionprops/vol_region_props.html)

## No.2026.045 —— (x, y, t) で数える ―― 通過台数とオクルージョン、そして L/V という 1 つの定数

[![(x, y, t) で数える ―― 通過台数とオクルージョン、そして L/V という 1 つの定数](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/01_per_frame_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/01_per_frame.png)

*↑ **(x, y, t) で数える ―― 通過台数とオクルージョン、そして L/V という 1 つの定数** ―― 車を流した合成動画で、フレームごとの計数・仮想ループ・(t, x) スリット画像の連結成分を並べた図。フレームごとの最大値は通過 10 台に対し 7 ―― 別の量を測っている。破綻の条件は 3 つとも車長 ÷ 速度 = L/V(9.0 フレーム)で書け、フレーム間隔 16 では帯が千切れて 10 → 49 台。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/02_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/02_scene.png)

*↑ 測定の図*

[![トラックは画像の 50 行から 99 行を占めるので、遠い車線の計数行 63 を横切る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/03_tall_vehicles_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/03_tall_vehicles.png)

*↑ トラックは画像の 50 行から 99 行を占めるので、遠い車線の計数行 63 を横切る。*

[![全部の帯を数えると千切れて過大に(実測は最大 67 だが、他の系列が潰れるので 20 で頭打ちにして描いている)、計数列と交わる帯だけなら見逃しだけ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/04_framerate_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/04_framerate.png)

*↑ 全部の帯を数えると千切れて過大に(実測は最大 67 だが、他の系列が潰れるので 20 で頭打ちにして描いている)、計数列と交わる帯だけなら見逃しだけ。*

[![動画(768 × 422、10 fps、210 コマ = 撮った速さ): 2 車線の道路を 18 秒。上段はカメラの画に前景マスク(橙)と計数列(黄の縦線)を重ねたもの、下段は 2 車線の計数行を時間方向に積んだスリット画像 (t, x) ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/05_counting_video.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/05_counting_video.gif)

*↑ 動く図 ―― 動画(768 × 422、10 fps、210 コマ = 撮った速さ): 2 車線の道路を 18 秒。上段はカメラの画に前景マスク(橙)と計数列(黄の縦線)を重ねたもの、下段は 2 車線の計数行を時間方向に積んだスリット画像 (t, x) が上から伸びていく —— 車 1 台が斜めの帯 1 本になり、傾きが速度。見出しの数字は時刻までの累積で、最後は 真値 10 / 仮想ループ 10 / スリット法 10 台と同点(途中で真値が遅れて見えるのは、真値を車体の中心で、ループとスリットを車体の先端で数えるため)。フレームごとに連結成分を数えるゼロ点は最大 7 で、「いま写っている数」を数えているだけ。*

```
py -3.11 examples/poc_traffic_counting.py
```

ソース: [examples/poc_traffic_counting.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_traffic_counting.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_traffic_counting)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`data_to_pixel`](https://furuse.work/ops/annotate/plot/data_to_pixel.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html)

## No.2026.089 —— 庫内の滞留はどこで生まれたか ―― 待ちの種類を分けずに数えると全部「混雑」になる

[![庫内の滞留はどこで生まれたか ―― 待ちの種類を分けずに数えると全部「混雑」になる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/09_scene_layout_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/09_scene_layout.png)

*↑ **庫内の滞留はどこで生まれたか ―― 待ちの種類を分けずに数えると全部「混雑」になる** ―― 物流センターの平面図と 26 台の軌跡を合成し、補充待ち・人待ち・通路の干渉・システム待ち・欠品を既知の時刻と長さで仕込んで、動画を (t, y, x) の 1 つの体積として読んだ図。ゼロ点の「総滞留時間」321.5 秒のうち真の待ちは 198.0 秒(61.6 %)で、残りは生産的な作業と徐行。人待ちを全部止めても通路の干渉を全部止めてもゼロ点は -39.0 / -38.0 秒しか違わず原因が決まらないが、種類別なら該当の型だけが 0 に落ちる。欠品は滞留を -17.0 秒しか動かさないのに余計な移動を 94.6 m 生み、崖は 3 軸で別々の型を殺す ―― 標本間隔は短い待ち、遮蔽は棚に張りつく型、ID の併合は 2 人の関係を読む型。*

[![ヒートマップは場所を当てるが、「1 人が長く待った」と「何人も短く止まった」を分けない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/01_heat_ambiguity_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/01_heat_ambiguity.png)

*↑ 測定の図 ―― ヒートマップは場所を当てるが、「1 人が長く待った」と「何人も短く止まった」を分けない。*

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

ソース: [examples/poc_warehouse_flow.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_warehouse_flow.py)

この回が作った図は全部で **12 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_warehouse_flow)

使用 op(ノートへ): [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`face_areas`](https://furuse.work/ops/3d/mesh_process/face_areas.html) · [`mesh_volume`](https://furuse.work/ops/3d/mesh_process/mesh_volume.html) · [`occupancy_grid`](https://furuse.work/ops/3d/occupancy/occupancy_grid.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`vol_dilate`](https://furuse.work/ops/2d/3d/vol_dilate.html) · [`vol_erode`](https://furuse.work/ops/2d/3d/vol_erode.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_opening_ball`](https://furuse.work/ops/2d/3d/vol_opening_ball.html) · [`vol_region_props`](https://furuse.work/ops/3d/regionprops/vol_region_props.html)

## No.2026.053 —— 到達時刻面を (x, y, t) の等値面として取り出す

[![到達時刻面を (x, y, t) の等値面として取り出す](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/01_dt_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/01_dt_sweep.png)

*↑ **到達時刻面を (x, y, t) の等値面として取り出す** ―― 点源から広がる波面の到達時刻面を (x, y, t) 体積の等値面として取り出した図。ゼロ点(初めて超えたフレーム番号)の偏りは Δt/2 で枚数では消えず、線形補間で 27 倍(0.0209 ms)。放物線補間は線形に負け、しきい値がガウス波形の変曲点 θ = 0.6065 にあるとき線形が最良(3.8 倍差)。*

[![変曲点 θ=0.6065 では線形が 3.8 倍勝ち、θ=0.2 では放物線が 3.6 倍勝つ。交点は θ≈0.35 と θ≈0.75。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/02_threshold_crossover_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/02_threshold_crossover.png)

*↑ 測定の図 ―― 変曲点 θ=0.6065 では線形が 3.8 倍勝ち、θ=0.2 では放物線が 3.6 倍勝つ。交点は θ≈0.35 と θ≈0.75。*

[![各帯の中央値。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/03_merge_line_speed_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/03_merge_line_speed.png)

*↑ 各帯の中央値。*

[![差は上下 99 % 分位(±0.0327 ms)で切った。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/04_arrival_surface_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/04_arrival_surface.png)

*↑ 差は上下 99 % 分位(±0.0327 ms)で切った。*

[![動画(624 × 586、20 fps、171 コマ): 2 つの点源から波面が広がる(源 B は 4 ms 遅れて点火)。左が波面の強度、右は線形補間で出した到達時刻を、波面が通り過ぎた画素から順に塗ったもの —— 動画 (t, y, x](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/05_arrival_video.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/05_arrival_video.gif)

*↑ 動く図 ―― 動画(624 × 586、20 fps、171 コマ): 2 つの点源から波面が広がる(源 B は 4 ms 遅れて点火)。左が波面の強度、右は線形補間で出した到達時刻を、波面が通り過ぎた画素から順に塗ったもの —— 動画 (t, y, x) を1 つの体積とみなしたときの等値面が、こうして 1 枚の面になる。点線は撮る前に閉形式で予測した合流線。下段は行 72 の断面で、白 = 真値、橙 = ゼロ点(初めてしきい値を超えたコマの時刻、1 ms の階段)、青 = 線形補間。最後に全画素の誤差: ゼロ点 RMS 0.568 ms(偏り +0.489)、線形補間 RMS 0.0209 ms(27 倍)。*

```
py -3.11 examples/poc_xyt_event_surface.py
```

ソース: [examples/poc_xyt_event_surface.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_xyt_event_surface.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_xyt_event_surface)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`data_to_pixel`](https://furuse.work/ops/annotate/plot/data_to_pixel.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html) · [`vertex_normals`](https://furuse.work/ops/3d/mesh_process/vertex_normals.html) · [`vol_edge_probe`](https://furuse.work/ops/3d/probe/vol_edge_probe.html)

## No.2026.127 —— 動画を空間 × 時間の立方体として見る ―― 何が・どこを・いつ通ったかが 1 枚の立体に出る

[![動画を空間 × 時間の立方体として見る ―― 何が・どこを・いつ通ったかが 1 枚の立体に出る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/02_cube_orbit.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/02_cube_orbit.gif)

*↑ **動画を空間 × 時間の立方体として見る ―― 何が・どこを・いつ通ったかが 1 枚の立体に出る** ―― Video Summagator(Nguyen・Niu・Liu、ACM CHI 2012)は動画を (x, y, t) の立方体にし、動かない背景を薄く・動く物体を濃く描いて、切ったり回したりして場面へ飛ぶ道具。同じことを新族 videocube の 6 op(numpy + scipy のみ、新しい型なし)で再実装した: 時間差分の大きさを不透明度に(video_spacetime_cube)、任意視点の前から後ろへの α 合成で軌跡を時刻の色(青 = 始め → 赤 = 終わり)に塗る(vol_render_transfer)、断面(video_cube_cut: x–t のスリットスキャン)、回す(video_cube_orbit)、代表フレーム(video_summary_keyframes)、アニメーション GIF に書く(video_write_gif、使い回しの出口)。監視カメラ風の合成クリップ(通過の行・時刻・速度が既知の 3 物体)で、スリットスキャンの筋の最初の行と傾きから読んだ出現時刻と速度は真値と一致(±0 フレーム、速度 +2.00 / −1.50 / +1.00)、代表フレームは 3 物体すべての出現直後を捉える(乱数で 4 枚選ぶと平均 0.21 物体)。同じ op でハエの脳の EM 連続断面(CREMI sample A、32 断面、生データは commit しない)を立方体にすると、膜が奥行きの色で塗られた管になって神経突起が断面を貫いて走る。Studio では Tools ▸ Video cube が対話的に動く(ドラッグで回転、断面のスライダ、断面をクリックでそのフレームへ、.npy / GIF / 動画 / .hdf のスタックを開く、Save GIF)。*

[![the clip as a space-time cube (time = depth to the right): moving objects leave trails coloured by time (blue = start, r](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/01_cube_time_coloured_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/01_cube_time_coloured.png)

*↑ 測定の図 ―― the clip as a space-time cube (time = depth to the right): moving objects leave trails coloured by time (blue = start, red = end); the static background is a faint grey*

[![x-t slit scans of the three rows: a streak's first row is the onset, its slope is the speed (yellow ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/03_slit_scans_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/03_slit_scans.png)

*↑ x-t slit scans of the three rows: a streak's first row is the onset, its slope is the speed (yellow line = injected onset)*

[![video_summary_keyframes picks the frames right after each object appears; the head-on cube is the wh](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/04_keyframes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/04_keyframes.png)

*↑ video_summary_keyframes picks the frames right after each object appears; the head-on cube is the whole clip in one image*

[![a real clip from this repo (a turntable GIF, 40 frames of 160x160): a rotating object becomes a heli](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/05_turntable_cube_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/05_turntable_cube.png)

*↑ a real clip from this repo (a turntable GIF, 40 frames of 160x160): a rotating object becomes a helix in the space-time cube*

[![the same cube operators on a z-stack of EM sections (CREMI sample A, 32 sections of 256^2 (adult Dro](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/06_em_stack_cube_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/06_em_stack_cube.png)

*↑ the same cube operators on a z-stack of EM sections (CREMI sample A, 32 sections of 256^2 (adult Drosophila FAFB)): membranes become tubes running thr…*

[![the EM stack rotating: neurites are the tubes, coloured by depth; the same operator that rotated the surveillance clip](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/07_em_stack_orbit.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/07_em_stack_orbit.gif)

*↑ 動く図 ―― the EM stack rotating: neurites are the tubes, coloured by depth; the same operator that rotated the surveillance clip*

```
py -3.11 examples/poc_video_cube.py
```

ソース: [examples/poc_video_cube.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_video_cube.py)

この回が作った図は全部で **7 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_video_cube)

使用 op(ノートへ): [`intensity`](https://furuse.work/ops/2d/features/intensity.html) · [`video_cube_cut`](https://furuse.work/ops/videocube/cube/video_cube_cut.html) · [`video_cube_orbit`](https://furuse.work/ops/videocube/render/video_cube_orbit.html) · [`video_spacetime_cube`](https://furuse.work/ops/videocube/cube/video_spacetime_cube.html) · [`video_summary_keyframes`](https://furuse.work/ops/videocube/summary/video_summary_keyframes.html) · [`video_write_gif`](https://furuse.work/ops/videocube/export/video_write_gif.html) · [`vol_render_transfer`](https://furuse.work/ops/videocube/render/vol_render_transfer.html)

## No.2026.128 —— 生きている組織の 3D+t を古典手法だけで短い 3D 動画像に ―― 増幅・流れ・補間・高さ場、全部に真値

[![生きている組織の 3D+t を古典手法だけで短い 3D 動画像に ―― 増幅・流れ・補間・高さ場、全部に真値](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/01_beating_orbit.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/01_beating_orbit.gif)

*↑ **生きている組織の 3D+t を古典手法だけで短い 3D 動画像に ―― 増幅・流れ・補間・高さ場、全部に真値** ―― 動画生成 AI は「もっともらしい動き」を発明する。新族 live4d(14 op、numpy + scipy のみ、新語は volseq = 体積の時系列 (T, Z, Y, X) の 1 つ)は内容を発明しない代わりに、実在する動きを見える形にする 4 つの道を用意し、どれも真値つきの合成系列で数字に固定した。(1) 増幅: 半径が 0.1 voxel(目に見えない)だけ拍動する殻を volseq_magnify_motion(Wu らの Eulerian 線形拡大の 3 次元版)で 8 倍にすると、読み取った半径の振幅は 7.89 倍、周期は不変。(2) 流れ: 既知の速さ ±0.75 voxel/frame で分かれる 2 つの塊の変位場(vol_flow_3d、3 次元 Lucas–Kanade)は勾配のある場所で +0.776 / −0.776、軌跡(volseq_pathline_render)は時刻の色で 1 枚の立体になる。(3) 補間: 2 倍のレートで作った系列を半分に間引いて volseq_interpolate_flow で埋めると、1 コマの動きが塊の大きさの 2 倍のとき抜いた真のフレームとの RMSE は 0.0016(線形ブレンドは 0.0207)—— ただし動きが約 0.8 σ より小さい領域ではブレンドで足り、warp の再標本化が少し損をする(正直に図にした)。(4) 高さ場: 焦点掃引の時系列(動く山)から focus_sweep_height_video が起こした高さは真値と RMSE 0.31 枚。Cell Tracking Challenge の生きた細胞の 3D+t(Fluo-N3DH-CHO、生データは commit しない)も同じ経路で回る。*

[![radius of the shell read from each volume: the measured beat (0.10 voxel) is below one voxel; after magnification it fol](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/02_radius_trace_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/02_radius_trace.png)

*↑ 測定の図 ―― radius of the shell read from each volume: the measured beat (0.10 voxel) is below one voxel; after magnification it follows alpha x truth*

[![pathlines of particles carried by the 3-D flow of the dividing blob, coloured by time (blue = start,](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/03_pathlines_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/03_pathlines.png)

*↑ pathlines of particles carried by the 3-D flow of the dividing blob, coloured by time (blue = start, red = end); the faint grey is the first volume*

[![a frame removed from a 2x-rate series (motion 5 voxel = 2 sigma per step) re-created two ways (max p](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/05_interpolation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/05_interpolation.png)

*↑ a frame removed from a 2x-rate series (motion 5 voxel = 2 sigma per step) re-created two ways (max projections): the linear blend shows two ghosts per…*

[![error of the re-created frames against the removed ones, as the motion per step grows: below about o](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/06_interpolation_regimes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/06_interpolation_regimes.png)

*↑ error of the re-created frames against the removed ones, as the motion per step grows: below about one blob width a linear blend is as good (the warp'…*

[![Fluo-N3DH-CHO/01 (12 volumes of (5, 111, 128), y/x 1/4): pathlines of the 3-D flow between consecuti](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/09_ctc_pathlines_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/09_ctc_pathlines.png)

*↑ Fluo-N3DH-CHO/01 (12 volumes of (5, 111, 128), y/x 1/4): pathlines of the 3-D flow between consecutive volumes, coloured by time*

[![the same pathlines orbited: two straight bundles leaving the split point at +/-0.75 voxel/frame](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/04_pathlines_orbit.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/04_pathlines_orbit.gif)

*↑ 動く図 ―― the same pathlines orbited: two straight bundles leaving the split point at +/-0.75 voxel/frame*

[![height field recovered from a focus sweep series (a moving bump, 11 planes), shaded and coloured by height (blue = low, ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/07_focus_surface.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/07_focus_surface.gif)

*↑ 動く図 ―― height field recovered from a focus sweep series (a moving bump, 11 planes), shaded and coloured by height (blue = low, red = high); RMSE 0.31 planes*

[![Fluo-N3DH-CHO/01 (12 volumes of (5, 111, 128), y/x 1/4): the live volumes orbited while time advances (intensity as opac](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/08_ctc_orbit.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/08_ctc_orbit.gif)

*↑ 動く図 ―― Fluo-N3DH-CHO/01 (12 volumes of (5, 111, 128), y/x 1/4): the live volumes orbited while time advances (intensity as opacity)*

```
py -3.11 examples/poc_live4d.py
```

ソース: [examples/poc_live4d.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_live4d.py)

この回が作った図は全部で **10 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_live4d)

使用 op(ノートへ): [`blend`](https://furuse.work/ops/shape2d/morph/blend.html) · [`focus_sweep_height_video`](https://furuse.work/ops/live4d/render/focus_sweep_height_video.html) · [`focus_sweep_surface_video`](https://furuse.work/ops/live4d/render/focus_sweep_surface_video.html) · [`vol_flow_3d`](https://furuse.work/ops/live4d/flow/vol_flow_3d.html) · [`volseq_interpolate_flow`](https://furuse.work/ops/live4d/time/volseq_interpolate_flow.html) · [`volseq_magnify_motion`](https://furuse.work/ops/live4d/time/volseq_magnify_motion.html) · [`volseq_pathline_orbit`](https://furuse.work/ops/live4d/flow/volseq_pathline_orbit.html) · [`volseq_pathline_render`](https://furuse.work/ops/live4d/flow/volseq_pathline_render.html) · [`volseq_render_orbit`](https://furuse.work/ops/live4d/render/volseq_render_orbit.html) · [`volseq_synth_beating`](https://furuse.work/ops/live4d/synth/volseq_synth_beating.html) · [`volseq_synth_dividing`](https://furuse.work/ops/live4d/synth/volseq_synth_dividing.html)

## No.2026.170 —— 卓球の球を先駆者の目で測る ―― 真値つきの台で、多カメラ追跡・三角測量・軌道予測・跳ね・スピンを定理で採点する

[![卓球の球を先駆者の目で測る ―― 真値つきの台で、多カメラ追跡・三角測量・軌道予測・跳ね・スピンを定理で採点する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/01_rig_view_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/01_rig_view.png)

*↑ **卓球の球を先駆者の目で測る ―― 真値つきの台で、多カメラ追跡・三角測量・軌道予測・跳ね・スピンを定理で採点する** ―― ロボット卓球の視覚は 1988 年から同じ構えでできている: 複数のカメラで球を見つけ、三角測量で 3-D の点にし、抗力とマグヌスの入った運動方程式で先を読み、跳ねを越えて予測し、できれば模様からスピンを測る。この展示はその一式を numpy の op で組み、世界の側が持つ真値(球の中心・姿勢・接触時刻・角速度は生成時に決めた式)で採点する。まず力学の定理: 抗力もマグヌスも 0 なら RK4 の飛翔は閉形式の放物線と 1e-12、放物線の最小二乗は g = 9.81 を 4.0e-15 で戻す。乱数 500 通りの衝突(e ∈ [0.3, 1]、μ ∈ [0, 0.6])で接触点まわりの角運動量の相対誤差は最大 4.9e-16、転がりに移るのが 136、滑ったままが 364。30.5 cm から落とすと(e = 0.90)頂点は 24.7、20.0、16.2、13.1 cm で閉形式 e^{2k}h₀ と 3.0e-07、最初の跳ね 24.7 cm は ITTF の規格 24〜26 cm の中、頂点列からも接触間隔からも e = 0.900000 が戻り、止まるまでの総時間 4.736 s は閉形式 4.738 s と並ぶ。次にITTF の台に 40 mm の球(模様 14 個)を置き、トップスピン(ω = 240 rad/s)の打球を 100 fps で 0.6 秒、カメラ 2 台 + 近接 1 台で撮る(61 コマ × 2 台の描画に 22.0 s)。真値の接触は t = 0.3094 s、点 (0.507, 0.052)、v [5.15, −0.28, −2.65] → [5.01, −0.17, 2.39]、ω [0, 240, 0] → [8.5, 250.6, 0](grip)。色度で検出した中心は 122 / 122 コマで見つかり真値の投影と中央値 0.152 px、90 % 点 0.299 px、最大 2.094 px(像の半径 ≈ 4.3 px)。DLT の三角測量は真値の投影から 3.8e-15 m、検出からは中央値 1.61 mm、90 % 点 4.25 mm、最大 23.56 mm(再投影 rms の中央値 0.094 px)。等加速度の Kalman は放物線に厳密なので真値を入れた新息は最大 8.2e-09 m(抗力 + マグヌスの真値だと 2.3e-03 m = モデルの外)、検出からの速度の誤差は中央値 0.074 m/s(|v| ≈ 5.9 m/s)。z の局所最小は t = 0.31 で真値と 0.6 ms。跳ねる前の 15 コマ(0.15 s)から 6 パラメータの Gauss–Newton で初期状態を当て(真値の軌跡なら 3.2e-13 で戻る)、跳ねを越えて予測すると、真のスピンを知っていれば着地点は 0.4 cm(時刻 0.5 ms)、スピンを無視すると 20.2 cm、放物線で当てると真のスピンでも 6.6 cm 外れる —— その差がマグヌスの分。跳ね際の近接カメラ(1000 fps、ストロボ)で模様が 2 つ以上対応づいたコマ組 19 / 19 を Kabsch で回した角速度の中央値は [1.7, 256.6, −2.1] rad/s(真値 [8.5, 250.6, 0]、|ω| 2394 rpm)で相対誤差 3.7 %。反発係数は前後 12 コマずつを運動方程式で当てて v_z −2.637 → 2.403、e = 0.9114(真値 0.90)。正直に: 放物線の当てはめだと 0.9398 で、抗力とマグヌスを g に吸って 4.4 % ずれる。球の検出は色が既知の合成映像で実写の照明・ぼけ・背景は無く、空力係数は文献の代表値で真値も同じ式(空力の門ではない)。10 門、42.0 s。最後に、自由に動くラケット 2 本(板 15 × 16 cm、速さ ≤ 6 m/s)で打ち合う: 前回に近い少しずらした位置へ返す送り合いは上限 12 本まで続き、遠い隅を速く狙う攻める側が入ると 9 本で終わる(打つ前に真の物理で先読みして外すなら巻き戻す仕組みつき、攻める側は 99 回巻き戻しても外した)。知覚の位置に雑音を足すと 5 cm までは本数が変わらず(板の余裕)、10 cm で 2 本 —— ラリーの本数が知覚・予測・制御の一式を採点する指標。*

[![カメラ 1 の像での球の軌跡: 真値の投影(線)と検出(点)。中心の誤差の中央値 0.15 px。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/02_tracks_2d_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/02_tracks_2d.png)

*↑ 測定の図 ―― カメラ 1 の像での球の軌跡: 真値の投影(線)と検出(点)。中心の誤差の中央値 0.15 px。*

[![x–z 面の軌跡。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/03_trajectory_xz_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/03_trajectory_xz.png)

*↑ x–z 面の軌跡。*

[![30.5 cm から落とした球(e = 0.90)の頂点: 閉形式 e^{2k}h₀ と 1e-6 で一致し、最初の跳ね 24.7 cm は ITTF の規格 24〜26 cm の中。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/04_drop_apexes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/04_drop_apexes.png)

*↑ 30.5 cm から落とした球(e = 0.90)の頂点: 閉形式 e^{2k}h₀ と 1e-6 で一致し、最初の跳ね 24.7 cm は ITTF の規格 24〜26 cm の中。*

[![跳ね際の近接カメラ(1000 fps、256 × 256、20°)の 4 コマ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/05_spin_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/05_spin_frames.png)

*↑ 跳ね際の近接カメラ(1000 fps、256 × 256、20°)の 4 コマ。*

[![知覚(球の位置)にガウス雑音を足したときのラリーの本数(送り合い、上限 8 本): 0 mm → 8 本、50 mm → 8 本、100 mm → 2 本。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/08_rally_vs_noise_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/08_rally_vs_noise.png)

*↑ 知覚(球の位置)にガウス雑音を足したときのラリーの本数(送り合い、上限 8 本): 0 mm → 8 本、50 mm → 8 本、100 mm → 2 本。*

[![追跡カメラ 1(2 × 2 平均で 512 × 400)、100 fps を 1/10 速で。橙の十字は検出、緑は Kalman の状態の投影、赤は跳ねる前の 15 コマから予測した着地点。球は 2291 rpm のトップスピンで、台で 1](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/06_rally_gif.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/06_rally_gif.gif)

*↑ 動く図 ―― 追跡カメラ 1(2 × 2 平均で 512 × 400)、100 fps を 1/10 速で。橙の十字は検出、緑は Kalman の状態の投影、赤は跳ねる前の 15 コマから予測した着地点。球は 2291 rpm のトップスピンで、台で 1 度跳ねる(e = 0.90)。*

[![自由に動く 2 本のラケット(板 15 × 16 cm、速さ ≤ 6 m/s、加速度 ≤ 60 m/s²)の送り合い(前回に近い少しずらした位置へ返す)、最初の 3 秒を 1/5 速で。相手コートに 1 度跳ねた球を面 x = ±1.55 ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/07_rally_two_rackets.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/07_rally_two_rackets.gif)

*↑ 動く図 ―― 自由に動く 2 本のラケット(板 15 × 16 cm、速さ ≤ 6 m/s、加速度 ≤ 60 m/s²)の送り合い(前回に近い少しずらした位置へ返す)、最初の 3 秒を 1/5 速で。相手コートに 1 度跳ねた球を面 x = ±1.55 m で迎え撃ち、狙った点へ運動方程式で返す。この設定では上限 12 本まで続く。攻める側(遠い隅を速く)が入ると 9 本で終わる(out)。*

```
py -3.11 examples/poc_ball_bounce.py
```

ソース: [examples/poc_ball_bounce.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ball_bounce.py)

この回が作った図は全部で **8 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_ball_bounce)

使用 op(ノートへ): [`add_ball`](https://furuse.work/ops/drive/ballworld/add_ball.html) · [`apex_sequence`](https://furuse.work/ops/drive/ball/apex_sequence.html) · [`ball_detect`](https://furuse.work/ops/drive/balltrack/ball_detect.html) · [`ball_mesh`](https://furuse.work/ops/drive/ballworld/ball_mesh.html) · [`ball_params`](https://furuse.work/ops/drive/ball/ball_params.html) · [`ball_set_pose`](https://furuse.work/ops/drive/ballworld/ball_set_pose.html) · [`ball_track`](https://furuse.work/ops/drive/balltrack/ball_track.html) · [`ball_truth`](https://furuse.work/ops/drive/ballworld/ball_truth.html) · [`bounce`](https://furuse.work/ops/drive/ball/bounce.html) · [`bounce_detect`](https://furuse.work/ops/drive/balltrack/bounce_detect.html) · [`bounce_total_time`](https://furuse.work/ops/drive/ball/bounce_total_time.html) · [`camera_rig`](https://furuse.work/ops/drive/ballworld/camera_rig.html) · [`contact_angular_momentum`](https://furuse.work/ops/drive/ball/contact_angular_momentum.html) · [`crosshair`](https://furuse.work/ops/annotate/pointer/crosshair.html) · [`fit_parabola`](https://furuse.work/ops/drive/ball/fit_parabola.html) · [`flight_fit`](https://furuse.work/ops/drive/ball/flight_fit.html) · [`flight_ode`](https://furuse.work/ops/drive/ball/flight_ode.html) · [`flight_simulate`](https://furuse.work/ops/drive/ball/flight_simulate.html) · [`flight_state_at`](https://furuse.work/ops/drive/ball/flight_state_at.html) · [`flight_vacuum`](https://furuse.work/ops/drive/ball/flight_vacuum.html) · [`impact_params`](https://furuse.work/ops/drive/ball/impact_params.html) · [`kalman_ca`](https://furuse.work/ops/drive/balltrack/kalman_ca.html) · [`marker_direction`](https://furuse.work/ops/drive/balltrack/marker_direction.html) · [`racket_params`](https://furuse.work/ops/drive/racket/racket_params.html) …(他 12)

## No.2026.171 —— けん玉を先駆者の目で ―― 本物の形のけん玉を 2 台のカメラで撮り、画像だけから玉の軌道を予測して大皿・小皿・中皿で受ける

[![けん玉を先駆者の目で ―― 本物の形のけん玉を 2 台のカメラで撮り、画像だけから玉の軌道を予測して大皿・小皿・中皿で受ける](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/01_rig_view_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/01_rig_view.png)

*↑ **けん玉を先駆者の目で ―― 本物の形のけん玉を 2 台のカメラで撮り、画像だけから玉の軌道を予測して大皿・小皿・中皿で受ける** ―― けん玉をロボットにやらせた研究は 30 年続いている(1996 年の人の手本からの via-point、2009 年の DMP + 強化学習の ball-in-a-cup、2020 年の「振り上げはオフライン・キャッチはオンライン」の 2 段割り)。この展示はその構えを numpy の op で組み直した。形: 日本けん玉協会の公表値(玉 60 mm、横幅 70 mm、全長 180 mm)とユーザー提供の JKA 16-2 型の説明(けんの高さ 160 mm、皿 大皿 42・中皿 38・小皿 35 mm、糸は皿胴の穴から。一次資料は未確認)で、けん(けん先 → 細い首 → 皿胴を貫く胴 → 段と輪のある握り → 中皿)と皿胴(両端がラッパのように開いて大皿・小皿)を回転体で、穴(直径 17 mm・深さ 40 mm のくぼみ)のある玉を作り、寸法を頂点から測ると全部 1e-9 で一致、けん先を穴の底まで挿した全長も 180 mm(穴の深さ 40 mm は 160 + 60 − 180 で導いた値)。力学の定理: K(0.5) = 1.685750354812596 を AGM が 1e-12、周期 4√(L/g)K(sin θ₀/2) をひも(有効長 0.42 m)が 3.0e-4・棒が 8.9e-11、張力の閉形式と最大 0.26 %、弛む角 125.04°(閉形式 125.26°)、射影法の散逸は dt に 1 次(比 9.7)、snap の落ちは ½mv_r² と 0.2 %。閉ループの根拠は画像だけ: 2 台のカメラ(480 × 360、100 fps)で世界を描き、色度で玉を検出して三角測量(誤差 中央値 0.51 mm)、玉と皿胴の糸穴の距離がひもより 5 mm 短いコマが 2 回続いたら弛んだとし(真値 0.077 s、画像 0.100 s)、その後のコマに重力つきの放物線(未知 6)を当てて玉の着地点を読む。真値 (p, v) は世界を描くためだけに使う。制御は段階を明示した: 膝で真上に引き上げる(4.9 g、けんは糸穴の側へ 10 cm 逃がす)→ 弛むまで待つ → 玉の下端がけん玉を越えるまで待つ → 皿を玉の真下へ水平に運ぶ → 着地で下げる。玉を動かすのは重力とひもの張力だけで、けんが玉に触れたら失敗(逃がさない振り上げは 0.260 s に皿胴に当たる)。同じ計画で技の姿勢だけを切り替え、20 試行の成功率は 大皿 真値 1.00・画像 1.00(横ずれ 2.40 mm)、小皿 1.00・1.00、中皿 0.95・0.95、ろうそく(真値)0.95。着地で下げると相対速さの平均は 0.91 → 0.61 m/s(大皿)。落下点の予測誤差は弛んだ後のコマ数とともに 10.51 mm(3 コマ)→ 0.98 mm(44 コマ)と減る。画素雑音 0 / 0.5 / 1 / 2 / 8 / 16 px の成功率は 1.00 / 1.00 / 1.00 / 1.00 / 0.90 / 0.40 —— 2 px まで平らなのは皿の縁の余裕(半径 21 mm)が吸う分で、横ずれは 2.40 → 4.12 → 12.05 mm と増える。推奨品(大皿 49 mm)も 1.00。玉の穴は静止した玉なら 2 台の三角測量で向きの誤差 中央値 1.8°・最大 4.7°。世界を 3D Gaussian Splatting にしてから認識もした(gsplatnp: 世界の面にガウシアンを貼り、EWA 投影・手前からの α 合成・Mip-Splatting の不透明度の補正で描く。ガウシアンは写真から学習したものでなく真の形から作り、再構成の不完全さは間隔と誤差のつまみで模す): 間隔 4 mm の 3DGS の画像だけで閉ループは 1 + 2 試行すべて捕り(三角測量の誤差 中央値 0.30 mm)、間隔を 2〜64 mm に振っても玉の検出率は 1.00(曲率の上限で玉の上には 146 個以上が残る)、崩すのは位置の誤差(20 mm で 0.25)と色の誤差(0.3 で 0.00)。玉の穴は 480 × 360 では 3DGS のぼけに塗りつぶされ(40 姿勢で 1、メッシュは 14)、解像度 × 2・間隔 2 mm で 16(誤差 中央値 2.3°)、間隔 4 mm では 0 —— 穴を読むには玉に画素が、穴の中にガウシアンが要る。穴は表面に貼った円盤でなく深さ 40 mm のくぼみとして作る(円盤だと 3DGS では手前の玉のガウシアンに覆われて消えた)。連続技も入れた(ユーザー「受けたら、受けた状態から続けて別の皿で受けて」「10 回成功すれば良し」): 受けた皿から放ち(皿を上へ加速して g より強く止めると玉が皿から離れる、頂点は v²/2g の閉形式と 2e-6 m)、飛んでいる間に持ち替えて(手首 ≤ 30 rad/s、仮定)次の皿を着地点の真下へ運び、位置と速度を目標にする手元の制御で速さを合わせて受ける(位置だけの制御は頂点 20 cm で 1 回も受けられない)。画像だけで もしかめ(大皿 ↔ 中皿)も 3 皿(大皿 → 小皿 → 中皿)も 10 回連続(協会のもしかめの級で 5 級相当)、着地の相対速さ 0.41〜0.48 m/s、飛び始めも毎回画像から。正直に: 雑音が無いと 100 回でも同じ 1 周期の繰り返しで、画素雑音 2 px では もしかめ 3 回・3 皿 6 回で崩れる。正直に: 実写でなく真値つきの合成映像、玉の回転は解かない(弛んだら最後の姿勢のまま)、捕球は「縁に触れた瞬間に横ずれ ≤ 縁の半径・相対速さ ≤ 1 m/s(仮定の閾値)・下降中」の判定で跳ねと転がりは扱わない、皿持ちの傾き 15°・皿の深さ・玉 75 g などは仮定。飛翔中の穴は下を向き、目の高さの 2 台からは 2 台同時にはほぼ見えない(54 コマ中 0)。ろうそくが中皿より難しい理由は剛体・並進だけの手元では表せない。16 門、171.0 s。*

[![近接カメラ(図のためだけ、けん玉から 0.36 m)で見た 4 技の持ち方の姿勢(けんと皿胴は 1 つの剛体、持つ所だけが違う)。けん(けん先 → 細い首 → 皿胴を貫く胴 → 段と輪のある握り → 中皿)、皿胴の両端がラッパのように開いた](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/02_kendama_closeup_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/02_kendama_closeup.png)

*↑ 測定の図 ―― 近接カメラ(図のためだけ、けん玉から 0.36 m)で見た 4 技の持ち方の姿勢(けんと皿胴は 1 つの剛体、持つ所だけが違う)。けん(けん先 → 細い首 → 皿胴を貫く胴 → 段と輪のある握り → 中皿)、皿胴の両端がラッパのように開いた大皿(赤)・小皿(紫)、中皿(青)、直径 17 mm・深さ 40 mm の穴(くぼみ)のある玉、皿胴の糸穴から出る糸。寸法は JKA 16-2 型(けん 160 mm、横幅 70 mm、皿 42 / 38 / 35 mm)。玉の位置と向きは見せるために置いたもの。*

[![真下から 150° 相当の速さ(3.92 m/s)で打ち出した玉のひも(有効長 0.42 m)の張力。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/03_tension_closed_form_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/03_tension_closed_form.png)

*↑ 真下から 150° 相当の速さ(3.92 m/s)で打ち出した玉のひも(有効長 0.42 m)の張力。*

[![y–z 面(手元を逃がす向き)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/04_catch_yz_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/04_catch_yz.png)

*↑ y–z 面(手元を逃がす向き)。*

[![画像だけの閉ループの成功率(大皿、各 20 試行): 0 px → 1.00、0.5 px → 1.00、1 px → 1.00、2 px → 1.00、8 px → 0.90、16 px → 0.4](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/07_success_vs_pixel_noise_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/07_success_vs_pixel_noise.png)

*↑ 画像だけの閉ループの成功率(大皿、各 20 試行): 0 px → 1.00、0.5 px → 1.00、1 px → 1.00、2 px → 1.00、8 px → 0.90、16 px → 0.40。*

[![3DGS の世界の捕球の試行(弛み → 捕球の 12 コマ)を、つまみを振った 3DGS で描き直して色度の検出(balltrack.ball_detect)にかけた。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/09_gs_noise_knobs_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/09_gs_noise_knobs.png)

*↑ 3DGS の世界の捕球の試行(弛み → 捕球の 12 コマ)を、つまみを振った 3DGS で描き直して色度の検出(balltrack.ball_detect)にかけた。*

[![カメラ 2、100 fps を 1/10 速で(最後のコマで 1 秒止める)。振り上げ → t = 0.077 s にひもが弛む(画像での検出 0.100 s)→ 玉がけんを越えるまで待つ → 皿を水平に運ぶ → 着地で下げる → t = ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/05_catch_gif.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/05_catch_gif.gif)

*↑ 動く図 ―― カメラ 2、100 fps を 1/10 速で(最後のコマで 1 秒止める)。振り上げ → t = 0.077 s にひもが弛む(画像での検出 0.100 s)→ 玉がけんを越えるまで待つ → 皿を水平に運ぶ → 着地で下げる → t = 0.540 s に大皿で受ける。十字は画像の予測(弛んだ後のコマに当てた重力つきの放物線)から読んだ着地点、枠の中は同じカメラでけん玉のまわりを 3 倍の解像度に描き直した窓。t ≈ 0.3 s に玉がけんに重なって見えるのはカメラから見た重なりで、けんは糸穴の側へ 10 cm 逃げて玉の奥にある(その間の隙間の最小 41 mm)。正直に: 捕球は「縁に触れた瞬間に横ずれ ≤ 21 mm・相対速さ ≤ 1 m/s・下降中」の判定で、縁での跳ねと転がりは描いていない。*

[![右 = 閉ループの知覚が実際に見た画像(世界を 3DGS にして描いたもの、カメラ 2、100 fps を 1/10 速)、左 = 同じ瞬間のメッシュ(真の形)。右上の窓 = 同じカメラでけん玉のまわりを 3 倍の解像度に描き直したもの(左](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/10_gs_catch_gif.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/10_gs_catch_gif.gif)

*↑ 動く図 ―― 右 = 閉ループの知覚が実際に見た画像(世界を 3DGS にして描いたもの、カメラ 2、100 fps を 1/10 速)、左 = 同じ瞬間のメッシュ(真の形)。右上の窓 = 同じカメラでけん玉のまわりを 3 倍の解像度に描き直したもの(左はメッシュ、右は同じ 3DGS)。青の輪 = 色度で検出した玉、十字 = 弛んだ後のコマに当てた重力つきの放物線から読んだ着地点。t = 0.541 s に大皿で受ける(横ずれ 4.34 mm、推定 391 回は全部 3DGS の画像から)。*

```
py -3.11 examples/poc_kendama.py
```

ソース: [examples/poc_kendama.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_kendama.py)

この回が作った図は全部で **11 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_kendama)

使用 op(ノートへ): [`ball_detect`](https://furuse.work/ops/drive/balltrack/ball_detect.html) · [`camera_perceiver`](https://furuse.work/ops/drive/kendamaworld/camera_perceiver.html) · [`catch_plan_staged`](https://furuse.work/ops/drive/kendama/catch_plan_staged.html) · [`catch_success_rate`](https://furuse.work/ops/drive/kendama/catch_success_rate.html) · [`crosshair`](https://furuse.work/ops/annotate/pointer/crosshair.html) · [`elliptic_k_agm`](https://furuse.work/ops/drive/kendama/elliptic_k_agm.html) · [`gs_from_world`](https://furuse.work/ops/drive/gsplat/gs_from_world.html) · [`gs_render`](https://furuse.work/ops/drive/gsplat/gs_render.html) · [`gs_render_fn`](https://furuse.work/ops/drive/gsplat/gs_render_fn.html) · [`gs_update`](https://furuse.work/ops/drive/gsplat/gs_update.html) · [`hole_detect`](https://furuse.work/ops/drive/kendama/hole_detect.html) · [`ken_mesh`](https://furuse.work/ops/drive/kendamaworld/ken_mesh.html) · [`kendama_clearance`](https://furuse.work/ops/drive/kendamaworld/kendama_clearance.html) · [`kendama_combo_simulate`](https://furuse.work/ops/drive/kendama/kendama_combo_simulate.html) · [`kendama_params`](https://furuse.work/ops/drive/kendama/kendama_params.html) · [`kendama_pose`](https://furuse.work/ops/drive/kendamaworld/kendama_pose.html) · [`kendama_rig`](https://furuse.work/ops/drive/kendamaworld/kendama_rig.html) · [`kendama_simulate`](https://furuse.work/ops/drive/kendama/kendama_simulate.html) · [`kendama_world`](https://furuse.work/ops/drive/kendamaworld/kendama_world.html) · [`leader_line`](https://furuse.work/ops/annotate/pointer/leader_line.html) · [`overlay_mask`](https://furuse.work/ops/annotate/overlay/overlay_mask.html) · [`pendulum_launch_speed`](https://furuse.work/ops/drive/kendama/pendulum_launch_speed.html) · [`pendulum_period_exact`](https://furuse.work/ops/drive/kendama/pendulum_period_exact.html) · [`pendulum_rod_simulate`](https://furuse.work/ops/drive/kendama/pendulum_rod_simulate.html) …(他 10)

## No.2026.174 —— 回転で曲がる卓球の球を撮って、回転を 2 通りで読む ―― 曲がり方から / 球の模様から

[![回転で曲がる卓球の球を撮って、回転を 2 通りで読む ―― 曲がり方から / 球の模様から](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/03_top_view_sidespin.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/03_top_view_sidespin.gif)

*↑ **回転で曲がる卓球の球を撮って、回転を 2 通りで読む ―― 曲がり方から / 球の模様から** ―― 同じ速さ・同じ向きで打ち出した卓球の球でも、トップスピン(前回転)は沈んで手前に、バックスピン(下回転)は浮いて奥に落ち、横回転は横に逸れる(マグヌス効果、力は ω × v の向き)。この展示は回転だけ違う 4 本(150 rad/s ≈ 1,430 rpm)を 2 台のカメラ(240 fps)で撮り、回転を **2 通りで読む**。曲がり方から: 三角測量した跳ねる前の軌跡に、抗力 + マグヌスの運動方程式を位置・速度・回転の 9 パラメータで当てる(新しい op fit_spin、減衰つきの当てはめ)。垂直成分の誤差はトップ 3.9 %・バック 0.9 %・横 1.7 %、読んだ回転で先読みした着地点は 4 本とも真値と 2 cm 以内(x = [0.488, 0.754, 1.124] m、順はトップ < 無回転 < バック)。模様から: 同じ打球を近接カメラ(1000 fps、20 コマ)で撮り、黒い模様(14 個)の動きを Kabsch で当てる —— 4.8 %・3.2 %・0.9 %。2 つの測り方は独立(片方は軌跡だけ、片方は模様だけを見る)で、互いに 10 % 以内に一致する(第 2 実装の門)。定理の門: マグヌスの力は ω × v なので、進行方向に平行な回転は力を生まない —— 瞬間の加速度の差は 1e-12 未満、0.25 s 飛んでも 7.1 mm(垂直な回転なら 5.4 cm)。だから fit_spin はこの成分を分けて返し、無回転の球で当てはめが出した 22 rad/s の回転はほとんどこの読めない向きにある。軌跡が短いと曲がりが検出の誤差に埋もれて読めない(400.3 % → 4.0 %)。見つけたこと: 打つ側のカメラから見ると、ネットの向こうで低く飛ぶ球の上半分がネットの白帯に隠れ、検出の中心がずれる(三角測量で最大 26 mm)—— 半径が前後の 0.8 倍未満の検出を捨てる。模様の向きを出す op(marker_direction)は球を光軸上とみなしていたので、画面を横切る球では視線の変化がそのまま見かけの回転になった(1 ms で 0.01 rad、1 コマの回転の 7 %)—— カメラの K を渡すと透視で厳密に解くようにした。正直に: 合成映像(色が既知、実写の照明・ぼけ無し)、空力係数(C_d = 0.4、スピン比の C_L)は真値と当てはめで同じ式、回転は飛行中一定。8 門、34.4 s。*

[![同じ速さ・同じ向き(v₀ = (6.0, 0, 1.3) m/s)で打ち出した 3 本を横から: トップスピン(橙)は沈んで x = 0.49 m、無回転(黄)は 0.75 m、バックスピン(青)は浮いて 1.12 m に落ちる(台の中心か](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/01_side_three_serves.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/01_side_three_serves.gif)

*↑ 測定の図 ―― 同じ速さ・同じ向き(v₀ = (6.0, 0, 1.3) m/s)で打ち出した 3 本を横から: トップスピン(橙)は沈んで x = 0.49 m、無回転(黄)は 0.75 m、バックスピン(青)は浮いて 1.12 m に落ちる(台の中心から)。球は見やすさのため 1.6 倍で描いた。MP4 = 240 fps の全コマ(1/8 スロー)。*

[![曲がり方(軌跡に運動方程式を当てる)と模様(近接カメラの Kabsch)は独立。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/04_two_readings_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/04_two_readings.png)

*↑ 曲がり方(軌跡に運動方程式を当てる)と模様(近接カメラの Kabsch)は独立。*

[![跳ねる前の先頭 n コマだけで回転を読む。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/05_error_vs_length_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/05_error_vs_length.png)

*↑ 跳ねる前の先頭 n コマだけで回転を読む。*

[![近接カメラ(1000 fps、20 コマ = 20 ms)のトップスピン。黒い模様(14 個、見えるのは 4〜6 個)を前のコマと向きで対応づけ、Kabsch で回転を当てる: ω = [-0.7, 150.1, -7.2) rad/s(真](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/02_spin_closeup.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/02_spin_closeup.gif)

*↑ 動く図 ―― 近接カメラ(1000 fps、20 コマ = 20 ms)のトップスピン。黒い模様(14 個、見えるのは 4〜6 個)を前のコマと向きで対応づけ、Kabsch で回転を当てる: ω = [-0.7, 150.1, -7.2] rad/s(真値 (0, 150, 0))。1/100 スロー、3 回繰り返し。*

```
py -3.11 examples/poc_table_tennis_spin.py
```

ソース: [examples/poc_table_tennis_spin.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_table_tennis_spin.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_table_tennis_spin)

使用 op(ノートへ): [`add_ball`](https://furuse.work/ops/drive/ballworld/add_ball.html) · [`ball_detect`](https://furuse.work/ops/drive/balltrack/ball_detect.html) · [`ball_mesh`](https://furuse.work/ops/drive/ballworld/ball_mesh.html) · [`ball_params`](https://furuse.work/ops/drive/ball/ball_params.html) · [`ball_set_pose`](https://furuse.work/ops/drive/ballworld/ball_set_pose.html) · [`ball_track`](https://furuse.work/ops/drive/balltrack/ball_track.html) · [`bounce_detect`](https://furuse.work/ops/drive/balltrack/bounce_detect.html) · [`camera_rig`](https://furuse.work/ops/drive/ballworld/camera_rig.html) · [`fit_spin`](https://furuse.work/ops/drive/ball/fit_spin.html) · [`flight_ode`](https://furuse.work/ops/drive/ball/flight_ode.html) · [`flight_simulate`](https://furuse.work/ops/drive/ball/flight_simulate.html) · [`impact_params`](https://furuse.work/ops/drive/ball/impact_params.html) · [`marker_direction`](https://furuse.work/ops/drive/balltrack/marker_direction.html) · [`reproject`](https://furuse.work/ops/drive/balltrack/reproject.html) · [`rotation_from_omega`](https://furuse.work/ops/drive/ballworld/rotation_from_omega.html) · [`spin_from_marker_sequence`](https://furuse.work/ops/drive/balltrack/spin_from_marker_sequence.html) · [`table_params`](https://furuse.work/ops/drive/ballworld/table_params.html) · [`table_world`](https://furuse.work/ops/drive/ballworld/table_world.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`track_triangulate`](https://furuse.work/ops/drive/balltrack/track_triangulate.html) · [`world_camera`](https://furuse.work/ops/drive/world/world_camera.html)

## No.2026.175 —— 跳ねる卓球の球を高速カメラで撮って、反発係数と摩擦係数を読む ―― 公表値と照合する

[![跳ねる卓球の球を高速カメラで撮って、反発係数と摩擦係数を読む ―― 公表値と照合する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_bounce/05_regime_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_bounce/05_regime_map.png)

*↑ **跳ねる卓球の球を高速カメラで撮って、反発係数と摩擦係数を読む ―― 公表値と照合する** ―― 卓球の球が台で跳ねると、縦の速さは反発係数 e の分だけ残り、横の速さと回転は摩擦で入れ替わる。接地点の滑りが小さければ跳ねの途中で止まって**転がりに移り**、大きければ**滑ったまま**離れる。この展示は台の上の跳ね 22 本を横から 1 台の高速カメラ(1000 fps、ROI 読み出し)で撮り、**画像だけから** e・摩擦係数 μ・跳ねの種類を読んで公表値と照合する。運動面が分かっているので 1 台で位置が出る(中心の画素の視線と面の交点)。跳ねの前後に抗力 + マグヌスの運動方程式を当てて接触の瞬間の速度を出し、回転は球の模様から 2 段で読む(新しい op spin_from_marker_sequence)。門: Cross 2002 の閉形式(薄い殻の球: 転がりに移る跳ねは v_x' = 0.6 v_x + 0.4 rω、滑ったままは Δv_t = μ(1+e)|v_z|、境目は (2/5)|s| = μ(1+e)|v_z|)が力積で書いた実装と乱数 300 通りで一致 / ITTF の台の跳ね(Laws 2.1.3: 30 cm → 約 23 cm)を動画から 23.0 cm / e の速さへの依存の傾き -0.00572 /(km/h)がInaba ら 2017 の実測 −0.0058 と 1.4 % / 滑ったままの跳ねから μ = 0.2500(真値 0.25)/ 跳ねの種類が閉形式の境目と 15 / 15 / 転がりに移った跳ねはrω' と v_x' が 3 % 以内 / 摩擦の無い台では横の速さも回転も変わらない。見つけたこと: 30 → 23 cm を e = √(23/30) = 0.876 と読むと空気抵抗の分を落とす —— その台は 21.7 cm しか跳ねず、抗力込みで約 23 cm になる e は 0.9019。Inaba らの式そのもの(切片 1.0002)は 30 cm から 25.5 cm 跳ねる台になり、ITTF と公表値同士で食い違う(研究室の台と規格の差か、測り方の差かは未確認)。転がりに移った跳ねの「見かけの μ」は μ の下界にすぎない。正直に: 合成映像、台の e(v) は ITTF の切片と Inaba らの傾きを継いだ合成、μ は定数(Inaba らの実測は接地点の速さで増える)、球の変形(5.5 m/s からの座屈)は入れていない。7 門、21.6 s。*

[![ITTF の台の跳ねの試験(Laws 2.1.3: 30 cm から落として約 23 cm)。球の下端を 30 cm から落とし、動画から読んだ跳ねの高さは 23.0 cm(世界の真値 23.0 cm)。物差しは 1 cm 刻み。MP4 =](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_bounce/01_drop_test.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_bounce/01_drop_test.gif)

*↑ 測定の図 ―― ITTF の台の跳ねの試験(Laws 2.1.3: 30 cm から落として約 23 cm)。球の下端を 30 cm から落とし、動画から読んだ跳ねの高さは 23.0 cm(世界の真値 23.0 cm)。物差しは 1 cm 刻み。MP4 = 240 fps の全コマ(1/8 スロー)。*

[![動画から読んだ e(22 本)と公表値。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_bounce/04_restitution_vs_speed_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_bounce/04_restitution_vs_speed.png)

*↑ 動画から読んだ e(22 本)と公表値。*

[![バックスピン(ω = −150 rad/s)の跳ね(当たる瞬間 v = (4.9, −4.3) m/s)、1000 fps を 1/40 スローで。接地点が大きく滑ったまま離れる(滑り +7.89 → +2.89 m/s)。模様から読んだ回](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_bounce/02_backspin_bounce.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_bounce/02_backspin_bounce.gif)

*↑ 動く図 ―― バックスピン(ω = −150 rad/s)の跳ね(当たる瞬間 v = (4.9, −4.3) m/s)、1000 fps を 1/40 スローで。接地点が大きく滑ったまま離れる(滑り +7.89 → +2.89 m/s)。模様から読んだ回転 -150 → +0 rad/s、横の速さの減り 1.997 m/s → 見かけの μ 0.250。*

[![トップスピン(ω = +200 rad/s)の跳ね(当たる瞬間 v = (2.9, −3.1) m/s)。接地点の滑りが小さいので跳ねの途中で止まり、転がりに移って離れる(滑り -1.17 → -0.01 m/s、跳ねた後の rω' = 3](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_bounce/03_topspin_bounce.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_bounce/03_topspin_bounce.gif)

*↑ 動く図 ―― トップスピン(ω = +200 rad/s)の跳ね(当たる瞬間 v = (2.9, −3.1) m/s)。接地点の滑りが小さいので跳ねの途中で止まり、転がりに移って離れる(滑り -1.17 → -0.01 m/s、跳ねた後の rω' = 3.320 m/s と v_x' = 3.312 m/s)。*

```
py -3.11 examples/poc_table_tennis_bounce.py
```

ソース: [examples/poc_table_tennis_bounce.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_table_tennis_bounce.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_table_tennis_bounce)

使用 op(ノートへ): [`add_ball`](https://furuse.work/ops/drive/ballworld/add_ball.html) · [`ball_detect`](https://furuse.work/ops/drive/balltrack/ball_detect.html) · [`ball_mesh`](https://furuse.work/ops/drive/ballworld/ball_mesh.html) · [`ball_params`](https://furuse.work/ops/drive/ball/ball_params.html) · [`ball_set_pose`](https://furuse.work/ops/drive/ballworld/ball_set_pose.html) · [`bounce`](https://furuse.work/ops/drive/ball/bounce.html) · [`bounce_detect`](https://furuse.work/ops/drive/balltrack/bounce_detect.html) · [`crosshair`](https://furuse.work/ops/annotate/pointer/crosshair.html) · [`flight_fit`](https://furuse.work/ops/drive/ball/flight_fit.html) · [`flight_ode`](https://furuse.work/ops/drive/ball/flight_ode.html) · [`flight_simulate`](https://furuse.work/ops/drive/ball/flight_simulate.html) · [`flight_state_at`](https://furuse.work/ops/drive/ball/flight_state_at.html) · [`impact_params`](https://furuse.work/ops/drive/ball/impact_params.html) · [`marker_direction`](https://furuse.work/ops/drive/balltrack/marker_direction.html) · [`ray_plane_range`](https://furuse.work/ops/drive/lidar/ray_plane_range.html) · [`reproject`](https://furuse.work/ops/drive/balltrack/reproject.html) · [`rotation_from_omega`](https://furuse.work/ops/drive/ballworld/rotation_from_omega.html) · [`spin_from_marker_sequence`](https://furuse.work/ops/drive/balltrack/spin_from_marker_sequence.html) · [`table_params`](https://furuse.work/ops/drive/ballworld/table_params.html) · [`table_world`](https://furuse.work/ops/drive/ballworld/table_world.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`world_camera`](https://furuse.work/ops/drive/world/world_camera.html)

## No.2026.177 —— 読みの誤差が卓球のラリーを終わらせる ―― 雑音と遅れが着地点をどれだけ動かすかを、打つ前に閉形式で出す

[![読みの誤差が卓球のラリーを終わらせる ―― 雑音と遅れが着地点をどれだけ動かすかを、打つ前に閉形式で出す](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_rally_loop/01_landing_cloud.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_rally_loop/01_landing_cloud.gif)

*↑ **読みの誤差が卓球のラリーを終わらせる ―― 雑音と遅れが着地点をどれだけ動かすかを、打つ前に閉形式で出す** ―― 卓球ロボットは球の位置を読んでから、相手コートの狙った点に落ちる打球を計算して打つ。読みが δ ずれていれば、計算は**ずれた位置から**、球は**本当の位置から**飛び出すので着地点がずれ、台の縁までの余白を越えるとアウトでラリーが終わる。この展示は「読みの誤差 → 着地点の誤差」の伝わり方(ヤコビアン J、2 × 3)を打つ前に出し、雑音・遅れ・ラリーの途切れがそれで説明できるかを確かめる。門: 空気の無い世界で、狙い・ラケットの計画・衝突・飛翔を通した数値の J が閉形式 ΔL_xy = −δ_xy − (v_xy/|v_z(T)|)δ_z と差 2.5e-06(高さの読み違い 1 cm は前後に 2.1 cm)/ 抗力 + マグヌスありで σ = 2 cm の読みの 300 本のばらつき (前後 4.6, 左右 2.0) cm が J Σ Jᵀ と 1.0・0.8 % / 縁から 6 cm を σ = 3 cm で狙うアウトの確率が予測 0.043・打った 300 本で 0.060(二項の 1.5 σ)/ 遅れ τ = 5・10・20 ms の着地点のずれが J · (−vτ − ½gτ² ẑ) と 0.2〜0.6 % / 雑音 0 の送り合いは 4 回とも上限の 10 本、σ = 6 cm(余白から出した上限 σ* = 5.2 cm の 1.2 倍)では 9・8・2・7 本ですべてアウト / 誤差 0 なら狙いから 0.52 mm。見つけたこと: 「τ 前の読み」の高さを + ½gτ² と書いていた(正しくは −)。門は同じ読みのずれを両辺に入れて比べるので、誤りのまま通っていた —— 数値積分と突き合わせて直した。雑音が大きい側(縁 12 cm を σ = 5 cm)は予測 0.017、実際 0.003 —— 前の乱数では逆向きに 2.7 σ 外れていて、300 本では一次の近似の誤りの向きは決まらない。正直に: 誤差は球の位置の読みだけ(速度・回転は真値)で毎コマ独立のガウス、ラケットは計画どおりに打てる、アウトは縁の余白だけで判定。6 門、289 s。*

[![高さを 5 cm 高く読むと、狙いの計算(灰)は低い弾道を選び、本当の位置から打った球(赤)は狙いより 10.2 cm 手前に落ちる。J の前後の増幅 2.06 × 5 cm = 10.3 cm(一次の予測)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_rally_loop/02_height_misread.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_rally_loop/02_height_misread.gif)

*↑ 測定の図 ―― 高さを 5 cm 高く読むと、狙いの計算(灰)は低い弾道を選び、本当の位置から打った球(赤)は狙いより 10.2 cm 手前に落ちる。J の前後の増幅 2.06 × 5 cm = 10.3 cm(一次の予測)。*

[![読みの雑音は 3 方向に同じ大きさでも、着地点のずれは前後に 2.2 倍伸びる(高さの読み違いが落ちる角の分だけ増える)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_rally_loop/04_spread_vs_prediction_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_rally_loop/04_spread_vs_prediction.png)

*↑ 読みの雑音は 3 方向に同じ大きさでも、着地点のずれは前後に 2.2 倍伸びる(高さの読み違いが落ちる角の分だけ増える)。*

[![上から見た送り合い(1/2 速)。上 = 読みの雑音 0 で上限の 10 本、下 = 毎コマの読みに σ = 6 cm で 9 本(アウト)。ラケットは届いている —— 途切れる理由は空振りでなく、読み違いから狙った打球のアウト。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_rally_loop/03_rally_compare.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_rally_loop/03_rally_compare.gif)

*↑ 動く図 ―― 上から見た送り合い(1/2 速)。上 = 読みの雑音 0 で上限の 10 本、下 = 毎コマの読みに σ = 6 cm で 9 本(アウト)。ラケットは届いている —— 途切れる理由は空振りでなく、読み違いから狙った打球のアウト。*

```
py -3.11 examples/poc_table_tennis_rally_loop.py
```

ソース: [examples/poc_table_tennis_rally_loop.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_table_tennis_rally_loop.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_table_tennis_rally_loop)

使用 op(ノートへ): [`aim_velocity`](https://furuse.work/ops/drive/racket/aim_velocity.html) · [`ball_params`](https://furuse.work/ops/drive/ball/ball_params.html) · [`flight_simulate`](https://furuse.work/ops/drive/ball/flight_simulate.html) · [`impact_params`](https://furuse.work/ops/drive/ball/impact_params.html) · [`racket_impact`](https://furuse.work/ops/drive/racket/racket_impact.html) · [`racket_params`](https://furuse.work/ops/drive/racket/racket_params.html) · [`racket_plan`](https://furuse.work/ops/drive/racket/racket_plan.html) · [`rally_simulate`](https://furuse.work/ops/drive/racket/rally_simulate.html) · [`table_params`](https://furuse.work/ops/drive/ballworld/table_params.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html)

## No.2026.145 —— 継ぎ目の無い動画で、時間方向 op の周期境界を検査する

[![継ぎ目の無い動画で、時間方向 op の周期境界を検査する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/05_contamination_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/05_contamination_map.png)

*↑ **継ぎ目の無い動画で、時間方向 op の周期境界を検査する** ―― 周期的な素材には、時間方向 op が満たすべき**厳密な不変量**がある —— 周期 T の動画 v に対し、周期境界を正しく扱う op なら **op(roll(v,k)) == roll(op(v),k)**(巡回シフト等変性)が厳密に成り立つ。端を複製・固定・切り捨てで埋める実装はここで割れる。`perpetual_loop` は時間依存の量をすべて θ の関数にして作るので**継ぎ目は消したのでなく最初から存在せず**(継ぎ目の比 1.0509 —— 0 ではなく 1 が正解)、この等式の真値は厳密に 0 差になる。**新しい op は 1 つも足していない。**★★この回の芯は「**『厳密に一致』が空の出力から出た**」こと: `three_frame_difference` を既定のまま走らせると最大差 **0.0e+00**・汚れ **0 フレーム**という満点を返すが、**中身のあるフレームは 0/32** —— 既定のしきい値 0.1 に対し素材の隣接フレーム差が最大 **0.0841** しかなく、何も検出していない。空の出力はどうシフトしても空なので一致して当然で、**等変性だけを見る門はここに構造的に盲目**。しきい値を 0.03 にすると同じ op が中身 30/32・汚れ 4 フレーム・最大差 1.000 となり、**満点が嘘だったと分かる**。★台帳から拾った **video -> video の単入力 op 16 本を全数走査**すると 3 群に割れた: (1) **窓つき**(端だけ汚れる)= frame_difference_causal 2 / optical_flow_magnitude_stream 2 / moving_average_window 4 / background_subtraction_window 8 / temporal_bilateral 8 / temporal_median_window 8 —— **その枚数を捨てれば残りは厳密に一致**。(2) **全フレーム**(32/32)= deflicker / exponential_background / exponential_foreground / running_gaussian_background / running_gaussian_foreground —— 再帰や全域統計なので端を捨てても直らない。(3) **空に近い** = three_frame_difference / motion_history_image / motion_energy_image —— 汚れ 0 に見えるが合格ではない。★★★**汚れるフレームは個数でなく集合として閉形式で予言できる**: 窓幅 w のop が汚すのは集合 **roll(B,k) ∪ B**(B = 不完全なフレーム)で、w = 3/5/7/9/11/13 の**6 通りとも集合そのものが一致**(4/8/12/16/19/21)。素朴な「w-1 フレーム」は6 通り全部外れ、2(w-1) も w=11 で外れる —— T=32・シフト 9 で 2 つの帯が**重なる**からで、重なり 1 フレームまで閉形式が説明する。★はじめ「中心窓なので前後 (w-1)/2」と予言して外した。外れた集合を引き算すると**汚れているのは先頭側だけで末尾は無傷**だった —— つまり窓は中心でなく**後方(因果的)**で、不完全なのは先頭の w-1 フレーム。**窓の向きは、実装を読まなくても汚れた集合の形から読める。**検査 17 件・図 9 枚(動く図 1 枚を含む)。*

[![`perpetual_loop("plasma_orbit")` の 4 コマ。時間に依る量をすべて θ の関数にしてあるので、**t = T は t = 0 と同じ式**です ---- 継ぎ目は消したのではなく最初から作られていません(継](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/01_loop_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/01_loop_frames.png)

*↑ 測定の図 ―― `perpetual_loop("plasma_orbit")` の 4 コマ。時間に依る量をすべて θ の関数にしてあるので、**t = T は t = 0 と同じ式**です ---- 継ぎ目は消したのではなく最初から作られていません(継ぎ目の比 1.0509、**0 ではなく 1 が正解**)。★だから「巡回シフトしても同じ動画」という**厳密な真値**が素材の側に立ちます。*

[![`three_frame_difference` の同じコマです。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/03_empty_output_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/03_empty_output.png)

*↑ `three_frame_difference` の同じコマです。*

[![継ぎ目の無い動画 32 コマを巡回シフトして測った全数走査です。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/04_scan_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/04_scan.png)

*↑ 継ぎ目の無い動画 32 コマを巡回シフトして測った全数走査です。*

[![窓幅 7 のときに汚れたフレームの位置。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/07_bad_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/07_bad_frames.png)

*↑ 窓幅 7 のときに汚れたフレームの位置。*

[![端だけが汚れる 6 本について、汚れたフレーム数を少ない順に並べたもの。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/08_trim_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/08_trim.png)

*↑ 端だけが汚れる 6 本について、汚れたフレーム数を少ない順に並べたもの。*

[![同じ動画を実際に回したもの(32 コマ)。**最後のコマから最初のコマへ戻るところに継ぎ目が見えません** ---- 消したのではなく、時間に依る量をすべて θ の関数にしてあるので**最初から存在しない**からです。★この性質があるので「](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/02_loop.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/02_loop.gif)

*↑ 動く図 ―― 同じ動画を実際に回したもの(32 コマ)。**最後のコマから最初のコマへ戻るところに継ぎ目が見えません** ---- 消したのではなく、時間に依る量をすべて θ の関数にしてあるので**最初から存在しない**からです。★この性質があるので「巡回シフトしても同じ動画」が**厳密な真値**になり、時間方向 op の周期境界を数で採点できます。*

```
py -3.11 examples/poc_periodic_video_boundary.py
```

ソース: [examples/poc_periodic_video_boundary.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_periodic_video_boundary.py)

この回が作った図は全部で **9 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_periodic_video_boundary)

使用 op(ノートへ): [`moving_average_window`](https://furuse.work/ops/videostream/window/moving_average_window.html) · [`perpetual_loop`](https://furuse.work/ops/generative/loop/perpetual_loop.html) · [`perpetual_loop_seam`](https://furuse.work/ops/generative/loop/perpetual_loop_seam.html) · [`three_frame_difference`](https://furuse.work/ops/videostream/motion/three_frame_difference.html)

### 幾何・校正ウィング ―― 残差が小さいことは正しさの証明にならない

カメラ校正の再投影誤差、パノラマの継ぎ目、点群位置合わせの残差。どれも「小さいほど良い」と読まれる数字ですが、この部屋の 12 点はその読み方が成り立たない場面を、真値を握った上で並べています。

再投影誤差 0.0688〜0.0690 px で焦点距離の誤差が 0.026〜7.334 %。隣の継ぎ目が 0.12 px なのに閉じる 1 本だけ 1.5 px。球や円柱では残差が同じまま姿勢が任意。最小二乗は残差を雑音まで落とすのが仕事で、落ちた先が真値かどうかは別の話です。

測り方そのものの罠も残してあります。点群を 1 組固定して姿勢だけ振っても標本は 1 つしか無く、乱数の種だけで「象限誤り 0 %」と「100 %」の両方が出ました。真値なしで測れる絶対量は、一周する撮り方の閉ループ誤差くらいしかありません。

## No.2026.006 —— 再投影誤差 0.05 px は何も保証しない

[![再投影誤差 0.05 px は何も保証しない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/03_frame_fill_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/03_frame_fill.png)

*↑ **再投影誤差 0.05 px は何も保証しない** ―― 既知の内部パラメータと姿勢で格子点を投影し、校正し直して成分ごとに誤差を出した図。板の傾き 32 / 8 / 2 度で再投影 RMS は 0.0688〜0.0690 px(比 1.00)なのに、fx の誤差は 0.026〜7.334 %(281 倍)。歪みのあるカメラでは退化検出の門が発火せず、非線形最適化は正面配置でも答えを返す。*

[![RMS は 1.00 倍しか動かないのに fx 誤差は 281 倍動く。配置の良し悪しを映すのは sigma_fx のほう。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/01_reproj_vs_truth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/01_reproj_vs_truth.png)

*↑ 測定の図 ―― RMS は 1.00 倍しか動かないのに fx 誤差は 281 倍動く。配置の良し悪しを映すのは sigma_fx のほう。*

[![2 本は重なる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/02_fx_z_coupling_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/02_fx_z_coupling.png)

*↑ 2 本は重なる。*

[![どちらも雑音 0 では真値。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/04_noise_amplification_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/04_noise_amplification.png)

*↑ どちらも雑音 0 では真値。*

[![第 1 部: 同じ雑音 0.05 px の観測を、傾き 32 度(左)と 2 度(右)の配置で解く反復。再投影 RMS はどちらも 0.069 / 0.069 px まで下がるが、fx は左が 1199.7(誤差 0.026 %)、右が 1](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/05_calibration_convergence.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/05_calibration_convergence.gif)

*↑ 動く図 ―― 第 1 部: 同じ雑音 0.05 px の観測を、傾き 32 度(左)と 2 度(右)の配置で解く反復。再投影 RMS はどちらも 0.069 / 0.069 px まで下がるが、fx は左が 1199.7(誤差 0.026 %)、右が 1112.0(誤差 7.33 %)で止まる。第 2 部: fx を真値の 0.92〜1.08 倍に固定して残りを解き直すと、左は RMS が 0.54 / 0.45 px(両端)まで跳ね上がるのに、右は 0.069 / 0.069 px とほとんど動かない —— 板までの距離 Z が fx と同じ比で動いて(Z 比 0.920 / 1.080)、画素の位置を保つため。右の配置では再投影誤差が焦点距離について何も言っていない。*

```
py -3.11 examples/poc_camera_calibration.py
```

ソース: [examples/poc_camera_calibration.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_camera_calibration.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_camera_calibration)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`data_to_pixel`](https://furuse.work/ops/annotate/plot/data_to_pixel.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`project_points`](https://furuse.work/ops/3d/render/project_points.html) · [`reprojection_error`](https://furuse.work/ops/3d/pose_estimation/reprojection_error.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html)

## No.2026.028 —— 隣どうしを鎖でつなぐと、一周して元に戻れない

[![隣どうしを鎖でつなぐと、一周して元に戻れない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/01_seams_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/01_seams.png)

*↑ **隣どうしを鎖でつなぐと、一周して元に戻れない** ―― 既知の回転列で円筒パノラマから 36 枚を切り出し、隣接ペアの鎖で一周させた図。隣の継ぎ目は 0.12 px なのに閉じる 1 本だけ 1.5 px(13 倍)開く。埋もれていた `bundle_adjust_mosaic` は鎖を上回らず(30/36 枚が単位行列のまま)、姿勢の最悪誤差は鎖 1.65 → 大域最適化 0.56 px。*

[![系 2(等分)は閉ループ誤差を下げるのに姿勢はかえって悪化する。新しい観測を足さずに効くのは系 3。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/02_pose_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/02_pose_error.png)

*↑ 測定の図 ―― 系 2(等分)は閉ループ誤差を下げるのに姿勢はかえって悪化する。新しい観測を足さずに効くのは系 3。*

[![上 2 枚はどちらも継ぎ目が綺麗に見える(後勝ちの上書きで混合しないため)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/03_mosaic_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/03_mosaic.png)

*↑ 上 2 枚はどちらも継ぎ目が綺麗に見える(後勝ちの上書きで混合しないため)。*

[![実測 log-log 傾き 0.89。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/04_drift_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/04_drift.png)

*↑ 実測 log-log 傾き 0.89。*

[![鎖(隣どうしの相対回転を掛けるだけ)で 36 枚を円筒に 1 枚ずつ貼る過程。白い枠が真の位置、橙の枠が鎖の推定位置(ずれを 20 倍に誇張)。隣どうしの継ぎ目は平均 0.119 px で合っているのに、真の姿勢からのずれ(右下の曲線)は積](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/05_chain_drift_video.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/05_chain_drift_video.gif)

*↑ 動く図 ―― 鎖(隣どうしの相対回転を掛けるだけ)で 36 枚を円筒に 1 枚ずつ貼る過程。白い枠が真の位置、橙の枠が鎖の推定位置(ずれを 20 倍に誇張)。隣どうしの継ぎ目は平均 0.119 px で合っているのに、真の姿勢からのずれ(右下の曲線)は積み上がって最悪 1.65 px(フレーム 16)。一周して 0 枚目(赤紫)と35 枚目(緑)を重ねると閉じる継ぎ目が 1.50 px 開き、縁に色の縞(二重像)が出る(左下、4 倍拡大)。最後に同じ 36 本の辺を閉ループ拘束で解き直すと(水色)、姿勢のずれは最悪 1.18 px、閉じる継ぎ目は 0.11 px。*

```
py -3.11 examples/poc_panorama_drift.py
```

ソース: [examples/poc_panorama_drift.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_panorama_drift.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_panorama_drift)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`pose_error`](https://furuse.work/ops/3d/metrics/pose_error.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html) · [`warp_by_plane`](https://furuse.work/ops/3d/plane_sweep_stereo/warp_by_plane.html)

## No.2026.108 —— 実写のステレオ写真で測る ―― 合成では出ない 3 つの躓き

[![実写のステレオ写真で測る ―― 合成では出ない 3 つの躓き](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stereo_depth/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stereo_depth/01_scene.png)

*↑ **実写のステレオ写真で測る ―― 合成では出ない 3 つの躓き** ―― この博物館で初めて**実写**を通した 1 本(Middlebury 2014 motorcycle、真値視差つき)。★配布元の注記は真値の穴を NaN と書いているが実際は +inf で、np.nanmedian は中央視差を 42.55 px でなく 44.97 px と答える(isfinite で判定している fill_disparity と apply_cmap は正しく穴として扱った)。★既定 max_disp=16 は bad2 95.06 % ―― 真の最大視差 59.91 px を下回る設定は前景を丸ごと失うので、崖は 48 と 64 の間に立つ(幾何から先に言える)。ゼロ点 94.04 % に対し SGM 15.81 %、信頼度で下位 4 割を捨てると 6.80 %。★★距離に落とすところで形が反り返る: depth_from_disparity に主点オフセット doffs が無く、実写の校正値 31.086 px を無視すると距離が 1.519〜5.243 倍にばらけ、最良の単一スケール 0.3733 を掛けてなお残差 958.3 mm RMS(奥行きレンジ 2889 mm の 33.2 %)、遠い面は +1676 mm 押し出され近い面は -926 mm 引き込まれる。この PoC で doffs を引数に足した(閉形式と最大差 0 mm)。★census は実装が弱いのではなく 64 bit パックで窓が 7 で頭打ち(3/5/7 で 75.27/48.62/35.44 % と伸びている途中)。*

[![下位 4 割を捨てると bad2 は 26.75 % -> 6.80 %。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stereo_depth/02_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stereo_depth/02_error.png)

*↑ 測定の図 ―― 下位 4 割を捨てると bad2 は 26.75 % -> 6.80 %。*

[![真の最大視差を下回る設定は前景を丸ごと失う。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stereo_depth/03_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stereo_depth/03_cliff.png)

*↑ 真の最大視差を下回る設定は前景を丸ごと失う。*

[![単一のスケールでは直らない(最良でも残差 958 mm RMS)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stereo_depth/04_depth_bend_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stereo_depth/04_depth_bend.png)

*↑ 単一のスケールでは直らない(最良でも残差 958 mm RMS)。*

[![census が最下位なのは窓が 64 bit で頭打ちだから。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stereo_depth/05_methods_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stereo_depth/05_methods.png)

*↑ census が最下位なのは窓が 64 bit で頭打ちだから。*

```
py -3.11 examples/poc_real_stereo_depth.py
```

ソース: [examples/poc_real_stereo_depth.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_stereo_depth.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_real_stereo_depth)



## No.2026.034 —— 点群位置合わせの収束域 ―― 初期姿勢がどれだけずれたら壊れるか

[![点群位置合わせの収束域 ―― 初期姿勢がどれだけずれたら壊れるか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/01_basin_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/01_basin.png)

*↑ **点群位置合わせの収束域 ―― 初期姿勢がどれだけずれたら壊れるか** ―― 点群を毎試行取り直し、初期姿勢のずれに対する ICP の成功率を等高線にした図。並進ずれ 0 で成功率が 50 % を切るのは点対点 90 度、点対面 120 度。球や円柱は残差が同じまま姿勢が任意で、大域手法では 16/16 が見かけ上収束しつつ姿勢は誤り ―― 残差では検出できない。*

[![非対称性が消えると 4 候補が形として区別できず、選択が崩れる(選ばれた解が第 1 候補から離れる)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/02_pca_quadrant_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/02_pca_quadrant.png)

*↑ 測定の図 ―― 非対称性が消えると 4 候補が形として区別できず、選択が崩れる(選ばれた解が第 1 候補から離れる)。*

[![平らな線ほど「広い」。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/03_width_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/03_width.png)

*↑ 平らな線ほど「広い」。*

[![球・円柱は残差が小さいまま姿勢が任意。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/04_symmetry_lies_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/04_symmetry_lies.png)

*↑ 球・円柱は残差が小さいまま姿勢が任意。*

[![点対点 ICP を 1 反復ずつ動かす(fs.icp(max_iter=1) を前回の姿勢から連鎖)。灰 = 目標の点群、色 = 動かしている点群(斜めから見た正射影)。同じ回転軸で初期回転ずれだけを 30 / 90 / 150 度と変え、](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/05_icp_basin_iterations.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/05_icp_basin_iterations.gif)

*↑ 動く図 ―― 点対点 ICP を 1 反復ずつ動かす(fs.icp(max_iter=1) を前回の姿勢から連鎖)。灰 = 目標の点群、色 = 動かしている点群(斜めから見た正射影)。同じ回転軸で初期回転ずれだけを 30 / 90 / 150 度と変え、並進ずれは直径の 10 %。反復予算は本文の点対点 ICP と同じ 60 回で、その後の回転誤差: 30 度 → 0.6 度(成功)、90 度 → 0.6 度(成功)、150 度 → 179.5 度(失敗)。下の曲線は回転誤差の推移(対数、灰線 = 成功のしきい値 3 度)。動画専用に取り直した 1 組の点群での 1 試行の軌跡で、成功率は第 2 章の表。*

```
py -3.11 examples/poc_registration_basin.py
```

ソース: [examples/poc_registration_basin.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_registration_basin.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_registration_basin)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`farthest_point_sampling`](https://furuse.work/ops/3d/geodesic/farthest_point_sampling.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html)

## No.2026.117 —— 「回転しても同じ」と言える量はどれか —— 実写の硬貨を 72 角度で回して数える

[![「回転しても同じ」と言える量はどれか —— 実写の硬貨を 72 角度で回して数える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rotation_invariance_audit/01_rotation_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rotation_invariance_audit/01_rotation_frames.png)

*↑ **「回転しても同じ」と言える量はどれか —— 実写の硬貨を 72 角度で回して数える** ―― 形の特徴量は当たり前のように「回転不変」と呼ばれる。だが**画素の格子は回転で不変ではない**ので、その主張はたいてい下請け(境界の数え方・補間・しきい値)の任意性のところで壊れる。scikit-image 同梱の実写 `coins`(大英博物館、ポンペイ出土のギリシャ硬貨)を 5 度ずつ 1 周させ、揺れを**3 本の腕**に分けて犯人を特定する: **A** 灰を線形補間して回してから二値化(人が実際にやること)/ **B** 0 度の二値マスクを最近傍で回す(境界の再ラスタライズだけ)/ **C** 90 度の倍数だけを `np.rot90` で回す(補間も再ラスタライズも無い)。回す道具は fullseye ではなく scipy —— 自分の回転で自分の不変性を測ると、両方同じ向きに間違っても気づけない。★**腕 C は 7 量すべてきっかり 0.00 %**。測り方そのものに向き依存は無く、揺れは全部「格子に置き直す代償」。★★**予測が外れた**: 書いた時点では「灰を補間して二値化し直すほうが荒れる」と思っていたが、**逆**だった —— 周囲長は A **2.52 %** < B **9.47 %**(3.8 倍)、円形度は A **4.82 %** < B **20.45 %**(4.2 倍)。二値マスクを最近傍で回すと境界が**階段のまま置き直される**のに対し、灰を補間してから二値化すると境界が下の連続信号から引き直される。**回すなら灰でやってから二値化する。二値マスクを回してはいけない。**★閉形式の錨(合成の正方形 L=80)では、45 度の 4 連結階段周囲長 `4L → 4L√2` の **+41.4 %** が上限。実測は **7.91 %** で、`regionprops` の Crofton 補正が 5.2 倍下回らせている —— 予測は「上限」であって「実測の当て」ではない、と書いておく。★**分母を疑う**: Hu[1](`moments_region_central_invar`)は円に近い形では真値がほぼ 0(3.9e-04)なので、相対ばらつき 29.6 % は「30 % ずれた」ではなく**0 を分母にした**だけ。表にその判定を並べてある。★図は反転色 `mode="xor"`(最上位 bit だけ反転 —— 地の模様が残り、どの階調でも消えない)で輪郭を描き、72 コマの GIF で数字の揺れが見えるようにした。*

[![実写の硬貨を 5 度ずつ 1 周。地がモノクロなので輪郭は彩度のある色で描いている(灰色には彩度が無いので、どの階調とも色相で区別がつく)。右の表の数字がどれだけ揺れるかが見える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rotation_invariance_audit/02_rotating_coin.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rotation_invariance_audit/02_rotating_coin.gif)

*↑ 測定の図 ―― 実写の硬貨を 5 度ずつ 1 周。地がモノクロなので輪郭は彩度のある色で描いている(灰色には彩度が無いので、どの階調とも色相で区別がつく)。右の表の数字がどれだけ揺れるかが見える。*

```
py -3.11 examples/poc_rotation_invariance_audit.py
```

ソース: [examples/poc_rotation_invariance_audit.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_rotation_invariance_audit.py)

この回が作った図は全部で **2 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_rotation_invariance_audit)

使用 op(ノートへ): [`annotate_outline`](https://furuse.work/ops/annotate/paper/annotate_outline.html) · [`annotate_table`](https://furuse.work/ops/annotate/paper/annotate_table.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`circularity`](https://furuse.work/ops/2d/features/circularity.html) · [`eccentricity`](https://furuse.work/ops/2d/features/eccentricity.html) · [`moments_region_2nd_invar`](https://furuse.work/ops/2d/features/moments_region_2nd_invar.html) · [`moments_region_central_invar`](https://furuse.work/ops/2d/features/moments_region_central_invar.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html)

## No.2026.190 —— 同じ場面を 2 つの世界で撮る ―― 写実シミュレータの深度を閉形式の真値で採点し、自前の世界と並べる

[![同じ場面を 2 つの世界で撮る ―― 写実シミュレータの深度を閉形式の真値で採点し、自前の世界と並べる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_carla_bridge/01_carla_two_worlds_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_carla_bridge/01_carla_two_worlds.png)

*↑ **同じ場面を 2 つの世界で撮る ―― 写実シミュレータの深度を閉形式の真値で採点し、自前の世界と並べる** ―― 著者の発案「一番リアルに近い環境に、今までの技術を駆使した完成形を載せたい」→ 環境は両方。自前の世界(真値を全部持つが写実ではない)と外部の高写実シミュレータ CARLA 0.9.16(コード MIT・アセット CC-BY、写実だが中の式は見えない)を、同じ規約で結ぶ橋 carlabridge(25 op、numpy だけ)の図。Town04 の直線で自車の前方に先行車を 8〜64 m で置いて RGB・深度・意味分割を撮り、記録の姿勢(左手系・度)を右手系に写して後ろ面までの像面距離を閉形式で出し、同じルールベースの知覚(車のラベルの画素の深度の中央値)を CARLA の像と、同じ内部パラメータ・取り付けで自前の世界を描き直した像の両方に掛けた。CARLA の深度は全コマ真値 +0.10 m(箱の原点のずれ)、自前の描き直しは ±0.3 m、車の画素数は両方で 1/d²(両対数の傾き −1.94 / −1.99)、画素数の比 0.90〜1.08。門: 回転行列が CARLA の客体の get_matrix と一致、カメラ姿勢 = look_at、深度の往復 ≤ 量子化 1 段、自前の世界 → 記録 → 描き直しが画素単位で同じ。正直に: CARLA の真値そのものは検証できない ―― 確かめたのは規約が可逆なことと閉形式との一致で、一致は正しさの証拠ではない。CARLA の像のアセットは CC-BY(CARLA team)。*

[![先行車の後ろ面までの像面距離の真値は記録の姿勢から閉形式で出す。車のラベルの画素の深度の中央値は CARLA で全コマ +0.1 m、自前の描き直しで ±0.3 m。最下行から平らな路面の式で出す距離は後輪の接地を見るのでバンパーより 0.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_carla_bridge/02_carla_depth_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_carla_bridge/02_carla_depth_error.png)

*↑ 測定の図 ―― 先行車の後ろ面までの像面距離の真値は記録の姿勢から閉形式で出す。車のラベルの画素の深度の中央値は CARLA で全コマ +0.1 m、自前の描き直しで ±0.3 m。最下行から平らな路面の式で出す距離は後輪の接地を見るのでバンパーより 0.5 m ほど先を指す。*

[![像面に平行な後ろ面の面積は距離の 2 乗に反比例する。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_carla_bridge/03_carla_pixels_inverse_square_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_carla_bridge/03_carla_pixels_inverse_square.png)

*↑ 像面に平行な後ろ面の面積は距離の 2 乗に反比例する。*

[![コマごとの数字。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_carla_bridge/04_carla_pair_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_carla_bridge/04_carla_pair_table.png)

*↑ コマごとの数字。*

```
py -3.11 examples/poc_carla_bridge.py
```

ソース: [examples/poc_carla_bridge.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_carla_bridge.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_carla_bridge)

使用 op(ノートへ): [`camera_pose_to_carla`](https://furuse.work/ops/drive/carla/camera_pose_to_carla.html) · [`carla_camera_pose`](https://furuse.work/ops/drive/carla/carla_camera_pose.html) · [`carla_depth_decode`](https://furuse.work/ops/drive/carla/carla_depth_decode.html) · [`carla_depth_encode`](https://furuse.work/ops/drive/carla/carla_depth_encode.html) · [`carla_label_map`](https://furuse.work/ops/drive/carla/carla_label_map.html) · [`carla_label_unmap`](https://furuse.work/ops/drive/carla/carla_label_unmap.html) · [`carla_labels`](https://furuse.work/ops/drive/carla/carla_labels.html) · [`carla_rotation_angles`](https://furuse.work/ops/drive/carla/carla_rotation_angles.html) · [`carla_scene_load`](https://furuse.work/ops/drive/carla/carla_scene_load.html) · [`carla_scene_save`](https://furuse.work/ops/drive/carla/carla_scene_save.html) · [`carla_scene_synthetic`](https://furuse.work/ops/drive/carla/carla_scene_synthetic.html) · [`carla_transform_matrix`](https://furuse.work/ops/drive/carla/carla_transform_matrix.html) · [`intrinsics_to_fullseye`](https://furuse.work/ops/drive/carla/intrinsics_to_fullseye.html) · [`lead_truth_depth`](https://furuse.work/ops/drive/carla/lead_truth_depth.html) · [`scene_pair_table`](https://furuse.work/ops/drive/carla/scene_pair_table.html)

## No.2026.191 —— 町を 1 つに組む ―― 教習所の要素を自動で継ぎ、入口から出口まで通して走り、途中の停止線を全部採点する

[![町を 1 つに組む ―― 教習所の要素を自動で継ぎ、入口から出口まで通して走り、途中の停止線を全部採点する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_town/01_town_overview_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_town/01_town_overview.png)

*↑ **町を 1 つに組む ―― 教習所の要素を自動で継ぎ、入口から出口まで通して走り、途中の停止線を全部採点する** ―― 著者の発案「各 PoC 系列で 1 回ずつ集大成を作る。第 1 弾は運転」の土台。これまで要素ごとに置いて個別に採点してきた交差点・踏切・坂道・縦列駐車を、新モジュール drivetown(10 op)で 1 本の道に継ぐ(要素 k+1 の entry を要素 k の exit に合わせる閉形式の配置、0.05 m の食い込み)。既定の町は 9 要素 235.1 m。中心線に沿う縦だけの運転は、先の停止線を止まっている先行車と見なして IDM で減速し、交差点は 2 秒、踏切は左右確認の後に発進し、警報中に着けば遮断かんが上がるまで待つ(踏切には遮断機つき警報機・遮断かん・列車を置き、解釈基準の状態機械で動かす)。法規パック town_rules は JP = 左側通行・踏切は常に停止と確認、US・DE = 右側通行・警報中だけ停止で、JP 以外は一次資料を確認していないので verified False と表に出す。図は町の俯瞰(多角形・中心線・停止線・止まった位置・信号機)、速度と加速度の時間図、車載カメラの通し走行(赤信号で停止 → 青で発進 → 遮断中 → 列車の通過 → 上がって発進 → 坂道の手前)、法規パック 9 通りの表、教則 159 場面の台帳の内訳。門 38 本: 警報 20 s の列車で踏切の発進 65.50 s ≥ 上昇完了 65.45 s、警報中に踏切面にかかった時間 0、JP は 2 回停止・US/DE は列車なしなら 1 回、右側通行の停止線は交差点中心の鏡像(s 40.95 ↔ 65.95)、遮断中のコマに遮断かん 1078 画素・列車のコマに 46,129 画素、 継ぎ目 8 か所の位置差 − overlap = 1.1e-14、向きの差 0、総延長 = Σ centerline_length − 0.05 × 8 で差 0、停止線の位置は規格の寸法から閉形式、停止は停止線の 0.537 / 0.536 m 手前、|a| 最大 1.877 ≤ 3、台形則の ∫v dt と s の差 3.9e-11 m、制動距離 ≥ v²/2b、既存の crossing_stop_check が ok、同じ指令を long_simulate(RK4)に渡した第 2 実装と停止位置の差 0.002 m。正直に: 横は中心線に貼り付け、信号は「2 秒待てば青」の規則で灯火の色は読まない、他車・歩行者は置かない。US/DE の保持時間などは JP の値の流用。*

[![IDM(a_max 1.5、b_max 3.0、v_max 8)で停止線の手前に止まる。交差点は 2 秒。踏切は左右確認 4 秒の後、警報 20 s に始まった状態機械(降下 → 遮断 → 列車 → 上昇)が idle に戻る 65.5 s](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_town/02_town_speed_time_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_town/02_town_speed_time.png)

*↑ 測定の図 ―― IDM(a_max 1.5、b_max 3.0、v_max 8)で停止線の手前に止まる。交差点は 2 秒。踏切は左右確認 4 秒の後、警報 20 s に始まった状態機械(降下 → 遮断 → 列車 → 上昇)が idle に戻る 65.5 s まで待って発進。下の帯 = 警報中の区間と列車が踏切に居る区間。|a| の最大 1.88 m/s²。*

[![止まった位置は停止線の 0.54, 0.54 m 手前。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_town/03_town_speed_distance_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_town/03_town_speed_distance.png)

*↑ 止まった位置は停止線の 0.54, 0.54 m 手前。*

[![GIF の 6 コマ(静止画)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_town/05_town_camera_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_town/05_town_camera_frames.png)

*↑ GIF の 6 コマ(静止画)。*

[![JP = 左側通行・踏切は常に停止 + 左右確認(道路交通法 33 条 1 項、本文で確認)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_town/06_town_rules_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_town/06_town_rules_table.png)

*↑ JP = 左側通行・踏切は常に停止 + 左右確認(道路交通法 33 条 1 項、本文で確認)。*

[![docs/drive/kyosoku_scenarios.json の件数。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_town/07_town_kyosoku_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_town/07_town_kyosoku_table.png)

*↑ docs/drive/kyosoku_scenarios.json の件数。*

[![車載カメラ(640×400、13 コマ)で町を通し走行。赤信号で止まり、青で発進、踏切で止まって左右を見て、下りた遮断かんと点滅する警報灯の前で列車が過ぎて上がるまで待ってから渡り、坂を越えて縦列駐車の前を抜ける。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_town/04_town_drive_through.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_town/04_town_drive_through.gif)

*↑ 動く図 ―― 車載カメラ(640×400、13 コマ)で町を通し走行。赤信号で止まり、青で発進、踏切で止まって左右を見て、下りた遮断かんと点滅する警報灯の前で列車が過ぎて上がるまで待ってから渡り、坂を越えて縦列駐車の前を抜ける。*

```
py -3.11 examples/poc_driving_town.py
```

ソース: [examples/poc_driving_town.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_driving_town.py)

この回が作った図は全部で **7 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_driving_town)

使用 op(ノートへ): [`course_crank`](https://furuse.work/ops/drive/course/course_crank.html) · [`course_loop_bend`](https://furuse.work/ops/drive/course/course_loop_bend.html) · [`course_road`](https://furuse.work/ops/drive/course/course_road.html) · [`course_s_curve`](https://furuse.work/ops/drive/course/course_s_curve.html) · [`crossing_stop_check`](https://furuse.work/ops/drive/crossing/crossing_stop_check.html) · [`idm_accel`](https://furuse.work/ops/drive/traffic/idm_accel.html) · [`intersection`](https://furuse.work/ops/2d/nary/intersection.html) · [`kyosoku_summary`](https://furuse.work/ops/drive/town/kyosoku_summary.html) · [`long_params`](https://furuse.work/ops/drive/long/long_params.html) · [`long_simulate`](https://furuse.work/ops/drive/long/long_simulate.html) · [`town_centerline`](https://furuse.work/ops/drive/town/town_centerline.html) · [`town_chain`](https://furuse.work/ops/drive/town/town_chain.html) · [`town_checks`](https://furuse.work/ops/drive/town/town_checks.html) · [`town_crossing_state`](https://furuse.work/ops/drive/town/town_crossing_state.html) · [`town_layout`](https://furuse.work/ops/drive/town/town_layout.html) · [`town_rules`](https://furuse.work/ops/drive/town/town_rules.html) · [`town_run`](https://furuse.work/ops/drive/town/town_run.html) · [`town_stop_lines`](https://furuse.work/ops/drive/town/town_stop_lines.html) · [`town_world`](https://furuse.work/ops/drive/town/town_world.html) · [`world_camera`](https://furuse.work/ops/drive/world/world_camera.html)

## No.2026.192 —— 実在の日本の町を自前の世界に建てて走る ―― 道は OpenStreetMap、建物は PLATEAU、道具立てと規則は日本のもの

[![実在の日本の町を自前の世界に建てて走る ―― 道は OpenStreetMap、建物は PLATEAU、道具立てと規則は日本のもの](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_japan_town/04_japan_town_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_japan_town/04_japan_town_frames.png)

*↑ **実在の日本の町を自前の世界に建てて走る ―― 道は OpenStreetMap、建物は PLATEAU、道具立てと規則は日本のもの** ―― 著者の発案「出来れば日本のマップでやりたい」。外部の高写実シミュレータの同梱マップは欧米の町(右側通行)で、日本の町を入れるにはエディタのビルドと日本の資産が要る。そこで自前の世界に日本を作る。道路網は OpenStreetMap の抜粋(等距円筒で平面に、幅は OSM のタグか道路構造令の車線幅の既定)、道路の形は辺を幅つきの線分としてラスタに描いた和集合を Fullseye の輪郭追跡(contours_xld、面積は画素数に厳密に一致)で境界ループにし、穴 = 街区を歩道と縁石にする。建物は国土交通省 Project PLATEAU の CityGML(LOD1 の足元と高さ → 押し出し柱、driveplateau)。道具立ては規格の寸法から: 一時停止の標識(330-A、一辺 80 cm)、停止線(45 cm)、路面文字「止まれ」(交通規制基準 図例(1): 1 字 240 × 80 cm、字間 1 m、縦表示)、進行方向に平行な 45 cm の縞の横断歩道、踏切警標、電柱、カーブミラー。経路は最短路(一方通行を守る)を左の車線中心に寄せ、信号・一時停止・踏切を停止線にして drivetown の通し走行(JP 法規パック)で走る。図は銀座 0.7 × 0.6 km の俯瞰、PLATEAU の建物 852 棟を立てた鳥瞰、車載カメラの通し走行(赤で停止 → 青で発進 → 一時停止)、同じ走行のコマ、一時停止の手前の道具立てと面ラベル、道路網の内訳の表、速度。門 24 本: 緯度 0.001° = 111.3195 m・第 2 実装と 1e-9 で一致、直線路の和集合の面積 = L w + π(w/2)² に 0.04 %、境界ループの面積 = 画素数 × step² に 1.5e-11 m²、3 × 3 格子の穴 4、最短路 160 m・停止線 76.25 / 156.25 m(閉形式)、右側通行の経路は鏡像、逆向きの一方通行を避けて 320 m、停止 2 回が停止線の 0.54 m 手前で town_checks ok、一時停止の板は一辺 0.8 m・上辺 2.5 m、「止まれ」の列 9.2 m、一時停止の手前のコマに標識と路面の字が映る、合成 CityGML の柱 30 m。実データでは OSM 586 辺・街区 122・建物 852 棟、面積の門 5e-8 m²、信号のある交差点への 461 m を停止 7 回で走り ok。正直に: 幅は OSM にタグが無い辺(6 割)が種別の既定、車線の割り付け・信号の現示・他車・歩行者は無し、「止まれ」の字形は折線の略字形(寸法は公式)、踏切警標の板の寸法は仮定、4 m² 未満の細片の街区は置かず、PLATEAU の地盤の起伏は無視。図の出典: 道路 © OpenStreetMap contributors(ODbL)、建物 出典: 国土交通省 Project PLATEAU。データそのものは repo に入れない。*

[![銀座 0.7 × 0.6 km の俯瞰: OSM の道路網を幅つきでラスタ化した和集合の穴 = 街区(歩道 + 縁石)、信号・横断歩道・電柱。 道路: © OpenStreetMap contributors (ODbL) / 建物: 出典](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_japan_town/01_japan_town_topdown_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_japan_town/01_japan_town_topdown.png)

*↑ 測定の図 ―― 銀座 0.7 × 0.6 km の俯瞰: OSM の道路網を幅つきでラスタ化した和集合の穴 = 街区(歩道 + 縁石)、信号・横断歩道・電柱。 道路: © OpenStreetMap contributors (ODbL) / 建物: 出典 国土交通省 Project PLATEAU*

[![PLATEAU(国交省 3D 都市モデル、LOD1 の足元と高さ)の建物 852 棟を押し出し柱で立てた銀座。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_japan_town/02_japan_town_bird_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_japan_town/02_japan_town_bird.png)

*↑ PLATEAU(国交省 3D 都市モデル、LOD1 の足元と高さ)の建物 852 棟を押し出し柱で立てた銀座。*

[![日本の道具立て(寸法は道路標識令 別表第二 / 交通規制基準 第 46 図例(1))。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_japan_town/05_japan_furniture_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_japan_town/05_japan_furniture.png)

*↑ 日本の道具立て(寸法は道路標識令 別表第二 / 交通規制基準 第 46 図例(1))。*

[![幅の由来: {'lanes': 192, 'default': 375, 'width': 19}(width タグ / lanes × 車線幅 / 種別の既定)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_japan_town/06_japan_road_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_japan_town/06_japan_road_table.png)

*↑ 幅の由来: {'lanes': 192, 'default': 375, 'width': 19}(width タグ / lanes × 車線幅 / 種別の既定)。*

[![停止線: [(3.3, 'intersection'), (15.2, 'intersection'), (133.1, 'intersection'), (396.4, 'intersection'](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_japan_town/07_japan_speed_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_japan_town/07_japan_speed.png)

*↑ 停止線: [(3.3, 'intersection'), (15.2, 'intersection'), (133.1, 'intersection'), (396.4, 'intersection'), (419.3, 'intersection'), (432.1, 'intersection'…*

[![左の車線中心を通して走る車載カメラ(JP 法規パック): 赤で停止 → 2 秒で青 → 発進、一時停止では止まって確認。道路: © OpenStreetMap contributors (ODbL) / 建物: 出典 国土交通省 Proje](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_japan_town/03_japan_town_drive.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_japan_town/03_japan_town_drive.gif)

*↑ 動く図 ―― 左の車線中心を通して走る車載カメラ(JP 法規パック): 赤で停止 → 2 秒で青 → 発進、一時停止では止まって確認。道路: © OpenStreetMap contributors (ODbL) / 建物: 出典 国土交通省 Project PLATEAU*

```
py -3.11 examples/poc_driving_japan_town.py
```

ソース: [examples/poc_driving_japan_town.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_driving_japan_town.py)

この回が作った図は全部で **7 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_driving_japan_town)

使用 op(ノートへ): [`citygml_synthetic`](https://furuse.work/ops/drive/japan/citygml_synthetic.html) · [`intersection`](https://furuse.work/ops/2d/nary/intersection.html) · [`japan_stats`](https://furuse.work/ops/drive/japan/japan_stats.html) · [`japan_world`](https://furuse.work/ops/drive/japan/japan_world.html) · [`jp_sign_stop_mesh`](https://furuse.work/ops/drive/japan/jp_sign_stop_mesh.html) · [`jp_stop_marking_mesh`](https://furuse.work/ops/drive/japan/jp_stop_marking_mesh.html) · [`latlon_to_local`](https://furuse.work/ops/drive/japan/latlon_to_local.html) · [`osm_parse`](https://furuse.work/ops/drive/japan/osm_parse.html) · [`osm_road_graph`](https://furuse.work/ops/drive/japan/osm_road_graph.html) · [`osm_road_loops`](https://furuse.work/ops/drive/japan/osm_road_loops.html) · [`osm_road_mask`](https://furuse.work/ops/drive/japan/osm_road_mask.html) · [`osm_route`](https://furuse.work/ops/drive/japan/osm_route.html) · [`osm_synthetic`](https://furuse.work/ops/drive/japan/osm_synthetic.html) · [`plateau_parse`](https://furuse.work/ops/drive/japan/plateau_parse.html) · [`town_checks`](https://furuse.work/ops/drive/town/town_checks.html) · [`town_run`](https://furuse.work/ops/drive/town/town_run.html) · [`world_camera`](https://furuse.work/ops/drive/world/world_camera.html)

## No.2026.193 —— 他人の場面で自分の運転手を走らせ、他人の採点器に出す ―― CommonRoad の公開シナリオと TUM の公式チェッカー

[![他人の場面で自分の運転手を走らせ、他人の採点器に出す ―― CommonRoad の公開シナリオと TUM の公式チェッカー](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_commonroad/01_commonroad_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_commonroad/01_commonroad_scene.png)

*↑ **他人の場面で自分の運転手を走らせ、他人の採点器に出す ―― CommonRoad の公開シナリオと TUM の公式チェッカー** ―― ユーザーの指摘「自分でトラップ作って自分で攻略する形は限界がある」を受けて、真値・門・被験者のどれか 1 つを外から持ち込む第 1 弾。これまでの運転 PoC は合成の世界に自分で真値を仕込み、自分で門を書き、自分の運転手を採点していた。ここでは場面 = CommonRoad(TUM)の公開シナリオ(BSD-3)、採点器 = TUM の drivability-checker(Windows では入らないので WSL で動かし、tools/check_solution_json.py で合否を JSON に)、自分のものは運転手だけ。新モジュール drivecommonroad(10 op): 2020a XML を自前で読み(lanelet の左右境界・動的障害物・planning problem・標識 274 の制限速度・stopLine)、successor で経路を継ぎ、縦は IDM・横は pure-pursuit、運動学は KS(後軸中心、RK4、BMW_320i の母数は commonroad-vehicle-models の parameters_vehicle2 を写す)、停止線で止まって発進し、公式の solution XML(ksTrajectory)を書く。採点器の第 2 実装(実現可能性 = 記録入力で KS を回して 2 cm・0.03 rad、衝突 = 分離軸判定、道路境界 = 多角形の点包含)も持ち、公式 JSON と並べる。図は俯瞰(lanelet・障害物の軌跡・自車・ゴール lanelet)、速度と加速度、各障害物との間隔、6 コマ(出発・交差点の手前・左折中・対向車と最接近・ゴール lanelet・停止)、自前と公式の判定の表、sweep の表。門 22 本: 合成 T 字路で読み(lanelet 4・障害物 1・274 → 13.89 m/s)、経路 98.84 m = Σ 中心線(1e-6)、KS の直進 1e-9・円 R = l_wb/tan δ(1e-6)、ゴール到達・|a| ≤ 3・v ≤ 制限、停止線の 0.90 m 手前で v = 0、feasible(max_pos_err 0)、衝突なし、前を見ない運転手は (step 52, 障害物 2) で衝突、blocked では手前停止、ksState 201 = step 数・位置 = 後軸 + b(1e-12)。実データ ZAM_Tjunction-1_1_T-1(lanelet 12・障害物 5・制限 14.0・経路 347.6 m)は IDM の既定では対向車 1 と衝突し、gap acceptance の sweep 14 回目(a_lat 8.0、lookahead 5.0)で 148 state の走行が通る(v_max 9.82 m/s、横ずれ 0.83 m)。公式チェッカー: valid true・goal_reached・feasible・衝突なし・n_states 148 一致。負の対照(穏やかな既定の運転手)は自前で (68, 1) の衝突、公式も obstacle_collision true・valid false(feasible は true)で、自前と公式の 5 項目 × 正負が全部一致。正直に: ZAM は IDM だけでは解けず sweep で解いた(譲る運転は未実装、待つとゴールの時間窓を満たせない)、a_lat 8 m/s² は快適性として高い(摩擦円 8.1 < 11.5 で採点器の範囲内)、公開 2020a の場面に信号・stopLine・一時停止標識 206 が無いので規則の採点は合成場面のみ、公式の合否は WSL の JSON が正(自前の feasibility は記録入力で同じ RK4 を回すので誤差 0)、縦だけの運転手は Speyer・Moabit では衝突が残る。出典: CommonRoad scenarios(TUM、BSD-3)。データは repo に入れない(FULLSEYE_COMMONROAD_DATA)。*

[![IDM の希望速度 v₀ = min(制限, 曲率の許容 √(a_lat/|κ|))。a は区分一定(RK4 の 1 step ごと)。|a| ≤ max(a_max 1.5, b_max 3.0)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_commonroad/02_commonroad_speed_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_commonroad/02_commonroad_speed.png)

*↑ 測定の図 ―― IDM の希望速度 v₀ = min(制限, 曲率の許容 √(a_lat/|κ|))。a は区分一定(RK4 の 1 step ごと)。|a| ≤ max(a_max 1.5, b_max 3.0)。*

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

ソース: [examples/poc_driving_commonroad.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_driving_commonroad.py)

この回が作った図は全部で **6 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_driving_commonroad)

使用 op(ノートへ): [`boundary`](https://furuse.work/ops/2d/region/boundary.html) · [`cr_checker_result`](https://furuse.work/ops/drive/commonroad/cr_checker_result.html) · [`cr_collision`](https://furuse.work/ops/drive/commonroad/cr_collision.html) · [`cr_drive`](https://furuse.work/ops/drive/commonroad/cr_drive.html) · [`cr_drive_sweep`](https://furuse.work/ops/drive/commonroad/cr_drive_sweep.html) · [`cr_feasible`](https://furuse.work/ops/drive/commonroad/cr_feasible.html) · [`cr_read`](https://furuse.work/ops/drive/commonroad/cr_read.html) · [`cr_route`](https://furuse.work/ops/drive/commonroad/cr_route.html) · [`cr_solution_xml`](https://furuse.work/ops/drive/commonroad/cr_solution_xml.html) · [`cr_synthetic`](https://furuse.work/ops/drive/commonroad/cr_synthetic.html) · [`ks_step`](https://furuse.work/ops/drive/commonroad/ks_step.html)

## No.2026.195 —— 柔らかい手首のペグ挿入 ―― Whitney の準静的幾何を門に、手首カメラの計測で穴へ寄せ、MuJoCo の接触で確かめる

[![柔らかい手首のペグ挿入 ―― Whitney の準静的幾何を門に、手首カメラの計測で穴へ寄せ、MuJoCo の接触で確かめる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pegsim_insertion/03_pegsim_wrist_overlay_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pegsim_insertion/03_pegsim_wrist_overlay.png)

*↑ **柔らかい手首のペグ挿入 ―― Whitney の準静的幾何を門に、手首カメラの計測で穴へ寄せ、MuJoCo の接触で確かめる** ―― 物理シミュ × Fullseye 系列の第 1 弾(「自作の罠は限界: 真値・門・被験者の 1 つを外から」の物理側)。外から来るものは 2 つ。定理 = Whitney 1982(ASME J. Dyn. Sys. Meas. Control 104(1)、DOI 10.1115/1.3149634。原著は有料で未読、式は著者本人の MIT OCW 2.875 Class 3 スライドの本文から: 二点接触の深さ l/d = c/θ、θ_m = √(2c)、くさび θ > c/μ、かじりの平行四辺形 λ = l/(2rμ))。接触の物理 = MuJoCo(接触点・法線力・mj_geomDistance)。学習は使わず、計測 → 補正 → 下げる → 力で減速、のルールだけ。自分で作ったのは 3 つ: 3-D の円柱で厳密にした二点接触の深さ l tan θ = 2R − r(cos θ + sec θ)(導出、l sin θ ≈ 2c_r が 4 次まで正確)、真の姿勢から接触点数を幾何だけで予測する第 2 実装、手首 RGB-D 1 枚から穴中心(反エイリアスの縁を板の平面へ持ち上げて円を当てる)とペグ先端(depth の点群に既知半径の円柱、先端は影の端を投影した縁の円で合わせる)を 3-D で読む計測。新モジュール pegsim 18 op(+ mujoco が要る facade 9)。図は手首カメラの重ね図(緑 = 真値・赤 = 推定・黄 = 縁の点、右下に 3 倍拡大)、補正ありの挿入 GIF、補正なしで面取りを滑る GIF、l₂ の理論線 3 本と MuJoCo の実測点、かじりの図(l = 2 / 8 mm)、成功率の表。門 23 本: Whitney の量の手計算(c = 0.0385、θ_m = 15.9°、面取りの許容 1.2 mm、c/μ = 7.35°)、l₂ sin θ = 0.3977〜0.3999 mm(2c_r = 0.400)、2-D の長方形近似は 6° で 0.52 mm ずれる(反例)、第 2 実装が l₂ ∓ 0.05 mm で 1 点 / 2 点に切り替わる、PnP の恒等式 1e-9、既知半径の円当てはめは全周で measure.fit_circle と 1e-9・25° の弧では中央値 0.15 px(自由な当てはめ 3.3 px)、合成 RGB-D(解析的レイキャスト、mujoco 不要)で穴中心 0.004 px・相対ずれ 0.0004 mm、画像面の楕円の中心は円の中心の投影から 0.80 px ずれる(3-D で当てる理由)。MuJoCo の門: 深度バッファは MSAA でサンプル 0 の位置 (−0.125, +0.375) px(offsamples=0 なら画素中心)、8 姿勢(|ε| ≤ 3 mm、|θ| ≤ 3°)で穴中心 max 0.18 px(自由な円)/ 0.045 px(治具の図面の半径 R + W で当てる)・相対ずれ 0.024 / 0.010 mm・先端の横 0.003 px、mj_geomDistance の二分法で測った l₂ が閉形式と 0.017〜0.070 mm(1.5〜6°)で l₂ sin θ = 0.396〜0.398 mm、接触状態が l₂ ∓ 0.3 mm で一点 / 二点、ε = (2, 1) mm・θ = 2° の挿入が成功して二点接触の始まりで l sin θ = 0.400 mm、サーボ 7 回で真のずれ 2.24 → 0.03 mm、補正なし ε₀ = 1 mm は面取りが押して入る、格子 ε₀ {0, 1, 2, 3} mm × θ₀ {0, 1.5, 3}° は補正なし 1 mm まで(2 mm 以上は入口で止まる = 面取りの許容 1.2 mm)・補正あり 12 / 12。正直に: 先端の軸方向は影の端 1 画素の被覆率だけから読むので max 0.50 px(目標 0.3 px は未達)、接触点数の予測と接触計算の一致は生で 0.69(±1 で 0.96 —— 柔らかい接触は 0/1 点・1/2 点の間でちらつく)、剛体 + ばねの手首で実機の遅れ・たわみ・較正誤差は入れていない、くさびは θ ≤ 3°・μ = 0.3 では起きない領域で起こす実験はしていない、原著未読。踏んだ罠: MuJoCo の 4×MSAA の depth は画素中心でなくサンプル 0 の位置の深度(傾けた平面で実測、depth は offsamples=0 で別コンパイル)、円柱の既定 28 スライスで半径が 0.04 mm 内側(numslices=128)、最初に書いた 2-D の長方形近似 D = d/cos θ + l tan θ は θ = 6° で 0.5 mm 違う。mujoco が無ければ MuJoCo の門は [skip] で numpy の門 12 本だけ。37 s。*

[![傾き θ で二点接触が始まる深さ l₂(最狭部から)。3-D の円柱で厳密にした (1′) と小角の式 l₂ sin θ = 2c_r は重なり、2-D の長方形近似は θ = 6° で 0.5 mm 浅い。点は MuJoCo の mj_g](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pegsim_insertion/01_pegsim_two_point_depth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pegsim_insertion/01_pegsim_two_point_depth.png)

*↑ 測定の図 ―― 傾き θ で二点接触が始まる深さ l₂(最狭部から)。3-D の円柱で厳密にした (1′) と小角の式 l₂ sin θ = 2c_r は重なり、2-D の長方形近似は θ = 6° で 0.5 mm 浅い。点は MuJoCo の mj_geomDistance の二分法で測った値(閉形式と 0.07 mm 以内)。1° では 22.9 mm と穴の深さ 20 mm を超え、二点接触は起きない。*

[![Whitney のかじりの図(OCW p.34): 二点接触中にペグが進むのは加える力の比がこの平行四辺形の内側にあるとき。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pegsim_insertion/02_pegsim_jamming_diagram_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pegsim_insertion/02_pegsim_jamming_diagram.png)

*↑ Whitney のかじりの図(OCW p.34): 二点接触中にペグが進むのは加える力の比がこの平行四辺形の内側にあるとき。*

[![初期横ずれ ε₀ × 傾き θ₀ の成功 / 失敗(各 1 走行、ずれの向きは 30°)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pegsim_insertion/06_pegsim_success_grid_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pegsim_insertion/06_pegsim_success_grid.png)

*↑ 初期横ずれ ε₀ × 傾き θ₀ の成功 / 失敗(各 1 走行、ずれの向きは 30°)。*

[![補正ありの挿入(ε₀ = (2, 1) mm、θ₀ = 2°、側面カメラ、0.15 s ごと): サーボで穴の上に寄せ、下げ、一点 → 二点接触を経て 15 mm。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pegsim_insertion/04_pegsim_insert_corrected.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pegsim_insertion/04_pegsim_insert_corrected.gif)

*↑ 動く図 ―― 補正ありの挿入(ε₀ = (2, 1) mm、θ₀ = 2°、側面カメラ、0.15 s ごと): サーボで穴の上に寄せ、下げ、一点 → 二点接触を経て 15 mm。*

[![補正なし(ε₀ = 1 mm < 面取りの許容 1.2 mm、θ₀ = 2°): 面取りが柔らかい手首を横へ押し、ペグが滑り込む。2 mm では入口で止まる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pegsim_insertion/05_pegsim_chamfer_slide_no_correction.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pegsim_insertion/05_pegsim_chamfer_slide_no_correction.gif)

*↑ 動く図 ―― 補正なし(ε₀ = 1 mm < 面取りの許容 1.2 mm、θ₀ = 2°): 面取りが柔らかい手首を横へ押し、ペグが滑り込む。2 mm では入口で止まる。*

```
py -3.11 examples/poc_pegsim_insertion.py
```

ソース: [examples/poc_pegsim_insertion.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pegsim_insertion.py)

この回が作った図は全部で **6 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_pegsim_insertion)

使用 op(ノートへ): [`camera_world_to_cv`](https://furuse.work/ops/drive/pegsim/camera_world_to_cv.html) · [`chamfer_capture`](https://furuse.work/ops/drive/pegsim/chamfer_capture.html) · [`circle_fit_known_radius`](https://furuse.work/ops/drive/pegsim/circle_fit_known_radius.html) · [`contact_state_predict`](https://furuse.work/ops/drive/pegsim/contact_state_predict.html) · [`jamming_diagram`](https://furuse.work/ops/drive/pegsim/jamming_diagram.html) · [`peg_measure_overlay`](https://furuse.work/ops/drive/pegsim/peg_measure_overlay.html) · [`peg_offset_from_rgbd`](https://furuse.work/ops/drive/pegsim/peg_offset_from_rgbd.html) · [`peg_params`](https://furuse.work/ops/drive/pegsim/peg_params.html) · [`peg_scene_mjcf`](https://furuse.work/ops/drive/pegsim/peg_scene_mjcf.html) · [`peg_synthetic_rgbd`](https://furuse.work/ops/drive/pegsim/peg_synthetic_rgbd.html) · [`project_points`](https://furuse.work/ops/3d/render/project_points.html) · [`two_point_depth`](https://furuse.work/ops/drive/pegsim/two_point_depth.html) · [`wedging_check`](https://furuse.work/ops/drive/pegsim/wedging_check.html) · [`whitney_clearance`](https://furuse.work/ops/drive/pegsim/whitney_clearance.html)

## No.2026.133 —— 公共カメラはどこを向いているか ―― 位置しか公開されない固定カメラの向きを、写真そのものから決める

[![公共カメラはどこを向いているか ―― 位置しか公開されない固定カメラの向きを、写真そのものから決める](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading/02_yaw_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading/02_yaw_sweep.gif)

*↑ **公共カメラはどこを向いているか ―― 位置しか公開されない固定カメラの向きを、写真そのものから決める** ―― 公共の固定カメラ(道路・気象・観光)は位置は公開されるが向きは無いか粗い(道路の増減方向、id のハッシュ、手校正)。向きが無いと写真を地図・DEM・3D 都市に置けない。新族 geocam(7 op、numpy + scipy)は位置既知のカメラの (yaw, pitch, roll) を写真そのものから学習なしで、2 つの独立な手掛かりで決めて互いに検算する。(1) スカイライン: カメラ位置から DEM で描いた 360° の稜線(dem_skyline、地球の丸みと屈折、DEM の外は地平線の沈みで下限)と、写真から動的計画法で抜いた空と地形の境界(skyline_extract、Lie ら 2005)を照合し、yaw を一周した残差曲線と 2 番目の谷との差(margin)を返す(camera_orientation_from_skyline)。(2) 太陽: 太陽の見かけの位置は時刻と場所の閉形式(sun_position、NOAA、春分・夏至の既知値で検証)。写真の飽和した円盤(sun_pixel_position、雲や空の帯は充填率で拒否)を 2 点以上拾えば回転は Wahba 問題の SVD 解で一意(camera_orientation_from_sun)。真値の姿勢が分かる合成カメラ(合成 DEM + 空 + 雲 + 前景の柱 + 雑音、内部行列既知)で、スカイライン経路の誤差 0.11 / 0.06 / 0.06°、太陽経路 0.02 / 0.04 / 0.05°(6 コマ、朝夕の 2 コマだけでも 0.004°)、2 経路の一致 0.09°。対照 = 公開メタデータに近い「道路方向の事前知識」は 7.5°、平地の DEM では稜線が全方位で同じなので op が ambiguous を返す(黙って 137° 間違えない)。先行 = Lalonde ら IJCV 2010(太陽と空、webcam 22 台で 3°)/ Baatz ら ECCV 2012(スカイライン、位置未知の大規模版)。正直な内訳: 合成のみ(実データはフィンランド Fintraffic + NLS 標高、ノルウェー Statens vegvesen + Kartverket DTM10 が次の段、生画像は commit しない)、内部行列 K は要る(誤りは pitch と roll に化ける)、スカイラインは山があってこそ、太陽は写っていてこそ。*

[![the DEM ridge drawn at the estimated yaw / pitch / roll lies on the extracted skyline; errors 0.06 / 0.03 / 0.01 deg](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading/01_skyline_lock_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading/01_skyline_lock.png)

*↑ 測定の図 ―― the DEM ridge drawn at the estimated yaw / pitch / roll lies on the extracted skyline; errors 0.06 / 0.03 / 0.01 deg*

[![the op returns the whole residual curve so that the ambiguity is visible: a runner-up valley at 15 d](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading/03_yaw_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading/03_yaw_profile.png)

*↑ the op returns the whole residual curve so that the ambiguity is visible: a runner-up valley at 15 deg is 1.28 deg worse; the flat DEM curve is level*

[![the sun's path over the day where it is above the ridge (yellow, projected with the pose estimated f](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading/04_sun_track_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading/04_sun_track.png)

*↑ the sun's path over the day where it is above the ridge (yellow, projected with the pose estimated from the sun) and the 5 sun discs picked by sun_pix…*

[![both routes recover the pose to well under a degree and agree with each other; the public-metadata p](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading/05_numbers_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading/05_numbers.png)

*↑ both routes recover the pose to well under a degree and agree with each other; the public-metadata prior is off by ten degrees and the flat-ground cas…*

```
py -3.11 examples/poc_public_camera_heading.py
```

ソース: [examples/poc_public_camera_heading.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_public_camera_heading.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_public_camera_heading)

使用 op(ノートへ): [`camera_orientation_from_skyline`](https://furuse.work/ops/geocam/orientation/camera_orientation_from_skyline.html) · [`camera_orientation_from_sun`](https://furuse.work/ops/geocam/sun/camera_orientation_from_sun.html) · [`dem_skyline`](https://furuse.work/ops/geocam/skyline/dem_skyline.html) · [`project`](https://furuse.work/ops/3d/bundle_adjust/project.html) · [`render_skyline_view`](https://furuse.work/ops/geocam/skyline/render_skyline_view.html) · [`skyline_extract`](https://furuse.work/ops/geocam/skyline/skyline_extract.html) · [`sun_pixel_position`](https://furuse.work/ops/geocam/sun/sun_pixel_position.html) · [`sun_position`](https://furuse.work/ops/geocam/sun/sun_position.html)

## No.2026.134 —— 公共カメラはどこを向いているか・実写編 ―― 807 局の道路カメラで太陽を探し、日没 1 本から向きを決めて道路で検算する

[![公共カメラはどこを向いているか・実写編 ―― 807 局の道路カメラで太陽を探し、日没 1 本から向きを決めて道路で検算する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading_real/02_sunset_follow.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading_real/02_sunset_follow.gif)

*↑ **公共カメラはどこを向いているか・実写編 ―― 807 局の道路カメラで太陽を探し、日没 1 本から向きを決めて道路で検算する** ―― 合成(poc_public_camera_heading)では「太陽 = 飽和した小さな円盤」で足りたが、実写の道路カメラは違った。フィンランド Fintraffic 天候カメラ(807 局、CC BY 4.0、鍵なし)の 9 月 20〜21 日 24 時間分から太陽高度 2〜12° のフレームだけ探針すると、見た目の門(sun_pixel_position)は局名の白い文字・標識・白い車・レンズの水滴を太陽と言い(最初の探針で 24/24 誤検出)、太陽は円盤でなく露出で大きさの変わるブルームで上端の局名帯で切れ、カメラは道路を見下ろして空は上 3 分の 1しか無い。そこで geocam に 2 op を足した: sun_bloom_fit(最大の飽和塊の切れていない縁に Kåsa の円を当てて中心を返す。重心は切れた側の反対へ平均 12 px 偏る)と camera_orientation_from_sun_candidates(フレームごとの候補から、固定カメラで太陽の速さで動く 1 本を RANSAC で選び、道路カメラの事前知識 |roll| ≤ 12°・pitch −40〜0°・水平画角 25〜120° で非物理な仮説を捨て、焦点距離も同時に探索する。地平線下の時刻は投票しない)。807 局 × 24 時間で追えた日没は 1 本(E18・Hamina、公式メタデータの向きは UNKNOWN): 5 枚(15:01〜16:01 UTC)から yaw 267.9°・pitch −4.6°・roll 0.9°・f 1439 px(水平画角 48°)、残差 0.34°。独立な検算 = 同じ姿勢で画像中の車線の消失点(昼のフレーム複数の medoid)を世界方位に変えると 272.7°、OpenStreetMap の E18 の路線方位は 275.3°、差 2.5°。弱い自由度は隠さない: 1 枚抜きで yaw は 1.3° しか動かないが roll は 10°、f は 2 % 動く(1 時間の低仰角の弧の限界)。同じ写真で見た目の門は 22 回「太陽」と言い、正確 3・太陽だが中心ずれ 2・別の物 17。生画像は commit せず、集計(時刻・円当て・消失点・路線方位)だけを置く。出典 Fintraffic / Digitraffic(CC BY 4.0)、OpenStreetMap(ODbL)。*

[![the sunset seen by C0362200 (E18, Hamina, Finland; metadata says direction UNKNOWN): the sun's path for the evening draw](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading_real/01_sunset_track_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading_real/01_sunset_track.png)

*↑ 測定の図 ―― the sunset seen by C0362200 (E18, Hamina, Finland; metadata says direction UNKNOWN): the sun's path for the evening drawn from the fitted pose (magenta) and the 5 blooms fitted with a circle (cyan); yaw 267.9, pitch -4.6, roll 0.9, HFOV 48*

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

ソース: [examples/poc_public_camera_heading_real.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_public_camera_heading_real.py)

この回が作った図は全部で **6 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_public_camera_heading_real)

使用 op(ノートへ): [`bloom`](https://furuse.work/ops/gfx2d/post/bloom.html) · [`camera_orientation_from_sun_candidates`](https://furuse.work/ops/geocam/sun/camera_orientation_from_sun_candidates.html) · [`ellipse`](https://furuse.work/ops/annotate/shape/ellipse.html) · [`project`](https://furuse.work/ops/3d/bundle_adjust/project.html) · [`sun_position`](https://furuse.work/ops/geocam/sun/sun_position.html)

### 色・分離ウィング ―― 「効く手法」は無い、あるのは効く条件だけ

光源を推定して色を戻す、多波長で絵画の層を剥がす、偏光で鏡面反射を分離する。この部屋の 4 点は、既知の分光反射率・既知の光源・フレネルの式から線形の輻度を合成し、分離の結果を真値と突き合わせています。

結論は、どの展示でも「壊れる軸が直交している」ことでした。白パッチ法は白が在れば最良で、いちばん明るい 1 枚を外すだけで 8 倍悪くなる。灰色世界は飽和に強く、有彩色が 2 割を超えると負ける。基準光源では全手法がゼロ点に負ける。バンドを増やしても勝てず、近赤外を入れた瞬間に勝つ。

共通の注意は「リニアな輻度に戻してから渡す」こと。sRGB ガンマのまま渡しても例外は出ず、分離が静かに劣化するだけです。例外が出ない失敗は、この展示全体で最も多い型です。

## No.2026.032 —— 多波長で層を剥がす ―― 下絵・地塗り・上塗り・褪色を、真値を握ったまま分離する

[![多波長で層を剥がす ―― 下絵・地塗り・上塗り・褪色を、真値を握ったまま分離する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/01_per_field_auc_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/01_per_field_auc.png)

*↑ **多波長で層を剥がす ―― 下絵・地塗り・上塗り・褪色を、真値を握ったまま分離する** ―― 地塗り・下絵・上塗り・褪色を重ねた分光キューブを合成し、層を分離した図。可視だけを 16 バンドに割っても RGB と同じ(再現率 0.118 対 0.119)で、勝ったのは近赤外を入れたこと。同じ検出器が群青で AUC 1.000、アズライトで 0.630、剥落部で 0.013 ―― 平均すると全部消える。褪色前の色の復元は ΔE00 16.79 → 16.46 で、ゼロ点にほぼ勝てなかった。*

[![近赤外の差分は剥落部(楕円)で消え、近赤外 1 枚は面ごとに水準が違う。塗り分けは 1–99 分位でクリップした表示のみ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/02_detector_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/02_detector_maps.png)

*↑ 測定の図 ―― 近赤外の差分は剥落部(楕円)で消え、近赤外 1 枚は面ごとに水準が違う。塗り分けは 1–99 分位でクリップした表示のみ。*

[![半分を割るのは tau 0.30–0.60 のあいだ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/03_thickness_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/03_thickness_cliff.png)

*↑ 半分を割るのは tau 0.30–0.60 のあいだ。*

[![ゼロ点の線より下に来た復元が 1 本も無い。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/04_restoration_vs_null_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/04_restoration_vs_null.png)

*↑ ゼロ点の線より下に来た復元が 1 本も無い。*

```
py -3.11 examples/poc_pigment_unmixing.py
```

ソース: [examples/poc_pigment_unmixing.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pigment_unmixing.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_pigment_unmixing)

使用 op(ノートへ): [`delta_e_map`](https://furuse.work/ops/imgmetrics/colordiff/delta_e_map.html) · [`linear_to_srgb`](https://furuse.work/ops/gfx2d/colorspace/linear_to_srgb.html) · [`spectrum_to_srgb`](https://furuse.work/ops/optics/appearance/spectrum_to_srgb.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html)

## No.2026.033 —— 偏光で鏡面反射を剥がす ―― フレネルの式で真値を作り、分離結果を突き合わせる

[![偏光で鏡面反射を剥がす ―― フレネルの式で真値を作り、分離結果を突き合わせる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/01_fresnel_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/01_fresnel.png)

*↑ **偏光で鏡面反射を剥がす ―― フレネルの式で真値を作り、分離結果を突き合わせる** ―― 拡散と鏡面を s/p 成分で合成し、フレネルの式から偏光度を出して分離結果を採点した図。偏光を使う手は入射角 20 度では 1.2 倍しか勝たない。拡散成分の誤差は閉形式 R_p·E に一致してブリュースター角 56.31 度で 0 ―― `polarization_separate` の拡散はその分だけ系統的に大きい。*

[![実測と閉形式が重なる。70 度の絶対誤差は 20 度より悪いのに、ゼロ点比では 70 度が最良 —— 最適角は評価軸で割れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/02_angle_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/02_angle_error.png)

*↑ 測定の図 ―― 実測と閉形式が重なる。70 度の絶対誤差は 20 度より悪いのに、ゼロ点比では 70 度が最良 —— 最適角は評価軸で割れる。*

[![残差はローブと同じ形。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/03_separation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/03_separation.png)

*↑ 残差はローブと同じ形。*

[![画素率 1.8 倍で誤差 2.8 倍 —— 雑音(σ に比例)や較正誤差(δ に比例)と違い、飽和は超線形に効く。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/04_saturation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/04_saturation.png)

*↑ 画素率 1.8 倍で誤差 2.8 倍 —— 雑音(σ に比例)や較正誤差(δ に比例)と違い、飽和は超線形に効く。*

```
py -3.11 examples/poc_polarization_specular.py
```

ソース: [examples/poc_polarization_specular.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_polarization_specular.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_polarization_specular)

使用 op(ノートへ): [`fresnel_reflectance`](https://furuse.work/ops/3d/optics/fresnel_reflectance.html) · [`polarization_dolp_map`](https://furuse.work/ops/specular/polarization/polarization_dolp_map.html) · [`polarization_render`](https://furuse.work/ops/specular/polarization/polarization_render.html) · [`polarization_separate`](https://furuse.work/ops/specular/polarization/polarization_separate.html) · [`polarization_stokes`](https://furuse.work/ops/specular/polarization/polarization_stokes.html) · [`rmse`](https://furuse.work/ops/imgmetrics/fidelity/rmse.html)

## No.2026.107 —— 実写の免疫染色を色で分ける ―― 見張り役が、見張るべき誤りにだけ盲目だった

[![実写の免疫染色を色で分ける ―― 見張り役が、見張るべき誤りにだけ盲目だった](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stain_unmix/01_separation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stain_unmix/01_separation.png)

*↑ **実写の免疫染色を色で分ける ―― 見張り役が、見張るべき誤りにだけ盲目だった** ―― 実写の免疫染色像(ヘマトキシリン + DAB)を色分離する。★合成なら完璧に分かれる(片方だけ濃度 1.0 を合成して解き直すと回収 1.0000 / 漏れ 0.0000)ので、合成だけ見ていると「解けている」で終わる。★実写では H の濃度が -4.446 まで振れ、負になる画素が 11.51 % ―― 負の濃度は「色素が光を出した」の意味で存在しない。★★染色ベクトルを平面内で ±20 度回すと H の中央値は 0.0471 → 0.1348(2.86 倍)、DAB は 0.3590 → 0.1836 と大きく動くのに、**残差チャネルの絶対中央値は 0.0345 のまま幅 3.3e-16** ―― 2 本が張る平面は回しても変わらないので、平面に直交する残差は定義上動かない。**「あてはまりの良さ」を見張っているつもりの量が、いちばん起こりやすい誤りだけを見ていない**。★★回した染色自身の負率も 11.51 % で完全に不変(双対ベクトルの向きが変わらず長さだけ変わるので符号は 1 画素も動かない)。動くのは相方 DAB の負率だけで、-20 度 0.00 % → +20 度 30.38 %。**見張り役は、自分ではなく相方を見る**。ただし単調なので片側の上限しか出ない。★往復の再構成は最大誤差 1e-06 だが、それは 4 節の誤りを何も否定しない ―― 何を検算しているかを言わないと検算にならない。この回に stain_unmix / stain_recompose / stain_vectors_from_patches を新設した(spec_unmix は 3 チャネルを設計上拒否するので RGB の入口が無かった)。*

[![H の中央値は 0.0656 -> 0.1348。残差の絶対中央値は 0.0345 のまま。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stain_unmix/02_blind_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stain_unmix/02_blind.png)

*↑ 測定の図 ―― H の中央値は 0.0656 -> 0.1348。残差の絶対中央値は 0.0345 のまま。*

[![残差と自分の負率は平坦。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stain_unmix/03_diagnostics_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stain_unmix/03_diagnostics.png)

*↑ 残差と自分の負率は平坦。*

[![濃度は 2.9 倍動くのに残差は 4 桁目まで同じ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stain_unmix/04_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stain_unmix/04_sweep.png)

*↑ 濃度は 2.9 倍動くのに残差は 4 桁目まで同じ。*

```
py -3.11 examples/poc_real_stain_unmix.py
```

ソース: [examples/poc_real_stain_unmix.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_stain_unmix.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_real_stain_unmix)



## No.2026.051 —— 色恒常性(ホワイトバランス)―― 「効く手法」は無い、あるのは効く条件だけ

[![色恒常性(ホワイトバランス)―― 「効く手法」は無い、あるのは効く条件だけ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/01_casts_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/01_casts.png)

*↑ **色恒常性(ホワイトバランス)―― 「効く手法」は無い、あるのは効く条件だけ** ―― 24 枚の既知分光反射率と既知光源から線形 RGB を合成し、光源推定の回復角度誤差を測った図。白パッチ法は 11 光源の中央値 1.06 度で最良だが、いちばん明るい 1 枚を外すと 8.45 度、露出 3 倍で 43 % を飽和させると 13.61 度で「何もしない」と一致。真の光源で対角補正しても 2500 K では ΔE00 平均 5.07 が残る。*

[![灰色世界はゼロ点(何もしない)の線を 0.1〜0.2 の間で上抜けする = そこから先は回すだけ損。白パッチ法には崖が無い。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/02_bias_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/02_bias_cliff.png)

*↑ 測定の図 ―― 灰色世界はゼロ点(何もしない)の線を 0.1〜0.2 の間で上抜けする = そこから先は回すだけ損。白パッチ法には崖が無い。*

[![露出 3 以上で白パッチ法の線が「何もしない」に重なる(max が (1,1,1) に張り付く)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/03_saturation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/03_saturation.png)

*↑ 露出 3 以上で白パッチ法の線が「何もしない」に重なる(max が (1,1,1) に張り付く)。*

[![最右列が推定誤差の実費。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/04_angle_to_de_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/04_angle_to_de.png)

*↑ 最右列が推定誤差の実費。*

```
py -3.11 examples/poc_white_balance.py
```

ソース: [examples/poc_white_balance.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_white_balance.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_white_balance)

使用 op(ノートへ): [`delta_e_map`](https://furuse.work/ops/imgmetrics/colordiff/delta_e_map.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`illuminant_from_dichromatic_planes`](https://furuse.work/ops/specular/dichromatic/illuminant_from_dichromatic_planes.html) · [`laplace`](https://furuse.work/ops/2d/edges/laplace.html) · [`linear_to_srgb`](https://furuse.work/ops/gfx2d/colorspace/linear_to_srgb.html) · [`mean_image`](https://furuse.work/ops/2d/smoothing/mean_image.html) · [`prewitt_amp`](https://furuse.work/ops/2d/edges/prewitt_amp.html) · [`roberts`](https://furuse.work/ops/2d/edges/roberts.html) · [`sobel_amp`](https://furuse.work/ops/2d/edges/sobel_amp.html) · [`spectrum_to_srgb`](https://furuse.work/ops/optics/appearance/spectrum_to_srgb.html)

### 法科学・文書ウィング ―― 1 枚の成功例は証拠にならない

改竄検出と書類の正対化。どちらも「見つかった 1 枚」「まっすぐになった 1 枚」で語られがちですが、この部屋の 4 点は、貼付の場所と品質、既知のホモグラフィと照明、を自分で決めた上で、画素ごとの ROC と画素単位の幾何誤差で採点しています。

改竄検出は検出側(防御)の PoC です。改竄を自分で作るのは検出器を測るのに真値が要るためだけで、作り方は最も稚拙なものに留めてあります。この展示がいちばん強く示すのは、保存ボタン 1 回でどの手掛かりも弱る、という検出側に不利な事実のほうです。

書類のほうは、名前が同じでモデルが違う関数を取り違えても例外が出ず、台形が残ったままもっともらしい絵が返る、という穴を数字にしています。影除去に良いところ取りは無く、平らにするほど薄い字が消えます。

## No.2026.015 —— 手持ちで撮った書類をまっすぐに戻す ―― 台形補正と影除去を、真値と突き合わせて測る

[![手持ちで撮った書類をまっすぐに戻す ―― 台形補正と影除去を、真値と突き合わせて測る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/01_rectify_zero_points_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/01_rectify_zero_points.png)

*↑ **手持ちで撮った書類をまっすぐに戻す ―― 台形補正と影除去を、真値と突き合わせて測る** ―― 既知のホモグラフィと照明で撮った書類を戻し、4 隅と格子の画素誤差で採点した図。推定は格子 RMS 1.070 px(何もしない 37.376 px)だが、名前が同じでモデルが違う関数(アフィン)を取り違えると 32 倍悪く、例外は出ない。影の強さ 0.45 で 4 隅 RMS 5.72 px、0.55 で 65.10 px と崖。*

[![平坦・薄字・誤検出なしを同時に満たす行は 1 つも無い。窓 9 が fs.op で届く上限、窓 61 は自前。図の階調は真値で 217 段。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/02_shadow_tradeoff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/02_shadow_tradeoff.png)

*↑ 測定の図 ―― 平坦・薄字・誤検出なしを同時に満たす行は 1 つも無い。窓 9 が fs.op で届く上限、窓 61 は自前。図の階調は真値で 217 段。*

[![下寄りの横長の帯が図の階調。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/03_shadow_removal_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/03_shadow_removal.png)

*↑ 下寄りの横長の帯が図の階調。*

[![60 度でも 2 px 台。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/04_tilt_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/04_tilt_cliff.png)

*↑ 60 度でも 2 px 台。*

```
py -3.11 examples/poc_document_scan.py
```

ソース: [examples/poc_document_scan.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_document_scan.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_document_scan)

使用 op(ノートへ): [`corner_response`](https://furuse.work/ops/2d/edges/corner_response.html) · [`dc_homomorphic`](https://furuse.work/ops/2d/decomposition/dc_homomorphic.html) · [`fill_holes`](https://furuse.work/ops/2d/region/fill_holes.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`get_region_contour`](https://furuse.work/ops/2d/region/get_region_contour.html) · [`gray_tophat`](https://furuse.work/ops/2d/morphology/gray_tophat.html) · [`illuminate`](https://furuse.work/ops/2d/gray/illuminate.html) · [`mean_image`](https://furuse.work/ops/2d/smoothing/mean_image.html) · [`opening_circle`](https://furuse.work/ops/2d/region/opening_circle.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`project_points`](https://furuse.work/ops/3d/render/project_points.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`select_largest`](https://furuse.work/ops/2d/region/select_largest.html) · [`sobel_dir`](https://furuse.work/ops/2d/edges/sobel_dir.html) · [`var_threshold`](https://furuse.work/ops/2d/segmentation/var_threshold.html)

## No.2026.020 —— 改竄検出を ROC で語る ―― 「見つかった 1 枚」ではなく、偽陽性を固定したときの検出率

[![改竄検出を ROC で語る ―― 「見つかった 1 枚」ではなく、偽陽性を固定したときの検出率](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/01_score_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/01_score_maps.png)

*↑ **改竄検出を ROC で語る ―― 「見つかった 1 枚」ではなく、偽陽性を固定したときの検出率** ―― JPEG q60 の素材を q92 の背景に貼って q95 で保存した改竄画像 10 枚を、画素ごとの ROC で採点した図。ELA の 1 つの数字は向きが教科書と逆(貼付部 / 背景 = 0.58 倍)で、改竄していない画像でも場所への偏りで AUC 0.797 が出る。ゴーストの谷の深さは AUC 0.997 だが、全体を q75 で再圧縮すると 0.975 へ落ちる。*

[![凡例の数字は AUC。乱数が対角線に乗ることで測り方に偏りが無いと言える。ゴーストA は乱数と重なる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/02_roc_tampered_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/02_roc_tampered.png)

*↑ 測定の図 ―― 凡例の数字は AUC。乱数が対角線に乗ることで測り方に偏りが無いと言える。ゴーストA は乱数と重なる。*

[![凡例の数字は AUC。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/03_roc_postprocess_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/03_roc_postprocess.png)

*↑ 凡例の数字は AUC。*

[![保存ボタン 1 回(q60 再圧縮)で ゴーストV は乱数以下。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/04_breaking_conditions_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/04_breaking_conditions.png)

*↑ 保存ボタン 1 回(q60 再圧縮)で ゴーストV は乱数以下。*

```
py -3.11 examples/poc_forensics_roc.py
```

ソース: [examples/poc_forensics_roc.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_forensics_roc.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_forensics_roc)

使用 op(ノートへ): [`copy_move_regions`](https://furuse.work/ops/imgforensics/copy_move/copy_move_regions.html) · [`error_level_map`](https://furuse.work/ops/imgforensics/compression/error_level_map.html) · [`jpeg_ghost_map`](https://furuse.work/ops/imgforensics/compression/jpeg_ghost_map.html) · [`jpeg_ghost_quality`](https://furuse.work/ops/imgforensics/compression/jpeg_ghost_quality.html) · [`noise_inconsistency_map`](https://furuse.work/ops/imgforensics/noise/noise_inconsistency_map.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html)

## No.2026.067 —— 絵画のひび割れ網 ―― 3 指標のうち撮影条件で壊れるのは分岐次数だけ

[![絵画のひび割れ網 ―― 3 指標のうち撮影条件で壊れるのは分岐次数だけ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/07_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/07_scene.png)

*↑ **絵画のひび割れ網 ―― 3 指標のうち撮影条件で壊れるのは分岐次数だけ** ―― ボロノイ網を閉形式で描き、乾燥ひび(セル小・蛇行)と経年ひび(セル大・格子的)の 2 種に色斑・光沢むら・斜光・ぼけ・雑音を足して、リッジ op → 骨格 → 分岐点の op 列で網を測った。真値でセル径 18.0 vs 45.2 px、直線度 0.960 vs 1.000、次数 4 割合 0.20 vs 0.83 と 3 指標とも 2 種を分けるが、経年型の次数 4 割合は質感で 0.87 → 0.64、斜光で 0.70 と乾燥側へ動き、セル径と直線度は動かない。予想した崖は 2 つとも来なかった: 幅 0.15 px でも再現率 0.696、質感 c = 0.64 でも偽陽性 0.382。斜光は幅を +0.37 px 片側に太らせ、中心線を光源側へ 0.75 px 寄せる。*

[![Frangi は分岐点で応答が落ち、斜光でセルが崩れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/01_ridge_ops_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/01_ridge_ops.png)

*↑ 測定の図 ―― Frangi は分岐点で応答が落ち、斜光でセルが崩れる。*

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

ソース: [examples/poc_fresco_craquelure.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_fresco_craquelure.py)

この回が作った図は全部で **11 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_fresco_craquelure)

使用 op(ノートへ): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`cv_blackhat`](https://furuse.work/ops/2d/morphology/cv_blackhat.html) · [`distance_transform`](https://furuse.work/ops/2d/region/distance_transform.html) · [`hx_split_skeleton_region`](https://furuse.work/ops/2d/halcon_ext/hx_split_skeleton_region.html) · [`hysteresis_threshold`](https://furuse.work/ops/2d/segmentation/hysteresis_threshold.html) · [`junctions_skeleton`](https://furuse.work/ops/2d/region/junctions_skeleton.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`pruning`](https://furuse.work/ops/2d/region/pruning.html) · [`r2_endpoints_skeleton`](https://furuse.work/ops/2d/region/r2_endpoints_skeleton.html) · [`sk_area_opening`](https://furuse.work/ops/2d/morphology/sk_area_opening.html) · [`sk_frangi`](https://furuse.work/ops/2d/texture/sk_frangi.html) · [`sk_otsu`](https://furuse.work/ops/2d/segmentation/sk_otsu.html) · [`skeleton`](https://furuse.work/ops/2d/region/skeleton.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html) · [`xsk_meijering`](https://furuse.work/ops/2d/texture/xsk_meijering.html) · [`xsk_sato`](https://furuse.work/ops/2d/texture/xsk_sato.html)

## No.2026.077 —— カメラ指紋(PRNU)で「どのカメラで撮ったか」を当てる ―― 指紋は枚数で育ち、保存ボタンで消える

[![カメラ指紋(PRNU)で「どのカメラで撮ったか」を当てる ―― 指紋は枚数で育ち、保存ボタンで消える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/01_estimators_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/01_estimators.png)

*↑ **カメラ指紋(PRNU)で「どのカメラで撮ったか」を当てる ―― 指紋は枚数で育ち、保存ボタンで消える** ―― 2 台の仮想カメラに固定の感度むら K を仕込み、30 枚の残差から指紋を推定して照合した。清浄条件では同一カメラの PCE 中央値 2192 に対し別カメラ 15.7(AUC 1.000)だが、JPEG 相当の量子化は品質 50 相当で PCE を 3.6 % に、0.5× 縮小は 1.5 % に落とす ―― 消したのは幾何ではなく残差抽出器だった。K=0 のカメラでも同じ背景を 30 枚写せば PCE 1706 の「指紋」ができる。被写体は指紋に化ける。*

[![別カメラのピークは毎回別の位置に立つ((0,0) は 0/30)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/02_match_pce_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/02_match_pce.png)

*↑ 測定の図 ―― 別カメラのピークは毎回別の位置に立つ((0,0) は 0/30)。*

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

ソース: [examples/poc_prnu_camera_fingerprint.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_prnu_camera_fingerprint.py)

この回が作った図は全部で **10 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint)

使用 op(ノートへ): [`aug_jpeg_blocks`](https://furuse.work/ops/2d/augmentation/aug_jpeg_blocks.html) · [`evidence_quantile`](https://furuse.work/ops/imgforensics/calibration/evidence_quantile.html) · [`fingerprint_correlate`](https://furuse.work/ops/imgforensics/sensor/fingerprint_correlate.html) · [`gauss_image`](https://furuse.work/ops/2d/smoothing/gauss_image.html) · [`median_image`](https://furuse.work/ops/2d/rank/median_image.html) · [`null_distribution`](https://furuse.work/ops/imgforensics/calibration/null_distribution.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`sensor_fingerprint`](https://furuse.work/ops/imgforensics/sensor/sensor_fingerprint.html) · [`sk_nlm`](https://furuse.work/ops/2d/smoothing/sk_nlm.html) · [`sk_tv`](https://furuse.work/ops/2d/smoothing/sk_tv.html) · [`sk_wavelet`](https://furuse.work/ops/2d/smoothing/sk_wavelet.html) · [`xsp_dct_denoise`](https://furuse.work/ops/2d/smoothing/xsp_dct_denoise.html) · [`xsp_wiener`](https://furuse.work/ops/2d/smoothing/xsp_wiener.html)

### 3-D 形状ウィング ―― 合わせてから測ると、合わせた分だけ欠陥が消える

点群とメッシュの仕事は、2-D の仕事と 1 つだけ決定的に違います。**測る前に姿勢を合わせる**という段が入ることです。合わせる段は、測りたいずれを最小にする向きに形を回します。だから欠陥が大きいほど、合わせの段が欠陥を吸い、残差は小さく、部品は良品に見えます。この部屋の展示は、その吸われた分を数える試みです。

真値はすべて式で置いてあります。立体は解析的な面のブール演算で作り、体積・表面積・肉厚・曲率が式で分かるものを選びます。変形は既知の場(局所のへこみ、反り、法線方向の一定の摩耗)、姿勢は既知の回転と並進、点群は面からの一様サンプルに既知の密度・雑音・欠測を掛けたものです。だから「合わせの誤差」と「形の誤差」を別々に持てます。

3-D 特有の落とし穴も、この部屋では別々に数えます。最近傍距離は雑音があると必ず正へ偏る(片側だけ数える量だから)、法線の符号は下請けの都合で決まる、密度を変えると距離の尺度そのものが動く、対称な形は姿勢が一意に決まらない。どれも 1 つの数字に畳んだ瞬間に見えなくなります。

## No.2026.054 —— 電池セルの内部劣化を CT で測る ―― 膨れは外から見え、原因は中にある

[![電池セルの内部劣化を CT で測る ―― 膨れは外から見え、原因は中にある](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/02_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/02_scene.png)

*↑ **電池セルの内部劣化を CT で測る ―― 膨れは外から見え、原因は中にある** ―― 角形リチウムイオンセルの積層電極とアルミ缶を真値つきで組み、劣化を既知の場(一様膨れ・局所膨れ・層間ガス空隙・電極ずれ)として与えて、順投影 → ビームハードニング → 光子雑音 → FBP 再構成という実際の撮像を通してから測った。電極が 10 % 膨れても外形に出るのは 29.4 % だけで、しかも中央のノギスは体積等価な平均の 3.6 倍(+0.235 対 +0.066 mm)を読む。外形のふくらみを揃えた 3 つのセルは缶の高さが 0.000 mm しか違わないのに、内部指標は空隙率 0.00 対 5.20 %、層の平面度 0.0156 対 0.0784 mm で分かれ、その内部指標が壊れる崖は電極厚 0.200 mm ではなく層間の隙間 0.120 mm が決めた(voxel/層厚 = 0.30、標本化定理からの予測 0.80 は外れ)。*

[![真正面(0 度)なら空隙の影までは見える。ただし奥行きに積算されているので厚みも深さも出ない。22 度傾けると層の縞そのものが重なって消える —— 投影では姿勢が結果を決めてしまう。だから断層に落とす。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/01_xray_projection_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/01_xray_projection.png)

*↑ 測定の図 ―― 真正面(0 度)なら空隙の影までは見える。ただし奥行きに積算されているので厚みも深さも出ない。22 度傾けると層の縞そのものが重なって消える —— 投影では姿勢が結果を決めてしまう。だから断層に落とす。*

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

ソース: [examples/poc_battery_ct_degradation.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_battery_ct_degradation.py)

この回が作った図は全部で **16 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_battery_ct_degradation)

使用 op(ノートへ): [`beam_hardening_apply`](https://furuse.work/ops/tomography/artifact/beam_hardening_apply.html) · [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`fbp_volume`](https://furuse.work/ops/tomography/volume/fbp_volume.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`plane_sdf`](https://furuse.work/ops/3d/sdf_csg/plane_sdf.html) · [`projection_angles`](https://furuse.work/ops/tomography/layout/projection_angles.html) · [`radon_volume`](https://furuse.work/ops/tomography/volume/radon_volume.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`ring_artifact_apply`](https://furuse.work/ops/tomography/artifact/ring_artifact_apply.html) · [`sdf_intersect`](https://furuse.work/ops/3d/sdf_csg/sdf_intersect.html) · [`sdf_subtract`](https://furuse.work/ops/3d/sdf_csg/sdf_subtract.html) · [`sdf_to_occupancy`](https://furuse.work/ops/3d/transform/sdf_to_occupancy.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`vol_bounding_box`](https://furuse.work/ops/3d/domain/vol_bounding_box.html) · [`vol_edge_probe`](https://furuse.work/ops/3d/probe/vol_edge_probe.html) · [`vol_fft_lowpass`](https://furuse.work/ops/3d/frequency/vol_fft_lowpass.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_profile_line`](https://furuse.work/ops/3d/probe/vol_profile_line.html) · [`vol_region_props`](https://furuse.work/ops/3d/regionprops/vol_region_props.html) · [`vol_resize`](https://furuse.work/ops/3d/geom_transform/vol_resize.html) · [`vol_wall_thickness`](https://furuse.work/ops/3d/probe/vol_wall_thickness.html)

## No.2026.056 —— 鳥瞰図への多センサ融合 —— 画像では合格の校正が、遠くでは長さになる

[![鳥瞰図への多センサ融合 —— 画像では合格の校正が、遠くでは長さになる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/01_scene_bev_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/01_scene_bev.png)

*↑ **鳥瞰図への多センサ融合 —— 画像では合格の校正が、遠くでは長さになる** ―― 解析的な街路(先行トラック + 互いの影に 1 台ずつ隠れる遠方車)を作り、左ミラーの LiDAR と右ミラーの深度カメラを共通の鳥瞰格子へ融合して、外部パラメータの誤差を回転・並進・時刻ずれに分けて掃引した。融合の占有 IoU 0.7033 は単センサの最良 0.5417 を上回るが、その利得はすべて視界の相補性から来ている。再投影 1 px は 22 m 先で 0.083 m に化け、崖はセル 0.2 m ではなく車幅で決まり(半分の点がセルを跨いでも IoU は 5.8 % しか落ちない)、yaw 3 度で融合は単センサに負ける。*

[![横に 1.80 m 離した 2 センサの「自由と言い切れた領域」。青い帯が LiDAR にしか見えない所、橙の帯がカメラにしか見えない所、灰色は両方。白は真値の障害物。22 m の 2 台は**互いの影に 1 台ずつ入っている**。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/02_shadow_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/02_shadow_map.png)

*↑ 測定の図 ―― 横に 1.80 m 離した 2 センサの「自由と言い切れた領域」。青い帯が LiDAR にしか見えない所、橙の帯がカメラにしか見えない所、灰色は両方。白は真値の障害物。22 m の 2 台は**互いの影に 1 台ずつ入っている**。*

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

ソース: [examples/poc_bev_sensor_fusion.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bev_sensor_fusion.py)

この回が作った図は全部で **9 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_bev_sensor_fusion)

使用 op(ノートへ): [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`closing_circle`](https://furuse.work/ops/2d/region/closing_circle.html) · [`depth_to_points`](https://furuse.work/ops/3d/transform/depth_to_points.html) · [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`fill_up`](https://furuse.work/ops/2d/region/fill_up.html) · [`fuse`](https://furuse.work/ops/3d/tsdf_fusion/fuse.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`occupancy_grid`](https://furuse.work/ops/3d/occupancy/occupancy_grid.html) · [`project_points`](https://furuse.work/ops/3d/render/project_points.html) · [`sdf_to_occupancy`](https://furuse.work/ops/3d/transform/sdf_to_occupancy.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`voxel_grid_downsample`](https://furuse.work/ops/3d/preprocess/voxel_grid_downsample.html) · [`voxel_iou`](https://furuse.work/ops/3d/metrics/voxel_iou.html)

## No.2026.058 —— CAD と実測点群の差分検査 ―― 合わせた分だけ欠陥が消え、無い所にへこみが出る

[![CAD と実測点群の差分検査 ―― 合わせた分だけ欠陥が消え、無い所にへこみが出る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/01_scene.png)

*↑ **CAD と実測点群の差分検査 ―― 合わせた分だけ欠陥が消え、無い所にへこみが出る** ―― 解析形状の機械部品に、局所へこみ・反り・摩耗を法線方向の既知量として仕込み、既知の姿勢・雑音・欠測つきの実測点群を合成した。合わせてから符号付き偏差と公差外面積を測ると、局所へこみの読みは 3.7 % しか薄まらないのに、真値が 1.2 µm しかない部品中央に深さ 121 µm の存在しないへこみが出る(閉形式の予測 -120 µm)。消えるか化けるかは剛体 6 自由度が吸える偏差場に似ているかどうかで決まり、稜線では最近傍が隣の面へ飛んで、欠陥ゼロの対照でも 66.5 mm^2 の偽の公差外領域が出た。*

[![真の姿勢を与えた最終行が推定器そのものの床。点-面 ICP との差は姿勢ではなく datum の取り方の差。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/02_methods_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/02_methods.png)

*↑ 測定の図 ―― 真の姿勢を与えた最終行が推定器そのものの床。点-面 ICP との差は姿勢ではなく datum の取り方の差。*

[![3 枚目が一様に色づくのが第 6 章の主張 —— 位置合わせが反りの平均を吸って、部品全体が下へずれて読める。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/03_deviation_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/03_deviation_maps.png)

*↑ 3 枚目が一様に色づくのが第 6 章の主張 —— 位置合わせが反りの平均を吸って、部品全体が下へずれて読める。*

[![2 次元 Poisson 点過程の最近傍距離の平均 = 0.5/√ρ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/05_density_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/05_density_bias.png)

*↑ 2 次元 Poisson 点過程の最近傍距離の平均 = 0.5/√ρ。*

[![深さを 30 倍にしても割合は動かないが、広がりを変えると比例して増える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/08_dent_area_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/08_dent_area.png)

*↑ 深さを 30 倍にしても割合は動かないが、広がりを変えると比例して増える。*

[![上面だけを見ている。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/11_warp_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/11_warp_maps.png)

*↑ 上面だけを見ている。*

[![主図(動画、640 × 360・30 fps・12 秒): 前半は実測点群(だいだい)が CAD の参照点(灰)に重なるまで —— 位置合わせなし → FPFH 粗合わせ → 点-面 ICP の推定姿勢の間を補間して動かす(偏差 RMS 1](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/14_align_orbit.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/14_align_orbit.gif)

*↑ 動く図 ―― 主図(動画、640 × 360・30 fps・12 秒): 前半は実測点群(だいだい)が CAD の参照点(灰)に重なるまで —— 位置合わせなし → FPFH 粗合わせ → 点-面 ICP の推定姿勢の間を補間して動かす(偏差 RMS 18285.3 → 105.4 → 81.7 µm)。後半は重なった点群を一周し、符号付き偏差(±0.40 mm、だいだい = 足りない / 青 = 余る)で塗る(形が読めるよう陰影を薄く足した)。公差 ±0.10 mm を外れた面積は推定 2300.6 mm²、真値 2514.5 mm²。左手前の 3 本の線は CAD の x・y・z 軸。*

```
py -3.11 examples/poc_cad_scan_deviation.py
```

ソース: [examples/poc_cad_scan_deviation.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_cad_scan_deviation.py)

この回が作った図は全部で **14 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_cad_scan_deviation)

使用 op(ノートへ): [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`chamfer_distance`](https://furuse.work/ops/3d/metrics/chamfer_distance.html) · [`color_bar`](https://furuse.work/ops/annotate/furniture/color_bar.html) · [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`estimate_oriented_normals`](https://furuse.work/ops/3d/normals_orient/estimate_oriented_normals.html) · [`face_areas`](https://furuse.work/ops/3d/mesh_process/face_areas.html) · [`gicp`](https://furuse.work/ops/3d/gicp/gicp.html) · [`hausdorff_distance`](https://furuse.work/ops/3d/metrics/hausdorff_distance.html) · [`icp_point2plane`](https://furuse.work/ops/3d/refine/icp_point2plane.html) · [`icp_point2point_3d`](https://furuse.work/ops/3d/refine/icp_point2point_3d.html) · [`query_distance`](https://furuse.work/ops/3d/occupancy/query_distance.html) · [`register_fpfh`](https://furuse.work/ops/3d/feature_register/register_fpfh.html) · [`sphere_sdf`](https://furuse.work/ops/3d/sdf_csg/sphere_sdf.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`voxel_grid_downsample`](https://furuse.work/ops/3d/preprocess/voxel_grid_downsample.html)

## No.2026.063 —— 作物の葉面積を上から測る —— 隠れるより先に、投影が畳んでしまう

[![作物の葉面積を上から測る —— 隠れるより先に、投影が畳んでしまう](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crop_phenotyping/08_scene_nadir_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crop_phenotyping/08_scene_nadir.png)

*↑ **作物の葉面積を上から測る —— 隠れるより先に、投影が畳んでしまう** ―― 葉を解析曲面(片面面積 pi/4·L·W、葉角も投影係数も閉形式)で組んだトウモロコシ群落に、天頂からの厳密な z-buffer をかけて植被率・遮蔽・葉角を測った。植被率を Beer-Lambert で戻す素朴な葉面積指数は、消光係数を真値に直しても真の 4.85 に対し -52.2 %、しかも 2 段階クランピングから予測した天井 2.26 のすぐ上(実測 2.70)で止まる。遮蔽は天頂の植被率を 1 ビットも変えず、壊しているのは 1 セルを平均 3.49 枚の葉が覆うのに 1 枚と数える「投影が畳む分」のほうで、点密度を 4 倍にしても判別できる上限は +1.92 しか伸びなかった。*

[![閉形式 2 pi r h + 4 pi r^2 / pi r^2 h + 4/3 pi r^3 と比べる。2 値化を挟むと面積だけが一方向に膨らむ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crop_phenotyping/01_capsule_calibration_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crop_phenotyping/01_capsule_calibration.png)

*↑ 測定の図 ―― 閉形式 2 pi r h + 4 pi r^2 / pi r^2 h + 4/3 pi r^3 と比べる。2 値化を挟むと面積だけが一方向に膨らむ。*

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

ソース: [examples/poc_crop_phenotyping.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_crop_phenotyping.py)

この回が作った図は全部で **17 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_crop_phenotyping)

使用 op(ノートへ): [`boundary_vertices`](https://furuse.work/ops/3d/mesh_process/boundary_vertices.html) · [`capsule_sdf`](https://furuse.work/ops/3d/sdf_csg/capsule_sdf.html) · [`dem_slope`](https://furuse.work/ops/dem/surface/dem_slope.html) · [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`face_areas`](https://furuse.work/ops/3d/mesh_process/face_areas.html) · [`face_normals`](https://furuse.work/ops/3d/mesh_process/face_normals.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`mesh_area`](https://furuse.work/ops/3d/mesh_process/mesh_area.html) · [`mesh_sample_points`](https://furuse.work/ops/3d/resolution/mesh_sample_points.html) · [`mesh_volume`](https://furuse.work/ops/3d/mesh_process/mesh_volume.html) · [`occupancy_grid`](https://furuse.work/ops/3d/occupancy/occupancy_grid.html) · [`plane_segmentation`](https://furuse.work/ops/3d/segment/plane_segmentation.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`sdf_to_occupancy`](https://furuse.work/ops/3d/transform/sdf_to_occupancy.html)

## No.2026.064 —— 接合層のボイドを 1 個の数字に畳む ―― 畳んだ分だけ、寿命に効く形が消える

[![接合層のボイドを 1 個の数字に畳む ―― 畳んだ分だけ、寿命に効く形が消える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/01_scene_sections_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/01_scene_sections.png)

*↑ **接合層のボイドを 1 個の数字に畳む ―― 畳んだ分だけ、寿命に効く形が消える** ―― 合成のダイアタッチ接合層に、体積率を 3.000 % に厳密にそろえたまま位置・形・近接だけを変えた 5 条件のボイドを仕込み、PSF・雑音・カッピングつきの X 線 CT として撮り直した。2 値化してボイド率だけを出すゼロ点は 5 条件を 2.46〜2.63 %(開きは 0.17 ポイント)としか分けないのに、界面に接する扁平ボイドが界面を塞ぐ面積は同体積の球の 2.09 倍(14.49 対 6.92 %)、連なりの跨ぎ率は散在の 13.1 倍(80.0 対 6.1 %)になる。崖の予想は外れ、ボクセルを 60 µm まで粗くしてもボイド率は 3.21 % と崩れず(格子の位相の運で ±1.36 ポイント振れるだけ)、代わりに扁平度が測れなくなり界面欠損率が 14.16 → 9.78 % と『安全』側へ落ちた ―― 壊れる向きが合格の側なのがいちばん悪い。*

[![疑似カラーはラベル番号を並べ替えたもの。側面図で界面(上端)に貼りついているのが見える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/02_void_label_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/02_void_label_map.png)

*↑ 測定の図 ―― 疑似カラーはラベル番号を並べ替えたもの。側面図で界面(上端)に貼りついているのが見える。*

[![ボイド率の列だけを見ると 5 条件は区別できない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/03_controls_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/03_controls_table.png)

*↑ ボイド率の列だけを見ると 5 条件は区別できない。*

[![界面欠損率は 球/中央/散 0.0 % / 球/界面/散 6.9 % / 扁平/界面/散 14.5 % / 球/中央/連 0.0 % / 扁平/界面/連 14.7 % —— 体積率が同じでも 0 から](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/05_controls_section_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/05_controls_section.png)

*↑ 界面欠損率は 球/中央/散 0.0 % / 球/界面/散 6.9 % / 扁平/界面/散 14.5 % / 球/中央/連 0.0 % / 扁平/界面/連 14.7 % —— 体積率が同じでも 0 から 14.7 % まで動く。*

[![60 µm では扁平度が測れない(nan なので描けない)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/08_voxel_cliff_shape_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/08_voxel_cliff_shape.png)

*↑ 60 µm では扁平度が測れない(nan なので描けない)。*

[![塊の数が 24 から落ちた瞬間、最近接間隔は『隣のボイドまで』から『隣の鎖まで』に黙って入れ替わる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/10_threshold_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/10_threshold_sweep.png)

*↑ 塊の数が 24 から落ちた瞬間、最近接間隔は『隣のボイドまで』から『隣の鎖まで』に黙って入れ替わる。*

[![主図(動画、640 × 360・30 fps・11 秒): 同じボイド率の 2 条件(球・散在・層中央 2.46 % / 扁平・連なり・界面接触 2.63 %)で、xz 断面(橙の枠)を y 方向に掃引しながら 3-D のボイド(2 値化の](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/13_section_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/13_section_sweep.gif)

*↑ 動く図 ―― 主図(動画、640 × 360・30 fps・11 秒): 同じボイド率の 2 条件(球・散在・層中央 2.46 % / 扁平・連なり・界面接触 2.63 %)で、xz 断面(橙の枠)を y 方向に掃引しながら 3-D のボイド(2 値化の結果を marching cubes で面に)を回す。色はダイ側界面までの距離 —— 前者は層の中ほど(界面離隔の中央値 60.0 µm)、後者は界面に貼りつく(10.0 µm)。下は同じ断面の観測 CT(上 = ダイ)。合否の 1 個の数字(ボイド率)は 2 つを分けない。z は画面上だけ 2 倍。*

```
py -3.11 examples/poc_ct_void_morphology.py
```

ソース: [examples/poc_ct_void_morphology.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_void_morphology.py)

この回が作った図は全部で **13 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_ct_void_morphology)

使用 op(ノートへ): [`boundary_vertices`](https://furuse.work/ops/3d/mesh_process/boundary_vertices.html) · [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`color_bar`](https://furuse.work/ops/annotate/furniture/color_bar.html) · [`cylinder_sdf`](https://furuse.work/ops/3d/sdf_csg/cylinder_sdf.html) · [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`face_areas`](https://furuse.work/ops/3d/mesh_process/face_areas.html) · [`mesh_volume`](https://furuse.work/ops/3d/mesh_process/mesh_volume.html) · [`morph_dilate3d`](https://furuse.work/ops/3d/morphology/morph_dilate3d.html) · [`plane_sdf`](https://furuse.work/ops/3d/sdf_csg/plane_sdf.html) · [`query_distance`](https://furuse.work/ops/3d/occupancy/query_distance.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`sphere_sdf`](https://furuse.work/ops/3d/sdf_csg/sphere_sdf.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`vol_boundary_points`](https://furuse.work/ops/3d/boundary/vol_boundary_points.html) · [`vol_gaussian_psf`](https://furuse.work/ops/3d/restoration/vol_gaussian_psf.html) · [`voxel_to_mips`](https://furuse.work/ops/3d/transform/voxel_to_mips.html)

## No.2026.065 —— 造形しやすさを形から測る —— しきい値に貼りついた面は、丸めた分だけ判定が飛ぶ

[![造形しやすさを形から測る —— しきい値に貼りついた面は、丸めた分だけ判定が飛ぶ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/01_scene.png)

*↑ **造形しやすさを形から測る —— しきい値に貼りついた面は、丸めた分だけ判定が飛ぶ** ―― 設計値の分かる合成部品(薄壁・スロット・45 度前後の補強・穴)をボクセル化し、肉厚・要サポート面積・工具の入る隙間を測りました。しきい値 45 度の両側で必要面積は 185.22 → 576.10 mm^2 と 0.2 度で 3.11 倍に跳ね、その段差は等値面を距離場から取ると 100 %、平滑化でも 12 % 消えます。肉厚は 2 voxel 刻みに潰れ(内接球にしても同じ)、隙間の誤判定は両方向に出て、粗さ 0.500 mm では隙間が 2.000 mm に太り入らない工具を通します。*

[![上: 左端の 2 本が薄壁(1.500 mm)とそのあいだのスロット(1.500 mm)、右の三角が補強。下: リブと薄壁の footprint。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/02_sections_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/02_sections.png)

*↑ 測定の図 ―― 上: 左端の 2 本が薄壁(1.500 mm)とそのあいだのスロット(1.500 mm)、右の三角が補強。下: リブと薄壁の footprint。*

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

ソース: [examples/poc_dfm_thickness_overhang.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dfm_thickness_overhang.py)

この回が作った図は全部で **9 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_dfm_thickness_overhang)

使用 op(ノートへ): [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`erfc`](https://furuse.work/ops/math/numerics/erfc.html) · [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`face_areas`](https://furuse.work/ops/3d/mesh_process/face_areas.html) · [`face_normals`](https://furuse.work/ops/3d/mesh_process/face_normals.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`morph_erode3d`](https://furuse.work/ops/3d/morphology/morph_erode3d.html) · [`render_shaded`](https://furuse.work/ops/3d/render/render_shaded.html) · [`sdf_intersect`](https://furuse.work/ops/3d/sdf_csg/sdf_intersect.html) · [`sdf_subtract`](https://furuse.work/ops/3d/sdf_csg/sdf_subtract.html) · [`sdf_to_occupancy`](https://furuse.work/ops/3d/transform/sdf_to_occupancy.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`vol_wall_thickness`](https://furuse.work/ops/3d/probe/vol_wall_thickness.html) · [`voxel_to_mesh`](https://furuse.work/ops/3d/transform/voxel_to_mesh.html)

## No.2026.070 —— 斜面の土量 ―― 合わせてから引くと、崩れが浅くなる

[![斜面の土量 ―― 合わせてから引くと、崩れが浅くなる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/09_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/09_scene.png)

*↑ **斜面の土量 ―― 合わせてから引くと、崩れが浅くなる** ―― 傾斜のある合成地形に既知体積の掘削と堆積を仕込み、2 時期の航空点群から鉛直差分と法線方向の差で土量を測った。予想した「斜面では cos だけ体積が縮む」は外れで、水平投影面積で積む限り cos は約分し、掘削体積の誤差は傾斜 0〜40 度でどれも -0.011 % のまま動かない。壊れたのは合わせ方のほうで、変化域が視野の 33 % もあると位置合わせが変化そのものを吸い、正味土量は真値 -30.4 m3 に対し -3.8 m3 まで潰れた ―― 変化なしの対照ですら偽の掘削が 83.8 m3 出る。*

[![傾斜を 0 から 40 度まで振っても体積の誤差に傾向が無い。cos は積分で約分する。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/01_geometry_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/01_geometry.png)

*↑ 測定の図 ―― 傾斜を 0 から 40 度まで振っても体積の誤差に傾向が無い。cos は積分で約分する。*

[![真の掘削は 164.2 m3。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/02_controls_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/02_controls.png)

*↑ 真の掘削は 164.2 m3。*

[![予測式は先に立ててから測った。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/04_slope_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/04_slope_table.png)

*↑ 予測式は先に立ててから測った。*

[![誤差はそのしきい値以上の真値に対する値。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/07_occlusion_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/07_occlusion.png)

*↑ 誤差はそのしきい値以上の真値に対する値。*

[![M3C2 の L は法線方向なので cos 25 度 = 0.906 倍だけ浅く出る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/11_scar_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/11_scar_profile.png)

*↑ M3C2 の L は法線方向なので cos 25 度 = 0.906 倍だけ浅く出る。*

[![主図(動画、640 × 360・30 fps・12 秒): 前半は傾斜 25 度の斜面を北の上空から横切り、時期 1 の点群(8 pt/m²、樹冠に当たった点 = 緑)を見せる(動画専用の乱数で作った別の標本)。後半は時期 2 の地形の周り](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/12_flight.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/12_flight.gif)

*↑ 動く図 ―― 主図(動画、640 × 360・30 fps・12 秒): 前半は傾斜 25 度の斜面を北の上空から横切り、時期 1 の点群(8 pt/m²、樹冠に当たった点 = 緑)を見せる(動画専用の乱数で作った別の標本)。後半は時期 2 の地形の周りを回り、色を DoD の鉛直差から M3C2 の法線距離へ塗り替える(同じ尺度 ±1.2 m、青 = 下がった)。崩壊中心の深さは DoD 1.212 m / M3C2 1.096 m で比 1.105(sec 25 度 = 1.103)。有意な core の M3C2 土量は掘削 142.3 / 堆積 107.7 m³(真値 164.2 / 133.7)。黒っぽい所は測れなかった core。*

```
py -3.11 examples/poc_lidar_terrain_change.py
```

ソース: [examples/poc_lidar_terrain_change.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_lidar_terrain_change.py)

この回が作った図は全部で **14 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_lidar_terrain_change)

使用 op(ノートへ): [`chamfer_distance`](https://furuse.work/ops/3d/metrics/chamfer_distance.html) · [`color_bar`](https://furuse.work/ops/annotate/furniture/color_bar.html) · [`dem_hillshade`](https://furuse.work/ops/dem/shading/dem_hillshade.html) · [`dem_slope`](https://furuse.work/ops/dem/surface/dem_slope.html) · [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`estimate_oriented_normals`](https://furuse.work/ops/3d/normals_orient/estimate_oriented_normals.html) · [`fit_plane_3d`](https://furuse.work/ops/3d/geometry/fit_plane_3d.html) · [`icp_point2point_3d`](https://furuse.work/ops/3d/refine/icp_point2point_3d.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`ransac_plane`](https://furuse.work/ops/3d/robust_fit/ransac_plane.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`voxel_grid_downsample`](https://furuse.work/ops/3d/preprocess/voxel_grid_downsample.html)

## No.2026.099 —— シルエットから体重を測る ―― 台数で買える誤差と、いくら買っても消えない誤差

[![シルエットから体重を測る ―― 台数で買える誤差と、いくら買っても消えない誤差](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/10_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/10_scene.png)

*↑ **シルエットから体重を測る ―― 台数で買える誤差と、いくら買っても消えない誤差** ―― 多視点シルエットの交差(visual hull)から家畜の体積を出し、体重へ換算する。視体積交差は**必ず上界**なので、問うべきは「良いか」ではなく「**必ず上に出る**」ほうだ。★★**閉形式の崖が、現場の目安を訂正した**。「K 台なら K 角形」は正しくない —— 平行投影ではカメラ 1 台が視線に**直交する接線 2 本**を与え(法線は方位 ± 90 度)、しかも**向かい合う 2 台は同じ 2 本**しか与えない。したがって接線の本数は偶数 K なら K 本、**奇数 K なら 2K 本**。結果として **3 台と 6 台は幾何としてまったく同じ**(閉形式 1.16772 / 1.16772、接線の集合が一致。実測差 0.013 は離散化だけ)、**偶数台は半分が無駄**で、**13 台(実測 1.03056)が 16 台(1.04768)に勝つ**。「体重 2 % 以内」を要求すると奇数 **13 台** / 偶数 **24 台**。円の素朴な読み (K/π)tan(π/K) は 13 台と出るので、**偶数台で組む現場は 11 台足りない見積り**を持つことになる。支持関数から出した楕円(a/b = 2.76)の厳密値に対し、近似平行投影(60 m・4.0 mm/px)の実測は**全 K で閉形式のすぐ上**に乗った(K=4: 1.27324 / 1.27528、K=8: 1.11657 / 1.12231、K=24: 1.01790 / 1.02821)—— **下界として的中**し、差は被覆マージンで説明できる。★対照群でこの縮退が**平行投影の性質**だと確かめた: 距離 8 m まで近づけると 3 台 1.20699 / 6 台 1.11211 と差が 7.1 倍に開く。★★この展示の中心は、**カメラを増やして消える誤差と、いくら増やしても消えない誤差を分けて数える**こと。脚の間の幽霊は K=4 → 48 で **7.13 % → 1.37 %**(5.2 倍)と素直に減るのに、**背中のくぼみはカメラを 12 倍にしても 3.8 ポイントしか減らない**(56.4 % → 52.6 %)。分かれ目は「その凹みが**輪郭に出るか**」で、出ない凹みはシルエットにそもそも情報が無い。K=48 で残る +3.4 % の内訳はくぼみ +1.00 % / 幽霊 +1.76 %、真の voxel の**取りこぼしは全 K で 0**(上界であることの確認)。★**前景抽出の 1 画素**も台数では買えない: K=12・4.0 mm/px で **+3.21 %/px**(体重 +23.7 kg)。Steiner の ΔV/V = (S/V)δ の予測 +3.09 %/px と比 1.04 で当たるが、押し上げ要因と押し下げ要因が**偶然釣り合った**結果なので、そのまま一般化しないよう本文に書いた。±3 画素で -8.71 〜 +9.43 %。★**物差しで勝者が入れ替わる**: 体積由来の体重とアロメトリ体重は「K=24 + 2 画素収縮」が最良だが、**重心の高さでは収縮なしの K=24 が勝つ**(細い脚が先に消えて重心が上がる)。3 つの物差しに 2 通りの勝者。★★**予想を外した**: 「巻尺は体に巻くから凸包を測っている。だから胸囲では 3-D 凸包が強いはず」と踏んだが、実測 **+55.2 %** で最悪の部類だった。体全体の凸包は**腹の下を埋める**ので、縦断面が地面まで伸びる —— **『断面の凸包』と『凸包の断面』は別物**。★カメラ配置の対照(上半球ランダム 8 台 対 等間隔 8 台、120 試行)は平均では互角(等間隔以下 57.5 %)だが、**最悪値は +30.20 % で等間隔の 2.4 倍** —— **危ないのは平均ではなく裾**。★★道具の穴を見つけて**その場で埋めた**: 空間彫刻が要求する OpenCV 規約(+Z 前方)の姿勢ヘルパは`fs.` / `fs.op.` / `fs.ledger.` / `op_find('look')`(0 件)の**どこからも引けず**、公開層で `look_at` の名を持つのは render3d の gluLookAt 版(-Z 前方)だけだった。**同じ名前で規約が逆**なので、掴み間違えると全点がカメラ後方に落ち、**例外を出さずに空の hull** が返る(カメラ 0 台は ValueError で fail-closed なのに、規約違いは無言)。`carve_look_at` を台帳に載せて引けるようにし、点が 1 つ残らず後方なら警告を出すようにし、`render3d.look_at` の docstring にも「彫刻には渡すな」と書いた。*

[![真値 0.7238 m^3 / 738 kg。外接直方体と OBB は上界の中でもいちばん粗い。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/01_null_baseline_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/01_null_baseline.png)

*↑ 測定の図 ―― 真値 0.7238 m^3 / 738 kg。外接直方体と OBB は上界の中でもいちばん粗い。*

[![法線は方位 ± 90 度。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/02_closed_form_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/02_closed_form.png)

*↑ 法線は方位 ± 90 度。*

[![くぼみ(輪郭に出ない凹み)は台数に鈍感、脚の間(輪郭に出る凹み)は台数に敏感。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/04_persistent_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/04_persistent.png)

*↑ くぼみ(輪郭に出ない凹み)は台数に鈍感、脚の間(輪郭に出る凹み)は台数に敏感。*

[![K=12・4.0 mm/px。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/07_controls_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/07_controls.png)

*↑ K=12・4.0 mm/px。*

[![脚の間の空隙はどの 1 枚にも写っている(だから彫れる)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/11_silhouettes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/11_silhouettes.png)

*↑ 脚の間の空隙はどの 1 枚にも写っている(だから彫れる)。*

[![動画(270 コマ、560 × 420 px): 牛の周りを 1 周しながら、彫刻に使うカメラの台数を 4 → 48 台(軸周り等間隔、8 m 先)へ増やす。表示は §4 で数えた視体積交差の占有の表面で、真の体に接する面は灰、真に空の所に](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/14_hull_orbit.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/14_hull_orbit.gif)

*↑ 動く図 ―― 動画(270 コマ、560 × 420 px): 牛の周りを 1 周しながら、彫刻に使うカメラの台数を 4 → 48 台(軸周り等間隔、8 m 先)へ増やす。表示は §4 で数えた視体積交差の占有の表面で、真の体に接する面は灰、真に空の所に立つ面(余分)はだいだい。最初の段は真の占有。横腹の帯と脚の間の幽霊(7.13 % → 1.37 %)は台数とともに消えるが、背中のくぼみに被さる蓋は K = 48 でも 52.6 % 埋まったまま(K = 4 で 56.4 %)—— 輪郭に出ない凹みはシルエットに情報が無い。体積は真値の 1.2255 → 1.0339 倍。カメラの仰角は 20 → 46 度へ上げていき、台数の多い段ほど背中の蓋が見える。左下の 3 本は x(体長)・y(体幅)・z(上)、灰の細線は地面の x 軸・y 軸。*

```
py -3.11 examples/poc_livestock_body_volume.py
```

ソース: [examples/poc_livestock_body_volume.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_livestock_body_volume.py)

この回が作った図は全部で **14 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_livestock_body_volume)

使用 op(ノートへ): [`carve`](https://furuse.work/ops/3d/space_carving/carve.html) · [`carve_look_at`](https://furuse.work/ops/3d/space_carving/carve_look_at.html) · [`convex_hull`](https://furuse.work/ops/3d/bounds/convex_hull.html) · [`erosion_circle`](https://furuse.work/ops/2d/region/erosion_circle.html) · [`mesh_volume`](https://furuse.work/ops/3d/mesh_process/mesh_volume.html) · [`synthesize_silhouette`](https://furuse.work/ops/3d/space_carving/synthesize_silhouette.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`vol_rle_bbox`](https://furuse.work/ops/3d/rle_region/vol_rle_bbox.html) · [`vol_rle_centroid`](https://furuse.work/ops/3d/rle_region/vol_rle_centroid.html) · [`vol_rle_encode`](https://furuse.work/ops/3d/rle_region/vol_rle_encode.html) · [`vol_rle_volume`](https://furuse.work/ops/3d/rle_region/vol_rle_volume.html) · [`voxel_to_mesh`](https://furuse.work/ops/3d/transform/voxel_to_mesh.html)

## No.2026.072 —— 壊れたメッシュを直してから測る ―― 消えるのは欠陥の数で、戻るのは量ではない

[![壊れたメッシュを直してから測る ―― 消えるのは欠陥の数で、戻るのは量ではない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/01_scene.png)

*↑ **壊れたメッシュを直してから測る ―― 消えるのは欠陥の数で、戻るのは量ではない** ―― 球とトーラスと角柱のブール和から閉じた三角メッシュを作り、穴・裏返った面・非多様体辺・退化三角形・重複頂点・自己交差を種類ごとに既知個数だけ仕込んで、位相の数字と体積・表面積の両方で追いました。オイラー標数は 6 種のうち 5 種にまったく反応せず、穴 6 個と重複面 6 枚を同時に入れると頂点・辺・面・χ が健全な部品と 1 つも違わなくなります。直したあとも量は戻らず、半頂角 45° の穴を塞いだ球は表面積が予測 -2.145 % に対して実測 +6.868 %(縁が円ではなく階段だから)、頂点を 6 個だけ突き刺したメッシュは位相の検査を 3 つとも通り抜けたまま表面積 +4.414 % / 体積 -0.332 % と 13 倍食い違いました。*

[![健全な部品の χ は 0(種数 1)。χ=2 を合格条件にすると健全品が落ちる。最終行は打ち消し。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/02_euler_blindspots_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/02_euler_blindspots.png)

*↑ 測定の図 ―― 健全な部品の χ は 0(種数 1)。χ=2 を合格条件にすると健全品が落ちる。最終行は打ち消し。*

[![ただし順番が両向きに効く —— 溶接前は割れの境界を穴として数え、溶接後は退化三角形を数え損ねる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/03_defect_counts_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/03_defect_counts.png)

*↑ ただし順番が両向きに効く —— 溶接前は割れの境界を穴として数え、溶接後は退化三角形を数え損ねる。*

[![幅ゼロの割れ(重複頂点 18 個)を直した結果。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/05_repair_vs_restore_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/05_repair_vs_restore.png)

*↑ 幅ゼロの割れ(重複頂点 18 個)を直した結果。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/08_hole_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/08_hole_frames.png)

*↑ この回の図*

[![面積 0 の判定に引っかかるずっと手前で、潰れ面の法線は使いものにならなくなる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/11_sliver_threshold_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/11_sliver_threshold.png)

*↑ 面積 0 の判定に引っかかるずっと手前で、潰れ面の法線は使いものにならなくなる。*

[![動画(272 コマ、480 × 480 px): 健全な部品(面 11208 枚)の周りを 1.5 周しながら、QEM 簡略化の削減率を 0 → 98 % へ 8 段で上げる。面は平らに塗り、色は面の 3 頂点の平均曲率 |H|(尺度は削減](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/14_decimate_orbit.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/14_decimate_orbit.gif)

*↑ 動く図 ―― 動画(272 コマ、480 × 480 px): 健全な部品(面 11208 枚)の周りを 1.5 周しながら、QEM 簡略化の削減率を 0 → 98 % へ 8 段で上げる。面は平らに塗り、色は面の 3 頂点の平均曲率 |H|(尺度は削減前の 99 パーセンタイル 12.6 /mm で固定)。50 % 削減で体積の誤差は -0.019 % しかないのに曲率の 95 パーセンタイルは 5.89 → 7.72(+31 %)—— 明るい(尖った)面が先に増える。98 % 削減でようやく体積 -4.199 %。左下の 3 本は配列の軸(0 = 貫通穴の軸 = 画面の上、2 = 角柱ボスの側)。*

```
py -3.11 examples/poc_mesh_quality_repair.py
```

ソース: [examples/poc_mesh_quality_repair.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_mesh_quality_repair.py)

この回が作った図は全部で **14 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_mesh_quality_repair)

使用 op(ノートへ): [`decimate_qem`](https://furuse.work/ops/3d/mesh_process/decimate_qem.html) · [`face_normals`](https://furuse.work/ops/3d/mesh_process/face_normals.html) · [`fill_holes`](https://furuse.work/ops/2d/region/fill_holes.html) · [`inertia_tensor`](https://furuse.work/ops/3d/moment_invariant/inertia_tensor.html) · [`mesh_area`](https://furuse.work/ops/3d/mesh_process/mesh_area.html) · [`mesh_edge_lengths`](https://furuse.work/ops/3d/terrain/mesh_edge_lengths.html) · [`mesh_edge_stats`](https://furuse.work/ops/3d/resolution/mesh_edge_stats.html) · [`sdf_subtract`](https://furuse.work/ops/3d/sdf_csg/sdf_subtract.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`vertex_curvature`](https://furuse.work/ops/3d/mesh_process/vertex_curvature.html) · [`vertex_normals`](https://furuse.work/ops/3d/mesh_process/vertex_normals.html) · [`voxel_to_mesh`](https://furuse.work/ops/3d/transform/voxel_to_mesh.html)

## No.2026.101 —— パレットの積載率 —— 1 つの数字が「隙間」と「はみ出し」を同じ値にする

[![パレットの積載率 —— 1 つの数字が「隙間」と「はみ出し」を同じ値にする](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pallet_load_utilization/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pallet_load_utilization/01_scene.png)

*↑ **パレットの積載率 —— 1 つの数字が「隙間」と「はみ出し」を同じ値にする** ―― 1200 x 1000 mm のパレットに、中身が正反対の 2 つの荷を積んだ。荷 A は上から見えない 400 x 400 x 420 mm の空洞と幅 20 / 50 / 120 mm の隙間だらけ、荷 B は詰まっているが 90 mm はみ出して天端が制限 1800 mm を 100 mm 超える。中段の高さを閉形式で 995.0 mm に解くと、見かけの積載率は 62.65 % と 62.67 %(差 0.02 pt)で一致する——同じ数字なのに A は 3.11 pt が見えない空洞、B ははみ出し 2.10 pt + 高さ超過 0.58 pt で、処置は「積み直す」と「降ろす」で逆。荷を 1 個の外形とみなすゼロ点は荷 B で AABB 113.90 % / OBB 166.44 % と 100 % を超え、真の中身と押し出し形の IoU は 0.9493 と 1.0000 でどちらも「よく合っている」としか読めない。高さマップのセル寸法という 1 つのつまみが逆向きに 2 通り壊し、幅 w の隙間は max(0, 1 - g/w) で消え(g = 40 mm で 20 mm の隙間は完全に消失、g = w ちょうどは位相で全か無かに割れて 5 回に 1 回だけ全部見える)、一方で 1 mm も出ていない荷 A に周長 x g/2 x 天端 の偽はみ出しが立ち、g = 40 mm からは本当に出ている荷 B の 0.0450 m3 を上回る。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pallet_load_utilization/02_hidden_void_section_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pallet_load_utilization/02_hidden_void_section.png)

*↑ 測定の図*

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

ソース: [examples/poc_pallet_load_utilization.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pallet_load_utilization.py)

この回が作った図は全部で **8 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_pallet_load_utilization)

使用 op(ノートへ): [`aabb`](https://furuse.work/ops/3d/bounds/aabb.html) · [`convex_hull`](https://furuse.work/ops/3d/bounds/convex_hull.html) · [`euclidean_cluster`](https://furuse.work/ops/3d/segment/euclidean_cluster.html) · [`inner_box3`](https://furuse.work/ops/3d/regionprops/inner_box3.html) · [`mesh_volume`](https://furuse.work/ops/3d/mesh_process/mesh_volume.html) · [`voxel_iou`](https://furuse.work/ops/3d/metrics/voxel_iou.html)

## No.2026.075 —— 配管内面の減肉を展開図で測る ―― 軸を決めた分だけ、管底の腐食が消える

[![配管内面の減肉を展開図で測る ―― 軸を決めた分だけ、管底の腐食が消える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/01_scene_pipe_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/01_scene_pipe.png)

*↑ **配管内面の減肉を展開図で測る ―― 軸を決めた分だけ、管底の腐食が消える** ―― 合成の管に孔食・全周減肉・管底腐食・溶接ビード・楕円化・曲がりを既知の深さで仕込み、管内を走る距離センサの軸を意図的にずらして展開図を作りました。軸が 4.0 mm ずれるだけで腐食ゼロの真円の管の 44.8 % が減肉と判定され(中心のずれは振幅 e の 1 周期の正弦波になる、という幾何の予測との差は 1.84 ポイント)、偽の減肉体積は本物の孔食の 149.9 倍になります。1 周期を消せば偽物は消えますが、下水管でいちばん多い管底の腐食もその 79 % が同じ 1 周期に居るので検出率が 100.0 → 34.4 % へ落ち、軸の動きを物理どおり(直線とたわみ)に縛って初めて両方が残ります。*

[![下の帯の細くなっている所が管底腐食。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/02_scene_polar_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/02_scene_polar.png)

*↑ 測定の図 ―― 下の帯の細くなっている所が管底腐食。*

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

ソース: [examples/poc_pipe_wall_loss.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pipe_wall_loss.py)

この回が作った図は全部で **19 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_pipe_wall_loss)

使用 op(ノートへ): [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_select`](https://furuse.work/ops/blob/select/blob_select.html) · [`cylinder_sdf`](https://furuse.work/ops/3d/sdf_csg/cylinder_sdf.html) · [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`polar_unwrap`](https://furuse.work/ops/3d/curvilinear/polar_unwrap.html) · [`ransac_cylinder`](https://furuse.work/ops/3d/robust_fit/ransac_cylinder.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`sdf_subtract`](https://furuse.work/ops/3d/sdf_csg/sdf_subtract.html) · [`sdf_to_occupancy`](https://furuse.work/ops/3d/transform/sdf_to_occupancy.html) · [`spectrum`](https://furuse.work/ops/oned/signal/spectrum.html) · [`vol_wall_thickness`](https://furuse.work/ops/3d/probe/vol_wall_thickness.html)

## No.2026.076 —— 積層の反りは層の履歴が決める —— 均した面積は置き場所を捨てる

[![積層の反りは層の履歴が決める —— 均した面積は置き場所を捨てる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/01_scene.png)

*↑ **積層の反りは層の履歴が決める —— 均した面積は置き場所を捨てる** ―― 1 層あたり一定の収縮ひずみを仕込んだ合成形状 7 つを層に切り、断面積の履歴だけから梁の閉形式で反りを予測して、層を 1 枚ずつ生やす有限要素の実測と突き合わせた。最終形状だけを見る予測器は原理的にゼロ(2.712e-21)を返し、履歴の閉形式は 7 形状中 4 形状で 0.4 % 以内に当たるが、面積を長さ方向に均した瞬間に「どこに置いたか」が消える。層面積の履歴が 1 mm^2 も違わない三つ子でたわみは 0.4109 / 0.3809 / 0.3271 mm と 26 % 開き、基板を引き剥がす力に至っては 11.8 対 573.5 N の 48 倍違って合否まで割れた。*

[![この断面の面積の列だけが、閉形式の入力になる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/02_layer_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/02_layer_frames.png)

*↑ 測定の図 ―― この断面の面積の列だけが、閉形式の入力になる。*

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

ソース: [examples/poc_print_warpage_risk.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_print_warpage_risk.py)

この回が作った図は全部で **20 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_print_warpage_risk)

使用 op(ノートへ): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`sdf_to_occupancy`](https://furuse.work/ops/3d/transform/sdf_to_occupancy.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html)

## No.2026.081 —— 人と機械の安全距離 —— 代表点に置き換えた分だけ、危険が消える

[![人と機械の安全距離 —— 代表点に置き換えた分だけ、危険が消える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_safety_clearance/02_frames_clearance_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_safety_clearance/02_frames_clearance.png)

*↑ **人と機械の安全距離 —— 代表点に置き換えた分だけ、危険が消える** ―― 多関節の骨格に太さを持たせた人体(カプセル 10 本)と可動アームを合成し、表面どうしの真の最小分離距離を時刻ごとに閉形式で持たせた場面で、速度分離監視の判定がどこで嘘になるかを数えた。人を重心 1 点 + 半径 0.30 m の球で代表すると危険時に +0.166 m 遠く言い、危険の 14.3 % を見落とす(足元 1 点なら 28.6 %)—— どちらも誤検知はほぼ 0 で、壊れ方は片側にしか出ない。背面カメラ 1 台では危険フレームの 48.6 % で「推定を決めた部位が真の最近傍と違う」ことが起き見落としは 18.1 %、2 台目で 0 % に戻るが、繰り返し性から名乗った不確かさ 0.036 m は遮蔽の偏り 0.178 m の 5 分の 1 しか無い。*

[![危険 = 真の距離 < 0.640 m、停止判定 = 推定 < 0.690 m。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_safety_clearance/01_conditions_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_safety_clearance/01_conditions.png)

*↑ 測定の図 ―― 危険 = 真の距離 < 0.640 m、停止判定 = 推定 < 0.690 m。*

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

ソース: [examples/poc_safety_clearance.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_safety_clearance.py)

この回が作った図は全部で **14 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_safety_clearance)

使用 op(ノートへ): [`annotate3d_label`](https://furuse.work/ops/3d/annotate3d/annotate3d_label.html) · [`annotate3d_measure`](https://furuse.work/ops/3d/annotate3d/annotate3d_measure.html) · [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`capsule_sdf`](https://furuse.work/ops/3d/sdf_csg/capsule_sdf.html) · [`chamfer_distance`](https://furuse.work/ops/3d/metrics/chamfer_distance.html) · [`distance_line_line`](https://furuse.work/ops/3d/geometry/distance_line_line.html) · [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`face_areas`](https://furuse.work/ops/3d/mesh_process/face_areas.html) · [`hausdorff_distance`](https://furuse.work/ops/3d/metrics/hausdorff_distance.html) · [`query_distance`](https://furuse.work/ops/3d/occupancy/query_distance.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`sdf_to_occupancy`](https://furuse.work/ops/3d/transform/sdf_to_occupancy.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html)

## No.2026.082 —— 設計と実物の食い違いを部屋から測る ―― 合わせの妥協角は、無傷の部材へ配られる

[![設計と実物の食い違いを部屋から測る ―― 合わせの妥協角は、無傷の部材へ配られる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/01_scene_plan_section_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/01_scene_plan_section.png)

*↑ **設計と実物の食い違いを部屋から測る ―― 合わせの妥協角は、無傷の部材へ配られる** ―― 部屋 1 つ分の合成建物に、壁の傾き・床の勾配と反り・柱の寸法違い・開口のずれを既知量で仕込み、3 か所からの走査(柱の影・入射角依存の雑音・混合画素・レジストレーション誤差つき)で測り返した。設計モデルへの平均距離という建物 1 個の数字は施工誤差の有無で 1.41 mm しか動かず、点群を一括で合わせると壁の傾きは真値の 69 % に痩せ、代わりに完全に水平な天井が 0.89 mrad 傾いて見える(合わせが吸う量を閉形式で先に予測し、実測との差は 0.05 mrad)。崖は欠測率でなく残った面の高さで決まり、同じ 90 % の欠測でも無作為に落とせば 0.098 mrad、下から順に残す形なら 1.234 mrad と 12.6 倍違った。*

[![いちばん暗い所は 1 か所も見ていない。柱の影はスキャン位置から放射状に伸びる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/02_station_coverage_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/02_station_coverage.png)

*↑ 測定の図 ―― いちばん暗い所は 1 か所も見ていない。柱の影はスキャン位置から放射状に伸びる。*

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

ソース: [examples/poc_scan_to_bim_asbuilt.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_scan_to_bim_asbuilt.py)

この回が作った図は全部で **15 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt)

使用 op(ノートへ): [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`chamfer_distance`](https://furuse.work/ops/3d/metrics/chamfer_distance.html) · [`cylinder_sdf`](https://furuse.work/ops/3d/sdf_csg/cylinder_sdf.html) · [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`euclidean_cluster`](https://furuse.work/ops/3d/segment/euclidean_cluster.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`plane_sdf`](https://furuse.work/ops/3d/sdf_csg/plane_sdf.html) · [`plane_segmentation`](https://furuse.work/ops/3d/segment/plane_segmentation.html) · [`sdf_intersect`](https://furuse.work/ops/3d/sdf_csg/sdf_intersect.html) · [`sdf_subtract`](https://furuse.work/ops/3d/sdf_csg/sdf_subtract.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`voxel_grid_downsample`](https://furuse.work/ops/3d/preprocess/voxel_grid_downsample.html)

## No.2026.086 —— 構造物を年ごとに測り返す —— 測る場所がずれると、劣化は進んだように見える

[![構造物を年ごとに測り返す —— 測る場所がずれると、劣化は進んだように見える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/01_scene.png)

*↑ **構造物を年ごとに測り返す —— 測る場所がずれると、劣化は進んだように見える** ―― 橋桁(平面 7 枚 + 円柱 2 本)に既知のたわみ・断面欠損・支承沈下・ひび割れを 3 時点ぶん仕込み、走査位置も密度も姿勢も毎回変えて測り返した。劣化ゼロで測り直しただけで最近傍差分は中央値 21.07 mm・最大 42.64 mm の「変化」を返し、しきい値 1 mm で数えた偽の補修候補 5.098 L は本物 5.882 L の 87 % に達する。たわみを含めて全点で合わせると中央のたわみの 0.689(閉形式 2/3)が姿勢に吸われて支点に -1.737 mm の偽の隆起が出、決まらない橋軸方向は桁の平面ではなく支承の円柱にだけ「41.2 mm 水平に動いた」として現れる。*

[![下フランジの暗い窪みが断面欠損、面全体の淡い変化がたわみ。腹板(法線が水平)にはたわみが出ない ——同じ劣化でも面の向きで見え方が変わる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/02_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/02_frames.png)

*↑ 測定の図 ―― 下フランジの暗い窪みが断面欠損、面全体の淡い変化がたわみ。腹板(法線が水平)にはたわみが出ない ——同じ劣化でも面の向きで見え方が変わる。*

[![同じ構造物を 3 回測る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/03_conditions_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/03_conditions.png)

*↑ 同じ構造物を 3 回測る。*

[![真のたわみは中央 3.00 mm。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/05_scope_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/05_scope.png)

*↑ 真のたわみは中央 3.00 mm。*

[![予測は (ω×(p-c))·n を core 上で積んだだけ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/07_cliff_angle_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/07_cliff_angle.png)

*↑ 予測は (ω×(p-c))·n を core 上で積んだだけ。*

[![押し出し形状の平面は法線に x 成分を持たない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/09_prism_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/09_prism.png)

*↑ 押し出し形状の平面は法線に x 成分を持たない。*

[![動画(640 × 530、15 fps、135 コマ): 橋桁を 2 年で 3 回点検する。左は真の法線方向変化(展開図、真値は 3 時点だけ定義なので点検の間は直線で補間して描いた)、右は法線方向に測った変化で、点検(1 年・2 年)が来](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/12_years_video.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/12_years_video.gif)

*↑ 動く図 ―― 動画(640 × 530、15 fps、135 コマ): 橋桁を 2 年で 3 回点検する。左は真の法線方向変化(展開図、真値は 3 時点だけ定義なので点検の間は直線で補間して描いた)、右は法線方向に測った変化で、点検(1 年・2 年)が来たときだけ更新される。下段は代表 3 点の時系列(線 = 真値、点 = 測定)。灰の帯は t2 の差の誤差 RMS の ±2 倍(±3.45 mm)で、代表 3 点のうち欠損の谷(真 -21.4 mm)だけが帯を大きく越える。速度の誤差 RMS は 0.863 mm/年 で、1 mm/年 の進行は 2σ = 1.726 mm/年 の下に沈む。*

```
py -3.11 examples/poc_structure_4d_deterioration.py
```

ソース: [examples/poc_structure_4d_deterioration.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_structure_4d_deterioration.py)

この回が作った図は全部で **12 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_structure_4d_deterioration)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`chamfer_distance`](https://furuse.work/ops/3d/metrics/chamfer_distance.html) · [`cylinder_sdf`](https://furuse.work/ops/3d/sdf_csg/cylinder_sdf.html) · [`data_to_pixel`](https://furuse.work/ops/annotate/plot/data_to_pixel.html) · [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`euclidean_cluster`](https://furuse.work/ops/3d/segment/euclidean_cluster.html) · [`fit_circle_3d`](https://furuse.work/ops/3d/geometry/fit_circle_3d.html) · [`fit_plane_3d`](https://furuse.work/ops/3d/geometry/fit_plane_3d.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`hausdorff_distance`](https://furuse.work/ops/3d/metrics/hausdorff_distance.html) · [`plane_sdf`](https://furuse.work/ops/3d/sdf_csg/plane_sdf.html) · [`rmse`](https://furuse.work/ops/imgmetrics/fidelity/rmse.html) · [`sdf_intersect`](https://furuse.work/ops/3d/sdf_csg/sdf_intersect.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html) · [`voxel_grid_downsample`](https://furuse.work/ops/3d/preprocess/voxel_grid_downsample.html)

## No.2026.087 —— 対称性で欠けを補う —— 仮定した面がずれた分だけ、復元は嘘をつく

[![対称性で欠けを補う —— 仮定した面がずれた分だけ、復元は嘘をつく](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/01_scene.png)

*↑ **対称性で欠けを補う —— 仮定した面がずれた分だけ、復元は嘘をつく** ―― 左右対称な仮面を合成して完全形と対称面を真値に持ち、片側を球で削って対称復元を測った。面が真値なら復元 RMS 0.81 mm で穴埋め補間(1.60 mm)に勝つが、面が 1.39 度(84 分角)または 1.41 mm ずれた時点で負ける —— 誤差は鏡像変位の法線成分で予測でき(相対誤差 4.6 %、素朴な 2d sin α は 50.6 % 外す)、崖の位置は幾何だけで決まる。★欠損は面をずらす前に軸ごと飛ばし(失った点 3.1 % で PCA 候補の順位が逆転)、しかも本当は対称でない形では面が真値でも装飾を 3436 mm³ 捏造するか 3495 mm³ 消す。*

[![失われた真値の点から復元点群までの距離(符号なし、6 mm で頭打ち)。対称復元だけが眼窩の形を取り戻す。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/02_restore_error_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/02_restore_error_maps.png)

*↑ 測定の図 ―― 失われた真値の点から復元点群までの距離(符号なし、6 mm で頭打ち)。対称復元だけが眼窩の形を取り戻す。*

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

ソース: [examples/poc_symmetry_restoration.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_symmetry_restoration.py)

この回が作った図は全部で **10 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_symmetry_restoration)

使用 op(ノートへ): [`detect_reflection_symmetry`](https://furuse.work/ops/3d/symmetry/detect_reflection_symmetry.html) · [`fill_holes`](https://furuse.work/ops/2d/region/fill_holes.html) · [`fit_plane_3d`](https://furuse.work/ops/3d/geometry/fit_plane_3d.html) · [`icp_point2point_3d`](https://furuse.work/ops/3d/refine/icp_point2point_3d.html) · [`normalize`](https://furuse.work/ops/shape2d/descriptor/normalize.html) · [`reflect_points`](https://furuse.work/ops/3d/symmetry/reflect_points.html) · [`reflection_symmetry_score`](https://furuse.work/ops/3d/symmetry/reflection_symmetry_score.html)

## No.2026.146 —— 無限に寄り続ける絵と、回り続ける立体 ―― 「戻ってくること」を真値にする

[![無限に寄り続ける絵と、回り続ける立体 ―― 「戻ってくること」を真値にする](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/01_zoom_steps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/01_zoom_steps.png)

*↑ **無限に寄り続ける絵と、回り続ける立体 ―― 「戻ってくること」を真値にする** ―― 終わらない動きには、終わりを見なくても採点できる等式がある —— **無限ズーム**は自己相似比だけ寄ると絵が**画素単位で**元に戻り、**立体回転**は 2π で元に戻る。どちらも「最後に頭へ戻す」編集ではなく構成から従うので、真値は厳密に 0 差になる。素材は**パスカルの三角形 mod 2**(規則 90 の真値そのもの)で、空隙の階層は桁を数えるだけで閉形式に出る: `I = floor(u·2^D)`、`J = floor(v·2^D)`、`b` を `I & J` の最上位ビット位置として**深さ `d = D − b`**。`u → u/2` で `I → I>>1` だから `b` は 1 減り `d` は 1 増える —— **だからいくら寄っても解像度が落ちない**(拡大した画像を引き伸ばしているのではなく、画素ごとに整数のビット判定で決めている)。1 周 8 倍のズームで frame(T) と frame(0) の最大差は **0.0e+00**。★★芯 1: **測った次元がズームで 1 ミリも動かない。** 既存の `fractal_dimension` をズーム 6 段に掛けると標準偏差が**厳密に 0**、しかも近似の深さと画素の細かさが合ったときは **log2(3) = 1.584962500721 に差 8.9e-16 で一致**する —— 近似ではない。★★芯 2: **同じ op が 0.0 を返す場面がある。** 画素より細かい近似(深さ 9)を渡すと 0.0 になるが、これは「構造が無い」ではなく「**画素より細かい**」の意味で、実際その近似は 262,144 画素中**前景 0 画素**まで消えている。数字だけ見る門はここで嘘をつく。★★芯 3: **2π は浮動小数では閉じない。** 角度 `2πi/T` で作った回転は i=T で `sin(2π) = -2.45e-16` のぶんだけずれ、法線に **1.40e-12** が残る。周期を**整数の剰余**で閉じると **0.0e+00**(厳密) —— 周期境界 PoC と同じ型の教訓。★★芯 4: **外した予言を 1 つそのまま残してある。** 立方体のシルエット面積は正射影なら `a²(|cosθ|+|sinθ|)`。実測の残差 2% を見て「marching cubes の面取りのせい」と読んだが**外れ**で、距離を 6 → 96 に伸ばすと厳密な立方体も marching cubes も同じように 0.128 → 0.004 まで落ちた —— 床の正体は**透視投影**だった。面取りのぶんは距離では直らない別の量に出る: シルエット面積の最大/最小は厳密な立方体では √2 = 1.4142 に収束する(1.4167)のに、marching cubes では **1.3958 で止まる**。**1 つの残差を 2 つの原因に切り分けたのは、距離を振ったから。**ほかに、素材(深さの場)の 4 回対称は厳密 0 なのに**絵にすると 1.1e-16 崩れる**(数学ではなく 2×2 平均の足す順番)、ジャイロイドの 2 つの迷路の体積比は奇対称から 0.500000000000。**新しい op は 1 つも足していない。**検査 25 件・図 15 枚(動く図 2 枚を含む)。*

[![右は 2 枚の差をそのまま出したもので、**全画素が 0**(最大差 0.0e+00)。倍率を 8 倍にしたのに同じ絵になるのは、色の巡回(周期 3)が深さの巡回とちょうど噛み合うから。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/02_zoom_seam_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/02_zoom_seam.png)

*↑ 測定の図 ―― 右は 2 枚の差をそのまま出したもので、**全画素が 0**(最大差 0.0e+00)。倍率を 8 倍にしたのに同じ絵になるのは、色の巡回(周期 3)が深さの巡回とちょうど噛み合うから。*

[![**空隙の深さ(色 = 深さ、深いほど濃い)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/04_zoom_depth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/04_zoom_depth.png)

*↑ **空隙の深さ(色 = 深さ、深いほど濃い)。*

[![左から深さ 5..9。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/06_dimension_vs_level_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/06_dimension_vs_level.png)

*↑ 左から深さ 5..9。*

[![正射影ならシルエット面積は `a²(|cosθ| + |sinθ|)` で、45 度が最大(√2 倍)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/10_cube_steps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/10_cube_steps.png)

*↑ 正射影ならシルエット面積は `a²(|cosθ| + |sinθ|)` で、45 度が最大(√2 倍)。*

[![厳密な立方体は √2 = 1.4142 に収束する(1.4167)のに、marching cubes で取り出した面は **1.3958 で止まる**。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/13_mesh_is_not_a_cube_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/13_mesh_is_not_a_cube.png)

*↑ 厳密な立方体は √2 = 1.4142 に収束する(1.4167)のに、marching cubes で取り出した面は **1.3958 で止まる**。*

[![止めどきは呼んだ側が決める。24 コマで 1 周(8 倍)、そこから先は同じ絵が続く。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/03_zoom_loop.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/03_zoom_loop.gif)

*↑ 動く図 ―― 止めどきは呼んだ側が決める。24 コマで 1 周(8 倍)、そこから先は同じ絵が続く。*

[![1 周 18 コマ。添字の剰余で角度を作っているので、18 コマ目は 0 コマ目と画素単位で同じ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/08_solid_loop.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/08_solid_loop.gif)

*↑ 動く図 ―― 1 周 18 コマ。添字の剰余で角度を作っているので、18 コマ目は 0 コマ目と画素単位で同じ。*

```
py -3.11 examples/poc_endless_zoom_and_turning_solids.py
```

ソース: [examples/poc_endless_zoom_and_turning_solids.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_endless_zoom_and_turning_solids.py)

この回が作った図は全部で **15 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids)

使用 op(ノートへ): [`fractal_dimension`](https://furuse.work/ops/2d/features/fractal_dimension.html) · [`gyroid_isosurface`](https://furuse.work/ops/3d/surface/gyroid_isosurface.html) · [`mesh_volume`](https://furuse.work/ops/3d/mesh_process/mesh_volume.html) · [`perpetual_loop_seam`](https://furuse.work/ops/generative/loop/perpetual_loop_seam.html) · [`phong_shade`](https://furuse.work/ops/3d/render/phong_shade.html)

## No.2026.149 —— 4 次元の主張を、3 次元の平凡な op で採点する

[![4 次元の主張を、3 次元の平凡な op で採点する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/02_nested_tori_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/02_nested_tori.png)

*↑ **4 次元の主張を、3 次元の平凡な op で採点する** ―― **4 次元の位相と代数は、この箱にある 3 次元の産業用 op で厳密に採点できる** —— `fit_circle_3d`(点群に円を当てる)、`mesh_volume`(閉メッシュの符号つき体積)、`curve3d_tube_mesh`、`render_mesh`。ホップ束は S³ を S² 上の円の束に分ける。S³ の点を (z₁, z₂) ∈ C² と見ると、S² の 1 点 (θ, φ) の上の**繊維**は `q(t) = (cos(θ/2) e^{it}, sin(θ/2) e^{i(t+φ)})` という円で、**立体射影しても厳密に円のまま**(ヴィラルソー円)。★★芯 1: **4 次元の円が 2 次元の点になる。** 1 本の繊維をホップ写像で落とすと S² 上の広がりが **8.9e-16** —— 256 点すべてが 1 点に潰れる。★★芯 2: **その円を「点群に円を当てる op」が認める。** 立体射影した繊維の半径は緯度によって 0.70 から 7.34 まで変わるのに、`fit_circle_3d` の残差はどれも **1e-14 台**、平面からの外れも同じ桁。近似ではなく定理。★★芯 3: **2 本の繊維は必ず 1 回だけ絡む —— その整数が積分から出て、寄る速さまで予言できる。** ガウスの絡み数を離散化すると 4 通りの組すべてで 1 に寄り、**分割数を 2 倍にすると誤差がちょうど 1/4**(実測の比 **4.01 / 4.00 / 4.00 / 4.00**)—— **収束の次数が 1/n² だという予言が当たっている**。★★芯 4: **4 次元の回転は 2 枚の面で同時に起きて、比が有理のときだけ閉じる。** 超立方体(頂点 16・辺 32・面 24・胞 8、V − E + F − C = **0**、一辺 2 の超体積 **16.000000000000000**)を xy 面と zw 面で同時に回すと、比 1:2 / 2:3 / 3:4 は 60 歩でちょうど戻る(差 **0.0e+00**、途中の最小の隔たりは 0.23 以上なので「動いていないから一致した」ではない)。ところが比 1:φ(黄金比)は刻みを 400 に細かくして 20,000 歩まで回しても最小の隔たり **0.0257** で 0 に落ちない。★周期は**角度でなく整数の剰余**で閉じている。★★芯 5: **管の体積の誤差は、2 つに厳密に分かれる。** 真値を 2 段に置く —— A =「円断面・円中心線」、B =「**正 m 角形**断面・円中心線」。すると **B との相対差が断面の角数にまったく依らない**(同じ中心線なら m = 24 / 48 / 96 で差 **7.8e-16** 以内)—— **断面の粗さと中心線の粗さは独立に効く**。断面の効果は閉形式どおり **1/m²** で消える(比 3.99 / 4.00)。★★**外した予言を残してある。** 中心線の効果は 1/n² だと読んだが**外れ**で、点数を 2 倍・4 倍にすると **2.09 倍・4.15 倍**、つまり **1/n** でしか消えない —— 折れ線の周長は 1/n² で真値に寄るので、**残った差の原因は周長ではない**(継ぎ目の肉厚)。だから**片方のノブだけでは届かない**: 断面 96 角だけなら −0.001588、中心線 1600 点だけなら −0.003064 で止まり、両方回して −0.000925。**新しい op は 1 つも足していない。** 検査 19 件・図 10 枚(動く図 3 枚を含む)。*

[![ホップ束の繊維 4 本を立体射影して管にしたもの。★**4 次元では 4 本とも同じ大きさの円**なのに、3 次元へ写すと大きさが変わる —— それでも `fit_circle_3d` は 4 本すべてを **残差 1.4e-14** で円](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/01_hopf_fibers_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/01_hopf_fibers.png)

*↑ 測定の図 ―― ホップ束の繊維 4 本を立体射影して管にしたもの。★**4 次元では 4 本とも同じ大きさの円**なのに、3 次元へ写すと大きさが変わる —— それでも `fit_circle_3d` は 4 本すべてを **残差 1.4e-14** で円と認める。どの 2 本も**必ず 1 回だけ絡む**。*

[![`fit_circle_3d` に 200 点を食わせた残差。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/04_circle_fit_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/04_circle_fit.png)

*↑ `fit_circle_3d` に 200 点を食わせた残差。*

[![ガウスの積分で求めた絡み数の、**整数 1** からの差。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/05_linking_vs_n_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/05_linking_vs_n.png)

*↑ ガウスの積分で求めた絡み数の、**整数 1** からの差。*

[![真値 B は「**正 m 角形**断面・円中心線」の体積。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/08_tube_error_split_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/08_tube_error_split.png)

*↑ 真値 B は「**正 m 角形**断面・円中心線」の体積。*

[![断面の効果は閉形式どおり **1/m²**(比 3.99 / 4.00)で消えるのに、中心線の効果は **1/n**(比 2.09 / 4.15)でしか消えない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/09_tube_two_knobs_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/09_tube_two_knobs.png)

*↑ 断面の効果は閉形式どおり **1/m²**(比 3.99 / 4.00)で消えるのに、中心線の効果は **1/n**(比 2.09 / 4.15)でしか消えない。*

[![同じ 4 本を視点だけ回して見たもの。★**視点の周期は角度でなく整数の剰余で閉じている**(24 コマ目が 0 コマ目と同じ式になる)ので、継ぎ目が出ない。絡み方は視点を変えても変わらない —— 絡み数は**位相の量**だから。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/03_hopf_turn.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/03_hopf_turn.gif)

*↑ 動く図 ―― 同じ 4 本を視点だけ回して見たもの。★**視点の周期は角度でなく整数の剰余で閉じている**(24 コマ目が 0 コマ目と同じ式になる)ので、継ぎ目が出ない。絡み方は視点を変えても変わらない —— 絡み数は**位相の量**だから。*

[![比 **1 : 2**(有理)。60 コマでちょうど元に戻る —— 戻ったときの差は **0.0e+00**。★角度は**整数の剰余**で作っているので、有理な比なら継ぎ目が出ない。描いているのは 4 次元の超立方体を**2 枚の面で同時に](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/06_tesseract_rational.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/06_tesseract_rational.gif)

*↑ 動く図 ―― 比 **1 : 2**(有理)。60 コマでちょうど元に戻る —— 戻ったときの差は **0.0e+00**。★角度は**整数の剰余**で作っているので、有理な比なら継ぎ目が出ない。描いているのは 4 次元の超立方体を**2 枚の面で同時に回して**から w を落とした影。辺は 32 本とも同じ長さなのに、影では伸び縮みする。*

[![比 **1 : φ**(無理、黄金比)。この 60 コマでは戻らない。別に**刻みを 400 に細かくして 20,000 歩**まで回しても、最小の隔たりは **0.0257** で 0 に落ちない。★角度は**整数の剰余**で作っているの](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/07_tesseract_irrational.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/07_tesseract_irrational.gif)

*↑ 動く図 ―― 比 **1 : φ**(無理、黄金比)。この 60 コマでは戻らない。別に**刻みを 400 に細かくして 20,000 歩**まで回しても、最小の隔たりは **0.0257** で 0 に落ちない。★角度は**整数の剰余**で作っているので、有理な比なら継ぎ目が出ない。描いているのは 4 次元の超立方体を**2 枚の面で同時に回して**から w を落とした影。辺は 32 本とも同じ長さなのに、影では伸び縮みする。*

```
py -3.11 examples/poc_four_dimensions_by_three_d_tools.py
```

ソース: [examples/poc_four_dimensions_by_three_d_tools.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_four_dimensions_by_three_d_tools.py)

この回が作った図は全部で **10 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools)

使用 op(ノートへ): [`curve3d_tube_mesh`](https://furuse.work/ops/3d/surface/curve3d_tube_mesh.html) · [`fit_circle_3d`](https://furuse.work/ops/3d/geometry/fit_circle_3d.html) · [`mesh_volume`](https://furuse.work/ops/3d/mesh_process/mesh_volume.html)




---

**この展示館は Claude Code と一緒に作りました。** 問いと方向決めは私、実装・掃引・対照群・敵対レビューは Claude Code、という分業です。53 本の PoC を 2 日で走らせて図まで揃えられたのは、この運用のおかげです。試してみたい方は、こちらの招待リンクから **1 週間の無料トライアル** が使えます: [claude.ai/referral/0sqPw8E_lw](https://claude.ai/referral/0sqPw8E_lw)

面白い展示が 1 つでもあったら、**いいね・ストック**をもらえると助かります。どのウィングを次に増やすかは反応を見て決めるつもりなので、「自分の分野のこれが欲しい」もコメントで教えてください。実データに差し替えて崖の位置が変わった話は、いちばん聞きたい話です。
