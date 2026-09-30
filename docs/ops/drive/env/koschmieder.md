---
op: koschmieder
dim: drive
category: env
in: any × any × scalar × any
out: any
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# koschmieder — DRIVE `env` op

- **データ種**: `any × any × scalar × any` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.koschmieder(L0, L_h, beta: 'float', d)` (実装を直接呼ぶなら `import driveenv; driveenv.koschmieder(L0, L_h, beta: 'float', d)`、台帳から引くなら `opsdrive.get("koschmieder")`)

## 使い方

Koschmieder の法則: 距離 d の物体の見かけの輝度 L = L₀ e^{−βd} + L_h (1 − e^{−βd})(配列可)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`env`)

[julian_day](julian_day.md) · [sun_at](sun_at.md) · [sun_events](sun_events.md) · [sun_vector](sun_vector.md) · [sun_illuminance](sun_illuminance.md) · [mor_from_beta](mor_from_beta.md) · [beta_from_mor](beta_from_mor.md) · [road_row_distance](road_row_distance.md)

---
*Provenance: driveenv.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
