---
op: symmetry_difference_map
dim: aoi
category: symmetry
in: image2d × table
out: image2d
examples: [poc_symmetry_self_reference_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# symmetry_difference_map — AOI `symmetry` op

- **データ種**: `image2d × table` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.symmetry_difference_map(image, symmetry, exclusion_mask=None, detrend=True)` (実装を直接呼ぶなら `import symmetry2d; symmetry2d.symmetry_difference_map(image, symmetry, exclusion_mask=None, detrend=True)`、台帳から引くなら `opsaoi.get("symmetry_difference_map")`)

## 使い方

推定した反射軸または回転中心に対する自己参照差分マップを返す。

Parameters
----------
image : array-like, shape (H, W)
    検査するグレー画像。
symmetry : dict
    :func:`reflection_axis` または :func:`rotational_symmetry` の table。
exclusion_mask : array-like or None, default None
    設計上の非対称を除外する H x W mask。True 部とその変換先をともに 0 にする。
detrend : bool, default True
    True なら符号付き差から頑健な一次面を引き、線形な照明勾配を抑える。

Returns
-------
numpy.ndarray
    ``abs(image - transformed_image)``。再標本化は線形補間で、最近傍は使わない。

Notes
-----
定数入力、モデル種別不明、mask の形不一致は例外。自己参照なので欠陥は元位置と
対称位置の対で現れ、軸上の欠陥や同じ欠陥が対称位置にもある場合は消える。一次面の
除去は線形照明に限り、急な陰影や飽和は欠陥と区別できない。

## 詳しい使い方ガイド

- [aoi_frontend ファミリ ガイド](../guides/aoi_frontend.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_symmetry_self_reference_inspection](../../../../examples/poc_symmetry_self_reference_inspection.py) — `py -3.11 examples/poc_symmetry_self_reference_inspection.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[flat_field_correct](../photometric/flat_field_correct.md) · [register_image](../geometric/register_image.md) · [tiled_map](../aggregate/tiled_map.md) · [center_from_symmetric_edges](center_from_symmetric_edges.md) · [reflection_axis](reflection_axis.md) · [rotational_symmetry](rotational_symmetry.md) · [symmetry_score](symmetry_score.md)

## 同カテゴリ(`symmetry`)

[center_from_symmetric_edges](center_from_symmetric_edges.md) · [reflection_axis](reflection_axis.md) · [rotational_symmetry](rotational_symmetry.md) · [symmetry_score](symmetry_score.md)

---
*Provenance: symmetry2d.py — AOI operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
