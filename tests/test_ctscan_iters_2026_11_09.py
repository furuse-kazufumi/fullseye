"""Regression tests for the convergence of ctscan.sirt_reconstruct /
os_sart_reconstruct at their default iteration counts, and the early stop
through on_iter (2026-11-09 op audit g2_calib_ct).

The defaults (SIRT 50, OS-SART 10) stop well before convergence; comparing
methods there makes SIRT look worse than it is. The test pins that fact so a
silent change of the defaults or of the update shows up."""
import numpy as np
import pytest

import ctscan

N = 16


@pytest.fixture(scope="module")
def scene():
    g = ctscan.ct_scan_geometry("cone", n_views=12, n_u=32, n_v=24, vol_shape=(N, N, N))
    truth = ctscan.shepp_logan_3d(N)
    p = ctscan.ct_forward_project(truth, g, device="cpu")       # consistent data
    return g, truth, p


def _nrms(x, t):
    return float(np.sqrt(np.mean((x - t) ** 2)) / (t.max() - t.min()))


def test_sirt_default_is_not_converged(scene):
    g, truth, p = scene
    e50 = _nrms(np.asarray(ctscan.sirt_reconstruct(p, g, device="cpu")), truth)
    e200 = _nrms(np.asarray(ctscan.sirt_reconstruct(p, g, n_iter=200, device="cpu")), truth)
    assert e200 < 0.75 * e50, (e50, e200)


def test_os_sart_default_is_not_converged(scene):
    g, truth, p = scene
    e10 = _nrms(np.asarray(ctscan.os_sart_reconstruct(p, g, n_subsets=6, device="cpu")), truth)
    e40 = _nrms(np.asarray(ctscan.os_sart_reconstruct(p, g, n_iter=40, n_subsets=6, device="cpu")), truth)
    assert e40 < 0.8 * e10, (e10, e40)


@pytest.mark.parametrize("fn", [ctscan.sirt_reconstruct, ctscan.os_sart_reconstruct])
def test_on_iter_true_stops_early(scene, fn):
    g, truth, p = scene
    seen = []

    def stop_at_3(k, v):
        seen.append(k)
        return k == 2

    kw = {"device": "cpu"}
    if fn is ctscan.os_sart_reconstruct:
        kw["n_subsets"] = 6                         # the scene has 12 views
    x = np.asarray(fn(p, g, n_iter=50, on_iter=stop_at_3, **kw))
    assert seen == [0, 1, 2]
    # same volume as running exactly 3 iterations
    kw["n_iter"] = 3
    assert np.array_equal(x, np.asarray(fn(p, g, **kw)))


@pytest.mark.parametrize("fn", [ctscan.sirt_reconstruct, ctscan.os_sart_reconstruct])
@pytest.mark.parametrize("value", [None, False, np.False_, 0, 1, 0.5, {"a": 1}, np.ones(3), [1]])
def test_on_iter_returning_none_or_non_bool_continues(scene, fn, value):
    # only a boolean True stops: a recorder that happens to return a number, a dict or
    # an array must run to the end (and an array must not raise)
    g, truth, p = scene
    seen = []
    kw = {"n_subsets": 6} if fn is ctscan.os_sart_reconstruct else {}
    fn(p, g, n_iter=4, device="cpu", on_iter=lambda k, v: seen.append(k) or value, **kw)
    assert seen == [0, 1, 2, 3]


@pytest.mark.parametrize("fn", [ctscan.sirt_reconstruct, ctscan.os_sart_reconstruct])
def test_on_iter_numpy_bool_stops(scene, fn):
    # the docstring's recipe returns a numpy comparison: np.bool_, not bool
    g, truth, p = scene
    kw = {"n_subsets": 6} if fn is ctscan.os_sart_reconstruct else {}
    pn = np.linalg.norm(p)
    seen = []

    def stop_when_residual_small(k, v):
        seen.append(k)
        rel = np.linalg.norm(ctscan.ct_forward_project(v, g, device="cpu") - p) / pn
        return np.float64(rel) < np.float64(10.0)          # np.True_ on the first call

    fn(p, g, n_iter=30, device="cpu", on_iter=stop_when_residual_small, **kw)
    assert seen == [0]
    seen2 = []
    fn(p, g, n_iter=30, device="cpu", on_iter=lambda k, v: seen2.append(k) or np.bool_(k == 4), **kw)
    assert seen2 == [0, 1, 2, 3, 4]


def test_docstrings_say_the_defaults_are_not_converged():
    for fn in (ctscan.sirt_reconstruct, ctscan.os_sart_reconstruct):
        assert "not converged" in fn.__doc__


def test_tv_reconstruct_follows_the_same_rule(scene):
    g, truth, p = scene
    seen = []
    ctscan.tv_reconstruct(p, g, n_iter=20, device="cpu", on_iter=lambda k, v: seen.append(k) or np.bool_(k == 2))
    assert seen == [0, 1, 2]
    seen2 = []
    ctscan.tv_reconstruct(p, g, n_iter=5, device="cpu", on_iter=lambda k, v: seen2.append(k) or float(k + 1))
    assert seen2 == [0, 1, 2, 3, 4]
