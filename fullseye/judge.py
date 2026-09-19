# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""fullseye.judge — 計測値を仕様に照らして **根拠つきの Verdict** にする(検査ワークフロー層 #2)。

op 931 本で「測る」ことはできても、測った数字を **良否に変える入口** が無かった。
:class:`fsruntime.Verdict` は PLC が読む語彙(``ok`` / ``ng`` / ``error`` / ``timeout``)を
持ち、出口 :func:`device.signal_verdict` はそれをコイルに one-hot で出す。ここはその
**入口** —— 計測 dict と仕様 dict から Verdict を作る、op ではない facade 関数。

仕様 ``spec`` は ``{計測キー: 規則}`` で、規則は次のいずれか(組み合わせ可)::

    {"min": 10, "max": 15}            # 下限・上限(境界を含む。片方だけでも可)
    {"nominal": 3.0, "tol": 0.05}     # 公称 ± 公差(境界を含む)
    {"eq": "OK"}                      # 等しい(文字列・数値)
    {"in": ["A", "B"]}                # 集合に含まれる

**fail-closed の約束**(黙って ok にしない):

- 仕様にあって計測に無いキーは ``strict=True``(既定)で ``error``。``strict=False`` なら
  飛ばして ``result["missing"]`` に残す(ok と区別できる)。
- 非有限(NaN / inf)や、数値規則に数値でない値は ``error``(比較できないものを ng にも
  ok にもしない)。
- 規則の綴り間違い(``"mx"`` 等)は ``ValueError`` —— 誤字の規則が「何も検査しない」で
  通ると、その仕様は永久に全部 ok になる。
- 違反が 1 つでもあれば ``ng``。``result["violations"]`` に ``{key, value, rule, limit}`` を
  全部並べ、``detail`` は人が読む 1 行の根拠。

単位は呼び手の責任(ここで換算しない)。仕様に無い計測キーは無視する(仕様が「見るもの」を決める)。
"""
from __future__ import annotations

import math
import numbers
import time

import numpy as np

from fsruntime import Verdict

__all__ = ["judge", "RULE_KEYS"]

#: 仕様の規則として受け付けるキー。これ以外は ValueError(誤字が「検査しない」に化けない)。
RULE_KEYS = frozenset({"min", "max", "nominal", "tol", "eq", "in"})


def _is_number(v) -> bool:
    return isinstance(v, (numbers.Real, np.integer, np.floating)) and not isinstance(v, bool)


def _as_float(v) -> float:
    return float(v)


def _validate_spec(spec) -> None:
    if not isinstance(spec, dict) or not spec:
        raise ValueError("judge: spec must be a non-empty dict of {key: rule}")
    for key, rule in spec.items():
        if not isinstance(rule, dict) or not rule:
            raise ValueError("judge: rule for %r must be a non-empty dict" % (key,))
        unknown = set(rule) - RULE_KEYS
        if unknown:
            raise ValueError("judge: unknown rule key(s) %s for %r (allowed: %s)"
                             % (sorted(unknown), key, sorted(RULE_KEYS)))
        if ("nominal" in rule) != ("tol" in rule):
            raise ValueError("judge: rule for %r needs both 'nominal' and 'tol'" % (key,))
        for k in ("min", "max", "nominal", "tol"):
            if k in rule and not _is_number(rule[k]):
                raise ValueError("judge: rule %r for %r must be a number, got %r" % (k, key, rule[k]))
        if "tol" in rule and float(rule["tol"]) < 0:
            raise ValueError("judge: 'tol' for %r must be >= 0" % (key,))
        if "min" in rule and "max" in rule and float(rule["min"]) > float(rule["max"]):
            raise ValueError("judge: 'min' > 'max' for %r" % (key,))
        if "in" in rule:
            try:
                iter(rule["in"])
            except TypeError:
                raise ValueError("judge: 'in' for %r must be iterable" % (key,)) from None
            if isinstance(rule["in"], (str, bytes)):
                raise ValueError("judge: 'in' for %r must be a collection, not a string" % (key,))


def _check_one(key, value, rule):
    """1 キーの照合。返り: (violations list, error message or None)。"""
    viol = []
    needs_number = any(k in rule for k in ("min", "max", "nominal"))
    if needs_number:
        if not _is_number(value):
            return [], "%s=%r is not a number (rule %s)" % (key, value, _rule_str(rule))
        x = _as_float(value)
        if not math.isfinite(x):
            return [], "%s=%r is not finite" % (key, value)
        if "min" in rule and x < float(rule["min"]):
            viol.append({"key": key, "value": x, "rule": "min", "limit": float(rule["min"])})
        if "max" in rule and x > float(rule["max"]):
            viol.append({"key": key, "value": x, "rule": "max", "limit": float(rule["max"])})
        if "nominal" in rule:
            nom, tol = float(rule["nominal"]), float(rule["tol"])
            if abs(x - nom) > tol:
                viol.append({"key": key, "value": x, "rule": "nominal±tol",
                             "limit": [nom - tol, nom + tol]})
    if "eq" in rule:
        want = rule["eq"]
        if _is_number(value) and not math.isfinite(_as_float(value)):
            return [], "%s=%r is not finite" % (key, value)
        if not _equal(value, want):
            viol.append({"key": key, "value": _plain(value), "rule": "eq", "limit": _plain(want)})
    if "in" in rule:
        allowed = list(rule["in"])
        if _is_number(value) and not math.isfinite(_as_float(value)):
            return [], "%s=%r is not finite" % (key, value)
        if not any(_equal(value, a) for a in allowed):
            viol.append({"key": key, "value": _plain(value), "rule": "in",
                         "limit": [_plain(a) for a in allowed]})
    return viol, None


def _equal(a, b) -> bool:
    if _is_number(a) and _is_number(b):
        return _as_float(a) == _as_float(b)
    return a == b


def _plain(v):
    if _is_number(v):
        return _as_float(v) if isinstance(v, (float, np.floating)) else int(v)
    return v


def _rule_str(rule) -> str:
    return ", ".join("%s=%r" % (k, rule[k]) for k in ("min", "max", "nominal", "tol", "eq", "in") if k in rule)


def _limit_str(v) -> str:
    if isinstance(v, list):
        return "[" + ", ".join(_limit_str(x) for x in v) + "]"
    if isinstance(v, float):
        return "%g" % v
    return repr(v) if isinstance(v, str) else str(v)


def judge(measurements: dict, spec: dict, *, strict: bool = True) -> Verdict:
    """計測 dict を仕様 dict に照らし、根拠つきの :class:`fsruntime.Verdict` を返す。

    ``measurements`` は ``{"area": 12.5, "width_mm": 3.02, "label": "OK"}`` のように計測 op の
    出力を dict にしたもの。``spec`` は ``{"area": {"min": 10, "max": 15}, ...}``(規則は
    モジュール docstring)。返り値は ``status`` が ``"ok"`` / ``"ng"`` / ``"error"`` のいずれかで、
    ``result`` は ``{"violations": [...], "checked": n, "missing": [...], "errors": [...]}``、
    ``detail`` は 1 行の根拠。そのまま :func:`device.signal_verdict` に渡せる。

    ``strict=True``(既定)では仕様にあって計測に無いキーが ``error``。``False`` なら飛ばして
    ``result["missing"]`` に列挙する(検査しなかった事実を残す)。仕様の形が壊れていれば
    ``ValueError``(誤字の規則を「検査しない」で通さない)。
    """
    t0 = time.perf_counter()
    _validate_spec(spec)
    if not isinstance(measurements, dict):
        raise ValueError("judge: measurements must be a dict, got %s" % type(measurements).__name__)

    violations, errors, missing = [], [], []
    checked = 0
    for key in spec:                                        # 仕様の順で決定的に
        if key not in measurements:
            missing.append(key)
            if strict:
                errors.append("missing measurement %r" % (key,))
            continue
        viol, err = _check_one(key, measurements[key], spec[key])
        if err is not None:
            errors.append(err)
            continue
        checked += 1
        violations.extend(viol)

    result = {"violations": violations, "checked": checked, "missing": missing, "errors": errors}
    elapsed = (time.perf_counter() - t0) * 1000.0
    if errors:
        status, detail = "error", "error: " + "; ".join(errors)
    elif violations:
        status = "ng"
        detail = "ng: " + "; ".join(
            "%s=%s violates %s %s" % (v["key"], _limit_str(v["value"]), v["rule"], _limit_str(v["limit"]))
            for v in violations)
    else:
        status = "ok"
        detail = "ok: %d/%d checks within spec" % (checked, len(spec))
        if missing:
            detail += " (skipped %d missing: %s)" % (len(missing), ", ".join(map(str, missing)))
    return Verdict(status=status, result=result, elapsed_ms=elapsed, detail=detail)
