# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""パルスエコー超音波と走査型音響顕微鏡(ultrasound.py)の 7 op の門。

★この回の規律: **材料定数の値そのものに門を掛けない**。表の値は読んだ出典を写したもので、
確かめ方が弱いもの(Si の減衰、成膜した酸化膜)がある。門は関係だけに立てた:

1. **界面の恒等式**: ``R² + (Z1/Z2)T² = 1``、符号は ``Z2 < Z1`` のときに限り負。
2. **別の計算で答え合わせ**: 伝達行列の応答 = 下から積み上げる Airy の再帰(周波数領域)
   = 時間領域で経路を 1 本ずつ数えた和。光学の薄膜の Airy 式(matappear、n ↔ Z)とも。
3. **閉形式**: λ/2 層は透明、``Z = sqrt(Z0 Z2)`` の λ/4 層は無反射。
4. **べき乗則の逆算**: 2 つの厚さの裏面エコーのスペクトル比から α0, n を取り戻す。
5. **比例則**: 点の像の半値全幅が ``λ_w · F#``(log-log 傾き −1、狭帯域の極限で絶対値も)。
6. **位相 vs 振幅**: 振幅が等しく符号が逆の 2 つ(小さなボイドと大きなパッド)を作り、
   振幅では分けられず位相では分けられることを数える。
7. **最適周波数**: 閉形式 = 数値最適化 = 総当たり。POD の a90/95 で向きを確かめる。

壊して確かめた(手で一時的に壊し、どの門が落ちるかを見た。結果は CHANGELOG とコミット文に):
伝達行列の i の符号 / 水の波長の代わりに Si の波長で PSF / 反射係数の分母の符号 /
減衰の往復の 2 を落とす / 位相の基準を引き忘れる。
"""
from __future__ import annotations

import heapq
import math
import os
import sys

import numpy as np
import pytest

import ultrasound as us
import opsacoustics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MAT = us.acoustic_material_table()["materials"]


def _slope(x, y):
    return float(np.polyfit(np.log(x), np.log(y), 1)[0])


def _airy_recursive(stack, f):
    """下の界面から上へ ``R_j = (r_j + R_{j+1} e^{−2ik d}) / (1 + r_j R_{j+1} e^{−2ik d})``。

    伝達行列とは別の書き方(界面の反射係数と層の往復の位相だけ)。
    """
    media = [stack["couplant"]] + list(stack["layers"]) + [stack["substrate"]]
    f = np.asarray(f, dtype=np.float64)
    z = [m["Z"] for m in media]
    r_bottom = (z[-1] - z[-2]) / (z[-1] + z[-2])
    R = np.full(f.shape, r_bottom, dtype=np.complex128)
    for j in range(len(media) - 2, 0, -1):          # 層 j(媒質 j)の上の界面へ
        m = media[j]
        k = 2 * np.pi * f / m["c"] - 1j * (m["alpha0"] * f ** m["alpha_n"] if m["alpha0"] else 0.0)
        ph = np.exp(-2j * k * m["thickness"])
        r = (z[j] - z[j - 1]) / (z[j] + z[j - 1])
        R = (r + R * ph) / (1 + r * R * ph)
    return R


def _ray_sum(stack, t_max, amp_floor=1e-13):
    """時間領域の経路の和: 界面で反射・透過を 1 回ずつ分けて、結合液に戻る到着を数える。

    経路は「層 j を片道で何回通ったか」の回数の組で時刻が決まる(``t = Σ n_j τ_j``)。
    同じ回数の組・同じ界面・同じ向きの経路は同じ時刻に着くので振幅を足してから進める
    (足さないと経路の数が指数で増える)。返り: [(時刻 [s] 表面エコー = 0 から, 振幅)]。
    損失なしの層だけ。
    """
    media = [stack["couplant"]] + list(stack["layers"]) + [stack["substrate"]]
    z = [m["Z"] for m in media]
    nl = len(media) - 2                                 # 層の数
    tau = [0.0] + [m["thickness"] / m["c"] for m in stack["layers"]] + [0.0]
    rd = [(z[i + 1] - z[i]) / (z[i + 1] + z[i]) for i in range(nl + 1)]
    td = [2 * z[i + 1] / (z[i + 1] + z[i]) for i in range(nl + 1)]
    tu = [2 * z[i] / (z[i + 1] + z[i]) for i in range(nl + 1)]
    out = {}
    pending = {}
    q = []

    def push(counts, i, above, a):
        tt = sum(n * tau[j + 1] for j, n in enumerate(counts))
        if tt > t_max:
            return
        key = (counts, i, above)
        if key in pending:
            pending[key] += a
        else:
            pending[key] = a
            heapq.heappush(q, (tt, key))

    def bump(counts, layer):                             # 層 layer(1..nl)を 1 回通る
        c = list(counts)
        c[layer - 1] += 1
        return tuple(c)

    def emit(counts, a):
        out[counts] = out.get(counts, 0.0) + a

    push(tuple([0] * nl), 0, True, 1.0)
    while q:
        _, key = heapq.heappop(q)
        a = pending.pop(key)
        counts, i, above = key
        if abs(a) < amp_floor:
            continue
        if above:                                        # 媒質 i から界面 i に下向きで着いた
            refl, trans = a * rd[i], a * td[i]
            if i == 0:
                emit(counts, refl)
            else:
                push(bump(counts, i), i - 1, False, refl)
            if i + 1 <= nl:
                push(bump(counts, i + 1), i + 1, True, trans)
        else:                                            # 媒質 i+1 から界面 i に上向きで着いた
            refl, trans = -a * rd[i], a * tu[i]
            if i + 1 <= nl:
                push(bump(counts, i + 1), i + 1, True, refl)
            if i == 0:
                emit(counts, trans)
            else:
                push(bump(counts, i), i - 1, False, trans)
    return [(sum(n * tau[j + 1] for j, n in enumerate(c)), a) for c, a in out.items()]


def _bulk(name, d=1e-3, sub="silicon"):
    return us.acoustic_layer_stack([(name, d)], substrate=sub)


# --------------------------------------------------------------------------- #
# 1. 材料の表と界面
# --------------------------------------------------------------------------- #
def test_every_material_carries_a_source_and_a_verified_flag():
    for name, m in MAT.items():
        assert m["source"] and m["uncertainty"], name
        assert m["verified"] in (True, False), name
        assert m["Z"] == pytest.approx(m["rho"] * m["c"])
    # 確かめていない代表値は既定では使えない
    with pytest.raises(ValueError, match="unverified"):
        us.acoustic_layer_stack([("polyimide", 5e-6)])
    s = us.acoustic_layer_stack([("polyimide", 5e-6)], allow_unverified=True)
    assert s["verified"] is False
    assert us.acoustic_layer_stack()["verified"] is True


@pytest.mark.parametrize("pair", [("water", "silicon"), ("silicon", "air"), ("silicon", "copper"),
                                  ("silicon", "sio2"), ("copper", "sio2"), ("sio2", "silicon")])
def test_interface_energy_is_conserved_and_the_sign_flips_exactly_when_z_drops(pair):
    a, b = pair
    s = us.acoustic_layer_stack([(a, 1e-3)], substrate=b) if a != "water" else \
        us.acoustic_layer_stack([], substrate=b)
    c = us.acoustic_interface_coefficients(s)
    assert np.allclose(c["energy"], 1.0, atol=1e-14)
    assert np.array_equal(c["R"] < 0, c["z2"] < c["z1"])
    assert np.array_equal(c["inverted"], c["z2"] < c["z1"])
    assert np.allclose(c["T"], 1 + c["R"], atol=1e-15)        # 圧力の連続


def test_random_impedances_conserve_energy_and_flip_sign_only_on_a_drop():
    rng = np.random.default_rng(3)
    for _ in range(200):
        z1, z2 = np.exp(rng.uniform(np.log(1e2), np.log(1e8), 2))
        s = us.acoustic_layer_stack([({"rho": z1 / 1000.0, "c": 1000.0}, 1e-3)],
                                    substrate={"rho": z2 / 1000.0, "c": 1000.0},
                                    couplant={"rho": z1 / 1000.0, "c": 1000.0})
        c = us.acoustic_interface_coefficients(s)
        assert abs(c["energy"][1] - 1.0) < 1e-12
        assert (c["R"][1] < 0) == (z2 < z1)


# --------------------------------------------------------------------------- #
# 2. 伝達行列 = 別の計算
# --------------------------------------------------------------------------- #
def _random_stack(rng, n):
    names = ["silicon", "sio2", "copper"]
    layers = [(names[rng.integers(3)], float(rng.uniform(0.3e-6, 40e-6))) for _ in range(n)]
    return us.acoustic_layer_stack(layers, substrate=names[rng.integers(3)])


def test_transfer_matrix_equals_the_recursive_airy_sum_on_random_stacks():
    rng = np.random.default_rng(11)
    f = np.linspace(1e6, 2e9, 777)
    for n in (0, 1, 2, 3, 5, 8):
        for _ in range(5):
            s = _random_stack(rng, n)
            assert np.max(np.abs(us._stack_reflection(s, f) - _airy_recursive(s, f))) < 1e-12


def test_lossy_layers_also_agree_and_attenuate():
    lossy = {"rho": 1200.0, "c": 2500.0, "alpha0": 2e-9, "alpha_n": 1.3, "name": "lossy"}
    s = us.acoustic_layer_stack([(lossy, 0.5e-3), ("copper", 10e-6)], substrate="air")
    f = np.linspace(5e6, 3e8, 300)
    assert np.max(np.abs(us._stack_reflection(s, f) - _airy_recursive(s, f))) < 1e-12


def test_ascan_equals_the_time_domain_ray_sum():
    """伝達行列の A スキャン(周波数領域)= 経路を 1 本ずつ数えた和(時間領域)。"""
    s = us.acoustic_layer_stack([("silicon", 120e-6), ("copper", 35e-6)], substrate="sio2")
    a = us.pulse_echo_ascan(s, f0=80e6, bandwidth=0.6, water_path=1e-4, n_reverb=40)
    window = a["t"][-1] - a["t"][0]
    rays = _ray_sum(s, t_max=20 * window)            # 窓の外の残響も(FFT の折り返しは両方に同じ)
    # 同じパルスを経路の時刻に置いて足す(水の経路の位相と減衰は両方に同じ係数で掛かる)
    fb, wb = a["freqs"], a["weights"]
    hw = np.exp(-2j * (2 * np.pi * fb / s["couplant"]["c"] - 1j * MAT["water"]["alpha0"] * fb ** 2)
                * a["water_path"])
    amp = np.array([r[1] for r in rays])
    tt = np.array([r[0] for r in rays])
    spec = (amp[None, :] * np.exp(-2j * np.pi * fb[:, None] * tt[None, :])).sum(axis=1)
    sel = slice(0, a["t"].size, 7)
    pulse = (wb * hw * spec) @ np.exp(2j * np.pi * np.outer(fb, a["t"][sel]))
    err = np.max(np.abs(pulse - a["analytic"][sel])) / np.max(np.abs(a["analytic"]))
    assert len(rays) > 20
    assert err < 1e-6, err


def test_half_wave_layer_is_transparent_and_quarter_wave_matches():
    f = 50e6
    zx = 7.0e6
    cx = 3000.0
    half = us.acoustic_layer_stack([({"rho": zx / cx, "c": cx}, cx / (2 * f))], substrate="water")
    assert abs(us._stack_reflection(half, np.array([f]))[0]) < 1e-12
    zq = math.sqrt(MAT["water"]["Z"] * MAT["silicon"]["Z"])
    quarter = us.acoustic_layer_stack([({"rho": zq / cx, "c": cx}, cx / (4 * f))], substrate="silicon")
    assert abs(us._stack_reflection(quarter, np.array([f]))[0]) < 1e-12
    # 帯域の外では反射が戻る(恒等的に 0 になる式を書いていない)
    assert abs(us._stack_reflection(quarter, np.array([1.5 * f]))[0]) > 0.3
    # 層が無いときの裸の界面と比べて、λ/4 の厚さで最小・λ/2 で裸と同じ
    bare = abs(us._stack_reflection(us.acoustic_layer_stack([], substrate="silicon"), np.array([f]))[0])
    lam2 = us.acoustic_layer_stack([({"rho": zq / cx, "c": cx}, cx / (2 * f))], substrate="silicon")
    assert abs(abs(us._stack_reflection(lam2, np.array([f]))[0]) - bare) < 1e-12


def test_single_layer_matches_the_optical_thin_film_airy_formula():
    """n ↔ Z、δ = 4π n d / λ ↔ 2 k d の写像で、光学の薄膜の反射率(matappear)と一致。"""
    import matappear

    for film, sub in (("sio2", "silicon"), ("copper", "silicon"), ("silicon", "sio2")):
        s = us.acoustic_layer_stack([(film, 3.0e-6)], substrate=sub)
        z0, z1, z2 = (m["Z"] / 1e6 for m in (s["couplant"], s["layers"][0], s["substrate"]))
        c1 = s["layers"][0]["c"]
        f = np.linspace(10e6, 4e9, 400)
        lam_nm = z1 * c1 / f * 1e9
        opt = matappear.thin_film_reflectance(lam_nm, thickness_nm=3.0e-6 * 1e9, n_film=z1,
                                              n_sub=z2, n_out=z0)
        ac = np.abs(us._stack_reflection(s, f)) ** 2
        assert np.max(np.abs(opt - ac)) < 1e-12


# --------------------------------------------------------------------------- #
# 3. 減衰のべき乗則を取り戻す
# --------------------------------------------------------------------------- #
def _backwall_spectrum(a, t_echo, hw):
    sel = (a["t"] >= t_echo - hw) & (a["t"] <= t_echo + hw)
    x = np.zeros_like(a["rf"])
    x[sel] = a["rf"][sel] * np.hanning(sel.sum())
    return np.abs(np.fft.rfft(x))


@pytest.mark.parametrize("n_true", [1.0, 1.3, 2.0])
def test_echo_spectrum_ratio_recovers_the_attenuation_power_law(n_true):
    a0 = 400.0 / (1e8 ** n_true)                     # 100 MHz で 400 Np/m
    mat = {"rho": 1200.0, "c": 2500.0, "alpha0": a0, "alpha_n": n_true, "name": "lossy"}
    d1, d2 = 1.0e-3, 1.5e-3
    spec, fq = [], None
    for d in (d1, d2):
        s = us.acoustic_layer_stack([(mat, d)], substrate="air")
        a = us.pulse_echo_ascan(s, f0=60e6, bandwidth=0.8, water_path=1e-3, rate=1.0e9,
                                duration=6.0e-6)          # 2 つの厚さで同じ窓・同じ周波数格子
        hw = 0.3e-6                                   # 窓は広く(狭いとスペクトルが窓で均される)
        spec.append(_backwall_spectrum(a, a["t_interfaces"][1], hw))
        fq = np.fft.rfftfreq(a["rf"].size, 1 / a["rate"])
    ws = spec[0] > 0.2 * spec[0].max()
    alpha = -np.log(spec[1][ws] / spec[0][ws]) / (2 * (d2 - d1))
    n_fit, c_fit = np.polyfit(np.log(fq[ws]), np.log(alpha), 1)
    assert abs(n_fit - n_true) < 0.02, n_fit
    # α0 は切片なので n の誤差を f^Δn で増幅する(1e8^0.01 = 1.2 倍)—— 帯域の中心の α で比べる
    f_mid = 60e6
    assert abs(math.exp(c_fit) * f_mid ** n_fit / (a0 * f_mid ** n_true) - 1) < 0.02


# --------------------------------------------------------------------------- #
# 4. 横分解能 ∝ λ_w · F#
# --------------------------------------------------------------------------- #
def _point_fwhm(f0, fnum, bw=0.6, px=0.4e-6, water_path=1e-6):
    """点反射体の振幅像の半値全幅。

    ★水の経路は既定でほぼ 0: 減衰 ∝ f² はスペクトルの重心を下げ(0.2 mm・250 MHz で約 8 %)、
    像を太らせる —— それは物理だが、ここで測りたいのは幾何の比例則なので切り離す。
    """
    # 厚い Si(3 mm): 狭帯域の長いパルスでも表面エコーの裾がゲートに入らない
    bg = us.acoustic_layer_stack([("silicon", 3e-3)], substrate="silicon")       # R = 0
    pt = us.acoustic_layer_stack([("silicon", 3e-3)], substrate="air")           # R = −1
    n = 161
    m = np.zeros((n, n), dtype=np.int64)
    m[n // 2, n // 2] = 1
    lam = 1481.0 / f0
    px = lam * fnum / 12.0
    c = us.sam_cscan(m, {0: bg, 1: pt}, pixel_size=px, f0=f0, bandwidth=bw, f_number=fnum,
                     water_path=water_path, n_reverb=2)
    prof = c["amplitude"][n // 2]
    half = prof.max() / 2
    above = np.nonzero(prof >= half)[0]
    i0, i1 = above[0], above[-1]
    x_l = i0 - 1 + (half - prof[i0 - 1]) / (prof[i0] - prof[i0 - 1])
    x_r = i1 + (prof[i1] - half) / (prof[i1] - prof[i1 + 1])
    return (x_r - x_l) * px, c


def test_point_response_width_scales_as_lambda_times_f_number():
    fs_ = np.array([60e6, 100e6, 160e6, 250e6])
    w = np.array([_point_fwhm(f, 3.0)[0] for f in fs_])
    assert abs(_slope(fs_, w) + 1.0) < 0.02
    fn = np.array([3.0, 4.5, 7.0])
    w2 = np.array([_point_fwhm(100e6, x)[0] for x in fn])
    assert abs(_slope(fn, w2) - 1.0) < 0.02


def test_narrowband_point_width_is_the_closed_form():
    w, c = _point_fwhm(100e6, 3.0, bw=0.08)
    closed = 1.02 * (1481.0 / 100e6) * 3.0
    assert abs(w / closed - 1) < 0.02, w / closed
    assert c["psf_fwhm_f0"] == pytest.approx(closed)


def test_psf_frequency_nodes_converge():
    bg = us.acoustic_layer_stack([("silicon", 100e-6)], substrate="silicon")
    pt = us.acoustic_layer_stack([("silicon", 100e-6)], substrate="air")
    m = np.zeros((64, 64), dtype=np.int64)
    m[28:36, 30:33] = 1
    kw = dict(pixel_size=2e-6, f0=150e6, f_number=3.0, water_path=0.5e-3)
    a = us.sam_cscan(m, {0: bg, 1: pt}, psf_nodes=32, **kw)
    b = us.sam_cscan(m, {0: bg, 1: pt}, psf_nodes=128, **kw)
    assert np.max(np.abs(a["amplitude"] - b["amplitude"])) < 1e-3 * a["amplitude"].max()


def test_receiver_noise_has_the_stated_rms_in_both_quadratures():
    """雑音は RF の実部の RMS = noise_rms として入る。期待時刻で読んだ同相・直交の成分の画素間の
    標準偏差はどちらも noise_rms(±5 %)、平均は一面の値(雑音なし)から動かない。
    ★包絡線の山の時刻で位相を読んでいた版では、山の時刻の揺れが位相を回し、同相成分の
    ばらつきが雑音の数倍になっていた(POD の閾値がそれで決まってしまう)。"""
    s = us.acoustic_layer_stack([("silicon", 100e-6), ("sio2", 1e-6), ("sio2", 1e-6)])
    for nz in (1e-3, 3e-3):
        c = us.sam_cscan(np.zeros((48, 48), dtype=np.int64), {0: s}, f0=200e6, water_path=1e-3,
                         gate_interface=2, noise_rms=nz, seed=3)
        q = c["amplitude_at_t"] * np.sin(c["phase"])
        assert abs(c["inphase"].std() / nz - 1) < 0.05
        assert abs(q.std() / nz - 1) < 0.05
        assert abs(c["inphase"].mean() - c["plane_phasor"][0].real) < 0.05 * nz


def test_aperture_beyond_the_critical_angle_is_refused():
    s = us.acoustic_layer_stack()
    m = np.zeros((8, 8), dtype=np.int64)
    fmin = 1 / (2 * math.tan(math.asin(1481.0 / 8430.0)))
    with pytest.raises(ValueError, match="critical angle"):
        us.sam_cscan(m, {0: s}, f_number=0.98 * fmin)
    us.sam_cscan(m, {0: s}, f_number=1.02 * fmin)


# --------------------------------------------------------------------------- #
# 5. 位相は振幅が分けられないものを分ける
# --------------------------------------------------------------------------- #
def _equal_amplitude_case():
    """半無限の界面: 背景 Si|Si(R = 0)、ボイド Si|空気(R ≈ −1)の小円、パッド Si|Cu(R > 0)の大円。

    ボイドの直径を二分法で選び、中心の振幅をパッドの中心に揃える。返り: (C スキャン, 直径 [m],
    ボイドの中心, パッドの中心)。
    """
    bg = us.acoustic_layer_stack([("silicon", 300e-6)], substrate="silicon")
    vd = us.acoustic_layer_stack([("silicon", 300e-6)], substrate="air")
    pd = us.acoustic_layer_stack([("silicon", 300e-6)], substrate="copper")
    px, ny, nx = 1.5e-6, 64, 128
    yy, xx = np.mgrid[:ny, :nx]
    cv, cp = (32, 100), (32, 34)
    kw = dict(pixel_size=px, f0=150e6, bandwidth=0.6, f_number=3.0, water_path=0.5e-3)

    def run(dv):
        m = np.zeros((ny, nx), dtype=np.int64)
        m[(yy - cp[0]) ** 2 + (xx - cp[1]) ** 2 <= (40e-6 / px) ** 2] = 2      # パッド 80 µm
        m[((yy - cv[0]) * px) ** 2 + ((xx - cv[1]) * px) ** 2 <= (dv / 2) ** 2] = 1
        return us.sam_cscan(m, {0: bg, 1: vd, 2: pd}, **kw)

    lo, hi = 3e-6, 40e-6
    for _ in range(14):
        mid = 0.5 * (lo + hi)
        c = run(mid)
        if c["amplitude"][cv] < c["amplitude"][cp]:
            lo = mid
        else:
            hi = mid
    dv = 0.5 * (lo + hi)
    return run(dv), dv, cv, cp


def test_void_and_pad_with_equal_amplitude_have_opposite_phase():
    c, dv, cv, cp = _equal_amplitude_case()
    av, ap = c["amplitude"][cv], c["amplitude"][cp]
    # 振幅は同じ(ラベルの地図は画素で刻まれ、1.5 µm の輪 1 つでボイドの中心の振幅が数 % 跳ぶ
    # ので、二分法で揃えられるのは 2 % まで。実測 1.3 %)
    assert abs(av / ap - 1) < 0.02
    assert 4e-6 < dv < c["psf_fwhm_f0"]                       # ビームより小さいボイド
    pv, pp = math.degrees(c["phase"][cv]), math.degrees(c["phase"][cp])
    assert abs(abs(pv) - 180) < 3, pv                          # 反転
    assert abs(pp) < 3, pp                                     # 同相
    assert c["inphase"][cv] < 0 < c["inphase"][cp]
    pol = us.echo_phase_polarity(c)["polarity"]
    assert pol[cv] == -1 and pol[cp] == 1
    # 振幅の閾値ではどちらか一方だけを「ボイド」と言うことはできない
    for thr in np.linspace(0, 2 * ap, 101):
        if abs(thr - ap) > 0.02 * ap:
            assert (av > thr) == (ap > thr)


def test_thin_bond_layer_echoes_are_quadrature_and_voids_are_inverted():
    """位相は接合面(上下の半分が出会う面、界面 2)の期待時刻で読む。薄い Cu・SiO2 の層は
    その面を中心に対称なので直交(±90°)、ボイドは反転。"""
    die = 100e-6
    diel = us.acoustic_layer_stack([("silicon", die), ("sio2", 1e-6), ("sio2", 1e-6)])
    pad = us.acoustic_layer_stack([("silicon", die), ("copper", 1e-6), ("copper", 1e-6)])
    void = us.acoustic_layer_stack([("silicon", die), ("sio2", 1e-6), ("air", 0.1e-6), ("sio2", 1e-6)])
    vpad = us.acoustic_layer_stack([("silicon", die), ("copper", 1e-6), ("air", 0.1e-6), ("copper", 1e-6)])
    out = {}
    for f0 in (150e6, 250e6, 350e6):
        for name, s in (("diel", diel), ("pad", pad), ("void", void), ("vpad", vpad)):
            a = us.pulse_echo_ascan(s, f0=f0, water_path=0.5e-3)
            out[name, f0] = us.echo_phase_polarity(a, interface=2)
        assert out["void", f0]["polarity"] == -1 and out["vpad", f0]["polarity"] == -1
        assert out["pad", f0]["polarity"] == 0 and 75 < out["pad", f0]["phase_deg"] < 105
        assert out["diel", f0]["polarity"] == 0 and -105 < out["diel", f0]["phase_deg"] < -75
    # 従来の「極性」(ゲート内で |RF| が最大の 1 点の符号)は、無傷の Cu パッドで周波数によって
    # 反転側にも同相側にも転ぶ(直交のエコーの 1 点の符号に意味が無い)。
    assert {out["pad", f]["signed_peak"] for f in (150e6, 250e6, 350e6)} == {-1, 1}
    out = {k[0]: v for k, v in out.items() if k[1] == 250e6}
    # 薄い層の閉形式: R ≈ (i k t/2)(z − 1/z) — Cu は +90°、SiO2 は −90°
    zs = MAT["silicon"]["Z"]
    for nm, sign in (("copper", 1), ("sio2", -1)):
        z = MAT[nm]["Z"] / zs
        assert np.sign(z - 1 / z) == sign
    assert out["void"]["amplitude"] > 2 * out["pad"]["amplitude"]


def test_the_reference_is_the_front_echo_and_it_can_itself_be_inverted():
    """位相は表面エコーに対して測る。表面そのものが Z の下がる界面なら(水より柔らかい層)、
    Z の上がる深い界面のエコーは表面に対して 180° —— 基準を引かなければ 0° と読まれる。"""
    soft = {"rho": 500.0, "c": 1000.0, "name": "soft"}            # Z = 0.5 MRayl < 水
    s = us.acoustic_layer_stack([(soft, 200e-6)], substrate="silicon")
    a = us.pulse_echo_ascan(s, f0=60e6, water_path=0.5e-3)
    r = us.echo_phase_polarity(a, interface=1)
    assert abs(abs(r["phase_deg"]) - 180) < 3 and r["polarity"] == -1
    c = us.sam_cscan(np.zeros((8, 8), dtype=np.int64), {0: s}, f0=60e6, f_number=3.0, water_path=0.5e-3)
    assert abs(abs(c["reference_phase"]) - math.pi) < 0.05
    assert np.all(np.abs(np.abs(c["phase"]) - math.pi) < 0.05)


# --------------------------------------------------------------------------- #
# 6. 最適周波数と POD
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("a", [3e-6, 10e-6, 30e-6, 100e-6])
@pytest.mark.parametrize("zw", [0.3e-3, 1e-3])
def test_closed_form_optimum_matches_numeric_and_brute_force(a, zw):
    s = us.acoustic_layer_stack()
    r = us.sam_frequency_tradeoff(s, a, water_path=zw, f_number=3.0)
    assert r["f_opt_closed"] is not None
    assert abs(r["f_opt"] / r["f_opt_closed"] - 1) < 1e-6
    f = np.geomspace(1e6, 5e9, 200001)
    k = r["k"]
    sig = (1 - 2.0 ** (-(a * f / k) ** 2)) * np.exp(-r["beta"] * f ** 2)
    fb = f[np.argmax(sig)]
    assert abs(fb / r["f_opt_closed"] - 1) < 1e-4
    # 小さなボイドの極限は 1/√β
    if a == 3e-6:
        assert abs(r["f_opt_closed"] * math.sqrt(r["beta"]) - 1) < 0.25


def test_the_time_resolution_bound_is_where_the_front_echo_leaks_into_the_gate():
    """``f_min_time`` の上では、薄いダイ(100 µm)の接合面のゲートの振幅が、表面エコーから遠い厚い
    ダイ(2 mm、Si の減衰 0 なので同じ損失)と一致する。下では表面エコーの裾がゲートを支配する。"""
    bond = [("sio2", 1e-6), ("sio2", 1e-6)]
    thin = us.acoustic_layer_stack([("silicon", 100e-6)] + bond)
    thick = us.acoustic_layer_stack([("silicon", 2e-3)] + bond)
    fm = us.sam_frequency_tradeoff(thin, 10e-6, water_path=1e-3, interface=1)["f_min_time"]
    assert 100e6 < fm < 170e6
    amp = lambda s, f: us.echo_phase_polarity(us.pulse_echo_ascan(s, f0=f, water_path=1e-3), 1)["amplitude"]
    for k in (1.0, 1.3, 2.0):
        assert abs(amp(thin, k * fm) / amp(thick, k * fm) - 1) < 0.01, k
    assert amp(thin, 0.8 * fm) > 2 * amp(thick, 0.8 * fm)


def test_non_quadratic_attenuation_uses_the_numeric_optimum():
    lossy = {"rho": 1200.0, "c": 2500.0, "alpha0": 1e-6, "alpha_n": 1.1, "name": "lossy"}
    s = us.acoustic_layer_stack([("silicon", 50e-6), (lossy, 20e-6)], substrate="silicon")
    r = us.sam_frequency_tradeoff(s, 10e-6, water_path=0.5e-3, f_number=3.0)
    assert r["f_opt_closed"] is None
    f = np.geomspace(1e6, 5e9, 200001)
    k = r["k"]
    loss = 2 * MAT["water"]["alpha0"] * 0.5e-3 * f ** 2 + 2 * 1e-6 * 20e-6 * f ** 1.1
    sig = (1 - 2.0 ** (-(10e-6 * f / k) ** 2)) * np.exp(-loss)
    assert abs(f[np.argmax(sig)] / r["f_opt"] - 1) < 1e-4
    assert r["f_opt"] < us.sam_frequency_tradeoff(us.acoustic_layer_stack(), 10e-6, water_path=0.5e-3,
                                                  f_number=3.0)["f_opt"]


def _pod_run(f0, seed, n_side=6, spacing=60e-6, px=2e-6, noise=4e-4):
    rng = np.random.default_rng(seed)
    die = 100e-6
    diel = us.acoustic_layer_stack([("silicon", die), ("sio2", 1e-6), ("sio2", 1e-6)])
    void = us.acoustic_layer_stack([("silicon", die), ("sio2", 1e-6), ("air", 0.1e-6), ("sio2", 1e-6)])
    n = int(round(n_side * spacing / px))
    m = np.zeros((n, n), dtype=np.int64)
    yy, xx = np.mgrid[:n, :n]
    sizes, centres = [], []
    for i in range(n_side):
        for j in range(n_side):
            d = float(np.exp(rng.uniform(np.log(3e-6), np.log(30e-6))))
            cy, cx = (i + 0.5) * spacing / px, (j + 0.5) * spacing / px
            m[(yy - cy) ** 2 + (xx - cx) ** 2 <= (d / 2 / px) ** 2] = 1
            sizes.append(d)
            centres.append((int(round(cy)), int(round(cx))))
    c = us.sam_cscan(m, {0: diel, 1: void}, pixel_size=px, f0=f0, f_number=3.0, water_path=1e-3,
                     noise_rms=noise, seed=seed)
    ahat = np.array([-c["inphase"][y, x] for y, x in centres])
    # 無欠陥の部位: 格子の間(ボイドから半間隔離れた点)
    good = np.array([-c["inphase"][int(round(i * spacing / px)) % n, int(round(j * spacing / px)) % n]
                     for i in range(n_side) for j in range(n_side)])
    return np.array(sizes), ahat, good


def test_pod_a90_95_is_smaller_at_the_predicted_better_frequency():
    import pod

    res = {}
    for f0 in (150e6, 350e6):
        a, ah, good = [], [], []
        for seed in (1, 2, 3):
            s_, h_, g_ = _pod_run(f0, seed)
            a.append(s_); ah.append(h_); good.append(g_)
        a, ah, good = np.concatenate(a), np.concatenate(ah), np.concatenate(good)
        a_dec = float(good.mean() + 3.09 * good.std())
        fit = pod.pod_ahat_fit({"a": a * 1e6, "ahat": ah}, log_size=True)
        p = pod.pod_from_ahat(fit, a_dec)
        res[f0] = p["a90_95"]
    tr = us.sam_frequency_tradeoff(us.acoustic_layer_stack(), 10e-6, water_path=1e-3, f_number=3.0)
    sig = lambda f: float(np.interp(f, tr["freqs"], tr["signal"]))
    better = 150e6 if sig(150e6) > sig(350e6) else 350e6
    worse = 350e6 if better == 150e6 else 150e6
    assert res[better] < res[worse], res


# --------------------------------------------------------------------------- #
# 7. 拒否(fail-closed)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("call", [
    lambda: us.acoustic_layer_stack([("silicon", 0.0)]),
    lambda: us.acoustic_layer_stack([("silicon", -1e-6)]),
    lambda: us.acoustic_layer_stack([("silicon", float("nan"))]),
    lambda: us.acoustic_layer_stack([("silicon", 2.0)]),            # µm を m に渡し忘れ
    lambda: us.acoustic_layer_stack([("silicon", "1e-6")]),
    lambda: us.acoustic_layer_stack([("unobtainium", 1e-6)]),
    lambda: us.acoustic_layer_stack([({"rho": 0.0, "c": 1000.0}, 1e-6)]),
    lambda: us.acoustic_layer_stack([({"rho": 1000.0, "c": -5.0}, 1e-6)]),
    lambda: us.acoustic_layer_stack([({"rho": 1000.0, "c": 1000.0, "alpha0": -1.0}, 1e-6)]),
    lambda: us.acoustic_layer_stack([({"rho": float("inf"), "c": 1000.0}, 1e-6)]),
    lambda: us.acoustic_layer_stack([("silicon", 1e-6)], allow_unverified=1),
    lambda: us.acoustic_interface_coefficients({"a": 1}),
    lambda: us.pulse_echo_ascan(us.acoustic_layer_stack(), f0=0.0),
    lambda: us.pulse_echo_ascan(us.acoustic_layer_stack(), f0=-1e6),
    lambda: us.pulse_echo_ascan(us.acoustic_layer_stack(), f0=float("nan")),
    lambda: us.pulse_echo_ascan(us.acoustic_layer_stack(), f0=50e9),
    lambda: us.pulse_echo_ascan(us.acoustic_layer_stack(), water_path=0.0),
    lambda: us.pulse_echo_ascan(us.acoustic_layer_stack(), bandwidth=3.0),
    lambda: us.pulse_echo_ascan(us.acoustic_layer_stack(), rate=10e6),
    lambda: us.sam_cscan(np.zeros((4, 4)), {0: us.acoustic_layer_stack()}),           # float の地図
    lambda: us.sam_cscan(np.zeros((4, 4), int), {1: us.acoustic_layer_stack()}),      # ラベルに積層が無い
    lambda: us.sam_cscan(np.zeros((4, 4), int), {0: us.acoustic_layer_stack()}, pixel_size=0.0),
    lambda: us.sam_cscan(np.zeros((4, 4), int), {0: us.acoustic_layer_stack()}, noise_rms=-1.0),
    lambda: us.sam_cscan(np.zeros((4, 4), int), {0: us.acoustic_layer_stack()}, seed=1.5),
    lambda: us.sam_cscan(np.zeros((4, 4), int), {0: {"kind": "x"}}),
    lambda: us.echo_phase_polarity({"kind": "x"}),
    lambda: us.echo_phase_polarity(us.pulse_echo_ascan(us.acoustic_layer_stack()), interface=9),
    lambda: us.sam_frequency_tradeoff(us.acoustic_layer_stack(), 0.0),
    lambda: us.sam_frequency_tradeoff(us.acoustic_layer_stack(), 1e-5, f_min=1e9, f_max=1e8),
    lambda: us.sam_frequency_tradeoff(us.acoustic_layer_stack(), 1e-5, water_path=0.0),  # 損失なし
])
def test_bad_inputs_are_refused(call):
    with pytest.raises(ValueError):
        call()


def test_couplants_must_agree_across_classes():
    a = us.acoustic_layer_stack()
    b = us.acoustic_layer_stack(couplant={"rho": 1000.0, "c": 1500.0})
    m = np.zeros((4, 4), dtype=np.int64)
    m[0, 0] = 1
    with pytest.raises(ValueError, match="couplant"):
        us.sam_cscan(m, {0: a, 1: b})


# --------------------------------------------------------------------------- #
# 8. 台帳と公開経路
# --------------------------------------------------------------------------- #
def test_the_ledger_lists_every_op_and_nothing_is_missing():
    listed = set(opsacoustics.list_ops("ultrasonic"))
    assert listed == set(us.__all__), listed
    assert not opsacoustics.missing()
    for name in listed:
        assert opsacoustics.info(name)["module"] == "ultrasound"
        assert len(opsacoustics.info(name)["doc"]) >= 20
        assert "Raises" in (opsacoustics.get(name).__doc__ or ""), name


def test_every_op_is_reachable_from_the_public_tier():
    import fullseye as fs

    for name in us.__all__:
        assert hasattr(fs.ledger, name), name


def test_the_typed_catalog_declares_the_family():
    import typed_catalog as tc

    rows = {r[0]: r for r in tc.catalog() if r[0] in us.__all__}
    assert set(rows) == set(us.__all__)
    assert rows["sam_cscan"][2] == ["labels2d", "table"] and rows["sam_cscan"][3] == "table"


def test_the_fuzzer_builds_arguments_that_actually_compute():
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import chain_fuzz as cf

    for name in us.__all__:
        assert name in cf.OP_ARG_BUILDERS, name
        args, kw = cf.OP_ARG_BUILDERS[name](None, np.random.default_rng(0))
        out = opsacoustics.call(name, *args, **kw)
        assert cf.TYPE_CHECKS[opsacoustics.info(name)["out"]](out), name


def test_a_foreign_table_cannot_pose_as_a_stack_or_an_ascan():
    """Why no new sort: stacks, A-scans and C-scans travel as tables with a kind mark; every
    consumer refuses an unmarked table, so another family's table fails loudly."""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import chain_fuzz as cf

    pool_table = cf.make_generators()["table"](np.random.default_rng(0))
    for fn in (us.acoustic_interface_coefficients, us.pulse_echo_ascan, us.echo_phase_polarity,
               lambda t: us.sam_frequency_tradeoff(t, 1e-5)):
        with pytest.raises(ValueError):
            fn(pool_table)
    with pytest.raises(ValueError):
        us.sam_cscan(np.zeros((4, 4), dtype=np.int64), {0: pool_table})
