"""ballworld の門: ITTF の表 / 台の世界 / 正 20 面体球 / 模様つき球 / 姿勢と回転 / カメラの組 / 真値の投影と描画・検出の整合。"""
import numpy as np
import pytest

import balltrack as BT
import ballworld as BW
import driveworld as DW

ORANGE = (1.0, 0.55, 0.05)
BALL_P = np.array([-0.15, 0.2, 1.0])


def _closeup():
    """球 BALL_P を ~5 px 半径で写す近接カメラ(320×200・fov 60°)。"""
    K = DW.camera_intrinsics(60, 320, 200)
    pose = DW.camera_pose((-0.3, -0.5, 1.2), tuple(BALL_P))
    return {"pose": pose, "K": K, "width": 320, "height": 200}


def _to_camera_dir(cam, p):
    """点 p からカメラ中心への単位ベクトル(世界)。"""
    T = cam["pose"]
    pc = T[:3, :3] @ p + T[:3, 3]
    d = T[:3, :3].T @ (-pc)
    return d / np.linalg.norm(d)


def _signed_volume(V, F):
    return float(np.sum(np.einsum("ij,ij->i", V[F[:, 0]], np.cross(V[F[:, 1]], V[F[:, 2]]))) / 6.0)


def _closeup_scene():
    """近接カメラ + カメラを向く模様と裏の模様を持つ球の世界。返り値 (world, i, cam)。"""
    cam = _closeup()
    to_cam = _to_camera_dir(cam, BALL_P)
    w = BW.table_world(BW.table_params())
    bm = BW.ball_mesh(0.02, 3, markers=[(to_cam, 20.0), (-to_cam, 20.0)])
    i = BW.add_ball(w, bm, BALL_P, np.eye(3))
    return w, i, cam


# ─────────────────────────────── 台 ─────────────────────────────────────────

def test_table_params_defaults_are_ittf():
    """既定 = ITTF(2.74 × 1.525 × 0.76、ネット 0.1525 高・1.83 長)。非正の寸法は ValueError。"""
    tp = BW.table_params()
    assert (tp["length"], tp["width"], tp["height"], tp["net_height"], tp["net_length"]) == (2.74, 1.525, 0.76, 0.1525, 1.83)
    assert tp["line_width"] == 0.02 and tp["centre_line"] == 0.003
    assert BW.table_params(length=3.0)["length"] == 3.0
    with pytest.raises(ValueError):
        BW.table_params(width=0.0)
    with pytest.raises(ValueError):
        BW.table_params(net_height=-0.1)


def test_table_world_has_floor_table_lines_and_net():
    """objects に床・台・5 本の線・ネット部品があり、bounds = (±1.37, ±0.7625)、表は world["table"] に残る。floor=False なら床が無い。"""
    tp = BW.table_params()
    w = BW.table_world(tp)
    names = [o["name"] for o in w["objects"]]
    assert "floor" in names and "table" in names and names.count("line") == 5
    assert any(n.startswith("net") for n in names)
    assert np.allclose(w["bounds"], (-1.37, 1.37, -0.7625, 0.7625)) and w["table"] is tp
    wf = BW.table_world(tp, floor=False)
    assert "floor" not in [o["name"] for o in wf["objects"]] and 25 not in np.unique(wf["face_label"])


def test_table_world_labels_and_geometry_are_consistent():
    """ラベル ⊆ {20, 21, 22, 25}、頂点は有限で索引は範囲内、台の面は 20、天板の上面 z = height で x, y は ±L/2, ±W/2。"""
    tp = BW.table_params()
    w = BW.table_world(tp)
    assert set(np.unique(w["face_label"]).tolist()) <= {20, 21, 22, 25}
    assert np.isfinite(w["V"]).all() and w["F"].max() < len(w["V"])
    assert len(w["F"]) == len(w["face_label"]) == len(w["face_color"])
    names = [o["name"] for o in w["objects"]]
    tab = w["objects"][names.index("table")]
    Vt = w["V"][slice(*tab["verts"])]
    assert Vt[:, 2].max() == tp["height"] and Vt[:, 2].min() < tp["height"]
    assert np.allclose(Vt[:, 0].min(), -1.37) and np.allclose(Vt[:, 0].max(), 1.37)
    assert np.allclose(Vt[:, 1].min(), -0.7625) and np.allclose(Vt[:, 1].max(), 0.7625)
    assert (w["face_label"][slice(*tab["faces"])] == 20).all()
    lines = [i for i, n in enumerate(names) if n == "line"]
    assert len(lines) >= 2                                   # 白線は端の 2 本 + 中央線(空なら下の表明は無条件に通る)
    for k in lines:
        Vl = w["V"][slice(*w["objects"][k]["verts"])]
        assert (Vl[:, 2] > tp["height"]).all() and (w["face_label"][slice(*w["objects"][k]["faces"])] == 21).all()


# ─────────────────────────────── 球 ─────────────────────────────────────────

def test_icosphere_counts_radius_and_orientation():
    """面 20·4^s、頂点 10·4^s + 2、全頂点 |v| = radius(1e-12)、外向き(符号つき体積 > 0、subdiv 3 で 4/3πr³ の 3 % 以内)。"""
    for s in range(4):
        V, F = BW.icosphere(1.0, s)
        assert len(F) == 20 * 4 ** s and len(V) == 10 * 4 ** s + 2
        assert F.min() == 0 and F.max() == len(V) - 1
    V, F = BW.icosphere(0.02, 2)
    assert np.abs(np.linalg.norm(V, axis=1) - 0.02).max() < 1e-12
    V, F = BW.icosphere(0.02, 3)
    vol = _signed_volume(V, F)
    assert vol > 0 and abs(vol / (4.0 / 3.0 * np.pi * 0.02 ** 3) - 1.0) < 0.03
    with pytest.raises(ValueError):
        BW.icosphere(0.0, 1)
    with pytest.raises(ValueError):
        BW.icosphere(1.0, -1)


def test_ball_mesh_marker_faces_are_exactly_the_cone():
    """模様(ラベル 24)の面 = 重心の向きが marker_dir から marker_angle 以内の面そのもの。2 つの模様は 2 つの集合、色は marker_color。"""
    bm = BW.ball_mesh(0.02, 3, marker_dir=(0.0, 0.0, 1.0), marker_angle=25.0)
    cen = bm["V"][bm["F"]].mean(axis=1)
    cen /= np.linalg.norm(cen, axis=1, keepdims=True)
    expect = cen @ np.array([0.0, 0.0, 1.0]) > np.cos(np.radians(25.0))
    assert np.array_equal(bm["label"] == 24, expect) and expect.sum() > 0 and (~expect).sum() > 0
    assert np.allclose(bm["color"][expect], (0.05, 0.05, 0.05)) and np.allclose(bm["color"][~expect], ORANGE)
    assert bm["radius"] == 0.02 and len(bm["markers"]) == 1 and np.allclose(bm["markers"][0], (0, 0, 1))
    d2 = np.array([1.0, 0.0, 0.0])
    bm2 = BW.ball_mesh(0.02, 3, markers=[((0, 0, 1), 25.0), (d2, 18.0)], marker_color=(0.1, 0.2, 0.3))
    e1 = cen @ np.array([0.0, 0.0, 1.0]) > np.cos(np.radians(25.0))
    e2 = cen @ d2 > np.cos(np.radians(18.0))
    assert not (e1 & e2).any() and np.array_equal(bm2["label"] == 24, e1 | e2)
    assert np.allclose(bm2["color"][e1 | e2], (0.1, 0.2, 0.3)) and len(bm2["markers"]) == 2
    bm3 = BW.ball_mesh(0.02, 3, markers=[((2.0, 0.0, 0.0), 18.0)])       # 向きは正規化される
    assert np.allclose(bm3["markers"][0], (1, 0, 0)) and np.array_equal(bm3["label"] == 24, e2)


def test_add_ball_and_set_pose_are_rigid():
    """add_ball / ball_set_pose の頂点 = local @ Rᵀ + p(1e-12)、面ラベルは写される、球でない物体は ValueError。"""
    tp = BW.table_params()
    w = BW.table_world(tp)
    bm = BW.ball_mesh(0.02, 2, markers=[((0, 0, 1), 25.0)])
    p = np.array([0.3, -0.1, tp["height"] + 0.2])
    R = BW.rotation_from_omega([10.0, -20.0, 30.0], 0.01)
    i = BW.add_ball(w, bm, p, R)
    obj = w["objects"][i]
    assert obj["name"] == "ball" and obj["label"] == 23 and obj["radius"] == 0.02
    assert np.abs(w["V"][slice(*obj["verts"])] - (bm["V"] @ R.T + p)).max() < 1e-12
    assert np.array_equal(w["face_label"][slice(*obj["faces"])], bm["label"]) and 24 in w["face_label"]
    assert np.allclose(obj["center"], p) and np.allclose(obj["R"], R) and np.array_equal(obj["local"], bm["V"])
    nF = len(w["F"])
    p2 = p + (0.1, 0.05, 0.02)
    R2 = BW.rotation_from_omega([0.0, 120.0, 40.0], 1 / 200) @ R
    BW.ball_set_pose(w, i, p2, R2)
    assert np.abs(w["V"][slice(*obj["verts"])] - (bm["V"] @ R2.T + p2)).max() < 1e-12
    assert np.allclose(obj["center"], p2) and np.allclose(obj["R"], R2)
    assert np.array_equal(w["face_label"][slice(*obj["faces"])], bm["label"]) and len(w["F"]) == nF
    j = BW.add_ball(w, bm, p, None, name="ball2")                        # R 省略 = 単位
    assert np.abs(w["V"][slice(*w["objects"][j]["verts"])] - (bm["V"] + p)).max() < 1e-12
    with pytest.raises(ValueError):
        BW.ball_set_pose(w, 0, p, R)                                     # floor は球でない


def test_rotation_from_omega_is_a_proper_rotation():
    """直交・det +1・回転角 |ω|dt・ω が不動軸、ω = 0 で単位、N 歩の合成 = 1 歩(1e-9)。"""
    omega = np.array([50.0, -120.0, 300.0])
    Rw = BW.rotation_from_omega(omega, 1 / 200)
    assert np.allclose(Rw @ Rw.T, np.eye(3), atol=1e-12) and abs(np.linalg.det(Rw) - 1.0) < 1e-12
    assert abs(np.arccos((np.trace(Rw) - 1.0) / 2.0) - np.linalg.norm(omega) / 200) < 1e-9
    assert np.allclose(Rw @ omega, omega, atol=1e-12)
    v = np.cross(omega, [1.0, 0.0, 0.0])
    assert abs(np.arccos(v @ (Rw @ v) / (v @ v)) - np.linalg.norm(omega) / 200) < 1e-9     # 直交方向は角度そのぶん回る
    assert np.array_equal(BW.rotation_from_omega([0.0, 0.0, 0.0], 0.1), np.eye(3))
    assert np.array_equal(BW.rotation_from_omega(omega, 0.0), np.eye(3))
    Rn = np.eye(3)
    for _ in range(50):
        Rn = BW.rotation_from_omega(omega, 1 / 10000) @ Rn
    assert np.abs(Rn - BW.rotation_from_omega(omega, 50 / 10000)).max() < 1e-9


# ─────────────────────────────── カメラ ─────────────────────────────────────

def test_camera_rig_looks_at_table_centre():
    """n = 2, 4 の全カメラで台の中心(z = height + 0.1)が像の中心に写る(1 px 以内)。n = 3 は ValueError。"""
    tp = BW.table_params()
    target = np.array([[0.0, 0.0, tp["height"] + 0.1]])
    for n in (2, 4):
        rig = BW.camera_rig(tp, n=n, width=320, height_px=256, fov_deg=40)
        assert len(rig) == n
        for c in rig:
            assert c["pose"].shape == (4, 4) and c["K"].shape == (3, 3) and (c["width"], c["height"]) == (320, 256)
            uv = BT.reproject(target, c["pose"], c["K"])[0]
            assert np.isfinite(uv).all() and np.hypot(uv[0] - c["K"][0, 2], uv[1] - c["K"][1, 2]) < 1.0
            assert c["eye"][2] == 1.7 and abs(c["eye"][0]) > tp["length"] / 2
    with pytest.raises(ValueError):
        BW.camera_rig(tp, n=3)


def test_ball_truth_agrees_with_render_and_detection():
    """近接カメラで描いた球: 真値の uv は球の画素(ラベル 23/24)の 1.5 px 以内、radius_px = f·r/深度、像の等価半径も 1 px 以内、
    chroma 検出は真値から 0.5 px 以内(実測 0.14 px)。"""
    w, i, cam = _closeup_scene()
    tr = BW.ball_truth(w, i, cam)
    view = DW.world_camera(w, cam["pose"], cam["K"], cam["width"], cam["height"])
    ball = (view["label"] == 23) | (view["label"] == 24)
    assert ball.sum() > 20
    rr, cc = np.nonzero(ball)
    assert np.hypot(cc - tr["uv"][0], rr - tr["uv"][1]).min() < 1.5
    assert tr["depth"] > 0 and abs(tr["radius_px"] - cam["K"][0, 0] * 0.02 / tr["depth"]) < 1e-12
    assert abs(np.sqrt(ball.sum() / np.pi) - tr["radius_px"]) < 1.0
    det = BT.ball_detect(view["color"], mode="chroma", color=ORANGE, color_tol=0.12)
    assert det and np.hypot(det[0]["col"] - tr["uv"][0], det[0]["row"] - tr["uv"][1]) < 0.5
    assert abs(det[0]["radius"] - tr["radius_px"]) < 1.0


def test_ball_truth_marker_visibility_follows_pose():
    """カメラを向く模様の markers_uv は有限で円板の中(描いた模様の画素の重心と 1 px 以内)、裏側の模様は NaN。
    半回転で表裏が入れ替わり、中心の uv は動かない。"""
    w, i, cam = _closeup_scene()
    tr = BW.ball_truth(w, i, cam)
    m = tr["markers_uv"]
    assert m.shape == (2, 2) and np.isfinite(m[0]).all() and np.isnan(m[1]).all()
    assert np.hypot(m[0, 0] - tr["uv"][0], m[0, 1] - tr["uv"][1]) < tr["radius_px"]
    view = DW.world_camera(w, cam["pose"], cam["K"], cam["width"], cam["height"])
    mk = view["label"] == 24
    assert mk.any()
    mr, mc = np.nonzero(mk)
    assert np.hypot(mc.mean() - m[0, 0], mr.mean() - m[0, 1]) < 1.0
    to_cam = _to_camera_dir(cam, BALL_P)
    BW.ball_set_pose(w, i, BALL_P, BW.rotation_from_omega(np.cross(to_cam, [0.0, 0.0, 1.0]), np.pi))
    tr2 = BW.ball_truth(w, i, cam)
    assert np.isnan(tr2["markers_uv"][0]).all() and np.isfinite(tr2["markers_uv"][1]).all()
    assert np.allclose(tr2["uv"], tr["uv"]) and abs(tr2["radius_px"] - tr["radius_px"]) < 1e-12
    view2 = DW.world_camera(w, cam["pose"], cam["K"], cam["width"], cam["height"])
    assert (view2["label"] == 24).any()                                   # 裏の模様が表に来て描かれる
