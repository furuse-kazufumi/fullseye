---
op: rgb_to_lab
dim: imgmetrics
category: colorspace
in: rgbimage
out: lab
examples: [image_quality_metrics, poc_leaf_disease_area, poc_solder_fillet_aoi]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# rgb_to_lab — IMGMETRICS `colorspace` op

- **データ種**: `rgbimage` → `lab`
- **呼び出し**: `import fullseye as fs; fs.ledger.rgb_to_lab(rgb, white=(0.95047, 1.0, 1.08883))` (実装を直接呼ぶなら `import imgmetrics; imgmetrics.rgb_to_lab(rgb, white=(0.95047, 1.0, 1.08883))`、台帳から引くなら `opsimgmetrics.get("rgb_to_lab")`)

## 使い方

sRGB → CIE L\*a\*b\*(D65)。ΔE を測る前段。

``xyz_to_lab(rgb_to_xyz(rgb), white)`` の合成。検証と失敗条件はその 2 つに従う:

- ``rgb``: 最後の軸が 3。整数 dtype は dtype の最大値で ``[0, 1]`` に正規化、
  float は ``[0, 1]`` に収まっていることを要求(外れると ``MetricContractError``)。
  線形 RGB ではなく **ガンマ付きの sRGB** を渡すこと。
- ``white``: Lab の白色点。sRGB の行列は D65 固定なので、通常は既定のまま。
- 返り値: 入力と同じ形の float64。``L`` は ``[0, 100]``、白 ``(1, 1, 1)`` で
  ``(100, 0, 0)`` 付近。

画像 2 枚の色差なら ``delta_e_map`` が変換から色差まで一度にやる。
``lab_to_rgb`` で戻せるが、色域外は切り詰められる。

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
- [poc_leaf_disease_area](../../../../examples/poc_leaf_disease_area.py) — `py -3.11 examples/poc_leaf_disease_area.py`
- [poc_solder_fillet_aoi](../../../../examples/poc_solder_fillet_aoi.py) — `py -3.11 examples/poc_solder_fillet_aoi.py`

## 型が繋がる次の op(`lab` を入力に取れる)

[lab_to_rgb](lab_to_rgb.md) · [delta_e_2000](../colordiff/delta_e_2000.md) · [delta_e_76](../colordiff/delta_e_76.md)

## 同カテゴリ(`colorspace`)

[lab_to_rgb](lab_to_rgb.md) · [rgb_to_xyz](rgb_to_xyz.md) · [xyz_to_lab](xyz_to_lab.md)

---
*Provenance: imgmetrics.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
