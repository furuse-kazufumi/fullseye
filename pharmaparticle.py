# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""顕微鏡の粒子表と校正表から、採否・3 基準の分布・分位点・来歴を一体で返す。

Microscopy particle-size reporting needs decisions that a unit conversion alone cannot make:
border objects, unresolved overlaps, calibration validity, uncertainty, and the distinction
between number-, area-, and volume-weighted distributions. This module keeps those decisions
in one fail-closed operator. It does not claim conformity with USP <776>, <788>, or <429>.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import date
from statistics import NormalDist

import numpy as np

import measuring1d
import pod

__all__ = ["particle_size_distribution"]

DEFAULT_BIN_COUNT = 12
DEFAULT_BOOTSTRAP_SAMPLES = 2000
DEFAULT_CONFIDENCE = 0.95
DEFAULT_SEED = 776
# A percentile CI reports a distribution, not a single particle.  Thirty is the
# predeclared lower limit used by this screening op; below it resampling merely
# replays a handful of particles and is deliberately reported as insufficient.
MIN_EFFECTIVE_PARTICLES = 30
_BORDER_POLICIES = ("include", "exclude", "correct")
_SPLIT_STATUSES = ("isolated", "split", "unsplit", "ambiguous")
_PARTICLE_UNITS = {"diameter_unit": "px", "area_unit": "px2"}
_SCALE_UNIT = "mm/px"


def _column(table, key, n=None):
    """Read one 1-D table column / 1 次元の表の列を読む。"""
    if not isinstance(table, dict) or key not in table:
        raise ValueError("particle_size_distribution: particles must contain column %r" % key)
    value = np.asarray(table[key])
    if value.ndim != 1:
        raise ValueError("particle_size_distribution: particles[%r] must be a 1-D column" % key)
    if n is not None and value.size != n:
        raise ValueError("particle_size_distribution: particle columns have different lengths")
    return value


def _numbers(table, key, n, *, positive=False, nonnegative=False):
    """Read a finite numeric column / 有限な数値列を読む。"""
    try:
        value = _column(table, key, n).astype(np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError("particle_size_distribution: particles[%r] must be numeric" % key) from exc
    if not np.all(np.isfinite(value)):
        raise ValueError("particle_size_distribution: particles[%r] contains NaN or Inf" % key)
    if positive and np.any(value <= 0.0):
        raise ValueError("particle_size_distribution: particles[%r] must be > 0" % key)
    if nonnegative and np.any(value < 0.0):
        raise ValueError("particle_size_distribution: particles[%r] must be >= 0" % key)
    return value


def _one(table, key):
    """Read one calibration-table cell / 校正表の単一セルを読む。"""
    if not isinstance(table, dict) or key not in table:
        raise ValueError("particle_size_distribution: calibration must contain %r" % key)
    value = table[key]
    if isinstance(value, np.ndarray):
        if value.size != 1:
            raise ValueError("particle_size_distribution: calibration[%r] must have one value" % key)
        return value.reshape(-1)[0].item()
    if isinstance(value, (list, tuple)):
        if len(value) != 1:
            raise ValueError("particle_size_distribution: calibration[%r] must have one value" % key)
        return value[0]
    return value


def _finite(table, key, *, positive=False, nonnegative=False):
    """Read a finite calibration number / 校正表の有限値を読む。"""
    raw = _one(table, key)
    if isinstance(raw, (bool, np.bool_)):
        raise ValueError("particle_size_distribution: calibration[%r] must be numeric" % key)
    try:
        value = float(raw)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("particle_size_distribution: calibration[%r] must be numeric" % key) from exc
    if not math.isfinite(value) or (positive and value <= 0.0) or (nonnegative and value < 0.0):
        relation = "> 0" if positive else ">= 0" if nonnegative else "finite"
        raise ValueError("particle_size_distribution: calibration[%r] must be %s" % (key, relation))
    return value


def _day(value, name):
    """Parse an ISO date only / 日付は ISO 形式だけを受ける。"""
    if not isinstance(value, str):
        raise ValueError("particle_size_distribution: %s must be an ISO date YYYY-MM-DD" % name)
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("particle_size_distribution: %s must be an ISO date YYYY-MM-DD" % name) from exc


def _jsonable(value):
    """Canonical JSON value for provenance / 来歴ハッシュ用の値。"""
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError("particle_size_distribution: provenance value is not JSON-safe")


def _sha256(value):
    """SHA-256 of canonical UTF-8 JSON / 正規 UTF-8 JSON の SHA-256。"""
    payload = json.dumps(_jsonable(value), ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _weighted_midpoint_dx(diameters, weights, q):
    """Weighted empirical-midpoint Dx / 重み付き経験分布の中点規約による Dx。"""
    order = np.argsort(diameters, kind="mergesort")
    d, w = np.asarray(diameters, np.float64)[order], np.asarray(weights, np.float64)[order]
    unique, inverse = np.unique(d, return_inverse=True)
    summed = np.bincount(inverse, weights=w, minlength=unique.size)
    if unique.size == 1:
        return float(unique[0])
    # Each observed particle mass is centred at its diameter.  Unlike lower
    # cumulative interpolation, this cannot shift every percentile one bin low.
    positions = (np.cumsum(summed) - 0.5 * summed) / summed.sum()
    return float(np.interp(float(q) / 100.0, positions, unique,
                           left=unique[0], right=unique[-1]))


def _effective_particles(weights):
    """Kish effective n for unequal count weights / 不等重みの Kish 有効標本数。"""
    weight = np.asarray(weights, np.float64)
    return float(weight.sum() ** 2 / np.square(weight).sum())


def _edges(diameters, supplied):
    """Validate or derive fixed physical bins / 物理径の固定ビン端。"""
    if supplied is not None:
        try:
            out = np.asarray(supplied, np.float64)
        except (TypeError, ValueError) as exc:
            raise ValueError("particle_size_distribution: bin_edges must be numeric") from exc
        if (out.ndim != 1 or out.size < 2 or not np.all(np.isfinite(out))
                or np.any(out <= 0.0) or np.any(np.diff(out) <= 0.0)):
            raise ValueError("particle_size_distribution: bin_edges must be positive and strictly increasing")
        if out[0] > diameters.min() or out[-1] < diameters.max():
            raise ValueError("particle_size_distribution: bin_edges do not cover accepted diameters")
        return out
    lo, hi = float(diameters.min()), float(diameters.max())
    if lo == hi:
        return np.geomspace(lo * 0.95, hi * 1.05, DEFAULT_BIN_COUNT + 1)
    return np.geomspace(lo, np.nextafter(hi, math.inf), DEFAULT_BIN_COUNT + 1)


def particle_size_distribution(particles, calibration, *, border_policy="exclude",
                               measurement_date=None, bin_edges=None,
                               confidence=DEFAULT_CONFIDENCE,
                               bootstrap_samples=DEFAULT_BOOTSTRAP_SAMPLES,
                               seed=DEFAULT_SEED):
    """粒子表を校正し、採否理由、3 基準のビン、D10/D50/D90 と信頼区間、来歴を返す。

    D10/D50/D90 は、重複径を重みごとに集約した**重み付き経験分布の中点規約**で求める。
    ``unsplit`` と ``ambiguous`` の重なりは常に除外し、1 粒として黙って数えない。
    上流の ``blob_split`` と ``blob_count_interval`` に由来する成分 ID、分割根拠、
    個数区間、決定可否が全行で必須であり、未決定行は ``ambiguous`` として除外する。
    ``border_policy="correct"`` は端粒子について ``border_inclusion_probability``、
    ``border_corrected_diameter_px``、``border_corrected_area_px2`` が揃う場合だけ
    Horvitz--Thompson の個数重み ``1/p`` と補正寸法を使う。尺度の標準不確かさは
    各径へ線形伝播し、分位点では決定的 bootstrap の標本区間と尺度区間を合成する。
    有効粒子数が ``MIN_EFFECTIVE_PARTICLES`` 未満なら、母集団分位点を主張せず
    ``insufficient_sample`` を返す。bootstrap 区間は独立粒子の経験分布を再標本化する
    条件付き区間であり、端補正時は設計ベース保証ではなく実験的な不確かさである。

    Parameters
    ----------
    particles : table (dict of 1-D columns)
        必須列は ``object_id``、``diameter_px``、``area_px2``、``diameter_unit="px"``、
        ``area_unit="px2"``、``touches_border``、``split_status``、``component_id``、
        ``split_evidence``、``count_interval_lo``、``count_interval_hi``、``count_determined``。
        状態は ``isolated`` / ``split`` / ``unsplit`` / ``ambiguous``。
        ``major_axis_px`` と ``minor_axis_px`` は任意。
    calibration : table (one-row dict)
        ``scale`` = {``value``, ``unit="mm/px"``, ``standard_uncertainty``} と
        ``calibrator_id``、``calibrated_at``、``valid_until``。``pixel_to_world`` と同じ
        mm/px 契約だけを許す。
    border_policy : {"include", "exclude", "correct"}
        端粒子を切れた測定のまま含める、除外する、必要情報を使って補正する方針。
    measurement_date : str
        測定日 ``YYYY-MM-DD``。省略不可。校正日より前、期限後なら拒否する。
    bin_edges : sequence or None
        物理径のビン端。None なら採用径の範囲に固定した対数 12 ビン。
    confidence : float
        両側信頼水準。
    bootstrap_samples : int
        決定的 bootstrap の反復数。200 以上。
    seed : int
        bootstrap の乱数種。

    Returns
    -------
    table
        ``particle_rows``、``counts``、``bins``(number / area / volume)、``quantiles``、
        ``calibration_provenance``、``accepted_proportion_ci`` を持つ。

    Raises
    ------
    ValueError
        空表、列不整合、非有限・非正、補正情報不足、校正期間外、採用粒子ゼロを拒否する。

    English: combine microscopy particles and a calibration record into an auditable report.
    Unresolved overlaps are excluded; border correction is refused without inclusion probability
    and corrected dimensions. Number, area and volume bases remain distinct and are not treated
    as an interchangeable laser-diffraction result.

    Examples
    --------
    >>> p = {"object_id": ["a"] * 30, "diameter_px": [10.] * 30, "area_px2": [78.5] * 30,
    ...      "diameter_unit": "px", "area_unit": "px2", "touches_border": [False] * 30,
    ...      "split_status": ["isolated"] * 30, "component_id": ["c%d" % i for i in range(30)],
    ...      "split_evidence": ["blob_count_interval" ] * 30, "count_interval_lo": [1] * 30,
    ...      "count_interval_hi": [1] * 30, "count_determined": [True] * 30}
    >>> c = {"scale": {"value": .002, "unit": "mm/px", "standard_uncertainty": .00002},
    ...      "calibrator_id": "SM-01", "calibrated_at": "2026-01-01", "valid_until": "2026-12-31"}
    >>> r = particle_size_distribution(p, c, measurement_date="2026-06-01", bootstrap_samples=200)
    >>> r["counts"]["accepted_observed"], r["particle_rows"][0]["diameter"]
    (30, 0.02)
    """
    op = "particle_size_distribution"
    if border_policy not in _BORDER_POLICIES:
        raise ValueError("%s: border_policy must be one of %r" % (op, _BORDER_POLICIES))
    if measurement_date is None:
        raise ValueError("%s: measurement_date is required" % op)
    measured = _day(measurement_date, "measurement_date")

    scale_record = _one(calibration, "scale")
    if not isinstance(scale_record, dict):
        raise ValueError("%s: calibration['scale'] must be a unit-tagged table" % op)
    scale = _finite(scale_record, "value", positive=True)
    scale_u = _finite(scale_record, "standard_uncertainty", nonnegative=True)
    unit_raw = _one(scale_record, "unit")
    if unit_raw != _SCALE_UNIT:
        raise ValueError("%s: calibration['scale']['unit'] must be 'mm/px'" % op)
    calibrator = _one(calibration, "calibrator_id")
    if not isinstance(calibrator, str) or not calibrator.strip():
        raise ValueError("%s: calibration['calibrator_id'] must be a non-empty string" % op)
    calibrated_raw, valid_raw = _one(calibration, "calibrated_at"), _one(calibration, "valid_until")
    calibrated, valid = _day(calibrated_raw, "calibrated_at"), _day(valid_raw, "valid_until")
    if valid < calibrated or not calibrated <= measured <= valid:
        raise ValueError("%s: calibration is not valid on measurement_date" % op)

    if isinstance(confidence, (bool, np.bool_)):
        raise ValueError("%s: confidence must be in (0, 1)" % op)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("%s: confidence must be in (0, 1)" % op) from exc
    if not math.isfinite(confidence) or not 0.0 < confidence < 1.0:
        raise ValueError("%s: confidence must be in (0, 1)" % op)
    if (isinstance(bootstrap_samples, (bool, np.bool_))
            or not isinstance(bootstrap_samples, (int, np.integer)) or bootstrap_samples < 200):
        raise ValueError("%s: bootstrap_samples must be an integer >= 200" % op)
    if isinstance(seed, (bool, np.bool_)) or not isinstance(seed, (int, np.integer)):
        raise ValueError("%s: seed must be an integer" % op)

    ids = _column(particles, "object_id")
    n = int(ids.size)
    if n == 0:
        raise ValueError("%s: particles is empty" % op)
    ids = [str(v) for v in ids.tolist()]
    if any(not v for v in ids) or len(set(ids)) != n:
        raise ValueError("%s: object_id values must be non-empty and unique" % op)
    for key, expected in _PARTICLE_UNITS.items():
        value = _one(particles, key)
        if value != expected:
            raise ValueError("%s: particles[%r] must be %r" % (op, key, expected))
    diameter_px = _numbers(particles, "diameter_px", n, positive=True)
    area_px2 = _numbers(particles, "area_px2", n, positive=True)
    touches_raw = _column(particles, "touches_border", n)
    if not all(isinstance(v, (bool, np.bool_)) for v in touches_raw.tolist()):
        raise ValueError("%s: touches_border must contain booleans" % op)
    touches = touches_raw.astype(bool)
    statuses = [str(v) for v in _column(particles, "split_status", n).tolist()]
    unknown = sorted(set(statuses) - set(_SPLIT_STATUSES))
    if unknown:
        raise ValueError("%s: unknown split_status values %r" % (op, unknown))
    component = [str(v) for v in _column(particles, "component_id", n).tolist()]
    evidence = [str(v) for v in _column(particles, "split_evidence", n).tolist()]
    if any(not value for value in component) or any(not value for value in evidence):
        raise ValueError("%s: component_id and split_evidence must be non-empty" % op)
    interval_lo = _numbers(particles, "count_interval_lo", n, positive=True)
    raw_hi = _column(particles, "count_interval_hi", n).tolist()
    try:
        interval_hi = np.asarray([np.nan if value is None else float(value) for value in raw_hi], np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError("%s: count_interval_hi must be positive or None" % op) from exc
    if np.any(np.isinf(interval_hi)) or np.any(interval_hi[~np.isnan(interval_hi)] <= 0.0):
        raise ValueError("%s: count_interval_hi must be positive or None" % op)
    determined_raw = _column(particles, "count_determined", n)
    if not all(isinstance(v, (bool, np.bool_)) for v in determined_raw.tolist()):
        raise ValueError("%s: count_determined must contain booleans" % op)
    determined = determined_raw.astype(bool)
    if np.any(interval_hi[~np.isnan(interval_hi)] < interval_lo[~np.isnan(interval_hi)]):
        raise ValueError("%s: count_interval_hi must be >= count_interval_lo" % op)
    if any((not ok and status != "ambiguous") for ok, status in zip(determined, statuses)):
        raise ValueError("%s: undetermined count_interval rows must be split_status='ambiguous'" % op)
    if any((ok and (not math.isfinite(hi) or lo != hi)) for ok, lo, hi in zip(determined, interval_lo, interval_hi)):
        raise ValueError("%s: determined count_interval rows must have equal bounds" % op)

    major = _numbers(particles, "major_axis_px", n, positive=True) if "major_axis_px" in particles else None
    minor = _numbers(particles, "minor_axis_px", n, positive=True) if "minor_axis_px" in particles else None
    if (major is None) != (minor is None) or (major is not None and np.any(major < minor)):
        raise ValueError("%s: major/minor axes must be paired and major_axis_px >= minor_axis_px" % op)

    used_d, used_a, count_weight = diameter_px.copy(), area_px2.copy(), np.ones(n)
    correction_provenance = None
    if border_policy == "correct" and np.any(touches):
        required = ("border_inclusion_probability", "border_inclusion_probability_uncertainty",
                    "border_corrected_diameter_px", "border_corrected_diameter_uncertainty_px",
                    "border_corrected_area_px2", "border_corrected_area_uncertainty_px2",
                    "border_correction_provenance")
        missing = [key for key in required if key not in particles]
        if missing:
            raise ValueError("%s: border correction requires columns %r" % (op, missing))
        prob = _numbers(particles, required[0], n, positive=True)
        prob_u = _numbers(particles, required[1], n, nonnegative=True)
        corr_d = _numbers(particles, required[2], n, positive=True)
        corr_d_u = _numbers(particles, required[3], n, nonnegative=True)
        corr_a = _numbers(particles, required[4], n, positive=True)
        corr_a_u = _numbers(particles, required[5], n, nonnegative=True)
        correction_provenance = _one(particles, required[6])
        if not isinstance(correction_provenance, dict) or not all(
                key in correction_provenance for key in ("view_shape", "inclusion_probability_method", "correction_method")):
            raise ValueError("%s: border_correction_provenance must state view_shape, inclusion_probability_method, correction_method" % op)
        if np.any(prob > 1.0):
            raise ValueError("%s: border_inclusion_probability must be <= 1" % op)
        used_d[touches], used_a[touches], count_weight[touches] = corr_d[touches], corr_a[touches], 1.0 / prob[touches]

    accepted = np.ones(n, bool)
    reasons = []
    for i, status in enumerate(statuses):
        if status in ("unsplit", "ambiguous"):
            accepted[i] = False
            reasons.append("overlap_%s_excluded" % status)
        elif touches[i] and border_policy == "exclude":
            accepted[i] = False
            reasons.append("border_excluded")
        elif touches[i] and border_policy == "correct":
            reasons.append("accepted_border_corrected")
        elif touches[i]:
            reasons.append("accepted_border_included_truncated")
        else:
            reasons.append("accepted_overlap_split" if status == "split" else "accepted_isolated")
    if not np.any(accepted):
        raise ValueError("%s: no particle remains after decisions" % op)

    z = NormalDist().inv_cdf(0.5 + confidence / 2.0)
    scale_lo, scale_hi = scale - z * scale_u, scale + z * scale_u
    if scale_lo <= 0.0:
        raise ValueError("%s: calibration uncertainty interval includes a non-positive scale" % op)
    unit = "mm"
    diameters = np.array([measuring1d.pixel_to_world(v, scale) for v in used_d])
    idx = np.flatnonzero(accepted)
    d, dpx, cw, area = diameters[idx], used_d[idx], count_weight[idx], used_a[idx]
    weights = {"number": cw, "area": cw * area, "volume": cw * dpx ** 3}
    bin_edges = _edges(d, bin_edges)
    bins = {"edges": bin_edges, "unit": unit}
    for basis, weight in weights.items():
        hist = np.histogram(d, bins=bin_edges, weights=weight)[0].astype(float)
        bins[basis] = hist / hist.sum()

    effective_n = _effective_particles(cw)
    rng = np.random.default_rng(int(seed))
    # Equal-probability row bootstrap is conditional on observed particles.  It
    # describes sampling uncertainty for the declared particle population; it is
    # not a design-based guarantee for experimental border correction.
    draws = rng.integers(0, idx.size, size=(int(bootstrap_samples), idx.size), endpoint=False)
    alpha = (1.0 - confidence) / 2.0
    quantiles = {}
    for basis, weight in weights.items():
        quantiles[basis] = {}
        for q in (10, 50, 90):
            key = "D%d" % q
            if effective_n < MIN_EFFECTIVE_PARTICLES:
                quantiles[basis][key] = {"status": "insufficient_sample", "value": None,
                                         "ci_lower": None, "ci_upper": None, "unit": unit,
                                         "effective_particles": effective_n,
                                         "minimum_effective_particles": MIN_EFFECTIVE_PARTICLES}
                continue
            sample = np.array([_weighted_midpoint_dx(dpx[take], weight[take], q) for take in draws])
            lo, hi = np.quantile(sample, [alpha, 1.0 - alpha])
            quantiles[basis][key] = {
                "status": "estimated", "value": _weighted_midpoint_dx(dpx, weight, q) * scale,
                "ci_lower": float(lo * scale_lo), "ci_upper": float(hi * scale_hi), "unit": unit,
                "effective_particles": effective_n, "minimum_effective_particles": MIN_EFFECTIVE_PARTICLES,
            }

    rows = []
    for i in range(n):
        row = {"object_id": ids[i], "accepted": bool(accepted[i]), "reason": reasons[i],
               "split_status": statuses[i], "touches_border": bool(touches[i]),
               "diameter_px_input": float(diameter_px[i]), "diameter_px_used": float(used_d[i]),
               "diameter": float(diameters[i]), "diameter_uncertainty": float(used_d[i] * scale_u),
               "diameter_ci_lower": float(used_d[i] * scale_lo),
               "diameter_ci_upper": float(used_d[i] * scale_hi), "unit": unit,
               "count_weight": float(count_weight[i]) if accepted[i] else 0.0}
        if major is not None:
            row.update(major_axis=float(major[i] * scale), minor_axis=float(minor[i] * scale))
        rows.append(row)

    counts = {"input": n, "accepted_observed": int(accepted.sum()),
              "accepted_corrected": float(count_weight[accepted].sum()),
              "border_total": int(touches.sum()), "border_excluded": int(np.sum(touches & ~accepted)),
              "overlap_split_accepted": int(sum(a and s == "split" for a, s in zip(accepted, statuses))),
              "overlap_unsplit_excluded": statuses.count("unsplit"),
              "overlap_ambiguous_excluded": statuses.count("ambiguous")}
    record = {"scale": {"value": scale, "unit": unit_raw, "standard_uncertainty": scale_u},
              "calibrator_id": calibrator, "calibrated_at": calibrated_raw,
              "valid_until": valid_raw, "measurement_date": measurement_date}
    return {"particle_rows": rows, "counts": counts, "bins": bins, "quantiles": quantiles,
            "accepted_proportion_ci": pod.proportion_interval(counts["accepted_observed"], n,
                                                               confidence=confidence),
            "calibration_provenance": {"record": record, "sha256": _sha256(record),
                                       "particles_sha256": _sha256(particles),
                                       "scale_ci": {"lower": scale_lo, "upper": scale_hi,
                                                    "confidence": confidence, "unit": unit_raw}},
             "policy": {"border": border_policy, "overlap": "exclude_unsplit_and_ambiguous",
                        "bases": ["number", "area", "volume"],
                        "quantile_convention": "weighted_empirical_midpoint",
                        "minimum_effective_particles": MIN_EFFECTIVE_PARTICLES,
                        "interval": "conditional nonparametric bootstrap + normal calibration scale interval",
                        "border_correction": correction_provenance,
                        "laser_diffraction_equivalence": False},
            "bootstrap": {"samples": int(bootstrap_samples), "seed": int(seed)}}
