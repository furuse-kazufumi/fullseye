"""Object segmentation + description + (feature-based) identification.

For robot manipulation ("pick this up", "sort these") you need to (1) separate
objects from the scene, (2) describe each one, and (3) identify which is which.
This module wires the existing segmentation/region ops into per-instance object
records and a simple nearest-prototype classifier.

Honest scope: identification here is **feature-based** (shape/moment descriptors +
nearest prototype), not a learned/deep classifier — that (out_of_scope_model in
the operator disposition) remains a future capability. For appearance matching by
template, use the normalized-correlation operator.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

__all__ = ["segment_objects", "object_descriptor", "nearest_prototype", "draw_objects",
           "feature_table"]


def feature_table(objects, top=12):
    """Compact per-object feature lines (area, circularity, eccentricity, centroid)
    -- the region feature display a vision IDE shows for a segmented result."""
    lines = ["#    area  circ  ecc   centroid(y,x)"]
    for i, o in enumerate(objects[:top], 1):
        cy, cx = o["centroid"]
        lines.append("%-3d %6.0f %4.2f %4.2f  (%.0f,%.0f)" % (
            i, o["area"], o.get("circularity", float("nan")),
            o.get("eccentricity", float("nan")), cy, cx))
    if len(objects) > top:
        lines.append("... +%d more" % (len(objects) - top))
    return "\n".join(lines)


def _otsu_mask(g):
    """Otsu threshold -> foreground mask. Between-class variance is
    ``(mu·tot - w·muT)^2 / (w·wf)`` (Otsu 1979); it is evaluated only on bins where
    both classes are non-empty, so a degenerate last bin can no longer win and
    return an all-empty mask."""
    x = np.clip(np.asarray(g, np.float64), 0, 1)
    hist, edges = np.histogram(x, 256, (0, 1))
    hist = hist.astype(np.float64)
    w = np.cumsum(hist)
    tot = w[-1]
    if tot <= 0:
        return np.zeros_like(x, bool)
    mids = (edges[:-1] + edges[1:]) / 2
    mu = np.cumsum(hist * mids)
    muT = mu[-1]
    wf = tot - w
    valid = (w > 0) & (wf > 0)
    between = np.zeros_like(w)
    between[valid] = (mu[valid] * tot - w[valid] * muT) ** 2 / (w[valid] * wf[valid])
    t = mids[int(np.argmax(between))]
    return x > t


def segment_objects(image, threshold="otsu", invert: bool = False,
                    min_area: int = 1, connectivity: int = 2):
    """Segment foreground objects; return one record per connected component.

    Parameters
    ----------
    image     : (H, W) grayscale float in [0, 1] (or a binary {0,1} mask).
    threshold : 'otsu' (default), or a float in [0, 1], or 'none' if *image*
                is already a binary mask.
    invert    : treat dark objects on a light background.
    min_area  : drop components smaller than this (pixels).

    Each record is a dict: label, area, centroid (y, x), bbox (y0, x0, y1, x1),
    eccentricity, extent, solidity, orientation (rad), equiv_diameter, hu (7,),
    and mask (full-image bool). Records are sorted by area, largest first.
    """
    g = np.asarray(image, np.float64)
    if threshold == "none":
        mask = g > 0.5
    elif threshold == "otsu":
        mask = _otsu_mask(g)
    else:
        mask = g > float(threshold)
    if invert:
        mask = ~mask

    struct = ndimage.generate_binary_structure(2, 2 if connectivity == 2 else 1)
    lab, n = ndimage.label(mask, structure=struct)
    objs = []
    try:
        from skimage.measure import regionprops
        props = regionprops(lab)
        for p in props:
            if p.area < min_area:
                continue
            try:
                equiv_d = float(p.equivalent_diameter_area)   # skimage >= 0.26
            except Exception:
                equiv_d = float(p.equivalent_diameter)
            try:
                perim = float(p.perimeter)
            except Exception:
                perim = float("nan")
            circ = float(4 * np.pi * p.area / (perim * perim)) if perim > 0 else float("nan")
            y0, x0, y1, x1 = p.bbox
            objs.append(dict(
                label=int(p.label), area=float(p.area),
                centroid=(float(p.centroid[0]), float(p.centroid[1])),
                bbox=(int(y0), int(x0), int(y1), int(x1)),
                eccentricity=float(p.eccentricity),
                extent=float(p.extent), solidity=float(p.solidity),
                orientation=float(p.orientation),
                perimeter=perim, circularity=min(circ, 1.0) if circ == circ else circ,
                equiv_diameter=equiv_d,
                hu=np.asarray(p.moments_hu, np.float64),
                mask=(lab == p.label),
            ))
    except Exception:
        for i in range(1, n + 1):
            m = lab == i
            area = float(m.sum())
            if area < min_area:
                continue
            ys, xs = np.nonzero(m)
            objs.append(dict(
                label=int(i), area=area,
                centroid=(float(ys.mean()), float(xs.mean())),
                bbox=(int(ys.min()), int(xs.min()), int(ys.max()) + 1, int(xs.max()) + 1),
                eccentricity=float("nan"), extent=float(area / (((ys.max() - ys.min() + 1) *
                                                                 (xs.max() - xs.min() + 1)))),
                solidity=float("nan"), orientation=float("nan"),
                equiv_diameter=float(2 * np.sqrt(area / np.pi)),
                hu=_hu_moments(m.astype(np.float64)),
                mask=m,
            ))
    objs.sort(key=lambda o: o["area"], reverse=True)
    return objs


def _hu_moments(img):
    """Log-scaled Hu moment invariants (7,) — scale/rotation/translation robust."""
    y, x = np.mgrid[0:img.shape[0], 0:img.shape[1]]
    m00 = img.sum()
    if m00 <= 0:
        return np.zeros(7)
    xb = (x * img).sum() / m00
    yb = (y * img).sum() / m00

    def mu(p, q):
        return (((x - xb) ** p) * ((y - yb) ** q) * img).sum() / (m00 ** (1 + (p + q) / 2))

    n20, n02, n11 = mu(2, 0), mu(0, 2), mu(1, 1)
    n30, n03, n21, n12 = mu(3, 0), mu(0, 3), mu(2, 1), mu(1, 2)
    h = np.zeros(7)
    h[0] = n20 + n02
    h[1] = (n20 - n02) ** 2 + 4 * n11 ** 2
    h[2] = (n30 - 3 * n12) ** 2 + (3 * n21 - n03) ** 2
    h[3] = (n30 + n12) ** 2 + (n21 + n03) ** 2
    h[4] = ((n30 - 3 * n12) * (n30 + n12) * ((n30 + n12) ** 2 - 3 * (n21 + n03) ** 2) +
            (3 * n21 - n03) * (n21 + n03) * (3 * (n30 + n12) ** 2 - (n21 + n03) ** 2))
    h[5] = ((n20 - n02) * ((n30 + n12) ** 2 - (n21 + n03) ** 2) +
            4 * n11 * (n30 + n12) * (n21 + n03))
    h[6] = ((3 * n21 - n03) * (n30 + n12) * ((n30 + n12) ** 2 - 3 * (n21 + n03) ** 2) -
            (n30 - 3 * n12) * (n21 + n03) * (3 * (n30 + n12) ** 2 - (n21 + n03) ** 2))
    return -np.sign(h) * np.log10(np.abs(h) + 1e-30)


def object_descriptor(obj) -> np.ndarray:
    """A compact, scale/rotation-robust descriptor for identification: the 7 Hu
    moments plus two shape ratios (eccentricity, extent)."""
    ecc = obj.get("eccentricity", np.nan)
    ext = obj.get("extent", np.nan)
    extra = np.array([0.0 if not np.isfinite(ecc) else ecc,
                      0.0 if not np.isfinite(ext) else ext])
    return np.concatenate([np.asarray(obj["hu"], np.float64), extra])


def nearest_prototype(descriptor, prototypes: dict):
    """Classify a descriptor against ``{label: prototype_descriptor}`` by nearest
    Euclidean distance. Returns ``(label, distance)`` (``(None, inf)`` if empty)."""
    d = np.asarray(descriptor, np.float64)
    best, bd = None, np.inf
    for name, proto in prototypes.items():
        dist = float(np.linalg.norm(d - np.asarray(proto, np.float64)))
        if dist < bd:
            best, bd = name, dist
    return best, bd


def draw_objects(image, objects, box_color=(1.0, 0.0, 0.0)):
    """Return an RGB visualisation with each object's mask tinted and bbox drawn."""
    import imgio
    out = imgio.ensure_color(imgio.to_float01(image)).copy()
    rng = np.random.default_rng(0)
    for o in objects:
        col = rng.random(3)
        out = imgio.overlay_mask(out, o["mask"], color=col, alpha=0.35)
        y0, x0, y1, x1 = o["bbox"]
        y1 = min(y1, out.shape[0] - 1); x1 = min(x1, out.shape[1] - 1)
        out[y0:y1, x0] = box_color; out[y0:y1, x1] = box_color
        out[y0, x0:x1] = box_color; out[y1, x0:x1] = box_color
    return np.clip(out, 0, 1)
