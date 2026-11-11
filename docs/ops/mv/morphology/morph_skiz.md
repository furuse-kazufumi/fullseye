---
op: morph_skiz
dim: mv
category: morphology
in: mask
out: mask
halcon: morph_skiz
gpu: なし
examples: [machine_vision_tour, poc_real_grain_skiz]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# morph_skiz — MV `morphology` op

- **データ種**: `mask` → `mask`
- **呼び出し**: `import fullseye as fs; fs.ledger.morph_skiz(region)` (実装を直接呼ぶなら `import mvmorph; mvmorph.morph_skiz(region)`、台帳から引くなら `opsmv.get("morph_skiz")`)
- **HALCON 相当**: `morph_skiz`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

領域の連結成分の影響圏の境界(SKIZ)をユークリッド距離で求める。

背景の各画素について最も近い連結成分(8 連結)の集合を求め、(1) 同距離の成分が 2 つ以上ある
画素と、(2) 4 近傍の隣と集合が重ならない対のうち、自分の成分から遠い側(等しければ両方)の
画素を境界にする。規則は対の両側を同じに扱うので、境界は像の上下・左右の反転と転置に対して
対称(偶数幅の隙間では中央の 2 列、奇数幅では中央の 1 列)。その代わり線は 1 画素幅とは限らず、同距離の
画素から 1 画素のひげ(端点)が出やすい(実写の金属組織 168 枚で、片側の規則の 265 本に対し 1,116 本)。
1 画素幅の線や端点の数が要るなら、後段で細線化すること。連結成分が 1 つなら境界は無く、
全部 False を返す(理由: 影響圏が 1 つで境界が無い)。空の入力(``region`` が 0 要素)は ValueError。

Args:
    region: 2-D の領域。

Returns:
    ``region`` と同じ形の bool 配列。

## 詳しい使い方ガイド

- [machine_vision_classics ファミリ ガイド](../guides/machine_vision_classics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [machine_vision_tour](../../../../examples/machine_vision_tour.py) — `py -3.11 examples/machine_vision_tour.py`
- [poc_real_grain_skiz](../../../../examples/poc_real_grain_skiz.py) — `py -3.11 examples/poc_real_grain_skiz.py`

## 型が繋がる次の op(`mask` を入力に取れる)

[hit_or_miss_golay](hit_or_miss_golay.md) · [hit_or_miss_seq](hit_or_miss_seq.md) · [thickening_hit_miss](thickening_hit_miss.md) · [thickening_golay](thickening_golay.md) · [thickening_seq](thickening_seq.md) · [morph_hat](morph_hat.md) · [opening_seg](opening_seg.md) · [update_bg_esti](../tracking/update_bg_esti.md)

## 同カテゴリ(`morphology`)

[golay_elements](golay_elements.md) · [hit_or_miss_golay](hit_or_miss_golay.md) · [hit_or_miss_seq](hit_or_miss_seq.md) · [thickening_hit_miss](thickening_hit_miss.md) · [thickening_golay](thickening_golay.md) · [thickening_seq](thickening_seq.md) · [morph_hat](morph_hat.md) · [opening_seg](opening_seg.md)

---
*Provenance: mvmorph.py — MV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
