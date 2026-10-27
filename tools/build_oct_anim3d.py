# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""合成 OCT で網膜の層厚を測る、動く 3-D 教材。患者データは使わない。"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ops
import pocviewer as pv

OUT_HTML = ROOT / "docs" / "view2026" / "anim3d" / "oct_retina_anim3d.html"
LANGS = ("ja", "en")
NX, SPECTROMETER_PIXELS, FRAMES = 128, 2048, 17
LAMBDA0_NM = 840.0
BANDS_NM = (45.0, 70.0)


def T(ja, en):
    return pv.viewer_text(ja, en)


def _e(x):
    return "< 1e-12" if abs(float(x)) < 1e-12 else "%.3g" % float(x)


def axial_resolution_um(band_nm):
    return 2.0 * math.log(2.0) / math.pi * (LAMBDA0_NM ** 2) / band_nm / 1000.0


def _fwhm(y, dz):
    """ピーク位置を知らず、半値の左右交点だけから幅を測る。"""
    y = np.asarray(y, float)
    p = int(np.argmax(y)); half = y[p] / 2.0
    left = np.where(y[:p] <= half)[0]
    right = np.where(y[p + 1:] <= half)[0]
    if not len(left) or not len(right):
        raise ValueError("FWHM is outside the sampled depth range")
    i = int(left[-1]); j = p + 1 + int(right[0])
    xl = i + (half-y[i])/(y[i+1]-y[i])
    xr = j-1 + (half-y[j-1])/(y[j]-y[j-1])
    return float((xr-xl)*dz)


def source_spectrum(band_nm):
    """波長等間隔の分光器上に、波長 FWHM を持つ Gaussian 光源を置く。"""
    lam_nm=np.linspace(LAMBDA0_NM-3*band_nm,LAMBDA0_NM+3*band_nm,SPECTROMETER_PIXELS)
    source=np.exp(-4*math.log(2)*((lam_nm-LAMBDA0_NM)/band_nm)**2)
    return lam_nm,source


def k_linearize(lam_nm, values):
    """波長等間隔の観測を k=2π/λ の等間隔へ補間する。"""
    k=2*math.pi/(np.asarray(lam_nm,float)/1000.0)
    order=np.argsort(k); k=k[order]; v=np.asarray(values)[order]
    klin=np.linspace(k[0],k[-1],len(k))
    if v.ndim==1: out=np.interp(klin,k,v)
    else: out=np.vstack([np.interp(klin,k,v[:,c]) for c in range(v.shape[1])]).T
    dk=float(klin[1]-klin[0]); dz=math.pi/(len(klin)*dk)
    return klin,out,dz


def point_ascan(band_nm, depth_um=173.37, seed=0):
    """波長分光器の干渉縞を k 線形化して逆 FFT する。"""
    lam,source=source_spectrum(band_nm); k=2*math.pi/(lam/1000.0)
    rng=np.random.default_rng(seed)
    interferogram=source*np.cos(2*k*depth_um+.37)
    interferogram += rng.normal(0,2e-5,len(lam))
    klin,y,dz=k_linearize(lam,interferogram)
    scan=np.abs(np.fft.rfft(y*np.hanning(len(y))))
    return scan,dz


def geometry():
    x = np.linspace(-1.0, 1.0, NX)
    pit = 72.0 * np.exp(-(x/0.24)**2)
    top = 145.35 + 7.0*x*x + pit
    middle = top + 78.65 + 8.0*np.cos(1.7*np.pi*x)
    bottom = middle + 112.40 + 5.0*np.sin(1.3*np.pi*x)
    return x, np.vstack([top, middle, bottom])


def synthesize_bscan(band_nm=BANDS_NM[1]):
    """波長空間の干渉スペクトルを列ごとに合成し、k 線形化して逆 FFT する。"""
    x,bounds_um=geometry(); lam,source=source_spectrum(band_nm); k=2*math.pi/(lam/1000.0)
    spectra=np.empty((len(lam),NX),float)
    for col in range(NX):
        rng = np.random.default_rng(9100 + col)
        fringe=np.zeros(len(lam),float)
        for amp,z in zip((1.0,.82,.70),bounds_um[:,col]):
            fringe += amp*np.cos(2*k*z+rng.uniform(-.22,.22))
        # weak random-phase scatterers create speckle; detector noise is added in spectral space.
        for z in rng.uniform(bounds_um[0,col],bounds_um[2,col],16):
            fringe += .018*np.cos(2*k*z+rng.uniform(-np.pi,np.pi))
        spectra[:,col]=source*fringe+rng.normal(0,.0025,len(lam))
    klin,linear,dz=k_linearize(lam,spectra)
    out=np.abs(np.fft.rfft(linear*np.hanning(len(lam))[:,None],axis=0))
    out /= np.percentile(out, 99.7)
    return x,bounds_um,np.clip(out,0,1),dz


def _path(score, floor=None, jump=5):
    """画像全体から連続な最大勾配経路を選ぶ。floor は先に測った経路だけから作る。"""
    s=np.asarray(score,float).copy(); h,w=s.shape
    s[:3]=0; s[-3:]=0
    if floor is not None:
        for c,r in enumerate(np.asarray(floor,int)): s[:max(0,r),c]=-np.inf
    cost = np.full((h,w), -np.inf); back=np.zeros((h,w),np.int16); cost[:,0]=s[:,0]
    penalty=.055
    for c in range(1,w):
        for r in range(h):
            a=max(0,r-jump); b=min(h,r+jump+1)
            cand=cost[a:b,c-1]-penalty*np.abs(np.arange(a,b)-r)
            q=int(np.argmax(cand)); cost[r,c]=s[r,c]+cand[q]; back[r,c]=a+q
    rows=np.empty(w,int); rows[-1]=int(np.argmax(cost[:,-1]))
    for c in range(w-1,0,-1): rows[c-1]=back[rows[c],c]
    return rows


def measure(bscan,dz):
    smooth = np.asarray(ops.RT["gaussian"](bscan, .15, .0), float)
    edge = np.asarray(ops.RT["sobel_mag"](smooth, .0, .0), float)
    # 解剖学的仮定は「別の境界は直前の境界から 45 µm 以上下」のみ。真の位置や窓は渡さない。
    gap=max(1,int(math.ceil(45.0/dz)))
    p0=_path(edge); p1=_path(edge,p0+gap); p2=_path(edge,p1+gap)
    paths=np.vstack([p0,p1,p2]).astype(float)*dz
    return paths, edge


def spectral_pixel_rolloff(depth_um,band_nm=BANDS_NM[1]):
    """有限な波長画素内を数値積分した振幅低下と、中心画素幅による sinc 近似。"""
    lam,source=source_spectrum(band_nm); dl=float(lam[1]-lam[0]); offsets=np.linspace(-.5,.5,33)*dl
    fine=lam[:,None]+offsets[None,:]; kk=2*math.pi/(fine/1000.0)
    centre=2*math.pi/(lam/1000.0)
    box=np.mean(np.exp(-2j*kk*depth_um),axis=1)
    measured=float(abs(np.sum(source*box*np.exp(2j*centre*depth_um))/np.sum(source)))
    dk_pixel=2*math.pi*dl/(LAMBDA0_NM/1000.0)**2/1000.0
    closed=float(abs(np.sinc(dk_pixel*depth_um/math.pi)))
    return measured,closed


def compute():
    widths=[]; dzs=[]
    for i,b in enumerate(BANDS_NM):
        a,dz=point_ascan(b,seed=100+i); widths.append(_fwhm(a,dz)); dzs.append(dz)
    x,truth,bscan,dz=synthesize_bscan(); measured,edge=measure(bscan,dz)
    thick_truth=truth[2]-truth[0]; thick_meas=measured[2]-measured[0]
    pit_truth=((truth[0,0]+truth[0,-1])/2-truth[0,NX//2])
    pit_meas=((measured[0,0]+measured[0,-1])/2-measured[0,NX//2])
    roll=np.array([spectral_pixel_rolloff(z) for z in (150.0,600.0)])
    g={"resolution_measured":np.array(widths),"resolution_closed":np.array([axial_resolution_um(b) for b in BANDS_NM]),
       "thickness_max_error":float(np.max(np.abs(thick_meas-thick_truth))),
       "pit_measured":float(pit_meas),"pit_truth":float(pit_truth),"pit_error":float(abs(pit_meas-pit_truth)),
       "rolloff_measured":roll[:,0],"rolloff_closed":roll[:,1],"rolloff_error":float(np.max(abs(roll[:,0]-roll[:,1]))),"dz":dz}
    return {"x":x,"truth":truth,"bscan":bscan,"measured":measured,"edge":edge,"dz":dz,"g":g}


def _grid_mesh(x, layers):
    yy=np.linspace(-.22,.22,7); pos=[]; faces=[]
    for li,zline in enumerate(layers):
        base=len(pos)
        for y in yy:
            for xx,zz in zip(x,zline): pos.append([6*xx,6*y,-zz/55])
        for j in range(len(yy)-1):
            for i in range(len(x)-1):
                a=base+j*len(x)+i; faces.extend([[a,a+1,a+len(x)+1],[a,a+len(x)+1,a+len(x)]])
    return np.asarray(pos,float),np.asarray(faces,int)


def _scanner_mesh():
    p=np.array([[-.18,-.18,0],[.18,-.18,0],[.18,.18,0],[-.18,.18,0],[-.08,-.08,-5],[.08,-.08,-5],[.08,.08,-5],[-.08,.08,-5]],float)
    f=np.array([[0,1,2],[0,2,3],[4,6,5],[4,7,6],[0,4,5],[0,5,1],[1,5,6],[1,6,2],[2,6,7],[2,7,3],[3,7,4],[3,4,0]])
    return p,f


def _poses(n,b):
    xyz=np.zeros((n,b,3)); q=np.zeros((n,b,4)); q[...,0]=1; return xyz,q


def _pane(img, cursor=True):
    base=(np.clip(img[::4],0,1)*255).astype(np.uint8)  # 表示だけ深さ方向を間引く。測定は全 1,025 点。
    base=np.stack([base,base,base],axis=-1)
    frames=[]
    for k in range(FRAMES):
        a=base.copy(); c=round(k*(NX-1)/(FRAMES-1))
        if cursor: a[:,max(0,c-1):min(NX,c+2)]=(255,180,45)
        frames.append(a)
    return np.asarray(frames)


def checks(g, limit=False):
    diff=np.abs(g["resolution_measured"]-g["resolution_closed"])
    rows=[
      {"what":T("逆 FFT 点反射の半値幅と軸方向分解能(帯域 2 種)","inverse-FFT point-reflector FWHM vs axial resolution (two bandwidths)"),"criterion":"≤ 1.5 µm","result":"%.2f / %.2f µm"%tuple(diff),"ok":bool(np.max(diff)<=1.5)},
      {"what":T("B スキャンだけから測った全層厚と合成幾何","total layer thickness measured only from B-scan vs synthetic geometry"),"criterion":T("≤ 10 µm (約 13 深さ画素・2 PSF 幅)","≤ 10 µm (about 13 depth pixels or two PSF widths)"),"result":"%.2f µm"%g["thickness_max_error"],"ok":g["thickness_max_error"]<=10},
      {"what":T("画像から測った中心窩のくぼみと合成幾何","foveal pit measured from image vs synthetic geometry"),"criterion":"≤ 8 µm","result":"%.2f µm"%g["pit_error"],"ok":g["pit_error"]<=8}]
    if limit:
        rows.extend([
          {"what":T("有限な分光器画素で測った roll-off と sinc 閉形式","roll-off measured with finite spectrometer pixels vs sinc closed form"),"criterion":"< 0.02","result":"%.4f"%g["rolloff_error"],"ok":g["rolloff_error"]<.02},
          {"what":T("600 µm 深部で 95 % 以上の感度を保つ","retain at least 95% sensitivity at 600 µm depth"),"criterion":"≥ 0.95","result":"%.3f"%g["rolloff_measured"][1],"ok":g["rolloff_measured"][1]>=.95}])
    return rows


def lesson(q,c,a,e,f,l):
    return {"question":q,"choices":c,"answer":a,"explain":e,"formula":f,"limit":l}


def build_spec(r):
    x,truth,bscan,measured,g=r["x"],r["truth"],r["bscan"],r["measured"],r["g"]
    pos,faces=_grid_mesh(x[::2],truth[:,::2]); beam,bf=_scanner_mesh()
    bodies=[{"name":"retinal layers","pos":pos,"faces":faces,"rgb":[90,185,235],"alpha":.52},{"name":"scanning light","pos":beam,"faces":bf,"rgb":[255,205,70],"alpha":.8}]
    xyz,q=_poses(FRAMES,2); xyz[:,1,0]=np.linspace(-6,6,FRAMES); xyz[:,1,2]=3
    times=np.arange(FRAMES)/12
    common=dict(t=times,bodies=bodies,xyz=xyz,quat=q,view={"target":[0,0,-3.5],"distance":13,"yaw":.4,"pitch":-.25})
    ax={"values":np.linspace(-1,1,FRAMES),"segments":[{"k":0,"label":T("走査位置","scan position"),"unit":"","decimals":2}]}
    p1,_=point_ascan(BANDS_NM[1]); scan_series=np.interp(np.linspace(0,len(p1)-1,FRAMES),np.arange(len(p1)),p1)
    tabs=[]
    tabs.append(pv.viewer_anim3d_tab("interference",T("干渉が深さを符号にする","Interference encodes depth"),"passed",T("参照光と網膜の反射光は、光路差に応じた周波数の縞を分光器に作る。黄色い走査光が中心窩を横切る。","Reference and retinal reflections form spectral fringes whose frequency encodes path difference. The yellow scan crosses the fovea."),series=[{"label":T("点反射の A スキャン","point-reflector A-scan"),"values":scan_series,"unit":"","color":"#ffd54f"}],numbers=[pv.viewer_number(T("中心波長","centre wavelength"),"840 nm")],checks=checks(g),axis=ax,lesson=lesson(T("深い反射ほどスペクトルの縞はどうなる?","What happens to spectral fringes for a deeper reflector?"),[T("細かくなる","become finer"),T("粗くなる","become coarser")],0,T("光路差が大きいほど波数に対する位相の回転が速い。","A larger path difference rotates phase faster with wavenumber."),T("I(k) ∝ cos(2kz)","I(k) ∝ cos(2kz)"),T("単一散乱と均一な屈折率を仮定する。","Single scattering and a uniform refractive index are assumed.")),**common))
    tabs.append(pv.viewer_anim3d_tab("ascan",T("スペクトルを逆 FFT する","Inverse FFT the spectrum"),"passed",T("波長等間隔の2048画素でガウス光源と干渉縞を観測し、k=2π/λ の等間隔へ補間してから逆 FFT する。深さ刻み0.787 µmはk範囲から決まり、閉形式からは与えていない。","A 2048-pixel spectrometer samples a Gaussian source and fringes uniformly in wavelength. They are interpolated to uniform k=2π/λ before inverse FFT. The 0.787 µm depth pitch comes from the k range, not the closed form."),series=[{"label":T("45 nm の実測半値幅","measured FWHM at 45 nm"),"values":np.full(FRAMES,g["resolution_measured"][0]),"unit":"µm","color":"#ff8a65"},{"label":T("70 nm の実測半値幅","measured FWHM at 70 nm"),"values":np.full(FRAMES,g["resolution_measured"][1]),"unit":"µm","color":"#4fc3f7"}],numbers=[pv.viewer_number(T("閉形式","closed form"),"2 ln2/π · λ₀²/Δλ")],checks=checks(g),axis=ax,lesson=lesson(T("光源の帯域を広げると深さ分解能は?","What does a broader source bandwidth do to depth resolution?"),[T("細かくなる","improves"),T("粗くなる","worsens")],0,T("広い波数帯域の逆 FFT は狭い深さピークになる。","A wider wavenumber band transforms into a narrower depth peak."),T("δz = 2 ln2/π · λ₀²/Δλ","δz = 2 ln2/π · λ₀²/Δλ"),T("空気中の値。組織では屈折率で割る。","Value in air; divide by refractive index in tissue.")),**common))
    tabs.append(pv.viewer_anim3d_tab("bscan",T("A スキャンを並べて層を測る","Stack A-scans and measure layers"),"passed",T("gaussian と sobel_mag の後、最初の境界は画像全体から探索する。次の境界は測定済み経路の45 µm以上下を探す。この最小間隔だけを解剖学的仮定とし、真の位置は推定器へ渡さない。","After gaussian and sobel_mag, the first boundary is searched over the whole image. Each next boundary is sought at least 45 µm below the measured path. This minimum spacing is the only anatomical assumption; true positions are not passed to the estimator."),panes=[{"label":T("合成 B スキャン。黄線は走査位置","synthetic B-scan; yellow line is scan position"),"frames":_pane(bscan),"png":True,"wide":True}],series=[{"label":T("測定した全層厚","measured total thickness"),"values":np.interp(np.linspace(0,NX-1,FRAMES),np.arange(NX),measured[2]-measured[0]),"unit":"µm","color":"#80cbc4"}],numbers=[pv.viewer_number(T("最大厚み誤差","maximum thickness error"),"%.2f µm"%g["thickness_max_error"]),pv.viewer_number(T("中心窩の誤差","foveal-pit error"),"%.2f µm"%g["pit_error"])],checks=checks(g),axis=ax,lesson=lesson(T("境界を一列ずつ最大勾配だけで選ぶと何が起こる?","What happens if every column independently picks only the strongest gradient?"),[T("スペックルへ飛ぶ","it jumps to speckle"),T("必ず同じ層を追う","it always follows one layer")],0,T("連続性の費用を加えた経路探索で飛びを抑える。","A path search with a continuity cost suppresses jumps."),T("score = Σ edge − continuity cost","score = Σ edge − continuity cost"),T("合成データであり、患者の診断には使えない。","Synthetic data; it must not be used for diagnosis.")),**common))
    tabs.append(pv.viewer_anim3d_tab("limits",T("深くなるほど像が壊れる","Why deeper images degrade"),"limit",T("有限幅の分光器画素で干渉縞を箱平均すると、600 µm の反射振幅は 0.798 まで落ちる。sinc の閉形式は 0.811。分散差はピークを広げ、実信号の逆 FFT は鏡像も作る。","Box-averaging fringes over finite spectrometer pixels reduces a reflector at 600 µm to amplitude 0.798; the sinc closed form gives 0.811. Dispersion mismatch broadens peaks, and the inverse FFT of a real signal also creates a mirror image."),panes=[{"label":T("有限画素の roll-off を含まない B スキャン","B-scan without finite-pixel roll-off"),"frames":_pane(bscan),"png":True,"wide":True}],series=[{"label":T("画素内積分で測った感度","sensitivity measured by pixel integration"),"values":np.interp(np.linspace(150,600,FRAMES),(150,600),g["rolloff_measured"]),"unit":"","color":"#ff8a65"},{"label":T("sinc 閉形式","sinc closed form"),"values":np.interp(np.linspace(150,600,FRAMES),(150,600),g["rolloff_closed"]),"unit":"","color":"#4fc3f7"}],numbers=[pv.viewer_number(T("600 µm の実測感度","measured sensitivity at 600 µm"),"%.3f"%g["rolloff_measured"][1])],checks=checks(g,True),axis=ax,lesson=lesson(T("この画像だけで診断できる?","Can this image be used for diagnosis?"),[T("できる","yes"),T("できない","no")],1,T("患者データではなく、単純化した合成散乱体である。","It is not patient data but a simplified synthetic scatterer model."),T("roll-off・分散・鏡像は別々に校正","calibrate roll-off, dispersion, and mirror image separately"),T("深部感度、分散、多重散乱、眼球運動を含めない。","Depth sensitivity, dispersion, multiple scattering, and eye motion are omitted.")),**common))
    return pv.viewer_spec("oct_retina",T("光で目の奥の断面を撮る","Imaging a retinal cross-section with light"),T("スペクトルから A スキャンを作り、B スキャンの層厚を画像だけから測る","Build A-scans from spectra and measure B-scan layer thickness from the image alone"),T("①問い → ②予想 → ③再生 → ④式 → ⑤限界。網膜と測定値はすべて合成。","Question, prediction, playback, formula, then limitations. Retina and measurements are entirely synthetic."),tabs,credit=T("すべて合成。実在の患者データ、装置の較正値、メーカー名、製品名、病院名を含まない。診断には使わない。","Entirely synthetic. No real patient data, instrument calibration, manufacturer, product, or hospital is included. Not for diagnosis."))


def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument("--check",action="store_true"); ap.add_argument("--out",default=str(OUT_HTML)); a=ap.parse_args(argv)
    r=compute(); g=r["g"]
    for k,v in g.items(): print("%-26s %s"%(k,v))
    spec=build_spec(r)
    html=pv._build_html(spec,list(LANGS))
    if len(html.encode("utf-8"))>600000: raise ValueError("page exceeds 600,000 bytes")
    if a.check: print("ok: %d bytes (not written)"%len(html.encode("utf-8"))); return 0
    path=pv.write_viewer(spec,a.out,list(LANGS)); print("wrote %s (%d bytes)"%(path,Path(path).stat().st_size)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
