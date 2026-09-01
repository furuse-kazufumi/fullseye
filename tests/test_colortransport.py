# -*- coding: utf-8 -*-
"""「分布を運ぶ」op の検査。

:mod:`imgmetrics` が測る側なら、こちらは直す側。同じく **外部・解析的な基準**に
突き合わせる形にしてある:

* 1 次元の最適輸送 → ``scipy.optimize.linear_sum_assignment`` の総当たり解
* 2-Wasserstein → ガウス分布の閉じた式 ``sqrt((m1-m2)^2 + (s1-s2)^2)``
* Poisson 合成 → **出力だけから確かめられる 2 つの不変量**
  (内部のラプラシアンが元と一致 / マスク外は貼り先と厳密一致)
* Sinkhorn → 正則化を弱めると厳密解へ近づくこと

加えて、この族が**黙って間違う**場所(Reinhard の単峰仮定、チャネルごとの
ヒストグラム整合が相関を壊すこと、Sinkhorn の距離の偏り)を、
「そういう結果になる」テストとして残す。
"""
from __future__ import annotations

import numpy as np
import pytest
from scipy import ndimage
from scipy.optimize import linear_sum_assignment

import colortransport as CT


def _normal_quantiles(n, mu, sigma):
    """決定論的な正規標本(分位点そのもの)。乱数の揺らぎを消すため。"""
    from scipy.stats import norm
    return mu + sigma * norm.ppf((np.arange(n) + 0.5) / n)


# =========================================================================
# 1 次元の最適輸送 —— 総当たり解との厳密一致
# =========================================================================

@pytest.mark.parametrize("n", [5, 20, 50])
def test_wasserstein_1d_matches_the_brute_force_assignment_exactly(n):
    """1 次元は並べ替えるだけで最適 ―― 総当たりの割当問題と厳密に一致する。

    実測(seed 0):n=5 で差 **0.00e+00**、n=20 で 1.78e-15、n=50 で 1.11e-15。
    """
    rng = np.random.default_rng(0)
    a = rng.normal(0, 1, n)
    b = rng.normal(1, 2, n)
    cost = np.abs(a[:, None] - b[None, :])
    r, c = linear_sum_assignment(cost)
    brute = cost[r, c].sum() / n
    assert CT.wasserstein_1d(a, b, p=1) == pytest.approx(brute, abs=1e-12)


def test_w2_matches_the_gaussian_closed_form():
    """ガウスどうしの 2-Wasserstein は ``hypot(m1-m2, s1-s2)``。

    分位点そのものを標本にすると乱数の揺らぎが消え、n を増やすと
    **単調に**閉形式へ寄る。
    """
    closed = float(np.hypot(2.0 - 0.0, 3.0 - 1.0))
    errs = []
    for n in (200, 2000, 20000):
        w2 = CT.wasserstein_1d(_normal_quantiles(n, 0.0, 1.0),
                               _normal_quantiles(n, 2.0, 3.0), p=2)
        errs.append(abs(w2 - closed))
    assert errs[0] > errs[1] > errs[2], errs
    assert errs[-1] < 1e-2, errs


def test_wasserstein_is_zero_for_identical_samples_and_symmetric():
    a = _normal_quantiles(100, 0.0, 1.0)
    assert CT.wasserstein_1d(a, a.copy()) == pytest.approx(0.0, abs=1e-12)
    b = _normal_quantiles(100, 1.0, 2.0)
    assert CT.wasserstein_1d(a, b) == pytest.approx(CT.wasserstein_1d(b, a), abs=1e-12)


def test_wasserstein_handles_samples_of_different_length():
    a = _normal_quantiles(37, 0.0, 1.0)
    b = _normal_quantiles(101, 0.0, 1.0)
    assert CT.wasserstein_1d(a, b) < 0.1


def test_wasserstein_weights_are_normalised_and_shift_the_answer():
    """重みを付けると答えが変わること(受け取って無視していないこと)。"""
    a = np.array([0.0, 1.0])
    b = np.array([0.0, 1.0])
    assert CT.wasserstein_1d(a, b) == pytest.approx(0.0, abs=1e-12)
    heavy = CT.wasserstein_1d(a, b, u_weights=[0.9, 0.1])
    assert heavy > 0.3, heavy


def test_wasserstein_fails_closed():
    with pytest.raises(ValueError, match="non-empty"):
        CT.wasserstein_1d([], [1.0])
    with pytest.raises(ValueError, match="finite"):
        CT.wasserstein_1d([np.nan], [1.0])
    with pytest.raises(ValueError, match=r"p must be"):
        CT.wasserstein_1d([0.0], [1.0], p=0.5)


def test_transport_plan_has_exactly_the_right_marginals():
    """行和・列和は構成上厳密。数値誤差以外でずれない。"""
    a = np.array([3.0, 1.0, 2.0, 5.0])
    b = np.array([0.0, 4.0, 2.0])
    plan = CT.transport_plan_1d(a, b)
    assert plan.shape == (4, 3)
    assert np.allclose(plan.sum(axis=1), 1.0 / 4, atol=1e-12)
    assert np.allclose(plan.sum(axis=0), 1.0 / 3, atol=1e-12)
    assert plan.sum() == pytest.approx(1.0, abs=1e-12)
    assert np.all(plan >= 0.0)


def test_transport_plan_costs_the_same_as_the_closed_form_distance():
    a = _normal_quantiles(24, 0.0, 1.0)
    b = _normal_quantiles(24, 1.5, 2.0)
    plan = CT.transport_plan_1d(a, b)
    cost = np.abs(a[:, None] - b[None, :])
    assert float(np.sum(plan * cost)) == pytest.approx(CT.wasserstein_1d(a, b, p=1), abs=1e-12)


# =========================================================================
# ヒストグラム整合
# =========================================================================

def test_histogram_match_reproduces_the_reference_distribution_exactly():
    """順位を保って参照の分位点に置き換えるだけなので、分布は厳密に一致する。"""
    rng = np.random.default_rng(1)
    src = rng.random((32, 32))
    ref = rng.normal(0.5, 0.2, 1024)
    out = CT.histogram_match(src, ref)
    assert out.shape == src.shape
    assert np.allclose(np.sort(out.ravel()), np.sort(ref), atol=1e-12)


def test_histogram_match_preserves_the_ranking():
    """値は総取り替えでも、明暗の順序は変わらない(単調写像だから)。"""
    rng = np.random.default_rng(2)
    src = rng.random(500)
    out = CT.histogram_match(src, rng.normal(0, 3, 500))
    assert np.array_equal(np.argsort(src, kind="mergesort"),
                          np.argsort(out, kind="mergesort"))


def test_binned_histogram_match_is_an_approximation_not_the_exact_answer():
    """``bins`` を渡すと速いが厳密でなくなる ―― 既定を None にした理由。"""
    rng = np.random.default_rng(3)
    src = rng.random(2000)
    ref = rng.normal(0.5, 0.2, 2000)
    exact = CT.histogram_match(src, ref)
    approx = CT.histogram_match(src, ref, bins=16)
    assert not np.allclose(exact, approx, atol=1e-6)
    assert np.max(np.abs(np.sort(approx) - np.sort(ref))) > 1e-3


def test_histogram_match_fails_closed():
    with pytest.raises(ValueError, match="non-empty"):
        CT.histogram_match(np.zeros(0), np.ones(4))
    with pytest.raises(ValueError, match="finite"):
        CT.histogram_match(np.array([np.inf]), np.ones(4))
    with pytest.raises(ValueError, match="bins must be"):
        CT.histogram_match(np.zeros(4), np.ones(4), bins=1)


# =========================================================================
# 色移し
# =========================================================================

def _two_tone_image(n=48, seed=0):
    """前景と背景がはっきり分かれた**二峰**の絵(Reinhard の仮定が破れる形)。"""
    rng = np.random.default_rng(seed)
    img = np.full((n, n, 3), 0.1) + 0.02 * rng.standard_normal((n, n, 3))
    img[n // 3: 2 * n // 3, n // 3: 2 * n // 3] = 0.9 + 0.02 * rng.standard_normal(
        (n - 2 * (n // 3) + (n // 3) - (n // 3), n - 2 * (n // 3) + (n // 3) - (n // 3), 3))
    return np.clip(img, 0, 1)


def test_gaussian_transfer_reproduces_the_reference_moments():
    """共分散ごと運ぶので、平均も共分散も参照に一致する(標本の範囲で)。"""
    rng = np.random.default_rng(4)
    src = np.clip(rng.random((64, 64, 3)) * 0.4 + 0.1, 0, 1)
    ref = np.clip(rng.random((64, 64, 3)) * 0.3 + 0.6, 0, 1)
    out = CT.color_transfer(src, ref, method="gaussian", space="rgb")
    a = out.reshape(-1, 3)
    b = ref.reshape(-1, 3)
    assert np.allclose(a.mean(axis=0), b.mean(axis=0), atol=2e-2)
    assert np.allclose(np.cov(a, rowvar=False), np.cov(b, rowvar=False), atol=5e-3)


def test_histogram_transfer_matches_the_marginals_but_breaks_the_correlation():
    """周辺分布は完璧に合うのに、チャネル間の相関は壊れる ―― 実測で示す。

    これが「各軸を別々に合わせる」やり方の代償で、例外は出ない。
    """
    rng = np.random.default_rng(5)
    n = 4096
    # 強く相関した元(R が上がれば G も上がる)
    t = rng.random(n)
    src = np.clip(np.stack([t, t * 0.9 + 0.05, 1.0 - t], axis=1), 0, 1).reshape(64, 64, 3)
    # 相関のない参照
    ref = rng.random((64, 64, 3))

    out = CT.color_transfer(src, ref, method="histogram", space="rgb")
    a = out.reshape(-1, 3)
    b = ref.reshape(-1, 3)
    for c in range(3):                                  # 周辺分布は一致
        assert np.allclose(np.sort(a[:, c]), np.sort(b[:, c]), atol=1e-6)

    src_rg = float(np.corrcoef(src.reshape(-1, 3)[:, 0], src.reshape(-1, 3)[:, 1])[0, 1])
    out_rg = float(np.corrcoef(a[:, 0], a[:, 1])[0, 1])
    ref_rg = float(np.corrcoef(b[:, 0], b[:, 1])[0, 1])
    assert src_rg > 0.99                                # 元は強い相関
    assert abs(ref_rg) < 0.1                            # 参照には相関が無い
    assert out_rg > 0.9, out_rg                         # 出力は元の相関を引きずる


def test_reinhard_fits_the_moments_but_not_the_distribution():
    """二峰の絵に単峰の仮定を当てると、**統計は合うのに分布は合わない**。

    平均と標準偏差は参照にぴたりと寄る。にもかかわらず分布そのものは遠い
    ―― 距離は自前の厳密な :func:`wasserstein_1d` で測る。同じ 2 枚に
    ヒストグラム整合を掛ければ距離はほぼ 0 になるので、**差は手法の仮定に
    由来する**と言い切れる。例外は一切出ない。
    """
    src = _two_tone_image(seed=6)
    rng = np.random.default_rng(7)
    ref = np.clip(0.5 + 0.05 * rng.standard_normal((48, 48, 3)), 0, 1)   # 単峰

    rein = CT.color_transfer(src, ref, method="reinhard", space="rgb").reshape(-1, 3)
    hist = CT.color_transfer(src, ref, method="histogram", space="rgb").reshape(-1, 3)
    b = ref.reshape(-1, 3)

    # 統計は合う(これが「うまくいった」ように見える理由)
    assert np.allclose(rein.mean(axis=0), b.mean(axis=0), atol=2e-2)
    assert np.allclose(rein.std(axis=0), b.std(axis=0), atol=2e-2)

    # しかし分布は遠い。ヒストグラム整合なら同じ 2 枚でほぼ 0 まで詰まる。
    d_rein = CT.wasserstein_1d(rein[:, 0], b[:, 0])
    d_hist = CT.wasserstein_1d(hist[:, 0], b[:, 0])
    assert d_hist < 1e-6, d_hist
    assert d_rein > 20 * max(d_hist, 1e-9), (d_rein, d_hist)
    assert d_rein > 0.02, d_rein


def test_reinhard_refuses_a_constant_channel():
    src = np.zeros((16, 16, 3))
    ref = np.random.default_rng(8).random((16, 16, 3))
    with pytest.raises(ValueError, match="no spread"):
        CT.color_transfer(src, ref, method="reinhard", space="rgb")


def test_gaussian_map_refuses_a_singular_covariance():
    """疑似逆で誤魔化すと「運べていないのに運んだ顔をした」写像になる。"""
    flat = np.stack([np.linspace(0, 1, 50)] * 3, axis=1)        # 3 軸が完全に相関
    ref = np.random.default_rng(9).random((50, 3))
    with pytest.raises(ValueError, match="singular"):
        CT.gaussian_transport_map(flat, ref)


def test_color_transfer_checks_its_arguments():
    img = np.random.default_rng(10).random((8, 8, 3))
    with pytest.raises(ValueError, match="method must be"):
        CT.color_transfer(img, img, method="mkl")
    with pytest.raises(ValueError, match="space must be"):
        CT.color_transfer(img, img, space="hsv")
    with pytest.raises(ValueError, match="3 channels"):
        CT.color_transfer(np.zeros((8, 8)), img)


def test_color_transfer_works_through_lab_by_default():
    rng = np.random.default_rng(11)
    src = np.clip(rng.random((32, 32, 3)) * 0.4, 0, 1)
    ref = np.clip(rng.random((32, 32, 3)) * 0.4 + 0.5, 0, 1)
    out = CT.color_transfer(src, ref)
    assert out.shape == src.shape
    assert out.min() >= 0.0 and out.max() <= 1.0
    assert out.mean() > src.mean()               # 明るい参照に寄っている


# =========================================================================
# Sinkhorn —— 厳密でないことを明示する
# =========================================================================

def test_sinkhorn_approaches_the_exact_answer_as_the_regularisation_falls():
    a_s = np.linspace(0.0, 1.0, 24)
    b_s = np.linspace(0.4, 2.0, 24)
    cost = np.abs(a_s[:, None] - b_s[None, :])
    a = np.full(24, 1.0 / 24)
    exact = CT.wasserstein_1d(a_s, b_s, p=1)
    errs = [abs(CT.sinkhorn_distance(a, a.copy(), cost, reg=r) - exact)
            for r in (0.5, 0.1, 0.02)]
    assert errs[0] > errs[1] > errs[2], errs
    assert errs[-1] < 0.05, errs


def test_sinkhorn_plan_has_the_requested_marginals():
    rng = np.random.default_rng(12)
    a = rng.random(12); a /= a.sum()
    b = rng.random(9); b /= b.sum()
    cost = rng.random((12, 9))
    plan = CT.sinkhorn(a, b, cost, reg=0.1)
    assert np.allclose(plan.sum(axis=1), a, atol=1e-6)
    assert np.allclose(plan.sum(axis=0), b, atol=1e-6)


def test_sinkhorn_distance_to_itself_is_not_zero_because_of_the_bias():
    """正則化のぶん偏るので、自分自身との「距離」も 0 にならない。

    厳密が要る 1 次元では ``wasserstein_1d`` を使うべき、という根拠。
    """
    a_s = np.linspace(0.0, 1.0, 20)
    cost = np.abs(a_s[:, None] - a_s[None, :])
    a = np.full(20, 1.0 / 20)
    assert CT.wasserstein_1d(a_s, a_s.copy()) == pytest.approx(0.0, abs=1e-12)
    biased = CT.sinkhorn_distance(a, a.copy(), cost, reg=0.2)
    assert biased > 0.05, biased


def test_sinkhorn_refuses_a_regularisation_that_underflows():
    """支持が離れていて ``exp(-cost/reg)`` が全滅する場合。"""
    a_s = np.linspace(0.0, 1.0, 8)
    b_s = np.linspace(1000.0, 1001.0, 8)
    cost = np.abs(a_s[:, None] - b_s[None, :])
    a = np.full(8, 0.125)
    with pytest.raises(ValueError, match="underflowed"):
        CT.sinkhorn(a, a.copy(), cost, reg=1e-4)


def test_sinkhorn_refuses_when_only_some_rows_underflow():
    """**「全体が 0 か」だけを見る検査では足りない**ことを固定する。

    対角だけが生き残るような場合、行列全体としては非零の要素があるので
    素朴な検査は通ってしまう。しかし質量のある行が 1 つでも全滅すると、
    その質量の行き先が無くなり、割り算の下駄で**でたらめな計画が黙って返る**。
    最初に書いた検査はここを取りこぼしていた(2026-09-02 に実測で判明し、
    行・列ごとに見る形へ直した)。
    """
    cost = np.array([
        [0.0, 100.0, 100.0],
        [100.0, 0.0, 100.0],
        [100.0, 100.0, 0.0],
    ])
    # 全体としては非零(対角が 1.0)なので「どこかに正の値がある」検査は通る
    K = np.exp(-cost / 1e-3)
    assert np.any(K > 0) and np.count_nonzero(K) == 3

    # 質量の配り方をずらすと、対角だけでは要求された周辺分布を作れない。
    # 反復は「収束」する(u が動かなくなる)が、答えは要求を満たしていない。
    # 入力側の検査では通ってしまうので、**出した計画を測ってから返す**。
    a = np.array([0.6, 0.2, 0.2])
    b = np.array([0.2, 0.2, 0.6])
    with pytest.raises(RuntimeError, match="marginals are off by"):
        CT.sinkhorn(a, b, cost, reg=1e-3, n_iter=5000, tol=1e-12)


def test_converging_is_not_the_same_as_converging_to_the_right_answer():
    """上のケースが「発散」ではなく「間違った答えへの収束」であることの確認。

    反復が止まらないなら既存の未収束チェックで捕まる。実際に危ないのは
    **止まるのに答えが違う**場合で、それは出力を測らないと分からない。
    """
    cost = np.array([[0.0, 100.0], [100.0, 0.0]])
    a = np.array([0.9, 0.1])
    b = np.array([0.1, 0.9])
    with pytest.raises(RuntimeError) as exc:
        CT.sinkhorn(a, b, cost, reg=1e-3, n_iter=100000, tol=1e-12)
    assert "did not converge" not in str(exc.value)      # 未収束ではない
    assert "marginals are off by" in str(exc.value)


def test_sinkhorn_raises_rather_than_returning_an_unconverged_plan():
    rng = np.random.default_rng(13)
    a = rng.random(10); a /= a.sum()
    b = rng.random(10); b /= b.sum()
    cost = rng.random((10, 10))
    with pytest.raises(RuntimeError, match="did not converge"):
        CT.sinkhorn(a, b, cost, reg=0.01, n_iter=2, tol=1e-15)


def test_sinkhorn_checks_the_marginals():
    a = np.full(4, 0.25)
    with pytest.raises(ValueError, match="equal mass"):
        CT.sinkhorn(a, np.full(4, 0.5), np.zeros((4, 4)))
    with pytest.raises(ValueError, match="non-negative"):
        CT.sinkhorn(np.array([-1.0, 2.0]), np.array([0.5, 0.5]), np.zeros((2, 2)))
    with pytest.raises(ValueError, match="cost must be"):
        CT.sinkhorn(a, a.copy(), np.zeros((3, 3)))


# =========================================================================
# Poisson 合成 —— 出力だけから正しさを確かめる
# =========================================================================

_LAPLACIAN = np.array([[0.0, -1.0, 0.0], [-1.0, 4.0, -1.0], [0.0, -1.0, 0.0]])


def test_poisson_blend_keeps_the_source_laplacian_inside():
    """構成上の不変量その 1 ―― 内部のラプラシアンが元の勾配場と一致する。

    実測(40x50 の src、24x30 のマスク):最大差 **1.78e-15**、
    線形系の残差も **1.78e-15**。
    """
    rng = np.random.default_rng(14)
    src = rng.random((40, 50))
    dst = rng.random((60, 70))
    mask = np.zeros((40, 50), bool)
    mask[8:32, 10:40] = True

    out, info = CT.poisson_blend(src, dst, mask, offset=(10, 12))
    assert info["residual"] < 1e-10, info
    window = out[10:50, 12:62]
    inner = ndimage.binary_erosion(mask)
    lap_out = ndimage.convolve(window, _LAPLACIAN, mode="nearest")
    lap_src = ndimage.convolve(src, _LAPLACIAN, mode="nearest")
    assert np.max(np.abs(lap_out[inner] - lap_src[inner])) < 1e-10


def test_poisson_blend_leaves_everything_outside_the_mask_bit_identical():
    """構成上の不変量その 2 ―― マスク外は 1 画素も触らない。"""
    rng = np.random.default_rng(15)
    src = rng.random((40, 50))
    dst = rng.random((60, 70))
    mask = np.zeros((40, 50), bool)
    mask[8:32, 10:40] = True

    out, _ = CT.poisson_blend(src, dst, mask, offset=(10, 12))
    restored = out.copy()
    restored[10:50, 12:62][mask] = dst[10:50, 12:62][mask]
    assert np.array_equal(restored, dst)


def test_poisson_blend_reports_how_far_it_moved_the_pixels():
    """貼った物の色は変わる ―― どれだけ動いたかを返り値で言うこと。"""
    rng = np.random.default_rng(16)
    src = np.full((30, 30), 0.9) + 0.01 * rng.standard_normal((30, 30))
    dst = np.full((50, 50), 0.1)
    mask = np.zeros((30, 30), bool)
    mask[5:25, 5:25] = True
    out, info = CT.poisson_blend(src, dst, mask, offset=(10, 10))
    assert info["solved_pixels"] == 400
    assert info["changed_pixels"] == 400
    # 明るい物を暗い場所に貼ると、内部は貼り先の明るさへ引き寄せられる
    assert out[15:35, 15:35].mean() < 0.3, out[15:35, 15:35].mean()


def test_poisson_blend_handles_colour():
    rng = np.random.default_rng(17)
    src = rng.random((30, 30, 3))
    dst = rng.random((50, 50, 3))
    mask = np.zeros((30, 30), bool)
    mask[5:25, 5:25] = True
    out, info = CT.poisson_blend(src, dst, mask, offset=(10, 10))
    assert out.shape == dst.shape
    assert info["residual"] < 1e-10


def test_poisson_blend_refuses_a_mask_that_touches_the_edge():
    """境界条件が取れない ―― 黙って内側に丸めると別の問題を解くことになる。"""
    src = np.zeros((20, 20))
    dst = np.zeros((40, 40))
    mask = np.ones((20, 20), bool)
    with pytest.raises(ValueError, match="touches the edge"):
        CT.poisson_blend(src, dst, mask)


def test_poisson_blend_fails_closed():
    src = np.zeros((20, 20))
    dst = np.zeros((40, 40))
    mask = np.zeros((20, 20), bool)
    with pytest.raises(ValueError, match="no pixels"):
        CT.poisson_blend(src, dst, mask)
    mask[5:10, 5:10] = True
    with pytest.raises(ValueError, match="does not fit inside"):
        CT.poisson_blend(src, dst, mask, offset=(30, 30))
    with pytest.raises(ValueError, match="mask must be"):
        CT.poisson_blend(src, dst, np.zeros((10, 10), bool))
    with pytest.raises(ValueError, match="finite"):
        CT.poisson_blend(np.full((20, 20), np.nan), dst, mask)


# =========================================================================
# TRIZ による点検で見つかった欠陥と、その解(2026-09-02)
# =========================================================================

def test_histogram_match_maps_equal_inputs_to_equal_outputs():
    """単調写像なら「等しい入力は等しい出力」―― 素朴な実装はこれを破る。

    実測(値 2 が 4 画素ある整数画像):``ties="break"`` では出力が
    ``0.2222 / 0.3333 / 0.4444 / 0.5556`` の 4 つに分かれる。つまり
    **平坦だった領域に、元の絵に無い濃淡が生える**。整数画像は同値だらけ
    なので、これは例外ではなく常態。
    """
    src = np.array([[3, 3, 3, 1, 1, 2, 2, 2, 2, 5]], dtype=np.uint8)
    ref = np.linspace(0.0, 1.0, 10)

    avg = CT.histogram_match(src, ref)                      # 既定
    for v in np.unique(src):
        assert len(np.unique(avg[src == v])) == 1, v

    brk = CT.histogram_match(src, ref, ties="break")
    assert len(np.unique(brk[src == 2])) == 4               # 4 画素が 4 値に割れる
    assert np.allclose(np.sort(np.unique(brk[src == 2])),
                       [0.2222, 0.3333, 0.4444, 0.5556], atol=1e-3)


def test_the_two_tie_policies_each_give_something_up():
    """どちらを選んでも失うものがある ―― だから黙って決めず引数にした。

    * ``ties="break"`` は**分布が参照と厳密一致**するが、平坦部が割れる。
    * ``ties="average"`` は**平坦部を守る**が、分布は階段状に丸まる。
    """
    rng = np.random.default_rng(20)
    src = (rng.random((32, 32)) * 8).astype(np.uint8)       # 同値だらけ
    ref = rng.normal(0.5, 0.2, 1024)

    brk = CT.histogram_match(src, ref, ties="break")
    avg = CT.histogram_match(src, ref, ties="average")

    assert np.allclose(np.sort(brk.ravel()), np.sort(ref), atol=1e-12)   # 厳密一致
    assert not np.allclose(np.sort(avg.ravel()), np.sort(ref), atol=1e-3)
    assert len(np.unique(avg)) == len(np.unique(src))        # 値の種類は入力どおり
    assert len(np.unique(brk)) > len(np.unique(src))         # 増えている


def test_continuous_input_is_unaffected_by_the_tie_policy():
    """同値が無ければ両者は一致する(既定を変えても連続入力の結果は不変)。"""
    rng = np.random.default_rng(21)
    src = rng.random((16, 16))
    ref = rng.normal(0.5, 0.2, 256)
    assert np.allclose(CT.histogram_match(src, ref),
                       CT.histogram_match(src, ref, ties="break"), atol=1e-12)


def test_ties_argument_is_checked():
    with pytest.raises(ValueError, match="ties must be"):
        CT.histogram_match(np.zeros(4), np.ones(4), ties="first")


def test_sinkhorn_divergence_cancels_its_own_bias():
    """正則化の偏りを、自分自身との距離から引いて打ち消す。

    実測(20 点・reg=0.2):``sinkhorn_distance`` の自己距離は **0.151611**、
    ``sinkhorn_divergence`` は **0.0**。
    """
    s = np.linspace(0.0, 1.0, 20)
    cost = np.abs(s[:, None] - s[None, :])
    w = np.full(20, 1.0 / 20)

    assert CT.sinkhorn_distance(w, w.copy(), cost, reg=0.2) == pytest.approx(0.151611, abs=1e-4)
    assert CT.sinkhorn_divergence(w, w.copy(), cost, reg=0.2) == pytest.approx(0.0, abs=1e-9)


def test_sinkhorn_divergence_still_separates_different_distributions():
    a_s = np.linspace(0.0, 1.0, 20)
    b_s = np.linspace(0.6, 1.6, 20)
    cost = np.abs(a_s[:, None] - b_s[None, :])
    caa = np.abs(a_s[:, None] - a_s[None, :])
    cbb = np.abs(b_s[:, None] - b_s[None, :])
    w = np.full(20, 1.0 / 20)
    d = CT.sinkhorn_divergence(w, w.copy(), cost, cost_aa=caa, cost_bb=cbb, reg=0.05)
    assert d > 0.4, d
    assert d == pytest.approx(CT.wasserstein_1d(a_s, b_s), abs=0.1)


def test_sinkhorn_divergence_refuses_to_guess_the_self_costs():
    """非正方の費用行列から自己費用を勝手に作ると、引く量が別物になる。"""
    a = np.full(4, 0.25)
    b = np.full(6, 1.0 / 6)
    with pytest.raises(ValueError, match="cannot be inferred"):
        CT.sinkhorn_divergence(a, b, np.ones((4, 6)))


def test_transport_plan_now_has_consumers():
    """袋小路の解消 ―― 作るだけで使い道が無い型を残さない。"""
    u = np.array([0.0, 1.0, 2.0, 3.0])
    v = np.array([10.0, 11.0, 12.0, 13.0])
    plan = CT.transport_plan_1d(u, v)

    # 同じ長さ・同じ順序なので計画は対角。重心写像は行き先をそのまま返す
    assert np.allclose(CT.apply_transport(plan, v), v)
    assert CT.transport_cost(plan, np.abs(u[:, None] - v[None, :])) == pytest.approx(10.0, abs=1e-12)
    assert CT.transport_cost(plan, np.abs(u[:, None] - v[None, :])) == pytest.approx(
        CT.wasserstein_1d(u, v), abs=1e-12)


def test_apply_transport_handles_vector_valued_targets():
    u = np.array([0.0, 1.0, 2.0])
    v = np.array([5.0, 6.0, 7.0])
    plan = CT.transport_plan_1d(u, v)
    colours = np.stack([v, v * 2, v * 3], axis=1)
    out = CT.apply_transport(plan, colours)
    assert out.shape == (3, 3)
    assert np.allclose(out[:, 1], out[:, 0] * 2)


def test_apply_transport_refuses_a_row_with_no_mass():
    """行き先の無い送り元を 0 で埋めると、黒が黙って混ざる。"""
    plan = np.array([[0.5, 0.0], [0.0, 0.0]])
    with pytest.raises(ValueError, match="no mass"):
        CT.apply_transport(plan, np.array([1.0, 2.0]))


def test_transport_cost_checks_that_it_was_handed_a_plan():
    with pytest.raises(ValueError, match="negative mass"):
        CT.transport_cost(np.array([[-0.5, 0.5]]), np.zeros((1, 2)))
    with pytest.raises(ValueError, match="same shape"):
        CT.transport_cost(np.zeros((2, 3)), np.zeros((3, 2)))
