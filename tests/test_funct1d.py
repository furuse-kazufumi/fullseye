# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""funct1d のGTテスト: HALCON funct_1d ファミリ 23 関数を解析的グラウンドトゥルースで検証。

各テストは「数学的に答えが分かっている入力」を使う(sin の微分は cos、微分の積分は
元関数-初期値、sin のゼロ交差は kπ、既知シフトの復元 等)。fail-closed 検証
(NaN / 2-D / 空 / 不正パラメータ → ValueError)も全経路をカバーする。
"""
import numpy as np
import pytest

import funct1d as F


# --------------------------------------------------------------------------- #
# analytic ground truth
# --------------------------------------------------------------------------- #

def test_derivate_of_sin_is_cos():
    dt = 0.01
    t = np.arange(0, 4 * np.pi, dt)
    d = F.derivate_funct_1d(np.sin(t)) / dt          # per-sample -> per-radian
    assert np.max(np.abs(d - np.cos(t))) < 1e-3      # 位相も振幅も合う(中心差分 O(h^2))


def test_integrate_of_derivate_recovers_signal():
    t = np.linspace(0, 6, 500)
    y = np.sin(t) + 0.3 * t ** 2
    rec = F.integrate_funct_1d(F.derivate_funct_1d(y))
    assert np.max(np.abs(rec - (y - y[0]))) < 5e-3   # ∫f' = f - f(0)


def test_integrate_constant_is_linear_ramp():
    out = F.integrate_funct_1d(np.full(11, 2.0))
    assert np.allclose(out, 2.0 * np.arange(11))     # ∫2 dx = 2x(台形則は定数で厳密)
    assert out[0] == 0.0


def test_zero_crossings_of_sin_at_k_pi():
    dt = 0.01
    t = np.arange(0.5, 12.0, dt)                     # 0.5..12 rad: kπ = π, 2π, 3π
    idx = F.zero_crossings_funct_1d(np.sin(t))
    got = t[idx]
    expected = np.array([np.pi, 2 * np.pi, 3 * np.pi])
    assert len(got) == 3
    assert np.max(np.abs(got - expected)) < dt + 1e-12


def test_local_min_max_of_sin():
    dt = 0.01
    t = np.arange(0.2, 12.0, dt)                     # 極大 π/2, 5π/2, 7π/2? -> π/2+2kπ
    ext = F.local_min_max_funct_1d(np.sin(t))
    maxima, minima = t[ext["max"]], t[ext["min"]]
    assert np.max(np.abs(maxima - np.array([np.pi / 2, np.pi / 2 + 2 * np.pi]))) < 2 * dt
    assert np.max(np.abs(minima - np.array([3 * np.pi / 2, 3 * np.pi / 2 + 2 * np.pi]))) < 2 * dt


def test_smooth_gauss_preserves_dc_and_shrinks_variance():
    rng = np.random.default_rng(0)
    y = 5.0 + rng.normal(0, 1, 4000)
    sm = F.smooth_funct_1d_gauss(y, sigma=3.0)
    assert abs(sm.mean() - y.mean()) < 0.01                      # DC 保存
    assert np.var(sm - 5.0) < 0.25 * np.var(y - 5.0)             # 分散縮小
    # 理論: var 比 ~ 1/(2σ√π) ≈ 0.094 (σ=3)
    assert np.var(sm - 5.0) / np.var(y - 5.0) == pytest.approx(1 / (2 * 3.0 * np.sqrt(np.pi)), rel=0.3)


def test_smooth_mean_iterated_shrinks_variance_monotonically():
    rng = np.random.default_rng(1)
    y = rng.normal(0, 1, 2000)
    v1 = np.var(F.smooth_funct_1d_mean(y, size=5, iterations=1))
    v3 = np.var(F.smooth_funct_1d_mean(y, size=5, iterations=3))
    assert v1 == pytest.approx(1 / 5, rel=0.2)                   # box 平均の分散 = σ²/size
    assert v3 < v1 < np.var(y)
    # iterations=0 は入力そのまま
    assert np.array_equal(F.smooth_funct_1d_mean(y, size=5, iterations=0), y)


def test_compose_exact_chain():
    y1 = np.array([10.0, 20.0, 30.0, 40.0])
    y2 = np.array([0.0, 3.0, 1.0, 2.0, 2.4])
    out = F.compose_funct_1d(y1, y2)
    assert np.array_equal(out, [10.0, 40.0, 20.0, 30.0, 30.0])   # 丸め+参照が厳密
    # 域外はクランプ(文書化済みポリシー)
    assert np.array_equal(F.compose_funct_1d(y1, [-5.0, 99.0]), [10.0, 40.0])


def test_match_funct_1d_trans_recovers_known_shift_and_is_scale_invariant():
    t = np.linspace(0, 8 * np.pi, 400)
    y1 = np.sin(t) * np.exp(-t / 20)
    for s in (7, -5, 0):
        y2 = np.roll(y1, s)                                      # y2[i] = y1[i-s]
        r = F.match_funct_1d_trans(y1, y2)
        assert r["shift"] == -s                                  # 規約: y1[i] ~= y2[i - shift]
        assert r["score"] > 0
    # 正のスケール+オフセットに shift は不変
    r = F.match_funct_1d_trans(y1, 3.0 * np.roll(y1, 7) + 2.0)
    assert r["shift"] == -7


def _four_peak_record_and_one_peak_template(n=400, centres=(60, 150, 245, 330), width=9.0):
    """4 山の記録と、その 1 山だけを持つ**同じ長さ**のテンプレート。

    テンプレートの山は既に centres[0] にあるので、正解の shift は測る前から 0。
    山の間隔は最小 85 サンプル ≒ 9.4σ なので、山同士の交差項は exp(-22) ≈ 1e-10 ――
    「テンプレートの山をどの記録の山に載せるか」の 4 通りは数学的に等価である。
    """
    idx = np.arange(n, dtype=float)
    rec = np.zeros(n)
    for c in centres:
        rec += np.exp(-0.5 * ((idx - c) / width) ** 2)
    tmpl = np.exp(-0.5 * ((idx - float(centres[0])) / width) ** 2)
    return rec, tmpl


def test_match_funct_1d_trans_is_not_fooled_by_a_shrinking_overlap():
    """同じ長さの入力で、短い重なりを持つ端の lag が勝ってしまう回帰の門。

    旧実装(重なりだけの非正規化相関和)は shift=270 / score=11.2403 を返した ――
    例外も NaN も無く、もっともらしい数字で。重なりは lag 0 で 400、lag 270 で
    130 しかなく、和は打ち切られた分だけ罰を免れる。文書の「長さの違う候補を
    比べるな」は効かない: この入力は**同じ長さ**である。
    """
    rec, tmpl = _four_peak_record_and_one_peak_template()
    r = F.match_funct_1d_trans(rec, tmpl)
    assert r["shift"] == 0                       # 旧実装は 270(実測)
    assert 0.0 <= r["score"] <= 1.0              # 旧 score は 11.2403 = 係数ではない
    assert r["score"] == pytest.approx(0.430110, abs=1e-6)   # 実測 0.4301102692709698

    # 4 通りの重ね方は等価 —— 測る前から分かっている対称性を数値で確認する。
    lags, scores = F._match_scores(rec - rec.mean(), tmpl - tmpl.mean())
    four = np.array([scores[int(np.where(lags == L)[0][0])] for L in (0, 90, 185, 270)])
    assert four.max() - four.min() < 1e-9        # 実測の広がり 2.804e-10
    assert four.max() == pytest.approx(r["score"], abs=F._MATCH_TIE_ATOL)
    # 同点でないものはきちんと離れている(隣の lag 269 は実測 0.428164)
    others = scores[~np.isin(lags, (0, 90, 185, 270))]
    assert others.max() < four.min() - 1e-3


def test_match_score_is_a_correlation_coefficient():
    """score の意味の固定: 固定窓上の Pearson 係数 ―― [-1,1]、振幅にも長さにも依らない。"""
    t = np.linspace(0, 8 * np.pi, 400)
    y1 = np.sin(t) * np.exp(-t / 20)

    # 自分自身は厳密に 1.0(係数の定義そのもの)
    assert F.match_funct_1d_trans(y1, y1) == {"shift": 0, "score": 1.0}
    # 正のアフィン変換 (a*y+b, a>0) で score も shift も不変
    plain = F.match_funct_1d_trans(y1, np.roll(y1, 7))
    scaled = F.match_funct_1d_trans(y1, 1000.0 * np.roll(y1, 7) - 4.0)
    assert scaled["shift"] == plain["shift"] == -7
    assert scaled["score"] == pytest.approx(plain["score"], rel=1e-9)
    # y1 側の振幅にも依らない(旧 score は振幅と重なり長で青天井に伸びた)
    assert F.match_funct_1d_trans(0.001 * y1, np.roll(y1, 7))["score"] == \
        pytest.approx(plain["score"], rel=1e-9)
    assert plain["score"] == pytest.approx(0.999704, abs=1e-6)   # 実測 0.9997035437

    # 全 lag が [-1,1] に入り、NaN は 1 つも無い
    lags, scores = F._match_scores(y1 - y1.mean(), np.roll(y1, 7) - y1.mean())
    assert np.all(np.isfinite(scores)) and scores.min() >= -1.0 and scores.max() <= 1.0

    # 同点は最小の |shift| に倒す(周期 100 の正弦は lag 0,±100,±200,... が厳密同点。
    # 旧実装は argmax が最初の同点 = 最も負の lag を拾った)
    per = np.sin(np.arange(400) * 2 * np.pi / 100.0)
    assert F.match_funct_1d_trans(per, per) == {"shift": 0, "score": 1.0}


def test_match_never_scores_a_degenerate_window():
    """縮退窓の門: 重なりだけで正規化する実装が壊れる入力を、係数のまま拒む。

    重なり 2 サンプルの Pearson は必ず ±1 になる(2 点は必ず直線に乗る)。窓を
    y1 の定義域に固定し y2 を端値で延長することで、この縮退そのものが起きない。
    """
    rec, tmpl = _four_peak_record_and_one_peak_template()

    # 2 サンプルだけのテンプレート: 重なり正規化なら必ず |r| = 1 が出る入力
    two = tmpl[55:57]
    lags, scores = F._match_scores(rec - rec.mean(), two - two.mean())
    assert np.all(np.isfinite(scores))
    assert np.abs(scores).max() < 0.5            # 実測 0.2515(重なり正規化なら 1.0)
    assert abs(F.match_funct_1d_trans(rec, two)["score"]) < 0.5

    # y2 を窓の外へ完全に押し出す lag は「形が無い」= 厳密に 0.0
    assert scores[0] == 0.0 and scores[-1] == 0.0

    # 定数入力は分散が無い → shift 0 / score 0.0、NaN は返さない
    const = np.ones(50)
    wave = np.sin(np.arange(50) / 3.0)
    for a, b in ((const, wave), (wave, const), (const, const)):
        r = F.match_funct_1d_trans(a, b)
        assert r == {"shift": 0, "score": 0.0}


def test_match_scores_equal_the_direct_per_lag_definition():
    """prefix-sum のベクトル化が、lag ごとに窓を作る素朴な定義と一致すること。"""
    def direct(a, b):
        n1, n2 = a.size, b.size
        out = []
        for L in range(-(n2 - 1), n1):
            v = b[np.clip(np.arange(n1) - L, 0, n2 - 1)]
            uc, vc = a - a.mean(), v - v.mean()
            nu, nv = np.linalg.norm(uc), np.linalg.norm(vc)
            out.append(0.0 if nu == 0 or nv <= 1e-12 * np.linalg.norm(v)
                       else float(uc @ vc / (nu * nv)))
        return np.array(out)

    rng = np.random.default_rng(11)
    worst = 0.0
    for _ in range(12):
        n1, n2 = int(rng.integers(1, 60)), int(rng.integers(1, 60))
        a = rng.normal(0, rng.uniform(0.1, 50), n1) + rng.uniform(-1e3, 1e3)
        b = rng.normal(0, rng.uniform(0.1, 50), n2) + rng.uniform(-1e3, 1e3)
        _, fast = F._match_scores(a - a.mean(), b - b.mean())
        worst = max(worst, float(np.max(np.abs(fast - direct(a - a.mean(), b - b.mean())))))
    assert worst < 1e-11                          # 実測 5.769e-14(60 対で最悪)


def test_match_shift_estimate_is_unbiased_across_true_shifts():
    """真の shift が 0 でなくても同じ精度で当たること(旧実装は 0 へ約 0.8 縮んだ)。

    幅 81 の窓とテンプレート、雑音 σ=0.20、独立に 150 回。旧実装の平均推定は
    真値 -5 に対し -4.21、真値 +12 に対し +11.22 ―― 「真値 0 のときだけ良く当たる」
    のは精度ではなく偏りだった(実測 exact 率 0.865 / 0.295 / 0.307)。
    """
    half, width, n = 40, 9.0, 400
    idx = np.arange(n, dtype=float)
    base = np.zeros(n)
    centres = [60, 150, 245, 330]
    for c in centres:
        base += np.exp(-0.5 * ((idx - c) / width) ** 2)
    tmpl = np.exp(-0.5 * ((np.arange(2 * half + 1) - float(half)) / width) ** 2)

    for true_shift in (0, -5, 12):
        got = []
        for seed in range(150):
            y = base + np.random.default_rng(seed).normal(0.0, 0.20, n)
            lo = centres[seed % 4] - half - true_shift
            got.append(F.match_funct_1d_trans(y[lo:lo + 2 * half + 1], tmpl)["shift"])
        bias = float(np.mean(got)) - true_shift
        assert abs(bias) < 0.15, f"true {true_shift}: bias {bias:+.3f} samples"
        assert np.mean(np.abs(np.array(got) - true_shift)) < 0.7   # 実測 ~0.48


def test_distance_symmetry_identity_and_modes():
    a = np.array([1.0, 2.0, 3.0])
    b = np.array([2.0, 2.0, 5.0])
    assert F.distance_funct_1d(a, b, "max") == F.distance_funct_1d(b, a, "max") == 2.0
    assert F.distance_funct_1d(a, b, "mean") == F.distance_funct_1d(b, a, "mean") == 1.0
    assert F.distance_funct_1d(a, a) == 0.0


def test_transform_round_trip_identity():
    y = np.array([1.0, -2.0, 4.0])
    fwd = F.transform_funct_1d(y, mult_x=2.0, add_x=1.0, mult_y=3.0, add_y=-1.0)
    assert np.allclose(fwd[:, 0], [1.0, 3.0, 5.0])
    assert np.allclose(fwd[:, 1], [2.0, -7.0, 11.0])
    # 逆係数で往復恒等
    back = np.column_stack([(fwd[:, 0] - 1.0) / 2.0, (fwd[:, 1] + 1.0) / 3.0])
    ident = F.transform_funct_1d(y)
    assert np.allclose(back, ident)
    assert np.allclose(ident, F.funct_1d_to_pairs(y))            # 恒等変換 = to_pairs


def test_invert_monotonic_is_true_inverse():
    y = np.array([1.0, 3.0, 7.0, 15.0])                          # 単調増加
    inv = F.invert_funct_1d(y)
    assert np.array_equal(inv["x"], y)                           # 新しい x = 元の y
    assert np.array_equal(inv["y"], [0.0, 1.0, 2.0, 3.0])        # 新しい y = 元の index
    # f^-1(f(i)) = i を interp で確認
    assert np.allclose(np.interp(y, inv["x"], inv["y"]), np.arange(4))


def test_scale_abs_negate_algebra():
    y = np.array([-1.0, 0.0, 2.0])
    assert np.array_equal(F.scale_y_funct_1d(y, 2.0, 1.0), [-1.0, 1.0, 5.0])
    assert np.array_equal(F.abs_funct_1d(y), [1.0, 0.0, 2.0])
    assert np.array_equal(F.negate_funct_1d(y), [1.0, 0.0, -2.0])
    assert np.array_equal(F.negate_funct_1d(F.negate_funct_1d(y)), y)   # 二重否定 = 恒等


def test_sample_and_num_points_and_ranges():
    y = np.arange(10.0)
    assert np.array_equal(F.sample_funct_1d(y, 3), [0.0, 3.0, 6.0, 9.0])
    assert np.array_equal(F.sample_funct_1d(y, 1), y)
    assert F.num_points_funct_1d(y) == 10
    assert F.x_range_funct_1d(y) == (0.0, 9.0)
    assert F.y_range_funct_1d(2.0 * y - 3.0) == (-3.0, 15.0)


def test_get_pair_and_get_y_value():
    y = np.array([10.0, 20.0, 30.0])
    assert np.array_equal(F.get_pair_funct_1d(y, 1), [1.0, 20.0])
    assert np.array_equal(F.get_pair_funct_1d(y, -5), [0.0, 10.0])    # クランプ(文書化)
    assert np.array_equal(F.get_pair_funct_1d(y, 99), [2.0, 30.0])
    assert F.get_y_value_funct_1d(y, 0.5) == 15.0                     # 線形補間
    assert F.get_y_value_funct_1d(y, 0.6, interpolate=False) == 20.0  # 最近傍
    assert F.get_y_value_funct_1d(y, -4.0) == 10.0                    # 端でホールド(文書化)
    assert F.get_y_value_funct_1d(y, 99.0) == 30.0


def test_create_array_and_pairs():
    y = [1, 2, 3]
    out = F.create_funct_1d_array(y)
    assert out.dtype == np.float64 and np.array_equal(out, [1.0, 2.0, 3.0])
    # (x,y) 対 → 整数グリッド floor(min)..ceil(max)、線形補間
    g = F.create_funct_1d_pairs([0.0, 2.0], [0.0, 4.0])
    assert np.array_equal(g, [0.0, 2.0, 4.0])
    # 未ソート入力も同じ結果(内部でソート)
    g2 = F.create_funct_1d_pairs([2.0, 0.0], [4.0, 0.0])
    assert np.array_equal(g2, g)


def test_funct_1d_to_pairs_shape_and_content():
    p = F.funct_1d_to_pairs([5.0, 6.0])
    assert p.shape == (2, 2)
    assert np.array_equal(p, [[0.0, 5.0], [1.0, 6.0]])


def test_degenerate_lengths_documented_contract():
    # 空を許す関数: 空を返す
    assert F.zero_crossings_funct_1d([]).size == 0
    ext = F.local_min_max_funct_1d([1.0, 2.0])
    assert ext["max"].size == 0 and ext["min"].size == 0
    assert F.num_points_funct_1d([]) == 0
    assert F.abs_funct_1d([]).size == 0
    assert F.sample_funct_1d([], 2).size == 0
    assert F.funct_1d_to_pairs([]).shape == (0, 2)
    inv = F.invert_funct_1d([])
    assert inv["x"].size == 0 and inv["y"].size == 0
    # 1 点: integrate は [0], smooth は恒等
    assert np.array_equal(F.integrate_funct_1d([7.0]), [0.0])
    assert np.allclose(F.smooth_funct_1d_gauss([7.0], 2.0), [7.0])
    # match の縮退(1 点): shift 0 / score 0(文書化)
    r = F.match_funct_1d_trans([1.0], [5.0])
    assert r["shift"] == 0 and r["score"] == 0.0


# --------------------------------------------------------------------------- #
# fail-closed: 全経路で ValueError
# --------------------------------------------------------------------------- #

_UNARY = [
    F.smooth_funct_1d_gauss, F.smooth_funct_1d_mean, F.derivate_funct_1d,
    F.integrate_funct_1d, F.zero_crossings_funct_1d, F.local_min_max_funct_1d,
    F.funct_1d_to_pairs, F.abs_funct_1d, F.negate_funct_1d, F.scale_y_funct_1d,
    F.num_points_funct_1d, F.sample_funct_1d, F.get_pair_funct_1d,
    F.invert_funct_1d, F.transform_funct_1d, F.x_range_funct_1d,
    F.y_range_funct_1d, F.create_funct_1d_array,
]


@pytest.mark.parametrize("fn", _UNARY, ids=lambda f: f.__name__)
def test_unary_rejects_nan_and_2d(fn):
    with pytest.raises(ValueError):
        fn(np.array([1.0, np.nan, 3.0]))
    with pytest.raises(ValueError):
        fn(np.array([1.0, np.inf, 3.0]))
    with pytest.raises(ValueError):
        fn(np.ones((2, 3)))


def test_binary_rejects_nan_and_2d():
    good = np.array([1.0, 2.0, 3.0])
    bad_nan = np.array([1.0, np.nan, 3.0])
    bad_2d = np.ones((2, 3))
    for fn in (F.compose_funct_1d, F.distance_funct_1d,
               F.create_funct_1d_pairs, F.match_funct_1d_trans):
        for a, b in ((bad_nan, good), (good, bad_nan), (bad_2d, good), (good, bad_2d)):
            with pytest.raises(ValueError):
                fn(a, b)
    with pytest.raises(ValueError):
        F.get_y_value_funct_1d(bad_nan, 1.0)
    with pytest.raises(ValueError):
        F.get_y_value_funct_1d(bad_2d, 1.0)


def test_empty_rejected_where_data_is_required():
    for fn in (F.smooth_funct_1d_gauss, F.smooth_funct_1d_mean,
               F.integrate_funct_1d, F.x_range_funct_1d, F.y_range_funct_1d):
        with pytest.raises(ValueError):
            fn([])
    with pytest.raises(ValueError):
        F.derivate_funct_1d([1.0])                    # 微分は n>=2
    with pytest.raises(ValueError):
        F.derivate_funct_1d([])
    with pytest.raises(ValueError):
        F.compose_funct_1d([], [1.0])                 # 外側関数は n>=1
    with pytest.raises(ValueError):
        F.get_pair_funct_1d([], 0)
    with pytest.raises(ValueError):
        F.get_y_value_funct_1d([], 0.0)
    with pytest.raises(ValueError):
        F.distance_funct_1d([], [])
    with pytest.raises(ValueError):
        F.create_funct_1d_pairs([], [])
    with pytest.raises(ValueError):
        F.match_funct_1d_trans([], [1.0])


def test_invalid_parameters_rejected():
    y = np.array([1.0, 2.0, 3.0])
    with pytest.raises(ValueError):
        F.smooth_funct_1d_gauss(y, sigma=0.0)         # sigma > 0
    with pytest.raises(ValueError):
        F.smooth_funct_1d_gauss(y, sigma=-1.0)
    with pytest.raises(ValueError):
        F.smooth_funct_1d_gauss(y, sigma=np.nan)
    with pytest.raises(ValueError):
        F.smooth_funct_1d_mean(y, size=0)             # size >= 1
    with pytest.raises(ValueError):
        F.smooth_funct_1d_mean(y, iterations=-1)      # iterations >= 0
    with pytest.raises(ValueError):
        F.sample_funct_1d(y, step=0)                  # step >= 1
    with pytest.raises(ValueError):
        F.distance_funct_1d(y, y, mode="median")      # mode 列挙
    with pytest.raises(ValueError):
        F.distance_funct_1d(y, np.array([1.0]))       # 長さ不一致(暗黙 broadcast 拒否)
    with pytest.raises(ValueError):
        F.create_funct_1d_pairs([1.0, 2.0], [1.0])    # 長さ不一致
    with pytest.raises(ValueError):
        F.scale_y_funct_1d(y, mult=np.inf)            # 非有限係数
    with pytest.raises(ValueError):
        F.transform_funct_1d(y, mult_x=np.nan)
    with pytest.raises(ValueError):
        F.get_y_value_funct_1d(y, np.nan)             # 非有限 x
    with pytest.raises(ValueError):
        F.get_pair_funct_1d(y, index=np.inf)          # 非有限 index


def test_ops_list_matches_public_surface():
    assert len(F.FUNCT1D_OPS) == 23
    for name in F.FUNCT1D_OPS:
        assert callable(getattr(F, name))
    assert set(F.FUNCT1D_OPS) <= set(F.__all__)


def test_facade_exports_funct1d():
    """配線ガード: fullseye facade からも api からも 23 関数が引ける。"""
    import api
    import fullseye
    for name in F.FUNCT1D_OPS:
        assert getattr(api, name) is getattr(F, name)
        assert getattr(fullseye, name) is getattr(F, name)
        assert name in api.__all__ and name in fullseye.__all__
    assert fullseye.funct1d is F
