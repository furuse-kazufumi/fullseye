---
op: stream_synth
dim: drive
category: scoop
in: scalar × scalar × scalar
out: table
examples: [poc_powder_scoop_pour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# stream_synth — DRIVE `scoop` op

- **データ種**: `scalar × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.stream_synth(flux: 'float', radius: 'float', width: 'float', *, v0: 'float' = 0.3, s0: 'float' = 0.02, rows: 'int' = 192, cols: 'int' = 64, pitch: 'float' = 0.0005, dt: 'float' = 0.0015, n_frames: 'int' = 16, supersample: 'int' = 4, seed: 'int | None' = 0) -> 'dict'` (実装を直接呼ぶなら `import scoop; scoop.stream_synth(flux: 'float', radius: 'float', width: 'float', *, v0: 'float' = 0.3, s0: 'float' = 0.02, rows: 'int' = 192, cols: 'int' = 64, pitch: 'float' = 0.0005, dt: 'float' = 0.0015, n_frames: 'int' = 16, supersample: 'int' = 4, seed: 'int | None' = 0) -> 'dict'`、台帳から引くなら `opsdrive.get("stream_synth")`)

## 使い方

口から落ちる粉の流れ(横から見た薄い帯)の被覆率のコマ列を合成する。

粒は Poisson 過程(率 ``flux`` [個/s])で口を離れ、横位置は幅 ``width`` に一様、初速 ``v0`` で自由落下
``s = v₀ τ + ½ g τ²``(口からの落下距離 ``s``)。画像の行 0 は ``s = s0``、1 画素 ``pitch``。半径 ``radius`` の円板の和
(副標本 ``supersample``² の被覆率)。位置が独立なので被覆率は Boolean 模型に従う —— 合成器はその式を使わない
(:func:`stream_areal_density` の独立な被験者)。
返り: ``frames``(``n_frames`` 枚)、``dt``、``pitch``、``s_rows``(行中心の落下距離)、``truth``(``flux``、
``crossings``(行中心の各高さを ``[0, n_frames·dt)`` に横切った実数の個数 / 時間 = 実現した流量)、``v``(行中心の
自由落下の速さ)、``radius_px``)。**Raises** ``ValueError``: 引数の範囲。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_powder_scoop_pour](../../../../examples/poc_powder_scoop_pour.py) — `py -3.11 examples/poc_powder_scoop_pour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`scoop`)

[spoon_bowl_volume](spoon_bowl_volume.md) · [scoop_synth_side](scoop_synth_side.md) · [revolution_volume_side](revolution_volume_side.md) · [two_view_volume](two_view_volume.md) · [scoop_volume_read](scoop_volume_read.md) · [scoop_count](scoop_count.md) · [scoop_image_limit](scoop_image_limit.md) · [tilt_wedge_retained](tilt_wedge_retained.md)

---
*Provenance: scoop.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
