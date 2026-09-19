# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Statistical process control — control charts, capability, multivariate T² (numpy + scipy only).

Machine vision earns its keep on a production line by *measuring*: a dimension, a
defect count, an intensity, a registration error. This library has a deep bench of
operators that produce such measurements (:mod:`measure1d` / :mod:`shapestat` /
:mod:`imgmetrics` / :mod:`blob`), but nothing that answers the question the line
actually asks of them — *is this process in control, and is it capable?* That is
statistical process control, and it is a small set of closed-form operators, each
with an exact identity to check it against rather than a fitted model.

Four operators, in the order a line uses them:

  * **chart** — :func:`spc_xbar_r`: the Shewhart Xbar-R chart. Given subgroups of
    ``n`` measurements each (``2 <= n <= 10``), the centre lines are the grand mean
    and the mean range, and the limits are ``Xbarbar +- A2*Rbar`` and
    ``(D3*Rbar, D4*Rbar)`` with the ISO 8258 / ASTM constants for that ``n``. Range
    estimates spread without assuming a model for it, which is why the classical
    chart uses it for small subgroups.
  * **change** — :func:`spc_cusum`: the tabular CUSUM for individual measurements.
    ``C+_i = max(0, C+_{i-1} + (x_i - target) - k)`` and the mirror ``C-``, alarming
    when either exceeds ``h``. It detects a sustained small shift far sooner than a
    Shewhart chart, at the cost of reacting slowly to a large spike — the explicit
    trade the reference model makes.
  * **capability** — :func:`spc_capability`: ``Cp = (USL-LSL)/(6 sigma)`` and
    ``Cpk = min(USL-mu, mu-LSL)/(3 sigma)``. Cp is what the spread *could* deliver
    if centred; Cpk is what the current centring *does* deliver. Reporting Cp alone
    hides an off-centre process, so both are returned and ``Cpk <= Cp`` always.
  * **multivariate** — :func:`spc_hotelling_t2`: when several measurements move
    together, charting them one at a time both misses joint drift and inflates the
    false-alarm rate. Hotelling's ``T^2 = (x-mu)' S^-1 (x-mu)`` charts them jointly
    against an F-distributed control limit, so correlated features are judged as one.

Measured — the closed-form identities the tests are built on
(``tests/test_spc.py``):

    quantity                                  analytic / measured
    Xbar-R constants, n=5                     A2=0.577, D3=0.000, D4=2.115 (ISO 8258)
    in-control subgroups                      no out-of-control points reported
    CUSUM on a constant-at-target series      C+ == C- == 0 for all i
    CUSUM slope after a step of size d        accumulates at rate (d - k) per sample
    Cpk of a centred process (mu at midpoint) Cpk == Cp exactly
    Cpk == Cp*(1 - 2k) for off-centre k       k = (mu-midpoint)/(USL-LSL)
    Hotelling T² of the mean row              0 (x == mu); UCL from F_{a,p,m-p}

Provenance — textbook and standards only (see ``docs/PROVENANCE.md``; the naming
rule forbids any product or company name):

  * W. A. Shewhart, *Economic Control of Quality of Manufactured Product*, 1931 —
    the control chart and 3-sigma limits.
  * ISO 8258:1991 / ASTM Manual 7 — the A2, D3, D4 subgroup constants.
  * E. S. Page, "Continuous inspection schemes", *Biometrika* 41:100, 1954 — CUSUM.
  * V. E. Kane, "Process capability indices", *J. Quality Technology* 18:41, 1986 —
    Cp and Cpk.
  * H. Hotelling, "Multivariate quality control", in *Techniques of Statistical
    Analysis*, 1947 — the T² statistic and its F-distributed limit.
"""
from __future__ import annotations

import numpy as np

#: The largest measurement series / matrix we coerce, before float64 promotion.
MAX_SPC_POINTS = 1 << 22

#: Shewhart Xbar-R constants (ISO 8258:1991 / ASTM Manual 7), keyed by subgroup
#: size n -> (A2, D3, D4). D3 is 0 for n <= 6 (the lower range limit is clamped to
#: zero there because the range cannot be negative and D3 would be < 0).
_XBAR_R_CONSTANTS: dict[int, tuple[float, float, float]] = {
    2:  (1.880, 0.000, 3.267),
    3:  (1.023, 0.000, 2.575),
    4:  (0.729, 0.000, 2.282),
    5:  (0.577, 0.000, 2.115),
    6:  (0.483, 0.000, 2.004),
    7:  (0.419, 0.076, 1.924),
    8:  (0.373, 0.136, 1.864),
    9:  (0.337, 0.184, 1.816),
    10: (0.308, 0.223, 1.777),
}


def _as_float_array(a, name: str, op: str) -> np.ndarray:
    """Coerce to float64 — after the size cap, refusing the silent-truncation traps
    (masked arrays, complex, non-finite, string/object/bool dtypes) the same way the
    other entity modules do, so a mislabelled input fails loudly, never plausibly."""
    if np.ma.is_masked(a):
        raise ValueError("%s: %s is a masked array with masked (invalid) entries — "
                         "fill or drop them explicitly" % (op, name))
    if isinstance(a, (str, bytes)):
        raise ValueError("%s: %s is a string — expected an array of numbers"
                         % (op, name))
    n = int(np.size(a))
    if n > MAX_SPC_POINTS:
        raise ValueError("%s: %s has %d elements, over the %d cap — refusing before "
                         "the float64 promotion" % (op, name, n, MAX_SPC_POINTS))
    if np.iscomplexobj(a):
        raise ValueError("%s: %s is complex — coercion to float64 would silently "
                         "discard the imaginary part; take .real explicitly if that "
                         "is what you mean" % (op, name))
    kind = getattr(getattr(a, "dtype", None), "kind", None)
    if kind is None and not isinstance(a, np.ndarray):
        kind = np.asarray(a).dtype.kind
    if kind in ("U", "S", "O", "V", "b"):
        raise ValueError("%s: %s has dtype '%s' — an unparsed string or object array "
                         "would parse into meaningless float64; convert it "
                         "explicitly" % (op, name, kind))
    arr = np.asarray(a, dtype=np.float64)
    if not np.isfinite(arr).all():
        raise ValueError("%s: %s has non-finite values (nan/inf) — control limits "
                         "computed from them would be meaningless" % (op, name))
    return arr


def _as_1d(a, name: str, op: str) -> np.ndarray:
    arr = _as_float_array(a, name, op)
    if arr.ndim != 1:
        raise ValueError("%s: %s must be 1-D, got a %d-D array of shape %r"
                         % (op, name, arr.ndim, arr.shape))
    if arr.size == 0:
        raise ValueError("%s: %s is empty" % (op, name))
    return arr


def spc_xbar_r(subgroups):
    """Shewhart Xbar-R control chart from subgroup measurements.

    ``subgroups`` is a 2-D array of shape ``(m, n)`` — ``m`` subgroups of ``n``
    measurements each, ``2 <= n <= 10`` (the range chart is only calibrated for
    small subgroups). For each subgroup ``j`` the plotted statistics are the mean
    ``Xbar_j`` and the range ``R_j = max - min``. The centre lines are the grand
    mean ``Xbarbar`` and the mean range ``Rbar``, and with the ISO 8258 constants
    ``(A2, D3, D4)`` for that ``n``::

        xbar_ucl = Xbarbar + A2*Rbar   xbar_lcl = Xbarbar - A2*Rbar
        r_ucl    = D4*Rbar             r_lcl    = D3*Rbar

    Returns a dict (a "table") with the per-subgroup ``xbar`` / ``r`` arrays, the
    six limits and three centre lines, the integer indices ``out_of_control`` of
    subgroups outside either chart, and ``in_control`` (True when that list is
    empty). The constants are fixed by ``n``: for ``n=5`` they are exactly
    ``A2=0.577, D3=0.000, D4=2.115`` (pinned in the tests).

    **Raises** ``ValueError``: a non-2-D / empty *subgroups*, a subgroup size
    outside ``[2, 10]``, or non-finite / mislabelled input.
    """
    op = "spc_xbar_r"
    arr = _as_float_array(subgroups, "subgroups", op)
    if arr.ndim != 2:
        raise ValueError("%s: subgroups must be 2-D (m subgroups x n measurements), "
                         "got a %d-D array of shape %r" % (op, arr.ndim, arr.shape))
    m, n = arr.shape
    if m == 0:
        raise ValueError("%s: no subgroups" % op)
    if not (2 <= n <= 10):
        raise ValueError("%s: subgroup size n must be 2..10 (the range chart is only "
                         "calibrated there), got n=%d" % (op, n))
    a2, d3, d4 = _XBAR_R_CONSTANTS[n]
    xbar = arr.mean(axis=1)
    rng = arr.max(axis=1) - arr.min(axis=1)
    xbarbar = float(xbar.mean())
    rbar = float(rng.mean())
    xbar_ucl = xbarbar + a2 * rbar
    xbar_lcl = xbarbar - a2 * rbar
    r_ucl = d4 * rbar
    r_lcl = d3 * rbar
    ooc = np.nonzero((xbar > xbar_ucl) | (xbar < xbar_lcl)
                     | (rng > r_ucl) | (rng < r_lcl))[0]
    return {"xbar": xbar, "r": rng,
            "xbar_cl": xbarbar, "xbar_ucl": xbar_ucl, "xbar_lcl": xbar_lcl,
            "r_cl": rbar, "r_ucl": r_ucl, "r_lcl": r_lcl,
            "n": n, "a2": a2, "d3": d3, "d4": d4,
            "out_of_control": ooc.tolist(), "in_control": bool(ooc.size == 0)}


def spc_cusum(signal, target, k=0.5, h=5.0):
    """Tabular CUSUM chart for individual measurements.

    ``signal`` is a 1-D series of individual measurements. With a reference value
    ``target``, a slack ``k`` (in the same units as the measurements — commonly half
    the shift you want to catch) and a decision interval ``h``::

        C+_i = max(0, C+_{i-1} + (x_i - target) - k)
        C-_i = max(0, C-_{i-1} - (x_i - target) - k)

    starting from ``C+_0 = C-_0 = 0``, alarming at index ``i`` when ``C+_i > h`` or
    ``C-_i > h``. Returns a dict with the ``c_plus`` / ``c_minus`` arrays, the
    integer ``alarms`` indices, the first alarm index (or ``-1``), and the echoed
    ``target`` / ``k`` / ``h``.

    Ground truth (pinned in the tests): a series constant at ``target`` keeps
    ``C+ == C- == 0``; after a sustained upward step of size ``d > k`` the upper sum
    grows at exactly ``d - k`` per sample.

    **Raises** ``ValueError``: a non-1-D / empty *signal*, a non-finite
    *target* / *k* / *h*, a negative *k*, or a non-positive *h*.
    """
    op = "spc_cusum"
    x = _as_1d(signal, "signal", op)
    for nm, v in (("target", target), ("k", k), ("h", h)):
        if not np.isfinite(v):
            raise ValueError("%s: %s must be finite, got %r" % (op, nm, v))
    if k < 0:
        raise ValueError("%s: k (slack) must be >= 0, got %r" % (op, k))
    if h <= 0:
        raise ValueError("%s: h (decision interval) must be > 0, got %r" % (op, h))
    dev = x - float(target)
    cp = np.empty(x.size, dtype=np.float64)
    cm = np.empty(x.size, dtype=np.float64)
    p = m = 0.0
    for i in range(x.size):
        p = max(0.0, p + dev[i] - k)
        m = max(0.0, m - dev[i] - k)
        cp[i] = p
        cm[i] = m
    alarms = np.nonzero((cp > h) | (cm > h))[0]
    first = int(alarms[0]) if alarms.size else -1
    return {"c_plus": cp, "c_minus": cm, "alarms": alarms.tolist(),
            "first_alarm": first, "target": float(target), "k": float(k),
            "h": float(h), "in_control": bool(alarms.size == 0)}


def spc_ewma(signal, target, lam=0.2, L=3.0, sigma=None):
    """EWMA control chart for individual measurements (Roberts 1959).

    ``signal`` is a 1-D series of individual measurements. With a reference value
    ``target`` (the in-control mean), a smoothing constant ``lam`` in ``(0, 1]`` and
    a control-limit width ``L`` (in sigmas), the exponentially weighted moving
    average and its time-varying limits are::

        z_i  = lam * x_i + (1 - lam) * z_{i-1},          z_0 = target
        var_i = sigma^2 * (lam / (2 - lam)) * (1 - (1 - lam) ** (2 (i + 1)))
        UCL_i / LCL_i = target +/- L * sqrt(var_i)

    ``sigma`` is the process standard deviation; if ``None`` it is estimated from the
    series as the sample std (``ddof=1``). The limits widen from the first sample to
    the asymptote ``target +/- L * sigma * sqrt(lam / (2 - lam))``. EWMA, like CUSUM,
    catches small sustained shifts that a single-point Shewhart chart misses; ``lam``
    trades memory (small = long memory, sensitive to small shifts) against speed.

    Returns a dict with the ``z`` / ``ucl`` / ``lcl`` arrays, the integer ``alarms``
    indices (``z_i`` outside its limits), the first alarm index (or ``-1``), the
    asymptotic ``ucl_inf`` / ``lcl_inf``, and the echoed ``target`` / ``lam`` / ``L``
    / ``sigma`` / ``in_control``.

    Ground truth (pinned in the tests): a series constant at ``target`` keeps
    ``z == target`` with no alarm; ``z`` is exactly the recursion above; ``ucl``
    increases monotonically toward ``ucl_inf``; with ``lam = 1`` the chart reduces to
    a Shewhart individuals chart (``z == x``, limits constant at ``target +/- L
    sigma``).

    **Raises** ``ValueError``: a non-1-D / empty *signal*, a non-finite
    *target* / *lam* / *L*, ``lam`` outside ``(0, 1]``, a non-positive *L*, a
    non-finite or non-positive *sigma*, or (when estimating) a constant series whose
    sample std is zero.
    """
    op = "spc_ewma"
    x = _as_1d(signal, "signal", op)
    for nm, v in (("target", target), ("lam", lam), ("L", L)):
        if not np.isfinite(v):
            raise ValueError("%s: %s must be finite, got %r" % (op, nm, v))
    if not (0.0 < lam <= 1.0):
        raise ValueError("%s: lam (smoothing) must be in (0, 1], got %r" % (op, lam))
    if L <= 0:
        raise ValueError("%s: L (limit width) must be > 0, got %r" % (op, L))
    if sigma is None:
        if x.size < 2:
            raise ValueError("%s: need at least 2 measurements to estimate sigma, got "
                             "%d (or pass sigma explicitly)" % (op, x.size))
        sd = float(x.std(ddof=1))
        if sd <= 0:
            raise ValueError("%s: estimated sigma is %r — a constant series has no "
                             "spread; pass sigma explicitly" % (op, sd))
    else:
        if not np.isfinite(sigma):
            raise ValueError("%s: sigma must be finite, got %r" % (op, sigma))
        sd = float(sigma)
        if sd <= 0:
            raise ValueError("%s: sigma must be > 0, got %r" % (op, sd))
    tgt = float(target)
    z = np.empty(x.size, dtype=np.float64)
    prev = tgt
    for i in range(x.size):
        prev = lam * x[i] + (1.0 - lam) * prev
        z[i] = prev
    i1 = np.arange(1, x.size + 1, dtype=np.float64)
    var = sd * sd * (lam / (2.0 - lam)) * (1.0 - (1.0 - lam) ** (2.0 * i1))
    half = L * np.sqrt(var)
    ucl = tgt + half
    lcl = tgt - half
    alarms = np.nonzero((z > ucl) | (z < lcl))[0]
    first = int(alarms[0]) if alarms.size else -1
    inf = L * sd * np.sqrt(lam / (2.0 - lam))
    return {"z": z, "ucl": ucl, "lcl": lcl, "alarms": alarms.tolist(),
            "first_alarm": first, "target": tgt, "lam": float(lam), "L": float(L),
            "sigma": sd, "ucl_inf": tgt + inf, "lcl_inf": tgt - inf,
            "in_control": bool(alarms.size == 0)}


def spc_capability(signal, lsl, usl, sigma=None):
    """Process capability indices Cp and Cpk from measurements and spec limits.

    ``signal`` is a 1-D series of individual measurements; ``lsl`` / ``usl`` are the
    lower / upper specification limits (``lsl < usl``). With the sample mean ``mu``
    and standard deviation ``sigma`` (sample std, ``ddof=1``, unless one is passed
    in explicitly)::

        Cp  = (USL - LSL) / (6 sigma)
        Cpk = min(USL - mu, mu - LSL) / (3 sigma)

    Returns a dict with ``mean`` / ``std`` / ``cp`` / ``cpk`` and the echoed spec
    limits and midpoint. ``Cpk <= Cp`` always, with equality exactly when the
    process is centred (``mu`` at the spec midpoint) — pinned in the tests.

    **Raises** ``ValueError``: a non-1-D / empty *signal*, fewer than two points
    (no spread to estimate), ``lsl >= usl``, non-finite limits, or a non-positive
    standard deviation (a constant series has no capability to report).
    """
    op = "spc_capability"
    x = _as_1d(signal, "signal", op)
    if x.size < 2:
        raise ValueError("%s: need at least 2 measurements to estimate spread, got "
                         "%d" % (op, x.size))
    for nm, v in (("lsl", lsl), ("usl", usl)):
        if not np.isfinite(v):
            raise ValueError("%s: %s must be finite, got %r" % (op, nm, v))
    if not (lsl < usl):
        raise ValueError("%s: need lsl < usl, got lsl=%r usl=%r" % (op, lsl, usl))
    mu = float(x.mean())
    if sigma is None:
        sd = float(x.std(ddof=1))
    else:
        if not np.isfinite(sigma):
            raise ValueError("%s: sigma must be finite, got %r" % (op, sigma))
        sd = float(sigma)
    if sd <= 0:
        raise ValueError("%s: standard deviation is %r — a constant process has no "
                         "capability to report (Cp/Cpk would divide by zero)"
                         % (op, sd))
    cp = (usl - lsl) / (6.0 * sd)
    cpk = min(usl - mu, mu - lsl) / (3.0 * sd)
    return {"mean": mu, "std": sd, "cp": cp, "cpk": cpk,
            "lsl": float(lsl), "usl": float(usl),
            "midpoint": 0.5 * (float(lsl) + float(usl))}


def spc_hotelling_t2(data, alpha=0.0027, mean=None, cov=None):
    """Multivariate SPC by Hotelling's T² with an F-distributed control limit.

    ``data`` is a 2-D array of shape ``(m, p)`` — ``m`` observations of ``p``
    correlated features. With the sample mean vector ``mu`` and covariance ``S``
    (unless passed in explicitly), each row's statistic is::

        T^2_i = (x_i - mu)' S^-1 (x_i - mu)

    charted against the phase-II control limit::

        UCL = p (m+1)(m-1) / (m (m-p)) * F_{alpha, p, m-p}

    at false-alarm rate ``alpha`` (default 0.0027, the 3-sigma-equivalent). Returns
    a dict with the per-row ``t2`` array, the ``ucl``, the integer indices
    ``out_of_control``, and ``in_control``. The mean row (``x == mu``) has
    ``T^2 == 0`` (pinned in the tests).

    **Raises** ``ValueError``: a non-2-D / empty *data*, fewer observations than
    features plus one (covariance not invertible), ``alpha`` outside ``(0, 1)``, a
    singular covariance, or non-finite / mislabelled input.
    """
    op = "spc_hotelling_t2"
    arr = _as_float_array(data, "data", op)
    if arr.ndim != 2:
        raise ValueError("%s: data must be 2-D (m observations x p features), got a "
                         "%d-D array of shape %r" % (op, arr.ndim, arr.shape))
    m, p = arr.shape
    if not (0.0 < alpha < 1.0):
        raise ValueError("%s: alpha must be in (0, 1), got %r" % (op, alpha))
    if mean is None or cov is None:
        if m < p + 1:
            raise ValueError("%s: need at least p+1=%d observations to estimate an "
                             "invertible covariance, got m=%d" % (op, p + 1, m))
    mu = arr.mean(axis=0) if mean is None else _as_1d(mean, "mean", op)
    if mu.size != p:
        raise ValueError("%s: mean has %d entries but data has p=%d features"
                         % (op, mu.size, p))
    if cov is None:
        s = np.cov(arr, rowvar=False, ddof=1)
        s = np.atleast_2d(s)
    else:
        s = _as_float_array(cov, "cov", op)
        s = np.atleast_2d(s)
        if s.shape != (p, p):
            raise ValueError("%s: cov must be (p, p)=(%d, %d), got %r"
                             % (op, p, p, s.shape))
    try:
        s_inv = np.linalg.inv(s)
    except np.linalg.LinAlgError as exc:
        raise ValueError("%s: covariance is singular (%s) — features are collinear, "
                         "so T² is undefined; drop a redundant feature" % (op, exc))
    d = arr - mu
    t2 = np.einsum("ij,jk,ik->i", d, s_inv, d)
    from scipy.stats import f as _f
    fcrit = float(_f.ppf(1.0 - alpha, p, m - p)) if m > p else float("inf")
    ucl = p * (m + 1.0) * (m - 1.0) / (m * (m - p)) * fcrit if m > p else float("inf")
    ooc = np.nonzero(t2 > ucl)[0]
    return {"t2": t2, "ucl": ucl, "p": p, "m": m, "alpha": float(alpha),
            "out_of_control": ooc.tolist(), "in_control": bool(ooc.size == 0)}


#: The op family, mirrored by :mod:`opsspc` (name -> callable).
SPC = {
    "spc_xbar_r": spc_xbar_r,
    "spc_cusum": spc_cusum,
    "spc_capability": spc_capability,
    "spc_hotelling_t2": spc_hotelling_t2,
}


if __name__ == "__main__":                                # pragma: no cover
    rng = np.random.default_rng(0)
    sg = rng.normal(10.0, 1.0, size=(20, 5))
    print("spc: %d ops" % len(SPC))
    print("  xbar_r in_control:", spc_xbar_r(sg)["in_control"])
    print("  cusum first_alarm:", spc_cusum(rng.normal(0, 1, 50), target=0.0)["first_alarm"])
    print("  cpk:", round(spc_capability(rng.normal(10, 1, 200), 6.0, 14.0)["cpk"], 3))
