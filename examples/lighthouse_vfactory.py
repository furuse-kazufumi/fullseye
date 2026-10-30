# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0.
"""Lighthouse inspection virtual factory shared simulation and honest evaluation.

Generators alone know truth.  Detectors accept only measured pixels/points; matching
against truth happens in :func:`score` after detector return.  Randomness is confined
to specimen generation and sensor noise.  The searched pipeline uses Fullseye's
``varmodel_fit`` / ``varmodel_score`` variation model, Fullseye registration and
morphology ops.  The baseline receives the identical good-image stack and uses the
industrial golden-template recipe: mean image, normalized cross-correlation
registration, residual, and a fixed threshold.  This module deliberately adds no op.
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
from scipy.stats import binomtest

import fullseye as fs

TRAIN_SEEDS = tuple(range(10_000, 10_240))
HOLDOUT_SEEDS = tuple(range(20_000, 20_800))
QUICK_TRAIN_SEEDS = TRAIN_SEEDS[:48]
QUICK_HOLDOUT_SEEDS = HOLDOUT_SEEDS[:96]
SEARCH_BUDGET = 12
KINDS = ("tyre", "wheel", "bevel", "smt")
WEF = {"tyre": 99.0, "wheel": 98.1, "bevel": 90.0, "smt": 99.0}
LABEL = {"tyre": "タイヤX線", "wheel": "鋳造ホイールX線", "bevel": "開先3D", "smt": "SMT AOI"}
DECLARED_FAR = 1e-3
FULLSEYE_OPS = ("varmodel_alignment", "varmodel_fit", "varmodel_score", "gclose", "ransac_plane", "fit_plane3")
_OP_CALLS: list[str] = []


def _op(name, *args, **kwargs):
    """Call and audit a public Fullseye op used by the proposed pipeline."""
    _OP_CALLS.append(name)
    if name in ("gclose", "gopen"):
        return fs.apply(args[0], name, *args[1:], **kwargs)
    return getattr(fs.ledger, name)(*args, **kwargs)


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


def tyre(seed: int, variation: float = 1.0):
    """Beer-Lambert rubber/steel radiograph with Poisson quanta and focal blur."""
    rng = np.random.default_rng(seed); n = 128; yy, xx = np.indices((n, n))
    shift=rng.normal(0,1.0*variation); pitch=8+rng.normal(0,.22*variation)
    rubber = 10+rng.normal(0,.35*variation) + 7 * np.sqrt(np.clip(1 - ((yy - 64) / 58) ** 2, 0, 1))
    mu_path = .055 * rubber
    for x in np.arange(12, 121, pitch):
        mu_path += .30 * np.exp(-((xx - x-shift-(1.5+rng.normal(0,.12*variation))*np.sin(yy/15+rng.normal(0,.05*variation)))**2)/1.2)
    bad = rng.random() < .72; typ = rng.choice(("cord_waviness", "foreign", "bubble", "broken_cord"))
    cy, cx = int(rng.integers(26, 103)), int(rng.integers(25, 104)); size = float(rng.uniform(1.3, 6.2))
    contrast = float(rng.uniform(.025, .20))
    if bad:
        m = _disk((n, n), cy, cx, size)
        if typ in ("bubble", "broken_cord"): mu_path[m] -= contrast
        else: mu_path[m] += contrast
    photons = 8500*(1+rng.normal(0,.025*variation)) * np.exp(-mu_path)
    img = rng.poisson(np.maximum(photons, 1)).astype(float) / 8500
    img = ndi.gaussian_filter(img, .9)  # finite focal spot
    diff = float(np.clip(1 - contrast / .20 + .05 / max(size, 1), 0, 1))
    return img, Truth(bad, bad and size >= 4.5, (cy, cx), diff, str(typ), size)


def wheel(seed: int, variation: float = 1.0):
    """Cast aluminium radiograph; pores/shrinkage/inclusion in spoke-root ROI."""
    rng = np.random.default_rng(seed); n = 128; yy, xx = np.indices((n, n)); r = np.hypot(xx-64, yy-64)
    dy,dx=rng.normal(0,.8*variation,2); theta=rng.normal(0,.025*variation); rr=np.hypot(xx-64-dx,yy-64-dy); phi=np.arctan2(yy-64-dy,xx-64-dx)+theta
    spoke = (.15+rng.normal(0,.018*variation))*(np.cos(5*phi)>.55)*((rr>20)&(rr<57))
    thickness=5+rng.normal(0,.22*variation)+(8+rng.normal(0,.28*variation))*((rr>17)&(rr<59))+spoke
    img = np.exp(-.075*thickness); bad = rng.random() < .64
    typ = str(rng.choice(("gas_pore", "shrinkage", "inclusion"))); a = float(rng.uniform(1.2, 6.8))
    ang = rng.uniform(-math.pi, math.pi); rad = rng.uniform(20, 55); cy = 64+rad*np.sin(ang); cx = 64+rad*np.cos(ang)
    amp = float(rng.uniform(.025, .18))
    if bad:
        m = _disk(img.shape, cy, cx, a)
        img[m] += amp if typ != "inclusion" else -amp
        if typ == "shrinkage": img += amp*.45*np.exp(-((xx-cx)**2/25+(yy-cy)**2/3))
    img=ndi.gaussian_filter(img,max(.65,1+rng.normal(0,.08*variation))); img*=1+rng.normal(0,.018*variation); img += rng.normal(0,.012,img.shape)
    root = 20 <= rad <= 34
    severe = bool(bad and (a >= 4.0 or (a >= 2.7 and root)))
    diff = float(np.clip(1-amp/.18+.04/a, 0, 1))
    return img, Truth(bad, severe, (cy, cx), diff, typ, a)


def smt(seed: int, variation: float = 1.0):
    """Three-ring AOI image with five common solder-joint defect modes."""
    rng = np.random.default_rng(seed); h, w = 96, 144; yy, xx = np.indices((h, w))
    board = .20+.035*np.sin(xx/13)+.02*np.cos(yy/11); img = np.dstack((board*.7, board, board*.65))
    dx,dy=rng.normal(0,1.0*variation,2); ang=rng.normal(0,.025*variation); xr=(xx-72-dx)*np.cos(ang)+(yy-48-dy)*np.sin(ang); yr=-(xx-72-dx)*np.sin(ang)+(yy-48-dy)*np.cos(ang)
    pad=(abs(xr)<35+rng.normal(0,.7*variation))&(abs(yr)<13+rng.normal(0,.5*variation)); solder=np.array((.68,.72,.76))*(1+rng.normal(0,.07*variation)); img[pad]=solder
    bad = rng.random() < .68; typ = str(rng.choice(("bridge", "open", "shift", "void", "tombstone")))
    size = float(rng.uniform(2, 10)); amp = float(rng.uniform(.06, .38)); cy, cx = 48., 72.
    if bad:
        if typ == "bridge": m = (abs(xx-72)<size)&(abs(yy-48)<25)
        elif typ == "open": m = _disk((h,w), 48, 72, size)
        elif typ == "shift": m = (abs(xx-(72+size))<27)&(abs(yy-48)<10)
        elif typ == "void": m = _disk((h,w), 48, 72, size)
        else: m = (abs(xx-72)<29)&(abs(yy-(48-size))<8)
        img[m] += (-amp if typ in ("open", "void") else amp)*np.array((.8,.45,.2))
    warp=1+rng.normal(0,.025*variation)*(yy-h/2)/(h/2); img*=warp[...,None]*(1+rng.normal(0,.035*variation)); img=ndi.gaussian_filter(img,(.8,.8,0)); img+=rng.normal(0,.015,img.shape)
    gray = img @ np.array((.25,.6,.15)); diff=float(np.clip(1-amp/.38+.03/size,0,1))
    return gray, Truth(bad, bad and (size >= 6 or typ in ("bridge","tombstone")), (cy,cx), diff, typ, size)


def bevel(seed: int, variation: float = 1.0):
    """Metric plate bevel cloud with scanner noise, missing points and outliers."""
    rng=np.random.default_rng(seed); n=900; x=rng.uniform(-45,45,n); y=rng.uniform(-16,16,n)
    angle=35.0; root=2.0; z=np.where(abs(y)<8, (8-abs(y))*math.tan(math.radians(angle)), 0)
    true_rot=float(rng.normal(0,1.5*variation)); true_shift=float(rng.normal(0,.7*variation)); bad=rng.random()<.62
    angle_err=float(rng.uniform(-4.5,4.5)) if bad else float(rng.normal(0,.5)); root_err=float(rng.uniform(-1.0,1.0)) if bad else float(rng.normal(0,.1))
    z += np.where(abs(y)<8, (8-abs(y))*(math.tan(math.radians(angle+angle_err))-math.tan(math.radians(angle))), 0)
    keep=rng.random(n)>(.10+.03*variation); pts=np.c_[x[keep]+true_shift,y[keep]*np.cos(np.radians(true_rot)),z[keep]+y[keep]*np.sin(np.radians(true_rot))]; pts += rng.normal(0,.08*(1+.2*variation),pts.shape)
    out=rng.uniform((-45,-16,-2),(45,16,8),(35,3)); pts=np.vstack((pts,out))
    truth=Truth(bad, bad and (abs(angle_err)>3 or abs(root_err)>.6),(48,72),min(1,abs(angle_err)/6+.2),"angle_or_root",abs(angle_err),angle_err,root_err)
    return pts, truth


GENERATORS={"tyre":tyre,"wheel":wheel,"bevel":bevel,"smt":smt}


def baseline_detector(measured: np.ndarray, kind: str, threshold: float=.16, model=None):
    """Golden mean + normalized cross-correlation registration + fixed threshold."""
    if kind == "bevel":
        p=measured[np.abs(measured[:,1])<7]; slope=np.polyfit(np.abs(p[:,1]),p[:,2],1)[0]
        angle=math.degrees(math.atan(abs(slope))); return {"hit":abs(angle-35)>threshold,"angle":angle,"root":2.0}
    a=np.asarray(measured,float)
    if model is not None:
        ref=model["golden"]
        aa=(a-a.mean())/(a.std()+1e-12); rr=(ref-ref.mean())/(ref.std()+1e-12)
        cc=np.fft.irfft2(np.fft.rfft2(aa)*np.conj(np.fft.rfft2(rr)))
        shift=np.array(np.unravel_index(np.argmax(cc),cc.shape),float)
        shift[shift>np.array(a.shape)/2]-=np.array(a.shape)[shift>np.array(a.shape)/2]
        a=ndi.shift(a,-shift,order=1,mode="nearest"); residual=np.abs(a-ref)
    else:
        residual=np.abs(a-ndi.gaussian_filter(a,5))
    scale_values=residual
    if kind == "smt":
        roi=np.zeros_like(residual,bool); roi[38:59,58:87]=True
        scale_values=residual[roi]
        residual=np.where(roi,residual,0.0)
    pos=np.unravel_index(np.argmax(residual),residual.shape)
    strength=float(residual[pos]/(np.std(scale_values)+1e-12))
    return {"hit":bool(strength>threshold),"center":tuple(map(float,pos)),"strength":strength}


def fullseye_detector(measured: np.ndarray, kind: str, threshold: float=.08, scale: float=3.0, model=None):
    """Fullseye op pipeline: varmodel_score registration/statistics then gclose morphology."""
    if kind == "bevel":
        p=np.asarray(measured); core=p[(np.abs(p[:,1])<7)&(p[:,2]>-1)&(p[:,2]<8)]
        planes=[]
        for side in (-1,1):
            q=core[core[:,1]*side>0]
            _op("fit_plane3",q)  # least-squares audit/reference using the identical points
            planes.append(_op("ransac_plane",q,.30)[0])
        slopes=[abs(float(pl["normal"][1]/pl["normal"][2])) for pl in planes]
        angle=math.degrees(math.atan(float(np.mean(slopes))))
        return {"hit":abs(angle-35)>threshold,"angle":angle,"root":2.0}
    a=np.asarray(measured,float)
    if model is not None and "variation" in model:
        scored=_op("varmodel_score",a,model["variation"],align="translate")
        residual=np.abs(scored["z"]); residual=np.asarray(_op("gclose",residual,.15,.15),float)
        mask=scored["valid"] & (residual>threshold)
    else:
        residual=np.abs(a-ndi.median_filter(a,size=max(3,int(scale)*2+1)))
        mad=np.median(np.abs(residual-np.median(residual)))+1e-9; mask=residual>threshold*mad
    labels,n=ndi.label(mask,structure=np.ones((3,3),int))
    if int(n)==0: return {"hit":False,"center":(-1.,-1.),"strength":0.}
    ids=np.arange(1,int(n)+1); weights=ndi.sum(residual,labels,ids); k=int(ids[int(np.argmax(weights))])
    cy,cx=ndi.center_of_mass(residual,labels,k)
    return {"hit":bool(weights.max()>threshold),"center":(float(cy),float(cx)),"strength":float(weights.max())}


def score(kind: str, seeds, detector, params, variation: float = 1.0):
    """Independent truth matching and metrics with Wilson 95% intervals."""
    rows=[]; t0=time.perf_counter()
    for seed in seeds:
        measured,truth=GENERATORS[kind](seed,variation=variation); out=detector(measured,kind,**params)
        loc=True if (kind=="bevel" or not truth.defective) else np.hypot(*(np.subtract(out.get("center",(-99,-99)),truth.center))) <= max(8,2*truth.size)
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


def _training_model(kind: str, seeds):
    """Build both methods from the exact same training-good images."""
    if kind not in ("tyre", "wheel", "smt"):
        return None
    good=[]
    for seed in seeds:
        measured, truth=GENERATORS[kind](seed)
        if not truth.defective: good.append(np.asarray(measured,float))
    stack=np.stack(good)
    _op("varmodel_alignment",stack,max_misalign_px=12.0)
    vm=_op("varmodel_fit",stack,spread="moderated",far=DECLARED_FAR,align="translate",
           max_misalign_px=12.0,spread_floor=.003)
    return {"golden":stack.mean(axis=0),"variation":vm,"training_good_seeds":[s for s in seeds if not GENERATORS[kind](s)[1].defective]}


def tune(kind: str, detector, seeds, model=None):
    """同じ12候補の探索予算で、学習用の見逃し+過検出だけを最小化する。"""
    if kind == "bevel":
        grid=np.linspace(.15,4.2,SEARCH_BUDGET)
    elif detector is fullseye_detector:
        grid=np.geomspace(2.0,500.0,SEARCH_BUDGET)
    else:
        grid=np.linspace(.45,6.5,SEARCH_BUDGET)
    best=None
    for th in grid:
        params={"threshold":float(th),"model":model}
        if detector is fullseye_detector: params["scale"]=3
        m,_=score(kind,seeds,detector,params)
        objective=m["miss_rate"][0]+m["false_positive_rate"][0]
        # 「全部出す」「何も出さない」は選ばない。
        valid=0 < m["miss_rate"][0] < 100 and 0 < m["false_positive_rate"][0] < 100
        key=(not valid,objective)
        if best is None or key<best[0]: best=(key,float(th),m)
    return best[1],best[2]


def _mcnemar(base_rows, ours_rows, selector):
    pairs=[(selector(a),selector(b)) for a,b in zip(base_rows,ours_rows) if a[0].defective==b[0].defective]
    n10=sum(a and not b for a,b in pairs); n01=sum((not a) and b for a,b in pairs)
    p=float(binomtest(min(n10,n01),n10+n01,.5).pvalue) if n10+n01 else 1.0
    return {"baseline_only_error":n10,"ours_only_error":n01,"exact_p":p,"significant_0_05":p<.05}


def audit_detector_boundary():
    """Fail if detector interfaces/source can consume generator truth."""
    for f in (baseline_detector,fullseye_detector):
        assert "truth" not in inspect.signature(f).parameters
        src=inspect.getsource(f)
        assert "GENERATORS" not in src and "Truth(" not in src
    return True


def run(kind: str, full: bool=False):
    _OP_CALLS.clear()
    audit_detector_boundary(); train=TRAIN_SEEDS if full else QUICK_TRAIN_SEEDS; hold=HOLDOUT_SEEDS if full else QUICK_HOLDOUT_SEEDS
    model=_training_model(kind,train)
    base_threshold,base_search=tune(kind,baseline_detector,train,model)
    threshold,train_metric=tune(kind,fullseye_detector,train,model)
    bp={"threshold":base_threshold,"model":model}; op={"threshold":threshold,"scale":3,"model":model}
    base_train,_=score(kind,train,baseline_detector,bp); ours_train,_=score(kind,train,fullseye_detector,op)
    base_hold,base_rows=score(kind,hold,baseline_detector,bp); ours_hold,ours_rows=score(kind,hold,fullseye_detector,op)
    b=base_hold["miss_rate"][0]; o=ours_hold["miss_rate"][0]; reduction=100*(b-o)/b if b else None
    sig={"defect_miss":_mcnemar(base_rows,ours_rows,lambda r:r[0].defective and not r[1]),
         "good_false_positive":_mcnemar(base_rows,ours_rows,lambda r:(not r[0].defective) and r[1])}
    sweep=[]
    for level in (.25,.5,1.,1.5,2.):
        ss=hold[:min(160,len(hold))]
        bm,_=score(kind,ss,baseline_detector,bp,level); om,_=score(kind,ss,fullseye_detector,op,level)
        sweep.append({"variation_level":level,"baseline_false_positive_percent":bm["false_positive_rate"][0],"ours_false_positive_percent":om["false_positive_rate"][0]})
    far={"declared_pixel_far":DECLARED_FAR,"measured_pixel_far":None,"good_images":0}
    if model is not None:
        ne=nv=ng=0
        for seed in hold:
            image,truth=GENERATORS[kind](seed)
            if not truth.defective:
                z=_op("varmodel_score",image,model["variation"],align="translate")
                ne+=z["n_exceed"]; nv+=z["n_valid"]; ng+=1
        far={"declared_pixel_far":DECLARED_FAR,"measured_pixel_far":ne/nv if nv else None,"good_images":ng}
    return {"kind":kind,"model":LABEL[kind],"mode":"full" if full else "quick","seeds":{"train":list(train),"holdout":list(hold)},"search_budget_each":SEARCH_BUDGET,"defect_model":DEFECT_TABLE[kind],"good_variation":VARIATION_TABLE[kind],"baseline":"同じ学習良品の平均像+正規化相互相関位置合わせ+固定閾値" if kind!="bevel" else "同じ点群を使う外れ値除去なし最小二乗","pipeline":"Fullseye位置合わせ→良品変動モデル→z残差→形態学" if kind!="bevel" else "同じ点群ROI→頑健中央値プロファイル→角度当てはめ","fullseye_ops":sorted(set(_OP_CALLS)),"selected_thresholds":{"baseline":base_threshold,"ours":threshold},"train_search_metric":{"baseline":base_search,"ours":train_metric},"train":{"baseline":base_train,"ours":ours_train},"holdout":{"baseline":base_hold,"ours":ours_hold},"variation_sweep":sweep,"far_check":far,"mcnemar":sig,"miss_reduction_percent":reduction,"wef_reported_reduction_percent":WEF[kind],"comparison_warning":"WEFは各実工場の導入前との比較。本仮想工場の同一真値比較とは前提が異なり、勝敗を示さない。","loss_condition":"variation_sweepまたは高難度曲線で提案法が基準を下回る条件を負けとして申告する。","_rows":(base_rows,ours_rows)}


DEFECT_TABLE={
 "tyre":{"types":["コード乱れ","異物","気泡","コード切れ"],"size":"半径1.3–6.2 px","prevalence":"72%","basis":"Beer–Lambert、8500光子、焦点ぼけσ=0.9 px。寸法・率は公開性能値ではなく感度試験の設計範囲。"},
 "wheel":{"types":["ガス気孔","引け巣","介在物"],"size":"半径1.2–6.8 px","prevalence":"64%","basis":"重大=半径4 px以上、またはスポーク根元で2.7 px以上。応力集中部を厳しくする工学的スクリーニング規則（規格の合否値ではない）。"},
 "bevel":{"types":["開先角外れ","ルート面外れ"],"size":"角度±4.5°、ルート±1.0 mm","prevalence":"62%","basis":"実寸mm、点雑音σ=0.08 mm、欠測10%、外れ値35点。範囲は位置合わせ感度試験の設計値。"},
 "smt":{"types":["ブリッジ","未はんだ","ずれ","ボイド","トゥームストーン"],"size":"2–10 px","prevalence":"68%","basis":"3色リングAOIの簡略反射像。種類はIPC-A-610で一般に検査される状態、寸法・率は感度試験の設計値。"}}

VARIATION_TABLE={
 "tyre":{"factors":"コードpitch σ0.22 px、うねりσ0.12、ゴム厚σ0.35、管電流σ2.5%、搬送σ1.0 px","basis":"Beer–Lambert線積分とPoisson量子雑音に重ねた工程感度試験範囲。"},
 "wheel":{"factors":"鋳造肉厚σ0.22/0.28、置き方σ0.8 px・回転σ0.025 rad、線源倍率σ1.8%、スポーク厚σ0.018","basis":"鋳造・治具・撮像の独立工程変動として与えた感度試験値。"},
 "bevel":{"factors":"置き方σ0.7 mm・σ1.5°、視点傾き、欠測10%+3%×強度、点雑音σ0.08 mm","basis":"既存CAD/scan・ICP PoCと同じ実寸点群の感度試験。"},
 "smt":{"factors":"載置x/y σ1 px・θ σ0.025 rad、はんだ寸法σ0.7/0.5 px・量σ7%、反りσ2.5%、照明σ3.5%","basis":"IPC-A-610状態分類を対象にした簡略3リングAOI工程の感度試験値。"}}


def save_result(kind: str, result: dict, out: Path):
    out.mkdir(parents=True,exist_ok=True); clean={k:v for k,v in result.items() if k!="_rows"}
    (out/"results.json").write_text(json.dumps(clean,ensure_ascii=False,indent=2),encoding="utf-8")
