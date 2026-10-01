---
op: flash_frequency
dim: drive
category: decide
in: signal
out: table
examples: [poc_driving_decisions]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# flash_frequency — DRIVE `decide` op

- **データ種**: `signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.flash_frequency(intensity_series, fps, *, f_min: 'float' = 0.0, pad: 'int' = 8) -> 'Dict[str, float]'` (実装を直接呼ぶなら `import drivedecide; drivedecide.flash_frequency(intensity_series, fps, *, f_min: 'float' = 0.0, pad: 'int' = 8) -> 'Dict[str, float]'`、台帳から引くなら `opsdrive.get("flash_frequency")`)

## 使い方

画素(または領域の平均)の明るさの時系列から点滅の周波数を推定する(FFT のいちばん高い山)。

平均を引き、Hann 窓をかけ、``pad`` 倍に 0 を詰めて rFFT。``f_min`` 以上でいちばん高い山を対数振幅の放物線で
補間する。返る周波数は **見かけの** 周波数(fps/2 を超える点滅は ``aliased_frequency`` の値に折り返って見える)。

返り値: ``frequency``、``bin_width`` = fps / n(窓の分解能の目安)、``nyquist`` = fps/2、``peak_ratio``(山の高さ /
山以外の中央値。点滅していない画素は小さい)。一定の系列(振れ幅 0)は ValueError。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_decisions](../../../../examples/poc_driving_decisions.py) — `py -3.11 examples/poc_driving_decisions.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`decide`)

[mirror_reflection_matrix](mirror_reflection_matrix.md) · [mirror_virtual_camera](mirror_virtual_camera.md) · [mirror_aim_normal](mirror_aim_normal.md) · [convex_mirror_fov](convex_mirror_fov.md) · [mirror_blind_zone](mirror_blind_zone.md) · [check_sequence_score](check_sequence_score.md) · [signal_phase_plan](signal_phase_plan.md) · [signal_state](signal_state.md)

---
*Provenance: drivedecide.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
