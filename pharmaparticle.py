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
import re
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
# This is a provisional screening gate.  The neighbouring effective-n sweep
# measures its behaviour; it is not a pharmaceutical sampling requirement.
MIN_EFFECTIVE_PARTICLES = 30
PROVENANCE_KEYS = ("blob_split", "blob_count_interval")
PHYSICAL_TAIL_Z = 6.0
_BORDER_POLICIES = ("include", "exclude", "correct")
_SPLIT_STATUSES = ("isolated", "split", "unsplit", "ambiguous")
_PARTICLE_UNITS = {"diameter_unit": "px", "area_unit": "px2"}
_SCALE_UNIT = "mm/px"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


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


def _upstream_provenance_digest(records):
    """Digest structured blob_split/count-interval records / 構造化上流記録を要約する。"""
    if not isinstance(records, dict) or set(records) != set(PROVENANCE_KEYS):
        raise ValueError("particle_size_distribution: upstream_records must contain blob_split and blob_count_interval")
    split, interval = records["blob_split"], records["blob_count_interval"]
    if np.asarray(split).ndim != 2 or not isinstance(interval, dict) or "components" not in interval:
        raise ValueError("particle_size_distribution: upstream_records must be blob_split and blob_count_interval outputs")
    components = interval["components"]
    if not isinstance(components, dict) or not all(key in components for key in ("label", "lo", "hi", "status")):
        raise ValueError("particle_size_distribution: blob_count_interval components are incomplete")
    return _sha256(records)


def _bounded_normal(rng, mean, standard_uncertainty, *, lower, upper, shape):
    """Draw normal sensitivity values inside a physical domain / 物理範囲内で正規感度値を再抽出する。"""
    mean = np.asarray(mean, dtype=float)
    standard_uncertainty = np.asarray(standard_uncertainty, dtype=float)
    result = np.broadcast_to(mean, shape).copy()
    active = np.broadcast_to(standard_uncertainty > 0.0, shape)
    if not np.any(active):
        return result
    remaining = active.copy()
    for _ in range(100):
        candidate = rng.normal(np.broadcast_to(mean, shape)[remaining],
                               np.broadcast_to(standard_uncertainty, shape)[remaining])
        valid = (candidate > lower) & (candidate <= upper)
        locations = np.flatnonzero(remaining)
        result.flat[locations[valid]] = candidate[valid]
        remaining.flat[locations[valid]] = False
        if not np.any(remaining):
            return result
    raise ValueError("particle_size_distribution: could not draw border-correction sensitivity values inside the physical domain")


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


def _wilson_lower(successes, trials, confidence=.95):
    """Wilson lower endpoint without optional statistics packages / 追加統計パッケージなしの Wilson 下側端点。"""
    if not (isinstance(trials, int) and trials > 0 and 0 <= successes <= trials and confidence == .95):
        raise ValueError("particle_size_distribution: Wilson inputs are invalid")
    z = 1.959963984540054
    p = successes / trials
    return float((p + z * z / (2 * trials) - z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials ** 2))) /
                 (1 + z * z / trials))


def _conditional_simultaneous_coverage_validation(trials=400):
    """Recompute the synthetic conditional-family coverage observation / 条件付き区間族の合成被覆観測を再計算する。

    This is an observational, post-hoc exploratory calculation.  It supplies the
    PoC figure and its regression test from exactly the same deterministic run;
    it is not a predeclared acceptance gate and does not prove nominal coverage.
    """
    if not isinstance(trials, int) or trials < 1:
        raise ValueError("particle_size_distribution: trials must be a positive integer")
    rng = np.random.default_rng(42)
    population = rng.lognormal(np.log(20.0), .08, 100_000)
    acceptance_probability = .92 * .90 * (.78 + .20 / (1.0 + np.exp(-(population - 16.0) / 3.0)))
    truth = {}
    for basis, weight in (("number", acceptance_probability),
                          ("area", acceptance_probability * population ** 2),
                          ("volume", acceptance_probability * population ** 3)):
        truth[basis] = {"D%d" % q: _weighted_midpoint_dx(population, weight, q) * .001 for q in (10, 50, 90)}
    simultaneous = []
    for seed in range(trials):
        source = rng.choice(population, 96)
        source = source[rng.random(source.size) < (.78 + .20 / (1.0 + np.exp(-(source - 16.0) / 3.0)))]
        determined = rng.random(source.size) < .92
        border = rng.random(source.size) < .10
        true_scale = .001 + rng.normal(0.0, .000004)
        observed_px = source * .001 / true_scale + rng.normal(0.0, .18, source.size)
        labels = np.arange(1, source.size + 1, dtype=int)
        upstream_records = {"blob_split": labels.reshape(1, -1),
                            "blob_count_interval": {"components": {
                                "label": labels, "lo": np.ones(source.size, dtype=int),
                                "hi": np.where(determined, 1, -1),
                                "status": np.where(determined, "determined", "ambiguous")}}}
        digest = _upstream_provenance_digest(upstream_records)
        particles = {"object_id": ["trial-%03d-%03d" % (seed, i) for i in range(source.size)],
                     "diameter_px": observed_px, "area_px2": np.pi * np.square(observed_px) / 4.0,
                     "diameter_unit": "px", "area_unit": "px2", "touches_border": border,
                     "split_status": ["isolated" if item else "ambiguous" for item in determined],
                     "component_id": ["component-%d" % label for label in labels],
                     "split_evidence": ["blob_split + blob_count_interval:determined"] * source.size,
                     "upstream_provenance_hash": [digest] * source.size,
                     "upstream_component_label": labels, "upstream_split_label": labels,
                     "count_interval_lo": np.ones(source.size, dtype=int),
                     "count_interval_hi": [1 if item else None for item in determined],
                     "count_determined": determined}
        calibration = {"scale": {"value": true_scale + rng.normal(0.0, .000004), "unit": "mm/px",
                                  "standard_uncertainty": .000004},
                       "calibrator_id": "COVERAGE-SYNTHETIC", "calibrated_at": "2026-10-01", "valid_until": "2027-09-30"}
        report = particle_size_distribution(particles, calibration, border_policy="exclude", measurement_date="2026-11-23",
                                            bootstrap_samples=200, seed=seed, upstream_records=upstream_records)
        family = []
        for basis, targets in truth.items():
            for name, target in targets.items():
                interval = report["quantiles"][basis][name]
                if interval["status"] != "estimated":
                    raise AssertionError("coverage trial fell below the effective-particle gate")
                family.append(interval["ci_lower"] <= target <= interval["ci_upper"])
        simultaneous.append(all(family))
    successes = int(sum(simultaneous))
    return {"trials": trials, "successes": successes, "observed_proportion": successes / trials,
            "wilson_lower_95": _wilson_lower(successes, trials), "nominal_family_confidence": DEFAULT_CONFIDENCE,
            "interpretation": "post_hoc_exploratory_observation"}


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
                               seed=DEFAULT_SEED, upstream_records=None):
    """粒子表を校正し、採否理由、3 基準のビン、D10/D50/D90 と信頼区間、来歴を返す。

    D10/D50/D90 は、重複径を重みごとに集約した**重み付き経験分布の中点規約**で求める。
    ``unsplit`` と ``ambiguous`` の重なりは常に除外し、1 粒として黙って数えない。
    上流の ``blob_split`` と ``blob_count_interval`` に由来する成分 ID、分割根拠、
    来歴ハッシュ、上流の構造化 ``blob_split`` / ``blob_count_interval`` 記録、個数区間、
    決定可否が必須であり、op 内で再計算したダイジェストと一致しない入力は拒否する。
    ``component_id`` と上流 label は一対一、各行の split label は実際の ``blob_split``
    画像と一対一で照合する。これは同一実行内の整合性検査であり、署名または不変の外部
    成果物が無いので改ざん検知ではない。改ざん検知は実行記録と署名を備えた規制対応基盤で扱う。
    未決定行は ``ambiguous`` として除外する。
    ``border_policy="correct"`` は端粒子について ``border_inclusion_probability``、
    ``border_corrected_diameter_px``、``border_corrected_area_px2`` が揃う場合だけ
    Horvitz--Thompson の個数重み ``1/p`` と補正寸法を使う。尺度の標準不確かさは
    各径へ線形伝播し、分位点では決定的 bootstrap、尺度、端補正不確かさの
    感度再標本化を保守的に合成する。端補正の径・面積・包含確率は独立と明示した周辺正規
    不確かさとして扱うため、相関を持つ校正には使えない。物理範囲外の抽出値は切り詰めず
    再抽出する。
    有効粒子数が ``MIN_EFFECTIVE_PARTICLES`` 未満なら、母集団分位点を主張せず
    ``insufficient_sample`` を返す。bootstrap 区間は独立粒子の経験分布を再標本化する
    **分割後に受理された粒子に条件付けた区間**であり、端補正時は設計ベース保証ではなく
    実験的な不確かさである。

    Parameters
    ----------
    particles : table (dict of 1-D columns)
        必須列は ``object_id``、``diameter_px``、``area_px2``、``diameter_unit="px"``、
        ``area_unit="px2"``、``touches_border``、``split_status``、``component_id``、
        ``split_evidence``、``upstream_provenance_hash``、``upstream_component_label``、``upstream_split_label``、``count_interval_lo``、
        ``count_interval_hi``、``count_determined``。来歴ハッシュは元の ``blob_split`` と
        ``blob_count_interval`` の構造化記録を正規化して SHA-256 化したもの。
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
    upstream_records : dict
        ``{"blob_split": blob_split出力, "blob_count_interval": blob_count_interval出力}``。
        各行の ``upstream_component_label`` と個数記録、``upstream_split_label`` と実際の
        split 画像を照合し、op がダイジェストを再計算する。これは改ざん検知ではない。

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
    >>> p = {"object_id": ["p%d" % i for i in range(30)], "diameter_px": [10.] * 30, "area_px2": [78.5] * 30,
    ...      "diameter_unit": "px", "area_unit": "px2", "touches_border": [False] * 30,
    ...      "split_status": ["isolated"] * 30, "component_id": ["c%d" % i for i in range(30)],
    ...      "split_evidence": ["blob_split + blob_count_interval"] * 30,
    ...      "upstream_provenance_hash": ["0" * 64] * 30, "count_interval_lo": [1] * 30,
    ...      "count_interval_hi": [1] * 30, "count_determined": [True] * 30}
    >>> c = {"scale": {"value": .002, "unit": "mm/px", "standard_uncertainty": .00002},
    ...      "calibrator_id": "SM-01", "calibrated_at": "2026-01-01", "valid_until": "2026-12-31"}
    >>> u = {"blob_split": np.arange(30).reshape(1, 30) + 1,
    ...      "blob_count_interval": {"components": {"label": np.arange(1, 31), "lo": np.ones(30, int),
    ...      "hi": np.ones(30, int), "status": np.array(["determined"] * 30)}}}
    >>> p["upstream_component_label"] = list(range(1, 31)); p["upstream_provenance_hash"] = [_upstream_provenance_digest(u)] * 30
    >>> r = particle_size_distribution(p, c, measurement_date="2026-06-01", bootstrap_samples=200, upstream_records=u)
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
    upstream_digest = _upstream_provenance_digest(upstream_records)

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
    if any("blob_split" not in value or "blob_count_interval" not in value for value in evidence):
        raise ValueError("%s: split_evidence must identify blob_split and blob_count_interval" % op)
    hashes = [str(v) for v in _column(particles, "upstream_provenance_hash", n).tolist()]
    if any(_SHA256_RE.fullmatch(value) is None for value in hashes):
        raise ValueError("%s: upstream_provenance_hash must be a SHA-256 of structured upstream records" % op)
    if any(value != upstream_digest for value in hashes):
        raise ValueError("%s: upstream_provenance_hash does not match recomputed structured upstream records" % op)
    component_label = _numbers(particles, "upstream_component_label", n, positive=True)
    if np.any(component_label != np.floor(component_label)):
        raise ValueError("%s: upstream_component_label must be an integer" % op)
    split_label = _numbers(particles, "upstream_split_label", n, positive=True)
    if np.any(split_label != np.floor(split_label)):
        raise ValueError("%s: upstream_split_label must be an integer" % op)
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
    upstream_components = upstream_records["blob_count_interval"]["components"]
    upstream_labels = np.asarray(upstream_components["label"])
    upstream_lo = np.asarray(upstream_components["lo"], dtype=float)
    upstream_hi_raw = np.asarray(upstream_components["hi"])
    upstream_status = [str(value) for value in np.asarray(upstream_components["status"], dtype=object).tolist()]
    if not (upstream_labels.ndim == upstream_lo.ndim == upstream_hi_raw.ndim == 1
            and len(upstream_labels) == len(upstream_lo) == len(upstream_hi_raw) == len(upstream_status)):
        raise ValueError("%s: blob_count_interval component columns have different lengths" % op)
    upstream_index = {int(label): i for i, label in enumerate(upstream_labels.tolist())}
    if len(upstream_index) != len(upstream_labels):
        raise ValueError("%s: blob_count_interval component labels must be unique" % op)
    actual_split_labels = set(np.unique(np.asarray(upstream_records["blob_split"], dtype=int)).tolist()) - {0}
    reported_split_labels = set(split_label.astype(int).tolist())
    if not actual_split_labels or reported_split_labels != actual_split_labels:
        raise ValueError("%s: rows must correspond one-to-one with nonzero blob_split labels" % op)
    component_to_label = {}
    label_to_component = {}
    for component_id, label in zip(component, component_label.astype(int)):
        previous_label = component_to_label.setdefault(component_id, label)
        previous_component = label_to_component.setdefault(label, component_id)
        if previous_label != label or previous_component != component_id:
            raise ValueError("%s: component_id and upstream_component_label must be one-to-one" % op)
    if set(label_to_component) != set(upstream_index):
        raise ValueError("%s: particle rows and blob_count_interval labels must agree in both directions" % op)
    for i, label in enumerate(component_label.astype(int)):
        if label not in upstream_index:
            raise ValueError("%s: upstream_component_label is absent from blob_count_interval" % op)
        j = upstream_index[label]
        expected_hi = None if int(upstream_hi_raw[j]) < 0 else float(upstream_hi_raw[j])
        expected_determined = upstream_status[j] == "determined"
        if (float(interval_lo[i]) != float(upstream_lo[j]) or
                (None if np.isnan(interval_hi[i]) else float(interval_hi[i])) != expected_hi or
                bool(determined[i]) != expected_determined):
            raise ValueError("%s: particle count interval does not match structured upstream component" % op)
    # A component is the audit unit.  Row-wise checks alone would allow one
    # component to be reported repeatedly as many independent particles.
    for component_id in sorted(set(component)):
        members = [i for i, value in enumerate(component) if value == component_id]
        first = members[0]
        signature = lambda i: (statuses[i], evidence[i], hashes[i], float(interval_lo[i]),
                               None if np.isnan(interval_hi[i]) else float(interval_hi[i]), bool(determined[i]))
        if any(signature(i) != signature(first) for i in members[1:]):
            raise ValueError("%s: component %r has inconsistent split/count/provenance records" % (op, component_id))
        if determined[first]:
            declared = int(interval_lo[first])
            if interval_lo[first] != declared or len(members) != declared:
                raise ValueError("%s: determined component %r must report exactly its declared count" % (op, component_id))
            expected_status = "isolated" if declared == 1 else "split"
            if statuses[first] != expected_status:
                raise ValueError("%s: determined component %r has inconsistent split_status" % (op, component_id))
        elif statuses[first] != "ambiguous":
                raise ValueError("%s: undetermined component %r must be ambiguous" % (op, component_id))
    for label, component_id in label_to_component.items():
        members = np.flatnonzero(component_label.astype(int) == label)
        expected_rows = int(upstream_lo[upstream_index[label]])
        if upstream_status[upstream_index[label]] == "determined" and members.size != expected_rows:
            raise ValueError("%s: upstream label %d must report exactly its declared count" % (op, label))

    major = _numbers(particles, "major_axis_px", n, positive=True) if "major_axis_px" in particles else None
    minor = _numbers(particles, "minor_axis_px", n, positive=True) if "minor_axis_px" in particles else None
    if (major is None) != (minor is None) or (major is not None and np.any(major < minor)):
        raise ValueError("%s: major/minor axes must be paired and major_axis_px >= minor_axis_px" % op)

    used_d, used_a, count_weight = diameter_px.copy(), area_px2.copy(), np.ones(n)
    prob_u = corr_d_u = corr_a_u = np.zeros(n, dtype=float)
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
                key in correction_provenance for key in ("view_shape", "inclusion_probability_method", "correction_method",
                                                         "uncertainty_dependence")):
            raise ValueError("%s: border_correction_provenance must state view_shape, inclusion_probability_method, correction_method, uncertainty_dependence" % op)
        if correction_provenance["uncertainty_dependence"] != "independent":
            raise ValueError("%s: only explicitly independent border-correction uncertainties are supported; correlated inputs are fail-closed" % op)
        if np.any(prob > 1.0):
            raise ValueError("%s: border_inclusion_probability must be <= 1" % op)
        if np.any(prob - PHYSICAL_TAIL_Z * prob_u <= 0.0) or np.any(prob + PHYSICAL_TAIL_Z * prob_u > 1.0):
            raise ValueError("%s: border inclusion probability uncertainty leaves (0, 1] within the declared six-sigma physical tail" % op)
        if np.any(corr_d - PHYSICAL_TAIL_Z * corr_d_u <= 0.0) or np.any(corr_a - PHYSICAL_TAIL_Z * corr_a_u <= 0.0):
            raise ValueError("%s: corrected dimensions must remain positive within the declared six-sigma physical tail" % op)
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

    rng = np.random.default_rng(int(seed))
    # Equal-probability row bootstrap is conditional on observed particles.  It
    # describes sampling uncertainty for the declared particle population; it is
    # not a design-based guarantee for experimental border correction.
    draws = rng.integers(0, idx.size, size=(int(bootstrap_samples), idx.size), endpoint=False)
    # Sensitivity draws carry corrected-diameter, corrected-area and inclusion
    # probability uncertainty into both weights and Dx.  They are only random
    # for border-corrected rows; ordinary rows remain exactly observed.
    dpx_draw = np.broadcast_to(dpx, draws.shape).copy()
    area_draw = np.broadcast_to(area, draws.shape).copy()
    count_draw = np.broadcast_to(cw, draws.shape).copy()
    corrected_positions = np.flatnonzero(touches[idx])
    if corrected_positions.size:
        sensitivity_rng = np.random.default_rng(int(seed) + 104729)
        local = idx[corrected_positions]
        physical_shape = (int(bootstrap_samples), local.size)
        dpx_draw[:, corrected_positions] = _bounded_normal(
            sensitivity_rng, used_d[local], corr_d_u[local], lower=0.0, upper=math.inf, shape=physical_shape)
        area_draw[:, corrected_positions] = _bounded_normal(
            sensitivity_rng, used_a[local], corr_a_u[local], lower=0.0, upper=math.inf, shape=physical_shape)
        probability_draw = _bounded_normal(
            sensitivity_rng, 1.0 / cw[corrected_positions], prob_u[local], lower=0.0, upper=1.0,
            shape=physical_shape)
        count_draw[:, corrected_positions] = 1.0 / probability_draw
    # Nine Dx intervals are reported together (3 bases x D10/D50/D90).  Use a
    # Bonferroni bootstrap envelope so the stated 95% family is not made
    # spuriously narrow at a high weighted tail.  This is conservative for an
    # individual Dx and is declared in the returned policy.
    alpha = (1.0 - confidence) / (2.0 * 9.0)
    quantiles = {}
    effective_particles = {}
    for basis, weight in weights.items():
        effective_n = _effective_particles(weight)
        effective_particles[basis] = effective_n
        quantiles[basis] = {}
        for q in (10, 50, 90):
            key = "D%d" % q
            if effective_n < MIN_EFFECTIVE_PARTICLES:
                quantiles[basis][key] = {"status": "insufficient_sample", "value": None,
                                         "ci_lower": None, "ci_upper": None, "unit": unit,
                                         "effective_particles": effective_n,
                                         "minimum_effective_particles": MIN_EFFECTIVE_PARTICLES}
                continue
            sample = np.empty(int(bootstrap_samples), dtype=float)
            for draw_index, take in enumerate(draws):
                sampled_dpx = dpx_draw[draw_index, take]
                sampled_count = count_draw[draw_index, take]
                if basis == "number":
                    sampled_weight = sampled_count
                elif basis == "area":
                    sampled_weight = sampled_count * area_draw[draw_index, take]
                else:
                    sampled_weight = sampled_count * sampled_dpx ** 3
                sample[draw_index] = _weighted_midpoint_dx(sampled_dpx, sampled_weight, q)
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
               "diameter": float(diameters[i]), "diameter_uncertainty": float(math.hypot(
                   used_d[i] * scale_u, corr_d_u[i] * scale)),
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
                                       "upstream_records_sha256": upstream_digest,
                                       "scale_ci": {"lower": scale_lo, "upper": scale_hi,
                                                    "confidence": confidence, "unit": unit_raw}},
             "policy": {"border": border_policy, "overlap": "exclude_unsplit_and_ambiguous",
                        "bases": ["number", "area", "volume"],
                         "quantile_convention": "weighted_empirical_midpoint",
                         "minimum_effective_particles": MIN_EFFECTIVE_PARTICLES,
                         "interval": "Bonferroni (9 Dx) conditional accepted-particle bootstrap + calibration and border-correction sensitivity",
                         "interval_claim": "conditional_on_accepted_particles_after_segmentation",
                         "interval_family_confidence": confidence,
                         "interval_per_dx_bootstrap_confidence": 1.0 - 2.0 * alpha,
                         "effective_particles": effective_particles,
                         "border_correction": correction_provenance,
                          "border_uncertainty_propagation": "independent marginal-normal sensitivity resampling with physical-domain rejection sampling; correlations are unsupported" if corrected_positions.size else "not_applicable",
                        "laser_diffraction_equivalence": False},
            "bootstrap": {"samples": int(bootstrap_samples), "seed": int(seed)}}
