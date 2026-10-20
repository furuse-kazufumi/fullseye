import numpy as np

import conngraph


def _old_ridge_readout(X, Y, alpha):
    Xb = np.hstack([X, np.ones((X.shape[0], 1))])
    gram = Xb.T @ Xb + alpha * np.eye(Xb.shape[1])
    return np.linalg.solve(gram, Xb.T @ Y)


def _old_states_participation_ratio(X):
    Xc = X - X.mean(axis=0, keepdims=True)
    gram = Xc @ Xc.T if Xc.shape[0] < Xc.shape[1] else Xc.T @ Xc
    values = np.clip(np.linalg.eigvalsh(gram), 0.0, None)
    total = float(values.sum())
    return total * total / float((values ** 2).sum()) if total > 0.0 else 0.0


def test_ridge_readout_dual_agrees_with_primal_and_uses_small_system(monkeypatch):
    rng = np.random.default_rng(20261020)
    X = rng.standard_normal((128, 1024))
    Y = rng.standard_normal((128, 4))
    expected = _old_ridge_readout(X, Y, 0.3)
    sizes = []
    solve = np.linalg.solve

    def counted(a, b):
        sizes.append(a.shape)
        return solve(a, b)

    monkeypatch.setattr(np.linalg, "solve", counted)
    actual = conngraph.ridge_readout(X, Y, alpha=0.3)
    np.testing.assert_allclose(actual, expected, rtol=1e-10, atol=1e-12)
    assert sizes == [(128, 128)]


def test_ridge_readout_keeps_primal_for_tall_and_zero_alpha(monkeypatch):
    rng = np.random.default_rng(7)
    solve = np.linalg.solve
    sizes = []

    def counted(a, b):
        sizes.append(a.shape)
        return solve(a, b)

    monkeypatch.setattr(np.linalg, "solve", counted)
    conngraph.ridge_readout(rng.normal(size=(20, 3)), rng.normal(size=(20, 2)), alpha=0.2)
    conngraph.ridge_readout(rng.normal(size=(12, 3)), rng.normal(size=(12, 2)), alpha=0.0)
    assert sizes == [(4, 4), (4, 4)]


def test_ridge_readout_dual_ill_conditioned_agrees_with_primal():
    rng = np.random.default_rng(9)
    base = rng.normal(size=(32, 1))
    X = np.hstack([base + 1e-8 * rng.normal(size=(32, 1)) for _ in range(80)])
    Y = rng.normal(size=(32, 3))
    np.testing.assert_allclose(
        conngraph.ridge_readout(X, Y, alpha=0.1),
        _old_ridge_readout(X, Y, 0.1),
        rtol=1e-10,
        atol=1e-11,
    )


def test_states_participation_ratio_matches_eigenvalue_reference():
    rng = np.random.default_rng(11)
    cases = [
        rng.normal(size=(40, 12)),
        rng.normal(size=(40, 1)) @ rng.normal(size=(1, 12)),
        np.eye(12) + 1e-8 * rng.normal(size=(12, 12)),
        1e-12 * rng.normal(size=(30, 9)),
    ]
    for X in cases:
        np.testing.assert_allclose(
            conngraph.states_participation_ratio(X),
            _old_states_participation_ratio(X),
            rtol=1e-12,
            atol=1e-12,
        )


def test_states_participation_ratio_is_scale_safe():
    rng = np.random.default_rng(12)
    X = rng.normal(size=(30, 9))
    expected = conngraph.states_participation_ratio(X)
    np.testing.assert_allclose(conngraph.states_participation_ratio(X * 1e150), expected, rtol=1e-12)
    np.testing.assert_allclose(conngraph.states_participation_ratio(X * 1e-150), expected, rtol=1e-12)
