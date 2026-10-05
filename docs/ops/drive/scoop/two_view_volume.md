---
op: two_view_volume
dim: drive
category: scoop
in: image2d × image2d × scalar
out: table
examples: [poc_powder_scoop_pour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# two_view_volume — DRIVE `scoop` op

- **データ種**: `image2d × image2d × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.two_view_volume(side_a, side_b, pitch: 'float', *, threshold: 'float' = 0.5) -> 'dict'` (実装を直接呼ぶなら `import scoop; scoop.two_view_volume(side_a, side_b, pitch: 'float', *, threshold: 'float' = 0.5) -> 'dict'`、台帳から引くなら `opsdrive.get("two_view_volume")`)

## 使い方

直交する 2 方向の側面像から体積 —— 行ごとの 2 つの弦 ``W_a``・``W_b`` を軸とする楕円の和
``V = Σ f π (W_a/2)(W_b/2) pitch³``。

断面が楕円(軸対称でない山、縦長の盛り)なら厳密で、片方だけの回転体の仮定は楕円の扁平さの比で外れる(PoC で
1.6 : 1 の楕円錐が片方だと −38 % / +60 %)。行の満ち具合 ``f``(平らな面が行の途中を横切る行、像 a で読む)で弦を
``W = w / f`` に直してから掛ける(幅の積は ``f²`` で数え落とすため)。雑音は先に消す。2 枚は同じ高さの刻み(同じ行が
同じ高さ)であること。返り: ``V``、``V_a`` / ``V_b``(片方だけの回転体、Pappus)、``ellipticity``(弦の比の中央値
max/min)。**Raises** ``ValueError``: 行数が違う / 被覆率でない / 空。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_powder_scoop_pour](../../../../examples/poc_powder_scoop_pour.py) — `py -3.11 examples/poc_powder_scoop_pour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`scoop`)

[spoon_bowl_volume](spoon_bowl_volume.md) · [scoop_synth_side](scoop_synth_side.md) · [revolution_volume_side](revolution_volume_side.md) · [scoop_volume_read](scoop_volume_read.md) · [scoop_count](scoop_count.md) · [scoop_image_limit](scoop_image_limit.md) · [tilt_wedge_retained](tilt_wedge_retained.md) · [tilt_pour_rate](tilt_pour_rate.md)

---
*Provenance: scoop.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
