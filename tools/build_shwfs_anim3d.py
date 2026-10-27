# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Shack-Hartmann wavefront sensing as a compact moving 3-D lesson."""
from __future__ import annotations
import argparse, math, sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
for p in (str(ROOT),str(ROOT/"tools")):
    if p not in sys.path: sys.path.insert(0,p)
import match3d
import pocviewer as pv

OUT_HTML=ROOT/"docs"/"view2026"/"anim3d"/"shack_hartmann_anim3d.html"
LANGS=("ja","en"); F_MM=12.0; PITCH_MM=.30; WL_UM=.55
LOW_MODES=((2,0),(2,2),(2,-2),(3,1),(3,-1),(4,0))
SYN_MODES=LOW_MODES+((4,2),(5,1))
RICH_MODES=SYN_MODES+((4,-2),(4,4),(5,-1),(5,3))
SUB_N=32; PAD_N=128; HALF=.11; WINDOW=15
PIX_PER_SLOPE=PAD_N*(2*HALF/SUB_N)
T=pv.viewer_text

def _e(x): return "< 1e-12" if abs(float(x))<1e-12 else "%.3g"%float(x)
def _poses(n,b):
    x=np.zeros((n,b,3)); q=np.zeros((n,b,4)); q[...,0]=1; return x,q
def _box(sx,sy,sz):
    p=np.array([[x,y,z] for x in (-sx/2,sx/2) for y in (-sy/2,sy/2) for z in (-sz/2,sz/2)],float)
    f=np.array([[0,1,3],[0,3,2],[4,6,7],[4,7,5],[0,4,5],[0,5,1],[2,3,7],[2,7,6],[0,2,6],[0,6,4],[1,5,7],[1,7,3]])
    return p,f
def _disc(r=.5,n=24):
    a=np.linspace(0,2*np.pi,n,endpoint=False); p=np.vstack([[0,0,0],np.column_stack([np.zeros(n),r*np.cos(a),r*np.sin(a)])])
    return p,np.array([[0,i+1,(i+1)%n+1] for i in range(n)])

def _lenslet_array(x,y):
    pos=[]; faces=[]
    for cx,cy in zip(x,y):
        p,f=_disc(.105,12); p[:,1]+=cx; p[:,2]+=cy; k=len(pos); pos.extend(p); faces.extend(f+k)
    return np.asarray(pos),np.asarray(faces)

def _basis(x,y,modes=SYN_MODES):
    r=np.hypot(x,y); th=np.arctan2(y,x); B,idx=match3d._zernike_eval(r,th,max(k[0] for k in modes))
    return np.column_stack([B[idx.index(k)] for k in modes])

def _slopes(x,y,modes=SYN_MODES):
    h=1e-5
    return (_basis(x+h,y,modes)-_basis(x-h,y,modes))/(2*h),(_basis(x,y+h,modes)-_basis(x,y-h,modes))/(2*h)

def _diffraction_image(coeff,cx,cy,photons,rng,noise=True):
    """Square subaperture -> padded Fraunhofer FFT -> detector noise and quantisation."""
    u=(np.arange(SUB_N)+.5)/SUB_N*(2*HALF)-HALF
    ux,uy=np.meshgrid(u,u); wave=_basis(cx+ux,cy+uy,SYN_MODES)@coeff
    field=np.exp(2j*np.pi*wave).reshape(SUB_N,SUB_N)
    focal=np.abs(np.fft.fftshift(np.fft.fft2(field,s=(PAD_N,PAD_N))))**2
    c=PAD_N//2; h=WINDOW//2; model=focal[c-h:c+h+1,c-h:c+h+1]
    model=photons*model/model.sum()
    if noise:
        # Photon shot noise, 1.6 e- read noise, then 12-bit integer detector counts.
        im=rng.poisson(model+1.2).astype(float)+rng.normal(0,1.6,model.shape)
        im=np.clip(np.rint(im),0,4095)
    else: im=model
    yy,xx=np.mgrid[:WINDOW,:WINDOW]; q=(WINDOW-1)/2
    bg=np.median(np.r_[im[0],im[-1],im[:,0],im[:,-1]]); w=np.maximum(im-bg,0); s=w.sum()
    return float((w*xx).sum()/s-q),float((w*yy).sum()/s-q),im

def _full_diffraction_centroid(coeff,cx,cy):
    u=(np.arange(SUB_N)+.5)/SUB_N*(2*HALF)-HALF; ux,uy=np.meshgrid(u,u)
    wave=_basis(cx+ux,cy+uy,SYN_MODES)@coeff
    focal=np.abs(np.fft.fftshift(np.fft.fft2(np.exp(2j*np.pi*wave).reshape(SUB_N,SUB_N),s=(PAD_N,PAD_N))))**2
    py,px=np.unravel_index(np.argmax(focal),focal.shape); c=PAD_N//2
    return float(px-c),float(py-c)

def _recover(points,x,y,modes):
    gx,gy=_slopes(x,y,modes); A=np.vstack([gx,gy]); b=np.r_[points[:,0],points[:,1]]/PIX_PER_SLOPE
    return np.linalg.lstsq(A,b,rcond=None)[0]

def _mosaic(images,shape):
    n=images.shape[-1]; out=np.zeros((shape[0]*n,shape[1]*n,3),np.uint8)
    hi=np.percentile(images,99.5) or 1
    for k,im in enumerate(images):
        i,j=divmod(k,shape[1]); u=np.clip(255*im/hi,0,255).astype(np.uint8)
        out[i*n:(i+1)*n,j*n:(j+1)*n]=np.stack([u,np.minimum(255,u*1.25),np.minimum(255,u*1.8)],-1)
    return out

def compute():
    grid=np.linspace(-.78,.78,7); xx,yy=np.meshgrid(grid,grid); keep=xx*xx+yy*yy<.93**2
    x,y=xx[keep],yy[keep]
    frames=18; strength=np.linspace(0,.42,frames); base=np.array([.22,-.13,.09,.11,-.07,.055,.045,-.035])
    rng=np.random.default_rng(20261027); rec=[]; low=[]; rich=[]; centroid=[]; mosaics=[]; rms=[]; residual=[]
    for j,s in enumerate(strength):
        truth=s*base/base[0]
        measured=[]; ims=[]; photons=4200
        for cx,cy in zip(x,y):
            ux,uy,im=_diffraction_image(truth,cx,cy,photons,rng); measured.append((ux,uy)); ims.append(im)
        measured=np.asarray(measured); c=_recover(measured,x,y,SYN_MODES)
        rec.append(c); low.append(_recover(measured,x,y,LOW_MODES)); rich.append(_recover(measured,x,y,RICH_MODES))
        centroid.append(measured); mosaics.append(_mosaic(np.asarray(ims),(7,7)))
        z=_basis(x,y,SYN_MODES); rms.append(float(np.sqrt(np.mean((z@truth)**2))))
        residual.append(float(np.sqrt(np.mean((z@(c-truth))**2))))
    rec=np.asarray(rec); low=np.asarray(low); rich=np.asarray(rich); centroid=np.asarray(centroid); residual=np.asarray(residual)
    # Fixed grid/window, fresh diffraction images; fit log(error)=slope*log(photons)+constant.
    levels=np.array([500,1000,2000,4000,8000,16000]); noise=[]
    truth=.30*base/base[0]
    for ph in levels:
        errors=[]
        for _ in range(10):
            pts=[]
            for cx,cy in zip(x,y):
                ux,uy,_=_diffraction_image(truth,cx,cy,int(ph),rng); pts.append((ux,uy))
            c=_recover(np.asarray(pts),x,y,SYN_MODES)
            errors.append(np.sqrt(np.mean((_basis(x,y)@(c-truth))**2)))
        noise.append(np.median(errors))
    photon_slope=float(np.polyfit(np.log(levels),np.log(noise),1)[0])
    # Dynamic range: noiseless diffraction centroid in the same fixed detector window.
    amps=np.linspace(.08,4.5,18); dyn=[]
    for a in amps:
        truth=np.zeros(len(SYN_MODES)); truth[0]=a; shifts=[]
        for cx,cy in zip(x,y):
            ux,uy=_full_diffraction_centroid(truth,cx,cy); shifts.extend((abs(ux),abs(uy)))
        dyn.append(float(max(shifts)-(WINDOW-1)/2))
    z=_basis(x,y,SYN_MODES); end=strength[-1]*base/base[0]
    low_wave=_basis(x,y,LOW_MODES)@low[-1]; rich_wave=_basis(x,y,RICH_MODES)@rich[-1]; true_wave=z@end
    low_error=float(np.sqrt(np.mean((low_wave-true_wave)**2))); rich_error=float(np.sqrt(np.mean((rich_wave-true_wave)**2)))
    noise_allow=float(2.5*np.median(noise[-2:]))
    return dict(x=x,y=y,strength=strength,truth=strength[:,None]*base/base[0],recovered=rec,
      recovered_low=low,recovered_rich=rich,centroid=centroid,mosaics=np.asarray(mosaics),rms=np.asarray(rms),residual=residual,
      levels=levels,noise=np.asarray(noise),photon_slope=photon_slope,amps=amps,dynamic=np.asarray(dyn),
      low_error=low_error,matched_error=float(residual[-1]),rich_error=rich_error,noise_allow=noise_allow)

def gates(r):
    c=r["truth"][-1]; q=r["recovered"][-1]
    coeff_rms=float(np.sqrt(np.mean((q-c)**2)))
    first_bad=int(np.flatnonzero(r["dynamic"]>0)[0])
    return dict(coeff_rms=coeff_rms,wavefront_rms=float(r["residual"][-1]),photon_slope=float(r["photon_slope"]),
      low_error=r["low_error"],matched_error=r["matched_error"],rich_error=r["rich_error"],noise_allow=r["noise_allow"],
      dynamic_limit=float(r["amps"][first_bad]),dynamic_over=float(r["dynamic"][-1]))

def _checks(g,limit=False):
    rows=[
      {"what":T("画像重心から復元した Zernike 係数","Zernike coefficients recovered from image centroids"),"criterion":"RMS < 0.025 waves","result":"%.4f waves"%g["coeff_rms"],"ok":g["coeff_rms"]<.025},
      {"what":T("復元波面と合成波面","reconstructed versus synthetic wavefront"),"criterion":"RMS < 0.025 waves","result":"%.4f waves"%g["wavefront_rms"],"ok":g["wavefront_rms"]<.025},
      {"what":T("光子数に対する復元誤差の両対数傾き","log-log slope of recovery error versus photon count"),"criterion":"−0.70–−0.30 (theory −0.5)","result":"%.3f"%g["photon_slope"],"ok":-.70<g["photon_slope"]<-.30},
      {"what":T("合成8モードを6 / 8 / 12モードで復元","8 synthetic modes recovered with 6 / 8 / 12 modes"),"criterion":T("8,12モード誤差 < 雑音許容 %.4f"%g["noise_allow"],"8- and 12-mode errors < noise allowance %.4f"%g["noise_allow"]),"result":"%.4f / %.4f / %.4f waves"%(g["low_error"],g["matched_error"],g["rich_error"]),"ok":g["matched_error"]<g["noise_allow"] and g["rich_error"]<g["noise_allow"] and g["low_error"]>g["matched_error"]}]
    if limit: rows.append({"what":T("スポットが隣のセルへ出ても一意に復元","unique recovery after a spot leaves its cell"),"criterion":T("窓の半幅以内","inside half-window"),"result":T("%.2f waves で範囲外、最大 %.2f px"%(g["dynamic_limit"],g["dynamic_over"]),"outside at %.2f waves; maximum %.2f px"%(g["dynamic_limit"],g["dynamic_over"])),"ok":False})
    return rows

def _lesson(q,ch,a,e,f,l): return {"question":q,"choices":ch,"answer":a,"explain":e,"formula":f,"limit":l}
def build_spec(r,g):
    lens,lf=_lenslet_array(r["x"],r["y"]); cam,cf=_box(.12,2.5,2.5); n=len(r["strength"]); xyz,q=_poses(n,2); xyz[:,1,0]=1.0
    scene=[{"name":"lenslet array","pos":lens,"faces":lf,"rgb":[80,190,245],"alpha":.42},{"name":"camera","pos":cam,"faces":cf,"rgb":[75,85,96],"alpha":.30}]
    checks=_checks(g); tabs=[]
    tabs.append(pv.viewer_anim3d_tab("principle",T("ずれから傾きを読む","Reading slope from displacement"),"passed",T("各32×32サブ開口の複素波面を128×128へゼロ詰めし、フラウンホーファー FFT の強度からスポット像を作る。開口内の高次ゆがみも、ぼけと非対称として残る。","Each 32 by 32 complex subaperture is zero-padded to 128 by 128; Fraunhofer FFT intensity forms the spot. Higher-order shape inside the aperture remains as blur and asymmetry."),np.arange(n)/12,scene,xyz,q,panes=[{"label":T("カメラ像: 各セルの回折スポット","camera image: one diffraction spot per cell"),"frames":r["mosaics"],"png":True,"wide":True}],series=[{"label":T("波面 RMS","wavefront RMS"),"values":r["rms"],"unit":" waves","color":"#4fc3f7"}],numbers=[pv.viewer_number(T("小レンズ数","lenslets"),str(len(r["x"]))),pv.viewer_number(T("焦点距離","focal length"),"12 mm")],checks=checks,axis={"values":r["strength"],"segments":[{"k":0,"label":T("デフォーカス係数","defocus coefficient"),"unit":" waves","decimals":2}]},view={"az":-.7,"el":.35,"dist":1},lesson=_lesson(T("スポットの横ずれは何を測る?","What does lateral spot displacement measure?"),[T("波面の高さ","wavefront height"),T("波面の傾き","wavefront slope")],1,T("回折スポットの重心はサブ開口の平均傾きに対応する。","The diffraction-spot centroid corresponds to mean slope over the subaperture."),T("I = |FFT{exp(i 2πW/λ)}|²","I = |FFT{exp(i 2πW/λ)}|²"),T("1セル内の細かな高次形状は位置だけでなくスポット形状にも現れる。","Fine high-order shape within one cell also changes spot shape, not only position."))))
    tabs.append(pv.viewer_anim3d_tab("array",T("レンズ配列とスポット像","Lenslet array and spot image"),"passed",T("固定した円形瞳を7×7格子で標本化する。円内に入るセルだけを使い、雑音入り像から重心を測る。","A fixed circular pupil is sampled by a 7 by 7 grid. Only cells inside the circle are used, and centroids are measured from noisy images."),np.arange(n)/12,scene,xyz,q,panes=[{"label":T("読み出したスポット格子","measured spot grid"),"frames":r["mosaics"],"png":True}],series=[{"label":T("復元残差","reconstruction residual"),"values":r["residual"],"unit":" waves","color":"#ffb74d"}],checks=checks,axis={"values":r["strength"],"segments":[{"k":0,"label":T("収差の強さ","aberration strength"),"unit":" waves","decimals":2}]},view={"az":-.9,"el":.4,"dist":.95},lesson=_lesson(T("平面波のスポットはどう並ぶ?","How do spots from a flat wavefront arrange?"),[T("規則格子","regular grid"),T("中心に1点","one central point")],0,T("各小レンズの傾きがゼロなので、焦点は基準格子へ戻る。","Zero slope at every lenslet returns foci to the reference grid."),T("∇W = 0 ⇒ Δx = Δy = 0","∇W = 0 ⇒ Δx = Δy = 0"),T("欠けたスポットや背景むらはここでは入れていない。","Missing spots and uneven background are omitted."))))
    tabs.append(pv.viewer_anim3d_tab("recover",T("傾きから波面を復元","Reconstructing a wavefront from slopes"),"passed",T("観測はサブ開口 FFT から作り、復元行列は別にレンズ中心の Zernike 傾きで作る近似。合成8モードを6、8、12モードで解き、高次の取りこぼしと余分なモードへの混ざりを比べる。","Observations come from subaperture FFTs; the separate recovery matrix approximates each lenslet by Zernike slope at its centre. Eight synthetic modes are solved with 6, 8 and 12 modes to expose omitted high order and leakage into extra modes."),np.arange(n)/12,scene,xyz,q,series=[{"label":T("真のデフォーカス","true defocus"),"values":r["truth"][:,0],"unit":" waves","color":"#4fc3f7"},{"label":T("8モード復元","8-mode recovery"),"values":r["recovered"][:,0],"unit":" waves","color":"#ffb74d"}],numbers=[pv.viewer_number(T("6 / 8 / 12モード波面誤差","6 / 8 / 12-mode wavefront errors"),"%.4f / %.4f / %.4f"%(g["low_error"],g["matched_error"],g["rich_error"])),pv.viewer_number(T("雑音から求めた許容","allowance propagated from noise"),"%.4f waves"%g["noise_allow"])],checks=checks,axis={"values":r["strength"],"segments":[{"k":0,"label":T("入力デフォーカス","input defocus"),"unit":" waves","decimals":2}]},view={"az":-.65,"el":.3,"dist":1},lesson=_lesson(T("スポット1個だけで波面全体を復元できる?","Can one spot recover the full wavefront?"),[T("できる","yes"),T("全セルの傾きが要る","slopes from all cells are needed")],1,T("各セルは局所傾きだけを測るため、全体のモードは多数点を同時に解いて得る。","Each cell measures only local slope, so global modes require a simultaneous fit to many points."),T("min_c ||Acentre c − scentroid||²","min_c ||Acentre c − scentroid||²"),T("中心傾きはサブ開口平均の近似。少ないモードは高次を混ぜ、多すぎるモードは雑音を余分な係数へ流す。","Centre slope approximates the subaperture mean. Too few modes mix omitted high order; too many leak noise into extra coefficients."))))
    m=len(r["amps"]); x2,q2=_poses(m,2); x2[:,1,0]=1
    tabs.append(pv.viewer_anim3d_tab("limits",T("細かさ・明るさ・測定範囲","Sampling, light and dynamic range"),"limit",T("固定グリッドと窓で光子数6点の誤差を測り、両対数傾きを当てはめる。測定範囲も同じ回折スポットのピークがセル半幅を越えた所で決める。","With grid and window fixed, errors at six photon levels give a fitted log-log slope. Dynamic range is also found from the same diffraction spot when its peak crosses the cell half-width."),np.arange(m)/12,scene,x2,q2,series=[{"label":T("回折ピークのセル窓超過","diffraction peak beyond cell window"),"values":r["dynamic"],"unit":" px","color":"#ef6c00","threshold":0}],numbers=[pv.viewer_number(T("範囲を外れる係数","coefficient leaving range"),"%.2f waves"%g["dynamic_limit"]),pv.viewer_number(T("光子誤差の両対数傾き","photon-error log-log slope"),"%.3f"%g["photon_slope"])],checks=_checks(g,True),axis={"values":r["amps"],"segments":[{"k":0,"label":T("デフォーカス係数","defocus coefficient"),"unit":" waves","decimals":2}]},view={"az":-.8,"el":.4,"dist":.95},lesson=_lesson(T("収差をどこまでも大きくして測れる?","Can arbitrarily large aberration be measured?"),[T("測れる","it can"),T("隣のセルと混同する","spots become confused with neighbours")],1,T("回折ピークがセル間隔へ近づくと対応付けが一意でなくなる。","Association becomes ambiguous as the diffraction peak approaches the neighbouring cell."),T("|peak(FFT)| < pitch/2","|peak(FFT)| < pitch/2"),T("セルより細かな揺らぎは見えず、弱い光では重心がぶれる。固定窓を越えると復元は壊れる。","Structure finer than a cell is unseen; weak light jitters centroids. Recovery fails beyond the fixed window."))))
    return pv.viewer_spec("shack-hartmann",T("スポットのずれで光の波面を測る","Measuring a wavefront from spot shifts"),T("小レンズ配列、カメラ像、Zernike 復元、標本化と光量の限界","Lenslet array, camera image, Zernike recovery, and sampling and light limits"),T("①問い → ②予想 → ③再生 → ④式 → ⑤限界。3-D はドラッグで回せる。","Follow ① question → ② prediction → ③ play → ④ formula → ⑤ limit. Drag to rotate the 3-D view."),tabs,credit=T("波面、レンズ配列、スポット像はすべて固定 seed の合成データ。寸法は説明用の仮定で、特定の製品を表さない。","Wavefront, lenslet array and spot images are fixed-seed synthetic data. Dimensions are explanatory assumptions and represent no specific product."))

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument("--check",action="store_true"); ap.add_argument("--out",default=str(OUT_HTML)); a=ap.parse_args(argv)
    r=compute(); g=gates(r)
    for k,v in g.items(): print("%-24s %s"%(k,v))
    spec=build_spec(r,g)
    if a.check: print("ok: %d bytes (not written)"%len(pv._build_html(spec,list(LANGS)).encode())); return 0
    path=pv.write_viewer(spec,a.out,list(LANGS)); print("wrote %s (%d bytes)"%(path,Path(path).stat().st_size)); return 0
if __name__=="__main__": raise SystemExit(main())
