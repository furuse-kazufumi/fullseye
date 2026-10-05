---
op: detector_calibrate
dim: drive
category: pxrd
in: image2d × signal × table
out: table
examples: [poc_pxrd_phase_peel]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# detector_calibrate — DRIVE `pxrd` op

- **データ種**: `image2d × signal × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.detector_calibrate(image, d_spacings, geometry_guess, n_azimuth=180, fit_tilt=True, min_rings=2)` (実装を直接呼ぶなら `import pxrd; pxrd.detector_calibrate(image, d_spacings, geometry_guess, n_azimuth=180, fit_tilt=True, min_rings=2)`、台帳から引くなら `opsdrive.get("detector_calibrate")`)

## 使い方

既知の標準(Si など)の環から検出器の中心・距離・傾きを較正する。

    ``d_spacings`` は標準の面間隔 [Å] の list(強い順でなくてよい)、``geometry_guess`` には少なくとも ``pixel`` と
    ``wavelength``、分かっていれば ``cx``・``cy``・``distance``・``tilt``・``tilt_dir`` を入れる。手順:

    1. 中心が無ければ明るい画素の重心から始め、最も強い環を光線に沿って拾い、円の当てはめで中心を 3 回更新する。
    2. 距離が無ければ、半径方向のプロファイルの最初の山を d の候補(小さい 2θ から 4 本)に当て、他の環の予測と
       観測の山が最も多く一致する組を選ぶ。
    3. 現在の幾何で各環の位置を ``n_azimuth`` 本の光線上で予測し、窓の中の強度の重心で点を拾い、
       ``scipy.optimize.least_squares`` で ``(cx, cy, distance, tilt の 2 成分)`` を 2θ の残差 [deg] で当てる。窓を
       縮めながら 3 回。傾きは回転ベクトルの 2 成分 ``tilt·(cos φ, sin φ)`` で解く(傾き 0 で φ が不定になる特異点を避ける)。

    返り値(dict): 幾何(``cx``・``cy``・``distance``・``pixel``・``wavelength``・``tilt``・``tilt_dir``)に
    ``rms_two_theta_deg``・``n_points``・``n_rings``・``rings_deg``・``ok``(rms が画素 1/4 の角 ``0.25·pixel/distance`` 未満
かつ環 >= ``min_rings``)を足したもの。

    Raises ValueError: 像が 2-D でない、d が 1 本も無い、pixel / wavelength が無い、環が ``min_rings`` 本見つからない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_pxrd_phase_peel](../../../../examples/poc_pxrd_phase_peel.py) — `py -3.11 examples/poc_pxrd_phase_peel.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pxrd`)

[cif_read](cif_read.md) · [cubic_prototype](cubic_prototype.md) · [powder_reflections](powder_reflections.md) · [scherrer_size](scherrer_size.md) · [debye_ring_image](debye_ring_image.md) · [detector_two_theta](detector_two_theta.md) · [azimuthal_integrate](azimuthal_integrate.md) · [diffraction_peaks](diffraction_peaks.md)

---
*Provenance: pxrd.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
