# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ボアスコープのリレー結像とファイバ束の限界を動く 3-D で見る。"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
from scipy.special import j1

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT), str(ROOT / "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import optics
import pocviewer as pv

OUT_HTML = ROOT / "docs" / "view2026" / "anim3d" / "borescope_anim3d.html"
LANGS = ("ja", "en")
F = 12.0
PITCH_UM = 32.0


def T(ja, en):
    return pv.viewer_text(ja, en)


def _e(x):
    return "< 1e-12" if abs(float(x)) < 1e-12 else "%.3g" % float(x)


def _box(sx, sy, sz):
    p = np.array([[x, y, z] for x in (-sx/2, sx/2) for y in (-sy/2, sy/2) for z in (-sz/2, sz/2)], float)
    f = np.array([[0,1,3],[0,3,2],[4,6,7],[4,7,5],[0,4,5],[0,5,1],[2,3,7],[2,7,6],[0,2,6],[0,6,4],[1,5,7],[1,7,3]])
    return p, f


def _disc(r=.5, n=24):
    a = np.linspace(0, 2*np.pi, n, endpoint=False)
    p = np.vstack([[0,0,0], np.column_stack([np.zeros(n), r*np.cos(a), r*np.sin(a)])])
    return p, np.array([[0, i+1, (i+1)%n+1] for i in range(n)])


def _poses(n, b):
    xyz = np.zeros((n,b,3)); q = np.zeros((n,b,4)); q[...,0] = 1
    return xyz, q


def _band(rows, width=720, height=96):
    out=np.zeros((len(rows),height,width,3),np.uint8); cols=((50,155,220),(255,183,55),(102,187,106),(239,108,92))
    for k,row in enumerate(rows):
        out[k]=(9,18,28)
        for j,v in enumerate(row):
            x0,x1=j*width//4+7,(j+1)*width//4-7; h=int(np.clip(v,0,1)*(height-18))
            out[k,height-8-h:height-8,x0:x1]=cols[j]
    return out


def _explicit(elements, ray):
    """ABCD op と独立な、面ごとの y,u 更新。"""
    y,u=map(float,ray); path=[(y,u)]
    for kind,value in elements:
        if kind == "free": y += value*u
        elif kind == "lens": u -= y/value
        else: raise ValueError(kind)
        path.append((y,u))
    return np.array(path)


def _image_crossings(elements, angles=(.017, .031)):
    """軸上物点から出た2光線が free 区間内で再交差する位置を返す。"""
    states=np.array([[0.0,float(u)] for u in angles]); x=0.0; hits=[]
    for kind,value in elements:
        if kind == "free":
            dy=states[0,0]-states[1,0]; du=states[0,1]-states[1,1]
            if abs(du)>1e-15:
                d=-dy/du
                if 1e-10 < d <= value+1e-10: hits.append(x+d)
            states[:,0] += value*states[:,1]; x += value
        elif kind == "lens": states[:,1] -= states[:,0]/value
        else: raise ValueError(kind)
    return np.array(hits)


def _fiber_response(period_um, rng, pitch=PITCH_UM, core_ratio=.8):
    """円形コアで連続正弦を積分し、六角セル再構成像の窓つき DFT で応答を測る。"""
    radius=.5*core_ratio*pitch; phase=.37
    rows,cols=42,84
    centers=[]
    for row in range(rows):
        off=(row&1)*pitch/2
        for col in range(cols): centers.append((col*pitch+off,row*pitch*math.sqrt(3)/2))
    centers=np.asarray(centers); cx=centers[:,0]
    # 固定した高解像の円内格子。値は点標本でなくコア開口の面積平均。
    g=np.linspace(-radius,radius,25); ox,oy=np.meshgrid(g,g)
    ox=ox[(ox*ox+oy*oy)<=radius*radius]
    vals=.5+.42*np.cos(2*np.pi*(cx[:,None]+ox[None,:])/period_um+phase).mean(axis=1)
    vals=np.clip(vals+rng.normal(0,.006,len(vals)),0,1)
    # pitch/8 の画素ごとに最寄りの六角コアを選び、その値で Voronoi セルを塗り戻す。
    step=pitch/8; w=cols*8; h=int((rows-1)*pitch*math.sqrt(3)/2/step)+1
    xx=(np.arange(w)+.5)*step; yy=(np.arange(h)+.5)*step
    best=np.full((h,w),np.inf); index=np.zeros((h,w),int)
    base_r=np.rint(yy/(pitch*math.sqrt(3)/2)).astype(int)
    for dr in (-1,0,1):
        rr=np.clip(base_r+dr,0,rows-1)
        off=(rr&1)*pitch/2
        base_c=np.rint((xx[None,:]-off[:,None])/pitch).astype(int)
        for dc in (-1,0,1):
            cc=np.clip(base_c+dc,0,cols-1)
            dx=xx[None,:]-(cc*pitch+off[:,None]); dy=yy[:,None]-rr[:,None]*(pitch*math.sqrt(3)/2)
            d2=dx*dx+dy*dy; take=d2<best
            best[take]=d2[take]; index[take]=(rr[:,None]*cols+cc)[take]
    recon=vals[index]
    # 各行に Hann 窓を掛け、真のチャート周波数で複素 DFT を1点だけ測る。
    win=np.hanning(w); carrier=np.exp(-2j*np.pi*xx/period_um)
    means=(recon*win).sum(axis=1)/win.sum()
    amps=2*np.abs(((recon-means[:,None])*win*carrier).sum(axis=1))/win.sum()
    measured=float(np.median(amps/means)/.84)       # 入力正弦の Michelson contrast 0.84 で正規化
    # 埋め込み表示は5×5平均で軽量化するが、測定は上の pitch/8 像だけを使う。
    hh=h//5*5; ww=w//5*5; image=recon[:hh,:ww].reshape(hh//5,5,ww//5,5).mean(axis=(1,3))
    image=np.repeat(np.clip(image*255,0,255).astype(np.uint8)[...,None],3,axis=2)
    z=2*np.pi*radius/period_um
    aperture=1.0 if z==0 else abs(2*j1(z)/z)
    # 近似閉形式: 円形コアの jinc × 六角 Voronoi セルと同面積の円の jinc。
    cell_radius=math.sqrt((math.sqrt(3)/2*pitch*pitch)/math.pi)
    zc=2*np.pi*cell_radius/period_um
    reconstruction=1.0 if zc==0 else abs(2*j1(zc)/zc)
    closed=aperture*reconstruction
    return measured,closed,image


def _aperture_area_fraction(A, B, aperture):
    """矩形 |y|<=A, |v|<=B を2本の瞳 |y|,|y+v|<=a で切った厳密な多角形面積。"""
    poly=[(-A,-B),(A,-B),(A,B),(-A,B)]
    planes=[(1,0,aperture),(-1,0,aperture),(1,1,aperture),(-1,-1,aperture)]
    for nx,ny,c in planes:
        out=[]
        for p,q in zip(poly,poly[1:]+poly[:1]):
            fp=nx*p[0]+ny*p[1]-c; fq=nx*q[0]+ny*q[1]-c
            if fp<=0: out.append(p)
            if (fp<=0) != (fq<=0):
                t=fp/(fp-fq); out.append((p[0]+t*(q[0]-p[0]),p[1]+t*(q[1]-p[1])))
        poly=out
    area=.5*abs(sum(p[0]*q[1]-q[0]*p[1] for p,q in zip(poly,poly[1:]+poly[:1])))
    return area/(4*A*B)


def compute():
    stages=np.arange(1,7); image_x=[]; magnification=[]; matrix_error=[]; invariant_error=[]
    for n in stages:
        elements=[]
        for _ in range(n): elements += [("free",2*F),("lens",F),("free",2*F),("lens",F)]
        M=np.asarray(optics.abcd_matrix(elements),float)
        crossings=_image_crossings(elements)
        if len(crossings) != n: raise AssertionError((n,crossings))
        image_x.append(crossings[-1]); magnification.append(M[0,0])
        e0=_explicit(elements,(1.7,.021)); e1=_explicit(elements,(-.8,-.013))
        op0=optics.abcd_trace(M,1.7,21.0)
        matrix_error.append(float(np.max(np.abs(e0[-1]-[op0["height_mm"],op0["angle_mrad"]/1000]))))
        inv=e0[:,0]*e1[:,1]-e1[:,0]*e0[:,1]
        invariant_error.append(float(np.max(np.abs(inv-inv[0]))))

    # Fixed entrance bundle. More relay stages add independent aperture opportunities; nothing is rescaled.
    yy,uu=np.meshgrid(np.linspace(-2.8,2.8,401),np.linspace(-.035,.035,401)); rays=np.column_stack([yy.ravel(),uu.ravel()])
    transmissions=[]; estimates=[]
    for n in stages:
        alive=np.ones(len(rays),bool); state=rays.copy()
        for j in range(n):
            state[:,0] += 2*F*state[:,1]; alive &= np.abs(state[:,0]) <= 2.35
            state[:,1] -= state[:,0]/F
            state[:,0] += 2*F*state[:,1]; alive &= np.abs(state[:,0]) <= 2.35
            state[:,1] -= state[:,0]/F
        transmissions.append(alive.mean())
        # Separate closed area of |Y+2fU| <= aperture for two independent uniforms.
        # The ideal 4f relay repeats the same pupil, so it does not multiply this loss by stage count.
        A,B,a=2.8,2*F*.035,2.35
        one=_aperture_area_fraction(A,B,a)
        estimates.append(one)

    periods=np.linspace(1.45,8.0,28)*PITCH_UM; measured=[]; closed=[]; images=[]; rng=np.random.default_rng(2601)
    for period in periods:
        a,b,im=_fiber_response(period,rng); measured.append(a); closed.append(b); images.append(im)
    measured=np.asarray(measured); closed=np.asarray(closed)
    def cross50(y):
        hit=np.flatnonzero(y>=.5)
        if not len(hit): return float("inf")
        i=int(hit[0])
        if i==0: return float(periods[0])
        return float(np.interp(.5,y[i-1:i+1],periods[i-1:i+1]))
    resolution_um=cross50(measured); closed_resolution_um=cross50(closed)
    return dict(stages=stages,image_x=np.array(image_x),magnification=np.array(magnification),matrix_error=np.array(matrix_error),
                invariant_error=np.array(invariant_error),transmission=np.array(transmissions),estimate=np.array(estimates),
                periods_um=periods,contrast=measured,closed_contrast=closed,fiber_images=np.array(images),
                resolution_um=resolution_um,closed_resolution_um=closed_resolution_um)


def gates(r):
    return {"image_matrix_error":float(r["matrix_error"].max()),"invariant_error":float(r["invariant_error"].max()),
            "vignetting_error":float(np.max(np.abs(r["transmission"]-r["estimate"]))),
            "vignetting_stage_span":float(np.ptp(r["transmission"])),
            "fiber_resolution_um":r["resolution_um"],"fiber_closed_um":r["closed_resolution_um"],
            "fiber_resolution_error_um":abs(r["resolution_um"]-r["closed_resolution_um"])}


def _checks(g, limit=False):
    rows=[
      {"what":T("段ごとの像位置・倍率: 逐次追跡と ABCD op","image position and magnification: sequential trace vs ABCD op"),"criterion":"< 1e-9","result":_e(g["image_matrix_error"]),"ok":g["image_matrix_error"]<1e-9},
      {"what":T("各面のラグランジュ不変量","Lagrange invariant at every surface"),"criterion":"< 1e-9","result":_e(g["invariant_error"]),"ok":g["invariant_error"]<1e-9},
      {"what":T("同じ瞳を繰り返す理想 4f 段の透過率","transmission through repeated identical ideal 4f pupils"),"criterion":"< 1e-12","result":_e(g["vignetting_stage_span"]),"ok":g["vignetting_stage_span"]<1e-12},
      {"what":T("多数光線の透過率と口径面積の閉形式","many-ray transmission vs closed aperture-area form"),"criterion":"< 0.02","result":"%.4f"%g["vignetting_error"],"ok":g["vignetting_error"]<.02},
      {"what":T("合成ファイバ像と円開口閉形式の 50% 周期","50% period: synthetic fibre image vs circular-aperture form"),"criterion":T("ファイバ間隔以内","within one fibre pitch"),"result":"%.1f µm"%g["fiber_resolution_error_um"],"ok":g["fiber_resolution_error_um"]<=PITCH_UM}]
    if limit: rows.append({"what":T("曲げても硬性リレーが像を運ぶ","rigid relay carries an image around a bend"),"criterion":T("曲がった管を通る","passes a bent tube"),"result":T("通らない。ファイバ束にも網目と断線が残る","no; a fibre bundle also retains its grid and broken cores"),"ok":False})
    if limit: rows.append({"what":T("等面積円の近似が Nyquist 付近の折り返しも再現","equal-area-circle approximation reproduces aliasing near Nyquist"),"criterion":T("六角セル形状と折り返しを含む","includes hex-cell shape and aliasing"),"result":T("含まない。50%% 周期差 %.2f µm"%g["fiber_resolution_error_um"],"not included; 50%% period difference %.2f µm"%g["fiber_resolution_error_um"]),"ok":False})
    return rows


def _lesson(q,choices,answer,explain,formula,limit):
    return {"question":q,"choices":choices,"answer":answer,"explain":explain,"formula":formula,"limit":limit}


def build_spec(r,g):
    tube,tf=_box(8,2.4,2.4); lens,lf=_disc(.9); n=len(r["stages"]); tabs=[]
    xyz,q=_poses(n,2); xyz[:,0,0]=0; xyz[:,1,0]=np.linspace(-3,3,n)
    common=[{"name":"tube","pos":tube,"faces":tf,"rgb":[75,85,96],"alpha":.28},{"name":"lens","pos":lens,"faces":lf,"rgb":[80,190,245],"alpha":.55}]
    tabs.append(pv.viewer_anim3d_tab("inside",T("細い管の奥を見る","Looking into a narrow tube"),"passed",T("直径 6 mm の管に対物・リレー・接眼を並べる。各 4f 段が像を次へ渡す。最初の瞳で光束は切られるが、同じ瞳を正確に繰り返す理想模型では段数を増しても追加のケラレはない。","An objective, relays and eyepiece fit in a 6 mm tube. Each 4f stage hands the image onward. The first pupil clips the bundle, but repeating that pupil exactly causes no additional vignetting in the ideal model."),np.arange(n)/12,common,xyz,q,series=[{"label":T("追跡透過率","traced transmission"),"values":r["transmission"],"unit":"","color":"#4fc3f7"}],panes=[{"label":T("対象 → 対物 → リレー段 → 接眼","target → objective → relay stages → eyepiece"),"frames":_band(np.column_stack([np.ones(n),np.ones(n),r["stages"]/6,r["transmission"]]))}],numbers=[pv.viewer_number(T("管の内径","tube bore"),"6.0 mm"),pv.viewer_number(T("6 段後の透過率","transmission after 6 stages"),"%.1f %%"%(100*r["transmission"][-1]))],checks=_checks(g),axis={"values":r["stages"],"segments":[{"k":0,"label":T("リレー段数","relay stages"),"unit":"","decimals":0}]},view={"az":-.7,"el":.35,"dist":1.0},lesson=_lesson(T("同じ理想 4f リレーを足すたび、幾何学的な透過率はさらに下がる?","Does geometric transmission fall again whenever an identical ideal 4f relay is added?"),[T("段ごとに下がる","falls at every stage"),T("最初の瞳以後は一定","stays constant after the first pupil")],1,T("4f 段は同じ光束を同じ瞳へ戻すため、理想模型では最初に通った光線は後段も通る。","A 4f stage returns the same bundle to the same pupil, so rays passing the first pupil pass later ideal stages."),T("4f 段: P(2f) L(f) P(2f) L(f)","4f stage: P(2f) L(f) P(2f) L(f)"),T("実機の反射損失、芯ずれ、収差は段数とともに損失を増やすが、ここでは省いた。","Real reflection loss, decentring and aberrations compound with stage count but are omitted here."))))
    xyz,q=_poses(n,2); xyz[:,0,0]=-2; xyz[:,1,0]=2
    tabs.append(pv.viewer_anim3d_tab("relay",T("像を何度も結び直す","Refocusing the image repeatedly"),"passed",T("青と橙の2本の近軸光線を各レンズ面で更新する。ABCD 行列の結果と逐次追跡が全段で重なる。","Two paraxial rays are updated at every lens surface. The ABCD result and sequential trace overlap through every stage."),np.arange(n)/12,common,xyz,q,series=[{"label":T("倍率","magnification"),"values":r["magnification"],"unit":"×","color":"#ffb74d"},{"label":T("像位置","image position"),"values":r["image_x"],"unit":"mm","color":"#4fc3f7"}],numbers=[pv.viewer_number(T("最大 ABCD 差","maximum ABCD difference"),_e(g["image_matrix_error"])),pv.viewer_number(T("6 段の像位置","image after 6 stages"),"%.0f mm"%r["image_x"][-1])],checks=_checks(g),axis={"values":r["stages"],"segments":[{"k":0,"label":T("段数","stages"),"unit":"","decimals":0}]},view={"az":-.8,"el":.4,"dist":.9},lesson=_lesson(T("同じ 4f リレーを足すと倍率は積み上がる?","Does magnification accumulate when identical 4f relays are added?"),[T("毎段で2倍","doubles each stage"),T("1倍のまま","stays at 1×")],1,T("この配置の各段の行列は単位行列で、像だけを次へ送る。","Each stage has the identity matrix in this layout, passing the image onward."),T("[y',u']ᵀ = M[y,u]ᵀ","[y',u']ᵀ = M[y,u]ᵀ"),T("実レンズの厚さと収差を含めると完全一致ではない。","Real lens thickness and aberrations prevent perfect agreement."))))
    xyz,q=_poses(n,1)
    tabs.append(pv.viewer_anim3d_tab("invariant",T("細さ・視野・明るさの交換","Trading diameter, field and brightness"),"passed",T("ラグランジュ不変量は各面で同じ。細い管で視野を広げれば、通せる角度幅が減り、周辺光線が口径に切られる。多数光線との差は有限な 401×401 格子で面積を数えた離散化誤差。","The Lagrange invariant is unchanged at every surface. In a narrow tube, widening the field reduces the angular range that passes, so apertures clip marginal rays. The many-ray difference is finite-grid error from counting area on a 401×401 grid."),np.arange(n)/12,[common[0]],xyz,q,series=[{"label":T("追跡透過率","traced transmission"),"values":r["transmission"],"unit":"","color":"#66bb6a"},{"label":T("口径面積の閉形式","closed aperture-area form"),"values":r["estimate"],"unit":"","color":"#ffb74d"}],panes=[{"label":T("固定した入射光束を、同じ口径で段ごとに数える","counting one fixed incident bundle through the same aperture at every stage"),"frames":_band(np.column_stack([r["transmission"],r["estimate"],1-r["transmission"],r["stages"]/6]))}],numbers=[pv.viewer_number(T("不変量の最大残差","maximum invariant residual"),_e(g["invariant_error"])),pv.viewer_number(T("有限格子と閉形式の差","finite-grid versus closed-form difference"),"%.4f"%g["vignetting_error"])],checks=_checks(g),axis={"values":r["stages"],"segments":[{"k":0,"label":T("段数","stages"),"unit":"","decimals":0}]},view={"az":-.65,"el":.3,"dist":1.0},lesson=_lesson(T("管を細くしたまま視野を広げると、同じ明るさを保てる?","Can brightness stay unchanged while field widens in the same narrow tube?"),[T("保てる","yes"),T("周辺光が減る","marginal light falls")],1,T("像高と光線角の積には上限があり、口径を越えた光線はケラレる。","The product of image height and ray angle is bounded; rays beyond the aperture vignette."),T("H = y₁u₂ − y₂u₁ = constant","H = y₁u₂ − y₂u₁ = constant"),T("照明の不均一と反射率は含めない。","Illumination nonuniformity and reflectance are omitted."))))
    m=len(r["periods_um"]); xyz,q=_poses(m,1)
    tabs.append(pv.viewer_anim3d_tab("fiber",T("曲がる管とファイバ束の限界","Bent tubes and fibre-bundle limits"),"limit",T("連続正弦チャートを直径 0.8p の円形コアで面積積分し、固定雑音を加えて六角セルへ塗り戻す。位相を格子からずらし、pitch/8 の再構成像に行別 Hann 窓を掛け、真の周波数の DFT 振幅から MTF を測る。","A continuous sine chart is area-integrated over circular cores of diameter 0.8p, given fixed noise, and painted into hexagonal cells. Its phase is offset; MTF is measured from a one-point DFT at the true frequency after a row-wise Hann window on the pitch/8 reconstruction."),np.arange(m)/12,[{"name":"bundle","pos":tube,"faces":tf,"rgb":[80,135,105],"alpha":.35}],xyz,q,series=[{"label":T("合成像から測った MTF","MTF measured from the synthetic image"),"values":r["contrast"],"unit":"","color":"#ffca28","threshold":.5},{"label":T("円開口と等面積セルの jinc 近似","jinc approximation for core and equal-area cell"),"values":r["closed_contrast"],"unit":"","color":"#4fc3f7"}],panes=[{"label":T("円形コアで積分し、ハニカムへ再構成した像","image integrated by circular cores and reconstructed on the honeycomb"),"frames":r["fiber_images"],"png":True,"wide":True}],numbers=[pv.viewer_number(T("測った 50% 周期","measured 50% period"),"%.1f µm"%g["fiber_resolution_um"]),pv.viewer_number(T("近似式の 50% 周期","approximate-form 50% period"),"%.1f µm"%g["fiber_closed_um"])],checks=_checks(g,True),axis={"values":r["periods_um"],"segments":[{"k":0,"label":T("正弦周期","sine period"),"unit":"µm","decimals":0}]},view={"az":-.85,"el":.45,"dist":.9},lesson=_lesson(T("曲がるファイバ束なら、硬性リレーと同じ像を運べる?","Can a flexible fibre bundle carry the same image as a rigid relay?"),[T("完全に同じ","identically"),T("芯の間隔と断線が残る","core pitch and breaks remain")],1,T("円形コアの平均化と六角格子の Nyquist 限界が細部を落とす。近似式はコアの jinc と、六角セルと同面積の円の jinc の積。Nyquist 付近の差はセル形状と折り返しを円近似が表せない限界。","Circular-core averaging and the hexagonal grid's Nyquist limit remove detail. The approximation multiplies the core jinc by the jinc of a circle equal in area to one hexagonal cell; near Nyquist it misses cell shape and aliasing."),T("MTF ≈ jinc(core) × jinc(equal-area cell)","MTF ≈ jinc(core) × jinc(equal-area cell)"),T("硬性リレーは曲がらない。ファイバ束は曲がるが、網目・クロストーク・断線が限界。","A rigid relay cannot bend. A fibre bundle bends, but its grid, crosstalk and broken cores are limits."))))
    return pv.viewer_spec("borescope",T("ボアスコープは細い管の奥をどう見るか","How a borescope sees through a narrow tube"),T("リレー結像、光学不変量、ケラレ、ファイバ束を同じ模型で比べる","Compare relay imaging, optical invariant, vignetting and a fibre bundle in one model"),T("①問い → ②予想 → ③再生 → ④式 → ⑤限界。3-D はドラッグで回せる。","Follow ① question → ② prediction → ③ play → ④ formula → ⑤ limit. Drag to rotate the 3-D view."),tabs,credit=T("管、レンズ、点検対象、ファイバ像はすべて合成。寸法は説明用の仮定で、特定の製品を表さない。","Tube, lenses, inspection target and fibre image are entirely synthetic. Dimensions are explanatory assumptions and represent no specific product."))


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument("--check",action="store_true"); ap.add_argument("--out",default=str(OUT_HTML)); a=ap.parse_args(argv)
    r=compute(); g=gates(r)
    for k,v in g.items(): print("%-28s %s"%(k,v))
    spec=build_spec(r,g)
    if a.check: print("ok: %d bytes (not written)"%len(pv._build_html(spec,list(LANGS)).encode())); return 0
    path=pv.write_viewer(spec,a.out,list(LANGS)); print("wrote %s (%d bytes)"%(path,Path(path).stat().st_size)); return 0


if __name__ == "__main__": raise SystemExit(main())
