---
op: spoon_bowl_volume
dim: drive
category: scoop
in: scalar × scalar
out: table
examples: [poc_powder_scoop_pour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# spoon_bowl_volume — DRIVE `scoop` op

- **データ種**: `scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.spoon_bowl_volume(a: 'float', h: 'float', *, fill_depth: 'float | None' = None, phi_deg: 'float | None' = None) -> 'dict'` (実装を直接呼ぶなら `import scoop; scoop.spoon_bowl_volume(a: 'float', h: 'float', *, fill_depth: 'float | None' = None, phi_deg: 'float | None' = None) -> 'dict'`、台帳から引くなら `opsdrive.get("spoon_bowl_volume")`)

## 使い方

球冠の椀(縁の半径 ``a``、深さ ``h``)の閉形式 —— すり切り・途中まで・山盛り。

球の半径 ``R = (a² + h²) / (2h)``、すり切り ``V_struck = π h (3a² + h²) / 6``。``fill_depth = y`` を与えると底から
``y`` まで平らに満たした体積 ``V_fill = π y² (3R − y) / 3``(``y = h`` で ``V_struck`` に一致する恒等式)。
``phi_deg`` を与えると縁を底面とする安息角 φ の円錐(山盛りの上限)``V_heap = (π/3) a³ tan φ``、高さ ``a tan φ``、
``V_heaped = V_struck + V_heap``、山盛り / すり切りの比。
返り: ``R``, ``V_struck``, ``V_fill``(与えたとき)、``V_heap`` / ``H_heap`` / ``V_heaped`` / ``heaped_ratio``(φ を与えたとき)。
**Raises** ``ValueError``: ``a``・``h`` が ≤ 0、``h > a``(半球より深い椀は縁が最も広い所でなく、側面から上だけを
見る :func:`scoop_volume_read` の前提が崩れる)、``fill_depth`` が ``(0, h]`` の外、φ が (0, 90) の外。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_powder_scoop_pour](../../../../examples/poc_powder_scoop_pour.py) — `py -3.11 examples/poc_powder_scoop_pour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`scoop`)

[scoop_synth_side](scoop_synth_side.md) · [revolution_volume_side](revolution_volume_side.md) · [two_view_volume](two_view_volume.md) · [scoop_volume_read](scoop_volume_read.md) · [scoop_count](scoop_count.md) · [scoop_image_limit](scoop_image_limit.md) · [tilt_wedge_retained](tilt_wedge_retained.md) · [tilt_pour_rate](tilt_pour_rate.md)

---
*Provenance: scoop.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
