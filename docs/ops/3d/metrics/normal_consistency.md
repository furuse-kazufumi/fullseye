---
op: normal_consistency
dim: 3d
category: metrics
in: points × normals
out: measurement
examples: [metrics_eval]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# normal_consistency — 3D `metrics` op

- **データ種**: `points × normals` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.normal_consistency(points_a, normals_a, points_b, normals_b)` (実装を直接呼ぶなら `import metrics3d; metrics3d.normal_consistency(points_a, normals_a, points_b, normals_b)`、台帳から引くなら `ops3d.get("normal_consistency")`)

## 使い方

最近傍対応での法線一致度 = mean|cos(na, nb)|(向き無視)。→ [0,1]。1=完全一致。

Raises ValueError: 点群が空 or (N,3) でない/法線が点と 1 対 1 でない場合。

計算: ``points_a`` の各点について ``points_b`` の最近傍(``cKDTree``、``k=1``)を
取り、その点の法線 ``nb`` と自分の法線 ``na`` を単位化(ノルム + 1e-12 で割る)
して ``|na · nb|`` を平均する。絶対値を取るので法線の向き(表裏)の不一致は
無視される。**非対称**(``a`` → ``b`` の一方向のみ。逆向きが要るなら引数を入れ替えて
もう一度呼ぶ)。

引数: ``points_a`` ``(N, 3)``、``normals_a`` ``(N, 3)``、``points_b`` ``(M, 3)``、
``normals_b`` ``(M, 3)``。4 つとも空でない ``(*, 3)`` であること、法線の行数が
対応する点群の行数と一致することを検査する(違反は ``ValueError``)。ゼロ法線は
``1e-12`` で割られてほぼ 0 の寄与になる(エラーにしない)。

返り値: Python ``float``、``[0, 1]``。1 = 全対応で法線が平行。乱雑な法線対なら
3-D では期待値 0.5 程度になる(cos の絶対値の平均)。

注意: 位置の近さは見ない(遠い最近傍でも法線だけ比べる)。位置と合わせて評価する
なら ``chamfer_distance`` / ``fscore`` と併用する。法線が無い雲は
``estimate_point_normals``(局所 PCA)で作ってから渡す。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)
- [measurement_uncertainty](../../math/guides/measurement_uncertainty.md) — 計測の不確かさと校正の知識 — 「測れている」を主張するために

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [metrics_eval](../../../../examples_3d/metrics_eval.py) — `py -3.11 examples_3d/metrics_eval.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[vol_gaussian_psf](../restoration/vol_gaussian_psf.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`metrics`)

[chamfer_distance](chamfer_distance.md) · [hausdorff_distance](hausdorff_distance.md) · [m3c2_distance](m3c2_distance.md) · [fscore](fscore.md) · [rmse_correspondence](rmse_correspondence.md) · [voxel_iou](voxel_iou.md) · [pose_error](pose_error.md)

---
*Provenance: metrics3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
