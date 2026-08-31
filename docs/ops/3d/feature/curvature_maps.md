---
op: curvature_maps
dim: 3d
category: feature
in: voxel
out: curvature
gpu: true
examples: [diff_features]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# curvature_maps — 3D `feature` op

- **データ種**: `voxel` → `curvature`
- **呼び出し**: `import match3d; match3d.curvature_maps(vol, device='cpu', mc=0.000625)` (または `ops3d.get("curvature_maps")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

level-set の主曲率 → shape index S(Koenderink)と curvedness。閉形式(Kindlmann 2003)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [diff_features](../../../../examples_3d/diff_features.py) — `py -3.11 examples_3d/diff_features.py`

## 型が繋がる次の op(`curvature` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`feature`)

[sobel3d](sobel3d.md) · [hessian3d](hessian3d.md) · [edt_jfa](edt_jfa.md) · [vol_frangi](vol_frangi.md) · [vol_sato](vol_sato.md) · [vol_hessian_blobness](vol_hessian_blobness.md) · [vol_gradient_magnitude](vol_gradient_magnitude.md) · [vol_local_maxima](vol_local_maxima.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
