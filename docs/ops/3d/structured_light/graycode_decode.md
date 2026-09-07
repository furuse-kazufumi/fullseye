---
op: graycode_decode
dim: 3d
category: structured_light
in: images
out: image2d
examples: [graycode_structured_light, structured_light_scan]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# graycode_decode — 3D `structured_light` op

- **データ種**: `images` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.graycode_decode(bit_images, thresh=0.5) -> 'np.ndarray'` (実装を直接呼ぶなら `import fringe; fringe.graycode_decode(bit_images, thresh=0.5) -> 'np.ndarray'`、台帳から引くなら `ops3d.get("graycode_decode")`)

## 使い方

Gray code ビット画像列 → 整数フリンジ次数マップ(絶対次数)。

bit_images: 長さ K のシーケンス(各 2D 画像、明=1 / 暗=0)。**MSB first**(bit_images[0] が
            最上位ビット)。thresh で二値化する。
thresh:     二値化しきい値(画素値 >= thresh を 1)。

処理: 各ビット面を二値化 → MSB first で Gray 値を組み立て → Gray→binary 変換
      (binary = gray ^ (gray>>1) ^ ... ^ (gray>>(K-1)))で絶対次数(整数)を返す。
返り値: dtype int64 の 2D 次数マップ(値域 0..2**K-1)。

検証(``ValueError``): ``None`` / ``(K, H, W)`` に変換できない / ``K < 1`` /
``K > 62``(int64 に収まらない) / NaN・Inf を含む。``thresh`` は検査しない
(画素値と同じスケールで与える。``[0, 1]`` 画像なら 0.5 が既定)。

二値化は固定閾値 ``>= thresh`` のみ — 反転パターン(ネガ画像)との比較や
局所閾値は行わない。影・低反射で暗く出た画素は 0 ビットとして復号され、
エラーにならず誤った次数になるので、``modulation`` などで作った信頼マスクを
呼び手が別に持つこと。

次数の意味: Gray 符号は隣接コードが 1 ビットしか違わないので、境界画素の
二値化誤りは次数を ±1 しかずらさない(binary 符号なら大きく飛ぶ)。返る整数を
投影機コラム番号や縞の絶対次数として、``absolute_phase`` の ``coarse``
(``2π * 次数`` を位相に換算)や ``triangulate_column`` の ``column`` に使う。

## 背景知識ガイド(この op の手前にある物理・規約)

- [depth_sensors](../guides/depth_sensors.md) — 深度センサの知識 — 測距原理・実機の値・欠測の出方

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [graycode_structured_light](../../../../examples_3d/graycode_structured_light.py) — `py -3.11 examples_3d/graycode_structured_light.py`
- [structured_light_scan](../../../../examples_3d/structured_light_scan.py) — `py -3.11 examples_3d/structured_light_scan.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [eval_poly_surface](../surface_fit/eval_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](../render/matcap_shade.md)

## 同カテゴリ(`structured_light`)

[wrapped_phase](wrapped_phase.md) · [unwrap_phase_2d](unwrap_phase_2d.md) · [decode_fringe](decode_fringe.md) · [synthesize_fringes](synthesize_fringes.md) · [absolute_phase](absolute_phase.md) · [triangulate_column](triangulate_column.md)

---
*Provenance: fringe.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
