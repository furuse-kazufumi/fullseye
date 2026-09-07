---
op: shape_synthesize
dim: shapestat
category: model
in: shapemodel
out: points
examples: [shapestat_landmark_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# shape_synthesize — SHAPESTAT `model` op

- **データ種**: `shapemodel` → `points`
- **呼び出し**: `import fullseye as fs; fs.ledger.shape_synthesize(model, sigmas=None, n_modes: 'int' = 3, seed: 'int' = 0)` (実装を直接呼ぶなら `import shapestats; shapestats.shape_synthesize(model, sigmas=None, n_modes: 'int' = 3, seed: 'int' = 0)`、台帳から引くなら `opsshapestat.get("shape_synthesize")`)

## 使い方

モデルから**もっともらしい新しい形**を 1 つ作る。→ ``(N, 3)``。

``sigmas`` を与えればその標準偏差倍のスコア、省けば先頭 ``n_modes`` 本を
正規乱数で引く。3 標準偏差を超える形は群の中に 1 つも無かった形なので、
既定では引かない(``sigmas`` で明示すれば作れる)。

## 詳しい使い方ガイド

- [shape_statistics ファミリ ガイド](../guides/shape_statistics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [shapestat_landmark_tour](../../../../examples/shapestat_landmark_tour.py) — `py -3.11 examples/shapestat_landmark_tour.py`

## 型が繋がる次の op(`points` を入力に取れる)

[shape_perturb](../synth/shape_perturb.md) · [procrustes_fit](../procrustes/procrustes_fit.md) · [procrustes_align](../procrustes/procrustes_align.md) · [procrustes_distance](../procrustes/procrustes_distance.md) · [shape_project](shape_project.md) · [shape_mahalanobis](shape_mahalanobis.md) · [mirror_plane_from_pairs](../symmetry/mirror_plane_from_pairs.md) · [landmark_asymmetry](../symmetry/landmark_asymmetry.md)

## 同カテゴリ(`model`)

[shape_pca](shape_pca.md) · [shape_project](shape_project.md) · [shape_reconstruct](shape_reconstruct.md) · [shape_mahalanobis](shape_mahalanobis.md) · [shape_explained_variance](shape_explained_variance.md)

---
*Provenance: shapestats.py — SHAPESTAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
