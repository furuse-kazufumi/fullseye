---
op: fit_zernike
dim: 3d
category: curvilinear
in: image2d
out: descriptor
gpu: true
examples: [curvilinear_proj]
author: Kazufumi Furuse
license: Apache-2.0
version: 0  # fullseye lib version this note was generated for
---

# fit_zernike — 3D `curvilinear` op

- **データ種**: `image2d` → `descriptor`
- **呼び出し**: `import match3d; match3d.fit_zernike(disk_image, n_max=6, device='cpu', nr=48, nt=72)` (または `ops3d.get("fit_zernike")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

円板画像 → Zernike 係数(光学/波面計測の**極座標曲面近似**)。返り値 {(n,m): coef}。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [curvilinear_proj](../../../../examples_3d/curvilinear_proj.py) — `py -3.11 examples_3d/curvilinear_proj.py`

## 型が繋がる次の op(`descriptor` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [shape_distance](../shape_descriptor/shape_distance.md)

## 同カテゴリ(`curvilinear`)

[polar_unwrap](polar_unwrap.md) · [cylinder_unwrap](cylinder_unwrap.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
