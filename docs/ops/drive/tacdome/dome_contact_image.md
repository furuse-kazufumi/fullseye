---
op: dome_contact_image
dim: drive
category: tacdome
in: scalar × scalar
out: image2d
examples: [poc_tacdome_large_deformation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# dome_contact_image — DRIVE `tacdome` op

- **データ種**: `scalar × scalar` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.dome_contact_image(a: 'float', pitch: 'float', n: 'int' = 128, centre=None, fg: 'float' = 1.0, bg: 'float' = 0.12, footprint: 'float | None' = None, outside: 'float' = 0.0, noise: 'float' = 0.0, seed: 'int' = 0, ss: 'int' = 8) -> 'np.ndarray'` (実装を直接呼ぶなら `import tacdome; tacdome.dome_contact_image(a: 'float', pitch: 'float', n: 'int' = 128, centre=None, fg: 'float' = 1.0, bg: 'float' = 0.12, footprint: 'float | None' = None, outside: 'float' = 0.0, noise: 'float' = 0.0, seed: 'int' = 0, ss: 'int' = 8) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("dome_contact_image")`)

## 使い方

ドームの内側から撮った接触の像(接触域が明るい、全反射の破れ型の照明の理想化)。(n, n) の float。

半径 ``a`` [m] の円盤 = ``fg``、ドームの底の円(``footprint`` [m]、None なら全面)の残り = ``bg``、外 = ``outside``。縁は画素を
``ss`` × ``ss`` に割った被覆率で反エイリアス(補間しない)。``centre`` = (行, 列)[px] (既定は中央 + 副画素のずれ 0.37, −0.21)。
``noise`` = 画素ごとの正規雑音の σ。**Raises** ``ValueError``: a・pitch ≤ 0、n < 16、ss < 1、円盤が窓からはみ出す、fg ≤ bg。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacdome_large_deformation](../../../../examples/poc_tacdome_large_deformation.py) — `py -3.11 examples/poc_tacdome_large_deformation.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[flow_from_depth_motion](../ttc/flow_from_depth_motion.md) · [ttc_truth](../ttc/ttc_truth.md) · [ttc_from_flow](../ttc/ttc_from_flow.md) · [foe_from_flow](../ttc/foe_from_flow.md) · [perlin2](../terrain/perlin2.md) · [fbm_height](../terrain/fbm_height.md) · [fbm_gradient](../terrain/fbm_gradient.md) · [radial_periodogram](../terrain/radial_periodogram.md)

## 同カテゴリ(`tacdome`)

[powerlaw_linear_contact](powerlaw_linear_contact.md) · [largedef_correction](largedef_correction.md) · [largedef_radius_ratio](largedef_radius_ratio.md) · [largedef_universal_correction](largedef_universal_correction.md) · [large_deformation_contact](large_deformation_contact.md) · [large_deformation_inverse](large_deformation_inverse.md) · [mdr_spring_bed](mdr_spring_bed.md) · [neohookean_cylinder_exact](neohookean_cylinder_exact.md)

---
*Provenance: tacdome.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
