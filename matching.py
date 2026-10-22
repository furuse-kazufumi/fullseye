"""テンプレートマッチング(HALCON "Matching" chapter の genuine core, numpy 自作).

handle ベースの HALCON matching の**アルゴリズム核**(NCC/SSD/相関)を本物で実装する。
model は軽量 dict(create → find のペア)。画像は [0,1] の 2D float64、template も同様。
"""
from __future__ import annotations

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from scipy import signal

from fslib import FsValueError


def _f(a):
    return np.asarray(a, dtype=np.float64)


def _ncc_scale(a, name, *, return_constant=False, return_exponent=False):
    """Return ``(finite float64 array, exact power-of-two scale)``."""
    value = _f(a)
    if not np.isfinite(value).all():
        raise FsValueError(f"{name} contains NaN or infinity")
    if value.size:
        minimum = float(np.min(value))
        maximum = float(np.max(value))
        magnitude = max(abs(minimum), abs(maximum))
        is_constant = minimum == maximum
    else:
        magnitude = 0.0
        is_constant = False
    if magnitude == 0.0:
        result = value, 1.0, 0
        selected = result if return_exponent else result[:2]
        return (*selected, is_constant) if return_constant else selected
    _, exponent = np.frexp(magnitude)
    if -500 <= exponent - 1 <= 500:
        result = value, 1.0, 0
    else:
        # A subnormal may request shift=1074.  Materialising 2**1074 as a
        # float overflows even though scaling the array is safe.  2**1023 is
        # finite and already brings every non-zero binary64 value into the
        # normal range, so cap only the stored/materialised scale.
        shift = min(1 - exponent, 1023)
        result = np.ldexp(value, shift), float(np.ldexp(1.0, shift)), shift
    selected = result if return_exponent else result[:2]
    return (*selected, is_constant) if return_constant else selected


def _ncc_local_variance(img, h, w):
    """Return integral-image window variances and their reliability mask."""
    # Removing a shared offset is exact for variance and prevents a large DC
    # level (or a smooth, narrow-range image) from consuming the significant
    # bits of the two integral images.  Keep ordinary [0, 1] imagery untouched
    # so its established score bits do not change unnecessarily.
    mean = float(img.mean())
    span = float(np.ptp(img))
    work = img - mean if abs(mean) > span else img
    integral = np.pad(np.cumsum(np.cumsum(work, axis=0), axis=1), ((1, 0), (1, 0)))
    squared = work * work
    integral2 = np.pad(np.cumsum(np.cumsum(squared, axis=0), axis=1), ((1, 0), (1, 0)))
    sums = integral[h:, w:] - integral[:-h, w:] - integral[h:, :-w] + integral[:-h, :-w]
    sums2 = integral2[h:, w:] - integral2[:-h, w:] - integral2[h:, :-w] + integral2[:-h, :-w]
    variance = np.maximum(sums2 - sums * sums / (h * w), 0.0)
    # Two cumulative sums and the four-corner subtraction expose each local
    # moment to error set by the largest cumulative squared magnitude, not by
    # the (possibly tiny) local result.  1e6 eps is deliberately conservative:
    # adversarial hot-pixel sweeps need this margin, while ordinary 512-square
    # random images flag no windows.
    accumulation = float(np.max(np.abs(integral2)))
    bound = 1e6 * np.finfo(np.float64).eps * accumulation
    unstable = variance <= bound
    # Preserve the exact legacy scores for small, extreme-offset fixtures.
    # Large searches use the offset-stabilized moments above; their fallback
    # would otherwise dominate runtime without improving the stated accuracy.
    if img.size < 65536 and abs(mean) > 1000.0 * max(span, np.finfo(float).tiny):
        unstable.fill(True)
    return variance, unstable


def _ncc_extreme_dynamic_range(value):
    """Whether one global scale would discard meaningful finite values."""
    nonzero = np.abs(value[value != 0.0])
    if not nonzero.size:
        return False
    _, maximum_exp = np.frexp(float(nonzero.max()))
    _, minimum_exp = np.frexp(float(nonzero.min()))
    return maximum_exp - minimum_exp > 500


def _ncc_exact_windows(out, img, t0, coordinates, h, w, *, local_scale=False):
    """Recompute selected Pearson scores with a scale local to each window."""
    if not len(coordinates):
        return
    windows = sliding_window_view(img, (h, w))
    bytes_per_window = h * w * np.dtype(np.float64).itemsize
    block_size = max(1, (64 * 1024**2) // (4 * bytes_per_window))
    for start in range(0, len(coordinates), block_size):
        block = coordinates[start:start + block_size]
        flat = windows[block[:, 0], block[:, 1]].reshape(len(block), -1)
        constant = np.max(flat, axis=1) == np.min(flat, axis=1)
        if local_scale:
            scales = np.max(np.abs(flat), axis=1)
            work = np.divide(flat, scales[:, None], out=np.zeros_like(flat),
                             where=scales[:, None] != 0.0)
        else:
            work = flat
        centered = work - work.mean(axis=1, keepdims=True)
        # Preserve the established flattened reduction when no extreme-range
        # local scaling is required.
        norms = np.fromiter((np.linalg.norm(row) for row in centered),
                            dtype=np.float64, count=len(block))
        numerators = (centered * t0.ravel()).sum(axis=1)
        values = np.divide(numerators, norms, out=np.zeros(len(block)),
                           where=(norms != 0.0) & ~constant)
        values[np.abs(values - 1.0) <= 8.0 * np.finfo(np.float64).eps] = 1.0
        values[np.abs(values + 1.0) <= 8.0 * np.finfo(np.float64).eps] = -1.0
        out[block[:, 0], block[:, 1]] = values


def _ncc_unstable_count(t_or_model, img):
    """Return ``(flagged, total)`` for the private exact-window fallback."""
    t = t_or_model["template"] if isinstance(t_or_model, dict) else _f(t_or_model)
    image = _f(img)
    h, w = t.shape
    if image.shape[0] < h or image.shape[1] < w:
        return 0, 0
    total = (image.shape[0] - h + 1) * (image.shape[1] - w + 1)
    if _ncc_extreme_dynamic_range(image):
        return total, total
    image, _ = _ncc_scale(image, "image")
    _, unstable = _ncc_local_variance(image, h, w)
    return int(np.count_nonzero(unstable)), int(unstable.size)


def _ncc_map(t_or_model, img):
    """Return a valid Pearson NCC map with values in ``[-1, 1]``.

    Scores are invariant to positive scaling.  Magnitudes with a binary
    exponent below -500 or above 500 (that is, below ``2**-500`` or at least
    ``2**501``) are brought near one by an exact power-of-two factor.  Images
    spanning more than 500 binary exponents instead use a scale local to each
    window.  A constant template or window, detected by exact range, scores
    0.  Every finite non-constant input self-matches within 1e-12, including
    mixed ``1e-200``/``1e200`` data.  NaN and infinity raise ``FsValueError``.

    Returns:
        A float64 array with shape ``(H-h+1, W-w+1)`` (each dimension is
        clamped at zero).  Undefined correlations from a constant template,
        a constant search image, or a constant image window are exactly 0.

    Benchmark (512x512, median of 5), sizes 7/8/9/15/16/17/31/32/33.
    Random flagged before/after: all 0/0%; seconds before
    .093743/.113507/.138235/.358469/.027835/.027368/.027780/.027232/
    .027847, after .023674/.023164/.023502/.023644/.024055/.025178/
    .024200/.024045/.024148.  DC+1e6 flagged before 93.235/95.093/
    96.472/99.643/99.735/99.847/100/100/100%, after all 0%; seconds
    before 1.128436/1.166500/1.207564/1.516455/1.180512/1.185536/
    1.347987/1.377629/1.344309, after .024393/.024236/.024131/.024865/
    .025674/.024492/.024264/.024980/.024569.  Smooth flagged before/
    after all 0/0%; seconds before .094807/.113363/.138216/.361590/
    .028206/.028148/.027105/.028454/.028040, after .024482/.023516/
    .024399/.024519/.024618/.024896/.024467/.025211/.025145.
    """
    if isinstance(t_or_model, dict):
        t = t_or_model["template"]
        t0 = t_or_model["t0n"]
        tn = float(t_or_model["norm"])
        template_is_constant = bool(t_or_model.get("constant", np.max(t) == np.min(t)))
    else:
        source_template = _f(t_or_model)
        template_is_constant = bool(
            source_template.size and np.max(source_template) == np.min(source_template)
        )
        t, _ = _ncc_scale(source_template, "template")
        t0 = t - t.mean() if not template_is_constant else np.zeros_like(t)
        tn = np.linalg.norm(t0) if not template_is_constant else 0.0
        if tn != 0.0:
            t0 = t0 / tn
    source_image = _f(img)
    if not np.isfinite(source_image).all():
        raise FsValueError("image contains NaN or infinity")
    dangerous_range = _ncc_extreme_dynamic_range(source_image)
    if dangerous_range:
        img = source_image
        image_is_constant = bool(img.size and np.max(img) == np.min(img))
    else:
        img, _, image_is_constant = _ncc_scale(source_image, "image", return_constant=True)
    H, W = img.shape
    h, w = t.shape
    shape = (max(H - h + 1, 0), max(W - w + 1, 0))
    out = np.full(shape, -1.0)
    if not out.size:
        return out
    if template_is_constant:
        out.fill(0.0)
        return out
    # Every Pearson denominator is zero for a constant search image.  Detect
    # that case before correlation and integral-image construction.
    if image_is_constant:
        out.fill(0.0)
        return out
    if dangerous_range:
        out.fill(0.0)
        coordinates = np.argwhere(np.ones(shape, dtype=bool))
        _ncc_exact_windows(out, img, t0, coordinates, h, w, local_scale=True)
        np.clip(out, -1.0, 1.0, out=out)
        return out
    # Direct correlation wins on small images.  On large images its cost is
    # quadratic in template size, and FFT is already faster for 7x7 kernels.
    method = "fft" if img.size >= 65536 or h * w > 225 else "direct"
    cross = signal.correlate(img, t0, mode="valid", method=method)
    variance, unstable = _ncc_local_variance(img, h, w)
    stable = ~unstable
    out.fill(0.0)
    out[stable] = cross[stable] / np.sqrt(variance[stable])
    # Recompute windows whose integral moments can lose their small variation
    # beside a large offset.  Process selected sliding-window views in bounded
    # blocks; patches, centered patches, and their product together stay at or
    # below a conservative 64 MiB working-set budget per block.
    coordinates = np.argwhere(unstable)
    _ncc_exact_windows(out, img, t0, coordinates, h, w)
    np.clip(out, -1.0, 1.0, out=out)
    out[np.abs(out - 1.0) <= 8.0 * np.finfo(np.float64).eps] = 1.0
    out[np.abs(out + 1.0) <= 8.0 * np.finfo(np.float64).eps] = -1.0
    return out


def create_ncc_model(template) -> dict:
    """NCC モデル(=正規化テンプレート)を準備(create_ncc_model)。

    Args:
        template: 2次元の有限値テンプレート。呼び出し元と独立した
            float64 コピーを保持する。

    Returns:
        中心化・単位ノルム化済みテンプレートと準備時の
        ``template_scale``、整数の ``template_scale_exp`` を持つモデル。
        最大絶対値の2進指数が -500 未満または 500 超、すなわち
        ``2**-500`` 未満または ``2**501`` 以上のとき、有限な正の
        2のべき乗で拡大縮小して ``norm`` を計算する。有限の非定数
        テンプレートは倍率によらず自己一致が 1（誤差 1e-12 以下）に
        なり、``1e-200`` と ``1e200`` の混在も含む。最大値と最小値が
        等しい定数テンプレートは ``constant=True``、``norm=0``、
        ``t0n`` が全ゼロとなり、すべての窓にスコア0を返す。

    Raises:
        FsValueError: ``template`` が NaN または無限大を含む場合。
    """
    source = np.asarray(template)
    t = np.array(source, dtype=np.float64, copy=True)
    constant = bool(t.size and np.max(t) == np.min(t))
    prepared, template_scale, template_scale_exp = _ncc_scale(
        t, "template", return_exponent=True
    )
    mean = float(prepared.mean())
    t0 = np.zeros_like(prepared) if constant else prepared - mean
    norm = 0.0 if constant else float(np.linalg.norm(t0))
    t0n = t0 / norm if norm != 0.0 else np.zeros_like(t0)
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
        "template_scale": template_scale,
        "template_scale_exp": template_scale_exp,
        "constant": constant,
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
        image: 探索対象の有限値2次元画像。最大値と最小値が等しい窓は
            スコア0。有限の非定数窓は倍率によらず自己一致が1（誤差
            1e-12以下）となり、``1e-200`` と ``1e200`` の混在も含む。
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
    モデルまたは画像に NaN、無限大があれば ``FsValueError`` を送出する。
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
