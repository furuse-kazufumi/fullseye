---
op: scoop_volume_read
dim: drive
category: scoop
in: image2d × scalar × scalar × scalar × scalar
out: table
examples: [poc_powder_scoop_pour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# scoop_volume_read — DRIVE `scoop` op

- **データ種**: `image2d × scalar × scalar × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.scoop_volume_read(side, rim_row: 'int', a_px: 'float', h_px: 'float', pitch: 'float', *, opaque: 'bool' = True, assume_level: 'bool' = False, heap_min_frac: 'float' = 0.005, level_tol: 'float' = 0.01, rim_full_frac: 'float' = 0.95, fit_angle: 'bool' = True) -> 'dict'` (実装を直接呼ぶなら `import scoop; scoop.scoop_volume_read(side, rim_row: 'int', a_px: 'float', h_px: 'float', pitch: 'float', *, opaque: 'bool' = True, assume_level: 'bool' = False, heap_min_frac: 'float' = 0.005, level_tol: 'float' = 0.01, rim_full_frac: 'float' = 0.95, fit_angle: 'bool' = True) -> 'dict'`、台帳から引くなら `opsdrive.get("scoop_volume_read")`)

## 使い方

スプーンの側面像からすくった体積を読む。

- ``opaque=True``(金属の椀): 縁より下は見えないので、縁より上の山を :func:`revolution_volume_side` で測り、
  すり切りの閉形式(:func:`spoon_bowl_volume`)に足す ``V = V_struck + V_above``。縁より上に何も無いと、すり切りか
  足りないかを側面から区別できない —— ``assume_level=True`` でなければ ``ValueError``(黙ってすり切りと言わない)。
- ``opaque=False``(透明な椀・断面の像): 全体を Pappus の形で積分し、すり切りの ``1 − level_tol`` に満たなければ
  ``under`` として深さを閉形式 ``V_fill(y)`` の逆(二分法)で返す(平らな粉面を仮定)。
- ``fit_angle``: 山が十分大きければ(左右 8 点以上)縁を地面とみなして granular の ``repose_angle_silhouette`` で
  山の斜面の角を読む(安息角との照合用、小さな山では ``None``)。
返り: ``V``, ``V_struck``, ``V_above``, ``state``(``heaped`` / ``level`` / ``under``)、``heap_angle_deg``、
``heap_base_frac``(縁の行の山の幅 / 縁の直径)、``rim_full``(``heap_base_frac ≥ rim_full_frac``: 山の裾が縁まで届いている =
椀が縁まで満ちている見込み。届いていない「山になりかけ」は縁の際が満ちきらず、不透明の読みは閉形式の分だけ多く出る ——
MuJoCo で 0.90 のとき +9 %、0.99 のとき +1 %)、``axis_col``、``fill_depth_px``(透明のとき)。
**Raises** ``ValueError``: ``rim_row`` が像の外 / 縁より上が空で ``assume_level`` でない(不透明のとき)/ 引数の範囲。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_powder_scoop_pour](../../../../examples/poc_powder_scoop_pour.py) — `py -3.11 examples/poc_powder_scoop_pour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`scoop`)

[spoon_bowl_volume](spoon_bowl_volume.md) · [scoop_synth_side](scoop_synth_side.md) · [revolution_volume_side](revolution_volume_side.md) · [two_view_volume](two_view_volume.md) · [scoop_count](scoop_count.md) · [scoop_image_limit](scoop_image_limit.md) · [tilt_wedge_retained](tilt_wedge_retained.md) · [tilt_pour_rate](tilt_pour_rate.md)

---
*Provenance: scoop.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
