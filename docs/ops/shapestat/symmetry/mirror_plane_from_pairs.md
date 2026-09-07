---
op: mirror_plane_from_pairs
dim: shapestat
category: symmetry
in: points
out: matrix
examples: [shapestat_landmark_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# mirror_plane_from_pairs — SHAPESTAT `symmetry` op

- **データ種**: `points` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.mirror_plane_from_pairs(landmarks, pairs=None, midline=None)` (実装を直接呼ぶなら `import shapestats; shapestats.mirror_plane_from_pairs(landmarks, pairs=None, midline=None)`、台帳から引くなら `opsshapestat.get("mirror_plane_from_pairs")`)

## 使い方

左右の対応ランドマークから正中面を出す。→ ``(2, 3)``(1 行目 = 点、2 行目 = 法線)。

左右の対 ``(i, j)`` の**中点**は、どれも正中面の上に乗る。だからその中点集合に
平面を当てればよい —— 変形の量に依らず面が決まるのが要点で、残差を最小に
する面(:func:`symmetry3d.detect_reflection_symmetry`)とは別物である。

★ 2026-09-06 の実測: 6.4 mm の片側変形を入れると、**残差最適面は真の正中面
から 2.92 mm / 1.72 度ずれ、非対称量の 46 % を消した**(利得 0.54)。この
ランドマーク面なら利得 1.03。**見つけるなら残差最適面、量を言うならこちら**。

*midline* は正中線上にある(対にならない)ランドマークの添字。与えると
中点集合に足して面の当てはめを安定させる。

``pairs=None`` は**前半と後半を対にする**規約(``i`` と ``i + N//2``)。
左のランドマークを全部並べてから右を同じ順で並べる、という保存形式が
形態計測では一般的なので、それに合わせてある。**点数が奇数なら拒否する**
—— 半分に割れない並びを黙って切り詰めると、対が 1 つずつずれて全部の
符号が入れ替わる。

## 詳しい使い方ガイド

- [shape_statistics ファミリ ガイド](../guides/shape_statistics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [shapestat_landmark_tour](../../../../examples/shapestat_landmark_tour.py) — `py -3.11 examples/shapestat_landmark_tour.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

—

## 同カテゴリ(`symmetry`)

[landmark_asymmetry](landmark_asymmetry.md)

---
*Provenance: shapestats.py — SHAPESTAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
