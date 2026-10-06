---
op: powder_reflections
dim: drive
category: pxrd
in: table × scalar
out: table
examples: [poc_pxrd_phase_peel]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# powder_reflections — DRIVE `pxrd` op

- **データ種**: `table × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.powder_reflections(phase, wavelength, two_theta_max=90.0, lorentz='powder', lattice_scale=1.0, include_extinct=False, rel_cutoff=1e-10)` (実装を直接呼ぶなら `import pxrd; pxrd.powder_reflections(phase, wavelength, two_theta_max=90.0, lorentz='powder', lattice_scale=1.0, include_extinct=False, rel_cutoff=1e-10)`、台帳から引くなら `opsdrive.get("powder_reflections")`)

## 使い方

相の粉末反射の一覧: 面間隔 d、Bragg の 2θ、多重度、|F|²、強度(Lorentz 因子つき、偏光なし)。

全ての (h, k, l) を ``2θ <= two_theta_max`` まで列挙し、構造因子
``F = Σ occ f₀(s) exp(−B s²) exp(2πi h·x)`` を計算して、**同じ d・同じ |F|² の反射を 1 本にまとめる**(多重度 m)。
粉末では同じ d の反射は区別できないので、d が同じで |F|² の違う族(立方晶の 333 と 511 など)は別の行のまま同じ 2θ に並ぶ。
``lattice_scale`` は格子定数を全部その倍率にする(熱膨張・固溶の模擬。:func:`phase_fractions` の格子の追い込みが使う)。
``include_extinct=True`` で |F|² が最大の ``rel_cutoff`` 倍未満の(消滅した)反射も残す(``extinct=True`` の印つき)。
強度 = ``m |F|² L(2θ)``(``lorentz``: ``"powder"`` = ``1/(sin² θ cos θ)``、``"none"``)。偏光は
:func:`azimuthal_integrate` が割り戻す前提で入れない。

返り値(dict): ``hkl``(代表、(n, 3) int)・``d`` [Å]・``two_theta`` [deg]・``multiplicity``・``F2``・``intensity``・
``extinct``(bool)、2θ の昇順。``name``・``volume``・``density`` も写す。

Raises ValueError: 相の形でない、波長が非正、``two_theta_max`` が (0, 180) の外、Lorentz の綴り違い。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_pxrd_phase_peel](../../../../examples/poc_pxrd_phase_peel.py) — `py -3.11 examples/poc_pxrd_phase_peel.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pxrd`)

[cif_read](cif_read.md) · [cubic_prototype](cubic_prototype.md) · [scherrer_size](scherrer_size.md) · [debye_ring_image](debye_ring_image.md) · [detector_two_theta](detector_two_theta.md) · [detector_calibrate](detector_calibrate.md) · [azimuthal_integrate](azimuthal_integrate.md) · [diffraction_peaks](diffraction_peaks.md)

---
*Provenance: pxrd.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
