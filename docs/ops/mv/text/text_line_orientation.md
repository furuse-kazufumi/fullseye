---
op: text_line_orientation
dim: mv
category: text
in: image2d
out: scalar
halcon: text_line_orientation
gpu: なし
examples: [machine_vision_tour, poc_real_typewritten_ocr]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# text_line_orientation — MV `text` op

- **データ種**: `image2d` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.text_line_orientation(image, max_angle=30.0, step=0.25)` (実装を直接呼ぶなら `import mvtext; mvtext.text_line_orientation(image, max_angle=30.0, step=0.25)`、台帳から引くなら `opsmv.get("text_line_orientation")`)
- **HALCON 相当**: `text_line_orientation`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

文字行の傾きを射影の鋭さの最大で求める(度)。

行の射影は傾きが合うと階段が最も鋭くなる。その鋭さ(隣り合う射影の差の 2 乗和)を
``-max_angle .. max_angle`` で走査する。角度の向きはこの repo の矩形と同じで、右へ進むと行
が増える向きが正。インクが無い画像は 0.0 を返す(理由: 傾きを決める手がかりが無い)。
空の入力(``image`` が 0 要素)は ValueError。

Args:
    image: 灰色画像か bool の領域 (H, W)。灰色は Otsu のしきい値で二値にする。
    max_angle: 走査の範囲(度、> 0)。
    step: 走査の刻み(度、> 0)。

Returns:
    傾き(度)。

## 詳しい使い方ガイド

- [machine_vision_classics ファミリ ガイド](../guides/machine_vision_classics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [machine_vision_tour](../../../../examples/machine_vision_tour.py) — `py -3.11 examples/machine_vision_tour.py`
- [poc_real_typewritten_ocr](../../../../examples/poc_real_typewritten_ocr.py) — `py -3.11 examples/poc_real_typewritten_ocr.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

—

## 同カテゴリ(`text`)

[text_line_slant](text_line_slant.md) · [segment_characters](segment_characters.md) · [select_characters](select_characters.md)

---
*Provenance: mvtext.py — MV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
