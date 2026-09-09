---
op: eval_bspline_surface
dim: 3d
category: freeform
in: bspline_surface × image2d × image2d
out: image2d
examples: [bspline_freeform]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# eval_bspline_surface — 3D `freeform` op

- **データ種**: `bspline_surface × image2d × image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.eval_bspline_surface(tck, x, y, grid=False)` (実装を直接呼ぶなら `import bspline_surf; bspline_surf.eval_bspline_surface(tck, x, y, grid=False)`、台帳から引くなら `ops3d.get("eval_bspline_surface")`)

## 使い方

フィット済み曲面 tck を評価(bisplev)。散布点(既定)または格子の 2 モード。

Parameters
----------
tck : list
    fit_bspline_surface が返した ``[tx, ty, c, kx, ky]``。
x, y : array_like
    grid=False(既定): 同一 shape の散布/対応点。各 (x[i], y[i]) で評価し
    入力と同じ shape の z を返す(計測=各サンプル位置での曲面高さ)。
    grid=True: x, y を昇順の 1 次元軸として扱い、テンソル格子
    (len(x), len(y)) 上で評価(密な可視化・再サンプリング用)。
grid : bool
    評価モード。曲面残差など点対応の比較には False。

Returns
-------
z : numpy.ndarray
    grid=False なら x と同 shape、grid=True なら (len(x), len(y))。

Raises
------
ValueError
    tck が曲面モデル([tx,ty,c,kx,ky])でない(曲線 tck / 多項式 dict を含む)、
    または x, y の shape 不一致・空。

補足:
- grid=True では x, y を内部で昇順に並べ替えて ``bisplev`` を呼び、結果を **入力の順序** に戻して返す。したがって ``out[i, j]`` は常に ``(x[i], y[j])`` の値で、軸を降順で渡しても壊れない。
- grid=False は点ごとに ``bisplev`` を呼ぶ Python ループなので点数に比例して遅い。大量点の評価は可能なら grid=True に寄せる。
- 節点範囲(フィットに使った x, y の範囲)の外側は外挿になり、その値は保証しない。
- 返り値は float64。grid=False なら x と同じ shape(スカラーを渡せば 0 次元配列)。
- 典型: ``fit_bspline_surface`` → 本 op(再サンプリング・可視化)。残差評価は ``surface_residual`` がこれを内部で呼ぶ。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [bspline_freeform](../../../../examples_3d/bspline_freeform.py) — `py -3.11 examples_3d/bspline_freeform.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [eval_poly_surface](../surface_fit/eval_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](../render/matcap_shade.md)

## 同カテゴリ(`freeform`)

[fit_bspline_surface](fit_bspline_surface.md) · [surface_residual](surface_residual.md) · [fit_bspline_curve](fit_bspline_curve.md) · [eval_bspline_curve](eval_bspline_curve.md)

---
*Provenance: bspline_surf.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
