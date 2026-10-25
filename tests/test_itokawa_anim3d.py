# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""tools/build_itokawa_anim3d.py(小惑星イトカワの重力、動く 3-D の 5 タブ)と、その出力 docs/anim3d/itokawa_gravity.html を守る。

全頂点の重力の計算は数分かかるので、ここでは回さない。代わりに
* 形状データ(data/itokawa_shape/gaskell_q64.npz)の出どころの SHA-256・件数・閉じていること・公表値との差、
* commit した HTML に埋めた色(頂点ごとの op の値)を、抜き出した頂点で op を回し直した値と比べる
  (量子化の刻みの半分以内。手で描いた色ではないこと)、
* 頭と胴の 2 密度の模型が Lowry et al. 2014 の値(胴 1,750 ± 110 kg/m³、重心のずれ 21 ± 12 m)を再現すること、
* バッジの表(checks)・学習用の型(lesson)・時間つまみ(axis)が全タブにあり、限界の回が最初でないこと、
* 画面に出す op の名前が実在し台帳に登録されていること、容量 3 MB 以内・外部 URL / ローカルパス / ** が無いこと
を確かめる。
"""
from __future__ import annotations

import importlib
import importlib.util
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "docs" / "anim3d" / "itokawa_gravity.html"


def _tool():
    name = "build_itokawa_anim3d"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mesh():
    m = _tool()
    V, F, n_dup = m.load_mesh()
    return m, V, F, n_dup


@pytest.fixture(scope="module")
def page():
    html = HTML.read_text(encoding="utf-8")
    data = json.loads(re.search(r"const D = (\{.*?\});\nconst \$ = ", html, re.S).group(1))
    return html, data


def test_shape_data_is_the_recorded_public_model(mesh):
    m, V, F, n_dup = mesh
    import hashlib
    z = np.load(m.DATA, allow_pickle=False)
    assert str(z["source_sha256"]) == m.SHA256_TAB
    assert z["vertices_cm"].shape == (25350, 3) and z["faces"].shape == (49152, 3)
    assert len(F) == 49152 and len(V) + n_dup == 25350 and n_dup > 0      # 面から使われない重複頂点(原本の注意書き)
    st = m.L.mesh_edge_stats(V, F)
    assert st["boundary_edges"] == 0 and st["non_manifold_edges"] == 0
    vol = m.L.mesh_volume((V, F))
    assert abs(vol / m.PUB_VOLUME - 1.0) < m.PUB_VOLUME_REL                 # Demura 2006 の ± 5 %
    assert abs(vol * m.RHO / m.PUB_MASS_F - 1.0) < m.RHO_SIGMA / m.RHO       # Fujiwara 2006 の密度の幅
    readme = (m.DATA.parent / "README.md").read_text(encoding="utf-8")
    assert m.SHA256_TAB in readme and "CC0 1.0" in readme
    assert hashlib.sha256((ROOT / "tools" / "import_itokawa_shape.py").read_bytes()).hexdigest()   # 取り込みの道具がある


def test_spin_period_from_the_pds_rotation_rate(mesh):
    m = mesh[0]
    assert m.PERIOD_H == pytest.approx(12.1324, abs=1e-4)
    assert m.OMEGA == pytest.approx(2 * math.pi / (m.PERIOD_H * 3600.0), rel=1e-12)


def test_two_density_model_reproduces_lowry_2014(mesh):
    m, V, F, _ = mesh
    pg = m.pg
    probe = np.array([[0.0, 0.0, 1.0e4]])
    w = pg.polyhedron_gravity((V, F), probe, density=1.0)
    head = pg.polyhedron_clip_halfspace((V, F), [m.LOWRY_X_CUT, 0.0, 0.0], [1.0, 0.0, 0.0])
    h = pg.polyhedron_gravity(head, probe, density=1.0)
    vol, vh = w["volume"], h["volume"]
    rho_b = (m.LOWRY_RHO_MEAN * vol - m.LOWRY_RHO_HEAD * vh) / (vol - vh)
    com = (rho_b * vol * w["center_of_mass"] + (m.LOWRY_RHO_HEAD - rho_b) * vh * h["center_of_mass"]) / (m.LOWRY_RHO_MEAN * vol)
    assert abs(rho_b - m.LOWRY_RHO_BODY) <= m.LOWRY_RHO_BODY_SIGMA
    assert abs((com - w["center_of_mass"])[0] - m.LOWRY_COM_X) <= m.LOWRY_COM_X_SIGMA
    assert 0.1 < vh / vol < 0.3


def test_page_structure_badges_checks_lessons(page):
    html, data = page
    tabs = data["tabs"]
    assert [t["id"] for t in tabs] == ["size", "shape", "gravity", "muses", "limit", "math"]
    assert tabs[0]["badge"] != "limit"
    badges = {t["id"]: t["badge"] for t in tabs}
    assert badges["limit"] == "limit" and all(b == "passed" for k, b in badges.items() if k != "limit")
    assert len(tabs) == 6
    for t in tabs:
        assert t["checks"] and t["lesson"] and t["axis"], t["id"]
        if t["badge"] == "passed":
            assert all(r["ok"] for r in t["checks"]), t["id"]
    assert any(not r["ok"] for r in tabs[4]["checks"])          # 限界の回は落ちる行を正直に出す
    credit = json.dumps(data.get("credit"), ensure_ascii=False)
    assert "CC0 1.0" in credit and "Gaskell" in credit and "NASA PDS" in credit


def test_page_is_small_and_has_no_urls_paths_or_bold(page):
    html, _ = page
    assert len(html.encode("utf-8")) < 3.0e6
    assert "http://" not in html and "https://" not in html
    assert "C:\\" not in html and "C:/" not in html
    assert "**" not in html


def test_embedded_colours_are_the_op_values(mesh, page):
    """色は op の値: 抜き出した頂点で polyhedron_gravity を回し直し、埋めた値と量子化の刻みの半分以内で比べる。"""
    m, V, F, _ = mesh
    html, data = page
    pv = m.pv
    A = data["arrays"]
    tabs = {t["id"]: t for t in data["tabs"]}
    rng = np.random.default_rng(3)
    idx = rng.choice(len(V), size=48, replace=False)
    VN = m.L.vertex_normals((V, F))
    g = m.pg.polyhedron_gravity((V, F), V[idx], density=m.RHO, omega=m.OMEGA, normals=VN[idx])
    ge_um = np.linalg.norm(g["effective_acceleration"], axis=1) * 1e6
    rec = A[tabs["gravity"]["bodies"][0]["val"]]
    back = pv._decode_array(rec)[idx]
    cb = tabs["gravity"]["cbar"]
    step = pv._quant_step(rec)
    assert np.all(np.abs(back - np.clip(ge_um, cb["lo"], cb["hi"])) <= step / 2 + 1e-9)
    assert float(np.ptp(pv._decode_array(rec))) > 10.0                    # 定数の色ではない
    # 限界の回: 2 密度 ÷ 一様 − 1 の色
    head = m.pg.polyhedron_clip_halfspace((V, F), [m.LOWRY_X_CUT, 0.0, 0.0], [1.0, 0.0, 0.0])
    h = m.pg.polyhedron_gravity(head, V[idx], density=1.0)
    vol, vh = g["volume"], h["volume"]
    rb = (m.LOWRY_RHO_MEAN * vol - m.LOWRY_RHO_HEAD * vh) / (vol - vh)
    cw = g["center_of_mass"]
    c2 = (rb * vol * cw + (m.LOWRY_RHO_HEAD - rb) * vh * h["center_of_mass"]) / (m.LOWRY_RHO_MEAN * vol)
    accW = g["acceleration"] / m.RHO

    def geff(acc, c):
        d = V[idx] - c
        d[:, 2] = 0.0
        return np.linalg.norm(acc + m.OMEGA ** 2 * d, axis=1)

    dg = (geff(rb * accW + (m.LOWRY_RHO_HEAD - rb) * h["acceleration"], c2) / geff(m.LOWRY_RHO_MEAN * accW, cw) - 1.0) * 100.0
    rec = A[tabs["limit"]["bodies"][0]["val"]]
    cb = tabs["limit"]["cbar"]
    assert np.all(np.abs(pv._decode_array(rec)[idx] - np.clip(dg, cb["lo"], cb["hi"])) <= pv._quant_step(rec) / 2 + 1e-9)


def test_ops_named_on_screen_exist_and_are_registered():
    m = _tool()
    import fullseye as fs
    import opsdrive
    assert len(m.OPS_USED) == 12
    for full in m.OPS_USED:
        mod, name = full.split(".")
        assert callable(getattr(importlib.import_module(mod), name)), full
        if mod == "polygrav":
            assert name in opsdrive.list_ops(), full
        else:
            assert callable(getattr(fs.ledger, name)), full


def test_venue_asset_is_recorded_and_drawn_at_its_bbox():
    """会場(PLATEAU)の資産: 出どころの SHA-256・README のライセンス表示、描いた幅 = 資産の外接箱。"""
    m = _tool()
    V, F, ext = m.load_venue()
    assert V.shape[1] == 3 and len(F) > 1000
    assert np.allclose(np.ptp(V, axis=0), ext, atol=1e-9)
    readme = (m.VENUE_NPZ.parent / "README.md").read_text(encoding="utf-8")
    assert "PLATEAU" in readme and "PDL1.0" in readme
    R = {"V": None}
    # 物差しの配置だけ組み立てて、会場の幅を外接箱と比べる(全頂点の重力は要らない)
    Vi, Fi, _ = m.load_mesh()
    up = np.array([0.0, 0.0, 1.0])
    t1, t2 = m._tangent_frame(up)
    R = {"V": Vi, "size": {"k": 0, "up": up, "t1": t1, "t2": t2,
                           "venue": {"V": V, "F": F, "ext": ext}}}
    assert m.venue_extent_error(R) < 1e-9


def test_principal_extents_of_a_rotated_box_are_its_sides():
    """慣性主軸に沿った長さ(符号付き四面体の 2 次モーメント)は、回した直方体で辺の長さそのもの。"""
    m = _tool()
    V = np.array([[x, y, z] for x in (0, 4.0) for y in (0, 2.0) for z in (0, 1.0)], float)
    quads = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    F = np.array([f for q in quads for f in ([q[0], q[1], q[2]], [q[0], q[2], q[3]])])
    a = 0.7
    Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1.0]])
    Vr = V @ Rz.T + [5.0, -3.0, 2.0]
    ext, U = m.principal_extents(Vr, F, Vr.mean(axis=0))
    assert np.allclose(ext, [4.0, 2.0, 1.0], atol=1e-9)
    assert abs(abs(U[:, 0] @ Rz[:, 0]) - 1.0) < 1e-9
