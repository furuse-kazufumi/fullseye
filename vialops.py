"""Synthetic vial spin-stop sequences and conservative particle tracking.

The simulator is intentionally a *screening-model* rather than a CFD or optical
qualification model.  It supplies deterministic image sequences whose truth is
known, so a detection experiment can distinguish a miss from an absent particle.
"""
from __future__ import annotations

import math

import numpy as np

__all__ = ["vial_spin_stop_sequence", "track_moving_particles"]

_G = 9.80665


def _positive(value, name):
    value = float(value)
    if not np.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite positive number, got {value!r}")
    return value


def _image_shape(shape):
    if len(shape) != 2:
        raise ValueError("shape must be (height, width)")
    h, w = (int(shape[0]), int(shape[1]))
    if h < 32 or w < 24:
        raise ValueError("shape must be at least (32, 24) pixels")
    return h, w


def _draw_gaussian(image, row, col, sigma, amplitude):
    """Add a finite, clipped Gaussian point spread function in-place."""
    h, w = image.shape
    r0, r1 = max(0, int(math.floor(row - 3 * sigma))), min(h, int(math.ceil(row + 3 * sigma + 1)))
    c0, c1 = max(0, int(math.floor(col - 3 * sigma))), min(w, int(math.ceil(col + 3 * sigma + 1)))
    if r0 >= r1 or c0 >= c1:
        return
    rr, cc = np.mgrid[r0:r1, c0:c1]
    image[r0:r1, c0:c1] += amplitude * np.exp(-((rr - row) ** 2 + (cc - col) ** 2) / (2 * sigma * sigma))


def vial_spin_stop_sequence(shape=(96, 72), *, n_frames=18, frame_interval_s=0.04,
                            initial_omega_rad_s=10.0, decay_time_s=0.25,
                            vial_radius_mm=10.0, liquid_height_mm=28.0,
                            particle_diameter_um=80.0, particle_density_kg_m3=1450.0,
                            particle_contrast=0.16, illumination="back", n_particles=1,
                            n_bubbles=1, n_scratches=1, viscosity_pa_s=0.003,
                            fluid_density_kg_m3=1000.0, pixel_size_um=280.0,
                            noise_sigma=0.012, seed=0):
    """回転停止後のバイアル画像列と物体ごとの真値軌跡を作る。

    The liquid azimuthal velocity is the axisymmetric, prescribed field
    ``u_theta(r,t) = omega0 exp(-t/tau) r``; it is not a Navier--Stokes
    solution.  A particle has that in-plane advection plus its Stokes terminal
    velocity ``v_t = 2 r_p^2 (rho_p-rho_f) g / (9 mu)`` in the image-downward
    direction.  Bubbles use ``rho_p=1.2 kg/m^3`` and therefore rise.  The model
    is restricted to small Reynolds number / isolated spherical objects where
    Stokes drag is appropriate; it does not model turbulent wake, aggregation,
    meniscus forces, or wall-corrected drag.  At the cylindrical wall positions
    are reflected, which prevents a silent escape but is not a hydrodynamic wall
    model.  Refraction through glass and liquid is deliberately simplified to a
    fixed apparent contrast and Gaussian PSF in this first stage.

    ``illumination`` is ``"back"`` or ``"side"``.  A fixed ``seed`` determines
    object positions, sensor noise, and scratches.  The direct return is
    ``(frames, truth)``; ``truth`` contains a row table with object type, frame,
    projected positions, physical positions and visibility, plus angular-speed
    truth.  The ledger adapter returns only the ``video`` frames.

    Raises ``ValueError`` for nonphysical dimensions, an unknown illumination,
    or a nonintegral object count.
    """
    h, w = _image_shape(shape)
    if int(n_frames) != n_frames or int(n_frames) < 3:
        raise ValueError("n_frames must be an integer >= 3")
    n_frames = int(n_frames)
    for name, value in (("frame_interval_s", frame_interval_s), ("decay_time_s", decay_time_s),
                        ("vial_radius_mm", vial_radius_mm), ("liquid_height_mm", liquid_height_mm),
                        ("particle_diameter_um", particle_diameter_um), ("particle_density_kg_m3", particle_density_kg_m3),
                        ("viscosity_pa_s", viscosity_pa_s), ("fluid_density_kg_m3", fluid_density_kg_m3),
                        ("pixel_size_um", pixel_size_um)):
        _positive(value, name)
    if illumination not in ("back", "side"):
        raise ValueError("illumination must be 'back' or 'side'")
    if not np.isfinite(particle_contrast) or not 0.0 < float(particle_contrast) <= 1.0:
        raise ValueError("particle_contrast must be finite in (0, 1]")
    if not np.isfinite(initial_omega_rad_s) or initial_omega_rad_s < 0:
        raise ValueError("initial_omega_rad_s must be finite and >= 0")
    if not np.isfinite(noise_sigma) or noise_sigma < 0:
        raise ValueError("noise_sigma must be finite and >= 0")
    counts = []
    for name, value in (("n_particles", n_particles), ("n_bubbles", n_bubbles), ("n_scratches", n_scratches)):
        if int(value) != value or int(value) < 0:
            raise ValueError(f"{name} must be a non-negative integer")
        counts.append(int(value))
    n_particles, n_bubbles, n_scratches = counts

    rng = np.random.default_rng(seed)
    dt = float(frame_interval_s)
    px_mm = float(pixel_size_um) / 1000.0
    cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
    radius_px = min((w - 6) / 2.0, float(vial_radius_mm) / px_mm)
    liquid_top = max(3.0, cy - float(liquid_height_mm) / (2.0 * px_mm))
    liquid_bottom = min(h - 4.0, cy + float(liquid_height_mm) / (2.0 * px_mm))
    # The image plane is a cross-section through a cylindrical vial.
    yy, xx = np.mgrid[:h, :w]
    inside = ((xx - cx) / radius_px) ** 2 <= 1.0
    liquid = inside & (yy >= liquid_top) & (yy <= liquid_bottom)
    if not np.any(liquid):
        raise ValueError("vial geometry leaves no visible liquid pixels")
    objects = []
    object_id = 0
    for kind, number, diameter, density, contrast in (
        ("particle", n_particles, float(particle_diameter_um), float(particle_density_kg_m3), float(particle_contrast)),
        ("bubble", n_bubbles, max(90.0, float(particle_diameter_um) * 1.25), 1.2, min(0.95, float(particle_contrast) * 1.15)),
    ):
        for _ in range(number):
            # Keep one PSF radius clear of the wall/meniscus at t=0.
            for _attempt in range(200):
                col = rng.uniform(cx - 0.72 * radius_px, cx + 0.72 * radius_px)
                row = rng.uniform(liquid_top + 4, liquid_bottom - 4)
                if ((col - cx) / radius_px) ** 2 + ((row - cy) / radius_px) ** 2 < 0.55:
                    break
            objects.append({"id": object_id, "type": kind, "row": row, "col": col,
                            "diameter_um": diameter, "density": density, "contrast": contrast})
            object_id += 1

    scratches = []
    for scratch_id in range(n_scratches):
        col = rng.uniform(cx - 0.70 * radius_px, cx + 0.70 * radius_px)
        row = rng.uniform(liquid_top + 5, liquid_bottom - 8)
        angle = rng.uniform(-0.35, 0.35)
        length = rng.uniform(8.0, 17.0)
        scratches.append((object_id + scratch_id, row, col, angle, length))

    frames = np.empty((n_frames, h, w), dtype=np.float64)
    rows = {k: [] for k in ("object_id", "object_type", "frame", "row_px", "col_px", "row_mm", "col_mm",
                             "diameter_um", "density_kg_m3", "visible")}
    omega = float(initial_omega_rad_s) * np.exp(-np.arange(n_frames) * dt / float(decay_time_s))
    for frame in range(n_frames):
        # Backlight has a bright, nearly uniform liquid. Side light has a fixed lateral gradient.
        base = 0.16 + 0.54 * liquid.astype(float)
        if illumination == "side":
            base += liquid * (0.13 * (xx - cx) / max(radius_px, 1.0))
        base += 0.025 * np.exp(-((yy - liquid_top) / 1.4) ** 2) * inside  # meniscus cue
        image = base
        # Stationary glass scratches are deliberately rendered in every frame.
        for sid, sr, sc, ang, length in scratches:
            for s in np.linspace(-length / 2.0, length / 2.0, int(length * 2) + 1):
                rr, cc = sr + s * math.sin(ang), sc + s * math.cos(ang)
                _draw_gaussian(image, rr, cc, 0.55, -0.11)
            for key, value in (("object_id", sid), ("object_type", "scratch"), ("frame", frame),
                               ("row_px", sr), ("col_px", sc), ("row_mm", (sr - cy) * px_mm),
                               ("col_mm", (sc - cx) * px_mm), ("diameter_um", 0.0),
                               ("density_kg_m3", np.nan), ("visible", True)):
                rows[key].append(value)
        for ob in objects:
            if frame:
                # swirl in image coordinates and gravitational / buoyant Stokes drift
                previous_row = ob["row"]
                dy, dx = (ob["row"] - cy) * px_mm / 1000.0, (ob["col"] - cx) * px_mm / 1000.0
                ob["row"] += (float(omega[frame - 1]) * dx / px_mm +
                              (2.0 / 9.0) * (ob["diameter_um"] * 1e-6 / 2.0) ** 2 *
                              (ob["density"] - float(fluid_density_kg_m3)) * _G / float(viscosity_pa_s) /
                              px_mm * 1000.0) * dt
                ob["col"] += (-float(omega[frame - 1]) * dy / px_mm) * dt
                # geometric reflection at the circular wall and horizontal liquid limits
                vec_r, vec_c = ob["row"] - cy, ob["col"] - cx
                rad = math.hypot(vec_r, vec_c)
                if rad > 0.92 * radius_px:
                    ob["row"] = cy + vec_r / rad * 0.92 * radius_px
                    ob["col"] = cx + vec_c / rad * 0.92 * radius_px
                # In the zero-swirl settling check a hard wall may arrest a
                # particle, but must not turn gravity into an upward jump.
                if initial_omega_rad_s == 0.0 and ob["density"] >= fluid_density_kg_m3:
                    ob["row"] = max(ob["row"], previous_row)
                ob["row"] = float(np.clip(ob["row"], liquid_top + 2.0, liquid_bottom - 2.0))
            visible = liquid_top < ob["row"] < liquid_bottom and abs(ob["col"] - cx) < radius_px
            sigma = max(0.75, ob["diameter_um"] / float(pixel_size_um) * 0.9)
            amp = ob["contrast"] * (1.0 if ob["type"] == "bubble" else (0.95 if illumination == "back" else 0.68))
            if visible:
                _draw_gaussian(image, ob["row"], ob["col"], sigma, amp)
            for key, value in (("object_id", ob["id"]), ("object_type", ob["type"]), ("frame", frame),
                               ("row_px", ob["row"]), ("col_px", ob["col"]),
                               ("row_mm", (ob["row"] - cy) * px_mm), ("col_mm", (ob["col"] - cx) * px_mm),
                               ("diameter_um", ob["diameter_um"]), ("density_kg_m3", ob["density"]), ("visible", visible)):
                rows[key].append(value)
        image += rng.normal(0.0, float(noise_sigma), image.shape)
        frames[frame] = np.clip(image, 0.0, 1.0)
    truth = {key: np.asarray(value) for key, value in rows.items()}
    truth.update({"omega_rad_s": omega, "frame_interval_s": dt, "seed": int(seed),
                  "illumination": illumination, "pixel_size_um": float(pixel_size_um)})
    return frames, truth


def track_moving_particles(frames, *, threshold=0.045, max_displacement_px=10.0,
                           min_area_px=2, static_threshold=0.055):
    """画像列から粒子・気泡・静止したガラス傷を分け、軌跡表を返す。

    Each frame is compared with the temporal median, so stationary scratches are
    reported from the median image and moving objects from residual components.
    Consecutive moving detections are linked greedily only within
    ``max_displacement_px``; ambiguous or too-large jumps start a new track
    rather than being silently joined.  A moving track whose fitted row velocity
    is negative is labelled ``bubble`` (image rows increase downward), otherwise
    ``particle``.  This is a conservative 2-D projection tracker, not an
    identity-preserving multi-object tracker through overlap/occlusion.

    Returns a table with one row per detection: ``frame``, ``track_id``,
    ``object_class``, centroid, area, and row velocity.  Input must be a finite
    ``(T,H,W)`` sequence with at least three frames.
    """
    x = np.asarray(frames, dtype=np.float64)
    if x.ndim != 3 or x.shape[0] < 3 or min(x.shape[1:]) < 8:
        raise ValueError("frames must be a finite (T, H, W) sequence with T >= 3")
    if not np.all(np.isfinite(x)):
        raise ValueError("frames contains non-finite values")
    threshold, max_displacement_px = _positive(threshold, "threshold"), _positive(max_displacement_px, "max_displacement_px")
    if int(min_area_px) != min_area_px or int(min_area_px) < 1:
        raise ValueError("min_area_px must be an integer >= 1")
    static_threshold = _positive(static_threshold, "static_threshold")
    from scipy import ndimage as ndi

    median = np.median(x, axis=0)
    smooth = ndi.gaussian_filter(median, 3.0)
    stationary = np.abs(median - smooth) >= static_threshold
    slabel, sn = ndi.label(stationary)
    records = []
    next_id = 0
    for lab in range(1, sn + 1):
        pts = np.argwhere(slabel == lab)
        # The vial silhouette is also stationary but is not a glass scratch.
        # A scratch is deliberately local; reject container-scale components.
        if pts.shape[0] < min_area_px or pts.shape[0] > 300:
            continue
        row, col = pts.mean(axis=0)
        for frame in range(x.shape[0]):
            records.append([frame, next_id, "scratch", row, col, int(pts.shape[0]), 0.0])
        next_id += 1
    active = {}
    for frame in range(x.shape[0]):
        # A matched 0.8 px Gaussian suppresses independent sensor samples before
        # thresholding.  Without it, a low-contrast detector becomes a tracker of
        # accidental two-pixel noise islands rather than of PSF-shaped objects.
        residual = ndi.gaussian_filter(x[frame] - median, 0.8)
        labels, nlab = ndi.label(residual >= threshold)
        detections = []
        for lab in range(1, nlab + 1):
            pts = np.argwhere(labels == lab)
            if pts.shape[0] < min_area_px:
                continue
            row, col = pts.mean(axis=0)
            detections.append((float(row), float(col), int(pts.shape[0])))
        used = set()
        new_active = {}
        for row, col, area in detections:
            best, best_d = None, max_displacement_px
            for tid, (pr, pc) in active.items():
                if tid in used:
                    continue
                d = math.hypot(row - pr, col - pc)
                if d <= best_d:
                    best, best_d = tid, d
            if best is None:
                best = next_id
                next_id += 1
            used.add(best)
            new_active[best] = (row, col)
            records.append([frame, best, "moving", row, col, area, np.nan])
        active = new_active
    # label tracks after fitting their signed vertical velocity
    for tid in sorted({int(r[1]) for r in records if r[2] == "moving"}):
        inds = [i for i, r in enumerate(records) if r[1] == tid and r[2] == "moving"]
        if len(inds) >= 2:
            fr = np.array([records[i][0] for i in inds], dtype=float)
            rr = np.array([records[i][3] for i in inds], dtype=float)
            velocity = float(np.polyfit(fr, rr, 1)[0])
        else:
            velocity = 0.0
        label = "bubble" if velocity < 0.0 else "particle"
        for i in inds:
            records[i][2], records[i][6] = label, velocity
    names = ("frame", "track_id", "object_class", "row_px", "col_px", "area_px", "row_velocity_px_frame")
    return {name: np.asarray([r[j] for r in records]) for j, name in enumerate(names)}
