---
op: range_doppler_map
dim: rangedoppler
category: process
in: beatcube
out: image2d
examples: [fmcw_range_doppler]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# range_doppler_map — RANGEDOPPLER `process` op

- **データ種**: `beatcube` → `image2d`
- **呼び出し**: `import rangedoppler; rangedoppler.range_doppler_map(cube, combine='incoherent', antenna=None, normalize=False)` (または `opsrangedoppler.get("range_doppler_map")`)

## 使い方

The 2-D FFT of a beat cube -> a ``(n_doppler, n_range)`` magnitude map.

Fast time transforms to **range** (last axis, not shifted: bin ``j`` is
``j * c*f_s/(2*S*N_s)`` metres, and a physical range is always positive so
the whole ``[0, f_s)`` band is used). Slow time transforms to **velocity**
(middle axis, ``fftshift``ed so the map is centred on zero velocity: bin
``i`` is ``(i - N_c//2) * lambda/(2*N_c*T_c)`` metres per second, positive =
receding).

The antenna axis is collapsed by *combine*: ``"incoherent"`` (default) is the
**mean of the magnitudes**, which is angle independent and therefore the
right default for detection; ``"coherent"`` is the **magnitude of the mean**,
i.e. a beam pointed at boresight, which attenuates an off-boresight target on
purpose. ``antenna=k`` uses element ``k`` alone. For a single-element cube
all three agree exactly.

``normalize=True`` divides by ``N_c * N_s``, so a bin-centred target of
amplitude ``a`` peaks at exactly ``a`` (measured: 1.0 for a unit target,
absolute error 0.0). The default ``False`` keeps the raw FFT magnitude.

No window is applied — compose :func:`fmcw_window_apply` first if you want
one. The output is a plain 2-D float64 array, so every 2-D operator in
Fullseye (threshold, morphology, labelling, blob measurement — the pieces a
CFAR detector is made of) applies to it directly.

**Raises** ``ValueError``: a real-valued cube (it would put a mirror ghost of
every target at a fabricated range), fewer than 2 chirps or 2 samples, an
out-of-range *antenna* index, an unknown *combine*, a cube over the element
cap, an FFT that overflows to NaN, or NaN/Inf on the way in.

## 詳しい使い方ガイド

- [fmcw_range_doppler ファミリ ガイド](../guides/fmcw_range_doppler.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [fmcw_range_doppler](../../../../examples/fmcw_range_doppler.py) — `py -3.11 examples/fmcw_range_doppler.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[range_doppler_peaks](range_doppler_peaks.md)

## 同カテゴリ(`process`)

[fmcw_window_apply](fmcw_window_apply.md) · [range_doppler_peaks](range_doppler_peaks.md) · [fmcw_range_profile](fmcw_range_profile.md)

---
*Provenance: rangedoppler.py — RANGEDOPPLER operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
