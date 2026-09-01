"""Multi-seed champion selection: the reported holdout must be the one it names,
and the floor it is compared against must be IN the artifact.

robust.py has two holdouts available and they mean different things. The OBSERVED
split (seed+10000) is scored every generation by evolve.run; the LOCKED split
(seed+20000) is scored exactly once per seed. Reporting only the observed tally
while framing the file around honesty is one failure mode these tests pin.

The other one is newer and cost a published table its reproducibility: robust.py
used to read the floors out of ``baseline_<problem>.json`` and, when nobody had run
``baseline.py`` into that workdir, wrote ``baseline_hand: null`` and carried on.
Every out/rb_*/robust_*.json from 2026-09-01 has all four floors null, so the
numbers in docs/EVOLUTION_ENVIRONMENT.md could never be checked against the run
that supposedly produced them. The floors are now measured by robust.py itself and
a null floor is a hard abort.
"""
from __future__ import annotations

import json
import sys

import baseline
import evolve
import robust


UNIT = "dB PSNR"


def _floors(hand=20.0, trivial=15.0, hand_locked=23.0, trivial_locked=12.0,
            hand_train=21.0, trivial_train=16.0):
    return {"trivial": {"pipeline": "identity", "train": trivial_train,
                        "holdout": trivial, "locked": trivial_locked},
            "hand": {"pipeline": "gaussian(a=0.26,b=0.00)", "train": hand_train,
                     "holdout": hand, "locked": hand_locked}}


def _stub_floors(monkeypatch, **kw):
    monkeypatch.setattr(baseline, "measure_baselines", lambda *a, **k: _floors(**kw))


def _baseline_file(wd, **kw):
    """A baseline_<problem>.json on disk — now only a CROSS-CHECK, not the source."""
    f = _floors(**kw)
    (wd / "baseline_denoise.json").write_text(json.dumps({
        "hand": {"holdout": f["hand"]["holdout"], "locked_holdout": f["hand"]["locked"]},
        "trivial": {"holdout": f["trivial"]["holdout"],
                    "locked_holdout": f["trivial"]["locked"]},
        "config": {"n_train": 4, "n_holdout": 4, "size": 32, "seed": 0},
    }), encoding="utf-8")


def _champ(seed, train, holdout, locked):
    c = {"problem": "denoise", "unit": UNIT, "genome": [], "pipeline": "stub%d" % seed,
         "train": train, "holdout": holdout, "seed": seed, "gens": 1, "pop": 2}
    if locked is not None:
        c["locked_holdout"] = locked
    return c


def _run_robust(wd, champs, monkeypatch, extra=()):
    it = iter(champs)
    monkeypatch.setattr(evolve, "run", lambda *a, **k: next(it))
    monkeypatch.setattr(sys, "argv", ["robust.py", "--problem", "denoise",
                                      "--workdir", str(wd), "--seeds", str(len(champs)),
                                      "--gens", "1", "--pop", "2", *extra])
    robust.main()
    return json.loads((wd / "robust_denoise.json").read_text(encoding="utf-8"))


def test_locked_split_is_tallied_separately_from_the_observed_one(tmp_path, monkeypatch):
    # Distinct thresholds per split: the locked tally MUST use the LOCKED-split
    # baseline (hand_locked=23 / trivial_locked=12), not the observed one (20 / 15).
    # With the observed thresholds applied to the locked champions you would get
    # 1 beat / 2 collapse; the honest tally against the locked baseline is 0 / 0.
    _stub_floors(monkeypatch)
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


def test_floors_are_never_null_even_without_a_baseline_file(tmp_path, monkeypatch):
    """The regression this file exists for.

    No ``baseline_denoise.json`` anywhere — the old code wrote four nulls and a
    locked tally of null. The floors are measured in-run now, so every comparison
    the report makes is present in the report.
    """
    assert not (tmp_path / "baseline_denoise.json").exists()
    _stub_floors(monkeypatch)
    champs = [_champ(0, 30.0, 25.0, 22.0), _champ(1, 20.0, 21.0, 14.0)]
    s = _run_robust(tmp_path, champs, monkeypatch)

    for key in ("baseline_hand", "baseline_trivial",
                "baseline_hand_locked", "baseline_trivial_locked"):
        assert s[key] is not None, key
    assert s["n_beat_hand_locked"] is not None
    assert s["n_collapse_below_trivial_locked"] is not None
    assert all(v.startswith("measured") for v in s["baseline_source"].values())
    assert s["baseline_file_mismatch"] == []


def test_baseline_file_disagreement_is_disclosed_not_silently_resolved(tmp_path, monkeypatch):
    """A stale file must not quietly win, and must not be quietly ignored either."""
    _baseline_file(tmp_path, hand=20.0, hand_locked=99.0)     # stale locked floor
    _stub_floors(monkeypatch)                                  # measured says 23.0
    s = _run_robust(tmp_path, [_champ(0, 30.0, 25.0, 22.0)], monkeypatch)

    assert s["baseline_hand_locked"] == 23.0                   # measured wins
    fields = {m["field"]: m for m in s["baseline_file_mismatch"]}
    assert "hand_locked" in fields
    assert fields["hand_locked"]["baseline_file"] == 99.0
    assert fields["hand_locked"]["measured"] == 23.0
    assert "DISAGREES" in s["baseline_source"]["hand_locked"]


def test_missing_locked_score_leaves_the_locked_fields_null(tmp_path, monkeypatch):
    """Fail-closed: never substitute the observed split for a locked number we lack.

    This is the CHAMPION side — evolve.run is what supplies locked_holdout, and a
    champion record without one still yields null locked fields.
    """
    _stub_floors(monkeypatch)
    champs = [_champ(0, 30.0, 25.0, None), _champ(1, 20.0, 21.0, 22.0)]
    s = _run_robust(tmp_path, champs, monkeypatch)

    assert s["locked_holdout_spread"] is None
    assert s["n_beat_hand_locked"] is None and s["n_collapse_below_trivial_locked"] is None
    assert s["n_beat_hand"] == 2                 # the observed tally still reports
    assert s["selected_by_train"]["locked_holdout"] is None
    assert s["baseline_hand_locked"] is not None  # the FLOOR is still measured


def test_report_carries_provenance_and_a_ready_table_row(tmp_path, monkeypatch):
    """A published row must be readable off the artifact, stamped with when."""
    _stub_floors(monkeypatch)
    s = _run_robust(tmp_path, [_champ(0, 30.0, 25.0, 22.0)], monkeypatch)

    assert s["commit"] and isinstance(s["commit"], str)
    assert s["split_config"]["n_holdout"] and s["split_config"]["size"]
    assert s["measured_at"] and s["python"]
    row = s["table_row"]
    assert row["identity_locked"] == 12.0 and row["hand_locked"] == 23.0
    assert row["evolved_locked"] == 22.0
    assert row["evolved_locked_std"] == 0.0            # single seed
    assert row["vs_hand_locked_abs"] == -1.0
    # observed-minus-locked is what exposes a champion fitted to the observed split
    assert s["observed_minus_locked"]["selected_champion"] == 3.0
    assert s["per_seed"][0]["seed"] == 0


def test_real_evolution_run_populates_the_locked_tally(tmp_path):
    """End-to-end on the real evolve.run, which is what supplies locked_holdout."""
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
    # baseline.py and robust.py measure the same floor on the same config
    assert s["baseline_file_mismatch"] == []


def test_baseline_file_and_measured_floors_agree(tmp_path):
    """baseline.py's JSON and robust.py's in-run measurement are the same numbers.

    They are computed by different call paths; if they ever drift, a table row and
    the file it cites would disagree with no way to tell which is right.
    """
    import problems
    sys.argv = ["baseline.py", "--problem", "denoise", "--workdir", str(tmp_path),
                "--random-samples", "5", "--n-train", "4", "--n-holdout", "4", "--size", "32"]
    baseline.main()
    doc = json.loads((tmp_path / "baseline_denoise.json").read_text(encoding="utf-8"))
    cfg = baseline.resolve_cfg(tmp_path, "denoise")
    assert cfg["n_holdout"] == 4 and cfg["size"] == 32      # resolved from the file
    m = baseline.measure_baselines(problems.PROBLEMS["denoise"], cfg)
    assert m["hand"]["holdout"] == doc["hand"]["holdout"]
    assert m["hand"]["locked"] == doc["hand"]["locked_holdout"]
    assert m["trivial"]["locked"] == doc["trivial"]["locked_holdout"]


def test_isolated_seeds_reproduce_the_in_process_result(tmp_path):
    """--isolate must change WHERE the work runs, not WHAT it returns.

    Measured 2026-09-02: the chain fuzzer's reachability depends on what ran
    earlier in the same interpreter, so evolution measurements are run in fresh
    child processes. That is only safe if isolation is a no-op on the result.
    """
    args = ["--problem", "denoise", "--workdir", None, "--seeds", "2",
            "--gens", "2", "--pop", "6"]
    got = []
    for tag, extra in (("inproc", []), ("iso", ["--isolate"])):
        wd = tmp_path / tag
        wd.mkdir()
        sys.argv = ["robust.py", *[str(wd) if v is None else v for v in args], *extra]
        robust.main()
        got.append(json.loads((wd / "robust_denoise.json").read_text(encoding="utf-8")))

    assert got[1]["isolated_seeds"] is True and got[0]["isolated_seeds"] is False
    for key in ("baseline_hand_locked", "baseline_trivial_locked"):
        assert got[0][key] == got[1][key]
    assert got[0]["selected_by_train"] == got[1]["selected_by_train"]
    assert got[0]["locked_holdout_spread"] == got[1]["locked_holdout_spread"]


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
