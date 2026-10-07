---
op: crt_displacement
dim: residue
category: image
in: image2d × image2d
out: table
examples: [poc_residue_crt]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# crt_displacement — RESIDUE `image` op

- **データ種**: `image2d × image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.crt_displacement(image0, image1, periods=(5.0, 7.0, 9.0, 11.0, 13.0, 16.0), sigma_px=40.0, max_disp=40.0, axis='x', refine=2) -> 'dict'` (実装を直接呼ぶなら `import residue; residue.crt_displacement(image0, image1, periods=(5.0, 7.0, 9.0, 11.0, 13.0, 16.0), sigma_px=40.0, max_disp=40.0, axis='x', refine=2) -> 'dict'`、台帳から引くなら `opsresidue.get("crt_displacement")`)

## 使い方

Local displacement from band phases at several wavelengths, unwrapped by CRT -> ``dict``.

A band of wavelength ``p`` measures the local shift only modulo ``p``, so
any single-band phase method breaks at ``|d| = p/2`` (``motionmag.phase_displacement``
reports this as ``wrap_limit_px``). Bands at *coprime* wavelengths each break
there too, but together they fix ``d`` over the least common multiple —
693 px for 7/9/11 — so the limit becomes ``max_disp``, the search half-width.

``image1`` is ``image0`` with its content moved by ``d(y, x)`` along ``axis``
(``"x"`` = columns, ``"y"`` = rows; positive towards increasing index) —
``image1 = np.roll(image0, +d)`` gives ``+d``. Note that
``filters_freq.phase_correlation_fft(image0, image1)`` uses the *opposite* sign
(it returns ``-d``); flip one when swapping methods. For each
wavelength a Gaussian band-pass (analytic, one-sided, spatial std ``sigma_px``)
gives a local phase and a *local* wavelength (measured, not nominal — see
``_band_measure``); their phase differences are residues of ``d``; amplitude
products are the weights; every pixel is solved by the phasor-agreement search
of :func:`residue_crt`. ``refine`` iterations then warp ``image1`` back by the
current estimate and add the (now small, wrap-free) weighted residual.

Returns ``{"d", "weight", "margin", "residual", "valid", "wrap_limit_single_px"}``.
``valid`` = enough contrast in the bands *and* a margin above 0.05; a pixel
that fails is still returned but should not be trusted.

**Where it applies**: textured regions that each move (nearly) rigidly by a
large amount — measured on two regions of the public scikit-image textures moving
+20 / -15 px, pixels farther than 1.5 ``sigma_px`` from the region boundary are
off by more than 1 px on 2 % (grass) / 5 % (gravel) / 6 % (brick), where the
best pyramid Lucas-Kanade (3-6 levels) is off on 49 / 50 / 67 %.
**Where it does not**: within ~1.5 ``sigma_px`` of a motion boundary; where the
displacement changes inside the window (a 6 px field with gradient 0.07 is
already off on half the pixels — a band narrow enough to keep the local
frequency stable needs a window too wide to follow the field); flat regions
(``weight`` and ``valid`` say where); occlusions. A single global translation is
better served by phase correlation. Numbers: ``examples/poc_residue_crt.py``.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_residue_crt](../../../../examples/poc_residue_crt.py) — `py -3.11 examples/poc_residue_crt.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`image`)

[harmonic_rotation](harmonic_rotation.md)

---
*Provenance: residue.py — RESIDUE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
