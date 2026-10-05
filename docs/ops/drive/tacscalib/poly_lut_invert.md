---
op: poly_lut_invert
dim: drive
category: tacscalib
in: rgb × table × image2d
out: normalmap
examples: [poc_tacscalib_sphere_lut]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# poly_lut_invert — DRIVE `tacscalib` op

- **データ種**: `rgb × table × image2d` → `normalmap`
- **呼び出し**: `import fullseye as fs; fs.ledger.poly_lut_invert(rgb, poly: 'dict', mask=None, method: 'str' = 'coarse') -> 'np.ndarray'` (実装を直接呼ぶなら `import tacscalib; tacscalib.poly_lut_invert(rgb, poly: 'dict', mask=None, method: 'str' = 'coarse') -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("poly_lut_invert")`)

## 使い方

アダプタ: 外部の**位置依存**多項式 LUT(``bins`` と ``grad_r`` / ``grad_g`` / ``grad_b`` = (bins, bins, 6)、ビンごとに
6 係数 [x², y², xy, x, y, 1]・x = 列・y = 行を**画素のまま**で背景差分の各チャネルを表す書式)を、
:func:`gradient_lut_invert` と同じ逆引き(同じビン割り・同じ粗 → 細)に通す。``rgb`` は外部の手順と同じ背景処理をした差分。
外部の表は全ビンが埋まっているので全ビンを使う。
**Raises** ``ValueError``: キー欠落 / 係数の形が (bins, bins, 6) でない / 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacscalib_sphere_lut](../../../../examples/poc_tacscalib_sphere_lut.py) — `py -3.11 examples/poc_tacscalib_sphere_lut.py`

## 型が繋がる次の op(`normalmap` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`tacscalib`)

[calib_pack_load](calib_pack_load.md) · [sphere_normals_known](sphere_normals_known.md) · [lights_fit_from_sphere](lights_fit_from_sphere.md) · [membrane_predict_rgb](membrane_predict_rgb.md) · [gradient_lut_build](gradient_lut_build.md) · [gradient_lut_invert](gradient_lut_invert.md) · [normal_error_map](normal_error_map.md) · [sphere_cap_height](sphere_cap_height.md)

---
*Provenance: tacscalib.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
