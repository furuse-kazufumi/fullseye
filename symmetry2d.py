# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Self-referenced symmetry measurement and inspection for 2-D images.

The five public functions deliberately exchange ordinary ``dict`` models.  This
keeps the operators on Fullseye's existing ``image2d`` / ``table`` /
``measurement`` sorts: an estimated axis or centre can be passed directly to a
difference map and then to a score without inventing a symmetry-only sort.
"""
from __future__ import annotations

import math

import numpy as np
from scipy.ndimage import map_coordinates
from scipy.optimize import minimize

from measuring1d import gen_measure_rectangle2, measure_pos

__all__ = [
    "center_from_symmetric_edges",
    "reflection_axis",
    "rotational_symmetry",
    "symmetry_difference_map",
    "symmetry_score",
]


def _image(image, name):
    a = np.asarray(image, dtype=np.float64)
    if a.ndim != 2 or min(a.shape, default=0) < 5:
        raise ValueError(f"{name}: image must be a non-empty 2-D array at least 5 x 5")
    if not np.all(np.isfinite(a)):
        raise ValueError(f"{name}: image contains NaN or infinity")
    lo, hi = float(np.min(a)), float(np.max(a))
    scale = max(1.0, abs(lo), abs(hi))
    # Relative to the signal magnitude: rounding dust in a uniform image must
    # not turn into an axis or an apparent rotational order.
    if hi - lo <= 64.0 * np.finfo(np.float64).eps * scale:
        raise ValueError(f"{name}: a constant or numerically uniform image has no measurable symmetry")
    return a, lo, hi


def _normalised(image, name):
    a, lo, hi = _image(image, name)
    return a, (a - lo) / (hi - lo), hi - lo


def _robust_location(values, mad_z):
    x = np.asarray(values, dtype=np.float64)
    if x.size < 3:
        raise ValueError("too few symmetric edge pairs")
    med = float(np.median(x))
    mad = float(np.median(np.abs(x - med)))
    floor = 64.0 * np.finfo(np.float64).eps * max(1.0, float(np.max(np.abs(x))))
    if mad <= floor:
        keep = np.abs(x - med) <= floor
    else:
        keep = np.abs(x - med) <= float(mad_z) * 1.4826 * mad
    if np.count_nonzero(keep) < 3:
        return med, int(x.size), float(mad)
    return float(np.mean(x[keep])), int(np.count_nonzero(keep)), float(mad)


def _outer_pair(image, measure, sigma, threshold, min_span):
    edges = measure_pos(image, measure, sigma=sigma, threshold=threshold, transition="all")
    if len(edges) < 2:
        return None
    first, last = edges[0], edges[-1]
    if last["pos"] - first["pos"] < min_span:
        return None
    return first, last


def center_from_symmetric_edges(image, threshold=0.08, sigma=1.0, min_span=6.0,
                                mad_z=3.5, diagonals=False):
    """対称な外側エッジ対の中点を頑健に集約し、2-D 中心を返す。

    Parameters
    ----------
    image : array-like, shape (H, W)
        グレー画像または region。各行・列のプロファイルを既存の
        :func:`measuring1d.measure_pos` でサブピクセル計測する。
    threshold : float, default 0.08
        エッジ振幅の下限。画像ダイナミックレンジに対する比で、範囲は (0, 1]。
    sigma : float, default 1.0
        1-D プロファイルを微分する前の Gaussian sigma [px]。範囲は [0, 10]。
    min_span : float, default 6.0
        採用する外側エッジ対の最小間隔 [px]。範囲は (0, min(H,W)]。
    mad_z : float, default 3.5
        中点を残す MAD 尺度。範囲は [1, 20]。
    diagonals : bool, default False
        True なら ±45 度の走査線も中心候補に加える。

    Returns
    -------
    dict
        ``center=(row,col)``、採用対数、MAD、走査方向別の中点を持つ table。

    Notes
    -----
    片側の欠けは少数の中点だけを動かすため面積重心より頑健だが、欠けのない滑らかな
    領域では全画素を使う重心の方が精密になり得る。対が 3 本未満、定数入力、対象が
    画像端で切れる場合は ``ValueError``。内部模様の最外エッジが外形より強い場合や、
    欠けが走査線の半数を超える場合は頑健集約でも救えない。

    Liu, Hel-Or, Kaplan and Van Gool, Computational Symmetry in Computer Vision
    and Computer Graphics, FnT CGV 5(1-2), 2010.
    """
    a, _, hi = _image(image, "center_from_symmetric_edges")
    lo = float(np.min(a))
    if not 0.0 < float(threshold) <= 1.0:
        raise ValueError("center_from_symmetric_edges: threshold must be in (0, 1]")
    if not 0.0 <= float(sigma) <= 10.0:
        raise ValueError("center_from_symmetric_edges: sigma must be in [0, 10]")
    if not 0.0 < float(min_span) <= min(a.shape):
        raise ValueError("center_from_symmetric_edges: min_span must be in (0, min(H,W)]")
    if not 1.0 <= float(mad_z) <= 20.0:
        raise ValueError("center_from_symmetric_edges: mad_z must be in [1, 20]")
    amp = float(threshold) * (hi - lo)
    h, w = a.shape
    xs, ys, diag_rows, diag_cols = [], [], [], []

    for row in range(h):
        m = gen_measure_rectangle2(row, (w - 1) / 2.0, 0.0, (w - 1) / 2.0, 0.0, a.shape)
        pair = _outer_pair(a, m, sigma, amp, min_span)
        if pair is not None:
            xs.append(0.5 * (pair[0]["col"] + pair[1]["col"]))
    for col in range(w):
        m = gen_measure_rectangle2((h - 1) / 2.0, col, math.pi / 2.0,
                                   (h - 1) / 2.0, 0.0, a.shape)
        pair = _outer_pair(a, m, sigma, amp, min_span)
        if pair is not None:
            ys.append(0.5 * (pair[0]["row"] + pair[1]["row"]))

    if bool(diagonals):
        length = 0.5 * math.hypot(h - 1, w - 1)
        # Parallel diagonals.  Their midpoints contribute both coordinates;
        # clipping at the image boundary is harmless because lines without two
        # object edges are rejected.
        for phi in (math.pi / 4.0, 3.0 * math.pi / 4.0):
            for off in np.linspace(-0.35, 0.35, max(9, min(h, w) // 3)):
                n = np.array([-math.sin(phi), math.cos(phi)])
                c = np.array([(h - 1) / 2.0, (w - 1) / 2.0]) + off * min(h, w) * n
                m = gen_measure_rectangle2(c[0], c[1], phi, length, 0.0, a.shape)
                pair = _outer_pair(a, m, sigma, amp, min_span)
                if pair is not None:
                    diag_rows.append(0.5 * (pair[0]["row"] + pair[1]["row"]))
                    diag_cols.append(0.5 * (pair[0]["col"] + pair[1]["col"]))

    if diag_cols:
        xs.extend(diag_cols)
        ys.extend(diag_rows)
    try:
        col, nx, mad_x = _robust_location(xs, mad_z)
        row, ny, mad_y = _robust_location(ys, mad_z)
    except ValueError as exc:
        raise ValueError("center_from_symmetric_edges: too few usable outer-edge pairs") from exc
    return {
        "kind": "center",
        "center": (row, col),
        "row": row,
        "col": col,
        "pairs_horizontal": len(xs) - len(diag_cols),
        "pairs_vertical": len(ys) - len(diag_rows),
        "pairs_diagonal": len(diag_rows),
        "pairs_kept_col": nx,
        "pairs_kept_row": ny,
        "mad_row_px": mad_y,
        "mad_col_px": mad_x,
    }


def _coordinates(shape):
    return np.indices(shape, dtype=np.float64)


def _reflect(image, angle_deg, offset_px, order=1):
    h, w = image.shape
    rr, cc = _coordinates(image.shape)
    centre = np.array([(h - 1) / 2.0, (w - 1) / 2.0])
    phi = math.radians(float(angle_deg))
    # Axis direction is (sin(phi), cos(phi)) in (row,col); n is perpendicular.
    n = np.array([-math.cos(phi), math.sin(phi)])
    d = n[0] * (rr - centre[0]) + n[1] * (cc - centre[1]) - float(offset_px)
    src_r = rr - 2.0 * d * n[0]
    src_c = cc - 2.0 * d * n[1]
    return map_coordinates(image, [src_r, src_c], order=order, mode="constant", cval=0.0)


def _rotate(image, center, angle_deg, order=1):
    rr, cc = _coordinates(image.shape)
    cr, cl = map(float, center)
    th = math.radians(float(angle_deg))
    ct, st = math.cos(th), math.sin(th)
    # Inverse map: output coordinate samples the source rotated by -theta.
    y, x = rr - cr, cc - cl
    src_r = cr + ct * y + st * x
    src_c = cl - st * y + ct * x
    return map_coordinates(image, [src_r, src_c], order=order, mode="constant", cval=0.0)


def _difference_cost(a, b):
    union = (a > 0.02) | (b > 0.02)
    if np.count_nonzero(union) < 16:
        return float("inf")
    return float(np.mean(np.abs(a[union] - b[union])))


def reflection_axis(image, angle_step=2.0, offset_search=4.0):
    """線対称な 2-D 画像から反射軸の角度とオフセットを推定する。

    Parameters
    ----------
    image : array-like, shape (H, W)
        グレー画像または region。回転済みの試験像はグレーを補間してから二値化する。
    angle_step : float, default 2.0
        粗い角度走査の刻み [degree]。範囲は [0.25, 15]。最良点は連続最適化で詰める。
    offset_search : float, default 4.0
        エッジ対中心から軸法線方向に探索する半幅 [px]。範囲は [0.5, min(H,W)/3]。

    Returns
    -------
    dict
        ``angle_deg`` は +col 軸から +row 方向へ測る [0,180) 度、``offset_px`` は
        画像中心から軸の法線方向への符号付き距離。score、2位との差 margin も返す。

    Notes
    -----
    線形補間した鏡像との正規化絶対差を最小化する。定数入力、外側エッジ対が足りない
    入力は ``ValueError``。円・正方形・回転対称と線対称を併せ持つ図形では軸が多義で、
    小さい ``margin`` がその警告になる。画像外で切れた対象や反射で等価な内部模様も
    一意な軸を保証しない。

    Liu et al., Computational Symmetry in Computer Vision and Computer Graphics,
    FnT CGV 5(1-2), 2010.
    """
    a, norm, _ = _normalised(image, "reflection_axis")
    step = float(angle_step)
    span = float(offset_search)
    if not 0.25 <= step <= 15.0:
        raise ValueError("reflection_axis: angle_step must be in [0.25, 15] degrees")
    if not 0.5 <= span <= min(a.shape) / 3.0:
        raise ValueError("reflection_axis: offset_search must be in [0.5, min(H,W)/3]")
    c = center_from_symmetric_edges(norm, threshold=0.06, sigma=1.0, min_span=4.0)["center"]
    imc = np.array([(a.shape[0] - 1) / 2.0, (a.shape[1] - 1) / 2.0])

    # Every reflection axis is a principal axis of the intensity measure (unless
    # the second moments are degenerate).  Interpolating an already rotated
    # raster can move the pixelwise-difference minimum by a few tenths of a
    # degree; the moment identity supplies an independent, subpixel invariant.
    rr, cc = _coordinates(a.shape)
    weight = np.maximum(norm, 0.0)
    mass = float(np.sum(weight))
    wr = float(np.sum(weight * rr) / mass)
    wc = float(np.sum(weight * cc) / mass)
    dy, dx = rr - wr, cc - wc
    cov = np.array([[np.sum(weight * dx * dx), np.sum(weight * dx * dy)],
                    [np.sum(weight * dx * dy), np.sum(weight * dy * dy)]]) / mass
    _, eigvec = np.linalg.eigh(cov)
    pca_candidates = []
    for k in range(2):
        v = eigvec[:, k]  # (col,row)
        ang = float(np.degrees(np.arctan2(v[1], v[0])) % 180.0)
        n = np.array([-math.cos(math.radians(ang)), math.sin(math.radians(ang))])
        off = float(np.dot(np.array([wr, wc]) - imc, n))
        pca_candidates.append((ang, off))

    def base_offset(angle):
        p = math.radians(float(angle))
        n = np.array([-math.cos(p), math.sin(p)])
        return float(np.dot(np.asarray(c) - imc, n))

    def cost(x):
        ang = float(x[0]) % 180.0
        off = float(x[1])
        return _difference_cost(norm, _reflect(norm, ang, off, order=1))

    coarse = []
    for ang in np.arange(0.0, 180.0, step):
        off0 = base_offset(ang)
        # A short offset sweep prevents an angle from losing only because the
        # robust edge centre is biased by a local defect.
        vals = [(cost((ang, off)), off) for off in np.linspace(off0 - span, off0 + span, 5)]
        val, off = min(vals)
        coarse.append((val, float(ang), float(off)))
    coarse.sort()
    refined = []
    for _, ang, off in coarse[:min(6, len(coarse))]:
        res = minimize(cost, np.array([ang, off]), method="Powell",
                       bounds=[(ang - step, ang + step), (off - span / 2.0, off + span / 2.0)],
                       options={"xtol": 1e-5, "ftol": 1e-8, "maxiter": 120})
        refined.append((float(res.fun), float(res.x[0] % 180.0), float(res.x[1])))
    refined.sort()
    best = refined[0]
    pca_scored = sorted((cost((ang, off)), ang, off) for ang, off in pca_candidates)
    # Prefer the exact second-moment invariant when it is essentially tied with
    # the resampling objective.  A material improvement remains free to move the
    # axis when a real asymmetric disturbance biases the moments.
    if pca_scored[0][0] <= best[0] * 1.10 + 1e-12:
        best = tuple(map(float, pca_scored[0]))
    runner = next((x for x in refined[1:]
                   if min(abs(x[1] - best[1]), 180.0 - abs(x[1] - best[1])) > max(1.0, step)),
                  coarse[1] if len(coarse) > 1 else best)
    phi = math.radians(best[1])
    n = np.array([-math.cos(phi), math.sin(phi)])
    point = imc + best[2] * n
    return {
        "kind": "reflection",
        "angle_deg": best[1],
        "offset_px": best[2],
        "point": (float(point[0]), float(point[1])),
        "score": best[0],
        "runner_up_score": float(runner[0]),
        "margin": float(runner[0] - best[0]),
        "interpolation": "linear",
    }


def _polar_image(image, center, radial_samples, angular_samples):
    h, w = image.shape
    cr, cc = map(float, center)
    rmax = max(2.0, min(cr, cc, h - 1 - cr, w - 1 - cc))
    radii = np.linspace(0.0, rmax, radial_samples)
    theta = np.linspace(0.0, 2.0 * math.pi, angular_samples, endpoint=False)
    rr = cr + radii[:, None] * np.sin(theta)[None, :]
    cols = cc + radii[:, None] * np.cos(theta)[None, :]
    return map_coordinates(image, [rr, cols], order=1, mode="constant", cval=0.0)


def rotational_symmetry(image, max_order=12, angular_samples=720, score_threshold=0.18):
    """180 度の点対称中心と極座標自己相関による回転対称次数を返す。

    Parameters
    ----------
    image : array-like, shape (H, W)
        グレー画像または region。
    max_order : int, default 12
        調べる最大次数。範囲は [2, 36]。
    angular_samples : int, default 720
        極座標の角度標本数。範囲は [180, 2880] で、2..max_order の公倍数を推奨。
    score_threshold : float, default 0.18
        正規化 RMS 差を対称とみなす上限。範囲は (0, 1)。

    Returns
    -------
    dict
        ``center=(row,col)``、``point_symmetric``、``order``、各次数の polar
        autocorrelation と差を持つ table。order=1 は非回転対称を表す。

    Notes
    -----
    中心は外側エッジ対から推定し、その中心で極座標画像を作る。角度方向に 360/n 度
    循環シフトした自己相関を測り、しきい値を満たす最大 n を次数とする。定数入力、中心が
    求まらない入力は ``ValueError``。同心円のように連続回転対称な像、角度標本数で割り切れ
    ない次数、中心から画像端まで対象が切れる像では次数は多義または不安定になる。

    Loy and Zelinsky, Fast radial symmetry for detecting points of interest,
    IEEE TPAMI 25(8), 2003; Liu et al., FnT CGV 5(1-2), 2010.
    """
    _, norm, _ = _normalised(image, "rotational_symmetry")
    max_order = int(max_order)
    angular_samples = int(angular_samples)
    threshold = float(score_threshold)
    if not 2 <= max_order <= 36:
        raise ValueError("rotational_symmetry: max_order must be in [2, 36]")
    if not 180 <= angular_samples <= 2880:
        raise ValueError("rotational_symmetry: angular_samples must be in [180, 2880]")
    if not 0.0 < threshold < 1.0:
        raise ValueError("rotational_symmetry: score_threshold must be in (0, 1)")
    center_model = center_from_symmetric_edges(norm, threshold=0.06, sigma=1.0, min_span=4.0)
    edge_center = center_model["center"]
    rr, cc = _coordinates(norm.shape)
    weights = np.maximum(norm, 0.0)
    mass = float(np.sum(weights))
    centroid = (float(np.sum(weights * rr) / mass), float(np.sum(weights * cc) / mass))
    radial_samples = max(32, min(256, min(norm.shape)))

    # The edge-pair centre is resistant to a local bite; the intensity centroid
    # is exact for an undisturbed odd-order (not point-symmetric) shape.  Select
    # between these two independent estimates by the best polar self-match.
    def candidate_score(candidate):
        p = _polar_image(norm, candidate, radial_samples, angular_samples)
        sd = float(np.std(p)) + 1e-15
        return min(float(np.sqrt(np.mean((p - np.roll(
            p, int(round(angular_samples / n)), axis=1)) ** 2)) / sd)
                   for n in range(2, max_order + 1))

    candidates = [edge_center]
    if math.hypot(edge_center[0] - centroid[0], edge_center[1] - centroid[1]) > 1e-6:
        candidates.append(centroid)
    center = min(candidates, key=candidate_score)
    polar = _polar_image(norm, center, radial_samples, angular_samples)
    energy = float(np.std(polar))
    if energy <= 64.0 * np.finfo(np.float64).eps:
        raise ValueError("rotational_symmetry: polar image has no measurable structure")
    scores, correlations = {}, {}
    accepted = []
    flat = polar - float(np.mean(polar))
    den = float(np.sum(flat * flat))
    for n in range(2, max_order + 1):
        shift = int(round(angular_samples / n))
        moved = np.roll(polar, shift, axis=1)
        rms = float(np.sqrt(np.mean((polar - moved) ** 2)) / (energy + 1e-15))
        corr = float(np.sum(flat * np.roll(flat, shift, axis=1)) / (den + 1e-15))
        scores[n] = rms
        correlations[n] = corr
        if rms <= threshold:
            accepted.append(n)
    order = max(accepted) if accepted else 1
    half = _rotate(norm, center, 180.0, order=1)
    point_score = float(np.sqrt(np.mean((norm - half) ** 2)) / (float(np.std(norm)) + 1e-15))
    return {
        "kind": "rotation",
        "center": (float(center[0]), float(center[1])),
        "row": float(center[0]),
        "col": float(center[1]),
        "point_symmetric": bool(point_score <= threshold),
        "point_score": point_score,
        "order": int(order),
        "symmetric": bool(order > 1),
        "order_scores": scores,
        "autocorrelation": correlations,
        "score_threshold": threshold,
        "interpolation": "linear",
    }


def _model_transform(image, symmetry):
    if not isinstance(symmetry, dict):
        raise TypeError("symmetry model must be the table returned by reflection_axis or rotational_symmetry")
    kind = symmetry.get("kind")
    if kind == "reflection":
        return _reflect(image, symmetry["angle_deg"], symmetry["offset_px"], order=1)
    if kind in ("rotation", "center"):
        center = symmetry.get("center")
        if center is None:
            raise ValueError("rotation symmetry model has no center")
        if "rotation_deg" in symmetry:
            angle = float(symmetry["rotation_deg"])
        else:
            order_n = int(symmetry.get("order", 2))
            angle = 360.0 / max(order_n, 2)
        return _rotate(image, center, angle, order=1)
    raise ValueError("symmetry model kind must be 'reflection', 'rotation', or 'center'")


def _robust_plane(residual, valid):
    rr, cc = _coordinates(residual.shape)
    keep = np.asarray(valid, dtype=bool).copy()
    if np.count_nonzero(keep) < 6:
        return np.zeros_like(residual)
    coef = np.zeros(3)
    for _ in range(4):
        x = np.column_stack([np.ones(np.count_nonzero(keep)), rr[keep], cc[keep]])
        coef = np.linalg.lstsq(x, residual[keep], rcond=None)[0]
        err = residual - (coef[0] + coef[1] * rr + coef[2] * cc)
        med = float(np.median(err[keep]))
        mad = float(np.median(np.abs(err[keep] - med)))
        if mad <= 64.0 * np.finfo(np.float64).eps * max(1.0, float(np.max(np.abs(residual)))):
            break
        keep = valid & (np.abs(err - med) <= 3.5 * 1.4826 * mad)
        if np.count_nonzero(keep) < 6:
            break
    return coef[0] + coef[1] * rr + coef[2] * cc


def symmetry_difference_map(image, symmetry, exclusion_mask=None, detrend=True):
    """推定した反射軸または回転中心に対する自己参照差分マップを返す。

    Parameters
    ----------
    image : array-like, shape (H, W)
        検査するグレー画像。
    symmetry : dict
        :func:`reflection_axis` または :func:`rotational_symmetry` の table。
    exclusion_mask : array-like or None, default None
        設計上の非対称を除外する H x W mask。True 部とその変換先をともに 0 にする。
    detrend : bool, default True
        True なら符号付き差から頑健な一次面を引き、線形な照明勾配を抑える。

    Returns
    -------
    numpy.ndarray
        ``abs(image - transformed_image)``。再標本化は線形補間で、最近傍は使わない。

    Notes
    -----
    定数入力、モデル種別不明、mask の形不一致は例外。自己参照なので欠陥は元位置と
    対称位置の対で現れ、軸上の欠陥や同じ欠陥が対称位置にもある場合は消える。一次面の
    除去は線形照明に限り、急な陰影や飽和は欠陥と区別できない。
    """
    a, _, _ = _image(image, "symmetry_difference_map")
    transformed = _model_transform(a, symmetry)
    valid = np.ones(a.shape, dtype=bool)
    if exclusion_mask is not None:
        mask = np.asarray(exclusion_mask, dtype=bool)
        if mask.shape != a.shape:
            raise ValueError("symmetry_difference_map: exclusion_mask must have image shape")
        moved_mask = _model_transform(mask.astype(np.float64), symmetry) > 0.01
        valid &= ~(mask | moved_mask)
    residual = a - transformed
    if bool(detrend):
        lo, hi = float(np.min(a)), float(np.max(a))
        # Fit illumination only where either copy contains the part.  Letting a
        # large zero background vote would force the plane to zero; subtracting
        # the plane from that background would conversely manufacture a defect.
        support = ((a - lo) > 0.02 * (hi - lo)) | ((transformed - lo) > 0.02 * (hi - lo))
        plane = _robust_plane(residual, valid & support)
        residual = np.where(support, residual - plane, residual)
    out = np.abs(residual)
    out[~valid] = 0.0
    return out


def symmetry_score(image, symmetry, exclusion_mask=None, detrend=True):
    """自己参照差分をダイナミックレンジで正規化した対称からの距離を返す。

    Parameters
    ----------
    image : array-like, shape (H, W)
        検査するグレー画像。
    symmetry : dict
        反射軸または回転中心の table。
    exclusion_mask : array-like or None, default None
        設計上の非対称を除外する mask。形は image と同じ。
    detrend : bool, default True
        線形照明差を除くなら True。

    Returns
    -------
    float
        有効画素の平均絶対差 / 画像ダイナミックレンジ。0 が完全対称で、大きいほど
        対称から遠い連続値。

    Notes
    -----
    定数・一様入力は相対床で ``ValueError``。この値は同じ画像、同じモデル、同じ mask
    の乱れを比較する量で、異なる補間床や画角の画像を一律の合否しきい値で比べない。
    軸・中心を乱れた画像自身から毎回再推定すると、推定器が欠陥へ寄って単調性を弱める。
    """
    a, _, dynamic = _normalised(image, "symmetry_score")
    diff = symmetry_difference_map(a, symmetry, exclusion_mask=exclusion_mask, detrend=detrend)
    valid = np.ones(a.shape, dtype=bool)
    if exclusion_mask is not None:
        mask = np.asarray(exclusion_mask, dtype=bool)
        moved_mask = _model_transform(mask.astype(np.float64), symmetry) > 0.01
        valid &= ~(mask | moved_mask)
    if np.count_nonzero(valid) == 0:
        raise ValueError("symmetry_score: exclusion_mask removes every pixel")
    q01, q99 = np.percentile(a[valid], [1.0, 99.0])
    robust_dynamic = float(q99 - q01)
    floor = 64.0 * np.finfo(np.float64).eps * max(1.0, abs(float(q01)), abs(float(q99)))
    denominator = robust_dynamic if robust_dynamic > floor else dynamic
    return float(np.mean(diff[valid]) / denominator)
