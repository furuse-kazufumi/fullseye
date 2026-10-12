# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Global light transport — interreflection in concave Lambertian parts, direct/global separation, and the phase error it puts into fringe projection and AMCW time of flight (numpy only).

縞投影(位相シフト)も ToF も、「カメラの画素に届く光は、投影した 1 点(1 経路)から来た」と
仮定して位相を距離に変える。凹んだ形 —— V 溝、加工ポケットの内角、はんだフィレット、部屋の
隅 —— では、ある面で反射した光が向かいの面を照らし、画素には**別の場所の位相を持った光**が
混ざる(相互反射 = 大域成分)。白い Lambert 面でも凹んでいれば起きる。``fringe.py`` /
``photoncount.py`` / ``gi_render.py`` はどれもこれを扱っていない(docstring に限界として明記)。

11 の op(並びは物理の順):

  * :func:`groove_profile` — 凹んだ断面(V 溝・円弧の樋・フィレット・任意の折れ線)をパッチに
    分ける。カメラは真上からの正射影で、1 パッチ = 1 画素の列。
  * :func:`form_factors_2d` — 2-D(押し出し形状)の形態係数。Hottel の crossed-strings 則の閉形式。
  * :func:`transport_matrix_radiosity` — Lambert のラジオシティ ``B = ρE + ρFB`` の輸送行列
    ``T = (I − diag(ρ)F)^-1 diag(ρ)``(``n_bounces`` で反射回数を打ち切った Neumann 和も)。
  * :func:`high_frequency_patterns` — 縞(2 値、点灯率 α)・市松・正弦の投影パターンをずらした組。
  * :func:`render_transport` — 投影パターン → 輸送行列 → カメラ画像(順方向の描画)。
  * :func:`separate_direct_global` — Nayar ら(2006)の L_max / L_min による直接・大域の分離。
  * :func:`fringe_multipath_phase_error` — 直接と大域のフェーザ和の位相 ``arg(a1 e^{iφ1} + a2 e^{iφ2})``
    と、そのバイアス(最悪値 ``asin(a2/a1)`` も)。
  * :func:`predict_fringe_phase_error` — 輸送行列から、各画素の縞位相のバイアスと高さ誤差を予測する。
  * :func:`micro_phase_decode` — 高周波の狭い帯域の縞の組(Gupta & Nayar 2012 の考え方)を復号し、
    2 周波のうなり(合成波長)で次数を決める。
  * :func:`tof_multipath_phase` — AMCW ToF の多経路フェーザ和(経路ごとの振幅と往復経路長)。
  * :func:`tof_transport_depth` — 輸送行列に反射ごとの経路遅延を入れた複素ラジオシティで、
    凹んだ形(部屋の隅)の ToF 距離のバイアスを予測する。

座標の約束:
  * 断面は ``(x, z)``。x は横(カメラ画像の列)、+z は上(カメラ・プロジェクタ側)。断面は z(x) の
    関数で、**下に凸**(凹み)であること —— そのとき断面上の 2 点は互いに遮られずに見え、
    crossed-strings 則が厳密になる。凸でない断面は ``ValueError``(遮蔽を扱わないため)。
  * プロジェクタは正射影で、鉛直から +x 側へ ``triangulation_deg`` 傾いた向き ``d = (sin β, cos β)``
    から照らす。プロジェクタ座標は ``u = x cos β − z sin β``(光線に沿って一定)。全パッチで
    ``n·d > 0``(= u が断面に沿って単調)なら、どの光線も断面にちょうど 1 回当たる(影が無い)。
  * 画像の値はラジオシティ B(Lambert なら放射輝度は B/π。比だけを使うので定数は落とす)。

真値(``tests/test_lighttransport.py``):
  * 形態係数: V 溝の閉形式 ``F = 1 − sin(θ/2)`` と、核 ``cosθi cosθj / (2r)`` の Gauss–Legendre
    二重積分(別の経路)。相反性 ``Li Fij = Lj Fji``、開口を含めた行和 = 1。
  * ラジオシティ: Neumann 和が行列の解に収束、ρ → 0 で直接光だけ。
  * 分離: 輸送行列で描いたパターン画像(分離 op とは別の経路)から分離した L_d, L_g を、全点灯の
    輸送行列の真値と照合。周期を細かくすると誤差が単調に減る。
  * 位相: 描いた縞画像を ``fringe.wrapped_phase`` で復号した位相と、フェーザ和の閉形式。

★正直に書いておくこと(範囲):
  * **Lambert(完全拡散)・2-D(押し出し形状)だけ**。溝の軸方向に無限に長い形と、軸に平行な
    縞(または一様な光)のときに厳密。市松パターンは 2-D の問題にならないので ``render_transport``
    が拒む。実物の相互反射は鏡面成分が支配的なことが多い —— 鏡面の相互反射の真値には
    ``gi_render.render_gi``(Mitsuba 3、optional)が要り、本モジュールでは扱っていない。
  * 断面の両端の外は黒(反射しない)とみなす。``fillet`` の左端(床が続く側)では、続く床からの
    相互反射を落としている。
  * パッチ内の放射は一様(区分一定のラジオシティ)。頂点(V 溝の底)の近くでは真の分布が
    発散的に変わるので、パッチを細かくすると数字が少し動く(テストで測ってある)。
  * ToF の複素ラジオシティは、光源をカメラ位置の**線光源**(2-D の点光源)とし、遅延はパッチ中心
    間の距離で近似する(パッチが変調波長より十分小さいこと)。部屋の隅の数字は 2-D モデルのもの。

出典:
  * S. K. Nayar, G. Krishnan, M. D. Grossberg, R. Raskar, "Fast Separation of Direct and Global
    Components of a Scene using High Frequency Illumination", ACM Trans. Graphics 25(3), 2006
    (SIGGRAPH)。§3.3 の式 (7)–(9)(点灯率 α、消灯の明るさ b、パターンとその補)と §4.1(市松を
    ずらして L_max / L_min)を本文で読んだ。``scheme="complement"`` は式 (8)、``scheme="shift"``
    (同じパターンをずらすだけで補を使わない場合)は本モジュールで同じ仮定から導いた形。
  * M. Gupta, S. K. Nayar, "Micro Phase Shifting", CVPR 2012。式 (5)–(11)(大域光で位相が
    ``atan(Q/P)`` にずれる)と §3(全周波数を狭い高周波の帯域に置く)を本文で読んだ。論文の
    F + 2 枚の同時解法(式 (12)–(14))と Gushov–Solodkin の位相接続は**実装していない**:
    本モジュールは周波数ごとに N 枚の位相シフトで復号し、2 周波のうなりで次数を決める。
  * 形態係数の crossed-strings 則(H. C. Hottel)は教科書の標準形で、閉形式 ``1 − sin(θ/2)`` と
    数値積分で照合したものだけを門にした。
"""
from __future__ import annotations

import math

import numpy as np

import fringe

__all__ = [
    "groove_profile",
    "form_factors_2d",
    "transport_matrix_radiosity",
    "high_frequency_patterns",
    "render_transport",
    "separate_direct_global",
    "fringe_multipath_phase_error",
    "predict_fringe_phase_error",
    "micro_phase_decode",
    "tof_multipath_phase",
    "tof_transport_depth",
]

#: 断面であることを示す印(transport_matrix_radiosity などが fail-closed で確かめる)。
PROFILE_KIND = "lt_profile"
#: 輸送行列であることを示す印。
TRANSPORT_KIND = "lt_transport"
#: パッチ数の上限(P×P の行列を確保する前に拒む)。
MAX_PATCHES = 2048
#: 画像の画素数の上限。
MAX_PIXELS = 1 << 24
#: 真空中の光速 [m/s]。
C_LIGHT = 299_792_458.0
_KINDS = ("vgroove", "trough", "fillet", "polyline")


# --------------------------------------------------------------------------- #
# 入力の検証(fail-closed)
# --------------------------------------------------------------------------- #
def _num(v, name, op, lo=None, hi=None, lo_open=False, hi_open=False):
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, float, np.integer, np.floating)):
        raise ValueError("%s: %s must be a real number, got %r" % (op, name, v))
    v = float(v)
    if not math.isfinite(v):
        raise ValueError("%s: %s must be finite, got %r" % (op, name, v))
    if lo is not None and (v < lo or (lo_open and v == lo)):
        raise ValueError("%s: %s must be %s %g, got %g" % (op, name, ">" if lo_open else ">=", lo, v))
    if hi is not None and (v > hi or (hi_open and v == hi)):
        raise ValueError("%s: %s must be %s %g, got %g" % (op, name, "<" if hi_open else "<=", hi, v))
    return v


def _int(v, name, op, lo, hi):
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)):
        raise ValueError("%s: %s must be an integer, got %r" % (op, name, v))
    v = int(v)
    if v < lo or v > hi:
        raise ValueError("%s: %s must be in [%d, %d], got %d" % (op, name, lo, hi, v))
    return v


def _real(a, name, op):
    """実数の配列(None / bool / 複素 / 文字列 / マスク / 非有限は拒む)。"""
    if a is None:
        raise ValueError("%s: %s is None" % (op, name))
    if np.ma.is_masked(a):
        raise ValueError("%s: %s is a masked array — pass plain values" % (op, name))
    arr = np.asarray(a)
    if arr.dtype == object or arr.dtype.kind not in "iuf":
        raise ValueError("%s: %s must be real numbers, got dtype %s" % (op, name, arr.dtype))
    arr = arr.astype(np.float64)
    if arr.size == 0:
        raise ValueError("%s: %s is empty" % (op, name))
    if not np.isfinite(arr).all():
        raise ValueError("%s: %s contains NaN or Inf" % (op, name))
    return arr


def _stack(images, op, name="images", min_n=1):
    """画像の列 → (K, H, W) float64(list / tuple / 3-D 配列を受ける)。"""
    if images is None:
        raise ValueError("%s: %s is None" % (op, name))
    if isinstance(images, np.ndarray):
        arr = images
    else:
        try:
            frames = [np.asarray(f) for f in images]
        except TypeError:
            raise ValueError("%s: %s must be a sequence of 2-D images" % (op, name)) from None
        if not frames:
            raise ValueError("%s: %s is empty" % (op, name))
        if any(f.ndim != 2 for f in frames) or len({f.shape for f in frames}) != 1:
            raise ValueError("%s: %s must be 2-D images of one shape, got %s"
                             % (op, name, [f.shape for f in frames]))
        arr = np.stack(frames)
    if arr.ndim != 3:
        raise ValueError("%s: %s must be (K, H, W) or a list of 2-D images, got shape %s"
                         % (op, name, getattr(arr, "shape", None)))
    stack = _real(arr, name, op)
    if stack.shape[0] < min_n:
        raise ValueError("%s: %s needs at least %d images, got %d" % (op, name, min_n, stack.shape[0]))
    if stack.shape[1] * stack.shape[2] > MAX_PIXELS:
        raise ValueError("%s: %s has %d pixels per image (limit %d)"
                         % (op, name, stack.shape[1] * stack.shape[2], MAX_PIXELS))
    return stack


def _profile(p, op):
    if not isinstance(p, dict) or p.get("kind") != PROFILE_KIND:
        raise ValueError("%s: expected a profile from groove_profile (a dict with kind=%r)"
                         % (op, PROFILE_KIND))
    v = _real(p.get("vertices"), "profile vertices", op)
    if v.ndim != 2 or v.shape[1] != 2 or not (2 <= v.shape[0] - 1 <= MAX_PATCHES):
        raise ValueError("%s: profile vertices must be (P+1, 2) with 2 <= P <= %d" % (op, MAX_PATCHES))
    return _check_concave(v, op)


def _transport(t, op):
    if not isinstance(t, dict) or t.get("kind") != TRANSPORT_KIND:
        raise ValueError("%s: expected a transport from transport_matrix_radiosity (a dict with kind=%r)"
                         % (op, TRANSPORT_KIND))
    prof = t.get("profile")
    geo = _profile(prof, op)
    P = geo["n"]
    T = _real(t.get("transport"), "transport matrix", op)
    rho = _real(t.get("albedo"), "albedo", op)
    if T.shape != (P, P) or rho.shape != (P,):
        raise ValueError("%s: transport (%s) / albedo (%s) do not match the profile's %d patches"
                         % (op, T.shape, rho.shape, P))
    return geo, T, rho, prof


# --------------------------------------------------------------------------- #
# 断面
# --------------------------------------------------------------------------- #
def _check_concave(v, op):
    """折れ線が z(x) の関数で下に凸(凹み)かを確かめ、パッチの幾何を返す。"""
    x, z = v[:, 0], v[:, 1]
    dx = np.diff(x)
    if (dx <= 0.0).any():
        raise ValueError("%s: the profile must be a function z(x) with strictly increasing x "
                         "(the camera looks straight down; an overhang hides a patch)" % op)
    slope = np.diff(z) / dx
    scale = max(1.0, float(np.abs(slope).max()))
    if (np.diff(slope) < -1e-9 * scale).any():
        k = int(np.argmin(np.diff(slope)))
        raise ValueError("%s: the profile must be concave (slopes non-decreasing, a valley); it turns "
                         "convex at vertex %d — a bump would occlude, and occlusion is not modelled" % (op, k + 1))
    a, b = v[:-1], v[1:]
    t = b - a
    L = np.hypot(t[:, 0], t[:, 1])
    if (L <= 0.0).any():
        raise ValueError("%s: zero-length patch in the profile" % op)
    tn = t / L[:, None]
    normals = np.stack([-tn[:, 1], tn[:, 0]], axis=1)       # 左 → 右の接線を +90° 回す = 上向き
    return {"vertices": v, "a": a, "b": b, "lengths": L, "normals": normals,
            "centers": 0.5 * (a + b), "n": len(L)}


def groove_profile(kind="vgroove", n_patches=240, width=1.0, angle_deg=None, floor_frac=None, vertices=None):
    """Split a concave cross-section (V-groove, circular trough, fillet or any concave polyline) into patches, one camera pixel column each.

    The part is extruded along the groove axis; the cross-section is a
    function ``z(x)`` that is concave (a valley), viewed by an orthographic
    camera from straight above, one patch per pixel column. The built-in
    shapes are sampled at ``n_patches + 1`` uniform ``x`` (a kink between two
    samples is cut by the chord), rims at ``z = 0``. *angle_deg* is the
    shape's defining angle and *floor_frac* the share of *width* that is a
    flat floor; ``None`` takes the per-shape default.

    * ``"vgroove"`` — two plates with full opening angle *angle_deg*
      (default 90 = an inner corner tipped by 45 degrees, range ``[5, 175]``),
      meeting at the bottom or, with ``floor_frac > 0`` (default 0), on a
      centred flat floor (a trapezoidal groove). With no floor and an even
      *n_patches* the vertex is a patch edge.
    * ``"trough"`` — circular arcs that reach a wall slope of *angle_deg*
      at the rims (default 60, range ``(0, 90)``), with an optional centred
      floor (default 0).
    * ``"fillet"`` — a flat floor over the left *floor_frac* of the width
      (default 0.5, range ``(0, 1)``), then a circular arc tangent to it rising
      to a wall slope of *angle_deg* at the right rim (default 70, range
      ``(0, 85]``) — a solder-fillet-like meniscus. The floor's left end is open.
    * ``"polyline"`` — *vertices* ``(P+1, 2)`` as ``(x, z)``.

    Returns a dict (a ``table``) with ``kind = "lt_profile"``, ``shape``,
    ``vertices`` (P+1, 2), ``centers`` (P, 2), ``normals`` (P, 2, unit, pointing
    up out of the material), ``lengths`` (P,) and ``x_centers`` (P,).

    **Raises** ``ValueError``: unknown *kind*; *n_patches* not an integer in
    ``[2, 2048]``; non-positive or non-finite *width*; *angle_deg* or
    *floor_frac* outside the shape's range; *vertices* given for a built-in
    shape or missing for ``"polyline"``; vertices that are not a concave
    function ``z(x)`` (x not strictly increasing, or a convex turn).
    """
    op = "groove_profile"
    if not isinstance(kind, str) or kind not in _KINDS:
        raise ValueError("%s: kind must be one of %s, got %r" % (op, "/".join(_KINDS), kind))
    if kind == "polyline":
        if vertices is None:
            raise ValueError("%s: kind='polyline' needs vertices (P+1, 2)" % op)
        if angle_deg is not None or floor_frac is not None:
            raise ValueError("%s: angle_deg / floor_frac do not apply to kind='polyline'" % op)
        v = _real(vertices, "vertices", op)
        if v.ndim != 2 or v.shape[1] != 2 or not (2 <= v.shape[0] - 1 <= MAX_PATCHES):
            raise ValueError("%s: vertices must be (P+1, 2) with 2 <= P <= %d, got %s"
                             % (op, MAX_PATCHES, v.shape))
    else:
        if vertices is not None:
            raise ValueError("%s: vertices is only for kind='polyline'" % op)
        P = _int(n_patches, "n_patches", op, 2, MAX_PATCHES)
        w = _num(width, "width", op, lo=0.0, lo_open=True)
        half = 0.5 * w
        x = np.linspace(-half, half, P + 1)
        if kind == "fillet":
            wall = math.radians(_num(70.0 if angle_deg is None else angle_deg, "angle_deg", op,
                                     lo=0.0, hi=85.0, lo_open=True))
            ff = _num(0.5 if floor_frac is None else floor_frac, "floor_frac", op,
                      lo=0.0, hi=1.0, lo_open=True, hi_open=True)
            xf = -half + ff * w
            R = (half - xf) / math.sin(wall)
            depth = R * (1.0 - math.cos(wall))
            s = np.clip(x - xf, 0.0, None)
            z = -depth + R - np.sqrt(np.clip(R * R - s * s, 0.0, None))
        else:
            ff = _num(0.0 if floor_frac is None else floor_frac, "floor_frac", op, lo=0.0, hi=1.0, hi_open=True)
            e = half * (1.0 - ff)                                   # 片側の壁の横幅
            s = np.clip(np.abs(x) - half * ff, 0.0, None)          # 床の縁からの横距離
            if kind == "vgroove":
                th = math.radians(_num(90.0 if angle_deg is None else angle_deg, "angle_deg", op,
                                       lo=5.0, hi=175.0))
                depth = e / math.tan(0.5 * th)
                z = -depth + s * (depth / e)
                if ff == 0.0 and P % 2 == 0:
                    x[P // 2], z[P // 2] = 0.0, -depth             # 頂点を丸めずに置く
            else:  # trough
                a = math.radians(_num(60.0 if angle_deg is None else angle_deg, "angle_deg", op,
                                      lo=0.0, hi=90.0, lo_open=True, hi_open=True))
                R = e / math.sin(a)
                depth = R * (1.0 - math.cos(a))
                z = -depth + R - np.sqrt(np.clip(R * R - s * s, 0.0, None))
        v = np.stack([x, z], axis=1)
    geo = _check_concave(v, op)
    return {"kind": PROFILE_KIND, "shape": kind, "vertices": geo["vertices"], "centers": geo["centers"],
            "normals": geo["normals"], "lengths": geo["lengths"], "x_centers": geo["centers"][:, 0].copy()}


# --------------------------------------------------------------------------- #
# 形態係数とラジオシティ
# --------------------------------------------------------------------------- #
def _dist(p, q):
    return np.hypot(p[:, None, 0] - q[None, :, 0], p[:, None, 1] - q[None, :, 1])


def _crossed_strings(geo):
    a, b, L = geo["a"], geo["b"], geo["lengths"]
    crossed = _dist(a, a) + _dist(b, b)
    uncrossed = _dist(a, b) + _dist(b, a)
    G = np.maximum(crossed - uncrossed, 0.0)       # 同一直線上のパッチの丸め屑(±1e-16)を 0 に
    np.fill_diagonal(G, 0.0)
    F = G / (2.0 * L[:, None])
    # 開口(最後の頂点 → 最初の頂点)へ。周回の順は a_i, b_i, …, A, B。
    A, B = geo["vertices"][-1], geo["vertices"][0]
    da_A, db_B = np.hypot(*(a - A).T), np.hypot(*(b - B).T)
    da_B, db_A = np.hypot(*(a - B).T), np.hypot(*(b - A).T)
    F_open = np.maximum((da_A + db_B) - (da_B + db_A), 0.0) / (2.0 * L)
    return F, F_open


def form_factors_2d(profile):
    """Patch-to-patch form factors of a concave 2-D (extruded) cross-section by Hottel's crossed-strings rule.

    For strips ``i`` and ``j`` of an extruded surface that see each other
    unobstructed (always true on a concave cross-section),
    ``F_ij = [(crossed strings) − (uncrossed strings)] / (2 L_i)`` — the
    fraction of the energy leaving strip ``i`` that lands on strip ``j``.
    Exact (no quadrature); reciprocity ``L_i F_ij = L_j F_ji`` holds by
    construction, ``F_ii = 0`` for flat patches, and each row plus the
    form factor to the opening sums to 1 (the closed polygon is an enclosure).

    *profile* is a ``table`` from :func:`groove_profile`. Returns the
    ``(P, P)`` matrix (``matrix``).

    **Raises** ``ValueError``: *profile* is not a ``groove_profile`` table or
    its vertices are not a concave function ``z(x)``.
    """
    F, _ = _crossed_strings(_profile(profile, "form_factors_2d"))
    return F


def transport_matrix_radiosity(profile, albedo=0.8, n_bounces=None):
    """Light-transport matrix of a Lambertian concave cross-section: radiosity B = T E with T = (I − diag(ρ)F)^-1 diag(ρ).

    The radiosity equation ``B = ρ E + ρ F B`` (``E`` = irradiance from the
    projector, ``F`` from :func:`form_factors_2d`) is solved for the matrix
    that maps any irradiance pattern to the radiosity the camera sees. The
    direct part is ``diag(ρ)``; everything else is global (interreflection).

    *albedo* is a scalar or one value per patch, each in ``[0, 1)``.
    *n_bounces* ``None`` solves exactly; an integer ``k >= 0`` returns the
    Neumann partial sum ``Σ_{m<=k} (diag(ρ)F)^m diag(ρ)`` — light that has
    bounced at most ``k`` times between patches (``0`` = direct only).

    Returns a dict (a ``table``) with ``kind = "lt_transport"``, ``transport``
    (P, P), ``direct`` (P,) = the diagonal direct part ``ρ``, ``albedo``,
    ``form_factors``, ``opening_form_factors`` (P,), ``n_bounces``,
    ``gain_bound`` = ``max_i ρ_i Σ_j F_ij`` (< 1, bounds the Neumann series)
    and the ``profile``.

    **Raises** ``ValueError``: not a ``groove_profile`` table; an albedo outside
    ``[0, 1)``, non-finite, or of the wrong length; *n_bounces* not ``None`` or
    an integer in ``[0, 10000]``.
    """
    op = "transport_matrix_radiosity"
    geo = _profile(profile, op)
    P = geo["n"]
    rho = _real(albedo, "albedo", op)
    if rho.ndim == 0:
        rho = np.full(P, float(rho))
    if rho.shape != (P,):
        raise ValueError("%s: albedo must be a scalar or (%d,) per patch, got shape %s" % (op, P, rho.shape))
    if (rho < 0.0).any() or (rho >= 1.0).any():
        raise ValueError("%s: albedo must be in [0, 1) (an albedo of 1 makes the enclosure lossless "
                         "only through its opening), got range [%g, %g]" % (op, rho.min(), rho.max()))
    if n_bounces is not None:
        n_bounces = _int(n_bounces, "n_bounces", op, 0, 10000)
    F, F_open = _crossed_strings(geo)
    K = rho[:, None] * F
    if n_bounces is None:
        T = np.linalg.solve(np.eye(P) - K, np.diag(rho))
    else:
        T = np.diag(rho)
        term = T
        for _ in range(n_bounces):
            term = K @ term
            T = T + term
    return {"kind": TRANSPORT_KIND, "transport": T, "direct": rho.copy(), "albedo": rho.copy(),
            "form_factors": F, "opening_form_factors": F_open, "n_bounces": n_bounces,
            "gain_bound": float((rho * F.sum(axis=1)).max()), "profile": profile}


# --------------------------------------------------------------------------- #
# 投影パターン
# --------------------------------------------------------------------------- #
def high_frequency_patterns(shape=(1, 256), period=8, kind="stripes", fill=0.5, n_shifts=None,
                            complement=False):
    """Shifted high-frequency projector patterns: binary stripes with fill ratio α, a checkerboard, or phase-shifted sinusoids (one or several periods).

    *shape* ``(H, W)`` is the projector frame; ``x`` is the column index.

    * ``"stripes"`` — ``1`` where ``(x − s_k) mod period < α·period``, for
      shifts ``s_k = floor(k·period/n_shifts)``; *period* an integer ``>= 2``
      and ``α·period`` must be a whole number of pixels (the realised fill is
      then exactly α — a rounded fill would bias the separation). Default
      ``n_shifts = period`` (every pixel is lit and unlit at least once).
      *complement* appends ``1 − p`` for each pattern (Nayar et al. eq. 7).
    * ``"checker"`` — squares of side ``period/2`` (``α = 0.5``), shifted by
      ``floor(k·period/n_shifts)`` in both axes (``n_shifts²`` images, default
      ``n_shifts = min(period, 5)``). Not a 2-D problem, so
      :func:`render_transport` refuses it; it is for real captures.
    * ``"sinusoid"`` — ``0.5 + 0.5 cos(2π x / period − 2π n / N)``,
      ``n = 0..N−1``, ``N = n_shifts`` (default 4, ``>= 3``) — the sign
      convention of ``fringe.wrapped_phase``, which returns ``2π x / period``.
      *period* may be a sequence (a micro phase-shifting set): the stacks are
      concatenated in that order. *fill* must stay 0.5 here.

    Returns a list of ``(H, W)`` float arrays in ``[0, 1]`` (``images``).

    **Raises** ``ValueError``: bad *shape*; unknown *kind*; *period* out of
    range (stripes/checker integer ``>= 2``, checker even; sinusoid ``> 2``);
    *fill* outside ``(0, 1)`` or not a whole number of pixels per period
    (checker and sinusoid: not 0.5); *n_shifts* out of range; *complement*
    with a kind other than stripes.
    """
    op = "high_frequency_patterns"
    try:
        H, W = (int(shape[0]), int(shape[1])) if len(shape) == 2 else (None, None)
    except (TypeError, ValueError):
        H = W = None
    if H is None or isinstance(shape, str) or H < 1 or W < 1 or H * W > MAX_PIXELS:
        raise ValueError("%s: shape must be (H, W) with H, W >= 1 and H*W <= %d, got %r" % (op, MAX_PIXELS, shape))
    if not isinstance(kind, str) or kind not in ("stripes", "checker", "sinusoid"):
        raise ValueError("%s: kind must be stripes/checker/sinusoid, got %r" % (op, kind))
    alpha = _num(fill, "fill", op, lo=0.0, hi=1.0, lo_open=True, hi_open=True)
    if complement and kind != "stripes":
        raise ValueError("%s: complement is only defined for kind='stripes'" % op)
    x = np.arange(W)
    if kind == "sinusoid":
        if alpha != 0.5:
            raise ValueError("%s: a sinusoid has no fill ratio; leave fill=0.5, got %g" % (op, alpha))
        periods = np.atleast_1d(np.asarray(period, dtype=object))
        N = 4 if n_shifts is None else _int(n_shifts, "n_shifts", op, 3, 64)
        out = []
        for p in periods:
            pv = _num(p, "period", op, lo=2.0, lo_open=True)
            for n in range(N):
                row = 0.5 + 0.5 * np.cos(2.0 * np.pi * x / pv - 2.0 * np.pi * n / N)
                out.append(np.repeat(row[None, :], H, axis=0))
        return out
    p = _int(period, "period", op, 2, 1 << 16)
    if kind == "checker":
        if p % 2:
            raise ValueError("%s: a checker period must be even (square side = period/2), got %d" % (op, p))
        if alpha != 0.5:
            raise ValueError("%s: a checkerboard has fill 0.5, got %g" % (op, alpha))
        N = min(p, 5) if n_shifts is None else _int(n_shifts, "n_shifts", op, 1, p)
        yy, xx = np.mgrid[0:H, 0:W]
        out = []
        for ky in range(N):
            sy = (ky * p) // N
            for kx in range(N):
                sx = (kx * p) // N
                out.append((((xx - sx) % p < p // 2) ^ ((yy - sy) % p < p // 2)).astype(np.float64))
        return out
    lit = alpha * p
    if abs(lit - round(lit)) > 1e-9 or not (1 <= round(lit) <= p - 1):
        raise ValueError("%s: fill*period must be a whole number of pixels in [1, period-1] "
                         "(fill %g, period %d gives %g)" % (op, alpha, p, lit))
    lit = int(round(lit))
    N = p if n_shifts is None else _int(n_shifts, "n_shifts", op, 1, p)
    out = []
    for k in range(N):
        s = (k * p) // N
        row = (((x - s) % p) < lit).astype(np.float64)
        out.append(np.repeat(row[None, :], H, axis=0))
    if complement:
        out = out + [1.0 - f for f in out]
    return out


# --------------------------------------------------------------------------- #
# 描画(順方向)
# --------------------------------------------------------------------------- #
def _projector(geo, beta_deg, wp, op):
    """プロジェクタ座標の足跡: 各パッチの n·d と、プロジェクタ画素への重なり (P, wp)。"""
    beta = math.radians(_num(beta_deg, "triangulation_deg", op, lo=0.0, hi=80.0, lo_open=True))
    d = np.array([math.sin(beta), math.cos(beta)])
    cos_i = geo["normals"] @ d
    if (cos_i <= 1e-9).any():
        k = int(np.argmin(cos_i))
        raise ValueError("%s: patch %d faces away from (or is grazed by) the projector at %.1f degrees — "
                         "it would be in shadow; reduce triangulation_deg" % (op, k, math.degrees(beta)))
    v = geo["vertices"]
    u = v[:, 0] * math.cos(beta) - v[:, 1] * math.sin(beta)      # n·d > 0 ⇔ u が単調増加(影が無い)
    u0, span = float(u[0]), float(u[-1] - u[0])
    pitch = span / wp
    lo = u0 + pitch * np.arange(wp)
    hi = lo + pitch
    ua, ub = u[:-1], u[1:]
    ov = np.clip(np.minimum(ub[:, None], hi[None, :]) - np.maximum(ua[:, None], lo[None, :]), 0.0, None)
    Wm = ov / (ub - ua)[:, None]
    return {"beta": beta, "cos": cos_i, "W": Wm, "u0": u0, "pitch": pitch, "u": u}


def render_transport(transport, patterns, triangulation_deg=20.0, irradiance=1.0, black_level=0.0, rows=1):
    """Render camera images of a concave Lambertian cross-section under projector patterns, through the light-transport matrix (direct + interreflection).

    The orthographic projector is tilted *triangulation_deg* from the
    vertical towards ``+x``; its frame (the pattern width ``W_p``) spans the
    cross-section exactly, and each patch is lit by the average of the
    projector pixels inside its footprint, times ``n·d`` and *irradiance*.
    A deactivated projector pixel still emits *black_level* (Nayar's ``b``).
    The radiosity ``B = T E`` is the camera image: one column per patch,
    repeated over *rows* rows (the groove axis).

    *transport* is a ``table`` from :func:`transport_matrix_radiosity` (pass
    ``n_bounces=0`` for the direct-only truth). *patterns* (``images``) must
    be constant along each column (stripes or fringes parallel to the groove):
    the 2-D transport is exact only then.

    Returns a list of ``(rows, P)`` images (``images``).

    **Raises** ``ValueError``: not a transport table; patterns empty, non-finite,
    outside ``[0, 1]`` or varying along the groove axis (a checkerboard);
    *triangulation_deg* outside ``(0, 80]`` or a patch facing away from the
    projector (it would be in shadow); *irradiance* ``<= 0``; *black_level*
    outside ``[0, 1)``; *rows* not an integer in ``[1, 4096]``.
    """
    op = "render_transport"
    geo, T, _, _ = _transport(transport, op)
    pats = _stack(patterns, op, "patterns")
    if (pats < 0.0).any() or (pats > 1.0).any():
        raise ValueError("%s: projector patterns must be in [0, 1]" % op)
    if pats.shape[1] > 1 and np.ptp(pats, axis=1).max() > 1e-12:
        raise ValueError("%s: patterns vary along the groove axis (rows) — the 2-D transport is exact only "
                         "for stripes or fringes parallel to the groove; a checkerboard is a 3-D problem" % op)
    I0 = _num(irradiance, "irradiance", op, lo=0.0, lo_open=True)
    b = _num(black_level, "black_level", op, lo=0.0, hi=1.0, hi_open=True)
    rows = _int(rows, "rows", op, 1, 4096)
    pj = _projector(geo, triangulation_deg, pats.shape[2], op)
    drive = b + (1.0 - b) * pats[:, 0, :]                        # (K, W_p)
    E = I0 * pj["cos"][None, :] * (drive @ pj["W"].T)            # (K, P)
    B = E @ T.T
    return [np.repeat(r[None, :], rows, axis=0) for r in B]


# --------------------------------------------------------------------------- #
# 直接・大域の分離(Nayar ら 2006)
# --------------------------------------------------------------------------- #
def separate_direct_global(images, fill=0.5, black_level=0.0, scheme="shift"):
    """Separate direct and global (interreflection) components from images under shifted high-frequency patterns, from per-pixel L_max and L_min (Nayar et al. 2006).

    With a fraction α of the projector lit in a pattern of high frequency,
    a pixel whose scene point is lit sees ``L_d + α L_g`` (the global part
    only depends on the average power when it is smooth over the pattern
    period) and an unlit one sees only the global part.

    * ``scheme="shift"`` — every image is the same pattern (fill α) shifted:
      ``L_max = L_d + (α + b(1−α)) L_g``, ``L_min = b L_d + (α + b(1−α)) L_g``,
      so ``L_d = (L_max − L_min)/(1 − b)``.
    * ``scheme="complement"`` — a pattern and its complement (Nayar et al.
      eq. 8): ``L_max = L_d + (α + b(1−α)) L_g``,
      ``L_min = b L_d + (1 − α + αb) L_g`` (assumes ``L_max`` is the lit image).

    Both reduce to ``L_d = L_max − L_min``, ``L_g = 2 L_min`` for α = 0.5,
    b = 0. *black_level* ``b`` is the relative brightness of an unlit
    projector pixel.

    Returns a dict (a ``table``) with ``direct``, ``global``, ``l_max``,
    ``l_min`` (each ``(H, W)``).

    **Raises** ``ValueError``: fewer than 2 images, non-2-D or non-finite;
    *fill* outside ``(0, 1)``; *black_level* outside ``[0, 1)``; unknown
    *scheme*.
    """
    op = "separate_direct_global"
    st = _stack(images, op, min_n=2)
    a = _num(fill, "fill", op, lo=0.0, hi=1.0, lo_open=True, hi_open=True)
    b = _num(black_level, "black_level", op, lo=0.0, hi=1.0, hi_open=True)
    if scheme not in ("shift", "complement"):
        raise ValueError("%s: scheme must be 'shift' or 'complement', got %r" % (op, scheme))
    lmax, lmin = st.max(axis=0), st.min(axis=0)
    g_hi = a + b * (1.0 - a)
    if scheme == "shift":
        ld = (lmax - lmin) / (1.0 - b)
        lg = (lmin - b * ld) / g_hi
    else:
        g_lo = (1.0 - a) + a * b
        det = g_lo - b * g_hi                                   # = (1 − α)(1 − b²) > 0
        ld = (g_lo * lmax - g_hi * lmin) / det
        lg = (lmin - b * lmax) / det
    return {"direct": ld, "global": lg, "l_max": lmax, "l_min": lmin}


# --------------------------------------------------------------------------- #
# 位相のバイアス(縞)
# --------------------------------------------------------------------------- #
def _wrap(p):
    return np.angle(np.exp(1j * p))


def fringe_multipath_phase_error(direct_amplitude, direct_phase, global_amplitude, global_phase):
    """Phase measured when a direct fringe phasor and a global phasor add: arg(a1 e^{iφ1} + a2 e^{iφ2}), its bias against φ1, and the worst case asin(a2/a1).

    Phase shifting decodes the phase of the sum of every light path reaching
    the pixel (Gupta & Nayar 2012, eqs. 6–11): with a direct amplitude
    ``a1`` at the true phase ``φ1`` and a global phasor ``a2 e^{iφ2}``,
    the decoded phase is ``arg(a1 e^{iφ1} + a2 e^{iφ2})`` and the bias is
    ``atan2(r sin Δ, 1 + r cos Δ)`` with ``r = a2/a1``, ``Δ = φ2 − φ1``.
    Over all ``Δ`` its magnitude peaks at ``asin(r)`` when ``r < 1``; for
    ``r >= 1`` any bias up to π is possible.

    Inputs broadcast (scalars or arrays; phases in radians).

    Returns a dict (a ``table``): ``phase`` (wrapped to ``(-π, π]``),
    ``bias`` (``(-π, π]``), ``amplitude`` (``|sum|``), ``ratio`` (``a2/a1``)
    and ``worst_case`` (``asin(min(r, 1))``, π where ``r >= 1``).

    **Raises** ``ValueError``: non-finite inputs, a negative amplitude or a
    zero direct amplitude, shapes that do not broadcast.
    """
    op = "fringe_multipath_phase_error"
    a1 = _real(direct_amplitude, "direct_amplitude", op)
    p1 = _real(direct_phase, "direct_phase", op)
    a2 = _real(global_amplitude, "global_amplitude", op)
    p2 = _real(global_phase, "global_phase", op)
    try:
        a1, p1, a2, p2 = np.broadcast_arrays(a1, p1, a2, p2)
    except ValueError:
        raise ValueError("%s: the four inputs do not broadcast to one shape" % op) from None
    if (a1 <= 0.0).any() or (a2 < 0.0).any():
        raise ValueError("%s: the direct amplitude must be > 0 and the global amplitude >= 0" % op)
    s = a1 * np.exp(1j * p1) + a2 * np.exp(1j * p2)
    r = a2 / a1
    worst = np.where(r < 1.0, np.arcsin(np.clip(r, 0.0, 1.0)), np.pi)
    return {"phase": np.angle(s), "bias": _wrap(np.angle(s) - p1), "amplitude": np.abs(s),
            "ratio": r, "worst_case": worst}


def predict_fringe_phase_error(transport, period=16.0, triangulation_deg=20.0, projector_width=None,
                               irradiance=1.0):
    """Predict, per camera pixel, the fringe-phase bias and height error that interreflection causes in phase-shifting profilometry, from the light-transport matrix.

    A sinusoid of *period* projector pixels illuminates patch ``i`` with the
    complex amplitude ``ζ_i = n_i·d · mean_footprint(e^{i 2π x / period})``.
    The camera sees ``Z = T (irradiance · ζ)``; its direct part is
    ``ρ_i · irradiance · ζ_i`` and the rest is the global phasor. The decoded
    phase is the argument of the sum (:func:`fringe_multipath_phase_error`).
    The height error follows from ``u = x cos β − z sin β``:
    ``Δz = −Δu / sin β`` with ``Δu = bias · period · pitch / (2π)``
    (*pitch* = projector pixel in scene units).

    *transport* from :func:`transport_matrix_radiosity`;
    *projector_width* (default: the number of patches) must match the pattern
    width given to :func:`render_transport` for the two to agree.

    Returns a dict (a ``table``): ``bias`` (rad, (P,)), ``height_error``
    (scene units, (P,)), ``direct_amplitude``, ``direct_phase``,
    ``global_amplitude``, ``global_phase``, ``ratio``, ``worst_case``,
    ``pitch`` and ``x`` (patch centres).

    **Raises** ``ValueError``: not a transport table; *period* ``<= 2``;
    *triangulation_deg* outside ``(0, 80]`` or a shadowed patch;
    *projector_width* not an integer in ``[2, 1<<16]``; *irradiance* ``<= 0``.
    """
    op = "predict_fringe_phase_error"
    geo, T, rho, _ = _transport(transport, op)
    p = _num(period, "period", op, lo=2.0, lo_open=True)
    wp = geo["n"] if projector_width is None else _int(projector_width, "projector_width", op, 2, 1 << 16)
    I0 = _num(irradiance, "irradiance", op, lo=0.0, lo_open=True)
    pj = _projector(geo, triangulation_deg, wp, op)
    zeta = pj["W"] @ np.exp(2j * np.pi * np.arange(wp) / p)
    A = I0 * pj["cos"] * zeta
    Z = T @ A
    Zd = rho * A
    Zg = Z - Zd
    res = fringe_multipath_phase_error(np.abs(Zd), np.angle(Zd), np.abs(Zg), np.angle(Zg))
    du = res["bias"] * p * pj["pitch"] / (2.0 * np.pi)
    return {"bias": res["bias"], "height_error": -du / math.sin(pj["beta"]),
            "direct_amplitude": np.abs(Zd), "direct_phase": np.angle(Zd),
            "global_amplitude": np.abs(Zg), "global_phase": np.angle(Zg),
            "ratio": res["ratio"], "worst_case": res["worst_case"], "pitch": pj["pitch"],
            "x": geo["centers"][:, 0].copy()}


# --------------------------------------------------------------------------- #
# マイクロ位相シフトの復号
# --------------------------------------------------------------------------- #
def micro_phase_decode(images, periods=(14.0, 15.0, 16.0), n_shifts=4):
    """Decode a narrow-band high-frequency fringe set (micro phase shifting, Gupta & Nayar 2012) into an absolute projector coordinate, ordering the fringes by the beat of the first two periods.

    *images* is the concatenation of ``n_shifts`` phase-shifted sinusoids per
    period (as :func:`high_frequency_patterns` with ``kind="sinusoid"`` and a
    sequence of periods returns them). Each period is decoded with
    ``fringe.wrapped_phase``; the beat ``φ1 − φ2`` of the first two periods
    is a synthetic fringe of period ``p1 p2 / |p1 − p2|``, which fixes the
    fringe order of every period; the coordinate is the mean over periods.
    Because every period is short, the global light seen by a pixel is nearly
    the same in all frames and barely moves the phase. (Gupta & Nayar solve
    ``F + 2`` images jointly and order with Gushov–Solodkin; neither is
    implemented here.)

    Returns a dict (a ``table``): ``coordinate`` ``(H, W)`` in projector
    pixels, unambiguous over ``[0, synthetic_period)``; ``wrapped_phase``
    ``(F, H, W)``; ``coarse`` (the beat estimate); ``synthetic_period``.

    **Raises** ``ValueError``: images not ``len(periods) * n_shifts`` finite
    2-D frames of one shape; fewer than 2 periods, a period ``<= 2``, or the
    first two equal; *n_shifts* not an integer in ``[3, 64]``.
    """
    op = "micro_phase_decode"
    per = [_num(p, "period", op, lo=2.0, lo_open=True) for p in np.atleast_1d(np.asarray(periods, dtype=object))]
    if len(per) < 2:
        raise ValueError("%s: need at least 2 periods to order the fringes, got %d" % (op, len(per)))
    if per[0] == per[1]:
        raise ValueError("%s: the first two periods must differ (their beat orders the fringes)" % op)
    N = _int(n_shifts, "n_shifts", op, 3, 64)
    st = _stack(images, op, min_n=3)
    if st.shape[0] != N * len(per):
        raise ValueError("%s: expected %d images (%d periods x %d shifts), got %d"
                         % (op, N * len(per), len(per), N, st.shape[0]))
    phases = np.stack([fringe.wrapped_phase(st[f * N:(f + 1) * N]) for f in range(len(per))])
    p1, p2 = per[0], per[1]
    ps = p1 * p2 / abs(p1 - p2)
    beat = phases[0] - phases[1] if p1 < p2 else phases[1] - phases[0]
    coarse = np.mod(beat, 2.0 * np.pi) / (2.0 * np.pi) * ps
    us = []
    for f, p in enumerate(per):
        uw = np.mod(phases[f], 2.0 * np.pi) / (2.0 * np.pi) * p
        us.append(uw + np.round((coarse - uw) / p) * p)
    return {"coordinate": np.mean(us, axis=0), "wrapped_phase": phases, "coarse": coarse,
            "synthetic_period": ps}


# --------------------------------------------------------------------------- #
# AMCW ToF の多経路
# --------------------------------------------------------------------------- #
def tof_multipath_phase(amplitudes, path_lengths, modulation_hz=20e6):
    """Continuous-wave time-of-flight depth when several light paths reach one pixel: the phase of the phasor sum, and its bias against the direct path.

    Path ``k`` with amplitude ``a_k`` and round-trip length ``L_k`` (metres)
    contributes ``a_k e^{i 2π f L_k / c}``; the sensor reports the phase of the
    sum and converts it to depth ``c φ / (4π f)`` (modulo the ambiguity range
    ``c / (2f)``). Path 0 is the direct one (true depth ``L_0 / 2``). With two
    paths the bias is ``atan2(r sin Δ, 1 + r cos Δ) · c/(4π f)`` (``r = a_1/a_0``,
    ``Δ`` = the extra phase), positive while ``0 < Δ < π``.

    *amplitudes* and *path_lengths* are ``(K, ...)`` (paths first) and
    broadcast against each other.

    Returns a dict (a ``table``): ``phase`` (``[0, 2π)``), ``depth``,
    ``true_depth``, ``bias`` (depth units, from the wrapped phase difference),
    ``amplitude`` and ``ambiguity_range``.

    **Raises** ``ValueError``: non-finite values, fewer than one path, a
    negative amplitude or a zero direct amplitude, a non-positive path length,
    shapes that do not broadcast, *modulation_hz* outside ``(0, 1e10]``.
    """
    op = "tof_multipath_phase"
    a = _real(amplitudes, "amplitudes", op)
    L = _real(path_lengths, "path_lengths", op)
    f = _num(modulation_hz, "modulation_hz", op, lo=0.0, hi=1e10, lo_open=True)
    if a.ndim == 0 or L.ndim == 0:
        raise ValueError("%s: amplitudes and path_lengths must have a leading path axis" % op)
    try:
        a, L = np.broadcast_arrays(a, L)
    except ValueError:
        raise ValueError("%s: amplitudes %s and path_lengths %s do not broadcast"
                         % (op, np.shape(amplitudes), np.shape(path_lengths))) from None
    if (a < 0.0).any() or (a[0] <= 0.0).any():
        raise ValueError("%s: amplitudes must be >= 0 and the direct (first) path > 0" % op)
    if (L <= 0.0).any():
        raise ValueError("%s: path lengths must be > 0" % op)
    k = 2.0 * np.pi * f / C_LIGHT
    s = (a * np.exp(1j * k * L)).sum(axis=0)
    ph = np.mod(np.angle(s), 2.0 * np.pi)
    scale = C_LIGHT / (4.0 * np.pi * f)
    return {"phase": ph, "depth": ph * scale, "true_depth": 0.5 * L[0],
            "bias": _wrap(np.angle(s) - k * L[0]) * scale, "amplitude": np.abs(s),
            "ambiguity_range": C_LIGHT / (2.0 * f)}


def tof_transport_depth(transport, camera_xz=(0.0, 1.0), modulation_hz=20e6, n_bounces=None):
    """AMCW time-of-flight depth of a concave Lambertian cross-section (a room corner) with every interreflection delayed by its path length: complex radiosity, per-pixel depth bias.

    The source sits at the camera (*camera_xz*, a line source in 2-D) and
    lights patch ``j`` with ``ρ_j cos_j / r_j · e^{i k r_j}``, ``k = 2π f / c``.
    Each hop ``j → i`` multiplies by ``F_ij e^{i k R_ij}`` (``R_ij`` = centre
    distance), so ``B = (I − diag(ρ)(F ∘ e^{ikR}))^-1 diag(ρ) E`` (or the
    Neumann sum up to *n_bounces* hops); the pixel sees ``B_i e^{i k r_i}``.
    Depth is ``c φ / (4π f)``; truth is ``r_i``. Patches must be small next to
    the modulation wavelength.

    *transport* from :func:`transport_matrix_radiosity` supplies the
    profile, form factors and albedo; the camera must be inside the concave
    region (above the profile, between its ends) so that every patch faces it.

    Returns a dict (a ``table``): ``depth``, ``true_depth``, ``bias`` (from the
    wrapped phase difference), ``direct_amplitude``, ``global_amplitude``,
    ``ratio``, ``x`` (patch centres) and ``ambiguity_range``.

    **Raises** ``ValueError``: not a transport table; *camera_xz* not two finite
    numbers inside the region or a patch facing away from it;
    *modulation_hz* outside ``(0, 1e10]``; *n_bounces* not ``None`` or an
    integer in ``[0, 10000]``.
    """
    op = "tof_transport_depth"
    geo, _, rho, _ = _transport(transport, op)
    cam = _real(camera_xz, "camera_xz", op)
    if cam.shape != (2,):
        raise ValueError("%s: camera_xz must be (x, z), got shape %s" % (op, cam.shape))
    f = _num(modulation_hz, "modulation_hz", op, lo=0.0, hi=1e10, lo_open=True)
    if n_bounces is not None:
        n_bounces = _int(n_bounces, "n_bounces", op, 0, 10000)
    v = geo["vertices"]
    if not (v[0, 0] < cam[0] < v[-1, 0]) or cam[1] <= np.interp(cam[0], v[:, 0], v[:, 1]):
        raise ValueError("%s: the camera must be inside the concave region (above the profile, "
                         "between its ends), got %s" % (op, cam.tolist()))
    c = geo["centers"]
    to_cam = cam[None, :] - c
    r = np.hypot(to_cam[:, 0], to_cam[:, 1])
    cos_i = (geo["normals"] * to_cam).sum(axis=1) / r
    if (cos_i <= 1e-9).any():
        raise ValueError("%s: patch %d faces away from the camera" % (op, int(np.argmin(cos_i))))
    F, _ = _crossed_strings(geo)
    k = 2.0 * np.pi * f / C_LIGHT
    R = _dist(c, c)
    Kc = rho[:, None] * F * np.exp(1j * k * R)
    E = cos_i / r * np.exp(1j * k * r)
    direct = rho * E
    if n_bounces is None:
        B = np.linalg.solve(np.eye(geo["n"]) - Kc, direct)
    else:
        B = direct.copy()
        term = direct
        for _ in range(n_bounces):
            term = Kc @ term
            B = B + term
    seen = B * np.exp(1j * k * r)
    seen_d = direct * np.exp(1j * k * r)
    scale = C_LIGHT / (4.0 * np.pi * f)
    gl = seen - seen_d
    return {"depth": np.mod(np.angle(seen), 2.0 * np.pi) * scale, "true_depth": r,
            "bias": _wrap(np.angle(seen) - 2.0 * k * r) * scale,
            "direct_amplitude": np.abs(seen_d), "global_amplitude": np.abs(gl),
            "ratio": np.abs(gl) / np.abs(seen_d), "x": c[:, 0].copy(),
            "ambiguity_range": C_LIGHT / (2.0 * f)}
