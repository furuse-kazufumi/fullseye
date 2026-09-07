---
op: xyz_to_lab
dim: imgmetrics
category: colorspace
in: rgb
out: lab
examples: [image_quality_metrics]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# xyz_to_lab — IMGMETRICS `colorspace` op

- **データ種**: `rgb` → `lab`
- **呼び出し**: `import fullseye as fs; fs.ledger.xyz_to_lab(xyz, white=(0.95047, 1.0, 1.08883))` (実装を直接呼ぶなら `import imgmetrics; imgmetrics.xyz_to_lab(xyz, white=(0.95047, 1.0, 1.08883))`、台帳から引くなら `opsimgmetrics.get("xyz_to_lab")`)

## 使い方

CIE XYZ → CIE 1976 L\*a\*b\*。既定の白色点は D65 2°。

式: ``t = XYZ / white`` として ``f(t) = cbrt(t)``(``t > (6/29)^3``)、
それ以外は ``t / (3 (6/29)^2) + 4/29``。``L = 116 f(Y) - 16``、
``a = 500 (f(X) - f(Y))``、``b = 200 (f(Y) - f(Z))``。

- ``xyz``: 最後の軸が 3 の任意の形。``rgb_to_xyz`` の出力と同じ、Y = 1 が白の尺度。
- ``white``: 白色点 ``(Xn, Yn, Zn)`` の 3 つの正の数。既定 ``D65_WHITE`` =
  ``(0.95047, 1.0, 1.08883)``。別の光源(D50 など)で撮った XYZ ならここを変える。
- 返り値: 入力と同じ形の float64。``L`` は白で 100、黒で 0。``a``/``b`` は符号つき。
- 失敗(``MetricContractError``): 最後の軸が 3 でない / ``white`` が 3 要素でない、
  または 0 以下を含む。XYZ の値域は検査しない(負や 1 超もそのまま計算する)。

``delta_e_76`` / ``delta_e_2000`` はこの Lab を入力にする。

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

[rgb_to_lab](rgb_to_lab.md) · [lab_to_rgb](lab_to_rgb.md) · [rgb_to_xyz](rgb_to_xyz.md)

---
*Provenance: imgmetrics.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
