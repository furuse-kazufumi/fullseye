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

**収録 50 項目**

## 測る (18)

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

動く例: `poc_geodetic_height_frames`, `poc_geodetic_benchmarks_real`, `dem_geodesy_tour`

### [レーザー光切断の誤差の床はスペックルが決める(コヒーレント結像・スペックルの統計・三角測量の不確かさ)](capabilities/laser-speckle-floor.md)

レーザーで照らした粗面を、**コヒーレント結像**で撮ります。面の凹凸が波長より大きいと反射光の位相は場所ごとにでたらめになり、カメラの開口(瞳)で帯域を切られた**複素振幅**が干渉して粒々の模様(スペックル)になります。光切断やレーザー変位計の高さの誤差の下限は、画素の雑音ではなくこの粒で決まります。

使う op: `coherent_image`, `speckle_field`, `speckle_statistics`, `laser_line_coherent`, `triangulation_speckle_limit`, `speckle_reduction`

動く例: `poc_laser_line_speckle_floor`

### [凹みの相互反射で縞投影と ToF が外れる量を、撮る前に予測する(大域光輸送・直接と大域の分離・マイクロ位相シフト)](capabilities/light-transport.md)

縞投影(位相シフト)も ToF も、「画素に届く光は 1 つの経路から来た」と仮定して位相を距離に変えます。V 溝・加工ポケットの内角・はんだフィレット・部屋の隅のような凹んだ形では、片方の面で反射した光が向かいの面を照らし、画素には**別の場所の位相を持った光**が混ざります(相互反射 = 大域成分)。光沢も金属も要らず、**白い Lambert 面でも凹んでいれば起きます**。このページの op は、その光の行き来を輸送行列として明示的に解き、誤差を閉形式で予測します。

使う op: `groove_profile`, `form_factors_2d`, `transport_matrix_radiosity`, `high_frequency_patterns`, `render_transport`, `separate_direct_global`, `fringe_multipath_phase_error`, `predict_fringe_phase_error`, `micro_phase_decode`, `tof_multipath_phase`, `tof_transport_depth`

動く例: `poc_interreflection_fringe_error`

### [その数字のうち、いくつが測り方のものか(ゲージ R&R と測定の不確かさ)](capabilities/measurement-system-and-uncertainty.md)

工程のばらつきを見る管理図も工程能力も、**測定のばらつきを含んだままの数字**を見ています。この層はそれを分けます —— 総変動のうち何割が部品どうしの差で、何割が「測るという行為」の差なのか。そして 1 回の測定について、成分ごとの不確かさを合成して報告可能な形にします。

使う op: `msa_anova_table`, `msa_gauge_rr`, `msa_bias_linearity`, `msa_attribute_agreement`, `gum_standard_uncertainty`, `gum_propagate`, `gum_expanded`, `gum_monte_carlo`, `gum_validate`, `spc_capability`, `spc_xbar_r`

動く例: `poc_measurement_system_analysis`

### [モアレで位置合わせ(ピッチの僅かに違う 2 枚の格子 → 縞の位相 → nm のずれ、差動と Talbot ギャップ)](capabilities/moire-alignment.md)

リソグラフィやナノインプリントでは、マスクとウェハを nm の精度で重ねます。マスク側にピッチ p_m、ウェハ側に僅かに違うピッチ p_w の格子を置くと、2 枚はカメラのぼけで見えなくても、重ねた像には周期 P = p_m p_w / |Δp| の縞(モアレ)が現れ、ウェハが δ 動くと縞は M = p_m / |Δp| 倍の距離を動きます(マスクが動くなら p_w / |Δp| 倍)。`moirealign` の 8 本はその設計・合成・読み取り・限界を受け持ちます。

使う op: `moire_magnification`, `moire_talbot_gap`, `moire_overlay_image`, `moire_phase`, `moire_phase_to_shift`, `moire_differential_shift`, `moire_mark_read`, `moire_phase_crlb`

動く例: `poc_moire_alignment`

### [どの大きさなら見つかるか(検出確率 POD と a90/95、MIL-HDBK-1823A)](capabilities/probability-of-detection.md)

検査の性能を「この大きさの傷は何 % の確率で見つかるか」で言います。欠陥の大きさ `a` と検査系の応答 `â`(あるいは見つけた/見落とした)の組から、POD(a) 曲線・a50・a90・**a90/95**(90 % の確率で見つかると 95 % の信頼で言える最小の大きさ)と、無欠陥部位の応答から誤検出確率を出します。手順は非破壊検査の信頼性評価の公開ハンドブック MIL-HDBK-1823A のとおりです。

使う op: `pod_ahat_fit`, `pod_from_ahat`, `pod_hitmiss_fit`, `pod_false_call`, `pod_decision_tradeoff`, `light_source`, `detectability_limit`

動く例: `poc_pod_lighting`

### [SEM の明るい縁が寸法をどれだけ太らせるかを、真値つきで測る](capabilities/sem-edge-effect-metrology.md)

走査電子顕微鏡(SEM)像では、二次電子が斜面でよけいに出る(放出 ∝ sec θ)ので段差の縁が明るく縁取られ、ビームの有限径(PSF)がその縁を広げます。`sem_render` は高さ場からこの SEM 像を**閉形式の真値つき**で作ります(平面で一様 / 斜面で平面比 = sec θ / 段差の明るい縁の幅 = PSF 幅)。作った像をしきい値 → `blob_label` → `blob_features` で測ると、明るい縁ごと拾って面積が系統的に太ること、その太りが **周囲長 × PSF 幅** でよく説明でき、既知の PSF 幅で引くと消えることが数で示せます。`seg_dice_jaccard` / `seg_boundary_f` で専門家マスクと採点し、`pod_hitmiss_fit` で埋め込み欠陥の検出確率 a90/95 を出します。

使う op: `sem_render`, `blob_label`, `blob_features`, `seg_dice_jaccard`, `seg_boundary_f`, `pod_hitmiss_fit`

動く例: `poc_sem_wafer_defect_edge_bias`

### [黒光沢とガラスの形を偏光で測る(偏光からの形状復元・曖昧さの集合・屈折率の推定)](capabilities/shape-from-polarization.md)

4 方位のオンチップ偏光子を持つセンサの 1 ショットから、面の**法線**と**高さ**を出します。黒い光沢の樹脂やガラスのレンズは拡散反射がほとんど無く、照明を変えても陰影が出ないので、照度差ステレオや陰影からの形状復元が拠り所を失います。けれど表面で 1 回反射した光の偏光は、面の傾きで決まっています(Fresnel の式)。

使う op: `sfp_dolp_model`, `dolp_to_zenith`, `aolp_to_azimuth`, `sfp_render`, `sfp_normals`, `sfp_disambiguate`, `sfp_estimate_index`, `sfp_height`

動く例: `poc_shape_from_polarization`

### [画像から寸法をサブピクセルで測る](capabilities/subpixel-2d-metrology.md)

測定線に沿った輝度の勾配からエッジを**画素より細かく**求め、対になるエッジの間隔として寸法を返します。二値化して画素を数える方法と違い、しきい値の選び方で答えが動きません。

使う op: `measure_pos`, `measure_pairs`, `blob_label`, `blob_select`

動く例: `poc_dimensional_inspection`, `poc_screw_thread_metrology`, `poc_calipers_under_illusion`

### [テレセントリックレンズと寸法計測(主光線の傾き → 高さで変わる倍率 → ケラレとぼけ)](capabilities/telecentric-metrology.md)

段差のある部品(ボンディングのダイ、コネクタのピン、穴)の寸法を 1 枚の画像で測るとき、通常のレンズは近い面ほど大きく写すので、高さの違う面で同じ寸法が違う長さに写ります。`telecentric` の 7 本は `raytrace` の処方(`lens_system` の table)を実光線で追い、この誤差がどれだけ出てどれだけ消えるかを数字で返します。

使う op: `telecentric_lens`, `chief_ray_angle`, `magnification_vs_depth`, `telecentricity_error`, `defocus_spot_vs_depth`, `vignetting_vs_field`, `lens_equivalent_pinhole`

動く例: `poc_telecentric_metrology`

### [地形の傾き・水の流れ・見通しを測る](capabilities/terrain-and-visibility.md)

高さ格子(DEM)から、傾斜・斜面方位・可視領域・流向を出します。いずれも閉形式と突き合わせられる量なので、実装の誤りを数字で捕まえられます。

使う op: `dem_slope`, `dem_aspect`, `dem_viewshed`, `dem_flow_direction`

動く例: `poc_dem_terrain`, `dem_terrain_analysis_tour`

### [3-D スキャンから体積・土量を出す](capabilities/volume-from-3d-scan.md)

点群や高さ格子から、閉じたメッシュの符号つき体積、voxel 領域の体積、2 つの面のあいだの土量を出します。欠測は補間で埋められますが、**その補間がどこまで効いたか**を別に持ち出せます。

使う op: `mesh_volume`, `vol_rle_volume`, `interp_scattered`, `dem_slope`

動く例: `poc_stockpile_volume`, `poc_lidar_terrain_change`

### [絵では確かめられないもの(積分器の次数・リアプノフ指数・分岐・相関次元・極小曲面)](capabilities/what-a-picture-cannot-check.md)

力学系(軌道・ベクトル場・ポアンカレ断面・リアプノフ指数・分岐図・相関次元)と極小曲面(カテノイド・ヘリコイド・エンネパー・シェルク・ジャイロイド)を作り、**恒等式と定義だけで採点します**。軌道は管メッシュにして立体で見られます。

使う op: `ode_flow_states`, `ode_vector_field_grid`, `dynsys_poincare_section`, `dynsys_lyapunov_spectrum`, `dynsys_bifurcation_map`, `dynsys_correlation_dimension`, `minimal_surface`, `minimal_surface_bend`, `gyroid_isosurface`, `gyroid_solid_mask`, `curve3d_tube_mesh`

動く例: `poc_what_a_picture_cannot_check`

## 見つける (5)

### [領域を切り出して、選んで、数える](capabilities/blob-and-region.md)

連結成分にラベルを付け、面積・形・位置で選び、数えます。接触している対象は分水嶺で分けられます。

使う op: `blob_label`, `blob_select`, `blob_count`, `watersheds`

動く例: `poc_cell_counting`, `poc_particle_sizing`, `poc_real_coin_metrology`

### [画像の中の文字を、正しい文字列に合わせて直す](capabilities/fix-text-in-images.md)

生成 AI が出したレポート用の画像や看板の文字が 1 字だけ壊れている —— そういうとき、画像を作り直さずに、**本当はこう書いてあるべき文字列**を渡して直せます。入口は JSON 一枚(`spec = {"items": [{"text": "電気設備", "bbox": [x, y, w, h]}]}`)で、Python の `glyph_correct_spec` からも MCP の `fullseye_fix_text` からも同じ形で呼べます。文字を**認識はしません**: 正しい文字列が与えられるので、各マスを指定の 1 字と 1 対 1 で照合するだけで済み、6,000 字の分類器は要りません。閾値は勘で置かず、その環境の書体で同じ字を描き分けた距離の 95 % 点(書体雑音の床)から導きます。

使う op: `glyph_correct_spec`, `glyph_make_spec`, `glyph_find_text_lines`, `glyph_rewrite_line`, `glyph_find_plate`, `glyph_typeface_noise_floor`, `glyph_rendering_noise_floor`, `glyph_distance`, `glyph_replace`, `glyph_split_cells`, `glyph_fonts`

動く例: `fix_text_in_image`, `poc_glyph_typo_detection`

### [PL 像で細い溝が見えなくなる理由を、キャリア拡散の PSF と欠陥の種類で切り分ける(Si ウェハ・太陽電池の PL/EL 検査)](capabilities/pl-carrier-diffusion-visibility.md)

フォトルミネッセンス(PL)像は、励起で作った過剰キャリアが**拡散してから**光ります。だから像には光学の PSF のほかに、拡散長 L = √(Dτ) で決まる**もう 1 つの PSF**(2 次元のグリーン関数 K₀(r/L)/2πL²)が掛かります。`pl_diffusion_psf` はその核を総和 1 で返し、`pl_image_simulate` は励起の場と追加再結合の場から定常拡散方程式を格子で厳密に解いて PL 像を作ります(光学 PSF と雑音は任意)。`pl_groove_visibility` は溝の幅・拡散長・雑音から、**影の溝**(励起や発光の欠け、コントラスト 1 − e^{−w/2L})と**沈みの溝**(再結合の線、Donolato 型 SL/(SL+2D))のコントラスト・CNR・見える/見えないの境界 L* を閉形式で返します。

使う op: `pl_diffusion_psf`, `pl_image_simulate`, `pl_groove_visibility`, `pod_hitmiss_fit`

動く例: `poc_si_wafer_pl_defect_visibility`

### [小さな点状の目標を見つけて、副画素で位置を出す](capabilities/point-target-detection.md)

頑健に推定した背景と雑音から `背景 + kσ` を超える局所最大を拾い、重心で副画素の位置を返します。名前は天体ですが**中身は分野中立**で、漂流物・微小欠陥・蛍光輝点・粒子に同じものが使えます。

使う op: `star_detect`, `peak_subbin`, `find_peaks`, `noise_sigma`

動く例: `poc_search_sweep_width`, `poc_astro_photometry`

### [ハイブリッド接合のボイドを、超音波のエコーの明るさでなく位相で見つける(走査型音響顕微鏡の C スキャン・周波数の取引・POD)](capabilities/sam-bond-voids.md)

貼り合わせた積層(Si のダイ + SiO2 と Cu パッドの接合層)を、水の中の集束探触子で上から 1 点ずつ測る走査型音響顕微鏡(SAM)を、層の物理から組み立てます。接合面の**空洞(ボイド)**は空気なので、そこで音響インピーダンスが約 4 万分の 1 に落ち、エコーが**反転**します。符号はボイドがビームより小さくても薄まりません。

使う op: `acoustic_material_table`, `acoustic_layer_stack`, `acoustic_interface_coefficients`, `pulse_echo_ascan`, `sam_cscan`, `echo_phase_polarity`, `sam_frequency_tradeoff`

動く例: `poc_sam_hybrid_bonding_voids`

## 形にする (3)

### [レンズの歪みを画像ごと補正する(たる型・糸巻き型・接線)](capabilities/lens-distortion-correction.md)

広角・魚眼寄りのレンズは直線を曲げます(たる型・糸巻き型)。`undistort_image(image, K, dist)` は Brown–Conrady モデル(`dist = [k1, k2, p1, p2(, k3)]`、OpenCV と同じ並び)で**画像を丸ごと補正**し、曲がった直線をまっすぐに戻します。`distort_image` はその逆で、理想画像から歪んだ画像を作ります(合成テストデータ・レンズの見えの確認)。

使う op: `undistort_image`, `distort_image`, `distort_points`, `undistort_points`

動く例: `lens_undistort`

### [投影から断面を再構成する(CT)](capabilities/tomography-reconstruction.md)

平行ビームの順投影(サイノグラム)と、フィルタ補正逆投影による再構成、リングアーチファクトやビームハードニングの付与と補正を行います。再構成した体積はそのまま等値面としてメッシュ化できます。

使う op: `radon_transform`, `fbp_volume`, `ring_artifact_remove`, `marching_cubes`

動く例: `poc_ct_fidelity`, `poc_ct_void_morphology`

### [シルエットから立体を彫り出す(視体積交差)](capabilities/visual-hull-from-silhouettes.md)

校正済みの複数カメラの前景マスクから、物体を必ず内包する体積を voxel として彫り出します。学習モデルも深度センサも要りません。

使う op: `synthesize_silhouette`, `carve`, `visual_hull`, `carve_look_at`

動く例: `space_carving`, `poc_livestock_body_volume`

## 光と色 (7)

### [色を測る(XYZ / Lab / 色差)](capabilities/colour-and-delta-e.md)

分光反射率または RGB から CIE XYZ・Lab を求め、CIE76 / CIEDE2000 の色差を出します。色差は画像全体の地図としても返せます。

使う op: `rgb_to_lab`, `xyz_to_lab`, `delta_e_2000`, `cie_xyz_from_wavelength`

動く例: `poc_white_balance`, `poc_pigment_unmixing`

### [光ファイバとライトガイド(ガラスの分散 → LP モード → モード径 → 照明の効率)](capabilities/fiber-and-light-guide.md)

検査の照明はライトガイド(ファイバの束)で運び、干渉・分光の光は単一モードファイバで運びます。どちらもガラスの分散と導波の式で決まるので、`fiberoptics` の 7 本は材料表(`materials`)のガラスを名前で受けます。

使う op: `material_group_index`, `material_gvd`, `fiber_numerical_aperture`, `fiber_v_number`, `fiber_lp_modes`, `fiber_mode_field_diameter`, `fiber_bundle_coupling`

動く例: `poc_fiber_light_guide`

### [材料の光学物性を 1 つの表で引く(硝材・結晶・半導体・金属・液体・プラスチック 83 種、一次文献の係数と数表、硝材カタログの取り込み口)](capabilities/material-optical-property-library.md)

観察用の光学系(レンズ・窓・鏡・膜)も観察対象(ウェハ・モールド・はんだ)も、見え方は材料の光学特性で決まります。これまで Fullseye は硝材 20 種の Sellmeier(`raytrace`)、金属 5 種の 5 点の n,k(`glassmirror`)、見た目のカタログ(`surfacelib` / `metalfinish`)が別々の名前空間にあり、同じ材料を光学系側と対象側で引く口がありませんでした。この回は**1 材料 = 1 レコード**の材料表を `materials` に作り、`opsoptics` の新カテゴリ `matprop` に 16 本を足しました。

使う op: `material_table`, `material_record`, `material_optical_constants`, `material_dispersion`, `material_extinction`, `material_absorption`, `material_transmittance`, `material_reflectance`, `abbe_number`, `glass_map`, `thermo_optic_coefficient`, `plate_focus_shift`, `silicon_free_carrier_absorption`, `material_from_sellmeier`, `material_from_curves`, `read_glass_catalog_agf`

動く例: `poc_material_optical_library`

### [光の反射・屈折・干渉を計算する](capabilities/optics-and-materials.md)

Fresnel の反射率、薄膜干渉の色、回折格子の色、ベクトル形の屈折(光線ごとの全反射判定つき)を、実在の硝材の分散を含めて計算します。

使う op: `fresnel_dielectric`, `thin_film_reflectance`, `grating_rgb`, `refract_rays`

動く例: `glass_and_mirror_optics`, `appearance_structural_colour`

### [偏光カメラの生フレームを Stokes・DoLP・Mueller に読む](capabilities/polarization-imaging.md)

偏光カメラ(Sony IMX250MZR 系: FLIR BFS-U3-51S5P、LUCID TRI050S-P など)は 2×2 の画素ブロックに 0/45/90/135 度の偏光子を並べた**モザイク**を 1 枚で出します。`polarization_demosaic` がそれを 4 枚(0/45/90/135)に戻し(双線形。1 次の場は厳密に戻り、縁はモザイクを鏡映して位相を保つ)、そのまま `polarization_stokes` / `polarization_dolp_map` / `polarization_separate` に渡せます(角度の既定が一致しているので引数無しで繋がる)。センサの配列が違えば `layout=((a00, a01), (a10, a11))` で渡します。**カラー偏光センサ**(IMX250MYR、4×4 ブロック)は `polarization_demosaic_color` が (4, H, W, 3) に戻します —— 各偏光子位置の画素は半解像度の Bayer なので `raw_demosaic_bilinear` で展開し、戻してから各チャネルを偏光 demosaic する(2 つの厳密な段の合成)。

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

## 波と信号 (4)

### [配列で方向を測り、距離と速度を分ける](capabilities/beamforming-and-range-doppler.md)

素子配列の受信からビームを立てて到来角を出し、FMCW の受信から距離-速度面を作って検出を距離 [m] と速度 [m/s] に戻します。

使う op: `beamform_delay_sum`, `beamform_doa`, `range_doppler_map`, `range_doppler_peaks`

動く例: `poc_multibeam_bathymetry`, `poc_bev_sensor_fusion`

### [うなりは一つ(膜のモード・干渉縞・回折次数・印刷のモアレ・墨に落とす)](capabilities/beats-fringes-and-screens.md)

膜の固有モードと節線、二重スリットの干渉縞、回折格子の次数、そして印刷の網点・モアレ・彫版線・ハッチ・モザイクを作り、**どれも絵の外にある真値で採点します**。

使う op: `wave_membrane_mode`, `wave_mode_frequencies`, `wave_nodal_lines`, `wave_two_slit`, `wave_fringe_period`, `wave_grating_orders`, `halftone_screen`, `halftone_moire_period`, `engrave_lines`, `hatch_field`, `mosaic_tiles_sites`, `mosaic_tiles_render`

動く例: `poc_beats_fringes_and_screens`

### [干渉計の共振器・量子雑音の予算・色つき雑音の中の既知波形を閉形式で設計する(重力波望遠鏡の式を検査装置の干渉計・振動計・AE に)](capabilities/gw-interferometer-quantum-noise-and-matched-filter.md)

重力波望遠鏡は km 級の Michelson 干渉計の両腕に Fabry-Perot 共振器を置き、腕の長さの差を光量で読む装置です。その設計の式は、検査装置のエタロン(波長フィルタ)・レーザー共振器・白色干渉計・振動計の式と同じで、Fullseye にはこれまで共振器そのものと量子雑音の予算、そして**雑音の PSD で割る整合フィルタ**が 1 本もありませんでした。この回は 12 本を 2 つの台帳に足しました。

使う op: `fabry_perot_response`, `cavity_strain_transfer`, `michelson_dc_readout`, `pdh_error_signal`, `quantum_noise_budget`, `psd_welch`, `whiten_by_psd`, `chirp_newtonian`, `chirp_mass_from_track`, `matched_filter_snr`, `optimal_snr`, `coincidence_delay`

動く例: `poc_gw_detector_pseudo_simulation`

### [振動と音から異常を診断する](capabilities/vibration-and-acoustics.md)

包絡スペクトル・ケプストラム・オクターブ帯域・軸受の特徴周波数など、回転機械の診断に使う量を出します。周波数は幾何から先に計算できるので、**どのピークを見るべきかを測る前に決められます**。

使う op: `signal_features`, `envelope_spectrum`, `bearing_defect_frequencies`, `octave_spectrum`, `spectrum`

動く例: `poc_bearing_diagnosis`, `poc_rail_corrugation`

## 組み立てる (7)

### [位置を合わせて重ねる](capabilities/align-and-stack.md)

画像列の平行移動を投票で合わせ、サブピクセルで再標本して重ねます。点群は ICP で合わせられます。

使う op: `frame_align`, `drizzle_resample`, `icp_point2point_3d`, `interp_scattered`

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

## 見せる (3)

### [結果を人が読める図にする](capabilities/figures-and-annotation.md)

パネルを並べた図、寸法や矢印の注釈、高さの疑似カラー、SDF から起こした立体のレンダリングまで、**fullseye 自身の op** で作れます。外部の作図ライブラリを挟まずに、出力そのものを図にできます。

使う op: `annotate_figure_grid`, `colorize_height`, `render_beauty`

動く例: `poc_colormap_readability`, `poc_dem_terrain`

### [地の色を知らずに線と領域を描く(反転色)](capabilities/inverted-colour-overlays.md)

検査画像に測定線や ROI を重ねるとき、**地が明るいか暗いか分からない**のが普通です。白で描けば白飛びの上で消え、黒で描けば影の上で消えます。反転色は「その場の色をひっくり返して描く」ことでこれを避ける古典手で、`annotate_invert_path` が折れ線(アンチエイリアス・破線可)、`annotate_invert` が領域を、`draw="fill"` で中身ごと、`draw="margin"` で輪郭だけ反転します(HALCON の `set_draw` と同じ語)。

使う op: `annotate_invert`, `annotate_invert_path`, `annotate_invert_visibility`

動く例: `annotate_paper_tour`

### [画像の上に、文字と表を置きたい場所へ置く](capabilities/text-and-tables-on-images.md)

検査画像や解析結果に、**位置を指定して**文字を焼き込めます。`text_box` は 9 方向のアンカー・半透明の板・折り返し、`annotate_text_path` は折れ線に沿った配置で、**斜め**(接線角に 1 字ずつ回す)・**縦書き**(`upright=True`)・**改行**(`\n`)・経路に沿ったそろえ(`anchor="start"/"center"/"end"`)・線に触れさせない**法線オフセット**が使えます。字は色(役割名または RGB)に加えて、合成の **Bold / Italic** も指定できます。

使う op: `text_box`, `annotate_text_path`, `annotate_text_path_layout`, `annotate_table`, `annotate_table_layout`, `measure_text`

動く例: `annotate_paper_tour`

## 描く (3)

### [写真を 1 本の線にする(点描 → 巡回路 → 回る円)](capabilities/one-stroke-drawing.md)

写真の**濃淡**を、紙から鉛筆を離さずに引ける**1 本の閉じた線**に変えます。濃いところで線が密になるので、離れて見ると元の絵の階調が戻ります。巡回路は閉じているので、そのまま**複素フーリエ級数**に載り、**回る円の連鎖**として描き直せます。出口は既存の G-code op なので、ペンプロッタで実際に引けます。自分の写真で走らせる口も付いています::

使う op: `stipple_points_from_image`, `stipple_energy`, `stroke_tour_closed`, `mst_length`, `stroke_resample_closed`, `stroke_tone_error`, `contour_fourier_complex`, `contour_epicycle_chain`, `contour_fourier_truncation_energy`

動く例: `poc_one_stroke_epicycles`

### [目が嘘をつく絵を作って、測る側を採点する(錯視・無限描画・循環動画)](capabilities/pictures-that-carry-their-own-truth.md)

**真値が最初から付いている画像**を作ります。Fullseye のほとんどの op は与えられた 画像を測る側にいますが、この族だけが反対側にいます。

使う op: `illusion_cafe_wall`, `illusion_muller_lyer`, `illusion_checker_shadow`, `illusion_kanizsa`, `illusion_fraser_spiral`, `illusion_ground_truth`, `perpetual_elementary_ca`, `perpetual_langtons_ant`, `perpetual_apollonian`, `perpetual_flow_field`, `perpetual_identities`, `perpetual_state`, `perpetual_step`, `perpetual_render`, `perpetual_loop`, `perpetual_loop_seam`

動く例: `poc_illusions_and_perpetual_drawing`

### [定理が門になる図(アポロニウス・フォード・測地ドーム・葉序・IFS・空間充填曲線)](capabilities/theorems-as-pictures.md)

数学的に美しい図を描きます —— 互いに接する円の充填、ファレイ数列のフォード円、正二十面体からの測地ドーム、葉序の螺旋、IFS のアトラクタ、空間充填曲線。

使う op: `circle_packing_apollonian`, `ford_circles`, `phyllotaxis_pattern`, `neighbour_index_gaps`, `ifs_fractal`, `ifs_similarity_dimension`, `space_filling_curve`, `curve_locality`, `geodesic_dome`

動く例: `poc_theorems_as_pictures`
