---
op: lockin_ring_normals
dim: optics
category: lockin
in: table
out: table
gpu: なし
examples: [poc_lockin_imaging]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# lockin_ring_normals — OPTICS `lockin` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.lockin_ring_normals(demod, zenith_deg) -> 'dict'` (実装を直接呼ぶなら `import lockin; lockin.lockin_ring_normals(demod, zenith_deg) -> 'dict'`、台帳から引くなら `opsoptics.get("lockin_ring_normals")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Surface normals from the first-harmonic response of a dipole-modulated ring -> dict of maps.

For a Lambertian pixel with unit normal ``n = (n_x, n_y, n_z)`` under a ring of sources at zenith angle
``zeta`` modulated with multipole 1, the response at the modulation frequency is
``z = A exp(j phi) = (rho / 2) sin(zeta) (n_x - j n_y)`` and the DC is ``rho cos(zeta) n_z`` (per unit ring
power). The albedo ``rho`` cancels: ``(n_x - j n_y) / n_z = 2 z / (DC tan zeta)``. ``demod`` is the table of
:func:`lockin_demodulate`. The result has ``height_gradient_x`` / ``height_gradient_y`` (-n_x / n_z, -n_y / n_z),
``normal`` (H, W, 3), ``tilt_deg``, ``azimuth_deg`` (direction of the height gradient) and ``valid``.
A pixel is valid only if no source of the ring is in shadow, which is ``A / DC < 1/2`` (tilt below 90 - zenith_deg);
the other pixels, and pixels with DC <= 0, are NaN in every map and False in ``valid``: the model does not apply there.

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

- [poc_lockin_imaging](../../../../examples/poc_lockin_imaging.py) — `py -3.11 examples/poc_lockin_imaging.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`lockin`)

[lockin_demodulate](lockin_demodulate.md) · [lockin_amplitude](lockin_amplitude.md) · [lockin_phase](lockin_phase.md) · [lockin_noise_floor](lockin_noise_floor.md) · [lockin_walsh_codes](lockin_walsh_codes.md) · [lockin_separate](lockin_separate.md) · [lockin_ring_synthesize](lockin_ring_synthesize.md) · [lockin_thermal_wave](lockin_thermal_wave.md)

---
*Provenance: lockin.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
