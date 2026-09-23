---
op: seg_inject_merge
dim: emproof
category: inject
in: labels2d
out: labels2d
examples: [poc_em_second_opinion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# seg_inject_merge — EMPROOF `inject` op

- **データ種**: `labels2d` → `labels2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.seg_inject_merge(labels, n: 'int' = 1, seed: 'int' = 0, min_area: 'int' = 3000, ignore_zero: 'bool' = True) -> 'np.ndarray'` (実装を直接呼ぶなら `import emproof; emproof.seg_inject_merge(labels, n: 'int' = 1, seed: 'int' = 0, min_area: 'int' = 3000, ignore_zero: 'bool' = True) -> 'np.ndarray'`、台帳から引くなら `opsemproof.get("seg_inject_merge")`)

## 使い方

評価用に**融合**を仕込む: 隣接する大きなラベル対を ``n`` 組選び、片方の id をもう片方に書き換える。

``min_area`` px 以上のラベルだけを候補にし(小さな断片の融合は弦が短くて検出できず、評価が
「仕込めない誤り」に引っ張られる)、乱数(``seed``)で対を選ぶ。同じラベルは 1 回しか使わない。
``n`` 組取れなければ ValueError(黙って少ない数で返すと AUC の分母が変わる)。仕込んだ対は
``seg_label_changes(labels, out)["merge_before"]`` で取り出せる。

>>> merged = seg_inject_merge(labels, n=1, seed=3)
>>> seg_label_changes(labels, merged)["merge_before"]     # 吸われた id

## 詳しい使い方ガイド

- [emproof ファミリ ガイド](../guides/emproof.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_em_second_opinion](../../../../examples/poc_em_second_opinion.py) — `py -3.11 examples/poc_em_second_opinion.py`

## 型が繋がる次の op(`labels2d` を入力に取れる)

[seg_membrane_chord_score](../suspect/seg_membrane_chord_score.md) · [seg_boundary_membrane_gap](../suspect/seg_boundary_membrane_gap.md) · [seg_inject_split](seg_inject_split.md) · [seg_label_changes](seg_label_changes.md)

## 同カテゴリ(`inject`)

[seg_inject_split](seg_inject_split.md) · [seg_label_changes](seg_label_changes.md)

---
*Provenance: emproof.py — EMPROOF operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
