---
id: empty-and-tiny-inputs-raised-raw-library-errors
date: 2026-09-19
found_by: degenerate_inputs
kind: gate-gap
severity: medium
where: [api.py, engine.py, imgevolve.py]
ops: [gaussian, otsu, tophat, fft_image, lowpass, structure_tensor_orientation]
gate: [test_empty_input_is_one_clean_sentence_under_raise, test_empty_input_is_recorded_and_falls_back_under_the_default_policy, test_raw_error_from_inside_an_op_gets_an_op_and_shape_note, test_pipeline_validate_explains_a_missing_backend]
status: fixed
---

# 空・極小の入力が、op ごとにばらばらな生エラーで落ちていた

## 症状

GenSpark のレビュー(別ノート 3 本)を直したあと、同じ族が他に無いかを**全 op で数えた**。image / region 入力の 681 op に 7 種の退化入力 —— 空 (0,0)・1×1・2×2・1-D・inf・範囲外・RGB (H,W,3) —— を `on_error="raise"` で渡し、例外を「文に op 名か fullseye の語がある(clean)/ 無い(raw)」で分類した(走査 3 秒)。

| 入力 | ok | clean | raw / other | 内訳 |
|---|---|---|---|---|
| 空 (0,0) | 410 | 5 | **266** | 49 群: numpy の `zero-size array to reduction`(70)、OpenCV の assert(40)、skimage `cannot be an empty array`(31)、FFT `data points (0)`(11)、`ZeroDivisionError`(7)、`'NoneType' object has no attribute 'astype'`(4)… |
| 1×1 | 639 | 0 | 42 | kornia `Padding size should be less than the corresponding input`(9)、numpy `Shape of array too small to calculate a numerical gradient`(4)、skimage `invalid entry in coordinates array`(4)… |
| 2×2 | 658 | 0 | 23 | 同上 + `index 4 is out of bounds for array with size 4` |
| 1-D | 0 | **681** | 0 | 既存の門 `_check_input_sort` が全部断る |
| inf | 657 | 5 | 19 | op 自身の日本語の拒否文(bridge / random_walker …)と numpy の `range … is not finite` |
| RGB (H,W,3) | 348 | 89 | 244 | `docs/KNOWN_ISSUES.md` #32-4(3-D を体積として通す設計、未着手) |

空のフレームは実務では「読めなかった」「ROI が画像の外」の**下流症状**で、どの op で出るかは偶然。その偶然ごとに 49 種類の文が出ていた。410 op は空や定数を黙って返す(「0 枚検査して全部 ok」の族)。

## なぜ門が通したか

入力の門は **1-D**(ndim)・dtype・値域を見ていて、**サイズ 0** を見ていなかった。1-D が 681/681 で断られているのは門が在ったから、空が 266 通りなのは門が無かったから —— 同じ場所に立つ門が 1 本足りなかっただけ([[feedback_one_probe_input_is_not_coverage]]: 探針は 1×1 や 32×32 で、(0,0) を一度も渡していない)。極小画像の生エラーは、`raise` の約束が「op の本当の例外をそのまま」なので包み直せず、**どの op が投げたか**を足す手段が無かった(Python 3.11 の `add_note` を使っていなかった)。

## 直し

1. **`api._check_input_empty`** を入力の門の先頭に —— ラスタ sort(image / region / volume / color)で `size == 0` なら「`op X: empty input (shape) — nothing to process. … check the step upstream (read_image / crop)`」の 1 文。方針は他の入力検査と同じ(raise で止まり、fallback / warn で記録して sort の既定値)。feature / signal など空が正当でありうる sort には掛けない。
2. **`api._annotate_raw`** —— `raise` の経路で op の中から出た例外に、**型も文も変えず** `add_note` で「op 名・入力の形・dtype・op ノートを見よ」を注記。文に op 名が既にある例外(clean)には足さない。3.10 では何もしない。
3. **兄弟箇所**: `engine.diagnose_stages`(Studio / `fullseye run --describe` の validate)の「unknown operator」も `api._explain_unregistered` を通し、backend 不足なら不足 extra を言う。`fullseye has` の呼び出し例に配布物の CLI(`fullseye apply`)と Python 呼び出しを併記(checkout 専用の綴りだけだった)。

**残したもの(設計・未着手)**: RGB (H,W,3) を 2-D op が体積として通す件は KNOWN_ISSUES #32-4 のまま(3-D を意図して受ける op の一覧が要る)。極小画像の**最小サイズ**は op ごとに違い(kornia は窓 ≥ 3 で 2×2 以上、numpy gradient は 2 以上、HOG は cell 単位)、注記で「どの op がどの形で」までは言えるが「必要な最小サイズ」は各 op の門の仕事として残す。
