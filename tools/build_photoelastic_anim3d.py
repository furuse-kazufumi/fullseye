#!/usr/bin/env python3
"""Photoelastic Brazilian-disc lesson for ViEW 2026."""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import photoelastic as pe  # noqa: E402
import pocviewer as pv  # noqa: E402

T = pv.viewer_text
OUT_HTML = ROOT / "docs" / "view2026" / "anim3d" / "photoelastic_anim3d.html"
LANGS = ("ja", "en")
RADIUS, THICKNESS, COEFF = 0.025, 0.006, 5.0e-11
WAVELENGTHS_NM = np.array([450.0, 532.0, 633.0])
LOADS = (240.0, 480.0, 720.0)
READ_NOISE = 0.01
FULL_WELL = 10_000
ADC_LEVELS = 256


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
    """White-light RGB camera sequence computed from three wavelengths, with seeded sensor noise."""
    rng=np.random.default_rng(20261027); out=[]
    yy,xx=np.mgrid[:size,:size]; illum=.90+.08*xx/(size-1)+.03*yy/(size-1)
    for load in load_values:
        g=pe.brazilian_disc_stress(RADIUS,THICKNESS,max(float(load),1e-3),size=size)
        p=pe.principal_stress(g["sxx"],g["syy"],g["txy"])
        channels=[]
        for lam in (633.0,532.0,450.0):
            ret=pe.photoelastic_retardation(p["difference"],THICKNESS,COEFF,lam*1e-9)
            im=pe.polariscope_intensity(ret["delta_rad"],setup="circular_dark")
            channels.append(im)
        rgb=np.stack(channels,-1)*illum[...,None]
        rgb+=rng.normal(0,.006,rgb.shape); rgb[~g["inside"]]=.018
        out.append(np.uint8(np.clip(rgb,0,1)*255))
    return out


def _grid_mesh(x, y, inside, scale=100.0):
    """Triangulate only complete grid cells; holes and specimen rims stay real geometry."""
    h, w = inside.shape
    ids = -np.ones((h, w), int)
    ids[inside] = np.arange(int(inside.sum()))
    pos = np.c_[x[inside] * scale, y[inside] * scale, np.zeros(int(inside.sum()))]
    faces = []
    for r in range(h - 1):
        for c in range(w - 1):
            q = ids[r:r + 2, c:c + 2]
            if np.all(q >= 0):
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


def _rgb_white_light(diff, angle, inside, thickness=THICKNESS, noise=0.0, fade=0.0, seed=0):
    channels=[]
    for lam in (633.0,532.0,450.0):
        ret=pe.photoelastic_retardation(diff,thickness,COEFF,lam*1e-9)
        channels.append(pe.polariscope_intensity(ret["delta_rad"],setup="circular_dark"))
    rgb=np.stack(channels,-1)
    if fade:
        order=pe.photoelastic_retardation(diff,thickness,COEFF,532e-9)["fringe_order"]
        rgb=.5+(rgb-.5)*np.exp(-fade*np.maximum(order-3,0))[...,None]
    if noise:
        rgb += np.random.default_rng(seed).normal(0,noise,rgb.shape)
    rgb=np.where(inside[...,None],rgb,.012)
    return np.uint8(np.clip(rgb,0,1)*255)


def _map_rgb(a, inside, lo=None, hi=None, diverging=False):
    v=np.asarray(a,float); good=inside & np.isfinite(v)
    if lo is None: lo=float(np.percentile(v[good],2)) if np.any(good) else 0.0
    if hi is None: hi=float(np.percentile(v[good],98)) if np.any(good) else 1.0
    u=np.clip((v-lo)/max(hi-lo,1e-12),0,1)
    if diverging:
        rgb=np.stack([np.clip(2*u,0,1),1-np.abs(2*u-1),np.clip(2*(1-u),0,1)],-1)
    else:
        rgb=np.stack([.15+.85*u,.25+.65*np.sqrt(u),.75-.65*u],-1)
    rgb[~inside]=.012
    return np.uint8(np.clip(rgb,0,1)*255)


def _profile_image(truth, estimate, width=96, height=48):
    im=np.full((height,width,3),12,np.uint8); n=len(truth); vmax=max(float(np.max(truth)),float(np.max(estimate)),1e-9)
    def draw(y,color):
        xx=np.linspace(4,width-5,n); yy=height-6-(height-12)*np.clip(y/vmax,0,1)
        for i in range(n-1):
            steps=max(1,int(abs(xx[i+1]-xx[i]))+1)
            xs=np.linspace(xx[i],xx[i+1],steps).astype(int); ys=np.linspace(yy[i],yy[i+1],steps).astype(int)
            im[np.clip(ys,0,height-1),np.clip(xs,0,width-1)]=color
    im[height-6,4:width-4]=70; im[5:height-5,4]=70
    draw(truth,[79,195,247]); draw(estimate,[255,183,77]); return im


def _field_sweep(kind, values, size=29, noisy=False, fade=0.0):
    """One op-driven array set feeds the 3-D field and synchronized panels (a)-(d)."""
    rgb3,fringe_images,iso,nmap,errmap,profiles,diffs,raw_height=[],[],[],[],[],[],[],[]
    nmap_data,profile_data=[],[]
    mesh=None
    for k,value in enumerate(values):
        if kind=="disc":
            g=pe.brazilian_disc_stress(RADIUS,THICKNESS,max(float(value),1e-6),size=size)
        else:
            g=pe.kirsch_plate_stress(.005,max(float(value),1.0),half_width_m=.02,size=size)
        p=pe.principal_stress(g["sxx"],g["syy"],g["txy"]); inside=g["inside"]
        if mesh is None: mesh=_grid_mesh(g["x"],g["y"],inside)
        ret=[]; phases=[]
        for lam in WAVELENGTHS_NM:
            rr=pe.photoelastic_retardation(p["difference"],THICKNESS,COEFF,lam*1e-9); ret.append(rr)
            phases.append(np.abs(np.mod(rr["delta_rad"]+np.pi,2*np.pi)-np.pi))
        # The displayed inverse follows the same multi-wavelength op as the PoC.
        uw=pe.retardation_unwrap_multiwavelength(phases,WAVELENGTHS_NM.tolist(),12000.0)
        n_true=ret[1]["fringe_order"]; n_hat=uw["retardation_nm"]/WAVELENGTHS_NM[1]
        # Exercise the polarization forward and inverse ops on the same field.
        pol=pe.photoelastic_polarization_images(ret[1]["delta_rad"],p["angle_deg"]+90,"stokes6")
        phase=pe.photoelastic_phase_estimate(pol,"stokes6",sum_tolerance=.08)
        isoc=np.sin(np.deg2rad(2*p["angle_deg"]))**2*np.sin(ret[1]["delta_rad"]/2)**2
        rgb=_rgb_white_light(p["difference"],p["angle_deg"],inside,noise=.018 if noisy else 0,
                             fade=fade,seed=900+k)
        rgb3.append(rgb[inside]);fringe_images.append(rgb);iso.append(_map_rgb(isoc,inside,0,1));nmap.append(_map_rgb(n_hat,inside,0,max(1,float(np.percentile(n_true[inside],98)))))
        e=np.where(inside,n_hat-n_true,np.nan); lim=max(.02,float(np.nanpercentile(np.abs(e),98)))
        errmap.append(_map_rgb(e,inside,-lim,lim,True));diffs.append(p["difference"][inside]/1e6)
        # Height is σ1−σ2, while x/y stay the specimen's physical coordinates.
        raw_height.append(p["difference"][inside])
        row=size//2; valid=np.flatnonzero(inside[row]); truth=p["difference"][row,valid]/1e6
        estimate=(n_hat[row,valid]*WAVELENGTHS_NM[1]*1e-9/(THICKNESS*COEFF))/1e6
        profiles.append(_profile_image(truth,estimate))
        nmap_data.append(np.where(inside,n_hat,0.0))
        profile_data.append(np.stack([truth,estimate]))
        assert phase["delta_rad"].shape == p["difference"].shape
    # A global vertical scale preserves the load-dependent surface amplitude.
    zref=max(float(np.percentile(raw_height[-1],98)),1.0)
    positions=np.stack([np.c_[mesh[0][:,:2],.08+1.15*np.clip(z/zref,0,1)] for z in raw_height])
    panes=[np.stack(fringe_images),np.stack(iso),
           np.concatenate([np.stack(nmap),np.stack(errmap)],axis=2),np.stack(profiles)]
    pane_data=[None,None,np.stack(nmap_data),np.stack(profile_data)]
    return {"pos":mesh[0],"faces":mesh[1],"rgb":np.stack([x for x in rgb3]),"diff":np.stack(diffs),
            "surface_pos":positions,"panes":panes,"pane_data":pane_data}


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
    return {"disc_rel":abs(disc_op/disc_closed-1),"disc_op":disc_op,"disc_closed":disc_closed,
            "kirsch_ratio":kirsch/sigma,"kirsch_rel":abs(kirsch/(3*sigma)-1),"order_rms":rms_order,
            "iso_fail":iso_fail,"other_fail":other_fail,"iso_concentration":iso_fail/max(other_fail,1e-12)}


def _lesson(qj, qe, choices, answer, ej, ee, formula, lj, le):
    return {"question": T(qj, qe), "choices": [T(*x) for x in choices], "answer": answer,
            "explain": T(ej, ee), "formula": formula, "limit": T(lj, le)}


def build_spec():
    rows=measurements(); gates=scientific_gates(); frames=9; time=np.arange(frames)/8.0
    loads=np.linspace(0,720,frames); remote=np.linspace(.05e6,1e6,frames); high=np.linspace(0,1800,frames)
    disc=_field_sweep("disc",loads); hole=_field_sweep("hole",remote); limit=_field_sweep("disc",high,noisy=True,fade=.32)
    shoe1=_contact_shoe(1);shoe2=_contact_shoe(-1);rim=_hole_rim()
    pane_labels=[T("(a) 白色光・暗視野の等色線", "(a) white-light dark-field isochromatics"),
                 T("(b) 等傾線", "(b) isoclinics"),
                 T("(c) 縞次数 N | 閉形式との差", "(c) fringe order N | error from closed form"),
                 T("(d) 水平直径: 推定（橙）/閉形式（青）", "(d) horizontal diameter: estimate (orange) / closed form (blue)")]
    def panes(field):
        units=[None,None,"fringe order N","MPa (truth | estimate)"]
        out=[]
        for j,lab in enumerate(pane_labels):
            p={"label":lab,"frames":field["panes"][j],"png":True}
            if field["pane_data"][j] is not None:
                p.update(data=field["pane_data"][j],data_unit=units[j])
            out.append(p)
        return out
    def poses(n):
        x,q=_motion(frames,n);return x,q
    db=[{"name":"disc_field","pos":disc["pos"],"faces":disc["faces"],"rgb":disc["rgb"]},
        {"name":"upper_contact_shoe","pos":shoe1[0],"faces":shoe1[1],"rgb":[210,115,70]},
        {"name":"lower_contact_shoe","pos":shoe2[0],"faces":shoe2[1],"rgb":[210,115,70]}]
    dx,dq=poses(3); approach=np.linspace(.18,0,frames);dx[:,1,1]=approach;dx[:,2,1]=-approach
    hb=[{"name":"plate_with_hole","pos":hole["pos"],"faces":hole["faces"],"rgb":hole["rgb"]},
        {"name":"hole_edge","pos":rim[0],"faces":rim[1],"rgb":[235,235,225]}]
    hx,hq=poses(2)
    ub=[{"name":"disc_fringe","pos":disc["pos"],"faces":disc["faces"],"rgb":disc["rgb"],"alpha":.48},
        {"name":"stress_difference_surface","pos":disc["surface_pos"],"faces":disc["faces"],"val":disc["diff"],"alpha":.68},
        {"name":"upper_contact_shoe","pos":shoe1[0],"faces":shoe1[1],"rgb":[210,115,70]},
        {"name":"lower_contact_shoe","pos":shoe2[0],"faces":shoe2[1],"rgb":[210,115,70]}]
    ux,uq=poses(4);ux[:,2,1]=approach;ux[:,3,1]=-approach
    lb=[{"name":"high_order_disc","pos":limit["pos"],"faces":limit["faces"],"rgb":limit["rgb"]},
        {"name":"upper_contact_shoe","pos":shoe1[0],"faces":shoe1[1],"rgb":[210,115,70]},
        {"name":"lower_contact_shoe","pos":shoe2[0],"faces":shoe2[1],"rgb":[210,115,70]}]
    lx,lq=poses(3);lx[:,1,1]=approach;lx[:,2,1]=-approach
    axis_load={"values":loads,"segments":[{"k":0,"label":T("荷重 P","load P"),"unit":"N","decimals":0}]}
    series_load=[{"label":T("中心の主応力差","central principal-stress difference"),"values":8*loads/(np.pi*2*RADIUS*THICKNESS)/1e6,"unit":"MPa","color":"#4fc3f7"}]
    max_phase=max(r["load_error_pct"] for r in rows)
    tabs=[]
    tabs.append(pv.viewer_anim3d_tab("load",T("① 荷重を上げる円板","① Load the disc"),"passed",
      T("荷重を上げると、荷重点から白色光の縞が湧き、中心へ詰まる。同じ op 配列を 3-D と (a)〜(d) に使う。根拠: 閉形式。", "As load rises, white-light fringes emerge at the contacts and crowd toward the centre. The 3-D field and panels (a)-(d) share one op array. Evidence: closed form."),
      time,db,dx,dq,panes=panes(disc),series=series_load,axis=axis_load,checks=[
        {"what":T("円板中心 σ₁−σ₂","disc-centre σ1−σ2"),"criterion":T("独立な 8P/(πDt) と相対差 < 1e-9","relative difference from independent 8P/(πDt) < 1e-9"),"result":"%.3e"%gates["disc_rel"],"ok":gates["disc_rel"]<1e-9},
        {"what":T("雑音入り偏光像からの荷重","load from noisy polarization images"),"criterion":T("3 荷重で最大誤差 < 2%","maximum error < 2% at three loads"),"result":"%.3f %%"%max_phase,"ok":max_phase<2}],
      lesson=_lesson("縞の数は荷重とどう変わる？","How does fringe count change with load?",[("増える","increases"),("減る","decreases")],0,"応力光学則で縞次数は主応力差に比例する。","The stress-optic law makes fringe order proportional to principal-stress difference.",T("N=t(σ₁−σ₂)C/λ","N=t(σ1−σ2)C/λ"),"この展示で実材料の残留応力や厚さむらは言えない。","This exhibit cannot determine real-material residual stress or thickness variation."),view={"az":-.9,"el":.55,"dist":1.05}))
    tabs.append(pv.viewer_anim3d_tab("hole",T("② 穴の縁の応力集中","② Stress concentration at a hole"),"passed",
      T("穴あき板を引くと穴の縁に縞が集中する。白い輪は計算領域の穴そのもので、箱による代用ではない。根拠: Kirsch の閉形式。", "Tension crowds fringes around the actual hole edge; the white ring marks the computed hole, not a box proxy. Evidence: Kirsch closed form."),
      time,hb,hx,hq,panes=panes(hole),series=[{"label":T("遠方応力","remote stress"),"values":remote/1e6,"unit":"MPa","color":"#ffb74d"},{"label":T("穴縁の閉形式","closed-form hole edge"),"values":3*remote/1e6,"unit":"MPa","color":"#4fc3f7"}],
      axis={"values":remote/1e6,"segments":[{"k":0,"label":T("遠方応力 σ∞","remote stress σ∞"),"unit":"MPa","decimals":2}]},checks=[
        {"what":T("穴縁の周方向応力 / σ∞","hole-edge hoop stress / σ∞"),"criterion":T("Kirsch の独立値 3、相対差 < 1e-9","independent Kirsch value 3, relative error < 1e-9"),"result":"%.9f"%gates["kirsch_ratio"],"ok":gates["kirsch_rel"]<1e-9}],
      lesson=_lesson("穴の縁の最大応力は遠方の何倍？","What is the peak hole-edge stress?",[("約 1 倍","about 1×"),("約 3 倍","about 3×")],1,"Kirsch 解では円孔縁の最大周方向応力が 3σ∞。","Kirsch gives a peak hoop stress of 3σ∞ at the circular hole.",T("Kt=σmax/σ∞=3","Kt=σmax/σ∞=3"),"有限幅、塑性、接触、傷の成長はこの無限板模型では言えない。","This infinite-plate model says nothing about finite width, plasticity, contact, or crack growth."),view={"az":-.9,"el":.62,"dist":1.0}))
    hi=float(np.max(disc["diff"]))
    tabs.append(pv.viewer_anim3d_tab("unwrap",T("③ 巻き戻しと誤差","③ Unwrap and error"),"passed",
      T("半透明曲面の高さと色は σ₁−σ₂、(c) 左は多波長で巻き戻した N、右は閉形式との差。根拠: 数値模型を閉形式で検証。", "The translucent surface height and color are σ1−σ2; panel (c) shows multi-wavelength N and its closed-form error. Evidence: numerical model checked by closed form."),
      time,ub,ux,uq,panes=panes(disc),series=series_load,axis=axis_load,cbar={"lo":0,"hi":hi,"unit":"MPa","cmap":"seq","label":T("σ₁−σ₂","σ1−σ2")},checks=[
        {"what":T("多波長巻き戻し N の RMS","RMS fringe-order error after multi-wavelength unwrap"),"criterion":"< 1e-6 fringe","result":"%.3e fringe"%gates["order_rms"],"ok":gates["order_rms"]<1e-6},
        {"what":T("低変調による失敗の等方点への集中","low-modulation failures concentrated at isotropic points"),"criterion":T("等方域の失敗率 > その他","failure rate in isotropic region > elsewhere"),"result":T("等方 %.1f%% / その他 %.1f%%"%(100*gates["iso_fail"],100*gates["other_fail"]),"isotropic %.1f%% / elsewhere %.1f%%"%(100*gates["iso_fail"],100*gates["other_fail"])),"ok":gates["iso_fail"]>gates["other_fail"]}],
      lesson=_lesson("巻き戻しは最大応力から壊れる？","Does unwrapping fail first at maximum stress?",[("はい","yes, at maximum stress"),("いいえ、低変調域","no, at low modulation")],1,"等方点では位相軸が定まらず、応力が小さくても失敗する。","At isotropic points the phase axis is undefined, so failure can occur at low stress.",T("R=tC(σ₁−σ₂)","R=tC(σ1−σ2)"),"実験校正なしに定量応力を保証できない。","Quantitative stress is not guaranteed without experimental calibration."),view={"az":-.9,"el":.48,"dist":1.05}))
    tabs.append(pv.viewer_anim3d_tab("limits",T("④ 白色光の限界","④ White-light limits"),"limit",
      T("高次縞は退色し、雑音と画素平均で区別できなくなる。壊れる条件を隠さず同じ場で示す。根拠: 数値模型。", "High-order fringes desaturate and merge under noise and pixel averaging. Failure conditions are shown on the same field. Evidence: numerical model."),
      time,lb,lx,lq,panes=panes(limit),series=[{"label":T("荷重","load"),"values":high,"unit":"N","color":"#ffb74d"}],axis={"values":high,"segments":[{"k":0,"label":T("荷重 P","load P"),"unit":"N","decimals":0}]},checks=[
        {"what":T("高次縞から荷重だけを一意に分離","uniquely isolate load from high-order fringes"),"criterion":T("残留応力・厚さむら・退色と分離","separate residual stress, thickness variation, and desaturation"),"result":T("像だけでは分離不能","not separable from images alone"),"ok":False}],
      lesson=_lesson("縞が画素より細いと次数を保てる？","Can order survive subpixel fringes?",[("保てる","yes"),("保てない","no")],1,"画素内平均と白色光の有限コヒーレンスで高次縞が退色する。","Pixel averaging and finite white-light coherence desaturate high-order fringes.",T("Δxfringe < pixel","Δxfringe < pixel"),"この展示で実部品の合否や破壊荷重は言えない。","This exhibit cannot certify a real part or predict failure load."),view={"az":-.9,"el":.55,"dist":1.05}))
    spec=pv.viewer_spec("photoelastic",T("見えない応力を色の縞で測る","Measure invisible stress with colored fringes"),
      T("円板・穴あき板の同じ op 配列を 3-D、論文型4図、CSV/PLYへ","One op array for disc and holed plate: 3-D, four paper-style panels, CSV/PLY"),
      T("荷重つまみを動かし、(a)〜(d) と 3-D が同期することを確かめる","Move the load slider and verify that 3-D and panels (a)-(d) stay synchronized"),tabs,
      credit=T("合成データ。応力場は brazilian_disc_stress / kirsch_plate_stress、偏光と巻き戻しは photoelastic op。","Synthetic data. Stress uses brazilian_disc_stress / kirsch_plate_stress; polarization and unwrapping use photoelastic ops."))
    spec["generated"]="2026-10-31"
    return spec


def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument("--out",type=Path,default=OUT_HTML); ap.add_argument("--check",action="store_true"); a=ap.parse_args(argv)
    for r in measurements(): print("CHECK load=%.0fN phase=%.2fN (%.3f%%) spatial=%.2fN (%.3f%%) N_rmse=%.4f route_difference=%.3f%%"%(r["load"],r["inferred_load"],r["load_error_pct"],r["fringe_load"],r["fringe_error_pct"],r["order_rmse"],r["route_difference_pct"]))
    spec=build_spec()
    if a.check: pv._build_html(spec,list(LANGS))
    else: pv.write_viewer(spec,str(a.out),list(LANGS))
    return 0


if __name__ == "__main__": raise SystemExit(main())
