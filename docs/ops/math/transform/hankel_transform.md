---
op: hankel_transform
dim: math
category: transform
in: signal × signal
out: table
examples: [transforms_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# hankel_transform — MATH `transform` op

- **データ種**: `signal × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.hankel_transform(r, f, *, r_max: 'float | None' = None, order: 'int' = 0, n: 'int' = 256) -> 'dict'` (実装を直接呼ぶなら `import mathtransforms; mathtransforms.hankel_transform(r, f, *, r_max: 'float | None' = None, order: 'int' = 0, n: 'int' = 256) -> 'dict'`、台帳から引くなら `opsmath.get("hankel_transform")`)

## 使い方

p 次の Hankel 変換 F(ν) = 2π ∫_0^∞ f(r) J_p(2πνr) r dr を quasi-discrete 法で。

``(r, f)`` は動径の標本(r は昇順)。標本点 r_k へは線形補間で載せ、``r_max``(既定 = r の最大値)の外は 0。
``f`` に呼び出し可能を渡すと、標本点で直接評価する(``r`` は無視して ``r_max`` を必ず渡す)。
標本点は r_k = j_k R / S(j_k は J_p の k 番目の零点、S = j_{n+1})、周波数 ν_k = j_k / (2πR)。
この変換は核 T が**対合**(T·T = I)なので、同じ関数で逆変換もできる(``F`` を f として渡す)。

門: exp(−π r²) は自己双対(F(ν) = exp(−π ν²))。0 次の Hankel 変換は軸対称な関数の
2 次元フーリエ変換の動径断面に等しい。
返り値: ``{"r", "f", "nu", "F", "T_involution_error"}``(最後は ‖T·T − I‖_max)。

## ファミリ共通の入力契約(fail-closed)

mathops の全 op は入力を検証してから計算する(黙って通さない):

- **complex 入力は `ValueError`** — float64 への強制変換は虚部を黙って捨てる(numpy は ComplexWarning だけ出して「もっともらしく間違った」実数を返す)。`.real`/`.imag`/`abs()` を明示するか、複素対応の complexops を使う。
- **masked array(masked 要素あり)は `ValueError`** — マスクを剥がして下の生値を使う暗黙変換を拒否。埋める/落とすを明示する。
- **NaN/Inf は全入力で `ValueError`**(件数を明示して拒否 — 結果全体に伝播するため)。
- **形状は厳格**: 1-D と 2-D を暗黙昇格・ブロードキャストしない(vector 枠に matrix、matrix 枠に vector は `ValueError`。reshape を明示する)。
- **サイズ上限**: 行列を取る op と `stat_histogram` の bins は `mathops.MAX_ELEMENTS`(2^26 ≈ 6700 万要素)超で `ValueError`。

## 詳しい使い方ガイド

- [math_metrology ファミリ ガイド](../guides/math_metrology.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [transforms_tour](../../../../examples/transforms_tour.py) — `py -3.11 examples/transforms_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[dynsys_poincare_section](../dynsys/dynsys_poincare_section.md) · [dwt_inverse](dwt_inverse.md) · [chebyshev_eval_nd](../numerics/chebyshev_eval_nd.md)

## 同カテゴリ(`transform`)

[abel_transform](abel_transform.md) · [abel_inverse](abel_inverse.md) · [abel_inverse_image](abel_inverse_image.md) · [abel_revolve](abel_revolve.md) · [tf_poles_zeros](tf_poles_zeros.md) · [tf_freq_response](tf_freq_response.md) · [tf_impulse_response](tf_impulse_response.md) · [tf_step_response](tf_step_response.md)

---
*Provenance: mathtransforms.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
