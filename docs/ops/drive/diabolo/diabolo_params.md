---
op: diabolo_params
dim: drive
category: diabolo
in: 
out: table
examples: [poc_diabolo_model_and_vision]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# diabolo_params — DRIVE `diabolo` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.diabolo_params(kind: 'str' = 'red', **override) -> 'dict'` (実装を直接呼ぶなら `import diabolo; diabolo.diabolo_params(kind: 'str' = 'red', **override) -> 'dict'`、台帳から引くなら `opsdrive.get("diabolo_params")`)

## 使い方

ディアボロと糸の寸法の辞書。``kind`` = red / blue / patterned / green(論文の表 I の質量・直径・長さ・軸受)。

論文に無い値は仮定として ``assumed`` に名前を残す: 軸の半径 6.5 mm(公開実装の既定値)、糸 1.45 m(本文の「145 cm」)、
μ_acc = 1/r(転がりの極限、rad/m)、μ_dec = 0.8/r、c_L = 1 cm・c_F = 5 cm(論文の図の説明)、張りつめの余裕 3 cm(公開実装)、
面の規則の余裕 5 cm(本文)、カップの底の板 半径 12 mm・中心から 12 mm、マーカーは内面の 55 % の半径に 8 か所(うち反射は
0, 1, 3 番 = 回転の向きが一意に決まる非対称の並び。論文は反射しない印刷のダミーで質量の対称を保った)。

**Raises** ``ValueError``: 知らない ``kind``、綴りの違う鍵(fail-closed)、質量・寸法が有限の正でない、底の板がカップの外、
c_L ≥ c_F。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_diabolo_model_and_vision](../../../../examples/poc_diabolo_model_and_vision.py) — `py -3.11 examples/poc_diabolo_model_and_vision.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`diabolo`)

[diabolo_spheroid](diabolo_spheroid.md) · [spheroid_closest](spheroid_closest.md) · [diabolo_dynamics_step](diabolo_dynamics_step.md) · [diabolo_simulate](diabolo_simulate.md) · [diabolo_state_sequence](diabolo_state_sequence.md) · [diabolo_throw_catch_truth](diabolo_throw_catch_truth.md) · [string_tension_static](string_tension_static.md) · [string_tension_from_sag](string_tension_from_sag.md)

---
*Provenance: diabolo.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
