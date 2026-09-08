---
op: blob_features
dim: blob
category: measure
in: labels2d
out: table
examples: [poc_bone_trabecular_thickness, poc_bump_coplanarity, poc_fresco_craquelure, poc_gear_tooth_metrology, poc_leaf_disease_area, poc_metal_grain_size, poc_nuclei_ploidy, poc_particle_sizing, poc_particle_tracking, poc_print_warpage_risk, poc_pv_thermal_survey, poc_real_coin_metrology, poc_rotation_invariance_audit, poc_sea_ice_concentration, poc_solar_el_inspection, poc_solder_fillet_aoi, poc_traffic_counting, poc_vessel_network, poc_weld_radiograph_porosity, poc_wound_area_tracking]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# blob_features — BLOB `measure` op

- **データ種**: `labels2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.blob_features(labels: 'Any', spacing: 'float' = 1.0) -> 'dict'` (実装を直接呼ぶなら `import blob2d; blob2d.blob_features(labels: 'Any', spacing: 'float' = 1.0) -> 'dict'`、台帳から引くなら `opsblob.get("blob_features")`)

## 使い方

物体ごとの形の特徴量を、**鍵ごとに 1 本の配列**で返す。

Parameters
----------
labels : array_like
    :func:`blob_label` の出力(整数、背景 0)。
spacing : float
    画素 1 個の大きさ[単位/px]。長さにこれを、面積にその 2 乗を掛ける。
    **既定 1.0 = 画素のまま**。

Returns
-------
dict
    ``n``(物体数)、``spacing``、``units``(項目 → 単位の対応)と、
    長さ ``n`` の配列 19 本(:data:`FEATURE_KEYS`)。物体が 0 個でも
    鍵は全部揃えて空配列で返す(呼び手が分岐しなくて済む)。

Notes
-----
* ``angle`` は**行列座標系**の傾き(+列 → +行 が正 = 画面では時計回り)。
* ``major`` / ``minor`` は**同じ 2 次モーメントを持つ楕円**の軸長
  (``4 sqrt(lambda)``)。画素の並びの外接ではないので、正方形に対しては
  辺長より少し長く出る —— これは定義どおりで、誤差ではない。
* ``circularity`` は ``4 pi A / P^2``。**HALCON の ``circularity`` は
  「面積 / 最遠点を半径とする円の面積」で別物**なので、値を突き合わせる
  ときは定義を確かめること。
* ``touches_border`` が True の物体は、面積も周長も**切れた分だけ小さい**。
  数える前に捨てるか、真値の側も同じ規約で数えること。

Examples
--------
>>> import numpy as np
>>> m = np.zeros((20, 20), bool); m[4:14, 4:9] = True
>>> f = blob_features(blob_label(m))
>>> int(f["n"]), float(f["area"][0])
(1, 50.0)

## 詳しい使い方ガイド

- [blob_analysis ファミリ ガイド](../guides/blob_analysis.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_bone_trabecular_thickness](../../../../examples/poc_bone_trabecular_thickness.py) — `py -3.11 examples/poc_bone_trabecular_thickness.py`
- [poc_bump_coplanarity](../../../../examples/poc_bump_coplanarity.py) — `py -3.11 examples/poc_bump_coplanarity.py`
- [poc_fresco_craquelure](../../../../examples/poc_fresco_craquelure.py) — `py -3.11 examples/poc_fresco_craquelure.py`
- [poc_gear_tooth_metrology](../../../../examples/poc_gear_tooth_metrology.py) — `py -3.11 examples/poc_gear_tooth_metrology.py`
- [poc_leaf_disease_area](../../../../examples/poc_leaf_disease_area.py) — `py -3.11 examples/poc_leaf_disease_area.py`
- [poc_metal_grain_size](../../../../examples/poc_metal_grain_size.py) — `py -3.11 examples/poc_metal_grain_size.py`
- [poc_nuclei_ploidy](../../../../examples/poc_nuclei_ploidy.py) — `py -3.11 examples/poc_nuclei_ploidy.py`
- [poc_particle_sizing](../../../../examples/poc_particle_sizing.py) — `py -3.11 examples/poc_particle_sizing.py`
- [poc_particle_tracking](../../../../examples/poc_particle_tracking.py) — `py -3.11 examples/poc_particle_tracking.py`
- [poc_print_warpage_risk](../../../../examples/poc_print_warpage_risk.py) — `py -3.11 examples/poc_print_warpage_risk.py`
- [poc_pv_thermal_survey](../../../../examples/poc_pv_thermal_survey.py) — `py -3.11 examples/poc_pv_thermal_survey.py`
- [poc_real_coin_metrology](../../../../examples/poc_real_coin_metrology.py) — `py -3.11 examples/poc_real_coin_metrology.py`
- [poc_rotation_invariance_audit](../../../../examples/poc_rotation_invariance_audit.py) — `py -3.11 examples/poc_rotation_invariance_audit.py`
- [poc_sea_ice_concentration](../../../../examples/poc_sea_ice_concentration.py) — `py -3.11 examples/poc_sea_ice_concentration.py`
- [poc_solar_el_inspection](../../../../examples/poc_solar_el_inspection.py) — `py -3.11 examples/poc_solar_el_inspection.py`
- [poc_solder_fillet_aoi](../../../../examples/poc_solder_fillet_aoi.py) — `py -3.11 examples/poc_solder_fillet_aoi.py`
- [poc_traffic_counting](../../../../examples/poc_traffic_counting.py) — `py -3.11 examples/poc_traffic_counting.py`
- [poc_vessel_network](../../../../examples/poc_vessel_network.py) — `py -3.11 examples/poc_vessel_network.py`
- [poc_weld_radiograph_porosity](../../../../examples/poc_weld_radiograph_porosity.py) — `py -3.11 examples/poc_weld_radiograph_porosity.py`
- [poc_wound_area_tracking](../../../../examples/poc_wound_area_tracking.py) — `py -3.11 examples/poc_wound_area_tracking.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`measure`)

—

---
*Provenance: blob2d.py — BLOB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
