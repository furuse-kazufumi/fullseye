---
op: azimuthal_integrate
dim: drive
category: pxrd
in: image2d × table
out: table
examples: [poc_pxrd_phase_peel]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# azimuthal_integrate — DRIVE `pxrd` op

- **データ種**: `image2d × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.azimuthal_integrate(image, geometry, n_bins=None, two_theta_range=None, mask=None, solid_angle=True, polarization=None, chi_range=None, supersample=2)` (実装を直接呼ぶなら `import pxrd; pxrd.azimuthal_integrate(image, geometry, n_bins=None, two_theta_range=None, mask=None, solid_angle=True, polarization=None, chi_range=None, supersample=2)`、台帳から引くなら `opsdrive.get("azimuthal_integrate")`)

## 使い方

2-D の検出器像を 2θ の 1-D プロファイルに落とす(方位積分、マスクと補正つき)。

各画素を ``supersample``² 個の副画素に分け(値は等分)、副画素の中心の 2θ でビンに振り分けて、ビンごとに **平均**
する(画素の分け方の粗さによる縞を減らす)。``solid_angle=True`` で相対立体角を、``polarization`` が数(0 = 無偏光、
1 = 水平偏光)なら偏光因子を、平均の前に割り戻す。``mask`` は True の画素を **除く**(同じ形の bool)。``chi_range``
= (χ₀, χ₁) [deg] で扇形だけを積分(χ は ``atan2`` の (−180, 180])。非有限の画素は mask に入っていなければ拒否する。

``n_bins`` の既定は画素 1 個の角の半分の幅になる数(``0.5·pixel/distance`` [rad])。
返り値(dict): ``two_theta``(ビンの中心 [deg])・``intensity``(平均)・``count``(副画素の重みの和、0 のビンは
``intensity`` が nan —— 埋めない)・``sigma``(Poisson を仮定した平均の標準誤差)。

Raises ValueError: 2-D でない、mask の形の不一致、非有限の画素、範囲が空、扇形が空、ビン数 < 8。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_pxrd_phase_peel](../../../../examples/poc_pxrd_phase_peel.py) — `py -3.11 examples/poc_pxrd_phase_peel.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pxrd`)

[cif_read](cif_read.md) · [cubic_prototype](cubic_prototype.md) · [powder_reflections](powder_reflections.md) · [scherrer_size](scherrer_size.md) · [debye_ring_image](debye_ring_image.md) · [detector_two_theta](detector_two_theta.md) · [detector_calibrate](detector_calibrate.md) · [diffraction_peaks](diffraction_peaks.md)

---
*Provenance: pxrd.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
