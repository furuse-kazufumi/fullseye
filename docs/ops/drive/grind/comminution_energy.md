---
op: comminution_energy
dim: drive
category: grind
in: scalar × scalar
out: table
examples: [poc_powder_grinding_ae]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# comminution_energy — DRIVE `grind` op

- **データ種**: `scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.comminution_energy(x_feed: 'float', x_product: 'float | None' = None, law: 'str' = 'bond', C: 'float' = 1.0, n: 'float | None' = None, energy: 'float | None' = None) -> 'dict'` (実装を直接呼ぶなら `import grind; grind.comminution_energy(x_feed: 'float', x_product: 'float | None' = None, law: 'str' = 'bond', C: 'float' = 1.0, n: 'float | None' = None, energy: 'float | None' = None) -> 'dict'`、台帳から引くなら `opsdrive.get("comminution_energy")`)

## 使い方

粉砕則の閉形式(Reddy の式 (1)・(5)〜(7))。``x_product`` と ``energy`` の **ちょうど一方** を与える。

一般式 ``dE = −C dx / x^n`` を積分して ``E = C/(n−1) (x₂^{1−n} − x₁^{1−n})``(n ≠ 1)、``E = C ln(x₁/x₂)``(n = 1)。
``law``: ``"kick"``(n = 1)、``"bond"``(n = 1.5、``E = 2C(1/√x₂ − 1/√x₁)``)、``"rittinger"``(n = 2)、``"walker"``(``n`` を渡す)、
``"bond_wi"``(``W = 10 Wi (1/√P80 − 1/√F80)``、``C`` を作業指数 Wi [kWh/t] と読み、径は µm、= ``bond`` で ``C = 5 Wi``)。
``x_feed`` は n > 1 なら ``inf`` を許す(無限大の供給からの全エネルギー、Reddy の式 (2)〜(4))。
返り: ``E``・``x_feed``・``x_product``・``law``・``n``・``C``。細かくならない(``x_product ≥ x_feed``)・負のエネルギー → ``ValueError``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_powder_grinding_ae](../../../../examples/poc_powder_grinding_ae.py) — `py -3.11 examples/poc_powder_grinding_ae.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`grind`)

[particle_size_read](particle_size_read.md) · [particle_size_dx](particle_size_dx.md) · [particle_size_oversize](particle_size_oversize.md) · [particle_size_synth](particle_size_synth.md) · [comminution_law_fit](comminution_law_fit.md) · [breakage_first_order_fit](breakage_first_order_fit.md) · [replicate_compare](replicate_compare.md) · [ae_read_csv](ae_read_csv.md)

---
*Provenance: grind.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
