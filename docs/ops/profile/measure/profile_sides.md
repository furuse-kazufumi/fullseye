---
op: profile_sides
dim: profile
category: measure
in: pairs
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# profile_sides — PROFILE `measure` op

- **データ種**: `pairs` → `table`
- **呼び出し**: `import profileops; profileops.profile_sides(contour, n=101, normalise=True)` (または `opsprofile.get("profile_sides")`)

## 使い方

上面・下面を弦方向の関数として取り出す。返りは dict。

弦を ``n`` 等分し、各位置で輪郭と交わる上下の点を線形補間で拾う。

**開いた曲線はここで拒否される** —— 1 価の関数(MTF 曲線のような)を渡すと
下面が取れないので、「これは閉じた断面ではない」と明示して落とす。型ではなく
検証で守っている(``pairs`` は関数データにも閉輪郭にも使われる語彙なので、
型を分けると既存の輪郭生成 op から繋がらなくなる)。

Returns:
    dict: ``x``(``(n,)``)、``upper`` / ``lower``(``(n,)``)、``normalised``。

## 詳しい使い方ガイド

- [profile_metrology ファミリ ガイド](../guides/profile_metrology.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`measure`)

[profile_thickness](profile_thickness.md) · [profile_camber](profile_camber.md) · [profile_leading_edge_radius](profile_leading_edge_radius.md) · [profile_trailing_edge_gap](profile_trailing_edge_gap.md)

---
*Provenance: profileops.py — PROFILE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
