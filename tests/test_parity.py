"""Cross-backend parity harness: the reported claim must match what was measured.

parity.py is an evidence document, so its failure mode is a reporting one: a
number that reads as 'these backends agree' when the harness never looked hard
enough to know. These tests pin the three ways that used to happen — a single
knob operating point, clipping the diff to [0,1], and dropping a group whose
backend raised — plus the wording of the claim itself.
"""
from __future__ import annotations

import numpy as np
import pytest

import ops
import parity


# --- the diff must not clip the divergence away before measuring it ------------- #
def test_diff_reports_out_of_range_divergence():
    a, b = np.full((4, 4), 2.0), np.full((4, 4), 5.0)
    # clipping both to [0,1] first made this read 0.0 -> banded 'agree'
    assert parity._diff(a, b, "image") == pytest.approx(3.0)


def test_diff_still_agrees_when_backends_really_match():
    a = np.linspace(0, 1, 16).reshape(4, 4)
    assert parity._diff(a, a.copy(), "image") == pytest.approx(0.0)


# --- one operating point is not evidence about the whole knob space ------------- #
def test_run_takes_an_operating_point():
    name = "invert"
    fn = ops.RT.get(name)
    if fn is None:
        pytest.skip("invert not registered (backend absent)")
    op = next(o for o in ops.REGISTRY if o.name == name)
    img = np.linspace(0, 1, 64).reshape(8, 8)
    # default kept for backward compatibility; the knobs are now addressable
    assert parity._run(op, img, 0.5, 0.4) is not None
    assert parity._run(op, img) is not None


def test_knobs_sweep_more_than_one_point():
    assert len(parity.KNOBS) >= 2
    assert len(set(parity.KNOBS)) == len(parity.KNOBS)
    assert (0.5, 0.4) in parity.KNOBS          # the historical point stays covered


@pytest.mark.parametrize("halcon", ["threshold", "dilation_circle", "erosion_circle"])
def test_ops_that_only_agree_at_one_point_are_not_banded_agree(halcon):
    """These agree exactly at (0.5, 0.4) yet diverge by 1.0 at a knob corner."""
    rows = {r["halcon"]: r for r in parity.analyze()}
    r = rows.get(halcon)
    if r is None:
        pytest.skip(f"{halcon} has no multi-backend group here")
    assert r["band"] != "agree", f"{halcon} banded 'agree' on single-point evidence"
    assert r["max_disagreement"] > 0.10
    assert r["worst_knob"] is not None          # the point that exposed it is disclosed


# --- a group we could not compare is not a group that agreed ------------------- #
def test_incomparable_groups_are_counted_not_dropped(monkeypatch):
    rows_before = parity.analyze()
    victim = rows_before[0]["halcon"]
    real = parity._run

    def flaky(op, v, a=0.5, b=0.4):
        if (op.halcon or "").strip() == victim:
            return None                         # simulate a backend that raises
        return real(op, v, a, b)

    monkeypatch.setattr(parity, "_run", flaky)
    rows_after = parity.analyze()
    assert len(rows_after) == len(rows_before), "a failing backend silently dropped the row"
    r = next(r for r in rows_after if r["halcon"] == victim)
    assert r["band"] == "incomparable"
    assert r["max_disagreement"] is None         # no number is better than a wrong one


def test_every_row_carries_a_band_and_the_points_tested():
    for r in parity.analyze():
        assert r["band"] in ("agree", "close", "differ", "incomparable")
        assert r["knobs_tested"] == len(parity.KNOBS)


# --- the claim itself ---------------------------------------------------------- #
def test_docstring_does_not_claim_faithful_implementation_is_proven():
    doc = parity.__doc__
    assert "falsifiable evidence the operation is faithfully implemented" not in doc, \
        "agreement at sampled points is not proof of a faithful implementation"
    assert "OPERATING POINTS TESTED" in doc
    assert "incomparable" in doc
