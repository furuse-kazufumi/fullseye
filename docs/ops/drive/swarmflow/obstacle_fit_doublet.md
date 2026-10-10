---
op: obstacle_fit_doublet
dim: drive
category: swarmflow
in: table
out: table
examples: [poc_swarm_obstacle_from_flow]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# obstacle_fit_doublet — DRIVE `swarmflow` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.obstacle_fit_doublet(field, speed=None, upstream_only: 'bool' = False, exclude_margin: 'float' = 1.25, min_explained: 'float' = 0.5, min_radius=None) -> 'dict'` (実装を直接呼ぶなら `import swarmflow; swarmflow.obstacle_fit_doublet(field, speed=None, upstream_only: 'bool' = False, exclude_margin: 'float' = 1.25, min_explained: 'float' = 0.5, min_radius=None) -> 'dict'`、台帳から引くなら `opsdrive.get("obstacle_fit_doublet")`)

## 使い方

速度場に円柱まわりのポテンシャル流 u − i v = U (1 − R²/(z − z_c)²) を当てはめる(実装 2、2 次元の非線形最小二乗)。

未知数は (x_c, y_c, R², U)。出発点は 2 つ: :func:`stagnation_from_centerline` と、格子の節点を中心の候補にした
粗い探索(U を固定すると模型は R² について 1 次なので閉形式で解ける)。説明できる割合の大きい方を採る。円の
``exclude_margin`` 倍より内側の格子は使わない(格子へ移す核が壁をまたいで速さを均すため)—— 推定し直して 3 回回す。
``upstream_only`` なら衝突点より上流(x < x_c − R)の格子だけで当てはめる(「当たる前に」分かるか)。

判定: 一様流だけの模型(u, v が定数)の残差 RSS₀ に対して、円柱の模型で減った割合 1 − RSS₁/RSS₀(**乱れのうち
円柱で説明できる割合**)が ``min_explained`` 以上、半径が ``min_radius``(既定 = 格子の間隔 2 つ)以上、中心が場の中
—— の 3 つで ``detected``。否定の判定(障害物なし)はこの割合が小さいことで出る。
★半径の下限は解像の限界: :func:`swarm_field_from_tracks` の格子は個体の間隔 s ごとなので、既定では R < 2s の障害物を
「ある」と言わない。拒否が正当なことは実測で確かめた(一様に撒いた粒子、R = 0.6 m: R/s ≈ 5 で中心・半径とも 2 % 以内、
R/s ≈ 2.5 で 5 % 以内、R/s ≈ 1.2 で半径が 48 % 小さく出る)。

Returns:
    dict: ``center``・``radius``・``speed``・``stagnation``・``explained``・``detected``・``n_used``・``rms_residual``
    (m/s)・``rms_null``(m/s)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_swarm_obstacle_from_flow](../../../../examples/poc_swarm_obstacle_from_flow.py) — `py -3.11 examples/poc_swarm_obstacle_from_flow.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`swarmflow`)

[sph_kernel](sph_kernel.md) · [sph_density_pressure](sph_density_pressure.md) · [swarm_simulate](swarm_simulate.md) · [swarm_render_overhead](swarm_render_overhead.md) · [swarm_field_from_tracks](swarm_field_from_tracks.md) · [swarm_field_from_piv](swarm_field_from_piv.md) · [potential_flow_cylinder](potential_flow_cylinder.md) · [velocity_deficit_map](velocity_deficit_map.md)

---
*Provenance: swarmflow.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
