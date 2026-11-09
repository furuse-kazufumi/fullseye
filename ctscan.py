# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""X-ray CT scan geometries on one shared projector: cone, helical, laminography and more.

:mod:`tomography` reconstructs parallel-beam slices. Industrial CT is a cone beam on a
flat panel, and a helix, a tilted laminography orbit, a fan, a short scan, an offset
detector and a tomosynthesis arc are the same physics with different positions. So
this module has **one description of a scan** and no per-scan projector:

    ct_scan_geometry(scan, ...) -> dict
        per view: source (or ray direction), detector centre, detector u and v axes

:mod:`tomography_gpu` holds the only three kernels, and they read that dict. What a
scan adds here is its orbit and its weight, nothing else:

    scan              reconstruction                                  weight it adds
    ----------------  ----------------------------------------------  ------------------
    cone (circular)   FDK (Feldkamp, Davis & Kress 1984)              cosine, 1/U^2
    fan               same formula with one row                       cosine, 1/U^2
    short scan        same, arc < 360                                 Parker 1982
    offset detector   same, 360 degrees with half the fan             Wang 2002
    helical           FDK per voxel over the views that see it        detector-row Q
    laminography      same, tilted orbit                              sin(tilt)
    parallel          same, no divergence                             none
    tomosynthesis     no exact inversion: SIRT, OS-SART or TV         -
    few views, limited angle   SIRT, OS-SART or TV                    -

Dual energy is two scans of one geometry, separated into two basis materials in the
projection domain (Alvarez & Macovski 1976) and reconstructed by any route above.

**Ground truth is closed form.** The line integral through a uniform ellipsoid is a
chord length, so :func:`ellipsoid_projections` gives the exact data for any geometry
here, with no projector involved, and :func:`shepp_logan_3d` the voxels they describe.

**Coordinates.** Physical units, origin at the volume centre.
``x = col - (W-1)/2``, ``y = row - (H-1)/2``, ``z = slice - (Z-1)/2``, each times the
voxel size. A volume is ``(Z, Y, X)``. Projections are ``(view, V, U)``, which is
deliberately not the ``(slice, angle, detector)`` of a parallel ``sinostack``: the two
are both 3-D float arrays, so they are separate sorts in :mod:`opstomography`.

**Line integrals in, attenuation out.** The input is ``-log(I/I0)`` in units of
1/voxel-unit times length, and the output is an attenuation coefficient.

Honest disclosure, measured in ``docs/perf/gpu_ct_2026-11-02.md``:

  * **FDK is exact only in the mid-plane.** Above it a circular orbit does not measure
    the data (Tuy's condition fails), and the error grows with the cone angle. That
    growth is a gate here, not a surprise.
  * **Helical is an approximate rule.** It is not Katsevich's exact inversion; the
    ramp filter runs along detector rows and the redundancy is a smooth window.
  * **Laminography and tomosynthesis do not measure a cone of frequencies** around the
    axis, so depth resolution is lost and no filter returns it.
  * **The short-scan and offset weights are 2-D weights** applied to a cone beam;
    above the mid-plane they are approximate as FDK itself is.

Provenance, public literature only:

  * L. A. Feldkamp, L. C. Davis & J. W. Kress, "Practical cone-beam algorithm",
    *J. Opt. Soc. Am. A* 1(6):612-619, 1984.
  * D. L. Parker, "Optimal short scan convolution reconstruction for fan-beam CT",
    *Med. Phys.* 9(2):254-257, 1982.
  * G. Wang, "X-ray micro-CT with a displaced detector array", *Med. Phys.*
    29(7):1634-1636, 2002.
  * G. Wang, T.-H. Lin, P. C. Cheng & D. M. Shinozaki, "A general cone-beam
    reconstruction algorithm", *IEEE Trans. Med. Imaging* 12(3):486-496, 1993.
  * K. Stierstorfer, A. Rauscher, J. Boese, H. Bruder, S. Schaller & T. Flohr,
    "Weighted FBP - a simple approximate 3D FBP algorithm for multislice spiral CT",
    *Phys. Med. Biol.* 49(11):2209-2218, 2004.
  * A. Myagotin, A. Voropaev, L. Helfen, D. Hanschke & T. Baumbach, "Efficient volume
    reconstruction for parallel-beam computed laminography by filtered backprojection
    on multiple graphics processing units", *IEEE Trans. Image Process.* 22(12), 2013.
  * P. Gilbert, "Iterative methods for the three-dimensional reconstruction of an
    object from projections", *J. Theor. Biol.* 36(1):105-117, 1972 (SIRT).
  * G. Wang & M. Jiang, "Ordered-subset simultaneous algebraic reconstruction
    techniques (OS-SART)", *J. X-Ray Sci. Technol.* 12(3):169-177, 2004.
  * A. Chambolle & T. Pock, "A first-order primal-dual algorithm for convex problems
    with applications to imaging", *J. Math. Imaging Vis.* 40(1):120-145, 2011.
  * E. Y. Sidky, J. H. Jorgensen & X. Pan, "Convex optimization problem prototyping for
    image reconstruction in computed tomography with the Chambolle-Pock algorithm",
    *Phys. Med. Biol.* 57(10):3065-3091, 2012.
  * R. E. Alvarez & A. Macovski, "Energy-selective reconstructions in X-ray
    computerised tomography", *Phys. Med. Biol.* 21(5):733-744, 1976.
  * A. C. Kak & M. Slaney, *Principles of Computerized Tomographic Imaging*, IEEE Press
    1988: the fan-beam formulas and the 3-D head phantom.
"""
from __future__ import annotations

import numpy as np

import tomography as _tomo
import tomography_gpu as _gpu

__all__ = [
    "ct_scan_geometry", "shepp_logan_3d", "ellipsoid_phantom", "ellipsoid_projections",
    "ct_forward_project", "ct_adjoint_project", "fdk_reconstruct", "sirt_reconstruct",
    "os_sart_reconstruct", "tv_reconstruct", "ct_dual_energy_reconstruct",
    "SCANS", "DETECTORS", "SHEPP_LOGAN_3D", "MAX_VOLUME_ELEMENTS", "CTSCAN",
]

#: The public operators, by name.
CTSCAN = [
    "ct_scan_geometry", "shepp_logan_3d", "ellipsoid_phantom", "ellipsoid_projections",
    "ct_forward_project", "ct_adjoint_project", "fdk_reconstruct", "sirt_reconstruct",
    "os_sart_reconstruct", "tv_reconstruct", "ct_dual_energy_reconstruct",
]

#: Scan orbits accepted by :func:`ct_scan_geometry`.
SCANS = ("parallel", "fan", "cone", "helical", "laminography", "tomosynthesis")

#: Detector shapes: ``flat`` is equally spaced on a plane, ``arc`` equally spaced in
#: angle on a cylinder around the source (the equiangular fan).
DETECTORS = ("flat", "arc")

#: Largest volume on the GPU route (1290^3).
MAX_VOLUME_ELEMENTS = 1 << 31

#: Largest volume on the numpy route (512^3 at float64 is 1 GB).
MAX_CPU_VOLUME_ELEMENTS = 1 << 27

#: Largest number of views in a scan.
MAX_VIEWS = 1 << 16

#: Largest number of detector samples in one projection stack (views x V x U).
MAX_PROJECTION_ELEMENTS = 1 << 33

#: Fraction of the detector half-height where the helical row window starts to fall.
HELICAL_ROW_TAPER = 0.7

#: The modified 3-D Shepp-Logan head phantom, rows ``(x0, y0, z0, a, b, c, phi_deg,
#: rho)`` in the normalised cube ``[-1, 1]^3``. The in-plane columns are the same as
#: :data:`tomography.SHEPP_LOGAN`, with the modified contrasts; the z columns follow
#: the 3-D head phantom of Kak & Slaney 1988. Only the rotation about z is kept.
SHEPP_LOGAN_3D = (
    (0.0000, 0.0000, 0.00, 0.6900, 0.9200, 0.810, 0.0, 1.00),
    (0.0000, -0.0184, 0.00, 0.6624, 0.8740, 0.780, 0.0, -0.80),
    (0.2200, 0.0000, 0.00, 0.1100, 0.3100, 0.220, -18.0, -0.20),
    (-0.2200, 0.0000, 0.00, 0.1600, 0.4100, 0.280, 18.0, -0.20),
    (0.0000, 0.3500, -0.15, 0.2100, 0.2500, 0.410, 0.0, 0.10),
    (0.0000, 0.1000, 0.25, 0.0460, 0.0460, 0.050, 0.0, 0.10),
    (0.0000, -0.1000, 0.25, 0.0460, 0.0460, 0.050, 0.0, 0.10),
    (-0.0800, -0.6050, 0.00, 0.0460, 0.0230, 0.050, 0.0, 0.10),
    (0.0000, -0.6060, 0.00, 0.0230, 0.0230, 0.020, 0.0, 0.10),
    (0.0600, -0.6050, 0.00, 0.0230, 0.0460, 0.020, 0.0, 0.10),
)


def _count(v, name, lo, hi, op):
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)):
        raise ValueError("%s: %s must be an int, got %r" % (op, name, v))
    if not lo <= int(v) <= hi:
        raise ValueError("%s: %s must be in [%d, %d], got %d" % (op, name, lo, hi, v))
    return int(v)


def _positive(v, name, op):
    x = _tomo._finite_scalar(v, name)
    if x <= 0.0:
        raise ValueError("%s: %s must be > 0, got %g" % (op, name, x))
    return x


def _unit(a):
    return a / np.linalg.norm(a, axis=-1, keepdims=True)


def _vol_shape(vol_shape, op):
    if isinstance(vol_shape, (int, np.integer)) and not isinstance(vol_shape, bool):
        vol_shape = (vol_shape, vol_shape, vol_shape)
    if len(vol_shape) != 3:
        raise ValueError("%s: vol_shape must be (Z, Y, X), got %r" % (op, vol_shape))
    shape = tuple(_count(n, "vol_shape", 1, 1 << 14, op) for n in vol_shape)
    if shape[0] * shape[1] * shape[2] > MAX_VOLUME_ELEMENTS:
        raise ValueError("%s: a %r volume is %d elements, over the %d cap"
                         % (op, shape, int(np.prod(shape, dtype=np.int64)),
                            MAX_VOLUME_ELEMENTS))
    return shape


def _orbit(angles_deg, arc_deg, start_deg, n_views, op):
    if angles_deg is not None:
        ang = np.deg2rad(np.asarray(angles_deg, dtype=np.float64).ravel())
        if ang.size < 1 or not np.all(np.isfinite(ang)):
            raise ValueError("%s: angles_deg must be finite and non-empty" % (op,))
        if ang.size > 1 and not np.all(np.diff(ang) > 0.0):
            raise ValueError("%s: angles_deg must be strictly increasing" % (op,))
        if ang.size == 1:
            return ang, np.array([2.0 * np.pi]), 360.0
        steps = np.gradient(ang)
        arc = float(np.rad2deg(ang[-1] - ang[0] + np.median(np.diff(ang))))
        return ang, steps, arc
    arc = _positive(arc_deg, "arc_deg", op)
    if arc > 360.0 + 1e-9:
        raise ValueError("%s: arc_deg must be at most 360, got %g; a helix is scan="
                         "'helical'" % (op, arc))
    ang = np.deg2rad(_tomo._finite_scalar(start_deg, "start_deg")
                     + arc * np.arange(n_views) / n_views)
    return ang, np.full(n_views, np.deg2rad(arc) / n_views), arc


def ct_scan_geometry(scan="cone", n_views=360, n_u=256, n_v=256, vol_shape=(256, 256, 256),
                     voxel=1.0, du=None, dv=None, dso=None, dsd=None, detector="flat",
                     arc_deg=None, start_deg=0.0, angles_deg=None, offset_u=0.0, pitch=1.0,
                     turns=None, tilt_deg=30.0):
    """Describe one CT scan: per view, where the source and the detector are.

    Every other operator in this family reads this dict and nothing else, so a new
    scan is a new orbit here and never a new projector. The result carries, for each
    view, ``source`` (for a parallel beam the ray direction), ``det_center``, ``det_u``
    and ``det_v`` in physical units with the origin at the volume centre.

    The orbits. ``"cone"`` is a circle around the z axis with a flat panel, the
    industrial default; ``"fan"`` the same with a single detector row, for a single
    slice; ``"helical"`` the cone with the source and detector moving along z, ``pitch``
    detector heights per turn; ``"laminography"`` a circle tilted so that the beam meets
    the board normal at ``tilt_deg`` (90 is an ordinary CT, and ``dso=None`` with
    ``scan="laminography"`` is the parallel-beam form); ``"tomosynthesis"`` a source arc
    of ``arc_deg`` over a detector that does not move; ``"parallel"`` parallel rays.

    A short scan is ``arc_deg < 360``, a few-view scan a small ``n_views``, a
    limited-angle scan a small ``arc_deg`` or an explicit ``angles_deg``, and an
    offset detector ``offset_u`` bins. Those are parameters of the orbit, not new scans.

    :param scan: one of :data:`SCANS`.
    :param n_views: views, ``1 .. 65536``; ignored when *angles_deg* is given.
    :param n_u: detector columns.
    :param n_v: detector rows.
    :param vol_shape: ``(Z, Y, X)`` of the reconstruction, or one int for a cube.
    :param voxel: voxel edge in physical units.
    :param du: detector column pitch; ``None`` gives one voxel at the isocentre.
    :param dv: detector row pitch; ``None`` gives one voxel at the isocentre.
    :param dso: source to isocentre distance; ``None`` gives 3 volume widths.
    :param dsd: source to detector distance; ``None`` gives ``2 * dso``.
    :param detector: one of :data:`DETECTORS`.
    :param arc_deg: orbit length; ``None`` gives 360, or 180 for ``"parallel"``, or 40
        for ``"tomosynthesis"``.
    :param start_deg: first view angle.
    :param angles_deg: explicit increasing view angles; overrides *n_views* and *arc_deg*.
    :param offset_u: detector shift in bins along u, for an extended field of view.
    :param pitch: helical table feed per turn, in detector heights at the isocentre.
    :param turns: helical turns; ``None`` covers the volume height.
    :param tilt_deg: laminography angle between the beam and the rotation axis.
    :returns: geometry dict; ``vol_shape``, ``n_views``, ``n_v``, ``n_u`` and the per-view
        arrays are the public fields.
    :raises ValueError: on an unknown scan or detector, a non-positive length, a source
        inside the volume, ``arc`` above 360, or an oversized request.
    """
    op = "ct_scan_geometry"
    kind = _tomo._choice(scan, SCANS, "scan", op)
    det = _tomo._choice(detector, DETECTORS, "detector", op)
    n_u = _count(n_u, "n_u", 1, 1 << 15, op)
    n_v = _count(n_v, "n_v", 1, 1 << 15, op)
    n_views = _count(n_views, "n_views", 1, MAX_VIEWS, op)
    shape = _vol_shape(vol_shape, op)
    voxel = _positive(voxel, "voxel", op)
    width = max(shape[1], shape[2]) * voxel
    extent = 0.5 * voxel * float(np.sqrt(shape[0] ** 2 + shape[1] ** 2 + shape[2] ** 2))
    parallel = kind == "parallel" or (kind == "laminography" and dso is None)
    if parallel:
        if det != "flat":
            raise ValueError("%s: a parallel beam has no arc detector" % (op,))
        d_so = d_sd = None
        mag = 1.0
    else:
        d_so = 3.0 * width if dso is None else _positive(dso, "dso", op)
        d_sd = 2.0 * d_so if dsd is None else _positive(dsd, "dsd", op)
        if d_so <= extent:
            raise ValueError(
                "%s: dso=%g puts the source inside the %.1f radius of the volume, where "
                "a ray has no direction" % (op, d_so, extent))
        if d_sd <= d_so:
            raise ValueError("%s: dsd=%g must exceed dso=%g" % (op, d_sd, d_so))
        mag = d_sd / d_so
    d_u = voxel * mag if du is None else _positive(du, "du", op)
    d_v = voxel * mag if dv is None else _positive(dv, "dv", op)
    off = _tomo._finite_scalar(offset_u, "offset_u")
    if abs(off) >= 0.5 * n_u and n_u > 1:
        raise ValueError("%s: offset_u=%g moves the rotation axis off the detector"
                         % (op, off))
    if kind == "fan" and n_v != 1:
        raise ValueError("%s: scan='fan' has one detector row, got n_v=%d" % (op, n_v))
    if kind == "fan" and shape[0] != 1:
        raise ValueError("%s: scan='fan' reconstructs one slice, got %r" % (op, shape))

    arc = arc_deg
    if arc is None:
        arc = {"parallel": 180.0, "tomosynthesis": 40.0}.get(kind, 360.0)
    geom = {
        "kind": "ct_geometry", "scan": kind, "beam": "parallel" if parallel else "cone",
        "detector": det, "vol_shape": shape, "voxel": voxel, "n_u": n_u, "n_v": n_v,
        "du": d_u, "dv": d_v, "dso": d_so, "dsd": d_sd,
        "cu": (n_u - 1) / 2.0 - off, "cv": (n_v - 1) / 2.0, "offset_u": off,
    }
    if kind == "helical":
        height = n_v * d_v / mag
        feed = _positive(pitch, "pitch", op) * height
        if turns is None:
            n_turns = (shape[0] * voxel + height) / feed
        else:
            n_turns = _positive(turns, "turns", op)
        beta = np.deg2rad(_tomo._finite_scalar(start_deg, "start_deg")
                          + 360.0 * n_turns * np.arange(n_views) / n_views)
        steps = np.full(n_views, 2.0 * np.pi * n_turns / n_views)
        z = feed * (beta - beta.mean()) / (2.0 * np.pi)
        arc_val = 360.0 * n_turns
        geom.update({"pitch": float(pitch), "turns": n_turns})
    else:
        beta, steps, arc_val = _orbit(angles_deg, arc, start_deg, n_views, op)
        z = np.zeros_like(beta)
    n = beta.size
    cb, sb = np.cos(beta), np.sin(beta)
    zero = np.zeros(n)
    u = np.stack([cb, sb, zero], axis=1)
    normal = np.stack([-sb, cb, zero], axis=1)
    v = np.tile(np.array([0.0, 0.0, 1.0]), (n, 1))
    if kind == "laminography":
        tilt = np.deg2rad(_positive(tilt_deg, "tilt_deg", op))
        if tilt > 0.5 * np.pi + 1e-9:
            raise ValueError("%s: tilt_deg must be at most 90, got %g" % (op, tilt_deg))
        down = np.array([0.0, 0.0, -1.0])
        ray = np.sin(tilt) * normal + np.cos(tilt) * down
        v = np.cos(tilt) * normal - np.sin(tilt) * down
        normal = ray
        geom["tilt_deg"] = float(tilt_deg)
    if kind == "tomosynthesis":
        s = np.stack([d_so * np.sin(beta), zero, d_so * np.cos(beta)], axis=1)
        c = np.tile(np.array([0.0, 0.0, d_so - d_sd]), (n, 1))
        u = np.tile(np.array([1.0, 0.0, 0.0]), (n, 1))
        v = np.tile(np.array([0.0, 1.0, 0.0]), (n, 1))
    elif parallel:
        s = normal
        c = np.zeros((n, 3))
    else:
        offset = np.stack([zero, zero, z], axis=1)
        s = -d_so * normal + offset
        c = (d_sd - d_so) * normal + offset
    geom.update({
        "n_views": n, "angles_rad": beta, "view_steps": steps, "arc_deg": float(arc_val),
        "source": s, "det_center": c, "det_u": u, "det_v": v,
        "planar": parallel and kind == "parallel" and d_v == voxel and n_v == shape[0],
    })
    if shape[0] == 1 and kind in ("fan", "parallel") and n_v == 1:
        geom["planar"] = True
    n_elem = n * n_v * n_u
    if n_elem > MAX_PROJECTION_ELEMENTS:
        raise ValueError("%s: %d views x %d x %d = %d detector samples, over the %d cap"
                         % (op, n, n_v, n_u, n_elem, MAX_PROJECTION_ELEMENTS))
    return geom


def _check_geometry(geometry, op):
    if not isinstance(geometry, dict) or geometry.get("kind") != "ct_geometry":
        raise ValueError("%s: geometry must come from ct_scan_geometry, got %s"
                         % (op, type(geometry).__name__))
    return geometry


def _check_projections(projections, geom, op, name="projections"):
    a = np.asarray(projections)
    if a.size == 0:
        raise ValueError("%s: %s is empty" % (op, name))
    if not np.issubdtype(a.dtype, np.number) or np.iscomplexobj(a):
        raise ValueError("%s: %s must be real numbers, got %s" % (op, name, a.dtype))
    want = (geom["n_views"], geom["n_v"], geom["n_u"])
    if a.shape != want:
        raise ValueError(
            "%s: %s has shape %r but the geometry describes (view, V, U) = %r. A "
            "(slice, angle, detector) stack is not this layout" % (op, name, a.shape, want))
    if not np.all(np.isfinite(a)):
        raise ValueError("%s: %s contains non-finite values" % (op, name))
    return a


def _check_volume(volume, geom, op):
    a = np.asarray(volume)
    if a.size == 0:
        raise ValueError("%s: volume is empty" % (op,))
    if a.shape != tuple(geom["vol_shape"]):
        raise ValueError("%s: volume has shape %r but the geometry describes %r"
                         % (op, a.shape, tuple(geom["vol_shape"])))
    if not np.all(np.isfinite(a)):
        raise ValueError("%s: volume contains non-finite values" % (op,))
    return a


def _check_device(geom, device, op):
    dev = _gpu.resolve_device(device)
    n = int(np.prod(geom["vol_shape"], dtype=np.int64))
    if dev == "cpu" and n > MAX_CPU_VOLUME_ELEMENTS:
        raise ValueError(
            "%s: a %r volume is over the %d element cap of the numpy route; it needs a "
            "GPU" % (op, tuple(geom["vol_shape"]), MAX_CPU_VOLUME_ELEMENTS))
    return dev


def _as_ellipsoids(ellipsoids, op):
    table = SHEPP_LOGAN_3D if ellipsoids is None else ellipsoids
    e = np.asarray(table, dtype=np.float64)
    if e.ndim != 2 or e.shape[1] != 8 or e.shape[0] < 1:
        raise ValueError("%s: ellipsoids must be (N, 8) rows (x0, y0, z0, a, b, c, phi_deg, "
                         "rho), got shape %r" % (op, e.shape))
    if not np.all(np.isfinite(e)) or np.any(e[:, 3:6] <= 0.0):
        raise ValueError("%s: ellipsoids need finite values and positive semi-axes" % (op,))
    return e


def ellipsoid_phantom(shape=(128, 128, 128), ellipsoids=None, supersample=2):
    """Rasterise a sum of uniform ellipsoids onto a ``(Z, Y, X)`` grid.

    The normalised cube ``[-1, 1]^3`` maps onto the grid with half-width ``X/2`` voxels
    on every axis, so voxels stay cubic. Each voxel is the mean of ``supersample^3``
    sub-samples, so an edge voxel carries its true volume fraction.

    :param shape: ``(Z, Y, X)``, or one int for a cube.
    :param ellipsoids: ``(N, 8)`` rows; ``None`` gives :data:`SHEPP_LOGAN_3D`.
    :param supersample: anti-alias factor per axis, ``1 .. 4``.
    :returns: float64 volume.
    :raises ValueError: on a degenerate ellipsoid or an oversized grid.
    """
    op = "ellipsoid_phantom"
    nz, ny, nx = _vol_shape(shape, op)
    ss = _count(supersample, "supersample", 1, 4, op)
    if nz * ny * nx * ss ** 2 > MAX_CPU_VOLUME_ELEMENTS:
        raise ValueError("%s: %r with supersample=%d is over the cap" % (op, (nz, ny, nx), ss))
    ell = _as_ellipsoids(ellipsoids, op)
    half = nx / 2.0
    sub = (np.arange(ss, dtype=np.float64) + 0.5) / ss - 0.5
    xs = ((np.arange(nx, dtype=np.float64)[:, None] + sub).ravel() - (nx - 1) / 2.0) / half
    ys = ((np.arange(ny, dtype=np.float64)[:, None] + sub).ravel() - (ny - 1) / 2.0) / half
    zs = ((np.arange(nz, dtype=np.float64)[:, None] + sub).ravel() - (nz - 1) / 2.0) / half
    out = np.zeros((nz, ny, nx), dtype=np.float64)
    xg = xs[None, :]
    yg = ys[:, None]
    for k in range(nz):
        plane = np.zeros((ny * ss, nx * ss), dtype=np.float64)
        for j in range(ss):
            z = zs[k * ss + j]
            for x0, y0, z0, a, b, c, phi, rho in ell:
                rest = 1.0 - ((z - z0) / c) ** 2
                if rest <= 0.0:
                    continue
                ph = np.deg2rad(phi)
                cp, sp = np.cos(ph), np.sin(ph)
                dx = xg - x0
                dy = yg - y0
                p = dx * cp + dy * sp
                q = -dx * sp + dy * cp
                plane += np.where((p / a) ** 2 + (q / b) ** 2 <= rest, rho, 0.0)
        out[k] = plane.reshape(ny, ss, nx, ss).mean(axis=(1, 3)) / ss
    return out


def shepp_logan_3d(size=128, supersample=2):
    """The modified 3-D Shepp-Logan head phantom on a ``size``-cube.

    The in-plane ellipses are those of :data:`tomography.SHEPP_LOGAN`, with extents
    along z, so a CT reconstruction has an exact volume to be measured against, and
    :func:`ellipsoid_projections` has the exact data for it.

    :param size: edge of the cube, ``2 .. 1024``; or ``(Z, Y, X)``.
    :param supersample: anti-alias factor per axis, ``1 .. 4``.
    :returns: float64 volume spanning ``[0, 1]``.
    :raises ValueError: on an oversized grid.
    """
    return ellipsoid_phantom(size, None, supersample)


def ellipsoid_projections(geometry, ellipsoids=None, device="auto"):
    """Exact line integrals of a sum of ellipsoids, for any scan in this family.

    Each ray is mapped to the frame where the ellipsoid is a unit sphere, and the
    chord length comes from the quadratic's discriminant. No voxels, no interpolation
    and no projector are involved, which is what makes this the ground truth the
    projector and every reconstruction here are measured against.

    :param geometry: dict from :func:`ct_scan_geometry`.
    :param ellipsoids: ``(N, 8)`` rows; ``None`` gives :data:`SHEPP_LOGAN_3D`.
    :param device: ``"auto"``, ``"cpu"`` or ``"cuda"``.
    :returns: ``(view, V, U)`` float array.
    :raises ValueError: on a geometry not from :func:`ct_scan_geometry`.
    """
    op = "ellipsoid_projections"
    geom = _check_geometry(geometry, op)
    ell = _as_ellipsoids(ellipsoids, op)
    b = _gpu._backend(device)
    nv = geom["n_v"]
    half = geom["vol_shape"][2] * geom["voxel"] / 2.0
    out = b.zeros((geom["n_views"], nv, geom["n_u"]))
    rows = max(1, int(b.sample_budget(32 * len(ell)) // geom["n_u"]))
    for i in range(geom["n_views"]):
        for r0 in range(0, nv, rows):
            r1 = min(r0 + rows, nv)
            ox, oy, oz, dx, dy, dz = _gpu._rays(b, geom, i, r0, r1)
            acc = 0.0
            for x0, y0, z0, a, bb, c, phi, rho in ell:
                ph = np.deg2rad(phi)
                cp, sp = float(np.cos(ph)), float(np.sin(ph))
                wx = ox - x0 * half
                wy = oy - y0 * half
                wz = oz - z0 * half
                px = (wx * cp + wy * sp) / (a * half)
                py = (-wx * sp + wy * cp) / (bb * half)
                pz = wz / (c * half)
                qx = (dx * cp + dy * sp) / (a * half)
                qy = (-dx * sp + dy * cp) / (bb * half)
                qz = dz / (c * half)
                aa = qx * qx + qy * qy + qz * qz
                hb = px * qx + py * qy + pz * qz
                cc = px * px + py * py + pz * pz - 1.0
                disc = hb * hb - aa * cc
                acc = acc + _sqrt_pos(b, disc) * 2.0 * rho / aa
            out[i, r0:r1] = acc
    return b.host(out)


def _sqrt_pos(b, a):
    if b.name == "cuda":
        return b.torch.sqrt(a.clamp_min(0.0))
    return np.sqrt(np.maximum(a, 0.0))


def ct_forward_project(volume, geometry, device="auto"):
    """Project a volume along every ray of *geometry*: the discrete operator ``A``.

    Rays are sampled at one voxel step, trilinearly, a sample outside the volume
    counting zero. For a parallel slice this is the definition of
    :func:`tomography.radon_transform`.

    :param volume: ``(Z, Y, X)`` of the geometry's ``vol_shape``.
    :param geometry: dict from :func:`ct_scan_geometry`.
    :param device: ``"auto"``, ``"cpu"`` or ``"cuda"``.
    :returns: ``(view, V, U)`` float array of line integrals.
    :raises ValueError: on a shape that disagrees with the geometry. Empty input
        (``volume`` with 0 elements) raises ``ValueError``.
    """
    op = "ct_forward_project"
    geom = _check_geometry(geometry, op)
    vol = _check_volume(volume, geom, op)
    return _gpu.forward_project(vol, geom, device=_check_device(geom, device, op))


def ct_adjoint_project(projections, geometry, device="auto"):
    """The exact transpose ``A^T`` of :func:`ct_forward_project`.

    ``<A x, y> = <x, A^T y>`` holds to rounding, on every scan. This is what an
    iterative solver needs; it is not the reconstruction :func:`fdk_reconstruct` does.

    :param projections: ``(view, V, U)`` array.
    :param geometry: dict from :func:`ct_scan_geometry`.
    :param device: ``"auto"``, ``"cpu"`` or ``"cuda"``.
    :returns: ``(Z, Y, X)`` float volume.
    :raises ValueError: on a shape that disagrees with the geometry. Empty input
        (``projections`` with 0 elements) raises ``ValueError``.
    """
    op = "ct_adjoint_project"
    geom = _check_geometry(geometry, op)
    proj = _check_projections(projections, geom, op)
    return _gpu.adjoint_project(proj, geom, device=_check_device(geom, device, op))


def _fan_angles(geom):
    """Per detector column: the fan angle of the column at the source, in radians."""
    u = (np.arange(geom["n_u"], dtype=np.float64) - geom["cu"]) * geom["du"]
    if geom["detector"] == "arc":
        return u / geom["dsd"]
    return np.arctan(u / geom["dsd"])


def _cosine_weight(geom):
    """The ``(V, U)`` pre-weight: cosine of the ray angle at the source."""
    u = (np.arange(geom["n_u"], dtype=np.float64) - geom["cu"]) * geom["du"]
    v = (np.arange(geom["n_v"], dtype=np.float64) - geom["cv"]) * geom["dv"]
    uu = u[None, :]
    vv = v[:, None]
    dsd = geom["dsd"]
    if geom["detector"] == "arc":
        return np.cos(uu / dsd) * dsd / np.sqrt(dsd * dsd + vv * vv)
    return dsd / np.sqrt(dsd * dsd + uu * uu + vv * vv)


def _parker(beta, gamma, half_fan):
    """Parker's short-scan weight, ``(views, columns)``, on ``0 .. pi + 2 half_fan``.

    The conjugate of a ray ``(beta, gamma)`` is at ``beta + pi + 2 gamma`` with
    ``-gamma``, and the two weights sum to 1.
    """
    b = beta[:, None]
    g = gamma[None, :]
    w = np.ones((beta.size, gamma.size))
    up = b < 2.0 * (half_fan - g)
    down = b > np.pi - 2.0 * g
    with np.errstate(divide="ignore", invalid="ignore"):
        rise = np.sin(0.25 * np.pi * b / (half_fan - g)) ** 2
        fall = np.sin(0.25 * np.pi * (np.pi + 2.0 * half_fan - b) / (half_fan + g)) ** 2
    w = np.where(up, rise, w)
    w = np.where(down, fall, w)
    return np.clip(np.nan_to_num(w), 0.0, 1.0)


def _displaced(gamma, offset_sign):
    """Wang's displaced-detector weight, ``(columns,)``; ``w(g) + w(-g) = 1``."""
    g = gamma * offset_sign
    g0 = float(np.abs(g.min()))
    a = np.clip(g / g0, -1.0, 1.0)
    w = np.sin(0.25 * np.pi * (1.0 + a)) ** 2
    return np.where(g >= g0, 1.0, w)


def _redundancy(geom, allow_incomplete, op):
    """The ``(views, columns)`` weight and the name of the rule that made it.

    Full 360-degree data measures every line twice, hence 1/2. A short scan and an
    offset detector measure part of the lines once, hence a weight between 0 and 1
    where the pair sums to 1.
    """
    n, nu = geom["n_views"], geom["n_u"]
    arc = np.deg2rad(geom["arc_deg"])
    full = geom["arc_deg"] >= 360.0 - 1e-6
    if geom["beam"] == "parallel":
        if full:
            return np.full((n, nu), 0.5), "full"
        if geom["scan"] == "laminography":
            raise ValueError("%s: filtered laminography needs a full 360-degree orbit, got "
                             "%g; use sirt_reconstruct" % (op, geom["arc_deg"]))
        if geom["arc_deg"] < 180.0 - 1e-6 and not allow_incomplete:
            raise ValueError("%s: a parallel scan needs 180 degrees, got %g; use "
                             "sirt_reconstruct or tv_reconstruct, or pass "
                             "allow_incomplete=True" % (op, geom["arc_deg"]))
        return np.ones((n, nu)), "half-turn"
    gamma = _fan_angles(geom)
    half_fan = float(np.max(np.abs(gamma)))
    offset = geom.get("offset_u", 0.0)
    if full:
        if offset != 0.0:
            return np.tile(_displaced(gamma, np.sign(offset)), (n, 1)), "displaced"
        return np.full((n, nu), 0.5), "full"
    if offset != 0.0:
        raise ValueError("%s: an offset detector needs a full 360-degree orbit, got %g"
                         % (op, geom["arc_deg"]))
    need = np.pi + 2.0 * half_fan
    if arc < need - 2.0 * np.pi / max(n, 1):
        if not allow_incomplete:
            raise ValueError(
                "%s: an arc of %g degrees is under the short-scan minimum of %.2f (180 + "
                "the full fan). These data do not determine the object: use "
                "sirt_reconstruct or tv_reconstruct, or pass allow_incomplete=True"
                % (op, geom["arc_deg"], np.rad2deg(need)))
        return np.ones((n, nu)), "incomplete"
    beta = geom["angles_rad"] - geom["angles_rad"][0]
    return _parker(beta, -gamma, 0.5 * (arc - np.pi)), "parker"


def _helical_window(iv, cv):
    """The detector-row window of the helical rule, in ``[0, 1]``."""
    q = abs(iv - cv) / max(cv, 1.0)
    t = ((q - HELICAL_ROW_TAPER) / (1.0 - HELICAL_ROW_TAPER)).clip(0.0, 1.0)
    w = 1.0 - t * t * (3.0 - 2.0 * t)
    return w * (q < 1.0)


def fdk_reconstruct(projections, geometry, filter_name="ramp", cutoff=1.0, device="auto",
                    allow_incomplete=False):
    """Filtered back-projection for every scan with a formula: FDK and its relatives.

    The Feldkamp-Davis-Kress steps, on one code path: weight each sample by the cosine
    of its ray and by the scan's redundancy, ramp-filter along the detector rows, then
    back-project with the ``(DSO / U)^2`` weight. A fan is one row, a short scan takes
    Parker's weight, an offset detector Wang's, a helix a row window normalised per
    voxel, laminography a ``sin(tilt)`` scale, and a parallel beam has no divergence
    weight. The equiangular detector takes the ``(gamma / sin gamma)^2`` kernel.

    A scan with no formula, or an arc too short to determine the object, is refused
    and named: use :func:`sirt_reconstruct` or :func:`tv_reconstruct`.

    :param projections: ``(view, V, U)`` line integrals.
    :param geometry: dict from :func:`ct_scan_geometry`.
    :param filter_name: one of :data:`tomography.FILTERS` except ``"none"``.
    :param cutoff: fraction of Nyquist to keep, ``(0, 1]``.
    :param device: ``"auto"``, ``"cpu"`` or ``"cuda"``.
    :param allow_incomplete: reconstruct an arc under the minimum anyway. The result
        is missing a wedge of the object and the density reads low.
    :returns: ``(Z, Y, X)`` float attenuation volume.
    :raises ValueError: on a shape that disagrees with the geometry, a tomosynthesis
        scan, or an incomplete arc. Empty input (``projections`` with 0 elements) raises
        ``ValueError``.
    """
    op = "fdk_reconstruct"
    geom = _check_geometry(geometry, op)
    proj = _check_projections(projections, geom, op)
    dev = _check_device(geom, device, op)
    kind = _tomo._choice(filter_name, _tomo.FILTERS, "filter_name", op)
    if kind == "none":
        raise ValueError("%s: filter_name='none' is an unfiltered back-projection, which "
                         "has no absolute scale; use ct_adjoint_project" % (op,))
    cut = _tomo._finite_scalar(cutoff, "cutoff")
    if not 0.0 < cut <= 1.0:
        raise ValueError("%s: cutoff must be in (0, 1], got %g" % (op, cut))
    if geom["scan"] == "tomosynthesis":
        raise ValueError("%s: tomosynthesis has no inversion formula here; use "
                         "sirt_reconstruct or tv_reconstruct" % (op,))
    b = _gpu._backend(dev)
    real = np.float64 if dev == "cpu" else np.float32
    data = np.asarray(proj, dtype=real)
    helical = geom["scan"] == "helical"
    if helical:
        weight = None
    else:
        red, _rule = _redundancy(geom, bool(allow_incomplete), op)
        weight = red.astype(real)
    parallel = geom["beam"] == "parallel"
    if parallel:
        tau = geom["du"]
        d_gamma = None
    else:
        tau = geom["du"] * geom["dso"] / geom["dsd"]
        d_gamma = geom["du"] / geom["dsd"] if geom["detector"] == "arc" else None
        data = data * _cosine_weight(geom).astype(real)[None, :, :]
    if weight is not None:
        data = data * weight[:, None, :]
    filtered = _gpu._filter_rows(b, data, kind, cut, d_gamma)
    scale = 1.0 / tau
    if geom["scan"] == "laminography":
        scale *= float(np.sin(np.deg2rad(geom["tilt_deg"])))
    steps = geom["view_steps"] * scale
    normalize = None
    if helical:
        cv = geom["cv"]

        def normalize(iv):
            return _helical_window(iv, cv)

    return b.host(_gpu._voxel_backproject(b, filtered, geom, steps, normalize, False))


def _subsets(n_views, n_subsets):
    """Interleaved view subsets, visited in bit-reversed order."""
    order = [int(format(k, "b").zfill(16)[::-1], 2) for k in range(n_subsets)]
    order = [k for _, k in sorted(zip(order, range(n_subsets)))]
    return [np.arange(k, n_views, n_subsets) for k in order]


def _iter_args(projections, geometry, device, n_iter, relaxation, initial, nonnegative, op):
    geom = _check_geometry(geometry, op)
    proj = _check_projections(projections, geom, op)
    dev = _check_device(geom, device, op)
    n_it = _count(n_iter, "n_iter", 1, 5000, op)
    lam = _tomo._finite_scalar(relaxation, "relaxation")
    if not 0.0 < lam < 2.0:
        raise ValueError("%s: relaxation must be in (0, 2), got %g" % (op, lam))
    if not isinstance(nonnegative, (bool, np.bool_)):
        raise ValueError("%s: nonnegative must be a bool, got %r"
                         % (op, type(nonnegative).__name__))
    b = _gpu._backend(dev)
    if initial is None:
        x = b.zeros(tuple(geom["vol_shape"]))
    else:
        x = b.asarray(_check_volume(initial, geom, op))
    return geom, b, b.asarray(proj), n_it, lam, x


def _inverse(b, a, floor):
    """``1 / a`` where ``a > floor``, zero elsewhere (an unmeasured ray or voxel)."""
    mask = a > floor
    return mask * (1.0 / (a + (~mask) * 1.0))


def _clip_positive(b, x):
    return x.clamp_min(0.0) if b.name == "cuda" else np.maximum(x, 0.0)


def _report(on_iter, b, k, x):
    """Call ``on_iter(k, volume)``; True when it asks to stop.

    Only a boolean ``True`` stops: a Python ``bool`` or a ``numpy.bool_`` (what
    ``rel < 1e-3`` returns). Every other return value — ``None``, a number, a
    dict, an array — is ignored and the iteration continues, so a callback that
    records and happens to return something (``curve.append(...)`` returns None,
    ``d.setdefault(...)`` and a residual-returning lambda do not) is never cut
    short and an array return never raises. History (independent reviews
    2026-11-09): ``is True`` ignored ``numpy.True_`` (30/30 iterations ran);
    the truthiness rule that replaced it stopped value-returning recorders after
    1 of 20 iterations and raised on arrays."""
    if on_iter is None:
        return False
    r = on_iter(k, b.host(x))
    return isinstance(r, (bool, np.bool_)) and bool(r)


def sirt_reconstruct(projections, geometry, n_iter=50, relaxation=1.0, initial=None,
                     nonnegative=True, device="auto", on_iter=None):
    """SIRT: every view at once, ``x <- x + lam C A^T R (p - A x)``.

    ``R`` and ``C`` are the inverse row and column sums of ``A``. With the matched
    pair of this family it minimises a weighted least-squares error, and it needs no
    formula, so it is the route for tomosynthesis, few views and limited angle.

    :param projections: ``(view, V, U)`` line integrals.
    :param geometry: dict from :func:`ct_scan_geometry`.
    :param n_iter: iterations, ``1 .. 5000``.
    :param relaxation: step ``lam``, ``(0, 2)``.
    :param initial: starting volume; ``None`` gives zeros.
    :param nonnegative: clip to ``>= 0`` after each iteration.
    :param device: ``"auto"``, ``"cpu"`` or ``"cuda"``.
    :param on_iter: optional ``on_iter(iteration, volume)`` for a convergence curve;
        returning a boolean ``True`` (``bool`` or ``numpy.bool_``) stops after
        that iteration; any other return value (``None``, numbers, dicts,
        arrays) is ignored.
    :returns: ``(Z, Y, X)`` float volume.
    :raises ValueError: on a shape that disagrees with the geometry or a relaxation
        outside ``(0, 2)``. Empty input (``projections`` with 0 elements) raises
        ``ValueError``.

    **The default 50 iterations is not converged.** SIRT moves slowly. On
    consistent data (24^3 Shepp-Logan, cone, 20 views) the relative residual is
    0.0318 at 50 iterations and 0.0087 at 200, and the nRMS to the truth drops
    from 0.0407 to 0.0232 (43 %); on the measured walnut (fan, 50 views) the RMSE
    to the reference is 0.0055 /mm at 60 iterations and 0.0036 at 400 (2026-11-09
    audit). Comparing methods at the defaults makes SIRT look worse than it is.
    Choose ``n_iter`` from a curve: ``on_iter`` can compute the residual
    ``|A x - p| / |p|`` (``ct_forward_project``) or the error on held-out views,
    and return ``True`` once its relative change falls below e.g. ``1e-3``. With
    noisy data the error to the truth reaches a minimum and then rises again
    (semi-convergence), so the residual alone is not a stopping rule there.
    """
    op = "sirt_reconstruct"
    geom, b, p, n_it, lam, x = _iter_args(projections, geometry, device, n_iter, relaxation,
                                          initial, nonnegative, op)
    ones = b.zeros(tuple(geom["vol_shape"])) + 1.0
    rows = _inverse(b, _gpu._forward(b, ones, geom), 1e-6 * geom["voxel"])
    cols = _inverse(b, _gpu._adjoint(b, rows * 0.0 + 1.0, geom), 1e-6 * geom["voxel"])
    for k in range(n_it):
        resid = (p - _gpu._forward(b, x, geom)) * rows
        x = x + lam * cols * _gpu._adjoint(b, resid, geom)
        if nonnegative:
            x = _clip_positive(b, x)
        if _report(on_iter, b, k, x):
            break
    return b.host(x)


def os_sart_reconstruct(projections, geometry, n_iter=10, n_subsets=16, relaxation=0.8,
                        initial=None, nonnegative=True, device="auto", on_iter=None):
    """OS-SART: the SIRT update applied to one ordered subset of views at a time.

    One iteration passes over all subsets, so it costs about one SIRT iteration and
    moves about *n_subsets* times as far early on. With inconsistent data it settles
    into a limit cycle rather than a point.

    :param projections: ``(view, V, U)`` line integrals.
    :param geometry: dict from :func:`ct_scan_geometry`.
    :param n_iter: passes over all subsets, ``1 .. 5000``.
    :param n_subsets: subsets, ``1 .. n_views``.
    :param relaxation: step ``lam``, ``(0, 2)``.
    :param initial: starting volume; ``None`` gives zeros.
    :param nonnegative: clip to ``>= 0`` after each subset.
    :param device: ``"auto"``, ``"cpu"`` or ``"cuda"``.
    :param on_iter: optional ``on_iter(iteration, volume)``, called after each full
        pass; returning a boolean ``True`` (``bool`` or ``numpy.bool_``) stops
        there, any other return value is ignored.
    :returns: ``(Z, Y, X)`` float volume.
    :raises ValueError: on a shape that disagrees with the geometry, a relaxation
        outside ``(0, 2)``, or more subsets than views. Empty input (``projections``
        with 0 elements) raises ``ValueError``.

    **The default 10 passes is not converged.** On consistent data (24^3
    Shepp-Logan, cone, 20 views, 16 subsets) the relative residual is 0.0135 at
    10 passes and 0.0044 at 40, nRMS to the truth 0.0278 -> 0.0176 (37 %); on the
    measured walnut (fan, 50 views, 10 subsets) the RMSE to the reference is
    0.0048 /mm at 10 passes and 0.0036 at 40 (2026-11-09 audit). Pick the count
    from a curve (``on_iter``, see :func:`sirt_reconstruct`).
    """
    op = "os_sart_reconstruct"
    geom, b, p, n_it, lam, x = _iter_args(projections, geometry, device, n_iter, relaxation,
                                          initial, nonnegative, op)
    subs = _count(n_subsets, "n_subsets", 1, geom["n_views"], op)
    subsets = _subsets(geom["n_views"], subs)
    ones = b.zeros(tuple(geom["vol_shape"])) + 1.0
    floor = 1e-6 * geom["voxel"]
    rows = []
    cols = []
    for s in subsets:
        r = _inverse(b, _gpu._forward(b, ones, geom, s), floor)
        rows.append(r)
        cols.append(_inverse(b, _gpu._adjoint(b, r * 0.0 + 1.0, geom, s), floor))
    for k in range(n_it):
        for s, r, c in zip(subsets, rows, cols):
            resid = (p[_index(b, s)] - _gpu._forward(b, x, geom, s)) * r
            x = x + lam * c * _gpu._adjoint(b, resid, geom, s)
            if nonnegative:
                x = _clip_positive(b, x)
        if _report(on_iter, b, k, x):
            break
    return b.host(x)


def _index(b, s):
    return s if b.name == "cpu" else b.torch.as_tensor(s, device=b.device)


def _grad(b, x):
    """Forward differences on the axes longer than 1; ``(axes, Z, Y, X)``."""
    parts = []
    for axis in range(3):
        if x.shape[axis] < 2:
            continue
        d = b.zeros(x.shape)
        lo = [slice(None)] * 3
        hi = [slice(None)] * 3
        lo[axis] = slice(0, -1)
        hi[axis] = slice(1, None)
        d[tuple(lo)] = x[tuple(hi)] - x[tuple(lo)]
        parts.append(d)
    return parts


def _grad_t(b, parts, shape):
    """The transpose of :func:`_grad`."""
    out = b.zeros(shape)
    used = [a for a in range(3) if shape[a] >= 2]
    for axis, d in zip(used, parts):
        lo = [slice(None)] * 3
        hi = [slice(None)] * 3
        lo[axis] = slice(0, -1)
        hi[axis] = slice(1, None)
        out[tuple(lo)] = out[tuple(lo)] - d[tuple(lo)]
        out[tuple(hi)] = out[tuple(hi)] + d[tuple(lo)]
    return out


def _operator_norm(b, geom, n=8):
    """``||A||`` by power iteration from a fixed start."""
    rng = np.random.default_rng(0)
    x = b.asarray(rng.standard_normal(tuple(geom["vol_shape"])))
    value = 1.0
    for _ in range(n):
        x = x / float((x * x).sum()) ** 0.5
        y = _gpu._adjoint(b, _gpu._forward(b, x, geom), geom)
        value = float((x * y).sum()) ** 0.5
        x = y
    return value


def tv_reconstruct(projections, geometry, tv_weight=3e-4, n_iter=200, initial=None,
                   nonnegative=True, device="auto", on_iter=None):
    """Total-variation reconstruction by the Chambolle-Pock primal-dual method.

    Solves ``min 0.5 ||A x - p||^2 + w ||grad x||_1`` with ``x >= 0``, in the form Sidky,
    Jorgensen & Pan 2012 give for CT. The prior says that the object is piecewise
    constant, which is what lets it fill data that was never measured: few views and
    limited angle. On an object that is not piecewise constant it paints the same
    flat patches, so a low residual here is not evidence of truth.

    *tv_weight* is in units of ``||A||^2`` times the volume scale, so that one value
    behaves alike across grid sizes.

    :param projections: ``(view, V, U)`` line integrals.
    :param geometry: dict from :func:`ct_scan_geometry`.
    :param tv_weight: strength of the prior, ``>= 0``.
    :param n_iter: primal-dual iterations, ``1 .. 5000``.
    :param initial: starting volume; ``None`` gives zeros.
    :param nonnegative: enforce ``x >= 0``.
    :param device: ``"auto"``, ``"cpu"`` or ``"cuda"``.
    :param on_iter: optional ``on_iter(iteration, volume)``; returning a boolean
        ``True`` (``bool`` or ``numpy.bool_``) stops after that iteration, any other
        return value is ignored (same rule as :func:`sirt_reconstruct`).
    :returns: ``(Z, Y, X)`` float volume.
    :raises ValueError: on a shape that disagrees with the geometry or a negative
        weight. Empty input (``projections`` with 0 elements) raises ``ValueError``.
    """
    op = "tv_reconstruct"
    geom, b, p, n_it, _lam, x = _iter_args(projections, geometry, device, n_iter, 1.0,
                                           initial, nonnegative, op)
    weight = _tomo._finite_scalar(tv_weight, "tv_weight")
    if weight < 0.0:
        raise ValueError("%s: tv_weight must be >= 0, got %g" % (op, weight))
    shape = tuple(geom["vol_shape"])
    norm_a = _operator_norm(b, geom)
    n_axes = sum(1 for n in shape if n >= 2)
    norm_g = (4.0 * n_axes) ** 0.5
    nu = norm_a / norm_g
    lip = (norm_a * norm_a + (nu * norm_g) ** 2) ** 0.5
    sigma = tau = 0.9 / lip
    bound = weight * norm_a * norm_a / nu
    y = b.zeros(p.shape)
    z = [b.zeros(shape) for _ in range(n_axes)]
    bar = x
    for k in range(n_it):
        y = (y + sigma * (_gpu._forward(b, bar, geom) - p)) / (1.0 + sigma)
        g = _grad(b, bar)
        z = [zi + sigma * nu * gi for zi, gi in zip(z, g)]
        mag = 0.0
        for zi in z:
            mag = mag + zi * zi
        mag = mag ** 0.5
        shrink = 1.0 / _max1(b, mag / max(bound, 1e-30))
        z = [zi * shrink for zi in z]
        step = _gpu._adjoint(b, y, geom) + nu * _grad_t(b, z, shape)
        new = x - tau * step
        if nonnegative:
            new = _clip_positive(b, new)
        bar = 2.0 * new - x
        x = new
        if _report(on_iter, b, k, x):
            break
    return b.host(x)


def _max1(b, a):
    return a.clamp_min(1.0) if b.name == "cuda" else np.maximum(a, 1.0)


def ct_dual_energy_reconstruct(proj_low, proj_high, geometry, mu_low=(1.0, 0.4),
                               mu_high=(0.6, 0.3), method="fdk", device="auto", **options):
    """Two scans of one geometry to two basis-material volumes.

    At each detector sample the two line integrals are two linear equations in the two
    material path lengths, ``L = M t`` (Alvarez & Macovski 1976). The system is solved
    in the projection domain, where beam hardening has not yet been smeared across the
    volume, and each material is reconstructed on its own. *mu_low* and *mu_high* are
    effective attenuation coefficients; for a polychromatic beam, call
    :func:`dualxray.basis_material_decompose` per view first and reconstruct its output.

    The noise of the two path lengths grows with the condition number of ``M``, which
    is returned.

    :param proj_low: ``(view, V, U)`` line integrals of the low-energy scan.
    :param proj_high: the high-energy scan, same shape.
    :param geometry: dict from :func:`ct_scan_geometry`.
    :param mu_low: attenuation of the two basis materials at the low energy.
    :param mu_high: attenuation of the two basis materials at the high energy.
    :param method: ``"fdk"``, ``"sirt"``, ``"os_sart"`` or ``"tv"``.
    :param device: ``"auto"``, ``"cpu"`` or ``"cuda"``.
    :param options: passed to the reconstruction.
    :returns: dict with ``basis_0`` and ``basis_1`` (path-length densities, volumes),
        and ``condition``.
    :raises ValueError: on mismatched shapes or a singular matrix. Empty input
        (``proj_low`` with 0 elements) raises ``ValueError``.
    """
    op = "ct_dual_energy_reconstruct"
    geom = _check_geometry(geometry, op)
    low = _check_projections(proj_low, geom, op, "proj_low")
    high = _check_projections(proj_high, geom, op, "proj_high")
    routes = {"fdk": fdk_reconstruct, "sirt": sirt_reconstruct,
              "os_sart": os_sart_reconstruct, "tv": tv_reconstruct}
    name = _tomo._choice(method, tuple(routes), "method", op)
    m = np.array([np.asarray(mu_low, dtype=np.float64), np.asarray(mu_high, dtype=np.float64)])
    if m.shape != (2, 2) or not np.all(np.isfinite(m)):
        raise ValueError("%s: mu_low and mu_high must be pairs of finite numbers" % (op,))
    cond = float(np.linalg.cond(m))
    if not np.isfinite(cond) or cond > 1e6:
        raise ValueError("%s: the two energies do not separate these materials (condition "
                         "number %.3g)" % (op, cond))
    inv = np.linalg.inv(m)
    t0 = inv[0, 0] * low + inv[0, 1] * high
    t1 = inv[1, 0] * low + inv[1, 1] * high
    route = routes[name]
    return {"basis_0": route(t0, geom, device=device, **options),
            "basis_1": route(t1, geom, device=device, **options),
            "condition": cond}
