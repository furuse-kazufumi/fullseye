# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""船速によらないケルビン航跡角を、高さ場から測る動く 3-D 学習ページ。"""
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

OUT_HTML = ROOT / "docs" / "view2026" / "anim3d" / "kelvin_wake_anim3d.html"
LANGS = ("ja", "en")
G = 9.80665
SPEEDS = (4.0, 7.0, 12.0)
TRUE_ANGLE_DEG = math.degrees(math.asin(1.0 / 3.0))


def T(ja, en):
    return pv.viewer_text(ja, en)


def _grid(speed):
    # Every speed is sampled on the same physical ruler.  This deliberately
    # prevents speed cases from becoming rescaled copies of one another.
    return np.linspace(-250.0, 10.0, 281), np.linspace(-90.0, 90.0, 201)


def synthesize_height(speed, component="both"):
    """Deep-water ray packets summed on a regular height grid.

    Each wave-number direction obeys omega^2=gk and omega=U*kx.  Its
    group-ray angle is computed separately; crowding of rays creates the
    cusp.  No closed-form Kelvin angle is supplied to the raster synthesis.
    """
    x, y = _grid(speed)
    X, Y = np.meshgrid(x, y)
    z = np.zeros_like(X)
    theta = np.linspace(-1.25, 1.25, 241)
    if component == "transverse":
        theta = theta[np.abs(theta) < 0.48]
    elif component == "divergent":
        theta = theta[np.abs(theta) >= 0.48]
    for a in theta:
        beta = math.atan2(math.sin(a) * math.cos(a), 1.0 + math.sin(a) ** 2)
        dx, dy = -math.cos(beta), math.sin(beta)
        along = X * dx + Y * dy
        cross = -X * dy + Y * dx
        k = G / (speed * speed * math.cos(a) ** 2)
        # 1.8 m is a fixed physical source-width proxy; 320 m is a fixed
        # display attenuation length.  Neither changes with speed.
        packet = np.cos(k * along) * np.exp(-(cross / 1.8) ** 2)
        z += packet * (along > 0.0) * np.exp(-along / 320.0)
    z /= max(1, len(theta))
    return x, y, z


def measure_cusp_angle(x, y, z):
    """Locate the steepest angular fall of mean |height| (image edge)."""
    angles = np.linspace(14.0, 24.0, 201)
    distances = np.linspace(45.0, 220.0, 240)
    scores = []
    for deg in angles:
        xx = -distances
        yy = distances * math.tan(math.radians(deg))
        jf = (xx - x[0]) / (x[1] - x[0])
        iy = np.clip(np.rint((yy - y[0]) / (y[1] - y[0])).astype(int), 0, len(y)-1)
        jx = np.clip(np.rint(jf).astype(int), 0, len(x)-1)
        scores.append(float(np.mean(np.abs(z[iy, jx]))))
    scores = np.asarray(scores)
    measured = float(angles[np.argmin(np.gradient(scores, angles))])
    pixel_angle = math.degrees(math.atan2(y[1] - y[0], distances.mean()))
    # The edge derivative spans about six transverse pixels; convert that
    # image support plus the angular scan step into the acceptance angle.
    criterion = 6.0 * pixel_angle + (angles[1] - angles[0])
    return measured, criterion, angles, scores


def measure_transverse_wavelength(x, y, z):
    """Measure the dominant centreline period without using U or g."""
    row = z[np.argmin(np.abs(y))]
    keep = x < -20.0
    xx = x[keep]
    signal = row[keep] - np.mean(row[keep])
    # Zero padding interpolates the observed finite-window spectrum; the
    # signal itself still comes only from the fixed physical raster.
    spectrum = np.abs(np.fft.rfft(signal * np.hanning(len(signal)), 8192))
    freq = np.fft.rfftfreq(8192, xx[1] - xx[0])
    peak = 1 + int(np.argmax(spectrum[1:]))
    return float(1.0 / freq[peak]), float(xx[-1] - xx[0]) / len(xx)


def compute():
    rows = []
    for speed in SPEEDS:
        x, y, z = synthesize_height(speed)
        angle, angle_limit, angular_axis, angular_score = measure_cusp_angle(x, y, z)
        wavelength, pitch = measure_transverse_wavelength(x, y, z)
        rows.append(dict(speed=speed, x=x, y=y, z=z, angle=angle,
                         angle_limit=angle_limit, angular_axis=angular_axis,
                         angular_score=angular_score, wavelength=wavelength,
                         wavelength_truth=2.0 * math.pi * speed * speed / G,
                         wavelength_limit=2.5 * pitch))
    return rows


def gates(rows):
    angle_errors = np.array([abs(r["angle"] - TRUE_ANGLE_DEG) for r in rows])
    angle_spread = float(np.ptp([r["angle"] for r in rows]))
    angle_limit = max(r["angle_limit"] for r in rows)
    wave_errors = np.array([abs(r["wavelength"] - r["wavelength_truth"]) for r in rows])
    wave_limits = np.array([r["wavelength_limit"] for r in rows])
    wave_ratio = rows[-1]["wavelength"] / rows[0]["wavelength"]
    ratio_limit = max(rows[0]["wavelength_limit"] / rows[0]["wavelength"],
                      rows[-1]["wavelength_limit"] / rows[-1]["wavelength"]) * 9.0
    return dict(max_angle_error_deg=float(angle_errors.max()), angle_spread_deg=angle_spread,
                angle_limit_deg=float(angle_limit), max_wavelength_error_m=float(wave_errors.max()),
                wavelength_limit_m=float(wave_limits.max()), wave_errors=wave_errors,
                wave_limits=wave_limits, wavelength_ratio=wave_ratio,
                wavelength_ratio_error=abs(wave_ratio - 9.0), wavelength_ratio_limit=ratio_limit)


def _surface(row, stride=8, height=240.0):
    x, y, z = row["x"][::stride], row["y"][::stride], row["z"][::stride, ::stride]
    X, Y = np.meshgrid(x, y)
    p = np.column_stack([X.ravel(), Y.ravel(), (height*z).ravel()])
    n, m = X.shape
    f = []
    for i in range(n-1):
        for j in range(m-1):
            a = i*m+j
            f.extend(((a, a+1, a+m+1), (a, a+m+1, a+m)))
    return p, np.asarray(f, int)


def _boat():
    p = np.array([[2,0,1],[-2,-1,0],[-2,1,0],[-1,0,1.2],[-2,0,-.5]], float)
    f = np.array([[0,1,3],[0,3,2],[0,4,1],[0,2,4],[1,4,2],[1,2,3]])
    return p, f


def _poses(n, bodies):
    xyz = np.zeros((n, bodies, 3)); q = np.zeros((n, bodies, 4)); q[..., 0] = 1
    return xyz, q


def _raster(rows):
    frames = []
    for r in rows:
        a = np.abs(r["z"]); a /= max(float(a.max()), 1e-12)
        img = np.zeros(a.shape + (3,), np.uint8)
        img[..., 0] = np.clip(12 + 120*a, 0, 255)
        img[..., 1] = np.clip(36 + 190*a, 0, 255)
        img[..., 2] = np.clip(58 + 197*a, 0, 255)
        frames.append(img)
    return np.asarray(frames)


def _checks(g, limit=False):
    rows = [
        {"what":T("高さ画像から測ったカスプ角", "cusp angle measured from height images"),
         "criterion":"error < %.2f deg" % g["angle_limit_deg"],
         "result":"%.2f deg" % g["max_angle_error_deg"],
         "ok":g["max_angle_error_deg"] < g["angle_limit_deg"]},
        {"what":T("船速を変えたときの角度差", "angle spread across speeds"),
         "criterion":"< %.2f deg" % g["angle_limit_deg"],
         "result":"%.2f deg" % g["angle_spread_deg"],
         "ok":g["angle_spread_deg"] < g["angle_limit_deg"]},
        {"what":T("中心線スペクトルの横波波長", "transverse wavelength from centreline spectrum"),
         "criterion":"error < %.2f m" % g["wavelength_limit_m"],
         "result":"%.2f m" % g["max_wavelength_error_m"],
         "ok":g["max_wavelength_error_m"] < g["wavelength_limit_m"]},
        {"what":T("12 m/s と 4 m/s の横波波長比", "transverse-wavelength ratio: 12 m/s to 4 m/s"),
         "criterion":"error < %.2f" % g["wavelength_ratio_limit"],
         "result":"%.2f (error %.2f)" % (g["wavelength_ratio"], g["wavelength_ratio_error"]),
         "ok":g["wavelength_ratio_error"] < g["wavelength_ratio_limit"]},
    ]
    if limit:
        rows.append({"what":T("浅水・船体幅・粘性でも同じ角度", "same angle with shallow water, hull width and viscosity"),
                     "criterion":T("これらをモデルに含む", "model includes these effects"),
                     "result":T("未計算", "not computed"), "ok":False})
    return rows


def _lesson(q, choices, answer, explain, formula, limit):
    return {"question":q, "choices":choices, "answer":answer,
            "explain":explain, "formula":formula, "limit":limit}


def build_spec(rows=None):
    rows = compute() if rows is None else rows
    g = gates(rows)
    boat, boat_f = _boat()
    mid = rows[1]
    surf, surf_f = _surface(mid)
    bodies = [{"name":"water", "pos":surf, "faces":surf_f, "rgb":[35,125,170], "alpha":.82},
              {"name":"boat", "pos":boat, "faces":boat_f, "rgb":[245,180,55]}]
    n = 49; xyz, q = _poses(n, 2); xyz[:,1,0] = np.linspace(-18,3,n); xyz[:,1,2] = 2
    common = dict(t=np.arange(n)/24, bodies=bodies, xyz=xyz, quat=q,
                  trails=[{"xyz":xyz[:,1,:],"color":"#ffd54f","tail":18}],
                  view={"az":-.82,"el":.48,"dist":1.05,"target":[-25,0,0]})
    tabs=[]
    tabs.append(pv.viewer_anim3d_tab("shape",T("V 字の航跡","V-shaped wake"),"passed",
        T("点状の圧力源が作る深水波を重ねると、波の山が二本のカスプ線へ集まる。高さ画像の角度方向を走査し、信号が最も急に落ちる境界を測った。","Superposing deep-water waves from a point pressure source crowds crests onto two cusp lines. The measurement scans height-image angles and finds the steepest signal edge."),
        panes=[{"label":T("合成した高さ画像","synthetic height image"),"frames":_raster([mid]*n),"png":True,"wide":True}],
        numbers=[pv.viewer_number(T("画像から測った半角","measured half-angle"),"%.2f deg"%mid["angle"]),pv.viewer_number(T("閉形式","closed form"),"arcsin(1/3) = %.2f deg"%TRUE_ANGLE_DEG)],checks=_checks(g),axis={"values":np.linspace(0,1,n),"segments":[{"k":0,"label":T("船の進行","boat travel"),"unit":"","decimals":2}]},
        lesson=_lesson(T("速い船ほど V 字は細くなる?","Does a faster boat make a narrower V?"),[T("細くなる","yes, narrower"),T("深水では同じ","unchanged in deep water")],1,T("速さは波長を変えるが、点源の深水カスプ角は変えない。","Speed changes wavelength, but not the deep-water point-source cusp angle."),T("omega^2 = g k; omega = U kx","omega^2 = g k; omega = U kx"),T("点源・深水・線形・非粘性の模型。","Point-source, deep-water, linear and inviscid model.")),**common))

    rframes = _raster(rows)
    xyz2,q2=_poses(3,2); xyz2[:,1,2]=2
    tabs.append(pv.viewer_anim3d_tab("speed",T("速さを 3 倍にする","Triple the speed"),"passed",
        T("4、7、12 m/s の高さ場を同じ実寸格子で比較する。V の角度は格子基準内で一致し、中心線の波長は U^2 に比例して伸びる。","Compare height fields at 4, 7 and 12 m/s on the same physical grid. Their V angles agree within the grid-derived criterion while centreline wavelength grows with U^2."),
        np.arange(3)/2,bodies,xyz2,q2,panes=[{"label":T("速度ごとの高さ画像","height image at each speed"),"frames":rframes,"png":True,"wide":True}],
        series=[{"label":T("画像から測った角度","image-measured angle"),"values":[r["angle"] for r in rows],"unit":"deg","color":"#ffca28","threshold":TRUE_ANGLE_DEG}],
        numbers=[pv.viewer_number(T("角度差","angle spread"),"%.2f deg"%g["angle_spread_deg"]),pv.viewer_number(T("波長 4 → 12 m/s","wavelength, 4 → 12 m/s"),"%.1f → %.1f m"%(rows[0]["wavelength"],rows[-1]["wavelength"]))],checks=_checks(g),axis={"values":list(SPEEDS),"segments":[{"k":0,"label":T("船速 U","boat speed U"),"unit":"m/s","decimals":0}]},view={"az":-.82,"el":.48,"dist":1.05,"target":[-25,0,0]},
        lesson=_lesson(T("船速を 3 倍にすると何が 9 倍になる?","What becomes 9 times larger when speed triples?"),[T("航跡角","wake angle"),T("横波の波長","transverse wavelength")],1,T("分散関係と定常条件から中心線では k=g/U^2。","On the centreline, dispersion and stationarity give k=g/U^2."),T("lambda = 2 pi U^2 / g","lambda = 2 pi U^2 / g"),T("全速度を同じ実寸格子、同じ包絡幅、同じ減衰長で比較する。","All speeds use the same physical grid, envelope width and attenuation length."))))

    xt,yt,zt=synthesize_height(7,"transverse"); xd,yd,zd=synthesize_height(7,"divergent")
    comp_rows=[dict(z=zt),dict(z=zd),dict(z=zt+zd)]
    xyz3,q3=_poses(3,2);xyz3[:,1,2]=2
    tabs.append(pv.viewer_anim3d_tab("components",T("横波と発散波","Transverse and divergent waves"),"passed",
        T("船尾にほぼ直角な横波と、斜めに走る発散波を別々に描き、最後に重ねる。両方の群速度の光線が同じ外縁へ密集して V 字を作る。","Draw near-transverse stern waves and oblique divergent waves separately, then combine them. Group-velocity rays from both families crowd onto the same outer V edge."),
        np.arange(3)/2,bodies,xyz3,q3,panes=[{"label":T("横波 → 発散波 → 重ね合わせ","transverse → divergent → superposed"),"frames":_raster(comp_rows),"png":True,"wide":True}],
        checks=_checks(g),axis={"values":[0,1,2],"segments":[{"k":0,"label":T("成分","component"),"unit":"","decimals":0}]},view={"az":-.82,"el":.48,"dist":1.05,"target":[-25,0,0]},
        lesson=_lesson(T("V 字は一種類の波だけでできる?","Does only one wave family make the V?"),[T("横波だけ","transverse only"),T("横波と発散波の重ね合わせ","both wave families")],1,T("異なる向きの波数成分が、群速度で運ぶ包絡線上に集まる。","Different wave-number directions collect on the envelope carried by group velocity."),T("cg = d omega / d k","cg = d omega / d k"),T("波高は線形重ね合わせで、砕波を含めない。","Wave height is linearly superposed; breaking is omitted."))))

    tabs.append(pv.viewer_anim3d_tab("limit",T("深水模型の限界","Limits of the deep-water model"),"limit",
        T("約 19.47 deg は点源・深水の結果である。浅水では分散関係が変わり、有限の船体幅や高いフルード数は見かけの角度を狭め、粘性は短い波を弱める。","About 19.47 deg is a point-source, deep-water result. Shallow water changes dispersion; finite hull width and high Froude number can narrow the apparent angle, while viscosity damps short waves."),
        np.arange(3)/2,bodies,xyz3,q3,panes=[{"label":T("この模型が計算した深水の高さ画像","deep-water height image computed by this model"),"frames":rframes,"png":True,"wide":True}],checks=_checks(g,True),axis={"values":list(SPEEDS),"segments":[{"k":0,"label":T("船速 U","boat speed U"),"unit":"m/s","decimals":0}]},view={"az":-.82,"el":.48,"dist":1.05,"target":[-25,0,0]},
        lesson=_lesson(T("実船の航跡はいつも 19.47 deg?","Is every real wake 19.47 deg?"),[T("いつも同じ","always"),T("水深・船体・粘性で変わる","it changes with depth, hull and viscosity")],1,T("普遍なのは限定した深水点源模型のカスプ角で、すべての見かけの航跡角ではない。","The universal value belongs to the restricted deep-water point-source cusp, not every apparent wake angle."),T("omega^2 = g k tanh(k h)","omega^2 = g k tanh(k h)"),T("これが限界の回。浅水、船体形状、砕波、粘性は未計算。","This is the limit tab. Shallow water, hull shape, breaking and viscosity are not computed."))))
    return pv.viewer_spec("kelvin_wake",T("船の V 字の航跡","A ship's V-shaped wake"),T("なぜ速さや大きさが違っても開きは約 19.47 deg なのか","Why the opening stays near 19.47 deg across speeds and sizes"),T("問い、予想、再生、式、限界の順に進む。高さ画像から角度と波長を測り、閉形式と比べる。","Follow question, prediction, play, formula and limit. Measure angle and wavelength from height images, then compare with closed forms."),tabs,credit=T("すべて合成。深水を進む点状圧力源の線形・非粘性モデル。特定の船、造船所、運航者を表さない。","Entirely synthetic: a linear inviscid point-pressure source moving on deep water. No specific vessel, yard or operator is represented."))


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check",action="store_true"); ap.add_argument("--out",default=str(OUT_HTML)); a=ap.parse_args(argv)
    rows=compute(); g=gates(rows)
    for k,v in g.items():
        if np.isscalar(v): print("%-30s %s"%(k,v))
    spec=build_spec(rows)
    if a.check:
        print("ok: %d bytes (not written)"%len(pv._build_html(spec,list(LANGS)).encode("utf-8"))); return 0
    path=pv.write_viewer(spec,a.out,list(LANGS)); print("wrote %s (%d bytes)"%(path,Path(path).stat().st_size)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
