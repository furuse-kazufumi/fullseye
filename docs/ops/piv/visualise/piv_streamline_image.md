---
op: piv_streamline_image
dim: piv
category: visualise
in: flow2d
out: rgb
examples: [piv_field_analysis_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# piv_streamline_image — PIV `visualise` op

- **データ種**: `flow2d` → `rgb`
- **呼び出し**: `import fullseye as fs; fs.ledger.piv_streamline_image(flow, upsample=8, background=None, color=(0.08, 0.08, 0.12), width=1.5, arrows=True, **stream_kw)` (実装を直接呼ぶなら `import pivops; pivops.piv_streamline_image(flow, upsample=8, background=None, color=(0.08, 0.08, 0.12), width=1.5, arrows=True, **stream_kw)`、台帳から引くなら `opspiv.get("piv_streamline_image")`)

## 使い方

流線図(MATLAB の ``streamslice``)。返りは ``(h*upsample, w*upsample, 3)``。

:func:`piv_streamlines` の等間隔配置で線を引き、各線の弧長の中ほどに
向きの矢じりを 1 つ置く(LIC と違って**前後が読める**)。線の間隔が揃うので、
**線の密度では速さを表さない** —— 速さを見たいときは ``background`` に
``piv_flow_magnitude`` か色相図を敷く。

Args:
    flow: ``(2, h, w)``。
    upsample / background / color / width: :func:`piv_quiver` と同じ。
    arrows: 矢じりを置くか。
    **stream_kw: :func:`piv_streamlines` へ素通し(``separation`` など)。
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

[piv_flow_to_rgbimage](piv_flow_to_rgbimage.md) · [piv_line_integral_convolution](piv_line_integral_convolution.md) · [piv_streamlines](piv_streamlines.md) · [piv_quiver](piv_quiver.md)

---
*Provenance: pivops.py — PIV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
