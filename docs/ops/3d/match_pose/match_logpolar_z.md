---
op: match_logpolar_z
dim: 3d
category: match_pose
in: voxel × voxel
out: rot_scale
gpu: true
examples: [shape_desc_pose]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# match_logpolar_z — 3D `match_pose` op

- **データ種**: `voxel × voxel` → `rot_scale`
- **呼び出し**: `import match3d; match3d.match_logpolar_z(a, b, device='cpu', project='mip', nt=360, nr=192)` (または `ops3d.get("match_logpolar_z")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

log-polar × 位相相関(Fourier-Mellin)で **z 軸回転 + 等方スケール**を復元。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [shape_desc_pose](../../../../examples_3d/shape_desc_pose.py) — `py -3.11 examples_3d/shape_desc_pose.py`

## 型が繋がる次の op(`rot_scale` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`match_pose`)

[match_phase_3d](match_phase_3d.md) · [match_pca](match_pca.md) · [moment_axes](moment_axes.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
