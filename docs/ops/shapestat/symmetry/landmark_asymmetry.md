---
op: landmark_asymmetry
dim: shapestat
category: symmetry
in: points
out: signal
examples: [shapestat_landmark_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# landmark_asymmetry — SHAPESTAT `symmetry` op

- **データ種**: `points` → `signal`
- **呼び出し**: `import shapestats; shapestats.landmark_asymmetry(landmarks, pairs=None, plane=None)` (または `opsshapestat.get("landmark_asymmetry")`)

## 使い方

左右の対ごとの**符号つき**非対称量。→ ``(M,)``。

各対について、片方を面で鏡映してもう片方と比べ、面の法線方向の差を返す。
符号は「右が外側なら正」(:func:`mirror_plane_from_pairs` が法線をその向きに
揃えている)。**絶対値にまとめない** —— 左右どちらが張り出しているかは
臨床でも検査でも意味が違う。

``pairs=None`` / ``plane=None`` はどちらも :func:`mirror_plane_from_pairs`
と同じ既定(前半/後半の対、その対から出した正中面)。**面を省くと、面自体が
同じ対から決まる**ので「面を決めた材料で面からのずれを測る」ことになる ——
それでも左右差は測れる(中点は定義上どちらの側にも寄らない)が、
別の情報源から面が決まるなら渡したほうが強い。

## 詳しい使い方ガイド

- [shape_statistics ファミリ ガイド](../guides/shape_statistics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [shapestat_landmark_tour](../../../../examples/shapestat_landmark_tour.py) — `py -3.11 examples/shapestat_landmark_tour.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[shape_reconstruct](../model/shape_reconstruct.md)

## 同カテゴリ(`symmetry`)

[mirror_plane_from_pairs](mirror_plane_from_pairs.md)

---
*Provenance: shapestats.py — SHAPESTAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
