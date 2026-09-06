---
op: morph_dilate3d
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

# morph_dilate3d — 3D `morphology` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import match3d; match3d.morph_dilate3d(vol, r=1, device='cpu', se='cube')` (または `ops3d.get("morph_dilate3d")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

3D グレースケール dilation(SE 半径 r の局所 max)。明領域を膨張。

se="cube"(既定、torch 経路で GPU 可)/ "ball"(等方 SE、scipy 経路)。

SE は一辺 ``2r+1`` の立方体(cube)か ``z²+y²+x² <= r²`` の球(ball)。``r=0`` は恒等。
境界の外は −∞ 扱い(画像内の値だけで max を取る。torch の ``max_pool3d`` の implicit
padding と scipy の ``cval=-inf`` で同じ結果)。cube は torch があれば ``max_pool3d``
(``device`` 有効)、ball または torch 不在なら ``scipy.ndimage.grey_dilation``(``device`` は
無視)。入力は float32 に変換され、返り値 ``(D,H,W)`` float32 numpy。``se`` がその 2 つ以外なら
ValueError。2 値 volume(0/1)ならそのまま 2 値 dilation になる。``se="ball"`` は r が
大きいと footprint 走査で遅い。
後段: ``morph_erode3d`` と組で ``morph_open3d`` / ``morph_close3d`` / ``morph_gradient3d``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [morphology_3d](../../../../examples_3d/morphology_3d.py) — `py -3.11 examples_3d/morphology_3d.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`morphology`)

[morph_erode3d](morph_erode3d.md) · [morph_open3d](morph_open3d.md) · [morph_close3d](morph_close3d.md) · [morph_gradient3d](morph_gradient3d.md) · [morph_tophat3d](morph_tophat3d.md) · [morph_blackhat3d](morph_blackhat3d.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
