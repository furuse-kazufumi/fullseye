---
op: signed_surface_distance
dim: shapestat
category: deviation
in: points × points
out: signal
examples: [shapestat_landmark_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# signed_surface_distance — SHAPESTAT `deviation` op

- **データ種**: `points × points` → `signal`
- **呼び出し**: `import shapestats; shapestats.signed_surface_distance(query, surface, surface_normals=None, k: 'int' = 1)` (または `opsshapestat.get("signed_surface_distance")`)

## 使い方

問い合わせ点から面までの**符号つき**距離。→ ``(N,)``。

符号は面の法線から決める(外側が正)。1-D の輪郭には
``profileops.profile_deviation`` があるのに 3-D に相当が無かった、というのが
2026-09-06 に PoC が出した穴。

法線を省くと :func:`normals_orient.estimate_oriented_normals` で推定する
—— **向き付き**でなければ符号が点ごとにばらつく(素の PCA 法線は符号が任意で、
回転すると 4 割が裏返る。``pointcloud.fpfh`` が踏んだのと同じ穴)。

``k`` は符号を決めるときに使う最近傍の数。1 だと最近傍 1 点の法線に賭ける
ことになり、雑音のある面では符号が飛ぶ。2 以上にすると距離で重みを付けた
平均の向きで決める(距離そのものは最近傍のまま)。

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

## 同カテゴリ(`deviation`)

—

---
*Provenance: shapestats.py — SHAPESTAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
