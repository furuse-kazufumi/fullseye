# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""真値つきのカメラ校正 —— 画像から K と歪みを詰め、どこで誤るかの地図と、次にどの姿勢で撮れば効くかまで。

Camera calibration with ground truth: from rendered checkerboard images to K and distortion, a map of where
the estimate errs, and which pose to shoot next.

1. 真の K・歪み(樽型 k1 = −0.21)・6 姿勢でチェッカー板を描く(画素を板へ逆に引く描画、4x4 標本)。
2. ``find_checkerboard_corners`` で角を拾い、描画の真値とのずれを数える。
3. Zhang の閉形式(既存 ``camera_calibration``、K だけ)と ``camera_calibration_lm``(K・歪み・姿勢を同時に)を比べる。
4. Fullseye だけの層: 真値と比べた誤差の地図(画像のどこで何 px 誤るか)、共分散を写した不確かさの地図、
   板を中心にしか置いていない 4 枚に「次の 1 枚」を推薦させ、モンテカルロで当たっているかを確かめる。

    PYTHONPATH=. py -3.11 examples/poc_calibration_truth_map.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402

import camera  # noqa: E402
import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402

K_TRUE = np.array([[800.0, 0.0, 319.5], [0.0, 790.0, 241.0], [0.0, 0.0, 1.0]])
D_TRUE = np.array([-0.21, 0.08, 0.0012, -0.0008, 0.0])
SHAPE = (480, 640)
PATTERN, SQUARE = (9, 6), 20.0


def place(rx, ry, rz, uc, vc, Z):
    """板の中心を画素 (col uc, row vc)・奥行き Z [mm] に置く姿勢(板 → カメラ)。"""
    R = camera.rodrigues([rx, ry, rz])
    t = Z * np.array([(uc - K_TRUE[0, 2]) / K_TRUE[0, 0], (vc - K_TRUE[1, 2]) / K_TRUE[1, 1], 1.0]) \
        - R @ np.array([80.0, 50.0, 0.0])
    P = np.eye(4)
    P[:3, :3], P[:3, 3] = R, t
    return P


def project(obj, P):
    s = fs.ledger.sim_checkerboard(PATTERN, SQUARE, K_TRUE, D_TRUE, P, SHAPE, supersample=1)
    return s["corners"]


def main():
    obj = fs.ledger.checkerboard_points(PATTERN, SQUARE)
    poses = [place(0.3, -0.2, 0.05, 300, 220, 520), place(-0.25, 0.3, -0.1, 330, 250, 560),
             place(0.1, 0.35, 0.2, 200, 150, 500), place(-0.35, -0.15, 0.0, 450, 330, 600),
             place(0.2, 0.1, -0.3, 440, 140, 540), place(0.0, -0.4, 0.1, 190, 340, 580)]

    # --- 1-2. 描画と角の検出 / render and detect ----------------------------------------------------
    sims = [fs.ledger.sim_checkerboard(PATTERN, SQUARE, K_TRUE, D_TRUE, P, SHAPE, supersample=4) for P in poses]
    assert all(s["visible"] for s in sims)
    found = [fs.ledger.find_checkerboard_corners(s["image"], PATTERN) for s in sims]
    err = np.concatenate([np.linalg.norm(f - s["corners"], axis=1) for f, s in zip(found, sims)])
    print("corner detection vs rendered truth: rms %.3f px, max %.3f px (%d corners, 6 views)"
          % (np.sqrt(np.mean(err ** 2)), err.max(), len(err)))
    assert np.sqrt(np.mean(err ** 2)) < 0.08

    # --- 3. Zhang の閉形式 vs LM / closed form vs joint refinement -----------------------------------
    zh = fs.ledger.camera_calibration(obj, found)
    cal = fs.ledger.camera_calibration_lm(obj, found, dist_model="k1k2p1p2")
    print("\n%-28s %9s %9s %9s %9s" % ("", "fx", "fy", "cx", "cy"))
    print("%-28s %9.2f %9.2f %9.2f %9.2f" % ("truth", 800.0, 790.0, 319.5, 241.0))
    print("%-28s %9.2f %9.2f %9.2f %9.2f" % ("Zhang closed form (K only)", zh["fx"], zh["fy"], zh["cx"], zh["cy"]))
    print("%-28s %9.2f %9.2f %9.2f %9.2f" % ("LM (K + distortion + poses)", cal["fx"], cal["fy"], cal["cx"], cal["cy"]))
    print("%-28s %9.2f %9.2f %9.2f %9.2f" % ("  1-sigma from covariance", *[cal["param_std"][k] for k in
                                                                            ("fx", "fy", "cx", "cy")]))
    print("k1 %.4f (true -0.21 +- %.4f), reprojection rms %.3f px"
          % (cal["dist"][0], cal["param_std"]["k1"], cal["reproj_rms"]))
    zerr, lerr = abs(zh["fx"] / 800 - 1), abs(cal["fx"] / 800 - 1)
    print("fx error: Zhang %.2f %%, LM %.3f %%" % (100 * zerr, 100 * lerr))
    assert lerr < zerr and lerr < 0.005
    for k, v in (("fx", 800.0), ("fy", 790.0), ("cx", 319.5), ("cy", 241.0)):
        assert abs(cal[k] - v) < 4 * cal["param_std"][k], (k, cal[k])

    # --- 4a. 真値と比べた誤差の地図・不確かさの地図 / error map against the truth, uncertainty map ---------
    em = fs.ledger.calibration_error_map(cal, K_TRUE, D_TRUE, SHAPE, step=16, depth=500.0)
    um = fs.ledger.calibration_uncertainty_map(cal, SHAPE, step=16, depth=500.0)
    h, w = em["reproj_error_px"].shape
    centre = em["reproj_error_px"][h // 3:2 * h // 3, w // 3:2 * w // 3].mean()
    print("\nerror map vs truth: centre third %.3f px, whole image rms %.3f px, max %.3f px at (row, col) = (%.0f, %.0f);"
          " at 500 mm that is %.3f mm" % (centre, em["rms_px"], em["max_px"], *em["max_at"], em["max_3d_mm"]))
    print("uncertainty map (from the covariance, no truth needed): mean %.3f px, max %.3f px at (%.0f, %.0f)"
          % (um["mean_px"], um["max_px"], *um["max_at"]))
    assert em["max_px"] > 3 * centre                       # 隅で大きい / larger in the corners

    # --- 4b. 次の 1 枚 / next view ------------------------------------------------------------------
    sig = 0.2
    base = [place(0.3, 0, 0, 320, 240, 480), place(-0.3, 0, 0.05, 320, 240, 500),
            place(0.2, 0.2, -0.05, 320, 240, 460), place(-0.15, -0.25, 0.1, 320, 240, 490)]
    names = ["centre, frontal", "centre, far (1.1 m)", "top-left", "bottom-right", "top-right", "bottom-left"]
    cands = [place(0, 0, 0, 320, 240, 480), place(0, 0, 0, 320, 240, 1100), place(0.15, 0.15, 0, 175, 120, 560),
             place(-0.15, 0.15, 0, 470, 370, 560), place(0.15, -0.15, 0, 470, 115, 560),
             place(-0.15, -0.15, 0, 170, 365, 560)]
    rng = np.random.default_rng(0)
    c4 = fs.ledger.camera_calibration_lm(obj, [project(obj, P) + rng.normal(0, sig, (len(obj), 2)) for P in base],
                                         dist_model="k1k2p1p2")
    nx = fs.ledger.calibration_next_pose(c4, cands, SHAPE)
    actual = []
    for i in range(len(cands)):
        e = []
        for k in range(15):
            r = np.random.default_rng(100 + k)
            obs = [project(obj, P) + r.normal(0, sig, (len(obj), 2)) for P in base]
            c = fs.ledger.camera_calibration_lm(obj, obs + [project(obj, cands[i]) + r.normal(0, sig, (len(obj), 2))],
                                                dist_model="k1k2p1p2")
            e.append(fs.ledger.calibration_error_map(c, K_TRUE, D_TRUE, SHAPE)["reproj_error_px"].mean())
        actual.append(float(np.mean(e)))
    print("\nnext view after 4 centred views (sigma %.1f px): predicted mean uncertainty now %.2f px" %
          (sig, nx["current_mean_px"]))
    print("%-22s %12s %16s" % ("candidate", "predicted px", "actual error px"))
    for i, n in enumerate(names):
        mark = "  <- recommended" if i == nx["best_index"] else ""
        print("%-22s %12.2f %16.2f%s" % (n, nx["scores"][i], actual[i], mark))
    worst = int(np.argmax(nx["scores"]))
    assert actual[nx["best_index"]] < actual[worst]
    assert nx["best_index"] >= 2                            # 隅のどれか / one of the corners
    # --- 図 / figures --------------------------------------------------------------------------
    # 1) 描画した 1 枚と検出した角(赤)・真の角(青)。2) 誤差の地図(真値つき)と不確かさの地図(共分散から)。
    img = sims[0]["image"]
    over = np.stack([img, img, img], axis=-1)
    for pts, ch in ((found[0], 0), (sims[0]["corners"], 2)):
        rr = np.clip(np.rint(pts[:, 0]).astype(int), 0, SHAPE[0] - 1)
        cc = np.clip(np.rint(pts[:, 1]).astype(int), 0, SHAPE[1] - 1)
        for dr in range(-4, 5):                          # 9 px の十字 / 9-px crosses
            over[np.clip(rr + dr, 0, SHAPE[0] - 1), cc, ch] = 1.0
            over[rr, np.clip(cc + dr, 0, SHAPE[1] - 1), ch] = 1.0
    # 図は細かい格子(2 px おき)で作り直す —— 16 px おきの地図を拡大して見せない
    emap = fs.ledger.calibration_error_map(cal, K_TRUE, D_TRUE, SHAPE, step=2)["reproj_error_px"]
    umap = fs.ledger.calibration_uncertainty_map(cal, SHAPE, step=2)["std_px"]
    for nm, arr in (("image", img), ("error map", emap), ("uncertainty map", umap)):
        assert np.isfinite(arr).all() and float(np.ptp(arr)) > 0.0, nm
    hi = float(max(emap.max(), umap.max()))
    figs.save_grid("calibration_maps", [over, emap, umap],
                   captions=["rendered view 1: detected corners red, truth blue (rms %.3f px)"
                             % np.sqrt(np.mean(err ** 2)),
                             "error vs truth after removing the best rotation [px] (max %.3f)" % emap.max(),
                             "predicted 1-sigma from the covariance [px] (no truth needed)"],
                   ncols=3, gray=[True, False, False], vrange=[None, (0.0, hi), (0.0, hi)],
                   colorbar=[False, True, True], unit="px",
                   caption="camera_calibration_lm on 6 rendered views (k1 = -0.21): where the estimate errs")
    figs.save_table("calibration_next_pose", ["candidate", "predicted px", "actual error px (MC 15)"],
                    [[n + ("  <- recommended" if i == nx["best_index"] else ""), "%.2f" % nx["scores"][i],
                      "%.2f" % actual[i]] for i, n in enumerate(names)],
                    title="next view after 4 centred views (sigma %.1f px)" % sig,
                    caption="calibration_next_pose prediction vs Monte Carlo error against the truth")
    figs.save_plot("calibration_next_pose_scatter",
                   [("candidates", np.asarray(nx["scores"]), np.asarray(actual)),
                    ("y = x", np.array([0.0, max(max(nx["scores"]), max(actual))]),
                     np.array([0.0, max(max(nx["scores"]), max(actual))]))],
                   xlabel="predicted mean uncertainty [px]", ylabel="actual mean error [px]",
                   title="next-view recommendation: predicted vs actual", kinds=["scatter", "line"],
                   styles=[None, "dashed"], colors=["emphasis", "reference"],
                   caption="6 candidate poses; the linear prediction ranks the far centre worst and the corners best")
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("PASS")


if __name__ == "__main__":
    main()
