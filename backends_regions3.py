"""Binary-region operators, round 3 (registry tier, prefix ``r3_``).

Genuine region-processing operators over binary region masks, each implementing the
algorithm named by a real, previously-uncovered HALCON operator (verified against
``data/halcon_graph.json``: every non-empty ``halcon`` name below has ``covered =
False`` there).  Every op is a module-level ``fn(v, a, b)`` so tests can call it
directly; the tier is assembled by :func:`build`, which the caller wires into the op
registry.  ``build`` wraps each fn in a sort-aware, exception-safe guard so a fn can
never raise into the registry and always returns a contract-valid result.

Region contract: input/return is a 2-D float64 mask (0/1) in [0,1] with the SAME shape
as the input; feature ops return a finite scalar float64.  All fns are deterministic
and fail-soft on empty / const / tiny / malformed input (never raise).

Honesty notes
-------------
* ``r3_rank_region`` implements the GENUINE HALCON ``rank_region`` — a *morphological
  rank operator* (a pixel is set iff at least ``number`` of the pixels in a
  ``width x height`` window belong to the region; ``number = w*h`` => erosion,
  ``number = 1`` => dilation).  This deliberately differs from a "keep the k-th
  component by area" reading, which would neither match ``rank_region`` nor add new
  coverage (that behaviour is already the ``sort_region`` op in ``backends_regions2``).
* ``r3_polar_trans_region`` returns a REGION (per the real operator's ``-> HObject``
  return), even though the graph's ``sort_out_hint`` heuristically says "feature".
* ``r3_region_features`` / ``r3_runlength_distribution`` return a single scalar because
  the FEATURE sort is scalar; they compute a genuine member of the operator's output
  (a shape feature; a summary of the run-length distribution).  Same modelling choice
  as ``r2_runlength_features`` in the sibling tier.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

# HALCON operators intentionally NOT implemented in this tier (with honest reason).
SKIPPED: dict[str, str] = {}


# --------------------------------------------------------------------------- #
# shared helpers
# --------------------------------------------------------------------------- #
def _as_mask(v) -> np.ndarray:
    """Coerce any region-ish input to a 2-D boolean foreground mask (fail-soft)."""
    a = np.asarray(v, dtype=np.float64)
    if a.ndim == 0:
        a = a.reshape(1, 1)
    elif a.ndim == 1:
        a = a.reshape(1, -1)
    elif a.ndim > 2:
        a = a.reshape(a.shape[0], -1)
    return np.isfinite(a) & (a > 0.5)


def _as_gray(v, clip: bool = True) -> np.ndarray:
    """Coerce input to a finite 2-D float64 array (fail-soft).

    ``clip`` squashes the result into [0,1], which is right for intensity ops but
    destroys a label image: every label >= 1 collapses onto 1.0 and becomes one
    blob.  Label-reading ops pass ``clip=False`` to keep the label values apart.
    """
    a = np.asarray(v, dtype=np.float64)
    if a.ndim == 0:
        a = a.reshape(1, 1)
    elif a.ndim == 1:
        a = a.reshape(1, -1)
    elif a.ndim > 2:
        a = a.reshape(a.shape[0], -1)
    a = np.nan_to_num(a, nan=0.0, posinf=1.0, neginf=0.0)
    return np.clip(a, 0.0, 1.0) if clip else a


def _clip01(a: np.ndarray) -> np.ndarray:
    return np.clip(np.nan_to_num(a, nan=0.0, posinf=1.0, neginf=0.0), 0.0, 1.0)


def _knob(x) -> float:
    try:
        x = float(x)
    except (TypeError, ValueError):
        return 0.5
    if not np.isfinite(x):
        return 0.5
    return min(1.0, max(0.0, x))


def _row_runs(row: np.ndarray):
    """Return (starts, lengths) of maximal True runs in a 1-D boolean row."""
    padded = np.concatenate(([0], row.astype(np.int8), [0]))
    d = np.diff(padded)
    starts = np.where(d == 1)[0]
    ends = np.where(d == -1)[0]
    return starts, ends - starts


def _all_run_lengths(m: np.ndarray) -> np.ndarray:
    """All horizontal foreground run lengths across every row of ``m`` (bool)."""
    lengths: list[int] = []
    for row in m:
        if row.any():
            _, lens = _row_runs(row)
            lengths.extend(lens.tolist())
    return np.asarray(lengths, dtype=np.float64)


# --------------------------------------------------------------------------- #
# operators
# --------------------------------------------------------------------------- #
def r3_background_seg(v, a, b):
    """Connected components of the background of the region (HALCON background_seg).

    The background is the complement of the foreground; its connected components are
    labelled and returned as a mask.  ``a`` acts as a relative area filter: components
    smaller than ``a * (largest background component)`` are dropped (``a = 0`` returns
    the full background, i.e. the exact ``background_seg`` result).
    """
    m = _as_mask(v)
    bg = ~m
    out = np.zeros(m.shape, np.float64)
    lab, n = ndimage.label(bg)
    if n == 0:
        return out
    sizes = ndimage.sum(np.ones_like(lab, dtype=np.float64), lab,
                        index=np.arange(1, n + 1))
    thresh = _knob(a) * float(sizes.max())
    keep = np.zeros(m.shape, dtype=bool)
    for i, s in enumerate(sizes, start=1):
        if s >= thresh:
            keep |= (lab == i)
    out[keep] = 1.0
    return _clip01(out)


def r3_clip_region(v, a, b):
    """Clip the region to a central rectangle (HALCON clip_region).

    ``a`` = kept fraction of the height, ``b`` = kept fraction of the width; the window
    is centred.  Region pixels outside the window are removed.
    """
    m = _as_mask(v)
    h, w = m.shape
    wh = max(1, int(round(_knob(a) * h)))
    ww = max(1, int(round(_knob(b) * w)))
    r0 = (h - wh) // 2
    c0 = (w - ww) // 2
    out = np.zeros(m.shape, np.float64)
    out[r0:r0 + wh, c0:c0 + ww] = m[r0:r0 + wh, c0:c0 + ww].astype(np.float64)
    return _clip01(out)


def r3_eliminate_runs(v, a, b):
    """Remove horizontal foreground runs shorter than a threshold (eliminate_runs).

    A pixel survives only if it belongs to a horizontal run of length ``>= min_len``,
    where ``min_len = 1 + max(1, round(a*8))`` (a small pixel count).  Thin one-pixel
    bridges (runs of length 1) are severed at ``a = 0`` (min_len = 2).
    """
    m = _as_mask(v)
    out = np.zeros(m.shape, np.float64)
    if not m.any():
        return out
    min_len = 1 + max(1, int(round(_knob(a) * 8)))
    for i, row in enumerate(m):
        if not row.any():
            continue
        starts, lens = _row_runs(row)
        for s, ln in zip(starts, lens):
            if ln >= min_len:
                out[i, s:s + ln] = 1.0
    return _clip01(out)


def r3_rank_region(v, a, b):
    """Morphological rank operator over the region (GENUINE HALCON rank_region).

    A pixel is set iff at least ``number`` of the pixels in a ``sz x sz`` window belong
    to the region.  ``sz`` (odd, 3..7) comes from ``a``; ``number`` from ``b`` as a
    fraction of the window area (>= 1).  ``number = sz*sz`` => erosion, ``number = 1``
    => dilation, intermediate => rank/median filtering.
    """
    m = _as_mask(v).astype(np.int64)
    sz = 1 + 2 * max(1, int(round(_knob(a) * 3)))          # 3,5,7
    area = sz * sz
    number = int(round(_knob(b) * area))
    number = min(area, max(1, number))
    kernel = np.ones((sz, sz), dtype=np.int64)
    count = ndimage.convolve(m, kernel, mode="constant", cval=0)
    return _clip01((count >= number).astype(np.float64))


def r3_region_features(v, a, b):
    """Region -> feature: a genuine HALCON shape feature (region_features).

    ``a < 0.5`` returns the normalised area (foreground fraction); ``a >= 0.5`` returns
    the compactness ``P^2 / (4*pi*A)`` (== 1 for an ideal disk, 16/(4*pi) ~ 1.273 for a
    square, and grows with elongation), where ``P`` is the 4-connected edge perimeter.
    """
    m = _as_mask(v)
    area = float(m.sum())
    if area == 0.0:
        return np.float64(0.0)
    if _knob(a) < 0.5:
        return np.float64(area / float(m.size))
    lost = float(np.sum(m[:, 1:] & m[:, :-1]) + np.sum(m[1:, :] & m[:-1, :]))
    perim = 4.0 * area - 2.0 * lost
    comp = (perim * perim) / (4.0 * np.pi * area)
    return np.float64(comp if np.isfinite(comp) else 0.0)


def r3_runlength_distribution(v, a, b):
    """Region -> feature: summary of the horizontal run-length distribution.

    ``a < 0.5`` returns the (population) variance of run lengths; ``a >= 0.5`` returns
    the Shannon entropy (bits) of the run-length histogram.  Both are genuine scalar
    summaries of the distribution produced by HALCON runlength_distribution.
    """
    m = _as_mask(v)
    lengths = _all_run_lengths(m)
    if lengths.size == 0:
        return np.float64(0.0)
    if _knob(a) < 0.5:
        return np.float64(float(np.var(lengths)))
    _, counts = np.unique(lengths, return_counts=True)
    p = counts.astype(np.float64) / float(counts.sum())
    ent = -float(np.sum(p * np.log2(p)))
    return np.float64(ent if np.isfinite(ent) else 0.0)


def r3_select_region_point(v, a, b):
    """Keep the connected component containing the point at (a*H, b*W) (select_region_point).

    If the addressed pixel is background, the result is empty.
    """
    m = _as_mask(v)
    out = np.zeros(m.shape, np.float64)
    h, w = m.shape
    r = min(h - 1, max(0, int(round(_knob(a) * (h - 1)))))
    c = min(w - 1, max(0, int(round(_knob(b) * (w - 1)))))
    lab, n = ndimage.label(m)
    if n == 0:
        return out
    lv = int(lab[r, c])
    if lv > 0:
        out[lab == lv] = 1.0
    return _clip01(out)


def r3_partition_dynamic(v, a, b):
    """Partition the region horizontally at columns of small vertical extent (partition_dynamic).

    Columns whose foreground density is positive but ``<= a * max_density`` are treated
    as necks and cleared, splitting the region there.  A region of uniform density has
    no such columns and is returned unchanged.
    """
    m = _as_mask(v)
    out = m.astype(np.float64).copy()
    if not m.any():
        return np.zeros(m.shape, np.float64)
    density = m.sum(axis=0).astype(np.float64)
    cols = np.where(density > 0)[0]
    c0, c1 = int(cols.min()), int(cols.max())
    maxd = float(density[c0:c1 + 1].max())
    thresh = _knob(a) * maxd
    interior = np.arange(c0 + 1, c1)                       # never cut the two ends
    for j in interior:
        if 0.0 < density[j] <= thresh:
            out[:, j] = 0.0
    return _clip01(out)


def r3_polar_trans_region(v, a, b):
    """Polar remap of the region about its centroid (polar_trans_region).

    Output rows are the radial axis (0..``rmax``), output columns the angular axis
    (0..``angle_end``).  ``a`` scales the radial extent, ``b`` the angular sweep.  Output
    keeps the input shape.  Nearest-neighbour sampling.
    """
    m = _as_mask(v)
    out = np.zeros(m.shape, np.float64)
    if not m.any():
        return out
    h, w = m.shape
    ys, xs = np.where(m)
    cy = float(ys.mean())
    cx = float(xs.mean())
    rmax = float(np.sqrt((((ys - cy) ** 2) + ((xs - cx) ** 2)).max())) * (0.25 + 0.75 * _knob(a))
    angle_end = 2.0 * np.pi * (0.25 + 0.75 * _knob(b))
    ii, jj = np.mgrid[0:h, 0:w].astype(np.float64)
    r = rmax * ii / max(h - 1, 1)
    th = angle_end * jj / max(w - 1, 1)
    sr = np.rint(cy - r * np.sin(th)).astype(np.int64)
    sc = np.rint(cx + r * np.cos(th)).astype(np.int64)
    ok = (sr >= 0) & (sr < h) & (sc >= 0) & (sc < w)
    vals = np.zeros(m.shape, dtype=bool)
    vals[ok] = m[sr[ok], sc[ok]]
    out[vals] = 1.0
    return _clip01(out)


def r3_label_to_region(v, a, b):
    """Extract the region of pixels sharing one gray value from a label image (label_to_region).

    Distinct positive gray values (rounded to 3 decimals) are the labels, sorted
    ascending; the label at index ``round(a * maxlabel)`` is selected and its pixels are
    returned as a mask.  A plain 0/1 mask has a single label and yields its foreground.
    """
    arr = _as_gray(v, clip=False)
    q = np.round(arr, 3)
    levels = np.unique(q[q > 0.0])
    out = np.zeros(arr.shape, np.float64)
    if levels.size == 0:
        return out
    k = min(levels.size - 1, max(0, int(round(_knob(a) * (levels.size - 1)))))
    target = float(levels[k])
    out[q == target] = 1.0
    return _clip01(out)


# --------------------------------------------------------------------------- #
# op descriptions (module-level DOCS table)
# --------------------------------------------------------------------------- #
#: 各 ``r3_*`` 関数自身には docstring があるが、実際に登録される ``op.fn`` は
#: ``build()`` 内の ``_wrap`` が返すクロージャ ``inner`` であり、``__doc__`` を
#: 転記していないため素通しでは説明が消える（``backend_safe.guard`` が 82 本で
#: 踏んだのと同じ穴）。qualname が ``<lambda>`` を含まなくても症状は同じなので、
#: ここに Japanese の説明を書き ops.py の登録ループで Op.doc に積ませる。
#: キーは op 名。
DOCS = {
    "r3_background_seg": (
        "領域の背景（前景の補集合）を連結成分に分け、小さすぎる成分を捨てて返す"
        "（HALCON ``background_seg`` に相当）。\n\n"
        "背景を連結成分ラベリングし、``a``（0〜1）を「最大背景成分の面積に対する"
        "相対しきい値」としてそれ未満の成分を除去する（``a=0`` で全背景＝正真正銘の"
        "``background_seg`` 結果）。``b`` は未使用。"
    ),
    "r3_clip_region": (
        "領域を画像中心の矩形窓でクリップする（HALCON ``clip_region`` に相当）。\n\n"
        "``a`` は残す高さの割合（0〜1）、``b`` は残す幅の割合（0〜1）。窓は画像の"
        "中心に置かれ、窓の外側の領域画素はすべて消される。"
    ),
    "r3_eliminate_runs": (
        "水平方向の連結ラン（連続する前景画素の並び）のうち、指定長未満のものを"
        "消す（HALCON ``eliminate_runs`` に相当）。\n\n"
        "``a``（0〜1）から最小ラン長 ``min_len = 1 + max(1, round(8*a))`` を決め、"
        "これに満たない水平ランを除去する（``a=0`` で ``min_len=2``、すなわち"
        "1 画素だけの細い橋を切る）。``b`` は未使用。走査は行ごと・水平方向のみ"
        "（縦方向のランは対象外）。"
    ),
    "r3_rank_region": (
        "領域の形態学的ランクオペレータ（HALCON 正真正銘の ``rank_region``: 収縮でも"
        "膨張でもない一般化）。\n\n"
        "``sz x sz``（``sz`` は 3, 5, 7 のいずれかを ``a`` で選ぶ）の窓の中で、"
        "領域に属する画素が ``number`` 個以上あれば出力を立てる。``number`` は"
        "``b``（0〜1）を窓面積に対する割合として決める（``number = sz*sz`` で"
        "収縮相当、``number = 1`` で膨張相当、中間ではランク/メディアンフィルタ"
        "相当の挙動になる）。"
    ),
    "r3_region_features": (
        "領域の形状特徴量を 1 つ返す（HALCON ``region_features`` の一部を実装）。"
        "\n\n"
        "``a < 0.5`` なら正規化面積（前景画素数/全画素数）、``a >= 0.5`` なら"
        "真円度の逆数にあたるコンパクトネス ``P^2 / (4*pi*A)``（``P`` は 4 連結"
        "境界の周囲長。円で 1、正方形で約 1.27、細長いほど大きくなる）を返す。"
        "``b`` は未使用。領域が空なら 0.0。"
    ),
    "r3_runlength_distribution": (
        "水平方向のラン長分布の要約統計量を 1 つ返す（HALCON "
        "``runlength_distribution`` に相当）。\n\n"
        "領域の全行にわたる水平連結ランの長さを集め、``a < 0.5`` ならその"
        "（母）分散、``a >= 0.5`` ならラン長ヒストグラムのシャノンエントロピー"
        "（ビット）を返す。``b`` は未使用。ランが 1 つも無ければ 0.0。"
    ),
    "r3_select_region_point": (
        "指定した 1 点を含む連結成分だけを残す（HALCON ``select_region_point`` に"
        "相当）。\n\n"
        "``a``, ``b``（いずれも 0〜1）を画像の行・列に線形写像した座標"
        "``(round(a*(H-1)), round(b*(W-1)))`` の画素を指定点とし、その画素が"
        "属する連結成分だけを返す。指定点が背景なら結果は空。"
    ),
    "r3_partition_dynamic": (
        "領域を、垂直方向の広がりが小さい列（くびれ）で水平に分割する（HALCON"
        "``partition_dynamic`` に相当）。\n\n"
        "各列の前景画素数（密度）を数え、``0 < 密度 <= a * 最大密度`` を満たす"
        "列（くびれ）をゼロに潰して領域を分断する。``a``（0〜1）がくびれと判定"
        "するしきい値の割合。``b`` は未使用。密度が一様な領域には分断対象の列が"
        "無く、そのまま返る。"
    ),
    "r3_polar_trans_region": (
        "領域を重心中心の極座標へリマップする（HALCON ``polar_trans_region`` に"
        "相当）。\n\n"
        "出力の行が半径軸（0〜``rmax``）、列が角度軸（0〜``angle_end``）に"
        "あたる。``a``（0〜1）は半径方向の広がり（``rmax`` は重心から最遠画素"
        "までの距離に ``0.25+0.75*a`` を掛けたもの）、``b``（0〜1）は角度方向の"
        "掃引幅（``angle_end = 2*pi*(0.25+0.75*b)``）を振る。最近傍サンプリング。"
        "出力の形状は入力と同じ。"
    ),
    "r3_label_to_region": (
        "ラベル画像から 1 つのグレー値（ラベル）を持つ画素だけを抽出する（HALCON"
        "``label_to_region`` に相当）。\n\n"
        "入力を 3 桁に丸めた上で 0 より大きい値をラベルとみなし、昇順に並べた"
        "``round(a * (ラベル数-1))`` 番目のラベルを選んで、その値を持つ画素を"
        "領域として返す。``b`` は未使用。単純な 0/1 マスクはラベルが 1 つしか"
        "無いので常にその前景が返る。"
    ),
}


# --------------------------------------------------------------------------- #
# registry assembly
# --------------------------------------------------------------------------- #
def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    """Return the r3_ binary-region operator tier (each fn sort-aware & exception-safe)."""
    cat = "region"
    defs = [
        ("r3_background_seg", "background_seg", REGION, REGION, r3_background_seg),
        ("r3_clip_region", "clip_region", REGION, REGION, r3_clip_region),
        ("r3_eliminate_runs", "eliminate_runs", REGION, REGION, r3_eliminate_runs),
        ("r3_rank_region", "rank_region", REGION, REGION, r3_rank_region),
        ("r3_region_features", "region_features", REGION, FEATURE, r3_region_features),
        ("r3_runlength_distribution", "runlength_distribution", REGION, FEATURE,
         r3_runlength_distribution),
        ("r3_select_region_point", "select_region_point", REGION, REGION,
         r3_select_region_point),
        ("r3_partition_dynamic", "partition_dynamic", REGION, REGION, r3_partition_dynamic),
        ("r3_polar_trans_region", "polar_trans_region", REGION, REGION,
         r3_polar_trans_region),
        ("r3_label_to_region", "label_to_region", REGION, REGION, r3_label_to_region),
    ]

    def _wrap(fn, osort):
        def inner(v, a, b):
            try:
                out = fn(v, a, b)
            except Exception as _e:  # noqa: BLE001 - recorded, strict mode re-raises
                from backend_safe import is_strict as _bs_strict, record as _bs_record
                if _bs_strict():
                    raise
                _bs_record(None, _e, osort)
                out = None
            if osort == FEATURE:
                try:
                    f = float(out)
                except (TypeError, ValueError):
                    return np.float64(0.0)
                return np.float64(f if np.isfinite(f) else 0.0)
            # region output: enforce shape / dtype / 0-1 domain, fail-soft to zeros
            shape = _as_mask(v).shape
            if not isinstance(out, np.ndarray) or out.shape != shape:
                return np.zeros(shape, np.float64)
            return _clip01(np.where(out > 0.5, 1.0, 0.0)).astype(np.float64)
        # ラッパは振る舞いを包むのであって説明を消してはいけない
        # (backend_safe.guard と同じ穴。同型のラッパ族が 4 つあった)。
        inner.__name__ = getattr(fn, "__name__", "op")
        inner.__doc__ = getattr(fn, "__doc__", None)
        return inner

    return [Op(name, cat, halcon, isort, osort, _wrap(fn, osort))
            for (name, halcon, isort, osort, fn) in defs]
