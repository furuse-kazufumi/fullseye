---
op: piv_line_integral_convolution
dim: piv
category: visualise
in: flow2d
out: image2d
examples: [piv_field_analysis_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# piv_line_integral_convolution — PIV `visualise` op

- **データ種**: `flow2d` → `image2d`
- **呼び出し**: `import pivops; pivops.piv_line_integral_convolution(flow, length=12, upsample=4, seed=0)` (または `opspiv.get("piv_line_integral_convolution")`)

## 使い方

線積分畳み込み(LIC)—— 流れに沿って白色雑音をぼかした模様の画像。

ベクトルの矢印は密にすると潰れ、疎にすると構造を見落とす。LIC は**画素ごと**
に流線に沿って雑音を平均するので、密度の選択が要らない。向きの情報は落ちる
(前後を区別しない)ので、**回転の向きを見たいときは矢印か色相図と併用する**。

Args:
    flow: ``(2, h, w)``。
    length: 流線に沿って積分する片側の歩数。長いほど滑らかになるが、
        渦の芯のような曲率の大きい場所では**構造が伸びて嘘になる**。
    upsample: 出力の解像度倍率(格子は粗いので拡大してから積分する)。
    seed: 白色雑音の種。
Returns:
    ``(h * upsample, w * upsample)`` float64、値域 [0, 1]。

## 詳しい使い方ガイド

- [piv_displacement ファミリ ガイド](../guides/piv_displacement.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [piv_field_analysis_tour](../../../../examples/piv_field_analysis_tour.py) — `py -3.11 examples/piv_field_analysis_tour.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[piv_cross_correlate](../estimate/piv_cross_correlate.md) · [piv_multipass](../estimate/piv_multipass.md) · [piv_deform_pass](../estimate/piv_deform_pass.md) · [strain_from_displacement](../solid/strain_from_displacement.md) · [correlation_quality](../solid/correlation_quality.md) · [speckle_quality](../solid/speckle_quality.md)

## 同カテゴリ(`visualise`)

[piv_flow_to_rgbimage](piv_flow_to_rgbimage.md)

---
*Provenance: pivops.py — PIV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
