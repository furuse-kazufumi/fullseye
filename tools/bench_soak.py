"""Soak test — does the cycle time or the memory drift over a long run?

``docs/FSCRIPT_MEASUREMENTS.md`` could only claim "no GC jitter over 10 minutes",
which is not evidence for 24/7 operation.  This closes part of that gap: run the
industrial inspection continuously and report, per bucket, the cycle-time
distribution and the process RSS, so drift shows up as a trend rather than as a
single number.

It does not replace a real 24-hour run on target hardware — it detects the fast
failure modes (leak per cycle, allocator fragmentation, monotonic slowdown) that
would make a longer test pointless.

Run:  py -3.11 tools/bench_soak.py --minutes 30
"""
from __future__ import annotations

import argparse
import contextlib
import gc
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import fslib                                  # noqa: E402
from fslib import FImage                      # noqa: E402
from bench_realtime import make_scene          # noqa: E402


def rss_mb() -> float:
    """Resident set size without requiring psutil."""
    try:
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD),
                        ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t),
                        ("PeakPagefileUsage", ctypes.c_size_t)]

        pmc = PMC()
        pmc.cb = ctypes.sizeof(PMC)
        # Modern Windows exports the API from kernel32 as K32GetProcessMemoryInfo;
        # psapi.dll still forwards it. Try both and require a non-zero return.
        for dll, fn in ((ctypes.windll.kernel32, "K32GetProcessMemoryInfo"),
                        (ctypes.windll.psapi, "GetProcessMemoryInfo")):
            f = getattr(dll, fn, None)
            if f is None:
                continue
            f.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
            f.restype = wintypes.BOOL
            if f(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
                return pmc.WorkingSetSize / 1024 / 1024
        raise OSError("GetProcessMemoryInfo failed")
    except Exception:
        try:
            import resource
            return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        except Exception:
            return float("nan")


@contextlib.contextmanager
def timer_resolution(ms: int = 1):
    """Raise the Windows scheduler timer resolution for the block.

    docs/FSCRIPT_DECISION.md R4 identifies ``timeBeginPeriod(1)`` as the single
    biggest lever on the cycle-time TAIL — in the reference measurement it moved
    max from 8.9 ms to 0.34 ms (26x), more than GC.  A Runtime must hold it for
    its whole life; this lets the soak measure the tail with and without it.
    Yields whether the resolution was actually raised (no-op / False off Windows).
    """
    winmm = None
    try:
        import ctypes
        cand = ctypes.WinDLL("winmm")
        if cand.timeBeginPeriod(int(ms)) == 0:      # TIMERR_NOERROR
            winmm = cand
    except Exception:
        winmm = None
    try:
        yield winmm is not None
    finally:
        if winmm is not None:
            winmm.timeEndPeriod(int(ms))


def inspect(img: FImage):
    sm = fslib.gauss(img, 1.5)
    reg = fslib.threshold(sm, 0.5, 1.0)
    objs = fslib.connection(reg)
    kept = fslib.select_shape(objs, "area", 20, 1e12)
    areas, rows, cols = fslib.region_features(kept)
    return len(kept), float(rows.mean()) if len(kept) else 0.0


def inspect_timed(img: FImage):
    """Same inspection, but return per-phase timings (ms) so a tail cycle can be
    attributed to a specific operator (cv2 gauss/connection vs numpy select)."""
    c = time.perf_counter
    t0 = c(); sm = fslib.gauss(img, 1.5)
    t1 = c(); reg = fslib.threshold(sm, 0.5, 1.0)
    t2 = c(); objs = fslib.connection(reg)
    t3 = c(); kept = fslib.select_shape(objs, "area", 20, 1e12)
    t4 = c(); areas, rows, cols = fslib.region_features(kept)
    t5 = c()
    phases = {"gauss": (t1 - t0) * 1e3, "threshold": (t2 - t1) * 1e3,
              "connection": (t3 - t2) * 1e3, "select": (t4 - t3) * 1e3,
              "features": (t5 - t4) * 1e3}
    return (len(kept), float(rows.mean()) if len(kept) else 0.0), phases


def page_faults() -> int:
    """Cumulative hard+soft page-fault count for this process (Windows), or -1."""
    try:
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t),
                        ("PeakPagefileUsage", ctypes.c_size_t)]

        pmc = PMC(); pmc.cb = ctypes.sizeof(PMC)
        for dll, fn in ((ctypes.windll.kernel32, "K32GetProcessMemoryInfo"),
                        (ctypes.windll.psapi, "GetProcessMemoryInfo")):
            f = getattr(dll, fn, None)
            if f is None:
                continue
            f.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
            f.restype = wintypes.BOOL
            if f(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
                return int(pmc.PageFaultCount)
    except Exception:
        pass
    return -1


def pct(xs, q):
    s = sorted(xs)
    return s[min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--minutes", type=float, default=30.0)
    ap.add_argument("--size", default="2048x2048x200")
    ap.add_argument("--profile", default="industrial")
    ap.add_argument("--bucket", type=int, default=2000, help="cycles per report row")
    ap.add_argument("--timer-resolution", action=argparse.BooleanOptionalAction,
                    default=True,
                    help="hold Windows timeBeginPeriod(1) for the run (R4; tail lever)")
    ap.add_argument("--cv2-threads", type=int, default=-1,
                    help="cv2.setNumThreads(N); -1 leaves the default (tests the "
                         "thread-pool tail hypothesis)")
    ap.add_argument("--diagnose", action="store_true",
                    help="attribute each cycle to a phase and report the slowest "
                         "cycles' breakdown + per-bucket page faults")
    ap.add_argument("--json", default=None)
    args = ap.parse_args(argv)

    if args.cv2_threads >= 0:
        try:
            import cv2
            cv2.setNumThreads(args.cv2_threads)
            print("cv2.setNumThreads(%d)" % args.cv2_threads, flush=True)
        except Exception as e:
            print("cv2.setNumThreads failed: %s" % e, flush=True)

    h, w, nb = (int(x) for x in args.size.lower().split("x"))
    base = make_scene(h, w, nb)
    img = FImage.from_u8((np.clip(base, 0, 1) * 255).astype(np.uint8))

    # In --diagnose the slowest K cycles keep their phase breakdown for attribution.
    slowest: list[tuple[float, int, dict]] = []          # (cycle_ms, cycle_idx, phases)
    KEEP_SLOW = 30

    tr_cm = timer_resolution(1) if args.timer_resolution else contextlib.nullcontext(False)
    with tr_cm as tr_on, fslib.profile(args.profile):
        print("timer_resolution(1): %s  diagnose=%s" % (
              "ON" if tr_on else ("requested but unavailable" if args.timer_resolution else "off"),
              args.diagnose), flush=True)
        for _ in range(20):
            inspect(img)                               # warm caches / allocator
        gc.collect()
        rss0 = rss_mb()
        gc0 = sum(s["collections"] for s in gc.get_stats())
        pf0 = page_faults()
        t_end = time.perf_counter() + args.minutes * 60.0
        print("soak: %s %s  target %.0f min  rss0=%.1f MB  pf0=%d" %
              (args.size, args.profile, args.minutes, rss0, pf0), flush=True)
        print("%8s %10s %8s %8s %8s %8s %9s %8s %8s" %
              ("cycles", "elapsed_s", "p50", "p99", "p99.9", "max", "rss_MB", "d_rss", "d_pf"),
              flush=True)

        rows, times, total, first_p50 = [], [], 0, None
        pf_prev = pf0
        while time.perf_counter() < t_end:
            for _ in range(args.bucket):
                t0 = time.perf_counter()
                if args.diagnose:
                    _out, phases = inspect_timed(img)
                    dt = (time.perf_counter() - t0) * 1000.0
                    if len(slowest) < KEEP_SLOW or dt > slowest[-1][0]:
                        slowest.append((dt, total + len(times), phases))
                        slowest.sort(key=lambda x: x[0], reverse=True)
                        del slowest[KEEP_SLOW:]
                else:
                    inspect(img)
                    dt = (time.perf_counter() - t0) * 1000.0
                times.append(dt)
            total += args.bucket
            r = rss_mb()
            pf_now = page_faults()
            d_pf = (pf_now - pf_prev) if (pf_now >= 0 and pf_prev >= 0) else -1
            pf_prev = pf_now
            row = {"cycles": total, "elapsed_s": round(args.minutes * 60 - (t_end - time.perf_counter()), 1),
                   "p50": round(pct(times, .5), 3), "p99": round(pct(times, .99), 3),
                   "p999": round(pct(times, .999), 3), "max": round(max(times), 3),
                   "rss_mb": round(r, 1), "d_rss_mb": round(r - rss0, 1), "d_pf": d_pf}
            rows.append(row)
            if first_p50 is None:
                first_p50 = row["p50"]
            print("%8d %10.1f %8.2f %8.2f %8.2f %8.2f %9.1f %+8.1f %8d" %
                  (row["cycles"], row["elapsed_s"], row["p50"], row["p99"],
                   row["p999"], row["max"], row["rss_mb"], row["d_rss_mb"], row["d_pf"]), flush=True)
            times = []

        gc_total = sum(s["collections"] for s in gc.get_stats()) - gc0

    last = rows[-1]
    print("", flush=True)
    print("cycles=%d  p50 drift %.2f -> %.2f ms (%+.1f%%)  rss drift %+.1f MB  gc_collections=%d"
          % (last["cycles"], first_p50, last["p50"],
             100.0 * (last["p50"] - first_p50) / max(1e-9, first_p50),
             last["d_rss_mb"], gc_total), flush=True)

    if args.diagnose and slowest:
        print("\n--- slowest %d cycles: phase breakdown (ms) ---" % len(slowest), flush=True)
        print("%10s %8s %9s %10s %8s %9s %8s" %
              ("cycle_ms", "gauss", "threshold", "connection", "select", "features", "at_cycle"),
              flush=True)
        for dt, idx, ph in slowest:
            print("%10.2f %8.2f %9.2f %10.2f %8.2f %9.2f %8d" %
                  (dt, ph["gauss"], ph["threshold"], ph["connection"],
                   ph["select"], ph["features"], idx), flush=True)
        # which phase dominates the excess on tail cycles?
        agg = {k: sum(ph[k] for _, _, ph in slowest) for k in
               ("gauss", "threshold", "connection", "select", "features")}
        worst = max(agg, key=agg.get)
        print("tail time is dominated by phase: %s (%.1f%% of summed slow-cycle time)"
              % (worst, 100.0 * agg[worst] / max(1e-9, sum(agg.values()))), flush=True)

    if args.json:
        out = {"rows": rows,
               "slowest": [{"cycle_ms": dt, "at_cycle": idx, "phases": ph}
                           for dt, idx, ph in slowest],
               "config": {"size": args.size, "profile": args.profile,
                          "timer_resolution": bool(tr_on), "cv2_threads": args.cv2_threads,
                          "diagnose": args.diagnose}}
        Path(args.json).write_text(json.dumps(out, indent=1), encoding="utf-8")
        print("wrote %s" % args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
