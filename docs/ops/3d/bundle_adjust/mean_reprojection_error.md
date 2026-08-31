---
op: mean_reprojection_error
dim: 3d
category: bundle_adjust
in: pose × points
out: measurement
examples: [bundle_adjust]
author: Kazufumi Furuse
license: Apache-2.0
version: 0  # fullseye lib version this note was generated for
---

# mean_reprojection_error — 3D `bundle_adjust` op

- **データ種**: `pose × points` → `measurement`
- **呼び出し**: `import bundle3d; bundle3d.mean_reprojection_error(cameras, points, obs_cam, obs_pt, obs_uv, K)` (または `ops3d.get("mean_reprojection_error")`)

## 使い方

再投影 RMS 誤差(ピクセル)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [bundle_adjust](../../../../examples_3d/bundle_adjust.py) — `py -3.11 examples_3d/bundle_adjust.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`bundle_adjust`)

[bundle_adjust](bundle_adjust.md) · [project](project.md)

---
*Provenance: bundle3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
