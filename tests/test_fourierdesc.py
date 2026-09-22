# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""fourierdesc(楕円フーリエ記述子)のGTテスト。

beat-the-null: 「再構成が形状に収束する」「同形状は変換に不変で異形状とは乖離する」
という判別的 GT を数値で置く。ランダムな係数では通らない。
"""
import numpy as np
import pytest

import fourierdesc as F


def shp(kind, n=200, R=40, cx=0, cy=0, phi0=0.0):
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    if kind == "circle":
        x, y = R * np.cos(t), R * np.sin(t)
    elif kind == "square":
        c, s = np.cos(t), np.sin(t)
        m = np.maximum(np.abs(c), np.abs(s))
        x, y = R * c / m, R * s / m
    elif kind == "star":
        rr = R * (0.6 + 0.4 * np.cos(5 * t))
        x, y = rr * np.cos(t), rr * np.sin(t)
    elif kind == "ellipse":
        x, y = R * np.cos(t), 0.5 * R * np.sin(t)
    else:
        raise ValueError(kind)
    return np.column_stack([x * np.cos(phi0) - y * np.sin(phi0) + cx,
                            x * np.sin(phi0) + y * np.cos(phi0) + cy])


def _maxdist(pts, poly):
    P = np.vstack([poly, poly[0]])
    A, B = P[:-1], P[1:]
    AB = B - A
    L2 = (AB ** 2).sum(1) + 1e-12
    out = 0.0
    for p in pts:
        tt = np.clip(((p - A) * AB).sum(1) / L2, 0, 1)
        proj = A + tt[:, None] * AB
        out = max(out, np.sqrt(((proj - p) ** 2).sum(1)).min())
    return out


# --------------------------------------------------------------------------- #
# 係数と再構成                                                                 #
# --------------------------------------------------------------------------- #
def test_circle_is_first_harmonic():
    m = F.elliptic_fourier(shp("circle", R=50), n_harmonics=8)
    amp = F._amplitudes(m["coeffs"])[:, 0]  # 各高調波の長軸
    assert abs(amp[0] - 50.0) < 1.0            # 第1高調波 ≈ 半径
    assert amp[1:].max() < 0.05 * amp[0]       # 高次は無視できる


def test_dc_is_centroid():
    m = F.elliptic_fourier(shp("square", R=50, cx=12, cy=-7), n_harmonics=10)
    assert abs(m["a0"] - 12.0) < 0.5 and abs(m["c0"] + 7.0) < 0.5


def test_reconstruction_converges_with_harmonics():
    sq = shp("square", R=50)
    errs = [_maxdist(F.reconstruct(F.elliptic_fourier(sq, N), 300), sq)
            for N in [1, 3, 6, 12, 24]]
    # 高調波を増やすと単調に(ほぼ)減り、十分小さくなる(角の Gibbs は残る)
    assert all(errs[i] >= errs[i + 1] - 0.5 for i in range(len(errs) - 1))
    assert errs[-1] < 3.0 and errs[-1] < 0.2 * errs[0]


def test_reconstruct_truncation_smooths():
    star = shp("star", R=40)
    m = F.elliptic_fourier(star, 20)
    rough = F.reconstruct(m, 300, n_harmonics=20)
    smooth = F.reconstruct(m, 300, n_harmonics=2)  # 低次だけ = 丸い
    # 低次再構成の方が真円(半径一定)に近い = とがりが消える
    r_rough = np.std(np.hypot(rough[:, 0], rough[:, 1]))
    r_smooth = np.std(np.hypot(smooth[:, 0], smooth[:, 1]))
    assert r_smooth < r_rough


# --------------------------------------------------------------------------- #
# 不変性とマッチング(beat-the-null)                                          #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("variant", [
    dict(phi0=0.7), dict(R=68), dict(cx=120, cy=-40), dict(phi0=1.3, R=55, cx=-30, cy=25),
])
def test_descriptor_is_invariant(variant):
    base = F.elliptic_fourier(shp("star", R=40), 12)
    var = F.elliptic_fourier(np.roll(shp("star", **variant), 37, axis=0), 12)
    d_same = F.descriptor_distance(base, var, 12)
    d_diff = F.descriptor_distance(base, F.elliptic_fourier(shp("square", R=40), 12), 12)
    assert d_same < 1e-6                    # 相似変換+始点シフトに不変
    assert d_same < 0.01 * d_diff           # 異形状とは桁違いに離れる


def test_retrieval_picks_correct_shape():
    gallery = {k: F.elliptic_fourier(shp(k, R=30, cx=10, phi0=1.1), 12)
               for k in ["circle", "square", "star", "ellipse"]}
    query = F.elliptic_fourier(shp("square", R=55, cx=-40, cy=20, phi0=2.3), 12)
    dists = {k: F.descriptor_distance(query, g, 12) for k, g in gallery.items()}
    assert min(dists, key=dists.get) == "square"
    assert dists["square"] < 1e-6


# --------------------------------------------------------------------------- #
# 複素フーリエ平滑化                                                           #
# --------------------------------------------------------------------------- #
def test_fourier_smooth_identity_at_full_band():
    c = shp("circle", R=50, n=256)
    assert np.abs(F.fourier_smooth(c, keep=200) - c).max() < 1e-9


def test_fourier_smooth_denoises():
    c = shp("circle", R=50, n=256)
    rng = np.random.default_rng(0)
    noisy = c + rng.normal(0, 3, c.shape)
    sm = F.fourier_smooth(noisy, keep=3)
    dev_noisy = np.std(np.hypot(noisy[:, 0], noisy[:, 1]))
    dev_sm = np.std(np.hypot(sm[:, 0], sm[:, 1]))
    assert dev_sm < 0.5 * dev_noisy         # 高周波ノイズが落ちて半径が一定に近づく


# --------------------------------------------------------------------------- #
# XLD 連携と入力検証                                                           #
# --------------------------------------------------------------------------- #
def test_from_xld_integration():
    import contours_xld as X
    xld = X.gen_circle_contour_xld(128, 128, 40, n=120)
    m = F.elliptic_fourier(F.from_xld(xld), n_harmonics=6)
    assert m["coeffs"].shape == (6, 4)


def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        F.elliptic_fourier(np.zeros((2, 2)), 5)          # <3点
    with pytest.raises(ValueError):
        F.elliptic_fourier(np.zeros((10, 3)), 5)         # 形状不正
    with pytest.raises(ValueError):
        F.elliptic_fourier(shp("circle"), 0)             # n_harmonics<1
    with pytest.raises(ValueError):
        F.fourier_smooth(shp("circle"), 0)               # keep<1

# --------------------------------------------------------------------------- #
# 輪郭を「回る振り子の連鎖」で描く 3 op(2026-09-22)                            #
#   真値は全部閉形式 —— パーセバルにより、次数 K で打ち切った再構成の二乗誤差は  #
#   「|k| > K の係数の二乗和」に**厳密に等しい**。だから誤差を**予言**できる。   #
# --------------------------------------------------------------------------- #
def _circle(n=256, radius=7.0, centre=(0.0, 0.0)):
    """(row, col) 順の円。複素平面では実軸 = col、虚軸 = row。"""
    t = np.arange(n) / n
    return np.stack([centre[0] + radius * np.sin(2 * np.pi * t),
                     centre[1] + radius * np.cos(2 * np.pi * t)], axis=1)


def _square(n=400, side=50.0):
    """周を等間隔に回る正方形(4 回対称なので係数の立つ位置が決まる)。"""
    s = np.linspace(0.0, 4.0, n, endpoint=False)
    rows, cols = [], []
    for u in s:
        if u < 1.0:
            rows.append(0.0); cols.append(u)
        elif u < 2.0:
            rows.append(u - 1.0); cols.append(1.0)
        elif u < 3.0:
            rows.append(1.0); cols.append(3.0 - u)
        else:
            rows.append(4.0 - u); cols.append(0.0)
    return np.stack([np.asarray(rows) * side, np.asarray(cols) * side], axis=1)


def _coeffs(spectrum):
    k = np.round(spectrum[:, 0]).astype(int)
    return k, spectrum[:, 1] + 1j * spectrum[:, 2]


def test_a_circle_needs_exactly_one_term():
    """★円は 1 項で尽きる —— 非ゼロ係数が 1 本だけで、その大きさが半径そのもの。"""
    pts = _circle(radius=7.0)
    sp = F.contour_fourier_complex(pts)
    k, c = _coeffs(sp)
    big = np.abs(c) > 1e-9
    assert k[big].tolist() == [1], k[big]
    assert abs(c[big][0]) == pytest.approx(7.0, abs=1e-12)
    # 中心をずらすと c_0 がその位置になる(形の項は変わらない)
    sp2 = F.contour_fourier_complex(_circle(radius=7.0, centre=(3.0, -4.0)))
    k2, c2 = _coeffs(sp2)
    z0 = c2[list(k2).index(0)]
    assert z0.real == pytest.approx(-4.0, abs=1e-9)      # col
    assert z0.imag == pytest.approx(3.0, abs=1e-9)       # row


def test_parseval_closes_to_machine_precision():
    pts = _square()
    sp = F.contour_fourier_complex(pts)
    _k, c = _coeffs(sp)
    z = pts[:, 1] + 1j * pts[:, 0]
    assert float((np.abs(z) ** 2).mean()) == pytest.approx(float((np.abs(c) ** 2).sum()),
                                                           rel=1e-12)


def test_the_predicted_truncation_error_equals_the_measured_one():
    """★★予言が当たる: 打ち切り誤差は再構成する前に closed form で出る。"""
    pts = _square()
    sp = F.contour_fourier_complex(pts)
    k, c = _coeffs(sp)
    tab = F.contour_fourier_truncation_energy(sp)
    z = pts[:, 1] + 1j * pts[:, 0]
    n = z.size
    t = np.arange(n) / n
    orders = list(tab["order"])
    for K in (1, 2, 3, 5, 10, 20, 50):
        sel = np.abs(k) <= K
        rec = np.zeros(n, dtype=complex)
        for kj, cj in zip(k[sel], c[sel]):
            rec += cj * np.exp(2j * np.pi * kj * t)
        measured = float(np.sqrt((np.abs(z - rec) ** 2).mean()))
        predicted = float(tab["rms_error"][orders.index(K)])
        assert predicted == pytest.approx(measured, rel=1e-9, abs=1e-12), (K, predicted, measured)
    # 誤差は次数について単調非増加、エネルギーの割合は単調非減少で 1 に達する
    assert np.all(np.diff(tab["rms_error"]) <= 1e-15)
    assert np.all(np.diff(tab["energy_fraction"]) >= -1e-15)
    assert tab["energy_fraction"][-1] == pytest.approx(1.0, abs=1e-12)
    assert tab["rms_error"][-1] == pytest.approx(0.0, abs=1e-9)


def test_a_squares_coefficients_fall_off_as_one_over_k_squared():
    """★正方形は 4 回対称なので k = 1, 5, 9, … にだけ立ち、|c_k| k^2 が一定。"""
    sp = F.contour_fourier_complex(_square())
    k, c = _coeffs(sp)
    scaled = []
    for K in (1, 5, 9, 13):
        i = list(k).index(K)
        scaled.append(abs(c[i]) * K * K)
    ref = scaled[0]
    for v in scaled[1:]:
        assert v == pytest.approx(ref, rel=0.01), scaled
    # 4 の倍数だけずれた位置は厳密に 0(対称性の帰結)
    for K in (3, 7, 11):
        i = list(k).index(K)
        assert abs(c[i]) < 1e-9 * ref


def test_the_chain_tip_is_the_partial_sum_and_the_arms_are_the_amplitudes():
    sp = F.contour_fourier_complex(_square(), n_harmonics=40)
    k, c = _coeffs(sp)
    for t in np.linspace(0.0, 1.0, 9):
        chain = F.contour_epicycle_chain(sp, t)
        assert chain.shape == (2 * 40 + 2, 2)
        assert np.abs(chain[0]).max() == 0.0                       # 最初の腕は原点から
        tip = chain[-1, 1] + 1j * chain[-1, 0]
        assert abs(tip - complex((c * np.exp(2j * np.pi * k * t)).sum())) < 1e-9
    chain = F.contour_epicycle_chain(sp, 0.3)
    arms = np.hypot(np.diff(chain[:, 0]), np.diff(chain[:, 1]))
    order = np.argsort(np.abs(k) * 2 + (k < 0), kind="stable")
    assert np.abs(arms - np.abs(c[order])).max() < 1e-12
    # 振幅順に並べると、前のほうの腕が長くなる(少ない項で速く近づく)
    amp = F.contour_epicycle_chain(sp, 0.3, order="amplitude")
    a2 = np.hypot(np.diff(amp[:, 0]), np.diff(amp[:, 1]))
    assert np.all(np.diff(a2) <= 1e-12)
    assert a2[:5].sum() > arms[:5].sum()


def test_the_parametrisation_changes_the_answer_and_must_be_stated():
    """★★同じ形でも標本の密度が違えば係数は別物になる —— 絵は似たまま静かに。"""
    dense = _square(n=400)
    rng = np.random.default_rng(0)
    keep = np.sort(rng.choice(dense.shape[0], 120, replace=False))
    uneven = dense[keep]
    a = F.contour_fourier_complex(uneven, n_harmonics=20, parametrisation="index")
    b = F.contour_fourier_complex(uneven, n_harmonics=20, parametrisation="arclength")
    ka, ca = _coeffs(a)
    _kb, cb = _coeffs(b)
    rel = float(np.abs(ca - cb).sum() / np.abs(cb).sum())
    assert rel > 0.05, rel                       # 実測 0.20 —— 無視できる差ではない
    i3 = list(ka).index(3)
    assert abs(ca[i3]) > 5.0 * abs(cb[i3])       # 実測は 47 倍
    # 均等に打った輪郭なら 2 つの読み方はほぼ一致する(差は標本の偏りが作っている)
    a2 = F.contour_fourier_complex(dense, n_harmonics=20, parametrisation="index")
    b2 = F.contour_fourier_complex(dense, n_harmonics=20, parametrisation="arclength")
    _k2, c2a = _coeffs(a2)
    _k3, c2b = _coeffs(b2)
    assert float(np.abs(c2a - c2b).sum() / np.abs(c2b).sum()) < 0.02


def test_the_ops_refuse_what_they_cannot_answer():
    pts = _square(n=120)
    with pytest.raises(ValueError, match="contour_fourier_complex.*Nyquist"):
        F.contour_fourier_complex(pts, n_harmonics=500)
    with pytest.raises(ValueError, match="contour_fourier_complex.*parametrisation"):
        F.contour_fourier_complex(pts, parametrisation="by_angle")
    with pytest.raises(ValueError, match="contour_fourier_complex.*n_harmonics"):
        F.contour_fourier_complex(pts, n_harmonics=0)
    with pytest.raises(ValueError, match="must be a sequence of"):
        F.contour_fourier_complex(np.zeros((5, 3)))
    with pytest.raises(ValueError, match="non-finite"):
        bad = pts.copy()
        bad[3, 0] = np.nan
        F.contour_fourier_complex(bad)
    sp = F.contour_fourier_complex(pts, n_harmonics=5)
    with pytest.raises(ValueError, match="contour_epicycle_chain.*order"):
        F.contour_epicycle_chain(sp, 0.25, order="random")
    with pytest.raises(ValueError, match="contour_epicycle_chain.*finite"):
        F.contour_epicycle_chain(sp, np.nan)
    with pytest.raises(ValueError, match="spectrum must be the"):
        F.contour_epicycle_chain(np.zeros((4, 2)), 0.0)
    with pytest.raises(ValueError, match="contour_fourier_truncation_energy.*orders"):
        F.contour_fourier_truncation_energy(sp, orders=[0, 99])


def test_parseval_holds_for_every_sample_count_even_and_odd():
    """★★回帰: 偶数点でナイキストの係数を 2 回数えてパーセバルが破れていた。

    ``np.fft`` の添字 ``n/2`` は ``k = +n/2`` と ``k = -n/2`` の**同じ 1 つの係数**で、
    両方を並べるとエネルギーを 1 本ぶん多く数える。実測のずれは n=8 で 1.17e-01、
    n=512 で 7.5e-03。**最初の検査(正方形の輪郭)はこの係数がたまたま 0 に近くて
    通っていた** —— 構造の違う入力を並べないと見つからない種類の誤りである。
    """
    for n in (8, 9, 16, 17, 64, 255, 256):
        rng = np.random.default_rng(n)
        pts = np.stack([rng.normal(size=n), rng.normal(size=n)], axis=1)
        sp = F.contour_fourier_complex(pts)
        assert sp.shape[0] == n, (n, sp.shape)     # 係数の本数 = 標本の本数
        _k, c = _coeffs(sp)
        z = pts[:, 1] + 1j * pts[:, 0]
        assert float((np.abs(z) ** 2).mean()) == pytest.approx(
            float((np.abs(c) ** 2).sum()), rel=1e-12), n


def test_a_truncated_spectrum_gives_a_lower_bound_not_an_exact_error():
    """★打ち切った係数列では、捨てた側のエネルギーは**知りようがない**。

    返る誤差は下界になる。過小な誤差を「厳密」と言わないための検査。
    """
    n = 512
    rng = np.random.default_rng(3)
    pts = np.stack([rng.normal(size=n) * 10.0, rng.normal(size=n) * 10.0], axis=1)
    full = F.contour_fourier_complex(pts)
    cut = F.contour_fourier_complex(pts, n_harmonics=128)
    kf, cf = _coeffs(full)
    z = pts[:, 1] + 1j * pts[:, 0]
    t = np.arange(n) / n
    tf = F.contour_fourier_truncation_energy(full)
    tc = F.contour_fourier_truncation_energy(cut)
    of, oc = list(tf["order"]), list(tc["order"])
    for K in (4, 16, 64):
        sel = np.abs(kf) <= K
        rec = np.zeros(n, dtype=complex)
        for kj, cj in zip(kf[sel], cf[sel]):
            rec += cj * np.exp(2j * np.pi * kj * t)
        measured = float(np.sqrt((np.abs(z - rec) ** 2).mean()))
        assert tf["rms_error"][of.index(K)] == pytest.approx(measured, rel=1e-9)
        assert tc["rms_error"][oc.index(K)] <= measured + 1e-12   # 下界
    assert tc["rms_error"][oc.index(4)] < tf["rms_error"][of.index(4)]
