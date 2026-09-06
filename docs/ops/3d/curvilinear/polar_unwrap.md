---
op: polar_unwrap
dim: 3d
category: curvilinear
in: image2d
out: image2d
gpu: true
examples: [curvilinear_proj]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# polar_unwrap — 3D `curvilinear` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import match3d; match3d.polar_unwrap(image, center=None, r_in=0.0, r_out=None, ntheta=360, nr=64, device='cpu')` (または `ops3d.get("polar_unwrap")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

画像の円環/円板を (θ×r) 矩形へアンラップ(工業: ラベル/リング/回転体の検査)。

円周方向に並ぶ特徴を「縦」に伸ばして通常の 2D 手法(直線探索/相関)を適用できる。grid_sample。
θ 軸は endpoint 無し(行 k の角度 = k·2π/ntheta)= 0° と 360° を重複サンプルしない
周期グリッド(θ 方向 FFT/循環相関の前提を満たす。2026-08-30 修正、旧版は先頭行=末尾行)。

Raises ValueError: 入力が 2-D でない・2x2 未満・NaN/Inf/float32 桁あふれ。

引数: ``center=(cy, cx)`` は **(行, 列)** の順(既定は画像中心 ``((H−1)/2, (W−1)/2)``)。
``r_in``〜``r_out``(画素、既定 ``min(H,W)/2 − 1``)を ``nr`` 等分、角度を ``ntheta`` 等分。
出力 ``(ntheta, nr)`` float32: 行 k の角度 ``θ = k·2π/ntheta``、列 j の半径
``r = r_in + j·(r_out − r_in)/(nr−1)``、サンプル点は ``(cy + r sinθ, cx + r cosθ)``(θ=0 が
+列方向、θ が増えると +行方向へ回る)。画像外は 0 で埋まる(bilinear)。
後段: 行方向(θ)の直線探索・``ncc_locate``、θ 方向の 1-D 相関で回転角。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [curvilinear_proj](../../../../examples_3d/curvilinear_proj.py) — `py -3.11 examples_3d/curvilinear_proj.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [eval_poly_surface](../surface_fit/eval_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [fit_zernike](fit_zernike.md) · [matcap_shade](../render/matcap_shade.md) · [antialias](../render/antialias.md)

## 同カテゴリ(`curvilinear`)

[cylinder_unwrap](cylinder_unwrap.md) · [fit_zernike](fit_zernike.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
