---
op: swarm_render_overhead
dim: drive
category: swarmflow
in: matrix × any × scalar
out: image2d
examples: [poc_swarm_obstacle_from_flow]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# swarm_render_overhead — DRIVE `swarmflow` op

- **データ種**: `matrix × any × scalar` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.swarm_render_overhead(points, shape, res: 'float', center=(0.0, 0.0), diameter_px: 'float' = 3.0, intensity: 'float' = 1.0, background: 'float' = 0.0) -> 'np.ndarray'` (実装を直接呼ぶなら `import swarmflow; swarmflow.swarm_render_overhead(points, shape, res: 'float', center=(0.0, 0.0), diameter_px: 'float' = 3.0, intensity: 'float' = 1.0, background: 'float' = 0.0) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("swarm_render_overhead")`)

## 使い方

個体の位置 → 上から見た 1 コマ(ガウスの輝点、直径 = 標準偏差の 2 倍 = PIV の慣行、pivops と同じ)。

Args:
    points: (N, 2) の位置 [m] (空でもよい = 背景だけ)。
    shape: (H, W) [px]。
    res: 画素の大きさ [m/px]。
    center: 画像の中心の世界座標 [m]。
    diameter_px: 輝点の直径 [px]。
    intensity: 輝点の明るさ。
    background: 一様な下駄。
Returns:
    (H, W) float64。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_swarm_obstacle_from_flow](../../../../examples/poc_swarm_obstacle_from_flow.py) — `py -3.11 examples/poc_swarm_obstacle_from_flow.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[flow_from_depth_motion](../ttc/flow_from_depth_motion.md) · [ttc_truth](../ttc/ttc_truth.md) · [ttc_from_flow](../ttc/ttc_from_flow.md) · [foe_from_flow](../ttc/foe_from_flow.md) · [perlin2](../terrain/perlin2.md) · [fbm_height](../terrain/fbm_height.md) · [fbm_gradient](../terrain/fbm_gradient.md) · [radial_periodogram](../terrain/radial_periodogram.md)

## 同カテゴリ(`swarmflow`)

[sph_kernel](sph_kernel.md) · [sph_density_pressure](sph_density_pressure.md) · [swarm_simulate](swarm_simulate.md) · [swarm_field_from_tracks](swarm_field_from_tracks.md) · [swarm_field_from_piv](swarm_field_from_piv.md) · [potential_flow_cylinder](potential_flow_cylinder.md) · [velocity_deficit_map](velocity_deficit_map.md) · [stagnation_from_centerline](stagnation_from_centerline.md)

---
*Provenance: swarmflow.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
