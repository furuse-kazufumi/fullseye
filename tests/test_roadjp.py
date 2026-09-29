"""roadjp の門: 公表寸法を頂点から測る / 灯の色順 / 法線の向き / 標識画像の色の面積比 / 板の面色 = 区画平均 / 状態切替 / fail-closed。

実行: PYTHONPATH="C:/dev/projects/imgevolve_wt_conn5" py -3.11 -m pytest test_roadjp.py(driveworld・annotate は worktree から)。"""
import math
import os
import sys

import numpy as np
import pytest

import driveworld as DW  # noqa: E402
import roadjp as R  # noqa: E402

SQ3 = math.sqrt(3.0)
_ARIAL = r"C:\Windows\Fonts\arial.ttf"


def _normals(V, F):
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    n = np.cross(b - a, c - a)
    return n / np.linalg.norm(n, axis=1, keepdims=True)


def _near(img, color, tol=0.12):
    """色 color に近い画素(alpha > 0.5 の中で)の割合。"""
    a = img[..., 3] > 0.5
    d = np.abs(img[..., :3] - np.asarray(color)).max(axis=-1)
    return float(((d < tol) & a).sum() / a.sum())


# ─────────────────────────────── 標識: 寸法・画像 ───────────────────────────────

def test_sign_kinds_and_published_params():
    assert len(R.SIGN_KINDS) == 10 and len(set(R.SIGN_KINDS)) == 10
    for k in R.SIGN_KINDS:
        p = R.sign_params(k)
        assert p["mount_height"] == 1.8 and p["width"] > 0 and p["height"] > 0
        assert p["shape"] in ("circle", "triangle_down", "diamond", "pentagon", "rect")
    assert R.sign_params("speed_limit")["width"] == 0.6 == R.sign_params("no_entry")["height"]      # 円 直径 600 mm
    t = R.sign_params("stop")
    assert t["width"] == 0.6 and abs(t["height"] - 0.6 * SQ3 / 2) < 1e-12                          # 逆三角形 一辺 600 mm
    d = R.sign_params("caution_crossing")
    assert abs(d["width"] - 0.45 * math.sqrt(2)) < 1e-12 and d["width"] == d["height"]              # 菱形 一辺 450 mm
    t8 = R.sign_params("stop", side=0.8)                                                           # 一時停止 800 mm の記述
    assert t8["width"] == 0.8 and abs(t8["height"] - 0.8 * SQ3 / 2) < 1e-12
    assert R.sign_params("no_parking")["border"] == R.SIGN_COLORS["red"]


def test_sign_image_is_rgba_with_alpha_outside_the_shape():
    for k in R.SIGN_KINDS:
        img = R.sign_image(k)
        assert img.ndim == 3 and img.shape[2] == 4 and img.shape[1] == 128
        assert np.isfinite(img).all() and img.min() >= 0 and img.max() <= 1
        H, W = img.shape[:2]
        assert img[H // 2, W // 2, 3] == 1.0
    circ = R.sign_image("no_entry")
    assert circ[0, 0, 3] == 0.0 and circ[-1, -1, 3] == 0.0 and circ[0, -1, 3] == 0.0             # 円の外 = 透明
    tri = R.sign_image("stop")
    assert abs(tri.shape[0] / tri.shape[1] - SQ3 / 2) < 0.02 and tri[-1, 0, 3] == 0.0             # 逆三角形の下の角は透明
    assert R.sign_image("one_way").shape[:2] == (64, 128)


def test_stop_colour_fractions():
    img = R.sign_image("stop")
    red, white = _near(img, R.SIGN_COLORS["red"]), _near(img, R.SIGN_COLORS["white"], 0.2)
    assert red > 0.5 and white > 0.05, (red, white)


def test_no_entry_has_red_ground_and_white_band():
    img = R.sign_image("no_entry")
    assert _near(img, R.SIGN_COLORS["red"]) > 0.6
    H, W = img.shape[:2]
    row = img[H // 2]
    inside = row[:, 3] > 0.5
    assert inside.sum() > 100
    white = np.abs(row[:, :3] - R.SIGN_COLORS["white"]).max(axis=-1) < 0.1
    assert (white & inside).sum() / inside.sum() > 0.5                    # 中央の行は白の帯
    assert not white[int(np.argmax(inside))] and not white[W - 1 - int(np.argmax(inside[::-1]))]   # 帯の両端の外は赤


def test_caution_signs_are_mostly_yellow_with_black():
    kinds = [k for k in R.SIGN_KINDS if k.startswith("caution_")]
    assert len(kinds) == 3
    for k in kinds:
        img = R.sign_image(k)
        assert _near(img, R.SIGN_COLORS["yellow"]) > 0.5, k
        assert _near(img, R.SIGN_COLORS["black"]) > 0.03, k


@pytest.mark.skipif(not os.path.isfile(_ARIAL), reason="CJK を持たないフォント(arial.ttf)が無い")
def test_missing_glyphs_raise_instead_of_tofu():
    with pytest.raises(ValueError):
        R.sign_image("stop", font_path=_ARIAL)                             # 「止まれ」は Arial に無い
    img = R.sign_image("speed_limit", value=50, font_path=_ARIAL)         # 数字はある
    assert _near(img, R.SIGN_COLORS["blue"]) > 0.02


# ─────────────────────────────── 板メッシュ ───────────────────────────────────

def test_plate_faces_equal_cell_means_and_skip_transparent_cells():
    rng = np.random.default_rng(3)
    H, W, cell = 24, 32, 4
    img = rng.random((H, W, 4))
    img[:8, :, 3] = 0.0                                  # 上 2 行の区画は透明
    img[8:12, :16, 3] = 0.4                              # 平均 0.4 < 0.5 → 出ない
    img[8:12, 16:, 3] = 1.0
    img[12:, :, 3] = 1.0
    m = R.plate_mesh_from_image(img, 0.32, 0.24, cell=cell)
    rows, cols = m["cells"]
    assert (rows, cols) == (6, 8)
    expected = []
    for r in range(rows):
        for c in range(cols):
            blk = img[r * cell:(r + 1) * cell, c * cell:(c + 1) * cell]
            a = blk[..., 3]
            if a.mean() >= 0.5:
                expected.append((blk[..., :3] * a[..., None]).sum((0, 1)) / a.sum())
    assert len(expected) == 8 * 3 + 4                    # 下 3 行 + 行 2 の右半分
    f0, f1 = m["front_faces"]
    assert f1 - f0 == 2 * len(expected) and m["back_faces"] == (f1, 2 * f1)
    C = m["color"][f0:f1:2]
    assert np.abs(C - np.asarray(expected)).max() < 1e-9
    assert np.abs(m["color"][f0 + 1:f1:2] - np.asarray(expected)).max() < 1e-9
    assert np.allclose(m["color"][f1:], (0.55, 0.55, 0.55))
    assert m["V"][:, 2].max() < 0.12 - 0.08 + 1e-12      # 透明な上 2 行(0.08 m)は頂点も残らない
    assert m["V"][:, 1].max() == pytest.approx(0.16) and m["V"][:, 1].min() == pytest.approx(-0.16)


def test_plate_normals_and_thickness():
    img = np.ones((16, 16, 4))
    m = R.plate_mesh_from_image(img, 0.4, 0.4, cell=4, thickness=0.01)
    n = _normals(m["V"], m["F"])
    f0, f1 = m["front_faces"]
    assert f1 - f0 == 32 and len(m["F"]) == 64
    assert np.allclose(n[f0:f1], (-1, 0, 0)) and np.allclose(n[f1:], (1, 0, 0))
    assert m["V"][:, 0].min() == pytest.approx(-0.005) and m["V"][:, 0].max() == pytest.approx(0.005)
    ext = m["V"].max(0) - m["V"].min(0)
    assert np.allclose(ext[1:], (0.4, 0.4)) and np.allclose(m["V"].mean(0)[1:], 0.0)


def test_sign_mesh_measures_published_sizes_from_vertices():
    tol = 2 * 0.6 / 32                                    # 区画 2 つぶん(円・三角の縁の階段)
    for kind, w, h in (("speed_limit", 0.6, 0.6), ("no_entry", 0.6, 0.6), ("stop", 0.6, 0.6 * SQ3 / 2),
                       ("caution_signal", 0.45 * math.sqrt(2), 0.45 * math.sqrt(2)), ("one_way", 0.6, 0.3)):
        m = R.sign_mesh(kind)
        ext = m["V"].max(0) - m["V"].min(0)
        assert abs(ext[1] - w) <= tol and abs(ext[2] - h) <= tol, (kind, ext)
        assert abs(ext[1] - w) < 1e-9 or ext[1] < w                     # 内側にしか外れない
        assert len(m["F"]) > 100 and m["label"] == 4 and m["width"] == w
    n = _normals(*(R.sign_mesh("stop")[k] for k in ("V", "F")))
    f0, f1 = R.sign_mesh("stop")["front_faces"]
    assert np.allclose(n[f0:f1], (-1, 0, 0))


def test_add_sign_mount_height_and_facing_convention():
    w = DW._empty_world()
    i = R.add_sign(w, "stop", 3.0, -2.0, 0.0)
    obj = w["objects"][i]
    assert obj["label"] == 4 and obj["kind"] == "stop" and w["objects"][i - 1]["label"] == 6
    Vb = w["V"][slice(*obj["verts"])]
    assert Vb[:, 2].min() == pytest.approx(1.8, abs=0.02)                                   # 板の下端 1.8 m
    assert Vb[:, 2].max() == pytest.approx(1.8 + 0.6 * SQ3 / 2, abs=0.02)
    assert Vb[:, 1].mean() == pytest.approx(-2.0, abs=1e-6) and Vb[:, 0].max() < 3.0       # 柱の手前(車の側)
    f0 = obj["faces"][0]
    a, b = obj["front_faces"]
    n = _normals(w["V"], w["F"][f0 + a:f0 + b])
    assert len(n) > 100 and np.allclose(n, (-1, 0, 0))
    pole = w["V"][slice(*w["objects"][i - 1]["verts"])]
    assert pole[:, 2].min() == 0.0 and pole[:, 2].max() > Vb[:, 2].max()
    # yaw π → 法線 +x(−x へ進んで来る車に向く)、yaw π/2 → 法線 (0, −1, 0)
    for yaw, nrm in ((math.pi, (1, 0, 0)), (math.pi / 2, (0, -1, 0))):
        w2 = DW._empty_world()
        j = R.add_sign(w2, "speed_limit", 0.0, 0.0, yaw, value=30)
        o = w2["objects"][j]
        g0 = o["faces"][0]
        c, d = o["front_faces"]
        n2 = _normals(w2["V"], w2["F"][g0 + c:g0 + d])
        assert len(n2) > 100 and np.allclose(n2, nrm, atol=1e-9), yaw


# ─────────────────────────────── 信号灯器 ─────────────────────────────────────

def test_signal_head_lens_size_order_and_normals():
    h = R.signal_jp_mesh(state="off")
    assert set(h["lamp_faces"]) == {"green", "yellow", "red"}
    n = _normals(h["V"], h["F"])
    ys = {}
    for name, (f0, f1) in h["lamp_faces"].items():
        assert f1 - f0 == 24
        assert np.allclose(n[f0:f1], (-1, 0, 0))                                          # 表示面は −x
        P = h["V"][h["F"][f0:f1]].reshape(-1, 3)
        assert P[:, 1].max() - P[:, 1].min() == pytest.approx(0.30, abs=1e-9)             # レンズ径 300 mm
        assert P[:, 2].max() - P[:, 2].min() == pytest.approx(0.30, abs=1e-9)
        assert np.allclose(P[:, 0], -0.155)                                                # 前面 (−0.15) の 5 mm 外
        ys[name] = float(P[:, 1].mean())
        assert np.allclose(h["color"][f0:f1], DW._LAMP["off"])
    assert ys["green"] > ys["yellow"] > ys["red"]                                           # +y = 青、−y = 赤
    assert ys["green"] == pytest.approx(0.40) and ys["red"] == pytest.approx(-0.40)
    ext = h["V"].max(0) - h["V"].min(0)
    assert h["width"] == pytest.approx(1.25) and h["height"] == pytest.approx(0.43)
    assert ext[1] == pytest.approx(1.25) and ext[2] == pytest.approx(0.43) and h["V"][:, 2].min() == 0.0
    h25 = R.signal_jp_mesh(lens=0.25, state="green")
    assert h25["width"] == pytest.approx(3 * 0.35 + 0.05)
    g0, g1 = h25["lamp_faces"]["green"]
    assert np.allclose(h25["color"][g0:g1], DW._LAMP["green"])


def test_add_signal_jp_geometry_and_state_toggle():
    w = DW._empty_world()
    i = R.add_signal_jp(w, 10.0, 4.0, 0.0, state="red", arm=2.0, lamp_bottom=5.0)
    head, pole = w["objects"][i], w["objects"][i - 1]
    assert head["name"] == "traffic_light" and head["label"] == 3 and pole["name"] == "signal_pole" and pole["label"] == 3
    Vh = w["V"][slice(*head["verts"])]
    assert Vh[:, 2].min() == pytest.approx(5.0)                                            # 灯器の底 = lamp_bottom
    assert Vh[:, 1].mean() == pytest.approx(4.0 - 2.0, abs=0.05)                            # 車線の上(運転者の右 = −y へ arm)
    assert Vh[:, 0].max() < 10.0 + 0.3                                                       # 柱の x に吊る
    Vp = w["V"][slice(*pole["verts"])]
    assert Vp[:, 2].min() == 0.0 and Vp[:, 2].max() >= 5.7 - 1e-9
    assert Vp[:, 1].min() == pytest.approx(4.0 - 2.0)                                       # アームの先 = 柱から arm
    assert Vp[:, 1].max() == pytest.approx(4.0 + 0.08)
    # lamp_faces は世界の面索引: 面の色が状態に従う
    lf = head["lamp_faces"]
    assert set(lf) == {"green", "yellow", "red"} and all(b - a == 24 for a, b in lf.values())
    for (a, b) in lf.values():
        assert head["faces"][0] <= a < b <= head["faces"][1]
    assert np.allclose(w["face_color"][slice(*lf["red"])], DW._LAMP["red"])
    assert np.allclose(w["face_color"][slice(*lf["green"])], DW._LAMP["off"])
    Pg = w["V"][w["F"][slice(*lf["green"])]].reshape(-1, 3)
    Pr = w["V"][w["F"][slice(*lf["red"])]].reshape(-1, 3)
    assert Pg[:, 1].mean() > Pr[:, 1].mean() and Pg[:, 2].min() == pytest.approx(5.0 + 0.065)
    n = _normals(w["V"], w["F"][slice(*lf["red"])])
    assert np.allclose(n, (-1, 0, 0))
    V0 = w["V"].copy()
    DW.set_signal_state(w, i, "green")
    assert np.array_equal(V0, w["V"]) and head["state"] == "green"
    assert np.allclose(w["face_color"][slice(*lf["green"])], DW._LAMP["green"])
    assert np.allclose(w["face_color"][slice(*lf["red"])], DW._LAMP["off"])
    assert len(w["objects"]) == 2


def test_add_signal_jp_yaw_and_arm_side():
    # yaw π/2: +y へ進んで来る車。運転者の右 = +x。表示面の法線 = (0, −1, 0)
    w = DW._empty_world()
    i = R.add_signal_jp(w, 0.0, 0.0, math.pi / 2, state="yellow", arm=3.0, lamp_bottom=5.6)
    head = w["objects"][i]
    Vh = w["V"][slice(*head["verts"])]
    assert Vh[:, 0].mean() == pytest.approx(3.0, abs=0.05) and Vh[:, 2].min() == pytest.approx(5.6)
    n = _normals(w["V"], w["F"][slice(*head["lamp_faces"]["yellow"])])
    assert len(n) == 24 and np.allclose(n, (0, -1, 0), atol=1e-9)
    Pg = w["V"][w["F"][slice(*head["lamp_faces"]["green"])]].reshape(-1, 3)
    Pr = w["V"][w["F"][slice(*head["lamp_faces"]["red"])]].reshape(-1, 3)
    assert Pg[:, 0].mean() < Pr[:, 0].mean()                    # 運転者(+y を向く)の左 = −x に青
    assert np.allclose(w["face_color"][slice(*head["lamp_faces"]["yellow"])], DW._LAMP["yellow"])
    # arm_side="right": 柱が運転者の右、アームは左(yaw 0 で +y)へ
    w2 = DW._empty_world()
    j = R.add_signal_jp(w2, 0.0, 0.0, 0.0, arm_side="right", arm=2.5)
    Vh2 = w2["V"][slice(*w2["objects"][j]["verts"])]
    assert Vh2[:, 1].mean() == pytest.approx(2.5, abs=0.05)


def test_world_camera_sees_sign_and_signal_labels():
    w = DW._empty_world()
    R.add_sign(w, "stop", 0.0, 2.0, 0.0)
    i = R.add_signal_jp(w, 4.0, 4.0, 0.0, state="red")
    K = DW.camera_intrinsics(70, 320, 240)
    im = DW.world_camera(w, DW.camera_pose((-8.0, 2.0, 1.4), (2.0, 2.0, 3.0)), K, 320, 240)
    labels = set(np.unique(im["label"]).tolist())
    assert 4 in labels and 3 in labels
    f0, f1 = w["objects"][i]["lamp_faces"]["red"]
    red_px = (im["face"] >= f0) & (im["face"] < f1)
    assert red_px.sum() > 3                                      # 赤レンズが映る
    c = im["color"][red_px].mean(axis=0)
    assert c[0] > 0.6 and c[0] > 4 * c[1] and c[0] > 4 * c[2]         # Lambert で暗くなっても赤が支配的


# ─────────────────────────────── fail-closed ───────────────────────────────────

def test_fail_closed():
    with pytest.raises(ValueError):
        R.sign_image("yield")
    with pytest.raises(ValueError):
        R.sign_params("octagon_stop")
    with pytest.raises(ValueError):
        R.sign_params("stop", side=0.0)
    with pytest.raises(ValueError):
        R.sign_image("speed_limit", value=0)
    with pytest.raises(ValueError):
        R.plate_mesh_from_image(np.ones((8, 8, 4)), 0.0, 0.5)
    with pytest.raises(ValueError):
        R.plate_mesh_from_image(np.ones((8, 8, 4)), 0.5, 0.5, cell=0)
    with pytest.raises(ValueError):
        R.plate_mesh_from_image(np.ones((8, 8, 3)), 0.5, 0.5)
    with pytest.raises(ValueError):
        R.signal_jp_mesh(lens=0.0)
    with pytest.raises(ValueError):
        R.signal_jp_mesh(n=4)
    w = DW._empty_world()
    with pytest.raises(ValueError):
        R.add_signal_jp(w, 0, 0, 0, arm=3.6)                     # 最大 3.5 m
    with pytest.raises(ValueError):
        R.add_signal_jp(w, 0, 0, 0, lamp_bottom=4.4)             # 4.5 m 以上
    with pytest.raises(ValueError):
        R.add_signal_jp(w, 0, 0, 0, state="blue")
    with pytest.raises(ValueError):
        R.add_signal_jp(w, 0, 0, 0, arm_side="up")
    with pytest.raises(ValueError):
        R.add_sign(w, "stop", 0, 0, 0, mount_height=-1.0)
    assert len(w["objects"]) == 0                                # 失敗は世界を汚さない
    R.add_signal_jp(w, 0, 0, 0, arm=3.5, lamp_bottom=4.5)        # 端は通る
    assert len(w["objects"]) == 2
