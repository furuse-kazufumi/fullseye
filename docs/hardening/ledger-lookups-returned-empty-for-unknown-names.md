---
id: ledger-lookups-returned-empty-for-unknown-names
date: 2026-09-20
found_by: genspark_external_review
kind: silent-wrong
severity: medium
where: [opassist.py, dsp.py, api.py]
ops: [cv_cc_count, xsk_random_walker]
gate: [test_producers_and_consumers_refuse_unknown_sorts_and_op_names, test_presets_refuse_unknown_ops_and_are_empty_for_known_ops_without_presets, test_write_wav_path_is_not_a_data_input_in_the_ledger, test_no_ignored_exception_leaks_to_stderr_when_write_wav_is_misused, test_list_ops_rows_expose_the_native_guard, test_empty_input_contract_is_uniform_across_ops, test_every_shared_alias_resolves_by_rule_not_by_registration_order, test_list_ops_rows_name_their_alias_peers, test_list_ops_sort_and_search_fold_case_and_accents, test_op_run_refuses_to_call_with_a_none_sample_and_names_the_sort, test_non_array_images_are_type_errors_regardless_of_policy, test_data_range_of_without_arrays_is_a_contract_error, test_lazy_torch_import_error_says_whether_torch_is_installed, test_list_ops_unknown_sort_is_refused_and_lists_the_known_ones]
status: fixed
---

# 台帳の引き方が未知の名前に黙って空を返し、write_wav の path が台帳でデータ扱いされていた

## 症状

GenSpark 第 15〜27 報(N67 / N68 / N69 / N71、N84 / N85 / N87、N92 / N94 / N95 / N97、および N72 / N73 / N74 / N80 / N88 / N89 / N90 / N91 / N93 / N96 / N99 / N100)。

- **N68**: `op_producers("gaussian")` / `op_consumers("laplace")` が `[]`。120 op を叩いて全部空。引数は **型名(sort)** であって op 名ではないが、空は「そういう型は無い」とも「産む op が無い」とも読めない。
- **N69**: `op_presets("no_such_op_xyz")` が `{}`。「プリセットが無い op」と「存在しない op」が同じ答え。
- **N71**: `op_run("write_wav")` を叩くと標準エラーに `Exception ignored in Wave_write.__del__ … no attribute '_file'` が呼び出しごとに出る。本当の原因(`OSError: Invalid argument: '[0. 0.0158 …'`)は、台帳の `in=["signal"]` が **第 1 引数 `path` に signal を割り当て**、デモの配列をファイル名として `wave.open(str(array))` していたこと。`read_wav(None)` は `'None'` というファイルを探していた。`_require_finite(None)` は「1 non-finite sample」と言っていた。
- **N67**: 4 op(`cv_cc_count` / `xsitk_minmax_curv_flow` / `xsk3_h_minima` / `xsk_random_walker`)のネイティブ側のクラッシュ・ハングは入口の関門(`ops.NATIVE_CRASHES_ON_DEGENERATE`)が防いでいる —— GenSpark 自身も subprocess 隔離 20 ランで SIGSEGV 0・ハング 0 を確認し「低」に格下げ —— が、その事実が ops.py の中にしか無く、registry を使う側から見えなかった。

## なぜ門が通したか

- `producers` / `consumers` は「空文字でない str」だけを検査し、既知の型の集合を持っていなかった。テストは `producers("no_such_sort") == []` を **正しい挙動として pin** していた。
- `presets` は `PRESETS.get(op_name, {})` で、台帳に照会していなかった(`assist` / `run` / `param_spec` は照会して ValueError にしていた —— 同じ族で 1 本だけ違った、[[feedback_same_bug_class_recurs_check_siblings]])。
- `param_spec` は「第 1 引数から順に、宣言 in 型の本数だけをデータ入力」と決め打ちしていた。読む側(`read_wav(path)`、in=["file"])は正しく、書く側(`write_wav(path, x)`、in=["signal"])だけ食い違う。台帳に「file を出す op」は 1 本しか無く、探針が当たらなかった。
- stdlib の `wave.open(str, "wb")` は open に失敗すると半端な `Wave_write` が残り、その `__del__` が例外を吐く(Python 3.11 / 3.12 とも)。

## 直し

1. **`known_sorts()`**(facade `op_sorts()`)= 台帳の in / out に出る型名の一覧。`producers` / `consumers` は未知の型を **ValueError**、op 名を渡されたら「それは op 名で、型は `op_assist(name)['in'/'out']`」と言う。既知の型で産む op が無い空だけが空。
2. **`presets`** は台帳に無い op を `assist` と同じ ValueError。台帳にある op の `{}` は「意図して無し」(プリセットは実在の規格値・材質が意味を持つ 13 op にだけある)。
3. **`param_spec`**: パス名の引数(`path` / `filename` / …)は宣言 sort が `"file"` のときだけデータ。それ以外は書き先のパラメータで、データ型は次の引数へ送る。`write_wav` は `path`(text, required)+ `x`(data, signal)+ `rate` になり、`op_run("write_wav")` は「path is None — pass a file path」の 1 文で止まる(サンプルは書き先を発明しない)。
4. **`dsp`**: `_require_path` が None / 配列を str にせず TypeError(取り違えには「the signal is the second argument」)。`write_wav` はファイルを自分で開いて `wave.open(fileobj)`(半端な Wave_write を作らない)。`_require_finite(None)` は TypeError。
5. **`list_ops()`** の registry 行に **`native_guard`**(関門の理由の文、無ければ None)。
6. **N84(第 20 報)**: 同じ HALCON 別名を複数 op が名乗る(387 別名中 68。うち 66 は別名が実在 op 名と同じで**完全一致が勝つ**、残り 2 は `_ALIAS_CANONICAL` の明示行)。規則は `find_op` に元からあり曖昧ではないが、行から見えなかった —— registry 行に **`halcon_peers`**(同じ別名を名乗る他の op)。門: 正規 op の無い衝突は必ず明示行を持つ(登録順で決まる別名をゼロに固定)。
7. **N85(第 20 報)**: `list_ops(sort="IMAGE")` が 0 行、`search="ötsu"` が 0 行 —— sort / search とも NFKD + casefold で畳む。
8. **N87(第 20 報)**: `op_run` が種を作れない型(mesh / lab / matrix)に None を渡し IndexError / AttributeError / AxisError が 11 op で利用者に届いていた(実測 1053 op 中)。呼ばずに「no built-in sample for input sort 'lab' — pass the input(s) explicitly」。自動の数値サンプル(1.0)が座標を要する引数に合わない `scene_box` 等は「the built-in sample values for ['center_mm', …] do not fit — pass them explicitly」に翻訳。データ引数が署名の先頭に無い op(`write_wav(path, x)`)は名前で渡す。第 23 報の全数走査(1,024 op)で IndexError 14・AttributeError 2(N93 `covers_sensor` / `light_wavelengths` = table の種が None)・KeyError 1 は全部この経路。
9. **N97(第 26 報、高)**: `apply("abc", "gaussian")` が既定の fallback 方針で **"abc" をそのまま返していた** —— `_reject_untyped` は ndarray しか見ず、素の str / dict / スカラーは素通り(raise 方針では別の門が止めていた)。raster を取る op には配列にしてから同じ検査を掛け、0 次元(スカラー)も方針に依らず TypeError。dict を取る sort(contour 等)は従来どおり。
10. **N92(第 23 報)**: `data_range_of()` を配列なしで呼ぶと空集合の pop(KeyError)/ 0-d の float()(TypeError)—— `MetricContractError("needs at least one array")`。
11. **N94(第 24・25 報)**: torch が入っているのに「optional 'torch' backend — install with」だけが出た。`torch_lazy` は find_spec で在ると判定しても `import torch` が失敗すると同じ文を出していた —— 「installed but importing it failed: <型>: <文>」か「not installed」を添える(GenSpark 環境の 30 op はこの経路 = torch の import が落ちている)。
12. **N95(第 24 報)**: `list_ops(sort="nonsense")` が黙って 0 行 —— 未知の sort は既知一覧つきの ValueError(空文字は従来どおり全件)。
13. **N100(第 27 報)**: `imgio.colorize_labels` が float 画像を `astype(int)` で全 0 にして真っ黒を返していた —— float は整数値のときだけ受け、それ以外は ValueError。

**同じ 2 報で設計・直し済みとして分けたもの**:

| 指摘 | 判断 | 理由 |
|---|---|---|
| N66 `imgevolve.py has …` の壊れた案内文 | 0.2.0 のみ | 第 1 陣で `fullseye has` + `op_find` の文に直し済み(master)。0.2.1 で配布物に入る |
| N72 0 要素入力で生の numpy 文(`zero-size array to reduction operation fmin`) | 0.2.0 のみ | 第 2 陣の `_check_input_empty` が全 op で「op 'x': empty input (shape …)」の 1 文に置換済み |
| N73 退化入力で「例外」と「スカラー 0」が混在 | 設計 | master では方針ごとに一様: `on_error="raise"` は全 op が同じ 1 文の ValueError、既定の fallback は全 op が台帳に `empty input` を記録して **sort の既定値**(計数 op は 0、画像 op は同形の 0)を返す。返り値の形は sort ごとに違うのが契約で、機械判定の信号は台帳(`fullseye.fallbacks()`) |
| N67 危険情報の可視性 | 直した(上の 5) | 関門そのものは有効(GenSpark も 20 ランで確認) |
| N70 registry の docstring 被覆 45 %(`Op.doc` > 15 文字が 422 / 931) | 設計 | 説明の正本は `docs/ops/**/*.md`(2,092 枚、全 op)。`Op.doc` は 1 行の要約で、無い op はノートを読む(第 1 陣の表と同じ) |
| `DROPPED_DUPLICATES` に laplace 等 4 件があるのに registry に現れる | 設計 | 同名の **二重登録の後勝ち分を捨てた記録**で、op は残る(コアの fallback 版が勝つ意図的な上書き。`tests/test_opdocs.py` が「ちょうどこの集合」を pin) |
| N74(第 17 報)`edges_color_sub_pix` が `unsupported format string passed to dict.format` | 非不具合 | 出力型は **contour**(`{'cs': [...], 'shape': (H, W)}` の dict)で、master でも 0.2.0 でも例外は出ない。その文は dict を `'{:.3f}'.format()` に通した側(集計スクリプト)で出る。`list_ops()` の `out_sort` が contour と言っている |
| N68 の訂正「台帳側 80 op も空」(第 17 報) | 同根 | 引数に op 名を渡している(型名が要る)。上の 1 で ValueError になり「それは op 名」と言う |
| N72 の根本原因は `_norm` / `signed01`(第 17 報の推定) | 該当せず | master は入口の `_check_input_empty` が op の中に入る前に止める。0.2.0 では止めていなかったので推定は 0.2.0 の挙動としては妥当 |
| N84 `binary_threshold` に Otsu / Li / Yen が同居(第 20 報) | 設計 | `binary_threshold` という op が実在するので完全一致が走る(Otsu の固定閾値版ではなく本家の二値化)。cv_otsu / sk_li / sk_yen が同じ HALCON 名を名乗るのは「HALCON のこの演算に相当する実装」という台帳の意味で、別名を分割しない。行の `halcon_peers` で全部見える |
| N86 `op_find` が n-ary を索引しない(第 20 報) | 0.2.0 のみ | 第 3 陣で nary 段を検索対象に |
| N88 `fullseye.engine` が無い(第 20 報 → 第 22 報で撤回) | 設計 | エンジンは `fullseye.FullseyeEngine` / トップレベル `engine.py` |
| N89 台帳の引数 `doc` が None(第 21 報) | 次回候補(doc-hole) | 実測 4,616 引数中 3,848(83 %)が None。`_doc_line` は docstring の「name: 説明」行しか拾わない。書式を決めて埋める回を別に立てる(op 1,053 本分) |
| N80 `run_pipeline([A, B], ["add_image"])`(第 19・22 報) | 次回候補 | 先頭段だけ n-ary を受ける拡張(上の表と同じ) |
| N90 `write_wav` に配列(第 23 報) | 直し済み(上の 4) | `_require_path` の TypeError |
| N91 `observe_surface()` が 2 GB 制限下で MemoryError(第 23 報) | 設計 | 既定値のフル合成(256×256×3、手元で 108 s・ピーク 1.4 GB)。退化入力ではなく**重い正規の計算**で、台帳の `op_run` は「押せば動く」の範囲外。走らせる前の見積りは次回候補(サイズを返す `estimate` を op に添える案) |
| N96 `register_fpfh` の device が非公開(第 25 報) | 該当せず | master の署名は `device="cpu"` を持ち `param_spec` も 15 引数目に出す(0.2.0 の署名との差) |
| N99 `from_ops(["gaussian","otsu"])` の段名が壊れる(第 27 報) | 0.2.0 のみ | 第 6 陣で `from_ops` がリストを受ける(test_engine_instance_load) |
| N98 `backend_safe.region01("abc")` が () を返す(第 26 報) | 設計(内部) | 公開 API ではなく guard の内側の補助。入口(N97)で止まる |
| N68 の裏返し「台帳 op なら非空か」 | 確認済み | `producers("normalmap")` は `tangent_field` / `micro_normals` を返す(既存テスト) |
