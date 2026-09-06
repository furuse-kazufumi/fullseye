---
op: wrapped_phase
dim: 3d
category: structured_light
in: images
out: image2d
examples: [structured_light, structured_light_scan]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# wrapped_phase — 3D `structured_light` op

- **データ種**: `images` → `image2d`
- **呼び出し**: `import fringe; fringe.wrapped_phase(images) -> 'np.ndarray'` (または `ops3d.get("wrapped_phase")`)

## 使い方

N-step 位相シフト縞画像から wrapped phase (-π, π] を求める。

標準 N-step 公式 φ = atan2(Σ_n I_n sin(2πn/N), Σ_n I_n cos(2πn/N))。N >= 3 の等間隔位相シフトを
仮定。返り値は各画素の巻き込み位相(-π,π] の 2D 配列。

images: 長さ N のシーケンス(各 2D [0,1] 画像)または (N, H, W) 配列。

計算: 位相シフト量を等間隔 ``δ_n = 2πn/N``(``n = 0..N-1``)とし、
``s = Σ_n I_n sin δ_n``、``c = Σ_n I_n cos δ_n`` を ``tensordot`` で取って
``np.arctan2(s, c)``。``I_n = a + b cos(φ - δ_n)`` のモデル(``synthesize_fringes``
と同じ符号規約)なら ``φ`` が符号反転なしで戻る。平均輝度 ``a`` は消えるので
バイアスの影響を受けない。

入力と検証(``ValueError``): ``None`` / 3-D ``(N, H, W)`` に変換できない /
``N < 3`` / NaN・Inf を含む。値域 ``[0, 1]`` は前提であって検査はしない(範囲外
でも計算は通る)。

返り値: ``(H, W)`` float64、値域 ``(-π, π]``。``s = c = 0`` の画素(縞が無い・
変調ゼロ)は ``arctan2(0, 0) = 0`` を返し、エラーにも NaN にもならない —
信頼できる画素を選ぶには ``modulation``(同モジュールの関数)で変調度を見る
(``decode_fringe`` の ``min_modulation`` がそれを行う)。

注意: 位相シフト量が等間隔でない・枚数と順序が合っていない画像列を渡すと、
エラーにならず「もっともらしく間違った」位相が出る。次段は
``unwrap_phase_2d``(空間展開)か ``absolute_phase``(粗い絶対位相で次数確定)。

## 背景知識ガイド(この op の手前にある物理・規約)

- [depth_sensors](../guides/depth_sensors.md) — 深度センサの知識 — 測距原理・実機の値・欠測の出方

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [structured_light](../../../../examples_3d/structured_light.py) — `py -3.11 examples_3d/structured_light.py`
- [structured_light_scan](../../../../examples_3d/structured_light_scan.py) — `py -3.11 examples_3d/structured_light_scan.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [eval_poly_surface](../surface_fit/eval_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](../render/matcap_shade.md)

## 同カテゴリ(`structured_light`)

[unwrap_phase_2d](unwrap_phase_2d.md) · [graycode_decode](graycode_decode.md) · [decode_fringe](decode_fringe.md) · [synthesize_fringes](synthesize_fringes.md) · [absolute_phase](absolute_phase.md) · [triangulate_column](triangulate_column.md)

---
*Provenance: fringe.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
