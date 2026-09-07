---
op: shape_project
dim: shapestat
category: model
in: shapemodel × points
out: signal
examples: [shapestat_landmark_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# shape_project — SHAPESTAT `model` op

- **データ種**: `shapemodel × points` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.shape_project(model, shape, align: 'bool' = True)` (実装を直接呼ぶなら `import shapestats; shapestats.shape_project(model, shape, align: 'bool' = True)`、台帳から引くなら `opsshapestat.get("shape_project")`)

## 使い方

形をモデルの座標(主成分スコア)へ。→ ``(k,)``。

``align=True`` なら先に平均形状へ Procrustes で合わせる。合わせずに投影すると
位置と向きの違いがスコアに漏れ、**同じ形なのに別の個体に見える**。

式: ``scores = components @ (shape - mean).ravel()``(``components`` は
``(k, N*3)`` の正規直交行、``mean`` は ``(N, 3)``)。``align=True`` のときは
``procrustes_align(shape, mean)``(スケール込み・鏡像なし)を先に掛ける。

- ``model``: ``shape_pca`` の返り値(``mean`` / ``components`` / ``variance`` /
  ``n_points`` を持つ dict)。欠けていれば ``ValueError``。
- ``shape``: ``(N, 3)``、``N == model["n_points"]``、有限。点の並びは学習に使った
  ランドマークと同じ順であること(対応が違っても例外は出ない)。
- ``align``: 既定 True。``shape_pca(align=False)`` で作ったモデル(大きさを形質に
  含める)に投影するときは、ここも ``False`` にしないとスケールが消える。
- 返り値: ``(k,)`` float64。各成分の単位は座標と同じ。``sqrt(variance)`` で割れば
  標準偏差単位(何 σ 外れているか)になる。
- 失敗: ``ValueError``(モデルの形式、点数の不一致、非有限)。

逆写像は ``shape_reconstruct``、外れ具合の 1 数値は ``shape_mahalanobis``。

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

[shape_pca](shape_pca.md) · [shape_reconstruct](shape_reconstruct.md) · [shape_mahalanobis](shape_mahalanobis.md) · [shape_explained_variance](shape_explained_variance.md) · [shape_synthesize](shape_synthesize.md)

---
*Provenance: shapestats.py — SHAPESTAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
