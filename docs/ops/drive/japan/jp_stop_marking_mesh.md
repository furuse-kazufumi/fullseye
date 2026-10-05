---
op: jp_stop_marking_mesh
dim: drive
category: japan
in: 
out: any
examples: [poc_driving_japan_town]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# jp_stop_marking_mesh — DRIVE `japan` op

- **データ種**: `なし` → `any`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.jp_stop_marking_mesh(*, char_h: 'float' = 2.4, char_w: 'float' = 0.8, gap: 'float' = 1.0, z: 'float' = 0.007)` (実装を直接呼ぶなら `import drivejapan; drivejapan.jp_stop_marking_mesh(*, char_h: 'float' = 2.4, char_w: 'float' = 0.8, gap: 'float' = 1.0, z: 'float' = 0.007)`、台帳から引くなら `opsdrive.get("jp_stop_marking_mesh")`)

## 使い方

路面文字「止まれ」(法定外表示、白)。局所座標: 原点 = 字の列の手前端(車に近い側)の車線中心、+x = 進む向き、+y = 左。

寸法は警察庁「交通規制基準」第 46 の図例(1): 1 字 240 × 80 cm、画 15 cm、横棒 30 cm、字間 1 m、縦表示で遠い方から
止・ま・れ(運転者は上から読む = 遠い字が上)。設置指針では停止線の 1〜3 m 手前から(:data:`JP_TOMARE_SETBACK_M`)。
字形は折線の略字形(曲線は近似)。返り値 (V, F, colors)。**Raises** ``ValueError``: 寸法が正でない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_japan_town](../../../../examples/poc_driving_japan_town.py) — `py -3.11 examples/poc_driving_japan_town.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`japan`)

[osm_synthetic](osm_synthetic.md) · [osm_parse](osm_parse.md) · [osm_road_graph](osm_road_graph.md) · [osm_road_mask](osm_road_mask.md) · [osm_road_loops](osm_road_loops.md) · [osm_route](osm_route.md) · [japan_world](japan_world.md) · [japan_stats](japan_stats.md)

---
*Provenance: drivejapan.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
