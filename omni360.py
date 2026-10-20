"""Omnidirectional projection, resampling, stereo and inspection utilities.

Arrays follow the repository convention: gray images are ``(H,W)`` and colour
images ``(H,W,3)`` floating arrays.  Directions are unit ``(...,3)`` vectors.
Cubemap face order is ``+x,-x,+y,-y,+z,-z``.
"""
from __future__ import annotations

import math
import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation


def _unit(d):
    d = np.asarray(d, float)
    n = np.linalg.norm(d, axis=-1, keepdims=True)
    if np.any(~np.isfinite(d)) or np.any(n <= 0):
        raise ValueError("directions must be finite and non-zero")
    return d / n


def equirect_to_dir(h, w, uv=None):
    """Convert equirectangular pixel coordinates to unit directions."""
    if h <= 0 or w <= 0:
        raise ValueError("image dimensions must be positive")
    if uv is None:
        yy, xx = np.mgrid[0:h, 0:w]
        uv = np.stack((xx + .5, yy + .5), axis=-1)
    uv = np.asarray(uv, float)
    lon = uv[..., 0] * (2 * np.pi / w) - np.pi
    lat = np.pi / 2 - uv[..., 1] * (np.pi / h)
    cl = np.cos(lat)
    return np.stack((cl * np.sin(lon), np.sin(lat), cl * np.cos(lon)), axis=-1)


def dir_to_equirect(dirs, h, w):
    """Convert directions to continuous equirectangular ``(x,y)`` pixels."""
    d = _unit(dirs)
    lon = np.arctan2(d[..., 0], d[..., 2])
    lat = np.arcsin(np.clip(d[..., 1], -1, 1))
    return np.stack(((lon + np.pi) * w / (2*np.pi), (np.pi/2-lat)*h/np.pi), axis=-1)


def dir_to_cubemap(dirs, size=1):
    """Map directions to face index and continuous face pixels."""
    d = _unit(dirs); a = np.abs(d); axis = np.argmax(a, axis=-1)
    face = np.empty(axis.shape, int); u = np.empty(axis.shape); v = np.empty(axis.shape)
    for ax in range(3):
        for sign in (-1, 1):
            m = (axis == ax) & ((d[..., ax] >= 0) == (sign > 0))
            q = a[..., ax]
            if ax == 0:
                face[m] = 0 if sign > 0 else 1; u[m] = (-sign*d[..., 2]/q)[m]; v[m] = (-d[..., 1]/q)[m]
            elif ax == 1:
                face[m] = 2 if sign > 0 else 3; u[m] = (d[..., 0]/q)[m]; v[m] = (sign*d[..., 2]/q)[m]
            else:
                face[m] = 4 if sign > 0 else 5; u[m] = (sign*d[..., 0]/q)[m]; v[m] = (-d[..., 1]/q)[m]
    uv = np.stack(((u+1)*size/2, (v+1)*size/2), axis=-1)
    return face, uv


def cubemap_to_dir(face, uv, size=1):
    """Inverse of :func:`dir_to_cubemap`."""
    f = np.asarray(face, int); uv = np.asarray(uv, float)
    if np.any((f < 0) | (f > 5)) or size <= 0:
        raise ValueError("face must be in 0..5 and size positive")
    u = 2*uv[..., 0]/size-1; v = 2*uv[..., 1]/size-1
    d = np.empty(f.shape+(3,), float)
    forms = ((np.ones_like(u),-v,-u),(-np.ones_like(u),-v,u),
             (u,np.ones_like(u),v),(u,-np.ones_like(u),-v),
             (u,-v,np.ones_like(u)),(-u,-v,-np.ones_like(u)))
    for i, form in enumerate(forms):
        m=f==i; d[m]=np.stack(form,axis=-1)[m]
    return _unit(d)


def _radius(theta, model, f, k):
    if model == "equidistant": return f*theta
    if model == "equisolid": return 2*f*np.sin(theta/2)
    if model == "stereographic": return 2*f*np.tan(theta/2)
    if model == "orthographic": return f*np.sin(theta)
    if model == "polynomial":
        return f*sum(float(c)*theta**(2*i+1) for i,c in enumerate(k))
    raise ValueError("unknown fisheye model")


def fisheye_project(dirs, model="equidistant", f_px=1, centre=(0,0), k=(1,), fov_deg=180):
    """Project directions through a named rotationally symmetric fisheye."""
    d=_unit(dirs); theta=np.arccos(np.clip(d[...,2],-1,1)); limit=np.deg2rad(fov_deg/2)
    if np.any(theta > limit+1e-14): raise ValueError("direction lies outside fisheye field")
    r=_radius(theta,model,float(f_px),k); s=np.divide(r,np.sin(theta),out=np.full_like(r,float(f_px)),where=theta>1e-14)
    return np.stack((centre[0]+s*d[...,0], centre[1]-s*d[...,1]),axis=-1)


def fisheye_unproject(uv, model="equidistant", f_px=1, centre=(0,0), k=(1,), fov_deg=180):
    """Unproject fisheye pixels; polynomial inversion rejects ambiguous radii."""
    uv=np.asarray(uv,float); x=uv[...,0]-centre[0]; y=-(uv[...,1]-centre[1]); r=np.hypot(x,y); f=float(f_px)
    limit=np.deg2rad(fov_deg/2)
    if model == "equidistant": theta=r/f
    elif model == "equisolid": theta=2*np.arcsin(np.clip(r/(2*f),-1,1))
    elif model == "stereographic": theta=2*np.arctan(r/(2*f))
    elif model == "orthographic": theta=np.arcsin(np.clip(r/f,-1,1))
    elif model == "polynomial":
        grid=np.linspace(0,limit,2049)
        rv=_radius(grid,model,f,k); deriv=np.diff(rv)
        if np.any(deriv <= 0):
            turn=np.argmax(deriv<=0)+1; maxr=rv[turn]
            if np.any(r >= maxr): raise ValueError("polynomial is non-monotone at requested radius")
            grid=grid[:turn+1]; rv=rv[:turn+1]
        if np.any(r > rv[-1]+1e-12): raise ValueError("pixel lies outside calibrated polynomial")
        theta=np.interp(r,rv,grid)
        for _ in range(12):
            val=_radius(theta,model,f,k)-r
            der=f*sum((2*i+1)*float(c)*theta**(2*i) for i,c in enumerate(k))
            if np.any(der<=0): raise ValueError("polynomial inverse is not unique")
            theta-=val/der
    else: raise ValueError("unknown fisheye model")
    if np.any(theta > limit+1e-12): raise ValueError("pixel lies outside fisheye field")
    q=np.divide(np.sin(theta),r,out=np.full_like(r,1/f),where=r>1e-14)
    return _unit(np.stack((q*x,q*y,np.cos(theta)),axis=-1))


def perspective_project(dirs, fov_deg, size):
    d=_unit(dirs); h,w=(size,size) if np.isscalar(size) else size
    if np.any(d[...,2] <= 0): raise ValueError("point is behind the pinhole")
    f=.5*w/np.tan(np.deg2rad(fov_deg)/2)
    return np.stack((w/2+f*d[...,0]/d[...,2],h/2-f*d[...,1]/d[...,2]),axis=-1)


def perspective_unproject(uv, fov_deg, size):
    uv=np.asarray(uv,float); h,w=(size,size) if np.isscalar(size) else size; f=.5*w/np.tan(np.deg2rad(fov_deg)/2)
    return _unit(np.stack(((uv[...,0]-w/2)/f,-(uv[...,1]-h/2)/f,np.ones(uv.shape[:-1])),axis=-1))


def _sample(image, uv, wrap_x=False):
    im=np.asarray(image,float); x=uv[...,0]-.5; y=uv[...,1]-.5
    # Interpolation is a partition of unity; preserve that invariant exactly.
    if np.ptp(im) == 0:
        return np.full(uv.shape[:-1] + im.shape[2:], im.flat[0], dtype=float)
    if wrap_x: x=np.mod(x,im.shape[1])
    coords=[y,x]
    if im.ndim==2: return map_coordinates(im,coords,order=1,mode="nearest")
    return np.stack([map_coordinates(im[...,c],coords,order=1,mode="nearest") for c in range(im.shape[2])],axis=-1)


def cubemap_from_equirect(equi, face_size):
    """Resample an equirectangular image into six cubemap faces."""
    yy,xx=np.mgrid[0:face_size,0:face_size]; uv=np.stack((xx+.5,yy+.5),axis=-1)
    return np.stack([_sample(equi,dir_to_equirect(cubemap_to_dir(np.full((face_size,face_size),f),uv,face_size),*equi.shape[:2]),True) for f in range(6)])


def equirect_from_cubemap(cube, out_shape):
    """Resample six cubemap faces into an equirectangular image."""
    cube=np.asarray(cube,float); h,w=out_shape; d=equirect_to_dir(h,w); face,uv=dir_to_cubemap(d,cube.shape[1]); out=np.empty((h,w)+cube.shape[3:],float)
    for f in range(6):
        m=face==f; out[m]=_sample(cube[f],uv)[m]
    return out


def equirect_from_fisheye_pair(images, rotations, out_shape, model="equidistant",
                                f_px=None, centres=None, fov_deg=190, feather_deg=8):
    """Stitch two calibrated fisheyes and report overlap, seam error and blind spots."""
    ims=[np.asarray(x,float) for x in images]
    if len(ims)!=2 or len(rotations)!=2: raise ValueError("exactly two eye images and rotations are required")
    h,w=out_shape; world=equirect_to_dir(h,w); samples=[]; weights=[]
    for i,(im,R) in enumerate(zip(ims,rotations)):
        R=np.asarray(R,float); local=world@R
        theta=np.arccos(np.clip(local[...,2],-1,1)); valid=theta<=np.deg2rad(fov_deg/2)
        fp=float(f_px[i] if np.ndim(f_px) else (f_px if f_px is not None else min(im.shape[:2])*.45))
        cen=(centres[i] if centres is not None else (im.shape[1]/2,im.shape[0]/2))
        uv=fisheye_project(np.where(valid[...,None],local,np.array([0.,0.,1.])),
                           model=model, f_px=fp, centre=cen, fov_deg=fov_deg)
        inside=valid&(uv[...,0]>=.5)&(uv[...,0]<im.shape[1]-.5)&(uv[...,1]>=.5)&(uv[...,1]<im.shape[0]-.5)
        edge=np.deg2rad(fov_deg/2)-theta; weight=np.clip(edge/max(np.deg2rad(feather_deg),1e-12),0,1)*inside
        samples.append(_sample(im,uv)); weights.append(weight)
    den=weights[0]+weights[1]; blind=den==0; overlap=(weights[0]>0)&(weights[1]>0)
    shape=den.shape+(1,)*(samples[0].ndim-2); out=(samples[0]*weights[0][(...,)+(None,)*(samples[0].ndim-2)]+samples[1]*weights[1][(...,)+(None,)*(samples[1].ndim-2)])/np.where(den,den,1).reshape(shape)
    out[blind]=np.nan
    diff=np.mean(np.abs(samples[0]-samples[1]),axis=-1) if samples[0].ndim==3 else np.abs(samples[0]-samples[1])
    return {"image":out,"blind_mask":blind,"overlap_mask":overlap,"seam_error":np.where(overlap,diff,np.nan),"seam_mean":float(np.nanmean(np.where(overlap,diff,np.nan))) if overlap.any() else np.nan}


def equirect_from_perspectives(images, extrinsics, intrinsics, out_shape, feather=0.05):
    """Blend a calibrated perspective rig into an equirectangular image."""
    h,w=out_shape; world=equirect_to_dir(h,w); num=None; den=np.zeros((h,w))
    for im,R,K in zip(images,extrinsics,intrinsics):
        im=np.asarray(im,float); local=world@np.asarray(R,float); z=local[...,2]
        fx,fy,cx,cy=(K[k] for k in ("fx","fy","cx","cy")) if isinstance(K,dict) else (K[0,0],K[1,1],K[0,2],K[1,2])
        uv=np.stack((cx+fx*local[...,0]/np.where(z>0,z,1),cy-fy*local[...,1]/np.where(z>0,z,1)),axis=-1)
        inside=(z>0)&(uv[...,0]>=.5)&(uv[...,0]<im.shape[1]-.5)&(uv[...,1]>=.5)&(uv[...,1]<im.shape[0]-.5)
        edge=np.minimum.reduce((uv[...,0],im.shape[1]-uv[...,0],uv[...,1],im.shape[0]-uv[...,1]))
        wt=np.clip(edge/(feather*min(im.shape[:2])),0,1)*inside; sam=_sample(im,uv)
        if num is None: num=np.zeros_like(sam,float)
        num+=sam*wt[(...,)+(None,)*(sam.ndim-2)]; den+=wt
    out=num/np.where(den,den,1)[(...,)+(None,)*(num.ndim-2)]; out[den==0]=np.nan
    return {"image":out,"blind_mask":den==0,"weight":den}


def panorama_scene(h=256, w=512, seed=275, n_frames=30, fisheye_size=320):
    """Build a deterministic synthetic tunnel-and-bay inspection scene.

    The return value contains the equirectangular radiance and radial depth,
    truth masks for a crack and marked parts, six cubemap faces, a calibrated
    back-to-back 190-degree fisheye capture, and a moving panorama sequence.
    All dimensions are configurable and ``seed`` controls surface variation.
    """
    if min(h, w, fisheye_size) < 16 or n_frames < 1:
        raise ValueError("scene dimensions and frame count must be positive")
    rng = np.random.default_rng(seed)
    d = equirect_to_dir(h, w)
    lon = np.arctan2(d[..., 0], d[..., 2])
    lat = np.arcsin(np.clip(d[..., 1], -1, 1))
    # Corrugated cylindrical tunnel with a brighter service bay straight ahead.
    depth = 3.0 / np.maximum(np.sqrt(d[..., 0]**2 + d[..., 1]**2), .16)
    depth *= 1 + .035*np.sin(12*lon) + .02*np.cos(9*lat)
    mortar = .08*np.cos(24*lon) + .045*np.cos(18*lat)
    noise = rng.normal(0, .018, (h, w))
    base = .34 + mortar + noise
    bay = (np.abs(lon) < .42) & (np.abs(lat) < .31)
    base[bay] = .55 + .08*np.cos(7*lon[bay])*np.cos(8*lat[bay])
    crack_curve = -.36 + .11*np.sin(14*(lat + .08))
    crack = (np.abs(lon-crack_curve) < np.deg2rad(1.5)) & (lat > -.38) & (lat < .34)
    part_a = (np.abs(lon-.15) < .10) & (np.abs(lat-.05) < .075)
    part_b = (np.abs(lon+.18) < .075) & (np.abs(lat+.12) < .09)
    rgb = np.stack((base*.92, base, base*1.04), axis=-1)
    rgb[crack] = (.07, .025, .02)
    rgb[part_a] = (.92, .43, .08)
    rgb[part_b] = (.14, .72, .82)
    # Distance rings and a metric reference stripe make the inspection scale visible.
    rings = (np.cos(32*lat) > .975) & ~bay
    rgb[rings] = np.maximum(rgb[rings], (.62, .64, .58))
    rgb = np.clip(rgb, 0, 1)
    face_size = max(16, min(h//2, w//4))
    cube = cubemap_from_equirect(rgb, face_size)
    fs = int(fisheye_size); yy, xx = np.mgrid[0:fs, 0:fs]
    centre = (fs/2, fs/2); fpx = fs*.30
    pixels = np.stack((xx+.5, yy+.5), axis=-1)
    radius = np.hypot(xx+.5-centre[0], yy+.5-centre[1])
    valid = radius <= _radius(np.deg2rad(95), "equidistant", fpx, (1,))
    pixels = np.where(valid[..., None], pixels, np.asarray(centre))
    local = fisheye_unproject(pixels, f_px=fpx,
                              centre=centre, fov_deg=190)
    front_r = np.eye(3); back_r = _ypr(180, 0, 0)
    fisheyes = np.stack([_sample(rgb, dir_to_equirect(local @ r.T, h, w), True)
                         for r in (front_r, back_r)])
    fisheyes[:, ~valid] = 0
    t = np.linspace(0, 1, n_frames, endpoint=False)
    path = np.column_stack((-65 + 150*t, 7*np.sin(2*np.pi*t)))
    frames = np.stack([equirect_rotate(rgb, _ypr(-yaw, -pitch, 0))
                       for yaw, pitch in path])
    return {"equirect": rgb, "depth_m": depth, "cubemap": cube,
            "fisheyes": fisheyes, "fisheye_rotations": np.stack((front_r, back_r)),
            "fisheye_f_px": fpx, "fisheye_centres": (centre, centre),
            "crack_mask": crack, "part_masks": np.stack((part_a, part_b)),
            "frames": frames, "view_path_deg": path,
            "truth": {"tunnel_radius_m": 3.0, "crack_angular_width_deg": 3.0,
                      "crack_axial_extent_m": 2.16}}


def ods_render(scene_fn, ipd_m, h, w):
    """Render ODS rays using ``scene_fn(origins, directions)``."""
    d=equirect_to_dir(h,w); lon=np.arctan2(d[...,0],d[...,2]); tangent=np.stack((np.cos(lon),np.zeros_like(lon),-np.sin(lon)),axis=-1)
    left=scene_fn(-ipd_m/2*tangent,d); right=scene_fn(ipd_m/2*tangent,d)
    return np.asarray(left,float),np.asarray(right,float)


def ods_from_cubemap_pair(left_cube,right_cube,out_shape):
    return equirect_from_cubemap(left_cube,out_shape),equirect_from_cubemap(right_cube,out_shape)


def equirect_defect_unwrap_pipe(equi, axis="horizontal", radius_m=None, length_m=None):
    """Unwrap the cylindrical wall; equirect longitude is circumference and latitude is axial.

    Empty input (``equi`` has zero elements) returns an empty image (reason: an
    empty upstream inspection has no cylindrical samples to unwrap).
    """
    im=np.asarray(equi,float)
    if axis not in ("horizontal","vertical"): raise ValueError("axis must be horizontal or vertical")
    strip=im.copy() if axis=="horizontal" else np.swapaxes(im,0,1)
    return {"image":strip,"metres_per_pixel_circumference":None if radius_m is None else 2*np.pi*radius_m/strip.shape[1],"metres_per_pixel_axis":None if length_m is None else length_m/strip.shape[0]}


def viewport_from_equirect(equi,yaw=0,pitch=0,roll=0,fov_deg=90,size=(256,256)):
    """Extract a rectilinear viewer viewport from an equirectangular image."""
    h,w=(size,size) if np.isscalar(size) else size; yy,xx=np.mgrid[0:h,0:w]
    d=perspective_unproject(np.stack((xx+.5,yy+.5),axis=-1),fov_deg,(h,w)); R=_ypr(yaw,pitch,roll)
    return _sample(equi,dir_to_equirect(d@R.T,*equi.shape[:2]),True)


def _ypr(yaw,pitch,roll):
    y,p,r=np.deg2rad([yaw,pitch,roll]); cy,sy=np.cos(y),np.sin(y); cp,sp=np.cos(p),np.sin(p); cr,sr=np.cos(r),np.sin(r)
    return np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]])@np.array([[1,0,0],[0,cp,-sp],[0,sp,cp]])@np.array([[cr,-sr,0],[sr,cr,0],[0,0,1]])


def equirect_rotate(equi,R):
    """Apply a proper three-dimensional rotation to a panorama."""
    R=np.asarray(R,float)
    if R.shape!=(3,3) or not np.allclose(R.T@R,np.eye(3),atol=1e-9) or np.linalg.det(R)<0: raise ValueError("R must be a proper rotation")
    h,w=equi.shape[:2]; d=equirect_to_dir(h,w)@R
    return _sample(equi,dir_to_equirect(d,h,w),True)


def equirect_weight_map(h,w,solid_angle=False):
    """Return cosine-latitude weights, optionally normalised to four pi."""
    lat=np.pi/2-(np.arange(h)+.5)*np.pi/h; q=np.cos(lat)[:,None]*np.ones((1,w))
    if solid_angle: q*=4*np.pi/q.sum()
    return q


def ws_psnr(a,b,data_range=1.0):
    """Compute cosine-latitude weighted spherical PSNR.

    Identical inputs return ``inf``, the PSNR of zero mean-squared error.
    """
    a=np.asarray(a,float); b=np.asarray(b,float); w=equirect_weight_map(a.shape[0],a.shape[1]);
    if a.ndim==3: w=w[...,None]
    mse=np.sum(w*(a-b)**2)/(np.sum(w)*(a.shape[2] if a.ndim==3 else 1))
    return float(np.inf if mse==0 else 10*np.log10(data_range**2/mse))


def s_psnr(a,b,n=10000,data_range=1.0):
    """Compute PSNR at deterministic near-uniform sphere samples.

    Identical inputs return ``inf``, the PSNR of zero mean-squared error.
    """
    i=np.arange(n); y=1-2*(i+.5)/n; lon=(np.pi*(3-np.sqrt(5))*i+np.pi)%(2*np.pi)-np.pi
    d=np.stack((np.sqrt(1-y*y)*np.sin(lon),y,np.sqrt(1-y*y)*np.cos(lon)),axis=-1)
    aa=_sample(a,dir_to_equirect(d,*a.shape[:2]),True); bb=_sample(b,dir_to_equirect(d,*b.shape[:2]),True); mse=np.mean((aa-bb)**2)
    return float(np.inf if mse==0 else 10*np.log10(data_range**2/mse))


def equirect_filter_gaussian(image,sigma_deg):
    """Gaussian-filter a panorama with longitude scale adapted to latitude."""
    im=np.asarray(image,float); h,w=im.shape[:2]; sy=sigma_deg*h/180; out=np.empty_like(im)
    for y in range(h):
        lat=np.pi/2-(y+.5)*np.pi/h; sx=min(sigma_deg*w/(360*max(np.cos(lat),1e-3)),w/4)
        row=gaussian_filter(im, (0,sx) if im.ndim==2 else (0,sx,0), mode=("nearest","wrap") if im.ndim==2 else ("nearest","wrap","nearest"))[y]
        out[y]=row
    return gaussian_filter(out,(sy,0) if im.ndim==2 else (sy,0,0),mode="nearest")


def equirect_stabilise(frames, residual_limit=0.08, sample_shape=(24, 48)):
    """Estimate and remove camera rotations from an equirectangular sequence.

    Each frame is registered to the first one by minimising a cosine-latitude
    weighted photometric residual on the sphere.  The returned rotations map
    each input frame back to the reference.  ``removable`` is false when the
    remaining normalised RMS exceeds ``residual_limit``; callers must inspect
    it rather than silently treating translational/parallax motion as rotation.
    """
    fs = np.asarray(frames, float)
    if fs.ndim not in (3, 4) or len(fs) < 1 or not np.all(np.isfinite(fs)):
        raise ValueError("frames must be a finite (N,H,W[,C]) array")
    sh, sw = map(int, sample_shape)
    if sh < 8 or sw < 16 or residual_limit <= 0:
        raise ValueError("sample grid or residual limit is invalid")
    yy, xx = np.mgrid[0:sh, 0:sw]
    dirs = equirect_to_dir(sh, sw).reshape(-1, 3)
    uv0 = dir_to_equirect(dirs, *fs.shape[1:3])
    ref = _sample(fs[0], uv0, True)
    if ref.ndim == 1:
        ref = ref[..., None]
    weights = np.sqrt(equirect_weight_map(sh, sw)).reshape(-1, 1)
    scale = max(float(np.ptp(ref)), 1e-12)
    rotations = [np.eye(3)]
    residuals = [0.0]
    stable = [fs[0].copy()]
    previous = np.zeros(3)
    for frame in fs[1:]:
        # Global yaw seed avoids the discontinuity at the -180/180-degree wrap.
        gray_ref = ref.mean(-1).reshape(sh, sw)
        gray = _sample(frame, uv0, True)
        if gray.ndim == 2:
            gray = gray.mean(-1)
        gray = gray.reshape(sh, sw)
        score_weights = weights.reshape(sh, sw)
        scores = [np.sum(score_weights * gray_ref * np.roll(gray, k, axis=1)) for k in range(sw)]
        yaw = -2 * np.pi * int(np.argmax(scores)) / sw
        seed = previous.copy()
        seed[1] = yaw

        def fun(rotvec):
            r = Rotation.from_rotvec(rotvec).as_matrix()
            got = _sample(frame, dir_to_equirect(dirs @ r, *frame.shape[:2]), True)
            if got.ndim == 1:
                got = got[..., None]
            return ((got - ref) * weights / scale).ravel()

        fit = least_squares(fun, seed, method="trf", max_nfev=80,
                            xtol=1e-11, ftol=1e-11, gtol=1e-11)
        r = Rotation.from_rotvec(fit.x).as_matrix()
        rms = float(np.sqrt(np.mean(fun(fit.x) ** 2)))
        rotations.append(r); residuals.append(rms); previous = fit.x
        stable.append(equirect_rotate(frame, r))
    residuals = np.asarray(residuals)
    return {"frames": np.stack(stable), "rotations": np.stack(rotations),
            "residual": residuals, "removable": residuals <= residual_limit}


def ods_depth_to_disparity(depth_m,ipd_m,w):
    """Convert radial depth to ODS horizontal pixel disparity."""
    d=np.asarray(depth_m,float)
    if np.any(d<ipd_m/2): raise ValueError("depth is inside the eye circle")
    return 2*np.arcsin(ipd_m/(2*d))*w/(2*np.pi)


def ods_disparity_to_depth(disp_px,ipd_m,w):
    """Convert ODS horizontal pixel disparity to radial depth."""
    a=np.asarray(disp_px,float)*2*np.pi/w
    if np.any(a<=0) or np.any(a>=np.pi): raise ValueError("disparity must subtend an angle in (0,pi)")
    return ipd_m/(2*np.sin(a/2))


def stereo360_sbs(left,right):
    """Pack a panorama pair side by side."""
    return stereo_pack(left,right,"sbs")


def stereo360_top_bottom(left,right):
    """Pack a panorama pair top and bottom."""
    return stereo_pack(left,right,"tb")


_DUBOIS_L=np.array([[.456100,-.040082,-.015216],[.500484,-.037824,-.020597],[.176381,-.015759,-.005469]])
_DUBOIS_R=np.array([[-.043471,.378476,-.072153],[-.087939,.733640,-.112961],[-.001555,-.018450,1.226400]])


def anaglyph(left,right,method="dubois"):
    """Compose a colour-filter stereo image; Dubois matrices follow the 2001 least-squares paper."""
    l=np.asarray(left,float); r=np.asarray(right,float)
    if l.shape!=r.shape: raise ValueError("eye images must have equal shape")
    if l.ndim==2: l=np.repeat(l[...,None],3,axis=-1); r=np.repeat(r[...,None],3,axis=-1)
    if method=="dubois": out=l@_DUBOIS_L.T+r@_DUBOIS_R.T
    elif method=="true": out=np.stack((l.mean(-1),r.mean(-1),r.mean(-1)),axis=-1)
    elif method=="gray": out=np.stack((l.mean(-1),r.mean(-1),r.mean(-1)),axis=-1)
    elif method=="color": out=np.stack((l[...,0],r[...,1],r[...,2]),axis=-1)
    elif method=="half_color": out=np.stack((l.mean(-1),r[...,1],r[...,2]),axis=-1)
    elif method=="optimized": out=np.stack((.7*l[...,1]+.3*l[...,2],r[...,1],r[...,2]),axis=-1)
    else: raise ValueError("unknown anaglyph method")
    return np.clip(out,0,1)


def anaglyph_crosstalk(left,right,glasses_transmission=None,method="dubois"):
    """Return previews and wrong-eye/right-eye energy ratios."""
    if glasses_transmission is None: glasses_transmission=((1,0,0),(0,1,1))
    tl,tr=(np.asarray(x,float) for x in glasses_transmission); a=anaglyph(left,right,method)
    ls=a*tl; rs=a*tr
    wrong_l=np.sum((a*np.array([0,1,1])*tl)**2); right_l=np.sum((a*np.array([1,0,0])*tl)**2)
    wrong_r=np.sum((a*np.array([1,0,0])*tr)**2); right_r=np.sum((a*np.array([0,1,1])*tr)**2)
    return {"left_view":ls,"right_view":rs,"ghosting_left":float(wrong_l/right_l if right_l else np.inf),"ghosting_right":float(wrong_r/right_r if right_r else np.inf)}


def anaglyph_preview(left,right,**kwargs):
    q=anaglyph_crosstalk(left,right,**kwargs); return q["left_view"],q["right_view"]


def stereo_parallax_budget(disparity_px,width_px,viewing_distance_m,screen_width_m,ipd_m):
    """Report physical parallax and the common one- and three-percent limits."""
    mm=abs(float(disparity_px))/width_px*screen_width_m*1000; frac=mm/(screen_width_m*1000)
    return {"parallax_mm":mm,"screen_fraction":frac,"comfort_1pct":frac<=.01,"comfort_3pct":frac<=.03,
            "vergence_distance_m":float(ipd_m/(ipd_m/viewing_distance_m + np.sign(disparity_px)*mm/1000/max(viewing_distance_m,1e-12)))}


def stereo_pack(left,right,layout="sbs"):
    """Pack two eye images in a named display layout."""
    a=np.asarray(left); b=np.asarray(right)
    if a.shape!=b.shape: raise ValueError("eye images must have equal shape")
    if layout=="sbs": return np.concatenate((a,b),axis=1)
    if layout=="tb": return np.concatenate((a,b),axis=0)
    if layout=="interlaced":
        out=np.empty((a.shape[0]*2,)+a.shape[1:],a.dtype); out[0::2]=a; out[1::2]=b; return out
    if layout=="anaglyph": return anaglyph(a,b)
    raise ValueError("unknown stereo layout")


def stereo_unpack(packed,layout="sbs"):
    p=np.asarray(packed)
    if layout=="sbs": n=p.shape[1]//2; return p[:,:n],p[:,n:]
    if layout=="tb": n=p.shape[0]//2; return p[:n],p[n:]
    if layout=="interlaced": return p[0::2],p[1::2]
    raise ValueError("layout is not reversibly packed")


def anaglyph_from_ods(left,right,yaw=0,pitch=0,fov=90,size=(256,256),method="dubois"):
    """Extract an ODS viewport pair and compose a colour-filter view."""
    return anaglyph(viewport_from_equirect(left,yaw,pitch,0,fov,size),viewport_from_equirect(right,yaw,pitch,0,fov,size),method)


def video360_viewport_track(frames,yaw,pitch,fov=90,size=(256,256)):
    """Extract a moving viewport from an equirectangular frame sequence."""
    n=len(frames); ys=np.asarray(yaw(n) if callable(yaw) else yaw,float); ps=np.asarray(pitch(n) if callable(pitch) else pitch,float)
    if ys.size!=n or ps.size!=n: raise ValueError("view path length must equal frame count")
    return np.stack([viewport_from_equirect(frames[i],ys[i],ps[i],0,fov,size) for i in range(n)])


def video360_tile_coverage(view_path,tiles=(8,4),fov_deg=90):
    """Report which longitude-latitude streaming tiles a view path touches.

    Empty input (``view_path`` has zero elements) returns an empty coverage mask
    (reason: a path with no views requests no streaming tiles).
    """
    path=np.asarray(view_path,float); nx,ny=tiles; seen=np.zeros((ny,nx),bool)
    hy=fov_deg/2
    for yaw,pitch in path:
        cy=int(np.floor((pitch+90)/180*ny)); span=max(1,int(np.ceil(fov_deg/360*nx)))
        rows=np.where(np.abs((-90+(np.arange(ny)+.5)*180/ny)-pitch)<=hy)[0]
        c=int(np.floor((yaw%360)/360*nx)); seen[np.ix_(rows,(np.arange(c-span,c+span+1)%nx))]=True
    return {"mask":seen,"count":int(seen.sum()),"fraction":float(seen.mean())}
