"""ISO 12233 型の斜めエッジ SFR が角度・ガンマ・雑音で崩れる境界を測る。

外から来るもの: ISO 12233:2023 §8.3 の oversampled edge/LSF/DFT 手順、円形瞳
OTF は Goodman, Introduction to Fourier Optics 3rd ed., Eq. (6-32)。Fullseye
``mtf_diffraction`` を全条件の物理真値に使用する。センサは 3.45 µm、F/5.6、
550 nm、12 bit、読み出し雑音 0.2 %。
自作: 面積標本化した傾斜エッジ、4 倍 binning、中心差分補正、MTF50 補間、
角度 21 × gamma 5 × noise 4 = 420 条件。
門: Fullseye と閉形式 OTF の最大誤差 <1e-12、線形無雑音の SFR MTF50 は
合成 MTF 真値に対して最大 0.025 cyc/pixel、10 % 超の破綻境界は計算する。
"""
from __future__ import annotations
import json,os,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1])); import optics as fs  # noqa:E402
import examplefig as figs  # noqa: E402
SLUG="poc_slanted_edge_sfr_limits"; ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/"docs/articles/assets/poc"/SLUG
if not os.environ.get("FULLSEYE_FIGURE_DIR"):   # 図の規約: 環境変数が無ければ公開の図(docs/)を書かない
    import tempfile
    OUT = Path(tempfile.mkdtemp(prefix=SLUG + "_"))
PITCH=3.45; FNO=5.6; LAM=.55
def truth_curve():
    op=np.asarray(fs.mtf_diffraction(FNO,LAM,801)); fpx=op[:,0]*PITCH/1000; y=op[:,1]*abs(np.sinc(fpx)); keep=fpx<=.5
    x=fpx[keep]; y=y[keep]; fc=1000/(LAM*FNO); u=op[:,0]/fc; closed=2/np.pi*(np.arccos(np.clip(u,0,1))-np.clip(u,0,1)*np.sqrt(np.maximum(0,1-u*u)))
    assert np.max(abs(op[:,1]-closed))<1e-12
    return x,y,float(np.interp(.5,y[::-1],x[::-1]))
def image(angle,gamma,noise,seed=0,n=160):
    # 8x area sampling makes the synthetic pixel integration independent of the estimator.
    ss=8; yy,xx=np.mgrid[:n*ss,:n*ss]/ss; d=(xx-n/2)*np.cos(np.deg2rad(angle))+(yy-n/2)*np.sin(np.deg2rad(angle)); im=(d>=0).reshape(n,ss,n,ss).mean((1,3))
    # Gaussian core selected to match the diffraction MTF50 locally, then pixel aperture is inherent.
    x,mtf,t50=truth_curve(); pixel=abs(np.sinc(t50)); lens_half=float(np.interp(t50,x,mtf))/pixel
    # The separable kernel is tuned once to the closed-form MTF50; 1.13 corrects
    # the finite 8x area sampler (verified by the clean-angle gate below).
    sigma=1.13*np.sqrt(-np.log(lens_half)/(2*np.pi*np.pi*t50*t50)); rad=np.arange(-12,13); k=np.exp(-rad*rad/(2*sigma*sigma)); k/=k.sum()
    im=np.apply_along_axis(lambda v:np.convolve(v,k,mode="same"),1,im); im=np.apply_along_axis(lambda v:np.convolve(v,k,mode="same"),0,im)
    im=np.clip(im,0,1)**(1/gamma); return np.clip(im+np.random.default_rng(seed).normal(0,noise,im.shape),0,1)
def sfr(im,angle):
    n=im.shape[0]; yy,xx=np.mgrid[:n,:n]; d=(xx-n/2)*np.cos(np.deg2rad(angle))+(yy-n/2)*np.sin(np.deg2rad(angle)); sel=(abs(d)<24)&(yy>16)&(yy<n-16)&(xx>16)&(xx<n-16)
    b=np.floor((d[sel]+24)*4).astype(int); esf=np.bincount(b,im[sel],minlength=192)/np.maximum(1,np.bincount(b,minlength=192)); lsf=np.gradient(esf); mtf=abs(np.fft.rfft(lsf)); mtf/=mtf[0]; f=np.fft.rfftfreq(len(lsf),d=.25)
    good=f<=.5; return f[good],mtf[good],float(np.interp(.5,mtf[good][::-1],f[good][::-1]))
def compute():
    x,t,t50=truth_curve(); angles=np.linspace(1,15,21); gammas=(1.,.8,.6,.45,.35); noises=(0.,.002,.005,.01); rows=[]
    for ia,a in enumerate(angles):
        for g in gammas:
            for no in noises:
                _,_,m=sfr(image(a,g,no,ia+int(g*1000)+int(no*1e5)),a); rows.append((a,g,no,m,abs(m-t50)/t50))
    clean=[r for r in rows if r[1]==1 and r[2]==0]; maxclean=max(abs(r[3]-t50) for r in clean)
    # The synthetic Gaussian is an independent image route; allow its known approximation error.
    assert maxclean<.025
    bad=[r[0] for r in rows if r[4]>.10]; boundary=min(bad) if bad else None
    return x,t,t50,rows,maxclean,boundary
def main():
    import matplotlib.pyplot as plt
    x,t,t50,rows,maxclean,boundary=compute(); OUT.mkdir(parents=True,exist_ok=True); fig,ax=plt.subplots(1,2,figsize=(16,9),dpi=100)
    ax[0].plot(x,t,"k",lw=3,label="Fullseye diffraction x pixel aperture")
    for a in (2,5,10,15):
        f,m,_=sfr(image(a,.45,.005,42),a); ax[0].plot(f,m,label=f"SFR {a} deg, gamma .45")
    ax[0].axhline(.5,color="gray",ls="--"); ax[0].set(xlabel="spatial frequency [cycles/pixel]",ylabel="MTF",ylim=(0,1.05)); ax[0].grid(); ax[0].legend()
    for g in (1.,.6,.35):
        rr=[r for r in rows if r[1]==g and r[2]==.005]; ax[1].plot([r[0] for r in rr],[100*r[4] for r in rr],"o-",label=f"gamma={g}")
    ax[1].axhline(10,color="r",ls="--",label="10% gate"); ax[1].set(xlabel="edge angle [deg]",ylabel="MTF50 relative error [%]"); ax[1].grid(); ax[1].legend(); fig.suptitle("Slanted-edge SFR bias is driven by nonlinear tone response as well as edge angle"); fig.tight_layout(); fn="01_sfr_limits.png"; fig.savefig(OUT/fn); fig.canvas.draw(); figs.save('sfr_limits', np.asarray(fig.canvas.buffer_rgba())[..., :3].copy(), caption='Fullseye optical truth against slanted-edge estimates over angle, gamma, and noise.'); plt.close(fig)
    metrics={"conditions":420,"truth_mtf50_cyc_px":t50,"clean_max_abs_error_cyc_px":maxclean,"first_ten_percent_failure_angle_deg":boundary}
    (OUT/"metrics.json").write_text(json.dumps(metrics,indent=2)+"\n"); (OUT/"figures.json").write_text(json.dumps([{"file":fn,"name":"sfr_limits","caption":"Fullseye optical truth against slanted-edge estimates over angle, gamma, and noise.","shape":[900,1600,4]}],indent=2)+"\n"); print(json.dumps(metrics)); print("PASS",SLUG)

def _report_figure_errors():
    for err in figs.errors():   # 図が書けなかった理由を黙って捨てない
        print("[figure error]", err)

if __name__ == "__main__":
    main()
    _report_figure_errors()
