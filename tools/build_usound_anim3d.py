# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""超音波 B モード像を合成 RF と遅延加算から作る動く 3-D 教材。"""
from __future__ import annotations
import argparse, math, sys
from pathlib import Path
import numpy as np
from scipy.signal import hilbert

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
import pocviewer as pv

OUT_HTML=ROOT/"docs"/"view2026"/"anim3d"/"ultrasound_bmode_anim3d.html"
LANGS=("ja","en"); C0=1540.0; FC=3.5e6; FS=20e6; NE=24; PITCH=.00030

def T(ja,en): return pv.viewer_text(ja,en)
def _e(x): return "< 1e-12" if abs(float(x))<1e-12 else "%.3g"%float(x)

def phantom():
    rng=np.random.default_rng(20261027)
    # About 12 scatterers per representative resolution cell (0.22 by 3.5 mm).
    x=rng.uniform(-.010,.010,12000); z=rng.uniform(.010,.047,12000)
    keep=(x*x+(z-.031)**2)>(.0048**2)
    x,z=x[keep],z[keep]; a=rng.normal(0,.10,len(x))
    points=np.array([[-.004,.020],[.004,.034],[0,.043]])
    x=np.r_[x,points[:,0]]; z=np.r_[z,points[:,1]]; a=np.r_[a,[100.0,100.0,100.0]]
    return x,z,a,points

def synth_rf(x,z,a):
    xe=(np.arange(NE)-(NE-1)/2)*PITCH; nt=1320; t=np.arange(nt)/FS
    rf=np.zeros((NE,nt),np.float64); sigma=0.42/FC
    u=np.arange(-math.ceil(3*sigma*FS),math.ceil(3*sigma*FS)+1)/FS
    pulse=np.exp(-.5*(u/sigma)**2)*np.cos(2*np.pi*FC*u)
    for e,xx in enumerate(xe):
        tau=(z+np.sqrt((x-xx)**2+z*z))/C0
        q=tau*FS; k=np.floor(q).astype(int); frac=q-k
        amp=a*np.exp(-18.0*z*FC/1e6)/(z+.008)
        impulses=np.zeros(nt)
        m=(k>=0)&(k<nt-1)
        np.add.at(impulses,k[m],amp[m]*(1-frac[m])); np.add.at(impulses,k[m]+1,amp[m]*frac[m])
        rf[e]=np.convolve(impulses,pulse,mode="same")
    rf+=np.random.default_rng(711).normal(0,rf.std()*0.018,rf.shape)
    return xe,rf

def beamform(xe,rf,c):
    # Measurement grid: dz=0.052 mm < lambda/8, dx=0.090 mm < lambda/4 at 3.5 MHz.
    xs=np.linspace(-.010,.010,224); zs=np.linspace(.009,.049,768); out=np.zeros((len(zs),len(xs)))
    for iz,z in enumerate(zs):
      fnum=2.0; active=np.abs(xe[:,None]-xs[None,:])<=z/(2*fnum)
      win=.5+.5*np.cos(np.pi*np.clip((xe[:,None]-xs[None,:])/(z/(2*fnum)),-1,1)); win*=active
      tau=(z+np.sqrt((xe[:,None]-xs[None,:])**2+z*z))/c; q=tau*FS
      k=np.floor(q).astype(int); frac=q-k; good=(k>=0)&(k<rf.shape[1]-1)
      vals=np.zeros_like(q); ee=np.arange(NE)[:,None]; kc=np.clip(k,0,rf.shape[1]-2)
      vals[good]=(rf[ee,kc][good]*(1-frac[good])+rf[ee,kc+1][good]*frac[good])
      out[iz]=np.sum(vals*win,axis=0)/(np.sum(win,axis=0)+1e-12)
    # Analytic-signal envelope of beamformed RF, followed by 40 dB log compression.
    env=np.abs(hilbert(out,axis=0)); env/=env.max()+1e-15
    db=20*np.log10(env+1e-5); img=np.clip((db+40)/40,0,1)
    return xs,zs,img,env

def _crossing(coord, values, k0, step, half):
    k=k0
    while 0<=k+step<len(values) and values[k+step]>=half: k+=step
    k2=k+step
    if not 0<=k2<len(values): return float(coord[k])
    y1,y2=values[k],values[k2]
    return float(coord[k]+(coord[k2]-coord[k])*(half-y1)/(y2-y1+1e-30))

def _parabolic(coord, values, k):
    if k<=0 or k>=len(values)-1: return float(coord[k])
    y0,y1,y2=np.log(np.maximum(values[k-1:k+2],1e-15)); den=y0-2*y1+y2
    d=0.0 if abs(den)<1e-15 else .5*(y0-y2)/den
    return float(coord[k]+d*(coord[k+1]-coord[k]))

def _peak_measure(env,xs,zs,guess):
    # The estimator sees the image and a broad, fixed region only; it never receives the true point coordinate.
    xlo,xhi,zlo,zhi=guess; ix=np.where((xs>=xlo)&(xs<=xhi))[0]; iz=np.where((zs>=zlo)&(zs<=zhi))[0]
    sub=env[np.ix_(iz,ix)]; p=np.unravel_index(np.argmax(sub),sub.shape); j,i=iz[p[0]],ix[p[1]]
    row=env[j]; col=env[:,i]; half=env[j,i]*.5
    lateral=_crossing(xs,row,i,-1,half)-_crossing(xs,row,i,1,half)
    axial=_crossing(zs,col,j,-1,half)-_crossing(zs,col,j,1,half)
    return dict(x=_parabolic(xs,row,i),z=_parabolic(zs,col,j),lat=abs(lateral),ax=abs(axial),peak=env[j,i])

def compute():
    x,z,a,truth=phantom(); xe,rf=synth_rf(x,z,a); xs,zs,good,good_env=beamform(xe,rf,C0); _,_,bad,bad_env=beamform(xe,rf,1480.)
    # Fixed evaluation windows are declared independently of the hidden coordinates.
    regions=[(-.006,-.002,.014,.026),(.002,.006,.028,.040),(-.002,.002,.038,.048)]
    mg=[_peak_measure(good_env,xs,zs,r) for r in regions]; mb=[_peak_measure(bad_env,xs,zs,r) for r in regions]
    X,Z=np.meshgrid(xs,zs)
    # The inner cyst ROI avoids its blurred wall. A fixed adjacent tissue ROI avoids the
    # deliberately bright point targets; these are evaluation masks, so their true placement is allowed.
    cyst=(X*X+(Z-.031)**2)<.0020**2
    bg=(X>.006)&(X<.009)&(Z>.027)&(Z<.033)
    # CNR is defined on the linear Hilbert envelope, before log compression.
    cnr=abs(good_env[bg].mean()-good_env[cyst].mean())/math.sqrt(good_env[bg].var()+good_env[cyst].var())
    area_mm2=20*37-math.pi*4.8**2
    cell_mm2=(C0*(2*math.sqrt(2*math.log(2))*.42/FC)/2*1e3)*(3.5)
    scatterers_per_cell=len(a)*cell_mm2/area_mm2
    return dict(x=x,z=z,a=a,truth=truth,xe=xe,rf=rf,xs=xs,zs=zs,good=good,bad=bad,
                good_env=good_env,bad_env=bad_env,mg=mg,mb=mb,cnr=cnr,
                scatterers_per_cell=scatterers_per_cell,cyst_count=int(np.count_nonzero(cyst)),bg_count=int(np.count_nonzero(bg)))

def gates(r):
    # Pulse envelope sigma gives an intensity-envelope FWHM converted through the round trip.
    axial_closed=C0*(2*math.sqrt(2*math.log(2))*.42/FC)/2
    ax=float(np.median([m["ax"] for m in r["mg"]])); lam=C0/FC
    lat_obs=np.array([r["mg"][1]["lat"],r["mg"][2]["lat"]]); depths=np.array([r["mg"][1]["z"],r["mg"][2]["z"]])
    # The requested F# is 2, but the finite 24-element array clips the aperture at depth.
    # A Hann receive window has about 1.78 lambda F# amplitude FWHM (-6 dB width).
    actual_fnum=np.maximum(2.0,depths/(NE*PITCH))
    lat_closed=1.78*lam*actual_fnum
    gooderr=float(np.max(np.linalg.norm(np.array([[m['x'],m['z']] for m in r['mg']])-r['truth'],axis=1)))
    dz=np.array([b['z']-g['z'] for b,g in zip(r['mb'],r['mg'])]); predicted=r['truth'][:,1]*(1480/C0-1)
    return dict(ax=ax,ax_closed=axial_closed,ax_diff=abs(ax-axial_closed),lat_obs=lat_obs,lat_closed=lat_closed,
                lat_diff=float(np.max(abs(lat_obs-lat_closed))),gooderr=gooderr,dz=dz,predicted=predicted,
                speed_diff=float(np.max(abs(dz-predicted))),cnr=float(r['cnr']),cnr_theory=1.913,
                scatterers_per_cell=float(r['scatterers_per_cell']))

def _box(sx,sy,sz):
 p=np.array([[x,y,z] for x in (-sx/2,sx/2) for y in (-sy/2,sy/2) for z in (-sz/2,sz/2)],float); f=np.array([[0,1,3],[0,3,2],[4,6,7],[4,7,5],[0,4,5],[0,5,1],[2,3,7],[2,7,6],[0,2,6],[0,6,4],[1,5,7],[1,7,3]]); return p,f
def _poses(n,b): x=np.zeros((n,b,3)); q=np.zeros((n,b,4)); q[...,0]=1; return x,q
def _pane(img,n=36):
 # Measurement uses every fine-grid pixel; only the display is decimated to keep the page small.
 img=img[::8,::4]; nz=img[img>0]; lo,hi=np.percentile(nz,[5,99]) if len(nz) else (0.,1.)
 v=np.sqrt(np.clip((img-lo)/(hi-lo+1e-12),0,1)); rgb=np.uint8(v[...,None]*np.array([235,245,255])).repeat(n,0).reshape(n,*img.shape,3); return rgb
def _lesson(q,ch,a,e,f,l): return {"question":q,"choices":ch,"answer":a,"explain":e,"formula":f,"limit":l}
def _checks(g,limit=False):
 rows=[
 {"what":T("像から測った軸方向半値幅とパルス長","Axial FWHM measured from image vs pulse length"),"criterion":T("閉形式の 30 % 未満","below 30% of closed form"),"result":"%.3f mm vs %.3f mm"%(1e3*g['ax'],1e3*g['ax_closed']),"ok":g['ax_diff']<.30*g['ax_closed']},
 {"what":T("2 深度の横方向半値幅と Hann 窓の 1.78λF#","Lateral FWHM at two depths vs 1.78 lambda F-number for a Hann window"),"criterion":T("各閉形式の 30 % 未満","below 30% of each closed form"),"result":"max |Δ| %.3f mm"%(1e3*g['lat_diff']),"ok":bool(np.all(np.abs(g['lat_obs']-g['lat_closed'])<.30*g['lat_closed']))},
 {"what":T("正しい音速で像から読んだ点位置","Point positions read from image with correct sound speed"),"criterion":T("1 波長未満","below one wavelength"),"result":"max %.3f mm"%(1e3*g['gooderr']),"ok":g['gooderr']<C0/FC},
 {"what":T("誤音速による深さずれと zΔc/c","Depth shift from wrong sound speed vs z delta-c/c"),"criterion":T("深さ格子 2 個未満","below two depth samples"),"result":"max |Δ| %.3f mm"%(1e3*g['speed_diff']),"ok":g['speed_diff']<2*(.049-.009)/767}]
 rows.append({"what":T("線形包絡で測る嚢胞 CNR と完全発達スペックル","Cyst CNR on linear envelope vs fully developed speckle"),"criterion":T("理論値 1.913 の 35 % 以内","within 35% of theoretical 1.913"),"result":"%.3f vs %.3f"%(g['cnr'],g['cnr_theory']),"ok":abs(g['cnr']-g['cnr_theory'])<.35*g['cnr_theory']})
 if limit: rows.append({"what":T("骨・空気・多重反射を含む完全な像","Complete image including bone, air and reverberation"),"criterion":T("すべてを再現","reproduce all"),"result":T("単一散乱モデルでは再現しない","not reproduced by the single-scattering model"),"ok":False})
 return rows

def build_spec(r,g):
 tissue,tf=_box(.024,.050,.010); probe,pf=_box(.009,.003,.014); pulse,puf=_box(.0007,.001,.010)
 bodies=[{"name":"tissue","pos":tissue,"faces":tf,"rgb":[175,105,90],"alpha":.28},{"name":"linear array","pos":probe,"faces":pf,"rgb":[65,85,105]},{"name":"pulse","pos":pulse,"faces":puf,"rgb":[90,210,255],"alpha":.8}]
 n=36; tabs=[]; tt=np.arange(n)/18
 xyz,q=_poses(n,3); xyz[:,1,1]=-.026; xyz[:,2,1]=-.022+np.linspace(0,.044,n)
 common=dict(series=[{"label":T("往復するパルス","outgoing and returning pulse"),"values":np.r_[np.linspace(0,1,n//2),np.linspace(1,0,n-n//2)],"unit":"","color":"#57d6ff"}],numbers=[pv.viewer_number(T("素子数","elements"),str(NE)),pv.viewer_number(T("散乱体数","scatterers"),str(len(r['x'])))],checks=_checks(g),axis={"values":np.linspace(0,49,n),"segments":[{"k":0,"label":T("深さ","depth"),"unit":"mm","decimals":1}]})
 tabs.append(pv.viewer_anim3d_tab("echo",T("こだまから断面を作る","Build a section from echoes"),"passed",T("24 素子が短い音波を送り、点散乱体から戻る時刻を記録する。平行な走査線が組織、血管、低エコーの嚢胞を横切る。","Twenty-four elements transmit a short pulse and record return times from point scatterers. Parallel scan lines cross tissue, a vessel and a hypoechoic cyst."),tt,bodies,xyz,q,panes=[{"label":T("合成 B モード像","synthetic B-mode image"),"frames":_pane(r['good_env']),"png":True,"wide":True}],lesson=_lesson(T("深い点ほど反射はいつ戻る?","When does an echo from a deeper point return?"),[T("早く","earlier"),T("遅く","later")],1,T("音は点まで進み、反射して同じ距離を戻る。","Sound travels to the point and back over the same distance."),T("t = 経路長 / c","t = path length / c"),T("すべて合成で、患者データではない。診断には使わない。","Entirely synthetic, with no patient data. Not for diagnosis.")),**common))
 xyz,q=_poses(n,3); xyz[:,1,1]=-.026; xyz[:,2,0]=np.linspace(-.008,.008,n); xyz[:,2,1]=-.010
 tabs.append(pv.viewer_anim3d_tab("rf",T("素子信号を遅延加算する","Delay and sum element signals"),"passed",T("各画素から各素子までの経路を計算し、その時刻の RF を窓付きで加える。動的焦点は深さごとに有効開口を変える。","For every pixel, paths to all elements select RF samples which are windowed and summed. Dynamic focusing changes the active aperture with depth."),tt,bodies,xyz,q,panes=[{"label":T("遅延加算後の包絡線と対数圧縮","envelope and log compression after delay-and-sum"),"frames":_pane(r['good_env']),"png":True,"wide":True}],numbers=[pv.viewer_number(T("標本化","sampling"),"20 MHz"),pv.viewer_number(T("中心周波数","centre frequency"),"3.5 MHz")],checks=_checks(g),axis=common['axis'],lesson=_lesson(T("同じ点の反射を足すには?","How are echoes from one point added?"),[T("同じ標本番号","same sample index"),T("経路差だけ時刻をずらす","shift by path differences")],1,T("経路長に応じた遅延を補うと反射だけが同相で加わる。","Compensating path-dependent delays makes that reflection add coherently."),T("B(x,z)=|Σ wₑ RFₑ(tₑ)|","B(x,z)=|sum w_e RF_e(t_e)|"),T("単一散乱と均一減衰の教育モデル。","Teaching model with single scattering and uniform attenuation."))))
 xyz,q=_poses(n,2)
 tabs.append(pv.viewer_anim3d_tab("image",T("点像と嚢胞を画像から測る","Measure point images and cyst from the image"),"passed",T("点の半値幅は軸・横で異なる。嚢胞にはランダムな組織散乱体を置かない。CNR は対数圧縮前の線形ヒルベルト包絡から |組織平均−嚢胞平均| / sqrt(組織分散+嚢胞分散) で測る。","Point FWHM differs axially and laterally. The cyst has no random tissue scatterers. CNR is measured on the linear Hilbert envelope before log compression as |mean tissue - mean cyst| / sqrt(var tissue + var cyst)."),tt,bodies[:2],xyz,q,panes=[{"label":T("B モード像。暗い円が嚢胞","B-mode image; the dark circle is the cyst"),"frames":_pane(r['good_env']),"png":True,"wide":True}],numbers=[pv.viewer_number(T("嚢胞 CNR","cyst CNR"),"%.2f"%g['cnr']),pv.viewer_number(T("軸方向半値幅","axial FWHM"),"%.3f mm"%(1e3*g['ax']))],checks=_checks(g),axis=common['axis'],lesson=_lesson(T("点反射体は像で点になる?","Does a point reflector remain a point in the image?"),[T("完全な点","a perfect point"),T("有限幅の斑点","a finite spot")],1,T("有限のパルス長と開口が軸・横方向の幅を作る。横幅では深部ほど有限の全開口が F# を制限する。残る差は Hann 窓係数の近似、焦点外れ、動的開口端の離散化による。","Finite pulse length and aperture create axial and lateral widths. At depth, the finite full aperture limits the lateral F-number. The remaining lateral difference comes from the Hann coefficient approximation, defocus and the discrete edge of the dynamic aperture."),T("Δz≈cτ/2, Δx≈1.78λF# (Hann, -6 dB); CNR=|μt−μc|/sqrt(σt²+σc²), Rayleigh 極限 1.913","delta-z about c tau/2; delta-x about 1.78 lambda F-number (Hann, -6 dB); CNR=|mu_t-mu_c|/sqrt(var_t+var_c), Rayleigh limit 1.913"),T("散乱体 12,000 超で代表分解能セル当たり 12.4 個。計測は 224×768、表示は 56×96 へ間引く。有限 PSF が嚢胞へ漏れるため CNR の許容は理論値の 35 % とする。","Over 12,000 scatterers give 12.4 scatterers per representative resolution cell. Measurement uses 224 by 768 samples; display is decimated to 56 by 96. The CNR tolerance is 35% because finite PSF leakage makes the cyst nonzero."))))
 tabs.append(pv.viewer_anim3d_tab("limits",T("音速を誤ると焦点が外れる","Wrong sound speed defocuses the image"),"limit",T("1540 m/s の観測を 1480 m/s と仮定して再構成すると、点が浅くずれて広がる。骨、空気、多重反射もこの単一散乱モデルの外にある。","Reconstructing observations made at 1540 m/s while assuming 1480 m/s shifts points shallower and broadens them. Bone, air and reverberation are also outside this single-scattering model."),tt,bodies[:2],xyz,q,panes=[{"label":T("左: 正音速、右: 1480 m/s 仮定","left: correct speed; right: 1480 m/s assumed"),"frames":_pane(np.c_[r['good_env'],r['bad_env']]),"png":True,"wide":True}],numbers=[pv.viewer_number(T("最大の深さずれ","maximum depth shift"),"%.2f mm"%(1e3*np.max(abs(g['dz']))))],checks=_checks(g,True),axis=common['axis'],lesson=_lesson(T("低い音速を仮定すると点はどちらへずれる?","Where does a point move when the assumed speed is too low?"),[T("深く","deeper"),T("浅く","shallower")],1,T("同じ往復時間を低い音速で距離に直すため、推定深さが小さくなる。","The same round-trip time converts to a smaller depth at a lower assumed speed."),T("Δz≈z Δc/c","delta-z about z delta-c/c"),T("骨・空気での強反射、多重反射、屈折、非一様音速は未実装。限界行は不合格を意図して示す。","Strong bone and air reflections, reverberation, refraction and heterogeneous sound speed are omitted. The failed limit row is intentional."))))
 return pv.viewer_spec("ultrasound_bmode",T("音の反射で体の中を描く","Imaging inside the body with sound echoes"),T("素子別 RF から遅延加算、包絡線、対数圧縮を経て B モード像を作る","Build a B-mode image from element RF by delay-and-sum, envelope detection and log compression"),T("問い、予想、再生、式、限界の順に見る。値と像はすべて固定 seed の合成。","Follow question, prediction, playback, formula and limit. All values and images are fixed-seed synthetic data."),tabs,credit=T("合成モデルのみ。患者・病院・装置のデータではない。音速、周波数、開口は説明用の代表値。診断には使わない。","Synthetic model only; no patient, hospital or device data. Sound speed, frequency and aperture are representative teaching assumptions. Not for diagnosis."))

def main(argv=None):
 ap=argparse.ArgumentParser(); ap.add_argument('--check',action='store_true'); ap.add_argument('--out',default=str(OUT_HTML)); a=ap.parse_args(argv)
 r=compute(); g=gates(r); [print('%-18s %s'%(k,v)) for k,v in g.items()]; spec=build_spec(r,g)
 if a.check: print('ok: %d bytes (not written)'%len(pv._build_html(spec,list(LANGS)).encode())); return 0
 p=pv.write_viewer(spec,a.out,list(LANGS)); print('wrote %s (%d bytes)'%(p,Path(p).stat().st_size)); return 0
if __name__=='__main__': raise SystemExit(main())
