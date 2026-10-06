---
op: piv_quiver
dim: piv
category: visualise
in: flow2d
out: rgb
examples: [piv_field_analysis_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# piv_quiver — PIV `visualise` op

- **データ種**: `flow2d` → `rgb`
- **呼び出し**: `import fullseye as fs; fs.ledger.piv_quiver(flow, spacing=None, scale=None, upsample=8, background=None, color=(0.08, 0.08, 0.12), width=1.5)` (実装を直接呼ぶなら `import pivops; pivops.piv_quiver(flow, spacing=None, scale=None, upsample=8, background=None, color=(0.08, 0.08, 0.12), width=1.5)`、台帳から引くなら `opspiv.get("piv_quiver")`)

## 使い方

矢印図(MATLAB の ``quiver``)。返りは ``(h*upsample, w*upsample, 3)``。

``spacing`` 格子ごとに 1 本、起点を格子点に置き、先端を ``起点 + scale * v``
に引く。``scale`` を省くと **最も長い矢印が間隔の 0.9 倍** になる(MATLAB の
自動倍率と同じ考え方で、隣の矢印に重ならない)。**倍率は図ごとに変わる**
ので、並べて比べる図では ``scale`` を固定する。長さが 1 画素に満たない
矢印は描かない(向きの無い点は印と読まれる)。

Args:
    flow: ``(2, h, w)``(``dy, dx``)。
    spacing: 矢印の間隔 [格子]。``None`` で長い辺に約 20 本。
    scale: 矢印の長さ = ``scale * 速さ`` [格子]。
    upsample: 出力の倍率(矢じりを描ける大きさにする)。
    background: ``(h*upsample, w*upsample)`` か ``(…, 3)``。``None`` で白。
        色相図(``piv_flow_to_rgbimage`` を拡大したもの)や LIC を敷ける。
    color / width: 矢印の色(palette の役割名か RGB)と軸の太さ [px]。
        既定は黒に近い墨色(色相図を敷いても読める)。
Returns:
    ``(h*upsample, w*upsample, 3)`` float64、値域 [0, 1]。

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

[piv_flow_to_rgbimage](piv_flow_to_rgbimage.md) · [piv_line_integral_convolution](piv_line_integral_convolution.md) · [piv_streamlines](piv_streamlines.md) · [piv_streamline_image](piv_streamline_image.md)

---
*Provenance: pivops.py — PIV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
