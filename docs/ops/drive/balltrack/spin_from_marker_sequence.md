---
op: spin_from_marker_sequence
dim: drive
category: balltrack
in: any
out: table
examples: [poc_table_tennis_bounce, poc_table_tennis_spin]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# spin_from_marker_sequence — DRIVE `balltrack` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.spin_from_marker_sequence(dirs, dt: 'float', *, lag: 'int' = 4, max_angle: 'float' = 0.5) -> 'dict'` (実装を直接呼ぶなら `import balltrack; balltrack.spin_from_marker_sequence(dirs, dt: 'float', *, lag: 'int' = 4, max_angle: 'float' = 0.5) -> 'dict'`、台帳から引くなら `opsdrive.get("spin_from_marker_sequence")`)

## 使い方

コマの列の模様の向き ``dirs[k]``((M_k, 3) の単位ベクトル、見つからないコマは None)から角速度を読む(2 段)。

1 段目: 隣のコマ同士で、向きが ``max_angle`` [rad] 以内で最も近い模様を組にして Kabsch(:func:`spin_from_markers`)、
その中央値を ω₁ とする。2 段目: ``lag`` コマ離れた組を、前のコマを ω₁ で回した予測に最も近い模様(``max_angle``/2 以内)と
組んで当て直す —— 回転角が lag 倍になるので、模様の位置の誤差が効く割合は 1/lag。★1 コマの回転角は ``max_angle``
より十分小さいこと(模様の取り違え)、lag コマの回転は π より小さいこと(Kabsch は最短の回転を返す)。
返り値 ``{"omega", "omega_stage1", "n_pairs", "per_pair" (N, 3)}``(ω は dirs と同じ座標系)。組が 1 つも無ければ
ω は NaN。模様が見えた向きの組が要るので、各コマ 2 個以上の模様が要る。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_table_tennis_bounce](../../../../examples/poc_table_tennis_bounce.py) — `py -3.11 examples/poc_table_tennis_bounce.py`
- [poc_table_tennis_spin](../../../../examples/poc_table_tennis_spin.py) — `py -3.11 examples/poc_table_tennis_spin.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`balltrack`)

[ball_detect](ball_detect.md) · [ball_track](ball_track.md) · [kalman_ca](kalman_ca.md) · [triangulate_dlt](triangulate_dlt.md) · [track_triangulate](track_triangulate.md) · [bounce_detect](bounce_detect.md) · [marker_direction](marker_direction.md) · [spin_from_markers](spin_from_markers.md)

---
*Provenance: balltrack.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
