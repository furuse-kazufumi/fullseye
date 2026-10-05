---
op: ozaki_error_bound
dim: drive
category: ozaki
in: matrix × matrix × scalar
out: matrix
examples: [poc_reproducible_icp]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# ozaki_error_bound — DRIVE `ozaki` op

- **データ種**: `matrix × matrix × scalar` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.ozaki_error_bound(A, B, n_slices: 'int')` (実装を直接呼ぶなら `import ozakimm; ozakimm.ozaki_error_bound(A, B, n_slices: 'int')`、台帳から引くなら `opsdrive.get("ozaki_error_bound")`)

## 使い方

``matmul_ozaki(A, B, n_slices)``(Ozaki-I)の打ち切り誤差の要素ごとの保証上界(行列)。

切り捨ての残りと捨てた切れ端の組の和の上界で、最後の float64 の組み立ての丸め(``(s+1) u |A||B|`` 程度)は含めない。
門では 26 万点余りの要素で破れ 0(PoC と tests)。並べ替えた和で計算するので、上界そのものも内側の順に依らない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_reproducible_icp](../../../../examples/poc_reproducible_icp.py) — `py -3.11 examples/poc_reproducible_icp.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[world_camera](../world/world_camera.md) · [lidar_scan](../lidar/lidar_scan.md) · [relative_motion](../ttc/relative_motion.md) · [foe_from_motion](../ttc/foe_from_motion.md) · [flow_from_depth_motion](../ttc/flow_from_depth_motion.md) · [ttc_truth](../ttc/ttc_truth.md) · [world_materials](../terrain/world_materials.md) · [mesh_signed_volume](../terrain/mesh_signed_volume.md)

## 同カテゴリ(`ozaki`)

[matmul_ozaki](matmul_ozaki.md) · [matmul_reproducible](matmul_reproducible.md) · [cross_covariance_reproducible](cross_covariance_reproducible.md) · [kabsch_reproducible](kabsch_reproducible.md) · [fp64_emulation_probe](fp64_emulation_probe.md)

---
*Provenance: ozakimm.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
