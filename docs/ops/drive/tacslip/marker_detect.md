---
op: marker_detect
dim: drive
category: tacslip
in: image2d × scalar × scalar
out: table
examples: [poc_tacsim_marker_shear]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# marker_detect — DRIVE `tacslip` op

- **データ種**: `image2d × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.marker_detect(m, dark: 'float', r_px: 'float', binary: 'bool' = False) -> 'dict'` (実装を直接呼ぶなら `import tacslip; tacslip.marker_detect(m, dark: 'float', r_px: 'float', binary: 'bool' = False) -> 'dict'`、台帳から引くなら `opsdrive.get("marker_detect")`)

## 使い方

マーカー像 m(:func:`marker_image`)→ マーカー中心。``weighted``(主、(N, 2) の (x, y) [px]): 高しきい値 0.5·dark の連結成分
(:func:`blob2d.blob_label`)を本体とし、低しきい値 0.08·dark の画素(縞)を距離変換で最近傍の本体へ割り当て、m を重みにした重心を
反復ガウス重み(σ = r_px)で精密化。``weighted_plain`` = 精密化前。``binary=True`` なら ``binary`` = :func:`blob2d.blob_features` の
row/col(二値重心、周長・凸包まで計算するので 1,000 個で 0.4 s)。縁に触る成分は捨てる。``n`` = 本体の数。
縞を本体から切るのは、滑り環で隣接間隔が 8 → 6 px に縮むと低しきい値の縞が繋がって 1 成分に併合するから(実測)。
**Raises** ValueError: m が 2 次元でない、dark が (0, 1] の外、r_px ≤ 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacsim_marker_shear](../../../../examples/poc_tacsim_marker_shear.py) — `py -3.11 examples/poc_tacsim_marker_shear.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tacslip`)

[mindlin_partial_slip](mindlin_partial_slip.md) · [mindlin_traction](mindlin_traction.md) · [hertz_surface_ur](hertz_surface_ur.md) · [hertzian_tangential_inner](hertzian_tangential_inner.md) · [cerruti_kernel](cerruti_kernel.md) · [cerruti_surface_displacement](cerruti_surface_displacement.md) · [membrane_shear_field](membrane_shear_field.md) · [membrane_markers](membrane_markers.md)

---
*Provenance: tacslip.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
