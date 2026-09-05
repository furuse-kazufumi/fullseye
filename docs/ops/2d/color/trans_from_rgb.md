---
op: trans_from_rgb
dim: 2d
category: color
in: color
out: color
halcon: trans_from_rgb
examples: [gallery2d_color_artistic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# trans_from_rgb — 2D `color` op

- **データ種**: `color` → `color`
- **呼び出し**: `fullseye.apply(img, "trans_from_rgb", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `trans_from_rgb`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

RGB 画像を別の色空間（HSV / Lab / YUV / XYZ）へ変換する。HALCON の
``trans_from_rgb``（RGB 色空間から任意の色空間への変換）に相当。

内部は OpenCV の ``cv2.cvtColor`` を 8bit 経由で呼ぶだけで、変換先の
色空間そのものの定義は OpenCV の実装に従う。

a は変換先を 4 通り（HSV, Lab, YUV, XYZ の順）から選ぶ
（``min(3, int(a * 4))``）。b は未使用。8bit 量子化を経由するため、
逆変換（``trans_to_rgb``）と組み合わせても厳密には可逆でない。

## 詳しい使い方ガイド

- [gallery2d_color_artistic ファミリ ガイド](../guides/gallery2d_color_artistic.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [colorimetry](../guides/colorimetry.md) — 測色と分光の知識 — 色は「分光 × 光源 × 観測者」でしか決まらない

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_color_artistic](../../../../examples/gallery2d_color_artistic.py) — `py -3.11 examples/gallery2d_color_artistic.py`

## 型が繋がる次の op(`color` を入力に取れる)

[identity](../misc/identity.md) · [trans_to_rgb](trans_to_rgb.md) · [linear_trans_color](linear_trans_color.md) · [principal_comp](principal_comp.md) · [rgb1_to_gray](rgb1_to_gray.md) · [rgb3_to_gray](rgb3_to_gray.md) · [access_channel](access_channel.md) · [edges_color](../edges/edges_color.md)

## 同カテゴリ(`color`)

[cfa_to_rgb](cfa_to_rgb.md) · [trans_to_rgb](trans_to_rgb.md) · [linear_trans_color](linear_trans_color.md) · [principal_comp](principal_comp.md) · [rgb1_to_gray](rgb1_to_gray.md) · [rgb3_to_gray](rgb3_to_gray.md) · [access_channel](access_channel.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
