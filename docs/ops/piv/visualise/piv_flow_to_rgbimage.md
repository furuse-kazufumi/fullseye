---
op: piv_flow_to_rgbimage
dim: piv
category: visualise
in: flow2d
out: rgb
examples: [piv_field_analysis_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# piv_flow_to_rgbimage — PIV `visualise` op

- **データ種**: `flow2d` → `rgb`
- **呼び出し**: `import fullseye as fs; fs.ledger.piv_flow_to_rgbimage(flow, scale=None)` (実装を直接呼ぶなら `import pivops; pivops.piv_flow_to_rgbimage(flow, scale=None)`、台帳から引くなら `opspiv.get("piv_flow_to_rgbimage")`)

## 使い方

色相 = 向き、明度 = 速さの標準的なフロー可視化。返りは ``(h, w, 3)``。

``reprconv.flow_to_rgbimage`` の 2 次元版(あちらは ``(3, D, H, W)`` の
3-D シーンフロー専用で、平面フローは形で弾かれる)。

**色相環の凡例を図の側で必ず一緒に焼くこと** —— 色の意味が書いていない
フロー図は綺麗なだけで読めない。``scale`` を省くと最大の速さで正規化する
ので、**図ごとに色の意味が変わる**。複数の図を並べるなら明示的に固定する。

Args:
    flow: ``(2, h, w)``。
    scale: 明度 1.0 に対応する速さ [px]。``None`` で最大値。
Returns:
    ``(h, w, 3)`` float64、値域 [0, 1]。

## 詳しい使い方ガイド

- [piv_displacement ファミリ ガイド](../guides/piv_displacement.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [piv_field_analysis_tour](../../../../examples/piv_field_analysis_tour.py) — `py -3.11 examples/piv_field_analysis_tour.py`

## 型が繋がる次の op(`rgb` を入力に取れる)

—

## 同カテゴリ(`visualise`)

[piv_line_integral_convolution](piv_line_integral_convolution.md)

---
*Provenance: pivops.py — PIV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
