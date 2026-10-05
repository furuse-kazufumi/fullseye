---
op: contact_patch_radius
dim: drive
category: tacdome
in: image2d × scalar
out: table
examples: [poc_tacdome_large_deformation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# contact_patch_radius — DRIVE `tacdome` op

- **データ種**: `image2d × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.contact_patch_radius(img, pitch: 'float', ring_px: 'float' = 4.0) -> 'dict'` (実装を直接呼ぶなら `import tacdome; tacdome.contact_patch_radius(img, pitch: 'float', ring_px: 'float' = 4.0) -> 'dict'`、台帳から引くなら `opsdrive.get("contact_patch_radius")`)

## 使い方

接触の像(:func:`dome_contact_image` の型)から接触半径を読む。被覆率の線形和(面積法)で縁の副画素まで使う。

1) しきい値 (1 % 点 + 99.9 % 点)/2 で粗い円盤 → 重心と半径 r_t。2) 内側 r < r_t − ``ring_px`` の中央値を fg、外の輪
r_t + ``ring_px`` 〜 r_t + 2·``ring_px`` の中央値を bg。3) 被覆率 (I − bg)/(fg − bg) を r < r_t + ``ring_px`` で**切らずに**足す
(切ると雑音が片側に偏る)→ a = pitch·√(Σ/π)、重心は被覆率の重み。返り: ``a``・``a_px``・``a_threshold``(しきい値の画素数の円)・
``centre``(行, 列)・``fg``・``bg``・``edge_points``(しきい値の円盤の境界画素 (行, 列)、measure.fit_circle に渡せる)。
**Raises** ``ValueError``: 2 次元でない、明るい円盤が無い(コントラスト 0)、円盤が小さすぎる(r_t < 3 px)か窓の縁に触れる。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacdome_large_deformation](../../../../examples/poc_tacdome_large_deformation.py) — `py -3.11 examples/poc_tacdome_large_deformation.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tacdome`)

[powerlaw_linear_contact](powerlaw_linear_contact.md) · [largedef_correction](largedef_correction.md) · [largedef_radius_ratio](largedef_radius_ratio.md) · [largedef_universal_correction](largedef_universal_correction.md) · [large_deformation_contact](large_deformation_contact.md) · [large_deformation_inverse](large_deformation_inverse.md) · [mdr_spring_bed](mdr_spring_bed.md) · [neohookean_cylinder_exact](neohookean_cylinder_exact.md)

---
*Provenance: tacdome.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
