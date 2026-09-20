---
op: seg_label_changes
dim: emproof
category: inject
in: labels2d × labels2d
out: table
examples: [poc_em_second_opinion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# seg_label_changes — EMPROOF `inject` op

- **データ種**: `labels2d × labels2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.seg_label_changes(before, after, min_pixels: 'int' = 1, ignore_zero: 'bool' = True) -> 'dict'` (実装を直接呼ぶなら `import emproof; emproof.seg_label_changes(before, after, min_pixels: 'int' = 1, ignore_zero: 'bool' = True) -> 'dict'`、台帳から引くなら `opsemproof.get("seg_label_changes")`)

## 使い方

2 枚のラベル画像の差を**融合と分断の対**として返す(校正の前後、または仕込んだ誤りの答え合わせ)。

``before`` のラベル b と ``after`` のラベル a が同じ画素を ``min_pixels`` 以上共有する対を数え、
* 融合 = after の 1 ラベルが before の 2 ラベル以上を覆う → ``merge_after`` / ``merge_before``(対ごとに 1 行。
  吸った側の id 自身も before の 1 つとして並ぶ)
* 分断 = before の 1 ラベルが after の 2 ラベル以上に割れる → ``split_before`` / ``split_after``(同様に
  残った側の id も並ぶ)
``n_merged`` / ``n_split`` は誤りの数(after 側・before 側の id で数える)。id の一致は見ない
(ラベルを振り直した 2 枚でも使える)。

>>> ch = seg_label_changes(truth, seg_inject_merge(truth))
>>> int(ch["n_merged"])
1

## 詳しい使い方ガイド

- [emproof ファミリ ガイド](../guides/emproof.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_em_second_opinion](../../../../examples/poc_em_second_opinion.py) — `py -3.11 examples/poc_em_second_opinion.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`inject`)

[seg_inject_merge](seg_inject_merge.md) · [seg_inject_split](seg_inject_split.md)

---
*Provenance: emproof.py — EMPROOF operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
