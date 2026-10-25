# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""探針(probe)の共通本体: 代表 10 op を同じ入力で計時する。CPython でも Pyodide でも**同じファイル**を読む。

入力は決定的(seed 0): 512×512 の float 画像(縞 + 円 + 雑音)と、1 万点の点群(平面 70% + 外れ値 30%)。
各 op は 1 回ウォームアップしてから ``reps`` 回の中央値を取る。戻り値は JSON にできる dict。
"""
from __future__ import annotations

import json
import statistics
import sys
import time
import traceback


def make_inputs():
    import numpy as np
    rng = np.random.default_rng(0)
    yy, xx = np.mgrid[0:512, 0:512].astype(np.float32) / 512.0
    img = 0.5 + 0.25 * np.sin(2 * np.pi * 6 * xx) * np.cos(2 * np.pi * 4 * yy)
    img += 0.3 * (((xx - 0.5) ** 2 + (yy - 0.5) ** 2) < 0.08)
    img += 0.05 * rng.standard_normal(img.shape, dtype=np.float32)
    img = np.clip(img, 0, 1).astype(np.float32)
    n = 10_000
    k = int(n * 0.7)
    xy = rng.uniform(-1, 1, size=(k, 2))
    z = 0.3 * xy[:, 0] - 0.2 * xy[:, 1] + 0.1 + rng.normal(0, 0.005, size=k)
    plane = np.column_stack([xy, z])
    outl = rng.uniform(-1, 1, size=(n - k, 3))
    pts = np.vstack([plane, outl]).astype(np.float64)
    return img, pts


def _median_ms(fn, reps):
    fn()  # warm-up(初回の遅延 import / JIT を外す)
    ts = []
    for _ in range(reps):
        t = time.perf_counter()
        fn()
        ts.append((time.perf_counter() - t) * 1e3)
    return round(statistics.median(ts), 2)


def run_bench(reps: int = 5) -> dict:
    import numpy as np
    out = {"python": sys.version.split()[0], "platform": sys.platform, "numpy": np.__version__, "ops": {}}
    try:
        import scipy
        out["scipy"] = scipy.__version__
    except Exception:
        out["scipy"] = None
    t0 = time.perf_counter()
    import api
    out["import_api_s"] = round(time.perf_counter() - t0, 2)
    out["registry_n"] = len(api.REGISTRY)
    try:
        out["failed_backends"] = sorted(api.FAILED_BACKENDS) if isinstance(api.FAILED_BACKENDS, (set, list, tuple)) else str(api.FAILED_BACKENDS)[:500]
    except Exception as e:  # noqa: BLE001
        out["failed_backends"] = "err %s" % e
    img, pts = make_inputs()

    def ap(name, a=0.5, b=0.5):
        return lambda: api.apply(img, name, a, b)

    cases = {
        "otsu": ap("otsu"),
        "gaussian": ap("gaussian"),
        "median": ap("median"),
        "sobel_amp": ap("sobel_amp"),
        "canny": ap("canny"),
        "opening_circle": ap("opening_circle"),
        "dist_transform": ap("dist_transform"),
    }
    try:
        import ransac_fit
        import curvature3d
        cases["ransac_plane_10k"] = lambda: ransac_fit.ransac_plane(pts, 0.02, iters=200, seed=0)
        cases["estimate_normals_10k"] = lambda: curvature3d.estimate_normals(pts, k=25)
    except Exception as e:  # noqa: BLE001
        out["ops"]["3d_import_error"] = repr(e)
    try:
        import optics
        psf = optics.airy_pattern(size=256)
        cases["airy_pattern_256"] = lambda: optics.airy_pattern(size=256)
        cases["psf_to_mtf_256"] = lambda: optics.psf_to_mtf(psf, pixel_pitch_um=0.5)
    except Exception as e:  # noqa: BLE001
        out["ops"]["optics_import_error"] = repr(e)
    for name, fn in cases.items():
        try:
            out["ops"][name] = {"ms": _median_ms(fn, reps)}
        except Exception as e:  # noqa: BLE001
            out["ops"][name] = {"error": "%s: %s" % (type(e).__name__, str(e)[:300]),
                                "tb": traceback.format_exc()[-600:]}
    return out


if __name__ == "__main__":
    print(json.dumps(run_bench(int(sys.argv[1]) if len(sys.argv) > 1 else 5), ensure_ascii=False, indent=1))
