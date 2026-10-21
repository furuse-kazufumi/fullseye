# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""doe — design of experiments: which settings to run, in coded and natural units.

A simulation or a test bench answers "what happens at this setting?". Before any
regression, sensitivity index or calibration can be trusted, the *settings* have to
be chosen so that the effects of interest can be told apart. This module builds the
classical plans and returns them as a ``design``: one object that carries **both**
the coded matrix (each factor scaled to −1..+1, what the statistics is computed
on) and the natural matrix (volts, millimetres, milliseconds — what the bench is
set to), together with the confounding (alias) table that says which effects the
plan cannot separate.

Why a separate sort and not a plain ``matrix``: coded and natural matrices have the
same shape and the same dtype, and mixing them up never raises — a regression on
natural units with a quadratic model silently returns coefficients for a
differently-centred polynomial, and the stationary point lands somewhere else. The
``design`` keeps the two together and every consumer reads the one it needs.

Ops
---
``doe_lhs``                   Latin hypercube (McKay, Beckman & Conover 1979): one
                              point in each of ``n`` equal strata of every factor.
``doe_orthogonal_array``      Taguchi / Bose-Bush orthogonal arrays L4, L8, L9, L12,
                              L16, L18, L27, copied from published tables (see
                              :data:`OA_SOURCES`); returns the interaction-column table.
``doe_fractional_factorial``  regular two-level 2^(k-p) fraction from generators
                              (Box & Hunter 1961): defining relation, resolution,
                              alias table up to two-factor interactions.
``doe_central_composite``     central composite design (Box & Wilson 1951):
                              factorial + axial (±alpha) + centre points; rotatable
                              alpha = F^(1/4) (F = number of factorial points).
``doe_box_behnken``           Box-Behnken design (Box & Behnken 1960) for 3-5 factors.
``doe_encode`` / ``doe_decode`` natural <-> coded, linear or log scale per factor.

The ``design`` sort (a ``dict``)
-------------------------------
``sort`` = ``"design"`` · ``kind`` · ``factors`` (names) · ``units`` · ``lo`` / ``hi``
(the natural values that map to coded −1 / +1) · ``scale`` (``"linear"`` or ``"log"``
per factor) · ``coded`` (n, k) · ``natural`` (n, k) · ``levels`` (distinct levels per
factor) · ``alias`` (list of human-readable confounding lines, empty = none known) ·
``resolution`` (int or ``None``) · ``source`` (where the plan comes from) · ``meta``
(kind-specific: centre points, alpha, generators, trajectories ...).

Fail-closed: an unknown array name, more factors than the plan has columns,
non-finite or inverted ranges, a log scale with a non-positive bound, generators
that reference unknown letters or repeat a word, and unsupported sizes are refused
with ``ValueError`` — never padded or clipped.
"""
from __future__ import annotations

import itertools
import math
import re

import numpy as np

__all__ = [
    "doe_lhs", "doe_orthogonal_array", "doe_fractional_factorial",
    "doe_central_composite", "doe_box_behnken", "doe_encode", "doe_decode",
]

#: upper bounds that keep one call bounded in memory/time
MAX_RUNS = 1_000_000
MAX_FACTORS = 64
#: factor letters for two-level fractions: I is skipped (it is the identity word),
#: as in Box, Hunter & Hunter and the NIST/SEMATECH e-Handbook tables
LETTERS = "ABCDEFGHJKLMNOPQRSTUVWXYZ"


# --------------------------------------------------------------------------- #
# factor specification and the design dict                                    #
# --------------------------------------------------------------------------- #
def _factor_spec(factors, op: str, k_default: int | None = None) -> dict:
    """Normalise a factor specification.

    Accepts an int ``k`` (names ``x1..xk``, range −1..+1, no unit), a list of names,
    a list of ``(name, lo, hi[, unit[, scale]])`` tuples, or a list of dicts with
    keys ``name, lo, hi, unit, scale``.
    """
    if factors is None:
        if k_default is None:
            raise ValueError("%s: factors is required" % op)
        factors = k_default
    if isinstance(factors, (int, np.integer)) and not isinstance(factors, bool):
        k = int(factors)
        if not 1 <= k <= MAX_FACTORS:
            raise ValueError("%s: number of factors must be 1..%d, got %d" % (op, MAX_FACTORS, k))
        return {"names": ["x%d" % (i + 1) for i in range(k)], "lo": np.full(k, -1.0),
                "hi": np.full(k, 1.0), "units": [""] * k, "scale": ["linear"] * k}
    if isinstance(factors, (str, bytes)) or not hasattr(factors, "__iter__"):
        raise ValueError("%s: factors must be an int, a list of names, (name, lo, hi[, unit[, scale]]) "
                         "tuples or dicts, got %r" % (op, factors))
    items = list(factors)
    if not 1 <= len(items) <= MAX_FACTORS:
        raise ValueError("%s: number of factors must be 1..%d, got %d" % (op, MAX_FACTORS, len(items)))
    names, lo, hi, units, scale = [], [], [], [], []
    for i, it in enumerate(items):
        if isinstance(it, str):
            rec = {"name": it, "lo": -1.0, "hi": 1.0}
        elif isinstance(it, dict):
            rec = dict(it)
        elif isinstance(it, (tuple, list)) and 3 <= len(it) <= 5:
            rec = dict(zip(("name", "lo", "hi", "unit", "scale"), it))
        else:
            raise ValueError("%s: factor %d must be a name, (name, lo, hi[, unit[, scale]]) or a dict, got %r"
                             % (op, i, it))
        name = str(rec.get("name", "x%d" % (i + 1)))
        try:
            a, b = float(rec["lo"]), float(rec["hi"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("%s: factor %r needs numeric lo and hi" % (op, name)) from None
        if not (math.isfinite(a) and math.isfinite(b)) or not b > a:
            raise ValueError("%s: factor %r needs finite lo < hi, got lo=%r hi=%r" % (op, name, a, b))
        sc = str(rec.get("scale") or "linear")
        if sc not in ("linear", "log"):
            raise ValueError("%s: factor %r scale must be 'linear' or 'log', got %r" % (op, name, sc))
        if sc == "log" and a <= 0:
            raise ValueError("%s: factor %r has a log scale but lo=%r <= 0" % (op, name, a))
        names.append(name)
        lo.append(a)
        hi.append(b)
        units.append(str(rec.get("unit") or ""))
        scale.append(sc)
    if len(set(names)) != len(names):
        raise ValueError("%s: factor names must be unique, got %s" % (op, names))
    return {"names": names, "lo": np.asarray(lo), "hi": np.asarray(hi), "units": units, "scale": scale}


def _to_natural(coded: np.ndarray, spec: dict) -> np.ndarray:
    """Coded (−1..+1 maps to lo..hi) -> natural, per-factor linear or log10."""
    nat = np.empty_like(coded, dtype=np.float64)
    for j, sc in enumerate(spec["scale"]):
        a, b = spec["lo"][j], spec["hi"][j]
        if sc == "log":
            la, lb = math.log10(a), math.log10(b)
            nat[:, j] = 10.0 ** (0.5 * (la + lb) + 0.5 * (lb - la) * coded[:, j])
        else:
            nat[:, j] = 0.5 * (a + b) + 0.5 * (b - a) * coded[:, j]
    return nat


def _to_coded(natural: np.ndarray, spec: dict, op: str) -> np.ndarray:
    cod = np.empty_like(natural, dtype=np.float64)
    for j, sc in enumerate(spec["scale"]):
        a, b = spec["lo"][j], spec["hi"][j]
        if sc == "log":
            if (natural[:, j] <= 0).any():
                raise ValueError("%s: factor %r is on a log scale but has values <= 0"
                                 % (op, spec["names"][j]))
            la, lb = math.log10(a), math.log10(b)
            cod[:, j] = (np.log10(natural[:, j]) - 0.5 * (la + lb)) / (0.5 * (lb - la))
        else:
            cod[:, j] = (natural[:, j] - 0.5 * (a + b)) / (0.5 * (b - a))
    return cod


def _design(kind: str, coded: np.ndarray, spec: dict, *, alias=None, resolution=None,
            source: str = "", meta: dict | None = None) -> dict:
    coded = np.asarray(coded, dtype=np.float64)
    if coded.ndim != 2 or coded.shape[1] != len(spec["names"]):
        raise ValueError("internal: coded matrix shape %s does not match %d factors"
                         % (coded.shape, len(spec["names"])))
    if coded.shape[0] > MAX_RUNS:
        raise ValueError("%s: %d runs exceeds the cap %d" % (kind, coded.shape[0], MAX_RUNS))
    # a coded value that is -0.0 prints as "-0" in tables; normalise
    coded = coded + 0.0
    levels = [int(np.unique(np.round(coded[:, j], 12)).size) for j in range(coded.shape[1])]
    return {
        "sort": "design", "kind": kind,
        "factors": list(spec["names"]), "units": list(spec["units"]),
        "lo": np.asarray(spec["lo"], dtype=np.float64).copy(),
        "hi": np.asarray(spec["hi"], dtype=np.float64).copy(),
        "scale": list(spec["scale"]),
        "coded": coded, "natural": _to_natural(coded, spec),
        "levels": levels, "alias": list(alias or []),
        "resolution": resolution, "source": source, "meta": dict(meta or {}),
    }


def _spec_from_design(design, op: str) -> dict:
    """Validate a ``design`` dict and return its factor spec (fail-closed)."""
    if not isinstance(design, dict) or design.get("sort") != "design":
        raise ValueError("%s: expected a design (dict with sort='design'), got %s"
                         % (op, type(design).__name__))
    for key in ("factors", "lo", "hi", "scale", "coded", "natural"):
        if key not in design:
            raise ValueError("%s: design is missing %r" % (op, key))
    k = len(design["factors"])
    coded = np.asarray(design["coded"], dtype=np.float64)
    if coded.ndim != 2 or coded.shape[1] != k or coded.shape[0] < 1:
        raise ValueError("%s: design coded matrix shape %s does not match %d factors" % (op, coded.shape, k))
    if not np.isfinite(coded).all():
        raise ValueError("%s: design coded matrix contains NaN or inf" % op)
    spec = _factor_spec([{"name": n, "lo": a, "hi": b, "unit": u, "scale": s}
                         for n, a, b, u, s in zip(design["factors"], design["lo"], design["hi"],
                                                  design.get("units") or [""] * k, design["scale"])], op)
    return spec


def _design_coded(design, op: str = "design") -> np.ndarray:
    """The validated coded matrix of a design (helper shared by the analysis ops)."""
    _spec_from_design(design, op)
    return np.asarray(design["coded"], dtype=np.float64)


def _int_arg(v, name: str, op: str, lo: int, hi: int) -> int:
    if isinstance(v, bool) or not isinstance(v, (int, np.integer, float, np.floating)):
        raise ValueError("%s: %s must be an integer, got %r" % (op, name, v))
    if float(v) != int(v):
        raise ValueError("%s: %s must be an integer, got %r" % (op, name, v))
    v = int(v)
    if not lo <= v <= hi:
        raise ValueError("%s: %s must be in %d..%d, got %d" % (op, name, lo, hi, v))
    return v


# --------------------------------------------------------------------------- #
# Latin hypercube                                                             #
# --------------------------------------------------------------------------- #
def _min_dist(u: np.ndarray) -> float:
    if u.shape[0] >= 512:
        from scipy.spatial import cKDTree
        return float(cKDTree(u).query(u, k=2)[0][:, 1].min())
    from scipy.spatial.distance import pdist
    return float(pdist(u).min())


def _min_dist_bounded(u: np.ndarray, upper: float, return_pairs: bool = False):
    """Minimum distance, stopping once the candidate cannot beat ``upper``."""
    best = np.inf
    pairs = 0
    for i in range(u.shape[0] - 1):
        d = np.sqrt(((u[i + 1:] - u[i]) ** 2).sum(axis=1))
        pairs += d.size
        row = float(d.min())
        if row < best:
            best = row
        if best <= upper:
            return (best, pairs) if return_pairs else best
    value = float(best)
    return (value, pairs) if return_pairs else value


def doe_lhs(n=10, factors=3, seed=0, maximin=0, centered=False) -> dict:
    """Latin hypercube design (McKay, Beckman & Conover 1979) -> ``design``.

    Each factor's range is cut into ``n`` equal strata and every stratum holds
    exactly one run, so each factor is sampled evenly however many factors there
    are (a random design of the same size leaves strata empty). Construction
    (McKay et al. 1979, section 2): for factor j draw an independent random
    permutation ``pi_j`` of ``0..n-1`` and put run i at
    ``u_ij = (pi_j(i) + U_ij) / n`` with ``U_ij ~ Uniform[0, 1)`` (``centered=True``
    uses the stratum mid-point, ``U = 1/2``). Coded value = ``2u - 1``.

    ``maximin=m`` (m >= 2) draws m independent hypercubes and keeps the one with the
    largest smallest inter-point distance (each candidate is still a Latin hypercube,
    so the stratum property is never traded away); ``0`` or ``1`` = one plain draw.

    Parameters: ``n`` runs (2..1e6), ``factors`` (int or factor list, see module
    docstring), ``seed`` (int, reproducible), ``maximin`` (0..1000 candidates),
    ``centered``.

    Returns a ``design`` whose ``meta`` holds ``strata_ok`` (every factor has one
    point per stratum — the defining property, checked on the returned matrix) and
    ``min_distance`` (in the unit cube).
    """
    op = "doe_lhs"
    n = _int_arg(n, "n", op, 2, MAX_RUNS)
    spec = _factor_spec(factors, op)
    k = len(spec["names"])
    maximin = _int_arg(maximin, "maximin", op, 0, 1000)
    if maximin >= 2 and n * n * k > 50_000_000:
        raise ValueError("%s: maximin needs n*n*k <= 5e7 (pairwise distances), got n=%d k=%d" % (op, n, k))
    rng = np.random.default_rng(seed)

    def one():
        perm = np.stack([rng.permutation(n) for _ in range(k)], axis=1).astype(np.float64)
        jitter = np.full((n, k), 0.5) if centered else rng.random((n, k))
        return (perm + jitter) / n

    if maximin < 2:
        u = one()
        md = _min_dist(u) if n * n * k <= 50_000_000 else float("nan")
    else:
        best, md = None, -1.0
        for _ in range(maximin):
            cand = one()
            d = _min_dist_bounded(cand, md)
            if d > md:
                best, md = cand, d
        u = best
    strata = np.floor(u * n).astype(np.int64)
    strata_ok = all(np.array_equal(np.sort(strata[:, j]), np.arange(n)) for j in range(k))
    if not strata_ok:                                       # pragma: no cover - construction guarantees it
        raise RuntimeError("%s: internal error, a stratum holds two points" % op)
    return _design("lhs", 2.0 * u - 1.0, spec,
                   source="McKay, Beckman & Conover 1979, Technometrics 21(2):239, doi:10.1080/00401706.1979.10489755",
                   meta={"maximin_candidates": maximin, "centered": bool(centered), "seed": seed,
                         "strata_ok": strata_ok, "min_distance": md})


# --------------------------------------------------------------------------- #
# orthogonal arrays (published tables)                                         #
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# published tables (copied, not generated)                                     #
# --------------------------------------------------------------------------- #
#: Taguchi orthogonal arrays as published, level symbols 1/2/3. Copied 2026-10-15 from the
#: University of York "Orthogonal Arrays (Taguchi Designs)" tables and checked row-for-row
#: against NIST Dataplot's L*.DAT files (Taguchi, System of Experimental Design, vol. 2):
#: L4/L8/L9/L12/L16/L27 identical; NIST's L18 is the 6^1 3^6 form, identical to the table
#: below after merging columns 1-2 into one six-level column. tests/test_multivar_doe.py
#: re-parses the NIST files (tests/data/doe_published/) on every run.
OA_PUBLISHED = {
    "L4": {"levels": [2, 2, 2], "rows": [
        [1, 1, 1],
        [1, 2, 2],
        [2, 1, 2],
        [2, 2, 1],
    ]},
    "L8": {"levels": [2, 2, 2, 2, 2, 2, 2], "rows": [
        [1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 2, 2, 2, 2],
        [1, 2, 2, 1, 1, 2, 2],
        [1, 2, 2, 2, 2, 1, 1],
        [2, 1, 2, 1, 2, 1, 2],
        [2, 1, 2, 2, 1, 2, 1],
        [2, 2, 1, 1, 2, 2, 1],
        [2, 2, 1, 2, 1, 1, 2],
    ]},
    "L9": {"levels": [3, 3, 3, 3], "rows": [
        [1, 1, 1, 1],
        [1, 2, 2, 2],
        [1, 3, 3, 3],
        [2, 1, 2, 3],
        [2, 2, 3, 1],
        [2, 3, 1, 2],
        [3, 1, 3, 2],
        [3, 2, 1, 3],
        [3, 3, 2, 1],
    ]},
    "L12": {"levels": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2], "rows": [
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2],
        [1, 1, 2, 2, 2, 1, 1, 1, 2, 2, 2],
        [1, 2, 1, 2, 2, 1, 2, 2, 1, 1, 2],
        [1, 2, 2, 1, 2, 2, 1, 2, 1, 2, 1],
        [1, 2, 2, 2, 1, 2, 2, 1, 2, 1, 1],
        [2, 1, 2, 2, 1, 1, 2, 2, 1, 2, 1],
        [2, 1, 2, 1, 2, 2, 2, 1, 1, 1, 2],
        [2, 1, 1, 2, 2, 2, 1, 2, 2, 1, 1],
        [2, 2, 2, 1, 1, 1, 1, 2, 2, 1, 2],
        [2, 2, 1, 2, 1, 2, 1, 1, 1, 2, 2],
        [2, 2, 1, 1, 2, 1, 2, 1, 2, 2, 1],
    ]},
    "L16": {"levels": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2], "rows": [
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2],
        [1, 1, 1, 2, 2, 2, 2, 1, 1, 1, 1, 2, 2, 2, 2],
        [1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1],
        [1, 2, 2, 1, 1, 2, 2, 1, 1, 2, 2, 1, 1, 2, 2],
        [1, 2, 2, 1, 1, 2, 2, 2, 2, 1, 1, 2, 2, 1, 1],
        [1, 2, 2, 2, 2, 1, 1, 1, 1, 2, 2, 2, 2, 1, 1],
        [1, 2, 2, 2, 2, 1, 1, 2, 2, 1, 1, 1, 1, 2, 2],
        [2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2],
        [2, 1, 2, 1, 2, 1, 2, 2, 1, 2, 1, 2, 1, 2, 1],
        [2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1],
        [2, 1, 2, 2, 1, 2, 1, 2, 1, 2, 1, 1, 2, 1, 2],
        [2, 2, 1, 1, 2, 2, 1, 1, 2, 2, 1, 1, 2, 2, 1],
        [2, 2, 1, 1, 2, 2, 1, 2, 1, 1, 2, 2, 1, 1, 2],
        [2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1, 1, 2],
        [2, 2, 1, 2, 1, 1, 2, 2, 1, 1, 2, 1, 2, 2, 1],
    ]},
    "L18": {"levels": [2, 3, 3, 3, 3, 3, 3, 3], "rows": [
        [1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 2, 2, 2, 2, 2, 2],
        [1, 1, 3, 3, 3, 3, 3, 3],
        [1, 2, 1, 1, 2, 2, 3, 3],
        [1, 2, 2, 2, 3, 3, 1, 1],
        [1, 2, 3, 3, 1, 1, 2, 2],
        [1, 3, 1, 2, 1, 3, 2, 3],
        [1, 3, 2, 3, 2, 1, 3, 1],
        [1, 3, 3, 1, 3, 2, 1, 2],
        [2, 1, 1, 3, 3, 2, 2, 1],
        [2, 1, 2, 1, 1, 3, 3, 2],
        [2, 1, 3, 2, 2, 1, 1, 3],
        [2, 2, 1, 2, 3, 1, 3, 2],
        [2, 2, 2, 3, 1, 2, 1, 3],
        [2, 2, 3, 1, 2, 3, 2, 1],
        [2, 3, 1, 3, 2, 3, 1, 2],
        [2, 3, 2, 1, 3, 1, 2, 3],
        [2, 3, 3, 2, 1, 2, 3, 1],
    ]},
    "L27": {"levels": [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3], "rows": [
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2],
        [1, 1, 1, 1, 3, 3, 3, 3, 3, 3, 3, 3, 3],
        [1, 2, 2, 2, 1, 1, 1, 2, 2, 2, 3, 3, 3],
        [1, 2, 2, 2, 2, 2, 2, 3, 3, 3, 1, 1, 1],
        [1, 2, 2, 2, 3, 3, 3, 1, 1, 1, 2, 2, 2],
        [1, 3, 3, 3, 1, 1, 1, 3, 3, 3, 2, 2, 2],
        [1, 3, 3, 3, 2, 2, 2, 1, 1, 1, 3, 3, 3],
        [1, 3, 3, 3, 3, 3, 3, 2, 2, 2, 1, 1, 1],
        [2, 1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2, 3],
        [2, 1, 2, 3, 2, 3, 1, 2, 3, 1, 2, 3, 1],
        [2, 1, 2, 3, 3, 1, 2, 3, 1, 2, 3, 1, 2],
        [2, 2, 3, 1, 1, 2, 3, 2, 3, 1, 3, 1, 2],
        [2, 2, 3, 1, 2, 3, 1, 3, 1, 2, 1, 2, 3],
        [2, 2, 3, 1, 3, 1, 2, 1, 2, 3, 2, 3, 1],
        [2, 3, 1, 2, 1, 2, 3, 3, 1, 2, 2, 3, 1],
        [2, 3, 1, 2, 2, 3, 1, 1, 2, 3, 3, 1, 2],
        [2, 3, 1, 2, 3, 1, 2, 2, 3, 1, 1, 2, 3],
        [3, 1, 3, 2, 1, 3, 2, 1, 3, 2, 1, 3, 2],
        [3, 1, 3, 2, 2, 1, 3, 2, 1, 3, 2, 1, 3],
        [3, 1, 3, 2, 3, 2, 1, 3, 2, 1, 3, 2, 1],
        [3, 2, 1, 3, 1, 3, 2, 2, 1, 3, 3, 2, 1],
        [3, 2, 1, 3, 2, 1, 3, 3, 2, 1, 1, 3, 2],
        [3, 2, 1, 3, 3, 2, 1, 1, 3, 2, 2, 1, 3],
        [3, 3, 2, 1, 1, 3, 2, 3, 2, 1, 2, 1, 3],
        [3, 3, 2, 1, 2, 1, 3, 1, 3, 2, 3, 2, 1],
        [3, 3, 2, 1, 3, 2, 1, 2, 1, 3, 1, 3, 2],
    ]},
}

#: where each array comes from (cited in the design's ``source``)
OA_SOURCES = {
    "L4": {"citation": "Taguchi, System of Experimental Design (1987), vol. 2; table as published by the University of York (www.york.ac.uk/depts/maths/tables/l4.gif) and NIST Dataplot L4.DAT", "nist_dat": "L4.DAT"},
    "L8": {"citation": "Taguchi, System of Experimental Design (1987), vol. 2; table as published by the University of York (www.york.ac.uk/depts/maths/tables/l8.gif) and NIST Dataplot L8.DAT", "nist_dat": "L8.DAT"},
    "L9": {"citation": "Taguchi, System of Experimental Design (1987), vol. 2; table as published by the University of York (www.york.ac.uk/depts/maths/tables/l9.gif) and NIST Dataplot L9.DAT", "nist_dat": "L9.DAT"},
    "L12": {"citation": "Taguchi, System of Experimental Design (1987), vol. 2; table as published by the University of York (www.york.ac.uk/depts/maths/tables/l12.gif) and NIST Dataplot L12.DAT", "nist_dat": "L12.DAT"},
    "L16": {"citation": "Taguchi, System of Experimental Design (1987), vol. 2; table as published by the University of York (www.york.ac.uk/depts/maths/tables/l16.htm) and NIST Dataplot L16.DAT", "nist_dat": "L16.DAT"},
    "L18": {"citation": "Taguchi, System of Experimental Design (1987), vol. 2; table as published by the University of York (www.york.ac.uk/depts/maths/tables/l18.gif) and NIST Dataplot L18.DAT", "nist_dat": "L18.DAT"},
    "L27": {"citation": "Taguchi, System of Experimental Design (1987), vol. 2; table as published by the University of York (www.york.ac.uk/depts/maths/tables/l27.htm) and NIST Dataplot L27.DAT", "nist_dat": "L27.DAT"},
}

#: Recommended 2^(k-p) generators: NIST/SEMATECH e-Handbook of Statistical Methods, section
#: 5.3.3.4.7, Table 3.17 (designs from Box, Hunter & Hunter 1978), letters without I.
#: (k, p) -> (resolution as published, generators). The resolution is recomputed from the
#: generators by doe_fractional_factorial and must equal the published one (a test pins it).
FF_NIST = {
    (3, 1): (3, ["C=AB"]),
    (4, 1): (4, ["D=ABC"]),
    (5, 1): (5, ["E=ABCD"]),
    (5, 2): (3, ["D=AB", "E=AC"]),
    (6, 1): (6, ["F=ABCDE"]),
    (6, 2): (4, ["E=ABC", "F=BCD"]),
    (6, 3): (3, ["D=AB", "E=AC", "F=BC"]),
    (7, 1): (7, ["G=ABCDEF"]),
    (7, 2): (4, ["F=ABCD", "G=ABDE"]),
    (7, 3): (4, ["E=ABC", "F=BCD", "G=ACD"]),
    (7, 4): (3, ["D=AB", "E=AC", "F=BC", "G=ABC"]),
    (8, 1): (8, ["H=ABCDEFG"]),
    (8, 2): (5, ["G=ABCD", "H=ABEF"]),
    (8, 3): (4, ["F=ABC", "G=ABD", "H=BCDE"]),
    (8, 4): (4, ["E=BCD", "F=ACD", "G=ABC", "H=ABD"]),
    (9, 2): (6, ["H=ACDFG", "J=BCEFG"]),
    (9, 3): (4, ["G=ABCD", "H=ACEF", "J=CDEF"]),
    (9, 4): (4, ["F=BCDE", "G=ACDE", "H=ABDE", "J=ABCE"]),
    (9, 5): (3, ["E=ABC", "F=BCD", "G=ACD", "H=ABD", "J=ABCD"]),
    (10, 3): (5, ["H=ABCG", "J=BCDE", "K=ACDF"]),
    (10, 4): (4, ["G=BCDF", "H=ACDF", "J=ABDE", "K=ABCE"]),
    (10, 5): (4, ["F=ABCD", "G=ABCE", "H=ABDE", "J=ACDE", "K=BCDE"]),
    (10, 6): (3, ["E=ABC", "F=BCD", "G=ACD", "H=ABD", "J=ABCD", "K=AB"]),
    (11, 4): (5, ["H=ABCG", "J=BCDE", "K=ACDF", "L=ABCDEFG"]),
    (11, 5): (4, ["G=CDE", "H=ABCD", "J=ABF", "K=BDEF", "L=ADEF"]),
    (11, 6): (4, ["F=ABC", "G=BCD", "H=CDE", "J=ACD", "K=ADE", "L=BDE"]),
    (11, 7): (3, ["E=ABC", "F=BCD", "G=ACD", "H=ABD", "J=ABCD", "K=AB", "L=AC"]),
    (15, 11): (3, ["E=AB", "F=AC", "G=AD", "H=BC", "J=BD", "K=CD", "L=ABC", "M=ABD", "N=ACD", "O=BCD", "P=ABCD"]),
}


def _oa_published(name: str, op: str) -> np.ndarray:
    key = str(name).upper()
    if key not in OA_PUBLISHED:
        raise ValueError("%s: unknown orthogonal array %r (have %s)" % (op, name, ", ".join(OA_PUBLISHED)))
    return np.asarray(OA_PUBLISHED[key]["rows"], dtype=np.int64)


def _level_codes(col: np.ndarray) -> np.ndarray:
    """Published symbols (1, 2[, 3]) -> coded −1, +1 or −1, 0, +1 (equally spaced)."""
    syms = np.unique(col)
    s = syms.size
    pos = np.searchsorted(syms, col)
    return -1.0 + 2.0 * pos / (s - 1)


def _contrast_basis(col: np.ndarray) -> np.ndarray:
    """Orthonormal basis of the main-effect space of one column (indicator space minus the mean)."""
    syms = np.unique(col)
    ind = (col[:, None] == syms[None, :]).astype(np.float64)
    ind -= ind.mean(axis=0, keepdims=True)
    u, s, _ = np.linalg.svd(ind, full_matrices=False)
    return u[:, s > 1e-9 * max(1.0, s.max())]


def _interaction_basis(ci: np.ndarray, cj: np.ndarray) -> np.ndarray:
    """Orthonormal basis of the i x j interaction space, orthogonal to the mean and both main effects."""
    bi, bj = _contrast_basis(ci), _contrast_basis(cj)
    prod = np.concatenate([(bi[:, a] * bj[:, b])[:, None]
                           for a in range(bi.shape[1]) for b in range(bj.shape[1])], axis=1)
    base = np.concatenate([np.ones((ci.size, 1)) / math.sqrt(ci.size), bi, bj], axis=1)
    prod = prod - base @ np.linalg.lstsq(base, prod, rcond=None)[0]
    u, s, _ = np.linalg.svd(prod, full_matrices=False)
    if s.size == 0 or s.max() < 1e-9:
        return np.zeros((ci.size, 0))
    return u[:, s > 1e-9 * s.max()]


def _oa_interaction_share(table: np.ndarray, i: int, j: int) -> np.ndarray:
    """Share of the i x j interaction that falls on each column (0..1 per column).

    ``||Q_m^T Q_ij||_F^2 / dim(ij)`` with Q orthonormal bases. A regular two-level array
    puts the whole interaction on one column (share 1); a regular three-level array
    splits it over two columns (0.5 each); a non-regular array (L12, L18) spreads it
    thinly over many columns (L12: 1/9 on each of the other nine).
    """
    qij = _interaction_basis(table[:, i], table[:, j])
    out = np.zeros(table.shape[1])
    if qij.shape[1] == 0:
        return out
    for m in range(table.shape[1]):
        if m in (i, j):
            continue
        qm = _contrast_basis(table[:, m])
        out[m] = float(np.sum((qm.T @ qij) ** 2) / qij.shape[1])
    return out


def _oa_strength2_ok(table: np.ndarray) -> bool:
    """True if every pair of columns shows every level pair equally often (strength-2 orthogonality)."""
    n = table.shape[0]
    for a, b in itertools.combinations(range(table.shape[1]), 2):
        sa, ia = np.unique(table[:, a], return_inverse=True)
        sb, ib = np.unique(table[:, b], return_inverse=True)
        if n % (sa.size * sb.size):
            return False
        want = n // (sa.size * sb.size)
        counts = np.bincount(ia * sb.size + ib, minlength=sa.size * sb.size)
        if not np.all(counts == want):
            return False
    return True


def doe_orthogonal_array(name="L9", factors=None, columns=None) -> dict:
    """Orthogonal array L4 / L8 / L9 / L12 / L16 / L18 / L27 from a published table -> ``design``.

    The arrays are **copied from published tables** (sources and the copy check in
    :data:`OA_SOURCES`), not generated: Taguchi's numbering of columns is what
    shop-floor literature and the linear graphs refer to, and a generated array with
    another column order would silently assign factors to interaction columns.
    Published level symbols 1, 2 (, 3) map to coded −1, +1 (, or −1, 0, +1).

    ``factors``: int / names / (name, lo, hi[, unit[, scale]]) (default: one factor per
    column). ``columns``: 1-based column numbers to assign the factors to, in order
    (default: the first k columns; for L18 column 1 is the two-level one).

    The returned ``alias`` lists, for every pair of assigned factors, the columns their
    interaction falls on and the share (see :func:`_oa_interaction_share`) — if such a
    column also carries an assigned factor, that main effect is confounded with the
    interaction. ``meta['strength2_ok']`` re-checks orthogonality on the table actually
    used, and ``meta['regular']`` says whether interactions land on whole columns.
    """
    op = "doe_orthogonal_array"
    table = _oa_published(name, op)
    key = str(name).upper()
    n, m = table.shape
    if factors is None:
        factors = m if columns is None else len(list(columns))
    spec = _factor_spec(factors, op)
    k = len(spec["names"])
    if columns is None:
        cols = list(range(k))
    else:
        cols = []
        for c in columns:
            ci = _int_arg(c, "column", op, 1, m) - 1
            cols.append(ci)
        if len(set(cols)) != len(cols):
            raise ValueError("%s: columns must not repeat, got %s" % (op, list(columns)))
    if len(cols) != k:
        raise ValueError("%s: %d factors but %d columns" % (op, k, len(cols)))
    if k > m:
        raise ValueError("%s: %s has %d columns, cannot hold %d factors" % (op, key, m, k))
    coded = np.stack([_level_codes(table[:, c]) for c in cols], axis=1)
    alias, shares = [], {}
    regular = True
    col_of = {c: spec["names"][t] for t, c in enumerate(cols)}
    for a, b in itertools.combinations(range(k), 2):
        sh = _oa_interaction_share(table, cols[a], cols[b])
        hits = [(int(c) + 1, float(sh[c])) for c in np.flatnonzero(sh > 1e-9)]
        shares["%s x %s" % (spec["names"][a], spec["names"][b])] = hits
        if any(abs(s - 1.0) > 1e-9 and abs(s - 0.5) > 1e-9 for _c, s in hits):
            regular = False
        conf = [(c, s) for c, s in hits if (c - 1) in col_of]
        if conf:
            alias.append("%s x %s falls on %s" % (
                spec["names"][a], spec["names"][b],
                ", ".join("column %d (%s, share %.3g)" % (c, col_of[c - 1], s) for c, s in conf)))
    src = OA_SOURCES.get(key, {})
    return _design("orthogonal_array", coded, spec, alias=alias, resolution=None,
                   source=src.get("citation", ""),
                   meta={"array": key, "columns": [c + 1 for c in cols], "table": table.copy(),
                         "interaction_columns": shares, "strength2_ok": _oa_strength2_ok(table),
                         "regular": regular, "published_levels": OA_PUBLISHED[key].get("levels")})


# --------------------------------------------------------------------------- #
# two-level fractional factorials                                             #
# --------------------------------------------------------------------------- #
_GEN = re.compile(r"^\s*([A-Z])\s*=\s*([+-]?)\s*([A-Z]+)\s*$")


def _parse_generators(gens, k: int, op: str):
    letters = LETTERS[:k]
    base_n = k - len(gens)
    if base_n < 1:
        raise ValueError("%s: %d generators for %d factors leaves no base factors" % (op, len(gens), k))
    base = letters[:base_n]
    added = {}
    for g in gens:
        mm = _GEN.match(str(g).upper())
        if not mm:
            raise ValueError("%s: generator %r must look like 'D=ABC' or 'E=-ABD'" % (op, g))
        new, sign, word = mm.group(1), mm.group(2), mm.group(3)
        if new not in letters[base_n:]:
            raise ValueError("%s: generator %r defines %r, expected one of the added factors %s"
                             % (op, g, new, letters[base_n:]))
        if new in added:
            raise ValueError("%s: factor %r is generated twice" % (op, new))
        if len(set(word)) != len(word) or any(ch not in base for ch in word) or len(word) < 2:
            raise ValueError("%s: generator %r must be a product of >= 2 distinct base factors %s"
                             % (op, g, base))
        added[new] = (-1 if sign == "-" else 1, word)
    if set(added) != set(letters[base_n:]):
        raise ValueError("%s: generators must define exactly %s" % (op, letters[base_n:]))
    words = [w for _s, w in added.values()]
    if len(set(frozenset(w) for w in words)) != len(words):
        raise ValueError("%s: two generators use the same word (the fraction would alias two factors)" % op)
    return base, added


def _word_str(s: frozenset) -> str:
    return "".join(sorted(s, key=LETTERS.index)) or "I"


def _defining_relation(added: dict):
    gens = [(frozenset(w) | {new}, sgn) for new, (sgn, w) in added.items()]
    rel = []
    for r in range(1, len(gens) + 1):
        for combo in itertools.combinations(gens, r):
            s, sign = frozenset(), 1
            for w, sg in combo:
                s = s ^ w
                sign *= sg
            rel.append((s, sign))
    return rel


def _ff_alias_table(added: dict, k: int, max_order: int = 2) -> dict:
    """``{effect: [(alias word, sign), ...]}`` for main effects and 2-factor interactions."""
    rel = _defining_relation(added)
    letters = LETTERS[:k]
    out = {}
    for order in range(1, max_order + 1):
        for eff in itertools.combinations(letters, order):
            e = frozenset(eff)
            out[_word_str(e)] = sorted(((_word_str(e ^ w), s) for w, s in rel),
                                       key=lambda t: (len(t[0]), t[0]))
    return out


def doe_fractional_factorial(factors=5, p=2, generators=None, center=0) -> dict:
    """Regular two-level fractional factorial 2^(k-p) from generators (Box & Hunter 1961) -> ``design``.

    The first ``k - p`` factors (letters A, B, C ... skipping I) form a full factorial
    in standard (Yates) order, A changing fastest. Each generator ``"D=ABC"`` sets an
    added factor's column to the product of base columns (``"E=-ABD"`` for the other
    half). ``generators=None`` takes the recommended generators for (k, p) from the
    NIST/SEMATECH e-Handbook table (:data:`FF_NIST`, 5.3.3.4.7 Table 3.17, after Box, Hunter
    & Hunter); ``p=0`` or ``generators=()`` gives the full factorial 2^k.

    The defining relation (every product of generator words ``I = ABCD = ...``), the
    **resolution** (length of the shortest word: III = main effects aliased with two-factor
    interactions, IV = main effects clear but 2fi aliased with each other, V = 2fi clear)
    and the alias table of main effects and two-factor interactions are returned in
    ``meta`` and ``alias``. They are computed from the generators, and the returned
    matrix is checked against them (each aliased pair of columns is identical up to sign).

    ``center`` adds centre runs (coded 0) for a curvature check; they do not change the
    alias structure.
    """
    op = "doe_fractional_factorial"
    spec = _factor_spec(factors, op)
    k = len(spec["names"])
    if k > len(LETTERS):
        raise ValueError("%s: at most %d factors" % (op, len(LETTERS)))
    p = _int_arg(p, "p", op, 0, k - 1)
    if generators is None:
        if p == 0:
            gens = []
        elif (k, p) in FF_NIST:
            gens = list(FF_NIST[(k, p)][1])
        else:
            raise ValueError("%s: no published generators for k=%d, p=%d (have %s) — pass generators explicitly"
                             % (op, k, p, sorted(FF_NIST)))
    else:
        gens = list(generators)
        if p and len(gens) != p:
            raise ValueError("%s: p=%d but %d generators given" % (op, p, len(gens)))
    center = _int_arg(center, "center", op, 0, 1000)
    base, added = _parse_generators(gens, k, op) if gens else (LETTERS[:k], {})
    nb = len(base)
    if 2 ** nb > MAX_RUNS:
        raise ValueError("%s: 2^%d base runs exceeds the cap" % (op, nb))
    runs = 2 ** nb
    cols = {}
    idx = np.arange(runs)
    for b, ch in enumerate(base):
        cols[ch] = np.where((idx >> b) & 1, 1.0, -1.0)      # A fastest (Yates order)
    for new, (sgn, w) in added.items():
        c = np.ones(runs)
        for ch in w:
            c = c * cols[ch]
        cols[new] = sgn * c
    coded = np.stack([cols[ch] for ch in LETTERS[:k]], axis=1)
    rel = _defining_relation(added) if added else []
    resolution = min((len(w) for w, _s in rel), default=None)
    table = _ff_alias_table(added, k) if added else {}
    # self-check: the matrix must honour every word of the defining relation
    for w, s in rel:
        prod = np.ones(runs)
        for ch in w:
            prod = prod * cols[ch]
        if not np.allclose(prod, s):                          # pragma: no cover - construction guarantees it
            raise RuntimeError("%s: internal error, word %s is not constant" % (op, _word_str(w)))
    alias = []
    names = dict(zip(LETTERS[:k], spec["names"]))

    def nm(word):
        return "*".join(names[ch] for ch in word)

    for eff, lst in table.items():
        al = [("-" if s < 0 else "") + nm(w) for w, s in lst if len(w) <= 2]
        if al:
            alias.append("%s = %s" % (nm(eff), " = ".join(al)))
    if center:
        coded = np.concatenate([coded, np.zeros((center, k))], axis=0)
    roman = {3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII", 8: "VIII"}
    return _design("fractional_factorial", coded, spec, alias=alias, resolution=resolution,
                   source="Box & Hunter 1961, Technometrics 3(3):311, doi:10.1080/00401706.1961.10489951",
                   meta={"letters": names, "generators": list(gens),
                         "defining_relation": ["I"] + [("-" if s < 0 else "") + _word_str(w) for w, s in rel],
                         "resolution_roman": roman.get(resolution, "full" if resolution is None else str(resolution)),
                         "alias_table": table, "n_factorial": runs, "n_center": center})


# --------------------------------------------------------------------------- #
# response-surface designs                                                    #
# --------------------------------------------------------------------------- #
def doe_central_composite(factors=3, alpha="rotatable", center=4, generators=None, inscribed=False) -> dict:
    """Central composite design (Box & Wilson 1951) -> ``design``.

    Three parts: the two-level factorial (full 2^k, or a fraction from ``generators``
    as in :func:`doe_fractional_factorial` — it must be resolution V or better so that
    every two-factor interaction of the quadratic model stays estimable), 2k axial
    points at ±alpha on each axis, and ``center`` centre points.

    ``alpha``: ``"rotatable"`` — alpha = F^(1/4) with F the number of factorial points
    (the prediction variance then depends only on the distance from the centre;
    Box & Hunter 1957), ``"face"`` — alpha = 1 (face-centred, three levels only),
    ``"spherical"`` — alpha = sqrt(k), or a number > 0.

    ``inscribed=True`` shrinks the whole design by 1/alpha so that the axial points sit at
    the ends of the range (lo/hi) and the factorial points inside it; otherwise the
    factorial points sit at lo/hi and the axial points go **outside** the range —
    ``meta['outside_range']`` then names the factors whose natural values leave lo..hi
    (check that the bench can be set there).
    """
    op = "doe_central_composite"
    spec = _factor_spec(factors, op)
    k = len(spec["names"])
    if k < 2:
        raise ValueError("%s: needs at least 2 factors" % op)
    center = _int_arg(center, "center", op, 0, 1000)
    gens = list(generators) if generators else []
    frac = doe_fractional_factorial(k, 0, gens) if gens else doe_fractional_factorial(k, 0)
    if gens and (frac["resolution"] or 99) < 5:
        raise ValueError("%s: the factorial part has resolution %s; a quadratic model needs >= V "
                         "(two-factor interactions would be aliased: %s)"
                         % (op, frac["meta"]["resolution_roman"], "; ".join(frac["alias"][:4])))
    fac = frac["coded"]
    F = fac.shape[0]
    if isinstance(alpha, str):
        if alpha == "rotatable":
            a = F ** 0.25
        elif alpha == "face":
            a = 1.0
        elif alpha == "spherical":
            a = math.sqrt(k)
        else:
            raise ValueError("%s: alpha must be 'rotatable', 'face', 'spherical' or a number, got %r" % (op, alpha))
    else:
        try:
            a = float(alpha)
        except (TypeError, ValueError):
            raise ValueError("%s: alpha must be 'rotatable', 'face', 'spherical' or a number" % op) from None
        if not (math.isfinite(a) and a > 0):
            raise ValueError("%s: alpha must be > 0, got %r" % (op, alpha))
    ax = np.zeros((2 * k, k))
    for j in range(k):
        ax[2 * j, j] = -a
        ax[2 * j + 1, j] = a
    coded = np.concatenate([fac, ax, np.zeros((center, k))], axis=0)
    if inscribed:
        coded = coded / a
    outside = [spec["names"][j] for j in range(k) if np.abs(coded[:, j]).max() > 1 + 1e-12]
    return _design("central_composite", coded, spec, alias=frac["alias"], resolution=frac["resolution"],
                   source="Box & Wilson 1951, JRSS B 13(1):1, doi:10.1111/j.2517-6161.1951.tb00067.x",
                   meta={"alpha": a, "alpha_rule": alpha if isinstance(alpha, str) else "given",
                         "n_factorial": F, "n_axial": 2 * k, "n_center": center,
                         "inscribed": bool(inscribed), "outside_range": outside,
                         "generators": gens})


def doe_box_behnken(factors=3, center=3) -> dict:
    """Box-Behnken design (Box & Behnken 1960) for 3, 4 or 5 factors -> ``design``.

    Three levels per factor and no run at a corner of the cube: for every pair of
    factors, a 2^2 factorial (±1, ±1) with all other factors at 0, plus ``center``
    centre runs — 12, 24 and 40 edge runs for k = 3, 4, 5 (the pair construction of
    Box & Behnken's table for these k). Useful when the extreme corners are unsafe or
    cannot be set. k = 4 is rotatable. Larger k use incomplete-block constructions
    that are not reproduced here and are refused.
    """
    op = "doe_box_behnken"
    spec = _factor_spec(factors, op)
    k = len(spec["names"])
    if k not in (3, 4, 5):
        raise ValueError("%s: supports 3, 4 or 5 factors (the pairwise construction), got %d" % (op, k))
    center = _int_arg(center, "center", op, 0, 1000)
    rows = []
    for i, j in itertools.combinations(range(k), 2):
        for si in (-1.0, 1.0):
            for sj in (-1.0, 1.0):
                r = np.zeros(k)
                r[i], r[j] = si, sj
                rows.append(r)
    coded = np.concatenate([np.asarray(rows), np.zeros((center, k))], axis=0)
    return _design("box_behnken", coded, spec,
                   source="Box & Behnken 1960, Technometrics 2(4):455, doi:10.1080/00401706.1960.10489912",
                   meta={"n_edge": len(rows), "n_center": center})


# --------------------------------------------------------------------------- #
# encode / decode                                                             #
# --------------------------------------------------------------------------- #
def doe_encode(natural=None, factors=None) -> dict:
    """Natural-unit settings (n, k) -> ``design`` with coded values (−1..+1 = lo..hi).

    Use it to bring runs that were *not* planned here (a historical log, a hand-made
    plan) into the same coded frame the analysis ops read. ``factors`` gives the
    ranges (and per-factor ``"log"`` scale: coded = position of log10(x) between
    log10(lo) and log10(hi)). Values outside lo..hi are kept (coded beyond ±1) and named
    in ``meta['outside_range']``.
    """
    op = "doe_encode"
    if natural is None:
        natural = np.array([[0.0, 0.0], [1.0, 1.0]])
        factors = factors if factors is not None else [("x1", 0.0, 1.0), ("x2", 0.0, 1.0)]
    try:
        nat = np.asarray(natural, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("%s: natural must be a numeric (n, k) matrix" % op) from None
    if nat.ndim == 1:
        nat = nat[:, None]
    if nat.ndim != 2 or nat.shape[0] < 1:
        raise ValueError("%s: natural must be (n, k), got shape %s" % (op, nat.shape))
    if not np.isfinite(nat).all():
        raise ValueError("%s: natural contains NaN or inf" % op)
    if factors is None:
        raise ValueError("%s: factors (with lo, hi) are required — the coding is defined by the ranges, "
                         "not guessed from the data" % op)
    spec = _factor_spec(factors, op)
    if len(spec["names"]) != nat.shape[1]:
        raise ValueError("%s: %d factors but natural has %d columns" % (op, len(spec["names"]), nat.shape[1]))
    coded = _to_coded(nat, spec, op)
    d = _design("encoded", coded, spec, source="doe_encode",
                meta={"outside_range": [spec["names"][j] for j in range(coded.shape[1])
                                        if np.abs(coded[:, j]).max() > 1 + 1e-12]})
    d["natural"] = nat.copy()                    # exactly what was given (no round trip)
    return d


def doe_decode(design=None, coded=None) -> np.ndarray:
    """``design`` -> natural-unit matrix (n, k); or decode any coded point(s) with its ranges.

    ``coded=None`` returns the design's natural matrix recomputed from its coded matrix
    (so a hand-edited ``natural`` cannot drift from ``coded``). Pass ``coded`` (k,) or
    (m, k) — e.g. a stationary point from :func:`multivar.rsm_fit` — to map it to bench
    settings with the same ranges and scales.
    """
    op = "doe_decode"
    if design is None:
        design = doe_box_behnken(3)
    spec = _spec_from_design(design, op)
    k = len(spec["names"])
    if coded is None:
        c = np.asarray(design["coded"], dtype=np.float64)
    else:
        try:
            c = np.asarray(coded, dtype=np.float64)
        except (TypeError, ValueError):
            raise ValueError("%s: coded must be numeric" % op) from None
        if c.ndim == 1:
            c = c[None, :]
        if c.ndim != 2 or c.shape[1] != k:
            raise ValueError("%s: coded must be (k,) or (m, k) with k=%d, got shape %s" % (op, k, c.shape))
        if not np.isfinite(c).all():
            raise ValueError("%s: coded contains NaN or inf" % op)
    return _to_natural(c, spec)
