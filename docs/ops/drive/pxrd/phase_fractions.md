---
op: phase_fractions
dim: drive
category: pxrd
in: signal × signal × table
out: table
examples: [poc_pxrd_phase_peel]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# phase_fractions — DRIVE `pxrd` op

- **データ種**: `signal × signal × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.phase_fractions(two_theta, intensity, dictionary, background_order=4, sigma=None, lattice_tolerance=0.0, phases=None)` (実装を直接呼ぶなら `import pxrd; pxrd.phase_fractions(two_theta, intensity, dictionary, background_order=4, sigma=None, lattice_tolerance=0.0, phases=None)`、台帳から引くなら `opsdrive.get("phase_fractions")`)

## 使い方

非負の最小二乗(NNLS)で混合物の相分率を出す(背景は Chebyshev の多項式で同時に当てる)。

``y ≈ Σ sₚ Rₚ(2θ) + Σ cₖ Tₖ(2θ)``、``sₚ >= 0``、``cₖ`` は符号自由(``scipy.optimize.lsq_linear`` の BVLS)。
体積分率 ``vₚ ∝ sₚ``、重量分率 ``Wₚ ∝ sₚ ρₚ``(module の docstring)。``sigma`` を渡せば 1/σ で重みを付ける。
``lattice_tolerance`` > 0 なら相ごとに格子の倍率を ``1 ± tolerance`` の中で黄金分割の座標降下で追い込む
(参照の格子定数と試料の格子定数がずれていると、山が半分ずれた参照は倍率が下がり分率が偏る —— 罠の門を参照)。
``phases`` で辞書の一部の名前だけを使う。

返り値(dict): ``names``・``scale``・``volume_fraction``・``weight_fraction``・``lattice_scale``・``fit``・
``background``・``residual``・``rwp``(重みつきの相対残差)・``two_theta``・``wavelength``。

Raises ValueError: 長さの不一致、辞書の格子と 2θ の不一致、背景の次数が負、未知の相の名前。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_pxrd_phase_peel](../../../../examples/poc_pxrd_phase_peel.py) — `py -3.11 examples/poc_pxrd_phase_peel.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pxrd`)

[cif_read](cif_read.md) · [cubic_prototype](cubic_prototype.md) · [powder_reflections](powder_reflections.md) · [scherrer_size](scherrer_size.md) · [debye_ring_image](debye_ring_image.md) · [detector_two_theta](detector_two_theta.md) · [detector_calibrate](detector_calibrate.md) · [azimuthal_integrate](azimuthal_integrate.md)

---
*Provenance: pxrd.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
