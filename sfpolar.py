# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Shape from polarisation — surface normals of transparent and black-glossy parts from a 4-direction polariser sweep (numpy + scipy).

偏光カメラ(4 方位のオンチップ偏光子を持つセンサ)は、1 ショットで直線偏光の Stokes 量
``S0, S1, S2`` を返す。物体表面で反射・射出した光の偏光は、**面の傾き**で決まる:

  * 偏光度 DoLP は天頂角 θ(法線と視線のなす角)と屈折率 n の関数(Fresnel の式)。
  * 偏光の方位 AoLP は、法線を像面へ落とした向き φ(方位角)で決まる —— 鏡面反射なら
    入射面に**直交**(``ψ = φ + 90°``)、拡散(内部で散乱して出てくる光)なら入射面に
    **平行**(``ψ = φ``)。

透明体(ガラス・樹脂レンズ・バイアル)や黒光沢(黒樹脂・塗装)は拡散成分がほとんど無く、
陰影も模様も乏しいので、照度差ステレオや陰影からの形状復元が拠り所を失う。けれど鏡面
反射の偏光はそこでこそ強い。本モジュールはその逆問題を、**曖昧さを隠さずに**解く。

8 つの op(並びは物理の順):

  * :func:`sfp_dolp_model` — 順方向: 天頂角 → DoLP(鏡面 = Fresnel 反射、拡散 = Fresnel
    透過)。
  * :func:`dolp_to_zenith` — 逆: DoLP → 天頂角の**解の集合**。拡散は単調で 1 解、鏡面は
    Brewster 角 ``θ_B = atan n`` を挟んで 2 解(``ρ = 1`` の 1 点だけ 1 解)。
  * :func:`aolp_to_azimuth` — AoLP → 方位角の 2 候補(π の曖昧さ)。拡散と鏡面で 90° ずれる。
  * :func:`sfp_render` — 法線場 → 4 方位の偏光画像(順方向の描画。鏡面・拡散・混合)。
  * :func:`sfp_normals` — 偏光画像 → 法線の**候補の集合**(拡散 2 本、鏡面 4 本)。
  * :func:`sfp_disambiguate` — 候補から 1 本を選ぶ(凸の事前情報 + Brewster の稜線での
    領域分け、または粗い深度・粗い法線)。
  * :func:`sfp_estimate_index` — 屈折率の推定(DoLP と天頂角の最小二乗、鏡面なら DoLP 最大の
    天頂角から ``n = tan θ_B`` も)。
  * :func:`sfp_height` — 法線 → 高さ(:func:`photometric.integrate_gradients` を鏡像拡張して
    使う。周期境界の歪みを消す)。

座標の約束(**ここを決めないと方位の符号が黙って反転する**):
  * 法線場は ``(H, W, 3)`` の ``(nx, ny, nz)``。x は列方向、y は**行方向**(下向き)、
    +z はカメラへ向く(:mod:`photometric` と同じ規約)。正射影のカメラ(視線は全画素で +z)。
  * 偏光子の角度 t と AoLP ψ は、**x 軸(列方向)から y 軸(行方向)へ回る向き**に測る。
    法線の方位角 ``φ = atan2(ny, nx)`` と同じ向き。表示画像を y 上向きで見て反時計回りに
    角度を振るセンサでは、``angles_deg`` に符号を反転した角度を渡す。
  * 4 枚の順は :data:`optics.POLARIZATION_SWEEP_ANGLES` = (0, 45, 90, 135)、
    :func:`optics.polarization_demosaic` の出力そのまま。

式(導出は本モジュールの docstring とテストで閉じている):
  * 鏡面: ``ρ_s = (R_s − R_p)/(R_s + R_p)``
    ``= 2 sin²θ cosθ √(n² − sin²θ) / (n² − sin²θ − n² sin²θ + 2 sin⁴θ)``。
    ``θ = θ_B`` で分母と分子が等しくなる(``ρ_s = 1``、代数的に厳密)。
  * 拡散: 物体内部から出る光の透過率の偏光差 ``ρ_d = (T_p − T_s)/(T_p + T_s)``、
    ``T = 1 − R``(エネルギー透過率は内外で相反)
    ``= (n − 1/n)² sin²θ / (2 + 2n² − (n + 1/n)² sin²θ + 4 cosθ √(n² − sin²θ))``。
    θ について単調増加で、最大値は ``ρ_d(90°) = (n² − 1)/(n² + 1)``。
  * 画素の強度: ``I(t) = (S0/2)(1 + ρ cos 2(t − ψ))``(Malus の部分偏光版)。

真値(``tests/test_sfpolar.py`` の門):
  * 閉形式の式を、**別の式で書かれた** ``glassmirror.fresnel_dielectric`` の s/p 反射率から
    作った DoLP と照合(鏡面・拡散とも 1e-12)。``match3d.fresnel_reflectance`` は無偏光の
    反射率で、描画の ``S0`` を照合する。
  * 往復: 球・円柱の解析的な法線を ``optics.mueller_element`` / ``mueller_apply`` の Mueller
    行列の経路(本モジュールとは別のコード)で 4 方位画像にし、逆算した法線の角度誤差。

★正直に書いておくこと(限界):
  * 単一の界面・単一の反射。**透明体の裏面反射**(ガラスの裏から戻る光)と相互反射は
    入っていない。実物のガラスでは裏面反射が DoLP を下げ、天頂角を浅く読ませる。
  * 鏡面モデルは「環境からの無偏光の光が一様に当たる」前提(画素に届く反射光の強度は
    問わず、偏光の比だけを使う)。点光源のハイライトの外では反射光そのものが弱く、雑音に
    埋もれる —— 本モジュールは DoLP の比を返すだけで、その画素が使えるかは強度で判断する。
  * 金属(複素屈折率 n + ik)は扱わない(``glassmirror.fresnel_conductor`` の曲線は別物)。
  * 正射影。透視のカメラでは視線が画素ごとに傾き、天頂角は視線基準になる。
  * 拡散と鏡面が混ざった画素は、どちらのモデルで読んでも誤る(位相が 90° ずれた 2 つの
    正弦波の和なので、偏光が打ち消し合う)。:func:`sfp_render` の ``diffuse_radiance`` で
    その誤差を測れるが、混合比を画像から推定する op は無い。

出典: 式は Fresnel の反射・透過係数(M. Born & E. Wolf, *Principles of Optics*, §1.5)
から本モジュールで導き、``glassmirror`` の Fresnel と数値で照合した。閉形式の形は
G. A. Atkinson & E. R. Hancock, "Recovery of surface orientation from diffuse polarization",
*IEEE Trans. Image Processing* 15(6):1653–1664, 2006 で広く引用される形と同じ
(★原論文の本文は読めていない。式は自分で導いて照合したものだけを使う)。鏡面の 2 解を
Brewster の稜線で分ける考えは D. Miyazaki ら(ICCV 2003)に帰されるが、これも本文は
読めていない —— 本モジュールの領域分けの手順は自分で決めたもので、テストで測ってある。
"""
from __future__ import annotations

import math

import numpy as np

__all__ = [
    "sfp_dolp_model",
    "dolp_to_zenith",
    "aolp_to_azimuth",
    "sfp_render",
    "sfp_normals",
    "sfp_disambiguate",
    "sfp_estimate_index",
    "sfp_height",
]

#: 画素数の上限(作業配列を確保する前に拒む)。
MAX_PIXELS = 1 << 24
#: 屈折率の上限(誘電体の現実的な範囲を大きく覆う)。
MAX_INDEX = 10.0
#: 二分法の反復回数(区間 π/2 を 2^-64 まで縮める = float64 の分解能より細かい)。
_BISECT_ITERS = 64
#: 候補の集合であることを示す印(sfp_disambiguate の fail-closed 検査に使う)。
CANDIDATES_KIND = "sfp_candidates"
#: 鏡面の 2 解を 1 解とみなす DoLP(Brewster の頂上)。
_BREWSTER_EPS = 1e-12
_MODELS = ("diffuse", "specular")
_DEFAULT_ANGLES = (0.0, 45.0, 90.0, 135.0)


# --------------------------------------------------------------------------- #
# 入力の検証(fail-closed)
# --------------------------------------------------------------------------- #
def _num(v, name, op, lo=None, hi=None, lo_open=True, hi_open=False):
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


def _index(n, op, name="refractive_index"):
    """屈折率: 実数・有限・1 より大きい(n = 1 では界面が無く偏光も生じない)。材料名なら d 線の n(``materials._index_of``)。"""
    import materials as _mat
    return _num(_mat._index_of(n, op, name), name, op, lo=1.0, hi=MAX_INDEX, lo_open=True)


def _model(model, op, allowed=_MODELS):
    if not isinstance(model, str) or model.strip().lower() not in allowed:
        raise ValueError("%s: model must be one of %s, got %r" % (op, "/".join(allowed), model))
    return model.strip().lower()


def _real(a, name, op, ndim=None):
    """実数の配列(bool / 複素 / 文字列 / マスク / 非有限は拒む)。"""
    if a is None:
        raise ValueError("%s: %s is None" % (op, name))
    if np.ma.is_masked(a):
        raise ValueError("%s: %s is a masked array with masked entries" % (op, name))
    arr = np.asarray(a)
    if arr.dtype.kind not in "iuf":
        raise ValueError("%s: %s must be a real numeric array, got dtype %s" % (op, name, arr.dtype))
    arr = arr.astype(np.float64)
    if ndim is not None and arr.ndim != ndim:
        raise ValueError("%s: %s must be %d-D, got shape %r" % (op, name, ndim, tuple(arr.shape)))
    if arr.size == 0:
        raise ValueError("%s: %s is empty" % (op, name))
    if arr.size > MAX_PIXELS * 4:
        raise ValueError("%s: %s has %d elements, over the cap %d" % (op, name, arr.size, MAX_PIXELS * 4))
    if not np.isfinite(arr).all():
        raise ValueError("%s: %s has %d non-finite value(s)" % (op, name, int((~np.isfinite(arr)).sum())))
    return arr


def _mask(mask, shape, op, name="mask"):
    if mask is None:
        return np.ones(shape, dtype=bool)
    m = np.asarray(mask)
    if m.dtype != bool:
        raise ValueError("%s: %s must be a boolean array, got dtype %s" % (op, name, m.dtype))
    if m.shape != tuple(shape):
        raise ValueError("%s: %s has shape %r, expected %r" % (op, name, tuple(m.shape), tuple(shape)))
    if not m.any():
        raise ValueError("%s: %s selects no pixel" % (op, name))
    return m


def _normal_field(normals, op, name="normals", unit_tol=1e-6):
    """(H, W, 3) の有限な単位法線、+z 側(カメラ向き、nz >= 0)。"""
    n = _real(normals, name, op, ndim=3)
    if n.shape[2] != 3:
        raise ValueError("%s: %s must be (H, W, 3), got shape %r" % (op, name, tuple(n.shape)))
    if n.shape[0] * n.shape[1] > MAX_PIXELS:
        raise ValueError("%s: %s has %d pixels, over the cap %d" % (op, name, n.shape[0] * n.shape[1], MAX_PIXELS))
    ln = np.linalg.norm(n, axis=-1)
    bad = np.abs(ln - 1.0) > unit_tol
    if bad.any():
        raise ValueError("%s: %s has %d non-unit normal(s) (worst length %.6g) — normalise them first"
                         % (op, name, int(bad.sum()), float(ln.flat[int(np.argmax(np.abs(ln - 1.0)))])))
    if (n[..., 2] < -1e-12).any():
        raise ValueError("%s: %s has %d normal(s) facing away from the camera (nz < 0) — a camera "
                         "cannot see a back-facing surface" % (op, name, int((n[..., 2] < -1e-12).sum())))
    return n


# --------------------------------------------------------------------------- #
# 閉形式(DoLP の曲線)
# --------------------------------------------------------------------------- #
def _rho_specular(theta, n):
    s2 = np.sin(theta) ** 2
    c = np.cos(theta)
    root = np.sqrt(np.maximum(n * n - s2, 0.0))
    num = 2.0 * s2 * c * root
    den = n * n - s2 - n * n * s2 + 2.0 * s2 * s2
    return num / den


def _rho_diffuse(theta, n):
    s2 = np.sin(theta) ** 2
    c = np.cos(theta)
    root = np.sqrt(np.maximum(n * n - s2, 0.0))
    num = (n - 1.0 / n) ** 2 * s2
    den = 2.0 + 2.0 * n * n - (n + 1.0 / n) ** 2 * s2 + 4.0 * c * root
    return num / den


def _rho(theta, n, model):
    return _rho_specular(theta, n) if model == "specular" else _rho_diffuse(theta, n)


def _bisect(f, target, lo, hi, increasing):
    """単調な f の f(θ) = target を区間 [lo, hi] で二分法(配列ごと)。"""
    lo = np.broadcast_to(np.asarray(lo, np.float64), target.shape).copy()
    hi = np.broadcast_to(np.asarray(hi, np.float64), target.shape).copy()
    for _ in range(_BISECT_ITERS):
        mid = 0.5 * (lo + hi)
        below = f(mid) < target
        if not increasing:
            below = ~below
        lo = np.where(below, mid, lo)
        hi = np.where(below, hi, mid)
    return 0.5 * (lo + hi)


def sfp_dolp_model(zenith_deg, refractive_index=1.5, model="specular"):
    """Degree of linear polarisation of reflected (specular) or emitted (diffuse) light versus zenith angle, from the Fresnel equations.

    *zenith_deg* is the angle between the surface normal and the viewing
    direction, in degrees, ``0 <= zenith <= 90`` (a scalar or an array of any
    shape — an ``(H, W)`` zenith map gives an ``(H, W)`` DoLP map).

    ``model="specular"``: ``(R_s - R_p) / (R_s + R_p)`` for light reflected off
    a dielectric of index *refractive_index*. It rises from 0 at normal
    incidence to **exactly 1 at Brewster's angle** ``atan(n)`` (``R_p = 0``)
    and falls back to 0 at grazing incidence — so one DoLP value has two
    zenith angles.

    ``model="diffuse"``: ``(T_p - T_s) / (T_p + T_s)`` for light scattered
    inside the body and refracted out through the surface. It rises
    monotonically from 0 to ``(n^2 - 1)/(n^2 + 1)`` at 90 degrees (0.385 for
    n = 1.5) — weaker, but one value has one angle.

    Returns a float64 array of the input's shape (a 0-d array for a scalar).

    **Raises** ``ValueError``: zenith outside ``[0, 90]`` or non-finite;
    *refractive_index* not a finite real ``> 1``; unknown *model*.

    *refractive_index* (here and in every op of this module) may also be a
    material name of the shared table ``materials`` (e.g. ``"N-BK7"``,
    ``"PMMA"``, ``"WATER"``): its index at the d line (587.56 nm) is used.
    Metals and materials that absorb there are refused.
    """
    op = "sfp_dolp_model"
    n = _index(refractive_index, op)
    m = _model(model, op)
    z = _real(zenith_deg, "zenith_deg", op)
    if (z < 0.0).any() or (z > 90.0).any():
        raise ValueError("%s: zenith_deg must be in [0, 90] degrees, got range [%g, %g]"
                         % (op, float(z.min()), float(z.max())))
    rho = _rho(np.radians(z), n, m)
    return np.clip(rho, 0.0, 1.0)


def dolp_to_zenith(dolp, refractive_index=1.5, model="diffuse", out_of_range="clamp"):
    """Invert DoLP to the set of zenith angles that produce it — one for the diffuse model, two (straddling Brewster) for the specular model.

    Returns a dict (a ``table``):

    * ``zenith_deg`` — ``(K, *dolp.shape)``; ``K = 1`` for ``"diffuse"``,
      ``K = 2`` for ``"specular"`` (row 0 = the branch below Brewster's angle,
      row 1 = the branch above it). Where the specular DoLP is 1 (to 1e-12)
      both rows hold Brewster's angle.
    * ``n_solutions`` — integer map: 1 or 2 (specular; 1 only at Brewster),
      1 (diffuse), **0 where no zenith produces the DoLP** — a diffuse DoLP
      above ``(n^2-1)/(n^2+1)``, which noise or a wrong index produces.
    * ``brewster_deg`` (specular) / ``dolp_max`` — the model's limits.

    ``out_of_range`` decides what the unreachable pixels hold: ``"clamp"``
    (default — the nearest reachable angle, 90 degrees for the diffuse model,
    **flagged by** ``n_solutions == 0``, so a caller cannot mistake it for a
    solution), ``"nan"`` or ``"raise"``.

    The inversion is bisection on the monotone branches of
    :func:`sfp_dolp_model`'s closed form (64 halvings — finer than float64).
    Near Brewster's angle the specular curve is flat, so a DoLP rounding error
    of 1e-16 moves the zenith by up to ~1e-6 degrees; that is the conditioning
    of the problem, not of the solver.

    **Raises** ``ValueError``: DoLP outside ``[0, 1]`` or non-finite;
    *refractive_index* not ``> 1``; unknown *model* / *out_of_range*; with
    ``out_of_range="raise"``, any unreachable pixel.
    """
    op = "dolp_to_zenith"
    n = _index(refractive_index, op)
    m = _model(model, op)
    if out_of_range not in ("nan", "clamp", "raise"):
        raise ValueError("%s: out_of_range must be 'nan', 'clamp' or 'raise', got %r" % (op, out_of_range))
    rho = _real(dolp, "dolp", op)
    if (rho < 0.0).any() or (rho > 1.0).any():
        raise ValueError("%s: dolp must be in [0, 1], got range [%.6g, %.6g]"
                         % (op, float(rho.min()), float(rho.max())))
    half = 0.5 * math.pi
    if m == "diffuse":
        rmax = (n * n - 1.0) / (n * n + 1.0)
        reach = rho <= rmax
        if out_of_range == "raise" and not reach.all():
            raise ValueError("%s: %d pixel(s) have a DoLP above the diffuse maximum %.6g for n = %g "
                             "(max %.6g) — wrong index, specular light, or noise"
                             % (op, int((~reach).sum()), rmax, n, float(rho.max())))
        th = _bisect(lambda t: _rho_diffuse(t, n), np.minimum(rho, rmax), 0.0, half, True)
        if out_of_range == "nan":
            th = np.where(reach, th, np.nan)
        out = np.degrees(th)[None]
        nsol = reach.astype(np.int64)
        return {"zenith_deg": out, "n_solutions": nsol, "model": m, "refractive_index": n,
                "dolp_max": float(rmax), "brewster_deg": float(math.degrees(math.atan(n)))}
    tb = math.atan(n)
    low = _bisect(lambda t: _rho_specular(t, n), rho, 0.0, tb, True)
    high = _bisect(lambda t: _rho_specular(t, n), rho, tb, half, False)
    top = rho >= 1.0 - _BREWSTER_EPS
    low = np.where(top, tb, low)
    high = np.where(top, tb, high)
    nsol = np.where(top, 1, 2).astype(np.int64)
    out = np.degrees(np.stack([low, high]))
    return {"zenith_deg": out, "n_solutions": nsol, "model": m, "refractive_index": n,
            "dolp_max": 1.0, "brewster_deg": float(math.degrees(tb))}


def aolp_to_azimuth(aolp_deg, model="diffuse"):
    """Turn the angle of linear polarisation into the two candidate azimuths of the surface normal (the pi ambiguity), diffuse and specular differing by 90 degrees.

    Diffuse light leaves polarised **in** the plane of incidence, so the
    normal's image-plane azimuth is ``phi = psi`` or ``psi + 180``; specular
    reflection is polarised **across** it, so ``phi = psi + 90`` or
    ``psi + 270``. Angles are measured from the image x axis (columns) toward
    the y axis (rows), the same sense as ``atan2(ny, nx)`` of a
    :mod:`photometric` normal map.

    Returns a dict: ``azimuth_deg`` ``(2, *aolp.shape)`` in ``[0, 360)`` (row 1
    is row 0 plus 180), ``offset_deg`` (0 or 90) and ``model``. The pi
    ambiguity is a property of a linear polariser — ``psi`` and ``psi + 180``
    are the same measurement — and no setting of this operator removes it; that
    is :func:`sfp_disambiguate`'s job.

    **Raises** ``ValueError``: non-finite or non-real *aolp_deg*; unknown
    *model*.
    """
    op = "aolp_to_azimuth"
    m = _model(model, op)
    psi = _real(aolp_deg, "aolp_deg", op)
    off = 0.0 if m == "diffuse" else 90.0
    a0 = np.mod(psi + off, 360.0)
    a0 = np.where(a0 >= 360.0, 0.0, a0)
    a1 = np.mod(a0 + 180.0, 360.0)
    return {"azimuth_deg": np.stack([a0, a1]), "offset_deg": off, "model": m}


def _stokes_from_normals(nrm, n, model, radiance):
    """法線場 → (S0, S1, S2)。強度は radiance、DoLP は閉形式、AoLP は方位 + offset。"""
    theta = np.arccos(np.clip(nrm[..., 2], -1.0, 1.0))
    phi = np.arctan2(nrm[..., 1], nrm[..., 0])
    rho = _rho(theta, n, model)
    psi = phi + (0.5 * math.pi if model == "specular" else 0.0)
    s0 = radiance
    return s0, s0 * rho * np.cos(2.0 * psi), s0 * rho * np.sin(2.0 * psi)


def sfp_render(normals, refractive_index=1.5, specular_radiance=1.0, diffuse_radiance=0.0,
               angles_deg=_DEFAULT_ANGLES, mask=None):
    """Render the images a 4-direction polarisation camera records of a dielectric surface with the given normal map (the forward model of shape from polarisation).

    Each pixel is ``I(t) = (S0/2) (1 + rho cos 2(t - psi))`` with ``rho`` from
    :func:`sfp_dolp_model` and ``psi`` the normal's azimuth (diffuse) or the
    azimuth plus 90 degrees (specular). Orthographic camera looking down -z;
    angles in the module's convention (x toward y).

    The pixel is the Stokes sum of a specular part (unpolarised environment
    light reflected once off the surface, radiance *specular_radiance*) and a
    diffuse part (light scattered inside the body and refracted out, radiance
    *diffuse_radiance*). The defaults ``(1, 0)`` give a pure specular surface
    (black gloss, glass); ``(0, 1)`` a pure diffuse one. Anything in between is
    a **mixed** pixel: the two polarisations are 90 degrees apart and partly
    cancel, which is exactly why such a pixel misleads either single model.
    Both radiances are scalars or ``(H, W)`` maps, ``>= 0``, not both zero.
    Pixels outside *mask* are black.

    Returns ``(N, H, W)`` float64 — the ``polsweep`` sort, in the order of
    *angles_deg* (default 0/45/90/135, :func:`optics.polarization_demosaic`'s
    order), ready for :func:`sfp_normals` and the specularity polarisation ops.

    **Raises** ``ValueError``: *normals* not a finite ``(H, W, 3)`` field of
    unit normals facing the camera; index not ``> 1``; negative, non-finite or
    all-zero radiance; fewer than 3 or non-finite angles.
    """
    op = "sfp_render"
    nrm = _normal_field(normals, op)
    n = _index(refractive_index, op)
    H, W = nrm.shape[:2]
    msk = _mask(mask, (H, W), op)

    def _rad(v, name):
        r = _real(v, name, op)
        if r.ndim not in (0, 2) or (r.ndim == 2 and r.shape != (H, W)):
            raise ValueError("%s: %s must be a scalar or an (H, W) map, got shape %r" % (op, name, tuple(r.shape)))
        if (r < 0.0).any():
            raise ValueError("%s: %s must be >= 0 (a negative radiance is not a scene)" % (op, name))
        return np.broadcast_to(r, (H, W))

    rs = _rad(specular_radiance, "specular_radiance")
    rd = _rad(diffuse_radiance, "diffuse_radiance")
    if not (rs.any() or rd.any()):
        raise ValueError("%s: specular_radiance and diffuse_radiance are both zero — there is no light" % op)
    ang = _real(angles_deg, "angles_deg", op, ndim=1)
    if ang.size < 3 or ang.size > 64:
        raise ValueError("%s: angles_deg must hold 3..64 angles, got %d" % (op, ang.size))
    a = _stokes_from_normals(nrm, n, "specular", rs)
    b = _stokes_from_normals(nrm, n, "diffuse", rd)
    s0, s1, s2 = a[0] + b[0], a[1] + b[1], a[2] + b[2]
    t = np.radians(ang)[:, None, None]
    img = 0.5 * (s0[None] + s1[None] * np.cos(2.0 * t) + s2[None] * np.sin(2.0 * t))
    img = np.where(msk[None], np.maximum(img, 0.0), 0.0)
    return np.ascontiguousarray(img, dtype=np.float64)


def _normal_from_angles(theta_deg, phi_deg):
    th = np.radians(theta_deg)
    ph = np.radians(phi_deg)
    s = np.sin(th)
    return np.stack([s * np.cos(ph), s * np.sin(ph), np.cos(th)], axis=-1)


def sfp_normals(sweep, refractive_index=1.5, model="specular", angles_deg=_DEFAULT_ANGLES,
                violation_tol=0.05, out_of_range="invalid"):
    """From a polariser sweep to the explicit set of candidate surface normals per pixel — 2 for the diffuse model, 4 for the specular model (2 zeniths x 2 azimuths).

    *sweep* is an ``(N, H, W)`` stack through linear analysers at *angles_deg*
    (the ``polsweep`` sort; :func:`optics.polarization_demosaic` gives it from a
    raw mosaic). Per pixel the sinusoid ``I(t) = a0 + a1 cos 2t + a2 sin 2t`` is
    fitted (the same least-squares fit as :func:`specularity.polarization_dolp_map`),
    giving ``DoLP = hypot(a1, a2)/a0`` and ``AoLP = 0.5 atan2(a2, a1)``; then
    :func:`dolp_to_zenith` and :func:`aolp_to_azimuth` give the zenith and
    azimuth candidates.

    A fitted minimum below zero (modulation above the mean, DoLP > 1) is
    impossible for light. Near Brewster's angle the true minimum is ~0, so
    sensor noise pushes it slightly negative; *violation_tol* is the largest
    excess ``DoLP - 1`` that is read as noise (DoLP clipped to 1). A larger
    excess marks the pixel **invalid** — the frames do not match *angles_deg*,
    or the pixel saw something other than a polariser sweep. Such a pixel is
    reported in ``violation``, never silently clipped.
    (:func:`specularity.polarization_dolp_map` refuses the whole image instead;
    a shape map with one hot pixel is still a shape map, so here the decision
    is per pixel and :func:`sfp_disambiguate` refuses invalid pixels inside its
    mask by default.)

    *out_of_range*: a DoLP that no zenith produces (diffuse model, above
    ``(n^2-1)/(n^2+1)``) makes the pixel ``"invalid"`` (default) or is
    ``"clamp"``-ed to the reachable limit and kept, flagged in ``clamped``.

    Returns a dict (a ``table``, marked ``kind == "sfp_candidates"``):

    * ``candidates`` ``(K, H, W, 3)`` unit normals; specular order is
      ``[low zenith & azimuth 0, low & azimuth 1, high & azimuth 0, high &
      azimuth 1]``, diffuse ``[azimuth 0, azimuth 1]``. Zero vectors at
      invalid pixels (see ``valid``) — never NaN, never a made-up unit normal.
    * ``zenith_deg`` ``(1|2, H, W)``, ``azimuth_deg`` ``(2, H, W)``,
      ``dolp``, ``aolp_deg``, ``intensity`` (``S0``) ``(H, W)``.
    * ``n_distinct`` ``(H, W)`` — how many genuinely different normals the
      pixel admits: 4 (specular), 2 at Brewster's angle or for the diffuse
      model, 0 where nothing fits or the pixel is dark.
    * ``valid`` ``(H, W)`` bool — lit, physically possible and invertible;
      ``violation`` / ``clamped`` ``(H, W)`` bool — why a pixel is suspect.
    * ``model``, ``refractive_index``, ``brewster_deg``.

    Nothing here chooses among the candidates; a single "best" normal map
    returned at this stage would be a guess dressed as a measurement.

    **Raises** ``ValueError``: not an ``(N, H, W)`` stack of >= 3 finite
    non-negative frames; angles that do not match or do not determine the fit;
    *violation_tol* outside ``[0, 1]``; index not ``> 1``; unknown *model* /
    *out_of_range*.
    """
    op = "sfp_normals"
    import specularity as _sp                      # noqa: PLC0415 — 同じ正弦波の当てはめを再利用する
    n = _index(refractive_index, op)
    m = _model(model, op)
    if out_of_range not in ("invalid", "clamp"):
        raise ValueError("%s: out_of_range must be 'invalid' or 'clamp', got %r" % (op, out_of_range))
    stack = _real(sweep, "sweep", op, ndim=3)
    if stack.shape[0] < 3:
        raise ValueError("%s: sweep needs at least 3 analyser angles, got %d frames" % (op, stack.shape[0]))
    if (stack < 0.0).any():
        raise ValueError("%s: sweep has %d negative value(s) — radiance through an analyser cannot be "
                         "negative" % (op, int((stack < 0.0).sum())))
    if stack.shape[1] * stack.shape[2] > MAX_PIXELS:
        raise ValueError("%s: %d pixels, over the cap %d" % (op, stack.shape[1] * stack.shape[2], MAX_PIXELS))
    vt = _num(violation_tol, "violation_tol", op, lo=0.0, hi=1.0, lo_open=False)
    # 当てはめは specularity と同じもの。負の最小値の判定は画素ごとにここで行うので 1.0 で渡す。
    a0, a1, a2, amp, _imin, (H, W) = _sp._polar_fit(stack, angles_deg, op, 1.0)
    lit = a0 > 0.0
    dolp = np.zeros_like(a0)
    np.divide(amp, a0, out=dolp, where=lit)
    violation = (lit & (dolp > 1.0 + vt)).reshape(H, W)
    dolp = np.clip(dolp, 0.0, 1.0).reshape(H, W)
    aolp = np.degrees(np.mod(0.5 * np.arctan2(a2, a1), math.pi)).reshape(H, W)
    zen = dolp_to_zenith(dolp, n, m, out_of_range="clamp")
    az = aolp_to_azimuth(aolp, m)
    zd, ad = zen["zenith_deg"], az["azimuth_deg"]
    cands = [_normal_from_angles(z, a) for z in zd for a in ad]
    cand = np.stack(cands)
    lit2 = lit.reshape(H, W)
    clamped = lit2 & (zen["n_solutions"] == 0)
    valid = lit2 & ~violation
    if out_of_range == "invalid":
        valid &= ~clamped
    cand = np.where(valid[None, ..., None], cand, 0.0)
    n_distinct = np.where(valid, 2 * np.maximum(zen["n_solutions"], 1), 0).astype(np.int64)
    return {"kind": CANDIDATES_KIND, "candidates": cand, "zenith_deg": zd, "azimuth_deg": ad,
            "dolp": dolp, "aolp_deg": aolp, "intensity": (2.0 * a0).reshape(H, W),
            "n_distinct": n_distinct, "valid": valid, "violation": violation, "clamped": clamped,
            "model": m, "refractive_index": n, "brewster_deg": zen["brewster_deg"]}


def _check_candidates(c, op):
    if not isinstance(c, dict) or c.get("kind") != CANDIDATES_KIND:
        raise ValueError("%s: candidates must be the dict returned by sfp_normals (kind == %r)"
                         % (op, CANDIDATES_KIND))
    for k in ("candidates", "zenith_deg", "azimuth_deg", "dolp", "valid", "model"):
        if k not in c:
            raise ValueError("%s: candidates is missing key %r" % (op, k))
    cand = np.asarray(c["candidates"], dtype=np.float64)
    if cand.ndim != 4 or cand.shape[-1] != 3 or cand.shape[0] not in (2, 4):
        raise ValueError("%s: candidates['candidates'] must be (2|4, H, W, 3), got %r" % (op, tuple(cand.shape)))
    H, W = cand.shape[1:3]
    for k in ("dolp", "valid"):
        if np.shape(c[k]) != (H, W):
            raise ValueError("%s: candidates[%r] has shape %r, expected %r" % (op, k, np.shape(c[k]), (H, W)))
    model = c["model"]
    if model not in _MODELS or (model == "specular") != (cand.shape[0] == 4):
        raise ValueError("%s: candidates model %r does not match %d candidates" % (op, model, cand.shape[0]))
    return cand, H, W


def sfp_disambiguate(candidates, prior="convex", mask=None, center=None, prior_normals=None,
                     coarse_depth=None, brewster_tol=0.02, invalid="raise"):
    """Pick one normal per pixel from the candidate set of :func:`sfp_normals`, using a stated prior — convexity with Brewster-ridge segmentation, or a coarse depth / normal map.

    ``prior="convex"`` (an object bulging toward the camera, such as a dome,
    a lens or a cap): the azimuth is the candidate pointing **away from**
    *center* (default: the centroid of *mask*). For the specular model the two
    zenith branches are separated by the **Brewster ridge** — the pixels whose
    DoLP is within *brewster_tol* of 1: the connected region of the mask that
    contains *center* (minus the ridge) takes the branch below Brewster's angle,
    the rest of the mask the branch above. Inside the ridge band the branch is
    read from the radial slope of the DoLP (a convex surface tilts more toward
    its rim, so the DoLP rises outward below Brewster's angle and falls outward
    above it). If the object never reaches Brewster's
    angle there is no ridge and every pixel stays on the low branch, which is
    right for a shallow dome. If noise breaks the ridge, the outside leaks in
    and takes the low branch — measured in the tests, not hidden.

    ``prior="normals"`` / ``prior="depth"``: per pixel, the candidate closest
    in angle to *prior_normals* ``(H, W, 3)`` — or to the normals of
    *coarse_depth* ``(H, W)`` (height toward the camera, pixel units,
    :func:`photometric.surface_normals`). This resolves both ambiguities at
    once, and a coarse depth needs to be right only to within the angular
    distance between candidates.

    Pixels outside *mask* (default ``candidates["valid"]``) are set to
    ``(0, 0, 1)`` (flat background, the convention of
    :func:`photometric.integrate_normals`). Invalid pixels inside the mask
    (``valid`` is False: dark, physically impossible, or out of the model's
    reach): ``invalid="raise"`` refuses (fail-closed), ``"exclude"`` drops them
    to the background.

    Returns an ``(H, W, 3)`` float64 unit normal map (the ``normalmap`` sort).

    **Raises** ``ValueError``: *candidates* not an :func:`sfp_normals`
    result; unknown *prior* / *invalid*; a prior's array missing or of the
    wrong shape; an empty mask; invalid pixels inside the mask with
    ``invalid="raise"``.
    """
    op = "sfp_disambiguate"
    cand, H, W = _check_candidates(candidates, op)
    if prior not in ("convex", "normals", "depth"):
        raise ValueError("%s: prior must be 'convex', 'normals' or 'depth', got %r" % (op, prior))
    if invalid not in ("raise", "exclude"):
        raise ValueError("%s: invalid must be 'raise' or 'exclude', got %r" % (op, invalid))
    valid = np.asarray(candidates["valid"], dtype=bool)
    msk = valid.copy() if mask is None else _mask(mask, (H, W), op).copy()
    if not np.isfinite(cand).all():
        raise ValueError("%s: candidates hold non-finite values — not an sfp_normals result" % op)
    bad = msk & ~valid
    if bad.any():
        if invalid == "raise":
            raise ValueError("%s: %d pixel(s) inside the mask have no valid candidate (dark, a DoLP "
                             "above 1 + violation_tol, or a DoLP out of the model's reach) — pass "
                             "invalid='exclude', a tighter mask, or out_of_range='clamp' to sfp_normals"
                             % (op, int(bad.sum())))
        msk &= ~bad
    if not msk.any():
        raise ValueError("%s: no pixel left to disambiguate" % op)
    K = cand.shape[0]
    model = candidates["model"]
    out = np.zeros((H, W, 3))
    out[..., 2] = 1.0
    if prior == "convex":
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
        if center is None:
            cy, cx = float(yy[msk].mean()), float(xx[msk].mean())
        else:
            try:
                cy, cx = (_num(v, "center", op) for v in center)
            except TypeError:
                raise ValueError("%s: center must be (row, col)" % op) from None
        radial = np.stack([xx - cx, yy - cy], axis=-1)
        # 方位: 中心から外へ向く候補(像面成分と放射方向の内積が大きい方)
        az = np.asarray(candidates["azimuth_deg"], dtype=np.float64)
        ra = np.radians(az)
        score = np.cos(ra) * radial[None, ..., 0] + np.sin(ra) * radial[None, ..., 1]
        ia = np.argmax(score, axis=0)                          # 0 or 1
        if model == "specular":
            dolp = np.asarray(candidates["dolp"], dtype=np.float64)
            tol = _num(brewster_tol, "brewster_tol", op, lo=0.0, hi=1.0, lo_open=False)
            ridge = dolp >= 1.0 - tol
            from scipy import ndimage as _nd               # noqa: PLC0415
            lab, _nl = _nd.label(msk & ~ridge)
            iy = int(min(max(round(cy), 0), H - 1))
            ix = int(min(max(round(cx), 0), W - 1))
            inner = lab[iy, ix]
            if inner == 0:                                 # 中心が稜線上か mask の外: 最寄りの領域
                d = np.where(lab > 0, (yy - cy) ** 2 + (xx - cx) ** 2, np.inf)
                j = int(np.argmin(d))
                inner = lab.flat[j] if np.isfinite(d.flat[j]) else -1
            core = lab == inner
            # 稜線の帯の中は DoLP の放射方向の傾きで分ける: 凸なら天頂角は外へ向かって増える
            # ので、DoLP が外へ向かって増えていれば Brewster より手前(低い枝)、減っていれば
            # 向こう側(高い枝)。帯の幅は zenith で非対称なので、画素の距離では分けられない
            # (帯の中央で分けると 248 画素が最大 7° 外れた、2026-10-13 実測)。
            gy, gx = np.gradient(dolp)
            rlen = np.hypot(radial[..., 0], radial[..., 1])
            gr = (gx * radial[..., 0] + gy * radial[..., 1]) / np.where(rlen > 0, rlen, 1.0)
            low = core | (ridge & (gr >= 0.0))
            iz = np.where(low, 0, 1)
            k = 2 * iz + ia
        else:
            k = ia
    else:
        if prior == "normals":
            if prior_normals is None:
                raise ValueError("%s: prior='normals' needs prior_normals" % op)
            pn = _real(prior_normals, "prior_normals", op, ndim=3)
            if pn.shape != (H, W, 3):
                raise ValueError("%s: prior_normals must be %r, got %r" % (op, (H, W, 3), tuple(pn.shape)))
        else:
            if coarse_depth is None:
                raise ValueError("%s: prior='depth' needs coarse_depth" % op)
            zd = _real(coarse_depth, "coarse_depth", op, ndim=2)
            if zd.shape != (H, W):
                raise ValueError("%s: coarse_depth must be %r, got %r" % (op, (H, W), tuple(zd.shape)))
            import photometric as _ph                     # noqa: PLC0415
            pn = np.asarray(_ph.surface_normals(zd), dtype=np.float64)
        ln = np.linalg.norm(pn, axis=-1, keepdims=True)
        if (ln[msk] == 0.0).any():
            raise ValueError("%s: the prior has zero-length normals inside the mask" % op)
        pn = pn / np.where(ln == 0.0, 1.0, ln)
        dots = np.einsum("khwc,hwc->khw", cand, pn)
        k = np.argmax(dots, axis=0)
    pick = np.take_along_axis(cand, k[None, ..., None].repeat(3, axis=-1), axis=0)[0]
    out[msk] = pick[msk]
    del K
    return out


def sfp_estimate_index(dolp, zenith_deg, model="specular", mask=None, n_bounds=(1.05, 3.0)):
    """Estimate the refractive index from DoLP observed at known zenith angles — a least-squares fit of the Fresnel curve, plus Brewster's ``n = tan(theta_B)`` at the DoLP maximum for the specular model.

    *dolp* and *zenith_deg* are maps of the same shape (the zenith from a
    coarse geometry such as a sphere's silhouette, a CAD model or a coarse
    depth). The fit minimises ``sum (rho_model(theta; n) - dolp)^2`` over
    *mask* with a coarse grid over *n_bounds* followed by a bounded scalar
    minimisation.

    Returns a dict: ``refractive_index`` (the fit), ``rmse`` (DoLP units),
    ``n_pixels``, ``model``, and for the specular model ``brewster_index`` =
    ``tan`` of the zenith where DoLP is largest (with ``brewster_dolp``, the
    DoLP there — far below 1 means the data never reached Brewster's angle and
    the number is a lower bound, not an estimate).

    The DoLP maximum by itself says nothing about *n* (the specular maximum is
    exactly 1 for every index); the index is in **where** the maximum falls,
    which is why a zenith map is required.

    **Raises** ``ValueError``: shapes differ; DoLP outside ``[0, 1]`` or zenith
    outside ``[0, 90]``; fewer than 3 pixels in the mask; bounds not
    ``1 < lo < hi``; unknown *model*.
    """
    op = "sfp_estimate_index"
    m = _model(model, op)
    rho = _real(dolp, "dolp", op)
    z = _real(zenith_deg, "zenith_deg", op)
    if rho.shape != z.shape:
        raise ValueError("%s: dolp %r and zenith_deg %r must have the same shape" % (op, rho.shape, z.shape))
    if (rho < 0.0).any() or (rho > 1.0).any():
        raise ValueError("%s: dolp must be in [0, 1]" % op)
    if (z < 0.0).any() or (z > 90.0).any():
        raise ValueError("%s: zenith_deg must be in [0, 90]" % op)
    try:
        lo, hi = n_bounds
    except (TypeError, ValueError):
        raise ValueError("%s: n_bounds must be (lo, hi)" % op) from None
    lo = _index(lo, op, "n_bounds[0]")
    hi = _index(hi, op, "n_bounds[1]")
    if not lo < hi:
        raise ValueError("%s: n_bounds must satisfy lo < hi, got (%g, %g)" % (op, lo, hi))
    msk = _mask(mask, rho.shape, op)
    if int(msk.sum()) < 3:
        raise ValueError("%s: need at least 3 pixels in the mask, got %d" % (op, int(msk.sum())))
    r = rho[msk]
    th = np.radians(z[msk])

    def sse(nn):
        d = _rho(th, nn, m) - r
        return float(np.dot(d, d))

    grid = np.linspace(lo, hi, 241)
    vals = np.array([sse(g) for g in grid])
    j = int(np.argmin(vals))
    a, b = grid[max(j - 1, 0)], grid[min(j + 1, grid.size - 1)]
    from scipy.optimize import minimize_scalar      # noqa: PLC0415
    res = minimize_scalar(sse, bounds=(a, b), method="bounded", options={"xatol": 1e-12})
    nfit = float(res.x) if res.fun <= vals[j] else float(grid[j])
    out = {"refractive_index": nfit, "rmse": math.sqrt(sse(nfit) / r.size), "n_pixels": int(r.size),
           "model": m}
    if m == "specular":
        i = int(np.argmax(r))
        out["brewster_index"] = float(math.tan(th[i]))
        out["brewster_dolp"] = float(r[i])
    return out


def sfp_height(normals, mask=None, max_zenith_deg=88.0):
    """Integrate a normal map to a height map with Frankot-Chellappa on a mirror-extended domain, so the periodic boundary of the FFT does not bend the result.

    Gradients ``p = -nx/nz``, ``q = -ny/nz`` are formed inside *mask* (zero
    outside — the object stands on a flat background); slopes steeper than
    *max_zenith_deg* (the occluding rim, where ``nz -> 0`` and the gradient
    diverges) are clamped to that zenith with the azimuth kept. The field is
    then reflected into a ``2H x 2W`` even-symmetric domain (``p`` changes sign
    under the mirror in x, ``q`` under the mirror in y) and handed to
    :func:`photometric.integrate_gradients` — the same Frankot-Chellappa
    solver, without its wrap-around. Measured on a 64 x 80 tilted plane
    (slopes 0.3 and -0.2): largest height error 0.06 px here against 18 px with
    the periodic solver, which cannot represent a ramp at all (the residual
    0.06 px is the kink of the half-sample mirror at the seam).

    Returns ``(H, W)`` float64 heights in pixel units (multiply by the pixel
    pitch), with the background (outside *mask*) at mean 0, or the whole image
    at mean 0 when there is no mask.

    Compared with :func:`photometric.integrate_normals` (registered in ops3d):
    that operator integrates as is (periodic, no validation, no rim clamp);
    this one validates the field (unit, finite, facing the camera) and fixes
    the boundary.

    **Raises** ``ValueError``: *normals* not a finite ``(H, W, 3)`` field of
    unit normals with ``nz >= 0``; *mask* not boolean of shape ``(H, W)`` or
    empty; *max_zenith_deg* outside ``(0, 90)``.
    """
    op = "sfp_height"
    nrm = _normal_field(normals, op)
    H, W = nrm.shape[:2]
    msk = _mask(mask, (H, W), op)
    zmax = _num(max_zenith_deg, "max_zenith_deg", op, lo=0.0, hi=90.0, lo_open=True, hi_open=True)
    import photometric as _ph                         # noqa: PLC0415
    nz_min = math.cos(math.radians(zmax))
    nz = nrm[..., 2]
    steep = nz < nz_min
    nxy = np.hypot(nrm[..., 0], nrm[..., 1])
    scale = np.where(steep, math.sin(math.radians(zmax)) / np.maximum(nxy, 1e-300), 1.0)
    nx = nrm[..., 0] * scale
    ny = nrm[..., 1] * scale
    nzc = np.where(steep, nz_min, nz)
    p = np.where(msk, -nx / nzc, 0.0)
    q = np.where(msk, -ny / nzc, 0.0)
    P = np.block([[p, -p[:, ::-1]], [p[::-1, :], -p[::-1, ::-1]]])
    Q = np.block([[q, q[:, ::-1]], [-q[::-1, :], -q[::-1, ::-1]]])
    z = _ph.integrate_gradients(P, Q)[:H, :W]
    ref = ~msk if (mask is not None and (~msk).any()) else np.ones((H, W), bool)
    z = z - float(z[ref].mean())
    return np.ascontiguousarray(z, dtype=np.float64)
