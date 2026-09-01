---
op: xyz_to_lab
dim: imgmetrics
category: colorspace
in: rgbimage
out: lab
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# xyz_to_lab — IMGMETRICS `colorspace` op

- **データ種**: `rgbimage` → `lab`
- **呼び出し**: `import imgmetrics; imgmetrics.xyz_to_lab(xyz, white=(0.95047, 1.0, 1.08883))` (または `opsimgmetrics.get("xyz_to_lab")`)

## 使い方

CIE XYZ → CIE 1976 L\*a\*b\*。既定の白色点は D65 2°。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`lab` を入力に取れる)

[lab_to_rgb](lab_to_rgb.md) · [delta_e_2000](../colordiff/delta_e_2000.md) · [delta_e_76](../colordiff/delta_e_76.md)

## 同カテゴリ(`colorspace`)

[rgb_to_lab](rgb_to_lab.md) · [lab_to_rgb](lab_to_rgb.md) · [rgb_to_xyz](rgb_to_xyz.md)

---
*Provenance: imgmetrics.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
