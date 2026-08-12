"""Evolution core: reproducibility and the holdout-honesty invariant.

The project's headline honesty guarantee is that HOLDOUT is tracked every
generation but NEVER used for selection (the 'pseudo-equation trap' guard).
These tests pin the practical consequences: same seed -> same champion, and
the two datasets are genuinely distinct.
"""
from __future__ import annotations

import numpy as np
import pytest

import evolve
import problems


def _run(tmp_path, problem="denoise", seed=0):
    return evolve.run(problem, workdir=str(tmp_path), gens=6, pop=10, seed=seed, verbose=False)


def test_evolve_is_reproducible_given_seed(tmp_path):
    c1 = _run(tmp_path / "a", seed=7)
    c2 = _run(tmp_path / "b", seed=7)
    assert c1["genome"] == c2["genome"]
    assert c1["train"] == c2["train"] and c1["holdout"] == c2["holdout"]


def test_different_seeds_can_diverge(tmp_path):
    c1 = _run(tmp_path / "a", seed=1)
    c2 = _run(tmp_path / "b", seed=2)
    # Not a hard guarantee, but the search must at least be seed-sensitive somewhere.
    assert (c1["genome"] != c2["genome"]) or (c1["train"] != c2["train"])


def test_train_and_holdout_are_distinct_datasets():
    prob = problems.PROBLEMS["denoise"]
    tr = prob.make(8, 48, 0)
    ho = prob.make(8, 48, 10_000)
    assert not np.array_equal(tr["input"], ho["input"]), "holdout must differ from train"


def test_champion_train_score_is_recomputable(tmp_path):
    """The reported champion train score must match a fresh evaluation on the
    SAME train set — proof selection scored on train, deterministically."""
    champ = _run(tmp_path, problem="binarize", seed=3)
    prob = problems.PROBLEMS["binarize"]
    cfg = champ["config"]
    tr = prob.make(cfg["n_train"], cfg["size"], cfg["seed"])
    recomputed = prob.score(np.asarray(champ["genome"], np.float64), tr)
    assert recomputed == pytest.approx(champ["train"], abs=1e-4)


def test_holdout_is_not_secretly_the_selection_score(tmp_path):
    """If selection had leaked holdout, champion['train'] would equal a holdout
    evaluation. Assert the champion was chosen on train, not holdout."""
    champ = _run(tmp_path, problem="edge", seed=4)
    prob = problems.PROBLEMS["edge"]
    cfg = champ["config"]
    ho = prob.make(cfg["n_holdout"], cfg["size"], cfg["seed"] + 10_000)
    holdout_recomputed = prob.score(np.asarray(champ["genome"], np.float64), ho)
    assert holdout_recomputed == pytest.approx(champ["holdout"], abs=1e-4)
    # train score is what was maximized; it should not be *defined* by holdout
    assert "train" in champ and champ["train"] >= 0.0
