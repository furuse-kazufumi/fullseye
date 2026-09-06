---
op: shape_explained_variance
dim: shapestat
category: model
in: shapemodel
out: signal
examples: [shapestat_landmark_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# shape_explained_variance — SHAPESTAT `model` op

- **データ種**: `shapemodel` → `signal`
- **呼び出し**: `import shapestats; shapestats.shape_explained_variance(model)` (または `opsshapestat.get("shape_explained_variance")`)

## 使い方

各主成分の寄与率(合計 1)。→ ``(k,)``。

式: ``variance / total_variance``。分母は ``model["total_variance"]``(``shape_pca``
が**全**特異値から計算した総分散)で、無ければ ``variance.sum()``。

- ``model``: ``shape_pca`` の返り値。必須キーが無ければ ``ValueError``。
- 返り値: ``(k,)`` float64、各要素は ``[0, 1]``。``shape_pca(n_components=0)``
  (全成分)なら合計は 1。**``n_components`` で打ち切ったモデルでは合計が 1 未満**
  になる(切り捨てた成分の分だけ足りない)―― 「上位 k 本でどれだけ説明できるか」
  を読むにはむしろその方が正しい。
- 総分散が 0(全個体が同じ形)なら全要素 0 を返す(0 除算にしない)。

``shape_pca`` の分散は標本分散(``K-1`` で割る)なので、個体数が少ないと
固有値の絶対値は膨らむが、比であるこの量は影響を受けにくい。累積和
(``cumsum``)で「99 % に何本要るか」を決め、``shape_mahalanobis`` の ``cumulative``
や ``shape_synthesize`` の ``n_modes`` に渡す。

## 詳しい使い方ガイド

- [shape_statistics ファミリ ガイド](../guides/shape_statistics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [shapestat_landmark_tour](../../../../examples/shapestat_landmark_tour.py) — `py -3.11 examples/shapestat_landmark_tour.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[shape_reconstruct](shape_reconstruct.md)

## 同カテゴリ(`model`)

[shape_pca](shape_pca.md) · [shape_project](shape_project.md) · [shape_reconstruct](shape_reconstruct.md) · [shape_mahalanobis](shape_mahalanobis.md) · [shape_synthesize](shape_synthesize.md)

---
*Provenance: shapestats.py — SHAPESTAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
