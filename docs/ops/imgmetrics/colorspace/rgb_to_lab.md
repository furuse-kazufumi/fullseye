---
op: rgb_to_lab
dim: imgmetrics
category: colorspace
in: rgbimage
out: lab
examples: [image_quality_metrics]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.6  # fullseye lib version this note was generated for
---

# rgb_to_lab — IMGMETRICS `colorspace` op

- **データ種**: `rgbimage` → `lab`
- **呼び出し**: `import imgmetrics; imgmetrics.rgb_to_lab(rgb, white=(0.95047, 1.0, 1.08883))` (または `opsimgmetrics.get("rgb_to_lab")`)

## 使い方

sRGB → CIE L\*a\*b\*(D65)。ΔE を測る前段。

## 詳しい使い方ガイド

- [image_difference_metrics ファミリ ガイド](../guides/image_difference_metrics.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [colorimetry](../../2d/guides/colorimetry.md) — 測色と分光の知識 — 色は「分光 × 光源 × 観測者」でしか決まらない

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [image_quality_metrics](../../../../examples/image_quality_metrics.py) — `py -3.11 examples/image_quality_metrics.py`

## 型が繋がる次の op(`lab` を入力に取れる)

[lab_to_rgb](lab_to_rgb.md) · [delta_e_2000](../colordiff/delta_e_2000.md) · [delta_e_76](../colordiff/delta_e_76.md)

## 同カテゴリ(`colorspace`)

[lab_to_rgb](lab_to_rgb.md) · [rgb_to_xyz](rgb_to_xyz.md) · [xyz_to_lab](xyz_to_lab.md)

---
*Provenance: imgmetrics.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
