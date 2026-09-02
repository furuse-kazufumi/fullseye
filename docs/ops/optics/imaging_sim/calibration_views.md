---
op: calibration_views
dim: optics
category: imaging_sim
in: table
out: table
examples: [lens_calibration_loop_demo]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# calibration_views — OPTICS `imaging_sim` op

- **データ種**: `table` → `table`
- **呼び出し**: `import lensimage; lensimage.calibration_views(system, image_size=(1024, 1024), pixel_pitch_um=5.5, target=(9, 7, 5.0), poses=None, distance_mm=None, noise_px=0.0, seed=0, order=2)` (または `opsoptics.get("calibration_views")`)

## 使い方

Synthetic camera-calibration views of a planar target through the designed lens (``table``).

A chessboard-like grid of *target* = (cols, rows, pitch_mm) corner points
on the plane z = 0 is placed at each of *poses* — ``(rx_deg, ry_deg,
rz_deg, tx_mm, ty_mm, tz_mm)`` in the camera frame (camera at the origin
looking along +z; default: five poses, frontal and ±20° about x and y, at
*distance_mm* — default the distance at which the target spans 60 % of
the sensor width) — projected by a pinhole of the prescription's EFL and
then displaced by the lens's **real radial distortion** (the polynomial
:func:`distortion_map` fits from traced chief rays), and expressed as
``(row, col)`` pixels on an *image_size* sensor of *pixel_pitch_um*.
Optional Gaussian corner-detection noise *noise_px* (deterministic for
*seed*).

Returns ``object_points`` (N,2) mm on the target plane, ``image_points``
(a list of (N,2) ``(row, col)`` arrays — exactly what
``calib.camera_calibration`` consumes), ``K_true`` (fx = fy = EFL/pitch
px, cx, cy at the sensor centre), the distortion polynomial, the poses,
and per view the fraction of points that landed on the sensor. Views with
fewer than four visible points, a target behind the camera, or an afocal
prescription are ``ValueError``.

The point of the op is the **closed loop**: feed the output to
``calib.camera_calibration`` and compare the recovered intrinsics with
``K_true`` — for a distortion-free lens (the paraboloid) Zhang's method
returns the EFL to 1e-6, and the singlet's barrel distortion shows up as a
focal-length bias and a non-zero reprojection RMS, so the calibration
module is checked end to end against a lens whose truth is known, and a
real chart can be judged against the same numbers.

## ファミリ共通の入力契約(fail-closed)

optics の全 op は入力を検証してから計算する(黙って通さない):

- **単位は引数名に埋め込む** — `_mm` / `_um` / `_deg` / `_mrad`。mm と µm の取り違えは crash ではなく「もっともらしく間違った答え」なので、名前で防ぐ。大きさから単位を推測する処理は一切しない。
- **文字列は `ValueError`** — `float('50')` は成功してしまうため、未パースの設定値が長さとして通り抜ける(実測: `thin_lens('50', '200')` がもっともらしい 66.667 mm を返していた)。bool も `True == 1` の暗黙昇格として拒否。
- **complex / masked array は `ValueError`**(実数枠のみ。虚部の無言切り捨て・マスク剥がしを拒否)。**NaN/Inf は全入力で `ValueError`**。
- **0 除算とその親戚を名指しで拒否**: 焦点距離 0・曲率半径 0・屈折率 <= 0・不透明な開口(全 0 なので正規化が 0/0)・総和 <= 0 の PSF・S0 = 0 の Stokes ベクトル・物体が前側焦点にある(像が無限遠)。
- **非有限を返すのは 2 op だけ、しかも契約として明記**: `depth_of_field` の過焦点距離以遠の `far_mm = inf`(それが過焦点距離の定義)と `gaussian_beam` のウエストでの `wavefront_radius_mm = inf`(平面波面の曲率半径)。どちらも有限の相棒(`far_is_infinite` / `curvature_per_mm`)を併せて返す。**それ以外の無言 NaN/Inf は内部で検出して `ValueError`** —「float64 が溢れた」と「答えが無限大」は別の主張なので、後者の顔で前者を返さない。
- **サイズ上限**: 生成格子は `optics.MAX_GRID`(4096)、供給された場/PSF/開口は `optics.MAX_FIELD_ELEMENTS`(2^24)、ABCD 素子列は `optics.MAX_SYSTEM_ELEMENTS`(1024)、Zernike は `MAX_ZERNIKE_TERMS`(512)/ `MAX_ZERNIKE_ORDER`(40)/ `MAX_ZERNIKE_BASIS`(2^25)。小さな引数から巨大な内部確保が起きる経路(実測: n_max=40 × 4096² で 108 GB)を fail-closed で塞ぐ。
- **物理的に不可能な状態も拒否**: 偏光度 > 1 の Stokes ベクトル、負の透過率、負の強度、n-|m| が奇数などの不正な Zernike 添字。

## 詳しい使い方ガイド

- [optics_imaging ファミリ ガイド](../guides/optics_imaging.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [lens_calibration_loop_demo](../../../../examples/lens_calibration_loop_demo.py) — `py -3.11 examples/lens_calibration_loop_demo.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md) · [spot_diagram](../design/spot_diagram.md)

## 同カテゴリ(`imaging_sim`)

[psf_from_opd](psf_from_opd.md) · [distortion_map](distortion_map.md) · [render_through_lens](render_through_lens.md) · [defect_dataset](defect_dataset.md)

---
*Provenance: lensimage.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
