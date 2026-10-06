---
op: contact_state_predict
dim: drive
category: pegsim
in: table
out: table
examples: [poc_pegsim_insertion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# contact_state_predict — DRIVE `pegsim` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.contact_state_predict(kp, tip_xyz, axis, tol: 'float' = 6e-05) -> 'dict'` (実装を直接呼ぶなら `import pegsim; pegsim.contact_state_predict(kp, tip_xyz, axis, tol: 'float' = 6e-05) -> 'dict'`、台帳から引くなら `opsdrive.get("contact_state_predict")`)

## 使い方

真のペグ姿勢(先端中心と軸の向き)から、接触点の数と場所を**幾何だけで**予測する(接触計算と独立な第 2 実装)。

先端の縁の円(半径 r、水平投影は e₁ 方向 r・傾き方向 r cos θ の楕円)が穴の最狭部の円 R(面取り帯では高さに応じた円錐の半径)に
届けば「tip」、胴の最狭部(z = −W)での水平断面(半径 r と r/cos θ の楕円)が R に届けば「mouth」。胴が面取りの円錐に触れる
場所は tan θ < 1 なら必ず最狭部の縁になる(円錐の半径は高さに 1 で増え、断面の中心は tan θ でしか動かない)。
返り: ``n``(0/1/2)、``where``("none" / "chamfer" / "tip" / "mouth" / "tip+mouth")、``depth``(口の面からの先端深さ、
負なら空中)、``depth_below_chamfer``、``tilt`` [rad]。``tol`` は「届いた」とみなす半径方向の余裕。
**Raises** ``ValueError``: axis がゼロ、tip_xyz の形が (3,) でない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_pegsim_insertion](../../../../examples/poc_pegsim_insertion.py) — `py -3.11 examples/poc_pegsim_insertion.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegsim`)

[peg_params](peg_params.md) · [whitney_clearance](whitney_clearance.md) · [two_point_depth](two_point_depth.md) · [wedging_check](wedging_check.md) · [jamming_diagram](jamming_diagram.md) · [chamfer_capture](chamfer_capture.md) · [circle_fit_known_radius](circle_fit_known_radius.md) · [cylinder_fit_known_radius](cylinder_fit_known_radius.md)

---
*Provenance: pegsim.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
