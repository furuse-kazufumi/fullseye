# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""レンズ 1 枚から光学系へ(tools/build_lens_system_anim3d.py)の門。

理論の線(結像公式・レンズメーカーの式・ABCD・cos⁴)= 門の値。op の値をそれに当て、実光線(trace_rays)が
近軸の式から外れる所は「限界」として、外れが本当にあること(と、外れない所では合うこと)を確かめる。

* 薄レンズ: thin_lens(主点から測る)と paraxial_trace の像の位置が 1e-9 で一致。a = 2f で m = −1。
  開口を絞った実光線(半径の 5%)は近軸の像に 0.1% で寄る(独立経路)。縁寄りの実光線は f の近くで 10% 超ずれる。
* レンズメーカー: thick_lens = paraxial_trace(1e-12)、薄肉の式は R = 300 mm で 0.2% 以内・R = 24 mm で 5% 超。
  屈折率は材料ライブラリの値そのもの。
* 2 枚組: abcd_matrix の −1/C = paraxial_trace の efl = 1/(1/f1 + 1/f2 − d/(f1 f2))(1e-9)、det M = 1。
  ごく低い実光線の焦点が paraxial_trace の F′ に一致(独立経路)。
* 瞳: chief_ray は絞りの中心を通る。小さな画角の主光線の延長が光軸と交わる所 = 入射瞳(独立経路)。縁で切らない
  系では 10° まで cos⁴ に 1% で合い、縁で切る系では 21° で cos⁴ の半分未満。
* ページ: 4 タブ・op の登録名・3 MB 以内。
* 半透明: レンズは alpha 0.25〜0.4(中を通る光線が透ける)、台・支柱・スクリーン・センサー・絞りは不透明のまま。
  HTML の JSON に alpha が載り、半透明の描画(drawTranslucent)が入る。
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _mod():
    for p in (os.path.join(_ROOT, "tools"), _ROOT):
        if p not in sys.path:
            sys.path.insert(0, p)
    import build_lens_system_anim3d as L
    return L


@pytest.fixture(scope="module")
def res():
    L = _mod()
    return L, L.run_all()


# --------------------------------------------------------------------------- 薄レンズの結像
def test_thin_lens_matches_paraxial_trace_from_principal_planes(res):
    L, r = res
    A = r["imaging"]
    rel = np.abs(A["b_para"] - A["b_thin"]) / np.abs(A["b_thin"])
    assert rel.max() < 1e-9
    resid = 1.0 / A["a"] + 1.0 / A["b_thin"] - 1.0 / A["f"]              # 理論の線そのもの
    assert np.abs(resid).max() < 1e-12
    k2 = int(np.argmin(np.abs(A["a"] - 2 * A["f"])))
    assert abs(A["a"][k2] - 2 * A["f"]) < 1e-9 and abs(A["m_thin"][k2] + 1.0) < 1e-12
    assert np.all(A["b_thin"][A["a"] > A["f"]] > 0) and np.all(A["b_thin"][A["a"] < A["f"]] < 0)


def test_stopped_down_real_rays_converge_to_the_paraxial_image():
    """独立経路: 半径の 5% の輪だけの実光線は、近軸(thin_lens)の像の位置に 0.1% 以内で集まる。"""
    L = _mod()
    import optics
    import raytrace as rt
    Ls = L.LENS_A
    n = L.n_of(Ls["glass"])
    for a_over_f in (3.0, 2.0, 1.5):
        sys0 = rt.lens_system(L.singlet(Ls["R1"], Ls["R2"], Ls["t"], Ls["ap"], n), stop=0, object_mm=200.0)
        p0 = rt.paraxial_trace(sys0)
        f, xH, xH2 = p0["efl"], p0["pp_front"], Ls["t"] + p0["pp_rear"]
        a = a_over_f * f
        system = rt.lens_system(L.singlet(Ls["R1"], Ls["R2"], Ls["t"], Ls["ap"], n), stop=0, object_mm=a - xH)
        tip = np.array([0.0, 0.0, -(a - xH)])
        q = [np.array([0.05 * Ls["ap"] * math.cos(t), 0.05 * Ls["ap"] * math.sin(t), 0.0]) for t in np.linspace(0, 6.2, 8)]
        D = np.array([x - tip for x in q])
        D /= np.linalg.norm(D, axis=1, keepdims=True)
        tr = rt.trace_rays(system, np.tile(tip, (len(D), 1)), D, image_mm=50.0)
        ns = len(system["surfaces"])
        p = L.nearest_point(tr["points"][:, ns], tr["dirs"][:, ns])
        b = optics.thin_lens(focal_mm=f, object_mm=a)["image_mm"]
        assert abs((p[2] - xH2) - b) / b < 1e-3


def test_edge_rays_depart_from_the_formula_near_f(res):
    L, r = res
    A = r["imaging"]
    rel = np.abs(A["b_ray"] - A["b_thin"]) / np.abs(A["b_thin"])
    far = A["a"] >= 2 * A["f"] - 1e-9
    assert rel[far].max() < 0.02                                          # 2f より遠い: 2% 以内(実測 1.5%)
    near = (A["a"] > A["f"]) & (A["a"] < 1.3 * A["f"])
    assert rel[near].max() > 0.10                                         # f の近く: 10% を超える(限界の段)
    assert np.all(np.sign(A["b_ray"][far]) == 1) and np.all(A["b_ray"][far] < A["b_thin"][far])   # 縁の光は手前で集まる


# --------------------------------------------------------------------------- レンズメーカーの式
def test_lensmaker_thick_lens_equals_paraxial_trace_and_thin_formula_limits(res):
    L, r = res
    B = r["lensmaker"]
    assert np.max(np.abs(B["f_thick"] - B["f_para"]) / B["f_para"]) < 1e-12
    dev = np.abs(B["f_thick"] - B["f_thin"]) / B["f_thin"]
    assert dev[0] < 0.002 and abs(B["R"][0] - 300.0) < 1e-9               # R = 300 mm: 薄肉の式で足りる
    k24 = L.NF_B1 - 1
    assert abs(B["R"][k24] - 24.0) < 1e-9 and dev[k24] > 0.05             # R = 24 mm: 5% を超えて外れる
    thin = 1.0 / ((B["n"] - 1.0) * (2.0 / B["R"]))                          # 理論の線(独立に計算)
    assert np.max(np.abs(thin - B["f_thin"]) / thin) < 1e-14


def test_lensmaker_index_comes_from_the_material_library(res):
    L, r = res
    import materials
    B = r["lensmaker"]
    seen = {}
    for m, n in zip(B["mat"], B["n"]):
        seen.setdefault(m, n)
        assert n == materials.material_optical_constants(m, L.WL_NM)["n"]
    phase2 = B["mat"][L.NF_B1:]                                            # 後半: R = 50 mm のまま材料を替える
    assert list(dict.fromkeys(phase2)) == list(L.MATS_B) and np.all(B["R"][L.NF_B1:] == L.R_FIX)
    k2 = [L.NF_B1 + phase2.index(m) for m in L.MATS_B]
    f_at_R50 = B["f_thick"][k2]
    assert np.all(np.diff(f_at_R50) < 0)                                   # n が上がると f は縮む
    assert np.all(np.diff([seen[m] for m in L.MATS_B]) > 0)


# --------------------------------------------------------------------------- 2 枚組と ABCD
def test_abcd_from_principal_planes_equals_the_real_prescription(res):
    L, r = res
    C = r["doublet"]
    ok = np.isfinite(C["f_para"])
    assert np.max(np.abs(C["f_abcd"][ok] - C["f_para"][ok]) / np.abs(C["f_para"][ok])) < 1e-9
    assert np.max(np.abs(C["f_formula"] - C["f_abcd"]) / np.abs(C["f_abcd"])) < 1e-9
    assert np.max(np.abs(C["det"] - 1.0)) < 1e-12
    fin = np.isfinite(C["x_F"])
    assert np.max(np.abs(C["x_F"][fin] - C["x_F_para"][fin])) < 1e-6        # F' の位置も一致(mm)
    # 屈折力は d について一直線、d = f1 + f2 で 0(望遠鏡)
    P = 1.0 / C["f_abcd"]
    assert np.all(np.diff(P) < 0)
    k = int(np.argmax(C["d_pp"] > C["f1"] + C["f2"]))
    assert P[k - 1] > 0 > P[k]


def test_low_real_ray_focus_matches_paraxial_trace():
    """独立経路: 高さ 0.01 mm の実光線が光軸を横切る所 = paraxial_trace の F′(処方は 2 枚組、間隔 3 通り)。"""
    L = _mod()
    import raytrace as rt
    n = L.n_of(L.L1_C["glass"])
    for g in (10.0, 60.0, 200.0):
        surf = L.singlet(L.L1_C["R1"], L.L1_C["R2"], L.L1_C["t"], L.L1_C["ap"], n, nxt=g) + \
            L.singlet(L.L2_C["R1"], L.L2_C["R2"], L.L2_C["t"], L.L2_C["ap"], n, nxt=100.0)
        system = rt.lens_system(surf, stop=0)
        para = rt.paraxial_trace(system)
        z_last = L.L1_C["t"] + g + L.L2_C["t"]
        O, D = L.collimated([0.01])
        tr = rt.trace_rays(system, O, D)
        zc = L.axis_crossing(tr["points"][0, 4], tr["dirs"][0, 4])
        assert abs(zc - (z_last + para["bfl"])) < 1e-3


# --------------------------------------------------------------------------- 絞りと瞳
def test_chief_ray_passes_the_stop_centre_and_defines_the_entrance_pupil(res):
    L, r = res
    import raytrace as rt
    D = r["pupils"]
    assert np.nanmax(np.abs(D["stop_hit"])) < 1e-6
    # 独立経路: 小さな画角の主光線の物体側の延長が光軸と交わる所 = 入射瞳の位置
    cr = rt.chief_ray(D["system"], field=0.5)
    p, d = cr["points"][0], cr["dirs"][0]
    z_cross = p[2] - p[1] / d[1] * d[2]
    assert abs(z_cross - D["para"]["ep_position"]) < 0.05
    # 対称な系: 射出瞳は入射瞳の鏡像
    assert abs(D["para"]["xp_position"] + D["para"]["ep_position"]) < 1e-9


def test_cos4_holds_without_clipping_and_fails_with_it(res):
    L, r = res
    D = r["pupils"]
    assert np.max(np.abs(D["cos4"] - np.cos(np.radians(D["theta"])) ** 4)) < 1e-12   # op = 理論の線
    c4 = np.cos(np.radians(D["theta_noclip"])) ** 4
    small = D["theta_noclip"] <= 10.0 + 1e-9
    assert np.max(np.abs(D["ri_noclip"][small] - c4[small]) / c4[small]) < 0.01
    assert D["ri_real"][-1] < 0.5 * D["cos4"][-1]                           # 縁で切ると cos⁴ の半分未満
    assert D["vig"][0] == 1.0 and D["vig"][-1] < 0.6
    assert abs(D["ri_real"][1] - D["cos4"][1]) < 0.01                       # 光軸の近くは合う


# --------------------------------------------------------------------------- 3-D と ページ
def test_rods_cover_segments_exactly():
    """光線の棒: 覆った長さが線分と一致し、棒が線分の外へはみ出さない。"""
    L = _mod()
    sc = L.Scene(3, -100, 400)
    sc.color("x", (255, 0, 0))
    P, Q = np.array([0.0, 0.0, 0.0]), np.array([337.0, 0.0, 21.0])
    for k in range(3):
        sc.seg(k, "x", P, Q * (k + 1) / 3)
    pool, plans = sc._alloc()
    for k, plan in enumerate(plans):
        q = Q * (k + 1) / 3
        D = np.linalg.norm(q)
        u = q / D
        ivs = sorted((float(np.dot(p, u)), float(np.dot(p, u)) + L_) for (_, L_, _), p, _ in plan)
        assert ivs[0][0] > -1e-9 and ivs[-1][1] < D + 1e-9                 # はみ出さない
        cur = 0.0
        for a, b in ivs:
            assert a <= cur + 1e-9                                         # すき間が無い
            cur = max(cur, b)
        assert abs(cur - D) < 1e-9


def test_page_has_four_tabs_with_op_names_and_fits_3mb(res, tmp_path):
    L, r = res
    import pocviewer as pv
    spec, S, infos = L.build_spec(r)
    assert [t["id"] for t in spec["tabs"]] == ["imaging", "lensmaker", "doublet", "pupils"]
    assert [t["badge"] for t in spec["tabs"]] == ["passed", "passed", "passed", "limit"]
    for t in spec["tabs"]:
        assert np.asarray(t["panes"][0]["frames"]).shape[0] == len(t["t"]) == L.NF
    out = pv.write_viewer(spec, str(tmp_path / "lens.html"), list(L.LANGS))
    html = open(out, encoding="utf-8").read()
    assert len(html.encode("utf-8")) < 3_000_000
    for op in ("paraxial_trace", "thin_lens", "trace_rays", "thick_lens", "material_optical_constants", "abcd_matrix",
               "abcd_trace", "chief_ray", "ray_bundle", "relative_illumination"):
        assert op in html
    assert "http://" not in html and "https://" not in html


def test_lenses_are_translucent_and_opaque_parts_stay_opaque(res, tmp_path):
    L, r = res
    import re

    import pocviewer as pv
    spec, S, infos = L.build_spec(r)
    assert 0.25 <= L.GLASS_ALPHA <= 0.4
    for t in spec["tabs"]:
        lenses = [b for b in t["bodies"] if b["name"].startswith("lens") and not b["name"].endswith("_post")]
        assert lenses, t["id"]
        for b in lenses:
            assert b.get("alpha") == L.GLASS_ALPHA, (t["id"], b["name"])
        for b in t["bodies"]:
            opaque = (b["name"] in ("bench", "screen", "sensor", "stop") or b["name"].endswith("_post")
                      or b["name"].startswith("ray_"))
            if opaque:
                assert "alpha" not in b, (t["id"], b["name"])
    out = pv.write_viewer(spec, str(tmp_path / "lens.html"), list(L.LANGS))
    html = open(out, encoding="utf-8").read()
    assert re.search(r'"alpha":\s*%s' % re.escape(repr(L.GLASS_ALPHA)), html)
    assert "drawTranslucent" in html
