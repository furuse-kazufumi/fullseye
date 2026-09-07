---
op: vol_rle_centroid
dim: 3d
category: rle_region
in: rle_region
out: position
examples: [rle_region_efficiency]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# vol_rle_centroid — 3D `rle_region` op

- **データ種**: `rle_region` → `position`
- **呼び出し**: `import fullseye as fs; fs.ledger.vol_rle_centroid(region, spacing=None)` (実装を直接呼ぶなら `import volregion; volregion.vol_rle_centroid(region, spacing=None)`、台帳から引くなら `ops3d.get("vol_rle_centroid")`)

## 使い方

Centroid ``(z, y, x)`` of the region, computed on the runs (no decode).

Each run contributes ``n`` voxels at its row's ``(z, y)`` and mean x
``(start + end - 1) / 2`` — the exact arithmetic mean of the member voxel
indices, so it matches the dense centroid to floating-point accuracy.
Pass *spacing* ``(sz, sy, sx)`` for physical coordinates. An empty region
raises ``ValueError``.

返り値: ``(z, y, x)`` の 3 つの ``float``(depth, row, col 順)。``spacing`` 無しなら
voxel index 単位(index の算術平均そのもの)、``spacing`` を渡すと各成分に
``(sz, sy, sx)`` を掛けた物理座標(mm など、spacing と同じ単位)。``spacing`` は
長さ 3 の正の有限値、または ``spacing_mm`` 属性を持つ ``volio.VolumeMeta``。

検証(``ValueError``): ``VolRLE`` の整合性検査 / run が 0 本 / ``spacing`` が
長さ 3 でない・非正・非有限。

注意: 質量中心ではなく voxel の幾何重心(全 voxel 等重み)。gray 値で重み付けした
重心が欲しい場合は ``vol_rle_decode`` してから自分で計算する。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [rle_region_efficiency](../../../../examples_3d/rle_region_efficiency.py) — `py -3.11 examples_3d/rle_region_efficiency.py`

## 型が繋がる次の op(`position` を入力に取れる)

[refine_peak_newton](../refine/refine_peak_newton.md) · [refine_translation_lk](../refine/refine_translation_lk.md) · [refine_lm](../refine/refine_lm.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`rle_region`)

[vol_rle_encode](vol_rle_encode.md) · [vol_rle_decode](vol_rle_decode.md) · [vol_rle_volume](vol_rle_volume.md) · [vol_rle_bbox](vol_rle_bbox.md) · [vol_rle_union](vol_rle_union.md) · [vol_rle_intersect](vol_rle_intersect.md) · [vol_rle_difference](vol_rle_difference.md) · [vol_rle_components](vol_rle_components.md)

---
*Provenance: volregion.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
