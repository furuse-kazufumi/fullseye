"""Coverage recipes for the operators the first recipe round reported missing (2026-11-03).

Each item of the MISSING_OPS lists of book_2d / book_3d / book_measure / book_optics was checked across
every layer first (2-D registry and its HALCON aliases, every ledger, the ``fullseye`` facade, plain
module functions, ``opsearch.search_ops`` with synonyms). Most of them **existed** under another name
or vocabulary; those get a recipe here that uses the existing op:

* watershed basins, one label per object      -> ``hierarchical_watershed`` (segmentation, ``basins`` / ``n_basins``)
* watersheds_marker with a mask               -> ``blob_split`` (blob: labels = the mask, seeds = the markers,
                                                  priority high-first, so pass the inverted landscape)
* polar unwrap about a given centre / radii   -> ``polar_unwrap`` (3d: ``center=(row, col)``, ``r_in``, ``r_out``)
* grey volume -> binary volume                 -> ``vol_threshold`` (2-D registry, sort ``volume``; ``a`` is the level)
* TDOA + mic spacing -> bearing                -> ``tdoa_bearing`` (drive: GCC delay and asin(cΔt/d) in one op)
* PSD peak of surface_psd's pairs             -> ``spectral_stats`` (optics: ``peak_nm`` is the x of the peak in
                                                  the unit of the pairs' first column — here cycles/length)

Three were really missing and were added in the same change (their recipes need the regenerated
OP_GRAPH / docs/ops to pass the "op is in OP_GRAPH" and family checks):

* ``fit_circle_xld`` (shape2d)        — circle per XLD contour: row, col, radius (HALCON fit_circle_contour_xld)
* ``wave_dominant_frequency`` (math)  — strongest non-DC 2-D FFT peak: cycles/px, period, angle
* ``find_surface_pose`` (3d)          — ppf.py was on the facade only; now a ledger op ``points × points -> pose``

Samples carry the ``nw_`` prefix; every one is synthetic with a closed-form answer.
"""
from __future__ import annotations

import math

import numpy as np

from fullseye.recipebook.common import rng


# =================================================================================================
# samples
# =================================================================================================
def _coverage_disk(n, discs, sub=8):
    """Grey image of discs drawn by sub-pixel coverage (the edge greys carry the true boundary)."""
    yy, xx = np.mgrid[0:n, 0:n]
    off = (np.arange(sub) + 0.5) / sub - 0.5
    img = np.zeros((n, n))
    for (cy, cx, r, level) in discs:
        cov = np.zeros((n, n))
        for dy in off:
            for dx in off:
                cov += ((yy + dy - cy) ** 2 + (xx + dx - cx) ** 2 <= r * r)
        img = np.maximum(img, level * cov / (sub * sub))
    return img


def nw_bore(variant: int):
    """A round bore / washer (bright disc on dark), drawn by coverage. Truth = centre (row, col), radius."""
    cy, cx, r = (50.3, 44.6, 20.5) if variant == 0 else (41.7, 52.2, 14.25)
    img = 0.15 + 0.7 * _coverage_disk(96, [(cy, cx, r, 1.0)])
    return {"value": img, "aux": {}, "truth": {"row": cy, "col": cx, "radius": r}}


def nw_touching(variant: int):
    """k = 3 + variant touching discs r = 10 px, 16 px apart on one row (they merge into one component)."""
    k = 3 + int(variant)
    n = 96
    yy, xx = np.mgrid[0:n, 0:n]
    m = np.zeros((n, n), bool)
    for i in range(k):
        m |= (yy - 48) ** 2 + (xx - (16 + 16 * i)) ** 2 <= 10 ** 2
    img = np.where(m, 0.8, 0.15) + 0.01 * rng(variant, 61).standard_normal((n, n))
    return {"value": np.clip(img, 0.0, 1.0), "aux": {}, "truth": {"count": k}}


def nw_two_grey_parts(variant: int):
    """Two touching parts of different grey (0.45 / 0.85) on 0.1: one mask, two markers.

    Left part = rectangle rows 20..59, cols 10..(c-1); right part = rectangle cols c..(c+w-1); the
    marker of each is a 3x3 patch in its middle. Truth = total mask area and Σ label·area for labels
    1 (left) and 2 (right) — a watershed restricted to the mask keeps the background at 0.
    """
    c = 34 + 6 * int(variant)
    w = 22 - 4 * int(variant)
    img = np.full((80, 80), 0.1)
    img[20:60, 10:c] = 0.45
    img[20:60, c:c + w] = 0.85
    markers = np.zeros((80, 80), np.int32)
    markers[38:41, (10 + c) // 2 - 1:(10 + c) // 2 + 2] = 1
    markers[38:41, c + w // 2 - 1:c + w // 2 + 2] = 2
    a1, a2 = 40 * (c - 10), 40 * w
    return {"value": img, "aux": {"markers": markers},
            "truth": {"area": float(a1 + a2), "weighted": float(a1 + 2 * a2), "n": 2}}


def nw_offcentre_ring(variant: int):
    """A thin bright ring (Gaussian profile, σ 1.5 px) of radius R about an off-centre point.

    Truth = the column of the unwrapped image (r_in 10, r_out 40, 61 radii -> 0.5 px per column) where
    the ring lies: (R − 10) / 0.5.
    """
    cy, cx, R = (70.0, 52.0, 25.0) if variant == 0 else (58.0, 71.0, 31.0)
    yy, xx = np.mgrid[0:128, 0:128]
    img = 0.1 + 0.8 * np.exp(-((np.hypot(yy - cy, xx - cx) - R) ** 2) / (2 * 1.5 ** 2))
    return {"value": img, "aux": {"center": [cy, cx]}, "truth": {"ring_col": (R - 10.0) / 0.5}}


def nw_grey_spheres(variant: int):
    """Spheres (r 4 voxels) on a 0.1 background: bright ones 0.8 and dim ones 0.4.

    vol_count binarises at a fixed 0.5 and sees only the bright ones; thresholding at 0.25 first
    counts all of them. Truth = all spheres (3 + variant).
    """
    centres = [(8, 0.8), (20, 0.4), (32, 0.8)] + ([(44, 0.4)] if variant else [])
    zz, yy, xx = np.mgrid[0:24, 0:24, 0:52]
    v = np.full((24, 24, 52), 0.1)
    for c, b in centres:
        v[(zz - 12) ** 2 + (yy - 12) ** 2 + (xx - c) ** 2 <= 16] = b
    v = np.clip(v + 0.02 * rng(variant, 62).standard_normal(v.shape), 0.0, 1.0)
    return {"value": v, "aux": {}, "truth": {"count": len(centres)}}


def _frac_delay(x, s):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x))
    return np.fft.irfft(X * np.exp(-2j * np.pi * f * s), len(x))


def nw_mic_pair(variant: int):
    """Broadband source at a known bearing θ, two mics d = 0.2 m apart, 48 kHz, c = 343 m/s.

    The right channel is the left delayed by Δt = d sin θ / c (fractional delay in the frequency
    domain) — truth = θ (deg) and Δt (s).
    """
    theta = 25.0 if variant == 0 else -40.0
    fs, d, c = 48000.0, 0.2, 343.0
    src = rng(variant, 63).standard_normal(4096)
    dt = d * math.sin(math.radians(theta)) / c
    left = src
    right = _frac_delay(src, dt * fs)
    return {"value": left, "aux": {"right": right, "fs": fs, "d": d},
            "truth": {"bearing_deg": theta, "delay": dt}}


def nw_feed_marks(variant: int):
    """A turned / milled surface: feed marks of wavelength λ (mm) plus fine roughness, dx = 0.01 mm.

    Truth = the PSD peak spatial frequency q = 1/λ (cycles/mm) and λ itself.
    """
    lam = 0.08 if variant == 0 else 0.125
    dx = 0.01
    yy, xx = np.mgrid[0:128, 0:128]
    z = 0.5e-3 * np.sin(2 * np.pi * xx * dx / lam) + 0.02e-3 * rng(variant, 64).standard_normal((128, 128))
    return {"value": z, "aux": {"dx": dx}, "truth": {"q_peak": 1.0 / lam, "wavelength": lam}}


def nw_grating(variant: int):
    """Stripes cos(2π(x cosθ + y sinθ)/p) — truth = θ (deg) and p (px)."""
    theta, p = (30.0, 8.0) if variant == 0 else (115.0, 11.0)
    th = math.radians(theta)
    yy, xx = np.mgrid[0:64, 0:64]
    img = 0.5 + 0.4 * np.cos(2 * np.pi * (xx * math.cos(th) + yy * math.sin(th)) / p)
    img = np.clip(img + 0.02 * rng(variant, 65).standard_normal(img.shape), 0.0, 1.0)
    return {"value": img, "aux": {}, "truth": {"angle_deg": theta, "period": p}}


def _rot(axis, deg):
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    t = math.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + math.sin(t) * K + (1 - math.cos(t)) * K @ K


def nw_bracket_scene(variant: int):
    """Model = an L-bracket with a boss (no rotational symmetry); scene = the same part moved by a known
    (R, t), 10 % of its points dropped, 0.005 noise, 40 clutter points 3 units above, order shuffled.
    Truth = (R, t).

    ★Honest scope (2026-11-03 probes): the scene reuses the model's own sampling. With 30 % of this coarse
    model dropped, or with a scene resampled independently on the same surfaces, the point-to-point ICP
    refinement slides on the plates: 1-3 deg / 0.03-0.07 translation error (the model spacing, 0.33-0.5).
    A denser model of the same part (372 points) made the vote flip to a 170-175 deg wrong pose and took
    13-17 s — reported as a finding on ppf, not hidden by this sample."""
    g = np.linspace(0.0, 1.0, 7)
    base = np.array([[x * 3.0, y * 2.0, 0.0] for x in g for y in g])
    wall = np.array([[0.0, y * 2.0, z * 1.5] for y in g for z in g[1:]])
    th = np.linspace(0.0, 2 * np.pi, 16, endpoint=False)
    boss = np.array([[2.2 + 0.35 * math.cos(a), 0.6 + 0.35 * math.sin(a), z] for a in th for z in (0.3, 0.6, 0.9)])
    model = np.vstack([base, wall, boss])
    R, t = ((_rot((0.0, 0.0, 1.0), 35.0), np.array([0.5, -0.3, 0.2])) if variant == 0
            else (_rot((1.0, 1.0, 0.3), 65.0), np.array([-0.4, 0.8, 0.1])))
    g2 = rng(variant, 66)
    keep = g2.permutation(len(model))[: int(round(0.9 * len(model)))]
    scene = model[keep] @ R.T + t + 0.005 * g2.standard_normal((len(keep), 3))
    scene = np.vstack([scene, g2.uniform(-1.0, 4.0, (40, 3)) + np.array([0.0, 0.0, 3.0])])
    scene = scene[g2.permutation(len(scene))]
    return {"value": model, "aux": {"scene": scene},
            "truth": {"tx": float(t[0]), "ty": float(t[1]), "tz": float(t[2]),
                      "r00": float(R[0, 0]), "r12": float(R[1, 2])}}


SAMPLES = {
    "nw_bore": nw_bore, "nw_touching": nw_touching, "nw_two_grey_parts": nw_two_grey_parts,
    "nw_offcentre_ring": nw_offcentre_ring, "nw_grey_spheres": nw_grey_spheres, "nw_mic_pair": nw_mic_pair,
    "nw_feed_marks": nw_feed_marks, "nw_grating": nw_grating, "nw_bracket_scene": nw_bracket_scene,
}


# =================================================================================================
# recipes
# =================================================================================================
RECIPES = [
    # ------------------------------------------------ new op: fit_circle_xld (shape2d), family 2d
    {"name": "Measure — bore centre and radius from a sub-pixel contour (circle fit per XLD contour)",
     "family": "2d", "task": "measure", "task_class": "measurement", "halcon": "2D Metrology",
     "input_sort": "image", "sample": "nw_bore",
     "stages": [{"op": "threshold_sub_pix", "a": 0.5, "b": 0.5}, {"op": "fit_circle_xld"}],
     "expect": [{"get": ["n_contours"], "equals": 1},
                {"get": ["row", 0], "approx": "row", "atol": 0.06},
                {"get": ["col", 0], "approx": "col", "atol": 0.06},
                {"get": ["radius", 0], "approx": "radius", "atol": 0.15}],
     "note": "HALCON threshold_sub_pix -> fit_circle_contour_xld: the iso-grey line at 0.5 of a round bore / "
             "washer as a sub-pixel XLD contour, then a geometric least-squares circle per contour (row, col, "
             "radius in px, RMS residual). The disc is drawn by pixel coverage, so the truth is the drawn circle; "
             "the ~0.08 px radius excess is the contour extraction, not the fit (exact on points on a circle)."},
    # ------------------------------------------------ existing: hierarchical_watershed basins
    {"name": "Inspect — count touching parts as watershed basins (one label per object)",
     "family": "segmentation", "task": "count", "task_class": "inspection", "halcon": "Segmentation",
     "input_sort": "image", "sample": "nw_touching",
     "stages": [{"op": "threshold", "a": 0.5, "b": 0.5},
                {"op": "distance_transform", "a": 0.5, "b": 0.5},
                {"op": "invert_image", "a": 0.5, "b": 0.5},
                {"op": "hierarchical_watershed", "kw": {"mask": "$s1"}}],
     "expect": [{"get": ["n_basins"], "equals": "count"}, {"get": ["labels", "@max"], "equals": "count"}],
     "note": "HALCON watersheds with 'basins' output: binarise, distance map (normalised, peak 1 at each part's "
             "centre), invert it so every part is a valley, then the dynamics watershed inside the part mask "
             "returns the basins as a label image (1..k) and their number. Touching discs r = 10 px 16 px "
             "apart: 3 / 4 basins = 3 / 4 parts, each a measurable label."},
    # ------------------------------------------------ existing: blob_split as a masked marker watershed
    {"name": "Segment — marker-controlled watershed inside a mask (two touching parts, background kept out)",
     "family": "blob", "task": "segment", "task_class": "inspection", "halcon": "Segmentation",
     "input_sort": "image", "sample": "nw_two_grey_parts",
     "stages": [{"op": "threshold", "a": 0.25, "b": 0.5},
                {"op": "blob_label", "args": ["$s1"]},
                {"op": "sobel_amp", "args": ["$in"], "a": 0.5, "b": 0.5},
                {"op": "invert_image", "a": 0.5, "b": 0.5},
                {"op": "blob_split", "args": ["$s2", "$aux.markers", "$s4"]}],
     "expect": [{"get": ["@max"], "equals": "n"}, {"get": ["@count"], "approx": "area", "atol": 0.5},
                {"get": ["@sum"], "approx": "weighted", "rtol": 0.03}],
     "note": "watersheds_marker with a mask: the part mask (grey > 0.25) as one label, two operator markers, and "
             "the gradient magnitude as the landscape. blob_split floods from the markers in descending order of "
             "its priority field, so the inverted gradient makes it a classic low-first watershed; it never "
             "leaves the mask, so the labelled area equals the mask area exactly and each part's area is right "
             "to ~3 % (the dam sits on the grey step between them)."},
    # ------------------------------------------------ existing: polar_unwrap about a given centre
    {"name": "Measure — unwrap an off-centre ring about its centre and read its radius",
     "family": "3d", "task": "measure", "task_class": "measurement", "halcon": "Transformations",
     "input_sort": "image", "sample": "nw_offcentre_ring",
     "stages": [{"op": "polar_unwrap", "kw": {"center": "$aux.center", "r_in": 10.0, "r_out": 40.0,
                                               "ntheta": 180, "nr": 61}},
                {"op": "img_to_projection_profile", "a": 0.0, "b": 0.2}],
     "expect": [{"get": ["@argmax"], "approx": "ring_col", "atol": 1.0}],
     "note": "HALCON polar_trans_image_ext with Row / Column / RadiusStart / RadiusEnd: unwrap the annulus "
             "10..40 px about the located centre (row, col) into 180 angles x 61 radii, then the mean over angle "
             "per radius; the ring's column is (R − 10) / 0.5. An off-centre ring unwraps to a straight line only "
             "about its own centre — the image-centre-only polar_trans_image cannot do this."},
    # ------------------------------------------------ existing: vol_threshold (registry, volume sort)
    {"name": "Inspect — count bright and dim inclusions in a grey volume (threshold, then count)",
     "family": "2d", "task": "count", "task_class": "inspection", "halcon": None,
     "input_sort": "volume", "sample": "nw_grey_spheres",
     "stages": [{"op": "vol_threshold", "a": 0.25, "b": 0.5}, {"op": "vol_count", "a": 0.5, "b": 0.5}],
     "expect": [{"get": [], "equals": "count"}],
     "note": "CT / confocal stack: binarise the grey volume at an explicit level (a = 0.25, absolute grey in "
             "[0, 1]) so dim inclusions (0.4) are kept as well as bright ones (0.8), then count the 6-connected "
             "components. vol_count alone binarises at a fixed 0.5 and would see only the bright spheres."},
    # ------------------------------------------------ existing: tdoa_bearing
    {"name": "Sense — bearing of a sound source from a microphone pair (time difference of arrival)",
     "family": "drive", "task": "estimate", "task_class": "sensing", "halcon": None,
     "input_sort": "signal", "sample": "nw_mic_pair",
     "stages": [{"op": "tdoa_bearing", "args": ["$in", "$aux.right", "$aux.fs", "$aux.d"]}],
     "expect": [{"get": ["bearing_deg"], "approx": "bearing_deg", "atol": 0.3},
                {"get": ["delay"], "approx": "delay", "atol": 2e-6}],
     "note": "two microphones 0.2 m apart at 48 kHz: the delay Δt from the up-sampled cross-correlation "
             "(restricted to |Δt| ≤ d/c), then the far-field bearing θ = asin(c Δt / d) with c = 343 m/s "
             "(left positive). Front/back stay ambiguous with two mics."},
    # ------------------------------------------------ existing: surface_psd -> spectral_stats
    {"name": "Measure — feed-mark wavelength of a machined surface from its areal PSD peak",
     "family": "roughness", "task": "measure", "task_class": "measurement", "halcon": None,
     "input_sort": "depth", "sample": "nw_feed_marks",
     "stages": [{"op": "surface_psd", "kw": {"dx": "$aux.dx"}}, {"op": "spectral_stats"}],
     "expect": [{"get": ["peak_nm"], "approx": "q_peak", "rtol": 0.03}],
     "note": "areal PSD of a height map (ring average, q in cycles/mm since dx is in mm), then the curve summary: "
             "the peak's abscissa is the dominant spatial frequency q = 1/λ of the feed marks (λ 0.08 / "
             "0.125 mm). spectral_stats names it peak_nm, but it is the x of the peak in the pairs' own unit."},
    # ------------------------------------------------ new op: wave_dominant_frequency (math)
    {"name": "Measure — period and direction of a stripe / grating texture (strongest 2-D FFT peak)",
     "family": "math", "task": "measure", "task_class": "measurement", "halcon": None,
     "input_sort": "image", "sample": "nw_grating",
     "stages": [{"op": "wave_dominant_frequency"}],
     "expect": [{"get": ["period_px"], "approx": "period", "rtol": 0.01},
                {"get": ["angle_deg"], "approx": "angle_deg", "atol": 0.5}],
     "note": "pitch of a grating, halftone screen, fabric weave or machining texture together with its "
             "orientation: Hann-windowed 2-D FFT, the largest non-DC peak refined by a log-parabola per axis, "
             "returned as cycles/px, period px and the wave-vector angle (deg, normal to the stripes)."},
    # ------------------------------------------------ new op: find_surface_pose (3d)
    {"name": "3D — find a known part's 6-DoF pose in a scene cloud (PPF surface matching)",
     "family": "3d", "task": "locate", "task_class": "3d", "halcon": "3D Matching",
     "input_sort": "points", "sample": "nw_bracket_scene",
     "stages": [{"op": "find_surface_pose", "args": ["$in", "$aux.scene"]}],
     "expect": [{"get": [1, 0], "approx": "tx", "atol": 0.02}, {"get": [1, 1], "approx": "ty", "atol": 0.02},
                {"get": [1, 2], "approx": "tz", "atol": 0.02}, {"get": [0, 0, 0], "approx": "r00", "atol": 0.02},
                {"get": [0, 1, 2], "approx": "r12", "atol": 0.02}],
     "note": "HALCON find_surface_model: point-pair-feature voting (Drost 2010) over the model's oriented "
             "normals finds the pose without an initial guess, then ICP refines it; the ledger returns the pose "
             "canon (R, t) with scene ≈ model R^T + t. Scene = the part moved, 10 % of its points dropped, noise "
             "0.005, 40 clutter points, shuffled — the bracket has no rotational symmetry, so the pose is unique. "
             "The scene reuses the model's sampling; an independently resampled scene is 1-3 deg off (ICP slides "
             "on the plates of this coarse model), see the sample's docstring."},
]


#: 2026-11-03: 項目の 1 つ(voxel -> voxel)だけは語彙の側に残る。
MISSING_OPS = [
    {"family": "3d", "need": "voxel -> voxel grey threshold (the ledger twin of the registry's vol_threshold)",
     "why": "vol_threshold exists (2-D registry, sort 'volume', a = absolute level) and the volume-sorted chain "
            "vol_threshold -> vol_count runs; but the ledger's voxel chain (vol_label, regionprops3d, "
            "skeletonize_vol) takes 'voxel', and no op turns a grey voxel volume into a binary one at a chosen "
            "level, so threshold -> label / measure in 3-D still has a type cut between 'volume' and 'voxel'"},
]

FAILED_ATTEMPTS = [
    {"family": "shape2d", "recipe": "contour -> from_xld -> elliptic_fourier (EFD of a sub-pixel contour)",
     "op": "from_xld",
     "error": "opsshape2d declares from_xld inputs ['table'], but the function requires the XLD contour dict "
              "{'shape', 'cs'} and refuses a table: fs.ledger.from_xld([[1, 2], [3, 4]]) -> ValueError: from_xld: "
              "contour must be an XLD contour dict with key 'cs', got list. The registry contour producers "
              "(threshold_sub_pix, edges_sub_pix) output 'contour', so contour -> from_xld is a type cut although "
              "the call works; the declaration should be ['contour']",
     "cause": "declaration_lie"},
]


NOTES_JA = {
    "Measure — bore centre and radius from a sub-pixel contour (circle fit per XLD contour)":
        "穴の中心と半径をサブピクセル輪郭から測る — threshold_sub_pix で円板の縁を XLD 輪郭にし、"
        "fit_circle_xld で輪郭ごとに幾何距離の円を当てて中心(行・列)と半径を画素で読む"
        "(HALCON fit_circle_contour_xld)。真値は被覆率で描いた円。",
    "Inspect — count touching parts as watershed basins (one label per object)":
        "接した部品を分水嶺の盆地として数える — 二値化・距離変換・反転で部品ごとの谷を作り、"
        "hierarchical_watershed をマスクの中で回して盆地のラベル画像(1..k)と個数を得る"
        "(HALCON watersheds の basins 出力)。",
    "Segment — marker-controlled watershed inside a mask (two touching parts, background kept out)":
        "マスク付きのマーカー分水嶺 — 部品のマスクを 1 ラベル、作業者の印を種、勾配の反転を優先度にして "
        "blob_split で流す。マスクの外へは出ないので面積の合計がマスクと一致し、2 部品の面積が分かる"
        "(watersheds_marker に mask 引数が無い穴の代わり)。",
    "Measure — unwrap an off-centre ring about its centre and read its radius":
        "中心のずれたリングを、その中心で極座標展開して半径を読む — polar_unwrap に中心(行・列)と"
        "半径の範囲を渡し、角度で平均した断面の最大の列からリングの半径を得る"
        "(HALCON polar_trans_image_ext の Row/Column/Radius)。",
    "Inspect — count bright and dim inclusions in a grey volume (threshold, then count)":
        "濃淡ボリュームの明るい介在物と暗い介在物を数える — vol_threshold で明示のレベル(0.25)で"
        "二値化してから vol_count で連結成分を数える。vol_count だけだと 0.5 固定で暗い方を落とす。",
    "Sense — bearing of a sound source from a microphone pair (time difference of arrival)":
        "マイク 2 本で音源の方位を測る — tdoa_bearing が相互相関で到着時間差 Δt を取り、"
        "遠方近似 θ = asin(cΔt/d) で方位(度)にする。マイク間隔 0.2 m、48 kHz。",
    "Measure — feed-mark wavelength of a machined surface from its areal PSD peak":
        "加工面の送りマークの波長を面 PSD の山から測る — surface_psd の (q, PSD) 対を spectral_stats に"
        "渡し、山の横軸 q(cycles/mm)= 1/λ を読む。peak_nm という名前だが単位は対の横軸のまま。",
    "Measure — period and direction of a stripe / grating texture (strongest 2-D FFT peak)":
        "縞・格子・テクスチャの周期と向きを測る — wave_dominant_frequency が Hann 窓の 2-D FFT の DC 以外の"
        "最大の山を対数放物線で細かく読み、周期(画素)と波数ベクトルの向き(度)を返す。",
    "3D — find a known part's 6-DoF pose in a scene cloud (PPF surface matching)":
        "既知の部品の 6 自由度の姿勢を場面の点群から求める — find_surface_pose が点対特徴(PPF)の投票で"
        "初期値なしに姿勢を立て、ICP で詰めて (R, t) を返す(HALCON find_surface_model)。",
}
