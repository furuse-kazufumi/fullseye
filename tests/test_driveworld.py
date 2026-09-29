"""driveworld の門: OBJ 読み(UV → 色)/ 資産の実寸 / 耳切りの面積 / 世界の組み立て / 信号の状態 / カメラの整合 / fail-closed。"""
import io
import os

import numpy as np
import pytest

import driveworld as DW


def _rect_course(L=30.0, w=7.0):
    rect = np.array([[0, 0], [L, 0], [L, w], [0, w]], float)
    return {"kind": "road", "polygon": rect, "width": w, "entry": (0, w / 2, 0.0), "exit": (L, w / 2, 0.0)}


# ─────────────────────────────── OBJ ───────────────────────────────────────

def test_read_obj_colored_uses_uv_centroid_and_fans_quads(tmp_path):
    obj = tmp_path / "t.obj"
    obj.write_text("\n".join([
        "v 0 0 0 1 0 0", "v 1 0 0 1 0 0", "v 1 1 0 1 0 0", "v 0 1 0 1 0 0",
        "vt 0.1 0.1", "vt 0.9 0.1", "vt 0.9 0.9", "vt 0.1 0.9",
        "f 1/1 2/2 3/3 4/4",                      # 四角形 → 扇で 2 三角形
    ]), encoding="utf-8")
    tex = np.zeros((2, 2, 3))
    tex[1, 0] = (0, 1, 0)      # 左下(v 小 → 行 1)
    tex[0, 1] = (0, 0, 1)      # 右上
    tex[1, 1] = (1, 1, 0)      # 右下
    tex[0, 0] = (1, 0, 1)      # 左上
    V, F, C = DW.read_obj_colored(obj, tex)
    assert V.shape == (4, 3) and F.shape == (2, 3)
    # 三角形 (1,2,3) の UV 重心 = (0.63, 0.37) → 右下 / (1,3,4) の重心 = (0.37, 0.63) → 左上
    assert np.allclose(C[0], (1, 1, 0)) and np.allclose(C[1], (1, 0, 1))
    V2, F2, C2 = DW.read_obj_colored(obj, None)     # テクスチャ無し → 頂点色
    assert np.allclose(C2, (1, 0, 0))


def test_read_obj_colored_fails_closed(tmp_path):
    bad = tmp_path / "b.obj"
    bad.write_text("v 0 0 0\nv 1 0 0\nf 1 2 9\n", encoding="utf-8")
    with pytest.raises(ValueError):
        DW.read_obj_colored(bad, None)
    (tmp_path / "e.obj").write_text("# nothing\n", encoding="utf-8")
    with pytest.raises(ValueError):
        DW.read_obj_colored(tmp_path / "e.obj", None)


# ─────────────────────────────── 資産 ───────────────────────────────────────

def test_assets_have_real_dimensions_and_ground_contact():
    for name, (_kit, _f, dims, label) in DW.ASSETS.items():
        m = DW.load_asset(name)
        ext = m["V"].max(0) - m["V"].min(0)
        assert np.allclose(ext, dims, atol=1e-9), name
        assert abs(m["V"][:, 2].min()) < 1e-12, name           # 底面が z = 0
        assert np.allclose(m["V"][:, :2].mean(0), 0.0, atol=ext[:2].max() * 0.5)
        assert m["label"] == label and len(m["color"]) == len(m["F"])
        assert (m["color"] >= 0).all() and (m["color"] <= 1).all()
    assert len(np.unique(DW.load_asset("sedan")["color"].round(2), axis=0)) > 20   # 色は 1 色でない


def test_load_asset_fails_closed():
    with pytest.raises(ValueError):
        DW.load_asset("spaceship")
    with pytest.raises(ValueError):
        DW.load_asset("sedan", dims=(4.5, -1.0, 1.4))


def test_place_mesh_is_rigid():
    m = DW.load_asset("sedan")
    V2 = DW.place_mesh(m["V"], 3.0, -2.0, 0.7, z=0.5)
    d0 = np.linalg.norm(m["V"][::50, None] - m["V"][None, ::50], axis=-1)
    d1 = np.linalg.norm(V2[::50, None] - V2[None, ::50], axis=-1)
    assert np.allclose(d0, d1, atol=1e-9)
    assert abs(V2[:, 2].min() - 0.5) < 1e-12


# ─────────────────────────────── 耳切り ─────────────────────────────────────

def _shoelace(P):
    x, y = P[:, 0], P[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def _tri_area(P, T):
    a, b, c = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    return 0.5 * np.abs((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])).sum()


def test_ear_clipping_area_matches_shoelace_on_nonconvex_polygons():
    Z = np.array([[0, 0], [12, 0], [12, 3.5], [3.5, 3.5], [3.5, 12], [0, 12]], float)   # L 字(凹)
    T = DW.polygon_triangulate(Z)
    assert len(T) == len(Z) - 2 and abs(_tri_area(Z, T) - _shoelace(Z)) < 1e-9
    rng = np.random.default_rng(0)
    for _ in range(20):                                    # 乱数の星形(凹が多い)
        n = int(rng.integers(6, 30))
        ang = np.sort(rng.uniform(0, 2 * np.pi, n))
        r = rng.uniform(1.0, 3.0, n)
        P = np.column_stack([r * np.cos(ang), r * np.sin(ang)])
        T = DW.polygon_triangulate(P)
        assert len(T) == n - 2 and abs(_tri_area(P, T) - _shoelace(P)) < 1e-9
    T2 = DW.polygon_triangulate(Z[::-1])                   # 時計回りでも同じ面積(索引は渡した順の点を指す)
    assert abs(_tri_area(Z[::-1], T2) - _shoelace(Z)) < 1e-9
    with pytest.raises(ValueError):
        DW.polygon_triangulate(Z[:2])


# ─────────────────────────────── 世界 ───────────────────────────────────────

def test_world_build_carries_labels_and_props():
    course = _rect_course()
    course["signal_poses"] = [(24.0, -1.0, np.pi / 2)]
    course["stop_lines"] = [((22.0, 0.0), (22.0, 7.0))]
    w = DW.world_build(course, props=[("sedan", 8, 2, 0.1), ("cone", 12, 0.5, 0.0)])
    assert len(w["F"]) == len(w["face_label"]) == len(w["face_color"])
    assert w["F"].max() < len(w["V"])
    present = set(np.unique(w["face_label"]).tolist())
    assert {0, 1, 2, 3, 5, 9} <= present
    names = [o["name"] for o in w["objects"]]
    assert "ground" in names and "sedan" in names and "traffic_light" in names and "stop_line" in names
    sedan = [o for o in w["objects"] if o["name"] == "sedan"][0]
    f0, f1 = sedan["faces"]
    assert (w["face_label"][f0:f1] == 2).all() and sedan["pose"] == (8.0, 2.0, 0.1)
    # 縁石は矩形の 4 辺(継ぎ目なし)を 0.5 m の小片に割った帯 = (60 + 14 + 60 + 14) 片 × 10 三角形
    kerb = [o for o in w["objects"] if o["name"].startswith("kerb")][0]
    assert kerb["faces"][1] - kerb["faces"][0] == (60 + 14 + 60 + 14) * 10


def test_signal_state_changes_only_colour():
    course = _rect_course()
    course["signal_poses"] = [(24.0, -1.0, np.pi / 2)]
    w = DW.world_build(course)
    i = [k for k, o in enumerate(w["objects"]) if o["name"] == "traffic_light"][0]
    V0 = w["V"].copy()
    red = w["face_color"][slice(*w["objects"][i]["lamp_faces"]["red"])].copy()
    DW.set_signal_state(w, i, "green")
    assert np.array_equal(V0, w["V"]) and w["objects"][i]["state"] == "green"
    grn = w["face_color"][slice(*w["objects"][i]["lamp_faces"]["green"])]
    assert grn[0, 1] > 0.9 and w["face_color"][slice(*w["objects"][i]["lamp_faces"]["red"])][0, 0] < 0.2
    assert red[0, 0] > 0.9
    with pytest.raises(ValueError):
        DW.set_signal_state(w, i, "blue")
    with pytest.raises(ValueError):
        DW.set_signal_state(w, 0, "red")                   # ground は信号機でない


def test_camera_labels_depth_and_projection_agree():
    course = _rect_course()
    w = DW.world_build(course, props=[("sedan", 10, 3.5, 0.0)])
    K = DW.camera_intrinsics(60, 320, 200)
    pose = DW.camera_pose((-2, 3.5, 1.4), (12, 3.5, 0.8))
    im = DW.world_camera(w, pose, K, 320, 200)
    hit = im["label"] >= 0
    assert hit.any() and np.isfinite(im["depth"][hit]).all() and np.isinf(im["depth"][~hit]).all()
    assert (im["label"][hit] == w["face_label"][im["face"][hit]]).all()
    assert 2 in np.unique(im["label"]) and 0 in np.unique(im["label"])
    # 車の頂点を投影した画素は、車か(手前の何かに隠れていなければ)背景でない
    sedan = [o for o in w["objects"] if o["name"] == "sedan"][0]
    Vs = w["V"][slice(*sedan["verts"])]
    col, row, depth = DW.world_project_points(Vs, pose, K)
    inside = (depth > 0) & (col >= 0) & (col < 320) & (row >= 0) & (row < 200)
    c = np.rint(col[inside]).astype(int)
    r = np.rint(row[inside]).astype(int)
    frac = np.mean(im["label"][r, c] == 2)
    assert frac > 0.8, frac                               # 縁の画素は隣に落ちるので 100 % ではない
    over = DW.overlay_points(im["color"], Vs, pose, K, (1.0, 0.0, 1.0), depth_test=im["depth"])
    assert over.shape == im["color"].shape and (over != im["color"]).any()


def test_world_add_fails_closed():
    w = DW.world_build(_rect_course())
    with pytest.raises(ValueError):
        DW.world_add(w, np.zeros((3, 3)), np.array([[0, 1, 5]]), 0, (1, 1, 1))
    with pytest.raises(ValueError):
        DW.world_add(w, np.array([[0, 0, np.nan], [1, 0, 0], [0, 1, 0]]), np.array([[0, 1, 2]]), 0, (1, 1, 1))


def test_world_move_is_rigid_and_matches_a_fresh_placement():
    """動かした頂点 = 最初からその姿勢で置いた頂点(1e-9)。往復で元に戻る。資産でない物体は ValueError。"""
    w = DW.world_build(_rect_course(), props=[("taxi", 3.0, 1.0, 0.3)])
    i = [k for k, o in enumerate(w["objects"]) if o["name"] == "taxi"][0]
    v0, v1 = w["objects"][i]["verts"]
    before = w["V"][v0:v1].copy()
    DW.world_move(w, i, 8.0, -2.0, 2.0)
    fresh = DW.place_mesh(DW.load_asset("taxi")["V"], 8.0, -2.0, 2.0)
    assert np.allclose(w["V"][v0:v1], fresh, atol=1e-9)
    assert w["objects"][i]["pose"] == (8.0, -2.0, 2.0)
    DW.world_move(w, i, 3.0, 1.0, 0.3)
    assert np.allclose(w["V"][v0:v1], before, atol=1e-9)
    ground = [k for k, o in enumerate(w["objects"]) if o["label"] == 0][0]
    with pytest.raises(ValueError):
        DW.world_move(w, ground, 0.0, 0.0, 0.0)


def test_car_assets_face_plus_x_at_yaw_zero():
    """車キットの資産は yaw 0 で +x が前(ユーザー指摘 2026-09-29 の回帰): パトカーの赤いテールランプの面は後ろ(x < 0)、
    セダンの頂点は生の z-up 変換を x・y で反転したもの(180° 回した規約が外れたら落ちる)。"""
    m = DW.load_asset("police")
    C = m["color"]
    red = (C[:, 0] > 0.6) & (C[:, 1] < 0.35) & (C[:, 2] < 0.35)
    assert red.any()
    assert m["V"][m["F"][red]].mean(axis=(0, 1))[0] < -0.1 * m["dims"][0]      # 実測 −0.70 m(車長 4.8 m、赤い灯は中心より後ろ)
    kd = DW.asset_dir() / DW._KIT_DIR["cars"]
    V, F, _ = DW.read_obj_colored(kd / "sedan.obj", DW._read_png_rgb(kd / DW._COLORMAP))
    V = DW._yup_to_zup(V)
    lo, hi = V.min(axis=0), V.max(axis=0)
    raw = (V - (lo + hi) / 2.0) / np.where(hi - lo > 1e-9, hi - lo, 1.0) * np.asarray(DW.ASSETS["sedan"][2])
    s = DW.load_asset("sedan")["V"]
    assert np.allclose(s[:, :2], -raw[:, :2], atol=1e-9) and np.allclose(s[:, 2] - s[:, 2].min(), raw[:, 2] - raw[:, 2].min())
