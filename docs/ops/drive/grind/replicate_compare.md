---
op: replicate_compare
dim: drive
category: grind
in: any
out: table
examples: [poc_powder_grinding_ae]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# replicate_compare — DRIVE `grind` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.replicate_compare(groups: 'dict', log: 'bool' = True) -> 'dict'` (実装を直接呼ぶなら `import grind; grind.replicate_compare(groups: 'dict', log: 'bool' = True) -> 'dict'`、台帳から引くなら `opsdrive.get("replicate_compare")`)

## 使い方

独立試行のばらつきと、群(材料)どうしの差を同じ物差しで並べる。

``groups``: 名前 → ``(n_runs, n_conditions)`` の配列(例: 材料ごとに 3 回 × 7 時点の D50)。全群で ``n_conditions`` が同じ。
``log=True`` は ln をとってから比べる(径の比のばらつき = 変動係数に近い)。返り: ``spread``(群 → 条件ごとの ``mean``・``sd``・
``cv``(SD/平均、元の尺度)、``cv_pooled``(cv の二乗平均の根)、``cv_max``)、``separation``(群の組 → 条件ごとの
``|Δ平均| / √(SE₁² + SE₂²)``(SE = SD/√n)と、その最小 ``min_z``。鍵は ``"名前1|名前2"`` の文字列)。試行が 2 未満 → ``ValueError``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_powder_grinding_ae](../../../../examples/poc_powder_grinding_ae.py) — `py -3.11 examples/poc_powder_grinding_ae.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`grind`)

[particle_size_read](particle_size_read.md) · [particle_size_dx](particle_size_dx.md) · [particle_size_oversize](particle_size_oversize.md) · [particle_size_synth](particle_size_synth.md) · [comminution_energy](comminution_energy.md) · [comminution_law_fit](comminution_law_fit.md) · [breakage_first_order_fit](breakage_first_order_fit.md) · [ae_read_csv](ae_read_csv.md)

---
*Provenance: grind.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
