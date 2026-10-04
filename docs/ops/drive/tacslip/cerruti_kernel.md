---
op: cerruti_kernel
dim: drive
category: tacslip
in: scalar × scalar × scalar × scalar
out: table
examples: [poc_tacsim_marker_shear, poc_tactile_dipole_torque]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# cerruti_kernel — DRIVE `tacslip` op

- **データ種**: `scalar × scalar × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.cerruti_kernel(n: 'int', pitch: 'float', G: 'float', nu: 'float', sub: 'int' = 4, with_uz: 'bool' = False) -> 'dict'` (実装を直接呼ぶなら `import tacslip; tacslip.cerruti_kernel(n: 'int', pitch: 'float', G: 'float', nu: 'float', sub: 'int' = 4, with_uz: 'bool' = False) -> 'dict'`、台帳から引くなら `opsdrive.get("cerruti_kernel")`)

## 使い方

x 向き接線トラクション(1 画素 = pitch² に一様 1 Pa)が作る表面変位の離散核を 2n 格子(零詰めの線形畳み込み用)で作り、rfft2 済みで返す。

核は画素ごとに**画素平均**で持つ(sub×sub の副標本の平均)。中心画素は 1/r が可積分なので解析値 —— ∫□ 1/r dA = 4h ln(1+√2)、
∫□ x²/r³ dA = 2h ln(1+√2)(対称性から ∫x²/r³ = ∫y²/r³ = ½∫1/r)、∫□ xy/r³ = ∫□ x/r² = 0。返り: ``Kxx``・``Kyx``(接線 → 接線)、
``with_uz=True`` なら ``Kzx``(接線 → 法線、係数 (1−2ν) で ν 0.48 では 0.04 倍)、``n``・``pitch``・``G``・``nu``。
閉形式 (3.91) との一致は ūx 0.017 %・ūy 0.03 %(256 px、PoC の門)。**Raises** ValueError: n < 8、pitch, G ≤ 0、sub < 1。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacsim_marker_shear](../../../../examples/poc_tacsim_marker_shear.py) — `py -3.11 examples/poc_tacsim_marker_shear.py`
- [poc_tactile_dipole_torque](../../../../examples/poc_tactile_dipole_torque.py) — `py -3.11 examples/poc_tactile_dipole_torque.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tacslip`)

[mindlin_partial_slip](mindlin_partial_slip.md) · [mindlin_traction](mindlin_traction.md) · [hertz_surface_ur](hertz_surface_ur.md) · [hertzian_tangential_inner](hertzian_tangential_inner.md) · [cerruti_surface_displacement](cerruti_surface_displacement.md) · [membrane_shear_field](membrane_shear_field.md) · [membrane_markers](membrane_markers.md) · [displace_markers](displace_markers.md)

---
*Provenance: tacslip.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
