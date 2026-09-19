# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""fullseye.fixture — 既知の良品/不良品セットで recipe + spec を配備前に検定する(検査ワークフロー層 #4)。

現場でレシピと仕様を決めたあと、最初に聞かれるのは「それで良品は全部通り、不良品は全部止まるのか」と
「どれくらい余裕があるのか」。ここはその 2 つを 1 回の呼び出しで返す:

    fixture = inspection_fixture(good_dir, bad_dir, recipe, measure=..., spec=...)
    fixture["passed"]          # 良品が全部 ok かつ 不良品が全部 ng(error は失敗に数える = fail-closed)
    fixture["confusion"]       # {"good": {"ok","ng","error"}, "bad": {"ok","ng","error"}}
    fixture["escapes"]         # 不良品なのに ok になった行(見逃し)
    fixture["false_rejects"]   # 良品なのに ng になった行(過検出)
    fixture["margins"]         # 仕様キーごとの余裕(良品の計測が限界にどれだけ近いか、0 = 限界上、負 = 超過)
    fixture["detail"]          # 人が読む 1 行

**約束**: 空のセットは ``ValueError``(0 枚で「全部通った」は証明にならない)。error 行は passed を落とす。
margin は仕様の単位で返し、``tol`` / (max−min) があれば正規化した ``margin_norm`` も付ける(1.0 = 限界幅ぶんの余裕)。
新アルゴリズムは無い。:func:`fullseye.inspect_batch.inspect_batch` と :func:`fullseye.judge.judge` の配線。
"""
from __future__ import annotations

import math
import numbers

import numpy as np

from fullseye.inspect_batch import inspect_batch
from fullseye.judge import _validate_spec

__all__ = ["inspection_fixture", "spec_margins"]


def _is_number(v) -> bool:
    return isinstance(v, (numbers.Real, np.integer, np.floating)) and not isinstance(v, bool)


def _margin_one(value, rule):
    """1 つの計測値の、規則の限界までの余裕(仕様の単位)。数値規則以外は None。"""
    if not _is_number(value) or not math.isfinite(float(value)):
        return None, None
    x = float(value)
    cands = []
    width = None
    if "nominal" in rule:
        nom, tol = float(rule["nominal"]), float(rule["tol"])
        cands.append(tol - abs(x - nom))
        width = tol
    if "min" in rule:
        cands.append(x - float(rule["min"]))
    if "max" in rule:
        cands.append(float(rule["max"]) - x)
    if "min" in rule and "max" in rule:
        width = (float(rule["max"]) - float(rule["min"])) / 2.0
    if not cands:
        return None, None
    m = min(cands)
    return m, (m / width if width and width > 0 else None)


def spec_margins(measurements, spec) -> dict:
    """良品の計測 dict の列に対し、仕様キーごとの余裕を集計する。

    返り値 ``{key: {"n", "min_margin", "mean_margin", "min_margin_norm", "worst_value"}}``。
    ``min_margin`` が負なら少なくとも 1 枚が限界を超えている(= その良品は ng になる)。
    eq / in の規則(数値でない)は ``{"n", "violations"}`` だけ。
    """
    _validate_spec(spec)
    out = {}
    for key, rule in spec.items():
        vals = [m.get(key) for m in measurements if isinstance(m, dict) and key in m]
        numeric = any(k in rule for k in ("min", "max", "nominal"))
        if not numeric:
            viol = sum(1 for v in vals if ("eq" in rule and v != rule["eq"]) or ("in" in rule and v not in list(rule["in"])))
            out[key] = {"n": len(vals), "violations": int(viol)}
            continue
        ms, ns, worst = [], [], None
        for v in vals:
            m, n = _margin_one(v, rule)
            if m is None:
                continue
            ms.append(m)
            if n is not None:
                ns.append(n)
            if worst is None or m < worst[0]:
                worst = (m, float(v))
        out[key] = {"n": len(ms),
                    "min_margin": float(min(ms)) if ms else None,
                    "mean_margin": float(np.mean(ms)) if ms else None,
                    "min_margin_norm": float(min(ns)) if ns else None,
                    "worst_value": worst[1] if worst else None}
    return out


def inspection_fixture(good, bad, recipe=None, *, measure, spec, sort="image",
                       on_error="record", report_path=None, title=None) -> dict:
    """既知の良品セット ``good`` と不良品セット ``bad`` で recipe + spec を検定する。

    ``good`` / ``bad`` は :func:`inspect_batch` と同じ(ディレクトリ or パス列)。両方とも 1 枚以上必須。
    返り値::

        {"passed": bool, "confusion": {"good": {...}, "bad": {...}},
         "escapes": [row...], "false_rejects": [row...], "errors": [row...],
         "margins": spec_margins(良品の計測, spec),
         "good": inspect_batch の返り, "bad": inspect_batch の返り, "detail": str}

    ``report_path``(.xlsx / .md / .jsonl)を渡すと良品と不良品を別々に ``<stem>_good.<ext>`` /
    ``<stem>_bad.<ext>`` に書く。
    """
    _validate_spec(spec)
    import os
    rp_good = rp_bad = None
    if report_path:
        stem, ext = os.path.splitext(os.fspath(report_path))
        rp_good, rp_bad = stem + "_good" + ext, stem + "_bad" + ext
    t = title or "Inspection fixture"
    res_good = inspect_batch(good, recipe, measure=measure, spec=spec, sort=sort, on_error=on_error,
                             report_path=rp_good, title=t + " / good")
    res_bad = inspect_batch(bad, recipe, measure=measure, spec=spec, sort=sort, on_error=on_error,
                            report_path=rp_bad, title=t + " / bad")

    def _conf(res):
        c = {"ok": 0, "ng": 0, "error": 0}
        for r in res["rows"]:
            c[r["verdict"]["status"]] += 1
        return c

    conf = {"good": _conf(res_good), "bad": _conf(res_bad)}
    escapes = [r for r in res_bad["rows"] if r["verdict"]["status"] == "ok"]
    false_rejects = [r for r in res_good["rows"] if r["verdict"]["status"] == "ng"]
    errors = [r for r in res_good["rows"] + res_bad["rows"] if r["verdict"]["status"] == "error"]
    passed = (conf["good"]["ok"] == len(res_good["rows"]) and conf["bad"]["ng"] == len(res_bad["rows"]))
    margins = spec_margins([r["measurements"] for r in res_good["rows"] if not r.get("error")], spec)
    tight = [(k, v["min_margin_norm"]) for k, v in margins.items()
             if v.get("min_margin_norm") is not None]
    tight.sort(key=lambda kv: kv[1])
    if passed:
        detail = "passed: good %d/%d ok, bad %d/%d ng" % (conf["good"]["ok"], len(res_good["rows"]),
                                                          conf["bad"]["ng"], len(res_bad["rows"]))
        if tight:
            detail += "; tightest margin %s=%.2f of limit width" % (tight[0][0], tight[0][1])
    else:
        parts = []
        if escapes:
            parts.append("%d escape(s): %s" % (len(escapes), ", ".join(os.path.basename(r["path"]) for r in escapes[:5])))
        if false_rejects:
            parts.append("%d false reject(s): %s" % (len(false_rejects), ", ".join(os.path.basename(r["path"]) for r in false_rejects[:5])))
        if errors:
            parts.append("%d error(s)" % len(errors))
        detail = "failed: " + "; ".join(parts)
    return {"passed": passed, "confusion": conf, "escapes": escapes, "false_rejects": false_rejects,
            "errors": errors, "margins": margins, "good": res_good, "bad": res_bad, "detail": detail}
