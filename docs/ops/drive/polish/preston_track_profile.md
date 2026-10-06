---
op: preston_track_profile
dim: drive
category: polish
in: signal × scalar × scalar × scalar
out: signal
examples: [poc_polish_wipe_measure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# preston_track_profile — DRIVE `polish` op

- **データ種**: `signal × scalar × scalar × scalar` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.preston_track_profile(y, force: 'float', radius: 'float', k_p: 'float', kind: 'str' = 'flat', spin: 'float' = 0.0, speed=None, estar=None) -> 'np.ndarray'` (実装を直接呼ぶなら `import polish; polish.preston_track_profile(y, force: 'float', radius: 'float', k_p: 'float', kind: 'str' = 'flat', spin: 'float' = 0.0, speed=None, estar=None) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("preston_track_profile")`)

## 使い方

長い直線の一筆(+x へ進む)の断面の除去の深さ h(y) [m] (y = 進む向きの左が正の横ずれ、``y`` と同じ形)。閉形式:
平板 2 k_p p √(a² − y²)、Hertz k_p (E*/R)(a² − y²)(a は力から Hertz で)、回る平板(``spin`` = ω、``speed`` = v が要る)
(k_p p / v)[c √(b² + ω²c²) + (b²/ω) asinh(ωc/|b|)] (c = √(a² − y²)、b = v − ωy)。|y| ≥ a は 0。
**Raises** ValueError: 数の検査、回る時に速さが無い、Hertz で回す(閉形式が無い)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_polish_wipe_measure](../../../../examples/poc_polish_wipe_measure.py) — `py -3.11 examples/poc_polish_wipe_measure.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[flight_vacuum](../ball/flight_vacuum.md) · [magnus_lift_coefficient](../ball/magnus_lift_coefficient.md) · [drag_coefficient_sphere](../ball/drag_coefficient_sphere.md) · [restitution_from_apexes](../ball/restitution_from_apexes.md) · [restitution_from_intervals](../ball/restitution_from_intervals.md) · [fit_parabola](../ball/fit_parabola.md) · [flight_fit](../ball/flight_fit.md) · [fit_aero](../ball/fit_aero.md)

## 同カテゴリ(`polish`)

[preston_pressure_kernel](preston_pressure_kernel.md) · [preston_removal_map](preston_removal_map.md) · [wipe_band_width](wipe_band_width.md) · [raster_wipe_area](raster_wipe_area.md) · [coat_image](coat_image.md) · [coat_thickness_from_image](coat_thickness_from_image.md) · [wipe_coverage](wipe_coverage.md) · [band_width_profile](band_width_profile.md)

---
*Provenance: polish.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
