---
op: gradient_lut_invert
dim: drive
category: tacscalib
in: rgb × table × image2d
out: normalmap
examples: [poc_tacscalib_sphere_lut]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# gradient_lut_invert — DRIVE `tacscalib` op

- **データ種**: `rgb × table × image2d` → `normalmap`
- **呼び出し**: `import fullseye as fs; fs.ledger.gradient_lut_invert(rgb, table: 'dict', mask=None, min_count: 'int' = 1, method: 'str' = 'coarse', coarse: 'int' = 3, topk: 'int' = 2, chunk: 'int' = 1024) -> 'np.ndarray'` (実装を直接呼ぶなら `import tacscalib; tacscalib.gradient_lut_invert(rgb, table: 'dict', mask=None, min_count: 'int' = 1, method: 'str' = 'coarse', coarse: 'int' = 3, topk: 'int' = 2, chunk: 'int' = 1024) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("gradient_lut_invert")`)

## 使い方

RGB (H, W, 3) → 法線 (H, W, 3): 中身のあるビン(count ≥ ``min_count``)のうち色が最も近いものの中心法線。位置依存版の
表(:func:`gradient_lut_build` に positions を与えたもの)は画素の位置で各ビンの色を予測してから比べる。

``method="coarse"``(既定): ``coarse`` × ``coarse`` ビンの区画ごとに代表(行の最も多いビン)を置いて色の近い上位 ``topk``
区画を選び、それぞれの周り 3 × 3 区画だけ全ビンを比べる(粗 → 細)。``"exact"``: 全ビンの総当たり(基準)。
色 → 法線は多峰(離れたビンがほぼ同じ色を持つ)なので、粗 → 細は総当たりと**同じビンを選ぶとは限らない**: 実機の 1 台目で
一致は約 9 割、外れた画素も角誤差の中央値はほぼ同じ(門で測る)。
``mask`` の外は (0, 0, 1)。``min_count`` は使うビンの行数の下限: ノイズの無い合成なら 1 でよいが、実機では 1 行だけのビン
(1 台目の較正 24 枚で 624 個)の色の平均がノイズそのもので、1 のままだと復元した深さが +18 % 偏る(行 10 以上で +6 %)。
逆に位置の項を当てたビンだけ(``min_count=min_rows_poly``)で引くと傾き 0〜15° が不感帯になる。
**Raises** ``ValueError``: 形 / mask の形 / method の綴り / coarse・topk・chunk が 1 未満 / 使えるビンが 0 /
位置依存版で画像の大きさが違う。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacscalib_sphere_lut](../../../../examples/poc_tacscalib_sphere_lut.py) — `py -3.11 examples/poc_tacscalib_sphere_lut.py`

## 型が繋がる次の op(`normalmap` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`tacscalib`)

[calib_pack_load](calib_pack_load.md) · [sphere_normals_known](sphere_normals_known.md) · [lights_fit_from_sphere](lights_fit_from_sphere.md) · [membrane_predict_rgb](membrane_predict_rgb.md) · [gradient_lut_build](gradient_lut_build.md) · [normal_error_map](normal_error_map.md) · [sphere_cap_height](sphere_cap_height.md) · [field_position_sweep](field_position_sweep.md)

---
*Provenance: tacscalib.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
