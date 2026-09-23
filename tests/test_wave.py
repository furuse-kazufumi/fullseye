# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""波動 6 op の門。**閉形式の固有値・ベッセルの零点・既存 op** だけで採点する。

数学の絵はきれいなので、合っているかを誰も確かめない —— ここで確かめるのは
「絵の外に真値があるか」で、どれも op が使った式とは別の所から来ている:

* 矩形膜の固有値は ``pi^2 (m^2/a^2 + n^2/b^2)``。★よく書かれる ``m n pi`` ではない
  (積ではなく平方和)。節線の本数 ``m-1`` / ``n-1`` は整数なので、丸めの余地がない。
* 円膜の節円は **``J_0`` の零点**にある(``J'_0`` の零点は**腹**の位置)。自由端の
  半径方向の量子化が ``J'_m`` の零点、節円が ``J_0`` の零点 —— 取り違えると
  「op が間違っている」と読み違える(実際に一度読み違えた)。
* 二重スリットの縞間隔は ``lambda D / d``。作る op と測る op を分けてあるので、
  使った式で答え合わせにならない。
* 格子の次数は既存 ``grating_wavelengths`` で**逆算**できる(往復して元の
  波長に戻るか)。
"""
import numpy as np
import pytest

import mathops


PI2 = np.pi ** 2


def test_square_membrane_eigenvalues_are_the_sum_of_squares_not_the_product():
    """正方膜の固有値 / pi^2 は m^2 + n^2 の小さい順 = 2, 5, 5, 8, 10, 10, 13, 13。

    ★``m n pi`` という式を目にするが、それだと (1,1) と (2,2) の比が 4 になる。
    実際の比は 8/2 = 4 …… ここは一致してしまうので、**縮退の重複**(5 が 2 回、
    10 が 2 回)まで見ないと区別できない。それが積の式では出ない。
    """
    lam = np.asarray(mathops.wave_mode_frequencies("rectangular", 8, 1.0))
    want = np.array([2, 5, 5, 8, 10, 10, 13, 13], dtype=np.float64) * PI2
    assert lam.shape == (8,)
    assert np.allclose(lam, want, rtol=0, atol=1e-9), (lam / PI2, want / PI2)
    # 積の式 (m n pi)^2 なら [1, 4, 4, 16, 9, 9, ...] で並び順すら違う
    product_law = np.sort(np.array([(m * n) ** 2 for m in (1, 2, 3) for n in (1, 2, 3)],
                                   dtype=np.float64))[:8] * PI2
    assert not np.allclose(lam, product_law)


def test_rectangular_aspect_moves_the_eigenvalues_by_the_closed_form():
    """2:1 の長方形は m^2 + n^2/4 の小さい順。辺比が入る所は 1 か所だけ。"""
    got = np.asarray(mathops.wave_mode_frequencies("rectangular", 6, 2.0)) / PI2
    want = np.sort(np.array([m * m + n * n / 4.0
                             for m in range(1, 5) for n in range(1, 5)]))[:6]
    assert np.allclose(got, want, atol=1e-9), (got, want)


@pytest.mark.parametrize("m,n", [(3, 4), (5, 2), (6, 6)])
def test_nodal_line_count_is_an_integer_fixed_by_the_mode_numbers(m, n):
    """(m, n) モードの節線は縦 m-1 本・横 n-1 本。整数なので丸めの余地がない。"""
    u = np.asarray(mathops.wave_membrane_mode("rectangular", m, n, (401, 401), 1.0,
                                              free_edge=False))
    row, col = u[200, :], u[:, 200]
    nv = int((np.sign(row[:-1]) * np.sign(row[1:]) < 0).sum())
    nh = int((np.sign(col[:-1]) * np.sign(col[1:]) < 0).sum())
    assert (nv, nh) == (m - 1, n - 1), (nv, nh, m, n)
    mask = np.asarray(mathops.wave_nodal_lines(u))
    assert mask.dtype == np.bool_ and mask.shape == u.shape
    # 節線は在るが画面を埋め尽くさない(「走った」≠「意味のある出力」)
    assert 0 < mask.mean() < 0.2, mask.mean()


def test_mode_field_is_signed_and_normalised():
    """モードの形は [-1, 1] の**符号つき**。image2d を名乗ると腹の位相が消える。"""
    u = np.asarray(mathops.wave_membrane_mode("rectangular", 2, 3, (128, 128), 1.0))
    assert u.min() < -0.9 and u.max() > 0.9
    assert abs(max(abs(u.min()), abs(u.max())) - 1.0) < 1e-12


def test_circular_membrane_nodal_circles_sit_at_the_zeros_of_J0():
    """円膜の節円は **J_0 の零点 / k**。J'_0 の零点は腹であって節ではない。"""
    sp = pytest.importorskip("scipy.special")
    u = np.asarray(mathops.wave_membrane_mode("circular", 0, 3, (401, 401)))
    prof = u[200, 200:]
    sgn = np.sign(prof)
    cross = np.flatnonzero(sgn[:-1] * sgn[1:] < 0) / 200.0
    k = sp.jnp_zeros(0, 3)[-1]                       # 自由端 → J'_0 の零点が k を決める
    want = sp.jn_zeros(0, 3) / k                     # 節円は J_0 の零点
    assert cross.size >= want.size - 1, (cross, want)
    got = cross[:want.size] if cross.size >= want.size else cross
    assert np.allclose(got, want[:got.size], atol=0.01), (got, want)
    # ★J'_0 の零点と比べると合わない —— 取り違えを門で固定する
    wrong = sp.jnp_zeros(0, 3) / k
    assert not np.allclose(got, wrong[:got.size], atol=0.01)


@pytest.mark.parametrize("lam_nm,d_um,D_mm,px", [
    (550.0, 200.0, 200.0, 5.0),
    (450.0, 200.0, 200.0, 5.0),
    (550.0, 400.0, 200.0, 5.0),
    (550.0, 200.0, 400.0, 5.0),
])
def test_two_slit_fringe_period_is_lambda_D_over_d(lam_nm, d_um, D_mm, px):
    """縞間隔は lambda D / d。**作る op と測る op を分けてある**。"""
    img = np.asarray(mathops.wave_two_slit(lam_nm, d_um, D_mm, (64, 1024), px))
    assert img.min() >= 0.0 and img.max() <= 1.0
    meas = float(mathops.wave_fringe_period(img))
    pred = (lam_nm * 1e-3) * (D_mm * 1e3) / (d_um * px)
    assert abs(meas / pred - 1.0) < 0.02, (meas, pred)


def test_two_slit_refuses_a_screen_that_cannot_hold_three_fringes():
    """縞が 3 本入らない設定は黙って 1 本の縞を返さず ValueError。"""
    with pytest.raises(ValueError, match="fewer than 3 fringes"):
        mathops.wave_two_slit(550.0, 20.0, 200.0, (64, 512), 5.0)


def test_grating_orders_round_trip_through_the_existing_op():
    """格子の次数 → 既存 grating_wavelengths で逆算 → 元の波長に戻る。"""
    import fullseye as fs
    d_um, lam_nm = 1.6, 550.0
    t = mathops.wave_grating_orders(d_um, lam_nm, 0.0, (-2, -1, 0, 1, 2))
    assert set(t) >= {"order", "sin_out", "angle_deg", "propagates"}
    assert np.array_equal(np.asarray(t["order"]), np.array([-2, -1, 0, 1, 2]))
    # 0 次は入射方向のまま
    zero = np.asarray(t["sin_out"])[np.asarray(t["order"]) == 0]
    assert abs(float(zero[0])) < 1e-12
    sel = np.asarray(t["order"]) == 1
    back = np.asarray(fs.ledger.grating_wavelengths(
        pitch_um=d_um, sin_in=0.0, sin_out=np.asarray(t["sin_out"])[sel],
        orders=(1,))).ravel()
    assert np.allclose(back, lam_nm, rtol=1e-9), back


def test_grating_marks_evanescent_orders_instead_of_returning_a_fake_angle():
    """|sin_out| > 1 の次数は伝播しない —— 角度を捏造せず propagates=False で返す。"""
    t = mathops.wave_grating_orders(0.4, 550.0, 0.0, (-2, -1, 0, 1, 2))
    prop = np.asarray(t["propagates"]).astype(bool)
    assert not prop.all(), np.asarray(t["sin_out"])
    ang = np.asarray(t["angle_deg"])
    assert np.all(~np.isfinite(ang[~prop])) or np.all(np.isnan(ang[~prop]))
