# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""錠剤の欠け・割れ・色むら・異物を画素と色差で測る動く 3-D 学習ページ。"""
from __future__ import annotations

import argparse
import math
import statistics
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import blob2d
import fullseye as fs
import imgmetrics
import pocviewer as pv

OUT_HTML = ROOT / "docs" / "view2026" / "anim3d" / "tablet_inspection_anim3d.html"
LANGS = ("ja", "en")
N = 33
PITCH_MM = 0.08
NOISE_SIGMA = 0.08
DEFECT_CONTRAST = 0.20


def T(ja, en):
    return pv.viewer_text(ja, en)


def _e(x):
    return "< 1e-12" if abs(float(x)) < 1e-12 else "%.3g" % float(x)


def _uv_ellipsoid(rx=1.0, ry=1.0, rz=.35, nu=24, nv=10):
    p = [[0, 0, rz]]
    for j in range(1, nv):
        v = math.pi * j / nv
        for i in range(nu):
            u = 2 * math.pi * i / nu
            p.append([rx*math.sin(v)*math.cos(u), ry*math.sin(v)*math.sin(u), rz*math.cos(v)])
    p.append([0, 0, -rz]); bot = len(p)-1; f=[]
    for i in range(nu): f.append([0, 1+i, 1+(i+1)%nu])
    for j in range(nv-2):
        a=1+j*nu; b=a+nu
        for i in range(nu):
            q=(i+1)%nu; f.extend([[a+i,b+i,b+q],[a+i,b+q,a+q]])
    a=1+(nv-2)*nu
    for i in range(nu): f.append([a+i, bot, a+(i+1)%nu])
    return np.asarray(p,float), np.asarray(f,int)


def _poses(n, positions):
    xyz=np.repeat(np.asarray(positions,float)[None,:,:],n,axis=0)
    q=np.zeros((n,len(positions),4),float); q[...,0]=1
    return xyz,q


def _disk_mask(h, w, row, col, radius):
    yy,xx=np.ogrid[:h,:w]
    return (yy-row)**2+(xx-col)**2 <= radius**2


def _tray_frame(chip_px=0, colour_de=0.0, speck_px=0, light_deg=45.0):
    """既知の真値を持つ 4 錠のカメラ像。表示と op 入力を同じ配列から作る。"""
    h,w=120,240; yy,xx=np.mgrid[:h,:w]
    rgb=np.full((h,w,3),.12,float)
    centres=[(34,48),(34,132),(86,62),(84,166)]
    radii=[23,22,21,24]
    cols=np.array([[.82,.70,.45],[.68,.82,.72],[.78,.72,.84],[.86,.70,.57]])
    for (r,c),rad,col in zip(centres,radii,cols):
        m=(yy-r)**2+(xx-c)**2<=rad**2
        shade=np.clip(1-.008*np.sqrt((yy-r)**2+(xx-c)**2),.72,1)
        rgb[m]=col*shade[m,None]
    # 欠け: 1 錠目の右縁を背景へ戻す。真値は切り欠き円の半径。
    if chip_px:
        m=_disk_mask(h,w,34,48+23,int(chip_px)); rgb[m]=.12
    # 色むら: 3 錠目の局所パッチ。表示強度だけを ΔE のつまみに連動。
    m=_disk_mask(h,w,82,62,8)
    rgb[m]=np.clip(rgb[m]+np.array([.008,-.004,.006])*colour_de,0,1)
    # 異物: 4 錠目の暗点。
    if speck_px:
        m=_disk_mask(h,w,84,166,int(speck_px)); rgb[m]=.05
    # 浅い割れ: 2 錠目。照明方向と直交するとコントラストが消える。
    contrast=.16*abs(math.sin(math.radians(light_deg)))
    crack=(abs(xx-132)<1.2)&(abs(yy-34)<15)
    rgb[crack]=np.clip(rgb[crack]-contrast,0,1)
    return np.uint8(np.round(rgb*255))


def _de00_direct(a, b):
    """CIEDE2000 のスカラー式。imgmetrics と独立に門を作る。"""
    L1,a1,b1=map(float,a); L2,a2,b2=map(float,b)
    C1=math.hypot(a1,b1); C2=math.hypot(a2,b2); cb=(C1+C2)/2
    G=.5*(1-math.sqrt(cb**7/(cb**7+25**7)))
    ap1=(1+G)*a1; ap2=(1+G)*a2; cp1=math.hypot(ap1,b1); cp2=math.hypot(ap2,b2)
    hp1=math.degrees(math.atan2(b1,ap1))%360; hp2=math.degrees(math.atan2(b2,ap2))%360
    dL=L2-L1; dC=cp2-cp1; dh=hp2-hp1
    if cp1*cp2==0: dh=0
    elif dh>180: dh-=360
    elif dh<-180: dh+=360
    dH=2*math.sqrt(cp1*cp2)*math.sin(math.radians(dh/2))
    lb=(L1+L2)/2; cp=(cp1+cp2)/2
    if cp1*cp2==0: hp=hp1+hp2
    elif abs(hp1-hp2)<=180: hp=(hp1+hp2)/2
    elif hp1+hp2<360: hp=(hp1+hp2+360)/2
    else: hp=(hp1+hp2-360)/2
    tr=(1-.17*math.cos(math.radians(hp-30))+.24*math.cos(math.radians(2*hp))
        +.32*math.cos(math.radians(3*hp+6))-.20*math.cos(math.radians(4*hp-63)))
    sl=1+.015*(lb-50)**2/math.sqrt(20+(lb-50)**2); sc=1+.045*cp; sh=1+.015*cp*tr
    rt=-2*math.sqrt(cp**7/(cp**7+25**7))*math.sin(math.radians(60*math.exp(-((hp-275)/25)**2)))
    return math.sqrt((dL/sl)**2+(dC/sc)**2+(dH/sh)**2+rt*(dC/sc)*(dH/sh))


def compute():
    # 欠陥位置: サブピクセル真値と撮像雑音を持つ像を Otsu で分け、最大連結成分を
    # area_center の公開 op で測る。孤立した雑音点を異物として数えないための選択である。
    h=w=51; truth=(25.37,27.62); yy,xx=np.mgrid[:h,:w]
    rng=np.random.default_rng(2601027)
    image=.7+rng.normal(0,NOISE_SIGMA,(h,w))
    particle=(yy-truth[0])**2+(xx-truth[1])**2<=7**2
    image[particle]-=DEFECT_CONTRAST
    reg=fs.apply(.7-image,"otsu")
    labels,nlabels=ndimage.label(reg)
    sizes=np.bincount(labels.ravel()); sizes[0]=0
    particle_region=labels==int(np.argmax(sizes))
    ac=np.asarray(fs.apply(particle_region,"area_center"),float)
    location_error=float(math.hypot(ac[1]-truth[0],ac[2]-truth[1]))
    # 欠けなし 800 像と欠けあり 800 像を面積ごとに独立合成する。既知形状の窓で
    # 平均コントラストを測り、欠けなしの上位 1 % をしきい値にする。
    trials=800; areas=np.arange(1,16); rates=[]; false_rates=[]; thresholds=[]
    rng=np.random.default_rng(2601026)
    cy,cx=15.37,16.62; py,px=np.mgrid[:31,:31]
    order=np.argsort(((py-cy)**2+(px-cx)**2).ravel())
    for area in areas:
        rr,cc=np.unravel_index(order[:area],(31,31))
        clean=.7+rng.normal(0,NOISE_SIGMA,(trials,31,31))
        defect=.7+rng.normal(0,NOISE_SIGMA,(trials,31,31))
        defect[:,rr,cc]-=DEFECT_CONTRAST
        null_score=.7-clean[:,rr,cc].mean(axis=1)
        defect_score=.7-defect[:,rr,cc].mean(axis=1)
        threshold=float(np.quantile(null_score,.99,method="higher"))
        thresholds.append(threshold)
        false_rates.append(float(np.mean(null_score>=threshold)))
        rates.append(float(np.mean(defect_score>=threshold)))
    rates=np.asarray(rates); false_rates=np.asarray(false_rates)
    measured_area=int(areas[np.flatnonzero(rates>=.90)[0]])
    # 片側 1 % 誤検出 + 90 % 検出の正規近似。実測とは独立な閉形式。
    normal=statistics.NormalDist()
    z_alpha=normal.inv_cdf(.99); z_power=normal.inv_cdf(.90)
    formula_area=int(math.ceil(((z_alpha+z_power)*NOISE_SIGMA/DEFECT_CONTRAST)**2))
    # 公開 blob op を実際の分離円板で通す。
    blobs=np.zeros((100,180),bool)
    for rc in [(28,30),(28,85),(28,140),(72,57),(72,116)]: blobs|=_disk_mask(*blobs.shape,*rc,12)
    blob_result=blob2d.blob_count_interval(blobs, rel_lo=.05, rel_hi=.15, min_prominence=1)
    lab1=np.array([50.,2.6772,-79.7751]); lab2=np.array([50.,0.,-82.7485])
    de_op=float(imgmetrics.delta_e_2000(lab1,lab2)); de_direct=_de00_direct(lab1,lab2)
    angles=np.linspace(0,90,N); crack_contrast=.16*np.abs(np.sin(np.radians(angles)))
    chip=np.sqrt(areas/math.pi); des=np.linspace(8,0,N); speck=np.linspace(7,1,N)
    tray=np.array([_tray_frame(chip_px=4) for _ in range(N)])
    chip_frames=np.array([_tray_frame(chip_px=max(1,int(round(x)))) for x in chip])
    colour_frames=np.array([_tray_frame(colour_de=x) for x in des])
    light_frames=np.array([_tray_frame(speck_px=3,light_deg=x) for x in angles])
    return dict(location_error=location_error, location_truth=truth, formula_area=formula_area, measured_area=measured_area,
        min_area_mm2=formula_area*PITCH_MM**2, blob_result=blob_result, de_op=de_op,
        de_direct=de_direct, de_error=abs(de_op-de_direct), angles=angles,
        crack_contrast=crack_contrast, chip=chip, areas=areas, detection_rates=rates,
        false_rates=false_rates, thresholds=np.asarray(thresholds), trials=trials, des=des, speck=speck,
        tray=tray, chip_frames=chip_frames, colour_frames=colour_frames, light_frames=light_frames)


def gates(r):
    br=r["blob_result"]
    return {"location_error_px":r["location_error"],"formula_area_px":r["formula_area"],
        "measured_area_px":r["measured_area"],"area_step_error":abs(r["measured_area"]-r["formula_area"]),
        "false_positive_rate":float(r["false_rates"][r["measured_area"]-1]),"delta_e_error":r["de_error"],
        "blob_count":br.get("count"),"blob_determined":bool(br.get("determined")),
        "dark_light_crack_contrast":float(r["crack_contrast"][0])}


def _checks(g, limit=False):
    rows=[
      {"what":T("異物位置: Otsu → area_center","foreign-particle location: Otsu → area_center"),"criterion":T("真値から ≤ 1 px","≤ 1 px from truth"),"result":"%.3f px"%g["location_error_px"],"ok":g["location_error_px"]<=1},
      {"what":T("欠けの最小検出面積: 800 試行/面積","minimum detectable chip area: 800 trials/area"),"criterion":T("90 % 検出点が正規近似の ±1 px²","90% detection point within ±1 px² of normal approximation"),"result":"%d px² vs %d px²"%(g["measured_area_px"],g["formula_area_px"]),"ok":g["area_step_error"]<=1},
      {"what":T("CIEDE2000: op と直接式","CIEDE2000: op vs direct formula"),"criterion":"< 1e-9","result":_e(g["delta_e_error"]),"ok":g["delta_e_error"]<1e-9},
      {"what":T("分離した錠剤の blob 数","blob count for separated tablets"),"criterion":T("区間でなく 5 個に決まる","determined as 5, not an interval"),"result":str(g["blob_count"]),"ok":g["blob_determined"] and g["blob_count"]==5},
    ]
    if limit:
      rows.append({"what":T("照明 1 方向で浅い割れを常に検出","one light direction always detects a shallow crack"),"criterion":T("コントラスト ≥ 0.05","contrast ≥ 0.05"),"result":"%.3f"%g["dark_light_crack_contrast"],"ok":g["dark_light_crack_contrast"]>=.05})
    return rows


def _lesson(q, choices, answer, explain, formula, limit):
    return {"question":q,"choices":choices,"answer":answer,"explain":explain,"formula":formula,"limit":limit}


def build_spec(r=None, g=None):
    r=compute() if r is None else r; g=gates(r) if g is None else g
    pos,faces=_uv_ellipsoid(); positions=[[-2.2,-1,0],[-.7,1,0],[.8,-1,0],[2.2,1,0],[-1.4,0,0],[1.5,0,0]]
    xyz,q=_poses(N,positions); bodies=[]
    colours=[[224,180,112],[170,214,188],[200,183,220],[224,176,146],[235,210,145],[175,205,228]]
    for i,(p,c) in enumerate(zip(positions,colours)):
        scale=np.array([1.0, .8 if i%2 else 1.0, .32]); bodies.append({"name":"tablet_%d"%i,"pos":pos*scale,"faces":faces,"rgb":c})
    base=dict(t=np.arange(N)/16,bodies=bodies,xyz=xyz,quat=q,view={"az":-.75,"el":.65,"dist":1.0})
    tabs=[]
    tabs.append(pv.viewer_anim3d_tab("tray",T("トレイ全体","Whole tray"),"passed",T("形と色だけの合成錠剤。カメラ像には欠け、割れ、色むら、異物の真値を埋め、Otsu、area_center、blob_count_interval で測る。","Synthetic tablets use shape and colour only. Known chips, cracks, colour patches and foreign particles are embedded in the camera image and measured with Otsu, area_center and blob_count_interval."),panes=[{"label":T("合成カメラ像","synthetic camera image"),"frames":r["tray"],"png":True,"wide":True}],numbers=[pv.viewer_number(T("分離 blob","separated blobs"),str(g["blob_count"])),pv.viewer_number(T("位置誤差","position error"),"%.3f px"%g["location_error_px"])],checks=_checks(g),axis={"values":np.arange(N),"segments":[{"k":0,"label":T("検査順","inspection step"),"unit":"","decimals":0}]},lesson=_lesson(T("目視だけで全欠陥を同じ確かさで見つけられる?","Can visual inspection find every defect with equal certainty?"),[T("はい","yes"),T("いいえ","no")],1,T("画素数、ノイズ、色差、照明方向で見つけやすさが変わる。","Detectability changes with pixel count, noise, colour difference and lighting direction."),T("領域 = Otsu(像); (A,r,c) = area_center(領域)","region = Otsu(image); (A,r,c) = area_center(region)"),T("合成像であり、実製造ラインの合否基準ではない。","This is synthetic imagery, not an acceptance rule for a production line.")),**base))
    chip_base=dict(t=np.arange(len(r["areas"]))/8,bodies=bodies,xyz=xyz[:len(r["areas"])],quat=q[:len(r["areas"])],view=base["view"])
    tabs.append(pv.viewer_anim3d_tab("chip",T("欠けの検出限界","Chip detection limit"),"passed",
        T("面積 1〜15 px² ごとに欠けなし 800 像と欠けあり 800 像を合成する。欠けなしの誤検出率を 1 % にした平均コントラスト検出器が、90 % 以上を拾う最小面積を測る。",
          "For every area from 1 to 15 px², synthesize 800 images without a chip and 800 with one. Measure the smallest area detected at least 90% of the time by a mean-contrast detector whose false-positive rate is set to 1% on chip-free trials."),
        panes=[{"label":T("面積を増やした欠けのカメラ像","camera image as chip area grows"),"frames":r["chip_frames"],"png":True,"wide":True}],
        series=[{"label":T("800 試行の検出率","detection rate over 800 trials"),"values":r["detection_rates"],"unit":"","color":"#ffca28","threshold":.90}],
        numbers=[pv.viewer_number(T("実測 90 % 点","measured 90% point"),"%d px²"%r["measured_area"]),pv.viewer_number(T("正規近似","normal approximation"),"%d px²"%r["formula_area"]),pv.viewer_number(T("画素ピッチ","pixel pitch"),"0.08 mm")],
        checks=_checks(g),axis={"values":r["areas"],"segments":[{"k":0,"label":T("欠け面積","chip area"),"unit":"px²","decimals":0}]},
        lesson=_lesson(T("欠けを小さくすると、いつ見逃す?","When is a shrinking chip missed?"),[T("面積と無関係","independent of area"),T("検出率が 90 % を下回る","when detection rate falls below 90%")],1,
          T("同じコントラストなら、面積が増えるほど平均値の雑音が減って検出率が上がる。","At fixed contrast, averaging more pixels lowers noise and raises detection probability."),
          T("A ≈ ((z0.99 + z0.90)σ/ΔI)²","A ≈ ((z0.99 + z0.90)σ/ΔI)²"),
          T("独立なガウス雑音、既知の欠け位置、一様な背景を仮定。実像では位置探索と焦点ぼけがさらに効く。","Assumes independent Gaussian noise, known chip position and a uniform background; location search and defocus add further costs in real images.")),**chip_base))
    tabs.append(pv.viewer_anim3d_tab("colour",T("色むらと ΔE00","Colour patch and ΔE00"),"passed",T("局所パッチの色差を ΔE00 = 8 から 0 へ下げる。RGB 距離でなく Lab と CIEDE2000 を使い、op を直接式で検算する。","A local patch fades from ΔE00 = 8 to 0. Lab and CIEDE2000 are used instead of RGB distance, and the op is checked against the direct formula."),panes=[{"label":T("色むらを弱めたカメラ像","camera image as the colour patch fades"),"frames":r["colour_frames"],"png":True,"wide":True}],series=[{"label":T("ΔE00","ΔE00"),"values":r["des"],"unit":"","color":"#ce93d8","threshold":2.0}],numbers=[pv.viewer_number(T("式との残差","residual from formula"),_e(g["delta_e_error"])),pv.viewer_number(T("表示範囲","display sweep"),"ΔE00 8 → 0")],checks=_checks(g),axis={"values":r["des"],"segments":[{"k":0,"label":T("ΔE00","ΔE00"),"unit":"","decimals":1}]},lesson=_lesson(T("RGB の差だけで知覚的な色差を判定できる?","Can RGB distance alone judge perceptual colour difference?"),[T("はい","yes"),T("Lab と観察条件が要る","Lab and viewing conditions are needed")],1,T("CIEDE2000 は明度、彩度、色相の非一様さを補正する。","CIEDE2000 corrects non-uniformity in lightness, chroma and hue."),T("ΔE00 = CIEDE2000(Lab1, Lab2)","ΔE00 = CIEDE2000(Lab1, Lab2)"),T("白色点、照明、露光を揃えない色差は比較できない。","Colour differences are not comparable unless white point, lighting and exposure match.")),**base))
    tabs.append(pv.viewer_anim3d_tab("light",T("異物・割れと照明","Foreign particle, crack and lighting"),"limit",T("小さな暗点は正面照明でも残るが、浅い割れの陰影は照明が溝と平行な 0° で消える。1 方向だけの照明には死角がある。","A small dark particle remains under frontal light, but shallow-crack shading vanishes at 0° when light is parallel to the groove. One lighting direction has a blind spot."),panes=[{"label":T("照明角を変えたカメラ像","camera image as lighting angle changes"),"frames":r["light_frames"],"png":True,"wide":True}],series=[{"label":T("割れコントラスト","crack contrast"),"values":r["crack_contrast"],"unit":"","color":"#ef5350","threshold":.05}],numbers=[pv.viewer_number(T("0° の割れコントラスト","crack contrast at 0°"),"%.3f"%r["crack_contrast"][0]),pv.viewer_number(T("異物半径","foreign-particle radius"),"3 px")],checks=_checks(g,True),axis={"values":r["angles"],"segments":[{"k":0,"label":T("照明角","lighting angle"),"unit":"°","decimals":0}]},lesson=_lesson(T("照明が 1 方向でも浅い割れを必ず見つけられる?","Does one lighting direction always reveal a shallow crack?"),[T("必ず見つかる","always"),T("向きによって消える","it vanishes at some orientations")],1,T("溝と光が平行なとき陰影のコントラストが 0 になる模型。","In this model, shading contrast becomes zero when the groove and light are parallel."),T("Ccrack = Cmax |sin θ|","Ccrack = Cmax |sin θ|"),T("これが限界の回。多方向照明や形状計測を足さない限り、浅い割れを見逃す。","This is the limit tab. A shallow crack can be missed unless multi-directional lighting or shape measurement is added.")),**base))
    return pv.viewer_spec("tablet_inspection",T("錠剤の欠け・割れ・色むら・異物はどこまで見える?","How small can tablet chips, cracks, colour patches and foreign particles be?"),T("合成した真値を Otsu、面積・重心、blob、CIEDE2000 で測る","Measure synthetic truth with Otsu, area and centroid, blobs, and CIEDE2000"),T("①問い → ②予想 → ③再生 → ④式 → ⑤限界。ドラッグで回転し、バッジで計算の門を見る。","Follow ① question → ② prediction → ③ play → ④ formula → ⑤ limit. Drag to orbit; tap a badge for computed gates."),tabs,credit=T("すべて合成。形と色だけの一般的な錠剤模型で、会社名、製品名、薬剤名、実患者データは含まない。","Entirely synthetic generic tablet shapes and colours; no company, product, medicine or patient data are included."))


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__.splitlines()[0]); ap.add_argument("--check",action="store_true"); ap.add_argument("--out",default=str(OUT_HTML)); a=ap.parse_args(argv)
    r=compute(); g=gates(r)
    for k,v in g.items(): print("%-32s %s"%(k,v))
    spec=build_spec(r,g)
    if a.check:
        print("ok: %d bytes (not written)"%len(pv._build_html(spec,list(LANGS)).encode("utf-8"))); return 0
    path=pv.write_viewer(spec,a.out,list(LANGS)); print("wrote %s (%d bytes)"%(path,Path(path).stat().st_size)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
