---
op: label_components
dim: 3d
category: regionprops
in: voxel
out: labels
examples: [region_props_3d, watershed3d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# label_components — 3D `regionprops` op

- **データ種**: `voxel` → `labels`
- **呼び出し**: `import regionprops3d; regionprops3d.label_components(vol, connectivity: 'int' = 26)` (または `ops3d.get("label_components")`)
- **台帳経由の戻り値**: `fullseye.ledger.label_components(...)` は**宣言 out 型 `labels` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.label_components.raw(...)`、または `regionprops3d.label_components` を直接呼ぶ。
  - 本体の返り: `(labels, n) → labels`

## 使い方

3D 二値ボリュームを連結成分にラベリングする。

Parameters
----------
vol : array_like
    bool または 0/1 の 3D 配列。
connectivity : int
    6(面) / 18(面+辺) / 26(面+辺+角)のいずれか。

Returns
-------
labels : ndarray(int)
    vol と同形状。背景 0、各連結成分に 1..n のラベル。
n : int
    連結成分数。

補足:
- 入力は ``astype(bool)`` で二値化する。0 以外はすべて前景で、float の NaN も True(前景)になる点に注意。
- 軸順は (z, y, x) = numpy の配列軸順。``labels`` の dtype は ``scipy.ndimage.label`` の返す整数型(通常 int32)。前景が無い/空配列なら int32 のゼロ配列と 0 を返す。
- ラベル番号の付与順は scipy の走査順で、体積順ではない。
- Raises ``ValueError``: 3 次元でない入力、``connectivity`` が 6/18/26 以外。
- 接触している物体は 1 成分に融合する。分離が要るなら前段で ``morph_erode3d`` / ``morph_open3d`` や ``vol_watershed`` で切る。
- 後段: ``region_props``(計測)、``largest_component`` / ``filter_by_volume``(選別)、``vol_select_labels``(特徴でふるい)、``vol_colorize_labels``(可視化)。

## 背景知識ガイド(この op の手前にある物理・規約)

- [measurement_uncertainty](../../math/guides/measurement_uncertainty.md) — 計測の不確かさと校正の知識 — 「測れている」を主張するために

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [region_props_3d](../../../../examples_3d/region_props_3d.py) — `py -3.11 examples_3d/region_props_3d.py`
- [watershed3d](../../../../examples_3d/watershed3d.py) — `py -3.11 examples_3d/watershed3d.py`

## 型が繋がる次の op(`labels` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [vol_region_props](vol_region_props.md)

## 同カテゴリ(`regionprops`)

[region_props](region_props.md) · [largest_component](largest_component.md) · [filter_by_volume](filter_by_volume.md) · [inner_box3](inner_box3.md) · [vol_label](vol_label.md) · [vol_region_props](vol_region_props.md)

---
*Provenance: regionprops3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
