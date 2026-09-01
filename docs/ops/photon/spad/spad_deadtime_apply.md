---
op: spad_deadtime_apply
dim: photon
category: spad
in: countrate
out: countrate
examples: [photon_timeresolved]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# spad_deadtime_apply — PHOTON `spad` op

- **データ種**: `countrate` → `countrate`
- **呼び出し**: `import photoncount; photoncount.spad_deadtime_apply(rate_hz, dead_time_ns=50.0, paralyzable=False)` (または `opsphoton.get("spad_deadtime_apply")`)

## 使い方

Distort a true photon rate by the detector's dead time (counts lost).

After every detection a SPAD is blind for a recharge (dead) time ``tau``, so
the *measured* rate ``m`` is always below the *true* incident rate ``n``.
Two classical laws, and this op implements both:

  * **non-paralysable** (default) — an arriving photon during the dead time is
    simply lost: ``m = n / (1 + n*tau)``. Monotonic, saturating at ``1/tau``.
  * **paralysable** (``paralyzable=True``) — an arriving photon *restarts* the
    dead time: ``m = n * exp(-n*tau)``. This law **peaks** at ``n = 1/tau``
    (where ``m = 1/(e*tau)``) and then falls, so a bright scene can read
    *darker* than a dim one. That is why no inverse op exists for it (see
    :func:`spad_deadtime_correct`).

*rate_hz* is a 1-D array of true rates in counts per second; *dead_time_ns*
is the dead time in nanoseconds, defaulting to 50 — the middle of the
10-100 ns range a passively quenched SPAD occupies, and a placeholder to be
replaced by the datasheet value, never a measurement of your detector.
Returns the measured rates as a float64 1-D array of the same length.

Ground truth (pinned in the tests): at ``n = 1/tau`` the non-paralysable law
gives exactly ``n/2``; the paralysable law's maximum is exactly
``1/(e*tau)`` at ``n = 1/tau``; both reduce to ``m = n`` as ``n*tau -> 0``.

**Raises** ``ValueError``: negative, non-finite or non-1-D *rate_hz*, a
non-positive *dead_time_ns*, and a non-bool *paralyzable*.

## 詳しい使い方ガイド

- [photon_timeresolved ファミリ ガイド](../guides/photon_timeresolved.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [photon_timeresolved](../../../../examples/photon_timeresolved.py) — `py -3.11 examples/photon_timeresolved.py`

## 型が繋がる次の op(`countrate` を入力に取れる)

[spad_deadtime_correct](spad_deadtime_correct.md)

## 同カテゴリ(`spad`)

[spad_deadtime_correct](spad_deadtime_correct.md) · [tcspc_coates_correct](tcspc_coates_correct.md)

---
*Provenance: photoncount.py — PHOTON operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
