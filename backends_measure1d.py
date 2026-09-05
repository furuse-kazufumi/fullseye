"""1-D caliper / projection measurement along a line (image -> feature / contour).

HALCON's *measure* package fits a 1-D measure object (a line or arc) onto an image
and analyses the gray-value profile sampled along it: `measure_projection` (the
1-D projection of the measure rectangle), `measure_pos` (sub-pixel edge
positions), `measure_thresh` (profile crossings of a gray-value threshold),
`measure_pairs` (rising/falling edge pairs), and `fuzzy_measure_pos` (edges
selected by a fuzzy membership score).  This module reproduces those genuinely
and exposes them as ``m1_*`` ops.

Geometry (shared by every op):
  * The caliper line runs *edge to edge* across the image.  ``a`` sets its
    orientation ``theta = a*pi``; the line direction is ``d = (sin theta, cos
    theta)`` in (row, col) and the perpendicular is ``n = (-cos theta, sin
    theta)``.  The line passes through the image centre, shifted along ``n`` by a
    perpendicular offset.  The infinite line is clipped to the image rectangle
    (Liang-Barsky) and the visible segment is bilinearly sampled at ~1 px
    spacing, giving a 1-D intensity profile.
  * Edges along the profile are the peaks of ``|d/ds gray|`` after a small
    Gaussian smoothing (HALCON's ``Sigma``); each peak is refined to sub-pixel by
    a 3-tap parabola on the gradient magnitude, and its polarity is the sign of
    the gradient (rising = dark->bright, falling = bright->dark).

Per-op use of ``b``:
  * ``m1_measure_projection`` — ``b`` is the perpendicular *offset* (0..1, 0.5 =
    centred) of the caliper line; the op band-averages perpendicular to the line
    (the true projection) and returns the projection's mean gray value -> feature.
  * ``m1_measure_pos`` — centred line; ``b`` is the (relative) minimum edge
    amplitude.  Sub-pixel edge positions -> contour (one point per edge, in
    (row, col)); the primary result is the edge count (``count_contours``).
  * ``m1_measure_thresh`` — centred line; ``b`` is the gray-value threshold.
    Number of times the raw profile crosses level ``b`` -> feature.
  * ``m1_measure_pairs`` — centred line; ``b`` is the (relative) edge amplitude.
    Number of rising->falling edge PAIRS (bright objects) -> feature.
  * ``m1_fuzzy_measure_pos`` — centred line; each edge gets a fuzzy amplitude
    membership score in [0, 1]; edges with score >= ``b`` are kept -> contour.

Same contract as the other backend modules: ``build()`` returns typed ``Op``
wrappers, each exception-safe, deterministic and finite.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter1d, map_coordinates

_SMOOTH_SIGMA = 1.0          # profile Gaussian smoothing (HALCON "Sigma")
_MERGE_SEP = 1.5             # merge gradient peaks closer than this (px)


# --------------------------------------------------------------------------- #
# Input coercion.                                                             #
# --------------------------------------------------------------------------- #
def _as_image(v):
    """Coerce input to a 2-D float64 image in [0, 1]; None if not usable.

    Integer images are scaled by their dtype range first (uint8 -> /255, uint16 ->
    /65535, int8/int16 by their positive max; wider ints such as python-list input
    are scaled by 255 / 65535 / their max according to the data range), so a 0..255
    step is no longer clipped flat and edge-less (2026-09-02). Floats are used
    as-is and clipped to [0, 1]; bool -> {0, 1}.
    """
    arr = np.asarray(v)
    if arr.dtype == bool:
        x = arr.astype(np.float64)
    elif np.issubdtype(arr.dtype, np.integer):
        x = arr.astype(np.float64)
        if arr.dtype.itemsize <= 2:
            x /= float(np.iinfo(arr.dtype).max)
        elif x.size:
            mx = float(x.max())
            if mx > 1.0:
                x /= 255.0 if mx <= 255.0 else (65535.0 if mx <= 65535.0 else mx)
    else:
        x = np.asarray(arr, np.float64)
    if x.ndim == 3:
        x = x.mean(-1)
    if x.ndim != 2 or x.shape[0] < 2 or x.shape[1] < 2:
        return None
    x = np.nan_to_num(x, nan=0.0, posinf=1.0, neginf=0.0)
    return np.clip(x, 0.0, 1.0)


# --------------------------------------------------------------------------- #
# Line clipping and profile sampling.                                        #
# --------------------------------------------------------------------------- #
def _clip_line(c0, d, H, W):
    """Clip the infinite line ``c0 + t*d`` to [0, H-1] x [0, W-1].

    Returns (tmin, tmax) arc-length range (``d`` is unit, so ``t`` is pixels) or
    None when the line misses the image.
    """
    tmin, tmax = -np.inf, np.inf
    for pos, dd, hi in ((c0[0], d[0], H - 1), (c0[1], d[1], W - 1)):
        if abs(dd) < 1e-12:
            if pos < 0.0 or pos > hi:
                return None
        else:
            t0 = (0.0 - pos) / dd
            t1 = (hi - pos) / dd
            lo, hh = (t0, t1) if t0 <= t1 else (t1, t0)
            tmin = max(tmin, lo)
            tmax = min(tmax, hh)
    if not (np.isfinite(tmin) and np.isfinite(tmax)) or tmax <= tmin:
        return None
    return tmin, tmax


def _sample(img, a, offset01, band=0.0):
    """Sample the intensity profile along the caliper line.

    Returns a dict with the 1-D ``prof`` plus the line geometry (``c0``, ``d``,
    ``tmin``, ``ds``) so a fractional profile index maps back to (row, col), or
    None when the clipped segment is shorter than 2 px.
    """
    H, W = img.shape
    theta = float(np.clip(a, 0.0, 1.0)) * np.pi
    d = np.array([np.sin(theta), np.cos(theta)], np.float64)   # (dr, dc), unit
    n = np.array([-np.cos(theta), np.sin(theta)], np.float64)  # perpendicular
    center = np.array([(H - 1) / 2.0, (W - 1) / 2.0], np.float64)
    extent = float(min(H - 1, W - 1))
    shift = (float(np.clip(offset01, 0.0, 1.0)) - 0.5) * extent
    c0 = center + shift * n
    clip = _clip_line(c0, d, H, W)
    if clip is None:
        return None
    tmin, tmax = clip
    length = tmax - tmin
    if length < 2.0:
        return None
    N = max(2, int(round(length)) + 1)
    ts = tmin + np.linspace(0.0, length, N)
    if band <= 0.0:
        rows = c0[0] + ts * d[0]
        cols = c0[1] + ts * d[1]
        prof = map_coordinates(img, [rows, cols], order=1, mode="nearest")
    else:
        k = max(1, int(round(band)))
        ws = np.linspace(-band, band, 2 * k + 1)
        acc = np.zeros(N, np.float64)
        for w in ws:
            cc = c0 + w * n
            rows = cc[0] + ts * d[0]
            cols = cc[1] + ts * d[1]
            acc += map_coordinates(img, [rows, cols], order=1, mode="nearest")
        prof = acc / len(ws)
    prof = np.nan_to_num(np.asarray(prof, np.float64), nan=0.0, posinf=1.0, neginf=0.0)
    return {"prof": prof, "c0": c0, "d": d, "tmin": tmin, "ds": length / (N - 1)}


# --------------------------------------------------------------------------- #
# Edge extraction on the 1-D profile.                                        #
# --------------------------------------------------------------------------- #
def _merge_peaks(edges):
    """Merge gradient peaks closer than ``_MERGE_SEP`` px, keeping the strongest.

    A step sampled on the integer grid yields a two-sample gradient plateau; both
    samples parabola-refine to the same sub-pixel position, so merging collapses
    them into a single edge.
    """
    if not edges:
        return []
    edges = sorted(edges, key=lambda e: e[0])
    merged = [list(edges[0])]
    for pos, amp, sign in edges[1:]:
        if pos - merged[-1][0] < _MERGE_SEP:
            if amp > merged[-1][1]:
                merged[-1] = [pos, amp, sign]
        else:
            merged.append([pos, amp, sign])
    return [tuple(e) for e in merged]


def _profile_edges(prof):
    """Sub-pixel edges of a 1-D profile: (pos_index, amplitude, sign) list.

    ``sign`` = +1 rising (dark->bright), -1 falling (bright->dark).
    """
    p = np.asarray(prof, np.float64)
    if p.size >= 3:
        p = gaussian_filter1d(p, _SMOOTH_SIGMA, mode="nearest")
    g = np.gradient(p)
    ag = np.abs(g)
    out = []
    for i in range(1, len(ag) - 1):
        if ag[i] >= ag[i - 1] and ag[i] >= ag[i + 1] and ag[i] > 1e-9:
            den = ag[i - 1] - 2.0 * ag[i] + ag[i + 1]
            delta = 0.5 * (ag[i - 1] - ag[i + 1]) / den if abs(den) > 1e-12 else 0.0
            delta = float(np.clip(delta, -1.0, 1.0))
            out.append((i + delta, float(ag[i]), 1.0 if g[i] >= 0.0 else -1.0))
    return _merge_peaks(out)


def _index_to_rc(samp, idx):
    """Map a fractional profile index back to an (row, col) point on the line."""
    t = samp["tmin"] + idx * samp["ds"]
    r = samp["c0"][0] + t * samp["d"][0]
    c = samp["c0"][1] + t * samp["d"][1]
    return float(r), float(c)


def _points_dict(shape, pts):
    """Wrap (row, col) points as a CONTOUR dict (one 1x2 sub-contour per point)."""
    H, W = shape
    cs = []
    for r, c in pts:
        if np.isfinite(r) and np.isfinite(c):
            r = float(np.clip(r, 0.0, H - 1))
            c = float(np.clip(c, 0.0, W - 1))
            cs.append(np.array([[r, c]], np.float64))
    return {"shape": (int(H), int(W)), "cs": cs}


def _empty_contour(v):
    img = _as_image(v)
    shp = img.shape if img is not None else (1, 1)
    return {"shape": (int(shp[0]), int(shp[1])), "cs": []}


# --------------------------------------------------------------------------- #
# Module-level op functions (so tests can call them directly).               #
# --------------------------------------------------------------------------- #
def m1_measure_projection(v, a, b):
    """Mean gray value of the 1-D projection of the caliper band (feature)."""
    img = _as_image(v)
    if img is None:
        return np.float64(0.0)
    samp = _sample(img, a, b, band=1.0)   # b = perpendicular offset
    if samp is None:
        return np.float64(0.0)
    val = float(np.mean(samp["prof"]))
    if not np.isfinite(val):
        return np.float64(0.0)
    return np.float64(np.clip(val, 0.0, 1.0))


def m1_measure_pos(v, a, b):
    """Sub-pixel positions of the strongest edges along the centred line (contour)."""
    img = _as_image(v)
    if img is None:
        return _empty_contour(v)
    samp = _sample(img, a, 0.5)
    if samp is None:
        return _empty_contour(v)
    edges = _profile_edges(samp["prof"])
    if not edges:
        return _points_dict(img.shape, [])
    gmax = max(e[1] for e in edges)
    thr = max(1e-6, float(np.clip(b, 0.0, 1.0)) * gmax)
    pts = [_index_to_rc(samp, pos) for (pos, amp, _s) in edges if amp >= thr]
    return _points_dict(img.shape, pts)


def m1_measure_thresh(v, a, b):
    """Number of times the profile crosses gray-value level ``b`` (feature)."""
    img = _as_image(v)
    if img is None:
        return np.float64(0.0)
    samp = _sample(img, a, 0.5)
    if samp is None:
        return np.float64(0.0)
    level = float(np.clip(b, 0.0, 1.0))
    sgn = np.sign(samp["prof"] - level)
    nz = sgn[sgn != 0.0]
    if nz.size < 2:
        return np.float64(0.0)
    return np.float64(int(np.count_nonzero(np.diff(nz) != 0.0)))


def m1_measure_pairs(v, a, b):
    """Number of rising->falling edge pairs (bright objects) along the line (feature)."""
    img = _as_image(v)
    if img is None:
        return np.float64(0.0)
    samp = _sample(img, a, 0.5)
    if samp is None:
        return np.float64(0.0)
    edges = _profile_edges(samp["prof"])
    if len(edges) < 2:
        return np.float64(0.0)
    gmax = max(e[1] for e in edges)
    thr = max(1e-6, float(np.clip(b, 0.0, 1.0)) * gmax)
    es = [e for e in edges if e[1] >= thr]
    count = 0
    i = 0
    while i < len(es) - 1:
        if es[i][2] > 0.0 and es[i + 1][2] < 0.0:   # rising then falling
            count += 1
            i += 2
        else:
            i += 1
    return np.float64(count)


def m1_fuzzy_measure_pos(v, a, b):
    """Edges kept by a fuzzy amplitude membership score >= ``b`` (contour)."""
    img = _as_image(v)
    if img is None:
        return _empty_contour(v)
    samp = _sample(img, a, 0.5)
    if samp is None:
        return _empty_contour(v)
    edges = _profile_edges(samp["prof"])
    if not edges:
        return _points_dict(img.shape, [])
    gmax = max(e[1] for e in edges)
    if gmax <= 1e-9:
        return _points_dict(img.shape, [])
    lo = 0.05 * gmax
    thr = float(np.clip(b, 0.0, 1.0))
    pts = []
    for pos, amp, _s in edges:
        mu = float(np.clip((amp - lo) / (gmax - lo) if gmax > lo else 1.0, 0.0, 1.0))
        if mu >= thr:
            pts.append(_index_to_rc(samp, pos))
    return _points_dict(img.shape, pts)


#: 各 ``m1_*`` 関数自身には一行の docstring があるが、実際に登録される ``op.fn`` は
#: ``build()`` 内の ``_safe_feature`` / ``_safe_contour`` が返すクロージャ ``w`` で
#: あり ``__doc__`` を転記しないため、素通しでは説明が消える。ここに Japanese の
#: 説明を書き ops.py の登録ループで Op.doc に積ませる。キーは op 名。
#: 共通の幾何: キャリパー線は画像を端から端まで貫く直線で、``a`` が向き
#: （``theta = a*pi``）を振る。FEATURE を返す op はスカラー、CONTOUR を返す op は
#: ``{"shape": (H, W), "cs": [1x2 の (row, col) 配列, ...]}``（単位は入力画像の
#: ピクセル、小数値＝サブピクセル位置）。
DOCS = {
    "m1_measure_projection": (
        "測定用のキャリパー線（直線）を画像に当て、垂直方向に平均した輝度"
        "プロファイルの平均値を返す（HALCON ``measure_projection`` に相当:"
        "矩形/円弧に垂直な 1 次元射影を抽出する）。\n\n"
        "キャリパー線は画像の端から端まで引かれ、``a`` で向きを ``theta = a*pi``"
        "に振る（0＝横方向、0.5＝斜め45度、1＝横方向の逆向き）。``b`` は線を法線"
        "方向にずらす垂直オフセット（0〜1、0.5 が画像中心を通る）。線に沿って"
        "幅 1px 分の帯を平均サンプリングし（真の「射影」）、その平均輝度"
        "（[0,1]）を feature として返す。線が画像に掛からない/画像が小さすぎる"
        "場合は 0.0 を返す。"
    ),
    "m1_measure_pos": (
        "中心を通るキャリパー線上のサブピクセルエッジ位置を抽出する（HALCON"
        "``measure_pos`` に相当: 矩形/円弧に垂直な直線エッジを検出する）。\n\n"
        "線は画像中心を通り、``a`` で向きを ``theta = a*pi`` に振る。輝度"
        "プロファイルをガウシアンで軽く平滑化してから ``|d/ds gray|`` のピーク"
        "をサブピクセル（3 点放物線補間）で検出し、``b``（0〜1）を最大振幅に"
        "対する相対しきい値として弱いエッジを捨てる。戻り値は CONTOUR"
        "（``{\"shape\": (H,W), \"cs\": [1x2 の (row, col) 点, ...]}``）、座標"
        "単位は入力画像のピクセル。主な使い道はエッジ数を ``count_contours``"
        "で数えること。"
    ),
    "m1_measure_thresh": (
        "中心を通るキャリパー線上で、輝度プロファイルが指定レベルを横切った"
        "回数を数える（HALCON ``measure_thresh`` に相当: 矩形/円弧に沿って"
        "特定のグレー値を持つ点を抽出する）。\n\n"
        "``a`` は線の向き（``theta = a*pi``）、``b`` はグレー値のしきい値レベル"
        "（0〜1、そのまま）。生のプロファイル（平滑化なし）がこのレベルをまたぐ"
        "回数を feature（整数値）として返す。線が画像に掛からない場合は 0.0。"
    ),
    "m1_measure_pairs": (
        "中心を通るキャリパー線上で、立ち上がり→立ち下がりのエッジ対（明るい"
        "物体の両端）の個数を数える（HALCON ``measure_pairs`` に相当: 矩形/円弧"
        "に垂直な直線エッジのペアを抽出する）。\n\n"
        "``a`` は線の向き（``theta = a*pi``）。エッジ検出は ``m1_measure_pos``"
        "と同じ（勾配ピークのサブピクセル検出）で、``b``（0〜1）は最大振幅に"
        "対する相対しきい値。しきい値を超えたエッジを順に走査し、極性が"
        "rising→falling と並ぶ組を 1 対として数える（feature、整数値）。エッジ"
        "が 2 本未満なら 0.0。"
    ),
    "m1_fuzzy_measure_pos": (
        "中心を通るキャリパー線上のエッジを、ファジィなメンバーシップスコアで"
        "ふるいにかけて返す（HALCON ``fuzzy_measure_pos`` に相当: 矩形/円弧に"
        "垂直な直線エッジをファジィ判定で検出する）。\n\n"
        "エッジ検出は ``m1_measure_pos`` と同じ。各エッジの振幅を"
        "``(amp - lo) / (gmax - lo)``（``lo = 0.05*gmax``）で [0,1] のファジィ"
        "スコアに写像し、``b``（0〜1）以上のものだけを残す（0/1 のハードしきい値"
        "ではなく振幅に応じた連続的な信頼度で選別する点が ``measure_pos`` と"
        "違う）。``a`` は線の向き（``theta = a*pi``）。戻り値は CONTOUR、座標"
        "単位はピクセル。"
    ),
}


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    """Return the 1-D caliper measurement ops (image -> feature / contour)."""
    def _safe_feature(fn):
        def w(v, a, b):
            try:
                out = fn(v, a, b)
                val = np.float64(out)
                if not np.isfinite(val):
                    return np.float64(0.0)
                return val
            except Exception as _e:  # noqa: BLE001 - recorded, strict mode re-raises
                from backend_safe import is_strict as _bs_strict, record as _bs_record
                if _bs_strict():
                    raise
                _bs_record(None, _e, "feature")
                return np.float64(0.0)
        # ラッパは振る舞いを包むのであって説明を消してはいけない
        # (backend_safe.guard と同じ穴。同型のラッパ族が 4 つあった)。
        w.__name__ = getattr(fn, "__name__", "op")
        w.__doc__ = getattr(fn, "__doc__", None)
        return w

    def _safe_contour(fn):
        def w(v, a, b):
            try:
                out = fn(v, a, b)
            except Exception as _e:  # noqa: BLE001 - recorded, strict mode re-raises
                from backend_safe import is_strict as _bs_strict, record as _bs_record
                if _bs_strict():
                    raise
                _bs_record(None, _e, "contour")
                out = None
            if isinstance(out, dict) and "cs" in out and "shape" in out:
                return out
            return _empty_contour(v)
        # ラッパは振る舞いを包むのであって説明を消してはいけない
        # (backend_safe.guard と同じ穴。同型のラッパ族が 4 つあった)。
        w.__name__ = getattr(fn, "__name__", "op")
        w.__doc__ = getattr(fn, "__doc__", None)
        return w

    return [
        Op("m1_measure_projection", "measure1d", "measure_projection", IMAGE, FEATURE, _safe_feature(m1_measure_projection)),
        Op("m1_measure_pos", "measure1d", "measure_pos", IMAGE, CONTOUR, _safe_contour(m1_measure_pos)),
        Op("m1_measure_thresh", "measure1d", "measure_thresh", IMAGE, FEATURE, _safe_feature(m1_measure_thresh)),
        Op("m1_measure_pairs", "measure1d", "measure_pairs", IMAGE, FEATURE, _safe_feature(m1_measure_pairs)),
        Op("m1_fuzzy_measure_pos", "measure1d", "fuzzy_measure_pos", IMAGE, CONTOUR, _safe_contour(m1_fuzzy_measure_pos)),
    ]
