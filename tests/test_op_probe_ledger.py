"""CI-resident op probe: every registry op runs on structured inputs through the facade.

Counts THREE things separately (memory rule: coverage must distinguish "ran /
refused every time / could not build an argument"), because a single success
number lets a permanently broken op hide inside "861/861 callable":

* ``fallback`` — the op body raised and the ledger recorded it (``backend_safe``);
* ``raised``   — a core op without a guard raised through the facade;
* ``degenerate`` — the op ran but returned its input unchanged or a constant on a
  structured, non-constant input.

Every degenerate op must be listed in ``docs/OP_PROBE_ALLOWLIST.json`` with a
reason a reviewer verified (knob 0.5 = "no transform", no holes in the probe mask,
no template set, contract says constant …). A NEW degenerate op, or a fallback /
raise on the probe inputs, fails this test — that is the point.

This is the permanent form of the 2026-09-02 "runtime degeneracy" audit
(``out/robustness-audit-2026-09-02/probe_runtime_degeneracy.py``), run on every CI.
"""
import json
import os
import warnings

import numpy as np
import pytest

import api
import backend_safe as bs
import ops

HERE = os.path.dirname(os.path.abspath(__file__))
ALLOWLIST = os.path.join(HERE, "..", "docs", "OP_PROBE_ALLOWLIST.json")


def _img(n=48):
    y, x = np.mgrid[0:n, 0:n]
    g = np.clip(0.5 + 0.3 * np.sin(x / 5.0) * np.cos(y / 7.0), 0, 1)
    g[10:20, 25:40] = 0.9
    g[30:42, 8:18] = 0.1
    return g


def _inputs():
    g = _img()
    return {
        "image": g,
        "region": (g > 0.55).astype(np.float64),
        "color": np.stack([g, np.roll(g, 5, 0), np.roll(g, 9, 1)], -1),
        "volume": np.stack([np.roll(_img(24), k, 0) for k in range(10)], 0),
    }


def _probe():
    ins = _inputs()
    out = {}
    for op in ops.REGISTRY:
        v = ins.get(op.in_sort)
        if v is None:
            out[op.name] = ("uncallable", op.in_sort)
            continue
        bs.clear_fallbacks()
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                res = api.apply(v, op.name, 0.5, 0.5, on_error="fallback")
        except Exception as e:                      # noqa: BLE001 - core op without a guard
            out[op.name] = ("raised", "%s: %s" % (type(e).__name__, e))
            continue
        fb = bs.fallbacks()
        if fb:
            out[op.name] = ("fallback", fb[0]["error"])
            continue
        tag = "ok"
        if isinstance(res, np.ndarray) and res.size > 1:
            if res.shape == v.shape and np.array_equal(res, v):
                tag = "identity"
            elif np.all(res == res.flat[0]):
                tag = "constant"
        out[op.name] = (tag, op.in_sort)
    return out


@pytest.fixture(scope="module")
def probe():
    return _probe()


@pytest.fixture(scope="module")
def allow():
    with open(ALLOWLIST, encoding="utf-8") as f:
        return json.load(f)


def test_probe_reaches_most_of_the_registry(probe):
    n_call = sum(1 for t, _ in probe.values() if t != "uncallable")
    assert n_call >= 0.7 * len(probe), (n_call, len(probe))


def test_no_op_falls_back_or_raises_on_the_structured_probe(probe):
    bad = {k: v for k, v in probe.items() if v[0] in ("fallback", "raised")}
    assert not bad, "ops that FAIL on the structured probe inputs (dead or broken):\n" + \
        "\n".join("  %s: %s" % (k, v[1]) for k, v in sorted(bad.items()))


def test_every_degenerate_op_is_allowlisted_with_a_reason(probe, allow):
    degenerate = {k: v[0] for k, v in probe.items() if v[0] in ("identity", "constant")}
    listed = allow["ops"]
    new = {k: t for k, t in degenerate.items() if k not in listed}
    assert not new, ("NEW degenerate ops (identity/constant on a structured input). Verify each "
                     "with other knobs/inputs and add it to docs/OP_PROBE_ALLOWLIST.json with the "
                     "reason, or fix it:\n" + "\n".join("  %s: %s" % kv for kv in sorted(new.items())))
    for k, entry in listed.items():
        assert isinstance(entry.get("reason"), str) and len(entry["reason"]) > 10, k


def test_allowlist_has_no_stale_entries(probe, allow):
    """An allowlisted op that is no longer degenerate (fixed, or removed) must be dropped,
    so the list stays an honest picture rather than a growing waiver."""
    degenerate = {k for k, v in probe.items() if v[0] in ("identity", "constant")}
    stale = [k for k in allow["ops"] if k not in degenerate and k in probe]
    gone = [k for k in allow["ops"] if k not in probe]
    assert not stale and not gone, {"no_longer_degenerate": stale, "not_in_registry": gone}
