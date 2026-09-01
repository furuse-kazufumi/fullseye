---
op: color_transfer
dim: colortransport
category: matching
in: rgbimage × rgbimage
out: rgbimage
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# color_transfer — COLORTRANSPORT `matching` op

- **データ種**: `rgbimage × rgbimage` → `rgbimage`
- **呼び出し**: `import colortransport; colortransport.color_transfer(src, ref, method='reinhard', space='lab')` (または `opscolortransport.get("color_transfer")`)

## 使い方

``src`` の色味を ``ref`` に寄せる。

Parameters
----------
src, ref : array_like
    ``(..., 3)`` の sRGB(``[0, 1]`` の float、または整数 dtype)。
    大きさは違ってよい(統計だけを使う)。
method : {"reinhard", "gaussian", "histogram"}
    * ``"reinhard"`` —— 各チャネルの平均と標準偏差だけ合わせる
      (Reinhard, Ashikhmin, Gooch & Shirley, IEEE CG&A 21(5), 2001)。
      **各チャネルが単峰の正規分布**という仮定が効いている。
      前景と背景がはっきり分かれた 二峰の絵では、平均と分散は合うのに
      **どちらの峰にも当たらない色**になる(例外は出ない)。
    * ``"gaussian"`` —— 共分散ごと運ぶ Monge 写像。**相関が保たれる**。
    * ``"histogram"`` —— チャネルごとに厳密なヒストグラム整合。
      周辺分布は完全に一致するが、**チャネル間の相関は壊れる**。
space : {"lab", "rgb"}
    統計を取る空間。既定の ``lab`` は :mod:`imgmetrics` の実体を使う。

Returns
-------
ndarray
    ``src`` と同じ形の sRGB ``[0, 1]``(色域外は切り詰められる)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`rgbimage` を入力に取れる)

—

## 同カテゴリ(`matching`)

[histogram_match](histogram_match.md) · [gaussian_transport_map](gaussian_transport_map.md)

---
*Provenance: colortransport.py — COLORTRANSPORT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
