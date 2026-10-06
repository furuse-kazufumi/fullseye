---
op: abel_inverse
dim: math
category: transform
in: signal
out: signal
examples: [transforms_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# abel_inverse — MATH `transform` op

- **データ種**: `signal` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.abel_inverse(A, dr: 'float' = 1.0, *, method: 'str' = 'derivative', n_quad: 'int' = 64) -> 'np.ndarray'` (実装を直接呼ぶなら `import mathtransforms; mathtransforms.abel_inverse(A, dr: 'float' = 1.0, *, method: 'str' = 'derivative', n_quad: 'int' = 64) -> 'np.ndarray'`、台帳から引くなら `opsmath.get("abel_inverse")`)

## 使い方

投影 A(y) から軸対称な分布 f(r) を戻す(逆 Abel 変換 = 軸対称物体の断層化)。

* ``"derivative"`` —— f(r) = −(1/π) ∫_r^R A'(y) / √(y² − r²) dy。y = √(r² + u²) と置いて特異点を消し、
  A を 3 次スプラインで微分する。滑らかな投影には精度が高いが、**微分が雑音を増幅する**:
  雑音の誤差は標本間隔 dr に反比例して増える(2026-10-03 実測、雑音 1%: 標本数 80 → 640 で
  平均誤差 0.027 → 0.237、両対数の傾き ≈ 1)。粗い格子ではこちらが良い。
* ``"onion"`` —— 殻を剥く: f を半径 dr の殻ごとに一定とみなし、弦の長さの上三角行列を外側から解く。
  解像度は殻の幅で決まり、微分を取らないぶん雑音の増え方が緩い(同じ実測で 0.036 → 0.100、傾き ≈ 1/2)。
  **細かい格子の実測ではこちら**(n=640 で微分の 2.4 分の 1)、粗い格子(n≈80)では逆転する。

2 つは独立な離散化なので、**同じ投影に両方を当てて食い違いを見る**のが検算になる。
門: A(y) = √π σ exp(−y²/σ²) から f(r) = exp(−r²/σ²)。

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

[abel_transform](abel_transform.md) · [abel_inverse_image](abel_inverse_image.md) · [abel_revolve](abel_revolve.md) · [hankel_transform](hankel_transform.md) · [tf_poles_zeros](tf_poles_zeros.md) · [tf_freq_response](tf_freq_response.md) · [tf_impulse_response](tf_impulse_response.md) · [tf_step_response](tf_step_response.md)

---
*Provenance: mathtransforms.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
