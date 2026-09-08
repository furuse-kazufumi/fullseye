---
op: match_funct_1d_trans
dim: oned
category: function
in: signal × signal
out: table
examples: [signal_funct1d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# match_funct_1d_trans — ONED `function` op

- **データ種**: `signal × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.match_funct_1d_trans(y1, y2)` (実装を直接呼ぶなら `import funct1d; funct1d.match_funct_1d_trans(y1, y2)`、台帳から引くなら `ops1d.get("match_funct_1d_trans")`)

## 使い方

Best integer translation between two functions by correlation
(HALCON ``match_funct_1d_trans``, translation only).

The returned ``shift`` uses the convention

    ``y1[i] ~= y2[i - shift]``

i.e. if *y2* is *y1* delayed (rolled right) by ``s`` samples, ``shift`` is
``-s``.

**Scoring convention.** ``score`` is the Pearson correlation coefficient
between *y1* and the shifted *y2* over the fixed reference window
``i = 0 .. len(y1) - 1`` — **the same window for every candidate lag**.
Where the shifted *y2* falls outside its own domain it is *end-held* at
``y2[0]`` / ``y2[-1]``, which is this module's out-of-domain convention
already (:func:`compose_funct_1d`, :func:`get_y_value_funct_1d`,
:func:`get_pair_funct_1d` all clamp). So ``score`` is in ``[-1, 1]``,
``1.0`` means the two agree up to a positive scale and offset, it is
comparable between lags *and* between calls, and it does not grow with
amplitude or with the length of the inputs. A lag that pushes *y2* entirely
off the window leaves a constant there and scores ``0.0``.

When several lags score within ``1e-6`` of the best, the **smallest**
``|shift|`` among them is returned: if the data cannot tell the translations
apart, this operator does not invent a large one.

**The bug this convention fixes.** Until 2026-09 the score was
``np.correlate(y1 - mean, y2 - mean, "full").max()`` — an unnormalised sum
over whatever happened to overlap at that lag. A shorter overlap simply
stops accumulating the mismatch, so edge lags win *without any exception,
NaN or warning*, and the caveat that used to sit here ("compare scores only
between candidates of the same length") does not save you: the inputs below
are the **same length**. A 400-sample record with Gaussian peaks (sigma 9)
at 60, 150, 245, 330 matched against a 400-sample template holding one such
peak at 60 — already aligned, so ``shift`` must be 0 — measured:

====== ======= ========= =========== ========
lag    overlap old (sum) old/overlap  new (r)
====== ======= ========= =========== ========
0          400 10.862705    0.027157 0.430110
90         310 10.989277    0.035449 0.430110
185        215 11.053477    0.051412 0.430110
270        130 11.240300    0.086464 0.430110
====== ======= ========= =========== ========

The old code returned ``shift 270, score 11.2403``; it now returns
``shift 0, score 0.430110``. The four lags are the four ways the single
template peak can sit on a record peak, and under the new convention they
are *exactly* as equivalent as they look — the four scores agree to
``2.804e-10``, the next-best lag (269) is ``0.428164``, and the tie is
broken by the smallest ``|shift|``. The score also stops flattering the
answer: ``0.43``, not ``11.24``, is what one template peak explains of a
four-peak record.

**The obvious cures were tried and measured, and they do not work** —
recorded so the next person does not spend the afternoon on them. Dividing
the overlap sum by the overlap length makes it *worse* (column 3 above: lag
270 now wins by 3.2x instead of 1.03x, and on a clean roll-by-7 the argmax
moves to lag -8). Renormalising to a coefficient over the overlap alone
(local means and local norms) rates lag 270 at ``0.999964`` against
``0.430110`` at lag 0 — the fit really is near perfect once you throw away
two thirds of the data — and it detonates on the degenerate end, scoring a
2-sample overlap at exactly ``1.0`` (on ``y1`` vs ``y1`` it picks lag -398
over lag 0). Multiplying that coefficient by the overlap fraction does fix
this case, but it biases every honest answer toward zero: on the damped sine
of ``test_match_funct_1d_trans_recovers_known_shift_and_is_scale_invariant``
it returns -6 for a true shift of -7. A fixed window and an explicit border
are what make the lags comparable; nothing weaker did.

**What the change costs.** The old truncation is not merely wrong at the
edges — it *shrinks the answer toward lag 0*, because the samples a
non-zero lag drops are the ones that would have contributed. That shrinkage
is free accuracy when the true shift happens to be 0 and a systematic error
everywhere else. Measured on 400 independent noise draws, an 81-sample
window of a sigma-9 Gaussian peak against an 81-sample template of the same
peak, noise sigma 0.20:

========== ============== ========= ============== =========
true shift old mean shift old exact new mean shift new exact
========== ============== ========= ============== =========
0                   -0.00     0.865          +0.01     0.547
-5                  -4.21     0.295          -4.99     0.547
+12                +11.22     0.307         +12.01     0.547
========== ============== ========= ============== =========

The new estimator is unbiased and equally accurate at every true shift; the
old one is biased by about 0.8 samples toward zero and its exact-hit rate
is a function of the answer it is looking for. Mean absolute error over the
three rows: 0.66 samples old, 0.48 new. The price is variance — with a true
shift of 0 and this much noise the new score really cannot separate lag 0
from lag +-1 (219 exact of 400 against 346), and it says so instead of
being rescued by a bias that points the right way by accident.

:func:`match_funct_1d_trans` still does not make an ill-posed match
well-posed. On a record of four random, well-separated peaks matched
against a template holding one of them, the four alignments are a genuine
tie and the answer is a convention, not a measurement: measured over 200
such records, the returned shift is 0 in 68.5% of them (old: 17.5%), the
rest being records where peak cross-talk breaks the tie for real.

Honest limitations: integer lag only (no sub-sample refinement), no x-scale
model, and no y-offset model beyond the mean subtraction that Pearson
implies. The window is *y1*'s domain, so the operator is asymmetric when the
lengths differ — it answers "where does *y2* sit inside *y1*", and
``match(y1, y2)["shift"]`` is not in general ``-match(y2, y1)["shift"]``.
A length-1 input has no variance and degenerates to ``shift 0, score 0.0``.
End-holding assumes the functions stay flat outside their domain; for a
signal with a strong trend or envelope, whiten first (match the
:func:`derivate_funct_1d` of both) — ``examples/signal_funct1d.py``
recovers a 25-sample delay exactly this way.

:param y1: 1-D function, at least 1 sample. Defines the reference window.
:param y2: 1-D function, at least 1 sample (lengths may differ).
:returns: dict ``{"shift": int, "score": float}``, ``score`` in ``[-1, 1]``.
:raises ValueError: non-1-D / NaN / Inf input, or empty input.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [signal_funct1d](../../../../examples/signal_funct1d.py) — `py -3.11 examples/signal_funct1d.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`function`)

[create_funct_1d_array](create_funct_1d_array.md) · [create_funct_1d_pairs](create_funct_1d_pairs.md) · [smooth_funct_1d_gauss](smooth_funct_1d_gauss.md) · [smooth_funct_1d_mean](smooth_funct_1d_mean.md) · [derivate_funct_1d](derivate_funct_1d.md) · [integrate_funct_1d](integrate_funct_1d.md) · [zero_crossings_funct_1d](zero_crossings_funct_1d.md) · [local_min_max_funct_1d](local_min_max_funct_1d.md)

---
*Provenance: funct1d.py — ONED operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
