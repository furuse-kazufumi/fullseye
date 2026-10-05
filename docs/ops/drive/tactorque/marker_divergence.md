---
op: marker_divergence
dim: drive
category: tactorque
in: matrix × matrix × scalar
out: table
examples: [poc_tactile_dipole_torque]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# marker_divergence — DRIVE `tactorque` op

- **データ種**: `matrix × matrix × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.marker_divergence(pts, u, radius: 'float', min_neighbors: 'int' = 4, k_max: 'int' = 24) -> 'dict'` (実装を直接呼ぶなら `import tactorque; tactorque.marker_divergence(pts, u, radius: 'float', min_neighbors: 'int' = 4, k_max: 'int' = 24) -> 'dict'`、台帳から引くなら `opsdrive.get("marker_divergence")`)

## 使い方

散在マーカー pts (N, 2) と変位 u (N, 2) から各点の発散 ``div`` = ∂ux/∂x + ∂uy/∂y と回転 ``curl`` = ∂uy/∂x − ∂ux/∂y
(単位は u の単位 ÷ pts の単位)。近傍半径 ``radius`` 内(最大 ``k_max`` 個)の点に平面 c0 + c1 x + c2 y を最小二乗で当てる
(規則格子 + 半径 1.01 ピッチなら 5 点の中心差分と同値で :func:`sceneflow.flow_divergence` と 1e-15、半径 1.5 ピッチの 9 点は行平均の差分で
縁で 11 % 違う、実測)。正規方程式を点ごとに一括で解く。近傍が ``min_neighbors`` 未満、または正規方程式が特異(共線)な点は
``valid`` = False、div/curl = nan(fail-closed: 黙って 0 にしない)。FEM の散在節点にも同じ op。
**Raises** ValueError: pts/u が (N, 2) でない、形が違う、radius ≤ 0、N < min_neighbors。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tactile_dipole_torque](../../../../examples/poc_tactile_dipole_torque.py) — `py -3.11 examples/poc_tactile_dipole_torque.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tactorque`)

[punch_pressure](punch_pressure.md) · [punch_surface_uz](punch_surface_uz.md) · [hertz_pressure_shifted](hertz_pressure_shifted.md) · [ellipse_pressure_shifted](ellipse_pressure_shifted.md) · [pressure_first_moment](pressure_first_moment.md) · [boussinesq_kernel](boussinesq_kernel.md) · [boussinesq_surface_displacement](boussinesq_surface_displacement.md) · [surface_divergence_closed_form](surface_divergence_closed_form.md)

---
*Provenance: tactorque.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
