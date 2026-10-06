---
op: mirror_virtual_camera
dim: drive
category: decide
in: any
out: table
examples: [poc_driving_decisions]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# mirror_virtual_camera — DRIVE `decide` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.mirror_virtual_camera(cam_pose, mirror_plane) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivedecide; drivedecide.mirror_virtual_camera(cam_pose, mirror_plane) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("mirror_virtual_camera")`)

## 使い方

平面鏡に映る像を撮る **仮想カメラ**。

``cam_pose`` は world→camera の 4×4(``render3d.look_at`` の規約: X_cam = P X、−Z 前方)。``mirror_plane`` は
(n_x, n_y, n_z, d)(n·X = d)。

返り値(dict):

* ``reflection``: 折り返し S(``mirror_reflection_matrix``)。
* ``pose_mirrored`` = P·S: 実物の場面をこれで写すと、実カメラが **鏡越しに見る像そのもの**(画素の位置まで同じ)。
  回転部の行列式は −1(左右が反転した座標系。描画器によっては面の表裏の判定が逆になる)。
* ``pose`` = F·P·S、F = diag(−1, 1, 1, 1): 普通の右手系のカメラ(行列式 +1)= 鏡の向こうにいる仮想カメラ。
  これで撮った画像は鏡に映る像の **左右反転**(画素では u' = 2c_x − u)。バックミラーを「後ろ向きのカメラ」と
  して扱うときはこちら(運転者が見る像に戻すには左右を反転する)。
* ``eye``: 仮想カメラの位置 S(C)(C = 実カメラの位置)。``eye_real``: C。
* ``flip``: ``"x"``(``pose`` の画像は x を反転すると鏡像になる)。

閉形式: S(X) = X − 2(n·X − d)n。鏡に映る点 Q の像の位置は S(Q)(鏡の向こう側、鏡面から同じ距離)。
門(テスト): 入射角 = 反射角を満たす鏡面上の点 M を数値で解き(Fermat の最短経路)、C + (|CM| + |MQ|)·unit(M − C)
が S(Q) と一致すること。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_decisions](../../../../examples/poc_driving_decisions.py) — `py -3.11 examples/poc_driving_decisions.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`decide`)

[mirror_reflection_matrix](mirror_reflection_matrix.md) · [mirror_aim_normal](mirror_aim_normal.md) · [convex_mirror_fov](convex_mirror_fov.md) · [mirror_blind_zone](mirror_blind_zone.md) · [check_sequence_score](check_sequence_score.md) · [signal_phase_plan](signal_phase_plan.md) · [signal_state](signal_state.md) · [predict_amber_onset](predict_amber_onset.md)

---
*Provenance: drivedecide.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
