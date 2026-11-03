# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""記号の印字品質の等級 —— 1-D(ISO/IEC 15416 の考え方)と 2-D(ISO/IEC 15415 の考え方)。

Print-quality grading of symbols. The *quantities* follow the published structure of
the two verification methods — a 1-D symbol is graded from scan reflectance profiles
(symbol contrast, minimum reflectance, minimum edge contrast, modulation, defects,
decodability, decode, quiet zone), a 2-D symbol from a reflectance image sampled at
the module centres (symbol contrast, modulation with the error-correction rule,
fixed-pattern damage, axial and grid non-uniformity, unused error correction,
decode). Each parameter gets a grade 4 (A) .. 0 (F); a 1-D profile's grade is its
worst parameter and the symbol grade the mean over profiles; a 2-D symbol's grade is
its worst parameter.

★これは**認証された検証器ではない**。規格の本文は著作物なので写していない。定義と
等級の境界は公開の解説(GS1 General Specifications のバーコード品質の節、各社の公開
技術資料)で広く引かれている値に合わせ、細部(反射率の校正、測定開口の形、要素の
端の扱い)は Fullseye の実装として docstring に書いた。**数値は合成の真値で門を掛けて
ある**(理想のシンボル → 最高等級、既知の劣化 → 閉形式で決まる値と向き)。
This is not a certified verifier: the standards' text is not reproduced; grade
boundaries are the values widely quoted in public explanations, and implementation
details are documented here. Gates use closed forms on synthetic symbols.

入力の反射率 / reflectance: 画像の値をそのまま反射率(0..1)とみなす。実機では
既知の反射率の校正板で撮像系を校正してから渡すこと(しないと SC・Rmin が装置で変わる)。
Image values are taken as calibrated reflectance.

出典(公開文書のみ)/ sources (public only): GS1 General Specifications(バーコードの
品質の節、公開)/ R. C. Palmer, *The Bar Code Book*, 5th ed., 2007 / ISO/IEC 15416・
15415 は**番号の参照のみ**(本文は写していない)。
"""
from __future__ import annotations

import numpy as np

import barcode1d as _b1

__all__ = ["grade_letter", "grade_barcode_profile", "grade_barcode1d", "grade_datacode2d",
           "GRADE_TABLE_1D", "GRADE_TABLE_2D"]

#: 1-D の等級の境界(下限: その値以上でその等級。defects だけは上限)。
#: Grade boundaries (lower bounds; ``defects`` is an upper bound) for 1-D profiles.
GRADE_TABLE_1D = {
    "symbol_contrast": (0.70, 0.55, 0.40, 0.20),
    "modulation": (0.70, 0.60, 0.50, 0.40),
    "defects": (0.15, 0.20, 0.25, 0.30),          # 上限 / upper bounds
    "decodability": (0.62, 0.50, 0.37, 0.25),
}
#: 2-D の等級の境界 / grade boundaries for 2-D symbols.
GRADE_TABLE_2D = {
    "symbol_contrast": (0.70, 0.55, 0.40, 0.20),
    "module_modulation": (0.50, 0.40, 0.30, 0.20),
    "axial_nonuniformity": (0.06, 0.08, 0.10, 0.12),   # 上限
    "grid_nonuniformity": (0.38, 0.50, 0.63, 0.75),    # 上限(モジュール単位)
    "unused_error_correction": (0.62, 0.50, 0.37, 0.25),
}
_LOWER_IS_BETTER = {"defects", "axial_nonuniformity", "grid_nonuniformity"}


def _grade(value, name, table):
    th = table[name]
    if name in _LOWER_IS_BETTER:
        for g, t in zip((4, 3, 2, 1), th):
            if value <= t + 1e-12:
                return g
        return 0
    for g, t in zip((4, 3, 2, 1), th):
        if value >= t - 1e-12:
            return g
    return 0


def grade_letter(grade):
    """数値の等級(0..4)を文字へ: A ≥ 3.5、B ≥ 2.5、C ≥ 1.5、D ≥ 0.5、それ未満 F(``str``)。

    Numeric grade (0..4, may be a mean) to its letter. Rejects (``ValueError``) values
    outside [0, 4] or non-finite.
    """
    g = float(grade)
    if not np.isfinite(g) or not 0.0 <= g <= 4.0:
        raise ValueError("grade_letter: grade must be in [0, 4], got %r" % (grade,))
    for t, L in ((3.5, "A"), (2.5, "B"), (1.5, "C"), (0.5, "D")):
        if g >= t:
            return L
    return "F"


def _trapped(v, light):
    """要素内の「閉じ込められた」凹み(明要素)/ 凸(暗要素)の最大の深さ。

    For a space: depth_i = min(max left of i, max right of i) − v_i (a valley between
    two peaks inside the element). For a bar the mirror image. Monotone edges give 0.
    """
    if v.size < 3:
        return 0.0
    if not light:
        v = -v
    left = np.maximum.accumulate(v)
    right = np.maximum.accumulate(v[::-1])[::-1]
    return float(np.max(np.minimum(left, right) - v))


def grade_barcode_profile(profile, symbologies=None, *, quiet_zone_x=None):
    """1 本の走査線(反射率の 1-D 列)の印字品質のパラメータと等級を返す(``table``)。

    Grade one scan reflectance profile. The profile must cover the symbol and its
    quiet zones. Quantities (reflectances in [0, 1]):

    * ``r_max`` / ``r_min``: highest / lowest reflectance over the profile.
    * ``symbol_contrast`` SC = r_max − r_min; global threshold GT = r_min + SC / 2.
    * elements = runs between GT crossings; a space's reflectance is its maximum, a
      bar's its minimum; the quiet zones are the outer spaces.
    * ``edge_contrast_min`` ECmin = min over adjacent element pairs of |Rs − Rb|.
    * ``modulation`` MOD = ECmin / SC.
    * ``defects`` = ERNmax / SC, where an element's reflectance non-uniformity ERN is
      the deepest valley trapped between two higher samples inside a space (or the
      highest peak trapped inside a bar) — monotone edges contribute nothing.
    * ``decodability`` = the smallest per-character decode margin returned by the
      reference decode (:func:`barcode1d.decode_barcode_profile` at GT): for the
      edge-to-similar-edge symbologies (EAN/UPC, Code 128) the margin of each
      similar-edge sum from its decision boundary (half a module), for the two-width
      ones (Code 39, ITF) the margin of the narrowest wide / widest narrow element from
      the mid threshold, both scaled to 1 = ideal, 0 = on the boundary.
    * ``decode`` (bool), ``quiet_zone_ok`` (both light zones at least the symbology's
      quiet zone, or ``quiet_zone_x`` X, wide), ``r_min_ok`` (Rmin ≤ 0.5 Rmax),
      ``edge_contrast_ok`` (ECmin ≥ 0.15).

    Grades 4..0 per parameter (``grades``), ``profile_grade`` = the minimum, and
    ``limiting`` = the parameters at that minimum. A profile that does not decode is
    graded 0 with ``decode = False`` (the other quantities are still reported when the
    profile has edges).

    空の入力(16 標本未満)は ``ValueError``。
    拒否(``ValueError``): 1-D でない、非有限、``quiet_zone_x`` が負。平らな走査線
    (縁が無い)は SC = 0 で ``profile_grade = 0``(読めない、と数える)。
    """
    op = "grade_barcode_profile"
    p = _b1._profile(profile, op)
    qz_req = None
    if quiet_zone_x is not None:
        qz_req = float(quiet_zone_x)
        if not np.isfinite(qz_req) or qz_req < 0:
            raise ValueError("%s: quiet_zone_x must be >= 0, got %r" % (op, quiet_zone_x))
    rmax, rmin = float(p.max()), float(p.min())
    sc = rmax - rmin
    out = {"r_max": rmax, "r_min": rmin, "symbol_contrast": sc, "threshold": rmin + 0.5 * sc}
    if sc <= 1e-6:
        out.update({"decode": False, "modulation": 0.0, "defects": 0.0, "decodability": 0.0,
                    "edge_contrast_min": 0.0, "grades": {}, "profile_grade": 0,
                    "limiting": ["decode"], "quiet_zone_ok": False, "r_min_ok": False,
                    "edge_contrast_ok": False, "text": None, "symbology": None})
        return out
    gt = rmin + 0.5 * sc
    try:
        dec = _b1.decode_barcode_profile(p, symbologies, threshold=gt)
    except _b1.Barcode1DError:
        dec = None
    if dec is not None:
        a, b = dec["start"], dec["stop"]
        x = dec["x_dim"]
        ql, qr = _b1.QUIET[dec["symbology"]]
        if qz_req is not None:
            ql = qr = qz_req
        lo = max(0, int(np.floor(a - (ql + 1) * x)))
        hi = min(p.size, int(np.ceil(b + (qr + 1) * x)) + 1)
        seg = p[lo:hi]
        # 静寂域 = 最初のバーの前と最後のバーの後の明るい要素の幅(画像の端で切れたら端まで)
        bf, wf, _cf = _b1._elements(p, gt)
        i_a = int(np.argmin(np.abs(bf - a)))
        i_b = int(np.argmin(np.abs(bf - b)))
        q_left = float(wf[i_a - 1]) if i_a >= 1 else 0.0
        q_right = float(wf[i_b]) if i_b < wf.size else 0.0
        qz_ok = q_left >= ql * x - 0.5 and q_right >= qr * x - 0.5
        out["quiet_zone_x"] = (q_left / x, q_right / x)
    else:
        seg = p
        qz_ok = False
    rmax, rmin = float(seg.max()), float(seg.min())
    sc = rmax - rmin
    gt = rmin + 0.5 * sc
    bounds, widths, colors = _b1._elements(seg, gt)
    edges_idx = np.concatenate([[0], np.floor(bounds[1:-1]).astype(int) + 1, [seg.size]])
    refl, ern = [], 0.0
    for k in range(widths.size):
        i0, i1 = edges_idx[k], edges_idx[k + 1]
        if i1 <= i0:
            refl.append(gt)
            continue
        e = seg[i0:i1]
        is_bar = bool(colors[k])
        refl.append(float(e.min()) if is_bar else float(e.max()))
        ern = max(ern, _trapped(e, light=not is_bar))
    refl = np.asarray(refl)
    ec = np.abs(np.diff(refl)) if refl.size > 1 else np.array([0.0])
    ecmin = float(ec.min())
    mod = ecmin / sc
    defects = ern / sc
    decodability = float(min(dec["margins"])) if dec is not None else 0.0
    grades = {
        "symbol_contrast": _grade(sc, "symbol_contrast", GRADE_TABLE_1D),
        "modulation": _grade(mod, "modulation", GRADE_TABLE_1D),
        "defects": _grade(defects, "defects", GRADE_TABLE_1D),
        "decodability": _grade(decodability, "decodability", GRADE_TABLE_1D),
        "r_min": 4 if rmin <= 0.5 * rmax + 1e-12 else 0,
        "edge_contrast_min": 4 if ecmin >= 0.15 - 1e-12 else 0,
        "decode": 4 if dec is not None else 0,
        "quiet_zone": 4 if qz_ok else 0,
    }
    pg = min(grades.values())
    out.update({"r_max": rmax, "r_min": rmin, "symbol_contrast": sc, "threshold": gt,
                "edge_contrast_min": ecmin, "modulation": mod, "defects": defects,
                "decodability": decodability, "decode": dec is not None,
                "quiet_zone_ok": bool(qz_ok), "r_min_ok": grades["r_min"] == 4,
                "edge_contrast_ok": grades["edge_contrast_min"] == 4,
                "grades": grades, "profile_grade": int(pg),
                "limiting": sorted(k for k, g in grades.items() if g == pg),
                "text": None if dec is None else dec["text"],
                "symbology": None if dec is None else dec["symbology"],
                "n_elements": int(widths.size)})
    return out


def _aperture_filter(a, diameter_px):
    from scipy import ndimage
    import symrender
    if diameter_px <= 0:
        return a
    return ndimage.convolve(a, symrender._disk_kernel(diameter_px), mode="nearest")


def grade_barcode1d(image, symbologies=None, *, n_scans=10, aperture_x=0.5, angle_deg=None,
                    expected_text=None):
    """画像の 1-D シンボルの印字品質の等級(``n_scans`` 本の走査線の平均)を返す(``table``)。

    Grade a 1-D symbol in a reflectance image: read it (:func:`barcode1d.read_barcode1d`)
    to find the bar direction and the module width X, filter the image with a
    circular measuring aperture of ``aperture_x`` · X diameter (default 0.5 X), take
    ``n_scans`` profiles evenly over 10 %..90 % of the bar height and grade each
    (:func:`grade_barcode_profile`). ``symbol_grade`` = mean of the profile grades
    (0..4), ``letter`` its letter; ``parameters`` = per-parameter lists over the scans
    and ``parameter_grade_mean`` their mean grades; ``limiting`` = the parameters that
    most often set a profile's grade. With ``expected_text`` a profile that decodes to
    a different string is graded 0 (``misread`` counts them) — a misread is worse than
    a no-read.

    限界 / limits: 開口は円(画素で積分)、反射率は画像の値そのまま。走査線は画像の端まで
    伸ばし、各走査線で読めたシンボルの両側の静寂域 + 1 X だけを評価に使う。

    空の入力は ``ValueError``。
    拒否(``ValueError``): 2-D でない、非有限、``n_scans`` < 1、``aperture_x`` が
    [0, 2] の外。シンボルが見つからなければ :class:`barcode1d.Barcode1DError`。
    """
    op = "grade_barcode1d"
    a = _b1._image(image, op)
    if isinstance(n_scans, bool) or not isinstance(n_scans, (int, np.integer)) or n_scans < 1:
        raise ValueError("%s: n_scans must be a positive integer, got %r" % (op, n_scans))
    ap = float(aperture_x)
    if not np.isfinite(ap) or not 0.0 <= ap <= 2.0:
        raise ValueError("%s: aperture_x must lie in [0, 2], got %r" % (op, aperture_x))
    rd = _b1.read_barcode1d(a, symbologies, angle_deg=angle_deg)
    x_px = rd["x_dim_px"]
    filt = _aperture_filter(a, ap * x_px)
    sp = _b1.barcode_scan_profiles(filt, angle_deg=rd["angle_deg"], n_lines=int(n_scans),
                                   band=(0.1, 0.9))
    allowed = (rd["symbology"],) if rd["symbology"] != "upca" else ("ean13", "upca")
    per, misread = [], 0
    for prof in sp["profiles"]:
        g = grade_barcode_profile(prof, allowed)
        if expected_text is not None and g["decode"] and g["text"] != expected_text:
            misread += 1
            g["profile_grade"] = 0
            g["grades"]["decode"] = 0
            g["limiting"] = ["decode"]
        per.append(g)
    names = ("symbol_contrast", "r_min", "edge_contrast_min", "modulation", "defects",
             "decodability")
    params = {n: [float(g[n]) for g in per] for n in names}
    grade_keys = sorted({k for g in per for k in g["grades"]})
    pgm = {k: float(np.mean([g["grades"].get(k, 0) for g in per])) for k in grade_keys}
    lim = {}
    for g in per:
        for k in g["limiting"]:
            lim[k] = lim.get(k, 0) + 1
    sg = float(np.mean([g["profile_grade"] for g in per]))
    return {"symbol_grade": sg, "letter": grade_letter(sg), "profile_grades": [g["profile_grade"] for g in per],
            "parameters": params, "parameter_grade_mean": pgm,
            "limiting": sorted(lim, key=lambda k: -lim[k]), "text": rd["text"],
            "symbology": rd["symbology"], "x_dim_px": float(x_px), "aperture_px": ap * x_px,
            "n_scans": int(n_scans), "misread": int(misread), "profiles": per}


# --------------------------------------------------------------------------- #
# 2-D(ISO/IEC 15415 の考え方)/ 2-D symbols
# --------------------------------------------------------------------------- #
def _apply_h(H, x, y):
    w = H[2, 0] * x + H[2, 1] * y + H[2, 2]
    return (H[0, 0] * x + H[0, 1] * y + H[0, 2]) / w, (H[1, 0] * x + H[1, 1] * y + H[1, 2]) / w


def _sample_at(img, H, uu, vv):
    from scipy import ndimage
    cx, cy = _apply_h(H, uu, vv)
    return ndimage.map_coordinates(img, [cy.ravel(), cx.ravel()], order=1, mode="nearest").reshape(uu.shape), cx, cy


def _qr_block_of(blocks):
    """QR の送出順の符号語 → ブロック番号(データは列ごと、短いブロックが先)。"""
    seq = []
    maxd = max(b[0] for b in blocks)
    for i in range(maxd):
        for k, (nd, _ne) in enumerate(blocks):
            if i < nd:
                seq.append(k)
    ne = blocks[0][1]
    for _i in range(ne):
        for k in range(len(blocks)):
            seq.append(k)
    return np.asarray(seq)


def _dm_block_of(blocks):
    nb = len(blocks)
    nd = sum(b[0] for b in blocks)
    ne = sum(b[1] for b in blocks)
    return np.concatenate([np.arange(nd) % nb, np.arange(ne) % nb])


def _qr_fixed_mask(n, function_mask):
    """QR の固定パターン(ファインダ・分離帯・タイミング・位置合わせ)= 機能部 − 形式/型番情報。"""
    import qrsym
    m = np.asarray(function_mask, bool).copy()
    a, b = qrsym._format_coords(n)
    for (r, c) in a + b:
        m[r, c] = False
    m[n - 8, 8] = False                                     # 暗モジュール(1 個)/ the dark module
    if n >= 45:
        va, vb = qrsym._version_coords(n)
        for (r, c) in va + vb:
            m[r, c] = False
    return m


def _qr_timing_lines(n):
    """QR のタイミング(行 6 / 列 6)の区間(モジュール座標の始点・終点・向き)。"""
    return [("row", 6, 8, n - 8), ("col", 6, 8, n - 8)]


def _dm_timing_lines(rows, cols):
    return [("row", 0, 0, cols), ("col", cols - 1, 0, rows)]


def _fit_h(uv, xy):
    """正規化 DLT で平面 (u, v) → 画素 (x, y) の射影を当てる(最小二乗)。"""
    def norm(p):
        c = p.mean(axis=0)
        d = np.sqrt(((p - c) ** 2).sum(axis=1)).mean()
        s = np.sqrt(2.0) / max(d, 1e-12)
        return np.array([[s, 0, -s * c[0]], [0, s, -s * c[1]], [0, 0, 1.0]])
    Ta, Tb = norm(uv), norm(xy)
    a = (Ta @ np.column_stack([uv, np.ones(len(uv))]).T).T
    b = (Tb @ np.column_stack([xy, np.ones(len(xy))]).T).T
    rows = []
    for (u, v, _), (x, y, _) in zip(a, b):
        rows.append([-u, -v, -1, 0, 0, 0, x * u, x * v, x])
        rows.append([0, 0, 0, -u, -v, -1, y * u, y * v, y])
    _, _, vt = np.linalg.svd(np.asarray(rows))
    Hn = vt[-1].reshape(3, 3)
    H = np.linalg.inv(Tb) @ Hn @ Ta
    return H / H[2, 2]


def _edge_correspondences(img, H, ideal, gt, step=0.02):
    """理想格子の明暗の境(行・列の全部)を画像の上で縁として測り、(平面の点, 画素) の対を返す。

    Along every module row and column, find the sub-sample GT crossings near each ideal
    dark/light boundary (within 0.45 module) and pair the measured pixel position with
    the ideal plane point. Uniform ink spread moves rising and falling edges in
    opposite directions, so it does not bias the fitted grid.
    """
    R, C = ideal.shape
    uv, xy = [], []
    for axis in (0, 1):
        n_lines, length = (R, C) if axis == 0 else (C, R)
        t = np.arange(0.0, length + 1e-9, step)
        for k in range(n_lines):
            line = ideal[k, :] if axis == 0 else ideal[:, k]
            bnd = np.flatnonzero(line[1:] != line[:-1]) + 1.0      # 境界の位置(整数)
            if bnd.size == 0:
                continue
            if axis == 0:
                uu, vv = t, np.full_like(t, k + 0.5)
            else:
                uu, vv = np.full_like(t, k + 0.5), t
            prof, _cx, _cy = _sample_at(img, H, uu, vv)
            s_ = prof < gt
            idx = np.flatnonzero(s_[1:] != s_[:-1])
            if idx.size == 0:
                continue
            den = prof[idx + 1] - prof[idx]
            f = np.where(np.abs(den) > 0, (gt - prof[idx]) / np.where(den == 0, 1, den), 0.5)
            pos = t[idx] + np.clip(f, 0, 1) * step
            for b in bnd:
                j = int(np.argmin(np.abs(pos - b)))
                if abs(pos[j] - b) > 0.45:
                    continue
                if axis == 0:
                    px, py = _apply_h(H, np.array([pos[j]]), np.array([k + 0.5]))
                    uv.append((b, k + 0.5))
                else:
                    px, py = _apply_h(H, np.array([k + 0.5]), np.array([pos[j]]))
                    uv.append((k + 0.5, b))
                xy.append((float(px[0]), float(py[0])))
    return np.asarray(uv, float), np.asarray(xy, float)


def _timing_deviation(img, H, lines, gt):
    """タイミングの各モジュールの中心を縁から測り、当てた射影格子からのずれ(モジュール)。

    Locate each timing-pattern module centre from its two edges (sub-sample GT
    crossings along the line, 0.02-module steps) and return the deviations from the
    fitted projective grid in module units (the edges are converted back with H⁻¹).
    """
    devs = []
    for kind, idx, a, b in lines:
        t = np.arange(a, b + 1e-9, 0.02)
        if kind == "row":
            uu, vv = t, np.full_like(t, idx + 0.5)
        else:
            uu, vv = np.full_like(t, idx + 0.5), t
        prof, _cx, _cy = _sample_at(img, H, uu, vv)
        s = prof < gt
        k = np.flatnonzero(s[1:] != s[:-1])
        if k.size < 2:
            continue
        f = (gt - prof[k]) / np.where(np.abs(prof[k + 1] - prof[k]) > 0, prof[k + 1] - prof[k], 1.0)
        edge = t[k] + np.clip(f, 0, 1) * 0.02
        # 縁は整数の位置にあるはず → 中心 = 隣り合う縁の中点、理想 = 整数 + 0.5
        mids = 0.5 * (edge[1:] + edge[:-1])
        ideal = np.floor(mids) + 0.5
        ok = np.abs(np.round(edge[1:]) - np.round(edge[:-1])) == 1     # 1 モジュールの要素だけ
        devs.extend(np.abs(mids - ideal)[ok].tolist())
    return np.asarray(devs)


def grade_datacode2d(image, symbology="auto", *, aperture_x=0.8, expected_text=None):
    """画像の 2-D シンボル(QR / DataMatrix)の印字品質の等級を返す(``table``)。

    Grade a QR Code or Data Matrix in a reflectance image. The symbol is read
    (``qrsym.qr_read`` / ``dmsym.dm_read``), the image is filtered with a circular
    measuring aperture of ``aperture_x`` · X (default 0.8 X) and sampled at every module
    centre through the reader's homography, plus a one-module ring of quiet zone.

    * ``symbol_contrast`` SC = Rmax − Rmin over those samples; GT = Rmin + SC / 2.
    * module modulation ``2·|R − GT| / SC``; a module on the wrong side of GT (compared
      with the *ideal* module rebuilt from the decoded data) is graded 0. A codeword's
      grade is its worst module; the ``modulation`` grade is the highest level L such that
      the codewords graded below L, counted as errors, still leave unused error
      correction of grade ≥ L in every block (the error-correction rule of the 2-D
      method, as publicly described).
    * ``fixed_pattern_damage``: the worst module grade over the fixed patterns (QR:
      finders, separators, timing, alignment; Data Matrix: the L finder, the clock track
      and alignment patterns) and the quiet-zone ring. ★Simplified: one dull module of a
      finder limits it (the published method grades finder segments separately).
    * the grid: the reader's homography is re-fitted (normalised DLT, twice) to every
      module edge measured along all rows and columns (sub-sample GT crossings within
      0.45 module of an ideal dark/light boundary), so that the reader's own fit error is
      not graded as print non-uniformity (``grid_refined``).
    * ``axial_nonuniformity`` = |X̄ − Ȳ| / ((X̄ + Ȳ)/2) of the mean module pitch along
      the two grid axes in pixels (the fitted grid: a tilt about one axis shows up here).
    * ``grid_nonuniformity`` = the largest distance (modules) between a timing-pattern
      module centre located from its own edges and the fitted projective grid.
    * ``unused_error_correction`` = min over blocks of ``1 − 2·e / (n_ec − p)`` with the
      decoder's corrected-codeword count ``e`` and the misdecode-protection codewords
      ``p`` (QR 1-L/M/Q, 2-L, 3-L; 0 for Data Matrix).
    * ``decode``: 4 if read (and equal to ``expected_text`` when given), else 0.

    ``overall_grade`` = the minimum parameter grade (0..4), ``letter``, ``limiting``.
    ``ideal_source`` says how the ideal modules were obtained (``"reencode"``: the
    decoded text re-encoded with the same version / level / mask / mode reproduced the
    read; ``"codewords"`` (Data Matrix): rebuilt from the corrected codewords;
    ``"sampled"``: neither was possible, the thresholded samples stand in and wrong-side
    modules cannot be seen — ``modulation`` is then optimistic, flagged).

    限界 / limits: 反射率は画像の値のまま、開口は円。Data Matrix 144x144 の不揃いな
    ブロックのブロック割り当ては近似。鏡像の QR は読み取り器の格子(転置)で採点する。

    空の入力は ``ValueError``。
    拒否(``ValueError``): 2-D でない、非有限、未知の ``symbology``、``aperture_x`` が
    [0, 2] の外。**読めないシンボル**は例外にせず ``overall_grade = 0``、``decode = False``
    (検証器が F を付けるのと同じ。読めない理由は ``error``)。
    """
    op = "grade_datacode2d"
    a = _b1._image(image, op)
    if symbology not in ("auto", "qr", "datamatrix"):
        raise ValueError("%s: symbology must be 'auto', 'qr' or 'datamatrix', got %r" % (op, symbology))
    ap = float(aperture_x)
    if not np.isfinite(ap) or not 0.0 <= ap <= 2.0:
        raise ValueError("%s: aperture_x must lie in [0, 2], got %r" % (op, aperture_x))
    r, sym, errs = None, None, []
    for cand in (("qr", "datamatrix") if symbology == "auto" else (symbology,)):
        try:
            if cand == "qr":
                import qrsym
                r = qrsym.qr_read(a)
            else:
                import dmsym
                r = dmsym.dm_read(a)
            sym = cand
            break
        except ValueError as exc:
            errs.append("%s: %s" % (cand, exc))
    if r is None:
        return {"overall_grade": 0, "letter": "F", "decode": False, "symbology": None,
                "limiting": ["decode"], "grades": {"decode": 0}, "error": "; ".join(errs),
                "text": None}
    H = np.asarray(r["homography"], dtype=np.float64)
    if sym == "qr":
        R = C = int(r.get("size", np.asarray(r["reflectance"]).shape[0]))
    else:
        R, C = int(r["rows"]), int(r["cols"])
    # 画素のモジュール寸法 / module pitch in pixels from the grid
    jj, ii = np.meshgrid(np.arange(C) + 0.5, np.arange(R) + 0.5)
    _r0, cx, cy = _sample_at(a, H, jj, ii)
    dx = np.hypot(np.diff(cx, axis=1), np.diff(cy, axis=1))
    dy = np.hypot(np.diff(cx, axis=0), np.diff(cy, axis=0))
    xbar, ybar = float(dx.mean()), float(dy.mean())
    X = 0.5 * (xbar + ybar)
    filt = _aperture_filter(a, ap * X)
    Rg, _, _ = _sample_at(filt, H, jj, ii)
    # 静寂域の 1 モジュールの環 / one-module quiet-zone ring
    ring_u = np.concatenate([np.arange(-1, C + 1) + 0.5, np.arange(-1, C + 1) + 0.5,
                             np.full(R, -0.5), np.full(R, C + 0.5)])
    ring_v = np.concatenate([np.full(C + 2, -0.5), np.full(C + 2, R + 0.5),
                             np.arange(R) + 0.5, np.arange(R) + 0.5])
    ring, _, _ = _sample_at(filt, H, ring_u, ring_v)
    allv = np.concatenate([Rg.ravel(), ring.ravel()])
    rmax, rmin = float(allv.max()), float(allv.min())
    sc = rmax - rmin
    gt = rmin + 0.5 * sc
    # 理想のモジュール / ideal modules
    ideal, cw_index, fixed, src = None, None, None, "sampled"
    if sym == "qr":
        import qrsym
        try:
            e = qrsym.qr_encode(r["text"], ec_level=r["ec_level"], version=r["version"],
                                mask=r["mask"], mode=r["mode"])
            ideal = np.asarray(e["modules"], bool)
            cw_index = np.asarray(e["codeword_index"])
            fm = np.asarray(e["function_mask"], bool)
            if r.get("mirrored"):
                ideal, cw_index, fm = ideal.T, cw_index.T, fm.T
            fixed = _qr_fixed_mask(R, fm.T if r.get("mirrored") else fm)
            if r.get("mirrored"):
                fixed = fixed.T
            sampled = Rg < gt
            bad_cw = set(np.unique(cw_index[(sampled != ideal) & (cw_index >= 0)]).tolist())
            src = "reencode" if len(bad_cw) == int(r["n_corrected"]) else "sampled"
            if src == "sampled":
                ideal = None
        except ValueError:
            ideal = None
        blocks = r["blocks"]
        block_of = _qr_block_of(blocks)
        p = list(r.get("block_p", [0] * len(blocks)))
        lines = _qr_timing_lines(R)
    else:
        import dmsym
        try:
            n_data = int(sum(b[0] for b in r["blocks"]))
            mods, _cws = dmsym._symbol_from_data_codewords(list(r["codewords"])[:n_data], R, C)
            ideal = np.asarray(mods, bool)
            src = "codewords"
        except (ValueError, KeyError):
            ideal = None
        cw_index = np.asarray(r["codeword_index"])
        fixed = np.asarray(r["function_mask"], bool)
        blocks = r["blocks"]
        block_of = _dm_block_of(blocks)
        p = [0] * len(blocks)
        lines = _dm_timing_lines(R, C)
    if ideal is None:
        ideal = Rg < gt
        if cw_index is None:
            cw_index = np.full((R, C), -1)
        if fixed is None:
            fixed = np.zeros((R, C), bool)
    # 縁から格子を当て直す(読み取り器の当てはめの誤差を印字の不均一と取り違えない)
    # refine the grid from all measured module edges, so that the reader's fit error is
    # not graded as print non-uniformity
    refined = False
    for _it in range(2):
        uv, xy = _edge_correspondences(filt, H, ideal, gt)
        if len(uv) >= 16:
            H = _fit_h(uv, xy)
            refined = True
    if refined:
        _r0, cx, cy = _sample_at(a, H, jj, ii)
        dx = np.hypot(np.diff(cx, axis=1), np.diff(cy, axis=1))
        dy = np.hypot(np.diff(cx, axis=0), np.diff(cy, axis=0))
        xbar, ybar = float(dx.mean()), float(dy.mean())
        X = 0.5 * (xbar + ybar)
        Rg, _, _ = _sample_at(filt, H, jj, ii)
        ring, _, _ = _sample_at(filt, H, ring_u, ring_v)
        allv = np.concatenate([Rg.ravel(), ring.ravel()])
        rmax, rmin = float(allv.max()), float(allv.min())
        sc = rmax - rmin
        gt = rmin + 0.5 * sc
    modv = 2.0 * np.abs(Rg - gt) / max(sc, 1e-12)
    wrong = (Rg < gt) != ideal
    mg = np.zeros((R, C), int)
    for g, t in zip((4, 3, 2, 1), GRADE_TABLE_2D["module_modulation"]):
        mg = np.where((mg == 0) & (modv >= t - 1e-12), g, mg)
    mg = np.where(wrong, 0, mg)
    # 符号語の等級 = 最悪のモジュール / codeword grade = its worst module
    ncw = int(block_of.size)
    cw_grade = np.full(ncw, 4, int)
    sel = cw_index >= 0
    np.minimum.at(cw_grade, cw_index[sel].astype(int), mg[sel])
    nb = len(blocks)
    n_ec = np.array([b[1] for b in blocks], float)
    pp = np.asarray(p, float)

    def uec_from_counts(err_counts):
        den = np.maximum(n_ec - pp, 1.0)
        return float(np.min(np.clip(1.0 - 2.0 * np.asarray(err_counts, float) / den, 0.0, 1.0)))

    mod_grade = 0
    for L in (4, 3, 2, 1):
        e_L = [int(np.sum((cw_grade < L) & (block_of == b))) for b in range(nb)]
        gL = min(L, _grade(uec_from_counts(e_L), "unused_error_correction", GRADE_TABLE_2D))
        mod_grade = max(mod_grade, gL)
    uec = uec_from_counts(r["block_corrected"])
    # 固定パターン + 静寂域の環 / fixed patterns + quiet ring (ideal light)
    ring_mod = 2.0 * (ring - gt) / max(sc, 1e-12)
    ring_g = np.zeros(ring.shape, int)
    for g, t in zip((4, 3, 2, 1), GRADE_TABLE_2D["module_modulation"]):
        ring_g = np.where((ring_g == 0) & (ring_mod >= t - 1e-12), g, ring_g)
    fpd = int(min(mg[fixed].min() if fixed.any() else 4, ring_g.min()))
    an = abs(xbar - ybar) / X
    devs = _timing_deviation(filt, H, lines, gt)
    gn = float(devs.max()) if devs.size else float("nan")
    text_ok = expected_text is None or r["text"] == expected_text
    grades = {
        "symbol_contrast": _grade(sc, "symbol_contrast", GRADE_TABLE_2D),
        "modulation": int(mod_grade),
        "fixed_pattern_damage": fpd,
        "axial_nonuniformity": _grade(an, "axial_nonuniformity", GRADE_TABLE_2D),
        "grid_nonuniformity": _grade(gn, "grid_nonuniformity", GRADE_TABLE_2D) if np.isfinite(gn) else 0,
        "unused_error_correction": _grade(uec, "unused_error_correction", GRADE_TABLE_2D),
        "decode": 4 if text_ok else 0,
    }
    og = min(grades.values())
    return {"overall_grade": int(og), "letter": grade_letter(og), "decode": True,
            "text": r["text"], "text_matches": bool(text_ok), "symbology": sym,
            "grades": grades, "limiting": sorted(k for k, g in grades.items() if g == og),
            "symbol_contrast": sc, "r_max": rmax, "r_min": rmin, "threshold": gt,
            "axial_nonuniformity": float(an), "grid_nonuniformity": gn,
            "unused_error_correction": uec, "codeword_grades": cw_grade,
            "module_modulation": modv, "wrong_modules": int(wrong.sum()),
            "ideal_source": src, "x_dim_px": X, "pitch_px": (xbar, ybar),
            "aperture_px": ap * X, "rows": R, "cols": C, "grid_refined": refined,
            "homography": H,
            "block_corrected": list(r["block_corrected"]), "blocks": [tuple(b) for b in blocks]}
