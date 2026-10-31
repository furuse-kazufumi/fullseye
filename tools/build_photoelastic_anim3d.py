#!/usr/bin/env python3
"""Photoelastic Brazilian-disc lesson for ViEW 2026."""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_erosion, maximum_filter, median_filter, minimum_filter
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import photoelastic as pe  # noqa: E402
import matappear as ma  # noqa: E402
import pocviewer as pv  # noqa: E402

T = pv.viewer_text
OUT_HTML = ROOT / "docs" / "view2026" / "anim3d" / "photoelastic_anim3d.html"
LANGS = ("ja", "en")
RADIUS, THICKNESS, COEFF = 0.025, 0.006, 5.0e-11
WAVELENGTHS_NM = np.array([450.0, 532.0, 633.0])
WHITE_WAVELENGTHS_NM = np.linspace(400.0, 700.0, 31)
REFERENCE_WAVELENGTH_NM = 532.0
LOADS = (240.0, 480.0, 720.0)
READ_NOISE = 0.01
FULL_WELL = 10_000
ADC_LEVELS = 256
FRAME_COUNT = 24
FIELD_SIZE = 161
SURFACE_SIZE = 101
PANEL_SIZE = 256
LIMIT_SUPERSAMPLE = 4
RGB_ORDER_MAX = 24.0
RGB_ORDER_STEP = 0.002

_RGB_ORDER_TREE = None
_RGB_ORDER_GRID = None
_RGB_INVERSE_CACHE = {}
_CAMERA_PALETTE_TREE = None
_CAMERA_PALETTE = None


def _disc(n=48):
    """Deterministic two-faced disc mesh; no triangulator."""
    a = np.arange(n) * 2 * np.pi / n
    rim0 = np.c_[RADIUS * np.cos(a), RADIUS * np.sin(a), np.full(n, -THICKNESS / 2)]
    rim1 = rim0.copy(); rim1[:, 2] *= -1
    v = np.vstack([rim0, rim1, [[0, 0, -THICKNESS / 2], [0, 0, THICKNESS / 2]]])
    f = []
    for i in range(n):
        j = (i + 1) % n
        f.extend([[i, j, n + j], [i, n + j, n + i], [2*n, j, i], [2*n+1, n+i, n+j]])
    return v * 115.0, np.asarray(f, int)


def _plate(x, z, w=.85, h=2.2):
    v = np.array([[x, -w, z-h], [x, w, z-h], [x, w, z+h], [x, -w, z+h]], float)
    return v, np.array([[0, 1, 2], [0, 2, 3]], int)


def _motion(frames, bodies):
    xyz = np.zeros((frames, bodies, 3)); q = np.zeros((frames, bodies, 4)); q[..., 0] = 1
    return xyz, q


def _e(x):
    return "< 1e-12" if abs(float(x)) < 1e-12 else "%.4g" % float(x)


def _quantized_camera(ideal, rng):
    """Shot noise at a 10k-electron full well + 1% read noise + 8-bit ADC."""
    shot=rng.poisson(np.clip(ideal,0,1)*FULL_WELL)/FULL_WELL
    noisy=np.clip(shot+rng.normal(0,READ_NOISE,np.shape(ideal)),0,1)
    return np.rint(noisy*(ADC_LEVELS-1))/(ADC_LEVELS-1)


def _field(load_n, size):
    """Stress on an offset sensor grid; the physical centre is not a pixel centre."""
    step=2*RADIUS/(size-5); cx=(size-1)/2+.37; cy=(size-1)/2-.29
    yy,xx=np.mgrid[:size,:size]; xm=(xx-cx)*step; ym=(yy-cy)*step
    inside=xm*xm+ym*ym < (.995*RADIUS)**2
    g={k:np.zeros((size,size),float) for k in ("sxx","syy","txy")}
    d=pe.brazilian_disc_stress(RADIUS,THICKNESS,load_n,x=xm[inside],y=ym[inside])
    for k in g: g[k][inside]=d[k]
    p=pe.principal_stress(g["sxx"],g["syy"],g["txy"])
    return g,p,inside,xm,ym,cx,cy


def _spatial_order(mono, inside, xm, cy, closed_order):
    """Unwrap N(x) from one horizontal image profile and locate dark lines quadratically."""
    row=int(round(cy)); profile=np.mean(mono[row-1:row+2],axis=0)
    valid=np.where(inside[row])[0]; left=valid[valid < np.mean(valid)]
    # Work from the rim toward the centre. A short moving average suppresses one-pixel ADC/read-noise extrema.
    z=np.convolve(profile[left],np.ones(3)/3,mode="same")[1:-1]; cols=left[1:-1]
    scale=max(float(np.percentile(z,98)),.2); z=np.clip(z/scale,0,1)
    minima=[]
    for i in range(1,len(z)-1):
        if z[i]<z[i-1] and z[i]<=z[i+1] and z[i]<.25 and (not minima or cols[i]-minima[-1]>4):
            den=z[i-1]-2*z[i]+z[i+1]
            off=0.5*(z[i-1]-z[i+1])/den if abs(den)>1e-12 else 0.0
            minima.append(float(cols[i]+np.clip(off,-.5,.5)))
    centre_level=float(np.mean(z[-3:])); frac=float(np.arcsin(np.sqrt(np.clip(centre_level,0,1)))/np.pi)
    rising=float(np.mean(z[-3:])-np.mean(z[-8:-5])) >= 0
    centre_order=len(minima)+(frac if rising else 1-frac)
    # N(x) is built only from the observed dark-line positions (integer orders), rim, and observed centre intensity.
    ax=np.array([cols[0],*minima,cols[-1]],float)
    ay=np.array([0,*range(1,len(minima)+1),centre_order],float)
    order=np.interp(cols,ax,ay)
    truth=np.interp(xm[row,cols],xm[row],closed_order[row])
    rmse=float(np.sqrt(np.mean((order-truth)**2)))
    return {"profile":profile,"cols":cols,"order":order,"truth":truth,"rmse":rmse,
            "minima":minima,"centre_order":centre_order}


def observe(load_n: float, size=129, seed=0):
    """Create noisy camera frames, then estimate stress without passing load or true stress to either estimator."""
    g,p,inside,xm,ym,cx,cy=_field(load_n,size)
    rng = np.random.default_rng(1200 + seed)
    phase, six = [], None
    for wi, lam_nm in enumerate(WAVELENGTHS_NM):
        ret = pe.photoelastic_retardation(p["difference"], THICKNESS, COEFF, lam_nm * 1e-9)
        raw = pe.photoelastic_polarization_images(ret["delta_rad"], p["angle_deg"] + 90.0, "stokes6")
        yy, xx = np.mgrid[:size, :size]
        illumination = 0.91 + 0.08 * xx / (size - 1) + 0.03 * yy / (size - 1)
        noisy = _quantized_camera(raw * illumination, rng)
        est = pe.photoelastic_phase_estimate(noisy, "stokes6", sum_tolerance=.08)
        phase.append(est["delta_rad"])
        if wi == 1:
            six = noisy
    unwrap = pe.retardation_unwrap_multiwavelength(phase, WAVELENGTHS_NM.tolist(), 4200.0)
    stress = unwrap["retardation_nm"] * 1e-9 / (THICKNESS * COEFF)
    c0=int(round(cy)); c1=int(round(cx)); centre_stress=float(np.nanmedian(stress[c0-2:c0+3,c1-2:c1+3]))
    ret532=pe.photoelastic_retardation(p["difference"],THICKNESS,COEFF,532e-9)
    mono_ideal=pe.polariscope_intensity(ret532["delta_rad"],setup="circular_dark")*illumination
    mono=_quantized_camera(mono_ideal,rng); mono[~inside]=0
    spatial=_spatial_order(mono,inside,xm,cy,ret532["fringe_order"])
    fringe_stress=spatial["centre_order"]*532e-9/(THICKNESS*COEFF)
    return {"grid": g, "principal": p, "camera": six, "stress": stress,
            "centre_stress": centre_stress, "fringe_stress": fringe_stress,
            "dark_count":len(spatial["minima"]),"spatial":spatial,"mono":mono,"valid":unwrap["valid"]}


def measurements():
    rows = []
    factor = 8.0 / (math.pi * (2 * RADIUS) * THICKNESS)
    for i, load in enumerate(LOADS):
        o = observe(load, seed=i)
        closed = factor * load
        inferred = o["centre_stress"] / factor
        fringe_load=o["fringe_stress"]/factor
        rows.append({"load": load, "closed_stress": closed, "phase_stress": o["centre_stress"],
                     "inferred_load": inferred, "load_error_pct": abs(inferred-load)/load*100,
                     "fringe_load":fringe_load,"fringe_error_pct":abs(fringe_load-load)/load*100,
                     "fringe_stress": o["fringe_stress"], "dark_count": o["dark_count"],"order_rmse":o["spatial"]["rmse"],
                     "route_difference_pct": abs(o["fringe_stress"]-o["centre_stress"])/o["centre_stress"]*100})
    return rows


def fringe_frames(load_values, size=57):
    """White-light RGB sequence integrated over 31 wavelengths, with seeded sensor noise."""
    out=[]
    for load in load_values:
        g=pe.brazilian_disc_stress(RADIUS,THICKNESS,max(float(load),1e-3),size=size)
        p=pe.principal_stress(g["sxx"],g["syy"],g["txy"])
        out.append(_rgb_white_light(p["difference"],p["angle_deg"],g["inside"],noise=.006,
                                    seed=20261027+len(out)))
    return out


def _grid_mesh(x, y, inside, scale=100.0):
    """Triangulate only complete grid cells; holes and specimen rims stay real geometry."""
    h, w = inside.shape
    ids = np.arange(h * w, dtype=int).reshape(h, w)
    pos = np.c_[x.ravel() * scale, y.ravel() * scale, np.zeros(h * w)]
    faces = []
    for r in range(h - 1):
        for c in range(w - 1):
            q = ids[r:r + 2, c:c + 2]
            if np.all(inside[r:r + 2, c:c + 2]):
                faces.extend([[q[0, 0], q[0, 1], q[1, 1]], [q[0, 0], q[1, 1], q[1, 0]]])
    return pos, np.asarray(faces, int), ids


def _contact_shoe(sign=1, n=18):
    """Curved loading shoe matching the disc rim (not a generic box)."""
    a = np.linspace(np.deg2rad(70), np.deg2rad(110), n)
    if sign < 0:
        a = -a
    r0, r1, z0, z1 = RADIUS * 100, RADIUS * 100 + .42, -.16, .16
    rings = [np.c_[r * np.cos(a), r * np.sin(a), np.full(n, z)] for z in (z0, z1) for r in (r0, r1)]
    v = np.vstack(rings); f = []
    for base0, base1 in ((0, n), (2*n, 3*n), (0, 2*n), (n, 3*n)):
        for i in range(n - 1):
            f.extend([[base0+i, base0+i+1, base1+i+1], [base0+i, base1+i+1, base1+i]])
    return v, np.asarray(f, int)


def _hole_rim(radius=.005, n=48):
    a = np.arange(n) * 2*np.pi/n
    rr = [radius*100*.94, radius*100*1.06]
    v = np.vstack([np.c_[r*np.cos(a), r*np.sin(a), np.full(n, .045)] for r in rr])
    f=[]
    for i in range(n):
        j=(i+1)%n; f.extend([[i,j,n+j],[i,n+j,n+i]])
    return v,np.asarray(f,int)


def _linear_to_srgb(linear):
    """IEC 61966-2-1 transfer function after the spectral op returns linear sRGB."""
    a=np.clip(np.asarray(linear,float),0.0,1.0)
    return np.where(a<=.0031308,12.92*a,1.055*np.power(a,1/2.4)-.055)


def _spectral_rgb_from_order(order):
    """Michel-Lévy colour from a continuous white-light spectrum.

    The 400--700 nm band is sampled at 31 wavelengths.  ``matappear.spectrum_to_srgb``
    integrates the spectrum with the CIE 1931 2-degree colour-matching functions and
    D65, then converts XYZ to linear sRGB.  Its CMF source is the Wyman, Sloan & Shirley,
    JCGT 2(2), 2013 multi-lobe Gaussian approximation (about 1 % maximum table error);
    the sRGB matrix and transfer function follow IEC 61966-2-1.  A circular dark-field
    polariscope contributes ``sin^2(pi * retardation / wavelength)`` at each wavelength.
    """
    n=np.asarray(order,float)
    spectrum=np.sin(np.pi*n[...,None]*REFERENCE_WAVELENGTH_NM/WHITE_WAVELENGTHS_NM)**2
    return _linear_to_srgb(ma.spectrum_to_srgb(WHITE_WAVELENGTHS_NM,spectrum))


def _rgb_white_light(diff, angle, inside, thickness=THICKNESS, noise=0.0, seed=0):
    """Render continuous-spectrum dark-field colour; no artificial high-order fade mask."""
    del angle
    order=thickness*COEFF*np.asarray(diff,float)/(REFERENCE_WAVELENGTH_NM*1e-9)
    rgb=_spectral_rgb_from_order(order)
    if noise:
        # Smooth fixed-pattern camera noise remains compressible; spectral fading itself
        # comes only from integrating the continuous spectrum above.
        rng=np.random.default_rng(seed);h,w=rgb.shape[:2]
        low=rng.normal(0,noise,(max(2,(h+7)//8),max(2,(w+7)//8),3)).astype(np.float32)
        smooth=np.stack([np.asarray(Image.fromarray(low[...,c],"F").resize((w,h),Image.Resampling.BILINEAR)) for c in range(3)],-1)
        rgb += smooth
    rgb=np.where(inside[...,None],rgb,.012)
    return np.uint8(np.rint(np.clip(rgb,0,1)*255))


def _pixel_aperture_white_light(kind, value, factor=LIMIT_SUPERSAMPLE, noise=0.0, seed=0):
    """Area-integrate a supersampled spectral fringe field into native 256 px pixels.

    Every output pixel is the arithmetic mean of a ``factor x factor`` block at every
    one of the 31 wavelengths *before* CIE integration and sRGB encoding.  This is an
    actual rectangular pixel-aperture integral, not a grey overlay or a contrast mask.
    """
    factor=int(factor)
    if factor < 2:
        raise ValueError("pixel-aperture supersampling factor must be an integer >= 2")
    high=PANEL_SIZE*factor
    if kind=="disc":
        g=pe.brazilian_disc_stress(RADIUS,THICKNESS,max(float(value),1e-9),size=high)
    else:
        g=pe.kirsch_plate_stress(.005,max(float(value),1e-9),half_width_m=.02,size=high)
    p=pe.principal_stress(g["sxx"],g["syy"],g["txy"]);inside=np.asarray(g["inside"],bool)
    order=THICKNESS*COEFF*p["difference"]/(REFERENCE_WAVELENGTH_NM*1e-9)
    spectra=np.empty((PANEL_SIZE,PANEL_SIZE,len(WHITE_WAVELENGTHS_NM)),np.float32)
    for j,lam in enumerate(WHITE_WAVELENGTHS_NM):
        mono=np.sin(np.pi*order*REFERENCE_WAVELENGTH_NM/lam)**2
        mono=np.where(inside,mono,.012)
        spectra[...,j]=mono.reshape(PANEL_SIZE,factor,PANEL_SIZE,factor).mean(axis=(1,3))
    rgb=_linear_to_srgb(ma.spectrum_to_srgb(WHITE_WAVELENGTHS_NM,spectra))
    if noise:
        rng=np.random.default_rng(seed);h,w=rgb.shape[:2]
        low=rng.normal(0,noise,(max(2,(h+7)//8),max(2,(w+7)//8),3)).astype(np.float32)
        smooth=np.stack([np.asarray(Image.fromarray(low[...,c],"F").resize((w,h),Image.Resampling.BILINEAR)) for c in range(3)],-1)
        rgb=np.clip(rgb+smooth,0,1)
    inside_blocks=inside.reshape(PANEL_SIZE,factor,PANEL_SIZE,factor)
    inside_low=inside_blocks.all(axis=(1,3))
    truth=np.where(inside,order,0.0).reshape(PANEL_SIZE,factor,PANEL_SIZE,factor).mean(axis=(1,3))
    return _camera_palette_rgb(np.uint8(np.rint(np.clip(rgb,0,1)*255))),truth,inside_low


def _map_rgb(a, inside, lo=None, hi=None, diverging=False):
    """Map a scalar field to the same blue-white-red / sequential colours used in panels."""
    v=np.asarray(a,float); good=inside & np.isfinite(v)
    if lo is None: lo=float(np.percentile(v[good],2)) if np.any(good) else 0.0
    if hi is None: hi=float(np.percentile(v[good],98)) if np.any(good) else 1.0
    u=np.clip((v-lo)/max(hi-lo,1e-30),0,1)
    if diverging:
        # Exact white at zero for symmetric lo/hi, saturated blue/red at the limits.
        rgb=np.stack([np.clip(2*u,0,1),1-np.abs(2*u-1),np.clip(2*(1-u),0,1)],-1)
    else:
        rgb=np.stack([.15+.85*u,.25+.65*np.sqrt(u),.75-.65*u],-1)
    rgb[~inside]=.012
    return np.uint8(np.clip(rgb,0,1)*255)


def _quantize_rgb(rgb, levels=5):
    """Deterministic colour cube (5³=125 colours), allowing indexed lossless PNG storage."""
    a=np.asarray(rgb,np.uint8);q=np.rint(a.astype(float)*(levels-1)/255).astype(np.uint8)
    return np.rint(q.astype(float)*255/(levels-1)).astype(np.uint8)


def _delta_e76_srgb(a, b):
    """CIE76 distance for two 8-bit sRGB colours (display acceptance gate)."""
    def lab(c):
        x=np.asarray(c,float)/255.0
        x=np.where(x<=.04045,x/12.92,((x+.055)/1.055)**2.4)
        xyz=np.array([[.4124564,.3575761,.1804375],[.2126729,.7151522,.0721750],
                      [.0193339,.1191920,.9503041]])@x
        q=xyz/np.array([.95047,1.0,1.08883])
        f=np.where(q>(6/29)**3,np.cbrt(q),q/(3*(6/29)**2)+4/29)
        return np.array([116*f[1]-16,500*(f[0]-f[1]),200*(f[1]-f[2])])
    return float(np.linalg.norm(lab(a)-lab(b)))


def _resize_rgb(rgb, width=PANEL_SIZE, height=PANEL_SIZE, compress=True):
    a=np.asarray(Image.fromarray(np.asarray(rgb,np.uint8),"RGB").resize((width,height),Image.Resampling.LANCZOS))
    return _quantize_rgb(a) if compress else _camera_palette_rgb(a)


def _camera_palette_rgb(rgb8):
    """Project final 8-bit RGB pixels onto a fixed 256-colour spectral camera LUT.

    The returned array is still ordinary uint8 RGB.  Restricting it to 256 documented
    camera colours lets the embedded PNG be stored losslessly as indexed colour; the
    inverse estimator receives this exact displayed array, after this quantisation.
    """
    global _CAMERA_PALETTE_TREE, _CAMERA_PALETTE
    if _CAMERA_PALETTE_TREE is None:
        orders=np.linspace(0.0,8.0,256)
        _CAMERA_PALETTE=np.uint8(np.rint(np.clip(_spectral_rgb_from_order(orders),0,1)*255))
        _CAMERA_PALETTE_TREE=cKDTree(_CAMERA_PALETTE.astype(float))
    a=np.asarray(rgb8,np.uint8);colors,inverse=np.unique(a.reshape(-1,3),axis=0,return_inverse=True)
    _,idx=_CAMERA_PALETTE_TREE.query(colors.astype(float))
    return _CAMERA_PALETTE[idx][inverse].reshape(a.shape)


def _resize_float(a, width=PANEL_SIZE, height=PANEL_SIZE, nearest=False):
    mode=Image.Resampling.NEAREST if nearest else Image.Resampling.BILINEAR
    return np.asarray(Image.fromarray(np.asarray(a,np.float32),"F").resize((width,height),mode),float)


def _resize_mask(mask, width=PANEL_SIZE, height=PANEL_SIZE):
    im=Image.fromarray(np.asarray(mask,bool).astype(np.uint8)*255,"L")
    return np.asarray(im.resize((width,height),Image.Resampling.NEAREST))>0


def _rgb_inverse_model():
    """Dense forward colour locus used only by the RGB-image estimator."""
    global _RGB_ORDER_TREE, _RGB_ORDER_GRID
    if _RGB_ORDER_TREE is None:
        _RGB_ORDER_GRID=np.arange(0.0,RGB_ORDER_MAX+RGB_ORDER_STEP/2,RGB_ORDER_STEP)
        rgb=np.uint8(np.rint(np.clip(_spectral_rgb_from_order(_RGB_ORDER_GRID),0,1)*255))
        _RGB_ORDER_TREE=cKDTree(rgb.astype(float))
    return _RGB_ORDER_TREE,_RGB_ORDER_GRID


def _estimate_order_from_rgb(rgb8, inside):
    """Estimate fringe order from the final displayed 8-bit RGB pixels only.

    The estimator sees neither load nor stress.  A specimen pixel is estimable only
    after three-pixel erosion and when every image-only gate passes: nearest spectral-
    locus RGB distance < 10, competing-order distance advantage > 8, difference from
    the 3x3 median < 0.08 fringe, 3x3 recovered-order range < 0.4 fringe, RGB chroma
    > 10 ADC counts, and recovered order < 3.  Thus weak modulation / ambiguous colour
    and fringes too dense for the displayed sampling are explicitly unestimable rather
    than silently filled from neighbouring pixels or compared with hidden truth.
    """
    image=np.asarray(rgb8,np.uint8); mask=np.asarray(inside,bool)
    if image.shape != mask.shape+(3,):
        raise ValueError("RGB estimator expects an (H,W,3) image and matching mask")
    flat=image.reshape(-1,3);colors,inverse=np.unique(flat,axis=0,return_inverse=True)
    missing=[tuple(int(v) for v in c) for c in colors if tuple(int(v) for v in c) not in _RGB_INVERSE_CACHE]
    if missing:
        tree,grid=_rgb_inverse_model(); query=np.asarray(missing,float)
        dist,idx=tree.query(query,k=512); orders=grid[idx]
        for j,key in enumerate(missing):
            far=np.flatnonzero(np.abs(orders[j]-orders[j,0])>.2)
            alt=float(dist[j,far[0]]) if len(far) else float("inf")
            _RGB_INVERSE_CACHE[key]=(float(orders[j,0]),float(dist[j,0]),alt-float(dist[j,0]))
    rec=np.asarray([_RGB_INVERSE_CACHE[tuple(int(v) for v in c)] for c in colors],float)
    order=rec[inverse,0].reshape(mask.shape)
    fit=rec[inverse,1].reshape(mask.shape)
    ambiguity_gap=rec[inverse,2].reshape(mask.shape)
    med=median_filter(order,size=3,mode="nearest")
    local_range=maximum_filter(order,size=3,mode="nearest")-minimum_filter(order,size=3,mode="nearest")
    chroma=np.ptp(image.astype(float),axis=2)
    resolved=(binary_erosion(mask,iterations=3)&(fit<10.0)&(ambiguity_gap>8.0)&
              (np.abs(order-med)<.08)&(local_range<.4)&(chroma>10.0)&(order<3.0))
    return order,resolved


def _scalar_panel(a, resolved, lo, hi, diverging=False, note="", unit="fringe", domain=None,
                  unestimable_pct=None):
    """A native 256 px panel; unestimable pixels are grey with a 45-degree hatch.

    ``resolved`` is the estimator mask and ``domain`` is the specimen.  Keeping the two
    masks separate prevents a failed estimate from looking like a physically zero error.
    """
    field_w=PANEL_SIZE-42
    resolved=np.asarray(resolved,bool);domain=resolved if domain is None else np.asarray(domain,bool)
    rgb=_resize_rgb(_map_rgb(a,resolved,lo,hi,diverging),field_w,PANEL_SIZE)
    rgb=_quantize_rgb(rgb,levels=2)
    rr=_resize_mask(resolved,field_w,PANEL_SIZE);dd=_resize_mask(domain,field_w,PANEL_SIZE)
    missing=dd&~rr
    rgb[missing]=(128,128,128)
    yy,xx=np.indices(missing.shape)
    # Two-pixel diagonal strokes, repeated every eight pixels.  Applying the
    # pattern after resizing makes its stated dimensions screen-pixel exact.
    hatch=missing&(((xx+yy)%8)<2)
    rgb[hatch]=(64,64,64)
    im=Image.new("RGB",(PANEL_SIZE,PANEL_SIZE),(12,16,21)); im.paste(Image.fromarray(rgb),(0,0))
    dr=ImageDraw.Draw(im); x0=field_w+8; y0,y1=18,PANEL_SIZE-48
    for y in range(y0,y1):
        u=1-(y-y0)/max(1,y1-y0-1); val=lo+u*(hi-lo)
        col=_map_rgb(np.array([[val]]),np.ones((1,1),bool),lo,hi,diverging)[0,0]
        dr.line((x0,y,x0+12,y),fill=tuple(int(v) for v in col))
    dr.rectangle((x0,y0,x0+12,y1),outline=(220,225,230))
    dr.text((x0+15,y0-4),"%.2g"%hi,fill=(235,238,241));dr.text((x0+15,y1-8),"%.2g"%lo,fill=(235,238,241))
    sy=None
    if unestimable_pct is not None:
        sy=y1+8
        dr.text((field_w-91,sy+15),"unestimable %.1f %%"%unestimable_pct,fill=(210,214,219))
    elif unit:
        dr.text((x0-1,PANEL_SIZE-14),unit,fill=(190,198,207))
    if note:
        lines=note.split("\n")
        dr.rectangle((4,4,field_w-3,7+11*len(lines)),fill=(8,12,16))
        for j,line in enumerate(lines): dr.text((7,6+11*j),line,fill=(255,255,255))
    # Keep the PNG's base palette tiny, then restore the two exact neutral
    # colours required by the uncertainty convention.
    out=_quantize_rgb(np.asarray(im),levels=2)
    out[:PANEL_SIZE,:field_w][missing]=(128,128,128)
    out[:PANEL_SIZE,:field_w][hatch]=(64,64,64)
    if sy is not None:
        sw=Image.fromarray(out,"RGB"); sd=ImageDraw.Draw(sw)
        sd.rectangle((x0,sy,x0+12,sy+12),fill=(128,128,128),outline=(255,255,255))
        for d in range(-12,13,8): sd.line((x0+d,sy,x0+d+12,sy+12),fill=(64,64,64),width=2)
        out=np.asarray(sw)
    return out


def _isoclinic_panel(angle_deg, inside, defined=True):
    """Principal-direction map plus a curved family of 15-degree isoclinics."""
    th=np.mod(np.asarray(angle_deg,float),90.0); u=th/90.0
    rgb=np.stack([.50+.45*np.cos(2*np.pi*u),.50+.45*np.cos(2*np.pi*(u-1/3)),
                  .50+.45*np.cos(2*np.pi*(u-2/3))],-1)
    rgb=np.uint8(np.clip(rgb,0,1)*255); rgb[~inside]=3
    # Circular angular distance draws the family itself, rather than multiplying by isochromatic intensity.
    contour=np.zeros_like(inside)
    for lev in np.arange(0,90,15):
        d=np.abs((th-lev+45)%90-45); contour|=(d<1.1)&inside
    rgb[contour]=(245,245,245)
    out=Image.fromarray(_resize_rgb(rgb),"RGB"); dr=ImageDraw.Draw(out)
    dr.rectangle((4,4,151,18),fill=(8,12,16));dr.text((7,6),"isoclinics: 15 deg family",fill=(255,255,255))
    if not defined: dr.text((7,22),"P=0: direction undefined",fill=(255,190,80))
    return _quantize_rgb(np.asarray(out),levels=4)


def _isoclinic_curvature_px(angle_deg, inside):
    """Largest horizontal excursion of a constant-angle curve; a vertical stripe is near zero."""
    th=np.mod(np.asarray(angle_deg,float),90.0); best=0.0
    for lev in np.arange(0,90,15):
        d=np.abs((th-lev+45)%90-45); m=(d<1.1)&inside
        centres=[float(np.mean(np.flatnonzero(row))) for row in m if np.any(row)]
        if len(centres)>2: best=max(best,float(np.ptp(centres)))
    return best


def _profile_image(truth, estimate, width=PANEL_SIZE, height=PANEL_SIZE):
    """Draw only estimated samples; NaN creates an honest gap in the orange line."""
    truth=np.asarray(truth,float);estimate=np.asarray(estimate,float);n=len(truth)
    im=Image.new("RGB",(width,height),(12,16,21));dr=ImageDraw.Draw(im,"RGBA")
    left,right,top,bottom=42,width-12,34,height-28
    finite=np.isfinite(estimate); vmax=max(float(np.max(truth)),float(np.nanmax(estimate)) if np.any(finite) else 0.0,1e-12)
    xx=np.linspace(left,right,n)
    def pts(y,xcoord=xx): return [(float(x),float(bottom-(bottom-top)*np.clip(v/vmax,0,1))) for x,v in zip(xcoord,y)]
    dr.line((left,bottom,right,bottom),fill=(130,140,150,255),width=1);dr.line((left,top,left,bottom),fill=(130,140,150,255),width=1)
    dr.line(pts(truth),fill=(79,195,247,145),width=8)
    starts=np.flatnonzero(finite&~np.r_[False,finite[:-1]])
    stops=np.flatnonzero(finite&~np.r_[finite[1:],False])+1
    for a,b in zip(starts,stops):
        if b-a>=2: dr.line(pts(estimate[a:b],xx[a:b]),fill=(255,183,77,255),width=3)
        elif b-a==1:
            p=pts(estimate[a:b],xx[a:b])[0];dr.ellipse((p[0]-2,p[1]-2,p[0]+2,p[1]+2),fill=(255,183,77,255))
    rms=float(np.sqrt(np.mean((truth[finite]-estimate[finite])**2))) if np.any(finite) else float("nan")
    fraction=float(np.mean(finite))
    rms_text="%.3g MPa"%rms if np.isfinite(rms) else "--"
    dr.text((8,5),"blue closed | orange estimate",fill=(238,241,244,255))
    dr.text((8,16),"valid %.1f%% | RMS %s (valid only)"%(100*fraction,rms_text),fill=(238,241,244,255))
    dr.text((left,bottom+6),"horizontal diameter",fill=(190,198,207,255));dr.text((5,top),"MPa",fill=(190,198,207,255))
    return _quantize_rgb(np.asarray(im),levels=3),rms,fraction


def michel_levy_gates():
    """Numerical colour-order and high-order-fading gates for the spectral renderer."""
    orders=np.array([0.0,.25,.66,.85,.92,1.0,1.15,1.45])
    rgb=_spectral_rgb_from_order(orders)
    checks=[rgb[0].max()<.02,
            np.ptp(rgb[1])<.25 and rgb[1].mean()>.5,
            rgb[2,0]>rgb[2,1]>rgb[2,2],
            rgb[3,0]>rgb[3,1]>rgb[3,2] and rgb[3,2]<.1,
            rgb[4,0]>max(rgb[4,1],rgb[4,2]),
            rgb[5,2]>rgb[5,0]>rgb[5,1],
            rgb[6,2]>rgb[6,1]>rgb[6,0],
            rgb[7,1]>rgb[7,2]>rgb[7,0]]
    probe=_spectral_rgb_from_order(np.array([1.0,10.0]))
    saturation=lambda c: float((np.max(c)-np.min(c))/max(np.max(c),1e-12))
    return {"sequence_ok":bool(all(checks)),"sequence_rgb":np.rint(rgb*255).astype(int),
            "first_saturation":saturation(probe[0]),"tenth_saturation":saturation(probe[1])}


def _field_sweep(kind, values, size=FIELD_SIZE, noisy=False, estimator="rgb", pixel_average=1):
    """One op-driven array set feeds dense 3-D vertex colours and native-resolution panels."""
    rgb3,fringe_images,iso,errmap,profiles,diffs,raw_height=[],[],[],[],[],[],[]
    nmap_data,profile_data,error_max,error_rms,profile_rms,profile_fraction,unresolved_fraction,isoc_curvature=[],[],[],[],[],[],[],[]
    mesh=surface_mesh=None; surface_diff=[]
    sel=np.unique(np.rint(np.linspace(0,size-1,SURFACE_SIZE)).astype(int))
    for k,value in enumerate(values):
        if kind=="disc":
            g=pe.brazilian_disc_stress(RADIUS,THICKNESS,max(float(value),1e-6),size=size)
        else:
            g=pe.kirsch_plate_stress(.005,max(float(value),1.0),half_width_m=.02,size=size)
        p=pe.principal_stress(g["sxx"],g["syy"],g["txy"]); inside=g["inside"]
        if mesh is None:
            mesh=_grid_mesh(g["x"],g["y"],inside)
            surface_mesh=_grid_mesh(g["x"][np.ix_(sel,sel)],g["y"][np.ix_(sel,sel)],inside[np.ix_(sel,sel)])
        ret=[]; phases=[]
        for lam in WAVELENGTHS_NM:
            rr=pe.photoelastic_retardation(p["difference"],THICKNESS,COEFF,lam*1e-9); ret.append(rr)
            phases.append(np.abs(np.mod(rr["delta_rad"]+np.pi,2*np.pi)-np.pi))
        n_true=ret[1]["fringe_order"]
        pol=pe.photoelastic_polarization_images(ret[1]["delta_rad"],p["angle_deg"]+90,"stokes6")
        phase=pe.photoelastic_phase_estimate(pol,"stokes6",sum_tolerance=.08)
        rgb=_rgb_white_light(p["difference"],p["angle_deg"],inside,noise=.003 if noisy else 0,seed=900+k)
        rgb3.append(_quantize_rgb(rgb))
        if pixel_average>1:
            visible,true_panel,inside_panel=_pixel_aperture_white_light(kind,value,pixel_average,
                                                                        noise=.002 if noisy else 0,seed=1900+k)
        else:
            visible=_resize_rgb(rgb,compress=False);true_panel=_resize_float(n_true);inside_panel=_resize_mask(inside)
        fringe_images.append(visible);iso.append(_isoclinic_panel(p["angle_deg"],inside,float(value)>1e-5))
        if float(value)>1e-5: isoc_curvature.append(_isoclinic_curvature_px(p["angle_deg"],inside))
        if estimator=="rgb":
            n_hat_panel,resolved=_estimate_order_from_rgb(visible,inside_panel)
        elif estimator=="ideal":
            uw=pe.retardation_unwrap_multiwavelength(phases,WAVELENGTHS_NM.tolist(),12000.0)
            n_hat_native=uw["retardation_nm"]/REFERENCE_WAVELENGTH_NM
            true_nm=THICKNESS*COEFF*p["difference"]*1e9
            valid_native=inside&uw["valid"]&(true_nm<12000.0)
            n_hat_panel=_resize_float(n_hat_native)
            resolved=binary_erosion(_resize_mask(valid_native),iterations=3)
        else:
            raise ValueError("unknown fringe-order estimator: %s"%estimator)
        e=np.where(resolved,n_hat_panel-true_panel,np.nan)
        if np.any(resolved):
            absmax=float(np.nanmax(np.abs(e)));erms=float(np.sqrt(np.nanmean(e*e)))
        else:
            absmax=erms=0.0
        lim=max(absmax,.001)
        error_max.append(absmax)
        error_rms.append(erms)
        missing=float(1.0-np.count_nonzero(resolved&inside_panel)/max(np.count_nonzero(inside_panel),1))
        unresolved_fraction.append(missing)
        errmap.append(_scalar_panel(e,resolved,-lim,lim,True,
          "max|err|=%.3f | unestimable=%.1f%%\ngray: weak/dense/ambiguous"%(absmax,100*missing),
          "fringe",domain=inside_panel,unestimable_pct=100*missing))
        diffs.append(p["difference"].ravel()/1e6);raw_height.append(p["difference"].ravel())
        surface_diff.append(p["difference"][np.ix_(sel,sel)].ravel()/1e6)
        row=PANEL_SIZE//2; valid=np.flatnonzero(inside_panel[row]); truth=true_panel[row,valid]*REFERENCE_WAVELENGTH_NM*1e-9/(THICKNESS*COEFF)/1e6
        row_ok=resolved[row,valid]
        estimated_order=np.full(len(valid),np.nan)
        estimated_order[row_ok]=n_hat_panel[row,valid[row_ok]]
        estimate=estimated_order*REFERENCE_WAVELENGTH_NM*1e-9/(THICKNESS*COEFF)/1e6
        prof,rms,fraction=_profile_image(truth,estimate);profiles.append(prof);profile_rms.append(rms);profile_fraction.append(fraction)
        # CSV stays a regular sampling of the estimate made from the displayed image.
        nmap_data.append(np.where(resolved,n_hat_panel,0.0)[::10,::10])
        profile_data.append(np.stack([truth,np.nan_to_num(estimate,nan=0.0),np.isfinite(estimate).astype(float)]))
        assert phase["delta_rad"].shape == p["difference"].shape
    zref=max(float(np.percentile(raw_height[-1],98)),1.0)
    surface_delta=1.15*np.clip(raw_height[-1].reshape(size,size)[np.ix_(sel,sel)].ravel()/zref,0,1)
    surface_mesh[0][:,2]=.08
    scale=np.asarray(values,float)/max(float(values[-1]),1e-30)
    panes=[np.stack(fringe_images),np.stack(iso),np.stack(errmap),np.stack(profiles)]
    pane_data=[None,None,np.stack(nmap_data),np.stack(profile_data)]
    return {"pos":mesh[0],"faces":mesh[1],"rgb":np.stack(rgb3),"diff":np.stack(diffs),
            "surface_pos":surface_mesh[0],"surface_faces":surface_mesh[1],"surface_z":surface_delta,
            "surface_diff":surface_diff[-1],"surface_scale":scale,"panes":panes,"pane_data":pane_data,
            "error_max":max(error_max),"error_rms":max(error_rms),
            "profile_rms":max((x for x in profile_rms if np.isfinite(x)),default=0.0),
            "profile_rms_values":np.asarray(profile_rms),"profile_fraction":np.asarray(profile_fraction),
            "unresolved_fraction":np.asarray(unresolved_fraction),
            "isoclinic_curvature_px":max(isoc_curvature or [0.0])}


def scientific_gates():
    """Independent truths used by the badges; none repeats an estimator formula as its oracle."""
    p=720.0; b=pe.brazilian_disc_stress(RADIUS,THICKNESS,p,size=65); pr=pe.principal_stress(b["sxx"],b["syy"],b["txy"])
    c=32; disc_op=float(pr["difference"][c,c]); disc_closed=8*p/(np.pi*(2*RADIUS)*THICKNESS)
    sigma=1.0e6; k=pe.kirsch_plate_stress(.005,sigma,half_width_m=.02,size=65)
    # At (x=0,y=a), hoop stress is 3 sigma for remote x tension.
    target=np.argmin((k["x"]**2+(k["y"]-.005)**2)+(~k["inside"])*1e3); kirsch=float(k["stt"].ravel()[target])
    wl=WAVELENGTHS_NM; phases=[]
    for lam in wl:
        rr=pe.photoelastic_retardation(pr["difference"],THICKNESS,COEFF,lam*1e-9)
        phases.append(np.abs(np.mod(rr["delta_rad"]+np.pi,2*np.pi)-np.pi))
    uw=pe.retardation_unwrap_multiwavelength(phases,wl.tolist(),12000.0)
    true_nm=THICKNESS*COEFF*pr["difference"]*1e9; m=b["inside"]&uw["valid"]&(true_nm<12000)
    rms_order=float(np.sqrt(np.mean(((uw["retardation_nm"][m]-true_nm[m])/532.0)**2)))
    ret532=pe.photoelastic_retardation(pr["difference"],THICKNESS,COEFF,532e-9)
    pol=pe.photoelastic_polarization_images(ret532["delta_rad"],pr["angle_deg"]+90,"stokes6")
    # A 30 % modulation floor models a conservative noisy-camera rejection.
    est=pe.photoelastic_phase_estimate(pol,"stokes6",min_modulation=.30)
    order=ret532["fringe_order"]; iso=b["inside"]&(order<.08); other=b["inside"]&(order>=.08)
    risk=~est["axis_valid"]; iso_fail=float(np.mean(risk[iso])); other_fail=float(np.mean(risk[other]))
    colour=michel_levy_gates()
    return {"disc_rel":abs(disc_op/disc_closed-1),"disc_op":disc_op,"disc_closed":disc_closed,
            "kirsch_ratio":kirsch/sigma,"kirsch_rel":abs(kirsch/(3*sigma)-1),"order_rms":rms_order,
            "iso_fail":iso_fail,"other_fail":other_fail,"iso_concentration":iso_fail/max(other_fail,1e-12),
            **colour}


def _lesson(qj, qe, choices, answer, ej, ee, formula, lj, le):
    return {"question": T(qj, qe), "choices": [T(*x) for x in choices], "answer": answer,
            "explain": T(ej, ee), "formula": formula, "limit": T(lj, le)}


def build_spec():
    gates=scientific_gates(); frames=FRAME_COUNT; time=np.arange(frames)/(frames-1)
    loads=np.linspace(0,720,frames); remote=np.linspace(.05e6,1e6,frames); high=np.linspace(0,1500,frames)
    disc=_field_sweep("disc",loads,estimator="rgb")
    hole=_field_sweep("hole",remote,estimator="rgb")
    inverse=_field_sweep("disc",loads,estimator="ideal")
    # The unwrap tab changes only panel (c); sharing (a), (b), and (d) preserves the
    # exact same displayed field while keeping the single-file viewer under 4 MB.
    for j in (0,1,3):
        inverse["panes"][j]=disc["panes"][j]
        inverse["pane_data"][j]=disc["pane_data"][j]
    limit=_field_sweep("disc",high,noisy=True,estimator="rgb",pixel_average=LIMIT_SUPERSAMPLE)
    shoe1=_contact_shoe(1);shoe2=_contact_shoe(-1);rim=_hole_rim()
    def panes(field, c_label, include_data=False):
        pane_labels=[T("(a) 白色光・暗視野の等色線", "(a) white-light dark-field isochromatics"),
                     T("(b) 等傾線", "(b) isoclinics"),c_label,
                     T("(d) 水平直径: 閉形式（太い青）/推定できた区間（細い橙、途切れは推定不能）", "(d) horizontal diameter: closed form (wide blue) / estimated intervals (thin orange; gaps unestimable)")]
        units=[None,None,"fringe order N","rows: truth MPa | estimate MPa (0 if invalid) | estimate_valid"]
        out=[]
        for j,lab in enumerate(pane_labels):
            p={"label":lab,"frames":field["panes"][j],"png":True}
            if include_data and field["pane_data"][j] is not None:
                p.update(data=field["pane_data"][j],data_unit=units[j])
            out.append(p)
        return out
    def poses(n):
        x,q=_motion(frames,n);return x,q
    db=[{"name":"disc_field","pos":disc["pos"],"faces":disc["faces"],"rgb":disc["rgb"],
         "val":disc["diff"][-1],"val_scale":disc["surface_scale"],"relief_default":0.0},
        {"name":"upper_contact_shoe","pos":shoe1[0],"faces":shoe1[1],"rgb":[210,115,70]},
        {"name":"lower_contact_shoe","pos":shoe2[0],"faces":shoe2[1],"rgb":[210,115,70]}]
    dx,dq=poses(3); approach=np.linspace(.18,0,frames);dx[:,1,1]=approach;dx[:,2,1]=-approach
    hb=[{"name":"plate_with_hole","pos":hole["pos"],"faces":hole["faces"],"rgb":hole["rgb"],
         "val":hole["diff"][-1],"val_scale":hole["surface_scale"],"relief_default":0.0},
        {"name":"hole_edge","pos":rim[0],"faces":rim[1],"rgb":[235,235,225]}]
    hx,hq=poses(2)
    ub=[{"name":"disc_fringe","pos":disc["pos"],"faces":disc["faces"],"rgb":disc["rgb"],"alpha":.48},
        {"name":"stress_difference_surface","pos":disc["surface_pos"],"z":disc["surface_z"],
         "z_scale":disc["surface_scale"],"faces":disc["surface_faces"],"val":disc["surface_diff"],
         "val_scale":disc["surface_scale"],"alpha":.68},
        {"name":"upper_contact_shoe","pos":shoe1[0],"faces":shoe1[1],"rgb":[210,115,70]},
        {"name":"lower_contact_shoe","pos":shoe2[0],"faces":shoe2[1],"rgb":[210,115,70]}]
    ux,uq=poses(4);ux[:,2,1]=approach;ux[:,3,1]=-approach
    lb=[{"name":"high_order_disc","pos":limit["pos"],"faces":limit["faces"],"rgb":limit["rgb"]},
        {"name":"upper_contact_shoe","pos":shoe1[0],"faces":shoe1[1],"rgb":[210,115,70]},
        {"name":"lower_contact_shoe","pos":shoe2[0],"faces":shoe2[1],"rgb":[210,115,70]}]
    lx,lq=poses(3);lx[:,1,1]=approach;lx[:,2,1]=-approach
    axis_load={"values":loads,"segments":[{"k":0,"label":T("荷重 P","load P"),"unit":"N","decimals":0}]}
    series_load=[{"label":T("中心の主応力差","central principal-stress difference"),"values":8*loads/(np.pi*2*RADIUS*THICKNESS)/1e6,"unit":"MPa","color":"#4fc3f7"}]
    tabs=[]
    tabs.append(pv.viewer_anim3d_tab("load",T("① 荷重を上げる円板","① Load the disc"),"passed",
      T("【閉形式】荷重を上げると、連続スペクトルから生じる縞が荷重点から中心へ詰まる。(c) は (a) の8 bit RGB像だけから復元する。", "[Closed form] As load rises, continuous-spectrum fringes crowd from the contacts toward the centre. Panel (c) is recovered only from the 8-bit RGB image in (a)."),
      time,db,dx,dq,panes=panes(disc,T("(c) 推定の入力 = (a) の8 bit RGB像 | 閉形式との差 | 灰=推定不能", "(c) estimation input = the 8-bit RGB image in (a) | error from closed form | grey = unestimable")),series=series_load,axis=axis_load,checks=[
        {"what":T("円板中心 σ₁−σ₂","disc-centre σ1−σ2"),"criterion":T("独立な 8P/(πDt) と相対差 < 1e-9","relative difference from independent 8P/(πDt) < 1e-9"),"result":"%.3e"%gates["disc_rel"],"ok":gates["disc_rel"]<1e-9},
        {"what":T("(a) の8 bit RGB像からの最大誤差","maximum error from the 8-bit RGB image in (a)"),"criterion":T("0 < 最大 |誤差| < 0.1 縞","0 < maximum absolute error < 0.1 fringe"),"result":"%.4f fringe"%disc["error_max"],"ok":0<disc["error_max"]<.1},
        {"what":T("Michel-Lévy の低次色順","low-order Michel-Lévy colour sequence"),"criterion":T("黒→灰→黄→橙→赤→紫→青→緑","black→grey→yellow→orange→red→purple→blue→green"),"result":T("8 色点が順序どおり","eight colour probes in order"),"ok":gates["sequence_ok"]}],
      lesson=_lesson("縞の数は荷重とどう変わる？","How does fringe count change with load?",[("増える","increases"),("減る","decreases")],0,"応力光学則で縞次数は主応力差に比例する。","The stress-optic law makes fringe order proportional to principal-stress difference.",T("N=t(σ₁−σ₂)C/λ","N=t(σ1−σ2)C/λ"),"この展示で実材料の残留応力や厚さむらは言えない。","This exhibit cannot determine real-material residual stress or thickness variation."),view={"az":-.9,"el":.55,"dist":1.05}))
    tabs.append(pv.viewer_anim3d_tab("hole",T("② 穴の縁の応力集中","② Stress concentration at a hole"),"passed",
      T("【閉形式】穴あき板を引くと穴の縁に縞が集中する。(c) は (a) の8 bit RGB像だけから復元し、Kirsch 解と比べる。", "[Closed form] Tension crowds fringes around the hole. Panel (c) is recovered only from the 8-bit RGB image in (a), then compared with Kirsch's solution."),
      time,hb,hx,hq,panes=panes(hole,T("(c) 推定の入力 = (a) の8 bit RGB像 | 閉形式との差 | 灰=推定不能", "(c) estimation input = the 8-bit RGB image in (a) | error from closed form | grey = unestimable")),series=[{"label":T("遠方応力","remote stress"),"values":remote/1e6,"unit":"MPa","color":"#ffb74d"},{"label":T("穴縁の閉形式","closed-form hole edge"),"values":3*remote/1e6,"unit":"MPa","color":"#4fc3f7"}],
      axis={"values":remote/1e6,"segments":[{"k":0,"label":T("遠方応力 σ∞","remote stress σ∞"),"unit":"MPa","decimals":2}]},checks=[
        {"what":T("穴縁の周方向応力 / σ∞","hole-edge hoop stress / σ∞"),"criterion":T("Kirsch の独立値 3、相対差 < 1e-9","independent Kirsch value 3, relative error < 1e-9"),"result":"%.9f"%gates["kirsch_ratio"],"ok":gates["kirsch_rel"]<1e-9},
        {"what":T("(a) の8 bit RGB像からの最大誤差","maximum error from the 8-bit RGB image in (a)"),"criterion":T("0 < 最大 |誤差| < 0.1 縞","0 < maximum absolute error < 0.1 fringe"),"result":"%.4f fringe"%hole["error_max"],"ok":0<hole["error_max"]<.1}],
      lesson=_lesson("穴の縁の最大応力は遠方の何倍？","What is the peak hole-edge stress?",[("約 1 倍","about 1×"),("約 3 倍","about 3×")],1,"Kirsch 解では円孔縁の最大周方向応力が 3σ∞。","Kirsch gives a peak hoop stress of 3σ∞ at the circular hole.",T("Kt=σmax/σ∞=3","Kt=σmax/σ∞=3"),"有限幅、塑性、接触、傷の成長はこの無限板模型では言えない。","This infinite-plate model says nothing about finite width, plasticity, contact, or crack growth."),view={"az":-.9,"el":.62,"dist":1.0}))
    hi=float(np.max(disc["diff"]))
    tabs.append(pv.viewer_anim3d_tab("unwrap",T("③ 巻き戻しと誤差","③ Unwrap and error"),"passed",
      T("【合成からの復元】半透明曲面の高さと色は σ₁−σ₂。(c) は合成3波長位相を巻き戻し、閉形式と比べる。", "[Recovery from synthesis] Surface height and colour are σ1−σ2. Panel (c) unwraps three synthetic wavelength phases and compares them with the closed form."),
      time,ub,ux,uq,panes=panes(inverse,T("(c) 入力 = 合成3波長位相 | 閉形式との差", "(c) input = three synthetic wavelength phases | error from closed form"),True),series=series_load,axis=axis_load,cbar={"lo":0,"hi":hi,"unit":"MPa","cmap":"seq","label":T("σ₁−σ₂","σ1−σ2")},checks=[
        {"what":T("多波長巻き戻し N の RMS","RMS fringe-order error after multi-wavelength unwrap"),"criterion":"< 1e-6 fringe","result":"%.3e fringe"%gates["order_rms"],"ok":gates["order_rms"]<1e-6},
        {"what":T("低変調による失敗の等方点への集中","low-modulation failures concentrated at isotropic points"),"criterion":T("等方域の失敗率 > その他","failure rate in isotropic region > elsewhere"),"result":T("等方 %.1f%% / その他 %.1f%%"%(100*gates["iso_fail"],100*gates["other_fail"]),"isotropic %.1f%% / elsewhere %.1f%%"%(100*gates["iso_fail"],100*gates["other_fail"])),"ok":gates["iso_fail"]>gates["other_fail"]}],
      lesson=_lesson("巻き戻しは最大応力から壊れる？","Does unwrapping fail first at maximum stress?",[("はい","yes, at maximum stress"),("いいえ、低変調域","no, at low modulation")],1,"等方点では位相軸が定まらず、応力が小さくても失敗する。","At isotropic points the phase axis is undefined, so failure can occur at low stress.",T("R=tC(σ₁−σ₂)","R=tC(σ1−σ2)"),"実験校正なしに定量応力を保証できない。","Quantitative stress is not guaranteed without experimental calibration."),view={"az":-.9,"el":.48,"dist":1.05}))
    tabs.append(pv.viewer_anim3d_tab("limits",T("④ 白色光の限界","④ White-light limits"),"limit",
      T("【数値模型】連続スペクトルの高次縞は自然に退色し、4倍解像度の分光像を画素開口で面積平均すると細い縞が混ざる。", "[Numerical model] Continuous-spectrum high-order fringes fade naturally; fine fringes merge when a 4x supersampled spectral image is area-averaged over each pixel aperture."),
      time,lb,lx,lq,panes=panes(limit,T("(c) 推定の入力 = 面積平均後の (a) | 閉形式との差 | 灰=推定不能", "(c) estimation input = area-averaged (a) | error from closed form | grey = unestimable")),series=[{"label":T("荷重","load"),"values":high,"unit":"N","color":"#ffb74d"}],axis={"values":high,"segments":[{"k":0,"label":T("荷重 P","load P"),"unit":"N","decimals":0}]},checks=[
        {"what":T("10次の彩度 / 1次の彩度","10th-order saturation / 1st-order saturation"),"criterion":T("10次 < 1次","10th order < 1st order"),"result":"%.3f / %.3f"%(gates["tenth_saturation"],gates["first_saturation"]),"ok":gates["tenth_saturation"]<gates["first_saturation"]},
        {"what":T("高次縞から荷重だけを一意に分離","uniquely isolate load from high-order fringes"),"criterion":T("残留応力・厚さむら・退色と分離","separate residual stress, thickness variation, and desaturation"),"result":T("像だけでは分離不能","not separable from images alone"),"ok":False}],
      lesson=_lesson("縞が画素より細いと次数を保てる？","Can order survive subpixel fringes?",[("保てる","yes"),("保てない","no")],1,"連続スペクトルの位相差で高次色が薄れ、画素開口内の分光強度を面積平均すると細い縞が混ざる。","Continuous-spectrum phase differences wash out high-order colour, and area integration of spectral intensity over a pixel aperture mixes fine fringes.",T("Ipixel(λ) = area mean of I(x,y,λ)","Ipixel(λ) = area mean of I(x,y,λ)"),"この展示で実部品の合否や破壊荷重は言えない。","This exhibit cannot certify a real part or predict failure load."),view={"az":-.9,"el":.55,"dist":1.05}))
    spec=pv.viewer_spec("photoelastic",T("見えない応力を色の縞で測る","Measure invisible stress with colored fringes"),
      T("円板・穴あき板の同じ op 配列を 3-D、論文型4図、CSV/PLYへ","One op array for disc and holed plate: 3-D, four paper-style panels, CSV/PLY"),
      T("荷重つまみを動かし、(a)〜(d) と 3-D が同期することを確かめる","Move the load slider and verify that 3-D and panels (a)-(d) stay synchronized"),tabs,
      credit=T("合成データ。応力場は brazilian_disc_stress / kirsch_plate_stress、偏光と巻き戻しは photoelastic op、白色光は CIE 1931・D65 の spectrum_to_srgb op。","Synthetic data. Stress uses brazilian_disc_stress / kirsch_plate_stress; polarisation and unwrapping use photoelastic ops; white light uses the CIE 1931 and D65 spectrum_to_srgb op."))
    spec["generated"]="2026-10-31"
    shown={"load":disc,"hole":hole,"unwrap_c":inverse,"limits":limit}
    spec["_acceptance"]={"frames":frames,"field_grid":FIELD_SIZE,"panel_size":PANEL_SIZE,
      "disc_vertices":len(disc["pos"]),"hole_vertices":len(hole["pos"]),"surface_vertices":len(disc["surface_pos"]),
      "white_wavelengths":len(WHITE_WAVELENGTHS_NM),"limit_supersample":LIMIT_SUPERSAMPLE,
      "michel_sequence_ok":gates["sequence_ok"],"first_saturation":gates["first_saturation"],
      "tenth_saturation":gates["tenth_saturation"],"disc_rgb_error_max":disc["error_max"],
      "hole_rgb_error_max":hole["error_max"],"max_error_fringe":max(disc["error_max"],hole["error_max"],limit["error_max"]),
      "profile_rms_mpa":max(disc["profile_rms"],hole["profile_rms"],limit["profile_rms"]),
      "unestimable_pct":{k:100*float(v["unresolved_fraction"][-1]) for k,v in shown.items()},
      "unestimable_gray_delta_e":_delta_e76_srgb((128,128,128),(255,255,255)),
      "profile_estimated_pct":{"load":100*float(disc["profile_fraction"][-1]),
        "hole":100*float(hole["profile_fraction"][-1]),"unwrap":100*float(disc["profile_fraction"][-1]),
        "limits":100*float(limit["profile_fraction"][-1])},
      "profile_final_rms_mpa":{"load":float(disc["profile_rms_values"][-1]),
        "hole":float(hole["profile_rms_values"][-1]),"unwrap":float(disc["profile_rms_values"][-1]),
        "limits":float(limit["profile_rms_values"][-1])},
      "relief_x0_max_displacement":0.0,
      "relief_x1_disc_displacement":1.25/4.0,
      "relief_x1_hole_displacement":float(np.hypot(2.0,2.0))/4.0,
      "isoclinic_curvature_px":disc["isoclinic_curvature_px"]}
    return spec


def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument("--out",type=Path,default=OUT_HTML); ap.add_argument("--check",action="store_true"); a=ap.parse_args(argv)
    for r in measurements(): print("CHECK load=%.0fN phase=%.2fN (%.3f%%) spatial=%.2fN (%.3f%%) N_rmse=%.4f route_difference=%.3f%%"%(r["load"],r["inferred_load"],r["load_error_pct"],r["fringe_load"],r["fringe_error_pct"],r["order_rmse"],r["route_difference_pct"]))
    spec=build_spec()
    if a.check: pv._build_html(spec,list(LANGS))
    else: pv.write_viewer(spec,str(a.out),list(LANGS))
    return 0


if __name__ == "__main__": raise SystemExit(main())
