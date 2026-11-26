"""Independent-review regressions for the vial particle POD PoC."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("poc_vial_particle_pod", ROOT / "examples" / "poc_vial_particle_pod.py")
assert SPEC is not None and SPEC.loader is not None
POC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(POC)


def test_correspondence_is_a_global_one_to_one_bipartite_assignment():
    truth = {
        "object_id": np.array([0, 0, 0, 1, 1, 1]),
        "object_type": np.array(["particle"] * 6),
        "frame": np.array([0, 1, 2, 0, 1, 2]),
        "row_px": np.array([10.0, 10.0, 10.0, 10.0, 10.0, 10.0]),
        "col_px": np.array([10.0, 10.0, 10.0, 13.4, 13.4, 13.4]),
    }
    tracks = {
        "track_id": np.array([100, 100, 100, 101, 101, 101]),
        "object_class": np.array(["moving"] * 6),
        "frame": np.array([0, 1, 2, 0, 1, 2]),
        "row_px": np.array([10.1, 10.1, 10.1, 10.2, 10.2, 10.2]),
        "col_px": np.array([10.0, 10.0, 10.0, 9.8, 9.8, 9.8]),
    }

    links = POC.correspondence(truth, tracks, kinds=("particle",), max_distance_px=3.5)

    assert set(links) == {0, 1}
    assigned = {oid: {pair[-1] for pair in pairs} for oid, pairs in links.items()}
    assert assigned == {0: {101}, 1: {100}}
    assert len(set().union(*assigned.values())) == 2


def test_condition_a90_leaves_complete_separation_unestimated():
    rows = []
    for illumination in POC.ILLUMINATIONS:
        for contrast in POC.CONTRASTS:
            for diameter in POC.DIAMETERS:
                for _rep in range(10):
                    rows.append({"illumination": illumination, "contrast": float(contrast),
                                 "diameter_um": float(diameter), "hit": int(diameter >= 160.0)})

    result = POC.fit_condition_a90(rows)

    assert len(result) == len(POC.ILLUMINATIONS) * len(POC.CONTRASTS)
    assert all(entry["fit"] is None for entry in result.values())
    assert all(POC._condition_a90_text(entry) == "a90: 求まらない（点が足りない）"
               for entry in result.values())
