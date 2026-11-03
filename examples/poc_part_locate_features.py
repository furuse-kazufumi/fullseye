# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_part_locate_features — 散らかった台の上の部品を、特徴照合 + ホモグラフィで位置決めする(真値つき)。

    py -3.11 examples/poc_part_locate_features.py

【この例が示すこと】
寸法表から描いた板金部品(穴 4・長穴 1・面取り・刻印)を、既知の姿勢(回転 37 度・0.85 倍・わずかな遠近・
照明 0.8 倍・ぼけ・雑音)で散らかった背景へ置き、テンプレート(部品の画像)から位置・回転・倍率を推定する。

【グラウンドトゥルース(すべて assert で落とす)】
1. ``features_sift`` → ``features_match`` → ``ransac_homography`` の H が、合成に使った真の H と
   部品の 4 隅で 1 px 未満で一致し、中心の位置の誤差 < 0.05 mm(1 px = 0.1 mm)、回転の誤差 < 0.2 度。
2. ``features_orb`` でも 4 隅誤差 < 2 px。
3. ★既存の ``features.match_keypoints``(Harris + 正規化パッチ、スケール・回転不変ではない)+
   ``mosaic.proj_match_points_ransac`` では 37 度回転で外す(4 隅誤差 > 10 px か合意なし)—— 新しい op が要る理由。
4. 部品のテンプレートで ``features_accuracy_table`` を回すと、どの条件で壊れるかが表で出る
   (identity の照合精度 1.0、ぼけ σ=4 で 4 隅誤差が identity より大きい)。
5. 重なり 80 px の 2 枚の貼り合わせ。★8 自由度の射影は正しい組 9 つに合うのに帯の外へ外挿して
   4 隅誤差 > 3 px、物理に合わせた並進の模型では < 0.2 px。既存の ``mosaic.gen_projective_mosaic`` で
   貼り合わせた絵と真の絵の差の rms が撮像の雑音(σ=0.01)の 1.5 倍未満。

【読み方】各節は「真値 / 推定 / 差」。PASS 行が出れば全部通っている。
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import featmatch as fm  # noqa: E402
import features  # noqa: E402
import mosaic  # noqa: E402

MM_PER_PX = 0.1

#: 部品の寸法表 [mm](板 28 × 18、穴 4、長穴 1、面取り 3、刻印 5 文字ぶんの矩形)
PART = {
    "plate": (28.0, 18.0),
    "chamfer": 3.0,
    "holes": [(4.0, 4.0, 1.6), (24.0, 4.0, 1.6), (4.0, 14.0, 1.1), (19.0, 13.0, 2.2)],
    "slot": (9.0, 7.5, 16.0, 7.5, 1.2),                  # (x0, y0, x1, y1, 半幅)
    "marks": [(9.0 + 1.6 * k, 12.0, 1.0, 2.2) for k in range(5)],   # (x, y, 幅, 高さ)
}


def render_part(ss=4):
    """寸法表から部品を描く(ss 倍で描いて面積平均で縮める = 縁の部分被覆)。→ (反射率, 被覆)。"""
    W, H = PART["plate"]
    pw, ph = int(round(W / MM_PER_PX)), int(round(H / MM_PER_PX))
    yy, xx = np.mgrid[0:ph * ss, 0:pw * ss].astype(float)
    x = (xx + 0.5) / ss * MM_PER_PX
    y = (yy + 0.5) / ss * MM_PER_PX
    c = PART["chamfer"]
    plate = (x >= 0) & (x <= W) & (y >= 0) & (y <= H) & (x + y >= c) & ((W - x) + y >= c)
    refl = np.where(plate, 0.72, 0.0)
    rng = np.random.default_rng(5)
    tex = ndimage.gaussian_filter(rng.normal(0, 1, refl.shape), 3.0 * ss)
    refl = refl + plate * 0.05 * tex / tex.std()                     # 加工目
    for hx, hy, r in PART["holes"]:
        refl[(x - hx) ** 2 + (y - hy) ** 2 <= r * r] = 0.12
    x0, y0, x1, y1, hw = PART["slot"]
    t = np.clip(((x - x0) * (x1 - x0) + (y - y0) * (y1 - y0)) / ((x1 - x0) ** 2 + (y1 - y0) ** 2), 0, 1)
    refl[np.hypot(x - (x0 + t * (x1 - x0)), y - (y0 + t * (y1 - y0))) <= hw] = 0.18
    for mx, my, mw, mh in PART["marks"]:
        refl[(x >= mx) & (x <= mx + mw) & (y >= my) & (y <= my + mh)] = 0.42
    refl = refl.reshape(ph, ss, pw, ss).mean((1, 3))
    cov = plate.astype(float).reshape(ph, ss, pw, ss).mean((1, 3))
    return refl, cov


def place(template, cover, H, shape, background, gain=0.8, blur=0.7, noise=0.015, seed=0):
    """テンプレートを H で背景へ置き、照明・ぼけ・雑音を足す。"""
    pw, _ = fm.warp_homography(template, H, out_shape=shape, order=3)
    cw, _ = fm.warp_homography(cover, H, out_shape=shape, order=1)
    cw = np.clip(cw, 0, 1)
    img = background * (1 - cw) + np.clip(pw, 0, 1) * cw
    img = ndimage.gaussian_filter(gain * img, blur)
    img = img + np.random.default_rng(seed).normal(0, noise, img.shape)
    return np.clip(img, 0, 1)


def pose_from_h(H, center):
    """中心の写る位置と、中心まわりの回転・倍率(H の線形部を中心で微分)。"""
    c2 = fm._apply_h(H, center[None])[0]
    e = 1.0
    dx = fm._apply_h(H, (center + [e, 0])[None])[0] - c2
    dy = fm._apply_h(H, (center + [0, e])[None])[0] - c2
    ang = math.degrees(math.atan2(dx[1] - dy[0], dx[0] + dy[1]))
    scale = math.sqrt(abs(dx[0] * dy[1] - dx[1] * dy[0]))
    return c2, ang, scale


def main():
    tmpl, cov = render_part()
    tmpl_full = tmpl * cov + 0.25 * (1 - cov)                      # テンプレートの背景は一様(台の上で撮った見本)
    print("部品のテンプレート %s px(%.1f × %.1f mm、1 px = %.1f mm)"
          % (tmpl.shape, tmpl.shape[1] * MM_PER_PX, tmpl.shape[0] * MM_PER_PX, MM_PER_PX))
    shape = (360, 480)
    bg = 0.2 + 0.3 * fm.synthetic_scene(shape, seed=11)
    ph, pw = tmpl.shape
    center = np.array([(pw - 1) / 2.0, (ph - 1) / 2.0])
    th = math.radians(37.0)
    s = 0.85
    T1 = np.array([[1, 0, -center[0]], [0, 1, -center[1]], [0, 0, 1.0]])
    RS = np.array([[s * math.cos(th), -s * math.sin(th), 0], [s * math.sin(th), s * math.cos(th), 0], [0, 0, 1.0]])
    P = np.array([[1, 0, 0], [0, 1, 0], [1e-4, -5e-5, 1.0]])
    T2 = np.array([[1, 0, 270.0], [0, 1, 190.0], [0, 0, 1.0]])
    H_true = T2 @ P @ RS @ T1
    scene = place(tmpl, cov, H_true, shape, bg)
    c_true, a_true, s_true = pose_from_h(H_true, center)
    corners = (pw, ph)

    print("\n1. SIFT で位置決め")
    ft = fm.features_sift(tmpl_full)
    fs_ = fm.features_sift(scene)
    m = fm.features_match(ft, fs_)
    h = fm.ransac_homography(m)
    ce = fm.corner_error(h["H"], H_true, (ph, pw))
    c_est, a_est, s_est = pose_from_h(h["H"], center)
    dpos = np.linalg.norm(c_est - c_true) * MM_PER_PX
    print("   特徴点 テンプレート %d / 場面 %d、照合 %d、内れ値 %d" % (len(ft["xy"]), len(fs_["xy"]),
                                                       len(m["idx"]), h["n_inliers"]))
    print("   中心 真値 (%.2f, %.2f) px / 推定 (%.2f, %.2f) px / 差 %.3f mm" % (*c_true, *c_est, dpos))
    print("   回転 真値 %.3f 度 / 推定 %.3f 度 / 差 %.3f 度" % (a_true, a_est, abs(a_est - a_true)))
    print("   倍率 真値 %.4f / 推定 %.4f" % (s_true, s_est))
    print("   部品の 4 隅誤差 %.3f px" % ce)
    # 図: テンプレート / 場面 / 推定の H で場面へ写したテンプレートの輪郭(真の H との差は 4 隅誤差の数字)
    cov_est, _ = fm.warp_homography(cov, h["H"], out_shape=shape, order=1)
    cov_true, _ = fm.warp_homography(cov, H_true, out_shape=shape, order=1)
    overlay = np.stack([np.clip(scene + 0.6 * (np.abs(np.gradient(cov_est)[0]) + np.abs(np.gradient(cov_est)[1]) > 0.2), 0, 1),
                        scene, np.clip(scene + 0.6 * (np.abs(np.gradient(cov_true)[0]) + np.abs(np.gradient(cov_true)[1]) > 0.2), 0, 1)],
                       axis=-1)
    figs.save_grid("part_locate_sift", [tmpl_full, scene, overlay],
                   captions=["template (0.1 mm/px)", "scene: rot 37 deg, x0.85", "edges: est. red + true blue (magenta = agree)"],
                   gray=[True, True, False],
                   caption="SIFT -> features_match -> ransac_homography: corner error %.3f px" % ce)
    assert ce < 1.0 and dpos < 0.05 and abs(a_est - a_true) < 0.2 and abs(s_est - s_true) < 0.005

    print("\n2. ORB で位置決め")
    mo = fm.features_match(fm.features_orb(tmpl_full), fm.features_orb(scene))
    ho = fm.ransac_homography(mo)
    ceo = fm.corner_error(ho["H"], H_true, (ph, pw))
    print("   照合 %d、内れ値 %d、4 隅誤差 %.3f px" % (len(mo["idx"]), ho["n_inliers"], ceo))
    assert ceo < 2.0

    print("\n3. ★既存の Harris + パッチ記述子(スケール・回転不変ではない)では")
    p1, p2 = features.match_keypoints(tmpl_full, scene, detector="harris")
    if len(p1) >= 4:
        r = mosaic.proj_match_points_ransac(p1[:, ::-1], p2[:, ::-1], thresh=2.0, iters=2000)
        Hb = r["H"]                                       # (row, col) の点で推定しても、H 自体は (x, y) に掛かる
        ceb = fm.corner_error(Hb, H_true, (ph, pw)) if r["num_inliers"] >= 4 else float("inf")
        print("   照合 %d、内れ値 %d、4 隅誤差 %s px" % (len(p1), r["num_inliers"],
                                                "%.1f" % ceb if np.isfinite(ceb) else "合意なし"))
    else:
        ceb = float("inf")
        print("   照合 %d 組 —— ホモグラフィを推定できない" % len(p1))
    assert ceb > 10.0
    print("   → 37 度の回転と 0.85 倍で外す。SIFT は %.3f px。" % ce)

    print("\n4. 部品のテンプレートで、どの条件で壊れるか(features_accuracy_table、SIFT)")
    T = fm.features_accuracy_table(tmpl_full, detector="sift",
                                   conditions=["identity", "rotate_45", "scale_0.5", "scale_2.0", "perspective_high",
                                               "gain_0.5", "blur_2", "blur_4", "noise_0.05", "noise_0.10"])
    print("   %-18s %6s %6s %6s %8s" % ("条件", "再現率", "精度", "照合数", "4隅[px]"))
    for row in T["rows"]:
        e = row["corner_error_px"]
        print("   %-18s %6.2f %6.2f %6d %8s" % (row["condition"], row["repeatability"], row["precision"],
                                              row["n_matches"], "失敗" if e is None else "%.3f" % e))
    rows = {r["condition"]: r for r in T["rows"]}
    assert rows["identity"]["precision"] == 1.0 and rows["identity"]["corner_error_px"] < 1e-6
    e4 = rows["blur_4"]["corner_error_px"]
    assert e4 is None or e4 > rows["identity"]["corner_error_px"]
    print("   最も悪い条件: %s" % T["worst"])
    figs.save_table("part_locate_accuracy_table", ["condition", "repeatability", "precision", "matches",
                                                   "corner_err_px"],
                    [[r["condition"], "%.2f" % r["repeatability"], "%.2f" % r["precision"], str(r["n_matches"]),
                      "fail" if r["corner_error_px"] is None else "%.3f" % r["corner_error_px"]] for r in T["rows"]],
                    title="features_accuracy_table (SIFT, part template)")

    print("\n5. 貼り合わせ(XY ステージで横へ 140 px 動かした 2 枚、既存の mosaic.gen_projective_mosaic を再利用)")
    wide = 0.15 + 0.7 * fm.synthetic_scene((200, 360), seed=21)
    rng = np.random.default_rng(3)
    a = wide[:, :220] + rng.normal(0, 0.01, (200, 220))           # 重なり 80 px、2 枚は別々に撮った雑音 σ=0.01
    b = wide[:, 140:] + rng.normal(0, 0.01, (200, 220))
    mab = fm.features_match(fm.features_sift(a), fm.features_sift(b))
    H_t = np.array([[1, 0, -140.0], [0, 1, 0], [0, 0, 1.0]])
    print("   照合 %d 組(正しい組は重なりの 80 px の帯にしか無い)" % len(mab["idx"]))
    print("   %-12s %6s %22s %12s" % ("模型", "内れ値", "原点の並進 [px]", "4 隅誤差[px]"))
    errs = {}
    for model in ("projective", "affine", "similarity", "translation"):
        hm = fm.ransac_homography(mab, model=model, min_inliers=4)
        errs[model] = fm.corner_error(hm["H"], H_t, a.shape)
        print("   %-12s %6d %10.3f %10.3f %12.3f" % (model, hm["n_inliers"], hm["H"][0, 2], hm["H"][1, 2],
                                                     errs[model]))
        if model == "translation":
            hb = hm
    # ★8 自由度の射影は帯の中の組には合うのに、帯の外へ外挿すると大きく外す(この対では 4 隅誤差 9 px 超)。
    #   物理の模型(ステージの並進)に合わせて自由度を落とすと 0.1 px 未満。
    assert errs["projective"] > 3.0 and errs["translation"] < 0.2
    H_ba = np.linalg.inv(hb["H"])                                 # b → a の座標
    canvas = mosaic.gen_projective_mosaic([a, b], [np.eye(3), H_ba], out_shape=(400, 720))
    off = (100, 180)                                              # gen_projective_mosaic の置き場所(高さ・幅の 1/4)
    got = canvas[off[0]:off[0] + 200, off[1]:off[1] + 360]
    inner = (slice(4, -4), slice(4, -4))
    rms = float(np.sqrt(np.mean((got - wide)[inner] ** 2)))
    print("   並進の模型で貼り合わせた絵と真の絵の差 rms %.4f(撮像の雑音そのものが σ = 0.0100)" % rms)
    # 位置がずれていれば模様の差が雑音に上乗せされる。雑音の床の 1.5 倍未満 = 位置の誤差は雑音に埋もれる大きさ
    assert rms < 0.015
    figs.save_table("part_locate_stitch_models", ["model", "corner_err_px"],
                    [[k, "%.3f" % v] for k, v in errs.items()],
                    title="stitch model", caption="80 px overlap, 9 true pairs: corner error per model")

    for name, arr in (("scene", scene), ("canvas", got)):
        assert np.isfinite(arr).all() and float(np.ptp(arr)) > 0.0, name
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
