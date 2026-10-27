# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""衛星レーダー干渉で数 mm の沈下を読む動く 3-D 教材。"""
from __future__ import annotations

import argparse, math, sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
import fullseye as fs
import pocviewer as pv

OUT_HTML=ROOT/"docs"/"view2026"/"anim3d"/"insar_subsidence_anim3d.html"
LANGS=("ja","en")
LAM=.056; N=49; SEED=26027
ALTITUDE_M=700_000.0; INCIDENCE_DEG=35.0; BPERP_M=120.0; LOOKS=16

def T(ja,en): return pv.viewer_text(ja,en)
def _e(x): return "< 1e-12" if abs(float(x))<1e-12 else "%.3g"%float(x)

def _grid_mesh(n=17):
    y,x=np.mgrid[-1:1:complex(n),-1:1:complex(n)]
    z=.12*np.exp(-2.2*(x*x+y*y))+.025*x
    p=np.c_[x.ravel(),y.ravel(),z.ravel()]; f=[]
    for j in range(n-1):
        for i in range(n-1):
            a=j*n+i; f.extend([[a,a+1,a+n+1],[a,a+n+1,a+n]])
    return p,np.asarray(f,int)

def _smooth_random(rng,n,scale):
    small=rng.normal(size=(7,7)); yy,xx=np.mgrid[0:7:complex(n),0:7:complex(n)]
    # independent, deterministic bilinear interpolation; no truth enters this field
    a=np.empty((n,n))
    for j in range(n):
        v=yy[j,0]; j0=min(int(v),5); fy=v-j0
        for i in range(n):
            u=xx[0,i]; i0=min(int(u),5); fx=u-i0
            a[j,i]=(small[j0,i0]*(1-fx)*(1-fy)+small[j0,i0+1]*fx*(1-fy)+small[j0+1,i0]*(1-fx)*fy+small[j0+1,i0+1]*fx*fy)
    a-=a.mean(); return a/a.std()*scale

def compute(atmosphere_mm=1.4):
    rng=np.random.default_rng(SEED); y,x=np.mgrid[-1:1:complex(N),-1:1:complex(N)]
    theta=math.radians(INCIDENCE_DEG); slant_range=ALTITUDE_M/math.cos(theta)
    los=np.array([math.sin(theta),0,math.cos(theta)])
    vertical=-.032*np.exp(-((x-.073)**2/(2*.28**2)+(y+.041)**2/(2*.22**2)))
    expected=-vertical*los[2]
    topo=.12*np.exp(-2.2*(x*x+y*y))+.025*x
    dem=topo+_smooth_random(rng,N,.0012)
    atmosphere=_smooth_random(rng,N,atmosphere_mm/1000)
    coherence=.93-.55*np.exp(-((x+.48)**2+(y-.38)**2)/.055)
    topo_factor=4*np.pi*BPERP_M/(LAM*slant_range*math.sin(theta))
    topo_phase=topo_factor*topo; dem_phase=topo_factor*dem
    physical_phase=topo_phase+(4*np.pi/LAM)*(expected+atmosphere)
    shape=(N,N,4,4)
    s1=(rng.normal(size=shape)+1j*rng.normal(size=shape))/math.sqrt(2)
    independent=(rng.normal(size=shape)+1j*rng.normal(size=shape))/math.sqrt(2)
    gamma=coherence[...,None,None]
    s2=(gamma*s1+np.sqrt(1-gamma*gamma)*independent)*np.exp(1j*physical_phase[...,None,None])
    interferogram=np.mean(s1*np.conj(s2),axis=(-2,-1))
    corrected=interferogram*np.exp(1j*dem_phase)
    wrapped=np.angle(corrected)
    unwrapped=fs.ledger.unwrap_phase_2d(wrapped)
    # Estimate only from the observed phase. A quiet border supplies the arbitrary offset.
    border=np.zeros((N,N),bool); border[:5]=border[-5:]=True; border[:,:5]=True; border[:,-5:]=True
    unwrapped=unwrapped-np.median(unwrapped[border])
    estimated=-LAM/(4*np.pi)*unwrapped
    err=estimated-expected; rms=float(np.sqrt(np.mean(err**2)))
    k=np.unravel_index(np.argmax(estimated),estimated.shape)
    centre_error=float(abs(estimated[k]-expected.max()))
    # Count complete colour cycles along the observed row through the estimated maximum.
    row=np.unwrap(wrapped[k[0]]); cycles=float((row.max()-row.min())/(2*np.pi))
    fringe_depth=cycles*LAM/2
    sigma_phase=np.sqrt((1-coherence**2)/(2*LOOKS*coherence**2))
    sigma_range=LAM/(4*np.pi)*sigma_phase
    rms_bound=1.35*math.sqrt((atmosphere_mm/1000)**2+float(np.mean(sigma_range**2)))
    low=coherence<.5; low_rms=float(np.sqrt(np.mean(err[low]**2))) if np.any(low) else 0.0
    h_2pi=LAM*slant_range*math.sin(theta)/(2*BPERP_M)
    return dict(x=x,y=y,topo=topo,wrapped=wrapped,unwrapped=unwrapped,estimated=estimated,expected=expected,
        coherence=coherence,rms=rms,centre_error=centre_error,cycles=cycles,fringe_depth=fringe_depth,
        peak=float(expected.max()),atm_mm=atmosphere_mm,los=los,s1=s1,s2=s2,interferogram=interferogram,
        rms_bound=rms_bound,low_fraction=float(np.mean(low)),low_rms=low_rms,h_2pi=h_2pi,
        slant_range=slant_range,topo_factor=topo_factor)

def gates(r):
    noisy=compute(5.0)
    return {"rms_mm":1000*r["rms"],"rms_bound_mm":1000*r["rms_bound"],"centre_mm":1000*r["centre_error"],
      "fringe_mm":1000*abs(r["fringe_depth"]-r["peak"]),"cycles":r["cycles"],
      "high_atm_rms_mm":1000*noisy["rms"],"atmosphere_growth_mm":1000*(noisy["rms"]-r["rms"]),
      "low_fraction_pct":100*r["low_fraction"],"low_rms_mm":1000*r["low_rms"],"h_2pi_m":r["h_2pi"]}

def _img(a,cmap=False):
    if cmap:
        h=(a+np.pi)/(2*np.pi); return np.uint8(np.stack([127+127*np.cos(2*np.pi*h),127+127*np.cos(2*np.pi*(h-1/3)),127+127*np.cos(2*np.pi*(h-2/3))],-1).clip(0,255))
    q=(a-a.min())/(np.ptp(a)+1e-15); return np.uint8(np.round(q*255))

def _checks(g,limit=False):
    rows=[
      {"what":T("アンラップ位相からの沈下地図","subsidence map from unwrapped phase"),"criterion":T("16 ルックの位相 CRB と大気 RMS から %.2f mm 未満"%g["rms_bound_mm"],"below %.2f mm from 16-look phase CRB and atmospheric RMS"%g["rms_bound_mm"]),"result":"%.2f mm"%g["rms_mm"],"ok":g["rms_mm"]<g["rms_bound_mm"]},
      {"what":T("推定中心沈下","estimated central subsidence"),"criterion":"< 4.0 mm","result":"%.2f mm"%g["centre_mm"],"ok":g["centre_mm"]<4},
      {"what":T("画像から数えた縞 × λ/2","image-counted fringes × λ/2"),"criterion":"< 12 mm","result":"%.2f mm"%g["fringe_mm"],"ok":g["fringe_mm"]<12},]
    if limit:
      rows.append({"what":T("低コヒーレンス域でも位相が安定","phase remains stable in low-coherence area"),"criterion":T("γ < 0.5 の領域でも全体と同等","same accuracy where gamma < 0.5"),"result":T("全画素の %.1f %%、RMS %.2f mm"%(g["low_fraction_pct"],g["low_rms_mm"]),"%.1f %% of pixels; RMS %.2f mm"%(g["low_fraction_pct"],g["low_rms_mm"])),"ok":False})
      rows.append({"what":T("大気遅延を 1.4 mm から 5.0 mm に増やしても精度が同じ","accuracy unchanged when atmospheric delay grows from 1.4 to 5.0 mm"),"criterion":T("誤差が増えない","error does not grow"),"result":T("RMS が %.2f mm 増加"%g["atmosphere_growth_mm"],"RMS increases by %.2f mm"%g["atmosphere_growth_mm"]),"ok":False})
    return rows

def _lesson(q,ch,a,e,f,l): return {"question":q,"choices":ch,"answer":a,"explain":e,"formula":f,"limit":l}
def build_spec(r=None,g=None):
    r=compute() if r is None else r; g=gates(r) if g is None else g; p,f=_grid_mesh(); n=25
    xyz=np.zeros((n,2,3)); xyz[:,0]=[-2.1,-1.3,2.5]; xyz[:,1]=[2.0,-1.1,2.7]
    q=np.zeros((n,2,4)); q[...,0]=1; t=np.linspace(0,1,n)
    common=dict(axis={"values":t,"segments":[{"k":0,"label":T("観測の進行","observation progress"),"unit":"","decimals":2}]},view={"az":-.8,"el":.45,"dist":1.05})
    mesh={"name":"terrain","pos":p,"faces":f,"rgb":[55,135,85]}; sat={"name":"satellites","pos":np.array([[0,0,0],[.18,0,0],[0,.18,0]]),"faces":np.array([[0,1,2]]),"rgb":[255,190,55]}
    tabs=[]
    tabs.append(pv.viewer_anim3d_tab("mm",T("なぜ数 mm が分かる？","Why can it see millimetres?"),"passed",T("高度 700 km、入射角 35°、垂直基線 120 m の二つの軌道から同じ合成地表を見る。波長 5.6 cm では往復距離 λ/2 ごとに色が一周する。","Two orbits at 700 km altitude, 35° incidence and 120 m perpendicular baseline view the same synthetic surface. At 5.6 cm wavelength, colour cycles for every λ/2 of range."),t,[mesh,sat],xyz,q,series=[{"label":T("1 周に相当する距離","range per cycle"),"values":np.full(n,LAM/2*1000),"unit":"mm","color":"#ffd54f"}],numbers=[pv.viewer_number(T("高さ曖昧さ h₂π","height ambiguity h₂π"),"%.1f m"%g["h_2pi_m"]),pv.viewer_number(T("位相 1 周","one phase cycle"),"28 mm")],checks=_checks(g),lesson=_lesson(T("位相が一周すると距離はいくら変わる？","How much range change makes one phase cycle?"),[T("λ","λ"),T("λ/2","λ/2"),T("2λ","2λ")],1,T("電波は地表まで往復するため。","The wave travels to the ground and back."),T("φtopo = 4π B⊥ h / (λ R sinθ); h₂π = λ R sinθ / (2 B⊥)","φtopo = 4π B⊥ h / (λ R sinθ); h₂π = λ R sinθ / (2 B⊥)"),T("測れるのは視線方向だけ。","Only line-of-sight motion is measured.")),**common))
    tabs.append(pv.viewer_anim3d_tab("fringes",T("色の輪を数える","Count the coloured rings"),"passed",T("相関した円形ガウスのスペックルから二つの複素 SAR 像を作り、s1·conj(s2) を 4×4 平均して干渉を得た。DEM の地形位相を引き、変位・大気・デコヒーレンスが残る。","Two complex SAR images use correlated circular-Gaussian speckle. The interferogram is the 4×4-look mean of s1·conj(s2); subtracting DEM topographic phase leaves motion, atmosphere and decorrelation."),t,[mesh],xyz[:,:1],q[:,:1],panes=[{"label":T("巻き戻った干渉位相 −π〜π","wrapped interferometric phase −π to π"),"frames":np.repeat(_img(r["wrapped"],True)[None],n,0),"png":True,"wide":True}],series=[{"label":T("断面の位相周回数","phase cycles on section"),"values":np.linspace(0,g["cycles"],n),"unit":"cycles","color":"#ef6c9c"}],numbers=[pv.viewer_number(T("像から数えた周回","cycles counted from image"),"%.2f"%g["cycles"])],checks=_checks(g),lesson=_lesson(T("輪の中心ほど沈下が大きい？","Is subsidence larger toward the ring centre?"),[T("はい","yes"),T("いいえ","no")],0,T("連続した距離変化が 2π ごとに折り返す。","Continuous range change wraps every 2π."),T("I = mean(s1·conj(s2)); ΔR = N λ / 2","I = mean(s1·conj(s2)); ΔR = N λ / 2"),T("大気も輪を曲げる。","Atmosphere also bends the rings.")),**common))
    tabs.append(pv.viewer_anim3d_tab("unwrap",T("輪を沈下地図へ","Turn rings into a subsidence map"),"passed",T("既存の 2-D 位相アンラップ op を観測像に適用し、静かな外周だけで零点を決めた。推定器は真の沈下を見ない。","The existing 2-D phase-unwrapping op processes the observed image; only a quiet border sets the offset. The estimator never sees true displacement."),t,[mesh],xyz[:,:1],q[:,:1],panes=[{"label":T("推定した視線方向沈下","estimated line-of-sight subsidence"),"frames":np.repeat(_img(r["estimated"])[None],n,0),"png":True,"wide":True}],series=[{"label":T("推定中心沈下","estimated central subsidence"),"values":np.linspace(0,r["estimated"].max()*1000,n),"unit":"mm","color":"#4fc3f7"}],numbers=[pv.viewer_number(T("地図 RMS 誤差","map RMS error"),"%.2f mm"%g["rms_mm"]),pv.viewer_number(T("中心誤差","centre error"),"%.2f mm"%g["centre_mm"])],checks=_checks(g),lesson=_lesson(T("色の飛びを戻した後、距離へ何を掛ける？","After unwrapping, what converts phase to range?"),[T("−λ/(4π)","−λ/(4π)"),T("λ/2","λ/2"),T("4π/λ","4π/λ")],0,T("往復位相式を距離について解く。","Solve the round-trip phase equation for range."),T("ΔR = −λ φ / (4π)","ΔR = −λ φ / (4π)"),T("絶対オフセットには基準領域が要る。","An absolute offset needs a reference area.")),**common))
    tabs.append(pv.viewer_anim3d_tab("limit",T("大気と植生の限界","Atmosphere and vegetation limits"),"limit",T("大気遅延を実際に増やして再計算すると RMS が増える。低コヒーレンス域は位相雑音が大きい。水平と鉛直は一本の視線だけでは分離できない。","Recomputing with stronger atmospheric delay increases RMS. Low-coherence areas have more phase noise. One line of sight cannot separate horizontal and vertical motion."),t,[mesh],xyz[:,:1],q[:,:1],panes=[{"label":T("コヒーレンス（暗い所ほど不安定）","coherence (dark means unstable)"),"frames":np.repeat(_img(r["coherence"])[None],n,0),"png":True,"wide":True}],numbers=[pv.viewer_number(T("通常大気の RMS","baseline-atmosphere RMS"),"%.2f mm"%g["rms_mm"]),pv.viewer_number(T("強い大気の RMS","strong-atmosphere RMS"),"%.2f mm"%g["high_atm_rms_mm"])],checks=_checks(g,True),lesson=_lesson(T("大気遅延を増やすと沈下推定は？","What happens when atmospheric delay grows?"),[T("誤差が増える","error grows"),T("変わらない","unchanged")],0,T("大気位相も変位位相に加算される。","Atmospheric phase adds to displacement phase."),T("φ = φterrain + φmotion + φatmosphere + noise","φ = φterrain + φmotion + φatmosphere + noise"),T("植生の低コヒーレンスと視線方向だけという曖昧さも残る。","Vegetation decorrelation and line-of-sight ambiguity remain.")),**common))
    return pv.viewer_spec("insar_subsidence",T("宇宙から数 mm の沈下を測る","Measure millimetre subsidence from orbit"),T("干渉縞をほどき、合成地表の沈下へ変える","Unwrap interference fringes into subsidence of a synthetic surface"),T("問い、予想、再生、式、限界の順に進む。","Follow question, prediction, play, formula and limit."),tabs,credit=T("地形・沈下・軌道・大気・雑音はすべて合成。固有の衛星、機関、地域を表さない。","Terrain, subsidence, orbit, atmosphere and noise are entirely synthetic and represent no specific satellite, institution or place."))

def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument("--check",action="store_true"); ap.add_argument("--out",default=str(OUT_HTML)); a=ap.parse_args(argv)
    r=compute(); g=gates(r); [print("%-24s %s"%(k,v)) for k,v in g.items()]; spec=build_spec(r,g)
    if a.check: print("ok: %d bytes"%len(pv._build_html(spec,list(LANGS)).encode())); return 0
    path=pv.write_viewer(spec,a.out,list(LANGS)); print("wrote",path,Path(path).stat().st_size); return 0
if __name__=="__main__": raise SystemExit(main())
