---
op: shape_synth_family
dim: shapestat
category: synth
in: 
out: shapeset
examples: [shapestat_landmark_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# shape_synth_family — SHAPESTAT `synth` op

- **データ種**: `なし` → `shapeset`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.shape_synth_family(n_shapes: 'int' = 8, n_points: 'int' = 64, n_modes: 'int' = 2, mode_scale=(0.3, 0.12), noise: 'float' = 0.0, seed: 'int' = 0)` (実装を直接呼ぶなら `import shapestats; shapestats.shape_synth_family(n_shapes: 'int' = 8, n_points: 'int' = 64, n_modes: 'int' = 2, mode_scale=(0.3, 0.12), noise: 'float' = 0.0, seed: 'int' = 0)`、台帳から引くなら `opsshapestat.get("shape_synth_family")`)

## 使い方

既知の変形モードを持つ形の群を作る。→ ``(n_shapes, n_points, 3)``。

基準形は楕円体上の準一様な点で、そこに **正規直交な変形モード**を
既知の重みで足す。モード 1 は長軸方向の伸び、モード 2 は左右の曲げ。
:func:`shape_pca` に食わせると、**主成分の分散比が ``mode_scale`` の 2 乗比に
一致する**はずで、これが統計形状モデルの検算になる。

``noise`` は点ごとの等方ガウス雑音の標準偏差(モデルに乗らない成分)。

## 詳しい使い方ガイド

- [shape_statistics ファミリ ガイド](../guides/shape_statistics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [shapestat_landmark_tour](../../../../examples/shapestat_landmark_tour.py) — `py -3.11 examples/shapestat_landmark_tour.py`

## 型が繋がる次の op(`shapeset` を入力に取れる)

[generalized_procrustes](../procrustes/generalized_procrustes.md) · [shape_mean](../procrustes/shape_mean.md) · [shape_pca](../model/shape_pca.md)

## 同カテゴリ(`synth`)

[shape_perturb](shape_perturb.md)

---
*Provenance: shapestats.py — SHAPESTAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
