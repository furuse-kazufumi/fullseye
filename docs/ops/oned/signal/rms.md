---
op: rms
dim: oned
category: signal
in: signal
out: measurement
examples: [lens_design_demo, lightfield_depth, piv_field_analysis_tour, piv_flow_from_particles, poc_battery_electrode_breathing, poc_bilateral_asymmetry, poc_bump_coplanarity, poc_cad_scan_deviation, poc_camera_calibration, poc_dimensional_inspection, poc_exoplanet_transit, poc_fabric_defect, poc_focus_stacking, poc_gear_tooth_metrology, poc_machine_condition_fusion, poc_panorama_drift, poc_print_registration, poc_real_stereo_depth, poc_river_surface_velocity, poc_screw_thread_metrology, poc_solar_limb_darkening, poc_strain_history, poc_surface_roughness, poc_symmetry_restoration, poc_thermal_radiometry, poc_water_level, profile_shape_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# rms — ONED `signal` op

- **データ種**: `signal` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.rms(x, frame=None, hop=None)` (実装を直接呼ぶなら `import dsp; dsp.rms(x, frame=None, hop=None)`、台帳から引くなら `ops1d.get("rms")`)

## 使い方

RMS level. Scalar for the whole signal, or a framewise array when *frame*
is given (a vibration/energy envelope over time).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [lens_design_demo](../../../../examples/lens_design_demo.py) — `py -3.11 examples/lens_design_demo.py`
- [lightfield_depth](../../../../examples/lightfield_depth.py) — `py -3.11 examples/lightfield_depth.py`
- [piv_field_analysis_tour](../../../../examples/piv_field_analysis_tour.py) — `py -3.11 examples/piv_field_analysis_tour.py`
- [piv_flow_from_particles](../../../../examples/piv_flow_from_particles.py) — `py -3.11 examples/piv_flow_from_particles.py`
- [poc_battery_electrode_breathing](../../../../examples/poc_battery_electrode_breathing.py) — `py -3.11 examples/poc_battery_electrode_breathing.py`
- [poc_bilateral_asymmetry](../../../../examples/poc_bilateral_asymmetry.py) — `py -3.11 examples/poc_bilateral_asymmetry.py`
- [poc_bump_coplanarity](../../../../examples/poc_bump_coplanarity.py) — `py -3.11 examples/poc_bump_coplanarity.py`
- [poc_cad_scan_deviation](../../../../examples/poc_cad_scan_deviation.py) — `py -3.11 examples/poc_cad_scan_deviation.py`
- [poc_camera_calibration](../../../../examples/poc_camera_calibration.py) — `py -3.11 examples/poc_camera_calibration.py`
- [poc_dimensional_inspection](../../../../examples/poc_dimensional_inspection.py) — `py -3.11 examples/poc_dimensional_inspection.py`
- [poc_exoplanet_transit](../../../../examples/poc_exoplanet_transit.py) — `py -3.11 examples/poc_exoplanet_transit.py`
- [poc_fabric_defect](../../../../examples/poc_fabric_defect.py) — `py -3.11 examples/poc_fabric_defect.py`
- [poc_focus_stacking](../../../../examples/poc_focus_stacking.py) — `py -3.11 examples/poc_focus_stacking.py`
- [poc_gear_tooth_metrology](../../../../examples/poc_gear_tooth_metrology.py) — `py -3.11 examples/poc_gear_tooth_metrology.py`
- [poc_machine_condition_fusion](../../../../examples/poc_machine_condition_fusion.py) — `py -3.11 examples/poc_machine_condition_fusion.py`
- [poc_panorama_drift](../../../../examples/poc_panorama_drift.py) — `py -3.11 examples/poc_panorama_drift.py`
- [poc_print_registration](../../../../examples/poc_print_registration.py) — `py -3.11 examples/poc_print_registration.py`
- [poc_real_stereo_depth](../../../../examples/poc_real_stereo_depth.py) — `py -3.11 examples/poc_real_stereo_depth.py`
- [poc_river_surface_velocity](../../../../examples/poc_river_surface_velocity.py) — `py -3.11 examples/poc_river_surface_velocity.py`
- [poc_screw_thread_metrology](../../../../examples/poc_screw_thread_metrology.py) — `py -3.11 examples/poc_screw_thread_metrology.py`
- [poc_solar_limb_darkening](../../../../examples/poc_solar_limb_darkening.py) — `py -3.11 examples/poc_solar_limb_darkening.py`
- [poc_strain_history](../../../../examples/poc_strain_history.py) — `py -3.11 examples/poc_strain_history.py`
- [poc_surface_roughness](../../../../examples/poc_surface_roughness.py) — `py -3.11 examples/poc_surface_roughness.py`
- [poc_symmetry_restoration](../../../../examples/poc_symmetry_restoration.py) — `py -3.11 examples/poc_symmetry_restoration.py`
- [poc_thermal_radiometry](../../../../examples/poc_thermal_radiometry.py) — `py -3.11 examples/poc_thermal_radiometry.py`
- [poc_water_level](../../../../examples/poc_water_level.py) — `py -3.11 examples/poc_water_level.py`
- [profile_shape_inspection](../../../../examples/profile_shape_inspection.py) — `py -3.11 examples/profile_shape_inspection.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`signal`)

[lowpass](lowpass.md) · [highpass](highpass.md) · [bandpass](bandpass.md) · [envelope](envelope.md) · [resample](resample.md) · [spectrum](spectrum.md) · [spectrogram](spectrogram.md) · [zero_crossing_rate](zero_crossing_rate.md)

---
*Provenance: dsp.py — ONED operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
