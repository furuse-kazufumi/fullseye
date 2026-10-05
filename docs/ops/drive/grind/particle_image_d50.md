---
op: particle_image_d50
dim: drive
category: grind
in: image2d × scalar
out: table
examples: [poc_powder_grinding_ae]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# particle_image_d50 — DRIVE `grind` op

- **データ種**: `image2d × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.particle_image_d50(image, pitch: 'float', basis: 'str' = 'volume', threshold: 'float' = 0.02, border: 'str' = 'exclude') -> 'dict'` (実装を直接呼ぶなら `import grind; grind.particle_image_d50(image, pitch: 'float', basis: 'str' = 'volume', threshold: 'float' = 0.02, border: 'str' = 'exclude') -> 'dict'`、台帳から引くなら `opsdrive.get("particle_image_d50")`)

## 使い方

被覆率の画像の粒子から D10 / D50 / D90 [µm]。面積は **ラベルの中の被覆率の和**(縁の部分画素を数える、閾値で太らない)。

``basis``: ``"volume"``(球と見て d³ の重み —— レーザー回折と同じ体積基準)、``"number"``(個数基準)。同じ画像でも
この 2 つは別の分布で、体積基準が大きく出る。``border``: ``"exclude"``(縁に触れる粒子を捨てる)/ ``"include"``。
返り: ``d10``・``d50``・``d90``・``diameters``(等価円直径 µm)・``n``・``n_border``・``basis``。粒子が 3 未満 → ``ValueError``。
融合した粒子は 1 個に数える(分けない —— 塗れた面積の分離は別の op の仕事)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_powder_grinding_ae](../../../../examples/poc_powder_grinding_ae.py) — `py -3.11 examples/poc_powder_grinding_ae.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`grind`)

[particle_size_read](particle_size_read.md) · [particle_size_dx](particle_size_dx.md) · [particle_size_oversize](particle_size_oversize.md) · [particle_size_synth](particle_size_synth.md) · [comminution_energy](comminution_energy.md) · [comminution_law_fit](comminution_law_fit.md) · [breakage_first_order_fit](breakage_first_order_fit.md) · [replicate_compare](replicate_compare.md)

---
*Provenance: grind.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
