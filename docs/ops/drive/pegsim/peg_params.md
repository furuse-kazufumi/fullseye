---
op: peg_params
dim: drive
category: pegsim
in: 
out: table
examples: [poc_peg_failure_recovery, poc_peg_insertion_tactile, poc_pegsim_insertion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# peg_params — DRIVE `pegsim` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.peg_params(r: 'float' = 0.005, R: 'float' = 0.0052, hole_depth: 'float' = 0.02, chamfer: 'float' = 0.001, chamfer_deg: 'float' = 45.0, peg_length: 'float' = 0.04, mu: 'float' = 0.3, n_seg: 'int' = 36, k_trans: 'float' = 600.0, k_rot: 'float' = 1.5, image_size=(640, 480), fovy_deg: 'float' = 40.0) -> 'dict'` (実装を直接呼ぶなら `import pegsim; pegsim.peg_params(r: 'float' = 0.005, R: 'float' = 0.0052, hole_depth: 'float' = 0.02, chamfer: 'float' = 0.001, chamfer_deg: 'float' = 45.0, peg_length: 'float' = 0.04, mu: 'float' = 0.3, n_seg: 'int' = 36, k_trans: 'float' = 600.0, k_rot: 'float' = 1.5, image_size=(640, 480), fovy_deg: 'float' = 40.0) -> 'dict'`、台帳から引くなら `opsdrive.get("peg_params")`)

## 使い方

ペグと穴の寸法の表(m・rad): ペグ半径 r、穴半径 R、穴の深さ、面取りの幅と角、ペグ長、摩擦係数、手首剛性、手首カメラ。

既定は試作の寸法: r = 5.0 mm、R = 5.2 mm(半径 clearance 0.2 mm、c = 0.0385)、深さ 20 mm、45° の面取り 1 mm、ペグ 40 mm、
μ = 0.3(MuJoCo の滑り摩擦)。``n_seg`` は穴の壁を近似する箱の数(MJCF)、``k_trans`` [N/m]・``k_rot`` [N m/rad] は
手首(コンプライアント支持)の並進・回転剛性、``image_size`` と ``fovy_deg`` は手首カメラ。
**Raises** ``ValueError``: r ≤ 0、R ≤ r、面取りが穴より深い、μ < 0、面取り角が (0°, 90°) の外。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_failure_recovery](../../../../examples/poc_peg_failure_recovery.py) — `py -3.11 examples/poc_peg_failure_recovery.py`
- [poc_peg_insertion_tactile](../../../../examples/poc_peg_insertion_tactile.py) — `py -3.11 examples/poc_peg_insertion_tactile.py`
- [poc_pegsim_insertion](../../../../examples/poc_pegsim_insertion.py) — `py -3.11 examples/poc_pegsim_insertion.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegsim`)

[whitney_clearance](whitney_clearance.md) · [two_point_depth](two_point_depth.md) · [wedging_check](wedging_check.md) · [jamming_diagram](jamming_diagram.md) · [chamfer_capture](chamfer_capture.md) · [contact_state_predict](contact_state_predict.md) · [circle_fit_known_radius](circle_fit_known_radius.md) · [cylinder_fit_known_radius](cylinder_fit_known_radius.md)

---
*Provenance: pegsim.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
