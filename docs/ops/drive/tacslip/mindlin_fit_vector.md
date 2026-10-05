---
op: mindlin_fit_vector
dim: drive
category: tacslip
in: table × matrix × matrix
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# mindlin_fit_vector — DRIVE `tacslip` op

- **データ種**: `table × matrix × matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.mindlin_fit_vector(model: 'dict', pts_px, u_m, n_coarse: 'int' = 51, n_fine: 'int' = 21) -> 'dict'` (実装を直接呼ぶなら `import tacslip; tacslip.mindlin_fit_vector(model: 'dict', pts_px, u_m, n_coarse: 'int' = 51, n_fine: 'int' = 21) -> 'dict'`、台帳から引くなら `opsdrive.get("mindlin_fit_vector")`)

## 使い方

向きを持つせん断の Mindlin 当てはめ(:func:`mindlin_fit` の 2 成分版): (c/a, μP, 向き φ) を一度に読む。

比例載荷では接線トラクションは同じ半径分布 × 方向ベクトルなので、場は u(p) = A·F_x(p; c) + B·F_y(p; c)(F_y は x 向きの単位場
F_x を 90° 回した場 R(90°)F_x(R(−90°)p)、核は等方な半空間なので回転で閉じる)—— 各 c/a で (A, B) は線形の最小二乗。
μP = √(A² + B²)、φ = atan2(B, A)、Q = μP(1 − (c/a)³)。c/a は粗く走査 → 最良の周りを細かく。
向きを先に「固着核の平均変位」で決めて 1 成分の :func:`mindlin_fit` に回す版は、規則格子の位相で核の標本が非対称になり 0.5° 前後の
偏り(純 v のせん断に 0.01 N の偽の u 成分)を出した(pegtactile の試作で測って捨てた)。
返り ``c_over_a``・``q_ratio``・``muP``・``Q``・``phi``・``rms_m``。**Raises** ``ValueError``: 形の不一致、点が 3 個未満。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tacslip`)

[mindlin_partial_slip](mindlin_partial_slip.md) · [mindlin_traction](mindlin_traction.md) · [hertz_surface_ur](hertz_surface_ur.md) · [hertzian_tangential_inner](hertzian_tangential_inner.md) · [cerruti_kernel](cerruti_kernel.md) · [cerruti_surface_displacement](cerruti_surface_displacement.md) · [membrane_shear_field](membrane_shear_field.md) · [membrane_markers](membrane_markers.md)

---
*Provenance: tacslip.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
