---
op: wavefront_stats
dim: optics
category: imaging
in: table
out: table
examples: [optics_imaging]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# wavefront_stats — OPTICS `imaging` op

- **データ種**: `table` → `table`
- **呼び出し**: `import optics; optics.wavefront_stats(coeffs, radial=128, angular=192)` (または `opsoptics.get("wavefront_stats")`)

## 使い方

Wavefront error statistics from a Zernike expansion: RMS, PV and Strehl.

*coeffs* is exactly the dict :func:`match3d.fit_zernike` returns —
``{(n, m): coefficient}``, coefficients **in waves** — and this op re-uses
``match3d``'s own basis builder, so the two cannot drift apart in
normalisation or in the ``(n, m)`` convention. Fit with ``fit_zernike``,
characterise here.

The wavefront is reconstructed on a polar grid (*radial* x *angular*) over
the unit pupil and reduced with the **area element** ``rho d(rho) d(theta)``
— an unweighted mean over a uniform-in-rho grid over-counts the centre and
is a real, silent, ~10% error.

Returns a dict: ``rms_waves`` (piston removed — piston is not an
aberration) · ``pv_waves`` peak-to-valley over the pupil · ``strehl`` the
Marechal estimate ``exp(-(2*pi*rms)^2)`` · ``marechal_valid`` whether
``rms_waves <= MARECHAL_RMS_LIMIT`` (0.1), because past that the estimate is
optimistic and reporting the number without the caveat is the dishonest
option · ``terms`` and ``n_max`` of the expansion.

Ground truth it reproduces (measured at the defaults): pure defocus
``{(2, 0): 0.1}`` — for which ``Z = 2*rho^2 - 1`` has an exact pupil RMS of
``1/sqrt(3)`` — gives ``rms_waves = 0.0577422`` against the exact
``0.0577350``, a relative error of 1.2e-4 from the discrete quadrature
(3.1e-5 at ``radial=256``), and ``pv_waves = 0.2`` exactly; the Strehl is
0.8766676 against the exact 0.8766962. Pure astigmatism ``{(2, 2): 0.1}``
(exact RMS ``1/sqrt(6)``) gives 0.0408280 against 0.0408248. Piston alone
(``{(0, 0): c}``) gives rms 0 and Strehl 1 for any ``c``, and RMS scales
exactly linearly in the coefficients (doubling them doubles the RMS to
machine precision).

**Raises** ``ValueError``: *coeffs* is not a dict, is empty, holds more than
:data:`MAX_ZERNIKE_TERMS` terms, has a key that is not an ``(n, m)`` int
pair or is not a valid Zernike index (``n >= 0``, ``|m| <= n``, ``n-|m|``
even), or a non-finite coefficient; a radial order above
:data:`MAX_ZERNIKE_ORDER` (40 — the shared basis builder's factorial
recurrence breaks its own ``|Z| <= 1`` bound at ``n = 46``, measured, and
the same bound is re-checked at runtime); *radial* / *angular* outside
``[8, MAX_GRID]``.

The radial quadrature is discrete, so its error grows with the order being
integrated: measured, the relative RMS error tracks ``(n_max/radial)^2``
within a factor 2 — 1.2e-4 at ``n_max=2``, 1.7e-3 at ``n_max=6`` and 4.3e-2
at ``n_max=20``, all at the default ``radial=128``. Below
``radial >= 16*n_max`` a ``RuntimeWarning`` says so rather than letting a
12%-wrong Strehl look authoritative. Raising *radial* fixes it at
``O(1/radial^2)``, but note the basis is built for *all* orders up to
``n_max``, so the working set grows as ``n_max^2 * radial * angular`` and is
capped by :data:`MAX_ZERNIKE_BASIS`.

Marechal is a small-aberration approximation and the RMS is over the *fitted*
expansion, so it says nothing about wavefront structure finer than ``n_max``
— and ``fit_zernike`` itself discloses ~10% inter-mode crosstalk at its
default sampling. Both limits compound; treat the Strehl as an indicator,
not a measurement.

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

[abcd_matrix](../geometric/abcd_matrix.md)

## 同カテゴリ(`imaging`)

[psf_to_mtf](psf_to_mtf.md) · [mtf_diffraction](mtf_diffraction.md)

---
*Provenance: optics.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
