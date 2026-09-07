---
op: morph_close3d
dim: 3d
category: morphology
in: voxel
out: voxel
gpu: true
examples: [morphology_3d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# morph_close3d — 3D `morphology` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.morph_close3d(vol, r=1, device='cpu', se='cube')` (実装を直接呼ぶなら `import match3d; match3d.morph_close3d(vol, r=1, device='cpu', se='cube')`、台帳から引くなら `ops3d.get("morph_close3d")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

3D closing = dilation → erosion。SE より小さい**暗構造(隙間・空洞)**を埋める。

``morph_erode3d(morph_dilate3d(vol, r, ...), r, ...)``。出力は入力以上(``close >= vol``)で、
SE(一辺 ``2r+1`` の cube か半径 r の ball)より小さい暗い穴・亀裂・面の隙間が周囲の
明るさで埋まり、大きな暗領域は残る(等冪)。境界外は dilation で −∞、erosion で +∞ 扱い
なので端が勝手に埋まることはない。``se`` は "cube"/"ball"(他は ValueError)、``device`` は
cube+torch のときだけ有効。返り値 ``(D,H,W)`` float32 numpy。
用途: ``close − vol`` が ``morph_blackhat3d``(小さな暗構造の抽出)。点群 splat の表面の
穴埋め、``signed_distance_field`` 前の占有の穴埋め。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [morphology_3d](../../../../examples_3d/morphology_3d.py) — `py -3.11 examples_3d/morphology_3d.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`morphology`)

[morph_dilate3d](morph_dilate3d.md) · [morph_erode3d](morph_erode3d.md) · [morph_open3d](morph_open3d.md) · [morph_gradient3d](morph_gradient3d.md) · [morph_tophat3d](morph_tophat3d.md) · [morph_blackhat3d](morph_blackhat3d.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
