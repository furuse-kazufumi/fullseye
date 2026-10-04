# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""drivejapan の門: 等距円筒の既知値と第 2 実装(driveplateau)との一致、直線路の和集合の面積 = L w + π(w/2)²、境界ループの面積 = 画素数 × step²、
格子の穴の数 = (n−1)²、辺の数と総延長、最短路の長さ・停止線の位置(閉形式)、一方通行の遵守、左右の車線の鏡像、drivetown.town_run での通し走行、
日本の道具立ての寸法(一時停止 80 cm・「止まれ」9.2 m)、世界の面ラベル、箱の外に物を置かない、fail-closed の ValueError。
examples/poc_driving_japan_town.py の門を単体テストにしたもの。実データ(OSM / PLATEAU)は環境変数があるときだけ。"""
import math
import os
from pathlib import Path

import numpy as np
import pytest

import drivejapan as DJ
import drivetown as TW
import driveworld as DW

PITCH = 80.0


@pytest.fixture(scope="module")
def grid():
    osm = DJ.osm_parse(DJ.osm_synthetic("grid", n=3, pitch=PITCH))
    g = DJ.osm_road_graph(osm)
    return osm, g


def _node_at(g, i, j, n=3):
    """格子の (i, j) に最も近い節点 id。"""
    x, y = (i - (n - 1) / 2) * PITCH, (j - (n - 1) / 2) * PITCH
    return min(g["nodes"], key=lambda k: (g["nodes"][k]["xy"][0] - x) ** 2 + (g["nodes"][k]["xy"][1] - y) ** 2)


# ── 座標 ──────────────────────────────────────────────────────────────────────
def test_latlon_known_value_and_second_implementation():
    import driveplateau as PL
    x, y = DJ.latlon_to_local(35.0 + 0.001, 139.0, (35.0, 139.0))
    assert abs(float(y) - DJ.R_EARTH_M * math.pi / 180 * 0.001) < 1e-9 and abs(float(x)) < 1e-12
    x2, y2 = PL.latlon_to_local(35.6700, 139.7650, (35.6715, 139.7660))
    x1, y1 = DJ.latlon_to_local(35.6700, 139.7650, (35.6715, 139.7660))
    assert abs(float(x1) - float(x2)) < 1e-9 and abs(float(y1) - float(y2)) < 1e-9
    with pytest.raises(ValueError):
        DJ.latlon_to_local(91.0, 0.0, (0.0, 0.0))


# ── 読み込みと道路網 ───────────────────────────────────────────────────────────
def test_parse_and_graph_counts(grid):
    osm, g = grid
    assert osm["n_nodes"] == 11 and osm["n_ways"] == 6 and osm["n_dangling"] == 0
    assert g["n_edges"] == 2 * 3 * 2 + 2                       # 12 本 + 途中に挿した 2 節点で 2 本増える
    assert abs(g["total_length"] - 2 * 3 * 2 * PITCH) < 1e-4          # 緯度経度 11 桁 → 1e-6 m 級
    feats = {f: sum(1 for n in g["nodes"].values() if f in n["features"]) for f in DJ.NODE_FEATURES}
    assert feats == {"traffic_signals": 1, "crossing": 1, "stop": 1, "give_way": 0, "level_crossing": 1}
    st = DJ.japan_stats(g)
    assert st["junctions"] == 5 and len(st["table"]) == 2 and st["width_from"] == {"lanes": 7, "default": 7}


def test_parse_rejects_garbage():
    with pytest.raises(ValueError):
        DJ.osm_parse("<osm></osm>")
    with pytest.raises(ValueError):
        DJ.osm_parse("<html></html>")
    with pytest.raises(ValueError):
        DJ.osm_parse("not xml at all <")
    with pytest.raises(ValueError):
        DJ.osm_synthetic("hexagon")
    osm = DJ.osm_parse(DJ.osm_synthetic("line", n=2))
    with pytest.raises(ValueError):
        DJ.osm_road_graph(osm, way_types=("primary",))         # residential しか無い → 辺ゼロ
    with pytest.raises(ValueError):
        DJ.osm_road_graph(osm, way_types=("autobahn",))


def test_width_sources():
    assert DJ._edge_width({"width": "12 m"}, "primary") == (12.0, 4, "width")
    assert DJ._edge_width({"lanes": "3"}, "primary") == (3 * 3.25, 3, "lanes")
    assert DJ._edge_width({}, "residential") == (5.5, 2, "default")
    assert DJ._edge_width({"width": "1"}, "service")[0] == 2.5     # 下限


# ── ラスタの和集合と境界 ───────────────────────────────────────────────────────
def test_straight_road_area_closed_form():
    osm = DJ.osm_parse(DJ.osm_synthetic("line", n=2, pitch=100.0))
    g = DJ.osm_road_graph(osm)
    e = g["edges"][0]
    rm = DJ.osm_road_mask(g, step=0.25)
    exact = e["length"] * e["width"] + math.pi * (e["width"] / 2) ** 2
    assert abs(rm["area_m2"] - exact) / exact < 0.01
    with pytest.raises(ValueError):
        DJ.osm_road_mask(g, step=0.0)
    with pytest.raises(ValueError):
        DJ.osm_road_mask(g, step=0.001)                            # 4e7 画素超


def test_loops_area_equals_pixels_and_hole_count(grid):
    _, g = grid
    rm = DJ.osm_road_mask(g, step=0.5)
    lp = DJ.osm_road_loops(rm)
    assert lp["area_check"]["abs_err"] < 1e-6
    assert len(lp["outer"]) == 1 and len(lp["holes"]) == 4
    assert len(lp["holes"]) == 4
    for P in lp["holes"]:
        assert abs(abs(DJ._signed_area(P)) - (PITCH - 5.5 / 2 - 6.5 / 2) ** 2) < 60.0    # 街区 ≈ (80 − 半幅の和)²、画素化と DP の誤差
    assert len(lp["holes_raw"]) == 4


def test_runs_mesh_area_equals_pixels():
    """斜めに接する穴(耳切りが拒む形)を行の束で埋めると面積 = 画素数 × step²。"""
    mask = np.ones((12, 12), bool)
    mask[3:6, 3:6] = False
    mask[6:9, 6:9] = False                                          # 角で接する 2 つの穴 → 1 本の自己接触ループ
    rm = {"mask": mask, "xmin": 0.0, "ymin": 0.0, "step": 1.0, "shape": mask.shape, "area_m2": float(mask.sum())}
    lp = DJ.osm_road_loops(rm, tolerance_px=0.1)
    assert lp["area_check"]["abs_err"] < 1e-9
    tot = 0.0
    for Praw in lp["holes_raw"]:
        V, F = DJ._runs_mesh(Praw, rm, 0.15)
        a = sum(abs((V[f[1], 0] - V[f[0], 0]) * (V[f[2], 1] - V[f[0], 1]) - (V[f[2], 0] - V[f[0], 0]) * (V[f[1], 1] - V[f[0], 1])) / 2
                for f in F)
        tot += a
    assert abs(tot - 18.0) < 1e-9 and np.allclose(V[:, 2], 0.15)


# ── 経路 ──────────────────────────────────────────────────────────────────────
def test_route_length_and_stop_lines(grid):
    _, g = grid
    src, dst = _node_at(g, 0, 1), _node_at(g, 2, 1)
    r = DJ.osm_route(g, src, dst)
    assert abs(r["length"] - 2 * PITCH) < 1e-4 and abs(r["graph_length"] - 2 * PITCH) < 1e-4
    kinds = [d["kind"] for d in r["stop_lines"]]
    assert kinds == ["intersection", "stop_sign"]
    r_x = 5.5 / 2                                                   # 交差する residential の半幅
    assert abs(r["stop_lines"][0]["s"] - (PITCH - r_x - 1.0)) < 1e-4
    assert abs(r["stop_lines"][1]["s"] - (2 * PITCH - r_x - 1.0)) < 1e-4
    # 左側通行: 車線中心は進行方向の左に 幅/4(primary lanes=2 → 6.5/4)
    assert abs(r["polyline"][0, 1] - 6.5 / 4) < 1e-9
    assert np.all(np.diff(r["cum"]) >= 0) and abs(r["cum"][-1] - r["length"]) < 1e-12
    with pytest.raises(ValueError):
        DJ.osm_route(g, src, src)
    with pytest.raises(ValueError):
        DJ.osm_route(g, src, 10 ** 9)


def test_route_mirror_for_right_hand_traffic(grid):
    _, g = grid
    src, dst = _node_at(g, 0, 1), _node_at(g, 2, 1)
    rl = DJ.osm_route(g, src, dst, side="left")
    rr = DJ.osm_route(g, src, dst, side="right")
    assert np.allclose((rl["polyline"] + rr["polyline"]) / 2, np.column_stack([rl["polyline"][:, 0], np.zeros(len(rl["polyline"]))]), atol=1e-9)
    with pytest.raises(ValueError):
        DJ.osm_route(g, src, dst, side="middle")


def test_route_respects_oneway():
    xml = DJ.osm_synthetic("grid", n=3, pitch=PITCH).replace('<tag k="name" v="EW 1"/>', '<tag k="name" v="EW 1"/>\n    <tag k="oneway" v="-1"/>')
    g = DJ.osm_road_graph(DJ.osm_parse(xml))
    src, dst = _node_at(g, 0, 1), _node_at(g, 2, 1)
    r = DJ.osm_route(g, src, dst)
    assert abs(r["graph_length"] - 4 * PITCH) < 1e-4                # 中段は逆向きの一方通行 → 上か下の段を回る
    r2 = DJ.osm_route(g, dst, src)
    assert abs(r2["graph_length"] - 2 * PITCH) < 1e-4               # 逆向きなら中段を通れる


def test_town_run_on_route(grid):
    _, g = grid
    r = DJ.osm_route(g, _node_at(g, 0, 1), _node_at(g, 2, 1))
    run = TW.town_run(r, dt=0.05, v_max=8.0)
    assert len(run["stops"]) == 2
    assert [s[1] for s in run["stops"]] == ["intersection", "stop_sign"]
    for s_stop, kind, _, _ in run["stops"]:
        line = [d for d in r["stop_lines"] if d["kind"] == kind][0]
        assert 0.0 <= line["s"] - s_stop <= 1.0
    ck = TW.town_checks(run, r)
    assert ck["ok"] and ck["count_ok"] and abs(run["total_length"] - r["length"]) < 1e-9
    assert np.allclose(run["z"], 0.0)
    with pytest.raises(ValueError):
        TW.town_run({"kind": "route", "polyline": np.zeros((1, 2)), "cum": np.zeros(1), "stop_lines": []})


# ── 道具立てと世界 ─────────────────────────────────────────────────────────────
def test_jp_props_dimensions():
    V, F, C = DJ.jp_sign_stop_mesh()
    plate = V[np.unique(F[np.all(np.isclose(C, DJ._C_WHITE), axis=1)])]          # 白の板(縁取り)の頂点
    assert abs(np.ptp(plate[:, 1]) - 0.8) < 1e-9 and abs(plate[:, 2].max() - 2.5) < 1e-9      # 一辺 80 cm、上辺が高さ 2.5 m
    assert abs((plate[:, 2].max() - plate[:, 2].min()) - 0.8 * math.sqrt(3) / 2) < 1e-9
    V, F, C = DJ.jp_stop_marking_mesh()
    assert abs(np.ptp(V[:, 0]) - DJ.jp_stop_marking_length()) < 1e-9 and abs(DJ.jp_stop_marking_length() - 9.2) < 1e-12
    assert np.ptp(V[:, 1]) <= 0.8 + 1e-9 and np.allclose(V[:, 2], V[0, 2]) and len(F) > 20
    V, F, C = DJ.jp_crossbuck_mesh()
    assert abs(V[:, 1].max() + V[:, 1].min()) < 1e-9                                           # 左右対称
    fns = (DJ.jp_pole_mesh, DJ.jp_mirror_mesh)
    assert len(fns) == 2
    for fn in fns:
        V, F, C = fn()
        assert len(F) == len(C) and V[:, 2].min() >= -1e-9
    with pytest.raises(ValueError):
        DJ.jp_stop_marking_mesh(char_h=0.0)


def test_world_labels_and_props(grid):
    _, g = grid
    w = DJ.japan_world(g)
    st = w["stats"]
    stop_node = [n for n in g["nodes"].values() if "stop" in n["features"]][0]
    assert st["blocks"] == 4 and st["blocks_skipped"] == 0
    assert st["signals"] == 4 and st["stop_signs"] == stop_node["degree"] == 3 and st["crossings"] == 1 and st["crosswalks"] == 1
    assert st["poles"] > 0 and st["markings"] > 0
    labels = set(np.unique(w["face_label"]).tolist())
    assert {0, 1, 3, 4, 8, 9, 12, 15, 16} <= labels
    xmin, xmax, ymin, ymax = w["bounds"]
    assert xmin <= w["V"][:, 0].min() - 1e-6 + 1e-6 and w["V"][:, 0].max() <= xmax + 1e-6 and w["V"][:, 1].max() <= ymax + 1e-6
    assert len(w["signals"]) == 4 and all(w["objects"][s["object"]]["name"] == "traffic_light" for s in w["signals"])
    with pytest.raises(ValueError):
        DJ.japan_world(g, side="centre")


def test_camera_sees_stop_sign_and_marking(grid):
    _, g = grid
    w = DJ.japan_world(g)
    r = DJ.osm_route(g, _node_at(g, 0, 1), _node_at(g, 2, 1))
    P, c = r["polyline"], r["cum"]
    k = int(np.searchsorted(c, r["stop_lines"][1]["s"] - 14.0))
    d = P[k + 1] - P[k]
    d = d / np.hypot(*d)
    K = DW.camera_intrinsics(60.0, 320, 200)
    pose = DW.camera_pose((P[k][0], P[k][1], 1.35), (P[k][0] + 20 * d[0], P[k][1] + 20 * d[1], 1.0))
    img = DW.world_camera(w, pose, K, 320, 200)
    lab = img["label"]
    assert (lab == 4).sum() > 10 and (lab == 9).sum() > 50 and np.ptp(img["color"]) > 0.3


def test_buildings_from_synthetic_plateau(grid):
    import driveplateau as PL
    osm, g = grid
    xml = PL.citygml_synthetic(n=3, origin=osm["origin"], spacing=30.0, size=10.0, heights=[10.0, 20.0, 30.0])
    d = PL.plateau_parse(xml, origin=osm["origin"])
    w = DJ.japan_world(g, buildings=d["buildings"])
    assert w["stats"]["buildings"] == 3 and 14 in set(np.unique(w["face_label"]).tolist())
    Vb = w["V"][w["F"][w["face_label"] == 14].ravel()]
    assert abs(Vb[:, 2].max() - 30.0) < 1e-9


# ── 実データ(あるときだけ) ───────────────────────────────────────────────────
@pytest.mark.skipif(not os.environ.get("FULLSEYE_OSM_DATA"), reason="FULLSEYE_OSM_DATA が無い(OSM の抜粋は repo に置かない)")
def test_real_osm_extract():
    p = Path(os.environ["FULLSEYE_OSM_DATA"]) / "ginza.osm"
    osm = DJ.osm_parse(p)
    g = DJ.osm_road_graph(osm, bbox=osm["bbox"])
    rm = DJ.osm_road_mask(g, step=1.0)
    lp = DJ.osm_road_loops(rm)
    assert lp["area_check"]["abs_err"] < 1e-4 and len(lp["holes"]) > 20 and g["n_edges"] > 100
