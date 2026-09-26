# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""4f 光学プロセッサの門 —— **外部の参照値を一つも使わない**。

レンズがフーリエ面でフィルタを掛ける系は、真値が全部**閉形式か整数**で書ける:

* 恒等フィルタ → 出力は入力の **180 度回転**(2 回のフーリエ変換が座標反転を作る)
* ``(i2πf)^n`` → **n 階の空間微分**。ガウシアンの微分は閉じた式
* 渦位相板 ``exp(imφ)`` の**巻き数が整数 m**(閉路上の位相差の和 / 2π)
* ``lowpass + highpass = 1``(同じ半径なら厳密に)
* 線形性・合成・Parseval

だから HALCON の数値も参照画像も要らない。★門は**壊して確かめる** ——
フーリエ面の符号を 1 つ反転させたら、微分の門が落ちることを見る。
"""
from __future__ import annotations

import numpy as np
import pytest

import optics as O

N = 64
PITCH = 1.0
W = 8.0


def _grid(n: int = N, pitch: float = PITCH):
    x = (np.arange(n) - n // 2) * pitch
    return np.meshgrid(x, x, indexing="xy")


def _gaussian(n: int = N, pitch: float = PITCH, w: float = W):
    X, Y = _grid(n, pitch)
    return np.exp(-(X * X + Y * Y) / (w * w)), X, Y


def _rot180(a: np.ndarray) -> np.ndarray:
    """添字の写像 ``n -> (-n) mod N``。DC 標本(添字 0)は動かない。"""
    return np.roll(a[::-1, ::-1], 1, axis=(0, 1))


# --------------------------------------------------------------------------- #
# 1. 4f 系が 4f 系であること(座標反転つきの畳み込み)
# --------------------------------------------------------------------------- #
def test_identity_filter_returns_the_input_rotated_by_180_degrees():
    """★「フーリエ面で掛けるだけ」の計算と実物の 4f 系の違いがここに出る。

    レンズは 2 枚とも**前向きの**フーリエ変換を行うので ``F{F{u}}(x) = u(-x)``、
    つまり像は反転する。反転を忘れた実装はこの門で落ちる。
    """
    u, _, _ = _gaussian()
    out = O.four_f_filter(u, O.fourier_plane_filter(N, "identity"))
    assert np.abs(out - _rot180(u)).max() < 1e-14
    # 反転を省いた場合は、入力そのままに戻る(こちらは 4f 系ではない)
    flat = O.four_f_filter(u, O.fourier_plane_filter(N, "identity"), invert=False)
    assert np.abs(flat - u).max() < 1e-14


def test_a_blocked_fourier_plane_gives_exactly_zero():
    """フーリエ面を塞いだら厳密にゼロ(1e-16 の屑も出ない)。"""
    u, _, _ = _gaussian()
    out = O.four_f_filter(u, O.fourier_plane_filter(N, "block"))
    assert np.abs(out).max() == 0.0


# --------------------------------------------------------------------------- #
# 2. レンズが微分を計算すること(閉形式が真値)
# --------------------------------------------------------------------------- #
#: ガウシアン ``exp(-r^2/w^2)`` の x 方向 n 階微分(閉形式)。
#: エルミート多項式で書ける: d^n/dx^n exp(-x^2/w^2) = (-1/w)^n H_n(x/w) exp(...)
def _gaussian_derivative_x(order: int, X, u):
    t = X / W
    if order == 1:
        herm = 2.0 * t
    elif order == 2:
        herm = 4.0 * t * t - 2.0
    elif order == 3:
        herm = 8.0 * t ** 3 - 12.0 * t
    else:
        raise AssertionError("order %d の閉形式を書いていない" % order)
    return (-1.0 / W) ** order * herm * u


#: 階数ごとの許容。高階ほど帯域の打ち切りが増幅されるので同じ数字では測れない
#: (実測: 1 階 5.8e-08 / 2 階 5.4e-08 / 3 階 7.9e-06)。1 つの数字で括ると、
#: 緩い側に合わせて低階の門が甘くなる。
_DERIV_TOL = {1: 3e-7, 2: 3e-7, 3: 2e-5}


@pytest.mark.parametrize("order", [1, 2, 3])
def test_a_derivative_filter_computes_the_spatial_derivative(order):
    """★これが「レンズが微分を計算する」の実測。真値はガウシアンの微分の閉形式。

    1e-16 にはならない —— ガウシアンは厳密に帯域制限されていないので、
    打ち切りの分が残る。**どこまで合うかを数字で固定する**のが門の仕事である。
    """
    u, X, _ = _gaussian()
    h = O.fourier_plane_filter(N, "derivative_x", order=order, pixel_pitch_um=PITCH)
    got = O.four_f_filter(u, h, invert=False).real
    truth = _gaussian_derivative_x(order, X, u)
    c = slice(8, -8)                      # 端は折り返しが乗るので内側で採点
    rel = np.abs(got[c, c] - truth[c, c]).max() / np.abs(truth).max()
    assert rel < _DERIV_TOL[order], (order, rel)


def test_the_y_derivative_is_the_x_derivative_of_the_transposed_field():
    """軸の取り違えを捕まえる —— 対称な入力だと x と y の間違いは見えない。"""
    u, X, Y = _gaussian()
    u = u * (1.0 + 0.3 * X / W)           # ★x 方向に非対称にする
    hx = O.fourier_plane_filter(N, "derivative_x", order=1, pixel_pitch_um=PITCH)
    hy = O.fourier_plane_filter(N, "derivative_y", order=1, pixel_pitch_um=PITCH)
    gx = O.four_f_filter(u, hx, invert=False).real
    gy = O.four_f_filter(u.T, hy, invert=False).real
    assert np.abs(gx - gy.T).max() < 1e-12


def test_order_zero_is_the_identity():
    """``(i2πf)^0 = 1`` —— 0 階微分は何もしないこと。"""
    u, _, _ = _gaussian()
    h = O.fourier_plane_filter(N, "derivative_x", order=0)
    assert np.abs(O.four_f_filter(u, h, invert=False) - u).max() < 1e-14


def test_the_laplacian_filter_matches_the_sum_of_two_second_derivatives():
    """等方 2 階微分は x と y の 2 階微分の和(真値は op 自身でなく閉形式の和)。"""
    u, X, Y = _gaussian()
    lap = O.four_f_filter(u, O.fourier_plane_filter(N, "laplacian",
                                                    pixel_pitch_um=PITCH),
                          invert=False).real
    t = (X * X + Y * Y) / (W * W)
    truth = (4.0 * t - 4.0) / (W * W) * u          # d2/dx2 + d2/dy2
    c = slice(8, -8)
    rel = np.abs(lap[c, c] - truth[c, c]).max() / np.abs(truth).max()
    assert rel < 3e-7, rel


# --------------------------------------------------------------------------- #
# 3. 整数の不変量(渦位相板の巻き数)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("charge", [1, 2, -1, -3, 5])
def test_the_vortex_winding_number_is_exactly_the_integer_charge(charge):
    """★門が整数になる例。閉路を 1 周した位相の増分は厳密に ``2π·charge``。

    浮動小数の計算なのに**整数**で採点できるのは、巻き数が位相の連続変形で
    変わらない位相的な量だからである。
    """
    h = O.fourier_plane_filter(N, "vortex", charge=charge)
    t = np.linspace(0.0, 2.0 * np.pi, 721, endpoint=False)
    r = 12
    ii = np.round(r * np.sin(t)).astype(int) % N
    jj = np.round(r * np.cos(t)).astype(int) % N
    ph = np.angle(h[ii, jj])
    d = np.diff(np.concatenate([ph, ph[:1]]))
    d = (d + np.pi) % (2.0 * np.pi) - np.pi
    assert abs(d.sum() / (2.0 * np.pi) - charge) < 1e-9


def test_the_vortex_removes_the_mean_so_it_enhances_edges():
    """渦位相板は DC を落とす(原点で位相が定義されない)→ 平均が消える。

    これは副作用ではなく、この板が**等方な縁強調**として働く理由である。
    """
    u, _, _ = _gaussian()
    out = O.four_f_filter(u, O.fourier_plane_filter(N, "vortex", charge=1))
    assert abs(out.mean()) < 1e-12
    assert abs(u.mean()) > 1e-3            # 元は平均を持っている(空を通さない)


# --------------------------------------------------------------------------- #
# 4. 相補なフィルタ(片方だけ直すと境界が食い違う型)
# --------------------------------------------------------------------------- #
def test_lowpass_plus_highpass_is_exactly_one():
    """★境界の画素をどちらに入れるかが 2 通りあると、ここが厳密に 1 にならない。

    だから補集合は op の中で作る(呼び出し側に ``1 - lowpass`` を書かせない)。
    """
    for frac in (0.1, 0.25, 0.5, 1.0):
        lp = O.fourier_plane_filter(N, "lowpass", radius_frac=frac)
        hp = O.fourier_plane_filter(N, "highpass", radius_frac=frac)
        assert np.abs(lp + hp - 1.0).max() == 0.0


def test_a_lowpass_never_adds_energy_and_a_highpass_removes_the_mean():
    u, _, _ = _gaussian()
    lp = O.four_f_filter(u, O.fourier_plane_filter(N, "lowpass", radius_frac=0.2),
                         invert=False)
    hp = O.four_f_filter(u, O.fourier_plane_filter(N, "highpass", radius_frac=0.2),
                         invert=False)
    p_in = float((np.abs(u) ** 2).sum())
    assert float((np.abs(lp) ** 2).sum()) <= p_in * (1.0 + 1e-12)
    assert abs(hp.mean()) < 1e-12          # DC は落ちている
    # 低域 + 高域 = 元の場(フィルタが 1 に足されるので、場も足される)
    assert np.abs(lp + hp - u).max() < 1e-13


def test_the_hilbert_filter_makes_a_real_even_field_odd():
    """片側位相 ``-i·sign(fx)`` は偶関数を奇関数に変える(縁が立つ)。"""
    u, _, _ = _gaussian()
    out = O.four_f_filter(u, O.fourier_plane_filter(N, "hilbert_x"), invert=False)
    # x について奇 -> 反転すると符号が変わる(DC 列を除いて)
    flipped = np.roll(out[:, ::-1], 1, axis=1)
    # ★ナイキストのビンを 0 にしたので、この対称性は 1e-16 台で成り立つ
    assert np.abs(out + flipped).max() < 1e-14


# --------------------------------------------------------------------------- #
# 5. 系としての性質(線形性・合成・Parseval・移動同変)
# --------------------------------------------------------------------------- #
def test_the_system_is_linear():
    u1, X, _ = _gaussian()
    u2 = np.exp(-((X - 6.0) ** 2) / (W * W))
    h = O.fourier_plane_filter(N, "derivative_x", order=1)
    a, b = 0.7, -1.3
    lhs = O.four_f_filter(a * u1 + b * u2, h)
    rhs = a * O.four_f_filter(u1, h) + b * O.four_f_filter(u2, h)
    assert np.abs(lhs - rhs).max() < 1e-12


def test_two_systems_in_series_equal_one_with_the_product_filter():
    """合成は透過関数の積。★反転を 2 回かけると元に戻るので invert=False で試す。"""
    u, _, _ = _gaussian()
    h1 = O.fourier_plane_filter(N, "derivative_x", order=1)
    h2 = O.fourier_plane_filter(N, "lowpass", radius_frac=0.3)
    two = O.four_f_filter(O.four_f_filter(u, h1, invert=False), h2, invert=False)
    one = O.four_f_filter(u, h1 * h2, invert=False)
    assert np.abs(two - one).max() < 1e-12


def test_a_unit_modulus_filter_conserves_total_power():
    """|H| = 1 なら総パワーは保たれる(Parseval)。任意の透過関数を渡す経路も通る。"""
    u, _, _ = _gaussian()
    fy = np.fft.fftfreq(N, d=PITCH)[:, None]
    fx = np.fft.fftfreq(N, d=PITCH)[None, :]
    h = np.exp(-2j * np.pi * (3.0 * fx + 5.0 * fy))    # 純粋な位相(= 平行移動)
    out = O.four_f_filter(u, h, invert=False)
    p_in = float((np.abs(u) ** 2).sum())
    p_out = float((np.abs(out) ** 2).sum())
    assert abs(p_out - p_in) / p_in < 1e-12


def test_shifting_the_input_shifts_the_output():
    """変成関係: 入力をずらすと出力も同じだけずれる(反転を省いた座標で)。"""
    u, _, _ = _gaussian()
    h = O.fourier_plane_filter(N, "derivative_x", order=1)
    base = O.four_f_filter(u, h, invert=False)
    shifted = O.four_f_filter(np.roll(u, (4, 7), axis=(0, 1)), h, invert=False)
    assert np.abs(shifted - np.roll(base, (4, 7), axis=(0, 1))).max() < 1e-12


# --------------------------------------------------------------------------- #
# 6. 門を壊して確かめる
# --------------------------------------------------------------------------- #
def test_the_gate_would_catch_a_sign_flip_in_the_fourier_plane():
    """★符号を 1 つ反転させたら微分の門が落ちること。

    これが無いと「いつも通る門」でも緑になり、閉形式と一致しているのか
    偶然なのか区別できない。
    """
    u, X, _ = _gaussian()
    h = O.fourier_plane_filter(N, "derivative_x", order=1, pixel_pitch_um=PITCH)
    seeded = -h                                   # 種: フーリエ面の符号を反転
    got = O.four_f_filter(u, seeded, invert=False).real
    truth = _gaussian_derivative_x(1, X, u)
    c = slice(8, -8)
    rel = np.abs(got[c, c] - truth[c, c]).max() / np.abs(truth).max()
    assert rel > 1.0, ("符号を反転させたのに門が通った —— 門が何も見ていない: %r"
                       % rel)


def test_the_identity_gate_would_catch_a_missing_inversion():
    """反転を省いた実装が恒等の門を通らないこと(4f 系でないものを通さない)。

    ★入力は**非対称**でなければならない。中心対称なガウシアンだと
    ``rot180(u) == u`` なので、反転してもしなくても通ってしまう —— 最初に
    書いたときそれで緑になり、門が何も見ていなかった。
    """
    u, X, Y = _gaussian()
    u = u * (1.0 + 0.5 * X / W + 0.3 * Y / W)      # 中心対称を破る
    assert np.abs(u - _rot180(u)).max() > 1e-3, "入力がまだ対称(門が無意味になる)"
    no_invert = O.four_f_filter(u, O.fourier_plane_filter(N, "identity"),
                               invert=False)
    assert np.abs(no_invert - _rot180(u)).max() > 1e-3


# --------------------------------------------------------------------------- #
# 7. 完備性 —— 種類を足したのに門が無い状態を作れないようにする
# --------------------------------------------------------------------------- #
#: この一覧に門がある種類。★``FOURIER_PLANE_KINDS`` に足したらここも足す。
_GATED_KINDS = {
    "identity": "test_identity_filter_returns_the_input_rotated_by_180_degrees",
    "block": "test_a_blocked_fourier_plane_gives_exactly_zero",
    "derivative_x": "test_a_derivative_filter_computes_the_spatial_derivative",
    "derivative_y": "test_the_y_derivative_is_the_x_derivative_of_the_transposed_field",
    "laplacian": "test_the_laplacian_filter_matches_the_sum_of_two_second_derivatives",
    "lowpass": "test_lowpass_plus_highpass_is_exactly_one",
    "highpass": "test_lowpass_plus_highpass_is_exactly_one",
    "hilbert_x": "test_the_hilbert_filter_makes_a_real_even_field_odd",
    "vortex": "test_the_vortex_winding_number_is_exactly_the_integer_charge",
}


def test_every_filter_kind_has_a_gate():
    """★新しい種類を足して門を忘れると、ここが落ちる。

    「登録済みを数える門」は未登録に盲目になるので、**op 側の一覧から**数える
    (門の側の一覧から数えると、足し忘れた種類は最初から見えない)。
    """
    missing = [k for k in O.FOURIER_PLANE_KINDS if k not in _GATED_KINDS]
    assert not missing, ("門の無いフィルタ種: %s —— 真値を 1 つ決めて "
                         "_GATED_KINDS に足すこと" % missing)
    stale = [k for k in _GATED_KINDS if k not in O.FOURIER_PLANE_KINDS]
    assert not stale, "op から消えた種が門の一覧に残っている: %s" % stale


def test_every_kind_actually_produces_a_distinct_transfer_function():
    """種類が名前だけ違って中身が同じ、を捕まえる(空を通す型の一種)。"""
    seen: dict[bytes, str] = {}
    for k in O.FOURIER_PLANE_KINDS:
        h = O.fourier_plane_filter(N, k, order=1, charge=1, radius_frac=0.25)
        assert h.shape == (N, N) and h.dtype == np.complex128
        assert np.isfinite(h).all(), k
        key = h.tobytes()
        assert key not in seen, "%s と %s が同じ透過関数を返す" % (k, seen[key])
        seen[key] = k


# --------------------------------------------------------------------------- #
# 8. 断る入力(fail-closed)
# --------------------------------------------------------------------------- #
def test_an_unknown_kind_is_refused_with_the_list_in_the_message():
    with pytest.raises(ValueError) as e:
        O.fourier_plane_filter(N, "sharpen")
    assert "identity" in str(e.value)       # 何が使えるかを言う


@pytest.mark.parametrize("kw", [
    {"size": 1}, {"size": 10 ** 9}, {"order": -1}, {"order": 9},
    {"charge": 33}, {"charge": -33}, {"radius_frac": 0.0},
    {"radius_frac": 1.5}, {"pixel_pitch_um": 0.0}, {"pixel_pitch_um": -1.0},
    {"pixel_pitch_um": float("nan")},
])
def test_out_of_range_parameters_are_refused(kw):
    with pytest.raises(ValueError):
        O.fourier_plane_filter(**{"size": N, "kind": "identity", **kw})


def test_a_transfer_of_the_wrong_shape_is_refused_and_says_why():
    u, _, _ = _gaussian()
    with pytest.raises(ValueError) as e:
        O.four_f_filter(u, O.fourier_plane_filter(N // 2, "identity"))
    assert "same shape" in str(e.value)


def test_a_non_finite_field_is_refused():
    u, _, _ = _gaussian()
    u = u.copy()
    u[0, 0] = np.nan
    with pytest.raises(ValueError):
        O.four_f_filter(u, O.fourier_plane_filter(N, "identity"))


def test_the_ops_are_reachable_from_the_facade_and_the_ledger():
    """★入口を 2 つとも数える —— 片方だけ登録して穴が半分残るのを防ぐ。"""
    import api
    assert callable(api.four_f_filter) and callable(api.fourier_plane_filter)
    names = {r["name"] for r in api.list_ops(include_ledger=True)}
    assert {"four_f_filter", "fourier_plane_filter"} <= names

# --------------------------------------------------------------------------- #
# 9. 展示の opt-in 経路を走らせる
# --------------------------------------------------------------------------- #
def test_the_exhibit_runs_including_the_figure_and_the_animation(tmp_path):
    """★図と動画は既定で出さない経路なので、門が無いと**静かに壊れる**。

    実際に壊れていた —— 分数階微分のフィルタを ``(1, N)`` のまま渡していて、
    ``four_f_filter`` が「2x2 未満」で断っていた(op が断ってくれたので気づけた)。
    text の経路だけ通しても、この失敗は 1 ミリも見えない。
    """
    import importlib
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "examples"))
    try:
        mod = importlib.import_module("optics_four_f_processor")
    finally:
        sys.path.pop(0)
    mod.report()                                   # text 経路
    png = tmp_path / "four_f.png"
    gif = tmp_path / "morph.gif"
    matplotlib = pytest.importorskip(
        "matplotlib", reason="図の経路だけは matplotlib が要る(text 経路は依存なし)")
    mod.save_figure(str(png))
    assert png.stat().st_size > 5000, "図が空に近い"
    imageio = pytest.importorskip(
        "imageio", reason="動画の経路だけは imageio が要る")
    mod.save_morph(str(gif), frames=6)             # 門では少ない枚数で
    assert gif.stat().st_size > 2000, "動画が空に近い"
    del matplotlib, imageio
