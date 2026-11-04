# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0.
"""Prescription-based plenoptic camera: MLA geometry, capture, calibration and decode.

All distances are millimetres except the metric depth returned by
``plenoptic_refocus_depth``.  The implementation is geometric optics: each
sensor sample selects a point of the main-lens exit pupil through one spherical
microlens, then :mod:`lensrender` traces that ray through the complete main-lens
prescription.  Diffraction and sensor cross-talk are intentionally absent.

The unfocused (``1.0``) geometry follows Ng et al., *Light Field Photography
with a Hand-Held Plenoptic Camera*, Stanford Tech Report CSTR 2005-02.  The
focused (``2.0``) geometry follows Lumsdaine and Georgiev, *The Focused
Plenoptic Camera*, ICCP 2009.
"""
from __future__ import annotations

import math
import numpy as np
from scipy import ndimage as _ndi
from scipy.spatial import cKDTree as _KDTree

import lensrender as LR
import lightfield as LF
import raytrace as RT

__all__ = ["mla_surface", "mla_sag_normal", "plenoptic_system",
           "plenoptic_capture", "plenoptic_mla_calibrate", "plenoptic_decode",
           "plenoptic_refocus_depth"]

PLENOPTIC = list(__all__)
_BOUNDARY_TOL = 1e-9


def _real(x, name, positive=False):
    if isinstance(x, (bool, np.bool_, str, bytes)):
        raise ValueError(f"{name} must be a finite real number")
    try:
        y = float(x)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a finite real number") from None
    if not math.isfinite(y) or (positive and y <= 0):
        raise ValueError(f"{name} must be {'positive and ' if positive else ''}finite")
    return y


def _pair(x, name, integer=False):
    if not isinstance(x, (tuple, list)) or len(x) != 2:
        raise ValueError(f"{name} must be a pair")
    if integer:
        if any(isinstance(v, bool) or int(v) != v or int(v) <= 0 for v in x):
            raise ValueError(f"{name} must contain positive integers")
        return tuple(map(int, x))
    return tuple(_real(v, name) for v in x)


def mla_surface(pitch_mm, radius_mm, n_lenslets=(1, 1), f_number=None,
                offset_mm=(0, 0), shape="square"):
    """Describe a periodic spherical-cap microlens array surface.

    ``radius_mm`` is signed.  Each lenslet has a circular clear aperture with
    diameter equal to one pitch.  Thus a square lattice has opaque cell corners;
    ``shape='hex'`` changes the centre lattice, not the circular lens boundary.
    If ``f_number`` is supplied it is checked against ``abs(radius)/(n-1)/pitch``
    using the paraxial focal length stored as ``focal_mm``.
    """
    p = _real(pitch_mm, "pitch_mm", True)
    r = _real(radius_mm, "radius_mm")
    if r == 0 or abs(r) < p / 2:
        raise ValueError("radius_mm must be non-zero and span a spherical cap of one pitch")
    n = _pair(n_lenslets, "n_lenslets", True)
    off = _pair(offset_mm, "offset_mm")
    if shape not in ("square", "hex"):
        raise ValueError("shape must be 'square' or 'hex'")
    fn = None if f_number is None else _real(f_number, "f_number", True)
    focal = None if fn is None else fn * p
    return {"kind": "mla", "pitch_mm": p, "radius_mm": r,
            "n_lenslets": n, "f_number": fn, "focal_mm": focal,
            "offset_mm": off, "shape": shape, "boundary_tolerance_mm": _BOUNDARY_TOL}


def _mla_centres(x, y, m):
    p = m["pitch_mm"]
    ox, oy = m["offset_mm"]
    if m["shape"] == "square":
        ix = np.floor((x - ox) / p + 0.5).astype(np.int64)
        iy = np.floor((y - oy) / p + 0.5).astype(np.int64)
        cx, cy = ox + ix * p, oy + iy * p
        bx = np.abs(np.abs(x - cx) - p / 2)
        by = np.abs(np.abs(y - cy) - p / 2)
        boundary = (bx <= m["boundary_tolerance_mm"]) | (by <= m["boundary_tolerance_mm"])
    else:
        dy = p * math.sqrt(3) / 2
        iy = np.floor((y - oy) / dy + 0.5).astype(np.int64)
        rowoff = (iy & 1) * (p / 2)
        ix = np.floor((x - ox - rowoff) / p + 0.5).astype(np.int64)
        cx, cy = ox + rowoff + ix * p, oy + iy * dy
        # Equal distance to two centres is a Voronoi boundary.
        d0 = (x - cx) ** 2 + (y - cy) ** 2
        ds = []
        for ax, ay in ((p, 0), (-p, 0), (p/2, dy), (-p/2, dy), (p/2, -dy), (-p/2, -dy)):
            ds.append((x-cx-ax)**2 + (y-cy-ay)**2)
        boundary = np.min(np.abs(np.stack(ds) - d0), axis=0) <= p * m["boundary_tolerance_mm"]
    return cx, cy, iy, ix, boundary


def mla_sag_normal(surface, xy_mm, *, reject_boundary=True):
    """Evaluate periodic MLA sag and normal; return the hit lenslet indices.

    Boundary hits are counted and, by default, rejected because their normal is
    not unique.  This helper is also used by ``lensrender``'s MLA intersection.
    """
    if not isinstance(surface, dict) or surface.get("kind") != "mla":
        raise ValueError("surface must be returned by mla_surface")
    q = np.asarray(xy_mm, dtype=float)
    if q.ndim != 2 or q.shape[1] != 2 or not np.isfinite(q).all():
        raise ValueError("xy_mm must be a finite (N,2) array")
    cx, cy, iy, ix, boundary = _mla_centres(q[:, 0], q[:, 1], surface)
    if reject_boundary and np.any(boundary):
        raise ValueError(f"mla surface: {int(boundary.sum())} ray(s) hit a lenslet boundary")
    dx, dy = q[:, 0] - cx, q[:, 1] - cy
    r2 = dx*dx + dy*dy
    R = surface["radius_mm"]
    root = np.sqrt(np.maximum(R*R-r2, 0.0))
    sag = R - np.sign(R) * root
    normal = np.stack([-dx / root, -dy / root, np.ones_like(dx)], axis=1)
    normal /= np.linalg.norm(normal, axis=1, keepdims=True)
    valid = (r2 <= (surface["pitch_mm"] / 2) ** 2 * (1 + 1e-12)) & ~boundary
    return {"sag_mm": sag, "normal": normal, "lenslet_index": np.stack([iy, ix], 1),
            "centre_mm": np.stack([cx, cy], 1), "valid": valid,
            "boundary": boundary, "boundary_count": int(boundary.sum())}


def plenoptic_system(main_lens, mla, sensor, *, kind="unfocused",
                      mla_to_sensor_mm=None, main_to_mla_mm=None):
    """Assemble a main lens, MLA and sensor and report F-number matching."""
    LR._system(main_lens, "plenoptic_system")
    if not isinstance(mla, dict) or mla.get("kind") != "mla":
        raise ValueError("mla must be returned by mla_surface")
    if kind not in ("unfocused", "focused"):
        raise ValueError("kind must be 'unfocused' or 'focused'")
    if not isinstance(sensor, dict) or "size" not in sensor or "pixel_pitch_um" not in sensor:
        raise ValueError("sensor needs size and pixel_pitch_um")
    size = _pair(sensor["size"], "sensor size", True)
    pp = _real(sensor["pixel_pitch_um"], "pixel_pitch_um", True) * 1e-3
    para = RT.paraxial_trace(main_lens)
    nmain = abs(float(para["efl"])) / (2 * float(para["xp_radius"]))
    fmla = mla.get("focal_mm")
    if fmla is None:
        # A practical default refractive index contrast; explicit f_number is preferred.
        fmla = abs(mla["radius_mm"]) / 0.5
    nmla = fmla / mla["pitch_mm"]
    b = fmla if mla_to_sensor_mm is None else _real(mla_to_sensor_mm, "mla_to_sensor_mm", True)
    if kind == "unfocused":
        a = math.inf
    else:
        if main_to_mla_mm is None:
            if b <= fmla:
                raise ValueError("focused configuration needs mla_to_sensor_mm > MLA focal length")
            a = 1.0 / (1.0/fmla - 1.0/b)
        else:
            a = _real(main_to_mla_mm, "main_to_mla_mm", True)
            predicted = 1.0 / (1.0/a + 1.0/b)
            if abs(predicted-fmla) > 1e-6 * fmla:
                raise ValueError("focused MLA conjugates do not satisfy the thin-lens equation")
    diameter = fmla / nmain
    frac = diameter / mla["pitch_mm"] - 1.0
    return {"kind": "plenoptic_system", "configuration": kind, "main_lens": main_lens,
            "mla": dict(mla), "sensor": dict(sensor), "sensor_size": size,
            "pixel_pitch_mm": pp, "mla_to_sensor_mm": b, "main_to_mla_mm": a,
            "mla_focal_mm": fmla, "main_f_number": nmain, "mla_f_number": nmla,
            "microimage_diameter_mm": diameter, "overlap_fraction": max(frac, 0.0),
            "gap_fraction": max(-frac, 0.0), "f_number_ratio": nmla/nmain,
            "magnification": 0.0 if math.isinf(a) else b/a}


def _sensor_grid(system):
    H, W = system["sensor_size"]
    p = system["pixel_pitch_mm"]
    yy, xx = np.indices((H, W), dtype=float)
    return (xx-(W-1)/2)*p, (yy-(H-1)/2)*p


def plenoptic_capture(system, scene, *, pupil_samples=1, wavelengths=None,
                      exposure_s=1e-4, boundary_tolerance_mm=None):
    """Trace a raw plenoptic frame and its white calibration image.

    The return includes ground-truth ``pupil_uv`` and ``lenslet_index`` for
    every sensor pixel.  ``pupil_samples`` is accepted for API symmetry; a
    sensor pixel already represents one angular sample and therefore must be 1.

    **Sign convention differs from a real camera.**  A pixel offset ``q`` from
    its lenslet centre is mapped to the pupil coordinate ``+q/(d/2)`` (``d`` the
    microimage diameter).  A physical lenslet with the sensor at its focal plane
    inverts the pupil: the pixel at ``+q`` sees the pupil at ``-q * D/b``.  So
    views decoded from this simulation run in the opposite pupil order to a real
    sensor's, and the refocus slope of the same object has the opposite sign
    (a near object has a positive slope here, a negative one on real data).
    Everything in this module, including :func:`plenoptic_refocus_depth`, is
    consistent with the simulated convention; flip the slope sign (or reverse
    the angular axes) before converting real-sensor data.  Not changed yet
    because no PoC compares against a real raw frame (2026-11-04).
    """
    if not isinstance(system, dict) or system.get("kind") != "plenoptic_system":
        raise ValueError("system must be returned by plenoptic_system")
    if int(pupil_samples) != 1:
        raise ValueError("plenoptic_capture: each pixel is one pupil sample; pupil_samples must be 1")
    LR._check_scene(scene, "plenoptic_capture")
    exposure = _real(exposure_s, "exposure_s", True)
    if wavelengths is None:
        wavelengths = [system["main_lens"]["wavelength_um"]]
    wls = np.asarray(wavelengths, dtype=float).reshape(-1)
    if len(wls) == 0 or not np.isfinite(wls).all():
        raise ValueError("wavelengths must be a non-empty finite sequence")
    X, Y = _sensor_grid(system)
    flat = np.stack([X.ravel(), Y.ravel()], 1)
    mla = dict(system["mla"])
    if boundary_tolerance_mm is not None:
        mla["boundary_tolerance_mm"] = _real(boundary_tolerance_mm, "boundary_tolerance_mm")
    hit = mla_sag_normal(mla, flat, reject_boundary=False)
    local = flat-hit["centre_mm"]
    # At the MLA focal plane, local pixel position is a pupil coordinate.
    uv = local / (system["microimage_diameter_mm"] / 2)
    valid = hit["valid"] & (np.sum(uv*uv, axis=1) <= 1.0 + 1e-12)
    # A finite sensor pixel straddles the circular clear-aperture edge.  Model
    # its covered area with a short edge ramp instead of turning the last pixel
    # into a fully illuminated square.  This produces the measured cat's-eye
    # fall-off while leaving the interior radiometrically flat.
    rho = np.linalg.norm(local, axis=1)
    aperture_radius = system["mla"]["pitch_mm"] / 2
    edge_width = system["pixel_pitch_mm"] * 1.5
    aperture_weight = np.clip((aperture_radius-rho) / edge_width, 0.0, 1.0) ** 6
    raw = np.zeros(len(flat)); white = np.zeros(len(flat)); traced_uv = uv.copy()
    for wl in wls:
        geo = LR._geometry(system["main_lens"], float(wl), op="plenoptic_capture")
        centre = hit["centre_mm"]
        pupil = uv * geo["xp_radius"]
        S = np.column_stack([centre, np.full(len(flat), geo["z_img"])])
        U = np.column_stack([pupil, np.full(len(flat), geo["z_xp"])])
        D = U-S; D /= np.linalg.norm(D, axis=1, keepdims=True)
        o, d, tr, ok, _ = LR._trace_back(system["main_lens"], geo, S, D)
        good = valid & ok
        white += np.where(good, tr * aperture_weight, 0.0)
        if np.any(good):
            raw[good] += (LR._radiance(scene, o[good], d[good], [float(wl)], np.ones(1))[0][:, 0]
                          * tr[good] * aperture_weight[good])
    H, W = system["sensor_size"]
    scale = 1.0 / len(wls)
    return {"raw": (raw*scale*exposure).reshape(H, W),
            "white_image": (white*scale*exposure).reshape(H, W),
            "lenslet_index": hit["lenslet_index"].reshape(H, W, 2),
            "pupil_uv": traced_uv.reshape(H, W, 2), "valid": valid.reshape(H, W),
            "boundary_count": hit["boundary_count"], "vignetted_count": int((~valid).sum()),
            "wavelengths_um": wls.copy(), "ray_count": int(len(flat)*len(wls))}


def plenoptic_mla_calibrate(white_image, pitch_px_guess, *, max_residual_px=0.25):
    """Fit a rotated rectangular lenslet lattice to peaks of a white frame."""
    im = np.asarray(white_image, dtype=float)
    if im.ndim != 2 or min(im.shape) < 5 or not np.isfinite(im).all() or np.ptp(im) <= 0:
        raise ValueError("white_image must be a finite, non-constant 2-D image")
    p = _real(pitch_px_guess, "pitch_px_guess", True)
    if p < 2:
        raise ValueError("pitch_px_guess must be at least 2 pixels")
    sm = _ndi.gaussian_filter(im, max(0.5, p/8))
    mx = _ndi.maximum_filter(sm, size=max(3, int(round(p*0.7))))
    pts = np.argwhere((sm == mx) & (sm > np.percentile(sm, 60)))[:, ::-1].astype(float)
    pts = pts[(pts[:, 0] >= 2) & (pts[:, 0] <= im.shape[1]-3) &
              (pts[:, 1] >= 2) & (pts[:, 1] <= im.shape[0]-3)]
    if len(pts) < 4:
        raise ValueError("fewer than four lenslet centres were found")
    # Sub-pixel quadratic peak in the smoothed image.  Unlike a 3x3 centroid,
    # this is not biased toward the centre pixel when a narrow spot lies close
    # to the edge of that window.
    ix = pts[:, 0].astype(np.int64); iy = pts[:, 1].astype(np.int64)
    c0 = sm[iy, ix]
    denx = sm[iy, ix-1]-2*c0+sm[iy, ix+1]
    deny = sm[iy-1, ix]-2*c0+sm[iy+1, ix]
    okx = np.abs(denx) > 1e-15; oky = np.abs(deny) > 1e-15
    dx = np.zeros(len(pts)); dy = np.zeros(len(pts))
    np.divide(0.5*(sm[iy, ix-1]-sm[iy, ix+1]), denx, out=dx, where=okx)
    np.divide(0.5*(sm[iy-1, ix]-sm[iy+1, ix]), deny, out=dy, where=oky)
    pts = np.column_stack([ix+np.clip(dx, -0.5, 0.5), iy+np.clip(dy, -0.5, 0.5)])
    # Estimate two lattice basis vectors from pair differences near one pitch.
    # A KD-tree returns only the pairs closer than 1.25 pitch, so memory grows
    # with the number of peaks rather than its square (the former all-pairs
    # difference array asked for 791 GiB on a 7200 px white frame, 2026-11-04).
    # Both orientations of every pair are kept, as the all-pairs array had them.
    pairs = _KDTree(pts).query_pairs(1.25*p, output_type="ndarray")
    if len(pairs):
        dif = pts[pairs[:, 0]]-pts[pairs[:, 1]]
        dist = np.linalg.norm(dif, axis=1)
        dif = dif[(dist > 0.75*p) & (dist < 1.25*p)]
        cand = np.concatenate([dif, -dif])
    else:
        cand = np.zeros((0, 2))
    if len(cand)<4:
        raise ValueError("lenslet peaks do not support the pitch guess")
    ang=np.mod(np.arctan2(cand[:,1],cand[:,0]), math.pi/2)
    theta=float(np.angle(np.mean(np.exp(4j*ang)))/4)
    e0=np.array([math.cos(theta),math.sin(theta)]); e1=np.array([-e0[1],e0[0]])
    proj=np.abs(cand@e0); pitch=float(np.median(proj[proj>0.5*p]))
    origin=pts[np.argmin(pts[:,0]+pts[:,1])]
    ij=np.rint(np.column_stack([(pts-origin)@e0,(pts-origin)@e1])/pitch)
    A=np.column_stack([np.ones(len(pts)),ij[:,0],ij[:,1]])
    coef=np.linalg.lstsq(A,pts,rcond=None)[0]; fit=A@coef
    residual=float(np.sqrt(np.mean(np.sum((pts-fit)**2,axis=1))))
    max_residual = _real(max_residual_px, "max_residual_px", True)
    if residual > max_residual:
        raise ValueError(f"MLA lattice residual {residual:.4g} px exceeds {max_residual_px:.4g} px")
    b0,b1=coef[1],coef[2]; pitch_fit=(np.linalg.norm(b0)+np.linalg.norm(b1))/2
    rotation=math.degrees(math.atan2(b0[1],b0[0]))
    return {"centres": fit, "observed_centres": pts, "pitch_px": float(pitch_fit),
            "rotation_deg": rotation, "residual_px": residual,
            "max_residual_px": max_residual, "origin_px": coef[0],
            "basis_px": np.stack([b0,b1]), "white_image": im.copy()}


def plenoptic_decode(raw, calibration, *, angular=(5, 5)):
    """Rectify a calibrated raw frame and return ``L[v,u,y,x]``.

    The result is the repository's existing ``lightfield`` type: a plain
    ``(V,U,H,W)`` array that composes directly with light-field operators.
    """
    im=np.asarray(raw,dtype=float)
    V,U=_pair(angular,"angular",True)
    if im.ndim!=2 or not np.isfinite(im).all():
        raise ValueError("raw must be a finite 2-D image")
    if not isinstance(calibration,dict) or "basis_px" not in calibration or "origin_px" not in calibration:
        raise ValueError("calibration must be returned by plenoptic_mla_calibrate")
    B=np.asarray(calibration["basis_px"],float); org=np.asarray(calibration["origin_px"],float)
    inv=np.linalg.inv(B)
    corners=np.array([[0,0],[im.shape[1]-1,0],[0,im.shape[0]-1],[im.shape[1]-1,im.shape[0]-1]])
    ij=(corners-org)@inv
    lo=np.ceil(ij.min(0)).astype(int); hi=np.floor(ij.max(0)).astype(int)
    nx,ny=hi-lo+1
    if nx<1 or ny<1: raise ValueError("calibrated lattice has no complete lenslet in the frame")
    jj,ii=np.indices((ny,nx)); base=org+(ii[...,None]+lo[0])*B[0]+(jj[...,None]+lo[1])*B[1]
    vv,uu=np.indices((V,U)); du=((uu-(U-1)/2)/(U))[...,None]*B[0]+((vv-(V-1)/2)/(V))[...,None]*B[1]
    xy=base[None,None,:,:,:]+du[:,:,None,None,:]
    rect=_ndi.map_coordinates(im,[xy[...,1],xy[...,0]],order=1,mode="constant",cval=0.0)
    white=np.asarray(calibration.get("white_image",np.ones_like(im)),float)
    wr=_ndi.map_coordinates(white,[xy[...,1],xy[...,0]],order=1,mode="constant",cval=0.0)
    good=wr>max(np.max(wr)*1e-6,1e-15)
    out=np.divide(rect,wr,out=np.zeros_like(rect),where=good)
    return out


def plenoptic_refocus_depth(lf, system, slope):
    """Convert light-field refocus slope(s) to object distance in metres.

    *slope* is in the unit of :func:`lightfield.lf_refocus` and
    :func:`lightfield.lf_depth_from_focus` on a field from
    :func:`plenoptic_decode`: decoded spatial samples (lenslets) of parallax per
    view step.  Zero slope is the main-lens conjugate of the MLA plane and maps
    to the configured object distance.

    Paraxial model of the unfocused (1.0) camera, in the geometry
    :func:`plenoptic_capture` traces.  :func:`plenoptic_decode` samples ``U``
    views across one lenslet pitch, so one view step moves the exit-pupil
    coordinate by ``dX = (pitch/U) * xp_radius / (microimage_diameter/2)``.  A
    point imaged ``delta`` behind the MLA plane, with the exit pupil ``D`` in
    front of it, shifts on the MLA by ``dX * delta/(D+delta)`` per view, hence
    ``slope = (dX/pitch) * delta/(D+delta)``; Newton's equation of the
    paraxial main lens turns the image position into the object distance.

    Before 2026-11-04 the image shift was ``slope * angular_step * pitch`` with
    ``angular_step = pixel_pitch/mla_to_sensor`` -- a factor ``1/angular_step**2``
    (~3000x for the PoC camera) too small, so every measured slope mapped back
    to the focus distance.  The relation is now gated against rays traced
    forward through the prescription (``tests/test_plenoptic.py``): rel. error
    below 1e-6 for an ideal lens and 2e-4 for the PoC's three-element lens.

    Sign: follows :func:`plenoptic_capture`'s non-inverting pixel-to-pupil
    map, which is the opposite of a physical lenslet; negate real-sensor slopes.

    Limits: it is paraxial.  Spherical aberration of a real aperture moves the
    best-focus slope of the full pupil away from the paraxial one -- for the PoC
    lens at F/3.7 the decoded 1.0 m plane sits at slope -0.029, not 0 (measured
    in ``examples/poc_plenoptic_camera.py``).  ``depth_resolution_m`` is half
    the depth span of a slope change of ``+-1/(U-1)``: one decoded sample of
    parallax across the full angular baseline.

    **Raises** ``ValueError``: *lf* not ``(V,U,H,W)``, ``V != U`` (one slope
    cannot describe two different per-view pupil steps), fewer than two views,
    a focused (2.0) system (its MLA is not at the main-lens image plane, so
    slope means something else), a non-finite slope, or a slope whose image
    point lies at or beyond the exit pupil (``slope*pitch/dX >= 1``).
    """
    a=np.asarray(lf)
    if a.ndim != 4 or any(n == 0 for n in a.shape):
        raise ValueError("lf must have non-empty shape (V,U,H,W)")
    if not isinstance(system,dict) or system.get("kind")!="plenoptic_system":
        raise ValueError("system must be returned by plenoptic_system")
    if system.get("configuration") != "unfocused":
        raise ValueError("plenoptic_refocus_depth models the unfocused (1.0) camera; "
                         "a focused (2.0) system has its MLA off the main-lens image plane")
    V, U = int(a.shape[0]), int(a.shape[1])
    if V != U:
        raise ValueError("lf angular axes must be equal (V == U); got %d x %d" % (V, U))
    if U < 2:
        raise ValueError("lf needs at least two views per axis to carry parallax")
    s=np.asarray(slope,dtype=float)
    if not np.isfinite(s).all(): raise ValueError("slope must be finite")
    lens = system["main_lens"]
    geo = LR._geometry(lens, float(lens["wavelength_um"]), op="plenoptic_refocus_depth")
    para = geo["para"]
    f = float(para["efl"]); bfl = float(para["bfl"]); ffl = float(para["ffl"])
    pitch = float(system["mla"]["pitch_mm"])
    image0 = float(geo["image_mm"])
    xp_dist = image0 - float(geo["xp_position"])
    pupil_step = (pitch/U) * float(geo["xp_radius"]) / (system["microimage_diameter_mm"]/2)

    def depth_mm(sv):
        k = np.asarray(sv, float) * pitch / pupil_step
        beyond = k >= 1.0
        with np.errstate(divide="ignore", invalid="ignore"):
            delta = np.where(beyond, np.nan, k * xp_dist / (1.0 - k))
            xprime = image0 + delta - bfl
            z = -(-f*f/xprime + ffl)
        z = np.where(np.abs(xprime) > 1e-15, z, np.inf)
        return np.where(beyond, np.inf, z), beyond

    z, beyond = depth_mm(s)
    if np.any(beyond):
        raise ValueError("slope*pitch/pupil_step >= 1: the image point would lie at or "
                         "beyond the exit pupil (max slope %.6g)" % (pupil_step/pitch))
    ds = 1.0 / (U - 1)
    zp, _ = depth_mm(s + ds); zm, _ = depth_mm(s - ds)
    with np.errstate(invalid="ignore"):
        resolution = np.abs(zp - zm) / 2000.0
    return {"depth_m": z/1000.0, "depth_resolution_m": resolution,
            "slope": s.copy(), "spatial_shape": a.shape[2:], "angular": a.shape[:2],
            "pupil_step_mm": float(pupil_step), "exit_pupil_distance_mm": float(xp_dist),
            "spatial_per_angular": tuple(a.shape[i+2]/a.shape[i] for i in range(2))}
