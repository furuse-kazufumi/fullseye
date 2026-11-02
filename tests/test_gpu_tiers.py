"""GPU tier 4-way classification gates (B').

門:
* 全 op の ``gpu_tier`` が 4 値(required/suitable/partial/none)で欠損 0。
* ``required`` 名簿の op が全部実在。
* ``SORT_TIER`` に無い型が 0(新設 sort が黙って none に落ちない)。
* 索引の ``gpu_tier`` が、OP_INDEX から独立に規則で数え直した値と一致。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _index():
    return json.loads((ROOT / "docs" / "OP_INDEX.json").read_text(encoding="utf-8"))


def _rules():
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    import gpu_tier_rules
    return gpu_tier_rules


def test_every_op_has_a_valid_gpu_tier():
    ops = _index()["ops"]
    gr = _rules()
    bad = [o["name"] for o in ops if o.get("gpu_tier") not in gr.TIERS]
    assert not bad, "gpu_tier missing/invalid on %d ops, e.g. %s" % (len(bad), bad[:5])


def test_required_roster_all_real():
    names = {o["name"] for o in _index()["ops"]}
    missing = _rules().check_roster(names)
    assert not missing, "required roster names not in registry: %s" % missing


def test_no_unknown_sorts():
    unk = _rules().unknown_sorts(_index()["ops"])
    assert not unk, "sorts absent from SORT_TIER (would silently become none): %s" % unk


def test_tier_recomputed_independently_matches_index():
    """別経路で数え直す: 名簿 + 型表から tier を再計算し、索引の値と一致させる。"""
    gr = _rules()
    ops = _index()["ops"]
    required = gr.load_required()
    mismatches = [(o["name"], o.get("gpu_tier"), gr.tier_for(o, required))
                  for o in ops if o.get("gpu_tier") != gr.tier_for(o, required)]
    assert not mismatches, "gpu_tier drift on %d ops, e.g. %s" % (len(mismatches), mismatches[:5])


def test_coverage_denominator_is_required_plus_suitable():
    gr = _rules()
    ops = _index()["ops"]
    gr._attach_gpu_accel(ops)
    for o in ops:
        if "gpu_tier" not in o:
            o["gpu_tier"] = gr.tier_for(o, gr.load_required())
    cov = gr.gpu_coverage(ops)
    assert cov["denom"] == sum(1 for o in ops if o["gpu_tier"] in ("required", "suitable"))
    assert 0.0 <= cov["rate"] <= 1.0 + cov["gpu_in_partial"] / max(1, cov["denom"])


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
