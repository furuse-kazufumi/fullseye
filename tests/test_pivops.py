# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""pivops —— 真値を定義から作り、閉形式と突き合わせる。

PIV は「それらしいベクトル図」が必ず出るので、目視は検証にならない。ここでは
変位場を先に決めて画像を作り、(1) 変位そのもの、(2) 渦度・発散の閉形式、
(3) 既知の系統誤差が**出るはずのとおりに出るか**、の 3 方向から固定する。
"""
from __future__ import annotations

import os
import re

import numpy as np
import pytest

import pivops as P

H = W = 256
CY, CX = (H - 1) / 2.0, (W - 1) / 2.0


# =========================================================================
# 0. 真値つきの場(閉形式)
# =========================================================================

def rotation(omega):
    """``(dy, dx) = (w(c-cx), -w(r-cy))``。画面上は時計回り、渦度は ``-2w``。"""
    def f(r, c):
        return omega * (c - CX), -omega * (r - CY)
    return f


def expansion(s):
    """一様膨張。発散 ``2s``、渦度 0。"""
    def f(r, c):
        return s * (r - CY), s * (c - CX)
    return f


def simple_shear(g):
    """単純せん断。渦度 ``g``、発散 0。"""
    def f(r, c):
        return np.zeros_like(r), g * (r - CY)
    return f


def _run(field, windows=(64, 32), shape=(H, W), density=0.02, seed=7, **kw):
    a, b, truth = P.piv_synth_pair(shape, field, density=density, seed=seed)
    flow, info = P.piv_multipass(a, b, windows=windows, **kw)
    t = P.piv_sample_at_windows(truth, info)
    return flow, info, t


# =========================================================================
# 1. 一様並進 —— 偏りと散らばりを分けて見る
# =========================================================================

def test_uniform_translation_is_recovered():
    flow, info, t = _run((1.37, -2.62))
    s = P.piv_error_stats(flow, t)
    assert abs(s["bias_dy"]) < 0.02 and abs(s["bias_dx"]) < 0.02, s
    assert s["rms"] < 0.12, s
    assert s["n_valid"] == s["n_total"]


@pytest.mark.parametrize("d", [0.5, 1.0, 3.0, 5.0])
def test_translation_over_a_range_of_magnitudes(d):
    a, b, truth = P.piv_synth_pair((H, W), (0.0, d), density=0.02, seed=5)
    flow, info = P.piv_cross_correlate(a, b, 32, 0.5)
    s = P.piv_error_stats(flow, P.piv_sample_at_windows(truth, info))
    assert abs(s["bias_dx"]) < 0.03, (d, s)


def test_the_grid_positions_are_window_centres():
    a, b, _ = P.piv_synth_pair((H, W), (0.0, 1.0), seed=1)
    flow, info = P.piv_cross_correlate(a, b, 32, 0.5)
    assert flow.shape[1:] == (info["rows"].size, info["cols"].size)
    assert info["rows"][0] == pytest.approx(15.5)      # (32-1)/2
    assert info["step"] == 16


# =========================================================================
# 2. 零方向への偏りと、その補正(実測を固定する)
# =========================================================================

def test_without_normalisation_the_bias_is_proportional_to_the_displacement():
    """素の相互相関は変位を**零へ引き寄せる**。偏り / (d/N) が一定になる。

    重なる領域が変位とともに減るのが原因なので、比が一定であることこそが
    「原因の説明が合っている」証拠になる(値が小さいことではなく)。
    """
    ratios = []
    for d in (1.0, 2.0, 4.0, 6.0):
        a, b, truth = P.piv_synth_pair((H, W), (0.0, d), density=0.02, seed=5)
        flow, info = P.piv_cross_correlate(a, b, 32, 0.5, normalize="none")
        s = P.piv_error_stats(flow, P.piv_sample_at_windows(truth, info))
        ratios.append(s["bias_dx"] / (-d / 32.0))
    assert all(1.0 < r < 1.6 for r in ratios), ratios
    assert max(ratios) - min(ratios) < 0.15, ratios      # 傾き一定


def test_overlap_normalisation_removes_most_of_that_bias():
    a, b, truth = P.piv_synth_pair((H, W), (0.0, 4.0), density=0.02, seed=5)
    t_of = lambda kw: P.piv_error_stats(  # noqa: E731
        *(lambda f, i: (f, P.piv_sample_at_windows(truth, i)))(
            *P.piv_cross_correlate(a, b, 32, 0.5, **kw)))
    off = t_of({"normalize": "none"})
    on = t_of({})
    assert abs(on["bias_dx"]) < 0.25 * abs(off["bias_dx"]), (on, off)


def test_normalising_without_a_search_limit_is_worse_than_not_normalising():
    """片方だけ入れると**悪化する**。実測で RMS が 45 倍になった。

    「補正を足したのだから良くなったはず」を測らずに信じないための固定。
    """
    a, b, truth = P.piv_synth_pair((H, W), (1.37, -2.62), density=0.02, seed=3)
    def rms(**kw):
        f, i = P.piv_cross_correlate(a, b, 32, 0.5, **kw)
        return P.piv_error_stats(f, P.piv_sample_at_windows(truth, i))["rms"]
    both, no_limit, neither = rms(), rms(search_limit=None), rms(normalize="none")
    assert no_limit > 10 * both, (both, no_limit)
    assert no_limit > 10 * neither, (neither, no_limit)


# =========================================================================
# 3. 渦度・発散 —— 閉形式と、独立な検算
# =========================================================================

@pytest.mark.parametrize("name,field,vort,div", [
    ("rotation", rotation(0.01), -0.02, 0.0),
    ("expansion", expansion(0.01), 0.0, 0.02),
    ("shear", simple_shear(0.02), 0.02, 0.0),
])
def test_vorticity_and_divergence_match_the_closed_form(name, field, vort, div):
    flow, info, _ = _run(field, shape=(320, 320))
    v = P.piv_vorticity(flow, info["step"])[1:-1, 1:-1]
    d = P.piv_divergence(flow, info["step"])[1:-1, 1:-1]
    assert np.mean(v) == pytest.approx(vort, abs=0.0015), (name, np.mean(v))
    assert np.mean(d) == pytest.approx(div, abs=0.0015), (name, np.mean(d))


def test_the_rotation_sign_is_the_documented_one_not_its_mirror():
    """符号の規約そのものを名指しで固定する。

    最初にこのテストを書いたとき、期待値を ``+2w`` と書いて落ちた —— 間違って
    いたのは**テストの側**で、``(w(c-cx), -w(r-cy))`` は画面上では時計回りに
    見える場だった。規約を使って書いたテストでは規約の反転を捕まえられないので、
    向きが分かる最小の場で別に固定する。
    """
    # 中心の右側が下へ動く = 画面上で時計回り = 渦度は負
    flow, info, _ = _run(rotation(0.01), shape=(320, 320))
    assert np.mean(P.piv_vorticity(flow, info["step"])[1:-1, 1:-1]) < 0


def test_divergence_is_an_independent_check_on_incompressible_fields():
    """真値と比べる評価とは**別経路**の検算。回転・せん断は発散 0 のはず。"""
    for field in (rotation(0.01), simple_shear(0.02)):
        flow, info, _ = _run(field, shape=(320, 320))
        d = P.piv_divergence(flow, info["step"])[1:-1, 1:-1]
        assert abs(np.mean(d)) < 5e-4, np.mean(d)


def test_flow_magnitude_is_one_way_and_matches_hypot():
    flow, _, _ = _run((3.0, 4.0), windows=(32,))
    m = P.piv_flow_magnitude(flow)
    assert np.median(m) == pytest.approx(5.0, abs=0.05)


# =========================================================================
# 4. 既知の系統誤差 —— 出るはずのものが出るか
# =========================================================================

@pytest.mark.parametrize("mode,limit", [("gauss3", 0.02), ("parabolic", 0.05)])
def test_subpixel_estimators_track_the_true_fraction(mode, limit):
    """小数部を 0→0.9 に振って、推定が対角線に乗るかを見る。"""
    err = []
    for x in (0.1, 0.3, 0.5, 0.7, 0.9):
        a, b, _ = P.piv_synth_pair((192, 192), (0.0, 3.0 + x), density=0.02,
                                   seed=int(x * 100) + 2)
        f, _ = P.piv_cross_correlate(a, b, 32, 0.5, peak=mode)
        err.append(float(np.median(f[1])) - (3.0 + x))
    assert max(abs(e) for e in err) < limit, (mode, err)


def test_the_centroid_estimator_shows_textbook_peak_locking():
    """``centroid`` は整数へ引き寄せる —— **出ないほうがおかしい**。

    実測: 真値 0.1 を 0.02、0.9 を 0.98 と答える。3 つの推定法を残しているのは
    選択肢のためではなく、系統誤差の違いを測れるようにするため。
    """
    got = []
    for x in (0.1, 0.9):
        a, b, _ = P.piv_synth_pair((192, 192), (0.0, 3.0 + x), density=0.02,
                                   seed=int(x * 100) + 2)
        f, _ = P.piv_cross_correlate(a, b, 32, 0.5, peak="centroid")
        got.append(float(np.median(f[1])) - 3.0)
    assert got[0] < 0.06, got          # 0.1 が 0 へ寄る
    assert got[1] > 0.94, got          # 0.9 が 1 へ寄る


def test_peak_locking_metric_is_sample_size_free():
    """``c0`` は一様標本で 1 前後になる(標本数に依らない)。"""
    rng = np.random.default_rng(0)
    uniform = rng.uniform(0.0, 1.0, (2, 40, 40))
    small = rng.uniform(0.0, 1.0, (2, 12, 12))
    assert 0.5 < P.piv_peak_locking(uniform, bins=10)["c0"] < 2.0
    assert 0.3 < P.piv_peak_locking(small, bins=10)["c0"] < 3.0


# =========================================================================
# 5. 外れ値
# =========================================================================

def test_the_normalised_median_test_finds_injected_outliers():
    a, b, truth = P.piv_synth_pair((320, 320), (1.5, -2.0), density=0.02, seed=13)
    flow, info = P.piv_cross_correlate(a, b, 32, 0.5)
    rng = np.random.default_rng(0)
    bad = np.zeros(flow.shape[1:], bool)
    bad.ravel()[rng.choice(flow[0].size, 12, replace=False)] = True
    spoiled = flow.copy()
    spoiled[0][bad] += 8.0
    spoiled[1][bad] -= 7.0
    mask = P.piv_outlier_mask(spoiled, 2.0)
    assert np.all(mask[bad]), "仕込んだ外れ値を見逃した"
    assert mask.sum() - bad.sum() <= 5, "誤検出が多すぎる: %d" % (mask.sum() - bad.sum())
    t = P.piv_sample_at_windows(truth, info)
    fixed = P.piv_replace_outliers(spoiled, mask, "median")
    assert P.piv_error_stats(fixed, t)["rms"] < 1.2 * P.piv_error_stats(flow, t)["rms"]


def test_the_epsilon_keeps_an_almost_uniform_field_from_being_all_outliers():
    """分母の下駄が無いと、**理想に近い入力ほど検定が壊れる**。

    ★ 最初は「完全に一様な場」で書いて落ちた —— 完全一様だと分子も分母も 0 で
    ``0/0 = nan``、``nan > 2`` は False なので**外れ値にならない**。壊れるのは
    「ほぼ一様」のときで、残差の中央値が 1e-16 になり、同じ桁のゆらぎが
    桁違いの比になる。危ないのは理想そのものではなく**理想の隣**だった。
    """
    rng = np.random.default_rng(0)
    flow = np.zeros((2, 9, 9))
    flow[1] = 3.0 + rng.normal(0.0, 1e-6, (9, 9))    # 実測できない桁のゆらぎ
    assert not P.piv_outlier_mask(flow, 2.0, 0.1).any(), "下駄つきで誤検出した"
    assert P.piv_outlier_mask(flow, 2.0, 0.0).mean() > 0.15,         "eps=0 でも壊れないなら前提が違う"


def test_replace_outliers_can_leave_them_as_missing():
    flow = np.zeros((2, 5, 5))
    mask = np.zeros((5, 5), bool)
    mask[2, 2] = True
    out = P.piv_replace_outliers(flow, mask, "nan")
    assert np.isnan(out[:, 2, 2]).all()
    assert np.isfinite(out[:, 0, 0]).all()


# =========================================================================
# 6. 多段
# =========================================================================

def test_multipass_gives_a_denser_grid_without_losing_accuracy():
    a, b, truth = P.piv_synth_pair((H, W), (1.37, -2.62), density=0.02, seed=3)
    coarse, ci = P.piv_cross_correlate(a, b, 64, 0.5)
    multi, mi = P.piv_multipass(a, b, (64, 32), 0.5)
    assert multi.shape[1] > coarse.shape[1] * 1.5      # 格子が密になる
    sc = P.piv_error_stats(coarse, P.piv_sample_at_windows(truth, ci))
    sm = P.piv_error_stats(multi, P.piv_sample_at_windows(truth, mi))
    assert sm["rms"] < 2.0 * sc["rms"], (sm, sc)


def test_a_predictor_pointing_outside_the_image_is_clamped_not_dropped():
    """縁の窓を欠測にすると、渦度・発散が nan で内側まで潰れる(実測)。"""
    flow, info, _ = _run(rotation(0.01), shape=(320, 320))
    assert np.isfinite(flow).all()


# =========================================================================
# 7. 型と単位 —— fail-closed
# =========================================================================

def test_a_one_by_one_grid_is_refused_with_our_own_message():
    """連鎖ファザーが実際に踏んだ形(32x32 の画像に窓 32 = 格子 1x1)。

    numpy の "Shape of array too small…" がそのまま外へ出ていた —— 例外が
    出ること自体は正しいが、**どの op がなぜ拒否したのか分からない**ので
    fail-closed としては片肺だった。
    """
    tiny = np.zeros((2, 1, 1))
    for fn in (P.piv_vorticity, P.piv_divergence):
        with pytest.raises(ValueError, match="at least 2x2 vectors"):
            fn(tiny)


def test_a_3d_scene_flow_is_refused_by_every_2d_op():
    scene = np.zeros((3, 4, 8, 8))
    for fn in (P.piv_vorticity, P.piv_divergence, P.piv_flow_magnitude,
               P.piv_outlier_mask):
        with pytest.raises(ValueError, match=r"\(2, h, w\)"):
            fn(scene)


def test_the_2d_flow_is_refused_by_the_3d_family():
    """逆向きも確かめる —— 型を分けた意味は**両方向**で効いてはじめて成立する。"""
    import reprconv
    flow = np.zeros((2, 5, 5))
    with pytest.raises(ValueError):
        reprconv.flow_magnitude(flow)


def test_velocity_conversion_requires_both_scales():
    flow = np.ones((2, 3, 3))
    with pytest.raises(TypeError):
        P.piv_to_velocity(flow)                      # 既定値を置いていない
    v = P.piv_to_velocity(flow, 1e-5, 2e-4)          # 10 um/px, 200 us
    assert v[0, 0, 0] == pytest.approx(0.05)
    for bad in (0.0, -1.0, np.inf):
        with pytest.raises(ValueError):
            P.piv_to_velocity(flow, bad, 1.0)


@pytest.mark.parametrize("kw,msg", [
    ({"window": 31}, "even"),
    ({"window": 4}, ">= 8"),
    ({"window": 512}, "does not fit"),
    ({"overlap": 1.0}, r"\[0, 1\)"),
    ({"peak": "spline"}, "peak must be one of"),
    ({"window_func": "blackman"}, "window_func must be one of"),
    ({"normalize": "yes"}, "normalize must be one of"),
    ({"search_limit": 0.9}, "search_limit"),
])
def test_bad_arguments_are_refused(kw, msg):
    a = np.zeros((64, 64))
    with pytest.raises(ValueError, match=msg):
        P.piv_cross_correlate(a, a, **kw)


def test_mismatched_or_broken_images_are_refused():
    with pytest.raises(ValueError, match="same shape"):
        P.piv_cross_correlate(np.zeros((64, 64)), np.zeros((64, 32)))
    with pytest.raises(ValueError, match="non-finite"):
        P.piv_cross_correlate(np.full((64, 64), np.nan), np.zeros((64, 64)))
    with pytest.raises(ValueError, match="2-D"):
        P.piv_cross_correlate(np.zeros((4, 64, 64)), np.zeros((4, 64, 64)))


def test_synthesis_arguments_are_validated():
    with pytest.raises(ValueError, match="density"):
        P.piv_synth_particles((64, 64), density=0.0)
    with pytest.raises(ValueError, match="diameter_px"):
        P.piv_synth_particles((64, 64), diameter_px=-1.0)
    with pytest.raises(ValueError, match="noise_sigma"):
        P.piv_synth_pair((64, 64), (1.0, 1.0), noise_sigma=-0.1)
    with pytest.raises(ValueError, match="length-2"):
        P.piv_synth_pair((64, 64), (1.0, 1.0, 1.0))


# =========================================================================
# 8. 合成そのものの性質
# =========================================================================

def test_the_second_frame_is_drawn_from_moved_particles_not_a_warped_first():
    """1 枚目を補間で歪めて作ると、平滑化のぶん**自分に有利な入力**になる。

    粒子を動かして描き直していれば、変位を整数にしても 2 枚は完全一致しない
    (縁から出入りする粒子があるため)。補間で作った画像は整数変位で厳密に
    一致してしまうので、そこで区別できる。
    """
    a, b, _ = P.piv_synth_pair((96, 96), (3.0, 0.0), density=0.02, seed=4)
    shifted = np.roll(a, 3, axis=0)
    assert not np.allclose(b, shifted)
    assert np.corrcoef(b.ravel(), shifted.ravel())[0, 1] > 0.9   # ほぼ同じではある


def test_noise_lowers_the_peak_ratio():
    a0, b0, _ = P.piv_synth_pair((192, 192), (1.5, 1.5), density=0.02, seed=6)
    a1, b1, _ = P.piv_synth_pair((192, 192), (1.5, 1.5), density=0.02, seed=6,
                                 noise_sigma=0.3)
    r0 = np.nanmedian(P.piv_cross_correlate(a0, b0, 32, 0.5)[1]["peak_ratio"])
    r1 = np.nanmedian(P.piv_cross_correlate(a1, b1, 32, 0.5)[1]["peak_ratio"])
    assert r1 < r0, (r0, r1)


def test_the_truth_field_is_pixelwise_and_matches_the_displacement():
    _, _, truth = P.piv_synth_pair((64, 64), expansion(0.01))
    assert truth.shape == (2, 64, 64)
    r, c = 10, 50
    # expansion() は本モジュールの CY/CX(256 画像の中心)を基準にしている ——
    # 場の定義と画像の大きさは**別物**なので、期待値も定義に合わせる
    assert truth[0, r, c] == pytest.approx(0.01 * (r - CY))
    assert truth[1, r, c] == pytest.approx(0.01 * (c - CX))


# =========================================================================
# 9. 台帳とガイド
# =========================================================================

def test_the_ledger_lists_every_op_and_finds_its_implementation():
    import opspiv
    public = {n for n in P.__all__ if callable(getattr(P, n))}
    assert set(opspiv.OPSPIV) == public
    assert opspiv.missing() == []


def test_the_ledger_declares_the_two_element_returns_honestly():
    """``(flow, info)`` を返す op は adapter で先頭を取り出す —— 旗で返り型が
    変わる設計にはしない(台帳がどちらの姿を宣言しても嘘になるため)。"""
    import opspiv
    for name in ("piv_cross_correlate", "piv_multipass", "piv_synth_pair",
                 "piv_synth_particles"):
        assert name in opspiv.RESULT_ADAPTERS, name
    a, b, _ = P.piv_synth_pair((96, 96), (1.0, 1.0), seed=2)
    flow = opspiv.call("piv_cross_correlate", a, b, 32)
    assert flow.ndim == 3 and flow.shape[0] == 2


def test_the_fuzzer_can_build_arguments_for_every_piv_op():
    import inspect
    import sys as _sys
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if os.path.join(root, "tools") not in _sys.path:
        _sys.path.insert(0, os.path.join(root, "tools"))
    from typed_catalog import PARAM_HINTS

    import opspiv
    unbindable = []
    for name, meta in opspiv.OPSPIV.items():
        sig = inspect.signature(meta["func"])
        for p in list(sig.parameters.values())[len(meta["in"]):]:
            if p.default is inspect.Parameter.empty and p.name not in PARAM_HINTS:
                unbindable.append(f"{name}.{p.name}")
    assert not unbindable, f"ファザーが束縛できない必須引数: {unbindable}"


def test_the_family_guide_python_snippet_actually_runs():
    guide = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "docs", "ops", "piv", "guides", "piv_displacement.md")
    with open(guide, encoding="utf-8") as f:
        blocks = re.findall(r"```python\n(.*?)```", f.read(), re.S)
    runnable = [b for b in blocks if "import pivops" in b]
    assert runnable, "piv ガイドから実行できる例が消えている"
    for src in runnable:
        exec(compile(src, guide, "exec"), {"__name__": "__guide__"})


def test_the_module_states_the_conventions_that_silently_break_things():
    doc = P.__doc__ or ""
    for probe in ("(dy, dx)", "画素/フレーム", "反時計回り", "scene_flow_lk"):
        assert probe in doc, f"規約の記述 {probe!r} が docstring から消えている"
