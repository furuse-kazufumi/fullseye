# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""printpath(G-code / 3MF / スライス / 層画像の検査)の門: 閉形式の真値で固定する。"""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import printpath as P  # noqa: E402

_OPS = ["gcode_read", "gcode_write", "gcode_extrusion_volume", "gcode_time_estimate", "gcode_layer_image",
        "mesh_slice_contours", "mesh_slice_stack", "contours_to_gcode", "read_3mf", "write_3mf", "print_layer_defect_map"]
FIL_AREA = np.pi * (1.75 / 2) ** 2


def box(x0, y0, z0, x1, y1, z1, flip=False):
    V = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0], [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], float)
    F = np.array([[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5], [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]])
    return V, (F[:, ::-1] if flip else F)


def box_with_hole():
    """20 × 10 × 6 mm の箱に 4 × 4 の角穴(内向きの面)。層の面積 = 200 − 16 = 184 mm²。"""
    V1, F1 = box(0, 0, 0, 20, 10, 6)
    V2, F2 = box(8, 3, -1, 12, 7, 7, flip=True)
    return np.vstack([V1, V2]), np.vstack([F1, F2 + 8])


def test_slicing_a_box_with_a_hole_gives_two_rings_and_the_exact_area():
    mesh = box_with_hole()
    c = P.mesh_slice_contours(mesh, 3.0)
    assert set(c) == {"ring", "x", "y"} and np.unique(c["ring"]).tolist() == [0, 1]
    boxes = sorted([(c["x"][c["ring"] == r].min(), c["x"][c["ring"] == r].max(), c["y"][c["ring"] == r].min(), c["y"][c["ring"] == r].max())
                    for r in (0, 1)])
    assert np.allclose(boxes[0], (0, 20, 0, 10)) and np.allclose(boxes[1], (8, 12, 3, 7))
    stack = P.mesh_slice_stack(mesh, layer_mm=1.0, px_per_mm=5.0)
    assert stack.shape == (8, 70, 120) and set(np.unique(stack)) <= {0.0, 1.0}
    assert abs(stack[3].sum() / 25.0 - 184.0) < 1e-9                        # even-odd で穴は穴のまま
    assert stack[0].sum() == 0.0 and stack[7].sum() == 0.0                    # 箱の外(穴だけ)の層は空
    with pytest.raises(ValueError, match="does not intersect"):
        P.mesh_slice_contours(box(0, 0, 0, 1, 1, 1), 5.0)
    with pytest.raises(ValueError, match="mesh must be"):
        P.mesh_slice_contours(np.zeros((3, 3)), 0.5)


def test_contours_to_gcode_extrudes_the_closed_form_amount_and_round_trips(tmp_path):
    mesh = box_with_hole()
    c = P.mesh_slice_contours(mesh, 3.0)
    g = P.contours_to_gcode(c, z=3.0, layer=3, layer_mm=0.2, line_width_mm=0.4)
    perim = 2 * (20 + 10) + 2 * (4 + 4)
    assert abs(g["e"].sum() - perim * 0.4 * 0.2 / FIL_AREA) < 1e-9
    assert (g["e"] == 0.0).sum() == 1                                         # 輪と輪の間の移動 1 本
    assert abs(P.gcode_extrusion_volume(g) - perim * 0.4 * 0.2) < 1e-9        # 体積 = 周長 × 線幅 × 層厚
    L = perim + float(np.hypot(g["x1"][g["e"] == 0] - g["x0"][g["e"] == 0], g["y1"][g["e"] == 0] - g["y0"][g["e"] == 0])[0])
    assert abs(P.gcode_time_estimate(g) - L / (1800.0 / 60.0)) < 1e-9
    path = P.gcode_write(g, str(tmp_path / "a.gcode"))
    t = P.gcode_read(path)
    assert abs(t["e"].sum() - g["e"].sum()) < 1e-6 and np.unique(t["layer"]).tolist() == [3]
    assert int((t["e"] > 0).sum()) == int((g["e"] > 0).sum())
    with pytest.raises(ValueError, match="segment table lacks columns"):
        P.gcode_extrusion_volume(c)


def test_gcode_read_honours_relative_modes_units_and_refuses_arcs_and_gaps(tmp_path):
    p = tmp_path / "rel.gcode"
    p.write_text("\n".join([
        "G21", "G91", "M83", "G0 X0 Y0 Z0.2 F3000",
        "G1 X10 E1.0 F1200",             # 相対: x 0 → 10、E +1
        "G1 Y5 E0.5",                    # y 0 → 5、E +0.5
        "G1 X-10 E-0.3",                 # リトラクト: 押し出しに数えない
        "G92 E0",
        "G1 Z0.2 E0",                    # 層が上がる(Z 増加 + 次の押し出し)
        "G1 X10 E2.0",
    ]) + "\n", encoding="utf-8")
    t = P.gcode_read(str(p))
    assert abs(t["e"].sum() - 3.5) < 1e-9
    assert t["x1"][0] == 10.0 and t["y1"][1] == 5.0 and t["x1"][2] == 0.0
    assert t["layer"].max() == 1 and t["layer"][-1] == 1                    # Z の増加で 2 層目
    p2 = tmp_path / "inch.gcode"
    p2.write_text("G20\nG90\nG0 X0 Y0 Z0 F100\nG1 X1 E1\n", encoding="utf-8")
    t2 = P.gcode_read(str(p2))
    assert abs(t2["x1"][-1] - 25.4) < 1e-9                                  # インチ → mm
    p3 = tmp_path / "arc.gcode"
    p3.write_text("G90\nG0 X0 Y0 Z0 F100\nG2 X1 Y1 I0.5 J0.5 E1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="arc moves"):
        P.gcode_read(str(p3))
    p4 = tmp_path / "gap.gcode"
    p4.write_text("G90\nG1 X10 E1 F100\n", encoding="utf-8")                # Y, Z が一度も無いまま押し出す
    with pytest.raises(ValueError, match="dialect gap"):
        P.gcode_read(str(p4))
    with pytest.raises(ValueError, match="file not found"):
        P.gcode_read(str(tmp_path / "nope.gcode"))


def test_layer_image_paints_the_line_width_and_the_defect_map_is_signed():
    mesh = box_with_hole()
    g = P.contours_to_gcode(P.mesh_slice_contours(mesh, 3.0), z=3.0, layer=3)
    img = P.gcode_layer_image(g, 3, px_per_mm=10.0, line_width_mm=0.4, bounds=(-2, -2, 22, 12))
    assert img.shape == (140, 240) and set(np.unique(img)) <= {0.0, 1.0}
    perim = 2 * (20 + 10) + 2 * (4 + 4)
    assert 0.7 * perim * 0.4 * 100 < img.sum() < 1.3 * perim * 0.4 * 100     # 面積 ≈ 周長 × 線幅(角で重なる)
    obs = img.copy()
    obs[20:30, 40:80] = 0.0                                                   # 欠け
    obs[5:9, 100:140] = 1.0                                                   # はみ出し
    d0 = P.print_layer_defect_map(obs, img, tolerance_px=0)
    assert d0.shape == img.shape and set(np.unique(d0)) <= {-1.0, 0.0, 1.0}
    assert (d0[20:30, 40:80] > 0).sum() == img[20:30, 40:80].sum()            # 欠けは +1(許容 0 なら画素どおり)
    assert (d0[5:9, 100:140] < 0).sum() == 160 - img[5:9, 100:140].sum()      # はみ出しは −1
    d = P.print_layer_defect_map(obs, img, tolerance_px=1)
    assert 0 < (d[20:30, 40:80] > 0).sum() < img[20:30, 40:80].sum()          # 許容 1 px は境界を見逃す(それが目的)
    assert np.array_equal(P.print_layer_defect_map(img, img, tolerance_px=0), np.zeros_like(img))
    with pytest.raises(ValueError, match="layer 9 has no moves"):
        P.gcode_layer_image(g, 9)
    with pytest.raises(ValueError, match="same non-empty 2-D shape"):
        P.print_layer_defect_map(img, img[:-1])


def test_3mf_round_trip_and_unit_scaling(tmp_path):
    V, F = box_with_hole()
    p = P.write_3mf(str(tmp_path / "a.3mf"), (V, F))
    V2, F2 = P.read_3mf(p)
    assert np.allclose(V2, V) and np.array_equal(F2, F)
    # 単位 inch の model を手で書く
    import zipfile
    q = tmp_path / "inch.3mf"
    model = io.open(os.path.join(tmp_path, "a.3mf"), "rb")
    model.close()
    with zipfile.ZipFile(p) as zf:
        xml = zf.read("3D/3dmodel.model").decode("utf-8").replace('unit="millimeter"', 'unit="inch"')
    with zipfile.ZipFile(q, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("3D/3dmodel.model", xml)
    V3, _ = P.read_3mf(str(q))
    assert np.allclose(V3, V * 25.4)
    bad = tmp_path / "bad.3mf"
    bad.write_bytes(b"not a zip")
    with pytest.raises(ValueError, match="not a zip"):
        P.read_3mf(str(bad))


# --------------------------------------------------------------------------- #
# 登録面の門                                                                    #
# --------------------------------------------------------------------------- #
def test_the_ledger_lists_every_op_and_nothing_is_missing():
    import opsprintpath

    assert opsprintpath.missing() == []
    assert set(opsprintpath.OPSPRINTPATH) == set(_OPS) == set(P.__all__) - {"MAX_GCODE_SEGMENTS", "MAX_LAYER_PIXELS"}
    assert len(opsprintpath.categories()) == 4


def test_every_op_is_reachable_from_the_public_tier():
    import fullseye as fs
    import opsprintpath

    for name in opsprintpath.OPSPRINTPATH:
        assert hasattr(fs.ledger, name), name


def test_the_typed_catalog_declares_the_family():
    import typed_catalog as tc

    rows = [r for r in tc.catalog() if r[1] == "printpath"]
    assert {r[0] for r in rows} == set(_OPS)
    assert {r[3] for r in rows} == {"table", "text", "measurement", "image2d", "voxel", "mesh"}


def test_the_fuzzer_has_predicates_and_seeds_for_every_sort():
    sys.path.insert(0, str(ROOT / "tools"))
    import chain_fuzz as cf
    import opsprintpath

    gens = cf.make_generators()
    for name, meta in opsprintpath.OPSPRINTPATH.items():
        assert meta["out"] in cf.TYPE_CHECKS, name
        for s in meta["in"]:
            # table / text / mesh は他の op が産む語(種は無く、連鎖の中で到達する)。述語だけを要求する
            assert s in cf.TYPE_CHECKS, (name, s)
            assert s in gens or s in ("table", "text", "mesh"), (name, s)


def test_op_run_works_for_every_op(tmp_path):
    import fullseye as fs

    run = lambda *a, **k: fs.op_run(*a, **k)[0]     # noqa: E731
    mesh = box_with_hole()
    c = run("mesh_slice_contours", mesh, 3.0)
    assert np.unique(c["ring"]).tolist() == [0, 1]
    assert run("mesh_slice_stack", mesh, layer_mm=2.0, px_per_mm=2.0).shape[0] == 4
    g = run("contours_to_gcode", c, 3.0, layer=3)
    assert run("gcode_extrusion_volume", g) > 0 and run("gcode_time_estimate", g) > 0
    assert run("gcode_layer_image", g, 3, px_per_mm=4.0).ndim == 2
    p = run("gcode_write", g, str(tmp_path / "o.gcode"))
    assert run("gcode_read", p)["e"].sum() > 0
    m = run("write_3mf", str(tmp_path / "o.3mf"), mesh)
    assert run("read_3mf", m)[1].shape == mesh[1].shape
    im = run("gcode_layer_image", g, 3, px_per_mm=4.0)
    assert run("print_layer_defect_map", im, im).sum() == 0.0


def test_the_family_guide_exists_and_names_its_ops():
    p = ROOT / "docs" / "ops" / "printpath" / "guides" / "printpath.md"
    assert p.exists()
    md = p.read_text(encoding="utf-8")
    assert "```mermaid" in md and "gcode_read" in md and "mesh_slice_contours" in md and "print_layer_defect_map" in md
    assert os.path.isdir(ROOT / "docs" / "ops" / "printpath")
