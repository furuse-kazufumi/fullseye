---
op: hankel_image
dim: math
category: transform
in: image2d
out: table
examples: [transforms_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# hankel_image — MATH `transform` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.hankel_image(image, *, center=None, spacing: 'float' = 1.0, n: 'int' = 256, r_max: 'float | None' = None) -> 'dict'` (実装を直接呼ぶなら `import mathtransforms; mathtransforms.hankel_image(image, *, center=None, spacing: 'float' = 1.0, n: 'int' = 256, r_max: 'float | None' = None) -> 'dict'`、台帳から引くなら `opsmath.get("hankel_image")`)

## 使い方

軸対称な画像(円い開口・ガウスの塊・回折の輪)の 2 次元フーリエ変換を、動径の 1 本の Hankel 変換で求める。

画像を中心からの距離で 1 画素幅の輪に分けて平均し(動径の分布)、``hankel_transform``(0 次)にかける。
軸対称なら 2 次元の変換が**1 本の積分**で済み(輪で平均するので雑音も 1/√(輪の画素数) に減る)、軸対称から
どれだけ崩れているか(``asymmetry``)を数で返す。周波数の刻みは 2-D FFT と同じく 1/(2·半径) 程度で、細かくはならない。

Args:
    image: 2-D の実画像。
    center: 中心 (行, 列)。省略すると明るさの重心。
    spacing: 1 画素の長さ(周波数の単位を決める)。
    n: Hankel 変換の標本数。
    r_max: 使う半径の上限(既定 = 中心から画像の縁までの最短距離。角の欠けた輪は使わない)。

Returns:
    ``nu``(周波数)・``F``(2-D フーリエ変換の動径断面、∬ f e^{−2πi k·x} dx の値)・``r``・``profile``(動径の分布)・
    ``center``・``asymmetry`` = ‖画像 − 分布から作り直した軸対称の画像‖ / ‖画像‖(0 なら軸対称。暗い背景で薄めない)。

門: 半径 R の円板は F(ν) = R J₁(2πνR)/ν(Airy)、exp(−π r²/σ²) は σ² exp(−π σ² ν²)(自己双対の拡大)、
2-D FFT の動径断面と一致。

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
