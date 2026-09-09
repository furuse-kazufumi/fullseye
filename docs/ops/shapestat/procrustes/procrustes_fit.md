---
op: procrustes_fit
dim: shapestat
category: procrustes
in: points × points
out: matrix
examples: [poc_change_detection_misreg, poc_die_tilt_tsv_overlay, shapestat_landmark_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# procrustes_fit — SHAPESTAT `procrustes` op

- **データ種**: `points × points` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.procrustes_fit(source, target, scaling: 'bool' = True, reflection: 'bool' = False)` (実装を直接呼ぶなら `import shapestats; shapestats.procrustes_fit(source, target, scaling: 'bool' = True, reflection: 'bool' = False)`、台帳から引くなら `opsshapestat.get("procrustes_fit")`)

## 使い方

*source* を *target* へ重ねる相似変換。→ ``(4, 4)`` の同次行列。

**点の並びが対応していること**が前提(i 番目どうしが同じ解剖学的位置)。
対応が無い点群では例外は出ず、意味の無い変換が返る —— 対応の有無は
この関数からは見えない。対応が無いなら ICP 系(``registration``)を使う。

``scaling=True`` なら大きさの違いも吸収する。``reflection=False``(既定)は
``det(R) = +1`` を強制する —— 許すと左手系の個体が右手系の平均に重なり、
左右非対称性という測りたいものが消える。

行列は同次座標で ``target ~ source @ M[:3,:3].T + M[:3,3]`` の向き。

## 詳しい使い方ガイド

- [shape_statistics ファミリ ガイド](../guides/shape_statistics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_change_detection_misreg](../../../../examples/poc_change_detection_misreg.py) — `py -3.11 examples/poc_change_detection_misreg.py`
- [poc_die_tilt_tsv_overlay](../../../../examples/poc_die_tilt_tsv_overlay.py) — `py -3.11 examples/poc_die_tilt_tsv_overlay.py`
- [shapestat_landmark_tour](../../../../examples/shapestat_landmark_tour.py) — `py -3.11 examples/shapestat_landmark_tour.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

—

## 同カテゴリ(`procrustes`)

[procrustes_align](procrustes_align.md) · [procrustes_distance](procrustes_distance.md) · [generalized_procrustes](generalized_procrustes.md) · [shape_mean](shape_mean.md)

---
*Provenance: shapestats.py — SHAPESTAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
