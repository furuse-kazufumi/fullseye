"""Honesty of the auto functional gate (regression).

Two ways the gate used to hand out a PASS it had not earned:

1. `_check_sort` accepted an `out_sort == "region"` result when its values merely
   sat inside [0, 1] (`... or (out.min() >= 0 and out.max() <= 1)`). Every
   grayscale image satisfies that, so an op declaring "region" that returned the
   canonical input untouched was gated as a valid region.
2. An identity / pass-through result was still `status == "pass"` and still landed
   in `covered_pass` (and therefore in the honest_summary headline); "it was an
   identity" was only a printed footnote.

Plus the same empty-reference short-circuit `backends_auto.build` had: with
`real` empty, `if real and name not in real` verified nothing and passed all.
"""
from __future__ import annotations

import backends_auto as BA
import verify_auto as VA


def _gray():
    return VA._canonical_image()


def test_region_sort_rejects_grayscale():
    """A region is a SET of pixels: [0,1]-range is not enough, it must be {0,1}."""
    g = _gray()
    ok, _, why = VA._check_sort(g, "region", g.shape)
    assert not ok
    assert "binary" in why
    assert g.min() >= 0 and g.max() <= 1     # the old clause that used to pass it


def test_region_sort_accepts_binary():
    g = _gray()
    ok, _, why = VA._check_sort(VA._canonical_region(g), "region", g.shape)
    assert ok and why == ""


def test_identity_is_not_counted_as_pass(tmp_path, monkeypatch):
    """A pass-through implements nothing; it must stay out of `passing_ops`."""
    monkeypatch.setattr(VA, "HERE", str(tmp_path))          # keep data/ artifact out of the repo
    art = VA.run()
    assert art["identity_ops"], "expected at least one identity spec on canonical inputs"
    for name in art["identity_ops"]:
        assert name not in art["passing_ops"]
    assert art["n_pass"] + art["n_fail"] + art["n_dropped"] == art["n_specs"]


def test_region_geom_specs_are_gated_as_build_compiles_them(tmp_path, monkeypatch):
    """`build` rebinarises geom+region specs, so the gate must too (else 3 false fails)."""
    monkeypatch.setattr(VA, "HERE", str(tmp_path))
    art = VA.run()
    for name in ("affine_trans_region", "zoom_region", "projective_trans_region"):
        assert name in art["passing_ops"]


def test_gate_fails_closed_without_reference(tmp_path, monkeypatch):
    """No real-name reference => every name-tagged spec is dropped, none passes."""
    monkeypatch.setattr(VA, "HERE", str(tmp_path))
    monkeypatch.setattr(BA, "_real_ops", set)
    art = VA.run()
    assert art["n_pass"] == 0 and art["passing_ops"] == []
    assert art["n_dropped"] == art["n_specs"]
