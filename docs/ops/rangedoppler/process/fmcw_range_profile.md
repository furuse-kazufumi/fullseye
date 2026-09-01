---
op: fmcw_range_profile
dim: rangedoppler
category: process
in: beatcube
out: signal
examples: [fmcw_range_doppler]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# fmcw_range_profile — RANGEDOPPLER `process` op

- **データ種**: `beatcube` → `signal`
- **呼び出し**: `import rangedoppler; rangedoppler.fmcw_range_profile(cube, chirp=None, antenna=None, normalize=False)` (または `opsrangedoppler.get("fmcw_range_profile")`)

## 使い方

Range-only profile: the fast-time FFT magnitude, averaged over the rest.

The 1-D marginal of :func:`range_doppler_map` — what a static scene needs,
and what a single chirp can give. Magnitudes are averaged (never the complex
values) over chirps and antennas, so the average is independent of the
target's velocity and angle: ``|FFT|`` does not rotate with the Doppler
phase, only the phase does.

Bin ``j`` is ``j * c*f_s/(2*S*N_s)`` metres. With ``normalize=True`` a
bin-centred target of amplitude ``a`` peaks at exactly ``a``.

*chirp* / *antenna* select one slice instead of averaging. Returns a 1-D
float64 array of length ``n_samples`` — a plain signal, so :mod:`dsp` and
:mod:`funct1d` (``find_peaks``, ``smooth_funct_1d_gauss``, ``spectrum``)
apply to it directly.

**Raises** ``ValueError``: as :func:`range_doppler_map`, plus an
out-of-bounds *chirp* index.

## 詳しい使い方ガイド

- [fmcw_range_doppler ファミリ ガイド](../guides/fmcw_range_doppler.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [fmcw_range_doppler](../../../../examples/fmcw_range_doppler.py) — `py -3.11 examples/fmcw_range_doppler.py`

## 型が繋がる次の op(`signal` を入力に取れる)

—

## 同カテゴリ(`process`)

[fmcw_window_apply](fmcw_window_apply.md) · [range_doppler_map](range_doppler_map.md) · [range_doppler_peaks](range_doppler_peaks.md)

---
*Provenance: rangedoppler.py — RANGEDOPPLER operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
