---
op: lifetime_phasor
dim: photon
category: lifetime
in: counts
out: table
examples: [photon_timeresolved]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# lifetime_phasor — PHOTON `lifetime` op

- **データ種**: `counts` → `table`
- **呼び出し**: `import photoncount; photoncount.lifetime_phasor(decay, bin_ps=100.0, harmonic=1, background=0.0)` (または `opsphoton.get("lifetime_phasor")`)

## 使い方

Phasor (frequency-domain) representation of a decay — the fit-free view.

FLIM's standard fit-free tool. With ``omega = 2*pi*harmonic/window`` and bin
centres ``t_k``::

    g = sum(h_k * cos(omega*t_k)) / sum(h_k)
    s = sum(h_k * sin(omega*t_k)) / sum(h_k)

For a **single** exponential of lifetime ``tau`` under periodic excitation the
exact analytic phasor is ``g = 1/(1+(omega*tau)^2)``,
``s = omega*tau/(1+(omega*tau)^2)``, which traces the **universal
semicircle** ``(g - 1/2)^2 + s^2 = 1/4`` as ``tau`` runs from 0 to infinity.
A multi-exponential decay falls strictly *inside* that circle — which is why
``semicircle_residual`` is returned: it is the honest detector of the
single-exponential assumption that :func:`lifetime_fit` cannot give you.

Returns a dict: ``g`` · ``s`` · ``modulation`` ``m = sqrt(g^2+s^2)`` ·
``phase_rad`` · ``omega_per_ps`` · ``tau_phi_ps`` ``= tan(phase)/omega`` ·
``tau_m_ps`` ``= sqrt(1/m^2 - 1)/omega`` · ``semicircle_residual``
``= (g-1/2)^2 + s^2 - 1/4`` (0 on the circle, **negative inside**) ·
``total_counts``. ``tau_phi_ps`` is ``None`` — not a negative number — when
the phase is not in ``(0, pi/2)``, and ``tau_m_ps`` is ``None`` when the
modulation is 0 or >= 1; both mean "this is not a decaying single
exponential", which is information, not a failure.

Honest accuracy: the analytic formula is the *continuous* integral over one
excitation period, while this op sums over bins, so the two differ by the
midpoint-rule error. Measured on an exactly bin-integrated single exponential
(``tau = 2000 ps``, 256 bins x 100 ps, i.e. a 25.6 ns period): ``g`` is
0.805809 against the analytic 0.805830 (-2.0e-05), ``s`` is 0.395653 against
0.395561 (+9.2e-05), ``tau_phi_ps`` comes back as 2000.52 ps (+0.026%),
``tau_m_ps`` as 1999.74 ps (-0.013%) and ``semicircle_residual`` is
+6.07e-05. Quadrupling to 1024 bins over the same window divides the residual
by exactly 16.00 (to 3.79e-06) and the ``tau_phi`` error by 16 — the
``O(bin^2)`` midpoint behaviour, not a bias in the op.

And the reason ``semicircle_residual`` earns its place: the same window with
a **two**-component decay (equal photon budgets at 500 ps and 4000 ps) gives
a residual of -0.0924, i.e. 1500x further inside the circle than the
single-exponential round-off. :func:`lifetime_fit` would have returned one
confident number for that same histogram.

**Raises** ``ValueError``: negative, non-finite, non-1-D or all-zero *decay*,
a non-positive *bin_ps*, a *harmonic* outside ``[1, bins//2]`` (above
Nyquist the phasor is aliased and meaningless), a negative *background*, and
a background subtraction that removes every count.

## 詳しい使い方ガイド

- [photon_timeresolved ファミリ ガイド](../guides/photon_timeresolved.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [photon_timeresolved](../../../../examples/photon_timeresolved.py) — `py -3.11 examples/photon_timeresolved.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`lifetime`)

[lifetime_fit](lifetime_fit.md)

---
*Provenance: photoncount.py — PHOTON operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
