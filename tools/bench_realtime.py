"""Cycle-time / jitter benchmark for the Fullseye runtime question.

The design question this answers is *not* "is Python fast?" — it is:

    For a manufacturing inspection cycle, how much of the wall clock is spent in
    (a) the pixel work (which a native core would also have to pay),
    (b) the L1 library's data-model choices, and
    (c) the L2 language/VM layer?

Only (c) is "the Python interpreter tax on the language".  (b) is a *design*
cost that a native rewrite would inherit unchanged if the data model is wrong,
which is why the ObjectSet variant is measured side by side: it isolates
"slow because Python" from "slow because the object model materialises one
full-frame mask per blob".

Manufacturing cares about the tail, not the mean: p99.9 and max decide whether a
trigger is missed.  Every mode is therefore reported as a distribution.

Run:
    py -3.11 tools/bench_realtime.py                     # default sweep
    py -3.11 tools/bench_realtime.py --quick             # short smoke run
    py -3.11 tools/bench_realtime.py --json out.json     # machine-readable
"""
from __future__ import annotations

import argparse
import gc
import json
import statistics
import sys
import time
from dataclasses import dataclass, asdict

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))

import fscript  # noqa: E402  (path set above)
import fslib  # noqa: E402
from fslib import FImage  # noqa: E402


# --------------------------------------------------------------------------- #
# Deterministic synthetic inspection scene
# --------------------------------------------------------------------------- #
def make_scene(h: int, w: int, n_blobs: int, seed: int = 7) -> np.ndarray:
    """A grey field with `n_blobs` bright discs plus illumination gradient and
    noise — the shape of a real "count and measure the parts" inspection."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    img = 0.25 + 0.10 * (xx / max(1, w - 1))          # illumination gradient
    radius = max(3.0, 0.006 * min(h, w))
    # place blobs on a jittered grid so they stay separated at every size
    cols = int(np.ceil(np.sqrt(n_blobs)))
    rows = int(np.ceil(n_blobs / cols))
    k = 0
    for r in range(rows):
        for c in range(cols):
            if k >= n_blobs:
                break
            cy = (r + 0.5) * h / rows + rng.uniform(-2, 2)
            cx = (c + 0.5) * w / cols + rng.uniform(-2, 2)
            rr = radius * rng.uniform(0.8, 1.4)
            m = (yy - cy) ** 2 + (xx - cx) ** 2 <= rr * rr
            img[m] = 0.85
            k += 1
    img += rng.normal(0.0, 0.01, size=img.shape).astype(np.float32)
    return np.clip(img, 0.0, 1.0).astype(np.float64)


# --------------------------------------------------------------------------- #
# The same inspection, expressed four ways
# --------------------------------------------------------------------------- #
MIN_AREA = 20.0


def cycle_raw_numpy(img):
    """Floor: hand-written scipy/numpy, label-image based.  This is the work a
    native core would also have to do — the irreducible pixel cost."""
    sm = ndi.gaussian_filter(img, 1.5)
    reg = (sm >= 0.5) & (sm <= 1.0)
    lbl, k = ndi.label(reg)
    if k == 0:
        return 0, []
    idx = np.arange(1, k + 1)
    areas = ndi.sum_labels(reg, lbl, index=idx)
    keep = idx[areas >= MIN_AREA]
    cents = ndi.center_of_mass(reg, lbl, keep) if keep.size else []
    return int(keep.size), list(cents)


def cycle_l1_builtins(img):
    """L1 via fscript's BUILTINS, which now delegate to the typed fslib model
    (FImage / Region / ObjectSet).  Measures the library layer without the
    language/VM overhead.  Since I-2 the object model *is* ObjectSet, so this and
    cycle_objectset now measure the same data model — the pre-I2 mask-per-blob
    cost is recorded in docs/FSCRIPT_MEASUREMENTS.md."""
    env = fscript.Env()
    B = fscript.BUILTINS
    sm = B["gauss_image"](env, FImage(img, value_range=(0.0, 1.0)), 1.5)
    reg = B["threshold"](env, sm, 0.5, 1.0)
    objs = B["connection"](env, reg)
    kept = B["select_shape"](env, objs, "area", MIN_AREA, 1e12)
    _areas, rows, cols = fslib.region_features(kept)
    return len(kept), list(zip(rows.tolist(), cols.tolist()))


def cycle_objectset(img):
    """The ObjectSet L1 in isolation (label image + id list, masks materialised
    lazily), driven straight through fslib.  Pure Python/numpy."""
    fim = FImage(img, value_range=(0.0, 1.0))
    sm = fslib.gauss(fim, 1.5)
    reg = fslib.threshold(sm, 0.5, 1.0)
    objs = fslib.connection(reg)
    kept = fslib.select_shape(objs, "area", MIN_AREA, 1e12)
    _areas, rows, cols = fslib.region_features(kept)
    return len(kept), list(zip(rows.tolist(), cols.tolist()))


FSCRIPT_SRC = """
Smooth := gauss_image(Image, 1.5)
Region := threshold(Smooth, 0.5, 1.0)
Objects := connection(Region)
N := count_obj(Objects)
Kept := 0
Rows := []
for I := 0 to N - 1
  Obj := select_obj(Objects, I)
  A := area(Obj)
  if (A >= 20)
    AC := area_center(Obj)
    Rows := [Rows, AC[1]]
    Kept := Kept + 1
  endif
endfor
"""

_FSCRIPT_PROGRAM = fscript.parse(FSCRIPT_SRC)


def cycle_fscript_vm(img):
    """Full L2: the AST interpreter runs the same algorithm.  The delta against
    cycle_l1_builtins is the language layer's tax."""
    env = fscript.run(_FSCRIPT_PROGRAM, images={"Image": img})
    return int(env.vars["Kept"]), env.vars["Rows"]


def cycle_native_cv2(img_u8):
    """What an industrial Fullseye runtime would actually be: the same algorithm,
    still driven from Python, but every kernel is a tuned native one (OpenCV) and
    the object model is the label image.  This is the shape every commercial
    vendor's Python API already has — Python orchestrating a native core."""
    import cv2
    sm = cv2.GaussianBlur(img_u8, (0, 0), 1.5)
    _, reg = cv2.threshold(sm, 127, 255, cv2.THRESH_BINARY)
    n, _lbl, stats, cents = cv2.connectedComponentsWithStats(reg, 8, cv2.CV_32S)
    keep = stats[1:, cv2.CC_STAT_AREA] >= MIN_AREA      # areas and centroids
    return int(keep.sum()), cents[1:][keep]             # come out of one pass


MODES = {
    "raw_numpy": cycle_raw_numpy,
    "l1_builtins": cycle_l1_builtins,
    "objectset": cycle_objectset,
    "fscript_vm": cycle_fscript_vm,
    "native_cv2": cycle_native_cv2,
}

#: modes that want an 8-bit frame (what a camera actually delivers) rather than
#: the float64 convention the current core normalises everything into.
U8_MODES = {"native_cv2"}


# --------------------------------------------------------------------------- #
# Measurement
# --------------------------------------------------------------------------- #
@dataclass
class Result:
    mode: str
    height: int
    width: int
    blobs: int
    cycles: int
    gc_enabled: bool
    mean_ms: float
    p50_ms: float
    p90_ms: float
    p99_ms: float
    p999_ms: float
    max_ms: float
    jitter_ratio: float          # max / p50 — the number a line engineer asks for
    gc_collections: int
    result_check: str


def _pct(xs, q):
    if not xs:
        return float("nan")
    s = sorted(xs)
    i = min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))
    return s[i]


def measure(mode: str, img, cycles: int, gc_enabled: bool, warmup: int = 5) -> Result:
    fn = MODES[mode]
    shape = img.shape
    if mode in U8_MODES:
        img = (np.clip(img, 0.0, 1.0) * 255).astype(np.uint8)
    for _ in range(warmup):
        fn(img)

    if not gc_enabled:
        gc.collect()
        gc.freeze()
        gc.disable()
    before = sum(s["collections"] for s in gc.get_stats())

    times = []
    check = None
    try:
        for _ in range(cycles):
            t0 = time.perf_counter()
            out = fn(img)
            times.append((time.perf_counter() - t0) * 1000.0)
            if check is None:
                check = "n=%d" % out[0]
    finally:
        if not gc_enabled:
            gc.enable()
            gc.unfreeze()
    after = sum(s["collections"] for s in gc.get_stats())

    return Result(
        mode=mode, height=shape[0], width=shape[1], blobs=-1,
        cycles=cycles, gc_enabled=gc_enabled,
        mean_ms=statistics.fmean(times),
        p50_ms=_pct(times, 0.50), p90_ms=_pct(times, 0.90),
        p99_ms=_pct(times, 0.99), p999_ms=_pct(times, 0.999),
        max_ms=max(times),
        jitter_ratio=max(times) / max(1e-9, _pct(times, 0.50)),
        gc_collections=after - before,
        result_check=check or "",
    )


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true", help="short run (smoke)")
    ap.add_argument("--cycles", type=int, default=0, help="cycles per config")
    ap.add_argument("--json", default=None, help="write results as JSON")
    ap.add_argument("--modes", default=",".join(MODES))
    ap.add_argument("--configs", default=None,
                    help="semicolon-separated HxWxBLOBS, e.g. '1024x1024x50;2048x2048x200'")
    args = ap.parse_args(argv)

    if args.configs:
        configs = []
        for spec in args.configs.split(";"):
            h, w, nb = (int(x) for x in spec.lower().split("x"))
            configs.append((h, w, nb))
        cycles = args.cycles or 120
    elif args.quick:
        configs = [(512, 512, 25)]
        cycles = args.cycles or 30
    else:
        configs = [
            (512, 512, 25),        # small part, few features
            (1024, 1024, 50),      # typical 1 MP inspection
            (2048, 2048, 50),      # 4 MP, same feature count
            (2048, 2048, 200),     # 4 MP, many features  <- the blow-up case
        ]
        cycles = args.cycles or 120

    modes = [m.strip() for m in args.modes.split(",") if m.strip()]
    rows: list[Result] = []
    for (h, w, nb) in configs:
        img = make_scene(h, w, nb)
        for mode in modes:
            for gc_on in (True, False):
                r = measure(mode, img, cycles, gc_on)
                r.blobs = nb
                rows.append(r)
                print("%-12s %5dx%-5d blobs=%-4d gc=%-5s "
                      "p50=%8.2f p99=%8.2f p99.9=%8.2f max=%8.2f jitter=%5.2fx gc_col=%d %s"
                      % (r.mode, r.height, r.width, r.blobs, r.gc_enabled,
                         r.p50_ms, r.p99_ms, r.p999_ms, r.max_ms,
                         r.jitter_ratio, r.gc_collections, r.result_check),
                      flush=True)
        print("", flush=True)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in rows], f, indent=1)
        print("wrote %s" % args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
