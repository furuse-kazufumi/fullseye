---
op: procrustes_distance
dim: shapestat
category: procrustes
in: points × points
out: measurement
examples: [shapestat_landmark_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# procrustes_distance — SHAPESTAT `procrustes` op

- **データ種**: `points × points` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.procrustes_distance(source, target, scaling: 'bool' = True, reflection: 'bool' = False, normalize: 'bool' = True)` (実装を直接呼ぶなら `import shapestats; shapestats.procrustes_distance(source, target, scaling: 'bool' = True, reflection: 'bool' = False, normalize: 'bool' = True)`、台帳から引くなら `opsshapestat.get("procrustes_distance")`)

## 使い方

Procrustes 距離 = 重ねたあとの点ごと RMS。→ float。

``normalize=True``(既定)は *target* の重心距離 RMS で割った**無次元**の値。
形どうしを大きさに依らず比べるならこちら。生の距離が要るなら False。

## 詳しい使い方ガイド

- [shape_statistics ファミリ ガイド](../guides/shape_statistics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [shapestat_landmark_tour](../../../../examples/shapestat_landmark_tour.py) — `py -3.11 examples/shapestat_landmark_tour.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`procrustes`)

[procrustes_fit](procrustes_fit.md) · [procrustes_align](procrustes_align.md) · [generalized_procrustes](generalized_procrustes.md) · [shape_mean](shape_mean.md)

---
*Provenance: shapestats.py — SHAPESTAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
