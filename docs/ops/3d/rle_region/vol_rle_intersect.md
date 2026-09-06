---
op: vol_rle_intersect
dim: 3d
category: rle_region
in: rle_region × rle_region
out: rle_region
examples: [rle_region_efficiency]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# vol_rle_intersect — 3D `rle_region` op

- **データ種**: `rle_region × rle_region` → `rle_region`
- **呼び出し**: `import volregion; volregion.vol_rle_intersect(a, b)` (または `ops3d.get("vol_rle_intersect")`)

## 使い方

Intersection of two RLE regions on the runs (no decode).

``vol_rle_union`` と同じ掃引エンジン(``_rle_boolean``)で、区間ごとの被覆状態が
``ia & ib``(両方の内側)の区間だけを run として残す。計算量は run 数に対して
O(n log n) で、voxel 数には依存しない。

返り値: 同じ ``shape`` の新しい ``VolRLE``。共通部分が無ければ run 0 本の region
(エラーではない。空かどうかは ``len(region) == 0`` か ``vol_rle_volume`` で見る)。
``vol_rle_decode(result) == decode(a) & decode(b)`` が voxel 単位で成り立つ。

検証(``ValueError``): どちらかが ``VolRLE`` でない・run 配列の整合性検査に失敗 /
``a.shape != b.shape``。

使いどころ: ROI(``vol_rle_encode`` した domain マスク)と成分(``vol_rle_components``)
の重なり判定、2 つの閾値結果の共通領域、``vol_rle_volume`` と組み合わせた
IoU 計算(``|a∩b| / |a∪b|``)を密配列なしで行う。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [rle_region_efficiency](../../../../examples_3d/rle_region_efficiency.py) — `py -3.11 examples_3d/rle_region_efficiency.py`

## 型が繋がる次の op(`rle_region` を入力に取れる)

[vol_rle_decode](vol_rle_decode.md) · [vol_rle_volume](vol_rle_volume.md) · [vol_rle_bbox](vol_rle_bbox.md) · [vol_rle_centroid](vol_rle_centroid.md) · [vol_rle_union](vol_rle_union.md) · [vol_rle_difference](vol_rle_difference.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`rle_region`)

[vol_rle_encode](vol_rle_encode.md) · [vol_rle_decode](vol_rle_decode.md) · [vol_rle_volume](vol_rle_volume.md) · [vol_rle_bbox](vol_rle_bbox.md) · [vol_rle_centroid](vol_rle_centroid.md) · [vol_rle_union](vol_rle_union.md) · [vol_rle_difference](vol_rle_difference.md) · [vol_rle_components](vol_rle_components.md)

---
*Provenance: volregion.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
