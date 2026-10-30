# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""FingerVision 公開式2版とGreen関数逆算を、独立した物理合成像で比較する。

外部: Yamaguchi & Atkeson (Humanoids 2016/2017) の式、Johnson (1985)
§3, §7.2、既存 tacsim/tacslip。自作: 4 mm XP-565相当層、皮膚--カメラ
22 mmの等距離魚眼、較正/評価分離、時系列評価。FULLSEYE_TAXIM_DATA が無い
環境なので有限厚FEM補正はせず、半空間が層厚4 mmを超える範囲を負け条件にする。
門: 同じRGB像、推定器はTruthを読まない、順方向に較正係数なし、基準式の探針。
Run: py -3.11 examples/poc_fingervision_benchmark.py [--full]
"""
from __future__ import annotations
import argparse, copy, math, sys, time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa:E402
import fvbench as F  # noqa:E402


def clone(c):
    d=copy.copy(c); d.previous=None; d.mog2=None
    return d


def _score_rmse(a,b): return float(np.sqrt(np.mean((np.asarray(a)-np.asarray(b))**2)))
def r2(a,b):
    a,b=np.asarray(a),np.asarray(b); return float(1-np.sum((a-b)**2)/max(np.sum((a-a.mean())**2),1e-12))
def f1_ci(y,p):
    y,p=np.asarray(y,bool),np.asarray(p,bool); tp=(y&p).sum(); fp=(~y&p).sum(); fn=(y&~p).sum()
    n=2*tp+fp+fn; score=float(2*tp/max(n,1)); z=1.96
    den=1+z*z/max(n,1); mid=(score+z*z/(2*max(n,1)))/den
    half=z*math.sqrt(score*(1-score)/max(n,1)+z*z/(4*max(n,1)**2))/den
    return score,max(0,mid-half),min(1,mid+half)


def evaluate(full=False):
    t0=time.perf_counter(); ref=F.synthesize(F.Truth((0,0,0)),seed=1)
    # 較正: 中心、半径12 mm、2--14 N。評価は半径9/16 mm、偏心、1--20 N。
    cal=[]
    for i,p in enumerate(np.linspace(2,14,14)):
        for fx,fy in ((0,0),(.18*p,0),(0,-.14*p)):
            tr=F.Truth((fx,fy,p)); cal.append((F.synthesize(tr,seed=10+i),tr.force_N,0.))
    c=F.calibrate(cal,ref)
    ev=[]
    for i,p in enumerate(np.linspace(1,20,40 if full else 16)):
        tr=F.Truth(((-1)**i*.22*p, .16*p, p),contact_xy_mm=(3,-2),indenter_radius_mm=9 if i%2 else 16)
        ev.append((tr,F.synthesize(tr,seed=100+i)))
    methods=(F.read_baseline2016,F.read_baseline2017,F.read_tactile); names=("基準2016","基準2017","Green逆算")
    def force_set(rows):
        truth=np.asarray([x[1] for x in rows]); pred=[]
        for fn in methods:
            pred.append(np.asarray([fn(im,clone(c))["force_N"] for im,_,_ in rows]))
        return truth,pred
    cal_truth,cal_pred=force_set(cal)
    ev_truth=np.asarray([tr.force_N for tr,_ in ev]); ev_pred=[np.asarray([fn(im,clone(c))["force_N"] for tr,im in ev]) for fn in methods]
    force={}
    for name,pc,pe in zip(names,cal_pred,ev_pred):
        force[name]={"cal_rmse":[_score_rmse(pc[:,j],cal_truth[:,j]) for j in range(3)],"cal_r2":[r2(cal_truth[:,j],pc[:,j]) for j in range(3)],
                     "eval_rmse":[_score_rmse(pe[:,j],ev_truth[:,j]) for j in range(3)],"eval_r2":[r2(ev_truth[:,j],pe[:,j]) for j in range(3)]}
    conditions=(("明","bright",1,False,False),("黒","black",1,False,False),("肌色","skin",1,False,False),
                ("背景移動","bright",1,False,True),("暗所","bright",.10,False,False),("非滑り変形","bright",1,True,False))
    cases=25 if full else 4; slip_rows=[]; delays=[[] for _ in methods]; leads=[]
    for ci,(label,color,bright,deform,moving) in enumerate(conditions):
        yy=[[] for _ in methods]; pp=[[] for _ in methods]
        for case in range(cases):
            states=[clone(c) for _ in methods]; first=[None]*3; precursor=None
            P=6+8*(case/max(cases-1,1)); onset=4
            for k,q in enumerate(np.linspace(0,1.25*F.MU*P,8)):
                slip=(q>=F.MU*P) and not deform
                tr=F.Truth((q,0,P),slip=slip,slip_dir=(1,0))
                im=F.synthesize(tr,color=color,brightness=bright,phase=k/2,deform=deform,moving_bg=moving,seed=ci*10000+case*20+k)
                for m,fn in enumerate(methods):
                    out=fn(im,states[m]); yy[m].append(slip); pp[m].append(out["slip"])
                    if out["slip"] and first[m] is None: first[m]=k
                    if m==2 and out.get("slip_precursor") and precursor is None: precursor=k
            for m in range(3): delays[m].append(1000*(first[m]-onset)/F.FPS if first[m] is not None else math.nan)
            if precursor is not None: leads.append(1000*(onset-precursor)/F.FPS)
        vals=[f1_ci(yy[m],pp[m]) for m in range(3)]; slip_rows.append((label,*vals))
    # 回転は画像の同じ組を三手法へ渡す。
    angles=np.linspace(-10,10,11); rot=[]
    for fn in methods:
        pred=[fn(F.synthesize(F.Truth((0,0,8),angle_deg=float(a)),seed=900+i),clone(c))["angle_deg"] for i,a in enumerate(angles)]
        rot.append(_score_rmse(pred,angles))
    print("力（各セル RMSE N / R2、軸 Fx,Fy,Fz）")
    print("method       calibration                         evaluation")
    for n in names:
        x=force[n]; print(f"{n:10s} {x['cal_rmse']} / {x['cal_r2']}   {x['eval_rmse']} / {x['eval_r2']}")
    print("滑り F1 [Wilson 95% CI]")
    for row in slip_rows: print(row[0],*[f"{v[0]:.3f}[{v[1]:.3f},{v[2]:.3f}]" for v in row[1:]])
    print("遅れ中央値ms",[float(np.nanmedian(x)) if np.isfinite(x).any() else None for x in delays],"前兆先行ms",float(np.median(leads)) if leads else None)
    print("回転RMSE deg",dict(zip(names,rot)))
    print("負け条件: Green逆算は暗所/マーカー消失、ヒステリシス、接触半径が4 mm層厚を超える大荷重で不利。有限厚FEMデータなし。")
    print("画像再現度: 実画像が無いためTaximのSSIM/PSNRとは比較しない。")
    if figs.enabled():
        figs.save_grid("fvbench_sensor_examples",[ref,ev[-1][1]],ncols=2,captions=["reference","unseen radius/offset"],caption="22 mm等距離魚眼、物理順方向。")
        series=[]
        for n,p in zip(names,ev_pred): series += [(n+" Fx",ev_truth[:,0],p[:,0]),(n+" Fz",ev_truth[:,2],p[:,2])]
        figs.save("fvbench_force_scatter",figs.render_plot(series,xlabel="truth [N]",ylabel="estimate [N]",title="held-out force"),caption="較正に無い半径・位置・範囲。")
        figs.save("fvbench_slip_delay",figs.render_plot([(n,np.arange(len(d)),np.nan_to_num(d,nan=200)) for n,d in zip(names,delays)],xlabel="sequence",ylabel="delay [ms]",title="30 fps slip onset"),caption="Q=muPからの遅れ。未検出は200 ms表示。")
        figs.save_table("fvbench_condition_f1",["condition",*names],[[r[0],*[f"{x[0]:.3f} [{x[1]:.3f},{x[2]:.3f}]" for x in r[1:]]] for r in slip_rows],title="Slip F1 (Wilson 95% CI)",caption="--fullは各条件25時系列×8=200フレーム。")
    return {"force":force,"slip":slip_rows,"delays":delays,"rotation":rot,"elapsed_s":time.perf_counter()-t0,"n_per_condition":cases*8}


if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--full",action="store_true"); ns=ap.parse_args(); out=evaluate(ns.full)
    if not ns.full and out["elapsed_s"]>60: raise SystemExit("default run exceeded 60 s")
