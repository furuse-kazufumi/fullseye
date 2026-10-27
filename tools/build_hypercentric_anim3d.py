# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ハイパーセントリックレンズで円柱の上面と側面を同時に見る動く 3-D 教材。"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import optics
import pocviewer as pv
import raytrace as rt
import fullseye as fs

OUT_HTML = ROOT / "docs" / "view2026" / "anim3d" / "hypercentric_lens_anim3d.html"
LANGS = ("ja", "en")
F_MM = 40.0
OBJECT_MM = 100.0
RADIUS_MM = 18.0
HEIGHT_MM = 30.0
IMAGE_SCALE = 1.7
IMAGE_SIZE = 192
AA = 4
IMAGE_OFFSET_PX = (0.37, -0.21)


def T(ja, en):
    return pv.viewer_text(ja, en)


def _e(x):
    return "< 1e-12" if abs(float(x)) < 1e-12 else "%.3g" % float(x)


def _system(stop_distance):
    return rt.lens_system([
        {"f": F_MM, "t": float(stop_distance), "ap": 24.0},
        {"R": float("inf"), "t": None, "n": 1.0, "ap": 7.0},
    ], stop=1, object_mm=OBJECT_MM)


def entrance_pupil_abcd(stop_distance):
    """Stop image through the thin lens, measured from the lens vertex."""
    d = float(stop_distance)
    m = optics.abcd_matrix([("free", d), ("lens", F_MM)])
    traced = optics.abcd_trace(m, height_mm=1.0, angle_mrad=0.0)
    if abs(m[1, 1]) < 1e-12:
        return -float("inf")
    # Add free propagation s after the lens. Imaging the stop requires
    # B_total = B + s D = 0; in the repository's lens coordinate this is B/D.
    pupil = float(m[0, 1] / m[1, 1])
    if not math.isfinite(traced["angle_mrad"]):
        raise ValueError("ABCD trace produced a non-finite ray")
    return pupil


def entrance_pupil_closed(stop_distance):
    d = float(stop_distance)
    return -float("inf") if abs(d-F_MM) < 1e-12 else F_MM*d/(F_MM-d)


def side_band_mm(pupil_from_lens):
    """Radial side band on the top plane from perspective projection."""
    if not math.isfinite(pupil_from_lens):
        return 0.0
    z = pupil_from_lens + OBJECT_MM
    if z >= -HEIGHT_MM:
        return 0.0
    return RADIUS_MM * HEIGHT_MM / (-z - HEIGHT_MM)


def _cylinder_projection_mesh(pupil_from_lens, n=128):
    """Project the top fan and cylindrical side mesh onto the top plane."""
    a = np.linspace(0, 2*np.pi, n, endpoint=False)
    z_top, z_bottom = -OBJECT_MM, -OBJECT_MM-HEIGHT_MM
    top = np.column_stack([RADIUS_MM*np.cos(a), RADIUS_MM*np.sin(a), np.full(n,z_top)])
    bottom = np.column_stack([RADIUS_MM*np.cos(a), RADIUS_MM*np.sin(a), np.full(n,z_bottom)])
    vertices = np.vstack([[[0,0,z_top]], top, bottom])
    faces=[]
    for i in range(n):
        j=(i+1)%n; faces += [[0,1+i,1+j],[1+i,1+n+i,1+n+j],[1+i,1+n+j,1+j]]
    if math.isfinite(pupil_from_lens):
        den = vertices[:,2]-pupil_from_lens
        k = (z_top-pupil_from_lens)/den
        xy = vertices[:,:2]*k[:,None]
    else:
        xy = vertices[:,:2].copy()
    return xy, np.asarray(faces,int)


def _render_cylinder(pupil_from_lens, seed, size=IMAGE_SIZE):
    """Area-sampled perspective rendering of a meshed cylinder with fixed noise."""
    xy, faces = _cylinder_projection_mesh(pupil_from_lens)
    top_ids=np.unique(faces[::3]); side_ids=np.unique(np.vstack([faces[1::3],faces[2::3]]))
    r_top=float(np.median(np.linalg.norm(xy[top_ids[1:]],axis=1)))
    r_side=float(np.max(np.linalg.norm(xy[side_ids],axis=1)))
    r_outer=max(r_top,r_side)
    yy,xx=np.mgrid[:size,:size]
    coverage_top=np.zeros((size,size),float); coverage_obj=np.zeros_like(coverage_top)
    ox,oy=IMAGE_OFFSET_PX
    for sy in (np.arange(AA)+.5)/AA-.5:
        for sx in (np.arange(AA)+.5)/AA-.5:
            dx=(xx+sx-(size/2+ox))/IMAGE_SCALE; dy=(yy+sy-(size/2+oy))/IMAGE_SCALE
            rr=np.hypot(dx,dy)
            coverage_top += rr <= r_top
            coverage_obj += rr <= r_outer
    coverage_top/=AA*AA; coverage_obj/=AA*AA
    gray=.08 + .60*coverage_obj + .20*coverage_top
    gray += np.random.default_rng(seed).normal(0,.018,gray.shape)
    gray=np.clip(gray,0,1)
    rgb=np.stack([.08+.82*coverage_obj, .08+.47*coverage_obj+.28*coverage_top,
                  .10+.10*coverage_obj+.68*coverage_top],axis=2)
    rgb=np.clip(rgb + (gray-(.08+.60*coverage_obj+.20*coverage_top))[...,None],0,1)
    return np.round(rgb*255).astype(np.uint8), gray, xy, faces


def _bilinear(im, x, y):
    x=np.asarray(x); y=np.asarray(y); x0=np.floor(x).astype(int); y0=np.floor(y).astype(int)
    x0=np.clip(x0,0,im.shape[1]-2); y0=np.clip(y0,0,im.shape[0]-2)
    fx=x-x0; fy=y-y0
    return ((1-fx)*(1-fy)*im[y0,x0]+fx*(1-fy)*im[y0,x0+1]+(1-fx)*fy*im[y0+1,x0]+fx*fy*im[y0+1,x0+1])


def _measure_band_px(gray):
    """Otsu segment, estimate the centre, then measure radial edges at subpixels."""
    obj=np.asarray(fs.apply(gray,"otsu"),bool)
    vals=gray[obj]
    if vals.size < 100:
        return 0.0, (float("nan"),float("nan"))
    split=np.asarray(fs.apply(vals.reshape(1,-1),"otsu"),bool).ravel()
    top=np.zeros_like(obj); top[obj]=split
    yy,xx=np.nonzero(top)
    if len(xx) < 100:
        return 0.0, (float("nan"),float("nan"))
    cx=float(np.mean(xx)); cy=float(np.mean(yy))
    bg=gray[~obj]; side=gray[obj & ~top]; tv=gray[top]
    outer_thr=.5*(float(np.percentile(bg,99))+float(np.percentile(side if side.size else vals,1)))
    inner_thr=.5*(float(np.percentile(side if side.size else vals,99))+float(np.percentile(tv,1)))
    radii=np.arange(0,95,.1); widths=[]
    for a in np.linspace(0,2*np.pi,72,endpoint=False):
        v=_bilinear(gray,cx+radii*np.cos(a),cy+radii*np.sin(a))
        inner=np.flatnonzero(v < inner_thr); outer=np.flatnonzero(v < outer_thr)
        if len(inner) and len(outer):
            ri=radii[inner[0]]; ro=radii[outer[outer>inner[0]][0]] if np.any(outer>inner[0]) else ri
            widths.append(max(0.0,ro-ri))
    return (float(np.median(widths)) if widths else 0.0), (cx,cy)


def _chief_trace(system, stop_distance, field=5.0):
    """Trace a chief ray aimed at the physical stop centre with trace_rays."""
    d=float(stop_distance)
    den=1+d/OBJECT_MM-d/F_MM
    y_lens=field*d/OBJECT_MM/den
    origin=np.array([[0.0,field,-OBJECT_MM]])
    direction=np.array([[0.0,y_lens-field,OBJECT_MM]])
    direction/=np.linalg.norm(direction,axis=1,keepdims=True)
    tr=rt.trace_rays(system,origin,direction)
    if not tr["valid"][0]:
        raise ValueError("chief ray did not pass the prescription")
    return tr["points"][0]


def compute():
    stop_distances = np.array([10.0, F_MM, 50.0])
    pupil_op, pupil_abcd, pupil_closed, chief = [], [], [], []
    for d in stop_distances:
        system = _system(d)
        pupil_op.append(rt.paraxial_trace(system)["ep_position"])
        pupil_abcd.append(entrance_pupil_abcd(d))
        pupil_closed.append(entrance_pupil_closed(d))
        chief.append(_chief_trace(system,d))
    sweep_d = np.linspace(50.0, 55.0, 49)
    sweep_p = np.array([rt.paraxial_trace(_system(d))["ep_position"] for d in sweep_d])
    sweep_band = np.array([side_band_mm(p) for p in sweep_p])
    images, measured, centers, render_meshes = [], [], [], []
    for i,p in enumerate(sweep_p):
        im,gray,xy,faces=_render_cylinder(p,1701+i)
        width,center=_measure_band_px(gray)
        images.append(im); measured.append(width/IMAGE_SCALE); centers.append(center); render_meshes.append((xy,faces))
    tele_image,tele_gray,tele_xy,tele_faces=_render_cylinder(-float("inf"),9917)
    tele_px,tele_center=_measure_band_px(tele_gray)
    return {"stop_distances": stop_distances, "pupil_op": np.array(pupil_op),
            "pupil_abcd": np.array(pupil_abcd), "pupil_closed":np.array(pupil_closed), "chief": chief, "sweep_d": sweep_d,
            "sweep_p": sweep_p, "band": sweep_band, "images": np.array(images),
            "measured_band": np.array(measured), "measured_centers":np.array(centers), "render_meshes":render_meshes,
            "tele_image": tele_image, "tele_band_px":tele_px, "tele_center":tele_center,
            "tele_mesh":(tele_xy,tele_faces), "scale": IMAGE_SCALE}


def gates(r):
    finite = np.isfinite(r["pupil_op"])
    pupil_err = float(np.max(np.abs(r["pupil_op"][finite] - r["pupil_abcd"][finite])))
    image_err_px = float(np.max(np.abs(r["measured_band"] - r["band"]) * r["scale"]))
    closed_err=float(np.max(np.abs(r["pupil_op"][finite]-r["pupil_closed"][finite])))
    tele_px = float(r["tele_band_px"])
    return {"pupil_error_mm": pupil_err, "image_band_error_px": image_err_px,
            "pupil_closed_error_mm":closed_err, "telecentric_band_px": tele_px}


def _box(sx, sy, sz):
    p = np.array([[x, y, z] for x in (-sx/2, sx/2) for y in (-sy/2, sy/2) for z in (-sz/2, sz/2)], float)
    f = np.array([[0,1,3],[0,3,2],[4,6,7],[4,7,5],[0,4,5],[0,5,1],[2,3,7],[2,7,6],[0,2,6],[0,6,4],[1,5,7],[1,7,3]])
    return p, f


def _cylinder(r=1.0, h=1.5, n=40):
    a = np.linspace(0, 2*np.pi, n, endpoint=False)
    rings = [np.column_stack([r*np.cos(a), r*np.sin(a), np.full(n, z)]) for z in (0.0, h)]
    p = np.vstack(rings + [np.array([[0,0,h]])])
    f = []
    for i in range(n):
        j=(i+1)%n; f += [[i,j,n+j],[i,n+j,n+i],[2*n,n+i,n+j]]
    return p, np.array(f)


def _poses(n, bodies):
    xyz=np.zeros((n,bodies,3)); q=np.zeros((n,bodies,4)); q[...,0]=1
    return xyz,q


def _area_resize_frames(frames, size=120):
    """Deterministic box-area shrink for display only; measurements use originals."""
    src=np.asarray(frames); h,w=src.shape[1:3]
    yedges=np.linspace(0,h,size+1); xedges=np.linspace(0,w,size+1)
    out=np.empty((len(src),size,size,3),np.uint8)
    for y in range(size):
        y0,y1=int(math.floor(yedges[y])),int(math.ceil(yedges[y+1]))
        for x in range(size):
            x0,x1=int(math.floor(xedges[x])),int(math.ceil(xedges[x+1]))
            out[:,y,x]=np.round(src[:,y0:y1,x0:x1].mean(axis=(1,2))).astype(np.uint8)
    return out


def _checks(g, limit=False):
    rows=[
        {"what":T("入射瞳: paraxial_trace と ABCD", "entrance pupil: paraxial_trace vs ABCD"), "criterion":"< 1e-9 mm", "result":_e(g["pupil_error_mm"])+" mm", "ok":g["pupil_error_mm"]<1e-9},
        {"what":T("像から測った側面帯と閉形式", "image-measured side band vs closed form"), "criterion":"< 0.5 px", "result":"%.3f px"%g["image_band_error_px"], "ok":g["image_band_error_px"]<0.5},
        {"what":T("テレセントリック像の側面帯", "side band in telecentric image"), "criterion":T("雑音床 ≤ 1 px", "noise floor ≤ 1 px"), "result":"%.3f px"%g["telecentric_band_px"], "ok":g["telecentric_band_px"]<=1.0},
    ]
    if limit:
        rows.append({"what":T("被写界深度と歪みも補正済み", "depth of field and distortion are corrected"), "criterion":T("実レンズ校正を含む", "includes real-lens calibration"), "result":T("未計算", "not computed"), "ok":False})
    return rows


def _lesson(q, choices, answer, explain, formula, limit):
    return {"question":q,"choices":choices,"answer":answer,"explain":explain,"formula":formula,"limit":limit}


def build_spec(r, g):
    cyl, cf=_cylinder(); lens, lf=_box(.15,2.8,2.8); tabs=[]
    n=49; xyz,q=_poses(n,2); xyz[:,1,2]=2.8
    common=[{"name":"cylinder","pos":cyl,"faces":cf,"rgb":[70,175,220]}, {"name":"lens","pos":lens,"faces":lf,"rgb":[110,205,255],"alpha":.42}]
    modes=np.repeat(np.arange(3),16); modes=np.append(modes,2)
    pupil=np.array([r["pupil_op"][i] for i in modes])
    band=np.array([side_band_mm(x) for x in pupil])
    tab=pv.viewer_anim3d_tab("compare",T("3 種類のレンズで同じ円柱を見る","View one cylinder with three lens types"),"passed",
        T("通常、テレセントリック、ハイパーセントリックで主光線の延長が作る入射瞳を比べる。物体の向こうにある仮想瞳では上面の外に側面が現れる。","Compare the entrance pupil formed by chief-ray extensions for entocentric, telecentric and hypercentric views. A virtual pupil beyond the object places the side outside the top face."),
        np.arange(n)/16,common,xyz,q,series=[{"label":T("側面帯","side band"),"values":band,"unit":"mm","color":"#ffb74d"}],
        numbers=[pv.viewer_number(T("通常の入射瞳","entocentric entrance pupil"),"13.333 mm"),pv.viewer_number(T("ハイパーセントリックの入射瞳","hypercentric entrance pupil"),"-200.000 mm")],checks=_checks(g),
        axis={"values":modes,"segments":[{"k":0,"label":T("レンズ種別","lens type"),"unit":"","decimals":0}]},view={"az":-.8,"el":.45,"dist":1.0},
        lesson=_lesson(T("円柱の側面まで同時に見えるのはどれ?","Which view shows the cylinder side at the same time?"),[T("通常","entocentric"),T("テレセントリック","telecentric"),T("ハイパーセントリック","hypercentric")],2,T("物体の向こうの仮想入射瞳へ主光線が収束して見えるため。","Chief rays appear to converge to a virtual entrance pupil beyond the object."),T("入射瞳 z = fd/(f-d)","entrance pupil z = fd/(f-d)"),T("近軸模型で、収差と開口によるケラレは省略。","Paraxial model; aberrations and aperture vignetting are omitted.")))
    tabs.append(tab)

    xyz,q=_poses(n,2); xyz[:,1,2]=2.8
    tab=pv.viewer_anim3d_tab("pupil",T("入射瞳を動かす","Move the entrance pupil"),"passed",
        T("絞りを焦点面から遠ざけると、仮想入射瞳が物体の向こうへ移り、見える側面の帯が広がる。","Moving the stop beyond the focal plane moves the virtual entrance pupil behind the object and widens the visible side band."),
        np.arange(n)/16,common,xyz,q,series=[{"label":T("入射瞳位置","entrance-pupil position"),"values":r["sweep_p"],"unit":"mm","color":"#4fc3f7"},{"label":T("側面帯","side band"),"values":r["band"],"unit":"mm","color":"#ffb74d"}],
        checks=_checks(g),axis={"values":r["sweep_d"],"segments":[{"k":0,"label":T("レンズから絞りまで d","lens-to-stop distance d"),"unit":"mm","decimals":1}]},view={"az":-.8,"el":.45,"dist":1.0},
        lesson=_lesson(T("入射瞳が円柱から遠ざかると側面帯は?","What happens to the side band as the pupil recedes?"),[T("狭くなる","narrows"),T("広くなる","widens")],0,T("遠方では主光線が平行に近づく。","At long distance the chief rays approach parallel."),T("w = RH/(|z_p|-H)","w = RH/(|z_p|-H)"),T("瞳が物体と交わる領域は表示しない。","Configurations where the pupil intersects the object are not shown.")))
    tabs.append(tab)

    display_idx=np.linspace(0,len(r["sweep_d"])-1,13).round().astype(int)
    display_images=_area_resize_frames(r["images"][display_idx])
    ni=len(display_idx); xyz,q=_poses(ni,1)
    tab=pv.viewer_anim3d_tab("image",T("像では上面と側面がどう並ぶ?","How do top and side appear in the image?"),"passed",
        T("投影光線から合成した像では、青い上面の外側に橙の側面がドーナツ状に並ぶ。帯幅は画像の色領域から測る。","In the image synthesized from projection rays, the orange side forms a doughnut around the blue top. Band width is measured from image pixels."),
        np.arange(ni)/4,[common[0]],xyz,q,panes=[{"label":T("合成カメラ像","synthetic camera image"),"frames":display_images,"png":True,"wide":True}],series=[{"label":T("画像で測った側面帯","side band measured in image"),"values":r["measured_band"][display_idx],"unit":"mm","color":"#ffb74d"}],checks=_checks(g),
        axis={"values":r["sweep_d"][display_idx],"segments":[{"k":0,"label":T("レンズから絞りまで d","lens-to-stop distance d"),"unit":"mm","decimals":1}]},view={"az":-.8,"el":.45,"dist":1.0},
        lesson=_lesson(T("側面は上面の内側と外側のどちらに現れる?","Does the side appear inside or outside the top face?"),[T("内側","inside"),T("外側","outside")],1,T("遠い側の円周が大きく投影され、外側の環になる。","The farther rim projects larger and becomes an outer annulus."),T("画素帯 ≈ scale × RH/(|z_p|-H)","pixel band ≈ scale × RH/(|z_p|-H)"),T("照明、質感、反射は含まない二色の輪郭像。","Two-colour silhouette only; lighting, texture and reflection are omitted.")))
    tabs.append(tab)

    xyz,q=_poses(ni,1)
    tab=pv.viewer_anim3d_tab("limit",T("見えることと測れることは同じ?","Is visibility the same as metrology?"),"limit",
        T("上面と側面を一枚に収めても、被写界深度、歪み、ケラレは別に校正が要る。この模型では未計算として限界を明示する。","Putting top and side in one frame does not calibrate depth of field, distortion or vignetting. This model marks them as uncomputed limits."),
        np.arange(ni)/4,[common[0]],xyz,q,panes=[{"label":T("合成像。実レンズの校正は含まない","synthetic image; real-lens calibration excluded"),"frames":display_images,"png":True,"wide":True}],checks=_checks(g,True),
        axis={"values":r["sweep_d"][display_idx],"segments":[{"k":0,"label":T("レンズから絞りまで d","lens-to-stop distance d"),"unit":"mm","decimals":1}]},view={"az":-.8,"el":.45,"dist":1.0},
        lesson=_lesson(T("一枚で見えれば、そのまま寸法測定できる?","If it is visible in one frame, is it immediately measurable?"),[T("できる","yes"),T("校正が必要","calibration is required")],1,T("奥行きごとの倍率と歪みを校正して初めて測定に使える。","Metrology requires calibration of depth-dependent magnification and distortion."),T("表示模型 = 近軸投影のみ","display model = paraxial projection only"),T("被写界深度、歪み、ケラレを未計算として残す。","Depth of field, distortion and vignetting remain uncomputed.")))
    tabs.append(tab)
    return pv.viewer_spec("hypercentric_lens",T("なぜ円柱の上面と側面を一枚で見られるのか","Why one image can show a cylinder top and side"),T("通常・テレセントリック・ハイパーセントリックの主光線と入射瞳を比べる","Compare chief rays and entrance pupils for entocentric, telecentric and hypercentric views"),T("①問い → ②予想 → ③再生 → ④式 → ⑤限界。バッジで計算の門を見る。","Follow ① question → ② prediction → ③ play → ④ formula → ⑤ limit. Tap a badge for computed gates."),tabs,credit=T("レンズ、円柱、像はすべて合成。寸法は説明用の仮定で、特定の製品やメーカーを表さない。","Lens, cylinder and images are entirely synthetic. Dimensions are explanatory assumptions and represent no specific product or manufacturer."))


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__.splitlines()[0]); ap.add_argument("--check",action="store_true"); ap.add_argument("--out",default=str(OUT_HTML)); a=ap.parse_args(argv)
    r=compute(); g=gates(r)
    for k,v in g.items(): print("%-28s %s"%(k,v))
    spec=build_spec(r,g)
    if a.check:
        print("ok: %d bytes (not written)"%len(pv._build_html(spec,list(LANGS)).encode())); return 0
    path=pv.write_viewer(spec,a.out,list(LANGS)); print("wrote %s (%d bytes)"%(path,Path(path).stat().st_size)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
