---
op: perpetual_loop_seam
dim: generative
category: loop
in: rgbvideo
out: table
examples: [poc_illusions_and_perpetual_drawing, poc_periodic_video_boundary]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# perpetual_loop_seam — GENERATIVE `loop` op

- **データ種**: `rgbvideo` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.perpetual_loop_seam(video: 'np.ndarray') -> 'dict'` (実装を直接呼ぶなら `import perpetual; perpetual.perpetual_loop_seam(video: 'np.ndarray') -> 'dict'`、台帳から引くなら `opsgenerative.get("perpetual_loop_seam")`)

## 使い方

循環動画の**継ぎ目**を数で出す(``table``)。

``seam`` = 最終コマ → 初コマの差、``typical`` = コマ間の差の中央値。
継ぎ目の無い動画では ``ratio = seam / typical`` が **1 に近い**(最後の
またぎが、ほかのまたぎと見分けが付かない)。**0 ではなく 1 が正解**なのが
ここの読みどころ —— 0 は「動きが止まっている」という意味になる。

## 詳しい使い方ガイド

- [generative_art ファミリ ガイド](../guides/generative_art.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_illusions_and_perpetual_drawing](../../../../examples/poc_illusions_and_perpetual_drawing.py) — `py -3.11 examples/poc_illusions_and_perpetual_drawing.py`
- [poc_periodic_video_boundary](../../../../examples/poc_periodic_video_boundary.py) — `py -3.11 examples/poc_periodic_video_boundary.py`

## 型が繋がる次の op(`table` を入力に取れる)

[perpetual_step](../stream/perpetual_step.md) · [perpetual_render](../stream/perpetual_render.md)

## 同カテゴリ(`loop`)

[perpetual_loop](perpetual_loop.md)

---
*Provenance: perpetual.py — GENERATIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
