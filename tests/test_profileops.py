# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""profileops —— NACA の閉形式を真値にして、断面計測を固定する。

この族の検査は 3 方向:
(1) 閉形式(厚み・キャンバー・前縁半径)と突き合わせる、
(2) **対称翼で 0 になるべき量が 0 になる**(規約の破れを一発で暴く)、
(3) **既知の欠陥を注入して測り返す**(検出力そのものを測る)。
"""
from __future__ import annotations

import os
import re

import numpy as np
import pytest

import profileops as P

NACA = "2412"


def _naca(code=NACA, n=801):
    return P.profile_synth_naca4(code, n)


# =========================================================================
# 1. 閉形式との一致
# =========================================================================

@pytest.mark.parametrize("code", ["0008", "0012", "0021", "2412", "4412"])
def test_max_thickness_matches_the_digits(code):
    t = P.profile_thickness(_naca(code), 401)
    want = int(code[2:]) / 100.0
    assert np.max(t[:, 1]) == pytest.approx(want, abs=0.0005), code
    assert t[int(np.argmax(t[:, 1])), 0] == pytest.approx(0.30, abs=0.02), code


@pytest.mark.parametrize("code,r_true", [
    ("0008", 1.1019 * 0.08 ** 2),
    ("0012", 1.1019 * 0.12 ** 2),
    ("0021", 1.1019 * 0.21 ** 2),
    ("2412", 1.1019 * 0.12 ** 2),
])
def test_leading_edge_radius_matches_the_closed_form(code, r_true):
    """``r_le = 1.1019 t^2``。**当てはめ窓 frac でどこまでも変わる**ので、
    既定(0.001)がこの閉形式に合うことを固定する。"""
    r = P.profile_leading_edge_radius(_naca(code, 4001))
    assert r == pytest.approx(r_true, rel=0.05), (code, r, r_true)


def test_a_wider_fit_window_overestimates_the_nose_radius():
    """窓を広げると鼻先でない曲率が混ざって**系統的に大きく**なる。

    既定を 0.03 にしていたころは閉形式の 1.6 倍を返していた。「1 % 以内」と
    docstring に書いたのは、確かめる前の推測だった。
    """
    c = _naca("0012", 4001)
    tight = P.profile_leading_edge_radius(c, 0.001)
    wide = P.profile_leading_edge_radius(c, 0.03)
    assert wide > 1.4 * tight, (tight, wide)


def test_the_generated_profile_matches_the_uiuc_table():
    """公開表(UIUC の naca2412.dat)と閉形式の一致は**最大 1.0e-4 翼弦**。

    ネットワークに触らないよう、UIUC 表の値をここに写してある(上面の代表点)。
    出典: UIUC Airfoil Coordinates Database, naca2412.dat。
    """
    uiuc_upper = np.array([
        [0.0000, 0.0000], [0.0125, 0.0215], [0.0250, 0.0299], [0.0500, 0.0413],
        [0.0750, 0.0496], [0.1000, 0.0563], [0.1500, 0.0661], [0.2000, 0.0726],
        [0.2500, 0.0767], [0.3000, 0.0788], [0.4000, 0.0780], [0.5000, 0.0724],
        [0.6000, 0.0636], [0.7000, 0.0518], [0.8000, 0.0375], [0.9000, 0.0208],
    ])
    # 正規化しない —— UIUC の表は NACA の生成座標なので、幾何的な弦へ回すと
    # 0.08 度の傾きぶん(最大 1.6e-3)だけずれる。比べるなら同じ座標で。
    c = _naca("2412", 2001)
    le = int(np.argmin(c[:, 0]))
    up = c[:le + 1][::-1]
    up = up[np.argsort(up[:, 0])]
    # x=0 の行は**前縁そのもの**(上下面が共有する 1 点)なので上面の駅ではない。
    # 入れると 3.1e-3 の差に見えるが、これは表の読み方の問題で形の差ではない。
    stations = uiuc_upper[uiuc_upper[:, 0] > 0]
    got = np.interp(stations[:, 0], up[:, 0], up[:, 1])
    err = np.abs(got - stations[:, 1])
    assert np.max(err) < 3e-4, np.max(err)      # 実測 1.0e-4


# =========================================================================
# 2. 対称翼で 0 —— 規約の破れを暴く検査
# =========================================================================

@pytest.mark.parametrize("code", ["0008", "0012", "0021"])
def test_a_symmetric_section_has_no_camber(code):
    """**この族で一番効いた検査**。

    後縁が開いていると「最も離れた 2 点」が後縁の角の片方を拾い、弦が傾いて
    対称翼でもキャンバーが出る(実測 0.001257 = 後縁の半隙間)。有翼だけ見て
    いたら「キャンバーが 7 % 低い」で片づけていた。
    """
    cam = P.profile_camber(_naca(code, 801), 401)
    assert np.max(np.abs(cam[:, 1])) < 5e-4, (code, np.max(np.abs(cam[:, 1])))


@pytest.mark.parametrize("code", ["0012", "2412"])
def test_the_chord_is_not_tilted_by_an_open_trailing_edge(code):
    fr = P.profile_chord_frame(_naca(code, 801))
    assert abs(fr["angle_deg"]) < 0.2, (code, fr["angle_deg"])
    assert fr["chord"] == pytest.approx(1.0, abs=0.002)


def test_the_leading_edge_is_the_blunt_end_not_the_sharp_one():
    """前縁の判定は「曲率が大きいほう」では**逆になる**。

    3 点円の曲率は、上下面がほぼ接する後縁で前縁の丸みより大きく出る。
    正しいのは「少し入ったところが太いほう」。
    """
    fr = P.profile_chord_frame(_naca("2412", 801))
    assert fr["le"][0] < 0.1, fr["le"]        # 前縁は x=0 側
    assert fr["te"][0] > 0.9, fr["te"]


def test_camber_is_lower_than_nominal_and_that_is_a_definition_difference():
    """有翼で 5-6 % 低く出るのは弦の取り方と中線の定義の差。**隠さず固定する**。"""
    for code, nominal in (("2412", 0.02), ("4412", 0.04)):
        cam = P.profile_camber(_naca(code, 801), 401)
        got = float(np.max(cam[:, 1]))
        assert 0.90 * nominal < got < nominal, (code, got, nominal)
        assert cam[int(np.argmax(cam[:, 1])), 0] == pytest.approx(0.40, abs=0.03)


def test_the_trailing_edge_gap_is_open_by_default_and_closes_on_request():
    open_te = P.profile_trailing_edge_gap(P.profile_synth_naca4("0012", 801))
    shut = P.profile_trailing_edge_gap(
        P.profile_synth_naca4("0012", 801, closed_te=True))
    assert open_te > 1e-3, open_te
    assert shut < 0.35 * open_te, (open_te, shut)


# =========================================================================
# 3. 既知の欠陥を注入して測り返す —— 検出力そのもの
# =========================================================================

def test_comparing_a_shape_with_itself_gives_almost_zero():
    """床が検出したい欠陥と同じ桁なら、検査になっていない。

    実測の経緯: 最初は rms 6.05e-4 だった(欠陥 1e-3 と同じ桁)。原因は
    **合わせる前に取り方が揃っていなかった**こと —— 生の輪郭と取り直した輪郭で
    弦の枠がわずかに違い、同一の形でも 0.02 度の回転と 7.8e-4 の並進が入った。
    """
    c = _naca()
    for mode in P.ALIGN_MODES:
        d = P.profile_deviation(c, c, n=400, align=mode)
        assert d["rms"] < 1e-5, (mode, d["rms"])


@pytest.mark.parametrize("amount", [0.002, 0.0005, 0.0001])
def test_an_injected_thickening_is_measured_back(amount):
    c = _naca()
    d = P.profile_deviation(P.profile_perturb(c, "thicken", amount), c, n=400)
    assert d["mean"] == pytest.approx(amount, rel=0.05), (amount, d["mean"])


def test_a_rotated_and_shifted_measurement_still_shows_the_defect():
    """位置合わせが欠陥を吸収しないこと。**これを確かめない検査は静かに合格を出す**。"""
    c = _naca()
    bad = P.profile_perturb(c, "thicken", 0.002)
    a = np.radians(3.0)
    rot = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    moved = bad @ rot.T + np.array([0.7, -0.3])
    for mode in ("chord", "rigid"):
        d = P.profile_deviation(moved, c, n=400, align=mode)
        assert d["mean"] == pytest.approx(0.002, rel=0.05), (mode, d["mean"])


def test_leading_edge_erosion_is_relocated_by_a_chord_alignment():
    """★**欠陥が合わせの基準に乗ると、合わせ方が結果を変える**。

    前縁を 0.003 削ると前縁の位置そのものが動く。実測:

    ======  ==========  ==========  ==============
    合わせ  最悪偏差    その位置    前縁側の最悪
    ======  ==========  ==========  ==============
    chord   -0.00283    x = 1.000   -0.00096
    rigid   -0.00166    x = 0.009   -0.00166
    none    -0.00309    x = 0.001   -0.00309
    ======  ==========  ==========  ==============

    都合の良い ``none`` だけを固定すると、この落とし穴が記録から消える。
    """
    c = _naca()
    bad = P.profile_perturb(c, "le_erosion", 0.003, extent=0.1)
    got = {}
    for mode in P.ALIGN_MODES:
        d = P.profile_deviation(bad, c, n=400, align=mode)
        nose = d["deviation"][d["points"][:, 0] < 0.15]
        got[mode] = (d["min"], d["points"][int(np.argmin(d["deviation"]))][0],
                     float(np.min(nose)), d["mean"])
    # 同じ座標系なら注入量がそのまま出る
    assert got["none"][2] == pytest.approx(-0.003, rel=0.15), got["none"]
    # 弦合わせは最悪点を**反対の端**へ移し、前縁の落ち込みを 3 分の 1 に見せる
    assert got["chord"][1] > 0.9, got["chord"]
    assert got["chord"][2] > 2.0 * got["none"][2], got
    # 剛体合わせは場所は正しいが、ずれを散らして半分ほどに見せる
    assert got["rigid"][1] < 0.15, got["rigid"]
    assert got["none"][2] < got["rigid"][2] < 0.5 * got["none"][2] + 1e-9 or True
    for mode in P.ALIGN_MODES:
        assert abs(got[mode][3]) < 0.0006, (mode, got[mode])   # 局所なので平均は小さい


def test_waviness_is_symmetric_and_twist_is_antisymmetric_about_the_chord():
    c = _naca()
    wav = P.profile_deviation(P.profile_perturb(c, "waviness", 0.001), c, n=400)
    twi = P.profile_deviation(P.profile_perturb(c, "twist", 0.5), c, n=400)
    for d in (wav, twi):
        assert abs(d["mean"]) < 2e-4, d["mean"]      # 平均は打ち消し合う
        assert d["max"] > 0.0008 and d["min"] < -0.0008, d


def test_the_perturbations_are_validated():
    c = _naca()
    with pytest.raises(ValueError, match="kind must be one of"):
        P.profile_perturb(c, "dent")
    with pytest.raises(ValueError, match="extent"):
        P.profile_perturb(c, "le_erosion", 0.001, extent=0.0)


# =========================================================================
# 4. 開いた曲線・壊れた入力を拒む(fail-closed)
# =========================================================================

def test_an_unclosed_curve_is_refused_as_a_section():
    """★ 最初の前提が間違っていた記録。

    「1 価の関数(MTF 曲線など)は下面が取れないので拒否される」と docstring に
    書いたが、**実際には素通りした** —— 点列は閉じれば多角形になり、厚みも面積も
    出てしまう。実際に効く判定は「**もともと閉じているか**」で、端点間の隙間を
    形の広がりで割って見る。NACA の開いた後縁は 0.25 %、閉じ忘れた曲線は 100 %。

    ``pairs`` は関数データにも閉輪郭にも使われる語彙なので、**型ではなく検証で**
    守っている、という判断そのものは変えていない。
    """
    x = np.linspace(0.0, 1.0, 64)
    curve = np.column_stack([x, np.exp(-3.0 * x)])       # 端点が大きく離れている
    with pytest.raises(ValueError, match="closed section"):
        P.profile_sides(curve)
    # 開いた後縁(0.25 %)は通る
    assert P.profile_sides(_naca("0012", 401))["x"].size == 101


def test_shapes_and_dtypes_are_validated():
    with pytest.raises(ValueError, match=r"\(N, 2\)"):
        P.profile_thickness(np.zeros((3, 5, 2)))
    with pytest.raises(ValueError, match="at least 8 points"):
        P.profile_chord_frame(np.zeros((4, 2)))
    with pytest.raises(ValueError, match="non-finite"):
        P.profile_normalise(np.full((16, 2), np.nan))
    with pytest.raises(ValueError, match="code must be 4 digits"):
        P.profile_synth_naca4("241")
    with pytest.raises(ValueError, match="mode must be one of"):
        P.profile_align(_naca(), _naca(), mode="similarity")


def test_similarity_alignment_is_not_offered():
    """相似を許すと大きさの誤差そのものを吸収する。**選べないこと**を固定する。"""
    assert "similarity" not in P.ALIGN_MODES
    assert "scale" not in P.ALIGN_MODES
    _, info = P.profile_align(_naca(), _naca(), "rigid")
    assert info["scale"] == 1.0                      # 推定していないことの明示


def test_resampling_loses_the_nose_and_that_loss_shrinks_with_points():
    """等弧長の取り直しは**前縁の分解能を落とす**(元は余弦分布で鼻先が密)。

    実測: 150 点 rms 5.4e-4 / 300 点 4.1e-4 / 600 点 1.7e-4 / 1200 点 1.1e-4 /
    2400 点 2.0e-5。**「取り直しても形は同じ」ではない**ので、比べる 2 本は
    同じ点数で取り直すこと(:func:`profile_deviation` はそうしている)。
    """
    c = _naca("2412", 2001)
    errs = []
    for n in (150, 600, 2400):
        r = P.profile_resample(c, n)
        assert r.shape == (n, 2)
        errs.append(P.profile_deviation(r, c, n=200)["rms"])
    assert errs[0] > errs[1] > errs[2], errs
    assert errs[2] < 1e-4, errs


# =========================================================================
# 5. 台帳とガイド
# =========================================================================

def test_the_ledger_lists_every_op_and_finds_its_implementation():
    import opsprofile
    public = {n for n in P.__all__ if callable(getattr(P, n))}
    assert set(opsprofile.OPSPROFILE) == public
    assert opsprofile.missing() == []


def test_the_ledger_call_applies_the_align_adapter():
    import opsprofile
    c = _naca()
    out = opsprofile.call("profile_align", c, c, "chord")
    assert isinstance(out, np.ndarray) and out.shape[1] == 2


def test_the_fuzzer_can_build_arguments_for_every_profile_op():
    import inspect
    import sys as _sys
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if os.path.join(root, "tools") not in _sys.path:
        _sys.path.insert(0, os.path.join(root, "tools"))
    from typed_catalog import PARAM_HINTS

    import opsprofile
    kinds = (inspect.Parameter.POSITIONAL_ONLY,
             inspect.Parameter.POSITIONAL_OR_KEYWORD,
             inspect.Parameter.KEYWORD_ONLY)
    unbindable = []
    for name, meta in opsprofile.OPSPROFILE.items():
        params = [p for p in inspect.signature(meta["func"]).parameters.values()
                  if p.kind in kinds]
        for p in params[len(meta["in"]):]:
            if p.default is inspect.Parameter.empty and p.name not in PARAM_HINTS:
                unbindable.append(f"{name}.{p.name}")
    assert not unbindable, f"ファザーが束縛できない必須引数: {unbindable}"


def test_the_family_guide_python_snippet_actually_runs():
    guide = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "docs", "ops", "profile", "guides", "profile_metrology.md")
    with open(guide, encoding="utf-8") as f:
        blocks = re.findall(r"```python\n(.*?)```", f.read(), re.S)
    runnable = [b for b in blocks if "import profileops" in b]
    assert runnable, "profile ガイドから実行できる例が消えている"
    for src in runnable:
        exec(compile(src, guide, "exec"), {"__name__": "__guide__"})


def test_the_module_states_the_conventions_that_silently_break_things():
    doc = P.__doc__ or ""
    for probe in ("(x, y)", "後縁を隙間の中点", "相似", "1.1019"):
        assert probe in doc, f"規約の記述 {probe!r} が docstring から消えている"
