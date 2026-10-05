---
op: large_deformation_inverse
dim: drive
category: tacdome
in: scalar × scalar × table
out: table
examples: [poc_tacdome_large_deformation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# large_deformation_inverse — DRIVE `tacdome` op

- **データ種**: `scalar × scalar × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.large_deformation_inverse(a: 'float', L: 'float', lin: 'dict', reading: 'str' = 'derived', tol: 'float' = 1e-14) -> 'dict'` (実装を直接呼ぶなら `import tacdome; tacdome.large_deformation_inverse(a: 'float', L: 'float', lin: 'dict', reading: 'str' = 'derived', tol: 'float' = 1e-14) -> 'dict'`、台帳から引くなら `opsdrive.get("large_deformation_inverse")`)

## 使い方

測った接触半径 a から押し込みと力を逆に読む(式 4 を d について解き、式 2 で力)。センサの読み出しの本体。

平頭は閉形式 d = 1 − (a0/a)²。それ以外は a(d) = (a/a_L)(d)·D·(dL)^{1/p} が d の単調増加なので二分法(相対 ``tol``)。
返り: ``d``・``delta``・``F``・``F_L``・``kappa``・``F_hertz_from_radius``(同じ a を線形解 = Hertz で読んだ力)・
``err_hertz_pct``(Hertz で読んだ力の誤差)・``beyond_validated``・``iterations``。
**Raises** ``ValueError``: a ≤ 0、平頭で a ≤ a0、d が 1 に届いても a に足りない(数値の範囲外)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacdome_large_deformation](../../../../examples/poc_tacdome_large_deformation.py) — `py -3.11 examples/poc_tacdome_large_deformation.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tacdome`)

[powerlaw_linear_contact](powerlaw_linear_contact.md) · [largedef_correction](largedef_correction.md) · [largedef_radius_ratio](largedef_radius_ratio.md) · [largedef_universal_correction](largedef_universal_correction.md) · [large_deformation_contact](large_deformation_contact.md) · [mdr_spring_bed](mdr_spring_bed.md) · [neohookean_cylinder_exact](neohookean_cylinder_exact.md) · [hertz_small_strain_error](hertz_small_strain_error.md)

---
*Provenance: tacdome.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
