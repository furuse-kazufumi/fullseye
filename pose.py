"""Silhouette pose / posture descriptors (numpy + scipy, optional scikit-image).

From a binary figure mask this extracts a structural posture summary — a skeleton
graph (endpoints, junctions, limb count) and the body's principal axis (orientation,
elongation) — a compact descriptor for judging posture (evis / hillco) and a feed
for a body-language / pose-token model. It is silhouette-structural, not a learned
keypoint detector (that stays a future capability).
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

__all__ = ["skeletonize_mask", "skeleton_nodes", "principal_axis", "pose_descriptor"]


def skeletonize_mask(mask):
    """1-px morphological skeleton of a binary figure."""
    m = np.asarray(mask) > 0.5
    try:
        from skimage.morphology import skeletonize
        return skeletonize(m)
    except Exception:
        # crude fallback: repeated thinning via medial-axis distance ridge
        from scipy.ndimage import distance_transform_edt
        d = distance_transform_edt(m)
        ridge = (d >= ndimage.maximum_filter(d, 3) - 1e-9) & m
        return ridge


def skeleton_nodes(mask):
    """Endpoint and junction counts of the figure's skeleton.

    Returns a dict: n_endpoints, n_junctions (counted as connected components of
    end/branch pixels, robust to small junction clusters), and their coordinates.
    """
    skel = skeletonize_mask(mask).astype(np.uint8)
    nb = ndimage.convolve(skel, np.ones((3, 3), int), mode="constant") - skel
    endpoints = (skel == 1) & (nb == 1)
    junctions = (skel == 1) & (nb >= 3)
    _, n_end = ndimage.label(endpoints)
    jl, n_jun = ndimage.label(junctions, structure=np.ones((3, 3)))
    ey, ex = np.nonzero(endpoints)
    return {
        "n_endpoints": int(n_end),
        "n_junctions": int(n_jun),
        "endpoints": list(zip(ey.tolist(), ex.tolist())),
        "skeleton_length": int(skel.sum()),
    }


def principal_axis(mask):
    """Principal axis of the figure via PCA of foreground pixels.

    Returns (orientation_rad, elongation) where orientation is the angle of the
    major axis (atan2(dy, dx), image y downward) and elongation = sqrt(λmax/λmin)."""
    ys, xs = np.nonzero(np.asarray(mask) > 0.5)
    if len(xs) < 2:
        return 0.0, 1.0
    pts = np.stack([xs, ys], axis=1).astype(np.float64)
    pts -= pts.mean(0)
    cov = (pts.T @ pts) / len(pts)
    vals, vecs = np.linalg.eigh(cov)          # ascending eigenvalues
    major = vecs[:, -1]
    orientation = float(np.arctan2(major[1], major[0]))
    elongation = float(np.sqrt(max(vals[-1], 0) / max(vals[0], 1e-12)))
    return orientation, elongation


def pose_descriptor(mask):
    """Compact posture descriptor combining the skeleton graph and principal axis.

    Vector: [orientation, elongation, n_endpoints, n_junctions, fill_ratio,
    aspect_ratio] — enough to distinguish gross postures (upright vs crouched,
    limbs extended vs tucked) and to key a pose-token table."""
    m = np.asarray(mask) > 0.5
    nodes = skeleton_nodes(m)
    orient, elong = principal_axis(m)
    ys, xs = np.nonzero(m)
    if len(xs) == 0:
        return np.zeros(6)
    h = ys.max() - ys.min() + 1
    w = xs.max() - xs.min() + 1
    fill = float(m.sum()) / float(h * w)
    aspect = float(h) / float(w)
    return np.array([orient, elong, nodes["n_endpoints"], nodes["n_junctions"],
                     fill, aspect], np.float64)
