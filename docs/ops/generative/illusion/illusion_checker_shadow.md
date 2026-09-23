---
op: illusion_checker_shadow
dim: generative
category: illusion
in: 
out: rgb
examples: [poc_illusions_and_perpetual_drawing]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# illusion_checker_shadow — GENERATIVE `illusion` op

- **データ種**: `なし` → `rgb`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.illusion_checker_shadow(size: 'int' = 46, n: 'int' = 8, light: 'float' = 0.62, dark: 'float' = 0.31) -> 'np.ndarray'` (実装を直接呼ぶなら `import illusion; illusion.illusion_checker_shadow(size: 'int' = 46, n: 'int' = 8, light: 'float' = 0.62, dark: 'float' = 0.31) -> 'np.ndarray'`、台帳から引くなら `opsgenerative.get("illusion_checker_shadow")`)

## 使い方

チェッカーシャドウ。**印を付けた 2 マスは厳密に同じ画素値**。

影の係数を ``dark / light`` に取ると、影の中の明マスは影の外の暗マスと
**数として同じ**になる。★この図は ``aa=0``(反エイリアスなし)で描く ——
縁の混色が入ると「厳密に同値」という主張のほうが嘘になるため。

不変量: :data:`CHECKER_PATCHES` の 2 マス —— **影の外の暗マス** (2,3) と
**影の中の明マス** (5,5) —— の画素値が完全に一致(差が厳密に 0)。

★ここは一度間違えた。対にすべきは「暗マス × 影なし」と「明マス × 影あり」で、
同じ明暗のマスを 2 つ選んでも当然ながら一致しない(実測 0.31 の差が出た)。
絵は「それらしく」見えてしまうので、**数で確かめるまで気づけない** ——
この族が守ろうとしているのと同じ型の事故。

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
