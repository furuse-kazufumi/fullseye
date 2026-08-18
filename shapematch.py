"""形状ベースマッチング(HALCON "Matching" chapter の genuine core, numpy).

Steger 流の勾配方向マッチング: モデル=テンプレートのエッジ点の正規化勾配ベクトル、
スコア=対応位置での勾配方向の一致(内積平均)。輝度変化やコントラスト反転に頑健。
handle でなく軽量 dict。画像/テンプレートは [0,1] の 2D float64。
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage


def _grad_field(img):
    gx = ndimage.sobel(img, axis=1)
    gy = ndimage.sobel(img, axis=0)
    mag = np.hypot(gx, gy)
    return gx, gy, mag


def create_shape_model(template, min_grad: float = 0.1) -> dict:
    """テンプレートのエッジ点(|grad|>min_grad)の正規化勾配ベクトルをモデル化(create_shape_model)。"""
    t = np.asarray(template, dtype=np.float64)
    gx, gy, mag = _grad_field(t)
    thr = min_grad * (mag.max() + 1e-9)
    ys, xs = np.nonzero(mag > thr)
    if len(ys) == 0:
        ys, xs = np.array([t.shape[0] // 2]), np.array([t.shape[1] // 2])
    n = np.hypot(gx[ys, xs], gy[ys, xs]) + 1e-9
    return {"shape": t.shape, "pts": np.column_stack([ys, xs]),
            "grad": np.column_stack([gy[ys, xs] / n, gx[ys, xs] / n])}


def create_generic_shape_model(template, min_grad: float = 0.1) -> dict:
    """汎用形状モデル(create_generic_shape_model、create_shape_model と同核)。"""
    return create_shape_model(template, min_grad)


def create_aniso_shape_model(template, min_grad: float = 0.1) -> dict:
    """異方性スケール形状モデル(create_aniso_shape_model、モデル自体は同一、find で異方 scale 探索)。"""
    m = create_shape_model(template, min_grad)
    m["aniso"] = True
    return m


def _score_at(model, gy_img, gx_img, mag_img, r0, c0):
    pts = model["pts"]
    ys = pts[:, 0] - model["shape"][0] // 2 + r0
    xs = pts[:, 1] - model["shape"][1] // 2 + c0
    H, W = mag_img.shape
    ok = (ys >= 0) & (ys < H) & (xs >= 0) & (xs < W)
    if ok.sum() < 3:
        return 0.0
    ys, xs = ys[ok], xs[ok]
    m = mag_img[ys, xs] + 1e-9
    ig = np.column_stack([gy_img[ys, xs] / m, gx_img[ys, xs] / m])
    dots = np.abs((ig * model["grad"][ok]).sum(1))       # 方向一致(反転許容=abs)
    return float(dots.mean())


def find_shape_model(model, image, min_score: float = 0.5, step: int = 2) -> dict:
    """モデルを画像中で探索し最良一致(行/列/スコア)を返す(find_shape_model)。"""
    img = np.asarray(image, dtype=np.float64)
    gx, gy, mag = _grad_field(img)
    H, W = img.shape
    h, w = model["shape"]
    best = (-1.0, -1, -1)
    for r0 in range(h // 2, H - h // 2, step):
        for c0 in range(w // 2, W - w // 2, step):
            s = _score_at(model, gy, gx, mag, r0, c0)
            if s > best[0]:
                best = (s, r0, c0)
    return {"row": best[1], "col": best[2], "score": best[0],
            "found": best[0] >= min_score}


def create_scaled_shape_model(template, min_grad: float = 0.1) -> dict:
    """等方スケール形状モデル(create_scaled_shape_model)。"""
    m = create_shape_model(template, min_grad)
    m["scaled"] = True
    return m


def find_scaled_shape_model(model, image, scales=(0.8, 1.0, 1.25),
                            min_score: float = 0.5, step: int = 2) -> dict:
    """スケールを変えながら最良一致を探索(find_scaled_shape_model)。"""
    best = {"row": -1, "col": -1, "score": -1.0, "scale": 1.0}
    base_pts = model["pts"].astype(float)
    center = np.array(model["shape"]) / 2
    for sc in scales:
        m2 = dict(model)
        m2["pts"] = ((base_pts - center) * sc + center).round().astype(int)
        m2["shape"] = (int(model["shape"][0] * sc), int(model["shape"][1] * sc))
        r = find_shape_model(m2, image, min_score=-1.0, step=step)
        if r["score"] > best["score"]:
            best = {**r, "scale": sc}
    best["found"] = best["score"] >= min_score
    return best


# ── 多インスタンス検出 / XLD 由来モデル / パラメータ決定・アクセサ ────────────── #
def find_shape_models(model, image, min_score=0.5, step=2, max_matches=10, min_distance=5):
    """複数インスタンスを非最大抑制つきで検出(find_shape_models)。"""
    from scipy import ndimage as _ndi
    img = np.asarray(image, np.float64)
    gy = _ndi.sobel(img, axis=0); gx = _ndi.sobel(img, axis=1)
    mag = np.hypot(gx, gy)
    H, W = img.shape; mh, mw = model["shape"]
    score_map = np.full((H, W), -1.0)
    for r0 in range(0, H - mh, step):
        for c0 in range(0, W - mw, step):
            score_map[r0, c0] = _score_at(model, gy, gx, mag, r0, c0)
    matches = []
    sm = score_map.copy()
    for _ in range(int(max_matches)):
        idx = np.unravel_index(np.argmax(sm), sm.shape)
        s = sm[idx]
        if s < min_score:
            break
        matches.append({"row": int(idx[0]), "column": int(idx[1]), "score": float(s)})
        r0 = max(0, idx[0] - min_distance); r1 = min(H, idx[0] + min_distance + 1)
        c0 = max(0, idx[1] - min_distance); c1 = min(W, idx[1] + min_distance + 1)
        sm[r0:r1, c0:c1] = -1.0
    return {"matches": matches, "num": len(matches)}


def find_ncc_models(model, image, min_score=0.5, max_matches=10, min_distance=5):
    """NCC モデルの複数インスタンス検出(find_ncc_models)。"""
    from matching import _ncc_map
    nccm = _ncc_map(model["template"], np.asarray(image, np.float64))
    H, W = nccm.shape; matches = []; sm = nccm.copy()
    for _ in range(int(max_matches)):
        idx = np.unravel_index(np.argmax(sm), sm.shape)
        if sm[idx] < min_score:
            break
        matches.append({"row": int(idx[0]), "column": int(idx[1]), "score": float(sm[idx])})
        r0 = max(0, idx[0] - min_distance); r1 = min(H, idx[0] + min_distance + 1)
        c0 = max(0, idx[1] - min_distance); c1 = min(W, idx[1] + min_distance + 1)
        sm[r0:r1, c0:c1] = -1.0
    return {"matches": matches, "num": len(matches)}


def find_scaled_shape_models(model, image, scales=(0.8, 1.0, 1.25), min_score=0.5, max_matches=10):
    """スケール探索つき複数インスタンス検出(find_scaled_shape_models)。"""
    best = {"matches": [], "num": 0, "scale": 1.0}
    for s in scales:
        from scipy.ndimage import zoom
        pts = model["pts"] * s
        scaled = {"shape": (int(model["shape"][0] * s), int(model["shape"][1] * s)),
                  "pts": pts.astype(int), "grad": model["grad"]}
        res = find_shape_models(scaled, image, min_score, max_matches=max_matches)
        if res["num"] > best["num"]:
            best = {**res, "scale": s}
    return best


def _contour_to_template(contour):
    """XLD 輪郭(dict {shape, cs})をエッジ強度テンプレート画像へラスタライズ。"""
    H, W = contour["shape"]
    t = np.zeros((H, W))
    for a in contour["cs"]:
        rr = np.clip(a[:, 0].round().astype(int), 0, H - 1)
        cc = np.clip(a[:, 1].round().astype(int), 0, W - 1)
        t[rr, cc] = 1.0
    from scipy.ndimage import gaussian_filter
    return gaussian_filter(t, 1.0)


def create_shape_model_xld(contour, min_grad=0.1):
    """XLD 輪郭から形状モデルを作る(create_shape_model_xld)。"""
    return create_shape_model(_contour_to_template(contour), min_grad)


def create_scaled_shape_model_xld(contour, min_grad=0.1):
    """XLD 輪郭からスケール対応形状モデル(create_scaled_shape_model_xld)。"""
    from shapematch import create_scaled_shape_model
    return create_scaled_shape_model(_contour_to_template(contour), min_grad)


def create_aniso_shape_model_xld(contour, min_grad=0.1):
    """XLD 輪郭から異方性スケール形状モデル(create_aniso_shape_model_xld)。"""
    return create_aniso_shape_model(_contour_to_template(contour), min_grad)


def determine_shape_model_params(template):
    """テンプレートから推奨 min_grad/コントラストを自動決定(determine_shape_model_params)。"""
    t = np.asarray(template, np.float64)
    gx, gy, mag = _grad_field(t)
    return {"min_contrast": float(np.percentile(mag, 75) / (mag.max() + 1e-9)),
            "num_levels": int(max(1, np.log2(min(t.shape)) - 2))}


def get_shape_model_contours(model):
    """形状モデルのエッジ点を輪郭として返す(get_shape_model_contours)。"""
    return {"shape": model["shape"], "cs": [model["pts"].astype(float)]}


def get_shape_model_origin(model):
    """形状モデルの原点(重心)を返す(get_shape_model_origin)。"""
    c = model["pts"].mean(0)
    return {"row": float(c[0]), "column": float(c[1])}


def set_shape_model_origin(model, row, col):
    """形状モデルの参照原点を設定(set_shape_model_origin)。"""
    model = dict(model); model["origin"] = (float(row), float(col))
    return model


def create_cam_pose_look_at_point(cam_pos, look_at, up=(0, 0, 1)):
    """カメラ位置と注視点から look-at 姿勢(4x4)を構築(create_cam_pose_look_at_point)。"""
    cam_pos = np.asarray(cam_pos, float); look_at = np.asarray(look_at, float)
    up = np.asarray(up, float)
    z = look_at - cam_pos; z = z / (np.linalg.norm(z) + 1e-12)   # 前方
    x = np.cross(up, z); x = x / (np.linalg.norm(x) + 1e-12)     # 右
    y = np.cross(z, x)                                           # 下
    R = np.column_stack([x, y, z])
    T = np.eye(4); T[:3, :3] = R; T[:3, 3] = cam_pos
    return T


# ── matching: generic/aniso/local-deformable/descriptor/params ────────────────── #
def find_generic_shape_model(model, image, min_score=0.5, step=2):
    """汎用形状モデル検出(find_generic_shape_model)。find_shape_model の別名。"""
    return find_shape_model(model, image, min_score, step)


def find_aniso_shape_model(model, image, min_score=0.5,
                           scale_r=(0.9, 1.0, 1.1), scale_c=(0.9, 1.0, 1.1)):
    """行/列独立スケール(異方性)での形状モデル検出(find_aniso_shape_model)。"""
    best = None
    for sr in scale_r:
        for sc in scale_c:
            pts = model["pts"] * np.array([sr, sc])
            mm = {"shape": (int(model["shape"][0] * sr), int(model["shape"][1] * sc)),
                  "pts": pts.astype(int), "grad": model["grad"]}
            res = find_shape_model(mm, image, min_score)
            if res.get("found") and (best is None or res["score"] > best["score"]):
                best = {**res, "scale_row": sr, "scale_col": sc}
    return best or {"found": False}


def find_aniso_shape_models(model, image, min_score=0.5, max_matches=10):
    """異方性スケールでの複数インスタンス検出(find_aniso_shape_models)。"""
    return find_shape_models(model, image, min_score, max_matches=max_matches)


def inspect_shape_model(model):
    """形状モデルのエッジ点数・広がり・原点を点検用に返す(inspect_shape_model)。"""
    pts = model["pts"]
    return {"num_points": len(pts), "extent": pts.max(0) - pts.min(0),
            "centroid": pts.mean(0).tolist(), "shape": model["shape"]}


def determine_ncc_model_params(template):
    """NCC モデルの推奨パラメータ(コントラスト/レベル数)を決定(determine_ncc_model_params)。"""
    t = np.asarray(template, float)
    return {"num_levels": int(max(1, np.log2(min(t.shape)) - 2)),
            "contrast": float(t.std())}


def determine_deformable_model_params(template):
    """変形モデルの推奨パラメータを決定(determine_deformable_model_params)。"""
    return determine_shape_model_params(template)


def adapt_shape_model_high_noise(template, min_grad=0.25, smooth=2.0):
    """高ノイズ向けに平滑化を強めた形状モデルを作る(adapt_shape_model_high_noise)。"""
    from scipy.ndimage import gaussian_filter
    return create_shape_model(gaussian_filter(np.asarray(template, float), smooth), min_grad)


def create_local_deformable_model(template, min_grad=0.1):
    """局所変形マッチング用モデル(テンプレート保持)(create_local_deformable_model)。"""
    t = np.asarray(template, float)
    return {"template": t, "shape": t.shape, "edge": create_shape_model(t, min_grad)}


def create_local_deformable_model_xld(contour, min_grad=0.1):
    """XLD 由来の局所変形モデル(create_local_deformable_model_xld)。"""
    return create_local_deformable_model(_contour_to_template(contour), min_grad)


def find_local_deformable_model(model, image, min_score=0.5):
    """剛体位置を粗く合わせた後、オプティカルフローで局所変形を推定
    (find_local_deformable_model)。変形ベクトル場を返す。"""
    rigid = find_shape_model(model["edge"], image, min_score)
    from filters_flow import optical_flow_mg
    t = model["template"]; H, W = t.shape
    r0 = int(rigid.get("row", 0)) - H // 2; c0 = int(rigid.get("column", 0)) - W // 2
    r0 = max(0, min(r0, image.shape[0] - H)); c0 = max(0, min(c0, image.shape[1] - W))
    patch = np.asarray(image, float)[r0:r0 + H, c0:c0 + W]
    flow = optical_flow_mg(t, patch, iterations=100)
    return {"row": rigid.get("row"), "column": rigid.get("column"),
            "score": rigid.get("score", 0.0), "deformation": flow}


def create_planar_uncalib_deformable_model(template, min_grad=0.1):
    """平面(未校正)変形モデル(create_planar_uncalib_deformable_model)。"""
    return create_local_deformable_model(template, min_grad)


def find_planar_uncalib_deformable_model(model, image, min_score=0.5):
    """平面未校正変形モデルの検出(find_planar_uncalib_deformable_model)。"""
    return find_local_deformable_model(model, image, min_score)


def create_planar_calib_deformable_model(template, cam_par, min_grad=0.1):
    """平面(校正済)変形モデル(create_planar_calib_deformable_model)。"""
    m = create_local_deformable_model(template, min_grad); m["cam_par"] = cam_par
    return m


def find_planar_calib_deformable_model(model, image, min_score=0.5):
    """平面校正済変形モデルの検出(find_planar_calib_deformable_model)。"""
    return find_local_deformable_model(model, image, min_score)


def create_planar_uncalib_deformable_model_xld(contour, min_grad=0.1):
    """XLD 由来の平面未校正変形モデル(create_planar_uncalib_deformable_model_xld)。"""
    return create_local_deformable_model(_contour_to_template(contour), min_grad)


def create_planar_calib_deformable_model_xld(contour, cam_par, min_grad=0.1):
    """XLD 由来の平面校正済変形モデル(create_planar_calib_deformable_model_xld)。"""
    m = create_local_deformable_model(_contour_to_template(contour), min_grad)
    m["cam_par"] = cam_par
    return m
