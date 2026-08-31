---
op: tps_fit
dim: 3d
category: deform
in: points × points
out: deformation
examples: [nonrigid_deform]
author: Kazufumi Furuse
license: Apache-2.0
version: 0  # fullseye lib version this note was generated for
---

# tps_fit — 3D `deform` op

- **データ種**: `points × points` → `deformation`
- **呼び出し**: `import deform3d; deform3d.tps_fit(src_ctrl, dst_ctrl, lam=0.0)` (または `ops3d.get("tps_fit")`)

## 使い方

3D Thin-Plate-Spline を制御点対応から当てはめる。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [nonrigid_deform](../../../../examples_3d/nonrigid_deform.py) — `py -3.11 examples_3d/nonrigid_deform.py`

## 型が繋がる次の op(`deformation` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [tps_warp](tps_warp.md)

## 同カテゴリ(`deform`)

[tps_warp](tps_warp.md) · [register_nonrigid](register_nonrigid.md) · [register_cpd_rigid](register_cpd_rigid.md)

---
*Provenance: deform3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
