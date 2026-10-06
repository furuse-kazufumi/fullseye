---
op: carla_label_unmap
dim: drive
category: carla
in: image2d
out: image2d
examples: [poc_carla_bridge]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# carla_label_unmap — DRIVE `carla` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.carla_label_unmap(label) -> 'np.ndarray'` (実装を直接呼ぶなら `import carlabridge; carlabridge.carla_label_unmap(label) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("carla_label_unmap")`)

## 使い方

Fullseye のラベル像 → CARLA のタグ像(uint8、代表タグ)。:func:`carla_label_map` の逆(ラベル側で恒等)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_carla_bridge](../../../../examples/poc_carla_bridge.py) — `py -3.11 examples/poc_carla_bridge.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[flow_from_depth_motion](../ttc/flow_from_depth_motion.md) · [ttc_truth](../ttc/ttc_truth.md) · [ttc_from_flow](../ttc/ttc_from_flow.md) · [foe_from_flow](../ttc/foe_from_flow.md) · [perlin2](../terrain/perlin2.md) · [fbm_height](../terrain/fbm_height.md) · [fbm_gradient](../terrain/fbm_gradient.md) · [radial_periodogram](../terrain/radial_periodogram.md)

## 同カテゴリ(`carla`)

[carla_labels](carla_labels.md) · [carla_label_map](carla_label_map.md) · [carla_depth_decode](carla_depth_decode.md) · [carla_depth_encode](carla_depth_encode.md) · [carla_intrinsics](carla_intrinsics.md) · [intrinsics_to_fullseye](intrinsics_to_fullseye.md) · [intrinsics_to_carla](intrinsics_to_carla.md) · [carla_rotation_matrix](carla_rotation_matrix.md)

---
*Provenance: carlabridge.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
