# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 公共カメラはどこを向いているか・実写編 ―― フィンランドの道路カメラ 807 局で太陽を探し、日没 1 本から向きを決める

合成(``poc_public_camera_heading``)では「太陽 = 飽和した小さな円盤」で足りた。実写の道路カメラ(Fintraffic 天候カメラ、
CC BY 4.0、鍵なし)は違った:

* **見た目では太陽と決められない。** 局名の白い文字・標識・白い車・レンズの水滴が同じように飽和する。合成向けの
  ``sun_pixel_position`` は最初の探針で **24 / 24 が誤検出**。濡れた路面に映った太陽の**反射**は太陽の速さで動くので動きでも
  区別できず、「カメラが上を向く」非物理な姿勢(pitch > 0)と、消失点の仰角(地平線は 0°)で弾く。
* **太陽は円盤でなくブルーム**(露出で大きさが変わる飽和の塊)で、画像の上端や局名の帯で切れる。切れた塊の重心は
  切れた側の反対へ偏る。
* **カメラは道路を見下ろし**、空は上 3 分の 1。太陽が画角に入るのは日の出・日没の 1 時間、しかもその向きの道路だけ。
  9 月 20〜21 日の 807 局 × 24 h から、動く塊 200 本を全日追跡して太陽の軌跡が 4 枚以上残ったのは **1 台**(E18・Hamina。3 枚だけの日の出が 2 台、不採用)。

そこで geocam に 2 op を足した(この PoC が使うのはそれ):

* ``sun_bloom_fit`` —— 最大の飽和塊の**切れていない縁**に円を当てて中心を返す。太陽とは決めない。
* ``camera_orientation_from_sun_candidates`` —— フレームごとの候補(太陽も車も混在)から、**時刻どおりに動く 1 本**を
  RANSAC で選び、道路カメラの事前知識(|roll| ≤ 12°・pitch −40〜0°・水平画角 25〜120°)で非物理な仮説を捨て、
  焦点距離も同時に探索する(公開カメラに内部パラメータは無い)。

**主張は 1 つだけ**: 位置しか公開されていない(向きは UNKNOWN)固定カメラの yaw を、日没の写真 5 枚と時刻だけから決め、
**独立な幾何で検算**する —— 同じ姿勢で画像中の車線の消失点を世界方位に変換すると、OpenStreetMap の路線方位と数度で一致する。
弱い自由度(roll と焦点距離: 1 時間の低仰角の弧では決まりにくい)は 1 枚抜き(jackknife)の散らばりで隠さず出す。

図:
1. ``sunset_track``: 日没のフレームに、推定姿勢で描いた太陽の軌跡(マゼンタ)と円当てした太陽(シアン)。
2. ``sunset_follow``: 日没の 9 枚を並べ、推定姿勢から**予測した**太陽の位置(マゼンタの円)が本物の太陽についていく GIF。
3. ``naive_picks``: 同じ写真で合成向けの門(``sun_pixel_position``)が「太陽」と言った場所 —— 文字・標識・車。
4. ``jackknife``: 1 枚抜きで姿勢と焦点距離がどれだけ動くか(yaw は動かず、roll と f が動く)。
5. ``bloom_bias``: 切れたブルームで重心と円当ての中心がどれだけずれるか。
6. ``numbers``: 数表。

データ: ``examples/data/fintraffic_sun_2026_09_20.json`` = 生画像から作った**集計だけ**(フレームごとの時刻とブルーム円当て、
合成向けの門の出力、消失点、OSM の路線方位)。生画像は commit しない。画像のある図は、キャッシュ
(``FULLSEYE_DATA_DIR/poc_fintraffic_sun/img/<preset>/<unix>.jpg``、既定 ``~/.cache/fullseye``)があるときだけ描く。
出典: Fintraffic / Digitraffic(CC BY 4.0)、OpenStreetMap(ODbL)。
走らせ方: ``py -3.11 examples/poc_public_camera_heading_real.py``(図は ``out/figures/poc_public_camera_heading_real/``)。
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import fullseye as fs  # noqa: E402
import examplefig as figs  # noqa: E402

L = fs.ledger
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "fintraffic_sun_2026_09_20.json")
CACHE = os.path.join(os.environ.get("FULLSEYE_DATA_DIR", os.path.join(os.path.expanduser("~"), ".cache", "fullseye")), "poc_fintraffic_sun", "img")
# 探針の内訳(2026-09-21 に走らせた実測。生画像は残さない): 807 局の 24 h 履歴から太陽高度 2〜12° の連続 2 枚を朝夕それぞれ落とし、
# 大きな飽和塊が右(時計回り)へ 15〜120 px 動くプリセットを候補にして全日追跡した。
PROBE = {"stations": 807, "naive_hits_checked": 24, "naive_hits_that_were_the_sun": 0,
         "presets_with_a_moving_blob": 200, "presets_tracked_all_day": 71, "presets_with_a_real_sun_track": 1,
         "presets_with_only_3_frames": 2}
MAGENTA, CYAN, YELLOW = (255, 60, 220), (80, 255, 255), (255, 200, 0)


def _hm(t):
    return time.strftime("%H:%M", time.gmtime(t))


def ang_diff(a, b):
    return (a - b + 180.0) % 360.0 - 180.0


# --------------------------------------------------------------------------- #
# 当てはめ                                                                       #
# --------------------------------------------------------------------------- #
def candidates_of(cam):
    """集計 → (候補 (N,2), フレーム添字 (N,), 時刻 (F,))。ブルームが当たったフレームだけが候補を持つ。"""
    ts = np.array([f["t"] for f in cam["frames"]], dtype=np.float64)
    C, FI = [], []
    for k, f in enumerate(cam["frames"]):
        if f["bloom"]:
            C.append([f["bloom"]["u"], f["bloom"]["v"]])
            FI.append(k)
    return np.array(C, dtype=np.float64), np.array(FI, dtype=np.float64), ts


def fit(cam, C, FI, ts):
    return L.camera_orientation_from_sun_candidates(C, FI, ts, cam["lat"], cam["lon"], tuple(cam["shape"]))


def project(cam, r, ts):
    """推定姿勢で各時刻の太陽を画素へ(見えない時刻は nan)。"""
    import geocam as G

    s = L.sun_position(cam["lat"], cam["lon"], ts)
    d = G._dir_from_az_el(s["azimuth_deg"], s["elevation_deg"]) @ G._rotation(r["yaw_deg"], r["pitch_deg"], r["roll_deg"])
    fx, fy, cx, cy = r["K"]
    ok = d[:, 2] > 0.05
    uv = np.full((len(ts), 2), np.nan)
    uv[ok, 0] = cx + fx * d[ok, 0] / d[ok, 2]
    uv[ok, 1] = cy + fy * d[ok, 1] / d[ok, 2]
    return uv, s


def bearing_of_pixel(cam, r, u, v):
    import geocam as G

    d = G._pixel_rays(np.array([[u, v]], dtype=np.float64), r["K"]) @ G._rotation(r["yaw_deg"], r["pitch_deg"], r["roll_deg"]).T
    az, el = G._az_el(d)
    return float(az[0]), float(el[0])


def jackknife(cam, C, FI, ts, r):
    """採用したフレームを 1 つずつ抜いて当て直す → 姿勢と f の散らばり。"""
    inl = np.nonzero(r["inlier"])[0]
    rows = []
    for q in inl:
        keep = np.ones(len(C), bool)
        keep[q] = False
        try:
            rq = L.camera_orientation_from_sun_candidates(C[keep], FI[keep], ts, cam["lat"], cam["lon"], tuple(cam["shape"]))
        except ValueError:
            continue
        rows.append((_hm(ts[int(FI[q])]), rq["yaw_deg"], rq["pitch_deg"], rq["roll_deg"], rq["f_px"], rq["n_inliers"]))
    return rows


# --------------------------------------------------------------------------- #
# 図                                                                            #
# --------------------------------------------------------------------------- #
def _load_frame(cam, t):
    p = os.path.join(CACHE, cam["preset"], "%d.jpg" % int(t))
    if not os.path.exists(p):
        return None
    try:
        from PIL import Image
    except ImportError:
        return None
    return Image.open(p).convert("RGB")


def _draw_track(cam, r, ts, uv, k_show, inl_frames, credit):
    from PIL import ImageDraw

    im = _load_frame(cam, ts[k_show])
    if im is None:
        return None
    d = ImageDraw.Draw(im)
    pts = [(uv[k, 0], uv[k, 1]) for k in range(len(ts)) if np.isfinite(uv[k, 0]) and -300 < uv[k, 0] < im.width + 300 and -300 < uv[k, 1] < im.height + 300]
    if len(pts) > 1:
        d.line(pts, fill=MAGENTA, width=3)
    for k in inl_frames:
        b = cam["frames"][k]["bloom"]
        d.ellipse([b["u"] - b["r"], b["v"] - b["r"], b["u"] + b["r"], b["v"] + b["r"]], outline=CYAN, width=3)
        d.text((b["u"] + b["r"] + 3, b["v"] - 6), _hm(ts[k]) + " UTC", fill=(255, 255, 255))
    d.text((8, im.height - 16), credit, fill=(255, 255, 255))
    return np.asarray(im)


def _follow_frames(cam, r, ts, uv, ks, credit):
    from PIL import ImageDraw

    out = []
    for k in ks:
        im = _load_frame(cam, ts[k])
        if im is None:
            continue
        d = ImageDraw.Draw(im)
        if np.isfinite(uv[k, 0]):
            u, v = uv[k]
            d.ellipse([u - 45, v - 45, u + 45, v + 45], outline=MAGENTA, width=4)
            d.line([(u - 70, v), (u - 50, v)], fill=MAGENTA, width=3)
            d.line([(u + 50, v), (u + 70, v)], fill=MAGENTA, width=3)
        d.rectangle([0, 0, 330, 22], fill=(0, 0, 0))
        d.text((6, 4), "%s UTC  predicted sun (magenta) from the fitted pose" % _hm(ts[k]), fill=(255, 255, 255))
        d.text((8, im.height - 16), credit, fill=(255, 255, 255))
        out.append(np.asarray(im.resize((im.width // 2, im.height // 2))))
    return out


def classify_naive(cam, uv):
    """合成向けの門の各 pick を 3 つに分ける: exact(予測の 25 px 以内)/ biased(太陽のブルーム上だが 25 px 超)/ other(別の物)。"""
    out = []
    for k, f in enumerate(cam["frames"]):
        if not f["naive"]:
            continue
        u, v = f["naive"]
        b = f["bloom"]
        on_bloom = b is not None and np.hypot(b["u"] - u, b["v"] - v) <= b["r"] + 10.0 and np.isfinite(uv[k, 0]) and np.hypot(uv[k, 0] - b["u"], uv[k, 1] - b["v"]) < 60.0
        exact = np.isfinite(uv[k, 0]) and np.hypot(uv[k, 0] - u, uv[k, 1] - v) < 25.0
        out.append((k, "exact" if exact else ("biased" if on_bloom else "other")))
    return out


def _naive_panels(cam, ts, uv, cls, n=6):
    from PIL import ImageDraw

    order = [kc for kc in cls if kc[1] == "other"][:4] + [kc for kc in cls if kc[1] == "biased"][:1] + [kc for kc in cls if kc[1] == "exact"][:1]
    panels, caps = [], []
    for k, c in order[:n]:
        f = cam["frames"][k]
        im = _load_frame(cam, ts[k])
        if im is None:
            continue
        u, v = f["naive"]
        crop = im.crop((int(u - 120), int(v - 70), int(u + 120), int(v + 70)))
        d = ImageDraw.Draw(crop)
        d.ellipse([120 - 8, 70 - 8, 120 + 8, 70 + 8], outline=YELLOW, width=2)
        panels.append(np.asarray(crop))
        caps.append("%s: %s" % (_hm(ts[k]), {"other": "not the sun", "biased": "the sun, centre off by %.0f px" % np.hypot(uv[k, 0] - u, uv[k, 1] - v), "exact": "the sun"}[c]))
    return panels, caps


# --------------------------------------------------------------------------- #
# 本体                                                                          #
# --------------------------------------------------------------------------- #
def main():
    data = json.load(open(DATA, encoding="utf-8"))
    checks, rows = [], []
    for cam in data["cameras"]:
        credit = "Image: Fintraffic / digitraffic.fi (CC BY 4.0), %s" % cam["name"]
        C, FI, ts = candidates_of(cam)
        r = fit(cam, C, FI, ts)
        uv, sun = project(cam, r, ts)
        inl_frames = sorted(int(FI[i]) for i in np.nonzero(r["inlier"])[0])
        print("== %s (%s, road %s, direction in metadata: %s, %s)" % (cam["preset"], cam["names"]["en"], cam["road_number"], cam["direction"], cam["camera_type"]))
        print("   frames %d, blooms %d, sun track: %d frames %s..%s UTC" % (len(ts), len(C), len(inl_frames), _hm(ts[inl_frames[0]]), _hm(ts[inl_frames[-1]])))
        print("   yaw %.1f  pitch %.1f  roll %.1f  f %.0f px (HFOV %.1f)  residual %.2f deg  leave-one-out %.1f px" % (
            r["yaw_deg"], r["pitch_deg"], r["roll_deg"], r["f_px"], r["hfov_deg"], r["residual_deg"], r["loo_px"]))

        # 独立な検算: 車線の消失点 → 世界方位 vs OSM の路線方位
        vp = cam["vanishing_point"]
        vp_az, vp_el = bearing_of_pixel(cam, r, vp["u"], vp["v"])
        road = cam["osm_road"]["bearing"]
        d_vp = ang_diff(vp_az, road) if abs(ang_diff(vp_az, road)) < abs(ang_diff(vp_az, road + 180.0)) else ang_diff(vp_az, road + 180.0)
        print("   vanishing point (%.0f, %.0f) -> bearing %.1f (el %.1f); OSM road %s bearing %.1f -> difference %+.1f deg" % (
            vp["u"], vp["v"], vp_az, vp_el, cam["osm_road"]["ref"], road, d_vp))
        checks.append(("vanishing point agrees with OSM road bearing within 5 deg", abs(d_vp) < 5.0))
        # 反射の門: 濡れた路面に映った太陽も太陽の速さで動く。本物なら同じ姿勢で道路の消失点は地平線(仰角 ≈ 0)にある
        checks.append(("the lane vanishing point sits on the horizon under this pose (|el| < 6 deg)", abs(vp_el) < 6.0))
        checks.append(("the answer is not pinned to a prior bound", r["at_prior_bound"] == 0.0))
        checks.append(("sun track has >= 4 frames spanning >= 0.5 h", r["n_inliers"] >= 4 and r["span_h"] >= 0.5))
        checks.append(("pose is physical (pitch -15..5, |roll| < 12)", -15.0 <= r["pitch_deg"] <= 5.0 and abs(r["roll_deg"]) < 12.0))

        # 対照 1: 合成向けの門は同じ写真で何を太陽と言ったか(3 つに分ける)
        cls = classify_naive(cam, uv)
        n_exact = sum(1 for _, c in cls if c == "exact")
        n_biased = sum(1 for _, c in cls if c == "biased")
        n_other = sum(1 for _, c in cls if c == "other")
        print("   naive sun_pixel_position: %d picks -> %d the sun, %d the sun but off by > 25 px (clipped bloom), %d something else (text, signs, cars)" % (len(cls), n_exact, n_biased, n_other))
        checks.append(("the look-alone detector points at something other than the sun in most frames", n_other > 0.5 * len(cls)))

        # 対照 2: 重心 vs 円当て(切れたブルーム)
        clipped = [f["bloom"] for f in cam["frames"] if f["bloom"] and f["bloom"]["clipped"] == 1.0]
        bias = [np.hypot(b["centroid_u"] - b["u"], b["centroid_v"] - b["v"]) for b in clipped]
        print("   clipped blooms: %d, centroid vs circle centre: mean %.1f px, max %.1f px" % (len(clipped), np.mean(bias) if bias else 0.0, np.max(bias) if bias else 0.0))
        checks.append(("the centroid of a clipped bloom is biased by > 5 px", bool(bias) and float(np.mean(bias)) > 5.0))

        # 弱い自由度: 1 枚抜き
        jk = jackknife(cam, C, FI, ts, r)
        yaw_sp = max(abs(ang_diff(a[1], r["yaw_deg"])) for a in jk) if jk else float("nan")
        roll_sp = max(abs(a[3] - r["roll_deg"]) for a in jk) if jk else float("nan")
        f_sp = max(abs(a[4] - r["f_px"]) / r["f_px"] for a in jk) if jk else float("nan")
        print("   jackknife (%d refits): yaw moves <= %.2f deg, roll <= %.1f deg, f <= %.0f%%" % (len(jk), yaw_sp, roll_sp, 100 * f_sp))
        checks.append(("yaw is stable under leave-one-out (< 2 deg)", yaw_sp < 2.0))

        rows.append([cam["preset"], "%.1f" % r["yaw_deg"], "%.1f" % r["pitch_deg"], "%.1f" % r["roll_deg"], "%.0f" % r["f_px"],
                     "%d/%d" % (r["n_inliers"], len(C)), "%.1f" % vp_az, "%.1f" % road, "%+.1f" % d_vp, "%.2f" % yaw_sp, "%.1f" % roll_sp])

        # 図 -------------------------------------------------------------------
        k_show = inl_frames[len(inl_frames) // 2]
        tr = _draw_track(cam, r, ts, uv, k_show, inl_frames, credit)
        if tr is not None:
            figs.save("sunset_track", tr, caption="the sunset seen by %s (E18, Hamina, Finland; metadata says direction UNKNOWN): "
                      "the sun's path for the evening drawn from the fitted pose (magenta) and the %d blooms fitted with a circle (cyan); yaw %.1f, pitch %.1f, roll %.1f, HFOV %.0f"
                      % (cam["preset"], len(inl_frames), r["yaw_deg"], r["pitch_deg"], r["roll_deg"], r["hfov_deg"]))
            ks = [k for k in range(len(ts)) if sun["elevation_deg"][k] > -1.0 and np.isfinite(uv[k, 0]) and 0 <= uv[k, 0] < cam["shape"][1] and 0 <= uv[k, 1] < cam["shape"][0]]
            fr = _follow_frames(cam, r, ts, uv, ks, credit)
            if len(fr) >= 3:
                figs.save_gif("sunset_follow", fr, fps=1.5, caption="the same evening frame by frame: the magenta circle is where astronomy plus the fitted pose says the sun must be — it follows the real sun down to the horizon (%d frames, 10 min apart)" % len(fr))
            panels, caps = _naive_panels(cam, ts, uv, cls)
            if panels:
                figs.save_grid("naive_picks", panels, captions=caps, ncols=3,
                               caption="what the look-alone detector (sun_pixel_position, built for synthetic discs) called the sun in the same camera: %d picks, %d exactly the sun, %d on the sun but off-centre, %d something else — station text, signs, white cars" % (len(cls), n_exact, n_biased, n_other))
        else:
            print("   (no cached frames: image figures skipped; aggregate figures only)")
        if jk:
            x = np.arange(len(jk), dtype=float)
            figs.save_plot("jackknife", [("yaw - fit [deg]", x, np.array([ang_diff(a[1], r["yaw_deg"]) for a in jk])),
                                         ("pitch - fit [deg]", x, np.array([a[2] - r["pitch_deg"] for a in jk])),
                                         ("roll - fit [deg]", x, np.array([a[3] - r["roll_deg"] for a in jk])),
                                         ("f / fit - 1 [x10]", x, np.array([10 * (a[4] / r["f_px"] - 1) for a in jk]))],
                           xlabel="left-out frame (index)", ylabel="change", title="leave-one-out: which degrees of freedom the short sunset arc pins down",
                           caption="refit with each sun frame removed: yaw barely moves, roll and the focal length are the weak directions of a 1-hour low-elevation arc — this is why the PoC reports them with their spread instead of a single number")
        if bias:
            figs.save_plot("bloom_bias", [("centroid - circle centre [px]", np.arange(len(bias), dtype=float), np.array(bias))],
                           xlabel="clipped bloom (index)", ylabel="px", title="a clipped bloom's centroid is not its centre",
                           caption="for blooms cut by the station-name band the centroid sits %.1f px (mean) away from the circle fitted to the unclipped rim; the fit uses the circle" % float(np.mean(bias)))
    figs.save_table("numbers", ["preset", "yaw", "pitch", "roll", "f px", "sun frames", "VP bearing", "OSM road", "diff", "yaw jk", "roll jk"], rows,
                    title="real cameras: pose from the sun, checked against the road", caption="one camera out of %d stations gave a sun track of 4 or more frames on 2026-09-20/21 (%d more had 3 frames and were left out); the vanishing point of its lanes, turned into a world bearing with the sun-derived pose, agrees with OpenStreetMap" % (PROBE["stations"], PROBE["presets_with_only_3_frames"]))

    print()
    print("probe: %d stations x 24 h; %d presets had a bright blob moving like the sun, %d were tracked all day, %d gave a sun track of >= 4 frames "
          "(%d more had only 3 frames and were not used); look-alone detector on the first probe: %d/%d wrong" % (
              PROBE["stations"], PROBE["presets_with_a_moving_blob"], PROBE["presets_tracked_all_day"], PROBE["presets_with_a_real_sun_track"],
              PROBE["presets_with_only_3_frames"], PROBE["naive_hits_checked"] - PROBE["naive_hits_that_were_the_sun"], PROBE["naive_hits_checked"]))
    bad = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print("  [%s] %s" % ("ok" if ok else "NG", name))
    if bad:
        print("FAIL: %d check(s) did not hold" % len(bad))
        raise SystemExit(1)
    assert not figs.errors(), figs.errors()                                    # 図の失敗を黙って捨てない
    print("PASS")


if __name__ == "__main__":
    main()
