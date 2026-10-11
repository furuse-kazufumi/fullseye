# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Contract probe for EVERY typed-ledger op (the index's ``ledger`` tier).

Each ledger op is called on representative inputs built from its declared input sorts
and judged on four contracts:

1. ``raises``           -- it runs without raising.  A ``ValueError`` is a typed refusal
                           (what the existing ledger gates accept), recorded separately as
                           ``refused`` because the op was then never exercised.
2. ``nonfinite``        -- numeric output is finite (ops in
                           ``chain_fuzz.NONFINITE_BY_CONTRACT`` are exempt by contract).
3. ``sort``             -- the output (after ``ADAPTERS``) passes the declared out-sort
                           predicate ``chain_fuzz.TYPE_CHECKS[out]``.
4. ``nondeterministic`` -- two calls on deep copies of the same arguments return
                           identical values.

Plus the reach checks ``refused`` / ``no_input`` / ``unbindable``: an op the probe could
not exercise is NOT silently dropped; it is a debt row like any other failure.

Inputs reuse the chain fuzzer (``tools/chain_fuzz``): its generators seed a type pool,
its ``OP_ARG_BUILDERS`` / ``_bind_args`` bind the arguments, and sorts that have no
generator are filled by the **declared** producer (``type_recipes``) -- chosen from the
ledger declarations alone, never from which op happened to succeed, so the inputs do
not drift with the environment.

An op whose optional backend is missing (``ImportError`` / ``NotImplementedError``, or
an upstream producer missing for that reason) is ``skip`` with the reason -- neither a
pass nor a failure, so the committed debt does not differ by environment.

``py -3.11 tools/ledger_contracts.py --write`` rewrites ``docs/LEDGER_CONTRACT_DEBT.json``
from a fresh probe.  Use it only to SHRINK the debt after fixing ops: the gate
(``tests/test_ledger_contracts.py``) refuses new debt.
"""
from __future__ import annotations

import copy
import importlib
import json
import numbers
import os
import random
import sys
import time
import warnings
import zlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

DEBT = os.path.join(ROOT, "docs", "LEDGER_CONTRACT_DEBT.json")

#: The judged contracts (the keys of the debt ledger), in report order.
CHECKS = ("refused", "no_input", "unbindable", "raises", "nonfinite", "sort",
          "nondeterministic")

_SEED = 20261011

#: Reason categories per check (``category()`` maps a failure detail onto one of these;
#: ``raises`` is ``raw_<ExceptionType>``).
CATEGORIES = {
    "refused": {"valueerror_on_probe"},
    "no_input": {"no_producer_value"},
    "unbindable": {"no_hint", "builder_raised"},
    "raises": {"raw_*"},
    "nonfinite": {"undocumented_nan_inf"},
    "sort": {"out_sort_mismatch", "returned_none", "adapter_failed"},
    "nondeterministic": {"global_rng", "fresh_state", "other"},
}

#: Size-only keyword overrides for the probe (measured 2026-10-11): these knobs scale the
#: work, not the meaning, and without them two ops took 40 s of an 82 s probe --
#: ``video_cube_orbit`` renders 36 frames of 256^2 by default (14.8 s per call) and
#: ``render_beauty`` 512^2 with 2x supersampling (5.0 s per call).
SIZE_OVERRIDES = {
    "video_cube_orbit": {"n_frames": 4, "size": 48},
    "render_beauty": {"size": 96},
}

#: Environment variables that point ops at local datasets. Cleared while probing so a
#: developer machine with a dataset unpacked judges the same as CI (no dataset).
_DATASET_ENV = ("FULLSEYE_TID2013_DATA", "FULLSEYE_AIRHOCKEY_DATA", "FULLSEYE_DATA_DIR",
                "FULLSEYE_KENNEY_DIR")


def _cf():
    import chain_fuzz
    return chain_fuzz


def ledger_ops():
    """The index's ledger tier as ``[(name, ledger_module, in_sorts, out_sort, fn)]``.

    Enumerated exactly like ``docs/OP_INDEX.json`` (``api.ledger_rows``: the first family
    wins a duplicated name; names taken by the registry / n-ary tiers are not ledger rows),
    and the callable is taken from the row's own ledger table.
    """
    import api
    import opassist
    tables = dict(opassist._LEDGERS)
    out = []
    for r in api.ledger_rows():
        mod = importlib.import_module(r["ledger"])
        meta = getattr(mod, tables[r["ledger"]])[r["name"]]
        out.append((r["name"], r["ledger"], list(meta["in"]), meta["out"], meta["func"]))
    return out


# --------------------------------------------------------------------------- #
# value helpers                                                                #
# --------------------------------------------------------------------------- #
def _to_numpy(v):
    """torch tensors compare / scan as numpy; everything else unchanged."""
    if type(v).__module__.startswith("torch") and hasattr(v, "detach"):
        return v.detach().cpu().numpy()
    return v


def nonfinite(v, depth=0):
    """True when *v* holds a NaN / Inf anywhere a number lives (arrays, scalars,
    containers, plain objects' attributes)."""
    if depth > 6:
        return False
    v = _to_numpy(v)
    if isinstance(v, np.ndarray):
        if v.dtype.kind in "fc":
            return not bool(np.isfinite(v).all())
        if v.dtype.kind == "O":
            return any(nonfinite(x, depth + 1) for x in v.flat)
        return False
    if isinstance(v, (bool, np.bool_, numbers.Integral)):
        return False
    if isinstance(v, numbers.Number):
        try:
            return not bool(np.isfinite(v))
        except TypeError:
            return False
    if isinstance(v, dict):
        return any(nonfinite(x, depth + 1) for x in v.values())
    if isinstance(v, (list, tuple)):
        return any(nonfinite(x, depth + 1) for x in v)
    d = getattr(v, "__dict__", None)
    if isinstance(d, dict) and not callable(v) and not isinstance(v, type):
        return any(nonfinite(x, depth + 1) for x in d.values())
    return False


#: "this pair cannot be compared reliably" (counted and reported, never a pass or fail).
UNCOMPARABLE = "uncomparable"


def same(a, b, depth=0):
    """Structural equality: ``True`` / ``False`` / :data:`UNCOMPARABLE`."""
    if depth > 8:
        return True
    a, b = _to_numpy(a), _to_numpy(b)
    if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
        if not (isinstance(a, np.ndarray) and isinstance(b, np.ndarray)):
            return False
        if a.shape != b.shape or a.dtype != b.dtype:
            return False
        if a.dtype.kind == "O":
            return _all_same(list(a.flat), list(b.flat), depth)
        if a.dtype.kind in "fc":
            return bool(np.array_equal(a, b, equal_nan=True))
        return bool(np.array_equal(a, b))
    num = (numbers.Number, np.bool_)
    if type(a) is not type(b) and not (isinstance(a, num) and isinstance(b, num)):
        return False
    if a is None or isinstance(a, (str, bytes, bool, np.bool_, numbers.Integral)):
        return bool(a == b)
    if isinstance(a, numbers.Number):
        if a != a and b != b:                    # both NaN
            return True
        return bool(a == b)
    if isinstance(a, dict):
        if set(a) != set(b):
            return False
        return _all_same([a[k] for k in a], [b[k] for k in a], depth)
    if isinstance(a, (list, tuple)):
        if len(a) != len(b):
            return False
        return _all_same(list(a), list(b), depth)
    if isinstance(a, (set, frozenset)):
        return a == b
    if callable(a):
        return getattr(a, "__qualname__", None) == getattr(b, "__qualname__", None)
    d = getattr(a, "__dict__", None)
    if isinstance(d, dict):
        return same(d, getattr(b, "__dict__", None), depth + 1)
    try:
        r = a == b
        if isinstance(r, (bool, np.bool_)):
            return bool(r)
    except Exception:                            # noqa: BLE001 - foreign objects
        pass
    return UNCOMPARABLE


def _all_same(xs, ys, depth):
    unc = False
    for x, y in zip(xs, ys):
        r = same(x, y, depth + 1)
        if r is False:
            return False
        unc = unc or r is UNCOMPARABLE
    return UNCOMPARABLE if unc else True


def optional_missing(exc):
    """The environment lacks an optional backend (not a defect of the op)."""
    return isinstance(exc, (ImportError, NotImplementedError))


def _rng(name):
    return np.random.default_rng((_SEED, zlib.crc32(name.encode("utf-8"))))


# --------------------------------------------------------------------------- #
# binding                                                                      #
# --------------------------------------------------------------------------- #
class Unbound(Exception):
    """No argument list could be built for the op (a gap of the probe, recorded)."""


def _io_builders():
    """The 3 ledger ops the chain fuzzer leaves out (``category == "io"``: files).

    Probed with a WAV the probe itself writes into the scratch cwd (``_scratch_cwd``).
    """
    def wav(pool, rng):
        import dsp
        p = "ledger_contract_probe.wav"
        dsp.write_wav(p, 0.5 * np.sin(np.linspace(0, 40 * np.pi, 800)), 8000)
        return [p], {}
    return {
        "read_wav": wav,
        "read_audio": wav,
        "write_wav": lambda pool, rng: (
            ["ledger_contract_probe_out.wav", 0.5 * np.sin(np.linspace(0, 20 * np.pi, 400))], {}),
    }


def bind(name, fn, ins, pool, cf, extra):
    """→ ``(args, kwargs)``; raises :class:`Unbound` (or the builder's own exception)."""
    args, kwargs = _bind_raw(name, fn, ins, pool, cf, extra)
    kwargs.update(SIZE_OVERRIDES.get(name, {}))
    return args, kwargs


def _bind_raw(name, fn, ins, pool, cf, extra):
    rng = _rng(name)
    if name in extra:
        args, kwargs = extra[name](pool, rng)
        return list(args), dict(kwargs)
    if name in cf.OP_ARG_BUILDERS:
        bound = cf.OP_ARG_BUILDERS[name](pool, rng)
        if isinstance(bound, list):
            bound = cf._bind_args(name, fn, bound, rng)
        if bound is None:
            raise Unbound("OP_ARG_BUILDERS / hints could not build the arguments")
        return list(bound[0]), dict(bound[1])
    gens = sorted(cf.make_generators())
    data = []
    for t in ins:
        if t == "any":
            t = gens[int(rng.integers(len(gens)))]
        data.append(pool[t][0])
    bound = cf._bind_args(name, fn, data, rng)
    if bound is None:
        raise Unbound("a required argument has no hint (PARAM_HINTS / OP_PARAM_HINTS)")
    return list(bound[0]), dict(bound[1])


def _call(fn, args, kwargs):
    # deep copies: an op that writes into its input (``integrate`` is in-place by design)
    # must not change what the second call -- or the next op -- sees.
    a, k = copy.deepcopy(args), copy.deepcopy(kwargs)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return fn(*a, **k)


# --------------------------------------------------------------------------- #
# one op                                                                       #
# --------------------------------------------------------------------------- #
def probe_one(name, ins, out, fn, pool, cf=None, extra=None):
    """Probe one op → ``{"status", "check", "detail", "sec", "result"}``.

    ``status`` is ``ok`` / ``fail`` / ``skip``; for ``fail``, ``check`` is the list of
    failed contracts (names from :data:`CHECKS`).
    """
    cf = _cf() if cf is None else cf
    extra = _io_builders() if extra is None else extra
    lack = sorted({t for t in ins if t != "any" and not pool.get(t)})
    if lack and name not in extra:
        return {"status": "fail", "check": ["no_input"],
                "detail": "no value of sort %s" % ", ".join(lack)}
    try:
        args, kwargs = bind(name, fn, ins, pool, cf, extra)
    except Unbound as e:
        return {"status": "fail", "check": ["unbindable"], "detail": str(e)}
    except Exception as e:                       # noqa: BLE001 - a builder broke
        if optional_missing(e):
            return {"status": "skip", "detail": "optional backend missing while binding: "
                    "%s: %s" % (type(e).__name__, str(e)[:120])}
        return {"status": "fail", "check": ["unbindable"],
                "detail": "argument builder raised %s: %s" % (type(e).__name__, str(e)[:120])}
    t0 = time.perf_counter()
    try:
        res = _call(fn, args, kwargs)
    except Exception as e:                       # noqa: BLE001 - the point of the probe
        if optional_missing(e):
            return {"status": "skip", "detail": "optional backend missing: %s: %s"
                    % (type(e).__name__, str(e)[:120])}
        if isinstance(e, ValueError):
            return {"status": "fail", "check": ["refused"],
                    "detail": "ValueError: %s" % str(e)[:160]}
        return {"status": "fail", "check": ["raises"],
                "detail": "%s: %s" % (type(e).__name__, str(e)[:160])}
    sec = time.perf_counter() - t0
    adapter = cf.ADAPTERS.get(name)
    if adapter is not None:
        try:
            res = adapter(res)
        except Exception as e:                   # noqa: BLE001
            return {"status": "fail", "check": ["sort"], "sec": sec,
                    "detail": "sort: result adapter failed: %s: %s"
                    % (type(e).__name__, str(e)[:120])}
    failures = []
    if name not in cf.NONFINITE_BY_CONTRACT and nonfinite(res):
        failures.append(("nonfinite", "NaN/Inf in the output"))
    pred = cf.TYPE_CHECKS.get(out)
    if res is None:
        failures.append(("sort", "declared %r but returned None" % out))
    elif pred is None:
        failures.append(("sort", "declared sort %r has no predicate in TYPE_CHECKS" % out))
    else:
        try:
            ok = bool(pred(res))
        except Exception:                        # noqa: BLE001 - a predicate that chokes = mismatch
            ok = False
        if not ok:
            failures.append(("sort", "declared %r but returned %s%s" % (
                out, type(res).__name__, getattr(res, "shape", ""))))
    eq = True
    try:
        res2 = _call(fn, args, kwargs)
        if adapter is not None:
            res2 = adapter(res2)
        eq = same(res, res2)
    except Exception as e:                       # noqa: BLE001
        failures.append(("nondeterministic", "other: the second identical call raised "
                         "%s: %s" % (type(e).__name__, str(e)[:100])))
    else:
        if eq is False:
            failures.append(("nondeterministic", why_nondeterministic(fn, args, kwargs, adapter)))
    v = {"status": "ok", "sec": sec, "result": res, "comparable": eq is not UNCOMPARABLE}
    if failures:
        v.update(status="fail", check=[c for c, _ in failures],
                 detail="; ".join("%s: %s" % f for f in failures))
    return v


def why_nondeterministic(fn, args, kwargs, adapter):
    """Reason category: does seeding the global RNGs make the op repeatable?"""
    outs = []
    # the global RNG state is put back afterwards: seeding it here must not leak into
    # whatever runs next in the same process.
    np_state, py_state = np.random.get_state(), random.getstate()
    try:
        for _ in range(2):
            np.random.seed(_SEED & 0xFFFFFFFF)
            random.seed(_SEED)
            try:
                r = _call(fn, args, kwargs)
                outs.append(adapter(r) if adapter is not None else r)
            except Exception:                    # noqa: BLE001
                return "other: differs between calls (and raised when re-run seeded)"
    finally:
        np.random.set_state(np_state)
        random.setstate(py_state)
    if same(outs[0], outs[1]) is True:
        return "global_rng: repeatable only when np.random / random are seeded"
    return ("fresh_state: differs even with the global RNGs seeded "
            "(unseeded default_rng / clock / ordering)")


# --------------------------------------------------------------------------- #
# every op                                                                     #
# --------------------------------------------------------------------------- #
def run(ops=None, verbose=False):
    """Probe every op → ``{name: verdict}`` (verdicts keep no results, to stay small).

    Ops run in index order, in rounds: an op whose input sort has no generator waits
    until the sort's **declared** producer has run and returned a value of that sort.
    """
    cf = _cf()
    ops = ledger_ops() if ops is None else ops
    gens = cf.make_generators()
    extra = _io_builders()
    verdict = {}
    saved_env = {k: os.environ.pop(k) for k in _DATASET_ENV if k in os.environ}
    try:
        _run(ops, cf, gens, extra, verdict, verbose)
    finally:
        os.environ.update(saved_env)
    return verdict


def _run(ops, cf, gens, extra, verdict, verbose):
    with cf._scratch_cwd():
        base = np.random.default_rng(_SEED)
        pool = {t: [g(base)] for t, g in sorted(gens.items())}
        recipe = cf.type_recipes(list(ops), gens)
        producer = {t: r[-1] for t, r in recipe.items() if r}
        why_empty = {}                          # sort -> what its producer did instead
        pending = list(ops)
        while pending:
            progressed, rest = False, []
            for op in pending:
                name, _led, ins, out, fn = op
                if name not in extra and any(not pool.get(t) for t in ins if t != "any"):
                    rest.append(op)
                    continue
                v = probe_one(name, ins, out, fn, pool, cf, extra)
                res = v.pop("result", None)
                verdict[name] = v
                progressed = True
                if verbose:
                    print("%-4s %-38s %6.2fs %s" % (v["status"], name, v.get("sec", 0.0),
                                                    v.get("detail", "")[:100]), flush=True)
                if producer.get(out) == name and not pool.get(out):
                    bad = set(v.get("check") or ()) & {"sort", "nonfinite"}
                    if "sec" in v and not bad and v["status"] != "skip":
                        pool[out] = [res]
                    else:
                        why_empty[out] = "%s %s (%s)" % (name, v["status"], v.get("detail", ""))
            if not progressed:
                for name, _led, ins, _out, _fn in rest:
                    lack = sorted({t for t in ins if t != "any" and not pool.get(t)})
                    why = "; ".join("%s <- %s" % (t, why_empty.get(t, "no declared producer"))
                                    for t in lack)
                    if any(" skip " in why_empty.get(t, "") for t in lack):
                        verdict[name] = {"status": "skip",
                                         "detail": "upstream producer skipped: " + why}
                    else:
                        verdict[name] = {"status": "fail", "check": ["no_input"],
                                         "detail": "no value of sort %s: %s" % (", ".join(lack), why)}
                break
            pending = rest


def category(check, detail):
    """A coarse, stable reason category for one failure (the detail text drifts)."""
    if check == "raises":
        return "raw_" + detail.split(":", 1)[0]
    if check == "nondeterministic":
        for part in detail.split("; "):
            if part.startswith("nondeterministic: "):
                return part[len("nondeterministic: "):].split(":", 1)[0]
        return "other"
    if check == "sort":
        if "returned None" in detail:
            return "returned_none"
        if "adapter failed" in detail:
            return "adapter_failed"
        return "out_sort_mismatch"
    if check == "nonfinite":
        return "undocumented_nan_inf"
    if check == "refused":
        return "valueerror_on_probe"
    if check == "unbindable":
        return "builder_raised" if "builder raised" in detail else "no_hint"
    if check == "no_input":
        return "no_producer_value"
    return "other"


def debt_from(verdict):
    """``{check: {op: reason_category}}`` -- the committed shape."""
    out = {c: {} for c in CHECKS}
    for name, v in sorted(verdict.items()):
        if v["status"] == "fail":
            for c in v["check"]:
                out[c][name] = category(c, v["detail"])
    return out


def known_category(check, cat):
    """Is *cat* one of the reason categories of *check*?"""
    if check == "raises":
        return isinstance(cat, str) and cat.startswith("raw_") and len(cat) > 4
    return cat in CATEGORIES.get(check, ())


def new_violations(verdict, debt):
    """``[(check, op, detail)]`` for failures the debt ledger does not list."""
    out = []
    for name, v in sorted(verdict.items()):
        if v["status"] != "fail":
            continue
        for c in v["check"]:
            if name not in debt.get(c, {}):
                out.append((c, name, v["detail"]))
    return out


def stale_debt(verdict, debt):
    """``[(check, op, now)]`` for debt rows that no longer fail that check.

    A ``skip`` (backend missing here) is NOT a pass: the row stays, so the ledger is the
    same in every environment. A row for an op that left the ledger tier is stale.
    """
    out = []
    for c in CHECKS:
        for name in sorted(debt.get(c, {})):
            v = verdict.get(name)
            if v is None:
                out.append((c, name, "not in the ledger tier any more"))
            elif v["status"] == "skip":
                continue
            elif v["status"] == "ok" or c not in v["check"]:
                out.append((c, name, "%s %s" % (v["status"], v.get("check") or "")))
    return out


def executed(verdict):
    """Ops that returned a value (judged on finite / sort / determinism)."""
    reach = {"refused", "no_input", "unbindable", "raises"}
    return sorted(n for n, v in verdict.items() if "sec" in v
                  and not (v["status"] == "fail" and set(v["check"]) & reach))


def summary(verdict):
    debt = debt_from(verdict)
    status = {s: sum(1 for v in verdict.values() if v["status"] == s)
              for s in ("ok", "fail", "skip")}
    lines = ["ledger ops %d  %s" % (len(verdict), status)]
    for c in CHECKS:
        cats = {}
        for cat in debt[c].values():
            cats[cat] = cats.get(cat, 0) + 1
        lines.append("  %-17s %4d  %s" % (c, len(debt[c]), dict(sorted(cats.items()))))
    return "\n".join(lines)


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(description="Contract probe for every typed-ledger op.")
    p.add_argument("--write", action="store_true",
                   help="rewrite docs/LEDGER_CONTRACT_DEBT.json (only to shrink it)")
    p.add_argument("--json", help="dump every verdict (with details) to this path")
    p.add_argument("-v", "--verbose", action="store_true")
    a = p.parse_args(argv)
    t0 = time.perf_counter()
    verdict = run(verbose=a.verbose)
    print(summary(verdict))
    print("(%.1f s)" % (time.perf_counter() - t0))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(verdict, f, ensure_ascii=False, indent=1, default=str)
    if a.write:
        write_debt(verdict)
    return 0


def write_debt(verdict):
    debt = debt_from(verdict)
    doc = {"_note": "型付き台帳の全 op に対する契約違反の既存分(tests/test_ledger_contracts.py の"
                    "ラチェット)。増えたら落ち、直って通るようになっても落ちる(= 縮むしかない)。"
                    "op 名 -> 理由の区分。詳細は py -3.11 tools/ledger_contracts.py -v で見る。",
           "_written": time.strftime("%Y-%m-%d"),
           "counts": {c: len(debt[c]) for c in CHECKS},
           "debt": debt}
    with open(DEBT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")


if __name__ == "__main__":
    sys.exit(main())
