---
op: edges_color
dim: 2d
category: edges
in: color
out: image
halcon: edges_color
examples: [gallery2d_edges]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# edges_color — 2D `edges` op

- **データ種**: `color` → `image`
- **呼び出し**: `fullseye.apply(img, "edges_color", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `edges_color`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

カラーエッジの強度を検出する。HALCON の ``edges_color``（Canny/Deriche/Shen
フィルタでカラーエッジを抽出する）に相当するとされるが、**実装はフィルタ
選択式ではなく Di Zenzo のマルチチャンネル勾配法に固定**されている。

各チャンネルに Sobel 勾配 (gx, gy) をかけ、勾配テンソル
``[[gxx, gxy], [gxy, gyy]]``（gxx=Σgx², gyy=Σgy², gxy=Σgx·gy）の最大
固有値を画素ごとに求め、その平方根をエッジ強度として最大値で正規化する。
a, b は未使用（HALCON 側にあるフィルタ種別・しきい値の選択はできない）。

## 詳しい使い方ガイド

- [gallery2d_edges ファミリ ガイド](../guides/gallery2d_edges.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_edges](../../../../examples/gallery2d_edges.py) — `py -3.11 examples/gallery2d_edges.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`edges`)

[sobel_mag](sobel_mag.md) · [prewitt_mag](prewitt_mag.md) · [roberts_mag](roberts_mag.md) · [dog](dog.md) · [grad_dir](grad_dir.md) · [log](log.md) · [corner_response](corner_response.md) · [sk_scharr](sk_scharr.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
