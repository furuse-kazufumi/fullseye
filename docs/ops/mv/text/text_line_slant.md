---
op: text_line_slant
dim: mv
category: text
in: image2d
out: scalar
halcon: text_line_slant
gpu: なし
examples: [machine_vision_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# text_line_slant — MV `text` op

- **データ種**: `image2d` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.text_line_slant(image, max_angle=45.0, step=0.5)` (実装を直接呼ぶなら `import mvtext; mvtext.text_line_slant(image, max_angle=45.0, step=0.5)`、台帳から引くなら `opsmv.get("text_line_slant")`)
- **HALCON 相当**: `text_line_slant`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

水平な文字行の字の斜体角を、列の射影の鋭さの最大で求める(度)。

せん断 ``col' = col + (row - row0) tan(a)`` で縦の字画が立つと列の射影が最も鋭くなる。
正の角度は下へ行くほど左へ寄った字(上が右へ倒れた字)。
インクが無い画像は 0.0 を返す(理由: 斜体角を決める手がかりが無い)。
空の入力(``image`` が 0 要素)は ValueError。

Args:
    image: 灰色画像か bool の領域 (H, W)。文字行は水平に直しておく。
    max_angle: 走査の範囲(度、0 より大きく 90 未満)。
    step: 走査の刻み(度、> 0)。

Returns:
    斜体角(度)。

## 詳しい使い方ガイド

- [machine_vision_classics ファミリ ガイド](../guides/machine_vision_classics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [machine_vision_tour](../../../../examples/machine_vision_tour.py) — `py -3.11 examples/machine_vision_tour.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

—

## 同カテゴリ(`text`)

[text_line_orientation](text_line_orientation.md) · [segment_characters](segment_characters.md) · [select_characters](select_characters.md)

---
*Provenance: mvtext.py — MV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
