---
op: illumination_train
dim: optics
category: illumination
in: 
out: table
examples: [poc_spectrometer_illumination]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# illumination_train — OPTICS `illumination` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.illumination_train(kind='kohler', source_mm=2.0, collector_f_mm=20.0, condenser_f_mm=10.0, field_stop_mm=6.0, aperture_stop_mm=6.0, source_distance_mm=30.0)` (実装を直接呼ぶなら `import illumdesign; illumdesign.illumination_train(kind='kohler', source_mm=2.0, collector_f_mm=20.0, condenser_f_mm=10.0, field_stop_mm=6.0, aperture_stop_mm=6.0, source_distance_mm=30.0)`、台帳から引くなら `opsoptics.get("illumination_train")`)

## 使い方

A microscope illumination train (``kohler`` or ``critical``) laid out paraxially (``table``).

Planes along the axis (thin lenses, distances in mm, z = 0 at the source):

* the source (a disc of diameter *source_mm*) at z = 0;
* the collector (focal length *collector_f_mm*) at z = *source_distance_mm*, with the
  field stop (diameter *field_stop_mm*) right at it; it images the source to z_A;
* the aperture stop (diameter *aperture_stop_mm*) at z_A, on the intermediate source image;
* the condenser (focal length *condenser_f_mm*):

  - ``kohler``: one focal length behind the aperture stop (the stop sits in its front focal
    plane, so the source is imaged to infinity), and the specimen where the condenser images
    the **field stop**;
  - ``critical``: two focal lengths behind the source image (a 1:1 relay), and the specimen
    where the condenser images the **source**. The aperture stop then sits at the source
    image (it trims the source), the field stop is in a pupil-like plane.

Returns the element list (``elements``: dicts with ``type`` lens / stop / source / specimen,
``z_mm``, ``f_mm`` or ``radius_mm``) that :func:`illumination_field` traces, plus the
conjugate bookkeeping read off the ABCD matrices: ``source_to_specimen`` and
``field_stop_to_specimen`` (A, B, C, D — B = 0 means "imaged onto the specimen"),
``source_magnification`` / ``field_stop_magnification`` (A when B = 0, else None),
``field_diameter_mm`` (the lit field: field stop x |M| for Koehler, source x |M| for critical),
``illumination_na`` (on-axis marginal ray: the smallest stop-limited angle), ``source_image_z_mm``.

**Raises** ``ValueError``: unknown kind, non-positive sizes or focal lengths, a source closer
than the collector focal length (no real intermediate image), a specimen that would be virtual.

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

## 背景知識ガイド(この op の手前にある物理・規約)

- [mv_illumination_practice](../guides/mv_illumination_practice.md) — 照明の実務知識 — 波長・偏光・点灯方式・外光・安全

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_spectrometer_illumination](../../../../examples/poc_spectrometer_illumination.py) — `py -3.11 examples/poc_spectrometer_illumination.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`illumination`)

[light_source](light_source.md) · [irradiance_map](irradiance_map.md) · [illumination_uniformity](illumination_uniformity.md) · [defect_contrast](defect_contrast.md) · [lighting_sweep](lighting_sweep.md) · [illumination_design](illumination_design.md) · [solid_angle_light](solid_angle_light.md) · [solid_angle_boundaries](solid_angle_boundaries.md)

---
*Provenance: illumdesign.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
