# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""optdraw(光学系の図面)の門。

図を**書いた文字列(SVG / DXF)から読み戻して**採点する。真値は optdraw の関数を通さない閉形式
(球面・円錐の sag、厚肉レンズの公式、optical_camera の視野の式)と、公表された処方の EFL。
壊して確かめる探針(sag の符号の反転、光線の折れ点のずれ、寸法の数字の書き換え、DXF の欠け)で
門が赤になることも確かめる。
"""
import math
import os
import re
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import optdraw as OD  # noqa: E402
import optscene as OS  # noqa: E402
import raytrace as RT  # noqa: E402
import telecentric as TC  # noqa: E402


def _sag(R, k, y):
    y = np.asarray(y, float)
    if R == math.inf:
        return np.zeros_like(y)
    if k == 0.0:
        return R - np.sign(R) * np.sqrt(R * R - y * y)
    c = 1.0 / R
    return c * y * y / (1.0 + np.sqrt(1.0 - (1.0 + k) * c * c * y * y))


def _zv(system):
    z = [0.0]
    for s in system["surfaces"][:-1]:
        z.append(z[-1] + s["t"])
    return z


def _cooke():
    """Cooke triplet(f = 50、F/5、半画角 20°)。公表 EFL 49.9998 mm at 0.55 µm。"""
    c = [{"R": 22.01359, "t": 3.25896, "n": "N-SK16"}, {"R": -435.76044, "t": 6.00755, "n": 1.0},
         {"R": -22.21328, "t": 0.99997, "n": "N-F2"}, {"R": 20.29192, "t": 4.75041, "n": 1.0, "ap": 4.6},
         {"R": 79.68360, "t": 2.95208, "n": "N-SK16"}, {"R": -18.39533, "t": 42.20778, "n": 1.0}]
    return RT.lens_system(c, stop=3, wavelength_um=0.55, field=20.0)


def _surface_residual(ents, system):
    zv = _zv(system)
    worst, n = 0.0, 0
    for e in ents:
        if e["type"] != "polyline" or e["layer"] not in ("OUTLINE", "THIN") or len(e["points"]) < 11:
            continue
        p = np.asarray(e["points"])
        z0 = p[np.argmin(np.abs(p[:, 1])), 0]
        i = int(np.argmin([abs(z0 - v) for v in zv]))
        s = system["surfaces"][i]
        worst = max(worst, float(np.max(np.abs(p[:, 0] - zv[i] - _sag(s["R"], s["k"], p[:, 1])))))
        n += 1
    return worst, n


def _ray_residual(ents, system):
    zv = _zv(system)
    worst = 0.0
    rays = [np.asarray(e["points"]) for e in ents if e["type"] == "polyline" and e["layer"].startswith("RAY_F")]
    for p in rays:
        for i, s in enumerate(system["surfaces"]):
            z, y = p[1 + i]
            worst = max(worst, abs(z - zv[i] - float(_sag(s["R"], s["k"], [y])[0])))
    return worst, len(rays)


def _dim(ents, name):
    v = [float(m.group(1)) for e in ents if e["type"] == "text"
         for m in [re.fullmatch(r"%s (-?\d+\.\d+)" % name, e["text"])] if m]
    return v[0] if len(v) == 1 else None


@pytest.fixture(scope="module")
def cooke_drawing():
    s = _cooke()
    return s, OD.lens_section_drawing(s, rays=5)


def test_cooke_efl_matches_published(cooke_drawing):
    s, d = cooke_drawing
    assert abs(d["values"]["efl"] / 49.9998 - 1.0) < 1e-3


@pytest.mark.parametrize("fmt", ["svg", "dxf"])
def test_surfaces_and_ray_hits_read_back_from_the_file(cooke_drawing, fmt):
    s, d = cooke_drawing
    ents = (OD.svg_entities(OD.drawing_svg(d)) if fmt == "svg" else OD.dxf_entities(OD.drawing_dxf(d)))["entities"]
    w, n = _surface_residual(ents, s)
    assert n == 6 and w < 1e-5
    w, n = _ray_residual(ents, s)
    assert n == 15 and w < 1e-5
    para = RT.paraxial_trace(s)
    for name, val in (("EFL", para["efl"]), ("BFL", para["bfl"])):
        assert abs(_dim(ents, name) - val) <= 0.005 + 1e-9


def test_chief_ray_matches_raytrace(cooke_drawing):
    s, d = cooke_drawing
    ents = OD.svg_entities(OD.drawing_svg(d))["entities"]
    for j, f in enumerate(d["values"]["fields"]):
        p = np.asarray([e for e in ents if e.get("tag") == "ray:%d:2" % j][0]["points"])
        ref = np.asarray(RT.chief_ray(s, field=f)["points"])[1:, [2, 1]]
        assert np.max(np.abs(p[1:] - ref)) < 1e-6


def test_thick_singlet_dimensions_match_lensmaker():
    n = 1.5168
    s = RT.lens_system([{"R": 60.0, "t": 6.0, "n": n, "ap": 12.0}, {"R": -80.0, "t": None, "n": 1.0}], stop=0)
    ents = OD.svg_entities(OD.drawing_svg(OD.lens_section_drawing(s)))["entities"]
    c1, c2, t = 1 / 60.0, -1 / 80.0, 6.0
    f = 1.0 / ((n - 1) * (c1 - c2 + (n - 1) * t * c1 * c2 / n))
    bfl = f * (1 - (n - 1) * t * c1 / n)
    assert abs(_dim(ents, "EFL") - f) <= 0.005 + 1e-9
    assert abs(_dim(ents, "BFL") - bfl) <= 0.005 + 1e-9


def test_conic_surface_is_drawn_with_the_conic_sag():
    s = RT.example_system("asphere")
    ents = OD.dxf_entities(OD.drawing_dxf(OD.lens_section_drawing(s)))["entities"]
    w, n = _surface_residual(ents, s)
    assert n == 2 and w < 1e-5


def test_object_side_telecentric_chief_ray_matches_newton_aiming():
    L = TC.telecentric_lens("object")
    d = OD.lens_section_drawing(L, fields=(0.0, 8.0), rays=3)
    ents = OD.svg_entities(OD.drawing_svg(d))["entities"]
    p = np.asarray([e for e in ents if e.get("tag") == "ray:1:1"][0]["points"])
    ang = math.degrees(math.atan2(p[1, 1] - p[0, 1], p[1, 0] - p[0, 0]))
    assert abs(ang - TC.chief_ray_angle(L, 8.0)["object_angle_deg"]) < 1e-6
    assert "BFL" in d["values"]["dimensions_skipped"]


def test_afocal_system_has_no_focal_dimensions():
    d = OD.lens_section_drawing(TC.telecentric_lens("bi"), fields=(0.0, 4.0))
    assert set(d["values"]["dimensions_skipped"]) == {"BFL", "EFL"}


@pytest.mark.parametrize("kind", ["ring", "dome", "bar", "coaxial", "backlight"])
def test_setup_drawing_fov_wd_dof_closed_forms(kind):
    sensor = OS.sensor_spec(pixel_um=3.45, resolution=(1024, 768))
    lens = OS.lens_spec(focal_mm=25.0, f_number=4.0, working_distance_mm=200.0)
    lay = OS.vision_layout(sensor, lens, [OS.light_spec(kind, radius_mm=60.0, height_mm=40.0, n=12)])
    ents = OD.svg_entities(OD.drawing_svg(OD.vision_setup_drawing(lay)))["entities"]
    fov_h = 768 * 3.45e-3 / (25.0 / 175.0)            # 画素数 × 画素 / m、m = f/(WD − f)(薄肉レンズを WD に合焦)
    ends = []
    for e in ents:
        if e.get("tag") == "side:fov_ray":
            a, b = e["points"]
            ends.append(a if abs(a[1]) < abs(b[1]) else b)
    ys = np.array([p[0] for p in ends])
    assert len(ends) == 4 and abs(ys.max() - fov_h / 2) < 1e-6 and abs(ys.min() + fov_h / 2) < 1e-6
    m = 25.0 / 175.0
    nw = (1 + m) * 4.0
    dof = (2 * nw * 3.45 + 2 * 0.55 * nw * nw) / (m * m) / 1000.0
    assert abs(_dim(ents, "WD") - 200.0) < 1e-9
    assert abs(_dim(ents, "DOF") - dof) <= 0.0005 + 1e-9
    if kind in ("ring", "bar"):
        el = [float(e["text"][:-1]) for e in ents if e["type"] == "text" and re.fullmatch(r"\d+\.\d°", e["text"])]
        assert abs(el[0] - math.degrees(math.atan2(40.0, 60.0))) <= 0.05 + 1e-9


def test_element_drawing_iso10110_fields():
    s = RT.lens_system([{"R": 51.68, "t": 5.0, "n": "N-BK7", "ap": 12.5}, {"R": math.inf, "t": None, "n": 1.0}], stop=0)
    d = OD.lens_element_drawing(s, trials=20)
    T = [e["text"] for e in OD.dxf_entities(OD.drawing_dxf(d))["entities"] if e["type"] == "text"]
    assert "R 51.680 CX  ±0.258" in T and "R INF" in T and "5.00±0.05" in T and "3/-(1)" in T and "4/3'" in T
    nd = [t for t in T if t.startswith("n_d ")][0]
    assert abs(float(nd.split()[1]) - 1.51680) <= 5e-6                  # メーカー公表値
    fr = max(abs(_sag(51.68 * (1 + e), 0, [12.5])[0] - _sag(51.68, 0, [12.5])[0]) for e in (0.005, -0.005)) / (0.54607e-3 / 2)
    assert abs(d["values"]["fringes_power"][0] - fr) < 1e-9
    d2 = OD.lens_element_drawing(s, trials=5, radius_tolerance="fringes")
    T2 = [e["text"] for e in d2["entities"] if e["type"] == "text"]
    assert "3/%s(%s)" % (OD._fringe(fr), OD._fringe(max(0.5, round(0.25 * fr * 2) / 2))) in T2


def test_roundtrip_svg_and_dxf(cooke_drawing):
    _, d = cooke_drawing
    order = {k: i for i, k in enumerate(OD.LAYERS)}
    for back, ents in ((OD.dxf_entities(OD.drawing_dxf(d)), d["entities"]),
                       (OD.svg_entities(OD.drawing_svg(d)), sorted(d["entities"], key=lambda e: order[e["layer"]]))):
        assert len(back["entities"]) == len(ents)
        for a, b in zip(ents, back["entities"]):
            assert a["type"] == b["type"] and a["layer"] == b["layer"]
            if a["type"] in ("line", "polyline"):
                assert np.max(np.abs(np.subtract(a["points"], b["points"]))) < 1e-6
            elif a["type"] == "text":
                assert a["text"] == b["text"]


def test_ezdxf_reads_the_file_if_available(cooke_drawing):
    ezdxf = pytest.importorskip("ezdxf")
    import io
    from ezdxf import recover
    _, d = cooke_drawing
    doc, aud = recover.read(io.BytesIO(OD.drawing_dxf(d).encode("ascii")))
    assert doc.dxfversion == "AC1009" and not aud.errors
    assert len(list(doc.modelspace())) == len(d["entities"])
    del ezdxf


# --------------------------------------------------------------------------- #
# 壊して確かめる
# --------------------------------------------------------------------------- #
def test_probe_flipped_sag_turns_the_gate_red(monkeypatch, cooke_drawing):
    s, _ = cooke_drawing
    orig = OD._sag_profile
    monkeypatch.setattr(OD, "_sag_profile", lambda srf, y: -orig(srf, y))
    try:
        bad = OD.lens_section_drawing(s, rays=3)
    except ValueError:
        return                                         # 縁の厚さが負で描けない = これも赤
    w, _ = _surface_residual(OD.svg_entities(OD.drawing_svg(bad))["entities"], s)
    assert w > 1e-3


def test_probe_shifted_ray_and_edited_number(cooke_drawing):
    s, d = cooke_drawing
    svg = OD.drawing_svg(d)
    ray = [e for e in OD.svg_entities(svg)["entities"] if e.get("tag") == "ray:1:0"][0]
    z, y = ray["points"][2]
    bad = svg.replace("%s,%s" % (OD._f(z), OD._f(-y)), "%s,%s" % (OD._f(z + 0.01), OD._f(-y)), 1)
    assert bad != svg and _ray_residual(OD.svg_entities(bad)["entities"], s)[0] > 5e-3
    t = "EFL %.2f" % d["values"]["efl"]
    bad = svg.replace(">%s<" % t, ">EFL %.2f<" % (d["values"]["efl"] + 0.1))
    assert abs(_dim(OD.svg_entities(bad)["entities"], "EFL") - d["values"]["efl"]) > 0.05


def test_probe_broken_dxf_is_refused_or_differs(cooke_drawing):
    _, d = cooke_drawing
    dxf = OD.drawing_dxf(d)
    k = dxf.index("\r\n  0\r\nVERTEX\r\n")
    k2 = dxf.index("\r\n  0\r\n", k + 4)
    back = OD.dxf_entities(dxf[:k] + dxf[k2:])
    lens = [len(e.get("points", [])) for e in back["entities"]]
    assert lens != [len(e.get("points", [])) for e in d["entities"]]
    with pytest.raises(ValueError):
        OD.dxf_entities(dxf.replace("\r\n  0\r\nENDSEC\r\n  0\r\nEOF\r\n", "\r\n  0\r\nEOF\r\n"))
    with pytest.raises(ValueError):
        OD.dxf_entities("  0\r\nSECTION\r\n  2\r\nENTITIES\r\n  0\r\nLINE\r\n 10\r\nnot-a-number\r\n")


# --------------------------------------------------------------------------- #
# 入口の拒否(fail-closed)
# --------------------------------------------------------------------------- #
def test_refuses_unsupported_inputs():
    # ★2026-10-15 から鏡は折り返した系の断面図(noncoaxial_drawing)に、接合レンズは組図になった(拒否しない)
    assert OD.lens_section_drawing(RT.example_system("paraboloid"))["meta"]["source"] == "raytrace3d.noncoaxial_system"
    assert OD.lens_element_drawing(RT.example_system("doublet"))["values"]["cemented"] is True
    with pytest.raises(ValueError):
        OD.lens_section_drawing({"surfaces": []})
    with pytest.raises(ValueError):
        OD.noncoaxial_drawing(RT.example_system("singlet"), view="xy")
    with pytest.raises(ValueError):
        OD.noncoaxial_drawing(RT.example_system("singlet"), rotate_deg=45)
    with pytest.raises(ValueError):
        OD.drawing_svg({"kind": "other"})
    with pytest.raises(ValueError):
        OD.svg_entities('<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY a "x">]><svg/>')
    with pytest.raises(ValueError):
        OD.vision_setup_drawing({"kind": "layout"} | {"camera": None}, view="front")
    d = OD.lens_section_drawing(RT.example_system("singlet"))
    d["entities"].append({"type": "text", "layer": "TEXT", "at": [0, 0], "text": "日本語", "height": 1.0})
    with pytest.raises(ValueError):
        OD.drawing_dxf(d)


def test_raster_has_the_paper_size():
    pytest.importorskip("matplotlib")
    d = OD.lens_section_drawing(RT.example_system("singlet"))
    img = OD.drawing_raster(d, dpi=25.4)
    x0, y0, x1, y1 = d["frame"]
    assert img.ndim == 3 and img.shape[2] == 3
    assert abs(img.shape[1] - (x1 - x0) * d["scale"]) <= 1.5 and abs(img.shape[0] - (y1 - y0) * d["scale"]) <= 1.5


def _imaged_width_px():
    sensor = OS.sensor_spec(pixel_um=13.8, resolution=(256, 192))
    lens = OS.lens_spec(focal_mm=25.0, f_number=4.0, working_distance_mm=200.0)
    part = OS.scene_box((0.0, 0.0, 0.05), (6.0, 4.0, 0.05))
    lay = OS.vision_layout(sensor, lens, [OS.light_spec("dome", radius_mm=80.0, height_mm=70.0, n=24)], scene=[part])
    mask = np.asarray(OS.layout_capture(lay, supersample=1, apply_diffraction=False)["part_mask"], bool)
    return int(mask[mask.shape[0] // 2].sum())


def test_imaged_width_matches_thin_lens_magnification():
    """図と独立の経路: 撮った画像の上で幅 12 mm の板が 12 × f/(WD − f) / 画素 の画素数に写る(2026-10-15 の混ざりの門)。"""
    want = 12.0 * (25.0 / 175.0) / 13.8e-3
    assert abs(_imaged_width_px() - want) <= 1.0


def test_probe_pinhole_at_focal_length_turns_the_imaging_gate_red(monkeypatch):
    monkeypatch.setattr(OS, "_thin_lens_image_distance", lambda f, wd: float(f))
    want = 12.0 * (25.0 / 175.0) / 13.8e-3
    assert abs(_imaged_width_px() - want) > 1.0


# --------------------------------------------------------------------------- #
# 2026-10-15: 折り返した系・接合レンズ・非球面の製作図(書いた SVG / DXF から読み戻して採点)
# --------------------------------------------------------------------------- #
def _texts(ents):
    return [e["text"] for e in ents if e["type"] == "text"]


@pytest.mark.parametrize("name", ["folded_singlet", "periscope", "epi_beamsplitter", "off_axis_parabola"])
def test_folded_layout_surfaces_and_rays_read_back_onto_the_3d_layout(name):
    import raytrace3d as R3
    s3 = R3.noncoaxial_example(name)
    d = OD.noncoaxial_drawing(s3)
    lay = R3.noncoaxial_layout(s3)
    for writer, reader in ((OD.drawing_svg, OD.svg_entities), (OD.drawing_dxf, OD.dxf_entities)):
        ents = reader(writer(d))["entities"]
        surfs = [e for e in ents if e["type"] == "polyline" and e.get("tag", "").startswith("surface:")] \
            if writer is OD.drawing_svg else [e for e in ents if e["type"] == "polyline" and e["layer"] in ("OUTLINE",)]
        # 面の曲線の中点 = 頂点(大域の z, y)に一致する面が、反射・屈折する面の数だけある
        verts = [(v["vertex"][2], v["vertex"][1]) for v in lay["surfaces"]]
        hit = 0
        assert len(verts) >= 2
        for (vz, vy) in verts:
            if any(np.min(np.hypot(np.asarray(e["points"])[:, 0] - vz, np.asarray(e["points"])[:, 1] - vy)) < 1e-5
                   for e in surfs):
                hit += 1
        assert hit >= len([v for v in lay["surfaces"] if v["reflect"] or v["beamsplitter"]])
        # 光線の折れ点は面の上(各光線の 2 点目以降は 3-D の追跡点の投影)
        rays = [np.asarray(e["points"]) for e in ents if e["type"] == "polyline" and e["layer"].startswith("RAY_F")]
        assert len(rays) == len(d["values"]["rays"])
        worst = max(float(np.max(np.abs(r[1:] - np.asarray(rr["points"])[:, [2, 1]])))
                    for r, rr in zip(rays, d["values"]["rays"]))
        assert worst < 2e-6
    # 寸法 W / H の数字 = 外接矩形
    ents = OD.svg_entities(OD.drawing_svg(d))["entities"]
    W = _dim(ents, "W")
    assert W is not None and abs(W - d["values"]["footprint"][0]) < 0.006


def test_folded_layout_path_length_and_fold_angle_match_the_closed_form():
    import raytrace3d as R3
    d = OD.noncoaxial_drawing(R3.noncoaxial_example("folded_singlet"))
    bfl = RT.paraxial_trace(RT.lens_system())["bfl"]
    assert abs(d["values"]["path_length"] - (5.0 + bfl)) < 1e-9          # 展開した軸の長さ = 中心厚 + BFL
    assert abs(d["values"]["fold_angles_deg"][0] - 90.0) < 1e-9          # 45° の鏡で 90°
    p = R3.noncoaxial_example("periscope")
    assert len(OD.noncoaxial_drawing(p)["values"]["fold_angles_deg"]) == 2


def test_probe_a_shifted_mirror_vertex_breaks_the_readback():
    import raytrace3d as R3
    s3 = R3.noncoaxial_example("folded_singlet")
    d = OD.noncoaxial_drawing(s3)
    svg = OD.drawing_svg(d)
    ents = OD.svg_entities(svg)["entities"]
    m = [e for e in ents if e["type"] == "polyline" and e.get("tag") == "surface:3"][0]
    v = R3.noncoaxial_layout(s3)["surfaces"][-1]["vertex"]
    ok = np.min(np.hypot(np.asarray(m["points"])[:, 0] - v[2], np.asarray(m["points"])[:, 1] - v[1])) < 1e-5
    assert ok
    bad = [dict(e, points=[[x + 0.01, y] for x, y in e["points"]]) if e is m else e for e in ents]
    mb = [e for e in bad if e["type"] == "polyline" and e.get("tag") == "surface:3"][0]
    assert np.min(np.hypot(np.asarray(mb["points"])[:, 0] - v[2], np.asarray(mb["points"])[:, 1] - v[1])) > 1e-3


def test_aspheric_element_drawing_writes_an_iso_10110_12_sag_table_that_reads_back():
    s = RT.example_system("asphere")
    d = OD.lens_element_drawing(s)
    tab = d["values"]["sag_tables"][2]
    surf = s["surfaces"][1]
    assert len(tab) == OD.SAG_TABLE_ROWS
    for h, z in tab:                                          # 表の数 = raytrace の sag の式(閉形式の円錐)
        c = 1.0 / surf["R"]
        want = c * h * h / (1.0 + math.sqrt(1.0 - (1.0 + surf["k"]) * c * c * h * h))
        assert abs(z - want) < 1e-12
    for writer, reader in ((OD.drawing_svg, OD.svg_entities), (OD.drawing_dxf, OD.dxf_entities)):
        rows = []
        for t in _texts(reader(writer(d))["entities"]):
            m = re.fullmatch(r"\s*(-?\d+\.\d{4})\s+(-?\d+\.\d{6})", t)
            if m:
                rows.append((float(m.group(1)), float(m.group(2))))
        assert len(rows) == OD.SAG_TABLE_ROWS
        for (h, z), (h2, z2) in zip(rows, tab):
            assert abs(h - h2) < 6e-5 and abs(z - z2) < 6e-7
    # 壊した表(sag の符号を反転)は閉形式と合わない
    assert max(abs(-z - z2) for (h, z), (h2, z2) in zip(tab, tab) if abs(z) > 1e-3) > 1e-3


def test_cemented_group_drawing_reads_back_radii_glasses_and_thicknesses():
    s = RT.example_system("doublet")
    d = OD.lens_element_drawing(s)
    v = d["values"]
    assert v["R"] == [61.47, -44.64, -129.94] and v["center_thickness"] == [6.0, 2.5]
    nd = [RT.refractive_index((1.5168, 64.17), RT.WL_D), RT.refractive_index((1.6477, 33.85), RT.WL_D)]
    assert max(abs(a - b) for a, b in zip(v["nd"], nd)) < 1e-12
    txt = _texts(OD.dxf_entities(OD.drawing_dxf(d))["entities"])
    assert txt
    assert any(re.fullmatch(r"2\s+-44\.6400\s+\S+", t) for t in txt)
    assert any(re.fullmatch(r"2\s+1\.64770\s+33\.85\s+2\.50", t) for t in txt)
    # 群の EFL(注記)= 処方の EFL
    assert abs(v["efl"] - RT.paraxial_trace(s)["efl"]) < 1e-9
