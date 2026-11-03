# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""真値つきのカメラ校正の門 / gates of calib_lm (checkerboard, Zhang + LM, stereo, error / uncertainty maps).

真値は op の外: 合成の真の K・歪み・姿勢、描画は画素を板へ逆に引く別経路、OpenCV(別実装、optional)、
モンテカルロの実測の散らばり、閉形式(cx のずれ → 地図は一定値 δ、3D は δ·Z/fx)。
"""
import numpy as np
import pytest

import calib_lm as C
import camera

K_TRUE = np.array([[800.0, 0.0, 319.5], [0.0, 790.0, 241.0], [0.0, 0.0, 1.0]])
D_TRUE = np.array([-0.21, 0.08, 0.0012, -0.0008, 0.0])
SHAPE = (480, 640)
OBJ = C.checkerboard_points((9, 6), 20.0)
OBJ3 = np.column_stack([OBJ, np.zeros(len(OBJ))])


def _pose(rx, ry, rz, t):
    P = np.eye(4)
    P[:3, :3] = camera.rodrigues([rx, ry, rz])
    P[:3, 3] = t
    return P


def _place(rx, ry, rz, uc, vc, Z, K=K_TRUE):
    """板の中心を画素 (uc = col, vc = row) の奥行き Z に置く姿勢。"""
    R = camera.rodrigues([rx, ry, rz])
    t = Z * np.array([(uc - K[0, 2]) / K[0, 0], (vc - K[1, 2]) / K[1, 1], 1.0]) - R @ np.array([80.0, 50.0, 0.0])
    P = np.eye(4)
    P[:3, :3], P[:3, 3] = R, t
    return P


POSES = [_pose(0.3, -0.2, 0.05, (-80, -50, 520)), _pose(-0.25, 0.3, -0.1, (-90, -60, 560)),
         _pose(0.1, 0.35, 0.2, (-70, -40, 500)), _pose(-0.35, -0.15, 0.0, (-100, -45, 600)),
         _pose(0.2, 0.1, -0.3, (-60, -70, 540)), _pose(0.0, -0.4, 0.1, (-85, -50, 580))]


def _proj(P, K=K_TRUE, d=D_TRUE):
    Xc = OBJ3 @ P[:3, :3].T + P[:3, 3]
    return C._proj(Xc, (K[0, 0], K[1, 1], K[0, 2], K[1, 2]), np.asarray(d, float), jac=False)[:, ::-1]


# --------------------------------------------------------------------------- 板と検出
def test_checkerboard_points_are_row_major_from_the_origin():
    p = C.checkerboard_points((4, 3), 5.0)
    assert p.shape == (12, 2)
    assert np.allclose(p[:4], [[0, 0], [5, 0], [10, 0], [15, 0]]) and np.allclose(p[4], [0, 5])
    with pytest.raises(ValueError):
        C.checkerboard_points((1, 3), 5.0)
    with pytest.raises(ValueError):
        C.checkerboard_points((4, 3), 0.0)


def test_sim_truth_corners_are_the_forward_projection():
    s = C.sim_checkerboard((9, 6), 20.0, K_TRUE, D_TRUE, POSES[0], SHAPE, supersample=1)
    assert np.allclose(s["corners"], _proj(POSES[0]), atol=1e-9) and s["visible"]
    assert s["image"].shape == SHAPE and 0.0 <= s["image"].min() and s["image"].max() <= 1.0


@pytest.fixture(scope="module")
def renders():
    return [C.sim_checkerboard((9, 6), 20.0, K_TRUE, D_TRUE, P, SHAPE, supersample=6) for P in POSES[:3]]


def test_detected_corners_match_the_rendered_truth_to_a_few_hundredths_of_a_pixel(renders):
    """描画(画素 → 板の逆向き、6x6 標本)の真値と: 各視点の rms < 0.04 px、最大 < 0.15 px。順は真値と同じ。"""
    for s in renders:
        d = C.find_checkerboard_corners(s["image"], (9, 6))
        e = np.linalg.norm(d - s["corners"], axis=1)
        assert np.sqrt(np.mean(e ** 2)) < 0.04 and e.max() < 0.15


def test_detector_is_not_worse_than_opencv_cornersubpix(renders):
    cv2 = pytest.importorskip("cv2")
    from scipy.spatial import cKDTree
    for s in renders:
        ours = np.linalg.norm(C.find_checkerboard_corners(s["image"], (9, 6)) - s["corners"], axis=1)
        img8 = (s["image"] * 255).round().astype(np.uint8)
        ok, cc = cv2.findChessboardCorners(img8, (9, 6))
        assert ok
        cc = cv2.cornerSubPix(img8, cc, (5, 5), (-1, -1),
                              (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 1e-4)).reshape(-1, 2)
        dd, _ = cKDTree(cc[:, ::-1]).query(s["corners"])
        assert np.sqrt(np.mean(ours ** 2)) <= np.sqrt(np.mean(dd ** 2))


def test_detector_survives_blur_and_noise():
    s = C.sim_checkerboard((9, 6), 20.0, K_TRUE, D_TRUE, POSES[1], SHAPE, supersample=4, blur_sigma=1.0,
                           noise_sigma=0.02, seed=3)
    e = np.linalg.norm(C.find_checkerboard_corners(s["image"], (9, 6)) - s["corners"], axis=1)
    assert np.sqrt(np.mean(e ** 2)) < 0.1


def test_detector_is_fail_closed():
    with pytest.raises(ValueError):
        C.find_checkerboard_corners(np.full((120, 160), 0.5), (9, 6))
    off = _pose(0.0, 0.0, 0.0, (150, -50, 520))                          # 板の右半分が画像の外
    s = C.sim_checkerboard((9, 6), 20.0, K_TRUE, D_TRUE, off, SHAPE, supersample=2)
    assert not s["visible"]
    with pytest.raises(ValueError):
        C.find_checkerboard_corners(s["image"], (9, 6))
    with pytest.raises(ValueError):
        C.find_checkerboard_corners(np.full((20, 20), np.nan), (3, 3))


# --------------------------------------------------------------------------- 単眼の校正
def test_lm_recovers_the_truth_from_exact_corners_where_zhang_does_not():
    cal = C.camera_calibration_lm(OBJ, [_proj(P) for P in POSES])
    for k, v in zip(("fx", "fy", "cx", "cy"), (800.0, 790.0, 319.5, 241.0)):
        assert cal[k] == pytest.approx(v, rel=1e-9)
    assert np.allclose(cal["dist"], D_TRUE, atol=1e-9)
    assert cal["reproj_rms"] < 1e-9 and cal["converged"]
    assert abs(cal["init"]["fx"] / 800.0 - 1) > 0.01                     # Zhang の閉形式は歪みで 1 % 以上ずれる
    assert len(cal["poses"]) == len(POSES)
    for P, Q in zip(POSES, cal["poses"]):
        assert np.allclose(P, Q, atol=1e-7)


def test_lm_agrees_with_opencv_calibratecamera_on_noisy_corners():
    cv2 = pytest.importorskip("cv2")
    rng = np.random.default_rng(1)
    # OpenCV は float32 の点を受けるので、同じ丸めを通した点を両方に渡す / same float32-rounded input
    ip = [(_proj(P) + rng.normal(0, 0.1, (len(OBJ), 2))).astype(np.float32).astype(float) for P in POSES]
    cal = C.camera_calibration_lm(OBJ, ip)
    rms, Kc, dc, _, _ = cv2.calibrateCamera([OBJ3.astype(np.float32)] * len(ip),
                                            [p[:, ::-1].astype(np.float32).reshape(-1, 1, 2) for p in ip],
                                            (SHAPE[1], SHAPE[0]), None, None,
                                            criteria=(cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 500, 1e-15))
    # 同じ極小: 費用は OpenCV 以下(解き方の止め方の差だけ)、変数の差は推定の標準偏差の 1 % 未満
    assert cal["reproj_rms"] <= rms * (1 + 1e-7)
    ours = [cal["fx"], cal["fy"], cal["cx"], cal["cy"]] + list(cal["dist"])
    theirs = [Kc[0, 0], Kc[1, 1], Kc[0, 2], Kc[1, 2]] + list(dc.ravel()[[0, 1, 2, 3, 4]])
    std = [cal["param_std"][n] for n in cal["param_names"]]
    assert np.all(np.abs(np.subtract(ours, theirs)) < 0.01 * np.asarray(std)), (ours, theirs, std)


def test_covariance_predicts_the_monte_carlo_scatter():
    """σ = 0.2 px で 200 本: 予測の標準偏差と実測の標準偏差が 15 % 以内(fx, fy, cx, cy, k1)。"""
    names = ("fx", "fy", "cx", "cy")
    est, pred = [], None
    for k in range(200):
        rng = np.random.default_rng(k)
        c = C.camera_calibration_lm(OBJ, [_proj(P) + rng.normal(0, 0.2, (len(OBJ), 2)) for P in POSES])
        est.append([c[n] for n in names] + [c["dist"][0]])
        if pred is None:
            pred = [c["param_std"][n] for n in names] + [c["param_std"]["k1"]]
            assert c["sigma_px"] == pytest.approx(0.2, rel=0.1)
    emp = np.std(np.asarray(est), axis=0, ddof=1)
    assert np.all(np.abs(np.asarray(pred) / emp - 1) < 0.15), (pred, emp)


def test_dist_model_none_keeps_distortion_at_zero():
    cal = C.camera_calibration_lm(OBJ, [_proj(P, d=np.zeros(5)) for P in POSES], dist_model="none")
    assert np.all(cal["dist"] == 0.0) and cal["fx"] == pytest.approx(800.0, rel=1e-9)
    assert cal["param_std"]["k1"] == 0.0


@pytest.mark.parametrize("bad", [
    dict(image_points_list=[_proj(P) for P in POSES[:2]]),
    dict(image_points_list=[_proj(P)[:-1] for P in POSES]),
    dict(image_points_list=[np.full((54, 2), np.nan)] * 3),
    dict(image_points_list=[_proj(P) for P in POSES], dist_model="fisheye"),
    dict(image_points_list=np.zeros((54, 2))),
])
def test_calibration_is_fail_closed(bad):
    with pytest.raises(ValueError):
        C.camera_calibration_lm(OBJ, **bad)


# --------------------------------------------------------------------------- ステレオ
R_REL = camera.rodrigues([0.02, -0.1, 0.01])
T_REL = np.array([-120.0, 2.0, 5.0])
K2 = np.array([[780.0, 0, 325.0], [0, 782.0, 238.0], [0, 0, 1.0]])
D2 = np.array([-0.15, 0.03, 0.0, 0.0005, 0.0])


def _right(P):
    Q = np.eye(4)
    Q[:3, :3], Q[:3, 3] = R_REL @ P[:3, :3], R_REL @ P[:3, 3] + T_REL
    return _proj(Q, K2, D2)


def test_stereo_recovers_the_relative_pose_exactly():
    st = C.stereo_calibration_lm(OBJ, [_proj(P) for P in POSES], [_right(P) for P in POSES])
    assert np.abs(st["R"] - R_REL).max() < 1e-9 and np.allclose(st["T"], T_REL, atol=1e-7)
    assert np.allclose(st["K2"], K2, atol=1e-6) and st["reproj_rms"] < 1e-9
    # 極線の拘束: 真の対応で x2ᵀ F x1 = 0
    u1 = np.column_stack([_proj(POSES[0], d=np.zeros(5))[:, ::-1], np.ones(len(OBJ))])
    Q = np.eye(4)
    Q[:3, :3], Q[:3, 3] = R_REL @ POSES[0][:3, :3], R_REL @ POSES[0][:3, 3] + T_REL
    u2 = np.column_stack([_proj(Q, K2, np.zeros(5))[:, ::-1], np.ones(len(OBJ))])
    lines = u1 @ st["F"].T                                               # 右画像の極線 / epipolar lines
    dist_px = np.abs(np.sum(u2 * lines, 1)) / np.hypot(lines[:, 0], lines[:, 1])
    assert dist_px.max() < 1e-6


def test_stereo_agrees_with_opencv_stereocalibrate():
    cv2 = pytest.importorskip("cv2")
    rng = np.random.default_rng(5)
    L = [(_proj(P) + rng.normal(0, 0.1, (len(OBJ), 2))).astype(np.float32).astype(float) for P in POSES]
    R = [(_right(P) + rng.normal(0, 0.1, (len(OBJ), 2))).astype(np.float32).astype(float) for P in POSES]
    st = C.stereo_calibration_lm(OBJ, L, R)
    f = [p[:, ::-1].astype(np.float32).reshape(-1, 1, 2) for p in L]
    g = [p[:, ::-1].astype(np.float32).reshape(-1, 1, 2) for p in R]
    op = [OBJ3.astype(np.float32)] * len(L)
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 500, 1e-15)
    _, K1c, d1c, _, _ = cv2.calibrateCamera(op, f, (SHAPE[1], SHAPE[0]), None, None, criteria=crit)
    _, K2c, d2c, _, _ = cv2.calibrateCamera(op, g, (SHAPE[1], SHAPE[0]), None, None, criteria=crit)
    rs = cv2.stereoCalibrate(op, f, g, K1c, d1c, K2c, d2c, (SHAPE[1], SHAPE[0]), flags=0, criteria=crit)
    assert st["reproj_rms"] <= rs[0] * (1 + 1e-7)                      # 費用は OpenCV 以下
    dang = np.linalg.norm(camera.rotation_log(st["R"] @ rs[5].T))
    assert dang < 0.01 * np.linalg.norm(st["rel_std"][:3])            # 回転の差は標準偏差の 1 % 未満
    assert np.all(np.abs(st["T"] - rs[6].ravel()) < 0.01 * st["rel_std"][3:])


# --------------------------------------------------------------------------- 真値つきの地図
def test_error_map_closed_forms():
    zero = C.calibration_error_map({"K": K_TRUE, "dist": D_TRUE}, K_TRUE, D_TRUE, SHAPE, depth=500.0)
    assert zero["max_px"] < 1e-9 and zero["max_3d_mm"] < 1e-9
    Kd = K_TRUE.copy()
    Kd[0, 2] += 1.5
    m = C.calibration_error_map({"K": Kd, "dist": np.zeros(5)}, K_TRUE, np.zeros(5), SHAPE, depth=500.0,
                                remove_rotation=False)
    assert np.allclose(m["dx_px"], 1.5, atol=1e-9) and np.allclose(m["dy_px"], 0.0, atol=1e-9)
    assert np.allclose(m["error_3d_mm"], 1.5 * 500.0 / 800.0, atol=1e-9)
    # 主点のずれの大部分はカメラの向きのずれと同じ形: 回して除くと 1/10 未満、回した角度 ≈ atan(δ/fx)
    r = C.calibration_error_map({"K": Kd, "dist": np.zeros(5)}, K_TRUE, np.zeros(5), SHAPE, depth=500.0)
    assert r["raw_rms_px"] == pytest.approx(1.5, abs=1e-9) and r["rms_px"] < 0.1 * 1.5
    assert r["rotation_removed_deg"] == pytest.approx(np.degrees(np.arctan(1.5 / 800.0)), rel=0.1)
    k1 = C.calibration_error_map({"K": K_TRUE, "dist": [-0.2, 0, 0, 0, 0]}, K_TRUE, np.zeros(5), SHAPE)
    corner, centre = k1["reproj_error_px"][0, 0], k1["reproj_error_px"].min()
    assert corner > 10 * centre                                         # 半径歪みの誤差は隅で大きい


@pytest.mark.parametrize(("remove_rotation", "rel"), [(False, 0.1), (True, 0.25)])
def test_uncertainty_map_matches_monte_carlo_error_map(remove_rotation, rel):
    """6 視点・σ = 0.2 px・k1k2p1p2: 共分散を写した地図の平均 = 真値つきの誤差の地図の rms の平均。

    実測(80 本): 回さない 6.42 / 6.39 px、回して除く 1.54 / 1.85 px(線形の予測は回転の当てはめの非線形と
    推定の偏りの分だけ小さめ)。★k3 も自由にすると、板の写っていない隅の外挿で線形の予測が実測の 3 倍に
    なる(隅 160 px / 55 px)—— この地図は「板の写っている範囲の近く」で信じる物で、門もその設定で見る。"""
    errs, um = [], None
    for k in range(80):
        rng = np.random.default_rng(300 + k)
        c = C.camera_calibration_lm(OBJ, [_proj(P) + rng.normal(0, 0.2, (len(OBJ), 2)) for P in POSES],
                                    dist_model="k1k2p1p2")
        if um is None:
            um = C.calibration_uncertainty_map(c, SHAPE, step=32, remove_rotation=remove_rotation)
        m = C.calibration_error_map(c, K_TRUE, D_TRUE, SHAPE, step=32, remove_rotation=remove_rotation)
        errs.append(np.stack([m["dx_px"], m["dy_px"]]))
    rms_map = np.sqrt(np.mean(np.sum(np.asarray(errs) ** 2, axis=1), axis=0))
    assert um["mean_px"] == pytest.approx(rms_map.mean(), rel=rel)
    # 端ほど大きい(板の写っていない所を歪みの多項式が外挿する)
    assert um["std_px"][0, 0] > um["std_px"][um["std_px"].shape[0] // 2, um["std_px"].shape[1] // 2]
    with pytest.raises(ValueError):
        C.calibration_uncertainty_map({"K": K_TRUE, "dist": D_TRUE}, SHAPE)


def test_next_pose_recommendation_beats_the_worst_candidate_in_monte_carlo():
    """板を中心にしか置いていない 4 枚に、候補 6 姿勢(中心・遠い中心・4 隅)。推薦を足した校正の実際の誤差は
    最下位の候補を足した校正より小さい(30 本、2 標準誤差の差)。"""
    sig = 0.2
    base = [_place(0.3, 0, 0, 320, 240, 480), _place(-0.3, 0, 0.05, 320, 240, 500),
            _place(0.2, 0.2, -0.05, 320, 240, 460), _place(-0.15, -0.25, 0.1, 320, 240, 490)]
    cands = [_place(0, 0, 0, 320, 240, 480), _place(0, 0, 0, 320, 240, 1100),
             _place(0.15, 0.15, 0, 175, 120, 560), _place(-0.15, 0.15, 0, 470, 370, 560),
             _place(0.15, -0.15, 0, 470, 115, 560), _place(-0.15, -0.15, 0, 170, 365, 560),
             _place(0, 0, 0, 900, 240, 480)]                              # 最後は画像の外
    rng = np.random.default_rng(0)
    cal = C.camera_calibration_lm(OBJ, [_proj(P) + rng.normal(0, sig, (54, 2)) for P in base],
                                  dist_model="k1k2p1p2")
    nx = C.calibration_next_pose(cal, cands, SHAPE)
    assert nx["visible"][-1] is False and nx["scores"][-1] == float("inf")
    assert nx["best_index"] in (2, 3, 4, 5) and nx["improvement"] > 0
    worst = max((i for i, v in enumerate(nx["visible"]) if v), key=lambda i: nx["scores"][i])
    assert worst == 1                                                    # 遠くて小さい板
    err = {nx["best_index"]: [], worst: []}
    for k in range(30):
        r = np.random.default_rng(100 + k)
        obs = [_proj(P) + r.normal(0, sig, (54, 2)) for P in base]
        for i in err:
            c = C.camera_calibration_lm(OBJ, obs + [_proj(cands[i]) + r.normal(0, sig, (54, 2))],
                                        dist_model="k1k2p1p2")
            err[i].append(C.calibration_error_map(c, K_TRUE, D_TRUE, SHAPE)["reproj_error_px"].mean())
    b, w = np.asarray(err[nx["best_index"]]), np.asarray(err[worst])
    se = np.sqrt(b.var(ddof=1) / len(b) + w.var(ddof=1) / len(w))
    assert w.mean() - b.mean() > 2 * se, (b.mean(), w.mean(), se)


def test_next_pose_is_fail_closed():
    cal = C.camera_calibration_lm(OBJ, [_proj(P) for P in POSES])
    with pytest.raises(ValueError):
        C.calibration_next_pose(cal, [], SHAPE, sigma_px=0.1)
    with pytest.raises(ValueError):
        C.calibration_next_pose(cal, [np.eye(3)], SHAPE, sigma_px=0.1)
    with pytest.raises(ValueError):
        C.calibration_next_pose(cal, [_place(0, 0, 0, 2000, 240, 480)], SHAPE, sigma_px=0.1)
    with pytest.raises(ValueError):
        C.calibration_next_pose({"K": K_TRUE, "dist": D_TRUE}, [POSES[0]], SHAPE)


# --------------------------------------------------------------------------- 画像から校正まで
def test_image_to_calibration_end_to_end(renders):
    """描画した 3 枚 + 角の検出 → LM: fx の誤差は共分散の 4 標準偏差以内(3 枚なので広い)。"""
    more = [C.sim_checkerboard((9, 6), 20.0, K_TRUE, D_TRUE, P, SHAPE, supersample=6) for P in POSES[3:]]
    ip = [C.find_checkerboard_corners(s["image"], (9, 6)) for s in list(renders) + more]
    cal = C.camera_calibration_lm(OBJ, ip, dist_model="k1k2p1p2")
    for k, v in zip(("fx", "fy", "cx", "cy"), (800.0, 790.0, 319.5, 241.0)):
        assert abs(cal[k] - v) < 4 * cal["param_std"][k] + 1e-6, (k, cal[k], cal["param_std"][k])
    assert cal["reproj_rms"] < 0.06
