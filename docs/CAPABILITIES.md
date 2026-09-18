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

**収録 22 項目**

## 測る (4)

### [地球規模の座標に載せる(ECEF と測地座標)](capabilities/geodetic-frames.md)

緯度・経度・高さと地球中心直交座標(ECEF)を往復します。往復の誤差の床は実測で緯度 6.4e-12 度・高さ 8.5e-07 m(緯度 ±85 度・高さ -500〜9000 m の 4000 点、最大値)。

使う op: `dem_geodetic_to_ecef`, `dem_ecef_to_geodetic`

動く例: `poc_geodetic_height_frames`, `dem_geodesy_tour`

### [画像から寸法をサブピクセルで測る](capabilities/subpixel-2d-metrology.md)

測定線に沿った輝度の勾配からエッジを**画素より細かく**求め、対になるエッジの間隔として寸法を返します。二値化して画素を数える方法と違い、しきい値の選び方で答えが動きません。

使う op: `measure_pos`, `measure_pairs`, `blob_label`, `blob_select`

動く例: `poc_dimensional_inspection`, `poc_screw_thread_metrology`

### [地形の傾き・水の流れ・見通しを測る](capabilities/terrain-and-visibility.md)

高さ格子(DEM)から、傾斜・斜面方位・可視領域・流向を出します。いずれも閉形式と突き合わせられる量なので、実装の誤りを数字で捕まえられます。

使う op: `dem_slope`, `dem_aspect`, `dem_viewshed`, `dem_flow_direction`

動く例: `poc_dem_terrain`, `dem_terrain_analysis_tour`

### [3-D スキャンから体積・土量を出す](capabilities/volume-from-3d-scan.md)

点群や高さ格子から、閉じたメッシュの符号つき体積、voxel 領域の体積、2 つの面のあいだの土量を出します。欠測は補間で埋められますが、**その補間がどこまで効いたか**を別に持ち出せます。

使う op: `mesh_volume`, `vol_rle_volume`, `interp_scattered`, `dem_slope`

動く例: `poc_stockpile_volume`, `poc_lidar_terrain_change`

## 見つける (3)

### [領域を切り出して、選んで、数える](capabilities/blob-and-region.md)

連結成分にラベルを付け、面積・形・位置で選び、数えます。接触している対象は分水嶺で分けられます。

使う op: `blob_label`, `blob_select`, `blob_count`, `watersheds`

動く例: `poc_cell_counting`, `poc_particle_sizing`, `poc_real_coin_metrology`

### [画像の中の文字を、正しい文字列に合わせて直す](capabilities/fix-text-in-images.md)

生成 AI が出したレポート用の画像や看板の文字が 1 字だけ壊れている —— そういうとき、画像を作り直さずに、**本当はこう書いてあるべき文字列**を渡して直せます。入口は JSON 一枚(`spec = {"items": [{"text": "電気設備", "bbox": [x, y, w, h]}]}`)で、Python の `glyph_correct_spec` からも MCP の `fullseye_fix_text` からも同じ形で呼べます。文字を**認識はしません**: 正しい文字列が与えられるので、各マスを指定の 1 字と 1 対 1 で照合するだけで済み、6,000 字の分類器は要りません。閾値は勘で置かず、その環境の書体で同じ字を描き分けた距離の 95 % 点(書体雑音の床)から導きます。

使う op: `glyph_correct_spec`, `glyph_make_spec`, `glyph_find_text_lines`, `glyph_rewrite_line`, `glyph_find_plate`, `glyph_typeface_noise_floor`, `glyph_rendering_noise_floor`, `glyph_distance`, `glyph_replace`, `glyph_split_cells`, `glyph_fonts`

動く例: `fix_text_in_image`, `poc_glyph_typo_detection`

### [小さな点状の目標を見つけて、副画素で位置を出す](capabilities/point-target-detection.md)

頑健に推定した背景と雑音から `背景 + kσ` を超える局所最大を拾い、重心で副画素の位置を返します。名前は天体ですが**中身は分野中立**で、漂流物・微小欠陥・蛍光輝点・粒子に同じものが使えます。

使う op: `star_detect`, `peak_subbin`, `find_peaks`, `noise_sigma`

動く例: `poc_search_sweep_width`, `poc_astro_photometry`

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

## 光と色 (4)

### [色を測る(XYZ / Lab / 色差)](capabilities/colour-and-delta-e.md)

分光反射率または RGB から CIE XYZ・Lab を求め、CIE76 / CIEDE2000 の色差を出します。色差は画像全体の地図としても返せます。

使う op: `rgb_to_lab`, `xyz_to_lab`, `delta_e_2000`, `cie_xyz_from_wavelength`

動く例: `poc_white_balance`, `poc_pigment_unmixing`

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

## 波と信号 (2)

### [配列で方向を測り、距離と速度を分ける](capabilities/beamforming-and-range-doppler.md)

素子配列の受信からビームを立てて到来角を出し、FMCW の受信から距離-速度面を作って検出を距離 [m] と速度 [m/s] に戻します。

使う op: `beamform_delay_sum`, `beamform_doa`, `range_doppler_map`, `range_doppler_peaks`

動く例: `poc_multibeam_bathymetry`, `poc_bev_sensor_fusion`

### [振動と音から異常を診断する](capabilities/vibration-and-acoustics.md)

包絡スペクトル・ケプストラム・オクターブ帯域・軸受の特徴周波数など、回転機械の診断に使う量を出します。周波数は幾何から先に計算できるので、**どのピークを見るべきかを測る前に決められます**。

使う op: `signal_features`, `envelope_spectrum`, `bearing_defect_frequencies`, `octave_spectrum`, `spectrum`

動く例: `poc_bearing_diagnosis`, `poc_rail_corrugation`

## 組み立てる (3)

### [位置を合わせて重ねる](capabilities/align-and-stack.md)

画像列の平行移動を投票で合わせ、サブピクセルで再標本して重ねます。点群は ICP で合わせられます。

使う op: `frame_align`, `drizzle_resample`, `icp_point2point_3d`, `interp_scattered`

動く例: `poc_astro_photometry`, `poc_registration_basin`

### [op の返り値(型付き)を JSON に出し、bit そのままで戻す](capabilities/typed-results-as-json.md)

op の返り値は `image` / `region` / `points` / `contour` / `feature` / `matrix` / `signal` … の**型(sort)**を持つ NumPy 配列や小さな dict で、次の op に渡すには良くても、ファイル・ログ・LLM・別プロセスには渡せません。`to_json(value, sort)` が sort ごとに**一つ**の JSON 形を与え、`from_json(text)` が `(value, sort)` に戻します。封筒は自己記述(`{"fullseye_sort": "points", "version": 1, "payload": …}`)で、戻すときに型の指定は要りません。

使う op: `to_json`, `from_json`, `to_jsonable`, `from_jsonable`, `save_json`, `load_json`, `to_json_lines`, `from_json_lines`, `as_value`, `apply_json`, `is_envelope`

動く例: `typed_results_json`

### [op の返り値(型付き)を Markdown で読める形にし、JSON を埋め込んで戻す](capabilities/typed-results-as-markdown.md)

JSON と Markdown は一緒に使う場面が多い —— 結果を報告書の中に貼る、数の表を「読ませる」、レビューに残す。機械に厳密な JSON 形(能力ノート `typed-results-as-json`)に対し、`fullseye/mdio.py` は**人が読む形**と、その**間の橋**を与えます。

使う op: `to_markdown`, `json_block`, `extract_json`, `report`

動く例: `typed_results_markdown`

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
