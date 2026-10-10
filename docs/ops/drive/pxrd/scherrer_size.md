---
op: scherrer_size
dim: drive
category: pxrd
in: scalar × scalar × scalar
out: scalar
examples: [poc_pxrd_phase_peel]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# scherrer_size — DRIVE `pxrd` op

- **データ種**: `scalar × scalar × scalar` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.scherrer_size(fwhm, two_theta, wavelength, K=0.9, instrumental_fwhm=0.0, combine='gauss')` (実装を直接呼ぶなら `import pxrd; pxrd.scherrer_size(fwhm, two_theta, wavelength, K=0.9, instrumental_fwhm=0.0, combine='gauss')`、台帳から引くなら `opsdrive.get("scherrer_size")`)

## 使い方

Scherrer の式で結晶子径 [Å] (``L = K λ / (β cos θ)``)。

``fwhm``・``instrumental_fwhm`` は 2θ の半値全幅 [deg]、``two_theta`` [deg]、``wavelength`` [Å]。試料による広がり β は
``combine="gauss"`` で ``sqrt(fwhm² − inst²)``、``"lorentz"`` で ``fwhm − inst``。配列を渡せば配列で返す。
Scherrer の式は **体積で重みを付けた柱の長さ** の目安で、ひずみの広がり(tan θ に比例)は区別しない —— ひずみが
疑わしいときは複数の山で Williamson–Hall のように tan θ への依存を見ること。

Raises ValueError: ``fwhm <= instrumental_fwhm``(装置より細い山 = 径が決まらない)、非正の値、綴り違い。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_pxrd_phase_peel](../../../../examples/poc_pxrd_phase_peel.py) — `py -3.11 examples/poc_pxrd_phase_peel.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`pxrd`)

[cif_read](cif_read.md) · [cubic_prototype](cubic_prototype.md) · [powder_reflections](powder_reflections.md) · [debye_ring_image](debye_ring_image.md) · [detector_two_theta](detector_two_theta.md) · [detector_calibrate](detector_calibrate.md) · [azimuthal_integrate](azimuthal_integrate.md) · [diffraction_peaks](diffraction_peaks.md)

---
*Provenance: pxrd.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
