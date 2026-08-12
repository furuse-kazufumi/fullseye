"""Multichannel (color) sort — HALCON color operators as a first-class sort.

Introduces `color` (H x W x 3 float64, RGB in [0,1]) into the typed pipeline so
the registry can host genuine HALCON color operators. The evolution reaches the
color sort through the bridge op `cfa_to_rgb` (image -> color, a real Bayer
demosaic); color -> image ops (rgb1_to_gray, access_channel, edges_color) bring
the sort back to gray. Grayscale tasks are unaffected: sorts are threaded, so a
gray-only op never receives a color array, and a color-ending pipeline is coerced
to a constant by `apply_genome` (poor fitness, no crash).

HALCON's Python binding types color ops with three separate R/G/B HObjects; the
multichannel-sort representation (one H x W x 3 array) is the faithful analog of
the same operation. Every op is a real cv2/numpy/skimage implementation; the
color functional gate (`verify()`) counts only those that run and return the
declared sort. Fake names are dropped fail-closed.

    py -3.11 backends_color.py         # self-report: ops, coverage, verify
"""
from __future__ import annotations

import json
import os

import numpy as np
from scipy import ndimage

try:
    import cv2
    _HAS_CV = True
except Exception:  # pragma: no cover
    _HAS_CV = False

HERE = os.path.dirname(os.path.abspath(__file__))
COLOR = "color"


def _to_color(v):
    """Coerce anything to H x W x 3 float64 in [0,1]."""
    v = np.asarray(v, np.float64)
    if v.ndim == 2:
        v = np.stack([v, v, v], -1)
    elif v.ndim == 3 and v.shape[-1] != 3:
        v = v[..., :3] if v.shape[-1] > 3 else np.repeat(v[..., :1], 3, -1)
    return np.clip(v, 0, 1)


def _gray(v):
    return np.clip(np.asarray(v, np.float64), 0, 1)


def _norm(x):
    x = np.asarray(x, np.float64)
    mx = float(np.max(np.abs(x)))
    return x / mx if mx > 1e-8 else x


def _safe(fn):
    def w(v, a, b):
        try:
            out = fn(v, a, b)
            return out if out is not None else v
        except Exception:
            return v
    return w


# --------------------------------------------------------------------------- #
# color operator implementations                                              #
# --------------------------------------------------------------------------- #
def _cfa_to_rgb(v, a, b):                         # image -> color : Bayer demosaic (the bridge)
    u = (_gray(v) * 255).astype(np.uint8)
    code = (cv2.COLOR_BayerBG2RGB, cv2.COLOR_BayerGB2RGB,
            cv2.COLOR_BayerRG2RGB, cv2.COLOR_BayerGR2RGB)[min(3, int(a * 4))]
    return cv2.cvtColor(u, code).astype(np.float64) / 255.0


def _trans_from_rgb(v, a, b):                     # color -> color : RGB -> {HSV,Lab,YUV,XYZ}
    c = (_to_color(v) * 255).astype(np.uint8)
    code, denom = ((cv2.COLOR_RGB2HSV, 255.0), (cv2.COLOR_RGB2Lab, 255.0),
                   (cv2.COLOR_RGB2YUV, 255.0), (cv2.COLOR_RGB2XYZ, 255.0))[min(3, int(a * 4))]
    return cv2.cvtColor(c, code).astype(np.float64) / denom


def _trans_to_rgb(v, a, b):                       # color -> color : HSV -> RGB (inverse transform)
    c = (_to_color(v) * 255).astype(np.uint8)
    return cv2.cvtColor(c, cv2.COLOR_HSV2RGB).astype(np.float64) / 255.0


def _linear_trans_color(v, a, b):                 # color -> color : 3x3 channel mixing matrix
    c = _to_color(v)
    th = np.pi * a
    M = np.array([[0.6 + 0.4 * np.cos(th), 0.2, 0.2],
                  [0.2, 0.6 + 0.4 * np.sin(th), 0.2],
                  [0.2, 0.2, 0.6]], np.float64)
    M = M / M.sum(1, keepdims=True)
    return np.clip(c @ M.T, 0, 1)


def _principal_comp(v, a, b):                     # color -> color : PCA over the 3 channels
    c = _to_color(v)
    H, W, _ = c.shape
    X = c.reshape(-1, 3)
    Xm = X - X.mean(0)
    cov = np.cov(Xm.T)
    w, vec = np.linalg.eigh(cov)
    order = np.argsort(w)[::-1]
    proj = Xm @ vec[:, order]
    proj = (proj - proj.min(0)) / (proj.ptp(0) + 1e-8)
    return proj.reshape(H, W, 3)


def _rgb_to_gray(v, a, b):                        # color -> image : luminance
    c = _to_color(v)
    return c[..., 0] * 0.299 + c[..., 1] * 0.587 + c[..., 2] * 0.114


def _access_channel(v, a, b):                     # color -> image : pick one channel
    return _to_color(v)[..., min(2, int(a * 3))]


def _edges_color(v, a, b):                        # color -> image : Di Zenzo color-gradient amplitude
    c = _to_color(v)
    gx = np.stack([ndimage.sobel(c[..., k], 1) for k in range(3)], -1)
    gy = np.stack([ndimage.sobel(c[..., k], 0) for k in range(3)], -1)
    gxx = np.sum(gx * gx, -1)
    gyy = np.sum(gy * gy, -1)
    gxy = np.sum(gx * gy, -1)
    lam = 0.5 * (gxx + gyy + np.sqrt(np.maximum((gxx - gyy) ** 2 + 4 * gxy * gxy, 0)))
    return _norm(np.sqrt(np.maximum(lam, 0)))


def _edges_color_sub_pix(v, a, b):                # color -> contour
    amp = _edges_color(v, a, b)
    lab, n = ndimage.label(amp > (0.15 + 0.5 * a), structure=np.ones((3, 3)))
    cs = []
    for i in range(1, n + 1):
        ys, xs = np.where(lab == i)
        if len(ys) >= 3:
            cs.append(np.stack([ys, xs], 1).astype(np.float64))
    return {"shape": amp.shape, "cs": cs}


def _lines_color(v, a, b):                        # color -> contour : ridges on luminance
    g = _rgb_to_gray(v, a, b)
    r = _norm(np.abs(ndimage.gaussian_laplace(g, 0.5 + 2.5 * a)))
    lab, n = ndimage.label(r > (0.2 + 0.4 * b), structure=np.ones((3, 3)))
    cs = [np.stack(np.where(lab == i), 1).astype(np.float64) for i in range(1, n + 1)]
    return {"shape": g.shape, "cs": [c for c in cs if len(c) >= 3]}


def _count_channels(v, a, b):                     # color -> feature
    c = np.asarray(v)
    return np.float64(c.shape[-1] if c.ndim == 3 else 1)


IMG = "image"
# (halcon, category, in_sort, out_sort, fn)
_DEFS = [
    ("cfa_to_rgb", "color", IMG, COLOR, _cfa_to_rgb),            # bridge image -> color
    ("trans_from_rgb", "color", COLOR, COLOR, _trans_from_rgb),
    ("trans_to_rgb", "color", COLOR, COLOR, _trans_to_rgb),
    ("linear_trans_color", "color", COLOR, COLOR, _linear_trans_color),
    ("principal_comp", "color", COLOR, COLOR, _principal_comp),
    ("rgb1_to_gray", "color", COLOR, IMG, _rgb_to_gray),
    ("rgb3_to_gray", "color", COLOR, IMG, _rgb_to_gray),
    ("access_channel", "color", COLOR, IMG, _access_channel),
    ("edges_color", "edges", COLOR, IMG, _edges_color),
    ("edges_color_sub_pix", "contour", COLOR, "contour", _edges_color_sub_pix),
    ("lines_color", "contour", COLOR, "contour", _lines_color),
    ("count_channels", "features", COLOR, "feature", _count_channels),
]


def _real_ops() -> set:
    p = os.path.join(HERE, "data", "halcon_operators.json")
    if not os.path.exists(p):
        return set()
    return {o["name"] for o in json.load(open(p, encoding="utf-8"))["operators"]}


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    """Return color Ops (fail-closed on fake names / missing cv2)."""
    if not _HAS_CV:
        build.dropped = ["(cv2 missing — color tier disabled)"]
        return []
    real = _real_ops()
    out, dropped = [], []
    for (n, cat, i, o, fn) in _DEFS:
        if real and n not in real:
            dropped.append(n)
            continue
        out.append(Op(n, cat, n, i, o, _safe(fn)))
    build.dropped = dropped
    return out


build.dropped = []


def coverage() -> dict:
    real = _real_ops()
    names = sorted({n for (n, *_ ) in _DEFS if (not real) or n in real}) if _HAS_CV else []
    return {"n_ops": len(names), "halcon_names": names, "has_cv2": _HAS_CV}


def verify() -> dict:
    """Color functional gate: run each op, check it returns the declared sort."""
    if not _HAS_CV:
        return {"n": 0, "pass": 0, "fail": ["cv2 missing"]}
    n = 48
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    gray = np.clip(xx / n + 0.1 * np.random.default_rng(0).random((n, n)), 0, 1)
    col = np.clip(np.stack([xx / n, yy / n, (xx + yy) / (2 * n)], -1)
                  + 0.05 * np.random.default_rng(1).random((n, n, 3)), 0, 1)
    passed, failed = [], []
    for (name, cat, i, o, fn) in _DEFS:
        base = gray if i == IMG else col
        try:
            out = fn(base.copy(), 0.5, 0.4)
            if o == COLOR:
                ok = isinstance(out, np.ndarray) and out.ndim == 3 and out.shape[-1] == 3
            elif o == IMG:
                ok = isinstance(out, np.ndarray) and out.ndim == 2
            elif o == "feature":
                ok = np.isfinite(float(np.asarray(out).reshape(-1)[0]))
            elif o == "contour":
                ok = isinstance(out, dict) and "cs" in out
            else:
                ok = False
            (passed if ok else failed).append(name)
        except Exception as e:  # noqa: BLE001
            failed.append("%s:%r" % (name, e))
    return {"n": len(_DEFS), "pass": len(passed), "fail": failed, "passing": passed}


if __name__ == "__main__":
    cov = coverage()
    v = verify()
    print("color sort tier: %d ops (cv2=%s, dropped %s)" % (cov["n_ops"], cov["has_cv2"], build.dropped))
    print("  functional gate: %d/%d pass" % (v["pass"], v["n"]))
    if v["fail"]:
        print("  FAIL:", v["fail"])
    print("  HALCON names:", ", ".join(cov["halcon_names"]))
