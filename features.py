"""Sparse feature detection, description and matching (numpy + scipy).

The sparse counterpart to :mod:`flow` (dense motion): find distinctive keypoints in
two images, describe a patch around each, and match them across the pair to get
point correspondences. Those correspondences feed :func:`camera.recover_pose` /
:func:`camera.solve_pnp` / :func:`odometry.pnp_odometry` — the feature-based front
end a robot uses for wide-baseline pose, relocalization and loop closure, where the
small-displacement assumption of dense optical flow breaks down.

Honest scope: the descriptor here is a **normalized intensity patch** matched by
SSD/NCC — invariant to affine illumination change but NOT to large rotation or
scale (that is what ORB/SIFT add). It is the right tool for small-to-moderate
baselines and template tracking; for large viewpoint change use the optional cv2
ORB path. numpy/scipy only.

Reference (public literature — reimplemented, not derived from any product):
- Harris & Stephens, "A combined corner and edge detector", Alvey 1988.
- Rosten & Drummond, "Machine learning for high-speed corner detection", ECCV 2006
  (FAST).
- Lowe, "Distinctive image features from scale-invariant keypoints", IJCV 2004
  (ratio test).
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

__all__ = ["harris_corners", "fast_corners", "describe_patches",
           "match_descriptors", "match_keypoints"]


def _gray(img):
    a = np.asarray(img, np.float64)
    if a.ndim == 3:
        a = a[..., :3].mean(-1)
    if a.ndim != 2:
        raise ValueError("img must be 2-D (or H,W,3)")
    return a


def _nms_peaks(response, min_distance, thresh, max_n):
    """Non-max-suppressed peaks of a response map, strongest first (row, col)."""
    size = 2 * int(min_distance) + 1
    mx = ndimage.maximum_filter(response, size, mode="constant", cval=-np.inf)
    peaks = (response == mx) & (response >= thresh)
    ys, xs = np.where(peaks)
    if ys.size == 0:
        return np.empty((0, 2), int)
    vals = response[ys, xs]
    order = np.argsort(-vals)
    ys, xs = ys[order], xs[order]
    if max_n is not None and ys.size > max_n:
        ys, xs = ys[:max_n], xs[:max_n]
    return np.stack([ys, xs], 1)


def harris_corners(img, sigma: float = 1.0, k: float = 0.04,
                   thresh_rel: float = 0.01, min_distance: int = 5,
                   max_n: int = 500) -> np.ndarray:
    """Harris corner keypoints (Harris & Stephens 1988), strongest first.

    Builds the Gaussian-windowed structure tensor from image gradients, scores each
    pixel ``R = det(M) - k*trace(M)^2``, and returns the non-max-suppressed peaks
    above ``thresh_rel * R.max()`` that are at least *min_distance* apart. Returns
    keypoints as (N, 2) ``(row, col)``."""
    g = _gray(img)
    gy, gx = np.gradient(g)
    Ixx = ndimage.gaussian_filter(gx * gx, sigma)
    Iyy = ndimage.gaussian_filter(gy * gy, sigma)
    Ixy = ndimage.gaussian_filter(gx * gy, sigma)
    det = Ixx * Iyy - Ixy * Ixy
    trace = Ixx + Iyy
    R = det - k * trace * trace
    if R.max() <= 0:
        return np.empty((0, 2), int)
    return _nms_peaks(R, min_distance, float(thresh_rel) * R.max(), max_n)


def fast_corners(img, thresh: float = 0.05, min_distance: int = 5,
                 max_n: int = 500, n_contig: int = 9) -> np.ndarray:
    """FAST-style corner keypoints (Rosten & Drummond 2006), strongest first.

    A pixel is a corner if at least *n_contig* contiguous pixels on the radius-3
    Bresenham circle are all brighter than centre+thresh or all darker than
    centre-thresh. The corner score (used for NMS ordering) is the summed absolute
    contrast over the ring. Returns (N, 2) ``(row, col)``."""
    g = _gray(img)
    # the 16 offsets of the radius-3 FAST ring, clockwise from top
    ring = [(-3, 0), (-3, 1), (-2, 2), (-1, 3), (0, 3), (1, 3), (2, 2), (3, 1),
            (3, 0), (3, -1), (2, -2), (1, -3), (0, -3), (-1, -3), (-2, -2), (-3, -1)]
    H, W = g.shape
    vals = np.stack([np.roll(np.roll(g, -dy, 0), -dx, 1) for dy, dx in ring])  # (16,H,W)
    bright = vals > (g + thresh)
    dark = vals < (g - thresh)

    def contig(mask):
        # is there a run of >= n_contig True around the 16-ring (circular)?
        m2 = np.concatenate([mask, mask[:n_contig - 1]], 0)          # wrap
        run = np.zeros_like(g)
        cur = np.zeros_like(g)
        for i in range(m2.shape[0]):
            cur = np.where(m2[i], cur + 1, 0.0)
            run = np.maximum(run, cur)
        return run >= n_contig

    is_corner = contig(bright) | contig(dark)
    score = np.abs(vals - g).sum(0) * is_corner
    score[:3] = score[-3:] = 0.0                      # ring undefined at the border
    score[:, :3] = score[:, -3:] = 0.0
    if score.max() <= 0:
        return np.empty((0, 2), int)
    return _nms_peaks(score, min_distance, 1e-9, max_n)


def describe_patches(img, keypoints, patch: int = 9):
    """Zero-mean, unit-norm intensity-patch descriptor around each keypoint.

    A ``patch x patch`` window is normalized (mean-subtracted, L2-normalized) so its
    dot product with another is the correlation — illumination-affine invariant.
    Keypoints closer than ``patch//2`` to the border are dropped. Returns
    ``(descriptors (M, patch*patch), kept_keypoints (M, 2))``."""
    g = _gray(img)
    kp = np.asarray(keypoints, int).reshape(-1, 2)
    r = int(patch) // 2
    H, W = g.shape
    keep = (kp[:, 0] >= r) & (kp[:, 0] < H - r) & (kp[:, 1] >= r) & (kp[:, 1] < W - r)
    kp = kp[keep]
    desc = np.empty((kp.shape[0], patch * patch))
    for i, (y, x) in enumerate(kp):
        p = g[y - r:y + r + 1, x - r:x + r + 1].ravel()
        p = p - p.mean()
        nrm = np.linalg.norm(p)
        desc[i] = p / nrm if nrm > 1e-12 else p
    return desc, kp


def match_descriptors(desc1, desc2, ratio: float = 0.8, mutual: bool = True):
    """Match two descriptor sets by nearest neighbour with Lowe's ratio test.

    For each descriptor in set 1, finds its two nearest neighbours in set 2 (by SSD)
    and keeps the match only if the best is clearly better than the second
    (``d1 < ratio * d2``, Lowe 2004), rejecting ambiguous matches. With
    ``mutual=True`` the match must also be each other's best (symmetric). Returns
    match index pairs ``(M, 2)`` into (set1, set2)."""
    A = np.asarray(desc1, np.float64)
    B = np.asarray(desc2, np.float64)
    if A.shape[0] == 0 or B.shape[0] == 0:
        return np.empty((0, 2), int)
    if A.shape[1] != B.shape[1]:
        raise ValueError("descriptor dimensions differ")
    # squared distances (M1, M2); ||a-b||^2 = |a|^2 + |b|^2 - 2 a.b
    d = (A ** 2).sum(1)[:, None] + (B ** 2).sum(1)[None, :] - 2.0 * A @ B.T
    d = np.maximum(d, 0.0)
    nn = np.argsort(d, axis=1)[:, :2]
    best = nn[:, 0]
    matches = []
    b_best = np.argmin(d, axis=0)                      # set2 -> best set1 (for mutual)
    for i in range(A.shape[0]):
        j = best[i]
        d1 = d[i, j]
        d2 = d[i, nn[i, 1]] if B.shape[0] > 1 else np.inf
        if d1 < (ratio ** 2) * d2 if np.isfinite(d2) else True:
            if not mutual or b_best[j] == i:
                matches.append((i, int(j)))
    return np.asarray(matches, int).reshape(-1, 2)


def match_keypoints(img1, img2, detector: str = "harris", patch: int = 9,
                    ratio: float = 0.8, **detector_kw):
    """Detect, describe and match keypoints between two images in one call.

    Runs *detector* ('harris' or 'fast') on both images, describes patches, and
    matches them. Returns ``(pts1, pts2)`` corresponding points as (M, 2) **(x, y)**
    pixel coordinates (ready for :func:`camera.recover_pose` / :func:`camera.solve_pnp`).
    Extra keyword args go to the detector."""
    det = {"harris": harris_corners, "fast": fast_corners}.get(detector)
    if det is None:
        raise ValueError("detector must be 'harris' or 'fast', got %r" % (detector,))
    k1 = det(img1, **detector_kw)
    k2 = det(img2, **detector_kw)
    d1, kp1 = describe_patches(img1, k1, patch)
    d2, kp2 = describe_patches(img2, k2, patch)
    m = match_descriptors(d1, d2, ratio=ratio)
    if m.shape[0] == 0:
        return np.empty((0, 2), float), np.empty((0, 2), float)
    pts1 = kp1[m[:, 0]][:, ::-1].astype(np.float64)    # (row,col) -> (x,y)
    pts2 = kp2[m[:, 1]][:, ::-1].astype(np.float64)
    return pts1, pts2
