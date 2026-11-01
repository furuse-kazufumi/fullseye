---
op: disp_caltab
dim: calib
category: target
in: table
out: image2d
gpu: なし
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# disp_caltab — CALIB `target` op

- **データ種**: `table` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.disp_caltab(caltab)` (実装を直接呼ぶなら `import caltab; caltab.disp_caltab(caltab)`、台帳から引くなら `opscalib.get("disp_caltab")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

校正板画像を返す(表示用)(disp_caltab)。

``gen_caltab`` / ``sim_caltab`` の返り(``image`` を持つ dict)か、2-D の画像そのもの。
画像を持たない dict や非有限の画像は ``ValueError``(以前は dict をそのまま返していた)。

## 詳しい使い方ガイド

- [camera_calibration ファミリ ガイド](../guides/camera_calibration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`image2d` を入力に取れる)

[find_caltab](find_caltab.md) · [find_marks_and_pose](../calibrate/find_marks_and_pose.md)

## 同カテゴリ(`target`)

[caltab_points](caltab_points.md) · [create_caltab](create_caltab.md) · [gen_caltab](gen_caltab.md) · [sim_caltab](sim_caltab.md) · [find_caltab](find_caltab.md)

---
*Provenance: caltab.py — CALIB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
