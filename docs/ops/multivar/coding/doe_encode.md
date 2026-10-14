---
op: doe_encode
dim: multivar
category: coding
in: matrix
out: design
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# doe_encode — MULTIVAR `coding` op

- **データ種**: `matrix` → `design`
- **呼び出し**: `import fullseye as fs; fs.ledger.doe_encode(natural=None, factors=None) -> 'dict'` (実装を直接呼ぶなら `import doe; doe.doe_encode(natural=None, factors=None) -> 'dict'`、台帳から引くなら `opsmultivar.get("doe_encode")`)

## 使い方

Natural-unit settings (n, k) -> ``design`` with coded values (−1..+1 = lo..hi).

Use it to bring runs that were *not* planned here (a historical log, a hand-made
plan) into the same coded frame the analysis ops read. ``factors`` gives the
ranges (and per-factor ``"log"`` scale: coded = position of log10(x) between
log10(lo) and log10(hi)). Values outside lo..hi are kept (coded beyond ±1) and named
in ``meta['outside_range']``.

## 詳しい使い方ガイド

- [design_of_experiments ファミリ ガイド](../guides/design_of_experiments.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`design` を入力に取れる)

[doe_decode](doe_decode.md)

## 同カテゴリ(`coding`)

[doe_decode](doe_decode.md)

---
*Provenance: doe.py — MULTIVAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
