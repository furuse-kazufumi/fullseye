---
op: vol_rle_encode
dim: 3d
category: rle_region
in: voxel
out: rle_region
examples: [rle_region_efficiency]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# vol_rle_encode — 3D `rle_region` op

- **データ種**: `voxel` → `rle_region`
- **呼び出し**: `import volregion; volregion.vol_rle_encode(vol_binary) -> 'VolRLE'` (または `ops3d.get("vol_rle_encode")`)

## 使い方

Encode a binary volume as x-runs (the 3-D HALCON-region representation).

A non-``{0, 1}`` input is thresholded at ``> 0.5`` (the :mod:`volops`
convention). NaN / Inf are rejected. An empty mask encodes to zero runs —
a valid region that decodes back to all-background.

Memory: proportional to the number of runs (~surface complexity per plane
row), not to the voxel count — measured 1/145 of the dense bool mask on a
realistic 384**3 part.

何を作るか: ``(D, H, W)`` のバイナリ volume を、x 軸(最終軸)方向の連続前景区間
(run)の列に変換する。``VolRLE`` は ``rows``(平面行 id ``z*H + y``、int32、昇順)、
``starts`` / ``ends``(run の x 範囲 ``[start, end)``、end は排他的)、``shape``
(元の ``(D, H, W)``)を持つ frozen dataclass。run ``i`` は
``vol[z, y, starts[i]:ends[i]]`` を表す。

引数と検証(fail-closed):
- ``vol_binary``: 3-D 配列。bool ならそのまま、それ以外は float64 に変換して
  NaN/Inf があれば ``ValueError``、``> 0.5`` で二値化する。
- 3-D でない、または voxel 数が ``MAX_VOXELS``(``1 << 27`` ≈ 1.34 億)を超えると
  ``ValueError``。
- 空マスクは run 数 0 の ``VolRLE`` になる(エラーではない)。

注意: 軸順は ``[z, y, x]``(depth, row, col)。run は x 方向にしか走らないので、
x 方向に細かく途切れる形状(縞・ノイズ)ほど run 数が増え、圧縮の利点は減る。
``vol_rle_volume`` / ``vol_rle_bbox`` / ``vol_rle_centroid`` は decode せずに
run 上で答える。集合演算は ``vol_rle_union`` / ``vol_rle_intersect`` /
``vol_rle_difference``、密配列へ戻すのは ``vol_rle_decode``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [rle_region_efficiency](../../../../examples_3d/rle_region_efficiency.py) — `py -3.11 examples_3d/rle_region_efficiency.py`

## 型が繋がる次の op(`rle_region` を入力に取れる)

[vol_rle_decode](vol_rle_decode.md) · [vol_rle_volume](vol_rle_volume.md) · [vol_rle_bbox](vol_rle_bbox.md) · [vol_rle_centroid](vol_rle_centroid.md) · [vol_rle_union](vol_rle_union.md) · [vol_rle_intersect](vol_rle_intersect.md) · [vol_rle_difference](vol_rle_difference.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`rle_region`)

[vol_rle_decode](vol_rle_decode.md) · [vol_rle_volume](vol_rle_volume.md) · [vol_rle_bbox](vol_rle_bbox.md) · [vol_rle_centroid](vol_rle_centroid.md) · [vol_rle_union](vol_rle_union.md) · [vol_rle_intersect](vol_rle_intersect.md) · [vol_rle_difference](vol_rle_difference.md) · [vol_rle_components](vol_rle_components.md)

---
*Provenance: volregion.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
