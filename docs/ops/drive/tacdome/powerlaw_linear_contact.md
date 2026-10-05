---
op: powerlaw_linear_contact
dim: drive
category: tacdome
in: text × scalar × scalar
out: table
examples: [poc_tacdome_large_deformation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# powerlaw_linear_contact — DRIVE `tacdome` op

- **データ種**: `text × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.powerlaw_linear_contact(shape: 'str', size: 'float', Estar: 'float', p: 'float | None' = None) -> 'dict'` (実装を直接呼ぶなら `import tacdome; tacdome.powerlaw_linear_contact(shape: 'str', size: 'float', Estar: 'float', p: 'float | None' = None) -> 'dict'`、台帳から引くなら `opsdrive.get("powerlaw_linear_contact")`)

## 使い方

べき乗則断面 f(r) = c·rᵖ を平板で押す線形解(式 1・5): F_L = C·δⁿ、a_L = D·δ^{1/p}、n = 1 + 1/p。

``shape``: ``"sphere"``(``size`` = 半径 R、放物線 c = 1/(2R)、C = (4/3)E*√R、D = √R = Hertz)/ ``"cone"``(``size`` = 側面の
傾き tanα = 高さ/底の半径、C = 2E*/(π tanα)、D = 2/(π tanα))/ ``"punch"``(平頭の円柱、``size`` = 半径 a0、n = 1、C = 2E*a0、
a_L = a0 で一定)/ ``"power"``(``size`` = c、``p`` が要る)。MDR の 1D 断面は g(x) = κ_p c |x|ᵖ で、
C = 2E*·p/(p+1)·(κ_p c)^{−1/p}、D = (κ_p c)^{−1/p}。

返り: ``shape``・``p``・``n``・``c``・``kappa_p``・``g_coef``(= κ_p c、punch は 0)・``C``・``D``・``Estar``・``size``。
**Raises** ``ValueError``: 知らない shape(綴り違い)、size・E* ≤ 0、power で p が無い / 範囲外、power 以外で p を渡した。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacdome_large_deformation](../../../../examples/poc_tacdome_large_deformation.py) — `py -3.11 examples/poc_tacdome_large_deformation.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tacdome`)

[largedef_correction](largedef_correction.md) · [largedef_radius_ratio](largedef_radius_ratio.md) · [largedef_universal_correction](largedef_universal_correction.md) · [large_deformation_contact](large_deformation_contact.md) · [large_deformation_inverse](large_deformation_inverse.md) · [mdr_spring_bed](mdr_spring_bed.md) · [neohookean_cylinder_exact](neohookean_cylinder_exact.md) · [hertz_small_strain_error](hertz_small_strain_error.md)

---
*Provenance: tacdome.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
