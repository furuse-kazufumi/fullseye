# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""薬の粒の大きさと溶出速度を、合成画像から測る動く 3-D 教材。"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import blob2d
import fullseye as fs
import pocviewer as pv

OUT_HTML = ROOT / "docs" / "view2026" / "anim3d" / "particle_dissolution_anim3d.html"
LANGS = ("ja", "en")
N = 41
R0 = 8.0
DRDT = 0.20
PX_MM = 0.10
NOISE = 0.035
MIN_EVAL_RADIUS_MM = 3.0


def T(ja, en):
    return pv.viewer_text(ja, en)


def _e(x):
    return "< 1e-12" if abs(float(x)) < 1e-12 else "%.3g" % float(x)


def _sphere(nu=18, nv=9):
    p = [[0, 0, 1.0]]
    for j in range(1, nv):
        v = math.pi*j/nv
        for i in range(nu):
            u = 2*math.pi*i/nu
            p.append([math.sin(v)*math.cos(u), math.sin(v)*math.sin(u), math.cos(v)])
    p.append([0, 0, -1.0]); bot=len(p)-1; f=[]
    for i in range(nu): f.append([0,1+i,1+(i+1)%nu])
    for j in range(nv-2):
        a=1+j*nu; b=a+nu
        for i in range(nu):
            q=(i+1)%nu; f.extend([[a+i,b+i,b+q],[a+i,b+q,a+q]])
    a=1+(nv-2)*nu
    for i in range(nu): f.append([a+i,bot,a+(i+1)%nu])
    return np.asarray(p,float),np.asarray(f,int)


def _poses(scales, centres):
    n=len(scales); xyz=np.repeat(np.asarray(centres,float)[None,:,:],n,axis=0)
    q=np.zeros((n,len(centres),4)); q[...,0]=1
    return xyz,q,np.asarray(scales)[:,None]


def _camera_frame(radii, seed):
    h=w=256; yy,xx=np.mgrid[:h,:w]; rng=np.random.default_rng(seed)
    image=.16+rng.normal(0,NOISE,(h,w))
    centres=[(128.37,127.63)] if len(radii)==1 else [(42.37,42.63),(42.71,128.29),(42.41,213.82),(128.73,42.18),
        (128.24,213.76),(213.62,42.31),(213.44,128.57),(213.36,213.68)]
    for rad,(cy,cx) in zip(radii,centres):
        mask=(yy-cy)**2+(xx-cx)**2 <= max(0,rad/PX_MM)**2
        image[mask]=.82+rng.normal(0,NOISE,mask.sum())
    return np.uint8(np.round(np.clip(image,0,1)*255))


def _measure_mass(frame):
    region=fs.apply(frame.astype(float)/255.0,"otsu")
    labels=blob2d.blob_label(region,connectivity=8)
    areas=[]
    for lab in range(1,int(labels.max())+1):
        a=float(fs.apply(labels==lab,"area_center")[0])
        if a >= 500: areas.append(a)
    radii=np.sqrt(np.asarray(areas)*PX_MM**2/math.pi)
    return float(np.sum(radii**3)),len(areas)


def _crossing_time(t, values, level=.10):
    """First descending level crossing, linearly interpolated between camera frames."""
    y=np.asarray(values,float); k=np.flatnonzero(y<=level)
    if not len(k): return float("nan")
    j=int(k[0])
    if j==0: return float(t[0])
    f=(level-y[j-1])/(y[j]-y[j-1])
    return float(t[j-1]+f*(t[j]-t[j-1]))


def compute():
    t=np.linspace(0,R0/DRDT,N); r=np.maximum(R0-DRDT*t,0)
    sol=solve_ivp(lambda tt,y: [-3*DRDT*max(y[0],0)**(2/3)],(0,t[-2]),[R0**3],t_eval=t[:-1],rtol=1e-11,atol=1e-12,max_step=(t[1]-t[0])/8)
    ode=np.r_[np.maximum(sol.y[0],0),0.0]; closed=r**3
    r8=R0/2; small=np.maximum(r8-DRDT*t,0)
    frames_one=np.asarray([_camera_frame([x],2600+i) for i,x in enumerate(r)])
    frames_eight=np.asarray([_camera_frame([x]*8,3600+i) for i,x in enumerate(small)])
    measured_one=np.array([_measure_mass(x)[0] for x in frames_one]); measured_eight=np.array([_measure_mass(x)[0] for x in frames_eight])
    count_one=np.array([_measure_mass(x)[1] for x in frames_one]); count_eight=np.array([_measure_mass(x)[1] for x in frames_eight])
    # The image estimate is normalised by its own first frame; truth is independently integrated.
    est_one=measured_one/measured_one[0]; est_eight=measured_eight/measured_eight[0]
    truth_one=ode/ode[0]; truth_eight=8*small**3/R0**3
    valid=(r>=MIN_EVAL_RADIUS_MM); valid8=(small>=MIN_EVAL_RADIUS_MM)
    image_error=max(np.max(np.abs(est_one[valid]-truth_one[valid])),np.max(np.abs(est_eight[valid8]-truth_eight[valid8])))
    # Half a boundary pixel propagated through m proportional to r^3, plus threshold jitter from image noise.
    contrast=.82-.16; rpx=MIN_EVAL_RADIUS_MM/PX_MM
    pixel_bound=3*(.5*PX_MM/MIN_EVAL_RADIUS_MM)+3*(NOISE/contrast)/math.sqrt(2*math.pi*rpx)
    measured_t_one=_crossing_time(t,est_one); measured_t_eight=_crossing_time(t,est_eight)
    measured_ratio=measured_t_eight/measured_t_one
    # One-frame timing quantisation plus the measured mass uncertainty converted by the closed curve's local slope at 10%.
    dt=float(t[1]-t[0]); slope=3*DRDT*(.10**(2/3))/R0
    ratio_bound=dt/measured_t_one + image_error/(slope*measured_t_one)
    return dict(t=t,r=r,small=small,ode=ode,closed=closed,frames_one=frames_one,frames_eight=frames_eight,
        display_one=frames_one[:,::2,::2],display_eight=frames_eight[:,::2,::2],
        est_one=est_one,est_eight=est_eight,truth_one=truth_one,truth_eight=truth_eight,count_one=count_one,count_eight=count_eight,
        ode_rel=float(np.max(np.abs(ode-closed))/closed[0]),image_error=float(image_error),pixel_bound=float(pixel_bound),
        measured_t_one=measured_t_one,measured_t_eight=measured_t_eight,measured_ratio=measured_ratio,ratio_bound=ratio_bound,
        t_one=R0/DRDT,t_eight=(R0/2)/DRDT)


def gates(r):
    return {"ode_relative_error":r["ode_rel"],"image_mass_error":r["image_error"],"image_error_bound":r["pixel_bound"],
        "time_ratio":r["measured_ratio"],"time_ratio_error":abs(r["measured_ratio"]-.5),"time_ratio_bound":r["ratio_bound"],
        "detected_particles":int(np.max(r["count_eight"]))}


def _checks(g, limit=False):
    rows=[
      {"what":T("1 粒: 数値 ODE と立方根則","one particle: numerical ODE vs cube-root law"),"criterion":"< 1e-6","result":_e(g["ode_relative_error"]),"ok":g["ode_relative_error"]<1e-6},
      {"what":T("合成像から測った溶け残り量","remaining mass measured from synthetic images"),"criterion":T("画素・雑音からの上限 %.3f 未満"%g["image_error_bound"],"below pixel/noise bound %.3f"%g["image_error_bound"]),"result":"%.3f"%g["image_mass_error"],"ok":g["image_mass_error"]<g["image_error_bound"]},
      {"what":T("画像曲線の 10 % 到達時間: 8 粒 / 1 粒","image-curve time to 10%: eight / one"),"criterion":T("1/2 との差 < 画像誤差・コマ刻み由来 %.3f"%g["time_ratio_bound"],"difference from 1/2 < image/frame bound %.3f"%g["time_ratio_bound"]),"result":"%.4f (差 %.3f)"%(g["time_ratio"],g["time_ratio_error"]),"ok":g["time_ratio_error"]<g["time_ratio_bound"]},
      {"what":T("画像で分離して測った粒","particles separated and measured in the image"),"criterion":T("8 個","8 particles"),"result":str(g["detected_particles"]),"ok":g["detected_particles"]==8},
    ]
    if limit:
      rows.append({"what":T("飽和・凝集・非球形でも同じ立方根則","same cube-root law near saturation, with aggregation or non-spherical grains"),"criterion":T("それらをモデルに含む","model includes them"),"result":T("未計算","not computed"),"ok":False})
    return rows


def _lesson(q, choices, answer, explain, formula, limit):
    return {"question":q,"choices":choices,"answer":answer,"explain":explain,"formula":formula,"limit":limit}


def build_spec(r=None,g=None):
    r=compute() if r is None else r; g=gates(r) if g is None else g; pos,faces=_sphere(); tabs=[]
    xyz,q,scale=_poses(r["r"]/R0,[[-1.3,0,0]]); xyz8,q8,scale8=_poses(r["small"]/(R0/2),[[-1.5,-1,0],[-.5,-1,0],[.5,-1,0],[1.5,-1,0],[-1.5,1,0],[-.5,1,0],[.5,1,0],[1.5,1,0]])
    common=dict(view={"az":-.8,"el":.55,"dist":.9},axis={"values":r["t"],"segments":[{"k":0,"label":T("時間","time"),"unit":"min","decimals":0}]})
    clouds=[]; centres=np.array([[-1.5,-1,0],[-.5,-1,0],[.5,-1,0],[1.5,-1,0],[-1.5,1,0],[-.5,1,0],[.5,1,0],[1.5,1,0]])
    for k,(a,b) in enumerate(zip(r["r"]/R0,r["small"]/(R0/2))):
        pts=np.vstack([pos*a+np.array([0,0,1.6])]+[pos*b+c for c in centres])
        clouds.append({"k":k,"pos":pts,"color":"#ffd166","point_size":.055})
    tabs.append(pv.viewer_anim3d_tab("size",T("1 粒と 8 粒","One grain or eight"),"passed",T("同じ総量でも 8 粒は表面積が 2 倍になり、画像から測る溶け残り曲線が早くゼロへ向かう。","For equal total mass, eight grains have twice the surface area, and the image-measured remaining-mass curve reaches zero sooner."),r["t"],[{"name":"vessel","pos":pos*2.8,"faces":faces,"rgb":[100,170,220],"alpha":.12}],np.zeros((N,1,3)),np.tile(np.array([1.,0,0,0]),(N,1,1)),clouds=clouds,panes=[{"label":T("上から撮った合成像: 1 粒(計測 256 px、表示 128 px)","synthetic top view: one grain (measured at 256 px, displayed at 128 px)"),"frames":r["display_one"],"png":True,"wide":True},{"label":T("上から撮った合成像: 8 粒(計測 256 px、表示 128 px)","synthetic top view: eight grains (measured at 256 px, displayed at 128 px)"),"frames":r["display_eight"],"png":True,"wide":True}],series=[{"label":T("1 粒: 像から推定","one: estimated from image"),"values":r["est_one"],"unit":"","color":"#ffd54f"},{"label":T("8 粒: 像から推定","eight: estimated from image"),"values":r["est_eight"],"unit":"","color":"#4fc3f7"}],numbers=[pv.viewer_number(T("画像曲線の 10 % 到達: 1 粒","image curve to 10%: one"),"%.2f min"%r["measured_t_one"]),pv.viewer_number(T("画像曲線の 10 % 到達: 8 粒","image curve to 10%: eight"),"%.2f min"%r["measured_t_eight"])],checks=_checks(g),lesson=_lesson(T("同じ量なら、1 個と 8 個のどちらが速く溶ける?","For equal mass, which dissolves faster: one grain or eight?"),[T("1 個","one"),T("8 個","eight"),T("同じ","same")],1,T("8 分割すると半径は半分、総表面積は 2 倍になる。","Eight-way splitting halves radius and doubles total surface area."),T("dm/dt = −k A (Cs − C)","dm/dt = −k A (Cs − C)"),T("球形、一定密度、シンク条件を仮定。","Assumes spheres, constant density and sink conditions.")),**common))
    xyz1,q1,_=_poses(np.ones(N),[[-1.2,0,0],[1.2,0,0]])
    tabs.append(pv.viewer_anim3d_tab("cube",T("立方根則","Cube-root law"),"passed",T("数値 ODE と閉形式を別々に計算する。m の立方根は時間に対して直線になり、残差は刻みから決めた門を通る。","The numerical ODE and closed form are computed separately. The cube root of mass is linear in time and passes a step-derived gate."),r["t"],[{"name":"ode","pos":pos,"faces":faces,"rgb":[255,180,70]},{"name":"closed","pos":pos,"faces":faces,"rgb":[90,190,245],"alpha":.55}],xyz1,q1,series=[{"label":T("数値 ODE: m^(1/3)","numerical ODE: m^(1/3)"),"values":np.cbrt(r["ode"]),"unit":"","color":"#ffca28"},{"label":T("閉形式","closed form"),"values":np.cbrt(r["closed"]),"unit":"","color":"#4fc3f7"}],numbers=[pv.viewer_number(T("最大相対残差","maximum relative residual"),_e(g["ode_relative_error"]))],checks=_checks(g),lesson=_lesson(T("球の質量の立方根を時間に対して描くと?","What does cube-root mass look like against time?"),[T("直線","a straight line"),T("放物線","a parabola")],0,T("表面積が半径の二乗、質量が半径の三乗なので半径が一定速で縮む。","Area scales as radius squared and mass as radius cubed, so radius shrinks at constant speed."),T("m0^(1/3) − m^(1/3) ∝ t","m0^(1/3) − m^(1/3) ∝ t"),T("液中濃度を無視できるシンク条件でのみ直線。","Linear only under sink conditions where liquid concentration stays negligible.")),**common))
    tabs.append(pv.viewer_anim3d_tab("distribution",T("粒度分布","Particle-size distribution"),"passed",T("大粒と小粒を混ぜると、小粒が初期の立ち上がりを作り、大粒が長い尾を作る。画像の円を二値化し、ラベルごとの面積から円相当半径を測る。誤差は半径 3.0 mm(直径 60 px)以上の区間で評価する。","Mixing sizes makes small grains drive the early rise while large grains make a long tail. Image circles are thresholded and labelled; equivalent radius comes from each labelled area. Error is evaluated while radius is at least 3.0 mm (60 px diameter)."),r["t"],[{"name":"grain","pos":pos,"faces":faces,"rgb":[210,155,235]}],xyz,q,panes=[{"label":T("二値化・ラベル・面積で測る合成像","synthetic image measured by threshold, labels and area"),"frames":r["display_eight"],"png":True,"wide":True}],series=[{"label":T("像からの残存量","image-derived remaining mass"),"values":r["est_eight"],"unit":"","color":"#ce93d8"},{"label":T("ODE 真値","ODE truth"),"values":r["truth_eight"],"unit":"","color":"#80cbc4"}],numbers=[pv.viewer_number(T("最大像誤差(半径 3.0 mm 以上)","maximum image error (radius at least 3.0 mm)"),"%.4f"%g["image_mass_error"]),pv.viewer_number(T("画素・雑音の上限","pixel/noise bound"),"%.3f"%g["image_error_bound"])],checks=_checks(g),lesson=_lesson(T("小粒が多い分布の曲線はどこが変わる?","Where does a distribution rich in small grains change the curve?"),[T("初期が速い","faster initially"),T("最後だけ速い","only the end is faster")],0,T("小粒は質量あたりの表面積が大きい。","Small grains have more surface area per unit mass."),T("C(t) = (m0 − Σm(t)) / V","C(t) = (m0 − Σm(t)) / V"),T("重なった粒や直径 60 px 未満の粒は、この誤差評価の対象外。","Overlapping grains and grains below 60 px diameter are outside this error evaluation.")),**common))
    tabs.append(pv.viewer_anim3d_tab("limit",T("モデルの限界","Model limits"),"limit",T("液が飽和に近づくと Cs − C が小さくなる。凝集は見かけの表面積を減らし、非球形は面積から質量への換算を崩す。","Near saturation, Cs − C falls. Aggregation reduces exposed area, and non-spherical shape breaks conversion from image area to mass."),r["t"],[{"name":"grain","pos":pos,"faces":faces,"rgb":[239,100,100]}],xyz,q,series=[{"label":T("シンク条件の予測","sink-condition prediction"),"values":r["truth_one"],"unit":"","color":"#ef5350"}],numbers=[pv.viewer_number(T("未計算の効果","uncomputed effects"),T("飽和・凝集・非球形","saturation, aggregation, shape"))],checks=_checks(g,True),lesson=_lesson(T("液が飽和へ近づいても同じ直線になる?","Does the same straight line hold near saturation?"),[T("なる","yes"),T("遅くなる","it slows")],1,T("駆動力 Cs − C が小さくなるため。","The driving difference Cs − C becomes smaller."),T("dm/dt = −k A (Cs − C)","dm/dt = −k A (Cs − C)"),T("この教材は合成模型で、製剤の品質判定や投与設計には使えない。","This synthetic model is not for medicine quality decisions or dose design.")),**common))
    return pv.viewer_spec("particle_dissolution",T("薬の粒はどう溶けるか","How medicine particles dissolve"),T("小さい粒ほど速く溶ける理由を、画像計測と溶出模型で確かめる","Test why smaller particles dissolve faster using image measurement and a dissolution model"),T("①問い → ②予想 → ③再生 → ④式 → ⑤限界。ドラッグで回転し、バッジで計算の門を見る。","Follow ① question → ② prediction → ③ play → ④ formula → ⑤ limit. Drag to orbit; tap a badge for computed gates."),tabs,credit=T("粒・液・画像はすべて合成。一般化した薬の粒で、会社名・商品名・一般名を表さない。","Particles, liquid and images are entirely synthetic. These are generic medicine particles, with no company, product or generic drug name."))


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__.splitlines()[0]); ap.add_argument("--check",action="store_true"); ap.add_argument("--out",default=str(OUT_HTML)); a=ap.parse_args(argv)
    r=compute(); g=gates(r)
    for k,v in g.items(): print("%-28s %s"%(k,v))
    spec=build_spec(r,g)
    if a.check:
        print("ok: %d bytes (not written)"%len(pv._build_html(spec,list(LANGS)).encode("utf-8"))); return 0
    path=pv.write_viewer(spec,a.out,list(LANGS)); print("wrote %s (%d bytes)"%(path,Path(path).stat().st_size)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
