#!/usr/bin/env python3
"""GPU 第 3 便の計測: 候補ごとに CPU(登録経路)と GPU(転送込み)の時間を測り JSON へ残す。

    py tools/gpu_fill3_bench.py cpu 2d          # CPU 側(GPU を使わない)
    py tools/gpu_fill3_bench.py gpu 2d          # GPU 側(loco venv の torch cu128)
    py tools/gpu_fill3_bench.py cpu typed --only radon_transform,piv_cross_correlate

作法(第 2 便を踏襲):
* CPU = 登録経路そのもの(float64、画像 1 枚ずつ)。枚数方向にだけ線形に伸ばす(寸法方向へは外挿しない)。
* GPU = host→device 転送 + op + device→host。初回はウォームアップとして捨て、残り 2 回の短い方を採る。
* 乱数生成は時間に含めない。

GPU を使う前に ``gpu_in_use.lock`` と ``UnrealEditor`` を確かめ、居れば測らずに exit 3。自分の名前で
ロックを作り、9 分で区切って必ず消す。ロックの場所は環境変数 ``FULLSEYE_GPU_LOCK``。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
from scipy import ndimage  # noqa: E402

LOG = ROOT / "docs" / "perf" / "logs"
LIMIT_S = 540.0
TAG = "gpu_agent_fill3_%d" % os.getpid()


def _unreal_alive() -> bool:
    try:
        out = subprocess.run(["tasklist"], capture_output=True, check=False).stdout
    except OSError:
        return True                 # 確かめられないなら「居る」側に倒す(GPU を奪わない)
    return b"unrealeditor" in out.lower()


class GpuLock:
    def __init__(self):
        self.path = Path(os.environ["FULLSEYE_GPU_LOCK"])
        self.mine = False

    def __enter__(self):
        if self.path.exists() or _unreal_alive():
            print("[fill3] GPU is busy (lock or UnrealEditor): not measuring", flush=True)
            raise SystemExit(3)
        self.path.write_text("%s %s\n" % (TAG, time.strftime("%Y-%m-%dT%H:%M:%S")), encoding="utf-8")
        self.mine = True
        return self

    def __exit__(self, *exc):
        if self.mine and self.path.exists() and self.path.read_text(encoding="utf-8").startswith(TAG):
            self.path.unlink()


def _images(n, h, seed=0):
    rng = np.random.default_rng(seed)
    base = rng.random((h, h))
    out = []
    for i in range(n):
        im = ndimage.gaussian_filter(np.roll(base, (i * 7, i * 13), (0, 1)), 1.5) * 3 - 1
        out.append(np.clip(im + rng.random((h, h)) * 0.1, 0, 1))
    return out


# ── 2-D 単入力: 名前 -> (kernel の属性名, 色か, GPU の 1 回のバッチ枚数) ──────────────
TWO_D = {
    "abs_image": ("_abs_image", 0, 50), "acos_image": ("_acos_image", 0, 50), "asin_image": ("_asin_image", 0, 50),
    "atan_image": ("_atan_image", 0, 50), "exp_image": ("_exp_image", 0, 50), "log_image": ("_log_image", 0, 50),
    "sin_image": ("_sin_image", 0, 50), "sqrt_image": ("_sqrt_image", 0, 50), "tan_image": ("_tan_image", 0, 50),
    "gamma_image": ("_gamma_image", 0, 50), "f2_lut_trans": ("_lut_trans", 0, 50),
    "median_rect": ("_median_rect", 0, 10), "mirror_image": ("_mirror_image", 0, 50),
    "it_convert_image_type": ("_convert_image_type", 0, 50), "it_crop_domain": ("_crop_domain", 0, 50),
    "it_crop_part": ("_crop_part", 0, 50), "it_crop_rectangle1": ("_crop_rectangle1", 0, 50),
    "gray_erosion_shape": ("_gray_erosion_shape", 0, 50), "gray_dilation_shape": ("_gray_dilation_shape", 0, 50),
    "gray_opening_shape": ("_gray_opening_shape", 0, 50), "gray_closing_shape": ("_gray_closing_shape", 0, 50),
    "texture_laws": ("_texture_laws", 0, 50), "derivate_gauss": ("_derivate_gauss", 0, 50),
    "affine_trans_image": ("_affine_warp", 0, 25), "affine_warp": ("_affine_warp", 0, 25),
    "affine_trans_image_size": ("_affine_warp", 0, 25), "rotate_image": ("_rotate_image", 0, 25),
    "rotate_img": ("_rotate_image", 0, 25), "zoom_image_factor": ("_zoom_factor", 0, 25),
    "rescale_img": ("_rescale_img", 0, 25), "zoom_image_size": ("_zoom_size", 0, 50),
    "rgb1_to_gray": ("_rgb_to_gray", 1, 25), "rgb3_to_gray": ("_rgb_to_gray", 1, 25),
    "linear_trans_color": ("_linear_trans_color", 1, 25), "principal_comp": ("_principal_comp", 1, 25),
}
#: 2048² の CPU 実測で転送床を超えられない等の判断に使う核なし op も CPU 側は測る
CPU_ONLY = ("polar_trans_image", "polar_trans_image_ext", "polar_trans_image_inv", "cfa_to_rgb",
            "bilateral_filter", "cv_bilateral", "trans_from_rgb", "trans_to_rgb")
NARY = {"add_image": "_nary_add", "sub_image": "_nary_sub", "mult_image": "_nary_mult", "div_image": "_nary_div",
        "abs_diff_image": "_nary_abs_diff", "max_image": "_nary_max", "min_image": "_nary_min",
        "convol_image@9x9": "_nary_convol", "convol_image@31x31": "_nary_convol"}
AB = (0.5, 0.4)


def _color(im):
    return np.stack([im, np.roll(im, 5, 0), np.roll(im, 9, 1)], -1)


def _time(fn):
    t = time.perf_counter()
    fn()
    return time.perf_counter() - t


def cpu_2d(names):
    import ops
    rows = {}
    for size, n_full, n_cpu in ((512, 100, 10), (2048, 50, 3)):
        imgs = _images(n_cpu, size)
        for name in names:
            color = name in TWO_D and TWO_D[name][1] or name in ("trans_from_rgb", "trans_to_rgb")
            xs = [_color(i) for i in imgs] if color else imgs
            fn = ops.RT[name]
            dt = _time(lambda: [fn(x.copy(), *AB) for x in xs])
            # .copy() の時間は引く(第 2 便と同じく前生成の画像で測る)
            dt0 = _time(lambda: [x.copy() for x in xs])
            rows.setdefault(name, {})["%d" % size] = {"n": n_full, "cpu_s": (dt - dt0) / n_cpu * n_full}
            print("cpu %-26s %5d x%-3d %8.2f s" % (name, size, n_full, rows[name]["%d" % size]["cpu_s"]), flush=True)
    return rows


def gpu_2d(names, deadline):
    import accel
    import torch
    rows = {}
    for size, n_full in ((512, 100), (2048, 50)):
        imgs = _images(4, size)
        for name in names:
            if time.time() > deadline:
                return rows
            attr, color, chunk = TWO_D[name]
            fn = getattr(accel, attr)
            base = [_color(i) for i in imgs] if color else imgs
            full = (base * (n_full // len(base) + 1))[:n_full]
            bs = chunk * 2 if size == 512 and chunk < 50 else chunk

            def run():
                for i in range(0, n_full, bs):
                    t = accel._to_batch(full[i:i + bs], "cuda")
                    accel._from_batch(fn(t, AB[0], AB[1], "cuda").clamp(0, 1))
            run()
            torch.cuda.reset_peak_memory_stats()
            dt = min(_time(run), _time(run))
            rows.setdefault(name, {})["%d" % size] = {
                "n": n_full, "gpu_s": dt, "vram_gb": torch.cuda.max_memory_allocated() / 2**30}
            print("gpu %-26s %5d x%-3d %8.3f s" % (name, size, n_full, dt), flush=True)
    return rows


def _nary_inputs(name, size, n):
    imgs = _images(n, size)
    if name.startswith("convol_image"):
        m = int(name.split("@")[1].split("x")[0])
        yy, xx = np.mgrid[-(m // 2):m // 2 + 1, -(m // 2):m // 2 + 1]
        return imgs, np.exp(-(xx * xx + yy * yy) / (2.0 * (m / 4.0) ** 2))
    return imgs, None


def cpu_nary(names):
    import imgops_nary as N
    table = {o.name: o for o in N.build_nary()}
    rows = {}
    for name in names:
        imgs, ker = _nary_inputs(name, 2048, 3)
        fn = table[name.split("@")[0]].fn
        dt = _time(lambda: [fn([x, ker if ker is not None else np.roll(x, 3, 0)], *AB) for x in imgs])
        rows[name] = {"2048": {"n": 50, "cpu_s": dt / 3 * 50}}
        print("cpu %-26s %8.2f s" % (name, rows[name]["2048"]["cpu_s"]), flush=True)
    return rows


def gpu_nary(names, deadline):
    import accel
    rows = {}
    for name in names:
        if time.time() > deadline:
            break
        imgs, ker = _nary_inputs(name, 2048, 4)
        full = (imgs * 13)[:50]
        fn = getattr(accel, NARY[name])

        def run():
            t = accel._to_batch(full, "cuda")
            if ker is not None:
                io = [t, accel._to_batch([ker], "cuda")]
            else:
                io = [t, accel._to_batch([np.roll(x, 3, 0) for x in full], "cuda")]
            accel._from_batch(fn(io, AB[0], AB[1], "cuda"))
        run()
        rows[name] = {"2048": {"n": 50, "gpu_s": min(_time(run), _time(run))}}
        print("gpu %-26s %8.3f s" % (name, rows[name]["2048"]["gpu_s"]), flush=True)
    return rows


def typed_cases():
    """実寸の入力。(名前 -> (説明, 呼び出し f(fn)))。入力の用意は時間に含めない(遅延生成して使い回す)。"""
    import plane_sweep as ps
    import tomography as tm
    rng = np.random.default_rng(1)

    def phantom(n):
        return np.clip(ndimage.gaussian_filter(rng.random((n, n)), n / 64.0) * 6 - 2.5, 0, 1)
    ang = np.linspace(0, 180, 180, endpoint=False)
    im1k = phantom(1024)
    im256 = phantom(256)
    vol = np.stack([phantom(512) for _ in range(8)])
    sino1k = tm.radon_transform(phantom(512), ang, n_detectors=1449)        # 1024² 再構成の入力
    sino256 = tm.radon_transform(im256, ang)
    A = ndimage.gaussian_filter(rng.random((2048, 2048)), 1.2)
    B = np.roll(A, (2, -1), (0, 1))
    fr = [np.roll(A[:1024, :1024], (i, -i), (0, 1)) for i in range(16)]
    K = np.array([[1000., 0, 512], [0, 1000, 512], [0, 0, 1]])
    Rm, t = np.eye(3), np.array([0.1, 0, 0])
    Lref = ndimage.gaussian_filter(rng.random((1024, 1024)), 1.0)
    Lsrc = ps.warp_by_plane(Lref, ps.plane_homography(K, Rm, t, 2.0), order=1, cval=0.0)
    depths = np.linspace(1, 4, 64)
    pts = rng.random((10_000_000, 3)) * 2 - 1
    vid = np.stack([np.clip(im1k + rng.random(im1k.shape) * 0.05, 0, 1) for _ in range(60)])
    lights = np.array([[np.cos(a) * .5, np.sin(a) * .5, 1.] for a in np.linspace(0, 6.28, 12, endpoint=False)])
    stack = np.stack([np.clip(_images(1, 2048, i)[0], 0, 1) for i in range(12)])
    bnd = ((-1, 1), (-1, 1), (-1, 1))
    stack3 = None
    v0 = ndimage.gaussian_filter(rng.random((128, 128, 128)), 1.5) * 4
    v1 = np.roll(v0, 1, 0)

    def sino_stack():
        nonlocal stack3
        if stack3 is None:
            stack3 = tm.radon_volume(vol, ang)
        return stack3
    return {
        "radon_transform": ("1024² 180 views", lambda f: f(im1k, ang)),
        "radon_volume": ("8 x 512² 180 views", lambda f: f(vol, ang)),
        "backproject_sinogram": ("1024² 180 views", lambda f: f(sino1k, ang, size=1024)),
        "filtered_backprojection": ("1024² 180 views", lambda f: f(sino1k, ang, size=1024)),
        "fbp_volume": ("8 x 512² 180 views", lambda f: f(sino_stack(), ang)),
        "sart_reconstruct": ("256² 180 views 3 sweeps", lambda f: f(sino256, ang, size=256, n_iter=3)),
        "piv_cross_correlate": ("2048² win32 ov0.5", lambda f: f(A, B, window=32)),
        "piv_multipass": ("2048² win64/32", lambda f: f(A, B)),
        "piv_ensemble_correlate": ("16 x 1024² win32", lambda f: f(fr, window=32)),
        "plane_sweep_depth": ("1024² 64 depths win5", lambda f: f(Lref, Lsrc, K, Rm, t, depths, window=5)),
        "joint_bilateral": ("2048² sigma 3", lambda f: f(A, B, 3.0, 0.1)),
        "temporal_bilateral": ("60 x 1024² window 5", lambda f: f(vid)),
        "voxel_grid_downsample": ("1e7 points", lambda f: f(pts, 0.01)),
        "occupancy_grid": ("1e7 points 256³", lambda f: f(pts, bnd, 256)),
        "photometric_stereo": ("12 x 2048²", lambda f: f(stack, lights)),
        "points_to_voxel": ("1e7 points 256³", lambda f: f(pts, 256)),
        "scene_flow_lk": ("128³", lambda f: f(v0, v1)),
    }


def run_typed(mode, names, deadline):
    import accel_typed as T
    cases = typed_cases()
    rows = {}
    for name in names:
        if time.time() > deadline:
            break
        desc, call = cases[name]
        module, fname, _k, takes_device = T.CANDIDATES[name]
        core = getattr(__import__(module), fname)
        if mode == "cpu":
            dt = _time(lambda: call(core))
            rows[name] = {"desc": desc, "cpu_s": dt}
        else:
            fn = lambda *a, **k: T.call_candidate(name, *a, device="cuda", **k)   # noqa: E731
            call(fn)
            rows[name] = {"desc": desc, "gpu_s": min(_time(lambda: call(fn)), _time(lambda: call(fn)))}
        print("%s %-26s %-26s %8.3f s" % (mode, name, desc, rows[name][mode + "_s"]), flush=True)
    return rows


def parity_2d(device, names):
    """登録経路との内部差(marg = max(3, k/2+1) を除く)を PARITY_AB 全点で測る。"""
    import accel
    import imgops_nary as N
    import ops
    rng = np.random.default_rng(7)
    base = [np.clip(rng.random((64, 64)) * 0.6 + 0.2 * (np.mgrid[0:64, 0:64][1] / 64), 0, 1) for _ in range(4)]
    smooth = np.clip(ndimage.gaussian_filter(rng.random((64, 80)), 2) * 4 - 1.5, 0, 1)
    gray = [(base, 4), ([np.full((64, 64), 0.42)], 1), ([np.round(base[0] * 255) / 255], 1), ([smooth], 1)]
    col = np.stack([base[0], base[1] * 0.5, smooth[:64, :64]], -1)
    rows = {}
    for name in names:
        attr, color, _c = TWO_D[name]
        fn = getattr(accel, attr)
        worst = full = ptp = 0.0
        groups = [([col, col * 0.7], 2)] if color else gray
        for a, b in accel.PARITY_AB:
            m = max(3, accel._k(a) // 2 + 1)
            for imgs, _n in groups:
                got = accel._from_batch(fn(accel._to_batch(imgs, device), a, b, device).clamp(0, 1))
                for im, g in zip(imgs, got):
                    ref = np.clip(ops.RT[name](im.copy(), a, b), 0, 1)
                    d = np.abs(ref - g)
                    worst = max(worst, float(d[m:-m, m:-m].max()))
                    full = max(full, float(d.max()))
                    ptp = max(ptp, float(np.ptp(ref)))
        rows[name] = {"inner": worst, "full": full, "ref_ptp": ptp}
    table = {o.name: o for o in N.build_nary()}
    x = base[:2]
    y = [np.clip(ndimage.gaussian_filter(rng.random((64, 64)), 1) * 3 - 1, 0, 1) for _ in range(2)]
    for name, attr in NARY.items():
        core = name.split("@")[0]
        fn = getattr(accel, attr)
        worst = ptp = 0.0
        for a, b in accel.PARITY_AB:
            if core == "convol_image":
                m = int(name.split("@")[1].split("x")[0])
                yy, xx = np.mgrid[-(m // 2):m // 2 + 1, -(m // 2):m // 2 + 1]
                ker = np.exp(-(xx * xx + yy * yy) / (2.0 * (m / 4.0) ** 2)) * (1 + 0.3 * xx / m)
                io, refs = [accel._to_batch(x, device), accel._to_batch([ker], device)], [[i, ker] for i in x]
            else:
                io, refs = [accel._to_batch(x, device), accel._to_batch(y, device)], [list(p) for p in zip(x, y)]
            got = accel._from_batch(fn(io, a, b, device))
            for r, g in zip(refs, got):
                ref = np.clip(table[core].fn(r, a, b), 0, 1)
                worst = max(worst, float(np.abs(ref - g).max()))
                ptp = max(ptp, float(np.ptp(ref)))
        rows[name] = {"inner": worst, "full": worst, "ref_ptp": ptp}
    return rows


def parity_typed(device, names):
    """型付き op の相対差 max|cpu-gpu| / max|cpu|(有限画素のみ)。plane_sweep は刃の上の同点を
    許すため「選ばれた深度の cost の差」で測り、深度が割れた画素率を別に残す。"""
    import accel_typed as T
    import match3d  # noqa: F401
    import pivops  # noqa: F401
    import plane_sweep as ps
    import tomography as tm
    rng = np.random.default_rng(3)
    im = np.clip(ndimage.gaussian_filter(rng.random((96, 96)), 3) * 5 - 2, 0, 1)
    ang = np.linspace(0, 180, 60, endpoint=False)
    sino = tm.radon_transform(im, ang)
    vol = np.stack([im, np.roll(im, 4, 0), im * 0.5])
    stack = tm.radon_volume(vol, ang)
    A = ndimage.gaussian_filter(rng.random((256, 256)), 1.2)
    B = ndimage.shift(A, (2.3, -1.4), order=3, mode="wrap")
    fr = [ndimage.shift(A, (0.8 * i, -0.4 * i), order=3, mode="wrap") + rng.random(A.shape) * 1e-3 for i in range(5)]
    K = np.array([[200., 0, 64], [0, 200, 64], [0, 0, 1]])
    Rm, t = np.eye(3), np.array([.1, 0, 0])
    L = ndimage.gaussian_filter(rng.random((128, 128)), 1.0)
    Ls = ps.warp_by_plane(L, ps.plane_homography(K, Rm, t, 2.0), order=1, cval=0.0)
    D = np.linspace(1, 4, 16)
    P = rng.random((20000, 3)) * 2 - 1
    lights = np.array([[0, 0, 1.], [.5, 0, 1], [0, .5, 1], [-.5, 0, 1], [0, -.5, 1]])
    stI = np.stack([np.clip(im * (0.5 + 0.1 * i) + 0.1, 0, 1) for i in range(5)])
    vid = np.stack([np.clip(im + rng.random(im.shape) * 0.05, 0, 1) for _ in range(9)])
    v0 = ndimage.gaussian_filter(rng.random((32, 32, 32)), 1.5) * 4
    v1 = np.roll(v0, 1, 0)
    bnd = ((-1, 1), (-1, 1), (-1, 1))
    cases = {
        "radon_transform": lambda f: f(im, ang), "radon_volume": lambda f: f(vol, ang),
        "backproject_sinogram": lambda f: f(sino, ang), "filtered_backprojection": lambda f: f(sino, ang),
        "fbp_volume": lambda f: f(stack, ang),
        # size=96 を明示する(既定 size は 95 になり core の答え自体が 2e6 へ発散する。報告の残課題)
        "sart_reconstruct": lambda f: f(sino, ang, size=96, n_iter=3),
        "piv_cross_correlate": lambda f: f(A, B, window=32)[0], "piv_multipass": lambda f: f(A, B)[0],
        "piv_ensemble_correlate": lambda f: f(fr, window=32)[0],
        "joint_bilateral": lambda f: f(im, np.roll(im, 1, 0), 2.0, 0.1), "temporal_bilateral": lambda f: f(vid),
        "voxel_grid_downsample": lambda f: f(P, 0.2), "occupancy_grid": lambda f: f(P, bnd, 32),
        "photometric_stereo": lambda f: f(stI, lights)[0], "points_to_voxel": lambda f: f(P, 32),
        "scene_flow_lk": lambda f: f(v0, v1),
    }
    rows = {}
    for name in names:
        module, fname, _k, _d = T.CANDIDATES[name]
        core = getattr(__import__(module), fname)
        gpu = lambda *a, **k: T.call_candidate(name, *a, device=device, **k)   # noqa: E731
        if name == "plane_sweep_depth":
            vol_c = ps.cost_volume(L, Ls, K, Rm, t, D, window=5)
            a = core(L, Ls, K, Rm, t, D, window=5)
            b = gpu(L, Ls, K, Rm, t, D, window=5)
            ok = np.isfinite(a) & np.isfinite(b)
            ia, ib = np.searchsorted(D, a[ok]), np.searchsorted(D, b[ok])
            yy, xx = np.nonzero(ok)
            dc = np.abs(vol_c[ia, yy, xx] - vol_c[ib, yy, xx]).max()
            rows[name] = {"inner": float(dc), "full": float(dc), "ref_ptp": float(np.ptp(a[ok])),
                          "depth_split_rate": float((a[ok] != b[ok]).mean()),
                          "nan_agree": float((np.isfinite(a) == np.isfinite(b)).mean())}
            continue
        a, b = np.asarray(cases[name](core), float), np.asarray(cases[name](gpu), float)
        ok = np.isfinite(a) & np.isfinite(b)
        rel = float(np.abs(a[ok] - b[ok]).max() / max(np.abs(a[ok]).max(), 1e-30))
        rows[name] = {"inner": rel, "full": rel, "ref_ptp": float(np.ptp(a[ok])),
                      "nan_agree": float((np.isfinite(a) == np.isfinite(b)).mean())}
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=("cpu", "gpu"))
    ap.add_argument("stage", choices=("2d", "nary", "typed", "parity"))
    ap.add_argument("--only", default="")
    a = ap.parse_args(argv)
    only = [x for x in a.only.split(",") if x]
    if a.mode == "cpu":
        os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
    out = LOG / ("fill3_%s_%s.json" % (a.mode, a.stage))
    prev = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"rows": {}}
    deadline = time.time() + LIMIT_S

    def go():
        if a.stage == "parity":
            import accel_typed as T
            dev = "cuda" if a.mode == "gpu" else "cpu"
            r = parity_2d(dev, list(TWO_D))
            r.update(parity_typed(dev, list(T.CANDIDATES)))
            return r
        if a.stage == "2d":
            names = only or (list(TWO_D) + (list(CPU_ONLY) if a.mode == "cpu" else []))
            return cpu_2d(names) if a.mode == "cpu" else gpu_2d(names, deadline)
        if a.stage == "nary":
            names = only or list(NARY)
            return cpu_nary(names) if a.mode == "cpu" else gpu_nary(names, deadline)
        import accel_typed as T
        return run_typed(a.mode, only or list(T.CANDIDATES), deadline)

    t0 = time.strftime("%Y-%m-%dT%H:%M:%S")
    if a.mode == "gpu":
        with GpuLock():
            import torch
            if not torch.cuda.is_available():
                print("[fill3] CUDA unavailable")
                return 2
            prev["gpu"] = torch.cuda.get_device_name(0)
            prev["torch"] = torch.__version__
            rows = go()
    else:
        prev["unreal_running_at_start"] = _unreal_alive()
        rows = go()
    for k, v in rows.items():
        prev["rows"].setdefault(k, {}).update(v)
    prev.setdefault("runs", []).append({"start": t0, "end": time.strftime("%Y-%m-%dT%H:%M:%S"), "names": sorted(rows)})
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(prev, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("[fill3] wrote %s (%d rows)" % (out.name, len(rows)), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
