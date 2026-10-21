---
op: increment_sign
dim: codematch
category: code
in: image2d
out: image2d
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.2  # fullseye lib version this note was generated for
---

# increment_sign — CODEMATCH `code` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.increment_sign(image, axis='h')` (実装を直接呼ぶなら `import codematch; codematch.increment_sign(image, axis='h')`、台帳から引くなら `opscodematch.get("increment_sign")`)

## 使い方

隣の画素との増分の符号 ``b = [I(次) >= I(今)]``(1 / 0 の uint8)。

``axis="h"``(既定)は行に沿って右隣と比べ、形は ``(H, W-1)``。``axis="v"`` は
下隣と比べ、形は ``(H-1, W)``。等しい画素の組は 1(論文の ``>=`` の規約)。
狭義単調増加の明るさの変換 ``g`` では ``increment_sign(g(I)) == increment_sign(I)``
が厳密に成り立つ(ISC の不変性の芯)。

## 詳しい使い方ガイド

- [robust_code_matching ファミリ ガイド](../guides/robust_code_matching.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`image2d` を入力に取れる)

[orientation_code](orientation_code.md) · [ocm_match](../match/ocm_match.md) · [isc_match](../match/isc_match.md) · [scc_match](../match/scc_match.md) · [radial_reach_filter](../change/radial_reach_filter.md)

## 同カテゴリ(`code`)

[orientation_code](orientation_code.md)

---
*Provenance: codematch.py — CODEMATCH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
