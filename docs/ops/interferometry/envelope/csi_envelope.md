---
op: csi_envelope
dim: interferometry
category: envelope
in: sweep
out: signal
examples: [coherence_scanning]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# csi_envelope — INTERFEROMETRY `envelope` op

- **データ種**: `sweep` → `signal`
- **呼び出し**: `import interferometry; interferometry.csi_envelope(signal, remove_bias=True)` (または `opsinterferometry.get("csi_envelope")`)

## 使い方

Coherence envelope of a z-scan interferogram (analytic-signal magnitude).

``dsp.envelope`` computes ``|hilbert(x)|`` for any 1-D signal and is called
here verbatim, so the two can never drift apart. The one thing added is the
one thing an interferogram needs and a generic signal does not: **removal of
the intensity pedestal**. An interferogram is ``a + b*V(z)*cos(...)`` with
``a > 0``, and the analytic-signal magnitude of that is not ``b*V`` — the DC
term passes through the Hilbert transform untouched and dominates.

Measured on the module's reference scan (``a = 0.5``, ``b = 0.4``, envelope
sigma 1.2 um, surface centred): with the bias removed the envelope matches the
analytic ``b*V(z)`` to **1.83e-07**; without it, the error is **0.5** — the
entire pedestal — and the recovered "envelope" never goes near zero.
``dsp.envelope`` called directly on the same raw interferogram gives that
identical 0.5, which is the honest statement of what this operator adds. That
is why ``remove_bias`` defaults to ``True``; ``False`` is available for a scan
whose pedestal you have already removed some other way, and it is your
statement that you did.

signal:      1-D scan intensities (``(n,)``, n >= 3).
remove_bias: subtract the scan mean before the transform.

Returns a 1-D float64 envelope of the same length.

**Raises** ``ValueError``: a non-1-D, empty, too-short (< 3), non-finite,
complex or masked *signal*, a *signal* over :data:`MAX_SCAN_POINTS` elements
(checked before the float64 promotion), or a non-bool *remove_bias*.

## 詳しい使い方ガイド

- [coherence_scanning ファミリ ガイド](../guides/coherence_scanning.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [coherence_scanning](../../../../examples/coherence_scanning.py) — `py -3.11 examples/coherence_scanning.py`

## 型が繋がる次の op(`signal` を入力に取れる)

—

## 同カテゴリ(`envelope`)

—

---
*Provenance: interferometry.py — INTERFEROMETRY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
