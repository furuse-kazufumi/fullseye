---
id: inputs-without-a-conversion-were-not-refused
date: 2026-09-19
found_by: genspark_external_review
kind: silent-wrong
severity: high
where: [api.py, ops.py]
ops: [otsu, sobel_amp]
gate: [test_non_numeric_arrays_are_refused_under_every_policy, test_complex_input_to_a_real_op_is_refused_not_silently_realised, test_otsu_all_nan_is_an_explicit_error_not_a_numpy_runtime_warning, test_nary_shape_mismatch_says_what_is_needed, test_op_objects_pickle_by_name]
status: fixed
---

# 変換の定義が無い入力が、黙って「それらしい」出力になっていた

## 症状

第三者レビュー(GenSpark、0.2.0、core / all の 2 環境)が dtype と形を網羅して見つけた 4 件。共通点は**例外にならず、値が返る**こと。

| 入力 | 0.2.0 の挙動 |
|---|---|
| 文字列配列 `np.array([["a"]*4]*4)` → `sobel_amp` | **無警告で全 0**(この木では `np.clip` の生の UFuncTypeError) |
| 複素配列 → `sobel_amp` | numpy の `ComplexWarning` 1 つで**虚部が捨てられ**、実部だけの結果と一致。`on_error="raise"` でも止まらない |
| 全 NaN → `otsu` | `RuntimeWarning: All-NaN slice encountered` ×2 を出して**全 0**。`raise` でも RuntimeWarning は捕まらない |
| `add_image` に (32,32) と (32,16) | 既定方針では台帳に numpy の broadcast エラーが残り、**第 1 入力がそのまま返る**。形だけ見た利用者には「(32,32) で成功」に見えた |

加えて、`Op` オブジェクトは `fn` が `backend_safe._safe` のクロージャなので pickle できず、multiprocessing / joblib に Op を渡すと `PicklingError`(名前を持つ `Pipeline` は通る、という非対称)。

## なぜ門が通したか

`on_error` の 3 方針は「**op が失敗したとき**、sort として妥当な値へ落とすか止めるか」の選択で、その入口 `_contract_dtype` は **uint8 → /255 のように変換が定義された dtype** だけを扱い、「float / complex / non-array: unchanged」と書いて通していた。文字列は clip で、複素は `np.asarray(v, np.float64)` で、全 NaN は `nanmin` で、それぞれ **numpy が先に何かを返してしまう**ので、fullseye の門に届く前に「値」になる。入力の dtype の探針は uint8 / bool / float だけだった。

形状不一致は台帳には正しく残っていた(`fullseye.fallbacks()` に broadcast エラー)。**通知が「形」に出ない**ことが問題で、返り値の shape が第 1 入力と同じなので気づけない。

## 直し

1. **`api._reject_untyped(v, op_or_sort)`** —— 数値として読めない配列(str / bytes / object / datetime)と、**実数 sort(image / region / volume / color)への複素配列**は、**方針に依らず** `TypeError` で止める。理由: 落とし先が無い。文字列を「全 0 の画像」にするのは fallback ではなく嘘、複素の |z| / Re / arg は呼ぶ側の判断。`apply` / `run_pipeline`(CPU・GPU)/ n-ary の各入力、`coerce` より**前**に立つ。`cimage` の op と `in_sort` any(`identity`)は複素をそのまま受ける。
2. **`otsu`** —— 有限の画素が無ければ `ValueError`(方針 fallback では台帳に記録して region の既定値、raise でそのまま止まる。numpy の RuntimeWarning は出ない)。定数画像は「0 なら全部背景、0 より大きければ全部前景」を docstring に明記(`docs/op_blank_frame.json` の測定と一致、門で pin)。
3. **n-ary の形状不一致** —— ラスタ同士の入力の形が違えば、broadcast エラーの代わりに「N 個の入力は同じ形で / crop・pad・resize を先に / fallback では第 1 入力がそのまま返る」を文で言う `ValueError`(方針はこれまでどおり: raise で止まり、fallback で台帳 + 第 1 入力)。
4. **`Op.__reduce__`** —— 名前で pickle し、復元先の環境の登録で引く。backend が無い環境で戻すと `KeyError`(不足 extra の案内つき)。黙って別の実装にはならない。

門: 3 方針すべてで文字列が TypeError / 複素は `warnings.simplefilter("error")` 下で ComplexWarning も出ない / 全 NaN の otsu で numpy の RuntimeWarning が出ない + 台帳に理由が残る / 形状不一致の文 / Op の pickle 往復が同一オブジェクト。
