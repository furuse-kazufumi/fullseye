---
op: matmul_reproducible
dim: drive
category: ozaki
in: matrix × matrix
out: matrix
examples: [poc_reproducible_icp]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# matmul_reproducible — DRIVE `ozaki` op

- **データ種**: `matrix × matrix` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.matmul_reproducible(A, B, tol: 'float' = 1.1102230246251565e-16)` (実装を直接呼ぶなら `import ozakimm; ozakimm.matmul_reproducible(A, B, tol: 'float' = 1.1102230246251565e-16)`、台帳から引くなら `opsdrive.get("matmul_reproducible")`)

## 使い方

ビット単位で再現する FP64 の精度の ``A @ B``(保証できなければ ``ValueError`` = fail-closed)。

:func:`matmul_ozaki` の Ozaki-I の自動選択に ``on_insufficient="raise"`` を固定したもの。誤差は要素ごとに
``tol · (|A||B|)_ij`` + 最後の組み立ての丸め(数 ulp)以下。内側の添字の順(点の順)・BLAS のスレッド数に依らず
同じビットを返す。点群の 3×N @ N×3 や 6×N @ N×6 の縮約向け(出力が大きい積では DGEMM の 15〜83 倍遅い)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_reproducible_icp](../../../../examples/poc_reproducible_icp.py) — `py -3.11 examples/poc_reproducible_icp.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[world_camera](../world/world_camera.md) · [lidar_scan](../lidar/lidar_scan.md) · [relative_motion](../ttc/relative_motion.md) · [foe_from_motion](../ttc/foe_from_motion.md) · [flow_from_depth_motion](../ttc/flow_from_depth_motion.md) · [ttc_truth](../ttc/ttc_truth.md) · [world_materials](../terrain/world_materials.md) · [mesh_signed_volume](../terrain/mesh_signed_volume.md)

## 同カテゴリ(`ozaki`)

[matmul_ozaki](matmul_ozaki.md) · [ozaki_error_bound](ozaki_error_bound.md) · [cross_covariance_reproducible](cross_covariance_reproducible.md) · [kabsch_reproducible](kabsch_reproducible.md) · [fp64_emulation_probe](fp64_emulation_probe.md)

---
*Provenance: ozakimm.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
