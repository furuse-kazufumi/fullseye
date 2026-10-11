# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Three gaps the mutation probe found NO gate for (2026-10-11), as ratchets.

g) ``description`` -- every typed-ledger op, every n-ary op (``imgops_nary._DEFS``) and
   every public function / class in ``fullseye.__all__`` says what it does: not empty, a
   head of at least 20 characters, not just its own name (the rules of
   ``tests/test_op_descriptions.py``, which only looked at ``ops.REGISTRY``).
h) ``empty_input`` -- a ledger op whose docstring promises a ``ValueError`` (or says it
   rejects / 拒否) on empty input really raises ``ValueError`` when its first data argument
   is an empty value of the same kind. Ops that return something for empty input WITHOUT
   any docstring statement are only counted (:func:`empty_census`) -- whether that should
   be refused is the owner's policy call.
f) ``dead_knob`` -- for each numeric keyword parameter with a default, the op is called
   with the default halved and doubled (0 -> 0.5 / 1); a knob whose change never changes
   the output on the probe input is flagged. False positives are expected (a knob that
   only matters for some inputs) and carry a reason category.

(h) and (f) piggy-back on the contract probe (:func:`ledger_contracts.run` with
``hooks=``): they reuse its arguments and its result, so the probe runs once.

The committed debt is ``docs/LEDGER_GAP_DEBT.json`` (``{gap: {key: category}}``), same
rules as ``LEDGER_CONTRACT_DEBT.json``: a new failure fails, a listed key that now passes
fails, so the debt can only shrink. ``py -3.11 tools/ledger_gaps.py --write`` rewrites it.
"""
from __future__ import annotations

import importlib
import inspect
import json
import numbers
import os
import re
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import ledger_contracts as lc  # noqa: E402

DEBT = os.path.join(ROOT, "docs", "LEDGER_GAP_DEBT.json")
GAPS = ("description", "empty_input", "dead_knob")


# --------------------------------------------------------------------------- #
# g) descriptions                                                              #
# --------------------------------------------------------------------------- #
def _head(doc: str) -> str:
    """First line of the docstring -- the same rule as tests/test_op_descriptions.py."""
    return (doc or "").strip().split("\n")[0].strip()


def thin(name: str, doc: str):
    """Reason category when *doc* is not a description, else ``None``."""
    if not (doc or "").strip():
        return "missing"
    head = _head(doc)
    if head.strip(" .。") == name:
        return "name_only"
    if len(head) < 20:
        return "short_head"
    return None


def description_targets():
    """``[(key, name, doc)]`` for the three tiers (``key`` = ``tier:name``)."""
    import api
    import opassist
    out = []
    tables = dict(opassist._LEDGERS)
    for r in api.ledger_rows():
        e = getattr(importlib.import_module(r["ledger"]), tables[r["ledger"]])[r["name"]]
        doc = (e.get("doc") or "") or (getattr(e.get("func"), "__doc__", None) or "")
        out.append(("ledger:" + r["name"], r["name"], doc))
    import imgops_nary
    for d in imgops_nary._DEFS:
        out.append(("nary:" + d[0], d[0], d[6] or ""))
    import fullseye
    for n in fullseye.__all__:
        o = getattr(fullseye, n, None)
        if not (inspect.isfunction(o) or inspect.isbuiltin(o) or inspect.isclass(o)
                or (callable(o) and not inspect.ismodule(o) and hasattr(o, "__wrapped__"))):
            continue
        doc = o.__doc__ or ""
        if inspect.isclass(o) and doc == (type(o).__doc__ or ""):
            doc = ""
        out.append(("facade:" + n, n, doc))
    return out


def description_audit():
    """``{key: category}`` for every target that is not a description, plus the scope."""
    targets = description_targets()
    bad = {k: c for k, n, d in targets for c in [thin(n, d)] if c}
    scope = {}
    for k, _n, _d in targets:
        tier = k.split(":", 1)[0]
        scope[tier] = scope.get(tier, 0) + 1
    return bad, scope


# --------------------------------------------------------------------------- #
# h) empty input                                                               #
# --------------------------------------------------------------------------- #
_NOT_EMPTY = "間気白洞港中想全腹"            # 空間 / 空気 / 空白 … are not "empty"
_PROMISE = (
    re.compile(r"(?i)(empty|zero[- ]length)[^.\n]{0,80}(ValueError|raise|reject|refus)"),
    re.compile(r"(?i)(ValueError|raises?\b|reject\w*|refus\w*)[^.\n]{0,100}\b(empty|zero[- ]length)\b"),
    re.compile(r"(?<!非)空(?![%s])[^。\n]{0,40}(ValueError|拒否|拒む|例外|断る)" % _NOT_EMPTY),
    re.compile(r"(ValueError|拒否|拒む|断る)[^。\n]{0,60}(?<!非)空(?![%s])" % _NOT_EMPTY),
)


#: The docstring says empty input is ACCEPTED (returns empty / zeros / no exception). It
#: wins over a promise: 2026-10-11 the first reader flagged 10 ops, and all 10 were
#: misreads of this kind or of a promise about ANOTHER argument (``pts1 が空``).
_ACCEPTS = (
    re.compile(r"空[^。\n]{0,24}(を返す|は空|が返る|例外(は|に)(出さ|し|出)ない|例外にはしない)"),
    re.compile(r"例外(は|に)(出さ|し|出)ない|例外にはしない"),
    re.compile(r"(?i)\bempty\b[^.\n]{0,40}(->|returns?\b|gives\b|yields\b|is returned)"),
    re.compile(r"(?i)(returns?|yields?) (an )?empty\b"),
)


def promises_empty_refusal(doc: str, first=None, others=()) -> bool:
    """Does *doc* promise a refusal of an EMPTY first argument?

    A promise that names another parameter right next to the empty-word (``pts1 が空``) is
    about that parameter, not the first one; a docstring that says empty input is accepted
    is not a promise at all -- unless a promise names the first parameter itself
    (``空の入力(``vertices`` が 0 要素)は ValueError`` beside "empty FACES are accepted").
    """
    d = re.sub(r"\s+", " ", doc or "")
    if first:
        named = re.compile(r"((?<!非)空(?![%s])の入力[(（]|(?i:\bempty input) \()``%s``"
                           % (_NOT_EMPTY, re.escape(first)))
        if any(named.search(d[m.start():m.end()]) for p in _PROMISE for m in p.finditer(d)):
            return True
    if any(p.search(d) for p in _ACCEPTS):
        return False
    for p in _PROMISE:
        for m in p.finditer(d):
            # whose emptiness? the parameter named just before the empty-word
            tok = re.search(r"(?<!非)空(?![%s])|(?i:\bempty\b)" % _NOT_EMPTY, d[m.start():m.end()])
            pos = m.start() + (tok.start() if tok else 0)
            before = d[max(0, pos - 12):pos]
            if any(o and re.search(r"\b%s\b" % re.escape(o), before) for o in others) \
                    and not (first and re.search(r"\b%s\b" % re.escape(first), before)):
                continue
            return True
    return False


def empty_like(v):
    """An empty value of the same kind as *v*, or ``None`` when emptiness has no meaning."""
    v = lc._to_numpy(v)
    if isinstance(v, np.ndarray):
        return v[:0] if v.ndim >= 1 else None
    if isinstance(v, (list, tuple)):
        return type(v)() if isinstance(v, list) else ()
    if isinstance(v, dict):
        return {}
    if isinstance(v, str):
        return ""
    return None


class EmptyInputHook:
    """Calls the op once more with its first data argument emptied."""
    key = "empty"

    def __call__(self, name, ins, fn, args, kwargs, res, verdict):
        if not ins or not args:
            return None
        e = empty_like(args[0])
        if e is None:
            return {"outcome": "n/a"}
        try:
            pnames = [p.name for p in inspect.signature(fn).parameters.values()]
        except (TypeError, ValueError):
            pnames = []
        promised = promises_empty_refusal(fn.__doc__ or "", pnames[0] if pnames else None,
                                          pnames[1:])
        try:
            lc._call(fn, [e] + list(args[1:]), kwargs)
        except Exception as exc:                 # noqa: BLE001
            if lc.optional_missing(exc):
                return {"outcome": "skip", "promised": promised}
            kind = "value_error" if isinstance(exc, ValueError) else "raw_" + type(exc).__name__
            return {"outcome": kind, "promised": promised}
        return {"outcome": "returned", "promised": promised}


def empty_failure(g):
    """Debt category for one empty-input observation (``None`` = passes / not judged)."""
    if not g or not g.get("promised") or g["outcome"] in ("value_error", "skip", "n/a"):
        return None
    return "returns_on_empty" if g["outcome"] == "returned" else g["outcome"]


# --------------------------------------------------------------------------- #
# f) dead knobs                                                                #
# --------------------------------------------------------------------------- #
#: Parameters that do not shape the output by design (where / how it runs, not what).
_NOT_A_KNOB = {"verbose", "seed", "random_state", "n_jobs", "workers", "threads", "device",
               "chunk", "chunk_size", "batch", "batch_size", "cache", "progress"}
_TOL = re.compile(r"(^|_)(tol|atol|rtol|eps|epsilon|max_iter|iters?|iterations|n_iter|maxiter|"
                  r"max_steps|patience|precision)($|_)")

#: Ops not swept for dead knobs because one call costs > 0.25 s on the probe (measured
#: 2026-10-11; each knob costs 1-2 more calls). A FIXED list, not a timing test: a timing
#: threshold made the swept set depend on the machine -- an op slow here but fast on CI
#: would be judged only on CI and fail there with "new" dead knobs.
KNOB_SKIP_SLOW = frozenset({
    "distance_peaks", "dynsys_lyapunov_spectrum", "perpetual_chaos_game",
    "perpetual_flow_field", "perpetual_harmonograph", "perpetual_loop", "perpetual_plasma",
    "perpetual_reaction_diffusion", "physarum_route", "piv_streamline_image", "psf_fit",
    "rally_simulate", "register_fpfh", "register_spin", "render_beauty",
    "render_through_lens", "smallest_box3", "tf_impulse_response", "tf_step_response",
    "tid2013_compare", "watershed_vol",
})


def knob_variants(default):
    """Two in-range alternatives to a numeric default."""
    if isinstance(default, bool) or not isinstance(default, numbers.Real):
        return []
    if isinstance(default, numbers.Integral):
        d = int(default)
        return [1, 2] if d == 0 else sorted({max(1, d // 2), d * 2} - {d}) if d > 0 else [d * 2, d // 2]
    d = float(default)
    if not np.isfinite(d):
        return []
    return [0.5, 1.0] if d == 0.0 else [d * 0.5, d * 2.0]


def _numbers(x, depth=0):
    """Every float in *x* (arrays, scalars, containers) as one flat array."""
    x = lc._to_numpy(x)
    if depth > 4:
        return []
    if isinstance(x, np.ndarray) and x.dtype.kind in "biuf":
        return [x.astype(np.float64).ravel()]
    if isinstance(x, (bool, np.bool_)):
        return []
    if isinstance(x, numbers.Real):
        return [np.array([float(x)])]
    if isinstance(x, dict):
        return [a for v in x.values() for a in _numbers(v, depth + 1)]
    if isinstance(x, (list, tuple)):
        return [a for v in x for a in _numbers(v, depth + 1)]
    return []


def degenerate(res):
    """The probe output is constant (e.g. an all-black render): no knob can show itself.

    ★2026-10-11: ``grating_rgb.strength`` multiplies the colour -- but the probe's colour
    was all zero, so ×0.1 … ×100 changed nothing. A dead knob on such an output says more
    about the probe than about the op; it gets its own category.
    """
    parts = [a for a in _numbers(res) if a.size]
    if not parts:
        return False
    v = np.concatenate(parts)
    v = v[np.isfinite(v)]
    return v.size > 1 and float(np.ptp(v)) == 0.0


def knob_category(param):
    if _TOL.search(param):
        return "tolerance_or_iterations"
    if re.search(r"(^|_)(n|num|count|size|len|length|max|min|k|levels?|order|degree|bins?)($|_)", param):
        return "size_or_count"
    if re.search(r"(sigma|radius|width|window|scale|alpha|beta|gamma|weight|thresh|threshold|gain)", param):
        return "smoothing_or_threshold"
    return "other"


class KnobHook:
    """Varies every numeric keyword default; reports the ones that never change the output."""
    key = "knobs"

    def __call__(self, name, ins, fn, args, kwargs, res, verdict):
        if name in KNOB_SKIP_SLOW:
            return {"slow": True}
        if "nondeterministic" in (verdict.get("check") or ()):
            return {}                            # two calls already differ: nothing to compare
        try:
            params = inspect.signature(fn).parameters.values()
        except (TypeError, ValueError):
            return {}
        base = lc._stable(name, res)
        adapter = lc._cf().ADAPTERS.get(name)
        out = {}
        if degenerate(base):
            out["__degenerate__"] = True
        for p in params:
            if p.default is inspect.Parameter.empty or p.name in _NOT_A_KNOB \
                    or p.kind not in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY):
                continue
            if p.name in kwargs:
                default = kwargs[p.name]
            else:
                default = p.default
            variants = knob_variants(default)
            if not variants:
                continue
            ran, changed, grey = 0, False, False
            for val in variants:
                kw = dict(kwargs)
                kw[p.name] = val
                try:
                    r = lc._call(fn, list(args), kw)
                    if adapter is not None:
                        r = adapter(r)
                except Exception:                # noqa: BLE001 - an out-of-range variant
                    continue
                ran += 1
                d = _differs(base, lc._stable(name, r))
                if d is None:
                    grey = True
                elif d:
                    changed = True
                    break
            out[p.name] = ("live" if changed else "unmeasured" if (grey or not ran) else "dead")
        return out


def _flat_numbers(x, out, depth=0):
    """Every number in a result, in order (None when the structure is not numeric)."""
    if depth > 8:
        return out
    if isinstance(x, dict):
        for k in sorted(x, key=str):
            if _flat_numbers(x[k], out, depth + 1) is None:
                return None
        return out
    if isinstance(x, (list, tuple)):
        for v in x:
            if _flat_numbers(v, out, depth + 1) is None:
                return None
        return out
    a = np.asarray(x) if not isinstance(x, (str, bytes)) else None
    if a is None or a.dtype.kind not in "biufc":
        return None
    out.extend(np.asarray(a, np.complex128).ravel().tolist())
    return out


def _differs(base, r):
    """Did turning the knob change the output **beyond rounding**? ``True`` / ``False`` / ``None``.

    ★2026-10-11: ``foe_from_flow.iters`` は探針の入力で 1 巡目に収束し、巡回を増やした差は丸めの屑だけ。
    手元(Windows の BLAS)は最後の桁が動いて「効く」、CI(Linux)は完全一致で「効かない」—— 厳密一致の
    比較だと判定が環境で割れて CI だけ赤になった。相対 1e-9 より小さい差は「変わっていない」と数える。
    ★同じ日の 2 度目: 1e-9 の 1 本の線にすると、線のすぐ上にいる op(``flight_fit.dt``: 当てはめが真値へ
    ~1e-9 で戻る)が Python の版ごとに線の上下へ振れた。線を帯にする —— 1e-9 未満は「変わらない」、
    1e-6 超は「変わる」、その間は**判定しない**(None → "unmeasured"、どちらの台帳にも入れない)。
    """
    if lc.same(base, r) is True:
        return False
    a, b = _flat_numbers(base, []), _flat_numbers(r, [])
    if a is None or b is None or len(a) != len(b) or not a:
        return True
    a, b = np.asarray(a), np.asarray(b)
    fin = np.isfinite(a) & np.isfinite(b)
    if not np.array_equal(fin, np.isfinite(a)) or not np.array_equal(fin, np.isfinite(b)):
        return True
    if np.any(a[~fin] != b[~fin]) and not np.all(np.isnan(a[~fin]) & np.isnan(b[~fin])):
        return True
    if np.allclose(a[fin], b[fin], rtol=1e-9, atol=1e-12):
        return False
    if not np.allclose(a[fin], b[fin], rtol=1e-6, atol=1e-9):
        return True
    return None


def knob_failures(name, g):
    """``{"op.param": category}`` for the dead knobs of one op."""
    if not g or g.get("slow"):
        return {}
    deg = bool(g.get("__degenerate__"))
    return {"%s.%s" % (name, p): ("degenerate_output" if deg else knob_category(p))
            for p, s in g.items() if s == "dead"}


# --------------------------------------------------------------------------- #
# the whole audit                                                              #
# --------------------------------------------------------------------------- #
def hooks():
    """The probe hooks of (h) and (f), for ``ledger_contracts.run(hooks=...)``."""
    return [EmptyInputHook(), KnobHook()]


def run(ops=None, verbose=False):
    """Contract probe + the (h) / (f) hooks → the verdict (each carries ``"gaps"``)."""
    return lc.run(ops=ops, verbose=verbose, hooks=hooks())


def load_debt():
    with open(DEBT, encoding="utf-8") as f:
        return json.load(f)["debt"]


def observed(verdict, descriptions=True):
    """``{gap: {key: category}}`` observed now, plus ``scope`` counts."""
    found = {g: {} for g in GAPS}
    scope = {}
    if descriptions:
        bad, dscope = description_audit()
        found["description"] = bad
        scope["description"] = dscope
    emp = {"judged": 0, "promised": 0, "returned_unpromised": 0, "skip": 0}
    knobs = {"ops": 0, "params": 0, "live": 0, "dead": 0, "unmeasured": 0, "slow_ops": 0}
    for name, v in sorted(verdict.items()):
        g = (v.get("gaps") or {})
        e = g.get("empty")
        if e and e["outcome"] != "n/a":
            emp["judged"] += 1
            emp["skip"] += e["outcome"] == "skip"
            emp["promised"] += bool(e.get("promised"))
            emp["returned_unpromised"] += (e["outcome"] == "returned" and not e.get("promised"))
            c = empty_failure(e)
            if c:
                found["empty_input"][name] = c
        k = g.get("knobs")
        if k is not None:
            if k.get("slow"):
                knobs["slow_ops"] += 1
                continue
            knobs["ops"] += 1
            for p, s in k.items():
                if p.startswith("__"):
                    continue
                knobs["params"] += 1
                knobs[s] += 1
            found["dead_knob"].update(knob_failures(name, k))
    scope["empty_input"] = emp
    scope["dead_knob"] = knobs
    return found, scope


def new_gaps(found, debt, gaps=GAPS):
    """``[(gap, key, category)]`` observed now but not in the debt ledger."""
    return [(g, k, c) for g in gaps for k, c in sorted(found[g].items()) if k not in debt.get(g, {})]


def stale_gaps(found, debt, verdict=None, gaps=GAPS):
    """Debt rows that no longer fail. Probe-based rows of an op that was not judged here
    (skipped for a missing backend) are kept, so the ledger is the same in every environment."""
    out = []
    for g in gaps:
        for k in sorted(debt.get(g, {})):
            if k in found[g]:
                continue
            if g != "description" and verdict is not None:
                op = k.split(".", 1)[0] if g == "dead_knob" else k
                v = verdict.get(op)
                if v is None:
                    out.append((g, k, "not in the ledger tier any more"))
                    continue
                gg = v.get("gaps") or {}
                if g == "empty_input" and (gg.get("empty") or {}).get("outcome") in (None, "skip"):
                    continue
                if g == "dead_knob":
                    kn = gg.get("knobs")
                    if kn is None or kn.get("slow") or kn.get(k.split(".", 1)[1]) in (None, "unmeasured"):
                        continue
            out.append((g, k, "passes now"))
    return out


def write_debt(found):
    doc = {"_note": "記述・空入力・効かないノブの既存分(tests/test_op_descriptions.py と "
                    "tests/test_ledger_contracts.py のラチェット)。"
                    "増えたら落ち、直って通るようになっても落ちる(= 縮むしかない)。key -> 理由の区分。",
           "_written": time.strftime("%Y-%m-%d"),
           "counts": {g: len(found[g]) for g in GAPS},
           "debt": found}
    with open(DEBT, "w", encoding="utf-8", newline="\r\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")


def summary(found, scope):
    lines = []
    for g in GAPS:
        cats = {}
        for c in found[g].values():
            cats[c] = cats.get(c, 0) + 1
        lines.append("  %-12s %4d  %s  scope=%s" % (g, len(found[g]), dict(sorted(cats.items())), scope.get(g)))
    return "\n".join(lines)


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(description="Description / empty-input / dead-knob gaps of the ledger.")
    p.add_argument("--write", action="store_true", help="rewrite docs/LEDGER_GAP_DEBT.json (only to shrink it)")
    p.add_argument("--json", help="dump the observed gaps and scopes to this path")
    p.add_argument("-v", "--verbose", action="store_true")
    a = p.parse_args(argv)
    t0 = time.perf_counter()
    verdict = run(verbose=a.verbose)
    found, scope = observed(verdict)
    print(summary(found, scope))
    print("(%.1f s)" % (time.perf_counter() - t0))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump({"found": found, "scope": scope,
                       "gaps": {n: v.get("gaps") for n, v in verdict.items()}},
                      f, ensure_ascii=False, indent=1, default=str)
    if a.write:
        write_debt(found)
    return 0


if __name__ == "__main__":
    sys.exit(main())
