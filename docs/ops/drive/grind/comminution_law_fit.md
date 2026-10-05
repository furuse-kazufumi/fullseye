---
op: comminution_law_fit
dim: drive
category: grind
in: signal × signal
out: table
examples: [poc_powder_grinding_ae]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# comminution_law_fit — DRIVE `grind` op

- **データ種**: `signal × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.comminution_law_fit(t, d, law: 'str' = 'all') -> 'dict'` (実装を直接呼ぶなら `import grind; grind.comminution_law_fit(t, d, law: 'str' = 'all') -> 'dict'`、台帳から引くなら `opsdrive.get("comminution_law_fit")`)

## 使い方

粒径の時間変化 ``d(t)`` に粉砕則を当てる(エネルギー ∝ ``t`` の仮定、モジュール冒頭)。誤差は **log(径)** で測る。

``t``: 正味の粉砕時間(エネルギーの代わり、≥ 0)、``d``: その時点の代表径 [µm] (D50 など)。独立試行は同じ ``t`` に複数並べてよい。
模型: Kick ``ln x = ln x₀ − k t``、n ≠ 1 の則は ``x^{1−n} = x₀^{1−n} + (n−1) k t``(``k`` = 単位時間あたりの E/C)。
``law``: ``"all"``(kick / bond / rittinger / walker を全部)か 1 つの名前。返り: ``fits``(則 → ``n``・``x0``・``k``・
``rms_log``・``aic``・``residual_log``)、``best_fixed``(n を固定した 3 則のうち ``rms_log`` 最小)、``n_points``。
``x0`` が ``inf`` になるのは「供給径の項が要らない」(n > 1 で x₀^{1−n} → 0)という当てはめの結果で、正直にそう返す。
点が 3 未満・径が非正 → ``ValueError``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_powder_grinding_ae](../../../../examples/poc_powder_grinding_ae.py) — `py -3.11 examples/poc_powder_grinding_ae.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`grind`)

[particle_size_read](particle_size_read.md) · [particle_size_dx](particle_size_dx.md) · [particle_size_oversize](particle_size_oversize.md) · [particle_size_synth](particle_size_synth.md) · [comminution_energy](comminution_energy.md) · [breakage_first_order_fit](breakage_first_order_fit.md) · [replicate_compare](replicate_compare.md) · [ae_read_csv](ae_read_csv.md)

---
*Provenance: grind.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
