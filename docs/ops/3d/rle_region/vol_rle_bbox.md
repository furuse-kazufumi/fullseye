---
op: vol_rle_bbox
dim: 3d
category: rle_region
in: rle_region
out: primitive
examples: [rle_region_efficiency]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# vol_rle_bbox — 3D `rle_region` op

- **データ種**: `rle_region` → `primitive`
- **呼び出し**: `import fullseye as fs; fs.ledger.vol_rle_bbox(region)` (実装を直接呼ぶなら `import volregion; volregion.vol_rle_bbox(region)`、台帳から引くなら `ops3d.get("vol_rle_bbox")`)

## 使い方

Tight bounding box ``(z0, y0, x0, z1, y1, x1)`` (exclusive upper bounds)

computed on the runs (no decode; measured ~1000x faster than scanning the
dense mask). Matches ``volops.vol_bounding_box`` of the decoded mask
exactly. An empty region raises ``ValueError`` (same fail-closed rule).

計算: ``z = rows // H``、``y = rows % H`` を復元し、``(z.min, y.min, starts.min,
z.max+1, y.max+1, ends.max)`` を返す。6 要素の ``int`` タプルで、軸順は
``(z, y, x)`` = (depth, row, col)。上限は排他的なので
``vol[z0:z1, y0:y1, x0:x1]`` がそのまま最小の外接部分 volume になる。
座標は voxel index(spacing は掛けない)。

検証: ``VolRLE`` の整合性検査(``_require_rle``)に加え、run が 1 本もない region は
「箱が定義できない」として ``ValueError``。``margin`` 引数は無い
(余白が要るなら ``vol_bounding_box`` を decode 後に使う)。

使いどころ: ``vol_rle_components`` の各成分の箱を取り、``vol_crop_domain`` 相当の
ROI 切り出しを密配列を作らずに決める。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [rle_region_efficiency](../../../../examples_3d/rle_region_efficiency.py) — `py -3.11 examples_3d/rle_region_efficiency.py`

## 型が繋がる次の op(`primitive` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [angle_between_lines](../geometry/angle_between_lines.md) · [angle_between_planes](../geometry/angle_between_planes.md) · [angle_line_plane](../geometry/angle_line_plane.md) · [distance_point_plane](../geometry/distance_point_plane.md) · [distance_point_line](../geometry/distance_point_line.md) · [distance_line_line](../geometry/distance_line_line.md) · [intersect_line_plane](../geometry/intersect_line_plane.md)

## 同カテゴリ(`rle_region`)

[vol_rle_encode](vol_rle_encode.md) · [vol_rle_decode](vol_rle_decode.md) · [vol_rle_volume](vol_rle_volume.md) · [vol_rle_centroid](vol_rle_centroid.md) · [vol_rle_union](vol_rle_union.md) · [vol_rle_intersect](vol_rle_intersect.md) · [vol_rle_difference](vol_rle_difference.md) · [vol_rle_components](vol_rle_components.md)

---
*Provenance: volregion.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
