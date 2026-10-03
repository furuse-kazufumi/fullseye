---
op: laplace_inverse_talbot
dim: math
category: transform
in: signal × signal × signal
out: signal
examples: [transforms_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# laplace_inverse_talbot — MATH `transform` op

- **データ種**: `signal × signal × signal` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.laplace_inverse_talbot(num, den, t, *, M: 'int' = 32) -> 'np.ndarray'` (実装を直接呼ぶなら `import mathtransforms; mathtransforms.laplace_inverse_talbot(num, den, t, *, M: 'int' = 32) -> 'np.ndarray'`、台帳から引くなら `opsmath.get("laplace_inverse_talbot")`)

## 使い方

有理関数 F(s) = num(s)/den(s) の数値逆ラプラス変換(固定 Talbot 法)。

厳密解は ``tf_impulse_response`` が行列指数で出すので、**2 つの独立な経路で同じ f(t) が出るか**が
この op の検算になる。任意の F(s)(1/√s など)は ``laplace_inverse_func`` へ。

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

## 型が繋がる次の op(`signal` を入力に取れる)

[mat_solve](../linalg/mat_solve.md) · [mat_lstsq](../linalg/mat_lstsq.md) · [stat_describe](../stats/stat_describe.md) · [stat_histogram](../stats/stat_histogram.md) · [stat_zscore](../stats/stat_zscore.md) · [interp_linear](../interp_poly/interp_linear.md) · [interp_cubic](../interp_poly/interp_cubic.md) · [interp_scattered](../interp_poly/interp_scattered.md)

## 同カテゴリ(`transform`)

[abel_transform](abel_transform.md) · [abel_inverse](abel_inverse.md) · [abel_inverse_image](abel_inverse_image.md) · [abel_revolve](abel_revolve.md) · [hankel_transform](hankel_transform.md) · [tf_poles_zeros](tf_poles_zeros.md) · [tf_freq_response](tf_freq_response.md) · [tf_impulse_response](tf_impulse_response.md)

---
*Provenance: mathtransforms.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
