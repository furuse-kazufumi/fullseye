---
op: contour_fourier_complex
dim: shape2d
category: descriptor
in: pairs
out: matrix
examples: [poc_one_stroke_epicycles]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# contour_fourier_complex — SHAPE2D `descriptor` op

- **データ種**: `pairs` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.contour_fourier_complex(points, n_harmonics=None, parametrisation='index')` (実装を直接呼ぶなら `import fourierdesc; fourierdesc.contour_fourier_complex(points, n_harmonics=None, parametrisation='index')`、台帳から引くなら `opsshape2d.get("contour_fourier_complex")`)

## 使い方

閉輪郭を複素フーリエ級数の係数にする —— ``z(t) = Σ c_k exp(2πi k t)``。

引数:
    points: (N,2) の閉輪郭頂点。**(row, col) 順**(``fourierdesc`` と同じ)。
    n_harmonics: 残す次数 ``K``(``|k| <= K``)。``None`` なら表せる上限まで。
    parametrisation: ``"index"`` = 点の添字を等間隔の媒介変数にする /
        ``"arclength"`` = **弧長**で等間隔に打ち直してから変換する。

返り値: ``(2K+1, 3)`` の実配列(``matrix``)。行は ``[k, Re c_k, Im c_k]`` で
``k`` は ``0, 1, -1, 2, -2, …``(低い周波数から)。

★**媒介変数の取り方を既定で黙って決めない**のがこの op の肝。不均一に標本化された
輪郭を ``"index"`` で読むと、点が密なところに余分な時間が割り当てられ、
**絵は似ているのに係数が別物**になる(実測で ``k=3`` の係数が 47 倍ちがった)。
既定は ``"index"``(FFT の素の意味)だが、形の記述として使うなら
``"arclength"`` を選ぶこと。

★★``"arclength"`` を選ぶと **op の内部で輪郭を打ち直す**ので、返る係数は
渡した配列ではなく**打ち直した輪郭**を記述する。だから
:func:`contour_fourier_truncation_energy` の予言は「打ち直した輪郭に対して」
厳密で、呼び手が手元の配列で誤差を測ると合わない(実測: 512 点で 1.15 ずれた)。
手元の配列に対して厳密な予言が欲しいときは、**先に弧長で打ち直してから**
``"index"`` で呼ぶこと。

★**弧長の打ち直しは冪等ではない**: 標本を弦で結ぶので、すでに等弧長の輪郭に
もう 1 度かけると点が最大 3.73 px 動き(平均 0.84 px)、長さがさらに 3.25 %
縮む。二度かけないこと。

## 詳しい使い方ガイド

- [shape_description_2d ファミリ ガイド](../guides/shape_description_2d.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_one_stroke_epicycles](../../../../examples/poc_one_stroke_epicycles.py) — `py -3.11 examples/poc_one_stroke_epicycles.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[contour_epicycle_chain](contour_epicycle_chain.md) · [contour_fourier_truncation_energy](contour_fourier_truncation_energy.md)

## 同カテゴリ(`descriptor`)

[elliptic_fourier](elliptic_fourier.md) · [reconstruct](reconstruct.md) · [invariants](invariants.md) · [normalize](normalize.md) · [descriptor_distance](descriptor_distance.md) · [fourier_smooth](fourier_smooth.md) · [from_xld](from_xld.md) · [contour_epicycle_chain](contour_epicycle_chain.md)

---
*Provenance: fourierdesc.py — SHAPE2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
