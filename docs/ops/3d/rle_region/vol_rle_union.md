---
op: vol_rle_union
dim: 3d
category: rle_region
in: rle_region × rle_region
out: rle_region
examples: [rle_region_efficiency]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# vol_rle_union — 3D `rle_region` op

- **データ種**: `rle_region × rle_region` → `rle_region`
- **呼び出し**: `import volregion; volregion.vol_rle_union(a, b)` (または `ops3d.get("vol_rle_union")`)

## 使い方

Union of two RLE regions, computed on the runs (no decode). Cost scales

with the run counts, not the voxel counts — merging two 512**3 masks never
touches 512**3 anything. Regions must share the same volume shape.

手順(``_rle_boolean`` 共通): 両 region の run を、平面行ごとに ``W + 1`` の
stride を取った 1 本の整数直線に写し(+1 の隙間で隣の行の run が結合しない)、
各 run の start/end をイベントとして並べ、区間ごとの被覆状態 ``(a の内側, b の内側)``
を掃引して ``ia | ib`` が真の区間を最大長の run にまとめ直す。計算量は run 数
``n`` に対して O(n log n)(``np.unique`` のソート)。

返り値: 同じ ``shape`` の新しい ``VolRLE``(run は行順・x 昇順、隣接・重複する run は
1 本に併合済み)。両方が空なら run 0 本の region。
``vol_rle_decode(union) == decode(a) | decode(b)`` が voxel 単位で成り立つ。

検証(``ValueError``): どちらかが ``VolRLE`` でない・整合性検査に失敗 /
``a.shape != b.shape``(別の volume に住む region は合成できない)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [rle_region_efficiency](../../../../examples_3d/rle_region_efficiency.py) — `py -3.11 examples_3d/rle_region_efficiency.py`

## 型が繋がる次の op(`rle_region` を入力に取れる)

[vol_rle_decode](vol_rle_decode.md) · [vol_rle_volume](vol_rle_volume.md) · [vol_rle_bbox](vol_rle_bbox.md) · [vol_rle_centroid](vol_rle_centroid.md) · [vol_rle_intersect](vol_rle_intersect.md) · [vol_rle_difference](vol_rle_difference.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`rle_region`)

[vol_rle_encode](vol_rle_encode.md) · [vol_rle_decode](vol_rle_decode.md) · [vol_rle_volume](vol_rle_volume.md) · [vol_rle_bbox](vol_rle_bbox.md) · [vol_rle_centroid](vol_rle_centroid.md) · [vol_rle_intersect](vol_rle_intersect.md) · [vol_rle_difference](vol_rle_difference.md) · [vol_rle_components](vol_rle_components.md)

---
*Provenance: volregion.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
