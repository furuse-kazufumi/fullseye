---
op: lights_fit_from_sphere
dim: drive
category: tacscalib
in: rgb × normalmap × image2d
out: table
examples: [poc_tacscalib_sphere_lut]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# lights_fit_from_sphere — DRIVE `tacscalib` op

- **データ種**: `rgb × normalmap × image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.lights_fit_from_sphere(diffs, normals, masks, order: 'int' = 0) -> 'dict'` (実装を直接呼ぶなら `import tacscalib; tacscalib.lights_fit_from_sphere(diffs, normals, masks, order: 'int' = 0) -> 'dict'`、台帳から引くなら `opsdrive.get("lights_fit_from_sphere")`)

## 使い方

背景差分画像(1 枚か列)と既知法線から、チャネルごとの線形 Lambertian 模型を最小二乗で解く。

``order=0``: I_c = a_c + l_c · n(3 チャネル × 4 = 12 パラメタ)。``order=2``(診断用): 4 つの係数それぞれが位置の 2 次式
(チャネルあたり 24、計 72 パラメタ)—— 線形模型の残差が「照明の非一様」か「反射の非線形」かを分ける。
``diffs`` (H, W, 3) かその列、``normals`` (H, W, 3) の列、``masks`` (H, W) bool の列。

返り: ``order``、``L`` (3, 3)(行 c = l_c、長さ = チャネルの強度。order 2 は画像中心の値)、``ambient`` (3,)、``rms`` (3,)
(当てはめ残差)、``n_rows``(使った画素数)、``cond``(設計行列の条件数)、order 2 は ``coef`` (4, 6, 3) と ``image_shape``。
**Raises** ``ValueError``: 列の長さ・形の不一致 / order が 0・2 以外 / 画素が未知数より少ない / 法線が退化(平面上)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacscalib_sphere_lut](../../../../examples/poc_tacscalib_sphere_lut.py) — `py -3.11 examples/poc_tacscalib_sphere_lut.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tacscalib`)

[calib_pack_load](calib_pack_load.md) · [sphere_normals_known](sphere_normals_known.md) · [membrane_predict_rgb](membrane_predict_rgb.md) · [gradient_lut_build](gradient_lut_build.md) · [gradient_lut_invert](gradient_lut_invert.md) · [normal_error_map](normal_error_map.md) · [sphere_cap_height](sphere_cap_height.md) · [field_position_sweep](field_position_sweep.md)

---
*Provenance: tacscalib.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
