---
op: matmul_ozaki
dim: drive
category: ozaki
in: matrix × matrix
out: matrix
examples: [poc_reproducible_icp]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# matmul_ozaki — DRIVE `ozaki` op

- **データ種**: `matrix × matrix` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.matmul_ozaki(A, B, n_slices=None, scheme: 'str' = 'ozaki1', tol: 'float' = 1.1102230246251565e-16, on_insufficient: 'str' = 'raise', return_info: 'bool' = False)` (実装を直接呼ぶなら `import ozakimm; ozakimm.matmul_ozaki(A, B, n_slices=None, scheme: 'str' = 'ozaki1', tol: 'float' = 1.1102230246251565e-16, on_insufficient: 'str' = 'raise', return_info: 'bool' = False)`、台帳から引くなら `opsdrive.get("matmul_ozaki")`)

## 使い方

FP64 の精度の行列積 ``A @ B`` を、正確な低精度の部分積から組む(Ozaki-I / Ozaki-II)。

``scheme="ozaki1"``: ``n_slices`` 枚に切る(積 ``n(n+1)/2`` 回)。``n_slices=None`` なら、誤差の保証上界が
``tol · (|A||B|)_ij`` 以下になる最少の枚数を自動で選ぶ(1〜16 枚)。届かなければ ``on_insufficient="raise"`` で
``ValueError``、``"fallback"`` で普通の float64 の積を返す(この場合だけ再現性の約束は外れる。``return_info=True``
の ``fallback`` で分かる)。
``scheme="ozaki2"``: 法の数を ``n_slices``(2〜20)で必ず指定する(積 ``n`` 回)。自動の選択は無い。
``return_info=True`` で ``(C, info)``(``n_slices``・``n_products``・``scheme``・``fallback``)。

どちらの方式も、同じ入力なら内側の並べ替え・BLAS のスレッド数に依らず同じビット。CPU では DGEMM より 1〜2 桁遅い
(module の docstring の使い分けを参照)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_reproducible_icp](../../../../examples/poc_reproducible_icp.py) — `py -3.11 examples/poc_reproducible_icp.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[world_camera](../world/world_camera.md) · [lidar_scan](../lidar/lidar_scan.md) · [relative_motion](../ttc/relative_motion.md) · [foe_from_motion](../ttc/foe_from_motion.md) · [flow_from_depth_motion](../ttc/flow_from_depth_motion.md) · [ttc_truth](../ttc/ttc_truth.md) · [world_materials](../terrain/world_materials.md) · [mesh_signed_volume](../terrain/mesh_signed_volume.md)

## 同カテゴリ(`ozaki`)

[matmul_reproducible](matmul_reproducible.md) · [ozaki_error_bound](ozaki_error_bound.md) · [cross_covariance_reproducible](cross_covariance_reproducible.md) · [kabsch_reproducible](kabsch_reproducible.md) · [fp64_emulation_probe](fp64_emulation_probe.md)

---
*Provenance: ozakimm.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
