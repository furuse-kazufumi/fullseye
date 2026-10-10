---
op: breakage_first_order_fit
dim: drive
category: grind
in: signal × signal
out: table
examples: [poc_powder_grinding_ae]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# breakage_first_order_fit — DRIVE `grind` op

- **データ種**: `signal × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.breakage_first_order_fit(t, w, x=None) -> 'dict'` (実装を直接呼ぶなら `import grind; grind.breakage_first_order_fit(t, w, x=None) -> 'dict'`、台帳から引くなら `opsdrive.get("breakage_first_order_fit")`)

## 使い方

一次の破砕速度 ``w(t) = w₀ exp(−S t)`` を当てる(Deniz 2004 の式 (2)、出典 Austin)。

``w`` が 1-D: ある区間(または径 ``x`` より上の累積)の体積割合の時系列。返り: ``S``・``w0``・``rms_log``・``r2``
(ln w の直線の決定係数)・``S_early`` / ``S_late``(前半・後半の時点だけで当てた S、一次なら等しい —— 遅くなるなら一次から外れる)。
``w`` が 2-D ``(n_x, n_t)`` で ``x``(各行の径、µm)を渡すと、行ごとの S と ``S = a_T x^α``(Deniz の式 (3))の ``a_T``・``alpha``。
``apparent=True`` は「最上位の区間でない(上から生まれ込む粒がある)ので式 (1) は厳密でない」の自己申告で、累積に当てた場合は常に True。
割合が 0 以下・1 超・点が 3 未満 → ``ValueError``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_powder_grinding_ae](../../../../examples/poc_powder_grinding_ae.py) — `py -3.11 examples/poc_powder_grinding_ae.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`grind`)

[particle_size_read](particle_size_read.md) · [particle_size_dx](particle_size_dx.md) · [particle_size_oversize](particle_size_oversize.md) · [particle_size_synth](particle_size_synth.md) · [comminution_energy](comminution_energy.md) · [comminution_law_fit](comminution_law_fit.md) · [replicate_compare](replicate_compare.md) · [ae_read_csv](ae_read_csv.md)

---
*Provenance: grind.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
