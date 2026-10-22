import numpy as np

import mathtransforms
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
    # stream は乱数の消費順と行列積の区切りが違う別の実現なので、ビット一致ではなく
    # Monte Carlo のばらつきの範囲で一致することを門にする(受け取り時の実測 2026-10-22:
    # u 0.0079、mean 0.0021、low 0.100、high 0.054、half_width 0.023、全体 max 0.136)。
    # 定数との 1e-15 比較は BLAS や OS で乱数以外の桁が変わると落ちるので使わない。
    u0 = float(np.asarray(default["u_monte_carlo"]).ravel()[0])
    u1 = float(np.asarray(blocked["u_monte_carlo"]).ravel()[0])
    assert abs(u1 - u0) <= 0.02 * u0, f"u_monte_carlo 既定 {u0:.6g} / stream {u1:.6g}"
    se = u0 / np.sqrt(n)
    m0 = float(np.asarray(default["mean"]).ravel()[0]); m1 = float(np.asarray(blocked["mean"]).ravel()[0])
    assert abs(m1 - m0) <= 5.0 * se, f"mean 既定 {m0:.6g} / stream {m1:.6g} / 標準誤差 {se:.3g}"
    hw = float(np.asarray(default["half_width"]).ravel()[0])
    for key in ("low", "high", "half_width"):
        d = float(np.max(np.abs(np.asarray(default[key], float) - np.asarray(blocked[key], float))))
        assert d <= 0.05 * hw, f"{key} の差 {d:.4g} が半幅 {hw:.4g} の 5 % を超える"
    assert measured_max_diff < 1.0, f"全戻り値の実測 max |diff|={measured_max_diff:.6g}"
    assert default["n"] == blocked["n"] and default["level"] == blocked["level"]


def test_p030_block_generator_obeys_64_mib_workspace_limit():
    m = 32
    block = next(spc._mc_standardised_blocks(
        ["normal"] * m, np.eye(m), 1_000_000, 1, "gum_monte_carlo"
    ))
    assert block.nbytes <= 64 * 1024 ** 2 / 3, block.nbytes


def _old_synthesis(lo, hi, h, g, axis):
    lo = np.moveaxis(lo, axis, -1)
    hi = np.moveaxis(hi, axis, -1)
    m = lo.shape[-1]
    n = 2 * m
    out = np.zeros(lo.shape[:-1] + (n,))
    idx = (2 * np.arange(m)[:, None] + np.arange(h.size)[None, :]) % n
    for j in range(h.size):
        out[..., idx[:, j]] += lo * h[j] + hi * g[j]
    return np.moveaxis(out, -1, axis)


def test_p040_tapwise_synthesis_is_bit_identical_for_odd_and_even_band_lengths():
    rng = np.random.default_rng(3040)
    for m in (15, 16):
        lo = rng.normal(size=m)
        hi = rng.normal(size=m)
        for order in (2, 4, 6):
            filters = mathtransforms.wavelet_filters(order)
            before = _old_synthesis(lo, hi, filters["lowpass"], filters["highpass"], 0)
            after = mathtransforms._synthesis_axis(
                lo, hi, filters["lowpass"], filters["highpass"], 0
            )
            measured_max_diff = float(np.max(np.abs(before - after)))
            assert measured_max_diff == 0.0, f"raw synthesis max |diff|={measured_max_diff}"


def test_p040_tapwise_synthesis_is_bit_identical_in_2d_on_each_axis():
    rng = np.random.default_rng(3041)
    for shape, axis in (((15, 12), 0), ((12, 15), 1)):
        lo = rng.normal(size=shape)
        hi = rng.normal(size=shape)
        filters = mathtransforms.wavelet_filters(6)
        before = _old_synthesis(lo, hi, filters["lowpass"], filters["highpass"], axis)
        after = mathtransforms._synthesis_axis(
            lo, hi, filters["lowpass"], filters["highpass"], axis
        )
        measured_max_diff = float(np.max(np.abs(before - after)))
        assert measured_max_diff == 0.0, f"axis={axis}, max |diff|={measured_max_diff}"


def test_p040_inverse_is_bit_identical_to_legacy_synthesis_at_three_levels():
    rng = np.random.default_rng(3042)
    for shape in ((64,), (32, 48)):
        for order in (2, 4, 6):
            coeffs = mathtransforms.dwt_transform(rng.normal(size=shape), order=order, levels=3)
            after = mathtransforms.dwt_inverse(coeffs)
            original = mathtransforms._synthesis_axis
            try:
                mathtransforms._synthesis_axis = _old_synthesis
                before = mathtransforms.dwt_inverse(coeffs)
            finally:
                mathtransforms._synthesis_axis = original
            measured_max_diff = float(np.max(np.abs(before - after)))
            assert measured_max_diff == 0.0, (
                f"shape={shape}, order={order}, inverse max |diff|={measured_max_diff}"
            )
