---
op: reconstruct
dim: shape2d
category: descriptor
in: efdmodel
out: pairs
examples: [contour_fourier]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# reconstruct — SHAPE2D `descriptor` op

- **データ種**: `efdmodel` → `pairs`
- **呼び出し**: `import fourierdesc; fourierdesc.reconstruct(model, n_points=300, n_harmonics=None)` (または `opsshape2d.get("reconstruct")`)

## 使い方

EFD 係数から輪郭を再構成する((M,2))。

n_harmonics を係数数より小さくすると **高調波を打ち切って平滑化** される
(低次だけ残すほど丸くなる)。

式: ``t = linspace(0, 1, n_points, endpoint=False)`` について
``x(t) = a0 + Σ a_n cos(2πnt) + b_n sin(2πnt)``、
``y(t) = c0 + Σ c_n cos(2πnt) + d_n sin(2πnt)``(``n = 1..N``)。

- ``model``: ``elliptic_fourier`` の返り値(``coeffs`` ``(N, 4)``、``a0``、``c0``)。
  ``normalize`` を通した係数を渡せば正準ポーズ(第 1 高調波で整列)の輪郭が
  出る。dict の検証はしない(キー欠落は ``KeyError``)。
- ``n_points``: 出力点数 ``M``(``int`` に切る)。等**パラメータ**間隔で、弧長
  等間隔ではない。``endpoint=False`` なので**末尾点は先頭点と一致しない**
  (閉じた多角形にするなら先頭点を末尾に足す)。0 なら空の ``(0, 2)``。
- ``n_harmonics``: 使う高調波数。``None`` で全部、``N`` より大きい値は ``N`` に
  切り詰め、0 以下なら DC だけ(全点が中心 ``(a0, c0)``)。
- 返り値: ``(M, 2)`` float64。座標の並び(``(x, y)`` か ``(row, col)``)は
  ``elliptic_fourier`` に渡した並びをそのまま引き継ぐ。``t = 0`` は元輪郭の
  始点に対応する。

輪郭を係数化せずに滑らかにするだけなら ``fourier_smooth``。係数どうしの
比較は ``invariants`` / ``descriptor_distance``。

## 詳しい使い方ガイド

- [shape_description_2d ファミリ ガイド](../guides/shape_description_2d.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [contour_fourier](../../../../examples/contour_fourier.py) — `py -3.11 examples/contour_fourier.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[elliptic_fourier](elliptic_fourier.md) · [fourier_smooth](fourier_smooth.md) · [add_frame_corners](../morph/add_frame_corners.md) · [warp_tps_image](../morph/warp_tps_image.md) · [warp_piecewise_affine](../morph/warp_piecewise_affine.md) · [morph](../morph/morph.md) · [morph_sequence](../morph/morph_sequence.md)

## 同カテゴリ(`descriptor`)

[elliptic_fourier](elliptic_fourier.md) · [invariants](invariants.md) · [normalize](normalize.md) · [descriptor_distance](descriptor_distance.md) · [fourier_smooth](fourier_smooth.md) · [from_xld](from_xld.md)

---
*Provenance: fourierdesc.py — SHAPE2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
