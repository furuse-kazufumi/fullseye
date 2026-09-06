---
op: inner_box3
dim: 3d
category: regionprops
in: voxel
out: primitive
examples: [inner_box_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# inner_box3 — 3D `regionprops` op

- **データ種**: `voxel` → `primitive`
- **呼び出し**: `import regionprops3d; regionprops3d.inner_box3(vol) -> 'dict'` (または `ops3d.get("inner_box3")`)

## 使い方

二値ボクセル領域に完全に内接する最大の軸平行ボックス(2-D ``inner_rectangle1`` の

3-D 版)。

厳密解: どの深さ区間 [z0, z1] についても、ボックスはスライス z0..z1 の **論理積**
(全スライスで前景のボクセル)の内側に無ければならない。その積の中の最大内接 2-D 長方形
(ヒストグラム法 = ``inner_rectangle1`` と同じコア)× 区間長 が候補ボックスで、全区間に
ついての最大が厳密な最大内接ボックスになる。O(D^2 * H * W)。

Returns
-------
dict
    (depth,row,col) 軸順で ``min`` / ``max`` 隅、``center`` (+ ``cd/cr/cc``)、
    全幅 ``size``、ボクセル数の ``volume``。

Raises
------
ValueError
    非 3-D 入力、または前景ゼロの領域(内接ボックス無し)。

補足:
- ``min`` / ``max`` は **両端を含む** ボクセル添字(float 配列)。``size = max - min + 1``、``volume = prod(size)``。``center`` は ``(min + max) / 2`` で .5 が付き得る。2-D 側の登録名は ``r2_inner_rectangle1``。
- 深さ区間ごとに Python ループで最大長方形を探す O(D²·H·W)。積が空になった時点でその z0 の探索は打ち切る。大きなボリュームでは遅い。
- 同体積の候補が複数あるときは先に見つかったもの(z0 が小さく、その中で z1 が小さい)を返す。
- 入力は 0 以外を前景として bool 化する(NaN も前景)。軸順は (depth, row, col)。
- 典型: ``largest_component`` で対象を 1 つに絞ってから呼ぶ(複数成分が混ざると最大成分のボックスとは限らない)。

## 背景知識ガイド(この op の手前にある物理・規約)

- [measurement_uncertainty](../../math/guides/measurement_uncertainty.md) — 計測の不確かさと校正の知識 — 「測れている」を主張するために

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [inner_box_inspection](../../../../examples_3d/inner_box_inspection.py) — `py -3.11 examples_3d/inner_box_inspection.py`

## 型が繋がる次の op(`primitive` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [angle_between_lines](../geometry/angle_between_lines.md) · [angle_between_planes](../geometry/angle_between_planes.md) · [angle_line_plane](../geometry/angle_line_plane.md) · [distance_point_plane](../geometry/distance_point_plane.md) · [distance_point_line](../geometry/distance_point_line.md) · [distance_line_line](../geometry/distance_line_line.md) · [intersect_line_plane](../geometry/intersect_line_plane.md)

## 同カテゴリ(`regionprops`)

[label_components](label_components.md) · [region_props](region_props.md) · [largest_component](largest_component.md) · [filter_by_volume](filter_by_volume.md) · [vol_label](vol_label.md) · [vol_region_props](vol_region_props.md)

---
*Provenance: regionprops3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
