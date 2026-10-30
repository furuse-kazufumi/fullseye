# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""FingerVision 公開式2版、Green逆算、場全体ridgeを独立した物理合成像で比較する。

外部: Yamaguchi & Atkeson (Humanoids 2016/2017) の式、Johnson (1985)
§3, §7.2、既存 tacsim/tacslip。自作: 4 mm XP-565相当接着層の選択的
低減積分Q4軸対称FEM、皮膚--カメラ22 mmの等距離魚眼、較正/評価分離。
ビーズは論文どおり金型底、すなわち接触表面（報告深さ0 mm）に置く。
FULLSEYE_TAXIM_DATA が無いためTaxim節点変位との第三照合は未実施。
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
import fvbench_layer as L  # noqa:E402


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


def physics_validation():
    rows=[]
    for nu in (.40,.45,.48,.49,.499):
        r,ur,uz=L.axisymmetric_bonded_layer(nu,96,18)
        uh,zh=L.halfspace_normal(r,nu)
        rows.append((nu,float(np.max(np.abs(ur))/np.max(np.abs(uh))),float(uz[0]/zh[0]),
                     float(np.max(np.abs(ur))),float(uz[0])))
    # Barber (2019) §4 Eq. (4.1), attributed there to Johnson: u=p/k.
    nu=.40; a=.016; r,_,uz=L.axisymmetric_bonded_layer(nu,96,18,16.,1.,rmax_mm=48.)
    p0=3/(2*math.pi*a*a); k=F.E_GEL*(1-nu)/((1+nu)*(1-2*nu)*F.THICKNESS)
    theory_ratio=float(uz[0]/(p0/k))
    return rows,L.convergence(.48),theory_ratio


def evaluate(full=False):
    t0=time.perf_counter(); ref=F.synthesize(F.Truth((0,0,0)),seed=1)
    # 較正: 半径11/13 mm、複数偏心、2--14 N。評価は未見の半径9/16 mm、
    # 未見の偏心(3,-2)と力範囲1--20 N。全手法へ同じ較正像を渡す。
    cal=[]
    cal_pos=((-2.,0.),(2.,1.),(0.,-2.))
    for i,p in enumerate(np.linspace(2,14,10)):
        for j,(fx,fy) in enumerate(((0,0),(.18*p,0),(-.18*p,0),(0,.14*p),(0,-.14*p))):
            tr=F.Truth((fx,fy,p),contact_xy_mm=cal_pos[(i+j)%3],indenter_radius_mm=11 if (i+j)%2 else 13)
            cal.append((F.synthesize(tr,seed=10+i*5+j),tr.force_N,0.))
    for i,tau in enumerate(np.linspace(-.003,.003,6)):
        tr=F.Truth((0,0,8),torque_Nm=float(tau),contact_xy_mm=cal_pos[i%3],indenter_radius_mm=12)
        cal.append((F.synthesize(tr,seed=1000+i),tr.force_N,tr.torque_Nm))
    c=F.calibrate(cal,ref)
    slip_cal=[]
    for case in range(6):
        p=5+case
        for k,q in enumerate(np.linspace(0,1.2*F.MU*p,8)):
            label=q>=F.MU*p; tr=F.Truth((q,0,p),slip=label)
            slip_cal.append((F.synthesize(tr,phase=k/2,seed=500+case*8+k),label))
    F.tune_slip_thresholds(c,slip_cal,budget=41)
    ev=[]
    for i,p in enumerate(np.linspace(1,20,40 if full else 16)):
        tr=F.Truth(((-1)**i*.22*p, .16*p, p),contact_xy_mm=(3,-2),indenter_radius_mm=9 if i%2 else 16)
        ev.append((tr,F.synthesize(tr,seed=100+i)))
    methods=(F.read_baseline2016,F.read_baseline2017,F.read_tactile,F.read_field_ridge)
    names=("基準2016","基準2017","層Green逆算","場全体ridge")
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
    torque_truth=np.linspace(-.003,.003,len(ev)); torque={"基準2016":"—","基準2017":"—"}
    for name,fn in zip(names[2:],methods[2:]):
        pred=[]
        for i,(tr,_) in enumerate(ev):
            tt=F.Truth(tr.force_N,torque_Nm=float(torque_truth[i]),contact_xy_mm=tr.contact_xy_mm,indenter_radius_mm=tr.indenter_radius_mm)
            pred.append(fn(F.synthesize(tt,seed=1500+i),clone(c))["torque"])
        torque[name]={"rmse_Nm":_score_rmse(pred,torque_truth),"r2":r2(torque_truth,pred)}
    conditions=(("明","bright",1,False,False),("黒","black",1,False,False),("肌色","skin",1,False,False),
                ("背景移動","bright",1,False,True),("暗所","bright",.10,False,False),("非滑り変形","bright",1,True,False))
    cases=25 if full else 4; slip_rows=[]; delays=[[] for _ in methods]; leads=[[],[]]
    for ci,(label,color,bright,deform,moving) in enumerate(conditions):
        yy=[[] for _ in methods]; pp=[[] for _ in methods]
        for case in range(cases):
            states=[clone(c) for _ in methods]; first=[None]*len(methods); precursor=[None,None]
            P=6+8*(case/max(cases-1,1)); onset=4
            for k,q in enumerate(np.linspace(0,1.25*F.MU*P,8)):
                slip=(q>=F.MU*P) and not deform
                tr=F.Truth((q,0,P),slip=slip,slip_dir=(1,0))
                im=F.synthesize(tr,color=color,brightness=bright,phase=k/2,deform=deform,moving_bg=moving,seed=ci*10000+case*20+k)
                for m,fn in enumerate(methods):
                    out=fn(im,states[m]); yy[m].append(slip); pp[m].append(out["slip"])
                    if out["slip"] and first[m] is None: first[m]=k
                    if m>=2 and out.get("slip_precursor") and precursor[m-2] is None: precursor[m-2]=k
            for m in range(len(methods)): delays[m].append(1000*(first[m]-onset)/F.FPS if first[m] is not None else math.nan)
            for m,x in enumerate(precursor):
                if x is not None: leads[m].append(1000*(onset-x)/F.FPS)
        vals=[f1_ci(yy[m],pp[m]) for m in range(len(methods))]; slip_rows.append((label,*vals))
    # 回転は画像の同じ組を三手法へ渡す。
    angles=np.linspace(-10,10,11); rot=[None,None]
    for fn in methods[2:3]:
        pred=[fn(F.synthesize(F.Truth((0,0,8),angle_deg=float(a)),seed=900+i),clone(c))["angle_deg"] for i,a in enumerate(angles)]
        rot.append(_score_rmse(pred,angles))
    rot.append(None)  # ridge はトルクを出すが物体角度は出さない
    # 黒ビーズと背景のMichelson contrastを直接測り、追跡成立境界を掃引する。
    contrast=[]
    for color in ("bright","skin","black"):
        for bright in np.linspace(.02,1,20):
            im=F.synthesize(F.Truth((1,0,8)),color=color,brightness=float(bright),seed=77)
            g=im.mean(2); hi=float(np.percentile(g,80)); lo=float(np.percentile(g,2))
            con=(hi-lo)/max(hi+lo,1e-9); matched=F._track(im,c)["matched"]
            contrast.append((color,float(bright),con,matched))
    contrast_boundary={}
    for color in ("bright","skin","black"):
        good=[x[2] for x in contrast if x[0]==color and x[3]>=6]
        bad=[x[2] for x in contrast if x[0]==color and x[3]<6]
        contrast_boundary[color]=(min(good) if good else None,max(bad) if bad else None)
    physical,conv,theory_ratio=physics_validation()
    print("半空間比（nu, 層/半空間 横最大, 縦中心, 層横m, 層縦m）")
    for row in physical: print(row)
    print("FEM収束（nr,nz,横最大,縦中心,直前格子との差）",conv)
    print(f"薄層理論照合: Barber (2019) §4 Eq. 4.1（Johnson帰属）のu=p/kに対するFEM中心変位比={theory_ratio:.3f} (nu=.40,a/h=4)。")
    print("力（各セル RMSE N / R2、軸 Fx,Fy,Fz）")
    print("method       calibration                         evaluation")
    for n in names:
        x=force[n]; print(f"{n:10s} {x['cal_rmse']} / {x['cal_r2']}   {x['eval_rmse']} / {x['eval_r2']}")
    print("ridge（較正内CVのみ）",c.ridge_cv_rmse,"選択",c.ridge_selected,"lambda",c.ridge_lambda)
    for variant in ("raw","green-pca"):
        pe=np.asarray([F.read_field_ridge(im,clone(c),variant)["force_N"] for _,im in ev])
        print("ridge変種",variant,"評価RMSE",[_score_rmse(pe[:,j],ev_truth[:,j]) for j in range(3)])
    print("トルク（評価RMSE N m / R2）",torque)
    print("滑り F1 [Wilson 95% CI]")
    for row in slip_rows: print(row[0],*[f"{v[0]:.3f}[{v[1]:.3f},{v[2]:.3f}]" for v in row[1:]])
    print("遅れ中央値ms",[float(np.nanmedian(x)) if np.isfinite(x).any() else None for x in delays],
          "前兆先行ms（固着域, 力比）",[float(np.median(x)) if x else None for x in leads])
    print("回転RMSE deg",{n:("—" if v is None else v) for n,v in zip(names,rot)})
    print("コントラスト境界（追跡可の最小, 不可の最大）",contrast_boundary)
    print("黒い物・暗所: 黒ビーズと黒背景の輝度差が消えると、公開法も提案法も同じ追跡入力を失い原理的に読めない。")
    print("改善案（白ビーズ・内部照明・縁取り）は光学模型を追加していないため未試験。")
    print("負け条件: 提案法は暗所/マーカー消失、ヒステリシス、剥離、未知のビーズ深さで不利。Taxim外部FEMデータなし。")
    print("画像再現度: 実画像が無いためTaximのSSIM/PSNRとは比較しない。")
    if figs.enabled():
        figs.save_grid("fvbench_sensor_examples",[ref,ev[-1][1]],ncols=2,captions=["reference","unseen radius/offset"],caption="22 mm等距離魚眼、物理順方向。")
        series=[]
        for n,p in zip(names,ev_pred): series += [(n+" Fx",ev_truth[:,0],p[:,0]),(n+" Fz",ev_truth[:,2],p[:,2])]
        figs.save("fvbench_force_scatter",figs.render_plot(series,xlabel="truth [N]",ylabel="estimate [N]",title="held-out force"),caption="較正に無い半径・位置・範囲。")
        figs.save("fvbench_slip_delay",figs.render_plot([(n,np.arange(len(d)),np.nan_to_num(d,nan=200)) for n,d in zip(names,delays)],xlabel="sequence",ylabel="delay [ms]",title="30 fps slip onset"),caption="Q=muPからの遅れ。未検出は200 ms表示。")
        figs.save_table("fvbench_condition_f1",["condition",*names],[[r[0],*[f"{x[0]:.3f} [{x[1]:.3f},{x[2]:.3f}]" for x in r[1:]]] for r in slip_rows],title="Slip F1 (Wilson 95% CI)",caption="--fullは各条件25時系列×8=200フレーム。")
        figs.save_table("fvbench_layer_physics",["nu","ur layer/half","uz layer/half","ur layer [um]","uz layer [um]"],
                        [[f"{x[0]:.3f}",f"{x[1]:.3f}",f"{x[2]:.3f}",f"{1e6*x[3]:.2f}",f"{1e6*x[4]:.2f}"] for x in physical],
                        title="4 mm bonded layer versus half-space",caption="1 N, a=6 mm; selective reduced integration Q4 FEM.")
        figs.save("fvbench_contrast_boundary",figs.render_plot([(x[0],np.asarray([r[2] for r in contrast if r[0]==x[0]]),np.asarray([r[3] for r in contrast if r[0]==x[0]])) for x in (("bright",),("skin",),("black",))],xlabel="Michelson contrast",ylabel="matched markers",title="visibility boundary"),caption="6 markers未満では全変位場手法が推定不能。")
        force_rows=[]
        for split in ("cal","eval"):
            for metric in ("rmse","r2"):
                for axis_i,axis in enumerate(("Fx","Fy","Fz")):
                    force_rows.append([f"{split} {axis} {metric}",*[f"{force[n][split+'_'+metric][axis_i]:.3f}" for n in names]])
        figs.save_table("fvbench_force_metrics",["metric",*names],force_rows,
                        title="Force calibration and held-out evaluation",caption="RMSE [N] / R2。ridgeのlambdaは較正内CVのみで選択。")
    return {"force":force,"torque":torque,"slip":slip_rows,"delays":delays,"rotation":rot,"physics":physical,"convergence":conv,"theory_ratio":theory_ratio,"contrast_boundary":contrast_boundary,"elapsed_s":time.perf_counter()-t0,"n_per_condition":cases*8}


if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--full",action="store_true"); ns=ap.parse_args(); out=evaluate(ns.full)
    if not ns.full and out["elapsed_s"]>60: raise SystemExit("default run exceeded 60 s")
