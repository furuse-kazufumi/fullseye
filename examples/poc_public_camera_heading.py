# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 公共カメラはどこを向いているか ―― 位置しか公開されない固定カメラの向きを、写真そのものから決める

公共の固定カメラ(道路・気象・観光)は**位置**は公開されるが**向き**は無いか粗い(道路の増減方向、id の
ハッシュ、手校正)。向きが無いと写真を地図・DEM・3D 都市に置けない。この PoC は新族 geocam の 7 op で、
位置既知のカメラの (yaw, pitch, roll) を**学習なし**で 2 つの独立な手掛かりから決め、互いに検算する:

* **スカイライン**: カメラ位置から DEM で描いた 360° の稜線(``dem_skyline``)と、写真から動的計画法で
  抜いた空と地形の境界(``skyline_extract``)を照合(``camera_orientation_from_skyline``)。yaw を一周
  探索した残差曲線をそのまま返し、谷が 1 つか複数か(曖昧さ)を隠さない。
* **太陽**: 太陽の見かけの位置は時刻と場所の閉形式(``sun_position``、NOAA)。時刻つきの写真で太陽の
  画素(``sun_pixel_position``)を 2 点以上拾えば、回転は Wahba 問題の SVD 解で一意(``camera_orientation_from_sun``)。

**主張は 1 つだけ**: 真値の姿勢が分かる合成カメラ(合成 DEM + 空 + 雲 + 前景の柱 + 雑音)で、2 経路とも
真値を 0.2° 以内に当て、互いに 0.3° 以内で一致する。対照 = 公開メタデータに近い「道路方向の事前知識」
(真値 ± 15°)と、平地の DEM(スカイラインが全方位で同じ → op が ambiguous を返す)。

図:
1. ``skyline_lock``: 写真 | 抜いた境界(シアン)と推定姿勢で描いた稜線(マゼンタ)| 推定姿勢の空マスク。
2. ``yaw_sweep``: yaw を一周させながら DEM の稜線を写真に重ねる GIF —— 真値で稜線が境界に**噛み合う**瞬間。
3. ``yaw_profile``: yaw ごとの残差曲線(真値の線、2 番目の谷)。山では谷が 1 つ、平地では平ら。
4. ``sun_track``: 一日の太陽の軌跡(推定姿勢で投影)と拾った太陽の画素。
5. ``numbers``: 2 経路と対照の誤差表。

データ: 合成(真値が要るため)。実データ(フィンランド Fintraffic 天候カメラ CC BY 4.0 + NLS 標高、
ノルウェー Statens vegvesen CCTV NLOD + Kartverket DTM10 CC BY 4.0)は次の段で、生画像は commit しない。
走らせ方: ``py -3.11 examples/poc_public_camera_heading.py``(図は ``out/figures/poc_public_camera_heading/``)。
"""
from __future__ import annotations

import calendar
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import fullseye as fs  # noqa: E402
import examplefig as figs  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET", "reduced" if os.environ.get("CI") else "full") == "reduced"
L = fs.ledger
LAT, LON = 35.68, 139.69                               # 合成 DEM の置き場所(北緯 36°、冬の低い太陽が南東の画角に入る)
SHAPE = (240, 320)
K = (280.0, 280.0, 160.0, 120.0)                       # 水平画角 ≈ 59°
TRUE = (150.0, -3.0, 2.0)                              # yaw, pitch, roll [度](南南東: 冬の朝の太陽が入り、稜線がぎざぎざ)
OBS = (170, 120)                                       # DEM 上のカメラのセル(南東の稜線が低い場所)
CELL = 30.0
CYAN, MAGENTA, YELLOW = np.array([0.2, 0.9, 1.0]), np.array([1.0, 0.25, 0.9]), np.array([1.0, 0.9, 0.2])


def _utc(*ymdhms):
    return float(calendar.timegm(ymdhms))


# --------------------------------------------------------------------------- #
# 合成                                                                          #
# --------------------------------------------------------------------------- #
def synthetic_dem(seed=0, n=300):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:n, 0:n]
    dem = np.zeros((n, n))
    for _ in range(25):
        cy, cx = rng.uniform(0, n), rng.uniform(0, n)
        a, sg = rng.uniform(150, 900), rng.uniform(12, 40)
        dem += a * np.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) / (2 * sg ** 2))
    for _ in range(60):                                                     # 小さな峰(稜線をぎざぎざに)
        cy, cx = rng.uniform(0, n), rng.uniform(0, n)
        a, sg = rng.uniform(40, 260), rng.uniform(3, 9)
        dem += a * np.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) / (2 * sg ** 2))
    return dem


def photograph(sky_mask, sun_uv=None, seed=1):
    """空のマスク → 写真らしい灰画像: 空の勾配、地形の模様、雲、前景の柱、雑音、太陽の円盤。"""
    rng = np.random.default_rng(seed)
    H, W = sky_mask.shape
    vv, uu = np.mgrid[0:H, 0:W]
    sky = 0.85 - 0.25 * vv / H                                              # 上が明るい空(飽和はしない)
    tex = rng.random((H // 8 + 1, W // 8 + 1))
    tex = np.kron(tex, np.ones((8, 8)))[:H, :W]
    terrain = 0.22 + 0.18 * tex
    img = np.where(sky_mask > 0.5, sky, terrain)
    cloud = ((uu - 80) ** 2 / 900.0 + (vv - 40) ** 2 / 120.0) < 1.0        # 雲(空の中の明るい塊)
    img[cloud & (sky_mask > 0.5)] = 0.90                                    # 雲は明るいが飽和はしない
    img[:, 230:234] = 0.08                                                  # 前景の柱(縦の縁 = 抽出の罠)
    if sun_uv is not None:
        u, v = sun_uv
        disc = (uu - u) ** 2 + (vv - v) ** 2 <= 9.0
        img[disc & (sky_mask > 0.5)] = 1.0
    return np.clip(img + rng.normal(0, 0.03, (H, W)), 0.0, 1.0)


def project(dirs_world, pose):
    """世界方向 (N,3) → 画素 (N,2)(カメラの前にあるものだけ True)。"""
    import geocam as G
    dc = dirs_world @ G._rotation(*pose)
    ok = dc[:, 2] > 0.05
    uv = np.column_stack([K[2] + K[0] * dc[:, 0] / np.where(ok, dc[:, 2], 1.0), K[3] + K[1] * dc[:, 1] / np.where(ok, dc[:, 2], 1.0)])
    return uv, ok


def ridge_rows(sky, pose):
    """姿勢で描いた稜線 = 各列で空マスクが地形に変わる行(無ければ nan)。"""
    m = L.render_skyline_view(sky, K, SHAPE, *pose)
    rows = np.full(SHAPE[1], np.nan)
    for u in range(SHAPE[1]):
        col = m[:, u] < 0.5
        if col.any() and not col.all():
            rows[u] = np.argmax(col)
    return rows


def draw_rows(rgb, rows, color, thick=1):
    H = rgb.shape[0]
    for u, r in enumerate(rows):
        if np.isfinite(r):
            r = int(round(r))
            rgb[max(0, r - thick):min(H, r + thick + 1), u] = color
    return rgb


def ang_err(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.time()
    dem = synthetic_dem()
    sky = L.dem_skyline(dem, CELL, OBS, eye_height=5.0, az_step_deg=0.5)
    print("DATA: synthetic DEM 300x300 @ %.0f m, camera at cell %s, relief %.0f m, skyline elevation %.1f..%.1f deg" % (
        CELL, OBS, np.ptp(dem), sky["elevation_deg"].min(), sky["elevation_deg"].max()))
    mask = L.render_skyline_view(sky, K, SHAPE, *TRUE)
    photo = photograph(mask)

    # 1. スカイライン経路 ------------------------------------------------------
    rows = L.skyline_extract(photo)
    truth_rows = ridge_rows(sky, TRUE)
    ok = np.isfinite(truth_rows)
    print("skyline_extract: mean |row error| %.2f px (max %.0f) against the rendered truth, despite the cloud and the pole" % (
        np.abs(rows[ok] - truth_rows[ok]).mean(), np.abs(rows[ok] - truth_rows[ok]).max()))
    est = L.camera_orientation_from_skyline(rows, K, sky)
    e_sky = (ang_err(est["yaw_deg"], TRUE[0]), abs(est["pitch_deg"] - TRUE[1]), abs(est["roll_deg"] - TRUE[2]))
    print("skyline route: yaw %.2f pitch %.2f roll %.2f (truth %s) -> errors %.3f / %.3f / %.3f deg, residual %.3f, margin %.2f, ambiguous %s" % (
        est["yaw_deg"], est["pitch_deg"], est["roll_deg"], TRUE, *e_sky, est["residual_deg"], est["margin_deg"], est["ambiguous"]))

    # 2. 太陽経路 ---------------------------------------------------------------
    ts = _utc(2024, 12, 20, 21, 0, 0) + np.arange(0, 12 * 3600, 1200.0)      # 冬至の頃の一日(JST 6:00〜18:00)
    sun = L.sun_position(LAT, LON, ts)
    import geocam as G
    dirs = G._dir_from_az_el(sun["azimuth_deg"], sun["elevation_deg"])
    uv_true, vis = project(dirs, TRUE)
    inside = vis & (uv_true[:, 0] > 4) & (uv_true[:, 0] < SHAPE[1] - 4) & (uv_true[:, 1] > 4) & (uv_true[:, 1] < SHAPE[0] - 4)
    obs_uv, obs_t = [], []
    for i in np.nonzero(inside)[0]:
        frame = photograph(mask, sun_uv=uv_true[i], seed=100 + int(i))
        try:
            p = L.sun_pixel_position(frame)
        except ValueError:
            continue                                                        # 太陽が地形に隠れる時刻
        obs_uv.append(p[0]); obs_t.append(ts[i])
    obs_uv, obs_t = np.array(obs_uv), np.array(obs_t)
    est_sun = L.camera_orientation_from_sun(obs_uv, obs_t, LAT, LON, K)
    e_sun = (ang_err(est_sun["yaw_deg"], TRUE[0]), abs(est_sun["pitch_deg"] - TRUE[1]), abs(est_sun["roll_deg"] - TRUE[2]))
    print("sun route: %d sun frames over the day (%d..%d UTC) -> yaw %.2f pitch %.2f roll %.2f, errors %.3f / %.3f / %.3f deg, residual %.3f" % (
        len(obs_t), int((obs_t[0] % 86400) // 3600), int((obs_t[-1] % 86400) // 3600), est_sun["yaw_deg"], est_sun["pitch_deg"], est_sun["roll_deg"], *e_sun, est_sun["residual_deg"]))
    two = L.camera_orientation_from_sun(obs_uv[[0, -1]], obs_t[[0, -1]], LAT, LON, K)
    e_two = ang_err(two["yaw_deg"], TRUE[0])
    print("  with only the first and the last frame: yaw error %.3f deg (two time-stamped sun pixels fix the rotation)" % e_two)
    agree = (ang_err(est["yaw_deg"], est_sun["yaw_deg"]), abs(est["pitch_deg"] - est_sun["pitch_deg"]), abs(est["roll_deg"] - est_sun["roll_deg"]))
    print("the two routes agree to %.3f / %.3f / %.3f deg (yaw / pitch / roll) without sharing any input but K" % agree)

    # 3. 対照 -------------------------------------------------------------------
    rng = np.random.default_rng(7)
    prior_err = np.abs(rng.uniform(-15.0, 15.0, 200)).mean()
    flat = np.full((60, 60), 100.0)
    sky_flat = L.dem_skyline(flat, CELL, (30, 30))
    rows_flat = L.skyline_extract(photograph(L.render_skyline_view(sky_flat, K, SHAPE, *TRUE), seed=3))
    est_flat = L.camera_orientation_from_skyline(rows_flat, K, sky_flat, yaw_step_deg=5.0)
    print("controls: road-direction prior (truth +/- 15 deg) mean error %.1f deg; flat DEM -> ambiguous %s (margin %.3f, yaw error %.1f deg would be silently wrong)" % (
        prior_err, est_flat["ambiguous"], est_flat["margin_deg"], ang_err(est_flat["yaw_deg"], TRUE[0])))
    try:
        L.camera_orientation_from_sun(obs_uv[:1], obs_t[:1], LAT, LON, K)
        one_refused = False
    except ValueError:
        one_refused = True
    print("  one sun frame is refused: %s" % one_refused)

    assert max(e_sky) < 0.2 and max(e_sun) < 0.2, (e_sky, e_sun)
    assert max(agree) < 0.3, agree
    assert not est["ambiguous"] and est_flat["ambiguous"] and one_refused
    assert prior_err > 5.0 and e_two < 0.3
    print("ORDER: skyline %.3f deg ~ sun %.3f deg << road-direction prior %.1f deg (yaw error)" % (e_sky[0], e_sun[0], prior_err))

    # 図 -----------------------------------------------------------------------
    if figs.enabled():
        base = np.stack([photo] * 3, -1)
        over = draw_rows(base.copy(), rows, CYAN)
        over = draw_rows(over, ridge_rows(sky, (est["yaw_deg"], est["pitch_deg"], est["roll_deg"])), MAGENTA)
        figs.save_grid("skyline_lock", [photo, over, L.render_skyline_view(sky, K, SHAPE, est["yaw_deg"], est["pitch_deg"], est["roll_deg"])],
                       captions=["synthetic photograph (cloud, foreground pole, noise)",
                                 "cyan = extracted skyline (skyline_extract), magenta = DEM ridge at the estimated pose",
                                 "sky mask rendered at the estimated pose (render_skyline_view)"],
                       gray=[True, False, True], ncols=3,
                       caption="the DEM ridge drawn at the estimated yaw / pitch / roll lies on the extracted skyline; errors %.2f / %.2f / %.2f deg" % e_sky)
        frames = []
        yaws = np.arange(0.0, 360.0, 5.0 if not REDUCED else 10.0)
        prof = np.interp(yaws, est["yaw_profile_deg"], est["yaw_profile_residual_deg"], period=360.0)
        pmax = float(prof.max())
        for y, r in zip(yaws, prof):
            fr = draw_rows(base.copy(), rows, CYAN)
            fr = draw_rows(fr, ridge_rows(sky, (y, est["pitch_deg"], est["roll_deg"])), MAGENTA)
            w = int(round((1.0 - r / pmax) * (SHAPE[1] - 20)))                 # 噛み合いのメーター(長いほど良い)
            fr[SHAPE[0] - 12:SHAPE[0] - 6, 10:10 + max(w, 1)] = YELLOW
            fr[SHAPE[0] - 12:SHAPE[0] - 6, 10 + int(round((1.0 - est["residual_deg"] / pmax) * (SHAPE[1] - 20))):][:, :2] = 1.0
            frames.append(fr)
        i_best = int(np.argmin(np.abs(((yaws - est["yaw_deg"]) + 180.0) % 360.0 - 180.0)))
        frames = frames + [frames[i_best]] * 12
        figs.save_gif("yaw_sweep", frames, fps=8.0,
                      caption="the DEM ridge (magenta) swept through every yaw over the photograph; the yellow meter is the fit and it peaks where the ridge locks onto the extracted skyline (cyan), at yaw %.1f" % est["yaw_deg"])
        top = float(est["yaw_profile_residual_deg"].max())
        figs.save_plot("yaw_profile",
                       [("skyline residual vs yaw (mountains)", est["yaw_profile_deg"], est["yaw_profile_residual_deg"]),
                        ("flat DEM", est_flat["yaw_profile_deg"], est_flat["yaw_profile_residual_deg"]),
                        ("truth yaw %.0f" % TRUE[0], np.array([TRUE[0], TRUE[0]]), np.array([0.0, top]))],
                       xlabel="yaw [deg]", ylabel="elevation residual RMS [deg]",
                       title="one valley in the mountains (margin %.2f deg), none on flat ground (ambiguous)" % est["margin_deg"],
                       caption="the op returns the whole residual curve so that the ambiguity is visible: a runner-up valley at %.0f deg is %.2f deg worse; the flat DEM curve is level" % (est["runner_up_yaw_deg"], est["margin_deg"]),
                       xlim=(0, 360))
        pose_sun = (est_sun["yaw_deg"], est_sun["pitch_deg"], est_sun["roll_deg"])
        track_uv, tvis = project(dirs, pose_sun)
        sky_est = L.render_skyline_view(sky, K, SHAPE, *pose_sun)
        tr = base.copy()
        for (u, v), o in zip(track_uv, tvis):
            if o and 0 <= u < SHAPE[1] and 0 <= v < SHAPE[0] and sky_est[int(v), int(u)] > 0.5:
                tr[max(0, int(v) - 1):int(v) + 2, max(0, int(u) - 1):int(u) + 2] = YELLOW
        for u, v in obs_uv:
            tr[max(0, int(v) - 3):int(v) + 4, max(0, int(u) - 3):int(u) + 4] = MAGENTA
        figs.save("sun_track", tr, caption="the sun's path over the day where it is above the ridge (yellow, projected with the pose estimated from the sun) and the %d sun discs picked by sun_pixel_position (magenta); two of them are enough" % len(obs_uv))
        figs.save_table("numbers", ["route", "yaw", "pitch", "roll", "yaw err", "pitch err", "roll err", "note"],
                        [["truth", "%.2f" % TRUE[0], "%.2f" % TRUE[1], "%.2f" % TRUE[2], "", "", "", "synthetic camera"],
                         ["skyline (DEM ridge vs extracted)", "%.2f" % est["yaw_deg"], "%.2f" % est["pitch_deg"], "%.2f" % est["roll_deg"], "%.3f" % e_sky[0], "%.3f" % e_sky[1], "%.3f" % e_sky[2], "residual %.3f, margin %.2f" % (est["residual_deg"], est["margin_deg"])],
                         ["sun (%d frames, Wahba/SVD)" % len(obs_t), "%.2f" % est_sun["yaw_deg"], "%.2f" % est_sun["pitch_deg"], "%.2f" % est_sun["roll_deg"], "%.3f" % e_sun[0], "%.3f" % e_sun[1], "%.3f" % e_sun[2], "residual %.3f" % est_sun["residual_deg"]],
                         ["sun (2 frames)", "%.2f" % two["yaw_deg"], "%.2f" % two["pitch_deg"], "%.2f" % two["roll_deg"], "%.3f" % e_two, "", "", "first + last"],
                         ["road-direction prior", "", "", "", "%.1f" % prior_err, "", "", "truth +/- 15 deg, as public metadata gives"],
                         ["skyline on flat DEM", "%.1f" % (round(est_flat["yaw_deg"], 1) % 360.0), "", "", "%.1f" % ang_err(est_flat["yaw_deg"], TRUE[0]), "", "", "ambiguous = True (refused, not silently wrong)"]],
                        title="fixed-camera orientation from the picture itself",
                        caption="both routes recover the pose to well under a degree and agree with each other; the public-metadata prior is off by ten degrees and the flat-ground case is flagged rather than guessed")
        assert not figs.errors(), figs.errors()
    print("elapsed %.0fs" % (time.time() - t0))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
