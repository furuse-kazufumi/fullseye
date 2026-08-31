---
op: mtf_diffraction
dim: optics
category: imaging
in: 
out: pairs
examples: [optics_imaging]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# mtf_diffraction — OPTICS `imaging` op

- **データ種**: `` → `pairs`
- **呼び出し**: `import optics; optics.mtf_diffraction(f_number=5.6, wavelength_um=0.55, samples=64)` (または `opsoptics.get("mtf_diffraction")`)

## 使い方

The diffraction-limited MTF of a circular pupil (closed form).

``MTF(x) = (2/pi)*(arccos(x) - x*sqrt(1 - x^2))`` with ``x = nu/nu_c`` the
frequency normalised to the cutoff ``nu_c = 1/(lambda*N)``. This is the
ceiling: no aberration-free lens at this f-number can do better, and a
measured :func:`psf_to_mtf` curve above it means the measurement is wrong.

Returns a ``(samples, 2)`` float64 ``pairs`` array: column 0 the spatial
frequency in **cycles per millimetre** from 0 to the cutoff, column 1 the
MTF in [0, 1].

Ground truth it reproduces exactly (machine precision): ``MTF(0) = 1``,
``MTF(nu_c) = 0``, and at half the cutoff the textbook ``0.391``
(``(2/pi)*(pi/3 - sqrt(3)/4) = 0.3910022...``). The cutoff itself at
``lambda = 0.55 um``, ``N = 5.6`` is ``324.7 cycles/mm`` — which is why
stopping a machine-vision lens past f/8 stops buying depth of field and
starts buying blur (compare :func:`depth_of_field`).

**Raises** ``ValueError``: non-positive or non-finite *f_number* /
*wavelength_um*; *samples* outside ``[2, MAX_GRID]``.

Incoherent illumination, circular unobstructed pupil, no aberration, no
defocus, and no detector: the pixel aperture and the sensor's own MTF
multiply on top of this and are not included.

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

[psf_to_mtf](psf_to_mtf.md) · [wavefront_stats](wavefront_stats.md)

---
*Provenance: optics.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
