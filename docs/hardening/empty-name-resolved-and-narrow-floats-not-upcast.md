---
id: empty-name-resolved-and-narrow-floats-not-upcast
date: 2026-09-20
found_by: genspark_external_review
kind: silent-wrong
severity: high
where: [api.py]
ops: [lowpass, gaussian]
gate: [test_empty_operator_name_is_unknown_not_lowpass, test_narrow_floats_are_upcast_to_the_float64_contract, test_on_error_message_names_the_default_none]
status: fixed
---

# 空の op 名が lowpass に解決し、float16 / float32 が契約の float64 に昇格されていなかった

## 症状

GenSpark 第 15 報(境界値・型不一致の総当たり)。

- **N27(高)**: `fullseye.apply(img, "")` と `run_pipeline(img, [""])` が **成功して別の画像を返す**(identity でもない)。`" "` は KeyError。保存したパイプラインに空名が混ざると、エラーにならず別の op が黙って走る。
- **N29(高)**: `float16` の 0..99 を `gaussian` に渡すと、出力は float16 の 0.23..1.0(float64 の同値入力なら 29.9..65.1)。内部で `RuntimeError: array type dtype('float16') not supported`(scipy.ndimage)→ fallback で**入力のコピー**が返り、警告は op ごとに初回だけ。
- 同報の未確定「float32 と float64 の出力差(38.121..61.415 vs 38.345..70.541)」も同じ根: float32 のまま op が走り、float32 を返していた(契約は float64)。
- **N35(低)**: `on_error="ignore"` の文が `must be one of ('fallback', 'warn', 'raise')` なのに、既定の `None` は受理される(一覧に無い)。

## なぜ門が通したか

- `find_op(name)` は名前の完全一致の次に **`halcon == name`** を見る。HALCON 対応の無い op は `halcon=""` なので、`""` がその最初の 1 本(`lowpass`)に一致した。名前の空検査が入口に無く、テストは実在名と綴り違いだけを流していた。
- `_contract_dtype` は「float / complex / non-array: unchanged」で、**整数と bool だけ**を契約(float64 in [0,1])に乗せていた。float16 / float32 は「float だから」素通し —— scipy は float16 を受けず、float32 は float32 で計算する。dtype の探針は uint8 / bool / float64 だけだった([[feedback_one_probe_input_is_not_coverage]])。

## 直し

1. **`find_op`** —— 空・空白だけ・文字列でない名前は None(→ `_resolve` が「unknown operator ''」の KeyError)。
2. **`_contract_dtype`** —— `float16` / `float32` は **float64 に無損失で昇格**して op に渡す(値も範囲も変わらないので記録しない。第 1 陣で「float32 昇格は記録しない」と決めた判断は、実は昇格そのものが行われていなかった —— 今回それを行う)。
3. `_policy` の文に `or None (= FULLSEYE_ON_ERROR, default 'fallback')` を足す。
4. **別名の大小文字とハイフン**(第 17 報 N50)—— `GAUSS_FILTER` / `Gauss-Filter` が unknown だった。元の綴りに一致が無いときだけ `lower()` + `-`→`_` で 1 度引き直す(既存の解決は変わらない)。

門: `""` / `" "` / `"\t"` が apply と run_pipeline で KeyError / float16 と float32 の gaussian が float64 を返し float64 入力と一致(float16 の差は入力量子化のみ)・台帳に記録が無い / on_error の文に None がある。

**同報で設計・直し済みとして分けたもの**: N28(int8〜uint32 の 0..99 が「桁違い」)= 契約外の整数は dtype の最大値で割る**文書化された変換**で、台帳に記録される(0..99 の int32 は意味のある画像ではない)。N30(NaN 入力で出力が有限化 / sobel_amp が 1 を超える)= 第 3 陣で非有限出力を記録・strict では停止。1 超の出力は op 側の正規化の問題として保留(image sort の出力を門で clip するかは別判断)。N31(object / str)= 第 1 陣の `_reject_untyped`。N32〜N34 = 第 4・6 陣。N36 = 索引の層の合算。
