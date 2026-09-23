---
op: illusion_scintillating_grid
dim: generative
category: illusion
in: 
out: rgb
examples: [poc_illusions_and_perpetual_drawing]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# illusion_scintillating_grid — GENERATIVE `illusion` op

- **データ種**: `なし` → `rgb`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.illusion_scintillating_grid(size: 'int' = 44, n: 'int' = 8, bar: 'float' = 12.0, dot: 'float' = 6.0) -> 'np.ndarray'` (実装を直接呼ぶなら `import illusion; illusion.illusion_scintillating_grid(size: 'int' = 44, n: 'int' = 8, bar: 'float' = 12.0, dot: 'float' = 6.0) -> 'np.ndarray'`、台帳から引くなら `opsgenerative.get("illusion_scintillating_grid")`)

## 使い方

きらめき格子。ヘルマン格子の交点に白丸を置いたもの。

不変量: すべての白丸が同一(半径も値も)。

## 詳しい使い方ガイド

- [generative_art ファミリ ガイド](../guides/generative_art.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_illusions_and_perpetual_drawing](../../../../examples/poc_illusions_and_perpetual_drawing.py) — `py -3.11 examples/poc_illusions_and_perpetual_drawing.py`

## 型が繋がる次の op(`rgb` を入力に取れる)

—

## 同カテゴリ(`illusion`)

[illusion_cafe_wall](illusion_cafe_wall.md) · [illusion_muller_lyer](illusion_muller_lyer.md) · [illusion_ponzo](illusion_ponzo.md) · [illusion_zollner](illusion_zollner.md) · [illusion_poggendorff](illusion_poggendorff.md) · [illusion_fraser_spiral](illusion_fraser_spiral.md) · [illusion_ebbinghaus](illusion_ebbinghaus.md) · [illusion_kanizsa](illusion_kanizsa.md)

---
*Provenance: illusion.py — GENERATIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
