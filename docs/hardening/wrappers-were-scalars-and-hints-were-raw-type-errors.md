---
id: wrappers-were-scalars-and-hints-were-raw-type-errors
date: 2026-09-20
found_by: genspark_external_review
kind: discoverability
severity: low
where: [api.py, fullseye/jsonio.py, opassist.py, imgevolve.py, graphengine.py, metriccontract.py]
ops: [gaussian, blend_mode]
gate: [test_apply_and_run_pipeline_and_to_json_unwrap_the_image_wrapper, test_op_run_names_the_missing_input_instead_of_a_raw_type_error, test_algo_run_without_seq_is_refused_with_the_example, test_op_find_doc_is_filled_from_the_op_note, test_graph_add_defaults_to_the_external_input_and_empty_graph_is_identity]
status: fixed
---

# `Image` が 0 次元のスカラーになり、入力不足が生の TypeError で、`op_find` の doc が空だった

## 症状

GenSpark 第 33〜55 報の残り候補 10 件を現 master で再現(2026-09-20)。本物 3 件・改善 3 件・非再現 2 件。

- **N188(再現)**: `apply(fullseye.Image(img), "gaussian")` が「expects a image array with at least one dimension, got a
  scalar Image」。`np.asarray(Image)` が 0 次元 object 配列になる。`to_json(Image, "image")` も「must be 2-D, got shape ()」(N171)。
- **N122(再現)**: `op_run("blend_mode", rgb)`(top 無し)が Python の生の「missing 1 required positional argument: 'top'」。
  0 個のときは種を作って言うのに、1 個以上のときは検査が無かった。
- **N187(再現、別症状)**: `fullseye algo run quicksort` が `--seq` 無しで空列をソートして `[]` を印字し rc 0 —— 無言の成功。
- **N119 / N162 / N178(一部再現)**: `op_find("gaussian")[0]["doc"]` が空。registry の `Op.doc` は 931 op 中 422 にしか無く、
  正本(ノート)を find が見ていなかった。`exact` / `total` は無い(list を返す設計、要約が要るなら別関数)。
- **N167 / N180(非再現 → 改善)**: `FullseyeGraph.add` の docstring は在り、空グラフの `run` は内部エラーでなく入力を返す。
  ただし 1 入力の先頭ノードにも `inputs` が必須だった。
- **非再現**: N183 `blend_mode` のモード検証順(型 → 形 → モードの順は docstring どおり、誤導ではない)/ N152 torch / skimage の
  非推奨警告(`-W default` で 0 件、レビュアー環境の版の問題)/ N184 `attempt*` の docstring は在る(`attempt_all` を補った)/
  N165 bench の SIGKILL は 2 GB 容器の問題(help に必要メモリの目安)。

## なぜ門が通したか

`Image` は unified 側の器で、facade の入口の門は ndarray と素の値しか想定していなかった。台帳の入力検査は「0 個」だけを
見ていた。`algo run` は「空列も列」として通る書き方だった。`op_find` の門は「引ける」ことを問い「doc がある」ことを問わなかった。

## 直し

1. `api._unwrap_image`: `apply` / `run_pipeline` の入口と `jsonio.to_jsonable` で `Image` を `.array` に剥がす(型名で判定、
   unified を api から import しない)。
2. `opassist.run`: 必須のデータ引数が位置でも名前でも来ていなければ「missing input(s) top (rgb) — this op takes base, top:
   op_run('blend_mode', <rgb>, <rgb>)」。
3. `fullseye algo run`: `--seq` 無しは「run needs --seq … e.g. fullseye algo run quicksort --seq 3,1,2」で rc 2。
4. `opassist.find`: registry op の doc が空ならノート(docs/ops、wheel では op_help HTML)の最初の散文 1 行。
5. `FullseyeGraph.add(inputs="$in")` を既定に、`run` の docstring に空グラフの振る舞い。`attempt_all` の docstring、`bench` の help。
