---
op: swarm_field_from_tracks
dim: drive
category: swarmflow
in: any × scalar × scalar
out: table
examples: [poc_swarm_obstacle_from_flow]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# swarm_field_from_tracks — DRIVE `swarmflow` op

- **データ種**: `any × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.swarm_field_from_tracks(frames, res: 'float', frame_dt: 'float', center=(0.0, 0.0), grid_step=None, h=None, threshold: 'float' = 0.3, max_disp_px=None, min_count: 'int' = 3, outlier_k: 'int' = 12, outlier_threshold: 'float' = 3.0) -> 'dict'` (実装を直接呼ぶなら `import swarmflow; swarmflow.swarm_field_from_tracks(frames, res: 'float', frame_dt: 'float', center=(0.0, 0.0), grid_step=None, h=None, threshold: 'float' = 0.3, max_disp_px=None, min_count: 'int' = 3, outlier_k: 'int' = 12, outlier_threshold: 'float' = 3.0) -> 'dict'`、台帳から引くなら `opsdrive.get("swarm_field_from_tracks")`)

## 使い方

俯瞰のコマ列 → 個体を検出(blob2d の連結成分 + 明るさの重心)→ 隣のコマと相互最近傍でつなぐ → 速度を SPH 核で格子へ。

つなぐ条件: A の点の最近傍が B の点で、その B の点の最近傍も A の点(相互)、かつ移動が ``max_disp_px`` 以下
(既定 = 検出した点どうしの最近傍の間隔の中央値の 0.45 倍。1 コマの移動がこれを超えると取り違える = 追跡の限界)。
全部のコマの組の速度を一つの集団にして平均する(定常の流れの前提)。取り違えた組は速度が桁で外れる(実測: 一様に
撒いた 1300 個で 2 % の組が 1〜3 m/s ずれ、格子の rms 誤差が U の 16 % になった)ので、格子へ移す前に**正規化した
中央値の検査**(PIV の慣行、近い ``outlier_k`` 個の速度の中央値からのずれ / その近傍のずれの中央値 > ``outlier_threshold``)
で捨てる。

Args:
    frames: 同じ大きさの (H, W) のコマの列(2 枚以上)。
    res: 画素の大きさ [m/px]。
    frame_dt: コマの間隔 [s]。
    center: 画像の中心の世界座標 [m]。
    grid_step: 格子の間隔 [m] (既定 = 個体の間隔の推定値)。
    h: 格子へ移す核の h [m] (既定 = grid_step)。
    threshold: 2 値化のしきい値(最小〜最大の割合)。
    max_disp_px: 1 コマの移動の上限 [px]。
    min_count: 格子の台の中に要る速度の数。
    outlier_k: 中央値の検査に使う近傍の数(0 で検査しない)。
    outlier_threshold: 検査のしきい値。
Returns:
    速度場の dict(module の規約)+ ``points`` (M, 2)・``point_velocity`` (M, 2)(つないだ組の中点と速度)、
    ``n_detected``(コマごと)、``n_linked``、``n_outliers``(中央値の検査で捨てた組)、``n_rejected_blobs``、
    ``spacing``(個体の間隔の推定 [m])。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_swarm_obstacle_from_flow](../../../../examples/poc_swarm_obstacle_from_flow.py) — `py -3.11 examples/poc_swarm_obstacle_from_flow.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`swarmflow`)

[sph_kernel](sph_kernel.md) · [sph_density_pressure](sph_density_pressure.md) · [swarm_simulate](swarm_simulate.md) · [swarm_render_overhead](swarm_render_overhead.md) · [swarm_field_from_piv](swarm_field_from_piv.md) · [potential_flow_cylinder](potential_flow_cylinder.md) · [velocity_deficit_map](velocity_deficit_map.md) · [stagnation_from_centerline](stagnation_from_centerline.md)

---
*Provenance: swarmflow.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
