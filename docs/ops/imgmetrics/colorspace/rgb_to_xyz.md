---
op: rgb_to_xyz
dim: imgmetrics
category: colorspace
in: rgbimage
out: rgb
examples: [image_quality_metrics]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# rgb_to_xyz — IMGMETRICS `colorspace` op

- **データ種**: `rgbimage` → `rgb`
- **呼び出し**: `import fullseye as fs; fs.ledger.rgb_to_xyz(rgb)` (実装を直接呼ぶなら `import imgmetrics; imgmetrics.rgb_to_xyz(rgb)`、台帳から引くなら `opsimgmetrics.get("rgb_to_xyz")`)

## 使い方

sRGB(``(..., 3)``)→ CIE XYZ。伝達関数を外してから行列を掛ける。

手順: ``srgb_to_linear`` で整数 dtype を ``[0, 1]`` に正規化しつつ伝達関数を
外し(IEC 61966-2-1)、線形 RGB に sRGB(D65)→XYZ の 3x3 行列を掛ける。
白 ``(1, 1, 1)`` は ``(0.9505, 1.0, 1.0890)`` に写る(Y を 1 に正規化した尺度)。

- 入力: 最後の軸が 3 なら形は任意(``(3,)`` の 1 色、``(N, 3)`` の色表、
  ``(H, W, 3)`` の画像)。整数 dtype(uint8/uint16 など)は dtype の最大値で割る。
  float は ``[0, 1]`` に収まっていなければ ``MetricContractError``(``ValueError``
  の部分型)。ガンマを外した線形値を渡すと二重にガンマを外すので注意。
- 返り値: 入力と同じ形の float64。
- 失敗: 最後の軸が 3 でない / float が ``[0, 1]`` の外 / 非有限。

次に ``xyz_to_lab`` を繋ぐのが常道(まとめて ``rgb_to_lab``)。

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

## 型が繋がる次の op(`rgb` を入力に取れる)

[xyz_to_lab](xyz_to_lab.md)

## 同カテゴリ(`colorspace`)

[rgb_to_lab](rgb_to_lab.md) · [lab_to_rgb](lab_to_rgb.md) · [xyz_to_lab](xyz_to_lab.md)

---
*Provenance: imgmetrics.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
