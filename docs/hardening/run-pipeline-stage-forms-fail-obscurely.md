---
id: run-pipeline-stage-forms-fail-obscurely
date: 2026-09-19
found_by: genspark_external_review
kind: implementation-bug
severity: medium
where: [api.py]
ops: [gaussian, sobel_amp, otsu]
gate: [test_run_pipeline_accepts_dict_knobs_comma_string_and_dict_stages, test_run_pipeline_bad_forms_say_why]
status: fixed
---

# run_pipeline の「外した書き方」が原因の読めない例外になっていた

## 症状

`run_pipeline(image, stages)` は `["gaussian", "otsu"]` と `[("gaussian", 0.3, 0.5), ...]` を受ける。第三者レビュー(GenSpark)が自然に書いた 3 つの形は、どれも**原因を指さない例外**で落ちた。

| 書いたもの | 出た例外 |
|---|---|
| `[("gaussian", {}), ("sobel_amp", {})]`(`apply` の a/b を kwargs で渡す流儀の類推) | `TypeError: float() argument must be a string or a real number, not 'dict'` |
| `"gaussian,sobel_amp,otsu"`(CLI `fullseye pipeline` と同じカンマ区切り) | `KeyError: unknown operator 'g'` —— 文字列を 1 文字ずつ op 名として引いていた |
| `run_pipeline(stages, image)`(引数の順を逆に) | `ValueError: The truth value of an array with more than one element is ambiguous` |

## なぜ門が通したか

正規化は `(list(st) + [a, b])[:3]` → `float(sa)` の 2 行で、**受ける形を列挙していない**。列挙が無いので「外した形」を検出する場所が無く、外れは最初に触る numpy / float() の例外になる。テストは正しい 2 形だけを回していた([[feedback_one_probe_input_is_not_coverage]] の入力形版 —— 探針が正しい書き方 2 つでは、間違った書き方の出口を一度も踏まない)。

## 直し

`api._normalise_stages(image, stages, a, b)` に**受ける形を列挙**し、それ以外は**何が要るか**を文で言う `TypeError` にした。

受ける形(全部同じ `[(name, a, b), ...]` に落ちる): カンマ区切り文字列 / 名前のリスト / `(name)` `(name, a)` `(name, a, b)` / `(name, {"a": .., "b": ..})` / Studio の保存形式と同じ `{"op": .., "a": .., "b": ..}`(`name` キーも可)。

言う内容: 引数が逆(第 2 引数が ndarray、または第 1 引数が文字列・名前のリスト)/ 知らないノブ名(`sigma` など —— op は a と b しか持たない)/ ノブが数でない / 段が名前で始まらない。op 名の間違いは従来どおり `KeyError`(語として引くので `'g'` にはならない)。

**変えていないこと**: 正しい 2 形の結果はビット一致(門で `np.array_equal`)。空の stages は従来どおり入力をそのまま返す(0 段の pipeline は恒等)。
