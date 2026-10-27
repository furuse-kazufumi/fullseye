# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""星の点像から衛星の姿勢を求める動く 3-D 学習ページ。"""
from __future__ import annotations

import argparse
import itertools
import math
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import fullseye as fs
import pocviewer as pv

OUT_HTML = ROOT / "docs" / "view2026" / "anim3d" / "star_tracker_anim3d.html"
LANGS = ("ja", "en")
SHAPE = (128, 128)
FOV_DEG = 18.0


def T(ja, en):
    return pv.viewer_text(ja, en)


def _e(x):
    return "< 1e-12" if abs(float(x)) < 1e-12 else "%.3g" % float(x)


def _rays(points):
    """(row,col) pixels to camera-frame unit rays; pixel centres are integer coordinates."""
    p = np.asarray(points, float)
    scale = 2.0 * math.tan(math.radians(FOV_DEG) / 2.0) / SHAPE[1]
    x = (p[:, 1] - (SHAPE[1] - 1) / 2.0) * scale
    y = -(p[:, 0] - (SHAPE[0] - 1) / 2.0) * scale
    q = np.column_stack([x, y, np.ones(len(p))])
    return q / np.linalg.norm(q, axis=1, keepdims=True)


def _catalog_match(measured, catalogue):
    """Triangle-angle hypotheses against the whole catalogue; return rows or -1.

    No attitude or visible-star row is given to this matcher.  Catalogue triples
    are found only by their mutual angles.  Each measured triangle and all six
    vertex permutations propose a rotation; the winner maximises unique catalogue
    matches within a fraction of one angular pixel.  Thus isolated hot pixels are
    outliers rather than extra catalogue stars.
    """
    cat = np.asarray(catalogue, float); obs = np.asarray(measured, float)
    max_side = 2.0 * math.sin(math.radians(FOV_DEG * 1.15) / 2.0)
    pairs = cKDTree(cat).query_pairs(max_side)
    neighbours = [set() for _ in range(len(cat))]
    for i, j in pairs:
        neighbours[i].add(j); neighbours[j].add(i)
    triples = []
    for i, j in pairs:
        if i > j: i, j = j, i
        for k in neighbours[i].intersection(neighbours[j]):
            if j < k:
                triples.append((i, j, k))
    triples = np.asarray(triples, int)
    if not len(triples):
        return np.full(len(obs), -1, int), np.eye(3), np.inf

    def tri_sig(x):
        return np.sort(np.arccos(np.clip(np.array([x[0]@x[1], x[0]@x[2], x[1]@x[2]]), -1, 1)))
    cat_sig = np.array([tri_sig(cat[t]) for t in triples])
    sig_tree = cKDTree(cat_sig)
    threshold = math.radians(FOV_DEG / SHAPE[1] * .55)
    best = (-1, np.inf, None, None)
    for oi in itertools.combinations(range(len(obs)), 3):
        _dist, near = sig_tree.query(tri_sig(obs[list(oi)]), k=min(2, len(triples)))
        for ci in np.atleast_1d(near):
            ct = triples[int(ci)]
            for perm in itertools.permutations(ct):
                r, _ = fs.kabsch(obs[list(oi)], cat[list(perm)])
                moved = obs @ r.T
                angles = np.arccos(np.clip(moved @ cat.T, -1, 1))
                rr, cc = linear_sum_assignment(angles)
                good = angles[rr, cc] < threshold
                score = int(np.sum(good))
                residual = float(np.sum(angles[rr[good], cc[good]])) if score else np.inf
                if score > best[0] or (score == best[0] and residual < best[1]):
                    rows = np.full(len(obs), -1, int); rows[rr[good]] = cc[good]
                    best = (score, residual, rows, r)
    rows, r = best[2], best[3]
    good = rows >= 0
    if np.sum(good) >= 3:
        r, _ = fs.kabsch(obs[good], cat[rows[good]])
    return rows, r, best[1]


def _direct_kabsch(src, dst):
    """Independent direct SVD path, retained as a numerical cross-check."""
    p, q = np.asarray(src), np.asarray(dst)
    pc, qc = p.mean(0), q.mean(0)
    u, _, vt = np.linalg.svd((p-pc).T @ (q-qc))
    d = np.sign(np.linalg.det(vt.T @ u.T))
    return vt.T @ np.diag([1.0, 1.0, d]) @ u.T


def _angle_deg(a, b):
    return math.degrees(math.acos(np.clip((np.trace(a @ b.T)-1)/2, -1, 1)))


def _quat_wxyz(r):
    q = Rotation.from_matrix(r).as_quat()
    return np.array([q[3], q[0], q[1], q[2]])


def compute():
    # This op supplies a noisy PSF image and deliberately off-centre subpixel truth.
    image, truth = fs.synth_starfield(shape=SHAPE, n_stars=16, flux_min=6000,
        flux_max=22000, fwhm_px=2.4, sky=35, read_sigma=3, margin_px=10,
        seed=20261026)
    # Two detector defects are not catalogue stars. Pick fixed pixels that stay
    # away from the planted PSFs, then let star_detect see them as ordinary peaks.
    hot = []
    planted = np.column_stack([truth["rows"], truth["cols"]])
    for rc in ((7, 7), (7, 120), (120, 7), (120, 120), (64, 7), (7, 64)):
        if np.min(np.linalg.norm(planted-np.asarray(rc), axis=1)) > 7:
            hot.append(rc)
        if len(hot) == 2: break
    image = image.copy()
    for row, col in hot:
        image[row, col] += 18000.0
    detected = fs.star_detect(image, threshold_sigma=5, min_separation=4,
                              max_stars=24, edge_margin=3, centroid_box=5, method="clip")
    truth_px = np.column_stack([truth["rows"], truth["cols"]])
    # This association is ground truth for scoring only; the matcher never sees it.
    d = np.linalg.norm(detected[:, None, :] - truth_px[None, :, :], axis=2)
    di, ti = linear_sum_assignment(d)
    keep = d[di, ti] < 1.2
    detection_truth_star = np.full(len(detected), -1, int)
    detection_truth_star[di[keep]] = ti[keep]
    true_r = Rotation.from_euler("zyx", [23.7, -11.4, 7.9], degrees=True).as_matrix()
    visible = _rays(truth_px) @ true_r.T
    measured = _rays(detected)
    # A fixed all-sky catalogue, shuffled so visible stars have no privileged rows.
    rng = np.random.default_rng(314159)
    background = rng.normal(size=(180, 3)); background /= np.linalg.norm(background, axis=1, keepdims=True)
    unshuffled = np.vstack([background, visible])
    permutation = rng.permutation(len(unshuffled)); catalogue = unshuffled[permutation]
    inverse = np.empty(len(permutation), int); inverse[permutation] = np.arange(len(permutation))
    truth_rows = np.full(len(detected), -1, int)
    genuine = detection_truth_star >= 0
    truth_rows[genuine] = inverse[180+detection_truth_star[genuine]]
    match, r_op, match_cost = _catalog_match(measured, catalogue)
    inlier = match >= 0
    r_svd = _direct_kabsch(measured[inlier], catalogue[match[inlier]])
    centroid_error = d[di[keep], ti[keep]]
    return dict(image=image, truth_px=truth_px, detected=detected, catalogue=catalogue,
        measured=measured, match=match, truth_rows=truth_rows, match_cost=match_cost,
        true_r=true_r, r_op=r_op, r_svd=r_svd, allsky=catalogue,
        centroid_error=centroid_error, hot=np.asarray(hot), n_genuine=int(np.sum(genuine)))


def gates(r):
    attitude_error = _angle_deg(r["r_op"], r["true_r"])
    svd_difference = float(np.max(np.abs(r["r_op"]-r["r_svd"])))
    genuine = r["truth_rows"] >= 0
    correct = float(np.mean(r["match"][genuine] == r["truth_rows"][genuine]))
    mismatch = int(np.sum(r["match"][genuine] != r["truth_rows"][genuine]))
    false_kept = int(np.sum(r["match"][~genuine] >= 0))
    limit = FOV_DEG / SHAPE[1]
    return dict(attitude_error_deg=attitude_error, angular_pixel_deg=limit,
        match_accuracy=correct, mismatch_count=mismatch, false_kept=false_kept,
        false_rejected=int(np.sum(~genuine)-false_kept), n_false=int(np.sum(~genuine)),
        kabsch_svd_max_difference=svd_difference,
        centroid_median_px=float(np.median(r["centroid_error"])), n_stars=int(np.sum(genuine)),
        n_detections=len(r["detected"]), catalogue_size=len(r["catalogue"]))


def _checks(g, limit=False):
    rows = [
        {"what":T("推定姿勢と真の姿勢の角度差", "angle between estimated and true attitude"),
         "criterion":"< %.3f deg" % g["angular_pixel_deg"], "result":"%.4f deg" % g["attitude_error_deg"],
         "ok":g["attitude_error_deg"] < g["angular_pixel_deg"]},
        {"what":T("角距離署名による対応付け", "angular-signature matching"), "criterion":T("誤対応 0", "0 mismatches"),
         "result":T("誤対応 %d / %d"%(g["mismatch_count"],g["n_stars"]), "%d / %d mismatches"%(g["mismatch_count"],g["n_stars"])), "ok":g["mismatch_count"]==0},
        {"what":T("星表に無いホットピクセル", "hot pixels absent from the catalogue"), "criterion":T("偽点をすべて捨てる", "reject every false point"),
         "result":T("%d / %d 個を棄却"%(g["false_rejected"],g["n_false"]), "%d / %d rejected"%(g["false_rejected"],g["n_false"])), "ok":g["false_kept"]==0},
        {"what":T("kabsch op と直接 SVD", "kabsch op vs direct SVD"), "criterion":"< 1e-12",
         "result":_e(g["kabsch_svd_max_difference"]), "ok":g["kabsch_svd_max_difference"]<1e-12},
    ]
    if limit:
        rows.append({"what":T("太陽・月、星不足、高速回転でも同じ精度", "same accuracy with Sun/Moon, too few stars, or fast slew"),
                     "criterion":T("迷光・不足・流れを含む", "includes glare, scarcity and trails"),
                     "result":T("未計算", "not computed"), "ok":False})
    return rows


def _lesson(q, choices, answer, explain, formula, limit):
    return {"question":q,"choices":choices,"answer":answer,"explain":explain,"formula":formula,"limit":limit}


def _poses(n, bodies):
    xyz=np.zeros((n,bodies,3)); q=np.zeros((n,bodies,4)); q[...,0]=1
    return xyz,q


def _sphere_points(points, radius=4.0):
    # Tiny octahedra make the random celestial points visible in the 3-D scene.
    verts=[]; faces=[]
    base=np.array([[.035,0,0],[-.035,0,0],[0,.035,0],[0,-.035,0],[0,0,.035],[0,0,-.035]])
    bf=np.array([[0,2,4],[2,1,4],[1,3,4],[3,0,4],[2,0,5],[1,2,5],[3,1,5],[0,3,5]])
    for p in points:
        off=len(verts); verts.extend(base+radius*p); faces.extend(bf+off)
    return np.asarray(verts),np.asarray(faces)


def _camera():
    p=np.array([[-.35,-.25,-.3],[.35,-.25,-.3],[.35,.25,-.3],[-.35,.25,-.3],[-.35,-.25,.3],[.35,-.25,.3],[.35,.25,.3],[-.35,.25,.3]])
    f=np.array([[0,1,2],[0,2,3],[4,6,5],[4,7,6],[0,4,5],[0,5,1],[1,5,6],[1,6,2],[2,6,7],[2,7,3],[3,7,4],[3,4,0]])
    return p,f


def _rgb(frame):
    lo,hi=np.percentile(frame,[2,99.8]); u=np.clip((frame-lo)/(hi-lo)*255,0,255).astype(np.uint8)
    return np.repeat(u[...,None],3,axis=2)


def build_spec(r,g):
    stars,sf=_sphere_points(r["allsky"]); cam,cf=_camera(); n=49
    t=np.arange(n)/24; tabs=[]
    xyz,q=_poses(n,2); xyz[:,1,2]=.5
    ang=np.linspace(0,1.1,n)
    q[:,1]=np.array([_quat_wxyz(Rotation.from_euler("y",a).as_matrix()) for a in ang])
    common=[{"name":"synthetic sky","pos":stars,"faces":sf,"rgb":[235,240,255]}, {"name":"satellite camera","pos":cam,"faces":cf,"rgb":[70,170,220]}]
    tabs.append(pv.viewer_anim3d_tab("fov",T("視野に入る星","Stars in the field of view"),"passed",
        T("固定した種で作った合成天球の中をカメラの視野錐が回る。2 星だけでは星を結ぶ軸まわりの回転が残るため、姿勢を一意にするには配置をもつ 3 星以上が要る。","A camera cone sweeps a seeded synthetic sky. Two stars leave rotation about their connecting axis ambiguous; three or more stars with geometry determine attitude."),
        t,common,xyz,q,series=[{"label":T("検出星数","detected stars"),"values":np.full(n,g["n_stars"]),"unit":"","color":"#ffd54f"}],
        numbers=[pv.viewer_number(T("この画像の星","stars in this image"),str(g["n_stars"])),pv.viewer_number(T("視野","field of view"),"18.0 deg")],checks=_checks(g),
        axis={"values":np.degrees(ang),"segments":[{"k":0,"label":T("衛星の回転","satellite rotation"),"unit":"deg","decimals":1}]},view={"az":-.8,"el":.35,"dist":1.05},
        lesson=_lesson(T("星 2 つだけで 3-D の向きは一意に決まる?","Do two stars uniquely fix a 3-D attitude?"),[T("決まる","yes, uniquely"),T("1 軸まわりが残る","rotation about one axis remains")],1,T("3 本以上の対応した方向ベクトルを使う。","Use three or more corresponded direction vectors."),T("catalogue direction = R × camera ray","catalogue direction = R × camera ray"),T("星表は実カタログでなく固定 seed の合成点。","The catalogue is seeded synthetic points, not a real catalogue."))))
    frames=np.repeat(_rgb(r["image"])[None],n,axis=0); xyz,q=_poses(n,1)
    tabs.append(pv.viewer_anim3d_tab("detect",T("像から星位置を取る","Locate stars in the image"),"passed",
        T("synth_starfield が PSF、光子雑音、読み出し雑音を含む像を作り、star_detect が背景を引いた重心を返す。真の中心は画素中心から外してある。","synth_starfield makes an image with PSF, photon noise and read noise; star_detect returns background-subtracted centroids. True centres are off pixel centres."),
        t,[{"name":"camera","pos":cam,"faces":cf,"rgb":[70,170,220]}],xyz,q,
        panes=[{"label":T("合成カメラ像: PSF + 雑音","synthetic camera image: PSF + noise"),"frames":frames,"png":True,"wide":True}],
        series=[{"label":T("重心誤差","centroid error"),"values":np.resize(r["centroid_error"],n),"unit":"px","color":"#4fc3f7"}],
        numbers=[pv.viewer_number(T("重心誤差の中央値","median centroid error"),"%.3f px"%g["centroid_median_px"]),pv.viewer_number(T("検出数(星 + 偽点)","detections (stars + false points)"),"%d (%d + %d)"%(g["n_detections"],g["n_stars"],g["n_false"]))],checks=_checks(g),
        axis={"values":np.arange(n),"segments":[{"k":0,"label":T("検出した点","detected point"),"unit":"","decimals":0}]},view={"az":-.7,"el":.4,"dist":.9},
        lesson=_lesson(T("一番明るい画素を星位置にすれば副画素精度になる?","Does the brightest pixel give subpixel position?"),[T("なる","yes, from one pixel"),T("重心が要る","a centroid is needed")],1,T("PSF の周囲の画素強度を重みにする。","Weight neighbouring pixels by the PSF intensity."),T("centroid = sum(I x) / sum(I)","centroid = sum(I x) / sum(I)"),T("接近した星や飽和はこの単純な重心から除いた。","Close pairs and saturation are omitted from this simple centroid model."))))
    xyz,q=_poses(n,2); q[:,0]=_quat_wxyz(r["true_r"]); q[:,1]=np.array([_quat_wxyz(Rotation.from_rotvec(Rotation.from_matrix(r["true_r"]).as_rotvec()*u).as_matrix()) for u in np.linspace(0,1,n)])
    tabs.append(pv.viewer_anim3d_tab("attitude",T("対応付けと Kabsch","Match and solve with Kabsch"),"passed",
        T("画像の星三つが作る角距離を、ランダム順の全196星表にある三角形と照合して姿勢仮説を作る。最も多くの点が一致する仮説を選び、偽点を捨て、検出光線を kabsch で星表方向へ回す。","Triangle angles from image stars are searched against every local triangle in the shuffled 196-star catalogue. The hypothesis with most agreeing points rejects outliers, then kabsch rotates detected rays onto catalogue directions."),
        t,common,xyz,q,series=[{"label":T("姿勢角誤差","attitude angle error"),"values":np.linspace(12,g["attitude_error_deg"],n),"unit":"deg","color":"#66bb6a","threshold":g["angular_pixel_deg"]}],
        numbers=[pv.viewer_number(T("姿勢角誤差","attitude angle error"),"%.4f deg"%g["attitude_error_deg"]),pv.viewer_number(T("誤対応 / 偽点棄却","mismatches / false points rejected"),"%d / %d"%(g["mismatch_count"],g["false_rejected"]))],checks=_checks(g),axis={"values":np.arange(n),"segments":[{"k":0,"label":T("解法の進行","solver progress"),"unit":"step","decimals":0}]},view={"az":-.8,"el":.35,"dist":1.0},
        lesson=_lesson(T("星の明るさだけで対応を決める?","Match stars by brightness alone?"),[T("はい","yes, brightness is enough"),T("角距離の配置を使う","use angular geometry")],1,T("回転しても星どうしの角距離は変わらない。三角形の候補から、全点の一致が最も多い姿勢を選ぶ。","Inter-star angles do not change under rotation. Triangle candidates vote for the attitude supported by the most points."),T("R = argmin sum ||R camera_i - catalogue_i||^2","R = argmin sum ||R camera_i - catalogue_i||^2"),T("196星の全探索を使う教材であり、大規模な実用星表の索引ではない。","This lesson searches 196 stars directly; it is not an index for a large operational catalogue."))))
    trails=np.repeat(frames,1,axis=0); xyz,q=_poses(n,1)
    tabs.append(pv.viewer_anim3d_tab("limits",T("迷光・星不足・星の流れ","Glare, too few stars and trails"),"limit",
        T("この成功例は点像と十分な星を仮定する。太陽や月の迷光、星が少ない視野、高速回転で伸びた星像は未計算なので、同じ精度とは言えない。","This successful case assumes point images and enough stars. Sun or Moon glare, a sparse field, and trails from fast slew are not computed, so the same accuracy cannot be claimed."),
        t,[{"name":"camera","pos":cam,"faces":cf,"rgb":[120,100,100]}],xyz,q,
        panes=[{"label":T("成功例の像。限界条件は未合成","successful image; limit cases are not synthesized"),"frames":trails,"png":True,"wide":True}],
        series=[{"label":T("使える星数","usable stars"),"values":np.linspace(g["n_stars"],2,n),"unit":"","color":"#ef5350","threshold":3}],numbers=[pv.viewer_number(T("一意な姿勢に必要","needed for a unique attitude"),T("3 星以上","3+ stars")),pv.viewer_number(T("未計算の条件","uncomputed conditions"),"3")],checks=_checks(g,True),axis={"values":np.linspace(0,1,n),"segments":[{"k":0,"label":T("限界への近さ","proximity to limit"),"unit":"","decimals":2}]},view={"az":-.7,"el":.4,"dist":.9},
        lesson=_lesson(T("点像で成功した結果を高速回転へそのまま使える?","Can a point-image result be reused unchanged during fast slew?"),[T("使える","yes"),T("星の流れを別に扱う","trails need a separate model")],1,T("伸びた像では点像の重心・対応付けの前提が変わる。","Trails change the assumptions behind centroiding and matching."),T("trail length ≈ angular rate × exposure","trail length ≈ angular rate × exposure"),T("太陽・月の迷光、星不足、星の流れは未計算。この行を ok:false にする。","Sun/Moon glare, too few stars and trails are uncomputed; this row is ok:false."))))
    return pv.viewer_spec("star_tracker",T("星の写真 1 枚で衛星の向きが分かるのはなぜか","How one star image reveals satellite attitude"),T("点像を測り、配置で星表へ結び、方向ベクトルの回転を解く","Measure point images, match their geometry to a catalogue, and solve the rotation"),T("①問い → ②予想 → ③再生 → ④式 → ⑤限界。ドラッグで回転し、バッジで計算の門を見る。","Follow ① question → ② prediction → ③ play → ④ formula → ⑤ limit. Drag to orbit; tap a badge for computed gates."),tabs,credit=T("星表と画像はすべて固定 seed の合成データ。実カタログ、事業者名、製品名、外部画像は使っていない。","Catalogue and image are entirely seeded synthetic data. No real catalogue, operator, product or external image is used."))


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
