---
op: spheres_to_silhouette
dim: drive
category: granular
in: matrix × scalar × scalar × scalar × scalar
out: image2d
examples: [poc_granular_heap_repose, poc_powder_scoop_pour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# spheres_to_silhouette — DRIVE `granular` op

- **データ種**: `matrix × scalar × scalar × scalar × scalar` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.spheres_to_silhouette(pos, radius: 'float', pitch: 'float', extent: 'float', height: 'float', supersample: 'int' = 4) -> 'np.ndarray'` (実装を直接呼ぶなら `import granular; granular.spheres_to_silhouette(pos, radius: 'float', pitch: 'float', extent: 'float', height: 'float', supersample: 'int' = 4) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("spheres_to_silhouette")`)

## 使い方

球の中心列から、横(y 方向)から見た正射影の被覆率画像(円板の和、反エイリアス)。行 0 が上。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_granular_heap_repose](../../../../examples/poc_granular_heap_repose.py) — `py -3.11 examples/poc_granular_heap_repose.py`
- [poc_powder_scoop_pour](../../../../examples/poc_powder_scoop_pour.py) — `py -3.11 examples/poc_powder_scoop_pour.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[flow_from_depth_motion](../ttc/flow_from_depth_motion.md) · [ttc_truth](../ttc/ttc_truth.md) · [ttc_from_flow](../ttc/ttc_from_flow.md) · [foe_from_flow](../ttc/foe_from_flow.md) · [perlin2](../terrain/perlin2.md) · [fbm_height](../terrain/fbm_height.md) · [fbm_gradient](../terrain/fbm_gradient.md) · [radial_periodogram](../terrain/radial_periodogram.md)

## 同カテゴリ(`granular`)

[heap_volume_cone](heap_volume_cone.md) · [heap_mass](heap_mass.md) · [heap_volume_heightmap](heap_volume_heightmap.md) · [beverloo_rate](beverloo_rate.md) · [beverloo_fit](beverloo_fit.md) · [discharge_synth](discharge_synth.md) · [dispense_mass_from_video](dispense_mass_from_video.md) · [hopper_discharge_rate](hopper_discharge_rate.md)

---
*Provenance: granular.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
