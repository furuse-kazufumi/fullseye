"""bspline_surf の ground-truth 数値検証。

既知の滑らかな解析曲面/曲線をサンプル → フィット → 評価が元形状に一致するか
(残差 RMS がノイズ以下 or 相関 > 0.99、最近傍残差小)を確認する。平滑化の
効き(ノイズ増で残差 RMS 増)と縮退時の graceful なエラーも押さえる。
"""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("scipy")

import bspline_surf as bs


# --------------------------------------------------------------------------- #
# ヘルパ                                                                       #
# --------------------------------------------------------------------------- #
def _rng():
    return np.random.default_rng(20260827)


def _scatter_grid(fn, n=24, lo=0.0, hi=3.0, noise=0.0, rng=None):
    """[lo,hi]^2 の n×n 格子で fn をサンプルし、散布 (x,y,z) を返す。"""
    rng = rng or _rng()
    ax = np.linspace(lo, hi, n)
    xx, yy = np.meshgrid(ax, ax)
    x = xx.ravel()
    y = yy.ravel()
    z = fn(x, y)
    if noise > 0:
        z = z + noise * rng.standard_normal(z.shape)
    return x, y, z


# --------------------------------------------------------------------------- #
# 曲面フィット: 既知の滑らかな曲面 z = sin(x)cos(y)                            #
# --------------------------------------------------------------------------- #
def test_surface_recovers_known_smooth_surface():
    f = lambda x, y: np.sin(x) * np.cos(y)
    noise = 0.02
    x, y, z = _scatter_grid(f, n=28, noise=noise)
    tck = bs.fit_bspline_surface(x, y, z, kx=3, ky=3, smooth=None)

    # 真値(ノイズ無し)との一致を独立な検証格子で評価。
    xv, yv, zt = _scatter_grid(f, n=20, noise=0.0)
    zhat = bs.eval_bspline_surface(tck, xv, yv, grid=False)

    rms = float(np.sqrt(np.mean((zhat - zt) ** 2)))
    corr = float(np.corrcoef(zhat.ravel(), zt.ravel())[0, 1])
    # フィットは真値をノイズ水準程度で復元し、強く相関する。
    assert rms < noise * 2.0
    assert corr > 0.99


def test_surface_eval_grid_matches_scatter():
    """grid=True の格子評価が同座標の散布評価と一致する(順序復元の健全性)。"""
    f = lambda x, y: 0.5 * np.sin(1.3 * x) + 0.4 * np.cos(0.9 * y)
    x, y, z = _scatter_grid(f, n=26, noise=0.0)
    tck = bs.fit_bspline_surface(x, y, z, smooth=0.0)

    ax = np.linspace(0.3, 2.7, 11)
    # わざと非ソートな軸を渡して並べ替え/復元経路を検証。
    axs = ax.copy()
    _rng().shuffle(axs)
    zg = bs.eval_bspline_surface(tck, axs, axs, grid=True)

    xx, yy = np.meshgrid(axs, axs, indexing="ij")
    zs = bs.eval_bspline_surface(tck, xx, yy, grid=False)
    assert zg.shape == (axs.size, axs.size)
    assert np.allclose(zg, zs, atol=1e-9)


def test_plane_residual_near_zero():
    """平面データは B スプライン曲面でほぼ完全に表現でき残差 ~0(kx=ky=3, =1 両方)。"""
    f = lambda x, y: 1.5 + 0.7 * x - 0.3 * y
    x, y, z = _scatter_grid(f, n=20, noise=0.0)
    for kx, ky in ((3, 3), (1, 1)):
        tck = bs.fit_bspline_surface(x, y, z, kx=kx, ky=ky, smooth=0.0)
        res = bs.surface_residual(x, y, z, tck)
        assert res["rms"] < 1e-6, (kx, ky, res)
        assert res["max"] < 1e-5, (kx, ky, res)


def test_surface_residual_keys_and_types():
    f = lambda x, y: np.sin(x) * np.cos(y)
    x, y, z = _scatter_grid(f, n=22, noise=0.05)
    tck = bs.fit_bspline_surface(x, y, z)
    res = bs.surface_residual(x, y, z, tck)
    assert set(res) == {"rms", "max", "pv"}
    for k in ("rms", "max", "pv"):
        assert isinstance(res[k], float)
        assert np.isfinite(res[k])
    # 普遍的に成立する不変条件のみを検証する(データ依存で自明通過しないもの)。
    # max_abs >= rms >= 0: RMS は絶対値の二乗平均平方根なので必ず最大絶対値以下。
    assert res["max"] >= res["rms"] >= 0.0
    # pv(符号付き残差レンジ)は非負で、かつ 2*max_abs 以下
    # (min/max とも絶対値が max_abs を超えないため)。
    # 注: pv >= max は残差が 0 を跨ぐ時しか成立しないので不変条件にしない
    #     (片側逸脱=純凸/純凹では pv < max。下の専用テストで検証)。
    assert 0.0 <= res["pv"] <= 2.0 * res["max"] + 1e-12
    # 返り値が定義どおりの値であることを独立再計算で確認。
    zhat = bs.eval_bspline_surface(tck, x, y, grid=False).ravel()
    resid = np.asarray(z, float).ravel() - zhat
    assert res["rms"] == pytest.approx(float(np.sqrt(np.mean(resid ** 2))))
    assert res["max"] == pytest.approx(float(np.max(np.abs(resid))))
    assert res["pv"] == pytest.approx(float(resid.max() - resid.min()))


def test_surface_residual_one_sided_deviation_allows_pv_below_max():
    """片側逸脱場(全残差が同符号=打痕/欠肉のような本来の検査シナリオ)では
    pv < max が起こり得ることを明示的に許容/検証する。

    かつては res["pv"] >= res["max"] を不変条件として主張していたが、これは
    残差が 0 を跨ぐデータでしか成立しない甘い(データ依存で自明通過する)条件。
    ここでは名目曲面から一様に正方向へずらした観測を作って全残差を同符号にし、
    surface_residual が正しい値を返すこと・pv < max が実際に起きることを示す。
    """
    f = lambda x, y: np.sin(x) * np.cos(y)
    x, y, z = _scatter_grid(f, n=22, noise=0.0)
    tck = bs.fit_bspline_surface(x, y, z, smooth=0.0)
    zhat = bs.eval_bspline_surface(tck, x, y, grid=False).ravel()

    # 名目曲面から一様に持ち上げ、位置で緩やかに変化させた観測(全残差 > 0 を保証)。
    # residual = z_obs - zhat = 0.5 + 0.05*(x+y) ∈ [0.5, 0.8]（x,y∈[0,3]）。
    z_obs = zhat + 0.5 + 0.05 * (np.asarray(x, float) + np.asarray(y, float))
    res = bs.surface_residual(x, y, z_obs, tck)

    resid = np.asarray(z_obs, float).ravel() - zhat
    assert np.all(resid > 0.0)  # 片側逸脱(同符号)であることを明示。

    # 定義どおりの値を独立再計算で確認。
    assert res["rms"] == pytest.approx(float(np.sqrt(np.mean(resid ** 2))))
    assert res["max"] == pytest.approx(float(np.max(np.abs(resid))))
    assert res["pv"] == pytest.approx(float(resid.max() - resid.min()))

    # 本題: 片側逸脱では pv < max が成立し得る(旧不変条件なら FAIL するケース)。
    assert res["pv"] < res["max"]
    # それでも普遍不変条件は保持されている。
    assert res["max"] >= res["rms"] >= 0.0
    assert 0.0 <= res["pv"] <= 2.0 * res["max"] + 1e-12


def test_surface_residual_increases_with_noise():
    """ノイズを増やすと(同じ平滑化のもとで)残差 RMS が単調に増える。"""
    f = lambda x, y: np.sin(x) * np.cos(y)
    rng = _rng()
    prev = -1.0
    for noise in (0.0, 0.05, 0.15, 0.30):
        x, y, z = _scatter_grid(f, n=26, noise=noise, rng=rng)
        # smooth を固定して比較の公平性を担保(自動値だと点数依存で動く)。
        tck = bs.fit_bspline_surface(x, y, z, smooth=0.5)
        rms = bs.surface_residual(x, y, z, tck)["rms"]
        assert rms >= prev - 1e-9, (noise, rms, prev)
        prev = rms
    assert prev > 0.0


def test_smooth_zero_fits_tighter_than_large_smooth():
    """s=0(補間寄り)は大 s(平滑)より学習点残差が小さい(トレードオフの向き)。"""
    f = lambda x, y: np.sin(x) * np.cos(y)
    x, y, z = _scatter_grid(f, n=26, noise=0.1)
    tight = bs.surface_residual(x, y, z, bs.fit_bspline_surface(x, y, z, smooth=0.0))["rms"]
    loose = bs.surface_residual(x, y, z, bs.fit_bspline_surface(x, y, z, smooth=5.0))["rms"]
    assert tight <= loose + 1e-9


# --------------------------------------------------------------------------- #
# 曲線フィット: 既知の 3D 螺旋                                                 #
# --------------------------------------------------------------------------- #
def _helix(n=120, turns=3.0):
    t = np.linspace(0.0, turns * 2 * np.pi, n)
    return np.column_stack([np.cos(t), np.sin(t), 0.15 * t])


def test_curve_recovers_known_helix():
    pts = _helix(n=140, turns=3.0)
    tck = bs.fit_bspline_curve(pts, smooth=0.0, k=3)
    # 曲線側は密に評価する(疎だと最近傍距離が弧長サンプル間隔に支配され、
    # フィット精度でなく離散化を測ってしまう。弧長 ~19 なので n=4000 で間隔 ~5e-3)。
    curve = bs.eval_bspline_curve(tck, n=4000)
    assert curve.shape == (4000, 3)

    # 元頂点の各点について、評価曲線上の最近傍距離が小さいこと。
    from scipy.spatial import cKDTree

    tree = cKDTree(curve)
    d, _ = tree.query(pts, k=1)
    # 螺旋半径 ~1。s=0 は補間なので残差は曲線サンプル間隔(~2.5e-3 半分)まで縮む。
    assert float(np.max(d)) < 5e-3
    assert float(np.sqrt(np.mean(d ** 2))) < 2e-3


def test_curve_endpoints_match_with_interpolation():
    """s=0 の補間なら端点は元点列の端点にほぼ一致する。"""
    pts = _helix(n=80, turns=2.0)
    tck = bs.fit_bspline_curve(pts, smooth=0.0, k=3)
    curve = bs.eval_bspline_curve(tck, n=300)
    assert np.allclose(curve[0], pts[0], atol=1e-6)
    assert np.allclose(curve[-1], pts[-1], atol=1e-6)


def test_curve_smoothing_reduces_wiggle_on_noisy_line():
    """ノイズ直線: 平滑化を強めると曲線長が短く(=まっすぐに)なる。"""
    rng = _rng()
    t = np.linspace(0, 1, 100)
    clean = np.column_stack([t, 0.5 * t, -0.2 * t])
    noisy = clean + 0.02 * rng.standard_normal(clean.shape)

    def _length(tck):
        c = bs.eval_bspline_curve(tck, n=400)
        return float(np.sum(np.linalg.norm(np.diff(c, axis=0), axis=1)))

    len_tight = _length(bs.fit_bspline_curve(noisy, smooth=0.0, k=3))
    len_loose = _length(bs.fit_bspline_curve(noisy, smooth=0.5, k=3))
    assert len_loose <= len_tight + 1e-9


def test_curve_dimension_generalizes_to_2d():
    theta = np.linspace(0, 2 * np.pi, 60)
    pts = np.column_stack([np.cos(theta), np.sin(theta)])
    tck = bs.fit_bspline_curve(pts, smooth=0.0, k=3)
    curve = bs.eval_bspline_curve(tck, n=200)
    assert curve.shape == (200, 2)
    r = np.linalg.norm(curve, axis=1)
    assert np.allclose(r, 1.0, atol=1e-2)


# --------------------------------------------------------------------------- #
# graceful なエラー / 縮退                                                     #
# --------------------------------------------------------------------------- #
def test_surface_too_few_points_raises():
    with pytest.raises(ValueError):
        bs.fit_bspline_surface([0.0, 1.0], [0.0, 1.0], [0.0, 1.0])


def test_surface_length_mismatch_raises():
    with pytest.raises(ValueError):
        bs.fit_bspline_surface([0, 1, 2, 3], [0, 1, 2], [0, 1, 2, 3])


def test_surface_nonfinite_raises():
    x, y, z = _scatter_grid(lambda a, b: a + b, n=8, noise=0.0)
    z = z.copy()
    z[0] = np.nan
    with pytest.raises(ValueError):
        bs.fit_bspline_surface(x, y, z)


def test_surface_high_degree_auto_reduced():
    """点数が (kx+1)*(ky+1) 未満でも次数を下げて縮退せずフィットできる。"""
    f = lambda x, y: 0.3 * x - 0.2 * y + 1.0
    x, y, z = _scatter_grid(f, n=3, noise=0.0)  # 9 点、双三次(16 係数)には不足
    tck = bs.fit_bspline_surface(x, y, z, kx=3, ky=3, smooth=0.0)
    res = bs.surface_residual(x, y, z, tck)
    assert res["rms"] < 1e-6


def test_surface_scatter_shape_mismatch_raises():
    f = lambda x, y: np.sin(x) * np.cos(y)
    x, y, z = _scatter_grid(f, n=16, noise=0.0)
    tck = bs.fit_bspline_surface(x, y, z)
    with pytest.raises(ValueError):
        bs.eval_bspline_surface(tck, np.zeros(4), np.zeros(5), grid=False)


def test_curve_too_few_points_raises():
    with pytest.raises(ValueError):
        bs.fit_bspline_curve(np.zeros((1, 3)))


def test_curve_low_point_count_reduces_degree():
    """3 点 + k=3 要求でも自動で k を下げて曲線を返す。"""
    pts = np.array([[0.0, 0.0, 0.0], [1.0, 0.5, 0.2], [2.0, 0.0, 0.5]])
    tck = bs.fit_bspline_curve(pts, smooth=0.0, k=3)
    curve = bs.eval_bspline_curve(tck, n=50)
    assert curve.shape == (50, 3)
    assert np.allclose(curve[0], pts[0], atol=1e-6)
    assert np.allclose(curve[-1], pts[-1], atol=1e-6)


def test_eval_curve_min_points_raises():
    pts = _helix(n=40)
    tck = bs.fit_bspline_curve(pts, smooth=0.0)
    with pytest.raises(ValueError):
        bs.eval_bspline_curve(tck, n=1)
