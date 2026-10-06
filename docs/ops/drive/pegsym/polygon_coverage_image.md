---
op: polygon_coverage_image
dim: drive
category: pegsym
in: matrix
out: image2d
examples: [poc_peg_symmetry_search]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# polygon_coverage_image — DRIVE `pegsym` op

- **データ種**: `matrix` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.polygon_coverage_image(vertices_px, size: 'int' = 160, ss: 'int' = 8, width: 'int | None' = None) -> 'np.ndarray'` (実装を直接呼ぶなら `import pegsym; pegsym.polygon_coverage_image(vertices_px, size: 'int' = 160, ss: 'int' = 8, width: 'int | None' = None) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("polygon_coverage_image")`)

## 使い方

凸多角形(画素座標 (col, row) の頂点列)の被覆率の像 0..1((size, width)、反エイリアスは ``ss`` × ``ss`` の副標本)。真値つきの
合成の部品。**Raises** ValueError: 凸でない、size < 8、ss < 1。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_symmetry_search](../../../../examples/poc_peg_symmetry_search.py) — `py -3.11 examples/poc_peg_symmetry_search.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[flow_from_depth_motion](../ttc/flow_from_depth_motion.md) · [ttc_truth](../ttc/ttc_truth.md) · [ttc_from_flow](../ttc/ttc_from_flow.md) · [foe_from_flow](../ttc/foe_from_flow.md) · [perlin2](../terrain/perlin2.md) · [fbm_height](../terrain/fbm_height.md) · [fbm_gradient](../terrain/fbm_gradient.md) · [radial_periodogram](../terrain/radial_periodogram.md)

## 同カテゴリ(`pegsym`)

[polygon_peg](polygon_peg.md) · [polygon_offset](polygon_offset.md) · [polygon_fit_check](polygon_fit_check.md) · [rotation_window](rotation_window.md) · [polygon_two_point_depth](polygon_two_point_depth.md) · [plane_topview](plane_topview.md) · [polygon_yaw_read](polygon_yaw_read.md) · [relative_yaw_from_images](relative_yaw_from_images.md)

---
*Provenance: pegsym.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
