"""外観検査(HALCON "Inspection" chapter の genuine core, numpy 自作).

variation model = 良品画像群の画素毎 mean±std。compare = 偏差が閾値超えの画素=欠陥領域。
古典的で明快な検査アルゴリズムを本物で実装する。画像は [0,1] の 2D float64。
"""
from __future__ import annotations

import numpy as np


def create_variation_model(images) -> dict:
    """良品画像群から画素毎の平均・標準偏差の variation model を作る(create_variation_model)。"""
    stack = np.stack([np.asarray(im, dtype=np.float64) for im in images], axis=0)
    return {"mean": stack.mean(0), "std": stack.std(0)}


def compare_variation_model(image, model, k: float = 3.0):
    """画像を variation model と比較し |image-mean| > k*std の欠陥領域を返す(compare_variation_model)。"""
    img = np.asarray(image, dtype=np.float64)
    dev = np.abs(img - model["mean"])
    thr = k * model["std"] + 1e-6
    return (dev > thr).astype(np.float64)


def compare_ext_variation_model(image, model, k: float = 3.0, abs_thresh: float = 0.05):
    """拡張比較: 相対(k*std)と絶対(abs_thresh)の両閾値を満たす画素を欠陥に(compare_ext_variation_model)。"""
    img = np.asarray(image, dtype=np.float64)
    dev = np.abs(img - model["mean"])
    return ((dev > k * model["std"] + 1e-6) & (dev > abs_thresh)).astype(np.float64)
