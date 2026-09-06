# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""roughness — 真値で検算するテスト。

方針:
  * **解析的に答えが分かる入力**(正弦波、既知の平面/二次曲面、PSD から作った
    高さ場)で当てる。「もっともらしい dict を返すだけの実装」は通らない。
  * 乱数だけの面に頼らない。``_structured()`` が **周期的な加工目 + 孤立した
    深い傷 4 本 + 傾き + うねり**を持つ面を作り、極値統計・ロバスト当てはめ・
    帯域分離の各テストがこれを踏む。ガウス乱数だけの面では Sz・Ssk・Sku・
    RANSAC の弱点がすべて隠れる。
  * fail-closed を「例外が出ること」だけでなく **文言**でも確かめる
    (黙って代用しないことがこの層の契約なので)。
"""
import math

import numpy as np
import pytest

import roughness as R

DX = 1.0
N = 256
LAM_C = 40.0
SEGS = ((150., 30., 215., 150.), (170., 170., 235., 230.),
        (195., 20., 200., 190.), (150., 215., 240., 200.))


# --------------------------------------------------------------------------- #
# 構造のある試験面(乱数だけの面では見えない欠陥を踏むため)                    #
# --------------------------------------------------------------------------- #
def _dist_seg(xx, yy, x0, y0, x1, y1):
    vx, vy = x1 - x0, y1 - y0
    t = np.clip(((xx - x0) * vx + (yy - y0) * vy) / (vx * vx + vy * vy), 0.0, 1.0)
    return np.hypot(xx - (x0 + t * vx), yy - (y0 + t * vy))


def _scratches(xx, yy, half_width=3.0, depth=3.0):
    """片側(x > 0.55 L)に寄せた孤立した深い傷 4 本。

    片側に寄せるのは **最小二乗平面が傷に引かれる**状況を作るため。
    中央に散らすと非対称が打ち消し合って、ロバスト当てはめの意味が消える。
    """
    s = np.zeros_like(xx)
    for seg in SEGS:
        s -= depth * np.exp(-0.5 * (_dist_seg(xx, yy, *seg) / half_width) ** 2)
    return s


def _structured(n=N, dx=DX, seed=20260906, scratch_hw=3.0):
    """加工目 + 傷 + PSD + うねり + 傾きの面。成分ごとに返す。"""
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64) * dx
    psd, _ = R.surface_synth_psd(n, dx, 0.8, 2.0 * dx, 32.0, 0.08, seed)
    lay = 0.25 * np.cos(2.0 * np.pi * yy / 16.0)          # 行方向に走る加工目
    scratch = _scratches(xx, yy, scratch_hw)
    wav = 0.60 * np.cos(2.0 * np.pi * xx / 128.0 + 0.7)   # 粗さではない
    tilt = 0.050 * xx - 0.025 * yy                        # 粗さではない
    return dict(xx=xx, yy=yy, psd=psd, lay=lay, scratch=scratch, wav=wav, tilt=tilt,
                rough=psd + lay + scratch, full=psd + lay + scratch + wav + tilt)


def _hp(z, dx=DX, lam=LAM_C):
    """端の扱いだけを固定した λc ハイパス(形を保つので比較が書きやすい)。"""
    return R.surface_filter(z, dx, lambda_c=lam, end_effect="mirror")[0]


def _sine(n, dx, lam, amp=1.0, axis=1):
    g = np.arange(n) * dx
    w = amp * np.cos(2.0 * np.pi * g / lam)
    return (w[None, :] * np.ones((n, 1))) if axis == 1 else (w[:, None] * np.ones((1, n)))


# --------------------------------------------------------------------------- #
# surface_synth_psd —— 真値の根拠そのもの                                      #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("n,hurst,lo,hi,sq,seed", [
    (128, 0.30, 4.0, 32.0, 0.5, 1),
    (256, 0.50, 4.0, 64.0, 0.08, 2),
    (256, 0.80, 2.0, 64.0, 0.08, 3),
    (128, 0.95, 8.0, 64.0, 2.0, 4),
    ((64, 128), 0.60, 4.0, 32.0, 0.3, 5),
])
def test_synth_psd_realisation_matches_analytic_sq(n, hurst, lo, hi, sq, seed):
    """実現の rms が解析 Sq と倍精度で一致する(位相に依存しない)。"""
    z, sq_analytic = R.surface_synth_psd(n, 1.0, hurst, lo, hi, sq, seed)
    assert sq_analytic == pytest.approx(sq, rel=0, abs=0)
    assert abs(float(z.std()) / sq_analytic - 1.0) < 1e-12
    assert abs(float(z.mean())) < 1e-12 * sq          # DC は帯域に無い


def test_synth_psd_sq_is_independent_of_seed():
    """種を振っても実現 rms が動かない = 真値が乱数に依存しない。"""
    vals = [R.surface_synth_psd(128, 1.0, 0.7, 4.0, 32.0, 0.5, s)[0].std()
            for s in range(6)]
    assert max(vals) - min(vals) < 1e-12


def test_synth_psd_is_a_surface_not_a_spike():
    """★PoC が踏んだバグの回帰テスト。

    位相を ``(u - u[-k])/2`` で反対称化すると位相が一様でなくなり、原点に
    1 本のスパイクが立つ(実測 PTV/rms 55.0、尖度 71.8)。**そのときも Sq は
    解析値と厳密に一致する**ので、分散だけ見ていたら気づけない。
    ここで尖度と PTV/rms を見るのは、その盲点を塞ぐため。
    """
    z, _ = R.surface_synth_psd(256, 1.0, 0.8, 2.0, 64.0, 0.08, 20260906)
    kurt = float(np.mean((z - z.mean()) ** 4) / z.std() ** 4)
    ptv_over_rms = float(np.ptp(z) / z.std())
    assert 2.3 < kurt < 3.7, f"尖度 {kurt:.2f} — 位相の引き方が壊れている"
    assert ptv_over_rms < 15.0, f"PTV/rms {ptv_over_rms:.1f} — スパイクが立っている"


def test_synth_psd_respects_the_band():
    """帯域の外にエネルギーが漏れていない。"""
    z, _ = R.surface_synth_psd(256, 1.0, 0.8, 4.0, 32.0, 1.0, 11)
    f = np.fft.fftfreq(256, 1.0)
    q = np.hypot(f[:, None], f[None, :])
    p = np.abs(np.fft.fft2(z)) ** 2
    outside = (q < 1.0 / 32.0 - 1e-12) | (q > 1.0 / 4.0 + 1e-12)
    assert float(p[outside].sum()) / float(p.sum()) < 1e-24


def test_synth_psd_hurst_changes_the_slope():
    """H を変えると PSD の傾きが -2(H+1) で動く(振幅則が効いている証拠)。"""
    slopes = []
    for h in (0.3, 0.8):
        z, _ = R.surface_synth_psd(256, 1.0, h, 2.0, 64.0, 0.08, 3)
        q, c = R.surface_psd(z, 1.0, kind="areal")
        sel = (q >= 2.0 / 64.0) & (q <= 0.4) & (c > 0)
        slopes.append(float(np.polyfit(np.log(q[sel]), np.log(c[sel]), 1)[0]))
    assert slopes[0] == pytest.approx(-2 * (0.3 + 1), abs=0.01)
    assert slopes[1] == pytest.approx(-2 * (0.8 + 1), abs=0.01)


@pytest.mark.parametrize("kw,msg", [
    (dict(n=4), "at least 8"),
    (dict(hurst=1.5), "hurst must be in"),
    (dict(lambda_lo=64.0, lambda_hi=8.0), "must be shorter than"),
    (dict(lambda_lo=1.0), "Nyquist"),
    (dict(lambda_hi=1e6), "exceeds the field extent"),
    (dict(sq=0.0), "sq must be a finite positive"),
    (dict(dx=-1.0), "dx must be a finite positive"),
])
def test_synth_psd_fails_closed(kw, msg):
    args = dict(n=64, dx=1.0, hurst=0.8, lambda_lo=4.0, lambda_hi=32.0, sq=1.0, seed=0)
    args.update(kw)
    with pytest.raises(ValueError, match=msg):
        R.surface_synth_psd(**args)


# --------------------------------------------------------------------------- #
# surface_params —— 解析的な真値で当てる                                        #
# --------------------------------------------------------------------------- #
def test_surface_params_on_a_sinusoid_matches_closed_form():
    """正弦波 A cos(2πx/λ) の Sa/Sq/Sp/Sv/Sz/Ssk/Sku は解析的に決まる。"""
    amp, lam = 1.7, 32.0
    z = _sine(256, 1.0, lam, amp)
    d = R.surface_params(z, 1.0)
    assert d["Sq"] == pytest.approx(amp / math.sqrt(2.0), rel=1e-12)
    assert d["Sa"] == pytest.approx(2.0 * amp / math.pi, rel=1e-12)
    assert d["Sp"] == pytest.approx(amp, rel=1e-12)
    assert d["Sv"] == pytest.approx(amp, rel=1e-12)
    assert d["Sz"] == pytest.approx(2.0 * amp, rel=1e-12)
    assert d["Ssk"] == pytest.approx(0.0, abs=1e-12)
    assert d["Sku"] == pytest.approx(1.5, rel=1e-12)       # 正弦の尖度は 3/2


def test_surface_params_sdq_matches_the_analytic_gradient():
    """Sdq = rms(|∇z|)。正弦なら (2πA/λ)/√2。中心差分の sinc バイアスも当てる。"""
    amp, lam = 1.0, 32.0
    analytic = (2.0 * math.pi * amp / lam) / math.sqrt(2.0)
    for dx in (0.5, 1.0, 4.0, 8.0):
        n = int(256 / dx)
        d = R.surface_params(_sine(n, dx, lam, amp), dx, assume_filtered=True)
        pred = analytic * float(np.sinc(2.0 * dx / lam))   # 中心差分の応答
        assert d["Sdq"] < analytic                         # 必ず過小
        assert d["Sdq"] == pytest.approx(pred, rel=0.01), f"dx={dx}"


def test_surface_params_sdr_matches_a_numerical_reference():
    """Sdr = mean(√(1+|∇z|²)) - 1。細かく標本化すれば解析値に一致する。"""
    lam, dx = 32.0, 0.25
    z = _sine(1024, dx, lam, 1.0)
    k = 2.0 * math.pi / lam
    t = np.linspace(0.0, lam, 200001)
    ref = float(np.mean(np.sqrt(1.0 + (k * np.sin(2 * np.pi * t / lam)) ** 2)) - 1.0)
    assert R.surface_params(z, dx)["Sdr"] == pytest.approx(ref, rel=2e-3)


def test_surface_params_sees_the_scratches_that_a_gaussian_field_hides():
    """★構造のある面。深い傷があると Ssk は強く負、Sku は 3 より遥かに大きい。

    ガウス乱数だけの面では Ssk≈0 / Sku≈3 になり、この 2 つは何も言わない指標に
    なってしまう —— 「乱数だけのテストデータは欠陥を隠す」の具体例。
    """
    C = _structured()
    d_scratch = R.surface_params(_hp(C["rough"]), DX)
    d_plain = R.surface_params(_hp(C["psd"] + C["lay"]), DX)
    assert d_scratch["Ssk"] < -1.0
    assert d_scratch["Sku"] > 8.0
    assert abs(d_plain["Ssk"]) < 0.5              # 傷を抜くと何も言わなくなる
    assert d_plain["Sku"] < 4.0
    assert d_scratch["Sv"] > 5.0 * d_scratch["Sp"]   # 谷だけが深い


def test_surface_params_rejects_an_unfiltered_field():
    """★ゼロ点。生の高さ場・平面だけ除いた面は拒否し、λc を掛けた面は通す。"""
    C = _structured()
    with pytest.raises(ValueError, match="does not look band-limited"):
        R.surface_params(C["full"], DX)
    plane_only, _ = R.surface_form_remove(C["full"], DX, order=1, method="ls")
    with pytest.raises(ValueError, match="does not look band-limited"):
        R.surface_params(plane_only, DX)
    d = R.surface_params(_hp(plane_only), DX)     # 正しい手順は通る
    assert d["assume_filtered"] is False
    assert d["band_long_wave_fraction"] < R._BAND_LONGWAVE_MAX


def test_surface_params_unfiltered_sq_is_wrong_by_an_order_of_magnitude():
    """拒否が過保護でないことの裏取り: 通してしまうと桁で間違う。"""
    C = _structured()
    truth = R.surface_params(_hp(C["rough"]), DX)
    raw = R.surface_params(C["full"], DX, assume_filtered=True)
    plane_only, _ = R.surface_form_remove(C["full"], DX, order=1, method="ls")
    only = R.surface_params(plane_only, DX, assume_filtered=True)
    assert raw["Sq"] > 10.0 * truth["Sq"]
    assert only["Sq"] > 1.5 * truth["Sq"]
    assert raw["Ssk"] > 0.0 > truth["Ssk"]        # 符号が反転する


def test_surface_params_assume_filtered_is_explicit_not_silent():
    C = _structured()
    d = R.surface_params(C["full"], DX, assume_filtered=True)
    assert d["assume_filtered"] is True
    assert d["band_long_wave_fraction"] > R._BAND_LONGWAVE_MAX   # 証拠は残る


def test_surface_params_correct_pipeline_recovers_the_truth():
    """★真値との突き合わせ。傾き + うねりを乗せた面から粗さを取り戻せるか。"""
    C = _structured()
    truth = R.surface_params(_hp(C["rough"]), DX)
    flat, _ = R.surface_form_remove(C["full"], DX, order=1, method="ls")
    got = R.surface_params(_hp(flat), DX)
    assert got["Sq"] == pytest.approx(truth["Sq"], rel=0.05)
    assert got["Sa"] == pytest.approx(truth["Sa"], rel=0.05)
    assert got["Sz"] == pytest.approx(truth["Sz"], rel=0.05)
    assert got["Ssk"] == pytest.approx(truth["Ssk"], rel=0.10)


def test_surface_params_sz_grows_with_the_evaluation_area():
    """★落とし穴 (a): Sz は「どれだけ長く見たか」を測る(単調増加、頭打ち無し)。"""
    C = _structured()
    fld = _hp(C["psd"] + C["lay"])                 # 傷を抜く(極値統計だけを見る)
    means = []
    for w in (32, 64, 128, 256):
        wins = [fld[i:i + w, j:j + w]
                for i in range(0, N - w + 1, w) for j in range(0, N - w + 1, w)]
        means.append(float(np.mean([np.ptp(v) for v in wins])))
    assert all(b > a for a, b in zip(means, means[1:])), means
    assert means[-1] / means[0] > 1.15
    # Sq は同じ掃引でほとんど動かない = 「Sz だけの性質」であることの対照
    sqs = []
    for w in (32, 256):
        wins = [fld[i:i + w, j:j + w]
                for i in range(0, N - w + 1, w) for j in range(0, N - w + 1, w)]
        sqs.append(float(np.mean([v.std() for v in wins])))
    assert abs(sqs[1] / sqs[0] - 1.0) < 0.5 * (means[-1] / means[0] - 1.0)


def test_surface_params_sq_is_the_most_sampling_robust():
    """★落とし穴 (b): 標本間隔に対して Sq > Sa > Sz の順に強い。

    「最も頑健なのは Sa」という直感が外れる —— エイリアシングはエネルギーを
    折り返すだけなので 2 次モーメント(Sq)は保たれる。
    """
    C = _structured()
    truth = R.surface_params(_hp(C["rough"]), DX)

    def measured(f):
        n = N // f
        yy, xx = np.mgrid[0:n, 0:n].astype(np.float64) * (DX * f)
        z = C["full"][::f, ::f] - (0.050 * xx - 0.025 * yy)
        return R.surface_params(_hp(z, DX * f), DX * f)

    e4, e8 = measured(4), measured(8)
    err = {k: abs(e8[k] / truth[k] - 1.0) for k in ("Sa", "Sq", "Sz")}
    assert err["Sq"] < err["Sa"] < err["Sz"], err
    assert err["Sq"] < 0.05
    assert err["Sz"] > 0.10                        # Sz が先に崖から落ちる
    assert abs(e4["Sq"] / truth["Sq"] - 1.0) < 0.05


@pytest.mark.parametrize("kw,msg", [
    (dict(z=np.zeros((4, 4))), "at least 8x8"),
    (dict(z=np.zeros(64)), "must be a 2-D height field"),
    (dict(z=np.full((16, 16), np.nan)), "NaN or Inf"),
    (dict(dx=0.0), "dx must be a finite positive"),
    (dict(dy=-2.0), "dy must be a finite positive"),
    (dict(z=np.zeros((16, 16))), "perfectly flat"),
])
def test_surface_params_fails_closed(kw, msg):
    args = dict(z=_sine(32, 1.0, 8.0), dx=1.0, dy=None, assume_filtered=True)
    args.update(kw)
    with pytest.raises(ValueError, match=msg):
        R.surface_params(**args)


# --------------------------------------------------------------------------- #
# surface_filter                                                               #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("lam_f", [16.0, 32.0, 64.0, 80.0, 128.0, 256.0])
def test_surface_filter_transmission_follows_iso(lam_f):
    """うねり側の振幅が ISO の透過率 exp(-π (α λc f)²) に載る。

    打ち切り ``±λc/2`` のぶん最大 +0.0096 ずれる(実測、λ=λc で最大)。
    """
    lam_c, dx = 80.0, 1.0
    n = int(lam_f) * max(2, int(math.ceil(640.0 / lam_f)))
    g = np.arange(n) * dx
    z = _sine(n, dx, lam_f)
    rough, wavy = R.surface_filter(z, dx, lambda_c=lam_c, end_effect="wrap")
    row = wavy[n // 2]
    amp = math.hypot(2 * float(np.mean(row * np.cos(2 * np.pi * g / lam_f))),
                     2 * float(np.mean(row * np.sin(2 * np.pi * g / lam_f))))
    iso = math.exp(-math.pi * (R.GAUSS_ALPHA * lam_c / lam_f) ** 2)
    assert abs(amp - iso) < 0.011
    assert np.allclose(rough + wavy, z, atol=1e-12)   # 分配は完全(消えも湧きもしない)


def test_surface_filter_halves_at_the_cutoff():
    """カットオフ波長ちょうどで透過率がほぼ 0.5(規格の定義そのもの)。"""
    lam = 64.0
    n = int(lam) * 10
    g = np.arange(n) * 1.0
    _, wavy = R.surface_filter(_sine(n, 1.0, lam), 1.0, lambda_c=lam, end_effect="wrap")
    row = wavy[n // 2]
    amp = math.hypot(2 * float(np.mean(row * np.cos(2 * np.pi * g / lam))),
                     2 * float(np.mean(row * np.sin(2 * np.pi * g / lam))))
    assert amp == pytest.approx(0.5, abs=0.012)


def test_surface_filter_reject_is_exact_where_it_returns_values():
    """★端の扱い。大きい面を切り出して真値を作り、3 つのやり方を比べる。

    reject は「返した所は厳密に正しい」。wrap は傾きが残っていると端で
    桁違いに壊れる。傾きを除けば wrap と mirror に差はほとんど無い。
    """
    nb, n, dx, lam_c = 352, 256, 1.0, 40.0
    m = int(math.ceil(0.5 * lam_c / dx))
    yy, xx = np.mgrid[0:nb, 0:nb].astype(np.float64) * dx
    big, _ = R.surface_synth_psd(nb, dx, 0.8, 2.0, 32.0, 0.08, 4242)
    big = big + 0.25 * np.cos(2 * np.pi * yy / 16.0) \
        + 0.60 * np.cos(2 * np.pi * xx / 128.0 + 0.7) + 0.050 * xx - 0.025 * yy
    o = (nb - n) // 2
    sl = (slice(o, o + n), slice(o, o + n))
    truth = R.surface_filter(big, dx, lambda_c=lam_c, end_effect="mirror")[0][sl]
    sub = big[sl]

    edge = np.ones((n, n), bool)
    edge[m:-m, m:-m] = False
    ref_edge = float(np.sqrt(np.mean(truth[edge] ** 2)))

    def edge_err(field):
        return float(np.sqrt(np.mean((field[edge] - truth[edge]) ** 2))) / ref_edge

    e_wrap = edge_err(R.surface_filter(sub, dx, lambda_c=lam_c, end_effect="wrap")[0])
    e_mirr = edge_err(R.surface_filter(sub, dx, lambda_c=lam_c, end_effect="mirror")[0])
    assert e_wrap > 5.0, e_wrap                     # 傾きつき wrap は桁で外す
    assert e_mirr < 0.5 * e_wrap

    flat = R.surface_form_remove(sub, dx, order=1, method="ls")[0]
    f_wrap = edge_err(R.surface_filter(flat, dx, lambda_c=lam_c, end_effect="wrap")[0])
    assert f_wrap < 0.15                            # 傾きを除けば wrap でも実用域

    rej = R.surface_filter(sub, dx, lambda_c=lam_c, end_effect="reject")[0]
    assert rej.shape == (n - 2 * m, n - 2 * m)
    assert np.allclose(rej, truth[m:-m, m:-m], atol=1e-12)   # 返した所は厳密


def test_surface_filter_lambda_s_removes_only_the_short_waves():
    """λs は短波長側だけを落とす(長波長側は素通し)。"""
    n, dx = 256, 1.0
    z = _sine(n, dx, 8.0, 1.0) + _sine(n, dx, 64.0, 1.0, axis=0)
    rough, _ = R.surface_filter(z, dx, lambda_c=128.0, lambda_s=16.0, end_effect="mirror")
    short = float(np.std(rough[n // 2, :]))         # λ=8 の成分が乗る行方向
    long_ = float(np.std(rough[:, n // 2]))         # λ=64 の成分が乗る列方向
    assert short < 0.1 * long_


@pytest.mark.parametrize("kw,msg", [
    (dict(kind="box"), "kind must be 'gaussian'"),
    (dict(end_effect="zero"), "end_effect must be one of"),
    (dict(lambda_c=None, lambda_s=None), "at least one of"),
    (dict(lambda_c=1.0), "Nyquist"),
    (dict(lambda_c=1e6), "exceeds the evaluation length"),
    (dict(lambda_c=16.0, lambda_s=32.0), "must be shorter than lambda_c"),
    (dict(lambda_c=200.0), "would discard the whole field"),
])
def test_surface_filter_fails_closed(kw, msg):
    args = dict(z=_sine(256, 1.0, 32.0), dx=1.0, lambda_c=40.0, end_effect="reject")
    args.update(kw)
    with pytest.raises(ValueError, match=msg):
        R.surface_filter(**args)


# --------------------------------------------------------------------------- #
# surface_form_remove                                                          #
# --------------------------------------------------------------------------- #
def test_form_remove_recovers_a_known_plane_exactly():
    n, dx = 64, 0.5
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64) * dx
    z = 3.0 + 0.07 * xx - 0.031 * yy
    resid, coef = R.surface_form_remove(z, dx, order=1, method="ls")
    assert np.abs(resid).max() < 1e-10
    assert coef[1] == pytest.approx(0.07, abs=1e-12)
    assert coef[2] == pytest.approx(-0.031, abs=1e-12)


def test_form_remove_recovers_a_known_quadric_exactly():
    n, dx = 64, 0.5
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64) * dx
    cx, cy = xx - xx.mean(), yy - yy.mean()
    z = 1.0 + 0.02 * cx - 0.01 * cy + 0.004 * cx ** 2 - 0.0015 * cx * cy + 0.003 * cy ** 2
    resid, coef = R.surface_form_remove(z, dx, order=2, method="ls")
    assert np.abs(resid).max() < 1e-9
    for got, want in zip(coef[1:], (0.02, -0.01, 0.004, -0.0015, 0.003)):
        assert got == pytest.approx(want, abs=1e-10)
    # 平面しか除かないと二次項が残る = order の効きの対照
    resid1, _ = R.surface_form_remove(z, dx, order=1, method="ls")
    assert np.abs(resid1).max() > 1e-3


def test_form_remove_ls_recovers_tilt_on_the_structured_surface():
    C = _structured()
    _, coef = R.surface_form_remove(C["psd"] + C["lay"] + C["tilt"], DX, 1, "ls")
    assert coef[1] == pytest.approx(0.050, abs=2e-4)
    assert coef[2] == pytest.approx(-0.025, abs=2e-4)


def test_form_remove_ransac_beats_ls_on_wide_outliers():
    """★ロバストが要るのは深い傷ではなく **広い** 外れ値。

    幅を変えて 2 点で測り、(1) 広いほど LS が悪化する (2) 中程度の面積比では
    RANSAC が勝つ、の両方を見る。細い傷では差が小さいことも同時に確かめる
    (「深い傷ならロバスト必須」という早合点への反例)。
    """
    def err(hw, method):
        C = _structured(scratch_hw=hw)
        truth = R.surface_params(C["rough"], DX, assume_filtered=True)["Sq"]
        resid, _ = R.surface_form_remove(C["rough"] + C["tilt"], DX, 1, method, seed=7)
        got = R.surface_params(resid, DX, assume_filtered=True)["Sq"]
        return got / truth - 1.0

    narrow_ls, narrow_rs = err(3.0, "ls"), err(3.0, "ransac")
    wide_ls, wide_rs = err(10.0, "ls"), err(10.0, "ransac")
    assert narrow_ls < 0.0 and wide_ls < 0.0            # 誤差は必ず過小側
    assert abs(wide_ls) > abs(narrow_ls)                # 広いほど LS が壊れる
    assert abs(wide_rs) < abs(wide_ls)                  # そこで RANSAC が勝つ
    assert abs(narrow_ls) < 0.05                        # 細い傷なら LS でも実用域


def test_form_remove_difference_vanishes_after_the_highpass():
    """★λc を後段に置くと LS と RANSAC の差は消える(順序で救える)。"""
    C = _structured(scratch_hw=10.0)
    truth = R.surface_params(_hp(C["rough"]), DX)["Sq"]
    out = {}
    for method in ("ls", "ransac"):
        resid, _ = R.surface_form_remove(C["rough"] + C["tilt"], DX, 1, method, seed=7)
        out[method] = R.surface_params(_hp(resid), DX)["Sq"] / truth - 1.0
    assert abs(out["ls"]) < 0.01 and abs(out["ransac"]) < 0.01
    assert abs(out["ls"] - out["ransac"]) < 0.005


def test_form_remove_ransac_is_deterministic_for_a_given_seed():
    C = _structured()
    a, ca = R.surface_form_remove(C["full"], DX, 1, "ransac", seed=3)
    b, cb = R.surface_form_remove(C["full"], DX, 1, "ransac", seed=3)
    assert np.array_equal(a, b) and np.array_equal(ca, cb)


@pytest.mark.parametrize("kw,msg", [
    (dict(order=3), "order must be 1"),
    (dict(method="huber"), "method must be"),
    (dict(method="ransac", thresh=-1.0), "thresh must be a finite positive"),
    (dict(dx=0.0), "dx must be a finite positive"),
])
def test_form_remove_fails_closed(kw, msg):
    args = dict(z=_sine(32, 1.0, 8.0), dx=1.0)
    args.update(kw)
    with pytest.raises(ValueError, match=msg):
        R.surface_form_remove(**args)


# --------------------------------------------------------------------------- #
# profile_params                                                               #
# --------------------------------------------------------------------------- #
def test_profile_params_on_a_sinusoid_matches_closed_form():
    amp, lam, n = 2.3, 32.0, 320
    p = amp * np.cos(2 * np.pi * np.arange(n) / lam)
    d = R.profile_params(p, 1.0, n_sampling=5)
    assert d["Rq"] == pytest.approx(amp / math.sqrt(2.0), rel=1e-12)
    assert d["Ra"] == pytest.approx(2.0 * amp / math.pi, rel=1e-12)
    assert d["Rt"] == pytest.approx(2.0 * amp, rel=1e-12)
    assert d["Rz"] == pytest.approx(2.0 * amp, rel=1e-12)   # 各区間に整数周期
    assert d["Rsk"] == pytest.approx(0.0, abs=1e-12)
    assert d["Rku"] == pytest.approx(1.5, rel=1e-12)
    assert d["sampling_length"] == pytest.approx(64.0)
    assert d["evaluation_length"] == pytest.approx(320.0)


def test_profile_params_rz_and_rt_differ_on_an_isolated_feature():
    """★Rz(5 区間平均)と Rt(全体)の定義差。孤立した傷があると開く。"""
    n = 500
    base = 0.2 * np.cos(2 * np.pi * np.arange(n) / 25.0)
    scratch = -3.0 * np.exp(-0.5 * ((np.arange(n) - 137.0) / 4.0) ** 2)
    d = R.profile_params(base + scratch, 1.0, n_sampling=5)
    d0 = R.profile_params(base, 1.0, n_sampling=5)
    assert d["Rt"] > 2.5 * d["Rz"], (d["Rt"], d["Rz"])
    assert d["Rz_max"] == pytest.approx(d["Rt"], rel=1e-12)   # 傷は 1 区間の中
    assert d0["Rt"] == pytest.approx(d0["Rz"], rel=1e-9)      # 傷が無ければ一致
    assert d["Rsk"] < -2.0                                    # 谷だけが深い


def test_profile_params_rz_depends_on_n_sampling():
    """n_sampling を変えると Rz が動く(= 条件を書かないと再現しない)。"""
    n = 480
    p = 0.2 * np.cos(2 * np.pi * np.arange(n) / 25.0) \
        - 3.0 * np.exp(-0.5 * ((np.arange(n) - 137.0) / 4.0) ** 2)
    rz = [R.profile_params(p, 1.0, k)["Rz"] for k in (1, 3, 5, 10)]
    assert rz[0] > rz[1] > rz[2] > rz[3]
    assert R.profile_params(p, 1.0, 1)["Rz"] == pytest.approx(
        R.profile_params(p, 1.0, 1)["Rt"], rel=1e-12)


def test_profile_params_is_anisotropic_on_a_lay_surface():
    """★加工目に直交する断面と平行な断面で Rq が大きく違う。"""
    C = _structured()
    fld = _hp(C["psd"] + C["lay"])            # 傷を抜く(向きの効果だけを見る)
    rows = [R.profile_params(fld[i, :], DX)["Rq"] for i in range(0, N, 8)]
    cols = [R.profile_params(fld[:, j], DX)["Rq"] for j in range(0, N, 8)]
    assert float(np.mean(cols)) > 1.5 * float(np.mean(rows))


def test_profile_params_single_section_rz_does_not_represent_the_area():
    """★断面 1 本の Rt は面の Sz を代表しない(本数と向きが要る)。"""
    C = _structured()
    fld = _hp(C["rough"])
    sz = R.surface_params(fld, DX)["Sz"]
    rt = np.array([R.profile_params(fld[i, :], DX)["Rt"] for i in range(0, N, 2)])
    assert rt.max() / rt.min() > 5.0                    # 同じ面の中で大きく振れる
    assert float((rt > 0.8 * sz).mean()) < 0.15         # Sz に届く断面はごく少数


@pytest.mark.parametrize("kw,msg", [
    (dict(p=np.zeros(4)), "at least 8 samples"),
    (dict(p=np.zeros((8, 8))), "must be a 1-D profile"),
    (dict(p=np.full(32, np.inf)), "NaN or Inf"),
    (dict(n_sampling=0), "n_sampling must be >= 1"),
    (dict(n_sampling=40), "samples per sampling length"),
    (dict(p=np.zeros(32)), "perfectly flat"),
    (dict(dx=0.0), "dx must be a finite positive"),
])
def test_profile_params_fails_closed(kw, msg):
    args = dict(p=np.cos(np.arange(64) / 3.0), dx=1.0, n_sampling=5)
    args.update(kw)
    with pytest.raises(ValueError, match=msg):
        R.profile_params(**args)


# --------------------------------------------------------------------------- #
# surface_psd                                                                  #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("hurst", [0.3, 0.5, 0.8, 0.95])
def test_surface_psd_recovers_the_planted_hurst(hurst):
    """★真値で検算。仕込んだ H が較正なしで戻り、2 規約の傾き差はちょうど 1。"""
    z, _ = R.surface_synth_psd(256, 1.0, hurst, 2.0, 64.0, 0.08, 11)
    got = {}
    for kind in ("areal", "radial"):
        q, c = R.surface_psd(z, 1.0, kind=kind)
        sel = (q >= 2.0 / 64.0) & (q <= 0.4) & (c > 0)
        got[kind] = float(np.polyfit(np.log(q[sel]), np.log(c[sel]), 1)[0])
    assert (-got["areal"] / 2.0 - 1.0) == pytest.approx(hurst, abs=0.01)
    assert ((-got["radial"] - 1.0) / 2.0) == pytest.approx(hurst, abs=0.01)
    assert got["areal"] - got["radial"] == pytest.approx(-1.0, abs=1e-3)


def test_surface_psd_normalisation_satisfies_parseval():
    """規約の要: 2 次元 PSD の総和が Sq² に厳密一致する。"""
    z, sq = R.surface_synth_psd(128, 0.5, 0.7, 2.0, 32.0, 0.37, 5)
    ny, nx = z.shape
    F = np.fft.fft2(z - z.mean())
    c2d = (0.5 * 0.5 / (ny * nx)) * np.abs(F) ** 2
    dq2 = (1.0 / (ny * 0.5)) * (1.0 / (nx * 0.5))
    assert float(c2d.sum()) * dq2 == pytest.approx(sq ** 2, rel=1e-12)


def test_surface_psd_radial_integral_recovers_sq_squared():
    """動径 PSD の積分も Sq² に戻る(環平均のぶん 1 % 程度は失う)。"""
    z, sq = R.surface_synth_psd(256, 1.0, 0.8, 2.0, 64.0, 0.08, 11)
    q, c = R.surface_psd(z, 1.0, kind="radial")
    integ = float(np.trapezoid(c, q)) if hasattr(np, "trapezoid") else float(np.trapz(c, q))
    assert integ == pytest.approx(sq ** 2, rel=0.02)


def test_surface_psd_excludes_dc_and_is_ordered():
    z, _ = R.surface_synth_psd(64, 1.0, 0.8, 4.0, 32.0, 1.0, 2)
    q, c = R.surface_psd(z + 1000.0, 1.0, kind="areal")   # 巨大な直流を足す
    assert q.min() > 0.0
    assert np.all(np.diff(q) > 0)
    assert len(q) == len(c)
    q2, c2 = R.surface_psd(z, 1.0, kind="areal")
    assert np.allclose(c, c2)                              # 直流は結果を汚さない


def test_surface_psd_scales_with_height_squared():
    z, _ = R.surface_synth_psd(64, 1.0, 0.8, 4.0, 32.0, 1.0, 2)
    _, c1 = R.surface_psd(z, 1.0, kind="areal")
    _, c3 = R.surface_psd(3.0 * z, 1.0, kind="areal")
    assert np.allclose(c3, 9.0 * c1, rtol=1e-12)


@pytest.mark.parametrize("kw,msg", [
    (dict(kind="1d"), "kind must be 'areal' or 'radial'"),
    (dict(dx=0.0), "dx must be a finite positive"),
    (dict(z=np.zeros((4, 4))), "at least 8x8"),
])
def test_surface_psd_fails_closed(kw, msg):
    args = dict(z=_sine(32, 1.0, 8.0), dx=1.0)
    args.update(kw)
    with pytest.raises(ValueError, match=msg):
        R.surface_psd(**args)


# --------------------------------------------------------------------------- #
# 端から端まで(合成 → 汚す → 復元 → 評価)                                     #
# --------------------------------------------------------------------------- #
def test_end_to_end_recovers_the_analytic_sq_of_a_pure_psd_surface():
    """★合成器の解析 Sq を、汚した面から手順どおりに取り戻せるか。

    帯域を PSD の帯域より上に取れば(λc > λ_hi)、λc ハイパスは PSD 成分を
    ほぼ素通しするので、**解析 Sq がそのまま真値になる**。
    """
    n, dx = 256, 1.0
    z, sq = R.surface_synth_psd(n, dx, 0.8, 2.0, 16.0, 0.5, 99)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64) * dx
    dirty = z + 0.9 * np.cos(2 * np.pi * xx / 128.0) + 0.08 * xx - 0.03 * yy
    flat, coef = R.surface_form_remove(dirty, dx, order=1, method="ls")
    rough, _ = R.surface_filter(flat, dx, lambda_c=64.0, end_effect="reject")
    got = R.surface_params(rough, dx)
    assert coef[1] == pytest.approx(0.08, abs=5e-4)
    assert got["Sq"] == pytest.approx(sq, rel=0.03)


def test_end_to_end_is_stable_across_hurst_and_size():
    """複数の H / 帯域 / 寸法で、真値と 3 % 以内に収まる。"""
    for n, hurst, lo, hi, sq in ((128, 0.4, 2.0, 8.0, 0.2),
                                 (192, 0.6, 2.0, 12.0, 1.0),
                                 (256, 0.9, 4.0, 16.0, 0.05)):
        z, _ = R.surface_synth_psd(n, 1.0, hurst, lo, hi, sq, 7)
        yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
        dirty = z + 0.5 * np.cos(2 * np.pi * xx / (n / 2.0)) + 0.02 * xx
        flat, _ = R.surface_form_remove(dirty, 1.0, order=1, method="ls")
        rough, _ = R.surface_filter(flat, 1.0, lambda_c=4.0 * hi, end_effect="reject")
        got = R.surface_params(rough, 1.0)["Sq"]
        assert got == pytest.approx(sq, rel=0.03), (n, hurst, got, sq)
