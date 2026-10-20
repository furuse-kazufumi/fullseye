"""Performance carry-over gates for the vehicle path planner.

The hashes below were produced by the original ``c305eaf50f`` planner.  They
pin the full sampled path and expansion tree, not merely the final cost.
"""
from __future__ import annotations

import hashlib

import numpy as np

import carpath as C


def _scenes():
    open_lot = np.zeros((24, 40), bool)
    corridor = open_lot.copy()
    corridor[:, 20] = True
    corridor[1:5, 20] = False
    ties = np.zeros((35, 55), bool)
    ties[7:28, 27] = True
    tie_poses = [(5.0, 17.5, 0.0), (49.0, 17.5, 0.0)]
    return [
        ("open", open_lot, [(3.0, 3.0, 0.0), (30.0, 18.0, np.pi / 2)],
         dict(radius=4.0, cell=1.0, return_tree=True)),
        ("corridor", corridor, [(3.0, 12.0, 0.0), (36.0, 12.0, 0.0)],
         dict(radius=4.0, cell=1.0, footprint=(2.0, 1.2, 0.5), return_tree=True)),
        ("ties", ties, tie_poses,
         dict(radius=3.0, cell=1.0, shot_every=2, return_tree=True)),
        ("ties-radius", ties, tie_poses,
         dict(radius=4.0, cell=1.0, shot_every=2, return_tree=True)),
    ]


_ORIGINAL = {
    "open": (31.77828287514351, 1, 0,
             "459e770f5df61a7fe639b3608057010b2b70dc21757cfdc7bc924dc878f12510",
             "d7520ba4feefa785432358ee41304e6aab56f21f76108b7129955536067b7130"),
    "corridor": (37.12920387578738, 841, 1552,
                 "55ea3f4d3c088b60a1006fe8adf85d42fd3ae65eb0f28928398becb1925f897e",
                 "748038e03ed23605aff3e46178a3911f72eae9c7a5bac1f179a84a40266d9949"),
    "ties": (49.66248210247126, 2071, 3579,
             "c12e38ffe3c1d769770968fa7eb6bb5d144c0558640564c520e7468aa646358f",
             "99421890fd50ef354588b15aad8e749e5d77c397eb33218a727e810b5fc8da30"),
    "ties-radius": (49.648461990183726, 2259, 3832,
                    "a4e241fba82b02e25f25ae50a99a10f826575fc7da277b483c5fa06da052799d",
                    "0079a919940b03705f60f2dd5f791b71e98bd4867e3c852cc88d4b6a18a5dd7d"),
}


def _digest(a):
    return hashlib.sha256(np.asarray(a).tobytes()).hexdigest()


def test_original_planner_reference_scenes_are_result_identical():
    for name, occupancy, poses, kwargs in _scenes():
        got = C.car_hybrid_astar(occupancy, poses, **kwargs)
        observed = (got["cost"], got["n_expanded"], got["n_generated"],
                    _digest(got["points"]), _digest(got["tree"]))
        assert observed == _ORIGINAL[name]


def test_178_fast_dominance_keeps_cost_and_feasibility():
    for _name, occupancy, poses, kwargs in _scenes():
        exact = C.car_hybrid_astar(occupancy, poses, **kwargs)
        fast = C.car_hybrid_astar(occupancy, poses, method="fast", **kwargs)
        assert abs(fast["cost"] - exact["cost"]) <= 1e-9
        assert not C._Collision(occupancy, kwargs["cell"], 0.0,
                                kwargs.get("footprint")).blocked(fast["points"])
