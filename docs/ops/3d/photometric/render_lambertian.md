---
op: render_lambertian
dim: 3d
category: photometric
in: normalmap
out: image2d
examples: [photometric_stereo, render_shade]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# render_lambertian — 3D `photometric` op

- **データ種**: `normalmap` → `image2d`
- **呼び出し**: `import photometric; photometric.render_lambertian(normals, albedo, light, ambient=0.0)` (または `ops3d.get("render_lambertian")`)

## 使い方

法線 + アルベド + 光源方向 → Lambertian 画像(検査サンプル生成 / GT 検証 / 逆レンダの順方向)。→ HxW。

``I = albedo * (max(n·L, 0) + ambient)``。``light`` は (3,) の光源方向ベクトルで内部で
単位長に正規化する(長さは強度として効かない)。``n·L < 0`` の画素は 0 にクリップ
される(付着影)。``ambient`` は法線に依らず一様に足す定数で、アルベドは掛かる
(既定 0)。``normals`` は ``(H,W,3)`` の法線(単位長を仮定し正規化しない)、``albedo``
は ``(H,W)`` またはブロードキャスト可能な配列・スカラ。返り値は float32 の ``(H,W)``。
上限は ``albedo * (1 + ambient)`` で、[0,1] へのクリップはしない。入力検証は無い。
``photometric_stereo`` の順方向モデルそのもの(光源正規化の規約は ``normalize=True``
に対応)なので、復元した法線・アルベドから再合成して元画像と比べる往復検証に使える。
鏡面・相互反射・投影影(cast shadow)は含まない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [photometric_stereo](../../../../examples_3d/photometric_stereo.py) — `py -3.11 examples_3d/photometric_stereo.py`
- [render_shade](../../../../examples_3d/render_shade.py) — `py -3.11 examples_3d/render_shade.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [eval_poly_surface](../surface_fit/eval_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](../render/matcap_shade.md)

## 同カテゴリ(`photometric`)

[photometric_stereo](photometric_stereo.md) · [surface_normals](surface_normals.md) · [integrate_normals](integrate_normals.md)

---
*Provenance: photometric.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
