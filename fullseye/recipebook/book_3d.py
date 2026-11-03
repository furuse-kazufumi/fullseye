"""3-D, depth, volume, CT, DEM and calibration recipes (coverage book ``book_3d``).

Families: 3d · reprconv · tomography · dem · calib · printpath · live4d · volcolor · geocam · videocube ·
cadmap · fit · fileio.
HALCON chapters: 3D Object Model, 3D Matching, 3D Reconstruction, Calibration, 2D Metrology, Matching.

Every sample here is synthetic with a closed-form answer (a sphere radius, a plane normal, a known rigid
transform, the slope of a tilted DEM, the pixel area of a CT phantom disk, the focal length used to render
calibration views ...). Sample names carry the ``t3_`` prefix.
"""
from __future__ import annotations

import numpy as np

from fullseye.recipebook.common import rng, sphere_points, tilted_plane_depth


# ---- helpers ---------------------------------------------------------------------------------
def _rot_z(deg):
    t = np.radians(deg)
    c, s = np.cos(t), np.sin(t)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def _blob_shape(g, n):
    """Asymmetric closed surface (ellipsoid 1 x 0.6 x 0.4 with a bump) — no symmetry for ICP to slip along."""
    u = g.standard_normal((n, 3))
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    p = u * np.array([1.0, 0.6, 0.4])
    p += 0.25 * np.exp(-8 * np.sum((u - np.array([0.6, 0.6, 0.5])) ** 2, axis=1))[:, None] * u
    return p


# ---- samples (point clouds) ------------------------------------------------------------------
def t3_sphere(variant):
    """Common sphere (r = 1 + 0.5·v) with derived truths: 1/r, volume, area, centroid of the samples."""
    s = sphere_points(variant, n=600)
    r = s["truth"]["radius"]
    return {"value": s["value"], "aux": {},
            "truth": dict(s["truth"], cx=float(s["value"][:, 0].mean()), inv_radius=1.0 / r,
                          volume=4 / 3 * np.pi * r ** 3, area=4 * np.pi * r ** 2)}


def t3_sphere_outliers(variant):
    """Sphere scan (0.3 % noise) plus 40 stray points in a box around it; truth = radius."""
    s = sphere_points(variant, n=600)
    g = rng(variant, 30)
    c = np.asarray(s["truth"]["center"])
    out = c + g.uniform(-2.5, 2.5, (40, 3)) * (1 + 0.5 * variant)
    pts = np.vstack([s["value"] + 0.003 * g.standard_normal(s["value"].shape), out])
    return {"value": pts, "aux": {}, "truth": dict(s["truth"])}


def t3_plane_outliers(variant):
    """Plane z = a·x + 0.5 (a = 0.15 + 0.25·v) with 120 clutter points (19 %); truth = |normal_z|."""
    g = rng(variant, 31)
    n = 500
    xy = g.uniform(-1, 1, (n, 2))
    a = 0.15 + 0.25 * variant
    z = a * xy[:, 0] + 0.5 + 0.002 * g.standard_normal(n)
    pts = np.column_stack([xy, z])
    out = np.column_stack([g.uniform(-1, 1, (120, 2)), g.uniform(-1, 2, 120)])
    return {"value": np.vstack([pts, out]), "aux": {},
            "truth": {"normal_z": float(1.0 / np.sqrt(a * a + 1.0)), "tilt_deg": float(np.degrees(np.arctan(a)))}}


def t3_cylinder(variant):
    """Points on a cylinder of radius 0.5 + 0.25·v, axis z, height 2, 0.2 % noise; truth = radius."""
    g = rng(variant, 32)
    r = 0.5 + 0.25 * variant
    n = 800
    th = g.uniform(0, 2 * np.pi, n)
    z = g.uniform(-1, 1, n)
    pts = np.column_stack([r * np.cos(th), r * np.sin(th), z]) + 0.002 * g.standard_normal((n, 3))
    return {"value": pts, "aux": {}, "truth": {"radius": r}}


def t3_rigid_pair(variant):
    """Scan ``src`` and the same scan moved by R_z(6 + 4·v deg) and t = (0.05 + 0.05·v, -0.03, 0.02)."""
    g = rng(variant, 33)
    src = _blob_shape(g, 900)
    ang = 6.0 + 4.0 * variant
    R = _rot_z(ang)
    t = np.array([0.05 + 0.05 * variant, -0.03, 0.02])
    dst = src @ R.T + t
    return {"value": src, "aux": {"dst": dst},
            "truth": {"tx": float(t[0]), "ty": float(t[1]), "angle_deg": ang, "r10": float(R[1, 0])}}


def t3_pnp(variant):
    """30 model points, their exact (u = col, v = row) projections under K and pose (R_z, t_z = 3 + v)."""
    g = rng(variant, 35)
    P = g.uniform(-0.5, 0.5, (30, 3))
    R = _rot_z(10.0 + 15.0 * variant)
    t = np.array([0.1, -0.05, 3.0 + 1.0 * variant])
    K = np.array([[500.0, 0, 320.0], [0, 500.0, 240.0], [0, 0, 1.0]])
    x = (P @ R.T + t) @ K.T
    uv = x[:, :2] / x[:, 2:3]
    return {"value": P, "aux": {"uv": uv, "K": K}, "truth": {"tz": float(t[2]), "r10": float(R[1, 0])}}


def t3_rigid_pair_nominal(variant):
    """``t3_rigid_pair`` plus the part's nominal pose (identity): the pose error to it is the applied motion."""
    s = t3_rigid_pair(variant)
    ang = s["truth"]["angle_deg"]
    t = np.array([s["truth"]["tx"], s["truth"]["ty"], 0.02])
    s["aux"]["nominal"] = (np.eye(3), np.zeros(3))
    s["truth"].update({"t_norm": float(np.linalg.norm(t)), "angle_deg": ang})
    return s


def t3_pnp_nominal(variant):
    """``t3_pnp`` plus the camera's nominal pose as a 4 x 4 identity (no rotation, object at the optical centre)."""
    s = t3_pnp(variant)
    ang = 10.0 + 15.0 * variant
    t = np.array([0.1, -0.05, 3.0 + 1.0 * variant])
    s["aux"]["nominal"] = np.eye(4)
    s["truth"].update({"angle_deg": ang, "t_norm": float(np.linalg.norm(t))})
    return s


def t3_sun_day(variant):
    """UNIX times (UTC) every 5 min over the March equinox day 2024-03-20, for Tokyo / Sydney.

    Truth: at the equinox the declination is ~0 (|delta| < 0.02 deg at either site's solar noon that day), so
    the day's highest true (unrefracted) sun elevation is 90 - |latitude|; the equation of time on 20 March is
    about -7.3 min (sundial behind the clock)."""
    t0 = 1710892800.0                                   # 2024-03-20T00:00:00Z
    lat, lon = (35.68, 139.77) if variant == 0 else (-33.87, 151.21)
    t = t0 + np.arange(0.0, 86400.0, 300.0)
    return {"value": t, "aux": {"lat": lat, "lon": lon}, "truth": {"el_max": 90.0 - abs(lat)}}


def t3_circle3d(variant):
    """3-D ring of radius R = 20 + 10·v mm, fronto-parallel at Z = 500 mm; truth = image radius f·R/Z px."""
    R = 20.0 + 10.0 * variant
    th = np.linspace(0, 2 * np.pi, 60, endpoint=False)
    P = np.column_stack([5 + R * np.cos(th), -3 + R * np.sin(th), np.full_like(th, 500.0)])
    cam = {"fx": 800.0, "fy": 800.0, "cx": 320.0, "cy": 240.0}
    return {"value": P, "aux": {"cam": cam}, "truth": {"r_px": 800.0 * R / 500.0}}


def t3_print_ball(variant):
    """Scanned ball of radius 10·(1 + 0.5·v) mm resting on the print bed (centre z = r)."""
    r = 10.0 * (1 + 0.5 * variant)
    g = rng(variant, 38)
    u = g.standard_normal((1500, 3))
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    return {"value": u * r + [0, 0, r], "aux": {"z": r},
            "truth": {"bead_volume": 2 * np.pi * r * 0.4 * 0.2, "radius": r}}


def t3_cube_corners(variant):
    """8 corners of a 2-unit CAD cube centred at Z0 = 6 + 2·v in front of a pinhole camera; truth = front face Z."""
    z0 = 6.0 + 2.0 * variant
    c = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], float) + [0, 0, z0]
    K = np.array([[60.0, 0, 31.5], [0, 60.0, 31.5], [0, 0, 1.0]])
    return {"value": c, "aux": {"K": K, "R": np.eye(3), "t": np.zeros(3),
                                "px": np.array([[31.5, 31.5], [35.0, 28.0]])},
            "truth": {"front": z0 - 1.0}}


# ---- samples (depth / images) ----------------------------------------------------------------
def t3_plane_depth(variant, h=48, w=48):
    """Depth image of the plane Z = 3 + a·X (a = 0.2 + 0.3·v) under fx = fy = 40; truth = |normal_z|."""
    fx = fy = 40.0
    cx, cy = (w - 1) / 2, (h - 1) / 2
    a = 0.2 + 0.3 * variant
    vv, uu = np.mgrid[0:h, 0:w].astype(float)
    z = 3.0 / (1.0 - a * (uu - cx) / fx)
    return {"value": z, "aux": {"fx": fx, "fy": fy, "cx": cx, "cy": cy},
            "truth": {"normal_z": float(1.0 / np.sqrt(a * a + 1.0))}}


def t3_height_bump(variant, n=64):
    """Height map with a Gaussian bump of height 1.5 + v (sigma 10 px); truth = peak-to-valley."""
    a = 1.5 + 1.0 * variant
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    h = a * np.exp(-((yy - n / 2) ** 2 + (xx - n / 2) ** 2) / (2 * 10.0 ** 2))
    return {"value": h, "aux": {}, "truth": {"peak": float(h.max() - h.min())}}


def t3_wall_depth(variant, h=64, w=64):
    """Fronto-parallel wall at Z0 = 1.6 + 0.6·v; truth = occupied (behind-the-wall) fraction of Z in [1, 3]."""
    z0 = 1.6 + 0.6 * variant
    return {"value": np.full((h, w), z0),
            "aux": {"fx": 32.0, "fy": 32.0, "cx": (w - 1) / 2, "cy": (h - 1) / 2,
                    "bounds": [[-0.5, -0.5, 1.0], [0.5, 0.5, 3.0]]},
            "truth": {"occ": (3.0 - z0) / 2.0}}


def t3_stereo_plane(variant, n=64):
    """Rectified stereo pair of a textured fronto-parallel plane at Z0 = 1 + 0.5·v (fx 40, baseline 0.1)."""
    from scipy.ndimage import gaussian_filter, shift as ndshift
    g = rng(variant, 34)
    fx, b = 40.0, 0.1
    z0 = 1.0 + 0.5 * variant
    left = gaussian_filter(g.random((n, n + 16)), 1.0)
    right = ndshift(left, (0, -fx * b / z0), order=3, mode="nearest")
    left, right = left[:, 8:8 + n], right[:, 8:8 + n]
    left = (left - left.min()) / np.ptp(left)
    right = (right - right.min()) / np.ptp(right)
    K = np.array([[fx, 0, (n - 1) / 2], [0, fx, (n - 1) / 2], [0, 0, 1.0]])
    return {"value": left, "aux": {"right": right, "K": K, "R": np.eye(3), "t": np.array([-b, 0.0, 0.0]),
                                   "cands": list(np.linspace(0.6, 2.4, 37))},
            "truth": {"z0": z0}}


def t3_hillshade_plane(variant):
    """Common tilted DEM with the Lambert hillshade of that slope (sun az 315, alt 45; aspect 270 = west)."""
    s = tilted_plane_depth(variant)
    sl = np.radians(s["truth"]["slope_deg"])
    zen, az, asp = np.radians(45.0), np.radians(315.0), np.radians(270.0)
    hs = np.cos(zen) * np.cos(sl) + np.sin(zen) * np.sin(sl) * np.cos(az - asp)
    return {"value": s["value"], "aux": s["aux"], "truth": dict(s["truth"], hillshade=float(hs))}


def t3_cone_valley(variant, n=81, cell=10.0):
    """Conical valley DEM (grade 0.15 + 0.1·v) with a peak to the north-east; observer at the centre."""
    g = 0.15 + 0.1 * variant
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    d = np.hypot(yy - n // 2, xx - n // 2) * cell
    peak = 120.0 * (1 + variant) * np.exp(-((yy - 10) ** 2 + (xx - 52) ** 2) / (2 * 6.0 ** 2))
    return {"value": g * d + peak, "aux": {"cell": cell, "obs": [n // 2, n // 2],
                                           "K": [40.0, 40.0, 31.5, 23.5], "shape": [48, 64]},
            "truth": {"grade": g}}


def t3_plane_circle_px(variant):
    """Pixel points of a world circle (radius 8 + 4·v mm) imaged through a plane homography H; aux = H^-1."""
    R = 8.0 + 4.0 * variant
    th = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    w = np.column_stack([R * np.cos(th) + 3.0, R * np.sin(th) - 2.0, np.ones_like(th)])
    H = np.array([[12.0, 1.5, 320.0], [-0.8, 11.0, 240.0], [0.002, 0.001, 1.0]])
    p = w @ H.T
    return {"value": p[:, :2] / p[:, 2:3], "aux": {"Hinv": np.linalg.inv(H)}, "truth": {"radius": R}}


def t3_calib_views(variant):
    """Five tilted views (row, col) of a 7x7 target, 10 mm pitch, rendered with fx = fy = 800 + 100·v."""
    fx = 800.0 + 100.0 * variant
    fy, cx, cy = fx, 320.0, 240.0
    gy, gx = np.mgrid[0:7, 0:7].astype(float) * 10.0
    obj = np.column_stack([gy.ravel(), gx.ravel()])        # caltab_points order (y, x), row-major
    views = []
    for ax, ay in ((25, 0), (-25, 5), (0, 25), (10, -25), (20, 20)):
        a, b = np.radians(ax), np.radians(ay)
        Rx = np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)], [0, np.sin(a), np.cos(a)]])
        Ry = np.array([[np.cos(b), 0, np.sin(b)], [0, 1, 0], [-np.sin(b), 0, np.cos(b)]])
        P = np.column_stack([obj[:, 0] - 30, obj[:, 1] - 30, np.zeros(len(obj))]) @ (Ry @ Rx).T + [0, 0, 400.0]
        views.append(np.column_stack([fy * P[:, 1] / P[:, 2] + cy, fx * P[:, 0] / P[:, 2] + cx]))
    return {"value": None, "aux": {"views": views}, "truth": {"fx": fx}}


def t3_shift_pair(variant, n=64):
    """Smooth random texture and its cyclic sub-pixel shift (dy, dx) = (2.5 + v, -1.25 - 2v)."""
    from scipy.ndimage import gaussian_filter, shift as ndshift
    g = rng(variant, 37)
    a = gaussian_filter(g.random((n, n)), 2.0)
    a = (a - a.min()) / np.ptp(a)
    dy, dx = 2.5 + variant, -1.25 - 2 * variant
    b = ndshift(a, (dy, dx), order=3, mode="wrap")
    return {"value": a, "aux": {"moved": b}, "truth": {"reg_dy": -dy, "reg_dx": -dx}}


def t3_moving_dot_video(variant, t=16, n=32):
    """Video (T, H, W) of a Gaussian spot crossing row 16 at 1 + 0.5·v px / frame."""
    v = 1.0 + 0.5 * variant
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    frames = np.stack([np.exp(-((yy - 16) ** 2 + (xx - (4 + v * k)) ** 2) / 4.0) for k in range(t)])
    return {"value": frames, "aux": {}, "truth": {"speed": v}}


# ---- samples (volumes / CT) ------------------------------------------------------------------
def t3_ball_binary(variant, n=24):
    """Binary ball of radius 5 + 2·v voxels plus 4 isolated speckle voxels; truth = ball voxel count."""
    r = 5.0 + 2.0 * variant
    zz, yy, xx = np.mgrid[0:n, 0:n, 0:n]
    m = ((zz - n / 2) ** 2 + (yy - n / 2) ** 2 + (xx - n / 2) ** 2) <= r * r
    v = m.astype(float)
    for (z, y, x) in ((1, 1, 1), (1, 20, 3), (21, 2, 18), (3, 21, 21)):
        v[z, y, x] = 1.0
    return {"value": v, "aux": {}, "truth": {"voxels": int(m.sum())}}


def t3_label_vol(variant, n=24):
    """Label volume with 3 + v cubes (sides 3, 4, 5, ...) labelled 1..k; truth = count, largest size."""
    lab = np.zeros((n, n, n), dtype=np.int32)
    k = 3 + variant
    sizes = []
    for i in range(k):
        s = 3 + i
        z = 2 + 5 * i
        lab[z:z + s, 4:4 + s, 4 + i:4 + i + s] = i + 1
        sizes.append(s ** 3)
    return {"value": lab, "aux": {}, "truth": {"count": k, "largest": max(sizes)}}


def t3_ct_disk(variant, n=64):
    """CT slice: uniform disk (density 1) of radius 12 + 6·v px; truth = rasterised pixel area."""
    r = 12.0 + 6.0 * variant
    cy, cx = n / 2 + 4, n / 2 - 3 * variant
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    img = (((yy - cy) ** 2 + (xx - cx) ** 2) <= r * r).astype(float)
    return {"value": img, "aux": {"angles": list(np.arange(0.0, 180.0, 2.0))},
            "truth": {"area": float(img.sum())}}


def _sino_disk(variant, c, n_det=91):
    """Analytic parallel-beam sinogram (90 views, 2 deg) of a disk (r = 12 + 4·v) whose axis is off by c bins."""
    r = 12.0 + 4.0 * variant
    th = np.radians(np.arange(0.0, 180.0, 2.0))
    x0, y0 = 6.0, -4.0
    s = np.arange(n_det, dtype=float)[None, :] - (n_det - 1) / 2 - c
    p = s - (x0 * np.cos(th) + y0 * np.sin(th))[:, None]
    sino = 2.0 * np.sqrt(np.clip(r * r - p * p, 0, None))
    return {"value": sino, "aux": {"angles": list(np.degrees(th))},
            "truth": {"shift": c, "area": float(np.pi * r * r)}}


def t3_sino_offaxis(variant):
    """Sinogram with the rotation axis 2 + 2·v detector bins off centre."""
    return _sino_disk(variant, 2.0 + 2.0 * variant)


def t3_sino_centred(variant):
    """Sinogram with a centred rotation axis (for the ring-artefact recipe)."""
    return _sino_disk(variant, 0.0)


def t3_ball_chord(variant):
    """Common grey ``volume_ball`` (r = 5 + 2·v); truth adds the voxel chord through the centre, 2r + 1."""
    from fullseye.recipebook.common import volume_ball
    s = volume_ball(variant)
    return {"value": s["value"], "aux": {}, "truth": dict(s["truth"], chord=2 * (5.0 + 2.0 * variant) + 1)}


def t3_ball_area(variant):
    """Common grey ``volume_ball`` with the analytic sphere area 4·pi·r^2 (r = 5 + 2·v voxels)."""
    from fullseye.recipebook.common import volume_ball
    s = volume_ball(variant)
    return {"value": s["value"], "aux": {}, "truth": dict(s["truth"], area_true=4 * np.pi * (5.0 + 2.0 * variant) ** 2)}


def t3_beat_aux(variant):
    """Parameters for the beating-shell generator (radius 5 + 1.5·v voxels, period 8 frames)."""
    return {"value": None, "aux": {"radius": 5.0 + 1.5 * variant, "period": 8.0}, "truth": {}}


SAMPLES = {
    "t3_sphere": t3_sphere, "t3_sphere_outliers": t3_sphere_outliers, "t3_plane_outliers": t3_plane_outliers,
    "t3_cylinder": t3_cylinder, "t3_rigid_pair": t3_rigid_pair, "t3_pnp": t3_pnp, "t3_circle3d": t3_circle3d,
    "t3_print_ball": t3_print_ball, "t3_cube_corners": t3_cube_corners, "t3_plane_depth": t3_plane_depth,
    "t3_height_bump": t3_height_bump, "t3_wall_depth": t3_wall_depth, "t3_stereo_plane": t3_stereo_plane,
    "t3_hillshade_plane": t3_hillshade_plane, "t3_cone_valley": t3_cone_valley,
    "t3_plane_circle_px": t3_plane_circle_px, "t3_calib_views": t3_calib_views, "t3_shift_pair": t3_shift_pair,
    "t3_moving_dot_video": t3_moving_dot_video, "t3_ball_binary": t3_ball_binary, "t3_label_vol": t3_label_vol,
    "t3_ct_disk": t3_ct_disk, "t3_sino_offaxis": t3_sino_offaxis, "t3_sino_centred": t3_sino_centred,
    "t3_beat_aux": t3_beat_aux, "t3_ball_chord": t3_ball_chord, "t3_ball_area": t3_ball_area,
    "t3_rigid_pair_nominal": t3_rigid_pair_nominal, "t3_pnp_nominal": t3_pnp_nominal, "t3_sun_day": t3_sun_day,
}

_3D = dict(family="3d", task="measure", task_class="3d")

RECIPES = [
    # ---- 3d: point-cloud preprocessing + primitive fitting (HALCON 3D Object Model) ----------
    dict(_3D, name="3D — radius of a ball from a noisy scan with stray points",
         halcon="3D Object Model", input_sort="points", sample="t3_sphere_outliers",
         stages=[{"op": "voxel_grid_downsample", "kw": {"voxel_size": 0.04}},
                 {"op": "ransac_sphere", "kw": {"thresh": 0.02, "iters": 300}}],
         expect=[{"get": [0, "radius"], "approx": "radius", "rtol": 0.01}],
         note="Measure a spherical part (ball, bearing, probe tip) from a 3-D scan that also caught stray points: "
              "voxel-grid downsampling evens out the density (voxel 0.04 units), then RANSAC sphere fitting "
              "(inlier band 0.02) ignores the outliers. Output: centre and radius in the scan's units."),
    dict(_3D, name="3D — ball radius by least squares after statistical outlier removal",
         halcon="3D Object Model", input_sort="points", sample="t3_sphere_outliers",
         stages=[{"op": "statistical_outlier_removal", "kw": {"k": 16, "std_ratio": 2.0}},
                 {"op": "fit_sphere_3d"}],
         expect=[{"get": [1], "approx": "radius", "rtol": 0.015}],
         note="Clean a scan before a plain (non-robust) least-squares fit: statistical outlier removal drops "
              "points whose mean distance to their 16 neighbours is beyond mean + 2 std, then the algebraic "
              "sphere fit gives (centre, radius). Without the cleaning the 40 stray points bias the radius by "
              "~15 %; after it the error is ~1 %."),
    dict(_3D, name="3D — tilt of a flat face (RANSAC plane) despite clutter",
         halcon="3D Object Model", input_sort="points", sample="t3_plane_outliers",
         stages=[{"op": "ransac_plane", "kw": {"thresh": 0.01, "iters": 300}}],
         expect=[{"get": [0, "normal", 2, "@abs"], "approx": "normal_z", "atol": 0.003}],
         note="Find the dominant flat face in a point cloud with 19 % clutter and read its unit normal (tilt "
              "against the z axis = acos|n_z|). Single stage: the robust plane fit is the whole task; feed its "
              "inlier mask to segmentation or its normal to an angle check."),
    dict(_3D, name="3D — pipe radius from a cylinder scan (normals + RANSAC cylinder)",
         halcon="3D Object Model", input_sort="points", sample="t3_cylinder",
         stages=[{"op": "estimate_point_normals", "kw": {"k": 16}},
                 {"op": "ransac_cylinder", "args": ["$in", "$prev"], "kw": {"thresh": 0.01, "iters": 300}}],
         expect=[{"get": [0, "radius"], "approx": "radius", "rtol": 0.01}],
         note="Measure the radius and axis of a pipe, shaft or bore from its point cloud: PCA normals from 16 "
              "neighbours, then RANSAC cylinder (axis from normal cross products). Radius in scan units."),
    dict(_3D, name="3D — mean curvature of a ball surface as a summary table", family="reprconv",
         task="measure", task_class="3d", halcon="3D Object Model", input_sort="points", sample="t3_sphere",
         stages=[{"op": "principal_curvatures", "kw": {"k": 25}}, {"op": "curvature_to_table"}],
         expect=[{"get": ["mean_curvature_mean"], "approx": "inv_radius", "rtol": 0.06}],
         note="Surface curvature of a scanned part summarised as one table (min / max / percentiles / mean "
              "curvature): per-point principal curvatures from a local quadric (k = 25), then the curvature -> table "
              "conversion. For a sphere the mean curvature is 1/r (1/length units); ~3 % bias from 600 points."),
    dict(_3D, name="3D — centre of a scanned part (centroid position)", family="reprconv", task="measure",
         task_class="3d", halcon="3D Object Model", input_sort="points", sample="t3_sphere",
         stages=[{"op": "voxel_grid_downsample", "kw": {"voxel_size": 0.05}}, {"op": "points_to_position"}],
         expect=[{"get": [0], "approx": "cx", "atol": 0.01}],
         note="Reduce a point cloud to one position (its centroid) for pick-and-place or tracking: voxel "
              "downsample (0.05) so dense patches do not dominate, then points -> position. Note the op names the "
              "axes (z, y, x) but it simply averages the three columns in input order."),
    dict(_3D, name="3D — enclosed volume of a scanned ball (convex hull mesh)",
         halcon="3D Object Model", input_sort="points", sample="t3_sphere",
         stages=[{"op": "convex_hull"}, {"op": "mesh_volume"}],
         expect=[{"get": [], "approx": "volume", "rtol": 0.035}],
         note="Volume of a convex part from its surface points: convex hull -> outward-wound triangle mesh -> "
              "divergence-theorem volume (units^3). The inscribed polyhedron of 600 points is ~2 % smaller than "
              "the true sphere, hence the 3.5 % gate."),
    dict(_3D, name="3D — surface area of a scanned ball (convex hull mesh)",
         halcon="3D Object Model", input_sort="points", sample="t3_sphere",
         stages=[{"op": "convex_hull"}, {"op": "mesh_area"}],
         expect=[{"get": [], "approx": "area", "rtol": 0.025}],
         note="Surface area of a convex scanned part (coating, plating, painting estimates): convex hull mesh, "
              "then the sum of triangle areas (units^2); ~1 % below 4·pi·r^2 for 600 points."),
    # ---- 3d: registration / pose (HALCON 3D Matching) ---------------------------------------
    dict(_3D, name="3D — align a scan to its reference (ICP rigid transform)",
         halcon="3D Matching", input_sort="points", sample="t3_rigid_pair",
         stages=[{"op": "voxel_grid_downsample", "kw": {"voxel_size": 0.03}},
                 {"op": "icp_point2point_3d", "args": ["$prev", "$aux.dst"], "kw": {"iters": 60}}],
         expect=[{"get": [1, 0], "approx": "tx", "atol": 0.01}],
         note="Recover the rigid transform (R, t) that moves a measured scan onto its reference model (small "
              "initial misalignment, here 6-10 deg and 0.05-0.1 units): voxel downsample the moving scan, then "
              "point-to-point ICP (Kabsch). Output (R, t, ...) with dst ≈ src·Rᵀ + t."),
    dict(_3D, name="3D — align a scan to its reference with point-to-plane ICP",
         halcon="3D Matching", input_sort="points", sample="t3_rigid_pair",
         stages=[{"op": "estimate_point_normals", "args": ["$aux.dst"], "kw": {"k": 16}},
                 {"op": "icp_point2plane", "args": ["$in", "$aux.dst", "$prev"], "kw": {"iters": 30}}],
         expect=[{"get": [1, 0], "approx": "tx", "atol": 1e-4}, {"get": [0, 1, 0], "approx": "r10", "atol": 1e-4}],
         note="Fine registration that converges in a few iterations on smooth parts: normals of the reference "
              "scan (k = 16), then point-to-plane ICP of the moving scan onto it. Recovers the known rotation "
              "and translation to 1e-4."),
    dict(_3D, name="3D — register two scans with generalized ICP (plane-to-plane)",
         halcon="3D Matching", input_sort="points", sample="t3_rigid_pair",
         stages=[{"op": "voxel_grid_downsample", "kw": {"voxel_size": 0.03}},
                 {"op": "gicp", "args": ["$prev", "$aux.dst"], "kw": {"max_iter": 30, "k": 20}}],
         expect=[{"get": [1, 0], "approx": "tx", "atol": 1e-3}, {"get": [0, 1, 0], "approx": "r10", "atol": 1e-3}],
         note="Generalized-ICP registration (covariance-weighted, robust on planar and noisy scans) of a "
              "downsampled moving scan onto its reference; returns the rigid transform (R, t) with "
              "dst ≈ src·Rᵀ + t. Needs a near initial alignment (here 6-10 deg)."),
    dict(_3D, name="3D — object pose from known 3-D points and their image (PnP)",
         halcon="3D Matching", input_sort="points", sample="t3_pnp",
         stages=[{"op": "dlt_pose", "args": ["$in", "$aux.uv"], "kw": {"K": "$aux.K"}}],
         expect=[{"get": [1, 2], "approx": "tz", "atol": 1e-6}, {"get": [0, 1, 0], "approx": "r10", "atol": 1e-6}],
         note="Camera-to-object pose (R, t, Xc = R·X + t) from model points and their pixel positions (u = col, "
              "v = row) with known intrinsics K: normalised DLT + LM refinement. Single stage: projecting with "
              "project_3d_point first gives (row, col) and silently mirrors the pose (see FAILED_ATTEMPTS)."),
    dict(_3D, name="3D — how far a part sits from its nominal pose (point-to-plane ICP -> pose error)",
         halcon="3D Matching", input_sort="points", sample="t3_rigid_pair_nominal",
         stages=[{"op": "estimate_point_normals", "args": ["$aux.dst"], "kw": {"k": 16}},
                 {"op": "icp_point2plane", "args": ["$in", "$aux.dst", "$prev"], "kw": {"iters": 30}},
                 {"op": "pose_error", "args": ["$prev", "$aux.nominal"]}],
         expect=[{"get": ["rotation_deg"], "approx": "angle_deg", "atol": 1e-3},
                 {"get": ["translation"], "approx": "t_norm", "atol": 1e-3}],
         note="Placement check of a fixtured part: register the measured scan onto the reference (point-to-plane "
              "ICP), then compare the recovered pose (R, t) with the nominal pose — rotation error in degrees "
              "(geodesic angle of R_estᵀ·R_nominal) and translation error |t_est − t_nominal| in scan units. "
              "The nominal pose is the identity, so the error is the applied motion (6 / 10 deg, ~0.06 / 0.1)."),
    dict(_3D, name="3D — camera pose deviation from its nominal mounting (PnP -> RRE / RTE)",
         halcon="3D Matching", input_sort="points", sample="t3_pnp_nominal",
         stages=[{"op": "dlt_pose", "args": ["$in", "$aux.uv"], "kw": {"K": "$aux.K"}},
                 {"op": "rotation_translation_error", "args": ["$aux.nominal", "$prev"]}],
         expect=[{"get": ["rre_deg"], "approx": "angle_deg", "atol": 1e-6},
                 {"get": ["rte"], "approx": "t_norm", "atol": 1e-6}],
         note="Registration-benchmark error measures (RRE = relative rotation error in degrees, RTE = relative "
              "translation error) between a nominal pose and the pose solved by PnP from model points and their "
              "pixels (u = col, v = row). The nominal side is a 4 x 4 transform and the estimate a (R, t) pose: "
              "the ledger door takes either. Identity nominal, so RRE / RTE are the true rotation / |t|."),
    # ---- 3d: depth / reconstruction (HALCON 3D Reconstruction) ------------------------------
    dict(_3D, name="3D — plane tilt from a depth camera image",
         halcon="3D Reconstruction", input_sort="depth", sample="t3_plane_depth",
         stages=[{"op": "depth_to_points", "kw": {"fx": "$aux.fx", "fy": "$aux.fy", "cx": "$aux.cx", "cy": "$aux.cy"}},
                 {"op": "ransac_plane", "kw": {"thresh": 0.005, "iters": 200}}],
         expect=[{"get": [0, "normal", 2, "@abs"], "approx": "normal_z", "atol": 0.002}],
         note="Orientation of a table, wall or part face seen by an RGB-D / ToF camera: back-project the depth "
              "image with the pinhole intrinsics (fx, fy, cx, cy in px) to an (X, Y, Z) cloud, then RANSAC plane "
              "-> unit normal."),
    dict(_3D, name="3D — height of a bump by phase-shift structured light",
         halcon="3D Reconstruction", input_sort="image", sample="t3_height_bump",
         stages=[{"op": "synthesize_fringes", "kw": {"n_steps": 4, "freq": 0.0, "phase_gain": 2.0}},
                 {"op": "decode_fringe", "kw": {"k": 0.5}}],
         expect=[{"get": ["@ptp"], "approx": "peak", "rtol": 0.01}],
         note="Fringe-projection profilometry end to end: render 4-step phase-shifted fringe images of a known "
              "height map (phase gain 2 rad / unit, so the bump wraps), then wrapped phase -> unwrap -> height "
              "with k = 1 / gain. Peak-to-valley height in height units."),
    dict(_3D, name="3D — fuse a depth image into a TSDF volume and read occupancy",
         halcon="3D Reconstruction", input_sort="depth", sample="t3_wall_depth",
         stages=[{"op": "tsdf_from_depth", "kw": {"fx": "$aux.fx", "fy": "$aux.fy", "cx": "$aux.cx", "cy": "$aux.cy",
                                                  "size": 32, "bounds": "$aux.bounds", "trunc": 0.2}},
                 {"op": "sdf_to_occupancy", "kw": {"iso": 0.0}}],
         expect=[{"get": ["@mean"], "approx": "occ", "atol": 0.04}],
         note="KinectFusion-style volumetric integration: depth image -> truncated signed distance volume "
              "(32^3 voxels, truncation 0.2 units) -> occupancy (behind the surface = 1). The occupied fraction "
              "of the box equals the depth range behind the wall (one-view TSDF fills the far side)."),
    dict(_3D, name="3D — depth of a surface from a calibrated stereo pair (plane sweep)",
         halcon="3D Reconstruction", input_sort="image", sample="t3_stereo_plane",
         stages=[{"op": "plane_sweep_depth", "args": ["$in", "$aux.right"],
                  "kw": {"K": "$aux.K", "R": "$aux.R", "t": "$aux.t", "depth_candidates": "$aux.cands", "window": 3}}],
         expect=[{"get": ["@median"], "approx": "z0", "rtol": 0.03}],
         note="Multi-view stereo by plane sweeping: warp the second image through fronto-parallel planes at "
              "candidate depths (0.6-2.4, step 0.05) with known K, R, t, keep the best photo-consistency per "
              "pixel (3x3 window). Output depth map in the baseline's units."),
    # ---- 3d: volumes ------------------------------------------------------------------------
    dict(_3D, name="3D — voxel count of an inclusion after removing speckle",
         halcon="3D Object Model", input_sort="voxel", sample="t3_ball_binary",
         stages=[{"op": "filter_by_volume", "kw": {"min_voxels": 10}}, {"op": "region_props"}],
         expect=[{"get": [0, "volume"], "equals": "voxels"}, {"get": ["@len"], "equals": 1}],
         note="Size of a pore, void or inclusion in a segmented CT volume: drop connected components under 10 "
              "voxels (single-voxel speckle), then per-component region properties (volume in voxels, centroid, "
              "bbox, equivalent radius, sphericity). Exactly one component and its exact voxel count remain."),
    dict(_3D, name="3D — volume of a CT inclusion from its marching-cubes surface",
         halcon="3D Object Model", input_sort="voxel", sample="volume_ball",
         stages=[{"op": "voxel_to_mesh", "kw": {"iso": 0.5}}, {"op": "mesh_volume"}],
         expect=[{"get": ["@abs"], "approx": "voxels", "rtol": 0.03}],
         note="Iso-surface the grey volume at 0.5 (marching cubes) and take the enclosed volume of the mesh "
              "(voxel^3). Marching-cubes faces wind inward, so the signed volume is negative — read its "
              "magnitude; it lands within ~2 % of the voxel count of the inclusion."),
    dict(_3D, name="3D — surface area of a CT inclusion (marching cubes + Taubin smoothing)",
         halcon="3D Object Model", input_sort="voxel", sample="t3_ball_area",
         stages=[{"op": "voxel_to_mesh", "kw": {"iso": 0.5}}, {"op": "taubin_smooth", "kw": {"iters": 10}},
                 {"op": "mesh_area"}],
         expect=[{"get": [], "approx": "area_true", "rtol": 0.03}],
         note="Surface area of a void / inclusion from a CT volume: marching cubes at iso 0.5, Taubin smoothing "
              "(10 iterations, volume-preserving) to remove the staircase, then the triangle-area sum "
              "(voxel^2); ~2 % above 4·pi·r^2."),
    dict(_3D, name="3D — label the objects in a CT volume and read their voxel counts",
         halcon="3D Object Model", input_sort="voxel", sample="volume_ball",
         stages=[{"op": "vol_label", "kw": {"connectivity": 26}}, {"op": "vol_region_props"}],
         expect=[{"get": [0, "voxel_count"], "equals": "voxels"}, {"get": ["@len"], "equals": 1}],
         note="Connected-component labelling of a grey CT volume (threshold 0.5, 26-connectivity) followed by "
              "per-component descriptors (voxel count, volume, centroid, bbox, surface area, sphericity)."),
    dict(_3D, name="Inspect — diameter of a dense inclusion along a probe line (CT volume)",
         halcon="3D Object Model", input_sort="voxel", sample="t3_ball_chord",
         stages=[{"op": "vol_window_level", "kw": {"center": 0.5, "width": 1.0}},
                 {"op": "vol_wall_thickness", "kw": {"p0": [12.0, 12.0, 0.0], "p1": [12.0, 12.0, 23.0]}}],
         expect=[{"get": [0], "approx": "chord", "atol": 0.3}],
         note="Caliper-style thickness along a line through a CT volume: window/level to [0, 1], then the "
              "edge-to-edge distance of each bright run along the probe (voxels). A ball of radius r occupies "
              "2r + 1 voxels on its centre line."),
    # ---- dem ----------------------------------------------------------------------------------
    dict(name="DEM — slope of a hillside after filling sinks", family="dem", task="measure",
         task_class="measurement", halcon=None, input_sort="depth", sample="tilted_plane_depth",
         stages=[{"op": "dem_fill_sinks"}, {"op": "dem_slope", "kw": {"cell_size": "$aux.cell_size"}}],
         expect=[{"get": ["@median"], "approx": "slope_deg", "atol": 0.05}],
         note="Terrain / heightmap slope in degrees: fill depressions (hydrologically correct DEM, a no-op on a "
              "clean plane) then Horn 3x3 slope with the cell size in metres; median over the map."),
    dict(name="DEM — hillshade of a tilted terrain", family="dem", task="visualize",
         task_class="visualization", halcon=None, input_sort="depth", sample="t3_hillshade_plane",
         stages=[{"op": "dem_hillshade", "kw": {"cell_size": "$aux.cell_size"}}],
         expect=[{"get": ["@median"], "approx": "hillshade", "atol": 0.005}],
         note="Shaded relief of a height map (sun azimuth 315 deg, altitude 45 deg, Lambert cosine law, no cast "
              "shadows), value 0..1. Single stage: it is the end product for maps and terrain inspection."),
    # ---- tomography -------------------------------------------------------------------------
    dict(name="CT — reconstruct a disk phantom and measure its area", family="tomography", task="measure",
         task_class="measurement", halcon=None, input_sort="image", sample="t3_ct_disk",
         stages=[{"op": "radon_transform", "kw": {"angles_deg": "$aux.angles"}},
                 {"op": "filtered_backprojection", "kw": {"angles_deg": "$aux.angles", "size": 64}},
                 {"op": "otsu", "a": 0.5, "b": 0.5}],
         expect=[{"get": ["@sum"], "approx": "area", "rtol": 0.03}],
         note="Simulated CT inspection: parallel-beam projection of a slice (90 views over 180 deg), filtered "
              "back-projection (ramp), Otsu segmentation; the segmented area in pixels matches the phantom disk."),
    dict(name="CT — find the rotation-axis offset of a scanner", family="tomography", task="calibrate",
         task_class="measurement", halcon=None, input_sort="sinogram", sample="t3_sino_offaxis",
         stages=[{"op": "sinogram_center_of_rotation", "kw": {"angles_deg": "$aux.angles"}}],
         expect=[{"get": [], "approx": "shift", "atol": 0.05}],
         note="CT geometry calibration: offset of the rotation axis from the detector centre in detector bins, "
              "from the centre-of-mass sinusoid of the projections (no reconstruction needed). Single stage: the "
              "next recipe applies the correction."),
    dict(name="CT — correct an off-centre axis, reconstruct and measure", family="tomography", task="measure",
         task_class="measurement", halcon=None, input_sort="sinogram", sample="t3_sino_offaxis",
         stages=[{"op": "sinogram_center_shift", "kw": {"angles_deg": "$aux.angles"}},
                 {"op": "filtered_backprojection", "kw": {"angles_deg": "$aux.angles", "size": 64}},
                 {"op": "otsu", "a": 0.5, "b": 0.5}],
         expect=[{"get": ["@sum"], "approx": "area", "rtol": 0.04}],
         note="Re-centre a sinogram whose rotation axis is 2-4 bins off (measured automatically), reconstruct "
              "by FBP and segment; without the shift the disk smears into a ring. Area in px vs pi·r^2."),
    dict(name="CT — suppress ring artefacts from a bad detector, then measure", family="tomography",
         task="restore", task_class="preprocess", halcon=None, input_sort="sinogram", sample="t3_sino_centred",
         stages=[{"op": "ring_artifact_apply", "kw": {"gain_sigma": 0.05, "seed": 3}},
                 {"op": "ring_artifact_remove", "kw": {"window": 5}},
                 {"op": "filtered_backprojection", "kw": {"angles_deg": "$aux.angles", "size": 64}},
                 {"op": "otsu", "a": 0.5, "b": 0.5}],
         expect=[{"get": ["@sum"], "approx": "area", "rtol": 0.04}],
         note="Ring-artefact correction: simulate a 5 % per-bin detector gain error, flatten the angle-averaged "
              "detector profile (median window 5 bins), reconstruct and segment; the part area survives."),
    # ---- calib / fit --------------------------------------------------------------------------
    dict(name="Calibrate — camera focal length from views of a planar target", family="calib",
         task="calibrate", task_class="measurement", halcon="Calibration", input_sort=None, sample="t3_calib_views",
         stages=[{"op": "caltab_points", "kw": {"rows": 7, "cols": 7, "spacing": 10.0}},
                 {"op": "camera_calibration", "kw": {"image_points_list": "$aux.views"}}],
         expect=[{"get": ["fx"], "approx": "fx", "rtol": 0.005}, {"get": ["reproj_rms", "@max"], "between": [0.0, 1e-6]}],
         note="Zhang intrinsic calibration: ideal mark coordinates of a 7x7 calibration plate (10 mm pitch) and "
              "five tilted views of it (row, col px) -> K (fx, fy, cx, cy, skew) with the per-view homography "
              "reprojection RMS (~0 px on exact synthetic views)."),
    dict(name="Measure — circle on a plane in millimetres from pixels (homography)", family="calib",
         task="measure", task_class="measurement", halcon="Calibration", input_sort="keypoints",
         sample="t3_plane_circle_px",
         stages=[{"op": "image_to_world_plane", "kw": {"homography": "$aux.Hinv"}}, {"op": "fit_circle_geometric"}],
         expect=[{"get": ["r"], "approx": "radius", "rtol": 1e-6}],
         note="Metric measurement on a calibrated plane: map edge pixels through the image->world plane "
              "homography (perspective removed) and fit a geometric circle; the radius comes out in mm."),
    dict(name="Measure — image radius of a 3-D ring seen by a camera", family="fit", task="measure",
         task_class="measurement", halcon="2D Metrology", input_sort="points", sample="t3_circle3d",
         stages=[{"op": "project_3d_point", "kw": {"cam_par": "$aux.cam"}}, {"op": "fit_circle_geometric"}],
         expect=[{"get": ["r"], "approx": "r_px", "rtol": 1e-6}],
         note="Predict how large a round feature appears in the image: project 3-D rim points through the "
              "pinhole camera (fx = 800 px) to (row, col), then geometric least-squares circle fit; radius = "
              "f·R/Z px for a fronto-parallel ring."),
    dict(name="Measure — sub-pixel shift between two images (phase correlation)", family="fit",
         task="register", task_class="measurement", halcon="Matching", input_sort="image", sample="t3_shift_pair",
         stages=[{"op": "phase_correlation_shift", "args": ["$in", "$aux.moved"]}],
         expect=[{"get": ["dy"], "approx": "reg_dy", "atol": 0.15}, {"get": ["dx"], "approx": "reg_dx", "atol": 0.15}],
         note="Translation registration of two images (drift, vibration, stitching) by whitened phase "
              "correlation with upsampled peak refinement; returns the (dy, dx) px that re-aligns the second "
              "image (= minus the applied shift). Measured error here ~0.1 px (Hann window on a cyclic shift)."),
    # ---- fileio -------------------------------------------------------------------------------
    dict(name="3D — save a scan as XYZ text, reload it and re-measure the ball", family="fileio",
         task="exchange", task_class="3d", halcon="3D Object Model", input_sort="points", sample="t3_sphere",
         stages=[{"op": "points_write_xyz"}, {"op": "points_read_xyz"},
                 {"op": "ransac_sphere", "kw": {"thresh": 0.01, "iters": 300}}],
         expect=[{"get": [0, "radius"], "approx": "radius", "rtol": 1e-6}],
         note="Point-cloud exchange round trip: write the scan as plain 'x y z' text (17 significant digits, "
              "lossless for float64), read it back, and check that the measurement survives (RANSAC sphere "
              "radius equals the true radius). The ops work on text in memory; write the text to any .xyz file."),
    dict(name="3D — export a part mesh as OBJ, re-import it and check its volume", family="fileio",
         task="exchange", task_class="3d", halcon="3D Object Model", input_sort="points", sample="t3_sphere",
         stages=[{"op": "convex_hull"}, {"op": "mesh_write_obj"}, {"op": "mesh_read_obj"}, {"op": "mesh_volume"}],
         expect=[{"get": [], "approx": "volume", "rtol": 0.035}],
         note="Mesh exchange round trip for CAD / slicer / viewer hand-off: convex-hull mesh of a scanned ball, "
              "Wavefront OBJ text out (v / vn / f), OBJ back in (geometry only), then the enclosed volume "
              "(units^3) — the re-imported mesh keeps its outward winding, so the volume stays positive."),
    # ---- printpath ----------------------------------------------------------------------------
    dict(name="Print — filament volume for the equator layer of a scanned ball", family="printpath",
         task="plan", task_class="simulation", halcon=None, input_sort="points", sample="t3_print_ball",
         stages=[{"op": "convex_hull"}, {"op": "mesh_slice_contours", "kw": {"z": "$aux.z"}},
                 {"op": "contours_to_gcode", "kw": {"z": "$aux.z"}}, {"op": "gcode_extrusion_volume"}],
         expect=[{"get": [], "approx": "bead_volume", "rtol": 0.02}],
         note="Scan-to-print: convex-hull mesh of a scanned part (mm), slice it at the equator, turn the contour "
              "into a perimeter G-code path (0.4 mm line, 0.2 mm layer, 1.75 mm filament) and total the extruded "
              "volume in mm^3 (= perimeter x width x layer height)."),
    # ---- cadmap -------------------------------------------------------------------------------
    dict(name="Inspect — map a camera pixel onto the CAD surface (depth of the hit)", family="cadmap",
         task="inspect", task_class="inspection", halcon="3D Object Model", input_sort="points",
         sample="t3_cube_corners",
         stages=[{"op": "convex_hull"},
                 {"op": "cad_pixel_to_surface", "args": ["$prev", "$aux.px"],
                  "kw": {"K": "$aux.K", "R": "$aux.R", "t": "$aux.t"}}],
         expect=[{"get": ["depth", 0], "approx": "front", "atol": 1e-6}],
         note="Locate an image defect on the CAD model: build the part mesh (convex hull of its corners), cast the "
              "pixel's viewing ray (K, R, t) and return the hit face id, barycentric coordinates, 3-D point and "
              "camera depth; a miss returns face -1, never the nearest face."),
    # ---- geocam -------------------------------------------------------------------------------
    dict(name="Sense — horizon line a camera sees from a DEM", family="geocam", task="simulate",
         task_class="simulation", halcon=None, input_sort="depth", sample="t3_cone_valley",
         stages=[{"op": "dem_skyline", "kw": {"cell_size": "$aux.cell", "observer_rc": "$aux.obs"}},
                 {"op": "render_skyline_view", "kw": {"K": "$aux.K", "shape": "$aux.shape", "yaw_deg": 0.0,
                                                      "pitch_deg": 0.0, "roll_deg": 0.0}},
                 {"op": "skyline_extract"}],
         expect=[],
         note="Geo-registration of an outdoor camera: skyline (horizon elevation per azimuth, earth curvature "
              "included) from a DEM at the observer, render the sky mask a north-facing camera would see, then "
              "extract the sky/terrain boundary row per column (dynamic programming) — the signal you match "
              "against a photo to solve the camera's yaw/pitch/roll."),
    # ---- volcolor -----------------------------------------------------------------------------
    dict(name="3D — per-object volume table of a labelled scan", family="volcolor", task="measure",
         task_class="3d", halcon="3D Object Model", input_sort="labels", sample="t3_label_vol",
         stages=[{"op": "vol_label_shape_stats"}],
         expect=[{"get": ["@len"], "equals": "count"}],
         note="Per-label statistics of a labelled 3-D volume (voxel count, centroid, bounding box, principal-axis "
              "shape indices) in O(N); one row per object. Single stage: label volumes come from a segmentation."),
    dict(name="3D — volume table of the objects found in a grey scan", family="volcolor", task="measure",
         task_class="3d", halcon="3D Object Model", input_sort="voxel", sample="volume_ball",
         stages=[{"op": "vol_label"}, {"op": "vol_label_shape_stats"}],
         expect=[{"get": [0, "voxel_count"], "equals": "voxels"}],
         note="From a grey CT volume straight to a per-object table: connected-component labels (threshold 0.5), "
              "then linear-time per-label statistics (voxel count, centroid, bbox, principal-axis shape)."),
    dict(name="3D — colour a labelled volume and cut an RGB slice", family="volcolor", task="visualize",
         task_class="visualization", halcon=None, input_sort="labels", sample="t3_label_vol",
         stages=[{"op": "vol_colorize_labels"}, {"op": "vol_label_slice_rgb", "kw": {"index": 8, "axis": "x"}}],
         expect=[],
         note="Colour-then-cut visualisation of a labelled volume: colour every label once in 3-D (stable "
              "colours across slices), then extract a sagittal RGB slice (x index 8) for a report figure."),
    # ---- videocube / live4d -------------------------------------------------------------------
    dict(name="Sense — slit-scan (x-t) image of a moving spot", family="videocube", task="analyze",
         task_class="analysis", halcon=None, input_sort="seq<image>", sample="t3_moving_dot_video",
         stages=[{"op": "video_cube_cut", "kw": {"plane": "xt", "position": 0.5}}],
         expect=[],
         note="Space-time slit scan: cut the video cube along one image row over time; a moving object becomes "
              "a slanted streak whose slope is its speed in px / frame (conveyor, web inspection, traffic)."),
    dict(name="Sense — beating shell: maximum-intensity projection video", family="live4d", task="visualize",
         task_class="visualization", halcon=None, input_sort=None, sample="t3_beat_aux",
         stages=[{"op": "volseq_synth_beating", "kw": {"shape": [16, 24, 24], "n_frames": 8,
                                                       "period": "$aux.period", "radius": "$aux.radius"}},
                 {"op": "volseq_mip_video", "kw": {"axis": 1}}],
         expect=[],
         note="4-D (volume time-series) preview: synthesize a beating shell (known radius law, 8 frames of "
              "16x24x24) and turn each volume into a maximum-intensity projection frame, giving a 2-D video of "
              "the 3-D motion for review."),
    dict(name="Sense — sun elevation at a site over a day", family="geocam", task="measure",
         task_class="sensing", halcon=None, input_sort="signal", sample="t3_sun_day",
         stages=[{"op": "sun_position", "kw": {"lat_deg": "$aux.lat", "lon_deg": "$aux.lon"}}],
         expect=[{"get": ["elevation_true_deg", "@max"], "approx": "el_max", "atol": 0.05},
                 {"get": ["equation_of_time_min", "@mean"], "between": [-8.0, -6.8]}],
         note="Sun azimuth / elevation (deg) for a list of UTC times at a known site (NOAA solar calculator, "
              "Meeus): the day's sun track for shading / glare prediction and for orienting a fixed camera from "
              "the sun. On the equinox the highest true elevation is 90 − |latitude| (Tokyo / Sydney) and the "
              "equation of time is about −7.3 min. The time series is the input; the site is a keyword."),
]

MISSING_OPS = [
    {"family": "3d", "need": "PPF / surface-based matching: find a CAD model's 6-DoF pose in a scene cloud "
                             "(HALCON find_surface_model)",
     "why": "no point-pair-feature or surface-model matching op exists in OP_GRAPH or docs/ops (only ICP / GICP / "
            "FPFH / SHOT / spin registration)"},
    {"family": "3d", "need": "threshold a grey voxel volume to a binary voxel volume (voxel -> voxel)",
     "why": "no explicit volume threshold op; vol_label thresholds implicitly at 0.5 (fixed), and "
            "region_props / label_components binarise with astype(bool) (every nonzero voxel is foreground)"},
    {"family": "reprconv", "need": "keypoints (row, col) <-> (u = col, v = row) swap",
     "why": "the keypoints sort carries both conventions (calib.project_3d_point returns (row, col); "
            "pnp3d.dlt_pose / pnp_ransac expect (u, v)) and no op converts between them"},
]

FAILED_ATTEMPTS = [
    {"family": "3d", "recipe": "3D — object pose from known 3-D points and their image (PnP)",
     "op": "project_3d_point -> dlt_pose",
     "error": "no exception; project_3d_point gives (row, col), dlt_pose reads (u, v) -> mirrored pose "
              "t = (-0.565, 0.61, 3.21) instead of (0.1, -0.05, 3.0)",
     "cause": "type_gap"},
    {"family": "reprconv", "recipe": "Measure — rotation angle of a part from matched 2-D points",
     "op": "vector_to_rigid -> matrix_to_angle",
     "error": "no exception; vector_to_rigid returns a 2-D homogeneous 3x3 [[c,-s,tx],[s,c,ty],[0,0,1]] while "
              "matrix_to_angle reads a rotation in axes (1, 2) (atan2(R[2,1], R[1,1])) -> 0.0 deg for a 20 deg "
              "rotation; matrix_to_rot_scale raises 'matrix: must be (2, 2); got (3, 3)'",
     "cause": "type_gap"},
]


#: 本ごとの日本語ノート(この本で足したレシピ。notes_ja.py の表と合わせて引く)。
NOTES_JA = {
    "3D — how far a part sits from its nominal pose (point-to-plane ICP -> pose error)":
        "部品の置き位置のずれ — 測った点群を基準に点対面 ICP で合わせ、求めた姿勢 (R, t) を公称の姿勢と比べて"
        "回転の誤差(度)と並進の誤差を出す。位置決め・治具の検査。",
    "3D — camera pose deviation from its nominal mounting (PnP -> RRE / RTE)":
        "カメラの取り付けのずれ — 既知の 3 次元点と画像上の位置から PnP で姿勢を解き、公称の取り付け(4×4)との"
        "相対回転誤差 RRE(度)と相対並進誤差 RTE を出す。姿勢は (R, t) でも 4×4 でも渡せる。",
    "Sense — sun elevation at a site over a day":
        "太陽の高さと方位の 1 日の動き — 場所(緯度・経度)と UTC の時刻の列から太陽の方位・仰角を出す"
        "(NOAA の太陽位置の式)。日照・まぶしさの予測、固定カメラの向きの推定に。春分の最高仰角は 90 − |緯度|。",
}
