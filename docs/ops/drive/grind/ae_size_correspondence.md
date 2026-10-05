---
op: ae_size_correspondence
dim: drive
category: grind
in: signal × signal
out: table
examples: [poc_powder_grinding_ae]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# ae_size_correspondence — DRIVE `grind` op

- **データ種**: `signal × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.ae_size_correspondence(power, d50, group=None) -> 'dict'` (実装を直接呼ぶなら `import grind; grind.ae_size_correspondence(power, d50, group=None) -> 'dict'`、台帳から引くなら `opsdrive.get("ae_size_correspondence")`)

## 使い方

AE の帯域電力と D50 の対応(単調性・相関・log–log の傾き α、``P ∝ D50^α``)。

``group`` を渡すと群(材料)ごとに出す(材料で電力の水準が桁で違うので、混ぜた相関は水準の差を拾う —— ``pooled`` は参考)。
返り: 群 → ``n``・``spearman``(順位相関)・``alpha``(ln P を ln D50 に当てた傾き)・``sign_agree``(全ての組で
「D50 が大きい方が P も大きい」の割合)。**点が 2 つなら spearman は ±1 しか取れない**(``n`` を必ず併記する)。

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
