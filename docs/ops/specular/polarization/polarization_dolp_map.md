---
op: polarization_dolp_map
dim: specular
category: polarization
in: polsweep
out: image2d
gpu: なし
examples: [example_polarization_metal, perf_polarization_analyze, poc_polarization_specular, polarization_camera_pipeline, specular_photometric]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# polarization_dolp_map — SPECULAR `polarization` op

- **データ種**: `polsweep` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.polarization_dolp_map(images, angles_deg=(0.0, 45.0, 90.0, 135.0), max_violation_frac=0.0)` (実装を直接呼ぶなら `import specularity; specularity.polarization_dolp_map(images, angles_deg=(0.0, 45.0, 90.0, 135.0), max_violation_frac=0.0)`、台帳から引くなら `opsspecular.get("polarization_dolp_map")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Degree of linear polarisation, per pixel. → (H, W) in [0, 1].

``sqrt(S1^2 + S2^2) / S0``, from the same sinusoid fit as
:func:`polarization_separate`. It answers the question that decides whether
a polariser is worth mounting at all: **1** means the light at that pixel is
fully linearly polarised and a crossed analyser extinguishes it completely,
**0** means the polariser will only cost you a stop of exposure.

Being a ratio, it is invariant to exposure: scaling every frame by 1e-4,
1e4 or 1e8 moves it by at most 3.9e-16 (measured), which is what makes it
comparable across a production line where the lamps age. Not *bit*-
identical — the least-squares fit rounds differently at a different scale —
and the difference between "invariant" and "bit-identical" is the kind of
claim this library measures rather than asserts.

Pixels with zero total radiance have no degree of polarisation (every ratio
would be 0/0) and are returned as 0.0 rather than as NaN; that is a
convention, and it is stated here because a NaN spreading into a
thresholding routine is exactly the silent failure this library refuses.

★Dark pixels (2026-11-09): "zero" is measured against the noise — a pixel
whose fitted mean ``a0 = S0/2`` is at most :data:`POLAR_DARK_K` (3) × the
noise of the modulation amplitude (``σ̂·√(v₁+v₂)``, one ``σ̂`` for the
image from the residuals of an N > 3 sweep) is returned as 0.0 too, i.e.
where the DoLP's own noise would be 1/3 or more. DoLP is a ratio, and
clipped sensor noise in a dark region (σ 0.001 of a scene peaking at 1)
used to come back as DoLP 1.0 — "completely polarised", the opposite of
the truth — on 72 % of the dark pixels once *max_violation_frac* let the
image through. **A 0 here means "not defined", not "unpolarised"** — use
:func:`polarization_stokes_map`'s ``lit`` to tell them apart. With three
angles there is no residual and only ``S0 = 0`` is 0 (noise-only dark
pixels are not screened). One ``σ̂`` assumes stationary noise; shot noise
grows with the signal, so the floor is set by the typical pixel.

**Raises** ``ValueError``: as :func:`polarization_separate`.

## 詳しい使い方ガイド

- [specular_photometric ファミリ ガイド](../guides/specular_photometric.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [example_polarization_metal](../../../../examples/example_polarization_metal.py) — `py -3.11 examples/example_polarization_metal.py`
- [perf_polarization_analyze](../../../../examples/perf_polarization_analyze.py) — `py -3.11 examples/perf_polarization_analyze.py`
- [poc_polarization_specular](../../../../examples/poc_polarization_specular.py) — `py -3.11 examples/poc_polarization_specular.py`
- [polarization_camera_pipeline](../../../../examples/polarization_camera_pipeline.py) — `py -3.11 examples/polarization_camera_pipeline.py`
- [specular_photometric](../../../../examples/specular_photometric.py) — `py -3.11 examples/specular_photometric.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[polarization_render](polarization_render.md) · [deflectometry_render](../deflectometry/deflectometry_render.md) · [deflectometry_phase_to_slope](../deflectometry/deflectometry_phase_to_slope.md)

## 同カテゴリ(`polarization`)

[polarization_render](polarization_render.md) · [polarization_separate](polarization_separate.md) · [polarization_stokes](polarization_stokes.md) · [polarization_stokes_map](polarization_stokes_map.md)

---
*Provenance: specularity.py — SPECULAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
