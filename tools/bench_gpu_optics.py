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
#: GPU の取り合いを防ぐロック。worktree の 2 つ上の tools/ に置く運用(環境変数で上書きできる)。
LOCK = os.environ.get("FULLSEYE_GPU_LOCK") or os.path.normpath(os.path.join(ROOT, "..", "..", "tools", "gpu_in_use.lock"))


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


#: 実寸: 2448 x 2048 の偏光センサ(IMX250MZR 系)8 枚。
POL_H, POL_W, POL_B = 2048, 2448, 8


def _pol_inputs():
    rng = np.random.default_rng(0)
    raw = rng.random((POL_B, POL_H, POL_W))
    y, x = np.mgrid[-0.7:0.7:POL_H * 1j, -0.7:0.7:POL_W * 1j]
    z = np.sqrt(np.clip(1.0 - x * x - y * y, 1e-6, None))
    nrm = np.stack([x, y, z], -1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    s0 = 1.0 + rng.random((POL_H, POL_W))
    k = rng.random((POL_H, POL_W, 3)) - 0.5
    k = k / np.linalg.norm(k, axis=-1, keepdims=True) * (0.8 * s0)[..., None]
    stokes = np.concatenate([s0[..., None], k], -1)
    delta = np.tile(rng.uniform(-6.0, 6.0, (POL_H, POL_W)), (POL_B, 1, 1))
    theta = rng.uniform(0.0, 180.0, (POL_H, POL_W))
    return raw, nrm, stokes, delta, theta


def polar_numpy():
    """既存の CPU 実装(numpy / scipy)。stokes_analyze はスカラー API なので Python ループと、同じ式の numpy 場の両方を測る。"""
    import optics
    import photoelastic
    import sfpolar
    raw, nrm, stokes, delta, theta = _pol_inputs()
    out = {}

    def t(fn):
        t0 = time.perf_counter()
        fn()
        return time.perf_counter() - t0

    out["demosaic_8"] = t(lambda: [optics.polarization_demosaic(r) for r in raw])
    out["photoelastic_8"] = t(lambda: [photoelastic.photoelastic_polarization_images(d, theta) for d in delta])
    out["sfp_render_8"] = t(lambda: [sfpolar.sfp_render(nrm, 1.5, 0.7, 0.3) for _ in range(POL_B)])
    rho = np.clip(stokes[..., 1] ** 2, 0.0, 1.0)
    out["dolp_to_zenith_1"] = t(lambda: sfpolar.dolp_to_zenith(rho, 1.5, "specular", out_of_range="clamp"))

    def field():
        s0, s1, s2, s3 = stokes[..., 0], stokes[..., 1], stokes[..., 2], stokes[..., 3]
        pol = np.sqrt(s1 * s1 + s2 * s2 + s3 * s3)
        lin = np.hypot(s1, s2)
        np.degrees(0.5 * np.arctan2(s2, s1)) % 180.0
        np.degrees(0.5 * np.arcsin(np.clip(s3 / pol, -1.0, 1.0)))
        np.minimum(pol / s0, 1.0), np.minimum(lin / s0, 1.0), np.minimum(np.abs(s3) / s0, 1.0)

    out["stokes_analyze_numpy_field_1"] = t(field)
    t0 = time.perf_counter()
    flat = stokes.reshape(-1, 4)
    done = 0
    for row in flat:
        optics.stokes_analyze(row)
        done += 1
        if done % 1000 == 0 and time.perf_counter() - t0 > CPU_LIMIT_S:
            break
    out["stokes_analyze_python_loop"] = {"pixels_asked": len(flat), "pixels_done": done,
                                         "seconds": time.perf_counter() - t0, "truncated": done < len(flat)}

    def muel():
        a = optics._mueller_field("retarder", "retarder", theta, 30.0)
        b = optics.mueller_element("polarizer", 20.0)
        c = optics.mueller_element("quarter_wave", 45.0)
        m = c @ a @ b
        np.einsum("...ij,...j->...i", m, stokes)

    out["mueller_chain_field_1"] = t(muel)
    return out


def polar(device, dtype="float64"):
    import torch

    import lens_gpu as LG
    import polar_gpu as PG
    raw, nrm, stokes, delta, theta = _pol_inputs()
    ang = theta

    def sync():
        if device != "cpu":
            torch.cuda.synchronize()

    def run(fn, n=3):
        ts = []
        for _ in range(n):
            t0 = time.perf_counter()
            fn()
            sync()
            ts.append(time.perf_counter() - t0)
        return {"first_s": ts[0], "best_s": min(ts[1:])}

    out = {"dtype": dtype, "device": device}
    out["demosaic_8"] = run(lambda: PG.polarization_demosaic_batch(raw, device=device, dtype=dtype).cpu())
    out["photoelastic_8"] = run(lambda: PG.photoelastic_images_batch(delta, theta, device=device, dtype=dtype).cpu())
    out["sfp_render_8"] = run(lambda: PG.sfp_render_batch(np.tile(nrm, (POL_B, 1, 1, 1)), 1.5, 0.7, 0.3, device=device, dtype=dtype).cpu())
    rho = np.clip(stokes[..., 1] ** 2, 0.0, 1.0)
    out["dolp_to_zenith_1"] = run(lambda: PG.dolp_to_zenith_batch(rho, 1.5, "specular", device=device, dtype=dtype)["zenith_deg"].cpu())
    out["stokes_analyze_field_1"] = run(
        lambda: {k: v.cpu() for k, v in PG.stokes_analyze_batch(torch.as_tensor(stokes, dtype=LG._dtype(dtype), device=device)).items()})

    def muel():
        a = PG.mueller_element_batch("retarder", ang, 30.0, device=device, dtype=dtype)
        b = PG.mueller_element_batch("polarizer", 20.0, device=device, dtype=dtype)
        c = PG.mueller_element_batch("quarter_wave", 45.0, device=device, dtype=dtype)
        torch.einsum("...ij,...j->...i", PG.chain([b, a, c]),
                     torch.as_tensor(stokes, dtype=a.dtype, device=device)).cpu()

    out["mueller_chain_field_1"] = run(muel)
    sys_, field = subjects()["triplet"]

    def pol_rays(m):
        def f():
            d = LG.tolerance_draws(RT._freeze_solves(sys_), trials=m, seed=0)
            ov = {k: d[k] for k in ("R", "t", "offset", "decenter", "tilt")}
            lens = LG.compile_lens(sys_, np.linspace(0.47, 0.67, 31), device=device, dtype=dtype, overrides=ov)
            PG.polarized_bundle(lens, field=field, rings=6)["jones"].cpu()
        return f

    out["polarized_rays_1000x31x127"] = run(pol_rays(1000))
    out["polarized_rays_1x1x127"] = run(lambda: PG.polarized_bundle(LG.compile_lens(sys_, device=device, dtype=dtype),
                                                                    field=field, rings=6)["jones"].cpu())
    if device != "cpu":
        out["peak_gpu_bytes"] = int(torch.cuda.max_memory_allocated())
    return out


def parity(device):
    """既存の CPU 実装との一致を実測して表にする(テストの題材をそのまま使う)。"""
    import torch

    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import test_lens_gpu as T

    import lens_gpu as G
    keys = T.SCALARS
    wl = [RT.WL_F, RT.WL_D, RT.WL_C]
    out = {}
    for name in sorted(T.SYSTEMS):
        s = T.SYSTEMS[name]()
        fld = T.FIELD[name]
        p = G.paraxial_batch(G.compile_lens(s, wl, device=device))
        rel = 0.0
        for w, x in enumerate(wl):
            q = RT.paraxial_trace(RT.with_wavelength(s, x))
            rel = max(rel, max(T.rel(p[k][0, w], q[k]) for k in keys))
        cpu = RT.ray_bundle(s, field=fld, rings=8, wavelength_um=RT.WL_C)
        P0, D0 = cpu["points"][:, 0, :], cpu["dirs"][:, 0, :]
        ref = RT.trace_rays(s, P0, D0, wavelength_um=RT.WL_C)
        lens = G.compile_lens(s, [RT.WL_C], device=device)
        tr = G.trace_batch(lens, tuple(torch.as_tensor(P0[:, j], device=lens.device)[None, None] for j in range(3)),
                           tuple(torch.as_tensor(D0[:, j], device=lens.device)[None, None] for j in range(3)), points=True)
        v = tr["valid"][0, 0].cpu().numpy()
        got = tr["points"][0, 0].cpu().numpy()
        mism = int((v != ref["valid"]).sum())
        both = v & ref["valid"]
        dpos = float(np.abs(got[both][:, -1, :] - ref["points"][both][:, -1, :]).max())
        dopl = float(np.abs(tr["opl"][0, 0].cpu().numpy()[both] - ref["opl"][both]).max())
        b = G.bundle_batch(G.compile_lens(s, device=device), field=fld, rings=6, pupil_fill=0.99)
        st = G.spot_stats_batch(b)
        c = RT.spot_stats(s, field=fld, rings=6, pupil_fill=0.99)
        out[name] = {"paraxial_rel_max": rel, "rays": len(v), "valid_rays": int(v.sum()), "valid_mismatch": mism,
                     "position_mm_max": dpos, "opl_mm_max": dopl,
                     "spot_rms_mm_diff": abs(float(st["rms_radius"][0, 0]) - c["rms_radius"])}
    for name, fld in (("catalog_doublet", 1.0), ("triplet", 14.0)):
        s = T.SYSTEMS[name]()
        sysf = RT._freeze_solves(s)
        tol = {"radius_pct": 0.5, "thickness_mm": 0.05, "index": 0.001, "decenter_mm": 0.02, "tilt_deg": 0.05}
        rng = np.random.default_rng(3)
        img = sysf["surfaces"][-1]["t"]
        e, r = [], []
        for _ in range(1000):
            q = RT._perturbed(sysf, rng, tol)
            pp = RT.paraxial_trace(q)
            sp = RT.spot_stats(q, field=fld, rings=6, pupil_fill=0.99, image_mm=pp["image_mm"] if img is None else img)
            e.append(pp["efl"])
            r.append(sp["rms_radius"])
        m = G.tolerance_monte_carlo(s, trials=1000, seed=3, field=fld, device=device)
        out["mc_" + name] = {"trials": 1000, "efl_rel_max": float(np.max(np.abs(m["efl_trial"] - e) / np.abs(e))),
                             "rms_mm_max": float(np.max(np.abs(m["rms_trial"] - r))), "failed": m["failed"]}
    return out


def float32_errors():
    """float32 の誤差を float64 と比べて測る(同じ入力、CPU の torch)。"""
    import polar_gpu as PG

    import lens_gpu as LG
    res = {}
    for name, (sys_, field) in subjects().items():
        a = LG.bundle_batch(LG.compile_lens(sys_, [0.48, 0.59, 0.66], device="cpu", dtype="float32"), field=field, rings=6)
        b = LG.bundle_batch(LG.compile_lens(sys_, [0.48, 0.59, 0.66], device="cpu"), field=field, rings=6)
        v = (a["valid"] & b["valid"]).numpy()
        pa = LG.paraxial_batch(LG.compile_lens(sys_, device="cpu", dtype="float32"))["efl"].item()
        pb = LG.paraxial_batch(LG.compile_lens(sys_, device="cpu"))["efl"].item()
        res[name] = {"ray_position_mm_max": float(np.abs(a["y"].numpy().astype(float) - b["y"].numpy())[v].max()),
                     "efl_rel": abs(pa - pb) / abs(pb), "valid_differs": int((a["valid"] != b["valid"]).sum())}
        ma = LG.tolerance_monte_carlo(sys_, trials=2000, field=field, device="cpu", dtype="float32")
        mb = LG.tolerance_monte_carlo(sys_, trials=2000, field=field, device="cpu")
        res[name]["mc_rms_rel_max"] = float(np.nanmax(np.abs(ma["rms_trial"] - mb["rms_trial"]) / mb["rms_trial"]))
    raw = np.random.default_rng(0).random((1, 256, 256))
    e = PG.polarization_demosaic_batch(raw, dtype="float32").numpy().astype(float) - PG.polarization_demosaic_batch(raw).numpy()
    res["demosaic_max_abs_unit_scale"] = float(np.abs(e).max())
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline", action="store_true")
    ap.add_argument("--batch", choices=("cpu", "cuda"))
    ap.add_argument("--polar", choices=("numpy", "cpu", "cuda"))
    ap.add_argument("--float32-errors", action="store_true")
    ap.add_argument("--parity", choices=("cpu", "cuda"))
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.baseline:
        res = {"baseline": baseline()}
    elif a.parity == "cpu":
        res = {"parity": parity("cpu")}
    elif a.parity == "cuda":
        why = gpu_busy()
        if why:
            print("GPU busy, not started:", why)
            return 3
        with GpuLock("gpu_optics_%d" % os.getpid()):
            res = {"parity": parity("cuda")}
    elif a.float32_errors:
        res = {"float32": float32_errors()}
    elif a.polar == "numpy":
        res = {"polar": polar_numpy()}
    elif a.polar == "cuda":
        why = gpu_busy()
        if why:
            print("GPU busy, not started:", why)
            return 3
        with GpuLock("gpu_optics_%d" % os.getpid()):
            res = {"polar64": polar("cuda"), "polar32": polar("cuda", "float32")}
    elif a.polar == "cpu":
        res = {"polar64": polar("cpu"), "polar32": polar("cpu", "float32")}
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
