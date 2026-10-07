"""2026-10-07 のレビューで見つかった数値の欠陥(ozakimm / residue / mathestimation / mathspectral)の回帰テスト。

各テストはレビューの反例そのものを入力にしている。
"""
from __future__ import annotations

import math
from fractions import Fraction

import numpy as np
import pytest

import mathestimation as E
import mathspectral as S
import ozakimm
import residue as R


# ------------------------------------------------------------------------------------------ #
# 1. Ozaki-II: 行・列のノルムがアンダー/オーバーフローして 0 を返していた
# ------------------------------------------------------------------------------------------ #
@pytest.mark.parametrize("a, b", [(1e-200, 1e200), (1e-150, 1e-150), (1e170, 1e-30), (1e200, 1e-200)])
def test_ozaki2_survives_extreme_but_representable_scales(a, b):
    A, B = np.full((2, 3), a), np.full((3, 2), b)
    truth = 3.0 * a * b
    C8 = ozakimm.matmul_ozaki(A, B, 8, "ozaki2")
    C20 = ozakimm.matmul_ozaki(A, B, 20, "ozaki2")
    assert np.all(np.abs(C8 - truth) <= 1e-8 * abs(truth))       # 反例では 0(真値 3.0)だった
    assert np.all(np.abs(C20 - truth) <= 4e-16 * abs(truth))


def test_ozaki2_is_bitwise_invariant_under_power_of_two_scaling():
    rng = np.random.default_rng(1)
    A, B = rng.standard_normal((4, 5)), rng.standard_normal((5, 3))
    C0 = ozakimm.matmul_ozaki(A, B, 8, "ozaki2")
    shifts = (-700, -300, 300, 700)
    checked = 0
    for s in shifts:
        C1 = ozakimm.matmul_ozaki(np.ldexp(A, s), np.ldexp(B, -s), 8, "ozaki2")
        assert np.array_equal(C0, C1), s
        # 行列の片側だけの 2 の冪の倍率は、結果にそのまま正確に乗る
        Cr = ozakimm.matmul_ozaki(np.ldexp(A, s), B, 8, "ozaki2")
        assert np.array_equal(Cr, np.ldexp(C0, s)), s
        checked += 1
    assert checked == len(shifts)


# ------------------------------------------------------------------------------------------ #
# 2. residue_crt: [lo, hi) に候補が無い標本が範囲外の値・margin 2.0 を返していた
# ------------------------------------------------------------------------------------------ #
def test_residue_crt_with_no_candidate_in_range_returns_nan_and_zero_margin():
    out = R.residue_crt([5, 5], [7, 9], lo=0, hi=1)
    assert np.isnan(out["value"]) and np.isnan(out["score"])
    assert float(out["margin"]) == 0.0                     # 以前は 2.0(最大の確信)で値は -2.75(範囲外)
    assert out["residual"].shape == (2,) and np.isnan(out["residual"]).all()


def test_residue_crt_empty_samples_do_not_disturb_the_valid_ones():
    out = R.residue_crt([[5.0, 0.5], [5.0, 0.5]], [7, 9], lo=0, hi=1)
    assert out["value"].shape == (2,) and out["margin"].shape == (2,) and out["residual"].shape == (2, 2)
    assert np.isnan(out["value"][0]) and out["margin"][0] == 0.0
    assert out["value"][1] == 0.5 and out["score"][1] == 1.0 and out["margin"][1] == 2.0
    single = R.residue_crt([0.5, 0.5], [7, 9], lo=0, hi=1)      # 有効な入力の結果は不変
    assert float(single["value"]) == 0.5 and float(single["margin"]) == 2.0


def test_residue_fault_locate_reports_undecidable_for_empty_samples():
    out = R.residue_fault_locate([[5.0, 0.5], [5.0, 0.5], [5.0, 0.5]], [7, 9, 11], lo=0, hi=1)
    assert np.isnan(out["value"][0]) and out["faulty"][0] == -2
    assert out["value"][1] == 0.5 and out["faulty"][1] == -1


# ------------------------------------------------------------------------------------------ #
# 3. residue_integer_crt: 生成器の 1.5 が 1 に化け、1e308 超の int が OverflowError
# ------------------------------------------------------------------------------------------ #
def test_integer_crt_rejects_a_fraction_hidden_in_a_generator():
    with pytest.raises(ValueError, match="integer"):
        R.residue_integer_crt((x for x in [1.5, 2]), [3, 5])
    assert R.residue_integer_crt((x for x in [1, 2]), (m for m in [3, 5]))["value"] == 7


def test_integer_crt_handles_integers_beyond_float_range():
    N = 10 ** 400
    m = [N + 1, N]
    v = 12345 * N + 678                                     # < (N+1)·N
    out = R.residue_integer_crt([v % x for x in m], m)
    assert out["value"] == v and out["modulus"] == (N + 1) * N
    big_r = R.residue_integer_crt([10 ** 400, 1], [3, 5])   # 剰余側も float を通さない
    assert big_r["value"] % 3 == (10 ** 400) % 3 and big_r["value"] % 5 == 1


@pytest.mark.parametrize("res", [[np.int64(2), np.int32(3)], [2.0, 3.0], [Fraction(2), 3], [True, 3]])
def test_integer_crt_still_accepts_exact_integer_spellings(res):
    assert R.residue_integer_crt(res, [5, 7])["value"] % 5 == int(res[0]) % 5


@pytest.mark.parametrize("bad", [[float("nan"), 1], [float("inf"), 1], [2.5, 1], ["2", 1],
                                 [Fraction(1, 2), 1], [None, 1]])
def test_integer_crt_rejects_non_integers(bad):
    with pytest.raises(ValueError):
        R.residue_integer_crt(bad, [5, 7])


# ------------------------------------------------------------------------------------------ #
# 4. crt_displacement: refine 後に |d| > max_disp の画素が valid のままだった
# ------------------------------------------------------------------------------------------ #
def test_crt_displacement_marks_pixels_beyond_max_disp_invalid():
    from scipy.ndimage import gaussian_filter
    rng = np.random.default_rng(0)
    a = gaussian_filter(rng.standard_normal((64, 96)), 1.5)
    out = R.crt_displacement(a, np.roll(a, 10, axis=1), max_disp=10.0)
    over = np.abs(out["d"]) > 10.0
    assert over.any()                                       # 反例: 最大 10.51 px が valid だった
    assert not (over & out["valid"]).any()
    assert (np.abs(out["d"][out["valid"]]) <= 10.0).all()
    inside = R.crt_displacement(a, np.roll(a, 7, axis=1), max_disp=10.0)
    assert inside["valid"].all()                            # 範囲内の普通の場合は従来どおり全部 valid


# ------------------------------------------------------------------------------------------ #
# 5. se3_log: π の近くで acos が桁落ち
# ------------------------------------------------------------------------------------------ #
def _rodrigues(axis, th):
    a = np.asarray(axis, dtype=np.float64)
    a = a / np.linalg.norm(a)
    K = np.array([[0.0, -a[2], a[1]], [a[2], 0.0, -a[0]], [-a[1], a[0], 0.0]])
    return np.eye(3) + math.sin(th) * K + (1 - math.cos(th)) * K @ K, a


AXES = [[1, 0, 0], [0, -1, 0], [0, 0, 1], [1, 2, 3], [-3, 0.5, -2], [0.3, -0.9, 0.1]]


@pytest.mark.parametrize("gap", [1e-1, 1e-3, 1.5e-6, 1e-9, 1e-11])
def test_se3_log_near_pi_matches_the_known_axis_angle(gap):
    th = math.pi - gap
    n = 0
    for ax in AXES:
        Rm, a = _rodrigues(ax, th)
        T = np.eye(4)
        T[:3, :3], T[:3, 3] = Rm, [0.1, -0.2, 0.3]
        xi = E.se3_log(T)
        assert np.abs(xi[3:] - th * a).max() < 1e-12, (ax, gap)   # acos では gap 1.5e-6 で 4e-4 rad
        assert np.abs(E.se3_exp(xi) - T).max() < 1e-12
        n += 1
    assert n == len(AXES)


def test_se3_log_moderate_angles_are_unchanged_and_exact_pi_is_refused():
    n = 0
    for ax in AXES:
        for th in (1e-3, 0.5, 2.0, 3.0):
            Rm, a = _rodrigues(ax, th)
            T = np.eye(4)
            T[:3, :3] = Rm
            assert np.abs(E.se3_log(T)[3:] - th * a).max() < 1e-13
            n += 1
    assert n == 4 * len(AXES)
    T = np.eye(4)
    T[:3, :3] = _rodrigues([1, 2, 3], math.pi)[0]
    with pytest.raises(ValueError, match="π"):
        E.se3_log(T)


# ------------------------------------------------------------------------------------------ #
# 6. kalman_smooth: ±inf が黙って欠測扱い
# ------------------------------------------------------------------------------------------ #
@pytest.mark.parametrize("bad", [np.inf, -np.inf])
def test_kalman_smooth_refuses_infinite_observations(bad):
    with pytest.raises(ValueError, match="inf"):
        E.kalman_smooth(np.array([[1.0], [bad], [2.0]]), 1, 1, 0.1, 0.1, [0.0], 1.0)


def test_kalman_smooth_nan_is_still_the_missing_marker():
    with_nan = E.kalman_smooth(np.array([[1.0], [np.nan], [2.0]]), 1, 1, 0.1, 0.1, [0.0], 1.0)
    assert np.all(np.isfinite(with_nan["x_smooth"]))


# ------------------------------------------------------------------------------------------ #
# 7. music_doa / esprit_doa: spacing <= 0 / 非有限を黙って受けていた
# ------------------------------------------------------------------------------------------ #
def _snapshots():
    rng = np.random.default_rng(0)
    M, K = 6, 200
    ang = np.radians([10.0, -20.0])
    a = np.exp(-2j * np.pi * 0.5 * np.arange(M)[:, None] * np.sin(ang)[None])
    return a @ (rng.standard_normal((2, K)) + 1j * rng.standard_normal((2, K)))


@pytest.mark.parametrize("fn", [S.music_doa, S.esprit_doa])
@pytest.mark.parametrize("spacing", [0.0, -0.5, float("nan"), float("inf"), "x"])
def test_doa_refuses_non_positive_or_non_finite_spacing(fn, spacing):
    with pytest.raises(ValueError, match="spacing"):
        fn(_snapshots(), 2, spacing=spacing)


@pytest.mark.parametrize("fn", [S.music_doa, S.esprit_doa])
def test_doa_valid_spacing_still_finds_the_sources(fn):
    doa = fn(_snapshots(), 2, spacing=0.5)["doa_deg"]
    assert np.abs(np.sort(doa) - np.array([-20.0, 10.0])).max() < 0.1


def test_complex_sort_ops_keep_the_imaginary_part():
    """★2026-10-07: cimage / beatcube を名乗る registry op が、guard の sanitize で実部だけにされていた。"""
    import ops
    rng = np.random.default_rng(0)
    z = rng.random((32, 32)) + 1j * rng.random((32, 32))
    names = [o.name for o in ops.REGISTRY if o.out_sort == "cimage" and o.in_sort == "cimage"]
    assert len(names) >= 2, names
    for n in names:
        op = [o for o in ops.REGISTRY if o.name == n][0]
        r = op.fn(z, 0.5, 0.5)
        assert np.iscomplexobj(r), "%s が複素を返していない(%s)" % (n, r.dtype)
        assert float(np.abs(r.imag).max()) > 0.0, n
