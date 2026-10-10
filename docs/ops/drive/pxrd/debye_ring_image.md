---
op: debye_ring_image
dim: drive
category: pxrd
in: any × signal × table
out: table
examples: [poc_pxrd_phase_peel]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# debye_ring_image — DRIVE `pxrd` op

- **データ種**: `any × signal × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.debye_ring_image(phases, weight_fractions, geometry, shape=(512, 512), size=inf, K=0.9, instrumental_fwhm=0.02, counts=20000.0, background=0.03, polarization=0.0, lorentz='powder', supersample=2, lattice_scales=None, seed=0, step=0.002, eta=0.0)` (実装を直接呼ぶなら `import pxrd; pxrd.debye_ring_image(phases, weight_fractions, geometry, shape=(512, 512), size=inf, K=0.9, instrumental_fwhm=0.02, counts=20000.0, background=0.03, polarization=0.0, lorentz='powder', supersample=2, lattice_scales=None, seed=0, step=0.002, eta=0.0)`、台帳から引くなら `opsdrive.get("debye_ring_image")`)

## 使い方

デバイ環の 2-D 検出器像を合成する(相ごとの寄与つき)。

相 p の単位立体角あたりの強度 ``∝ vₚ (1/Vₚ²) Σ m|F|² L(2θ) × 形``(体積分率 ``vₚ ∝ Wₚ / ρₚ``)、山の幅は Scherrer
(``size`` [Å]、相ごとの list も可、inf = 広がりなし)と装置の FWHM(``instrumental_fwhm`` [deg])をガウスで足す。
画素の値 = 強度 × 偏光 ``P(2θ, χ)`` × 相対立体角 + 平らな背景(``background`` × 最大の強度、これも立体角つき)。
画素は ``supersample``² 点の平均(画素の幅の広がりが自然に入る)。``counts`` が数なら最大を ``counts`` に揃えて
Poisson の雑音(``seed``)、``None`` なら雑音なし。``lattice_scales`` は相ごとの格子の倍率(熱膨張・固溶の模擬)。
``eta`` は山の形の Lorentz の割合(pseudo-Voigt、0 = ガウス)—— 辞書と違う形で合成して、形の取り違えの効きを測るため。

返り値(dict): ``image``((H, W) float、数え数)・``per_phase``((P, H, W)、雑音なしの相ごとの寄与)・``background``
((H, W))・``names``・``weight_fractions``・``volume_fractions``・``two_theta``(画素の中心の 2θ)・``geometry``。

Raises ValueError: 相と分率の数の不一致、負の分率・総和 0、幾何の不備、像が小さすぎる。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_pxrd_phase_peel](../../../../examples/poc_pxrd_phase_peel.py) — `py -3.11 examples/poc_pxrd_phase_peel.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pxrd`)

[cif_read](cif_read.md) · [cubic_prototype](cubic_prototype.md) · [powder_reflections](powder_reflections.md) · [scherrer_size](scherrer_size.md) · [detector_two_theta](detector_two_theta.md) · [detector_calibrate](detector_calibrate.md) · [azimuthal_integrate](azimuthal_integrate.md) · [diffraction_peaks](diffraction_peaks.md)

---
*Provenance: pxrd.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
