---
op: warp_by_plane
dim: 3d
category: plane_sweep_stereo
in: image2d
out: image2d
examples: [motion_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# warp_by_plane — 3D `plane_sweep_stereo` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import plane_sweep; plane_sweep.warp_by_plane(img: 'np.ndarray', H: 'np.ndarray', order: 'int' = 1, cval: 'float' = nan) -> 'np.ndarray'` (または `ops3d.get("warp_by_plane")`)

## 使い方

homography H で img を逆ワープ。→ out[y,x] = img(H·(x,y,1))(bilinear)。

H は出力(ref)画素 → 入力(src)画素の写像。視野外は cval(既定 NaN)。

出力画素 (x=列, y=行) ごとに ``q = H @ (x, y, 1)``、``(sx, sy) = (q0/q2, q1/q2)`` を求め、
``scipy.ndimage.map_coordinates`` で入力画像の (行 sy, 列 sx) を補間して埋める(逆ワープなので
穴が空かない)。出力の形は入力と同じ (h,w)。同モジュールの ``plane_homography`` が返す H
(ref 画素 → src 画素)をそのまま渡すと「src を ref 視点へ持ってきた画像」になる。

- ``img``: (H,W) の 2-D グレースケール(float に変換)。空・非 2-D は ``ValueError``。
- ``H``: (3,3) 以外は ``ValueError``。
- ``order``: 補間次数(既定 1 = bilinear)。``prefilter=False`` で呼ぶため、2 以上を指定しても
  スプライン前処理を省いた近似(平滑化寄り)になる。
- ``cval``: 入力の範囲外に写った画素、および ``|q2| < 1e-12``(無限遠に飛ぶ画素)に入れる値。
  既定 NaN なので、後段で ``np.isfinite`` により「対応が取れなかった画素」を区別できる。

``plane_sweep_depth`` は候補深度ごとにこの関数で src をワープし、``|I_ref - warp(I_src)|`` を
photo-consistency コストにしている。

## 背景知識ガイド(この op の手前にある物理・規約)

- [depth_sensors](../guides/depth_sensors.md) — 深度センサの知識 — 測距原理・実機の値・欠測の出方

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [motion_scene](../../../../examples_3d/motion_scene.py) — `py -3.11 examples_3d/motion_scene.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [eval_poly_surface](../surface_fit/eval_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](../render/matcap_shade.md)

## 同カテゴリ(`plane_sweep_stereo`)

[plane_sweep_depth](plane_sweep_depth.md)

---
*Provenance: plane_sweep.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
