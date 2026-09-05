---
op: ncc_locate
dim: 2d
category: matching
in: image
out: match
halcon: find_ncc_model
examples: [gallery2d_contour_measure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# ncc_locate — 2D `matching` op

- **データ種**: `image` → `match`
- **呼び出し**: `fullseye.apply(img, "ncc_locate", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `find_ncc_model`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

正規化相互相関（NCC）によるテンプレートマッチングで最良位置を探す。HALCON の ``find_ncc_model``（Find the best matches of an NCC model in an image.）に相当。

``a``, ``b`` は未使用——テンプレートは引数ではなく ``set_match_template`` でスレッドローカルな ``_MATCH_CTX`` に事前登録しておく（マッチング系 op 共通の作法、``_MatchCtx`` の docstring 参照）。``_ncc_map``（NCC 相関マップ、Lewis 1995 の定義で ``[-1,1]``）を計算し、その最大値の位置を ``[相関値, y, x]`` で返す。テンプレート未設定、または入力が 2 次元画像でない場合は ``[0,0,0]``（no-match）を返す——fail-closed。回転・スケール変化には非対応（``_shape_locate`` は回転を扱う）。

## 詳しい使い方ガイド

- [gallery2d_contour_measure ファミリ ガイド](../guides/gallery2d_contour_measure.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_contour_measure](../../../../examples/gallery2d_contour_measure.py) — `py -3.11 examples/gallery2d_contour_measure.py`

## 型が繋がる次の op(`match` を入力に取れる)

[identity](../misc/identity.md)

## 同カテゴリ(`matching`)

[shape_locate](shape_locate.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
