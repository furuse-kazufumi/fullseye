> **言語 / Language**: **日本語** · [English](https://github.com/furuse-kazufumi/fullseye/blob/master/docs/articles/fullseye_poc_museum_device_qiita_en.md)

# 紙面の計測館 —— 装置の棟(センサーと計測器を物理から再現する)

> **[紙面の計測館 総合案内](https://qiita.com/furuse-kazufumi/items/c1606bcfa2085d204ad6)** の一棟です。ほかの棟・用語・テーゼは案内にあります。

この棟には **32 点**を掛けています。番号は**収蔵番号**で、棟を移しても分けても変わりません。

> 各展示の「使用 op」から、その op のノート(型契約・罠・図・Studio で走るプログラム)へ飛べます: [オペレータ目録](https://furuse.work/OP_CATALOG.html) / [op ノートの索引](https://furuse.work/ops/INDEX.html)。

### 装置の棟 ―― 生の出力から、装置固有の壊れ方まで再現する

計測装置を名前だけ借り、都合のよい画像を出すのは簡単です。この部屋の 32 点は逆に、光子・電子・干渉・熱拡散・走査・光線追跡から装置の生出力を作り、そこから普段の測定値までを一続きにしています。

同じ距離でも iToF と dToF では多重反射と pile-up の現れ方が違い、同じ粒子でも SEM と TEM では直径が違って読めます。TDI は段数を増やせば暗い欠陥が見える一方、同期ずれを段数ぶん積み重ねます。装置名が同じでも、物理を省いた模型では壊れる場所を再現できません。

各展示は閉形式、公開実測値、独立実装のいずれかを門にしています。狙いは実機の完全な代用品を名乗ることではなく、どの物理を入れ、何をまだ入れていないかを明示したうえで、測定値がいつ信用できなくなるかを実機に触れる前に確かめることです。

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

## No.2026.016 —— 光子を数えて距離を測る ―― 何個数えれば何ミリまで出るのか

[![光子を数えて距離を測る ―― 何個数えれば何ミリまで出るのか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/01_light_front.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/01_light_front.gif)

*↑ **光子を数えて距離を測る ―― 何個数えれば何ミリまで出るのか** ―― 主図は48フレーム、576×432の光前線動画。反射振幅を1–99.5 %で伸張してγ=0.7を適用した灰色像へ、奥行き範囲の7 %に広げた表示窓の琥珀色の光帯が近距離から遠距離まで重なる。別図は飛び画素の8倍拡大、壁隅の湾曲、低反射物体の雑音を示す。*

[![飛び画素（8倍拡大）、壁隅の系統的な湾曲、低反射物体の距離雑音を同じ尺度で示す。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/02_labelled_artefacts_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/02_labelled_artefacts.png)

*↑ 測定の図 ―― 飛び画素（8倍拡大）、壁隅の系統的な湾曲、低反射物体の距離雑音を同じ尺度で示す。*

[![距離出力｜反射振幅（γ=0.5）｜ピーク/背景比。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/03_range_amplitude_confidence_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/03_range_amplitude_confidence.png)

*↑ 距離出力｜反射振幅（γ=0.5）｜ピーク/背景比。*

[![平面、角、暗い物体。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/04_pixel_histograms_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/04_pixel_histograms.png)

*↑ 平面、角、暗い物体。*

[![背景が無ければ素の重心で足りる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/06_methods_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/06_methods.png)

*↑ 背景が無ければ素の重心で足りる。*

[![ゲート重心は CRB に寄り添って落ちる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/07_crb_scaling_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/07_crb_scaling.png)

*↑ ゲート重心は CRB に寄り添って落ちる。*

```
py -3.11 examples/poc_dtof_ranging.py
```

ソース: [examples/poc_dtof_ranging.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dtof_ranging.py)

この回が作った図は全部で **8 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_dtof_ranging)

使用 op(ノートへ): [`dtof_cube_depth`](https://furuse.work/ops/photon/dtof/dtof_cube_depth.html) · [`dtof_cube_simulate`](https://furuse.work/ops/photon/dtof/dtof_cube_simulate.html) · [`dtof_depth`](https://furuse.work/ops/photon/dtof/dtof_depth.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`spad_deadtime_apply`](https://furuse.work/ops/photon/spad/spad_deadtime_apply.html) · [`tcspc_background_subtract`](https://furuse.work/ops/photon/tcspc/tcspc_background_subtract.html) · [`tcspc_coates_correct`](https://furuse.work/ops/photon/spad/tcspc_coates_correct.html) · [`tcspc_simulate`](https://furuse.work/ops/photon/tcspc/tcspc_simulate.html)

## No.2026.022 —— 白色干渉計でナノメートルの段差をどこまで正確に測れるか

[![白色干渉計でナノメートルの段差をどこまで正確に測れるか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/01_surface_interferograms_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/01_surface_interferograms.png)

*↑ **白色干渉計でナノメートルの段差をどこまで正確に測れるか** ―― 白色干渉計の走査スタックを合成し、50〜500 nm の段差を測り返した図。雑音 1 % で偏り 2.4 nm 以内・標準偏差 14.1 nm 以内、しかも段差の大きさにほぼ依らない。ゼロ点(包絡線の最大サンプル)の誤差は走査ステップの半分に厳密一致し、Nyquist 上限 0.15 µm の手前 0.14 µm では雑音なしでも +14.1 nm。*

[![Truth, recovered height, error and low-modulation dropout map; pseudo-colour bars carry units.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/02_surface_height_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/02_surface_height.png)

*↑ 測定の図 ―― Truth, recovered height, error and low-modulation dropout map; pseudo-colour bars carry units.*

[![包絡線の中心が段差ぶんずれる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/04_interferogram_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/04_interferogram.png)

*↑ 包絡線の中心が段差ぶんずれる。*

[![0.02〜0.12 µm は 0.05 nm 以内で平ら。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/05_zstep_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/05_zstep_sweep.png)

*↑ 0.02〜0.12 µm は 0.05 nm 以内で平ら。*

[![centroid は散らばりが gaussian の 1/3〜1/5 なのに総合誤差では上に来る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/06_noise_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/06_noise_sweep.png)

*↑ centroid は散らばりが gaussian の 1/3〜1/5 なのに総合誤差では上に来る。*

[![4 種の段差でゲインが揃う = オフセットではなく倍率の誤差。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/07_centroid_gain_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/07_centroid_gain.png)

*↑ 4 種の段差でゲインが揃う = オフセットではなく倍率の誤差。*

[![48 raw uint8 coherence-scan frames; the localized envelope sweeps over the tilted step.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/03_surface_z_scan.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/03_surface_z_scan.gif)

*↑ 動く図 ―― 48 raw uint8 coherence-scan frames; the localized envelope sweeps over the tilted step.*

[![動画(148 コマ): 仕込む段差を 0 → 0.90 µm へ連続に増やし、同じ表面を 2 つの方法で測る(雑音なし)。左は低い側・高い側 1 画素ずつのコヒーレンス走査の信号で、縦線は csi_height_map(gaussian)が](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/08_step_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/08_step_sweep.gif)

*↑ 動く図 ―― 動画(148 コマ): 仕込む段差を 0 → 0.90 µm へ連続に増やし、同じ表面を 2 つの方法で測る(雑音なし)。左は低い側・高い側 1 画素ずつのコヒーレンス走査の信号で、縦線は csi_height_map(gaussian)が包絡線から読んだ高さ。右は測った段差 vs 仕込んだ段差。包絡線(だいだい)は全域で対角線に乗り、誤差は最大 8.5e-11 nm —— 包絡線には周期が無いので巻き戻らない。位相シフト法(水色、4 段)は段差 0.153 µm(λ/4 = 0.150 µm の直後)で初めて λ/2 ぶん飛び、以後 λ/2 ごとに鋸の歯になる。*

```
py -3.11 examples/poc_interferometry_step.py
```

ソース: [examples/poc_interferometry_step.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_interferometry_step.py)

この回が作った図は全部で **8 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_interferometry_step)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`color_bar`](https://furuse.work/ops/annotate/furniture/color_bar.html) · [`csi_contrast_map`](https://furuse.work/ops/interferometry/surface/csi_contrast_map.html) · [`csi_design`](https://furuse.work/ops/interferometry/design/csi_design.html) · [`csi_height_map`](https://furuse.work/ops/interferometry/surface/csi_height_map.html) · [`csi_stack_simulate`](https://furuse.work/ops/interferometry/simulate/csi_stack_simulate.html) · [`decode_fringe`](https://furuse.work/ops/3d/structured_light/decode_fringe.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`synthesize_fringes`](https://furuse.work/ops/3d/structured_light/synthesize_fringes.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html)

## No.2026.023 —— ライトフィールドから深度を出す ―― 既知の深度で作った光場に、ゼロ点を並べて突きつける

[![ライトフィールドから深度を出す ―― 既知の深度で作った光場に、ゼロ点を並べて突きつける](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/01_scene_and_depth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/01_scene_and_depth.png)

*↑ **ライトフィールドから深度を出す ―― 既知の深度で作った光場に、ゼロ点を並べて突きつける** ―― 9×9 の光場を解析的な逆写像で描き、真値スロープ地図に対して焦点度・EPI・2 眼ブロックマッチングを採点した図。定数ゼロ点には 22 倍勝つが、視点 2 枚だけ使う 2 眼に対しては cubic でようやく 1.6 倍。既定の linear 補間は整数スロープに吸着し、真値 1.30 を 1.4750 と読む(深度で 11.9 %)。*

[![9 by 9 sub-aperture views; disparity is in pixels per adjacent view.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/02_subaperture_mosaic_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/02_subaperture_mosaic.png)

*↑ 測定の図 ―― 9 by 9 sub-aperture views; disparity is in pixels per adjacent view.*

[![Raw micro-image array with an 8-times-area centre inset; display resize uses Lanczos filtering.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/03_raw_mla_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/03_raw_mla.png)

*↑ Raw micro-image array with an 8-times-area centre inset; display resize uses Lanczos filtering.*

[![Slanted EPI lines encode disparity in px/view; benchmark format is 9 by 9 views.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/04_epi_pair_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/04_epi_pair.png)

*↑ Slanted EPI lines encode disparity in px/view; benchmark format is 9 by 9 views.*

[![linear は 1.08/1.15 を 1.0 へ、1.85 を 2.0 側へ引く。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/07_focus_snapping_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/07_focus_snapping.png)

*↑ linear は 1.08/1.15 を 1.0 へ、1.85 を 2.0 側へ引く。*

[![EPI は SNR 20 で既に -35 %。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/08_texture_breakdown_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/08_texture_breakdown.png)

*↑ EPI は SNR 20 で既に -35 %。*

[![Twenty-four uint8 refocus frames, 0 to 3 px/view.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/05_refocus_stack.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/05_refocus_stack.gif)

*↑ 動く図 ―― Twenty-four uint8 refocus frames, 0 to 3 px/view.*

```
py -3.11 examples/poc_lightfield_depth.py
```

ソース: [examples/poc_lightfield_depth.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_lightfield_depth.py)

この回が作った図は全部で **12 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_lightfield_depth)

使用 op(ノートへ): [`color_bar`](https://furuse.work/ops/annotate/furniture/color_bar.html) · [`lf_depth_from_focus`](https://furuse.work/ops/lightfield/depth/lf_depth_from_focus.html) · [`lf_disparity_to_depth`](https://furuse.work/ops/lightfield/depth/lf_disparity_to_depth.html) · [`lf_epi`](https://furuse.work/ops/lightfield/views/lf_epi.html) · [`lf_epi_slope`](https://furuse.work/ops/lightfield/depth/lf_epi_slope.html) · [`lf_refocus`](https://furuse.work/ops/lightfield/refocus/lf_refocus.html) · [`lf_to_mla`](https://furuse.work/ops/lightfield/decode/lf_to_mla.html)

## No.2026.033 —— 偏光で鏡面反射を剥がす ―― フレネルの式で真値を作り、分離結果を突き合わせる

[![偏光で鏡面反射を剥がす ―― フレネルの式で真値を作り、分離結果を突き合わせる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/01_raw_polarizer_mosaic_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/01_raw_polarizer_mosaic.png)

*↑ **偏光で鏡面反射を剥がす ―― フレネルの式で真値を作り、分離結果を突き合わせる** ―― 拡散と鏡面を s/p 成分で合成し、フレネルの式から偏光度を出して分離結果を採点した図。偏光を使う手は入射角 20 度では 1.2 倍しか勝たない。拡散成分の誤差は閉形式 R_p·E に一致してブリュースター角 56.31 度で 0 ―― `polarization_separate` の拡散はその分だけ系統的に大きい。*

[![Half-resolution analyzer samples separated from the mosaic (one quarter of the pixels each).](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/02_analyzer_samples_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/02_analyzer_samples.png)

*↑ 測定の図 ―― Half-resolution analyzer samples separated from the mosaic (one quarter of the pixels each).*

[![Stokes fields, polarization degree, hue-wheel angle and the minimum-polarized component.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/03_stokes_and_glare_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/03_stokes_and_glare.png)

*↑ Stokes fields, polarization degree, hue-wheel angle and the minimum-polarized component.*

[![R_p がブリュースター角で 0 を横切る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/04_fresnel_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/04_fresnel.png)

*↑ R_p がブリュースター角で 0 を横切る。*

[![実測と閉形式が重なる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/05_angle_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/05_angle_error.png)

*↑ 実測と閉形式が重なる。*

[![残差はローブと同じ形。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/06_separation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/06_separation.png)

*↑ 残差はローブと同じ形。*

```
py -3.11 examples/poc_polarization_specular.py
```

ソース: [examples/poc_polarization_specular.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_polarization_specular.py)

この回が作った図は全部で **7 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_polarization_specular)

使用 op(ノートへ): [`fresnel_reflectance`](https://furuse.work/ops/3d/optics/fresnel_reflectance.html) · [`polarization_dolp_map`](https://furuse.work/ops/specular/polarization/polarization_dolp_map.html) · [`polarization_render`](https://furuse.work/ops/specular/polarization/polarization_render.html) · [`polarization_separate`](https://furuse.work/ops/specular/polarization/polarization_separate.html) · [`polarization_stokes`](https://furuse.work/ops/specular/polarization/polarization_stokes.html) · [`rmse`](https://furuse.work/ops/imgmetrics/fidelity/rmse.html)

## No.2026.078 —— 太陽光発電所のドローン熱画像 —— 温度差を測っているつもりで、風と角度を測っている

[![太陽光発電所のドローン熱画像 —— 温度差を測っているつもりで、風と角度を測っている](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/06_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/06_scene.png)

*↑ **太陽光発電所のドローン熱画像 —— 温度差を測っているつもりで、風と角度を測っている** ―― 定常熱収支の閉形式でメガソーラーのアレイを合成し、既知の故障(セル内ホットスポット・ストリング故障)と、故障ではない温度差(影・汚れ)を仕込んだ図。余剰発熱 320 W/m² のホットスポットは薄まる前 11.20 K なのにカメラには 4.23 K しか届かず、薄めているのは予想した熱伝導(×0.960)ではなくカメラ(×0.511)だった。電気的故障をひとつも置かない対照群でも、画像平均を基準にすると塊が 6 個上がる(健全 1・非故障の温度差 5)。崖はしきい値ではなく面積の門が決め、ホットスポットは風速 1.0 m/s で消える(面積基準の予測 1.1 m/s、ピーク基準の予測 3.0 m/s は外れ)。列間影は同じストリングの日向側を +4.68 K 熱くし、本物のストリング故障 +5.55 K との差は 0.87 K しかない。*

[![「偽」= 故障でも影でも汚れでもない場所に出た塊。しきい値 3.0 K、風速 1.0 m/s。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/01_norm_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/01_norm_table.png)

*↑ 測定の図 ―― 「偽」= 故障でも影でも汚れでもない場所に出た塊。しきい値 3.0 K、風速 1.0 m/s。*

[![U(v) = 1.75·(5.7 + 3.8v + h_rad)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/02_wind_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/02_wind_sweep.png)

*↑ U(v) = 1.75·(5.7 + 3.8v + h_rad)。*

[![ε(θ) は Fresnel(等価屈折率 1.8)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/04_angle_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/04_angle_sweep.png)

*↑ ε(θ) は Fresnel(等価屈折率 1.8)。*

[![上段の塊はすべて偽か非故障の温度差。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/07_false_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/07_false_map.png)

*↑ 上段の塊はすべて偽か非故障の温度差。*

[![Module-level correction preserves the detection chapters and their thresholds.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/09_orthorectified_detection_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/09_orthorectified_detection.png)

*↑ Module-level correction preserves the detection chapters and their thresholds.*

```
py -3.11 examples/poc_pv_thermal_survey.py
```

ソース: [examples/poc_pv_thermal_survey.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pv_thermal_survey.py)

この回が作った図は全部で **10 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_pv_thermal_survey)

使用 op(ノートへ): [`beer_lambert_transmittance`](https://furuse.work/ops/optics/glassbody/beer_lambert_transmittance.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_select`](https://furuse.work/ops/blob/select/blob_select.html) · [`color_bar`](https://furuse.work/ops/annotate/furniture/color_bar.html) · [`fresnel_dielectric`](https://furuse.work/ops/optics/interface/fresnel_dielectric.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`overlay_mask`](https://furuse.work/ops/annotate/overlay/overlay_mask.html) · [`surface_form_remove`](https://furuse.work/ops/roughness/prepare/surface_form_remove.html) · [`volume_downsample`](https://furuse.work/ops/3d/preprocess/volume_downsample.html) · [`warp_by_plane`](https://furuse.work/ops/3d/plane_sweep_stereo/warp_by_plane.html) · [`zoom_image_factor`](https://furuse.work/ops/2d/geometry/zoom_image_factor.html)

## No.2026.113 —— 熱画像は温度画像ではない ―― 放射率・反射・透過を取り違えたまま「温度」と呼ぶ

[![熱画像は温度画像ではない ―― 放射率・反射・透過を取り違えたまま「温度」と呼ぶ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/15_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/15_scene.png)

*↑ **熱画像は温度画像ではない ―― 放射率・反射・透過を取り違えたまま「温度」と呼ぶ** ―― 熱カメラの DN を温度に戻す**全経路**を、真値を自分で植てて測る。前向きモデルは `L = τ[ε L_bb(T_obj) + (1-ε) L_bb(T_refl)] + (1-τ) L_bb(T_atm)`。★**床を先に測る**: 往復 1.75e-06 K、量子化 6.28e-03 K、+NETD 2.71e-02 K。**350.0 K では厳密に 0 が出たが、それは校正表の節点にたまたま乗っただけ**なので、節点を外して測り直した —— **0 を床と呼ぶのは嘘**になる。★★**閉形式の予測を印字して、外した**: 素朴な `n = c2/(λ_eff T)` は数値微分から最大 **16.6 %** ずれる。外れの正体は実効波長の選び方ではなく **`e^x/(e^x-1)` の欠け**(x = c2/λT)で、入れると誤差 **0.00 %**。MWIR 300 K は x=10.9 でほぼ Wien、LWIR 800 K は x=1.80 で Rayleigh–Jeans 寄り。★★**崖の向きも外した**: 「低温ほど急」と印字したが、**絶対誤差は高温ほど大きい**(Δε/ε=5 % で 305 K の 0.233 K → 800 K の **16.907 K**)。log-log の傾きは実測 **2.717**、内訳は T/n = 1.741 + 反射因子 0.977 = 2.718 —— **閉形式は最初からそう言っていて、自分の式を読み違えていた**。★★**「低温ほど急」は正しかったが、犯人が違った**: 周囲からの上昇 (T_obj - T_refl) で割ると、放射率の誤差は 4.7 % → 3.4 % と **1.40 倍しか動かず発散しない**(Δε/ε に収束する)。発散するのは **T_refl の取り違え**のほうで 13.2 % → 0.0 %(**972 倍**)。上昇 10 K を切ると、反射が放射率より重くなる。★★**不確かさは足し算にならない**。ε=0.60±0.05・T_refl=300±5 K・相関 ρ=+0.7 という現実的な組を 20000 試行で数えると、**「95 % 区間」が実際に真値を包む割合は 独立 RSS で 88.03 %、相関つき Monte Carlo で 94.44 %**(-6.4 点)。★**床を先に測ってある**: ρ=0 なら RSS 95.03 % / MC 94.52 % なので、この落差は実装ではなく**相関を無視したことそのもの**。真の u 5.6518 K に対し RSS は 4.5086 K = **区間が 20.2 % 狭い**。取りこぼしは片側に寄る(下 7.14 % / 上 4.83 %)。ρ=-0.7 なら逆に 99.64 % と**過剰**になる —— **独立と仮定することは、安全側でも危険側でもなく『分からない側』**。★★**guard band(合否判定)**: 40000 試行(真値 65〜95 ℃ 一様)で、**誤合格 8.03 %(不確かさ無視)→ 0.81 %(RSS)→ 0.14 %(相関つき MC)**。**RSS は MC の 5.6 倍 誤合格する**。誤不合格は 6.69 → 28.22 → 40.03 % で、MC の band が広いのは相関だけでなく**分布の歪み**の分もある(対称 1.96u なら 11.08 K、上側 97.5 百分位は 13.47 K)。★**単位の崖**は 8 通りで例外 3 / 静かに 5。★**同じ「T_refl を摂氏で書く」取り違えが、ε=0.95 では静かに通り(-22.1 K)、ε=0.10 では例外になる** —— **止まるかどうかは間違いの種類ではなく場面で決まる**。静かな側は DN 平均→温度(+1.543 K、Jensen)、見かけ温度(-2.121 K)、τ 二重掛け(+2.485 K)、ΔT/T をセ氏(感度を 1/4.46 に過小評価)。★**熱画像そのもの**: 同じ 375.0 K のボルト(ε=0.10)が、ε=1 の絵では周りの塗装面より **62.3 K 低く**写る(309.7 K 対 372.0 K)—— 発熱部の真上が**いちばん健全に見える**。ε 地図で 375.0 K に復帰(残差 rms 0.106 K)するが、★**補正は偏りを消す代わりに雑音を増やす**: 残差 rms は塗装面 0.0571 K に対しボルト **0.3673 K(6.4 倍)**。ε の比 9.5 より小さいのは、ボルトの DN が低くて光子雑音も小さいから —— **2 つの効き方が逆向き**。★★**道具の穴を見つけて、その場で直した**: `fs.noise_sigma(method='mad')` は整数値の画像で **σ=0.5 相当のとき 0.0000** を返し、返せる値は 1.4826 の倍数だけ(σ=1.0 も σ=1.983 も同じ 1.4826)。14 bit の生 DN はまさに整数。**下流はもっと悪く、200x200 の整数フレームに植えた点目標 2 個を `star_detect` が 0 個**と返していた。`star_detect` には `σ≤0` の門が**在った**のに、コメントが「完全に平坦 = 雑音が測れない」と書いていて**前提のほうが誤り**だった。しかも `clip` 法の存在はコード内コメントに書かれていた —— **知識は在ったが、読む側(docstring と既定値)に無かった**。いまは `noise_sigma` が警告、`star_detect` は**平坦なら空・平坦でなければ拒否**。`clip` に替えれば植えた 2 個がちゃんと出る。*

[![LWIR・350 K・ε=0.95。校正表と直接積分の相対差は最大 8.9e-16。以下の誤差はすべてこの床の上。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/01_floor_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/01_floor.png)

*↑ 測定の図 ―― LWIR・350 K・ε=0.95。校正表と直接積分の相対差は最大 8.9e-16。以下の誤差はすべてこの床の上。*

[![n = d ln L_bb/d ln T。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/02_planck_index_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/02_planck_index.png)

*↑ n = d ln L_bb/d ln T。*

[![LWIR・T_obj = 350 K・T_refl = 300 K。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/06_cliff_curves_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/06_cliff_curves.png)

*↑ LWIR・T_obj = 350 K・T_refl = 300 K。*

[![20000 試行 / 点。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/10_coverage_rho_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/10_coverage_rho.png)

*↑ 20000 試行 / 点。*

[![止まるのは校正表の範囲外に落ちたときだけ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/14_units_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/14_units.png)

*↑ 止まるのは校正表の範囲外に落ちたときだけ。*

```
py -3.11 examples/poc_thermal_radiometry.py
```

ソース: [examples/poc_thermal_radiometry.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_thermal_radiometry.py)

この回が作った図は全部で **18 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_thermal_radiometry)

使用 op(ノートへ): [`beer_lambert_transmittance`](https://furuse.work/ops/optics/glassbody/beer_lambert_transmittance.html) · [`interp_linear`](https://furuse.work/ops/math/interp_poly/interp_linear.html) · [`mat_eigh`](https://furuse.work/ops/math/linalg/mat_eigh.html) · [`noise_sigma`](https://furuse.work/ops/astrostack/quality/noise_sigma.html) · [`photon_uncertainty`](https://furuse.work/ops/photon/counting/photon_uncertainty.html) · [`poly_fit`](https://furuse.work/ops/math/interp_poly/poly_fit.html) · [`stat_correlation`](https://furuse.work/ops/math/stats/stat_correlation.html) · [`stat_covariance`](https://furuse.work/ops/math/stats/stat_covariance.html) · [`stat_describe`](https://furuse.work/ops/math/stats/stat_describe.html) · [`stat_histogram`](https://furuse.work/ops/math/stats/stat_histogram.html)

## No.2026.043 —— パルスサーモグラフィで内部欠陥の深さを測る

[![パルスサーモグラフィで内部欠陥の深さを測る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/02_depth_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/02_depth_map.png)

*↑ **パルスサーモグラフィで内部欠陥の深さを測る** ―― フラッシュ加熱後の表面温度を 1 次元熱伝導の厳密解で作り、剥離の深さを画像から当てる図。直径が深さの 4 倍以上なら数 % で当たるが、深さ 0.5 mm・直径 2 mm では +627 %。原因は横拡散ではなく当てはめる時間窓で、窓を 25 s → 4 s に切り詰めると -9 % に戻る。*

[![右下三角(直径が深さの 4 倍以上)は数 %。左上は横拡散で壊れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/01_depth_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/01_depth_table.png)

*↑ 測定の図 ―― 右下三角(直径が深さの 4 倍以上)は数 %。左上は横拡散で壊れる。*

[![Viewer-gamma grayscale; NETD 0.02 K, low-frequency NUC residual 0.08 K RMS, four dead pixels.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/03_thermal_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/03_thermal_frames.png)

*↑ Viewer-gamma grayscale; NETD 0.02 K, low-frequency NUC residual 0.08 K RMS, four dead pixels.*

[![Sequential turbo-like depth scale in millimetres; signed error at right.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/05_depth_truth_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/05_depth_truth_error.png)

*↑ Sequential turbo-like depth scale in millimetres; signed error at right.*

[![早期の勾配は -1/2。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/06_tsr_curves_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/06_tsr_curves.png)

*↑ 早期の勾配は -1/2。*

[![Forty-eight uint8 cooling frames after a non-uniform flash.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/04_cooling.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/04_cooling.gif)

*↑ 動く図 ―― Forty-eight uint8 cooling frames after a non-uniform flash.*

```
py -3.11 examples/poc_thermography_ndt.py
```

ソース: [examples/poc_thermography_ndt.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_thermography_ndt.py)

この回が作った図は全部で **7 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_thermography_ndt)

使用 op(ノートへ): [`color_bar`](https://furuse.work/ops/annotate/furniture/color_bar.html)

## No.2026.178 —— カメラを買わずにカメラを測る ―― EMVA 1288 の手順で、既知の値を仕込んだセンサから量子効率・ゲイン・暗雑音を取り戻す

[![カメラを買わずにカメラを測る ―― EMVA 1288 の手順で、既知の値を仕込んだセンサから量子効率・ゲイン・暗雑音を取り戻す](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/01_raw_dark_flat_saturation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/01_raw_dark_flat_saturation.png)

*↑ **カメラを買わずにカメラを測る ―― EMVA 1288 の手順で、既知の値を仕込んだセンサから量子効率・ゲイン・暗雑音を取り戻す** ―― 主図は640×480の暗画像・平坦画像・飽和像を等倍で並べ、行1 DN・列1.5 DN・画素4 DNの固定模様と9個の欠陥画素を見える形にした。*

[![平坦画像2枚の差（時間雑音）｜平坦平均−暗平均（空間雑音）｜6σ欠陥画素図。固定模様を無効化する検査では中央の空間模様が消え、ゲートは赤になる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/02_temporal_spatial_defects_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/02_temporal_spatial_defects.png)

*↑ 測定の図 ―― 平坦画像2枚の差（時間雑音）｜平坦平均−暗平均（空間雑音）｜6σ欠陥画素図。固定模様を無効化する検査では中央の空間模様が消え、ゲートは赤になる。*

[![規格の模擬カメラ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/03_highpass_prnu_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/03_highpass_prnu.png)

*↑ 規格の模擬カメラ。*

[![白い DSNU は平らな床(高さ = 標準偏差 1.5 DN)、正弦は鋭い山(横 0.04・縦 0.2 c/px)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/04_spectrogram_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/04_spectrogram.png)

*↑ 白い DSNU は平らな床(高さ = 標準偏差 1.5 DN)、正弦は鋭い山(横 0.04・縦 0.2 c/px)。*

[![線形なセンサを乱数を変えて撮り、式 51(局所の傾きの相対偏差の平均)を出す。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/06_eq51_pixels_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/06_eq51_pixels.png)

*↑ 線形なセンサを乱数を変えて撮り、式 51(局所の傾きの相対偏差の平均)を出す。*

[![暗画像の分散が 0.24 DN² より小さいと、規格は σ_d を推定しない(式 53・54)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/09_validity_boundary_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/09_validity_boundary.png)

*↑ 暗画像の分散が 0.24 DN² より小さいと、規格は σ_d を推定しない(式 53・54)。*

[![露光を上げながら同じ露光で 2 枚ずつ撮り、平均と時間分散(2 枚の差から、式 18)を 1 点ずつ置く。直線の傾きがシステムゲイン K = 0.2086 DN/e⁻(仕込み 0.21)。飽和の近くでは分散が潰れるので、規格は 0〜70 %](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/07_photon_transfer.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/07_photon_transfer.gif)

*↑ 動く図 ―― 露光を上げながら同じ露光で 2 枚ずつ撮り、平均と時間分散(2 枚の差から、式 18)を 1 点ずつ置く。直線の傾きがシステムゲイン K = 0.2086 DN/e⁻(仕込み 0.21)。飽和の近くでは分散が潰れるので、規格は 0〜70 % の点だけで当てる。*

```
py -3.11 examples/poc_emva1288_sensor.py
```

ソース: [examples/poc_emva1288_sensor.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_emva1288_sensor.py)

この回が作った図は全部で **10 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_emva1288_sensor)

使用 op(ノートへ): [`emva_dark_current`](https://furuse.work/ops/optics/sensorchar/emva_dark_current.html) · [`emva_defect_pixels`](https://furuse.work/ops/optics/sensorchar/emva_defect_pixels.html) · [`emva_dynamic_range`](https://furuse.work/ops/optics/sensorchar/emva_dynamic_range.html) · [`emva_exposure_for_snr`](https://furuse.work/ops/optics/sensorchar/emva_exposure_for_snr.html) · [`emva_highpass`](https://furuse.work/ops/optics/sensorchar/emva_highpass.html) · [`emva_linearity_error`](https://furuse.work/ops/optics/sensorchar/emva_linearity_error.html) · [`emva_pair_statistics`](https://furuse.work/ops/optics/sensorchar/emva_pair_statistics.html) · [`emva_photon_exposure`](https://furuse.work/ops/optics/sensorchar/emva_photon_exposure.html) · [`emva_photon_transfer`](https://furuse.work/ops/optics/sensorchar/emva_photon_transfer.html) · [`emva_ptc_linearity_check`](https://furuse.work/ops/optics/sensorchar/emva_ptc_linearity_check.html) · [`emva_quantum_efficiency`](https://furuse.work/ops/optics/sensorchar/emva_quantum_efficiency.html) · [`emva_sensitivity_threshold`](https://furuse.work/ops/optics/sensorchar/emva_sensitivity_threshold.html) · [`emva_snr_curve`](https://furuse.work/ops/optics/sensorchar/emva_snr_curve.html) · [`emva_spatial_nonuniformity`](https://furuse.work/ops/optics/sensorchar/emva_spatial_nonuniformity.html) · [`emva_spectrogram`](https://furuse.work/ops/optics/sensorchar/emva_spectrogram.html) · [`emva_total_snr`](https://furuse.work/ops/optics/sensorchar/emva_total_snr.html) · [`spectrogram`](https://furuse.work/ops/oned/signal/spectrogram.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html)

## No.2026.090 —— 溶接 X 線透過像の気孔 ―― 等級を 1 段間違える画像の割合で締める

[![溶接 X 線透過像の気孔 ―― 等級を 1 段間違える画像の割合で締める](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/01_scene_radiograph_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/01_scene_radiograph.png)

*↑ **溶接 X 線透過像の気孔 ―― 等級を 1 段間違える画像の割合で締める** ―― 板厚 10 mm + 円弧の余盛 + 球形気孔を Beer–Lambert で閉形式に描き、散乱・不鋭度・粒状雑音を足した透過像。固定しきい値のゼロ点は余盛のつま先を気孔に数える(塊 124 個、合計面積 15.19 mm²、真値 7.93)。検出の崖は CNR = 16.12·d² から先に予測でき、50 % 検出径は Rose の CNR = 4 では 0.50 mm と外れ、平滑化と最小面積 3 px を入れた予測 0.58 mm に対し実測 0.57 mm。背景推定 op の窓上限(矩形オープニング 9 px)は 2.0 mm から検出率 50 % を割り 2.5 mm で 0 % の崖になる ―― op を選ぶことが測定範囲を選ぶ。散乱 SPR=1 は体積径を (1+SPR)^(-1/3) で -22.6 %(予測 -20.6 %)縮める。等級を 1 段間違える画像はゼロ点 90 % → 体積径 23 %。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/02_map_detections_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/02_map_detections.png)

*↑ 測定の図*

[![小さい側の崖は CNR で予測どおり。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/03_detect_vs_diameter_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/03_detect_vs_diameter.png)

*↑ 小さい側の崖は CNR で予測どおり。*

[![面積径は小さい側で縮む(等高線が内側)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/05_diameter_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/05_diameter_error.png)

*↑ 面積径は小さい側で縮む(等高線が内側)。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/08_toe_false_positives_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/08_toe_false_positives.png)

*↑ この回の図*

[![体積径は (1+SPR)^(-1/3) で縮む。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/10_scatter_diameter_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/10_scatter_diameter_bias.png)

*↑ 体積径は (1+SPR)^(-1/3) で縮む。*

```
py -3.11 examples/poc_weld_radiograph_porosity.py
```

ソース: [examples/poc_weld_radiograph_porosity.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_weld_radiograph_porosity.py)

この回が作った図は全部で **12 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_weld_radiograph_porosity)

使用 op(ノートへ): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`blob_select`](https://furuse.work/ops/blob/select/blob_select.html) · [`estimate_noise`](https://furuse.work/ops/2d/features/estimate_noise.html) · [`gauss_image`](https://furuse.work/ops/2d/smoothing/gauss_image.html) · [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`gray_opening_rect`](https://furuse.work/ops/2d/morphology/gray_opening_rect.html) · [`identity`](https://furuse.work/ops/2d/misc/identity.html) · [`log_image`](https://furuse.work/ops/2d/arithmetic/log_image.html) · [`measure_pairs`](https://furuse.work/ops/measure1d/caliper/measure_pairs.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`median_rect`](https://furuse.work/ops/2d/rank/median_rect.html) · [`sk_rolling_ball`](https://furuse.work/ops/2d/smoothing/sk_rolling_ball.html) · [`xsitk_grayscale_grindpeak`](https://furuse.work/ops/2d/extra/xsitk_grayscale_grindpeak.html)

## No.2026.214 —— 粉末 X 線回折の 2-D 検出器像から相を 1 つずつ剥がす ―― 較正・方位積分・NNLS・残差の未知相。真値は NIST SRM 640g の証明書と COD の CIF、合成と解析が模型を共有する分は食い違わせて測る

[![粉末 X 線回折の 2-D 検出器像から相を 1 つずつ剥がす ―― 較正・方位積分・NNLS・残差の未知相。真値は NIST SRM 640g の証明書と COD の CIF、合成と解析が模型を共有する分は食い違わせて測る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pxrd_phase_peel/01_phase_peel.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pxrd_phase_peel/01_phase_peel.gif)

*↑ **粉末 X 線回折の 2-D 検出器像から相を 1 つずつ剥がす ―― 較正・方位積分・NNLS・残差の未知相。真値は NIST SRM 640g の証明書と COD の CIF、合成と解析が模型を共有する分は食い違わせて測る** ―― 混合物の粉末に X 線を当てると、検出器には相ごとのデバイ環が重なって写る。新モジュール pxrd(14 op)は学習なしに、標準 Si の環で検出器の中心・距離・傾きを較正し(傾き 3° で中心 0.011 px、距離 0.0009 %、傾き 3.004°・向き −40.01°、rms 0.019°)、方位積分で 2θ のプロファイルに落とし、山の幅から Scherrer で結晶子径を出し(354 Å、真 350 Å)、CIF から作った参照の辞書で相を 1 つずつ剥がし(NNLS の前進選択、NaCl > CaF₂ > コランダムの順、rwp 0.546 → 0.179)、残差に残った 8 本の山を立方晶 F・a = 4.2170 Å(真 4.2170)と指数付けして、候補 4 つ(MgO・NiO・CaO・KCl)から MgO を名指しする。4 相(35 / 30 / 20 / 15 wt%)の分率の誤差は 0.04 wt%。外の真値は NIST SRM 640g の証明書: a = 0.543 110 9 nm と Cu Kα1 から、表の線 11 本を Bragg + 消滅則で最大 0.00044° に再現し、140° までに他の線は 1 本も出ない。相は COD の CIF(CC0、repo の外)。罠: 傾き 5° を無視して積分すると環が楕円になり、山 10 本が 23 本に割れる。試料の格子が参照より 0.4 % 大きいだけで分率が崩れ、格子の追い込みで戻る。正直に: 合成と解析は同じ物理模型を共有するので、0.04 wt% は「幾何・画素・雑音・重なりを通り抜けても模型の量が戻る」確認にとどまる。模型をわざと食い違わせて漏れを測った: 山の形の取り違え 0.33 wt%、イオンと中性原子 0.06 wt%、結晶子径 −29 % で 0.97 wt%。微視的吸収・選択配向・異常分散は模型に無く、強度の外部真値(実測の相対強度)もまだ無い。*

[![the detector image coloured by phase (1:1 pixels, lossless PNG)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pxrd_phase_peel/02_detector_by_phase_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pxrd_phase_peel/02_detector_by_phase.png)

*↑ 測定の図 ―― the detector image coloured by phase (1:1 pixels, lossless PNG)*

[![the observed detector image (background removed, gamma 0.5)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pxrd_phase_peel/03_detector_observed_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pxrd_phase_peel/03_detector_observed.png)

*↑ the observed detector image (background removed, gamma 0.5)*

[![integrated profile, NNLS fit and each phase's contribution](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pxrd_phase_peel/04_profile_fit_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pxrd_phase_peel/04_profile_fit.png)

*↑ integrated profile, NNLS fit and each phase's contribution*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pxrd_phase_peel/06_trap_lattice_mismatch_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pxrd_phase_peel/06_trap_lattice_mismatch.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pxrd_phase_peel/08_calibration_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pxrd_phase_peel/08_calibration.png)

*↑ この回の図*

```
py -3.11 examples/poc_pxrd_phase_peel.py
```

ソース: [examples/poc_pxrd_phase_peel.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pxrd_phase_peel.py)

この回が作った図は全部で **9 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_pxrd_phase_peel)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`azimuthal_integrate`](https://furuse.work/ops/drive/pxrd/azimuthal_integrate.html) · [`cif_read`](https://furuse.work/ops/drive/pxrd/cif_read.html) · [`cubic_index`](https://furuse.work/ops/drive/pxrd/cubic_index.html) · [`cubic_prototype`](https://furuse.work/ops/drive/pxrd/cubic_prototype.html) · [`debye_ring_image`](https://furuse.work/ops/drive/pxrd/debye_ring_image.html) · [`detector_calibrate`](https://furuse.work/ops/drive/pxrd/detector_calibrate.html) · [`detector_two_theta`](https://furuse.work/ops/drive/pxrd/detector_two_theta.html) · [`difference`](https://furuse.work/ops/2d/nary/difference.html) · [`diffraction_peaks`](https://furuse.work/ops/drive/pxrd/diffraction_peaks.html) · [`grid_lines`](https://furuse.work/ops/annotate/plot/grid_lines.html) · [`intensity`](https://furuse.work/ops/2d/features/intensity.html) · [`legend_box`](https://furuse.work/ops/annotate/furniture/legend_box.html) · [`nice_ticks`](https://furuse.work/ops/annotate/plot/nice_ticks.html) · [`phase_dictionary`](https://furuse.work/ops/drive/pxrd/phase_dictionary.html) · [`phase_fractions`](https://furuse.work/ops/drive/pxrd/phase_fractions.html) · [`phase_peel`](https://furuse.work/ops/drive/pxrd/phase_peel.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`powder_reflections`](https://furuse.work/ops/drive/pxrd/powder_reflections.html) · [`scherrer_size`](https://furuse.work/ops/drive/pxrd/scherrer_size.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html) · [`unexplained_peaks`](https://furuse.work/ops/drive/pxrd/unexplained_peaks.html)

## No.2026.221 —— 黒光沢とガラスの形を偏光で測る ―― 陰影が無くても、偏光は傾きを覚えている

[![黒光沢とガラスの形を偏光で測る ―― 陰影が無くても、偏光は傾きを覚えている](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_shape_from_polarization/05_normals_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_shape_from_polarization/05_normals.png)

*↑ **黒光沢とガラスの形を偏光で測る ―― 陰影が無くても、偏光は傾きを覚えている** ―― 黒光沢樹脂のドーム(n 1.57)とガラスのレンズ(n 1.52)を、4 方位のオンチップ偏光子を持つセンサの**生のモザイク 1 枚**から測る。真値は描画に使った解析的な法線と高さ。★★法線の誤差の中央値はドーム 0.53° / レンズ 1.09°、ドームの高さの RMS 誤差 0.62 px(高さ 37.9 px)。同じドームを 4 方向の照明の照度差ステレオにかけると光沢の点しか写らず中央値 26.4°(50 倍、7,921 画素中 2,408 画素は法線を返せない)。★★曖昧さは隠さない: 解消する前は全画素に法線 4 本(Brewster を挟む天頂角 2 × π の方位 2)、2 つの天頂角の差は Brewster 角 57.5° の上で 0 に縮む。凸 + Brewster の稜線で 1 本を選ぶ。★屈折率は較正球の DoLP に Fresnel の曲線を当てはめて 1.5691(真値 1.57)、DoLP 最大の位置から読む近道は 1.715 と雑音の山を拾う。★★どこで壊れるか: 屈折率を 1.50 と仮定すると 0.89°・1.40 で 2.21°(谷は真値でちょうど 0)、雑音の誤差は Brewster の輪(1.27°)と頂点(4.87°)に集まり中腹は 0.57°、拡散が 30 % 混ざると平均 7.4°(偏光が 90° ずれて打ち消し合う)。裏面反射・相互反射・消光比は入っていない合成であることは docstring に明記。検査 11 件・約 2 秒。*

[![鏡面の DoLP は Brewster 角でちょうど 1 になり、その両側に同じ値が 2 回出る。拡散は単調だが弱い(最大 (n²−1)/(n²+1))。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_shape_from_polarization/01_fresnel_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_shape_from_polarization/01_fresnel.png)

*↑ 測定の図 ―― 鏡面の DoLP は Brewster 角でちょうど 1 になり、その両側に同じ値が 2 回出る。拡散は単調だが弱い(最大 (n²−1)/(n²+1))。*

[![左 = 黒光沢樹脂のドーム(n = 1.57)、右 = ガラスのレンズ(n = 1.52)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_shape_from_polarization/02_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_shape_from_polarization/02_scene.png)

*↑ 左 = 黒光沢樹脂のドーム(n = 1.57)、右 = ガラスのレンズ(n = 1.52)。*

[![鏡面の DoLP は Brewster を挟んで 2 つの天頂角を持ち、方位は偏光子にとって π が同じ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_shape_from_polarization/04_candidates_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_shape_from_polarization/04_candidates.png)

*↑ 鏡面の DoLP は Brewster を挟んで 2 つの天頂角を持ち、方位は偏光子にとって π が同じ。*

[![屈折率の誤りは全体を滑らかにずらす。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_shape_from_polarization/07_failures_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_shape_from_polarization/07_failures.png)

*↑ 屈折率の誤りは全体を滑らかにずらす。*

[![較正球で測れば 0.01 以内に入る([4))。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_shape_from_polarization/09_index_and_mixing_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_shape_from_polarization/09_index_and_mixing.png)

*↑ 較正球で測れば 0.01 以内に入る([4])。*

[![検光子を 0〜180° 回したときの明るさ。黒い蝶ネクタイが回る —— 暗くなる向きが、その画素の面の傾きの向き(鏡面では入射面に直交)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_shape_from_polarization/03_analyser.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_shape_from_polarization/03_analyser.gif)

*↑ 動く図 ―― 検光子を 0〜180° 回したときの明るさ。黒い蝶ネクタイが回る —— 暗くなる向きが、その画素の面の傾きの向き(鏡面では入射面に直交)。*

```
py -3.11 examples/poc_shape_from_polarization.py
```

ソース: [examples/poc_shape_from_polarization.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_shape_from_polarization.py)

この回が作った図は全部で **10 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_shape_from_polarization)

使用 op(ノートへ): [`aolp_to_azimuth`](https://furuse.work/ops/optics/shape_from_polarization/aolp_to_azimuth.html) · [`brdf_blinn_phong`](https://furuse.work/ops/specular/reflectance/brdf_blinn_phong.html) · [`dolp_to_zenith`](https://furuse.work/ops/optics/shape_from_polarization/dolp_to_zenith.html) · [`fresnel_dielectric`](https://furuse.work/ops/optics/interface/fresnel_dielectric.html) · [`photometric_stereo_robust`](https://furuse.work/ops/specular/photometric/photometric_stereo_robust.html) · [`polarization_demosaic`](https://furuse.work/ops/optics/polarization/polarization_demosaic.html) · [`sfp_disambiguate`](https://furuse.work/ops/optics/shape_from_polarization/sfp_disambiguate.html) · [`sfp_dolp_model`](https://furuse.work/ops/optics/shape_from_polarization/sfp_dolp_model.html) · [`sfp_estimate_index`](https://furuse.work/ops/optics/shape_from_polarization/sfp_estimate_index.html) · [`sfp_height`](https://furuse.work/ops/optics/shape_from_polarization/sfp_height.html) · [`sfp_normals`](https://furuse.work/ops/optics/shape_from_polarization/sfp_normals.html) · [`sfp_render`](https://furuse.work/ops/optics/shape_from_polarization/sfp_render.html)

## No.2026.185 —— 金属積層造形の熱画像から X 線 CT へ ―― 生信号を温度と呼ばない、時間軸と画素ピッチ、下向き面だけに付く粉

[![金属積層造形の熱画像から X 線 CT へ ―― 生信号を温度と呼ばない、時間軸と画素ピッチ、下向き面だけに付く粉](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_am_thermal_to_ct/01_melt_pool_frames.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_am_thermal_to_ct/01_melt_pool_frames.gif)

*↑ **金属積層造形の熱画像から X 線 CT へ ―― 生信号を温度と呼ばない、時間軸と画素ピッチ、下向き面だけに付く粉** ―― 金属積層造形(レーザ粉末床溶融、In718)の工程中の熱画像と、造形後の X 線 CT を Fullseye の既存 op でつなぐ。実データは米国国立標準技術研究所(NIST)の公開データ(熱画像 doi:10.18434/mds2-2716、X 線 CT doi:10.18434/mds2-2291 は Georgia Institute of Technology で測定)を 2026-10-02 に部分抽出し、しきい値処理・切り出し・疑似カラー化した(改変、NIST は AS IS で提供、https://www.nist.gov/open/license)。データは配布物に含めず、無ければ真値つきの合成で同じ門を走らせる。門: 生信号(DL)を温度と呼ばない —— 変換は放射率 ε を必須の引数にし、同じ飽和 4095 DL が ε=1 で 1401 ℃・ε=0.3 で 1641 ℃(差 239 K)、飽和は下限、0 は測定なし(式に通すと −204 ℃ に張り付く)/ 走査指令の laser-on 24 本 = 熱画像のバースト 24 本、周期は +2.3 % ずれる(原因は未解決として記録、合成では注入した 2.3 % を +2.31 % で読む) / 画素ピッチは走査速度から逆算して 21.31 µm(条件間で最大 0.20 %)/ 溶融池の長さは条件間のばらつきが反復内の 15 倍 / CT は設計 STL の断面と Dice 0.981、表面のはみ出しは下向き面(穴の天井)63 µm > 上向き 32 µm —— 付着粉が下向き面にだけ垂れる / 内部の空隙 0 個(検出下限 約 63 µm、閉じた空気 7 個はすべて表面から 0.02 mm 以内の付着粉)。正直に: 校正式は属性の文字列を推定して読んだ、液相線 1336 ℃ は仮定、CT のボクセル寸法は設計寸法からの逆算、時間軸の 2.3 % のずれは未解決。*

[![calibration T = 14388/(a ln(c eps/x + 1)) - b/a (reading of the file's model string is our assumption). 4095 DL = 1402 C](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_am_thermal_to_ct/02_dl_to_celsius_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_am_thermal_to_ct/02_dl_to_celsius.png)

*↑ 測定の図 ―― calibration T = 14388/(a ln(c eps/x + 1)) - b/a (reading of the file's model string is our assumption). 4095 DL = 1402 C at eps=1, 1641 C at eps=0.3. Pixels >= 2759 DL are above the liquidus for any eps <= 1. Source: National Institute of Standards and Technology (NIST), doi:10.18434/mds2-2716 (thermography) and doi:10.18434/mds2-2291 (XCT, measured at Georgia Tech); subsets extracted 2026-10-02, thresholded/cropped/false-coloured here (modified). Provided AS IS, https://www.nist.gov/open/license*

[![Line_0_1, row 300: 19 saturated frames are only a lower bound; the curve stops at frame 189 where th](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_am_thermal_to_ct/03_cooling_curve_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_am_thermal_to_ct/03_cooling_curve.png)

*↑ Line_0_1, row 300: 19 saturated frames are only a lower bound; the curve stops at frame 189 where the camera reports 0 (below 100 DL) instead of falli…*

[![Y pad: the command (XYPT, no time step stored) and the staring camera agree on the count and on the ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_am_thermal_to_ct/04_time_axis_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_am_thermal_to_ct/04_time_axis.png)

*↑ Y pad: the command (XYPT, no time step stored) and the staring camera agree on the count and on the long last interval, yet drift apart by 2.3 % per p…*

[![slice at z = 4.00 mm just below the crown of the 4 mm hole: particles hang into the hole from the do](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_am_thermal_to_ct/07_ct_hole_crown_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_am_thermal_to_ct/07_ct_hole_crown.png)

*↑ slice at z = 4.00 mm just below the crown of the 4 mm hole: particles hang into the hole from the down-facing surface; red = design.*

[![XCT vs STL: protrusion = p95 of the signed distance (outward positive) after subtracting the median ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_am_thermal_to_ct/08_protrusion_by_facing_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_am_thermal_to_ct/08_protrusion_by_facing.png)

*↑ XCT vs STL: protrusion = p95 of the signed distance (outward positive) after subtracting the median of each 0.25 mm surface cell (form error); line =…*

[![XCT slices 121..320 (z = 1.75..4.16 mm, build direction) with the STL cross-section in red. Note the powder/dross hangin](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_am_thermal_to_ct/06_ct_slices.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_am_thermal_to_ct/06_ct_slices.gif)

*↑ 動く図 ―― XCT slices 121..320 (z = 1.75..4.16 mm, build direction) with the STL cross-section in red. Note the powder/dross hanging under the hole crown and the 45 deg notch. Source: National Institute of Standards and Technology (NIST), doi:10.18434/mds2-2716 (thermography) and doi:10.18434/mds2-2291 (XCT, measured at Georgia Tech); subsets extracted 2026-10-02, thresholded/cropped/false-coloured here (modified). Provided AS IS, https://www.nist.gov/open/license*

```
py -3.11 examples/poc_am_thermal_to_ct.py
```

ソース: [examples/poc_am_thermal_to_ct.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_am_thermal_to_ct.py)

この回が作った図は全部で **9 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_am_thermal_to_ct)

使用 op(ノートへ): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_select_largest`](https://furuse.work/ops/blob/select/blob_select_largest.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`mesh_slice_stack`](https://furuse.work/ops/printpath/slice/mesh_slice_stack.html) · [`seg_boundary_f`](https://furuse.work/ops/segmentation/score/seg_boundary_f.html) · [`seg_dice_jaccard`](https://furuse.work/ops/segmentation/score/seg_dice_jaccard.html) · [`signed_surface_distance`](https://furuse.work/ops/shapestat/deviation/signed_surface_distance.html) · [`sk_otsu`](https://furuse.work/ops/2d/segmentation/sk_otsu.html) · [`vol_boundary_points`](https://furuse.work/ops/3d/boundary/vol_boundary_points.html) · [`vol_gaussian`](https://furuse.work/ops/2d/3d/vol_gaussian.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_region_props`](https://furuse.work/ops/3d/regionprops/vol_region_props.html)

## No.2026.225 —— SEM の明るい縁が寸法をどれだけ太らせるか ―― 形は合うのに面積が太る

[![SEM の明るい縁が寸法をどれだけ太らせるか ―― 形は合うのに面積が太る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_wafer_defect_edge_bias/01_sem_se_bse_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_wafer_defect_edge_bias/01_sem_se_bse_bias.png)

*↑ **SEM の明るい縁が寸法をどれだけ太らせるか ―― 形は合うのに面積が太る** ―― 主図は同じ欠陥の二次電子像と反射電子像に真値輪郭・検出輪郭・縁偏りを重ねる。線量10倍でSNRは3.16倍になり、縁の面積偏りは小欠陥ほど大きい。*

[![0.5 nm/pixel で再計算した 256 nm 視野。明帯幅は PSF とともに増える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_wafer_defect_edge_bias/02_sem_edge_rim_zoom_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_wafer_defect_edge_bias/02_sem_edge_rim_zoom.png)

*↑ 測定の図 ―― 0.5 nm/pixel で再計算した 256 nm 視野。明帯幅は PSF とともに増える。*

[![低照射量ほど粒状のショット雑音が増える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_wafer_defect_edge_bias/03_sem_dose_series_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_wafer_defect_edge_bias/03_sem_dose_series.png)

*↑ 低照射量ほど粒状のショット雑音が増える。*

[![合成 SEM 像(半径 22 px の円錐欠陥、PSF σ=3)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_wafer_defect_edge_bias/04_sem_edge_inflation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_wafer_defect_edge_bias/04_sem_edge_inflation.png)

*↑ 合成 SEM 像(半径 22 px の円錐欠陥、PSF σ=3)。*

[![面積の太りは小さい欠陥ほど大きい(周囲長/面積 ∝ 1/R)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_wafer_defect_edge_bias/05_sem_area_bias_vs_size_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_wafer_defect_edge_bias/05_sem_area_bias_vs_size.png)

*↑ 面積の太りは小さい欠陥ほど大きい(周囲長/面積 ∝ 1/R)。*

```
py -3.11 examples/poc_sem_wafer_defect_edge_bias.py
```

ソース: [examples/poc_sem_wafer_defect_edge_bias.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_sem_wafer_defect_edge_bias.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_sem_wafer_defect_edge_bias)

使用 op(ノートへ): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`pod_hitmiss_fit`](https://furuse.work/ops/spc/pod/pod_hitmiss_fit.html) · [`seg_boundary_f`](https://furuse.work/ops/segmentation/score/seg_boundary_f.html) · [`seg_dice_jaccard`](https://furuse.work/ops/segmentation/score/seg_dice_jaccard.html) · [`sem_image`](https://furuse.work/ops/generative/sem/sem_image.html) · [`sem_render`](https://furuse.work/ops/generative/sem/sem_render.html)

## No.2026.228 —— 重力波望遠鏡の擬似シミュレーション ―― 共振器の式・量子雑音の予算・整合フィルタを閉形式で繋ぎ、GW150914 の実データで採点

[![重力波望遠鏡の擬似シミュレーション ―― 共振器の式・量子雑音の予算・整合フィルタを閉形式で繋ぎ、GW150914 の実データで採点](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gw_detector_pseudo_simulation/05_gw150914_whitened_vs_prl_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gw_detector_pseudo_simulation/05_gw150914_whitened_vs_prl.png)

*↑ **重力波望遠鏡の擬似シミュレーション ―― 共振器の式・量子雑音の予算・整合フィルタを閉形式で繋ぎ、GW150914 の実データで採点** ―― km 級の Michelson 干渉計が 1e-21 のひずみを読む仕組みを閉じた式で再現し、GW150914 の実データ(GWOSC)と公表値で採点する。新 op 12 本: 腕共振器(`fabry_perot_response` は aLIGO の公表設計値でフィネス 445・極 42 Hz、`cavity_strain_transfer`、`michelson_dc_readout`、`pdh_error_signal` は Black 2001 の傾きと 0.9999 倍)、量子雑音の予算(`quantum_noise_budget`、散射 × 輻射圧 = SQL²/2 の恒等式、第二実装 gwinc 0.6.2 と 8 周波数で比 0.96〜1.12)、信号側(`psd_welch` → `whiten_by_psd` → `matched_filter_snr` / `optimal_snr`、`chirp_newtonian`、`chirp_mass_from_track`、`coincidence_delay`)。実データでは白色化 + 35〜350 Hz が PRL 116, 061102 図 1 の公表曲線と相関 0.959 / 0.935、数値相対論の波形の整合フィルタで SNR H1 19.0 / L1 13.1(公表 ≈ 20 / 13)、ネットワーク 23.1(公表 24)、L1 が 7.1 ms 先(公表 6.9 ms)。ニュートン近似のチャープは 9.1 / 5.6(合体・リングダウンが無い分だけ損)。設計曲線(T1800044)との比は 20 Hz 0.42・100 Hz 1.99・1 kHz 0.33 で、信号再利用と熱雑音の分だけ形が違うことを表で明示。持ち帰りは 1/f² の色つき雑音の中の既知波形: 白色化した整合フィルタは埋めた高さどおり、素の相関はトーンで 0.98・チャープで 0.50・減衰振動で 0.37。実データは環境変数に置けば走り、無ければ「未配置」と明示。学習 0、較正 0。*

[![単極 1/√(1+(f/f_p)²) × 往復伝搬の sinc(2πfL/c)。極で 1/√2、FSR = c/2L で零。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gw_detector_pseudo_simulation/01_cavity_transfer_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gw_detector_pseudo_simulation/01_cavity_transfer.png)

*↑ 測定の図 ―― 単極 1/√(1+(f/f_p)²) × 往復伝搬の sinc(2πfL/c)。極で 1/√2、FSR = c/2L で零。*

[![反対称で共振で零。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gw_detector_pseudo_simulation/02_pdh_error_signal_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gw_detector_pseudo_simulation/02_pdh_error_signal.png)

*↑ 反対称で共振で零。*

[![通常干渉計(信号再利用なし)の量子雑音。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gw_detector_pseudo_simulation/03_quantum_noise_budget_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gw_detector_pseudo_simulation/03_quantum_noise_budget.png)

*↑ 通常干渉計(信号再利用なし)の量子雑音。*

[![数値相対論の波形は公表どおりの山を立て、ニュートン近似(合体・リングダウン無し)は半分以下。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gw_detector_pseudo_simulation/06_matched_filter_snr_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gw_detector_pseudo_simulation/06_matched_filter_snr.png)

*↑ 数値相対論の波形は公表どおりの山を立て、ニュートン近似(合体・リングダウン無し)は半分以下。*

[![雑音が 1/f² のとき、波形が低周波を含むほど素の相関は損をし、白色化した整合フィルタは最適 SNR どおりに拾う。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gw_detector_pseudo_simulation/07_burst_in_coloured_noise_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gw_detector_pseudo_simulation/07_burst_in_coloured_noise.png)

*↑ 雑音が 1/f² のとき、波形が低周波を含むほど素の相関は損をし、白色化した整合フィルタは最適 SNR どおりに拾う。*

[![入射光量 100 W → 100 kW: 散射雑音は 1/√P で下がり、輻射圧雑音は √P で上がる。総和は K = 1 の周波数で SQL に触れ、その点が光量とともに高い周波数へ動く。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gw_detector_pseudo_simulation/04_power_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gw_detector_pseudo_simulation/04_power_sweep.gif)

*↑ 動く図 ―― 入射光量 100 W → 100 kW: 散射雑音は 1/√P で下がり、輻射圧雑音は √P で上がる。総和は K = 1 の周波数で SQL に触れ、その点が光量とともに高い周波数へ動く。*

```
FULLSEYE_GWOSC_DATA=<dir> py -3.11 examples/poc_gw_detector_pseudo_simulation.py
```

ソース: [examples/poc_gw_detector_pseudo_simulation.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_gw_detector_pseudo_simulation.py)

この回が作った図は全部で **7 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_gw_detector_pseudo_simulation)

使用 op(ノートへ): [`bandpass`](https://furuse.work/ops/oned/signal/bandpass.html) · [`cavity_strain_transfer`](https://furuse.work/ops/optics/cavity/cavity_strain_transfer.html) · [`chirp_mass_from_track`](https://furuse.work/ops/oned/matched/chirp_mass_from_track.html) · [`chirp_newtonian`](https://furuse.work/ops/oned/matched/chirp_newtonian.html) · [`coincidence_delay`](https://furuse.work/ops/oned/matched/coincidence_delay.html) · [`fabry_perot_response`](https://furuse.work/ops/optics/cavity/fabry_perot_response.html) · [`matched_filter_snr`](https://furuse.work/ops/oned/matched/matched_filter_snr.html) · [`michelson_dc_readout`](https://furuse.work/ops/optics/cavity/michelson_dc_readout.html) · [`optimal_snr`](https://furuse.work/ops/oned/matched/optimal_snr.html) · [`pdh_error_signal`](https://furuse.work/ops/optics/cavity/pdh_error_signal.html) · [`psd_welch`](https://furuse.work/ops/oned/matched/psd_welch.html) · [`quantum_noise_budget`](https://furuse.work/ops/optics/cavity/quantum_noise_budget.html) · [`spectrogram`](https://furuse.work/ops/oned/signal/spectrogram.html) · [`whiten_by_psd`](https://furuse.work/ops/oned/matched/whiten_by_psd.html)

## No.2026.234 —— 写真では見えない µm の凹みを、画面に映した縞の鏡像で見つける ―― 位相計測デフレクトメトリ

[![写真では見えない µm の凹みを、画面に映した縞の鏡像で見つける ―― 位相計測デフレクトメトリ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/03_photo_vs_pmd_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/03_photo_vs_pmd.png)

*↑ **写真では見えない µm の凹みを、画面に映した縞の鏡像で見つける ―― 位相計測デフレクトメトリ** ―― 光沢面(車の塗装パネル、カバーガラス)の深さ数 µm の凹みは、照明を当てた写真ではまず見えない —— 鏡は照明しか写さない。面の前の画面に位相シフト縞を出し、その鏡像を撮ると、面が 1e-3 rad 傾くだけで 30 cm 先の画面では 0.6 mm ずれる。新 op 6 本(`deflectometry`、`opsspecular` の `deflectometry`): `deflectometry_rig` / `deflectometry_screen_pattern` / `deflectometry_render`(高さ場 → 縞の鏡像。拡散成分、散乱、ガラスの裏面反射、開口積分のピント、雑音)/ `deflectometry_phase_to_slope`(絶対位相 → 法線、`match3d.normal_from_reflection`)/ `slope_to_curvature`(積分せず 1 回微分)/ `deflectometry_sensitivity`(撮る前の閉形式)。深さ 3 µm と 1 µm の凹み・うねり 0.8 µm・研磨ムラ 0.12 µm を仕込んだ塗装パネルで、ソフトボックスの写真の欠陥の信号は最大 0.00066(8 bit の 1 段の 0.17 倍)なのに、曲率マップの SNR は 110 と 57。勾配を積分した凹みの深さは真値と 0.5 % 以内。位相の雑音は閉形式 √(2/N)·σ/b と 1.00 倍、面の傾きの雑音は σ_u/(2d) の 0.67 倍(双線形の読み直しの √(4/9) どおり)。壊れるところ: 部品を 0.3 mm 浮かせると見かけの傾き Δz·sin θ/d(0.1 % で一致)と半径 388 m の椀が出るが凹みの深さは 0.7 % しか変わらない / 画面の距離を 2 % 間違えると深さが 2.3 % 浅い / 拡散成分 0.85 までは 1 µm の凹みが見え、0.9 で粗い縞の次数が飛び始める / 無反射コートの無いカバーガラスでは裏面の光が凹みの斜面(くさび)で逆向きに曲がり、傾きの感度が閉形式 0.246 に縮んで凹みが 1/4 の深さに見える(実測 0.246)/ 開口 8 mm では面にピントで縞の振幅が 0.60 倍、画面にピントで凹みが 0.52 倍の深さ。学習 0、較正 0、門 22 件。*

[![面の前の画面(520 × 320 mm)にこの 4 枚を順に出し、面に映った鏡像を撮る。縦縞は画面の u(入射面内)を、同じ 4 枚を横縞にしたものが v を符号化する。粗い縞(周期 160 mm)の 4 枚で次数を決める。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/01_screen_patterns_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/01_screen_patterns.png)

*↑ 測定の図 ―― 面の前の画面(520 × 320 mm)にこの 4 枚を順に出し、面に映った鏡像を撮る。縦縞は画面の u(入射面内)を、同じ 4 枚を横縞にしたものが v を符号化する。粗い縞(周期 160 mm)の 4 枚で次数を決める。*

[![左が真値の高さ(視野 40 mm、青 = 高い・橙 = 低い)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/02_sample_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/02_sample.png)

*↑ 左が真値の高さ(視野 40 mm、青 = 高い・橙 = 低い)。*

[![真値(破線)と復元(実線)はほぼ重なるので、差を 10 倍にして点線で重ねた。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/05_dimple_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/05_dimple_profile.png)

*↑ 真値(破線)と復元(実線)はほぼ重なるので、差を 10 倍にして点線で重ねた。*

[![平らな板を 0.3 mm 浮かせただけで、測った高さは 40 mm で約 14 µm 傾く(左、視野の中心で 3.4e-4 rad)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/08_ambiguity_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/08_ambiguity_map.png)

*↑ 平らな板を 0.3 mm 浮かせただけで、測った高さは 40 mm で約 14 µm 傾く(左、視野の中心で 3.4e-4 rad)。*

[![表と裏の反射率はほぼ同じ(R1 0.043、R2 0.039)なので、2 つの縞の和の位相は上限 1.16 rad までずれ得る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/12_glass_back_reflection_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/12_glass_back_reflection.png)

*↑ 表と裏の反射率はほぼ同じ(R1 0.043、R2 0.039)なので、2 つの縞の和の位相は上限 1.16 rad までずれ得る。*

[![拡散成分 k_d = 0, 0.5, 0.8, 0.85, 0.9, 0.95, 0.98, 0.99, 0.995 と上げていったときの平均曲率(±2.5e-3 /mm)。雑音が 1/(1 − k_d) で増え、浅い凹み B が先に沈み、](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/09_diffuse_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/09_diffuse_sweep.gif)

*↑ 動く図 ―― 拡散成分 k_d = 0, 0.5, 0.8, 0.85, 0.9, 0.95, 0.98, 0.99, 0.995 と上げていったときの平均曲率(±2.5e-3 /mm)。雑音が 1/(1 − k_d) で増え、浅い凹み B が先に沈み、最後は粗い縞の次数が飛ぶ。*

```
py -3.11 examples/poc_phase_measuring_deflectometry.py
```

ソース: [examples/poc_phase_measuring_deflectometry.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_phase_measuring_deflectometry.py)

この回が作った図は全部で **14 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry)

使用 op(ノートへ): [`absolute_phase`](https://furuse.work/ops/3d/structured_light/absolute_phase.html) · [`deflectometry_phase_to_slope`](https://furuse.work/ops/specular/deflectometry/deflectometry_phase_to_slope.html) · [`deflectometry_render`](https://furuse.work/ops/specular/deflectometry/deflectometry_render.html) · [`deflectometry_rig`](https://furuse.work/ops/specular/deflectometry/deflectometry_rig.html) · [`deflectometry_screen_pattern`](https://furuse.work/ops/specular/deflectometry/deflectometry_screen_pattern.html) · [`deflectometry_sensitivity`](https://furuse.work/ops/specular/deflectometry/deflectometry_sensitivity.html) · [`fresnel_dielectric`](https://furuse.work/ops/optics/interface/fresnel_dielectric.html) · [`integrate`](https://furuse.work/ops/3d/tsdf_fusion/integrate.html) · [`sfp_height`](https://furuse.work/ops/optics/shape_from_polarization/sfp_height.html) · [`slope_to_curvature`](https://furuse.work/ops/specular/deflectometry/slope_to_curvature.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`wrapped_phase`](https://furuse.work/ops/3d/structured_light/wrapped_phase.html)

## No.2026.235 —— TDI ラインスキャンとラインスキャン用レンズ ―― 段数で欠陥が見え、同期がずれると流れ、C マウントでは長いセンサの端が消える

[![TDI ラインスキャンとラインスキャン用レンズ ―― 段数で欠陥が見え、同期がずれると流れ、C マウントでは長いセンサの端が消える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tdi_linescan/01_tdi_stages_defects_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tdi_linescan/01_tdi_stages_defects.png)

*↑ **TDI ラインスキャンとラインスキャン用レンズ ―― 段数で欠陥が見え、同期がずれると流れ、C マウントでは長いセンサの端が消える** ―― フィルム・鋼板・ウェハのように流れてくるものはラインセンサで撮り、暗いラインでは TDI で N 段ぶん露光を積む。新 op 6 本(`linescan`、`opsoptics` の `linescan`): `tdi_snr`(EMVA 1288 の式 21 を段数倍、電荷加算 / デジタル加算)/ `tdi_sync_mtf`(同期ずれ・ヨーの閉形式)/ `linescan_acquire`(反射率の地図を搬送して撮る: 速度誤差・ヨー・蛇行・エンコーダ同期・レンズ・雑音)/ `lens_field_profile`(像高ごとの照度と MTF を光線追跡で)/ `linescan_lens_columns` / `linescan_lens_example`。★1 段 40 光子の暗い冷延鋼板で、2 枚撮りの時間雑音から測った SNR は式 21 と全段数で 1.2 % 以内。デジタル加算は 64 段で ×8.09(√64 = 8)、電荷加算は読み出し雑音を 1 回しか払わないので ×26.9。薄い傷・ピンホール・異物の検出は 1 段 0 / 3 → 64 段 3 / 3(誤検出 0)。★同期ずれ ε で像が N·ε 画素流れ、流れ方向の MTF は |sinc(f N ε)| —— 閉形式を先に印字し、正弦波の板で 45 条件の最大差 0.0035。速度のうねり ±3 % は自走で局所 MTF 0.64 まで落ち、エンコーダ同期で 1.000 に戻る。ヨーの幅方向のぼけ |sinc(f N sin θ)| はエンコーダでは直らない(9 条件で最大差 0.0017)。★同じ形の三枚玉を 57 mm の像円用(f 90)と 2/3 型用(f 35、C マウントの流用)に作って光線追跡: 照度は cos⁴ × 瞳 × 歪曲に厳密に分かれ(最大差 2e-16)、ラインスキャン用は端で 0.976(cos⁴ は 0.855、樽型歪曲 −2.9 % が ×1.111)、C マウントは像高 19.7 mm から光が届かない。フラットフィールド補正で照度の幅は 0.961 → 1.000 に揃うが、正弦波の変調は補正の前後で差 0.0006(MTF は直らない)、像高 14 mm の異物の CNR は C マウントで 1.52 → 1.54 のまま(ラインスキャン用 2.49)。学習 0、較正 0、門 19 件。*

[![EMVA 1288 の 2 枚撮り(時間雑音)で測った SNR と、式 21 を段数倍した閉形式。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tdi_linescan/02_snr_vs_stages_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tdi_linescan/02_snr_vs_stages.png)

*↑ 測定の図 ―― EMVA 1288 の 2 枚撮り(時間雑音)で測った SNR と、式 21 を段数倍した閉形式。*

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

ソース: [examples/poc_tdi_linescan.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_tdi_linescan.py)

この回が作った図は全部で **10 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_tdi_linescan)

使用 op(ノートへ): [`emva_pair_statistics`](https://furuse.work/ops/optics/sensorchar/emva_pair_statistics.html) · [`lens_field_profile`](https://furuse.work/ops/optics/linescan/lens_field_profile.html) · [`lens_shading_correct`](https://furuse.work/ops/gfx2d/isp/lens_shading_correct.html) · [`lens_shading_gain`](https://furuse.work/ops/gfx2d/isp/lens_shading_gain.html) · [`lens_system`](https://furuse.work/ops/optics/design/lens_system.html) · [`linescan_acquire`](https://furuse.work/ops/optics/linescan/linescan_acquire.html) · [`linescan_lens_columns`](https://furuse.work/ops/optics/linescan/linescan_lens_columns.html) · [`linescan_lens_example`](https://furuse.work/ops/optics/linescan/linescan_lens_example.html) · [`paraxial_trace`](https://furuse.work/ops/optics/design/paraxial_trace.html) · [`relative_illumination`](https://furuse.work/ops/optics/geometric/relative_illumination.html) · [`tdi_snr`](https://furuse.work/ops/optics/linescan/tdi_snr.html) · [`tdi_sync_mtf`](https://furuse.work/ops/optics/linescan/tdi_sync_mtf.html)

## No.2026.236 —— ピクセルシフト撮像 ―― センサを 1 画素動かすと偽色が消え、半画素動かすと折り返しが消える。MTF は上がらない

[![ピクセルシフト撮像 ―― センサを 1 画素動かすと偽色が消え、半画素動かすと折り返しが消える。MTF は上がらない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pixel_shift/14_real_chart_zoom_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pixel_shift/14_real_chart_zoom.png)

*↑ **ピクセルシフト撮像 ―― センサを 1 画素動かすと偽色が消え、半画素動かすと折り返しが消える。MTF は上がらない** ―― 撮像素子を圧電アクチュエータで 1 画素 / 半画素ずつ動かして撮る「ピクセルシフト」が、外観検査で何を増やし何を増やさないか。主役は実データ: 35 mm フルサイズのミラーレス(センサシフト機)で撮ったピクセルシフト 4 枚の未加工 RAW(PixelShift200、Qian ほか ICCP 2022、CC BY 4.0)で解像チャートを測る。★実機の巡り方は (0,0)→(1,0)→(1,−1)→(0,−1) で、op の既定の並びのまま渡すと止まった被写体の 23.2 % が「動いた」になる(正しい並びで 0.09 %)。合わせた像は著者の合成済み RGGB と相関 0.99999996。無彩色のチャートの色は 1 枚 + 双線形 0.054 → 4 枚 0.025、0.25 cyc/px より細かい縞の振幅は 4 枚が 1.67 倍。★よいデモザイク(rawpy の AHD)は振幅 1.01 倍・色 0.020 で 4 枚とほぼ同じ —— チャートの縞は 0.31 cyc/px 止まりで、4 枚の得はナイキストに近い細部で出る。以下は合成のシーンで壊れる条件を掃引する補助の章。新 op 6 本(`pixelshift`、`opsoptics` の `pixelshift`): `pixel_shift_pattern` / `pixel_shift_capture`(画素の開口の箱で厳密に積分、Bayer か白黒)/ `pixel_shift_merge`(公称のシフトで格子へ、埋められないシフト列は拒否)/ `pixel_shift_motion_mask` / `false_color_metric` / `pixel_shift_resolution_budget`(sinc × 回折 MTF、Q = λN/p)。1 画素シフト 4 枚は基板の配線・織物・網点・解像チャートで偽色を 0.043〜0.084 から 0 にする(静止・誤差 0 では定義上 0 —— 各画素の R・G・B が同じ開口で同じ点を見る)。半画素シフトでは 0.6〜0.9 cyc/px の縞の FFT の山が、1 枚の折り返し 1 − f₀ から本当の f₀ へ戻り、高さは 0.4·sinc(f₀) と 2e-14 で一致。★傾いたエッジの MTF50 は 1 枚 0.478・半画素 0.475・閉形式 0.467 cyc/px —— シフトで変わるのは折り返しで MTF ではない。drizzle(独立の実装)でも山は 0.700 に立ち、★センサのシフトをそのまま渡すと 0.300(符号の取り違えが折り返しに化ける)。画素 3.45 µm で F 1.4〜22 を振ると 0.7 cyc/px の変調は sinc·回折の閉形式と 0.0008 以内、Q > 1.43 で消え、解像の得は Q = 2 より手前の Q* = 1.47 で尽きる。開口率 0.5 なら 0.8 cyc/px の変調が 3.2 倍。壊れる条件: 1 枚だけ 0.05 px ずれた色の誤差は閉形式 2πf·a·sinc·δ/√2 と 1.2 %、乱数の誤差 σ = 0.1 px で偽色 0.012(1 枚のデモザイク 0.053)。搬送中の部品は 0.25 px/枚 までは 4 枚の破綻(0.161)が 1 枚のデモザイク(0.205)より小さく、0.5 px/枚 から逆転。動き検出で 1 枚に差し戻すと 1 枚の画質の天井に届き、静止部の誤検出 0 %。雑音は R・B が σ/√c、G が σ/√(2c) と 2.1 % 以内、動く縞では枚数を増やすほど誤差が増える(4 → 16 枚で 0.081 → 0.273)。学習 0、較正 0、門 34 件。*

[![基板の配線・織物・網点・解像チャート(上から)。左 = 3 色を各画素で取る理想センサ、中 = Bayer 1 枚 + 双線形デモザイク、右 = 1 画素シフト 4 枚。44 × 44 画素を最近傍で 5 倍。静止・誤差 0 では 4 枚の](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pixel_shift/01_four_shot_false_color_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pixel_shift/01_four_shot_false_color.png)

*↑ 測定の図 ―― 基板の配線・織物・網点・解像チャート(上から)。左 = 3 色を各画素で取る理想センサ、中 = Bayer 1 枚 + 双線形デモザイク、右 = 1 画素シフト 4 枚。44 × 44 画素を最近傍で 5 倍。静止・誤差 0 では 4 枚の偽色は定義上 0(4・5 章が壊れる条件)。*

[![解像チャートの 星形チャート(48 × 48 画素を 6 倍)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pixel_shift/02_star_split_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pixel_shift/02_star_split.png)

*↑ 解像チャートの 星形チャート(48 × 48 画素を 6 倍)。*

[![左は画素 1 つ = 8 × 8、右は出力画素 1 つ(= ½ センサ画素)= 4 × 4 で表示。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pixel_shift/05_grating_crops_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pixel_shift/05_grating_crops.png)

*↑ 左は画素 1 つ = 8 × 8、右は出力画素 1 つ(= ½ センサ画素)= 4 × 4 で表示。*

[![画素 3.45 µm、λ 0.55 µm で F 1.4〜22。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pixel_shift/08_lens_vs_pixel_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pixel_shift/08_lens_vs_pixel.png)

*↑ 画素 3.45 µm、λ 0.55 µm で F 1.4〜22。*

[![4 枚のピクセルシフトは雑音を下げるためのものではない(R・B は 1 枚と同じ)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pixel_shift/11_noise_sqrt_n_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pixel_shift/11_noise_sqrt_n.png)

*↑ 4 枚のピクセルシフトは雑音を下げるためのものではない(R・B は 1 枚と同じ)。*

[![左 = その枚の Bayer の生の値(画素ごとにフィルタの色で表示、センサの位置へずらして描く)、右 = 合わせた格子に R・G・B が揃っていく様子。最後は 1 枚のデモザイクと 4 枚の合成(24 × 24 画素を 10 倍)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pixel_shift/12_four_shot_capture.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pixel_shift/12_four_shot_capture.gif)

*↑ 動く図 ―― 左 = その枚の Bayer の生の値(画素ごとにフィルタの色で表示、センサの位置へずらして描く)、右 = 合わせた格子に R・G・B が揃っていく様子。最後は 1 枚のデモザイクと 4 枚の合成(24 × 24 画素を 10 倍)。*

```
py -3.11 examples/poc_pixel_shift.py
```

ソース: [examples/poc_pixel_shift.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pixel_shift.py)

この回が作った図は全部で **15 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_pixel_shift)

使用 op(ノートへ): [`airy_pattern`](https://furuse.work/ops/optics/wave/airy_pattern.html) · [`annotate_figure_grid`](https://furuse.work/ops/annotate/paper/annotate_figure_grid.html) · [`drizzle_resample`](https://furuse.work/ops/astrostack/stack/drizzle_resample.html) · [`edge_spread`](https://furuse.work/ops/optics/imaging/edge_spread.html) · [`false_color_metric`](https://furuse.work/ops/optics/pixelshift/false_color_metric.html) · [`halftone_screen`](https://furuse.work/ops/printpath/npr/halftone_screen.html) · [`mtf50`](https://furuse.work/ops/optics/imaging/mtf50.html) · [`mtf_diffraction`](https://furuse.work/ops/optics/imaging/mtf_diffraction.html) · [`pixel_shift_capture`](https://furuse.work/ops/optics/pixelshift/pixel_shift_capture.html) · [`pixel_shift_merge`](https://furuse.work/ops/optics/pixelshift/pixel_shift_merge.html) · [`pixel_shift_motion_mask`](https://furuse.work/ops/optics/pixelshift/pixel_shift_motion_mask.html) · [`pixel_shift_pattern`](https://furuse.work/ops/optics/pixelshift/pixel_shift_pattern.html) · [`pixel_shift_resolution_budget`](https://furuse.work/ops/optics/pixelshift/pixel_shift_resolution_budget.html) · [`psnr`](https://furuse.work/ops/imgmetrics/fidelity/psnr.html) · [`raw_demosaic_bilinear`](https://furuse.work/ops/gfx2d/isp/raw_demosaic_bilinear.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`sfr_from_edge`](https://furuse.work/ops/optics/imaging/sfr_from_edge.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`weave_normals`](https://furuse.work/ops/optics/surface/weave_normals.html)

## No.2026.243 —— 間接 ToF の多周波アンラップ ―― 周波数を上げるほど細かく測れるが、折り返し・多重反射・縁の混合・高調波で壊れる

[![間接 ToF の多周波アンラップ ―― 周波数を上げるほど細かく測れるが、折り返し・多重反射・縁の混合・高調波で壊れる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_itof_multifreq/01_warehouse_unwrap_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_itof_multifreq/01_warehouse_unwrap.png)

*↑ **間接 ToF の多周波アンラップ ―― 周波数を上げるほど細かく測れるが、折り返し・多重反射・縁の混合・高調波で壊れる** ―― 光を変調して戻り光との相関を 4 段の位相で測る間接 ToF(位相方式)を、生信号から距離まで通し、壊れる所まで測る。新 op 8 本(`itof`、`opsoptics` の `itof`): `itof_capture`(距離の図 → 周波数ごと 4 段のバケット、ショット雑音・背景光・余分な経路・画素の開口での混合)/ `itof_phase_amplitude` / `itof_noise_budget` / `itof_unwrap_multifreq`(次数の仮説を全部試す最尤の復号・`residue_crt`・2 周波のうなり)/ `itof_unwrap_error_rate` / `itof_multipath_separate`(等間隔の多周波の行列ペンシル)/ `itof_flying_pixel_mask` / `itof_wiggling_correct`。σ_d は SNR ≥ 3 の 11 条件で閉形式 c/(4πf)·√((B+σ_r²)/2)/A の 0.999〜1.029 倍、Lange の式とも一致。16/80/120 MHz の組は 18.7 m まで一意で、次数の誤りは σ_φ = 0.33 rad で 0.116(和集合の上界 0.132)。★同じ生信号で `residue_crt` は 0.1161 —— Wang–Xia の錨の選び方(雑音の分散が最小の帯)で最尤と同等(16 MHz を常に錨にしていた修正前は 0.556)。80/100/120 MHz の組では 7.5 m より奥の棚が何の警告も無く手前に折り返す。包装フィルムの奥の箱は 1 周波で手前に引かれ(`lighttransport.tof_multipath_phase` と一致)、20〜160 MHz の 8 周波の行列ペンシルは間隔 0.8 m で全画素を 2 cm 以内に戻すが 0.2 m 以下は分けられない。部屋の隅は全面で 8〜99 mm 奥へ伸び、輸送行列の 1 回反射と 1e-15 m で一致。箱の縁で宙に浮いた画素の 97 % に印をつけ、段差の無い画素を消すのは 0.03 %。矩形波の周期誤差 ±84.8 mm は閉形式 atan(u/(1−u)) と一致し、模型の逆引きで雑音の床(2.1 mm)まで下がる。太陽光が信号の 50 倍だと 12 m 以遠の次数の誤りが 12 % → 93 %。同じ卓上の場面を直接 ToF で撮ると縁は浮かず、フィルムの下もずれない。公開の実機の生データ(3 周波 × 3 段、Lawin・Forssén・Ovrén、ECCV 2016、Zenodo、CC BY 4.0)では、真値に対する 30 cm 以上の飛びが最尤 0.131・`residue_crt` 0.131(10 枚の平均、修正前は 0.293)、margin で際どい画素を捨てると 68 % を残して 0.020。学習 0、較正は周期誤差の 16 点と実データの左半分だけ、門 30 件。*

[![平らな板(距離は一様乱数)で信号を振り、次数を誤った画素の割合を数えた。破線は候補ごとのガウスの 2 仮説の誤りの和(和集合の上界)、点線はその最大の 1 項。実測は 2 本の間に入る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_itof_multifreq/02_unwrap_error_rate_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_itof_multifreq/02_unwrap_error_rate.png)

*↑ 測定の図 ―― 平らな板(距離は一様乱数)で信号を振り、次数を誤った画素の割合を数えた。破線は候補ごとのガウスの 2 仮説の誤りの和(和集合の上界)、点線はその最大の 1 項。実測は 2 本の間に入る。*

[![通路の画素を距離帯に分け、次数を誤った割合と、その帯の位相雑音から見積もった上界を並べた。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_itof_multifreq/03_warehouse_by_range_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_itof_multifreq/03_warehouse_by_range.png)

*↑ 通路の画素を距離帯に分け、次数を誤った割合と、その帯の位相雑音から見積もった上界を並べた。*

[![向かいの壁で 1 回以上反射した光が遅れて混ざり、内角の面は全体に奥へ伸びる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_itof_multifreq/05_corner_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_itof_multifreq/05_corner_bias.png)

*↑ 向かいの壁で 1 回以上反射した光が遅れて混ざり、内角の面は全体に奥へ伸びる。*

[![同じ卓上の場面を 2 つの方式で撮る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_itof_multifreq/08_itof_vs_dtof_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_itof_multifreq/08_itof_vs_dtof.png)

*↑ 同じ卓上の場面を 2 つの方式で撮る。*

[![σ_d = c/(4πf)·√((B + σ_r²)/2)/A。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_itof_multifreq/11_noise_closed_form_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_itof_multifreq/11_noise_closed_form.png)

*↑ σ_d = c/(4πf)·√((B + σ_r²)/2)/A。*

[![左の箱の点群を回して見る。横から見ると、縁から背後の床へ視線に沿って伸びる赤い点の列(フライングピクセル)が現れる。右は印を除いたもの。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_itof_multifreq/14_flying_pixels_orbit.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_itof_multifreq/14_flying_pixels_orbit.gif)

*↑ 動く図 ―― 左の箱の点群を回して見る。横から見ると、縁から背後の床へ視線に沿って伸びる赤い点の列(フライングピクセル)が現れる。右は印を除いたもの。*

```
py -3.11 examples/poc_itof_multifreq.py
```

ソース: [examples/poc_itof_multifreq.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_itof_multifreq.py)

この回が作った図は全部で **14 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_itof_multifreq)

使用 op(ノートへ): [`annotate_figure_grid`](https://furuse.work/ops/annotate/paper/annotate_figure_grid.html) · [`camera_rays`](https://furuse.work/ops/optics/scene/camera_rays.html) · [`dtof_cube_depth`](https://furuse.work/ops/photon/dtof/dtof_cube_depth.html) · [`dtof_cube_simulate`](https://furuse.work/ops/photon/dtof/dtof_cube_simulate.html) · [`erfc`](https://furuse.work/ops/math/numerics/erfc.html) · [`form_factors_2d`](https://furuse.work/ops/optics/light_transport/form_factors_2d.html) · [`gamma`](https://furuse.work/ops/2d/gray/gamma.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`groove_profile`](https://furuse.work/ops/optics/light_transport/groove_profile.html) · [`itof_capture`](https://furuse.work/ops/optics/itof/itof_capture.html) · [`itof_flying_pixel_mask`](https://furuse.work/ops/optics/itof/itof_flying_pixel_mask.html) · [`itof_multipath_separate`](https://furuse.work/ops/optics/itof/itof_multipath_separate.html) · [`itof_noise_budget`](https://furuse.work/ops/optics/itof/itof_noise_budget.html) · [`itof_phase_amplitude`](https://furuse.work/ops/optics/itof/itof_phase_amplitude.html) · [`itof_unwrap_error_rate`](https://furuse.work/ops/optics/itof/itof_unwrap_error_rate.html) · [`itof_unwrap_multifreq`](https://furuse.work/ops/optics/itof/itof_unwrap_multifreq.html) · [`itof_wiggling_correct`](https://furuse.work/ops/optics/itof/itof_wiggling_correct.html) · [`residue_crt`](https://furuse.work/ops/residue/robust/residue_crt.html) · [`tof_multipath_phase`](https://furuse.work/ops/optics/light_transport/tof_multipath_phase.html) · [`tof_transport_depth`](https://furuse.work/ops/optics/light_transport/tof_transport_depth.html) · [`transport_matrix_radiosity`](https://furuse.work/ops/optics/light_transport/transport_matrix_radiosity.html)

## No.2026.241 —— 工業用 OCT ―― 塗装・コート・多層フィルムの層厚と中の欠陥を、1 本の干渉スペクトルの FFT で深さ方向に見る

[![工業用 OCT ―― 塗装・コート・多層フィルムの層厚と中の欠陥を、1 本の干渉スペクトルの FFT で深さ方向に見る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/01_real_paint_bscans_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/01_real_paint_bscans.png)

*↑ **工業用 OCT ―― 塗装・コート・多層フィルムの層厚と中の欠陥を、1 本の干渉スペクトルの FFT で深さ方向に見る** ―― 塗装・コンフォーマルコート・接着層・多層フィルムの層の並びと、層の中の空洞・剥離を光干渉断層(OCT)で壊さずに見る。新 op 13 本(`octscan`、`opsoptics` の `oct`): `oct_design`(軸分解能 0.44 λ0²/Δλ・深さ範囲 λ0²/(4δλ)・roll-off・SNR・横分解能と焦点深度を撮る前に)/ `oct_interferogram`・`oct_bscan_simulate`(層の並び → 干渉スペクトル、屈折率と分散は材料表)/ `oct_k_linearize`・`oct_dispersion_compensate`・`oct_dispersion_estimate`・`oct_ascan`・`oct_bscan` / `oct_layer_thickness`(群屈折率で厚さ、分離できなければ拒否)・`oct_bscan_boundaries`・`oct_bscan_flatten` / `oct_from_spectra`(生のスペクトルの入口)。**実測**: 公開の自動車塗装の生スペクトル(CC BY 4.0)を Fullseye の op だけで処理し、透明層 44.5 / 86.4 / 99.7 / 70.8 µm が論文の OCT と 1.5 µm 以内・顕微鏡と 3.6 µm 以内、着色層は 4 枚中 3 枚が顕微鏡と 2.3 µm 以内(1 枚は 7.6 µm ずれて未解決)、白の見本の着色層の下は拒否、透明層の光学厚 155.6 µm の深さに水平に出る自己相関の幽霊。合成: 群屈折率で割った厚さが真値と 0.04 µm、位相屈折率なら 0.9〜1.9 % 厚い、SNR・roll-off・分散の広がりが閉形式と一致、点像の幅の 1.4 倍より薄い層は拒否、コートの厚さの地図と空洞・剥離の検出。*

[![屈折率は論文と同じ 1.56(透明層)・1.64(着色層)。表のどの行がどのファイルかは論文に無く、透明層の厚さで決めた(推定)。着色層はその対応と独立の突き合わせ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/02_real_thickness_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/02_real_thickness_table.png)

*↑ 測定の図 ―― 屈折率は論文と同じ 1.56(透明層)・1.64(着色層)。表のどの行がどのファイルかは論文に無く、透明層の厚さで決めた(推定)。着色層はその対応と独立の突き合わせ。*

[![黒・濃色は透明層の下の面と着色層の下の面の 2 つの山。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/03_real_flattened_profiles_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/03_real_flattened_profiles.png)

*↑ 黒・濃色は透明層の下の面と着色層の下の面の 2 つの山。*

[![SD 840/50 nm 2048 画素(深さ範囲 2.26 mm)、SS 1310/100 nm・瞬時線幅 0.1 nm。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/06_rolloff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/06_rolloff.png)

*↑ SD 840/50 nm 2048 画素(深さ範囲 2.26 mm)、SS 1310/100 nm・瞬時線幅 0.1 nm。*

[![試料腕が参照光と同じ桁に強いと、層の上下の面どうしの干渉が 0 の近くに立つ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/09_autocorrelation_ghost_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/09_autocorrelation_ghost.png)

*↑ 試料腕が参照光と同じ桁に強いと、層の上下の面どうしの干渉が 0 の近くに立つ。*

[![横 1.2 mm、縦は光路 25〜440 µm。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/12_coat_bscan_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/12_coat_bscan.png)

*↑ 横 1.2 mm、縦は光路 25〜440 µm。*

[![試料腕に溶融石英 12 mm の分散の不一致。補償の係数 a2 を 0 から 35.6 µm² まで動かすと、PMMA / PC / PS の 3 層の界面がにじみから線に締まる(横 0.6 mm、光路 130〜380 µm)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/15_dispersion_compensation.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/15_dispersion_compensation.gif)

*↑ 動く図 ―― 試料腕に溶融石英 12 mm の分散の不一致。補償の係数 a2 を 0 から 35.6 µm² まで動かすと、PMMA / PC / PS の 3 層の界面がにじみから線に締まる(横 0.6 mm、光路 130〜380 µm)。*

```
py -3.11 examples/poc_industrial_oct.py
```

ソース: [examples/poc_industrial_oct.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_industrial_oct.py)

この回が作った図は全部で **15 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_industrial_oct)

使用 op(ノートへ): [`glass`](https://furuse.work/ops/optics/design/glass.html) · [`material_optical_constants`](https://furuse.work/ops/optics/matprop/material_optical_constants.html) · [`oct_ascan`](https://furuse.work/ops/optics/oct/oct_ascan.html) · [`oct_bscan`](https://furuse.work/ops/optics/oct/oct_bscan.html) · [`oct_bscan_boundaries`](https://furuse.work/ops/optics/oct/oct_bscan_boundaries.html) · [`oct_bscan_flatten`](https://furuse.work/ops/optics/oct/oct_bscan_flatten.html) · [`oct_bscan_simulate`](https://furuse.work/ops/optics/oct/oct_bscan_simulate.html) · [`oct_design`](https://furuse.work/ops/optics/oct/oct_design.html) · [`oct_dispersion_broadening`](https://furuse.work/ops/optics/oct/oct_dispersion_broadening.html) · [`oct_dispersion_compensate`](https://furuse.work/ops/optics/oct/oct_dispersion_compensate.html) · [`oct_dispersion_estimate`](https://furuse.work/ops/optics/oct/oct_dispersion_estimate.html) · [`oct_from_spectra`](https://furuse.work/ops/optics/oct/oct_from_spectra.html) · [`oct_interferogram`](https://furuse.work/ops/optics/oct/oct_interferogram.html) · [`oct_k_linearize`](https://furuse.work/ops/optics/oct/oct_k_linearize.html) · [`oct_layer_thickness`](https://furuse.work/ops/optics/oct/oct_layer_thickness.html)

## No.2026.237 —— 分光反射率で薄膜の膜厚を測る ―― 公開の実測データで採点し、縞・干渉色・FFT とあてはめ・膜厚むらの画像へ

[![分光反射率で薄膜の膜厚を測る ―― 公開の実測データで採点し、縞・干渉色・FFT とあてはめ・膜厚むらの画像へ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thin_film_reflectometry/01_real_micrograph_thickness_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thin_film_reflectometry/01_real_micrograph_thickness.png)

*↑ **分光反射率で薄膜の膜厚を測る ―― 公開の実測データで採点し、縞・干渉色・FFT とあてはめ・膜厚むらの画像へ** ―― Si 上の SiO₂ の膜厚を反射スペクトルの干渉縞から測る op 5 本(`filmoptics`、`opsoptics` の `film`): `multilayer_reflectance`(転送行列)/ `film_color` / `film_thickness_fft` / `film_thickness_fit` / `film_thickness_map`。膜も基板も材料表(`materials`)の鍵で引く。★主役は他人が測った実物のデータ(どちらも CC BY 4.0): Schwarz ら 2024 の顕微分光では、裸の Si の実測反射率が材料表の Si と中央値 0.4 % 差、SiO₂ の膜厚は直入射のモデルで 92.9 nm(基準 98.5 nm と −5.7 %)、残差が最小の NA 0.5 を入れると 95.8 nm(−2.7 %)。測定点の被覆率は 11 点を平均 0.6 点の誤差で読み返す。同じ試料の実物のカラー顕微鏡写真からは、裸の Si で白を合わせるだけで画素ごとの膜厚が出て中央値 87.4 nm(−11 %、カメラの分光感度は不明)。Sánchez-Arriaga ら 2023 の安価な分光器では、標準 476.3 nm が 5 本すべて 2 % 以内、198.7 nm は中央値 +6.6 % で、1 本は最良の候補が 51 nm に外れて正しい値は 2 番目の候補に残る。FFT 法は 98 nm の膜を自分で「信頼できない」と言う(下限の閉形式 554 nm)。合成の章: 1 層は Airy の式(別実装)と 3e-15、縞の本数は d·Δx と ±1、FFT の下限の閉形式 538 nm と実測 525 nm、材料の取り違え・入射角・NA の偏りは閉形式どおり。公表の色表との色相の一致は 1〜3 次で 59 %(弱い門)。模型のウェハ(彗星は縁まで半径方向、縁の盛り上がり、芯ずれの輪 —— 量は文献表に結びつけ、無いものは模型と明記)では分光 31 帯域の膜厚マップが RMS 0.17 nm、RGB は候補が複数の画素が 14 %。学習 0、門 37 件。*

[![実測の反射スペクトルに film_thickness_fit を当てた。直入射のモデルは 92.9 nm、残差が最小の NA 0.5 で 95.8 nm。裸の Si は材料表の Si と中央値 -0.4 % 差。出典: Schwarz ら,](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thin_film_reflectometry/02_real_spectra_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thin_film_reflectometry/02_real_spectra.png)

*↑ 測定の図 ―― 実測の反射スペクトルに film_thickness_fit を当てた。直入射のモデルは 92.9 nm、残差が最小の NA 0.5 で 95.8 nm。裸の Si は材料表の Si と中央値 -0.4 % 差。出典: Schwarz ら, Adv. Opt. Mater. (2024) doi:10.1002/adom.202402502、データ Zenodo 10.5281/zenodo.13753754(CC BY 4.0)。改変: 表から 2 本を選び、モデルの曲線を重ねた。*

[![476.3 nm は最大 1.2 %、198.7 nm は中央値 6.6 % 厚めに読み、1 本は最良の候補が 51 nm に外れた(正しい膜厚は 2 番目の候補)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thin_film_reflectometry/03_real_standards_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thin_film_reflectometry/03_real_standards.png)

*↑ 476.3 nm は最大 1.2 %、198.7 nm は中央値 6.6 % 厚めに読み、1 本は最良の候補が 51 nm に外れた(正しい膜厚は 2 番目の候補)。*

[![100 nm は縞が 1 本未満、2 µm は 7 本余り。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thin_film_reflectometry/05_spectra_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thin_film_reflectometry/05_spectra.png)

*↑ 100 nm は縞が 1 本未満、2 µm は 7 本余り。*

[![顕微分光の対物は斜めの光も入れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thin_film_reflectometry/08_na_apparent_thickness_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thin_film_reflectometry/08_na_apparent_thickness.png)

*↑ 顕微分光の対物は斜めの光も入れる。*

[![分光カメラは全画素で真値と RMS 0.17 nm。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thin_film_reflectometry/10_thickness_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thin_film_reflectometry/10_thickness_maps.png)

*↑ 分光カメラは全画素で真値と RMS 0.17 nm。*

[![膜厚を 0 → 1.5 µm に振ると縞が増え、色が周期的に巡りながら淡くなる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thin_film_reflectometry/12_thickness_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thin_film_reflectometry/12_thickness_sweep.gif)

*↑ 動く図 ―― 膜厚を 0 → 1.5 µm に振ると縞が増え、色が周期的に巡りながら淡くなる。*

```
py -3.11 examples/poc_thin_film_reflectometry.py
```

ソース: [examples/poc_thin_film_reflectometry.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_thin_film_reflectometry.py)

この回が作った図は全部で **13 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_thin_film_reflectometry)

使用 op(ノートへ): [`annotate_colorbar`](https://furuse.work/ops/annotate/paper/annotate_colorbar.html) · [`blackbody_spectrum`](https://furuse.work/ops/optics/spectral/blackbody_spectrum.html) · [`film_color`](https://furuse.work/ops/optics/film/film_color.html) · [`film_thickness_fft`](https://furuse.work/ops/optics/film/film_thickness_fft.html) · [`film_thickness_fit`](https://furuse.work/ops/optics/film/film_thickness_fit.html) · [`film_thickness_map`](https://furuse.work/ops/optics/film/film_thickness_map.html) · [`multilayer_reflectance`](https://furuse.work/ops/optics/film/multilayer_reflectance.html) · [`spectrum`](https://furuse.work/ops/oned/signal/spectrum.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`thinning`](https://furuse.work/ops/2d/region/thinning.html)

## No.2026.238 —— クロマティック共焦点変位センサ ―― 硝材の分散で「虹のものさし」を作り、戻ってきた色で高さを読む

[![クロマティック共焦点変位センサ ―― 硝材の分散で「虹のものさし」を作り、戻ってきた色で高さを読む](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_chromatic_confocal/01_rainbow_ruler_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_chromatic_confocal/01_rainbow_ruler.png)

*↑ **クロマティック共焦点変位センサ ―― 硝材の分散で「虹のものさし」を作り、戻ってきた色で高さを読む** ―― 白色光を軸上色収差の大きいレンズで集光すると、波長ごとに焦点の高さが変わる。面で反射してピンホールを通って分光器へ戻るのは面にピントの合った色だけなので、戻ってきた光の色が高さになる(Molesini 1984)。そのセンサを、対物レンズの処方(`raytrace`)と硝材の分散(材料表 `materials`)から組み立て、観察対象(ホウケイ酸クラウンの板・金・アルミ・Si)も同じ材料表から引いた。新 op 6 本(`chromconf`、`opsoptics` の `confocal`): `chromatic_confocal_probe`(処方 → 波長ごとの焦点位置の較正表)/ `confocal_axial_response`(共焦点の軸応答、鏡面 sinc²(u/2)・点 sinc⁴(u/4)、縦球面収差つき)/ `chromatic_confocal_spectrum`(面と層 → 戻りスペクトル、Fresnel・傾き・粗さ・分光器・雑音)/ `chromatic_confocal_peaks` / `chromatic_confocal_readout`(高さと透明板の厚さ)/ `chromatic_confocal_limits`(範囲・分解能・傾き・最小膜厚)。★虹のものさし: 高分散の重フリント(n_d 1.923・V_d 20.9)の非球面単レンズ(f 16 mm、NA 0.16)で 450〜700 nm の焦点が 1,191 µm にわたって並び、近軸焦点は厚肉レンズの閉形式と 4e-12 µm、軸応答の幅は 0.443 λ/(1 − cos α) と一致(∝ λ/NA²)。非球面は 575 nm でしか球面収差を消さず、450 nm では縦収差 −40 µm、較正のピークはその半分 −20 µm ずれて高さは 0.74 に落ちる。同じ f の球面の単レンズは縦収差 −863 µm で応答の幅が 29 倍に崩れ、ハイパークロマート(フッ素クラウン V_d 90.9 の負 + 重フリントの正)は焦点距離あたりの範囲が 1.63 倍。★読み: 設計値の較正表のままだと推定法の偏りがガウス 0.060・放物線 0.108・重心 0.293・最大ビン 2.04 µm。実機と同じ「鏡を動かして読む較正」でガウスは 0.014 µm に消えるが、放物線は 0.090 µm 残る(ビンの刻みで振れる偏りは滑らかな表で消せない)。雑音では順位が入れ替わり、重心の再現性は光子 4 倍で 1/2.1(√N)、3 点のガウスは重心の 4.4 倍ばらつく。50 µm の段差は 49.96 µm。★透明な板: ホウケイ酸クラウン 500 µm は見かけの厚さ × n(λ₂) の近軸の補正で −1.23 µm(平板の球面収差)、NA の補正で −0.07 µm、カタログの n_d を使うと −2.18 µm。サファイア・PMMA を含む 4 枚で 0.1 % 以内。★失敗条件: 鏡面が 8.8°(赤)〜9.5°(青)を超えて傾くと何も戻らない(瞳の重なりはモンテカルロと 0.004)。金は反射率の立ち上がる509 nm 付近で読みが 0.15 µm 遠くなり、反射率の傾き / 応答の曲率の閉形式が予言する(材料表の金の反射率で割ると 0.005 µm)。32 µm より薄いホウケイ酸クラウンの膜は 2 ピークに分かれず(Sparrow の閉形式 30.6 µm)、readout は厚さを当て推量せず拒否する。白色 LED のむらは 0.93 µm の偏り、白色参照で割ると 0.014 µm。粗さの偏りは閉形式どおり小さい(σ 60 nm で 0.06 µm)。★実画像: 公開論文(Qin ほか, Sensors 24(20):6649, 2024, CC BY 4.0)の図 6(b) の目盛と印から標準溝の深さを 66.095 µm と読み、基準 66.14 µm と −0.045 µm、論文自身の当てはめ 66.244 µm と −0.149 µm(図の 1 画素 = 0.33 µm、読みの目安の内)。図 3(a) の生の分光画像は列ごとのピークで溝の段差を 4.0 画素と読めるが µm への換算は図に無い —— 論文の結果を図から読み直す検査で、センサの模型の実機検証ではない(図は同梱せず `FULLSEYE_CCF_REAL_DIR`)。範囲の式・軸応答の幅・傾きの上限・推定法の系統誤差・透明板に n と NA が要ることは一次文献で確かめ、NA の補正式と金・粗さ・光源による偏りの大きさは模型と明記した。学習 0、較正は合成データで鏡を動かす 1 回だけ、門 33 件(実画像の段 +6)。*

[![左: 単レンズの範囲 1191 µm、ハイパークロマート 1842 µm(焦点距離あたり 1.63 倍)。近軸焦点は閉形式と 4e-12 µm で一致(点)。右: 鏡で較正したピークは近軸焦点から縦球面収差のほぼ半分だけずれる —— 450](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_chromatic_confocal/02_calibration_curve_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_chromatic_confocal/02_calibration_curve.png)

*↑ 測定の図 ―― 左: 単レンズの範囲 1191 µm、ハイパークロマート 1842 µm(焦点距離あたり 1.63 倍)。近軸焦点は閉形式と 4e-12 µm で一致(点)。右: 鏡で較正したピークは近軸焦点から縦球面収差のほぼ半分だけずれる —— 450 nm で -20.0 µm。575 nm では 0(非球面で消した色)。*

[![鏡面の応答は sinc²(u/2)、FWHM = 0.443 λ/(1 − cos α)(∝ λ/NA²)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_chromatic_confocal/03_axial_response_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_chromatic_confocal/03_axial_response.png)

*↑ 鏡面の応答は sinc²(u/2)、FWHM = 0.443 λ/(1 − cos α)(∝ λ/NA²)。*

[![段差は 49.959 µm と読める(RMS 誤差 0.276 µm)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_chromatic_confocal/05_step_and_tilt_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_chromatic_confocal/05_step_and_tilt.png)

*↑ 段差は 49.959 µm と読める(RMS 誤差 0.276 µm)。*

[![左: 透明な板は表と裏の 2 ピーク。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_chromatic_confocal/06_plate_and_gold_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_chromatic_confocal/06_plate_and_gold.png)

*↑ 左: 透明な板は表と裏の 2 ピーク。*

[![(a) 鏡面の傾きが 8.8°(sin 2θ = 2NA)を超えると何も戻らない(瞳の光線のモンテカルロと一致)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_chromatic_confocal/07_failure_modes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_chromatic_confocal/07_failure_modes.png)

*↑ (a) 鏡面の傾きが 8.8°(sin 2θ = 2NA)を超えると何も戻らない(瞳の光線のモンテカルロと一致)。*

[![上: 虹のものさし(焦点付近の光線)と面(灰色の縦線)。下: ピンホールへ戻るスペクトル(棒の色はその波長の色、ピーク 3000 光子 + 読出し雑音)。面を遠ざけると、ピントの合う色が青から赤へ移り、戻る色が変わる。ピーク波長を較正表で引](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_chromatic_confocal/04_spectrum_vs_height.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_chromatic_confocal/04_spectrum_vs_height.gif)

*↑ 動く図 ―― 上: 虹のものさし(焦点付近の光線)と面(灰色の縦線)。下: ピンホールへ戻るスペクトル(棒の色はその波長の色、ピーク 3000 光子 + 読出し雑音)。面を遠ざけると、ピントの合う色が青から赤へ移り、戻る色が変わる。ピーク波長を較正表で引くと高さになる。*

```
py -3.11 examples/poc_chromatic_confocal.py
```

ソース: [examples/poc_chromatic_confocal.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_chromatic_confocal.py)

この回が作った図は全部で **8 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_chromatic_confocal)

使用 op(ノートへ): [`abbe_number`](https://furuse.work/ops/optics/matprop/abbe_number.html) · [`chromatic_confocal_limits`](https://furuse.work/ops/optics/confocal/chromatic_confocal_limits.html) · [`chromatic_confocal_peaks`](https://furuse.work/ops/optics/confocal/chromatic_confocal_peaks.html) · [`chromatic_confocal_probe`](https://furuse.work/ops/optics/confocal/chromatic_confocal_probe.html) · [`chromatic_confocal_readout`](https://furuse.work/ops/optics/confocal/chromatic_confocal_readout.html) · [`chromatic_confocal_spectrum`](https://furuse.work/ops/optics/confocal/chromatic_confocal_spectrum.html) · [`cie_xyz_from_wavelength`](https://furuse.work/ops/optics/appearance/cie_xyz_from_wavelength.html) · [`confocal_axial_response`](https://furuse.work/ops/optics/confocal/confocal_axial_response.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`led_spectrum`](https://furuse.work/ops/optics/spectral/led_spectrum.html) · [`lens_system`](https://furuse.work/ops/optics/design/lens_system.html) · [`material_optical_constants`](https://furuse.work/ops/optics/matprop/material_optical_constants.html) · [`material_reflectance`](https://furuse.work/ops/optics/matprop/material_reflectance.html) · [`paraxial_trace`](https://furuse.work/ops/optics/design/paraxial_trace.html) · [`plate_focus_shift`](https://furuse.work/ops/optics/matprop/plate_focus_shift.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`trace_rays`](https://furuse.work/ops/optics/scene/trace_rays.html) · [`with_wavelength`](https://furuse.work/ops/optics/design/with_wavelength.html)

## No.2026.245 —— 仮想 SEM ―― 電子を 1 個ずつ固体に撃つと、加速電圧で像も測れる線幅も変わる(実測値で採点)

[![仮想 SEM ―― 電子を 1 個ずつ固体に撃つと、加速電圧で像も測れる線幅も変わる(実測値で採点)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_virtual_sem_kv_cd_bse/01_sem_interaction_volume_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_virtual_sem_kv_cd_bse/01_sem_interaction_volume.png)

*↑ **仮想 SEM ―― 電子を 1 個ずつ固体に撃つと、加速電圧で像も測れる線幅も変わる(実測値で採点)** ―― 走査電子顕微鏡(SEM)の像は表面の写真ではなく、固体の中で散乱する一次電子の**相互作用の体積**から何が出てきたかの集計である。新 op 8 本(`sem_electron_mc` / `sem_yield_curve` / `sem_se_universal_curve` / `sem_line_profile` / `sem_cd_measure` / `sem_image` / `sem_charging_series` / `sem_se_escape_fraction`)と材料表の `material_electron_properties` で、一次電子を 1 個ずつ追うモンテカルロ(Joy の単散乱、弾性散乱は Browning 1994 の Mott 近似、阻止能は Joy-Luo)を組み、各段を外の実測値で採点した。反射電子係数 η は 7 元素(C〜Au)× 5/10/20/30 keV の全部が Joy のデータベースの実測の幅 ± 0.04 に入り、遮蔽ラザフォードに戻すと W・Au で外れる。最大の到達深さは Kanaya-Okayama の 0.83〜1.04 倍、深さは E^1.75(Si)/ E^1.52(Au)で伸びる(KO は 1.67)。二次電子の収率の形は C〜Ag の 5 元素で Lin & Joy 2005 の普遍曲線に RMS ≤ 0.076、Emax は表の −4〜+7 %(合わせていない)。W・Au は裾が厚く合わない(SE2 が主、未解決)。★ユーザーの見立て「Si の上の W は SE では見えず、反射電子の Z コントラストで浮かぶ」は条件つきで当たった: 段差の無い W を 1 kV で見たときだけ(SE +5 %、反射電子 +96 %)。5 kV では SE も +80 % —— 反射電子が表面を抜けるときに作る SE2 が Z を運ぶ。深さ 150 nm に埋もれた W は 1 kV では反射電子でも +3 %、20 kV で +154 %(情報深さ)。CD-SEM では PMMA の線(底辺 40 nm)を側壁 88 度で測ると、しきい値法の線幅が 1 kV 39.1 nm / 20 kV 39.9 nm ―― 低加速は側壁の上寄り(0.33)、高加速は根元(0.03)を測る。ただし側壁 80 度では差が小さく向きも逆で、「低加速ほど上を測る」は一般則ではない。垂直の側壁はどの電圧でも太く測る(+0.3〜+1.0 nm)。帯電は、η + δ > 1 の 0.5 kV で正に溜まって暗くなり、η + δ·F(V*) = 1 を二分法で別に解いた電位に 2e-15 V で止まる。20 kV は負に溜まり続けて明るくなる(現象論)。途中で見つけた欠陥も残す: 自由行程を出発点の材料で引いたまま材料の境界を素通りしていて、0.01 nm の Si のキャップで W の η が 0.425 → 0.329 に跳んでいた(境界で歩を切って直し、回帰の門にした)。実画像の章は未実施(線幅の真値つきの CC BY の CD-SEM 像が見つからない)。*

[![δ(E) を各元素の MC の山(Emax, δmax)で割った形(横軸は対数)。破線は Lin & Joy 2005 の普遍曲線(式 12)。C〜Ag の 5 元素は重なる。W と Au(赤)は E > 3 Emax で裾が厚い —— 重](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_virtual_sem_kv_cd_bse/02_sem_se_universal_curve_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_virtual_sem_kv_cd_bse/02_sem_se_universal_curve.png)

*↑ 測定の図 ―― δ(E) を各元素の MC の山(Emax, δmax)で割った形(横軸は対数)。破線は Lin & Joy 2005 の普遍曲線(式 12)。C〜Ag の 5 元素は重なる。W と Au(赤)は E > 3 Emax で裾が厚い —— 重元素は反射電子が多く、表面を抜けるときに作る SE2 が主になるので、SE1 だけを仮定した普遍曲線からずれる(未解決のまま数で固定)。*

[![レンズ内の SE の線プロファイル(基板の水準で割った)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_virtual_sem_kv_cd_bse/03_sem_cd_profiles_by_kv_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_virtual_sem_kv_cd_bse/03_sem_cd_profiles_by_kv.png)

*↑ レンズ内の SE の線プロファイル(基板の水準で割った)。*

[![PMMA の線(高さ 40 nm)を Si の上で。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_virtual_sem_kv_cd_bse/04_sem_cd_bias_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_virtual_sem_kv_cd_bse/04_sem_cd_bias_table.png)

*↑ PMMA の線(高さ 40 nm)を Si の上で。*

[![Si に埋もれた W(幅 100 nm、厚さ 60 nm)の、真上と 400 nm 離れた Si の平均との比 − 1(反射電子 / レンズ内 SE)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_virtual_sem_kv_cd_bse/06_sem_buried_w_contrast_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_virtual_sem_kv_cd_bse/06_sem_buried_w_contrast.png)

*↑ Si に埋もれた W(幅 100 nm、厚さ 60 nm)の、真上と 400 nm 離れた Si の平均との比 − 1(反射電子 / レンズ内 SE)。*

[![各パネルは Si の水準で割った信号(0〜3 で共通の濃淡)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_virtual_sem_kv_cd_bse/07_sem_tungsten_se_vs_bse_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_virtual_sem_kv_cd_bse/07_sem_tungsten_se_vs_bse.png)

*↑ 各パネルは Si の水準で割った信号(0〜3 で共通の濃淡)。*

[![Si の上の PMMA の線を 5 kV で 24 コマ走査し続けた像。PMMA だけが負に帯電して明るくなり、接地した Si は変わらない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_virtual_sem_kv_cd_bse/09_sem_charging_pmma_line.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_virtual_sem_kv_cd_bse/09_sem_charging_pmma_line.gif)

*↑ 動く図 ―― Si の上の PMMA の線を 5 kV で 24 コマ走査し続けた像。PMMA だけが負に帯電して明るくなり、接地した Si は変わらない。*

```
py -3.11 examples/poc_virtual_sem_kv_cd_bse.py
```

ソース: [examples/poc_virtual_sem_kv_cd_bse.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_virtual_sem_kv_cd_bse.py)

この回が作った図は全部で **9 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_virtual_sem_kv_cd_bse)

使用 op(ノートへ): [`material_electron_properties`](https://furuse.work/ops/optics/matprop/material_electron_properties.html) · [`sem_cd_measure`](https://furuse.work/ops/generative/sem/sem_cd_measure.html) · [`sem_charging_series`](https://furuse.work/ops/generative/sem/sem_charging_series.html) · [`sem_electron_mc`](https://furuse.work/ops/generative/sem/sem_electron_mc.html) · [`sem_image`](https://furuse.work/ops/generative/sem/sem_image.html) · [`sem_line_profile`](https://furuse.work/ops/generative/sem/sem_line_profile.html) · [`sem_se_escape_fraction`](https://furuse.work/ops/generative/sem/sem_se_escape_fraction.html) · [`sem_se_universal_curve`](https://furuse.work/ops/generative/sem/sem_se_universal_curve.html) · [`sem_yield_curve`](https://furuse.work/ops/generative/sem/sem_yield_curve.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html)

## No.2026.246 —— 仮想の透過電子顕微鏡 ―― 焦点を振ると Thon リングが動き、細部が反転し、実写の写真から焦点外れを当てる

[![仮想の透過電子顕微鏡 ―― 焦点を振ると Thon リングが動き、細部が反転し、実写の写真から焦点外れを当てる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tem_ctf_thon_rings/02_thon_rings_four_defoci_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tem_ctf_thon_rings/02_thon_rings_four_defoci.png)

*↑ **仮想の透過電子顕微鏡 ―― 焦点を振ると Thon リングが動き、細部が反転し、実写の写真から焦点外れを当てる** ―― 透過電子顕微鏡は薄い試料を透けた電子の位相を、球面収差 Cs と焦点外れ Δf で強度に変える。その変え方 CTF = −sin(χ + arcsin w) は周波数ごとに符号が入れ替わり、パワースペクトルに零点の同心円(Thon リング)を描く。新 op 11 本(`temsim`、`opsoptics` の `tem`): `tem_wavelength` / `tem_scherzer` / `tem_ctf` / `tem_ctf_profile` / `tem_projected_potential` / `tem_amorphous_film` / `tem_image_weak_phase` / `tem_multislice` / `tem_power_spectrum` / `tem_ctf_estimate` / `tem_ctf_correct`。結像は `coherent_image` に瞳 e^{iχ} を渡し、電子の散乱因子は `pxrd` の X 線の因子から Mott–Bethe で作り、リングの周期の初期値は k² について不等間隔の標本に `lomb_scargle`、フレームの位置合わせは `phase_correlation_fft`(どれも既存の op)。波長は公表値と 5 桁(300 kV で 1.9687 pm、補正なしは 13.7 % 長い)、零点は閉形式と 1.7e-12 Å⁻¹、Scherzer 焦点の最初の零点は 0.6580 Cs^¼ λ^¾、正弦位相格子の回折は J_n(φ₀)² と 1.6e-13。Si の平均内部ポテンシャルは中性原子の値 13.71 V に対して 13.83 V(実測 12.48 V より高いのは結合の分)。★Cu の f_e(0) は 10.5 % 小さい(X 線の当てはめの限界)。像が投影ポテンシャルに最もよく似る焦点は 900 Å で Scherzer 842 Å の 7 % 以内、正焦点では細部が反転する(相関 −0.30)。合成の写真 4 枚で Δf を 13 Å 以内、非点収差を 50 Å・5.2° 以内で回収し、jackknife の σ が誤差を覆う。雑音だけ・線量不足・正焦点の近く・タイルが 9 枚しかなく別の谷に落ちた当てはめ、の 4 例はすべて拒否。画素寸法を 2 % 間違えると Δf は 1.039 倍(閉形式 1.0404)。ドリフトした 10 枚は和にするとリングが消え(当てはまりの分解能 15.6 Å)、合わせると戻る(5.3 Å)。位相反転で投影ポテンシャルとの相関は 0.09 → 0.84、ウィーナーで 0.87、Δf を 10 % 間違えると 0.10。★実写(EMPIAR-10028、CC0)3 枚で、著者の CTFFIND3 の値と −55 / +65 / −0.5 Å(0.2 % 以内)。学習 0、較正 0、門 36 件。*

[![焦点外れ Δf を 0.3 → 3 µm と振る(300 kV、Cs 2.7 mm、非晶質炭素 50 Å、40 e/Å² 相当の雑音)。左はパワースペクトル(k ≤ 0.25 Å⁻¹、動径の背景で割った)、右は同じ写真の一部。Thon リン](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tem_ctf_thon_rings/01_thon_ring_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tem_ctf_thon_rings/01_thon_ring_sweep.gif)

*↑ 測定の図 ―― 焦点外れ Δf を 0.3 → 3 µm と振る(300 kV、Cs 2.7 mm、非晶質炭素 50 Å、40 e/Å² 相当の雑音)。左はパワースペクトル(k ≤ 0.25 Å⁻¹、動径の背景で割った)、右は同じ写真の一部。Thon リングは Δf とともに内側へ詰まり、写真の粒状の模様が細かくなる。*

[![CTF = −sin(χ + arcsin w) に空間・時間の包絡を掛けた曲線(300 kV、Cs 2.7 mm、照明の半角 0.05 mrad、焦点の広がり 60 Å)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tem_ctf_thon_rings/03_ctf_curves_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tem_ctf_thon_rings/03_ctf_curves.png)

*↑ CTF = −sin(χ + arcsin w) に空間・時間の包絡を掛けた曲線(300 kV、Cs 2.7 mm、照明の半角 0.05 mrad、焦点の広がり 60 Å)。*

[![真値 Δf 25000 Å・非点収差 1500 Å・75° の合成写真。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tem_ctf_thon_rings/06_estimate_diagnostic_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tem_ctf_thon_rings/06_estimate_diagnostic.png)

*↑ 真値 Δf 25000 Å・非点収差 1500 Å・75° の合成写真。*

[![10 枚が 1 枚あたり (2.0, 0.6) 画素ずつドリフト。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tem_ctf_thon_rings/10_drift_alignment_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tem_ctf_thon_rings/10_drift_alignment.png)

*↑ 10 枚が 1 枚あたり (2.0, 0.6) 画素ずつドリフト。*

[![EMPIAR-10028 part1_001 の 1024 × 1024 画素(1.34 Å/画素)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tem_ctf_thon_rings/13_real_micrograph_part1_001_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tem_ctf_thon_rings/13_real_micrograph_part1_001.png)

*↑ EMPIAR-10028 part1_001 の 1024 × 1024 画素(1.34 Å/画素)。*

```
py -3.11 examples/poc_tem_ctf_thon_rings.py
```

ソース: [examples/poc_tem_ctf_thon_rings.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_tem_ctf_thon_rings.py)

この回が作った図は全部で **16 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_tem_ctf_thon_rings)

使用 op(ノートへ): [`tem_amorphous_film`](https://furuse.work/ops/optics/tem/tem_amorphous_film.html) · [`tem_ctf`](https://furuse.work/ops/optics/tem/tem_ctf.html) · [`tem_ctf_correct`](https://furuse.work/ops/optics/tem/tem_ctf_correct.html) · [`tem_ctf_estimate`](https://furuse.work/ops/optics/tem/tem_ctf_estimate.html) · [`tem_ctf_profile`](https://furuse.work/ops/optics/tem/tem_ctf_profile.html) · [`tem_image_weak_phase`](https://furuse.work/ops/optics/tem/tem_image_weak_phase.html) · [`tem_multislice`](https://furuse.work/ops/optics/tem/tem_multislice.html) · [`tem_power_spectrum`](https://furuse.work/ops/optics/tem/tem_power_spectrum.html) · [`tem_projected_potential`](https://furuse.work/ops/optics/tem/tem_projected_potential.html) · [`tem_scherzer`](https://furuse.work/ops/optics/tem/tem_scherzer.html) · [`tem_wavelength`](https://furuse.work/ops/optics/tem/tem_wavelength.html)

## No.2026.250 —— 分光器と照明系 ―― 帯域の幅はスリットと格子のどこから来るか、光源の模様は視野に写るか

[![分光器と照明系 ―― 帯域の幅はスリットと格子のどこから来るか、光源の模様は視野に写るか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_spectrometer_illumination/03_slit_image_smile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_spectrometer_illumination/03_slit_image_smile.png)

*↑ **分光器と照明系 ―― 帯域の幅はスリットと格子のどこから来るか、光源の模様は視野に写るか** ―― ハイパースペクトルの PoC は「帯域の幅 10 nm」、クロマティック共焦点の PoC は「分光器の線幅」を与えられた数字として使っていた。その数字を、入口スリット・格子の溝・鏡の焦点距離・検出器の画素から格子の式で組み立てる。同じく顕微鏡と同軸落射の照明のむらを、光源のどの面がどこへ写るか(共役)から出す。新 op 8 本: `gratingspec`(`opsoptics` の新カテゴリ `spectrometer`)の `grating_dispersion`(格子の式・分散・分解能 mN・重なる次数)/ `czerny_turner_design`(帯域と検出器からカメラの焦点距離、Shafer のコマの条件)/ `spectrometer_bandpass`(スリットの像 ⊗ 画素 ⊗ 回折の装置関数の FWHM とエタンデュ)/ `spectrometer_slit_image`(溝に沿った方向余弦を保つ 3 次元の格子の式で smile と keystone)/ `spectrometer_spectrum`(入力スペクトル → 画素の読み、2 次・3 次の重なり)、`illumdesign` の `illumination_train`(ケーラー / クリティカルの共役)/ `illumination_field`(標本の点と方向から光源まで近軸で逆に追う放射照度)/ `coaxial_illumination`(ハーフミラーの往復 R·T と、鏡面・つや消しの部品の像)。★公表の分光器(CC BY 4.0 の論文 2 本): Shafer の条件でカメラ鏡の軸外し角 14.9679°(公表 14.968°)、式 (16) のカメラの焦点距離 68.88 mm(公表 r = 136 mm)、M 型の像の幅 39.2 / 43.7 / 52.6 µm(公表 40 / 43 / 50)と分解能 0.397 nm(公表 0.385〜0.391)。Feng 2021 の中心 0.4 nm だけは、本文の値からスリットの像だけで 0.49 nm になり合わない(差は残す)。★取引: 細いスリットは回折の床 0.886 λ/(mN) で止まり(矩形の瞳で 5e-4 以内)、広いスリットでは光の量 × 分解能 = 一定。Hg の 576.96 / 579.07 nm はスリット 50 µm(FWHM 0.79 nm)で分かれ、150 µm(2.37 nm)では山が 1 つに化ける。★smile: 長さ 4 mm のスリットの像は端で 41.9 µm(3 画素)長い波長の側へ曲がり、閉形式 y'²(sin α + sin β)/(2 f cos β) と 0.2 % 以内、Littrow の曲率半径 f/(2 tan β) と 1e-9。面内の式を流用した壊した模型は曲がりが 0 で門に落ちる。keystone は端の 750 nm で 60 µm。★迷光の次数: Hg ランプの 253.65 / 365.02 nm が 2 次で 507.30 / 730.04 nm の画素に偽の線を作り、ロングパス 400 nm で消える。★HSI(900〜1700 nm、150 本/mm、InGaAs 15 µm): HSI の PoC の「10 nm」はスリット 75 µm に当たる(全帯域で 10.01〜10.03 nm)、25 µm なら 3.4 nm、8 µm 以下で画素の 1.5 nm。装置関数は台形でガウスではない。★クロマティック共焦点: 可視の分光器のスリットを 25 → 400 µm に広げると、ホウケイ酸クラウンの 40 µm の板から順に表裏の 2 ピークが潰れ、400 µm では 100 µm の板まで readout が拒否する。★照明: コイルの縞の光源をクリティカル照明は視野に写し(CV 0.53)、ケーラー照明は消す(CV 2e-16)。視野の直径 = 視野絞り × |M|、E = L π NA² を 1 % で。開口絞りをコンデンサの焦点面から 4 mm 外す探針で縞が漏れる。同軸は往復 R·T = 1/4(optscene の同軸の光と同じ値)、吸収 6 % で最適 R = 0.47、鏡面の部品はパネルを 1 + h/H 倍に引き伸ばして写し(端のけられは閉形式どおり)、テレセントリックは 1 倍、つや消しは長方形の Lambert 面の閉形式と 0.2 % 以内。学習 0、較正 0、門 40 件。*

[![スリットの幅で帯域の幅とエタンデュがどう動くか(1200 本/mm、M 型 2025 の設計、625 nm)。左: 細いスリットは回折の床 0.886 λ / (mN) で止まり、NA を上げて照らす溝を増やすと床が下がる。右: 広いスリッ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_spectrometer_illumination/01_resolution_vs_throughput_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_spectrometer_illumination/01_resolution_vs_throughput.png)

*↑ 測定の図 ―― スリットの幅で帯域の幅とエタンデュがどう動くか(1200 本/mm、M 型 2025 の設計、625 nm)。左: 細いスリットは回折の床 0.886 λ / (mN) で止まり、NA を上げて照らす溝を増やすと床が下がる。右: 広いスリットでは光の量と分解能の積が一定(傾き −1)、細くしていくと床に当たって光だけを失う。*

[![Hg の黄色の 2 本を、スリットの幅を変えて読む。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_spectrometer_illumination/02_mercury_yellow_doublet_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_spectrometer_illumination/02_mercury_yellow_doublet.png)

*↑ Hg の黄色の 2 本を、スリットの幅を変えて読む。*

[![1 次の 500〜750 nm の検出器に、紫外の Hg 線の 2 次の像が偽の線として乗る(効率 0.3 の模型)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_spectrometer_illumination/05_second_order_ghosts_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_spectrometer_illumination/05_second_order_ghosts.png)

*↑ 1 次の 500〜750 nm の検出器に、紫外の Hg 線の 2 次の像が偽の線として乗る(効率 0.3 の模型)。*

[![可視の分光器(600 本/mm)のスリットを広げると、薄い板の表裏の 2 ピークが 1 つに潰れ、readout は厚さを当て推量せず拒否する。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_spectrometer_illumination/07_chromconf_plate_vs_slit_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_spectrometer_illumination/07_chromconf_plate_vs_slit.png)

*↑ 可視の分光器(600 本/mm)のスリットを広げると、薄い板の表裏の 2 ピークが 1 つに潰れ、readout は厚さを当て推量せず拒否する。*

[![同軸落射(視野 44 mm 角): 鏡面の部品はパネルそのものを写す(R·T = 1/4)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_spectrometer_illumination/09_coaxial_views_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_spectrometer_illumination/09_coaxial_views.png)

*↑ 同軸落射(視野 44 mm 角): 鏡面の部品はパネルそのものを写す(R·T = 1/4)。*

```
py -3.11 examples/poc_spectrometer_illumination.py
```

ソース: [examples/poc_spectrometer_illumination.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_spectrometer_illumination.py)

この回が作った図は全部で **10 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_spectrometer_illumination)

使用 op(ノートへ): [`chromatic_confocal_peaks`](https://furuse.work/ops/optics/confocal/chromatic_confocal_peaks.html) · [`chromatic_confocal_probe`](https://furuse.work/ops/optics/confocal/chromatic_confocal_probe.html) · [`chromatic_confocal_readout`](https://furuse.work/ops/optics/confocal/chromatic_confocal_readout.html) · [`chromatic_confocal_spectrum`](https://furuse.work/ops/optics/confocal/chromatic_confocal_spectrum.html) · [`coaxial_illumination`](https://furuse.work/ops/optics/illumination/coaxial_illumination.html) · [`czerny_turner_design`](https://furuse.work/ops/optics/spectrometer/czerny_turner_design.html) · [`grating_dispersion`](https://furuse.work/ops/optics/spectrometer/grating_dispersion.html) · [`illumination_field`](https://furuse.work/ops/optics/illumination/illumination_field.html) · [`illumination_train`](https://furuse.work/ops/optics/illumination/illumination_train.html) · [`spectrometer_bandpass`](https://furuse.work/ops/optics/spectrometer/spectrometer_bandpass.html) · [`spectrometer_slit_image`](https://furuse.work/ops/optics/spectrometer/spectrometer_slit_image.html) · [`spectrometer_spectrum`](https://furuse.work/ops/optics/spectrometer/spectrometer_spectrum.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`wave_grating_orders`](https://furuse.work/ops/math/wave/wave_grating_orders.html)

## No.2026.251 —— 格子干渉計 ―― 吸収では見えない繊維の向き・微小な割れ・気孔を、縞の振幅(暗視野)で見る

[![格子干渉計 ―― 吸収では見えない繊維の向き・微小な割れ・気孔を、縞の振幅(暗視野)で見る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_grating_interferometry/12_real_three_images_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_grating_interferometry/12_real_three_images.png)

*↑ **格子干渉計 ―― 吸収では見えない繊維の向き・微小な割れ・気孔を、縞の振幅(暗視野)で見る** ―― 吸収ではほとんど見えない繊維の向き・幅 2 µm の割れ・気孔の群を、X 線の格子干渉計の暗視野(縞の振幅の落ち方)で見る。新 op 8 本(`gratinginterf`、`opsoptics` の `grating_interf`): 設計の閉形式 `talbot_grating_design`(位相 π / π/2 / 吸収格子の分数タルボ距離、円錐ビームの d' = Ld/(L − d)、分析格子と Lau の線源格子の周期)、`talbot_carpet`(格子の後ろの強度 I(x, z) を回折次数の和で)、`talbot_source_visibility`(線源の幅・ガウスの焦点・線源格子で縞の可視度が何倍に落ちるか)、順モデル `grating_stepping_simulate`、`grating_step_period_estimate`(1 周期が何ステップかを残差の最小で)、`grating_three_image_retrieve`(試料と基準の 2 組 → 透過・微分位相・暗視野)、`darkfield_scatter_relation`(暗視野 → 散乱角の広がり)、`dpc_integrate`(微分位相 → 位相 → 厚さ、折り返しは拒否)。タルボ絨毯の縞の可視度の極大 4 本が分数タルボ距離 (m − 1/2)p²/(4λ) と格子 0.89 mm 以内、高さ 1.2732(方形波の基本波 4/π)、標本化した場の FFT 伝搬(第 2 実装)と 8e-4。焦点 2 mm では縞が ×0.001 に消え、Lau の条件の線源格子(41 本)で 2/π = 0.637 まで戻り、周期を 1/41 ずらすと再び消える(線源の点の和と 6e-5)。短繊維強化樹脂の板では、幅 2 µm の割れが暗視野で CNR 13.5(吸収 1.34)、4 方位の暗視野の cos 2ω から繊維の向きを中央値 2.7°・90 % 点 6.6° で戻し、穴の後ろの合流線の 90° を 89.8° と読む。★探針: 0/90° の 2 方位だけでは斜めの繊維の誤差が 30.3°。丸棒の厚さは微分位相の積分で 1.0 % 以内、感度を上げて本当の |φ| が π を超えると拒否する。★正直な限界: 鋭い縁の 1 画素だけが π を超える板は折り返しが見えず、中央の厚さを −857 µm(真値 2000)と黙って間違える。1 周期 20.85 段の走査を P = N と仮定すると微分位相の誤差 0.063 rad、推定した P で 0.022 rad。★残差をあてた平均で割ると最小が +0.03 段偏る(op は素の平均で割る)。**実データ**(CC BY 4.0、Zenodo 16944391): 基準 22 枚・試料 24 枚の 1 周期は 20.80・22.30 段(残差 0.0073 → 0.0044)、吸収の強い球は散乱が弱く(−ln D 0.17)繊維の束は散乱が強い(0.55)、球の左右の縁で微分位相の符号が逆。学習 0、較正 0、門 22 件(実データの章を走らせたとき。データが無い・CI では 19 件)。*

[![位相 π の格子(28 keV、p1 = 4.36 µm)の後ろの強度 I(x, z)。横 = 第 1 格子からの距離 0〜z_T/2(429 mm)、縦 = 2 周期。周期 p1/2 の縞が結ぶ距離が分数タルボ距離 (m − 1/2)p1](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_grating_interferometry/01_talbot_carpet_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_grating_interferometry/01_talbot_carpet.png)

*↑ 測定の図 ―― 位相 π の格子(28 keV、p1 = 4.36 µm)の後ろの強度 I(x, z)。横 = 第 1 格子からの距離 0〜z_T/2(429 mm)、縦 = 2 周期。周期 p1/2 の縞が結ぶ距離が分数タルボ距離 (m − 1/2)p1²/(4λ) = 54, 161, 268, 376 mm。z = 0 は純粋な位相格子なので強度は一様(縞が無い)。*

[![点線 = 閉形式の距離。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_grating_interferometry/02_carpet_visibility_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_grating_interferometry/02_carpet_visibility.png)

*↑ 点線 = 閉形式の距離。*

[![開口 1/2 の線源格子。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_grating_interferometry/04_lau_condition_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_grating_interferometry/04_lau_condition.png)

*↑ 開口 1/2 の線源格子。*

[![中央: 色相 = 向き、明るさ = 異方性の強さ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_grating_interferometry/06_fiber_orientation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_grating_interferometry/06_fiber_orientation.png)

*↑ 中央: 色相 = 向き、明るさ = 異方性の強さ。*

[![正直な限界: 鋭い縁の 1 画素だけが π を超える板は、折り返した値が背景と π 以内に収まるので見えずに通る(中央の厚さ -857 µm、真値 2000 µm)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_grating_interferometry/09_wrap_refusal_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_grating_interferometry/09_wrap_refusal.png)

*↑ 正直な限界: 鋭い縁の 1 画素だけが π を超える板は、折り返した値が背景と π 以内に収まるので見えずに通る(中央の厚さ -857 µm、真値 2000 µm)。*

[![格子の向きを 0〜180° に回したときの暗視野(4 方位から戻した a、b、θ で描く)。繊維が格子の感度の向きに直交すると暗くなり、明暗の帯が向きの場に沿って流れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_grating_interferometry/07_rotating_grating.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_grating_interferometry/07_rotating_grating.gif)

*↑ 動く図 ―― 格子の向きを 0〜180° に回したときの暗視野(4 方位から戻した a、b、θ で描く)。繊維が格子の感度の向きに直交すると暗くなり、明暗の帯が向きの場に沿って流れる。*

```
py -3.11 examples/poc_grating_interferometry.py
```

ソース: [examples/poc_grating_interferometry.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_grating_interferometry.py)

この回が作った図は全部で **12 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_grating_interferometry)

使用 op(ノートへ): [`angular_spectrum_propagate`](https://furuse.work/ops/optics/wave/angular_spectrum_propagate.html) · [`dpc_integrate`](https://furuse.work/ops/optics/grating_interf/dpc_integrate.html) · [`grating_step_period_estimate`](https://furuse.work/ops/optics/grating_interf/grating_step_period_estimate.html) · [`grating_stepping_simulate`](https://furuse.work/ops/optics/grating_interf/grating_stepping_simulate.html) · [`grating_three_image_retrieve`](https://furuse.work/ops/optics/grating_interf/grating_three_image_retrieve.html) · [`talbot_carpet`](https://furuse.work/ops/optics/grating_interf/talbot_carpet.html) · [`talbot_grating_design`](https://furuse.work/ops/optics/grating_interf/talbot_grating_design.html) · [`talbot_source_visibility`](https://furuse.work/ops/optics/grating_interf/talbot_source_visibility.html)

## No.2026.255 —— 肉の中の骨片とガラスを、2 つのエネルギーで材質ごとに分ける(デュアルエナジー / フォトンカウンティング X 線)

[![肉の中の骨片とガラスを、2 つのエネルギーで材質ごとに分ける(デュアルエナジー / フォトンカウンティング X 線)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dual_energy_xray/04_tray_single_vs_basis_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dual_energy_xray/04_tray_single_vs_basis.png)

*↑ **肉の中の骨片とガラスを、2 つのエネルギーで材質ごとに分ける(デュアルエナジー / フォトンカウンティング X 線)** ―― 食品の X 線検査の 1 枚の透過像は各画素で L = −ln(I/I₀) という 1 つの数しか測らない —— 厚い肉と薄い硬い異物は区別できない。光子のエネルギーを 2 つの窓で数え分ける検出器で撮ると、μ(E) の形が材質で違うので、各画素で厚みと材質が分かれる(Alvarez & Macovski 1976 の基底分解)。新 op 14 本(`opstomography` の `spectral_xray`): 材料表の X 線の列(`material_xray_attenuation` ほか 3 本、NIST SRD 126 の部分集合と混合則)と `dualxray` 10 本(X 線管のスペクトル・線質・検出器のチャネル・投影・基底分解・CRLB・R 値・実効 Z・弁別の誤り率)。μ/ρ は NIST の公表値と一致(Cu 8 keV 52.55、K 端 38.4 → 278.4)、管の模型の半価層は IEC 61267 の線質 8 つと 5.8 % 以内(模型は公開のスペクトル計算(MIT)の形に合わせ、IEC の値は合わせに使っていない)。厚さ 25〜60 mm の肉のトレイで、骨片とガラスの段差は肉のむらの 0.9 倍、しきい値 1 本では肉の 86 % を誤検出、高域を取っても肉の重なりの縁が偽の塊 2 個になるが、赤身 + Al に分けた Al の像は偽の塊 0。厚い PE と薄い Al の交絡の組は 1 つの窓では d′ = 0、2 つの窓の誤り率 Φ(−d′/2) はモンテカルロと 0.004 以内、分けられなくなる Al の厚さ(誤り率 5 %)は閉形式 0.125 mm・実測 0.126 mm、肉 40 mm の下で 0.364 mm。分解の雑音はクラメール・ラオの下限の 0.995 / 0.997 倍。壊れ方: 電荷共有 25 % を知らずに分解すると肉が Al に化け、単色の近似は肉 6 cm で Al −1.5 mm に偏る。埋まった異物の見かけの Z は密度でも動く(PVC は 13.9 が 18.7 に見える)。学習 0、較正 0、門 21 件。*

[![W 陽極の管(Kramers の厚い陽極 + 自己吸収 + K 線 59 / 67 keV)を Al 2.5 mm で濾した光子スペクトル(半価層 2.74 mm Al、平均 42.6 keV)。CdTe 2 mm の吸収効率をかけ、堆積エ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dual_energy_xray/01_spectrum_and_windows_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dual_energy_xray/01_spectrum_and_windows.png)

*↑ 測定の図 ―― W 陽極の管(Kramers の厚い陽極 + 自己吸収 + K 線 59 / 67 keV)を Al 2.5 mm で濾した光子スペクトル(半価層 2.74 mm Al、平均 42.6 keV)。CdTe 2 mm の吸収効率をかけ、堆積エネルギーで 2 つの窓に分ける。*

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

ソース: [examples/poc_dual_energy_xray.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dual_energy_xray.py)

この回が作った図は全部で **12 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_dual_energy_xray)

使用 op(ノートへ): [`basis_decomposition_crlb`](https://furuse.work/ops/tomography/spectral_xray/basis_decomposition_crlb.html) · [`basis_material_decompose`](https://furuse.work/ops/tomography/spectral_xray/basis_material_decompose.html) · [`dual_energy_separability`](https://furuse.work/ops/tomography/spectral_xray/dual_energy_separability.html) · [`dual_kvp_channels`](https://furuse.work/ops/tomography/spectral_xray/dual_kvp_channels.html) · [`ellipse`](https://furuse.work/ops/annotate/shape/ellipse.html) · [`material_effective_z`](https://furuse.work/ops/tomography/spectral_xray/material_effective_z.html) · [`material_from_sellmeier`](https://furuse.work/ops/optics/matprop/material_from_sellmeier.html) · [`material_xray_attenuation`](https://furuse.work/ops/tomography/spectral_xray/material_xray_attenuation.html) · [`material_xray_constants`](https://furuse.work/ops/tomography/spectral_xray/material_xray_constants.html) · [`photon_counting_channels`](https://furuse.work/ops/tomography/spectral_xray/photon_counting_channels.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`xray_beam_quality`](https://furuse.work/ops/tomography/spectral_xray/xray_beam_quality.html) · [`xray_channel_projection`](https://furuse.work/ops/tomography/spectral_xray/xray_channel_projection.html) · [`xray_tube_spectrum`](https://furuse.work/ops/tomography/spectral_xray/xray_tube_spectrum.html)

## No.2026.271 —— レンズの製造公差を、MTF・歩留まり・補償ストロークまで一枚の予算にする

[![レンズの製造公差を、MTF・歩留まり・補償ストロークまで一枚の予算にする](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/01_sensitivity_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/01_sensitivity.png)

*↑ **レンズの製造公差を、MTF・歩留まり・補償ストロークまで一枚の予算にする** ―― 公開処方の三枚玉に、曲率・厚み・屈折率・アッベ数・偏心・傾き・面の非点不整・くさび・群偏心を行ごとに割り当てる。新 op 8 本は分布、中央差分感度、Monte Carlo、Wilson 95 % 歩留まり区間、複数の補償変数と組立ストロークを一つの報告にする。薄いくさびの像移動は閉形式 f(n−1)α に 6e-8、1 fringe の非点不整の実光線 OPD RMS は閉形式に 1.3 %。CI の 16 試行では歩留まり 0.688、内部間隔と像面の補償を足すと 1.000。一様・正規・切断正規は同じ ±公差でも 0.750 / 1.000 / 1.000、首位の公差を締めて低感度を緩めた再配分は 0.833。学習 0、較正 0。*

[![同じ試行から得た MTF と RMS spot。赤線は合否限界。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/02_histograms_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/02_histograms.png)

*↑ 測定の図 ―― 同じ試行から得た MTF と RMS spot。赤線は合否限界。*

[![像面だけの場合と内部間隔を加えた場合を比較。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/03_compensation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/03_compensation.png)

*↑ 像面だけの場合と内部間隔を加えた場合を比較。*

[![一様・正規・±公差で切った正規分布の歩留まり。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/04_distributions_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/04_distributions.png)

*↑ 一様・正規・±公差で切った正規分布の歩留まり。*

[![線形予測と Monte-Carlo 実測を明示。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/05_rebudget_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/05_rebudget.png)

*↑ 線形予測と Monte-Carlo 実測を明示。*

[![同じ処方の基準像と、1 arcmin のくさびを入れた像。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/06_wedge_probe_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/06_wedge_probe.png)

*↑ 同じ処方の基準像と、1 arcmin のくさびを入れた像。*

[![感度首行を -tol から +tol へ掃引した点像。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/07_tolerance_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/07_tolerance_sweep.gif)

*↑ 動く図 ―― 感度首行を -tol から +tol へ掃引した点像。*

```
py -3.11 examples/poc_lens_tolerancing.py
```

ソース: [examples/poc_lens_tolerancing.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_lens_tolerancing.py)

この回が作った図は全部で **7 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_lens_tolerancing)

使用 op(ノートへ): [`chief_ray`](https://furuse.work/ops/optics/design/chief_ray.html) · [`lens_system`](https://furuse.work/ops/optics/design/lens_system.html) · [`opd_samples`](https://furuse.work/ops/optics/design/opd_samples.html) · [`ray_bundle`](https://furuse.work/ops/optics/design/ray_bundle.html) · [`tolerance_compensators`](https://furuse.work/ops/optics/tolerancing/tolerance_compensators.html) · [`tolerance_criteria`](https://furuse.work/ops/optics/tolerancing/tolerance_criteria.html) · [`tolerance_monte_carlo`](https://furuse.work/ops/optics/tolerancing/tolerance_monte_carlo.html) · [`tolerance_report`](https://furuse.work/ops/optics/tolerancing/tolerance_report.html) · [`tolerance_sensitivity`](https://furuse.work/ops/optics/tolerancing/tolerance_sensitivity.html) · [`tolerance_table`](https://furuse.work/ops/optics/tolerancing/tolerance_table.html) · [`tolerance_table_from_zmx`](https://furuse.work/ops/optics/tolerancing/tolerance_table_from_zmx.html) · [`tolerance_table_zmx`](https://furuse.work/ops/optics/tolerancing/tolerance_table_zmx.html)

## No.2026.272 —— 処方から撮るプレノプティックカメラ

[![処方から撮るプレノプティックカメラ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_plenoptic_camera/03_raw_microimages_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_plenoptic_camera/03_raw_microimages.png)

*↑ **処方から撮るプレノプティックカメラ** ―― 主レンズ、周期球面 MLA、センサを逆追跡する合成 PoC。生画像には円盤状マイクロ像の格子、円盤間の暗い隅、円盤内の場面断片が現れ、EPI には視差の斜線が現れる。白色面の暗い隅は 21.33 %（閉形式 21.46 %）、円盤端/中心の輝度比は 9.92e-6、格子ピークは 0.06667 cycle/pixel、EPI は 0.6 px/view。開口を外すと暗い隅が 0 % になり門が赤になる。境界光線と校正残差も fail-closed に拒否する。*

[![480 x 480 sensor, 32 x 32 MLA, 15 pixels per microlens; five prescription-traced rays.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_plenoptic_camera/01_camera_section_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_plenoptic_camera/01_camera_section.png)

*↑ 測定の図 ―― 480 x 480 sensor, 32 x 32 MLA, 15 pixels per microlens; five prescription-traced rays.*

[![F-number ratios 0.75, 1.00 and 1.50; matched diameter/pitch = 1.000.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_plenoptic_camera/02_f_number_matching_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_plenoptic_camera/02_f_number_matching.png)

*↑ F-number ratios 0.75, 1.00 and 1.50; matched diameter/pitch = 1.000.*

[![15 x 15 decoded views; EPI disparity is 0.6 px per view step.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_plenoptic_camera/04_decode_subaperture_epi_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_plenoptic_camera/04_decode_subaperture_epi.png)

*↑ 15 x 15 decoded views; EPI disparity is 0.6 px per view step.*

[![Truth and estimate at 600, 1000 and 1800 mm; signed error and colour bar.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_plenoptic_camera/06_depth_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_plenoptic_camera/06_depth_map.png)

*↑ Truth and estimate at 600, 1000 and 1800 mm; signed error and colour bar.*

[![Same MLA: plenoptic 1.0 images the pupil; focused 2.0 images scene fragments.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_plenoptic_camera/07_plenoptic_1_vs_2_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_plenoptic_camera/07_plenoptic_1_vs_2.png)

*↑ Same MLA: plenoptic 1.0 images the pupil; focused 2.0 images scene fragments.*

[![24-frame 480-pixel refocus sweep; all frames pass the content gates.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_plenoptic_camera/09_refocus.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_plenoptic_camera/09_refocus.gif)

*↑ 動く図 ―― 24-frame 480-pixel refocus sweep; all frames pass the content gates.*

```
py -3.11 examples/poc_plenoptic_camera.py
```

ソース: [examples/poc_plenoptic_camera.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_plenoptic_camera.py)

この回が作った図は全部で **9 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_plenoptic_camera)

使用 op(ノートへ): [`lens_scene`](https://furuse.work/ops/optics/lensrender/lens_scene.html) · [`lens_system`](https://furuse.work/ops/optics/design/lens_system.html) · [`lf_depth_from_focus`](https://furuse.work/ops/lightfield/depth/lf_depth_from_focus.html) · [`lf_refocus`](https://furuse.work/ops/lightfield/refocus/lf_refocus.html) · [`mla_surface`](https://furuse.work/ops/optics/plenoptic/mla_surface.html) · [`paraxial_trace`](https://furuse.work/ops/optics/design/paraxial_trace.html) · [`plenoptic_capture`](https://furuse.work/ops/optics/plenoptic/plenoptic_capture.html) · [`plenoptic_mla_calibrate`](https://furuse.work/ops/optics/plenoptic/plenoptic_mla_calibrate.html) · [`plenoptic_refocus_depth`](https://furuse.work/ops/optics/plenoptic/plenoptic_refocus_depth.html) · [`plenoptic_system`](https://furuse.work/ops/optics/plenoptic/plenoptic_system.html)

## No.2026.273 —— 同じ粒子を走査像と透過像で測る ―― 52 nm と 48 nm のどちらが正しいか

[![同じ粒子を走査像と透過像で測る ―― 52 nm と 48 nm のどちらが正しいか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/02_same_specimen_sem_tem_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/02_same_specimen_sem_tem.png)

*↑ **同じ粒子を走査像と透過像で測る ―― 52 nm と 48 nm のどちらが正しいか** ―― 同じ球形・ファセット粒子14個の台帳から二つの像を作り、面積相当径、最大傾斜、接触対の分水嶺、傾斜像の高さ、限定角再構成を共通の真値で採点する。52 nm粒子では走査像のしきい値径は+4.16 nm、透過像は正焦点で-0.18 nm、焦点外れ12000 nmで+9.82 nm。走査像の偏りはガウス縁の閉形式2 sqrt(2 ln 2) sigmaに一致し、透過像の暗い縁はsqrt(lambda defocus)に10%以内。反射信号の材料比は公表された反射係数、立体計測は平行投影の閉形式と完全角再構成で検算する。新opなし、学習0、較正0。*

[![Truth height only: turbo-like pseudo-colour with a nanometre colour bar in the margin.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/01_truth_height_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/01_truth_height.png)

*↑ 測定の図 ―― Truth height only: turbo-like pseudo-colour with a nanometre colour bar in the margin.*

[![Bright-field in-focus and under-focus output | derived diameters | absolute residual.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/03_tem_raw_overlay_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/03_tem_raw_overlay_error.png)

*↑ Bright-field in-focus and under-focus output | derived diameters | absolute residual.*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/04_diameter_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/04_diameter_bias.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/05_touching_watershed_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/05_touching_watershed.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/06_missing_wedge_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/06_missing_wedge.png)

*↑ この回の図*

[![24 greyscale bright-field frames with data bar; first and last defocus differ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/08_tem_focus_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/08_tem_focus_sweep.gif)

*↑ 動く図 ―― 24 greyscale bright-field frames with data bar; first and last defocus differ*

```
py -3.11 examples/poc_sem_tem_same_particle.py
```

ソース: [examples/poc_sem_tem_same_particle.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_sem_tem_same_particle.py)

この回が作った図は全部で **8 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_sem_tem_same_particle)

使用 op(ノートへ): [`color_bar`](https://furuse.work/ops/annotate/furniture/color_bar.html) · [`filtered_backprojection`](https://furuse.work/ops/tomography/reconstruct/filtered_backprojection.html) · [`radon_transform`](https://furuse.work/ops/tomography/forward/radon_transform.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`scale_bar`](https://furuse.work/ops/annotate/furniture/scale_bar.html) · [`sem_electron_mc`](https://furuse.work/ops/generative/sem/sem_electron_mc.html) · [`sem_image`](https://furuse.work/ops/generative/sem/sem_image.html) · [`sem_render`](https://furuse.work/ops/generative/sem/sem_render.html) · [`tem_image_weak_phase`](https://furuse.work/ops/optics/tem/tem_image_weak_phase.html) · [`tem_multislice`](https://furuse.work/ops/optics/tem/tem_multislice.html) · [`tem_projected_potential`](https://furuse.work/ops/optics/tem/tem_projected_potential.html) · [`tem_wavelength`](https://furuse.work/ops/optics/tem/tem_wavelength.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`watersheds_marker`](https://furuse.work/ops/segmentation/watershed/watersheds_marker.html)

## No.2026.274 —— 同じ3次元場面を間接ToFと直接ToFで測る――多経路・混合画素・pile-up・体積誤差

[![同じ3次元場面を間接ToFと直接ToFで測る――多経路・混合画素・pile-up・体積誤差](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/01_scene_viewer_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/01_scene_viewer.png)

*↑ **同じ3次元場面を間接ToFと直接ToFで測る――多経路・混合画素・pile-up・体積誤差** ―― 320×240画素の同じ場面を、IR振幅、1.5–6.0 mの色距離、点群で見比べる。合成と実測の振幅分布のW1距離は0.145（門0.594）。続く図は物理効果を順に加えた深度、振幅と距離雑音（対数傾きは実測 -0.878、合成 -1.027）、壁接合部の湾曲（実測 -551 mm、合成 +75 mm。プロファイルの向きを揃えると同符号）、透明板の1.35 m離れた二返り、細い柱の混合画素、直接方式の時間ヒストグラム、三つの箱の体積（誤差 +0.16 / +0.47 / +0.29 %）を示す。最後は48枚、576×432画素、8 fpsで1.4–6.2 mを進む光前線。実フレームは再配布せず、曲線と集計値だけを載せる。新しいop 0、学習0、較正0、門13件。*

[![全パネル同じ距離範囲。暗部の荒れと隅の湾曲が順に現れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/02_effects_added_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/02_effects_added.png)

*↑ 測定の図 ―― 全パネル同じ距離範囲。暗部の荒れと隅の湾曲が順に現れる。*

[![対数傾きは実測 -0.878、合成 -1.027。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/03_noise_vs_amplitude_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/03_noise_vs_amplitude.png)

*↑ 対数傾きは実測 -0.878、合成 -1.027。*

[![実測は曲線だけを掲載し、フレームを再配布しない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/04_corner_bow_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/04_corner_bow.png)

*↑ 実測は曲線だけを掲載し、フレームを再配布しない。*

[![手描きマスクではなく3×3サブ光線のフェーザ和。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/06_pole_flying_pixels_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/06_pole_flying_pixels.png)

*↑ 手描きマスクではなく3×3サブ光線のフェーザ和。*

[![強い画素では最初の光子が早い側へ偏る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/07_dtof_histograms_depth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/07_dtof_histograms_depth.png)

*↑ 強い画素では最初の光子が早い側へ偏る。*

[![48枚、576×432。各時刻を99パーセンタイル・γ=0.5で階調化。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/09_dtof_light_front.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/09_dtof_light_front.gif)

*↑ 動く図 ―― 48枚、576×432。各時刻を99パーセンタイル・γ=0.5で階調化。*

```
py -3.11 examples/poc_tof_camera.py
```

ソース: [examples/poc_tof_camera.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_tof_camera.py)

この回が作った図は全部で **9 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_tof_camera)

使用 op(ノートへ): [`bilateral_filter_depth`](https://furuse.work/ops/3d/depth_denoise/bilateral_filter_depth.html) · [`depth_to_points`](https://furuse.work/ops/3d/transform/depth_to_points.html) · [`dtof_cube_depth`](https://furuse.work/ops/photon/dtof/dtof_cube_depth.html) · [`dtof_cube_simulate`](https://furuse.work/ops/photon/dtof/dtof_cube_simulate.html) · [`points_render`](https://furuse.work/ops/3d/render/points_render.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html)

## No.2026.275 —— 全天球の検査撮影と立体表示を一つの測定工程として確かめる

[![全天球の検査撮影と立体表示を一つの測定工程として確かめる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_omni360_inspection/08_anaglyph_and_limits_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_omni360_inspection/08_anaglyph_and_limits.png)

*↑ **全天球の検査撮影と立体表示を一つの測定工程として確かめる** ―― 半径3 mの合成トンネルを魚眼2面から全天球へ戻し、継ぎ目誤差0.01569、死角0.000 %を測った。球面重み、視野移動、32枚中16枚のタイル範囲、3 mの距離を3.000000 mへ戻す立体視、回転補正によるWS-PSNR 20.13 dBから33.51 dB、円筒展開、赤シアン表示を同じ場面で確かめた。理想フィルターの漏れは0、10 %漏れでは左右0.0693/0.0014。画面上視差は1.80 mm。8章、静止画8枚、30フレームの動画。学習0、校正0。*

[![Seed 275; tunnel radius 3.00 m; crack angular width 3.00 deg.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_omni360_inspection/01_world_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_omni360_inspection/01_world.png)

*↑ 測定の図 ―― Seed 275; tunnel radius 3.00 m; crack angular width 3.00 deg.*

[![Measured seam MAE 0.0157; blind pixels 0.000 % (reported, never filled silently).](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_omni360_inspection/02_fisheye_stitch_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_omni360_inspection/02_fisheye_stitch.png)

*↑ Measured seam MAE 0.0157; blind pixels 0.000 % (reported, never filled silently).*

[![Horizontal half-height width ratio 0.314; defect solid angle 0.03687 sr versus unweighted 0.02399 sr](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_omni360_inspection/03_latitude_processing_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_omni360_inspection/03_latitude_processing.png)

*↑ Horizontal half-height width ratio 0.314; defect solid angle 0.03687 sr versus unweighted 0.02399 sr.*

[![At 3.00 m: disparity 3.477 px and inverted depth 3.000000 m.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_omni360_inspection/05_ods_depth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_omni360_inspection/05_ods_depth.png)

*↑ At 3.00 m: disparity 3.477 px and inverted depth 3.000000 m.*

[![WS-PSNR improved from 20.13 to 33.51 dB; residual 0.0078.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_omni360_inspection/06_stabilisation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_omni360_inspection/06_stabilisation.png)

*↑ WS-PSNR improved from 20.13 to 33.51 dB; residual 0.0078.*

[![Thirty differing frames; the first frame is already moving.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_omni360_inspection/09_viewport_flight.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_omni360_inspection/09_viewport_flight.gif)

*↑ 動く図 ―― Thirty differing frames; the first frame is already moving.*

```
py -3.11 examples/poc_omni360_inspection.py
```

ソース: [examples/poc_omni360_inspection.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_omni360_inspection.py)

この回が作った図は全部で **9 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_omni360_inspection)

使用 op(ノートへ): [`anaglyph_crosstalk`](https://furuse.work/ops/optics/omni360/anaglyph_crosstalk.html) · [`equirect_defect_unwrap_pipe`](https://furuse.work/ops/optics/omni360/equirect_defect_unwrap_pipe.html) · [`equirect_filter_gaussian`](https://furuse.work/ops/optics/omni360/equirect_filter_gaussian.html) · [`equirect_from_fisheye_pair`](https://furuse.work/ops/optics/omni360/equirect_from_fisheye_pair.html) · [`equirect_rotate`](https://furuse.work/ops/optics/omni360/equirect_rotate.html) · [`equirect_stabilize`](https://furuse.work/ops/optics/omni360/equirect_stabilize.html) · [`equirect_weight_map`](https://furuse.work/ops/optics/omni360/equirect_weight_map.html) · [`ods_depth_to_disparity`](https://furuse.work/ops/optics/omni360/ods_depth_to_disparity.html) · [`ods_disparity_to_depth`](https://furuse.work/ops/optics/omni360/ods_disparity_to_depth.html) · [`omni_anaglyph_compose`](https://furuse.work/ops/optics/omni360/omni_anaglyph_compose.html) · [`stereo_parallax_budget`](https://furuse.work/ops/optics/omni360/stereo_parallax_budget.html) · [`video360_tile_coverage`](https://furuse.work/ops/optics/omni360/video360_tile_coverage.html) · [`video360_viewport_track`](https://furuse.work/ops/optics/omni360/video360_viewport_track.html) · [`viewport_from_equirect`](https://furuse.work/ops/optics/omni360/viewport_from_equirect.html) · [`ws_psnr`](https://furuse.work/ops/optics/omni360/ws_psnr.html)




---

**この展示館は Claude Code と一緒に作りました。** 問いと方向決めは私、実装・掃引・対照群・敵対レビューは Claude Code、という分業です。53 本の PoC を 2 日で走らせて図まで揃えられたのは、この運用のおかげです。試してみたい方は、こちらの招待リンクから **1 週間の無料トライアル** が使えます: [claude.ai/referral/0sqPw8E_lw](https://claude.ai/referral/0sqPw8E_lw)

面白い展示が 1 つでもあったら、**いいね・ストック**をもらえると助かります。どのウィングを次に増やすかは反応を見て決めるつもりなので、「自分の分野のこれが欲しい」もコメントで教えてください。実データに差し替えて崖の位置が変わった話は、いちばん聞きたい話です。
