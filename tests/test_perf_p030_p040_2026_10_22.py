import numpy as np

import spc


def _max_result_diff(a, b):
    return max(float(np.max(np.abs(a[key] - b[key]))) for key in a)


def test_p030_block_mode_covers_correlated_and_power_models():
    n = 20_000
    m = 8
    table = {
        "u": np.linspace(0.1, 0.8, m),
        "sensitivity": np.linspace(-1.0, 1.0, m),
        "value": np.linspace(1.0, 2.0, m),
        "power": np.full(m, 2.0),
    }
    correlation = np.full((m, m), 0.15)
    np.fill_diagonal(correlation, 1.0)
    default = spc.gum_monte_carlo(
        table, n=n, seed=3040, correlation=correlation, value="value", power="power"
    )
    blocked = spc.gum_monte_carlo(
        table, n=n, seed=3040, correlation=correlation, value="value", power="power",
        stream=True,
    )
    measured_max_diff = _max_result_diff(default, blocked)
    assert abs(measured_max_diff - 0.13626698757917066) < 1e-15, (
        f"stream と既定の全戻り値の実測 max |diff|={measured_max_diff:.17g}"
    )


def test_p030_block_generator_obeys_64_mib_workspace_limit():
    m = 32
    block = next(spc._mc_standardised_blocks(
        ["normal"] * m, np.eye(m), 1_000_000, 1, "gum_monte_carlo"
    ))
    assert block.nbytes <= 64 * 1024 ** 2 / 3, block.nbytes
