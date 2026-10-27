# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""架線トロリ線の摩耗を走行中のラインカメラ像から測る動く 3-D 教材。"""
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

OUT_HTML = ROOT / "docs" / "view2026" / "anim3d" / "catenary_wear_anim3d.html"
LANGS = ("ja", "en")
RADIUS_MM = 6.0
MM_PER_PIXEL = 0.08
NFRAMES = 36
CAMERA_Z_MM = -120.0
FOCAL_PX = abs(CAMERA_Z_MM) / MM_PER_PIXEL
PSF_SIGMA_PX = 1.05
SUBPIXELS = 7


def T(ja, en):
    return pv.viewer_text(ja, en)


def _e(x):
    return "< 1e-12" if abs(float(x)) < 1e-12 else "%.4f" % float(x)


def remaining_height(width_mm):
    """円弧の弦幅から、摩耗面を含む残存高さを返す。"""
    w = np.asarray(width_mm, float)
    return RADIUS_MM + np.sqrt(np.maximum(0.0, RADIUS_MM**2 - (w / 2.0)**2))


def _measure_row(row):
    """真値を使わず、行自身の分位点から閾値とサブピクセル端点を求める。"""
    lo, hi = np.percentile(row, (15, 98))
    threshold = lo + 0.50 * (hi - lo)
    above = np.flatnonzero(row >= threshold)
    if len(above) < 2:
        return np.nan, np.nan
    a, b = int(above[0]), int(above[-1])
    left = (a - 1) + (threshold - row[a - 1]) / (row[a] - row[a - 1]) if a else float(a)
    right = b + (threshold - row[b]) / (row[b + 1] - row[b]) if b + 1 < len(row) else float(b)
    return 0.5 * (left + right), right - left


def _blur_1d(row, sigma=PSF_SIGMA_PX):
    radius = int(math.ceil(4.0 * sigma))
    x = np.arange(-radius, radius + 1, dtype=float)
    kernel = np.exp(-0.5 * (x / sigma)**2)
    kernel /= kernel.sum()
    return np.convolve(np.pad(row, radius, mode="edge"), kernel, mode="valid")


def _render_section(remaining_height_mm, stagger_mm, rng):
    """Render one camera row by intersecting subpixel rays with the worn circle.

    The image is not painted from chord width.  Each ray meets either the flat
    underside or the remaining circular arc; its normal drives Lambertian and
    Blinn-Phong terms under an oblique light.  Subpixel samples are integrated
    into detector pixels before optical blur and read noise are applied.
    """
    cut_z = 2.0 * RADIUS_MM - float(remaining_height_mm)
    half_chord = math.sqrt(max(0.0, RADIUS_MM**2 - (cut_z - RADIUS_MM)**2))
    offsets = (np.arange(SUBPIXELS, dtype=float) + 0.5) / SUBPIXELS - 0.5
    u = (np.arange(240, dtype=float)[:, None] + offsets[None, :]) - 119.37
    slope = u / FOCAL_PX
    cam_x = -float(stagger_mm)

    # Candidate intersection with the worn flat, followed by the lower-circle
    # quadratic intersection. Coordinates are local to the translated section.
    x_flat = cam_x + slope * (cut_z - CAMERA_Z_MM)
    use_flat = np.abs(x_flat) <= half_chord
    a = slope * slope + 1.0
    b = 2.0 * (slope * cam_x - slope * CAMERA_Z_MM - RADIUS_MM)
    c = cam_x * cam_x + (CAMERA_Z_MM + RADIUS_MM)**2 - RADIUS_MM**2
    raw_disc = b * b - 4.0 * a * c
    disc = np.maximum(0.0, raw_disc)
    z_circle = (-b - np.sqrt(disc)) / (2.0 * a)
    x_circle = cam_x + slope * (z_circle - CAMERA_Z_MM)
    hit_circle = (raw_disc >= 0.0) & (np.abs(x_circle) <= RADIUS_MM + 1e-9)
    x = np.where(use_flat, x_flat, x_circle)
    z = np.where(use_flat, cut_z, z_circle)

    nx = np.where(use_flat, 0.0, x / RADIUS_MM)
    nz = np.where(use_flat, -1.0, (z - RADIUS_MM) / RADIUS_MM)
    # Surface-to-light and surface-to-camera directions.  The finite camera
    # position naturally changes the view direction when stagger moves the wire.
    light = np.array([-0.42, -0.9075]); light /= np.linalg.norm(light)
    vx = cam_x - x; vz = CAMERA_Z_MM - z
    vl = np.sqrt(vx * vx + vz * vz); vx /= vl; vz /= vl
    lambert = np.maximum(0.0, nx * light[0] + nz * light[1])
    hx = light[0] + vx; hz = light[1] + vz
    hl = np.sqrt(hx * hx + hz * hz); hx /= hl; hz /= hl
    specular = np.maximum(0.0, nx * hx + nz * hz)**70
    radiance = 9.0 + 22.0 * lambert + 245.0 * specular
    radiance = np.where(use_flat | hit_circle, radiance, 9.0)
    integrated = radiance.mean(axis=1)
    blurred = _blur_1d(integrated)
    return np.clip(blurred + rng.normal(0.0, 2.2, blurred.size), 0.0, 255.0), 2.0 * half_chord


def synthesize(offset=True):
    rng = np.random.default_rng(20261027 + int(offset))
    distance = np.linspace(0.0, 180.0, NFRAMES)
    wear_depth = 0.09 + 0.16 * np.exp(-0.5 * ((distance - 108.0) / 25.0)**2)
    true_height = 2.0 * RADIUS_MM - wear_depth
    stagger_mm = np.zeros(NFRAMES) if not offset else 4.5 * np.sin(2 * np.pi * distance / 90.0)
    rendered = [_render_section(h, s, rng) for h, s in zip(true_height, stagger_mm)]
    rows = [v[0] for v in rendered]
    true_width = np.asarray([v[1] for v in rendered])
    image = np.asarray(rows)
    measured = np.asarray([_measure_row(row) for row in image])
    measured_width = measured[:, 1] * MM_PER_PIXEL
    measured_height = remaining_height(measured_width)
    return dict(distance=distance, true_width=true_width, stagger=stagger_mm, image=image,
                centre_px=measured[:, 0], measured_width=measured_width,
                true_height=true_height, measured_height=measured_height)


def compute():
    shifted = synthesize(True)
    centred = synthesize(False)
    return shifted, centred


def gates(result):
    r, base = result
    width_error = np.abs(r["measured_width"] - r["true_width"])
    height_error = np.abs(r["measured_height"] - r["true_height"])
    invariance = np.abs(r["measured_width"] - base["measured_width"])
    # One pixel of sampling, a two-sided PSF edge allowance and a reflectance
    # threshold allowance form the disclosed bound; no measured error enters it.
    tolerance = MM_PER_PIXEL + 2.0 * PSF_SIGMA_PX * MM_PER_PIXEL + 0.08
    return {"width_max_error_mm": float(np.max(width_error)),
            "width_tolerance_mm": tolerance,
            "height_max_error_mm": float(np.max(height_error)),
            "height_tolerance_mm": tolerance,
            "stagger_width_max_diff_mm": float(np.max(invariance)),
            "stagger_tolerance_mm": tolerance * 1.25,
            "rows": int(len(r["distance"]))}


def _box(size):
    sx, sy, sz = np.asarray(size, float) / 2
    p = np.array([[x, y, z] for x in (-sx, sx) for y in (-sy, sy) for z in (-sz, sz)])
    f = np.array([[0,1,3],[0,3,2],[4,6,7],[4,7,5],[0,4,5],[0,5,1],[2,3,7],[2,7,6],[0,2,6],[0,6,4],[1,5,7],[1,7,3]])
    return p, f


def _tube_curve(points, radius=.045, sides=8):
    p = np.asarray(points, float); verts=[]; faces=[]
    for x, y, z in p:
        for j in range(sides):
            a=2*math.pi*j/sides; verts.append([x, y+radius*math.cos(a), z+radius*math.sin(a)])
    for i in range(len(p)-1):
        for j in range(sides):
            k=(j+1)%sides; a=i*sides+j; b=(i+1)*sides+j
            faces += [[a,b,b-j+k],[a,b-j+k,a-j+k]]
    return np.asarray(verts), np.asarray(faces)


def _scene(r):
    s=np.linspace(-5,5,41); sag=.18*(np.cosh(s/3)-1); zig=.65*np.sin(np.pi*(s+5)/5)
    wire,wf=_tube_curve(np.c_[s,zig,3.0-sag]); roof,rf=_box((3.2,5.0,.18)); arm,af=_box((.10,1.7,1.1)); cam,cf=_box((.42,.42,.28))
    bodies=[{"name":"contact wire","pos":wire,"faces":wf,"rgb":[230,175,70]},
            {"name":"synthetic roof","pos":roof,"faces":rf,"rgb":[75,95,116]},
            {"name":"pantograph","pos":arm,"faces":af,"rgb":[220,90,75]},
            {"name":"line camera","pos":cam,"faces":cf,"rgb":[55,190,220]}]
    xyz=np.zeros((NFRAMES,4,3)); q=np.zeros((NFRAMES,4,4)); q[...,0]=1
    xyz[:,1]=[0,0,-.2]; xyz[:,2]=[0,0,1.25]; xyz[:,3]=[0,0,.35]
    xyz[:,0,1]=r["stagger"] / 43.0
    return bodies,xyz,q


def _checks(g, limit=False):
    rows=[
      {"what":T("画像から測った帯幅","band width measured from the image"),"criterion":"< %.3f mm"%g["width_tolerance_mm"],"result":"%.4f mm"%g["width_max_error_mm"],"ok":g["width_max_error_mm"]<g["width_tolerance_mm"]},
      {"what":T("帯幅から換算した残存高さ","remaining height converted from band width"),"criterion":"< %.3f mm"%g["height_tolerance_mm"],"result":"%.4f mm"%g["height_max_error_mm"],"ok":g["height_max_error_mm"]<g["height_tolerance_mm"]},
      {"what":T("偏位あり・なしでの幅の差","width difference with and without stagger"),"criterion":"< %.3f mm"%g["stagger_tolerance_mm"],"result":"%.4f mm"%g["stagger_width_max_diff_mm"],"ok":g["stagger_width_max_diff_mm"]<g["stagger_tolerance_mm"]}]
    if limit:
        rows.append({"what":T("雨・汚れ・振動・斜め視でも正しい幅になる","width remains correct with rain, dirt, vibration and oblique viewing"),"criterion":T("現場条件を含める","include field conditions"),"result":T("未計算: 反射低下と投影誤差を別に評価する","not computed: evaluate reflectance loss and projection bias separately"),"ok":False})
    return rows


def _lesson(q, choices, answer, explain, formula, limit):
    return {"question":q,"choices":choices,"answer":answer,"explain":explain,"formula":formula,"limit":limit}


def build_spec(result, g):
    r,_=result; bodies,xyz,q=_scene(r); t=np.arange(NFRAMES)/12.0
    axis={"values":r["distance"],"segments":[{"k":0,"label":T("走行距離","travel distance"),"unit":"m","decimals":1}]}
    image=np.repeat(r["image"][:,None,:,None],3,axis=3).astype(np.uint8)
    common=dict(t=t,bodies=bodies,xyz=xyz,quat=q,axis=axis,view={"az":-.75,"el":.35,"dist":1.0})
    tabs=[]
    tabs.append(pv.viewer_anim3d_tab("contact",T("なぜ下面が平らに削れるのか","Why the underside wears flat"),"passed",T("パンタグラフのすり板が円形に近いトロリ線の下面だけに繰り返し接触し、弦の形の平面を作る。","The pantograph strip repeatedly touches only the underside of the nearly circular contact wire, making a chord-shaped flat."),checks=_checks(g),lesson=_lesson(T("摩耗が進むと明るい平面の幅はどうなる？","As wear grows, what happens to the bright flat width?"),[T("広くなる","it grows wider"),T("狭くなる","it becomes narrower")],0,T("円を深く削るほど弦は広くなる。","A deeper cut through a circle makes a wider chord."),T("h = R + sqrt(R² − (w/2)²)","h = R + sqrt(R² − (w/2)²)"),T("断面を円、接触を一様とした合成モデル。","Synthetic model with a circular section and uniform contact.")),**common))
    tabs.append(pv.viewer_anim3d_tab("camera",T("ラインカメラ像で帯を追う","Track the band in a line-camera image"),"passed",T("照明を強く反射する摩耗面を、走行距離ごとの横一列として積み上げる。偏位は帯を横へ動かすが、両端の間隔は保つ。","Rows along the journey stack the strongly reflecting wear flat. Stagger moves the band sideways while preserving the edge spacing."),panes=[{"label":T("時間 × 横位置の合成ライン像","synthetic line image: time by lateral position"),"frames":image,"png":True,"wide":True}],series=[{"label":T("画像だけから測った帯幅","width measured from image only"),"values":r["measured_width"],"unit":"mm","color":"#ffd54f"}],checks=_checks(g),lesson=_lesson(T("偏位で帯が横へ動くと幅も変わる？","Does lateral stagger change the band width?"),[T("位置だけが変わる","only position changes"),T("幅も同じだけ変わる","width changes equally")],0,T("各行の明暗分布だけから閾値を作り、左右の端をサブピクセル補間する。真の幅は検出に渡さない。","Each row supplies its own threshold; both edges are interpolated to subpixels. The detector never receives the true width."),T("w = (x_right − x_left) × 0.08 mm/pixel","w = (x_right − x_left) × 0.08 mm/pixel"),T("0.08 mm/pixel と照明分布は説明用の仮定。","The 0.08 mm/pixel scale and illumination profile are explanatory assumptions.")),**common))
    tabs.append(pv.viewer_anim3d_tab("map",T("摩耗を走行距離の地図にする","Map wear along the route"),"passed",T("画像で測った幅を円の弦の式へ入れ、区間ごとの残存高さに直す。赤い線は合成に使った幾何で、検出器には渡していない。","The measured image width enters the circle-chord equation to give remaining height by section. The red line is synthetic geometry withheld from the detector."),series=[{"label":T("推定した残存高さ","estimated remaining height"),"values":r["measured_height"],"unit":"mm","color":"#4dd0e1"},{"label":T("合成した幾何","synthetic geometry"),"values":r["true_height"],"unit":"mm","color":"#ef5350"}],checks=_checks(g),lesson=_lesson(T("帯幅から直接わかるのは何？","What follows directly from band width?"),[T("円弧を仮定した残存高さ","remaining height under a circular-section assumption"),T("材質の強度","material strength")],0,T("同じ幅でも断面が円でなければ換算結果は変わる。","The conversion changes if the section is not circular."),T("h = R + sqrt(R² − (w/2)²)","h = R + sqrt(R² − (w/2)²)"),T("交換判定そのものではなく、測定の地図を示す。","This is a measurement map, not a replacement decision.")),**common))
    tabs.append(pv.viewer_anim3d_tab("limit",T("雨・汚れ・振動は別の誤差","Rain, dirt and vibration are separate errors"),"limit",T("反射が落ちると端が欠け、斜めから見ると見かけの幅が縮む。欠測をゼロ幅として扱ってはいけない。","Lost reflection can erase an edge, and oblique viewing shortens apparent width. A missing row must not become zero width."),checks=_checks(g,True),lesson=_lesson(T("帯が見えない行を 0 mm と記録してよい？","May an invisible band be recorded as 0 mm?"),[T("よい","yes"),T("欠測にして再評価する","mark it missing and reassess")],1,T("0 mm は摩耗なしという誤った観測になる。","Zero would falsely mean no wear."),T("欠測 ≠ 0 mm","missing ≠ 0 mm"),T("雨、汚れ、振動、斜視と保守判定はこの合成モデルの外。","Rain, dirt, vibration, oblique views and maintenance decisions are outside this synthetic model.")),**common))
    return pv.viewer_spec("catenary_wear",T("走りながら架線のすり減りを測る","Measure contact-wire wear while moving"),T("明るい帯の幅からトロリ線の残存高さを求める","Recover contact-wire height from a bright-band width"),T("①問い → ②予想 → ③再生 → ④式 → ⑤限界。バッジは画像から計算した値を示す。","Follow ① question → ② prediction → ③ play → ④ formula → ⑤ limit. Badges report values computed from images."),tabs,credit=T("架線、車両、カメラ像はすべて合成。固有の事業者、車両、製品、規格を表さない。","Wire, vehicle and camera image are entirely synthetic and represent no specific operator, vehicle, product or standard."))


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__.splitlines()[0]); ap.add_argument("--check",action="store_true"); ap.add_argument("--out",default=str(OUT_HTML)); a=ap.parse_args(argv)
    result=compute(); g=gates(result)
    for k,v in g.items(): print("%-30s %s"%(k,v))
    spec=build_spec(result,g); html=pv._build_html(spec,list(LANGS))
    if a.check: print("ok: %d bytes (not written)"%len(html.encode("utf-8"))); return 0
    path=pv.write_viewer(spec,a.out,list(LANGS)); print("wrote %s (%d bytes)"%(path,Path(path).stat().st_size)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
