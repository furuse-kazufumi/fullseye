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
    canvas=np.ones((260,520,3),float); vals=[]
    for split in ("train","holdout"):
        for method in ("baseline","ours"): vals.append(result[split][method]["miss_rate"][0])
    colors=((.65,.65,.65),(.15,.45,.8),(.65,.65,.65),(.15,.45,.8))
    for i,(v,c) in enumerate(zip(vals,colors)):
        x=45+i*115; h=int(2*v); canvas[225-h:225,x:x+65]=c
    return fs.annotate_legend(canvas,["見逃し率%: 学習 基準/提案、holdout 基準/提案",str([round(v,1) for v in vals])],(8,8),font_size=12)

def _curve(result):
    canvas=np.ones((240,520,3),float)
    for j,method in enumerate(("baseline","ours")):
        ds=result["holdout"][method]["difficulty"]
        pts=[]
        for i,d in enumerate(ds):
            if d["detection_rate"] is not None: pts.append((80+i*160,210-int(1.7*d["detection_rate"])))
        for a,b in zip(pts[:-1],pts[1:]):
            rr=np.linspace(a[1],b[1],100).astype(int); cc=np.linspace(a[0],b[0],100).astype(int); canvas[rr,cc]=((.5,.5,.5) if j==0 else (.1,.4,.85))
    return fs.annotate_legend(canvas,["難しさ別検出率: 灰=基準、青=提案","左=易 / 右=難"],(8,8),font_size=12)

def main(kind):
    ap=argparse.ArgumentParser(); ap.add_argument("--full",action="store_true"); ns=ap.parse_args()
    result=run(kind,ns.full); ids={"tyre":"tyre_xray","wheel":"cast_wheel","bevel":"bevel_pointcloud","smt":"smt_aoi"}; out=Path(__file__).resolve().parents[1]/"docs/articles/assets/poc"/("poc_lighthouse_"+ids[kind])
    save_result(kind,result,out); measured,truth=GENERATORS[kind](result["seeds"]["holdout"][0])
    figs.save("miss_comparison",_bar(result),caption="学習用と独立holdoutの見逃し率。95%区間はresults.json。")
    figs.save("difficulty_curve",_curve(result),caption="欠陥の難しさ別検出率。小寸法・低コントラスト・欠測側で低下する。")
    if kind!="bevel":
        im=np.asarray(measured,float); im=(im-im.min())/(np.ptp(im)+1e-9); rgb=np.dstack((im,im,im)); y,x=map(int,truth.center); rgb[max(0,y-8):y+9,[max(0,x-8),min(rgb.shape[1]-1,x+8)]]=(1,0,0); rgb[[max(0,y-8),min(rgb.shape[0]-1,y+8)],max(0,x-8):x+9]=(1,0,0)
    else:
        rgb=np.ones((240,520,3)); p=measured; x=((p[:,0]+50)*5).astype(int); y=(210-p[:,2]*20).astype(int); ok=(x>=0)&(x<520)&(y>=0)&(y<240); rgb[y[ok],x[ok]]=(.1,.2,.7)
    figs.save("representative_overlay",rgb,caption="代表holdout試料。赤枠（点群は青点）は測定データ上の欠陥領域で、縦横比を保持。")
    if figs.errors(): raise RuntimeError("; ".join(figs.errors()))
    clean={k:v for k,v in result.items() if k!="_rows"}; print(json.dumps(clean,ensure_ascii=False,indent=2)); return 0
