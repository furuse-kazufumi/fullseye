---
op: graycode_decode
dim: 3d
category: structured_light
in: images
out: image2d
examples: [graycode_structured_light]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# graycode_decode — 3D `structured_light` op

- **データ種**: `images` → `image2d`
- **呼び出し**: `import fringe; fringe.graycode_decode(bit_images, thresh=0.5) -> 'np.ndarray'` (または `ops3d.get("graycode_decode")`)

## 使い方

Gray code ビット画像列 → 整数フリンジ次数マップ(絶対次数)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [graycode_structured_light](../../../../examples_3d/graycode_structured_light.py) — `py -3.11 examples_3d/graycode_structured_light.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [eval_poly_surface](../surface_fit/eval_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](../render/matcap_shade.md)

## 同カテゴリ(`structured_light`)

[wrapped_phase](wrapped_phase.md) · [unwrap_phase_2d](unwrap_phase_2d.md) · [decode_fringe](decode_fringe.md) · [synthesize_fringes](synthesize_fringes.md)

---
*Provenance: fringe.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
