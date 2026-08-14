"""Ground-truth contracts for macro ("DNA") operators — condensed evolved champions.

A macro op must reproduce its champion pipeline EXACTLY. These tests prove, per
entry in ``data/macro_champions.json``:

  * it is registered with ``halcon=""`` (a new capability, no coverage claim) and
    the declared in/out sorts;
  * running the registered op is BIT-IDENTICAL to running the frozen name-pinned
    stages stage-by-stage on real evaluation images (faithful condensation);
  * its ``a,b`` knobs are frozen (output invariant to them);
  * the recorded provenance score is recomputable on the problem's holdout/locked
    splits (the DNA is the champion evolution found, not a drifted copy);
  * it is a candidate the evolutionary search can select (self-expanding registry).

The universal op-contract tests (finite / deterministic / declared-sort on the
degenerate battery) already cover macro ops automatically via the registry sweep.
"""
from __future__ import annotations

import os

import numpy as np
import pytest

import ops
import problems
from backends_macro import _DNA_PATH, _load_entries

ENTRIES = _load_entries()
IDS = [e.get("name", f"entry{i}") for i, e in enumerate(ENTRIES)]


def _stages(e):
    return ops.decode_by_names([(s["op"], s["a"], s["b"]) for s in e["stages"]])


def test_dna_file_present_and_nonempty():
    assert os.path.exists(_DNA_PATH), "data/macro_champions.json missing"
    assert ENTRIES, "expected at least one macro champion entry"


@pytest.mark.parametrize("e", ENTRIES, ids=IDS)
def test_macro_registered_with_new_capability_marker(e):
    assert e["name"] in ops._BY_NAME, f"{e['name']} not registered (backends_macro wired into ops.py?)"
    op = ops._BY_NAME[e["name"]]
    assert op.halcon == "", "a macro op makes no HALCON coverage claim"
    assert op.in_sort == e["in_sort"]
    assert op.out_sort == e["out_sort"]
    assert op.name in ops.RT


@pytest.mark.parametrize("e", ENTRIES, ids=IDS)
def test_macro_is_a_selectable_candidate(e):
    """Self-expanding registry: the DNA op is a candidate the next evolution can
    pick in a slot of its in_sort (or the sort-neutral 'any')."""
    names = [op.name for op in ops._candidates(e["in_sort"])]
    assert e["name"] in names


@pytest.mark.parametrize("e", ENTRIES, ids=IDS)
def test_macro_bit_identical_to_champion_pipeline(e):
    """The registered op == running the frozen stages stage-by-stage, on real
    evaluation images (where the pipeline is clean, so the op's final sanitize is a
    no-op and equality is exact — the faithful-condensation guarantee)."""
    stages = _stages(e)
    fn = ops.RT[e["name"]]
    prob = problems.PROBLEMS[e["problem"]]
    cfg = e["provenance"]["config"]
    banks = [
        prob.make(cfg["n_train"], cfg["size"], cfg["seed"])["input"],
        prob.make(cfg["n_holdout"], cfg["size"], cfg["seed"] + 10_000)["input"],
    ]
    imgs = [b[i] for b in banks for i in range(min(4, len(b)))]
    imgs += [np.clip(np.random.default_rng(k).random((48, 48)), 0, 1) for k in range(3)]
    for img in imgs:
        pipe_out = ops.run_stages(stages, img.copy())
        assert np.all(np.isfinite(np.asarray(pipe_out, np.float64))), "pipeline non-finite on eval image"
        macro_out = fn(img.copy(), 0.5, 0.5)
        assert np.array_equal(np.asarray(macro_out, np.float64), np.asarray(pipe_out, np.float64)), \
            f"{e['name']} diverges from its champion pipeline"


@pytest.mark.parametrize("e", ENTRIES, ids=IDS)
def test_macro_knobs_are_frozen(e):
    """A macro op is a fixed pipeline with evolved knobs baked in: its output does
    not depend on the op's own a,b."""
    fn = ops.RT[e["name"]]
    img = np.clip(np.random.default_rng(7).random((40, 40)), 0, 1)
    base = fn(img.copy(), 0.5, 0.5)
    for a, b in [(0.0, 0.0), (1.0, 1.0), (0.2, 0.9)]:
        assert np.array_equal(np.asarray(fn(img.copy(), a, b), np.float64),
                              np.asarray(base, np.float64)), f"{e['name']} is knob-sensitive"


@pytest.mark.parametrize("e", ENTRIES, ids=IDS)
def test_macro_provenance_score_recomputable(e):
    """The stored full-registry score is reproducible on the problem's splits — the
    DNA faithfully carries the champion evolution measured."""
    prov = e["provenance"]
    prob = problems.PROBLEMS[e["problem"]]
    cfg = prov["config"]
    stages = _stages(e)
    ho = prob.make(cfg["n_holdout"], cfg["size"], cfg["seed"] + 10_000)
    lk = prob.make(cfg.get("n_locked", cfg["n_holdout"]), cfg["size"], cfg["seed"] + 20_000)
    assert round(prob.score_stages(stages, ho), 4) == prov["score"]["holdout"]
    assert round(prob.score_stages(stages, lk), 4) == prov["score"]["locked_holdout"]


@pytest.mark.parametrize("e", ENTRIES, ids=IDS)
def test_macro_provenance_is_honest(e):
    """Provenance must carry the honest verdict fields (no silent 'we won')."""
    prov = e["provenance"]
    assert "beats_hand_on_locked_holdout" in prov
    assert "baselines" in prov and "hand" in prov["baselines"]
    assert isinstance(prov["beats_hand_on_locked_holdout"], bool)
    # score_matches_evolution must be truthful: if no op is overridden it should hold.
    if not prov.get("overridden_ops"):
        assert prov.get("score_matches_evolution") is True
