---
op: procrustes_align
dim: shapestat
category: procrustes
in: points × points
out: points
examples: [shapestat_landmark_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# procrustes_align — SHAPESTAT `procrustes` op

- **データ種**: `points × points` → `points`
- **呼び出し**: `import fullseye as fs; fs.ledger.procrustes_align(source, target, scaling: 'bool' = True, reflection: 'bool' = False)` (実装を直接呼ぶなら `import shapestats; shapestats.procrustes_align(source, target, scaling: 'bool' = True, reflection: 'bool' = False)`、台帳から引くなら `opsshapestat.get("procrustes_align")`)

## 使い方

*source* を *target* に重ねた点。→ ``(N, 3)``(:func:`procrustes_fit` の適用)。

``M = procrustes_fit(source, target, scaling, reflection)`` を求め、
``source @ M[:3, :3].T + M[:3, 3]`` を返す。変換は重心合わせ + SVD による回転
(+ 任意でスケール)の相似変換で、**i 番目どうしが対応している**ことが前提。
対応の無い点群を渡しても例外は出ず、意味の無い配置が返る(その場合は
ICP 系の登録を使う)。

- ``source``, ``target``: ``(N, 3)``、同じ ``N``、有限。``N = 1`` でも通る(並進のみ)。
- ``scaling=True``: 大きさの違いも吸収する。``False`` なら剛体変換。
  ``source`` が全点同一(広がり 0)のときスケールは 1 のまま。
- ``reflection=False``(既定): ``det(R) = +1`` を強制。``True`` にすると鏡像も
  許す ―― 左右非対称性を測る用途では消えてしまうので通常は既定のまま。
- 返り値: ``(N, 3)`` float64。残差を数値で欲しいなら ``procrustes_distance``、
  変換行列そのものは ``procrustes_fit``。
- 失敗: ``ValueError``(形が ``(N, 3)`` でない、``N`` 不一致、非有限)。

多数の形を同時に揃えるなら ``generalized_procrustes``。

## 詳しい使い方ガイド

- [shape_statistics ファミリ ガイド](../guides/shape_statistics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [shapestat_landmark_tour](../../../../examples/shapestat_landmark_tour.py) — `py -3.11 examples/shapestat_landmark_tour.py`

## 型が繋がる次の op(`points` を入力に取れる)

[shape_perturb](../synth/shape_perturb.md) · [procrustes_fit](procrustes_fit.md) · [procrustes_distance](procrustes_distance.md) · [shape_project](../model/shape_project.md) · [shape_mahalanobis](../model/shape_mahalanobis.md) · [mirror_plane_from_pairs](../symmetry/mirror_plane_from_pairs.md) · [landmark_asymmetry](../symmetry/landmark_asymmetry.md) · [signed_surface_distance](../deviation/signed_surface_distance.md)

## 同カテゴリ(`procrustes`)

[procrustes_fit](procrustes_fit.md) · [procrustes_distance](procrustes_distance.md) · [generalized_procrustes](generalized_procrustes.md) · [shape_mean](shape_mean.md)

---
*Provenance: shapestats.py — SHAPESTAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
