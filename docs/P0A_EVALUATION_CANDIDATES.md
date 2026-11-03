# P0-A 重複候補の全件比較表

基準コミット c9f46c26f64ea2cf2ed88fd88903158a79dbc891 の examples/poc_*.py を AST で再監査した一覧。調査報告時の件数との差は、その後に追加された PoC を含むためである。行番号は基準コミット上。

## 基底候補の比較と選定

| 役割 | 候補 | 契約の完全さ | 正しさの証拠 | 使用実績 | 性能 | 読みやすさ | 選定 |
|---|---|---|---|---|---|---|---|
| 結果 | poc_simcal_telecentric.gate | measured/expected/detailを保持 | PoC既定値で合格 | 対象PoC | 軽量 | 短い | 基底 |
| 結果 | validation_kit.aggregate | 数値集約のみ | 専用テストあり | validation kit | ベクトル化 | 明瞭 | 補助として呼出し |
| 結果 | 他117個のgate/check | 項目がPoCごとに異なる | 各PoC assert | 117 PoC | 軽量 | schema不統一 | 薄いadapterへ |
| truth | poc_pv_thermal_survey.ground_truth | fieldsがまとまる | 図と判定で使用 | 1 PoC | 場面依存 | 明瞭 | 基底 |
| truth | 他27個のtruth生成 | 単位・frame・maskが暗黙 | 各PoCで照合 | 27関数 | 場面依存 | 物理は明瞭 | TruthBundleへ格納 |
| metrics | imgmetrics.rmse | shape/finite検査あり | 既存テスト | 共有API | NumPy | 明瞭 | 2-D基底 |
| metrics | validation_kit.aggregate | 主要誤差を一括集約 | 既存テスト | 共有API | NumPy | 明瞭 | 集約基底 |
| metrics | metrics3d.rmse_correspondence/voxel_iou/voxel_dice | 3-D意味とempty規約あり | 既存テスト | 共有API | NumPy | 明瞭 | 3-D基底 |
| metrics | 他103個のローカル採点 | mask/NaN/emptyが不統一 | 各PoC既定値 | 73 PoC | 概ね軽量 | 用途特化 | 共通引数をadapterへ |
| artifact | examplefig manifest/save群 | caption/shape/fileを統一 | 既存テストと1966保存例 | 全PoC | I/O相当 | 公開API | 基底 |
| artifact | 34個のローカルfigures | 構成のみ | 各PoC図 | 34 PoC | 図数依存 | 明瞭 | 構成はPoCに残す |
| video | examplefig.save_video | MP4/GIF/fps/framesを記録 | 既存テストと82呼出し | 61 PoC | encode相当 | 公開API | 基底 |
| video | 82個の保存呼出し | hold/stride/scaleが分散 | 成果物目視/manifest | 61 PoC | encode相当 | 引数分散 | VideoSpecから基底を呼ぶ |
| manifest | examplefigのfigures.json | 図・動画の基本項目 | 既存テスト | 全PoC | 軽量 | 単純JSON | 基底 |
| manifest | golden.py/fixture.py | golden固定とfixture復元 | 既存テスト | 回帰試験 | 軽量 | 責務明瞭 | 比較・provenanceを再利用 |

## 合否集約 (118件)

| # | PoC | 関数/呼出し | 行 | 契約の完全さ | 正しさの証拠 | 使用実績 | 性能 | 読みやすさ | 基底 |
|---:|---|---|---:|---|---|---|---|---|---|
| 1 | poc_active_contours.py | gate | 62-64 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 2 | poc_agv_fleet.py | gate | 53-55 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 3 | poc_air_hockey_intercept.py | gate | 55-57 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 4 | poc_attention_identities.py | check | 85-88 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 5 | poc_ball_bounce.py | gate | 60-62 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 6 | poc_beats_fringes_and_screens.py | check | 62-66 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 7 | poc_braid_homotopy_classes.py | gate | 49-51 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 8 | poc_calipers_under_illusion.py | check | 54-57 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 9 | poc_carla_bridge.py | gate | 61-63 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 10 | poc_chromatic_confocal.py | gate | 86-90 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 11 | poc_complex_plane_fields.py | check | 115-117 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 12 | poc_dense_bubble_count.py | gate | 110-114 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 13 | poc_diabolo_model_and_vision.py | gate | 55-57 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 14 | poc_dose_uniformity_from_grinding.py | gate | 60-62 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 15 | poc_driving_commonroad.py | gate | 63-65 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 16 | poc_driving_crossing.py | gate | 105-107 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 17 | poc_driving_decisions.py | gate | 131-133 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 18 | poc_driving_endless_map.py | gate | 47-49 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 19 | poc_driving_japan_town.py | gate | 60-62 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 20 | poc_driving_lateral.py | gate | 99-101 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 21 | poc_driving_longitudinal.py | gate | 69-71 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 22 | poc_driving_pass.py | gate | 101-103 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 23 | poc_driving_school.py | gate | 69-71 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 24 | poc_driving_town.py | gate | 65-67 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 25 | poc_driving_traffic.py | gate | 119-121 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 26 | poc_driving_weather.py | gate | 84-86 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 27 | poc_dual_energy_xray.py | check | 100-102 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 28 | poc_emva1288_in_camera_processing.py | check | 64-66 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 29 | poc_emva1288_sensor.py | gate | 56-58 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 30 | poc_endless_zoom_and_turning_solids.py | check | 83-91 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 31 | poc_fiber_light_guide.py | gate | 54-58 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 32 | poc_flybrain_pointcloud.py | gate | 86-90 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 33 | poc_flybrain_pointcloud.py | check | 208-296 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 34 | poc_food_cutting_measure.py | gate | 53-57 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 35 | poc_four_dimensions_by_three_d_tools.py | check | 61-64 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 36 | poc_fourier_ptychography.py | gate | 100-104 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 37 | poc_good_sample_variation_model.py | check | 126-129 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 38 | poc_granular_heap_repose.py | gate | 46-48 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 39 | poc_graph_hierarchy_segmentation.py | gate | 75-77 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 40 | poc_grating_interferometry.py | gate | 87-91 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 41 | poc_gravitational_lens_invariants.py | check | 83-86 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 42 | poc_gw_detector_pseudo_simulation.py | gate | 83-87 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 43 | poc_hyperspectral_foreign_matter.py | gate | 117-121 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 44 | poc_illumination_cone_vs_na.py | gate | 70-74 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 45 | poc_illusions_and_perpetual_drawing.py | check | 49-52 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 46 | poc_industrial_oct.py | gate | 81-85 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 47 | poc_interreflection_fringe_error.py | check | 75-77 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 48 | poc_iqa_fsim_gmsd_vif.py | gate | 48-50 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 49 | poc_iqa_tid2013.py | gate | 56-58 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 50 | poc_itof_multifreq.py | gate | 106-110 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 51 | poc_kendama.py | gate | 129-131 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 52 | poc_knife_tactile_toughness.py | gate | 60-62 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 53 | poc_laser_line_speckle_floor.py | check | 75-77 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 54 | poc_lens_file_roundtrip.py | gate | 66-70 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 55 | poc_lens_global_search.py | gate | 45-49 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 56 | poc_lens_merit_operands.py | gate | 61-65 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 57 | poc_lens_solves_afocal.py | gate | 58-62 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 58 | poc_lens_tolerancing.py | gate | 37-40 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 59 | poc_lockin_imaging.py | gate | 50-54 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 60 | poc_material_optical_library.py | gate | 139-143 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 61 | poc_measurement_system_analysis.py | check | 79-83 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 62 | poc_moire_alignment.py | gate | 87-91 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 63 | poc_nir_silicon_transmission.py | gate | 77-81 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 64 | poc_noncoaxial_optics.py | gate | 89-93 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 65 | poc_omni360_inspection.py | gate | 19-21 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 66 | poc_optics_drawings.py | gate | 111-115 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 67 | poc_patch_anomaly.py | check | 110-113 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 68 | poc_peg_failure_recovery.py | gate | 50-52 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 69 | poc_peg_insertion_tactile.py | gate | 56-58 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 70 | poc_peg_symmetry_search.py | gate | 55-57 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 71 | poc_pegsim_insertion.py | gate | 64-66 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 72 | poc_periodic_video_boundary.py | check | 48-51 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 73 | poc_phase_measuring_deflectometry.py | check | 88-90 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 74 | poc_photograph_through_prescription.py | gate | 73-77 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 75 | poc_pixel_shift.py | gate | 111-115 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 76 | poc_plateau_venue_lod2.py | check | 59-62 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 77 | poc_pocket_interreflection.py | gate | 100-104 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 78 | poc_pod_lighting.py | check | 97-99 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 79 | poc_polish_wipe_measure.py | gate | 56-58 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 80 | poc_powder_grinding_ae.py | gate | 65-67 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 81 | poc_powder_scoop_pour.py | gate | 46-48 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 82 | poc_pxrd_phase_peel.py | gate | 64-66 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 83 | poc_reproducible_icp.py | gate | 49-51 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 84 | poc_rover_slip_risk_path.py | gate | 61-63 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 85 | poc_sam_hybrid_bonding_voids.py | check | 89-91 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 86 | poc_segmentation_gauntlet.py | gate | 77-79 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 87 | poc_sem_tem_same_particle.py | gate | 47-50 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 88 | poc_shape_from_polarization.py | check | 67-69 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 89 | poc_simcal_pixel_shift.py | gate | 126-130 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 90 | poc_simcal_telecentric.py | gate | 111-115 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | はい |
| 91 | poc_simcal_thin_film.py | gate | 84-88 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 92 | poc_spectrometer_illumination.py | gate | 89-93 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 93 | poc_swarm_obstacle_from_flow.py | gate | 47-49 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 94 | poc_table_tennis_bounce.py | gate | 62-64 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 95 | poc_table_tennis_rally_loop.py | gate | 49-51 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 96 | poc_table_tennis_spin.py | gate | 71-73 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 97 | poc_tacdome_large_deformation.py | gate | 56-58 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 98 | poc_tacscalib_sphere_lut.py | gate | 95-100 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 99 | poc_tacsim_elastic_membrane.py | gate | 56-58 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 100 | poc_tacsim_marker_shear.py | gate | 65-67 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 101 | poc_tactile_dipole_torque.py | gate | 69-71 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 102 | poc_tdi_linescan.py | gate | 66-70 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 103 | poc_telecentric_metrology.py | gate | 119-123 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 104 | poc_tem_ctf_thon_rings.py | gate | 72-76 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 105 | poc_theorems_as_pictures.py | check | 58-62 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 106 | poc_thin_film_reflectometry.py | gate | 115-119 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 107 | poc_tof_camera.py | gate | 37-41 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 108 | poc_ttc_rss.py | gate | 68-70 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 109 | poc_vanishing_detail_and_morphing_area.py | check | 79-82 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 110 | poc_video_physics_consistency.py | gate | 67-69 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 111 | poc_water_inspection_images.py | gate | 57-61 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 112 | poc_water_transparent_media.py | gate | 54-58 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 113 | poc_weed_rice_ratio.py | gate | 130-133 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 114 | poc_what_a_picture_cannot_check.py | check | 63-67 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 115 | poc_world_terrain.py | gate | 73-75 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 116 | poc_zernike_aberrations.py | check | 97-100 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 117 | poc_zmx_public_verify.py | gate | 41-43 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |
| 118 | poc_zoom_configurations.py | gate | 45-49 | relation・measured・unitは各PoC固有 | 各PoCのassert/終了コード | 1 PoC | 軽量 | 短いがschema不統一 | 否 |

## truth生成 (28件)

| # | PoC | 関数/呼出し | 行 | 契約の完全さ | 正しさの証拠 | 使用実績 | 性能 | 読みやすさ | 基底 |
|---:|---|---|---:|---|---|---|---|---|---|
| 1 | poc_allsky_cloud_cover.py | truth_fraction | 171-180 | 単位・座標・mask・段階の一部 | 図・assertとの照合 | 1 PoC | 場面依存 | 物理は明瞭、契約は暗黙 | 否 |
| 2 | poc_battery_electrode_breathing.py | truth | 132-146 | 単位・座標・mask・段階の一部 | 図・assertとの照合 | 1 PoC | 場面依存 | 物理は明瞭、契約は暗黙 | 否 |
| 3 | poc_bev_sensor_fusion.py | ground_truth | 264-283 | 単位・座標・mask・段階の一部 | 図・assertとの照合 | 1 PoC | 場面依存 | 物理は明瞭、契約は暗黙 | 否 |
| 4 | poc_bone_trabecular_thickness.py | truth_at | 262-264 | 単位・座標・mask・段階の一部 | 図・assertとの照合 | 1 PoC | 場面依存 | 物理は明瞭、契約は暗黙 | 否 |
| 5 | poc_change_detection_misreg.py | truth_masks | 289-304 | 単位・座標・mask・段階の一部 | 図・assertとの照合 | 1 PoC | 場面依存 | 物理は明瞭、契約は暗黙 | 否 |
| 6 | poc_emva1288_in_camera_processing.py | truth | 209-214 | 単位・座標・mask・段階の一部 | 図・assertとの照合 | 1 PoC | 場面依存 | 物理は明瞭、契約は暗黙 | 否 |
| 7 | poc_focus_stacking.py | ground_truth | 119-159 | 単位・座標・mask・段階の一部 | 図・assertとの照合 | 1 PoC | 場面依存 | 物理は明瞭、契約は暗黙 | 否 |
| 8 | poc_four_dimensions_by_three_d_tools.py | truth_b | 406-409 | 単位・座標・mask・段階の一部 | 図・assertとの照合 | 1 PoC | 場面依存 | 物理は明瞭、契約は暗黙 | 否 |
| 9 | poc_gear_tooth_metrology.py | _truth_radius | 519-525 | 単位・座標・mask・段階の一部 | 図・assertとの照合 | 1 PoC | 場面依存 | 物理は明瞭、契約は暗黙 | 否 |
| 10 | poc_hyperspectral_foreign_matter.py | comp_truth | 982-992 | 単位・座標・mask・段階の一部 | 図・assertとの照合 | 1 PoC | 場面依存 | 物理は明瞭、契約は暗黙 | 否 |
| 11 | poc_laser_line_speckle_floor.py | truth_row | 104-105 | 単位・座標・mask・段階の一部 | 図・assertとの照合 | 1 PoC | 場面依存 | 物理は明瞭、契約は暗黙 | 否 |
| 12 | poc_lidar_terrain_change.py | truth | 472-481 | 単位・座標・mask・段階の一部 | 図・assertとの照合 | 1 PoC | 場面依存 | 物理は明瞭、契約は暗黙 | 否 |
| 13 | poc_matrix_code_reading.py | ground_truth_homography | 170-194 | 単位・座標・mask・段階の一部 | 図・assertとの照合 | 1 PoC | 場面依存 | 物理は明瞭、契約は暗黙 | 否 |
| 14 | poc_pixel_shift.py | truth_rgb | 263-265 | 単位・座標・mask・段階の一部 | 図・assertとの照合 | 1 PoC | 場面依存 | 物理は明瞭、契約は暗黙 | 否 |
| 15 | poc_pv_thermal_survey.py | ground_truth | 577-600 | 単位・座標・mask・段階の一部 | 図・assertとの照合 | 1 PoC | 場面依存 | 物理は明瞭、契約は暗黙 | 否 |
| 16 | poc_rover_slip_risk_path.py | sand_truth | 76-83 | 単位・座標・mask・段階の一部 | 図・assertとの照合 | 1 PoC | 場面依存 | 物理は明瞭、契約は暗黙 | 否 |
| 17 | poc_screw_thread_metrology.py | thread_truth | 98-108 | 単位・座標・mask・段階の一部 | 図・assertとの照合 | 1 PoC | 場面依存 | 物理は明瞭、契約は暗黙 | 否 |
| 18 | poc_sea_ice_concentration.py | make_truth | 95-108 | 単位・座標・mask・段階の一部 | 図・assertとの照合 | 1 PoC | 場面依存 | 物理は明瞭、契約は暗黙 | 否 |
| 19 | poc_slanted_edge_sfr_limits.py | truth_curve | 24-28 | 単位・座標・mask・段階の一部 | 図・assertとの照合 | 1 PoC | 場面依存 | 物理は明瞭、契約は暗黙 | 否 |
| 20 | poc_structure_4d_deterioration.py | truth_normal | 399-402 | 単位・座標・mask・段階の一部 | 図・assertとの照合 | 1 PoC | 場面依存 | 物理は明瞭、契約は暗黙 | 否 |
| 21 | poc_structure_4d_deterioration.py | truth_footprint | 405-417 | 単位・座標・mask・段階の一部 | 図・assertとの照合 | 1 PoC | 場面依存 | 物理は明瞭、契約は暗黙 | 否 |
| 22 | poc_superresolution_limits.py | band_limited_truth | 306-308 | 単位・座標・mask・段階の一部 | 図・assertとの照合 | 1 PoC | 場面依存 | 物理は明瞭、契約は暗黙 | 否 |
| 23 | poc_thermal_radiometry.py | scene_truth | 1338-1355 | 単位・座標・mask・段階の一部 | 図・assertとの照合 | 1 PoC | 場面依存 | 物理は明瞭、契約は暗黙 | 否 |
| 24 | poc_thin_film_reflectometry.py | wafer_truth | 542-572 | 単位・座標・mask・段階の一部 | 図・assertとの照合 | 1 PoC | 場面依存 | 物理は明瞭、契約は暗黙 | 否 |
| 25 | poc_tree_ring_dendro.py | ray_truth | 210-247 | 単位・座標・mask・段階の一部 | 図・assertとの照合 | 1 PoC | 場面依存 | 物理は明瞭、契約は暗黙 | 否 |
| 26 | poc_vessel_network.py | truth_at | 562-571 | 単位・座標・mask・段階の一部 | 図・assertとの照合 | 1 PoC | 場面依存 | 物理は明瞭、契約は暗黙 | 否 |
| 27 | poc_video_physics_consistency.py | truth_track | 84-86 | 単位・座標・mask・段階の一部 | 図・assertとの照合 | 1 PoC | 場面依存 | 物理は明瞭、契約は暗黙 | 否 |
| 28 | poc_weed_rice_ratio.py | region_truth | 208-211 | 単位・座標・mask・段階の一部 | 図・assertとの照合 | 1 PoC | 場面依存 | 物理は明瞭、契約は暗黙 | 否 |

## 誤差・採点 (103件)

| # | PoC | 関数/呼出し | 行 | 契約の完全さ | 正しさの証拠 | 使用実績 | 性能 | 読みやすさ | 基底 |
|---:|---|---|---:|---|---|---|---|---|---|
| 1 | poc_allsky_cloud_cover.py | section5_split_errors | 394-428 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 2 | poc_am_thermal_to_ct.py | _dice_reg | 382-391 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 3 | poc_am_thermal_to_ct.py | seg_scores | 833-843 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 4 | poc_battery_ct_degradation.py | outer_metrics | 462-499 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 5 | poc_battery_ct_degradation.py | internal_metrics | 598-638 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 6 | poc_bev_sensor_fusion.py | metrics | 397-411 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 7 | poc_bev_sensor_fusion.py | _band_iou | 875-882 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 8 | poc_bilateral_asymmetry.py | plane_error | 289-293 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 9 | poc_bone_trabecular_thickness.py | direct_metrics | 228-235 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 10 | poc_bone_trabecular_thickness.py | plate_metrics | 238-250 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 11 | poc_camera_calibration.py | pose_errors | 245-252 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 12 | poc_camera_shake_deblur.py | psnr | 268-269 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 13 | poc_carla_bridge.py | score | 115-132 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 14 | poc_change_detection_misreg.py | radiometric_linear | 482-492 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 15 | poc_cold_chain_excursion.py | section_metrics | 813-906 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 16 | poc_ct_fidelity.py | rmse | 130-132 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 17 | poc_datacenter_thermal_field.py | peak_error | 330-334 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 18 | poc_datacenter_thermal_field.py | loc_error | 346-368 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 19 | poc_datacenter_thermal_field.py | section_metrics | 793-884 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 20 | poc_dehazing.py | psnr_masked | 285-291 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 21 | poc_dense_bubble_count.py | alcon_score | 219-236 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 22 | poc_dense_bubble_count.py | scored_by_component | 247-262 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 23 | poc_dense_bubble_count.py | chapter_scorer | 484-500 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 24 | poc_document_scan.py | landmark_error | 358-366 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 25 | poc_document_scan.py | band_metrics | 394-423 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 26 | poc_driving_town.py | joint_errors | 78-82 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 27 | poc_dtof_ranging.py | rmse_mm | 166-168 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 28 | poc_dual_energy_xray.py | _mc_error | 483-492 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 29 | poc_em_second_opinion.py | scores | 232-236 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 30 | poc_fabric_defect.py | _score | 154-157 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 31 | poc_fabric_defect.py | section_period_error | 569-633 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 32 | poc_focus_stacking.py | psnr | 255-256 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 33 | poc_forensics_roc.py | score_ela | 226-236 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 34 | poc_forensics_roc.py | score_noise | 239-242 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 35 | poc_forensics_roc.py | score_ghost_argmin | 248-251 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 36 | poc_forensics_roc.py | score_ghost_contrast | 254-263 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 37 | poc_forensics_roc.py | score_random | 266-275 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 38 | poc_fourier_ptychography.py | _field_error | 122-132 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 39 | poc_fourier_ptychography.py | _pupil_error_waves | 294-300 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 40 | poc_gear_tooth_metrology.py | section_pitch_error | 691-740 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 41 | poc_glyph_typo_detection.py | _score | 237-242 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 42 | poc_good_sample_variation_model.py | _score_all | 356-368 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 43 | poc_good_sample_variation_model.py | _metrics | 371-378 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 44 | poc_good_sample_variation_model.py | _save_visa_metrics_recorded | 381-396 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 45 | poc_graph_hierarchy_segmentation.py | dice | 80-81 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 46 | poc_itof_multifreq.py | mc_error_rate | 307-321 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 47 | poc_leaf_disease_area.py | error_kinds | 502-519 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 48 | poc_leak_localization.py | _score_1d | 219-227 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 49 | poc_livestock_body_volume.py | section_metrics | 710-763 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 50 | poc_matrix_code_reading.py | struct_score | 497-504 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 51 | poc_microns_brain_wave.py | _zscore_rows | 154-155 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 52 | poc_motion_magnification.py | fidelity_error | 170-180 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 53 | poc_mri_bias_field.py | area_errors | 220-226 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 54 | poc_mri_bias_field.py | predict_zero_errors | 229-237 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 55 | poc_mt_hidden_fault.py | score | 101-104 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 56 | poc_mueller_dofp_observability.py | _report_figure_errors | 55-57 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 57 | poc_pallet_load_utilization.py | section_iou | 585-625 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 58 | poc_panorama_drift.py | spread_loop_error | 321-324 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 59 | poc_panorama_drift.py | pose_error_px | 458-461 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 60 | poc_panorama_drift.py | seam_error_px | 464-472 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 61 | poc_particle_tracking.py | _score | 682-696 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 62 | poc_patch_anomaly.py | score_maps | 210-212 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 63 | poc_patch_anomaly.py | metrics | 224-228 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 64 | poc_phase_measuring_deflectometry.py | force_scores | 1031-1038 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 65 | poc_pigment_unmixing.py | score_maps | 742-749 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 66 | poc_pipe_wall_loss.py | score | 349-367 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 67 | poc_pixel_shift.py | psnr | 280-283 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 68 | poc_pixel_shift.py | chapter_shift_error | 539-587 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 69 | poc_pixel_shift.py | _real_region_metrics | 1091-1097 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 70 | poc_polarization_specular.py | rmse | 238-239 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 71 | poc_print_layer_inspection.py | score | 112-120 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 72 | poc_print_registration.py | section8_metrics | 1090-1258 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 73 | poc_pv_thermal_survey.py | radiometric_gain | 290-304 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 74 | poc_pv_thermal_survey.py | score | 662-686 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 75 | poc_real_deblur_honesty.py | psnr | 106-108 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 76 | poc_real_stereo_depth.py | score | 113-126 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 77 | poc_recycling_sorting.py | score | 406-439 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 78 | poc_recycling_sorting.py | compare | 761-771 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 79 | poc_registration_basin.py | rot_error_deg | 181-184 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 80 | poc_registration_basin.py | cen_error | 187-189 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 81 | poc_safety_clearance.py | section_metrics | 916-949 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 82 | poc_screw_thread_metrology.py | profile_metrics | 289-327 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 83 | poc_sea_ice_concentration.py | section_endmember_error | 355-376 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 84 | poc_sem_tem_same_particle.py | _error_panel | 447-454 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 85 | poc_settlement_significance.py | zscore | 271-274 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 86 | poc_simcal_pixel_shift.py | score | 308-319 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 87 | poc_simcal_telecentric.py | pure_error | 423-438 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 88 | poc_simcal_thin_film.py | split_indices | 327-333 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 89 | poc_slanted_edge_sfr_limits.py | _report_figure_errors | 81-83 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 90 | poc_solar_limb_darkening.py | _geometric_prediction | 372-377 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 91 | poc_symmetry_restoration.py | plane_error | 241-248 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 92 | poc_symmetry_restoration.py | restore_symmetric | 327-334 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 93 | poc_symmetry_restoration.py | score_restoration | 337-353 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 94 | poc_symmetry_restoration.py | trim_symmetric | 715-729 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 95 | poc_text_region_truth.py | _iou | 98-102 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 96 | poc_tree_ring_dendro.py | section_pith_error | 664-723 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 97 | poc_warehouse_flow.py | score | 658-691 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 98 | poc_wavefront_aberration_limits.py | _report_figure_errors | 73-75 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 99 | poc_web_roll_periodicity.py | comb_score | 276-293 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 100 | poc_weed_rice_ratio.py | iou | 179-181 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 101 | poc_weld_bead_scan_angle.py | score | 557-574 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 102 | poc_weld_bead_scan_angle.py | geometric_only | 763-772 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |
| 103 | poc_white_balance.py | angular_error | 296-304 | mask・NaN・emptyの一部 | 各PoCの既定値 | 1 PoC | 概ね軽量 | 用途特化 | 否 |

## 成果物集合 (34件)

| # | PoC | 関数/呼出し | 行 | 契約の完全さ | 正しさの証拠 | 使用実績 | 性能 | 読みやすさ | 基底 |
|---:|---|---|---:|---|---|---|---|---|---|
| 1 | poc_active_contours.py | figures | 327-430 | caption・shapeはexamplefigへ | figures.json/PNG | 1 PoC | 図数依存 | 構成は明瞭 | 否 |
| 2 | poc_agv_fleet.py | figures | 274-321 | caption・shapeはexamplefigへ | figures.json/PNG | 1 PoC | 図数依存 | 構成は明瞭 | 否 |
| 3 | poc_air_hockey_intercept.py | figures | 432-595 | caption・shapeはexamplefigへ | figures.json/PNG | 1 PoC | 図数依存 | 構成は明瞭 | 否 |
| 4 | poc_code_matching_breakdown.py | figures | 548-677 | caption・shapeはexamplefigへ | figures.json/PNG | 1 PoC | 図数依存 | 構成は明瞭 | 否 |
| 5 | poc_diabolo_model_and_vision.py | figures | 514-614 | caption・shapeはexamplefigへ | figures.json/PNG | 1 PoC | 図数依存 | 構成は明瞭 | 否 |
| 6 | poc_dose_uniformity_from_grinding.py | figures | 287-348 | caption・shapeはexamplefigへ | figures.json/PNG | 1 PoC | 図数依存 | 構成は明瞭 | 否 |
| 7 | poc_driving_crossing.py | figures | 1576-1606 | caption・shapeはexamplefigへ | figures.json/PNG | 1 PoC | 図数依存 | 構成は明瞭 | 否 |
| 8 | poc_driving_decisions.py | figures | 1831-1845 | caption・shapeはexamplefigへ | figures.json/PNG | 1 PoC | 図数依存 | 構成は明瞭 | 否 |
| 9 | poc_driving_lateral.py | figures | 1299-1311 | caption・shapeはexamplefigへ | figures.json/PNG | 1 PoC | 図数依存 | 構成は明瞭 | 否 |
| 10 | poc_driving_pass.py | figures | 1808-1846 | caption・shapeはexamplefigへ | figures.json/PNG | 1 PoC | 図数依存 | 構成は明瞭 | 否 |
| 11 | poc_driving_traffic.py | figures | 1182-1223 | caption・shapeはexamplefigへ | figures.json/PNG | 1 PoC | 図数依存 | 構成は明瞭 | 否 |
| 12 | poc_flybrain_pointcloud.py | figures | 312-376 | caption・shapeはexamplefigへ | figures.json/PNG | 1 PoC | 図数依存 | 構成は明瞭 | 否 |
| 13 | poc_food_cutting_measure.py | figures | 722-726 | caption・shapeはexamplefigへ | figures.json/PNG | 1 PoC | 図数依存 | 構成は明瞭 | 否 |
| 14 | poc_granular_heap_repose.py | figures | 631-638 | caption・shapeはexamplefigへ | figures.json/PNG | 1 PoC | 図数依存 | 構成は明瞭 | 否 |
| 15 | poc_graph_hierarchy_segmentation.py | figures | 444-556 | caption・shapeはexamplefigへ | figures.json/PNG | 1 PoC | 図数依存 | 構成は明瞭 | 否 |
| 16 | poc_iqa_fsim_gmsd_vif.py | figures | 190-249 | caption・shapeはexamplefigへ | figures.json/PNG | 1 PoC | 図数依存 | 構成は明瞭 | 否 |
| 17 | poc_knife_tactile_toughness.py | figures | 358-414 | caption・shapeはexamplefigへ | figures.json/PNG | 1 PoC | 図数依存 | 構成は明瞭 | 否 |
| 18 | poc_lens_tolerancing.py | figures | 152-198 | caption・shapeはexamplefigへ | figures.json/PNG | 1 PoC | 図数依存 | 構成は明瞭 | 否 |
| 19 | poc_peg_failure_recovery.py | figures | 315-398 | caption・shapeはexamplefigへ | figures.json/PNG | 1 PoC | 図数依存 | 構成は明瞭 | 否 |
| 20 | poc_peg_insertion_tactile.py | figures | 620-718 | caption・shapeはexamplefigへ | figures.json/PNG | 1 PoC | 図数依存 | 構成は明瞭 | 否 |
| 21 | poc_peg_symmetry_search.py | figures | 536-628 | caption・shapeはexamplefigへ | figures.json/PNG | 1 PoC | 図数依存 | 構成は明瞭 | 否 |
| 22 | poc_pegsim_insertion.py | figures | 295-361 | caption・shapeはexamplefigへ | figures.json/PNG | 1 PoC | 図数依存 | 構成は明瞭 | 否 |
| 23 | poc_plateau_venue_lod2.py | figures | 177-198 | caption・shapeはexamplefigへ | figures.json/PNG | 1 PoC | 図数依存 | 構成は明瞭 | 否 |
| 24 | poc_pocket_interreflection.py | figures | 346-414 | caption・shapeはexamplefigへ | figures.json/PNG | 1 PoC | 図数依存 | 構成は明瞭 | 否 |
| 25 | poc_polish_wipe_measure.py | figures | 427-523 | caption・shapeはexamplefigへ | figures.json/PNG | 1 PoC | 図数依存 | 構成は明瞭 | 否 |
| 26 | poc_powder_grinding_ae.py | figures | 465-493 | caption・shapeはexamplefigへ | figures.json/PNG | 1 PoC | 図数依存 | 構成は明瞭 | 否 |
| 27 | poc_powder_scoop_pour.py | figures | 700-707 | caption・shapeはexamplefigへ | figures.json/PNG | 1 PoC | 図数依存 | 構成は明瞭 | 否 |
| 28 | poc_reproducible_icp.py | figures | 362-443 | caption・shapeはexamplefigへ | figures.json/PNG | 1 PoC | 図数依存 | 構成は明瞭 | 否 |
| 29 | poc_segmentation_gauntlet.py | figures | 272-305 | caption・shapeはexamplefigへ | figures.json/PNG | 1 PoC | 図数依存 | 構成は明瞭 | 否 |
| 30 | poc_swarm_obstacle_from_flow.py | figures | 319-395 | caption・shapeはexamplefigへ | figures.json/PNG | 1 PoC | 図数依存 | 構成は明瞭 | 否 |
| 31 | poc_tacdome_large_deformation.py | figures | 348-469 | caption・shapeはexamplefigへ | figures.json/PNG | 1 PoC | 図数依存 | 構成は明瞭 | 否 |
| 32 | poc_tacsim_elastic_membrane.py | figures | 234-317 | caption・shapeはexamplefigへ | figures.json/PNG | 1 PoC | 図数依存 | 構成は明瞭 | 否 |
| 33 | poc_tacsim_marker_shear.py | figures | 427-538 | caption・shapeはexamplefigへ | figures.json/PNG | 1 PoC | 図数依存 | 構成は明瞭 | 否 |
| 34 | poc_tactile_dipole_torque.py | figures | 520-668 | caption・shapeはexamplefigへ | figures.json/PNG | 1 PoC | 図数依存 | 構成は明瞭 | 否 |

## 動画保存 (82件)

| # | PoC | 関数/呼出し | 行 | 契約の完全さ | 正しさの証拠 | 使用実績 | 性能 | 読みやすさ | 基底 |
|---:|---|---|---:|---|---|---|---|---|---|
| 1 | poc_active_contours.py | figs.save_video | 389 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 2 | poc_active_contours.py | figs.save_video | 412 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 3 | poc_active_contours.py | figs.save_video | 428 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 4 | poc_agv_fleet.py | figs.save_video | 300 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 5 | poc_am_thermal_to_ct.py | figs.save_video | 1057 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 6 | poc_am_thermal_to_ct.py | figs.save_video | 1114 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 7 | poc_am_thermal_to_ct.py | figs.save_video | 1130 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 8 | poc_beam_modal_video.py | figs.save_video | 911 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 9 | poc_cad_scan_deviation.py | figs.save_video | 1595 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 10 | poc_camera_calibration.py | figs.save_video | 492 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 11 | poc_camera_shake_deblur.py | figs.save_video | 435 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 12 | poc_crack_width_timeseries.py | figs.save_video | 594 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 13 | poc_ct_void_morphology.py | figs.save_video | 1045 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 14 | poc_dehazing.py | figs.save_video | 417 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 15 | poc_dem_terrain.py | figs.save_video | 248 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 16 | poc_dic_strain.py | figs.save_video | 740 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 17 | poc_driving_crossing.py | figs.save_video | 1194 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 18 | poc_driving_crossing.py | figs.save_video | 1283 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 19 | poc_driving_crossing.py | figs.save_video | 1359 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 20 | poc_driving_crossing.py | figs.save_video | 1454 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 21 | poc_driving_decisions.py | figs.save_video | 1554 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 22 | poc_driving_decisions.py | figs.save_video | 1666 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 23 | poc_driving_endless_map.py | figs.save_video | 302 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 24 | poc_driving_endless_map.py | figs.save_video | 348 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 25 | poc_driving_humanoids.py | figs.save_video | 173 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 26 | poc_driving_lateral.py | figs.save_video | 1030 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 27 | poc_driving_lateral.py | figs.save_video | 1115 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 28 | poc_driving_pass.py | figs.save_video | 1281 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 29 | poc_driving_pass.py | figs.save_video | 1416 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 30 | poc_driving_pass.py | figs.save_video | 1719 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 31 | poc_driving_traffic.py | figs.save_video | 995 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 32 | poc_driving_traffic.py | figs.save_video | 1100 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 33 | poc_dtof_ranging.py | figs.save_video | 330 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 34 | poc_emva1288_sensor.py | figs.save_video | 427 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 35 | poc_focus_stacking.py | figs.save_video | 351 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 36 | poc_graph_hierarchy_segmentation.py | figs.save_video | 535 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 37 | poc_graph_hierarchy_segmentation.py | figs.save_video | 544 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 38 | poc_graph_hierarchy_segmentation.py | figs.save_video | 553 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 39 | poc_interferometry_step.py | figs.save_video | 177 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 40 | poc_interferometry_step.py | figs.save_video | 347 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 41 | poc_lens_merit_operands.py | figs.save_video | 436 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 42 | poc_lens_solves_afocal.py | figs.save_video | 630 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 43 | poc_lens_tolerancing.py | figs.save_video | 197 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 44 | poc_lidar_terrain_change.py | figs.save_video | 1517 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 45 | poc_lightfield_depth.py | figs.save_video | 395 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 46 | poc_livestock_body_volume.py | figs.save_video | 1123 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 47 | poc_lockin_imaging.py | figs.save_video | 410 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 48 | poc_mesh_quality_repair.py | figs.save_video | 1182 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 49 | poc_motion_magnification.py | figs.save_video | 372 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 50 | poc_multibeam_bathymetry.py | figs.save_video | 1583 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 51 | poc_omni360_inspection.py | figs.save_video | 147 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 52 | poc_panorama_drift.py | figs.save_video | 646 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 53 | poc_particle_tracking.py | figs.save_video | 952 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 54 | poc_patch_anomaly.py | figs.save_video | 325 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 55 | poc_photoelasticity.py | figs.save_video | 607 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 56 | poc_photograph_through_prescription.py | figs.save_video | 704 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 57 | poc_plenoptic_camera.py | figs.save_video | 250 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 58 | poc_registration_basin.py | figs.save_video | 420 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 59 | poc_river_surface_velocity.py | figs.save_video | 995 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 60 | poc_sem_tem_same_particle.py | figs.save_video | 514 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 61 | poc_stockpile_volume.py | figs.save_video | 809 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 62 | poc_strain_history.py | figs.save_video | 886 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 63 | poc_structure_4d_deterioration.py | figs.save_video | 1725 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 64 | poc_superresolution_limits.py | figs.save_video | 501 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 65 | poc_table_tennis_bounce.py | figs.save_video | 396 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 66 | poc_table_tennis_bounce.py | figs.save_video | 423 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 67 | poc_table_tennis_rally_loop.py | figs.save_video | 302 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 68 | poc_table_tennis_rally_loop.py | figs.save_video | 337 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 69 | poc_table_tennis_rally_loop.py | figs.save_video | 376 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 70 | poc_table_tennis_spin.py | figs.save_video | 386 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 71 | poc_table_tennis_spin.py | figs.save_video | 393 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 72 | poc_table_tennis_spin.py | figs.save_video | 417 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 73 | poc_template_tracking.py | figs.save_video | 471 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 74 | poc_thermography_ndt.py | figs.save_video | 206 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 75 | poc_timelapse_growth.py | figs.save_video | 778 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 76 | poc_tof_camera.py | figs.save_video | 251 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 77 | poc_traffic_counting.py | figs.save_video | 941 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 78 | poc_water_inspection_images.py | figs.save_video | 534 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 79 | poc_water_transparent_media.py | figs.save_video | 545 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 80 | poc_wound_area_tracking.py | figs.save_video | 620 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 81 | poc_xyt_event_surface.py | figs.save_video | 978 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
| 82 | poc_zmx_public_verify.py | figs.save_video | 110 | fps・stride・scaleの一部 | GIF/MP4 manifest | 1 call | encode依存 | 引数がPoCごとに分散 | 否 |
