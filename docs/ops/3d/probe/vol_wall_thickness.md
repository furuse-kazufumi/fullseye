---
op: vol_wall_thickness
dim: 3d
category: probe
in: voxel
out: measurement
examples: [wall_thickness_probe]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# vol_wall_thickness — 3D `probe` op

- **データ種**: `voxel` → `measurement`
- **呼び出し**: `import volprobe; volprobe.vol_wall_thickness(vol, p0, p1, sigma=1.0, threshold=0.1, spacing=None)` (または `ops3d.get("vol_wall_thickness")`)

## 使い方

Wall thicknesses along the probe ``p0 -> p1`` — the industrial-CT

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [wall_thickness_probe](../../../../examples_3d/wall_thickness_probe.py) — `py -3.11 examples_3d/wall_thickness_probe.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[vol_gaussian_psf](../restoration/vol_gaussian_psf.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`probe`)

[vol_profile_line](vol_profile_line.md) · [vol_edge_probe](vol_edge_probe.md)

---
*Provenance: volprobe.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
