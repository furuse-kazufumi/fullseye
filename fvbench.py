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
import fvbench_layer as layer

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
    slip_threshold2016: float = 900.0
    slip_threshold2017: float = 900.0
    proposed_ca_threshold: float = .12
    ridge_models: dict = field(default_factory=dict)
    ridge_selected: str = "raw"
    ridge_lambda: float = math.nan
    ridge_cv_rmse: dict = field(default_factory=dict)
    ridge_mu_warning: float = .8


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
    """接着層の接線 Green 関数を離散トラクションに重ね合わせる。"""
    out = np.zeros_like(points)
    for force, src in zip(loads, sources):
        out += layer.tangential_kernel(points, src, force, NU, E_GEL, THICKNESS*1e3)
    return out


def _physical_displacement(truth: Truth):
    fx, fy, p = truth.force_N
    centre = np.asarray(truth.contact_xy_mm)*1e-3
    d = MARKER_WORLD-centre; r = np.linalg.norm(d, axis=1)
    u = np.zeros_like(d); uz = np.zeros(len(d))
    if p <= 0: return u, uz
    hz = tacsim.hertz_sphere(p, truth.indenter_radius_mm*1e-3, tacsim.combined_modulus(E_GEL, NU))
    # 4 mm bonded layer: selectively integrated axisymmetric Q4 FEM table.
    normal = layer.normal_kernel(MARKER_WORLD, centre, NU, p, max(hz["a"]*1e3, 1.0))
    u += normal[:,:2]; uz += normal[:,2]
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
    if truth.angle_deg:
        # Stuck contact carries the object's in-plane rotation into the marker field.
        theta=math.radians(truth.angle_deg); tang=np.column_stack((-d[:,1],d[:,0]))
        u += theta*tang*np.exp(-(r/max(hz["a"],1e-6))**4)[:,None]
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
            return float(np.clip((s-.25)/.65,0,1).sum())
        ds.append(area(m1,b)-area(m0,a))
    return np.column_stack((u[:,0],np.asarray(ds),u[:,1])),tr


def _field_features(image, calib):
    """追跡点を35個の基準格子へ対応させた [dx,dy,ds] の固定長特徴。"""
    pm,tr=_per_marker(image,calib); out=np.zeros((len(MARKERS),3))
    if len(pm):
        dist=np.linalg.norm(tr["p0"][:,None,:]-MARKERS[None,:,:],axis=2)
        for i,j in enumerate(np.argmin(dist,axis=1)):
            if dist[i,j] < calib.marker_pitch_px*.45:
                out[j]=[pm[i,0],pm[i,2],pm[i,1]]
    return out.ravel(),tr


def _ridge_predict(model, feature):
    x=(np.asarray(feature)-model["mean"])/model["scale"]
    if model["basis"] is not None: x=x@model["basis"]
    return np.r_[x,1.]@model["coef"]


def read_field_ridge(image, calib, variant=None):
    """場全体のridge推定。学習済み画像特徴だけを読み、真値経路を持たない。"""
    feat,tr=_field_features(image,calib); key=variant or calib.ridge_selected
    if key not in calib.ridge_models:
        raise ValueError("field ridge is not calibrated")
    y=_ridge_predict(calib.ridge_models[key],feat); force=y[:3]
    ratio=np.linalg.norm(force[:2])/max(MU*max(force[2],0.),1e-9)
    visible=tr.get("matched",0)>=6
    return {"force_N":force,"torque":float(y[3]),"slip":bool(visible and ratio>=1.),
            "slip_precursor":bool(visible and ratio>=calib.ridge_mu_warning),
            "slip_dir":force[:2]/(np.linalg.norm(force[:2])+1e-12),
            "proximity":float(np.mean(np.abs(image-calib.reference)))>.018,
            "angle_deg":None,"matched":tr.get("matched",0),"load_ratio":float(ratio),
            "method":"full-field-ridge-"+key}


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
    return {"force_N":np.array([paper[0],paper[2],paper[1]]),"torque":None,"slip":score>calib.slip_threshold2016,
            "slip_dir":None,"proximity":prox,"angle_deg":None,"motion_pixels":score,"method":"FingerVision-2016"}


def read_baseline2017(image, calib):
    """2017公開式。論文 y は法線: [cx dx, cy sqrt(dx^2+dy^2), cz dy]、単純平均。"""
    pm,_=_per_marker(image,calib)
    feat=np.array([pm[:,0].mean(),np.hypot(pm[:,0],pm[:,2]).mean(),pm[:,2].mean()]) if len(pm) else np.zeros(3)
    paper=_affine(calib.coef2017,feat); score,prox=_baseline_common(image,calib)
    return {"force_N":np.array([paper[0],paper[2],paper[1]]),"torque":None,"slip":score>calib.slip_threshold2017,
            "slip_dir":None,"proximity":prox,"angle_deg":None,"motion_pixels":score,"method":"FingerVision-2017"}


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
    n=len(xy); K=np.zeros((3*n,3*n))
    for j,s in enumerate(xy):
        ex=layer.tangential_kernel(xy,s,[1.,0.],NU,E_GEL); ey=layer.tangential_kernel(xy,s,[0.,1.],NU,E_GEL)
        ez=layer.normal_kernel(xy,s,NU,1.,2.)
        K[:n,3*j]=ex[:,0]; K[n:2*n,3*j]=ex[:,1]
        K[:n,3*j+1]=ey[:,0]; K[n:2*n,3*j+1]=ey[:,1]
        K[:n,3*j+2]=ez[:,0]; K[n:2*n,3*j+2]=ez[:,1]; K[2*n:,3*j+2]=ez[:,2]
    # blob projected area A is proportional to (D-z)^-2: dz ~= D*dA/(2A).
    ref_area=math.pi*calib.marker_radius_px**2
    uz_m=np.clip(pm[:,1]/max(2*ref_area,1)*CAMERA_DISTANCE,-2e-3,2e-3)
    obs=np.r_[u_m[:,0],u_m[:,1],uz_m]; lam=3e-3*np.linalg.norm(K,2)**2
    traction=np.linalg.solve(K.T@K+lam*np.eye(3*n),K.T@obs).reshape(n,3)
    traction[:,2]=np.maximum(traction[:,2],0); q=traction[:,:2].sum(0); P=float(traction[:,2].sum())
    rr=np.linalg.norm(xy,axis=1)
    # Cattaneo--Mindlin: c/a=(1-Q/(mu P))^(1/3), using only reconstructed tractions.
    load_ratio=np.linalg.norm(q)/max(MU*P,1e-9)
    ca=float(max(0.,1-load_ratio)**(1/3))
    direction=q/(np.linalg.norm(q)+1e-12); omega=np.sum(xy[:,0]*u_m[:,1]-xy[:,1]*u_m[:,0])/np.sum(xy*xy)
    visible=tr["matched"]>=6
    return {"force_N":np.array([q[0],q[1],P]),"torque":float(4*math.pi*G_GEL*omega*np.mean(rr**3)),
            "slip":bool(visible and ca<calib.proposed_ca_threshold),"slip_precursor":bool(visible and ca<.45),"slip_dir":direction,
            "proximity":float(np.mean(np.abs(image-calib.reference)))>.018,"angle_deg":math.degrees(omega),
            "matched":tr["matched"],"c_over_a":ca,"method":"regularized-bonded-layer-FEM"}


def _fit_affine(x,y):
    x=np.asarray(x); y=np.asarray(y); A=np.column_stack((np.ones(len(x)),x))
    return np.linalg.lstsq(A,y,rcond=None)[0]


def _green_basis(rank=18):
    """層Green関数の単位荷重応答から作る物理基底（評価値は不使用）。"""
    cols=[]; xy=MARKER_WORLD
    for src in MARKER_WORLD[::2]:
        ex=layer.tangential_kernel(xy,src,[1.,0.],NU,E_GEL)
        ey=layer.tangential_kernel(xy,src,[0.,1.],NU,E_GEL)
        ez=layer.normal_kernel(xy,src,NU,1.,2.)
        cols += [np.column_stack((ex[:,0],ex[:,1],np.zeros(len(xy)))).ravel(),
                 np.column_stack((ey[:,0],ey[:,1],np.zeros(len(xy)))).ravel(),
                 np.column_stack((ez[:,0],ez[:,1],ez[:,2])).ravel()]
    u,_,_=np.linalg.svd(np.asarray(cols).T,full_matrices=False)
    return u[:,:min(rank,u.shape[1])]


def _fit_ridge_cv(X,Y,basis,lambdas,folds=5):
    """決定論的CV。返値は較正集合だけから決まり、評価集合の引数を持たない。"""
    X=np.asarray(X,float); Y=np.asarray(Y,float); n=len(X)
    # 連続する同一法線荷重（標準較正は接線5方向）を同じfoldへ置く。
    if n < 10:
        fold=np.arange(n)%min(folds,n)
    else:
        group=5 if n >= 50 else 3
        fold=(np.arange(n)//group)%min(folds,max(2,n//group))
    scores=[]
    for lam in lambdas:
        pred=np.zeros_like(Y)
        for k in range(fold.max()+1):
            va=fold==k; tr=~va; mu=X[tr].mean(0); sc=X[tr].std(0); sc[sc<1e-8]=1.
            a=(X[tr]-mu)/sc; b=(X[va]-mu)/sc
            if basis is not None: a=a@basis; b=b@basis
            aa=np.column_stack((a,np.ones(len(a)))); reg=np.eye(aa.shape[1]); reg[-1,-1]=0
            w=np.linalg.solve(aa.T@aa+lam*reg,aa.T@Y[tr]); pred[va]=np.column_stack((b,np.ones(len(b))))@w
        scores.append(float(np.sqrt(np.mean((pred-Y)**2))))
    lam=float(lambdas[int(np.argmin(scores))]); mu=X.mean(0); sc=X.std(0); sc[sc<1e-8]=1.
    a=(X-mu)/sc
    if basis is not None: a=a@basis
    aa=np.column_stack((a,np.ones(len(a)))); reg=np.eye(aa.shape[1]); reg[-1,-1]=0
    w=np.linalg.solve(aa.T@aa+lam*reg,aa.T@Y)
    return {"mean":mu,"scale":sc,"basis":basis,"coef":w,"lambda":lam,"cv_rmse":min(scores)}


def calibrate(samples, reference):
    """全手法を同一較正集合で学習。ridge のλ選択も較正内CVだけで行う。"""
    c=Calibration(np.asarray(reference),_marker_map(reference))
    try:
        import cv2
        bgr=(np.clip(reference[...,::-1],0,1)*255).astype(np.uint8); hsv=cv2.cvtColor(bgr,cv2.COLOR_BGR2HSV)
        yy,xx=np.mgrid[:HEIGHT,:WIDTH]; mask=((((xx-WIDTH/2)/74)**2+((yy-HEIGHT/2)/64)**2)<1).astype(np.uint8)
        c.hs_hist=cv2.calcHist([hsv],[0,1],mask,[100,10],[0,180,0,256]); cv2.normalize(c.hs_hist,c.hs_hist,0,255,cv2.NORM_MINMAX)
    except (ImportError,AttributeError):
        c.use_cv2=False
    f16=[]; f17=[]; fields=[]; truth=[]
    for im,force,torque in samples:
        pm,_=_per_marker(im,c); f16.append(_aggregate_signed(pm))
        f17.append([pm[:,0].mean(),np.hypot(pm[:,0],pm[:,2]).mean(),pm[:,2].mean()]); fields.append(_field_features(im,c)[0])
        truth.append([force[0],force[2],force[1]])
    f16=np.asarray(f16); f17=np.asarray(f17); truth=np.asarray(truth)
    c.coef2016=np.column_stack([_fit_affine(f16[:,i],truth[:,i]) for i in range(3)])
    c.coef2017=np.column_stack([_fit_affine(f17[:,i],truth[:,i]) for i in range(3)])
    target=np.asarray([[*force,float(torque)] for _,force,torque in samples])
    lambdas=np.logspace(-5,4,15); raw=_fit_ridge_cv(fields,target,None,lambdas)
    # Green基底は物理変位の単位が異なるため、特徴標準化後に直交化し直す。
    gb=_green_basis()
    # Green応答はraw特徴空間の基底。ridge入力と同じ標準化座標へ写す。
    field_scale=np.asarray(fields).std(0); field_scale[field_scale<1e-8]=1.
    gb=np.linalg.qr(gb/field_scale[:,None])[0]
    physical=_fit_ridge_cv(fields,target,gb,lambdas)
    c.ridge_models={"raw":raw,"green-pca":physical}
    c.ridge_cv_rmse={k:v["cv_rmse"] for k,v in c.ridge_models.items()}
    c.ridge_selected=min(c.ridge_cv_rmse,key=c.ridge_cv_rmse.get)
    c.ridge_lambda=c.ridge_models[c.ridge_selected]["lambda"]
    return c


def tune_slip_thresholds(calib, frames, budget=41):
    """Tune all three slip thresholds on the same frames and search budget."""
    import copy
    methods=(read_baseline2016,read_baseline2017,read_tactile); vals=[]
    for fn in methods:
        state=copy.copy(calib); state.previous=None; state.mog2=None; row=[]
        for image,_ in frames:
            out=fn(image,state); row.append(out.get("motion_pixels",out.get("c_over_a",1.)))
        vals.append(np.asarray(row))
    y=np.asarray([label for _,label in frames],bool)
    def best(v, reverse=False):
        candidates=np.linspace(float(v.min())-1e-9,float(v.max())+1e-9,budget); chosen=(0.,candidates[0])
        for t in candidates:
            p=v<t if reverse else v>t; tp=np.sum(p&y); score=2*tp/max(2*tp+np.sum(p&~y)+np.sum(~p&y),1)
            if score>chosen[0]: chosen=(float(score),float(t))
        return chosen[1]
    calib.slip_threshold2016=best(vals[0]); calib.slip_threshold2017=best(vals[1]); calib.proposed_ca_threshold=best(vals[2],True)
    return calib
