"""Performance slice 13: exactness gates against the pre-change algorithms."""
from __future__ import annotations

import numpy as np
import pytest

import image_gray
import pcseg


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


def _old_euclidean_clusters(points, tol=.05, min_size=10, max_size=None):
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import connected_components
    from scipy.spatial import cKDTree
    points = np.asarray(points, np.float64)
    n = len(points)
    if not n:
        return []
    pairs = cKDTree(points).query_pairs(r=float(tol), output_type="ndarray")
    if pairs.size:
        rows = np.concatenate([pairs[:, 0], pairs[:, 1]])
        cols = np.concatenate([pairs[:, 1], pairs[:, 0]])
    else:
        rows = cols = np.zeros(0, int)
    graph = csr_matrix((np.ones(rows.size), (rows, cols)), shape=(n, n))
    ncomp, labels = connected_components(graph, directed=False)
    out = []
    for component in range(ncomp):
        idx = np.where(labels == component)[0]
        if idx.size >= min_size and (max_size is None or idx.size <= max_size):
            out.append(idx)
    out.sort(key=lambda a: -a.size)
    return out


def _assert_same_clusters(points, **kwargs):
    expected = _old_euclidean_clusters(points, **kwargs)
    got = pcseg.euclidean_clusters(points, **kwargs)
    assert len(got) == len(expected)
    assert all(np.array_equal(a, b) for a, b in zip(got, expected))


def test_euclidean_clusters_matches_old_order_boundary_and_filters():
    points = np.array([[0, 0, 0], [1, 0, 0], [10, 0, 0], [11, 0, 0],
                       [30, 0, 0], [30.5, 0, 0], [31, 0, 0]], float)
    _assert_same_clusters(points, tol=1.0, min_size=2)
    _assert_same_clusters(points, tol=1.0, min_size=2, max_size=2)
    _assert_same_clusters(points[:0], tol=1.0, min_size=1)


def test_euclidean_clusters_matches_old_with_many_tiny_noise_components():
    rng = np.random.default_rng(1302)
    blobs = [rng.normal((i * 3., 0, 0), .02, (80 + i % 3, 3)) for i in range(12)]
    noise = np.column_stack([np.arange(400) * 3. + 100., np.zeros(400), np.zeros(400)])
    points = np.vstack([*blobs, noise])
    _assert_same_clusters(points, tol=.1, min_size=20)
