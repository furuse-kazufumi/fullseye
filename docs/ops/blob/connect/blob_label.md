---
op: blob_label
dim: blob
category: connect
in: mask
out: labels2d
examples: [blob_split_tour, poc_bone_trabecular_thickness, poc_bump_coplanarity, poc_fresco_craquelure, poc_gear_tooth_metrology, poc_leaf_disease_area, poc_machine_condition_fusion, poc_metal_grain_size, poc_nuclei_ploidy, poc_particle_sizing, poc_particle_tracking, poc_pipe_wall_loss, poc_print_warpage_risk, poc_pv_thermal_survey, poc_sea_ice_concentration, poc_solar_el_inspection, poc_solder_fillet_aoi, poc_timelapse_growth, poc_traffic_counting, poc_vessel_network, poc_weld_radiograph_porosity, poc_wound_area_tracking]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# blob_label — BLOB `connect` op

- **データ種**: `mask` → `labels2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.blob_label(region: 'Any', connectivity: 'int' = 8) -> 'np.ndarray'` (実装を直接呼ぶなら `import blob2d; blob2d.blob_label(region: 'Any', connectivity: 'int' = 8) -> 'np.ndarray'`、台帳から引くなら `opsblob.get("blob_label")`)

## 使い方

二値領域を連結成分に分け、``int32`` のラベル画像(背景 0、物体 1..n)を返す。

Parameters
----------
region : array_like
    2-D。``> 0`` が前景(bool でも実数でもよい。NaN は背景)。
connectivity : {4, 8}
    斜めに触れる 2 画素をつなぐか。既定 8 は ``ndimage.label`` と
    HALCON ``connection`` の既定に一致する。**4 にすると斜めに接した塊が
    別々に数えられる**。

Returns
-------
numpy.ndarray
    ``(H, W)`` の ``int32``。番号は 1 から連番で歯抜けが無い。

Examples
--------
>>> import numpy as np
>>> m = np.zeros((6, 9), bool); m[1:4, 1:4] = True; m[1:4, 5:8] = True
>>> int(blob_label(m).max())
2

## 詳しい使い方ガイド

- [blob_analysis ファミリ ガイド](../guides/blob_analysis.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [blob_split_tour](../../../../examples/blob_split_tour.py) — `py -3.11 examples/blob_split_tour.py`
- [poc_bone_trabecular_thickness](../../../../examples/poc_bone_trabecular_thickness.py) — `py -3.11 examples/poc_bone_trabecular_thickness.py`
- [poc_bump_coplanarity](../../../../examples/poc_bump_coplanarity.py) — `py -3.11 examples/poc_bump_coplanarity.py`
- [poc_fresco_craquelure](../../../../examples/poc_fresco_craquelure.py) — `py -3.11 examples/poc_fresco_craquelure.py`
- [poc_gear_tooth_metrology](../../../../examples/poc_gear_tooth_metrology.py) — `py -3.11 examples/poc_gear_tooth_metrology.py`
- [poc_leaf_disease_area](../../../../examples/poc_leaf_disease_area.py) — `py -3.11 examples/poc_leaf_disease_area.py`
- [poc_machine_condition_fusion](../../../../examples/poc_machine_condition_fusion.py) — `py -3.11 examples/poc_machine_condition_fusion.py`
- [poc_metal_grain_size](../../../../examples/poc_metal_grain_size.py) — `py -3.11 examples/poc_metal_grain_size.py`
- [poc_nuclei_ploidy](../../../../examples/poc_nuclei_ploidy.py) — `py -3.11 examples/poc_nuclei_ploidy.py`
- [poc_particle_sizing](../../../../examples/poc_particle_sizing.py) — `py -3.11 examples/poc_particle_sizing.py`
- [poc_particle_tracking](../../../../examples/poc_particle_tracking.py) — `py -3.11 examples/poc_particle_tracking.py`
- [poc_pipe_wall_loss](../../../../examples/poc_pipe_wall_loss.py) — `py -3.11 examples/poc_pipe_wall_loss.py`
- [poc_print_warpage_risk](../../../../examples/poc_print_warpage_risk.py) — `py -3.11 examples/poc_print_warpage_risk.py`
- [poc_pv_thermal_survey](../../../../examples/poc_pv_thermal_survey.py) — `py -3.11 examples/poc_pv_thermal_survey.py`
- [poc_sea_ice_concentration](../../../../examples/poc_sea_ice_concentration.py) — `py -3.11 examples/poc_sea_ice_concentration.py`
- [poc_solar_el_inspection](../../../../examples/poc_solar_el_inspection.py) — `py -3.11 examples/poc_solar_el_inspection.py`
- [poc_solder_fillet_aoi](../../../../examples/poc_solder_fillet_aoi.py) — `py -3.11 examples/poc_solder_fillet_aoi.py`
- [poc_timelapse_growth](../../../../examples/poc_timelapse_growth.py) — `py -3.11 examples/poc_timelapse_growth.py`
- [poc_traffic_counting](../../../../examples/poc_traffic_counting.py) — `py -3.11 examples/poc_traffic_counting.py`
- [poc_vessel_network](../../../../examples/poc_vessel_network.py) — `py -3.11 examples/poc_vessel_network.py`
- [poc_weld_radiograph_porosity](../../../../examples/poc_weld_radiograph_porosity.py) — `py -3.11 examples/poc_weld_radiograph_porosity.py`
- [poc_wound_area_tracking](../../../../examples/poc_wound_area_tracking.py) — `py -3.11 examples/poc_wound_area_tracking.py`

## 型が繋がる次の op(`labels2d` を入力に取れる)

[blob_features](../measure/blob_features.md) · [blob_select](../select/blob_select.md) · [blob_select_largest](../select/blob_select_largest.md) · [blob_split](../split/blob_split.md) · [blob_region](../extract/blob_region.md) · [blob_boundaries](../extract/blob_boundaries.md) · [blob_overlay](../extract/blob_overlay.md)

## 同カテゴリ(`connect`)

—

---
*Provenance: blob2d.py — BLOB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
