"""Verification gates for performance batch 19 B (items 96--105)."""

import numpy as np

import regionprops3d


def _original_surface_area(mask):
    if not mask.any():
        return 0
    padded = np.pad(mask.astype(np.int8), 1)
    return sum(int(np.count_nonzero(np.diff(padded, axis=axis))) for axis in range(3))


def test_99_surface_area_is_exact_six_neighbour_count():
    probes = [
        np.array([[[1]]], dtype=bool),
        np.random.default_rng(99).random((7, 11, 5)) > 0.63,
        np.pad(np.ones((3, 4, 2), dtype=bool), ((0, 2), (1, 0), (0, 3))),
    ]
    for mask in probes:
        got = regionprops3d._surface_area(mask)
        assert got == _original_surface_area(mask)
        exposed = 0
        for index in np.argwhere(mask):
            for axis in range(3):
                for step in (-1, 1):
                    neighbour = index.copy()
                    neighbour[axis] += step
                    if (neighbour[axis] < 0 or neighbour[axis] >= mask.shape[axis]
                            or not mask[tuple(neighbour)]):
                        exposed += 1
        assert got == exposed
