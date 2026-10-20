# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""telecentric — テレセントリックレンズと寸法計測(主光線の傾き・高さで変わる倍率・ケラレ・ぼけ)。

動機(2026-10-15、ユーザーの要望「IR を使ったウエハやダイのボンディング機能ならテレセントリックレンズの再現も必要」):
棚卸しでは ``optscene.lens_spec(telecentric=True)`` に**倍率一定の旗が 1 つ**あるだけで、その旗を読む経路も、
テレセンの光学系そのものも無かった。しかも ``raytrace`` の光線の打ち出し(``_launch``)は入射瞳を目がけるので、
**入射瞳が無限遠にある物体側テレセンでは ``chief_ray`` / ``ray_bundle`` が ValueError で止まる**。
ここは ``raytrace`` の処方(``lens_system`` の table)と実光線の追跡(``trace_rays``)をそのまま使い、
光線の狙いを**入射瞳ではなく絞りそのもの**に置き直した層 —— だから入射瞳が無限遠でも、物体の裏にあっても同じ式で動く。

内容(7 op):
  生成      `telecentric_lens`(同じ単レンズの絞りの位置だけを変えた 3 種: 通常 / 物体側テレセン / 両側テレセン、
            絞りの位置ずれ ``stop_shift_mm`` でテレセン度を崩せる)
  主光線    `chief_ray_angle`(絞りの中心を通る実光線を Newton 法で探す。物体側の傾き = テレセン度、像の高さ、入射瞳までの距離)
            `magnification_vs_depth`(像面を固定して物体を ±Δz 動かしたときの倍率)
            `telecentricity_error`(段差 Δz の上下の面で寸法が何 % 狂うか、主光線の横ずれ Δz·tanθ の閉形式と並べる)
  ぼけと視野 `defocus_spot_vs_depth`(瞳を総当たりで埋めた光線束の RMS ぼけ —— 被写界深度と NA の取引)
            `vignetting_vs_field`(前玉の口径で光線束が欠ける割合 —— テレセンの視野は前玉径で決まる)
  描画      `lens_equivalent_pinhole`(主光線の幾何を ``render3d.render_mesh`` のピンホール(入射瞳の位置)に写す)

規約: 長さは mm、角度は度。光軸は +z で光は +z へ進む(``raytrace`` と同じ)。物体の高さ ``field_mm`` は +y。
``object_shift_mm`` は**レンズへ近づく向きが正**(背の高い部品の上面 = 正)。像面は処方の像面に固定する
(計測の実機はピントを合わせ直さない)。物体が無限遠の処方は fail-closed で拒否する(テレセンは有限物体の話)。

真値(外部): 主光線が入射瞳を通る幾何から m(Δz)/m(0) = L/(L − Δz)(L = 物体面から入射瞳までの距離)、
横ずれ Δz·tanθ(tanθ = h/L)、Newton の結像式 x·x' = −f²(絞りが後側焦点から δ ずれると入射瞳は前側焦点から −f²/δ)、
一様な円形の光線束の RMS 半径 = 幾何半径 / √2(幾何半径 = |m|·NA·|Δz|)、2 つの円の重なりの面積。
来歴: Smith, *Modern Optical Engineering*(テレセントリック系 = 絞りを焦点に置く)/ Welford, *Aberrations of Optical
Systems*(主光線と瞳)/ Wu et al., Opt. Eng. 54(6) 064103 (2015)(非テレセンの撮像が位相計測偏向法の誤差源)/
Marani et al., Sensors 15, 2283 (2015)(光切断の計測にテレセンのレンズ)。
"""
from __future__ import annotations

import copy
import math

import numpy as np

import raytrace as RT

__all__ = [
    "telecentric_lens", "chief_ray_angle", "magnification_vs_depth", "telecentricity_error",
    "defocus_spot_vs_depth", "vignetting_vs_field", "lens_equivalent_pinhole",
]

_KINDS = ("entocentric", "object", "bi")
_MAX_POINTS = 2001
_MAX_SAMPLES = 301


# --------------------------------------------------------------------------- #
# 検証
# --------------------------------------------------------------------------- #
def _num(v, name, op, positive=False, nonneg=False):
    if isinstance(v, (bool, np.bool_, str, bytes)) or v is None:
        raise ValueError("%s: %s must be a real number, got %r" % (op, name, v))
    try:
        x = float(v)
    except (TypeError, ValueError) as exc:
        raise ValueError("%s: %s must be a real number, got %r" % (op, name, v)) from exc
    if not math.isfinite(x):
        raise ValueError("%s: %s must be finite, got %r" % (op, name, v))
    if positive and x <= 0.0:
        raise ValueError("%s: %s must be > 0, got %r" % (op, name, v))
    if nonneg and x < 0.0:
        raise ValueError("%s: %s must be >= 0, got %r" % (op, name, v))
    return x


def _int(v, name, op, lo, hi):
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)):
        raise ValueError("%s: %s must be an integer, got %r" % (op, name, v))
    i = int(v)
    if not lo <= i <= hi:
        raise ValueError("%s: %s must lie in [%d, %d], got %d" % (op, name, lo, hi, i))
    return i


def _system(system, op):
    if not isinstance(system, dict) or "surfaces" not in system or "stop" not in system:
        raise ValueError("%s: expected the dict returned by raytrace.lens_system() or telecentric_lens(), got %r"
                         % (op, type(system).__name__))
    obj = float(system["object_mm"])
    if not math.isfinite(obj):
        raise ValueError("%s: the object is at infinity — telecentricity is about a finite object "
                         "(set object_mm in lens_system)" % op)
    return system


def _shift(system, dz, op):
    dz = _num(dz, "object_shift_mm", op)
    if dz >= float(system["object_mm"]):
        raise ValueError("%s: object_shift_mm %.6g moves the object onto or past the first lens vertex "
                         "(object_mm = %.6g)" % (op, dz, system["object_mm"]))
    return dz


def _range(lo, hi, n, op, lo_name="shift_min_mm", hi_name="shift_max_mm"):
    a = _num(lo, lo_name, op)
    b = _num(hi, hi_name, op)
    k = _int(n, "n_points", op, 2, _MAX_POINTS)
    if not b > a:
        raise ValueError("%s: need %s < %s, got %r, %r" % (op, lo_name, hi_name, lo, hi))
    return np.linspace(a, b, k)


# --------------------------------------------------------------------------- #
# 生成
# --------------------------------------------------------------------------- #
def _equiconvex_radius(f, n, t):
    """厚肉の等凸レンズの曲率半径(焦点距離 f、屈折率 n、中心厚 t)。

    1/f = (n−1)[2/R − (n−1)t/(nR²)] を R について解いた大きい根 R = (n−1)f[1 + √(1 − t/(nf))]。
    """
    disc = 1.0 - t / (n * f)
    if disc <= 0.0:
        raise ValueError("telecentric_lens: the lens is too thick (%.3g mm) for focal length %.3g mm" % (t, f))
    return (n - 1.0) * f * (1.0 + math.sqrt(disc))


def _singlet(f, glass, wl, ap):
    """焦点距離 f の等凸単レンズ(面 2 枚)。中心厚は縁の厚さが 1 mm 残るように選ぶ。"""
    n = RT.refractive_index(glass, wl)
    t = 4.0
    for _ in range(30):                      # 曲率は厚さに依存し、厚さは曲率(縁の厚さ)に依存する
        R = _equiconvex_radius(f, n, t)
        if ap >= R:
            raise ValueError("telecentric_lens: semi-aperture %.3g mm exceeds the lens radius %.3g mm "
                             "(focal length %.3g mm is too short for this aperture)" % (ap, R, f))
        sag = R - math.sqrt(R * R - ap * ap)
        t_new = max(4.0, 2.0 * sag + 1.0)
        if abs(t_new - t) < 1e-12:
            break
        t = t_new
    R = _equiconvex_radius(f, n, t)
    tl = RT.thick_lens(R, -R, t, n)
    return {"R": R, "t": t, "n_value": n, "efl": tl["efl"], "bfl": tl["bfl"], "ffl": tl["ffl"]}


def telecentric_lens(kind="object", focal_mm=100.0, magnification=-0.5, na_object=0.01,
                     front_aperture_mm=12.5, stop_shift_mm=0.0, glass="N-BK7", wavelength_um=0.58756):
    """同じ単レンズで、絞りの位置だけを変えた 3 種の撮像レンズの処方(``raytrace.lens_system`` の table)。

    * ``kind="entocentric"`` —— 通常のレンズ。絞りをレンズの直後(1 mm)に置く。入射瞳はレンズの位置にあり、
      主光線は物体から入射瞳へ向かって傾く(近い物ほど大きく写る)。
    * ``kind="object"`` —— 物体側テレセン。絞りを**後側焦点**に置く。入射瞳は無限遠、物体側の主光線は光軸に平行。
    * ``kind="bi"`` —— 両側テレセン。後側焦点の絞りの後ろに、前側焦点が絞りに来る 2 枚目のレンズ
      (焦点距離 ``|magnification| × focal_mm``)を置く。物体は 1 枚目の前側焦点、倍率は −f₂/f₁。

    *magnification* は横倍率(実像なので負)、*na_object* は物体側の開口数(絞りの半径を近軸の周辺光線から決める)、
    *front_aperture_mm* は前玉の半口径(テレセンの視野はこれで決まる)。*stop_shift_mm* は絞りを
    設計位置から光軸方向へずらす量(正 = 像側)で、テレセン度の崩れを再現する(Newton の式で入射瞳は前側焦点から
    −f²/δ)。レンズは *glass* の等凸単レンズで、縁の厚さが 1 mm 残る中心厚を選ぶ。像面は近軸の像の位置に固定する。

    返り値は ``lens_system`` の dict に ``"design"``(種別・焦点距離・絞りの半径・物体距離・面の役割)を足したもの。
    絞りの面は平面なので、その ``R`` は ``lens_system`` の規約どおり ``inf``(非有限は契約)。
    ``raytrace`` のどの op にもそのまま渡せる(ただし入射瞳が無限遠の処方は ``raytrace.chief_ray`` では
    狙えないので、主光線は :func:`chief_ray_angle` を使う)。
    """
    op = "telecentric_lens"
    if kind not in _KINDS:
        raise ValueError("%s: kind must be one of %s, got %r" % (op, _KINDS, kind))
    f1 = _num(focal_mm, "focal_mm", op, positive=True)
    m = _num(magnification, "magnification", op)
    if not m < 0.0:
        raise ValueError("%s: a single positive group forms a real, inverted image — magnification must be < 0, got %r"
                         % (op, magnification))
    na = _num(na_object, "na_object", op, positive=True)
    if na >= 0.5:
        raise ValueError("%s: na_object must be < 0.5 for this paraxial layout, got %r" % (op, na))
    ap = _num(front_aperture_mm, "front_aperture_mm", op, positive=True)
    shift = _num(stop_shift_mm, "stop_shift_mm", op)
    wl = _num(wavelength_um, "wavelength_um", op, positive=True)
    RT.refractive_index(glass, wl)                       # 名前と波長の範囲を先に検証する
    L1 = _singlet(f1, glass, wl, ap)
    surf = [{"R": L1["R"], "t": L1["t"], "n": glass, "ap": ap}]
    if kind == "entocentric":
        gap = 1.0 + shift
        obj = f1 * (1.0 - 1.0 / m)                         # 主点からの物体距離 s = f(1 − 1/m)
        obj -= (L1["ffl"] + f1)                            # 前側主点は第 1 面から pp_front = ffl + f
    elif kind == "object":
        gap = L1["bfl"] + shift
        obj = f1 * (1.0 - 1.0 / m) - (L1["ffl"] + f1)
    else:
        gap = L1["bfl"] + shift
        obj = -L1["ffl"]                                   # 1 枚目の前側焦点
    if gap <= 0.0:
        raise ValueError("%s: stop_shift_mm %.6g puts the stop inside the lens" % (op, shift))
    if obj <= 0.0:
        raise ValueError("%s: the object would sit inside the lens (object distance %.6g mm)" % (op, obj))
    surf.append({"R": -L1["R"], "t": gap, "n": 1.0, "ap": ap})
    roles = ["lens1_front", "lens1_rear", "stop"]
    stop_index = 2
    if kind == "bi":
        f2 = abs(m) * f1
        ap2 = ap * max(1.0, abs(m))
        L2 = _singlet(f2, glass, wl, ap2)
        d = -L2["ffl"] - shift                             # 2 枚目の前側焦点を設計上の絞り位置に
        if d <= 0.0:
            raise ValueError("%s: stop_shift_mm %.6g puts the stop inside the second lens" % (op, shift))
        surf.append({"R": "inf", "t": d, "n": 1.0, "ap": 1.0})
        surf.append({"R": L2["R"], "t": L2["t"], "n": glass, "ap": ap2})
        surf.append({"R": -L2["R"], "t": None, "n": 1.0, "ap": ap2})
        roles += ["lens2_front", "lens2_rear"]
    else:
        surf.append({"R": "inf", "t": None, "n": 1.0, "ap": 1.0})
    # 絞りの半径: 軸上の物点から傾き u の近軸光線が絞りで y = a·u → 半径 = NA·|a|
    probe = RT.lens_system(surf, stop=stop_index, object_mm=obj, wavelength_um=wl)
    c, t, n = RT._paraxial_model(probe)
    ys, _ = RT._trace_paraxial(c, t, n, obj * 1.0, 1.0)
    a = abs(float(ys[stop_index]))
    if a < 1e-12:
        raise ValueError("%s: the stop cannot be reached by an axial ray (degenerate layout)" % op)
    r_stop = na * a
    surf[stop_index]["ap"] = r_stop
    probe = RT.lens_system(surf, stop=stop_index, object_mm=obj, wavelength_um=wl)
    image = RT.paraxial_trace(probe)["image_mm"]
    if not (math.isfinite(image) and image > 0.0):
        raise ValueError("%s: the layout does not form a real image (image distance %r)" % (op, image))
    surf[-1]["t"] = image
    sysd = RT.lens_system(surf, stop=stop_index, object_mm=obj, wavelength_um=wl)
    para = RT.paraxial_trace(sysd)
    sysd["design"] = {"kind": kind, "focal_mm": f1, "magnification_design": m, "na_object": na,
                      "front_aperture_mm": ap, "stop_shift_mm": shift, "stop_radius_mm": r_stop,
                      "object_mm": obj, "image_mm": image, "glass": glass, "roles": roles,
                      "magnification_paraxial": para["magnification"],
                      "lens1": {k: L1[k] for k in ("R", "t", "efl", "bfl", "ffl")}}
    return sysd


# --------------------------------------------------------------------------- #
# 主光線(絞りの中心を狙う)
# --------------------------------------------------------------------------- #
def _open(system):
    """口径を外した複製(狙いの反復の途中で光線が蹴られて NaN にならないように)。"""
    s = copy.deepcopy(system)
    for sf in s["surfaces"]:
        sf["ap"] = None
    return s


def _trace_from(system, h, dz, slopes_x, slopes_y):
    """物点 (0, h, −(obj − dz)) から傾き (sx, sy) = (dx/dz, dy/dz) の光線を追う。"""
    sx = np.atleast_1d(np.asarray(slopes_x, np.float64))
    sy = np.atleast_1d(np.asarray(slopes_y, np.float64))
    z0 = -(float(system["object_mm"]) - dz)
    P = np.tile([0.0, h, z0], (len(sx), 1))
    D = np.stack([sx, sy, np.ones_like(sx)], 1)
    return RT.trace_rays(system, P, D)


def _chief_slope(system, h, dz, prepared=None, initial=None):
    """絞りの中心を通る主光線の物体側の傾き dy/dz(Newton 法、口径なしの処方で)。"""
    stop = system["stop"]
    so, para = prepared if prepared is not None else (_open(system), None)

    def y_stop(s):
        tr = _trace_from(so, h, dz, [0.0], [s])
        return float(tr["points"][0, stop + 1, 1])

    # 初期値: 近軸の主光線(入射瞳が有限ならその方向、無限遠なら 0)
    try:
        para = RT.paraxial_trace(system) if para is None else para
        L = float(system["object_mm"]) + para["ep_position"] - dz
        s = float(initial) if initial is not None else (-h / L if math.isfinite(L) and abs(L) > 1e-9 else 0.0)
    except ValueError:
        s = 0.0
    r = y_stop(s)
    if not math.isfinite(r):
        s = 0.0                                          # 近軸の初期値が面を外した: 光軸に平行から始める
        r = y_stop(s)
    if not math.isfinite(r):
        raise ValueError("chief ray: no launch toward the stop reaches it (field %.6g mm)" % h)
    it = 0
    for it in range(1, 60):
        if abs(r) < 1e-13:
            break
        e = 1e-7
        tr_pm = _trace_from(so, h, dz, [0.0, 0.0], [s + e, s - e])
        y_pm = tr_pm["points"][:, stop + 1, 1]
        d = float(y_pm[0] - y_pm[1]) / (2 * e)
        if not math.isfinite(d) or abs(d) < 1e-15:
            raise ValueError("chief ray: the stop does not respond to the launch slope (degenerate layout)")
        step = -r / d
        for _ in range(40):                              # 面を外したら歩幅を半分に(Newton の行き過ぎ)
            r_new = y_stop(s + step)
            if math.isfinite(r_new) and abs(r_new) < abs(r):
                break
            step *= 0.5
        else:
            raise ValueError("chief ray: Newton iteration stalled at field %.6g mm (residual %.3g mm)" % (h, abs(r)))
        s += step
        r = r_new
    return s, abs(r), it


def chief_ray_angle(system, field_mm=5.0, object_shift_mm=0.0):
    """物高 *field_mm* の点から絞りの中心を通る実の主光線: 物体側の傾き(= テレセン度)と像の位置。

    入射瞳を経由せず、**絞りの面で光線の高さが 0 になる打ち出しの傾き**を Newton 法で探す(口径を外した複製で
    狙い、最後に口径つきで追って蹴られを判定する)。だから入射瞳が無限遠(物体側テレセン)でも物体の裏
    (ハイパーセントリック)でも同じ式で動く。*object_shift_mm* は物体をレンズへ近づける量(正 = 高い面)。

    返り値: ``object_angle_deg``(物体側の主光線の傾き。**光軸から離れる向きが正**に符号を揃える: 通常のレンズは負、
    物体側テレセンは 0、ハイパーセントリックは正)・``object_slope``(dy/dz そのもの)・``image_angle_deg``(像側)・
    ``image_y_mm``(固定した像面での高さ)・``magnification``(image_y / field)・``pupil_distance_mm``
    (物体面から主光線が光軸と交わる点 = 実光線の入射瞳までの距離。正 = レンズ側、平行なら inf)・
    ``valid``(口径つきで像面まで届いたか)・``stop_residual_mm``・``iterations``。
    """
    op = "chief_ray_angle"
    _system(system, op)
    h = _num(field_mm, "field_mm", op)
    if h == 0.0:
        raise ValueError("%s: field_mm must be non-zero (on axis the chief ray is the axis itself)" % op)
    dz = _shift(system, object_shift_mm, op)
    s, res, it = _chief_slope(system, h, dz)
    tr = _trace_from(system, h, dz, [0.0], [s])
    ok = bool(tr["valid"][0])
    tro = tr if ok else _trace_from(_open(system), h, dz, [0.0], [s])
    yi = float(tro["points"][0, -1, 1])
    dimg = tro["dirs"][0, -1]
    sign = 1.0 if h > 0 else -1.0
    theta = math.degrees(math.atan(s)) * sign
    img_angle = math.degrees(math.atan2(dimg[1], dimg[2])) * sign
    L = -h / s if abs(s) > 1e-15 else math.inf
    return {"object_angle_deg": theta, "object_slope": s, "image_angle_deg": img_angle,
            "image_y_mm": yi, "magnification": yi / h, "pupil_distance_mm": L, "valid": ok,
            "stop_residual_mm": res, "iterations": it, "field_mm": h, "object_shift_mm": dz}


def magnification_vs_depth(system, field_mm=5.0, shift_min_mm=-2.0, shift_max_mm=2.0, n_points=21):
    """物体を光軸方向に動かしたときの倍率 m(Δz)(像面は固定、実の主光線の像の高さ / 物高)。

    pairs ``(Δz mm, m)``。Δz の正はレンズへ近づく向き。通常のレンズでは m(Δz)/m(0) = L/(L − Δz)
    (L = 物体面から入射瞳までの距離)で近い物ほど大きく、物体側テレセンでは L → ∞ で一定になる。
    像面を固定するのは計測の実機と同じ(ぼけた像の重心 = 主光線の位置で寸法を測る)。
    """
    op = "magnification_vs_depth"
    _system(system, op)
    h = _num(field_mm, "field_mm", op)
    if h == 0.0:
        raise ValueError("%s: field_mm must be non-zero" % op)
    zs = _range(shift_min_mm, shift_max_mm, n_points, op)
    if zs[-1] >= float(system["object_mm"]):
        raise ValueError("%s: shift_max_mm reaches the first lens vertex" % op)
    out = np.empty((len(zs), 2))
    prepared = (_open(system), RT.paraxial_trace(system))
    previous = None
    for i, dz in enumerate(zs):
        try:
            s, _, _ = _chief_slope(system, h, float(dz), prepared, previous)
        except ValueError:
            s, _, _ = _chief_slope(system, h, float(dz), prepared)
        previous = s
        tr = _trace_from(prepared[0], h, float(dz), [0.0], [s])
        out[i] = (dz, tr["points"][0, -1, 1] / h)
    return out


def telecentricity_error(system, field_mm=5.0, step_height_mm=1.0):
    """段差 *step_height_mm* の上と下の面に同じ寸法の物があるとき、像の上で寸法がどれだけ違って見えるか。

    返り値: ``object_angle_deg``(下の面での主光線の傾き)・``magnification_low`` / ``magnification_high``(実光線)・
    ``relative_size_error``(m_high / m_low − 1、寸法の読みの相対誤差)・``lateral_shift_um``(上の面の点が
    下の面の基準で何 µm ずれて見えるか、実光線)・``closed_form_shift_um``(主光線の幾何 Δz·tanθ。θ は下の面の
    主光線、符号は光軸から離れる向きが正)・``closed_form_relative``(Δz/(L − Δz)、L は実光線の入射瞳までの距離)。
    ★寸法の検査で「高さの違う面を同じ倍率で換算する」誤りの大きさそのもの。テレセン度 0.1° の残りでも、
    高さ 1 mm で 1.75 µm(tan 0.1° × 1 mm)ずれる。
    """
    op = "telecentricity_error"
    _system(system, op)
    h = _num(field_mm, "field_mm", op)
    if h == 0.0:
        raise ValueError("%s: field_mm must be non-zero" % op)
    dz = _shift(system, step_height_mm, op)
    if dz == 0.0:
        raise ValueError("%s: step_height_mm must be non-zero" % op)
    lo = chief_ray_angle(system, h, 0.0)
    hi = chief_ray_angle(system, h, dz)
    rel = hi["magnification"] / lo["magnification"] - 1.0
    L = lo["pupil_distance_mm"]
    cf_rel = dz / (L - dz) if math.isfinite(L) else 0.0
    sign = 1.0 if h > 0 else -1.0
    return {"object_angle_deg": lo["object_angle_deg"], "magnification_low": lo["magnification"],
            "magnification_high": hi["magnification"], "relative_size_error": rel,
            "lateral_shift_um": 1000.0 * h * rel * sign,
            "closed_form_shift_um": -1000.0 * dz * math.tan(math.radians(lo["object_angle_deg"])),
            "closed_form_relative": cf_rel, "pupil_distance_mm": L, "field_mm": h, "step_height_mm": dz}


# --------------------------------------------------------------------------- #
# 光線束(瞳を総当たりで埋める)
# --------------------------------------------------------------------------- #
def _bundle(system, h, dz, samples, prepared=None, initial=None):
    """物点から出て口径つきの処方を抜ける光線束(傾きの格子を 2 段で: 粗く当たりを付けてから細かく)。"""
    s0, _, _ = _chief_slope(system, h, dz, prepared, initial)
    obj = float(system["object_mm"]) - dz
    aps = [sf["ap"] for sf in system["surfaces"] if sf["ap"] is not None]
    reach = (max(aps) + abs(h)) / obj                    # どの面の口径の外へも出ない傾きの上限
    g = np.linspace(-reach, reach, 61)
    SX, SY = np.meshgrid(g, g + s0)
    tr = _trace_from(system, h, dz, SX.ravel(), SY.ravel())
    v = tr["valid"]
    if not v.any():
        return np.zeros((0, 2)), 0.0, (0.0, 0.0)
    step = g[1] - g[0]
    xs, ys = SX.ravel()[v], SY.ravel()[v]
    x0, x1 = xs.min() - step, xs.max() + step
    y0, y1 = ys.min() - step, ys.max() + step
    gx = np.linspace(x0, x1, samples)
    gy = np.linspace(y0, y1, samples)
    SX, SY = np.meshgrid(gx, gy)
    tr = _trace_from(system, h, dz, SX.ravel(), SY.ravel())
    v = tr["valid"]
    cell = (gx[1] - gx[0]) * (gy[1] - gy[0])
    return tr["points"][v, -1, :2], float(v.sum()) * cell, (x1 - x0, y1 - y0)


def defocus_spot_vs_depth(system, field_mm=0.0, shift_min_mm=-1.0, shift_max_mm=1.0, n_points=11, samples=61):
    """物体を ±Δz 動かしたときの像面(固定)での RMS ぼけ半径(µm、光線束を傾きの格子で総当たりに追う)。

    pairs ``(Δz mm, RMS 半径 µm)``。一様な円の光線束なら RMS = 幾何半径/√2 で、幾何半径 = |m|·NA·|Δz|
    (物体側 NA)—— 被写界深度は NA に反比例し、回折の限界 0.61λ/NA は NA に反比例して**逆に**悪くなる。
    Δz = 0 の値は収差の床(0 にならない)。光線束は絞りと各面の口径で実際に蹴られた残りなので、
    入射瞳が無限遠の処方でも狙いの近似が入らない。*samples* は傾きの格子の一辺の本数。
    """
    op = "defocus_spot_vs_depth"
    _system(system, op)
    h = _num(field_mm, "field_mm", op)
    zs = _range(shift_min_mm, shift_max_mm, n_points, op)
    if zs[-1] >= float(system["object_mm"]):
        raise ValueError("%s: shift_max_mm reaches the first lens vertex" % op)
    k = _int(samples, "samples", op, 11, _MAX_SAMPLES)
    out = np.empty((len(zs), 2))
    prepared = (_open(system), RT.paraxial_trace(system))
    for i, dz in enumerate(zs):
        pts, _, _ = _bundle(system, h, float(dz), k, prepared)
        if len(pts) < 3:
            raise ValueError("%s: fewer than 3 rays reach the image at shift %.6g mm (vignetted)" % (op, dz))
        d = pts - pts.mean(0)
        out[i] = (dz, 1000.0 * math.sqrt(float(np.mean(np.sum(d * d, 1)))))
    return out


def vignetting_vs_field(system, field_max_mm=None, n_points=41, samples=81):
    """物高ごとに、像面まで届く光線束の立体角(傾きの面積)を軸上に対する割合で(ケラレ)。

    pairs ``(物高 mm, 割合)``。物体側テレセンでは主光線が光軸に平行なので、**前玉の半口径より外の物は写らない**
    —— 視野の直径は前玉径で決まる(通常のレンズは主光線が光軸へ寄るので前玉より広く見える)。物体側テレセンの
    閉形式: 前玉の上の光線束は半径 r = NA·(物体から前玉まで)の円で中心が物高 h、前玉の半口径 a の円との重なりの
    面積 / πr²。*field_max_mm* の既定は前玉の半口径の 1.3 倍。
    """
    op = "vignetting_vs_field"
    _system(system, op)
    aps = [sf["ap"] for sf in system["surfaces"] if sf["ap"] is not None]
    hmax = 1.3 * float(system["surfaces"][0]["ap"] or max(aps)) if field_max_mm is None else \
        _num(field_max_mm, "field_max_mm", op, positive=True)
    k = _int(n_points, "n_points", op, 2, _MAX_POINTS)
    m = _int(samples, "samples", op, 11, _MAX_SAMPLES)
    hs = np.linspace(0.0, hmax, k)
    _, a0, _ = _bundle(system, 0.0, 0.0, m)
    if a0 <= 0.0:
        raise ValueError("%s: no ray reaches the image on axis" % op)
    out = np.empty((k, 2))
    out[0] = (0.0, 1.0)
    for i, h in enumerate(hs[1:], start=1):
        try:
            _, a, _ = _bundle(system, float(h), 0.0, m)
        except ValueError:
            a = 0.0
        out[i] = (h, a / a0)
    return out


# --------------------------------------------------------------------------- #
# 描画への橋
# --------------------------------------------------------------------------- #
def lens_equivalent_pinhole(system, pixel_pitch_um=25.0, width=240, height=240, field_mm=None,
                            max_pupil_distance_mm=1.0e7):
    """主光線の幾何を ``render3d.render_mesh`` のピンホールカメラ(pose, K)に写す。

    ピンホールは**入射瞳**に置く: 物体側の主光線はすべて入射瞳を通るので、近軸の範囲で像の幾何(どの点がどこに
    写り、どの面が隠れるか)はピンホールと同じになる。焦点距離(画素)は fx = |m|·L / ピッチ で、物体面
    (世界の z = 0、光軸 = 世界の z、カメラは +z から見下ろす)の倍率が処方と一致する。
    L(物体面から入射瞳)は *field_mm* を与えれば実の主光線(:func:`chief_ray_angle`)から、無ければ近軸から取る。
    物体側テレセン(L = ∞)は L を *max_pupil_distance_mm* に置いた**平行投影の代理**にし、``orthographic_proxy``
    を True で返す。入射瞳が物体の裏(L < 0、ハイパーセントリック)はピンホールで再現できないので ValueError。
    像の上下反転(実像)は写さない(センサの読み出しで戻すのと同じ)。返り値: ``pose`` / ``K`` / ``magnification`` /
    ``pupil_distance_mm`` / ``orthographic_proxy`` / ``pixel_pitch_um``。
    """
    op = "lens_equivalent_pinhole"
    _system(system, op)
    pitch = _num(pixel_pitch_um, "pixel_pitch_um", op, positive=True)
    w = _int(width, "width", op, 1, 8192)
    hgt = _int(height, "height", op, 1, 8192)
    lmax = _num(max_pupil_distance_mm, "max_pupil_distance_mm", op, positive=True)
    para = RT.paraxial_trace(system)
    m = float(para["magnification"])
    if field_mm is None:
        L = float(system["object_mm"]) + float(para["ep_position"])
    else:
        cr = chief_ray_angle(system, field_mm, 0.0)
        L = cr["pupil_distance_mm"]
        m = cr["magnification"]
    if math.isfinite(L) and L < 0.0 and abs(L) < lmax:
        raise ValueError("%s: the entrance pupil lies %.6g mm behind the object (hypercentric) — a pinhole camera "
                         "cannot reproduce that geometry" % (op, -L))
    proxy = (not math.isfinite(L)) or abs(L) >= lmax
    if proxy:
        L = lmax
    import render3d
    pose = render3d.look_at((0.0, 0.0, L), (0.0, 0.0, 0.0), up=(0.0, 1.0, 0.0))
    fpx = abs(m) * L / (pitch * 1e-3)
    K = np.array([[fpx, 0.0, (w - 1) * 0.5], [0.0, fpx, (hgt - 1) * 0.5], [0.0, 0.0, 1.0]])
    return {"pose": pose, "K": K, "magnification": m, "pupil_distance_mm": float(L),
            "orthographic_proxy": bool(proxy), "pixel_pitch_um": pitch, "width": w, "height": hgt}
