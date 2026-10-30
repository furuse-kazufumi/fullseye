# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0.
"""Lighthouse inspection virtual factory shared simulation and honest evaluation.

Generators alone know truth.  Detectors accept only measured pixels/points; matching
against truth happens in :func:`score` after detector return.  Randomness is confined
to specimen generation and sensor noise.  The searched pipeline uses Fullseye's
``components`` op after a robust residual transform; the baseline is a fixed global
contrast rule.  This module deliberately adds no Fullseye op.
"""
from __future__ import annotations

import inspect
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

import fullseye as fs

TRAIN_SEEDS = tuple(range(110, 122))
HOLDOUT_SEEDS = tuple(range(910, 930))
KINDS = ("tyre", "wheel", "bevel", "smt")
WEF = {"tyre": 99.0, "wheel": 98.1, "bevel": 90.0, "smt": 99.0}
LABEL = {"tyre": "タイヤX線", "wheel": "鋳造ホイールX線", "bevel": "開先3D", "smt": "SMT AOI"}


@dataclass(frozen=True)
class Truth:
    defective: bool
    severe: bool
    center: tuple[float, float]
    difficulty: float
    defect_type: str
    size: float
    angle_error: float = 0.0
    root_error: float = 0.0


def _disk(shape, y, x, r):
    yy, xx = np.indices(shape)
    return (yy - y) ** 2 + (xx - x) ** 2 <= r * r


def tyre(seed: int):
    """Beer-Lambert rubber/steel radiograph with Poisson quanta and focal blur."""
    rng = np.random.default_rng(seed); n = 128; yy, xx = np.indices((n, n))
    rubber = 10 + 7 * np.sqrt(np.clip(1 - ((yy - 64) / 58) ** 2, 0, 1))
    mu_path = .055 * rubber
    for x in range(12, 121, 8):
        mu_path += .30 * np.exp(-((xx - x - 1.5 * np.sin(yy / 15)) ** 2) / 1.2)
    bad = rng.random() < .72; typ = rng.choice(("cord_waviness", "foreign", "bubble", "broken_cord"))
    cy, cx = int(rng.integers(26, 103)), int(rng.integers(25, 104)); size = float(rng.uniform(1.3, 6.2))
    contrast = float(rng.uniform(.025, .20))
    if bad:
        m = _disk((n, n), cy, cx, size)
        if typ in ("bubble", "broken_cord"): mu_path[m] -= contrast
        else: mu_path[m] += contrast
    photons = 8500 * np.exp(-mu_path)
    img = rng.poisson(np.maximum(photons, 1)).astype(float) / 8500
    img = ndi.gaussian_filter(img, .9)  # finite focal spot
    diff = float(np.clip(1 - contrast / .20 + .05 / max(size, 1), 0, 1))
    return img, Truth(bad, bad and size >= 4.5, (cy, cx), diff, str(typ), size)


def wheel(seed: int):
    """Cast aluminium radiograph; pores/shrinkage/inclusion in spoke-root ROI."""
    rng = np.random.default_rng(seed); n = 128; yy, xx = np.indices((n, n)); r = np.hypot(xx-64, yy-64)
    spoke = .15 * (np.cos(5*np.arctan2(yy-64, xx-64)) > .55) * ((r > 20) & (r < 57))
    thickness = 5 + 8*((r > 17) & (r < 59)) + spoke
    img = np.exp(-.075*thickness); bad = rng.random() < .64
    typ = str(rng.choice(("gas_pore", "shrinkage", "inclusion"))); a = float(rng.uniform(1.2, 6.8))
    ang = rng.uniform(-math.pi, math.pi); rad = rng.uniform(20, 55); cy = 64+rad*np.sin(ang); cx = 64+rad*np.cos(ang)
    amp = float(rng.uniform(.025, .18))
    if bad:
        m = _disk(img.shape, cy, cx, a)
        img[m] += amp if typ != "inclusion" else -amp
        if typ == "shrinkage": img += amp*.45*np.exp(-((xx-cx)**2/25+(yy-cy)**2/3))
    img = ndi.gaussian_filter(img, 1.0); img += rng.normal(0, .012, img.shape)
    root = 20 <= rad <= 34
    severe = bool(bad and (a >= 4.0 or (a >= 2.7 and root)))
    diff = float(np.clip(1-amp/.18+.04/a, 0, 1))
    return img, Truth(bad, severe, (cy, cx), diff, typ, a)


def smt(seed: int):
    """Three-ring AOI image with five common solder-joint defect modes."""
    rng = np.random.default_rng(seed); h, w = 96, 144; yy, xx = np.indices((h, w))
    board = .20+.035*np.sin(xx/13)+.02*np.cos(yy/11); img = np.dstack((board*.7, board, board*.65))
    pad = (abs(xx-72)<35)&(abs(yy-48)<13); img[pad] = (.68, .72, .76)
    bad = rng.random() < .68; typ = str(rng.choice(("bridge", "open", "shift", "void", "tombstone")))
    size = float(rng.uniform(2, 10)); amp = float(rng.uniform(.06, .38)); cy, cx = 48., 72.
    if bad:
        if typ == "bridge": m = (abs(xx-72)<size)&(abs(yy-48)<25)
        elif typ == "open": m = _disk((h,w), 48, 72, size)
        elif typ == "shift": m = (abs(xx-(72+size))<27)&(abs(yy-48)<10)
        elif typ == "void": m = _disk((h,w), 48, 72, size)
        else: m = (abs(xx-72)<29)&(abs(yy-(48-size))<8)
        img[m] += (-amp if typ in ("open", "void") else amp)*np.array((.8,.45,.2))
    img = ndi.gaussian_filter(img, (.8,.8,0)); img += rng.normal(0,.015,img.shape)
    gray = img @ np.array((.25,.6,.15)); diff=float(np.clip(1-amp/.38+.03/size,0,1))
    return gray, Truth(bad, bad and (size >= 6 or typ in ("bridge","tombstone")), (cy,cx), diff, typ, size)


def bevel(seed: int):
    """Metric plate bevel cloud with scanner noise, missing points and outliers."""
    rng=np.random.default_rng(seed); n=900; x=rng.uniform(-45,45,n); y=rng.uniform(-16,16,n)
    angle=35.0; root=2.0; z=np.where(abs(y)<8, (8-abs(y))*math.tan(math.radians(angle)), 0)
    true_rot=float(rng.normal(0,1.5)); true_shift=float(rng.normal(0,.7)); bad=rng.random()<.62
    angle_err=float(rng.uniform(-4.5,4.5)) if bad else float(rng.normal(0,.5)); root_err=float(rng.uniform(-1.0,1.0)) if bad else float(rng.normal(0,.1))
    z += np.where(abs(y)<8, (8-abs(y))*(math.tan(math.radians(angle+angle_err))-math.tan(math.radians(angle))), 0)
    keep=rng.random(n)>.10; pts=np.c_[x[keep]+true_shift,y[keep],z[keep]]; pts += rng.normal(0,.08,pts.shape)
    out=rng.uniform((-45,-16,-2),(45,16,8),(35,3)); pts=np.vstack((pts,out))
    truth=Truth(bad, bad and (abs(angle_err)>3 or abs(root_err)>.6),(48,72),min(1,abs(angle_err)/6+.2),"angle_or_root",abs(angle_err),angle_err,root_err)
    return pts, truth


GENERATORS={"tyre":tyre,"wheel":wheel,"bevel":bevel,"smt":smt}


def baseline_detector(measured: np.ndarray, kind: str, threshold: float=.16):
    """Fixed classical rule; accepts measured data only."""
    if kind == "bevel":
        p=measured[np.abs(measured[:,1])<7]; slope=np.polyfit(np.abs(p[:,1]),p[:,2],1)[0]
        angle=math.degrees(math.atan(abs(slope))); return {"hit": abs(angle-35)>2.8, "angle":angle, "root":2.0}
    a=np.asarray(measured,float); bg=ndi.gaussian_filter(a,5); residual=np.abs(a-bg); pos=np.unravel_index(np.argmax(residual),residual.shape)
    return {"hit":bool(residual[pos]>threshold),"center":tuple(map(float,pos)),"strength":float(residual[pos])}


def fullseye_detector(measured: np.ndarray, kind: str, threshold: float=.08, scale: float=3.0):
    """Robust Fullseye pipeline; no truth argument or stochastic decision."""
    if kind == "bevel":
        p=np.asarray(measured); core=p[(np.abs(p[:,1])<7)&(p[:,2]>-1)&(p[:,2]<8)]
        bins=np.linspace(-7,7,22); med=[]; ctr=[]
        for lo,hi in zip(bins[:-1],bins[1:]):
            q=core[(core[:,1]>=lo)&(core[:,1]<hi)]
            if len(q)>5: ctr.append(abs((lo+hi)/2)); med.append(np.median(q[:,2]))
        slope=np.polyfit(ctr,med,1)[0]; angle=math.degrees(math.atan(abs(slope)))
        return {"hit":abs(angle-35)>threshold,"angle":angle,"root":2.0}
    a=np.asarray(measured,float); bg=ndi.median_filter(a,size=max(3,int(scale)*2+1)); residual=np.abs(a-bg)
    # Fullseye supplies the deterministic linear intensity transform; scipy labels.
    lo,hi=float(residual.min()),float(residual.max())
    residual=np.asarray(fs.scale_y_funct_1d(residual.ravel(),1/(hi-lo+1e-12),-lo/(hi-lo+1e-12)),float).reshape(residual.shape)
    mad=np.median(np.abs(residual-np.median(residual)))+1e-9; mask=residual > threshold*mad
    labels,n=ndi.label(mask,structure=np.ones((3,3),int))
    if int(n)==0: return {"hit":False,"center":(-1.,-1.),"strength":0.}
    ids=np.arange(1,int(n)+1); weights=ndi.sum(residual,labels,ids); k=int(ids[int(np.argmax(weights))])
    cy,cx=ndi.center_of_mass(residual,labels,k)
    return {"hit":bool(weights.max()>threshold),"center":(float(cy),float(cx)),"strength":float(weights.max())}


def score(kind: str, seeds, detector, params):
    """Independent truth matching and metrics with Wilson 95% intervals."""
    rows=[]; t0=time.perf_counter()
    for seed in seeds:
        measured,truth=GENERATORS[kind](seed); out=detector(measured,kind,**params)
        loc=True if kind=="bevel" else np.hypot(*(np.subtract(out.get("center",(-99,-99)),truth.center))) <= max(8,2*truth.size)
        detected=bool(out["hit"] and loc); rows.append((truth,detected,out))
    elapsed=(time.perf_counter()-t0)*1000/len(rows); defects=[r for r in rows if r[0].defective]; good=[r for r in rows if not r[0].defective]; sev=[r for r in defects if r[0].severe]
    miss=sum(not r[1] for r in defects); fp=sum(r[1] for r in good); smiss=sum(not r[1] for r in sev)
    def rate_ci(k,n):
        if not n:return [0.,0.,0.]
        z=1.96; ph=k/n; den=1+z*z/n; c=(ph+z*z/(2*n))/den; d=z*math.sqrt(ph*(1-ph)/n+z*z/(4*n*n))/den
        return [100*ph,100*max(0,c-d),100*min(1,c+d)]
    out={"n":len(rows),"defects":len(defects),"miss_rate":rate_ci(miss,len(defects)),"false_positive_rate":rate_ci(fp,len(good)),"severe_miss_rate":rate_ci(smiss,len(sev)),"ms_per_part":elapsed}
    if kind=="bevel":
        errs=[abs(r[2]["angle"]-(35+r[0].angle_error)) for r in rows]; out["angle_mae_deg"]=[float(np.mean(errs)),float(np.quantile(errs,.025)),float(np.quantile(errs,.975))]; out["registration_mm"]=[float(np.std(errs)*.12),0.,float(np.quantile(errs,.975)*.12)]
        roots=[abs(r[2]["root"]-(2+r[0].root_error)) for r in rows]; out["root_face_mae_mm"]=[float(np.mean(roots)),float(np.quantile(roots,.025)),float(np.quantile(roots,.975))]
    out["difficulty"]=[{"lo":lo,"hi":hi,"detection_rate":100*np.mean([r[1] for r in defects if lo<=r[0].difficulty<(hi+1e-9)]) if any(lo<=r[0].difficulty<(hi+1e-9) for r in defects) else None} for lo,hi in ((0,.33),(.33,.66),(.66,1))]
    return out,rows


def tune(kind: str):
    grid=([.1,.5,1.,2.,4.,8.] if kind!="bevel" else [1.0,1.5,2.0,2.5]); best=None
    for th in grid:
        m,_=score(kind,TRAIN_SEEDS,fullseye_detector,{"threshold":th,"scale":3})
        objective=m["miss_rate"][0]+m["false_positive_rate"][0]
        if best is None or objective<best[0]: best=(objective,th,m)
    return best[1],best[2]


def audit_detector_boundary():
    """Fail if detector interfaces/source can consume generator truth."""
    for f in (baseline_detector,fullseye_detector):
        assert "truth" not in inspect.signature(f).parameters
        src=inspect.getsource(f)
        assert "GENERATORS" not in src and "Truth(" not in src
    return True


def run(kind: str, full: bool=False):
    audit_detector_boundary(); train=TRAIN_SEEDS if full else TRAIN_SEEDS[:8]; hold=HOLDOUT_SEEDS if full else HOLDOUT_SEEDS[:12]
    threshold,train_metric=tune(kind); base_train,_=score(kind,train,baseline_detector,{"threshold":.13 if kind!="bevel" else 2.8})
    ours_train,_=score(kind,train,fullseye_detector,{"threshold":threshold,"scale":3}); base_hold,base_rows=score(kind,hold,baseline_detector,{"threshold":.13 if kind!="bevel" else 2.8}); ours_hold,ours_rows=score(kind,hold,fullseye_detector,{"threshold":threshold,"scale":3})
    b=base_hold["miss_rate"][0]; o=ours_hold["miss_rate"][0]; reduction=100*(b-o)/b if b else None
    return {"kind":kind,"model":LABEL[kind],"seeds":{"train":list(train),"holdout":list(hold)},"defect_model":DEFECT_TABLE[kind],"baseline":"固定全体コントラスト閾値" if kind!="bevel" else "外れ値除去なし最小二乗、角度閾値2.8°","pipeline":"median residual → Fullseye scale_y_funct_1d → MAD → components" if kind!="bevel" else "ROI・外れ値除去 → robust profile fit","selected_threshold":threshold,"train_search_metric":train_metric,"train":{"baseline":base_train,"ours":ours_train},"holdout":{"baseline":base_hold,"ours":ours_hold},"miss_reduction_percent":reduction,"wef_reported_reduction_percent":WEF[kind],"comparison_warning":"WEFは各実工場の導入前との比較。本仮想工場の同一真値比較とは前提が異なり、勝敗を示さない。","loss_condition":"高難度(小寸法・低コントラスト・境界/欠測)では基準を下回る場合がある。difficulty曲線を参照。","_rows":(base_rows,ours_rows)}


DEFECT_TABLE={
 "tyre":{"types":["コード乱れ","異物","気泡","コード切れ"],"size":"半径1.3–6.2 px","prevalence":"72%","basis":"Beer–Lambert、8500光子、焦点ぼけσ=0.9 px。寸法・率は公開性能値ではなく感度試験の設計範囲。"},
 "wheel":{"types":["ガス気孔","引け巣","介在物"],"size":"半径1.2–6.8 px","prevalence":"64%","basis":"重大=半径4 px以上、またはスポーク根元で2.7 px以上。応力集中部を厳しくする工学的スクリーニング規則（規格の合否値ではない）。"},
 "bevel":{"types":["開先角外れ","ルート面外れ"],"size":"角度±4.5°、ルート±1.0 mm","prevalence":"62%","basis":"実寸mm、点雑音σ=0.08 mm、欠測10%、外れ値35点。範囲は位置合わせ感度試験の設計値。"},
 "smt":{"types":["ブリッジ","未はんだ","ずれ","ボイド","トゥームストーン"],"size":"2–10 px","prevalence":"68%","basis":"3色リングAOIの簡略反射像。種類はIPC-A-610で一般に検査される状態、寸法・率は感度試験の設計値。"}}


def save_result(kind: str, result: dict, out: Path):
    out.mkdir(parents=True,exist_ok=True); clean={k:v for k,v in result.items() if k!="_rows"}
    (out/"results.json").write_text(json.dumps(clean,ensure_ascii=False,indent=2),encoding="utf-8")
