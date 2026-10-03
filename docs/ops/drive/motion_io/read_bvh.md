---
op: read_bvh
dim: drive
category: motion_io
in: 
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# read_bvh — DRIVE `motion_io` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.read_bvh(path) -> 'dict'` (実装を直接呼ぶなら `import motionio; motionio.read_bvh(path) -> 'dict'`、台帳から引くなら `opsdrive.get("read_bvh")`)

## 使い方

BVH を読み、骨格と全コマの関節の世界座標を返す。

Returns:
    ``names`` 関節名(End Site は ``<親>_end``)、``parents``(根は −1)、``offsets`` (J, 3)、
    ``positions`` (T, J, 3) 世界座標、``frame_time`` [s]、``channels``(関節ごとの CHANNELS の名前)、
    ``motion`` (T, C) の生の値。

Raises:
    ValueError: HIERARCHY / MOTION が無い、括弧の対応が崩れている、コマの値の数が CHANNELS の合計と違う。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`motion_io`)

[read_events](read_events.md) · [events_to_frames](events_to_frames.md)

---
*Provenance: motionio.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
