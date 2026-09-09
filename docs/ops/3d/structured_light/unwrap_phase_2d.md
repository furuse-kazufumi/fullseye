---
op: unwrap_phase_2d
dim: 3d
category: structured_light
in: image2d
out: image2d
examples: [structured_light]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# unwrap_phase_2d — 3D `structured_light` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.unwrap_phase_2d(wrapped, mask=None) -> 'np.ndarray'` (実装を直接呼ぶなら `import fringe; fringe.unwrap_phase_2d(wrapped, mask=None) -> 'np.ndarray'`、台帳から引くなら `ops3d.get("unwrap_phase_2d")`)

## 使い方

wrapped phase を skimage.restoration.unwrap_phase で連続位相に展開する。

wrapped: wrapped_phase の出力(2D)。NaN を含んでよい(無効画素として扱う)。
mask:    省略可。True = 有効画素(numpy masked array の慣習とは逆にした直感的な向き)。
         NaN 画素と mask=False 画素は無効としてアンラップから除外し、出力では NaN を返す。

返り値: 連続位相(2D float)。無効画素は NaN。大域オフセット(+2πm)の不定性は残る。

手順: 無効画素(``wrapped`` の非有限 ∪ ``mask == False``)が無ければ
``skimage.restoration.unwrap_phase(arr)`` をそのまま呼ぶ。あれば無効画素を 0 で
埋めた ``numpy.ma`` の masked array として渡し(skimage は masked 画素を展開から
除外する)、出力の無効画素を NaN に戻す。

検証: scikit-image が import できない環境では ``RuntimeError``(``ImportError``
ではない)。``wrapped`` が 2-D でない、``mask`` の形が違う、**全画素が無効**
(アンラップする画素が無い)は ``ValueError``。

前提(Itoh の条件): 隣接する有効画素の真の位相差が ``π`` 未満。急な段差・深い穴・
オクルージョン境界では 2π の飛びを誤り、その先の領域全体が ``2πm`` ずれる。
マスクで島に分かれた領域どうしの相対次数は決まらない(島ごとに独立な
オフセット)。絶対性が要るときは ``graycode_decode`` → ``absolute_phase`` の
画素独立な次数確定を使う。

使いどころ: ``wrapped_phase`` → 本 op → ``phase_to_height``(同モジュールの
関数、``height = k (phase - ref_phase)``)。参照面を同じ手順で展開して引けば
大域オフセットは相殺される。``decode_fringe`` はこの連鎖を 1 回で行う。

## 背景知識ガイド(この op の手前にある物理・規約)

- [depth_sensors](../guides/depth_sensors.md) — 深度センサの知識 — 測距原理・実機の値・欠測の出方

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [structured_light](../../../../examples_3d/structured_light.py) — `py -3.11 examples_3d/structured_light.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [eval_poly_surface](../surface_fit/eval_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](../render/matcap_shade.md)

## 同カテゴリ(`structured_light`)

[wrapped_phase](wrapped_phase.md) · [graycode_decode](graycode_decode.md) · [decode_fringe](decode_fringe.md) · [synthesize_fringes](synthesize_fringes.md) · [absolute_phase](absolute_phase.md) · [triangulate_column](triangulate_column.md)

---
*Provenance: fringe.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
