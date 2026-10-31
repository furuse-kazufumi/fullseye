"""ViEW2026 の引数掃引で、入力軸と評価系列を取り違えないための回帰試験。"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pytest

import pocviewer as pv
from tools import build_view2026_viewers as B


CASES = [
    (B.build_focus_sweep, "F値", "f-number", "真のテクスチャとのRMSE (0–1階調)",
     "RMSE from true texture (0–1 intensity)"),
    (B.build_interferometry_sweep, "雑音 σ", "noise σ", "段差0.55 µmとの絶対差",
     "Absolute error from 0.55 µm step"),
    (B.build_polarization_sweep, "入射角", "incidence angle", "真の拡散成分とのRMSE (0–1階調)",
     "RMSE from true diffuse component (0–1 intensity)"),
    (B.build_photoelastic_sweep, "検光子角", "analyser angle", "平均輝度 (0–1)",
     "Mean intensity (0–1)"),
    (B.build_compound_sweep, "視点ごとのSNR", "per-view SNR", "無雑音像とのRMSE (0–1階調)",
     "RMSE from noise-free image (0–1 intensity)"),
    (B.build_ct_threshold_sweep, "しきい値", "threshold", "ボイド体積率",
     "Void volume fraction"),
    (B.build_active_sweep, "反復回数", "iterations", "最終輪郭との座標RMS差",
     "Coordinate RMS difference from final contour"),
]


@pytest.fixture(scope="module", params=CASES, ids=lambda c: c[0].__name__)
def sweep(request):
    fn, pja, pen, mja, men = request.param
    spec = fn()
    return fn.__name__, spec, spec["tabs"][0], pja, pen, mja, men


def test_metric_label_is_not_parameter_label(sweep):
    _, _, tab, pja, pen, mja, men = sweep
    axis_label = tab["axis"]["segments"][0]["label"]
    metric_label = tab["series"][0]["label"]
    assert (axis_label["ja"], axis_label["en"]) == (pja, pen)
    assert (metric_label["ja"], metric_label["en"]) == (mja, men)
    assert metric_label["ja"] != axis_label["ja"]
    assert metric_label["en"] != axis_label["en"]
    assert set(metric_label) == set(pv.LANGS)


def _expected_endpoints(name):
    """各 builder と同じ公開 PoC 関数から、入力値と評価値の両端を独立に求める。"""
    if name == "build_focus_sweep":
        P = B._load("poc_focus_stacking"); depth, tex = P.ground_truth(size=128, seed=7)
        focus = np.linspace(float(depth.min()), float(depth.max()), 12); xs = np.linspace(2.0, 16.0, 24)
        def metric(v, _):
            st = P.focal_stack(tex, depth, focus, f_number=float(v), layers=16)
            return P.rms(P.fuse(st, P.fm_laplacian(st), focus)[0] - tex)
    elif name == "build_interferometry_sweep":
        P = B._load("poc_interferometry_step"); xs = np.linspace(0.0, 0.12, 24)
        metric = lambda v, i: abs(float(P.measure_step(0.55, float(v), i, dz=P.DZ, n_planes=P.NP)[0]) - 0.55)
    elif name == "build_polarization_sweep":
        P = B._load("poc_polarization_specular"); d, l = P.scene(128, 160); xs = np.linspace(0, 80, 25)
        def metric(v, _):
            ss, sp = P.specular_components(l, float(v)); sep = P.separate(P.render_sweep(d, ss, sp))
            return P.rmse(np.asarray(sep[0] if isinstance(sep, tuple) else sep), d)
    elif name == "build_photoelastic_sweep":
        P = B._load("poc_photoelasticity"); _, theta, delta = P.build_fields(); xs = np.linspace(0, 135, 25)
        metric = lambda v, _: float(np.mean(P.polariscope_image(delta, theta, float(v))))
    elif name == "build_compound_sweep":
        P = B._load("poc_compound_eye"); lf, _ = P.ommatidial_scene((1.0,), occlusion=False, seed=1)
        clean = np.asarray(lf[P.V_C, P.U_C]); xs = np.geomspace(0.5, 16, 24)
        def metric(v, i):
            noisy, _, _ = P.add_photoreceptor_noise(lf, float(v), seed=i)
            return float(np.sqrt(np.mean((np.asarray(noisy[P.V_C, P.U_C]) - clean) ** 2)))
    elif name == "build_ct_threshold_sweep":
        P = B._load("poc_ct_void_morphology"); voids = P.make_voids("sphere", "spread", "interface")
        sc = P.build_scene(voids, voxel=0.06); obs = P.observe(sc["mu"], 0.06); xs = np.linspace(0.2, 0.8, 24)
        metric = lambda v, _: P.void_fraction(P.segment(obs, sc["layer"], float(v)), sc["layer"])
    else:
        P = B._load("poc_active_contours"); history = B._quiet(P.u_shape)["gvf"]["history"]
        picks = np.unique(np.rint(np.linspace(0, len(history)-1, min(24, len(history)))).astype(int))
        final = np.asarray(history[-1], float); xs = 20 * picks
        metric = lambda _, i: float(np.sqrt(np.mean((np.asarray(history[picks[i]], float) - final) ** 2)))
    return xs[[0, -1]], np.asarray([metric(xs[0], 0), metric(xs[-1], len(xs)-1)])


def test_axis_and_metric_endpoints_match_poc_calculation(sweep):
    name, _, tab, *_ = sweep
    expected_axis, expected_metric = _expected_endpoints(name)
    assert np.asarray(tab["axis"]["values"])[[0, -1]] == pytest.approx(expected_axis)
    assert np.asarray(tab["series"][0]["values"])[[0, -1]] == pytest.approx(expected_metric)


OLD_SWEEP_TITLES = {
    "引数を動かして結果を見る", "Sweep a real PoC parameter", "移动参数查看结果", "移動參數查看結果",
    "매개변수를 움직여 결과 보기", "Einen PoC-Parameter variieren",
    "PoC पैरामीटर बदलकर परिणाम देखें", "Faire varier un paramètre du PoC",
}
ROOT = Path(__file__).resolve().parents[1]


def test_sweep_title_and_watch_are_specific_and_watch_contains_numbers(sweep):
    _, spec, tab, *_ = sweep
    assert set(spec["title"]) == set(pv.LANGS)
    assert set(spec["title"].values()).isdisjoint(OLD_SWEEP_TITLES)
    assert spec["subtitle"] == tab["text"]
    assert all(re.search(r"\d", spec["subtitle"][lang]) for lang in pv.LANGS)


def test_view2026_see_and_viewer_line_match_each_sweep_title(sweep):
    _, spec, _, *_ = sweep
    data = json.loads((ROOT / "docs" / "view2026" / "exhibits.json").read_text(encoding="utf-8"))
    exhibit = next(e for e in data["exhibits"] if e["id"] == spec["id"])
    viewer = next(e for e in data["viewers"]["items"] if e["id"] == spec["id"])
    assert exhibit["see"] == spec["title"]
    assert viewer["line"] == spec["title"]
    assert set(exhibit["see"].values()).isdisjoint(OLD_SWEEP_TITLES)


def test_frames_axis_uses_physical_value_and_keeps_seconds_fallback():
    spec = B.build_photoelastic_sweep()
    html = pv._build_html(spec, list(pv.LANGS))
    assert "tab.axis ? axisText(tab, f) : (f * tab.dt).toFixed(2) + ' s'" in html
    assert "tab.axis ? '<b>' + esc(axisText(tab, f))" in html
    # anim3d の既存経路も、axis が無い場合の秒表示も残す。
    assert "tab.axis ? axisText(tab, f) : (tab.t[f] - tab.t[0]).toFixed(2) + ' s'" in html


def test_axisless_frames_still_show_playback_seconds():
    tab = pv.viewer_frames_tab("f", {"ja": "コマ", "en": "Frames"}, "passed",
                               {"ja": "説明", "en": "Text"}, np.zeros((2, 2, 2), np.uint8), dt=0.25)
    spec = pv.viewer_spec("axisless", {"ja": "題", "en": "Title"}, {"ja": "副", "en": "Sub"},
                          {"ja": "ヒント", "en": "Hint"}, [tab])
    html = pv._build_html(spec, ["ja", "en"])
    assert "(f * tab.dt).toFixed(2) + ' s'" in html
    assert "function axisText" not in html
