# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""マルチビーム測深と音速屈折を学ぶ、合成データだけの動く 3-D ページ。"""
from __future__ import annotations
import argparse, math, sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
import pocviewer as pv

OUT_HTML=ROOT/"docs"/"view2026"/"anim3d"/"multibeam_bathymetry_anim3d.html"
LANGS=("ja","en")
C0=1500.0; DT=2.0e-5; CTD_DZ=1.0; CTD_SIGMA=0.08; ROLL_SIGMA_DEG=0.03

def T(ja,en): return pv.viewer_text(ja,en)
def _e(x): return "< 1e-12" if abs(float(x))<1e-12 else "%.3g"%float(x)
def sound_speed(z):
    z=np.asarray(z,float)
    return C0-0.055*np.minimum(z,120.0)+0.012*np.maximum(z-120.0,0.0)
def sound_speed_gradient(z):
    return -0.055 if z < 120.0 else 0.012
def seabed(x,y=0.0):
    x=np.asarray(x,float); y=np.asarray(y,float)
    slope=92.0+0.018*x
    valley=20.0*np.exp(-((x+75.0)/48.0)**2)
    mound=-10.0*np.exp(-((x-82.0)/18.0)**2-(np.asarray(y)/34.0)**2)
    return slope+valley+mound

def _ray_rhs(y):
    """2-D ray equation, integrated without using Snell's invariant."""
    x,z,a,t=y; c=float(sound_speed(z)); dc=sound_speed_gradient(z)
    return np.array([math.sin(a),math.cos(a),dc*math.sin(a)/c,1.0/c])
def trace_rk4(angle_deg, ds=0.02, max_steps=30000):
    """Integrate position, direction and time by RK4 until the synthetic bottom."""
    y=np.array([0.0,0.0,math.radians(angle_deg),0.0]); pts=[y[:2].copy()]
    q0=math.sin(y[2])/float(sound_speed(y[1])); qerr=0.0
    for k in range(max_steps):
        old=y.copy(); k1=_ray_rhs(y); k2=_ray_rhs(y+ds*k1/2); k3=_ray_rhs(y+ds*k2/2); k4=_ray_rhs(y+ds*k3)
        y=y+ds*(k1+2*k2+2*k3+k4)/6
        qerr=max(qerr,abs(math.sin(y[2])/float(sound_speed(y[1]))-q0))
        if k%12==0: pts.append(y[:2].copy())
        if y[1]>=float(seabed(y[0])):
            f0=old[1]-float(seabed(old[0])); f1=y[1]-float(seabed(y[0])); u=-f0/(f1-f0)
            y=old+u*(y-old); pts.append(y[:2].copy()); break
    p=np.zeros((len(pts),3)); p[:,0]=np.asarray(pts)[:,0]; p[:,2]=np.asarray(pts)[:,1]
    return p,y[0],y[1],y[3],qerr

def invert_layers(angle_deg, one_way_time, ctd, details=False):
    """Independent inverse: straight analytic segments in 1 m constant-c layers."""
    sign=-1.0 if angle_deg<0 else 1.0; a=math.radians(abs(angle_deg)); q=math.sin(a)/ctd[0]
    x=z=t=length=0.0; end_angle=a
    for c in ctd:
        s=float(np.clip(q*c,-.999999,.999999)); ca=math.sqrt(1-s*s)
        layer_time=CTD_DZ/(c*ca); use=min(layer_time,one_way_time-t)
        x+=c*s*use; z+=c*ca*use; length+=c*use; t+=use; end_angle=math.asin(s)
        if t>=one_way_time-1e-15: break
    point=np.array([sign*x,0.0,z])
    if details: return point,length,end_angle
    return point

def terrain_mesh(nx=37,ny=19):
    xs=np.linspace(-180,180,nx); ys=np.linspace(-150,150,ny)
    v=np.array([[x,y,float(seabed(x,y))] for x in xs for y in ys],float); f=[]
    for i in range(nx-1):
        for j in range(ny-1):
            a=i*ny+j; b=a+ny
            f.extend(([a,b,b+1],[a,b+1,a+1]))
    return v,np.asarray(f,int)

def compute():
    rng=np.random.default_rng(20261027)
    angles=np.linspace(-62,62,41); paths=[]; hit=[]; twtt=[]; invariants=[]; sigmas=[]
    true_roll=0.72*np.sin(np.arange(len(angles))*0.41+0.2)
    measured_roll=true_roll+rng.normal(0.0,ROLL_SIGMA_DEG,len(angles))
    for i,a in enumerate(angles):
        actual_angle=a+true_roll[i]
        p,x,z,t,e=trace_rk4(actual_angle); paths.append(p); hit.append([x,0,z])
        sigma=DT*(0.35+1.1*abs(a)/62); sigmas.append(sigma)
        observed=2*t+rng.normal(0.0,sigma)
        twtt.append(round(observed/DT)*DT); invariants.append(e)
    hit=np.asarray(hit); twtt=np.asarray(twtt)
    ctd_z=np.arange(0.5,401.0,CTD_DZ)
    ctd=sound_speed(ctd_z)+rng.normal(0.0,CTD_SIGMA,len(ctd_z))
    correct=[]; straight=[]; effective_speed=[]; terminal_angle=[]
    for a,rm,t2 in zip(angles,measured_roll,twtt):
        measured_angle=a+rm; point,length,a1=invert_layers(measured_angle,t2/2,ctd,details=True)
        correct.append(point); effective_speed.append(length/(t2/2)); terminal_angle.append(a1)
        ar=math.radians(measured_angle); straight.append([C0*t2/2*math.sin(ar),0,C0*t2/2*math.cos(ar)])
    correct=np.asarray(correct); straight=np.asarray(straight)
    rms=float(np.sqrt(np.mean(np.sum((correct[:,[0,2]]-hit[:,[0,2]])**2,axis=1))))
    mean_depth=float(np.mean(hit[:,2])); mean_range=float(np.mean(np.linalg.norm(hit[:,[0,2]],axis=1)))
    timing_1s=C0*np.sqrt(np.mean(np.asarray(sigmas)**2))/2
    ctd_1s=mean_depth*CTD_SIGMA/C0
    roll_1s=mean_range*math.radians(ROLL_SIGMA_DEG)
    layer_1s=mean_depth*(0.5*0.055*CTD_DZ)/C0
    allowed=float(3*np.sqrt(timing_1s**2+ctd_1s**2+roll_1s**2+layer_1s**2))
    edge=np.abs(angles)>=48
    bend=straight[:,2]-correct[:,2]
    measured_angle=np.radians(np.abs(angles+measured_roll)); terminal_angle=np.asarray(terminal_angle)
    effective_speed=np.asarray(effective_speed); one_way=twtt/2
    # z0 - z ≈ (C0-ceff)t cos(a0) + ceff t[cos(a0)-cos((a0+a1)/2)].
    # ceff=L/t is the path-length weighted harmonic mean of the layer speeds.
    range_term=(C0-effective_speed)*one_way*np.cos(measured_angle)
    angle_term=effective_speed*one_way*(np.cos(measured_angle)-np.cos((measured_angle+terminal_angle)/2))
    bend_approx=range_term+angle_term
    smile=float(np.mean(bend[edge])); approx=float(np.mean(bend_approx[edge]))
    return dict(angles=angles,paths=paths,hit=hit,twtt=twtt,correct=correct,straight=straight,
                rms=rms,allowed=allowed,smile=smile,approx=approx,invariant=max(invariants),
                bend=bend,bend_approx=bend_approx,range_term=range_term,angle_term=angle_term,
                effective_speed=effective_speed,true_roll=true_roll,measured_roll=measured_roll,
                ctd=ctd,uncertainty=(timing_1s,ctd_1s,roll_1s,layer_1s))

def gates(r):
    edge=np.abs(r["angles"])>=48
    residual_rms=float(np.sqrt(np.mean((r["bend"][edge]-r["bend_approx"][edge])**2)))
    bend_rms=float(np.sqrt(np.mean(r["bend"][edge]**2)))
    return dict(rms=r["rms"],allowed=r["allowed"],smile=r["smile"],approx=r["approx"],
                smile_error=abs(r["smile"]-r["approx"]),smile_residual_rms=residual_rms,
                smile_relative_error=residual_rms/bend_rms,invariant=r["invariant"])
def lesson(q,choices,answer,explain,formula,limit):
    return dict(question=q,choices=choices,answer=answer,explain=explain,formula=formula,limit=limit)
def poses(n,b):
    x=np.zeros((n,b,3)); q=np.zeros((n,b,4)); q[...,0]=1; return x,q
def box(sx,sy,sz):
    v=np.array([[x,y,z] for x in (-sx/2,sx/2) for y in (-sy/2,sy/2) for z in (-sz/2,sz/2)],float)
    f=np.array([[0,1,3],[0,3,2],[4,7,5],[4,6,7],[0,4,5],[0,5,1],[2,3,7],[2,7,6],[0,2,6],[0,6,4],[1,5,7],[1,7,3]])
    return v,f
def checks(g,limit=False):
    rows=[
      {"what":T("正しい音速で復元した海底の RMS","seabed RMS with the correct sound-speed profile"),"criterion":T("時間・CTD・層・ロールの合成 3σ < %.3f m"%g["allowed"],"combined timing, CTD, layer and roll 3σ < %.3f m"%g["allowed"]),"result":"%.3f m"%g["rms"],"ok":g["rms"]<g["allowed"]},
      {"what":T("外側ビームの曲がりと二項近似","outer-beam bend versus two-term estimate"),"criterion":T("無視した角度曲率の項: RMS < 曲がりの 25 %","omitted angular-curvature term: RMS < 25 % of bend"),"result":"%.2f %%"%(100*g["smile_relative_error"]),"ok":g["smile_relative_error"]<.25},
      {"what":T("各光線の Snell 不変量","Snell invariant along every ray"),"criterion":T("不変量を使わない RK4、刻み 0.02 m: < 1e-10","RK4 without the invariant, 0.02 m step: < 1e-10"),"result":_e(g["invariant"]),"ok":g["invariant"]<1e-10}]
    if limit: rows.append({"what":T("崖・気泡・多重反射でも必ず海底を得る","every beam returns from cliffs, bubbles and multipath"),"criterion":T("単一で明瞭な反射","one unambiguous return"),"result":T("反射なし・偽反射があり得る","missing or false returns are possible"),"ok":False})
    return rows

def build_spec(r,g):
    n=len(r["angles"]); tv,tf=terrain_mesh(); ship,sf=box(28,10,5); xyz,q=poses(n,2); xyz[:,0,2]=-4
    beam=np.zeros((n,2,3)); beam[:,1]=r["hit"]; trail=[{"xyz":beam[:,1],"color":"#ffee58","tail":0}]
    common=[{"name":"synthetic seabed","pos":tv,"faces":tf,"rgb":[43,112,96],"alpha":.88},{"name":"survey vessel","pos":ship,"faces":sf,"rgb":[225,230,235]}]
    axis={"values":r["angles"],"segments":[{"k":0,"label":T("送信角","beam angle"),"unit":"°","decimals":1}]}
    base=checks(g); tabs=[]
    tabs.append(pv.viewer_anim3d_tab("time",T("なぜ音で深さが分かる?","Why does travel time reveal depth?"),"passed",T("扇状の各ビームについて、送信から海底反射が戻るまでの時間を測る。中央ほど短く、外側ほど斜めに長い道を通る。","For every beam in the fan, measure the time from transmission to the seabed echo. The centre travels a shorter path; outer beams travel longer oblique paths."),np.arange(n)/20,common,xyz,q,trails=trail,series=[{"label":T("往復時間","two-way travel time"),"values":r["twtt"],"unit":"s","color":"#4fc3f7"}],numbers=[pv.viewer_number(T("時間分解能","time resolution"),"20 µs")],checks=base,axis=axis,view={"az":-.8,"el":.35,"dist":1.25},lesson=lesson(T("同じ往復時間なら、速い音ほど推定距離は?","For the same travel time, what does faster sound imply?"),[T("短い","shorter"),T("長い","longer")],1,T("距離は音速と片道時間の積。","Distance is sound speed times one-way time."),T("range = c × t / 2","range = c × t / 2"),T("斜めのビームでは距離だけでなく向きも必要。","An oblique beam also needs its direction."))))
    tabs.append(pv.viewer_anim3d_tab("swath",T("扇のビームが海底を帯で埋める","A fan of beams fills a swath"),"passed",T("規則格子から作った斜面・谷・小さな高まりへ 41 本の光線を追跡した。黄色い着底点が一度の測線幅を作り、船の前進で帯になる。","Forty-one rays hit a gridded synthetic slope, valley and small mound. Their yellow footprints form one cross-track line; vessel motion turns it into a swath."),np.arange(n)/20,common,xyz,q,trails=trail,series=[{"label":T("着底深さ","bottom depth"),"values":r["hit"][:,2],"unit":"m","color":"#ffee58"}],numbers=[pv.viewer_number(T("ビーム数","beam count"),str(n))],checks=base,axis=axis,view={"az":-.75,"el":.42,"dist":1.2},lesson=lesson(T("外側ビームの海底点は中央より?","Compared with the centre, outer footprints are...?"),[T("横に離れる","farther across-track"),T("真下に重なる","directly underneath")],0,T("送信角ごとに別の光線を追跡するため、扇状に広がる。","Each steering angle follows a different ray, producing a fan."),T("q = sinθ / c(z)","q = sinθ / c(z)"),T("合成地形と合成海水であり、特定海域ではない。","The terrain and water column are synthetic, not a real site."))))
    tabs.append(pv.viewer_anim3d_tab("refraction",T("音速を誤ると海底が笑う","A wrong sound speed bends the bottom into a smile"),"passed",T("観測は方向を状態に持つ細刻み RK4 で作る。青は雑音入り CTD を 1 m の一定音速層として解析的に逆算した点、赤は一定音速の直線で逆算した点。真の海底や真のロールは推定器へ渡さない。各角度で、実測した曲がりを距離項と角度項の和と比べる。","Observations come from fine-step RK4 with direction as a state. Blue points use analytic straight segments in 1 m constant-speed layers sampled by a noisy CTD; red points assume one constant speed. Neither true seabed nor true roll enters the estimators. At every angle, measured bend is compared with the sum of range and angular terms."),np.arange(n)/20,common,xyz,q,trails=[{"xyz":r["correct"],"color":"#40c4ff","tail":0},{"xyz":r["straight"],"color":"#ef5350","tail":0}],series=[{"label":T("実測した深さの曲がり","measured depth bend"),"values":r["bend"],"unit":"m","color":"#ef5350"},{"label":T("二項近似の曲がり","two-term bend estimate"),"values":r["bend_approx"],"unit":"m","color":"#ffb74d"},{"label":T("実効音速による距離項","range term from effective speed"),"values":r["range_term"],"unit":"m","color":"#66bb6a"},{"label":T("屈折による角度項","angular term from refraction"),"values":r["angle_term"],"unit":"m","color":"#ab47bc"}],numbers=[pv.viewer_number(T("正しい復元の RMS","correct-profile RMS"),"%.3f m"%g["rms"]),pv.viewer_number(T("外側の近似残差","outer approximation residual"),"%.1f %%"%(100*g["smile_relative_error"]))],checks=base,axis=axis,view={"az":-.8,"el":.35,"dist":1.2},lesson=lesson(T("音速プロファイルを無視すると誤差はどこで増える?","Where does ignoring the profile hurt most?"),[T("外側ビーム","outer beams"),T("真下だけ","nadir only")],0,T("斜めほど異なる深さの層を長く通り、屈折の積み残しが増える。","Oblique rays spend longer crossing layers, so neglected refraction accumulates."),T("δz ≈ (C0−ceff)t cosθ0 + ceff t[cosθ0−cos((θ0+θ1)/2)]","δz ≈ (C0−ceff)t cosθ0 + ceff t[cosθ0−cos((θ0+θ1)/2)]"),T("ceff=L/t は各層の音速を経路長で重み付けした調和平均。第1項は距離のずれ、第2項は屈折で平均角度が変わる寄与。角度が経路内で直線的に変わる近似が無視した曲率項を、外側ビームの曲がりの 25 % 以内とする。","ceff=L/t is the path-length-weighted harmonic mean of layer speeds. The first term is range error; the second is the change in mean direction caused by refraction. The approximation neglects curvature in angle along the path, bounded here to 25% of outer-beam bend."))))
    tabs.append(pv.viewer_anim3d_tab("limit",T("限界: 戻らない音と偽の音","Limit: missing and false echoes"),"limit",T("急な崖では鏡面反射が船へ戻らず、気泡は音を遮り、多重反射は遅い偽エコーを作る。往復時間が一つ得られるという前提そのものが壊れる。","A steep cliff can reflect sound away, bubbles can block it, and multipath can create a late false echo. The assumption of one clean travel time then fails."),np.arange(n)/20,common,xyz,q,trails=trail,series=[{"label":T("往復時間","two-way travel time"),"values":r["twtt"],"unit":"s","color":"#ef5350"}],numbers=[pv.viewer_number(T("判定","assessment"),T("要注意","needs review"))],checks=checks(g,True),axis=axis,view={"az":-.8,"el":.35,"dist":1.2},lesson=lesson(T("エコーが二つなら深さは一意?","Do two echoes give one unique depth?"),[T("一意","unique"),T("一意でない","ambiguous")],1,T("反射経路を選ぶ追加判定が必要。","Additional echo classification is required."),T("tobs = min/selected echo time","tobs = min/selected echo time"),T("崖・気泡・多重反射はこの単一反射モデルでは復元できない。","Cliffs, bubbles and multipath exceed this single-return model."))))
    return pv.viewer_spec("multibeam_bathymetry",T("船から音で海底地形を測る","Mapping the seabed with sound from a vessel"),T("マルチビーム測深で、層状の音速が外側ビームをどう曲げるかを見る","See how a layered sound speed bends outer beams in multibeam bathymetry"),T("問い、予想、再生、式、限界の順に、同じ合成観測を二つの方法で復元する。","Follow question, prediction, play, formula and limit while two methods invert the same synthetic observations."),tabs,credit=T("海底・海水・船・観測はすべて合成。代表値による学習用モデルで、実航海の測量には使わない。","Seabed, water, vessel and observations are entirely synthetic representative assumptions for learning, not for real surveys."))

def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument("--check",action="store_true"); ap.add_argument("--out",default=str(OUT_HTML)); a=ap.parse_args(argv)
    r=compute(); g=gates(r); print(g); spec=build_spec(r,g)
    if a.check: print("ok: %d bytes"%len(pv._build_html(spec,list(LANGS)).encode())); return 0
    p=pv.write_viewer(spec,a.out,list(LANGS)); print("wrote",p); return 0
if __name__=="__main__": raise SystemExit(main())
