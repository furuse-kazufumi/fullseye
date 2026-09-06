---
op: generalized_procrustes
dim: shapestat
category: procrustes
in: shapeset
out: shapeset
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# generalized_procrustes — SHAPESTAT `procrustes` op

- **データ種**: `shapeset` → `shapeset`
- **呼び出し**: `import shapestats; shapestats.generalized_procrustes(shapes, max_iter: 'int' = 100, tol: 'float' = 1e-10, scaling: 'bool' = True, reflection: 'bool' = False)` (または `opsshapestat.get("generalized_procrustes")`)

## 使い方

一般化 Procrustes(GPA)。全個体を共通の枠へ。→ ``(K, N, 3)``。

手順は教科書どおり: 1 個体を仮の平均にして全員を合わせ、平均を取り直し、
その平均を**最初の個体に合わせ直して**枠の漂流を止め、収束まで繰り返す。
最後の一手が無いと平均が毎回ゆっくり回り、``tol`` に到達しない。

収束の判定は平均形状の移動量(点ごと RMS)。反復数と収束の可否は
:func:`shape_mean` ではなくこちらには返らない —— 群を返す関数なので、
診断が要るときは前後で :func:`procrustes_distance` を測ること。

## 詳しい使い方ガイド

- [shape_statistics ファミリ ガイド](../guides/shape_statistics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`shapeset` を入力に取れる)

[shape_mean](shape_mean.md) · [shape_pca](../model/shape_pca.md)

## 同カテゴリ(`procrustes`)

[procrustes_fit](procrustes_fit.md) · [procrustes_align](procrustes_align.md) · [procrustes_distance](procrustes_distance.md) · [shape_mean](shape_mean.md)

---
*Provenance: shapestats.py — SHAPESTAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
