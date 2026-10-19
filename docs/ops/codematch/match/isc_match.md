---
op: isc_match
dim: codematch
category: match
in: image2d × image2d
out: table
examples: [poc_code_matching_breakdown]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.1  # fullseye lib version this note was generated for
---

# isc_match — CODEMATCH `match` op

- **データ種**: `image2d × image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.isc_match(image, template, direction='h', flat_thresh=0.01, min_valid=32) -> 'dict'` (実装を直接呼ぶなら `import codematch; codematch.isc_match(image, template, direction='h', flat_thresh=0.01, min_valid=32) -> 'dict'`、台帳から引くなら `opscodematch.get("isc_match")`)

## 使い方

増分符号相関(ISC)。増分符号が一致する割合が最大の位置を返す。

``r = (1/n) Σ [b_image == b_template]``(``n`` は増分の数)。乱れた位置での期待値は
0.5、同じものなら 1 に近い。``direction="h"`` は論文どおり行に沿った増分、
``"hv"`` は縦の増分も足す 2 次元の拡張。

**狭義単調増加の明るさの変換(ガンマ・ゲイン・オフセット・任意の単調な表)で
``score_map`` は 1 ビットも変わらない。**

テンプレートの増分のうち ``|Δ| > flat_thresh`` のものが ``min_valid`` に満たなければ
ValueError(平坦なテンプレートは符号が雑音で決まり、位置を決めない)。既定の 0.01 は
[0, 1] の明るさで 8 ビットの約 2.5 階調 —— これより小さい増分の符号は撮像の雑音と同じ桁で
決まる。この判定は
テンプレートだけを見るので、上の不変性を壊さない。拒否までの余裕は ``refusal_margin``。

## 詳しい使い方ガイド

- [robust_code_matching ファミリ ガイド](../guides/robust_code_matching.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_code_matching_breakdown](../../../../examples/poc_code_matching_breakdown.py) — `py -3.11 examples/poc_code_matching_breakdown.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`match`)

[ocm_match](ocm_match.md) · [scc_match](scc_match.md)

---
*Provenance: codematch.py — CODEMATCH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
