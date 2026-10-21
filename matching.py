"""テンプレートマッチング(HALCON "Matching" chapter の genuine core, numpy 自作).

handle ベースの HALCON matching の**アルゴリズム核**(NCC/SSD/相関)を本物で実装する。
model は軽量 dict(create → find のペア)。画像は [0,1] の 2D float64、template も同様。
"""
from __future__ import annotations

import numpy as np
from scipy import signal


def _f(a):
    return np.asarray(a, dtype=np.float64)


def _ncc_map(t_or_model, img):
    """Return a valid Pearson NCC map with values in ``[-1, 1]``.

    Scores are invariant to positive scaling.  A constant template or a
    truly constant image window has no defined correlation and scores 0.
    """
    if isinstance(t_or_model, dict):
        t = t_or_model["template"]
        t0 = t_or_model["t0n"]
        tn = float(t_or_model["norm"])
    else:
        t = _f(t_or_model)
        t0 = t - t.mean()
        tn = np.linalg.norm(t0)
        if tn > np.finfo(np.float64).tiny:
            t0 = t0 / tn
    img = _f(img)
    H, W = img.shape
    h, w = t.shape
    shape = (max(H - h + 1, 0), max(W - w + 1, 0))
    out = np.full(shape, -1.0)
    if not out.size:
        return out
    if tn <= np.finfo(np.float64).tiny:
        out.fill(0.0)
        return out
    # Direct correlation wins for small kernels; beyond 15x15 FFT avoids the
    # quadratic template-size cost.  Local moments come from integral images.
    method = "direct" if h * w <= 225 else "fft"
    cross = signal.correlate(img, t0, mode="valid", method=method)
    integral = np.pad(np.cumsum(np.cumsum(img, axis=0), axis=1), ((1, 0), (1, 0)))
    integral2 = np.pad(np.cumsum(np.cumsum(img * img, axis=0), axis=1), ((1, 0), (1, 0)))
    sums = integral[h:, w:] - integral[:-h, w:] - integral[h:, :-w] + integral[:-h, :-w]
    sums2 = integral2[h:, w:] - integral2[:-h, w:] - integral2[h:, :-w] + integral2[:-h, :-w]
    variance = sums2 - sums * sums / (h * w)
    variance = np.maximum(variance, 0.0)
    window_scale = np.maximum(np.abs(sums) / (h * w),
                              np.sqrt(np.maximum(sums2, 0.0) / (h * w)))
    threshold = (h * w) * (1e-6 * window_scale) ** 2
    stable = variance > threshold
    out.fill(0.0)
    out[stable] = cross[stable] / np.sqrt(variance[stable])
    # Recompute windows whose integral moments can lose their small variation
    # beside a large offset.  The threshold is relative to each window.
    unstable = ~stable
    for i, j in np.argwhere(unstable):
        p = img[i:i + h, j:j + w]
        p0 = p - p.mean()
        pn = np.linalg.norm(p0)
        if pn > np.finfo(np.float64).tiny:
            out[i, j] = float((p0 * t0).sum() / pn)
    np.clip(out, -1.0, 1.0, out=out)
    return out


def create_ncc_model(template) -> dict:
    """NCC モデル(=正規化テンプレート)を準備(create_ncc_model)。

    呼び出し元の配列とは独立した float64 コピーと、探索で再利用する中心化・
    単位ノルム化済みテンプレートを保持する。
    """
    source = np.asarray(template)
    t = np.array(source, dtype=np.float64, copy=True)
    mean = float(t.mean())
    t0 = t - mean
    norm = float(np.linalg.norm(t0))
    t0n = t0 / norm if norm > np.finfo(np.float64).tiny else np.zeros_like(t0)
    try:
        from fullseye import __version__
        version = __version__
    except (ImportError, AttributeError):
        version = "0"
    return {
        "template": t,
        "t0n": t0n,
        "norm": norm,
        "mean": mean,
        "shape": t.shape,
        "origin": (t.shape[0] // 2, t.shape[1] // 2),
        "dtype": source.dtype,
        "version": version,
    }


def find_ncc_model(model, image, min_score: float = 0.5) -> dict:
    """NCC モデルを画像中で探索し最良一致(行/列/スコア)を返す(find_ncc_model)。"""
    t = model["template"] if isinstance(model, dict) else _f(model)
    m = _ncc_map(model if isinstance(model, dict) else t, image)
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
    oh, ow = H - h + 1, W - w + 1
    if oh <= 0 or ow <= 0:
        return {"row": -1, "col": -1, "column": -1, "error": np.inf}
    method = "direct" if h * w <= 225 else "fft"
    cross = signal.correlate(img, t, mode="valid", method=method)
    sq = img * img
    integral = np.pad(np.cumsum(np.cumsum(sq, axis=0), axis=1), ((1, 0), (1, 0)))
    patch_sq = integral[h:, w:] - integral[:-h, w:] - integral[h:, :-w] + integral[:-h, :-w]
    errors = np.maximum(patch_sq - 2.0 * cross + float((t * t).sum()), 0.0)
    i, j = np.unravel_index(int(np.argmin(errors)), errors.shape)
    # Return the directly accumulated value, preserving the former public result.
    d = float(((img[i:i + h, j:j + w] - t) ** 2).sum())
    best = (d, int(i), int(j))
    # 基準点は find_ncc_model / find_shape_model と同じ **テンプレート中心**。
    r, c = best[1] + h // 2, best[2] + w // 2
    return {"row": r, "col": c, "column": c, "row_tl": best[1], "col_tl": best[2],
            "error": best[0]}


def exhaustive_match(template, image) -> dict:
    """全探索 NCC の最良一致(find_ncc_model と同核、error=1-score も返す)。"""
    r = find_ncc_model(create_ncc_model(template), image, min_score=-1.0)
    r["error"] = 1.0 - r["score"]
    return r
