---
op: detector_two_theta
dim: drive
category: pxrd
in: any × table
out: table
examples: [poc_pxrd_phase_peel]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# detector_two_theta — DRIVE `pxrd` op

- **データ種**: `any × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.detector_two_theta(shape, geometry)` (実装を直接呼ぶなら `import pxrd; pxrd.detector_two_theta(shape, geometry)`、台帳から引くなら `opsdrive.get("detector_two_theta")`)

## 使い方

検出器の各画素の 2θ・方位 χ・相対立体角(傾き・距離・中心つき)。

``shape = (H, W)``、``geometry`` は module の docstring の Fit2D 型。返り値(dict): ``two_theta`` [deg]・``chi`` [deg]
(``atan2``、+列が 0、+行が +90)・``solid_angle``(ビームの中心で傾き 0 のとき 1 になる相対値、``cos³`` で落ちる)。
2θ は ``atan2(hypot(Pₓ, P_y), P_z)`` で求める(acos を使うと 2θ → 0 の近くで丸めの床が出る)。

Raises ValueError: 形が 2 要素の正の整数でない、幾何の鍵の欠け・綴り違い、``|tilt| >= 60``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_pxrd_phase_peel](../../../../examples/poc_pxrd_phase_peel.py) — `py -3.11 examples/poc_pxrd_phase_peel.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pxrd`)

[cif_read](cif_read.md) · [cubic_prototype](cubic_prototype.md) · [powder_reflections](powder_reflections.md) · [scherrer_size](scherrer_size.md) · [debye_ring_image](debye_ring_image.md) · [detector_calibrate](detector_calibrate.md) · [azimuthal_integrate](azimuthal_integrate.md) · [diffraction_peaks](diffraction_peaks.md)

---
*Provenance: pxrd.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
