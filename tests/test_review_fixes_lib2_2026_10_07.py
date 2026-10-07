# -*- coding: utf-8 -*-
"""2026-10-07 の門の強化で見つかったライブラリ欠陥(lib2)の回帰テスト。

``tests/test_op_contracts.KNOWN_FALLS_BACK_ON_EDGE`` の bug-suspect 8 行、
``tests/test_degenerate_inputs.KNOWN_NONFINITE_ON_EMPTY_INPUT`` の 16 op、
``tests/test_fix_op_name_and_range_2026_09_02.KNOWN_OUT_OF_UNIT_RANGE_PENDING`` の 1 行を直した。
台帳の門は「落ちる / 落ちない」しか見ないので、ここでは**直した後の値が正しいこと**を
独立の経路(公開関数を直接呼ぶ・閉形式)で確かめる。

* B ``tb_cx_apply_transfer_function`` —— H をスペクトルと同じ形で作る(固定 32x32 をやめた)
* C ``tb_temporal_band_power`` / ``tb_temporal_bandpass`` —— 帯域を動画自身の DFT ビンから選ぶ
* D ``img_to_monogenic`` —— 波長 ``3 + 12 a``(a=0 が 2 px = ナイキストで拒否されていた)
* E ``tb_local_std`` —— window ∈ [3, 17](a=0 が 2)
* F ``tb_fit_spline_curve`` —— k ∈ [1, 5](a=1 が 6)
* G ``estimate_point_normals`` —— 3 近傍未満は明示の ValueError(einsum の内部エラーだった)
* H ``xsk_inpaint`` —— 全画素が欠損扱いなら入力をそのまま返す(空配列の min で落ちていた)
* I ``tb_normals_to_egi`` —— 橋の出口で割合([0,1]、和 1)。公開関数は計数のまま
* J 空入力の 0/0 —— 本体の明示拒否 + 橋の後始末 ``_fallback`` が NaN を作らない
* K 追跡されている .py に手元の絶対パスを置かない
"""
from __future__ import annotations

import os
import re
import subprocess

import numpy as np
import pytest

import backend_safe as _bs
import ops
from conftest import KNOBS, copy_input, inputs_for

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BY = {op.name: op for op in ops.REGISTRY}


def _op(name):
    op = BY.get(name)
    if op is None:
        pytest.skip("%s が登録されていない(optional backend 不在)" % name)
    return op


def _run_clean(name, v, a, b):
    """op を 1 回呼び、guard の fallback が**起きていない**ことを確かめて返す。"""
    m = _bs.mark()
    out = BY[name].fn(copy_input(v), a, b)
    ev = _bs.events_since(m, this_thread=False)
    assert _bs.mark() == m, "%s @ (a=%s, b=%s) が fallback した: %s" % (
        name, a, b, [(e["source"], str(e["error"])[:160]) for e in ev])
    return out


# --------------------------------------------------------------------------- #
# B: tb_cx_apply_transfer_function                                              #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("shape", [(24, 24), (32, 32), (128, 128), (17, 40)])
def test_cx_transfer_function_matches_any_spectrum_shape(shape):
    _op("tb_cx_apply_transfer_function")
    import complexops as cx

    rng = np.random.default_rng(0)
    spec = cx.cx_fft(rng.random(shape))
    for a, b in KNOBS:
        out = _run_clean("tb_cx_apply_transfer_function", spec, a, b)
        assert np.iscomplexobj(out) and out.shape == shape
        # 独立経路: 中心化ガウス H を閉形式で作って掛けたものと一致
        sigma = 0.02 + 0.48 * a
        fy = np.fft.fftshift(np.fft.fftfreq(shape[0]))
        fx = np.fft.fftshift(np.fft.fftfreq(shape[1]))
        H = np.exp(-0.5 * (fy[:, None] ** 2 + fx[None, :] ** 2) / sigma ** 2)
        np.testing.assert_allclose(out, spec * H, rtol=0, atol=1e-12)


def test_cx_transfer_function_knob_a_is_live_and_dc_is_kept():
    _op("tb_cx_apply_transfer_function")
    import complexops as cx

    spec = cx.cx_fft(np.random.default_rng(1).random((32, 32)))
    lo = _run_clean("tb_cx_apply_transfer_function", spec, 0.0, 0.5)
    hi = _run_clean("tb_cx_apply_transfer_function", spec, 1.0, 0.5)
    c = (16, 16)                                        # DC(中心化)は低域通過で動かない
    assert lo[c] == pytest.approx(spec[c]) and hi[c] == pytest.approx(spec[c])
    assert np.abs(lo).sum() < np.abs(hi).sum()          # 幅の狭い H ほどエネルギーを落とす


# --------------------------------------------------------------------------- #
# C: temporal band                                                             #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", ["tb_temporal_band_power", "tb_temporal_bandpass"])
@pytest.mark.parametrize("t", [2, 3, 8, 12, 64])
def test_temporal_band_always_holds_a_bin(name, t):
    _op(name)
    rng = np.random.default_rng(t)
    vid = rng.random((t, 6, 5))
    for a, b in KNOBS:
        out = _run_clean(name, vid, a, b)
        assert np.all(np.isfinite(out))


def test_temporal_band_power_is_parseval_exact_on_the_selected_bin():
    """12 フレーム・32 fps でビン 1(2.67 Hz)に振幅 0.3 の正弦 → a=0,b=0 の帯域で 0.3^2/2。"""
    _op("tb_temporal_band_power")
    import motionmag as mm

    t = np.arange(12)[:, None, None]
    vid = (0.5 + 0.3 * np.cos(2 * np.pi * 1 * t / 12)
           + 0.2 * np.cos(2 * np.pi * 4 * t / 12)) * np.ones((12, 4, 4))
    p_bin1 = _run_clean("tb_temporal_band_power", vid, 0.0, 0.0)
    np.testing.assert_allclose(p_bin1, 0.3 ** 2 / 2, rtol=1e-12)
    # 独立経路: 公開関数にビン 1 だけを囲む帯域を直接渡す
    df = 32.0 / 12
    ref = mm.temporal_band_power(vid, 0.5 * df, 1.5 * df, 32.0)
    np.testing.assert_allclose(p_bin1, ref, rtol=1e-12)
    # a=1(ナイキスト側の最上位ビン 6)、b=0 → ビン 4 の成分は入らない
    p_top = _run_clean("tb_temporal_band_power", vid, 1.0, 0.0)
    np.testing.assert_allclose(p_top, 0.0, atol=1e-20)
    # a は帯域を動かす: ビン 4 を中心に取ると 0.2^2/2
    p_bin4 = _run_clean("tb_temporal_band_power", vid, 0.6, 0.0)   # kc = 1 + round(0.6*5) = 4
    np.testing.assert_allclose(p_bin4, 0.2 ** 2 / 2, rtol=1e-12)


def test_temporal_single_frame_is_still_refused():
    """1 フレームには時間周波数が無い —— ここは拒否のまま(明示の拒否文で)。"""
    import motionmag as mm

    with pytest.raises(ValueError, match="T=1"):
        mm.temporal_band_power(np.zeros((1, 4, 4)), 1.0, 2.0, 32.0)


# --------------------------------------------------------------------------- #
# D: img_to_monogenic                                                          #
# --------------------------------------------------------------------------- #
def test_monogenic_knob_range_stays_inside_the_domain():
    _op("img_to_monogenic")
    import quatimage as Q

    img = np.random.default_rng(2).random((32, 32))
    for a, b in KNOBS:
        out = _run_clean("img_to_monogenic", img, a, b)
        assert out.shape == (32, 32, 4)
    # a=0.5 の 9 px は据え置き(図・既定の挙動は動かない)、a=0 は 3 px
    ref = Q.monogenic_signal(img, wavelength_px=9.0, bandwidth_octaves=1.125)
    np.testing.assert_allclose(_run_clean("img_to_monogenic", img, 0.5, 0.5), ref, atol=1e-12)
    ref0 = Q.monogenic_signal(img, wavelength_px=3.0, bandwidth_octaves=1.125)
    np.testing.assert_allclose(_run_clean("img_to_monogenic", img, 0.0, 0.5), ref0, atol=1e-12)


# --------------------------------------------------------------------------- #
# E / F: 整数引数の絶対範囲                                                       #
# --------------------------------------------------------------------------- #
def test_local_std_window_range():
    _op("tb_local_std")
    import dsp

    x = np.random.default_rng(3).random(64)
    for a, w in ((0.0, 3), (0.5, 10), (1.0, 17)):
        np.testing.assert_allclose(_run_clean("tb_local_std", x, a, 0.5), dsp.local_std(x, w),
                                   atol=1e-12)


def test_fit_spline_curve_degree_range():
    _op("tb_fit_spline_curve")
    import curve3d

    s = np.linspace(0, 3, 20)
    P = np.stack([np.cos(s), np.sin(s), 0.1 * s], axis=1)
    for a, k in ((0.0, 1), (0.5, 3), (1.0, 5)):
        np.testing.assert_allclose(_run_clean("tb_fit_spline_curve", P, a, 0.5),
                                   curve3d.fit_spline_curve(P, k=k), atol=1e-12)


# --------------------------------------------------------------------------- #
# G: estimate_point_normals                                                    #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("pts,k", [(np.zeros((1, 3)), 16), (np.eye(3)[:2], 16),
                                   (np.random.default_rng(4).random((10, 3)), 2)])
def test_point_normals_refuse_fewer_than_three_neighbours(pts, k):
    import match3d

    with pytest.raises(ValueError, match="at least 3 neighbours"):
        match3d.estimate_point_normals(pts, k=k)


def test_point_normals_refuse_a_wrong_shape_and_keep_valid_results():
    import match3d

    with pytest.raises(ValueError, match=r"\(N, 3\)"):
        match3d.estimate_point_normals(np.zeros((5, 2)))
    # 平面 z=0 の点群: 法線は ±z(既定の向きは重心から外向き = 平面では符号は任意)
    g = np.stack(np.meshgrid(np.arange(5.0), np.arange(5.0)), -1).reshape(-1, 2)
    P = np.column_stack([g, np.zeros(len(g))])
    n = match3d.estimate_point_normals(P, k=8)
    np.testing.assert_allclose(np.abs(n[:, 2]), 1.0, atol=1e-9)


# --------------------------------------------------------------------------- #
# H: xsk_inpaint                                                               #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("fill", [0.0, 1.0, 0.03, 0.97])
def test_inpaint_returns_an_all_masked_image_unchanged(fill):
    _op("xsk_inpaint")
    img = np.full((16, 16), fill)
    out = _run_clean("xsk_inpaint", img, 0.5, 0.5)
    np.testing.assert_array_equal(out, img)


def test_inpaint_still_fills_a_partial_mask():
    _op("xsk_inpaint")
    img = np.full((16, 16), 0.5)
    img[7:9, 7:9] = 1.0                                   # 欠損(> 0.92)
    out = _run_clean("xsk_inpaint", img, 0.5, 0.5)
    np.testing.assert_allclose(out[7:9, 7:9], 0.5, atol=1e-6)


# --------------------------------------------------------------------------- #
# I: tb_normals_to_egi                                                         #
# --------------------------------------------------------------------------- #
def test_egi_bridge_returns_fractions_and_public_function_keeps_counts():
    _op("tb_normals_to_egi")
    import reprconv

    n = np.random.default_rng(5).normal(size=(200, 3))
    n /= np.linalg.norm(n, axis=1, keepdims=True)
    n[:60] = (0.0, 0.0, 1.0)                              # 1 つの bin に 60 本 → 計数なら 60 以上
    counts = reprconv.normals_to_egi(n)
    assert counts.sum() == 200 and counts.max() >= 60     # 公開関数は計数のまま
    for a, b in KNOBS:
        out = _run_clean("tb_normals_to_egi", n, a, b)
        assert out.min() >= 0.0 and out.max() <= 1.0
        assert out.sum() == pytest.approx(1.0)
    out = _run_clean("tb_normals_to_egi", n, 0.5, 0.5)
    np.testing.assert_allclose(out, reprconv.normals_to_egi(n, n_az=40, n_el=20) / 200.0)


def test_egi_unit_range_holds_on_every_probe():
    """[0,1] の門を運で通っていた探針(ばらばらの単位法線)以外でも [0,1]。"""
    op = _op("tb_normals_to_egi")
    for iname, iv in inputs_for(op.in_sort, op.name):
        for a, b in ((0.2, 0.5), (0.5, 0.5), (0.8, 0.3)):
            out = np.asarray(op.fn(copy_input(iv), a, b), np.float64)
            assert out.min() >= 0.0 and out.max() <= 1.0 + 1e-12, iname


# --------------------------------------------------------------------------- #
# J: 空入力の 0/0                                                               #
# --------------------------------------------------------------------------- #
_EMPTY_FIXED = ["area_frac", "gray_histo_abs", "hx_estimate_sl_al_lr", "hx_estimate_sl_al_zc",
                "hx_estimate_tilt_lr", "hx_estimate_tilt_zc", "intensity", "sk_blur_effect",
                "tb_cplx_cr_residual", "tb_dtof_depth", "tb_dynsys_correlation_dimension",
                "tb_equivalent_level", "tb_estimate_alpha", "tb_get_y_value_funct_1d",
                "tb_reflection_symmetry_score", "tb_superquadric_residual"]
_EMPTY = {"image": (0, 0), "region": (0, 0), "cimage": (0, 0), "points": (0, 3),
          "signal": (0,), "counts": (0,)}


@pytest.mark.parametrize("name", _EMPTY_FIXED)
def test_empty_input_never_produces_a_nonfinite_value(name):
    op = _op(name)
    v = np.zeros(_EMPTY[op.in_sort], dtype=complex if op.in_sort == "cimage" else float)
    m = _bs.mark()
    out = op.fn(v, 0.5, 0.5)
    ev = _bs.events_since(m, this_thread=False)
    assert ev, "%s: 空入力で明示の拒否が記録されていない" % name   # 下の 2 つの表明の母数
    assert not any(e["source"] == "output" for e in ev), (
        "%s: 空入力で本体か橋の後始末が NaN/Inf を出し guard が置き換えた: %s" % (name, ev))
    assert np.all(np.isfinite(np.asarray(out, np.float64)))
    # 0/0 は**黙った値**ではなく明示の拒否(op の台帳に ValueError が残る)
    assert any(e["source"] == "op" and "ValueError" in str(e["error"]) for e in ev), ev


def test_typed_fallback_for_feature_is_zero_on_empty_and_mean_otherwise():
    import backends_typed as bt

    assert bt._fallback(np.zeros((0, 3)), "points", "feature") == 0.0
    assert bt._fallback(np.array([1.0, 3.0]), "signal", "feature") == 2.0


def test_superquadric_residual_refuses_an_empty_cloud():
    import superquadric as sq

    with pytest.raises(ValueError, match="empty point cloud"):
        sq.superquadric_residual(np.zeros((0, 3)), (1, 1, 1), (1, 1), np.eye(3), np.zeros(3))


# --------------------------------------------------------------------------- #
# K: 手元の絶対パス                                                              #
# --------------------------------------------------------------------------- #
#: この機械の作業場所の形(ドライブ文字 + 区切り + 作業ディレクトリの頭)。**OS の標準の
#: 場所(Windows のフォント、Program Files)は機械固有ではないので数えない**。
_LOCAL_ROOT = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]{1,2}"
                         r"(?:dev|Users|docs|projects|data|api-keys\.json)(?![A-Za-z0-9_])")

#: 免除は理由つきで名指しする。
_EXEMPT_FILES = {
    "tests/test_docs_no_local_paths.py": "門の破壊試験。綴りの見本を意図して本文に持つ",
    "tests/test_exhibits.py": "展示の生成器が手元パスを拒否することを確かめる fixture",
}


def _tracked_py():
    try:
        out = subprocess.run(["git", "-C", ROOT, "ls-files", "*.py"], capture_output=True,
                             text=True, check=True).stdout.split()
        if out:
            return sorted(out)
    except (OSError, subprocess.CalledProcessError):
        pass
    found = []                                            # git の無い展開(sdist / archive)
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = sorted(d for d in dn if not d.startswith(".")
                       and d not in ("build", "dist", "venv", "node_modules", "__pycache__"))
        found += [os.path.relpath(os.path.join(dp, f), ROOT).replace(os.sep, "/")
                  for f in fn if f.endswith(".py")]
    return sorted(found)


def test_no_tracked_python_file_carries_a_local_work_path():
    files = _tracked_py()
    assert len(files) > 500, "対象の .py が %d 本しか無い(列挙が壊れている)" % len(files)
    bad = []
    for rel in files:
        if rel in _EXEMPT_FILES:
            continue
        with open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace") as f:
            for i, ln in enumerate(f, 1):
                if _LOCAL_ROOT.search(ln):
                    bad.append("%s:%d  %s" % (rel, i, ln.strip()[:100]))
    assert not bad, ("手元の絶対パスが %d か所(Path(__file__) から求めるか環境変数で受ける):\n  %s"
                     % (len(bad), "\n  ".join(bad[:20])))


@pytest.mark.parametrize("line", [
    "ROOT = r'" + "C" + ":\\dev\\projects\\imgevolve'",
    "x = '" + "C" + ":/dev/projects/foo'",
    "p = r'" + "D" + ":\\docs\\image_corpus'",
    "k = '" + "D" + ":/api-keys.json'",
    "s = '" + "C" + ":\\\\dev\\\\data\\\\tid2013'",
])
def test_the_local_path_pattern_catches_each_spelling(line):
    assert _LOCAL_ROOT.search(line), line


@pytest.mark.parametrize("line", [
    "FONT = 'C" + ":/Windows/Fonts/meiryo.ttc'",
    "cl = r'C" + ":\\Program Files\\Microsoft Visual Studio'",
    "path = os.path.join(ROOT, 'docs', 'x.md')",
])
def test_the_local_path_pattern_ignores_os_standard_places(line):
    assert not _LOCAL_ROOT.search(line), line


def test_exemptions_still_earn_their_place():
    for rel, why in _EXEMPT_FILES.items():
        assert why.strip()
        with open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace") as f:
            assert _LOCAL_ROOT.search(f.read()), "免除が不要になった: %s" % rel
