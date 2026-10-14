# 成熟度台帳(Maturity)

**Language:** 日本語 / English column in the table.

この表は**手で書いていません**。`tools/gen_maturity.py` が能力ノート・例の台帳・
門の実体・`tests/` の中身から数えて出します。`tests/test_maturity.py` が
コミット済みの内容と生成物を突き合わせるので、古びると CI が落ちます。

*This ledger is generated, not written. Each row's status is derived from facts in the repository — which operators have tests, which linked examples an actual gate executes, and whether that example is driven by real measured data.*

## はしご(4 段)

| 段 | 意味 | Meaning |
|---|---|---|
| `research-prototype` | 実装はあるが、名指しの op に試験が揃っておらず、走る例も無い | Implemented, but not every named operator is exercised by a test and no linked example is executed by a gate. |
| `verified-synthetic` | 真値を持つ合成データで自動検証済み(名指しの op 全部に試験があるか、走る例がある) | Automatically verified against ground truth that is synthesised or computed in closed form. |
| `validated-public-real-data` | 公開された実写・実測データを使う例が、門で実際に走っている | At least one linked example that runs in CI is driven by real, publicly available measured data. |
| `validated-hardware` | 実機センサ・装置で検証済み(★CI に実機は無い。外部の実機検証報告を保守者が受理し、昇格規則を満たしたときだけ出る) | Validated against physical sensors or instruments. CI has no hardware, so this is emitted only from accepted external reports that meet the promotion rules (docs/VALIDATION_CONTRIBUTING.en.md). |

★ **`validated-hardware` は repo の中の事実からは出ません。** CI に実機センサが
無いからです。出る道は 1 本だけで、実機・実データを持つ人の検証報告を保守者が
受理して `docs/validation_reports.json` に記録し、昇格規則を満たしたときです。
データを外に出せない場合も、結果の数値だけで報告できます。

*Fullseye is developed without physical measurement rigs, so CI can only verify against synthetic or computed ground truth. If you have real hardware or real data, your results can move a capability up this ladder — results-only reports (data kept private) count too:* [report form](https://github.com/furuse-kazufumi/fullseye/issues/new?template=real_validation_report.yml) · [how reports are judged](VALIDATION_CONTRIBUTING.en.md) · [日本語](VALIDATION_CONTRIBUTING.md)

## 能力ごと

| 能力 | Capability | 分類 | 段 | op(名指しの試験/全) | 例(走る門) |
|---|---|---|---|---|---|
| [位置を合わせて重ねる](capabilities/align-and-stack.md) | Align and stack | 組み立てる | `verified-synthetic` | 4/4 | `poc_astro_photometry` synthetic → tests/test_poc_scripts_run.py<br>`poc_registration_basin` synthetic → tests/test_poc_scripts_run.py |
| [配列で方向を測り、距離と速度を分ける](capabilities/beamforming-and-range-doppler.md) | Beamform for direction, separate range from velocity | 波と信号 | `verified-synthetic` | 4/4 | `poc_multibeam_bathymetry` synthetic → tests/test_poc_scripts_run.py<br>`poc_bev_sensor_fusion` synthetic → tests/test_poc_scripts_run.py |
| [うなりは一つ(膜のモード・干渉縞・回折次数・印刷のモアレ・墨に落とす)](capabilities/beats-fringes-and-screens.md) | One beat (membrane modes, fringes, diffraction orders, print moire, and turning tone into ink) | 波と信号 | `verified-synthetic` | 12/12 | `poc_beats_fringes_and_screens` synthetic → tests/test_poc_scripts_run.py |
| [領域を切り出して、選んで、数える](capabilities/blob-and-region.md) | Segment regions, select them, and count | 見つける | `validated-public-real-data` | 3/4 | `poc_cell_counting` synthetic → tests/test_poc_scripts_run.py<br>`poc_particle_sizing` synthetic → tests/test_poc_scripts_run.py<br>`poc_real_coin_metrology` real → tests/test_poc_scripts_run.py |
| [平面ターゲットの多視点から内部行列 K を推定する(Zhang 法)](capabilities/camera-intrinsics-calibration.md) | Estimate the camera intrinsic matrix K from multiple planar views (Zhang) | 測る | `verified-synthetic` | 4/4 | `camera_intrinsics_calibration` synthetic → tests/test_example_scripts_run.py |
| [色を測る(XYZ / Lab / 色差)](capabilities/colour-and-delta-e.md) | Measure colour (XYZ / Lab / colour difference) | 光と色 | `verified-synthetic` | 4/4 | `poc_white_balance` synthetic → tests/test_poc_scripts_run.py<br>`poc_pigment_unmixing` synthetic → tests/test_poc_scripts_run.py |
| [複素平面を「面」で見る(位相彩色・吸引域・脱出時間・翼まわりの流れ)](capabilities/complex-plane-fields.md) | Seeing the complex plane as an area (domain colouring, basins, escape time, flow) | 測る | `verified-synthetic` | 8/8 | `poc_complex_plane_fields` synthetic → tests/test_poc_scripts_run.py |
| [周期パターンが標本化格子で折り返す距離と、縞の上で狂う衝突時間を閉形式で測る(複眼・検査カメラ)](capabilities/compound-eye-aliasing-and-ttc.md) | The distance at which a periodic pattern aliases on a sampling lattice, and the time-to-contact that stripes corrupt — in closed form (compound eyes and inspection cameras) | 測る | `verified-synthetic` | 8/8 | `poc_zebra_stripes_fly_eye` synthetic → tests/test_poc_scripts_run.py |
| [カメラのデータシートの数を EMVA 1288 の手順で測り直し、カメラの中の前処理がその数をどれだけ動かすかを見る(Linear と General)](capabilities/emva1288-camera-datasheets.md) | Re-measure a camera's datasheet numbers with the EMVA 1288 procedure, and see how much in-camera processing moves them (Linear and General) | 測る | `verified-synthetic` | 13/13 | `poc_emva1288_sensor` synthetic → tests/test_poc_scripts_run.py<br>`poc_emva1288_in_camera_processing` synthetic → tests/test_poc_scripts_run.py |
| [本来まっすぐな線から歪み係数を推定する(plumb-line、チェッカー不要)](capabilities/estimate-lens-distortion.md) | Estimate lens distortion coefficients from straight lines (plumb-line, no board) | 測る | `verified-synthetic` | 4/4 | `estimate_lens_distortion` synthetic → tests/test_example_scripts_run.py |
| [光ファイバとライトガイド(ガラスの分散 → LP モード → モード径 → 照明の効率)](capabilities/fiber-and-light-guide.md) | Optical fibres and light guides (glass dispersion, LP modes, mode field diameter, illumination efficiency) | 光と色 | `verified-synthetic` | 7/7 | `poc_fiber_light_guide` synthetic → tests/test_poc_scripts_run.py |
| [結果を人が読める図にする](capabilities/figures-and-annotation.md) | Turn results into figures people can read | 見せる | `verified-synthetic` | 3/3 | `poc_colormap_readability` synthetic → tests/test_poc_scripts_run.py<br>`poc_dem_terrain` synthetic → tests/test_poc_scripts_run.py |
| [画像の中の文字を、正しい文字列に合わせて直す](capabilities/fix-text-in-images.md) | Fix the text inside an image against the string it should read | 見つける | `verified-synthetic` | 1/11 | `fix_text_in_image` synthetic → tests/test_example_scripts_run.py<br>`poc_glyph_typo_detection` synthetic → tests/test_poc_scripts_run.py |
| [地球規模の座標に載せる(ECEF・高さの基準・局所 ENU)](capabilities/geodetic-frames.md) | Put measurements on the Earth (ECEF, height frames, local ENU) | 測る | `validated-public-real-data` | 8/8 | `poc_geodetic_height_frames` synthetic → tests/test_poc_scripts_run.py<br>`poc_geodetic_benchmarks_real` real → tests/test_poc_scripts_run.py<br>`dem_geodesy_tour` synthetic → tests/test_example_scripts_run.py |
| [基準画像(ゴールデン)と比べて欠陥を測り、ロットごと判定する](capabilities/golden-compare.md) | Compare against a golden image — align, diff, count defects, judge the lot | 組み立てる | `verified-synthetic` | 7/7 | `golden_compare` synthetic → tests/test_example_scripts_run.py |
| [干渉計の共振器・量子雑音の予算・色つき雑音の中の既知波形を閉形式で設計する(重力波望遠鏡の式を検査装置の干渉計・振動計・AE に)](capabilities/gw-interferometer-quantum-noise-and-matched-filter.md) | Cavity optics, the quantum-noise budget and a known waveform in coloured noise, in closed form (the gravitational-wave detector's equations for inspection interferometers, vibrometers and AE) | 波と信号 | `validated-public-real-data` | 12/12 | `poc_gw_detector_pseudo_simulation` real → tests/test_poc_scripts_run.py |
| [円形部品の内径を mm まで測る](capabilities/inner-diameter-in-mm.md) | Inner diameter of a round part, all the way to millimetres | 測る | `validated-public-real-data` | 4/4 | `example_inner_diameter_mm` synthetic → tests/test_example_scripts_run.py<br>`poc_dimensional_inspection` synthetic → tests/test_poc_scripts_run.py<br>`poc_real_coin_metrology` real → tests/test_poc_scripts_run.py |
| [既知の良品/不良品セットで検査レシピと仕様を配備前に検定し、余裕を測る](capabilities/inspection-fixture.md) | Validate a recipe and spec on known good/bad sets before deployment, and measure the margins | 組み立てる | `verified-synthetic` | 4/4 | `inspection_fixture` synthetic → tests/test_example_scripts_run.py |
| [フォルダを一括検査し、仕様で判定し、集計・SPC・レポート・監査ログまで出す](capabilities/inspection-workflow.md) | Inspect a folder in one call — batch, judge against a spec, aggregate, SPC, report, audit log | 組み立てる | `verified-synthetic` | 8/8 | `inspection_workflow` synthetic → tests/test_example_scripts_run.py |
| [地の色を知らずに線と領域を描く(反転色)](capabilities/inverted-colour-overlays.md) | Draw lines and regions without knowing the background colour | 見せる | `verified-synthetic` | 3/3 | `annotate_paper_tour` synthetic → tests/test_example_scripts_run.py |
| [レーザー光切断の誤差の床はスペックルが決める(コヒーレント結像・スペックルの統計・三角測量の不確かさ)](capabilities/laser-speckle-floor.md) | Speckle sets the error floor of laser sheet-of-light (coherent imaging, speckle statistics and triangulation uncertainty) | 測る | `verified-synthetic` | 6/6 | `poc_laser_line_speckle_floor` synthetic → tests/test_poc_scripts_run.py |
| [レンズの歪みを画像ごと補正する(たる型・糸巻き型・接線)](capabilities/lens-distortion-correction.md) | Correct lens distortion over a whole image (barrel, pincushion, tangential) | 形にする | `verified-synthetic` | 4/4 | `lens_undistort` synthetic → tests/test_example_scripts_run.py |
| [凹みの相互反射で縞投影と ToF が外れる量を、撮る前に予測する(大域光輸送・直接と大域の分離・マイクロ位相シフト)](capabilities/light-transport.md) | Predict how far interreflection in concave parts throws fringe projection and ToF off, before measuring (global light transport, direct/global separation, micro phase shifting) | 測る | `verified-synthetic` | 11/11 | `poc_interreflection_fringe_error` synthetic → tests/test_poc_scripts_run.py |
| [材料の光学物性を 1 つの表で引く(硝材・結晶・半導体・金属・液体・プラスチック 83 種、一次文献の係数と数表、硝材カタログの取り込み口)](capabilities/material-optical-property-library.md) | One table of material optical constants (83 glasses, crystals, semiconductors, metals, liquids and plastics from primary literature, with a glass-catalogue importer) | 光と色 | `validated-public-real-data` | 15/16 | `poc_material_optical_library` real → tests/test_poc_scripts_run.py |
| [その数字のうち、いくつが測り方のものか(ゲージ R&R と測定の不確かさ)](capabilities/measurement-system-and-uncertainty.md) | How much of that number is your measuring, not your process (gauge R&R and measurement uncertainty) | 測る | `verified-synthetic` | 11/11 | `poc_measurement_system_analysis` synthetic → tests/test_poc_scripts_run.py |
| [モアレで位置合わせ(ピッチの僅かに違う 2 枚の格子 → 縞の位相 → nm のずれ、差動と Talbot ギャップ)](capabilities/moire-alignment.md) | Moiré alignment (two gratings of slightly different pitch, fringe phase, nanometre shift, differential pairs and the Talbot gap) | 測る | `verified-synthetic` | 8/8 | `poc_moire_alignment` synthetic → tests/test_poc_scripts_run.py |
| [OCR の前処理(傾き補正・局所 2 値化・行の切り出し)](capabilities/ocr-preprocessing.md) | OCR pre-processing (deskew, local binarisation, line extraction) | 見つける | `verified-synthetic` | 2/4 | `gallery2d_segmentation` synthetic → tests/test_example_scripts_run.py<br>`poc_matrix_code_reading` synthetic → tests/test_poc_scripts_run.py<br>`gallery2d_region` synthetic → tests/test_example_scripts_run.py |
| [写真を 1 本の線にする(点描 → 巡回路 → 回る円)](capabilities/one-stroke-drawing.md) | Turn a photograph into a single line (stipple, tour, rotating circles) | 描く | `validated-public-real-data` | 9/9 | `poc_one_stroke_epicycles` real → tests/test_poc_scripts_run.py |
| [光の反射・屈折・干渉を計算する](capabilities/optics-and-materials.md) | Compute reflection, refraction and interference | 光と色 | `verified-synthetic` | 4/4 | `glass_and_mirror_optics` synthetic → tests/test_example_scripts_run.py<br>`appearance_structural_colour` synthetic → tests/test_example_scripts_run.py |
| [1-D 信号の周期欠陥を見つける](capabilities/periodic-defects-in-1d-signals.md) | Periodic defects in a 1-D signal | 波と信号 | `verified-synthetic` | 5/5 | `poc_web_roll_periodicity` synthetic → tests/test_poc_scripts_run.py<br>`poc_rail_corrugation` synthetic → tests/test_poc_scripts_run.py<br>`poc_bearing_diagnosis` synthetic → tests/test_poc_scripts_run.py |
| [光沢面の µm の凹みを縞の鏡像で測る(位相計測デフレクトメトリ: 縞 → 位相 → 傾き → 曲率)](capabilities/phase-measuring-deflectometry.md) | Find micrometre dents on glossy surfaces from the mirror image of a fringe screen (phase-measuring deflectometry) | 測る | `verified-synthetic` | 6/6 | `poc_phase_measuring_deflectometry` synthetic → tests/test_poc_scripts_run.py |
| [目が嘘をつく絵を作って、測る側を採点する(錯視・無限描画・循環動画)](capabilities/pictures-that-carry-their-own-truth.md) | Pictures that carry their own ground truth (illusions, endless drawing, seamless loops) | 描く | `verified-synthetic` | 14/16 | `poc_illusions_and_perpetual_drawing` synthetic → tests/test_poc_scripts_run.py |
| [ピクセルシフト撮像(1 画素シフトで全色、半画素シフトで折り返しを消す、壊れる条件まで)](capabilities/pixel-shift-imaging.md) | Pixel-shift imaging (full colour from 1-pixel shifts, no aliasing from half-pixel shifts, and where it breaks) | 光と色 | `verified-synthetic` | 6/6 | `poc_pixel_shift` synthetic → tests/test_poc_scripts_run.py |
| [PL 像で細い溝が見えなくなる理由を、キャリア拡散の PSF と欠陥の種類で切り分ける(Si ウェハ・太陽電池の PL/EL 検査)](capabilities/pl-carrier-diffusion-visibility.md) | Why a thin groove disappears in a PL image — the carrier-diffusion PSF and the kind of defect decide the visibility (PL/EL inspection of wafers and solar cells) | 見つける | `validated-public-real-data` | 4/4 | `poc_si_wafer_pl_defect_visibility` real → tests/test_poc_scripts_run.py |
| [3-D 点群から平面度を出す](capabilities/planarity-from-point-cloud.md) | Flatness of a surface from a 3-D point cloud | 測る | `verified-synthetic` | 4/4 | `geometry_metrology` synthetic → examples3d.py (suite runs a smoke subset)<br>`poc_bump_coplanarity` synthetic → tests/test_poc_scripts_run.py<br>`poc_scan_to_bim_asbuilt` synthetic → tests/test_poc_scripts_run.py |
| [小さな点状の目標を見つけて、副画素で位置を出す](capabilities/point-target-detection.md) | Find small point-like targets and locate them below the pixel | 見つける | `verified-synthetic` | 4/4 | `poc_search_sweep_width` synthetic → tests/test_poc_scripts_run.py<br>`poc_astro_photometry` synthetic → tests/test_poc_scripts_run.py |
| [偏光 4 方向で鏡面反射を除く(誘電体と金属で分ける)](capabilities/polarisation-specular-removal.md) | Remove specular reflection from a four-angle polariser sweep (dielectrics vs metals) | 光と色 | `verified-synthetic` | 4/4 | `example_polarization_metal` synthetic → tests/test_example_scripts_run.py<br>`poc_polarization_specular` synthetic → tests/test_poc_scripts_run.py<br>`specular_photometric` synthetic → tests/test_example_scripts_run.py |
| [偏光カメラの生フレームを Stokes・DoLP・Mueller に読む](capabilities/polarization-imaging.md) | Read a polarisation camera's raw frame into Stokes, DoLP and Mueller | 光と色 | `verified-synthetic` | 10/10 | `polarization_camera_pipeline` synthetic → tests/test_example_scripts_run.py<br>`poc_polarization_specular` synthetic → tests/test_poc_scripts_run.py |
| [どの大きさなら見つかるか(検出確率 POD と a90/95、MIL-HDBK-1823A)](capabilities/probability-of-detection.md) | Which flaw size will you actually find (probability of detection and a90/95, MIL-HDBK-1823A) | 測る | `verified-synthetic` | 7/7 | `poc_pod_lighting` synthetic → tests/test_poc_scripts_run.py |
| [Bayer の生フレームを、段ごとに説明できる式で表示画像にする](capabilities/raw-to-display-isp.md) | Turn a Bayer raw frame into a display image, one explainable stage at a time | 光と色 | `verified-synthetic` | 13/14 | `raw_to_display_isp` synthetic → tests/test_example_scripts_run.py |
| [ハイブリッド接合のボイドを、超音波のエコーの明るさでなく位相で見つける(走査型音響顕微鏡の C スキャン・周波数の取引・POD)](capabilities/sam-bond-voids.md) | Find hybrid-bond voids by the phase of the ultrasonic echo, not its brightness (scanning acoustic microscope C-scans, the frequency trade-off, POD) | 見つける | `verified-synthetic` | 7/7 | `poc_sam_hybrid_bonding_voids` synthetic → tests/test_poc_scripts_run.py |
| [微細スクラッチを見つけて、幅を測る](capabilities/scratch-detection-and-width.md) | Detect fine scratches and measure their width | 測る | `verified-synthetic` | 3/4 | `example_scratch_width` synthetic → tests/test_example_scripts_run.py<br>`poc_crack_width` synthetic → tests/test_poc_scripts_run.py<br>`poc_solar_el_inspection` synthetic → tests/test_poc_scripts_run.py |
| [SEM の明るい縁が寸法をどれだけ太らせるかを、真値つきで測る](capabilities/sem-edge-effect-metrology.md) | Measure how much the bright SEM edge inflates a dimension, with ground truth | 測る | `validated-public-real-data` | 6/6 | `poc_sem_wafer_defect_edge_bias` real → tests/test_poc_scripts_run.py |
| [黒光沢とガラスの形を偏光で測る(偏光からの形状復元・曖昧さの集合・屈折率の推定)](capabilities/shape-from-polarization.md) | Measure the shape of black-glossy and glass parts from polarisation (shape from polarisation, the ambiguity set, refractive index) | 測る | `verified-synthetic` | 8/8 | `poc_shape_from_polarization` synthetic → tests/test_poc_scripts_run.py |
| [光源 × 対象 × センサの分光の鎖(Planck・CIE A・LED・フィルタ・Si の QE、曲線の積と積分)](capabilities/spectral-radiometry-chain.md) | The spectral chain source × object × sensor (Planck, CIE A, LEDs, filters, Si QE, curve products and integrals) | 光と色 | `verified-synthetic` | 9/9 | `poc_nir_silicon_transmission` synthetic → tests/test_poc_scripts_run.py |
| [画像から寸法をサブピクセルで測る](capabilities/subpixel-2d-metrology.md) | Measure dimensions from an image, below the pixel | 測る | `verified-synthetic` | 4/4 | `poc_dimensional_inspection` synthetic → tests/test_poc_scripts_run.py<br>`poc_screw_thread_metrology` synthetic → tests/test_poc_scripts_run.py<br>`poc_calipers_under_illusion` synthetic → tests/test_poc_scripts_run.py |
| [表面の凹凸欠陥を、照明の設計から検出まで](capabilities/surface-defects-with-lighting.md) | Surface relief defects, from lighting design to detection | 見つける | `verified-synthetic` | 5/5 | `illumination_design_demo` synthetic → tests/test_example_scripts_run.py<br>`photometric_stereo` synthetic → examples3d.py (suite runs a smoke subset)<br>`poc_bump_coplanarity` synthetic → tests/test_poc_scripts_run.py |
| [TDI ラインスキャンとラインスキャン用レンズ(段数と SNR → 同期ずれの MTF → 像高ごとの照度と MTF)](capabilities/tdi-linescan-and-lens.md) | TDI line-scan cameras and line-scan lenses (stages and SNR, synchronisation MTF, illumination and MTF across the image height) | 光と色 | `verified-synthetic` | 6/6 | `poc_tdi_linescan` synthetic → tests/test_poc_scripts_run.py |
| [テレセントリックレンズと寸法計測(主光線の傾き → 高さで変わる倍率 → ケラレとぼけ)](capabilities/telecentric-metrology.md) | Telecentric lenses for dimensional metrology (chief-ray angle, magnification versus height, vignetting and blur) | 測る | `verified-synthetic` | 7/7 | `poc_telecentric_metrology` synthetic → tests/test_poc_scripts_run.py |
| [位置決め(テンプレート照合で測定線を追従させる)](capabilities/template-alignment.md) | Locate a part by template matching and move the measurement model with it | 見つける | `verified-synthetic` | 4/4 | `poc_template_tracking` synthetic → tests/test_poc_scripts_run.py<br>`gallery2d_contour_measure` synthetic → tests/test_example_scripts_run.py<br>`poc_search_sweep_width` synthetic → tests/test_poc_scripts_run.py |
| [地形の傾き・水の流れ・見通しを測る](capabilities/terrain-and-visibility.md) | Slope, flow and line of sight on a terrain | 測る | `verified-synthetic` | 4/4 | `poc_dem_terrain` synthetic → tests/test_poc_scripts_run.py<br>`dem_terrain_analysis_tour` synthetic → tests/test_example_scripts_run.py |
| [画像の上に、文字と表を置きたい場所へ置く](capabilities/text-and-tables-on-images.md) | Put text and tables exactly where you want them on an image | 見せる | `verified-synthetic` | 6/6 | `annotate_paper_tour` synthetic → tests/test_example_scripts_run.py |
| [定理が門になる図(アポロニウス・フォード・測地ドーム・葉序・IFS・空間充填曲線)](capabilities/theorems-as-pictures.md) | Theorems as pictures (Apollonian, Ford, geodesic dome, phyllotaxis, IFS, space-filling curves) | 描く | `verified-synthetic` | 9/9 | `poc_theorems_as_pictures` synthetic → tests/test_poc_scripts_run.py |
| [薄膜の膜厚を分光反射率で測る(転送行列 → 干渉色 → FFT・モデルあてはめ・膜厚マップ)](capabilities/thin-film-reflectometry.md) | Thin-film thickness by spectral reflectometry (transfer matrix, interference colour, FFT, model fit, thickness maps) | 光と色 | `validated-public-real-data` | 5/5 | `poc_thin_film_reflectometry` real → tests/test_poc_scripts_run.py |
| [投影から断面を再構成する(CT)](capabilities/tomography-reconstruction.md) | Reconstruct slices from projections (CT) | 形にする | `verified-synthetic` | 3/4 | `poc_ct_fidelity` synthetic → tests/test_poc_scripts_run.py<br>`poc_ct_void_morphology` synthetic → tests/test_poc_scripts_run.py |
| [op の返り値(型付き)を JSON に出し、bit そのままで戻す](capabilities/typed-results-as-json.md) | Write typed op results as JSON and read them back bit-for-bit | 組み立てる | `verified-synthetic` | 11/11 | `typed_results_json` synthetic → tests/test_example_scripts_run.py |
| [op の返り値(型付き)を Markdown で読める形にし、JSON を埋め込んで戻す](capabilities/typed-results-as-markdown.md) | Render typed op results as Markdown, with an exact JSON block to read back | 組み立てる | `verified-synthetic` | 4/4 | `typed_results_markdown` synthetic → tests/test_example_scripts_run.py |
| [振動と音から異常を診断する](capabilities/vibration-and-acoustics.md) | Diagnose faults from vibration and sound | 波と信号 | `verified-synthetic` | 5/5 | `poc_bearing_diagnosis` synthetic → tests/test_poc_scripts_run.py<br>`poc_rail_corrugation` synthetic → tests/test_poc_scripts_run.py |
| [シルエットから立体を彫り出す(視体積交差)](capabilities/visual-hull-from-silhouettes.md) | Carve a solid out of silhouettes (visual hull) | 形にする | `verified-synthetic` | 4/4 | `space_carving` synthetic → examples3d.py (suite runs a smoke subset)<br>`poc_livestock_body_volume` synthetic → tests/test_poc_scripts_run.py |
| [3-D スキャンから体積・土量を出す](capabilities/volume-from-3d-scan.md) | Turn a 3-D scan into a volume | 測る | `verified-synthetic` | 4/4 | `poc_stockpile_volume` synthetic → tests/test_poc_scripts_run.py<br>`poc_lidar_terrain_change` synthetic → tests/test_poc_scripts_run.py |
| [絵では確かめられないもの(積分器の次数・リアプノフ指数・分岐・相関次元・極小曲面)](capabilities/what-a-picture-cannot-check.md) | What a picture cannot check (integrator order, Lyapunov spectrum, bifurcations, correlation dimension, minimal surfaces) | 測る | `verified-synthetic` | 11/11 | `poc_what_a_picture_cannot_check` synthetic → tests/test_poc_scripts_run.py |
| [型付きの検査結果を Excel(.xlsx)レポートに書き出す](capabilities/xlsx-report.md) | Write typed inspection results to an Excel (.xlsx) report | 組み立てる | `verified-synthetic` | 4/4 | `xlsx_report` synthetic → tests/test_example_scripts_run.py |

## 外部からの検証報告(External validation reports)

記録した報告はまだ **0 件**です(`docs/validation_reports.json` は空)。
*No external report has been recorded yet.*

## 例が実際に走っているか

| | 件数 |
|---|---|
| 2-D 台帳の例 | 374 |
| `tests/test_poc_scripts_run.py` が走らせる | 237 |
| `tests/test_example_scripts_run.py` が走らせる | 137 |
| **どの門も走らせていない** | **0** |

走らせない門は、実行時の壊れに盲目です。2026-09-06 に PoC 側で穴が見つかり
(31 本のうち 4 本が exit 1 のまま放置)、**2026-09-09 に同じ穴が 1 つ内側で
再演していた**ことが分かりました —— 門を作ったのに、対象を数え直さなかったので
`poc_*` 以外の 83 件が外に残り、そのうち 2 件が落ちていました。
どちらの門も `PYTHONPATH` を渡さずに走らせます(利用者と同じ条件)。
機械可読版は [`maturity.json`](maturity.json)。
