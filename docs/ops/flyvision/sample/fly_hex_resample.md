---
op: fly_hex_resample
dim: flyvision
category: sample
in: image2d × table
out: signal
examples: [poc_fly_optomotor_steering, poc_fly_vision]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# fly_hex_resample — FLYVISION `sample` op

- **データ種**: `image2d × table` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.fly_hex_resample(image2d, lattice, drho_deg=8.23, fov_deg=90.0, mode='pinhole')` (実装を直接呼ぶなら `import flyvision; flyvision.fly_hex_resample(image2d, lattice, drho_deg=8.23, fov_deg=90.0, mode='pinhole')`、台帳から引くなら `opsflyvision.get("fly_hex_resample")`)

## 使い方

Resample a pinhole image onto an ommatidial lattice (the eye's view).

Each ommatidium integrates the image under a Gaussian acceptance function of
full width at half maximum *drho_deg* weighted by the pixel solid angle::

    signal_i = sum_p w_ip * image_p / sum_p w_ip
    w_ip = exp(-4 ln2 * a_ip^2 / drho_deg^2) * (1 + X_p^2 + Y_p^2)^(-3/2)

with ``a_ip`` the angular distance between ommatidium *i* and pixel *p*, cut
off at ``a <= 2*drho_deg``, and ``X, Y`` the pinhole-normalised pixel
coordinates. The image is a perspective (pinhole) view whose optical axis is
the lattice centre and whose *fov_deg* is the full **vertical** field of view.

image2d:  a 2-D ``(H, W)`` pinhole image.
lattice:  the dict returned by :func:`fly_hex_lattice`.
drho_deg: the acceptance FWHM in degrees.
fov_deg:  the full vertical field of view in degrees.
mode:     ``"pinhole"`` (the only projection implemented).

Returns a 1-D float64 signal of ``n`` ommatidial intensities.

Ground truth: an azimuthal sinusoid of angular wavelength ``lambda`` is
sampled with its amplitude scaled by the analytic modulation transfer
``exp(-pi^2 drho_deg^2 nu^2 / (4 ln2))``, ``nu = 1/lambda``, to within 0.05
over ``lambda`` from 15 to 80 degrees at equatorial ommatidia (pinned in the
tests).

**Raises** ``ValueError``: a non-2-D / empty / non-finite *image2d*, an image
over the element cap, a *lattice* that is not a :func:`fly_hex_lattice` result,
a non-positive *drho_deg* / *fov_deg*, a *fov_deg* not below 180, an unknown
*mode*, a ``n_ommatidia * n_pixels`` product over :data:`MAX_RESAMPLE_ELEMENTS`,
and — this is the field-of-view guard — any ommatidium whose nearest pixel is
farther than ``dphi_rad/2`` away (the eye is looking outside the image).

## 詳しい使い方ガイド

- [fly_vision ファミリ ガイド](../guides/fly_vision.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_fly_optomotor_steering](../../../../examples/poc_fly_optomotor_steering.py) — `py -3.11 examples/poc_fly_optomotor_steering.py`
- [poc_fly_vision](../../../../examples/poc_fly_vision.py) — `py -3.11 examples/poc_fly_vision.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[fly_hex_quantize](fly_hex_quantize.md) · [fly_emd_response](../motion/fly_emd_response.md) · [fly_lgmd_eta](../looming/fly_lgmd_eta.md) · [fly_tau_from_expansion](../looming/fly_tau_from_expansion.md) · [fly_dsi](../tuning/fly_dsi.md)

## 同カテゴリ(`sample`)

[fly_hex_quantize](fly_hex_quantize.md)

---
*Provenance: flyvision.py — FLYVISION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
