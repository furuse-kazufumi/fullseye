---
op: create_caltab
dim: calib
category: target
in: 
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.0  # fullseye lib version this note was generated for
---

# create_caltab — CALIB `target` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.create_caltab(rows=7, cols=7, spacing=1.0)` (実装を直接呼ぶなら `import caltab; caltab.create_caltab(rows=7, cols=7, spacing=1.0)`、台帳から引くなら `opscalib.get("create_caltab")`)

## 使い方

校正板の記述(理想点、板中心が原点)を作る(create_caltab)。

## 詳しい使い方ガイド

- [camera_calibration ファミリ ガイド](../guides/camera_calibration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[sim_caltab](sim_caltab.md) · [disp_caltab](disp_caltab.md)

## 同カテゴリ(`target`)

[caltab_points](caltab_points.md) · [gen_caltab](gen_caltab.md) · [sim_caltab](sim_caltab.md) · [disp_caltab](disp_caltab.md) · [find_caltab](find_caltab.md)

---
*Provenance: caltab.py — CALIB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
