---
op: depth_from_focus
dim: 3d
category: structured_light
in: images
out: depth
gpu: なし
examples: [ftp_and_focus_depth]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# depth_from_focus — 3D `structured_light` op

- **データ種**: `images` → `depth`
- **呼び出し**: `import fullseye as fs; fs.ledger.depth_from_focus(images, focus_positions=None)` (実装を直接呼ぶなら `import ops3d; ops3d.depth_from_focus(images, focus_positions=None)`、台帳から引くなら `ops3d.get("depth_from_focus")`)
- **台帳経由の戻り値**: `fullseye.ledger.depth_from_focus(...)` は**宣言 out 型 `depth` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.depth_from_focus.raw(...)`、または `ops3d.depth_from_focus` を直接呼ぶ。
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

焦点を変えた画像から高さ・深さを画素ごとの最良合焦位置として推定する。

「焦点を変えた画像から高さ」「ピントを変えた複数画像から深さ」を求める
shape-from-focus の入口。詳細な信頼度が必要なら
``reconstruction.depth_from_focus`` を直接呼び ``sharpness`` も確認する。

## 背景知識ガイド(この op の手前にある物理・規約)

- [depth_sensors](../guides/depth_sensors.md) — 深度センサの知識 — 測距原理・実機の値・欠測の出方

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [ftp_and_focus_depth](../../../../examples_3d/ftp_and_focus_depth.py) — `py -3.11 examples_3d/ftp_and_focus_depth.py`

## 型が繋がる次の op(`depth` を入力に取れる)

[depth_to_points](../transform/depth_to_points.md) · [tsdf_from_depth](../transform/tsdf_from_depth.md) · [to_points](../transform/to_points.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [depth_to_organized_points](../range_image/depth_to_organized_points.md) · [normals_from_depth](../range_image/normals_from_depth.md) · [occlusion_edges](../range_image/occlusion_edges.md) · [bearing_angle_image](../range_image/bearing_angle_image.md)

## 同カテゴリ(`structured_light`)

[wrapped_phase](wrapped_phase.md) · [unwrap_phase_2d](unwrap_phase_2d.md) · [graycode_decode](graycode_decode.md) · [decode_fringe](decode_fringe.md) · [fringe_ftp_phase](fringe_ftp_phase.md) · [synthesize_fringes](synthesize_fringes.md) · [absolute_phase](absolute_phase.md) · [triangulate_column](triangulate_column.md)

---
*Provenance: ops3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
