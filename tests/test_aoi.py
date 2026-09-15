# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""aoi —— 自動外観検査の前段 3 op を、真値を植えた**構造のある**画像で検査する。

乱数だけの入力は対称性の破れを隠す(feedback: random_test_data_hides_structural_defects)
ので、真値はすべて**構造を作った絵**で確かめる —— 片側に勾配・円・棒・1 点だけ明るい点・
市松・縞。各 op について「戻るか」だけでなく、**戻らないはずの条件で本当に戻らないか**を
対にして固定する(門は壊して確かめたものだけを残す)。

ここに書いてある数値は ``aoi.py`` の docstring と同じ実測値で、どちらかを変えたら
もう一方も直すこと。
"""
from __future__ import annotations

import numpy as np
import pytest

import aoi


# --------------------------------------------------------------------------- #
# 構造のある入力(乱数だけにしない)                                           #
# --------------------------------------------------------------------------- #
def _scene(n=128, seed=0):
    """勾配 + 円 + 棒 + 1 点 + 雑音。どの op でも「片側だけ壊れる」を出せる絵。"""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    g = 0.30 * (xx / (n - 1))
    disk = (((yy - n * 0.35) ** 2 + (xx - n * 0.40) ** 2) < (n * 0.18) ** 2) * 0.35
    bar = np.zeros((n, n))
    bar[n // 2: n // 2 + 6, 10:n - 10] = 0.25
    spot = np.zeros((n, n))
    spot[n // 3, 2 * n // 3] = 0.6
    return np.clip(g + disk + bar + spot + 0.08 * rng.standard_normal((n, n)), 0.02, 1.0)


def _vignette(n=128, strength=0.8):
    """cos⁴ 型のビネット(隅が暗い)。既知の**乗算**シェーディング。"""
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    c = (n - 1) / 2.0
    rr = np.hypot(yy - c, xx - c) / (n / 2.0)
    return np.cos(np.arctan(rr * strength)) ** 4


def _ffc_system(n=128, gain=0.9, dark=0.05, seed=3):
    """真値・フラット・暗・検査画像を作る。``raw = truth*(vign*gain) + dark``。"""
    truth = _scene(n, seed=seed)
    vign = _vignette(n)
    flat = vign * gain + dark
    raw = truth * (vign * gain) + dark
    return truth, flat, raw, dark


def _corner_centre(a, n=128):
    c = slice(n // 2 - 8, n // 2 + 8)
    k = slice(0, 16)
    return float(a[k, k].mean() / a[c, c].mean())


# --------------------------------------------------------------------------- #
# flat_field_correct                                                           #
# --------------------------------------------------------------------------- #
def test_flat_field_recovers_a_known_multiplicative_vignette():
    """既知の cos⁴ ビネットを掛けた絵が、補正で**元に戻る**(機械精度)。"""
    truth, flat, raw, dark = _ffc_system()
    out = aoi.flat_field_correct(raw, flat, dark=dark, target=1.0, clip=False)
    rel = float(np.abs(out - truth).max() / truth.max())
    assert rel < 1e-12, rel                       # 実測 1.755e-16
    # 隅が暗いままになっていないこと(真値と同じ比に戻る)。
    assert _corner_centre(out) == pytest.approx(_corner_centre(truth), rel=1e-9)


def test_flat_field_without_dark_does_not_recover():
    """★暗電流を無視すると戻らない —— 式が本当に dark を使っている証拠。

    省いても**絵としては破綻しない**(隅が明るいまま残るだけ)ので、目では合格に
    見えて数字だけが狂う。だからここで数値として固定する。
    """
    truth, flat, raw, dark = _ffc_system()
    good = aoi.flat_field_correct(raw, flat, dark=dark, target=1.0, clip=False)
    bad = aoi.flat_field_correct(raw, flat, dark=None, target=1.0, clip=False)
    err_good = float(np.abs(good - truth).max() / truth.max())
    err_bad = float(np.abs(bad - truth).max() / truth.max())
    assert err_good < 1e-12, err_good             # 実測 1.755e-16
    assert err_bad > 0.2, err_bad                 # 実測 2.252e-01
    assert err_bad / err_good > 1e10              # 実測 1.3e+15 倍
    # 補正しきれず隅が明るいまま残る(真値 0.1209 に対し実測 0.4867)。
    assert _corner_centre(bad) > 3 * _corner_centre(truth)


def test_subtractive_flattening_cannot_replace_this_op():
    """引き算(background_flatten)では乗算のムラは戻らない —— 族を足した理由の数値。"""
    match3d = pytest.importorskip("match3d")
    truth, flat, raw, dark = _ffc_system()
    div = aoi.flat_field_correct(raw, flat, dark=dark, target=1.0, clip=False)
    sub = match3d.background_flatten(raw, degree=2)
    sub = sub - sub.min() + 1e-9
    assert _corner_centre(div) == pytest.approx(_corner_centre(truth), rel=1e-9)
    assert _corner_centre(sub) > 4 * _corner_centre(truth)     # 実測 0.6436 対 0.1209


def test_flat_field_refuses_a_zero_or_negative_response():
    """ゼロ割りを黙って通さない(既定は fail-closed)。"""
    truth, flat, raw, dark = _ffc_system()
    dead = flat.copy()
    dead[10, 10] = dark                            # 応答ちょうど 0
    with pytest.raises(ValueError, match="zero-divide"):
        aoi.flat_field_correct(raw, dead, dark=dark)
    neg = flat.copy()
    neg[5, 5] = dark - 0.1                         # 応答が負
    with pytest.raises(ValueError, match="zero-divide"):
        aoi.flat_field_correct(raw, neg, dark=dark)


def test_flat_field_min_response_is_an_explicit_opt_in():
    """下限は**明示したときだけ**効く(既定にすると死んだ画素に値が生える)。"""
    truth, flat, raw, dark = _ffc_system()
    dead = flat.copy()
    dead[10, 10] = dark
    out = aoi.flat_field_correct(raw, dead, dark=dark, min_response=1e-3,
                                 target=1.0, clip=False)
    assert np.isfinite(out).all()
    for bad in (0.0, -1.0, float("inf"), "x", True):
        with pytest.raises(ValueError):
            aoi.flat_field_correct(raw, dead, dark=dark, min_response=bad)


def test_flat_field_dtype_and_range_are_pinned():
    """出力の dtype と値域(= 飽和の扱い)を固定する。"""
    truth, flat, raw, dark = _ffc_system()
    hot = raw * 3.0                                # わざと飽和させる
    free = aoi.flat_field_correct(hot, flat, dark=dark, target=1.0, clip=False)
    clipped = aoi.flat_field_correct(hot, flat, dark=dark, target=1.0, clip=True)
    assert free.dtype == np.float64 and clipped.dtype == np.float64
    assert free.max() > 1.0                        # 実測 2.9585
    assert clipped.min() >= 0.0 and clipped.max() <= 1.0
    assert int((free > 1.0).sum()) > 0             # 実測 5342 / 16384 画素が飽和


def test_flat_field_default_target_is_the_flat_mean():
    """既定 target の意味を数値で固定する(= 真値 x mean(flat-dark))。"""
    truth, flat, raw, dark = _ffc_system()
    out = aoi.flat_field_correct(raw, flat, dark=dark, clip=False)
    k = float((flat - dark).mean())
    assert np.abs(out - truth * k).max() < 1e-12   # 実測 8.327e-17
    # ★平均は保たれ**ない**(被写体と感度に相関があるとずれる)。実測 8.9 %。
    assert out.mean() != pytest.approx(float((raw - dark).mean()), rel=1e-3)


def test_flat_field_accepts_a_scalar_dark():
    truth, flat, raw, dark = _ffc_system()
    a = aoi.flat_field_correct(raw, flat, dark=dark, target=1.0, clip=False)
    b = aoi.flat_field_correct(raw, flat, dark=np.full_like(raw, dark),
                               target=1.0, clip=False)
    assert np.allclose(a, b, atol=1e-15)


@pytest.mark.parametrize("bad", ["image", "flat"])
def test_flat_field_refuses_mismatched_and_broken_input(bad):
    truth, flat, raw, dark = _ffc_system()
    small = np.ones((8, 8))
    with pytest.raises(ValueError, match="same shape"):
        if bad == "image":
            aoi.flat_field_correct(small, flat, dark=dark)
        else:
            aoi.flat_field_correct(raw, small, dark=dark)
    nan = raw.copy()
    nan[0, 0] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        aoi.flat_field_correct(nan, flat, dark=dark)


# --------------------------------------------------------------------------- #
# register_image                                                               #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("dy,dx", [(3, 5), (-4, 2), (0, 7)])
def test_register_recovers_a_known_integer_shift(dy, dx):
    ref = _scene()
    mov = np.roll(np.roll(ref, dy, 0), dx, 1)
    r = aoi.register_image(ref, mov)
    assert r["dy"] == pytest.approx(dy, abs=0.05)
    assert r["dx"] == pytest.approx(dx, abs=0.05)
    assert r["residual"] < 1e-6                    # 実測 0.000000
    assert r["consistent"] is True
    assert r["peak"] > 0.9                         # 実測 0.9698


@pytest.mark.parametrize("dy,dx", [(2.5, -1.5), (0.5, 0.0), (0.0, 0.5)])
def test_register_recovers_a_known_subpixel_shift(dy, dx):
    """副画素 0.5 px も回収できる(upsample=20 なので刻みは 0.05 px)。"""
    ref = _scene()
    mov = aoi._shift_fourier(ref, dy, dx)
    r = aoi.register_image(ref, mov, upsample=20)
    assert np.hypot(r["dy"] - dy, r["dx"] - dx) < 0.05      # 実測 0.0000
    assert r["consistent"] is True


@pytest.mark.parametrize("deg,resid_floor", [(2.0, 0.3), (5.0, 0.3), (10.0, 0.3)])
def test_register_flags_rotation_as_inconsistent(deg, resid_floor):
    """★回転を「いちばん近い平行移動」として黙って成功と言わない。

    例外は出さない(平行移動の当てはめ自体は返る)が、``residual`` が跳ねて
    ``consistent`` が False になる。返り値を見ずに dy/dx だけ使うと、回転 2 度を
    「ずれ 0.14 px」として飲み込む —— その形をここで固定する。
    """
    ref = _scene()
    r = aoi.register_image(ref, _rotate(ref, deg))
    assert r["residual"] > resid_floor, r          # 実測 0.5886 / 0.6555 / 0.7058
    assert r["consistent"] is False
    assert np.hypot(r["dy"], r["dx"]) < 5.0        # 小さい並進として返ってしまう


@pytest.mark.parametrize("s", [1.05, 1.10])
def test_register_flags_scale_as_inconsistent(s):
    ref = _scene()
    r = aoi.register_image(ref, _scaled(ref, s))
    assert r["residual"] > 0.3, r                  # 実測 0.6073 / 0.6767
    assert r["consistent"] is False


def test_register_reports_ambiguity_on_a_periodic_checkerboard():
    """周期構造では答えが一意に決まらない —— それが返り値に出る。"""
    n = 128
    yy, xx = np.mgrid[0:n, 0:n]
    check = (((xx // 8) + (yy // 8)) % 2).astype(float)
    r = aoi.register_image(check, np.roll(np.roll(check, 3, 0), 5, 1))
    assert r["peak_ratio"] > 0.9                   # 実測 1.0000
    assert r["ambiguous"] is True


def test_register_does_not_catch_a_one_directional_stripe():
    """★正直に固定する限界 —— 縞は ``ambiguous`` に**掛からない**。

    縞は縦方向に模様が無いので ``dy`` は原理的に決まらないのに、``peak_ratio`` は
    0.1996 で ``ambiguous`` は False。``peak_ratio`` は「離れた 2 番目の**山**」を
    見る量で、縞が作るのは山ではなく**尾根**(dy 方向に平らな筋)だから検出できない。
    しかも尾根から dy=0 を選んでいるのは画像ではなく Hann 窓の包絡である。

    直すまで忘れないために、**捕まらないことそのもの**を門にしてある。検出を
    足したらここが赤くなるので、そのときに docstring と一緒に直すこと。
    """
    n = 128
    yy, xx = np.mgrid[0:n, 0:n]
    stripe = ((xx // 8) % 2).astype(float)
    r = aoi.register_image(stripe, np.roll(np.roll(stripe, 3, 0), 5, 1))
    assert r["ambiguous"] is False                 # ← 望ましくはないが、これが現状
    assert abs(r["dy"]) < 0.1                      # 実測 0.000(窓が決めた値)
    assert r["dx"] == pytest.approx(4.9, abs=0.2)  # 5 を周期 8 で見た答え


@pytest.mark.parametrize("img", [np.full((32, 32), 0.4), np.zeros((32, 32)),
                                 np.ones((32, 32))])
def test_register_refuses_a_constant_image(img):
    """情報ゼロの絵に「ずれ 0 で完全一致」と言わせない。"""
    with pytest.raises(ValueError, match="constant"):
        aoi.register_image(img, img)


def test_register_refuses_degenerate_shapes():
    ref = _scene(32)
    with pytest.raises(ValueError, match="same shape"):
        aoi.register_image(ref, _scene(48))
    with pytest.raises(ValueError, match="at least 2x2"):
        aoi.register_image(np.zeros((1, 8)), np.zeros((1, 8)))
    with pytest.raises(ValueError, match="2-D"):
        aoi.register_image(np.zeros((4, 4, 3)), np.zeros((4, 4, 3)))


def test_register_rejects_unknown_knobs():
    ref = _scene(32)
    for kw in ({"method": "nope"}, {"window": "nope"}, {"upsample": 0},
               {"max_shift": -1.0}):
        with pytest.raises(ValueError):
            aoi.register_image(ref, ref.copy(), **kw)


# --------------------------------------------------------------------------- #
# tiled_map                                                                    #
# --------------------------------------------------------------------------- #
def test_tiled_map_mean_reconstructs_the_global_mean():
    """分解可能な量(平均)は、タイル統計から全体量に戻る = 検算になる。"""
    img = _scene(64, seed=7)
    t = aoi.tiled_map(img, tile=16, stat="mean")
    assert t["map"].shape == (4, 4)
    assert t["partial_tiles"] == 0 and t["dropped_tiles"] == 0
    assert t["covered_fraction"] == pytest.approx(1.0)
    w = float((t["map"] * t["counts"]).sum() / t["counts"].sum())
    assert w == pytest.approx(float(img.mean()), abs=1e-12)     # 実測 0.0e+00


def test_tiled_map_keeps_ragged_tiles_and_says_how_many():
    """★半端なタイルを黙って捨てない。捨てないほうが既定で、件数が返り値に出る。"""
    img = _scene(70, seed=7)
    t = aoi.tiled_map(img, tile=16, stat="mean")
    assert t["map"].shape == (5, 5)
    assert t["partial_tiles"] == 9                 # 最終行 5 + 最終列 5 - 角 1
    assert t["covered_fraction"] == pytest.approx(1.0)
    # 端数があっても、画素数で重み付ければ全体平均に戻る(タイルは画像を覆う)。
    w = float((t["map"] * t["counts"]).sum() / t["counts"].sum())
    assert w == pytest.approx(float(img.mean()), abs=1e-12)


def test_tiled_map_records_what_it_dropped():
    """捨てるなら、捨てたことが返り値に残る。"""
    img = _scene(70, seed=7)
    t = aoi.tiled_map(img, tile=16, stat="mean", drop_partial=True)
    assert t["map"].shape == (4, 4)
    assert t["partial_tiles"] == 0
    assert t["dropped_tiles"] == 9
    assert t["covered_fraction"] == pytest.approx(0.835918, abs=1e-5)
    assert t["covered_fraction"] < 1.0             # 覆えていないことが数字で分かる


def test_tiled_map_overlap_zero_and_positive():
    img = _scene(70, seed=7)
    a = aoi.tiled_map(img, tile=16, stat="mean", overlap=0)
    b = aoi.tiled_map(img, tile=16, stat="mean", overlap=8)
    assert b["map"].shape == (8, 8) and a["map"].shape == (5, 5)
    assert b["covered_fraction"] > 1.0             # 重なるので 1 を超える(実測 3.24)
    with pytest.raises(ValueError, match="overlap"):
        aoi.tiled_map(img, tile=8, overlap=8)


def test_tiled_map_tile_larger_than_image():
    """タイルが画像より大きいとき: 1 枚の半端タイル、落とすなら fail-closed。"""
    img = _scene(64, seed=7)
    t = aoi.tiled_map(img, tile=200, stat="mean")
    assert t["map"].shape == (1, 1)
    assert t["partial_tiles"] == 1
    assert t["map"][0, 0] == pytest.approx(float(img.mean()))
    with pytest.raises(ValueError, match="leaves no whole"):
        aoi.tiled_map(img, tile=200, drop_partial=True)


def test_tiled_map_std_is_not_decomposable():
    """まとめ直せる量とそうでない量を取り違えないための門(honest)。"""
    img = _scene(64, seed=7)
    t = aoi.tiled_map(img, tile=16, stat="std")
    w = float((t["map"] * t["counts"]).sum() / t["counts"].sum())
    assert w != pytest.approx(float(img.std()), rel=0.05)   # 実測 0.1058 対 0.1555


@pytest.mark.parametrize("stat", aoi.TILE_STATS)
def test_tiled_map_every_stat_runs_and_means_something(stat):
    img = _scene(64, seed=7)
    t = aoi.tiled_map(img, tile=16, stat=stat)
    assert np.isfinite(t["map"]).all()
    if stat != "count":                            # count は設計上どのタイルも同じ
        assert float(np.ptp(t["map"])) > 0.0


def test_tiled_map_rejects_unknown_stat():
    with pytest.raises(ValueError, match="stat"):
        aoi.tiled_map(_scene(32), tile=8, stat="nope")


# --------------------------------------------------------------------------- #
# 「走った」 != 「意味のある出力」—— 3 op 共通の全数検査                        #
# --------------------------------------------------------------------------- #
def test_no_op_returns_a_constant_or_non_finite_result():
    """出力が全部同じ値・全部 0・非有限になっていないことを数値で確かめる。

    走ったことと、意味のある値が出たことは別(feedback: ran_is_not_meaningful_output)。
    """
    truth, flat, raw, dark = _ffc_system(64)
    ffc = aoi.flat_field_correct(raw, flat, dark=dark, target=1.0, clip=False)
    assert np.isfinite(ffc).all()
    assert float(np.ptp(ffc)) > 0.01
    assert np.unique(ffc).size > ffc.size // 2
    assert not np.allclose(ffc, 0.0)

    ref = _scene(64)
    reg = aoi.register_image(ref, np.roll(ref, 3, 0))
    assert all(np.isfinite(reg[k]) for k in ("dy", "dx", "peak", "peak_ratio", "residual"))
    assert reg["peak"] > 0.0

    tm = aoi.tiled_map(ref, tile=16, stat="mean")
    assert np.isfinite(tm["map"]).all()
    assert float(np.ptp(tm["map"])) > 0.0
    assert tm["counts"].sum() == ref.size


def test_the_ledger_exposes_all_three_ops():
    """台帳・公開経路の両方から引けること(登録したと引けるは別)。"""
    import opsaoi
    assert sorted(opsaoi.list_ops()) == ["flat_field_correct", "register_image", "tiled_map"]
    assert opsaoi.missing() == []
    import fullseye as fs
    for name in ("flat_field_correct", "register_image", "tiled_map"):
        assert name in dir(fs.ledger), name


# --------------------------------------------------------------------------- #
# 変形のヘルパ(門の中でだけ使う。真値を作る側)                                #
# --------------------------------------------------------------------------- #
def _bilinear(img, sy, sx):
    n, m = img.shape
    y0 = np.clip(np.floor(sy).astype(int), 0, n - 2)
    x0 = np.clip(np.floor(sx).astype(int), 0, m - 2)
    fy = np.clip(sy - y0, 0, 1)
    fx = np.clip(sx - x0, 0, 1)
    return ((1 - fy) * (1 - fx) * img[y0, x0] + fy * (1 - fx) * img[y0 + 1, x0]
            + (1 - fy) * fx * img[y0, x0 + 1] + fy * fx * img[y0 + 1, x0 + 1])


def _rotate(img, deg):
    n = img.shape[0]
    yy, xx = np.mgrid[0:n, 0:n].astype(float) - (n - 1) / 2.0
    t = np.deg2rad(deg)
    sy = np.cos(t) * yy + np.sin(t) * xx + (n - 1) / 2.0
    sx = -np.sin(t) * yy + np.cos(t) * xx + (n - 1) / 2.0
    return _bilinear(img, sy, sx)


def _scaled(img, s):
    n = img.shape[0]
    yy, xx = np.mgrid[0:n, 0:n].astype(float) - (n - 1) / 2.0
    return _bilinear(img, yy / s + (n - 1) / 2.0, xx / s + (n - 1) / 2.0)
