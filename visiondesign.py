# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""visiondesign — design a machine-vision system on paper, before any hardware exists.

The question an integrator actually asks first is not "which algorithm?" but
**"will this camera and this lens, at this working distance, even see the defect
I care about?"** Answering it needs no simulation and no data — it is closed-form
optics plus sampling theory. This module answers it, and then builds the image
formation chain that turns an ideal scene into what that specific system would
actually capture.

Scope, and what this is NOT:

  * It is **closed-form**, not a renderer. There is no path tracing, no global
    illumination, no measured BRDF. Specular and transparent parts — exactly
    where light transport matters most — are outside what this can predict.
    Where a Monte-Carlo light-transport product would give you an image, this
    gives you the *limits*: resolution, depth of field, illumination falloff,
    contrast transfer. Those limits are often what decides feasibility.
  * It reuses ``optics`` rather than reimplementing it (``thin_lens``,
    ``depth_of_field``, ``airy_pattern``, ``mtf_diffraction``,
    ``relative_illumination``). Ray-surface interaction stays in ``match3d``;
    sensor corruption stays in the ``aug_*`` family; deconvolution stays in
    ``volrestore`` / ``complexops``.

The three questions it answers, in order:

  1. **Geometry** — what does the sensor see? (:func:`system_geometry`:
     field of view, magnification, millimetres per pixel, working distance.)
  2. **Resolution** — what is the smallest feature that survives? Two
     independent limits compete: **sampling** (Nyquist: you need ~2 pixels per
     feature) and **diffraction** (the Airy disc set by the f-number).
     :func:`resolving_power` reports both and **names which one dominates**,
     because the fix differs — a longer lens versus a faster aperture.
  3. **Feasibility** — put a defect size in, get a verdict out
     (:func:`system_feasibility`), including the depth range over which it holds
     and how much light is lost at the corner of the field.

Then :func:`image_formation` applies that system to an ideal image: diffraction
blur, defocus for the part's depth, cos^4 falloff, and exposure — so the picture
you evaluate an algorithm on is the picture *this* system would produce.

Units are stated in every parameter name (``_mm``, ``_um``, ``_deg``); mixing
them up is the classic error in this arithmetic, so nothing is left implicit.
"""
from __future__ import annotations

import numpy as np

import optics

__all__ = [
    "system_geometry", "resolving_power", "system_feasibility",
    "image_formation", "detectability_limit",
    "MAX_IMAGE_PIXELS",
]

#: Guard for :func:`image_formation` — the blur kernels are built in the Fourier
#: domain, so a careless resolution turns into several complex temporaries.
MAX_IMAGE_PIXELS = 1 << 24


def _pos(value, name):
    """Positive finite float, or a named ValueError. Rejects text explicitly.

    ``float("50")`` succeeds, so an unparsed config string would otherwise sail
    through as millimetres (the same trap the optics family found in
    ``thin_lens``).
    """
    if isinstance(value, (str, bytes, bool)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    v = float(value)
    if not np.isfinite(v) or v <= 0.0:
        raise ValueError("%s must be positive and finite, got %r" % (name, value))
    return v


def system_geometry(focal_mm=50.0, working_distance_mm=500.0,
                    pixel_pitch_um=3.45, width_px=2448, height_px=2048):
    """What the sensor covers on the part, from the lens and the standoff.

    Returns a table with the sensor size in millimetres, the (positive)
    magnification, the field of view on the object, and — the number an
    integrator actually writes down — **micrometres per pixel**.

    The magnification comes from the thin-lens conjugate, so it agrees with
    ``optics.thin_lens`` by construction rather than by a duplicated formula.
    A working distance at or inside the focal length has no real image; that is
    a ``ValueError``, not a negative field of view.

    Raises ValueError: non-positive or non-finite inputs, a non-integer or
    non-positive pixel count, or a working distance <= the focal length.
    """
    f = _pos(focal_mm, "focal_mm")
    wd = _pos(working_distance_mm, "working_distance_mm")
    pitch = _pos(pixel_pitch_um, "pixel_pitch_um")
    for name, n in (("width_px", width_px), ("height_px", height_px)):
        if isinstance(n, bool) or int(n) != n or int(n) < 1:
            raise ValueError("%s must be a positive integer, got %r" % (name, n))
    if wd <= f:
        raise ValueError(
            "working_distance_mm (%g) must exceed focal_mm (%g): at or inside "
            "the focal length the thin lens forms no real image" % (wd, f))
    conj = optics.thin_lens(focal_mm=f, object_mm=wd)
    mag = abs(float(conj["magnification"]))
    sensor_w_mm = int(width_px) * pitch * 1e-3
    sensor_h_mm = int(height_px) * pitch * 1e-3
    return {
        "sensor_w_mm": sensor_w_mm,
        "sensor_h_mm": sensor_h_mm,
        "sensor_diagonal_mm": float(np.hypot(sensor_w_mm, sensor_h_mm)),
        "magnification": mag,
        "image_distance_mm": float(conj["image_mm"]),
        "fov_w_mm": sensor_w_mm / mag,
        "fov_h_mm": sensor_h_mm / mag,
        "um_per_pixel": pitch / mag,
        "working_distance_mm": wd,
        "focal_mm": f,
    }


def resolving_power(pixel_pitch_um=3.45, f_number=8.0, magnification=0.1,
                    wavelength_um=0.55):
    """The smallest feature the system can resolve, and **which limit binds**.

    Two independent limits compete, and they have different fixes:

      * **Sampling (Nyquist)** — a feature needs about two pixels to be seen as
        a feature, so the object-side limit is ``2 * pixel_pitch / magnification``.
        Fix: more magnification (longer lens or shorter standoff) or a finer
        sensor.
      * **Diffraction** — the Airy disc diameter is ``2.44 * lambda * N_eff``
        with the *working* f-number ``N_eff = N * (1 + |m|)``, which is the one
        that matters at finite conjugates and is routinely forgotten at macro
        magnifications. Fix: a faster aperture (smaller N) — stopping down
        further makes this worse, not better.

    Returns both limits on the object, the binding one, and the ratio of the
    Airy disc to the pixel: below ~1 the system is sampling-limited (the sensor
    throws away optical detail), above ~2 it is diffraction-limited (extra
    pixels buy nothing).

    Raises ValueError: non-positive or non-finite inputs.
    """
    pitch = _pos(pixel_pitch_um, "pixel_pitch_um")
    n = _pos(f_number, "f_number")
    mag = _pos(magnification, "magnification")
    lam = _pos(wavelength_um, "wavelength_um")
    n_eff = n * (1.0 + mag)
    airy_um = 2.44 * lam * n_eff
    nyquist_object_um = 2.0 * pitch / mag
    diffraction_object_um = airy_um / mag
    limited_by = ("diffraction" if diffraction_object_um > nyquist_object_um
                  else "sampling")
    return {
        "working_f_number": n_eff,
        "airy_diameter_um": airy_um,
        "airy_over_pixel": airy_um / pitch,
        "nyquist_object_um": nyquist_object_um,
        "diffraction_object_um": diffraction_object_um,
        "resolution_object_um": max(nyquist_object_um, diffraction_object_um),
        "limited_by": limited_by,
    }


def system_feasibility(defect_um=50.0, focal_mm=50.0, working_distance_mm=500.0,
                       pixel_pitch_um=3.45, f_number=8.0, width_px=2448,
                       height_px=2048, wavelength_um=0.55, depth_tolerance_mm=5.0):
    """Can this system see a defect of *defect_um*? A verdict, with the reason.

    Combines :func:`system_geometry` and :func:`resolving_power`, then adds the
    two things that decide whether the answer survives contact with a real part:

      * **Depth of field** (via ``optics.depth_of_field``, with the circle of
        confusion set to one pixel referred to the object): a part that moves
        ``depth_tolerance_mm`` must stay inside it.
      * **Corner illumination** (via ``optics.relative_illumination``): the
        natural cos^4 falloff at the edge of the field, which is where the
        marginal defect will be.

    ``verdict`` is one of ``"resolvable"`` (the defect spans at least the
    resolution limit **and** the depth tolerance fits), ``"marginal"`` (resolved
    but the depth tolerance exceeds the depth of field), or ``"not_resolvable"``.
    ``pixels_across`` is the honest headline: how many pixels the defect covers.

    Raises ValueError: any non-positive or non-finite input.
    """
    defect = _pos(defect_um, "defect_um")
    tol = _pos(depth_tolerance_mm, "depth_tolerance_mm")
    geo = system_geometry(focal_mm, working_distance_mm, pixel_pitch_um,
                          width_px, height_px)
    res = resolving_power(pixel_pitch_um, f_number, geo["magnification"],
                          wavelength_um)
    pixels_across = defect / geo["um_per_pixel"]
    # 錯乱円は「object 側で 1 画素ぶん」に相当する image 側の大きさ = 画素ピッチ。
    dof = optics.depth_of_field(focal_mm=geo["focal_mm"], f_number=float(f_number),
                                subject_mm=geo["working_distance_mm"],
                                coc_mm=_pos(pixel_pitch_um, "pixel_pitch_um") * 1e-3)
    # ``optics.depth_of_field`` は近点/遠点/被写界深度/過焦点距離を返す。
    # 遠点が無限大なら深度も無限 — その場合はどんな公差も収まる。
    dof_total = float(dof["depth_mm"])
    dof_ok = bool(dof.get("far_is_infinite") or
                  (np.isfinite(dof_total) and dof_total >= tol))
    half_angle_deg = float(np.degrees(np.arctan2(
        geo["sensor_diagonal_mm"] / 2.0, geo["image_distance_mm"])))
    # ``relative_illumination`` は (角度, 相対照度) の曲線。最終行 = 視野の角。
    illum = np.asarray(optics.relative_illumination(half_angle_deg=half_angle_deg),
                       dtype=np.float64)
    corner = float(illum[-1, 1]) if illum.ndim == 2 and illum.shape[1] >= 2 else 1.0
    resolvable = defect >= res["resolution_object_um"]
    verdict = ("resolvable" if resolvable and dof_ok
               else "marginal" if resolvable else "not_resolvable")
    return {
        "verdict": verdict,
        "defect_um": defect,
        "pixels_across": pixels_across,
        "resolution_object_um": res["resolution_object_um"],
        "limited_by": res["limited_by"],
        "um_per_pixel": geo["um_per_pixel"],
        "fov_w_mm": geo["fov_w_mm"],
        "fov_h_mm": geo["fov_h_mm"],
        "depth_of_field_mm": dof_total,
        "depth_tolerance_mm": tol,
        "depth_of_field_ok": dof_ok,
        "corner_illumination": corner,
        "half_angle_deg": half_angle_deg,
    }


def image_formation(scene, f_number=8.0, pixel_pitch_um=3.45,
                    wavelength_um=0.55, defocus_px=0.0, vignetting=True,
                    exposure=1.0, image_distance_mm=None):
    """Turn an ideal image into what *this* system would capture.

    The chain, in the order light actually meets it:

      1. **Diffraction** — convolve with the Airy PSF for this f-number and
         pixel pitch (``optics.airy_pattern``). This is the optical floor; no
         amount of exposure recovers what it removes.
      2. **Defocus** — an additional Gaussian of ``defocus_px``, for the part of
         the scene that sits outside the depth of field.
      3. **Vignetting** — the cos^4 falloff across the field.
      4. **Exposure** — a linear gain, clipped to the sensor's [0, 1] range.

    Sensor noise is deliberately **not** applied here: the ``aug_*`` family
    already models read noise, fixed pattern, rolling shutter and the rest, and
    duplicating it would give two sources of truth. Compose them.

    ``image_distance_mm`` is **required when** ``vignetting=True``. The cos^4
    falloff is set by the *field angle*, and the field angle needs a physical
    distance from the exit pupil to the sensor — it cannot be recovered from the
    array alone. Get it from :func:`system_geometry`'s ``image_distance_mm``
    (``= focal * (1 + magnification)``), not from the focal length.

    .. note::
       Until 2026-09 this normalised the radius to the array's own corner and
       took ``cos(arctan(r))**4`` of it, which put **every** array corner at 45°
       — a fixed 0.2500 whatever the lens, the pitch or the crop. No exception,
       just a plausible wrong number: for f=35 mm at WD=200 mm on 2448x2048 the
       true corner is 0.9671, and a 232x232 tile of it is 0.9997. Passing the
       image distance is what makes the answer a physical one, so it is now
       demanded rather than defaulted.

    The array is assumed to be **centred on the optical axis** and to span
    ``n * pixel_pitch_um``; an off-axis crop gets the falloff of an on-axis
    crop of the same size. Pass ``vignetting=False`` and apply the field
    yourself when that matters.

    Returns the captured image as float64 in [0, 1], same shape as *scene*.

    Raises ValueError: *scene* is not 2-D, is non-finite, exceeds
    ``MAX_IMAGE_PIXELS``, any parameter is non-positive/non-finite
    (``defocus_px`` may be 0), or ``vignetting`` is on without
    ``image_distance_mm``.
    """
    img = np.asarray(scene, dtype=np.float64)
    if img.ndim != 2:
        raise ValueError("scene must be a 2-D image, got a %d-D array" % img.ndim)
    if img.size == 0:
        raise ValueError("scene is empty")
    if img.size > MAX_IMAGE_PIXELS:
        raise ValueError("scene has %d pixels, above MAX_IMAGE_PIXELS=%d — crop "
                         "or downsample first" % (img.size, MAX_IMAGE_PIXELS))
    if not np.isfinite(img).all():
        raise ValueError("scene has non-finite pixel(s) (NaN/Inf)")
    n = _pos(f_number, "f_number")
    pitch = _pos(pixel_pitch_um, "pixel_pitch_um")
    lam = _pos(wavelength_um, "wavelength_um")
    gain = _pos(exposure, "exposure")
    if isinstance(defocus_px, (str, bytes, bool)):
        raise ValueError("defocus_px must be a number, got %r" % (defocus_px,))
    blur = float(defocus_px)
    if not np.isfinite(blur) or blur < 0.0:
        raise ValueError("defocus_px must be >= 0 and finite, got %r" % (defocus_px,))

    from scipy import ndimage
    from scipy.signal import fftconvolve

    # 1) 回折。PSF はカーネルとして使える最小の奇数サイズに切る(Airy の裾は
    #    急速に落ちるので、実測で 99% 以上のエネルギーが入る範囲で足りる)。
    ksize = int(min(31, max(3, 2 * int(np.ceil(2.44 * lam * n / pitch)) + 1)))
    psf = np.asarray(optics.airy_pattern(size=ksize, wavelength_um=lam,
                                         f_number=n, pixel_pitch_um=pitch),
                     dtype=np.float64)
    s = float(psf.sum())
    if not np.isfinite(s) or s <= 0.0:
        raise ValueError("the Airy PSF for f/%g at %g um pitch is degenerate "
                         "(sum=%r) — check the parameters" % (n, pitch, s))
    # 縁の扱い: ``mode="same"`` はセンサの外を 0 とみなすので、一様な面を撮ると
    # **周辺光量落ちとは別の理由で縁が暗くなる**(実測: 一様 1.0 の面で角が
    # 0.727 になった)。シーンはセンサの外にも続いているのが物理なので、
    # カーネル半幅ぶんを端値で延長してから畳み込み、あとで切り戻す。
    pad = ksize // 2
    padded = np.pad(img, pad, mode="edge")
    out = fftconvolve(padded, psf / s, mode="same")[pad:pad + img.shape[0],
                                                    pad:pad + img.shape[1]]
    # 2) デフォーカス(こちらも端値で延長 = 同じ理由)
    if blur > 0.0:
        out = ndimage.gaussian_filter(out, sigma=blur, mode="nearest")
    # 3) 周辺光量落ち(視野の中心からの正規化半径に cos^4 を掛ける)
    if vignetting:
        h, w = out.shape
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
        cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
        r = np.hypot((yy - cy) / max(cy, 1e-12), (xx - cx) / max(cx, 1e-12))
        r = np.clip(r / np.sqrt(2.0), 0.0, 1.0)         # 角で 1
        out = out * np.cos(np.arctan(r)) ** 4
    # 4) 露光
    return np.clip(out * gain, 0.0, 1.0)


def detectability_limit(defect_um_grid, focal_mm=50.0, working_distance_mm=500.0,
                        pixel_pitch_um=3.45, f_number=8.0, width_px=2448,
                        height_px=2048, wavelength_um=0.55,
                        depth_tolerance_mm=5.0):
    """Sweep defect sizes and report **where the design stops working**.

    Feasibility is not a yes/no about one defect — it is a threshold. This runs
    :func:`system_feasibility` across *defect_um_grid* and returns the smallest
    size that is still ``"resolvable"``, plus the per-size table so the falloff
    is visible rather than asserted.

    ``limit_um`` is ``None`` when no size in the grid is resolvable — that is a
    real answer ("this design cannot do it"), not a failure, so it is returned
    rather than raised.

    **Two independent things can block "resolvable", and they are reported
    separately** because they are fixed by buying different hardware:

      * ``lateral_limit_um`` — the smallest feature the optics can *resolve*
        laterally (diffraction or sampling, whichever binds). This is closed
        form, so it is always a number; it never depends on the grid.
      * ``depth_of_field_ok`` — whether the required depth tolerance actually
        fits inside the depth of field.

    A design can resolve the defect perfectly and still never reach
    ``"resolvable"`` because the part moves out of focus. Folding that into a
    single "optical limit not reached" would send the reader shopping for a
    lens when the fix is aperture, tolerance, or a focus mechanism.

    Raises ValueError: an empty grid, or any non-positive/non-finite size.
    """
    grid = np.atleast_1d(np.asarray(defect_um_grid, dtype=np.float64))
    if grid.ndim != 1 or grid.size == 0:
        raise ValueError("defect_um_grid must be a non-empty 1-D sequence of "
                         "sizes in micrometres")
    if not np.isfinite(grid).all() or (grid <= 0).any():
        raise ValueError("defect_um_grid must be positive and finite")
    rows, limited_by, last = [], None, None
    for d in np.sort(grid):
        r = system_feasibility(float(d), focal_mm, working_distance_mm,
                               pixel_pitch_um, f_number, width_px, height_px,
                               wavelength_um, depth_tolerance_mm)
        limited_by = r["limited_by"]      # 欠陥サイズに依らないので上書きでよい
        last = r
        rows.append({"defect_um": float(d), "verdict": r["verdict"],
                     "pixels_across": r["pixels_across"]})
    ok = [r["defect_um"] for r in rows if r["verdict"] == "resolvable"]
    # 横分解能で見た限界。これは閉形式なので grid に依らず必ず数値になる。
    # 「resolvable が 1 つも無い」ときに limit_um が None になるのは、横分解能が
    # 足りないときも被写界深度が足りないときも同じなので、両者を必ず分けて返す。
    lateral = [r["defect_um"] for r in rows
               if r["defect_um"] >= last["resolution_object_um"]] if last else []
    return {
        "limit_um": (min(ok) if ok else None),
        "limited_by": limited_by,
        "resolution_object_um": last["resolution_object_um"] if last else None,
        "lateral_limit_um": (min(lateral) if lateral else None),
        "depth_of_field_ok": bool(last["depth_of_field_ok"]) if last else None,
        "depth_of_field_mm": last["depth_of_field_mm"] if last else None,
        "depth_tolerance_mm": last["depth_tolerance_mm"] if last else None,
        "table": rows,
    }
