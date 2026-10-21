"""Performance slice 14: exact gates against the implementations being replaced."""
from __future__ import annotations

import gc
import io
import os
import tracemalloc
import zipfile
from math import gcd

import numpy as np
import pytest
from scipy import ndimage

import deformreg as D
import residue as R
import volio as V


def _old_read_npy(path):
    arr = np.load(path, mmap_mode="r", allow_pickle=False)
    if arr.ndim != 3:
        raise ValueError
    V._check_voxel_budget(int(arr.size), str(path))
    return V._to_finite_f64(np.array(arr), str(path))


@pytest.mark.parametrize("dtype", [np.uint8, np.uint16, np.int16, np.float32, np.float64])
def test_npy_one_owned_conversion_is_bit_identical_and_closes_mapping(tmp_path, dtype):
    src = np.arange(3 * 17 * 19, dtype=dtype).reshape(3, 17, 19)
    path = tmp_path / "input.npy"
    np.save(path, src)
    expected = _old_read_npy(path)
    actual, _ = V._read_npy(path)
    assert np.array_equal(actual, expected)
    assert actual.dtype == np.float64 and actual.flags.owndata
    gc.collect()
    os.remove(path)  # Windows rejects this while a memmap handle remains open.
    assert not path.exists()


def _header_only_npz(path, shape, dtype=np.float32, member="volume.npy"):
    header = io.BytesIO()
    np.lib.format.write_array_header_2_0(
        header, {"descr": np.lib.format.dtype_to_descr(np.dtype(dtype)),
                 "fortran_order": False, "shape": shape})
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(member, header.getvalue())


def test_npz_rejects_oversize_from_header_without_array_allocation(tmp_path, monkeypatch):
    path = tmp_path / "huge.npz"
    _header_only_npz(path, (1024, 1024, 513))
    called = False
    original = np.lib.format.read_array

    def watched(*args, **kwargs):
        nonlocal called
        called = True
        return original(*args, **kwargs)

    monkeypatch.setattr(np.lib.format, "read_array", watched)
    tracemalloc.start()
    with pytest.raises(ValueError, match="MAX_VOLUME_BYTES"):
        V._read_npz(path, None)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert not called
    assert peak < 2_000_000, peak


def test_npz_valid_key_rules_and_corrupt_header_match_old_path(tmp_path):
    a = np.arange(24, dtype=np.int16).reshape(2, 3, 4)
    path = tmp_path / "many.npz"
    np.savez(path, first=a, second=a + 1)
    with pytest.raises(ValueError, match="key="):
        V._read_npz(path, None)
    got, meta = V._read_npz(path, "second")
    assert np.array_equal(got, (a + 1).astype(np.float64))
    assert meta.dtype == "int16"
    bad = tmp_path / "bad.npz"
    with zipfile.ZipFile(bad, "w") as zf:
        zf.writestr("arr_0.npy", b"not a numpy header")
    with pytest.raises(ValueError):
        V._read_npz(bad, None)


def _old_warp2d(img, fx, fy):
    h, w = img.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    return ndimage.map_coordinates(img, [yy - fy, xx - fx], order=1, mode="nearest")


def _old_warp_by_field(img, fx, fy):
    a = D._finite(img)
    if a.ndim == 0:
        a = np.atleast_2d(a)
    if a.ndim == 1:
        a = a.reshape(1, -1)
    a = np.clip(a, 0.0, 1.0)
    shape = a.shape[:2]
    fx, fy = D._field(fx, shape), D._field(fy, shape)
    if a.ndim >= 3:
        flat = a.reshape(shape[0], shape[1], -1)
        out = np.stack([_old_warp2d(flat[..., c], fx, fy) for c in range(flat.shape[2])], -1)
        out = out.reshape(a.shape)
    else:
        out = _old_warp2d(a, fx, fy)
    return D._sanitize_image(out, a)


@pytest.mark.parametrize("channels", [None, 3])
def test_warp_precomputed_coordinates_is_bit_identical(channels):
    rng = np.random.default_rng(1403)
    shape = (39, 47) if channels is None else (39, 47, channels)
    img = rng.random(shape)
    fx = rng.normal(0, 2, shape[:2]); fy = rng.normal(0, 2, shape[:2])
    assert np.array_equal(D.warp_by_field(img, fx, fy), _old_warp_by_field(img, fx, fy))


def _old_demons(fixed, moving, iters=50, sigma=1.5, max_step=0.5, eps=1e-9):
    f, m = D._image(fixed), D._image(moving)
    if m.shape != f.shape:
        m = D._resample_to(m, f.shape)
    fx = np.zeros(f.shape); fy = np.zeros(f.shape)
    gy, gx = D._grad(f); g2 = gx * gx + gy * gy
    for _ in range(iters):
        warped = _old_warp2d(m, fx, fy)
        diff = warped - f; den = g2 + diff * diff + eps
        vx, vy = diff * gx / den, diff * gy / den
        mag = np.hypot(vx, vy)
        scale = np.minimum(1.0, max_step / np.maximum(mag, D._EPS))
        nfx, nfy = fx + vx * scale, fy + vy * scale
        if sigma > 0:
            nfx = ndimage.gaussian_filter(nfx, sigma, mode="nearest")
            nfy = ndimage.gaussian_filter(nfy, sigma, mode="nearest")
        fx, fy = nfx, nfy
    return D._sanitize_image(_old_warp2d(m, fx, fy), f), fx, fy


def test_demons_50_iterations_and_grid_count_are_exact(monkeypatch):
    rng = np.random.default_rng(1450)
    fixed = ndimage.gaussian_filter(rng.random((48, 53)), 2)
    moving = ndimage.shift(fixed, (1.25, -2.5), order=1, mode="nearest")
    expected = _old_demons(fixed, moving)
    calls = 0
    original = np.mgrid.__getitem__

    def counted(item):
        nonlocal calls
        calls += 1
        return original(item)

    monkeypatch.setattr(type(np.mgrid), "__getitem__", lambda self, item: counted(item))
    actual = D.demons_register(fixed, moving)
    assert calls == 1
    assert len(actual) == len(expected) == 3
    assert all(np.array_equal(a, b) for a, b in zip(actual, expected))


def _old_crt(residues, moduli):
    r = [x % mi for x, mi in zip(residues, moduli)]
    digits = []
    for k in range(len(moduli)):
        acc, place = 0, 1
        for j in range(k):
            acc += digits[j] * place; place *= moduli[j]
        digits.append(((r[k] - acc) * pow(place % moduli[k], -1, moduli[k])) % moduli[k]
                      if k else r[0])
    value, place = 0, 1
    for digit, modulus in zip(digits, moduli):
        value += digit * place; place *= modulus
    return {"value": value, "modulus": place, "mixed_radix": digits}


def test_incremental_garner_matches_old_for_1000_random_sets():
    rng = np.random.default_rng(1414)
    primes = [int(x) for x in range(2, 312) if all(x % d for d in range(2, int(x ** .5) + 1))]
    primes.append((1 << 61) - 1)
    for _ in range(1000):
        k = int(rng.integers(2, min(64, len(primes)) + 1))
        moduli = [primes[i] for i in rng.choice(len(primes), k, replace=False)]
        residues = [int(rng.integers(-(1 << 61), 1 << 61)) for _ in moduli]
        got = R.residue_integer_crt(residues, moduli)
        assert got == _old_crt(residues, moduli)
        assert all(got["value"] % m == r % m for r, m in zip(residues, moduli))
        assert all(gcd(a, b) == 1 for i, a in enumerate(moduli) for b in moduli[i + 1:])
