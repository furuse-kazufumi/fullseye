---
op: cross_covariance_reproducible
dim: drive
category: ozaki
in: points × points
out: matrix
examples: [poc_reproducible_icp]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# cross_covariance_reproducible — DRIVE `ozaki` op

- **データ種**: `points × points` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.cross_covariance_reproducible(P, Q, tol: 'float' = 1.1102230246251565e-16)` (実装を直接呼ぶなら `import ozakimm; ozakimm.cross_covariance_reproducible(P, Q, tol: 'float' = 1.1102230246251565e-16)`、台帳から引くなら `opsdrive.get("cross_covariance_reproducible")`)

## 使い方

Kabsch / ICP の相互共分散 ``H = (P − P̄)ᵀ (Q − Q̄)``(3×3)を、点の順に依らないビットで返す。

平均は ``math.fsum``(正確に丸めた和)、中心化は要素ごと、縮約は :func:`matmul_reproducible`。P と Q は行ごとに
対応する (N, 3)(N ≥ 3)。精度は FP64 の積と同じ水準(要素ごとに ``tol · (|P−P̄|ᵀ|Q−Q̄|)_ij`` + 数 ulp)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_reproducible_icp](../../../../examples/poc_reproducible_icp.py) — `py -3.11 examples/poc_reproducible_icp.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[world_camera](../world/world_camera.md) · [lidar_scan](../lidar/lidar_scan.md) · [relative_motion](../ttc/relative_motion.md) · [foe_from_motion](../ttc/foe_from_motion.md) · [flow_from_depth_motion](../ttc/flow_from_depth_motion.md) · [ttc_truth](../ttc/ttc_truth.md) · [world_materials](../terrain/world_materials.md) · [mesh_signed_volume](../terrain/mesh_signed_volume.md)

## 同カテゴリ(`ozaki`)

[matmul_ozaki](matmul_ozaki.md) · [matmul_reproducible](matmul_reproducible.md) · [ozaki_error_bound](ozaki_error_bound.md) · [kabsch_reproducible](kabsch_reproducible.md) · [fp64_emulation_probe](fp64_emulation_probe.md)

---
*Provenance: ozakimm.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
