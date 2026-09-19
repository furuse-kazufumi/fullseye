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

**15 findings (15 fixed), from 10 PoCs.**

## By kind

| Kind | Findings | Fixed |
|---|---:|---:|
| Silently wrong (no exception) | 5 | 5 |
| Implementation defect | 3 | 3 |
| The gate did not stand where the accident happens | 2 | 2 |
| Present but unreachable | 4 | 4 |
| Documentation hole (one-way reference, stale number) | 1 | 1 |

## By the PoC that found it

| PoC | Findings |
|---|---:|
| [`genspark_external_review`](../examples/genspark_external_review.py) | 5 |
| [`degenerate_inputs`](../examples/degenerate_inputs.py) | 2 |
| [`poc_geodetic_height_frames`](../examples/poc_geodetic_height_frames.py) | 1 |
| [`poc_livestock_body_volume`](../examples/poc_livestock_body_volume.py) | 1 |
| [`poc_multibeam_bathymetry`](../examples/poc_multibeam_bathymetry.py) | 1 |
| [`poc_print_registration`](../examples/poc_print_registration.py) | 1 |
| [`poc_rotation_invariance_audit`](../examples/poc_rotation_invariance_audit.py) | 1 |
| [`poc_search_sweep_width`](../examples/poc_search_sweep_width.py) | 1 |
| [`poc_stockpile_volume`](../examples/poc_stockpile_volume.py) | 1 |
| [`poc_thermal_radiometry`](../examples/poc_thermal_radiometry.py) | 1 |

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

### The gate did not stand where the accident happens

#### [配布物の CLI で、help が別の入口を案内し、3 つのサブコマンドが使えなかった](hardening/cli-help-and-subcommands-broke-in-the-wheel.md) _(ja)_

GenSpark 第 6・7 報(0.2.0 を `pip install` した Linux で `fullseye` を叩いた実測)。 _(ja)_

Found by: `genspark_external_review` / Changed: `imgevolve.py`, `honest_summary.py`, `backends_color.py`, `backends_r3.py`, `backends_auto.py`, `studio.py` / Gate: `test_help_examples_use_the_installed_cli_name_when_run_as_fullseye`, `test_parity_subcommand_resets_argv_before_delegating`, `test_coverage_explains_the_missing_reference_data_instead_of_crashing`, `test_color_backend_name_check_is_fail_closed_without_the_json`, `test_registry_does_not_shrink_when_warnings_are_errors` / Status: fixed

#### [空・極小の入力が、op ごとにばらばらな生エラーで落ちていた](hardening/empty-and-tiny-inputs-raised-raw-library-errors.md) _(ja)_

GenSpark のレビュー(別ノート 3 本)を直したあと、同じ族が他に無いかを**全 op で数えた**。image / region 入力の 681 op に 7 種の退化入力 —— 空 (0,0)・1×1・2×2・1-D・inf・範囲外・RGB (H,W,3) —— を `on_error="raise"` で渡し、例外を「文に op 名か fullseye の語がある(clean)/ 無い(raw)」で分類した(走査 3 秒)。 _(ja)_

Found by: `degenerate_inputs` / Changed: `api.py`, `engine.py`, `imgevolve.py` / Gate: `test_empty_input_is_one_clean_sentence_under_raise`, `test_empty_input_is_recorded_and_falls_back_under_the_default_policy`, `test_raw_error_from_inside_an_op_gets_an_op_and_shape_note`, `test_pipeline_validate_explains_a_missing_backend` / Status: fixed

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

### Documentation hole (one-way reference, stale number)

#### [ベクトル版 refract が、per-ray 版 refract_rays の存在に触れていなかった](hardening/refract-one-way-reference.md) _(ja)_

`refract` の docstring は「(N,3) バッチも通るが **1 本でも TIR ならバッチ全体が `None`**。バッチで使うなら呼び出し側で **1 本ずつ回すこと**」とだけ書いていた。ところが**光線ごとに TIR を判定して (方向, マスク) を返す `refract_rays` が既にある**(`refract_rays` 側からの参照は在った)。 _(ja)_

Found by: `poc_multibeam_bathymetry` / Changed: `match3d.py` / Gate: `test_refract_points_at_the_per_ray_version_it_used_to_hide` / Status: fixed
