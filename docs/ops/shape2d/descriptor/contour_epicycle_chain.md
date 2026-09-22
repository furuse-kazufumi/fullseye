---
op: contour_epicycle_chain
dim: shape2d
category: descriptor
in: matrix
out: pairs
examples: [poc_one_stroke_epicycles]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# contour_epicycle_chain — SHAPE2D `descriptor` op

- **データ種**: `matrix` → `pairs`
- **呼び出し**: `import fullseye as fs; fs.ledger.contour_epicycle_chain(spectrum, phase, order='frequency')` (実装を直接呼ぶなら `import fourierdesc; fourierdesc.contour_epicycle_chain(spectrum, phase, order='frequency')`、台帳から引くなら `opsshape2d.get("contour_epicycle_chain")`)

## 使い方

位相 ``t`` における**回る振り子の連鎖**を返す(``pairs``)。

引数:
    spectrum: :func:`contour_fourier_complex` の ``(2K+1, 3)``。
    phase: ``t``(1 周 = 1.0)。
    order: ``"frequency"`` = 低い周波数から積む(教科書の絵)/
        ``"amplitude"`` = 振幅の大きい順(少ない項で似せる)。

返り値: ``(M+1, 2)`` の ``pairs``((row, col) 順)。行 0 が最初の腕の中心、
行 ``m`` が ``m`` 番目の腕の先(= 次の腕の中心)、**最後の行が筆先**で、
これが再構成された輪郭の点そのものになる。腕 ``m`` の長さは
``|c_k|``、角度は ``2π k t + arg c_k``。

## 詳しい使い方ガイド

- [shape_description_2d ファミリ ガイド](../guides/shape_description_2d.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_one_stroke_epicycles](../../../../examples/poc_one_stroke_epicycles.py) — `py -3.11 examples/poc_one_stroke_epicycles.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[elliptic_fourier](elliptic_fourier.md) · [fourier_smooth](fourier_smooth.md) · [contour_fourier_complex](contour_fourier_complex.md) · [add_frame_corners](../morph/add_frame_corners.md) · [warp_tps_image](../morph/warp_tps_image.md) · [warp_piecewise_affine](../morph/warp_piecewise_affine.md) · [morph](../morph/morph.md) · [morph_sequence](../morph/morph_sequence.md)

## 同カテゴリ(`descriptor`)

[elliptic_fourier](elliptic_fourier.md) · [reconstruct](reconstruct.md) · [invariants](invariants.md) · [normalize](normalize.md) · [descriptor_distance](descriptor_distance.md) · [fourier_smooth](fourier_smooth.md) · [from_xld](from_xld.md) · [contour_fourier_complex](contour_fourier_complex.md)

---
*Provenance: fourierdesc.py — SHAPE2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
