---
op: removal_depth_from_heights
dim: drive
category: polish
in: image2d × image2d
out: image2d
examples: [poc_polish_wipe_measure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# removal_depth_from_heights — DRIVE `polish` op

- **データ種**: `image2d × image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.removal_depth_from_heights(z_before, z_after, ref_mask=None, frame: 'float' = 0.1) -> 'np.ndarray'` (実装を直接呼ぶなら `import polish; polish.removal_depth_from_heights(z_before, z_after, ref_mask=None, frame: 'float' = 0.1) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("removal_depth_from_heights")`)

## 使い方

磨く前と後の高さ図(同じ格子に置かれていること)から削れた深さ [高さの単位、正 = 削れた]。後の図は載せ直しで傾きと高さが
変わるので、差 z_before − z_after から「触れていない所」(``ref_mask``、無ければ外周の ``frame`` の割合の枠)で最小二乗の平面を
引く。**Raises** ValueError: 形が違う・2-D でない・非有限、参照の画素が 3 未満、frame が (0, 0.5) の外。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_polish_wipe_measure](../../../../examples/poc_polish_wipe_measure.py) — `py -3.11 examples/poc_polish_wipe_measure.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[flow_from_depth_motion](../ttc/flow_from_depth_motion.md) · [ttc_truth](../ttc/ttc_truth.md) · [ttc_from_flow](../ttc/ttc_from_flow.md) · [foe_from_flow](../ttc/foe_from_flow.md) · [perlin2](../terrain/perlin2.md) · [fbm_height](../terrain/fbm_height.md) · [fbm_gradient](../terrain/fbm_gradient.md) · [radial_periodogram](../terrain/radial_periodogram.md)

## 同カテゴリ(`polish`)

[preston_pressure_kernel](preston_pressure_kernel.md) · [preston_removal_map](preston_removal_map.md) · [preston_track_profile](preston_track_profile.md) · [wipe_band_width](wipe_band_width.md) · [raster_wipe_area](raster_wipe_area.md) · [coat_image](coat_image.md) · [coat_thickness_from_image](coat_thickness_from_image.md) · [wipe_coverage](wipe_coverage.md)

---
*Provenance: polish.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
