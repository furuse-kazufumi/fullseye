---
op: decode_fringe
dim: 3d
category: structured_light
in: images
out: depth
examples: [structured_light]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# decode_fringe — 3D `structured_light` op

- **データ種**: `images` → `depth`
- **呼び出し**: `import fullseye as fs; fs.ledger.decode_fringe(phase_shift_images, ref_phase=None, k=1.0, mask=None, min_modulation=None) -> 'np.ndarray'` (実装を直接呼ぶなら `import fringe; fringe.decode_fringe(phase_shift_images, ref_phase=None, k=1.0, mask=None, min_modulation=None) -> 'np.ndarray'`、台帳から引くなら `ops3d.get("decode_fringe")`)

## 使い方

位相シフト画像列を一括復号: wrapped → unwrap →(参照減算で)高さ。

phase_shift_images: N-step 位相シフト縞画像列((N,H,W) または長さ N のシーケンス)。
ref_phase:          参照平面(高さ 0)のアンラップ済み位相。None なら高さ = k·(unwrapped)。
k:                  位相→高さ較正定数。
mask:               省略可。True=有効画素。無効画素は NaN。
min_modulation:     省略可。指定すると modulation < この値の画素を低信頼として無効化。

返り値: 高さマップ(2D float)。ref_phase=None のときは k を掛けた連続位相を返す。
無効画素は NaN。

手順(実装どおり): ``wrapped_phase`` → 信頼マスクを組む(``min_modulation`` が
あれば ``modulation(stack) >= min_modulation``、``mask`` があればそれと AND)→
``unwrap_phase_2d(wrapped, mask=信頼マスク)`` → ``ref_phase`` が ``None`` なら
``k * unwrapped``、あれば ``phase_to_height``(``k * (unwrapped - ref_phase)``)。

引数:
- ``phase_shift_images``: ``(N, H, W)``、``N >= 3``、等間隔位相シフト。
- ``ref_phase``: スカラまたは ``(H, W)``。参照面を**同じ手順で展開した**位相を
  渡す(``unwrap_phase_2d`` の大域オフセットが両者で同じ扱いになるよう、参照も
  本 op で ``ref_phase=None`` として復号した結果を使うのが安全)。
- ``k``: 位相→高さの較正定数(単位/rad)。``synthesize_fringes`` の
  ``phase_gain`` の逆数に対応。
- ``mask``: ``(H, W)`` の bool、True = 有効。``min_modulation``: 変調度の下限
  (``[0, 1]`` 程度。影・飽和の画素を落とす)。

検証(``ValueError``): 画像列が 3-D でない・``N < 3``・非有限 / ``mask`` の形が
違う / ``ref_phase`` の形が違う / 有効画素がゼロ。scikit-image が無ければ
``RuntimeError``。

返り値: ``(H, W)`` float64。無効画素は NaN。単位は ``k`` の単位。

注意: 空間アンラップに依存するので、段差・オクルージョンで島に分かれた場面では
島ごとに ``2πm k`` の高さオフセットが残りうる。絶対高さが要る場面は
``graycode_decode`` → ``absolute_phase`` → ``triangulate_column`` の経路。

## 背景知識ガイド(この op の手前にある物理・規約)

- [depth_sensors](../guides/depth_sensors.md) — 深度センサの知識 — 測距原理・実機の値・欠測の出方

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [structured_light](../../../../examples_3d/structured_light.py) — `py -3.11 examples_3d/structured_light.py`

## 型が繋がる次の op(`depth` を入力に取れる)

[depth_to_points](../transform/depth_to_points.md) · [tsdf_from_depth](../transform/tsdf_from_depth.md) · [to_points](../transform/to_points.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [depth_to_organized_points](../range_image/depth_to_organized_points.md) · [normals_from_depth](../range_image/normals_from_depth.md) · [occlusion_edges](../range_image/occlusion_edges.md) · [bearing_angle_image](../range_image/bearing_angle_image.md)

## 同カテゴリ(`structured_light`)

[wrapped_phase](wrapped_phase.md) · [unwrap_phase_2d](unwrap_phase_2d.md) · [graycode_decode](graycode_decode.md) · [synthesize_fringes](synthesize_fringes.md) · [absolute_phase](absolute_phase.md) · [triangulate_column](triangulate_column.md)

---
*Provenance: fringe.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
