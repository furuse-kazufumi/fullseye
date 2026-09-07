---
op: blob_select_largest
dim: blob
category: select
in: labels2d
out: labels2d
examples: [poc_gear_tooth_metrology, poc_solder_fillet_aoi, poc_wound_area_tracking]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# blob_select_largest — BLOB `select` op

- **データ種**: `labels2d` → `labels2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.blob_select_largest(labels: 'Any', count: 'int' = 1) -> 'np.ndarray'` (実装を直接呼ぶなら `import blob2d; blob2d.blob_select_largest(labels: 'Any', count: 'int' = 1) -> 'np.ndarray'`、台帳から引くなら `opsblob.get("blob_select_largest")`)

## 使い方

面積の大きい順に ``count`` 個だけ残す(**番号は面積の降順に振り直す**)。

同じ面積が並んだときは元の番号が小さいほうを先にする(実行ごとに順序が
変わらないよう ``argsort`` を安定ソートで固定してある)。``count`` が
物体数より多くても**あるだけ**返す(足りないことを例外にはしない ——
「上位 3 個」を頼んで 2 個しか無いのは異常ではない)。

## 詳しい使い方ガイド

- [blob_analysis ファミリ ガイド](../guides/blob_analysis.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_gear_tooth_metrology](../../../../examples/poc_gear_tooth_metrology.py) — `py -3.11 examples/poc_gear_tooth_metrology.py`
- [poc_solder_fillet_aoi](../../../../examples/poc_solder_fillet_aoi.py) — `py -3.11 examples/poc_solder_fillet_aoi.py`
- [poc_wound_area_tracking](../../../../examples/poc_wound_area_tracking.py) — `py -3.11 examples/poc_wound_area_tracking.py`

## 型が繋がる次の op(`labels2d` を入力に取れる)

[blob_features](../measure/blob_features.md) · [blob_select](blob_select.md) · [blob_split](../split/blob_split.md) · [blob_region](../extract/blob_region.md) · [blob_boundaries](../extract/blob_boundaries.md) · [blob_overlay](../extract/blob_overlay.md)

## 同カテゴリ(`select`)

[blob_select](blob_select.md)

---
*Provenance: blob2d.py — BLOB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
