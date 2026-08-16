"""Multi-seed champion selection: the reported holdout must be the one it names.

robust.py has two holdouts available and they mean different things. The OBSERVED
split (seed+10000) is scored every generation by evolve.run; the LOCKED split
(seed+20000) is scored exactly once per seed. Reporting only the observed tally
while framing the file around honesty is the failure mode these tests pin.
"""
from __future__ import annotations

import json
import sys

import evolve
import robust


UNIT = "dB PSNR"


def _baseline(wd, hand=20.0, trivial=15.0, hand_locked=None, trivial_locked=None):
    h = {"holdout": hand}
    t = {"holdout": trivial}
    if hand_locked is not None:
        h["locked_holdout"] = hand_locked        # baseline.py scores hand on the locked split too
    if trivial_locked is not None:
        t["locked_holdout"] = trivial_locked
    (wd / "baseline_denoise.json").write_text(json.dumps({
        "hand": h, "trivial": t,
        "config": {"n_train": 4, "n_holdout": 4, "size": 32, "seed": 0},
    }), encoding="utf-8")


def _champ(seed, train, holdout, locked):
    c = {"problem": "denoise", "unit": UNIT, "genome": [], "pipeline": "stub%d" % seed,
         "train": train, "holdout": holdout, "seed": seed, "gens": 1, "pop": 2}
    if locked is not None:
        c["locked_holdout"] = locked
    return c


def _run_robust(wd, champs, monkeypatch):
    it = iter(champs)
    monkeypatch.setattr(evolve, "run", lambda *a, **k: next(it))
    monkeypatch.setattr(sys, "argv", ["robust.py", "--problem", "denoise",
                                      "--workdir", str(wd), "--seeds", str(len(champs)),
                                      "--gens", "1", "--pop", "2"])
    robust.main()
    return json.loads((wd / "robust_denoise.json").read_text(encoding="utf-8"))


def test_locked_split_is_tallied_separately_from_the_observed_one(tmp_path, monkeypatch):
    # Distinct thresholds per split: the locked tally MUST use the LOCKED-split
    # baseline (hand_locked=23 / trivial_locked=12), not the observed one (20 / 15).
    # With the observed thresholds applied to the locked champions you would get
    # 1 beat / 2 collapse; the honest tally against the locked baseline is 0 / 0.
    _baseline(tmp_path, hand=20.0, trivial=15.0, hand_locked=23.0, trivial_locked=12.0)
    champs = [_champ(0, 30.0, 25.0, 22.0),
              _champ(1, 20.0, 21.0, 14.0),
              _champ(2, 10.0, 14.0, 13.0)]
    s = _run_robust(tmp_path, champs, monkeypatch)

    assert s["n_beat_hand"] == 2 and s["n_collapse_below_trivial"] == 1
    # locked champions [22,14,13] vs locked baseline hand=23 / trivial=12
    assert s["n_beat_hand_locked"] == 0 and s["n_collapse_below_trivial_locked"] == 0
    assert s["baseline_hand_locked"] == 23.0 and s["baseline_trivial_locked"] == 12.0
    assert s["locked_holdout_spread"]["min"] == 13.0
    assert s["locked_holdout_spread"]["max"] == 22.0
    # the train-selected champion carries both numbers, not just the observed one
    assert s["selected_by_train"]["holdout"] == 25.0
    assert s["selected_by_train"]["locked_holdout"] == 22.0
    # and the report says which split each field came from
    assert "seed+10000" in s["split_note"] and "seed+20000" in s["split_note"]


def test_locked_tally_is_null_without_a_locked_baseline(tmp_path, monkeypatch):
    """Fail-closed: with champion locked scores but NO locked-split baseline, the
    locked spread is reported but the beat/collapse tally is null — the observed
    threshold is never substituted for the missing locked one."""
    _baseline(tmp_path, hand=20.0, trivial=15.0)          # observed thresholds only
    champs = [_champ(0, 30.0, 25.0, 22.0), _champ(1, 20.0, 21.0, 14.0)]
    s = _run_robust(tmp_path, champs, monkeypatch)

    assert s["locked_holdout_spread"] is not None          # champions carry locked scores
    assert s["n_beat_hand_locked"] is None and s["n_collapse_below_trivial_locked"] is None
    assert s["baseline_hand_locked"] is None


def test_missing_locked_score_leaves_the_locked_fields_null(tmp_path, monkeypatch):
    """Fail-closed: never substitute the observed split for a locked number we lack."""
    _baseline(tmp_path)
    champs = [_champ(0, 30.0, 25.0, None), _champ(1, 20.0, 21.0, 22.0)]
    s = _run_robust(tmp_path, champs, monkeypatch)

    assert s["locked_holdout_spread"] is None
    assert s["n_beat_hand_locked"] is None and s["n_collapse_below_trivial_locked"] is None
    assert s["n_beat_hand"] == 2                 # the observed tally still reports
    assert s["selected_by_train"]["locked_holdout"] is None


def test_real_evolution_run_populates_the_locked_tally(tmp_path):
    """End-to-end on the real evolve.run, which is what supplies locked_holdout."""
    import baseline
    sys.argv = ["baseline.py", "--problem", "denoise", "--workdir", str(tmp_path),
                "--random-samples", "10", "--n-train", "4", "--n-holdout", "4", "--size", "32"]
    baseline.main()
    sys.argv = ["robust.py", "--problem", "denoise", "--workdir", str(tmp_path),
                "--seeds", "2", "--gens", "2", "--pop", "6"]
    robust.main()
    s = json.loads((tmp_path / "robust_denoise.json").read_text(encoding="utf-8"))
    champ = json.loads((tmp_path / "champion_denoise.json").read_text(encoding="utf-8"))

    assert s["n_beat_hand_locked"] is not None
    assert s["n_collapse_below_trivial_locked"] is not None
    assert s["locked_holdout_spread"] is not None
    assert s["selected_by_train"]["locked_holdout"] == champ["locked_holdout"]
    lo = s["locked_holdout_spread"]
    assert lo["min"] <= champ["locked_holdout"] <= lo["max"]


def test_docstring_names_both_splits():
    doc = robust.__doc__
    assert "seed+10000" in doc and "seed+20000" in doc
    assert "OBSERVED" in doc and "LOCKED" in doc


def test_seeds_below_one_is_rejected(monkeypatch):
    """Degenerate --seeds 0/negative must fail loudly at the arg boundary, not crash
    later on max() of an empty champion list (adversarial review)."""
    import pytest
    monkeypatch.setattr(sys, "argv", ["robust.py", "--problem", "denoise", "--seeds", "0"])
    with pytest.raises(SystemExit):
        robust.main()
