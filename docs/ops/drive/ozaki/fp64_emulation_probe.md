---
op: fp64_emulation_probe
dim: drive
category: ozaki
in: 
out: table
examples: [poc_reproducible_icp]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# fp64_emulation_probe — DRIVE `ozaki` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.fp64_emulation_probe()` (実装を直接呼ぶなら `import ozakimm; ozakimm.fp64_emulation_probe()`、台帳から引くなら `opsdrive.get("fp64_emulation_probe")`)

## 使い方

cuBLAS の FP64 エミュレーション(CUDA 13.0 Update 2 以降)が、この計算機で使えるかを表で返す。

**例外を出さない**: GPU・CUDA・cuBLAS 13 が無ければ ``available=False`` と理由を返す(重い依存は持たない。ctypes で
ライブラリを開いて版を読むだけ)。返り: ``available``(bool)、``rows``(候補ごとの ``library``・``path``・``loaded``・
``cublas_version``・``emulation_api``(``cublasSetEmulationStrategy`` があるか)・``gpu``(ハンドルを作れたか)・
``reason``)、``how``(有効にする方法)、``note``。

有効にする方法は opt-in: math mode ``CUBLAS_FP64_EMULATED_FIXEDPOINT_MATH``、またはコードを変えずに
``CUBLAS_EMULATE_DOUBLE_PRECISION=1``。cuBLAS の文書はエミュレーション中はビット単位の再現の保証が外れると書く
—— 再現が要るなら :func:`matmul_reproducible`。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_reproducible_icp](../../../../examples/poc_reproducible_icp.py) — `py -3.11 examples/poc_reproducible_icp.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`ozaki`)

[matmul_ozaki](matmul_ozaki.md) · [matmul_reproducible](matmul_reproducible.md) · [ozaki_error_bound](ozaki_error_bound.md) · [cross_covariance_reproducible](cross_covariance_reproducible.md) · [kabsch_reproducible](kabsch_reproducible.md)

---
*Provenance: ozakimm.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
