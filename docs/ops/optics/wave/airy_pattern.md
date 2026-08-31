---
op: airy_pattern
dim: optics
category: wave
in: 
out: image2d
examples: [optics_imaging]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# airy_pattern — OPTICS `wave` op

- **データ種**: `` → `image2d`
- **呼び出し**: `import optics; optics.airy_pattern(size=64, wavelength_um=0.55, f_number=5.6, pixel_pitch_um=0.5)` (または `opsoptics.get("airy_pattern")`)

## 使い方

The diffraction-limited PSF of a circular pupil (Airy pattern).

``I(r) = [2*J1(v)/v]^2`` with ``v = pi*r/(lambda*N)``, ``r`` the radial
distance in the image plane, ``N`` the working f-number. Sampled on a
``size x size`` grid centred between pixels for even *size* and on a pixel
for odd *size*. The normalisation is **analytic** (``I(0) = 1`` by the
``v -> 0`` limit), not a division by the sampled maximum: for odd *size*
the centre pixel is therefore exactly 1.0, and for even *size* the true
peak falls between pixels so the largest *sample* is below it (0.9679 at
``size = 8`` with the defaults, measured). Rescaling to the sampled maximum
instead would quietly change the physics with the parity of the grid.

Returns a ``(size, size)`` float64 intensity image.

Ground truth it reproduces (measured, ``tests/test_optics.py``): the first
dark ring sits at the first zero of ``J1``, ``r = 1.2197*lambda*N`` — at
``lambda = 0.55 um``, ``N = 5.6`` that is ``3.7567 um``, and the sampled
radial minimum lands at ``3.760 um`` on a 0.01 um grid (0.3 of a sample
away, which is the sampling, not an error); the peak is exactly 1.0 at the
centre and the pattern is symmetric to 1e-16.

The encircled energy inside that ring is the textbook 83.8% of the *whole
infinite* pattern — which a finite grid cannot measure: the Airy tails fall
off only as ``1/r^3``, so a 25.6 um half-width grid reports 0.857 and a
51.2 um one 0.847 (both measured). The number is quoted here as physics,
not as something this op returns.

The ``v -> 0`` limit is evaluated **explicitly** as 1.0 rather than left to
``0/0``: that division is the classic silent-NaN in every hand-rolled Airy
routine, and the centre pixel is exactly where it bites.

**Raises** ``ValueError``: *size* outside ``[2, MAX_GRID]``; non-positive or
non-finite *wavelength_um*, *f_number*, *pixel_pitch_um*.

Scalar, aberration-free, unobstructed circular pupil, low NA. A central
obscuration (a mirror telescope) changes the ring structure; high NA needs a
vector treatment. For the *measured* PSF of a real system use
:func:`psf_to_mtf` on an image of a point source instead.

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

## 型が繋がる次の op(`image2d` を入力に取れる)

[fraunhofer_pattern](fraunhofer_pattern.md) · [psf_to_mtf](../imaging/psf_to_mtf.md)

## 同カテゴリ(`wave`)

[angular_spectrum_propagate](angular_spectrum_propagate.md) · [fraunhofer_pattern](fraunhofer_pattern.md) · [gaussian_beam](gaussian_beam.md)

---
*Provenance: optics.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
