---
op: pure_pursuit_curvature
dim: drive
category: lateral
in: any
out: table
examples: [poc_driving_lateral]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# pure_pursuit_curvature — DRIVE `lateral` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.pure_pursuit_curvature(pose, path, lookahead, *, start_index=None, window: 'int' = 40) -> 'Dict[str, np.ndarray]'` (実装を直接呼ぶなら `import drivelateral; drivelateral.pure_pursuit_curvature(pose, path, lookahead, *, start_index=None, window: 'int' = 40) -> 'Dict[str, np.ndarray]'`、台帳から引くなら `opsdrive.get("pure_pursuit_curvature")`)

## 使い方

pure pursuit: 後車軸の中心(``pose`` = (x, y, ψ)、(N, 3) 可)から経路の上で距離 L_d 先の点を狙う曲率 κ = 2 sin α / L_d。

経路は折線(M, 2)。最も近い点を探し、そこから先で初めて距離が L_d になる点を区間の上で 2 次方程式で求める
(経路の終わりまで届かなければ終点を狙い、L_d をその距離にする)。``start_index`` と ``window`` で最も近い点を
探す範囲を絞る(長い経路の繰り返しを速くする。None なら全体)。
返り値: ``kappa``, ``alpha``, ``goal`` (N, 2), ``index``(最も近い区間), ``lateral``(経路からの横ずれ、左が正),
``lookahead``(実際の距離)。1 つの pose なら先頭の次元を落とす。

**Raises** ``ValueError``: 形の誤り、L_d ≤ 0、start_index が範囲外。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_lateral](../../../../examples/poc_driving_lateral.py) — `py -3.11 examples/poc_driving_lateral.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`lateral`)

[friction_circle_usage](friction_circle_usage.md) · [curve_speed_limit](curve_speed_limit.md) · [design_min_radius](design_min_radius.md) · [understeer_gradient](understeer_gradient.md) · [steady_cornering](steady_cornering.md) · [bicycle_model_step](bicycle_model_step.md) · [ackermann_steer_angles](ackermann_steer_angles.md) · [offtracking_circle](offtracking_circle.md)

---
*Provenance: drivelateral.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
