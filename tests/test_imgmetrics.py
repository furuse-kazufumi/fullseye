# -*- coding: utf-8 -*-
"""「2 枚の絵がどれだけ違うか」を測る op の検査。

この族を選んだ理由が **答え合わせが外からできること**なので、テストも
「自分の実装が自分と一致する」ではなく **外部の基準・解析的な既知値**に
突き合わせる形にしてある:

* CIEDE2000 — Sharma, Wu & Dalal (2005) の公開検証表 34 組
* SSIM / PSNR — 同一画像や既知の一定差など、閉じた形で答えが出る場面
* 相互情報量 — ``I(X;X) = H(X)`` の恒等式
* CIE L*a*b* — 白色点の定義から出る値(白 → L=100)

加えて、**黙って間違う場所を「そういう結果になる」テストとして残す**
(``data_range`` の取り違えで何 dB ずれるか、NCD の下駄が何ぼか等)。
"""
from __future__ import annotations

import numpy as np
import pytest

import imgmetrics as M


# =========================================================================
# CIEDE2000 —— 外部の公開検証表との照合(この族の中心)
# =========================================================================

def test_ciede2000_matches_all_published_reference_pairs():
    """Sharma et al. (2005) の 34 組すべてと、表の桁数(小数 4 桁)で一致すること。

    実装が踏み外しやすい 3 か所(色相角の平均、275°の項、無彩色近傍)を
    狙って選ばれた対なので、ここが通れば実装の主要な分岐は押さえられている。
    """
    worst = 0.0
    for L1, a1, b1, L2, a2, b2, want in M.CIEDE2000_TEST_PAIRS:
        got = float(M.delta_e_2000((L1, a1, b1), (L2, a2, b2)))
        worst = max(worst, abs(got - want))
    assert len(M.CIEDE2000_TEST_PAIRS) == 34
    assert worst < 5e-5, f"最大誤差 {worst:.3e}(表は小数 4 桁なので 5e-5 が丸めの上限)"


def test_ciede2000_is_symmetric():
    """対 7 と 8 は同じ 2 色を入れ替えたもので、期待値も同じ 2.3669。"""
    p7, p8 = M.CIEDE2000_TEST_PAIRS[6], M.CIEDE2000_TEST_PAIRS[7]
    assert p7[6] == p8[6] == 2.3669
    assert M.delta_e_2000(p7[:3], p7[3:6]) == pytest.approx(M.delta_e_2000(p8[:3], p8[3:6]))


def test_ciede2000_is_vectorised_and_agrees_with_the_scalar_path():
    lab1 = np.array([p[:3] for p in M.CIEDE2000_TEST_PAIRS])
    lab2 = np.array([p[3:6] for p in M.CIEDE2000_TEST_PAIRS])
    want = np.array([p[6] for p in M.CIEDE2000_TEST_PAIRS])
    assert M.delta_e_2000(lab1, lab2).shape == (34,)
    assert np.allclose(M.delta_e_2000(lab1, lab2), want, atol=5e-5)


def test_ciede2000_differs_from_cie76_where_it_is_supposed_to():
    """CIE76 が知覚と合わない典型(彩度の高い青)で、両者が実際に食い違うこと。

    対 1 の実測: **CIE76 = 4.0011 / ΔE00 = 2.0425 で比は 1.959**。
    「色差」と一言で書いて別の定義を混ぜると、この比率ぶん静かにずれる。
    """
    L1, a1, b1, L2, a2, b2, want = M.CIEDE2000_TEST_PAIRS[0]
    d76 = float(M.delta_e_76((L1, a1, b1), (L2, a2, b2)))
    assert d76 == pytest.approx(4.0011, abs=1e-4)
    assert float(M.delta_e_2000((L1, a1, b1), (L2, a2, b2))) == pytest.approx(want, abs=5e-5)
    assert d76 / want == pytest.approx(1.959, abs=1e-3)


def test_kL_kC_kH_must_be_positive():
    for kw in ({"kL": 0.0}, {"kC": -1.0}, {"kH": float("nan")}):
        with pytest.raises(ValueError, match="positive finite"):
            M.delta_e_2000((50, 0, 0), (50, 1, 1), **kw)


# =========================================================================
# 色空間 —— 定義から出る既知値
# =========================================================================

def test_white_maps_to_lightness_100_and_black_to_zero():
    """D65 白色点の定義から、sRGB の白は L*=100・a*=b*=0。"""
    white = M.rgb_to_lab(np.array([1.0, 1.0, 1.0]))
    assert white[0] == pytest.approx(100.0, abs=1e-6)
    assert white[1] == pytest.approx(0.0, abs=1e-3)
    assert white[2] == pytest.approx(0.0, abs=1e-3)
    black = M.rgb_to_lab(np.array([0.0, 0.0, 0.0]))
    assert np.allclose(black, [0.0, 0.0, 0.0], atol=1e-12)


def test_lab_roundtrip_is_exact_inside_the_gamut():
    rng = np.random.default_rng(0)
    rgb = rng.random((64, 3))
    back = M.lab_to_rgb(M.rgb_to_lab(rgb))
    assert np.max(np.abs(back - rgb)) < 1e-10


def test_lab_roundtrip_is_not_exact_outside_the_gamut():
    """色域外は切り詰められる ―― 往復が一致しないことを欠陥として隠さない。"""
    out_of_gamut = np.array([[60.0, 120.0, -120.0]])
    back = M.rgb_to_lab(M.lab_to_rgb(out_of_gamut))
    assert np.max(np.abs(back - out_of_gamut)) > 10.0


def test_uint8_is_accepted_and_matches_the_float_path():
    u8 = np.array([[0, 128, 255]], dtype=np.uint8)
    assert np.allclose(M.rgb_to_lab(u8), M.rgb_to_lab(u8 / 255.0))


def test_the_transfer_function_is_not_duplicated():
    """伝達関数の実体は gfx2d に一本化されている(2 つ持つと片方だけ直る)。"""
    gfx2d = pytest.importorskip("gfx2d")
    x = np.linspace(0.0, 1.0, 257).reshape(-1, 1).repeat(3, axis=1)
    assert np.array_equal(M.srgb_to_linear(x), gfx2d.srgb_to_linear(x))


def test_rgb_inputs_must_have_three_channels():
    with pytest.raises(ValueError, match="3 channels"):
        M.rgb_to_xyz(np.zeros((4, 4)))
    with pytest.raises(ValueError, match="3 channels"):
        M.delta_e_2000(np.zeros((4, 2)), np.zeros((4, 2)))


# =========================================================================
# data_range —— この族で最も黙って間違う場所
# =========================================================================

def test_integer_dtypes_fix_the_range_without_being_told():
    assert M.data_range_of(np.zeros((2, 2), np.uint8)) == 255.0
    assert M.data_range_of(np.zeros((2, 2), np.uint16)) == 65535.0
    assert M.data_range_of(np.zeros((2, 2), bool)) == 1.0


def test_unit_float_is_accepted_but_anything_wider_demands_an_explicit_range():
    assert M.data_range_of(np.linspace(0, 1, 9)) == 1.0
    with pytest.raises(ValueError, match=r"48\.13 dB"):
        M.data_range_of(np.linspace(0, 255, 9))
    with pytest.raises(ValueError, match="negative values"):
        M.data_range_of(np.linspace(-1, 1, 9))


def test_mixed_dtypes_are_refused_rather_than_guessed():
    with pytest.raises(ValueError, match="mixed dtypes"):
        M.data_range_of(np.zeros(4, np.uint8), np.zeros(4, np.float64))


def test_a_wrong_data_range_shifts_psnr_by_exactly_the_documented_amount():
    """[0,1] の float を 255 だと思って測ると 20*log10(255) = 48.1308 dB ずれる。

    例外は出ず、それらしい数値が出る ―― これが :func:`data_range_of` が
    推測を拒む理由。ずれ幅が理屈どおりであることを数値で残す。
    """
    rng = np.random.default_rng(1)
    a = rng.random((32, 32))
    b = a + 0.01 * rng.standard_normal((32, 32))
    shift = M.psnr(a, b, data_range=255.0) - M.psnr(a, b, data_range=1.0)
    assert shift == pytest.approx(20.0 * np.log10(255.0), abs=1e-9)
    assert shift == pytest.approx(48.1308, abs=1e-4)


def test_data_range_must_be_positive_and_finite():
    for bad in (0.0, -1.0, float("inf"), float("nan")):
        with pytest.raises(ValueError, match="positive finite"):
            M.data_range_of(np.zeros(4), data_range=bad)


# =========================================================================
# PSNR / MSE —— 閉じた形の既知値
# =========================================================================

def test_psnr_of_a_known_constant_difference_matches_the_closed_form():
    a = np.zeros((16, 16))
    b = np.full((16, 16), 0.1)
    assert M.mse(a, b) == pytest.approx(0.01)
    assert M.rmse(a, b) == pytest.approx(0.1)
    assert M.psnr(a, b, data_range=1.0) == pytest.approx(20.0, abs=1e-12)   # 10*log10(1/0.01)


def test_identical_images_give_infinite_psnr_rather_than_a_padded_number():
    """0 除算を小さな値で黙って避けると「非常に良い一致」が有限値に化ける。"""
    a = np.linspace(0, 1, 64).reshape(8, 8)
    assert M.psnr(a, a.copy()) == float("inf")


def test_non_finite_input_is_refused():
    a = np.zeros((4, 4))
    b = a.copy()
    b[0, 0] = np.nan
    with pytest.raises(ValueError, match="finite"):
        M.mse(a, b)


def test_shape_mismatch_is_refused_rather_than_broadcast():
    with pytest.raises(ValueError, match="same shape"):
        M.mse(np.zeros((4, 4)), np.zeros((4, 1)))


# =========================================================================
# SSIM / MS-SSIM
# =========================================================================

def test_ssim_of_an_image_with_itself_is_one():
    rng = np.random.default_rng(2)
    a = rng.random((64, 64))
    assert M.ssim(a, a.copy()) == pytest.approx(1.0, abs=1e-12)


def _structured_image(n=96):
    """なだらかな勾配 + 矩形 + 円。**構造のある絵**。

    純粋な一様乱数に雑音を足しても SSIM はあまり落ちない(構造が最初から
    無いので「構造の類似」が壊れない)。実測では σ=0.2 の雑音でも 0.83 に
    留まる ―― SSIM は雑音の量ではなく**構造**を測る指標なので、これは
    指標の性質であってバグではない。だから雑音耐性を見る絵は構造を持たせる。
    """
    y, x = np.mgrid[0:n, 0:n] / (n - 1.0)
    img = 0.25 + 0.5 * x
    img[n // 5: n // 2, n // 5: n // 2] = 0.95
    img[(y - 0.7) ** 2 + (x - 0.7) ** 2 < 0.02] = 0.05
    return img


def test_ssim_falls_as_noise_grows():
    rng = np.random.default_rng(3)
    a = _structured_image()
    vals = [M.ssim(a, np.clip(a + s * rng.standard_normal(a.shape), 0, 1), data_range=1.0)
            for s in (0.01, 0.05, 0.2)]
    assert vals[0] > vals[1] > vals[2], vals
    assert vals[0] > 0.9 and vals[2] < 0.3, vals


def test_ssim_measures_structure_not_noise_amplitude():
    """同じ雑音でも、構造のある絵は大きく落ち、雑音そのものは落ちない。

    SSIM を「雑音の量」と読み違えると、雑音だらけの絵で高い値が出たときに
    「よく復元できた」と誤読する。その差を数値で残しておく。
    """
    rng = np.random.default_rng(31)
    noise_sigma = 0.2
    structured = _structured_image()
    pure_noise = rng.random((96, 96))
    s_struct = M.ssim(structured,
                      np.clip(structured + noise_sigma * rng.standard_normal((96, 96)), 0, 1),
                      data_range=1.0)
    s_noise = M.ssim(pure_noise,
                     np.clip(pure_noise + noise_sigma * rng.standard_normal((96, 96)), 0, 1),
                     data_range=1.0)
    assert s_noise > s_struct + 0.3, (s_noise, s_struct)


def test_ssim_agrees_with_an_independent_implementation():
    """scikit-image があるときだけ突き合わせる(外部基準での確認)。

    比較は原論文の設定に揃える ―― ガウシアン窓 σ=1.5、母分散
    (``use_sample_covariance=False``)。片方だけ標本分散にすると値が変わる。
    """
    ski = pytest.importorskip("skimage.metrics")
    rng = np.random.default_rng(4)
    a = rng.random((96, 96))
    b = np.clip(a + 0.05 * rng.standard_normal(a.shape), 0, 1)
    mine = M.ssim(a, b, data_range=1.0)
    theirs = ski.structural_similarity(a, b, data_range=1.0, gaussian_weights=True,
                                       sigma=1.5, use_sample_covariance=False)
    assert mine == pytest.approx(theirs, abs=2e-3), f"mine={mine!r} theirs={theirs!r}"


def test_cropping_the_border_changes_the_number_so_the_setting_must_travel():
    """縁を落とすかどうかで値が変わる ―― 図注に数値だけ写すと条件が消える。"""
    rng = np.random.default_rng(5)
    a = rng.random((32, 32))
    b = np.clip(a + 0.05 * rng.standard_normal(a.shape), 0, 1)
    cropped = M.ssim(a, b, crop_border=True)
    kept = M.ssim(a, b, crop_border=False)
    assert abs(cropped - kept) > 1e-4, f"cropped={cropped!r} kept={kept!r}"


def test_ssim_map_shows_where_the_difference_is():
    a = np.zeros((64, 64))
    a[20:44, 20:44] = 1.0
    b = a.copy()
    b[28:36, 28:36] = 0.0                      # 真ん中に穴を開ける
    smap = M.ssim_map(a, b, data_range=1.0)
    assert smap.shape == (54, 54)               # 11 窓の縁 5 px を落とした形
    cy = cx = 32 - 5
    assert smap[cy, cx] < 0.5                   # 穴のところは似ていない
    assert smap[2, 2] > 0.99                    # 触っていない隅はそのまま


def test_ssim_refuses_an_image_smaller_than_the_window():
    with pytest.raises(ValueError, match="at least win_size"):
        M.ssim(np.zeros((7, 7)), np.zeros((7, 7)))


def test_ssim_window_must_be_odd_and_at_least_three():
    for bad in (2, 10, 1):
        with pytest.raises(ValueError, match="odd integer"):
            M.ssim(np.zeros((32, 32)), np.zeros((32, 32)), win_size=bad)


def test_ssim_handles_colour_through_channel_axis():
    rng = np.random.default_rng(6)
    a = rng.random((48, 48, 3))
    assert M.ssim(a, a.copy(), channel_axis=-1) == pytest.approx(1.0, abs=1e-12)


def test_ms_ssim_of_an_image_with_itself_is_one():
    rng = np.random.default_rng(7)
    a = rng.random((256, 256))
    assert M.ms_ssim(a, a.copy()) == pytest.approx(1.0, abs=1e-9)


def test_ms_ssim_refuses_to_silently_drop_a_scale():
    """段数の違う MS-SSIM は別の指標。足りない絵は黙って縮めず例外にする。"""
    rng = np.random.default_rng(8)
    a = rng.random((64, 64))
    with pytest.raises(ValueError, match="needs every axis to be at least"):
        M.ms_ssim(a, a.copy())
    # 段数を減らすと成立する(それは呼び手の明示的な選択)
    assert M.ms_ssim(a, a.copy(), weights=(0.5, 0.5)) == pytest.approx(1.0, abs=1e-9)


def test_ms_ssim_weights_must_be_a_normalised_distribution():
    rng = np.random.default_rng(9)
    a = rng.random((256, 256))
    for bad in ((0.5, 0.4), (-0.5, 1.5), (1.0,)):
        with pytest.raises(ValueError, match="summing to 1|1-D non-negative"):
            M.ms_ssim(a, a.copy(), weights=bad)


def test_ms_ssim_is_grayscale_only():
    with pytest.raises(ValueError, match="2-D grayscale"):
        M.ms_ssim(np.zeros((256, 256, 3)), np.zeros((256, 256, 3)))


# =========================================================================
# 情報量 —— 恒等式で答え合わせ
# =========================================================================

def test_self_information_equals_entropy_exactly():
    """I(X; X) = H(X) は定義から厳密に成り立つ ―― 同じビン割りで出す限り。"""
    rng = np.random.default_rng(10)
    a = rng.random((64, 64))
    assert M.mutual_information(a, a.copy()) == pytest.approx(M.image_entropy(a), abs=1e-12)


def test_normalised_mutual_information_is_one_for_identical_images():
    rng = np.random.default_rng(11)
    a = rng.random((64, 64))
    assert M.normalized_mutual_information(a, a.copy()) == pytest.approx(1.0, abs=1e-12)


def test_independent_noise_has_small_but_non_zero_mutual_information():
    """標本が有限なので厳密に 0 にはならない ―― 上振れ幅を数値で残す。"""
    rng = np.random.default_rng(12)
    a = rng.random((128, 128))
    b = rng.random((128, 128))
    mi = M.mutual_information(a, b, bins=64)
    assert 0.0 < mi < 0.35, f"独立な 2 枚の相互情報量 {mi:.4f} bit(64 ビン・16384 標本)"


def test_more_bins_inflate_mutual_information_on_independent_images():
    """ビンを増やすほど上振れする ―― bins を既定任せにしてはいけない理由。"""
    rng = np.random.default_rng(13)
    a = rng.random((128, 128))
    b = rng.random((128, 128))
    assert M.mutual_information(a, b, bins=16) < M.mutual_information(a, b, bins=128)


def test_joint_entropy_is_bounded_by_the_sum_of_marginals():
    rng = np.random.default_rng(14)
    a = rng.random((64, 64))
    b = np.clip(a + 0.1 * rng.standard_normal(a.shape), 0, 1)
    assert M.joint_entropy(a, b) <= M.image_entropy(a) + M.image_entropy(b) + 1e-12


def test_two_constant_images_make_the_normalising_bound_zero():
    """H(A)=H(B)=0 では比が定義できない。0 や 1 を返すのは推測なので拒否する。"""
    a = np.full((16, 16), 0.5)
    assert M.mutual_information(a, a.copy()) == pytest.approx(0.0, abs=1e-12)
    with pytest.raises(ValueError, match="undefined"):
        M.normalized_mutual_information(a, a.copy())


def test_bins_must_be_at_least_two():
    with pytest.raises(ValueError, match="bins must be"):
        M.mutual_information(np.zeros((8, 8)), np.zeros((8, 8)), bins=1)


# =========================================================================
# 圧縮距離
# =========================================================================

def test_ncd_of_an_array_with_itself_is_small_but_not_zero():
    """実際の圧縮器は理想的な複雑度ではないので下駄がある ―― 実測値を残す。"""
    rng = np.random.default_rng(15)
    a = (rng.random((64, 64)) * 255).astype(np.uint8)
    d = M.ncd(a, a.copy())
    assert 0.0 < d < 0.15, f"同一入力の NCD = {d:.4f}(lzma のヘッダぶんの下駄)"


def test_ncd_separates_related_from_unrelated_data():
    rng = np.random.default_rng(16)
    base = (rng.random((64, 64)) * 255).astype(np.uint8)
    near = base.copy()
    near[0, :] = 0
    far = (rng.random((64, 64)) * 255).astype(np.uint8)
    assert M.ncd(base, near) < M.ncd(base, far)


def test_ncd_compares_like_with_like():
    a = np.zeros((8, 8), np.uint8)
    with pytest.raises(ValueError, match="like with like"):
        M.ncd(a, np.zeros((8, 8), np.float64))
    with pytest.raises(ValueError, match="like with like"):
        M.ncd(a, np.zeros((4, 4), np.uint8))


def test_unknown_compressor_is_refused():
    with pytest.raises(ValueError, match="compressor must be"):
        M.compressed_size(np.zeros(8), compressor="brotli")


# =========================================================================
# まとめ op —— 数値と一緒に条件を返す
# =========================================================================

def test_compare_images_reports_the_conditions_alongside_the_numbers():
    """数値だけを図注に写して条件が消えるのを防ぐのが contract の役目。"""
    rng = np.random.default_rng(17)
    a = rng.random((64, 64))
    b = np.clip(a + 0.03 * rng.standard_normal(a.shape), 0, 1)
    rep = M.compare_images(a, b)
    for k in ("mse", "rmse", "psnr", "ssim", "mutual_information", "ncd", "contract"):
        assert k in rep
    assert rep["contract"]["data_range"] == 1.0
    assert rep["contract"]["ssim_win_size"] == 11
    assert rep["contract"]["ssim_crop_border"] is True
    assert rep["psnr"] > 20.0 and 0.0 < rep["ssim"] < 1.0


def test_compare_images_adds_colour_difference_for_rgb():
    rng = np.random.default_rng(18)
    a = rng.random((48, 48, 3))
    b = np.clip(a + 0.02 * rng.standard_normal(a.shape), 0, 1)
    rep = M.compare_images(a, b, channel_axis=-1)
    assert rep["delta_e_2000_mean"] > 0.0
    assert rep["delta_e_2000_mean"] == pytest.approx(float(np.mean(M.delta_e_map(a, b))))


def test_compare_images_survives_two_constant_images():
    """NMI が定義できない場合に落ちず、None で「測れなかった」と言うこと。"""
    a = np.full((32, 32), 0.25)
    rep = M.compare_images(a, a.copy())
    assert rep["normalized_mutual_information"] is None
    assert rep["psnr"] == float("inf")


def test_delta_e_map_needs_rgb_images():
    with pytest.raises(ValueError, match="RGB images"):
        M.delta_e_map(np.zeros((8, 8)), np.zeros((8, 8)))
    with pytest.raises(ValueError, match="same shape"):
        M.delta_e_map(np.zeros((8, 8, 3)), np.zeros((4, 4, 3)))


def test_delta_e_map_kind_is_checked():
    with pytest.raises(ValueError, match="kind must be"):
        M.delta_e_map(np.zeros((8, 8, 3)), np.zeros((8, 8, 3)), kind="1994")
