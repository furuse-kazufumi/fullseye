"""Performance slice 13: exactness gates against the pre-change algorithms."""
from __future__ import annotations

import numpy as np
import pytest

import image_gray


def _old_gen_cooc_matrix(image, region=None, ldgray=8, direction=0):
    im = np.asarray(image, dtype=np.float64)
    m = np.ones(im.shape, bool) if region is None else np.asarray(region, bool)
    levels = int(ldgray)
    q = np.clip((im * (levels - 1)).round().astype(int), 0, levels - 1)
    dr, dc = {0: (0, 1), 45: (-1, 1), 90: (-1, 0), 135: (-1, -1)}[int(direction)]
    matrix = np.zeros((levels, levels))
    height, width = q.shape
    for row in range(height):
        row2 = row + dr
        if not 0 <= row2 < height:
            continue
        for col in range(width):
            col2 = col + dc
            if 0 <= col2 < width and m[row, col] and m[row2, col2]:
                matrix[q[row, col], q[row2, col2]] += 1
    total = matrix.sum()
    return matrix / total if total > 0 else matrix


@pytest.mark.parametrize("direction", [0, 45, 90, 135])
@pytest.mark.parametrize("dtype", [np.uint8, np.float32, np.float64])
def test_gen_cooc_matrix_matches_old_on_mask_holes_and_border(direction, dtype):
    raw = np.array([[0, .14, .49, .51, 1], [.99, .5, .25, .75, .01],
                    [.12, .88, .34, .66, .45], [1.2, -.2, .5, .1, .9]])
    image = (raw * 255).astype(dtype) if dtype == np.uint8 else raw.astype(dtype)
    region = np.array([[1, 1, 0, 1, 1], [1, 0, 0, 1, 1],
                       [1, 1, 1, 0, 1], [1, 1, 1, 1, 1]], bool)
    got = image_gray.gen_cooc_matrix(image, region, 7, direction)
    expected = _old_gen_cooc_matrix(image, region, 7, direction)
    assert np.array_equal(got, expected)
    assert expected.sum() > 0.99


def test_gen_cooc_matrix_matches_old_across_row_blocks_and_empty_pairs():
    rng = np.random.default_rng(1301)
    image = rng.random((1307, 811))
    region = rng.random(image.shape) > .3
    assert np.array_equal(image_gray.gen_cooc_matrix(image, region, 16, 135),
                          _old_gen_cooc_matrix(image, region, 16, 135))
    isolated = np.zeros((3, 3), bool)
    isolated[1, 1] = True
    assert np.array_equal(image_gray.gen_cooc_matrix(image[:3, :3], isolated, 4, 0),
                          _old_gen_cooc_matrix(image[:3, :3], isolated, 4, 0))
