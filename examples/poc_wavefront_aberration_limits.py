"""波面収差別に Maréchal 近似の破綻を測る PoC。

外から来るもの: Mahajan, JOSA 73(6), 1983, Eq. (5) の Maréchal 近似
``S=exp[-(2*pi*sigma)^2]``、Born & Wolf 7th ed. §9.1 Eq. (8) の軸上
強度 ``S=|<exp(i*2*pi*W)>|^2``。Fullseye ``optics.pupil_psf``。
自作: Noll 正規化 Zernike (RMS=係数 [waves]) の直接瞳平均、収差別の
121 点掃引、PSF 像。門: Fullseye FFT と直接瞳平均の最大絶対誤差 < 0.015、
近似の 5 % 破綻点を全曲線から計算し、手書きしない。
"""
from __future__ import annotations

import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import optics as fs  # noqa: E402

SLUG = "poc_wavefront_aberration_limits"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/articles/assets/poc" / SLUG

def zernikes(n=192):
    q=(np.arange(n)+.5)*2/n-1; x,y=np.meshgrid(q,q); r=np.hypot(x,y); t=np.arctan2(y,x); m=r<=1
    # Noll normalization: each has unit RMS on the continuous unit disk.
    return m, {"defocus":np.sqrt(3)*(2*r*r-1),
               "astigmatism":np.sqrt(6)*r*r*np.cos(2*t),
               "coma":np.sqrt(8)*(3*r**3-2*r)*np.cos(t),
               "spherical":np.sqrt(5)*(6*r**4-6*r*r+1)}

def compute():
    pupil,zs=zernikes(); sig=np.linspace(0,.35,121); exact={}; fft={}
    base=fs.pupil_psf(pupil.astype(float), oversample=2); c=base.shape[0]//2; peak0=base[c,c]
    for name,z in zs.items():
        exact[name]=np.array([abs(np.mean(np.exp(2j*np.pi*s*z[pupil])))**2 for s in sig])
        # Fullseye is used through the sweep, not at endpoints.
        fft[name]=np.array([fs.pupil_psf(pupil.astype(float),opd_waves=s*z,oversample=2)[c,c]/peak0 for s in sig])
    marechal=np.exp(-(2*np.pi*sig)**2)
    maxerr=max(float(np.max(abs(fft[k]-exact[k]))) for k in zs)
    boundaries={k:float(sig[np.flatnonzero(abs(v-marechal)/v>.05)[0]]) for k,v in exact.items()}
    assert maxerr < .015
    return pupil,zs,sig,exact,fft,marechal,maxerr,boundaries

def main():
    import matplotlib.pyplot as plt
    pupil,zs,sig,exact,fft,marechal,maxerr,bounds=compute(); OUT.mkdir(parents=True,exist_ok=True)
    fig=plt.figure(figsize=(16,9),dpi=100); gs=fig.add_gridspec(2,4,height_ratios=[1.25,1])
    ax=fig.add_subplot(gs[0,:]); ax.plot(sig,marechal,"k--",lw=2,label="Marechal approximation")
    for name,v in exact.items(): ax.plot(sig,v,lw=2,label=f"{name}: pupil integral"); ax.plot(sig,fft[name],".",ms=2,alpha=.45)
    ax.set(xlabel="Zernike RMS [waves]",ylabel="Strehl ratio",ylim=(0,1.03)); ax.grid(); ax.legend(ncol=3)
    for a,(name,z) in zip([fig.add_subplot(gs[1,i]) for i in range(4)],zs.items()):
        ps=fs.pupil_psf(pupil.astype(float),opd_waves=.20*z,oversample=4); c=ps.shape[0]//2; a.imshow(np.log10(ps[c-35:c+36,c-35:c+36]+1e-9),cmap="magma",vmin=-8); a.set_title(f"{name}, 0.20 waves RMS"); a.set_xlabel("image x [samples]"); a.set_ylabel("image y [samples]")
    fig.suptitle("Aberration shape, not RMS alone, controls Marechal breakdown"); fig.tight_layout(); fn="01_aberration_limits.png"; fig.savefig(OUT/fn); plt.close(fig)
    metrics={"fft_vs_pupil_max_abs_error":maxerr,"five_percent_boundary_rms_waves":bounds,"conditions":484}
    (OUT/"metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")
    (OUT/"figures.json").write_text(json.dumps([{"file":fn,"name":"aberration_limits","caption":"Four unit-RMS Noll Zernike modes: exact pupil integral, Fullseye FFT, Marechal approximation, and computed PSFs.","shape":[900,1600,4]}],indent=2)+"\n",encoding="utf-8")
    print(json.dumps(metrics)); print("PASS",SLUG)
if __name__ == "__main__": main()
