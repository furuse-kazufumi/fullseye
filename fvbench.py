# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""FingerVision 型センサの独立な物理合成と三つの画像推定器。

座標は ``(x, y, z) = (画像横の接線, 画像縦の接線, 法線)``。論文の座標は
``(x, y, z) = (画像横の接線, 法線, 画像縦の接線)`` なので、2016 式
``[cx*dx, cy*ds, cz*dy]`` は本 API では ``[Fx,Fz,Fy]`` に対応する。
順方向は Johnson (1985) 3.41b/3.42a の Hertz 表面変位、Cerruti 点荷重の
重ね合わせ、Cattaneo--Mindlin の ``c/a=(1-Q/(mu P))**(1/3)``、等距離魚眼
投影だけを使う。推定器の較正係数は合成器から参照されない。
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
import numpy as np
import tacsim
import tacslip

WIDTH, HEIGHT, FPS = 320, 240, 30.0
E_GEL, NU, THICKNESS = 0.18e6, 0.48, 4e-3
R_INDENTER, MU, CAMERA_DISTANCE = 12e-3, 0.65, 22e-3
G_GEL = E_GEL / (2 * (1 + NU))
FISHEYE_F = (WIDTH / 2) / (math.pi / 2)
MARKER_RADIUS_MM = 0.5


@dataclass(frozen=True)
class Truth:
    """評価専用真値。画像推定 API へは渡さない。"""
    force_N: tuple[float, float, float]
    torque_Nm: float = 0.0
    slip: bool = False
    slip_dir: tuple[float, float] = (0.0, 0.0)
    proximity: bool = False
    angle_deg: float = 0.0
    contact_xy_mm: tuple[float, float] = (0.0, 0.0)
    indenter_radius_mm: float = 12.0


@dataclass
class Calibration:
    reference: np.ndarray
    marker_reference: np.ndarray
    coef2016: np.ndarray = field(default_factory=lambda: np.zeros((2, 3)))
    coef2017: np.ndarray = field(default_factory=lambda: np.zeros((2, 3)))
    previous: np.ndarray | None = None
    use_cv2: bool = True
    mog2: object | None = None
    hs_hist: np.ndarray | None = None
    marker_dark: float = .72
    marker_radius_px: float = 2.4
    marker_pitch_px: float = 24.0


def _project(xy_m: np.ndarray, z_m=0.0) -> np.ndarray:
    """皮膚からカメラまで22 mmの等距離射影 r=f atan(r_world/z)。"""
    xy = np.asarray(xy_m, float)
    r = np.linalg.norm(xy, axis=1)
    rp = FISHEYE_F * np.arctan2(r, CAMERA_DISTANCE - np.asarray(z_m))
    scale = np.divide(rp, r, out=np.full_like(r, FISHEYE_F / CAMERA_DISTANCE), where=r > 1e-12)
    return np.array([WIDTH / 2, HEIGHT / 2]) + xy * scale[:, None]


def _marker_world() -> np.ndarray:
    x = np.arange(-15, 15.01, 5) * 1e-3
    y = np.arange(-10, 10.01, 5) * 1e-3
    xx, yy = np.meshgrid(x, y)
    return np.column_stack((xx.ravel(), yy.ravel()))


MARKER_WORLD = _marker_world()
MARKERS = _project(MARKER_WORLD)


def _background(color, brightness, phase, deform, moving_bg):
    yy, xx = np.mgrid[:HEIGHT, :WIDTH]
    p = phase * 13 if moving_bg else 0
    bg = np.stack((.55+.12*np.sin((xx+p)/21), .62+.10*np.cos((yy+p)/17), .68+.08*np.sin((xx+yy)/29)), -1)
    rgb = {"black": (.025,)*3, "skin": (.78,.55,.42), "bright": (.95,.72,.12)}[color]
    # deform は輪郭だけでなく物体テクスチャそのものを皮膚越しに移動させる。
    shift = 11*phase if deform else 0
    cx, rx = 160 + shift, 74*(1+.10*math.sin(phase) if deform else 1)
    mask = ((xx-cx)/rx)**2 + ((yy-120)/64)**2 < 1
    tex = .06*np.sin((xx-shift)/8)*np.cos((yy+shift*.3)/11)
    return np.clip(np.where(mask[...,None], np.asarray(rgb)+tex[...,None], bg)*brightness, 0, 1)


def _cerruti_point(points, loads, sources):
    """Cerruti 式3.22の面内2成分を離散トラクションに重ね合わせる。"""
    out = np.zeros_like(points)
    for force, src in zip(loads, sources):
        d = points-src; r = np.maximum(np.linalg.norm(d, axis=1), 0.7e-3)
        # 等方半空間の接線点荷重 Green テンソル。
        A = 1/(4*math.pi*G_GEL)
        out += A*(2*(1-NU)*force/r[:,None] + 2*NU*d*np.sum(d*force,axis=1)[:,None]/r[:,None]**3)
    return out


def _physical_displacement(truth: Truth):
    fx, fy, p = truth.force_N
    centre = np.asarray(truth.contact_xy_mm)*1e-3
    d = MARKER_WORLD-centre; r = np.linalg.norm(d, axis=1)
    u = np.zeros_like(d); uz = np.zeros(len(d))
    if p <= 0: return u, uz
    hz = tacsim.hertz_sphere(p, truth.indenter_radius_mm*1e-3, tacsim.combined_modulus(E_GEL, NU))
    uz = tacsim.hertz_surface_uz(r, hz["a"], hz["delta"], hz["R"])
    ur = tacslip.hertz_surface_ur(r, hz["a"], hz["p0"], G_GEL, NU)
    u += np.divide(d, r[:,None], out=np.zeros_like(d), where=r[:,None]>0)*ur[:,None]
    q = np.array([fx, fy]); qn = np.linalg.norm(q)
    if qn:
        q = q*min(1.0, MU*p/qn); ca = max(0.0, 1-qn/(MU*p))**(1/3)
        # Cattaneo--Mindlin: Hertz形 q'(a)-q''(c) を同心円点荷重で積分。
        ns = 48; ang = np.linspace(0, 2*math.pi, ns, endpoint=False)
        rad = hz["a"]*.58; src = centre + rad*np.column_stack((np.cos(ang),np.sin(ang)))
        weights = np.full((ns,2), q/ns)
        u += _cerruti_point(MARKER_WORLD, weights, src)
        if ca > 0:
            src2 = centre + rad*ca*np.column_stack((np.cos(ang),np.sin(ang)))
            u -= _cerruti_point(MARKER_WORLD, weights*ca**2, src2)
    if truth.torque_Nm:
        tang = np.column_stack((-d[:,1], d[:,0])); rr=np.maximum(r,1e-3)
        # Reissner--Sagoci/Cerruti の遠方 1/r^2。係数はトルク次元から決まる。
        u += truth.torque_Nm*tang/(4*math.pi*G_GEL*rr[:,None]**3)
    return u, uz


def synthesize(truth: Truth, *, color="bright", brightness=1.0, phase=0.0, deform=False, moving_bg=False, seed=0):
    """物理変位を22 mm等距離魚眼で撮る。手書きの荷重→px係数は持たない。"""
    bg = _background(color, brightness, phase if (truth.proximity or truth.slip or deform) else 0, deform, moving_bg)
    u, uz = _physical_displacement(truth)
    pts = _project(MARKER_WORLD+u, uz)
    # ds はビーズの法線移動による透視距離だけから決まる。
    radii = MARKER_RADIUS_MM*1e-3*FISHEYE_F/(CAMERA_DISTANCE-uz)
    out = bg.copy()
    yy, xx = np.mgrid[:HEIGHT,:WIDTH]
    for p, rad in zip(pts, radii):
        a=np.clip(1-((xx-p[0])**2+(yy-p[1])**2)/max(rad**2,1e-6),0,1)[...,None]
        out *= 1-.84*a
    rng=np.random.default_rng(seed)
    return np.clip(out+rng.normal(0,.004+.012*(1-brightness),out.shape),0,1)


def _marker_map(image):
    g=np.asarray(image,float).mean(-1); local=max(float(np.percentile(g,78)),.04)
    return np.clip(1-g/local,0,1)


def _track(image, calib):
    return tacslip.marker_track(_marker_map(calib.reference), _marker_map(image), calib.marker_dark,
                                calib.marker_pitch_px, calib.marker_radius_px)


def _per_marker(image, calib):
    tr=_track(image,calib)
    if tr["matched"]<4: return np.zeros((0,3)),tr
    u=tr["u"]; p0=tr["p0"]
    # 各 blob の局所暗画素面積差を ds とする。
    m0,m1=_marker_map(calib.reference),_marker_map(image); ds=[]
    for a,b in zip(p0,tr["p1"]):
        def area(m,p):
            x,y=np.rint(p).astype(int); s=m[max(0,y-4):y+5,max(0,x-4):x+5]
            return float((s>.42).sum())
        ds.append(area(m1,b)-area(m0,a))
    return np.column_stack((u[:,0],np.asarray(ds),u[:,1])),tr


def _aggregate_signed(v):
    """論文2016: 各要素で絶対値80 percentile以下を平均（符号は保つ）。"""
    out=[]
    for x in v.T:
        keep=np.abs(x)<=np.percentile(np.abs(x),80); out.append(float(x[keep].mean()) if keep.any() else 0.)
    return np.asarray(out)


def _affine(coef, x): return coef[0]+coef[1]*np.asarray(x)


def _motion(prev,image):
    d=np.mean(np.abs(image-prev),2); mask=np.asarray(image).mean(2)>.08
    return float(((d>.06)&mask).sum())


def _baseline_common(image,calib):
    prev=calib.previous if calib.previous is not None else calib.reference
    score=_motion(prev,image); calib.previous=np.asarray(image).copy()
    if calib.use_cv2:
        try:
            import cv2
            if calib.mog2 is None:
                calib.mog2=cv2.createBackgroundSubtractorMOG2(history=40,varThreshold=12,detectShadows=False)
                calib.mog2.apply((calib.reference[...,::-1]*255).astype(np.uint8),learningRate=1.)
            bgr=(np.clip(image[...,::-1],0,1)*255).astype(np.uint8)
            fg=calib.mog2.apply(bgr,learningRate=.02)>0
            hsv=cv2.cvtColor(bgr,cv2.COLOR_BGR2HSV)
            bp=cv2.calcBackProject([hsv],[0,1],calib.hs_hist,[0,180,0,256],1)
            score=float((fg&(bp>12)).sum())
        except (ImportError,AttributeError):
            calib.use_cv2=False
    return score, float(np.mean(np.abs(image-calib.reference)))>.025


def read_baseline2016(image, calib):
    """2016公開式。論文 y は法線: [cx dx, cy ds, cz dy]、|.|80%以下を平均。"""
    pm,_=_per_marker(image,calib); feat=_aggregate_signed(pm) if len(pm) else np.zeros(3)
    paper=_affine(calib.coef2016,feat); score,prox=_baseline_common(image,calib)
    return {"force_N":np.array([paper[0],paper[2],paper[1]]),"torque":0.,"slip":score>900,
            "slip_dir":None,"proximity":prox,"angle_deg":0.,"motion_pixels":score,"method":"FingerVision-2016"}


def read_baseline2017(image, calib):
    """2017公開式。論文 y は法線: [cx dx, cy sqrt(dx^2+dy^2), cz dy]、単純平均。"""
    pm,_=_per_marker(image,calib)
    feat=np.array([pm[:,0].mean(),np.hypot(pm[:,0],pm[:,2]).mean(),pm[:,2].mean()]) if len(pm) else np.zeros(3)
    paper=_affine(calib.coef2017,feat); score,prox=_baseline_common(image,calib)
    return {"force_N":np.array([paper[0],paper[2],paper[1]]),"torque":0.,"slip":score>900,
            "slip_dir":None,"proximity":prox,"angle_deg":0.,"motion_pixels":score,"method":"FingerVision-2017"}


read_baseline=read_baseline2016


def read_tactile(image, calib):
    """画像変位場をGreen関数の正則化最小二乗で逆算する公開 API。"""
    pm,tr=_per_marker(image,calib)
    if len(pm)<6:
        return {"force_N":np.zeros(3),"torque":0.,"slip":False,"slip_precursor":False,"slip_dir":np.zeros(2),
                "proximity":False,"angle_deg":0.,"matched":tr.get("matched",0),"c_over_a":1.}
    p=tr["p0"]; u=tr["u"]
    # 画像pxを射影の局所Jacobianでmへ戻す。
    u_m=u*(CAMERA_DISTANCE/FISHEYE_F)
    xy=(p-np.array([WIDTH/2,HEIGHT/2]))*(CAMERA_DISTANCE/FISHEYE_F)
    n=len(xy); K=np.zeros((2*n,2*n))
    for j,s in enumerate(xy):
        ex=_cerruti_point(xy,np.array([[1.,0.]]),np.array([s])); ey=_cerruti_point(xy,np.array([[0.,1.]]),np.array([s]))
        K[:n,2*j]=ex[:,0]; K[n:,2*j]=ex[:,1]; K[:n,2*j+1]=ey[:,0]; K[n:,2*j+1]=ey[:,1]
    obs=np.r_[u_m[:,0],u_m[:,1]]; lam=1e-4*np.linalg.norm(K,2)**2
    traction=np.linalg.solve(K.T@K+lam*np.eye(2*n),K.T@obs).reshape(n,2)
    q=traction.sum(0)
    # 法線は Hertz 3.41b の符号付き放射変位を候補荷重へ物理当てはめ。
    rr=np.linalg.norm(xy,axis=1); radial=np.sum(u_m*xy,axis=1)/np.maximum(rr,1e-9)
    cand=np.linspace(.25,25,100); err=[]
    for P in cand:
        h=tacsim.hertz_sphere(P,R_INDENTER,tacsim.combined_modulus(E_GEL,NU))
        err.append(np.mean((radial-tacslip.hertz_surface_ur(rr,h["a"],h["p0"],G_GEL,NU))**2))
    P=float(cand[int(np.argmin(err))])
    mag=np.linalg.norm(u_m,axis=1); core=np.percentile(mag,25); ca=float(np.clip(1-np.std(mag)/(core+1e-9),0,1))
    direction=q/(np.linalg.norm(q)+1e-12); omega=np.sum(xy[:,0]*u_m[:,1]-xy[:,1]*u_m[:,0])/np.sum(xy*xy)
    visible=tr["matched"]>=6
    return {"force_N":np.array([q[0],q[1],P]),"torque":float(4*math.pi*G_GEL*omega*np.mean(rr**3)),
            "slip":bool(visible and ca<.12),"slip_precursor":bool(visible and ca<.45),"slip_dir":direction,
            "proximity":float(np.mean(np.abs(image-calib.reference)))>.018,"angle_deg":math.degrees(omega),
            "matched":tr["matched"],"c_over_a":ca,"method":"regularized-Boussinesq-Cerruti"}


def _fit_affine(x,y):
    x=np.asarray(x); y=np.asarray(y); A=np.column_stack((np.ones(len(x)),x))
    return np.linalg.lstsq(A,y,rcond=None)[0]


def calibrate(samples, reference):
    """同一較正集合で2016/2017を切片付き最小二乗。提案法には係数を渡さない。"""
    c=Calibration(np.asarray(reference),_marker_map(reference))
    try:
        import cv2
        bgr=(np.clip(reference[...,::-1],0,1)*255).astype(np.uint8); hsv=cv2.cvtColor(bgr,cv2.COLOR_BGR2HSV)
        yy,xx=np.mgrid[:HEIGHT,:WIDTH]; mask=((((xx-WIDTH/2)/74)**2+((yy-HEIGHT/2)/64)**2)<1).astype(np.uint8)
        c.hs_hist=cv2.calcHist([hsv],[0,1],mask,[100,10],[0,180,0,256]); cv2.normalize(c.hs_hist,c.hs_hist,0,255,cv2.NORM_MINMAX)
    except (ImportError,AttributeError):
        c.use_cv2=False
    f16=[]; f17=[]; truth=[]
    for im,force,_ in samples:
        pm,_=_per_marker(im,c); f16.append(_aggregate_signed(pm))
        f17.append([pm[:,0].mean(),np.hypot(pm[:,0],pm[:,2]).mean(),pm[:,2].mean()]); truth.append([force[0],force[2],force[1]])
    f16=np.asarray(f16); f17=np.asarray(f17); truth=np.asarray(truth)
    c.coef2016=np.column_stack([_fit_affine(f16[:,i],truth[:,i]) for i in range(3)])
    c.coef2017=np.column_stack([_fit_affine(f17[:,i],truth[:,i]) for i in range(3)])
    return c
