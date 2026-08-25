"""テンプレートマッチング(HALCON "Matching" chapter の genuine core, numpy 自作).

handle ベースの HALCON matching の**アルゴリズム核**(NCC/SSD/相関)を本物で実装する。
model は軽量 dict(create → find のペア)。画像は [0,1] の 2D float64、template も同様。
"""
from __future__ import annotations

import numpy as np


def _f(a):
    return np.asarray(a, dtype=np.float64)


def _ncc_map(t, img):
    """正規化相互相関マップ(valid、[-1,1])を返す。"""
    t = _f(t)
    img = _f(img)
    t0 = t - t.mean()
    tn = np.sqrt((t0 ** 2).sum()) + 1e-12
    H, W = img.shape
    h, w = t.shape
    out = np.full((max(H - h + 1, 0), max(W - w + 1, 0)), -1.0)
    for i in range(out.shape[0]):
        for j in range(out.shape[1]):
            p = img[i:i + h, j:j + w]
            p0 = p - p.mean()
            out[i, j] = float((p0 * t0).sum() / (np.sqrt((p0 ** 2).sum()) * tn + 1e-12))
    return out


def create_ncc_model(template) -> dict:
    """NCC モデル(=正規化テンプレート)を準備(create_ncc_model)。"""
    t = _f(template)
    return {"template": t, "mean": float(t.mean()), "shape": t.shape}


def find_ncc_model(model, image, min_score: float = 0.5) -> dict:
    """NCC モデルを画像中で探索し最良一致(行/列/スコア)を返す(find_ncc_model)。"""
    t = model["template"] if isinstance(model, dict) else _f(model)
    m = _ncc_map(t, image)
    if m.size == 0:
        return {"row": -1, "col": -1, "column": -1, "score": 0.0, "found": False}
    idx = np.unravel_index(int(np.argmax(m)), m.shape)
    score = float(m[idx])
    # **基準点はテンプレート中心**。_ncc_map の添字は左上なので中心へ直す。
    # HALCON の find_ncc_model が返すのはモデルの原点(既定 = 中心)であり、
    # 同じ物を探しても形状マッチ側 (find_shape_model) とテンプレート半分だけ
    # 座標がずれていた(実測: 中心 (60,150) に対し (40,130) を返していた)。
    # 左上が要る呼び出しのために row_tl/col_tl も併記する。
    r0, c0 = int(idx[0]), int(idx[1])
    r, c = r0 + t.shape[0] // 2, c0 + t.shape[1] // 2
    return {"row": r, "col": c, "column": c, "row_tl": r0, "col_tl": c0,
            "score": score, "found": score >= min_score}


def best_match(template, image) -> dict:
    """SSD(二乗差)最小位置を返す(best_match)。"""
    t = _f(template)
    img = _f(image)
    H, W = img.shape
    h, w = t.shape
    best = None
    for i in range(H - h + 1):
        for j in range(W - w + 1):
            d = float(((img[i:i + h, j:j + w] - t) ** 2).sum())
            if best is None or d < best[0]:
                best = (d, i, j)
    if best is None:
        return {"row": -1, "col": -1, "column": -1, "error": np.inf}
    # 基準点は find_ncc_model / find_shape_model と同じ **テンプレート中心**。
    r, c = best[1] + h // 2, best[2] + w // 2
    return {"row": r, "col": c, "column": c, "row_tl": best[1], "col_tl": best[2],
            "error": best[0]}


def exhaustive_match(template, image) -> dict:
    """全探索 NCC の最良一致(find_ncc_model と同核、error=1-score も返す)。"""
    r = find_ncc_model(create_ncc_model(template), image, min_score=-1.0)
    r["error"] = 1.0 - r["score"]
    return r
