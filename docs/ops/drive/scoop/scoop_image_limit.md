---
op: scoop_image_limit
dim: drive
category: scoop
in: scalar × scalar × scalar × scalar
out: table
examples: [poc_powder_scoop_pour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# scoop_image_limit — DRIVE `scoop` op

- **データ種**: `scalar × scalar × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.scoop_image_limit(a: 'float', pitch: 'float', radius: 'float', bulk_density: 'float', *, h: 'float | None' = None, phi_deg: 'float' = 30.0, edge_px: 'float' = 0.5, grain_frac: 'float' = 0.25, min_a_over_d: 'float' = 5.0, target_mass: 'float | None' = None, rel_tol: 'float' = 0.05) -> 'dict'` (実装を直接呼ぶなら `import scoop; scoop.scoop_image_limit(a: 'float', pitch: 'float', radius: 'float', bulk_density: 'float', *, h: 'float | None' = None, phi_deg: 'float' = 30.0, edge_px: 'float' = 0.5, grain_frac: 'float' = 0.25, min_a_over_d: 'float' = 5.0, target_mass: 'float | None' = None, rel_tol: 'float' = 0.05) -> 'dict'`、台帳から引くなら `opsdrive.get("scoop_image_limit")`)

## 使い方

山盛りのスプーンを側面像で量るときの不確かさの目安と「画像で足りるか、秤か」(**規則**、目安)。

模型: 体積の誤差 ≈ 見える表面積 ``S`` × 境界の不確かさ ``e = edge_px·pitch + grain_frac·r``(縁の画素と、輪郭が粒の
外側の包絡になる分のうち較正で消えない残り)。``S`` は山の円錐の側面 ``π a √(a² + H²)``(``H = a tan φ``)、体積は山盛りの
閉形式(``h`` を与えなければ ``a/2``)。``grain_frac = 0.25`` は MuJoCo の剛体球(半径 2 mm、縁の半径 30 mm、充填率を
1 回で較正)で 3 つの量 × 2 seed の数の誤差が 4.3 % 以内だった上限から逆算した 0.15 に余裕を見た値(PoC)。
**粒が少ないと線形の外挿より速く崩れる**(半径 3.5 mm、縁の半径 / 粒径 4.3 で 9.5 %)ので、``a / d < min_a_over_d``
は誤差によらず ``scale`` を返す。
返り: ``sigma_V``、``sigma_mass = ρ_b σ_V``、``rel_err = σ_V / V``、``a_over_d``(縁の半径 / 粒径)、``a_min``(``rel_tol`` を
満たす最小の縁の半径 —— 誤差は ``e / a`` に比例)、``verdict``(``image`` / ``scale``)、``reason``。``target_mass`` を
与えると、同じ形の椀をその質量に合わせて縮めたときの相対誤差 ``rel_err_target`` で判定する。
**Raises** ``ValueError``: 引数の範囲。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_powder_scoop_pour](../../../../examples/poc_powder_scoop_pour.py) — `py -3.11 examples/poc_powder_scoop_pour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`scoop`)

[spoon_bowl_volume](spoon_bowl_volume.md) · [scoop_synth_side](scoop_synth_side.md) · [revolution_volume_side](revolution_volume_side.md) · [two_view_volume](two_view_volume.md) · [scoop_volume_read](scoop_volume_read.md) · [scoop_count](scoop_count.md) · [tilt_wedge_retained](tilt_wedge_retained.md) · [tilt_pour_rate](tilt_pour_rate.md)

---
*Provenance: scoop.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
