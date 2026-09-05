---
op: filtered_backprojection
dim: tomography
category: reconstruct
in: sinogram
out: image2d
examples: [ct_reconstruction]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# filtered_backprojection — TOMOGRAPHY `reconstruct` op

- **データ種**: `sinogram` → `image2d`
- **呼び出し**: `import tomography; tomography.filtered_backprojection(sinogram, angles_deg=None, size=None, filter_name='ramp', cutoff=1.0, span_deg=None, _op='filtered_backprojection')` (または `opstomography.get("filtered_backprojection")`)

## 使い方

Filtered back-projection (FBP) — the standard CT reconstruction.

Filter each projection along the detector axis with the ramp ``|f|`` (times an
optional apodisation window), then back-project. This is the discretised
inverse Radon transform, and with enough samples it is exact: reconstructing a
uniform disc of density 1.0 from its **analytic** sinogram returns an interior
mean of **0.9954** with 363 detector bins and **0.9997** with 727, converging
on the truth as the *detector* is refined and not as the view count is (180,
360 and 720 views give the same 0.9954 to six figures). That absolute value is
what pins the ordinary-versus-angular frequency convention in the ramp: the
other convention, equally defensible and printed in the same textbooks, would
return ``2*pi`` times this, and a CT slice has no absolute grey level for
anyone to notice against.

Where it breaks, measured on the Shepp-Logan phantom (256 px, **analytic**
sinogram so the projector contributes no error of its own; normalised RMS
error against the truth):

    views     FBP (ramp)    SART (10 sweeps)    FBP/SART
      180        0.0250          0.0175           1.43
       90        0.0454          0.0195           2.33
       45        0.1039          0.0353           2.95
       32        0.1362          0.0497           2.74
       16        0.2341          0.0859           2.72
        8        0.3635          0.1257           2.89

**There is no crossing point, and the expectation that there would be one was
wrong.** The received story is that FBP wins when the data is complete and
loses only in the sparse regime; measured here, SART with a non-negativity
constraint is better at *every* view count — by 1.43x at 180 views and by
about 2.9x once the scan is sparse. What changes with the view count is the
price, not the ranking: at 180 views SART costs **312x** the wall clock
(37.7 s against 0.12 s for a 256-px slice) to buy that 1.43x, which is why
filtered back-projection is what production scanners run. At the sparse end
the same 2.9x comes nearly free, because both methods scale with the views.

With noise the ranking holds but the margins change, and the apodisation
windows stop being decoration (Poisson counts at ``I0 = 2e4``, same phantom):

    views    FBP ramp    FBP hann    SART (10 sweeps)
      180      0.0360      0.0371         0.0291
       45      0.1159      0.0766         0.0385
       16      0.2481      0.1921         0.0864
        8      0.3813      0.3093         0.1259

At 180 views the exact ramp beats Hann — the data is complete and the roll-off
only blurs. At 45 views and below Hann beats the exact inverse by up to 1.5x,
because the frequencies the ramp is busy amplifying were never measured.

Filters, and what they trade: ``"ramp"`` is the exact inverse and therefore
the sharpest and the noisiest; ``"shepp-logan"``, ``"cosine"``, ``"hann"`` and
``"hamming"`` roll the high frequencies off, in that order of aggressiveness.
``"none"`` skips the filter entirely and gives :func:`backproject_sinogram`.

:param sinogram: ``(n_angles, n_detectors)``, rows = angles.
:param angles_deg: view angles in degrees; ``None`` -> uniform ``[0, 180)``
    with one view per row.
:param size: output side; ``None`` -> the inscribed square.
:param filter_name: one of :data:`FILTERS`.
:param cutoff: fraction of Nyquist to keep, ``(0, 1]``.
:param span_deg: angular range for the ``d(theta)`` weight; ``None`` -> the
    range the views actually cover, inferred from the angle list (exact for
    a uniform grid over any span and for any full-coverage irregular set
    such as golden angle; see :func:`_span_weight`).
:returns: ``(size, size)`` float64 image.
:raises ValueError: on a non-2-D or non-finite sinogram, an angle count that
    disagrees with the row count, an unknown filter, a cutoff outside
    ``(0, 1]``, or an output over :data:`MAX_IMAGE_ELEMENTS`.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [ct_reconstruction](../../../../examples/ct_reconstruction.py) — `py -3.11 examples/ct_reconstruction.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[radon_transform](../forward/radon_transform.md)

## 同カテゴリ(`reconstruct`)

[backproject_sinogram](backproject_sinogram.md) · [sart_reconstruct](sart_reconstruct.md)

---
*Provenance: tomography.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
