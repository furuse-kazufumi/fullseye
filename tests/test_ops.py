"""Regression tests for the module-level matching context in ``ops``.

`set_match_template` used to write one module-level dict shared by every thread.
Under the parallel evaluation the evolution sweeps run (scorers on a thread pool),
two threads scoring different models clobbered each other: A set T_A, B overwrote
with T_B, and A then scored its image against T_B and returned a plausible-but-wrong
``[corr, y, x]`` with no exception. The store is thread-local now, so each thread
reads the template it set, while a thread that never set one still inherits the last
template set anywhere (the "build the dataset on the main thread, score in workers"
flow must keep working).
"""
from __future__ import annotations

import threading

import numpy as np
import pytest

import ops


@pytest.fixture(autouse=True)
def _restore_match_template():
    prev = ops._MATCH_CTX.get("template")
    yield
    ops._MATCH_CTX["template"] = prev


def _disc(size: int, r: int) -> np.ndarray:
    yy, xx = np.mgrid[0:size, 0:size]
    c = size // 2
    return ((xx - c) ** 2 + (yy - c) ** 2 <= r * r).astype(np.float64)


def _ell(size: int) -> np.ndarray:
    t = np.zeros((size, size), np.float64)
    t[2:size - 2, 2:4] = 1.0
    t[size - 4:size - 2, 2:size - 2] = 1.0
    return t


def _scene(T: np.ndarray, rc: tuple[int, int]) -> np.ndarray:
    """96x96 scene holding the EXACT template at `rc` (moderate contrast)."""
    img = np.full((96, 96), 0.10, np.float64)
    h = T.shape[0] // 2
    r, c = rc
    img[r - h:r + h + 1, c - h:c + h + 1] = 0.10 + 0.35 * T
    return img


T_A, T_B = _disc(11, 4), _ell(11)
RC_A, RC_B = (24, 24), (64, 64)


def test_concurrent_evaluators_each_read_their_own_match_template():
    results: dict[str, tuple[bool, np.ndarray]] = {}
    barrier = threading.Barrier(2)                 # force the interleaving the race needs

    def worker(name, T, rc):
        ops.set_match_template(T)
        barrier.wait()                             # the other thread sets ITS template here
        seen = ops._MATCH_CTX.get("template")
        results[name] = (np.array_equal(seen, T), ops._ncc_locate(_scene(T, rc), 0.0, 0.0))

    threads = [threading.Thread(target=worker, args=a)
               for a in (("A", T_A, RC_A), ("B", T_B, RC_B))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    for name, rc in (("A", RC_A), ("B", RC_B)):
        own, loc = results[name]
        assert own, f"thread {name} read another thread's template"
        assert loc[0] == pytest.approx(1.0, abs=1e-6)   # exact instance -> Pearson NCC 1.0
        assert (int(loc[1]), int(loc[2])) == rc


def test_shape_locate_is_thread_local_too():
    results: dict[str, np.ndarray] = {}
    barrier = threading.Barrier(2)

    def worker(name, T, rc):
        ops.set_match_template(T)
        barrier.wait()
        results[name] = ops._shape_locate(_scene(T, rc), 0.0, 0.0)

    threads = [threading.Thread(target=worker, args=a)
               for a in (("A", T_A, RC_A), ("B", T_B, RC_B))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    for name, rc in (("A", RC_A), ("B", RC_B)):
        loc = results[name]
        assert loc[0] == pytest.approx(1.0, abs=1e-6)
        assert (int(loc[1]), int(loc[2])) == rc


def test_worker_thread_inherits_template_set_on_the_main_thread():
    """Datasets are built (and the model set) on the main thread; workers only score."""
    ops.set_match_template(T_A)
    seen: list = []

    t = threading.Thread(target=lambda: seen.append(ops._ncc_locate(_scene(T_A, RC_A), 0.0, 0.0)))
    t.start(); t.join()

    assert seen[0][0] == pytest.approx(1.0, abs=1e-6)
    assert (int(seen[0][1]), int(seen[0][2])) == RC_A


def test_single_threaded_match_template_api_is_unchanged():
    ops.set_match_template(T_A)
    assert np.array_equal(ops._MATCH_CTX["template"], T_A)
    assert ops._MATCH_CTX.get("template").dtype == np.float64   # list input would convert too
    ops.set_match_template(None)
    assert ops._MATCH_CTX.get("template") is None
    assert np.array_equal(ops._ncc_locate(_scene(T_A, RC_A), 0.0, 0.0), np.zeros(3))
    assert np.array_equal(ops._shape_locate(_scene(T_A, RC_A), 0.0, 0.0), np.zeros(4))
