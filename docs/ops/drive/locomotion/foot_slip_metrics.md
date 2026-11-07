---
op: foot_slip_metrics
dim: drive
category: locomotion
in: any × mask × points
out: table
gpu: なし
examples: [walking_ops_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# foot_slip_metrics — DRIVE `locomotion` op

- **データ種**: `any × mask × points` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.foot_slip_metrics(foot_xyz, stance, body_xyz, max_slip: 'float' = 0.02, min_advance_ratio: 'float' = 0.5) -> 'dict'` (実装を直接呼ぶなら `import locomotion; locomotion.foot_slip_metrics(foot_xyz, stance, body_xyz, max_slip: 'float' = 0.02, min_advance_ratio: 'float' = 0.5) -> 'dict'`、台帳から引くなら `opsdrive.get("foot_slip_metrics")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Horizontal foot slip during stance, foot-measured progression, and a 'body-only' gate.

立脚中の足の水平の滑りと、足で測った前進。

* 滑り: 立脚の区間(``stance`` が続けて True のコマ)ごとに、足の水平位置が区間の最初の
  位置から離れた最大の距離 [m] (``slip``)。全区間の最大が ``max_slip_observed``。
* 足で測る前進: 足ごとに、続く 2 つの立脚の区間の最初の位置の差を進行方向に射影して
  足し、足の平均を取る(``foot_advance`` [m])。足を置き直さない限り増えない。
* 胴の前進: ``body_xyz`` の最初と最後の水平の差の大きさ(``body_advance``)。進行方向は
  その向き(胴が動かなければ足の平均の向き、それも無ければ +x)。
* 門 ``walking_ok``: ``max_slip_observed ≤ max_slip`` かつ
  ``foot_advance ≥ min_advance_ratio × body_advance``。胴だけが進み、足が置き直されない
  (滑っている・引きずられている・足が地面に描かれているだけ)見せかけの歩行を落とす。
  ``advance_ratio`` = ``foot_advance / body_advance``(胴が動かなければ ``None``)。

``foot_xyz`` (T, F, 3) [m]、``stance`` (T, F) bool(:func:`gait_phase` の ``stance``)、
``body_xyz`` (T, 3) [m]。空の入力(``foot_xyz`` が 0 要素)は ValueError で拒否する。

English: per stance interval the slip is the largest horizontal excursion of the foot from
where it touched down; progression measured by the feet is the sum of stance-to-stance
displacements along the direction of travel. ``walking_ok`` fails a scene in which only
the body advances.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [walking_ops_tour](../../../../examples/walking_ops_tour.py) — `py -3.11 examples/walking_ops_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`locomotion`)

[contact_points](contact_points.md) · [com_from_silhouette](com_from_silhouette.md) · [support_polygon](support_polygon.md) · [com_support_margin](com_support_margin.md) · [gait_phase](gait_phase.md) · [support_line_margin](support_line_margin.md) · [lipm_capture_point](lipm_capture_point.md) · [capture_margin](capture_margin.md)

---
*Provenance: locomotion.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
