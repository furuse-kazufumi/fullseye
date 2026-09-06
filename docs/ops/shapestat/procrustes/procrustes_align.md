---
op: procrustes_align
dim: shapestat
category: procrustes
in: points × points
out: points
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# procrustes_align — SHAPESTAT `procrustes` op

- **データ種**: `points × points` → `points`
- **呼び出し**: `import shapestats; shapestats.procrustes_align(source, target, scaling: 'bool' = True, reflection: 'bool' = False)` (または `opsshapestat.get("procrustes_align")`)

## 使い方

*source* を *target* に重ねた点。→ ``(N, 3)``(:func:`procrustes_fit` の適用)。

## 詳しい使い方ガイド

- [shape_statistics ファミリ ガイド](../guides/shape_statistics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`points` を入力に取れる)

[shape_perturb](../synth/shape_perturb.md) · [procrustes_fit](procrustes_fit.md) · [procrustes_distance](procrustes_distance.md) · [shape_project](../model/shape_project.md) · [shape_mahalanobis](../model/shape_mahalanobis.md) · [mirror_plane_from_pairs](../symmetry/mirror_plane_from_pairs.md) · [landmark_asymmetry](../symmetry/landmark_asymmetry.md) · [signed_surface_distance](../deviation/signed_surface_distance.md)

## 同カテゴリ(`procrustes`)

[procrustes_fit](procrustes_fit.md) · [procrustes_distance](procrustes_distance.md) · [generalized_procrustes](generalized_procrustes.md) · [shape_mean](shape_mean.md)

---
*Provenance: shapestats.py — SHAPESTAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
