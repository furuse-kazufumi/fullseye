---
op: opening_seg
dim: mv
category: morphology
in: mask × mask
out: labels2d
halcon: opening_seg
gpu: なし
examples: [machine_vision_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# opening_seg — MV `morphology` op

- **データ種**: `mask × mask` → `labels2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.opening_seg(region, se)` (実装を直接呼ぶなら `import mvmorph; mvmorph.opening_seg(region, se)`、台帳から引くなら `opsmv.get("opening_seg")`)
- **HALCON 相当**: `opening_seg`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

くびれで繋がった物体を収縮で切り離し、元の領域の中で広げ直してラベルにする。

構造要素で収縮 → 連結成分 → 各成分を最寄りの画素へ広げる(``region`` の中だけ)。収縮で
全部消えると全 0 のラベルを返す(理由: 切り離す種が残らない)。
空の入力(``region`` が 0 要素)は ValueError。

Args:
    region: 2-D の領域。
    se: 構造要素(奇数辺の bool 配列)。

Returns:
    ``region`` と同じ形の整数ラベル画像(背景 0、物体 1..n)。

## 詳しい使い方ガイド

- [machine_vision_classics ファミリ ガイド](../guides/machine_vision_classics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [machine_vision_tour](../../../../examples/machine_vision_tour.py) — `py -3.11 examples/machine_vision_tour.py`

## 型が繋がる次の op(`labels2d` を入力に取れる)

[select_characters](../text/select_characters.md)

## 同カテゴリ(`morphology`)

[golay_elements](golay_elements.md) · [hit_or_miss_golay](hit_or_miss_golay.md) · [hit_or_miss_seq](hit_or_miss_seq.md) · [thickening_hit_miss](thickening_hit_miss.md) · [thickening_golay](thickening_golay.md) · [thickening_seq](thickening_seq.md) · [morph_hat](morph_hat.md) · [morph_skiz](morph_skiz.md)

---
*Provenance: mvmorph.py — MV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
