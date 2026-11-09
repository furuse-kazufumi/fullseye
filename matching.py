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

    空の入力(``template`` が 0 要素)は ValueError。

    Raises:
        FsValueError: ``template`` が NaN または無限大を含む場合。
    """
    source = np.asarray(template)
    if source.size == 0:
        raise ValueError("create_ncc_model: template is empty — pass at least one pixel")
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


# --- partial-overlap (masked) NCC ------------------------------------------ #
# ★2026-11-09 op 点検(g0_match high): ``ops._ncc_map`` / ``ncc_locate`` は窓が画像から
#   1 画素でもはみ出す位置を 0 にする(full-overlap のみ。cv2.matchTemplate の valid と同じ)。
#   左端で 5 % 隠れただけの対象が得点 0 になり、同形の隣(0.9987)へ黙って乗り移っていた。
#   ここでは重なった画素だけで Pearson 相関を計る(Padfield 2012 "Masked object
#   registration in the Fourier domain" の FFT 版 masked NCC)。重なりが足りない位置は
#   NaN(=調べていない)にして、得点 0(=似ていない)と区別する。

#: 窓(または重なったテンプレート部分)の分散が、全体を単位分散に正規化したうえで
#: ``_MASKED_FLAT_REL × 画素数`` 以下なら「平坦」とみなし得点 0。FFT の丸め誤差
#: (1e-16 × 画素数)より十分大きく、局所の標準偏差が全体の 1e-5 未満の窓だけが掛かる。
_MASKED_FLAT_REL = 1e-10


def _validate_min_overlap(min_overlap):
    try:
        value = float(min_overlap)
    except (TypeError, ValueError):
        raise FsValueError(f"min_overlap must be a number in (0, 1], got {min_overlap!r}") from None
    if not (np.isfinite(value) and 0.0 < value <= 1.0):
        raise FsValueError(f"min_overlap must be in (0, 1], got {min_overlap!r}")
    return value


def _validate_template_2d(template, name="template"):
    t = _f(template)
    if t.ndim != 2 or t.size == 0:
        raise FsValueError(f"{name} must be a non-empty 2-D array, got shape {t.shape}")
    if not np.isfinite(t).all():
        raise FsValueError(f"{name} contains NaN or infinity")
    return t


class _MaskedNCC:
    """One image's spectra, reused for every template of the same shape.

    The value at ``(y, x)`` is Pearson's correlation between the template and
    the template-sized window **centred** there (``ops._ncc_map``'s convention:
    the window covers rows ``y - h//2 .. y - h//2 + h - 1``), computed over the
    pixels that are inside the image, finite, and inside the template mask.
    """

    def __init__(self, image, tshape):
        from scipy import fft as sfft

        img = _f(image)
        if img.ndim != 2:
            raise FsValueError(f"image must be a 2-D array, got shape {img.shape}")
        h, w = int(tshape[0]), int(tshape[1])
        valid = np.isfinite(img)
        self.nonfinite = int(valid.size - np.count_nonzero(valid))
        vals = img[valid]
        if vals.size:
            mu = float(vals.mean())
            sd = float(np.sqrt(np.mean((vals - mu) ** 2)))
        else:
            mu, sd = 0.0, 0.0
        x = np.where(valid, img - mu, 0.0)
        if sd > 0.0 and np.isfinite(sd):
            x = x / sd                                   # 全体を単位分散へ(ゲイン不変)
        self.shape = img.shape
        self.tshape = (h, w)
        pads = ((h // 2, h - 1 - h // 2), (w // 2, w - 1 - w // 2))
        mp = np.pad(valid.astype(np.float64), pads)
        xp = np.pad(x, pads)
        self.fshape = (sfft.next_fast_len(mp.shape[0] + h - 1, real=True),
                       sfft.next_fast_len(mp.shape[1] + w - 1, real=True))
        self._sfft = sfft
        self.Fm = sfft.rfft2(mp, self.fshape)
        self.Fx = sfft.rfft2(xp, self.fshape)
        self.Fxx = sfft.rfft2(xp * xp, self.fshape)

    def _spec(self, kernel):
        return self._sfft.rfft2(kernel[::-1, ::-1], self.fshape)

    def _inv(self, Fa, G):
        h, w = self.tshape
        H, W = self.shape
        full = self._sfft.irfft2(Fa * G, self.fshape)
        return full[h - 1:h - 1 + H, w - 1:w - 1 + W]

    def score(self, template, template_mask=None, min_overlap=0.75):
        """Return ``(score_map, overlap_fraction_map)``; score NaN where overlap < min_overlap."""
        T = _f(template)
        if T.shape != self.tshape:
            raise FsValueError(f"template shape {T.shape} != prepared shape {self.tshape}")
        Mt = np.isfinite(T)
        if template_mask is not None:
            Mt &= np.asarray(template_mask, bool)
        total = int(np.count_nonzero(Mt))
        H, W = self.shape
        if total == 0:
            return np.full((H, W), np.nan), np.zeros((H, W))
        tv = T[Mt]
        tmu = float(tv.mean())
        tsd = float(np.sqrt(np.mean((tv - tmu) ** 2)))
        t = np.where(Mt, T - tmu, 0.0)
        if tsd > 0.0 and np.isfinite(tsd):
            t = t / tsd
        mt = Mt.astype(np.float64)
        Gm, Gt, Gtt = self._spec(mt), self._spec(t), self._spec(t * t)
        n = np.rint(self._inv(self.Fm, Gm))             # 重なった画素数(整数)
        s_i = self._inv(self.Fx, Gm)
        s_ii = self._inv(self.Fxx, Gm)
        s_t = self._inv(self.Fm, Gt)
        s_tt = self._inv(self.Fm, Gtt)
        s_it = self._inv(self.Fx, Gt)
        frac = n / float(total)
        nn = np.maximum(n, 1.0)
        num = s_it - s_i * s_t / nn
        v_i = s_ii - s_i * s_i / nn
        v_t = s_tt - s_t * s_t / nn
        floor = _MASKED_FLAT_REL * nn
        ok = (n >= 2.0) & (v_i > floor) & (v_t > floor)
        out = np.zeros((H, W))
        out[ok] = num[ok] / np.sqrt(v_i[ok] * v_t[ok])
        np.clip(out, -1.0, 1.0, out=out)
        out[(frac < min_overlap - 1e-12) | (n < 2.0)] = np.nan
        return out, frac


def ncc_map_partial(template, image, min_overlap: float = 0.75) -> np.ndarray:
    """**はみ出しを許す** NCC 相関マップ(重なった画素だけの Pearson 相関、masked NCC)。

    ``ops._ncc_map``(``ncc_locate`` の核)は窓が画像から 1 画素でもはみ出す位置を 0 に
    する(full-overlap のみ、``cv2.matchTemplate`` の valid と同じ)。そのため画像の縁で
    一部が切れた対象は得点 0 になり、**同形の別の対象へ黙って乗り移る**(2026-11-09 実測:
    39×39 の対象を左端から 2 px 出すと真の位置 0.9987 → 0.0、ピークは 101 px 離れた隣)。
    この関数は窓のうち画像の内側にある画素だけで相関を計るので、同じ場面で真の位置の
    得点は 0.9987〜0.9988 のまま残る。

    Args:
        template: 2 次元の有限値テンプレート(``h × w``)。
        image: 2 次元画像。**NaN / inf の画素は欠測として相関から除く**(``ops._ncc_map``
            は例外)。
        min_overlap: 調べる位置の条件。テンプレートのうち画像の内側かつ有限な画素の割合が
            これ未満の位置は **NaN**(調べていない)。``(0, 1]``。1.0 で full-overlap のみ。

    Returns:
        画像と同じ形の float64 配列。``(y, x)`` の値は、そこを **中心** とする窓
        (``ops._ncc_map`` と同じ取り決め: 行 ``y - h//2`` から ``h`` 画素)との相関で
        ``[-1, 1]``。平坦な窓・平坦なテンプレート部分は 0、重なり不足は NaN。
        full-overlap の位置では ``ops._ncc_map`` と丸め誤差(1e-9 未満)で一致する。

    ★最大値は ``np.nanargmax`` で取ること。素の ``np.argmax`` は NaN を最大とみなして
    (調べていない)位置 ``(0, 0)`` を返す(2026-11-09 独立レビュー: 縁の場面 6 通り全部で
    ``(0, 0)``・値 NaN)。位置と素性が欲しいなら ``ncc_locate_ex`` を使う。

    限界:
        重なりが小さい位置ほど相関は少ない画素で決まるので、偶然の高得点が出やすい
        (重なり 50 % なら情報は半分)。``min_overlap`` を下げすぎないこと。

    Raises:
        FsValueError: テンプレートが空・非 2 次元・非有限、画像が非 2 次元、
            ``min_overlap`` が ``(0, 1]`` の外。
    """
    t = _validate_template_2d(template)
    mo = _validate_min_overlap(min_overlap)
    score, _ = _MaskedNCC(image, t.shape).score(t, None, mo)
    return score


#: ``ncc_locate_ex`` が、欠測のせいで調べなかった位置を計り直すときの下限 =
#: ``min_overlap × _MISSING_REMEASURE_FRACTION_OF_MIN_OVERLAP``(テンプレートに対する残り画素の割合)。
#:
#: 根拠(結果を見る前に決めた理屈。2026-11-09 4 回目の独立確認で、固定値 0.5 は
#: ``min_overlap <= 0.5`` のとき計り直す集合を空にし ``missing`` を殺すと指摘された):
#: 計り直しは「呼び出し側が通常の探索に要求した画素数(``min_overlap``)」の **半分以上** で
#: 行う。偶然の相関の広がりは残り画素数 n に対して ~1/sqrt(n) なので、半分の画素なら通常の
#: 探索の sqrt(2) ≒ 1.41 倍までに収まる —— 「通常の探索と同じ桁の信頼度」と言える最も緩い
#: 切りのよい値として 1/2 を置いた。画素の独立と、位置の数による多重比較は考えていない
#: 経験的な目安である(平滑化した画像では実効的な画素数はもっと少ない)。下限は ``min_overlap`` に連動するので、``min_overlap`` が
#: いくつでも計り直す集合(下限以上・``min_overlap`` 未満)は空にならない。
#: 下限より少ない残りしか無い位置は **捨てない**: 残り 2 画素以上なら計り直し、最良 −
#: ambiguity に届けば補足の弱い印 ``missing_low_overlap`` を立てる。
_MISSING_REMEASURE_FRACTION_OF_MIN_OVERLAP = 0.5


def ncc_locate_ex(template, image, min_overlap: float = 0.75, ambiguity: float = 0.01) -> dict:
    """``ncc_locate`` の **縁と欠測を区別する** 版。最良位置と、その答えの素性を返す。

    ``ops._ncc_locate`` は ``[得点, 行, 列]`` だけを返し、「縁ではみ出したので調べなかった」
    「NaN を含む画像」「見つからない」が区別できない。ここでは ``ncc_map_partial`` の
    マップから最良位置を取り、次を一緒に返す。

    Returns:
        dict:
          - ``score``: 最良位置の相関(``[-1, 1]``)。調べた位置が無ければ NaN。
          - ``row`` / ``col`` / ``column``: テンプレート **中心** の画素座標(``ncc_locate`` と
            同じ取り決め)。調べた位置が無ければ -1。
          - ``overlap``: 最良位置でテンプレートが画像の内側(かつ有限画素)に重なった割合。
          - ``geometric_overlap``: 最良位置で窓が画像の内側に入る割合(欠測を無視)。
          - ``full_overlap``: ``overlap == 1``(= ``ncc_locate`` でも調べられる位置)。
          - ``second_score`` / ``margin``: 最良位置の周り(テンプレートの大きさの矩形)を
            除いた 2 番目の得点と、その差(突出度)。無ければ NaN。
          - ``unsearched_fraction``: 重なり不足で調べなかった位置の割合。
          - ``rescanned_low_overlap_positions``: 欠測のせいで調べなかった位置のうち、残りが
            下限未満で 2 画素以上ある、弱い印のために **計り直した** 位置の数。残り 0〜1 画素の位置は
            相関が定義できないので数えない。
          - ``nonfinite_pixels``: 欠測として除いた画像の画素数。
          - ``flags``: 答えの素性の印(複数可、重い順):
            ``"unsearched"``(調べられる位置が 1 つも無い)/ ``"flat"``(調べた位置が
            すべて平坦で得点 0)/ ``"missing"``(欠測画素のせいで調べられなかった位置の
            うち、**欠測を除いた部分の相関が最良の得点 − ``ambiguity`` 以上** のものがある
            = 答えが変わりえた。隅の 1 画素の欠測のように判断に効かないものでは立たない。
            計り直すのは、残り画素の割合が ``min_overlap / 2`` 以上の位置だけ —— それより
            少ない位置は偶然の相関で届きうるので、強い印には数えない)/
            ``"window_missing"``(最良位置の窓の中に欠測画素がある)/ ``"ambiguous"``
            (2 位との差 ``margin`` が ``ambiguity`` 未満 = 同形の別物体と区別できない)/
            ``"border"``(最良位置で窓が **幾何的に** 画像からはみ出している。欠測とは別)/
            ``"missing_low_overlap"``(**補足の弱い印、常に最後**: 欠測のせいで調べなかった
            位置のうち、残りが ``min_overlap / 2`` 未満で強い印には数えなかった位置を、残り
            2 画素以上のものだけ計り直し、最良 − ``ambiguity`` に届いたものがある。残りが
            少ないので偶然の一致もありうる —— 「真の対象がそこにあったかもしれない」という
            疑い。残り 2 画素の位置では相関が定義上 ±1 になるので、欠測が 95 % を超える
            画像ではこの印がほぼ常に立つ。ほかの印があれば ``status`` はそちらになり、この
            印しか無いときだけ ``status`` になる(= 立てば ``ok`` にはならない))。
          - ``status``: ``flags`` の先頭、無ければ ``"ok"``。``"ok"`` は「縁にも欠測にも
            掛からず、2 位と ``ambiguity`` 以上の差で決まった」ことだけを言う(正しさの保証
            ではない)。
          - ``min_overlap`` / ``ambiguity``: 使った条件。

    Raises:
        FsValueError: ``ncc_map_partial`` と同じ。
    """
    t = _validate_template_2d(template)
    mo = _validate_min_overlap(min_overlap)
    amb = float(ambiguity)
    if not (np.isfinite(amb) and amb >= 0.0):
        raise FsValueError(f"ambiguity must be a finite number >= 0, got {ambiguity!r}")
    engine = _MaskedNCC(image, t.shape)
    score, frac = engine.score(t, None, mo)
    searched = np.isfinite(score)
    out = {"min_overlap": mo, "ambiguity": amb, "nonfinite_pixels": engine.nonfinite,
           "unsearched_fraction": float(1.0 - searched.mean()) if score.size else 1.0}
    if not searched.any():
        out.update(score=float("nan"), row=-1, col=-1, column=-1, overlap=0.0,
                   full_overlap=False, second_score=float("nan"),
                   margin=float("nan"), rescanned_low_overlap_positions=0,
                   flags=["unsearched"], status="unsearched")
        return out
    # 幾何だけで決まる重なり率(欠測を無視)。これで足りるのに調べていない位置 = 欠測のせい
    H, W = score.shape
    h, w = t.shape
    ys = np.arange(H)[:, None] - h // 2 + np.arange(h)[None, :]
    xs = np.arange(W)[:, None] - w // 2 + np.arange(w)[None, :]
    geo = (np.outer(((ys >= 0) & (ys < H)).sum(1), ((xs >= 0) & (xs < W)).sum(1))
           / float(h * w))
    lost = (geo >= mo - 1e-12) & ~searched               # 欠測のせいで調べなかった位置
    filled = np.where(searched, score, -np.inf)
    r, c = np.unravel_index(int(np.argmax(filled)), filled.shape)
    best = float(score[r, c])
    h, w = t.shape
    rest = filled.copy()
    rest[max(0, r - h // 2):r + h // 2 + 1, max(0, c - w // 2):c + w // 2 + 1] = -np.inf
    second = float(rest.max()) if np.isfinite(rest).any() else float("nan")
    flat = bool(np.all(score[searched] == 0.0))
    margin = float(best - second) if np.isfinite(second) else float("nan")
    full = bool(frac[r, c] >= 1.0)
    geo_rc = float(geo[r, c])
    # ★2026-11-09 2 回目の独立レビュー: border は幾何の重なりで判定する(以前は有限画素の割合
    #   frac < 1 だったので、内側の NaN 1 画素を「縁ではみ出した」と誤ラベルした)。
    #   missing は判断に効く欠測だけ: 調べなかった位置を、欠測を除いた残りの画素で計って
    #   最良 − ambiguity に届くものがあるときに限る。★3〜4 回目の確認: 残る画素が少ないと
    #   偶然の相関で届いてしまうので、計り直しは残りが min_overlap / 2 以上の位置だけ
    #   (下限の根拠は _MISSING_REMEASURE_FRACTION_OF_MIN_OVERLAP)。下限未満の位置は捨てず、
    #   判定できなかったことを missing_low_overlap で返す。
    missing = False
    low_overlap = False
    n_rescanned_low = 0
    if lost.any():
        floor = mo * _MISSING_REMEASURE_FRACTION_OF_MIN_OVERLAP
        loose, remaining = engine.score(t, None, floor)
        judgeable = lost & (remaining >= floor - 1e-12) & np.isfinite(loose)
        missing = bool(np.any(loose[judgeable] >= best - amb))
        # 下限未満の位置は捨てない。ただし相関が定義できる位置(残り 2 画素以上)だけを計り、
        # 最良 − ambiguity に届くものがあるときだけ弱い印を立てる(★5 回目の確認: 残り 0 の
        # 位置まで数えると、欠測の多い画像では答えが正しくてもほぼ常に立ち、印の意味が無かった)。
        below, _ = engine.score(t, None, 1e-12)              # 残り 2 画素以上で有限
        weak = lost & ~judgeable & np.isfinite(below)
        n_rescanned_low = int(np.count_nonzero(weak))
        low_overlap = bool(np.any(below[weak] >= best - amb))
    flags = []
    if flat:
        flags.append("flat")
    if missing:
        flags.append("missing")
    if frac[r, c] < geo_rc - 1e-12:
        flags.append("window_missing")
    if np.isfinite(margin) and margin < amb and not flat:
        flags.append("ambiguous")
    if geo_rc < 1.0:
        flags.append("border")
    # 補足の弱い印は最後(★5 回目の確認: 前に置くと status が ambiguous などを隠した)。
    # ほかに印が無いときだけ status になる(= 立てば status は ok にならない)。
    if low_overlap:
        flags.append("missing_low_overlap")
    out.update(score=best, row=int(r), col=int(c), column=int(c),
               rescanned_low_overlap_positions=n_rescanned_low,
               overlap=float(frac[r, c]), geometric_overlap=geo_rc, full_overlap=full,
               second_score=second, margin=margin,
               flags=flags, status=flags[0] if flags else "ok")
    return out


def _rotated_template(template, angle_deg):
    """Rotate ``template`` about its centre (``reshape=False``) and return ``(T_rot, mask)``.

    ★2026-11-09 op 点検(g0_match med): 以前の ``shape_locate`` は
    ``ndimage.rotate(T, ang, reshape=False)`` の四隅(cval=0)もテンプレートとして相関を
    取ったので、背景が 0 でない画像では正しい角度でも得点が構造的に下がった(背景 0.5・
    30° 回転で 0.7794)。ここでは四隅を **マスクで除く**: 値は ``mode="nearest"`` で回して
    縁を 0 と混ぜず、マスクは線形補間で全部が内側から来た画素(値 1)だけにする。
    """
    from scipy import ndimage

    T = _f(template)
    if float(angle_deg) % 360.0 == 0.0:
        return T.copy(), np.ones(T.shape, bool)
    rot = ndimage.rotate(T, float(angle_deg), reshape=False, order=3, mode="nearest")
    m = ndimage.rotate(np.ones(T.shape), float(angle_deg), reshape=False, order=1,
                       mode="constant", cval=0.0)
    return rot, m >= 1.0 - 1e-9


def _inscribed_disc(shape):
    """Pixels within the disc inscribed in a ``shape`` rectangle (rotation-invariant support)."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w]
    r = 0.5 * min(h, w)
    return (yy - (h - 1) / 2.0) ** 2 + (xx - (w - 1) / 2.0) ** 2 <= r * r


def _shape_scores(engine, template, angle_deg, support=None):
    """Full-overlap masked NCC map of the rotated template (0 where not searched).

    ``support`` (bool, template shape) further restricts the template pixels; ``None``
    uses every pixel that the rotation keeps inside (the corners are dropped).
    """
    rot, mask = _rotated_template(template, angle_deg)
    if support is not None:
        mask = mask & support
    score, _ = engine.score(rot, mask, 1.0)
    return np.nan_to_num(score, nan=0.0)


def shape_locate_fine(template, image, step_deg: float = 5.0, refine: bool = True,
                      angle_range=(0.0, 360.0)) -> dict:
    """回転を探すテンプレート照合の **刻み指定+副刻み** 版(``shape_locate`` の 30° 固定の代わり)。

    ``ops._shape_locate``(契約 op)は 0°〜330° を 30° 刻みで探すので、15° 回転した対象には
    角度 0 を返した(2026-11-09 実測)。ここでは ``angle_range`` を ``step_deg`` で粗く探し、
    ``refine=True`` なら最良角度の両隣の得点に放物線を当てて角度を刻みの内側へ詰め、その
    角度で位置を取り直す(詰めた結果の得点が粗探索より下がったら粗探索の答えを残す)。
    相関を取るのは **テンプレートの内接円の画素だけ**(全角度で同じ画素集合。角度ごとに
    四隅の抜け方が違うと、画素の少ない角度ほど得点が上がる偏りが出る)。そのため角度 0
    の得点は ``ncc_locate``(正方形全体)と一致しない。調べるのは内接円が画像の内側に
    全部入る位置だけ。

    角度の向きは ``scipy.ndimage.rotate`` と同じ(``shape_locate`` と同じ取り決め)。

    限界: 位置は整数画素で探すので、対象が副画素ずれていると **回転がそのずれを
    肩代わりして** 小さい角度の得点が 0° より高くなることがある(2026-11-09、
    poc_template_tracking の回っていない対象: 0° 0.866 / 3° 0.929 → 355.5° を返した。
    位置誤差は 0.10 px)。数度以下の角度は、この関数の答えをそのまま信じないこと。

    Returns:
        dict: ``score``(``[-1, 1]``)、``row`` / ``col`` / ``column``(テンプレート中心)、
        ``angle_deg``(副刻みの角度)、``coarse_angle_deg``(刻みの上の最良角度)—— どちらも
        **[0, 360) に正規化** —、``step_deg``。刻みが 360 を割り切らなくても、範囲の端の
        隣は ``ang ± step`` を評価し直して詰める。
        調べられる位置が無いときは ``score`` NaN・座標 -1。

    Raises:
        FsValueError: テンプレートが空・非 2 次元・非有限、画像が非 2 次元または非有限、
            ``step_deg`` が正の有限値でない、``angle_range`` が ``lo < hi`` の有限値でない。
    """
    t = _validate_template_2d(template)
    img = _f(image)
    if img.ndim != 2:
        raise FsValueError(f"image must be a 2-D array, got shape {img.shape}")
    if not np.isfinite(img).all():
        raise FsValueError("image contains NaN or infinity")
    step = float(step_deg)
    if not (np.isfinite(step) and 0.0 < step <= 360.0):
        raise FsValueError(f"step_deg must be in (0, 360], got {step_deg!r}")
    lo, hi = (float(a) for a in angle_range)
    if not (np.isfinite(lo) and np.isfinite(hi) and lo < hi):
        raise FsValueError(f"angle_range must be finite with lo < hi, got {angle_range!r}")
    angles = np.arange(lo, hi, step)
    engine = _MaskedNCC(img, t.shape)
    # 角度ごとに相関を取る画素の集合を変えると、画素数の少ない角度ほど(隅の合わない画素が
    # 抜けるぶん)得点が上がり、回っていない対象に 4° を返した(2026-11-09 実測)。
    # 全角度で同じ画素集合 = 内接円で比べる。
    disc = _inscribed_disc(t.shape)
    best_scores, best_pos = [], []
    for ang in angles:
        m = _shape_scores(engine, t, ang, disc)
        k = int(np.argmax(m))
        best_scores.append(float(m.flat[k]))
        best_pos.append(np.unravel_index(k, m.shape))
    if not best_scores:
        return {"score": float("nan"), "row": -1, "col": -1, "column": -1,
                "angle_deg": float("nan"), "coarse_angle_deg": float("nan"), "step_deg": step}
    k = int(np.argmax(best_scores))
    score, (r, c), ang = best_scores[k], best_pos[k], float(angles[k])
    result = {"score": score, "row": int(r), "col": int(c), "column": int(c),
              "angle_deg": ang, "coarse_angle_deg": ang, "step_deg": step}
    # 両隣の得点。範囲内なら粗探索の値を使い、範囲の端では(全周のときだけ)隣を
    # **実際に ang ± step で評価し直す**。★2026-11-09 独立レビュー: 以前は全周なら周期の
    # 隣(angles[-1] / angles[0])を借りたが、刻みが 360 を割り切らないとその隣は step だけ
    # 離れておらず、0° 付近の詰めが壊れた(step 7 で真値 +2° → 0.00°)。
    full_circle = abs((hi - lo) - 360.0) < 1e-9

    def _neighbour(idx, delta):
        j = idx + delta
        if 0 <= j < len(angles):
            return best_scores[j]
        if not full_circle:
            return None
        m_n = _shape_scores(engine, t, ang + delta * step, disc)
        return float(m_n.max())

    if refine and len(angles) >= 2:
        before, after = _neighbour(k, -1), _neighbour(k, +1)
        if before is not None and after is not None:
            off = _parabolic_offset(before, score, after)
            if off != 0.0:
                ang_f = ang + off * step
                m = _shape_scores(engine, t, ang_f, disc)
                j = int(np.argmax(m))
                if float(m.flat[j]) >= score:
                    rr, cc = np.unravel_index(j, m.shape)
                    result.update(score=float(m.flat[j]), row=int(rr), col=int(cc),
                                  column=int(cc), angle_deg=float(ang_f))
    # 返す角度は [0, 360) にそろえる(以前は -1.11° と 355.63° が混在した)
    for key in ("angle_deg", "coarse_angle_deg"):
        a_n = float(result[key]) % 360.0
        result[key] = 0.0 if a_n >= 360.0 - 1e-12 else a_n
    return result
