---
op: perpetual_loop
dim: generative
category: loop
in: 
out: rgbvideo
examples: [poc_illusions_and_perpetual_drawing, poc_periodic_video_boundary]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# perpetual_loop — GENERATIVE `loop` op

- **データ種**: `なし` → `rgbvideo`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.perpetual_loop(kind: 'str' = 'harmonograph', frames: 'int' = 48, size: 'int' = 360, seed: 'int' = 0) -> 'np.ndarray'` (実装を直接呼ぶなら `import perpetual; perpetual.perpetual_loop(kind: 'str' = 'harmonograph', frames: 'int' = 48, size: 'int' = 360, seed: 'int' = 0) -> 'np.ndarray'`、台帳から引くなら `opsgenerative.get("perpetual_loop")`)

## 使い方

**継ぎ目の無い循環動画**を作る → ``rgbvideo`` (T,H,W,3)。

★循環を「最後に頭へ戻す」で作らない。時間依存の量を**すべて θ の関数**に
して θ = 2πt/T を回すと、t = T は t = 0 と**同じ式**になる —— つまり継ぎ目は
最初から存在しない。これは編集で消す種類のものではなく、**構成から従う**。
:func:`perpetual_loop_seam` がその継ぎ目を数で出す(厳密に 0 になる)。

``frames`` コマ返す(t = 0 .. T-1)。t = T は t = 0 と一致するので含めない。

## 詳しい使い方ガイド

- [generative_art ファミリ ガイド](../guides/generative_art.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_illusions_and_perpetual_drawing](../../../../examples/poc_illusions_and_perpetual_drawing.py) — `py -3.11 examples/poc_illusions_and_perpetual_drawing.py`
- [poc_periodic_video_boundary](../../../../examples/poc_periodic_video_boundary.py) — `py -3.11 examples/poc_periodic_video_boundary.py`

## 型が繋がる次の op(`rgbvideo` を入力に取れる)

[perpetual_loop_seam](perpetual_loop_seam.md)

## 同カテゴリ(`loop`)

[perpetual_loop_seam](perpetual_loop_seam.md)

---
*Provenance: perpetual.py — GENERATIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
