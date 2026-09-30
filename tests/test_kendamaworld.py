"""kendamaworld の門: けん玉の形(公表寸法を頂点から測る)/ ラベルと色 / 糸 / 世界と姿勢 / カメラの組 / 真値の投影 / 描画 /
玉とけん玉の隙間 / 画像だけの知覚(窓の描画 = 全画面の切り出し、真値の速度を読まない、放物線の予測、閉ループの捕球)。

寸法の出どころ: 玉 60 mm・横幅 70 mm・全長 180 mm = 日本けん玉協会の公表値、けん 160 mm・皿 42 / 38 / 35 mm = ユーザー提供の
JKA 16-2 型の説明(一次資料は未確認)、推奨品の大皿 49 mm(同)。それ以外は kendama.kendama_params の docstring の「仮定」。
"""
import math

import numpy as np
import pytest

import balltrack as BT
import driveworld as DW
import kendama as K
import kendamaworld as BK

KP = K.kendama_params()
KL = K.kendama_params("recommended_large_cup")
KV = K.kendama_params(rho=0.0)
TARGET = np.array([0.0, 0.0, 1.0])
HAND = np.array([0.0, 0.0, 1.0])


def _signed_volume(V, F):
    return float(np.sum(np.einsum("ij,ij->i", V[F[:, 0]], np.cross(V[F[:, 1]], V[F[:, 2]]))) / 6.0)


def _boundary_edges(F):
    """境界辺の数(閉じたメッシュなら 0)。"""
    E = np.sort(np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), axis=1)
    _, cnt = np.unique(E, axis=0, return_counts=True)
    return int((cnt != 2).sum())


def _verts_of(m, labels):
    F = m["F"][np.isin(m["label"], labels)]
    return m["V"][np.unique(F)]


# ─────────────────────────────── 形 ─────────────────────────────────────────

def test_ken_mesh_parts_are_closed_outward_and_labelled():
    """けん(回転体)と皿胴(回転体)はそれぞれ閉じ(境界辺 0)、外向き(符号つき体積 > 0)。ラベルは 27 / 28 / 30 / 31 が全部あり、
    色はラベルごとに 1 色で互いに違う(けん = 木、大皿 = 赤、小皿 = 紫、中皿 = 青)。"""
    m = BK.ken_mesh(KP)
    for part in ("ken", "cross"):
        f0, f1 = m["parts"][part]
        F = m["F"][f0:f1]
        assert _boundary_edges(F) == 0
        assert _signed_volume(m["V"], F) > 0
    labs = set(np.unique(m["label"]).tolist())
    assert labs == {27, 28, 30, 31}
    cols = {}
    for lab in labs:
        C = m["color"][m["label"] == lab]
        assert np.ptp(C, axis=0).max() == 0.0
        cols[lab] = tuple(C[0])
    assert len(set(cols.values())) == 4
    assert cols[28] == BK.CUP_COLOR and cols[30] == BK.SMALL_CUP_COLOR and cols[31] == BK.BASE_CUP_COLOR
    assert m["cup_radius"] == KP["cup_radius_big"] and m["ken_length"] == KP["ken_length"]
    with pytest.raises(ValueError):
        BK.ken_mesh({k: v for k, v in KP.items() if k != "cup_depth"})
    with pytest.raises(ValueError):
        BK.ken_mesh(dict(KP, ken_length=0.0))
    with pytest.raises(ValueError):
        BK.ken_mesh(dict(KP, ken_length=0.09))                                 # 輪郭が組めない長さ


def test_published_dimensions_measured_from_vertices():
    """頂点から測る: 皿胴の幅(大皿の縁 〜 小皿の縁)= 70 mm、けんの高さ(けん先 → 中皿の縁)= 160 mm(公式ルールの下限 150 mm 以上)、
    大皿・中皿・小皿の縁の直径 = 42 / 38 / 35 mm(頂点は縁の円の上にあるので 1e-12、多角形の辺の中点での直径は cos(π/n) 倍 = 0.5 % 以内)、
    推奨品の大皿 = 49 mm。玉の直径 = 60 mm(icosphere の対蹠頂点の距離)。"""
    for kp, big in ((KP, 0.042), (KL, 0.049)):
        m = BK.ken_mesh(kp)
        cross = m["V"][np.unique(m["F"][slice(*m["parts"]["cross"])])]
        ken = m["V"][np.unique(m["F"][slice(*m["parts"]["ken"])])]
        assert np.ptp(cross[:, 2]) == pytest.approx(0.070, abs=1e-12)
        assert np.ptp(ken[:, 0]) == pytest.approx(0.160, abs=1e-12) and np.ptp(ken[:, 0]) >= 0.150
        d_big = 2 * np.hypot(*_verts_of(m, [28])[:, :2].T).max()
        d_small = 2 * np.hypot(*_verts_of(m, [30])[:, :2].T).max()
        d_base = 2 * np.hypot(*_verts_of(m, [31])[:, 1:].T).max()
        assert d_big == pytest.approx(big, abs=1e-12)
        assert d_small == pytest.approx(0.035, abs=1e-12) and d_base == pytest.approx(0.038, abs=1e-12)
        assert d_big * math.cos(math.pi / 32) > 0.995 * big
    bm = BK._ball_mesh_with_hole(KP)
    Vb = bm["V"][np.unique(bm["F"][bm["label"] == 23])]
    D = np.linalg.norm(Vb[:, None, :] - Vb[None, :, :], axis=2)
    assert D.max() == pytest.approx(0.060, abs=1e-12)


def test_assembled_kendama_is_180_mm_and_the_spike_fits_the_hole():
    """けん先を玉の穴の底まで挿した組み立て(穴の軸 = −けんの軸、玉の中心 = けん先 − (穴の深さ − r_b))の全長(けんの軸に沿って)
    = 中皿の縁 → 玉の向こう側 = 180 mm(1e-12: 穴の軸の反対側に icosphere の頂点がある。大皿・推奨品・中皿の姿勢で)。穴に入る部分(けん先から穴の深さ 40 mm)のけんの半径 < 穴の半径。
    穴の深さ 40 mm = けん 160 + 玉 60 − 全長 180(導いた値)。推奨品(穴 24 mm)も同じ全長。"""
    for kp in (KP, KL, K.kendama_params(trick="chuzara")):
        assert kp["hole_depth"] == pytest.approx(0.040, abs=1e-12) and kp["total_length"] == pytest.approx(0.180, abs=1e-12)
        w = BK.kendama_world(kp, floor=False, hand=HAND)
        u = kp["R_ken"] @ np.array([1.0, 0.0, 0.0])                            # けんの軸(世界)
        O = HAND - kp["R_ken"] @ kp["grip"]
        tip = O + kp["cross_from_tip"] * u
        R = BK._rot_from_to(BK.HOLE_AXIS_LOCAL, -u)
        centre = tip - (kp["hole_depth"] - kp["ball_radius"]) * u
        st = BK.kendama_pose(w, HAND, centre, R_ball=R)
        assert np.allclose(st["hole_axis"], -u) and np.allclose(st["cross"], O)
        idx = w["kendama"]
        Vk = w["V"][slice(*w["objects"][idx["ken"]]["verts"])] @ u
        ball = w["objects"][idx["ball"]]
        f0, f1 = ball["faces"]
        Fb = w["F"][f0:f1][w["face_label"][f0:f1] == 23]
        Vb = w["V"][np.unique(Fb)] @ u
        total = max(Vk.max(), Vb.max()) - min(Vk.min(), Vb.min())
        assert total == pytest.approx(0.180, abs=1e-12)
        m = BK.ken_mesh(kp)
        ken = m["V"][np.unique(m["F"][slice(*m["parts"]["ken"])])]
        inside = ken[:, 0] > kp["cross_from_tip"] - kp["hole_depth"] - 1e-12
        assert inside.sum() > 10 and np.hypot(ken[inside, 1], ken[inside, 2]).max() < kp["hole_radius"]


def test_add_ken_and_set_pose_are_rigid_and_carry_anchors():
    """add_ken の頂点 = local @ Rᵀ + p(1e-12)、面ラベルが写る、anchors(大皿の縁の中心 = (0, 0, 35 mm)、糸穴 = kp の tie_offset、
    けん先 = (58 mm, 0, 0))、ken_set_pose で頂点だけ動く、けんでない物体は ValueError。"""
    w = DW._empty_world()
    m = BK.ken_mesh(KP)
    assert np.allclose(m["anchors"]["big_rim"], [0, 0, 0.035]) and np.allclose(m["anchors"]["tie"], KP["tie_offset"])
    assert np.allclose(m["anchors"]["spike_tip"], [KP["cross_from_tip"], 0, 0])
    assert np.allclose(m["anchors"]["base_rim"], [KP["cross_from_tip"] - KP["ken_length"], 0, 0])
    p = np.array([0.1, -0.2, 1.1])
    a = np.radians(30.0)
    R = np.array([[np.cos(a), 0, np.sin(a)], [0, 1, 0], [-np.sin(a), 0, np.cos(a)]])
    i = BK.add_ken(w, m, p, R)
    obj = w["objects"][i]
    assert obj["kind"] == "ken" and obj["label"] == 27
    assert np.abs(w["V"][slice(*obj["verts"])] - (m["V"] @ R.T + p)).max() < 1e-12
    assert np.array_equal(w["face_label"][slice(*obj["faces"])], m["label"])
    nF, nV = len(w["F"]), len(w["V"])
    p2, R2 = p + (0.05, 0.0, 0.1), np.eye(3)
    BK.ken_set_pose(w, i, p2, R2)
    assert np.abs(w["V"][slice(*obj["verts"])] - (m["V"] + p2)).max() < 1e-12
    assert np.allclose(obj["center"], p2) and len(w["F"]) == nF and len(w["V"]) == nV
    j = DW.world_add(w, np.eye(3), np.array([[0, 1, 2]]), 25, (0.5, 0.5, 0.5))
    with pytest.raises(ValueError):
        BK.ken_set_pose(w, j, p, R)


# ─────────────────────────────── 糸 ─────────────────────────────────────────

def test_string_mesh_is_a_prism_of_the_right_length():
    """8 頂点 12 面、両端の 4 頂点の重心の距離 = |p_ball − p_cup|(1e-9)、断面は軸に直交し半径 r√2、体積 = (2r)² L(1e-12)、
    外向き。真下(軸が z に平行)と水平も通る。一致した 2 点は ValueError。"""
    cases = [([0.0, 0.0, 0.0], [0.1, 0.2, 0.3]), ([0.0, 0.0, 1.0], [0.0, 0.0, 0.6]), ([0.3, 0.0, 1.0], [-0.1, 0.0, 1.0])]
    assert len(cases) == 3
    for a, b in cases:
        V, F = BK.string_mesh(a, b, radius=0.0015)
        assert V.shape == (8, 3) and F.shape == (12, 3)
        L = np.linalg.norm(np.subtract(b, a))
        assert abs(np.linalg.norm(V[4:].mean(axis=0) - V[:4].mean(axis=0)) - L) < 1e-9
        assert np.allclose(V[:4].mean(axis=0), a) and np.allclose(V[4:].mean(axis=0), b)
        d = (np.subtract(b, a)) / L
        assert np.abs((V[:4] - a) @ d).max() < 1e-12
        assert np.allclose(np.linalg.norm(V[:4] - a, axis=1), 0.0015 * np.sqrt(2))
        assert _boundary_edges(F) == 0
        assert abs(_signed_volume(V, F) - (0.003 ** 2) * L) < 1e-12
    with pytest.raises(ValueError):
        BK.string_mesh([0, 0, 1], [0, 0, 1])


def test_add_string_and_string_set_update_vertices():
    """add_string はラベル 29・暗い灰、string_set で頂点が新しい両端に移る(長さも更新)、糸でない物体は ValueError。"""
    w = DW._empty_world()
    i = BK.add_string(w, [0.0, 0.0, 0.6], [0.0, 0.0, 1.0])
    obj = w["objects"][i]
    assert obj["kind"] == "string" and obj["label"] == 29
    assert (w["face_label"][slice(*obj["faces"])] == 29).all() and np.allclose(w["face_color"][slice(*obj["faces"])], BK.STRING_COLOR)
    BK.string_set(w, i, [0.2, 0.1, 0.7], [0.0, 0.0, 1.0])
    V2 = w["V"][slice(*obj["verts"])]
    L2 = np.linalg.norm(np.array([0.2, 0.1, 0.7]) - [0.0, 0.0, 1.0])
    assert abs(np.linalg.norm(V2[4:].mean(axis=0) - V2[:4].mean(axis=0)) - L2) < 1e-9
    assert np.allclose(V2[:4].mean(axis=0), [0.2, 0.1, 0.7]) and np.allclose(obj["p_ball"], [0.2, 0.1, 0.7])
    j = DW.world_add(w, np.eye(3), np.array([[0, 1, 2]]), 25, (0.5, 0.5, 0.5))
    with pytest.raises(ValueError):
        BK.string_set(w, j, [0, 0, 0], [0, 0, 1])


# ─────────────────────────────── 世界と姿勢 ─────────────────────────────────

def test_kendama_world_and_pose():
    """world["kendama"] の索引と名前、ラベル集合 = {23 玉, 25 床, 27 けん, 28 大皿, 29 糸, 30 小皿, 31 中皿, 32 玉の穴}、
    玉の中心は皿胴の糸穴からひもの有効長(糸 + r_b)、糸 = 糸穴 → 玉の糸穴(玉の表面、糸穴を向く)で長さ = 糸(0.39 m)、
    大きな穴は糸穴の反対(結び目から遠い側)を向く。kendama_pose で手元を動かすと糸穴・大皿の縁が一緒に動く。floor=False で 25 が消える。"""
    w = BK.kendama_world(KP, hand=HAND)
    idx = w["kendama"]
    for key in ("ken", "ball", "string"):
        assert 0 <= idx[key] < len(w["objects"]) and w["objects"][idx[key]]["name"] == key
    assert set(np.unique(w["face_label"]).tolist()) == {23, 25, 27, 28, 29, 30, 31, 32}
    ball = w["objects"][idx["ball"]]
    tie = HAND + KP["tie_offset"]
    assert np.linalg.norm(ball["center"] - tie) == pytest.approx(KP["pendulum_length"], abs=1e-12)
    s = w["objects"][idx["string"]]
    assert np.allclose(s["p_cup"], tie) and np.linalg.norm(s["p_ball"] - s["p_cup"]) == pytest.approx(KP["string"], abs=1e-12)
    assert np.linalg.norm(s["p_ball"] - ball["center"]) == pytest.approx(KP["ball_radius"], abs=1e-12)
    hole = ball["R"] @ BK.HOLE_AXIS_LOCAL
    assert float(hole @ (tie - ball["center"])) / KP["pendulum_length"] == pytest.approx(-1.0, abs=1e-12)
    st = BK.kendama_pose(w, HAND + [0.1, 0.0, 0.2], HAND + [0.1, 0.05, 0.0])
    assert np.allclose(st["tie"], HAND + [0.1, 0.0, 0.2] + KP["tie_offset"])
    assert np.allclose(st["cup"], HAND + [0.1, 0.0, 0.2] + KP["cup_offset"]) and np.allclose(st["cup_axis"], KP["cup_axis"])
    assert KP["cup_axis"][2] == pytest.approx(math.cos(math.radians(15.0)), abs=1e-12)          # 皿持ち: けん先が 15° 下
    for trick, cup in (("kozara", "small"), ("chuzara", "base"), ("rousoku", "base")):
        kt = K.kendama_params(trick=trick)
        wt = BK.kendama_world(kt, hand=HAND)
        st = BK.kendama_pose(wt, HAND, HAND + [0.0, -0.013, -0.3])
        assert kt["catch_cup"] == cup and np.allclose(st["cup"], HAND + kt["cup_offset"]) and np.allclose(st["cup_axis"], kt["cup_axis"])
        assert st["cup_axis"][2] > 0.96 and np.allclose(st["tie"], HAND + kt["tie_offset"])
    assert np.allclose(w["objects"][idx["ken"]]["center"], HAND + [0.1, 0.0, 0.2])
    w2 = BK.kendama_world(KP, floor=False, p_ball=(0.1, 0.0, 0.7))
    assert 25 not in np.unique(w2["face_label"]) and np.allclose(w2["objects"][w2["kendama"]["ball"]]["center"], (0.1, 0.0, 0.7))
    with pytest.raises(ValueError):
        BK.kendama_pose({"V": np.zeros((0, 3))}, HAND, HAND)


# ─────────────────────────────── カメラ・投影・描画 ─────────────────────────

def test_kendama_rig_looks_at_play_centre():
    """n = 2, 4 の全カメラで (0, 0, 1.0) が像の中心(1 px 以内)、方位は 0°/90°(/180°/270°)で目の高さ = height、
    カメラは水平距離 distance。既定 480 × 360。n = 3 は ValueError。"""
    assert (BK.kendama_rig(KP)[0]["width"], BK.kendama_rig(KP)[0]["height"]) == (480, 360)
    for n, az in ((2, (0.0, 90.0)), (4, (0.0, 90.0, 180.0, 270.0))):
        rig = BK.kendama_rig(KP, n=n, distance=1.2, height=1.2, fov_deg=40, width=640, height_px=480)
        assert len(rig) == n
        for c, a in zip(rig, az):
            assert c["pose"].shape == (4, 4) and c["K"].shape == (3, 3) and (c["width"], c["height"]) == (640, 480)
            uv = BT.reproject(TARGET[None], c["pose"], c["K"])[0]
            assert np.isfinite(uv).all() and np.hypot(uv[0] - c["K"][0, 2], uv[1] - c["K"][1, 2]) < 1.0
            assert c["eye"][2] == 1.2 and abs(np.hypot(c["eye"][0], c["eye"][1]) - 1.2) < 1e-12
            assert abs(np.degrees(np.arctan2(c["eye"][1], c["eye"][0])) % 360.0 - a) < 1e-9
    with pytest.raises(ValueError):
        BK.kendama_rig(KP, n=3)


def test_ken_truth_is_visible_and_matches_render():
    """既定の姿勢で大皿の縁の中心は全カメラで visible、深度 > 0、radius_px = f·r_cup/深度。描いた大皿の画素(28: 縁 + ラッパ)は
    真値の縁の中心から (縁の半径 + ラッパの長さ 20 mm) の像 + 2 px 以内。"""
    w = BK.kendama_world(KP)
    rig = BK.kendama_rig(KP)
    for c in rig:
        tr = BK.ken_truth(w, w["kendama"]["ken"], c)
        assert tr["visible"] and tr["depth"] > 0 and np.allclose(tr["p"], HAND + KP["cup_offset"])
        assert abs(tr["radius_px"] - c["K"][0, 0] * KP["cup_radius_big"] / tr["depth"]) < 1e-12
        view = DW.world_camera(w, c["pose"], c["K"], c["width"], c["height"])
        cup = view["label"] == 28
        assert cup.sum() > 20
        rr, cc = np.nonzero(cup)
        reach = c["K"][0, 0] * math.hypot(KP["cup_radius_big"], 0.020) / tr["depth"] + 2.0
        assert np.hypot(cc - tr["uv"][0], rr - tr["uv"][1]).max() < reach
    far = {"pose": DW.camera_pose((1.0, 0.0, 1.0), (3.0, 0.0, 1.0)), "K": rig[0]["K"], "width": 480, "height": 360}
    assert not BK.ken_truth(w, w["kendama"]["ken"], far)["visible"]
    with pytest.raises(ValueError):
        BK.ken_truth(w, w["kendama"]["ball"], rig[0])


def test_render_shows_every_part_in_its_colour():
    """近くのカメラ(0.45 m)で描くと、ラベル 23 / 27 / 28 / 29 / 30 / 31 / 32 が全部写り、大皿の画素は赤(R > 3G, 3B)、
    玉の画素は橙、穴の画素は暗い(明るさ < 0.15)。"""
    w = BK.kendama_world(KP, floor=False, hand=HAND, p_ball=HAND + [0.10, -0.013, -0.12])
    BK.kendama_pose(w, HAND, HAND + [0.10, -0.013, -0.12], R_ball=BK._rot_from_to(BK.HOLE_AXIS_LOCAL, [0.3, -1.0, 0.2]))
    K_ = DW.camera_intrinsics(50, 400, 400)
    view = DW.world_camera(w, DW.camera_pose(HAND + [0.2, -0.40, 0.08], HAND + [0.03, 0, -0.04]), K_, 400, 400)
    lb, img = view["label"], view["color"]
    assert np.isfinite(img).all() and img.min() >= 0 and img.max() <= 1
    for label in (23, 27, 28, 29, 30, 31, 32):
        assert (lb == label).sum() > 0, label
    R, G, B = img[..., 0], img[..., 1], img[..., 2]
    big = lb == 28
    assert np.median(R[big]) > 3 * np.median(G[big]) and np.median(R[big]) > 3 * np.median(B[big])
    ball = lb == 23
    assert np.median(G[ball] / R[ball]) == pytest.approx(0.55, abs=0.05)
    assert img[lb == 32].sum(axis=1).max() / 3 < 0.15


# ─────────────────────────────── 隙間 ───────────────────────────────────────

def test_kendama_clearance_exact_distances():
    """回転体までの距離 = 子午面の輪郭までの距離(厳密): 大皿の軸上 5 cm 上の点は縁の角まで √(r_c² + 5 cm²) − r_b、
    皿胴の中心は負(めり込み)、けん先の延長上の点は (距離 − けん先) − r_b、大皿の縁に乗った玉(縁の面から h_c = √(r_b² − r_c²) 上)の隙間は 0(1e-12: 縁は鋭い角、皿は玉の沈みより深い)。
    (N, 3) の軌跡も通る。不正は ValueError。"""
    ax = KP["cup_axis"]
    p = HAND + KP["cup_offset"] + 0.05 * ax
    g = BK.kendama_clearance(KP, HAND, p)
    assert g["gap"][0] == pytest.approx(math.hypot(KP["cup_radius_big"] - BK.CUP_WALL, 0.05) - KP["ball_radius"], abs=1e-12)
    assert BK.kendama_clearance(KP, HAND, HAND)["gap"][0] < -0.03
    assert BK.kendama_clearance(KP, HAND, HAND + KP["R_ken"] @ [0.5, 0.0, 0.0])["gap"][0] == pytest.approx(
        0.5 - KP["cross_from_tip"] - KP["ball_radius"], abs=1e-12)                              # けん先の延長上
    rest = BK.kendama_clearance(KP, HAND, HAND + KP["cup_offset"] + KP["cup_rest_height"] * ax)["gap"][0]
    assert abs(rest) < 1e-12
    P = HAND + np.column_stack([np.zeros(5), np.linspace(0.2, 0.6, 5), np.zeros(5)])
    gg = BK.kendama_clearance(KP, HAND, P)["gap"]
    assert gg.shape == (5,) and np.all(np.diff(gg) > 0)
    with pytest.raises(ValueError):
        BK.kendama_clearance(KP, HAND, [np.nan, 0, 0])


# ─────────────────────────────── 画像だけの知覚 ─────────────────────────────

def test_render_window_equals_crop_of_full_frame():
    """窓だけの描画(主点をずらす)は全画面の描画の切り出しと画素ごとに一致(0.0)。"""
    w = BK.kendama_world(KP)
    c = BK.kendama_rig(KP)[0]
    full = DW.world_camera(w, c["pose"], c["K"], c["width"], c["height"])["color"]
    win = BK._render_window(w, c, 150, 80, 128, 128)
    assert np.abs(win - full[80:208, 150:278]).max() == 0.0


def test_camera_perceiver_recovers_a_free_parabola_without_reading_v():
    """真空の放物線を飛ぶ玉(手元は玉の 20 cm 上・15 cm 横: 糸穴との距離はずっとひもより短い = 最初から弛んでいる)を 100 fps で撮らせ、速度は NaN を渡す(読めば NaN が出る)。
    弛みは最初の 2 コマで検出、3 コマ目から予測を返し(それまでは None)、0.3 s 後の予測は位置 < 2 mm・速度 < 0.05 m/s。
    画素雑音 2 px では誤差が大きくなる(同じ乱数)。拒否: fps ≤ 0、pixel_noise < 0、カメラ 1 台、scene なし。"""
    rig = BK.kendama_rig(KP)
    p0, v0 = np.array([0.05, -0.05, 1.05]), np.array([-0.1, 0.1, 1.5])
    errs = {}
    for pn in (0.0, 2.0):
        hand = HAND + [0.0, 0.15, 0.25]
        w = BK.kendama_world(KP, hand=hand)
        per = BK.camera_perceiver(w, rig, fps=100, pixel_noise=pn, rng=np.random.default_rng(3))
        scene = {"hand": hand, "tie": hand + KP["tie_offset"]}
        outs = []
        for i in range(301):
            t = i * 1e-3
            p = p0 + v0 * t - 0.5 * 9.81 * t * t * np.array([0, 0, 1.0])
            outs.append(per(t, p, np.full(3, np.nan), scene))
        assert per.slack_frame == 0
        first = next(i for i, o in enumerate(outs) if o is not None)
        assert first == 20 and all(o is None for o in outs[:20])
        ph, vh = outs[-1]
        t = 0.3
        errs[pn] = (np.linalg.norm(ph - (p0 + v0 * t - 0.5 * 9.81 * t * t * np.array([0, 0, 1.0]))),
                    np.linalg.norm(vh - (v0 - 9.81 * t * np.array([0, 0, 1.0]))))
        assert len(per.frames) == 31 and per.n_render >= 62 and np.isfinite(ph).all() and np.isfinite(vh).all()
    assert errs[0.0][0] < 2e-3 and errs[0.0][1] < 0.05
    assert errs[2.0][0] > errs[0.0][0]
    w = BK.kendama_world(KP)
    for kw in (dict(fps=0.0), dict(pixel_noise=-1.0), dict(min_frames=1), dict(window=16)):
        with pytest.raises(ValueError):
            BK.camera_perceiver(w, rig, **kw)
    with pytest.raises(ValueError):
        BK.camera_perceiver(w, rig[:1])
    with pytest.raises(ValueError):
        BK.camera_perceiver(w, rig)(0.0, HAND, None)


def test_closed_loop_driven_only_by_images_catches():
    """kendama_simulate + camera_perceiver(100 fps、画素雑音 0)+ catch_plan_staged: 横 2 cm にずれて吊った玉を振り上げ(手元を
    −y へ 10 cm 逃がす)、画像の予測だけで皿を運んで大皿で捕る。計画に渡した知覚は全部画像から(n_estimates = plan_log の数)、
    弛みの検出は真値の 1〜4 コマ後、玉はけん玉に触れない(contact で監視、隙間 > 0)。段階は lift → wait → hold → carry → absorb →
    caught の順。弛んだ瞬間の鉛直速度 > 0、頂点は弛んだ高さより上、捕球は頂点より下で下降中。同じ試行を真値の知覚でも捕る。"""
    kp = KP
    L = kp["pendulum_length"]
    h = K.swing_up_plan(kp, origin=HAND, lift=K.swing_up_lift(kp), dodge=(0.0, -0.10, 0.0))
    plan = K.catch_plan_staged(kp)
    contact = lambda hand, p: BK.kendama_clearance(kp, hand, p)["gap"][0]  # noqa: E731
    p0 = HAND + kp["tie_offset"] + [0.02, 0.0, -math.sqrt(L * L - 0.02 ** 2)]
    w = BK.kendama_world(kp, hand=HAND)
    per = BK.camera_perceiver(w, BK.kendama_rig(kp), fps=100)
    r = K.kendama_simulate(kp, h, p0=p0, v0=np.zeros(3), t_end=1.5, catch_plan=plan, plan_from=h.T_lift, perceive=per,
                           contact=contact)
    assert r["caught"] and r["lateral"] < 0.005 and r["min_gap"] > 0.0
    order = [st for i, st in enumerate(r["stage"]) if i == 0 or st != r["stage"][i - 1]]
    assert order == ["lift", "wait", "hold", "carry", "absorb", "caught"], order
    i_s = int(round(r["slack_t"] / 1e-3))
    i_a = int(np.argmax(r["p"][:, 2]))
    assert r["v"][i_s, 2] > 0 and r["p"][i_a, 2] > r["p"][i_s, 2] and r["p"][-1, 2] < r["p"][i_a, 2] and r["v"][-1, 2] < 0
    assert r["n_estimates"] == len(r["plan_log"]) > 100
    t_det = per.frames[per.slack_frame]["t"]
    assert 0.0 < t_det - r["slack_t"] <= 0.04
    assert BK.kendama_clearance(kp, r["hand"], r["p"])["gap"].min() > 0.0
    tr = K.kendama_simulate(kp, h, p0=p0, v0=np.zeros(3), t_end=1.5, catch_plan=K.catch_plan_staged(kp), plan_from=h.T_lift,
                            contact=contact)
    assert tr["caught"]


def test_render_fn_hook_and_frozen_ball_pose():
    """render_fn を差し替える口: 既定と同じ描画を返す関数を渡すと知覚の推定は既定と 1e-12 で一致し、呼ばれた回数 = 描いた窓の数。
    玉の姿勢(描画の約束): scene["taut"] の間は糸穴が糸穴を向き、弛んだコマからは最後の姿勢のまま(R_ball が変わらない)。"""
    rig = BK.kendama_rig(KP)
    calls = []

    def rf(world, cam):
        calls.append(1)
        return DW.world_camera(world, cam["pose"], cam["K"], int(cam["width"]), int(cam["height"]))["color"]

    outs = {}
    for name, fn in (("default", None), ("hook", rf)):
        hand = HAND + [0.0, 0.15, 0.25]
        w = BK.kendama_world(KP, hand=hand)
        per = BK.camera_perceiver(w, rig, fps=100, render_fn=fn)
        scene = {"hand": hand, "tie": hand + KP["tie_offset"]}
        p0, v0 = np.array([0.05, -0.05, 1.05]), np.array([-0.1, 0.1, 1.5])
        o = None
        for i in range(101):
            t = i * 1e-3
            scene["taut"] = t < 0.035
            o = per(t, p0 + v0 * t - 0.5 * 9.81 * t * t * np.array([0, 0, 1.0]), None, scene)
        outs[name] = (o, per)
    (a, pa), (b, pb) = outs["default"], outs["hook"]
    assert np.allclose(a[0], b[0], atol=1e-12) and np.allclose(a[1], b[1], atol=1e-12)
    assert len(calls) == pb.n_render > 0
    Rs = pb.R_ball
    assert len(Rs) == 11 and not np.allclose(Rs[0], Rs[3]) and all(np.allclose(Rs[4], R) for R in Rs[4:])


def test_hole_direction_from_two_views():
    """静止した玉(穴を 2 台の間の向きへ)を 2 台で撮り、kendama.hole_detect の重心を三角測量して玉の中心からの向きを出すと、
    真の穴の軸と 5° 以内(3 姿勢)。"""
    import kendama as KD
    w = BK.kendama_world(KP, hand=(0.0, 0.6, 1.3))
    rig = BK.kendama_rig(KP)
    P = np.array([c["pose"] for c in rig])
    Ks = np.array([c["K"] for c in rig])
    p = np.array([0.0, 0.0, 1.1])
    for d in ([1.0, 1.0, 0.2], [1.0, 0.6, -0.3], [0.7, 1.0, 0.5]):
        d = np.asarray(d) / np.linalg.norm(d)
        BK.kendama_pose(w, (0.0, 0.6, 1.3), p, R_ball=BK._rot_from_to(BK.HOLE_AXIS_LOCAL, d))
        ub, uh = [], []
        for c in rig:
            img = DW.world_camera(w, c["pose"], c["K"], c["width"], c["height"])["color"]
            b = [x for x in BT.ball_detect(img, mode="chroma", color=BK.BALL_COLOR, color_tol=0.12, radius_range=(2.5, 80))
                 if x["fill"] >= 0.6][0]
            h = KD.hole_detect(img, (b["col"], b["row"]), b["radius"])
            assert h["found"]
            ub.append((b["col"], b["row"]))
            uh.append((h["col"], h["row"]))
        e = BT.triangulate_dlt(np.array(uh), P, Ks)["p"] - BT.triangulate_dlt(np.array(ub), P, Ks)["p"]
        ang = math.degrees(math.acos(float(np.clip(e @ d / np.linalg.norm(e), -1, 1))))
        assert ang < 5.0, ang
