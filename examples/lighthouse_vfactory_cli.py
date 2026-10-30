"""CLI and committed figure writer for the four Lighthouse virtual factories."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import examplefig as figs
import fullseye as fs
from lighthouse_vfactory import GENERATORS, run, save_result

def _bar(result):
    canvas=np.ones((640,1280,3),float); vals=[]
    for split in ("train","holdout"):
        for method in ("baseline","ours","evolved"): vals.append(result[split][method]["miss_rate"][0])
    colors=((.65,.65,.65),(.15,.45,.8),(.15,.7,.35))*2
    for i,(v,c) in enumerate(zip(vals,colors)):
        x=65+i*195; h=int(5*v); canvas[570-h:570,x:x+115]=c
    return fs.annotate_legend(canvas,["見逃し率%: 学習/holdout × 基準・手組み・進化",str([round(v,1) for v in vals])],(20,20),font_size=24,radius=16)

def _curve(result):
    canvas=np.ones((640,1280,3),float)
    for j,method in enumerate(("baseline","ours","evolved")):
        ds=result["holdout"][method]["difficulty"]
        pts=[]
        for i,d in enumerate(ds):
            if d["detection_rate"] is not None: pts.append((180+i*420,570-int(4.8*d["detection_rate"])))
        for a,b in zip(pts[:-1],pts[1:]):
            rr=np.linspace(a[1],b[1],100).astype(int); cc=np.linspace(a[0],b[0],100).astype(int); canvas[rr,cc]=((.5,.5,.5),(.1,.4,.85),(.1,.7,.3))[j]
    return fs.annotate_legend(canvas,["難しさ別検出率: 灰=基準、青=手組み、緑=進化","左=易 / 右=難"],(20,20),font_size=24,radius=16)

def _budget_curve(result):
    canvas=np.ones((640,1280,3),float); rows=result["budget_curve"]
    for split,color in (("train",(.1,.4,.85)),("holdout",(.1,.7,.3))):
        pts=[(180+i*850,570-int(4.8*r[split]["miss_rate"][0])) for i,r in enumerate(rows)]
        for a,b in zip(pts[:-1],pts[1:]):
            rr=np.linspace(a[1],b[1],300).astype(int); cc=np.linspace(a[0],b[0],300).astype(int); canvas[rr,cc]=color
    return fs.annotate_legend(canvas,["探索予算と見逃し率: 青=学習、緑=最終評価",str(result["search_budgets"])],(20,20),font_size=24,radius=16)

def _variation_curve(result):
    canvas=np.ones((640,1280,3),float); rows=result["variation_sweep"]
    for j,key in enumerate(("baseline_false_positive_percent","ours_false_positive_percent")):
        pts=[(120+i*245,570-int(4.8*r[key])) for i,r in enumerate(rows)]
        for a,b in zip(pts[:-1],pts[1:]):
            rr=np.linspace(a[1],b[1],160).astype(int); cc=np.linspace(a[0],b[0],160).astype(int)
            canvas[rr,cc]=((.5,.5,.5) if j==0 else (.1,.4,.85))
    return fs.annotate_legend(canvas,["良品ばらつき強度と過検出率: 灰=golden、青=変動モデル","強度 0.25 / 0.5 / 1 / 1.5 / 2"],(20,20),font_size=24,radius=16)

def _overlay(measured,truth,label):
    if measured.ndim==2 and measured.shape[1]!=3:
        im=np.asarray(measured,float); im=(im-im.min())/(np.ptp(im)+1e-9); rgb=np.dstack((im,im,im))
        y,x=map(int,truth.center); r=max(8,int(2*truth.size))
        rgb[max(0,y-r):min(rgb.shape[0],y+r+1),[max(0,x-r),min(rgb.shape[1]-1,x+r)]]=(1,0,0)
        rgb[[max(0,y-r),min(rgb.shape[0]-1,y+r)],max(0,x-r):min(rgb.shape[1],x+r+1)]=(1,0,0)
        zoom=max(1,int(np.ceil(1280/rgb.shape[1]))); rgb=np.repeat(np.repeat(rgb,zoom,0),zoom,1)
    else:
        rgb=np.ones((640,1280,3)); p=measured; x=((p[:,0]+50)*12).astype(int); y=(570-p[:,2]*45).astype(int); ok=(x>=0)&(x<1280)&(y>=0)&(y<640); rgb[y[ok],x[ok]]=(.1,.2,.7)
    return fs.annotate_legend(rgb,[label,"赤枠=真値領域（点群は測定点）"],(20,20),font_size=22,radius=15)

def main(kind):
    ap=argparse.ArgumentParser(); ap.add_argument("--full",action="store_true"); ns=ap.parse_args()
    result=run(kind,ns.full); ids={"tyre":"tyre_xray","wheel":"cast_wheel","bevel":"bevel_pointcloud","smt":"smt_aoi"}; out=Path(__file__).resolve().parents[1]/"docs/articles/assets/poc"/("poc_lighthouse_"+ids[kind])
    save_result(kind,result,out)
    figs.save("miss_comparison",_bar(result),caption="学習用と独立holdoutの見逃し率。95%区間はresults.json。")
    figs.save("difficulty_curve",_curve(result),caption="欠陥の難しさ別検出率。小寸法・低コントラスト・欠測側で低下する。")
    figs.save("variation_false_positive_curve",_variation_curve(result),caption="良品ばらつきを増やしたときの過検出率。学習済み模型と閾値は固定。")
    figs.save("budget_curve",_budget_curve(result),caption="探索予算と学習・評価成績。差は過学習の大きさを示す。")
    ours=result["_rows"][2]; seeds=result["seeds"]["holdout"]
    cases=(("miss_example",lambda r:r[0].defective and not r[1],"提案法の見逃し例"),("false_positive_example",lambda r:(not r[0].defective) and r[1],"提案法の過検出例"))
    for name,pred,label in cases:
        idx=next((i for i,r in enumerate(ours) if pred(r)),0); measured,truth=GENERATORS[kind](seeds[idx])
        figs.save(name,_overlay(measured,truth,label),caption=label+"。検出器出力から選び、真値は表示だけに使用。長辺1280 px以上。")
    if figs.errors(): raise RuntimeError("; ".join(figs.errors()))
    clean={k:v for k,v in result.items() if k!="_rows"}; print(json.dumps(clean,ensure_ascii=False,indent=2)); return 0
