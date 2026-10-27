# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""トンネル覆工のひびを走行撮影して測る、動く 3-D 学習ページ。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import fullseye as fs
import pocviewer as pv

OUT_HTML = ROOT / "docs" / "view2026" / "anim3d" / "tunnel_crack_anim3d.html"
LANGS = ("ja", "en")
PIXEL_MM = np.round(np.arange(1.0, 0.099, -0.05), 2)
TRUE_WIDTH_MM = 0.20
EXTENT_MM = 25.6
FRANGI_THRESHOLD = 0.30
DETECT_MIN_FILL = 0.80


def T(ja, en):
    return pv.viewer_text(ja, en)


def _e(x):
    return "< 1e-12" if abs(float(x)) < 1e-12 else "%.3g" % float(x)


def _truth(n=256):
    """Fixed-size wall and off-centre curved crack, sampled on a 0.1 mm grid."""
    yy, xx = np.mgrid[:n, :n]
    x = (xx + 0.5) * EXTENT_MM / n
    y = (yy + 0.5) * EXTENT_MM / n
    centre = 8.137 + 2.15 * np.sin((y - 1.3) / 4.1) + 0.035 * y
    dist = np.abs(x - centre)
    crack = np.clip(1.0 - dist / TRUE_WIDTH_MM, 0.0, 1.0)
    valid = (y > 1.2) & (y < 24.3)
    joint = np.abs(y - 18.45) < 0.12
    stain = ((x - 18.2) ** 2 / 10.0 + (y - 9.1) ** 2 / 5.5) < 1.0
    texture = 0.035*np.sin(.73*x + .31*y) + 0.025*np.sin(1.27*x - .19*y)
    illumination = 0.09*np.cos((x-12.8)/13.0*np.pi)
    rng = np.random.default_rng(20261027)
    noise = rng.normal(0, .018, x.shape)
    background = .72 + texture + illumination - .38*joint - .12*stain + noise
    image = background - .43*crack*valid
    return np.clip(image, 0, 1), np.clip(background, 0, 1), valid & (dist < .16), joint, stain


def _sample(image, pixel_mm):
    # Sensor cells are anchored in physical coordinates; 25.6 mm need not be
    # divisible by their pitch (notably 1.0 mm).  Aggregate and expand by ids.
    ids = np.floor((np.arange(256)+.5)*.1/pixel_mm).astype(int)
    nc = int(ids.max()+1)
    labels = ids[:,None]*nc + ids[None,:]
    sums = np.bincount(labels.ravel(), weights=image.ravel(), minlength=nc*nc)
    counts = np.bincount(labels.ravel(), minlength=nc*nc)
    small = (sums/counts).reshape(nc,nc)
    return small[ids[:,None],ids[None,:]]


def _length(mask, pixel_mm=.1):
    sk = np.asarray(fs.apply(mask.astype(float), "sk_skeleton")) > .5
    # Pixel-centre polyline estimator. Diagonal links receive sqrt(2).
    h = np.count_nonzero(sk[:, 1:] & sk[:, :-1])
    v = np.count_nonzero(sk[1:, :] & sk[:-1, :])
    d1 = np.count_nonzero(sk[1:, 1:] & sk[:-1, :-1])
    d2 = np.count_nonzero(sk[1:, :-1] & sk[:-1, 1:])
    return pixel_mm * (h + v + .5*np.sqrt(2)*(d1+d2))


def compute():
    base, _background, truth, joint, stain = _truth()
    truth_len = _length(truth)
    images=[]; response=[]; masks=[]; skeleton=[]; recalls=[]; false_lengths=[]; widths=[]
    for p in PIXEL_MM:
        im = _sample(base, p)
        fr = np.asarray(fs.apply(im, "sk_frangi", a=.2, b=.45), float)
        # A fixed detector threshold: resolution changes, the physical field does not.
        mask = fr > FRANGI_THRESHOLD
        sk = np.asarray(fs.apply(mask.astype(float), "sk_skeleton")) > .5
        near = np.zeros_like(truth)
        for dx in range(-3, 4):
            near |= np.roll(truth, dx, axis=1)
        hit = sk & near
        false = sk & ~near
        valid_rows=truth.any(axis=1)
        recall=float(np.mean(hit.any(axis=1)[valid_rows]))
        # Follow the detected skeleton, not the planted curve.  For each row,
        # choose the strongest skeleton response near the previous row.  The
        # local background comes only from two flanks in this same observed
        # image; texture, noise and illumination therefore remain in the fit.
        centres=np.full(256,np.nan); previous=None
        search=max(12,int(round(p/.1))*2)
        for row in range(12,244):
            candidates=np.flatnonzero(sk[row])
            if previous is not None:
                candidates=candidates[np.abs(candidates-previous)<=search]
            if len(candidates):
                j=int(candidates[np.argmax(fr[row,candidates])])
                centres[row]=j; previous=j
        vals=[]; bg_sigma=[]
        for row in range(20,236):
            if not np.isfinite(centres[row]): continue
            j=int(centres[row])
            if j<14 or j>241: continue
            flanks=np.r_[im[row,j-12:j-5],im[row,j+6:j+13]]
            local=float(np.median(flanks))
            bg_sigma.append(1.4826*float(np.median(np.abs(flanks-local))))
            vals.append(np.sum(np.clip(local-im[row,j-4:j+5],0,None))*.1/.43)
        images.append(im); response.append(fr); masks.append(mask); skeleton.append(sk)
        recalls.append(recall); false_lengths.append(_length(false)); widths.append(float(np.median(vals)))
        if p == PIXEL_MM[-1]: best_bg_sigma=float(np.median(bg_sigma)); best_width_rows=len(vals)
    # 49 animation frames interpolate only the display; all gates use the four detector trials above.
    idx=np.rint(np.linspace(0,len(PIXEL_MM)-1,49)).astype(int)
    panes=np.empty((49,96,256,3),np.uint8)
    for k,i in enumerate(idx):
        gray=np.asarray(images[i][80:176]*255,np.uint8)
        panes[k]=np.repeat(gray[...,None],3,2)
        panes[k,skeleton[i][80:176],0]=255; panes[k,skeleton[i][80:176],1]=91; panes[k,skeleton[i][80:176],2]=72
    recalls=np.array(recalls); false_lengths=np.array(false_lengths); widths=np.array(widths)
    qualifying=np.flatnonzero(recalls>=.90)
    measured_90=float(PIXEL_MM[qualifying[0]]) if len(qualifying) else float("nan")
    estimate_90=TRUE_WIDTH_MM/DETECT_MIN_FILL
    return dict(base=base,truth=truth,joint=joint,stain=stain,images=images,response=response,masks=masks,
                skeleton=skeleton,recall=recalls,false_length=false_lengths,width=widths,truth_length=truth_len,
                measured_90=measured_90,estimate_90=estimate_90,idx=idx,panes=panes,
                best_bg_sigma=best_bg_sigma,best_width_rows=best_width_rows)


def gates(r):
    best=-1
    p=float(PIXEL_MM[best]); sigma=float(r["best_bg_sigma"])
    # One-pixel quantisation plus noise in nine core samples and uncertainty
    # of the median of fourteen background-flank samples.
    quant=p/np.sqrt(12)
    core_noise=sigma*np.sqrt(9)*.1/.43
    background_noise=1.253*sigma/np.sqrt(14)*9*.1/.43
    width_limit=float(np.sqrt(quant**2+core_noise**2+background_noise**2))
    step=float(abs(PIXEL_MM[1]-PIXEL_MM[0])); nrows=int(np.count_nonzero(r["truth"].any(axis=1)))
    recall_se=float(np.sqrt(.9*.1/nrows))
    q=np.flatnonzero(r["recall"]>=.9)[0]
    slope=abs(float(r["recall"][q]-r["recall"][q-1]))/step
    threshold_limit=step/2 + recall_se/max(slope,1e-12)
    return {"recall_best":float(r["recall"][best]), "false_best_mm":float(r["false_length"][best]),
            "width_error_mm":abs(float(r["width"][best])-TRUE_WIDTH_MM), "width_limit_mm":width_limit,
            "measured_90_mm":float(r["measured_90"]), "estimated_90_mm":float(r["estimate_90"]),
            "threshold_delta_mm":abs(float(r["measured_90"])-float(r["estimate_90"])),
            "threshold_limit_mm":threshold_limit,"recall_se":recall_se,"resolution_step_mm":step}


def _box(sx,sy,sz):
    p=np.array([[x,y,z] for x in (-sx/2,sx/2) for y in (-sy/2,sy/2) for z in (-sz/2,sz/2)],float)
    f=np.array([[0,1,3],[0,3,2],[4,6,7],[4,7,5],[0,4,5],[0,5,1],[2,3,7],[2,7,6],[0,2,6],[0,6,4],[1,5,7],[1,7,3]])
    return p,f


def _tunnel(nz=18, nt=24):
    verts=[]
    for z in np.linspace(-4,4,nz):
        for th in np.linspace(-1.35,1.35,nt):
            verts.append([3*np.sin(th),3*np.cos(th),z])
    faces=[]
    for z in range(nz-1):
        for t in range(nt-1):
            a=z*nt+t; faces += [[a,a+nt,a+nt+1],[a,a+nt+1,a+1]]
    return np.array(verts),np.array(faces)


def _crack_ribbon(n=48):
    verts=[]
    for z in np.linspace(-3.6,3.6,n):
        th=-.34+.055*np.sin(1.5*z)+.012*z
        for d in (-.012,.012):
            a=th+d; verts.append([3.012*np.sin(a),3.012*np.cos(a),z])
    faces=[]
    for k in range(n-1): faces += [[2*k,2*k+2,2*k+3],[2*k,2*k+3,2*k+1]]
    return np.array(verts),np.array(faces)


def _lesson(q, choices, answer, explain, formula, limit):
    return {"question":q,"choices":choices,"answer":answer,"explain":explain,"formula":formula,"limit":limit}


def _checks(g, limit=False):
    rows=[
      {"what":T("0.10 mm/画素で拾った真のひび長さ","true crack length recovered at 0.10 mm/pixel"),"criterion":">= 90 %","result":"%.1f %%"%(100*g["recall_best"]),"ok":g["recall_best"]>=.90},
      {"what":T("面積欠けから求めた幅の誤差","width error from integrated darkness"),"criterion":"< %.3f mm"%g["width_limit_mm"],"result":"%.3f mm"%g["width_error_mm"],"ok":g["width_error_mm"]<g["width_limit_mm"]},
      {"what":T("90 % 到達解像度: 実測と幅からの見積り","90% resolution: measured vs width estimate"),"criterion":"< %.3f mm"%g["threshold_limit_mm"],"result":"%.2f vs %.2f mm/pixel"%(g["measured_90_mm"],g["estimated_90_mm"]),"ok":g["threshold_delta_mm"]<g["threshold_limit_mm"]}]
    if limit:
        rows.append({"what":T("汚れ・目地・水しみをひびと区別できる","stains, joints and damp patches are always separable from cracks"),"criterion":T("誤検出長 0 mm","false-positive length 0 mm"),"result":"%.2f mm"%g["false_best_mm"],"ok":False})
    return rows


def build_spec(r,g):
    n=49; tunnel,tf=_tunnel(); crack,kf=_crack_ribbon(); car,cf=_box(.8,1.0,.7); line,lf=_box(5.0,.025,.08)
    xyz=np.zeros((n,4,3)); quat=np.zeros((n,4,4)); quat[...,0]=1
    xyz[:,1,2]=np.linspace(-3.2,3.2,n); xyz[:,1,1]=.2; xyz[:,2,2]=xyz[:,1,2]; xyz[:,2,1]=1.7
    bodies=[{"name":"tunnel lining","pos":tunnel,"faces":tf,"rgb":[116,126,132],"alpha":.72},
            {"name":"inspection vehicle","pos":car,"faces":cf,"rgb":[240,176,54]},
            {"name":"line camera field","pos":line,"faces":lf,"rgb":[72,220,255],"alpha":.42},
            {"name":"planted crack","pos":crack,"faces":kf,"rgb":[255,70,62]}]
    t=np.arange(n)/24; px=PIXEL_MM[r["idx"]]; rec=r["recall"][r["idx"]]; wid=r["width"][r["idx"]]
    common=dict(t=t,bodies=bodies,xyz=xyz,quat=quat,panes=[{"label":T("展開画像: 赤は検出骨格","unwrapped image: red is detected skeleton"),"frames":r["panes"],"png":True,"wide":True}],axis={"values":px,"segments":[{"k":0,"label":T("地上画素寸法","wall sampling"),"unit":"mm/pixel","decimals":2}]},view={"az":-.55,"el":.22,"dist":1.15,"target":[0,1,0]})
    tabs=[]
    tabs.append(pv.viewer_anim3d_tab("unwrap",T("走行撮影を壁の展開図へ","From a moving scan to an unwrapped wall"),"passed",T("円筒内面と車両を式から作り、同じ実寸 25.6 mm の壁を解像度だけ変えて撮る。ひびの中心は画素中心から外し、模様・雑音・照明むらを加えた。","A formula-built cylindrical lining and vehicle scan the same fixed 25.6 mm wall at different resolutions. The crack lies off pixel centres, with texture, noise and uneven lighting."),series=[{"label":T("ひび長さ再現率","crack-length recall"),"values":rec,"unit":"","color":"#ef5350"}],checks=_checks(g),lesson=_lesson(T("1 mm/画素で幅 0.2 mm のひびは線として残る?","Does a 0.2 mm crack remain a line at 1 mm/pixel?"),[T("ほぼ全部残る","almost all remains"),T("平均化され、多くを失う","averaging loses much of it")],1,T("画素内で暗さが平均され、細いひびのコントラストは幅/画素寸法に比例して下がる。","Pixel averaging reduces a thin crack's contrast in proportion to width divided by pixel size."),T("contrast ≈ crack width / pixel size","contrast ≈ crack width / pixel size"),T("合成覆工であり、実トンネルの保守判定には使わない。","This synthetic lining is not for real maintenance decisions.")),**common))
    tabs.append(pv.viewer_anim3d_tab("resolution",T("解像度で拾える長さが変わる","Resolution changes recovered length"),"passed",T("各撮像像を sk_frangi で線強調し、固定しきい値 0.30 で二値化、sk_skeleton で細線化した。真値近傍の骨格長だけを再現率に数える。0.05 mm 刻みで 90 % を初めて超える点を実測する。","Each sampled image runs through sk_frangi, a fixed 0.30 threshold and sk_skeleton. Only skeleton length near planted truth counts toward recall. Trials at 0.05 mm steps measure the first point above 90%."),series=[{"label":T("検出した真の長さ","recovered true length"),"values":rec,"unit":"","color":"#66bb6a"},{"label":T("目標 90 %","90% target"),"values":np.full(n,.9),"unit":"","color":"#ffee58"}],checks=_checks(g),lesson=_lesson(T("90 % を初めて超える解像度は?","Which resolution first exceeds 90%?"),[T("1.0 mm/画素","1.0 mm/pixel"),T("0.25 mm/画素","0.25 mm/pixel")],1,T("固定 Frangi 尺度としきい値 0.30 の予備走査から、画素内のひび充填率 0.80 を検出目安とした。幅 0.20 / 0.80 = 0.25 mm/画素。比較基準は 0.05 mm 刻みの半分と、有限なひび行数による再現率の標準誤差を局所勾配で解像度へ換算した値の和。","A pilot scan with fixed Frangi scale and threshold 0.30 sets a detectable pixel fill ratio of 0.80: width 0.20 / 0.80 = 0.25 mm/pixel. The comparison tolerance adds half the 0.05 mm step to the finite-row recall standard error converted to resolution by the local slope."),T("estimated pixel = crack width / minimum fill = 0.20 / 0.80","estimated pixel = crack width / minimum fill = 0.20 / 0.80"),T("Frangi の尺度やしきい値を変えると、充填率 0.80 と到達解像度も変わる。","Changing Frangi scale or threshold changes the 0.80 fill criterion and the crossing resolution.")),**common))
    tabs.append(pv.viewer_anim3d_tab("width",T("画素より細い幅を暗さから読む","Read subpixel width from darkness"),"passed",T("真の曲線は使わず、検出骨格の各行で前行に近い最大応答を追う。その両脇 14 画素の中央値を局所背景とし、中央 9 画素で失われた明るさを積分する。模様・雑音・照明むらは観測像に残る。","Without using the planted curve, each row follows the strongest detected-skeleton response near the previous row. The median of 14 flank pixels estimates local background, and missing brightness is integrated over nine central pixels. Texture, noise and uneven lighting remain in the observation."),series=[{"label":T("像から推定した幅","width estimated from image"),"values":wid,"unit":"mm","color":"#42a5f5"},{"label":T("埋めた真値","planted truth"),"values":np.full(n,TRUE_WIDTH_MM),"unit":"mm","color":"#ef5350"}],checks=_checks(g),lesson=_lesson(T("1画素未満の幅は必ず 0 と測られる?","Must a subpixel width measure as zero?"),[T("0 になる","it becomes zero"),T("暗さの面積から推定できる","integrated darkness can estimate it")],1,T("線が細いほど一画素の暗さは浅いが、欠けた明るさの面積は幅を保つ。幅の基準は画素量子化、中央9画素の雑音、両脇14画素の背景中央値のばらつきから合成した。","A thinner line makes a shallower pixel, while integrated missing brightness preserves width. The width criterion combines pixel quantisation, noise in nine core pixels and uncertainty of the 14-pixel flank median."),T("width ≈ Σ(local flank median − intensity) · pixel / contrast","width ≈ Σ(local flank median − intensity) · pixel / contrast"),T("背景推定、ぼけ、反射率がずれると幅に偏りが出る。","Background estimation, blur and reflectance can bias width.")),**common))
    tabs.append(pv.viewer_anim3d_tab("limit",T("目地や汚れも線に見える","Joints and stains also look like lines"),"limit",T("同じ画像に横目地と水しみを埋めた。線検出器は意味を知らないため、細線化後にも真のひびから離れた骨格が残る。","A transverse joint and damp patch share the image. The line detector knows no semantics, leaving skeleton away from the true crack."),series=[{"label":T("誤検出の骨格長","false-positive skeleton length"),"values":r["false_length"][r["idx"]],"unit":"mm","color":"#ffb74d"}],checks=_checks(g,True),lesson=_lesson(T("細い暗線なら全部ひびと呼べる?","Can every thin dark line be called a crack?"),[T("呼べる","yes"),T("目地・汚れとの識別が要る","joints and stains must be separated")],1,T("形だけでは目地や汚れも応答する。材質、時系列、別照明など追加の観測が要る。","Shape alone also responds to joints and stains; material, time-series or alternate illumination cues are needed."),T("false length = skeleton length outside truth tolerance","false length = skeleton length outside truth tolerance"),T("限界を見せる行は意図的に不合格。誤検出を隠さない。","The limit row intentionally fails so false positives remain visible.")),**common))
    return pv.viewer_spec("tunnel_crack",T("走りながらトンネルの 0.2 mm ひびを測る","Measuring a 0.2 mm tunnel crack while moving"),T("固定実寸の合成壁で、解像度・検出長・サブピクセル幅を結ぶ","A fixed-size synthetic wall links resolution, detected length and subpixel width"),T("①問い → ②予想 → ③再生 → ④式 → ⑤限界。バッジを押すと計算した門を見る。","Follow ① question → ② prediction → ③ play → ④ formula → ⑤ limit. Tap a badge for computed gates."),tabs,credit=T("すべて合成。覆工、ひび、撮像寸法は説明用の仮定で、事業者・路線・製品を表さない。","Entirely synthetic. Lining, crack and imaging dimensions are teaching assumptions and represent no operator, route or product."))


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__.splitlines()[0]); ap.add_argument("--check",action="store_true"); ap.add_argument("--out",default=str(OUT_HTML)); a=ap.parse_args(argv)
    r=compute(); g=gates(r); spec=build_spec(r,g)
    if a.check:
        print("recall %.3f false %.2f mm width_error %.4f mm threshold %.2f mm/pixel"%(g["recall_best"],g["false_best_mm"],g["width_error_mm"],g["measured_90_mm"]))
        return 0
    pv.write_viewer(spec,a.out,lang="ja"); print(a.out); return 0


if __name__ == "__main__":
    raise SystemExit(main())
