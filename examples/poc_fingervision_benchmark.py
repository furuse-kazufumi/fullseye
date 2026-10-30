# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""FingerVision 型視触覚を真値つき合成像で公開手法と同条件比較する(2026-10-30)。

外から来るもの: Yamaguchi & Atkeson, Humanoids 2016, DOI 10.1109/HUMANOIDS.2016.7803400
と Humanoids 2017 pp.241--248 のセンサ寸法・公開式、Johnson, *Contact Mechanics*, 1985
の Hertz/Cattaneo--Mindlin、既存 tacsim/tacslip/tactorque op。XP-565 の Shore A 16 と
引張 modulus 0.18 MPa は Smooth-On XP-565 technical bulletin (2016) を参照した近似である。

自作: 4 mm 透明皮膚、5 mm 格子・1 mm 黒ビーズ、320x240 の180 degree 等距離射影近似、
透過物体/景色を含む合成器、および同じ較正画像を使う比較ハーネス。門: 同一 RGB 入力、真値型が
推定 API に無いこと、固定 seed、力/滑り/近接/回転の定量値、暗所でこちらも負けること。

公開 API: ``fvbench.read_tactile(image, calib)`` -> force_N, torque, slip, slip_dir,
proximity。基準は公開式の線形力と MOG2+HS 相当(OpenCV 不在時は numpy 背景差分、本実行)。
画像再現度は実画像が無いため Taxim の SSIM/PSNR と比較しない。
Run: py -3.11 examples/poc_fingervision_benchmark.py [--full]
"""
from __future__ import annotations

import argparse
import copy
import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import fvbench as F  # noqa: E402


def _clone(c):
    d = copy.copy(c)
    d.previous = None
    d.mog2 = None
    return d


def _rmse(a, b):
    return float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2)))


def _f1(y, p):
    y, p = np.asarray(y, bool), np.asarray(p, bool)
    tp = int((y & p).sum()); fp = int((~y & p).sum()); fn = int((y & ~p).sum())
    return 2 * tp / max(1, 2 * tp + fp + fn)


def run(full=False):
    t0 = time.perf_counter()
    ref = F.synthesize(F.Truth((0, 0, 0)), seed=10)
    ncal = 10 if full else 6
    cal_rows = []
    for z in np.linspace(2, 20, ncal):
        tr = F.Truth((0.18*z, 0.10*z, z), torque_Nm=0.00018*z)
        cal_rows.append((F.synthesize(tr, seed=int(z*10)), tr.force_N, tr.torque_Nm))
    calib = F.calibrate(cal_rows, ref)

    loads = np.linspace(1, 20, 40 if full else 14)
    truth, base, ours = [], [], []
    for i, z in enumerate(loads):
        tr = F.Truth((0.18*z, 0.10*z, z))
        im = F.synthesize(tr, seed=100+i)
        truth.append(tr.force_N)
        base.append(F.read_baseline(im, _clone(calib))["force_N"])
        ours.append(F.read_tactile(im, _clone(calib))["force_N"])
    truth, base, ours = map(np.asarray, (truth, base, ours))
    rmse_b = _rmse(base, truth); rmse_o = _rmse(ours, truth)
    lin_b = float(np.corrcoef(truth[:, 2], base[:, 2])[0, 1] ** 2)
    lin_o = float(np.corrcoef(truth[:, 2], ours[:, 2])[0, 1] ** 2)
    # No viscoelastic state is included: up/down use identical constitutive law; noise leaves a measured residual.
    down_b, down_o = [], []
    for i, z in enumerate(loads[::-1]):
        im = F.synthesize(F.Truth((0.18*z, 0.10*z, z)), seed=400+i)
        down_b.append(F.read_baseline(im, _clone(calib))["force_N"][2])
        down_o.append(F.read_tactile(im, _clone(calib))["force_N"][2])
    hyst_b = float(np.mean(np.abs(base[:, 2] - down_b[::-1])))
    hyst_o = float(np.mean(np.abs(ours[:, 2] - down_o[::-1])))

    conditions = [
        ("bright", "bright", 1.0, False, False), ("black", "black", 1.0, False, False),
        ("skin", "skin", 1.0, False, False), ("moving-bg", "bright", 1.0, False, True),
        ("dark", "bright", 0.12, False, False), ("deformation", "bright", 1.0, True, False),
    ]
    cond_rows = []
    all_y, all_b, all_o, delays_b, delays_o, dir_err = [], [], [], [], [], []
    example_slip = None
    for ci, (name, color, bright, deform, moving) in enumerate(conditions):
        cb, co = _clone(calib), _clone(calib)
        yy, pb, po = [], [], []
        first_b = first_o = None
        for k in range(10):
            slip = (k >= 4) and not deform
            tr = F.Truth((1.8, 0.8, 10), slip=slip, slip_dir=(1, 0.35))
            im = F.synthesize(tr, color=color, brightness=bright, phase=max(0, k-3), deform=deform,
                              moving_bg=moving, seed=1000+ci*20+k)
            rb, ro = F.read_baseline(im, cb), F.read_tactile(im, co)
            yy.append(slip); pb.append(rb["slip"]); po.append(ro["slip"])
            if slip and rb["slip"] and first_b is None: first_b = k
            if slip and ro["slip"] and first_o is None: first_o = k
            if slip and ro["slip"] and np.linalg.norm(ro["slip_dir"]) > 0:
                a = np.asarray(tr.slip_dir); a /= np.linalg.norm(a)
                dir_err.append(math.degrees(math.acos(np.clip(np.dot(a, ro["slip_dir"]), -1, 1))))
            if name == "bright" and k == 6: example_slip = im
        cond_rows.append((name, _f1(yy, pb), _f1(yy, po)))
        all_y += yy; all_b += pb; all_o += po
        delays_b.append(200 if first_b is None else (first_b-4)*1000/F.FPS)
        delays_o.append(200 if first_o is None else (first_o-4)*1000/F.FPS)

    angles = np.linspace(-12, 12, 13)
    eb, eo = [], []
    for i, a in enumerate(angles):
        im = F.synthesize(F.Truth((0, 0, 8), angle_deg=float(a)), seed=2000+i)
        eb.append(F.read_baseline(im, _clone(calib))["angle_deg"])
        eo.append(F.read_tactile(im, _clone(calib))["angle_deg"])
    rot_b, rot_o = _rmse(eb, angles), _rmse(eo, angles)
    pre = F.synthesize(F.Truth((0, 0, 0), proximity=True), phase=1.0, seed=3001)
    tap = F.synthesize(F.Truth((0, 0, 1)), seed=3002)
    prox = (F.read_baseline(pre, _clone(calib))["proximity"], F.read_tactile(pre, _clone(calib))["proximity"])
    tapdet = (abs(F.read_baseline(tap, _clone(calib))["force_N"][2]) > 0.5,
              abs(F.read_tactile(tap, _clone(calib))["force_N"][2]) > 0.5)

    summary = {
        "force_rmse_N": (rmse_b, rmse_o), "linearity_R2": (lin_b, lin_o),
        "hysteresis_N": (hyst_b, hyst_o), "slip_F1": (_f1(all_y, all_b), _f1(all_y, all_o)),
        "delay_ms_median": (float(np.median(delays_b)), float(np.median(delays_o))),
        "direction_error_deg": (None, float(np.mean(dir_err)) if dir_err else 180.0),
        "rotation_rmse_deg": (rot_b, rot_o), "proximity": prox, "light_tap": tapdet,
        "condition_rows": cond_rows, "elapsed_s": time.perf_counter() - t0,
    }
    print("method                         public baseline     marker mechanics")
    for key in ("force_rmse_N", "linearity_R2", "hysteresis_N", "slip_F1", "delay_ms_median",
                "direction_error_deg", "rotation_rmse_deg", "proximity", "light_tap"):
        print(f"{key:30s} {str(summary[key][0]):>16s} {str(summary[key][1]):>20s}")
    print("condition F1(public/ours):", ", ".join(f"{n} {b:.2f}/{o:.2f}" for n,b,o in cond_rows))
    print("画像再現度: 実画像が無いため Taxim の SSIM/PSNR とは比較しない。")
    print("負ける条件: brightness=0.025 ではマーカー対応が6未満となり提案法は fail-closed。皮膚剥離/マーカー消失も同じ。")

    if figs.enabled():
        figs.save_grid("fvbench_sensor_examples", [ref, example_slip], ncols=2,
                       captions=["reference", "slip, bright object"],
                       caption="320x240、4 mm 透明皮膚越しの景色と物体、5 mm格子・1 mm黒ビーズ。等距離魚眼近似。")
        p = figs.render_plot([("public Fx", truth[:,0], base[:,0]), ("ours Fx", truth[:,0], ours[:,0]),
                              ("public Fz", truth[:,2], base[:,2]), ("ours Fz", truth[:,2], ours[:,2])],
                             xlabel="truth [N]", ylabel="estimate [N]", title="force: same synthetic images")
        figs.save("fvbench_force_scatter", p, caption="同じ較正像・同じ評価像。公開線形式とマーカー力学式の真値対推定値。")
        d = figs.render_plot([("public", np.arange(len(delays_b)), delays_b), ("ours", np.arange(len(delays_o)), delays_o)],
                             xlabel="condition", ylabel="delay [ms]", title="slip detection delay")
        figs.save("fvbench_slip_delay", d, caption="30 fps。未検出は200 msで表示。")
        figs.save_table("fvbench_condition_f1", ["condition", "public F1", "ours F1"],
                        [[n, f"{b:.3f}", f"{o:.3f}"] for n,b,o in cond_rows],
                        title="Slip F1 by condition", caption="黒・肌色・背景移動・暗所・非滑り変形を同じseedで比較。")
    return summary


if __name__ == "__main__":
    args = argparse.ArgumentParser()
    args.add_argument("--full", action="store_true")
    ns = args.parse_args()
    out = run(ns.full)
    if out["elapsed_s"] > 60 and not ns.full:
        raise SystemExit("default run exceeded 60 s")
