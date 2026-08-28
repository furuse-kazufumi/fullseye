---
op: match_sh_descriptor
dim: 3d
category: describe
in: voxel × voxel
out: measurement
gpu: true
examples: [sh_descriptor_retrieval, shape_descriptor]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# match_sh_descriptor — 3D `describe` op

- **データ種**: `voxel × voxel` → `measurement`
- **呼び出し**: `import match3d; match3d.match_sh_descriptor(a, b, L=8, nradii=12, device='cpu')` (または `ops3d.get("match_sh_descriptor")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

SH 記述子同士のコサイン類似度(回転不変な形状照合)。1 に近いほど同形状。voxel × SH 列。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sh_descriptor_retrieval](../../../../examples_3d/sh_descriptor_retrieval.py) — `py -3.11 examples_3d/sh_descriptor_retrieval.py`
- [shape_descriptor](../../../../examples_3d/shape_descriptor.py) — `py -3.11 examples_3d/shape_descriptor.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`describe`)

[sh_descriptor](sh_descriptor.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
