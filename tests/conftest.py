"""Shared fixtures + a per-sort input battery for imgevolve's test suite.

The library had no automated tests before this suite. These tests encode the
*contracts* every operator must honour (determinism, finiteness, declared sort,
value domain) plus correctness anchors and evolution-honesty invariants.
"""
from __future__ import annotations

import os
import sys
import warnings

import numpy as np
import pytest

# imgevolve is a flat project: the package modules live one directory up.
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Backends emit library deprecation/boundary warnings that are not the unit
# under test; silence them so a failing assertion is the only signal.
warnings.filterwarnings("ignore")


# --------------------------------------------------------------------------- #
# Deterministic input battery, one bank per sort.                             #
# --------------------------------------------------------------------------- #
def _rng():
    return np.random.default_rng(20260812)


def image_bank(n: int = 48) -> dict[str, np.ndarray]:
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    grad = xx / (n - 1)
    disk = ((yy - n * 0.35) ** 2 + (xx - n * 0.4) ** 2) < (n * 0.18) ** 2
    checker = ((xx.astype(int) // 6 + yy.astype(int) // 6) % 2) * 0.15
    normal = np.clip(0.35 * grad + 0.45 * disk + checker + 0.03 * _rng().standard_normal((n, n)), 0, 1)
    single = np.zeros((n, n)); single[n // 2, n // 2] = 1.0
    return {
        "normal": normal,
        "const0": np.zeros((n, n)),
        "const1": np.ones((n, n)),
        "const_mid": np.full((n, n), 0.42),
        "tiny4": (np.arange(16, dtype=np.float64) / 15.0).reshape(4, 4),
        "single_bright": single,
    }


def region_bank(n: int = 48) -> dict[str, np.ndarray]:
    yy, xx = np.mgrid[0:n, 0:n]
    disk = (((yy - n // 2) ** 2 + (xx - n // 2) ** 2) < (n * 0.25) ** 2).astype(np.float64)
    single = np.zeros((n, n)); single[n // 2, n // 2] = 1.0
    return {
        "disk": disk,
        "all0": np.zeros((n, n)),
        "all1": np.ones((n, n)),
        "single_px": single,
        "tiny4": np.array([[1, 0, 0, 1], [0, 1, 1, 0], [0, 0, 1, 1], [1, 1, 0, 0]], np.float64),
    }


def color_bank(n: int = 48) -> dict[str, np.ndarray]:
    g = image_bank(n)["normal"]
    return {
        "normal": np.clip(np.stack([g, 0.7 * g + 0.1, 1 - g], -1), 0, 1),
        "const0": np.zeros((n, n, 3)),
        "const1": np.ones((n, n, 3)),
        "rand": _rng().random((n, n, 3)),
    }


def contour_bank() -> dict[str, dict]:
    sq = np.array([[6.0, 6.0], [6.0, 20.0], [20.0, 20.0], [20.0, 6.0], [6.0, 6.0]])
    return {
        "square": {"shape": (32, 32), "cs": [sq]},
        "empty": {"shape": (32, 32), "cs": []},
        "single_pt": {"shape": (32, 32), "cs": [np.array([[8.0, 8.0]])]},
        "two_pt": {"shape": (32, 32), "cs": [np.array([[2.0, 2.0], [10.0, 10.0]])]},
    }


def volume_bank() -> dict[str, np.ndarray]:
    zz, vy, vx = np.mgrid[0:8, 0:24, 0:24]
    return {
        "normal": np.clip(0.5 + 0.3 * np.sin(vx / 3.0) * np.cos(vy / 4.0) * (zz / 8.0), 0, 1),
        "const0": np.zeros((8, 24, 24)),
        "const1": np.ones((8, 24, 24)),
    }


BANKS = {
    "image": image_bank,
    "region": region_bank,
    "color": color_bank,
    "contour": contour_bank,
    "volume": volume_bank,
    "any": image_bank,
}

KNOBS = [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0), (0.15, 0.85)]


def copy_input(x):
    if isinstance(x, dict):
        return {"shape": x["shape"], "cs": [c.copy() for c in x["cs"]]}
    return np.array(x, copy=True)


def inputs_for(in_sort: str):
    """Yield (name, value) edge inputs matching a sort. Unknown sort -> empty."""
    bank = BANKS.get(in_sort)
    if bank is None:
        return
    for name, val in bank().items():
        yield name, val


@pytest.fixture(scope="session")
def registry():
    import ops
    return ops
