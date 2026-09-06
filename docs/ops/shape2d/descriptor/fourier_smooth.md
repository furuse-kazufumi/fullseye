---
op: fourier_smooth
dim: shape2d
category: descriptor
in: pairs
out: pairs
examples: [contour_fourier]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# fourier_smooth — SHAPE2D `descriptor` op

- **データ種**: `pairs` → `pairs`
- **呼び出し**: `import fourierdesc; fourierdesc.fourier_smooth(points, keep)` (または `opsshape2d.get("fourier_smooth")`)

## 使い方

輪郭を複素 FFT で帯域制限して平滑化する。

輪郭を複素信号 z(t)=x(t)+i·y(t) と見て FFT し、低周波 ``keep`` 本(と対称成分)
だけ残して逆変換する。keep が小さいほど滑らか(高周波=細部/ノイズを落とす)。
keep が全周波数以上なら恒等。返り値は入力と同点数の (N,2)。

## 詳しい使い方ガイド

- [shape_description_2d ファミリ ガイド](../guides/shape_description_2d.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [contour_fourier](../../../../examples/contour_fourier.py) — `py -3.11 examples/contour_fourier.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[elliptic_fourier](elliptic_fourier.md) · [add_frame_corners](../morph/add_frame_corners.md) · [warp_tps_image](../morph/warp_tps_image.md) · [warp_piecewise_affine](../morph/warp_piecewise_affine.md) · [morph](../morph/morph.md) · [morph_sequence](../morph/morph_sequence.md)

## 同カテゴリ(`descriptor`)

[elliptic_fourier](elliptic_fourier.md) · [reconstruct](reconstruct.md) · [invariants](invariants.md) · [normalize](normalize.md) · [descriptor_distance](descriptor_distance.md) · [from_xld](from_xld.md)

---
*Provenance: fourierdesc.py — SHAPE2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
