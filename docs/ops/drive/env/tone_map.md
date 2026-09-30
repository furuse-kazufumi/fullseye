---
op: tone_map
dim: drive
category: env
in: any × scalar
out: any
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# tone_map — DRIVE `env` op

- **データ種**: `any × scalar` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.tone_map(radiance, exposure: 'float')` (実装を直接呼ぶなら `import driveenv; driveenv.tone_map(radiance, exposure: 'float')`、台帳から引くなら `opsdrive.get("tone_map")`)

## 使い方

HDR カメラの色を保つ階調の圧縮: m = 各画素の最大チャンネル × exposure、表示 = 輝度 × exposure × (1 + m/4)/(1 + m)
—— m ≪ 1 では線形、明るい所は 1 に漸近(色の比 = 色度は変えない。飽和で灯火が白くならない、仮定: 車載の HDR カメラ)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`env`)

[julian_day](julian_day.md) · [sun_at](sun_at.md) · [sun_events](sun_events.md) · [sun_vector](sun_vector.md) · [sun_illuminance](sun_illuminance.md) · [koschmieder](koschmieder.md) · [mor_from_beta](mor_from_beta.md) · [beta_from_mor](beta_from_mor.md)

---
*Provenance: driveenv.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
