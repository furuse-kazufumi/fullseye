# Fullseye でできること

**Language:** [日本語](CAPABILITIES.md) · [English](CAPABILITIES.en.md)

「どの op を呼ぶか」ではなく「**何ができるか**」から引く索引です。
1 項目 = 1 ファイル(`docs/capabilities/`)で、**すべて実在する op と、
その場で走る例に紐づいています** —— 裏づけの無い能力書きが混ざらないよう、
`tests/test_capabilities.py` が op 名を 4 層に、例をファイルの実在に
照らして落とします。

* op を名前で探すなら → [オペレータ索引](README.md#オペレータを探す)
* 真値つきで実問題を解いた記録なら → [PoC 展示館](README.md)
* 5 分で動かすなら → [GETTING_STARTED.md](GETTING_STARTED.md)

**足すには**: `docs/capabilities/<id>.md` を 1 本書いて
`py -3.11 tools/gen_capabilities_index.py` を実行するだけです
(この索引は生成物なので直接編集しないでください)。

**収録 24 項目**

## 課題から引く(推奨パイプライン)

op 名は全部レジストリに実在し、**型(in → out)が前段から後段へ繋がる**ことを `tests/test_capabilities.py` が検査する。型の同一視は 4 組だけ (`image2d`=`image`、`mask`=`region`、`measurement`=`feature`=`scalar`)。引数で渡す量は型連鎖の外。詳細(代替・限界・実寸校正)は各項目へ。

| 課題 | 推奨パイプライン(順序つき) | 動く例 |
|---|---|---|
| [位置を合わせて重ねる](capabilities/align-and-stack.md) | `align_frames` → `drizzle_resample` → `frame_quality` | `poc_astro_photometry` |
| [配列で方向を測り、距離と速度を分ける](capabilities/beamforming-and-range-doppler.md) | `beamform_doa` → `range_doppler_map` → `range_doppler_peaks` | `poc_multibeam_bathymetry` |
| [領域を切り出して、選んで、数える](capabilities/blob-and-region.md) | `auto_threshold` → `blob_label` → `blob_select` → `blob_features` | `poc_cell_counting` |
| [色を測る(XYZ / Lab / 色差)](capabilities/colour-and-delta-e.md) | `rgb_to_lab` → `delta_e_2000` | `poc_white_balance` |
| [結果を人が読める図にする](capabilities/figures-and-annotation.md) | `annotate_figure_grid` → `annotate_panel_label` → `annotate_scale_bar` → `annotate_colorbar` | `poc_colormap_readability` |
| [地球規模の座標に載せる(ECEF と測地座標)](capabilities/geodetic-frames.md) | `dem_geodetic_to_ecef` → `dem_ecef_to_geodetic` | `poc_geodetic_height_frames` |
| [円形部品の内径を mm まで測る](capabilities/inner-diameter-in-mm.md) | `gaussian` → `otsu` → `area_center` → `create_metrology_model` → `add_metrology_object_circle_measure` → `apply_metrology_model` → `mm_per_px_from_reference` → `pixel_to_world` | `example_inner_diameter_mm` |
| [地の色を知らずに線と領域を描く(反転色)](capabilities/inverted-colour-overlays.md) | `annotate_invert_visibility` → `annotate_invert` → `annotate_invert_path` | `annotate_paper_tour` |
| [OCR の前処理(傾き補正・局所 2 値化・行の切り出し)](capabilities/ocr-preprocessing.md) | `median` → `rotate_image` → `sk_sauvola` → `invert_region` → `remove_small` → `select_shape` → `dilation_rectangle1` | `gallery2d_segmentation` |
| [光の反射・屈折・干渉を計算する](capabilities/optics-and-materials.md) | `fresnel_dielectric` → `thin_film_reflectance` → `thin_film_rgb` | `glass_and_mirror_optics` |
| [1-D 信号の周期欠陥を見つける](capabilities/periodic-defects-in-1d-signals.md) | `smooth_funct_1d_gauss` → `bandpass` → `spectrum` → `find_peaks` → `peak_subbin` → `envelope` → `local_min_max_funct_1d` | `poc_web_roll_periodicity` |
| [3-D 点群から平面度を出す](capabilities/planarity-from-point-cloud.md) | `statistical_outlier_removal` → `ransac_plane` → `fit_plane_3d` → `distance_point_plane` | `geometry_metrology` |
| [小さな点状の目標を見つけて、副画素で位置を出す](capabilities/point-target-detection.md) | `noise_sigma` → `star_detect` → `find_peaks` → `peak_subbin` | `poc_search_sweep_width` |
| [偏光 4 方向で鏡面反射を除く(誘電体と金属で分ける)](capabilities/polarisation-specular-removal.md) | `polarization_dolp_map` → `polarization_separate` → `polarization_stokes` → `stokes_analyze` → `specular_diffuse_split` | `example_polarization_metal` |
| [微細スクラッチを見つけて、幅を測る](capabilities/scratch-detection-and-width.md) | `gaussian` → `lines_gauss` → `select_contours` → `fit_line_contours` → `gen_measure_rectangle2` → `measure_pairs` → `table_px_to_mm` | `example_scratch_width` |
| [画像から寸法をサブピクセルで測る](capabilities/subpixel-2d-metrology.md) | `gen_measure_rectangle2` → `measure_pos` → `measure_pairs` → `table_px_to_mm` | `poc_dimensional_inspection` |
| [表面の凹凸欠陥を、照明の設計から検出まで](capabilities/surface-defects-with-lighting.md) | `illumination_design` → `lighting_sweep` → `light_source` → `defect_contrast` → `irradiance_map` → `illumination_uniformity` → `photometric_stereo` → `integrate_normals` → `surface_form_error` → `bothat` → `auto_threshold` → `remove_small` | `illumination_design_demo` |
| [位置決め(テンプレート照合で測定線を追従させる)](capabilities/template-alignment.md) | `gaussian` → `ncc_locate` → `shape_locate` → `create_metrology_model` → `add_metrology_object_circle_measure` → `align_metrology_model` → `apply_metrology_model` | `poc_template_tracking` |
| [地形の傾き・水の流れ・見通しを測る](capabilities/terrain-and-visibility.md) | `dem_fill_sinks` → `dem_slope` → `dem_aspect` → `dem_flow_direction` → `dem_viewshed` | `poc_dem_terrain` |
| [画像の上に、文字と表を置きたい場所へ置く](capabilities/text-and-tables-on-images.md) | `measure_text` → `annotate_text_path_layout` → `annotate_text_path` → `annotate_table_layout` → `annotate_table` | `annotate_paper_tour` |
| [投影から断面を再構成する(CT)](capabilities/tomography-reconstruction.md) | `radon_transform` → `ring_artifact_remove` → `beam_hardening_correct` → `fbp_volume` → `vol_rle_components` → `vol_rle_volume` | `poc_ct_fidelity` |
| [振動と音から異常を診断する](capabilities/vibration-and-acoustics.md) | `bandpass` → `envelope` → `envelope_spectrum` → `find_peaks` → `bearing_defect_frequencies` | `poc_bearing_diagnosis` |
| [シルエットから立体を彫り出す(視体積交差)](capabilities/visual-hull-from-silhouettes.md) | `synthesize_silhouette` → `visual_hull` → `vol_rle_components` → `vol_rle_volume` | `space_carving` |
| [3-D スキャンから体積・土量を出す](capabilities/volume-from-3d-scan.md) | `vol_rle_components` → `vol_rle_volume` → `mesh_volume` | `poc_stockpile_volume` |

## 測る (7)

### [地球規模の座標に載せる(ECEF と測地座標)](capabilities/geodetic-frames.md)

緯度・経度・高さと地球中心直交座標(ECEF)を往復します。往復の誤差の床は実測で緯度 6.4e-12 度・高さ 8.5e-07 m(緯度 ±85 度・高さ -500〜9000 m の 4000 点、最大値)。

使う op: `dem_geodetic_to_ecef`, `dem_ecef_to_geodetic`

推奨パイプライン: [`dem_geodetic_to_ecef`](ops/dem/geodesy/dem_geodetic_to_ecef.md) → [`dem_ecef_to_geodetic`](ops/dem/geodesy/dem_ecef_to_geodetic.md)

代替: [`dem_geodetic_slope`](ops/dem/geodesy/dem_geodetic_slope.md)

限界: ジオイド高・正標高・局所 ENU・datum・epoch は**未実装**(2026-09-08 実測 0 件)。楕円体高と標高の取り違えは日本付近で 30〜40 m 静かにずれる(`poc_geodetic_height_frames`)。

実寸校正: 画素は関係しない。高さの基準面(楕円体か標高か)を必ず明示し、`H = h - N` の N は外部のジオイドモデルから持ち込む。

動く例: `poc_geodetic_height_frames`, `dem_geodesy_tour`

### [円形部品の内径を mm まで測る](capabilities/inner-diameter-in-mm.md)

穴・リング・ピンの内径を、粗い中心出し → サブピクセルの円当てはめ → 実寸校正 → mm、まで一気通貫で出します。文書だけを渡した AI は `measure_pairs` / `apply_metrology_model` で **px のまま止まっていた**(2026-09-15)ので、最後の 2 段(`mm_per_px_from_reference` / `pixel_to_world`)を op として型連鎖に置いてあります。

使う op: `add_metrology_object_circle_measure`, `apply_metrology_model`, `mm_per_px_from_reference`, `pixel_to_world`

推奨パイプライン: [`gaussian`](ops/2d/smoothing/gaussian.md) → [`otsu`](ops/2d/segmentation/otsu.md) → [`area_center`](ops/2d/features/area_center.md) → [`create_metrology_model`](ops/measure1d/model/create_metrology_model.md) → [`add_metrology_object_circle_measure`](ops/measure1d/model/add_metrology_object_circle_measure.md) → [`apply_metrology_model`](ops/measure1d/apply/apply_metrology_model.md) → [`mm_per_px_from_reference`](ops/measure1d/scale/mm_per_px_from_reference.md) → [`pixel_to_world`](ops/measure1d/scale/pixel_to_world.md)

代替: [`gen_measure_arc`](ops/measure1d/caliper/gen_measure_arc.md), [`measure_pos`](ops/measure1d/caliper/measure_pos.md), [`hx_fit_circle_contour`](ops/2d/halcon_ext/hx_fit_circle_contour.md), [`cv_hough_circles`](ops/2d/features/cv_hough_circles.md), [`hough_circle_trans`](ops/2d/features/hough_circle_trans.md), [`table_px_to_mm`](ops/measure1d/scale/table_px_to_mm.md)

限界: 参照半径が実物から ±6 px(`measure_length` 既定)より外れると縁が見つからない(+6.5 px で fail、実測)。丸い縁は −σ²/ρ だけ小さく出る。`n` は円周 3 px に 1 点で頭打ち(それ以上は独立に効かない、実測)。

実寸校正: 既知径の的(リングゲージ・基準穴)を**同じ円 op で**測り `mm_per_px_from_reference(2·radius_px, known_mm)` → `pixel_to_world(2·radius_px, mm_per_px)`。公称倍率は使わない。

動く例: `example_inner_diameter_mm`, `poc_dimensional_inspection`, `poc_real_coin_metrology`

### [3-D 点群から平面度を出す](capabilities/planarity-from-point-cloud.md)

定盤・フランジ・基板・床など「平らであるべき面」の点群から、外れ点を除き、頑健に平面を当てはめ、各点の面からの距離で**平面度**(PV・RMS)を出します。距離は符号つきなので、反り(低次)と局所の凹凸(高次)を分けて読めます。

使う op: `ransac_plane`, `fit_plane_3d`, `distance_point_plane`, `statistical_outlier_removal`

推奨パイプライン: [`statistical_outlier_removal`](ops/3d/preprocess/statistical_outlier_removal.md) → [`ransac_plane`](ops/3d/robust_fit/ransac_plane.md) → [`fit_plane_3d`](ops/3d/geometry/fit_plane_3d.md) → [`distance_point_plane`](ops/3d/geometry/distance_point_plane.md)

代替: [`fit_plane3`](ops/3d/geometry/fit_plane3.md), [`plane_segmentation`](ops/3d/segment/plane_segmentation.md), [`radius_outlier_removal`](ops/3d/preprocess/radius_outlier_removal.md), [`estimate_normals`](ops/3d/curvature/estimate_normals.md), [`surface_form_error`](ops/3d/surface_fit/surface_form_error.md)

限界: 平面度 PV は雑音の最大値統計で、完全に平らな面でも雑音だけで許容の 70 % を使う(RMS なら 2.03 mm 対 PV 4.89 mm)。最小二乗は外れ点 10 % で真値の 11 倍外れ、RANSAC は 45 % まで持って 55 % で別の面へ乗り換える。合わせ(ICP)は反りを吸って偽のへこみを作る。

実寸校正: 点群の座標系の単位(m / mm)を揃える。センサの測距雑音 σ を先に測り、PV は σ√(2 ln N) の床と比べて読む。

動く例: `geometry_metrology`, `poc_bump_coplanarity`, `poc_scan_to_bim_asbuilt`

### [微細スクラッチを見つけて、幅を測る](capabilities/scratch-detection-and-width.md)

線状の傷を**どこにあるか**(検出)と**どれだけ太いか**(幅)の 2 段で扱います。検出は Hessian リッジ応答(`lines_gauss`)か暗い細部だけを浮かせる形態学(`bothat`)、幅は検出した線に**直交する測定線**を張って `measure_pairs` で両側のエッジをサブピクセルで取り、`table_px_to_mm` で mm にします。

使う op: `lines_gauss`, `bothat`, `measure_pairs`, `table_px_to_mm`

推奨パイプライン: [`gaussian`](ops/2d/smoothing/gaussian.md) → [`lines_gauss`](ops/2d/contour/lines_gauss.md) → [`select_contours`](ops/2d/contour/select_contours.md) → [`fit_line_contours`](ops/2d/contour/fit_line_contours.md) → [`gen_measure_rectangle2`](ops/measure1d/caliper/gen_measure_rectangle2.md) → [`measure_pairs`](ops/measure1d/caliper/measure_pairs.md) → [`table_px_to_mm`](ops/measure1d/scale/table_px_to_mm.md)

代替: [`bothat`](ops/2d/morphology/bothat.md), [`tophat`](ops/2d/morphology/tophat.md), [`sk_frangi`](ops/2d/texture/sk_frangi.md), [`laplace_of_gauss`](ops/2d/edges/laplace_of_gauss.md), [`fuzzy_measure_pairing`](ops/measure1d/caliper/fuzzy_measure_pairing.md), [`mm_per_px_from_reference`](ops/measure1d/scale/mm_per_px_from_reference.md)

限界: `lines_gauss` は線の**幅も極性も返さない**(暗線・明線を同じ輪郭にする、実測)。幅 1〜3 px は `measure_pairs` の危険域(エッジ間距離 / PSF 幅 < 3.09 で大きい側へ偏り、失敗を返さない)—— 画素以下の幅は輝度欠損の積分で測る(`poc_crack_width`)。

実寸校正: 既知幅の的(スケールバー・基準溝)を同じ光学系で `measure_pairs` にかけ `mm_per_px_from_reference` → `table_px_to_mm`。0.1 mm を切る幅は mm/px の 1 % がそのまま効く。

動く例: `example_scratch_width`, `poc_crack_width`, `poc_solar_el_inspection`

### [画像から寸法をサブピクセルで測る](capabilities/subpixel-2d-metrology.md)

測定線に沿った輝度の勾配からエッジを**画素より細かく**求め、対になるエッジの間隔として寸法を返します。二値化して画素を数える方法と違い、しきい値の選び方で答えが動きません。

使う op: `measure_pos`, `measure_pairs`, `blob_label`, `blob_select`

推奨パイプライン: [`gen_measure_rectangle2`](ops/measure1d/caliper/gen_measure_rectangle2.md) → [`measure_pos`](ops/measure1d/caliper/measure_pos.md) → [`measure_pairs`](ops/measure1d/caliper/measure_pairs.md) → [`table_px_to_mm`](ops/measure1d/scale/table_px_to_mm.md)

代替: [`fuzzy_measure_pairing`](ops/measure1d/caliper/fuzzy_measure_pairing.md), [`gen_measure_arc`](ops/measure1d/caliper/gen_measure_arc.md), [`create_metrology_model`](ops/measure1d/model/create_metrology_model.md), [`blob_label`](ops/blob/connect/blob_label.md), [`blob_select`](ops/blob/select/blob_select.md), [`mm_per_px_from_reference`](ops/measure1d/scale/mm_per_px_from_reference.md)

限界: 斜めの測定線に cos 補正が無い。エッジ間距離 / PSF 幅 < 3.09 で幅が大きく出るのに失敗を返さない。縁の定義で 16 px 動く(guides/subpixel_measuring.md)。

実寸校正: 既知寸法の的を**同じ op で**測って `mm_per_px_from_reference` → `table_px_to_mm` で表ごと mm に。公称倍率は使わない(作動距離 10 % で全寸法 10 %)。

動く例: `poc_dimensional_inspection`, `poc_screw_thread_metrology`

### [地形の傾き・水の流れ・見通しを測る](capabilities/terrain-and-visibility.md)

高さ格子(DEM)から、傾斜・斜面方位・可視領域・流向を出します。いずれも閉形式と突き合わせられる量なので、実装の誤りを数字で捕まえられます。

使う op: `dem_slope`, `dem_aspect`, `dem_viewshed`, `dem_flow_direction`

推奨パイプライン: [`dem_fill_sinks`](ops/dem/hydrology/dem_fill_sinks.md) → [`dem_slope`](ops/dem/surface/dem_slope.md) → [`dem_aspect`](ops/dem/surface/dem_aspect.md) → [`dem_flow_direction`](ops/dem/hydrology/dem_flow_direction.md) → [`dem_viewshed`](ops/dem/visibility/dem_viewshed.md)

代替: [`dem_hillshade`](ops/dem/shading/dem_hillshade.md), [`dem_flow_accumulation`](ops/dem/hydrology/dem_flow_accumulation.md), [`dem_geodetic_slope`](ops/dem/geodesy/dem_geodetic_slope.md)

限界: 格子の刻みより細かい地形は出ない。可視領域は 1 観測点ぶん。測線の継ぎ目が地形に無い崖を作る(2.99 度 → 49.4 度、`poc_stockpile_volume`)。

実寸校正: `cell_size` [m] を渡す —— 傾斜は高さと格子間隔の**比**なので、単位が揃っていないと角度が全部ずれる。

動く例: `poc_dem_terrain`, `dem_terrain_analysis_tour`

### [3-D スキャンから体積・土量を出す](capabilities/volume-from-3d-scan.md)

点群や高さ格子から、閉じたメッシュの符号つき体積、voxel 領域の体積、2 つの面のあいだの土量を出します。欠測は補間で埋められますが、**その補間がどこまで効いたか**を別に持ち出せます。

使う op: `mesh_volume`, `vol_rle_volume`, `interp_scattered`, `dem_slope`

推奨パイプライン: [`vol_rle_components`](ops/3d/rle_region/vol_rle_components.md) → [`vol_rle_volume`](ops/3d/rle_region/vol_rle_volume.md) → [`mesh_volume`](ops/3d/mesh_process/mesh_volume.md)

代替: [`interp_scattered`](ops/math/interp_poly/interp_scattered.md), [`dem_slope`](ops/dem/surface/dem_slope.md), [`dem_fill_sinks`](ops/dem/hydrology/dem_fill_sinks.md), `marching_cubes`

限界: 底面が測れていない場面 —— 5 cm の仮定違いで 1.269 %(72.5 t)。外周平均の底面は誤差が打ち消して見えなくなる(`poc_stockpile_volume`)。

実寸校正: 格子間隔 [m] と高さ [m] の単位を揃える。ボクセル数はピッチの 3 乗。底面は**実際に見えた点だけ**で決める。

動く例: `poc_stockpile_volume`, `poc_lidar_terrain_change`

## 見つける (5)

### [領域を切り出して、選んで、数える](capabilities/blob-and-region.md)

連結成分にラベルを付け、面積・形・位置で選び、数えます。接触している対象は分水嶺で分けられます。

使う op: `blob_label`, `blob_select`, `blob_count`, `watersheds`

推奨パイプライン: [`auto_threshold`](ops/2d/segmentation/auto_threshold.md) → [`blob_label`](ops/blob/connect/blob_label.md) → [`blob_select`](ops/blob/select/blob_select.md) → [`blob_features`](ops/blob/measure/blob_features.md)

代替: [`watersheds`](ops/2d/segmentation/watersheds.md), [`blob_seeds`](ops/blob/split/blob_seeds.md), [`blob_count`](ops/2d/features/blob_count.md), [`remove_small`](ops/2d/region/remove_small.md), [`select_shape`](ops/2d/region/select_shape.md), [`otsu`](ops/2d/segmentation/otsu.md)

限界: 計数が合っていて分割が全部外れる点がある(`poc_cell_counting`)—— 数と形を別に数える。粒度分布で D50 が合う点は「正確」ではなく融合と縁切れの打ち消し(`poc_particle_sizing`)。

実寸校正: 面積は mm/px の **2 乗**。`mm_per_px_from_reference` で mm/px を出し、面積には自分で 2 乗して掛ける(`table_px_to_mm` が換算するのは長さ列だけ)。

動く例: `poc_cell_counting`, `poc_particle_sizing`, `poc_real_coin_metrology`

### [OCR の前処理(傾き補正・局所 2 値化・行の切り出し)](capabilities/ocr-preprocessing.md)

認識器(外部の OCR / 1-D・2-D コードのデコーダ)に渡す前の、**傾き補正 → 局所 2 値化 → ゴミ取り → 行のまとめ**を 2-D レジストリ op だけで組みます。認識そのものはこのライブラリの持ち場ではありません。

使う op: `sk_sauvola`, `rotate_image`, `remove_small`, `dilation_rectangle1`

推奨パイプライン: [`median`](ops/2d/rank/median.md) → [`rotate_image`](ops/2d/geometry/rotate_image.md) → [`sk_sauvola`](ops/2d/segmentation/sk_sauvola.md) → [`invert_region`](ops/2d/region/invert_region.md) → [`remove_small`](ops/2d/region/remove_small.md) → [`select_shape`](ops/2d/region/select_shape.md) → [`dilation_rectangle1`](ops/2d/region/dilation_rectangle1.md)

代替: [`sk_niblack`](ops/2d/segmentation/sk_niblack.md), [`adaptive_gauss_thresh`](ops/2d/segmentation/adaptive_gauss_thresh.md), [`otsu`](ops/2d/segmentation/otsu.md), [`gray_bothat`](ops/2d/morphology/gray_bothat.md), [`unsharp`](ops/2d/smoothing/unsharp.md), [`zoom_image_factor`](ops/2d/geometry/zoom_image_factor.md), [`affine_trans_image`](ops/2d/geometry/affine_trans_image.md)

限界: OCR 本体(文字認識)は無い —— ここは認識器に渡す 2 値画像を作る層。大域 `otsu` は照明むらで文字が欠ける(局所 `sk_sauvola` へ)。傾きは `rotate_image` の `a` で与える(角度の推定は輪郭 `fit_line_contours` か射影で別に取る)。細い字画は `remove_small` で消える。

実寸校正: 文字は px で扱い、実寸校正は不要。読み取り解像度の目安は x 高さ 20 px 以上(足りなければ `zoom_image_factor`)。

動く例: `gallery2d_segmentation`, `poc_matrix_code_reading`, `gallery2d_region`

### [小さな点状の目標を見つけて、副画素で位置を出す](capabilities/point-target-detection.md)

頑健に推定した背景と雑音から `背景 + kσ` を超える局所最大を拾い、重心で副画素の位置を返します。名前は天体ですが**中身は分野中立**で、漂流物・微小欠陥・蛍光輝点・粒子に同じものが使えます。

使う op: `star_detect`, `peak_subbin`, `find_peaks`, `noise_sigma`

推奨パイプライン: [`noise_sigma`](ops/astrostack/quality/noise_sigma.md) → [`star_detect`](ops/astrostack/photometry/star_detect.md) → [`find_peaks`](ops/oned/signal/find_peaks.md) → [`peak_subbin`](ops/oned/signal/peak_subbin.md)

代替: [`xsk3_peak_local_max`](ops/2d/segmentation/xsk3_peak_local_max.md), [`blob_seeds`](ops/blob/split/blob_seeds.md), [`blob_label`](ops/blob/connect/blob_label.md)

限界: 目標が広がっていると不適(`blob_label` へ)。検出率だけでは誤検出が見えない —— 空撮の誤検出は直下に集中し、閾値で走査幅が 406 → 170 m 動く(`poc_search_sweep_width`)。

実寸校正: 位置は px。実距離は `mm_per_px_from_reference`(空撮なら高度から GSD)で換算し、高度が変われば取り直す。

動く例: `poc_search_sweep_width`, `poc_astro_photometry`

### [表面の凹凸欠陥を、照明の設計から検出まで](capabilities/surface-defects-with-lighting.md)

打痕・バンプ・研削筋のような**形の欠陥**は、色ではなく面の傾きで見えます。だから照明を先に設計し(どの仰角の光でその傾斜が最もコントラストを出すか)、複数灯で法線を出し(フォトメトリックステレオ)、高さに積分し、そこから欠陥を切り出す —— この項目はその 4 段を 1 本に繋ぎます。

使う op: `illumination_design`, `lighting_sweep`, `photometric_stereo`, `integrate_normals`, `bothat`

推奨パイプライン: [`illumination_design`](ops/optics/illumination/illumination_design.md) → [`lighting_sweep`](ops/optics/illumination/lighting_sweep.md) → [`light_source`](ops/optics/illumination/light_source.md) → [`defect_contrast`](ops/optics/illumination/defect_contrast.md) → [`irradiance_map`](ops/optics/illumination/irradiance_map.md) → [`illumination_uniformity`](ops/optics/illumination/illumination_uniformity.md) → [`photometric_stereo`](ops/3d/photometric/photometric_stereo.md) → [`integrate_normals`](ops/3d/photometric/integrate_normals.md) → [`surface_form_error`](ops/3d/surface_fit/surface_form_error.md) → [`bothat`](ops/2d/morphology/bothat.md) → [`auto_threshold`](ops/2d/segmentation/auto_threshold.md) → [`remove_small`](ops/2d/region/remove_small.md)

代替: [`photometric_stereo_robust`](ops/specular/photometric/photometric_stereo_robust.md), [`normals_from_depth`](ops/3d/range_image/normals_from_depth.md), [`background_flatten`](ops/3d/surface_fit/background_flatten.md), [`tophat`](ops/2d/morphology/tophat.md), [`laplace_of_gauss`](ops/2d/edges/laplace_of_gauss.md), [`dem_slope`](ops/dem/surface/dem_slope.md)

限界: 照明設計は Michelson コントラストの**シミュレーション**(光沢面の峰は仰角 90° − 2×傾斜)で、実物の BRDF は代表値。フォトメトリックステレオは光源が 8 灯中 4 灯潰れると `lstsq` が 70 度外れ、頑健版でも汚染が半分を超えると壊れる。積分した高さは低周波が決まらない。

実寸校正: 高さは `photometric_stereo` の法線を `integrate_normals` で積分した**相対値**で、絶対 mm には mm/px と勾配の単位が要る。横方向は `mm_per_px_from_reference`、縦方向は既知段差の的で係数を出す。

動く例: `illumination_design_demo`, `photometric_stereo`, `poc_bump_coplanarity`

### [位置決め(テンプレート照合で測定線を追従させる)](capabilities/template-alignment.md)

ワークが画面内で動いても同じ場所を測るために、テンプレート照合で位置(と 30° 刻みの向き)を出し、そのずれを**測定モデルに反映**してから当てはめます。照合 → 位置決め → 計測、が型で繋がります。

使う op: `ncc_locate`, `shape_locate`, `align_metrology_model`, `translate_measure`

推奨パイプライン: [`gaussian`](ops/2d/smoothing/gaussian.md) → [`ncc_locate`](ops/2d/matching/ncc_locate.md) → [`shape_locate`](ops/2d/matching/shape_locate.md) → [`create_metrology_model`](ops/measure1d/model/create_metrology_model.md) → [`add_metrology_object_circle_measure`](ops/measure1d/model/add_metrology_object_circle_measure.md) → [`align_metrology_model`](ops/measure1d/apply/align_metrology_model.md) → [`apply_metrology_model`](ops/measure1d/apply/apply_metrology_model.md)

代替: [`edges_sub_pix`](ops/2d/contour/edges_sub_pix.md), [`fit_line_contours`](ops/2d/contour/fit_line_contours.md), [`translate_measure`](ops/measure1d/caliper/translate_measure.md), [`gen_measure_rectangle2`](ops/measure1d/caliper/gen_measure_rectangle2.md), [`rotate_image`](ops/2d/geometry/rotate_image.md), [`affine_trans_image`](ops/2d/geometry/affine_trans_image.md)

限界: `ncc_locate` は平行移動だけ、`shape_locate` は 30° 刻みの回転(それ以外の角度は最寄りに丸まる)。スコアが高いことは位置が正しい証拠にならない(繰り返し構造で 1.00 のまま外す —— `align-and-stack` の `frame_align` と同じ形)。`align_metrology_model` は平行移動だけで回転・スケールは扱わない。

実寸校正: 位置決め自体は px で閉じる。追従させた測定モデルの結果を mm にするときは `table_px_to_mm`(mm/px は `mm_per_px_from_reference`)。

動く例: `poc_template_tracking`, `gallery2d_contour_measure`, `poc_search_sweep_width`

## 形にする (2)

### [投影から断面を再構成する(CT)](capabilities/tomography-reconstruction.md)

平行ビームの順投影(サイノグラム)と、フィルタ補正逆投影による再構成、リングアーチファクトやビームハードニングの付与と補正を行います。再構成した体積はそのまま等値面としてメッシュ化できます。

使う op: `radon_transform`, `fbp_volume`, `ring_artifact_remove`, `marching_cubes`

推奨パイプライン: [`radon_transform`](ops/tomography/forward/radon_transform.md) → [`ring_artifact_remove`](ops/tomography/artifact/ring_artifact_remove.md) → [`beam_hardening_correct`](ops/tomography/artifact/beam_hardening_correct.md) → [`fbp_volume`](ops/tomography/volume/fbp_volume.md) → [`vol_rle_components`](ops/3d/rle_region/vol_rle_components.md) → [`vol_rle_volume`](ops/3d/rle_region/vol_rle_volume.md)

代替: `marching_cubes`, [`radon_volume`](ops/tomography/volume/radon_volume.md), [`sinogram_center_of_rotation`](ops/tomography/geometry/sinogram_center_of_rotation.md), [`ring_artifact_apply`](ops/tomography/artifact/ring_artifact_apply.md)

限界: iso-value を 1 段変えるだけでボイド体積・肉厚の合否が反転する(`poc_ct_void_morphology`)。投影数を減らすとフィルタ無し逆投影と 24 本で並び 12 本で逆転(`poc_ct_fidelity`)。

実寸校正: 体積はボクセルピッチの **3 乗**。ピッチは既知寸法のファントムを再構成して実測する(公称ピッチで 1 % ずれると体積 3 %)。

動く例: `poc_ct_fidelity`, `poc_ct_void_morphology`

### [シルエットから立体を彫り出す(視体積交差)](capabilities/visual-hull-from-silhouettes.md)

校正済みの複数カメラの前景マスクから、物体を必ず内包する体積を voxel として彫り出します。学習モデルも深度センサも要りません。

使う op: `synthesize_silhouette`, `carve`, `visual_hull`, `carve_look_at`

推奨パイプライン: [`synthesize_silhouette`](ops/3d/space_carving/synthesize_silhouette.md) → [`visual_hull`](ops/3d/space_carving/visual_hull.md) → [`vol_rle_components`](ops/3d/rle_region/vol_rle_components.md) → [`vol_rle_volume`](ops/3d/rle_region/vol_rle_volume.md)

代替: [`carve`](ops/3d/space_carving/carve.md), [`carve_look_at`](ops/3d/space_carving/carve_look_at.md), [`mesh_volume`](ops/3d/mesh_process/mesh_volume.md)

限界: 視体積交差は**必ず上界**。くぼみはカメラを増やしても残る(12 倍で 3.8 ポイント)。平行投影では偶数台の半分が無駄で 13 台が 16 台に勝つ。姿勢は OpenCV 規約(`carve_look_at`)。

実寸校正: K [px] と外部姿勢 [m] は校正済みのものを渡す。体積はボクセルピッチの 3 乗。シルエット 1 px の膨らみで体積 +3.21 %/px。

動く例: `space_carving`, `poc_livestock_body_volume`

## 光と色 (3)

### [色を測る(XYZ / Lab / 色差)](capabilities/colour-and-delta-e.md)

分光反射率または RGB から CIE XYZ・Lab を求め、CIE76 / CIEDE2000 の色差を出します。色差は画像全体の地図としても返せます。

使う op: `rgb_to_lab`, `xyz_to_lab`, `delta_e_2000`, `cie_xyz_from_wavelength`

推奨パイプライン: [`rgb_to_lab`](ops/imgmetrics/colorspace/rgb_to_lab.md) → [`delta_e_2000`](ops/imgmetrics/colordiff/delta_e_2000.md)

代替: [`rgb_to_xyz`](ops/imgmetrics/colorspace/rgb_to_xyz.md), [`xyz_to_lab`](ops/imgmetrics/colorspace/xyz_to_lab.md), [`delta_e_76`](ops/imgmetrics/colordiff/delta_e_76.md), [`delta_e_map`](ops/imgmetrics/colordiff/delta_e_map.md), [`cie_xyz_from_wavelength`](ops/optics/appearance/cie_xyz_from_wavelength.md), [`srgb_to_linear`](ops/gfx2d/colorspace/srgb_to_linear.md)

限界: 符号化 RGB を線形として扱うと全部ずれる。白色点(D50 / D65)の違う Lab を直接比べない。色恒常性に勝ち続ける手法は無い(`poc_white_balance`)。

実寸校正: 画素 → mm は関係しない。校正は**線形化**(`srgb_to_linear`)と**白色点**で、色差 ΔE は無次元。

動く例: `poc_white_balance`, `poc_pigment_unmixing`

### [光の反射・屈折・干渉を計算する](capabilities/optics-and-materials.md)

Fresnel の反射率、薄膜干渉の色、回折格子の色、ベクトル形の屈折(光線ごとの全反射判定つき)を、実在の硝材の分散を含めて計算します。

使う op: `fresnel_dielectric`, `thin_film_reflectance`, `grating_rgb`, `refract_rays`

推奨パイプライン: [`fresnel_dielectric`](ops/optics/interface/fresnel_dielectric.md) → [`thin_film_reflectance`](ops/optics/appearance/thin_film_reflectance.md) → [`thin_film_rgb`](ops/optics/appearance/thin_film_rgb.md)

代替: [`fresnel_conductor`](ops/optics/interface/fresnel_conductor.md), [`brewster_angle_deg`](ops/optics/interface/brewster_angle_deg.md), [`grating_rgb`](ops/optics/appearance/grating_rgb.md), [`refract_rays`](ops/optics/glassbody/refract_rays.md), [`fresnel_reflectance`](ops/3d/optics/fresnel_reflectance.md)

限界: `refract` は 1 本でも全反射があるとバッチ全体が `None`(`refract_rays` を使う)。`fresnel_dielectric` は実屈折率のみ —— 金属は `fresnel_conductor`。

実寸校正: 波長 [nm]・屈折率は無次元、角度は cos で渡す。画素校正は不要。

動く例: `glass_and_mirror_optics`, `appearance_structural_colour`

### [偏光 4 方向で鏡面反射を除く(誘電体と金属で分ける)](capabilities/polarisation-specular-removal.md)

偏光板を 0/45/90/135° に回した 4 枚(または DoFP センサの 4 画素)から、画素ごとに Malus の正弦波を当てはめ、**無偏光成分**(2·I_min)と**直線偏光成分**(I_max − I_min)に分けます。前者を拡散・後者を鏡面と呼ぶのは物理的仮定で、それが成り立つ誘電体と成り立たない金属を、この項目は分けて扱います。

使う op: `polarization_dolp_map`, `polarization_separate`, `polarization_stokes`, `specular_diffuse_split`

推奨パイプライン: [`polarization_dolp_map`](ops/specular/polarization/polarization_dolp_map.md) → [`polarization_separate`](ops/specular/polarization/polarization_separate.md) → [`polarization_stokes`](ops/specular/polarization/polarization_stokes.md) → [`stokes_analyze`](ops/optics/polarization/stokes_analyze.md) → [`specular_diffuse_split`](ops/specular/dichromatic/specular_diffuse_split.md)

代替: [`fresnel_conductor`](ops/optics/interface/fresnel_conductor.md), [`fresnel_dielectric`](ops/optics/interface/fresnel_dielectric.md), [`brewster_angle_deg`](ops/optics/interface/brewster_angle_deg.md), [`specular_free_transform`](ops/specular/dichromatic/specular_free_transform.md), [`specular_coefficient_map`](ops/specular/dichromatic/specular_coefficient_map.md)

限界: 分離が厳密なのは「鏡面が完全直線偏光」のとき = 誘電体の Brewster 角近傍だけ。金属は鏡面が部分偏光で、偏光度 p の残り (1−p)·S が **diffuse に残る**(`example_polarization_metal` が閉形式と一致させて示す)。法線入射では鏡面も無偏光で全部 diffuse。順序違いは等間隔角度では**検出できない**(全順列で違反率 0、実測)。

実寸校正: 画素校正は不要。`max_violation_frac` は雑音床で決める —— 違反は無偏光成分 D が 2〜3σ を切る画素で起き、その割合が目安(実測表は `specular_photometric.md`)。

動く例: `example_polarization_metal`, `poc_polarization_specular`, `specular_photometric`

## 波と信号 (3)

### [配列で方向を測り、距離と速度を分ける](capabilities/beamforming-and-range-doppler.md)

素子配列の受信からビームを立てて到来角を出し、FMCW の受信から距離-速度面を作って検出を距離 [m] と速度 [m/s] に戻します。

使う op: `beamform_delay_sum`, `beamform_doa`, `range_doppler_map`, `range_doppler_peaks`

推奨パイプライン: [`beamform_doa`](ops/rangedoppler/beamform/beamform_doa.md) → [`range_doppler_map`](ops/rangedoppler/process/range_doppler_map.md) → [`range_doppler_peaks`](ops/rangedoppler/process/range_doppler_peaks.md)

代替: [`beamform_delay_sum`](ops/rangedoppler/beamform/beamform_delay_sum.md)

限界: 語彙は電波レーダ向け。音響は `eta = 1/c` で読み替え、`beamform_doa` の距離・速度はパルス測深機に対応物が無い。素子スナップショット 1 枚を渡す口が無く立方体へ水増しが要る(`poc_multibeam_bathymetry` §11)。

実寸校正: 画素校正は無い。距離 [m] と速度 [m/s] は搬送波周波数・チャープ帯域・サンプル率から op が出すので、その 3 つを実機の設定値で渡す。

動く例: `poc_multibeam_bathymetry`, `poc_bev_sensor_fusion`

### [1-D 信号の周期欠陥を見つける](capabilities/periodic-defects-in-1d-signals.md)

ロール起因の周期むら、レールの波状摩耗、軸受の欠陥のように**同じ間隔で繰り返す**欠陥を、1-D の系列(断面・時系列・走査線)から見つけます。周期は `spectrum` の峰、峰の正確な周波数は `peak_subbin`、欠陥がどこにあるかは `envelope` の極値、という役割分担です。

使う op: `spectrum`, `find_peaks`, `peak_subbin`, `envelope`, `cepstrum`

推奨パイプライン: [`smooth_funct_1d_gauss`](ops/oned/function/smooth_funct_1d_gauss.md) → [`bandpass`](ops/oned/signal/bandpass.md) → [`spectrum`](ops/oned/signal/spectrum.md) → [`find_peaks`](ops/oned/signal/find_peaks.md) → [`peak_subbin`](ops/oned/signal/peak_subbin.md) → [`envelope`](ops/oned/signal/envelope.md) → [`local_min_max_funct_1d`](ops/oned/function/local_min_max_funct_1d.md)

代替: [`cepstrum`](ops/acoustics/bearing/cepstrum.md), [`envelope_spectrum`](ops/acoustics/bearing/envelope_spectrum.md), [`order_spectrum`](ops/acoustics/order/order_spectrum.md), [`signal_features`](ops/oned/signal/signal_features.md), [`zero_crossings_funct_1d`](ops/oned/function/zero_crossings_funct_1d.md), [`point_spectrum`](ops/oned/signal/point_spectrum.md)

限界: スペクトルの峰は周期の**存在**を言うだけで位置は言わない(位置は包絡の極値から)。ケプストラムは周期の族が 1 つのときだけ効く(`poc_web_roll_periodicity` §3 で使えなかった)。弦(versine)測定は伝達関数が 0 になる波長を「欠陥なし」と出す。

実寸校正: 標本間隔(`rate` [Hz] か 1 標本あたりの長さ [mm])を必ず渡す —— 周期 [mm] や周波数 [Hz] はそこから決まる。副ビン `peak_subbin` の精度はビン幅の 1/10 程度。

動く例: `poc_web_roll_periodicity`, `poc_rail_corrugation`, `poc_bearing_diagnosis`

### [振動と音から異常を診断する](capabilities/vibration-and-acoustics.md)

包絡スペクトル・ケプストラム・オクターブ帯域・軸受の特徴周波数など、回転機械の診断に使う量を出します。周波数は幾何から先に計算できるので、**どのピークを見るべきかを測る前に決められます**。

使う op: `signal_features`, `envelope_spectrum`, `bearing_defect_frequencies`, `octave_spectrum`, `spectrum`

推奨パイプライン: [`bandpass`](ops/oned/signal/bandpass.md) → [`envelope`](ops/oned/signal/envelope.md) → [`envelope_spectrum`](ops/acoustics/bearing/envelope_spectrum.md) → [`find_peaks`](ops/oned/signal/find_peaks.md) → [`bearing_defect_frequencies`](ops/acoustics/bearing/bearing_defect_frequencies.md)

代替: [`signal_features`](ops/oned/signal/signal_features.md), [`octave_spectrum`](ops/acoustics/level/octave_spectrum.md), [`spectrum`](ops/oned/signal/spectrum.md), [`cepstrum`](ops/acoustics/bearing/cepstrum.md), [`order_spectrum`](ops/acoustics/order/order_spectrum.md), [`rms`](ops/oned/signal/rms.md)

限界: 弦(versine)で測る波状摩耗のように伝達関数が 0 になる波長は「欠陥なし」と出る(`poc_rail_corrugation`)。束ねても情報が増えない条件がある(`poc_machine_condition_fusion`)。

実寸校正: サンプル率 `rate` [Hz] を必ず渡す。軸受の特徴周波数は回転数 [rpm] と幾何から `bearing_defect_frequencies` が先に出す。

動く例: `poc_bearing_diagnosis`, `poc_rail_corrugation`

## 組み立てる (1)

### [位置を合わせて重ねる](capabilities/align-and-stack.md)

画像列の平行移動を投票で合わせ、サブピクセルで再標本して重ねます。点群は ICP で合わせられます。

使う op: `frame_align`, `drizzle_resample`, `icp_point2point_3d`, `interp_scattered`

推奨パイプライン: [`align_frames`](ops/astrostack/align/align_frames.md) → [`drizzle_resample`](ops/astrostack/stack/drizzle_resample.md) → [`frame_quality`](ops/astrostack/quality/frame_quality.md)

代替: [`frame_align`](ops/astrostack/align/frame_align.md), [`icp_point2point_3d`](ops/3d/refine/icp_point2point_3d.md), [`register_cross`](ops/3d/fusion/register_cross.md), [`interp_scattered`](ops/math/interp_poly/interp_scattered.md)

限界: 繰り返し構造(網点・格子)では `frame_align` が `inlier_ratio` 1.00 のまま 80.85 px 外す —— `vote_margin` を併せて見る。合わせすぎると欠陥が消える(`poc_cad_scan_deviation`)。

実寸校正: 合わせは px のまま。変位を実寸にするなら既知寸法の的を同じ光学系で測り `mm_per_px_from_reference` → `pixel_to_world`。

動く例: `poc_astro_photometry`, `poc_registration_basin`

## 見せる (3)

### [結果を人が読める図にする](capabilities/figures-and-annotation.md)

パネルを並べた図、寸法や矢印の注釈、高さの疑似カラー、SDF から起こした立体のレンダリングまで、**fullseye 自身の op** で作れます。外部の作図ライブラリを挟まずに、出力そのものを図にできます。

使う op: `annotate_figure_grid`, `colorize_height`, `render_beauty`

推奨パイプライン: [`annotate_figure_grid`](ops/annotate/paper/annotate_figure_grid.md) → [`annotate_panel_label`](ops/annotate/paper/annotate_panel_label.md) → [`annotate_scale_bar`](ops/annotate/paper/annotate_scale_bar.md) → [`annotate_colorbar`](ops/annotate/paper/annotate_colorbar.md)

代替: `colorize_height`, [`render_beauty`](ops/3d/render/render_beauty.md), [`annotate_legend`](ops/annotate/paper/annotate_legend.md), [`annotate_inset`](ops/annotate/paper/annotate_inset.md)

限界: 疑似カラーの選び方で**無い境目**が見える(`poc_colormap_readability`)。`annotate_figure_grid` の `letters=True` と手書きの (a) が二重になる。

実寸校正: `annotate_scale_bar` の `units_per_pixel` は `mm_per_px_from_reference` で**実測**した mm/px を渡す(公称倍率で描いたスケールバーは嘘の長さになる)。

動く例: `poc_colormap_readability`, `poc_dem_terrain`

### [地の色を知らずに線と領域を描く(反転色)](capabilities/inverted-colour-overlays.md)

検査画像に測定線や ROI を重ねるとき、**地が明るいか暗いか分からない**のが普通です。白で描けば白飛びの上で消え、黒で描けば影の上で消えます。反転色は「その場の色をひっくり返して描く」ことでこれを避ける古典手で、`annotate_invert_path` が折れ線(アンチエイリアス・破線可)、`annotate_invert` が領域を、`draw="fill"` で中身ごと、`draw="margin"` で輪郭だけ反転します(HALCON の `set_draw` と同じ語)。

使う op: `annotate_invert`, `annotate_invert_path`, `annotate_invert_visibility`

推奨パイプライン: [`annotate_invert_visibility`](ops/annotate/overlay/annotate_invert_visibility.md) → [`annotate_invert`](ops/annotate/overlay/annotate_invert.md) → [`annotate_invert_path`](ops/annotate/overlay/annotate_invert_path.md)

代替: [`annotate_legend`](ops/annotate/paper/annotate_legend.md), [`text_box`](ops/annotate/text/text_box.md)

限界: 中間調で消える(8bit グレー `v ∈ [113, 142]` の 30/256 階調、`v=128` で比 1.014)。測るのは WCAG **輝度**比だけ。`alpha` を落とすと答えが変わる。地がグレーなら彩度のある色のほうが確実。

実寸校正: 描画のみ。実寸校正は不要。

動く例: `annotate_paper_tour`

### [画像の上に、文字と表を置きたい場所へ置く](capabilities/text-and-tables-on-images.md)

検査画像や解析結果に、**位置を指定して**文字を焼き込めます。`text_box` は 9 方向のアンカー・半透明の板・折り返し、`annotate_text_path` は折れ線に沿った配置で、**斜め**(接線角に 1 字ずつ回す)・**縦書き**(`upright=True`)・**改行**(`\n`)・経路に沿ったそろえ(`anchor="start"/"center"/"end"`)・線に触れさせない**法線オフセット**が使えます。字は色(役割名または RGB)に加えて、合成の **Bold / Italic** も指定できます。

使う op: `text_box`, `annotate_text_path`, `annotate_text_path_layout`, `annotate_table`, `annotate_table_layout`, `measure_text`

推奨パイプライン: [`measure_text`](ops/annotate/text/measure_text.md) → [`annotate_text_path_layout`](ops/annotate/paper/annotate_text_path_layout.md) → [`annotate_text_path`](ops/annotate/paper/annotate_text_path.md) → [`annotate_table_layout`](ops/annotate/paper/annotate_table_layout.md) → [`annotate_table`](ops/annotate/paper/annotate_table.md)

代替: [`text_box`](ops/annotate/text/text_box.md), [`annotate_panel_label`](ops/annotate/paper/annotate_panel_label.md)

限界: 本文組版ではない(縦中横・句読点寄せ無し)。Bold / Italic は合成。はみ出しと桁数不揃いは黙って切らず例外。

実寸校正: 描画のみ。`font_size` は px。実寸校正は不要。

動く例: `annotate_paper_tour`
