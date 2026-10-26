# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""地上分解能 GSD と回折限界を比べる動く 3-D 学習ページ。"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import fullseye as fs
import pocviewer as pv
import optscene

OUT_HTML = ROOT / "docs" / "view2026" / "anim3d" / "satellite_gsd_anim3d.html"
LANGS = ("ja", "en")
LAM_NM = 550.0
PIXEL_UM = 5.0
FOCAL_M = 8.0
SEEING_URAD = 5.0


def T(ja, en):
    return pv.viewer_text(ja, en)


def _e(x):
    return "< 1e-12" if abs(float(x)) < 1e-12 else "%.3g" % float(x)


def gsd_m(height_km, pixel_um=PIXEL_UM, focal_m=FOCAL_M):
    return pixel_um * 1e-6 * height_km * 1e3 / focal_m


def rayleigh_ground_m(height_km, aperture_m, wavelength_nm=LAM_NM):
    return 1.22 * wavelength_nm * 1e-9 * height_km * 1e3 / aperture_m


def mtf50_ground_m(height_km, aperture_m, wavelength_nm=LAM_NM):
    n = FOCAL_M / aperture_m
    curve = fs.mtf_diffraction(n, wavelength_nm * 1e-3, 2048)
    freq = np.interp(0.5, curve[::-1, 1], curve[::-1, 0]) * 1e3 / FOCAL_M
    return 1.0 / (2.0 * freq) * height_km * 1e3


def _box(sx, sy, sz):
    p = np.array([[x, y, z] for x in (-sx/2, sx/2) for y in (-sy/2, sy/2) for z in (-sz/2, sz/2)], float)
    f = np.array([[0,1,3],[0,3,2],[4,6,7],[4,7,5],[0,4,5],[0,5,1],[2,3,7],[2,7,6],[0,2,6],[0,6,4],[1,5,7],[1,7,3]])
    return p, f


def _disk(radius=1.0, z=0.0, n=48):
    a = np.linspace(0, 2*np.pi, n, endpoint=False)
    p = np.vstack([[0,0,z], np.column_stack([radius*np.cos(a), radius*np.sin(a), np.full(n,z)])])
    f = np.array([[0, i+1, (i+1)%n+1] for i in range(n)])
    return p, f


def _cone(radius=1.0, height=2.0, n=48):
    a = np.linspace(0, 2*np.pi, n, endpoint=False)
    p = np.vstack([[0,0,height], np.column_stack([radius*np.cos(a), radius*np.sin(a), np.zeros(n)])])
    f = np.array([[0, i+1, (i+1)%n+1] for i in range(n)])
    return p, f


def _poses(T, B):
    xyz = np.zeros((T, B, 3), float)
    q = np.zeros((T, B, 4), float); q[..., 0] = 1
    return xyz, q


def _band(rows, width=720, height=96):
    out = np.zeros((len(rows), height, width, 3), np.uint8)
    cols = [(39,79,110),(28,113,136),(46,125,50),(230,126,34)]
    for k, values in enumerate(rows):
        out[k] = (10,18,27)
        for j, v in enumerate(values):
            x0, x1 = j*width//4+6, (j+1)*width//4-6
            h = int(np.clip(v, 0, 1)*(height-20))
            out[k, height-8-h:height-8, x0:x1] = cols[j]
    return out


def compute():
    heights = np.geomspace(400.0, 36000.0, 49)
    apertures = np.linspace(0.1, 2.4, 49)
    focals = np.linspace(0.5, 20.0, 49)
    gsd = np.array([gsd_m(h) for h in heights])
    ray_h = np.array([rayleigh_ground_m(h, 2.4) for h in heights])
    ray_d = np.array([rayleigh_ground_m(400.0, d) for d in apertures])
    gsd_f = PIXEL_UM*1e-6*400e3/focals
    ray_const = rayleigh_ground_m(400.0, 2.4)
    mtf50 = np.array([mtf50_ground_m(400.0, d) for d in apertures])
    # op に実際の F 値を渡して像面の Rayleigh 半径を得る。
    op_r = np.array([optscene.airy_radius_um(FOCAL_M/d, LAM_NM) for d in apertures])
    closed_r = 1.22*(LAM_NM*1e-3)*(FOCAL_M/apertures)
    # 10 cm 周期の縞をセンサー上でぼかす。表示用に 1 m/px として地上像を直接合成する。
    sign = np.zeros((96, 320), float)
    sign[:, ::20] = 1.0; sign[:, 1::20] = 1.0
    cams = []
    blur_frames = []
    for d in apertures:
        ground_px = 0.05
        image_pixel_um = ground_px*FOCAL_M/(400e3)*1e6
        cam = optscene.optical_camera(FOCAL_M*1e3, image_pixel_um, (320,96), 400e6)
        cams.append(cam)
        b = optscene.diffraction_blur(sign, cam, FOCAL_M/d, LAM_NM)
        blur_frames.append(np.clip(b*255,0,255).astype(np.uint8))
    return dict(heights=heights, apertures=apertures, focals=focals, gsd=gsd, ray_h=ray_h,
                ray_d=ray_d, gsd_f=gsd_f, ray_const=ray_const, mtf50=mtf50,
                op_r=op_r, closed_r=closed_r, blur=np.array(blur_frames), cameras=cams)


def gates(r):
    op_ground = r["op_r"]*1e-6*400e3/FOCAL_M
    ray_err = float(np.max(np.abs(op_ground-r["ray_d"])))
    gsd_image = PIXEL_UM*1e-6*400e3/FOCAL_M
    mono = float(np.max(np.diff(r["mtf50"])))
    contrast = (r["blur"].max(axis=(1,2))-r["blur"].min(axis=(1,2)))/255.0
    return {"gsd_formula_vs_pixel_m":abs(gsd_m(400)-gsd_image), "rayleigh_max_err_m":ray_err,
            "mtf50_monotonic_residual_m":max(0.0, mono), "contrast_start":float(contrast[0]),
            "contrast_end":float(contrast[-1]), "seeing_floor_m":SEEING_URAD*1e-6*400e3}


def _checks(g, limit=False):
    rows = [
        {"what":T("GSD 閉形式と像の 1 画素幅", "GSD closed form vs one image pixel"), "criterion":"< 1e-12 m", "result":_e(g["gsd_formula_vs_pixel_m"])+" m", "ok":g["gsd_formula_vs_pixel_m"]<1e-12},
        {"what":T("Rayleigh 半径: op と 1.22 λf/D", "Rayleigh radius: op vs 1.22 λf/D"), "criterion":"< 1e-9 m", "result":_e(g["rayleigh_max_err_m"])+" m", "ok":g["rayleigh_max_err_m"]<1e-9},
        {"what":T("口径を広げたときの MTF50 地上幅", "ground MTF50 width as aperture grows"), "criterion":T("単調に小さくなる", "decreases monotonically"), "result":_e(g["mtf50_monotonic_residual_m"])+" m", "ok":g["mtf50_monotonic_residual_m"]<1e-12},
    ]
    if limit:
        rows.append({"what":T("大気を通っても回折限界どおり", "diffraction limit still holds through the atmosphere"),
                     "criterion":T("シーイングを含む", "includes seeing"),
                     "result":T("未計算(仮定 5 µrad なら地上 2.00 m)", "not computed (assumed 5 µrad gives 2.00 m on ground)"), "ok":False})
    return rows


def _lesson(q, choices, answer, explain, formula, limit):
    return {"question":q,"choices":choices,"answer":answer,"explain":explain,"formula":formula,"limit":limit}


def build_spec(r, g):
    ground, gf = _box(10,10,.12); sat, sf = _box(.7,.7,.5)
    cone, cf = _cone(2.2,5.5)
    disk, df = _disk(1.0,.08)
    tabs=[]
    Tn=len(r["heights"])
    xyz,q=_poses(Tn,2); xyz[:,0,2]=-2.5; xyz[:,1,2]=np.linspace(2,8,Tn)
    tab=pv.viewer_anim3d_tab("height",T("高度を上げる","Raise the altitude"),"passed",
        T("同じカメラでも高度 400 km から 36,000 km へ離れると、1 画素が覆う地上幅は 0.25 m から 22.5 mへ広がる。地上板の格子が一つの画素へ畳み込まれる。",
          "With the same camera, moving from 400 km to 36,000 km widens one ground pixel from 0.25 m to 22.5 m. Ground-grid cells collapse into one pixel."),
        np.arange(Tn)/24,[{"name":"ground","pos":ground,"faces":gf,"rgb":[48,110,70]},{"name":"camera","pos":sat,"faces":sf,"rgb":[245,180,40]}],xyz,q,
        trails=[{"xyz":xyz[:,1,:],"color":"#ffd54f","tail":0}],series=[{"label":T("GSD","GSD"),"values":r["gsd"],"unit":"m","color":"#4fc3f7"}],
        panes=[{"label":T("計算の帯: 画素 → 焦点距離 → 高度 → GSD","calculation band: pixel → focal length → altitude → GSD"),"frames":_band(np.column_stack([np.ones(Tn),np.ones(Tn),np.linspace(.1,1,Tn),r["gsd"]/r["gsd"].max()]))}],
        numbers=[pv.viewer_number(T("400 km の GSD","GSD at 400 km"),"%.3f m"%r["gsd"][0]),pv.viewer_number(T("36,000 km の GSD","GSD at 36,000 km"),"%.1f m"%r["gsd"][-1])],checks=_checks(g),
        axis={"values":r["heights"],"segments":[{"k":0,"label":T("高度 H","altitude H"),"unit":"km","decimals":0}]},view={"az":-.8,"el":.35,"dist":1.1},
        lesson=_lesson(T("高度だけを 90 倍にすると、1 画素の地上幅は?","If altitude alone grows 90-fold, what happens to one ground pixel?"),[T("変わらない","unchanged"),T("90 倍","90 times wider"),T("9,000 倍","9,000 times wider")],1,T("GSD は高度 H に比例する。","GSD is proportional to altitude H."),T("GSD = p H / f","GSD = p H / f"),T("地球の曲率と斜め視線は省いた直下視の模型。","Nadir-view model; Earth curvature and oblique viewing are omitted.")))
    tabs.append(tab)

    n=len(r["apertures"]); xyz,q=_poses(n,2); xyz[:,0,2]=-2.5; xyz[:,1,2]=2.8
    # 円錐と地上 Airy 円板を口径に応じて見せる代わりに、円板を固定メッシュ、帯と数値を物理量に直結。
    tab=pv.viewer_anim3d_tab("aperture",T("口径と Airy 円板","Aperture and Airy disc"),"passed",
        T("高度 400 km、波長 550 nm では口径 0.1 m の Rayleigh 半径は 2.68 m、2.4 m なら 0.112 m。半透明の光円錐の底が地上の回折幅を表す。",
          "At 400 km and 550 nm, Rayleigh radius is 2.68 m for a 0.1 m aperture and 0.112 m for 2.4 m. The base of the translucent cone represents diffraction width on ground."),
        np.arange(n)/24,[{"name":"cone","pos":cone,"faces":cf,"rgb":[80,180,255],"alpha":.28},{"name":"airy","pos":disk,"faces":df,"rgb":[255,210,60],"alpha":.65}],xyz,q,
        series=[{"label":T("Rayleigh 地上半径","Rayleigh ground radius"),"values":r["ray_d"],"unit":"m","color":"#ffca28"},{"label":T("MTF50 地上幅","MTF50 ground width"),"values":r["mtf50"],"unit":"m","color":"#4fc3f7"}],
        panes=[{"label":T("計算の帯: λ → f/D → airy_radius_um → 地上幅","calculation band: λ → f/D → airy_radius_um → ground width"),"frames":_band(np.column_stack([np.ones(n),1-r["apertures"]/2.5,np.ones(n),r["ray_d"]/r["ray_d"].max()]))}],
        numbers=[pv.viewer_number(T("0.1 m 口径","0.1 m aperture"),"%.2f m"%r["ray_d"][0]),pv.viewer_number(T("2.4 m 口径","2.4 m aperture"),"%.3f m"%r["ray_d"][-1])],checks=_checks(g),axis={"values":r["apertures"],"segments":[{"k":0,"label":T("口径 D","aperture D"),"unit":"m","decimals":2}]},view={"az":-.75,"el":.35,"dist":.9},
        lesson=_lesson(T("口径を大きくすると Airy 円板は?","What happens to the Airy disc when aperture grows?"),[T("小さくなる","shrinks"),T("大きくなる","grows"),T("変わらない","unchanged")],0,T("角半径は D に反比例する。","Angular radius is inversely proportional to D."),T("r = 1.22 λ H / D","r = 1.22 λ H / D"),T("円形で遮蔽のない理想瞳、単色光を仮定。","Assumes an ideal unobstructed circular pupil and monochromatic light.")))
    tabs.append(tab)

    n=len(r["focals"]); xyz,q=_poses(n,2); xyz[:,0,0]=-1.2; xyz[:,1,0]=1.2
    tab=pv.viewer_anim3d_tab("cross",T("画素と回折、先に効くのは?","Pixels or diffraction: which limits first?"),"passed",
        T("焦点距離を伸ばすと GSD は改善するが、口径を変えなければ回折幅は地上で一定。交点より先では画素を細かくしても回折が先に線を混ぜる。",
          "Longer focal length improves GSD, but ground diffraction stays fixed if aperture is unchanged. Beyond the crossing, finer pixels cannot undo diffraction mixing."),
        np.arange(n)/24,[{"name":"pixel","pos":disk,"faces":df,"rgb":[80,190,250],"alpha":.55},{"name":"diffraction","pos":disk*1.08,"faces":df,"rgb":[255,160,70],"alpha":.45}],xyz,q,
        series=[{"label":T("GSD","GSD"),"values":r["gsd_f"],"unit":"m","color":"#4fc3f7","threshold":r["ray_const"]},{"label":T("回折半径","diffraction radius"),"values":np.full(n,r["ray_const"]),"unit":"m","color":"#ff8a65"}],
        panes=[{"label":T("青 = 画素、橙 = 回折。低い方だけ改善しても高い方が限界","blue = pixels, orange = diffraction; improving only the lower one leaves the higher limit"),"frames":_band(np.column_stack([np.ones(n),r["gsd_f"]/r["gsd_f"].max(),np.full(n,r["ray_const"]/r["gsd_f"].max()),np.maximum(r["gsd_f"],r["ray_const"])/r["gsd_f"].max()]))}],
        numbers=[pv.viewer_number(T("交点の焦点距離","focal length at crossing"),"%.2f m"%(PIXEL_UM*1e-6*400e3/r["ray_const"])),pv.viewer_number(T("回折半径","diffraction radius"),"%.3f m"%r["ray_const"])],checks=_checks(g),axis={"values":r["focals"],"segments":[{"k":0,"label":T("焦点距離 f","focal length f"),"unit":"m","decimals":1}]},view={"az":-.8,"el":.55,"dist":.8},
        lesson=_lesson(T("焦点距離だけを伸ばし続ければ、分解能は無限に良くなる?","Can resolution improve without limit by increasing focal length alone?"),[T("なる","yes"),T("回折幅で止まる","it stops at diffraction")],1,T("GSD が回折半径を下回ると口径が律速する。","Once GSD falls below the diffraction radius, aperture is the bottleneck."),T("有効幅 ≳ max(pH/f, 1.22λH/D)","effective width ≳ max(pH/f, 1.22λH/D)"),T("画素開口、収差、揺れ、圧縮は含めない。","Pixel aperture, aberrations, jitter and compression are omitted.")))
    tabs.append(tab)

    xyz,q=_poses(len(r["apertures"]),1)
    tab=pv.viewer_anim3d_tab("sign",T("10 cm の線は像に残る?","Does a 10 cm line survive?"),"limit",
        T("10 cm 幅の線を 5 cm/px で合成し、diffraction_blur の出力をそのまま表示する。小口径では隣の線と混ざり、大口径でコントラストが戻る。ただし大気は未計算。",
          "Synthetic 10 cm lines sampled at 5 cm/px are shown directly after diffraction_blur. Small apertures merge adjacent lines; contrast returns with a larger aperture. Atmosphere is not computed."),
        np.arange(len(r["apertures"]))/24,[{"name":"ground","pos":ground,"faces":gf,"rgb":[52,88,60]}],xyz,q,
        panes=[{"label":T("diffraction_blur の出力(10 cm 線)","diffraction_blur output (10 cm lines)"),"frames":r["blur"],"png":True,"wide":True}],
        series=[{"label":T("Rayleigh 地上半径","Rayleigh ground radius"),"values":r["ray_d"],"unit":"m","color":"#ffca28"}],numbers=[pv.viewer_number(T("仮定したシーイング床","assumed seeing floor"),"%.2f m"%g["seeing_floor_m"]),pv.viewer_number(T("線幅","line width"),"0.10 m")],checks=_checks(g,True),axis={"values":r["apertures"],"segments":[{"k":0,"label":T("口径 D","aperture D"),"unit":"m","decimals":2}]},view={"az":-.9,"el":.55,"dist":.8},
        lesson=_lesson(T("理想回折で線が見えても、実際の大気越しでも同じ?","If ideal diffraction resolves a line, will the atmosphere preserve it?"),[T("必ず同じ","always"),T("大気でさらにぼける","the atmosphere adds blur")],1,T("この像は回折だけ。仮に 5 µrad のシーイングなら 400 km で 2.00 mとなり、10 cm線よりはるかに太い。","This image includes diffraction only. Assumed 5 µrad seeing spans 2.00 m at 400 km, far wider than a 10 cm line."),T("大気幅 ≈ α H(ここでは α = 5 µrad と仮定)","atmospheric width ≈ α H (α = 5 µrad assumed here)"),T("これが限界の回。シーイング値は測定値でなく説明用の仮定で、回折限界どおりには見えない。","This is the limit tab. Seeing is an explanatory assumption, not a measurement; real images need not reach the diffraction limit.")))
    tabs.append(tab)
    return pv.viewer_spec("satellite_gsd",T("なぜ軌道上のカメラは小さな文字を読めないか","Why an orbital camera cannot read tiny lettering"),T("地上分解能 GSD と回折限界を、同じ地上幅で比べる","Compare ground sampling distance and diffraction in the same ground units"),T("①問い → ②予想 → ③再生 → ④式 → ⑤限界。ドラッグで回転し、バッジで計算の門を見る。","Follow ① question → ② prediction → ③ play → ④ formula → ⑤ limit. Drag to orbit; tap a badge for computed gates."),tabs,credit=T("すべて合成。高度、口径、波長、画素ピッチ、焦点距離、シーイングは一般的な代表値として置いた仮定で、特定の機体・製品・運用者を表さない。","Entirely synthetic. Altitude, aperture, wavelength, pixel pitch, focal length and seeing are assumed representative values, not any specific vehicle, product or operator."))


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
