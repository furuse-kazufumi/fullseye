---
op: vol_profile_line
dim: 3d
category: probe
in: voxel
out: pairs
examples: [wall_thickness_probe]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# vol_profile_line — 3D `probe` op

- **データ種**: `voxel` → `pairs`
- **呼び出し**: `import volprobe; volprobe.vol_profile_line(vol, p0, p1, n=None, spacing=None, order=1)` (または `ops3d.get("vol_profile_line")`)

## 使い方

Gray-value profile along the straight probe ``p0 -> p1``.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [wall_thickness_probe](../../../../examples_3d/wall_thickness_probe.py) — `py -3.11 examples_3d/wall_thickness_probe.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`probe`)

[vol_edge_probe](vol_edge_probe.md) · [vol_wall_thickness](vol_wall_thickness.md)

---
*Provenance: volprobe.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
