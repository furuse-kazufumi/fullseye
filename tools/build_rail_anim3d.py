# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""レール頭頂摩耗と軌間を光切断で測る動く 3-D 学習ページ。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import fringe
import pocviewer as pv

OUT_HTML = ROOT / "docs" / "view2026" / "anim3d" / "rail_light_section_anim3d.html"
LANGS = ("ja", "en")
FX = 160.0
CX = 160.0
BASELINE_MM = 120.0
PIXEL_PITCH_MM = 0.18
WEAR_TRUE_MM = 2.37
GAUGE_WIDEN_TRUE_MM = 4.63
GAUGE_TRUE_MM = 1435.0
HEAD_HALF_WIDTH_MM = 32.5


def T(ja, en):
    return pv.viewer_text(ja, en)


def _e(x):
    return "< 1e-12" if abs(float(x)) < 1e-12 else "%.3g" % float(x)


def _box(sx, sy, sz):
    p = np.array([[x, y, z] for x in (-sx/2, sx/2) for y in (-sy/2, sy/2) for z in (-sz/2, sz/2)], float)
    f = np.array([[0,1,3],[0,3,2],[4,6,7],[4,7,5],[0,4,5],[0,5,1],[2,3,7],[2,7,6],[0,2,6],[0,6,4],[1,5,7],[1,7,3]])
    return p, f


def _poses(n, bodies):
    xyz = np.zeros((n, bodies, 3), float)
    q = np.zeros((n, bodies, 4), float); q[..., 0] = 1
    return xyz, q


def _centroid_line(columns, rng, sigma=0.72):
    """Render a noisy laser line and recover its centre without using truth directly."""
    offsets = np.arange(-4, 5, dtype=float)
    samples = np.floor(columns)[:, None] + offsets[None, :]
    image = 180.0*np.exp(-0.5*((samples-columns[:, None])/sigma)**2)
    image += 7.0 + rng.normal(0.0, 0.6, image.shape)
    weights = np.maximum(image-np.percentile(image, 10, axis=1)[:, None], 0.0)
    return np.sum(samples*weights, axis=1)/np.sum(weights, axis=1)


def _closed_depth(column, u):
    return FX*BASELINE_MM/(u-column)


def _smooth(y, n=9):
    pad=n//2
    return np.convolve(np.pad(y,pad,mode="edge"),np.ones(n)/n,mode="valid")


def _inner_reference(x, z, side):
    """Locate the inner head edge at 8 mm below that head's measured top."""
    mask=(x<0) if side=="left" else (x>0)
    xx=x[mask]; zz=_smooth(z[mask],7)
    target=float(np.min(zz)+8.0)
    # Inner half only: approach the track centre from each crown minimum.
    top=int(np.argmin(zz))
    ids=range(top,len(xx)-1) if side=="left" else range(top,0,-1)
    for i in ids:
        j=i+1 if side=="left" else i-1
        if (zz[i]-target)*(zz[j]-target)<=0 and zz[i]!=zz[j]:
            return float(xx[i]+(target-zz[i])*(xx[j]-xx[i])/(zz[j]-zz[i]))
    raise ValueError("inner head reference was not found")


def compute():
    rng = np.random.default_rng(20261026)
    u = np.arange(321, dtype=float)
    x_nom = (u-CX)*1000.0/FX
    # Two synthetic rail heads: circular crowns, web and foot are visualised in 3-D;
    # the measured head profile is deliberately off pixel centres.
    frames = 49
    progress = np.linspace(0, 1, frames)
    wear = WEAR_TRUE_MM*np.sin(np.pi*np.clip((progress-.18)/.64, 0, 1))**2
    widen = GAUGE_WIDEN_TRUE_MM*np.clip((progress-.35)/.45, 0, 1)
    profiles=[]; detected=[]; op_depth=[]; closed_depth=[]; wear_shapes=[]
    for w,dg in zip(wear,widen):
        reference_radius=HEAD_HALF_WIDTH_MM*np.sqrt(-np.log((17.0-8.0)/17.0))
        centre=0.5*(GAUGE_TRUE_MM+dg)+reference_radius
        left=np.exp(-((x_nom+centre)/HEAD_HALF_WIDTH_MM)**2)
        right=np.exp(-((x_nom-centre)/HEAD_HALF_WIDTH_MM)**2)
        crowns=np.maximum(left,right)
        z_ref=1000.0-17.0*crowns
        wear_shape=np.exp(-((x_nom+centre)/14.0)**4)
        z = z_ref+w*wear_shape
        col = u-FX*BASELINE_MM/z
        cen = _centroid_line(col, rng)
        cmap = cen.reshape(1, -1)
        kc=np.array([[FX,0,CX],[0,FX,0],[0,0,1.]],float)
        kp=kc.copy(); R=np.eye(3); trans=np.array([-BASELINE_MM,0,0.])
        zop=fringe.triangulate_column(cmap,kc,kp,R,trans)[0]
        profiles.append(z); detected.append(cen); op_depth.append(zop); closed_depth.append(_closed_depth(cen,u)); wear_shapes.append(wear_shape)
    profiles=np.array(profiles); detected=np.array(detected); op_depth=np.array(op_depth); closed_depth=np.array(closed_depth)
    wear_shapes=np.array(wear_shapes)
    # Shape-free estimator: compare each scan with its unworn synthetic reference,
    # smooth the measured difference, then take the deepest point on the left head.
    refs=profiles-wear[:,None]*wear_shapes
    left_mask=x_nom < -500.0
    recovered_wear_free=np.array([np.max(_smooth((z-ref)[left_mask],3)) for z,ref in zip(op_depth,refs)])
    # A disclosed comparison estimator assumes the planted wear footprint is known.
    recovered_wear_fit=np.array([np.dot(z-ref,shape)/np.dot(shape,shape) for z,ref,shape in zip(op_depth,refs,wear_shapes)])
    recovered_x=(u[None,:]-CX)*op_depth/FX
    inner_left=np.array([_inner_reference(x,z,"left") for x,z in zip(recovered_x,op_depth)])
    inner_right=np.array([_inner_reference(x,z,"right") for x,z in zip(recovered_x,op_depth)])
    raw_gauge=inner_right-inner_left
    # The unworn first scan is the installed nominal-gauge reference.  Subsequent
    # widening comes only from the two measured inner-reference points.
    gauge_est=GAUGE_TRUE_MM+(raw_gauge-raw_gauge[0])
    rms=np.sqrt(np.mean((op_depth-profiles)**2,axis=1))
    band=np.zeros((frames,96,321,3),np.uint8)
    for k,c in enumerate(detected):
        band[k]=(8,15,22)
        rr=np.clip(np.rint(48+(c-np.mean(c))*.28).astype(int),2,93)
        band[k,rr,np.arange(321)]=(60,255,190)
    return dict(u=u,x=x_nom,progress=progress,wear=wear,widen=widen,profiles=profiles,
                detected=detected,op_depth=op_depth,closed_depth=closed_depth,
                recovered_wear=recovered_wear_free,recovered_wear_free=recovered_wear_free,
                recovered_wear_fit=recovered_wear_fit,wear_fit_delta=np.abs(recovered_wear_fit-recovered_wear_free),
                recovered_x=recovered_x,inner_left=inner_left,inner_right=inner_right,raw_gauge=raw_gauge,
                gauge_est=gauge_est,gauge_truth=GAUGE_TRUE_MM+widen,rms=rms,band=band)


def gates(r):
    peak=int(np.argmax(r["wear"]))
    return {
        "profile_rms_mm":float(np.sqrt(np.mean((r["op_depth"]-r["profiles"])**2))),
        # 0.05 detector pixel propagated through Z=fB/disparity.  PIXEL_PITCH_MM
        # states the corresponding sensor sampling assumption on the page.
        "profile_limit_mm":1000.0**2/(FX*BASELINE_MM)*0.05,
        "wear_error_mm":abs(float(r["recovered_wear_free"][peak]-WEAR_TRUE_MM)),
        "wear_fit_delta_mm":float(r["wear_fit_delta"][peak]),
        "gauge_error_mm":abs(float(r["gauge_est"][-1]-r["gauge_truth"][-1])),
        "gauge_limit_mm":1000.0/FX*0.05*np.sqrt(2.0),
        "two_path_error_mm":float(np.nanmax(np.abs(r["op_depth"]-r["closed_depth"])))
    }


def _checks(g, limit=False):
    rows=[
      {"what":T("光線中心から戻した断面 RMS","section RMS from detected laser centre"),"criterion":"< %.3f mm"%g["profile_limit_mm"],"result":"%.4f mm"%g["profile_rms_mm"],"ok":g["profile_rms_mm"]<g["profile_limit_mm"]},
      {"what":T("頭頂摩耗の推定誤差","head-wear estimation error"),"criterion":"< 0.10 mm","result":"%.4f mm"%g["wear_error_mm"],"ok":g["wear_error_mm"]<.10},
      {"what":T("軌間の広がりの推定誤差","gauge-widening estimation error"),"criterion":"< %.3f mm"%g["gauge_limit_mm"],"result":"%.4f mm"%g["gauge_error_mm"],"ok":g["gauge_error_mm"]<g["gauge_limit_mm"]},
      {"what":T("三角測量: op と独立閉形式","triangulation: op vs independent closed form"),"criterion":"< 1e-12 mm","result":_e(g["two_path_error_mm"])+" mm","ok":g["two_path_error_mm"]<1e-12}]
    if limit:
        rows.append({"what":T("光沢・浅い角度・振動があっても全点を測れる","every point remains measurable with glare, grazing occlusion and vibration"),"criterion":T("欠測と偏りを含む","include missing and biased samples"),"result":T("未計算: 現場では再走査が必要","not computed: field data require rescanning"),"ok":False})
    return rows


def _lesson(q, choices, answer, explain, formula, limit):
    return {"question":q,"choices":choices,"answer":answer,"explain":explain,"formula":formula,"limit":limit}


def build_spec(r,g):
    n=len(r["progress"]); rail,rf=_box(.55,8,.42); sheet,sf=_box(3.8,.025,1.8); cam,cf=_box(.5,.7,.35)
    xyz,q=_poses(n,4); xyz[:,0,0]=-1.0; xyz[:,1,0]=1.0; xyz[:,2,2]=.7; xyz[:,3]=[0,-2.8,1.4]
    common=[{"name":"left rail","pos":rail,"faces":rf,"rgb":[105,120,132]},{"name":"right rail","pos":rail,"faces":rf,"rgb":[105,120,132]},{"name":"laser sheet","pos":sheet,"faces":sf,"rgb":[40,255,170],"alpha":.28},{"name":"camera","pos":cam,"faces":cf,"rgb":[245,180,55]}]
    tabs=[]
    tabs.append(pv.viewer_anim3d_tab("line",T("光の線が断面の形に曲がる","The light line bends with the section"),"passed",T("平らな光の面とレール表面の交線だけが光る。カメラ像の曲線は、頭頂・ウェブ・底部を横切った高さの並びである。","Only the intersection of a flat light sheet and the rail surface glows. Its image curve is the sequence of heights across head, web and foot."),np.arange(n)/24,common,xyz,q,panes=[{"label":T("雑音を加えた光線像","noisy laser-line image"),"frames":r["band"],"png":True,"wide":True}],series=[{"label":T("断面 RMS","section RMS"),"values":r["rms"],"unit":"mm","color":"#4fc3f7"}],checks=_checks(g),axis={"values":r["progress"],"segments":[{"k":0,"label":T("走行位置","travel position"),"unit":"","decimals":2}]},view={"az":-.75,"el":.4,"dist":1.0},lesson=_lesson(T("真っすぐな光を当てたのに、像の線はなぜ曲がる?","Why does the image line bend although the projected light is straight?"),[T("表面との交線だから","because it is the surface intersection"),T("光が空気中で曲がるから","because light bends in air")],0,T("光の面を断面形状が切り取り、カメラの視差が高さを画素位置へ変える。","The section clips the light plane and camera parallax converts height into pixel position."),T("光の面 ∩ 表面 = 光る線","light plane ∩ surface = bright line"),T("代表寸法だけを使った合成レール断面。","Synthetic rail section using assumed representative dimensions."))))
    tabs.append(pv.viewer_anim3d_tab("triangulation",T("三角測量で断面へ戻す","Triangulate back to a section"),"passed",T("画素中心から外れた光線を雑音付きで描き、9 画素の重心で中心を検出した。triangulate_column がカメラ視線と投影面の交点を深度へ戻す。","The line is rendered off pixel centres with noise and detected by a nine-pixel centroid. triangulate_column intersects each camera ray with the projected plane."),np.arange(n)/24,common,xyz,q,panes=[{"label":T("検出した中心から復元した断面","section recovered from detected centres"),"frames":r["band"],"png":True,"wide":True}],series=[{"label":T("復元誤差 RMS","reconstruction RMS"),"values":r["rms"],"unit":"mm","color":"#80cbc4"}],checks=_checks(g),axis={"values":r["progress"],"segments":[{"k":0,"label":T("走行位置","travel position"),"unit":"","decimals":2}]},view={"az":-.65,"el":.5,"dist":1.0},lesson=_lesson(T("1 本の像の線だけで奥行きを決められる条件は?","What makes depth solvable from one image line?"),[T("光の面の位置とカメラ校正が既知","known light plane and camera calibration"),T("線の色だけが既知","only the line colour is known")],0,T("既知の基線が、各画素の視線と光の面の交点を一意にする。","A known baseline makes the ray-plane intersection unique."),T("Z = f B / (u − u_p)","Z = f B / (u − u_p)"),T("基線 120 mm、焦点距離と画素ピッチは説明用の代表値。","The 120 mm baseline, focal length and pixel pitch are assumed representative values."))))
    tabs.append(pv.viewer_anim3d_tab("wear",T("摩耗区間を通過する","Pass through a worn section"),"passed",T("基準走査との差を 3 点で平滑化し、その最大値から形を仮定せず左頭頂の摩耗を測る。既知の摩耗形状へ最小二乗した比較値も並べ、仮定による差を隠さない。","The reference difference is smoothed over three points and its maximum measures left-head wear without assuming its shape. A comparison least-squares estimate assumes the known wear footprint, so their difference remains visible."),np.arange(n)/24,common,xyz,q,series=[{"label":T("形を仮定しない推定","shape-free estimate"),"values":r["recovered_wear_free"],"unit":"mm","color":"#ffb74d"},{"label":T("既知形状の最小二乗","known-shape least squares"),"values":r["recovered_wear_fit"],"unit":"mm","color":"#ab47bc"},{"label":T("真の摩耗深さ","true wear depth"),"values":r["wear"],"unit":"mm","color":"#ef5350"}],numbers=[pv.viewer_number(T("埋めた真値","planted truth"),"2.37 mm"),pv.viewer_number(T("二推定の差","difference between estimators"),"%.4f mm"%g["wear_fit_delta_mm"])],checks=_checks(g),axis={"values":r["progress"],"segments":[{"k":0,"label":T("走行位置","travel position"),"unit":"","decimals":2}]},view={"az":-.85,"el":.35,"dist":1.0},lesson=_lesson(T("摩耗区間へ入ると基準断面との差は?","What happens to the reference difference in the worn zone?"),[T("立ち上がる","it rises"),T("常にゼロ","it stays zero")],0,T("主推定は平滑化した差の最大値で、摩耗形状を使わない。紫線だけは形を既知とした最小二乗。","The main estimate is the maximum smoothed difference and does not use the wear shape. Only the purple line is a known-shape least-squares fit."),T("摩耗 = max smooth(z_measured − z_reference)","wear = max smooth(z_measured − z_reference)"),T("最小二乗の比較値は摩耗形状が既知という強い仮定を置く。温度、たわみ、基準断面の個体差も含めない。","The least-squares comparison makes the strong assumption that wear shape is known. Temperature, flexure and reference-section variation are also omitted."))))
    tabs.append(pv.viewer_anim3d_tab("limit",T("軌間と測れない条件","Gauge and unmeasurable conditions"),"limit",T("左右の復元点列で、それぞれ頭頂から 8 mm 下の内側交点を補間し、二点間距離の初回走査からの変化として 4.63 mm の広がりを測る。真値は推定式へ渡さない。","Each recovered profile is interpolated at the inner crossing 8 mm below its measured head top. Change in the distance between those two points from the first scan measures a planted 4.63 mm widening; truth is not passed to the estimator."),np.arange(n)/24,common,xyz,q,series=[{"label":T("点列から測った軌間","gauge measured from point profiles"),"values":r["gauge_est"],"unit":"mm","color":"#ba68c8"},{"label":T("合成した真値","synthetic truth"),"values":r["gauge_truth"],"unit":"mm","color":"#ef5350"}],numbers=[pv.viewer_number(T("埋めた広がり","planted widening"),"4.63 mm"),pv.viewer_number(T("画素と雑音からの基準","criterion from pixels and noise"),"%.3f mm"%g["gauge_limit_mm"])],checks=_checks(g,True),axis={"values":r["progress"],"segments":[{"k":0,"label":T("走行位置","travel position"),"unit":"","decimals":2}]},view={"az":-.8,"el":.42,"dist":1.0},lesson=_lesson(T("光の線が途切れた場所を 0 mm としてよい?","May a missing laser line be recorded as 0 mm?"),[T("よい","yes"),T("欠測として再走査する","mark missing and rescan")],1,T("0 は形状という誤った観測になる。光沢・遮蔽・振動を識別して欠測として扱う。","Zero would be a false shape observation. Detect glare, occlusion and vibration and keep the sample missing."),T("軌間 = x_right(頭頂−8 mm) − x_left(頭頂−8 mm)","gauge = x_right(head−8 mm) − x_left(head−8 mm)"),T("初回走査を公称軌間の基準にする。合成模型であり、保守判定や安全診断には使わない。","The first scan calibrates nominal gauge. This synthetic model is not for maintenance decisions or safety diagnosis."))))
    return pv.viewer_spec("rail_light_section",T("線状の光 1 本で、なぜレール断面が分かるのか","How one laser line reveals a rail section"),T("頭頂摩耗と軌間を、雑音のある光切断像から測る","Measure head wear and gauge from a noisy light-section image"),T("①問い → ②予想 → ③再生 → ④式 → ⑤限界。バッジは計算した値だけを表示する。","Follow ① question → ② prediction → ③ play → ④ formula → ⑤ limit. Badges show computed values only."),tabs,credit=T("すべて合成。断面形状、寸法、基線、画素ピッチ、摩耗、軌間は一般的な代表値として置いた仮定で、特定の事業者・車両・製品・規格を表さない。","Entirely synthetic. Section shape, dimensions, baseline, pixel pitch, wear and gauge are assumed representative values, not a specific operator, vehicle, product or standard."))


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__.splitlines()[0]); ap.add_argument("--check",action="store_true"); ap.add_argument("--out",default=str(OUT_HTML)); a=ap.parse_args(argv)
    r=compute(); g=gates(r)
    for k,v in g.items(): print("%-28s %s"%(k,v))
    spec=build_spec(r,g)
    if a.check:
        print("ok: %d bytes (not written)"%len(pv._build_html(spec,list(LANGS)).encode("utf-8"))); return 0
    path=pv.write_viewer(spec,a.out,list(LANGS)); print("wrote %s (%d bytes)"%(path,Path(path).stat().st_size)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
