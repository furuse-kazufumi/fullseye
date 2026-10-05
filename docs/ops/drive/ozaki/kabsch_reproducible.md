---
op: kabsch_reproducible
dim: drive
category: ozaki
in: points × points
out: table
examples: [poc_reproducible_icp]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# kabsch_reproducible — DRIVE `ozaki` op

- **データ種**: `points × points` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.kabsch_reproducible(P, Q)` (実装を直接呼ぶなら `import ozakimm; ozakimm.kabsch_reproducible(P, Q)`、台帳から引くなら `opsdrive.get("kabsch_reproducible")`)

## 使い方

``|R p + t − q|`` を最小にする剛体の ``R``・``t``(Kabsch 1976)を、点の順に依らないビットで返す。

返り: ``{"R": (3, 3), "t": (3,), "H": (3, 3)}``。``H`` は :func:`cross_covariance_reproducible`(どの計算機でも同じ
ビット)、``R`` は ``H`` の特異値分解から(反射は det で直す)。特異値分解は LAPACK なので、``R``・``t`` が同じビットに
なるのは同じ計算機・同じ LAPACK の上(3×3 なのでスレッド数には依らない)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_reproducible_icp](../../../../examples/poc_reproducible_icp.py) — `py -3.11 examples/poc_reproducible_icp.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`ozaki`)

[matmul_ozaki](matmul_ozaki.md) · [matmul_reproducible](matmul_reproducible.md) · [ozaki_error_bound](ozaki_error_bound.md) · [cross_covariance_reproducible](cross_covariance_reproducible.md) · [fp64_emulation_probe](fp64_emulation_probe.md)

---
*Provenance: ozakimm.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
