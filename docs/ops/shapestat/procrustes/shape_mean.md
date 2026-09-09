---
op: shape_mean
dim: shapestat
category: procrustes
in: shapeset
out: points
examples: [shapestat_landmark_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# shape_mean — SHAPESTAT `procrustes` op

- **データ種**: `shapeset` → `points`
- **呼び出し**: `import fullseye as fs; fs.ledger.shape_mean(shapes, max_iter: 'int' = 100, tol: 'float' = 1e-10, scaling: 'bool' = True, reflection: 'bool' = False)` (実装を直接呼ぶなら `import shapestats; shapestats.shape_mean(shapes, max_iter: 'int' = 100, tol: 'float' = 1e-10, scaling: 'bool' = True, reflection: 'bool' = False)`、台帳から引くなら `opsshapestat.get("shape_mean")`)

## 使い方

GPA で揃えたあとの平均形状。→ ``(N, 3)``。

★ **生の平均(``shapes.mean(0)``)と混同しないこと**。位置と向きを揃えずに
平均すると、個体がばらばらに置かれているぶんだけ形が縮む。合わせてから
平均するのが「平均形状」。

## 詳しい使い方ガイド

- [shape_statistics ファミリ ガイド](../guides/shape_statistics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [shapestat_landmark_tour](../../../../examples/shapestat_landmark_tour.py) — `py -3.11 examples/shapestat_landmark_tour.py`

## 型が繋がる次の op(`points` を入力に取れる)

[shape_perturb](../synth/shape_perturb.md) · [procrustes_fit](procrustes_fit.md) · [procrustes_align](procrustes_align.md) · [procrustes_distance](procrustes_distance.md) · [shape_project](../model/shape_project.md) · [shape_mahalanobis](../model/shape_mahalanobis.md) · [mirror_plane_from_pairs](../symmetry/mirror_plane_from_pairs.md) · [landmark_asymmetry](../symmetry/landmark_asymmetry.md)

## 同カテゴリ(`procrustes`)

[procrustes_fit](procrustes_fit.md) · [procrustes_align](procrustes_align.md) · [procrustes_distance](procrustes_distance.md) · [generalized_procrustes](generalized_procrustes.md)

---
*Provenance: shapestats.py — SHAPESTAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
