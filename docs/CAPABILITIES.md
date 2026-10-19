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

**収録 86 項目**

## 課題から引く(推奨パイプライン)

op 名は全部レジストリに実在し、**型(in → out)が前段から後段へ繋がる**ことを `tests/test_capabilities.py` が検査する。型の同一視は 4 組だけ (`image2d`=`image`、`mask`=`region`、`measurement`=`feature`=`scalar`)。引数で渡す量は型連鎖の外。詳細(代替・限界・実寸校正)は各項目へ。

| 課題 | 推奨パイプライン(順序つき) | 動く例 |
|---|---|---|
| [位置を合わせて重ねる](capabilities/align-and-stack.md) | `align_frames` → `drizzle_resample` → `frame_quality` | `poc_astro_photometry` |
| [配列で方向を測り、距離と速度を分ける](capabilities/beamforming-and-range-doppler.md) | `beamform_doa` → `range_doppler_map` → `range_doppler_peaks` | `poc_multibeam_bathymetry` |
| [領域を切り出して、選んで、数える](capabilities/blob-and-region.md) | `auto_threshold` → `blob_label` → `blob_select` → `blob_features` | `poc_cell_counting` |
| [クロマティック共焦点変位センサ(硝材の分散 → 較正表 → 戻りスペクトル → 高さ・厚さ)](capabilities/chromatic-confocal-sensor.md) | `chromatic_confocal_probe` → `chromatic_confocal_spectrum` → `chromatic_confocal_peaks` → `chromatic_confocal_readout` | `poc_chromatic_confocal` |
| [色を測る(XYZ / Lab / 色差)](capabilities/colour-and-delta-e.md) | `rgb_to_lab` → `delta_e_2000` | `poc_white_balance` |
| [多重反射・多重散乱・反復を収束まで回す —— 収束した証拠と残りの誤差を返し、収束しなければ値を出さない](capabilities/convergent-forward-models.md) | `iterate_fixed_point` → `conv_gci` | `converge_tour` |
| [圃場の RGB から作物と雑草を色と肌理で分け、雑草の被度を宣言した境で段階にする(学習器なし)](capabilities/crop-weed-cover-grade.md) | `superpixel_color_texture_features` → `fisher_lda_fit` → `fisher_lda_score` → `cover_ratio_grade` | `poc_weed_rice_ratio` |
| [X 線の 2 つのエネルギーで厚みと材質を分ける(デュアルエナジー / フォトンカウンティング: スペクトル → 窓 → 基底分解 → 実効 Z)](capabilities/dual-energy-xray-material-discrimination.md) | `xray_tube_spectrum` → `photon_counting_channels` → `basis_decomposition_crlb` → `basis_material_decompose` → `effective_z_map` | `poc_dual_energy_xray` |
| [結果を人が読める図にする](capabilities/figures-and-annotation.md) | `annotate_figure_grid` → `annotate_panel_label` → `annotate_scale_bar` → `annotate_colorbar` | `poc_colormap_readability` |
| [地球規模の座標に載せる(ECEF・高さの基準・局所 ENU)](capabilities/geodetic-frames.md) | `dem_geodetic_to_ecef` → `dem_ecef_to_geodetic` | `poc_geodetic_height_frames` |
| [良品を並べて「いつもと違う」を言う(良品統計の変動モデル、誤検出率の宣言つき)](capabilities/good-sample-variation-model.md) | `varmodel_alignment` → `varmodel_fit` → `varmodel_calibrate` → `varmodel_score` | `poc_good_sample_variation_model` |
| [格子干渉計(タルボ・ロー)で透過・微分位相・暗視野の 3 像を分ける](capabilities/grating-interferometry.md) | `talbot_grating_design` → `talbot_source_visibility` → `grating_step_period_estimate` → `grating_three_image_retrieve` → `darkfield_scatter_relation` → `dpc_integrate` | `poc_grating_interferometry` |
| [回折格子の分光器と顕微鏡の照明系(帯域の幅・smile / keystone・ケーラー / クリティカル・同軸のハーフミラー)](capabilities/grating-spectrometer-and-illumination.md) | `czerny_turner_design` → `spectrometer_bandpass` → `spectrometer_spectrum` | `poc_spectrometer_illumination` |
| [照明の円錐と観察の NA で、鏡面の小さな傾きを出す・消す(球冠の交わり → 傾きの帯 → 打痕・傷・梨地)](capabilities/illumination-cone-vs-na.md) | `solid_angle_light` → `solid_angle_boundaries` → `solid_angle_sweep` → `solid_angle_brightness` → `solid_angle_render` | `poc_illumination_cone_vs_na` |
| [工業用 OCT(干渉スペクトル → k 線形化 → 分散補償 → A / B スキャン → 群屈折率で層厚)](capabilities/industrial-oct.md) | `oct_design` → `oct_from_spectra` → `oct_bscan` → `oct_bscan_boundaries` → `oct_bscan_flatten` → `oct_layer_thickness` | `poc_industrial_oct` |
| [円形部品の内径を mm まで測る](capabilities/inner-diameter-in-mm.md) | `gaussian` → `otsu` → `area_center` → `create_metrology_model` → `add_metrology_object_circle_measure` → `apply_metrology_model` → `mm_per_px_from_reference` → `pixel_to_world` | `example_inner_diameter_mm` |
| [凹んだ部品の相互反射を、測光の真値を保ったまま収束まで数える(3-D の形態係数・漸進ラジオシティ・検査用の多重反射描画)](capabilities/interreflection-to-convergence.md) | `radiosity_patches` → `form_factor_matrix` | `poc_pocket_interreflection` |
| [地の色を知らずに線と領域を描く(反転色)](capabilities/inverted-colour-overlays.md) | `annotate_invert_visibility` → `annotate_invert` → `annotate_invert_path` | `annotate_paper_tour` |
| [間接 ToF(位相方式)の多周波アンラップと壊れ方(折り返し・多重反射・縁の混合・高調波・背景光)](capabilities/itof-multifreq.md) | `itof_noise_budget` → `itof_capture` → `itof_phase_amplitude` → `itof_unwrap_multifreq` | `poc_itof_multifreq` |
| [光学設計ファイル(.zmx の逐次処方を読む・書く・分類する)](capabilities/lens-prescription-files.md) | `lens_file_read` → `lens_file_system` → `paraxial_trace` → `spot_stats` → `lens_file_write` | `poc_lens_file_roundtrip` |
| [画素ごとの直交復調(ロックイン・時間相関イメージセンサ → 振幅・位相・直流、リング照明の法線・符号化照明の分離・熱波)](capabilities/lockin-demodulation.md) | `lockin_ring_synthesize` → `lockin_demodulate` → `lockin_ring_normals` | `poc_lockin_imaging` |
| [モアレで位置合わせ(ピッチの僅かに違う 2 枚の格子 → 縞の位相 → nm のずれ、差動と Talbot ギャップ)](capabilities/moire-alignment.md) | `moire_magnification` → `moire_mark_read` → `moire_phase_crlb` | `poc_moire_alignment` |
| [近赤外のハイパースペクトルで見た目が同じ異物を選別する(材料表の吸収帯 → 散乱層の反射 → InGaAs の帯域ごとの電子数)](capabilities/nir-hyperspectral-sorting.md) | `material_nir_absorption` → `kubelka_munk_reflectance` → `hyperspectral_capture` | `poc_hyperspectral_foreign_matter` |
| [非共軸の光学系(折り返しミラー・半透鏡・傾いた平板・シャインプルーフ・ゴースト)](capabilities/noncoaxial-optics.md) | `noncoaxial_system` → `noncoaxial_trace` → `image_orientation` → `ghost_analysis` → `noncoaxial_drawing` | `poc_noncoaxial_optics` |
| [OCR の前処理(傾き補正・局所 2 値化・行の切り出し)](capabilities/ocr-preprocessing.md) | `median` → `rotate_image` → `sk_sauvola` → `invert_region` → `remove_small` → `select_shape` → `dilation_rectangle1` | `gallery2d_segmentation` |
| [光の反射・屈折・干渉を計算する](capabilities/optics-and-materials.md) | `fresnel_dielectric` → `thin_film_reflectance` → `thin_film_rgb` | `glass_and_mirror_optics` |
| [光学系の図面(レンズ断面図・撮像系の設置図・単レンズの製作図を SVG / DXF で)](capabilities/optics-drawings.md) | `lens_section_drawing` → `drawing_svg` → `drawing_dxf` → `svg_entities` → `dxf_entities` | `poc_optics_drawings` |
| [1-D 信号の周期欠陥を見つける](capabilities/periodic-defects-in-1d-signals.md) | `smooth_funct_1d_gauss` → `bandpass` → `spectrum` → `find_peaks` → `peak_subbin` → `envelope` → `local_min_max_funct_1d` | `poc_web_roll_periodicity` |
| [光沢面の µm の凹みを縞の鏡像で測る(位相計測デフレクトメトリ: 縞 → 位相 → 傾き → 曲率)](capabilities/phase-measuring-deflectometry.md) | `deflectometry_rig` → `deflectometry_sensitivity` → `wrapped_phase` → `absolute_phase` → `deflectometry_phase_to_slope` → `slope_to_curvature` | `poc_phase_measuring_deflectometry` |
| [ピクセルシフト撮像(1 画素シフトで全色、半画素シフトで折り返しを消す、壊れる条件まで)](capabilities/pixel-shift-imaging.md) | `pixel_shift_resolution_budget` → `pixel_shift_pattern` → `pixel_shift_capture` → `pixel_shift_motion_mask` → `pixel_shift_merge` → `false_color_metric` | `poc_pixel_shift` |
| [3-D 点群から平面度を出す](capabilities/planarity-from-point-cloud.md) | `statistical_outlier_removal` → `ransac_plane` → `fit_plane_3d` → `distance_point_plane` | `geometry_metrology` |
| [点群をそのまま色の絵にする](capabilities/point-cloud-to-picture.md) | `points_render` | `points_render_basics` |
| [小さな点状の目標を見つけて、副画素で位置を出す](capabilities/point-target-detection.md) | `noise_sigma` → `star_detect` → `find_peaks` → `peak_subbin` | `poc_search_sweep_width` |
| [偏光 4 方向で鏡面反射を除く(誘電体と金属で分ける)](capabilities/polarisation-specular-removal.md) | `polarization_dolp_map` → `polarization_separate` → `polarization_stokes` → `stokes_analyze` → `specular_diffuse_split` | `example_polarization_metal` |
| [照明むら・ハイライト・遮蔽に強いテンプレート照合(明るさの変化の向きを符号にして比べ、決まらないテンプレートは拒否する)](capabilities/robust-code-matching.md) | `isc_match` → `ocm_match` | `poc_code_matching_breakdown` |
| [傷や突起に引きずられない平均線を引く(ロバストなガウス回帰・スプラインフィルタ、断面と面)](capabilities/robust-gaussian-spline-profile-filter.md) | `robust_gaussian_profile` → `profile_params` | `poc_robust_profile_filter` |
| [微細スクラッチを見つけて、幅を測る](capabilities/scratch-detection-and-width.md) | `gaussian` → `lines_gauss` → `select_contours` → `fit_line_contours` → `gen_measure_rectangle2` → `measure_pairs` → `table_px_to_mm` | `example_scratch_width` |
| [逐次光学設計の指標(理想レンズ面 → 囲みエネルギー → 子午/球欠 MTF → スルーフォーカス MTF)](capabilities/sequential-lens-design-metrics.md) | `lens_system` → `psf_from_opd` → `encircled_energy` → `energy_radii` → `mtf_tangential_sagittal` → `through_focus_mtf` | `optical_design_metrics` |
| [実物の画像から物理モデルの係数を合わせる(sim-to-real 較正)—— 画像が決めない係数には数を出さず、決まる組み合わせと理由を返す](capabilities/sim-to-real-calibration.md) | `simcal_model` → `simcal_observe` → `simcal_fit` → `simcal_identifiability` → `simcal_report` | `simcal_tour` |
| [画像から寸法をサブピクセルで測る](capabilities/subpixel-2d-metrology.md) | `gen_measure_rectangle2` → `measure_pos` → `measure_pairs` → `table_px_to_mm` | `poc_dimensional_inspection` |
| [表面の凹凸欠陥を、照明の設計から検出まで](capabilities/surface-defects-with-lighting.md) | `illumination_design` → `lighting_sweep` → `light_source` → `defect_contrast` → `irradiance_map` → `illumination_uniformity` → `photometric_stereo` → `integrate_normals` → `surface_form_error` → `bothat` → `auto_threshold` → `remove_small` | `illumination_design_demo` |
| [TDI ラインスキャンとラインスキャン用レンズ(段数と SNR → 同期ずれの MTF → 像高ごとの照度と MTF)](capabilities/tdi-linescan-and-lens.md) | `tdi_snr` → `tdi_sync_mtf` → `linescan_lens_example` → `lens_field_profile` → `linescan_lens_columns` → `linescan_acquire` | `poc_tdi_linescan` |
| [テレセントリックレンズと寸法計測(主光線の傾き → 高さで変わる倍率 → ケラレとぼけ)](capabilities/telecentric-metrology.md) | `telecentric_lens` → `chief_ray_angle` → `telecentricity_error` → `magnification_vs_depth` → `defocus_spot_vs_depth` → `vignetting_vs_field` | `poc_telecentric_metrology` |
| [仮想の透過電子顕微鏡(電子の波長 → CTF → 位相コントラストの像 → Thon リングから焦点外れを推定 → 補正)](capabilities/tem-phase-contrast-and-ctf.md) | `tem_power_spectrum` → `tem_ctf_estimate` → `tem_ctf_correct` | `poc_tem_ctf_thon_rings` |
| [位置決め(テンプレート照合で測定線を追従させる)](capabilities/template-alignment.md) | `gaussian` → `ncc_locate` → `shape_locate` → `create_metrology_model` → `add_metrology_object_circle_measure` → `align_metrology_model` → `apply_metrology_model` | `poc_template_tracking` |
| [地形の傾き・水の流れ・見通しを測る](capabilities/terrain-and-visibility.md) | `dem_fill_sinks` → `dem_slope` → `dem_aspect` → `dem_flow_direction` → `dem_viewshed` | `poc_dem_terrain` |
| [画像の上に、文字と表を置きたい場所へ置く](capabilities/text-and-tables-on-images.md) | `measure_text` → `annotate_text_path_layout` → `annotate_text_path` → `annotate_table_layout` → `annotate_table` | `annotate_paper_tour` |
| [薄膜の膜厚を分光反射率で測る(転送行列 → 干渉色 → FFT・モデルあてはめ・膜厚マップ)](capabilities/thin-film-reflectometry.md) | `multilayer_reflectance` → `film_thickness_fft` → `film_thickness_fit` → `film_thickness_map` | `poc_thin_film_reflectometry` |
| [投影から断面を再構成する(CT)](capabilities/tomography-reconstruction.md) | `radon_transform` → `ring_artifact_remove` → `beam_hardening_correct` → `fbp_volume` → `vol_rle_components` → `vol_rle_volume` | `poc_ct_fidelity` |
| [振動と音から異常を診断する](capabilities/vibration-and-acoustics.md) | `bandpass` → `envelope` → `envelope_spectrum` → `find_peaks` → `bearing_defect_frequencies` | `poc_bearing_diagnosis` |
| [仮想 SEM —— 電子と固体の相互作用をモンテカルロで解き、加速電圧・検出器・帯電で像と線幅がどう変わるかを実測値で採点しながら見る](capabilities/virtual-sem-monte-carlo.md) | `material_electron_properties` → `sem_electron_mc` → `sem_line_profile` → `sem_cd_measure` → `sem_image` | `poc_virtual_sem_kv_cd_bse` |
| [シルエットから立体を彫り出す(視体積交差)](capabilities/visual-hull-from-silhouettes.md) | `synthesize_silhouette` → `visual_hull` → `vol_rle_components` → `vol_rle_volume` | `space_carving` |
| [3-D スキャンから体積・土量を出す](capabilities/volume-from-3d-scan.md) | `vol_rle_components` → `vol_rle_volume` → `mesh_volume` | `poc_stockpile_volume` |

レシピ欄(推奨パイプライン / 代替 / 限界 / 実寸校正)がまだ無い項目が 33 件あります(下の各項目。`gen_capabilities_index.NO_RECIPE_YET` に理由つきで名指し)。

## 測る (31)

### [平面ターゲットの多視点から内部行列 K を推定する(Zhang 法)](capabilities/camera-intrinsics-calibration.md)

チェッカーボードのような平面ターゲットを角度を変えて何枚か撮り、その角点の対応だけからカメラの内部行列 `K`(焦点距離 fx,fy・主点 cx,cy・skew)を推定します。`camera_calibration(object_points, image_points_list)` は Zhang 法(平面ホモグラフィから内部拘束を 2 本ずつ集めて解く)で `K` を返します。回収した `K` は歪み係数の推定(能力ノート `estimate-lens-distortion`)や `undistort_image`、PnP・三角測量にそのまま渡せます。`object_points` は平面上の `(x, y)` 座標、`image_points_list` は各視点の `(row, col)` 画素対応です。

使う op: `camera_calibration`, `estimate_distortion`, `intrinsic_matrix`, `decompose_intrinsics`

動く例: `camera_intrinsics_calibration`

### [複素平面を「面」で見る(位相彩色・吸引域・脱出時間・翼まわりの流れ)](capabilities/complex-plane-fields.md)

複素解析の図を描きます —— 有理関数の位相彩色、ニュートン法の吸引域、マンデルブロ/ジュリア集合の脱出時間、ジューコフスキー翼まわりのポテンシャル流。既存の複素解析 op が**閉曲線の上**(積分・巻き数・ローラン係数・等角写像)を扱うのに対して、この層は**領域の上**を扱います。

使う op: `cplx_plane_grid`, `cplx_rational_field`, `cplx_domain_colour`, `cplx_newton_basins`, `cplx_escape_time`, `mandelbrot_interior`, `potential_flow_joukowski`, `joukowski_circulation`

動く例: `poc_complex_plane_fields`

### [周期パターンが標本化格子で折り返す距離と、縞の上で狂う衝突時間を閉形式で測る(複眼・検査カメラ)](capabilities/compound-eye-aliasing-and-ttc.md)

周期 P の縞を間隔 Δφ の格子で標本化すると、距離 d > P cos²θ/(√3 Δφ)(六角、正方は 2Δφ)で縞は折り返してモアレになります。`sampling_alias_distance` はこの距離と、ナイキストに残るコントラスト(MTF)を閉形式で返します —— Δφ を画素の瞬時視野、P を検査対象(ディスプレイ・メッシュ・織物・網点)のピッチと読めば、**検査カメラの作動距離の設計規則**です。`fly_view_plane_texture` は正面の周期面を六角個眼格子 + ガウス受容角の下で**解析的に**積分し(画像を再標本化しない)、`fly_t4t5_field(model="hr")` に渡すと相関型運動検出器(Hassenstein–Reichardt)の符号反転 sin(2πΔφ/λ) がどの個眼で起きるかを数えられます。`fly_expansion_readout` は眼全体の流れから衝突時間 τ を読み、縦縞のアパーチャ効果が放射当てはめ・発散とも**厳密に 2τ** を返すことを示します。`traj_tau_dot` は実測の 3-D 軌跡から距離・接近速度・τ・τ̇(Lee 1976)を出します。

使う op: `sampling_alias_distance`, `fly_view_plane_texture`, `fly_expansion_readout`, `fly_vogel_lattice`, `lattice_moire_peak`, `traj_tau_dot`, `fly_t4t5_field`, `fly_tau_from_expansion`

動く例: `poc_zebra_stripes_fly_eye`

### [カメラのデータシートの数を EMVA 1288 の手順で測り直し、カメラの中の前処理がその数をどれだけ動かすかを見る(Linear と General)](capabilities/emva1288-camera-datasheets.md)

画像センサ・カメラのデータシートの量子効率 η・システムゲイン K・暗雑音・飽和容量・最大 SNR・ダイナミックレンジ・DSNU・PRNU は、 EMVA 1288 Release 4.0 の手順で測った数です。ここではその手順を op にし、**値を仕込んだ合成センサ**で手順そのものを確かめます。 式は Release 4.0 Linear / General(2021-06-16、無償で公開されている本文)から写し、docstring に節と式の番号を書いてあります。

使う op: `emva_pair_statistics`, `emva_photon_transfer`, `emva_quantum_efficiency`, `emva_spatial_nonuniformity`, `emva_highpass`, `emva_spectrogram`, `emva_ptc_linearity_check`, `emva_bspline_regression`, `emva_noise_whiteness`, `emva_filter_distortion`, `emva_general_sensitivity`, `emva_general_nonuniformity`, `emva_general_relative_qe`

動く例: `poc_emva1288_sensor`, `poc_emva1288_in_camera_processing`

### [本来まっすぐな線から歪み係数を推定する(plumb-line、チェッカー不要)](capabilities/estimate-lens-distortion.md)

`undistort_image(image, K, dist)` は歪み係数 `dist` が**与えられている**前提でした。`estimate_distortion(lines, K)` はその上流 —— 係数を**測る**側です。本来まっすぐな線(印刷された直線・建物のエッジ・定規)がレンズで曲がった点列だけから、Brown–Conrady 係数 `[k1, k2, p1, p2, k3]` を推定します。**対応点もチェッカーボードも既知の間隔も要りません** —— 各線がまっすぐだと分かっていればよい(Discorpy が使う線パターンの考え方を、このライブラリの `(x, y)` 規約で)。推定した `dist` は `undistort_image` にそのまま渡せます。

使う op: `estimate_distortion`, `undistort_image`, `distort_points`, `undistort_points`

動く例: `estimate_lens_distortion`

### [地球規模の座標に載せる(ECEF・高さの基準・局所 ENU)](capabilities/geodetic-frames.md)

緯度・経度・高さを、地球中心直交座標(ECEF)・局所 ENU・別の測地成果(datum)へ移します。**高さは 2 つある**(GNSS が返す楕円体高 h と、地図・設計図が使う標高 H)ので、どちらの基準の量なのかを op に書かせ、`h − H − N` の残差で取り違えを検出します。

使う op: `dem_geodetic_to_ecef`, `dem_ecef_to_geodetic`, `dem_geoid_height`, `dem_height_frame_convert`, `dem_height_frame_residual`, `dem_datum_shift_3param`, `dem_enu_from_geodetic`, `dem_geodetic_from_enu`

推奨パイプライン: [`dem_geodetic_to_ecef`](ops/dem/geodesy/dem_geodetic_to_ecef.md) → [`dem_ecef_to_geodetic`](ops/dem/geodesy/dem_ecef_to_geodetic.md)

代替: [`dem_geoid_height`](ops/dem/geodesy/dem_geoid_height.md), [`dem_height_frame_convert`](ops/dem/geodesy/dem_height_frame_convert.md), [`dem_height_frame_residual`](ops/dem/geodesy/dem_height_frame_residual.md), [`dem_enu_from_geodetic`](ops/dem/geodesy/dem_enu_from_geodetic.md), [`dem_geodetic_from_enu`](ops/dem/geodesy/dem_geodetic_from_enu.md), [`dem_datum_shift_3param`](ops/dem/geodesy/dem_datum_shift_3param.md), [`dem_geodetic_slope`](ops/dem/geodesy/dem_geodetic_slope.md)

限界: epoch の移動(プレート運動)と 7 パラメータのヘルマート変換は**未実装**(`dem_datum_shift_3param` は平行移動 3 つだけ)。ジオイドモデルは計算せず公開格子を引くだけ。楕円体高と標高の取り違えは日本付近で 30〜40 m 静かにずれる(`poc_geodetic_height_frames`)。

実寸校正: 画素は関係しない。高さの基準面(楕円体か標高か)を必ず明示し、`dem_height_frame_convert` で `H = h - N`(N は `dem_geoid_height` が公開格子から引く)。混ざった表は `dem_height_frame_residual` の残差で見張り、公開測量成果 523 点で答え合わせ(`poc_geodetic_benchmarks_real`)。

動く例: `poc_geodetic_height_frames`, `poc_geodetic_benchmarks_real`, `dem_geodesy_tour`

### [格子干渉計(タルボ・ロー)で透過・微分位相・暗視野の 3 像を分ける](capabilities/grating-interferometry.md)

X 線(や可視光)の透過像は「どれだけ吸われたか」しか写しません。周期数 µm の格子を 2 枚(線源が大きいなら 3 枚)入れ、どちらかを 1 周期ずらしながら数枚撮ると、各画素で縞の正弦が取れます。その**平均**が透過(吸収)、**位相のずれ**が微分位相(屈折角)、**振幅の落ち方**が暗視野(画素より小さい構造からの小角散乱)です。吸収がまわりとほとんど同じ繊維・粉・微小な割れ・気孔の群が、暗視野でははっきり出ます。

使う op: `talbot_grating_design`, `talbot_carpet`, `talbot_source_visibility`, `grating_stepping_simulate`, `grating_step_period_estimate`, `grating_three_image_retrieve`, `darkfield_scatter_relation`, `dpc_integrate`

推奨パイプライン: [`talbot_grating_design`](ops/optics/grating_interf/talbot_grating_design.md) → [`talbot_source_visibility`](ops/optics/grating_interf/talbot_source_visibility.md) → [`grating_step_period_estimate`](ops/optics/grating_interf/grating_step_period_estimate.md) → [`grating_three_image_retrieve`](ops/optics/grating_interf/grating_three_image_retrieve.md) → [`darkfield_scatter_relation`](ops/optics/grating_interf/darkfield_scatter_relation.md) → [`dpc_integrate`](ops/optics/grating_interf/dpc_integrate.md)

代替: [`talbot_carpet`](ops/optics/grating_interf/talbot_carpet.md), [`grating_stepping_simulate`](ops/optics/grating_interf/grating_stepping_simulate.md), [`wrapped_phase`](ops/3d/structured_light/wrapped_phase.md), [`moire_talbot_gap`](ops/optics/moire_align/moire_talbot_gap.md), [`angular_spectrum_propagate`](ops/optics/wave/angular_spectrum_propagate.md)

限界: 位相ステップは 1 次の正弦だけを見る(格子の高次の調和・ステップの位置の揺れ・検出器の点広がりは模型に無い)。暗視野から散乱角へはガウス散乱の近似。単色の順モデルなので、多色の線源で吸収が平均のエネルギーを上げて可視度が落ちる効果は無い。折り返しは隣との跳びでしか見えない。

実寸校正: 1 周期のステップ数 P は空気(基準)の区画で grating_step_period_estimate から決める。基準と試料の露光の比は reference_exposure に渡す。屈折角・位相への換算は分析格子の周期 p2 と距離 d、波長で決まる(talbot_grating_design の値か実測)。

動く例: `poc_grating_interferometry`

### [工業用 OCT(干渉スペクトル → k 線形化 → 分散補償 → A / B スキャン → 群屈折率で層厚)](capabilities/industrial-oct.md)

塗装・コンフォーマルコート・接着層・多層フィルムの**層の並び**と、層の中の空洞・剥離を、壊さずに深さ方向で見ます。分光器型(SD-OCT)は 1 回の露光の干渉スペクトルを、波長掃引型(SS-OCT)は掃引の時間波形を、波数 k に等間隔に並べ直して FFT すると、深さごとの反射の振幅(A スキャン)になります。横に走査すると断面(B スキャン)です。

使う op: `oct_design`, `oct_dispersion_broadening`, `oct_interferogram`, `oct_bscan_simulate`, `oct_from_spectra`, `oct_k_linearize`, `oct_dispersion_estimate`, `oct_dispersion_compensate`, `oct_ascan`, `oct_bscan`, `oct_layer_thickness`, `oct_bscan_boundaries`, `oct_bscan_flatten`

推奨パイプライン: [`oct_design`](ops/optics/oct/oct_design.md) → [`oct_from_spectra`](ops/optics/oct/oct_from_spectra.md) → [`oct_bscan`](ops/optics/oct/oct_bscan.md) → [`oct_bscan_boundaries`](ops/optics/oct/oct_bscan_boundaries.md) → [`oct_bscan_flatten`](ops/optics/oct/oct_bscan_flatten.md) → [`oct_layer_thickness`](ops/optics/oct/oct_layer_thickness.md)

代替: [`oct_interferogram`](ops/optics/oct/oct_interferogram.md), [`oct_bscan_simulate`](ops/optics/oct/oct_bscan_simulate.md), [`oct_ascan`](ops/optics/oct/oct_ascan.md), [`oct_dispersion_estimate`](ops/optics/oct/oct_dispersion_estimate.md), [`material_group_index`](ops/optics/fiber/material_group_index.md), [`csi_design`](ops/interferometry/design/csi_design.md)

限界: 散乱は 1 回散乱(Beer–Lambert)の模型まで(多重散乱の背景は無い)。点像の幅の 1.4 倍(÷ n_g)より薄い層・雑音の 12 dB 上に立たない下の面・谷から 1 dB 立たない面は拒否。自己相関の幽霊は位相をずらした 2 枚か試料腕だけのスペクトルが無いと消えない。

実寸校正: 深さの刻みは分光器の波長の較正(画素ごとの波長)で決まり、物理厚は光学厚 ÷ 群屈折率。群屈折率は材料表の名前か、厚さの既知の試料で校正した値を使う(位相屈折率で割ると 1〜2 % 厚く出る)。

動く例: `poc_industrial_oct`

### [円形部品の内径を mm まで測る](capabilities/inner-diameter-in-mm.md)

穴・リング・ピンの内径を、粗い中心出し → サブピクセルの円当てはめ → 実寸校正 → mm、まで一気通貫で出します。文書だけを渡した AI は `measure_pairs` / `apply_metrology_model` で **px のまま止まっていた**(2026-09-15)ので、最後の 2 段(`mm_per_px_from_reference` / `pixel_to_world`)を op として型連鎖に置いてあります。

使う op: `add_metrology_object_circle_measure`, `apply_metrology_model`, `mm_per_px_from_reference`, `pixel_to_world`

推奨パイプライン: [`gaussian`](ops/2d/smoothing/gaussian.md) → [`otsu`](ops/2d/segmentation/otsu.md) → [`area_center`](ops/2d/features/area_center.md) → [`create_metrology_model`](ops/measure1d/model/create_metrology_model.md) → [`add_metrology_object_circle_measure`](ops/measure1d/model/add_metrology_object_circle_measure.md) → [`apply_metrology_model`](ops/measure1d/apply/apply_metrology_model.md) → [`mm_per_px_from_reference`](ops/measure1d/scale/mm_per_px_from_reference.md) → [`pixel_to_world`](ops/measure1d/scale/pixel_to_world.md)

代替: [`gen_measure_arc`](ops/measure1d/caliper/gen_measure_arc.md), [`measure_pos`](ops/measure1d/caliper/measure_pos.md), [`hx_fit_circle_contour`](ops/2d/halcon_ext/hx_fit_circle_contour.md), [`cv_hough_circles`](ops/2d/features/cv_hough_circles.md), [`hough_circle_trans`](ops/2d/features/hough_circle_trans.md), [`table_px_to_mm`](ops/measure1d/scale/table_px_to_mm.md)

限界: 参照半径が実物から ±6 px(`measure_length` 既定)より外れると縁が見つからない(+6.5 px で fail、実測)。丸い縁は −σ²/ρ だけ小さく出る。`n` は円周 3 px に 1 点で頭打ち(それ以上は独立に効かない、実測)。

実寸校正: 既知径の的(リングゲージ・基準穴)を**同じ円 op で**測り `mm_per_px_from_reference(2·radius_px, known_mm)` → `pixel_to_world(2·radius_px, mm_per_px)`。公称倍率は使わない。

動く例: `example_inner_diameter_mm`, `poc_dimensional_inspection`, `poc_real_coin_metrology`

### [間接 ToF(位相方式)の多周波アンラップと壊れ方(折り返し・多重反射・縁の混合・高調波・背景光)](capabilities/itof-multifreq.md)

光を周波数 f で強度変調し、戻り光との相関を 4 段(K 段)の位相で測る間接 ToF を、生信号から距離まで通し、壊れるところまで再現します。`itof` の 8 本は `opsoptics` の族 `itof` です。

使う op: `itof_capture`, `itof_phase_amplitude`, `itof_noise_budget`, `itof_unwrap_multifreq`, `itof_unwrap_error_rate`, `itof_multipath_separate`, `itof_flying_pixel_mask`, `itof_wiggling_correct`

推奨パイプライン: [`itof_noise_budget`](ops/optics/itof/itof_noise_budget.md) → [`itof_capture`](ops/optics/itof/itof_capture.md) → [`itof_phase_amplitude`](ops/optics/itof/itof_phase_amplitude.md) → [`itof_unwrap_multifreq`](ops/optics/itof/itof_unwrap_multifreq.md)

代替: [`dtof_cube_simulate`](ops/photon/dtof/dtof_cube_simulate.md), [`dtof_cube_depth`](ops/photon/dtof/dtof_cube_depth.md), [`tof_transport_depth`](ops/optics/light_transport/tof_transport_depth.md), [`residue_crt`](ops/residue/robust/residue_crt.md)

限界: 場面の強さは Lambert と逆二乗だけ(鏡面・迷光・画素間のクロストークなし)。行列ペンシルは等間隔の周波数専用で、帯域の分解能 c/(2FΔf) より近い 2 経路は雑音があると分けられない。雑音の閉形式は SNR ≥ 3 の近似(PoC)。

実寸校正: 距離は周期 c/(2f) の剰余から出るので尺度は光速と周波数で決まる。実機では段の位相の符号と原点・系の遅延(距離のオフセット)・周波数の正確な値を較正する(オフセットは itof_wiggling_correct の較正の定数項)。

動く例: `poc_itof_multifreq`

### [レーザー光切断の誤差の床はスペックルが決める(コヒーレント結像・スペックルの統計・三角測量の不確かさ)](capabilities/laser-speckle-floor.md)

レーザーで照らした粗面を、**コヒーレント結像**で撮ります。面の凹凸が波長より大きいと反射光の位相は場所ごとにでたらめになり、カメラの開口(瞳)で帯域を切られた**複素振幅**が干渉して粒々の模様(スペックル)になります。光切断やレーザー変位計の高さの誤差の下限は、画素の雑音ではなくこの粒で決まります。

使う op: `coherent_image`, `speckle_field`, `speckle_statistics`, `laser_line_coherent`, `triangulation_speckle_limit`, `speckle_reduction`

動く例: `poc_laser_line_speckle_floor`

### [凹みの相互反射で縞投影と ToF が外れる量を、撮る前に予測する(大域光輸送・直接と大域の分離・マイクロ位相シフト)](capabilities/light-transport.md)

縞投影(位相シフト)も ToF も、「画素に届く光は 1 つの経路から来た」と仮定して位相を距離に変えます。V 溝・加工ポケットの内角・はんだフィレット・部屋の隅のような凹んだ形では、片方の面で反射した光が向かいの面を照らし、画素には**別の場所の位相を持った光**が混ざります(相互反射 = 大域成分)。光沢も金属も要らず、**白い Lambert 面でも凹んでいれば起きます**。このページの op は、その光の行き来を輸送行列として明示的に解き、誤差を閉形式で予測します。

使う op: `groove_profile`, `form_factors_2d`, `transport_matrix_radiosity`, `high_frequency_patterns`, `render_transport`, `separate_direct_global`, `fringe_multipath_phase_error`, `predict_fringe_phase_error`, `micro_phase_decode`, `tof_multipath_phase`, `tof_transport_depth`

動く例: `poc_interreflection_fringe_error`

### [画素ごとの直交復調(ロックイン・時間相関イメージセンサ → 振幅・位相・直流、リング照明の法線・符号化照明の分離・熱波)](capabilities/lockin-demodulation.md)

変調した光や熱で場面を照らし、画素ごとに参照信号と相関を取ると、画像でなく「参照に追従する成分の振幅と位相」と直流が出ます。`lockin` の 9 本は、画像列 (T, H, W) に対するその直交復調と 3 つの使い方です。`lockin_demodulate` は振幅・位相・直流・同相・直交と窓の漏れを返し(`lockin_amplitude` / `lockin_phase` は 2 次元の画像だけ)、窓は宣言します: 矩形窓は参照の周期が整数のときだけ厳密で、そうでなければ拒否し、hann なら漏れの大きさを表で返します。`lockin_noise_floor` は白色雑音の下の振幅・位相の雑音を SN 比から閉形式(位相は Rice の分布)で与えます。

使う op: `lockin_demodulate`, `lockin_amplitude`, `lockin_phase`, `lockin_noise_floor`, `lockin_walsh_codes`, `lockin_separate`, `lockin_ring_synthesize`, `lockin_ring_normals`, `lockin_thermal_wave`

推奨パイプライン: [`lockin_ring_synthesize`](ops/optics/lockin/lockin_ring_synthesize.md) → [`lockin_demodulate`](ops/optics/lockin/lockin_demodulate.md) → [`lockin_ring_normals`](ops/optics/lockin/lockin_ring_normals.md)

代替: [`lockin_amplitude`](ops/optics/lockin/lockin_amplitude.md), [`lockin_phase`](ops/optics/lockin/lockin_phase.md), [`lockin_separate`](ops/optics/lockin/lockin_separate.md), [`lockin_walsh_codes`](ops/optics/lockin/lockin_walsh_codes.md), [`lockin_noise_floor`](ops/optics/lockin/lockin_noise_floor.md), [`lockin_thermal_wave`](ops/optics/lockin/lockin_thermal_wave.md)

限界: 法線の復元は朗伯面で、輪の光源のどれも影にならない画素(傾き < 90° − 天頂角)だけ有効(他は NaN と valid = False)。光沢・相互反射では式が崩れる。熱波は定常状態の 1 次元モデル(横拡散と立ち上がりの過渡は無し)で、位相は L/μ = 1.963 で最大になるのでそれより深い欠陥は位相から一意に読めない。矩形窓は周期が整数のときだけ(そうでなければ拒否)。

実寸校正: 位相は参照の周波数と標本化の時刻(fps)だけで決まり、画素の大きさや照度の絶対値は要らない。振幅は照明・反射率・放射率の掛け算を含むので、反射率を消したいときは A / 直流(法線)か位相(熱波)を使う。参照の周波数が 10 % ずれると振幅が落ちる(sinc)ので、参照は実測の周波数に合わせる。

動く例: `poc_lockin_imaging`

### [その数字のうち、いくつが測り方のものか(ゲージ R&R と測定の不確かさ)](capabilities/measurement-system-and-uncertainty.md)

工程のばらつきを見る管理図も工程能力も、**測定のばらつきを含んだままの数字**を見ています。この層はそれを分けます —— 総変動のうち何割が部品どうしの差で、何割が「測るという行為」の差なのか。そして 1 回の測定について、成分ごとの不確かさを合成して報告可能な形にします。

使う op: `msa_anova_table`, `msa_gauge_rr`, `msa_bias_linearity`, `msa_attribute_agreement`, `gum_standard_uncertainty`, `gum_propagate`, `gum_expanded`, `gum_monte_carlo`, `gum_validate`, `spc_capability`, `spc_xbar_r`

動く例: `poc_measurement_system_analysis`

### [モアレで位置合わせ(ピッチの僅かに違う 2 枚の格子 → 縞の位相 → nm のずれ、差動と Talbot ギャップ)](capabilities/moire-alignment.md)

リソグラフィやナノインプリントでは、マスクとウェハを nm の精度で重ねます。マスク側にピッチ p_m、ウェハ側に僅かに違うピッチ p_w の格子を置くと、2 枚はカメラのぼけで見えなくても、重ねた像には周期 P = p_m p_w / |Δp| の縞(モアレ)が現れ、ウェハが δ 動くと縞は M = p_m / |Δp| 倍の距離を動きます(マスクが動くなら p_w / |Δp| 倍)。`moirealign` の 8 本はその設計・合成・読み取り・限界を受け持ちます。

使う op: `moire_magnification`, `moire_talbot_gap`, `moire_overlay_image`, `moire_phase`, `moire_phase_to_shift`, `moire_differential_shift`, `moire_mark_read`, `moire_phase_crlb`

推奨パイプライン: [`moire_magnification`](ops/optics/moire_align/moire_magnification.md) → [`moire_mark_read`](ops/optics/moire_align/moire_mark_read.md) → [`moire_phase_crlb`](ops/optics/moire_align/moire_phase_crlb.md)

代替: [`moire_phase`](ops/optics/moire_align/moire_phase.md), [`moire_phase_to_shift`](ops/optics/moire_align/moire_phase_to_shift.md), [`moire_differential_shift`](ops/optics/moire_align/moire_differential_shift.md), [`moire_overlay_image`](ops/optics/moire_align/moire_overlay_image.md), [`moire_talbot_gap`](ops/optics/moire_align/moire_talbot_gap.md), [`absolute_phase`](ops/3d/structured_light/absolute_phase.md)

限界: 0.1 nm 級の数字は白色雑音だけの床(`moire_phase_crlb`、PoC で Monte-Carlo と比 1.00)。実機の精度(公表値 10〜30 nm)を決めるマークの非対称・ギャップと傾き・レジスト膜はモデルに無い。読みは格子 1 ピッチ(差動は p_m p_w / (p_m + p_w))で折り返す。

実寸校正: ずれの尺度は格子のピッチ(リソグラフィの寸法)で、カメラの倍率ではない —— 差動のマークならカメラの倍率 2 % の誤りは読みに入らない(PoC)。どちらの格子が動くかで拡大率が違う(ウェハ 50・マスク 51)ので取り違えると 2 % 狂う。

動く例: `poc_moire_alignment`

### [光沢面の µm の凹みを縞の鏡像で測る(位相計測デフレクトメトリ: 縞 → 位相 → 傾き → 曲率)](capabilities/phase-measuring-deflectometry.md)

塗装面・カバーガラス・鏡面研磨品の凹み、うねり、研磨ムラを、面の前に置いた画面の縞の**鏡像**から測ります。光沢面は鏡なので、照明を当てて撮った写真には照明しか写らず、深さ数 µm の凹みはまず見えません。画面に位相シフト縞を出して鏡像を撮ると、面が α 傾くだけで反射は 2α 曲がり、距離 d 先の画面では 2dα ずれます。傾きを、画面までの距離をてこにして測る方法です(Knauer ら 2004)。

使う op: `deflectometry_rig`, `deflectometry_screen_pattern`, `deflectometry_render`, `deflectometry_phase_to_slope`, `slope_to_curvature`, `deflectometry_sensitivity`

推奨パイプライン: [`deflectometry_rig`](ops/specular/deflectometry/deflectometry_rig.md) → [`deflectometry_sensitivity`](ops/specular/deflectometry/deflectometry_sensitivity.md) → [`wrapped_phase`](ops/3d/structured_light/wrapped_phase.md) → [`absolute_phase`](ops/3d/structured_light/absolute_phase.md) → [`deflectometry_phase_to_slope`](ops/specular/deflectometry/deflectometry_phase_to_slope.md) → [`slope_to_curvature`](ops/specular/deflectometry/slope_to_curvature.md)

代替: [`deflectometry_render`](ops/specular/deflectometry/deflectometry_render.md), [`deflectometry_screen_pattern`](ops/specular/deflectometry/deflectometry_screen_pattern.md), [`sfp_height`](ops/optics/shape_from_polarization/sfp_height.md), [`integrate_normals`](ops/3d/photometric/integrate_normals.md)

限界: 1 台のカメラと 1 枚の画面では面の高さと傾きを分けられない(面が Δz ずれると傾きが Δz sin θ / d 狂う)。画面の画素の格子と液晶の階調の非線形は入っていない。無反射コートの無いカバーガラスでは凹みが 1/4 の深さにしか見えない(PoC の門)。

実寸校正: 較正の op は無く、装置の幾何(入射角・カメラと画面までの距離 d・画面の画素ピッチ)は実測して `deflectometry_rig` に入れる。傾きは画面上のずれ / (2d) なので、d の誤りはそのまま傾きと曲率の比の誤りになる。

動く例: `poc_phase_measuring_deflectometry`

### [3-D 点群から平面度を出す](capabilities/planarity-from-point-cloud.md)

定盤・フランジ・基板・床など「平らであるべき面」の点群から、外れ点を除き、頑健に平面を当てはめ、各点の面からの距離で**平面度**(PV・RMS)を出します。距離は符号つきなので、反り(低次)と局所の凹凸(高次)を分けて読めます。

使う op: `ransac_plane`, `fit_plane_3d`, `distance_point_plane`, `statistical_outlier_removal`

推奨パイプライン: [`statistical_outlier_removal`](ops/3d/preprocess/statistical_outlier_removal.md) → [`ransac_plane`](ops/3d/robust_fit/ransac_plane.md) → [`fit_plane_3d`](ops/3d/geometry/fit_plane_3d.md) → [`distance_point_plane`](ops/3d/geometry/distance_point_plane.md)

代替: [`fit_plane3`](ops/3d/geometry/fit_plane3.md), [`plane_segmentation`](ops/3d/segment/plane_segmentation.md), [`radius_outlier_removal`](ops/3d/preprocess/radius_outlier_removal.md), [`estimate_normals`](ops/3d/curvature/estimate_normals.md), [`surface_form_error`](ops/3d/surface_fit/surface_form_error.md)

限界: 平面度 PV は雑音の最大値統計で、完全に平らな面でも雑音だけで許容の 70 % を使う(RMS なら 2.03 mm 対 PV 4.89 mm)。最小二乗は外れ点 10 % で真値の 11 倍外れ、RANSAC は 45 % まで持って 55 % で別の面へ乗り換える。合わせ(ICP)は反りを吸って偽のへこみを作る。

実寸校正: 点群の座標系の単位(m / mm)を揃える。センサの測距雑音 σ を先に測り、PV は σ√(2 ln N) の床と比べて読む。

動く例: `geometry_metrology`, `poc_bump_coplanarity`, `poc_scan_to_bim_asbuilt`

### [どの大きさなら見つかるか(検出確率 POD と a90/95、MIL-HDBK-1823A)](capabilities/probability-of-detection.md)

検査の性能を「この大きさの傷は何 % の確率で見つかるか」で言います。欠陥の大きさ `a` と検査系の応答 `â`(あるいは見つけた/見落とした)の組から、POD(a) 曲線・a50・a90・**a90/95**(90 % の確率で見つかると 95 % の信頼で言える最小の大きさ)と、無欠陥部位の応答から誤検出確率を出します。手順は非破壊検査の信頼性評価の公開ハンドブック MIL-HDBK-1823A のとおりです。

使う op: `pod_ahat_fit`, `pod_from_ahat`, `pod_hitmiss_fit`, `pod_false_call`, `pod_decision_tradeoff`, `light_source`, `detectability_limit`

動く例: `poc_pod_lighting`

### [傷や突起に引きずられない平均線を引く(ロバストなガウス回帰・スプラインフィルタ、断面と面)](capabilities/robust-gaussian-spline-profile-filter.md)

粗さは断面(または面)から平均線(うねり)を引いて残りを測ります。普通のガウスフィルタは深い傷に引かれて平均線が傷の側へ凹み、**傷の両側の健全な面が山に見えます**(PoC の実測で、傷の脇の粗さが真値の 2.5 倍)。`roughness` 族の新しい 3 本は、Tukey の biweight で傷の重みを下げながら反復し、平均線を傷から守ります。

使う op: `robust_gaussian_profile`, `robust_spline_profile`, `robust_gaussian_surface`, `surface_filter`

推奨パイプライン: [`robust_gaussian_profile`](ops/roughness/prepare/robust_gaussian_profile.md) → [`profile_params`](ops/roughness/measure/profile_params.md)

代替: [`robust_spline_profile`](ops/roughness/prepare/robust_spline_profile.md), [`surface_filter`](ops/roughness/prepare/surface_filter.md), [`robust_gaussian_surface`](ops/roughness/prepare/robust_gaussian_surface.md)

限界: 傷の標本が 4 割を超えると平均線が傷側へ破綻する(合成断面の実測で 35 % までは雑音の床、40 % で 3.5 µm)。外れ値の無い断面でもロバスト版は線形と一致しない(biweight が雑音の裾を刈る)。傷が窓(既定 ±λc)より広いと外挿せず拒否する。収束しなければ値を返さない。次数 2 は出していない。真値は閉形式と合成したうねりで、実スタイラス断面での検証は未了。

実寸校正: 平均線の真値は測定器では得られない。標本間隔 dx(µm)とカットオフ λc(測定条件で決まる値)は呼び出し側が与え、単位を混ぜても検出できない。伝達関数は dx と λc だけで決まる閉形式なので、既知波長の正弦を通して λc で 0.5 になるかを現場の設定で確かめられる。

動く例: `poc_robust_profile_filter`, `example_robust_profile_filter`

### [微細スクラッチを見つけて、幅を測る](capabilities/scratch-detection-and-width.md)

線状の傷を**どこにあるか**(検出)と**どれだけ太いか**(幅)の 2 段で扱います。検出は Hessian リッジ応答(`lines_gauss`)か暗い細部だけを浮かせる形態学(`bothat`)、幅は検出した線に**直交する測定線**を張って `measure_pairs` で両側のエッジをサブピクセルで取り、`table_px_to_mm` で mm にします。

使う op: `lines_gauss`, `bothat`, `measure_pairs`, `table_px_to_mm`

推奨パイプライン: [`gaussian`](ops/2d/smoothing/gaussian.md) → [`lines_gauss`](ops/2d/contour/lines_gauss.md) → [`select_contours`](ops/2d/contour/select_contours.md) → [`fit_line_contours`](ops/2d/contour/fit_line_contours.md) → [`gen_measure_rectangle2`](ops/measure1d/caliper/gen_measure_rectangle2.md) → [`measure_pairs`](ops/measure1d/caliper/measure_pairs.md) → [`table_px_to_mm`](ops/measure1d/scale/table_px_to_mm.md)

代替: [`bothat`](ops/2d/morphology/bothat.md), [`tophat`](ops/2d/morphology/tophat.md), [`sk_frangi`](ops/2d/texture/sk_frangi.md), [`laplace_of_gauss`](ops/2d/edges/laplace_of_gauss.md), [`fuzzy_measure_pairing`](ops/measure1d/caliper/fuzzy_measure_pairing.md), [`mm_per_px_from_reference`](ops/measure1d/scale/mm_per_px_from_reference.md)

限界: `lines_gauss` は線の**幅も極性も返さない**(暗線・明線を同じ輪郭にする、実測)。幅 1〜3 px は `measure_pairs` の危険域(エッジ間距離 / PSF 幅 < 3.09 で大きい側へ偏り、失敗を返さない)—— 画素以下の幅は輝度欠損の積分で測る(`poc_crack_width`)。

実寸校正: 既知幅の的(スケールバー・基準溝)を同じ光学系で `measure_pairs` にかけ `mm_per_px_from_reference` → `table_px_to_mm`。0.1 mm を切る幅は mm/px の 1 % がそのまま効く。

動く例: `example_scratch_width`, `poc_crack_width`, `poc_solar_el_inspection`

### [SEM の明るい縁が寸法をどれだけ太らせるかを、真値つきで測る](capabilities/sem-edge-effect-metrology.md)

走査電子顕微鏡(SEM)像では、二次電子が斜面でよけいに出る(放出 ∝ sec θ)ので段差の縁が明るく縁取られ、ビームの有限径(PSF)がその縁を広げます。`sem_render` は高さ場からこの SEM 像を**閉形式の真値つき**で作ります(平面で一様 / 斜面で平面比 = sec θ / 段差の明るい縁の幅 = PSF 幅)。作った像をしきい値 → `blob_label` → `blob_features` で測ると、明るい縁ごと拾って面積が系統的に太ること、その太りが **周囲長 × PSF 幅** でよく説明でき、既知の PSF 幅で引くと消えることが数で示せます。`seg_dice_jaccard` / `seg_boundary_f` で専門家マスクと採点し、`pod_hitmiss_fit` で埋め込み欠陥の検出確率 a90/95 を出します。

使う op: `sem_render`, `blob_label`, `blob_features`, `seg_dice_jaccard`, `seg_boundary_f`, `pod_hitmiss_fit`

動く例: `poc_sem_wafer_defect_edge_bias`

### [逐次光学設計の指標(理想レンズ面 → 囲みエネルギー → 子午/球欠 MTF → スルーフォーカス MTF)](capabilities/sequential-lens-design-metrics.md)

商用の逐次光学設計ソフトで毎日使う 4 つの道具を、Fullseye の op として足しました。

使う op: `lens_system`, `encircled_energy`, `ensquared_energy`, `energy_radii`, `mtf_tangential_sagittal`, `through_focus_mtf`, `with_aiming`, `ray_aiming`, `set_vignetting`, `lens_configurations`, `lens_with_configuration`, `lens_configuration_table`, `lens_configuration_metrics`, `lens_add_configuration`

推奨パイプライン: [`lens_system`](ops/optics/design/lens_system.md) → [`psf_from_opd`](ops/optics/imaging_sim/psf_from_opd.md) → [`encircled_energy`](ops/optics/imaging/encircled_energy.md) → [`energy_radii`](ops/optics/imaging/energy_radii.md) → [`mtf_tangential_sagittal`](ops/optics/imaging/mtf_tangential_sagittal.md) → [`through_focus_mtf`](ops/optics/imaging_sim/through_focus_mtf.md)

代替: [`psf_to_mtf`](ops/optics/imaging/psf_to_mtf.md), [`mtf_diffraction`](ops/optics/imaging/mtf_diffraction.md), [`spot_stats`](ops/optics/design/spot_stats.md), [`opd_map`](ops/optics/design/opd_map.md), [`wavefront_from_opd`](ops/optics/design/wavefront_from_opd.md), [`lens_section_drawing`](ops/optics/drawing/lens_section_drawing.md)

限界: 理想レンズ面の光路は軸上の物点(第 1 面で有限物体なら光線ごとの物点)に対して等光路で、途中の理想レンズでは平行入射を仮定する(収束光の中の理想レンズの OPD は近似)。理想レンズは非共軸の raytrace3d では読まず、鏡・円錐・非球面・硝材を持たない。囲み/四角エネルギーは PSF の窓の中の割合で、窓が翼を切ると高めに出る(切れて届かない割合は ValueError)。半径が 2 画素前後より小さいと PSF の点標本を画素に均等に広げた近似が効く。スルーフォーカス MTF は 1 視野 1 波長ずつ(多色は波長ごとに呼ぶ)。

実寸校正: 長さの尺度は PSF の画素ピッチ(psf_from_opd の pixel_pitch_um、または細かい格子の間隔 λ·F#·(size−1)/M)で決まり、周波数は cycles/mm。ピッチを間違えると半径が比例して狂う(探針で確認)。

動く例: `optical_design_metrics`, `poc_zoom_configurations`

### [黒光沢とガラスの形を偏光で測る(偏光からの形状復元・曖昧さの集合・屈折率の推定)](capabilities/shape-from-polarization.md)

4 方位のオンチップ偏光子を持つセンサの 1 ショットから、面の**法線**と**高さ**を出します。黒い光沢の樹脂やガラスのレンズは拡散反射がほとんど無く、照明を変えても陰影が出ないので、照度差ステレオや陰影からの形状復元が拠り所を失います。けれど表面で 1 回反射した光の偏光は、面の傾きで決まっています(Fresnel の式)。

使う op: `sfp_dolp_model`, `dolp_to_zenith`, `aolp_to_azimuth`, `sfp_render`, `sfp_normals`, `sfp_disambiguate`, `sfp_estimate_index`, `sfp_height`

動く例: `poc_shape_from_polarization`

### [実物の画像から物理モデルの係数を合わせる(sim-to-real 較正)—— 画像が決めない係数には数を出さず、決まる組み合わせと理由を返す](capabilities/sim-to-real-calibration.md)

周辺減光の強さ・ボケの幅・膜の厚さ・カメラの利得のような**物理の係数**を、実物の画像との差が雑音の大きさになるまで自動で 合わせます(`simcal`、10 op)。模型は fullseye の op の連鎖(例 `thin_film_reflectance` → 画像 → 利得と黒レベル)で、各段の 引数を単位・範囲・線形 / 対数つきの「つまみ」にします。当てはめは雑音の分散で重みをつけた最小二乗(重みは予測で更新)。

使う op: `simcal_model`, `simcal_simulate`, `simcal_observe`, `simcal_screen`, `simcal_fit`, `simcal_identifiability`, `simcal_uncertainty`, `simcal_validate`, `simcal_discrepancy`, `simcal_report`

推奨パイプライン: [`simcal_model`](ops/simcal/model/simcal_model.md) → [`simcal_observe`](ops/simcal/model/simcal_observe.md) → [`simcal_fit`](ops/simcal/fit/simcal_fit.md) → [`simcal_identifiability`](ops/simcal/check/simcal_identifiability.md) → [`simcal_report`](ops/simcal/report/simcal_report.md)

代替: [`simcal_screen`](ops/simcal/fit/simcal_screen.md), [`simcal_uncertainty`](ops/simcal/check/simcal_uncertainty.md), [`simcal_validate`](ops/simcal/check/simcal_validate.md), [`simcal_discrepancy`](ops/simcal/check/simcal_discrepancy.md), [`simcal_simulate`](ops/simcal/model/simcal_simulate.md), [`mv_confounding`](ops/multivar/identifiability/mv_confounding.md), [`mv_residual_pca`](ops/multivar/identifiability/mv_residual_pca.md), [`sens_morris`](ops/multivar/sensitivity/sens_morris.md)

限界: 推定の物差しはカメラの雑音モデル(EMVA 1288 の線形カメラかガウス)で、雑音モデルが無いと拒否する。雑音を 1/4 に見誤ると Cramér-Rao 下界も半分になり、40 組の採点は 39 組 → 29 組に落ちる(例で実測)。位置合わせは整数画素だけ。干渉縞のように谷がいくつもある問題では、小さな計画からの LM は隣の谷に落ちうる(値は返し、χ²/自由度を警告に出す)。モデルの食い違いがあると不確かさは楽観側になる(simcal_discrepancy が注記する)。

実寸校正: 係数はつまみの単位(px・DN・nm …)で返る。画素から mm への換算は模型の外の話で、倍率や画素ピッチをつまみに入れるなら、それが画像から決まるかを simcal_screen で先に確かめる(倍率と画素ピッチは積でしか効かない)。

動く例: `simcal_tour`, `simcal_checks_tour`

### [画像から寸法をサブピクセルで測る](capabilities/subpixel-2d-metrology.md)

測定線に沿った輝度の勾配からエッジを**画素より細かく**求め、対になるエッジの間隔として寸法を返します。二値化して画素を数える方法と違い、しきい値の選び方で答えが動きません。

使う op: `measure_pos`, `measure_pairs`, `blob_label`, `blob_select`

推奨パイプライン: [`gen_measure_rectangle2`](ops/measure1d/caliper/gen_measure_rectangle2.md) → [`measure_pos`](ops/measure1d/caliper/measure_pos.md) → [`measure_pairs`](ops/measure1d/caliper/measure_pairs.md) → [`table_px_to_mm`](ops/measure1d/scale/table_px_to_mm.md)

代替: [`fuzzy_measure_pairing`](ops/measure1d/caliper/fuzzy_measure_pairing.md), [`gen_measure_arc`](ops/measure1d/caliper/gen_measure_arc.md), [`create_metrology_model`](ops/measure1d/model/create_metrology_model.md), [`blob_label`](ops/blob/connect/blob_label.md), [`blob_select`](ops/blob/select/blob_select.md), [`mm_per_px_from_reference`](ops/measure1d/scale/mm_per_px_from_reference.md)

限界: 斜めの測定線に cos 補正が無い。エッジ間距離 / PSF 幅 < 3.09 で幅が大きく出るのに失敗を返さない。縁の定義で 16 px 動く(guides/subpixel_measuring.md)。

実寸校正: 既知寸法の的を**同じ op で**測って `mm_per_px_from_reference` → `table_px_to_mm` で表ごと mm に。公称倍率は使わない(作動距離 10 % で全寸法 10 %)。

動く例: `poc_dimensional_inspection`, `poc_screw_thread_metrology`, `poc_calipers_under_illusion`

### [テレセントリックレンズと寸法計測(主光線の傾き → 高さで変わる倍率 → ケラレとぼけ)](capabilities/telecentric-metrology.md)

段差のある部品(ボンディングのダイ、コネクタのピン、穴)の寸法を 1 枚の画像で測るとき、通常のレンズは近い面ほど大きく写すので、高さの違う面で同じ寸法が違う長さに写ります。`telecentric` の 7 本は `raytrace` の処方(`lens_system` の table)を実光線で追い、この誤差がどれだけ出てどれだけ消えるかを数字で返します。

使う op: `telecentric_lens`, `chief_ray_angle`, `magnification_vs_depth`, `telecentricity_error`, `defocus_spot_vs_depth`, `vignetting_vs_field`, `lens_equivalent_pinhole`

推奨パイプライン: [`telecentric_lens`](ops/optics/telecentric/telecentric_lens.md) → [`chief_ray_angle`](ops/optics/telecentric/chief_ray_angle.md) → [`telecentricity_error`](ops/optics/telecentric/telecentricity_error.md) → [`magnification_vs_depth`](ops/optics/telecentric/magnification_vs_depth.md) → [`defocus_spot_vs_depth`](ops/optics/telecentric/defocus_spot_vs_depth.md) → [`vignetting_vs_field`](ops/optics/telecentric/vignetting_vs_field.md)

代替: [`lens_system`](ops/optics/design/lens_system.md), [`paraxial_trace`](ops/optics/design/paraxial_trace.md), [`lens_equivalent_pinhole`](ops/optics/telecentric/lens_equivalent_pinhole.md), [`relative_illumination`](ops/optics/geometric/relative_illumination.md)

限界: 処方は単レンズの組み合わせで、実機のテレセン(5〜10 枚)の瞳収差・歪曲の補正は無い(物体側テレセンの単レンズは物高 8 mm で歪曲 3 %、テレセン度 0.05° が残る)。回折は扱わず、ぼけは幾何光学の光線束。物体が無限遠の処方は拒否する。

実寸校正: 画像の寸法を mm にする尺度は、両側テレセンなら高さに依らない(視野 4 mm・段差 5 mm で読みの差 −0.01 %)ので 1 枚の校正板でよい。通常のレンズでは同じ条件で 6.89 % 狂うので、測る面の高さで校正する。

動く例: `poc_telecentric_metrology`

### [仮想の透過電子顕微鏡(電子の波長 → CTF → 位相コントラストの像 → Thon リングから焦点外れを推定 → 補正)](capabilities/tem-phase-contrast-and-ctf.md)

透過電子顕微鏡(TEM)は薄い試料を透けた電子の位相を、対物レンズの球面収差 Cs と焦点外れ Δf で強度に変えて見ます。その変え方がコントラスト伝達関数 CTF = −sin(χ + arcsin w) で、周波数ごとに符号が入れ替わるので、写真の細部は焦点によって黒くも白くも写ります。パワースペクトルには CTF の零点が同心円(Thon リング)として出るので、逆にリングから焦点外れを読めます。`temsim`(`opsoptics` の `tem`、11 本)はこの流れを通します。

使う op: `tem_wavelength`, `tem_scherzer`, `tem_ctf`, `tem_ctf_profile`, `tem_projected_potential`, `tem_amorphous_film`, `tem_image_weak_phase`, `tem_multislice`, `tem_power_spectrum`, `tem_ctf_estimate`, `tem_ctf_correct`

推奨パイプライン: [`tem_power_spectrum`](ops/optics/tem/tem_power_spectrum.md) → [`tem_ctf_estimate`](ops/optics/tem/tem_ctf_estimate.md) → [`tem_ctf_correct`](ops/optics/tem/tem_ctf_correct.md)

代替: [`tem_ctf_profile`](ops/optics/tem/tem_ctf_profile.md), [`tem_scherzer`](ops/optics/tem/tem_scherzer.md), [`tem_image_weak_phase`](ops/optics/tem/tem_image_weak_phase.md), [`tem_amorphous_film`](ops/optics/tem/tem_amorphous_film.md), [`tem_multislice`](ops/optics/tem/tem_multislice.md)

限界: 弱位相近似の線形の像は位相の rms が 0.1 rad を超えると 10 % 以上ずれる(非線形は mode="coherent")。推定は CTF² の振動の当てはめで、リングが見えない・零点が 3 本無い・範囲の端・2-D の当てはめが別の谷に落ちた(z が低い)ときは拒否。Cu など重い元素の散乱因子は X 線の当てはめの限界で 10 % 小さい。

実寸校正: 焦点外れの値は画素寸法の 2 乗と電子の波長に比例して決まる(画素寸法を 2 % 間違えると Δf は 4 % ずれる)。画素寸法は検出器の画素 ÷ 倍率か、格子間隔の既知の試料(金の格子・グラファイト)のリングで校正し、電圧と Cs は装置の値を使う。

動く例: `poc_tem_ctf_thon_rings`

### [地形の傾き・水の流れ・見通しを測る](capabilities/terrain-and-visibility.md)

高さ格子(DEM)から、傾斜・斜面方位・可視領域・流向を出します。いずれも閉形式と突き合わせられる量なので、実装の誤りを数字で捕まえられます。

使う op: `dem_slope`, `dem_aspect`, `dem_viewshed`, `dem_flow_direction`

推奨パイプライン: [`dem_fill_sinks`](ops/dem/hydrology/dem_fill_sinks.md) → [`dem_slope`](ops/dem/surface/dem_slope.md) → [`dem_aspect`](ops/dem/surface/dem_aspect.md) → [`dem_flow_direction`](ops/dem/hydrology/dem_flow_direction.md) → [`dem_viewshed`](ops/dem/visibility/dem_viewshed.md)

代替: [`dem_hillshade`](ops/dem/shading/dem_hillshade.md), [`dem_flow_accumulation`](ops/dem/hydrology/dem_flow_accumulation.md), [`dem_geodetic_slope`](ops/dem/geodesy/dem_geodetic_slope.md)

限界: 格子の刻みより細かい地形は出ない。可視領域は 1 観測点ぶん。測線の継ぎ目が地形に無い崖を作る(2.99 度 → 49.4 度、`poc_stockpile_volume`)。

実寸校正: `cell_size` [m] を渡す —— 傾斜は高さと格子間隔の**比**なので、単位が揃っていないと角度が全部ずれる。

動く例: `poc_dem_terrain`, `dem_terrain_analysis_tour`

### [仮想 SEM —— 電子と固体の相互作用をモンテカルロで解き、加速電圧・検出器・帯電で像と線幅がどう変わるかを実測値で採点しながら見る](capabilities/virtual-sem-monte-carlo.md)

一次電子を固体の中で 1 個ずつ追うモンテカルロ(Joy の単散乱モデル。弾性散乱は Browning 1994 の Mott 近似、阻止能は Joy-Luo 1989)で、反射電子係数 η・二次電子収率 δ・到達深さを `sem_electron_mc` が、δ(E) の形を `sem_yield_curve` が出します。材料の Z・A・密度・二次電子の定数は、光学と同じ材料表の `material_electron_properties` から引きます。CD-SEM の線プロファイルは `sem_line_profile`(台形の断面、埋もれた矩形も)で、線幅は `sem_cd_measure`(しきい値法・最大傾斜法)で測ります。高さ場と材料の地図からは `sem_image` が画素ごとに電子を撃って像を作り(レンズ内 SE / 側方 SE / 反射電子)、`sem_charging_series` が絶縁物の帯電をコマ送りにします。外部真値の門は 4 本: η(Z, E) が Joy のデータベースの実測の幅に入る / 傾けた試料の η(θ) が Arnal の式 / 到達深さが Kanaya-Okayama / δ の形と Emax が Lin & Joy 2005。

使う op: `sem_electron_mc`, `sem_yield_curve`, `sem_se_universal_curve`, `sem_line_profile`, `sem_cd_measure`, `sem_image`, `sem_charging_series`, `sem_se_escape_fraction`, `material_electron_properties`

推奨パイプライン: [`material_electron_properties`](ops/optics/matprop/material_electron_properties.md) → [`sem_electron_mc`](ops/generative/sem/sem_electron_mc.md) → [`sem_line_profile`](ops/generative/sem/sem_line_profile.md) → [`sem_cd_measure`](ops/generative/sem/sem_cd_measure.md) → [`sem_image`](ops/generative/sem/sem_image.md)

代替: [`sem_render`](ops/generative/sem/sem_render.md), [`sem_yield_curve`](ops/generative/sem/sem_yield_curve.md), [`sem_charging_series`](ops/generative/sem/sem_charging_series.md)

限界: 重元素(W・Au)の δ(E) の形は普遍曲線より裾が厚く合わない(SE2 が主、未解決)。δmax は Lin & Joy の表の約 0.8 倍。帯電の負の側は現象論。像は画素ごとの直接 MC なので高加速・大きな像は遅い。「低加速ほど側壁の上を測る」は側壁 88 度で成り立ち 80 度では逆(`poc_virtual_sem_kv_cd_bse`)。

実寸校正: 高さ場・線幅・画素は nm のまま入れる。材料は `material_electron_properties` の名前で引き、表に無い材料の λ・ε は推定と明記される。実機と合わせるなら既知の材料(Si・Au)の η と δ を同じ加速電圧で測って比べる。

動く例: `poc_virtual_sem_kv_cd_bse`

### [3-D スキャンから体積・土量を出す](capabilities/volume-from-3d-scan.md)

点群や高さ格子から、閉じたメッシュの符号つき体積、voxel 領域の体積、2 つの面のあいだの土量を出します。欠測は補間で埋められますが、**その補間がどこまで効いたか**を別に持ち出せます。

使う op: `mesh_volume`, `vol_rle_volume`, `interp_scattered`, `dem_slope`

推奨パイプライン: [`vol_rle_components`](ops/3d/rle_region/vol_rle_components.md) → [`vol_rle_volume`](ops/3d/rle_region/vol_rle_volume.md) → [`mesh_volume`](ops/3d/mesh_process/mesh_volume.md)

代替: [`interp_scattered`](ops/math/interp_poly/interp_scattered.md), [`dem_slope`](ops/dem/surface/dem_slope.md), [`dem_fill_sinks`](ops/dem/hydrology/dem_fill_sinks.md), `marching_cubes`

限界: 底面が測れていない場面 —— 5 cm の仮定違いで 1.269 %(72.5 t)。外周平均の底面は誤差が打ち消して見えなくなる(`poc_stockpile_volume`)。

実寸校正: 格子間隔 [m] と高さ [m] の単位を揃える。ボクセル数はピッチの 3 乗。底面は**実際に見えた点だけ**で決める。

動く例: `poc_stockpile_volume`, `poc_lidar_terrain_change`

### [絵では確かめられないもの(積分器の次数・リアプノフ指数・分岐・相関次元・極小曲面)](capabilities/what-a-picture-cannot-check.md)

力学系(軌道・ベクトル場・ポアンカレ断面・リアプノフ指数・分岐図・相関次元)と極小曲面(カテノイド・ヘリコイド・エンネパー・シェルク・ジャイロイド)を作り、**恒等式と定義だけで採点します**。軌道は管メッシュにして立体で見られます。

使う op: `ode_flow_states`, `ode_vector_field_grid`, `dynsys_poincare_section`, `dynsys_lyapunov_spectrum`, `dynsys_bifurcation_map`, `dynsys_correlation_dimension`, `minimal_surface`, `minimal_surface_bend`, `gyroid_isosurface`, `gyroid_solid_mask`, `curve3d_tube_mesh`

動く例: `poc_what_a_picture_cannot_check`

## 見つける (12)

### [領域を切り出して、選んで、数える](capabilities/blob-and-region.md)

連結成分にラベルを付け、面積・形・位置で選び、数えます。接触している対象は分水嶺で分けられます。

使う op: `blob_label`, `blob_select`, `blob_count`, `watersheds`, `blob_count_interval`

推奨パイプライン: [`auto_threshold`](ops/2d/segmentation/auto_threshold.md) → [`blob_label`](ops/blob/connect/blob_label.md) → [`blob_select`](ops/blob/select/blob_select.md) → [`blob_features`](ops/blob/measure/blob_features.md)

代替: [`watersheds`](ops/2d/segmentation/watersheds.md), [`blob_seeds`](ops/blob/split/blob_seeds.md), [`blob_count`](ops/2d/features/blob_count.md), [`blob_count_interval`](ops/blob/split/blob_count_interval.md), [`remove_small`](ops/2d/region/remove_small.md), [`select_shape`](ops/2d/region/select_shape.md), [`otsu`](ops/2d/segmentation/otsu.md)

限界: 計数が合っていて分割が全部外れる点がある(`poc_cell_counting`)—— 数と形を別に数える。粒度分布で D50 が合う点は「正確」ではなく融合と縁切れの打ち消し(`poc_particle_sizing`)。

実寸校正: 面積は mm/px の **2 乗**。`mm_per_px_from_reference` で mm/px を出し、面積には自分で 2 乗して掛ける(`table_px_to_mm` が換算するのは長さ列だけ)。

動く例: `poc_cell_counting`, `poc_particle_sizing`, `poc_real_coin_metrology`, `poc_dense_bubble_count`

### [圃場の RGB から作物と雑草を色と肌理で分け、雑草の被度を宣言した境で段階にする(学習器なし)](capabilities/crop-weed-cover-grade.md)

水田や畑の RGB 画像(UAV・定点カメラ)から、作物の画素と雑草の画素を分け、雑草の程度を段階(少ない / 中程度 / 多い / 甚大)で答えます。深層学習は使わず、色の指標と肌理の特徴を領域ごとに出し、2 クラスの Fisher 線形判別(閉形式)で分けます。

使う op: `plant_color_index`, `superpixel_color_texture_features`, `fisher_lda_fit`, `fisher_lda_score`, `cover_ratio_grade`

推奨パイプライン: [`superpixel_color_texture_features`](ops/segmentation/plant/superpixel_color_texture_features.md) → [`fisher_lda_fit`](ops/segmentation/classify/fisher_lda_fit.md) → [`fisher_lda_score`](ops/segmentation/classify/fisher_lda_score.md) → [`cover_ratio_grade`](ops/segmentation/plant/cover_ratio_grade.md)

代替: [`plant_color_index`](ops/segmentation/plant/plant_color_index.md), [`snic_superpixels`](ops/segmentation/graph/snic_superpixels.md), [`class_ndim_norm`](ops/segmentation/classify/class_ndim_norm.md)

限界: 判別は 10 特徴の 1 次式で、色と肌理が作物と雑草でほとんど同じ(雑草イネ)だと位置の精度は IoU 0.4 程度。季節の違う飛行への汎化は弱い(撮影日を丸ごと外すと日の中の相関 0.14 の日がある)。暗い画素は色度が決まらず値を作らない。

実寸校正: 画像は uint8 か [0, 1] の float。照明の色が変わる圃場では、白板か灰色の板で白を合わせてから色指標を取る(色度座標の指標は一様な明るさの倍率には不変だが、色温度の変化には不変でない)。

動く例: `poc_weed_rice_ratio`

### [X 線の 2 つのエネルギーで厚みと材質を分ける(デュアルエナジー / フォトンカウンティング: スペクトル → 窓 → 基底分解 → 実効 Z)](capabilities/dual-energy-xray-material-discrimination.md)

1 枚の X 線透過像は、各画素で L = −ln(I/I₀) = Σ μₘ tₘ という**1 つの数**しか測りません。厚い肉と薄い骨片・ガラスは同じ L を作れるので、厚みと材質は分けられません。光子のエネルギーを 2 つ以上の窓で数え分ける検出器(フォトンカウンティング)か、2 つの管電圧で撮ると、μ(E) の**形**が材質で違う(光電効果は ≈ Z³/E³、コンプトン散乱は電子密度だけ)ので、各画素で方程式が窓の数だけ立ち、2 つの基底物質の厚みに分けられます(Alvarez & Macovski 1976、Lehmann ら 1981)。

使う op: `material_xray_table`, `material_xray_attenuation`, `material_xray_constants`, `material_effective_z`, `xray_tube_spectrum`, `xray_beam_quality`, `photon_counting_channels`, `dual_kvp_channels`, `xray_channel_projection`, `basis_material_decompose`, `basis_decomposition_crlb`, `r_value_map`, `effective_z_map`, `dual_energy_separability`

推奨パイプライン: [`xray_tube_spectrum`](ops/tomography/spectral_xray/xray_tube_spectrum.md) → [`photon_counting_channels`](ops/tomography/spectral_xray/photon_counting_channels.md) → [`basis_decomposition_crlb`](ops/tomography/spectral_xray/basis_decomposition_crlb.md) → [`basis_material_decompose`](ops/tomography/spectral_xray/basis_material_decompose.md) → [`effective_z_map`](ops/tomography/spectral_xray/effective_z_map.md)

代替: [`dual_kvp_channels`](ops/tomography/spectral_xray/dual_kvp_channels.md), [`r_value_map`](ops/tomography/spectral_xray/r_value_map.md), [`dual_energy_separability`](ops/tomography/spectral_xray/dual_energy_separability.md), [`xray_channel_projection`](ops/tomography/spectral_xray/xray_channel_projection.md), [`material_xray_attenuation`](ops/tomography/spectral_xray/material_xray_attenuation.md)

限界: 散乱線・検出器の K 蛍光の逃げ・パイルアップ・画素間の電荷共有の二重計数は入っていない。X 線管のスペクトルは簡易模型(半価層は IEC の線質と 6 % 以内)。肉に埋まった異物の見かけの Z は組成だけでなく密度でも動き(PVC は 13.9 が 18.7 に見える)、無機物の向きは Al(13)から Cu(29)まで狭い角度に詰まるので、Z を 1 刻みでは読めない。

実寸校正: 較正の op は無い。管電圧・ろ過・検出器の材料と厚さ・窓のしきい値・エネルギー分解能・電荷共有の割合を既知として `photon_counting_channels` に入れる —— 応答を知らずに分解すると肉が Al に化ける(PoC の門)。実機では厚さの分かった 2 材料の段の撮影でチャネルの応答を合わせる。

動く例: `poc_dual_energy_xray`

### [画像の中の文字を、正しい文字列に合わせて直す](capabilities/fix-text-in-images.md)

生成 AI が出したレポート用の画像や看板の文字が 1 字だけ壊れている —— そういうとき、画像を作り直さずに、**本当はこう書いてあるべき文字列**を渡して直せます。入口は JSON 一枚(`spec = {"items": [{"text": "電気設備", "bbox": [x, y, w, h]}]}`)で、Python の `glyph_correct_spec` からも MCP の `fullseye_fix_text` からも同じ形で呼べます。文字を**認識はしません**: 正しい文字列が与えられるので、各マスを指定の 1 字と 1 対 1 で照合するだけで済み、6,000 字の分類器は要りません。閾値は勘で置かず、その環境の書体で同じ字を描き分けた距離の 95 % 点(書体雑音の床)から導きます。

使う op: `glyph_correct_spec`, `glyph_make_spec`, `glyph_find_text_lines`, `glyph_rewrite_line`, `glyph_find_plate`, `glyph_typeface_noise_floor`, `glyph_rendering_noise_floor`, `glyph_distance`, `glyph_replace`, `glyph_split_cells`, `glyph_fonts`

動く例: `fix_text_in_image`, `poc_glyph_typo_detection`

### [良品を並べて「いつもと違う」を言う(良品統計の変動モデル、誤検出率の宣言つき)](capabilities/good-sample-variation-model.md)

位置をそろえた良品の画像を何枚か渡すと、画素ごとの「いつもの値」(中心)と「いつものばらつき」を覚え、新しい 1 枚のどの画素が許容帯の外にあるか、何 σ 外れたかを領域ごとに説明します。外観検査の古典(良品統計・バリエーションモデル)ですが、帯の幅 k を手で決めずに、**1 画素あたりの誤検出率を宣言して**分布から決めます。

使う op: `varmodel_alignment`, `varmodel_band_k`, `varmodel_fit`, `varmodel_calibrate`, `varmodel_score`, `anomaly_pixel_auroc`, `anomaly_pro`, `anomaly_image_auroc`, `anomaly_region_overlap`, `compare_to_golden`

推奨パイプライン: [`varmodel_alignment`](ops/spc/variation/varmodel_alignment.md) → [`varmodel_fit`](ops/spc/variation/varmodel_fit.md) → [`varmodel_calibrate`](ops/spc/variation/varmodel_calibrate.md) → [`varmodel_score`](ops/spc/variation/varmodel_score.md)

代替: `compare_to_golden`, [`dc_rpca_sparse`](ops/2d/decomposition/dc_rpca_sparse.md), [`anomaly_pro`](ops/spc/anomaly_eval/anomaly_pro.md)

限界: 並進だけを合わせる。回転・拡大・照明の違いが残る実画像では宣言の誤検出率は守られない(VisA pcb1 で宣言 1e-3 に対し 3.8 %、持ち出しの較正後も 2.4 %)。確率的なテクスチャには効かない(DAGM 2007 で偶然並み)。

実寸校正: 帯は画素値の単位のまま。欠陥の大きさを実寸で言うなら、既知寸法の的を同じ光学系で測り `mm_per_px_from_reference` → `pixel_to_world`。

動く例: `poc_good_sample_variation_model`, `anomaly_eval_metrics`

### [OCR の前処理(傾き補正・局所 2 値化・行の切り出し)](capabilities/ocr-preprocessing.md)

認識器(外部の OCR / 1-D・2-D コードのデコーダ)に渡す前の、**傾き補正 → 局所 2 値化 → ゴミ取り → 行のまとめ**を 2-D レジストリ op だけで組みます。認識そのものはこのライブラリの持ち場ではありません。

使う op: `sk_sauvola`, `rotate_image`, `remove_small`, `dilation_rectangle1`

推奨パイプライン: [`median`](ops/2d/rank/median.md) → [`rotate_image`](ops/2d/geometry/rotate_image.md) → [`sk_sauvola`](ops/2d/segmentation/sk_sauvola.md) → [`invert_region`](ops/2d/region/invert_region.md) → [`remove_small`](ops/2d/region/remove_small.md) → [`select_shape`](ops/2d/region/select_shape.md) → [`dilation_rectangle1`](ops/2d/region/dilation_rectangle1.md)

代替: [`sk_niblack`](ops/2d/segmentation/sk_niblack.md), [`adaptive_gauss_thresh`](ops/2d/segmentation/adaptive_gauss_thresh.md), [`otsu`](ops/2d/segmentation/otsu.md), [`gray_bothat`](ops/2d/morphology/gray_bothat.md), [`unsharp`](ops/2d/smoothing/unsharp.md), [`zoom_image_factor`](ops/2d/geometry/zoom_image_factor.md), [`affine_trans_image`](ops/2d/geometry/affine_trans_image.md)

限界: OCR 本体(文字認識)は無い —— ここは認識器に渡す 2 値画像を作る層。大域 `otsu` は照明むらで文字が欠ける(局所 `sk_sauvola` へ)。傾きは `rotate_image` の `a` で与える(角度の推定は輪郭 `fit_line_contours` か射影で別に取る)。細い字画は `remove_small` で消える。

実寸校正: 文字は px で扱い、実寸校正は不要。読み取り解像度の目安は x 高さ 20 px 以上(足りなければ `zoom_image_factor`)。

動く例: `gallery2d_segmentation`, `poc_matrix_code_reading`, `gallery2d_region`

### [PL 像で細い溝が見えなくなる理由を、キャリア拡散の PSF と欠陥の種類で切り分ける(Si ウェハ・太陽電池の PL/EL 検査)](capabilities/pl-carrier-diffusion-visibility.md)

フォトルミネッセンス(PL)像は、励起で作った過剰キャリアが**拡散してから**光ります。だから像には光学の PSF のほかに、拡散長 L = √(Dτ) で決まる**もう 1 つの PSF**(2 次元のグリーン関数 K₀(r/L)/2πL²)が掛かります。`pl_diffusion_psf` はその核を総和 1 で返し、`pl_image_simulate` は励起の場と追加再結合の場から定常拡散方程式を格子で厳密に解いて PL 像を作ります(光学 PSF と雑音は任意)。`pl_groove_visibility` は溝の幅・拡散長・雑音から、**影の溝**(励起や発光の欠け、コントラスト 1 − e^{−w/2L})と**沈みの溝**(再結合の線、Donolato 型 SL/(SL+2D))のコントラスト・CNR・見える/見えないの境界 L* を閉形式で返します。

使う op: `pl_diffusion_psf`, `pl_image_simulate`, `pl_groove_visibility`, `pod_hitmiss_fit`

動く例: `poc_si_wafer_pl_defect_visibility`

### [小さな点状の目標を見つけて、副画素で位置を出す](capabilities/point-target-detection.md)

頑健に推定した背景と雑音から `背景 + kσ` を超える局所最大を拾い、重心で副画素の位置を返します。名前は天体ですが**中身は分野中立**で、漂流物・微小欠陥・蛍光輝点・粒子に同じものが使えます。

使う op: `star_detect`, `peak_subbin`, `find_peaks`, `noise_sigma`

推奨パイプライン: [`noise_sigma`](ops/astrostack/quality/noise_sigma.md) → [`star_detect`](ops/astrostack/photometry/star_detect.md) → [`find_peaks`](ops/oned/signal/find_peaks.md) → [`peak_subbin`](ops/oned/signal/peak_subbin.md)

代替: [`xsk3_peak_local_max`](ops/2d/segmentation/xsk3_peak_local_max.md), [`blob_seeds`](ops/blob/split/blob_seeds.md), [`blob_label`](ops/blob/connect/blob_label.md)

限界: 目標が広がっていると不適(`blob_label` へ)。検出率だけでは誤検出が見えない —— 空撮の誤検出は直下に集中し、閾値で走査幅が 406 → 170 m 動く(`poc_search_sweep_width`)。

実寸校正: 位置は px。実距離は `mm_per_px_from_reference`(空撮なら高度から GSD)で換算し、高度が変われば取り直す。

動く例: `poc_search_sweep_width`, `poc_astro_photometry`

### [照明むら・ハイライト・遮蔽に強いテンプレート照合(明るさの変化の向きを符号にして比べ、決まらないテンプレートは拒否する)](capabilities/robust-code-matching.md)

明るさの**値**ではなく**変化の向き**を符号にして比べる照合の族(`codematch`、6 op)。学習した特徴を使わず、式と閾値だけで、 どこまで残りどこで壊れるかを自分で言えます。

使う op: `ocm_match`, `isc_match`, `scc_match`, `orientation_code`, `increment_sign`, `radial_reach_filter`

推奨パイプライン: [`isc_match`](ops/codematch/match/isc_match.md) → [`ocm_match`](ops/codematch/match/ocm_match.md)

代替: [`scc_match`](ops/codematch/match/scc_match.md), [`ncc_locate`](ops/2d/matching/ncc_locate.md), [`radial_reach_filter`](ops/codematch/change/radial_reach_filter.md)

限界: 回転には弱い(4 種とも 7〜9° で当たりが半分を割る。回転を探す方向符号ヒストグラムの系統は無い)。スケール変化も探さない。平坦な所の多いテンプレートは拒否されるか、SCC では採点できる位置が減る。SCC は「符号の合った画素だけを選ぶ」ので無関係な位置でも相関が高めに出る(選択の偏り)。既定の床でそれを抑えても OCM・ISC には届かない。RRF は背景が平坦な画素を判定しない(空・無地の壁)。

実寸校正: 座標は画素(テンプレート中心、find_ncc_model と同じ規約)。閾値 grad_thresh・flat_thresh・t_p は [0, 1] の明るさで書く(8 ビットなら 255 で割る)。

動く例: `poc_code_matching_breakdown`

### [ハイブリッド接合のボイドを、超音波のエコーの明るさでなく位相で見つける(走査型音響顕微鏡の C スキャン・周波数の取引・POD)](capabilities/sam-bond-voids.md)

貼り合わせた積層(Si のダイ + SiO2 と Cu パッドの接合層)を、水の中の集束探触子で上から 1 点ずつ測る走査型音響顕微鏡(SAM)を、層の物理から組み立てます。接合面の**空洞(ボイド)**は空気なので、そこで音響インピーダンスが約 4 万分の 1 に落ち、エコーが**反転**します。符号はボイドがビームより小さくても薄まりません。

使う op: `acoustic_material_table`, `acoustic_layer_stack`, `acoustic_interface_coefficients`, `pulse_echo_ascan`, `sam_cscan`, `echo_phase_polarity`, `sam_frequency_tradeoff`

動く例: `poc_sam_hybrid_bonding_voids`

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

## 形にする (3)

### [レンズの歪みを画像ごと補正する(たる型・糸巻き型・接線)](capabilities/lens-distortion-correction.md)

広角・魚眼寄りのレンズは直線を曲げます(たる型・糸巻き型)。`undistort_image(image, K, dist)` は Brown–Conrady モデル(`dist = [k1, k2, p1, p2(, k3)]`、OpenCV と同じ並び)で**画像を丸ごと補正**し、曲がった直線をまっすぐに戻します。`distort_image` はその逆で、理想画像から歪んだ画像を作ります(合成テストデータ・レンズの見えの確認)。

使う op: `undistort_image`, `distort_image`, `distort_points`, `undistort_points`

動く例: `lens_undistort`

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

## 光と色 (19)

### [クロマティック共焦点変位センサ(硝材の分散 → 較正表 → 戻りスペクトル → 高さ・厚さ)](capabilities/chromatic-confocal-sensor.md)

白色光を軸上色収差の大きい対物レンズで集光すると、波長ごとに焦点の高さが変わります。面で反射してピンホールを通って分光器へ戻るのは面にピントの合った色だけなので、戻りスペクトルのピーク波長が高さになります(Molesini 1984)。`chromconf` の 6 本は、このセンサを**対物レンズの処方(`raytrace`)と硝材の分散(`materials`)から**組み立てます。観察対象(透明板・金属・Si)の反射率と屈折率も同じ材料表から引きます。

使う op: `chromatic_confocal_probe`, `confocal_axial_response`, `chromatic_confocal_spectrum`, `chromatic_confocal_peaks`, `chromatic_confocal_readout`, `chromatic_confocal_limits`

推奨パイプライン: [`chromatic_confocal_probe`](ops/optics/confocal/chromatic_confocal_probe.md) → [`chromatic_confocal_spectrum`](ops/optics/confocal/chromatic_confocal_spectrum.md) → [`chromatic_confocal_peaks`](ops/optics/confocal/chromatic_confocal_peaks.md) → [`chromatic_confocal_readout`](ops/optics/confocal/chromatic_confocal_readout.md)

代替: [`confocal_axial_response`](ops/optics/confocal/confocal_axial_response.md), [`chromatic_confocal_limits`](ops/optics/confocal/chromatic_confocal_limits.md)

限界: 層のあいだの干渉は入れない(反射を強度で足す)ので数 µm の薄膜のチャネルドスペクトルは再現しない。縦球面収差は 3 次の 1 項だけ。NA の補正式・金や粗さや光源のむらによる偏りの大きさ・薄膜の限界は模型の値。

実寸校正: 較正表は合成データで鏡を動かして作る(ピーク波長 → 高さ)。滑らかな推定の偏りはこの較正で消え、ビンの刻みの振れは残る。実機では実測の較正表に差し替える。

動く例: `poc_chromatic_confocal`

### [色を測る(XYZ / Lab / 色差)](capabilities/colour-and-delta-e.md)

分光反射率または RGB から CIE XYZ・Lab を求め、CIE76 / CIEDE2000 の色差を出します。色差は画像全体の地図としても返せます。

使う op: `rgb_to_lab`, `xyz_to_lab`, `delta_e_2000`, `cie_xyz_from_wavelength`

推奨パイプライン: [`rgb_to_lab`](ops/imgmetrics/colorspace/rgb_to_lab.md) → [`delta_e_2000`](ops/imgmetrics/colordiff/delta_e_2000.md)

代替: [`rgb_to_xyz`](ops/imgmetrics/colorspace/rgb_to_xyz.md), [`xyz_to_lab`](ops/imgmetrics/colorspace/xyz_to_lab.md), [`delta_e_76`](ops/imgmetrics/colordiff/delta_e_76.md), [`delta_e_map`](ops/imgmetrics/colordiff/delta_e_map.md), [`cie_xyz_from_wavelength`](ops/optics/appearance/cie_xyz_from_wavelength.md), [`srgb_to_linear`](ops/gfx2d/colorspace/srgb_to_linear.md)

限界: 符号化 RGB を線形として扱うと全部ずれる。白色点(D50 / D65)の違う Lab を直接比べない。色恒常性に勝ち続ける手法は無い(`poc_white_balance`)。

実寸校正: 画素 → mm は関係しない。校正は**線形化**(`srgb_to_linear`)と**白色点**で、色差 ΔE は無次元。

動く例: `poc_white_balance`, `poc_pigment_unmixing`

### [多重反射・多重散乱・反復を収束まで回す —— 収束した証拠と残りの誤差を返し、収束しなければ値を出さない](capabilities/convergent-forward-models.md)

実物に近い順方向モデルは、閉じた式ではなく**繰り返しの極限**であることが多い —— 溝の壁から壁へ跳ね返り続ける光、濁った媒質の 中で散乱を繰り返す光子、どこかで止めるべき逆畳み込み。この族(`converge`、6 op)は、どれも収束まで回し、**収束した証拠**と **残りの誤差**を返し、収束しなければ値を返しません。

使う op: `iterate_fixed_point`, `conv_observed_order`, `conv_gci`, `mc_sequential_mean`, `mc_photon_slab`, `iv_richardson_lucy_until`

推奨パイプライン: [`iterate_fixed_point`](ops/converge/iterate/iterate_fixed_point.md) → [`conv_gci`](ops/converge/verification/conv_gci.md)

代替: [`conv_observed_order`](ops/converge/verification/conv_observed_order.md), [`mc_sequential_mean`](ops/converge/montecarlo/mc_sequential_mean.md), [`mc_photon_slab`](ops/converge/montecarlo/mc_photon_slab.md), [`iv_richardson_lucy_until`](ops/converge/stopping/iv_richardson_lucy_until.md), [`iv_richardson_lucy`](ops/2d/restoration/iv_richardson_lucy.md)

限界: 推定残り誤差は g が縮小写像である所でだけ意味を持つ(割線の比 L が 1 以上なら出さない)。GCI は離散化の誤差だけで、モデルの誤りは含まない。モンテカルロの区間は光子ごとの寄与の正規近似で、逐次に止めると被覆率は名目より少し下がりうる(0.95 に対し 400 回で実測、テストが両側で判定)。光子輸送は平行平板の層だけ(横方向の分布・ガラス層は無い)。Richardson-Lucy の止め方は雑音モデル(光子数か既知の σ)が正しいときだけ働く。

実寸校正: 単位は入力のまま(光子輸送は係数の長さの単位と厚さの単位を揃える。反射率・透過率は無次元)。画素から mm への換算は無い。

動く例: `converge_tour`

### [光ファイバとライトガイド(ガラスの分散 → LP モード → モード径 → 照明の効率)](capabilities/fiber-and-light-guide.md)

検査の照明はライトガイド(ファイバの束)で運び、干渉・分光の光は単一モードファイバで運びます。どちらもガラスの分散と導波の式で決まるので、`fiberoptics` の 7 本は材料表(`materials`)のガラスを名前で受けます。

使う op: `material_group_index`, `material_gvd`, `fiber_numerical_aperture`, `fiber_v_number`, `fiber_lp_modes`, `fiber_mode_field_diameter`, `fiber_bundle_coupling`

動く例: `poc_fiber_light_guide`

### [回折格子の分光器と顕微鏡の照明系(帯域の幅・smile / keystone・ケーラー / クリティカル・同軸のハーフミラー)](capabilities/grating-spectrometer-and-illumination.md)

分光器の「帯域の幅」は、入口スリットの幅・格子の溝の密度と照らされた本数・鏡の焦点距離・検出器の画素から決まります。`gratingspec` の 5 本は、格子の式 mλ = d(sin α + sin β) と Czerny–Turner の幾何からそれを組み立てます。`grating_dispersion` は角分散・逆線分散・分解能 mN・自由スペクトル範囲・同じ方向へ出る他の次数の波長を、`czerny_turner_design` は帯域と検出器の長さからカメラ鏡の焦点距離とコマを消す Shafer の角を、`spectrometer_bandpass` はスリットの像 ⊗ 画素 ⊗ 回折の装置関数の FWHM とエタンデュを、`spectrometer_slit_image` は溝に沿った方向余弦を保つ 3 次元の格子の式で長いスリットの像の smile と keystone を、`spectrometer_spectrum` は入力スペクトルから画素の読み(2 次・3 次の像の重なりとロングパスのフィルタつき)を出します。クロマティック共焦点の `spectrometer_fwhm_nm` とハイパースペクトルの `band_fwhm_nm` に渡す数字を、ここで作れます。

使う op: `grating_dispersion`, `czerny_turner_design`, `spectrometer_bandpass`, `spectrometer_slit_image`, `spectrometer_spectrum`, `illumination_train`, `illumination_field`, `coaxial_illumination`

推奨パイプライン: [`czerny_turner_design`](ops/optics/spectrometer/czerny_turner_design.md) → [`spectrometer_bandpass`](ops/optics/spectrometer/spectrometer_bandpass.md) → [`spectrometer_spectrum`](ops/optics/spectrometer/spectrometer_spectrum.md)

代替: [`grating_dispersion`](ops/optics/spectrometer/grating_dispersion.md), [`spectrometer_slit_image`](ops/optics/spectrometer/spectrometer_slit_image.md), [`illumination_train`](ops/optics/illumination/illumination_train.md), [`illumination_field`](ops/optics/illumination/illumination_field.md), [`coaxial_illumination`](ops/optics/illumination/coaxial_illumination.md)

限界: 鏡とレンズは無収差、カメラは歪曲の無い直線写像なので、帯域の幅は収差を入れない下限。高次の回折効率は 1 次との比の定数(模型)、偏光と blaze は入れない。照明は近軸で cos⁴ とレンズの収差を入れない。

実寸校正: 較正は無い(設計値から閉形式と数値の畳み込みで出す)。実機の分光器は輝線ランプで波長を較正し、装置関数は単色の線で測って差し替える。

動く例: `poc_spectrometer_illumination`

### [照明の円錐と観察の NA で、鏡面の小さな傾きを出す・消す(球冠の交わり → 傾きの帯 → 打痕・傷・梨地)](capabilities/illumination-cone-vs-na.md)

鏡面に近い金属部品では、浅い打痕(傾き 0.1〜0.5°)やヘアラインの上の傷、梨地のムラが「同軸落射で見えたり見えなかったりする」。どう見えるかは、光源の種類より先に**各点に届く光の円錐の半角 α と向き ψ**、それとカメラが受け取る円錐(物体側 NA、半角 β = asin NA)の関係で決まります。顕微鏡のケーラー照明でいう照明の NA と対物の NA、シュリーレン法のナイフエッジと同じ幾何です。

使う op: `solid_angle_light`, `solid_angle_boundaries`, `solid_angle_brightness`, `solid_angle_sweep`, `solid_angle_render`

推奨パイプライン: [`solid_angle_light`](ops/optics/illumination/solid_angle_light.md) → [`solid_angle_boundaries`](ops/optics/illumination/solid_angle_boundaries.md) → [`solid_angle_sweep`](ops/optics/illumination/solid_angle_sweep.md) → [`solid_angle_brightness`](ops/optics/illumination/solid_angle_brightness.md) → [`solid_angle_render`](ops/optics/illumination/solid_angle_render.md)

代替: [`light_source`](ops/optics/illumination/light_source.md), [`defect_contrast`](ops/optics/illumination/defect_contrast.md), [`lighting_sweep`](ops/optics/illumination/lighting_sweep.md), [`illumination_design`](ops/optics/illumination/illumination_design.md), [`micro_normals`](ops/optics/finish/micro_normals.md), [`blast_normals`](ops/optics/finish/blast_normals.md)

限界: 照明は各点に同じ円錐が届く遠方場の極限(ケーラー照明・光源を無限遠に置いた照明)、カメラはテレセン(どの画素も真上から同じ円錐)。Fresnel の反射率は小さな角では一定、回折・多重反射・円錐の中の放射輝度のむらは入れていない。粗さは微小面の傾きのガウス分布(σ 30° まで)。

実寸校正: 円錐の半角 α は照明の開口(絞り)の半径と照明レンズの焦点距離から α = atan(r/f)、観察の半角 β は物体側 NA の asin。境界 |α − β|/2・(α + β)/2 は鏡面の傾きの角度なので尺度の校正は要らないが、α と β の実測(光源像の大きさ・レンズの NA)が要る。

動く例: `poc_illumination_cone_vs_na`

### [凹んだ部品の相互反射を、測光の真値を保ったまま収束まで数える(3-D の形態係数・漸進ラジオシティ・検査用の多重反射描画)](capabilities/interreflection-to-convergence.md)

`render_optscene` は検査用の描画で、実在の照明器具を物理単位で置いて**直接光だけ**を数えます(測光に根拠があり、真値と突き合わせられる)。`render_studio` は多重反射まで解きますが、明るさの絶対値に意味がありません。加工ポケット・内角・箱の隅のような凹んだ部品では、向かいの壁で反射した光が底を照らすので、直接光だけのモデルを実写に合わせると、その分が反射率や照明の強さに**吸収されて、もっともらしく合ってしまいます**。

使う op: `form_factor_parallel_rects`, `form_factor_perpendicular_rects`, `form_factor_polygons`, `radiosity_patches`, `form_factor_matrix`, `radiosity_progressive_3d`, `render_optscene_gi`

推奨パイプライン: [`radiosity_patches`](ops/optics/radiosity/radiosity_patches.md) → [`form_factor_matrix`](ops/optics/radiosity/form_factor_matrix.md)

代替: [`render_optscene_gi`](ops/optics/radiosity/render_optscene_gi.md), [`radiosity_progressive_3d`](ops/optics/radiosity/radiosity_progressive_3d.md), [`render_optscene`](ops/optics/scene/render_optscene.md), [`render_studio`](ops/optics/scene/render_studio.md), [`transport_matrix_radiosity`](ops/optics/light_transport/transport_matrix_radiosity.md), [`form_factors_2d`](ops/optics/light_transport/form_factors_2d.md)

限界: Lambert(完全拡散)だけ。シーンは箱・箱をくり抜いたポケット・有限の板(球・円筒・鏡面・加工目・欠陥は拒否)。パッチ内のラジオシティは一様で、画素の相互反射は点 → 多角形の閉形式で集め直す(遮蔽はパッチ中心への光線 1 本)。

実寸校正: 照明の強さは線形に効き、幾何(形態係数・画素とパッチの対応)はシーンの形・カメラ・パッチの大きさの SHA-256 で使い回すので、反射率と照明の強さを動かす較正の繰り返しではラジオシティだけを解き直す。

動く例: `poc_pocket_interreflection`

### [光学設計ファイル(.zmx の逐次処方を読む・書く・分類する)](capabilities/lens-prescription-files.md)

市販の逐次光線追跡の設計ソフトが保存する処方のテキスト(`.zmx`)を、`lens_file_read` がそのまま `raytrace.lens_system` の処方にします。別の模型を作らないので、実光線(`spot_stats` / `ray_fan`)・Seidel 和(`seidel_coefficients`)・波面と PSF(`opd_map` / `psf_from_opd`)・色収差(`chromatic_shift`)・公差(`tolerance_analysis`)・最適化(`optimize_lens`)・断面図(`lens_section_drawing`)がそのまま使えます。視野と波長はファイルの並びのまま持ち、`lens_file_system` で 1 つ選んだ処方にします。直した処方は `lens_file_write` が同じ形式で書き戻し(視野・波長・まだ有効なソルブを保つ)、`lens_file_report` は読まずに全キーワードを「読む / 無視(理由つき)/ 扱えない」に分けます。硝材は材料表か、手元の `.agf`(`glass_dir` か環境変数 `FULLSEYE_GLASS_DIR`、`read_glass_catalog_agf` が読む)を名前の完全一致で引きます。

使う op: `lens_file_read`, `lens_file_system`, `lens_file_write`, `lens_file_report`

推奨パイプライン: [`lens_file_read`](ops/optics/lensfile/lens_file_read.md) → [`lens_file_system`](ops/optics/lensfile/lens_file_system.md) → [`paraxial_trace`](ops/optics/design/paraxial_trace.md) → [`spot_stats`](ops/optics/design/spot_stats.md) → [`lens_file_write`](ops/optics/lensfile/lens_file_write.md)

代替: [`lens_file_report`](ops/optics/lensfile/lens_file_report.md), [`read_glass_catalog_agf`](ops/optics/matprop/read_glass_catalog_agf.md), [`lens_system`](ops/optics/design/lens_system.md), [`optimize_lens`](ops/optics/optimization/optimize_lens.md), [`lens_section_drawing`](ops/optics/drawing/lens_section_drawing.md)

限界: 座標変換面(傾き・偏心・折り返し)は非共軸の追跡器へ読む(SCBD・物体空間を動かす先頭の変換・OBNA・像高の視野は拒否)。理想レンズ・トーリック・奇数次非球面は拒否。曲がった像面・温度、座標変換面と多構成の併用は allow_partial のときだけ近似として読む(多構成の表 MNUM は読み書きできる)。ソルブは保存値で読む。カタログに無い硝材は拒否(.agf を置く)。

実寸校正: 長さは mm に換算、波長は µm、視野は度(無限遠)か mm(有限の物体)。画素校正は不要。

動く例: `poc_lens_file_roundtrip`

### [材料の光学物性を 1 つの表で引く(硝材・結晶・半導体・金属・液体・プラスチック 86 種、一次文献の係数と数表、硝材カタログの取り込み口)](capabilities/material-optical-property-library.md)

観察用の光学系(レンズ・窓・鏡・膜)も観察対象(ウェハ・モールド・はんだ)も、見え方は材料の光学特性で決まります。これまで Fullseye は硝材 20 種の Sellmeier(`raytrace`)、金属 5 種の 5 点の n,k(`glassmirror`)、見た目のカタログ(`surfacelib` / `metalfinish`)が別々の名前空間にあり、同じ材料を光学系側と対象側で引く口がありませんでした。この回は**1 材料 = 1 レコード**の材料表を `materials` に作り、`opsoptics` の新カテゴリ `matprop` に 16 本を足しました。

使う op: `material_table`, `material_record`, `material_optical_constants`, `material_dispersion`, `material_extinction`, `material_absorption`, `material_transmittance`, `material_reflectance`, `abbe_number`, `glass_map`, `thermo_optic_coefficient`, `plate_focus_shift`, `silicon_free_carrier_absorption`, `material_from_sellmeier`, `material_from_curves`, `read_glass_catalog_agf`

動く例: `poc_material_optical_library`

### [近赤外のハイパースペクトルで見た目が同じ異物を選別する(材料表の吸収帯 → 散乱層の反射 → InGaAs の帯域ごとの電子数)](capabilities/nir-hyperspectral-sorting.md)

食品のライン(ナッツ・茶葉・米)に混じる殻・木片・樹脂片や、リサイクルの PET / PP / PE / PS は、色を合わせられると RGB のカメラでは分かりません。近赤外(0.9〜2.5 µm)では C-H の倍音・結合音と O-H の吸収帯が材料ごとに違うので、分光で分けられます。ここはその鎖を、観察対象と光学系が**同じ材料表**を引く形で組む 8 本です。

使う op: `material_nir_absorption`, `carbon_black_absorption`, `nir_model_info`, `ingaas_photodiode_qe`, `kubelka_munk_reflectance`, `spectral_reflectance_from_material`, `hyperspectral_band_weights`, `hyperspectral_capture`

推奨パイプライン: [`material_nir_absorption`](ops/optics/matprop/material_nir_absorption.md) → [`kubelka_munk_reflectance`](ops/optics/spectral/kubelka_munk_reflectance.md) → [`hyperspectral_capture`](ops/optics/spectral/hyperspectral_capture.md)

代替: [`spectral_reflectance_from_material`](ops/optics/spectral/spectral_reflectance_from_material.md), [`hyperspectral_band_weights`](ops/optics/spectral/hyperspectral_band_weights.md), [`ingaas_photodiode_qe`](ops/optics/spectral/ingaas_photodiode_qe.md), [`carbon_black_absorption`](ops/optics/matprop/carbon_black_absorption.md)

限界: 吸収帯の幅と強さは推定で実測のスペクトルに合わせていない。場面と分類器のライブラリを同じモデルから作ると逆犯罪になる。Kubelka–Munk は 2 流束の近似で、光沢・層の不均一・強い異方散乱は扱わない。InGaAs の QE は形のモデル。

実寸校正: 反射率は白板の電子数で割る平場補正(white_electrons)で読む。帯の中心は一次文献の実測、幅と強さは実測の帯(bands=...)に差し替える。

動く例: `poc_hyperspectral_foreign_matter`

### [非共軸の光学系(折り返しミラー・半透鏡・傾いた平板・シャインプルーフ・ゴースト)](capabilities/noncoaxial-optics.md)

`raytrace` の処方は光軸が 1 本の直線の共軸系でした。`raytrace3d` は面ごとに 3-D の姿勢(回転と原点)を持たせ、座標の切り替え(偏心してから x → y → z の順に回す。`undo` で逆順に戻す)、元の座標系への戻り、折り返しミラー(`fold_mirror`、45° で 90° 折れる)、傾いた平行平板や楔、平板の半透鏡(透過と反射の 2 本の枝)を組めます。面の式(円錐 + 偶数次の非球面)と屈折・反射の式は `raytrace` のままで、共軸の処方を変換した系は `raytrace.trace_rays` と 1e-12 で同じ交点・光路長になります。

使う op: `noncoaxial_system`, `noncoaxial_example`, `noncoaxial_layout`, `noncoaxial_trace`, `noncoaxial_spot`, `image_orientation`, `beamsplitter_branches`, `tilted_plate_shift`, `scheimpflug_tilt`, `surface_reflectance`, `ghost_analysis`, `ghost_image`, `ghost_path`, `noncoaxial_drawing`

推奨パイプライン: [`noncoaxial_system`](ops/optics/noncoaxial/noncoaxial_system.md) → [`noncoaxial_trace`](ops/optics/noncoaxial/noncoaxial_trace.md) → [`image_orientation`](ops/optics/noncoaxial/image_orientation.md) → [`ghost_analysis`](ops/optics/noncoaxial/ghost_analysis.md) → [`noncoaxial_drawing`](ops/optics/drawing/noncoaxial_drawing.md)

代替: [`lens_system`](ops/optics/design/lens_system.md), [`spot_stats`](ops/optics/design/spot_stats.md), [`tilted_plate_shift`](ops/optics/noncoaxial/tilted_plate_shift.md), [`scheimpflug_tilt`](ops/optics/noncoaxial/scheimpflug_tilt.md), [`surface_reflectance`](ops/optics/noncoaxial/surface_reflectance.md), [`lens_section_drawing`](ops/optics/drawing/lens_section_drawing.md)

限界: ゴーストは 2 回反射まで(3 回以上・散乱・鏡筒の迷光は持たない)。各面の反射率は視野の主光線の入射角での無偏光の値で、半透鏡の膜は与えた R(角度・波長の依存なし)。光線の狙いは絞りの点への Newton 法(狙えない光線は無効として数える)。近軸量(EFL・瞳)は共軸の処方から変換した系だけで、ほかは実光線の近軸極限で焦点を求める。

実寸校正: 長さは mm、角度は度。処方の数値がそのまま実寸で、校正は要らない。

動く例: `poc_noncoaxial_optics`

### [光の反射・屈折・干渉を計算する](capabilities/optics-and-materials.md)

Fresnel の反射率、薄膜干渉の色、回折格子の色、ベクトル形の屈折(光線ごとの全反射判定つき)を、実在の硝材の分散を含めて計算します。

使う op: `fresnel_dielectric`, `thin_film_reflectance`, `grating_rgb`, `refract_rays`

推奨パイプライン: [`fresnel_dielectric`](ops/optics/interface/fresnel_dielectric.md) → [`thin_film_reflectance`](ops/optics/appearance/thin_film_reflectance.md) → [`thin_film_rgb`](ops/optics/appearance/thin_film_rgb.md)

代替: [`fresnel_conductor`](ops/optics/interface/fresnel_conductor.md), [`brewster_angle_deg`](ops/optics/interface/brewster_angle_deg.md), [`grating_rgb`](ops/optics/appearance/grating_rgb.md), [`refract_rays`](ops/optics/glassbody/refract_rays.md), [`fresnel_reflectance`](ops/3d/optics/fresnel_reflectance.md)

限界: `refract` は 1 本でも全反射があるとバッチ全体が `None`(`refract_rays` を使う)。`fresnel_dielectric` は実屈折率のみ —— 金属は `fresnel_conductor`。

実寸校正: 波長 [nm]・屈折率は無次元、角度は cos で渡す。画素校正は不要。

動く例: `glass_and_mirror_optics`, `appearance_structural_colour`

### [ピクセルシフト撮像(1 画素シフトで全色、半画素シフトで折り返しを消す、壊れる条件まで)](capabilities/pixel-shift-imaging.md)

撮像素子を圧電アクチュエータで 1 画素 / 半画素ずつ動かして複数枚撮り、格子へ合わせる撮り方を、撮る側と合わせる側の両方で再現します。`pixelshift` の 6 本は `opsoptics` の族 `pixelshift` です。

使う op: `pixel_shift_pattern`, `pixel_shift_capture`, `pixel_shift_merge`, `pixel_shift_motion_mask`, `false_color_metric`, `pixel_shift_resolution_budget`

推奨パイプライン: [`pixel_shift_resolution_budget`](ops/optics/pixelshift/pixel_shift_resolution_budget.md) → [`pixel_shift_pattern`](ops/optics/pixelshift/pixel_shift_pattern.md) → [`pixel_shift_capture`](ops/optics/pixelshift/pixel_shift_capture.md) → [`pixel_shift_motion_mask`](ops/optics/pixelshift/pixel_shift_motion_mask.md) → [`pixel_shift_merge`](ops/optics/pixelshift/pixel_shift_merge.md) → [`false_color_metric`](ops/optics/pixelshift/false_color_metric.md)

代替: [`drizzle_resample`](ops/astrostack/stack/drizzle_resample.md), [`align_frames`](ops/astrostack/align/align_frames.md), [`raw_demosaic_bilinear`](ops/gfx2d/isp/raw_demosaic_bilinear.md)

限界: 合わせる側は公称のシフトが 1/scale 画素の格子に乗る場合専用。傾いたエッジの MTF50 は 1 枚でもシフトしても同じで(開口の sinc は動かない)、レンズが先に落ちていれば何も戻らない(PoC)。撮る側は理想の撮像素子で、雑音は呼び手が足す。

実寸校正: 実寸は 1 枚撮りと同じ画素ピッチ ÷ 倍率。半画素シフトで合わせた 2 倍の格子では 1 画素がその半分になる。シフトそのものは公称で合わせるので、圧電の誤差は `pixel_shift_pattern(error_px=…)` で見積もる。

動く例: `poc_pixel_shift`

### [偏光 4 方向で鏡面反射を除く(誘電体と金属で分ける)](capabilities/polarisation-specular-removal.md)

偏光板を 0/45/90/135° に回した 4 枚(または DoFP センサの 4 画素)から、画素ごとに Malus の正弦波を当てはめ、**無偏光成分**(2·I_min)と**直線偏光成分**(I_max − I_min)に分けます。前者を拡散・後者を鏡面と呼ぶのは物理的仮定で、それが成り立つ誘電体と成り立たない金属を、この項目は分けて扱います。

使う op: `polarization_dolp_map`, `polarization_separate`, `polarization_stokes`, `specular_diffuse_split`

推奨パイプライン: [`polarization_dolp_map`](ops/specular/polarization/polarization_dolp_map.md) → [`polarization_separate`](ops/specular/polarization/polarization_separate.md) → [`polarization_stokes`](ops/specular/polarization/polarization_stokes.md) → [`stokes_analyze`](ops/optics/polarization/stokes_analyze.md) → [`specular_diffuse_split`](ops/specular/dichromatic/specular_diffuse_split.md)

代替: [`fresnel_conductor`](ops/optics/interface/fresnel_conductor.md), [`fresnel_dielectric`](ops/optics/interface/fresnel_dielectric.md), [`brewster_angle_deg`](ops/optics/interface/brewster_angle_deg.md), [`specular_free_transform`](ops/specular/dichromatic/specular_free_transform.md), [`specular_coefficient_map`](ops/specular/dichromatic/specular_coefficient_map.md)

限界: 分離が厳密なのは「鏡面が完全直線偏光」のとき = 誘電体の Brewster 角近傍だけ。金属は鏡面が部分偏光で、偏光度 p の残り (1−p)·S が **diffuse に残る**(`example_polarization_metal` が閉形式と一致させて示す)。法線入射では鏡面も無偏光で全部 diffuse。順序違いは等間隔角度では**検出できない**(全順列で違反率 0、実測)。

実寸校正: 画素校正は不要。`max_violation_frac` は雑音床で決める —— 違反は無偏光成分 D が 2〜3σ を切る画素で起き、その割合が目安(実測表は `specular_photometric.md`)。

動く例: `example_polarization_metal`, `poc_polarization_specular`, `specular_photometric`

### [偏光カメラの生フレームを Stokes・DoLP・Mueller に読む](capabilities/polarization-imaging.md)

偏光カメラ(画素の上に偏光子を載せた市販の偏光イメージセンサを使う機種)は 2×2 の画素ブロックに 0/45/90/135 度の偏光子を並べた**モザイク**を 1 枚で出します。`polarization_demosaic` がそれを 4 枚(0/45/90/135)に戻し(双線形。1 次の場は厳密に戻り、縁はモザイクを鏡映して位相を保つ)、そのまま `polarization_stokes` / `polarization_dolp_map` / `polarization_separate` に渡せます(角度の既定が一致しているので引数無しで繋がる)。センサの配列が違えば `layout=((a00, a01), (a10, a11))` で渡します。**カラー偏光センサ**(4×4 ブロック)は `polarization_demosaic_color` が (4, H, W, 3) に戻します —— 各偏光子位置の画素は半解像度の Bayer なので `raw_demosaic_bilinear` で展開し、戻してから各チャネルを偏光 demosaic する(2 つの厳密な段の合成)。

使う op: `polarization_demosaic`, `polarization_demosaic_color`, `polarization_stokes`, `polarization_dolp_map`, `polarization_separate`, `stokes_analyze`, `mueller_from_intensities`, `mueller_checks`, `mueller_element`, `mueller_apply`

動く例: `polarization_camera_pipeline`, `poc_polarization_specular`

### [Bayer の生フレームを、段ごとに説明できる式で表示画像にする](capabilities/raw-to-display-isp.md)

カメラの ISP(Image Signal Processor)が RAW から RGB を作るまでの典型段を、**全部閉じた式**で持っています(gfx2d 台帳の `isp`)。黒レベル `raw_black_level`(台座を引いて白を 1 に)→ 欠陥画素 `raw_dead_pixel_mask` / `raw_dead_pixel_correct`(同色 8 近傍の全部から同じ向きに閾値以上ずれた画素を中央値で置く)→ 周辺減光 `lens_shading_gain` / `lens_shading_correct`(白い板を撮った flat から色ごとの利得地図)→ ホワイトバランス `awb_gains`(gray-world / white-patch)を `raw_apply_gains`(モザイク側)か `rgb_apply_gains` で → デモザイク `raw_demosaic_bilinear`(NumPy だけの双線形。OpenCV があれば `cfa_to_rgb` も)→ 色補正行列 `color_correction_matrix`(行和 1 に正規化して白を白のまま)→ `hue_saturation`(BT.601 の色差を回す・伸ばす)→ `brightness_contrast`(中灰を軸に)。`gamma` は既存 op。

使う op: `raw_black_level`, `raw_dead_pixel_mask`, `raw_dead_pixel_correct`, `lens_shading_gain`, `lens_shading_correct`, `awb_gains`, `raw_apply_gains`, `rgb_apply_gains`, `raw_demosaic_bilinear`, `color_correction_matrix`, `hue_saturation`, `brightness_contrast`, `cfa_to_rgb`, `gamma`

動く例: `raw_to_display_isp`

### [光源 × 対象 × センサの分光の鎖(Planck・CIE A・LED・フィルタ・Si の QE、曲線の積と積分)](capabilities/spectral-radiometry-chain.md)

像の明るさは、光源の分光分布 × 光学系と対象の透過・反射 × センサの量子効率を波長で積分した値で決まります。材料の透過率・反射率は `materials` が pairs(λ [nm], 値)で返しますが、光源とセンサの曲線が op として無く、「この光源で、このウェハ越しに、このセンサで何電子になるか」を組めませんでした。`spectralrad` の 9 本がその残り半分で、どの曲線も同じ pairs で返します。

使う op: `blackbody_spectrum`, `cie_illuminant_a`, `led_spectrum`, `bandpass_spectrum`, `silicon_photodiode_qe`, `energy_to_photons`, `spectral_product`, `spectral_integral`, `spectral_stats`

動く例: `poc_nir_silicon_transmission`

### [TDI ラインスキャンとラインスキャン用レンズ(段数と SNR → 同期ずれの MTF → 像高ごとの照度と MTF)](capabilities/tdi-linescan-and-lens.md)

フィルム・鋼板・ガラス・印刷物・ウェハのように流れてくるものはラインセンサで撮ります。暗いラインでは TDI(時間遅延積分)で N 段ぶん露光を積み、その代わりに搬送とラインレートの同期が画質を決めます。長いラインセンサ(8k × 7 µm = 57 mm など)は普通の C マウントレンズの像円に収まらないので、ラインスキャン用のレンズを使います。`linescan` の 6 本はこの 3 つを数で扱います。

使う op: `tdi_snr`, `tdi_sync_mtf`, `linescan_acquire`, `lens_field_profile`, `linescan_lens_columns`, `linescan_lens_example`

推奨パイプライン: [`tdi_snr`](ops/optics/linescan/tdi_snr.md) → [`tdi_sync_mtf`](ops/optics/linescan/tdi_sync_mtf.md) → [`linescan_lens_example`](ops/optics/linescan/linescan_lens_example.md) → [`lens_field_profile`](ops/optics/linescan/lens_field_profile.md) → [`linescan_lens_columns`](ops/optics/linescan/linescan_lens_columns.md) → [`linescan_acquire`](ops/optics/linescan/linescan_acquire.md)

代替: [`lens_system`](ops/optics/design/lens_system.md), [`emva_snr_curve`](ops/optics/sensorchar/emva_snr_curve.md), [`relative_illumination`](ops/optics/geometric/relative_illumination.md)

限界: レンズの模型は実在の型番の処方ではない(数字を特定のレンズの性能として引用しない)。ぼけは列ごとのガウス近似、同期の模型は一定の ε とライン周期ごとの ε まで。C マウントの流用では像高 19.7 mm から光が届かず、フラットフィールド補正で照度は揃っても MTF と欠陥の CNR は戻らない(PoC)。

実寸校正: 流れ方向の 1 画素は搬送速度 / ラインレートで決まるのでエンコーダ同期で取る(速度誤差 2 %・64 段で掃引 1.28 px、0.25 c/px の MTF 0.84)。幅方向は画素ピッチ / 倍率で、両方向とも既知長さの的で確かめる。

動く例: `poc_tdi_linescan`

### [薄膜の膜厚を分光反射率で測る(転送行列 → 干渉色 → FFT・モデルあてはめ・膜厚マップ)](capabilities/thin-film-reflectometry.md)

Si 上の SiO₂・Si₃N₄、コート、AR 膜の膜厚は、反射スペクトルの干渉縞から非接触で測ります(分光干渉式の膜厚計)。`filmoptics` の 5 本は、膜も基板も材料表(`materials`)の鍵で受けます。観察用の光学系と観察対象が同じ材料表を引くので、膜の n,k をどこかで別に持つ必要がありません。

使う op: `multilayer_reflectance`, `film_color`, `film_thickness_fft`, `film_thickness_fit`, `film_thickness_map`

推奨パイプライン: [`multilayer_reflectance`](ops/optics/film/multilayer_reflectance.md) → [`film_thickness_fft`](ops/optics/film/film_thickness_fft.md) → [`film_thickness_fit`](ops/optics/film/film_thickness_fit.md) → [`film_thickness_map`](ops/optics/film/film_thickness_map.md)

代替: [`thin_film_reflectance`](ops/optics/appearance/thin_film_reflectance.md), [`film_color`](ops/optics/film/film_color.md)

限界: 直入射のモデルは顕微分光の膜を薄く読む(実測で −5.7 %、NA を入れると −2.7 %)。FFT は縞 2 本未満(400〜800 nm の SiO₂ で約 540 nm 未満)で破綻。RGB は色が周期的に似るので次数を取り違える画素が残る。

実寸校正: 反射率の絶対値は裸の Si(材料表の Si の Fresnel)を基準にする(実測と中央値 0.4 % 差)。任意単位の分光器は fit_scale=True、カメラは裸の Si の領域で白を合わせる。

動く例: `poc_thin_film_reflectometry`

## 波と信号 (5)

### [配列で方向を測り、距離と速度を分ける](capabilities/beamforming-and-range-doppler.md)

素子配列の受信からビームを立てて到来角を出し、FMCW の受信から距離-速度面を作って検出を距離 [m] と速度 [m/s] に戻します。

使う op: `beamform_delay_sum`, `beamform_doa`, `range_doppler_map`, `range_doppler_peaks`

推奨パイプライン: [`beamform_doa`](ops/rangedoppler/beamform/beamform_doa.md) → [`range_doppler_map`](ops/rangedoppler/process/range_doppler_map.md) → [`range_doppler_peaks`](ops/rangedoppler/process/range_doppler_peaks.md)

代替: [`beamform_delay_sum`](ops/rangedoppler/beamform/beamform_delay_sum.md)

限界: 語彙は電波レーダ向け。音響は `eta = 1/c` で読み替え、`beamform_doa` の距離・速度はパルス測深機に対応物が無い。素子スナップショット 1 枚を渡す口が無く立方体へ水増しが要る(`poc_multibeam_bathymetry` §11)。

実寸校正: 画素校正は無い。距離 [m] と速度 [m/s] は搬送波周波数・チャープ帯域・サンプル率から op が出すので、その 3 つを実機の設定値で渡す。

動く例: `poc_multibeam_bathymetry`, `poc_bev_sensor_fusion`

### [うなりは一つ(膜のモード・干渉縞・回折次数・印刷のモアレ・墨に落とす)](capabilities/beats-fringes-and-screens.md)

膜の固有モードと節線、二重スリットの干渉縞、回折格子の次数、そして印刷の網点・モアレ・彫版線・ハッチ・モザイクを作り、**どれも絵の外にある真値で採点します**。

使う op: `wave_membrane_mode`, `wave_mode_frequencies`, `wave_nodal_lines`, `wave_two_slit`, `wave_fringe_period`, `wave_grating_orders`, `halftone_screen`, `halftone_moire_period`, `engrave_lines`, `hatch_field`, `mosaic_tiles_sites`, `mosaic_tiles_render`

動く例: `poc_beats_fringes_and_screens`

### [干渉計の共振器・量子雑音の予算・色つき雑音の中の既知波形を閉形式で設計する(重力波望遠鏡の式を検査装置の干渉計・振動計・AE に)](capabilities/gw-interferometer-quantum-noise-and-matched-filter.md)

重力波望遠鏡は km 級の Michelson 干渉計の両腕に Fabry-Perot 共振器を置き、腕の長さの差を光量で読む装置です。その設計の式は、検査装置のエタロン(波長フィルタ)・レーザー共振器・白色干渉計・振動計の式と同じで、Fullseye にはこれまで共振器そのものと量子雑音の予算、そして**雑音の PSD で割る整合フィルタ**が 1 本もありませんでした。この回は 12 本を 2 つの台帳に足しました。

使う op: `fabry_perot_response`, `cavity_strain_transfer`, `michelson_dc_readout`, `pdh_error_signal`, `quantum_noise_budget`, `psd_welch`, `whiten_by_psd`, `chirp_newtonian`, `chirp_mass_from_track`, `matched_filter_snr`, `optimal_snr`, `coincidence_delay`

動く例: `poc_gw_detector_pseudo_simulation`

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

## 組み立てる (7)

### [位置を合わせて重ねる](capabilities/align-and-stack.md)

画像列の平行移動を投票で合わせ、サブピクセルで再標本して重ねます。点群は ICP で合わせられます。

使う op: `frame_align`, `drizzle_resample`, `icp_point2point_3d`, `interp_scattered`

推奨パイプライン: [`align_frames`](ops/astrostack/align/align_frames.md) → [`drizzle_resample`](ops/astrostack/stack/drizzle_resample.md) → [`frame_quality`](ops/astrostack/quality/frame_quality.md)

代替: [`frame_align`](ops/astrostack/align/frame_align.md), [`icp_point2point_3d`](ops/3d/refine/icp_point2point_3d.md), [`register_cross`](ops/3d/fusion/register_cross.md), [`interp_scattered`](ops/math/interp_poly/interp_scattered.md)

限界: 繰り返し構造(網点・格子)では `frame_align` が `inlier_ratio` 1.00 のまま 80.85 px 外す —— `vote_margin` を併せて見る。合わせすぎると欠陥が消える(`poc_cad_scan_deviation`)。

実寸校正: 合わせは px のまま。変位を実寸にするなら既知寸法の的を同じ光学系で測り `mm_per_px_from_reference` → `pixel_to_world`。

動く例: `poc_astro_photometry`, `poc_registration_basin`

### [基準画像(ゴールデン)と比べて欠陥を測り、ロットごと判定する](capabilities/golden-compare.md)

現場でいちばん多い検査は「良品の画像と比べて違うところを探す」です。`fullseye/golden.py` の `compare_to_golden(image, golden)` はそれを 1 回の呼び出しにします —— 位相相関で整数並進を合わせ(`max_shift` を超える推定は採用せず `align_ok=0` で返す)、任意でガウス平滑してから差分 `|image − golden|` を取り、`threshold` を超えた画素を検査領域 `mask` の中で連結成分にして `min_area` 未満を落とし、計測 dict `{shift_row, shift_col, align_ok, ssim, psnr, max_diff, mean_diff, defect_area, defect_count, defect_area_max, valid_fraction}` と差分の絵(`diff` / `defect_mask` / `labels`)を返します。位置合わせで画像の外から巻き込んだ縁は `valid` から外し、欠陥にも平均にも数えません。

使う op: `compare_to_golden`, `golden_measure`, `golden_spec`, `inspect_batch`, `judge`, `ssim`, `psnr`

動く例: `golden_compare`

### [既知の良品/不良品セットで検査レシピと仕様を配備前に検定し、余裕を測る](capabilities/inspection-fixture.md)

レシピ(前処理)と計測と仕様を決めたあと、現場が最初に聞くのは「良品は全部通り、不良品は全部止まるのか」と「どれくらい余裕があるのか」です。`fullseye/fixture.py` の `inspection_fixture(good, bad, recipe, measure=..., spec=...)` は、既知の良品セットと不良品セット(フォルダまたはパス列)をそれぞれ `inspect_batch` で回し、**良品が全部 `ok` かつ不良品が全部 `ng` のときだけ `passed=True`** を返します。混同表 `confusion`、見逃した不良品の行 `escapes`、過検出した良品の行 `false_rejects`、読めなかった行 `errors` を並べ、`spec_margins` が仕様キーごとに**良品の計測が限界にどれだけ近いか**(`min_margin`、負なら超過。`tol` や max−min で正規化した `min_margin_norm` は 1.0 が限界幅ぶんの余裕)を出します。`detail` は「passed: good 6/6 ok, bad 4/4 ng; tightest margin bright_px=1.00 of limit width」のような 1 行です。

使う op: `inspection_fixture`, `spec_margins`, `inspect_batch`, `judge`

動く例: `inspection_fixture`

### [フォルダを一括検査し、仕様で判定し、集計・SPC・レポート・監査ログまで出す](capabilities/inspection-workflow.md)

op が 931 本あっても、ライン担当が最初に触る形は「画像フォルダを指して、前処理と計測を決め、仕様で良否をつけ、集計とレポートをもらう」です。`fullseye/inspect_batch.py` の `inspect_batch(folder, recipe, measure=..., spec=...)` はその 1 回の呼び出しで、各画像を **読む → recipe(`run_pipeline` の stages)→ `measure`(計測 op を束ねた callable → dict)→ `judge`(仕様照合)** に通し、行ごとに入力ファイルの sha256・計測値・根拠つきの Verdict・所要時間を返します。数値の計測列は時系列にまとめ、2 点以上あれば EWMA(`spc_ewma`)で工程が管理状態かを添えます。`report_path` の拡張子で `.xlsx` / `.md` / `.jsonl` に書き分け、`audit_path` を渡すと 1 行 1 JSON の監査ログに追記します。

使う op: `inspect_batch`, `judge`, `as_verdict`, `run_pipeline`, `spc_ewma`, `save_xlsx_report`, `report`, `to_json_lines`

動く例: `inspection_workflow`

### [op の返り値(型付き)を JSON に出し、bit そのままで戻す](capabilities/typed-results-as-json.md)

op の返り値は `image` / `region` / `points` / `contour` / `feature` / `matrix` / `signal` … の**型(sort)**を持つ NumPy 配列や小さな dict で、次の op に渡すには良くても、ファイル・ログ・LLM・別プロセスには渡せません。`to_json(value, sort)` が sort ごとに**一つ**の JSON 形を与え、`from_json(text)` が `(value, sort)` に戻します。封筒は自己記述(`{"fullseye_sort": "points", "version": 1, "payload": …}`)で、戻すときに型の指定は要りません。

使う op: `to_json`, `from_json`, `to_jsonable`, `from_jsonable`, `save_json`, `load_json`, `to_json_lines`, `from_json_lines`, `as_value`, `apply_json`, `is_envelope`

動く例: `typed_results_json`

### [op の返り値(型付き)を Markdown で読める形にし、JSON を埋め込んで戻す](capabilities/typed-results-as-markdown.md)

JSON と Markdown は一緒に使う場面が多い —— 結果を報告書の中に貼る、数の表を「読ませる」、レビューに残す。機械に厳密な JSON 形(能力ノート `typed-results-as-json`)に対し、`fullseye/mdio.py` は**人が読む形**と、その**間の橋**を与えます。

使う op: `to_markdown`, `json_block`, `extract_json`, `report`

動く例: `typed_results_markdown`

### [型付きの検査結果を Excel(.xlsx)レポートに書き出す](capabilities/xlsx-report.md)

検査の結果は現場では Excel で回ることが多い —— 測定表を貼る、良否を並べる、プレビュー画像を添える。`fullseye/xlsxio.py` の `save_xlsx_report(sections, path)` は、能力ノート `typed-results-as-markdown` の `report` と**同じ材料**(`(見出し, value, sort)` の列)から、そのまま `.xlsx` を作ります。`table` / `points` / `matrix` / `signal` / `vector` / `keypoints` / `counts` は本物のセルの表に、`feature` / `scalar` は 1 セルに、画像系(`image` / `color` / `region` …)はサムネイルを 1 枚埋め込みます。jsonio が「機械が bit で戻せる JSON」、mdio が「人が読む Markdown」なのに対し、xlsxio は「**現場が配る Excel**」—— 出力先が違うだけで、同じ 1 つの `sections` から 3 系統すべてを出せます。

使う op: `save_xlsx_report`, `report`, `to_markdown`, `save_json`

動く例: `xlsx_report`

## 見せる (5)

### [結果を人が読める図にする](capabilities/figures-and-annotation.md)

パネルを並べた図、寸法や矢印の注釈、高さの疑似カラー、SDF から起こした立体のレンダリングまで、**fullseye 自身の op** で作れます。外部の作図ライブラリを挟まずに、出力そのものを図にできます。

使う op: `annotate_figure_grid`, `colorize_height`, `render_beauty`

推奨パイプライン: [`annotate_figure_grid`](ops/annotate/paper/annotate_figure_grid.md) → [`annotate_panel_label`](ops/annotate/paper/annotate_panel_label.md) → [`annotate_scale_bar`](ops/annotate/paper/annotate_scale_bar.md) → [`annotate_colorbar`](ops/annotate/paper/annotate_colorbar.md)

代替: `colorize_height`, [`render_beauty`](ops/3d/render/render_beauty.md), [`annotate_legend`](ops/annotate/paper/annotate_legend.md), [`annotate_inset`](ops/annotate/paper/annotate_inset.md)

限界: 疑似カラーの選び方で**無い境目**が見える(`poc_colormap_readability`)。`annotate_figure_grid` の `letters=True` と手書きの (a) が二重になる。

実寸校正: `annotate_scale_bar` の `units_per_pixel` は `mm_per_px_from_reference` で**実測**した mm/px を渡す(公称倍率で描いたスケールバーは嘘の長さになる)。

動く例: `poc_colormap_readability`, `poc_dem_terrain`

### [結果を、触って見られる 1 枚の HTML にする(タブ・バッジ・3-D・動画・多言語)](capabilities/interactive-poc-viewer.md)

PoC や計測の結果を、**自己完結した 1 枚の HTML ビューア**にします。暗色で、素の WebGL と 2-D canvas だけ、外部ライブラリも外部 URL の読み込みも無く、`file://` でも iPhone の Safari でも動きます。同じ課題を違う方法で試した記録を**タブ**に並べ、各タブに正直な**バッジ**(門を通った / 限界を見せる / 何もしない場合)・短い説明・実測の数字を付けます。

使う op: `write_viewer`, `viewer_spec`, `viewer_points_tab`, `viewer_mesh_tab`, `viewer_frames_tab`, `viewer_split_tab`

動く例: `interactive_poc_viewer`

### [地の色を知らずに線と領域を描く(反転色)](capabilities/inverted-colour-overlays.md)

検査画像に測定線や ROI を重ねるとき、**地が明るいか暗いか分からない**のが普通です。白で描けば白飛びの上で消え、黒で描けば影の上で消えます。反転色は「その場の色をひっくり返して描く」ことでこれを避ける古典手で、`annotate_invert_path` が折れ線(アンチエイリアス・破線可)、`annotate_invert` が領域を、`draw="fill"` で中身ごと、`draw="margin"` で輪郭だけ反転します(HALCON の `set_draw` と同じ語)。

使う op: `annotate_invert`, `annotate_invert_path`, `annotate_invert_visibility`

推奨パイプライン: [`annotate_invert_visibility`](ops/annotate/overlay/annotate_invert_visibility.md) → [`annotate_invert`](ops/annotate/overlay/annotate_invert.md) → [`annotate_invert_path`](ops/annotate/overlay/annotate_invert_path.md)

代替: [`annotate_legend`](ops/annotate/paper/annotate_legend.md), [`text_box`](ops/annotate/text/text_box.md)

限界: 中間調で消える(8bit グレー `v ∈ [113, 142]` の 30/256 階調、`v=128` で比 1.014)。測るのは WCAG **輝度**比だけ。`alpha` を落とすと答えが変わる。地がグレーなら彩度のある色のほうが確実。

実寸校正: 描画のみ。実寸校正は不要。

動く例: `annotate_paper_tour`

### [点群をそのまま色の絵にする](capabilities/point-cloud-to-picture.md)

面を張れない点群 —— 細胞の位置、LiDAR、SfM の疎な点、粒子 —— を、点のまま RGB の絵にします。点は小数画素の位置に足跡(gaussian / disc / point)を落とし、**深さの順に**アルファ合成(over)するか、**光の総量を保って**足します(add、数の密度の地図になる)。カメラは `project_points` / `render_point_depth` と同じ OpenCV の規約(+Z が前)で、正射影は K を省くと点群を画像に収めます。

使う op: `points_render`, `render_point_depth`, `project_points`

推奨パイプライン: [`points_render`](ops/3d/render/points_render.md)

代替: [`render_point_depth`](ops/3d/render/render_point_depth.md), [`points_activity_video`](ops/conngraph/activity/points_activity_video.md), [`gs_render`](ops/drive/gsplat/gs_render.md), `render_mesh`

限界: 正射影の自動の収め方は R, t を当てた後の XY の箱で決まる(透視は K が要る)。disc の足跡は画素に量子化されるので、像の重心は半径 1〜1.5 画素で最大 0.05 画素ずれる(小数画素の位置を見るなら gaussian、1e-3 画素以内)。over は点ごとの不透明度で重ねるので、奥の密度は手前に隠れる —— 数を見るなら add。点 × 足跡の組が 4,000 万を超える描画は拒否する。

実寸校正: 画素校正は無い。縮尺が要るなら K の fx(画素 / 座標単位)から スケールバーを置く(annotate_scale_bar)。

動く例: `points_render_basics`, `poc_flybrain_pointcloud`

### [画像の上に、文字と表を置きたい場所へ置く](capabilities/text-and-tables-on-images.md)

検査画像や解析結果に、**位置を指定して**文字を焼き込めます。`text_box` は 9 方向のアンカー・半透明の板・折り返し、`annotate_text_path` は折れ線に沿った配置で、**斜め**(接線角に 1 字ずつ回す)・**縦書き**(`upright=True`)・**改行**(`\n`)・経路に沿ったそろえ(`anchor="start"/"center"/"end"`)・線に触れさせない**法線オフセット**が使えます。字は色(役割名または RGB)に加えて、合成の **Bold / Italic** も指定できます。

使う op: `text_box`, `annotate_text_path`, `annotate_text_path_layout`, `annotate_table`, `annotate_table_layout`, `measure_text`

推奨パイプライン: [`measure_text`](ops/annotate/text/measure_text.md) → [`annotate_text_path_layout`](ops/annotate/paper/annotate_text_path_layout.md) → [`annotate_text_path`](ops/annotate/paper/annotate_text_path.md) → [`annotate_table_layout`](ops/annotate/paper/annotate_table_layout.md) → [`annotate_table`](ops/annotate/paper/annotate_table.md)

代替: [`text_box`](ops/annotate/text/text_box.md), [`annotate_panel_label`](ops/annotate/paper/annotate_panel_label.md)

限界: 本文組版ではない(縦中横・句読点寄せ無し)。Bold / Italic は合成。はみ出しと桁数不揃いは黙って切らず例外。

実寸校正: 描画のみ。`font_size` は px。実寸校正は不要。

動く例: `annotate_paper_tour`

## 描く (4)

### [写真を 1 本の線にする(点描 → 巡回路 → 回る円)](capabilities/one-stroke-drawing.md)

写真の**濃淡**を、紙から鉛筆を離さずに引ける**1 本の閉じた線**に変えます。濃いところで線が密になるので、離れて見ると元の絵の階調が戻ります。巡回路は閉じているので、そのまま**複素フーリエ級数**に載り、**回る円の連鎖**として描き直せます。出口は既存の G-code op なので、ペンプロッタで実際に引けます。自分の写真で走らせる口も付いています::

使う op: `stipple_points_from_image`, `stipple_energy`, `stroke_tour_closed`, `mst_length`, `stroke_resample_closed`, `stroke_tone_error`, `contour_fourier_complex`, `contour_epicycle_chain`, `contour_fourier_truncation_energy`

動く例: `poc_one_stroke_epicycles`

### [光学系の図面(レンズ断面図・撮像系の設置図・単レンズの製作図を SVG / DXF で)](capabilities/optics-drawings.md)

`raytrace` の処方(`lens_system` の table)と `optscene.vision_layout` の撮像系から、打ち合わせと製作に使う図を出します。`lens_section_drawing` はレンズの子午断面図で、面は処方の円錐 + 非球面の sag、コバと平らな座、絞り、像面、視野ごとに色を分けた実光線(絞りを狙って追跡するので、入射瞳が無限遠のテレセンでも描けます)、EFL・BFL・全長・像高の寸法線、処方表を描きます。`vision_setup_drawing` は側面図と上面図で、カメラ・視野の錐・作動距離・被写界深度の帯と、照明 5 種(リング・ドーム・バー・同軸・バックライト)の位置と仰角を寸法つきで描きます。`lens_element_drawing` は単レンズの製作図で、ISO 10110 の 3 分割の表(左の面・材料・右の面)に R・有効径・3/ 4/ 5/、n_d・ν_d と 0/ 1/ 2/ を書き、公差は `tolerance_analysis` の公差の辞書から写して EFL の Monte-Carlo の幅を注記に残します。

使う op: `lens_section_drawing`, `vision_setup_drawing`, `lens_element_drawing`, `drawing_svg`, `drawing_dxf`, `drawing_raster`, `svg_entities`, `dxf_entities`

推奨パイプライン: [`lens_section_drawing`](ops/optics/drawing/lens_section_drawing.md) → [`drawing_svg`](ops/optics/drawing/drawing_svg.md) → [`drawing_dxf`](ops/optics/drawing/drawing_dxf.md) → [`svg_entities`](ops/optics/drawing/svg_entities.md) → [`dxf_entities`](ops/optics/drawing/dxf_entities.md)

代替: [`vision_setup_drawing`](ops/optics/drawing/vision_setup_drawing.md), [`lens_element_drawing`](ops/optics/drawing/lens_element_drawing.md), [`drawing_raster`](ops/optics/drawing/drawing_raster.md), [`paraxial_trace`](ops/optics/design/paraxial_trace.md), [`tolerance_analysis`](ops/optics/design/tolerance_analysis.md)

限界: 鏡・傾き・偏心のある処方の断面図、接合レンズと非球面の製作図は描かない(ValueError)。製作図の ISO 10110 の表記は公開の解説で確かめた範囲。設置図の鏡筒とカメラ本体の大きさは仮の寸法で、作動距離は物体から主点まで(薄肉の模型)。

実寸校正: 図は計算値そのものを実寸の mm で描くので、尺度の校正は要らない。SVG は紙の大きさ = 図 × 縮尺(100 % 表示・印刷で縮尺どおり)、DXF はモデル空間の 1 単位 = 1 mm。

動く例: `poc_optics_drawings`

### [目が嘘をつく絵を作って、測る側を採点する(錯視・無限描画・循環動画)](capabilities/pictures-that-carry-their-own-truth.md)

**真値が最初から付いている画像**を作ります。Fullseye のほとんどの op は与えられた 画像を測る側にいますが、この族だけが反対側にいます。

使う op: `illusion_cafe_wall`, `illusion_muller_lyer`, `illusion_checker_shadow`, `illusion_kanizsa`, `illusion_fraser_spiral`, `illusion_ground_truth`, `perpetual_elementary_ca`, `perpetual_langtons_ant`, `perpetual_apollonian`, `perpetual_flow_field`, `perpetual_identities`, `perpetual_state`, `perpetual_step`, `perpetual_render`, `perpetual_loop`, `perpetual_loop_seam`

動く例: `poc_illusions_and_perpetual_drawing`

### [定理が門になる図(アポロニウス・フォード・測地ドーム・葉序・IFS・空間充填曲線)](capabilities/theorems-as-pictures.md)

数学的に美しい図を描きます —— 互いに接する円の充填、ファレイ数列のフォード円、正二十面体からの測地ドーム、葉序の螺旋、IFS のアトラクタ、空間充填曲線。

使う op: `circle_packing_apollonian`, `ford_circles`, `phyllotaxis_pattern`, `neighbour_index_gaps`, `ifs_fractal`, `ifs_similarity_dimension`, `space_filling_curve`, `curve_locality`, `geodesic_dome`

動く例: `poc_theorems_as_pictures`
