# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""CT の CPU / GPU 実測(docs/perf/gpu_ct_2026-11-02.json を段ごとに更新する)。

    py -3.11 tools/bench_gpu_ct.py cpu                      既存 op の CPU 基準(GPU を使わない)
    <venv>/python tools/bench_gpu_ct.py gpu_parallel        同じ寸法の GPU 経路と parity
    <venv>/python tools/bench_gpu_ct.py fdk 512 720         コーンビーム FDK の実寸の実演
    <venv>/python tools/bench_gpu_ct.py iter 256 180        反復法の収束曲線
    <venv>/python tools/bench_gpu_ct.py gates 96            全方式の画質
    <venv>/python tools/bench_gpu_ct.py parity              GPU と CPU の一致

★測り方。GPU の時間は入力の転送から結果が host に戻るまでで、`torch.cuda.synchronize()`
を挟む(op が host へ戻す時点で同期する)。CPU は 1 件 90 秒で打ち切り、外挿しない。打ち切りは
子プロセスで実行して kill するので、打ち切った op の値は無い。
"""
from __future__ import annotations

import json
import multiprocessing as mp
import os
import platform
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import ctscan  # noqa: E402
import tomography as T  # noqa: E402
import tomography_gpu as G  # noqa: E402

OUT = os.path.join(ROOT, "docs", "perf", "gpu_ct_2026-11-02.json")
CACHE = os.environ.get("GPU_CT_CACHE", os.path.join(ROOT, ".gpu_ct_cache"))
CPU_LIMIT_S = 90.0


def load():
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def save(key, value):
    data = load()
    data[key] = value
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")


def host_info():
    info = {"python": platform.python_version(), "numpy": np.__version__,
            "cpu_threads": os.cpu_count()}
    try:
        import torch
        info["torch"] = torch.__version__
        if torch.cuda.is_available():
            info["gpu"] = torch.cuda.get_device_name(0)
            info["vram_total_gb"] = round(torch.cuda.get_device_properties(0).total_memory / 2**30, 1)
    except ImportError:
        pass
    return info


def rmse(a, b):
    return float(np.sqrt(np.mean((np.asarray(a, np.float64) - b) ** 2)))


def psnr(a, b, peak=1.0):
    return float(20.0 * np.log10(peak / max(rmse(a, b), 1e-12)))


def ssim(a, b, peak=1.0):
    """Wang ら 2004 の SSIM(11 画素の一様窓、スライス平均の形で 2-D に使う)。"""
    from scipy.ndimage import uniform_filter
    a = np.asarray(a, np.float64)
    b = np.asarray(b, np.float64)
    c1, c2 = (0.01 * peak) ** 2, (0.03 * peak) ** 2
    ma, mb = uniform_filter(a, 11), uniform_filter(b, 11)
    va = uniform_filter(a * a, 11) - ma * ma
    vb = uniform_filter(b * b, 11) - mb * mb
    cov = uniform_filter(a * b, 11) - ma * mb
    return float(np.mean((2 * ma * mb + c1) * (2 * cov + c2)
                         / ((ma * ma + mb * mb + c1) * (va + vb + c2))))


def _worker(queue, name, kwargs):
    t = time.perf_counter()
    result = CPU_CASES[name](**kwargs)
    queue.put(time.perf_counter() - t)
    os.makedirs(CACHE, exist_ok=True)
    np.save(os.path.join(CACHE, cache_name(name, kwargs)), result)


def cache_name(name, kwargs):
    return "%s_%s.npy" % (name, "_".join("%s%s" % kv for kv in sorted(kwargs.items())))


def _image(n):
    return T.ellipse_phantom(n, supersample=1)


def _angles(views):
    return np.linspace(0.0, 180.0, views, endpoint=False)


def _sino(n, views):
    return T.ellipse_sinogram(n, None, _angles(views), T._default_detectors(n, n))


def cpu_radon(n, views):
    return T.radon_transform(_image(n), _angles(views))


def cpu_bp(n, views):
    return T.backproject_sinogram(_sino(n, views), _angles(views))


def cpu_fbp(n, views):
    return T.filtered_backprojection(_sino(n, views), _angles(views))


def cpu_sart(n, views):
    return T.sart_reconstruct(_sino(n, views), _angles(views), n_iter=1)


def _volume(n):
    return ctscan.shepp_logan_3d(n, supersample=1)


def cpu_radon_volume(n, views):
    return T.radon_volume(_volume(n), _angles(views))


def _stack(n, views):
    d = T._default_detectors(n, n)
    return np.stack([T.ellipse_sinogram(n, None, _angles(views), d)] * n)


def cpu_fbp_volume(n, views):
    return T.fbp_volume(_stack(n, views), _angles(views))


CPU_CASES = {"radon_transform": cpu_radon, "backproject_sinogram": cpu_bp,
             "filtered_backprojection": cpu_fbp, "sart_reconstruct": cpu_sart,
             "radon_volume": cpu_radon_volume, "fbp_volume": cpu_fbp_volume}

SLICES = [(512, 512), (1024, 512), (2048, 512)]
VOLUMES = [(256, 180), (256, 512)]
CASES = ([(op, dict(n=n, views=v)) for op in
          ("radon_transform", "backproject_sinogram", "filtered_backprojection", "sart_reconstruct")
          for n, v in SLICES]
         + [(op, dict(n=n, views=v)) for op in ("radon_volume", "fbp_volume") for n, v in VOLUMES])


def stage_cpu():
    rows = []
    for name, kwargs in CASES:
        queue = mp.Queue()
        proc = mp.Process(target=_worker, args=(queue, name, kwargs))
        t = time.perf_counter()
        proc.start()
        status = "timeout"
        seconds = None
        while time.perf_counter() - t < CPU_LIMIT_S + 30.0:
            if not queue.empty():
                seconds = queue.get()
                status = "ok" if seconds <= CPU_LIMIT_S else "over_limit"
                break
            if not proc.is_alive() and queue.empty():
                status = "refused"
                break
            time.sleep(0.2)
        if seconds is not None:
            proc.join(30)
        proc.terminate()
        rows.append({"op": name, **kwargs, "status": status, "seconds": seconds})
        print(rows[-1], flush=True)
        save("cpu_baseline", {"host": host_info(), "limit_s": CPU_LIMIT_S, "rows": rows})


def _gpu_call(name, n, views):
    a = _angles(views)
    if name == "radon_transform":
        x = _image(n)
        return lambda: G.radon_transform(x, a, device="cuda")
    if name == "radon_volume":
        x = _volume(n).astype(np.float32)
        return lambda: G.radon_volume(x, a, device="cuda")
    if name == "fbp_volume":
        x = _stack(n, views).astype(np.float32)
        return lambda: G.fbp_volume(x, a, device="cuda")
    s = _sino(n, views)
    if name == "backproject_sinogram":
        return lambda: G.backproject_sinogram(s, a, device="cuda")
    if name == "filtered_backprojection":
        return lambda: G.filtered_backprojection(s, a, device="cuda")
    return lambda: G.sart_reconstruct(s, a, n_iter=1, device="cuda")


def stage_gpu_parallel():
    rows = []
    for name, kwargs in CASES:
        fn = _gpu_call(name, kwargs["n"], kwargs["views"])
        G.reset_gpu_memory_peak()
        t = time.perf_counter()
        out = fn()
        seconds = time.perf_counter() - t
        row = {"op": name, **kwargs, "seconds": seconds,
               "vram_peak_gb": G.gpu_memory_peak_bytes() / 2**30}
        path = os.path.join(CACHE, cache_name(name, kwargs))
        if os.path.exists(path):
            ref = np.load(path, mmap_mode="r")
            diff = np.abs(np.asarray(ref) - out)
            row["parity_max"] = float(diff.max())
            row["parity_rms"] = float(np.sqrt(np.mean(diff ** 2)))
            row["reference_peak"] = float(np.abs(ref).max())
        rows.append(row)
        print(row, flush=True)
        save("gpu_parallel", {"host": host_info(), "rows": rows})


def _planes(n, zs):
    """真値の断面だけを閉形式で求める(全ボリュームを host に持たないため)。"""
    half = n / 2.0
    c = (np.arange(n, dtype=np.float64) - (n - 1) / 2.0) / half
    out = {}
    for k in zs:
        z = (k - (n - 1) / 2.0) / half
        plane = np.zeros((n, n))
        for x0, y0, z0, a, b, cc, phi, rho in ctscan.SHEPP_LOGAN_3D:
            rest = 1.0 - ((z - z0) / cc) ** 2
            if rest <= 0.0:
                continue
            ph = np.deg2rad(phi)
            dx = c[None, :] - x0
            dy = c[:, None] - y0
            p = dx * np.cos(ph) + dy * np.sin(ph)
            q = -dx * np.sin(ph) + dy * np.cos(ph)
            plane += np.where((p / a) ** 2 + (q / b) ** 2 <= rest, rho, 0.0)
        out[k] = plane
    return out


def stage_fdk(n, views):
    import torch
    geom = ctscan.ct_scan_geometry("cone", n_views=views, n_u=int(1.5 * n), n_v=int(1.5 * n),
                                   vol_shape=n, voxel=1.0, dso=3.0 * n, dsd=6.0 * n, du=2.0, dv=2.0)
    G.reset_gpu_memory_peak()
    t = time.perf_counter()
    proj = ctscan.ellipsoid_projections(geom, device="cuda").astype(np.float32)
    t_proj = time.perf_counter() - t
    print("analytic", t_proj, proj.shape, flush=True)
    G.reset_gpu_memory_peak()
    t = time.perf_counter()
    rec = ctscan.fdk_reconstruct(proj, geom, device="cuda")
    torch.cuda.synchronize()
    t_fdk = time.perf_counter() - t
    peak = G.gpu_memory_peak_bytes() / 2**30
    zs = [n // 2, n // 4, 3 * n // 8, 5 * n // 8]
    truth = _planes(n, zs)
    quality = {str(k): {"rmse": rmse(rec[k], truth[k]), "psnr_db": psnr(rec[k], truth[k]),
                        "ssim": ssim(rec[k], truth[k])} for k in zs}
    row = {"size": n, "views": views, "detector": [geom["n_v"], geom["n_u"]],
           "seconds_fdk": t_fdk, "seconds_analytic_projection": t_proj,
           "gvoxel_views_per_s": n ** 3 * views / t_fdk / 1e9, "vram_peak_gb": peak,
           "quality_by_slice": quality, "host": host_info()}
    print(row, flush=True)
    save("fdk_%d_%d" % (n, views), row)


def stage_iter(n, views, only=None):
    """反復法の収束曲線。*only* = 0 SIRT, 1 OS-SART, 2 TV だけ(1 回 10 分の枠に収める)。"""
    import torch
    geom = ctscan.ct_scan_geometry("cone", n_views=views, n_u=3 * n // 2, n_v=3 * n // 2,
                                   vol_shape=n, du=2.0, dv=2.0)
    proj = ctscan.ellipsoid_projections(geom, device="cuda").astype(np.float32)
    truth = ctscan.shepp_logan_3d(n, supersample=1)
    result = load().get("iter_%d_%d" % (n, views), {"size": n, "views": views, "host": host_info()})
    fbp = ctscan.fdk_reconstruct(proj, geom, device="cuda")
    result["fdk_rmse"] = rmse(fbp, truth)
    routes = [("sirt", ctscan.sirt_reconstruct, {"n_iter": 25}),
              ("os_sart", ctscan.os_sart_reconstruct, {"n_iter": 5, "n_subsets": 12}),
              ("tv", ctscan.tv_reconstruct, {"n_iter": 25})]
    if only is not None:
        routes = [routes[only]]
    for name, fn, kw in routes:
        curve = []
        G.reset_gpu_memory_peak()
        t = time.perf_counter()

        def record(k, x, curve=curve, t=t):
            curve.append({"iteration": k + 1, "elapsed_s": time.perf_counter() - t,
                          "rmse": rmse(x, truth)})
            print(name, curve[-1], flush=True)

        fn(proj, geom, device="cuda", on_iter=record, **kw)
        torch.cuda.synchronize()
        result[name] = {"params": kw, "curve": curve, "seconds_total": time.perf_counter() - t,
                        "vram_peak_gb": G.gpu_memory_peak_bytes() / 2**30}
        save("iter_%d_%d" % (n, views), result)


def scan_table(n):
    half = float(np.rad2deg(np.arctan(n * 2.0 / (6.0 * n))))
    h = 3 * n // 8
    return [
        ("cone", dict(scan="cone", n_views=2 * n, n_u=2 * n, n_v=2 * n, vol_shape=n), "fdk"),
        ("helical", dict(scan="helical", n_views=8 * n, n_u=2 * n, n_v=h, vol_shape=n, pitch=0.5), "fdk"),
        ("laminography_parallel_60deg", dict(scan="laminography", n_views=2 * n, n_u=2 * n, n_v=2 * n,
                                             vol_shape=n, tilt_deg=60.0, du=1.0, dv=1.0), "fdk"),
        ("laminography_cone_60deg", dict(scan="laminography", n_views=2 * n, n_u=2 * n, n_v=2 * n,
                                         vol_shape=n, tilt_deg=60.0, dso=4.0 * n, dsd=8.0 * n), "fdk"),
        ("fan_flat", dict(scan="fan", n_views=2 * n, n_u=2 * n, n_v=1, vol_shape=(1, n, n)), "fdk"),
        ("fan_arc", dict(scan="fan", n_views=2 * n, n_u=2 * n, n_v=1, vol_shape=(1, n, n),
                         detector="arc"), "fdk"),
        ("short_scan_parker", dict(scan="cone", n_views=n + n // 2, n_u=2 * n, n_v=2 * n, vol_shape=n,
                                   arc_deg=182.0 + 2.0 * half), "fdk"),
        ("offset_detector", dict(scan="cone", n_views=2 * n, n_u=3 * n // 2, n_v=2 * n, vol_shape=n,
                                 offset_u=n / 3.0), "fdk"),
        ("tomosynthesis_sirt", dict(scan="tomosynthesis", n_views=31, n_u=2 * n, n_v=2 * n, vol_shape=n,
                                    arc_deg=60.0, start_deg=-30.0), "sirt"),
    ]


def stage_gates(n):
    rows = []
    for name, kwargs, how in scan_table(n):
        geom = ctscan.ct_scan_geometry(**kwargs)
        shape = geom["vol_shape"]
        truth = ctscan.ellipsoid_phantom(shape, None, supersample=1 if shape[0] > 1 else 2)
        proj = ctscan.ellipsoid_projections(geom, device="cuda").astype(np.float32)
        t = time.perf_counter()
        if how == "fdk":
            rec = ctscan.fdk_reconstruct(proj, geom, device="cuda")
        else:
            rec = ctscan.sirt_reconstruct(proj, geom, n_iter=30, device="cuda")
        seconds = time.perf_counter() - t
        mid = shape[0] // 2
        row = {"scan": name, "route": how, "views": geom["n_views"], "seconds": seconds,
               "rmse": rmse(rec, truth), "psnr_db": psnr(rec, truth),
               "ssim_mid": ssim(rec[mid], truth[mid]), "rmse_mid": rmse(rec[mid], truth[mid])}
        rows.append(row)
        print(row, flush=True)
        save("gates_%d" % n, {"size": n, "rows": rows, "host": host_info()})


def stage_parity():
    """GPU と CPU の一致。CPU が 90 秒に収まらない寸法は view を間引いて補間の定義を比べる。"""
    rows = []

    def add(name, cpu, gpu):
        a, g = np.asarray(cpu(), np.float64), np.asarray(gpu(), np.float64)
        diff = np.abs(a - g)
        rows.append({"case": name, "parity_max": float(diff.max()),
                     "parity_rms": float(np.sqrt(np.mean(diff ** 2))),
                     "reference_peak": float(np.abs(a).max()), "reference_std": float(a.std())})
        print(rows[-1], flush=True)
        save("parity", {"rows": rows, "host": host_info()})

    for n in (1024, 2048):
        img = _image(n)
        ang = _angles(8)
        add("radon_transform %d, 8 views" % n, lambda: T.radon_transform(img, ang),
            lambda: G.radon_transform(img, ang, device="cuda"))
    vol = _volume(64).astype(np.float64)
    ang = _angles(90)
    add("radon_volume 64, 90 views", lambda: T.radon_volume(vol, ang),
        lambda: G.radon_volume(vol, ang, device="cuda"))
    for name, kw in (("cone", dict(scan="cone", n_views=180, n_u=192, n_v=192, vol_shape=128, du=2.0,
                                   dv=2.0)),
                     ("helical", dict(scan="helical", n_views=360, n_u=128, n_v=32, vol_shape=64,
                                      pitch=0.5)),
                     ("laminography", dict(scan="laminography", n_views=120, n_u=128, n_v=128,
                                           vol_shape=64, du=1.0, dv=1.0)),
                     ("fan_arc", dict(scan="fan", n_views=360, n_u=256, n_v=1, vol_shape=(1, 128, 128),
                                      detector="arc"))):
        geom = ctscan.ct_scan_geometry(**kw)
        add("ellipsoid_projections " + name, lambda: ctscan.ellipsoid_projections(geom, device="cpu"),
            lambda: ctscan.ellipsoid_projections(geom, device="cuda"))
        proj = ctscan.ellipsoid_projections(geom, device="cpu")
        add("fdk " + name, lambda: ctscan.fdk_reconstruct(proj, geom, device="cpu"),
            lambda: ctscan.fdk_reconstruct(proj, geom, device="cuda"))
    geom = ctscan.ct_scan_geometry("cone", n_views=60, n_u=64, n_v=64, vol_shape=32)
    proj = ctscan.ellipsoid_projections(geom, device="cpu")
    add("forward cone 32", lambda: ctscan.ct_forward_project(ctscan.shepp_logan_3d(32), geom, device="cpu"),
        lambda: ctscan.ct_forward_project(ctscan.shepp_logan_3d(32), geom, device="cuda"))
    add("sirt cone 32, 5 iterations", lambda: ctscan.sirt_reconstruct(proj, geom, n_iter=5, device="cpu"),
        lambda: ctscan.sirt_reconstruct(proj, geom, n_iter=5, device="cuda"))
    add("os_sart cone 32, 2 passes",
        lambda: ctscan.os_sart_reconstruct(proj, geom, n_iter=2, n_subsets=6, device="cpu"),
        lambda: ctscan.os_sart_reconstruct(proj, geom, n_iter=2, n_subsets=6, device="cuda"))
    add("tv cone 32, 5 iterations", lambda: ctscan.tv_reconstruct(proj, geom, n_iter=5, device="cpu"),
        lambda: ctscan.tv_reconstruct(proj, geom, n_iter=5, device="cuda"))
    rng = np.random.default_rng(0)
    x = rng.random(geom["vol_shape"])
    y = rng.random((60, 64, 64))
    gaps = {}
    for label, double in (("float32", False), ("float64", True)):
        lhs = float(np.sum(np.asarray(G.forward_project(x, geom, device="cuda", double=double), np.float64) * y))
        rhs = float(np.sum(x * np.asarray(G.adjoint_project(y, geom, device="cuda", double=double), np.float64)))
        gaps[label] = abs(lhs - rhs) / abs(lhs)
    print(gaps, flush=True)
    save("adjoint_gap_gpu", gaps)


def main():
    stage = sys.argv[1]
    args = [int(a) for a in sys.argv[2:]]
    {"cpu": stage_cpu, "gpu_parallel": stage_gpu_parallel, "fdk": stage_fdk, "iter": stage_iter,
     "gates": stage_gates, "parity": stage_parity}[stage](*args)


if __name__ == "__main__":
    main()
