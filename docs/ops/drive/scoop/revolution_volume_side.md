---
op: revolution_volume_side
dim: drive
category: scoop
in: image2d × scalar
out: table
examples: [poc_powder_scoop_pour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# revolution_volume_side — DRIVE `scoop` op

- **データ種**: `image2d × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.revolution_volume_side(side, pitch: 'float', *, axis_col: 'float | None' = None, threshold: 'float' = 0.5) -> 'dict'` (実装を直接呼ぶなら `import scoop; scoop.revolution_volume_side(side, pitch: 'float', *, axis_col: 'float | None' = None, threshold: 'float' = 0.5) -> 'dict'`、台帳から引くなら `opsdrive.get("revolution_volume_side")`)

## 使い方

側面像 1 枚から軸対称を仮定した体積 —— Pappus の形 ``V = π Σ |x − x_axis| c(x, z) pitch³``(``c`` = 被覆率、
``x`` = 画素の中心の列)。

被覆率に **線形** なので、平らな粉面が行の途中を横切る行でも偏らない(行ごとの幅を直径にした円板の和
``Σ π (w/2)²`` は、満ち具合 ``f`` の行を ``f²`` で数えて 1.5 % 低く出た、実測)。雑音は先に物の外と内で消す
(``_clean_coverage``)。軸 ``axis_col``(画素の端が整数)を与えなければ被覆率の重心の列。行ごとの重心に直線を
当てて軸の傾き ``axis_tilt_deg``(atan2)も返す(傾いた椀は体積が増える; 判定は呼び手)。
返り: ``V`` [pitch の単位の 3 乗]、``V_px``、``V_discs``(円板の和、比較用)、``radius_px``(行ごとの半幅)、``axis_col``、
``axis_tilt_deg``、``rows_used``、``height_px``。
**Raises** ``ValueError``: 被覆率でない / 粉が写っていない / 左右の縁に触れている(切れている)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_powder_scoop_pour](../../../../examples/poc_powder_scoop_pour.py) — `py -3.11 examples/poc_powder_scoop_pour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`scoop`)

[spoon_bowl_volume](spoon_bowl_volume.md) · [scoop_synth_side](scoop_synth_side.md) · [two_view_volume](two_view_volume.md) · [scoop_volume_read](scoop_volume_read.md) · [scoop_count](scoop_count.md) · [scoop_image_limit](scoop_image_limit.md) · [tilt_wedge_retained](tilt_wedge_retained.md) · [tilt_pour_rate](tilt_pour_rate.md)

---
*Provenance: scoop.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
