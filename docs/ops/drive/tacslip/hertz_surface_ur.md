---
op: hertz_surface_ur
dim: drive
category: tacslip
in: matrix × scalar × scalar × scalar × scalar
out: matrix
examples: [poc_tacsim_marker_shear, poc_tactile_dipole_torque]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# hertz_surface_ur — DRIVE `tacslip` op

- **データ種**: `matrix × scalar × scalar × scalar × scalar` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.hertz_surface_ur(r, a: 'float', p0: 'float', G: 'float', nu: 'float') -> 'np.ndarray'` (実装を直接呼ぶなら `import tacslip; tacslip.hertz_surface_ur(r, a: 'float', p0: 'float', G: 'float', nu: 'float') -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("hertz_surface_ur")`)

## 使い方

法線荷重(Hertz 圧 p0√(1−r²/a²))が作る半空間表面の**半径方向**変位 ūr [m] (Johnson 1985 式 3.41b を E = 2G(1+ν) で書き直し)。
負 = 中心向き。内側 −(1−2ν)p0a²/(6Gr)[1 − (1−r²/a²)^{3/2}]、外側 −(1−2ν)p0a²/(6Gr)(= 点荷重 −(1−2ν)P/(4πGr))、r → 0 で 0。
最大は縁でなく r ≈ 0.93a(ūr(a) の 1.022 倍)。ūr(a)/δ = 2(1−2ν)/(3π(1−ν))(ν 0.48 で 1.6 %、ν 0.3 で 12 %)—— ほぼ非圧縮のゲルでは
法線荷重でマーカーはほとんど動かない。**Raises** ValueError: a, p0, G ≤ 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacsim_marker_shear](../../../../examples/poc_tacsim_marker_shear.py) — `py -3.11 examples/poc_tacsim_marker_shear.py`
- [poc_tactile_dipole_torque](../../../../examples/poc_tactile_dipole_torque.py) — `py -3.11 examples/poc_tactile_dipole_torque.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[world_camera](../world/world_camera.md) · [lidar_scan](../lidar/lidar_scan.md) · [relative_motion](../ttc/relative_motion.md) · [foe_from_motion](../ttc/foe_from_motion.md) · [flow_from_depth_motion](../ttc/flow_from_depth_motion.md) · [ttc_truth](../ttc/ttc_truth.md) · [world_materials](../terrain/world_materials.md) · [mesh_signed_volume](../terrain/mesh_signed_volume.md)

## 同カテゴリ(`tacslip`)

[mindlin_partial_slip](mindlin_partial_slip.md) · [mindlin_traction](mindlin_traction.md) · [hertzian_tangential_inner](hertzian_tangential_inner.md) · [cerruti_kernel](cerruti_kernel.md) · [cerruti_surface_displacement](cerruti_surface_displacement.md) · [membrane_shear_field](membrane_shear_field.md) · [membrane_markers](membrane_markers.md) · [displace_markers](displace_markers.md)

---
*Provenance: tacslip.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
