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


def _input_error(name, value, expected, why, fix, *, expected_ja=None, why_ja=None, fix_ja=None):
    """Make fail-closed input errors actionable in English and Japanese."""
    expected_ja = expected if expected_ja is None else expected_ja
    why_ja = why if why_ja is None else why_ja
    fix_ja = fix if fix_ja is None else fix_ja
    return ValueError(
        f"{name}={value!r} is invalid; expected {expected}. Why: {why}. "
        f"How to fix: {fix}. / {name}={value!r} は不正です。期待値: {expected_ja}。"
        f"理由: {why_ja}。対処: {fix_ja}。"
    )


def _positive(value, name):
    value = float(value)
    if not np.isfinite(value) or value <= 0:
        raise _input_error(name, value, "a finite number > 0",
                           "the physical scale and the detector threshold must be positive",
                           f"pass a finite positive {name}, for example 0.01")
    return value


def _image_shape(shape):
    if len(shape) != 2:
        raise _input_error("shape", shape, "(height, width)",
                           "the sequence renderer needs exactly two image dimensions",
                           "pass a tuple such as (96, 72)")
    h, w = (int(shape[0]), int(shape[1]))
    if h < 32 or w < 24:
        raise _input_error("shape", shape, "height >= 32 and width >= 24 pixels",
                           "smaller images cannot contain the vial, liquid, and tracking cues",
                           "increase shape to at least (32, 24)")
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


def _draw_ring(image, row, col, radius, amplitude):
    """Add a soft refractive bubble ring; the central void stays transparent."""
    h, w = image.shape
    r0, r1 = max(0, int(math.floor(row - radius - 3))), min(h, int(math.ceil(row + radius + 4)))
    c0, c1 = max(0, int(math.floor(col - radius - 3))), min(w, int(math.ceil(col + radius + 4)))
    if r0 >= r1 or c0 >= c1:
        return
    rr, cc = np.mgrid[r0:r1, c0:c1]
    distance = np.hypot(rr - row, cc - col)
    image[r0:r1, c0:c1] += amplitude * np.exp(-((distance - radius) ** 2) / 1.1)


def _vial_profile(height, width, body_half):
    """Return the visible half-width of an ISO 8362-1 2R-like vial.

    The outline preserves the public 2R proportions: 16 mm body diameter,
    13 mm neck/finish diameter, 35 mm overall height, and an 8 mm finish
    height.  It is scaled to the requested raster, so it is a drawing profile
    rather than a dimensional metrology model.  The wide finish, short shoulder
    transition, cylindrical body, and rounded heel deliberately avoid a
    long-necked bottle silhouette.  The flow remains the documented
    axisymmetric screening approximation.

    公開された ISO 8362-1 の 2R 比率(胴 16 mm、口部 13 mm、全高 35 mm、
    口部高 8 mm)を保つ描画用外形である。要求されたラスタに合わせて拡大縮小
    するため、寸法計測モデルではない。
    """
    y = np.arange(height, dtype=float)
    # 2R: d2 / d1 = 13 / 16.  8 / 35 of the usable height is the finish;
    # keep it visibly wide instead of using a bottle-like narrow neck.
    neck_half = max(2.0, (13.0 / 16.0) * body_half)
    top, neck_bottom = 0.025 * height, 0.255 * height
    shoulder_bottom = 0.370 * height
    heel_top, heel_bottom = 0.875 * height, 0.975 * height
    profile = np.full(height, body_half, dtype=float)
    profile[y < top] = 0.0
    q = (y >= top) & (y < neck_bottom)
    profile[q] = neck_half
    q = (y >= neck_bottom) & (y < shoulder_bottom)
    profile[q] = neck_half + (body_half - neck_half) * (y[q] - neck_bottom) / (shoulder_bottom - neck_bottom)
    q = (y > heel_top) & (y <= heel_bottom)
    # The circular heel creates the visible curved bottom rather than a box edge.
    t = (y[q] - heel_top) / (heel_bottom - heel_top)
    profile[q] = body_half * np.sqrt(np.clip(1.0 - 0.72 * t * t, 0.08, 1.0))
    profile[y > heel_bottom] = 0.0
    return profile


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

    The rendered outline is a display-only 2R-like profile, not a metrology
    calibration.  Its public dimensional source is ISO 8362-1:2018(E), Table 1
    (2R: 16 mm body, 13 mm finish, 35 mm overall height, 8 mm finish height),
    previewed at
    ``https://cdn.standards.iteh.ai/samples/74398/343407bc7b564f6184bfa0a9decede14/ISO-8362-1-2018.pdf``.
    An independent public 2R product listing confirms the 16 mm body and 35 mm
    overall height at
    ``https://www.westpharma.com/es-es/products/vial-containment-solutions/vials/nuova-ompi-sg-ez-fill-glass-vials-sterile-3-8-10``.
    描画外形は計測校正ではなく、公開 ISO 8362-1:2018(E) Table 1 の 2R 比率を
    使う表示モデルである。独立した公開製品寸法も上記 URL で確認する。

    Raises ``ValueError`` for nonphysical dimensions, an unknown illumination,
    or a nonintegral object count.
    """
    h, w = _image_shape(shape)
    if int(n_frames) != n_frames or int(n_frames) < 3:
        raise _input_error("n_frames", n_frames, "an integer >= 3",
                           "motion and a stationary background need at least three frames",
                           "pass n_frames=3 or more")
    n_frames = int(n_frames)
    for name, value in (("frame_interval_s", frame_interval_s), ("decay_time_s", decay_time_s),
                        ("vial_radius_mm", vial_radius_mm), ("liquid_height_mm", liquid_height_mm),
                        ("particle_diameter_um", particle_diameter_um), ("particle_density_kg_m3", particle_density_kg_m3),
                        ("viscosity_pa_s", viscosity_pa_s), ("fluid_density_kg_m3", fluid_density_kg_m3),
                        ("pixel_size_um", pixel_size_um)):
        _positive(value, name)
    if illumination not in ("back", "side"):
        raise _input_error("illumination", illumination, "'back' or 'side'",
                           "the simulator only has calibrated rendering rules for these two lighting modes",
                           "use illumination='back' or illumination='side'")
    if not np.isfinite(particle_contrast) or not 0.0 < float(particle_contrast) <= 1.0:
        raise _input_error("particle_contrast", particle_contrast, "a finite value in (0, 1]",
                           "contrast is rendered as a bounded fraction of the optical background",
                           "use a value such as 0.065")
    if not np.isfinite(initial_omega_rad_s) or initial_omega_rad_s < 0:
        raise _input_error("initial_omega_rad_s", initial_omega_rad_s, "a finite value >= 0",
                           "a negative angular speed is outside this one-direction spin-stop model",
                           "use 0 for no swirl or a positive angular speed")
    if not np.isfinite(noise_sigma) or noise_sigma < 0:
        raise _input_error("noise_sigma", noise_sigma, "a finite value >= 0",
                           "sensor noise is a non-negative standard deviation",
                           "use 0 for noiseless data or a small positive value")
    counts = []
    for name, value in (("n_particles", n_particles), ("n_bubbles", n_bubbles), ("n_scratches", n_scratches)):
        if int(value) != value or int(value) < 0:
            raise _input_error(name, value, "a non-negative integer",
                               "object counts must be whole items before trajectories are generated",
                               f"use {name}=0, 1, 2, ...")
        counts.append(int(value))
    n_particles, n_bubbles, n_scratches = counts

    rng = np.random.default_rng(seed)
    dt = float(frame_interval_s)
    px_mm = float(pixel_size_um) / 1000.0
    cx = (w - 1) / 2.0
    body_half = min(0.37 * (w - 1), float(vial_radius_mm) / px_mm)
    profile = _vial_profile(h, w, body_half)
    glass_px = max(1.0, min(3.5, 0.7 + 0.008 * body_half))
    yy, xx = np.mgrid[:h, :w]
    half_at_y = profile[np.clip(yy, 0, h - 1)]
    # A front view of the container: narrow neck, shoulders, cylindrical body
    # and rounded heel.  The flow remains the documented axial screening model.
    glass = np.abs(xx - cx) <= half_at_y
    inner = np.abs(xx - cx) <= np.maximum(0.0, half_at_y - glass_px)
    body_top, body_bottom = 0.29 * h, 0.875 * h
    liquid_bottom = min(body_bottom, 0.94 * h) - 2.0
    liquid_height_px = min(float(liquid_height_mm) / px_mm, 0.72 * h)
    liquid_top = max(body_top + 2.0, liquid_bottom - liquid_height_px)
    # A shallow concave meniscus: the edges are raised by the wetting cue.
    normalized_x = np.clip((xx - cx) / np.maximum(half_at_y, 1.0), -1.0, 1.0)
    meniscus = liquid_top + 2.0 * normalized_x * normalized_x
    liquid = inner & (yy >= meniscus) & (yy <= liquid_bottom)
    cy = 0.5 * (liquid_top + liquid_bottom)
    flow_radius = max(5.0, min(0.78 * body_half, 0.48 * (liquid_bottom - liquid_top)))
    if not np.any(liquid):
        raise _input_error("shape/liquid_height_mm", (shape, liquid_height_mm),
                           "a geometry with visible liquid pixels",
                           "the image is too short for the requested liquid height and vial profile",
                           "increase shape height or reduce liquid_height_mm")
    objects = []
    object_id = 0
    for kind, number, diameter, density, contrast in (
        ("particle", n_particles, float(particle_diameter_um), float(particle_density_kg_m3), float(particle_contrast)),
        ("bubble", n_bubbles, max(90.0, float(particle_diameter_um) * 1.25), 1.2, min(0.95, float(particle_contrast) * 1.15)),
    ):
        for _ in range(number):
            # Keep one PSF radius clear of the wall/meniscus and away from the
            # optical axis at t=0.  A particle exactly on the vortex centre has
            # no measurable lateral post-stop motion, so it would make a motion
            # detector appear to depend on a hidden random placement.
            for _attempt in range(200):
                angle = rng.uniform(0.0, 2.0 * math.pi)
                radial = rng.uniform(0.32, 0.65) * flow_radius
                col = cx + radial * math.cos(angle)
                row = cy + radial * math.sin(angle)
                if liquid_top + 4 < row < liquid_bottom - 4:
                    break
            objects.append({"id": object_id, "type": kind, "row": row, "col": col,
                            "diameter_um": diameter, "density": density, "contrast": contrast})
            object_id += 1

    scratches = []
    for scratch_id in range(n_scratches):
        col = rng.uniform(cx - 0.68 * body_half, cx + 0.68 * body_half)
        row = rng.uniform(liquid_top + 5, liquid_bottom - 8)
        angle = rng.uniform(-0.35, 0.35)
        length = rng.uniform(8.0, 17.0)
        scratches.append((object_id + scratch_id, row, col, angle, length))

    frames = np.empty((n_frames, h, w), dtype=np.float64)
    rows = {k: [] for k in ("object_id", "object_type", "frame", "row_px", "col_px", "row_mm", "col_mm",
                             "diameter_um", "density_kg_m3", "visible")}
    omega = float(initial_omega_rad_s) * np.exp(-np.arange(n_frames) * dt / float(decay_time_s))
    for frame in range(n_frames):
        edge_distance = np.abs(np.abs(xx - cx) - half_at_y)
        inner_edge_distance = np.abs(np.abs(xx - cx) - np.maximum(0.0, half_at_y - glass_px))
        rim = glass * np.exp(-(edge_distance / max(0.8, glass_px * 0.65)) ** 2)
        refracted_edge = inner * np.exp(-(inner_edge_distance / max(1.0, glass_px * 1.25)) ** 2)
        meniscus_line = inner * np.exp(-((yy - meniscus) / 1.05) ** 2)
        meniscus_shadow = liquid * np.exp(-((yy - meniscus - 1.8) / 1.6) ** 2)
        bottom_curve = glass * np.exp(-((yy - liquid_bottom) / 2.3) ** 2)
        side_shine = glass * np.exp(-((np.abs(xx - cx) - 0.72 * half_at_y) /
                                      max(1.4, 0.08 * body_half)) ** 2)
        if illumination == "back":
            # Bright-field: a white diffuser behind the vial makes opaque particles dark.
            base = 0.80 + 0.06 * np.exp(-((xx - cx) / max(1.0, body_half * 1.2)) ** 2)
            base = base - 0.12 * glass + 0.16 * inner + 0.035 * liquid
            base += 0.17 * rim + 0.08 * refracted_edge + 0.055 * side_shine
            base += 0.10 * meniscus_line - 0.065 * meniscus_shadow + 0.12 * bottom_curve
        else:
            # Dark-field / Tyndall-like side light: a dark field makes scattered light bright.
            base = np.full((h, w), 0.018, dtype=float)
            beam = np.exp(-((xx - (cx + 0.28 * body_half)) / max(1.0, 0.22 * body_half)) ** 2)
            base += glass * (0.030 + 0.055 * beam) + inner * (0.020 + 0.025 * beam)
            base += liquid * (0.018 + 0.025 * beam)
            base += 0.25 * rim + 0.10 * refracted_edge + 0.075 * side_shine
            base += 0.13 * meniscus_line + 0.09 * bottom_curve
        image = np.asarray(base, dtype=float)
        # Stationary glass scratches are deliberately rendered in every frame.
        for sid, sr, sc, ang, length in scratches:
            for s in np.linspace(-length / 2.0, length / 2.0, int(length * 2) + 1):
                rr, cc = sr + s * math.sin(ang), sc + s * math.cos(ang)
                _draw_gaussian(image, rr, cc, 0.55, -0.095 if illumination == "back" else 0.10)
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
                ob["row"] += (float(omega[frame - 1]) * dx * 1000.0 / px_mm +
                              (2.0 / 9.0) * (ob["diameter_um"] * 1e-6 / 2.0) ** 2 *
                              (ob["density"] - float(fluid_density_kg_m3)) * _G / float(viscosity_pa_s) /
                              px_mm * 1000.0) * dt
                ob["col"] += (-float(omega[frame - 1]) * dy / px_mm) * dt
                # geometric reflection at the circular wall and horizontal liquid limits
                vec_r, vec_c = ob["row"] - cy, ob["col"] - cx
                rad = math.hypot(vec_r, vec_c)
                if rad > 0.92 * flow_radius:
                    ob["row"] = cy + vec_r / rad * 0.92 * flow_radius
                    ob["col"] = cx + vec_c / rad * 0.92 * flow_radius
                # In the zero-swirl settling check a hard wall may arrest a
                # particle, but must not turn gravity into an upward jump.
                if initial_omega_rad_s == 0.0 and ob["density"] >= fluid_density_kg_m3:
                    ob["row"] = max(ob["row"], previous_row)
                ob["row"] = float(np.clip(ob["row"], liquid_top + 2.0, liquid_bottom - 2.0))
            visible = liquid_top < ob["row"] < liquid_bottom and abs(ob["col"] - cx) < 0.92 * body_half
            sigma = max(0.55, ob["diameter_um"] / float(pixel_size_um) * 0.35)
            size_gain = min(1.55, 0.28 + ob["diameter_um"] / 190.0)
            amp = ob["contrast"] * size_gain * (-1.15 if illumination == "back" else 1.35)
            if visible:
                if ob["type"] == "bubble":
                    _draw_ring(image, ob["row"], ob["col"], max(1.15, 1.45 * sigma), -0.7 * amp)
                    _draw_gaussian(image, ob["row"], ob["col"], 0.65 * sigma, 0.25 * amp)
                else:
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
    """画像列から動く物と静止したガラス傷を分け、軌跡表を返す。

    Each frame is compared with the temporal median, so stationary scratches are
    reported from the median image and moving objects from residual components.
    Consecutive moving detections are linked greedily only within
    ``max_displacement_px``; ambiguous or too-large jumps start a new track
    rather than being silently joined.  Every moving track is deliberately
    labelled ``"moving"``: the frame-only API has neither a calibrated lighting
    polarity nor enough 3-D trajectory context to identify a particle versus a
    bubble.  In particular, residual swirl can make a settling particle have a
    negative image-row velocity.  This is a conservative 2-D projection tracker,
    not an identity-preserving multi-object tracker through overlap/occlusion.

    動く軌跡は常に保守的に ``"moving"`` とし、速度符号だけで粒子/気泡を
    推定しない。残留旋回では沈降粒子も画像上向きに見えるためである。

    Returns a table with one row per detection: ``frame``, ``track_id``,
    ``object_class``, centroid, area, and row velocity.  Input must be a finite
    non-constant ``(T,H,W)`` sequence with at least three frames.  A sequence
    that is constant over both time and space is rejected; call it only for
    images with a motion or spatial cue, and record ``no detected motion``
    directly when the intended interpretation is no motion.
    """
    x = np.asarray(frames, dtype=np.float64)
    if x.ndim != 3 or x.shape[0] < 3 or min(x.shape[1:]) < 8:
        raise _input_error("frames.shape", tuple(x.shape), "a finite (T, H, W) sequence with T >= 3 and H,W >= 8",
                           "temporal subtraction needs a sequence and a spatial neighbourhood",
                           "pass at least three finite grayscale frames")
    if not np.all(np.isfinite(x)):
        raise _input_error("frames", "contains NaN or inf", "finite pixel values",
                           "a non-finite pixel makes a residual threshold meaningless",
                           "replace NaN/inf before calling track_moving_particles")
    if np.ptp(x) == 0.0:
        value = "all %d samples equal %g; shape=%s" % (x.size, float(x.flat[0]), tuple(x.shape))
        raise _input_error("frames", value, "finite frames with a spatial or temporal change",
                           "a sequence constant over time and space has no motion cue to track",
                           "pass consecutive camera frames with variation; for an intended still scene, "
                           "record 'no detected motion' without calling track_moving_particles",
                           expected_ja="空間または時間で変化する有限のフレーム",
                           why_ja="時間・空間の両方で一定な列には追跡する動きの手掛かりがないため",
                           fix_ja="変化を含む連続カメラフレームを渡す。静止場面ならこの op を呼ばず、"
                                  "'no detected motion' と記録する")
    threshold, max_displacement_px = _positive(threshold, "threshold"), _positive(max_displacement_px, "max_displacement_px")
    if int(min_area_px) != min_area_px or int(min_area_px) < 1:
        raise _input_error("min_area_px", min_area_px, "an integer >= 1",
                           "connected-component areas count whole pixels",
                           "use min_area_px=1 or a larger integer")
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
        # Bright-field particles are dark on a bright diffuser; dark-field /
        # Tyndall particles are bright on a dark field.  The signed residual is
        # kept for the image, but detection is intentionally polarity agnostic.
        labels, nlab = ndi.label(np.abs(residual) >= threshold)
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
    # 軌跡の縦速度は出すが、符号から種別を断定しない。
    # Keep the signed velocity for review, but never infer object kind from it.
    for tid in sorted({int(r[1]) for r in records if r[2] == "moving"}):
        inds = [i for i, r in enumerate(records) if r[1] == tid and r[2] == "moving"]
        if len(inds) >= 2:
            fr = np.array([records[i][0] for i in inds], dtype=float)
            rr = np.array([records[i][3] for i in inds], dtype=float)
            velocity = float(np.polyfit(fr, rr, 1)[0])
        else:
            velocity = 0.0
        for i in inds:
            records[i][6] = velocity
    names = ("frame", "track_id", "object_class", "row_px", "col_px", "area_px", "row_velocity_px_frame")
    return {name: np.asarray([r[j] for r in records]) for j, name in enumerate(names)}
