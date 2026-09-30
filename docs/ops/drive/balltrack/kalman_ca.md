---
op: kalman_ca
dim: drive
category: balltrack
in: points
out: table
examples: [poc_ball_bounce]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# kalman_ca — DRIVE `balltrack` op

- **データ種**: `points` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.kalman_ca(z, dt: 'float', *, q: 'float' = 1.0, r: 'float' = 1.0, x0=None, P0: 'float' = 1000.0) -> 'dict'` (実装を直接呼ぶなら `import balltrack; balltrack.kalman_ca(z, dt: 'float', *, q: 'float' = 1.0, r: 'float' = 1.0, x0=None, P0: 'float' = 1000.0) -> 'dict'`、台帳から引くなら `opsdrive.get("kalman_ca")`)

## 使い方

等加速度モデルの Kalman フィルタ(位置の観測 (N, D)、状態 = 位置・速度・加速度 × D)。

返り値 ``{"x" (N, 3D) 更新後, "x_pred" (N, 3D) 予測, "P" (N, 3D, 3D), "innovation" (N, D)}``。
``q`` = 加速度の変化の分散(白色ジャーク)、``r`` = 観測の分散。放物線の真値を入れると(モデルが厳密なので)収束後の
新息 → 0、r → 0 で更新後の位置 = 観測(門)。NaN の観測は予測だけ(欠測)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_ball_bounce](../../../../examples/poc_ball_bounce.py) — `py -3.11 examples/poc_ball_bounce.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`balltrack`)

[ball_detect](ball_detect.md) · [ball_track](ball_track.md) · [triangulate_dlt](triangulate_dlt.md) · [track_triangulate](track_triangulate.md) · [bounce_detect](bounce_detect.md) · [marker_direction](marker_direction.md) · [spin_from_markers](spin_from_markers.md) · [spin_from_marker_sequence](spin_from_marker_sequence.md)

---
*Provenance: balltrack.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
