# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""橋のたわみを離れたカメラから DIC で測る動く 3-D 学習ページ。"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matching
import pocviewer as pv

OUT_HTML = ROOT / "docs" / "view2026" / "anim3d" / "bridge_dic_anim3d.html"
LANGS = ("ja", "en")
SPAN_M = 24.0
FRAMES = 31
MM_PER_PIXEL = 0.40
MAX_DEFLECTION_MM = 7.6


def T(ja, en):
    return pv.viewer_text(ja, en)


def _e(x):
    return "< 1e-12" if abs(float(x)) < 1e-12 else "%.3g" % float(x)


def beam_deflection(x, load_x):
    """Unit-normalised Euler--Bernoulli deflection of a simply supported beam."""
    x = np.asarray(x, float); a = float(load_x); b = SPAN_M - a
    y = np.empty_like(x)
    left = x <= a
    y[left] = b*x[left]*(SPAN_M**2-b**2-x[left]**2)
    xr = SPAN_M-x[~left]
    y[~left] = a*xr*(SPAN_M**2-a**2-xr**2)
    # The common P/(6 L E I) factor cancels.  At x=a=L/2 the remaining
    # polynomial is L^4/8, so the normalised peak is exactly one.
    centre = SPAN_M**4/8.0
    return y/centre


def _reference_image(seed=20261027):
    rng = np.random.default_rng(seed)
    im = np.zeros((84, 160), float) + 0.12
    dots = rng.random(im.shape) < 0.075
    im += 0.82*gaussian_filter(dots.astype(float), 0.72)
    im += 0.08*gaussian_filter(rng.normal(size=im.shape), 1.1)
    return np.clip(im, 0, 1)


def _capture(reference, displacement_px, rng, noise_sigma, illumination_phase=0.0):
    """Warp projected texture, then sample and perturb it as a camera would."""
    rr, cc = np.indices(reference.shape, dtype=float)
    src_r = rr - displacement_px[None, :]
    image = map_coordinates(reference, [src_r, cc], order=3, mode="reflect")
    illumination = 0.94 + 0.07*np.sin(2*np.pi*cc/reference.shape[1] + 0.31 + illumination_phase)
    illumination *= 1.0 + rng.normal(0, 0.008)
    image = image*illumination + rng.normal(0, noise_sigma, image.shape)
    return np.clip(image, 0, 1)


def _measure_shift(reference_frame, image):
    # The estimator sees only pixels.  A fixed physical 31x31 window is used in every condition.
    r0, c0, half = 42, 80, 15
    template = reference_frame[r0-half:r0+half+1, c0-half:c0+half+1]
    # Keep the horizontal support equal to the template width: DIC searches the
    # vertical displacement of this physical target, not another look-alike patch.
    roi = image[:, c0-half:c0+half+1]
    model = matching.create_ncc_model(template)
    hit = matching.find_ncc_model(model, roi, min_score=-1, subpixel="interpolation")
    measured_row = hit["row_sub"]
    return measured_row-r0, hit["score"]


def compute(noise_sigma=0.012, seed=20261027):
    rng = np.random.default_rng(seed); reference = _reference_image(20261027)
    # Real DIC compares two observations.  Capture an unloaded reference frame
    # with its own sensor noise and illumination fluctuation; the estimator never
    # receives the clean synthetic texture used by the renderer.
    reference_frame = _capture(reference, np.zeros(reference.shape[1]), rng,
                               noise_sigma, illumination_phase=-0.37)
    load_x = np.linspace(1.2, SPAN_M-1.2, FRAMES)
    x_columns = np.linspace(0, SPAN_M, reference.shape[1])
    true_mm=[]; measured_mm=[]; scores=[]; images=[]; curves=[]
    for frame_index, a in enumerate(load_x):
        curve = MAX_DEFLECTION_MM*beam_deflection(x_columns, a)
        phase = 0.19*np.sin(2*np.pi*(frame_index+1)/(FRAMES+3))
        image = _capture(reference, curve/MM_PER_PIXEL, rng, noise_sigma, illumination_phase=phase)
        shift, score = _measure_shift(reference_frame, image)
        true_mm.append(float(MAX_DEFLECTION_MM*beam_deflection([SPAN_M/2], a)[0]))
        measured_mm.append(float(shift*MM_PER_PIXEL)); scores.append(float(score))
        images.append(np.rint(image*255).astype(np.uint8)); curves.append(curve)
    return dict(load_x=load_x, x=x_columns, true_mm=np.array(true_mm), measured_mm=np.array(measured_mm),
                scores=np.array(scores), images=np.array(images), curves=np.array(curves),
                reference=reference, reference_frame=reference_frame)


def noise_study():
    sigmas=np.array([.004,.007,.012,.020,.032]); spread=[]; predicted=[]
    clean=_capture(_reference_image(20261027),np.zeros(160),np.random.default_rng(77),0.0,0.0)
    patch=clean[27:58,65:96]
    gradient_energy=float(np.sum(np.gradient(patch,axis=0)**2))
    for j,s in enumerate(sigmas):
        vals=[]
        for k in range(12):
            r=compute(float(s), 1000+100*j+k); i=int(np.argmax(r["true_mm"])); vals.append(r["measured_mm"][i]-r["true_mm"][i])
        spread.append(float(np.std(vals, ddof=1)))
        # Both reference and deformed frames contain independent Gaussian noise.
        # The translation Cramer--Rao approximation is sqrt(2)*sigma/sqrt(sum Iy^2).
        predicted.append(MM_PER_PIXEL*math.sqrt(2.0)*float(s)/math.sqrt(gradient_energy))
    spread=np.array(spread); slope=float(np.polyfit(np.log(sigmas),np.log(spread),1)[0])
    predicted=np.array(predicted); theory_slope=float(np.polyfit(np.log(sigmas),np.log(predicted),1)[0])
    return sigmas,spread,slope,predicted,theory_slope


def gates(r):
    err=r["measured_mm"]-r["true_mm"]
    im=int(np.argmax(r["measured_mm"])); it=int(np.argmax(r["true_mm"])); sig,spread,slope,pred,theory_slope=noise_study()
    zero=compute(0.0,9090); zero_err=zero["measured_mm"]-zero["true_mm"]
    systematic_rms=float(np.sqrt(np.mean(zero_err**2)))
    nominal_spread=float(spread[int(np.argmin(np.abs(sig-.012)))])
    # A disclosed 3-sigma measurement budget: deterministic interpolation bias
    # measured at zero noise plus the observed two-frame random spread.
    limit=systematic_rms+3.0*nominal_spread
    return {"rmse_mm":float(np.sqrt(np.mean(err**2))),"limit_mm":float(limit),
            "peak_frame_error":abs(im-it),"peak_position_error_m":abs(float(r["load_x"][im]-SPAN_M/2)),
            "systematic_rms_mm":systematic_rms,"nominal_spread_mm":nominal_spread,
            "noise_slope":slope,"theory_slope":theory_slope,"noise_sigmas":sig,
            "noise_spread":spread,"noise_predicted":pred}


def _box(sx,sy,sz):
    p=np.array([[x,y,z] for x in (-sx/2,sx/2) for y in (-sy/2,sy/2) for z in (-sz/2,sz/2)],float)
    f=np.array([[0,1,3],[0,3,2],[4,6,7],[4,7,5],[0,4,5],[0,5,1],[2,3,7],[2,7,6],[0,2,6],[0,6,4],[1,5,7],[1,7,3]])
    return p,f


def _checks(g, limit=False):
    rows=[
      {"what":T("DIC と閉形式の中央たわみ RMS","centre deflection: DIC versus closed form"),"criterion":"< %.3f mm"%g["limit_mm"],"result":"%.4f mm"%g["rmse_mm"],"ok":g["rmse_mm"]<g["limit_mm"]},
      {"what":T("測定曲線から求めた最大時刻","peak time found from measured curve"),"criterion":T("中央フレーム ±1","centre frame ±1"),"result":T("差 %d フレーム"%g["peak_frame_error"],"difference %d frame(s)"%g["peak_frame_error"]),"ok":g["peak_frame_error"]<=1},
      {"what":T("雑音と測定ばらつきの傾き: 測定 / Cramér–Rao 近似","noise-spread slope: measured / Cramér–Rao approximation"),"criterion":T("傾きの差 < 0.3","slope difference < 0.3"),"result":"%.3f / %.3f"%(g["noise_slope"],g["theory_slope"]),"ok":abs(g["noise_slope"]-g["theory_slope"])<.3}]
    if limit:
        rows.append({"what":T("陽炎・カメラ揺れ・大きな照明変化でも同じ精度","same accuracy with shimmer, camera shake and large lighting change"),"criterion":T("現場の外乱を含む","include field disturbances"),"result":T("未計算: 不動点と現場試験が必要","not computed: fixed targets and field tests required"),"ok":False})
    return rows


def _lesson(q, choices, answer, explain, formula, limit):
    return {"question":q,"choices":choices,"answer":answer,"explain":explain,"formula":formula,"limit":limit}


def build_spec(r,g):
    n=FRAMES; deck,df=_box(6.0,.55,.18); truck,tf=_box(.55,.85,.38); camera,cf=_box(.38,.5,.32)
    xyz=np.zeros((n,3,3)); quat=np.zeros((n,3,4)); quat[...,0]=1
    xyz[:,0,2]=-.18; xyz[:,1,0]=(r["load_x"]-SPAN_M/2)/4; xyz[:,1,2]=.28; xyz[:,2]=[0,-3.2,1.3]
    xyz[:,0,2]-=np.max(r["curves"],axis=1)/350
    objs=[{"name":"bridge","pos":deck,"faces":df,"rgb":[95,125,145]},{"name":"moving load","pos":truck,"faces":tf,"rgb":[245,170,55]},{"name":"camera","pos":camera,"faces":cf,"rgb":[90,210,190]}]
    time=np.arange(n)/12; axis={"values":r["load_x"],"segments":[{"k":0,"label":T("荷重位置","load position"),"unit":"m","decimals":1}]}
    series=[{"label":T("DIC 測定","DIC measurement"),"values":r["measured_mm"],"unit":"mm","color":"#4fc3f7"},{"label":T("はりの閉形式","beam closed form"),"values":r["true_mm"],"unit":"mm","color":"#ffb74d"}]
    pane={"label":T("雑音と照明変動を含むカメラ像","camera image with noise and illumination drift"),"frames":r["images"],"png":True,"wide":True}
    tabs=[]
    tabs.append(pv.viewer_anim3d_tab("bridge",T("移動荷重で桁がたわむ","A moving load bends the beam"),"passed",T("格子で決めた桁と合成荷重。表示だけはたわみを誇張した。","A gridded synthetic beam and load; deflection is exaggerated only in the 3-D display."),time,objs,xyz,quat,series=series,checks=_checks(g),axis=axis,lesson=_lesson(T("たわみが最大になるのは荷重がどこに来た時?","Where is the load when deflection is largest?"),[T("支点の近く","near a support"),T("スパン中央","at midspan")],1,T("左右の支点から最も遠い中央で曲げが最大になる。","Bending is greatest at the point farthest from both supports."),T("Euler–Bernoulli の単純支持はり","Euler–Bernoulli simply supported beam"),T("合成模型であり、安全診断には使わない。","This synthetic model is not for safety diagnosis."))))
    tabs.append(pv.viewer_anim3d_tab("dic",T("斑点の移動を相関で測る","Measure speckle motion by correlation"),"passed",T("無荷重時に別撮影した雑音・照明ゆらぎ入りの基準コマから固定 31×31 画素窓を切り出す。各コマを find_ncc_model で探索し、3 点放物線で副画素位置を求める。原画と真値は推定器へ渡さない。","A fixed 31 by 31 pixel window is cut from a separately captured unloaded reference frame containing noise and illumination fluctuation. Each frame is searched by find_ncc_model and refined by a three-point parabola. Neither the clean texture nor truth is passed to the estimator."),time,objs,xyz,quat,panes=[pane],series=series,checks=_checks(g),axis=axis,lesson=_lesson(T("一番明るい斑点だけを追えばよい?","Is tracking only the brightest speckle enough?"),[T("よい","yes"),T("模様全体を相関する","correlate the whole pattern")],1,T("模様全体なら雑音や一個の斑点の変化を平均できる。","The whole pattern averages noise and changes in one speckle."),T("NCC = 正規化相互相関","NCC = normalized cross-correlation"),T("窓内の変形が大きい場合は多点 DIC が要る。","Large within-window deformation needs multi-point DIC."))))
    tabs.append(pv.viewer_anim3d_tab("scale",T("1 画素を mm に直す","Convert one pixel to millimetres"),"passed",T("距離と焦点距離で決まる投影倍率を 0.40 mm/画素と仮定し、副画素相関の移動量を換算する。","Projection scale set by distance and focal length is assumed to be 0.40 mm per pixel; subpixel correlation shifts are converted with it."),time,objs,xyz,quat,panes=[pane],series=series,checks=_checks(g),axis=axis,lesson=_lesson(T("遠くへ離れると同じたわみは像でどうなる?","What happens to the same deflection farther away?"),[T("画素移動が小さくなる","pixel motion becomes smaller"),T("画素移動が大きくなる","pixel motion becomes larger")],0,T("同じ焦点距離なら距離に反比例して像の移動が小さくなる。","At fixed focal length, image motion decreases inversely with distance."),T("物体寸法/画素 = pixel pitch × distance / focal length","object size/pixel = pixel pitch × distance / focal length"),T("0.40 mm/画素は説明用の仮定。校正誤差は含めない。","0.40 mm per pixel is an explanatory assumption; calibration error is omitted."))))
    tabs.append(pv.viewer_anim3d_tab("limit",T("カメラも空気も動く","The camera and air also move"),"limit",T("基準と変形後の両コマへ独立な雑音を入れ、固定窓のまま雑音を増やした。ばらつきは Cramér–Rao 近似の傾き 1 と比べる。RMSE の門は、雑音ゼロで測った補間バイアス %.4f mm と、公称雑音で測った標準偏差 %.4f mm の 3 倍との和 %.4f mm である。しかし陽炎やカメラ揺れは桁の動きと区別できない。"%(g["systematic_rms_mm"],g["nominal_spread_mm"],g["limit_mm"]),"Independent noise is added to both reference and deformed frames while the window remains fixed. Spread is compared with the Cramér–Rao slope of 1. The RMSE gate, %.4f mm, is the zero-noise interpolation bias %.4f mm plus three times the measured nominal-noise standard deviation %.4f mm. Shimmer and camera shake still cannot be distinguished from beam motion."%(g["limit_mm"],g["systematic_rms_mm"],g["nominal_spread_mm"])),time,objs,xyz,quat,panes=[pane],series=series,checks=_checks(g,True),axis=axis,lesson=_lesson(T("画面全体が揺れた時、桁のたわみと区別するには?","How can whole-image shake be separated from beam deflection?"),[T("不動点の参照ターゲットを使う","use a fixed reference target"),T("桁だけを見る","look only at the beam")],0,T("橋の外の不動点を同時に測り、共通の動きを差し引く。","Measure a fixed point outside the bridge and subtract common motion."),T("relative motion = beam target − fixed target","relative motion = beam target − fixed target"),T("陽炎、揺れ、照明変化は未計算。現場試験なしに保守判断へ使えない。","Shimmer, shake and lighting changes are uncomputed; field tests are required before maintenance use."))))
    return pv.viewer_spec("bridge_dic",T("橋のたわみを離れたカメラで測る","Measure bridge deflection with a distant camera"),T("合成した斑点像を DIC で追い、はりの式と独立に比べる","Track synthetic speckle images by DIC and compare independently with beam theory"),T("①問い → ②予想 → ③再生 → ④式 → ⑤限界。値はすべて合成観測から計算する。","Follow question, prediction, play, formula and limit. Every measured value comes from synthetic observations."),tabs,credit=T("すべて合成。スパン、たわみ、投影倍率、雑音は一般的な説明用の仮定で、実在の橋・自治体・会社・製品を表さない。","Entirely synthetic. Span, deflection, projection scale and noise are general explanatory assumptions, not a real bridge, authority, company or product."))


def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument("--out",default=str(OUT_HTML)); ap.add_argument("--check",action="store_true"); a=ap.parse_args(argv)
    r=compute(); g=gates(r)
    for k,v in g.items():
        if np.isscalar(v): print("%-24s %s"%(k,v))
    spec=build_spec(r,g)
    if a.check:
        print("ok: %d bytes (not written)"%len(pv._build_html(spec,list(LANGS)).encode("utf-8"))); return 0
    pv.write_viewer(spec,a.out,list(LANGS)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
