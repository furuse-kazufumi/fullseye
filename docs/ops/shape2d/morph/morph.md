---
op: morph
dim: shape2d
category: morph
in: image2d × image2d × pairs × pairs
out: image2d
examples: [image_morph]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# morph — SHAPE2D `morph` op

- **データ種**: `image2d × image2d × pairs × pairs` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.morph(imgA, imgB, ptsA, ptsB, alpha, method='affine', lam=0.0, with_corners=True)` (実装を直接呼ぶなら `import imagemorph; imagemorph.morph(imgA, imgB, ptsA, ptsB, alpha, method='affine', lam=0.0, with_corners=True)`、台帳から引くなら `opsshape2d.get("morph")`)

## 使い方

2 枚の画像 A, B を対応点でモーフし、比率 alpha の中間画像を作る。

手順(Beier–Neely 流のメッシュ・モーフ):
    1. 中間形状 mid = (1-alpha)·ptsA + alpha·ptsB を作る。
    2. A を ptsA→mid へ、B を ptsB→mid へワープ(両者の特徴を mid に揃える)。
    3. warp(A), warp(B) を alpha でクロスディゾルブ。
alpha=0 で A、alpha=1 で B に一致する。単純な blend(A,B,alpha) と違い、
目・鼻などの特徴が二重像にならず 1 つに重なる(=「本物の中間」)。

引数:
    imgA, imgB: (H,W[,C])、同 shape、[0,1]。
    ptsA, ptsB: (K,2) の (x,y)。A と B の対応点(同数・同順)。
    alpha: 合成比率 [0,1]。
    method: "affine"(区分アフィン, 速い)か "tps"(滑らか)。
    lam: TPS の平滑化係数(method="tps" のとき)。
    with_corners: True で四隅を固定点に足し、端の穴を防ぐ。

返り値: (H,W[,C]) の中間画像([0,1])。

## 詳しい使い方ガイド

- [shape_description_2d ファミリ ガイド](../guides/shape_description_2d.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [image_morph](../../../../examples/image_morph.py) — `py -3.11 examples/image_morph.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[warp_tps_image](warp_tps_image.md) · [warp_piecewise_affine](warp_piecewise_affine.md) · [blend](blend.md) · [morph_sequence](morph_sequence.md)

## 同カテゴリ(`morph`)

[add_frame_corners](add_frame_corners.md) · [warp_tps_image](warp_tps_image.md) · [warp_piecewise_affine](warp_piecewise_affine.md) · [blend](blend.md) · [morph_sequence](morph_sequence.md)

---
*Provenance: imagemorph.py — SHAPE2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
