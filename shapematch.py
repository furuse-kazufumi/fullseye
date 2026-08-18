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
