# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""レーザー回折のリング信号から粉体の粒度分布を推定する動く 3-D 教材。"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import nnls
from scipy.special import j1, ndtr

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pocviewer as pv

OUT_HTML = ROOT / "docs" / "view2026" / "anim3d" / "laser_diffraction_anim3d.html"
LANGS = ("ja", "en")
WAVELENGTH_UM = 0.633
DIAMETERS = np.geomspace(3.0, 180.0, 48)
THETA_EDGES = np.geomspace(2.0e-4, 0.28, 57)
NOISE_FRACTION = 0.006


def T(ja, en):
    return pv.viewer_text(ja, en)


def _e(x):
    return "< 1e-12" if abs(float(x)) < 1e-12 else "%.3g" % float(x)


def airy_intensity(theta, diameter_um):
    z = np.pi * float(diameter_um) / WAVELENGTH_UM * np.sin(np.asarray(theta, float))
    out = np.ones_like(z)
    nz = np.abs(z) > 1e-14
    out[nz] = (2.0 * j1(z[nz]) / z[nz]) ** 2
    return out


def scattering_kernel(diameters=DIAMETERS, samples=25):
    """Ring-integrated Fraunhofer kernel; columns have unit total signal."""
    diameters=np.asarray(diameters,float)
    k = np.empty((len(THETA_EDGES)-1, len(diameters)))
    for i, (a, b) in enumerate(zip(THETA_EDGES[:-1], THETA_EDGES[1:])):
        th = np.geomspace(a, b, samples)
        for j, d in enumerate(diameters):
            k[i, j] = np.trapezoid(airy_intensity(th, d) * 2*np.pi*np.sin(th), th)
    return k / np.maximum(k.sum(axis=0, keepdims=True), 1e-30)


def _lognormal_weights(diameters, median, sigma):
    x = np.log(np.asarray(diameters,float))
    y = np.exp(-0.5*((x-np.log(median))/sigma)**2)
    return y/y.sum()


def distributions(diameters=DIAMETERS):
    one = _lognormal_weights(diameters,42.0,.23)
    two = .58*_lognormal_weights(diameters,18.0,.18) + .42*_lognormal_weights(diameters,92.0,.16)
    return {"single": one/one.sum(), "bimodal": two/two.sum()}


def continuous_percentile(name, q):
    if name == "single":
        # The distribution is normal in log diameter; bisection keeps this path independent of the estimator grid.
        lo,hi=np.log(1.0),np.log(300.0)
        cdf=lambda x: ndtr((x-np.log(42.0))/.23)
    else:
        lo,hi=np.log(1.0),np.log(300.0)
        cdf=lambda x: .58*ndtr((x-np.log(18.0))/.18)+.42*ndtr((x-np.log(92.0))/.16)
    for _ in range(80):
        mid=(lo+hi)/2
        if cdf(mid)<q: lo=mid
        else: hi=mid
    return float(np.exp((lo+hi)/2))


def _roughness_matrix(n):
    d = np.zeros((n-2, n))
    for i in range(n-2):
        d[i, i:i+3] = (1., -2., 1.)
    return d


def invert_signal(kernel, signal):
    """Choose smoothing from the L-curve only, then solve augmented NNLS."""
    scale = np.maximum(np.linalg.norm(kernel, axis=0), 1e-12)
    a = kernel/scale[None, :]
    l = _roughness_matrix(a.shape[1])
    alphas = np.geomspace(2e-5, 2e-1, 25)
    sols=[]; residual=[]; rough=[]
    for alpha in alphas:
        z = nnls(np.vstack([a, math.sqrt(alpha)*l]), np.r_[signal, np.zeros(l.shape[0])], maxiter=5000)[0]
        x = z/scale; x /= max(x.sum(), 1e-30)
        sols.append(x); residual.append(np.linalg.norm(kernel@x-signal)); rough.append(np.linalg.norm(l@z))
    p = np.column_stack([np.log(np.maximum(residual,1e-30)), np.log(np.maximum(rough,1e-30))])
    curvature=np.zeros(len(alphas))
    for i in range(1,len(alphas)-1):
        u=p[i]-p[i-1]; v=p[i+1]-p[i]
        curvature[i]=abs(u[0]*v[1]-u[1]*v[0])/(max(np.linalg.norm(u)*np.linalg.norm(v)*np.linalg.norm(u+v),1e-30))
    idx=int(np.argmax(curvature[2:-2])+2)
    return sols[idx], float(alphas[idx]), residual[idx]


def percentile(diameters, weights, q):
    c=np.cumsum(weights)/np.sum(weights)
    return float(np.interp(q, c, diameters))


def _simulate(kernel, name, seed, noise=NOISE_FRACTION):
    # Observation path: 6x finer, half-step shifted diameter grid and independently integrated angular kernel.
    ratio=DIAMETERS[1]/DIAMETERS[0]
    fine=np.geomspace(DIAMETERS[0]*ratio**(1/12),DIAMETERS[-1]/ratio**(1/12),len(DIAMETERS)*6)
    truth_fine=distributions(fine)[name]
    observation_kernel=scattering_kernel(fine,samples=42)
    clean=observation_kernel@truth_fine; rng=np.random.default_rng(seed)
    sigma=noise*clean.max()
    observed=np.maximum(clean+rng.normal(0,sigma,len(clean)),0)
    observed/=observed.sum()
    estimate,alpha,residual=invert_signal(kernel,observed)
    return clean,observed,estimate,alpha,residual,fine,truth_fine,observation_kernel


def _render_pattern(diameter_um, size=192, theta_max=.16):
    # Offset centre prevents the closed-form dark angle from landing on a pixel centre.
    yy,xx=np.mgrid[:size,:size]; centre=(size-1)/2+.31
    radius=np.sqrt((xx-centre)**2+(yy-centre)**2); theta=radius*(theta_max/(size/2))
    return np.uint8(np.round(np.clip(airy_intensity(theta,diameter_um),0,1)*255))


def measure_first_dark(image, theta_max=.16):
    centre=(image.shape[1]-1)/2+.31; row=int(round(centre))
    profile=image[row,int(math.ceil(centre)):].astype(float)
    candidates=np.flatnonzero((profile[1:-1] <= profile[:-2]) & (profile[1:-1] < profile[2:]))+1
    i=int(candidates[0]); y=profile[i-1:i+2]
    delta=.5*(y[0]-y[2])/max(y[0]-2*y[1]+y[2],1e-30)
    pixel_radius=(int(math.ceil(centre))+i+delta)-centre
    return float(pixel_radius*theta_max/(image.shape[1]/2))


def compute():
    kernel=scattering_kernel(); display_truths=distributions(); cases={}
    for n,name in enumerate(("single","bimodal")):
        clean,obs,est,alpha,residual,fine,truth_fine,observation_kernel=_simulate(kernel,name,8100+n)
        cases[name]={"truth":display_truths[name],"fine_diameters":fine,"fine_truth":truth_fine,"observation_kernel":observation_kernel,
          "clean":clean,"observed":obs,"estimate":est,"alpha":alpha,"residual":residual,
          "true_d10":continuous_percentile(name,.1),"true_d50":continuous_percentile(name,.5),"true_d90":continuous_percentile(name,.9),
          "d10":percentile(DIAMETERS,est,.1),"d50":percentile(DIAMETERS,est,.5),"d90":percentile(DIAMETERS,est,.9)}
    noise_d50=[]
    for seed in range(12):
        noise_d50.append(percentile(DIAMETERS,_simulate(kernel,"single",9000+seed)[2],.5))
    dark_image=_render_pattern(48.0); dark=measure_first_dark(dark_image); closed=1.22*WAVELENGTH_UM/48.0
    grid_half=(math.sqrt(DIAMETERS[1]/DIAMETERS[0])-1)*100
    return {"kernel":kernel,"cases":cases,"dark":dark,"dark_closed":closed,"dark_error":abs(dark-closed),
            "dark_image":dark_image,"noise_d50":np.asarray(noise_d50),"noise_cv":float(np.std(noise_d50)/np.mean(noise_d50)),
            "grid_half_percent":grid_half}


def gates(r):
    bound=r["grid_half_percent"]+3*r["noise_cv"]*100
    return {"dark_error":r["dark_error"],
      "single_d50_error":abs(r["cases"]["single"]["d50"]-r["cases"]["single"]["true_d50"])/r["cases"]["single"]["true_d50"]*100,
      "bimodal_d50_error":abs(r["cases"]["bimodal"]["d50"]-r["cases"]["bimodal"]["true_d50"])/r["cases"]["bimodal"]["true_d50"]*100,
      "noise_cv":r["noise_cv"]*100,"d50_bound":bound,"grid_half_percent":r["grid_half_percent"]}


def _checks(g, limit=False):
    rows=[
      {"what":T("画像で測った第 1 暗環","first dark ring measured in the image"),"criterion":T("1.22 λ/d との差 < 0.0005 rad","difference from 1.22 λ/d < 0.0005 rad"),"result":"%.6f rad"%g["dark_error"],"ok":g["dark_error"]<5e-4},
      {"what":T("単峰分布の D50 復元誤差","unimodal D50 recovery error"),"criterion":T("半格子 %.2f %% + 雑音 CV の 3 倍 = %.2f %% 未満"%(g["grid_half_percent"],g["d50_bound"]),"below half-grid %.2f%% + 3 noise CV = %.2f%%"%(g["grid_half_percent"],g["d50_bound"])),"result":"%.2f %%"%g["single_d50_error"],"ok":g["single_d50_error"]<g["d50_bound"]},
      {"what":T("二峰分布の D50 復元誤差","bimodal D50 recovery error"),"criterion":T("半格子 %.2f %% + 雑音 CV の 3 倍 = %.2f %% 未満"%(g["grid_half_percent"],g["d50_bound"]),"below half-grid %.2f%% + 3 noise CV = %.2f%%"%(g["grid_half_percent"],g["d50_bound"])),"result":"%.2f %%"%g["bimodal_d50_error"],"ok":g["bimodal_d50_error"]<g["d50_bound"]},
      {"what":T("12 回の雑音試行による D50 のばらつき","D50 spread over 12 noise trials"),"criterion":T("変動係数 < 8 %（核とグリッドは固定）","coefficient of variation < 8% (fixed kernel and grid)"),"result":"%.2f %%"%g["noise_cv"],"ok":g["noise_cv"]<8}]
    if limit:
        rows.append({"what":T("微小・非球形・濃い粉にも同じ近似","same approximation for tiny, non-spherical or dense powder"),"criterion":T("ミー散乱・形状・多重散乱を含む","include Mie, shape and multiple scattering"),"result":T("未計算","not computed"),"ok":False})
    return rows


def _sphere(nu=12,nv=6):
    p=[[0,0,1.]]
    for j in range(1,nv):
        v=np.pi*j/nv
        for i in range(nu):
            u=2*np.pi*i/nu; p.append([np.sin(v)*np.cos(u),np.sin(v)*np.sin(u),np.cos(v)])
    p.append([0,0,-1.]); bot=len(p)-1; f=[]
    for i in range(nu): f.append([0,1+i,1+(i+1)%nu])
    for j in range(nv-2):
        a=1+j*nu; b=a+nu
        for i in range(nu): q=(i+1)%nu; f.extend([[a+i,b+i,b+q],[a+i,b+q,a+q]])
    a=1+(nv-2)*nu
    for i in range(nu): f.append([a+i,bot,a+(i+1)%nu])
    return np.asarray(p),np.asarray(f)


def _patterns():
    diameters=np.r_[48.0,np.geomspace(12,120,19)]
    return np.asarray([_render_pattern(d) for d in diameters])


def _lesson(q,choices,answer,explain,formula,limit):
    return {"question":q,"choices":choices,"answer":answer,"explain":explain,"formula":formula,"limit":limit}


def build_spec(r=None,g=None):
    r=compute() if r is None else r; g=gates(r) if g is None else g; pos,faces=_sphere(); n=20
    t=np.arange(n); q=np.zeros((n,18,4)); q[...,0]=1; xyz=np.zeros((n,18,3));
    base=np.array([[x,y,z] for x in (-.8,-.3,.2,.7) for y in (-.55,0,.55) for z in (-.4,.4)])[:18]
    for k in range(n): xyz[k]=base+np.array([0,.04*np.sin(k*.5),0])
    common={"view":{"az":-.7,"el":.35,"dist":.95},"axis":{"values":t,"segments":[{"k":0,"label":T("状態","state"),"unit":"","decimals":0}]}}
    checks=_checks(g); patterns=_patterns(); single=r["cases"]["single"]; bi=r["cases"]["bimodal"]
    particle_meshes=[{"name":"particle_%02d"%i,"pos":pos*.18,"faces":faces,"rgb":[245,190,75]} for i in range(18)]
    ring_points=[]
    for radius in np.linspace(.35,1.75,7):
        a=np.linspace(0,2*np.pi,90,endpoint=False)
        ring_points.append(np.column_stack([np.full(len(a),2.3),radius*np.cos(a),radius*np.sin(a)]))
    rings=np.vstack(ring_points); beam=np.column_stack([np.linspace(-3.0,2.3,180),np.zeros(180),np.zeros(180)])
    optical_clouds=[]
    for k in range(n):
        spread=.35+1.4*k/(n-1)
        glow=np.column_stack([np.full(100,2.25),spread*np.cos(np.linspace(0,2*np.pi,100,endpoint=False)),spread*np.sin(np.linspace(0,2*np.pi,100,endpoint=False))])
        pts=np.vstack([beam,rings,glow]); rgb=np.vstack([np.tile([1.,.18,.08],(len(beam),1)),np.tile([.12,.65,1.],(len(rings),1)),np.tile([1.,.72,.18],(len(glow),1))])
        optical_clouds.append({"k":k,"pos":pts,"rgb":rgb,"point_size":.055})
    tabs=[]
    tabs.append(pv.viewer_anim3d_tab("why",T("小粒ほど広がる","Small grains spread light"),"passed",T("レーザーが粒子群を通り、焦点面の同心リングへ届く。表示粒が小さくなるほど散乱像は外側へ広がる。","A laser crosses a particle cloud and reaches concentric focal-plane rings. Smaller displayed grains spread the pattern outward."),t,particle_meshes,xyz,q,clouds=optical_clouds,panes=[{"label":T("焦点面の合成散乱像","synthetic focal-plane pattern"),"frames":patterns,"png":True,"wide":True}],series=[{"label":T("代表粒径","representative diameter"),"values":np.geomspace(120,12,n),"unit":"µm","color":"#ffd166"}],numbers=[pv.viewer_number(T("48 µm の第 1 暗環","first dark ring for 48 µm"),"%.5f rad"%r["dark"])],checks=checks,lesson=_lesson(T("粒が小さくなると輪はどうなる?","What happens to the rings as grains shrink?"),[T("外へ広がる","spread outward"),T("内へ縮む","shrink inward")],0,T("暗環の角度は粒径に反比例する。","Dark-ring angle is inversely proportional to diameter."),T("θ₁ ≈ 1.22 λ/d","θ₁ ≈ 1.22 λ/d"),T("球形粒子のフラウンホーファー近似。","Fraunhofer approximation for spherical particles.")),**common))
    for key,title,case in [("single",T("単峰分布を復元","Recover one mode"),single),("bimodal",T("二峰分布を復元","Recover two modes"),bi)]:
        tabs.append(pv.viewer_anim3d_tab(key,title,"passed",T("リングごとの積分信号だけから、L 曲線で平滑化を選び非負最小二乗で分布を復元する。真の分布は推定器へ渡さない。","From integrated ring signals alone, an L-curve selects smoothing and NNLS recovers the distribution. Truth is never passed to the estimator."),t,particle_meshes,xyz,q,clouds=optical_clouds,series=[{"label":T("推定分布","estimated distribution"),"values":case["estimate"][:n],"unit":"","color":"#4fc3f7"},{"label":T("合成に使った分布（検査用）","generating distribution (check only)"),"values":case["truth"][:n],"unit":"","color":"#ffca28"}],numbers=[pv.viewer_number(T("D10","D10"),"%.1f µm"%case["d10"]),pv.viewer_number(T("D50","D50"),"%.1f µm"%case["d50"]),pv.viewer_number(T("D90","D90"),"%.1f µm"%case["d90"]),pv.viewer_number(T("L 曲線が選んだ α","L-curve α"),"%.3g"%case["alpha"])],checks=checks,lesson=_lesson(T("リング信号から粒径を一意に読める?","Can ring signals reveal sizes directly?"),[T("逆問題として解く","solve an inverse problem"),T("最も明るい輪だけ読む","read only the brightest ring")],0,T("各粒径の散乱が全リングで重なるため、核行列をまとめて反転する。","Every size overlaps across rings, so the full kernel matrix is inverted."),T("s = K p + ε;  p ≥ 0","s = K p + ε;  p ≥ 0"),T("平滑化は近い解を区別できないことを示す。","Smoothing reveals that nearby solutions cannot be distinguished.")),**common))
    tabs.append(pv.viewer_anim3d_tab("limit",T("近似の限界","Limits of the approximation"),"limit",T("数 µm 以下では屈折率を含むミー散乱が必要。非球形と高濃度の多重散乱も、この核には入っていない。","Below a few micrometres, Mie scattering with refractive index is needed. Shape and multiple scattering at high concentration are also absent."),t,particle_meshes,xyz,q,series=[{"label":T("フラウンホーファー核での推定","estimate under Fraunhofer kernel"),"values":single["estimate"][:n],"unit":"","color":"#ef5350"}],numbers=[pv.viewer_number(T("この模型に無い効果","effects absent here"),T("屈折率・形状・多重散乱","refractive index, shape, multiple scattering"))],checks=_checks(g,True),lesson=_lesson(T("どんな粉でも同じ核で測れる?","Can the same kernel measure every powder?"),[T("測れる","yes"),T("条件により崩れる","it can fail")],1,T("粒径、形状、濃度によって散乱模型が変わる。","The scattering model changes with size, shape and concentration."),T("I(θ) ∝ [2 J₁(x sin θ)/(x sin θ)]²","I(θ) ∝ [2 J₁(x sin θ)/(x sin θ)]²"),T("合成教材であり、製剤の品質判定には使えない。","This synthetic lesson is not for medicine quality decisions.")),**common))
    return pv.viewer_spec("laser_diffraction",T("光の輪で粉の粒径を測る","Measure powder size with rings of light"),T("合成リング信号を逆問題として解き、粒度分布と D10/D50/D90 を復元する","Solve synthetic ring signals as an inverse problem to recover a size distribution and D10/D50/D90"),T("①問い → ②予想 → ③再生 → ④式 → ⑤限界。ドラッグで回転し、バッジで計算の門を見る。","Follow ① question → ② prediction → ③ play → ④ formula → ⑤ limit. Drag to orbit; tap a badge for computed gates."),tabs,credit=T("粒子、レーザー、検出器信号はすべて合成。波長 0.633 µm と雑音 0.6 % は教材用の仮定。","Particles, laser and detector signals are synthetic. The 0.633 µm wavelength and 0.6% noise are teaching assumptions."))


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__.splitlines()[0]); ap.add_argument("--check",action="store_true"); ap.add_argument("--out",default=str(OUT_HTML)); a=ap.parse_args(argv)
    r=compute(); g=gates(r)
    for k,v in g.items(): print("%-25s %s"%(k,v))
    spec=build_spec(r,g)
    if a.check:
        print("ok: %d bytes (not written)"%len(pv._build_html(spec,list(LANGS)).encode("utf-8"))); return 0
    path=pv.write_viewer(spec,a.out,list(LANGS)); print("wrote %s (%d bytes)"%(path,Path(path).stat().st_size)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
