"""FFT では足りないスペクトル推定の門(2026-10-03、陣 1b): Lomb–Scargle と部分空間法の到来方向推定。

閉じた式と定理で立てる: Lomb–Scargle は等間隔なら |DFT|²/N / ESPRIT は雑音なしで厳密 /
MUSIC と ESPRIT は遅延和が 1 本に融かす 1 ビーム幅以内の 2 波を分ける / MDL は波源の数を当てる。
主張の裏(壊れる条件)も門に置く: 相関した 2 波では MUSIC の峰が割れない。
"""
import math
import warnings

import numpy as np
import pytest

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import fullseye as fs
    import mathspectral as S
    import opsmath

LEDGER = ["lomb_scargle", "ula_snapshots", "music_doa", "esprit_doa", "n_sources_mdl", "hilbert_analytic"]


def test_public_and_ledger():
    assert opsmath.missing() == []
    assert sorted(opsmath.list_ops("spectral")) == sorted(LEDGER)
    assert sorted(S.__all__) == sorted(LEDGER)
    for n in LEDGER:
        assert callable(getattr(fs, n)) and n in fs.__all__ and callable(getattr(fs.ledger, n)), n


def test_lomb_scargle_equals_the_periodogram_for_even_sampling():
    N, dt = 64, 0.5
    t = np.arange(N) * dt
    y = np.sin(2 * math.pi * 0.37 * t) + 0.3 * np.random.default_rng(0).normal(size=N)
    k = np.arange(1, N // 2)
    P = S.lomb_scargle(t, y, k / (N * dt))["power"]
    D = np.abs(np.fft.fft(y - y.mean()))[1:N // 2] ** 2 / N
    assert np.abs(P - D).max() < 1e-12 * D.max()


def test_lomb_scargle_finds_the_period_of_uneven_samples_where_a_naive_fft_cannot():
    rng = np.random.default_rng(1)
    t = np.sort(rng.uniform(0, 100, 150))
    y = np.sin(2 * math.pi * 0.137 * t) + 0.5 * rng.normal(size=t.size)
    f = np.linspace(0.01, 0.5, 5000)
    assert abs(S.lomb_scargle(t, y, f)["peak_freq"] - 0.137) < 2e-3
    with pytest.raises(ValueError):
        S.lomb_scargle(t, y, [0.0, 0.1])


def _bartlett_peaks(X, lo=5, hi=21):          # 2 波のまわりだけ(外はサイドローブ)
    R = X @ X.conj().T / X.shape[1]
    g = np.linspace(-90, 90, 3601)
    A = S._steer(X.shape[0], 0.5, np.radians(g))
    P = np.real(np.sum(A.conj() * (R @ A), axis=0))
    pk = np.flatnonzero((P[1:-1] > P[:-2]) & (P[1:-1] >= P[2:])) + 1
    return g[pk][(g[pk] > lo) & (g[pk] < hi)]


def test_subspace_methods_split_two_sources_inside_one_beamwidth():
    X = S.ula_snapshots([10.0, 16.0], 8, 400)               # 6° 差、ビーム幅 ≈ 12.7°
    assert len(_bartlett_peaks(X)) == 1                       # 遅延和は 1 本に融ける(対照)
    assert np.allclose(S.esprit_doa(X, 2)["doa_deg"], [10.0, 16.0], atol=1e-8)
    assert np.allclose(S.music_doa(X, 2)["doa_deg"], [10.0, 16.0], atol=0.05)
    Xn = S.ula_snapshots([10.0, 16.0], 8, 400, snr_db=10)
    assert np.allclose(S.esprit_doa(Xn)["doa_deg"], [10.0, 16.0], atol=0.5)


def test_mdl_counts_the_sources():
    assert S.n_sources_mdl(S.ula_snapshots([10.0, 16.0], 8, 400, snr_db=10))["n_sources"] == 2
    assert S.n_sources_mdl(S.ula_snapshots([-30.0, 5.0, 40.0], 8, 400, snr_db=15))["n_sources"] == 3
    r = S.music_doa(S.ula_snapshots([10.0, 16.0], 8, 400, snr_db=10))
    assert r["n_sources"] == 2 and r["n_sources_estimated"]


def test_coherent_sources_break_music_as_the_docstring_warns():
    """同じ信号の 2 つの到来(多重反射)では共分散の階数が 1 に潰れ、MUSIC は 2 本に割れない。"""
    M, K = 8, 400
    s = (np.random.default_rng(3).normal(size=K) + 1j * np.random.default_rng(4).normal(size=K)) / math.sqrt(2)
    A = S._steer(M, 0.5, np.radians([10.0, 16.0]))
    X = A @ np.vstack([s, 0.8 * s])
    vals = S.n_sources_mdl(X)["eigenvalues"]
    assert vals[1] < 1e-10 * vals[0]                          # 階数 1
    doa = S.music_doa(X, 2)["doa_deg"]
    assert not np.allclose(doa, [10.0, 16.0], atol=1.0)


# ── 解析信号と瞬時周波数(Hilbert)───────────────────────────────────────────────────────────────── #
def test_hilbert_turns_cos_into_sin():
    """Hilbert 変換の定義: H[cos] = sin。周期が窓にちょうど収まれば丸め誤差まで一致し、瞬時周波数は一定。"""
    t = np.arange(4000) / 1000.0
    r = S.hilbert_analytic(np.cos(2 * np.pi * 50 * t), 1000)
    assert np.abs(r["analytic"].imag - np.sin(2 * np.pi * 50 * t)).max() < 1e-10
    assert np.abs(r["frequency"] - 50).max() < 1e-8
    assert np.abs(r["amplitude"] - 1).max() < 1e-10


def test_hilbert_bedrosian_holds_and_breaks():
    """Bedrosian の定理: 包絡線の帯域が搬送波より下なら振幅がそのまま戻る(5e-13)。重なると戻らない(失敗例)。"""
    t = np.arange(4000) / 1000.0
    env = 1 + 0.5 * np.cos(2 * np.pi * 3 * t)
    assert np.abs(S.hilbert_analytic(env * np.cos(2 * np.pi * 120 * t), 1000)["amplitude"] - env).max() < 1e-10
    env2 = 1 + 0.5 * np.cos(2 * np.pi * 90 * t)
    assert np.abs(S.hilbert_analytic(env2 * np.cos(2 * np.pi * 60 * t), 1000)["amplitude"] - env2).max() > 0.2


def test_hilbert_chirp_frequency_converges_away_from_the_ends():
    """線形チャープ f(t) = f0 + k·t: 内側では瞬時周波数が真値に乗り、端の乱れ(周期の仮定)は端から離れるほど減る。"""
    t = np.arange(4000) / 1000.0
    r = S.hilbert_analytic(np.cos(2 * np.pi * (20 * t + 30 * t ** 2 / 2)), 1000)
    err = [np.abs(r["frequency"][m:-m] - (20 + 30 * t[m:-m])).max() for m in (100, 400, 800)]
    assert err[0] > err[1] > err[2] and err[2] < 0.02


def test_hilbert_rejects_bad_input():
    with pytest.raises(ValueError):
        S.hilbert_analytic([1.0, 2.0])
    with pytest.raises(ValueError):
        S.hilbert_analytic(np.ones(16), fs=0)
