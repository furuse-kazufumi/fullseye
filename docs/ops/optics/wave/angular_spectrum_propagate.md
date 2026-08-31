---
op: angular_spectrum_propagate
dim: optics
category: wave
in: cimage
out: cimage
examples: [optics_imaging]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# angular_spectrum_propagate — OPTICS `wave` op

- **データ種**: `cimage` → `cimage`
- **呼び出し**: `import optics; optics.angular_spectrum_propagate(field, wavelength_um=0.55, distance_um=100.0, pixel_pitch_um=1.0)` (または `opsoptics.get("angular_spectrum_propagate")`)

## 使い方

Exact scalar free-space propagation of a complex field (angular spectrum).

``U(z) = IFFT{ FFT{U(0)} * exp(i*2*pi*z*sqrt(1/lambda^2 - fx^2 - fy^2)) }``
in the ``exp(-i*omega*t)`` convention, so a positive *distance_um*
propagates forward. Components beyond the propagating cone
(``fx^2 + fy^2 > 1/lambda^2``) are **attenuated** by
``exp(-2*pi*|z|*sqrt(fx^2 + fy^2 - 1/lambda^2))``, which is the physical
evanescent decay — not zeroed, so ``distance_um = 0`` is an *exact*
identity and the transfer function is continuous through it.

Unlike Fresnel propagation this makes no paraxial approximation: it is the
exact solution of the Helmholtz equation for a band-limited field, valid
from a fraction of a wavelength outward.

Returns a complex128 array with the same shape as *field*.

Ground truth it reproduces (measured): ``distance_um = 0`` returns the field
bit-identically (it short-circuits the transform pair); propagating ``+z``
then ``-z`` returns the original to a relative L2 error of 4.3e-16 for a
band-limited field (no evanescent content); total power is conserved to
1.7e-16 relative. A field *with*
evanescent content does **not** round-trip — those components are gone by
construction, in both directions, because that is what physically happens.

*field* is a field in the **space** domain, not a spectrum: do not hand it
the fftshifted output of :func:`complexops.cx_fft`. Real input is promoted
to complex, which loses nothing.

Aliasing: the discrete transfer function is periodic, so a field that
diffracts past the array edge wraps around. The practical guard is the
usual one — pad the field so the propagated support stays inside, and keep
``pixel_pitch_um`` below ``lambda/(2*NA)``. No warning can detect this
reliably from the array alone, so none is invented.

**Raises** ``ValueError``: *field* is not 2-D, smaller than 2x2, larger than
:data:`MAX_FIELD_ELEMENTS`, masked, or non-finite; non-positive or
non-finite *wavelength_um* / *pixel_pitch_um*; non-finite *distance_um*.

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

## 型が繋がる次の op(`cimage` を入力に取れる)

[jones_apply](../polarization/jones_apply.md)

## 同カテゴリ(`wave`)

[airy_pattern](airy_pattern.md) · [fraunhofer_pattern](fraunhofer_pattern.md) · [gaussian_beam](gaussian_beam.md)

---
*Provenance: optics.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
