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
    for k, (x, y) in enumerate(pts.copy()):
        ix, iy = int(x), int(y)
        denx=sm[iy,ix-1]-2*sm[iy,ix]+sm[iy,ix+1]
        deny=sm[iy-1,ix]-2*sm[iy,ix]+sm[iy+1,ix]
        dx=0.5*(sm[iy,ix-1]-sm[iy,ix+1])/denx if abs(denx)>1e-15 else 0.0
        dy=0.5*(sm[iy-1,ix]-sm[iy+1,ix])/deny if abs(deny)>1e-15 else 0.0
        pts[k]=[ix+np.clip(dx,-0.5,0.5),iy+np.clip(dy,-0.5,0.5)]
    # Estimate two lattice basis vectors from pair differences near one pitch.
    dif = pts[:,None,:]-pts[None,:,:]; dist=np.linalg.norm(dif,axis=2)
    cand=dif[(dist>0.75*p)&(dist<1.25*p)]
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

    The paraxial relation uses MLA pitch as the spatial baseline and one angular
    pixel as ``pixel_pitch / mla_to_sensor`` radians.  Zero slope is the main
    lens conjugate and maps to its configured object distance.
    """
    a=np.asarray(lf)
    if a.ndim != 4 or any(n == 0 for n in a.shape):
        raise ValueError("lf must have non-empty shape (V,U,H,W)")
    if not isinstance(system,dict) or system.get("kind")!="plenoptic_system":
        raise ValueError("system must be returned by plenoptic_system")
    s=np.asarray(slope,dtype=float)
    if not np.isfinite(s).all(): raise ValueError("slope must be finite")
    para=RT.paraxial_trace(system["main_lens"]); f=abs(float(para["efl"]))
    z0=float(system["main_lens"]["object_mm"])
    if not math.isfinite(z0):
        z0=1e12
    image0=f*z0/(z0-f)
    angular_step=system["pixel_pitch_mm"]/system["mla_to_sensor_mm"]
    delta=s*angular_step*system["mla"]["pitch_mm"]
    image=image0+delta
    denom=1/f-1/image
    z=np.where(np.abs(denom)>1e-15,1/denom,np.inf)
    step=angular_step*system["mla"]["pitch_mm"]
    zp=1/(1/f-1/(image+step)); zm=1/(1/f-1/(image-step))
    return {"depth_m":z/1000.0,"depth_resolution_m":np.abs(zp-zm)/2000.0,
            "slope":s.copy(),"spatial_shape":a.shape[2:],"angular":a.shape[:2],
            "spatial_per_angular":tuple(a.shape[i+2]/a.shape[i] for i in range(2))}
