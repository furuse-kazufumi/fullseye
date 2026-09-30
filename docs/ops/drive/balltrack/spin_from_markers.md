---
op: spin_from_markers
dim: drive
category: balltrack
in: points × points
out: table
examples: [poc_ball_bounce, poc_table_tennis_spin]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# spin_from_markers — DRIVE `balltrack` op

- **データ種**: `points × points` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.spin_from_markers(dirs0, dirs1, dt: 'float') -> 'dict'` (実装を直接呼ぶなら `import balltrack; balltrack.spin_from_markers(dirs0, dirs1, dt: 'float') -> 'dict'`、台帳から引くなら `opsdrive.get("spin_from_markers")`)

## 使い方

模様の向きの組(前 (M, 3)、後 (M, 3)、単位ベクトル)から角速度ベクトル ω [rad/s] を出す。

M ≥ 2 なら Kabsch(SVD)で回転 R を当て、回転角 θ と軸から ω = θ/dt·軸(既知の ω で回した向きを入れると 1e-9 で戻る = 門)。
M = 1 なら d₀ → d₁ の最小回転(軸 = d₀ × d₁)を返す("full" = False): 模様の向きまわりの成分は原理的に決まらず、
コマ間の回転角が大きいと ω の直交成分の近似としても外れる(模様は ω の軸まわりの小円を描くので、最小回転の大円と違う)。
正直に: 1 つの模様で ω を出したいなら dt を小さく(回転角 ≪ 1 rad)、それでも軸まわりの成分は別の模様が要る。
返り値 ``{"omega", "angle", "axis", "R", "full", "rms"}``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_ball_bounce](../../../../examples/poc_ball_bounce.py) — `py -3.11 examples/poc_ball_bounce.py`
- [poc_table_tennis_spin](../../../../examples/poc_table_tennis_spin.py) — `py -3.11 examples/poc_table_tennis_spin.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`balltrack`)

[ball_detect](ball_detect.md) · [ball_track](ball_track.md) · [kalman_ca](kalman_ca.md) · [triangulate_dlt](triangulate_dlt.md) · [track_triangulate](track_triangulate.md) · [bounce_detect](bounce_detect.md) · [marker_direction](marker_direction.md) · [reproject](reproject.md)

---
*Provenance: balltrack.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
