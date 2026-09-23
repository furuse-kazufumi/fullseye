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


# =========================================================================== #
# 測定システム解析(MSA)と測定の不確かさ(GUM)
#
# ★管理図と工程能力は「工程のばらつき」を見るが、その数字は**測定のばらつきを
#   含んだまま**である。ゲージ R&R は総変動を「部品差」と「測る行為の差」に分け、
#   後者が前者を食っていないかを見る —— 工程能力の前に来るべき検査で、ここが
#   抜けていると「工程が暴れている」と読んだものが実は測定器だったという取り違えが
#   起きる。GUM は同じ問いを 1 回の測定について立て、成分ごとの不確かさを
#   合成する。どちらも閉形式で、照合できる恒等式を持つ。
# =========================================================================== #


def _scipy_stats():
    """scipy.stats を**関数内で**取る(spc.py の既存の作法に合わせる)。

    ★module 先頭で import すると、scipy を持たない環境で ``import spc`` 自体が
    落ちる —— この repo は「numpy だけでも動く」を保っているので、分布の分位点が
    要る op だけがその場で取りに行く。
    """
    from scipy import stats as _st             # noqa: PLC0415 — 遅延 import は意図
    return _st


# --------------------------------------------------------------------------- #
# 入力の検証(表 = 列名 -> 1-D 配列。fail-closed)
# --------------------------------------------------------------------------- #
def _cols(table, op: str, needed: tuple[str, ...]) -> dict[str, np.ndarray]:
    """表から必要な列だけを取り出す。長さが揃っていなければ拒む。"""
    if not isinstance(table, dict):
        raise ValueError(
            "%s: expected a table (a dict of column name -> 1-D array), got %s"
            % (op, type(table).__name__))
    missing = [c for c in needed if c not in table]
    if missing:
        raise ValueError("%s: the table lacks column(s) %s — it has %s"
                         % (op, missing, sorted(table)))
    out, n = {}, None
    for c in needed:
        a = np.asarray(table[c]).reshape(-1)
        if n is None:
            n = a.shape[0]
        elif a.shape[0] != n:
            raise ValueError("%s: column %r has %d rows but %r has %d — "
                             "the columns of one table must line up"
                             % (op, c, a.shape[0], needed[0], n))
        out[c] = a
    if not n:
        raise ValueError("%s: the table is empty" % op)
    return out


def _numeric(a: np.ndarray, col: str, op: str) -> np.ndarray:
    v = np.asarray(a, dtype=np.float64)
    if not np.isfinite(v).all():
        raise ValueError("%s: column %r must be finite" % (op, col))
    return v


def _balanced_cells(part, oper, value, op):
    """(部品 x 測定者)の升目に値を並べる。**釣り合っていない設計は拒む**。

    ★分散分析法の分散成分は釣り合った設計の期待平均平方から導く。欠測のある表を
    黙って受けると、式は動くが**別の量**を返す(重み付けの違いが分散成分に化ける)。
    規格(AIAG MSA / ISO 5725)も釣り合い型を前提にしているので、ここは拒む。
    """
    parts = np.unique(part)
    opers = np.unique(oper)
    p, o = len(parts), len(opers)
    if p < 2:
        raise ValueError("%s: need at least 2 parts, got %d — with one part the "
                         "part-to-part variance is not estimable" % (op, p))
    if o < 1:
        raise ValueError("%s: need at least 1 operator" % op)
    counts = np.zeros((p, o), dtype=np.int64)
    idx_p = {v: i for i, v in enumerate(parts)}
    idx_o = {v: j for j, v in enumerate(opers)}
    for a, b in zip(part, oper):
        counts[idx_p[a], idx_o[b]] += 1
    r = int(counts.flat[0])
    if r < 2:
        raise ValueError("%s: need at least 2 replicates per part x operator cell, "
                         "got %d — repeatability is the within-cell spread, so one "
                         "measurement per cell leaves nothing to estimate it with"
                         % (op, r))
    if not (counts == r).all():
        raise ValueError(
            "%s: the design is unbalanced (cell counts %d..%d, expected %d "
            "everywhere). The ANOVA variance components come from the expected mean "
            "squares of a balanced crossed design; an unbalanced table would return a "
            "different quantity rather than fail, so it is refused."
            % (op, int(counts.min()), int(counts.max()), r))
    cells = np.empty((p, o, r), dtype=np.float64)
    fill = np.zeros((p, o), dtype=np.int64)
    for a, b, v in zip(part, oper, value):
        i, j = idx_p[a], idx_o[b]
        cells[i, j, fill[i, j]] = v
        fill[i, j] += 1
    return parts, opers, cells


def _crossed_anova(cells: np.ndarray):
    """交差 2 元配置(繰り返しあり)の平方和。**恒等式が門**になる形で返す。

    ``SS_total == SS_part + SS_oper + SS_inter + SS_error`` は代数的な恒等式なので
    丸め誤差の範囲で必ず成り立つ —— 分散成分の出し方とは独立に検算できる。
    """
    p, o, r = cells.shape
    grand = cells.mean()
    m_p = cells.mean(axis=(1, 2))                  # 部品ごと
    m_o = cells.mean(axis=(0, 2))                  # 測定者ごと
    m_po = cells.mean(axis=2)                      # 升目ごと

    ss_part = o * r * float(((m_p - grand) ** 2).sum())
    ss_oper = p * r * float(((m_o - grand) ** 2).sum())
    inter = m_po - m_p[:, None] - m_o[None, :] + grand
    ss_inter = r * float((inter ** 2).sum())
    ss_err = float(((cells - m_po[:, :, None]) ** 2).sum())
    ss_tot = float(((cells - grand) ** 2).sum())

    df = {"part": p - 1, "operator": o - 1, "interaction": (p - 1) * (o - 1),
          "repeatability": p * o * (r - 1), "total": p * o * r - 1}
    ss = {"part": ss_part, "operator": ss_oper, "interaction": ss_inter,
          "repeatability": ss_err, "total": ss_tot}
    return ss, df, (p, o, r), grand


# --------------------------------------------------------------------------- #
# MSA
# --------------------------------------------------------------------------- #
def msa_anova_table(table, part="part", operator="operator", value="value"):
    """交差 2 元配置(部品 x 測定者 x 繰り返し)の分散分析表(``table``)。

    *table* は列 *part* / *operator* / *value* を持つ表。設計は**釣り合っている**
    こと(升目ごとの繰り返し数が同じ)——釣り合っていなければ拒む。

    返りは source / ss / df / ms / f / p の 6 列。``f`` と ``p`` は測定者と交互作用を
    交互作用平均平方で、交互作用を誤差平均平方で検定した値(規格の慣行)。

    ★門にできる厳密な恒等式: ``ss_total == ss_part + ss_oper + ss_inter + ss_err``。
    これは代数的な分解なので、分散成分をどう出そうと必ず成り立つ —— 片方が壊れれば
    一致しない。自由度も ``df_total == 和`` で閉じる。
    """
    op = "msa_anova_table"
    c = _cols(table, op, (part, operator, value))
    v = _numeric(c[value], value, op)
    parts, opers, cells = _balanced_cells(c[part], c[operator], v, op)
    ss, df, (p, o, r), _ = _crossed_anova(cells)

    ms = {k: (ss[k] / df[k] if df[k] > 0 else float("nan"))
          for k in ("part", "operator", "interaction", "repeatability")}
    # F 比。交互作用が自由度 0(測定者 1 人)のときは検定できない → nan を返す。
    f_part = ms["part"] / ms["interaction"] if df["interaction"] > 0 else float("nan")
    f_oper = ms["operator"] / ms["interaction"] if df["interaction"] > 0 else float("nan")
    f_int = ms["interaction"] / ms["repeatability"] if df["interaction"] > 0 else float("nan")

    def _p(fv, d1, d2):
        if not np.isfinite(fv) or d1 <= 0 or d2 <= 0:
            return float("nan")
        return float(_scipy_stats().f.sf(fv, d1, d2))

    src = ["part", "operator", "interaction", "repeatability", "total"]
    return {
        "source": np.array(src, dtype=object),
        "ss": np.array([ss[s] for s in src], dtype=np.float64),
        "df": np.array([df[s] for s in src], dtype=np.int64),
        "ms": np.array([ms.get(s, float("nan")) for s in src[:-1]] + [float("nan")]),
        "f": np.array([f_part, f_oper, f_int, float("nan"), float("nan")]),
        "p": np.array([_p(f_part, df["part"], df["interaction"]),
                       _p(f_oper, df["operator"], df["interaction"]),
                       _p(f_int, df["interaction"], df["repeatability"]),
                       float("nan"), float("nan")]),
        "n_parts": np.array([p], dtype=np.int64),
        "n_operators": np.array([o], dtype=np.int64),
        "n_replicates": np.array([r], dtype=np.int64),
    }


def msa_gauge_rr(table, part="part", operator="operator", value="value",
                 tolerance=None, pool_interaction="auto", pool_alpha=0.25):
    """分散分析法によるゲージ R&R(``table``)。

    繰り返し性 EV(同じ人が同じ物を測り直したときの散らばり)、再現性 AV(人が
    変わったときの散らばり。交互作用を含む)、その合成 GRR、部品間 PV、総変動 TV、
    ``%GRR = 100 GRR/TV``、区別できる階級数 ``ndc = 1.41 PV/GRR``。

    *tolerance* を渡すと公差に対する比 ``%tolerance = 100 GRR/tolerance`` も返す。

    ★分散成分は**釣り合った交差計画の期待平均平方**から出す:

        var_repeat = MS_err
        var_inter  = (MS_inter - MS_err) / r
        var_oper   = (MS_oper - MS_inter) / (p r)
        var_part   = (MS_part - MS_inter) / (o r)

    ★★**負の分散成分は 0 に丸めるが、丸めたことを隠さない**(``clamped`` 列)。
    期待平均平方の差は推定量なので、真の成分が 0 に近いと負になりうる。黙って 0 に
    すると「測定者差は無い」と読めてしまうが、正しくは「**推定できなかった**」。
    しかもこれは稀な端ではない —— 部品 60 x 測定者 4 x 繰り返し 5 で測定者差を
    **厳密に 0** にした合成データを種 40 本で回すと、**31 本**で再現性成分が負に出る
    (実測 2026-09-23)。丸めを申告しない実装は、この 31 本すべてで「差が無い」と
    言い切ってしまう。

    ★推定量の揺れも隠さない。同じ 60x4x5 で真値 0.4 の繰り返し性は種 40 本で
    平均 0.39710・標準偏差 0.00788 に出る —— 理論の ``sigma/sqrt(2 df)``
    (df = 960 で 0.00913)と同じ桁で、**1 本の種を 1 % の精度で信じてはいけない**。
    再現性はもっと悪く、測定者 4 人(自由度 3)からの推定なので真値 0.5 に対して
    標準偏差 0.159 —— 桁が合えば上等という量である。

    ★★**交互作用を残すか、誤差にプールするかで答えが変わる**。規格の手順は
    「交互作用の F 検定が有意でなければ交互作用項を落として再計算する」で、
    *pool_interaction* がその選択:

      * ``"auto"``(既定)—— 交互作用の p 値が *pool_alpha*(既定 0.25)を**超えたら**
        プールする。

    ★★**0.25 は規格が明記した数ではない**。参考マニュアル本文が言うのは
    「交互作用を見落とす危険を下げるため**高い有意水準を選べ**」という定性的な指示
    だけで、数値は書かれていない。0.25 はソフトウェア側の慣行の多数派で、
    別の実装は 0.05 を既定にしている。α を**大きく**すると `p > alpha` が成りにくく
    なる = **交互作用を残しやすい**ので、0.25 は本文の方針に忠実な(保守的な)側。
    一方で規格の worked example の表は脚注に「α = 0.05 で判定」と書いてあるので、
    **その表を再現すると名乗る検査は `pool_alpha=0.05` を明示して通すべき**である
    (既定値の話と、公表例題の再現条件の話は別)。この例題では F = 0.434 が
    どちらの α でも非有意なので結果は変わらないが、境界付近のデータでは既定の違いが
    EV / AV を数 % 動かす —— 実測でモデル切替は EV を 7.3 % 動かした。
      * ``False`` —— 常に交互作用を残す。
      * ``True`` —— 常にプールする。

    返りの ``interaction_pooled`` / ``interaction_p`` / ``pool_alpha`` に**どちらを
    使ったかを必ず載せる**。黙って切り替えると、同じ道具が同じ工程について別の数字を
    返し、その理由が出力のどこにも残らない。

    ★実測(規格の例題、10 部品 x 3 測定者 x 3 回の 90 点): 交互作用を残すと
    EV = 0.214435、プールすると EV = 0.199933 —— **7.3 % 違う**。選択は p 値の
    閾値で決まるので、データがわずかに動けばモデルが飛ぶ。この例題では
    ``F = 0.4337 / p = 0.9741`` と交互作用がまったく効いていないため、規格は
    プールした側を公表値にしている(その値をこの実装は 3e-7 で再現する)。

    ★門にできる厳密な関係: ``TV^2 == GRR^2 + PV^2`` と ``GRR^2 == EV^2 + AV^2``
    (定義そのもの)、寄与率の合計 100 %、そして**測定者が 1 人のときの EV は
    升目ごとの標本分散の平均に厳密に一致する**(numpy が真値になる)。
    """
    op = "msa_gauge_rr"
    c = _cols(table, op, (part, operator, value))
    v = _numeric(c[value], value, op)
    parts, opers, cells = _balanced_cells(c[part], c[operator], v, op)
    ss, df, (p, o, r), _ = _crossed_anova(cells)

    if pool_interaction not in (True, False, "auto"):
        raise ValueError("%s: pool_interaction must be True, False or \"auto\", got %r"
                         % (op, pool_interaction))
    if not (0.0 < float(pool_alpha) < 1.0):
        raise ValueError("%s: pool_alpha must lie strictly between 0 and 1, got %r"
                         % (op, pool_alpha))

    ms_err = ss["repeatability"] / df["repeatability"]
    ms_int = ss["interaction"] / df["interaction"] if df["interaction"] > 0 else ms_err
    ms_opr = ss["operator"] / df["operator"] if df["operator"] > 0 else 0.0
    ms_prt = ss["part"] / df["part"]

    # 交互作用の F 検定(誤差平均平方で検定する)。自由度が無ければ検定できない。
    p_int = float("nan")
    if df["interaction"] > 0 and df["repeatability"] > 0 and ms_err > 0:
        p_int = float(_scipy_stats().f.sf(ms_int / ms_err, df["interaction"],
                                          df["repeatability"]))
    if pool_interaction == "auto":
        pooled = bool(df["interaction"] > 0 and np.isfinite(p_int)
                      and p_int > float(pool_alpha))
    else:
        pooled = bool(pool_interaction) and df["interaction"] > 0

    if pooled:
        # 交互作用の平方和と自由度を誤差へ畳み込み、交互作用項を 0 にする。
        ms_err = ((ss["interaction"] + ss["repeatability"])
                  / (df["interaction"] + df["repeatability"]))
        ms_int = ms_err

    raw = {
        "repeatability": ms_err,
        "interaction": 0.0 if pooled else ((ms_int - ms_err) / r if df["interaction"] > 0 else 0.0),
        "operator": (ms_opr - ms_int) / (p * r) if df["operator"] > 0 else 0.0,
        "part": (ms_prt - ms_int) / (o * r),
    }
    clamped = {k: bool(val < 0.0) for k, val in raw.items()}
    var = {k: max(float(val), 0.0) for k, val in raw.items()}

    ev = float(np.sqrt(var["repeatability"]))
    av = float(np.sqrt(var["operator"] + var["interaction"]))
    grr = float(np.hypot(ev, av))
    pv = float(np.sqrt(var["part"]))
    tv = float(np.hypot(grr, pv))

    pct_grr = 100.0 * grr / tv if tv > 0 else float("nan")
    ndc = 1.41 * pv / grr if grr > 0 else float("inf")

    out = {
        "component": np.array(["repeatability", "reproducibility", "gauge_rr",
                               "part", "total"], dtype=object),
        "variance": np.array([ev ** 2, av ** 2, grr ** 2, pv ** 2, tv ** 2]),
        "sigma": np.array([ev, av, grr, pv, tv]),
        "pct_study": np.array([100.0 * x / tv if tv > 0 else float("nan")
                               for x in (ev, av, grr, pv, tv)]),
        "pct_contribution": np.array([100.0 * x ** 2 / tv ** 2 if tv > 0 else float("nan")
                                      for x in (ev, av, grr, pv, tv)]),
        "clamped": np.array([clamped["repeatability"],
                             clamped["operator"] or clamped["interaction"],
                             False, clamped["part"], False]),
        "pct_grr": np.array([pct_grr]),
        "ndc": np.array([ndc]),
        # ★どのモデルで出した数字かを必ず載せる(黙って切り替えない)
        "interaction_pooled": np.array([pooled]),
        "interaction_p": np.array([p_int]),
        "pool_alpha": np.array([float(pool_alpha)]),
        "n_parts": np.array([p], dtype=np.int64),
        "n_operators": np.array([o], dtype=np.int64),
        "n_replicates": np.array([r], dtype=np.int64),
    }
    if tolerance is not None:
        tol = float(tolerance)
        if not np.isfinite(tol) or tol <= 0:
            raise ValueError("%s: tolerance must be a positive finite width, got %r"
                             % (op, tolerance))
        out["pct_tolerance"] = np.array([100.0 * grr / tol])
    return out


def msa_bias_linearity(table, reference="reference", measured="measured"):
    """基準値に対する偏りと、その基準値依存(直線性)(``table``)。

    偏り ``bias = measured - reference`` を基準値に回帰する
    (``bias = intercept + slope * reference``)。傾きが 0 でなければ、測定系は
    測定範囲の**場所によって違う量だけずれている** = 直線性の問題。

    返りは基準値ごとの平均偏り(``ref`` / ``bias_mean`` / ``n``)と、回帰の
    ``intercept`` / ``slope`` / それぞれの標準誤差・t 値・p 値、全体平均偏り。

    ★門にできる厳密な性質: 雑音の無い ``bias = a + b*ref`` を渡すと最小二乗は
    a と b を**厳密に**返す(残差 0)。そのとき標準誤差は 0 なので t は ``inf`` /
    p は 0 —— これは欠陥ではなく完全適合の正しい報告なので、そのまま返す。
    """
    op = "msa_bias_linearity"
    c = _cols(table, op, (reference, measured))
    ref = _numeric(c[reference], reference, op)
    mea = _numeric(c[measured], measured, op)
    if ref.size < 3:
        raise ValueError("%s: need at least 3 measurements to fit a line, got %d"
                         % (op, ref.size))
    if np.ptp(ref) <= 0:
        raise ValueError("%s: every reference value is %g — with a single reference "
                         "the slope is not estimable, so this is a bias study, not a "
                         "linearity study" % (op, float(ref[0])))

    bias = mea - ref
    X = np.column_stack([np.ones_like(ref), ref])
    coef, *_ = np.linalg.lstsq(X, bias, rcond=None)
    resid = bias - X @ coef
    dof = ref.size - 2
    sse = float((resid ** 2).sum())
    mse = sse / dof
    xtx_inv = np.linalg.inv(X.T @ X)
    se = np.sqrt(np.maximum(np.diag(xtx_inv) * mse, 0.0))
    with np.errstate(divide="ignore", invalid="ignore"):
        tval = np.where(se > 0, coef / np.where(se > 0, se, 1.0),
                        np.where(coef == 0.0, 0.0, np.inf * np.sign(coef)))
    _st = _scipy_stats()
    pval = np.array([float(2.0 * _st.t.sf(abs(t), dof)) if np.isfinite(t)
                     else (0.0 if t != 0.0 else 1.0) for t in tval])

    refs = np.unique(ref)
    means = np.array([float(bias[ref == rv].mean()) for rv in refs])
    ns = np.array([int((ref == rv).sum()) for rv in refs], dtype=np.int64)
    return {
        "ref": refs,
        "bias_mean": means,
        "n": ns,
        "term": np.array(["intercept", "slope"], dtype=object),
        "coef": coef.astype(np.float64),
        "se": se.astype(np.float64),
        "t": np.asarray(tval, dtype=np.float64),
        "p": pval.astype(np.float64),
        "bias_overall": np.array([float(bias.mean())]),
        "residual_sd": np.array([float(np.sqrt(mse))]),
        "dof": np.array([dof], dtype=np.int64),
    }


def _cohen_kappa(a, b):
    """2 人分の評価から Cohen のカッパ。``(p_o - p_e)/(1 - p_e)``。"""
    cats = np.unique(np.concatenate([a, b]))
    k = len(cats)
    idx = {v: i for i, v in enumerate(cats)}
    m = np.zeros((k, k), dtype=np.float64)
    for x, y in zip(a, b):
        m[idx[x], idx[y]] += 1.0
    n = m.sum()
    p_o = float(np.trace(m) / n)
    p_e = float((m.sum(axis=1) @ m.sum(axis=0)) / (n * n))
    if p_e >= 1.0:                               # 全員が同じ 1 カテゴリしか使っていない
        return (1.0 if p_o >= 1.0 else float("nan")), p_o, p_e
    return (p_o - p_e) / (1.0 - p_e), p_o, p_e


def msa_attribute_agreement(table, appraiser="appraiser", part="part",
                            rating="rating"):
    """計数値(合否)検査の一致度(``table``)。

    同じ部品を複数の検査員が判定した表から、**検査員の対ごとの Cohen のカッパ**と
    全体の **Fleiss のカッパ**、および素の一致率を返す。

    ★カッパは一致率そのものではない。``kappa = (p_o - p_e)/(1 - p_e)`` で、
    **偶然でも起きる一致 p_e を割り引いた**残りを測る —— 合格率 95 % の工程では
    でたらめに判を押しても素の一致率は 90 % を超えるので、一致率だけ見ると
    「よく合っている」と読めてしまう。

    ★門にできる厳密な値: 全員が同じ判定 → ``kappa = 1``(厳密)。2 人 x 2 カテゴリの
    Cohen のカッパは ``2(ad-bc)/((a+b)(b+d)+(a+c)(c+d))`` という閉形式と一致する。
    独立でたらめな判定では期待値 0(こちらは標本ごとに揺れるので区間で見る)。
    """
    op = "msa_attribute_agreement"
    c = _cols(table, op, (appraiser, part, rating))
    app, prt, rat = c[appraiser], c[part], c[rating]
    apprs = np.unique(app)
    if len(apprs) < 2:
        raise ValueError("%s: need at least 2 appraisers to measure agreement, got %d"
                         % (op, len(apprs)))
    parts = np.unique(prt)
    # 検査員 x 部品 の判定表。1 人が同じ部品を 2 回以上見ている表は拒む(その場合は
    # どの回を使うかで答えが変わる —— 黙って最初の 1 回を採らない)。
    grid = {}
    for a, p_, r_ in zip(app, prt, rat):
        if (a, p_) in grid:
            raise ValueError(
                "%s: appraiser %r rated part %r more than once. Repeated appraisals "
                "measure a different thing (within-appraiser repeatability); pick the "
                "trial you mean instead of letting this op choose one." % (op, a, p_))
        grid[(a, p_)] = r_
    missing = [(a, p_) for a in apprs for p_ in parts if (a, p_) not in grid]
    if missing:
        raise ValueError("%s: %d appraiser/part combination(s) are missing (e.g. %r) — "
                         "agreement is only defined on the parts everyone saw"
                         % (op, len(missing), missing[0]))

    mat = np.array([[grid[(a, p_)] for p_ in parts] for a in apprs], dtype=object)
    pairs, kappas, obs = [], [], []
    for i in range(len(apprs)):
        for j in range(i + 1, len(apprs)):
            k, p_o, _ = _cohen_kappa(mat[i], mat[j])
            pairs.append("%s|%s" % (apprs[i], apprs[j]))
            kappas.append(k)
            obs.append(p_o)

    # Fleiss のカッパ(同じ部品を n 人が見た形)
    cats = np.unique(mat.reshape(-1))
    n_r = len(apprs)
    counts = np.zeros((len(parts), len(cats)), dtype=np.float64)
    cidx = {v: i for i, v in enumerate(cats)}
    for i in range(len(parts)):
        for a in range(n_r):
            counts[i, cidx[mat[a, i]]] += 1.0
    if n_r < 2 or len(cats) < 2:
        fleiss = 1.0 if len(cats) < 2 else float("nan")
        p_bar = 1.0
    else:
        p_i = (np.square(counts).sum(axis=1) - n_r) / (n_r * (n_r - 1))
        p_bar = float(p_i.mean())
        p_j = counts.sum(axis=0) / (len(parts) * n_r)
        p_e = float((p_j ** 2).sum())
        fleiss = (p_bar - p_e) / (1.0 - p_e) if p_e < 1.0 else (
            1.0 if p_bar >= 1.0 else float("nan"))

    all_agree = np.array([len(set(mat[:, i])) == 1 for i in range(len(parts))])
    return {
        "pair": np.array(pairs, dtype=object),
        "kappa": np.array(kappas, dtype=np.float64),
        "observed_agreement": np.array(obs, dtype=np.float64),
        "fleiss_kappa": np.array([float(fleiss)]),
        "overall_agreement": np.array([float(all_agree.mean())]),
        "n_appraisers": np.array([n_r], dtype=np.int64),
        "n_parts": np.array([len(parts)], dtype=np.int64),
        "n_categories": np.array([len(cats)], dtype=np.int64),
    }


# --------------------------------------------------------------------------- #
# GUM(測定の不確かさ)
# --------------------------------------------------------------------------- #
#: 分布の形 -> 半幅を割る数。いずれも分散の定義から出る厳密な値。
_GUM_DIVISOR = {
    "rectangular": np.sqrt(3.0),   # 一様分布 [-a, a] の標準偏差 = a/sqrt(3)
    "uniform": np.sqrt(3.0),
    "triangular": np.sqrt(6.0),    # 三角分布(半幅 a)の標準偏差 = a/sqrt(6)
    "u_shaped": np.sqrt(2.0),      # 逆正弦分布(半幅 a)の標準偏差 = a/sqrt(2)
    "arcsine": np.sqrt(2.0),
    "normal_95": 1.959963984540054,   # 半幅が 95 % 区間として与えられた場合
    "normal_99": 2.5758293035489004,
    "normal_k1": 1.0,              # 半幅が既に標準不確かさ
}


def gum_standard_uncertainty(table, halfwidth="halfwidth", distribution="distribution"):
    """不確かさの成分を**分布の形**から標準不確かさへ直す(``table``)。

    校正証明書や規格が与えるのは「半幅 a」「95 % で ±U」のような形であって標準偏差
    ではない。伝播則が食えるのは標準不確かさだけなので、ここで揃える:

        矩形(一様)  u = a / sqrt(3)      三角      u = a / sqrt(6)
        U 字(逆正弦) u = a / sqrt(2)      normal_95 u = a / 1.959964

    ★どれも分布の分散の定義から出る**厳密**な値で、モンテカルロで標本標準偏差を
    取れば同じ数に収束する(``gum_monte_carlo`` が独立に確かめる)。

    ★★**既定の分布を置かない**。一番よく使うからといって矩形を既定にすると、
    形を書き忘れた成分が黙って a/sqrt(3) になる —— 三角のつもりなら 1.41 倍、
    95 % 区間のつもりなら 1.13 倍ずれた不確かさが、例外を出さずに下流へ流れる。
    """
    op = "gum_standard_uncertainty"
    c = _cols(table, op, (halfwidth, distribution))
    a = _numeric(c[halfwidth], halfwidth, op)
    if (a < 0).any():
        raise ValueError("%s: a half-width cannot be negative" % op)
    kinds = [str(k).lower() for k in c[distribution]]
    bad = sorted({k for k in kinds if k not in _GUM_DIVISOR})
    if bad:
        raise ValueError("%s: unknown distribution(s) %s — known: %s"
                         % (op, bad, sorted(_GUM_DIVISOR)))
    div = np.array([_GUM_DIVISOR[k] for k in kinds], dtype=np.float64)
    return {
        "distribution": np.array(kinds, dtype=object),
        "halfwidth": a,
        "divisor": div,
        "u": a / div,
    }


def _uncertainty_terms(table, op, u, sensitivity):
    c = _cols(table, op, (u, sensitivity))
    uu = _numeric(c[u], u, op)
    cc = _numeric(c[sensitivity], sensitivity, op)
    if (uu < 0).any():
        raise ValueError("%s: a standard uncertainty cannot be negative" % op)
    return uu, cc


def gum_propagate(table, u="u", sensitivity="sensitivity", correlation=None):
    """不確かさの伝播則(GUM 5.2、相関つき)(``table``)。

        u_c^2 = sum_i (c_i u_i)^2 + 2 sum_{i<j} c_i c_j u_i u_j r_ij

    *table* は列 *u*(標準不確かさ)と *sensitivity*(感度係数 ``c_i = df/dx_i``)を
    持つ表。*correlation* に (n, n) の相関行列を渡すと相関項を含める。

    ★門にできる閉形式: ``f = x y`` なら ``c_x = y`` / ``c_y = x`` なので
    ``u_c/|f| = sqrt((u_x/x)^2 + (u_y/y)^2)`` —— 相対不確かさの二乗和。
    相関 ``r = +1`` の 2 成分では ``u_c = |c1 u1 + c2 u2||`` に**厳密に**一致し、
    ``r = -1`` では ``|c1 u1 - c2 u2|``(打ち消し)。無相関なら寄与の合計が
    ``u_c^2`` にぴったり閉じる。

    ★★**相関を無視した誤りの向きは一定ではない**。「独立として扱うと過小評価になる」
    はよく言われるが、**偽である**。規格の worked example(電圧・電流・位相差から
    抵抗とリアクタンスを同時に出す例、3 量すべてに相関がある)で相関を落として測ると:

        u_c(R)  0.0702 -> 0.1945   **2.8 倍の過大**
        u_c(X)  0.2961 -> 0.2009   過小
        u_c(Z)  0.2367 -> 0.2041   過小

    同じ 1 つのデータで、量によって向きが逆に出る —— 感度係数の符号と相関の符号の
    積で決まるので、当たり前といえば当たり前だが、「安全側に外れる」と思って相関を
    省くと **R では 3 倍近く過大な不確かさを報告**することになる。
    """
    op = "gum_propagate"
    uu, cc = _uncertainty_terms(table, op, u, sensitivity)
    n = uu.size
    contrib = (cc * uu) ** 2
    cov_total = 0.0
    if correlation is not None:
        R = np.asarray(correlation, dtype=np.float64)
        if R.shape != (n, n):
            raise ValueError("%s: correlation must be (%d, %d), got %s"
                             % (op, n, n, R.shape))
        if not np.allclose(R, R.T, atol=1e-12):
            raise ValueError("%s: correlation matrix is not symmetric" % op)
        if not np.allclose(np.diag(R), 1.0, atol=1e-12):
            raise ValueError("%s: correlation matrix must have 1 on the diagonal" % op)
        if (np.abs(R) > 1.0 + 1e-12).any():
            raise ValueError("%s: correlation coefficients must lie in [-1, 1]" % op)
        w = cc * uu
        cov_total = float(w @ R @ w - (w ** 2).sum())
    uc2 = float(contrib.sum() + cov_total)
    if uc2 < 0.0:
        # 相関行列が半正定値でないと負になりうる。黙って 0 に丸めない。
        raise ValueError(
            "%s: the propagated variance came out negative (%.3e). That means the "
            "correlation matrix is not positive semi-definite — it is not a possible "
            "set of correlations, so no combined uncertainty follows from it." % (op, uc2))
    uc = float(np.sqrt(uc2))
    # ★★**破綻は警告でなく構造で返す**。感度係数がすべて 0 になると、入力に
    #   不確かさがあるのに合成不確かさが 0 になる —— 規格の比較損失の例
    #   (``dY = X1^2 + X2^2`` を ``x_i = 0`` で評価)がまさにこれで、
    #   ``c_i = 2 x_i = 0`` だから 1 次近似は「不確かさゼロ」と答える。数式としては
    #   正しいが**測定の主張としては嘘**で、モンテカルロは同じ状況で ``u = 50e-6``
    #   を返す。0 を返すこと自体は止めない(それが伝播則の答えなので)が、
    #   ``guf_valid=False`` と ``invalid_reasons=["stationary_point"]`` を**結果に
    #   同伴させる**。警告にすると握りつぶされ、呼んだ側は「測定が完璧だった」と読む。
    #
    #   ★**この検出条件そのものは本実装の判断であって、規格が列挙したものではない**。
    #   規格が定めるのは線形モデルの 3 条件(Welch-Satterthwaite の適用可否 /
    #   有限自由度の入力が独立であること / 出力分布が正規または t で近似できること)と
    #   非線形モデルの 5 条件(最良推定値の近傍で連続微分可能 / 適切な次数の全微分で
    #   成立 / 高次項に関わる入力が独立 / その分布が正規 / 落とした高次項が無視できる)
    #   で、「感度が全部 0」「区間が定義域を出る」という**判定手順は書かれていない**。
    #   ここで実装したのは、その条件が破れたときに**観測される形**のほうである
    #   —— 停留点は高次項が支配する特殊例、負側への張り出しは正規近似の破綻の現れ。
    reasons = []
    if uc2 == 0.0 and (uu > 0).any():
        reasons.append("stationary_point")
    return {
        "u": uu,
        "sensitivity": cc,
        "contribution": contrib,
        # ★破綻は**警告でなく構造**で返す(警告は握りつぶされる/ログに消える)
        "guf_valid": np.array([not reasons]),
        "invalid_reasons": np.array(reasons, dtype=object),
        "pct_contribution": 100.0 * contrib / uc2 if uc2 > 0 else np.full(n, float("nan")),
        "covariance_term": np.array([cov_total]),
        "u_combined": np.array([uc]),
    }


def gum_expanded(table, u="u", sensitivity="sensitivity", dof="dof", level=0.95,
                 correlation=None, estimate=None, lower_bound=None, upper_bound=None):
    """Welch-Satterthwaite の有効自由度と包含係数 k、拡張不確かさ U(``table``)。

        nu_eff = u_c^4 / sum_i (c_i u_i)^4 / nu_i        U = k u_c,  k = t_{p}(nu_eff)

    ★門にできる厳密な性質が 3 つある:

      * 成分が 1 つだけなら ``nu_eff == nu``(厳密)。
      * ``nu_eff >= min_i nu_i`` が**常に**成り立つ。証明は
        ``sum u_i^4/nu_i <= (1/nu_min) sum u_i^4 <= (1/nu_min)(sum u_i^2)^2``。
        有効自由度が最小の成分より小さくなったら計算が壊れている。
      * すべての自由度が無限大なら ``k`` は正規分布の分位点へ収束する
        (95 % で 1.959964)。

    無限自由度(既知の定数など)は ``numpy.inf`` を入れる。
    """
    op = "gum_expanded"
    base = gum_propagate(table, u=u, sensitivity=sensitivity, correlation=correlation)
    c = _cols(table, op, (dof,))
    nu = np.asarray(c[dof], dtype=np.float64)
    if (nu <= 0).any():
        raise ValueError("%s: degrees of freedom must be positive (use numpy.inf for "
                         "a component known exactly)" % op)
    if not (0.0 < float(level) < 1.0):
        raise ValueError("%s: level must lie strictly between 0 and 1, got %r"
                         % (op, level))
    uc = float(base["u_combined"][0])
    terms = base["contribution"]                 # (c_i u_i)^2
    with np.errstate(divide="ignore", invalid="ignore"):
        denom = float(np.nansum(np.where(np.isfinite(nu), terms ** 2 / nu, 0.0)))
    nu_eff = float("inf") if denom <= 0 else uc ** 4 / denom
    _st = _scipy_stats()
    # ★規格は「nu_eff が整数でなければ**次に小さい整数へ切り捨ててから** t を引く」
    #   ことを要求する(安全側に倒すため)。16.64 のまま引くと k = 2.1132、
    #   切り捨てて 16 で引くと 2.1199 —— 公表例題の 2.12 は後者。0.3 % の差だが、
    #   拡張不確かさは報告書に載る数字なので規格どおりに倒す。切り捨て前の値も
    #   ``dof_effective`` に残す(どこで丸めたかが見えないと追えない)。
    if not np.isfinite(nu_eff):
        nu_used = float("inf")
        k = float(_st.norm.ppf(0.5 * (1.0 + level)))
    else:
        nu_used = float(np.floor(nu_eff))
        if nu_used < 1.0:
            raise ValueError(
                "%s: the effective degrees of freedom came out below 1 (%.3f). No "
                "coverage factor follows from that — the uncertainty budget is "
                "dominated by a component with almost no degrees of freedom." % (op, nu_eff))
        k = float(_st.t.ppf(0.5 * (1.0 + level), nu_used))
    reasons = list(base["invalid_reasons"])
    out = {
        "u_combined": np.array([uc]),
        "dof_effective": np.array([nu_eff]),
        "dof_used": np.array([nu_used]),
        "coverage_factor": np.array([k]),
        "level": np.array([float(level)]),
        "expanded": np.array([k * uc]),
    }
    if estimate is not None:
        y = float(estimate)
        lo, hi = y - k * uc, y + k * uc
        out["low"] = np.array([lo])
        out["high"] = np.array([hi])
        # ★**区間が定義域を出たら、それは測定の主張でなく近似の破綻**。
        #   比較損失(二乗の和)は構成上非負なのに、規格の例題では伝播則の 95 %
        #   区間が [-96, +296]e-6 と負側へ張り出す。伝播則は出力を正規と見なすので
        #   境界を知らない —— 知っているのは呼ぶ側だけなので、境界を渡されたときに
        #   限って検査する(既定で勝手に 0 を下限と仮定はしない)。
        if lower_bound is not None and lo < float(lower_bound) - 1e-15:
            reasons.append("infeasible_interval")
        elif upper_bound is not None and hi > float(upper_bound) + 1e-15:
            reasons.append("infeasible_interval")
    out["guf_valid"] = np.array([not reasons])
    out["invalid_reasons"] = np.array(reasons, dtype=object)
    return out


def gum_monte_carlo(table, u="u", sensitivity="sensitivity", n=200_000, seed=0,
                    level=0.95, correlation=None, distribution=None,
                    value=None, power=None):
    """GUM 補遺 1(JCGM 101)のモンテカルロ伝播(``table``)。

    各入力量を分布から引いて ``y = sum_i c_i x_i`` を作り、標本から標準不確かさと
    最短の包含区間を返す。既定は正規分布で、*distribution* に列名を渡すと
    ``gum_standard_uncertainty`` と同じ形の名前(rectangular / triangular / ...)を
    成分ごとに指定できる(半幅ではなく**標準不確かさ**を持つ分布を作る)。

    *value* と *power* に列名を渡すと **冪モデル** を回す:

        y = sum_i c_i (x_i + e_i)^{p_i}

    (``e_i`` が分布から引いた揺らぎ。既定は ``x_i = 0`` / ``p_i = 1`` = 線形。)
    冪までに絞ったのは、台帳に載る op は**宣言的**でなければならず、任意の関数を
    受け取れないため —— それでも規格の非線形の例(二乗の和)はこれで表現でき、
    伝播則が破綻する場面を再現できる。

    ★これは ``gum_propagate`` の**独立な検算**である。伝播則は偏微分と分散の代数、
    こちらは乱数の標本 —— 導出も実装も別なので、線形モデルでは
    ``u_mc -> u_c``(1/sqrt(n) の速さ)に近づくはずで、近づかなければどちらかが
    壊れている。相関は Cholesky 分解で入れるので、伝播則の相関項とは別の経路を通る。

    ★★**非線形では両者が食い違うのが正しい**。規格の例(比較損失
    ``dY = X1^2 + X2^2``、各 ``u = 0.005``)を ``x1 = x2 = 0`` で回すと:

        伝播則   感度 ``c_i = 2 x_i`` が**両方 0** になるので ``u_c = 0``、区間 [0, 0]
        モンテカルロ  ``dy = 50e-6``、``u = 50e-6``、区間 ``[0, 150e-6]``

    伝播則は「不確かさゼロ」と答える —— これは実装の誤りではなく、**1 次近似が
    極値で情報を失う**という手法そのものの限界。こういう場面があるから補遺 1 の
    モンテカルロが要る。``x1 = 0.010`` では伝播則の区間が ``[-96, +296]e-6`` と
    **負の損失**を含み(物理的にありえない)、``x1 = 0.050`` まで離れると
    ``[1520, 3480]`` 対 ``[1590, 3543]`` と近づく。

    ★★**正規分布でない入力では、包含区間は ``k u_c`` と一致しない**。矩形分布を
    足し合わせると中心極限定理で正規に近づくが、成分が 1 つだけなら最短 95 % 区間の
    半幅は **``0.95 a``**(支持の端 ``a`` ではない —— 95 % ぶんの幅しか要らない)で、
    ``k u = 1.96 a/sqrt(3) = 1.1316 a`` より**狭い**。比は
    ``1.959964/(sqrt(3) x 0.95) = 1.1911`` という閉形式で、実測 1.1914。
    これは欠陥ではなく**伝播則が分布の形を捨てている**ことの現れなので、両方返して
    読み手に見せる(この 0.95 を最初 ``a`` と思い込んで門を誤らせた)。
    """
    op = "gum_monte_carlo"
    uu, cc = _uncertainty_terms(table, op, u, sensitivity)
    m = uu.size
    n = int(n)
    if n < 1000:
        raise ValueError("%s: n must be at least 1000 to make a coverage interval "
                         "meaningful, got %d" % (op, n))
    kinds = ["normal"] * m
    if distribution is not None:
        col = _cols(table, op, (distribution,))[distribution]
        kinds = [str(k).lower() for k in col]
        known = set(_GUM_DIVISOR) | {"normal"}
        bad = sorted({k for k in kinds if k not in known})
        if bad:
            raise ValueError("%s: unknown distribution(s) %s" % (op, bad))

    rng = np.random.default_rng(int(seed))
    # 標準化した標本を作る(平均 0、標準偏差 1)。分布の形だけがここで効く。
    z = np.empty((n, m), dtype=np.float64)
    for i, kind in enumerate(kinds):
        if kind == "normal" or kind.startswith("normal_"):
            z[:, i] = rng.standard_normal(n)
        elif kind in ("rectangular", "uniform"):
            z[:, i] = rng.uniform(-1.0, 1.0, n) * np.sqrt(3.0)
        elif kind == "triangular":
            z[:, i] = rng.triangular(-1.0, 0.0, 1.0, n) * np.sqrt(6.0)
        elif kind in ("u_shaped", "arcsine"):
            z[:, i] = np.cos(rng.uniform(0.0, np.pi, n)) * np.sqrt(2.0)
        else:                                    # pragma: no cover
            raise ValueError("%s: unknown distribution %r" % (op, kind))
    if correlation is not None:
        R = np.asarray(correlation, dtype=np.float64)
        if R.shape != (m, m):
            raise ValueError("%s: correlation must be (%d, %d), got %s"
                             % (op, m, m, R.shape))
        try:
            L = np.linalg.cholesky(R)
        except np.linalg.LinAlgError as exc:
            raise ValueError(
                "%s: the correlation matrix is not positive definite, so there is no "
                "joint distribution with those correlations to sample from (%s)"
                % (op, exc)) from exc
        z = z @ L.T

    xs = np.zeros(m, dtype=np.float64)
    if value is not None:
        xs = _numeric(_cols(table, op, (value,))[value], value, op)
    ps = np.ones(m, dtype=np.float64)
    if power is not None:
        ps = _numeric(_cols(table, op, (power,))[power], power, op)
        if (ps <= 0).any() or not np.allclose(ps, np.round(ps)):
            raise ValueError("%s: power must be a positive whole number per component "
                             "(fractional powers of a negative sample are undefined)" % op)
    if value is None and power is None:
        y = z @ (cc * uu)                    # 線形(既定)—— 従来と同じ経路
    else:
        y = ((xs + z * uu) ** ps) @ cc

    u_mc = float(y.std(ddof=1))
    lo, hi = _shortest_interval(y, float(level))
    return {
        "u_monte_carlo": np.array([u_mc]),
        "mean": np.array([float(y.mean())]),
        "low": np.array([lo]),
        "high": np.array([hi]),
        "half_width": np.array([0.5 * (hi - lo)]),
        "level": np.array([float(level)]),
        "n": np.array([n], dtype=np.int64),
    }


def gum_validate(guf, mcm, ndig=2):
    """モンテカルロの結果で伝播則の結果を**検証**する(``table``)。

    *guf* は ``gum_expanded``(``estimate`` を渡して区間を出したもの)、*mcm* は
    ``gum_monte_carlo`` の返り。手続きは規格 8.1.3 のとおり:

      1. ``u(y)`` に対応する**数値許容差** ``delta`` を作る。``z`` を
         ``c x 10^l``(``c`` は *ndig* 桁の整数)の形に書いたとき ``delta = 0.5 x 10^l``。
      2. ``dlow = |y - U - y_low|`` と ``dhigh = |y + U - y_high|`` を求める
         —— 比べるのは**カバレッジ区間の端点**であって ``U`` そのものではない。
      3. 両方が ``delta`` 以下なら、そのインスタンスで伝播則は検証されたとする。

    ★**「一致した」と「一致すべきだった」を混同しない**。この op が返すのは
    *ndig* 桁で見たときの一致であって、真偽ではない。*ndig* を上げれば同じ数字でも
    不一致になる —— 実測(加法モデル、矩形入力、端点差 0.04):

        ndig=1 -> delta 0.5    一致
        ndig=2 -> delta 0.05   一致(きわどい)
        ndig=3 -> delta 0.005  **不一致**

    つまり ndig は「どこまでの桁を主張するか」であり、**主張を強くすれば伝播則は
    検証に落ちる**。既定の 2 は規格が典型と述べる値(1 か 2)の上側。

    ★★**出力が対称なとき**、端点で比べるのは幅で比べるより本質的に厳しい。最短区間の
    幅 ``W(a) = F(a+w) - F(a)`` は対称分布の中央で ``W' = 0`` かつ曲率が小さい
    **平らな谷**になるので、幅は精度よく決まるのに ``argmin``(位置)が定まらない。
    4 成分の加法モデル(正規)で種 12 本ずつ測った実測:

        n           半幅の標準偏差      区間の中心の標準偏差   比
        200,000     0.0054              0.0284                 5.2
        1,000,000   0.0035              0.0146                 4.1
        5,000,000   0.0011              0.0114                10.0

    ★**これは対称(または近対称)の出力に限った話**である。歪んだ出力では最適点が
    一意に強く決まるので位置も普通に ``1/sqrt(n)`` で収束する —— 同じ測り方で
    二乗の和(強い歪み)を測ると **位置 sd / 幅 sd の比は 1.0**(n=200,000 でも
    n=1,000,000 でも)。規格の比較損失の例でモンテカルロが公表値に素直に乗るのは
    そのため。

    したがって ``dlow`` / ``dhigh`` が大きいとき、**出力が対称なら**それは伝播則の
    誤りではなくモンテカルロの位置決めの揺れであることが多い。理論上は厳密に
    一致するはずの正規入力でも ``ndig=3``(``delta=0.005``)は n=5,000,000 で
    5 本中 2 本しか通らない。

    ★区間の推定器そのものに偏りは無い。1 成分・正規の厳密解(半幅 1.959964)に対し
    実測の偏りは n=50,000 で −0.0060、n=5,000,000 で **−0.000008** まで縮み、
    標準偏差も ``1/sqrt(n)`` に従う(0.0086 → 0.0009)。

    ★検証用のモンテカルロは ``delta/5`` の精度まで回すことが規格の推奨で、試行数の
    目安は ``M >= 10^4 / (1 - p)``(95 % なら 2 x 10^5)。
    """
    op = "gum_validate"
    for name, tb in (("guf", guf), ("mcm", mcm)):
        if not isinstance(tb, dict):
            raise ValueError("%s: %s must be a table (a dict of columns), got %s"
                             % (op, name, type(tb).__name__))
    need_guf = ("u_combined", "expanded", "low", "high")
    missing = [c for c in need_guf if c not in guf]
    if missing:
        raise ValueError(
            "%s: the guf table lacks %s — call gum_expanded with estimate=... so that "
            "it produces a coverage interval to compare (this procedure compares "
            "interval endpoints, not the expanded uncertainty)" % (op, missing))
    missing = [c for c in ("low", "high") if c not in mcm]
    if missing:
        raise ValueError("%s: the mcm table lacks %s" % (op, missing))

    ndig = int(ndig)
    if ndig < 1:
        raise ValueError("%s: ndig must be at least 1, got %r" % (op, ndig))
    uy = float(guf["u_combined"][0])
    if not np.isfinite(uy) or uy <= 0.0:
        raise ValueError(
            "%s: the numerical tolerance is built from u(y), which is %r here. With no "
            "spread there is no tolerance to compare against — this is exactly the "
            "stationary-point case the propagation law cannot describe." % (op, uy))
    lo_e = int(np.floor(np.log10(abs(uy)))) - (ndig - 1)
    delta = 0.5 * 10.0 ** lo_e

    dlow = abs(float(guf["low"][0]) - float(mcm["low"][0]))
    dhigh = abs(float(guf["high"][0]) - float(mcm["high"][0]))
    return {
        "agree": np.array([bool(dlow <= delta and dhigh <= delta)]),
        "dlow": np.array([dlow]),
        "dhigh": np.array([dhigh]),
        "delta": np.array([delta]),
        "ndig": np.array([ndig], dtype=np.int64),
        "u_y": np.array([uy]),
    }


def _shortest_interval(y: np.ndarray, level: float):
    """標本の最短包含区間(GUM 補遺 1 の推奨。非対称な分布でこれが効く)。"""
    if not (0.0 < level < 1.0):
        raise ValueError("gum_monte_carlo: level must lie strictly between 0 and 1")
    s = np.sort(y)
    n = s.size
    q = int(np.floor(level * n))
    if q < 1:
        raise ValueError("gum_monte_carlo: level too small for n=%d" % n)
    widths = s[q:] - s[:n - q]
    i = int(np.argmin(widths))
    return float(s[i]), float(s[i + q])
