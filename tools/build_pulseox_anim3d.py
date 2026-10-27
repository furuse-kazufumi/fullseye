# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""パルスオキシメータの二波長吸収を学ぶ動く 3-D ページ。"""
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

OUT_HTML = ROOT / "docs" / "view2026" / "anim3d" / "pulseox_anim3d.html"
LANGS = ("ja", "en")
# 説明用の無次元化した代表値。絶対値でなく二波長間の比を使う。
EPS = {"red_o": 0.10, "red_d": 0.80, "ir_o": 0.60, "ir_d": 0.20}
BASE_PATH_MM, PULSE_MM, NOISE = 1.00, 0.035, 0.00008


def T(ja, en):
    return pv.viewer_text(ja, en)


def _e(x):
    return "< 1e-12" if abs(float(x)) < 1e-12 else "%.3g" % float(x)


def absorption(s, wave):
    return EPS[wave + "_o"] * s + EPS[wave + "_d"] * (1.0 - s)


def closed_r(s):
    return absorption(s, "red") / absorption(s, "ir")


def inverse_closed(r):
    ro, rd, io, id_ = EPS["red_o"], EPS["red_d"], EPS["ir_o"], EPS["ir_d"]
    return (rd - r * id_) / (r * (io - id_) - (ro - rd))


def inverse_numeric(r):
    lo, hi = 0.0, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if closed_r(mid) > r:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _signal(s, wave, phase, noisy=True):
    path = BASE_PATH_MM + PULSE_MM * (0.5 + 0.5 * np.sin(phase))
    sigma = absorption(s, wave)
    y = np.asarray(fs.ledger.beer_lambert_transmittance(path, sigma), float)
    if noisy:
        rng = np.random.default_rng(610 if wave == "red" else 940)
        y = y + rng.normal(0.0, NOISE, len(y))
    return y


def acdc(y):
    # DC は平均、AC は既知の心拍周波数への最小二乗射影。信号生成式とは別の処理経路。
    n = len(y); phase = 2 * np.pi * np.arange(n) / n
    X = np.column_stack([np.ones(n), np.sin(phase), np.cos(phase)])
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    return float(np.hypot(b[1], b[2]) / b[0])


def compute():
    sat = np.linspace(1.0, 0.70, 49)
    phase = 2 * np.pi * np.arange(240) / 240
    # 小振幅 Beer--Lambert の閉形式 R。抽出値は op の時系列と雑音から求める。
    theory = np.array([closed_r(s) for s in sat])
    extracted, estimate = [], []
    for s in sat:
        rr = acdc(_signal(s, "red", phase)); ri = acdc(_signal(s, "ir", phase))
        r = rr / ri; extracted.append(r); estimate.append(inverse_closed(r))
    pulse = 0.5 + 0.5 * np.sin(np.linspace(0, 2*np.pi, 49))
    red_t = np.array([float(fs.ledger.beer_lambert_transmittance(BASE_PATH_MM+PULSE_MM*x, absorption(.92,"red"))) for x in pulse])
    ir_t = np.array([float(fs.ledger.beer_lambert_transmittance(BASE_PATH_MM+PULSE_MM*x, absorption(.92,"ir"))) for x in pulse])
    return dict(sat=sat, theory=theory, extracted=np.array(extracted), estimate=np.array(estimate),
                pulse=pulse, red_t=red_t, ir_t=ir_t)


def gates(r):
    rerr = float(np.max(np.abs(r["extracted"] - r["theory"])))
    serr = float(np.max(np.abs(r["estimate"] - r["sat"])))
    inv = float(max(abs(inverse_closed(x)-inverse_numeric(x)) for x in r["theory"]))
    true_s, co_fraction = .90, .10
    # 二波長模型が COHb を酸化 Hb と取り違える限界を、計算値で示す。
    co_read = true_s + (1-true_s)*co_fraction
    return {"r_max_error":rerr, "spo2_max_error":serr, "inverse_error":inv,
            "co_true":true_s, "co_read":co_read, "co_bias":co_read-true_s}


def _box(sx, sy, sz):
    p=np.array([[x,y,z] for x in (-sx/2,sx/2) for y in (-sy/2,sy/2) for z in (-sz/2,sz/2)],float)
    f=np.array([[0,1,3],[0,3,2],[4,6,7],[4,7,5],[0,4,5],[0,5,1],[2,3,7],[2,7,6],[0,2,6],[0,6,4],[1,5,7],[1,7,3]])
    return p,f


def _poses(n,b):
    x=np.zeros((n,b,3)); q=np.zeros((n,b,4)); q[...,0]=1; return x,q


def _band(a, b):
    out=np.zeros((len(a),92,640,3),np.uint8); out[:]=(12,18,27)
    for i,(x,y) in enumerate(zip(a,b)):
        out[i,18:42,:int(620*np.clip(x,0,1))]=(235,65,54)
        out[i,54:78,:int(620*np.clip(y,0,1))]=(110,170,245)
    return out


def _checks(g, limit=False):
    rows=[
      {"what":T("雑音入り時系列から抽出した R と閉形式","R extracted from noisy time series vs closed form"),"criterion":"< 0.03","result":"%.4f"%g["r_max_error"],"ok":g["r_max_error"]<.03},
      {"what":T("較正曲線から読んだ SpO₂ と合成真値","SpO2 read from calibration vs synthetic truth"),"criterion":"≤ 1 %","result":"%.3f %%"%(100*g["spo2_max_error"]),"ok":g["spo2_max_error"]<=.01},
      {"what":T("SpO₂ の閉形式逆関数と数値解","closed-form inverse vs numerical SpO2 solution"),"criterion":"< 1e-9","result":_e(g["inverse_error"]),"ok":g["inverse_error"]<1e-9}]
    if limit:
        rows.append({"what":T("COHb 10 % があっても真の SpO₂ を読む","true SpO2 despite 10% COHb"),"criterion":T("偏り 1 % 未満","bias below 1%"),"result":T("真値 %.1f %% → 読み %.1f %%"%(100*g["co_true"],100*g["co_read"]),"true %.1f%% → read %.1f%%"%(100*g["co_true"],100*g["co_read"])),"ok":g["co_bias"]<.01})
    return rows


def _lesson(q, choices, answer, explain, formula, limit):
    return {"question":q,"choices":choices,"answer":answer,"explain":explain,"formula":formula,"limit":limit}


def build_spec(r,g):
    tissue,tf=_box(8,5,2.8); artery,af=_box(8,1.2,.7); beam,bf=_box(10,.15,.15)
    bodies=[{"name":"tissue","pos":tissue,"faces":tf,"rgb":[224,150,135],"alpha":.35},{"name":"artery","pos":artery,"faces":af,"rgb":[180,35,45],"alpha":.7},{"name":"red light","pos":beam,"faces":bf,"rgb":[255,45,35]},{"name":"near infrared","pos":beam,"faces":bf,"rgb":[130,170,255]}]
    tabs=[]; n=49
    xyz,q=_poses(n,4); xyz[:,2,1]=-.45; xyz[:,3,1]=.45
    tabs.append(pv.viewer_anim3d_tab("finger",T("指を通る二つの光","Two lights through a finger"),"passed",T("皮膚と組織を挟んで、660 nm の赤と 940 nm の近赤外が動脈を通る。色ではなく透過量の比が酸素化で変わる。","Red 660 nm and near-infrared 940 nm cross the artery through skin and tissue. Oxygenation changes their transmission ratio, not merely their colour."),np.arange(n)/24,bodies,xyz,q,series=[{"label":T("赤の透過","red transmission"),"values":r["red_t"],"unit":"","color":"#ef5350"},{"label":T("近赤外の透過","near-infrared transmission"),"values":r["ir_t"],"unit":"","color":"#64b5f6"}],panes=[{"label":T("上: 赤、下: 近赤外の透過光","top: red; bottom: near-infrared transmission"),"frames":_band(r["red_t"],r["ir_t"]),"png":True,"wide":True}],numbers=[pv.viewer_number(T("波長","wavelengths"),"660 / 940 nm")],checks=_checks(g),axis={"values":r["pulse"],"segments":[{"k":0,"label":T("動脈の拍動","arterial pulse"),"unit":"","decimals":2}]},lesson=_lesson(T("酸素化が変わると二つの光は同じ割合で弱くなる?","Does oxygenation attenuate both lights by the same fraction?"),[T("同じ","the same"),T("異なる","differently")],1,T("酸化・還元ヘモグロビンの吸光係数は二波長で異なる。","Oxy- and deoxyhaemoglobin have different absorption at the two wavelengths."),T("A = Σ εᵢ cᵢ l","A = Σ εᵢ cᵢ l"),T("散乱を無視した Beer–Lambert 模型。係数と厚さは説明用の仮定。","Beer-Lambert model without scattering; coefficients and thickness are explanatory assumptions."))))
    xyz,q=_poses(n,4); xyz[:,1,2]=.35*r["pulse"]
    tabs.append(pv.viewer_anim3d_tab("pulse",T("拍動から AC/DC を取り出す","Extract AC/DC from the pulse"),"passed",T("拍動で変わる動脈だけが AC を作り、組織などの定常吸収は DC に残る。二波長それぞれの AC/DC を比べる。","Only the pulsating artery creates AC; steady tissue absorption remains in DC. The two AC/DC values are compared."),np.arange(n)/24,bodies,xyz,q,series=[{"label":T("比 R","ratio R"),"values":np.interp(np.arange(n),[0,n-1],[r["extracted"][0],r["extracted"][-1]]),"unit":"","color":"#ffd54f"}],panes=[{"label":T("AC/DC の赤・近赤外比","red-to-infrared AC/DC ratio"),"frames":_band(r["red_t"],r["ir_t"]),"png":True,"wide":True}],numbers=[pv.viewer_number(T("比 R","ratio R"),"%.3f"%r["extracted"][13])],checks=_checks(g),axis={"values":r["pulse"],"segments":[{"k":0,"label":T("拍動","pulse"),"unit":"","decimals":2}]},lesson=_lesson(T("組織の厚さが増えて DC が下がったら、拍動の読みはどうする?","If thicker tissue lowers DC, how should the pulse be read?"),[T("AC だけ使う","use AC alone"),T("AC/DC にする","use AC/DC")],1,T("各波長で AC を DC で割り、定常減衰の影響を減らす。","Divide AC by DC at each wavelength to reduce steady attenuation."),T("R=(ACred/DCred)/(ACir/DCir)","R=(ACred/DCred)/(ACir/DCir)"),T("実機のフィルタ、量子化、灌流の違いは含めない。","Instrument filtering, quantisation and perfusion variation are omitted."))))
    xyz,q=_poses(n,2)
    curve_bodies=bodies[:2]
    tabs.append(pv.viewer_anim3d_tab("calibration",T("R から酸素飽和度を読む","Read oxygen saturation from R"),"passed",T("SpO₂ を 100 % から 70 % へ動かすと R が増える。黄色の抽出値は雑音入り時系列、線は Beer–Lambert の閉形式。","As SpO2 moves from 100% to 70%, R rises. Yellow values come from noisy time series; the line is the Beer-Lambert closed form."),np.arange(n)/24,curve_bodies,xyz,q,series=[{"label":T("閉形式 R","closed-form R"),"values":r["theory"],"unit":"","color":"#4fc3f7"},{"label":T("抽出 R","extracted R"),"values":r["extracted"],"unit":"","color":"#ffd54f"}],numbers=[pv.viewer_number(T("最大 SpO₂ 誤差","maximum SpO2 error"),"%.3f %%"%(100*g["spo2_max_error"]))],checks=_checks(g),axis={"values":100*r["sat"],"segments":[{"k":0,"label":T("酸素飽和度","oxygen saturation"),"unit":"%","decimals":1}]},lesson=_lesson(T("SpO₂ が下がると、この模型の R は?","As SpO2 falls, what happens to R in this model?"),[T("下がる","falls"),T("上がる","rises")],1,T("赤の還元 Hb 吸収が相対的に強いため R が上がる。","R rises because deoxyhaemoglobin absorbs red light relatively strongly."),T("R=(εr,o S+εr,d(1-S))/(εi,o S+εi,d(1-S))","R=(εr,o S+εr,d(1-S))/(εi,o S+εi,d(1-S))"),T("実機は経験的較正を使う。この曲線は散乱なしの教育模型。","Real instruments use empirical calibration; this is a scattering-free teaching model."))))
    xyz,q=_poses(n,2)
    tabs.append(pv.viewer_anim3d_tab("limits",T("二波長では見分けられないもの","What two wavelengths cannot distinguish"),"limit",T("COHb 10 % を酸化 Hb と取り違える模型では、真の 90.0 % を 91.0 % と読む。体動、散乱、マニキュアも二波長の比を変える。","In a model that confuses 10% COHb with oxyhaemoglobin, a true 90.0% reads 91.0%. Motion, scattering and nail coating also alter the two-wavelength ratio."),np.arange(n)/24,curve_bodies,xyz,q,series=[{"label":T("真値","truth"),"values":np.full(n,100*g["co_true"]),"unit":"%","color":"#4fc3f7"},{"label":T("二波長の読み","two-wavelength reading"),"values":np.full(n,100*g["co_read"]),"unit":"%","color":"#ff8a65"}],numbers=[pv.viewer_number(T("COHb による偏り","bias from COHb"),"+%.1f %%"%(100*g["co_bias"]))],checks=_checks(g,True),axis={"values":np.linspace(0,10,n),"segments":[{"k":0,"label":T("一酸化炭素ヘモグロビン","carboxyhaemoglobin"),"unit":"%","decimals":1}]},lesson=_lesson(T("二波長だけで COHb と酸化 Hb を区別できる?","Can two wavelengths distinguish COHb from oxyhaemoglobin?"),[T("できる","yes"),T("できない","no")],1,T("未知成分が増えると二つの測定だけでは方程式が足りない。","With another unknown species, two measurements no longer provide enough equations."),T("未知濃度 3 種 > 波長 2 本","3 unknown concentrations > 2 wavelengths"),T("診断用ではない。散乱、体動、低灌流、マニキュア、COHb を扱わない模型。","Not for diagnosis. The model omits scattering, motion, low perfusion, nail coating and COHb."))))
    return pv.viewer_spec("pulseox",T("赤と近赤外から血液の酸素割合を読む","Reading blood oxygen fraction with red and near-infrared light"),T("拍動成分の二波長比を、指の断面と較正曲線で追う","Follow the two-wavelength pulsatile ratio through a finger cross-section and calibration curve"),T("①問い → ②予想 → ③再生 → ④式 → ⑤限界。値はすべて合成。","Follow question, prediction, playback, formula and limit. All values are synthetic."),tabs,credit=T("すべて合成。吸光係数、指の厚さ、拍動振幅、雑音は文献で一般的な関係を説明するための仮定であり、患者データや製品の較正値ではない。診断には使わない。","Entirely synthetic. Absorption coefficients, finger thickness, pulse amplitude and noise are explanatory assumptions for commonly reported relations, not patient data or product calibration. Not for diagnosis."))


def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument("--check",action="store_true"); ap.add_argument("--out",default=str(OUT_HTML)); a=ap.parse_args(argv)
    r=compute(); g=gates(r)
    for k,v in g.items(): print("%-24s %s"%(k,v))
    spec=build_spec(r,g)
    if a.check:
        print("ok: %d bytes (not written)"%len(pv._build_html(spec,list(LANGS)).encode())); return 0
    path=pv.write_viewer(spec,a.out,list(LANGS)); print("wrote %s (%d bytes)"%(path,Path(path).stat().st_size)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
