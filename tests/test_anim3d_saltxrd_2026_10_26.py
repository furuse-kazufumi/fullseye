# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""塩の結晶の粉末 X 線回折の動く 3-D(tools/build_saltxrd_anim3d.py)の門(2026-10-26)。

理論の線 = 門の値。op の出力(powder_reflections の d・2θ・|F|²、cif_read の密度、debye_ring_image の像)を、
op とは別に書いた閉じた式と比べる:

* Bragg: 2θ(op) = 2 asin(λ / 2d)、d(op) = a / √(h² + k² + l²)(反射 33 本、全部)
* 消滅則(Fm-3m): 混合パリティの |F|² は厳密に 0、全偶 / 全奇は 4 (f_Na ± f_Cl) e^(−Bs²) の閉じた式と一致
* 密度: cif_read = Z M / (N_A a³)、手引書の値 2.17 g/cm³ の 1 % 以内
* 限界: λ > 2d(111) では環が 0 本(op の一覧に残る 1 行は |F|² ≈ 4e-29 の数値ゼロ)
* ページ: 4 タブが学習用の型(lesson / axis / checks)を持ち、限界の回は最初でない、ok:false は limit のタブだけ
* 8 言語: 翻訳表が今の生成器の文字列と合い(未訳・古い訳・使われない訳 0)、commit 済みのページがその 8 言語版とバイト一致
"""
from __future__ import annotations

import importlib.util
import json
import math
import os
import re
import sys

import numpy as np
import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILDER = "build_saltxrd_anim3d"
PAGE = os.path.join(_ROOT, "docs", "view2026", "anim3d", "salt_xrd_anim3d.html")
TABLE = os.path.join(_ROOT, "tools", "anim3d_i18n_tables", BUILDER + ".json")


def _mod():
    for p in (os.path.join(_ROOT, "tools"), _ROOT):
        if p not in sys.path:
            sys.path.insert(0, p)
    import build_saltxrd_anim3d as B
    return B


def _load(name):
    spec = importlib.util.spec_from_file_location(name + "_saltxrd_t", os.path.join(_ROOT, "tools", name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def phase_rows():
    B = _mod()
    ph = B.load_phase()
    rr = B.rows(B.reflections(ph))
    assert len(rr) >= 30, "反射が %d 本しか無い(CIF か上限 2θ を疑う)" % len(rr)
    return B, ph, rr


@pytest.fixture(scope="module")
def built():
    B = _mod()
    res = B.run_all()
    g = B.gates(res)
    return B, res, g, B.build_spec(res, g)


# --------------------------------------------------------------------------- Bragg の閉形式
def test_two_theta_and_spacing_match_the_closed_forms_for_every_reflection(phase_rows):
    B, ph, rr = phase_rows
    a = ph["cell"][0]
    assert abs(a - 5.62) < 1e-9                                   # COD 1000041 の a
    assert len(rr) == 33
    for r in rr:
        assert abs(r["d"] - B.d_cubic(a, r["hkl"])) < 1e-12, r["hkl"]
        assert abs(r["tt"] - B.two_theta_closed(r["d"], B.LAM)) < 1e-9, r["hkl"]
    r200 = next(r for r in rr if r["hkl"] == (2, 0, 0))
    assert abs(r200["d"] - a / 2) < 1e-12
    assert abs(r200["tt"] - math.degrees(2 * math.asin(B.LAM / a))) < 1e-9
    assert math.isnan(B.two_theta_closed(3.0, 7.0))               # λ > 2d は定義域の外


def test_density_matches_z_m_over_na_a3_and_the_handbook(phase_rows):
    B, ph, _rr = phase_rows
    rho = B.density_closed(ph["cell"][0])
    assert abs(ph["density"] - rho) / rho < 1e-4                  # 原子量の桁(手引書)の違いだけ
    assert abs(ph["density"] - B.RHO_HANDBOOK) / B.RHO_HANDBOOK < 0.01
    assert 2.18 < ph["density"] < 2.19                            # a = 5.62 Å(3 桁)から出る値


# --------------------------------------------------------------------------- 消滅則
def test_mixed_parity_reflections_are_exactly_extinct_and_the_rest_match_the_closed_form(phase_rows):
    B, _ph, rr = phase_rows
    f2max = max(r["F2"] for r in rr)
    mixed = [r for r in rr if not B.parity_allowed(r["hkl"])]
    same = [r for r in rr if B.parity_allowed(r["hkl"])]
    assert len(mixed) >= 15
    assert len(same) >= 10
    for r in mixed:
        assert r["ext"] and r["F2"] < 1e-20 * f2max, r["hkl"]
    for r in same:
        assert not r["ext"] and r["F2"] > 1e-3 * f2max, r["hkl"]
    for r in rr:
        assert abs(r["F2"] - B.F2_closed(r["hkl"], r["d"])) < 1e-9 * f2max, r["hkl"]
    assert {r["hkl"] for r in mixed} >= {(1, 0, 0), (1, 1, 0), (2, 1, 0), (2, 1, 1)}
    assert {r["hkl"] for r in same} >= {(1, 1, 1), (2, 0, 0), (2, 2, 0), (3, 1, 1), (2, 2, 2), (4, 0, 0)}


def test_all_odd_is_weak_and_all_even_is_strong(phase_rows):
    B, _ph, rr = phase_rows
    f111 = next(r["F2"] for r in rr if r["hkl"] == (1, 1, 1))
    f200 = next(r["F2"] for r in rr if r["hkl"] == (2, 0, 0))
    s = 0.5 / next(r["d"] for r in rr if r["hkl"] == (1, 1, 1))
    fn, fc = B.f0("Na1+", s), B.f0("Cl1-", s)
    assert fc > fn > 0
    assert 0.02 < f111 / f200 < 0.1
    # 全奇の 8 原子の位相: Na は 0、Cl は π(逆向き)
    ph = B.atom_phases((1, 1, 1))
    assert len(ph) == 8
    for sp, phi in ph:
        want = 0.0 if sp == "Na" else math.pi
        assert abs((phi - want + math.pi) % (2 * math.pi) - math.pi) < 1e-12, (sp, phi)
    # 混合パリティの (100): Na の 4 本は 0, 0, π, π で 2 本ずつ打ち消す
    ph = B.atom_phases((1, 0, 0))
    na = sorted(round(p % (2 * math.pi), 9) for sp, p in ph if sp == "Na")
    assert na == [0.0, 0.0, round(math.pi, 9), round(math.pi, 9)]


# --------------------------------------------------------------------------- Bragg の幾何(n 枚の干渉)
def test_interference_peaks_stand_exactly_at_the_bragg_angles(phase_rows):
    B, _ph, rr = phase_rows
    d = next(r["d"] for r in rr if r["hkl"] == (2, 0, 0))
    for n, hkl in ((1, (2, 0, 0)), (2, (4, 0, 0)), (3, (6, 0, 0))):
        thb = next(r["tt"] for r in rr if r["hkl"] == hkl) / 2
        assert abs(B.interference(thb, d, B.LAM) - 1.0) < 1e-9
        assert abs(2 * d * math.sin(math.radians(thb)) - n * B.LAM) < 1e-9
        # 主極大の最初の零点は sinθ が λ/(2dN) 動いた所(θ が大きいほど山は広い)。その 1.5 倍の外は副極大(< 0.1)
        dz = math.degrees(math.asin(math.sin(math.radians(thb)) + B.LAM / (2 * d * B.N_BRAGG))) - thb
        for dth in (-1.5 * dz, 1.5 * dz):
            assert B.interference(thb + dth, d, B.LAM) < 0.1, (hkl, dth)
    th = np.linspace(20.0, 29.0, 901)                            # (200) と (400) の山の間
    vals = [B.interference(x, d, B.LAM) for x in th]
    assert len(vals) == 901 and max(vals) < 0.1


# --------------------------------------------------------------------------- 限界: λ > 2d
def test_long_wavelength_leaves_no_ring_and_the_op_edge_case_is_counted_as_zero(phase_rows):
    B, ph, rr = phase_rows
    d111 = next(r["d"] for r in rr if r["hkl"] == (1, 1, 1))
    f2_ref = max(r["F2"] for r in rr)
    assert B.LAM_END > 2 * d111
    end_rows = B.rows(B.reflections(ph, B.LAM_END, tmax=179.0, include_extinct=False))
    assert len(end_rows) >= 1                                     # op の一覧には行が残る…
    assert all(r["F2"] < 1e-20 * f2_ref for r in end_rows)        # …が全部 |F|² ≈ 0(相対しきい値の端)
    assert B.live_rows(end_rows, f2_ref) == []
    live = B.live_rows(B.rows(B.reflections(ph, 6.0, tmax=179.0, include_extinct=False)), f2_ref)
    assert [r["hkl"] for r in live] == [(1, 1, 1)]                # λ = 6.0 Å < 2d(111) なら (111) だけ残る


# --------------------------------------------------------------------------- 粉末: 点が環に乗る
def test_spots_from_random_orientations_lie_on_the_rings(phase_rows):
    B, _ph, rr = phase_rows
    allowed = [r for r in rr if not r["ext"]]
    imax = max(r["I"] for r in allowed)
    tt_edge = math.degrees(math.atan(B.DET_HALF * math.sqrt(2) / B.DET_D))
    fam = [(r["hkl"], B.equivalents(r["hkl"]), r["tt"], math.sqrt(r["I"] / imax)) for r in allowed if r["tt"] < tt_edge]
    assert len(fam) == 5
    assert len(B.equivalents((2, 0, 0))) == 6 and len(B.equivalents((1, 1, 1))) == 8 and len(B.equivalents((2, 2, 0))) == 12
    rng = np.random.default_rng(7)
    spots = []
    for _ in range(300):
        spots += B.spots_for(B.q_rot(B.q_random(rng)), fam, B.LAM)
    assert len(spots) >= 50
    byhkl = {r["hkl"]: r["tt"] for r in allowed}
    for P, bright, hkl in spots:
        tt = math.degrees(math.atan(math.hypot(P[0], P[1]) / B.DET_D))
        assert abs(tt - byhkl[hkl]) < 2 * B.TOL_DEG + 1e-9
        assert 0 < bright <= 1


# --------------------------------------------------------------------------- ページ
def test_every_tab_follows_the_textbook_flow_and_the_limit_tab_is_not_first(built):
    B, res, g, spec = built
    tabs = spec["tabs"]
    assert [t["id"] for t in tabs] == ["crystal", "bragg", "powder", "ext"]
    assert tabs[0]["badge"] == "passed" and tabs[2]["badge"] == "limit"
    for t in tabs:
        ls = t["lesson"]
        assert set(ls) == {"question", "choices", "answer", "explain", "formula", "limit"}
        assert 2 <= len(ls["choices"]) <= 3 and 0 <= ls["answer"] < len(ls["choices"])
        assert t["axis"]["values"].shape == (len(t["t"]),)
        assert t["axis"]["segments"][0]["k"] == 0
        assert len(t["checks"]) >= 3
        assert len(t["panes"]) >= 1 and t["panes"][0]["frames"].shape[0] == len(t["t"])
    assert len(tabs[2]["panes"]) == 2                            # 粉末の回は op の検出器像も並ぶ


def test_checks_come_from_the_gates_and_only_the_limit_tab_has_a_failed_row(built):
    B, res, g, spec = built
    failed = {t["id"]: [c for c in t["checks"] if not c["ok"]] for t in spec["tabs"]}
    assert failed["crystal"] == [] and failed["bragg"] == [] and failed["ext"] == []
    assert len(failed["powder"]) == 1
    assert "λ" in failed["powder"][0]["what"]["en"] and "2d(111)" in failed["powder"][0]["what"]["en"]
    assert g["rings_at_lam_end"] == 0 and g["last_B_rings"] == 0
    assert g["two_theta_max_diff_deg"] < 1e-9 and g["d_max_diff_A"] < 1e-12
    assert g["mixed_F2_max_rel"] < 1e-20 and g["F2_closed_max_rel_diff"] < 1e-9
    assert g["bragg_peak_vs_op_max_dig_deg"] < 0.002
    assert g["n_spots"] >= 100 and g["spot_two_theta_max_dev_deg"] < 2 * B.TOL_DEG
    assert g["n_image_peaks"] >= 3 and g["image_peak_vs_op_max_diff_deg"] < 0.2
    assert g["rings_cu"] == 5
    assert g["density_vs_handbook_pct"] < 1.0


def test_page_packs_with_lesson_axis_checks_and_is_under_the_size_limit(built):
    B, res, g, spec = built
    html = B.pv._build_html(spec, ["ja", "en"])
    assert "lessonTop" in html and "axisText" in html and "checksHTML" in html
    assert "**" not in html and "http://" not in html and "https://" not in html
    assert "COD 1000041" in html
    assert len(html.encode("utf-8")) < 3.3e6
    data = json.loads(re.search(r"const D = (\{.*?\});\nconst \$ = ", html, re.S).group(1))
    assert [t["id"] for t in data["tabs"]] == ["crystal", "bragg", "powder", "ext"]
    bodies = [b for t in data["tabs"] for b in t["bodies"]]
    assert len(bodies) >= 20
    assert any("alpha" in b for b in bodies)                                 # 格子面の板は半透明


# --------------------------------------------------------------------------- 8 言語
I18N = _load("anim3d_i18n")


@pytest.fixture(scope="module")
def spec_and_table():
    spec = I18N.pick_spec(I18N.capture_specs(I18N.example_script(BUILDER)), None)
    return spec, I18N.load_table(BUILDER)


def test_committed_table_passes(spec_and_table):
    spec, table = spec_and_table
    n = len({d["en"] for _, d in I18N.iter_texts(spec)})
    assert n > 50, "文字列が %d 本しか見つからない(横取りが壊れていないか)" % n
    problems, unused = I18N.audit(spec, table)
    assert problems == [], problems[:5]
    assert unused == [], unused[:5]


def test_translations_have_no_bold_marks_urls_or_local_paths(spec_and_table):
    _, table = spec_and_table
    assert len(table["strings"]) > 50
    for en, tr in table["strings"].items():
        for lang in I18N.NEW_LANGS:
            v = tr[lang]
            assert "**" not in v, (en, lang)
            assert not re.search(r"https?://|www\.|[A-Z]:\\", v), (en, lang)


def test_committed_page_is_the_eight_language_build(spec_and_table):
    spec, table = spec_and_table
    with open(PAGE, encoding="utf-8") as f:
        html = f.read()
    data = json.loads(re.search(r"const D = (\{.*?\});\nconst \$ = ", html, re.S).group(1))
    assert data["langs"] == list(I18N.LANGS)
    assert "function pickLang" in html, "ブラウザの言語で開く(detect_lang)になっていない"
    want = I18N.pv._build_html(I18N.translate(spec, table), list(I18N.LANGS), detect_lang=True)
    I18N.check_same_page(html, want, PAGE, BUILDER)
    assert os.path.getsize(PAGE) < 3.3e6
