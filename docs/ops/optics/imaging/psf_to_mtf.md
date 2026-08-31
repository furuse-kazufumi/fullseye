---
op: psf_to_mtf
dim: optics
category: imaging
in: image2d
out: pairs
examples: [optics_imaging]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# psf_to_mtf — OPTICS `imaging` op

- **データ種**: `image2d` → `pairs`
- **呼び出し**: `import optics; optics.psf_to_mtf(psf, pixel_pitch_um=1.0)` (または `opsoptics.get("psf_to_mtf")`)

## 使い方

Radially-averaged MTF of a measured point-spread function.

``OTF = FFT{PSF}``, ``MTF = |OTF| / |OTF(0)|``, then averaged over annuli of
constant spatial frequency out to the Nyquist limit ``1/(2*pitch)``. This
is the measurement side of resolution: image a point source (or a slit, or
differentiate a knife edge), hand the spot here, and compare the curve with
the diffraction limit from :func:`mtf_diffraction`.

Returns an ``(n, 2)`` float64 ``pairs`` array: column 0 the spatial
frequency in **cycles per millimetre**, column 1 the MTF in [0, 1]. One row
per non-empty radial bin (a very anisotropic array can leave a bin empty;
those rows are dropped rather than filled with a NaN).

Ground truth it reproduces (measured): a delta PSF gives MTF == 1 at every
frequency **exactly** (max deviation 0.0); a Gaussian PSF of sigma pixels
gives the closed form ``exp(-2*pi^2*sigma^2*f^2)`` — the maximum absolute
deviation over the whole curve is 4.1e-4 at sigma = 2 px on 128x128,
8.3e-4 at sigma = 1.5 px on 64x64 and 2.4e-4 at sigma = 3 px on 256x256
(the residual is the radial average over a square grid, not an error in the
transform). Doubling *pixel_pitch_um* halves every reported frequency and
leaves the MTF column bit-identical.

The PSF is **not** re-normalised or re-centred: a PSF whose energy is not
centred carries a linear phase, which the modulus discards, so the MTF is
unaffected — but the *phase* transfer function, which is where a
decentred/asymmetric PSF shows up, is deliberately not summarised here.

**Raises** ``ValueError``: *psf* is not 2-D / smaller than 2x2 / over the
size cap / complex / masked / non-finite; a PSF that sums to zero or less
(the DC normalisation would be 0/0 — an all-zero "PSF" is not a PSF);
non-positive or non-finite *pixel_pitch_um*.

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

## 型が繋がる次の op(`pairs` を入力に取れる)

—

## 同カテゴリ(`imaging`)

[mtf_diffraction](mtf_diffraction.md) · [wavefront_stats](wavefront_stats.md)

---
*Provenance: optics.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
