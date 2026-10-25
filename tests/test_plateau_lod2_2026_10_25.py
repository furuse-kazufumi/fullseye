# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""driveplateau.plateau_lod2_mesh(PLATEAU の CityGML LOD2 → 三角形メッシュ)と会場の npz の試験(2026-10-25)。

真値は閉形式: 合成の切妻屋根の建物(本体 2000 m³・部位 144 m³、屋根の面積 2·20·√41 + 36 − 4)と、
楕円体の厳密な往復変換。会場の npz は ``measuredHeight`` との一致(±0.05 m)と外向きの向きを確かめる。
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

import driveplateau as PL

ROOT = Path(__file__).resolve().parents[1]
ORG = (35.4575, 139.6375, 3.0)
VENUE = ROOT / "data" / "plateau_yokohama" / "venue_lod2.npz"


def _vol(V, F):
    v0, v1, v2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    return float(np.sum(np.einsum("ij,ij->i", v0, np.cross(v1, v2))) / 6.0)


def _area(V, F):
    return float(0.5 * np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1).sum())


# ---------------------------------------------------------------- 座標変換
def test_enu_round_trip_is_exact_to_a_nanometre():
    rng = np.random.default_rng(0)
    enu = rng.uniform(-500.0, 500.0, (200, 3))
    llh = PL._enu_to_geodetic(enu, ORG)
    back = PL._geodetic_to_enu(llh, ORG)
    assert np.max(np.abs(back - enu)) < 1e-6


def test_enu_matches_meridian_and_prime_vertical_radii():
    a, f = 6378137.0, 1.0 / 298.257222101
    e2 = f * (2 - f)
    lat = math.radians(ORG[0])
    w = math.sqrt(1 - e2 * math.sin(lat) ** 2)
    M, N = a * (1 - e2) / w ** 3, a / w
    d = 1e-5                                                     # 約 1 m
    p = PL._geodetic_to_enu(np.array([[ORG[0] + d, ORG[1], ORG[2]], [ORG[0], ORG[1] + d, ORG[2]]]), ORG)
    assert abs(p[0, 1] - math.radians(d) * M) < 1e-6
    assert abs(p[1, 0] - math.radians(d) * N * math.cos(lat)) < 1e-6
    assert abs(p[0, 0]) < 1e-9 and abs(p[1, 1]) < 1e-6


# ---------------------------------------------------------------- 合成の LOD2
def test_synthetic_heights_extents_and_attributes():
    m = PL.plateau_lod2_mesh(PL._citygml_lod2_example(), origin=ORG)
    body, part = m["units"]
    assert (body["part"], part["part"]) == (0, 1)
    assert body["building_id"] == part["building_id"] == "lod2_example_0001"
    assert part["gml_id"] == "lod2_example_0001_p1"
    assert body["measured_height"] == 12.0 and part["measured_height"] == 4.0
    assert abs(body["height_mesh"] - 12.0) < 1e-6 and abs(part["height_mesh"] - 4.0) < 1e-6
    assert np.allclose(body["extent_xy"], (20.0, 10.0), atol=1e-6)
    assert np.allclose(part["extent_xy"], (6.0, 6.0), atol=1e-6)
    assert body["attrs"] == {"note": "synthetic"}
    assert m["kinds"] == ("ground", "wall", "roof", "other")
    assert set(m["face_kind"].tolist()) == {0, 1, 2}
    # 非平面性は多角形ごとの等距円筒の近似で測るので、厳密な ENU で平らな面でも 1e-6 m 台が出る
    assert m["max_nonplanarity_m"] < 1e-5
    assert m["n_buildings"] == 1 and m["n_no_lod2"] == 0 and m["n_bad_polygons"] == 0


def test_synthetic_volume_is_closed_form_and_faces_point_outwards():
    m = PL.plateau_lod2_mesh(PL._citygml_lod2_example(with_hole=False), origin=ORG)
    V, F, U = m["V"], m["F"], m["face_unit"]
    assert abs(_vol(V, F[U == 0]) - 2000.0) < 1e-5                # 20·10·8 + 20·(10·4/2)
    assert abs(_vol(V, F[U == 1]) - 144.0) < 1e-5                 # 6·6·4
    # 閉じている: 各部位のどの辺もちょうど 2 枚の三角形が共有する
    for i in (0, 1):
        f = F[U == i]
        e = np.sort(np.vstack([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), axis=1)
        _, c = np.unique(e, axis=0, return_counts=True)
        assert set(c.tolist()) == {2}


def test_hole_is_left_open_and_roof_area_matches():
    m = PL.plateau_lod2_mesh(PL._citygml_lod2_example(with_hole=True), origin=ORG)
    roof = m["F"][m["face_kind"] == 2]
    want = 2 * 20 * math.hypot(5.0, 4.0) + 36.0 - 4.0              # 切妻 2 枚 + 部位の屋根 − 2 m 角の穴
    assert abs(_area(m["V"], roof) - want) < 1e-5
    # 穴の真ん中 (23, 5) を覆う屋根の三角形は無い
    P = m["V"][roof][:, :, :2]
    q = np.array([23.0, 5.0])
    d = lambda a, b: (b[:, 0] - a[:, 0]) * (q[1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (q[0] - a[:, 0])  # noqa: E731
    s0, s1, s2 = d(P[:, 0], P[:, 1]), d(P[:, 1], P[:, 2]), d(P[:, 2], P[:, 0])
    inside = ((s0 >= 0) & (s1 >= 0) & (s2 >= 0)) | ((s0 <= 0) & (s1 <= 0) & (s2 <= 0))
    assert not inside.any()


def test_default_origin_is_the_ground_centroid():
    m = PL.plateau_lod2_mesh(PL._citygml_lod2_example(with_hole=False))
    g = m["F"][m["face_kind"] == 0]
    # 地面の最低点が z = 0(合成は別の原点 ORG の接平面で置いたので、原点が 16.5 m 動いた分の
    # 地球の丸み d²/2R ≈ 2e-5 m だけずれる)
    assert abs(m["V"][np.unique(g), 2].min()) < 1e-4
    assert abs(m["origin"][2] - 3.0) < 1e-6
    # 原点の緯度経度 = 地面の頂点の平均(本体 4 点 + 部位 4 点 → x = (0+20+20+0+20+26+26+20)/8 = 16.5)
    xy = m["V"][np.unique(g), :2].mean(axis=0)
    assert np.allclose(xy, 0.0, atol=1e-3)


def test_ids_and_bbox_filters():
    src = PL._citygml_lod2_example()
    assert len(PL.plateau_lod2_mesh(src, ids=["lod2_example_0001"])["units"]) == 2
    with pytest.raises(ValueError):
        PL.plateau_lod2_mesh(src, ids=["nope"])
    with pytest.raises(ValueError):
        PL.plateau_lod2_mesh(src, ids=[])
    far = (10.0, 10.0, 10.1, 10.1)
    with pytest.raises(ValueError):
        PL.plateau_lod2_mesh(src, bbox_latlon=far)
    near = (35.45, 139.63, 35.47, 139.65)
    assert len(PL.plateau_lod2_mesh(src, bbox_latlon=near)["units"]) == 2
    with pytest.raises(ValueError):
        PL.plateau_lod2_mesh(src, bbox_latlon=(35.47, 139.63, 35.45, 139.65))


# ---------------------------------------------------------------- fail-closed
@pytest.mark.parametrize("old,new", [
    ("EPSG/0/6697", "EPSG/0/4326"),                                           # 別の座標参照系
    ('<gml:surfaceMember><gml:Polygon gml:id="p_g">',
     '<gml:surfaceMember><gml:OrientableSurface/><gml:Polygon gml:id="p_g">'),  # 未知の幾何
    ("bldg:GroundSurface", "bldg:InteriorWallSurface"),                       # 表に無い主題面
    ('xlink:href="#b_g"', 'xlink:href="#missing"'),                           # 見つからない参照
    ('uom="m">12.0', 'uom="ft">12.0'),                                        # m 以外の単位
    ('xlink:href="#b_g"', 'xlink:href="other.gml#b_g"'),                      # 外部ファイル参照
])
def test_fail_closed(old, new):
    src = PL._citygml_lod2_example()
    assert src.count(old) >= 1
    with pytest.raises(ValueError):
        PL.plateau_lod2_mesh(src.replace(old, new))


def test_bad_polygon_raises_by_default_and_is_counted_when_skipped():
    src = PL._citygml_lod2_example(with_hole=False)
    # 部位の地面の環を 1 点に潰す(面積 0)
    i = src.index('gml:id="p_g"')
    j = src.index("<gml:posList>", i) + len("<gml:posList>")
    k = src.index("</gml:posList>", j)
    first = " ".join(src[j:k].split()[:3])
    bad = src[:j] + " ".join([first] * 5) + src[k:]
    with pytest.raises(ValueError):
        PL.plateau_lod2_mesh(bad)
    m = PL.plateau_lod2_mesh(bad, on_bad_polygon="skip")
    assert m["n_bad_polygons"] == 1
    with pytest.raises(ValueError):
        PL.plateau_lod2_mesh(src, on_bad_polygon="ignore")


def test_rejects_empty_and_garbage_sources():
    for s in ("", b"", "<not xml", "no_such_file.gml"):
        with pytest.raises(ValueError):
            PL.plateau_lod2_mesh(s)


def test_building_without_lod2_is_counted_not_meshed():
    lod1 = PL.citygml_synthetic(n=2)
    with pytest.raises(ValueError):                                # LOD1 だけのファイルには LOD2 の部位が無い
        PL.plateau_lod2_mesh(lod1)


# ---------------------------------------------------------------- 会場の npz
def test_venue_asset_matches_measured_heights_and_is_small():
    assert VENUE.stat().st_size < 300_000
    d = np.load(VENUE, allow_pickle=False)
    V, F, U, K = d["V"], d["F"], d["face_unit"], d["face_kind"]
    assert V.dtype == np.float64 and np.all(np.isfinite(V))
    assert F.min() >= 0 and F.max() < len(V)
    n = len(d["unit_label_ja"])
    assert n == 7 and U.max() == n - 1 and set(np.unique(K).tolist()) <= {0, 1, 2, 3}
    for i in range(n):
        z = V[np.unique(F[U == i]), 2]
        g = V[np.unique(F[(U == i) & (K == 0)]), 2]
        h = z.max() - g.min()
        assert abs(h - d["unit_height_mesh"][i]) < 1e-9
        assert abs(h - d["unit_measured_height"][i]) <= 0.05
        assert _vol(V, F[U == i]) > 0.0                            # 外向き
    assert abs(d["unit_measured_height"].max() - 142.1) < 1e-9     # ホテル棟
    meta = json.loads(str(d["meta_json"]))
    assert "PDL1.0" in meta["licence"] and len(meta["files"]) == 2
    assert all(all(u["gates"]) for u in meta["units"])


def test_venue_readme_states_source_licence_and_changes():
    t = (ROOT / "data" / "plateau_yokohama" / "README.md").read_text(encoding="utf-8")
    for word in ("国土交通省", "PDL1.0", "CC BY 4.0", "加工して作成", "加工の内容"):
        assert word in t
