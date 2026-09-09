---
op: blob_overlay
dim: blob
category: extract
in: image2d × labels2d
out: rgb
examples: [poc_bump_coplanarity, poc_fresco_craquelure, poc_gear_tooth_metrology, poc_leaf_disease_area, poc_metal_grain_size, poc_nuclei_ploidy, poc_particle_sizing, poc_weld_radiograph_porosity]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# blob_overlay — BLOB `extract` op

- **データ種**: `image2d × labels2d` → `rgb`
- **呼び出し**: `import fullseye as fs; fs.ledger.blob_overlay(image: 'Any', labels: 'Any', alpha: 'float' = 0.5, seed: 'int' = 0) -> 'np.ndarray'` (実装を直接呼ぶなら `import blob2d; blob2d.blob_overlay(image: 'Any', labels: 'Any', alpha: 'float' = 0.5, seed: 'int' = 0) -> 'np.ndarray'`、台帳から引くなら `opsblob.get("blob_overlay")`)

## 使い方

元画像の上に物体を色分けして重ね、``(H, W, 3)`` の float RGB を返す。

この族の**出口**。作れて測れるが見られない型にしないために置く。
色は :func:`fullseye.colorize_labels` と同じ規則で、背景は元画像のまま。

## 詳しい使い方ガイド

- [blob_analysis ファミリ ガイド](../guides/blob_analysis.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_bump_coplanarity](../../../../examples/poc_bump_coplanarity.py) — `py -3.11 examples/poc_bump_coplanarity.py`
- [poc_fresco_craquelure](../../../../examples/poc_fresco_craquelure.py) — `py -3.11 examples/poc_fresco_craquelure.py`
- [poc_gear_tooth_metrology](../../../../examples/poc_gear_tooth_metrology.py) — `py -3.11 examples/poc_gear_tooth_metrology.py`
- [poc_leaf_disease_area](../../../../examples/poc_leaf_disease_area.py) — `py -3.11 examples/poc_leaf_disease_area.py`
- [poc_metal_grain_size](../../../../examples/poc_metal_grain_size.py) — `py -3.11 examples/poc_metal_grain_size.py`
- [poc_nuclei_ploidy](../../../../examples/poc_nuclei_ploidy.py) — `py -3.11 examples/poc_nuclei_ploidy.py`
- [poc_particle_sizing](../../../../examples/poc_particle_sizing.py) — `py -3.11 examples/poc_particle_sizing.py`
- [poc_weld_radiograph_porosity](../../../../examples/poc_weld_radiograph_porosity.py) — `py -3.11 examples/poc_weld_radiograph_porosity.py`

## 型が繋がる次の op(`rgb` を入力に取れる)

—

## 同カテゴリ(`extract`)

[blob_region](blob_region.md) · [blob_boundaries](blob_boundaries.md)

---
*Provenance: blob2d.py — BLOB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
