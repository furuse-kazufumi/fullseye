# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""排水量・浮心・メタセンタ高さを学ぶ、合成船型の動く 3-D ページ。"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import ConvexHull

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import fullseye as fs
import pocviewer as pv

OUT_HTML = ROOT / "docs" / "view2026" / "anim3d" / "ship_stability_anim3d.html"
LANGS = ("ja", "en")
LENGTH, BEAM, DEPTH = 72.0, 14.0, 8.0
RHO_WATER = 1025.0
TARGET_FRACTION = 0.46


def T(ja, en):
    return pv.viewer_text(ja, en)


def _e(x):
    return "< 1e-12" if abs(float(x)) < 1e-12 else "%.3g" % float(x)


def _orient(V, F):
    """ConvexHull の面を、内部点から見て外向きにそろえる。"""
    c = np.mean(V, axis=0)
    F = np.asarray(F, dtype=int).copy()
    a, b, d = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    flip = np.einsum("ij,ij->i", np.cross(b-a, d-a), (a+b+d)/3-c) < 0
    F[flip] = F[flip][:, [0, 2, 1]]
    return F


def _convex_mesh(points):
    V = np.unique(np.round(np.asarray(points, float), 12), axis=0)
    h = ConvexHull(V)
    return V, _orient(V, h.simplices)


def hull_mesh(length=LENGTH, beam=BEAM, depth=DEPTH, nx=17, na=17):
    """平らな甲板と丸い船底を持つ、一般的な無名の合成船型。"""
    pts = []
    for x in np.linspace(-length/2, length/2, nx):
        taper = max(0.08, math.sqrt(max(0.0, 1.0-(2*x/length)**2)))
        for a in np.linspace(math.pi, 2*math.pi, na):
            pts.append([x, beam/2*taper*math.cos(a), depth*taper*math.sin(a)])
        pts.extend(([x, -beam/2*taper, 0.0], [x, beam/2*taper, 0.0]))
    return _convex_mesh(pts)


def box_mesh(length, beam, depth):
    V = np.array([[x, y, z] for x in (-length/2, length/2)
                  for y in (-beam/2, beam/2) for z in (-depth, 0.0)], float)
    return _convex_mesh(V)


def rotate_x(V, phi):
    c, s = math.cos(phi), math.sin(phi)
    R = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    return np.asarray(V) @ R.T


def clip_below(V, F, z=0.0):
    """凸メッシュを水平面以下へ切る。公開の平面切断 op が無いため NumPy で辺交点を作る。"""
    inside = V[:, 2] <= z + 1e-12
    pts = [p for p, ok in zip(V, inside) if ok]
    edges = np.vstack((F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]))
    edges = np.unique(np.sort(edges, axis=1), axis=0)
    for i, j in edges:
        zi, zj = V[i, 2]-z, V[j, 2]-z
        if zi*zj < 0:
            u = zi/(zi-zj)
            pts.append(V[i] + u*(V[j]-V[i]))
    if len(pts) < 4:
        raise ValueError("water plane does not cut a volume")
    return _convex_mesh(pts)


def volume_centroid(V, F):
    """体積は公開 op、浮心は同じ面の符号付き四面体の一次モーメント。"""
    vol_op = abs(float(fs.ledger.mesh_volume((V, F))))
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    v = np.einsum("ij,ij->i", a, np.cross(b, c))/6.0
    sv = float(np.sum(v))
    ctr = np.sum(v[:, None]*(a+b+c)/4.0, axis=0)/sv
    return vol_op, ctr


def submerged(V, F, heel, heave):
    W = rotate_x(V, heel) + np.array([0.0, 0.0, heave])
    C, CF = clip_below(W, F)
    vol, ctr = volume_centroid(C, CF)
    return vol, ctr, C, CF


def solve_heave(V, F, heel, target, iterations=60):
    lo, hi = -2*DEPTH, 2*DEPTH
    for _ in range(iterations):
        mid = (lo+hi)/2
        W = rotate_x(V, heel) + np.array([0.0, 0.0, mid])
        if np.min(W[:, 2]) >= 0:
            vol = 0.0
        elif np.max(W[:, 2]) <= 0:
            vol = abs(float(fs.ledger.mesh_volume((W, F))))
        else:
            vol, *_ = submerged(V, F, heel, mid)
        if vol < target:
            hi = mid
        else:
            lo = mid
    h = (lo+hi)/2
    return (h,) + submerged(V, F, heel, h)


def waterplane_moments(V):
    """z=0 の甲板輪郭から水線面積と縦軸まわり二次モーメントを測る。"""
    p = V[np.isclose(V[:, 2], 0.0)]
    h = ConvexHull(p[:, :2])
    q = p[h.vertices, :2]
    x, y = q[:, 0], q[:, 1]
    xn, yn = np.roll(x, -1), np.roll(y, -1)
    cr = x*yn-xn*y
    area = abs(np.sum(cr)/2)
    ix = abs(np.sum((y*y+y*yn+yn*yn)*cr)/12)
    return area, ix


def hydrostatic_gm(V, F, target, kg):
    h, vol, B, *_ = solve_heave(V, F, 0.0, target)
    W = rotate_x(V, 0.0) + [0, 0, h]
    # 水面との交点を取り直し、水線面の二次モーメントを測る。
    edges = np.vstack((F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]))
    pts = []
    for i, j in np.unique(np.sort(edges, axis=1), axis=0):
        if W[i, 2]*W[j, 2] < 0:
            u = W[i, 2]/(W[i, 2]-W[j, 2]); pts.append(W[i]+u*(W[j]-W[i]))
    p = np.asarray(pts); hp = ConvexHull(p[:, :2]); q = p[hp.vertices, :2]
    x, y = q[:, 0], q[:, 1]; xn, yn = np.roll(x,-1), np.roll(y,-1); cr=x*yn-xn*y
    iwp = abs(np.sum((y*y+y*yn+yn*yn)*cr)/12)
    kb = DEPTH + B[2] - h
    return dict(heave=h, volume=vol, B=B, KB=kb, Iwp=iwp, BM=iwp/vol, GM=kb+iwp/vol-kg)


def compute():
    V, F = hull_mesh()
    full = abs(float(fs.ledger.mesh_volume((V, F))))
    target = TARGET_FRACTION*full
    kg = 2.45
    angles = np.radians(np.linspace(0.0, 30.0, 49))
    hs, Bs, vols, wet = [], [], [], []
    for phi in angles:
        h, vol, B, C, CF = solve_heave(V, F, float(phi), target)
        hs.append(h); vols.append(vol); Bs.append(B); wet.append((C, CF))
    hs, vols, Bs = np.array(hs), np.array(vols), np.array(Bs)
    zg = -DEPTH + kg
    G = np.column_stack((np.zeros(len(angles)), -zg*np.sin(angles), zg*np.cos(angles)+hs))
    gz = G[:, 1]-Bs[:, 1]
    hydro = hydrostatic_gm(V, F, target, kg)
    high = hydrostatic_gm(V, F, target, hydro["KB"]+hydro["BM"]+0.35)
    # 箱形船を同じ経路で測り、閉形式と比較する。
    L, B, D, draft = 20.0, 8.0, 5.0, 2.0
    BV, BF = box_mesh(L, B, D)
    box_target = L*B*draft
    bh, bvol, bc, *_ = solve_heave(BV, BF, 0.0, box_target)
    box_kg = 1.7
    box_gm_mesh = -bc[2] + (L*B**3/12)/bvol - box_kg
    box_gm_closed = draft/2 + B**2/(12*draft) - box_kg
    dims = np.sort(2*np.asarray(fs.obb(V)["extents"]))[::-1]
    return dict(V=V,F=F,full=full,target=target,kg=kg,angles=angles,heaves=hs,B=Bs,volumes=vols,
                wet=wet,G=G,gz=gz,hydro=hydro,high=high,dims=dims,
                box=dict(volume=bvol, center=bc, gm_mesh=box_gm_mesh, gm_closed=box_gm_closed,
                         volume_closed=box_target, center_closed=np.array([0,0,-draft/2]), heave=bh))


def gates(r):
    b = r["box"]
    box_err = max(abs(b["volume"]-b["volume_closed"])/b["volume_closed"],
                  np.linalg.norm(b["center"]-b["center_closed"])/2.0,
                  abs(b["gm_mesh"]-b["gm_closed"])/abs(b["gm_closed"]))
    disp_err = float(np.max(np.abs(r["volumes"]-r["target"]))/r["target"])
    # 0, 0.625, 1.25, 1.875, 2.5° の原点通過最小二乗傾き。
    p = r["angles"][:5]; slope = float(np.dot(np.sin(p), r["gz"][:5])/np.dot(np.sin(p), np.sin(p)))
    gm_err = abs(slope-r["hydro"]["GM"])/abs(r["hydro"]["GM"])
    return dict(box_relative_error=box_err, displacement_relative_error=disp_err,
                small_angle_gm_relative_error=gm_err, small_angle_slope=slope,
                high_gm=r["high"]["GM"])


def _checks(g, limit=False):
    rows = [
        {"what":T("箱形船: 排水量・浮心・GM", "box hull: displacement, B and GM"), "criterion":"relative < 1e-9", "result":_e(g["box_relative_error"]), "ok":g["box_relative_error"]<1e-9},
        {"what":T("喫水探索後の排水量と指定重量", "searched displacement vs specified weight"), "criterion":"relative < 1e-6", "result":_e(g["displacement_relative_error"]), "ok":g["displacement_relative_error"]<1e-6},
        {"what":T("小傾斜 GZ の傾きとメッシュ GM", "small-angle GZ slope vs mesh GM"), "criterion":"relative < 2 %", "result":"%.3f %%"%(100*g["small_angle_gm_relative_error"]), "ok":g["small_angle_gm_relative_error"]<.02},
    ]
    if limit:
        rows.append({"what":T("高い重心でも船は戻る", "the ship returns even with a high centre of gravity"),
                     "criterion":T("GM > 0", "GM > 0"), "result":"GM = %.3f m"%g["high_gm"], "ok":False})
    return rows


def _lesson(q, choices, answer, explain, formula, limit):
    return {"question":q,"choices":choices,"answer":answer,"explain":explain,"formula":formula,"limit":limit}


def _poses(n, bodies):
    xyz=np.zeros((n,bodies,3)); q=np.zeros((n,bodies,4)); q[...,0]=1
    return xyz,q


def _box_visual(sx, sy, sz):
    return box_mesh(sx,sy,sz)


def _band(values, width=720, height=96):
    a=np.asarray(values,float); out=np.zeros((len(a),height,width,3),np.uint8)
    colors=((38,145,190),(244,174,42),(101,190,105))
    scale=max(np.max(np.abs(a)),1e-12)
    for k,row in enumerate(a):
        out[k]=(10,18,27)
        for j,v in enumerate(row):
            x0=j*width//len(row)+8; x1=(j+1)*width//len(row)-8
            h=int(abs(v)/scale*(height-18)); out[k,height-8-h:height-8,x0:x1]=colors[j%3]
    return out


def build_spec(r, g):
    n=len(r["angles"]); hullV,hullF=r["V"],r["F"]
    cargo,cargoF=_box_visual(8,5,1.2); water,waterF=_box_visual(90,28,.18)
    xyz,q=_poses(n,3); xyz[:,0,2]=r["heaves"]; xyz[:,1,2]=0; xyz[:,2,:]=r["G"]
    q[:,0,0]=np.cos(r["angles"]/2); q[:,0,1]=np.sin(r["angles"]/2)
    checks=_checks(g)
    tabs=[]
    tabs.append(pv.viewer_anim3d_tab("float",T("なぜ浮くか","Why it floats"),"passed",
        T("喫水を二分探索し、水面下メッシュの体積×水の密度が指定重量に合う位置で止める。青い帯が排水量、黄が重量で、重なる所が釣り合い。","Draft is found by bisection until submerged mesh volume times water density matches the specified weight. Blue displacement and yellow weight meet at equilibrium."),
        np.arange(n)/24,[{"name":"hull","pos":hullV,"faces":hullF,"rgb":[175,185,194],"alpha":.82},{"name":"water","pos":water,"faces":waterF,"rgb":[52,152,219],"alpha":.28},{"name":"G","pos":cargo,"faces":cargoF,"rgb":[255,183,77]}],xyz,q,
        series=[{"label":T("排水体積","displaced volume"),"values":r["volumes"],"unit":"m³","color":"#4fc3f7"}],
        panes=[{"label":T("青: 排水量、黄: 指定重量に相当する体積","blue: displacement; yellow: volume equivalent of specified weight"),"frames":_band(np.column_stack((r["volumes"],np.full(n,r["target"]))))}],
        numbers=[pv.viewer_number(T("指定した排水体積","specified displaced volume"),"%.1f m³"%r["target"]),pv.viewer_number(T("合成船型の寸法","synthetic hull dimensions"),"%.0f × %.0f × %.0f m"%tuple(r["dims"]))],checks=checks,
        axis={"values":np.degrees(r["angles"]),"segments":[{"k":0,"label":T("横傾斜角","heel angle"),"unit":"°","decimals":1}]},view={"az":-.8,"el":.35,"dist":1.2},
        lesson=_lesson(T("重さを増やすと喫水は?","What happens to draft when weight increases?"),[T("浅くなる","becomes shallower"),T("深くなる","becomes deeper")],1,T("押しのけた水の重さが船の重さに等しくなるまで沈む。","The hull sinks until the displaced water weighs as much as the ship."),T("ρ水 V排水 g = W","ρwater Vdisplaced g = W"),T("静水中の釣り合い。波、速度、船体の弾性は含めない。","Static water only; waves, forward speed and hull flexibility are omitted."))))
    tabs.append(pv.viewer_anim3d_tab("buoyancy",T("傾けると浮心はどこへ動く?","Where does B move when the hull heels?"),"passed",
        T("傾くたびに水面下の形を切り直す。浮心 B は水面下体積の中心なので、深く沈んだ側へ横移動し、重心 G との水平距離が復原てこ GZ になる。","The submerged shape is cut anew at every heel. Buoyancy centre B is its volume centroid; it moves toward the deeper side, and its horizontal distance from G is the righting arm GZ."),
        np.arange(n)/24,[{"name":"hull","pos":hullV,"faces":hullF,"rgb":[177,188,196],"alpha":.72},{"name":"water","pos":water,"faces":waterF,"rgb":[55,155,220],"alpha":.25},{"name":"cargo","pos":cargo,"faces":cargoF,"rgb":[255,183,77]}],xyz,q,
        trails=[{"xyz":r["B"],"color":"#40c4ff","tail":0},{"xyz":r["G"],"color":"#ffb74d","tail":0}],series=[{"label":T("GZ","GZ"),"values":r["gz"],"unit":"m","color":"#66bb6a"}],numbers=[pv.viewer_number(T("GM","GM"),"%.3f m"%r["hydro"]["GM"]),pv.viewer_number(T("BM","BM"),"%.3f m"%r["hydro"]["BM"])],checks=checks,axis={"values":np.degrees(r["angles"]),"segments":[{"k":0,"label":T("横傾斜角","heel angle"),"unit":"°","decimals":1}]},view={"az":-.8,"el":.35,"dist":1.2},
        lesson=_lesson(T("右へ傾くと浮心 B は?","When the hull heels right, where does B move?"),[T("深く沈む側へ","toward the deeper side"),T("重心に固定","fixed to G")],0,T("浮力は水面下体積の中心 B を通って上向きに働く。","Buoyancy acts upward through centroid B of the submerged volume."),T("GZ = yG − yB","GZ = yG − yB"),T("水面下形状は凸多面体近似。平面切断は NumPy、体積は mesh_volume で測った。","The submerged shape is a convex polyhedral approximation. NumPy performs the plane cut; mesh_volume measures volume."))))
    tabs.append(pv.viewer_anim3d_tab("gz",T("GZ 曲線と GM","GZ curve and GM"),"passed",
        T("緑が切断メッシュから直接得た GZ、橙が小傾斜式 GM sinφ。原点近くの傾きが GM で、30°まで離れる様子が小傾斜式の範囲も示す。","Green is GZ measured directly from clipped meshes; orange is the small-angle line GM sinφ. Its slope at the origin is GM, and separation toward 30° shows the formula's range."),
        np.arange(n)/24,[{"name":"hull","pos":hullV,"faces":hullF,"rgb":[180,190,200],"alpha":.72},{"name":"water","pos":water,"faces":waterF,"rgb":[55,155,220],"alpha":.24}],xyz[:,:2],q[:,:2],series=[{"label":T("切断メッシュの GZ","GZ from clipped mesh"),"values":r["gz"],"unit":"m","color":"#66bb6a"},{"label":T("GM sinφ","GM sinφ"),"values":r["hydro"]["GM"]*np.sin(r["angles"]),"unit":"m","color":"#ffb74d"}],numbers=[pv.viewer_number(T("メッシュから測った GM","GM measured from mesh"),"%.3f m"%r["hydro"]["GM"]),pv.viewer_number(T("小傾斜の傾き","small-angle slope"),"%.3f m"%g["small_angle_slope"])],checks=checks,axis={"values":np.degrees(r["angles"]),"segments":[{"k":0,"label":T("横傾斜角","heel angle"),"unit":"°","decimals":1}]},view={"az":-.8,"el":.4,"dist":1.2},
        lesson=_lesson(T("GM は GZ 曲線のどこに現れる?","Where does GM appear on the GZ curve?"),[T("原点の傾き","the slope at the origin"),T("30°の最大値だけ","only the value at 30°")],0,T("小傾斜では GZ/ sinφ が GM に近づく。","At small heel, GZ / sinφ approaches GM."),T("GZ ≈ GM sinφ","GZ ≈ GM sinφ"),T("大傾斜では水線形状が変わるため、小傾斜式だけでは足りない。","At large heel the waterplane changes, so the small-angle formula is insufficient."))))
    highG=r["hydro"]["KB"]+r["hydro"]["BM"]+0.35
    tabs.append(pv.viewer_anim3d_tab("limit",T("限界: 重心が高すぎる","Limit: centre of gravity too high"),"limit",
        T("荷物を高く積み、KG を KB+BM より 0.35 m 高くすると GM は負になる。最初の傾きで GZ も転倒側を向き、静かな水でも戻らない。","Raise the load so KG is 0.35 m above KB+BM and GM becomes negative. The first GZ points toward capsize, so the hull does not return even in calm water."),
        np.arange(n)/24,[{"name":"hull","pos":hullV,"faces":hullF,"rgb":[180,190,200],"alpha":.72},{"name":"water","pos":water,"faces":waterF,"rgb":[55,155,220],"alpha":.24},{"name":"high cargo","pos":cargo,"faces":cargoF,"rgb":[239,83,80]}],xyz,q,series=[{"label":T("不安定な小傾斜 GZ","unstable small-angle GZ"),"values":g["high_gm"]*np.sin(r["angles"]),"unit":"m","color":"#ef5350"}],numbers=[pv.viewer_number(T("高い重心 KG","raised KG"),"%.3f m"%highG),pv.viewer_number(T("GM","GM"),"%.3f m"%g["high_gm"])],checks=_checks(g,True),axis={"values":np.degrees(r["angles"]),"segments":[{"k":0,"label":T("横傾斜角","heel angle"),"unit":"°","decimals":1}]},view={"az":-.8,"el":.35,"dist":1.2},
        lesson=_lesson(T("GM < 0 の船を少し傾けると?","What happens after a small heel when GM < 0?"),[T("元へ戻る","it returns"),T("さらに傾く","it heels farther")],1,T("M が G より下なら、浮力と重力の組は傾きを増やす向きに働く。","With M below G, buoyancy and weight form a moment that increases heel."),T("GM = KB + BM − KG","GM = KB + BM − KG"),T("自由水影響、波、荷崩れ、浸水、30°超での甲板浸水は計算していない。実船の安全判定には使わない。","Free-surface effect, waves, cargo shift, flooding and deck immersion beyond 30° are not computed. Do not use this lesson for real-vessel safety decisions."))))
    return pv.viewer_spec("ship_stability",T("船はなぜ浮き、傾いても戻るのか","Why a ship floats and returns after heeling"),T("排水量・浮心 B・メタセンタ M・重心 G を同じ合成船型で追う","Track displacement, buoyancy centre B, metacentre M and centre of gravity G on one synthetic hull"),T("①問い → ②予想 → ③再生 → ④式 → ⑤限界。ドラッグで回転し、バッジで計算の門を見る。","Follow ① question → ② prediction → ③ play → ④ formula → ⑤ limit. Drag to orbit and open badges for computed gates."),tabs,credit=T("すべて合成。船型と長さ 72 m、幅 14 m、深さ 8 m、海水密度 1,025 kg/m³ は説明用の代表値として置いた仮定で、特定の船・造船所・標準船型を表さない。","Entirely synthetic. Hull shape, length 72 m, beam 14 m, depth 8 m and seawater density 1,025 kg/m³ are representative assumptions for explanation, not a specific vessel, yard or standard hull form."))


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__.splitlines()[0]); ap.add_argument("--check",action="store_true"); ap.add_argument("--out",default=str(OUT_HTML)); a=ap.parse_args(argv)
    r=compute(); g=gates(r)
    for k,v in g.items(): print("%-34s %s"%(k,v))
    spec=build_spec(r,g)
    if a.check:
        print("ok: %d bytes (not written)"%len(pv._build_html(spec,list(LANGS)).encode("utf-8"))); return 0
    path=pv.write_viewer(spec,a.out,list(LANGS)); print("wrote %s (%d bytes)"%(path,Path(path).stat().st_size)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
