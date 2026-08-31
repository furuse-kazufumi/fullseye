---
op: region_props
dim: 3d
category: regionprops
in: voxel
out: table
examples: [region_props_3d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# region_props — 3D `regionprops` op

- **データ種**: `voxel` → `table`
- **呼び出し**: `import regionprops3d; regionprops3d.region_props(vol, connectivity: 'int' = 26) -> 'list[dict]'` (または `ops3d.get("region_props")`)

## 使い方

各連結成分のリージョンプロパティ一覧を返す。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [region_props_3d](../../../../examples_3d/region_props_3d.py) — `py -3.11 examples_3d/region_props_3d.py`

## 型が繋がる次の op(`table` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`regionprops`)

[label_components](label_components.md) · [largest_component](largest_component.md) · [filter_by_volume](filter_by_volume.md) · [inner_box3](inner_box3.md) · [vol_label](vol_label.md) · [vol_region_props](vol_region_props.md)

---
*Provenance: regionprops3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
