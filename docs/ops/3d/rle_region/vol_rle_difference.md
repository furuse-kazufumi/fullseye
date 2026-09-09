---
op: vol_rle_difference
dim: 3d
category: rle_region
in: rle_region × rle_region
out: rle_region
examples: [rle_region_efficiency]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# vol_rle_difference — 3D `rle_region` op

- **データ種**: `rle_region × rle_region` → `rle_region`
- **呼び出し**: `import fullseye as fs; fs.ledger.vol_rle_difference(a, b)` (実装を直接呼ぶなら `import volregion; volregion.vol_rle_difference(a, b)`、台帳から引くなら `ops3d.get("vol_rle_difference")`)

## 使い方

Set difference ``a \ b`` on the runs (no decode).

``a`` に含まれ ``b`` に含まれない voxel の region。掃引エンジン(``_rle_boolean``)
で区間ごとの被覆状態が ``ia & ~ib`` の区間を run として残す。非可換
(``vol_rle_difference(a, b) != vol_rle_difference(b, a)``)。計算量は run 数に
対して O(n log n)。

返り値: 同じ ``shape`` の新しい ``VolRLE``。``a`` が ``b`` に完全に含まれていれば
run 0 本の region。``vol_rle_decode(result) == decode(a) & ~decode(b)`` が
voxel 単位で成り立つ。

検証(``ValueError``): どちらかが ``VolRLE`` でない・run 配列の整合性検査に失敗 /
``a.shape != b.shape``。

使いどころ: 全体マスクから ROI 外や既知の成分(``vol_rle_components`` の 1 つ)を
取り除く、``vol_rle_encode(mask)`` と erode 結果の差で殻を作る、といった
「引き算」を密配列を作らずに行う。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [rle_region_efficiency](../../../../examples_3d/rle_region_efficiency.py) — `py -3.11 examples_3d/rle_region_efficiency.py`

## 型が繋がる次の op(`rle_region` を入力に取れる)

[vol_rle_decode](vol_rle_decode.md) · [vol_rle_volume](vol_rle_volume.md) · [vol_rle_bbox](vol_rle_bbox.md) · [vol_rle_centroid](vol_rle_centroid.md) · [vol_rle_union](vol_rle_union.md) · [vol_rle_intersect](vol_rle_intersect.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`rle_region`)

[vol_rle_encode](vol_rle_encode.md) · [vol_rle_decode](vol_rle_decode.md) · [vol_rle_volume](vol_rle_volume.md) · [vol_rle_bbox](vol_rle_bbox.md) · [vol_rle_centroid](vol_rle_centroid.md) · [vol_rle_union](vol_rle_union.md) · [vol_rle_intersect](vol_rle_intersect.md) · [vol_rle_components](vol_rle_components.md)

---
*Provenance: volregion.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
