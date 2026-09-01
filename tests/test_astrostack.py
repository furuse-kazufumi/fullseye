# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""astrostack —— 閉じた形の正解、破綻点、そして fail-closed の契約。

天体写真スタッキングは、画像処理の中では珍しく**答えが数式で書ける**。だから
この試験は「前回の出力と同じか」ではなく**恒等式**を軸に組んである:

  * **drizzle は総フラックスを保存する。** 入力画素をしずくとして面積比で撒く
    以上、しずくが出力格子の内側にある限り総和は変わらない —— 「ほぼ保存」では
    なく float64 の丸め(1e-15)まで。倍率と ``pixfrac`` を振っても変わらない。
  * **κ-σ 合成の破綻点は中央値と同じ 50 %。** 45 % までは誤差 0.01 台、
    50 % で汚染量の半分、55 % 以上で汚染量そのものになる。**この「壊れる側」も
    そのまま試験に残してある** —— 隠すと、後で誰かがこれを「直せる不具合」と
    誤解して、直らないものを直そうとする。理論の限界は理論として固定する。
  * **既知フラックスの測光。** ``erf`` による画素の厳密積分で描いた星は総和が
    入力フラックスに一致し(1.8e-16)、広い開口ならそれをそのまま測り返す
    (-0.0000 %)。小さい開口の負のずれは**画素化に由来する系統誤差**なので、
    「小さい」ではなく ``sigma`` の 2 乗に反比例して減ることまで固定する。

乱数を使う検査はすべて seed を固定し、**何枚・何画素で・どの分布の統計量に
どれだけの許容を置いたか**をコメントに書く。導出の無い許容値は願望であって
試験ではない。

物理に尺度があるところ(FWHM、フラックス、倍率、汚染率、露出枚数)は必ず
**2 つ以上の値**で確かめるので、単位の取り違えが 1 つの幸運な定数の陰に
隠れられない。

末尾のクラスは 2026-09-02 の実測で見つかった 4 件の不具合を、それを暴いた
最小再現とともに固定してある。
"""
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import astrostack as A          # noqa: E402
import opsastrostack            # noqa: E402


def _flat_frames(n, contaminated, offset=500.0, shape=(24, 24), value=100.0,
                 sigma=2.0, seed=4242):
    """真値 *value* の平坦場を *n* 枚。先頭 *contaminated* 枚に +*offset*。

    汚染は**全画素いっせい**に乗せる(画素ごとの汚染率を制御したいのではなく、
    「フレームの何割が汚れているか」だけを動かしたいので)。
    """
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        img = np.full(shape, value) + rng.normal(0.0, sigma, shape)
        if i < contaminated:
            img = img + offset
        out.append(img)
    return out


def _one_star(sigma_px, flux=10000.0, size=96, margin=40.0, seed=11):
    """ノイズも空も無い、既知フラックスの 1 星フレームと、その中心。"""
    frame, truth = A.synth_starfield(
        shape=(size, size), n_stars=1, flux_min=flux, flux_max=flux,
        fwhm_px=sigma_px * A.FWHM_PER_SIGMA, sky=0.0, read_sigma=0.0,
        noise=False, seed=seed, margin_px=margin)
    return frame, truth, np.array([[truth["rows"][0], truth["cols"][0]]])


# ===========================================================================
# 検算 1 —— 面積(総フラックス)の保存
# ===========================================================================
class TestFluxConservation:
    """「drizzle は面積を保存する」を、丸め誤差の桁で固定する。"""

    def test_synthetic_star_total_equals_the_requested_flux(self):
        """``erf`` の画素積分は近似ではない。1 星の総和 = 与えたフラックス。

        画像を星の 26 sigma 四方まで広げてあるので、外へ出た分は倍精度の
        表現限界より小さい(erf の裾は 8 sigma で既に 1e-15 を切る)。
        """
        for sigma in (1.0, 1.5, 3.0):        # 尺度を 3 つ = 単位の取り違え検出
            frame, truth, _ = _one_star(sigma)
            got, want = float(frame.sum()), float(truth["fluxes"][0])
            assert abs(got - want) / want < 1e-12, (sigma, got, want)

    def test_drizzle_conserves_total_flux_exactly(self):
        """しずくが格子の内側にあれば ``sci.sum()`` = 入力総和の平均。

        ディザ 0 なので縁からはみ出すしずくが無く、保存は**厳密**になる。
        許容 1e-12 は float64 の丸めの積み上がり(48x48x6 = 13824 回の加算で
        相対 1e-16 * sqrt(13824) ~ 1e-14)に 2 桁の余裕を取ったもの。
        """
        frames, _ = A.synth_frame_series(shape=(48, 48), n_frames=6,
                                         dither_px=0.0, n_stars=8, sky=40.0,
                                         read_sigma=4.0, seed=5)
        want = float(np.mean([f.sum() for f in frames]))
        for pixfrac in (1.0, 0.7, 0.4):      # しずくの大きさ 3 通り
            for scale in (1.0, 2.0, 3.0):    # 倍率 3 通り
                sci, wht = A.drizzle_resample(frames, scale=scale,
                                              pixfrac=pixfrac)
                assert sci.shape == (int(48 * scale), int(48 * scale))
                rel = abs(float(sci.sum()) - want) / want
                assert rel < 1e-12, (pixfrac, scale, rel)

    def test_drizzle_weight_map_is_exactly_one_when_drops_tile_the_grid(self):
        """``pixfrac=1``・ディザ 0 なら被覆はどこでも厳密に 1。

        しずくが入力画素そのものになり、入力画素は出力格子を隙間なく覆うので、
        重みマップは定数 1 でなければならない。ここがずれるのは座標系の
        半画素ずれ(``[i-0.5, i+0.5]`` の規約破り)の最も早い兆候。
        """
        frames, _ = A.synth_frame_series(shape=(32, 32), n_frames=4,
                                         dither_px=0.0, n_stars=5, seed=2)
        for scale in (1.0, 2.0, 4.0):
            _, wht = A.drizzle_resample(frames, scale=scale, pixfrac=1.0)
            assert np.allclose(wht, 1.0, atol=1e-12), (scale, wht.min(), wht.max())

    def test_drizzle_weight_scales_with_pixfrac_squared(self):
        """被覆は ``pixfrac^2`` に比例する(しずくの面積そのもの)。"""
        frames, _ = A.synth_frame_series(shape=(32, 32), n_frames=3,
                                         dither_px=0.0, n_stars=4, seed=3)
        for pf in (0.8, 0.5, 0.25):
            _, wht = A.drizzle_resample(frames, scale=2.0, pixfrac=pf)
            # scale=2 なら 1 出力画素に入るしずくは 1 枚ぶんの 1/4 面積 x 4
            assert np.allclose(wht, pf * pf, atol=1e-12), (pf, wht.mean())

    def test_dithered_drizzle_only_loses_flux_at_the_border(self):
        """ディザを入れると縁でしずくが外へ出る。失う量は縁の幅で説明できる。

        48x48 に最大 1.5 px のディザなので、失うのは高々
        ``1 - ((48-1.5)/48)^2 = 6.2 %``。実測は 1.463 % で、その内側に収まる。
        **「保存が破れた」のではなく「格子の外に出た」**ことを、上限で言う。
        """
        frames, truth = A.synth_frame_series(shape=(48, 48), n_frames=6,
                                             dither_px=1.5, n_stars=8,
                                             sky=40.0, read_sigma=4.0, seed=5)
        sci, _ = A.drizzle_resample(frames, shifts=truth["shifts"], scale=2.0,
                                    pixfrac=0.7)
        want = float(np.mean([f.sum() for f in frames]))
        loss = (want - float(sci.sum())) / want
        assert 0.0 <= loss < 0.062, loss
        assert loss == pytest.approx(0.01594, abs=2e-4)     # 実測を固定

    def test_drizzle_refuses_a_shift_table_of_the_wrong_shape(self):
        frames, _ = A.synth_frame_series(shape=(24, 24), n_frames=3,
                                         n_stars=3, seed=1)
        with pytest.raises(ValueError, match=r"shifts must be \(N, 2\)"):
            A.drizzle_resample(frames, shifts=np.zeros((2, 2)))
        with pytest.raises(ValueError, match="non-finite"):
            A.drizzle_resample(frames, shifts=np.full((3, 2), np.nan))


# ===========================================================================
# 検算 2 —— κ-σ 合成の破綻点は 50 %
# ===========================================================================
class TestSigmaClipBreakdown:
    """**理論の限界であって不具合ではない**ので、壊れる側もそのまま固定する。"""

    #: 汚染率 → κ-σ(mad)合成の真値からのずれ(実測、20 枚 / +500 / seed 4242)
    MEASURED = {0.00: -0.0016, 0.10: -0.0166, 0.20: -0.0187, 0.30: -0.0141,
                0.40: +0.0019, 0.45: +0.0071, 0.50: +249.9975,
                0.55: +499.9663, 0.60: +499.9686}

    def test_below_fifty_percent_the_answer_is_right(self):
        """汚染 45 % までは、汚染が 0 のときと同じ精度で真値を返す。

        許容 0.05 は、20 枚 x 576 画素の平均の標準誤差
        ``2.0 / sqrt(20*576) = 0.019`` の 2.6 倍(クリップで実効枚数が減る分)。
        """
        for c in (0.0, 0.10, 0.20, 0.30, 0.40, 0.45):
            k = int(round(c * 20))
            stack, acc = A.sigma_clip_stack(_flat_frames(20, k), kappa=3.0,
                                            iters=5, scale="mad")
            err = float(stack.mean()) - 100.0
            assert abs(err) < 0.05, (c, err)
            assert err == pytest.approx(self.MEASURED[c], abs=0.01)
            # 落とした割合は汚染率とほぼ一致する(落とすべきものを落としている)
            rejected = 1.0 - float(acc.mean())
            assert abs(rejected - c) < 0.03, (c, rejected)

    def test_at_and_above_fifty_percent_it_breaks_and_we_say_so(self):
        """**BREAKS BY THEORY**: 汚染が半数に達すると答えは壊れる。

        中央値を中心に使う以上、これは中央値の破綻点そのもの。壊れ方も
        決まっている —— ちょうど 50 % では中央値が 2 つの母集団の中点に乗るので
        誤差は汚染量の**半分**(+250)、それを超えると中央値が汚染側に乗るので
        誤差は汚染量**そのもの**(+500)になる。
        """
        stack, _ = A.sigma_clip_stack(_flat_frames(20, 10), kappa=3.0, iters=5,
                                      scale="mad")
        assert float(stack.mean()) - 100.0 == pytest.approx(250.0, abs=0.5)
        for c in (0.55, 0.60):
            k = int(round(c * 20))
            stack, _ = A.sigma_clip_stack(_flat_frames(20, k), kappa=3.0,
                                          iters=5, scale="mad")
            assert float(stack.mean()) - 100.0 == pytest.approx(500.0, abs=0.5)

    def test_the_plain_median_has_the_same_breakdown_point(self):
        """破綻点が実装ではなく**中央値**のものであることを、中央値自身で示す。"""
        assert float(A.sigma_clip_stack(_flat_frames(20, 9),
                                        mode="median")[0].mean()) \
            == pytest.approx(102.65, abs=0.5)
        assert float(A.sigma_clip_stack(_flat_frames(20, 11),
                                        mode="median")[0].mean()) \
            == pytest.approx(597.4, abs=1.0)

    def test_a_non_robust_scale_breaks_five_times_earlier(self):
        """``scale="std"`` は 20 % で既に**何も落とさない**(= 単純平均と同じ)。

        外れ値を見つけるための尺度を、その外れ値自身が膨らませるため。
        既定を ``"mad"`` にしてある理由がこれで、既定を選び直したくなった人が
        まずここを読むように試験として残す。
        """
        frames = _flat_frames(20, 4)                 # 20 % 汚染
        std_stack, std_acc = A.sigma_clip_stack(frames, scale="std", kappa=3.0)
        mad_stack, mad_acc = A.sigma_clip_stack(frames, scale="mad", kappa=3.0)
        mean_stack, _ = A.sigma_clip_stack(frames, mode="mean")
        assert float(1.0 - std_acc.mean()) == pytest.approx(0.0, abs=1e-9)
        assert np.allclose(std_stack, mean_stack)    # 文字どおり単純平均
        assert float(std_stack.mean()) - 100.0 == pytest.approx(100.0, abs=0.1)
        assert float(1.0 - mad_acc.mean()) == pytest.approx(0.20, abs=0.03)
        assert abs(float(mad_stack.mean()) - 100.0) < 0.05

    def test_mean_is_wrecked_by_a_single_contaminated_frame(self):
        """比較対象: 単純平均は 1 枚でも汚れれば汚染量 / N だけ必ずずれる。"""
        for k in (1, 2, 4):
            stack, _ = A.sigma_clip_stack(_flat_frames(20, k), mode="mean")
            assert float(stack.mean()) - 100.0 == pytest.approx(500.0 * k / 20,
                                                                abs=0.05)

    def test_clipping_never_empties_a_pixel(self):
        """全フレームが落ちる画素を作らない(答えが nan にならない)。

        極端な κ で全部を落としにいっても、最も中心に近い 1 枚は残す。
        """
        stack, acc = A.sigma_clip_stack(_flat_frames(9, 0), kappa=1e-9, iters=3)
        assert np.isfinite(stack).all()
        assert (acc.sum(axis=0) >= 1).all()


# ===========================================================================
# 検算 3 —— 既知フラックスの測光
# ===========================================================================
class TestKnownFluxPhotometry:

    def test_a_wide_aperture_returns_the_known_flux_exactly(self):
        """``r = 8 sigma`` の開口は、与えたフラックスをそのまま測り返す。

        8 sigma の外に残るのは ``exp(-32) = 1.3e-14`` なので、閉形式の
        ``1 - exp(-r^2/2sigma^2)`` は 1 と区別できない。4 つの尺度で確認する。
        """
        for sigma in (1.0, 1.5, 2.0, 3.0):
            frame, truth, ctr = _one_star(sigma, size=96, margin=40.0)
            r = 8.0 * sigma
            phot = A.aperture_photometry(frame, ctr, r_aperture=r,
                                         r_inner=r + 4, r_outer=r + 10)[0]
            assert phot["flux"] == pytest.approx(10000.0, rel=1e-9), sigma

    def test_a_three_sigma_aperture_matches_the_closed_form(self):
        """``r = 3 sigma`` で閉形式 0.98889 に当たる(標本化の分だけ下に)。"""
        for sigma in (1.5, 2.0, 3.0):
            frame, truth, ctr = _one_star(sigma)
            r = 3.0 * sigma
            phot = A.aperture_photometry(frame, ctr, r_aperture=r,
                                         r_inner=r + 4, r_outer=r + 10)[0]
            theory = 10000.0 * (1.0 - np.exp(-r * r / (2.0 * sigma ** 2)))
            assert theory == pytest.approx(9888.910, abs=1e-3)
            assert phot["flux"] == pytest.approx(theory, rel=0.005), sigma

    def test_the_small_aperture_bias_is_pixelation_and_shrinks_as_1_over_sigma2(self):
        """**バグではなく画素化**: ずれは常に負で、``sigma^2`` で消えていく。

        開口の縁の画素を「画素平均 x 面積比」で代表すると、内側ほど明るい
        ガウシアンでは必ず少なく出る。その大きさが標本化とともに 2 次で
        減ることを 4 点で確かめる —— 単なる「小さい」ではなく**由来が言える**
        誤差であることの証拠。
        """
        errs = {}
        for sigma in (1.0, 1.5, 2.0, 3.0):
            frame, _, ctr = _one_star(sigma)
            r = 3.0 * sigma
            phot = A.aperture_photometry(frame, ctr, r_aperture=r,
                                         r_inner=r + 4, r_outer=r + 10)[0]
            theory = 10000.0 * (1.0 - np.exp(-r * r / (2.0 * sigma ** 2)))
            errs[sigma] = (phot["flux"] - theory) / theory
        for sigma, e in errs.items():
            assert e < 0.0, (sigma, e)               # 必ず負(過小評価)
        assert errs[1.0] == pytest.approx(-0.00914, abs=5e-4)
        assert errs[3.0] == pytest.approx(-0.00092, abs=5e-5)
        # sigma を 3 倍 = 標本化 3 倍で、誤差は ~9 倍小さくなる(2 次)
        ratio = errs[1.0] / errs[3.0]
        assert 7.0 < ratio < 13.0, ratio

    def test_the_aperture_area_matches_pi_r_squared(self):
        """円形開口の実効画素数は ``pi r^2``(副画素標本化の離散化のみ)。"""
        frame, _, ctr = _one_star(1.5)
        for r in (3.0, 4.5, 7.0):
            phot = A.aperture_photometry(frame, ctr, r_aperture=r,
                                         r_inner=r + 4, r_outer=r + 10)[0]
            assert phot["area_px"] == pytest.approx(np.pi * r * r, rel=3e-3), r

    def test_the_annulus_removes_a_known_sky_level(self):
        """既知の空を足しても、環状背景がそれを引き戻す。"""
        frame, truth, ctr = _one_star(1.5)
        for sky in (0.0, 250.0, 1000.0):
            phot = A.aperture_photometry(frame + sky, ctr, r_aperture=12.0,
                                         r_inner=16.0, r_outer=24.0)[0]
            assert phot["background"] == pytest.approx(sky, abs=1e-9), sky
            assert phot["flux"] == pytest.approx(10000.0, rel=1e-6), sky

    def test_the_ccd_equation_reduces_to_pure_poisson(self):
        """``read_sigma=0``・``gain=1`` なら S/N は ``F / sqrt(F + A*B)``。"""
        frame, _, ctr = _one_star(1.5)
        phot = A.aperture_photometry(frame + 100.0, ctr, r_aperture=6.0,
                                     r_inner=10.0, r_outer=16.0)[0]
        want = phot["flux"] / np.sqrt(phot["flux"]
                                      + phot["area_px"] * phot["background"])
        assert phot["snr"] == pytest.approx(want, rel=1e-12)

    def test_photometry_refuses_radii_in_the_wrong_order(self):
        frame, _, ctr = _one_star(1.5)
        with pytest.raises(ValueError, match="radii must satisfy"):
            A.aperture_photometry(frame, ctr, r_aperture=9.0, r_inner=5.0,
                                  r_outer=12.0)
        with pytest.raises(ValueError, match="radii must satisfy"):
            A.aperture_photometry(frame, ctr, r_aperture=4.0, r_inner=12.0,
                                  r_outer=8.0)


# ===========================================================================
# ノイズと sqrt(N)
# ===========================================================================
class TestNoise:

    def test_stacking_n_frames_divides_the_noise_by_sqrt_n(self):
        """真値が分かっているので、雑音は残差 RMS で**直接**測れる。

        32 枚まで倍々で確かめる。許容 3 % は 64x64 = 4096 画素の RMS 推定の
        標準誤差 ``1/sqrt(2*4096) = 1.1 %`` の 2.7 倍。
        """
        frames, truth = A.synth_frame_series(shape=(64, 64), n_frames=32,
                                             dither_px=0.0, n_stars=10,
                                             sky=200.0, read_sigma=8.0, seed=7)
        ideal = truth["noiseless"]
        base = float(np.sqrt(np.mean((frames[0] - ideal) ** 2)))
        # 1 枚の残差は sqrt(sky + read^2) = sqrt(200 + 64) でなければならない
        assert base == pytest.approx(np.sqrt(264.0), rel=0.02)
        for n in (2, 4, 8, 16, 32):
            stack, _ = A.sigma_clip_stack(frames[:n], mode="mean")
            rms = float(np.sqrt(np.mean((stack - ideal) ** 2)))
            assert base / rms == pytest.approx(np.sqrt(n), rel=0.03), n

    def test_the_median_is_noisier_than_the_mean_by_sqrt_pi_over_two(self):
        """中央値合成の代償を数字で: 正規分布なら ``sqrt(pi/2) = 1.2533`` 倍。

        大標本の漸近値なので 25 枚で確かめ、許容は 5 %。
        """
        frames, truth = A.synth_frame_series(shape=(64, 64), n_frames=25,
                                             dither_px=0.0, n_stars=6,
                                             sky=400.0, read_sigma=0.0, seed=17)
        ideal = truth["noiseless"]
        mean, _ = A.sigma_clip_stack(frames, mode="mean")
        med, _ = A.sigma_clip_stack(frames, mode="median")
        r_mean = float(np.sqrt(np.mean((mean - ideal) ** 2)))
        r_med = float(np.sqrt(np.mean((med - ideal) ** 2)))
        assert r_med / r_mean == pytest.approx(np.sqrt(np.pi / 2), rel=0.05)

    def test_a_robust_sigma_is_not_fooled_by_the_stars_but_std_is(self):
        """星は上側だけの外れ値。``np.std`` は桁で外し、MAD は 2 割で収まる。"""
        frame, _ = A.synth_starfield(shape=(128, 128), n_stars=40, sky=100.0,
                                     read_sigma=6.0, flux_min=3000.0,
                                     flux_max=40000.0, seed=9)
        true_sigma = np.sqrt(100.0 + 36.0)
        assert float(np.std(frame)) / true_sigma > 10.0        # 実測 15.0 倍
        assert A.noise_sigma(frame) / true_sigma == pytest.approx(1.184, abs=0.02)
        assert A.noise_sigma(frame, "clip") / true_sigma == pytest.approx(
            1.059, abs=0.02)

    def test_a_robust_sigma_is_accurate_on_an_empty_field(self):
        """星がまばら(0 個)なら MAD は 1 % 台で当たる —— 上のずれは星の裾。"""
        frame, _ = A.synth_starfield(shape=(128, 128), n_stars=0, sky=100.0,
                                     read_sigma=6.0, seed=9)
        assert A.noise_sigma(frame) == pytest.approx(np.sqrt(136.0), rel=0.02)

    def test_noise_sigma_refuses_an_unknown_method(self):
        with pytest.raises(ValueError, match="method must be one of"):
            A.noise_sigma(np.zeros((8, 8)), method="stddev")


# ===========================================================================
# 星の検出・PSF
# ===========================================================================
class TestStarsAndPsf:

    def test_star_detect_finds_the_planted_stars_at_the_planted_places(self):
        """既知の 15 星を、副画素 0.1 px 以内で拾う(明るい星だけを見る)。"""
        frame, truth = A.synth_starfield(shape=(128, 128), n_stars=15,
                                         flux_min=20000.0, flux_max=40000.0,
                                         sky=60.0, read_sigma=5.0, seed=23,
                                         margin_px=10.0)
        found = A.star_detect(frame, threshold_sigma=5.0)
        assert found.shape[0] == 15
        for r, c in zip(truth["rows"], truth["cols"]):
            d = np.hypot(found[:, 0] - r, found[:, 1] - c)
            assert d.min() < 0.1, (r, c, d.min())

    def test_star_detect_returns_an_empty_keypoint_array_on_an_empty_field(self):
        """星が無い視野は正当な入力。空を返すのであって例外にはしない。"""
        frame, _ = A.synth_starfield(shape=(64, 64), n_stars=0, sky=100.0,
                                     read_sigma=5.0, seed=1)
        got = A.star_detect(frame, threshold_sigma=8.0)
        assert got.shape == (0, 2) and got.dtype == np.float64

    def test_star_detect_on_a_perfectly_flat_image_finds_nothing(self):
        """雑音が 0 ならしきい値が定義できない。全画素を星にしない。"""
        assert A.star_detect(np.full((32, 32), 7.0)).shape == (0, 2)

    def test_psf_fit_recovers_the_planted_fwhm_plus_the_pixel_box(self):
        """当てはめは真の FWHM ではなく **``sqrt(sigma^2 + 1/12)``** を返す。

        画素は連続分布を幅 1 の箱で積分した値で、一様な箱の分散は ``1/12``。
        だから連続ガウシアンを当てると必ずその分だけ太い。これは推定の誤差
        ではなく**画像がそうできている**ので、閉形式の予測ごと固定する ——
        「1 % 以内で当たる」と書いて 3.7 % ずれるのを許容値で飲み込むと、
        本当の由来が誰にも分からなくなる。3 つの尺度で確かめるので、
        ``1/12`` が偶然合っているだけ、ということも起こらない。
        """
        for fwhm in (2.5, 3.5, 5.0):
            frame, truth = A.synth_starfield(
                shape=(96, 96), n_stars=6, fwhm_px=fwhm, flux_min=40000.0,
                flux_max=60000.0, sky=50.0, read_sigma=4.0, seed=29,
                margin_px=16.0)
            fits = A.psf_fit(frame, A.star_detect(frame), box=15)
            got = np.median([f["fwhm_px"] for f in fits])
            sigma = fwhm / A.FWHM_PER_SIGMA
            predicted = A.FWHM_PER_SIGMA * np.sqrt(sigma ** 2 + 1.0 / 12.0)
            assert got == pytest.approx(predicted, rel=0.01), (fwhm, got,
                                                               predicted)
            # 箱を外せば真の値に戻る(補正が本当に 1/12 であることの裏取り)
            corrected = A.FWHM_PER_SIGMA * np.sqrt(
                (got / A.FWHM_PER_SIGMA) ** 2 - 1.0 / 12.0)
            assert corrected == pytest.approx(fwhm, rel=0.012), (fwhm, corrected)

    def test_psf_fit_recovers_a_moffat_profile_with_its_own_model(self):
        """Moffat で撒いた星は Moffat で当てる(FWHM は 3 % 以内)。"""
        frame, truth = A.synth_starfield(
            shape=(96, 96), n_stars=5, psf="moffat", moffat_beta=2.5,
            fwhm_px=3.5, flux_min=60000.0, flux_max=80000.0, sky=50.0,
            read_sigma=4.0, seed=31, margin_px=16.0)
        fits = A.psf_fit(frame, A.star_detect(frame), model="moffat", box=17)
        got = np.median([f["fwhm_px"] for f in fits])
        assert got == pytest.approx(3.5, rel=0.03), got

    def test_psf_fit_reports_roundness_near_one_for_a_circular_star(self):
        frame, _ = A.synth_starfield(shape=(96, 96), n_stars=6, fwhm_px=3.5,
                                     flux_min=40000.0, flux_max=60000.0,
                                     sky=50.0, read_sigma=4.0, seed=29,
                                     margin_px=16.0)
        fits = A.psf_fit(frame, A.star_detect(frame), box=15)
        assert np.median([f["roundness"] for f in fits]) > 0.93

    def test_psf_fit_keeps_the_stars_it_could_not_fit(self):
        """窓がはみ出す星も**落とさず** ``converged=False`` で返す。

        黙って消すと「星が減った」ことに誰も気づけない。
        """
        frame, _ = A.synth_starfield(shape=(64, 64), n_stars=3, seed=2)
        fits = A.psf_fit(frame, np.array([[1.0, 1.0]]), box=15)
        assert len(fits) == 1
        assert fits[0]["converged"] is False
        assert "box falls outside" in fits[0]["reason"]

    def test_psf_fit_refuses_an_even_box(self):
        frame, _, ctr = _one_star(1.5)
        with pytest.raises(ValueError, match="box must be odd"):
            A.psf_fit(frame, ctr, box=10)


# ===========================================================================
# lucky imaging の選別
# ===========================================================================
class TestLuckySelect:

    def test_the_score_falls_as_the_seeing_gets_worse(self):
        """点は FWHM と強く逆相関する(実測 -0.925)。"""
        frames, truth = A.synth_frame_series(
            shape=(96, 96), n_frames=12, dither_px=0.0, n_stars=20,
            fwhm_px=3.2, fwhm_jitter=0.9, sky=60.0, read_sigma=5.0, seed=21,
            flux_min=3000.0, flux_max=9000.0)
        _, scores = A.lucky_select(frames, keep_fraction=0.25)
        corr = float(np.corrcoef(truth["fwhms"], scores)[0, 1])
        assert corr < -0.85, corr

    def test_keeping_the_best_quarter_sharpens_the_stack(self):
        """上位 25 % を採ると、全部平均より合成後の FWHM が 1 割以上良くなる。

        枚数は 1/4 なので雑音は 2 倍になる —— **鋭さと雑音の取引**であって
        ただの改善ではない、というのが lucky imaging の正体。
        """
        frames, _ = A.synth_frame_series(
            shape=(96, 96), n_frames=12, dither_px=0.0, n_stars=20,
            fwhm_px=3.2, fwhm_jitter=0.9, sky=60.0, read_sigma=5.0, seed=21,
            flux_min=3000.0, flux_max=9000.0)
        idx, _ = A.lucky_select(frames, keep_fraction=0.25)
        assert len(idx) == 3
        lucky, _ = A.sigma_clip_stack([frames[i] for i in idx], mode="mean")
        every, _ = A.sigma_clip_stack(frames, mode="mean")
        f_lucky = A.frame_quality(lucky)["fwhm_px"]
        f_every = A.frame_quality(every)["fwhm_px"]
        assert f_lucky < f_every
        assert 1.0 - f_lucky / f_every == pytest.approx(0.166, abs=0.05)

    def test_selection_never_returns_an_empty_set(self):
        frames, _ = A.synth_frame_series(shape=(48, 48), n_frames=5,
                                         n_stars=6, seed=4)
        idx, scores = A.lucky_select(frames, keep_fraction=1e-6)
        assert len(idx) == 1 and len(scores) == 5

    def test_quality_scores_zero_on_a_starless_frame(self):
        """星が無ければ「選ぶ理由が無い」= 0.0。nan で並べ替えを壊さない。"""
        frame, _ = A.synth_starfield(shape=(64, 64), n_stars=0, sky=100.0,
                                     read_sigma=5.0, seed=1)
        q = A.frame_quality(frame, threshold_sigma=8.0)
        assert q["n_stars"] == 0 and q["score"] == 0.0
        assert np.isfinite(q["sharpness"])           # 星が無くても出る唯一の指標


# ===========================================================================
# 宇宙線
# ===========================================================================
class TestCosmicRays:

    def test_single_frame_rejection_is_precise_and_leaves_the_stars_alone(self):
        """適合率 0.97 —— 星の中心を宇宙線と呼ばないことが要点。"""
        frame, truth = A.synth_starfield(shape=(128, 128), n_stars=25,
                                         n_cosmic=15, cosmic_flux=6000.0,
                                         sky=60.0, read_sigma=5.0, seed=13)
        cleaned, mask = A.cosmic_ray_reject(frame, sigma=5.0, f_lim=2.0)
        hit = truth["cosmic_mask"]
        tp = int((mask & hit).sum())
        assert tp / mask.sum() > 0.9, "precision"
        assert tp / hit.sum() > 0.6, "recall"
        # 星の位置が消えていないこと(除去後も同じ数の星が立つ)
        assert len(A.star_detect(cleaned)) == len(A.star_detect(frame))

    def test_rejection_actually_removes_the_flux_it_flagged(self):
        frame, truth = A.synth_starfield(shape=(96, 96), n_stars=10,
                                         n_cosmic=10, cosmic_flux=8000.0,
                                         sky=60.0, read_sigma=5.0, seed=19)
        cleaned, mask = A.cosmic_ray_reject(frame)
        assert cleaned[mask].max() < frame[mask].max() / 5.0

    def test_frame_to_frame_rejection_catches_every_hit(self):
        """同じ場所に二度は当たらないので、枚数があれば再現率は 1.000 になる。"""
        frames, _ = A.synth_frame_series(shape=(128, 128), n_frames=8,
                                         dither_px=0.0, n_stars=25,
                                         n_cosmic=10, cosmic_flux=6000.0,
                                         sky=60.0, read_sigma=5.0, seed=55)
        truth = np.stack([
            A.synth_starfield(shape=(128, 128), n_stars=25, n_cosmic=10,
                              cosmic_flux=6000.0, sky=60.0, read_sigma=5.0,
                              seed=55 + 1000 * i + 1, field_seed=55,
                              fwhm_px=3.2)[1]["cosmic_mask"]
            for i in range(8)])
        _, mask = A.cosmic_ray_reject_stack(frames, kappa=5.0, read_sigma=5.0)
        tp = int((mask & truth).sum())
        assert tp == int(truth.sum())                # 1 画素も取りこぼさない
        assert tp / mask.sum() > 0.95                # 実測 0.996

    def test_the_noise_model_floor_is_what_makes_it_precise(self):
        """床を外すと適合率が 0.996 -> 0.38 に落ちる(再現率は落ちない)。

        少数標本の MAD は画素ごとに大きく散るので、床が無いと**背景**が
        宇宙線に化ける。既定を変えたくなった人がまずここを読むように残す。
        """
        frames, _ = A.synth_frame_series(shape=(128, 128), n_frames=8,
                                         dither_px=0.0, n_stars=25,
                                         n_cosmic=10, cosmic_flux=6000.0,
                                         sky=60.0, read_sigma=5.0, seed=55)
        _, loose = A.cosmic_ray_reject_stack(frames, kappa=5.0)
        _, tight = A.cosmic_ray_reject_stack(frames, kappa=5.0, read_sigma=5.0)
        assert loose.sum() > 2.0 * tight.sum()

    def test_frame_to_frame_rejection_needs_at_least_three_frames(self):
        frames, _ = A.synth_frame_series(shape=(32, 32), n_frames=2,
                                         n_stars=4, seed=1)
        with pytest.raises(ValueError, match="at least 3 frames"):
            A.cosmic_ray_reject_stack(frames)


# ===========================================================================
# 位置合わせ
# ===========================================================================
class TestAlignment:

    def test_frame_align_recovers_the_planted_dither(self):
        """真のずれを 0.15 px 以内で当てる(5 通りのずれで)。"""
        frames, truth = A.synth_frame_series(shape=(128, 128), n_frames=6,
                                             dither_px=4.0, n_stars=30,
                                             sky=60.0, read_sigma=5.0, seed=31)
        for i in range(1, 6):
            M, info = A.frame_align(frames[0], frames[i], model="similarity")
            want = truth["shifts"][0] - truth["shifts"][i]
            err = np.hypot(info["shift_row"] - want[0],
                           info["shift_col"] - want[1])
            assert err < 0.15, (i, err)
            assert info["scale"] == pytest.approx(1.0, abs=2e-3)
            assert abs(info["rotation_deg"]) < 0.2
            assert info["n_inliers"] >= 20

    def test_every_model_agrees_on_a_pure_translation(self):
        """並進しか無い対では、4 つのモデルが同じ答えに落ちる。"""
        frames, truth = A.synth_frame_series(shape=(128, 128), n_frames=3,
                                             dither_px=3.0, n_stars=30,
                                             sky=60.0, read_sigma=5.0, seed=37)
        want = truth["shifts"][0] - truth["shifts"][1]
        for model in A.ALIGN_MODELS:
            _, info = A.frame_align(frames[0], frames[1], model=model)
            err = np.hypot(info["shift_row"] - want[0],
                           info["shift_col"] - want[1])
            assert err < 0.2, (model, err)

    def test_alignment_fails_closed_instead_of_returning_the_identity(self):
        """**恒等変換を黙って返さない。** 星の無い像は例外で止める。

        「ずれ 0」として合成に混ぜると、例外も警告も無しに二重像ができる。
        """
        empty, _ = A.synth_starfield(shape=(64, 64), n_stars=0, sky=100.0,
                                     read_sigma=5.0, seed=1)
        stars, _ = A.synth_starfield(shape=(64, 64), n_stars=10, sky=100.0,
                                     read_sigma=5.0, seed=2)
        with pytest.raises(ValueError, match="cannot align on stars"):
            A.frame_align(stars, empty, threshold_sigma=10.0)

    def test_alignment_refuses_frames_of_different_sizes(self):
        a, _ = A.synth_starfield(shape=(64, 64), n_stars=8, seed=1)
        b, _ = A.synth_starfield(shape=(48, 48), n_stars=8, seed=1)
        with pytest.raises(ValueError, match="same"):
            A.frame_align(a, b)

    def test_align_frames_leaves_the_reference_untouched(self):
        """基準は変換を通さない —— 恒等変換でも補間は像を鈍らせるから。"""
        frames, _ = A.synth_frame_series(shape=(96, 96), n_frames=4,
                                         dither_px=2.0, n_stars=25,
                                         sky=60.0, read_sigma=5.0, seed=43)
        aligned, mats = A.align_frames(frames, reference=1)
        assert np.array_equal(aligned[1], frames[1])
        assert np.array_equal(mats[1], np.eye(3))

    def test_align_frames_actually_brings_the_stars_together(self):
        frames, _ = A.synth_frame_series(shape=(96, 96), n_frames=5,
                                         dither_px=3.0, n_stars=25,
                                         sky=60.0, read_sigma=5.0, seed=43)
        before, _ = A.sigma_clip_stack(frames, mode="mean")
        after, _ = A.sigma_clip_stack(A.align_frames(frames)[0], mode="mean")
        assert A.frame_quality(after)["fwhm_px"] \
            < A.frame_quality(before)["fwhm_px"]

    def test_cubic_resampling_keeps_the_peak_that_bilinear_loses(self):
        """既定が ``order=3`` である理由を数字で(0.5 px は双一次の最悪位相)。"""
        f0, _ = A.synth_starfield(shape=(64, 64), n_stars=12, sky=0.0,
                                  read_sigma=0.0, noise=False, seed=41,
                                  margin_px=12.0)
        f1, _ = A.synth_starfield(shape=(64, 64), n_stars=12, sky=0.0,
                                  read_sigma=0.0, noise=False, seed=41,
                                  margin_px=12.0, shift_row=0.5, shift_col=0.5)
        lin = A.align_frames([f0, f1], order=1, threshold_sigma=4.0)[0][1]
        cub = A.align_frames([f0, f1], order=3, threshold_sigma=4.0)[0][1]
        assert (lin.max() - f1.max()) / f1.max() == pytest.approx(-0.114, abs=0.02)
        assert (cub.max() - f1.max()) / f1.max() == pytest.approx(-0.003, abs=0.01)
        # 総フラックスはどちらでも保たれる(失うのはピークだけ)
        for w in (lin, cub):
            assert (w.sum() - f1.sum()) / f1.sum() == pytest.approx(0.0, abs=1e-3)


# ===========================================================================
# 合成データそのもの
# ===========================================================================
class TestSynthesis:

    def test_the_same_seed_gives_the_same_frame_on_any_machine(self):
        a, _ = A.synth_starfield(shape=(48, 48), n_stars=9, seed=5)
        b, _ = A.synth_starfield(shape=(48, 48), n_stars=9, seed=5)
        assert np.array_equal(a, b)

    def test_the_field_seed_and_the_exposure_seed_are_independent(self):
        """同じ空を別の晩に撮る = ``field_seed`` は同じ、``seed`` は違う。"""
        a, ta = A.synth_starfield(shape=(64, 64), n_stars=10, seed=1,
                                  field_seed=100)
        b, tb = A.synth_starfield(shape=(64, 64), n_stars=10, seed=2,
                                  field_seed=100)
        assert np.array_equal(ta["rows"], tb["rows"])       # 同じ空
        assert np.array_equal(ta["fluxes"], tb["fluxes"])
        assert not np.array_equal(a, b)                     # 違う観測

    def test_a_series_shows_the_same_sky_in_every_frame(self):
        """**BUG が入りやすい所**: seed を 1 本にすると空ごと変わってしまう。"""
        frames, truth = A.synth_frame_series(shape=(96, 96), n_frames=5,
                                             dither_px=0.0, n_stars=20,
                                             sky=60.0, read_sigma=5.0, seed=61,
                                             flux_min=20000.0, flux_max=30000.0)
        detected = [A.star_detect(f) for f in frames]
        assert all(len(d) == len(detected[0]) for d in detected)
        for d in detected[1:]:
            for r, c in detected[0]:
                assert np.hypot(d[:, 0] - r, d[:, 1] - c).min() < 0.3

    def test_shot_noise_obeys_the_poisson_law_it_was_drawn_from(self):
        """ノイズが :mod:`photoncount` のものであることを Fano 係数で確かめる。

        空だけのフレームなら分散 = 平均。1e4 画素の Fano 係数の標準誤差は
        ``sqrt(2/N) = 1.4 %`` なので、許容 5 % は 3.5 sigma。
        """
        frame, _ = A.synth_starfield(shape=(100, 100), n_stars=0, sky=300.0,
                                     read_sigma=0.0, seed=3)
        assert float(np.var(frame) / np.mean(frame)) == pytest.approx(1.0,
                                                                     rel=0.05)

    def test_read_noise_adds_in_quadrature_on_top_of_the_shot_noise(self):
        """読み出しノイズは加法ガウス —— 分散が足し算になる。"""
        for rs in (0.0, 10.0, 20.0):
            frame, _ = A.synth_starfield(shape=(100, 100), n_stars=0, sky=300.0,
                                         read_sigma=rs, seed=3)
            assert float(np.var(frame)) == pytest.approx(300.0 + rs * rs,
                                                         rel=0.06), rs

    def test_cosmic_rays_are_added_after_the_poisson_sampling(self):
        """宇宙線は光子ではない: 注入したフラックスがそのまま乗る。"""
        frame, truth = A.synth_starfield(shape=(64, 64), n_stars=0, sky=0.0,
                                         read_sigma=0.0, n_cosmic=8,
                                         cosmic_flux=1234.0, seed=6)
        assert truth["cosmic_mask"].sum() > 0
        assert np.allclose(frame[truth["cosmic_mask"]], 1234.0)
        assert np.allclose(frame[~truth["cosmic_mask"]], 0.0)

    def test_a_dither_moves_the_truth_with_the_picture(self):
        frame, truth = A.synth_starfield(shape=(96, 96), n_stars=8,
                                         flux_min=30000.0, flux_max=40000.0,
                                         sky=50.0, read_sigma=4.0, seed=8,
                                         margin_px=16.0, shift_row=2.0,
                                         shift_col=-3.0)
        base, tbase = A.synth_starfield(shape=(96, 96), n_stars=8,
                                        flux_min=30000.0, flux_max=40000.0,
                                        sky=50.0, read_sigma=4.0, seed=8,
                                        margin_px=16.0)
        assert np.allclose(truth["rows"] - tbase["rows"], 2.0)
        assert np.allclose(truth["cols"] - tbase["cols"], -3.0)

    def test_a_moffat_profile_has_heavier_wings_than_a_gaussian(self):
        """同じ FWHM でも Moffat の方が裾が重い(大気の星像がそうであるように)。"""
        g, _ = _one_star(1.5, size=64, margin=28.0)
        m, tm = A.synth_starfield(shape=(64, 64), n_stars=1, flux_min=10000.0,
                                  flux_max=10000.0, fwhm_px=1.5 * A.FWHM_PER_SIGMA,
                                  psf="moffat", moffat_beta=2.5, sky=0.0,
                                  read_sigma=0.0, noise=False, seed=11,
                                  margin_px=28.0)
        ctr = np.array([[tm["rows"][0], tm["cols"][0]]])
        gg = A.aperture_photometry(g, ctr, r_aperture=3.0, r_inner=8.0,
                                   r_outer=14.0)[0]["flux"]
        mm = A.aperture_photometry(m, ctr, r_aperture=3.0, r_inner=8.0,
                                   r_outer=14.0)[0]["flux"]
        assert mm < gg                                # 中心に集まる割合が小さい

    def test_synthesis_refuses_a_diverging_moffat(self):
        """``beta <= 1`` では積分が発散する。手前で名指しで止める。"""
        with pytest.raises(ValueError, match="moffat_beta"):
            A.synth_starfield(psf="moffat", moffat_beta=1.0)

    def test_a_series_refuses_the_arguments_it_controls_itself(self):
        with pytest.raises(ValueError, match="dither_px instead"):
            A.synth_frame_series(shift_row=1.0)
        with pytest.raises(ValueError, match="field_seed is pinned"):
            A.synth_frame_series(field_seed=3)


# ===========================================================================
# fail-closed の契約
# ===========================================================================
class TestFailClosed:

    def test_a_raw_3d_array_is_refused_as_a_frame_list(self):
        """(N,H,W) は video / voxel / histcube と見分けが付かない。

        構造検査はどれも通ってしまい、取り違えても例外にならず**もっともらしく
        間違った合成結果**が返る。list を要求することで、呼ぶ側に
        「先頭軸はフレーム軸だ」と宣言させる。
        """
        cube = np.random.default_rng(0).random((5, 16, 16))
        for fn in (A.sigma_clip_stack, A.drizzle_resample, A.align_frames,
                   A.lucky_select, A.cosmic_ray_reject_stack):
            with pytest.raises(ValueError, match="not a raw 3-D ndarray"):
                fn(cube)
        # list に直せば通る(拒否は不便のための不便ではない)
        stack, _ = A.sigma_clip_stack(list(cube))
        assert stack.shape == (16, 16)

    def test_frames_of_different_shapes_are_refused_by_name(self):
        with pytest.raises(ValueError, match=r"frames\[1\] has shape"):
            A.sigma_clip_stack([np.zeros((16, 16)), np.zeros((8, 8))])

    def test_non_finite_pixels_are_refused(self):
        bad = np.zeros((16, 16))
        bad[3, 4] = np.nan
        with pytest.raises(ValueError, match="non-finite"):
            A.noise_sigma(bad)
        with pytest.raises(ValueError, match="non-finite"):
            A.sigma_clip_stack([np.zeros((16, 16)), bad])

    def test_unknown_enumerations_are_refused_not_silently_defaulted(self):
        frames = [np.zeros((16, 16)), np.ones((16, 16))]
        with pytest.raises(ValueError, match="mode must be one of"):
            A.sigma_clip_stack(frames, mode="average")
        with pytest.raises(ValueError, match="psf must be one of"):
            A.synth_starfield(psf="airy")
        with pytest.raises(ValueError, match="model must be one of"):
            A.psf_fit(np.zeros((16, 16)), np.array([[8.0, 8.0]]), model="lorentz")
        with pytest.raises(ValueError, match="model must be one of"):
            A.frame_align(np.zeros((16, 16)), np.zeros((16, 16)),
                          model="projective")

    def test_a_single_frame_is_refused_where_two_are_needed(self):
        with pytest.raises(ValueError, match="at least 2 frames"):
            A.sigma_clip_stack([np.zeros((8, 8))])

    def test_oversized_requests_are_refused_before_numpy_is_asked(self):
        with pytest.raises(ValueError, match="MAX_OUTPUT_ELEMENTS"):
            A.drizzle_resample([np.zeros((2048, 2048))] * 2, scale=8.0)

    def test_a_boolean_is_not_an_integer_here(self):
        """``True`` は 1 ではない。数として通すと後で必ず刺さる。"""
        with pytest.raises(ValueError, match="n_stars"):
            A.synth_starfield(n_stars=True)
        with pytest.raises(ValueError, match="kappa"):
            A.sigma_clip_stack([np.zeros((8, 8))] * 2, kappa=True)


# ===========================================================================
# 台帳(opsastrostack)
# ===========================================================================
class TestRegistry:

    def test_every_declared_op_has_a_body(self):
        assert opsastrostack.missing() == []
        assert len(opsastrostack.OPSASTROSTACK) == 14
        assert len(opsastrostack.categories()) == 6

    def test_the_ledger_and_the_module_agree_on_the_op_list(self):
        assert sorted(opsastrostack.list_ops()) == sorted(A.ASTROSTACK)
        assert sorted(A.ASTROSTACK) == sorted(
            n for n in A.__all__ if callable(getattr(A, n, None)))

    def test_no_new_sort_was_invented(self):
        """既存語彙だけで宣言できている(新語を足していないことの機械検査)。"""
        known = {"image2d", "images", "table", "keypoints", "indices",
                 "measurement", "matrix"}
        for name in opsastrostack.list_ops():
            meta = opsastrostack.info(name)
            assert meta["out"] in known, (name, meta["out"])
            for s in meta["in"]:
                assert s in known, (name, s)

    #: 宣言 out 型 → ``tools/chain_fuzz.TYPE_CHECKS`` と同じ述語
    PREDICATES = {
        "image2d": lambda v: isinstance(v, np.ndarray) and v.ndim == 2,
        "images": lambda v: isinstance(v, (list, tuple)) and all(
            isinstance(x, np.ndarray) and x.ndim == 2 for x in v),
        "table": lambda v: isinstance(v, (list, dict)),
        "keypoints": lambda v: isinstance(v, np.ndarray) and v.ndim == 2,
        "indices": lambda v: isinstance(v, np.ndarray) and v.ndim == 1,
        "measurement": lambda v: isinstance(v, (int, float, np.floating,
                                                np.integer)),
        "matrix": lambda v: isinstance(v, np.ndarray) and v.ndim == 2,
    }

    def test_call_returns_exactly_what_the_ledger_declares(self):
        """14 op を実際に走らせ、素の返りを宣言型の述語に当てる(TYPEMISS 検査)。

        ``call`` は adapter を通した「台帳の姿」を返すので、ここが通れば
        連鎖の型接続が嘘でないことになる。
        """
        image, _ = A.synth_starfield(shape=(64, 64), n_stars=12,
                                     flux_min=20000.0, flux_max=40000.0,
                                     sky=60.0, read_sigma=5.0, seed=71,
                                     margin_px=12.0)
        frames, truth = A.synth_frame_series(shape=(64, 64), n_frames=4,
                                             dither_px=1.0, n_stars=12,
                                             flux_min=20000.0, flux_max=40000.0,
                                             sky=60.0, read_sigma=5.0, seed=71,
                                             margin_px=12.0)
        stars = A.star_detect(image)
        args = {
            "synth_starfield": ((), {"shape": (32, 32), "n_stars": 3}),
            "synth_frame_series": ((), {"shape": (32, 32), "n_frames": 3,
                                        "n_stars": 3}),
            "frame_quality": ((image,), {}),
            "lucky_select": ((frames,), {}),
            "noise_sigma": ((image,), {}),
            "sigma_clip_stack": ((frames,), {}),
            "drizzle_resample": ((frames,), {}),
            "cosmic_ray_reject": ((image,), {}),
            "cosmic_ray_reject_stack": ((frames,), {}),
            "star_detect": ((image,), {}),
            "psf_fit": ((image, stars), {}),
            "aperture_photometry": ((image, stars), {}),
            "frame_align": ((frames[0], frames[1]), {}),
            "align_frames": ((frames,), {}),
        }
        assert set(args) == set(opsastrostack.list_ops())
        for name, (a, kw) in args.items():
            out = opsastrostack.call(name, *a, **kw)
            declared = opsastrostack.info(name)["out"]
            assert self.PREDICATES[declared](out), (name, declared, type(out))

    def test_get_returns_the_bare_tuple_that_call_adapts(self):
        """``get`` は本体(タプル)、``call`` は台帳の姿(先頭要素)。"""
        frames, _ = A.synth_frame_series(shape=(32, 32), n_frames=3,
                                         n_stars=4, seed=1)
        raw = opsastrostack.get("sigma_clip_stack")(frames)
        adapted = opsastrostack.call("sigma_clip_stack", frames)
        assert isinstance(raw, tuple) and len(raw) == 2
        assert np.array_equal(raw[0], adapted)
        assert raw[1].shape == (3, 32, 32) and raw[1].dtype == bool

    def test_every_tuple_returning_op_has_an_adapter(self):
        """旗ではなくタプル + adapter、を機械で強制する。

        ``return_mask=True`` のような旗で返り型が変わる op を足すと、台帳が
        どちらの姿を宣言しても嘘になる。ここが落ちたらその設計に戻したという
        合図。
        """
        image, _ = A.synth_starfield(shape=(32, 32), n_stars=4, seed=1)
        frames, _ = A.synth_frame_series(shape=(32, 32), n_frames=3,
                                         n_stars=4, seed=1)
        probes = {"synth_starfield": ((), {"shape": (16, 16), "n_stars": 2}),
                  "synth_frame_series": ((), {"shape": (16, 16), "n_frames": 3,
                                              "n_stars": 2}),
                  "sigma_clip_stack": ((frames,), {}),
                  "drizzle_resample": ((frames,), {}),
                  "cosmic_ray_reject": ((image,), {}),
                  "cosmic_ray_reject_stack": ((frames,), {}),
                  "lucky_select": ((frames,), {}),
                  "align_frames": ((frames,), {})}
        for name, (a, kw) in probes.items():
            raw = opsastrostack.get(name)(*a, **kw)
            assert isinstance(raw, tuple), name
            assert name in opsastrostack.RESULT_ADAPTERS, name

    def test_the_docs_line_of_each_op_is_its_first_docstring_line(self):
        for name in opsastrostack.list_ops():
            doc = opsastrostack.info(name)["doc"]
            assert doc and not doc.startswith(" "), name


# ===========================================================================
# 2026-09-02 の実測が暴いた不具合(最小再現つき)
# ===========================================================================
class TestBugsFoundByMeasurement:

    def test_a_frame_series_no_longer_re_rolls_the_sky_every_frame(self):
        """BUG: ``seed`` 1 本で星の抽選もノイズも決めていたため、
        :func:`synth_frame_series` が**毎フレーム別の空**を作っていた。
        位置合わせは 1 対応しか見つけられず(正しく fail-closed した)、
        フレーム間の宇宙線除去は全画素を外れ値と呼んだ。"""
        frames, truth = A.synth_frame_series(shape=(96, 96), n_frames=4,
                                             dither_px=2.0, n_stars=25,
                                             sky=60.0, read_sigma=5.0, seed=31)
        _, info = A.frame_align(frames[0], frames[1])
        assert info["n_pairs"] >= 20            # 修正前は 1
        assert info["n_inliers"] >= 20

    def test_the_clip_scale_is_robust_by_default(self):
        """BUG: 既定が ``scale="std"`` だったので、汚染 20 % で**何も落とさず**
        単純平均と同じ答えを返していた。棄却率 0 % を「外れ値が無かった」と
        読むと、静かに間違える。"""
        _, acc = A.sigma_clip_stack(_flat_frames(20, 4), kappa=3.0)
        assert 1.0 - float(acc.mean()) > 0.15

    def test_the_offset_vote_no_longer_splits_across_a_bin_boundary(self):
        """BUG: 投票の絞り込みが 1 段だけだったので、真のずれがビン境界に
        乗ると票が 2 分され、26 対応あるフレーム対で票が 3 まで落ちた。
        推定値そのものは最近傍照合が救っていたが、票数を信頼度として読むと
        嘘になる。"""
        frames, _ = A.synth_frame_series(shape=(128, 128), n_frames=3,
                                         dither_px=4.0, n_stars=40, sky=60.0,
                                         read_sigma=5.0, seed=31)
        _, info = A.frame_align(frames[0], frames[1])
        assert info["votes"] >= 20               # 修正前は 3

    def test_the_cosmic_ray_laplacian_no_longer_calls_star_cores_hits(self):
        """BUG: 素の格子でラプラシアンを取っていたので、星の中心が必ず尖って
        見え、128x128 のフレームで 227 画素を宇宙線と呼んで適合率 0.185 だった
        (真の宇宙線は 54 画素)。2 倍標本化してから微細構造と比べると
        38 画素・適合率 0.974 になる。"""
        frame, truth = A.synth_starfield(shape=(128, 128), n_stars=25,
                                         n_cosmic=15, cosmic_flux=6000.0,
                                         sky=60.0, read_sigma=5.0, seed=13)
        _, mask = A.cosmic_ray_reject(frame, sigma=5.0, f_lim=2.0)
        assert int(mask.sum()) < 60              # 修正前は 227
        assert int((mask & truth["cosmic_mask"]).sum()) / mask.sum() > 0.9
