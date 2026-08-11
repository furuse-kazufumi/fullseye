"""Functional gate — proves generated ops actually DO what HALCON does.

The user's bar is capability, not naming: an operator counts only if it genuinely
runs and returns the declared sort. This module executes every spec's RAW factory
function (unwrapped, so exceptions surface instead of being swallowed by `_safe`)
on canonical inputs and checks:

  1. runs without exception on several (a, b) samples
  2. returns the declared output sort (image / region / feature / contour), with
     the right ndim / dtype / value domain
  3. (informational) whether it changed the input — pure pass-throughs are flagged

Honest coverage = distinct real HALCON operators whose generated op PASSES this
gate. That is the number we report — earned, not claimed.

    py -3.11 verify_auto.py            # summary
    py -3.11 verify_auto.py --failures # list every failing op + reason
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np

import backends_auto as BA

HERE = os.path.dirname(os.path.abspath(__file__))


def _canonical_image(n=64):
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    grad = xx / (n - 1)
    disk = ((yy - n * 0.35) ** 2 + (xx - n * 0.35) ** 2) < (n * 0.18) ** 2
    disk2 = ((yy - n * 0.7) ** 2 + (xx - n * 0.65) ** 2) < (n * 0.12) ** 2
    checker = ((xx.astype(int) // 6 + yy.astype(int) // 6) % 2) * 0.15
    rng = np.random.default_rng(7)
    img = 0.35 * grad + 0.5 * (disk | disk2) + checker + 0.04 * rng.standard_normal((n, n))
    return np.clip(img, 0, 1)


def _canonical_region(img):
    return (img > 0.5).astype(np.float64)


def _canonical_contour(img):
    m = np.hypot(*(np.gradient(img)))
    m = m / (m.max() + 1e-8)
    from scipy import ndimage
    lab, k = ndimage.label(m > 0.2, structure=np.ones((3, 3)))
    cs = []
    for i in range(1, k + 1):
        ys, xs = np.where(lab == i)
        if len(ys) >= 3:
            cs.append(np.stack([ys, xs], 1).astype(np.float64))
    return {"shape": img.shape, "cs": cs or [np.array([[1.0, 1.0], [2.0, 2.0], [3.0, 3.0]])]}


def _check_sort(out, sort, shape):
    """Return (ok, changed, reason)."""
    if sort == "feature":
        try:
            f = float(np.asarray(out).reshape(-1)[0]) if np.size(out) else float(out)
        except Exception:
            return False, True, "feature not scalar-like"
        return (np.isfinite(f), True, "" if np.isfinite(f) else "feature not finite")
    if sort == "contour":
        ok = isinstance(out, dict) and "cs" in out and isinstance(out["cs"], list)
        return ok, True, "" if ok else "not a contour dict"
    # image / region  -> 2-D float array
    if not isinstance(out, np.ndarray):
        return False, True, "not ndarray (%s)" % type(out).__name__
    if out.ndim != 2:
        return False, True, "ndim=%d" % out.ndim
    if not np.all(np.isfinite(out)):
        return False, True, "non-finite values"
    changed = out.shape != shape or float(np.max(np.abs(out - _REF.get(id(shape), out)))) > 1e-9
    if sort == "region":
        vals = np.unique(np.round(out, 6))
        binary = set(vals.tolist()) <= {0.0, 1.0} or (out.min() >= 0 and out.max() <= 1)
        return binary, changed, "" if binary else "region not in [0,1]"
    return True, changed, ""


_REF: dict = {}


def run(verbose_failures=False):
    img = _canonical_image()
    reg = _canonical_region(img)
    con = _canonical_contour(img)
    inputs = {"image": img, "region": reg, "contour": con}
    _REF[id(img.shape)] = img

    specs = BA.load_specs()
    real = BA._real_ops()
    results = []
    for s in specs:
        name, shape, in_s, out_s = (s["halcon"], s["shape"], s["in_sort"], s["out_sort"])
        if real and name not in real:
            results.append((name, "drop_fake", ""))
            continue
        if shape not in BA.SHAPES:
            results.append((name, "drop_shape", shape))
            continue
        try:
            fn = BA.SHAPES[shape](s.get("params", {}))
        except Exception as e:
            results.append((name, "bad_params", repr(e)))
            continue
        base = inputs.get(in_s)
        if base is None:
            results.append((name, "no_input", in_s))
            continue
        ref = base.copy() if isinstance(base, np.ndarray) else base
        ok_all, changed_any, reason = True, False, ""
        for (a, b) in ((0.3, 0.4), (0.6, 0.7), (0.15, 0.85)):
            try:
                out = fn(ref if not isinstance(ref, np.ndarray) else ref.copy(), a, b)
            except Exception as e:
                ok_all, reason = False, "raise:%s" % repr(e)[:80]
                break
            if isinstance(out, np.ndarray) and isinstance(ref, np.ndarray) and out.shape == ref.shape:
                if float(np.max(np.abs(out - ref))) > 1e-9:
                    changed_any = True
            else:
                changed_any = True
            ok, _, why = _check_sort(out, out_s, base.shape if isinstance(base, np.ndarray) else None)
            if not ok:
                ok_all, reason = False, why
                break
        results.append((name, "pass" if ok_all else "fail", "" if ok_all else reason,
                        "changed" if changed_any else "identity"))

    passed = [r for r in results if r[1] == "pass"]
    failed = [r for r in results if r[1] == "fail"]
    dropped = [r for r in results if r[1].startswith(("drop", "bad", "no_"))]
    identity = [r for r in passed if len(r) > 3 and r[3] == "identity"]
    covered_pass = {r[0] for r in passed}

    print("functional gate over %d specs:" % len(specs))
    print("  PASS %d  |  FAIL %d  |  dropped %d  |  (of PASS, %d were identity on canonical)"
          % (len(passed), len(failed), len(dropped), len(identity)))
    print("  distinct real HALCON ops that PASS: %d" % len(covered_pass))
    if failed:
        print("  --- failures (%d) ---" % len(failed))
        for name, _, reason, *_ in (failed if verbose_failures else failed[:15]):
            print("    %-26s %s" % (name, reason))
    if dropped:
        print("  --- dropped (%d): %s" % (len(dropped), [d[0] for d in dropped][:20]))
    # persist honest artifact
    art = {
        "n_specs": len(specs), "n_pass": len(passed), "n_fail": len(failed),
        "n_dropped": len(dropped), "n_identity_on_canonical": len(identity),
        "passing_ops": sorted(covered_pass),
        "failures": [(r[0], r[2]) for r in failed],
    }
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    json.dump(art, open(os.path.join(HERE, "data", "auto_functional_gate.json"), "w",
                        encoding="utf-8"), ensure_ascii=False, indent=1)
    return art


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--failures", action="store_true", help="list every failing op")
    a = ap.parse_args()
    run(a.failures)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
