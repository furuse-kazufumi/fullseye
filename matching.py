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


def _parabolic_offset(before, peak, after):
    denominator = before - 2.0 * peak + after
    if denominator == 0.0:
        return 0.0
    return float(np.clip(0.5 * (before - after) / denominator, -0.5, 0.5))


def _ncc_candidates(score_map, shape, min_score, num_matches, max_overlap,
                    min_distance, subpixel, origin):
    h, w = shape
    order = np.argsort(-score_map, axis=None, kind="stable")
    accepted = []
    for flat_index in order:
        map_index = np.unravel_index(int(flat_index), score_map.shape)
        r0, c0 = int(map_index[0]), int(map_index[1])
        score = float(score_map[r0, c0])
        if score < min_score:
            break
        if min_distance is not None:
            suppressed = any(
                abs(r0 - other[0]) <= min_distance
                and abs(c0 - other[1]) <= min_distance
                for other in accepted
            )
        else:
            suppressed = False
            for other_r, other_c in accepted:
                overlap_h = max(0, h - abs(r0 - other_r))
                overlap_w = max(0, w - abs(c0 - other_c))
                intersection = overlap_h * overlap_w
                iou = intersection / (2 * h * w - intersection)
                if iou > max_overlap:
                    suppressed = True
                    break
        if suppressed:
            continue
        accepted.append((r0, c0))
        row, col = r0 + origin[0], c0 + origin[1]
        match = {"row": row, "col": col, "column": col, "row_tl": r0,
                 "col_tl": c0, "score": score}
        if subpixel == "interpolation":
            dr = dc = 0.0
            if 0 < r0 < score_map.shape[0] - 1:
                dr = _parabolic_offset(score_map[r0 - 1, c0], score,
                                       score_map[r0 + 1, c0])
            if 0 < c0 < score_map.shape[1] - 1:
                dc = _parabolic_offset(score_map[r0, c0 - 1], score,
                                       score_map[r0, c0 + 1])
            match["row_sub"] = float(row + dr)
            match["col_sub"] = float(col + dc)
        yield match
        if len(accepted) >= num_matches:
            break


def find_ncc_model(model, image, min_score: float = 0.5, *, num_matches=1,
                   max_overlap=0.5, subpixel="none", angle_start=None,
                   angle_extent=None, num_levels=None, min_distance=None) -> dict:
    """NCC モデルを画像中で探索する(find_ncc_model)。

    Args:
        model: ``create_ncc_model`` の結果、または2次元テンプレート。
        image: 探索対象の2次元画像。
        min_score: 複数候補に含める最小NCCスコア。
        num_matches: 返す候補の最大数。既定は1。
        max_overlap: テンプレート矩形間のIoUがこの値を超える候補を抑制する。
            既定の0.5はHALCONの``MaxOverlap``既定値と同じ。
        subpixel: ``"none"``、または軸別3点放物線補間を行う
            ``"interpolation"``。
        angle_start: 未対応。HALCONの既定角度探索は0。
        angle_extent: 未対応。HALCONの既定角度探索は0。
        num_levels: 未対応の画像ピラミッド設定。
        min_distance: 旧``find_ncc_models``入口用の行列方向抑制距離。

    最良候補の従来キーに、スコア降順の ``matches`` を加えて返す。
    """
    unsupported = {"angle_start": angle_start, "angle_extent": angle_extent,
                   "num_levels": num_levels}
    for name, value in unsupported.items():
        if value is not None:
            raise NotImplementedError(
                f"find_ncc_model: {name} is not implemented in this version — "
                "rotation search and pyramids are tracked as H07 stage 2"
            )
    if int(num_matches) != num_matches or num_matches < 1:
        raise ValueError("num_matches must be a positive integer")
    if not 0.0 <= max_overlap <= 1.0:
        raise ValueError("max_overlap must be between 0 and 1")
    if subpixel not in {"none", "interpolation"}:
        raise ValueError("subpixel must be 'none' or 'interpolation'")
    t = model["template"] if isinstance(model, dict) else _f(model)
    m = _ncc_map(model if isinstance(model, dict) else t, image)
    if m.size == 0:
        return {"row": -1, "col": -1, "column": -1, "score": 0.0,
                "found": False, "matches": []}
    idx = np.unravel_index(int(np.argmax(m)), m.shape)
    score = float(m[idx])
    # **基準点はテンプレート中心**。_ncc_map の添字は左上なので中心へ直す。
    # HALCON の find_ncc_model が返すのはモデルの原点(既定 = 中心)であり、
    # 同じ物を探しても形状マッチ側 (find_shape_model) とテンプレート半分だけ
    # 座標がずれていた(実測: 中心 (60,150) に対し (40,130) を返していた)。
    # 左上が要る呼び出しのために row_tl/col_tl も併記する。
    r0, c0 = int(idx[0]), int(idx[1])
    origin = model.get("origin", (t.shape[0] // 2, t.shape[1] // 2)) \
        if isinstance(model, dict) else (t.shape[0] // 2, t.shape[1] // 2)
    r, c = r0 + origin[0], c0 + origin[1]
    candidate_threshold = -np.inf if int(num_matches) == 1 else min_score
    matches = list(_ncc_candidates(m, t.shape, candidate_threshold, int(num_matches),
                                   max_overlap, min_distance, subpixel, origin))
    result = {"row": r, "col": c, "column": c, "row_tl": r0, "col_tl": c0,
              "score": score, "found": score >= min_score, "matches": matches}
    if subpixel == "interpolation":
        if matches and matches[0]["row_tl"] == r0 and matches[0]["col_tl"] == c0:
            result["row_sub"] = matches[0]["row_sub"]
            result["col_sub"] = matches[0]["col_sub"]
        else:
            result["row_sub"] = float(r)
            result["col_sub"] = float(c)
    return result


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
