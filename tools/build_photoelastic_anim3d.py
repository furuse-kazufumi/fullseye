#!/usr/bin/env python3
"""Photoelastic Brazilian-disc lesson for ViEW 2026."""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import photoelastic as pe  # noqa: E402
import pocviewer as pv  # noqa: E402

T = pv.viewer_text
OUT_HTML = ROOT / "docs" / "view2026" / "anim3d" / "photoelastic_anim3d.html"
LANGS = ("ja", "en")
RADIUS, THICKNESS, COEFF = 0.025, 0.006, 5.0e-11
WAVELENGTHS_NM = np.array([450.0, 532.0, 633.0])
LOADS = (240.0, 480.0, 720.0)
READ_NOISE = 0.01
FULL_WELL = 10_000
ADC_LEVELS = 256


def _disc(n=48):
    """Deterministic two-faced disc mesh; no triangulator."""
    a = np.arange(n) * 2 * np.pi / n
    rim0 = np.c_[RADIUS * np.cos(a), RADIUS * np.sin(a), np.full(n, -THICKNESS / 2)]
    rim1 = rim0.copy(); rim1[:, 2] *= -1
    v = np.vstack([rim0, rim1, [[0, 0, -THICKNESS / 2], [0, 0, THICKNESS / 2]]])
    f = []
    for i in range(n):
        j = (i + 1) % n
        f.extend([[i, j, n + j], [i, n + j, n + i], [2*n, j, i], [2*n+1, n+i, n+j]])
    return v * 115.0, np.asarray(f, int)


def _plate(x, z, w=.85, h=2.2):
    v = np.array([[x, -w, z-h], [x, w, z-h], [x, w, z+h], [x, -w, z+h]], float)
    return v, np.array([[0, 1, 2], [0, 2, 3]], int)


def _motion(frames, bodies):
    xyz = np.zeros((frames, bodies, 3)); q = np.zeros((frames, bodies, 4)); q[..., 0] = 1
    return xyz, q


def _e(x):
    return "< 1e-12" if abs(float(x)) < 1e-12 else "%.4g" % float(x)


def _quantized_camera(ideal, rng):
    """Shot noise at a 10k-electron full well + 1% read noise + 8-bit ADC."""
    shot=rng.poisson(np.clip(ideal,0,1)*FULL_WELL)/FULL_WELL
    noisy=np.clip(shot+rng.normal(0,READ_NOISE,np.shape(ideal)),0,1)
    return np.rint(noisy*(ADC_LEVELS-1))/(ADC_LEVELS-1)


def _field(load_n, size):
    """Stress on an offset sensor grid; the physical centre is not a pixel centre."""
    step=2*RADIUS/(size-5); cx=(size-1)/2+.37; cy=(size-1)/2-.29
    yy,xx=np.mgrid[:size,:size]; xm=(xx-cx)*step; ym=(yy-cy)*step
    inside=xm*xm+ym*ym < (.995*RADIUS)**2
    g={k:np.zeros((size,size),float) for k in ("sxx","syy","txy")}
    d=pe.brazilian_disc_stress(RADIUS,THICKNESS,load_n,x=xm[inside],y=ym[inside])
    for k in g: g[k][inside]=d[k]
    p=pe.principal_stress(g["sxx"],g["syy"],g["txy"])
    return g,p,inside,xm,ym,cx,cy


def _spatial_order(mono, inside, xm, cy, closed_order):
    """Unwrap N(x) from one horizontal image profile and locate dark lines quadratically."""
    row=int(round(cy)); profile=np.mean(mono[row-1:row+2],axis=0)
    valid=np.where(inside[row])[0]; left=valid[valid < np.mean(valid)]
    # Work from the rim toward the centre. A short moving average suppresses one-pixel ADC/read-noise extrema.
    z=np.convolve(profile[left],np.ones(3)/3,mode="same")[1:-1]; cols=left[1:-1]
    scale=max(float(np.percentile(z,98)),.2); z=np.clip(z/scale,0,1)
    minima=[]
    for i in range(1,len(z)-1):
        if z[i]<z[i-1] and z[i]<=z[i+1] and z[i]<.25 and (not minima or cols[i]-minima[-1]>4):
            den=z[i-1]-2*z[i]+z[i+1]
            off=0.5*(z[i-1]-z[i+1])/den if abs(den)>1e-12 else 0.0
            minima.append(float(cols[i]+np.clip(off,-.5,.5)))
    centre_level=float(np.mean(z[-3:])); frac=float(np.arcsin(np.sqrt(np.clip(centre_level,0,1)))/np.pi)
    rising=float(np.mean(z[-3:])-np.mean(z[-8:-5])) >= 0
    centre_order=len(minima)+(frac if rising else 1-frac)
    # N(x) is built only from the observed dark-line positions (integer orders), rim, and observed centre intensity.
    ax=np.array([cols[0],*minima,cols[-1]],float)
    ay=np.array([0,*range(1,len(minima)+1),centre_order],float)
    order=np.interp(cols,ax,ay)
    truth=np.interp(xm[row,cols],xm[row],closed_order[row])
    rmse=float(np.sqrt(np.mean((order-truth)**2)))
    return {"profile":profile,"cols":cols,"order":order,"truth":truth,"rmse":rmse,
            "minima":minima,"centre_order":centre_order}


def observe(load_n: float, size=129, seed=0):
    """Create noisy camera frames, then estimate stress without passing load or true stress to either estimator."""
    g,p,inside,xm,ym,cx,cy=_field(load_n,size)
    rng = np.random.default_rng(1200 + seed)
    phase, six = [], None
    for wi, lam_nm in enumerate(WAVELENGTHS_NM):
        ret = pe.photoelastic_retardation(p["difference"], THICKNESS, COEFF, lam_nm * 1e-9)
        raw = pe.photoelastic_polarization_images(ret["delta_rad"], p["angle_deg"] + 90.0, "stokes6")
        yy, xx = np.mgrid[:size, :size]
        illumination = 0.91 + 0.08 * xx / (size - 1) + 0.03 * yy / (size - 1)
        noisy = _quantized_camera(raw * illumination, rng)
        est = pe.photoelastic_phase_estimate(noisy, "stokes6", sum_tolerance=.08)
        phase.append(est["delta_rad"])
        if wi == 1:
            six = noisy
    unwrap = pe.retardation_unwrap_multiwavelength(phase, WAVELENGTHS_NM.tolist(), 4200.0)
    stress = unwrap["retardation_nm"] * 1e-9 / (THICKNESS * COEFF)
    c0=int(round(cy)); c1=int(round(cx)); centre_stress=float(np.nanmedian(stress[c0-2:c0+3,c1-2:c1+3]))
    ret532=pe.photoelastic_retardation(p["difference"],THICKNESS,COEFF,532e-9)
    mono_ideal=pe.polariscope_intensity(ret532["delta_rad"],setup="circular_dark")*illumination
    mono=_quantized_camera(mono_ideal,rng); mono[~inside]=0
    spatial=_spatial_order(mono,inside,xm,cy,ret532["fringe_order"])
    fringe_stress=spatial["centre_order"]*532e-9/(THICKNESS*COEFF)
    return {"grid": g, "principal": p, "camera": six, "stress": stress,
            "centre_stress": centre_stress, "fringe_stress": fringe_stress,
            "dark_count":len(spatial["minima"]),"spatial":spatial,"mono":mono,"valid":unwrap["valid"]}


def measurements():
    rows = []
    factor = 8.0 / (math.pi * (2 * RADIUS) * THICKNESS)
    for i, load in enumerate(LOADS):
        o = observe(load, seed=i)
        closed = factor * load
        inferred = o["centre_stress"] / factor
        fringe_load=o["fringe_stress"]/factor
        rows.append({"load": load, "closed_stress": closed, "phase_stress": o["centre_stress"],
                     "inferred_load": inferred, "load_error_pct": abs(inferred-load)/load*100,
                     "fringe_load":fringe_load,"fringe_error_pct":abs(fringe_load-load)/load*100,
                     "fringe_stress": o["fringe_stress"], "dark_count": o["dark_count"],"order_rmse":o["spatial"]["rmse"],
                     "route_difference_pct": abs(o["fringe_stress"]-o["centre_stress"])/o["centre_stress"]*100})
    return rows


def fringe_frames(load_values, size=57):
    """White-light RGB camera sequence computed from three wavelengths, with seeded sensor noise."""
    rng=np.random.default_rng(20261027); out=[]
    yy,xx=np.mgrid[:size,:size]; illum=.90+.08*xx/(size-1)+.03*yy/(size-1)
    for load in load_values:
        g=pe.brazilian_disc_stress(RADIUS,THICKNESS,max(float(load),1e-3),size=size)
        p=pe.principal_stress(g["sxx"],g["syy"],g["txy"])
        channels=[]
        for lam in (633.0,532.0,450.0):
            ret=pe.photoelastic_retardation(p["difference"],THICKNESS,COEFF,lam*1e-9)
            im=pe.polariscope_intensity(ret["delta_rad"],setup="circular_dark")
            channels.append(im)
        rgb=np.stack(channels,-1)*illum[...,None]
        rgb+=rng.normal(0,.006,rgb.shape); rgb[~g["inside"]]=.018
        out.append(np.uint8(np.clip(rgb,0,1)*255))
    return out


def _lesson(qj, qe, choices, answer, ej, ee, formula, lj, le):
    return {"question": T(qj, qe), "choices": [T(*x) for x in choices], "answer": answer,
            "explain": T(ej, ee), "formula": formula, "limit": T(lj, le)}


def build_spec():
    rows = measurements(); frames = 49; time = np.arange(frames) / 12.0
    load_values=np.linspace(0,720,frames); pane=fringe_frames(load_values)
    disc_v, disc_f = _disc(); bodies = [{"name":"disc", "pos":disc_v, "faces":disc_f, "rgb":[105,185,220], "alpha":.64}]
    # Optical train: polarizer, quarter-wave plate, specimen, quarter-wave plate, analyzer, camera.
    labels = [("polarizer", -5.0, [235,190,70]), ("quarter1", -3.3, [180,110,220]),
              ("quarter2", 3.3, [180,110,220]), ("analyzer", 5.0, [235,190,70]), ("camera", 6.7, [80,170,110])]
    for name, x, rgb in labels:
        v, f = _plate(x, 0)
        bodies.append({"name":name, "pos":v, "faces":f, "rgb":rgb, "alpha":.48})
    xyz, q = _motion(frames, len(bodies)); xyz[:, 0, 0] = 0
    common_axis = {"values":np.linspace(0, 720, frames), "segments":[{"k":0,"label":T("荷重", "Load"),"unit":" N","decimals":0}]}
    phase_max=max(r["load_error_pct"] for r in rows)
    checks1 = [{"what":T("6 強度と 3 波長から推定した荷重", "Load estimated from six intensities and three wavelengths"),
                "criterion":T("3 荷重で誤差 < 2 %（1 % 読出し雑音とショット雑音を 5×5 画素で低減）", "error < 2% at three loads (1% read noise and shot noise reduced over 5×5 pixels)"),
                "result":T("最大 %.2f %%（3 条件）" % phase_max, "maximum %.2f%% (3 conditions)" % phase_max),
                "ok":phase_max < 2}]
    tabs = [pv.viewer_anim3d_tab("why", T("なぜ色の縞になる？", "Why colored fringes?"), "passed",
        T("偏光子と 1/4 波長板を通った光は、応力で生じた二つの屈折率の差を明暗へ変える。像は満杯 10,000 電子のショット雑音、最大強度の 1 % の読出し雑音、8 bit 量子化を含む。", "Polarizers and quarter-wave plates turn stress-induced birefringence into brightness. Images include shot noise at a 10,000-electron full well, 1% read noise, and 8-bit quantization."),
        time, bodies, xyz, q, checks=checks1, axis=common_axis,
        panes=[{"label":T("応力場から計算した白色光の縞", "White-light fringes computed from the stress field"),"frames":pane,"png":True,"wide":True}],
        lesson=_lesson("透明な円板に力を加えると何が変わる？", "What changes when a transparent disc is loaded?",
          [("厚さだけ", "Only thickness"), ("偏光の位相差", "Polarization phase delay")], 1,
          "主応力差が位相差を作る。", "Principal-stress difference creates phase delay.",
          T("N = t(σ₁−σ₂)/fσ,  I = sin²(πN)", "N = t(σ₁−σ₂)/fσ,  I = sin²(πN)"),
          "材料定数と厚さは一様と仮定する。", "Material coefficient and thickness are assumed uniform."), view={"az":-22,"el":15,"dist":1.25})]
    # Three load states move press blocks toward the disc; calculated rows drive the badge.
    press_v, press_f = _plate(0, 0, 2.6, .35)
    pb = [{"name":"disc", "pos":disc_v, "faces":disc_f, "rgb":[80,150,220], "alpha":.72},
          {"name":"top_press", "pos":press_v, "faces":press_f, "rgb":[230,105,80]},
          {"name":"bottom_press", "pos":press_v, "faces":press_f, "rgb":[230,105,80]}]
    px, pq = _motion(frames, 3); amount=np.linspace(0,1,frames); px[:,1,2]=3.55-.65*amount; px[:,2,2]=-3.55+.65*amount
    tabs.append(pv.viewer_anim3d_tab("load", T("荷重と縞", "Load and fringes"), "passed",
        T("押す力を 4 倍にすると、中心を通過する暗線の数が増える。", "Quadrupling the force increases the dark fringes crossing the centre."),
        time,pb,px,pq,panes=[{"label":T("荷重とともに増える色の縞", "Colored fringes increasing with load"),"frames":pane,"png":True,"wide":True}],checks=[{"what":T("中心を通る暗線", "Dark lines crossing the centre"),"criterion":T("荷重とともに増加", "increase with load"),
          "result":" → ".join(str(r["dark_count"]) for r in rows),"ok":all(rows[i]["dark_count"] <= rows[i+1]["dark_count"] for i in range(len(rows)-1))}],axis=common_axis,
        lesson=_lesson("荷重を上げると縞は？", "What happens to fringes as load rises?",[("減る", "Fewer"),("増える", "More")],1,
          "位相差が何周も進むため暗線が増える。", "More phase cycles produce more dark lines.", T("I = sin²(πN)", "I = sin²(πN)"),
          "高い次数では縞が詰まり、画素で分離できない。", "At high order, fringes crowd beyond pixel resolution."),view={"az":-30,"el":12,"dist":1.15}))
    route_max=max(r["route_difference_pct"] for r in rows); order_max=max(r["order_rmse"] for r in rows)
    table=" / ".join("%.0f N: %.1f / %.1f N"%(r["load"],r["fringe_load"],r["inferred_load"]) for r in rows)
    tabs.append(pv.viewer_anim3d_tab("inverse",T("縞から力を逆算", "Infer force from fringes"),"passed",
        T("暗線の数え上げと、6 強度・3 波長の位相推定を別々に行い、中心の主応力差を比べる。", "Independent fringe counting and six-intensity, three-wavelength phase recovery estimate central stress difference."),
        time,pb,px,pq,panes=[{"label":T("逆算に使う雑音入り偏光像", "Noisy polarized image used for inversion"),"frames":pane,"png":True,"wide":True}],checks=[
          {"what":T("水平直径の像から作った縞次数 N(x)", "Fringe order N(x) built from the image diameter"),"criterion":T("閉形式との RMS 差 < 0.10 次", "RMS difference from closed form < 0.10 order"),"result":T("最大 %.3f 次"%order_max,"maximum %.3f order"%order_max),"ok":order_max<.10},
          {"what":T("暗線像 / 6 強度多波長の荷重推定", "Load estimates: dark-fringe image / six-intensity multiwavelength"),"criterion":T("独立経路の差 < 4 %（各経路 2 % と 3 % の二乗和平方根）", "route difference < 4% (root-sum-square of 2% and 3% route budgets)"),
          "result":table,"ok":route_max<4}, *checks1],axis=common_axis,
        lesson=_lesson("像だけから荷重を戻せる？", "Can load be recovered from images alone?",[("戻せない", "Cannot recover"),("材料定数が分かれば戻せる", "Yes, with material data")],1,
          "中心応力差を像から求め、円板の関係式で荷重へ戻す。", "Recover central stress from images, then use the disc relation for force.",
          T("P = πDt(σ₁−σ₂)/8", "P = πDt(σ₁−σ₂)/8"), "残留応力は荷重による応力と区別できない。", "Residual stress cannot be separated from load stress."),view={"az":-30,"el":12,"dist":1.15}))
    tabs.append(pv.viewer_anim3d_tab("limits",T("見えない限界", "Limits of visibility"),"limit",
        T("縞が画素より細い領域、残留応力、厚さむらは、この単純な逆算では分けられない。", "Subpixel fringes, residual stress, and thickness variation cannot be separated by this simple inversion."),
        time,pb,px,pq,checks=[{"what":T("高次・残留応力・厚さむら", "High order, residual stress, thickness variation"),
          "criterion":T("荷重だけの応力を一意に分離", "uniquely isolate load stress"),"result":T("像だけでは分離不能", "not separable from images alone"),"ok":False}],axis=common_axis,
        lesson=_lesson("縞が細かすぎると次数を数えられる？", "Can order be counted when fringes are too fine?",[("数えられる", "Yes"),("数えられない", "No")],1,
          "画素内で明暗が混ざると次数を失う。", "Brightness averages within a pixel and order is lost.",T("Δxfringe < pixel", "Δxfringe < pixel"),
          "この合成モデルは校正の考え方を示すもので、実材料の検査条件を保証しない。", "This synthetic model illustrates calibration; it does not certify a real inspection."),view={"az":-30,"el":12,"dist":1.15}))
    return pv.viewer_spec("photoelastic",T("力を色の縞として見る", "See force as colored fringes"),
        T("透明な円板の応力を偏光像から測る", "Measure stress in a transparent disc from polarized images"),
        T("ドラッグで回し、荷重つまみを動かす", "Drag to rotate and move the load slider"),tabs,
        credit=T("合成データ。材料定数は説明用の仮定。", "Synthetic data; material constants are illustrative assumptions."))


def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument("--out",type=Path,default=OUT_HTML); ap.add_argument("--check",action="store_true"); a=ap.parse_args(argv)
    for r in measurements(): print("CHECK load=%.0fN phase=%.2fN (%.3f%%) spatial=%.2fN (%.3f%%) N_rmse=%.4f route_difference=%.3f%%"%(r["load"],r["inferred_load"],r["load_error_pct"],r["fringe_load"],r["fringe_error_pct"],r["order_rmse"],r["route_difference_pct"]))
    spec=build_spec()
    if a.check: pv._build_html(spec,list(LANGS))
    else: pv.write_viewer(spec,str(a.out),list(LANGS))
    return 0


if __name__ == "__main__": raise SystemExit(main())
