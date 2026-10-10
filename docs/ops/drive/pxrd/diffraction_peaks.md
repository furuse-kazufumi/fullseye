---
op: diffraction_peaks
dim: drive
category: pxrd
in: signal × signal
out: table
examples: [poc_pxrd_phase_peel]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# diffraction_peaks — DRIVE `pxrd` op

- **データ種**: `signal × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.diffraction_peaks(two_theta, intensity, min_snr=6.0, baseline_window=None, max_peaks=200, noise=None)` (実装を直接呼ぶなら `import pxrd; pxrd.diffraction_peaks(two_theta, intensity, min_snr=6.0, baseline_window=None, max_peaks=200, noise=None)`、台帳から引くなら `opsdrive.get("diffraction_peaks")`)

## 使い方

1-D の回折プロファイルから山を拾い、ガウス + 直線の局所の当てはめで位置・高さ・FWHM・面積を出す。

手順: 窓 ``baseline_window`` [deg] (既定 = 範囲の 4 %)の転がり最小 → 転がり平均で背景を作り、背景を引いた値の
局所の最大のうち ``min_snr`` × 雑音を超えるものを候補にする(雑音は間隔 1〜8 の差分の MAD の最大から。``noise`` に
数か、:func:`azimuthal_integrate` の ``sigma`` のようなビンごとの配列を渡してもよい —— 中心の近くや隅のように画素の
少ないビンの揺れを山と取り違えないためには配列が要る)。各候補の半値幅を目で測る代わりに半値の交点で見積もり、隣の候補との中点で切った窓でガウス + 直線を
``scipy.optimize.least_squares`` で当てる。重なった山は窓が切られるぶん偏る(分けたいなら :func:`phase_fractions`)。

返り値(dict): ``two_theta``・``height``・``fwhm`` [deg]・``area``・``snr``・``fit_ok``(当てはめが収束し窓の中に
収まったか)、``noise``、``baseline``(格子と同じ長さ)。山が無ければ長さ 0 の配列(空 = 失敗ではない)。

Raises ValueError: 長さの不一致・非有限・2θ が増えない、``min_snr <= 0``。

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
