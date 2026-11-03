# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""machine_vision_tour — 工業用ビジョンの定番 47 op を、答えの分かる入力で 1 周する

    py -3.11 examples/machine_vision_tour.py [--fig out.png]

【この例が示すこと】
ステレオ・平面への平行化・歪みの変換・古典形態学・カルマン背景・分類器・文字行の op を、真値を
自分で決めた合成データに掛ける。各段で答えを閉形式か独立の計算と比べ、合わなければ exit 1。
op は既存の型(image2d / mask / table / keypoints)でつながるので、視差 → 点群、校正の写像 →
map_image、点列 → B スプライン → nurbs_curve のように族をまたいで組める。

EXTEND: 実写のステレオは先に平行化してから binocular_disparity_ms へ渡す。distance は左右一致で
落とした画素が NaN になるので、後段で valid を必ず見る。背景モデルは照明の変化が遅いほど
process_noise を小さくする。
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fullseye as fs  # noqa: E402

L = fs.ledger


def _texture(shape, seed=0, sigma=1.0):
    t = ndimage.gaussian_filter(np.random.default_rng(seed).random(shape), sigma)
    return (t - t.min()) / (t.max() - t.min())


def stereo_section():
    """視差 → 距離 → 点群。"""
    right = _texture((60, 120), 1)
    d = np.full((60, 120), 8.0)
    rr, cc = np.mgrid[0:60, 0:120].astype(float)
    left = ndimage.map_coordinates(right, [rr, cc - d], order=3, mode="nearest")
    res = L.binocular_disparity_ms(left, right, max_disp=14)
    far = L.binocular_distance_ms(left, right, 500.0, 0.2, max_disp=14)
    pts = L.reconstruct_surface_stereo(res["disparity"], 500.0, 0.2, 60.0, 30.0)
    z = float(np.nanmedian(far["distance"]))
    print("stereo: valid %d px, median Z %.3f (true %.3f), points %d"
          % (res["valid"].sum(), z, 500.0 * 0.2 / 8.0, len(pts)))
    assert res["valid"].sum() > 3000 and abs(z - 12.5) < 0.2 and len(pts) == res["valid"].sum()
    return left, res["disparity"]


def resample_section():
    """写像・平行化・歪み・回転矩形。"""
    im = _texture((80, 100), 2, 2.0)
    rr, cc = np.mgrid[0:80, 0:100].astype(float)
    shifted = L.map_image(im, {"row_map": rr, "col_map": cc + 3.0})
    assert np.allclose(shifted[:, :90], im[:, 3:93])
    cam = {"fx": 200.0, "fy": 200.0, "cx": 50.0, "cy": 40.0}
    pose = np.eye(4)
    pose[:3, 3] = [-0.25, -0.2, 1.0]                 # 正面視: 平行化は相似の拡大
    top = L.rectify_to_world_plane(im, cam, pose, 100, 80, 0.005)
    assert np.allclose(top[10:70, 10:90], im[10:70, 10:90], atol=1e-9)
    cam_in = dict(cam, kappa=-1e-5)
    und = L.change_radial_distortion_image(im, cam_in, dict(cam, kappa=0.0))
    back = L.change_radial_distortion_image(und, dict(cam, kappa=0.0), cam_in)
    rms = float(np.sqrt(np.mean((back[15:65, 15:85] - im[15:65, 15:85]) ** 2)))
    crop = L.crop_rectangle2(0.5 * rr + cc, 40.0, 50.0, 0.0, 10.0, 4.0)
    assert np.allclose(crop[4], 0.5 * 40.0 + np.arange(40, 61))
    print("resample: undistort round trip rms %.4f, crop %s" % (rms, crop.shape))
    assert rms < 0.02
    return im, und


def gray_section():
    """灰色値の計測と検出。"""
    rr, cc = np.mgrid[0:64, 0:64].astype(float)
    blob = np.exp(-((rr - 20.5) ** 2 + (cc - 40.25) ** 2) / (2 * 2.5 ** 2))
    c = L.area_center_gray(blob)
    assert abs(c["row"] - 20.5) < 1e-3 and abs(c["column"] - 40.25) < 1e-3
    angle = L.atan2_image(rr - 32.0, cc - 32.0)
    assert abs(angle[32, 63] - 0.0) < 1e-12 and abs(angle[63, 32] - math.pi / 2) < 1e-12
    hist = L.gray_histo(blob)
    proj = L.gray_projections(blob)
    assert hist["absolute"].sum() == 64 * 64 and int(np.argmax(proj["vertical"])) == 40
    pts = L.points_lepetit(blob, 4, 1, 0.05, 0.05)
    assert len(pts) == 1 and np.hypot(pts[0, 0] - 20.5, pts[0, 1] - 40.25) < 0.3
    line = np.column_stack([np.linspace(20.5, 20.5, 9), np.linspace(36.25, 44.25, 9)])
    prof = L.get_grayval_contour_xld(blob, line)
    assert int(np.argmax(prof)) == 4
    tmpl = _texture((40, 40), 3)
    res = L.find_ncc_models([L.create_ncc_model(tmpl[5:15, 5:15]), L.create_ncc_model(tmpl[25:35, 20:30])],
                            tmpl, 0.9, 4, 4)
    print("gray: center (%.2f, %.2f), lepetit %s, ncc models found %d" % (c["row"], c["column"], pts[0].round(2), res["num"]))
    assert res["num"] == 2
    return blob


def pose_section():
    """円の像から 3-D の円。"""
    cam = {"fx": 400.0, "fy": 400.0, "cx": 64.0, "cy": 48.0}
    center, normal = np.array([0.1, -0.05, 1.0]), np.array([0.3, 0.2, -1.0])
    nz = normal / np.linalg.norm(normal)
    e1 = np.cross(nz, [1.0, 0.0, 0.0])
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(nz, e1)
    t = np.linspace(0, 2 * np.pi, 72, endpoint=False)
    p = center + 0.05 * (np.cos(t)[:, None] * e1 + np.sin(t)[:, None] * e2)
    uv = np.column_stack([400.0 * p[:, 1] / p[:, 2] + 48.0, 400.0 * p[:, 0] / p[:, 2] + 64.0])
    res = L.get_circle_pose(uv, 0.05, cam)
    err = min(np.linalg.norm(c - center) for c in res["center"])
    print("pose: closest center error %.2e" % err)
    assert err < 1e-5


def morphology_section():
    """Golay の組・肥厚・SKIZ・分離の開放。"""
    a = np.zeros((48, 96), bool)
    a[10:38, 8:36] = a[10:38, 60:88] = True
    a[23:25, 36:60] = True
    a[6, 20] = True
    lab = L.opening_seg(a, np.ones((5, 5), bool))
    assert lab.max() == 2
    a[23:25, 36:60] = False
    a[6, 20] = False
    a[20, 20] = False
    pair = L.golay_elements("l", 2)
    hm = L.hit_or_miss_golay(a, "l", 2)
    seq = L.hit_or_miss_seq(a, "i")
    hat = L.morph_hat(a, np.ones((3, 3), bool))
    skiz = L.morph_skiz(a)
    thick = L.thickening_hit_miss(a, L.golay_elements("c")["hit"], L.golay_elements("c")["miss"], 1)
    thick2 = L.thickening_golay(a, "c")
    filled = L.thickening_seq(a, "c")
    print("morph: labels %d, hat %d px, skiz columns %s" % (lab.max(), hat.sum(), np.unique(np.nonzero(skiz)[1])))
    assert pair["hit"].sum() == 4 and hm.sum() > 0 and seq.sum() == 0 and hat[20, 20]
    assert (thick == thick2).all() and skiz.sum() >= 48 and filled.sum() >= a.sum()
    return a, skiz


def curve_section():
    """点列を通る B スプラインを nurbs_curve へ渡す。"""
    t = np.linspace(0, 3, 8)
    q = np.column_stack([30.0 * np.cos(t), 20.0 * np.sin(t)])
    s = L.gen_nurbs_interp(q, 3)
    curve = L.nurbs_curve(s["control_points"], s["weights"], degree=3, knots=s["knots"], n=33)
    print("curve: end point error %.1e" % np.linalg.norm(curve["points"][-1] - q[-1]))
    assert np.allclose(curve["points"][0], q[0]) and np.allclose(curve["points"][-1], q[-1], atol=1e-9)


def tracking_section():
    """カルマンの定常ゲインと背景の更新。"""
    q, r = 0.02, 0.5
    x, cov = np.zeros(1), np.eye(1)
    for _ in range(100):
        step = L.filter_kalman(x, cov, [1.0], 1.0, 1.0, q, r)
        x, cov = step["x"], step["P"]
    pm = (q + math.sqrt(q * q + 4 * q * r)) / 2.0
    assert abs(step["gain"][0, 0] - pm / (pm + r)) < 1e-9
    base = _texture((32, 32), 4, 2.0) * 0.4 + 0.2
    model = L.create_bg_esti(base, 1e-4, 1e-3, 0.15, 0.0)
    frame = base.copy()
    frame[8:16, 8:16] = 0.95
    out = L.run_bg_esti(model, frame)
    model = L.update_bg_esti(out["model"], base + 0.02, ~out["foreground"])
    print("tracking: steady gain %.4f, foreground %d px" % (step["gain"][0, 0], out["foreground"].sum()))
    assert out["foreground"].sum() >= 50
    assert np.abs(L.give_bg_esti(model)[8:16, 8:16] - base[8:16, 8:16]).max() < 1e-12


def classify_section():
    """特徴ベクトルの分類器と語の照合。"""
    rng = np.random.default_rng(0)
    X = np.vstack([rng.normal([0, 0], 1.0, (200, 2)), rng.normal([6, 1], 1.0, (200, 2))])
    y = np.repeat([0, 1], 200)
    gmm = L.train_class_gmm(X, y)
    knn = L.train_class_knn(X, y)
    acc_g = (L.classify_class_gmm(gmm, X)["labels"] == y).mean()
    acc_k = (L.classify_class_knn(knn, X, 5)["labels"] == y).mean()
    post = L.evaluate_class_gmm(gmm, X)["posterior"]
    acc_m = (L.classify_class_mlp(L.train_class_mlp(X, y), X)["labels"] == y).mean()
    acc_s = (L.classify_class_svm(L.train_class_svm(X, y), X)["labels"] == y).mean()
    lex = L.create_lexicon(["bolt", "nut", "washer"])
    assert L.lookup_lexicon(lex, "nut") == 1.0
    sug = L.suggest_lexicon(lex, "wasber")
    print("classify: gmm %.3f knn %.3f mlp %.3f svm %.3f, suggest %s" % (acc_g, acc_k, acc_m, acc_s, sug["suggestion"]))
    assert min(acc_g, acc_k, acc_m, acc_s) > 0.97 and np.allclose(post.sum(axis=1), 1.0) and sug["distance"] == 1


def text_section():
    """文字行の傾き・斜体角・字の切り出し。"""
    im = np.ones((30, 100))
    for x in range(8, 88, 12):
        im[8:22, x:x + 6] = 0.0
    lab = L.segment_characters(im)
    kept = L.select_characters(lab)
    tilt = L.text_line_orientation(im < 0.5)
    slant = L.text_line_slant(im < 0.5)
    print("text: %d glyphs, tilt %.2f, slant %.2f" % (kept.max(), tilt, slant))
    assert kept.max() == 7 and abs(tilt) < 1.0 and abs(slant) < 1.0
    return im, lab


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    left, disparity = stereo_section()
    im, und = resample_section()
    blob = gray_section()
    pose_section()
    a, skiz = morphology_section()
    curve_section()
    tracking_section()
    classify_section()
    text, lab = text_section()
    if "--fig" in argv:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        path = argv[argv.index("--fig") + 1]
        panels = [("left image", left), ("disparity (NaN = invalid)", disparity), ("distorted input", im),
                  ("undistorted", und), ("gray blob", blob), ("two regions", a), ("SKIZ", skiz), ("glyph labels", lab)]
        fig, axes = plt.subplots(2, 4, figsize=(12, 6))
        for ax, (title, data) in zip(axes.ravel(), panels):
            ax.imshow(np.asarray(data, float), cmap="gray")
            ax.set_title(title, fontsize=10)
            ax.axis("off")
        fig.tight_layout()
        fig.savefig(path, dpi=110)
        plt.close(fig)
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
