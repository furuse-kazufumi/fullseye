---
op: region_props
dim: 3d
category: regionprops
in: voxel
out: table
examples: [region_props_3d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# region_props — 3D `regionprops` op

- **データ種**: `voxel` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.region_props(vol, connectivity: 'int' = 26) -> 'list[dict]'` (実装を直接呼ぶなら `import regionprops3d; regionprops3d.region_props(vol, connectivity: 'int' = 26) -> 'list[dict]'`、台帳から引くなら `ops3d.get("region_props")`)

## 使い方

各連結成分のリージョンプロパティ一覧を返す。

Parameters
----------
vol : array_like
    bool または 0/1 の 3D 配列。
connectivity : int
    6 / 18 / 26。

Returns
-------
list[dict]
    成分ごとの dict。キー:
      - ``label``           : ラベル番号 (int)
      - ``volume``          : ボクセル数 (int)
      - ``centroid``        : 重心 (z, y, x) の tuple(float)
      - ``bbox``            : (z0, y0, x0, z1, y1, x1)。z1/y1/x1 は排他的上端(stop)
      - ``extent``          : volume / bbox 体積(充填率、0..1)
      - ``principal_axes``  : (3,3) 主軸ベクトル(行、固有値降順)
      - ``principal_lengths``: (3,) 主軸長 = 座標共分散固有値の平方根(降順)
      - ``equivalent_radius``: 等価球半径 (3V/4π)^(1/3)
      - ``surface_area``    : 露出面カウント近似(ボクセル面単位)
      - ``sphericity``      : 等体積球表面積 / 実表面積(球=1 に近い、離散のため <1)

    前景ボクセルが無い(または空入力)場合は空リスト。

補足:
- 全量はボクセル単位(スペーシング補正なし)。実寸が要るなら ``volume`` に voxel 体積、``centroid`` / ``bbox`` / ``principal_lengths`` に各軸のスペーシングを掛ける(非等方だと主軸方向は歪む)。
- ``principal_lengths`` は座標の母共分散(N で割る)の固有値の平方根で、成分の半径ではなく座標の標準偏差。1 ボクセルの成分は ``principal_axes`` が単位行列、``principal_lengths`` が全 0。
- ``surface_area`` は配列端に接する面も数える(ゼロ padding)。``sphericity`` は離散化のため球でも約 0.66 が上限(モジュール docstring 参照)。
- ラベルは 1..n の順(``label_components`` と同じ scipy の走査順)で、体積順ではない。並べ替えは呼び手で行う。
- 入力は 0 以外を前景として bool 化する(NaN も前景)。Raises ``ValueError``: 3 次元でない入力、``connectivity`` が 6/18/26 以外。

## 背景知識ガイド(この op の手前にある物理・規約)

- [measurement_uncertainty](../../math/guides/measurement_uncertainty.md) — 計測の不確かさと校正の知識 — 「測れている」を主張するために

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [region_props_3d](../../../../examples_3d/region_props_3d.py) — `py -3.11 examples_3d/region_props_3d.py`

## 型が繋がる次の op(`table` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [mesh_select_lod](../resolution/mesh_select_lod.md)

## 同カテゴリ(`regionprops`)

[label_components](label_components.md) · [largest_component](largest_component.md) · [filter_by_volume](filter_by_volume.md) · [inner_box3](inner_box3.md) · [vol_label](vol_label.md) · [vol_region_props](vol_region_props.md)

---
*Provenance: regionprops3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
