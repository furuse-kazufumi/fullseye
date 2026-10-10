---
op: gradient_lut_build
dim: drive
category: tacscalib
in: matrix × matrix
out: table
examples: [poc_tacscalib_sphere_lut]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# gradient_lut_build — DRIVE `tacscalib` op

- **データ種**: `matrix × matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.gradient_lut_build(rgb_rows, normal_rows, bins: 'int' = 125, positions=None, image_shape=None, flat_rgb=None, flat_positions=None, min_rows_poly: 'int' = 30, ridge: 'float' = 0.001, pool: 'bool' = True) -> 'dict'` (実装を直接呼ぶなら `import tacscalib; tacscalib.gradient_lut_build(rgb_rows, normal_rows, bins: 'int' = 125, positions=None, image_shape=None, flat_rgb=None, flat_positions=None, min_rows_poly: 'int' = 30, ridge: 'float' = 0.001, pool: 'bool' = True) -> 'dict'`、台帳から引くなら `opsdrive.get("gradient_lut_build")`)

## 使い方

example-based の勾配 LUT: 法線の(傾き θ, 向き φ)を bins × bins に切り、各ビンに落ちた画素の RGB の**平均**を入れる
(``np.add.at`` で重複した添字も全部足す)。``rgb_rows`` (P, 3)、``normal_rows`` (P, 3)。

``positions``((P, 2) = (行, 列))と ``image_shape`` を与えると位置依存版: ``min_rows_poly`` 行以上のビンに
RGB = 6 係数 · [x², y², xy, x, y, 1] を当てる(x, y は画像寸法で −1..1、定数項以外に小さなリッジ)。``pool=True`` なら
行の少ないビンは角度で最も近い多項式ビンの位置の項(5 係数)を借り、定数項だけを自分の行の平均に合わせる —— 位置の項を
当てたビンだけで引くと傾きの小さいビンが全部落ちて 0〜15° が不感帯になる(試作で踏んだ罠)。
``flat_rgb``((F, 3)、位置つきなら ``flat_positions`` (F, 2) も)は「平らな例」= 法線 (0, 0, 1) として足す行(接触から
遠い輪など、弱い真値)。

返り: ``bins``、``mean_rgb`` (bins, bins, 3)(空のビンは nan)、``count`` (bins, bins)、``centre_normals`` (bins, bins, 3)、
``n_rows``、``n_flat``、``coef`` ((bins, bins, 6, 3) か None)、``basis``(``"unit"``)、``image_shape``、``poly_bins``・
``pooled_bins``(位置の項を当てた / 借りたビンの数)。
**Raises** ``ValueError``: 形の不一致 / bins < 4 / min_rows_poly < 6 / 行が 0 / 非有限 / positions と image_shape の片方だけ /
flat_positions だけ。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacscalib_sphere_lut](../../../../examples/poc_tacscalib_sphere_lut.py) — `py -3.11 examples/poc_tacscalib_sphere_lut.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tacscalib`)

[calib_pack_load](calib_pack_load.md) · [sphere_normals_known](sphere_normals_known.md) · [lights_fit_from_sphere](lights_fit_from_sphere.md) · [membrane_predict_rgb](membrane_predict_rgb.md) · [gradient_lut_invert](gradient_lut_invert.md) · [normal_error_map](normal_error_map.md) · [sphere_cap_height](sphere_cap_height.md) · [field_position_sweep](field_position_sweep.md)

---
*Provenance: tacscalib.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
