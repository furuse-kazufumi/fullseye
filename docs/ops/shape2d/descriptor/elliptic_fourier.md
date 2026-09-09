---
op: elliptic_fourier
dim: shape2d
category: descriptor
in: pairs
out: efdmodel
examples: [contour_fourier, shape2d_morph_descriptor_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# elliptic_fourier — SHAPE2D `descriptor` op

- **データ種**: `pairs` → `efdmodel`
- **呼び出し**: `import fullseye as fs; fs.ledger.elliptic_fourier(points, n_harmonics=10)` (実装を直接呼ぶなら `import fourierdesc; fourierdesc.elliptic_fourier(points, n_harmonics=10)`、台帳から引くなら `opsshape2d.get("elliptic_fourier")`)

## 使い方

閉輪郭の楕円フーリエ係数を Kuhl–Giardina 閉形式で求める。

引数:
    points: (N,2) の閉輪郭頂点。閉じていなければ内部で先頭点を末尾に補う。
    n_harmonics: 高調波数 N(多いほど細部まで表現)。

返り値: dict
    "coeffs": (N,4) 配列。行 n が [a_n, b_n, c_n, d_n]。
    "a0", "c0": DC 成分(輪郭の中心オフセット)。
    "n_harmonics": N。

再構成 :func:`reconstruct` は
    x(t)=a0+Σ a_n cos(2πnt)+b_n sin(2πnt),  y(t)=c0+Σ c_n cos+d_n sin  (t∈[0,1))。

## 詳しい使い方ガイド

- [shape_description_2d ファミリ ガイド](../guides/shape_description_2d.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [contour_fourier](../../../../examples/contour_fourier.py) — `py -3.11 examples/contour_fourier.py`
- [shape2d_morph_descriptor_tour](../../../../examples/shape2d_morph_descriptor_tour.py) — `py -3.11 examples/shape2d_morph_descriptor_tour.py`

## 型が繋がる次の op(`efdmodel` を入力に取れる)

[reconstruct](reconstruct.md) · [invariants](invariants.md) · [normalize](normalize.md) · [descriptor_distance](descriptor_distance.md)

## 同カテゴリ(`descriptor`)

[reconstruct](reconstruct.md) · [invariants](invariants.md) · [normalize](normalize.md) · [descriptor_distance](descriptor_distance.md) · [fourier_smooth](fourier_smooth.md) · [from_xld](from_xld.md)

---
*Provenance: fourierdesc.py — SHAPE2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
