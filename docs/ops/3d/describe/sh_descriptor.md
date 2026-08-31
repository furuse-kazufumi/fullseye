---
op: sh_descriptor
dim: 3d
category: describe
in: voxel
out: descriptor
gpu: true
examples: [sh_descriptor_retrieval, shape_descriptor]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# sh_descriptor — 3D `describe` op

- **データ種**: `voxel` → `descriptor`
- **呼び出し**: `import match3d; match3d.sh_descriptor(vol, L=8, nradii=12, ntheta=32, nphi=64, device='cpu')` (または `ops3d.get("sh_descriptor")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

球面調和記述子。同心球 shell の SH 帯域エネルギー ‖f_l(r)‖ を (半径 × 周波数) で返す。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sh_descriptor_retrieval](../../../../examples_3d/sh_descriptor_retrieval.py) — `py -3.11 examples_3d/sh_descriptor_retrieval.py`
- [shape_descriptor](../../../../examples_3d/shape_descriptor.py) — `py -3.11 examples_3d/shape_descriptor.py`

## 型が繋がる次の op(`descriptor` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [shape_distance](../shape_descriptor/shape_distance.md)

## 同カテゴリ(`describe`)

[match_sh_descriptor](match_sh_descriptor.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
