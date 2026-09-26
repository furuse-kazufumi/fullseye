# What the PoCs hardened — found, fixed, and gated

**Language:** [日本語](HARDENING.md) · [English](HARDENING.en.md)

The PoCs are exhibits, but they are also defect finders. This is the ledger:
which PoC found it, what was changed, and which gate now stops it coming back —
one file per finding.

A gate (`tests/test_capabilities.py`) checks `found_by` against the PoC files,
`ops` against all four public tiers, `gate` against the test functions that exist,
and `where` against the files on disk. An entry marked `status: fixed` with an
empty `gate` refuses to build the index at all — so that this ledger cannot itself
become a place where 'we fixed it' is recorded with nothing stopping a relapse.

* Organised by what you want to do → [CAPABILITIES.en.md](CAPABILITIES.en.md)
* Full narrative and numbers → [KNOWN_ISSUES.md](KNOWN_ISSUES.md)

**35 findings (35 fixed), from 14 PoCs.**

## By kind

| Kind | Findings | Fixed |
|---|---:|---:|
| Silently wrong (no exception) | 18 | 18 |
| Implementation defect | 5 | 5 |
| The gate did not stand where the accident happens | 4 | 4 |
| Present but unreachable | 7 | 7 |
| Documentation hole (one-way reference, stale number) | 1 | 1 |

## By the PoC that found it

| PoC | Findings |
|---|---:|
| [`genspark_external_review`](../examples/genspark_external_review.py) | 17 |
| [`shape_factors_closed_form`](../examples/shape_factors_closed_form.py) | 5 |
| [`degenerate_inputs`](../examples/degenerate_inputs.py) | 2 |
| [`line_handshake`](../examples/line_handshake.py) | 1 |
| [`poc_geodetic_height_frames`](../examples/poc_geodetic_height_frames.py) | 1 |
| [`poc_livestock_body_volume`](../examples/poc_livestock_body_volume.py) | 1 |
| [`poc_multibeam_bathymetry`](../examples/poc_multibeam_bathymetry.py) | 1 |
| [`poc_print_registration`](../examples/poc_print_registration.py) | 1 |
| [`poc_rotation_invariance_audit`](../examples/poc_rotation_invariance_audit.py) | 1 |
| [`poc_search_sweep_width`](../examples/poc_search_sweep_width.py) | 1 |
| [`poc_stockpile_volume`](../examples/poc_stockpile_volume.py) | 1 |
| [`poc_thermal_radiometry`](../examples/poc_thermal_radiometry.py) | 1 |
| [`threshold_family_agreement`](../examples/threshold_family_agreement.py) | 1 |
| [`tools/chain_fuzz.py`](../tools/chain_fuzz.py) | 1 |

## The findings

### Silently wrong (no exception)

#### [ECEF→測地座標が、自分の逆関数が拒否する緯度 180 度を黙って返していた](hardening/ecef-to-geodetic-returned-latitude-180.md) _(ja)_

地球の中心付近を渡すと **lat = 180.0000 度**が返る —— 緯度として存在しない値。しかも `dem_geodetic_to_ecef` 自身が「lat_deg must be within [-90, 90]」で**拒否する**値だった。**自分が産んだ値を自分の逆関数が受け取れない**。例外は出ないので、下流は「もっともらしい数字」を受け取る。 _(ja)_

Found by: `poc_geodetic_height_frames` / Changed: `demops.py` / Gate: `test_ecef_to_geodetic_refuses_the_region_where_latitude_is_not_unique`, `test_ecef_to_geodetic_never_returns_a_latitude_its_own_inverse_rejects` / Status: fixed

#### [位置合わせが、賛成率 1.00 のまま 80.85 px 外していた](hardening/frame-align-inlier-ratio-is-not-confidence.md) _(ja)_

網点のような**繰り返し構造**では、`frame_align` の `inlier_ratio` が **1.00 のまま 80.85 px 外す**。独立に再現した((0, 1.30) の真値に対し (54.24, 30.12) を返す)。例外は出ず、賛成率という「自信ありげな数字」だけが残る。 _(ja)_

Found by: `poc_print_registration` / Changed: `astrostack.py` / Gate: `test_inlier_ratio_is_not_a_probability_that_the_answer_is_right`, `test_a_tie_in_the_smoothed_vote_no_longer_picks_an_empty_bin` / Status: fixed

#### [頑健な雑音推定が整数画像で 0 に潰れ、点目標検出が黙って何も返さなくなっていた](hardening/noise-sigma-mad-collapses-on-quantised-data.md) _(ja)_

`noise_sigma(method="mad")` は整数値の画像で **σ=0.5 相当のとき 0.0000** を返す。返せる値は **1.4826 の倍数だけ**で、σ=1.0 も σ=1.983 も**同じ 1.4826**。14 bit の生 DN はまさに整数なので、これは特殊な入力ではない。下流の影響を独立に確認: 200x200 の整数フレームに**点目標を 2 個植えて `star_detect` が 0 個**を返した(例外なし)。 _(ja)_

Found by: `poc_thermal_radiometry` / Changed: `astrostack.py` / Gate: `test_mad_warns_when_quantisation_collapses_it_to_zero`, `test_star_detect_refuses_instead_of_silently_finding_nothing` / Status: fixed

#### [変換の定義が無い入力が、黙って「それらしい」出力になっていた](hardening/inputs-without-a-conversion-were-not-refused.md) _(ja)_

第三者レビュー(GenSpark、0.2.0、core / all の 2 環境)が dtype と形を網羅して見つけた 4 件。共通点は**例外にならず、値が返る**こと。 _(ja)_

Found by: `genspark_external_review` / Changed: `api.py`, `ops.py` / Gate: `test_non_numeric_arrays_are_refused_under_every_policy`, `test_complex_input_to_a_real_op_is_refused_not_silently_realised`, `test_otsu_all_nan_is_an_explicit_error_not_a_numpy_runtime_warning`, `test_nary_shape_mismatch_says_what_is_needed`, `test_op_objects_pickle_by_name` / Status: fixed

#### [NaN を含む画像がフィルタを通ると、NaN が黙って消えて有限の画像になっていた](hardening/nonfinite-output-was-sanitized-silently.md) _(ja)_

GenSpark の第 3 報(#14)。中央 1 画素だけ NaN の 9×9 画像を `gaussian` / `median_image` / `mean_image` / `sobel_amp` に通すと、**出力は全画素が有限**で、警告も `fullseye.fallbacks()` の記録も無い。`on_error="raise"` でも止まらない。scipy の `gaussian_filter` は NaN を伝播させるので、消しているのは fullseye。 _(ja)_

Found by: `degenerate_inputs` / Changed: `backend_safe.py`, `opassist.py`, `api.py` / Gate: `test_partial_nan_input_is_recorded_as_a_nonfinite_output_under_the_default_policy`, `test_partial_nan_input_stops_under_raise`, `test_nary_ops_are_found_by_op_find_and_explained_as_list_calls` / Status: fixed

#### [空の op 名が lowpass に解決し、float16 / float32 が契約の float64 に昇格されていなかった](hardening/empty-name-resolved-and-narrow-floats-not-upcast.md) _(ja)_

GenSpark 第 15 報(境界値・型不一致の総当たり)。 _(ja)_

Found by: `genspark_external_review` / Changed: `api.py` / Gate: `test_empty_operator_name_is_unknown_not_lowpass`, `test_narrow_floats_are_upcast_to_the_float64_contract`, `test_on_error_message_names_the_default_none` / Status: fixed

#### [`engine.load(path)` がインスタンスでは何もせず、空のエンジンが入力をそのまま返していた](hardening/engine-load-on-an-instance-was-silently-ignored.md) _(ja)_

GenSpark 第 16 報(N37 / N39 / N40 / N41)。 _(ja)_

Found by: `genspark_external_review` / Changed: `engine.py`, `imgevolve.py` / Gate: `test_load_on_an_instance_loads_into_it`, `test_dict_stages_are_understood_and_bad_stage_types_are_refused`, `test_upto_is_an_inclusive_stage_index_and_out_of_range_is_refused`, `test_to_python_carries_the_ops_string_and_a_coding_line` / Status: fixed

#### [write_image が書けなかった事実を捨てて無言で戻り、uint16 が 8 bit に潰れ、読めない理由が全部「無い」だった](hardening/image-io-dropped-write-failures-and-crushed-16-bit.md) _(ja)_

GenSpark 第 18・19 報(N75 / N76 / N77 / N78 / N79、N72 の同族、N81 の音声分)。全部 master で再現した。 _(ja)_

Found by: `genspark_external_review` / Changed: `api.py`, `imgio.py`, `ops.py`, `dsp.py` / Gate: `test_write_refuses_a_missing_directory_instead_of_pretending`, `test_write_refuses_an_unwritable_extension_naming_the_writable_ones`, `test_ppm_takes_a_grey_image_and_reads_back`, `test_read_errors_say_which_kind_of_failure`, `test_uint16_is_written_as_16_bit_and_float_depth_options_are_lossless`, `test_float_default_is_8_bit_as_documented_and_depth_needs_a_capable_extension` / Status: fixed

#### [台帳の引き方が未知の名前に黙って空を返し、write_wav の path が台帳でデータ扱いされていた](hardening/ledger-lookups-returned-empty-for-unknown-names.md) _(ja)_

GenSpark 第 15〜27 報(N67 / N68 / N69 / N71、N84 / N85 / N87、N92 / N94 / N95 / N97、および N72 / N73 / N74 / N80 / N88 / N89 / N90 / N91 / N93 / N96 / N99 / N100)。 _(ja)_

Found by: `genspark_external_review` / Changed: `opassist.py`, `dsp.py`, `api.py` / Gate: `test_producers_and_consumers_refuse_unknown_sorts_and_op_names`, `test_presets_refuse_unknown_ops_and_are_empty_for_known_ops_without_presets`, `test_write_wav_path_is_not_a_data_input_in_the_ledger`, `test_no_ignored_exception_leaks_to_stderr_when_write_wav_is_misused`, `test_list_ops_rows_expose_the_native_guard`, `test_empty_input_contract_is_uniform_across_ops`, `test_every_shared_alias_resolves_by_rule_not_by_registration_order`, `test_list_ops_rows_name_their_alias_peers`, `test_list_ops_sort_and_search_fold_case_and_accents`, `test_op_run_refuses_to_call_with_a_none_sample_and_names_the_sort`, `test_non_array_images_are_type_errors_regardless_of_policy`, `test_data_range_of_without_arrays_is_a_contract_error`, `test_lazy_torch_import_error_says_whether_torch_is_installed`, `test_list_ops_unknown_sort_is_refused_and_lists_the_known_ones` / Status: fixed

#### [MCP カタログの facade 層がクラス 41 個を op として並べていた](hardening/mcp-facade-layer-listed-classes-as-ops.md) _(ja)_

GenSpark 第 41 報(2026-09-20)N141: 「facade ソースに facade 表に無い名前が 474 件、Python のクラス名を含む」。 master で再現 —— `Catalog.load()` の 2,497 項目のうち facade だけの項目 501 件に、`Image` / `Pipeline` / `FullseyeEngine` / `VideoPipeline` / `MissingBackendError` / `TcpChannel` / `ModbusTcpServer` などクラス **41 個**が op として入っていた。`fullseye_search_ops("Pipeline")` がクラスを「op」として返し、LLM の検索面を汚す。 _(ja)_

Found by: `genspark_external_review` / Changed: `fullseye/mcp/catalog.py` / Gate: `test_facade_layer_lists_functions_only`, `test_search_surface_carries_no_class_names`, `test_real_facade_functions_stay_searchable` / Status: fixed

#### [PFM の既定が 8 bit 値を float 形式に書き、壊れた pipeline 設定が「成功」し、無い GPU が生の torch 文で報告されていた](hardening/pfm-default-wrote-8-bit-values-into-a-float-format.md) _(ja)_

GenSpark 第 28〜35 報(0.2.1 の仕上げに回した分)。 _(ja)_

Found by: `genspark_external_review` / Changed: `imgio.py`, `engine.py`, `api.py`, `accel.py`, `imgevolve.py`, `README.md` / Gate: `test_pfm_default_write_is_float_and_round_trips`, `test_from_dict_refuses_none_and_scalar_stages_but_keeps_the_documented_forms`, `test_device_cuda_without_a_gpu_is_explained_and_recorded`, `test_apply_with_a_ledger_op_name_points_to_op_run`, `test_accel_parity_label_carries_its_threshold`, `test_readme_intro_counts_match_the_shipped_index`, `test_has_knows_the_ledger_and_algorithm_tiers`, `test_ops_search_folds_case_and_accents`, `test_pipeline_with_an_empty_ops_string_is_refused_with_a_sentence` / Status: fixed

#### [`strict_mode()` が経路の一部しか厳密にしていなかった(+ 0.2.1 再測定の 4 件)](hardening/strict-mode-only-covered-some-of-the-guards.md) _(ja)_

GenSpark 第 55 報(0.2.1 を入れ直しての再測定、2026-09-20)。修正確認 8 件のあと、残存 8 件・新規 4 件。 _(ja)_

Found by: `genspark_external_review` / Changed: `api.py`, `opassist.py`, `imgevolve.py`, `fullseye/__main__.py`, `unified.py` / Gate: `test_strict_mode_makes_every_guard_raise`, `test_op_run_explains_the_argument_order_and_registry_ops`, `test_python_dash_m_fullseye_is_the_cli`, `test_index_names_the_difference_from_the_shipped_copy`, `test_index_default_output_never_lands_inside_an_installed_package`, `test_unified_pipeline_points_knob_tuples_to_run_pipeline` / Status: fixed

#### [大津のしきい値をビンの**中点**で取るので、背景の山を含むビンの画素が前景に入る](hardening/otsu-threshold-at-the-bin-midpoint.md) _(ja)_

値が 2 種類しかない板(背景 0.30・明部 0.90、20x20 = 400 px)で、`fullseye.apply(im, "otsu")` が **4,096 px 全部を前景**にする(期待 400)。例外も警告も出ない。 _(ja)_

Found by: `line_handshake` / Changed: `ops.py`, `accel.py`, `detect.py`, `fscript.py` / Gate: `test_a_flat_plate_gives_exactly_the_bright_box`, `test_the_three_implementations_of_otsu_agree`, `test_the_gpu_port_agrees_with_the_core_op`, `test_the_threshold_is_equivariant_under_an_affine_map`, `test_the_midpoint_spelling_is_what_the_gate_catches`, `test_segment_objects_sees_one_box_not_one_frame`, `test_the_fscript_builtin_agrees_with_the_core_op` / Status: fixed

#### [`compactness` が 1.0 で頭打ちし、長い傷を区別しなくなっていた](hardening/compactness-saturated-at-one.md) _(ja)_

幅 2 px の傷の長さを変えても、**長さ 80 以上は全部 `1.0`**。 _(ja)_

Found by: `shape_factors_closed_form` / Changed: `backends_auto.py` / Gate: `test_compactness_does_not_saturate_on_long_scratches`, `test_compactness_matches_the_closed_form_shape`, `test_the_old_squash_is_what_the_gate_catches` / Status: fixed

#### [寸法を持つ特徴が画像サイズで正規化されていて、HALCON の数と合わなかった](hardening/dimensional-features-were-normalised.md) _(ja)_

30x70 の矩形(画像 200x200)で、HALCON の画素値との倍率: _(ja)_

Found by: `shape_factors_closed_form` / Changed: `backends_auto.py`, `data/auto_specs/regions.json` / Gate: `test_area_center_is_pixels_not_a_fraction`, `test_contlength_is_the_perimeter_in_pixels`, `test_get_region_thickness_is_pixels_and_no_longer_saturates`, `test_diameter_region_is_the_max_chord_in_pixels`, `test_the_two_diameter_ops_agree`, `test_elliptic_axis_returns_ra_rb_phi_in_pixels`, `test_the_two_elliptic_axis_ops_use_the_same_angle_convention`, `test_a_bigger_image_does_not_change_a_pixel_measurement` / Status: fixed

#### [特徴が 1.0 で頭打ちし、形が違うのに同じ数を返していた(9 op)](hardening/features-saturated-at-one.md) _(ja)_

`compactness` の頭打ちを直したあと、**同じ型が他にも無いか**を機械的に探した。 「単調に形を変える列を渡して、出力が止まる op」を数える探針で 9 本出た。 _(ja)_

Found by: `shape_factors_closed_form` / Changed: `backends_auto.py` / Gate: `test_a_region_feature_responds_to_at_least_one_deformation`, `test_a_contour_feature_responds_to_at_least_one_deformation`, `test_height_width_ratio_reports_tall_objects_honestly`, `test_the_moment_features_keep_growing_on_long_shapes`, `test_the_probe_would_catch_a_squashed_feature`, `test_the_constant_ledger_names_ops_that_really_are_constant` / Status: fixed

#### [HALCON と同じ名前の形状係数が、HALCON と**別の量**を返していた](hardening/halcon-named-shape-factors.md) _(ja)_

同名を名乗る 6 本のうち、HALCON の式と一致していたのは `convexity` だけだった。 _(ja)_

Found by: `shape_factors_closed_form` / Changed: `backends_auto.py` / Gate: `test_the_op_returns_the_halcon_quantity`, `test_rectangularity_is_one_for_rectangles_whatever_the_angle`, `test_rectangularity_is_one_for_a_square`, `test_the_old_isoperimetric_formula_is_what_the_gate_catches`, `test_the_old_axis_aligned_extent_is_what_the_gate_catches`, `test_the_contour_twin_answers_the_same_question`, `test_every_same_named_shape_factor_is_either_checked_or_named`, `test_eccentricity_returns_the_three_halcon_values`, `test_eccentricity_is_one_one_zero_for_a_circle`, `test_the_old_scalar_eccentricity_is_what_the_gate_catches`, `test_the_contour_eccentricity_uses_moments_not_a_point_fit` / Status: fixed

#### [SimpleITK 由来の 3 つのしきい値 op が、兄弟 op の**補集合**を返していた](hardening/itk-threshold-ops-returned-the-dark-side.md) _(ja)_

明部ちょうど 400 px の板で: _(ja)_

Found by: `threshold_family_agreement` / Changed: `backends_r3.py` / Gate: `test_the_region_is_the_bright_side`, `test_a_global_automatic_threshold_gets_the_box_exactly`, `test_they_all_agree_with_each_other`, `test_the_complement_is_what_the_gate_catches`, `test_the_itk_convention_is_the_one_we_had_wrong` / Status: fixed

### Implementation defect

#### [可視領域が、目線より高いセルを軒並み「見えない」と返していた](hardening/dem-viewshed-self-occlusion.md) _(ja)_

平地に置いた円錐の**頂点**が、60 m 先・目線 2.0 m の開けた平地から可視 0.0。目線より高い 1541 セルの可視は **0 個**、底面の遮蔽率 0.8863(閉形式 0.5710)。独立に最小再現: 平地に高さ 10 m の柱を立てると可視 0.0、目線より低い 1 m の柱は 可視 1.0。**凸な立体の最高点は外から必ず見える**ので、幾何として誤り。 _(ja)_

Found by: `poc_stockpile_volume` / Changed: `demops.py` / Gate: `test_a_hill_taller_than_the_eye_is_visible_from_the_open`, `test_the_wall_itself_is_visible_even_though_its_far_side_is_not`, `test_a_hill_is_hidden_only_when_the_sight_line_passes_below_the_wall` / Status: fixed

#### [run_pipeline の「外した書き方」が原因の読めない例外になっていた](hardening/run-pipeline-stage-forms-fail-obscurely.md) _(ja)_

`run_pipeline(image, stages)` は `["gaussian", "otsu"]` と `[("gaussian", 0.3, 0.5), ...]` を受ける。第三者レビュー(GenSpark)が自然に書いた 3 つの形は、どれも**原因を指さない例外**で落ちた。 _(ja)_

Found by: `genspark_external_review` / Changed: `api.py` / Gate: `test_run_pipeline_accepts_dict_knobs_comma_string_and_dict_stages`, `test_run_pipeline_bad_forms_say_why` / Status: fixed

#### [Studio の実行キーが、Program に書いたばかりの編集を無視して古いパイプラインを走らせていた](hardening/studio-run-key-ignored-unapplied-edits.md) _(ja)_

GenSpark 第 8 報。Xvfb 上で Studio を起動し xdotool で操作、前後のスクリーンショットを画像解析で比べた実測: Program エディタに `gaussian (0.4, 0.5)` を打つとステータスが「● unapplied edits — Apply to run, or Reset to discard」に変わる(s8)。そこで実行キーを押しても **画面は 1 bit も変わらず**、ステータスもそのまま(s9 = s8)。報告では Ctrl+R を押していたが、Studio の実行キーは HDevelop 流の **F5 / Ctrl+Return** で、Ctrl+R は未割り当てだった —— ただし F5 を押しても同じ結果になる(下)。 _(ja)_

Found by: `genspark_external_review` / Changed: `studio.py` / Gate: `test_run_all_applies_unapplied_program_edits_first`, `test_run_all_does_not_run_the_old_pipeline_when_the_edit_does_not_parse`, `test_ctrl_r_is_an_alias_of_the_run_key` / Status: fixed

#### [pose ヘルパが、自分の出力(4×4 同次行列)を受け取れなかった](hardening/pose-helpers-could-not-take-their-own-matrix.md) _(ja)_

GenSpark 第 14 報(公開 API 955 本の一括スモークを有効引数で再検証した回)。ライブラリ自身の往復で落ちる: _(ja)_

Found by: `genspark_external_review` / Changed: `pose_quat.py` / Gate: `test_pose_helpers_accept_their_own_homogeneous_matrix`, `test_other_shapes_say_what_a_pose_is` / Status: fixed

#### [同じ段を 4 つの入口が別々に読んでいた](hardening/stage-forms-read-differently-by-four-entry-points.md) _(ja)_

GenSpark 第 53 報(0.2.0 の clone 調査、2026-09-20)。0.2.1 でも再現。 _(ja)_

Found by: `genspark_external_review` / Changed: `engine.py`, `unified.py` / Gate: `test_four_entry_points_read_the_same_stage_names`, `test_diagnose_stages_reports_a_broken_stage_instead_of_raising`, `test_engine_rejects_a_malformed_stage_with_the_shared_sentence`, `test_unified_pipeline_accepts_list_and_dict_stages` / Status: fixed

### The gate did not stand where the accident happens

#### [配布物の CLI で、help が別の入口を案内し、3 つのサブコマンドが使えなかった](hardening/cli-help-and-subcommands-broke-in-the-wheel.md) _(ja)_

GenSpark 第 6・7 報(0.2.0 を `pip install` した Linux で `fullseye` を叩いた実測)。 _(ja)_

Found by: `genspark_external_review` / Changed: `imgevolve.py`, `honest_summary.py`, `backends_color.py`, `backends_r3.py`, `backends_auto.py`, `studio.py` / Gate: `test_help_examples_use_the_installed_cli_name_when_run_as_fullseye`, `test_parity_subcommand_resets_argv_before_delegating`, `test_coverage_explains_the_missing_reference_data_instead_of_crashing`, `test_color_backend_name_check_is_fail_closed_without_the_json`, `test_registry_does_not_shrink_when_warnings_are_errors` / Status: fixed

#### [空・極小の入力が、op ごとにばらばらな生エラーで落ちていた](hardening/empty-and-tiny-inputs-raised-raw-library-errors.md) _(ja)_

GenSpark のレビュー(別ノート 3 本)を直したあと、同じ族が他に無いかを**全 op で数えた**。image / region 入力の 681 op に 7 種の退化入力 —— 空 (0,0)・1×1・2×2・1-D・inf・範囲外・RGB (H,W,3) —— を `on_error="raise"` で渡し、例外を「文に op 名か fullseye の語がある(clean)/ 無い(raw)」で分類した(走査 3 秒)。 _(ja)_

Found by: `degenerate_inputs` / Changed: `api.py`, `engine.py`, `imgevolve.py` / Gate: `test_empty_input_is_one_clean_sentence_under_raise`, `test_empty_input_is_recorded_and_falls_back_under_the_default_policy`, `test_raw_error_from_inside_an_op_gets_an_op_and_shape_note`, `test_pipeline_validate_explains_a_missing_backend` / Status: fixed

#### [sort `table` が「行のリスト」と「諸元 dict」の両方を指し、消費 op が口ごもって落ちた](hardening/table-sort-mixes-rows-and-spec-dicts.md) _(ja)_

連鎖ファザー(`tools/chain_fuzz.py --cover-all`、300 連鎖)の分類 164 件のうち、SUSPECT(契約の穴)8 件が同じ形だった: `vol_edge_probe` の返り(**行のリスト**)が pool の `table` に入り、次の op が `optical_camera` / `lens_spec` / `light_spec` の**dict**を待つ席に受け取る。`camera["K"]` は `TypeError: list indices must be integers or slices, not str`、`lens.get(...)` は `AttributeError: 'list' object has no attribute 'get'` —— 例外は出るが、どの op がどの入力を拒んだのかを言わない。型語彙 `table` は台帳全体で 207 か所に使われ、産む側は list-of-rows(`vol_edge_probe` / `region_props` / `glass_catalog` / `defect_dataset` / `copy_move_regions`)と dict(諸元・統計・設計)の両方がある。 _(ja)_

Found by: `tools/chain_fuzz.py` / Changed: `optscene.py`, `fourierdesc.py`, `tools/chain_fuzz.py`, `ops1d.py`, `opsoptics.py` / Gate: `test_table_consumers_refuse_a_list_of_rows_with_the_op_name`, `test_a_wrong_kind_of_spec_is_refused_too`, `test_peak_subbin_and_register_light_ledger_out_match_what_they_return`, `test_nonfinite_allowlist_additions_are_documented_and_really_nonfinite`, `test_the_eight_suspect_replays_are_white_now` / Status: fixed

#### [機能ゲートが `match` ソートを知らず、正しい op を「実装されていない」と数えていた](hardening/functional-gate-did-not-know-the-match-sort.md) _(ja)_

HALCON 対応の見出しが **979 から 977 に減った**。減らしたのは `eccentricity` / `eccentricity_xld` を HALCON の 3 値に直した変更 —— 正しくしたのに **対応数が減った**。 _(ja)_

Found by: `shape_factors_closed_form` / Changed: `verify_auto.py` / Gate: `test_the_functional_gate_accepts_a_match_sort_vector`, `test_the_functional_gate_still_rejects_a_wrong_shape`, `test_the_headline_equals_the_union_of_its_parts` / Status: fixed

### Present but unreachable

#### [空間彫刻の姿勢ヘルパが引けず、同名の別規約を掴むと例外なく空の hull が返った](hardening/carve-look-at-unreachable-and-silent.md) _(ja)_

`carve` / `synthesize_silhouette` が要求する姿勢は OpenCV 規約(`X_cam = R X + t`、**+Z 前方**)。それを作る `visualhull.look_at` は `fs.` / `fs.op.` / `fs.ledger.` の**どこからも引けず**、`op_find("look")` も **0 件**。一方、公開層で `look_at` の名を持つのは `render3d` の gluLookAt 版(4x4・**−Z 前方**)。その `M[:3,:3], M[:3,3]` を渡すと全点がカメラ後方に落ち、**例外を出さずに空のシルエット → 空の hull** が返る。独立に再現(立方体 8000 点で 正しい姿勢なら前景 2240 px、gluLookAt 由来で 0 px)。 _(ja)_

Found by: `poc_livestock_body_volume` / Changed: `visualhull.py`, `ops3d.py`, `render3d.py` / Gate: `test_carve_look_at_is_reachable_from_the_public_tiers`, `test_the_public_look_at_is_the_other_convention_and_says_so` / Status: fixed

#### [op_find が和文の複数語クエリに構造的に盲目だった](hardening/op-find-blind-to-japanese-queries.md) _(ja)_

副画素重心つきで点状目標の座標を返す 2-D op は `star_detect` だけなのに、`op_find("小さい目標 検出")` / `("スポット 検出")` / `("漂流 捜索")` は**いずれも 0 件**。英語の "point target detection" でようやく 20 件中 14 番目。名前が天文に閉じているせいだと思って docstring に説明語を足したが、**それでも 0 件のままだった**。 _(ja)_

Found by: `poc_search_sweep_width` / Changed: `opassist.py`, `astrostack.py` / Gate: `test_op_find_answers_japanese_queries` / Status: fixed

#### [「モーメント不変量」が 2 つの族にあり、名前だけで選ぶと落ちる](hardening/moment-invariants-two-families-same-name.md) _(ja)_

回転不変性を監査する PoC を書くとき、「回転不変なモーメント」を探して `moment_invariants` を見つけ、`(H,W)` の二値領域を渡した。返ってきたのは _(ja)_

Found by: `poc_rotation_invariance_audit` / Changed: `moments3d.py` / Gate: `test_the_three_d_moment_op_points_at_the_two_d_region_family` / Status: fixed

#### [「unknown operator」が backend 不足を隠し、存在しない CLI を案内していた](hardening/unknown-operator-hides-missing-backend.md) _(ja)_

第三者(GenSpark)が 0.2.0 を **core**(`pip install fullseye`、693 op)と **all**(`fullseye[all]`、899 op)の 2 環境で使い込んだ。core で `fullseye.apply(img, "sk_canny")` を呼ぶと _(ja)_

Found by: `genspark_external_review` / Changed: `api.py`, `ops.py`, `imgevolve.py`, `fullseye/data/OP_INDEX.json` / Gate: `test_missing_backend_error_is_a_keyerror_and_names_the_missing_extra`, `test_unknown_operator_message_names_a_real_cli_and_op_find`, `test_op_index_rows_carry_module_and_requires`, `test_optional_deps_table_matches_pyproject_extras` / Status: fixed

#### [台帳が黙って古い事象を捨て、studio の `--help` が abort し、facade に import の道具が漏れていた](hardening/ledger-evicted-silently-and-studio-help-aborted.md) _(ja)_

GenSpark 第 43・44・50 報(2026-09-20)。 _(ja)_

Found by: `genspark_external_review` / Changed: `backend_safe.py`, `api.py`, `studio.py`, `fullseye/__init__.py` / Gate: `test_fallback_ring_counts_what_it_evicts`, `test_studio_help_and_version_answer_without_qt`, `test_studio_without_a_display_stops_with_a_sentence_not_an_abort`, `test_facade_namespace_has_no_import_tools` / Status: fixed

#### [n-ary op は呼べるのに一覧に無く、つまみ a / b が効くかは文でしか分からず、CLI からは 2 入力の op を呼べなかった](hardening/nary-ops-unlisted-and-knobs-unstated.md) _(ja)_

GenSpark 第 18〜20 報の統合チケット(N60 + I1)。 _(ja)_

Found by: `genspark_external_review` / Changed: `api.py`, `imgevolve.py`, `tools/gen_mcp_data.py`, `pyproject.toml` / Gate: `test_op_names_include_nary_adds_exactly_the_nary_tier`, `test_every_list_ops_row_carries_a_knobs_summary`, `test_the_shipped_knob_table_equals_the_docs_copy`, `test_cli_apply_input2_runs_an_nary_op`, `test_cli_index_prints_the_four_tiers` / Status: fixed

#### [`Image` が 0 次元のスカラーになり、入力不足が生の TypeError で、`op_find` の doc が空だった](hardening/wrappers-were-scalars-and-hints-were-raw-type-errors.md) _(ja)_

GenSpark 第 33〜55 報の残り候補 10 件を現 master で再現(2026-09-20)。本物 3 件・改善 3 件・非再現 2 件。 _(ja)_

Found by: `genspark_external_review` / Changed: `api.py`, `fullseye/jsonio.py`, `opassist.py`, `imgevolve.py`, `graphengine.py`, `metriccontract.py` / Gate: `test_apply_and_run_pipeline_and_to_json_unwrap_the_image_wrapper`, `test_op_run_names_the_missing_input_instead_of_a_raw_type_error`, `test_algo_run_without_seq_is_refused_with_the_example`, `test_op_find_doc_is_filled_from_the_op_note`, `test_graph_add_defaults_to_the_external_input_and_empty_graph_is_identity` / Status: fixed

### Documentation hole (one-way reference, stale number)

#### [ベクトル版 refract が、per-ray 版 refract_rays の存在に触れていなかった](hardening/refract-one-way-reference.md) _(ja)_

`refract` の docstring は「(N,3) バッチも通るが **1 本でも TIR ならバッチ全体が `None`**。バッチで使うなら呼び出し側で **1 本ずつ回すこと**」とだけ書いていた。ところが**光線ごとに TIR を判定して (方向, マスク) を返す `refract_rays` が既にある**(`refract_rays` 側からの参照は在った)。 _(ja)_

Found by: `poc_multibeam_bathymetry` / Changed: `match3d.py` / Gate: `test_refract_points_at_the_per_ray_version_it_used_to_hide` / Status: fixed
