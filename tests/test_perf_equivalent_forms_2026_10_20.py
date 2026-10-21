"""性能第7便: 出力に届かない計算と不要な全表・全順位を除く同値変形の門。"""
from __future__ import annotations

import hashlib
import inspect
import math
import tracemalloc

import numpy as np
import pytest

import color_pca
import filters_arith
import fringe
import spc


def _old_gray_from_values(gray: np.ndarray, width: int) -> np.ndarray:
    binary = gray.copy()
    for shift in range(1, width):
        binary ^= gray >> shift
    return binary


def _bit_planes(values: np.ndarray, width: int) -> np.ndarray:
    return np.stack([(values >> shift) & 1
                     for shift in range(width - 1, -1, -1)])[:, None, :]


def _old_inpainting_ced(image, region, iterations=300, sigma=1.0):
    from scipy.ndimage import gaussian_filter

    im = np.asarray(image, dtype=np.float64).copy()
    mask = np.asarray(region, bool)
    for _ in range(int(iterations)):
        np.gradient(gaussian_filter(im, sigma))
        lap_perp = (np.roll(im, 1, 0) + np.roll(im, -1, 0)
                    + np.roll(im, 1, 1) + np.roll(im, -1, 1) - 4 * im)
        im = np.where(mask, im + 0.2 * lap_perp, im)
    return im


def _old_kappa(a, b):
    cats = np.unique(np.concatenate([a, b]))
    idx = {value: i for i, value in enumerate(cats)}
    table = np.zeros((len(cats), len(cats)), dtype=np.float64)
    for x, y in zip(a, b):
        table[idx[x], idx[y]] += 1.0
    n = table.sum()
    p_o = float(np.trace(table) / n)
    p_e = float((table.sum(1) @ table.sum(0)) / (n * n))
    if p_e >= 1.0:
        return (1.0 if p_o >= 1.0 else float("nan")), p_o, p_e
    return (p_o - p_e) / (1.0 - p_e), p_o, p_e


def _old_ewma(x, target, lam):
    out = np.empty(len(x), dtype=np.float64)
    previous = float(target)
    for i, value in enumerate(x):
        previous = lam * value + (1.0 - lam) * previous
        out[i] = previous
    return out


def _old_pca(images):
    array = np.asarray(images, dtype=np.float64)
    x = array.reshape(-1, array.shape[-1])
    mean = x.mean(0)
    covariance = np.cov((x - mean).T)
    values, vectors = np.linalg.eigh(covariance)
    order = np.argsort(values)[::-1]
    return mean, values[order], vectors[:, order], (x - mean) @ vectors[:, order]


@pytest.mark.parametrize("width", range(1, 17))
def test_graycode_parallel_prefix_is_bit_identical_exhaustively(width):
    gray = np.arange(1 << width, dtype=np.int64)
    actual = fringe.graycode_decode(_bit_planes(gray, width))
    assert np.array_equal(actual.ravel(), _old_gray_from_values(gray, width))


@pytest.mark.parametrize("width", [17, 31, 32, 47, 62])
def test_graycode_parallel_prefix_is_bit_identical_for_wide_values(width):
    rng = np.random.default_rng(width)
    top = (1 << width) - 1
    alternating_a = sum(1 << bit for bit in range(0, width, 2))
    alternating_b = top ^ alternating_a
    gray = np.concatenate((rng.integers(0, top + 1, 1_000_000, dtype=np.int64),
                           np.array([0, top, alternating_a, alternating_b], dtype=np.int64)))
    actual = fringe.graycode_decode(_bit_planes(gray, width))
    assert np.array_equal(actual.ravel(), _old_gray_from_values(gray, width))


def test_graycode_uses_logarithmic_number_of_xor_updates():
    source = inspect.getsource(fringe.graycode_decode)
    assert "shift <<= 1" in source
    assert source.count("binary ^=") == 1
    assert [math.ceil(math.log2(width)) for width in (1, 2, 16, 62)] == [0, 1, 4, 6]


def test_inpainting_drops_only_the_unused_gradient_for_gray_and_colour():
    rng = np.random.default_rng(20)
    gray = rng.random((19, 23))
    colour = rng.random((19, 23, 3))
    mask = np.zeros((19, 23), bool)
    mask[4:15, 6:17] = True
    assert np.array_equal(color_pca.inpainting_ced(gray, mask, 50, 1.3),
                          _old_inpainting_ced(gray, mask, 50, 1.3))
    # 現実装は2次元入力の契約なので、色画像は各面へ同じマスクを適用する。
    actual_colour = np.stack([color_pca.inpainting_ced(colour[..., c], mask, 50, 0.7)
                              for c in range(colour.shape[-1])], axis=-1)
    old_colour = np.stack([_old_inpainting_ced(colour[..., c], mask, 50, 0.7)
                           for c in range(colour.shape[-1])], axis=-1)
    assert np.array_equal(actual_colour, old_colour)


@pytest.mark.parametrize("sigma", [-1.0, np.nan])
def test_inpainting_keeps_the_existing_sigma_acceptance(sigma):
    image = np.arange(25.0).reshape(5, 5)
    mask = np.eye(5, dtype=bool)
    assert np.array_equal(color_pca.inpainting_ced(image, mask, 2, sigma),
                          _old_inpainting_ced(image, mask, 2, sigma))


@pytest.mark.parametrize("categories", [2, 5, 50, 5000])
def test_cohen_kappa_matches_full_table_reference(categories):
    rng = np.random.default_rng(categories)
    a = rng.integers(0, categories, 20_000)
    b = rng.integers(0, categories, 20_000)
    assert np.allclose(spc._cohen_kappa(a, b), _old_kappa(a, b), atol=1e-12,
                       rtol=0.0, equal_nan=True)


@pytest.mark.parametrize("a,b", [
    (np.array([], dtype=int), np.array([], dtype=int)),
    (np.zeros(9, dtype=int), np.zeros(9, dtype=int)),
    (np.zeros(9, dtype=int), np.ones(9, dtype=int)),
])
def test_cohen_kappa_preserves_empty_and_single_category_cases(a, b):
    assert np.allclose(spc._cohen_kappa(a, b), _old_kappa(a, b),
                       atol=0.0, rtol=0.0, equal_nan=True)


def test_cohen_kappa_peak_is_below_one_percent_of_full_table():
    a = np.arange(5000, dtype=np.int64)
    b = np.roll(a, 1)
    tracemalloc.start()
    _old_kappa(a, b)
    old_peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    tracemalloc.start()
    spc._cohen_kappa(a, b)
    new_peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    assert new_peak <= old_peak * 0.01


@pytest.mark.parametrize("lam", [0.05, 0.2, 1.0])
@pytest.mark.parametrize("length", [1, 2, 10, 100_000])
def test_ewma_filter_matches_loop(lam, length):
    x = np.random.default_rng(length).normal(size=length)
    result = spc.spc_ewma(x, target=0.375, lam=lam, L=3.0, sigma=1.0)
    assert np.allclose(result["z"], _old_ewma(x, 0.375, lam), atol=1e-12, rtol=0.0)


def test_ewma_alarm_boundary_remains_strict():
    # lam=1 なら z=x。上限上の点は警報にせず、その直後だけを警報にする。
    result = spc.spc_ewma([3.0, np.nextafter(3.0, np.inf)], target=0.0,
                          lam=1.0, L=3.0, sigma=1.0)
    assert result["alarms"] == [1]


@pytest.mark.parametrize("shape", [(13, 17, 3), (8, 9, 8)])
def test_pca_matches_cov_reference_reconstruction_and_subspace(shape):
    image = np.random.default_rng(sum(shape)).normal(size=shape)
    mean, values, vectors, projection = _old_pca(image)
    transform = color_pca.gen_principal_comp_trans(image)
    actual_projection = color_pca.principal_comp(image).reshape(-1, shape[-1])
    assert np.allclose(transform["eigenvalues"], values, rtol=1e-10, atol=1e-12)
    from scipy.linalg import subspace_angles
    angles = subspace_angles(vectors, transform["eigenvectors"])
    assert angles.max(initial=0.0) < 1e-8
    old_reconstruction = projection @ vectors.T + mean
    new_reconstruction = actual_projection @ transform["eigenvectors"].T + transform["mean"]
    assert np.allclose(new_reconstruction, old_reconstruction, rtol=1e-10, atol=1e-10)


def test_pca_one_sample_fails_as_before():
    with pytest.raises(np.linalg.LinAlgError):
        _old_pca(np.ones((1, 1, 3)))
    with pytest.raises(np.linalg.LinAlgError):
        color_pca.gen_principal_comp_trans(np.ones((1, 1, 3)))


def test_pca_large_stack_peak_is_at_most_sixty_percent_of_reference():
    image = np.random.default_rng(72).normal(size=(2048, 2048, 8))
    tracemalloc.start()
    old = _old_pca(image)
    old_peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    del old
    tracemalloc.start()
    new = color_pca.principal_comp(image)
    new_peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    assert new.shape == image.shape
    assert new_peak <= old_peak * 0.6


@pytest.mark.parametrize("count", [3, 4, 7, 16])
def test_rank_n_matches_sort_all_ranks_with_ties_nans_and_preserves_inputs(count):
    rng = np.random.default_rng(count)
    images = [rng.integers(0, 5, (17, 19)).astype(float) for _ in range(count)]
    images[0][::4, ::3] = np.nan
    before = [hashlib.sha256(image.tobytes()).digest() for image in images]
    stack = np.stack(images)
    for rank in range(count):
        actual = filters_arith.rank_n(images, rank)
        expected = np.sort(stack, axis=0)[rank]
        assert np.array_equal(actual, expected, equal_nan=True)
    after = [hashlib.sha256(image.tobytes()).digest() for image in images]
    assert after == before
