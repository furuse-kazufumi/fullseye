---
op: shape_reconstruct
dim: shapestat
category: model
in: shapemodel × signal
out: points
examples: [shapestat_landmark_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# shape_reconstruct — SHAPESTAT `model` op

- **データ種**: `shapemodel × signal` → `points`
- **呼び出し**: `import fullseye as fs; fs.ledger.shape_reconstruct(model, scores)` (実装を直接呼ぶなら `import shapestats; shapestats.shape_reconstruct(model, scores)`、台帳から引くなら `opsshapestat.get("shape_reconstruct")`)

## 使い方

スコアから形を戻す。→ ``(N, 3)``。

与えたスコアが本数より少なければ残りは 0(= 平均のまま)として扱う。
多ければ ``ValueError`` —— 黙って切り捨てると「入れたはずのモードが効かない」
という追いにくい形になる。

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

[shape_pca](shape_pca.md) · [shape_project](shape_project.md) · [shape_mahalanobis](shape_mahalanobis.md) · [shape_explained_variance](shape_explained_variance.md) · [shape_synthesize](shape_synthesize.md)

---
*Provenance: shapestats.py — SHAPESTAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
