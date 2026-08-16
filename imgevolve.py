"""imgevolve — single CLI entry point (designed to be usable by a future agent).

A future Claude Code session should be able to *use* this HALCON-parity library
without re-reading the source. Discover and invoke everything from here:

    py -3.11 imgevolve.py ops                    # list every implemented operator
    py -3.11 imgevolve.py ops --search edge      # search by name / halcon / category
    py -3.11 imgevolve.py ops --sort region      # filter by input sort
    py -3.11 imgevolve.py has gauss_filter       # is a HALCON op implemented? how to call it
    py -3.11 imgevolve.py apply gauss_filter in.png out.png --a 0.6
    py -3.11 imgevolve.py pipeline in.png out.png --ops "gauss_filter,sobel_amp,otsu"
    py -3.11 imgevolve.py coverage               # honest coverage numbers
    py -3.11 imgevolve.py index                  # (re)write docs/OP_INDEX.json (machine-readable)
    py -3.11 imgevolve.py algo list              # general-algorithm tier (sorts/reductions)
    py -3.11 imgevolve.py algo run quicksort --seq 3,1,2   # -> [1.0, 2.0, 3.0]
    py -3.11 imgevolve.py algo emit-c mergesort  # standalone, compilable C
    py -3.11 imgevolve.py algo difftest all      # honest gate (Python==oracle, C==Python bit-for-bit)
    py -3.11 imgevolve.py synth in.png out.png   # learn a texture -> synthesise a similar image
    py -3.11 imgevolve.py synth in.png out.png --method patch --size 320x320

Sorts: image (gray H*W [0,1]) / color (H*W*3 RGB) / region (binary) / feature
(scalar) / contour (XLD) / volume (3-D). `apply` loads the input to match the
op's in_sort and serialises the output by its out_sort (feature -> printed,
contour -> point count + optional raster).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _load_registry():
    import ops
    return ops


def _all_ops():
    """Every operator across the three tiers, as uniform dicts."""
    ops = _load_registry()
    rows = [{"name": o.name, "halcon": o.halcon, "in_sort": o.in_sort,
             "out_sort": o.out_sort, "category": o.category, "tier": "registry"}
            for o in ops.REGISTRY]
    try:
        import imgops_nary as NA
        rows += [{"name": o.name, "halcon": o.halcon, "in_sort": o.in_sorts[0],
                  "out_sort": o.out_sort, "category": "nary", "tier": "nary",
                  "arity": o.arity, "in_sorts": list(o.in_sorts)}
                 for o in NA.build_nary()]
    except Exception:
        pass
    return rows


# ---- image I/O ------------------------------------------------------------- #
def _imread(path, sort):
    import cv2
    if sort == "color":
        im = cv2.imread(path, cv2.IMREAD_COLOR)
        if im is None:
            raise SystemExit("cannot read %s" % path)
        return (im[:, :, ::-1].astype(np.float64)) / 255.0     # BGR->RGB
    im = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if im is None:
        raise SystemExit("cannot read %s" % path)
    g = im.astype(np.float64) / 255.0
    return (g > 0.5).astype(np.float64) if sort == "region" else g


def _imwrite(path, v):
    import cv2
    v = np.asarray(v)
    if v.ndim == 3 and v.shape[-1] == 3:
        out = np.clip(v * 255, 0, 255).astype(np.uint8)[:, :, ::-1]     # RGB->BGR
    else:
        out = np.clip(np.asarray(v, np.float64) * 255, 0, 255).astype(np.uint8)
    cv2.imwrite(path, out)


# ---- subcommands ----------------------------------------------------------- #
def cmd_ops(a):
    rows = _all_ops()
    kw = (a.search or "").lower()
    for r in sorted(rows, key=lambda r: (r["tier"], r["in_sort"], r["name"])):
        if a.sort and r["in_sort"] != a.sort:
            continue
        if kw and kw not in (r["name"] + " " + (r["halcon"] or "") + " " + r["category"]).lower():
            continue
        print("%-26s %-8s->%-8s  halcon=%-24s [%s/%s]"
              % (r["name"], r["in_sort"], r["out_sort"], r["halcon"] or "-", r["tier"], r["category"]))
    print("--- %d ops match ---" % sum(
        1 for r in rows if (not a.sort or r["in_sort"] == a.sort)
        and (not kw or kw in (r["name"] + " " + (r["halcon"] or "") + " " + r["category"]).lower())))
    return 0


def _disposition(op):
    p = os.path.join(HERE, "docs", "OP_DISPOSITION.json")
    if not os.path.exists(p):
        return None
    return json.load(open(p, encoding="utf-8"))["dispositions"].get(op)


def cmd_has(a):
    rows = _all_ops()
    q = a.op.lower()
    hits = [r for r in rows if q in (r["name"].lower(), (r["halcon"] or "").lower())]
    if not hits:
        # Every one of the 2313 real ops still gets a truthful response.
        d = _disposition(a.op)
        if d:
            print("NOT genuinely implemented: %s" % a.op)
            print("  disposition: %s" % d["status"])
            print("  reason: %s  [chapter=%s, arity=%d]" % (d["reason"], d["chapter"], d["arity"]))
            return 0
        near = [r for r in rows if q in r["name"].lower() or q in (r["halcon"] or "").lower()]
        print("unknown op: %s (not in the HALCON reference)" % a.op)
        if near:
            print("  near:", ", ".join(sorted({r["halcon"] or r["name"] for r in near}))[:400])
        return 1
    for r in hits:
        print("IMPLEMENTED: halcon=%s  name=%s  %s->%s  tier=%s"
              % (r["halcon"], r["name"], r["in_sort"], r["out_sort"], r["tier"]))
        if r["tier"] == "registry":
            print("  call: py -3.11 imgevolve.py apply %s <in> <out> --a A --b B" % (r["halcon"] or r["name"]))
        else:
            print("  n-ary (%d inputs) — use imgops_nary.build_nary() programmatically" % r.get("arity", 2))
    return 0


def _find_op(ops, key):
    # Exact op name wins; only then fall back to the HALCON alias. Several ops
    # share a halcon alias (e.g. remove_small carries halcon='select_shape'),
    # so first-match-wins on (name OR halcon) could bind `apply <name>` to an
    # unrelated op. Among halcon matches, prefer the canonical op (name==halcon).
    for o in ops.REGISTRY:
        if o.name == key:
            return o
    halcon_hits = [o for o in ops.REGISTRY if o.halcon == key]
    if not halcon_hits:
        return None
    for o in halcon_hits:
        if o.name == o.halcon:
            return o
    return halcon_hits[0]


def cmd_apply(a):
    ops = _load_registry()
    op = _find_op(ops, a.op)
    if op is None:
        raise SystemExit("unknown op %r (try: imgevolve.py has %s)" % (a.op, a.op))
    v = _imread(a.inp, op.in_sort)
    out = ops.RT[op.name](v, a.a, a.b)
    if op.out_sort == "feature":
        print("feature %s = %s" % (op.halcon or op.name, float(np.asarray(out).reshape(-1)[0])))
        return 0
    if op.out_sort == "contour":
        H, W = out["shape"]
        mask = np.zeros((H, W), np.float64)
        for c in out["cs"]:
            idx = np.clip(np.round(c).astype(int), [0, 0], [H - 1, W - 1])
            mask[idx[:, 0], idx[:, 1]] = 1.0
        _imwrite(a.out, mask)
        print("contour %s: %d contours -> %s (rasterised)" % (op.halcon or op.name, len(out["cs"]), a.out))
        return 0
    _imwrite(a.out, out)
    print("applied %s (%s->%s) -> %s" % (op.halcon or op.name, op.in_sort, op.out_sort, a.out))
    return 0


def cmd_pipeline(a):
    ops = _load_registry()
    names = [s.strip() for s in a.ops.split(",") if s.strip()]
    resolved = []
    for nm in names:
        op = _find_op(ops, nm)
        if op is None:
            raise SystemExit("unknown op in pipeline: %r" % nm)
        resolved.append(op)
    v = _imread(a.inp, resolved[0].in_sort)
    for op in resolved:
        v = ops.RT[op.name](v, a.a, a.b)
    if isinstance(v, np.ndarray):
        _imwrite(a.out, v)
        print("pipeline %s -> %s %s" % (" -> ".join(names), a.out, getattr(v, "shape", "")))
    else:
        print("pipeline %s -> %s" % (" -> ".join(names), type(v).__name__))
    return 0


def cmd_run(a):
    """Run a saved pipeline (Studio JSON or an ops string) via FullseyeEngine."""
    import engine
    import imgio
    if str(a.pipeline).lower().endswith(".json"):
        eng = engine.FullseyeEngine.load(a.pipeline)
    else:
        eng = engine.FullseyeEngine.from_ops(a.pipeline, a=a.a, b=a.b)

    if a.describe or a.to_python:
        if a.to_python:
            print(eng.to_python())
        else:
            print("pipeline %r: %s -> %s" % (eng.name, eng.input_sort(), eng.output_sort()))
            for d in eng.describe():
                mark = "" if d["known"] else "   [UNKNOWN OP]"
                print("  %2d. %-24s a=%.2f b=%.2f   [%s -> %s]%s"
                      % (d["index"], d["op"], d["a"], d["b"], d["in_sort"], d["out_sort"], mark))
            for p in eng.validate():
                print("  ! %-7s stage %d: %s" % (p["severity"], p["index"], p["message"]))
        if a.inp is None:
            return 0

    errors = [p for p in eng.validate() if p["severity"] == "error"]
    if errors:
        raise SystemExit("pipeline has errors: " + "; ".join(p["message"] for p in errors))
    if a.inp is None:
        raise SystemExit("need an input image (or use --describe / --to-python)")

    img = imgio.load(a.inp)
    if a.stepwise:
        for i, s in enumerate(eng.run_stepwise(img)):
            shp = getattr(s, "shape", type(s).__name__)
            if a.out and isinstance(s, np.ndarray) and s.ndim in (2, 3):
                base, ext = os.path.splitext(a.out)
                imgio.save("%s_%02d%s" % (base, i, ext or ".png"), s)
            print("  step %2d  %-24s -> %s" % (i, eng.stages[i][0], shp))
        return 0

    result = eng.run(img, upto=a.upto)
    if isinstance(result, np.ndarray) and result.ndim in (2, 3):
        if a.out:
            imgio.save(a.out, result)
            print("run %s -> %s %s" % (eng.name, a.out, result.shape))
        else:
            print("run %s -> result %s (pass --out to save)" % (eng.name, result.shape))
    else:
        print("run %s -> %s = %r" % (eng.name, type(result).__name__, result))
    return 0


def cmd_coverage(a):
    import honest_summary
    return honest_summary.main()


def cmd_parity(a):
    import parity
    return parity.main()


def cmd_accel(a):
    import sys as _s
    _s.argv = ["accel.py", "--device", a.device]
    import accel
    return accel.main()


def cmd_bench(a):
    import sys as _s
    _s.argv = ["bench.py", "--n", str(a.n), "--size", str(a.size), "--device", a.device]
    import bench
    return bench.main()


def cmd_index(a):
    rows = _all_ops()
    try:
        import backends_color as CL
        col = set(CL.coverage()["halcon_names"])
    except Exception:
        col = set()
    for r in rows:
        if r["halcon"] in col:
            r["tier"] = "color"
    out = {
        "n_ops": len(rows),
        "tiers": {t: sum(1 for r in rows if r["tier"] == t) for t in
                  sorted({r["tier"] for r in rows})},
        "sorts": sorted({r["in_sort"] for r in rows} | {r["out_sort"] for r in rows}),
        "ops": sorted(rows, key=lambda r: (r["tier"], r["name"])),
    }
    p = a.out or os.path.join(HERE, "docs", "OP_INDEX.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[index] %d ops (%s) -> %s" % (len(rows), out["tiers"], p))
    return 0


def cmd_algo(a):
    """General-algorithm tier (algo-c parity): list / run / emit C or Python / difftest.

    A separate, opt-in tier from the image ops (sequences, not rasters). See
    ``algo.py`` and ``docs/GENERAL_ALGORITHMS.md``.
    """
    import algo
    if a.action == "list":
        for op in algo.ALGO_REGISTRY:
            print("%-10s %-4s->%-6s [%-6s]  %s"
                  % (op.name, op.in_sort, op.out_sort, op.category, op.provenance))
        print("--- %d general-algorithm ops (seq/scalar tier) ---" % len(algo.ALGO_REGISTRY))
        return 0
    if a.action == "run":
        if a.op is None or algo.find_algo(a.op) is None:
            raise SystemExit("run needs a known op (try: imgevolve.py algo list)")
        seq = [float(x) for x in a.seq.split(",") if x.strip()]
        print(algo.run_algo(a.op, seq))
        return 0
    if a.action in ("emit-c", "emit-py"):
        import algo_codegen
        if a.op is None or algo.find_algo(a.op) is None:
            raise SystemExit("%s needs a known op (try: imgevolve.py algo list)" % a.action)
        op = algo.ALGO_BY_NAME[a.op]
        print(algo_codegen.emit_c(op) if a.action == "emit-c" else algo_codegen.emit_python(op))
        return 0
    if a.action == "difftest":
        import algo_difftest
        cc = None if a.no_c else "auto"
        names = algo.algo_names() if a.op in (None, "all") else [a.op]
        rc = 0
        for nm in names:
            if algo.find_algo(nm) is None:
                raise SystemExit("unknown algo op: %r (try: imgevolve.py algo list)" % nm)
            r = algo_difftest.difftest(nm, a.workdir, cc=cc)
            cb = r["c_backend"]
            extra = (" bit_identical=%s" % cb.get("c_vs_python_bit_identical")) if cb.get("status") == "ran" else ""
            print("[algo:%s] python pass=%s | C %s%s | c_verified=%s -> passed=%s"
                  % (nm, r["python_pass"], cb.get("status"), extra, r["c_verified"], r["passed"]))
            if not r["passed"]:
                rc = 1
        return rc
    return 0


def cmd_synth(a):
    """Learn a texture from an image and synthesise a NEW, similar one (synth.py)."""
    import imgio
    import synth
    img = imgio.load(a.inp)
    size = None
    if a.size:
        h, w = a.size.lower().split("x")
        size = (int(h), int(w))
    out = synth.synthesize_like(img, size=size, seed=a.seed, method=a.method)
    imgio.save(a.out, out)
    d = synth.feature_distance(img, out)
    nov = synth.patch_novelty(out, img)
    pyr = synth.pyramid_stat_distance(img, out)            # per-scale marginal match
    print("synth %s -> %s  spectrum_l2=%.4f hist_chi2=%.4f pyramid=%.4f novelty=%.5f"
          % (a.method, a.out, d["spectrum_l2"], d["hist_chi2"], pyr, nov))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("ops", help="list/search implemented operators")
    p.add_argument("--search", default="")
    p.add_argument("--sort", default="")
    p.set_defaults(fn=cmd_ops)

    p = sub.add_parser("has", help="is a HALCON op implemented + how to call it")
    p.add_argument("op")
    p.set_defaults(fn=cmd_has)

    p = sub.add_parser("apply", help="apply one operator to an image")
    p.add_argument("op"); p.add_argument("inp"); p.add_argument("out")
    p.add_argument("--a", type=float, default=0.5); p.add_argument("--b", type=float, default=0.5)
    p.set_defaults(fn=cmd_apply)

    p = sub.add_parser("pipeline", help="apply a comma-separated op sequence")
    p.add_argument("inp"); p.add_argument("out"); p.add_argument("--ops", required=True)
    p.add_argument("--a", type=float, default=0.5); p.add_argument("--b", type=float, default=0.5)
    p.set_defaults(fn=cmd_pipeline)

    p = sub.add_parser("run", help="run a saved pipeline (JSON or ops string) via FullseyeEngine")
    p.add_argument("pipeline", help="a pipeline .json (Studio 'Save pipeline') or a comma-separated ops string")
    p.add_argument("inp", nargs="?", default=None, help="input image (omit with --describe / --to-python)")
    p.add_argument("--out", default="", help="save the result here")
    p.add_argument("--upto", type=int, default=None, help="run only stages 0..N")
    p.add_argument("--stepwise", action="store_true", help="report/save each stage's result")
    p.add_argument("--describe", action="store_true", help="print pipeline I/O + validation, then exit if no input")
    p.add_argument("--to-python", action="store_true", dest="to_python", help="print the pipeline as a Python function")
    p.add_argument("--a", type=float, default=0.5); p.add_argument("--b", type=float, default=0.5)
    p.set_defaults(fn=cmd_run)

    p = sub.add_parser("coverage", help="print honest coverage numbers")
    p.set_defaults(fn=cmd_coverage)

    p = sub.add_parser("index", help="(re)write machine-readable docs/OP_INDEX.json")
    p.add_argument("--out", default="")
    p.set_defaults(fn=cmd_index)

    p = sub.add_parser("parity", help="cross-backend parity evidence (independent impls agree)")
    p.set_defaults(fn=cmd_parity)

    p = sub.add_parser("accel", help="GPU-ready batch backend: parity vs CPU registry ops")
    p.add_argument("--device", default="cpu")
    p.set_defaults(fn=cmd_accel)

    p = sub.add_parser("bench", help="throughput: CPU baseline vs batch (add --device cuda on a GPU)")
    p.add_argument("--n", type=int, default=200)
    p.add_argument("--size", type=int, default=256)
    p.add_argument("--device", default="cpu")
    p.set_defaults(fn=cmd_bench)

    p = sub.add_parser("algo", help="general-algorithm tier (algo-c): list/run/emit-c/emit-py/difftest")
    p.add_argument("action", choices=["list", "run", "emit-c", "emit-py", "difftest"])
    p.add_argument("op", nargs="?", default=None, help="op name (or 'all' for difftest)")
    p.add_argument("--seq", default="", help="run: comma-separated numbers, e.g. --seq 3,1,2")
    p.add_argument("--workdir", default="out/algo", help="difftest: where to emit/compile")
    p.add_argument("--no-c", action="store_true", help="difftest: force the honest C skip")
    p.set_defaults(fn=cmd_algo)

    p = sub.add_parser("synth", help="learn a texture from an image and synthesise a similar one")
    p.add_argument("inp"); p.add_argument("out")
    p.add_argument("--method", default="spectral", choices=["spectral", "pyramid", "patch"])
    p.add_argument("--size", default="", help="output HxW, e.g. 256x256 (default: source size)")
    p.add_argument("--seed", type=int, default=0)
    p.set_defaults(fn=cmd_synth)

    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
