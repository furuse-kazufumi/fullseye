---
op: vol_rle_decode
dim: 3d
category: rle_region
in: rle_region
out: voxel
examples: [rle_region_efficiency]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# vol_rle_decode — 3D `rle_region` op

- **データ種**: `rle_region` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.vol_rle_decode(region) -> 'np.ndarray'` (実装を直接呼ぶなら `import volregion; volregion.vol_rle_decode(region) -> 'np.ndarray'`、台帳から引くなら `ops3d.get("vol_rle_decode")`)

## 使い方

Decode a ``VolRLE`` back to a dense ``(D, H, W)`` float64 ``{0, 1}``

volume. Exact inverse of :func:`vol_rle_encode` (bit-identical round trip).
The region is validated first, so a corrupted RLE raises ``ValueError``
instead of writing out of bounds.

手順: ``(D*H, W+1)`` の int8 累積バッファに各 run の ``start`` へ +1、``end`` へ
-1 を加算(``np.add.at``)し、x 方向の累積和が ``> 0`` の位置を前景にする。
重なる run が渡されても加算で打ち消し合わない(count > 0 なら前景)。

返り値: ``(D, H, W)`` の float64、値は ``0.0`` / ``1.0`` のみ。``shape`` は
``region.shape`` から取るので、元 volume は不要。

検証(``ValueError``): ``VolRLE`` 以外 / ``shape`` が長さ 3 でない・空・
``MAX_VOXELS`` 超 / ``rows``・``starts``・``ends`` の長さ不一致 / 整数 dtype でない /
row id が ``0..D*H-1`` の外 / ``start < 0``、``end > W``、``end <= start`` の run。
手作りや外部から読んだ RLE も、割り当ての前にすべて検査する。

使いどころ: run 上でできない処理(フィルタ・モルフォロジー・``vol_label`` など)の
直前だけ decode し、結果を ``vol_rle_encode`` で戻す。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [rle_region_efficiency](../../../../examples_3d/rle_region_efficiency.py) — `py -3.11 examples_3d/rle_region_efficiency.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`rle_region`)

[vol_rle_encode](vol_rle_encode.md) · [vol_rle_volume](vol_rle_volume.md) · [vol_rle_bbox](vol_rle_bbox.md) · [vol_rle_centroid](vol_rle_centroid.md) · [vol_rle_union](vol_rle_union.md) · [vol_rle_intersect](vol_rle_intersect.md) · [vol_rle_difference](vol_rle_difference.md) · [vol_rle_components](vol_rle_components.md)

---
*Provenance: volregion.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
