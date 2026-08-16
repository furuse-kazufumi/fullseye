"""N-ary HALCON-parity capability tier (image arithmetic, region set theory).

The single-image evolution pipeline threads ONE value, so it cannot host HALCON
operators that take two images (add_image, sub_image, ...) or two regions
(union2, intersection, ...). Those are still real HALCON capabilities the user
wants imgevolve to *do* — so they live here as genuine multi-argument functions
with an honest, separate coverage count. They are difftest-able and codegen-able
even though evolution does not select them.

Every op is a real numpy/scipy implementation (never a stub); `verify()` runs each
on canonical inputs and `coverage()` reports how many distinct real HALCON n-ary
operators are implemented. Fail-closed: names not in the scraped reference are
dropped, never counted.

    py -3.11 imgops_nary.py            # self-report: ops, coverage, verify
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Callable

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))


def _f(x):
    return np.clip(np.asarray(x, np.float64), 0.0, 1.0)


def _b(x):
    return np.asarray(x) > 0.5


def _u8(x):
    return (_f(x) * 255).astype(np.uint8)


@dataclass
class NaryOp:
    name: str
    halcon: str
    arity: int
    in_sorts: tuple
    out_sort: str
    fn: Callable          # fn(inputs: list, a: float, b: float) -> output
    desc: str = ""


# --- image (x2) -> image : HALCON arithmetic (Mult, Add parameters via a,b) --- #
def _add(io, a, b):
    return np.clip((_f(io[0]) + _f(io[1])) * (0.5 + a) + (b - 0.5), 0, 1)


def _sub(io, a, b):
    return np.clip((_f(io[0]) - _f(io[1])) * (0.5 + a) + (b), 0, 1)


def _mult(io, a, b):
    return np.clip(_f(io[0]) * _f(io[1]) * (0.5 + 1.5 * a) + (b - 0.5), 0, 1)


def _div(io, a, b):
    return np.clip(_f(io[0]) / np.maximum(_f(io[1]), 1e-3) * (0.1 + 0.9 * a), 0, 1)


def _abs_diff(io, a, b):
    return np.clip(np.abs(_f(io[0]) - _f(io[1])) * (0.5 + 1.5 * a), 0, 1)


def _max_img(io, a, b):
    return np.maximum(_f(io[0]), _f(io[1]))


def _min_img(io, a, b):
    return np.minimum(_f(io[0]), _f(io[1]))


def _and_img(io, a, b):
    return (np.bitwise_and(_u8(io[0]), _u8(io[1])).astype(np.float64)) / 255.0


def _or_img(io, a, b):
    return (np.bitwise_or(_u8(io[0]), _u8(io[1])).astype(np.float64)) / 255.0


def _convol(io, a, b):
    ker = np.asarray(io[1], np.float64)
    ker = ker / (np.abs(ker).sum() + 1e-8)
    return np.clip(ndimage.convolve(_f(io[0]), ker, mode="reflect"), 0, 1)


# --- region (x2) -> region : HALCON set theory ------------------------------- #
def _union2(io, a, b):
    return (_b(io[0]) | _b(io[1])).astype(np.float64)


def _intersection(io, a, b):
    return (_b(io[0]) & _b(io[1])).astype(np.float64)


def _difference(io, a, b):
    return (_b(io[0]) & ~_b(io[1])).astype(np.float64)


def _symm_difference(io, a, b):
    return (_b(io[0]) ^ _b(io[1])).astype(np.float64)


# --- image + region -> image ------------------------------------------------- #
def _reduce_domain(io, a, b):
    return _f(io[0]) * _b(io[1]).astype(np.float64)


def _overpaint_region(io, a, b):
    out = _f(io[0]).copy()
    out[_b(io[1])] = a
    return out


def _paint_gray(io, a, b):
    # paint image[1] gray values into image[0] where region... here 2 images:
    return np.where(_b(io[1]) if io[1].max() <= 1.0 else _f(io[1]) > a, _f(io[1]), _f(io[0]))


IMG, REG = "image", "region"

_DEFS = [
    ("add_image", "add_image", 2, (IMG, IMG), IMG, _add, "Add two images."),
    ("sub_image", "sub_image", 2, (IMG, IMG), IMG, _sub, "Subtract two images."),
    ("mult_image", "mult_image", 2, (IMG, IMG), IMG, _mult, "Multiply two images."),
    ("div_image", "div_image", 2, (IMG, IMG), IMG, _div, "Divide two images."),
    ("abs_diff_image", "abs_diff_image", 2, (IMG, IMG), IMG, _abs_diff, "Absolute difference of two images."),
    ("max_image", "max_image", 2, (IMG, IMG), IMG, _max_img, "Pixelwise maximum of two images."),
    ("min_image", "min_image", 2, (IMG, IMG), IMG, _min_img, "Pixelwise minimum of two images."),
    ("bit_and", "bit_and", 2, (IMG, IMG), IMG, _and_img, "Bitwise AND of two images."),
    ("bit_or", "bit_or", 2, (IMG, IMG), IMG, _or_img, "Bitwise OR of two images."),
    ("convol_image", "convol_image", 2, (IMG, IMG), IMG, _convol, "Convolve an image with a filter mask."),
    ("union2", "union2", 2, (REG, REG), REG, _union2, "Union of two regions."),
    ("intersection", "intersection", 2, (REG, REG), REG, _intersection, "Intersection of two regions."),
    ("difference", "difference", 2, (REG, REG), REG, _difference, "Difference of two regions."),
    ("symm_difference", "symm_difference", 2, (REG, REG), REG, _symm_difference, "Symmetric difference of two regions."),
    ("reduce_domain", "reduce_domain", 2, (IMG, REG), IMG, _reduce_domain, "Reduce the domain of an image."),
    ("overpaint_region", "overpaint_region", 2, (IMG, REG), IMG, _overpaint_region, "Overpaint regions in an image."),
    ("paint_gray", "paint_gray", 2, (IMG, IMG), IMG, _paint_gray, "Paint gray values into an image."),
]


def _real_ops() -> set:
    """Real HALCON names — generated py-module first, flat data/ JSON second.

    `halcon_names_data` ships in the wheel, `data/halcon_operators.json` does not,
    so reading only the JSON returned an EMPTY set on a pip-installed package and
    the fail-closed guard in `build_nary` admitted everything instead.
    """
    try:
        from halcon_names_data import HALCON_NAMES
        return set(HALCON_NAMES)
    except Exception:
        pass
    p = os.path.join(HERE, "data", "halcon_operators.json")
    if not os.path.exists(p):
        return set()
    return {o["name"] for o in json.load(open(p, encoding="utf-8"))["operators"]}


def build_nary() -> list[NaryOp]:
    """Compile n-ary ops, dropping any whose HALCON name is not real (fail-closed).

    An unavailable reference set drops everything rather than admitting everything
    — an unverifiable name is not a verified one.
    """
    real = _real_ops()
    out, dropped = [], []
    for (n, h, ar, ins, o, fn, d) in _DEFS:
        if h not in real:
            dropped.append(h)
            continue
        out.append(NaryOp(n, h, ar, ins, o, fn, d))
    build_nary.dropped = dropped
    return out


build_nary.dropped = []


def coverage() -> dict:
    ops = build_nary()
    return {"n_ops": len(ops), "dropped": build_nary.dropped,
            "halcon_names": sorted({o.halcon for o in ops})}


def verify() -> dict:
    """Run every op on canonical inputs; count those returning the declared sort.

    Fail-closed on both counts a "region" claim can be faked with: the output must
    be BINARY ({0,1}), not merely inside [0,1] (any grayscale image satisfies the
    range test), and an op that returns its first input unchanged is an identity,
    not an implementation, so it is failed rather than counted.
    """
    n = 48
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    i1 = np.clip(xx / n + 0.2, 0, 1)
    i2 = np.clip(((yy - n / 2) ** 2 + (xx - n / 2) ** 2 < 120).astype(float) * 0.8 + 0.1, 0, 1)
    r1 = (i1 > 0.5).astype(np.float64)
    r2 = (i2 > 0.5).astype(np.float64)
    passed, failed = [], []
    for op in build_nary():
        io = [i1 if s == IMG else r1 for s in op.in_sorts]
        io[1] = i2 if op.in_sorts[1] == IMG else r2
        try:
            out = op.fn([x.copy() for x in io], 0.5, 0.4)
            ok = isinstance(out, np.ndarray) and out.ndim == 2 and np.all(np.isfinite(out))
            if ok and op.out_sort == REG:
                ok = set(np.unique(np.round(out, 6)).tolist()) <= {0.0, 1.0}
                if not ok:
                    failed.append("%s:region not binary {0,1}" % op.halcon)
                    continue
            if ok and out.shape == io[0].shape and float(np.max(np.abs(out - io[0]))) <= 1e-9:
                failed.append("%s:identity on canonical inputs" % op.halcon)
                continue
            (passed if ok else failed).append(op.halcon)
        except Exception as e:  # noqa: BLE001
            failed.append("%s:%r" % (op.halcon, e))
    return {"n": len(build_nary()), "pass": len(passed), "fail": failed}


if __name__ == "__main__":
    cov = coverage()
    v = verify()
    print("n-ary capability tier: %d ops (dropped %s)" % (cov["n_ops"], cov["dropped"]))
    print("  functional gate: %d/%d pass" % (v["pass"], v["n"]))
    if v["fail"]:
        print("  FAIL:", v["fail"])
    print("  HALCON names:", ", ".join(cov["halcon_names"]))
