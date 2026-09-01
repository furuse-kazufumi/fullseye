---
op: scene_flow_lk
dim: 3d
category: motion
in: voxel × voxel
out: flow_dense
gpu: true
examples: [motion_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# scene_flow_lk — 3D `motion` op

- **データ種**: `voxel × voxel` → `flow_dense`
- **呼び出し**: `import match3d; match3d.scene_flow_lk(vol0, vol1, device='cpu', win=3, levels=3, iters=3, reg=0.001)` (または `ops3d.get("scene_flow_lk")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

Lucas-Kanade scene flow(2D optical flow の 3D 版)。voxel ごとの運動場 d=(dz,dy,dx)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [motion_scene](../../../../examples_3d/motion_scene.py) — `py -3.11 examples_3d/motion_scene.py`

## 型が繋がる次の op(`flow_dense` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`motion`)

—

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
