---
op: footstep_plan
dim: drive
category: locomotion
in: mask
out: table
gpu: なし
examples: [walking_ops_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# footstep_plan — DRIVE `locomotion` op

- **データ種**: `mask` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.footstep_plan(mask, cell, start, goal_col, step_max, width_min, width_max, deviation_weight: 'float' = 0.1, extent=None) -> 'dict'` (実装を直接呼ぶなら `import locomotion; locomotion.footstep_plan(mask, cell, start, goal_col, step_max, width_min, width_max, deviation_weight: 'float' = 0.1, extent=None) -> 'dict'`、台帳から引くなら `opsdrive.get("footstep_plan")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Alternating left/right footstep sequence over a foothold mask (exact shortest path).

足場の候補の mask と、歩幅・歩隔の制約から、左右交互の着地点の列を出す。

格子の約束は :func:`terrain.elevation_map` と同じ(行 i = y、列 j = x、セル辺 ``cell`` [m])。
進行方向は +x(列が増える向き)、**左足は y が大きい側**(行が大きい)。

* 状態 = (いま立っている足のセル, その足が左か右か, 反対の足がゴールを越えているか)。
  次の一歩は反対の足を、``mask`` が True のセル c に置く:
  歩幅 ``0 ≤ (x_c − x_stance) ≤ step_max`` [m]、歩隔
  ``width_min ≤ (y_left − y_right) ≤ width_max`` [m] (左右が入れ替わる交差を許さない)。
* 一歩の費用 = ``1 + deviation_weight·[((x_c − x_s − step_max)/step_max)² +
  ((w − w_mid)/w_half)²]``(``w_mid``・``w_half`` は歩隔の幅の中央と半幅、
  半幅が 0 のときは 2 項目を 0)。第 1 項 1 が歩数を数え、残りは最大の歩幅・中央の
  歩隔へ寄せる(平地では規則的に交互に並ぶ)。
* ゴール = 最後の 2 歩(左右 1 歩ずつ)の両方が列 ``goal_col`` 以上。
* 解法: 状態の上の Dijkstra(費用は非負)= 厳密な最小費用。小さな格子では総当たりの
  最小と一致する(tests の門)。

``start`` は ``((行, 列) の左足, (行, 列) の右足)``。どちらの足から踏み出すかも探索が
決める。返り値 ``{"reached", "steps": [{"side": "L"/"R", "cell": (i, j), "xy"(extent が
あるとき)}], "cost", "n_steps", "expanded"}``。届かないときは ``reached = False``・
``steps`` 空・``cost = inf``(``risk_aware_path`` と同じ約束)。

★``roverslip.risk_aware_path`` は再利用しなかった: あちらの状態は 1 セル、辺は 8 近傍の
(8, H, W) の費用で、左右交互・歩幅の窓・歩隔の窓(反対の足との相対位置)を持てない。
空の入力(``mask`` が 0 要素)は ValueError で拒否する。

English: exact Dijkstra over (stance cell, side, other-foot-past-goal) states; a step puts
the other foot on a True cell within the step-length window ``[0, step_max]`` and the
step-width window ``[width_min, width_max]`` (left foot on the larger-y side). Unreachable
goals return ``reached = False`` and ``cost = inf``.

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
