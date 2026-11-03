---
op: get_grayval_contour_xld
dim: mv
category: gray
in: image2d × keypoints
out: signal
halcon: get_grayval_contour_xld
gpu: なし
examples: [machine_vision_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# get_grayval_contour_xld — MV `gray` op

- **データ種**: `image2d × keypoints` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.get_grayval_contour_xld(image, contour, order=1)` (実装を直接呼ぶなら `import mvimage; mvimage.get_grayval_contour_xld(image, contour, order=1)`、台帳から引くなら `opsmv.get("get_grayval_contour_xld")`)
- **HALCON 相当**: `get_grayval_contour_xld`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

輪郭の点列に沿って灰色値を補間で読み、1 本の信号にする。

``contour`` は (N, 2) の ``(row, col)`` か、輪郭が 1 本だけの XLD dict。``order`` は補間の
次数(0 最近傍 / 1 線形 / 3 三次)。画像の外の点があると ValueError(外挿の値を実測の
顔で返さない)。空の入力(``image`` が 0 要素)は ValueError。

Args:
    image: (H, W) の画像。
    contour: (N, 2) の点列、または ``{"shape", "cs"}`` の XLD dict。
    order: 補間の次数(0 / 1 / 3)。

Returns:
    長さ N の float 信号。

## 詳しい使い方ガイド

- [machine_vision_classics ファミリ ガイド](../guides/machine_vision_classics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [machine_vision_tour](../../../../examples/machine_vision_tour.py) — `py -3.11 examples/machine_vision_tour.py`

## 型が繋がる次の op(`signal` を入力に取れる)

—

## 同カテゴリ(`gray`)

[atan2_image](atan2_image.md) · [area_center_gray](area_center_gray.md) · [gray_histo](gray_histo.md) · [gray_projections](gray_projections.md)

---
*Provenance: mvimage.py — MV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
