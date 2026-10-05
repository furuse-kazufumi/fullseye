---
op: swarm_field_from_piv
dim: drive
category: swarmflow
in: any × scalar × scalar
out: table
examples: [poc_swarm_obstacle_from_flow]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# swarm_field_from_piv — DRIVE `swarmflow` op

- **データ種**: `any × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.swarm_field_from_piv(frames, res: 'float', frame_dt: 'float', center=(0.0, 0.0), window: 'int' = 24, overlap: 'float' = 0.5, min_peak_ratio: 'float' = 1.1, outlier_threshold=3.0) -> 'dict'` (実装を直接呼ぶなら `import swarmflow; swarmflow.swarm_field_from_piv(frames, res: 'float', frame_dt: 'float', center=(0.0, 0.0), window: 'int' = 24, overlap: 'float' = 0.5, min_peak_ratio: 'float' = 1.1, outlier_threshold=3.0) -> 'dict'`、台帳から引くなら `opsdrive.get("swarm_field_from_piv")`)

## 使い方

俯瞰のコマ列 → 隣どうしの相互相関の PIV(pivops.piv_cross_correlate)→ 全部の組の平均 → 世界の速度場。

個体を一つずつ見分けない(重なっても使える)代わりに、窓(``window`` px)より細かい乱れは均される。峰の比が
``min_peak_ratio`` 未満の窓は欠測(NaN)。★群れは格子のように並びやすく(押し合いで間隔がそろう)、相関の峰が
隣の格子の位置にも立つので峰の比が 1 に近い。実測(間隔 7.5 px、窓 24): しきい値 0 だと取り違えた窓が混ざり個体の
速度との rms が U の 13.7 %、1.1 で 1.9 %(測れた窓 85 %)、1.3 では測れた窓が 18 % に減る —— 既定は 1.1。
さらに組ごとに正規化した中央値の検査(pivops.piv_outlier_mask、しきい値 ``outlier_threshold``、None で掛けない)で
外れた窓を欠測にしてから平均する。pivops の注意どおり、急な勾配(障害物の肩)を外れと呼ばないよう慣行の 2 より緩い 3。pivops の成分 (dy, dx) [px/コマ] を u = dx·res/Δt、v = −dy·res/Δt に直す。

Returns:
    速度場の dict + ``valid_fraction``(窓のうち測れた割合)、``n_pairs``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_swarm_obstacle_from_flow](../../../../examples/poc_swarm_obstacle_from_flow.py) — `py -3.11 examples/poc_swarm_obstacle_from_flow.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`swarmflow`)

[sph_kernel](sph_kernel.md) · [sph_density_pressure](sph_density_pressure.md) · [swarm_simulate](swarm_simulate.md) · [swarm_render_overhead](swarm_render_overhead.md) · [swarm_field_from_tracks](swarm_field_from_tracks.md) · [potential_flow_cylinder](potential_flow_cylinder.md) · [velocity_deficit_map](velocity_deficit_map.md) · [stagnation_from_centerline](stagnation_from_centerline.md)

---
*Provenance: swarmflow.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
