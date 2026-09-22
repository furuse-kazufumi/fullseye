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
import fourierdesc as FD  # noqa: E402

_OPS = ["gcode_read", "gcode_write", "gcode_extrusion_volume", "gcode_time_estimate", "gcode_layer_image",
        "mesh_slice_contours", "mesh_slice_stack", "contours_to_gcode", "read_3mf", "write_3mf", "print_layer_defect_map",
        "stipple_points_from_image", "stipple_energy", "stroke_tour_closed", "mst_length", "stroke_resample_closed", "stroke_tone_error"]
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
    assert len(opsprintpath.categories()) == 5   # stroke を足した


def test_every_op_is_reachable_from_the_public_tier():
    import fullseye as fs
    import opsprintpath

    for name in opsprintpath.OPSPRINTPATH:
        assert hasattr(fs.ledger, name), name


def test_the_typed_catalog_declares_the_family():
    import typed_catalog as tc

    rows = [r for r in tc.catalog() if r[1] == "printpath"]
    assert {r[0] for r in rows} == set(_OPS)
    assert {r[3] for r in rows} == {"table", "text", "measurement",
                                    "image2d", "voxel", "mesh", "pairs"}


def test_the_fuzzer_has_predicates_and_seeds_for_every_sort():
    sys.path.insert(0, str(ROOT / "tools"))
    import chain_fuzz as cf
    import opsprintpath

    gens = cf.make_generators()
    for name, meta in opsprintpath.OPSPRINTPATH.items():
        assert meta["out"] in cf.TYPE_CHECKS, name
        for s in meta["in"]:
            # table / text / mesh / pairs は他の op が産む語で、種は無い(連鎖の中で
            # 到達する —— pairs はこの族では stipple_points_from_image が産む)。述語だけを要求する
            assert s in cf.TYPE_CHECKS, (name, s)
            assert s in gens or s in ("table", "text", "mesh", "pairs"), (name, s)


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

# --------------------------------------------------------------------------- #
# 濃淡 → 1 本の閉じた線(2026-09-22)                                          #
#   真値は「使った式」ではない: Lloyd の単調減少 / 置換であることの厳密検査 /   #
#   MST 下界との比 / 濃淡の再現そのもの(対照群つき)。                         #
# --------------------------------------------------------------------------- #
def _ramp(h=64, w=64):
    """左が白、右が黒。**局所密度 ∝ 暗さ**を測るための場。"""
    return np.tile(np.linspace(1.0, 0.0, w), (h, 1))


def _blob(h=96, w=96):
    yy, xx = np.mgrid[0:h, 0:w]
    img = (0.85
           - 0.55 * np.exp(-(((yy - 0.42 * h) / (0.23 * h)) ** 2
                             + ((xx - 0.52 * w) / (0.29 * w)) ** 2))
           - 0.25 * (xx / w))
    return np.clip(img, 0.0, 1.0)


def _tour_length(q):
    return float(np.hypot(np.diff(q[:, 0], append=q[0, 0]),
                          np.diff(q[:, 1], append=q[0, 1])).sum())


def _is_permutation(a, b):
    ka = np.lexsort((a[:, 1], a[:, 0]))
    kb = np.lexsort((b[:, 1], b[:, 0]))
    return np.allclose(a[ka], b[kb])


def _nn_distances(p):
    d = np.hypot(p[:, 0, None] - p[None, :, 0], p[:, 1, None] - p[None, :, 1])
    np.fill_diagonal(d, np.inf)
    return d.min(axis=1)


def test_the_point_density_follows_the_darkness():
    """★濃淡を読めていること。ランプの 8 帯で点の数と暗さの相関を測る。"""
    ramp = _ramp()
    p = P.stipple_points_from_image(ramp, 400, iterations=25, seed=1)
    assert p.shape == (400, 2)
    assert p[:, 0].min() >= 0.0 and p[:, 0].max() <= ramp.shape[0]
    assert p[:, 1].min() >= 0.0 and p[:, 1].max() <= ramp.shape[1]
    edges = np.linspace(0, ramp.shape[1], 9)
    count, _ = np.histogram(p[:, 1], bins=edges)
    dark = [float((1.0 - ramp[:, int(edges[i]):int(edges[i + 1])]).mean())
            for i in range(8)]
    r = float(np.corrcoef(count, dark)[0, 1])
    assert r > 0.95, (r, count.tolist())            # 実測 0.995
    assert count[-1] > 5 * count[0]                 # 実測 94 vs 10


def test_a_flat_image_gives_an_even_spread_which_is_the_control():
    """★対照群: 密度が一定なら重心ボロノイは**均等**になる。"""
    flat = np.full((64, 64), 0.5)
    q = P.stipple_points_from_image(flat, 200, iterations=25, seed=2)
    cv_flat = float(_nn_distances(q).std() / _nn_distances(q).mean())
    p = P.stipple_points_from_image(_ramp(), 200, iterations=25, seed=2)
    cv_ramp = float(_nn_distances(p).std() / _nn_distances(p).mean())
    assert cv_flat < 0.25, cv_flat                  # 実測 0.13
    assert cv_ramp > 1.5 * cv_flat, (cv_ramp, cv_flat)


def test_the_lloyd_energy_never_goes_up():
    """★反復を増やすとエネルギーは単調に下がる(厳密に確かめられる性質)。"""
    ramp = _ramp()
    e = [P.stipple_energy(ramp, P.stipple_points_from_image(ramp, 300,
                                                            iterations=k, seed=3))
         for k in (0, 1, 2, 4, 8, 16)]
    for i in range(len(e) - 1):
        assert e[i + 1] <= e[i] * (1.0 + 1e-9), (i, e)
    assert e[-1] < 0.6 * e[0], e                    # 実測 4654 / 8760


def test_the_tour_is_a_closed_permutation_and_never_beats_the_mst():
    """★巡回路の質は**下界との比**で言う(黄金ファイルを使わない)。"""
    rng = np.random.default_rng(0)
    n, side = 300, 100.0
    p = rng.uniform(0.0, side, (n, 2))
    mst = P.mst_length(p)
    bhh = 0.7124 * np.sqrt(n * side * side)
    prev = None
    for rounds in (0, 1, 2, 4, 8):
        t = P.stroke_tour_closed(p, two_opt_rounds=rounds)
        assert t.shape == (n, 2)
        assert _is_permutation(p, t)                # 各点をちょうど 1 回
        L = _tour_length(t)
        assert L >= mst - 1e-9, (L, mst)            # 閉路は MST より短くなれない
        if prev is not None:
            assert L <= prev + 1e-9, (rounds, L, prev)   # 2-opt は単調
        prev = L
    assert prev / mst < 1.35, prev / mst            # 実測 1.228
    assert 0.9 < prev / bhh < 1.3, prev / bhh       # 実測 1.144
    # 対照群: 座標順に繋ぐだけでは 8 倍以上長くなる
    naive = P.stroke_tour_closed(p, start="sorted", two_opt_rounds=0)
    assert _tour_length(naive) > 5.0 * prev, _tour_length(naive) / prev


def test_resampling_is_uniform_in_arc_length_and_refuses_to_shorten():
    rng = np.random.default_rng(0)
    p = rng.uniform(0.0, 100.0, (300, 2))
    t = P.stroke_tour_closed(p, two_opt_rounds=8)
    long = _tour_length(t)
    rs = P.stroke_resample_closed(t, 1024)
    assert rs.shape == (1024, 2)
    assert 0.95 < _tour_length(rs) / long < 1.0     # 実測 0.969(角を切る)
    # 細かくすれば長さは戻る
    assert _tour_length(P.stroke_resample_closed(t, 4000)) / long > 0.98
    # ★頂点より少ない標本は既定で拒否(長さが縮んで濃淡の再現が壊れる)
    with pytest.raises(ValueError, match="stroke_resample_closed.*fewer than"):
        P.stroke_resample_closed(t, 50)
    coarse = P.stroke_resample_closed(t, 50, allow_shortening=True)
    assert _tour_length(coarse) < 0.7 * long        # 実測 0.577
    with pytest.raises(ValueError, match="stroke_resample_closed.*n_points"):
        P.stroke_resample_closed(t, 2)


def test_the_tone_error_separates_a_real_stroke_from_a_random_one():
    """★★これが本当の目的関数。同じ本数のランダムな線を対照群に置く。"""
    img = _blob()
    pts = P.stipple_points_from_image(img, 900, iterations=25, seed=5)
    tour = P.stroke_tour_closed(pts, two_opt_rounds=6)
    good = P.stroke_tone_error(img, tour, pen_width=1.0, blur_sigma=4.0)
    rng = np.random.default_rng(7)
    rand = np.stack([rng.uniform(0, img.shape[0], 900),
                     rng.uniform(0, img.shape[1], 900)], axis=1)
    ctrl = P.stroke_tone_error(img, P.stroke_tour_closed(rand, two_opt_rounds=6),
                               pen_width=1.0, blur_sigma=4.0)
    assert good["corr"] > 0.85, good["corr"]        # 実測 0.922
    assert ctrl["corr"] < 0.3, ctrl["corr"]         # 実測 -0.174
    assert good["rms"] < 0.7 * ctrl["rms"], (good["rms"], ctrl["rms"])
    # インクの量は目標の暗さに釣り合う(桁で外れない)
    assert 0.6 < good["ink_fraction"] / good["target_darkness"] < 1.4, good
    assert good["length_px"] > 0.0
    for k in ("rms", "max_abs", "bias", "corr", "ink_fraction",
              "target_darkness", "length_px"):
        assert k in good and np.isfinite(good[k]), k


def test_the_stroke_feeds_the_fourier_ops_because_it_is_closed():
    """★噛み合わせ: 巡回路は閉じているので、そのままフーリエに載る。"""
    img = _blob(64, 64)
    pts = P.stipple_points_from_image(img, 200, iterations=15, seed=11)
    tour = P.stroke_tour_closed(pts, two_opt_rounds=4)
    closed = P.stroke_resample_closed(tour, 512)
    # ★完全な係数列で呼ぶ(打ち切ると尾のエネルギーが分からず予言が下界になる)。
    #   parametrisation は "index" —— stroke_resample_closed が**すでに弧長で**
    #   打ち直しているので、ここで "arclength" を選ぶと op が内部でもう 1 度
    #   打ち直して**別の輪郭の係数**になる(弧長の打ち直しは冪等でない)。
    sp = FD.contour_fourier_complex(closed, parametrisation="index")
    tab = FD.contour_fourier_truncation_energy(sp)
    # 予言した誤差が実測と一致する(パーセバル)
    k = np.round(sp[:, 0]).astype(int)
    c = sp[:, 1] + 1j * sp[:, 2]
    z = closed[:, 1] + 1j * closed[:, 0]
    t = np.arange(z.size) / z.size
    orders = list(tab["order"])
    for K in (4, 16, 64):
        sel = np.abs(k) <= K
        rec = np.zeros(z.size, dtype=complex)
        for kj, cj in zip(k[sel], c[sel]):
            rec += cj * np.exp(2j * np.pi * kj * t)
        measured = float(np.sqrt((np.abs(z - rec) ** 2).mean()))
        assert tab["rms_error"][orders.index(K)] == pytest.approx(measured, rel=1e-9)
    # 振り子の筆先は輪郭の点そのもの
    chain = FD.contour_epicycle_chain(sp, 0.0)
    assert chain.shape[1] == 2 and chain.shape[0] == sp.shape[0] + 1


def test_the_stipple_op_refuses_what_it_cannot_answer():
    img = _ramp()
    with pytest.raises(ValueError, match="stipple_points_from_image.*metric"):
        P.stipple_points_from_image(img, 50, metric="manhattan")
    with pytest.raises(ValueError, match="stipple_points_from_image.*n_points"):
        P.stipple_points_from_image(img, 2)
    with pytest.raises(ValueError, match="stipple_points_from_image.*floor"):
        P.stipple_points_from_image(img, 50, floor=0.0)
    with pytest.raises(ValueError, match="stipple_points_from_image.*gamma"):
        P.stipple_points_from_image(img, 50, gamma=0.0)
    with pytest.raises(ValueError, match="stipple_points_from_image.*more points"):
        P.stipple_points_from_image(np.zeros((5, 5)), 100)
    with pytest.raises(ValueError, match="stipple_points_from_image.*at least 4x4"):
        P.stipple_points_from_image(np.zeros((3, 3)), 5)
    with pytest.raises(ValueError, match="stipple_points_from_image.*non-finite"):
        bad = img.copy()
        bad[0, 0] = np.inf
        P.stipple_points_from_image(bad, 50)
    p = P.stipple_points_from_image(img, 40, iterations=3, seed=0)
    with pytest.raises(ValueError, match="stroke_tour_closed.*start"):
        P.stroke_tour_closed(p, start="random")
    with pytest.raises(ValueError, match="stroke_tour_closed.*given"):
        P.stroke_tour_closed(p, start="given")
    with pytest.raises(ValueError, match="stroke_tour_closed.*permutation"):
        P.stroke_tour_closed(p, start="given", order=list(range(len(p) - 1)))
    with pytest.raises(ValueError, match="stroke_tone_error.*blur_sigma"):
        P.stroke_tone_error(img, p, blur_sigma=0.0)
    with pytest.raises(ValueError, match="stroke_tone_error.*pen_width"):
        P.stroke_tone_error(img, p, pen_width=0.0)


def test_the_pen_width_is_a_continuous_knob_and_the_ink_follows_a_closed_form():
    """★★回帰 + 閉形式。

    以前は線を整数画素の円板で塗っていたので、ペン幅 0.5 / 1.0 / 1.5 px が
    **同じ絵**になり(インク率 0.1900 で一致)、2.0 で 0.4853 へ跳ねていた。
    ペン幅が階段だと「目標の濃さに合うペン幅」を解けない。被覆率で塗るよう直した。

    細い線が重ならないあいだは ``インク率 ≈ 線長 × ペン幅 / 面積`` が成り立つ。
    重なり始めると合併は和より小さくなるので、**予言は上側にずれる** ——
    そのずれ自体が重なりの量である。
    """
    img = _blob(96, 96)
    pts = P.stipple_points_from_image(img, 700, iterations=20, seed=17)
    tour = P.stroke_tour_closed(pts, two_opt_rounds=5)
    base = P.stroke_tone_error(img, tour, pen_width=1.0, blur_sigma=5.0)
    area = float(img.shape[0] * img.shape[1])
    length = base["length_px"]

    inks = [P.stroke_tone_error(img, tour, pen_width=w, blur_sigma=5.0)["ink_fraction"]
            for w in (0.25, 0.5, 0.75, 1.0)]
    # 連続に増える(階段ではない)
    for i in range(len(inks) - 1):
        assert inks[i + 1] > inks[i] * 1.1, inks
    # 細いうちは閉形式とよく合う
    predicted = 0.5 * length / area
    assert inks[1] == pytest.approx(predicted, rel=0.15), (inks[1], predicted)
    # 太くすると重なるので、実測は予言より**小さく**なる(合併 < 和)
    thick = P.stroke_tone_error(img, tour, pen_width=4.0, blur_sigma=5.0)
    assert thick["ink_fraction"] < 4.0 * length / area

    # ★目標の濃さに合うペン幅を閉形式で解くと、偏りが桁で縮む
    solved = base["target_darkness"] * area / length
    tuned = P.stroke_tone_error(img, tour, pen_width=solved, blur_sigma=5.0)
    assert abs(tuned["bias"]) < 0.5 * abs(base["bias"]), (tuned["bias"], base["bias"])


def test_the_stipple_is_unchanged_by_the_kd_tree_and_does_not_build_a_distance_matrix():
    """★★回帰 + 速さ。総当たりの距離行列を KD 木に替えても**答えは 1 ビットも変わらない**。

    以前は Lloyd の各反復で ``(画素 x 点)`` の距離行列をまるごと作っていた。
    202x300 の絵に 9,000 点だと 60,600 x 9,000 = 5.5 億要素(4.4 GB 相当)を 18 回
    組み直すことになり、手元で **101 秒**、共有ランナーでは PoC の実行門(1 本 600 秒)
    に迫っていた。KD 木は**厳密に同じ最近傍**を返すので、種を固定すれば結果は同一。

    実測: 101.4 秒 -> 0.4 秒(250 倍)、``stipple_energy`` も 0.02 秒。
    ここでは小さい絵で**総当たりを手で回して突き合わせ**、厳密一致を固定する。
    """
    h, w, n, it = 40, 52, 300, 10
    yy, xx = np.mgrid[0:h, 0:w]
    img = np.clip(0.9 - 0.7 * np.exp(-(((yy - 16) / 10.) ** 2 + ((xx - 26) / 14.) ** 2))
                  - 0.2 * (xx / w), 0, 1)
    got = P.stipple_points_from_image(img, n, iterations=it, gamma=1.6, seed=1)

    lo, hi = float(img.min()), float(img.max())
    weight = np.maximum(((hi - img) / (hi - lo)) ** 1.6, 0.02)
    rng = np.random.default_rng(1)
    flat = weight.ravel() / weight.sum()
    idx = rng.choice(flat.size, size=n, replace=True, p=flat)
    pts = np.stack([(idx // w).astype(float) + rng.random(n),
                    (idx % w).astype(float) + rng.random(n)], axis=1)
    rr, cc = np.mgrid[0:h, 0:w]
    rr = rr.astype(float).ravel()
    cc = cc.astype(float).ravel()
    wf = weight.ravel()
    for _ in range(it):
        d = (rr[:, None] - pts[None, :, 0]) ** 2 + (cc[:, None] - pts[None, :, 1]) ** 2
        o = np.argmin(d, axis=1)
        nr = np.bincount(o, weights=wf * rr, minlength=n)
        nc = np.bincount(o, weights=wf * cc, minlength=n)
        de = np.bincount(o, weights=wf, minlength=n)
        m = de > 0
        pts[m, 0] = nr[m] / de[m]
        pts[m, 1] = nc[m] / de[m]

    assert np.array_equal(got, pts), float(np.abs(got - pts).max())

    # エネルギーも同じ式の別経路なので、総当たりと一致する
    dm = (rr[:, None] - got[None, :, 0]) ** 2 + (cc[:, None] - got[None, :, 1]) ** 2
    assert P.stipple_energy(img, got, gamma=1.6) == pytest.approx(
        float((wf * dm.min(axis=1)).sum()), rel=1e-12)
