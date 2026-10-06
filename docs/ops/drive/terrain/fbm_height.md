---
op: fbm_height
dim: drive
category: terrain
in: image2d × image2d × table
out: image2d
examples: [poc_rover_slip_risk_path, poc_world_terrain]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# fbm_height — DRIVE `terrain` op

- **データ種**: `image2d × image2d × table` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.fbm_height(x, y, p: 'dict') -> 'np.ndarray'` (実装を直接呼ぶなら `import driveterrain; driveterrain.fbm_height(x, y, p: 'dict') -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("fbm_height")`)

## 使い方

fBm の高さの閉形式: h(x, y) = Σ_k A_k cos(2π f_k (x cosθ_k + y sinθ_k) + φ_k)(表は :func:`fbm_params`)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_rover_slip_risk_path](../../../../examples/poc_rover_slip_risk_path.py) — `py -3.11 examples/poc_rover_slip_risk_path.py`
- [poc_world_terrain](../../../../examples/poc_world_terrain.py) — `py -3.11 examples/poc_world_terrain.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[flow_from_depth_motion](../ttc/flow_from_depth_motion.md) · [ttc_truth](../ttc/ttc_truth.md) · [ttc_from_flow](../ttc/ttc_from_flow.md) · [foe_from_flow](../ttc/foe_from_flow.md) · [perlin2](perlin2.md) · [fbm_gradient](fbm_gradient.md) · [radial_periodogram](radial_periodogram.md) · [spectral_slope](spectral_slope.md)

## 同カテゴリ(`terrain`)

[perlin2](perlin2.md) · [fbm_params](fbm_params.md) · [fbm_gradient](fbm_gradient.md) · [radial_periodogram](radial_periodogram.md) · [spectral_slope](spectral_slope.md) · [course_distance](course_distance.md) · [terrain_params](terrain_params.md) · [terrain_height](terrain_height.md)

---
*Provenance: driveterrain.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
