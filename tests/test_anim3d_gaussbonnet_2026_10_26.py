# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""離散 Gauss–Bonnet の動く 3-D(tools/build_gaussbonnet_anim3d.py)の門。

真値 = 定理: 閉じた三角形メッシュで Σ_v K_v = 2πχ(K_v = 2π − Σθ は角度 = 幾何、χ = V − E + F は組合せ。独立な 2 経路)。
ここでは生成器の gates() の値(= ページのバッジの表の値)を、同じ基準で確かめる:

* 球 → 立方体の 5 つの形: Σ K / 2π = χ = 2(|差| < 1e-9)、球は 4π、立方体は K = π/2 の頂点がちょうど 8 つ。
* トーラス: Σ K = 0、χ = 0・種数 1、外側(K > 0)と内側(K < 0)の和が打ち消す。
* 穴 0・1・2・3: χ = 2 − 2g = 2, 0, −2, −4 と Σ K / 2π が一致、4 つとも閉じている。
* 実物(小惑星イトカワ): 閉じていて Σ K / 2π = χ = 2(負の K の頂点があっても)。
* 限界: 半球の皿(境界あり、χ = 1)では 2π − Σθ だけの和は 2πχ にならず、境界の項 π − Σθ を入れた op の和は一致する。
  走査(開いた面片の集まり)でも面片ごとに一致するが、χ は面片の数。ok:false の行は限界のタブに 1 行だけ。
* 2π − Σθ の和は別経路(2πV − πF、角の和の恒等式)とも一致する(皿・走査)。
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
    import build_gaussbonnet_anim3d as B
    return B


@pytest.fixture(scope="module")
def built():
    B = _mod()
    res = B.run_all()
    return B, res, B.gates(res)


def test_sphere_to_cube_keeps_the_total_at_4pi_while_k_gathers_at_corners(built):
    B, res, g = built
    recs = res["sharpen"]["recs"]
    assert len(recs) == 5
    diffs = np.array([abs(r["total"] - r["two_pi_chi"]) for r in recs])
    assert diffs.shape == (5,) and np.all(diffs < 1e-9)
    assert g["sharpen_chis"] == [2, 2, 2, 2, 2] and g["sharpen_all_closed"]
    assert g["sphere_total_vs_4pi"] < 1e-9
    assert g["cube_corners"] == 8 and g["cube_rest_max"] < 1e-9
    assert abs(recs[-1]["K"].max() - math.pi / 2) < 1e-12
    kmax = np.array(g["sharpen_kmax"])
    assert kmax.shape == (5,) and np.all(np.diff(kmax) > 0)          # K は角に集まっていく
    assert len(set(g["sharpen_vertices"])) == 1                      # 同じ格子(頂点数が同じ)


def test_torus_total_is_zero_because_outside_and_inside_cancel(built):
    B, res, g = built
    assert g["torus_total_abs"] < 1e-9
    assert g["torus_chi"] == 0 and g["torus_genus"] == 1
    assert g["torus_outer"] > 1.0 and g["torus_inner"] < -1.0 and g["torus_cancel"] < 1e-9
    ring = res["torus"]["recs"]["ring_sum"]
    assert ring.shape == (B.TORUS_NV,)
    assert abs(ring.sum()) < 1e-9
    assert ring[0] > 0 and ring[B.TORUS_NV // 2] < 0                 # 外の赤道の輪は正、内の赤道の輪は負
    cum = res["torus"]["cum"]
    assert cum.shape == (B.NF,) and abs(cum[-1]) < 1e-9


def test_each_hole_lowers_chi_by_two_and_the_total_by_4pi(built):
    B, res, g = built
    assert g["genus_chis"] == [2, 0, -2, -4]
    assert g["genus_genera"] == [0, 1, 2, 3]
    assert g["genus_max_diff"] < 1e-9 and g["genus_all_closed"]
    totals = np.array([r["total"] for r in res["genus"]["recs"]])
    assert totals.shape == (4,)
    assert np.all(np.abs(np.diff(totals) + 4 * math.pi) < 1e-9)


def test_the_measured_asteroid_is_a_closed_surface_with_total_4pi(built):
    B, res, g = built
    assert g["asteroid_closed"] and g["asteroid_boundary_edges"] == 0 and g["asteroid_nonmanifold_edges"] == 0
    assert g["asteroid_chi"] == 2 and g["asteroid_diff"] < 1e-9
    assert g["asteroid_V"] == 24578 and g["asteroid_F"] == 49152              # Gaskell Q = 64(使われない重複頂点は数えない)
    assert 0.2 < g["asteroid_neg_share"] < 0.9                                  # 鞍の頂点が確かにある
    assert g["asteroid_kmin"] < 0 < g["asteroid_kmax"]


def test_a_surface_with_boundary_needs_the_geodesic_term(built):
    B, res, g = built
    bd = res["boundary"]
    bowl, scan = bd["recs"]
    assert g["bowl_chi"] == 1 and g["bowl_boundary_vertices"] >= 12
    assert g["bowl_naive_diff"] > 1.0                                           # 限界: 2π − Σθ だけでは外れる
    assert g["bowl_op_diff"] < 1e-9                                             # 境界の項を入れた op は一致
    assert abs(g["bowl_interior_total"] + g["bowl_turning_total"] - 2 * math.pi) < 1e-9
    # 2π − Σθ の和の別経路: 角の和の恒等式 Σ_v (2π − Σθ_v) = 2πV − πF(皿と走査)
    assert abs(g["bowl_naive_total"] - (2 * math.pi * bowl["V"] - math.pi * bowl["F"])) < 1e-9
    assert abs(bd["scan_naive_total"] - (2 * math.pi * scan["V"] - math.pi * scan["F"])) < 1e-9
    assert g["scan_components"] > 1000 and g["scan_boundary_edges"] > 10000 and g["scan_nonmanifold_edges"] == 0
    assert g["scan_op_diff"] < 1e-9 and g["scan_naive_diff"] > 1.0
    assert g["scan_source"]["source_components"] >= g["scan_components"] > 1


def test_badge_table_has_exactly_one_failed_row_and_it_is_in_the_limit_tab(built):
    B, res, g = built
    spec = B.build_spec(res, g)
    tabs = spec["tabs"]
    assert [t["id"] for t in tabs] == ["sharpen", "torus", "genus", "asteroid", "boundary"]
    assert [t["badge"] for t in tabs] == ["passed", "passed", "passed", "passed", "limit"]
    failed = [(t["id"], c["what"]["en"]) for t in tabs for c in t["checks"] if not c["ok"]]
    assert len(failed) == 1 and failed[0][0] == "boundary" and "limit" in failed[0][1]
    n_rows = sum(len(t["checks"]) for t in tabs)
    assert n_rows >= 16
    for t in tabs:
        assert set(t["lesson"]) == {"question", "choices", "answer", "explain", "formula", "limit"}
        assert t["axis"]["values"].shape == (B.NF,)
    html = B.pv._build_html(spec, list(B.LANGS))
    assert len(html.encode("utf-8")) < 3_300_000                                 # ページの上限(8 言語版も同じ門を i18n の門で見る)


def test_check_mode_writes_nothing(tmp_path, monkeypatch, capsys):
    B = _mod()
    out = tmp_path / "x.html"
    assert B.main(["--check", "--out", str(out)]) == 0
    assert not out.exists()
    assert "ok:" in capsys.readouterr().out
