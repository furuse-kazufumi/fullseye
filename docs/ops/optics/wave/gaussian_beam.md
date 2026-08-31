---
op: gaussian_beam
dim: optics
category: wave
in: 
out: table
examples: [optics_imaging]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# gaussian_beam — OPTICS `wave` op

- **データ種**: `` → `table`
- **呼び出し**: `import optics; optics.gaussian_beam(waist_um=100.0, wavelength_um=1.064, distance_mm=0.0, n_medium=1.0)` (または `opsoptics.get("gaussian_beam")`)

## 使い方

Gaussian-beam propagation: spot size, wavefront curvature and Gouy phase.

The ``q``-parameter solution of the paraxial wave equation, evaluated at
*distance_mm* from the waist. With ``zR = pi*w0^2*n/lambda``:

``w(z) = w0*sqrt(1 + (z/zR)^2)`` · ``R(z) = z*(1 + (zR/z)^2)`` ·
``psi(z) = arctan(z/zR)`` (Gouy) · far-field half-divergence
``theta = lambda/(pi*n*w0)``.

Returns a dict: ``radius_um`` the 1/e^2 field radius ``w(z)`` ·
``rayleigh_mm`` ``zR`` · ``wavefront_radius_mm`` ``R(z)`` ·
``curvature_per_mm`` ``1/R(z)`` · ``gouy_deg`` · ``divergence_mrad`` the
far-field half angle · ``waist_um`` and ``distance_mm`` echoed back.

**``wavefront_radius_mm`` is ``inf`` exactly at the waist, by contract**:
the wavefront there is planar and a plane has infinite radius. That is why
``curvature_per_mm`` is also returned — it is 0 at the waist and finite
everywhere, so downstream arithmetic never has to divide by an infinity.
A negative ``R`` (before the waist, ``z < 0``) means a converging wavefront.

Ground truth it reproduces exactly (verified at machine precision): at
``z = zR`` the spot is ``sqrt(2)*w0``, the wavefront radius is ``2*zR`` (its
minimum over all z) and the Gouy phase is exactly 45 degrees; the
beam-parameter product ``w0*theta = lambda/(pi*n)`` holds for every input.

**Raises** ``ValueError``: non-positive or non-finite *waist_um*,
*wavelength_um*, *n_medium*; non-finite *distance_mm*.

Paraxial and fundamental-mode (TEM00) only: a real multimode beam needs an
``M^2`` factor, which this op deliberately does not fake by accepting one
silently.

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

- [optics_imaging](../../../../examples/optics_imaging.py) — `py -3.11 examples/optics_imaging.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md)

## 同カテゴリ(`wave`)

[airy_pattern](airy_pattern.md) · [angular_spectrum_propagate](angular_spectrum_propagate.md) · [fraunhofer_pattern](fraunhofer_pattern.md)

---
*Provenance: optics.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
