---
op: surface_form_error
dim: 3d
category: surface_fit
in: image2d
out: measurement
examples: [geometry_metrology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# surface_form_error — 3D `surface_fit` op

- **データ種**: `image2d` → `measurement`
- **呼び出し**: `import match3d; match3d.surface_form_error(height, degree=1)` (または `ops3d.get("surface_form_error")`)

## 使い方

高さ場 grid → 理想曲面(多項式)残差=形状誤差(平面度 deg1/球面度 deg2)。→ (residual, rms, pv)。

``(H,W)`` の高さ場に ``x = 列 index``、``y = 行 index`` で ``fit_poly_surface(degree)`` を当て、
``residual = height − fit`` を返す。``degree=1`` は最小二乗平面(平面度=pv)、``degree=2`` は
2 次曲面(球面の近似。真の球ではない)。
返り値 ``(residual (H,W) float64, rms, pv)``、単位は高さの単位(横方向は画素単位なので傾き
係数は「高さ/画素」)。NaN があると lstsq が失敗する(欠損は先に埋める)。2-D 以外の入力は
形の unpack で失敗する。
用途: 平面度・うねりの評価。``background_flatten`` は同じ計算の「画像版」。点群の平面度は
``fit_plane_3d`` の resid。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blas_threads_and_memory](../../math/guides/blas_threads_and_memory.md) — 行列分解が遅い理由の知識 — BLAS スレッド・キャッシュ・メモリ配置

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [geometry_metrology](../../../../examples_3d/geometry_metrology.py) — `py -3.11 examples_3d/geometry_metrology.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[vol_gaussian_psf](../restoration/vol_gaussian_psf.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`surface_fit`)

[fit_poly_surface](fit_poly_surface.md) · [eval_poly_surface](eval_poly_surface.md) · [background_flatten](background_flatten.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
