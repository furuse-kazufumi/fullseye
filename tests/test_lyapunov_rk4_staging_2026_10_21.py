"""リアプノフ接方程式の RK4 段と短すぎる積分窓の回帰テスト。"""

import numpy as np
import pytest
from scipy.integrate import solve_ivp

import mathops


def _reference_lorenz_exponents(dt):
    """本体と同じ各刻み QR を使い、刻み間だけ高精度に連成積分する。"""
    params = np.asarray(mathops.DYNSYS_SYSTEMS["lorenz"], dtype=np.float64)
    x = np.ones(3)
    q = np.eye(3)
    total = np.zeros(3)
    steps = round(0.2 / dt)

    def coupled(_t, z):
        state = z[:3]
        frame = z[3:].reshape(3, 3)
        return np.concatenate((mathops._dyn_derivative("lorenz", params, state),
                               (mathops._dyn_jacobian("lorenz", params, state)
                                @ frame).ravel()))

    for _ in range(steps):
        z0 = np.concatenate((x, q.ravel()))
        sol = solve_ivp(coupled, (0.0, dt), z0, method="DOP853",
                        rtol=1e-12, atol=1e-12)
        assert sol.success
        x = sol.y[:3, -1]
        q, r = np.linalg.qr(sol.y[3:, -1].reshape(3, 3))
        diagonal = np.diag(r).copy()
        signs = np.sign(diagonal)
        signs[signs == 0] = 1.0
        q *= signs
        total += np.log(np.abs(diagonal) + 1e-300)
    return np.sort(total / (steps * dt))[::-1]


def _old_linear_exponents(matrix, x0, t_end, dt):
    """修正前の接行列更新を固定した、定数ヤコビ行列用の対照群。"""
    matrix = np.asarray(matrix, dtype=np.float64)
    x = np.asarray(x0, dtype=np.float64)
    q = np.eye(matrix.shape[0])
    total = np.zeros(matrix.shape[0])
    steps = round(t_end / dt)
    for _ in range(steps):
        y1 = matrix @ q
        y2 = matrix @ (q + 0.5 * dt * y1)
        y3 = matrix @ (q + 0.5 * dt * y2)
        y4 = matrix @ (q + dt * y3)
        y = q + (dt / 6.0) * (y1 + 2.0 * y2 + 2.0 * y3 + y4)
        q, r = np.linalg.qr(y)
        diagonal = np.diag(r).copy()
        signs = np.sign(diagonal)
        signs[signs == 0] = 1.0
        q *= signs
        total += np.log(np.abs(diagonal) + 1e-300)
        # 状態は結果に影響しないが、旧実装と同じ RK4 更新を残す。
        k1 = matrix @ x
        k2 = matrix @ (x + 0.5 * dt * k1)
        k3 = matrix @ (x + 0.5 * dt * k2)
        k4 = matrix @ (x + dt * k3)
        x += (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
    return np.sort(total / (steps * dt))[::-1]


def test_lorenz_tangent_integration_has_fourth_order_convergence():
    dts = (0.02, 0.01, 0.005, 0.0025)
    errors = []
    for dt in dts:
        reference = _reference_lorenz_exponents(dt)
        actual = np.asarray(mathops.dynsys_lyapunov_spectrum(
            "lorenz", None, [1.0, 1.0, 1.0], 0.2, dt, 0.0))
        errors.append(float(np.max(np.abs(actual - reference))))
    orders = np.log2(np.asarray(errors[:-1]) / np.asarray(errors[1:]))
    assert np.all(orders >= 3.5), (errors, orders)
    assert errors[-1] < 1e-4, errors


def test_constant_jacobian_result_is_identical_to_old_staging():
    matrix = np.array([[0.2, 1.1], [-0.7, -0.4]])
    expected = _old_linear_exponents(matrix, [0.3, -0.8], 0.6, 0.01)
    actual = np.asarray(mathops.dynsys_lyapunov_spectrum(
        "linear", matrix.ravel(), [0.3, -0.8], 0.6, 0.01, 0.0))
    np.testing.assert_allclose(actual, expected, rtol=0.0, atol=1e-12)


def test_zero_integration_steps_raise_with_window_details():
    with pytest.raises(ValueError) as caught:
        mathops.dynsys_lyapunov_spectrum(
            "lorenz", t_end=0.01, burn_in=0.0, dt=0.1)
    message = str(caught.value)
    assert "dynsys_lyapunov_spectrum" in message
    assert "t_end" in message and "0.01" in message
    assert "dt" in message and "0.1" in message
    assert "0 integration steps" in message
