# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 公開された .zmx 処方を独立実装と照合し、検査レンズとして採点する。

収蔵番号 2026.270。無限遠作動距離、入口瞳径 1 mm、256×256 画素、画素ピッチ 5.5 µm の
センサーを仮定する。EFL/BFL、実光線、重心まわり RMS スポットを記録済みの
独立計算と照合し、照明、歪曲、倍率色、ナイキスト周波数の 1/4 における MTF、
角の 3 画素幅傷のコントラストで検査用途を採点する。

限界: 軸外 OPD は参照球と内部絞りの瞳写像の規約が異なり、光線座標が一致しても
ピーク比で数 % 違う。この差を図に残し、OPD を精密な一致の根拠にはしない。
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import lensfile as LF  # noqa: E402
import lensimage as LI  # noqa: E402
import lensmerit as LM  # noqa: E402
import optics as O  # noqa: E402
import raytrace as RT  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(ROOT, "tests", "data")
LENS = os.path.join(DATA, "lensfile")
REF = json.load(open(os.path.join(DATA, "zmx_public_ref.json"), encoding="utf-8"))
FILES = sorted(REF["prescriptions"])
PITCH = 5.5
SHAPE = (256, 256)
GATES = []
NUMBERS = {}


def gate(label, ok, value=""):
    GATES.append(bool(ok))
    print("  %s %-54s %s" % ("PASS" if ok else "FAIL", label, value))


def systems():
    return {name: LF.lens_file_read(os.path.join(LENS, name)) for name in FILES}


def inspection_stop(system):
    """Operate every prescription with a 1 mm entrance-pupil diameter."""
    out = dict(system)
    out["surfaces"] = [dict(v) for v in system["surfaces"]]
    out["surfaces"][system["stop"]]["ap"] = 0.5
    return out


def independent_differences(items):
    rows = []
    for name, p in items.items():
        ref = REF["prescriptions"][name]
        pa = RT.paraxial_trace(p["system"])
        rms = RT.spot_stats(p["system"], field=max(ref["fields_deg"]), rings=3, pupil_fill=0.8)["rms_radius"]
        rr = ref["spots"][str(len(ref["fields_deg"]) - 1)]["rms_mm"]
        rows.append([name.replace(".zmx", ""), pa["efl"], pa["efl"] - ref["efl_mm"],
                     pa["bfl"], pa["bfl"] - ref["bfl_mm"], rms, rms - rr])
    worst_f = max(abs(r[2]) / abs(r[1]) for r in rows)
    worst_b = max(abs(r[4]) / abs(r[3]) for r in rows)
    # RMS uses each reader's own pupil mapper in the table; the strict test replays identical launch rays.
    gate("EFL/BFL の相対差 < 1e-9", worst_f < 1e-9 and worst_b < 1e-9,
         "EFL %.2e, BFL %.2e" % (worst_f, worst_b))
    figs.save_table("independent_verification",
                    ["処方", "EFL", "差", "BFL", "差", "RMS", "差"], rows,
                    title="独立計算との照合 [mm]",
                    caption="4 処方。最大相対差は EFL %.2e、BFL %.2e。RMS は各読取器の瞳写像による値。" % (worst_f, worst_b))
    NUMBERS.update(worst_efl_rel=worst_f, worst_bfl_rel=worst_b)


def spot_figure(items):
    panels, caps = [], []
    for name in ("triplet_catalog.zmx", "double_gauss_const.zmx"):
        p = items[name]
        for field in p["fields"][:3]:
            b = RT.ray_bundle(p["system"], field=field["y"], rings=5, pupil_fill=0.8)
            xy = b["image_xy"][b["valid"]]
            xy -= xy.mean(0)
            lim = max(0.005, float(np.max(np.abs(xy))))
            canvas = np.zeros((180, 180))
            q = np.clip(((xy / (2.2 * lim) + 0.5) * 179).astype(int), 0, 179)
            canvas[q[:, 1], q[:, 0]] = 1
            rms = float(np.sqrt(np.mean(np.sum(xy * xy, axis=1))))
            panels.append(canvas); caps.append("%s, %.1f°, RMS %.1f µm" % (name[:-4], field["y"], rms * 1e3))
    figs.save_grid("spot_diagrams", panels, caps, title="3 視野のスポット (各列の尺度は個別)", ncols=3,
                   caption="2 処方、3 視野。各パネルの RMS は同じ実光線から計算。")
    p = items["triplet_catalog.zmx"]
    max_field = max(f["y"] for f in p["fields"])
    frames = []
    for field in np.linspace(0.0, max_field, 32):
        b = RT.ray_bundle(p["system"], field=float(field), rings=6, pupil_fill=0.8)
        xy = b["image_xy"][b["valid"]]
        xy -= xy.mean(0)
        canvas = np.zeros((240, 240))
        q = np.clip(((xy / 0.04 + 0.5) * 239).astype(int), 0, 239)
        canvas[q[:, 1], q[:, 0]] = 1.0
        frames.append(figs.video_frame(canvas, "視野角 %.1f°" % field, gray=True))
    assert len(frames) >= 24
    assert np.ptp(np.stack(frames).astype(np.int16), axis=0).max() > 0
    figs.save_video("spot_field_sweep", frames, caption="同じ処方のスポットを軸上から最大視野まで掃引する。",
                    fps=10.0, gif_every=2, gif_fps=5.0, gif_width=480)


def inspection(items):
    rows, rendered = [], []
    yy, xx = np.indices(SHAPE)
    image = np.full(SHAPE, 0.78)
    scratch = (np.abs(xx - (210 + 0.35 * (yy - 190))) <= 1.5) & (yy > 160) & (yy < 244)
    image[scratch] = 0.18
    for name, p in items.items():
        s = inspection_stop(p["system"]); fields = [f["y"] for f in p["fields"]]; corner = max(fields)
        ri = math.cos(math.radians(corner)) ** 4
        dist = LI.distortion_map(s, SHAPE, PITCH, fields=np.linspace(0, corner, 9))["max_distortion_pct"]
        wavelengths = tuple(w["um"] for w in p["wavelengths"])
        colour = RT.chromatic_shift(s, wavelengths, field=corner, rings=3)["lateral_color"] if len(wavelengths) > 1 else 0.0
        rms = RT.spot_stats(s, field=corner, rings=4, pupil_fill=0.8)["rms_radius"]
        psf = LI.psf_from_opd(s, field=corner, size=None, pixel_pitch_um=PITCH, oversample=8)
        mtf = O.psf_to_mtf(psf, pixel_pitch_um=PITCH)
        target = 0.25 * (1000.0 / (2 * PITCH))
        mtf_q = float(np.interp(target, mtf[:, 0], mtf[:, 1]))
        out = LI.render_through_lens(image, s, pixel_pitch_um=PITCH, field_of_view=corner,
                                     zones=2, noise=None, size=None, oversample=8)
        defect = float(np.mean(out[(scratch) & (xx > 190)]))
        bg = float(np.mean(out[(~scratch) & (xx > 190) & (yy > 160)]))
        contrast = (bg - defect) / max(bg, 1e-12)
        rendered.append(out)
        score = sum((ri >= 0.75, abs(dist) <= 2.0, rms * 1e3 <= PITCH,
                     abs(colour) * 1e3 / PITCH <= 1.0, mtf_q >= 0.2, contrast >= 0.1))
        rows.append([name[:-4], ri, dist, rms * 1e3 / PITCH, colour * 1e3 / PITCH, mtf_q, contrast, score])
    figs.save_table("inspection_scores", ["処方", "隅照明", "歪曲%", "RMS/px", "倍率色px", "MTF", "傷 contrast", "点/6"], rows,
                    title="検査レンズ採点: WD=∞, 入口瞳1 mm, 256², 5.5 µm",
                    caption="合格条件は照明≥0.75、|歪曲|≤2 %、RMS≤1 px、|倍率色|≤1 px、MTF≥0.2、傷 contrast≥0.1。")
    figs.save_grid("scratch_visibility", [image] + rendered, ["入力: 3 px 傷"] + [n[:-4] for n in FILES],
                   title="角の 3 px 傷", ncols=3,
                   caption="出力から測った傷 contrast は %.3f〜%.3f。" % (min(r[6] for r in rows), max(r[6] for r in rows)))
    NUMBERS.update(min_defect_contrast=min(r[6] for r in rows), max_defect_contrast=max(r[6] for r in rows))


def opd_limit(items):
    vals = []
    for name, p in items.items():
        ref = REF["prescriptions"][name]; s = p["system"]
        for fi, rv in ref["opd_waves"].items():
            px, py = RT._pupil_grid(3)
            w, valid = LM._opd_points(s, ref["fields_deg"][int(fi)], ref["primary_wavelength_um"], px, py)
            a = np.asarray(rv); ok = valid & np.isfinite(a)
            peak = np.max(np.abs(a[ok]))
            vals.append([ref["fields_deg"][int(fi)], 0 if peak < 1e-12 else np.max(np.abs(w[ok] - a[ok])) / peak * 100, name[:-4]])
    series = []
    for name in FILES:
        q = sorted((x for x in vals if x[2] == name[:-4]))
        series.append((name[:-4], [x[0] for x in q], [x[1] for x in q]))
    worst = max(x[1] for x in vals)
    figs.save_plot("opd_convention_limit", series, xlabel="視野角 [deg]", ylabel="ピーク OPD 比の差 [%]",
                   title="参照球・瞳写像の規約差",
                   caption="光線座標の門とは別に、軸外 OPD は最大 %.2f %% 違う。規約差を精度とは数えない。" % worst)
    NUMBERS["worst_opd_percent"] = worst


def main():
    c0 = time.process_time()
    print("公開 .zmx 処方の照合と検査レンズ採点 (収蔵番号 2026.270)")
    print("作動距離=∞、入口瞳径=1 mm、センサー=256×256、画素ピッチ=5.5 µm")
    items = systems()
    independent_differences(items); spot_figure(items); inspection(items); opd_limit(items)
    print("\n門")
    figures_enabled = figs.enabled()
    figure_count = len(figs.manifest())
    gate("4 処方を読み、図を 6 枚作る",
         len(items) == 4 and (not figures_enabled or figure_count == 6),
         "図 %s" % (figure_count if figures_enabled else "出力なし"))
    print("\n%d/%d PASS" % (sum(GATES), len(GATES)))
    figure_errors = figs.errors()
    if figure_errors:
        print("図の書き出しで失敗:", "; ".join(figure_errors))
    if not all(GATES) or figure_errors:
        raise SystemExit(1)
    print("所要 CPU %.1f s" % (time.process_time() - c0))
    print("PASS")


if __name__ == "__main__":
    main()
