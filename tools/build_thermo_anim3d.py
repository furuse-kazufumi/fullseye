# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""コンクリートの浮きをパルス赤外線で探す動く 3-D 教材。"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter, label, maximum_filter
from scipy.linalg import solve_banded

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pocviewer as pv

OUT_HTML = ROOT / "docs" / "view2026" / "anim3d" / "thermo_delamination_anim3d.html"
ALPHA = 7.0e-7
PX_MM = 2.0
DEPTHS_MM = np.array([8.0, 14.0, 22.0, 38.0])
CENTERS = ((12, 12), (12, 35), (35, 12), (35, 35))
RADII_PX = (5, 6, 7, 4)
TIMES = np.geomspace(1.0, 1800.0, 45)
NETD_K = 0.005
NX = 48
NZ = 61
DZ_M = 1.0e-3
DT_S = 1.0
K_CONCRETE = 1.4
CV_CONCRETE = K_CONCRETE / ALPHA
K_AIR = 0.026
CV_AIR = 1.2e3


def T(ja, en):
    return pv.viewer_text(ja, en)


def _e(x):
    return "< 1e-12" if abs(float(x)) < 1e-12 else "%.3g" % float(x)


def _masks(centers=CENTERS, radii=RADII_PX, n=NX):
    yy, xx = np.mgrid[:n, :n]
    out = []
    for (cy, cx), r in zip(centers, radii):
        out.append((yy-cy)**2 + (xx-cx)**2 <= r*r)
    return out


def _thermal_rgb(a):
    x = np.clip((a + 0.08) / 0.75, 0, 1)
    r = np.clip(2.2*x, 0, 1); g = np.clip(2.2*x-0.55, 0, 1); b = np.clip(2.2*x-1.35, 0, 1)
    return np.rint(255*np.stack([r, g, b], axis=-1)).astype(np.uint8)


def _fd_surface(times):
    """Explicit 1-D half-space pulse diffusion with the stability limit enforced."""
    dz = 0.5e-3
    dt = 0.12
    lam = ALPHA*dt/dz**2
    if lam > 0.5:
        raise ValueError("unstable explicit heat step")
    z = np.arange(240)*dz
    u = np.exp(-(z/(1.2*dz))**2)
    want = np.asarray(times); got=[]; k=0
    for n in range(int(math.ceil(want[-1]/dt))+1):
        now=n*dt
        while k<len(want) and now>=want[k]:
            got.append(float(u[0])); k+=1
        v=u.copy(); v[1:-1]=u[1:-1]+lam*(u[2:]-2*u[1:-1]+u[:-2]); v[0]=v[1]; v[-1]=0.0; u=v
        if k==len(want): break
    return np.asarray(got)


def _vertical_bands(depth_mm):
    """Backward-Euler depth operator for concrete, optionally with a 2 mm air layer."""
    k=np.full(NZ,K_CONCRETE); cv=np.full(NZ,CV_CONCRETE)
    if depth_mm is not None:
        q=int(round(float(depth_mm)))
        k[q:q+2]=K_AIR; cv[q:q+2]=CV_AIR
    face=2*k[:-1]*k[1:]/np.maximum(k[:-1]+k[1:],1e-30)
    up=np.zeros(NZ); dn=np.zeros(NZ)
    up[1:]=DT_S*face/(cv[1:]*DZ_M**2)
    dn[:-1]=DT_S*face/(cv[:-1]*DZ_M**2)
    ab=np.zeros((3,NZ)); ab[1]=1+up+dn; ab[0,1:]=-dn[:-1]; ab[2,:-1]=-up[1:]
    # The 60 mm boundary is held at ambient; the heated face is adiabatic after the pulse.
    ab[:, -1]=0; ab[1,-1]=1; ab[0,-1]=0
    return ab


def _solve_heat(depths, centers, radii, n=NX):
    """3-D finite differences: explicit x/y diffusion and implicit variable-k depth diffusion."""
    masks=_masks(centers,radii,n); code=np.zeros((n,n),np.int8)
    for i,m in enumerate(masks,1): code[m]=i
    yy,xx=np.mgrid[:n,:n]
    # A pulse deposits heat in the first millimetre; its smooth nonuniformity is a flux assumption.
    flux=1.0+0.12*(xx-(n-1)/2)/n+0.08*((yy-(n-1)/2)/n)**2
    u=np.zeros((n,n,NZ),np.float64); u[:,:,0]=50.0*flux
    bands=[_vertical_bands(None)]+[_vertical_bands(d) for d in depths]
    out=[]; wanted=np.rint(TIMES/DT_S).astype(int); wi=0
    lam=ALPHA*DT_S/(PX_MM*1e-3)**2
    if lam>0.25: raise ValueError("unstable lateral heat step")
    for step in range(1,int(wanted[-1])+1):
        # Fixed physical grid: reflected side boundaries, not a defect-dependent resize.
        p=np.pad(u,((1,1),(1,1),(0,0)),mode="edge")
        rhs=u+lam*(p[2:,1:-1]+p[:-2,1:-1]+p[1:-1,2:]+p[1:-1,:-2]-4*u)
        rhs[:,:,-1]=0.0
        for c,ab in enumerate(bands):
            ids=np.flatnonzero(code.ravel()==c)
            if ids.size:
                cols=rhs.reshape(-1,NZ)[ids].T
                u.reshape(-1,NZ)[ids]=solve_banded((1,1),ab,cols,overwrite_ab=False,overwrite_b=False).T
        while wi<len(wanted) and step>=wanted[wi]: out.append(u[:,:,0].copy()); wi+=1
    return np.asarray(out),masks


def _contrast_times(cube, masks):
    curves=[]; peaks=[]
    for m in masks:
        ring=gaussian_filter(m.astype(float),3.0)>.05; ring &= ~m
        c=cube[:,m].mean(axis=1)-cube[:,ring].mean(axis=1)
        curves.append(c); peaks.append(float(TIMES[int(np.argmax(c))]))
    return np.asarray(curves),np.asarray(peaks)


def compute():
    clean,masks=_solve_heat(DEPTHS_MM,CENTERS,RADII_PX)
    rng=np.random.default_rng(20261027)
    cube=clean+rng.normal(0,NETD_K,clean.shape)
    # Estimate the slowly varying healthy surface from the observation itself.
    residual=np.empty_like(cube)
    for k in range(len(TIMES)):
        residual[k]=cube[k]-gaussian_filter(cube[k],6.0,mode="reflect")
    peak=np.max(residual,axis=0); peak_i=np.argmax(residual,axis=0)
    threshold=4.0*NETD_K
    detect=gaussian_filter(peak,1.0,mode="reflect")
    seeds=(detect==maximum_filter(detect,9,mode="nearest")) & (detect>threshold)
    seeds[:6]=False; seeds[-6:]=False; seeds[:,:6]=False; seeds[:,-6:]=False
    found=[]
    sy,sx=np.nonzero(seeds)
    for cy0,cx0 in sorted(zip(sy,sx),key=lambda q:(round(q[0],6),round(q[1],6))):
        y0,y1=max(0,cy0-8),min(NX,cy0+9); x0,x1=max(0,cx0-8),min(NX,cx0+9)
        cut=detect[y0:y1,x0:x1]; labs,_=label(cut>max(threshold,.55*detect[cy0,cx0]))
        j=labs[cy0-y0,cx0-x0]; q=np.zeros_like(detect,dtype=bool)
        if j: q[y0:y1,x0:x1]=labs==j
        if q.sum()<8: continue
        y,x=np.nonzero(q); cy=float(y.mean()); cx=float(x.mean())
        area=float(q.sum()); tm=float(TIMES[int(np.argmax(residual[:,q].mean(axis=1)))])
        found.append({"cy":cy,"cx":cx,"area":area,"tmax":tm,"mask":q})
    found.sort(key=lambda q:(round(q["cy"],6),round(q["cx"],6)))
    # Match only for scoring. Detection and tmax above never receive truth masks or depths.
    matches=[]
    for cy,cx in CENTERS:
        near=min(found,key=lambda q:(q["cy"]-cy)**2+(q["cx"]-cx)**2) if found else None
        if near is not None and (near["cy"]-cy)**2+(near["cx"]-cx)**2 < 8**2:
            matches.append(near)
        else: matches.append(None)
    # Independent calibration simulation: different depths, positions and radii.
    cal_depth=np.array([10.,18.,30.]); cal_centers=((12,12),(12,35),(35,23)); cal_radii=(6,7,8)
    cal_cube,cal_masks=_solve_heat(cal_depth,cal_centers,cal_radii)
    _cal_contrast,cal_tmax=_contrast_times(cal_cube,cal_masks)
    fit=np.polyfit(cal_tmax,cal_depth**2,1)
    estimated=np.array([math.sqrt(max(0,np.polyval(fit,m["tmax"]))) if m else np.nan for m in matches])
    # Half-space check: normalize away pulse amplitude and compare shapes after early transients.
    chk_t=np.array([12.,24.,48.,96.]); fd=_fd_surface(chk_t); closed=1/np.sqrt(chk_t)
    fd/=fd[0]; closed/=closed[0]
    contrast,true_tmax=_contrast_times(clean,masks)
    display=np.stack([_thermal_rgb(x) for x in residual])
    return {"cube":cube,"clean":clean,"residual":residual,"frames":display,
            "peak":peak,"matches":matches,"estimated":estimated,"fit":fit,"fd":fd,"closed":closed,
            "masks":masks,"threshold":threshold,"contrast":contrast,"true_tmax":true_tmax,
            "cal_depth":cal_depth,"cal_tmax":cal_tmax}


def gates(r):
    visible=np.isfinite(r["estimated"])
    pos=[]; size=[]
    for (cy,cx),rad,m in zip(CENTERS,RADII_PX,r["matches"]):
        if m is not None:
            pos.append(PX_MM*math.hypot(m["cy"]-cy,m["cx"]-cx))
            size.append(abs(PX_MM*2*math.sqrt(m["area"]/math.pi)-PX_MM*2*rad))
    depth=np.abs(r["estimated"][visible]-DEPTHS_MM[visible])
    t=np.array([m["tmax"] for m in r["matches"] if m is not None])
    d2=DEPTHS_MM[visible]**2
    corr=float(np.corrcoef(t,d2)[0,1])
    return {"fd_rel":float(np.max(np.abs(r["fd"]-r["closed"]))),"position_mm":max(pos),
            "diameter_mm":max(size),"depth_mm":max(depth),"linearity":corr,"detected":int(visible.sum()),
            "deep_detected":bool(visible[-1]),"contrast_snr":np.max(r["contrast"],axis=1)/NETD_K}


def _wall_mesh():
    p=np.array([[x,y,z] for x in (-1.6,1.6) for y in (-1.1,1.1) for z in (-.18,.18)],float)
    f=np.array([[0,1,3],[0,3,2],[4,6,7],[4,7,5],[0,4,5],[0,5,1],[2,3,7],[2,7,6],[0,2,6],[0,6,4],[1,5,7],[1,7,3]])
    return p,f


def _disc(radius=.24,n=36):
    a=np.linspace(0,2*np.pi,n,endpoint=False); p=np.vstack([[0,0,0],np.column_stack([radius*np.cos(a),radius*np.sin(a),np.zeros(n)])]); f=[]
    for i in range(n): f.append([0,1+i,1+(i+1)%n])
    return p,np.asarray(f)


def _lesson(q, choices, answer, explain, formula, limit):
    return {"question":q,"choices":choices,"answer":answer,"explain":explain,"formula":formula,"limit":limit}


def _checks(g, limit=False):
    rows=[
      {"what":T("差分解と半無限体の冷却曲線","finite difference vs half-space cooling"),"criterion":"< 8 %","result":"%.2f %%"%(100*g["fd_rel"]),"ok":g["fd_rel"]<.08},
      {"what":T("画像から検出した中心位置","centre detected from images"),"criterion":"< 8 mm","result":"%.2f mm"%g["position_mm"],"ok":g["position_mm"]<8},
      {"what":T("画像から測った欠陥径","diameter measured from images"),"criterion":"< 14 mm","result":"%.2f mm"%g["diameter_mm"],"ok":g["diameter_mm"]<14},
      {"what":T("t_max から推定した深さ","depth estimated from t_max"),"criterion":"< 5 mm","result":"%.2f mm"%g["depth_mm"],"ok":g["depth_mm"]<5},
      {"what":T("t_max と深さの二乗の直線性","linearity of t_max and depth squared"),"criterion":"> 0.97","result":"%.4f"%g["linearity"],"ok":g["linearity"]>.97},
    ]
    if limit:
      rows.append({"what":T("深さ 38 mm の浮きを検出","detect the delamination at 38 mm"),"criterion":T("雑音の 4 倍を超える","exceeds 4 times the noise"),"result":T("検出できない","not detected"),"ok":False})
    return rows


def build_spec(r,g):
    wall,wf=_wall_mesh(); disc,df=_disc(); n=len(TIMES); bodies=6
    xyz=np.zeros((n,bodies,3)); quat=np.zeros((n,bodies,4)); quat[...,0]=1
    for i,((cy,cx),d) in enumerate(zip(CENTERS,DEPTHS_MM),start=1):
        xyz[:,i]=[(cx-48)/32,(48-cy)/42,.19-d/100]
    xyz[:,5]=[0,0,2.0]
    objs=[{"name":"wall","pos":wall,"faces":wf,"rgb":[125,135,145]}]
    objs += [{"name":"void%d"%i,"pos":disc,"faces":df,"rgb":[255,155,55],"alpha":.65} for i in range(4)]
    cam,cf=_wall_mesh(); objs.append({"name":"infrared camera","pos":cam*.16,"faces":cf,"rgb":[75,190,225]})
    pane={"label":T("近傍背景を引いた赤外線像","infrared image after local-background subtraction"),"frames":r["frames"]}
    axis={"values":TIMES,"segments":[{"k":0,"label":T("加熱後の時刻","time after heating"),"unit":"s","decimals":1}]}
    series=[{"label":T("時刻","time"),"color":"#90a4ae","values":TIMES,"lo":0,"hi":1800,"unit":"s","decimals":1}]
    depth_axis=np.linspace(float(DEPTHS_MM[0]),float(DEPTHS_MM[-1]),n)
    limit_axis={"values":depth_axis,"segments":[{"k":0,"label":T("欠陥深さ","defect depth"),"unit":"mm","decimals":1}]}
    limit_series=[{"label":T("ピークコントラスト/NETD","peak contrast / NETD"),"color":"#ff8a65",
                   "values":np.interp(depth_axis,DEPTHS_MM,g["contrast_snr"]),"lo":0,"hi":float(math.ceil(g["contrast_snr"][0])),
                   "threshold":4.0,"unit":"","decimals":2}]
    common=(TIMES,objs,xyz,quat)
    tabs=[]
    tabs.append(pv.viewer_anim3d_tab("why",T("なぜ浮きの上は熱いまま?","Why does a delamination stay warm?"),"passed",T("48×48×61 の固定格子で 3-D 熱伝導を解く。深さ方向 1 mm、面内 2 mm。空気層の 2 セルだけを空気の熱伝導率と熱拡散率にする。","3-D heat conduction is solved on a fixed 48×48×61 grid: 1 mm in depth and 2 mm laterally. Only 2 cells at each air layer use air conductivity and diffusivity."),*common,panes=[pane],series=series,checks=_checks(g),axis=axis,lesson=_lesson(T("空気層の上は加熱後どう冷える?","How does the surface above an air layer cool?"),[T("健全部より遅い","more slowly than sound concrete"),T("健全部より速い","faster than sound concrete")],0,T("奥へ逃げる熱が減るため、温度差が一時的に残る。","Less heat escapes into the depth, so a temporary contrast remains."),T("熱伝導: ∂T/∂t = α∇²T","heat conduction: ∂T/∂t = α∇²T"),T("格子は計算時間のため粗い。熱物性は説明用の仮定で、現場材料では測定が要る。","The grid is coarse to control runtime. Thermal properties are explanatory assumptions and require field measurement."))))
    tabs.append(pv.viewer_anim3d_tab("movie",T("温度むらを時間で見る","Watch the thermal pattern over time"),"passed",T("面内の加熱むらを表面パルスの分布として与え、5 mK のカメラ雑音を加える。表示像は各時刻の観測だけから局所背景を推定して引く。","Heating nonuniformity is applied as the surface-pulse distribution and 5 mK camera noise is added. The displayed local background is estimated from each observed frame alone."),*common,panes=[pane],series=series,checks=_checks(g),axis=axis,lesson=_lesson(T("欠陥が最も見やすい時刻は全部同じ?","Is the best viewing time identical for every defect?"),[T("深いほど遅い","deeper means later"),T("全部同じ","all are identical")],0,T("熱が往復する距離が長いほどピークは遅れる。","The peak arrives later when heat travels farther."),T("d ∝ √(α t_max)","d ∝ √(α t_max)"),T("表面の汚れや放射率差はこの模型に含めない。","Surface dirt and emissivity differences are omitted."))))
    tabs.append(pv.viewer_anim3d_tab("depth",T("ピーク時刻から深さを測る","Measure depth from peak time"),"passed",T("評価用とは別の 10、18、30 mm の欠陥をもう一度 3-D 計算し、その t_max だけで換算係数を決める。評価像の真の深さ・中心・健全部は推定器へ渡さない。","A separate 3-D simulation of 10, 18 and 30 mm calibration defects determines the conversion from t_max. True evaluation depths, centres and healthy background are never passed to the estimator."),*common,panes=[pane],series=series,checks=_checks(g),axis=axis,lesson=_lesson(T("t_max を 4 倍にすると推定深さは?","If t_max is multiplied by 4, what happens to depth?"),[T("2 倍","2 times"),T("4 倍","4 times")],0,T("深さは時刻の平方根に比例する。","Depth is proportional to the square root of time."),T("d² = a t_max + b","d² = a t_max + b"),T("校正用欠陥と同じ材料・加熱条件が必要。","Calibration defects require the same material and heating conditions."))))
    tabs.append(pv.viewer_anim3d_tab("limit",T("深い浮きは消える","A deep delamination disappears"),"limit",T("同じパルスと物性で解いたピークコントラストは深さとともに低下する。38 mm の小さい空気層だけが 4 NETD の検出門を越えない。","Peak contrast solved with the same pulse and properties decreases with depth. Only the small air layer at 38 mm remains below the 4-NETD detection gate."),*common,panes=[pane],series=limit_series,checks=_checks(g,True),axis=limit_axis,lesson=_lesson(T("見えない時は欠陥なしと言える?","Does no visible contrast prove there is no defect?"),[T("言えない","no"),T("言える","yes")],0,T("深さと大きさで信号が検出限界より小さくなる。","Depth and size can reduce the signal below the detection limit."),T("検出: contrast > 4 NETD","detection: contrast > 4 NETD"),T("日射、汚れ、含水、放射率を含まない。安全診断には使わない。","Sunlight, dirt, moisture and emissivity are omitted. Do not use this lesson for safety diagnosis."))))
    return pv.viewer_spec("thermo_delamination",T("温度のむらでコンクリートの浮きを探す","Find concrete delamination from thermal patterns"),T("パルス加熱・赤外線像・深さ推定を一つの因果でつなぐ","Connect pulse heating, infrared images and depth estimation in one causal model"),T("再生して温度像と時刻を一緒に見る","Play to watch the thermal image and time together"),tabs)


def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument("--out",default=str(OUT_HTML)); ap.add_argument("--check",action="store_true"); a=ap.parse_args(argv)
    r=compute(); g=gates(r); spec=build_spec(r,g)
    if a.check:
        print("ok: %d bytes (not written)"%len(pv._build_html(spec,["ja","en"]).encode("utf-8"))); return 0
    pv.write_viewer(spec,a.out,["ja","en"]); return 0


if __name__ == "__main__":
    main()
