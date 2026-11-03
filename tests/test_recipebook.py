"""Coverage recipes (fullseye/recipebook): every family has one, every recipe really runs.

Gates (none of them may be loosened to make a recipe pass — fix the recipe, or the op):

1. **Floor**: at least ``FLOOR_RECIPES`` coverage recipes (the index also carries recipes.py's 25).
2. **Family coverage**: every docs/ops family is the ``family`` of at least one recipe, and that family
   really holds one of the recipe's stage ops (a recipe cannot claim a family it does not touch).
3. **Types connect**: zero type cuts — each stage's input sort (OP_GRAPH ``inputs[j]``) equals the sort the
   referenced stage declared as output. At run time the values are also checked against chain_fuzz's
   ``TYPE_CHECKS`` predicates for those sorts (a declaration that lies is caught here, not downstream).
4. **e2e**: each recipe runs on two sample variants without an exception, every stage returns something,
   the final output is not degenerate (no numbers / no finite number / constant), the output moves when
   the input moves (a constant answer is not a measurement), and every ``expect`` truth gate holds on
   both variants.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

os.environ.setdefault("FULLSEYE_DEVICE", "cpu")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import fullseye  # noqa: E402,F401  (puts the engine modules on sys.path)
from fullseye import recipebook as rb  # noqa: E402

FLOOR_RECIPES = 100

# A recipe may opt out of the "output moves with the input" check only with a written reason
# (e.g. the op returns a pass/fail verdict that is legitimately the same on both variants).
STATIC_OK = {r["name"]: r["static_ok"] for r in rb.RECIPES if r.get("static_ok")}


def _type_checks():
    try:
        from chain_fuzz import TYPE_CHECKS
    except Exception:  # noqa: BLE001
        return {}
    return TYPE_CHECKS


TYPE_CHECKS = _type_checks()


def test_recipe_floor():
    assert len(rb.RECIPES) >= FLOOR_RECIPES, (len(rb.RECIPES), FLOOR_RECIPES)


def test_every_family_has_a_recipe():
    fams = rb.families()
    assert len(fams) >= 50, "docs/ops families went missing: %d" % len(fams)
    have = {r["family"] for r in rb.RECIPES}
    missing = sorted(set(fams) - have)
    assert not missing, "families without a recipe: %s" % missing
    unknown = sorted(have - set(fams))
    assert not unknown, "recipes name families that docs/ops does not have: %s" % unknown


@pytest.mark.parametrize("name", rb.names())
def test_recipe_is_well_formed(name):
    r = rb.get(name)
    for key in ("name", "family", "task", "task_class", "input_sort", "sample", "stages", "note"):
        assert key in r, (name, key)
    assert r["task_class"] in rb.TASK_CLASSES, (name, r["task_class"])
    assert r["stages"], name
    assert r["sample"] in rb.SAMPLES, (name, r["sample"])
    fam_ops = rb.op_families()
    for st in r["stages"]:
        assert rb.edge(st["op"]) is not None, (name, st["op"], "not in OP_GRAPH")
    touched = set().union(*(fam_ops.get(st["op"], set()) for st in r["stages"]))
    assert r["family"] in touched, (name, r["family"], sorted(touched))
    assert len(r["note"]) >= 20, (name, "write what the recipe is for and why these stages")


@pytest.mark.parametrize("name", rb.names())
def test_recipe_types_connect(name):
    r = rb.get(name)
    bad = [row for row in rb.connections(r) if not row[4]]
    assert not bad, "%s: type cuts (stage, arg, got, want): %s" % (name, [row[:4] for row in bad])


def _check_stage_types(r, outs):
    """宣言の出力型と実際の値(chain_fuzz の述語)。述語の無い型は見ない。"""
    lies = []
    for i, st in enumerate(r["stages"], 1):
        e = rb.edge(st["op"])
        o = e.get("output")
        pred = TYPE_CHECKS.get(o) or TYPE_CHECKS.get(rb.norm_sort(o))
        if pred is not None and o not in ("any", "poly"):
            try:
                ok = bool(pred(outs[i]))
            except Exception:  # noqa: BLE001
                ok = False
            if not ok:
                lies.append((i, st["op"], o, type(outs[i]).__name__, getattr(outs[i], "shape", None)))
    return lies


def _run_variant(r, variant):
    s = rb.sample(r, variant)
    out, outs = rb.run(r, s["value"], s["aux"])
    for i in range(1, len(r["stages"]) + 1):
        v = outs[i]
        assert v is not None, (r["name"], "stage %d returned None" % i)
        if isinstance(v, np.ndarray):
            assert v.size > 0, (r["name"], "stage %d returned an empty array" % i)
    return s, out, outs


@pytest.mark.parametrize("name", rb.names())
def test_recipe_runs_end_to_end(name):
    r = rb.get(name)
    s0, out0, outs0 = _run_variant(r, 0)
    s1, out1, outs1 = _run_variant(r, 1)
    lies = _check_stage_types(r, outs0)
    assert not lies, "%s: declared out sort does not match the value (stage, op, sort, type, shape): %s" % (name, lies)
    for v, out in ((0, out0), (1, out1)):
        why = rb.degeneracy(out)
        assert why is None, "%s (variant %d): %s" % (name, v, why)
    if name not in STATIC_OK:
        f0, f1 = rb.fingerprint(out0), rb.fingerprint(out1)
        same = f0.shape == f1.shape and np.allclose(f0, f1, rtol=1e-9, atol=1e-12)
        assert not same, "%s: output does not change between two different inputs" % name
    for v, (s, out, outs) in enumerate(((s0, out0, outs0), (s1, out1, outs1))):
        bad = rb.check_expect(r, out, outs, s["truth"])
        assert not bad, "%s (variant %d): %s" % (name, v, bad)


def test_static_ok_reasons_are_written():
    for name, why in STATIC_OK.items():
        assert isinstance(why, str) and len(why) >= 20, name
