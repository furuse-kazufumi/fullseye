"""driveplateau のテスト(numpy + pytest のみ、実データ不要)。"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

import driveplateau as pp

ORIGIN = (35.6716, 139.7650)


def signed_volume(V: np.ndarray, F: np.ndarray) -> float:
    """閉じた三角形メッシュの符号つき体積(発散定理 Σ v0·(v1×v2)/6)。"""
    v0 = V[F[:, 0]]
    v1 = V[F[:, 1]]
    v2 = V[F[:, 2]]
    return float(np.sum(np.einsum("ij,ij->i", v0, np.cross(v1, v2))) / 6.0)


def closed_prism(V: np.ndarray, F: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """prism_mesh の出力(底面なし)に、底の環 V[0:k] を使った底面(下向き)を足す。"""
    k = footprint.shape[0]
    bottom = pp.triangulate_polygon(footprint)[:, ::-1]  # 反転 → 下向き法線
    assert bottom.max() < k
    return np.vstack([F, bottom])


# --------------------------------------------------------------------------
# latlon_to_local
# --------------------------------------------------------------------------
def test_latlon_to_local_origin_is_zero():
    x, y = pp.latlon_to_local(ORIGIN[0], ORIGIN[1], ORIGIN)
    assert x == 0.0 and y == 0.0


def test_latlon_to_local_known_values():
    # 緯度 +0.001° ≈ 111.3 m(1 m 以内)。R·Δlat = 6378137·0.001·π/180 = 111.319 m
    _x, y = pp.latlon_to_local(ORIGIN[0] + 0.001, ORIGIN[1], ORIGIN)
    assert abs(y - 111.3) < 1.0
    # 経度 +0.001° は cos(35.67°)≈0.8124 倍 → 約 90.4 m
    x, _y = pp.latlon_to_local(ORIGIN[0], ORIGIN[1] + 0.001, ORIGIN)
    assert abs(x - 111.319 * math.cos(math.radians(ORIGIN[0]))) < 0.01
    assert x > 0.0


def test_latlon_to_local_array_and_sign():
    lat = np.array([ORIGIN[0], ORIGIN[0] - 0.001])
    lon = np.array([ORIGIN[1] - 0.001, ORIGIN[1]])
    x, y = pp.latlon_to_local(lat, lon, ORIGIN)
    assert x.shape == (2,) and y.shape == (2,)
    assert x[0] < 0.0 and y[0] == 0.0
    assert x[1] == 0.0 and y[1] < 0.0


def test_latlon_to_local_rejects_bad_input():
    with pytest.raises(ValueError):
        pp.latlon_to_local(0.0, 0.0, (0.0,))
    with pytest.raises(ValueError):
        pp.latlon_to_local(95.0, 0.0, ORIGIN)
    with pytest.raises(ValueError):
        pp.latlon_to_local(float("nan"), 0.0, ORIGIN)
    with pytest.raises(ValueError):
        pp.latlon_to_local(np.zeros(2), np.zeros(3), ORIGIN)


# --------------------------------------------------------------------------
# plateau_parse(合成 CityGML)
# --------------------------------------------------------------------------
def test_parse_synthetic_counts_heights_area_ground():
    heights = [8.0, 15.5, 31.0, 42.25]
    xml = pp.citygml_synthetic(4, origin=ORIGIN, size=12.0, heights=heights)
    parsed = pp.plateau_parse(xml, origin=ORIGIN)
    assert parsed["crs"] == "EPSG:6697 (lat, lon, alt)"
    assert parsed["n_skipped"] == 0
    bs = parsed["buildings"]
    assert len(bs) == 4
    assert len(bs) == len(heights) > 0
    for b, h in zip(bs, heights):
        assert b["height"] == h
        assert b["footprint"].shape == (4, 2)
        assert abs(pp.polygon_area(b["footprint"]) - 144.0) < 1e-6
        assert pp.polygon_area(b["footprint"]) > 0.0  # 反時計回り
        assert b["ground_z"] == 0.0
        assert b["id"].startswith("bldg_synth_")
    # 建物中心は spacing 間隔で x 方向に並ぶ
    cx = [b["footprint"].mean(axis=0)[0] for b in bs]
    assert len(cx) > 0
    for i, c in enumerate(cx):
        assert abs(c - 30.0 * i) < 1e-6


def test_parse_origin_none_uses_first_building_centroid():
    xml = pp.citygml_synthetic(3, origin=ORIGIN)
    parsed = pp.plateau_parse(xml)
    lat0, lon0 = parsed["origin"]
    assert abs(lat0 - ORIGIN[0]) < 1e-9 and abs(lon0 - ORIGIN[1]) < 1e-9
    assert np.allclose(parsed["buildings"][0]["footprint"].mean(axis=0), 0.0, atol=1e-6)
    assert abs(parsed["buildings"][0]["lat"] - ORIGIN[0]) < 1e-9


def test_parse_selects_bottom_face_of_lod1solid():
    # 底面標高 5 m、高さ 20 m。天面(標高 25 m)でなく底面(5 m)が選ばれる。
    xml = pp.citygml_synthetic(1, origin=ORIGIN, size=10.0, heights=[20.0], ground_z=5.0)
    b = pp.plateau_parse(xml, origin=ORIGIN)["buildings"][0]
    assert abs(b["ground_z"] - 5.0) < 1e-9
    assert abs(pp.polygon_area(b["footprint"]) - 100.0) < 1e-6
    assert b["height"] == 20.0


def test_parse_height_from_solid_when_measured_missing():
    xml = pp.citygml_synthetic(2, origin=ORIGIN, heights=[12.0, 27.5], ground_z=3.0, omit_measured_height=[1])
    assert xml.count("measuredHeight") == 2  # 開閉タグ 1 組 = 建物 0 だけ
    bs = pp.plateau_parse(xml, origin=ORIGIN)["buildings"]
    assert bs[0]["height"] == 12.0
    assert abs(bs[1]["height"] - 27.5) < 1e-9  # 最大標高 30.5 − 最小標高 3.0
    assert abs(bs[1]["ground_z"] - 3.0) < 1e-9


def test_parse_lod0_footprint_preferred():
    xml = pp.citygml_synthetic(1, origin=ORIGIN, size=9.0, heights=[7.0], use_lod0_footprint=True)
    assert "lod0FootPrint" in xml
    b = pp.plateau_parse(xml, origin=ORIGIN)["buildings"][0]
    assert abs(pp.polygon_area(b["footprint"]) - 81.0) < 1e-6
    assert b["height"] == 7.0


def test_parse_other_namespace_version_still_reads():
    xml = pp.citygml_synthetic(2, origin=ORIGIN)
    xml_v1 = xml.replace("http://www.opengis.net/citygml/building/2.0", "http://www.opengis.net/citygml/building/1.0")
    assert xml_v1 != xml
    assert len(pp.plateau_parse(xml_v1, origin=ORIGIN)["buildings"]) == 2
    # 接頭辞そのものを変えても読める
    xml_pref = xml.replace("xmlns:bldg=", "xmlns:b=").replace("bldg:", "b:")
    assert "bldg:" not in xml_pref and "xmlns:bldg" not in xml_pref
    assert len(pp.plateau_parse(xml_pref, origin=ORIGIN)["buildings"]) == 2


def test_parse_from_file_path(tmp_path: Path):
    xml = pp.citygml_synthetic(3, origin=ORIGIN)
    f = tmp_path / "synth.gml"
    f.write_text(xml, encoding="utf-8")
    assert len(pp.plateau_parse(f, origin=ORIGIN)["buildings"]) == 3
    assert len(pp.plateau_parse(str(f), origin=ORIGIN)["buildings"]) == 3


def test_parse_max_buildings():
    xml = pp.citygml_synthetic(5, origin=ORIGIN)
    assert len(pp.plateau_parse(xml, origin=ORIGIN, max_buildings=2)["buildings"]) == 2
    with pytest.raises(ValueError):
        pp.plateau_parse(xml, origin=ORIGIN, max_buildings=-1)


def test_parse_rejects_bad_poslist_and_empty():
    with pytest.raises(ValueError):
        pp.plateau_parse("")
    with pytest.raises(ValueError):
        pp.plateau_parse("   ")
    xml = pp.citygml_synthetic(1, origin=ORIGIN)
    # 1 つの posList の末尾に値を 1 個足して 3 の倍数でなくする
    broken = xml.replace("</gml:posList>", " 1.0</gml:posList>", 1)
    with pytest.raises(ValueError):
        pp.plateau_parse(broken, origin=ORIGIN)
    # 数値でない
    broken2 = xml.replace("<gml:posList>", "<gml:posList>abc ", 1)
    with pytest.raises(ValueError):
        pp.plateau_parse(broken2, origin=ORIGIN)
    # 壊れた XML
    with pytest.raises(ValueError):
        pp.plateau_parse(xml[: len(xml) // 2], origin=ORIGIN)
    # 存在しないパス
    with pytest.raises(ValueError):
        pp.plateau_parse("C:/no/such/file.gml")


def test_parse_skips_building_without_geometry():
    xml = pp.citygml_synthetic(1, origin=ORIGIN)
    extra = (
        "  <core:cityObjectMember>\n"
        "    <bldg:Building gml:id=\"nogeom\">\n"
        "      <bldg:measuredHeight uom=\"m\">5.0</bldg:measuredHeight>\n"
        "    </bldg:Building>\n"
        "  </core:cityObjectMember>\n"
    )
    xml2 = xml.replace("</core:CityModel>", extra + "</core:CityModel>")
    parsed = pp.plateau_parse(xml2, origin=ORIGIN)
    assert len(parsed["buildings"]) == 1
    assert parsed["n_skipped"] == 1


# --------------------------------------------------------------------------
# buildings_in_box
# --------------------------------------------------------------------------
def test_buildings_in_box():
    parsed = pp.plateau_parse(pp.citygml_synthetic(4, origin=ORIGIN, spacing=30.0), origin=ORIGIN)
    sel = pp.buildings_in_box(parsed, 20.0, 70.0, -10.0, 10.0)
    assert [b["id"] for b in sel] == ["bldg_synth_0001", "bldg_synth_0002"]
    assert pp.buildings_in_box(parsed, 200.0, 300.0, -10.0, 10.0) == []
    with pytest.raises(ValueError):
        pp.buildings_in_box(parsed, 10.0, 0.0, 0.0, 1.0)
    with pytest.raises(ValueError):
        pp.buildings_in_box({}, 0.0, 1.0, 0.0, 1.0)


# --------------------------------------------------------------------------
# 三角形分割・押し出し
# --------------------------------------------------------------------------
L_SHAPE = np.array([[0.0, 0.0], [2.0, 0.0], [2.0, 1.0], [1.0, 1.0], [1.0, 2.0], [0.0, 2.0]])


def tri_area_sum(poly: np.ndarray, tris: np.ndarray) -> float:
    s = 0.0
    assert len(tris) > 0
    for a, b, c in tris:
        s += 0.5 * abs(
            (poly[b, 0] - poly[a, 0]) * (poly[c, 1] - poly[a, 1])
            - (poly[b, 1] - poly[a, 1]) * (poly[c, 0] - poly[a, 0])
        )
    return s


def test_triangulate_concave_L_shape():
    tris = pp.triangulate_polygon(L_SHAPE)
    assert tris.shape == (4, 3)
    assert abs(tri_area_sum(L_SHAPE, tris) - 3.0) < 1e-12
    # 各三角形は反時計回り(正の面積)
    assert len(tris) > 0
    for a, b, c in tris:
        assert pp.polygon_area(L_SHAPE[[a, b, c]]) > 0.0
    # 時計回り入力でも同じ面積・同じ添字範囲
    tris_cw = pp.triangulate_polygon(L_SHAPE[::-1])
    assert abs(tri_area_sum(L_SHAPE[::-1], tris_cw) - 3.0) < 1e-12


def test_triangulate_more_concave_shapes():
    # U 字(凹 2 か所)と、一直線上の点を含む四角
    u = np.array([[0, 0], [3, 0], [3, 3], [2, 3], [2, 1], [1, 1], [1, 3], [0, 3]], dtype=float)
    tris = pp.triangulate_polygon(u)
    assert abs(tri_area_sum(u, tris) - 7.0) < 1e-12
    sq = np.array([[0, 0], [1, 0], [2, 0], [2, 2], [0, 2]], dtype=float)
    tris = pp.triangulate_polygon(sq)
    assert abs(tri_area_sum(sq, tris) - 4.0) < 1e-12
    with pytest.raises(ValueError):
        pp.triangulate_polygon(np.array([[0, 0], [1, 1], [2, 2]], dtype=float))  # 面積 0
    with pytest.raises(ValueError):
        pp.triangulate_polygon(np.array([[0, 0], [1, 0]], dtype=float))


def test_prism_volume_theorem_square_and_L():
    for poly, area in ((np.array([[0.0, 0.0], [12.0, 0.0], [12.0, 12.0], [0.0, 12.0]]), 144.0), (L_SHAPE * 7.0, 3.0 * 49.0)):
        h = 17.3
        V, F, is_roof = pp.prism_mesh(poly, h, base_z=2.0)
        k = poly.shape[0]
        assert V.shape == (2 * k, 3)
        assert F.shape[0] == 2 * k + (k - 2)
        assert is_roof.sum() == k - 2
        Fc = closed_prism(V, F, poly)
        assert abs(signed_volume(V, Fc) - area * h) < 1e-6
        # 側面の法線は外向き: 反時計回りの辺 (dx,dy) の外向き法線は (dy,-dx)。
        # 側面 i の 2 三角形は F[2i], F[2i+1](辺 i→i+1)。
        for i in range(k):
            dx, dy = poly[(i + 1) % k] - poly[i]
            out_xy = np.array([dy, -dx])
            for f in F[2 * i : 2 * i + 2]:
                n = np.cross(V[f[1]] - V[f[0]], V[f[2]] - V[f[0]])
                assert abs(n[2]) < 1e-9
                assert np.dot(n[:2], out_xy) > 0.0
        # 屋根の法線は上向き
        for f in F[is_roof]:
            n = np.cross(V[f[1]] - V[f[0]], V[f[2]] - V[f[0]])
            assert n[2] > 0.0


def test_building_prisms_assembly_and_colors():
    parsed = pp.plateau_parse(pp.citygml_synthetic(3, origin=ORIGIN, heights=[5.0, 30.0, 70.0]), origin=ORIGIN)
    V, F, C, ids = pp.building_prisms(parsed["buildings"])
    assert V.shape == (3 * 8, 3)
    assert F.shape == (3 * 10, 3)
    assert C.shape == (F.shape[0], 3) and ids.shape == (F.shape[0],)
    assert np.all((C >= 0.0) & (C <= 1.0))
    assert sorted(set(ids.tolist())) == [0, 1, 2]
    assert F.max() == V.shape[0] - 1
    # 高さで色が決定的に変わる(乱数なし)
    V2, F2, C2, ids2 = pp.building_prisms(parsed["buildings"])
    assert np.array_equal(C, C2) and np.array_equal(V, V2)
    assert not np.allclose(C[ids == 0][0], C[ids == 2][0])
    # 全建物の体積の和
    total = 0.0
    off = 0
    for bi, b in enumerate(parsed["buildings"]):
        Fb = F[ids == bi] - off
        Vb = V[off : off + 8]
        total += signed_volume(Vb, closed_prism(Vb, Fb, b["footprint"]))
        off += 8
    assert abs(total - 144.0 * (5.0 + 30.0 + 70.0)) < 1e-6
    # base_z=None なら ground_z に置く
    V3, _F3, _C3, _ids3 = pp.building_prisms(parsed["buildings"], base_z=None)
    assert np.allclose(V3[:4, 2], parsed["buildings"][0]["ground_z"])


def test_building_prisms_custom_color_fn_and_validation():
    parsed = pp.plateau_parse(pp.citygml_synthetic(2, origin=ORIGIN), origin=ORIGIN)
    V, F, C, ids = pp.building_prisms(parsed["buildings"], color_fn=lambda b: (1.0, 0.0, 0.0), roof_shade=1.0)
    assert np.all(C == np.array([1.0, 0.0, 0.0]))
    with pytest.raises(ValueError):
        pp.building_prisms(parsed["buildings"], color_fn=lambda b: (2.0, 0.0, 0.0))
    with pytest.raises(ValueError):
        pp.building_prisms([{"footprint": L_SHAPE}])
    with pytest.raises(ValueError):
        pp.prism_mesh(L_SHAPE, 0.0)
    V0, F0, C0, i0 = pp.building_prisms([])
    assert V0.shape == (0, 3) and F0.shape == (0, 3) and C0.shape == (0, 3) and i0.shape == (0,)


def test_citygml_synthetic_structure_and_validation():
    xml = pp.citygml_synthetic(2, origin=ORIGIN)
    for tag in ("core:CityModel", "bldg:Building", "bldg:measuredHeight", "bldg:lod1Solid", "gml:Solid",
                "gml:CompositeSurface", "gml:surfaceMember", "gml:Polygon", "gml:LinearRing", "gml:posList"):
        assert tag in xml
    assert xml.count("<gml:surfaceMember>") == 2 * 6
    assert "EPSG/0/6697" in xml
    with pytest.raises(ValueError):
        pp.citygml_synthetic(-1)
    with pytest.raises(ValueError):
        pp.citygml_synthetic(2, heights=[1.0])
    with pytest.raises(ValueError):
        pp.citygml_synthetic(1, size=0.0)
