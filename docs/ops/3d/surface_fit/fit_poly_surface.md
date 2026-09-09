---
op: fit_poly_surface
dim: 3d
category: surface_fit
in: image2d × image2d × image2d
out: poly_surface
examples: [contours_to_terrain]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# fit_poly_surface — 3D `surface_fit` op

- **データ種**: `image2d × image2d × image2d` → `poly_surface`
- **呼び出し**: `import fullseye as fs; fs.ledger.fit_poly_surface(x, y, z, degree=2)` (実装を直接呼ぶなら `import match3d; match3d.fit_poly_surface(x, y, z, degree=2)`、台帳から引くなら `ops3d.get("fit_poly_surface")`)

## 使い方

散布 (x,y,z) → z=f(x,y) 多項式最小二乗。返り値 model(coef/powers/degree/rms/pv)。

基底 ``{x^i·y^j : i + j <= degree}``(項数 ``(degree+1)(degree+2)/2``。degree=1 で 3 項の平面、
2 で 6 項の 2 次曲面)を ``lstsq`` で当てる。``x, y, z`` は同じ要素数なら形は問わない(内部で
ravel。格子なら ``np.mgrid`` の出力をそのまま)。
返り値 dict: ``coef`` (T,) 係数、``powers`` は各係数の ``(i, j)``(項 ``x**i * y**j``)、
``degree``、``rms`` は残差 RMS、``pv`` は残差の peak-to-valley(max − min)。単位は z。
- 点数が項数より少ないと最小ノルム解が黙って返る。x, y の桁が大きいと高次で条件が悪くなる
(座標を中心化・正規化してから)。NaN の検証は無い。
後段: ``eval_poly_surface(model, x, y)`` で任意点を評価。格子の高さ場なら ``surface_form_error``
/ ``background_flatten`` がこれを内部で呼ぶ。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blas_threads_and_memory](../../math/guides/blas_threads_and_memory.md) — 行列分解が遅い理由の知識 — BLAS スレッド・キャッシュ・メモリ配置

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [contours_to_terrain](../../../../examples_3d/contours_to_terrain.py) — `py -3.11 examples_3d/contours_to_terrain.py`

## 型が繋がる次の op(`poly_surface` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [eval_poly_surface](eval_poly_surface.md)

## 同カテゴリ(`surface_fit`)

[eval_poly_surface](eval_poly_surface.md) · [surface_form_error](surface_form_error.md) · [background_flatten](background_flatten.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
