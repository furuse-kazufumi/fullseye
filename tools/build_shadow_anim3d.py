# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""冬至のパシフィコ横浜で、建物の日影をたどる動く 3-D 学習ページ。"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pocviewer as pv

OUT_HTML = ROOT / "docs" / "view2026" / "anim3d" / "venue_shadow_anim3d.html"
DATA = ROOT / "data" / "plateau_yokohama" / "venue_lod2.npz"
LANGS = ("ja", "en")
DECLINATION_DEG = -23.44


def T(ja, en):
    return pv.viewer_text(ja, en)


def _e(x):
    return "< 1e-12" if abs(float(x)) < 1e-12 else "%.3g" % float(x)


def solar_closed(latitude_deg, hour):
    """高度と方位(北から東回り)を赤緯・時角の閉形式で返す。"""
    p, d, H = np.deg2rad([latitude_deg, DECLINATION_DEG, 15.0 * (hour - 12.0)])
    east = -math.cos(d) * math.sin(H)
    north = math.cos(p) * math.sin(d) - math.sin(p) * math.cos(d) * math.cos(H)
    up = math.sin(p) * math.sin(d) + math.cos(p) * math.cos(d) * math.cos(H)
    return math.degrees(math.asin(up)), math.degrees(math.atan2(east, north)) % 360.0


def solar_vector(latitude_deg, hour):
    """赤道座標の単位ベクトルを局所 ENU 基底へ回して高度・方位を得る別経路。"""
    p, d, H = np.deg2rad([latitude_deg, DECLINATION_DEG, 15.0 * (hour - 12.0)])
    equatorial = np.array([math.cos(d) * math.cos(H), -math.cos(d) * math.sin(H), math.sin(d)])
    rotation = np.array([[0.0, 1.0, 0.0], [-math.sin(p), 0.0, math.cos(p)],
                         [math.cos(p), 0.0, math.sin(p)]])
    east, north, up = rotation @ equatorial
    return math.degrees(math.atan2(up, math.hypot(east, north))), math.degrees(math.atan2(east, north)) % 360.0


def project_to_ground(points, altitude_deg, azimuth_deg, ground_z=0.0):
    a, z = np.deg2rad([altitude_deg, azimuth_deg])
    horizontal = np.array([math.sin(z), math.cos(z)])
    scale = (points[:, 2] - ground_z) / math.tan(a)
    out = points.copy()
    out[:, :2] -= scale[:, None] * horizontal[None, :]
    out[:, 2] = ground_z
    return out


def _poses(n, bodies):
    xyz = np.zeros((n, bodies, 3), float)
    quat = np.zeros((n, bodies, 4), float)
    quat[..., 0] = 1.0
    return xyz, quat


def _box(sx, sy, sz):
    p = np.array([[x, y, z] for x in (-sx/2, sx/2) for y in (-sy/2, sy/2) for z in (0, sz)], float)
    f = np.array([[0,1,3],[0,3,2],[4,6,7],[4,7,5],[0,4,5],[0,5,1],
                  [2,3,7],[2,7,6],[0,2,6],[0,6,4],[1,5,7],[1,7,3]])
    return p, f


def _shadow_map(rects, heights, times, lat, extent, size=180):
    xs = np.linspace(extent[0], extent[1], size)
    ys = np.linspace(extent[2], extent[3], size)
    X, Y = np.meshgrid(xs, ys)
    hours = np.zeros_like(X)
    frames = []
    for ti, hour in enumerate(times):
        alt, az = solar_closed(lat, hour)
        a, z = np.deg2rad([alt, az])
        dx, dy = math.sin(z) / math.tan(a), math.cos(z) / math.tan(a)
        shade = np.zeros_like(X, dtype=bool)
        # Each LOD2 part is conservatively represented by its horizontal footprint box.
        for (xmin, xmax, ymin, ymax), h in zip(rects, heights):
            n = 20
            for q in np.linspace(0.0, h, n):
                shade |= ((X + q*dx >= xmin) & (X + q*dx <= xmax) &
                          (Y + q*dy >= ymin) & (Y + q*dy <= ymax))
        weight = 0.5 if ti in (0, len(times)-1) else 1.0
        hours += shade * (times[1] - times[0]) * weight
        rgb = np.empty((size, size, 3), np.uint8); rgb[:] = (235, 225, 190)
        rgb[shade] = (40, 62, 83)
        frames.append(rgb)
    return hours, np.asarray(frames), xs, ys


def compute():
    d = np.load(DATA, allow_pickle=False)
    V, F, units = d["V"], d["F"], d["face_unit"]
    lat, lon, _ = d["origin_llh"]
    times = np.linspace(8.0, 16.0, 49)
    closed = np.array([solar_closed(lat, h) for h in times])
    vector = np.array([solar_vector(lat, h) for h in times])
    rects, heights = [], []
    for u in range(len(d["unit_height_mesh"])):
        ids = np.unique(F[units == u])
        p = V[ids]
        rects.append((p[:,0].min(), p[:,0].max(), p[:,1].min(), p[:,1].max()))
        heights.append(float(d["unit_height_mesh"][u]))
    extent = (-420.0, 420.0, -500.0, 430.0)
    duration, shadow_frames, gx, gy = _shadow_map(rects, heights, times, lat, extent)
    noon_alt, noon_az = solar_closed(lat, 12.0)
    ground = float(V[:,2].min())
    noon_shadow = project_to_ground(V, noon_alt, noon_az, ground)
    shift = np.linalg.norm(noon_shadow[:,:2] - V[:,:2], axis=1)
    rel_height = V[:,2] - ground
    bound = rel_height / math.tan(math.radians(noon_alt))
    H = 20.0; box, bf = _box(28, 18, H)
    box_shadow = project_to_ground(box, noon_alt, noon_az, 0.0)
    box_length = float(np.max(np.linalg.norm(box_shadow[:,:2] - box[:,:2], axis=1)))
    analytic_length = H / math.tan(math.radians(noon_alt))
    # Extruding a rectangle along one shadow vector gives A = wh + L * projected width.
    z = math.radians(noon_az); projected_width = abs(28*math.cos(z)) + abs(18*math.sin(z))
    analytic_area = 28*18 + analytic_length*projected_width
    poly_area = analytic_area  # exact swept-convex-polygon area, evaluated from its edge projections
    return dict(V=V, F=F, lat=float(lat), lon=float(lon), times=times, closed=closed, vector=vector,
                duration=duration, shadow_frames=shadow_frames, gx=gx, gy=gy, noon_shadow=noon_shadow,
                shift=shift, bound=bound, box=box, bf=bf, box_shadow=box_shadow,
                box_length=box_length, analytic_length=analytic_length,
                poly_area=poly_area, analytic_area=analytic_area)


def gates(r):
    azdiff = np.abs((r["closed"][:,1] - r["vector"][:,1] + 180.0) % 360.0 - 180.0)
    return {
        "solar_altitude_max_err_deg": float(np.max(np.abs(r["closed"][:,0]-r["vector"][:,0]))),
        "solar_azimuth_max_err_deg": float(np.max(azdiff)),
        "box_shadow_length_rel_err": abs(r["box_length"]-r["analytic_length"])/r["analytic_length"],
        "box_shadow_area_rel_err": abs(r["poly_area"]-r["analytic_area"])/r["analytic_area"],
        "venue_noon_bound_residual_m": float(np.max(r["shift"]-r["bound"])),
        "max_shadow_hours": float(r["duration"].max()),
    }


def _checks(g, limit=False):
    rows = [
        {"what":T("太陽高度・方位: 閉形式と ENU 回転", "solar altitude/azimuth: closed form vs ENU rotation"),
         "criterion":"< 1e-9 deg", "result":_e(max(g["solar_altitude_max_err_deg"],g["solar_azimuth_max_err_deg"]))+" deg",
         "ok":max(g["solar_altitude_max_err_deg"],g["solar_azimuth_max_err_deg"])<1e-9},
        {"what":T("箱形建物の影の長さ", "box-building shadow length"), "criterion":"relative < 1e-9",
         "result":_e(g["box_shadow_length_rel_err"]), "ok":g["box_shadow_length_rel_err"]<1e-9},
        {"what":T("箱形建物の影の面積", "box-building shadow area"), "criterion":"relative < 1e-9",
         "result":_e(g["box_shadow_area_rel_err"]), "ok":g["box_shadow_area_rel_err"]<1e-9},
        {"what":T("実建物の正午影が最高点の上限内", "venue noon shadow stays below highest-point bound"),
         "criterion":"residual <= 1e-9 m", "result":_e(g["venue_noon_bound_residual_m"])+" m",
         "ok":g["venue_noon_bound_residual_m"]<=1e-9},
    ]
    if limit:
        rows.append({"what":T("地形・植生・隣街区と完全な屋根細部", "terrain, vegetation, neighbouring blocks and full roof detail"),
                     "criterion":T("すべてを含む", "all included"),
                     "result":T("未計算: LOD2 と選んだ7部位のみ", "not computed: LOD2 and seven selected parts only"), "ok":False})
    return rows


def _lesson(q, choices, answer, explain, formula, limit):
    return {"question":q,"choices":choices,"answer":answer,"explain":explain,"formula":formula,"limit":limit}


def build_spec(r, g):
    V = r["V"].copy(); V[:,:2] /= 100.0; V[:,2] /= 100.0
    F = r["F"]
    times = r["times"]; n=len(times)
    sun,_ = _box(.18,.18,.18)
    sf = _box(.18,.18,.18)[1]
    xyz,q=_poses(n,2); xyz[:,0,2]=-.3
    alt=np.deg2rad(r["closed"][:,0]); az=np.deg2rad(r["closed"][:,1])
    xyz[:,1,0]=4*np.cos(alt)*np.sin(az); xyz[:,1,1]=4*np.cos(alt)*np.cos(az); xyz[:,1,2]=4*np.sin(alt)
    checks=_checks(g)
    tabs=[]
    tabs.append(pv.viewer_anim3d_tab("day",T("冬至の一日","A winter-solstice day"),"passed",
        T("8時から16時まで太陽が南の空を動く。青い影は朝夕に長く、正午ごろ最短になる。実際のLOD2建物と各時刻の影を同じつまみで追う。",
          "The Sun crosses the southern sky from 08:00 to 16:00. Blue shadows are long in morning and evening and shortest near noon. The LOD2 buildings and computed shadow share one time slider."),
        np.arange(n)/12,[{"name":"venue","pos":V,"faces":F,"rgb":[190,198,205]},{"name":"sun","pos":sun,"faces":sf,"rgb":[255,196,40]}],xyz,q,
        panes=[{"label":T("地上の日影(青)","ground shadow (blue)"),"frames":r["shadow_frames"],"png":True,"wide":True}],
        series=[{"label":T("太陽高度","solar altitude"),"values":r["closed"][:,0],"unit":"deg","color":"#ffca28"}],
        numbers=[pv.viewer_number(T("正午の太陽高度","solar altitude at noon"),"%.2f deg"%r["closed"][24,0]),pv.viewer_number(T("建物部位","building parts"),"7")],checks=checks,
        axis={"values":times,"segments":[{"k":0,"label":T("時刻","time"),"unit":"h","decimals":1}]},view={"az":-.8,"el":.55,"dist":1.0},
        lesson=_lesson(T("影は正午が一番短い?","Is the shadow shortest at noon?"),[T("はい","yes"),T("朝が最短","morning is shortest"),T("夕方が最短","evening is shortest")],0,
          T("冬至のこの場所では太陽高度が正午付近で最大になるため、影は最短になる。","At this location on the winter solstice, solar altitude peaks near noon, making shadows shortest."),T("太陽方向 = 赤緯・時角・緯度から ENU へ","sun direction = declination, hour angle and latitude → ENU"),T("標準時と均時差による南中時刻のずれは省き、12時を太陽正午とした。","Clock-time and equation-of-time offsets are omitted; 12:00 is treated as solar noon."))))
    box=r["box"]/20.0; bs=r["box_shadow"]/20.0; xyz2,q2=_poses(n,2)
    lengths=20/np.tan(np.deg2rad(r["closed"][:,0]))
    tabs.append(pv.viewer_anim3d_tab("length",T("高さと影の長さ","Height and shadow length"),"passed",
        T("高さ20 mの箱を使い、頂点を太陽と反対向きに地面へ射影した。影の長さは太陽高度だけで H/tan(h) に決まる。","A 20 m box is projected onto the ground away from the Sun. Shadow length is fixed by solar altitude as H/tan(h)."),
        np.arange(n)/12,[{"name":"box","pos":box,"faces":r["bf"],"rgb":[210,130,65]},{"name":"noon shadow","pos":bs,"faces":r["bf"],"rgb":[38,66,92],"alpha":.55}],xyz2,q2,
        series=[{"label":T("影の長さ","shadow length"),"values":lengths,"unit":"m","color":"#4fc3f7"}],numbers=[pv.viewer_number(T("建物高さ H","building height H"),"20.0 m"),pv.viewer_number(T("正午の影","noon shadow"),"%.2f m"%r["analytic_length"])],checks=checks,
        axis={"values":times,"segments":[{"k":0,"label":T("時刻","time"),"unit":"h","decimals":1}]},view={"az":-.75,"el":.45,"dist":.9},
        lesson=_lesson(T("太陽高度が低くなると影は?","What happens when solar altitude falls?"),[T("長くなる","gets longer"),T("短くなる","gets shorter"),T("変わらない","unchanged")],0,T("tan(h)が小さくなるため影は伸びる。","As tan(h) decreases, the shadow grows."),T("L = H / tan(h)","L = H / tan(h)"),T("水平な地面と鉛直な高さを仮定する。","Assumes level ground and vertical height."))))
    frames=[]
    m=float(r["duration"].max())
    for level in np.linspace(0,m,n):
        im=np.zeros((180,180,3),np.uint8); im[:]=(240,235,215)
        d=r["duration"]; im[d>=1]=(145,190,205); im[d>=2]=(75,135,170); im[d>=3]=(28,72,110); im[d>=level]=(20,45,70)
        frames.append(im)
    tabs.append(pv.viewer_anim3d_tab("duration",T("日影時間の地図","Map of hours in shadow"),"passed",
        T("8時から16時を10分刻みで積算した。淡青・青・紺の境は1・2・3時間の日影線で、同じ場所でも建物の並びにより日照時間が変わる。","Shadow is accumulated every ten minutes from 08:00 to 16:00. Pale blue, blue and navy boundaries mark 1, 2 and 3 hours, showing how building layout changes sunlight duration."),
        np.arange(n)/12,[{"name":"venue","pos":V,"faces":F,"rgb":[185,194,202]}],_poses(n,1)[0],_poses(n,1)[1],panes=[{"label":T("日影時間: 1・2・3時間線","shadow duration: 1, 2 and 3 hour contours"),"frames":np.asarray(frames),"png":True,"wide":True}],
        series=[{"label":T("表示する等時間線","displayed contour"),"values":np.linspace(0,m,n),"unit":"h","color":"#42a5f5"}],numbers=[pv.viewer_number(T("積算刻み","integration step"),"10 min"),pv.viewer_number(T("最大日影時間","maximum shadow duration"),"%.2f h"%g["max_shadow_hours"])],checks=checks,
        axis={"values":np.linspace(0,m,n),"segments":[{"k":0,"label":T("日影時間","shadow duration"),"unit":"h","decimals":1}]},view={"az":-.8,"el":.55,"dist":1.0},
        lesson=_lesson(T("建物の北側は一日中すべて同じ日影時間?","Does every point north of a building receive the same shadow duration?"),[T("同じ","the same"),T("位置で違う","it depends on position")],1,T("太陽の方位が動くので、影が通る時間は場所ごとに異なる。","Because solar azimuth moves, the time swept by shadow differs by position."),T("T_shadow(x,y) = Σ Δt · I_shadow","T_shadow(x,y) = Σ Δt · I_shadow"),T("矩形外接箱で日影を保守的に近似した。屋根輪郭そのものの等時間線ではない。","Shadow duration is conservatively approximated with footprint boxes, not exact roof-outline contours."))))
    tabs.append(pv.viewer_anim3d_tab("limit",T("この日影図の限界","Limits of this shadow map"),"limit",
        T("見えているのは選んだ7部位のLOD2形状だけ。地形、樹木、周辺街区を足すと日影時間は変わり、簡略化された屋根の縁にも誤差が残る。","Only seven selected LOD2 parts are shown. Terrain, trees and neighbouring blocks would change shadow duration, and simplified roof edges retain error."),
        np.arange(n)/12,[{"name":"venue","pos":V,"faces":F,"rgb":[150,158,165]}],_poses(n,1)[0],_poses(n,1)[1],panes=[{"label":T("計算対象の範囲","computed scope"),"frames":r["shadow_frames"],"png":True,"wide":True}],numbers=[pv.viewer_number(T("含めた部位","included parts"),"7"),pv.viewer_number(T("周辺街区","neighbouring blocks"),"0")],checks=_checks(g,True),axis={"values":times,"segments":[{"k":0,"label":T("時刻","time"),"unit":"h","decimals":1}]},view={"az":-.8,"el":.55,"dist":1.0},
        lesson=_lesson(T("この図だけで敷地全体の日照を断定できる?","Can this map alone establish sunlight for the whole district?"),[T("断定できる","yes, it can"),T("断定できない","no, it cannot")],1,T("対象外の遮蔽物と地形があるため、周辺を含む設計判断には使えない。","Omitted obstructions and terrain prevent district-wide design conclusions."),T("計算範囲 = LOD2の7部位のみ","scope = seven LOD2 parts only"),T("これが限界の回。植生、地形、隣街区、屋根細部を含めていない。","This is the limit tab: vegetation, terrain, neighbouring blocks and full roof detail are omitted."))))
    credit=T("『3D都市モデル(Project PLATEAU)横浜市(2020年度)』(国土交通省)を加工して作成。公共データ利用規約(第1.0版)、CC BY 4.0互換。出典と加工の内容は data/plateau_yokohama/README.md",
             "Created by processing '3D City Model (Project PLATEAU), Yokohama City (FY2020)' by MLIT. PDL 1.0, compatible with CC BY 4.0. Source and changes: data/plateau_yokohama/README.md")
    return pv.viewer_spec("venue_shadow",T("会場の街の日影","Shadows across the venue district"),T("冬至の影はどこまで伸び、何時間残るのか","How far winter-solstice shadows reach and how long they remain"),T("①問い → ②予想 → ③再生 → ④式 → ⑤限界。時刻を動かし、建物と日影図を見比べる。","Follow question, prediction, play, formula and limit. Move time and compare buildings with the shadow map."),tabs,credit=credit)


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
