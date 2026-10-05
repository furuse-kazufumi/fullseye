---
op: dwt_transform
dim: math
category: transform
in: image2d
out: table
examples: [transforms_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# dwt_transform — MATH `transform` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.dwt_transform(x, *, order: 'int' = 2, levels: 'int' = 1, axes=None) -> 'dict'` (実装を直接呼ぶなら `import mathtransforms; mathtransforms.dwt_transform(x, *, order: 'int' = 2, levels: 'int' = 1, axes=None) -> 'dict'`、台帳から引くなら `opsmath.get("dwt_transform")`)

## 使い方

Daubechies dbN の多段・N 次元の離散ウェーブレット変換(周期境界で厳密に正規直交)。

Args:
    x: 実配列(1-D 信号・2-D 画像・3-D ボリューム)。変換する軸の長さは 2^levels の倍数。
    order: dbN の N(1 = Haar)。
    levels: 段数。各段で近似(全軸ローパス)をさらに分ける。
    axes: 変換する軸(省略で全軸)。

Returns:
    ``approx`` 最後の近似、``details`` = 段ごとの dict(キーは軸ごとの 'a'/'d' の並び、例 2-D なら
    'ad'・'da'・'dd')、``energy_in``・``energy_out``(Parseval で一致)、``order``・``levels``・``axes``。
    ``dwt_inverse`` に丸ごと渡すと元に戻る。

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

[abel_transform](abel_transform.md) · [abel_inverse](abel_inverse.md) · [abel_inverse_image](abel_inverse_image.md) · [abel_revolve](abel_revolve.md) · [hankel_transform](hankel_transform.md) · [tf_poles_zeros](tf_poles_zeros.md) · [tf_freq_response](tf_freq_response.md) · [tf_impulse_response](tf_impulse_response.md)

---
*Provenance: mathtransforms.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
