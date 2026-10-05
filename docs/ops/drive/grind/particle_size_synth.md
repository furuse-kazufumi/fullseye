---
op: particle_size_synth
dim: drive
category: grind
in: scalar × scalar
out: table
examples: [poc_powder_grinding_ae]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# particle_size_synth — DRIVE `grind` op

- **データ種**: `scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.particle_size_synth(d50: 'float', sigma_ln: 'float', edges=None) -> 'dict'` (実装を直接呼ぶなら `import grind; grind.particle_size_synth(d50: 'float', sigma_ln: 'float', edges=None) -> 'dict'`、台帳から引くなら `opsdrive.get("particle_size_synth")`)

## 使い方

対数正規の **体積** 分布を装置と同じ区間に割り付けた粒度分布(真値つき)。

体積の累積 ``F(x) = Φ((ln x − ln d50) / σ)``。``edges`` を省くと公開データの装置の 74 端(比 1.13616)。
返り: ``edges``・``volume``(%)と ``truth``(``d10``・``d50``・``d90`` = ``d50 · exp(±1.28155 σ)``、``sigma_ln``)。
区間の外にはみ出す体積が 1e-6 を超えると ``ValueError``(端で切ると D10/D90 が黙って動く)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_powder_grinding_ae](../../../../examples/poc_powder_grinding_ae.py) — `py -3.11 examples/poc_powder_grinding_ae.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`grind`)

[particle_size_read](particle_size_read.md) · [particle_size_dx](particle_size_dx.md) · [particle_size_oversize](particle_size_oversize.md) · [comminution_energy](comminution_energy.md) · [comminution_law_fit](comminution_law_fit.md) · [breakage_first_order_fit](breakage_first_order_fit.md) · [replicate_compare](replicate_compare.md) · [ae_read_csv](ae_read_csv.md)

---
*Provenance: grind.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
