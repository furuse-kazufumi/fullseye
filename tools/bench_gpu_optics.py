# -*- coding: utf-8 -*-
"""GPU 第 4 便の測定: raytrace の CPU 基準と lens_gpu の一括経路を同じ題材で測る。

    py -3.11 tools/bench_gpu_optics.py --baseline --out cpu.json
    <loco venv>/python tools/bench_gpu_optics.py --batch cpu --out batch_cpu.json
    <loco venv>/python tools/bench_gpu_optics.py --batch cuda --out batch_gpu.json

★ GPU はこの道具が取り合いの門を見る。ロックファイルが在る間、または UnrealEditor が
居る間は ``--batch cuda`` を始めない(exit 3)。自分のロックは必ず消す。
★ 90 s を超えた CPU 測定は打ち切り、外挿せず ``truncated`` と書く。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402

import lensfile  # noqa: E402
import raytrace as RT  # noqa: E402

CPU_LIMIT_S = 90.0
LOCK = os.environ.get("FULLSEYE_GPU_LOCK", os.path.join("C:" + os.sep, "dev", "tools", "gpu_in_use.lock"))


#: 実演 1: 公差 MC(設計 × 波長 × 光線)。実演 2: 波長を細かく振った色収差とスポットの曲線。
DEMO_TRIALS, DEMO_MC_RINGS = 10000, 12
DEMO_MC_WL = np.linspace(0.47, 0.67, 31)
DEMO_SWEEP_WL, DEMO_SWEEP_RINGS = np.linspace(0.45, 0.70, 2501), 16


def triplet():
    """同梱の Cooke triplet(f ≈ 50 mm、絞りが中間面。chief ray の照準が要る代表)。"""
    return lensfile.lens_file_read()["system"]


def subjects():
    return {"catalog_doublet": (RT.example_system("catalog_doublet"), 1.0),
            "triplet": (triplet(), 14.0)}


def timed(fn, min_s=0.2, max_n=2000):
    n, t0 = 0, time.perf_counter()
    while True:
        fn()
        n += 1
        dt = time.perf_counter() - t0
        if dt >= min_s or n >= max_n:
            return dt / n, n


def mc_cpu(system, field, trials, limit=CPU_LIMIT_S, rings=6):
    """raytrace.tolerance_analysis の MC ループ本体を、打ち切りつきで実時間で回す(感度表は含まない)。"""
    system = RT._freeze_solves(system)
    tol = {"radius_pct": 0.5, "thickness_mm": 0.05, "index": 0.001, "decenter_mm": 0.02, "tilt_deg": 0.05}
    rng = np.random.default_rng(0)
    img = system["image_mm"] if system["image_mm"] is not None else system["surfaces"][-1]["t"]
    if img is None:
        img = RT.paraxial_trace(system)["image_mm"]
    t0 = time.perf_counter()
    done = fail = 0
    for _ in range(trials):
        if time.perf_counter() - t0 > limit:
            break
        try:
            s = RT._perturbed(system, rng, tol)
            RT.paraxial_trace(s)
            RT.spot_stats(s, field=field, rings=rings, pupil_fill=0.99, image_mm=img)
        except (ValueError, FloatingPointError):
            fail += 1
        done += 1
    return {"trials_asked": trials, "trials_done": done, "failed": fail, "seconds": time.perf_counter() - t0,
            "truncated": done < trials, "rings": rings, "rays_per_trial": len(RT._pupil_grid(rings)[0])}


def chrom_cpu(system, field, wls, limit=CPU_LIMIT_S):
    t0 = time.perf_counter()
    r = RT.chromatic_shift(system, wavelengths=list(map(float, wls)), field=field, rings=6)
    return {"n_wavelengths": len(wls), "seconds": time.perf_counter() - t0, "truncated": False,
            "rms_polychromatic": r["rms_polychromatic"]}


def mc_wl_cpu(system, field, trials, wls, rings, limit=CPU_LIMIT_S):
    """実演 1 の CPU 側: 設計案 × 波長 × 光線。打ち切ったら打ち切ったと返す。"""
    system = RT._freeze_solves(system)
    tol = {"radius_pct": 0.5, "thickness_mm": 0.05, "index": 0.001, "decenter_mm": 0.02, "tilt_deg": 0.05}
    rng = np.random.default_rng(0)
    img = system["image_mm"] if system["image_mm"] is not None else system["surfaces"][-1]["t"]
    if img is None:
        img = RT.paraxial_trace(system)["image_mm"]
    t0 = time.perf_counter()
    done = 0
    for _ in range(trials):
        s = RT._perturbed(system, rng, tol)
        cut = False
        for w in wls:
            try:
                RT.spot_stats(s, field=field, rings=rings, pupil_fill=0.99, image_mm=img, wavelength_um=float(w))
            except ValueError:
                pass
            if time.perf_counter() - t0 > limit:
                cut = True
                break
        if cut:
            break
        done += 1
    return {"trials_asked": trials, "trials_done": done, "n_wavelengths": len(wls), "rings": rings,
            "rays_per_case": len(RT._pupil_grid(rings)[0]), "seconds": time.perf_counter() - t0, "truncated": done < trials}


def sweep_cpu(system, field, wls, rings, limit=CPU_LIMIT_S):
    """実演 2 の CPU 側: chromatic_shift と同じ計算を波長ごとに、打ち切りつきで。"""
    t0 = time.perf_counter()
    ref = RT.paraxial_trace(system)
    img = system["image_mm"] if system["image_mm"] is not None else (
        system["surfaces"][-1]["t"] if system["surfaces"][-1]["t"] is not None else ref["bfl"])
    done = 0
    for w in wls:
        if time.perf_counter() - t0 > limit:
            break
        sw = RT.with_wavelength(system, float(w))
        RT.paraxial_trace(sw)
        RT.ray_bundle(sw, field=field, rings=rings, image_mm=img)
        done += 1
    return {"wavelengths_asked": len(wls), "wavelengths_done": done, "rings": rings,
            "rays_per_case": len(RT._pupil_grid(rings)[0]), "seconds": time.perf_counter() - t0, "truncated": done < len(wls)}


def baseline():
    out = {}
    for name, (sys_, field) in subjects().items():
        para = RT.paraxial_trace(sys_)
        b = RT.ray_bundle(sys_, field=field, rings=6)
        P, D, _ = RT._launch(sys_, *RT._pupil_grid(6), field, para)
        row = {"n_surfaces": len(sys_["surfaces"]), "stop": sys_["stop"], "efl": para["efl"],
               "n_valid_rays": int(b["valid"].sum()), "n_rays": len(b["valid"])}
        row["paraxial_trace_s"] = timed(lambda: RT.paraxial_trace(sys_))[0]
        row["trace_rays_127_s"] = timed(lambda: RT.trace_rays(sys_, P, D))[0]
        row["chromatic_shift_3wl_s"] = timed(lambda: RT.chromatic_shift(sys_, field=field))[0]
        row["chromatic_shift_301wl"] = chrom_cpu(sys_, field, np.linspace(0.45, 0.70, 301))
        row["mc_10000"] = mc_cpu(sys_, field, 10000)
        row["demo_mc"] = mc_wl_cpu(sys_, field, DEMO_TRIALS, DEMO_MC_WL, DEMO_MC_RINGS)
        row["demo_sweep"] = sweep_cpu(sys_, field, DEMO_SWEEP_WL, DEMO_SWEEP_RINGS)
        out[name] = row
        print(name, json.dumps(row), flush=True)
    return out


def gpu_busy():
    """他の使い手が居るなら理由を返す。"""
    if os.path.exists(LOCK):
        with open(LOCK, encoding="utf-8", errors="replace") as f:
            return "lock: " + f.read().strip()
    try:
        out = subprocess.run(["tasklist"], capture_output=True, text=True, errors="replace", timeout=30).stdout
    except (OSError, subprocess.TimeoutExpired) as e:
        return "tasklist failed: %s" % e
    if "unrealeditor" in out.lower():
        return "UnrealEditor is running"
    return None


class GpuLock:
    """自分の名前のロック。O_EXCL で作り、抜けるとき必ず消す。"""

    def __init__(self, name):
        self.name = name

    def __enter__(self):
        fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, ("%s %s" % (self.name, time.strftime("%Y-%m-%dT%H:%M:%S"))).encode())
        os.close(fd)
        return self

    def __exit__(self, *exc):
        os.remove(LOCK)


def batch(device):
    import torch

    import lens_gpu as G

    def sync():
        if device != "cpu":
            torch.cuda.synchronize()

    def run(fn, n=3):
        """転送込みの時間(最初の 1 回を別に返す。起動の遅れを平均に混ぜない)。"""
        ts = []
        for _ in range(n):
            t0 = time.perf_counter()
            fn()
            sync()
            ts.append(time.perf_counter() - t0)
        return {"first_s": ts[0], "best_s": min(ts[1:]) if n > 1 else ts[0]}

    out = {}
    for name, (sys_, field) in subjects().items():
        row = {}

        def par1():
            G.paraxial_batch(G.compile_lens(sys_, device=device))["efl"].cpu()

        def ray1():
            G.bundle_batch(G.compile_lens(sys_, device=device), field=field, rings=6)["y"].cpu()

        def chrom(wls, rings=6):
            def f():
                G.chromatic_batch(G.compile_lens(sys_, wls, device=device), field=field, rings=rings)["rms_spot"].cpu()
            return f

        row["paraxial_1"] = run(par1, 5)
        row["bundle_127"] = run(ray1, 5)
        row["chromatic_3wl"] = run(chrom([RT.WL_F, RT.WL_D, RT.WL_C]), 5)
        row["chromatic_301wl"] = run(chrom(np.linspace(0.45, 0.70, 301)))

        def mc10k():
            row["_mc"] = G.tolerance_monte_carlo(sys_, trials=10000, field=field, device=device, seed=0)

        row["mc_10000"] = run(mc10k, 2)
        row["mc_10000_failed"] = row.pop("_mc")["failed"]

        def demo_mc():
            row["_mc"] = G.tolerance_monte_carlo(sys_, trials=DEMO_TRIALS, field=field, rings=DEMO_MC_RINGS,
                                                 wavelengths=DEMO_MC_WL, device=device)

        row["demo_mc"] = run(demo_mc, 2)
        r = row.pop("_mc")
        row["demo_mc_summary"] = {"failed": r["failed"], "chunk": r["chunk"], "rms_spot_mean": r["rms_spot"]["mean"]}
        row["demo_sweep"] = run(chrom(DEMO_SWEEP_WL, DEMO_SWEEP_RINGS), 2)

        def mtf():
            G.mtf_batch(G.compile_lens(sys_, np.linspace(0.47, 0.67, 31), device=device), field=field, size=64,
                        frequency_cpmm=[10.0, 30.0])["tangential"].cpu()

        row["mtf_31wl_64"] = run(mtf, 3)
        out[name] = row
        print(name, json.dumps(row), flush=True)
    if device != "cpu":
        out["peak_gpu_bytes"] = int(torch.cuda.max_memory_allocated())
        out["gpu_name"] = torch.cuda.get_device_name(0)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline", action="store_true")
    ap.add_argument("--batch", choices=("cpu", "cuda"))
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.baseline:
        res = {"baseline": baseline()}
    elif a.batch == "cuda":
        why = gpu_busy()
        if why:
            print("GPU busy, not started:", why)
            return 3
        with GpuLock("gpu_optics_%d" % os.getpid()):
            res = {"batch": batch("cuda")}
    else:
        res = {"batch": batch("cpu")}
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
