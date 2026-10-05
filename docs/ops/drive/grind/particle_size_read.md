---
op: particle_size_read
dim: drive
category: grind
in: any
out: table
examples: [poc_powder_grinding_ae]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# particle_size_read — DRIVE `grind` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.particle_size_read(path) -> 'dict'` (実装を直接呼ぶなら `import grind; grind.particle_size_read(path) -> 'dict'`、台帳から引くなら `opsdrive.get("particle_size_read")`)

## 使い方

レーザー回折の粒度分布 CSV(ヘッダの ``key,value`` 行 + ``SizeClasses`` で始まる表)を読む。

返り: ``edges`` [µm] (表の 1 列目 = 区間の端)、``volume``(2 列目 = 端 i と i+1 の間の体積 %)、``header``
(文字列の dict)、``dx50_reported``(ヘッダの ``Dx (50)``、無ければ None)、``total_percent``(体積の総和)、
``n_rows``。読み込んだパスは返り値に残さない。表が無い・数値でない・最後の行が 0 でない → ``ValueError``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_powder_grinding_ae](../../../../examples/poc_powder_grinding_ae.py) — `py -3.11 examples/poc_powder_grinding_ae.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`grind`)

[particle_size_dx](particle_size_dx.md) · [particle_size_oversize](particle_size_oversize.md) · [particle_size_synth](particle_size_synth.md) · [comminution_energy](comminution_energy.md) · [comminution_law_fit](comminution_law_fit.md) · [breakage_first_order_fit](breakage_first_order_fit.md) · [replicate_compare](replicate_compare.md) · [ae_read_csv](ae_read_csv.md)

---
*Provenance: grind.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
