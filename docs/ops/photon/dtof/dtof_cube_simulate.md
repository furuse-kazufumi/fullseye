---
op: dtof_cube_simulate
dim: photon
category: dtof
in: depth
out: histcube
examples: [photon_timeresolved]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# dtof_cube_simulate — PHOTON `dtof` op

- **データ種**: `depth` → `histcube`
- **呼び出し**: `import photoncount; photoncount.dtof_cube_simulate(depth, bins=256, bin_ps=100.0, reflectivity=None, signal_photons=20.0, ambient_photons=5.0, irf_fwhm_ps=200.0, seed=0, noise=True)` (または `opsphoton.get("dtof_cube_simulate")`)

## 使い方

Synthesise the ``(H, W, T)`` photon histogram cube a SPAD array produces.

The per-pixel version of :func:`tcspc_simulate`: every pixel of the *depth*
map (metres, one-way distance) gets a Gaussian return at its own round-trip
time ``2d/c``, scaled by *signal_photons* times that pixel's *reflectivity*,
on a uniform ambient pedestal of ``ambient_photons/bins`` per bin, Poisson
sampled with ``numpy.random.default_rng(seed)``.

The output is the cube that :func:`dtof_cube_depth` inverts, and the axis
order is **(H, W, T) with time LAST** — the same layout a SPAD array streams.
That is not the ``(D, H, W)`` of a :mod:`volops` voxel volume; the two are
both 3-D float arrays and swapping them silently produces a plausible-wrong
depth map, which is why :func:`dtof_cube_depth` checks and says so.

``noise=False`` returns the exact expectation cube (no sampling).

Ground truth: with ``noise=False`` the per-pixel centroid of the cube returns
the input depth map to an RMS error of 3.2e-16 m (pinned in the tests) — the
pulse integral is analytic, so the only error is float round-off.

**Raises** ``ValueError``: a non-2-D, non-finite or non-positive *depth*, a
*reflectivity* that is negative or not the same shape as *depth*, a *bins*
outside ``[2, MAX_BINS]``, non-positive *bin_ps* / *irf_fwhm_ps*, negative
photon budgets, a non-integer *seed*, a cube over
:data:`MAX_CUBE_ELEMENTS` (``H*W*bins`` grows fast — 512x512x256 is 8x the
cap), and any depth whose round-trip time falls outside the time window
(which a real sensor would alias into a short distance).

## 詳しい使い方ガイド

- [photon_timeresolved ファミリ ガイド](../guides/photon_timeresolved.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [photon_timeresolved](../../../../examples/photon_timeresolved.py) — `py -3.11 examples/photon_timeresolved.py`

## 型が繋がる次の op(`histcube` を入力に取れる)

[dtof_cube_depth](dtof_cube_depth.md)

## 同カテゴリ(`dtof`)

[dtof_depth](dtof_depth.md) · [dtof_cube_depth](dtof_cube_depth.md)

---
*Provenance: photoncount.py — PHOTON operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
