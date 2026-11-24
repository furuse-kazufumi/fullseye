# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""二段式ロケットの分離から第1段再着陸を、MuJoCo の世界と RGB 映像計測で分けて採点する(2026-11-24)。

    py -3.11 examples/poc_rocket_landing.py
    CI=1 py -3.11 examples/poc_rocket_landing.py

主張: **世界側にだけある MuJoCo の真値を見ず、固定 2 カメラの RGB 映像から復元した位置・傾き・接地・炎の向き・
中心ずれで、成功だけでなく燃料不足と強風の失敗も同じ判定にできる。**

場面は実在の機体・会社・ロゴを使わない一般的な二段機で、寸法は第1段 6.0 m × 直径 1.5 m、上段 4.0 m ×
直径 1.12 m、着陸台半径 4.0 m。MuJoCo が 2 段を別の自由剛体として動かし、上段は分離直後に別の上昇軌道へ、
下段は逆噴射で戻る。制御は高さ h の停止速度 |v_z| = sqrt(2 a h) と横位置・速度の PID、15° のジンバル制限だけで、
学習済み重みは使わない。燃料は T/(Isp*g0) で減らし、MuJoCo の body mass / inertia も毎刻更新する。

Fullseye が見るものはレンダした RGB だけ。シアンの第1段、黄の上端、赤の下端、橙の炎、緑の台中心を色で検出し、
既存 op の ``camera.triangulate`` で 2 視点の画素から 3-D 軌跡と姿勢を復元する。``measure.fit_line`` は炎の
画像上の軸を測り、``calib.image_points_to_world_plane`` は台中心を校正値で z=0 へ戻す。MuJoCo の状態は採点後にだけ
照合する。成功の上限は速さ 4.0 m/s、傾き 25°、台中心から 2.5 m(この縮尺の PoC の門であって実機認証値ではない)。

調整用は nominal seed 3 / 11、holdout は seed 41 / 57。失敗側は fuel_shortage seed 7 と strong_wind seed 19。
CI=1 は 320×240・0.15 s 標本、通常は 512×384・0.10 s 標本で物理条件・seed・判定閾値を変えない。図を出すと、
分離→着陸の MP4/GIF、2 固定カメラの入力→計測→真値、3-D 軌跡と誤差表を作る。

正直な限界: 空力・抗力・燃焼・燃料スロッシング・構造たわみ・レンズ歪み・ローリングシャッターは入れていない。風は
seed 固定の外力で CFD ではなく、炎は推力方向の可視化で放射や流体を再現しない。色が既知で背景から分かれる合成 RGB は
実写より大幅に容易で、単眼ではなく既知校正済み 2 視点を使う。この段階は制御の有効性や実機安全性を主張しない。
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import time

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import annotate as an  # noqa: E402
import camera  # noqa: E402  # existing Fullseye calibrated 3-D reconstruction op
import examplefig as figs  # noqa: E402
import rocketlanding as rl  # noqa: E402


GATES: list[tuple[str, bool]] = []


def gate(name: str, ok: bool, detail: str = "") -> None:
    """Record one measured gate / 実測値つきの門を表示して集める。"""
    GATES.append((name, bool(ok)))
    print("  [%s] %s %s" % ("ok" if ok else "NG", name, detail))


def _colour_crosshair(image: np.ndarray, uv: np.ndarray, role: str) -> np.ndarray:
    """Draw one finite image point / 有限な画素座標だけを重ねる。"""
    # ``crosshair`` rounds its centre to a pixel.  Keep the outermost pixel
    # out of the display overlay so a true point at x=511.8 on a 512-px image
    # is shown as an out-of-frame truth, not rounded to the invalid x=512.
    if (not np.isfinite(uv).all() or uv[0] < 0.0 or uv[1] < 0.0
            or uv[0] > image.shape[1] - 1.0 or uv[1] > image.shape[0] - 1.0):
        return image
    return np.asarray(an.crosshair(image, (float(uv[0]), float(uv[1])), color=role,
                                         width=2, gap=3, extent=9))


def _comparison_frame(run: dict, measured: dict, index: int, cam_name: str) -> np.ndarray:
    """Overlay RGB measurement and simulator truth / 映像計測と真値を同じコマへ重ねる。

    Green is a display-only truth overlay added *after* the measurement; orange
    is the RGB result.  Neither affects :func:`rocketlanding.measure_from_rgb`.
    """
    row, obs = run["rows"][index], measured["series"][index]
    image = np.asarray(row["images"][cam_name], np.float64) / 255.0
    keys = ("booster", "nose", "engine")
    # Orange is the camera measurement.  All three target points use one
    # colour so the green truth crosshair remains unambiguous / RGB 計測は橙、
    # 真値は緑に固定し、三つの目標点で色の意味を変えない。
    for key in keys:
        image = _colour_crosshair(image, obs["ground_uv" if cam_name.startswith("ground") else "pad_uv"][key], "emphasis")
    cam = run["cameras"][cam_name]
    pts = np.vstack([row["truth_center"], row["truth_nose"], row["truth_engine"]])
    uv, _ = camera.project_points(pts, cam["K"], cam["R"], cam["t"])
    for p in uv:
        image = _colour_crosshair(image, p, "right")
    title = ("地上追尾 / ground tracking" if cam_name.startswith("ground") else "着陸台 / pad camera")
    if image.shape[1] < 400:
        txt, font_size = "%s t=%.2f RGB/真値" % (title, row["t_s"]), 11
    else:
        txt, font_size = "%s  t=%.2f s  橙=RGB測定  緑=MuJoCo真値" % (title, row["t_s"]), 14
    return np.asarray(an.text_box(image, txt, (8, 8), anchor="lt", font_size=font_size))


def _side_by_side(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    """Make the two fixed cameras one video frame / 2 台の固定カメラを横に並べる。"""
    h = max(left.shape[0], right.shape[0])
    w = left.shape[1] + right.shape[1] + 6
    out = np.zeros((h, w, 3), dtype=np.float64)
    out[:left.shape[0], :left.shape[1]] = left
    out[:right.shape[0], left.shape[1] + 6:] = right
    return out


def _comparison_movie(record: dict) -> list[np.ndarray]:
    """Build one two-camera evidence movie / 2 台カメラの証拠動画を組み立てる。"""
    run, measured = record["run"], record["measured"]
    return [_side_by_side(_comparison_frame(run, measured, i, "ground_tracking_camera"),
                          _comparison_frame(run, measured, i, "pad_camera"))
            for i in range(len(run["rows"]))]


def _gif_resize(frames: list[np.ndarray], width: int = 720) -> list[np.ndarray]:
    """Downsample display frames with Lanczos, never nearest neighbour / 表示コマだけを Lanczos で縮小する。"""
    from PIL import Image

    h, w = frames[0].shape[:2]
    out_h = max(1, int(round(h * width / w)))
    return [np.asarray(Image.fromarray(np.clip(frame * 255.0, 0, 255).astype(np.uint8)).resize(
        (width, out_h), Image.Resampling.LANCZOS), dtype=np.float64) / 255.0 for frame in frames]


def _truth_contact_index(record: dict) -> int:
    """Pick the rendered frame nearest simulator contact / シミュレータ接触に最も近い描画コマを選ぶ。"""
    rows = record["run"]["rows"]
    contact = record["summary"]["truth_contact"]
    if contact is None:
        return len(rows) - 1
    return int(np.argmin([abs(row["t_s"] - contact["time_s"]) for row in rows]))


def _group_stats(rows: list[dict]) -> dict[str, float]:
    """Aggregate already measured cases / 実行済みのケースだけを集計する。"""
    return {
        "pos_med_m": float(np.median([r["summary"]["position_median_m"] for r in rows])),
        "pos_max_m": float(np.max([r["summary"]["position_max_m"] for r in rows])),
        "tilt_med_deg": float(np.median([r["summary"]["tilt_median_deg"] for r in rows])),
        "flame_med_deg": float(np.median([r["summary"]["flame_angle_median_deg"] for r in rows])),
    }


def _write_inspection(frames: list[np.ndarray], contact_index: int | None, directory: str | None) -> list[Path]:
    """Write first/middle/last/contact frames outside the repo / 検分用コマを外部へ保存する。"""
    if not directory:
        return []
    from PIL import Image

    dst = Path(directory).expanduser().resolve()
    dst.mkdir(parents=True, exist_ok=True)
    picks = [("first", 0), ("middle", len(frames) // 2), ("last", len(frames) - 1)]
    if contact_index is not None:
        picks.append(("contact", max(0, min(contact_index, len(frames) - 1))))
    out = []
    for name, i in picks:
        path = dst / (name + ".png")
        Image.fromarray(np.clip(frames[i] * 255.0, 0, 255).astype(np.uint8)).save(path)
        out.append(path)
    # Contact sheet is kept outside the repo too, so full-size originals remain
    # the first inspection target / 接触票も縮小ではなく同じ実画素を並べる。
    sheet = np.concatenate([np.clip(frames[i] * 255.0, 0, 255).astype(np.uint8) for _, i in picks], axis=1)
    path = dst / "contact_sheet.png"
    Image.fromarray(sheet).save(path)
    out.append(path)
    return out


def _figure_outputs(focus: dict, failures: list[dict], inspection_dir: str | None) -> tuple[list[Path], int, tuple[int, int]]:
    """Emit the required visual evidence / 図・動画と検分用コマを作る。"""
    run, measured, summary = focus["run"], focus["measured"], focus["summary"]
    n = len(run["rows"])
    movie = _comparison_movie(focus)
    idx = (0, n // 2, n - 1)
    figs.save_grid("two_camera_input_output", [movie[i] for i in idx],
                   ["分離 / separation", "逆噴射 / boostback", "接地後 / after touchdown"], ncols=3,
                   caption="holdout seed %d の固定 2 カメラ。橙の十字は RGB からの計測、緑は後から重ねた MuJoCo 真値。"
                           "位置中央値 %.3f m、傾き中央値 %.3f°。" %
                   (focus["seed"], summary["position_median_m"], summary["tilt_median_deg"]))
    figs.save_video("separation_landing_video", movie,
                    caption="固定の地上追尾カメラ(左)と着陸台カメラ(右)。分離から着陸までの %d コマ、%.1f fps。"
                            "橙=RGB計測、緑=真値表示。" % (len(movie), 1.0 / run["dt_sample"]),
                    fps=1.0 / run["dt_sample"], gif_every=max(1, len(movie) // 72), gif_width=960)
    truth = np.asarray([r["truth_center"] for r in run["rows"]])
    est = np.asarray([r["center"] for r in measured["series"]])
    figs.save_plot("trajectory_truth_vs_rgb", [("MuJoCo truth x-z", truth[:, 0], truth[:, 2]),
                                                  ("RGB + calibrated triangulation x-z", est[:, 0], est[:, 2])],
                   kinds=["line", "scatter"], xlabel="x [m]", ylabel="z [m]",
                   caption="holdout の第1段 3-D 軌跡。RGBの重心を 2 視点の camera.triangulate で復元し、"
                           "真値との距離は中央値 %.3f m、最大 %.3f m。" %
                   (summary["position_median_m"], summary["position_max_m"]))
    vc = summary["vision_contact"]
    figs.save_table("holdout_error_table",
                    ["量 / quantity", "RGB計測", "MuJoCo真値", "誤差 / error"],
                    [["位置 [m] (median)", "-", "-", "%.3f" % summary["position_median_m"]],
                     ["傾き [deg] (median)", "-", "-", "%.3f" % summary["tilt_median_deg"]],
                     ["炎の画像軸 [deg] (median)", "-", "-", "%.3f" % summary["flame_angle_median_deg"]],
                     ["接地時刻 [s]", "%.2f" % vc["time_s"], "%.2f" % summary["truth_contact"]["time_s"],
                      "%.3f" % abs(vc["time_s"] - summary["truth_contact"]["time_s"])],
                     ["接地速さ [m/s]", "%.3f" % vc["speed_mps"], "%.3f" % summary["truth_contact"]["speed_mps"],
                      "%.3f" % abs(vc["speed_mps"] - summary["truth_contact"]["speed_mps"])],
                     ["台中心から [m]", "%.3f" % vc["offset_m"], "%.3f" % summary["truth_contact"]["offset_m"],
                      "%.3f" % abs(vc["offset_m"] - summary["truth_contact"]["offset_m"]) ]],
                    title="holdout RGB 計測と MuJoCo 真値",
                    caption="画面中の数値はこの実行の run から作った値。成功判定は RGB と真値の両方で一致した。")
    inspection = _write_inspection(movie, vc["index"] if vc else None, inspection_dir)
    # The two deliberate failures keep their own RGB video.  Use a Lanczos
    # display reduction for the compact GIF; no source measurement is resized.
    snapshots = []
    labels = []
    for rec in failures:
        failure_movie = _comparison_movie(rec)
        snapshots.append(failure_movie[_truth_contact_index(rec)])
        c = rec["summary"]["truth_contact"]
        labels.append("%s: truth/RGB = fail/fail, t=%.2f s" %
                      (rec["kind"], c["time_s"] if c else float("nan")))
        gif_frames = _gif_resize(failure_movie[::3])
        figs.save_gif("%s_rgb_failure" % rec["kind"], gif_frames,
                      caption="%s seed %d。固定2カメラ RGB の橙=計測、緑=MuJoCo真値。"
                              "真値/RGB の成功判定は %s/%s で、成功を返さない。" %
                      (rec["kind"], rec["seed"], rec["summary"]["truth_success"], rec["summary"]["vision_success"]),
                      fps=1.0 / (run["dt_sample"] * 3))
        del failure_movie, gif_frames
    figs.save_grid("failure_cases_rgb_truth", snapshots, labels, ncols=2,
                   caption="意図した燃料不足と強風。各画像は真値接触時刻に最も近い RGB コマで、"
                           "橙=RGB 計測、緑=MuJoCo 真値。両ケースを fail-closed として不成功にする。")
    return inspection, len(movie), movie[0].shape[:2]


def main() -> int:
    """Run the full first-stage PoC / 第1段の物理・映像・失敗判定を実行する。"""
    parser = argparse.ArgumentParser(description="MuJoCo/RGB reusable-rocket landing PoC")
    parser.add_argument("--ci", action="store_true", help="use the documented 320x240 reduced rendering mode")
    parser.add_argument("--inspection-dir", default=os.environ.get("FULLSEYE_ROCKET_INSPECTION_DIR", ""),
                        help="directory outside the repository for full-size inspection frames")
    args = parser.parse_args()
    ci = bool(args.ci or os.environ.get("CI") == "1")
    t0 = time.time()
    print("== reusable two-stage landing: MuJoCo truth -> fixed RGB cameras -> Fullseye measurement (%s)" %
          ("CI=1 320x240 / 0.15 s" if ci else "full 512x384 / 0.10 s"))

    # -- Physics invariants / 物理の不変量 ------------------------------------------------------------
    ff = rl.mujoco_free_fall_check()
    gate("推力 0 の MuJoCo 自由落下は閉形式 z(t), v(t) と一致", ff["height_error_m"] < 1e-9 and ff["velocity_error_mps"] < 1e-9,
         "|dz| %.1e m, |dv| %.1e m/s" % (ff["height_error_m"], ff["velocity_error_mps"]))
    fuel = rl.NOMINAL_FUEL
    masses, fuels = [], []
    for _ in range(32):
        fuel, _ = rl.propellant_step(fuel, 175.0)
        fuels.append(fuel); masses.append(rl.DRY_MASS + fuel)
    gate("燃料消費: 正の推力 32 刻で燃料と質量が単調に減る", bool(np.all(np.diff(fuels) < 0) and np.all(np.diff(masses) < 0)),
         "fuel %.3f -> %.3f kg, mass %.3f -> %.3f kg" % (rl.NOMINAL_FUEL, fuels[-1], rl.DRY_MASS + rl.NOMINAL_FUEL, masses[-1]))
    wind_a = np.vstack([rl.fixed_wind(41, t, 12.0) for t in (0.0, 1.0, 2.0)])
    wind_b = np.vstack([rl.fixed_wind(41, t, 12.0) for t in (0.0, 1.0, 2.0)])
    gate("風 seed=41 は再現し、異なる seed は同じ列にならない", np.array_equal(wind_a, wind_b) and not np.array_equal(wind_a, np.vstack([rl.fixed_wind(42, t, 12.0) for t in (0.0, 1.0, 2.0)])),
         "wind[0]=(%+.2f,%+.2f) N" % tuple(wind_a[0, :2]))

    # -- Cases / 調整用・holdout・意図した失敗 ------------------------------------------------------
    plan = [("tuning", "nominal", 3), ("tuning", "nominal", 11),
            ("holdout", "nominal", 41), ("holdout", "nominal", 57),
            ("failure", "fuel_shortage", 7), ("failure", "strong_wind", 19)]
    records = []
    for split, kind, seed in plan:
        run = rl.run_case(rl.case_spec(kind, seed), ci=ci,
                          keep_frames=(split == "holdout" and seed == 41) or split == "failure")
        observed = rl.measure_from_rgb(run)
        summary = rl.summarise(run, observed)
        rec = {"split": split, "kind": kind, "seed": seed, "run": run, "measured": observed, "summary": summary}
        records.append(rec)
        c = summary["truth_contact"]
        v = summary["vision_contact"]
        print("  %-8s %-13s seed=%2d pos median/max %.3f/%.3f m  tilt median %.3f deg  flame %.3f deg  truth/vision=%s/%s" %
              (split, kind, seed, summary["position_median_m"], summary["position_max_m"], summary["tilt_median_deg"],
               summary["flame_angle_median_deg"], summary["truth_success"], summary["vision_success"]))
        if c is not None:
            print("      contact truth t=%.2f s v=%.3f m/s tilt=%.2f deg offset=%.3f m; RGB %s" %
                  (c["time_s"], c["speed_mps"], c["tilt_deg"], c["offset_m"],
                   "unobserved -> fail closed" if v is None else "t=%.2f v=%.3f tilt=%.2f offset=%.3f" %
                   (v["time_s"], v["speed_mps"], v["tilt_deg"], v["offset_m"])))

    tune = [r for r in records if r["split"] == "tuning"]
    hold = [r for r in records if r["split"] == "holdout"]
    fail = [r for r in records if r["split"] == "failure"]
    for name, group in (("調整用", tune), ("holdout", hold)):
        st = _group_stats(group)
        all_ok = all(r["summary"]["truth_success"] and r["summary"]["vision_success"] and r["summary"]["decision_match"] for r in group)
        gate("%s: RGB と真値の成功判定が全 %d 回で一致" % (name, len(group)), all_ok,
             "pos median %.3f m, max %.3f m; tilt median %.3f deg; flame median %.3f deg" %
             (st["pos_med_m"], st["pos_max_m"], st["tilt_med_deg"], st["flame_med_deg"]))
    fail_ok = all((not r["summary"]["truth_success"]) and (not r["summary"]["vision_success"])
                  and r["summary"]["decision_match"] for r in fail)
    gate("失敗2回(燃料不足・強風)を RGB 判定が見逃さない", fail_ok,
         "; ".join("%s truth/vision=%s/%s" % (r["kind"], r["summary"]["truth_success"], r["summary"]["vision_success"]) for r in fail))

    # A second full plant run checks seed reproducibility, not merely the wind
    # helper / 風の関数だけでなくプラント全体を同じ seed で再走する。
    repeat = rl.run_case(rl.case_spec("nominal", 3), ci=ci, keep_frames=False)
    a = np.asarray([x["truth_center"] for x in tune[0]["run"]["rows"]])
    b = np.asarray([x["truth_center"] for x in repeat["rows"]])
    gate("MuJoCo + PID + 風の同一 seed 再走は真値軌跡が bit 一致", a.shape == b.shape and np.array_equal(a, b),
         "samples %d" % len(a))

    focus = next(r for r in hold if r["seed"] == 41)
    inspection: list[Path] = []
    frames, shape = 0, (0, 0)
    # CI's no-figure path deliberately avoids display-only rendering.  An
    # explicit inspection directory still renders the full-size evidence.
    if figs.enabled() or args.inspection_dir:
        inspection, frames, shape = _figure_outputs(focus, fail, args.inspection_dir or None)
    if figs.enabled():
        gate("図と動画を書き出せた", not figs.errors(), "; ".join(figs.errors()) if figs.errors() else "%d video frames, %dx%d px" % (frames, shape[1], shape[0]))
    if inspection:
        print("  inspection frames: " + ", ".join(str(p) for p in inspection))
    elif args.inspection_dir:
        gate("検分用コマを指定先へ書き出せた", False, args.inspection_dir)

    print("== result: %d / %d gates, %.1f s" % (sum(ok for _, ok in GATES), len(GATES), time.time() - t0))
    print("PASS" if all(ok for _, ok in GATES) else "FAIL")
    return 0 if all(ok for _, ok in GATES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
