"""POD の â 側の穴(2026-11-09 点検 g4_2d_stats の med 3 件)。

1. pod_from_ahat の a90/95 は Wald だけで、点数が少ないと被覆率が名目 95 % に届かない
   (n = 40 で 0.89)。尤度比(プロファイル)の a90_95_lr と、n < 40 の small_sample を返す。
2. pod_ahat_fit は censor_low 無しで床に張り付いた点(同値が多数)を検出しなかった
   (60 点中 11 点、傾き 0.951 対 打ち切りあり 1.053・真値 1.1)。suspected_floor を返す。
3. pod_from_ahat は a_dec が記録の下限 censor_low より下でも黙って受けた。a_dec_below_floor を返す。
"""
import math

import numpy as np
import pytest

pytest.importorskip("scipy")
import pod  # noqa: E402

B0, B1, S, YDEC = 0.5, 1.1, 0.4, 5.0


def _data(n, seed):
    rg = np.random.default_rng(seed)
    a = np.exp(rg.uniform(np.log(20), np.log(400), n))
    y = B0 + B1 * np.log(a) + rg.normal(0, S, n)
    return a, y


def _floor_data():
    a, y = _data(60, 11)
    return a, np.maximum(y, 4.5)


def test_suspected_floor_counts_the_piled_points():
    a, y = _floor_data()
    k = int((y == 4.5).sum())
    assert k >= 3
    f = pod.pod_ahat_fit({"a": a, "ahat": np.exp(y)}, log_size=True, log_response=True)
    v, cnt = f["suspected_floor"]
    assert cnt == k and v == pytest.approx(math.exp(4.5))
    fc = pod.pod_ahat_fit({"a": a, "ahat": np.exp(y)}, log_size=True, log_response=True,
                          censor_low=math.exp(4.5))
    assert fc["suspected_floor"] is None


def test_clean_data_has_no_suspected_floor():
    a, y = _data(60, 12)
    f = pod.pod_ahat_fit({"a": a, "ahat": np.exp(y)}, log_size=True, log_response=True)
    assert f["suspected_floor"] is None and f["suspected_ceiling"] is None


def test_a_dec_below_the_recorded_floor_is_flagged():
    a, y = _floor_data()
    fc = pod.pod_ahat_fit({"a": a, "ahat": np.exp(y)}, log_size=True, log_response=True,
                          censor_low=math.exp(4.5))
    assert pod.pod_from_ahat(fc, math.exp(4.0))["a_dec_below_floor"] is True
    assert pod.pod_from_ahat(fc, math.exp(5.0))["a_dec_below_floor"] is False
    T = pod.pod_decision_tradeoff(fc, np.exp(np.random.default_rng(0).normal(4.0, 0.3, 50)),
                                  a_dec_grid=np.exp([4.0, 4.6, 5.0]))
    assert T["a_dec_below_floor"].tolist() == [True, False, False]


def test_wald_values_unchanged_and_new_keys_present():
    a, y = _data(40, 3)
    f = pod.pod_ahat_fit({"a": a, "ahat": np.exp(y)}, log_size=True, log_response=True)
    p = pod.pod_from_ahat(f, math.exp(YDEC))
    # Wald の閉形式(デルタ法)と一致(数値は変えていない)
    st = pod._stats()
    z9, z95 = st.norm.ppf(0.9), st.norm.ppf(0.95)
    b0, b1, s, C = f["beta0"], f["beta1"], f["sigma"], f["cov"]
    J = np.array([-1 / b1, -((YDEC - b0) / b1 + z9 * s / b1) / b1, z9 / b1])
    x90 = (YDEC - b0) / b1 + z9 * s / b1
    assert math.log(p["a90_95"]) == pytest.approx(x90 + z95 * math.sqrt(J @ C @ J), rel=1e-9)
    assert p["n"] == 40 and p["small_sample"] is False
    assert p["lr_status"] == "ok" and p["a90_95_lr"] > p["a90"]
    p10 = pod.pod_from_ahat(pod.pod_ahat_fit({"a": a[:10], "ahat": np.exp(y[:10])}, log_size=True,
                                             log_response=True), math.exp(YDEC))
    assert p10["small_sample"] is True


def test_lr_bound_is_the_profile_likelihood_crossing():
    """a90_95_lr で、a90 を固定したプロファイルの逸脱度がちょうど χ²₁(0.90) になる(scipy で独立に最大化)。"""
    from scipy import optimize, stats
    a, y = _data(30, 5)
    f = pod.pod_ahat_fit({"a": a, "ahat": np.exp(y)}, log_size=True, log_response=True)
    p = pod.pod_from_ahat(f, math.exp(YDEC))
    x = np.log(a)
    z9 = stats.norm.ppf(0.9)

    def ll(b0, b1, s):
        return float(stats.norm.logpdf(y, b0 + b1 * x, s).sum())

    llmax = ll(f["beta0"], f["beta1"], f["sigma"])
    t = math.log(p["a90_95_lr"])
    res = optimize.minimize(lambda q: -ll(YDEC + z9 * math.exp(q[1]) - q[0] * t, q[0], math.exp(q[1])),
                            [f["beta1"], math.log(f["sigma"])], method="Nelder-Mead",
                            options={"xatol": 1e-10, "fatol": 1e-12, "maxiter": 20000})
    dev = 2 * (llmax + res.fun)
    assert dev == pytest.approx(stats.chi2.ppf(0.9, 1), abs=2e-6)


def test_lr_coverage_is_closer_to_nominal_than_wald():
    """真の a90 が既知の合成(n = 40、300 反復)で、尤度比の被覆率が Wald 以上で 0.90 以上。"""
    st = pod._stats()
    tx = (YDEC - B0 + st.norm.ppf(0.9) * S) / B1
    rg_seed = 7
    hw = hl = 0
    R = 300
    for r in range(R):
        a, y = _data(40, rg_seed * 1000 + r)
        p = pod.pod_from_ahat(pod.pod_ahat_fit({"a": a, "ahat": np.exp(y)}, log_size=True,
                                               log_response=True), math.exp(YDEC))
        hw += math.log(p["a90_95"]) >= tx
        hl += p["a90_95_lr"] is not None and math.log(p["a90_95_lr"]) >= tx
    assert hl >= hw and hl / R >= 0.90, (hw / R, hl / R)


def test_hand_made_fit_without_data_reports_no_data():
    a, y = _data(40, 3)
    f = pod.pod_ahat_fit({"a": a, "ahat": np.exp(y)}, log_size=True, log_response=True)
    g = {k: f[k] for k in ("beta0", "beta1", "sigma", "cov", "log_size", "log_response", "size_min", "size_max")}
    p = pod.pod_from_ahat(g, math.exp(YDEC))
    assert p["a90_95_lr"] is None and p["lr_status"] == "no_data" and p["small_sample"] is None


def test_lr_bound_that_overflows_is_reported_not_inf():
    """対数座標で上限が exp の範囲を超えると inf と "ok" を返していた(PoC の 350 件中 1 件)。"""
    import warnings
    rg = np.random.default_rng(1)
    x = rg.uniform(700, 707, 20)
    y = 0.5 + 1.1 * x + rg.normal(0, 0.4, 20)
    f = pod.pod_ahat_fit({"a": np.exp(x), "ahat": y}, log_size=True)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        p = pod.pod_from_ahat(f, 0.5 + 1.1 * 709.2)
    assert p["a90_95_lr"] is None and p["lr_status"] == "overflow"


def test_profile_failure_is_reported_not_counted_as_rejection(monkeypatch):
    """最大化の失敗を棄却(inf)と数えると上限が楽観側に出る。失敗したら None と "profile_failed"(独立レビュー R7)。"""
    a, y = _data(40, 3)
    f = pod.pod_ahat_fit({"a": a, "ahat": np.exp(y)}, log_size=True, log_response=True)
    real = pod._tobit_newton
    calls = {"n": 0}

    def flaky(*args, **kw):
        if kw.get("off"):
            calls["n"] += 1
            if calls["n"] == 2:
                raise ValueError("forced failure (test)")
        return real(*args, **kw)

    monkeypatch.setattr(pod, "_tobit_newton", flaky)
    p = pod.pod_from_ahat(f, math.exp(YDEC))
    assert p["a90_95_lr"] is None and p["lr_status"] == "profile_failed"
    assert math.isfinite(p["a90_95"])
