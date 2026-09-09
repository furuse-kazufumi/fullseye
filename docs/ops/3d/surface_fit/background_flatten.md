---
op: background_flatten
dim: 3d
category: surface_fit
in: image2d
out: image2d
examples: [geometry_metrology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# background_flatten — 3D `surface_fit` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.background_flatten(image, degree=2)` (実装を直接呼ぶなら `import match3d; match3d.background_flatten(image, degree=2)`、台帳から引くなら `ops3d.get("background_flatten")`)

## 使い方

画像の低次曲面(照明ムラ)をフィット減算=シェーディング補正。→ flattened。

``(H,W)`` 画像に ``x = 列``、``y = 行`` で ``fit_poly_surface(degree)``(既定 2 次)を当て、
``image − fit`` を float64 で返す。出力は平均がほぼ 0 で **負の値を含む**(表示・閾値化には
``min`` を引くか定数を足す)。前景が広いと前景もフィットに引かれて削られる(前景を除いた点で
``fit_poly_surface`` → ``eval_poly_surface`` で減算する方が安全)。
グレースケール 2-D のみ(3-D は失敗)。NaN があると lstsq が失敗する。
用途: 閾値化の前処理、``polar_unwrap`` した円環画像の照明補正。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blas_threads_and_memory](../../math/guides/blas_threads_and_memory.md) — 行列分解が遅い理由の知識 — BLAS スレッド・キャッシュ・メモリ配置

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [geometry_metrology](../../../../examples_3d/geometry_metrology.py) — `py -3.11 examples_3d/geometry_metrology.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](fit_poly_surface.md) · [eval_poly_surface](eval_poly_surface.md) · [surface_form_error](surface_form_error.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](../render/matcap_shade.md) · [antialias](../render/antialias.md)

## 同カテゴリ(`surface_fit`)

[fit_poly_surface](fit_poly_surface.md) · [eval_poly_surface](eval_poly_surface.md) · [surface_form_error](surface_form_error.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
