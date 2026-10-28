# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""raytrace3d — 非共軸の逐次光線追跡: 座標の切り替え・折り返しミラー・半透鏡・傾いた平板・シャインプルーフ・ゴースト。

動機(2026-10-15、ユーザーの言葉「色んな光学系の完成度を上げてほしい」): ``raytrace`` は共軸の球面・円錐面を
実光線で追い、近軸量・spot・OPD・Seidel・公差まで出すが、**光軸が 1 本の直線**であることを前提にしていた。
検査の光学系でありふれた構成 —— 装置を小さくする折り返しミラー、同軸落射の半透鏡(ビームスプリッタ)、
傾けた平板やプリズム、傾いた物面を全面で合焦させるシャインプルーフ配置 —— が組めず、半透鏡の裏面が作る
ゴースト(2 面の反射でできる像)が鏡面の部品の上に偽の欠陥として写る、という現場の事故も計算できなかった。

この module は ``raytrace`` の面の式(円錐 + 偶数次の非球面の交点・法線、屈折・反射の式)を**そのまま**使い、
面ごとに 3-D の姿勢(回転行列と原点)を持たせて追跡する。共軸の処方を変換した場合、光線の交点・方向・光路長は
``raytrace.trace_rays`` と同じ演算の順序で計算され、**1e-12 で一致する**(門)。

内容(13 op、opsoptics のカテゴリ ``noncoaxial``):
  組む      `noncoaxial_system`(面・座標の切り替え・戻り・折り返しミラー・平板・半透鏡の列 → 検証済みの処方。
            ``raytrace.lens_system`` の処方も受ける)/ `noncoaxial_example`(折り返し・潜望鏡・同軸落射・
            傾いた平板・シャインプルーフ・軸外し放物面・共軸の 2 枚玉)/ `noncoaxial_layout`(各面の大域の姿勢と頂点)
  追う      `noncoaxial_trace`(視野ごとの実光線の束、像面上の点、主光線の折れ線)/ `noncoaxial_spot`(RMS・幾何半径・重心)/
            `image_orientation`(像の向き: 反射の回数・裏返り・回転)/ `beamsplitter_branches`(透過と反射の 2 本の枝)
  閉形式    `tilted_plate_shift`(傾いた平行平板の横ずれ・焦点ずれ・非点隔差)/ `scheimpflug_tilt`(傾いた物面に対する
            像面の傾き、ヒンジ、実光線での確かめ)/ `surface_reflectance`(面の残留反射率: 材料表 + 膜)
  ゴースト  `ghost_analysis`(全ての 2 面の組のゴーストの焦点・像面上の大きさ・相対強度)/ `ghost_image`(像面の照度の図)/
            `ghost_path`(1 組のゴーストの光路を光線の折れ線で)

座標の規約(光学設計ファイル(.zmx)の座標の切り替えと同じ順序。ray-optics〔BSD-3〕の 'decenter' / 'reverse'、optiland〔MIT〕の
絶対座標と、式と規約だけを照合した。コードは写していない):
  * 大域の座標は第 1 面の頂点が原点、光は +z へ進む(``raytrace`` と同じ)。各面は**その時点の座標系**の中で
    ``raytrace`` の形のまま記述する(R は局所の +z 側に曲率中心があれば正)。
  * 座標の切り替え(``break``): 現在の座標系の中で、まず (dx, dy) だけ偏心し、次に局所の x 軸まわりに ax、
    回った後の y 軸まわりに ay、回った後の z 軸まわりに az だけ回す(内因的な x → y → z、R = Rx·Ry·Rz、
    右手系で正の角は反時計回り)。``order="zyx"`` は逆順(先に z → y → x の順に回し、回った軸で偏心)で、
    ``undo`` に切り替えの番号を渡すと、その逆変換(角と偏心の符号を反転して逆順)になる。切り替えの後の
    ``t`` は新しい z 軸に沿った距離。切り替えは**以後の全ての面**に効く。
  * 面ごとの ``decenter`` / ``tilt`` は ``raytrace`` と同じ「その面だけ」の偏心・傾き(偏心して戻る):
    後続の座標系を動かさない(公差の摂動用)。
  * 反射(鏡、半透鏡の反射の枝)の後は、座標系を局所の x 軸まわりに 180° 回す(z と y が反転する): 光は
    新しい +z へ進み、厚さは**正の物理的な距離**のまま(``raytrace`` の規約と同じ。屈折率の符号を反転する
    教科書の規約 n' = −n, t' < 0 とは表記が違うだけで同じ幾何)。後続の面の R は**新しい座標系**で書く。
  * 折り返しミラー ``fold_mirror(tilt=(ax, ay))``: 切り替え(ax, ay) → 傾いていない鏡 → 切り替え(ax, −ay の
    逆順)に展開する。光軸は鏡の法線について鏡映され、45° の鏡で 90° 折れる。
  * 像面は最後の座標系の z = 0 の面(``image_tilt`` で傾けられる)。像面の局所の (x, y) は、光の進む向きを z
    とした右手系 —— 反射を奇数回くぐると像は裏返り(行列式が負)、偶数回なら回転だけになる。
  * 傾けた像面 ``z = x·tan(ty) + y·tan(tx)`` の局所の (x, y) は**傾いた面そのものの上の座標**(傾いた受光素子の
    上の距離がそのまま出る): x 軸 = 面と傾けない座標系の xz 面との交線 ``(1, 0, tan ty)/‖·‖``、法線
    ``n = (−tan ty, −tan tx, 1)/‖·‖``、y 軸 = ``n × x``。単軸の傾きなら傾けた向きの長さは傾けない面への射影の
    1/cos θ' 倍(2026-10-24 までは射影した座標を返していた)。

ゴースト: 面 i < j の組ごとに、光は j まで進んで反射し、j−1 … i+1 を逆向きにくぐって i で反射し、i+1 から
先を通常どおり進んで像面に届く(2 回反射の経路は N(N−1)/2 本)。逆向きにくぐる面は通常の働き(屈折・反射)の
まま媒質を逆にたどる。各面の反射率は材料表の屈折率と膜(``filmoptics`` の特性行列)から引く。

真値(外部): 平面鏡の折り返しの像 = 展開した系の像の鏡映(Householder 変換)、反射の回数と像の裏返り、傾いた平行
平板の横ずれ Δ = t·sinθ(1 − cosθ/√(n² − sin²θ))(Smith, *Modern Optical Engineering*, 平行平板の節)と
非点隔差 (t/√(n² − sin²θ))(n²cos²θ/(n² − sin²θ) − 1)(Coddington の式から導出、接線像が遠い)、シャインプルーフの
tanθ' = m·tanθ とヒンジ(物面と前側主面・像面と後側主面が同じ高さで交わる)、Fresnel の反射率と λ/4 単層膜の
閉形式、平板の 2 回反射のゴーストの焦点 = 主像 + 2t/n、OSS の光線追跡 optiland(MIT、第 2 実装、任意)。

来歴: Welford, *Aberrations of Optical Systems*(1986)§ 傾き・偏心の座標変換 / Smith, *Modern Optical Engineering*
(4th ed.)平面鏡とプリズム・平行平板・ゴースト / Kingslake, *Lens Design Fundamentals* / Scheimpflug, GB 1196(1904)/
Merklinger, *Focusing the View Camera*(1993)/ Born & Wolf §1.6(特性行列)/ Macleod §2(λ/4 膜)。
"""
from __future__ import annotations

import math

import numpy as np

import raytrace as RT

__all__ = [
    "noncoaxial_system", "noncoaxial_example", "noncoaxial_layout", "noncoaxial_trace", "noncoaxial_spot", "image_orientation",
    "beamsplitter_branches", "tilted_plate_shift", "scheimpflug_tilt", "surface_reflectance",
    "ghost_analysis", "ghost_image", "ghost_path",
]

INF = RT.INF
WL_D = RT.WL_D
#: 反射の後の座標系の曲げ(局所の x 軸まわりの 180°)。対角が ±1 なので掛け算は丸めない。
_REV = np.diag([1.0, -1.0, -1.0])
_MAX_RECORDS = 400
#: 像面に届いたと見なす、像面の法線方向の方向余弦の下限(これ以下は像面とほぼ平行 = 89.94° 超)。
_MIN_DZ = 1e-3
_MAX_RAYS = 20000
_KINDS = ("surface", "break", "return")
_SURFACE_KEYS = frozenset(("type", "R", "t", "n", "k", "ap", "mirror", "decenter", "tilt", "asph",
                           "coating", "beamsplitter", "label"))
_BREAK_KEYS = frozenset(("type", "decenter", "tilt", "order", "undo", "t", "label"))
_RETURN_KEYS = frozenset(("type", "to", "t", "label"))
_FOLD_KEYS = frozenset(("type", "tilt", "t", "ap", "R", "k", "asph", "reflectance", "label"))
_PLATE_KEYS = frozenset(("type", "thickness", "n", "tilt", "t", "ap", "wedge", "coating_front",
                         "coating_back", "beamsplitter", "branch", "label"))


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


def _pair(v, name, op, n=2):
    if isinstance(v, (str, bytes)) or not hasattr(v, "__len__") or len(v) != n:
        raise ValueError("%s: %s must be a sequence of %d numbers, got %r" % (op, name, n, v))
    return tuple(_num(x, "%s[%d]" % (name, i), op) for i, x in enumerate(v))


def _keys(d, allowed, what, op):
    bad = sorted(set(d) - allowed)
    if bad:
        raise ValueError("%s: %s: unknown key(s) %s (allowed: %s)" % (op, what, bad, sorted(allowed)))


def _tnone(s, i, op):
    """要素の t(None は最後の要素だけ許す —— noncoaxial_system が後で確かめる)。"""
    t = s.get("t", 0.0)
    return None if t is None else _num(t, "element %d t" % i, op, nonneg=True)


def _rx(a):
    a = math.radians(a)
    c, s = math.cos(a), math.sin(a)
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])


def _ry(a):
    a = math.radians(a)
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])


def _rz(a):
    a = math.radians(a)
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def _break_matrix(tilt, order):
    ax, ay, az = tilt
    if order == "xyz":
        return _rx(ax) @ _ry(ay) @ _rz(az)
    return _rz(az) @ _ry(ay) @ _rx(ax)


# --------------------------------------------------------------------------- #
# 処方
# --------------------------------------------------------------------------- #
def _coating(c, what, op):
    """膜の指定を検証して正規形に(None / "bare" / 材料名 = λ/4 単層 / [(材料, nm), ...] / {"R": r})。"""
    if c is None or c == "bare":
        return None
    if isinstance(c, str):
        return {"quarter_wave": c.strip().upper()}
    if isinstance(c, dict):
        if set(c) == {"R"}:
            r = _num(c["R"], "%s reflectance" % what, op)
            if not 0.0 <= r <= 1.0:
                raise ValueError("%s: %s reflectance must lie in [0, 1], got %r" % (op, what, r))
            return {"R": r}
        if "quarter_wave" in c and set(c) <= {"quarter_wave", "design_wavelength_um"}:
            out = {"quarter_wave": str(c["quarter_wave"]).strip().upper()}
            if "design_wavelength_um" in c:
                out["design_wavelength_um"] = _num(c["design_wavelength_um"], "design_wavelength_um", op, positive=True)
            return out
        raise ValueError("%s: %s coating dict must be {'R': r} or {'quarter_wave': material[, design_wavelength_um]}"
                         % (op, what))
    if isinstance(c, (list, tuple)):
        layers = []
        for i, item in enumerate(c):
            if not isinstance(item, (list, tuple)) or len(item) != 2 or not isinstance(item[0], str):
                raise ValueError("%s: %s coating layer %d must be (material, thickness_nm)" % (op, what, i))
            layers.append((item[0], _num(item[1], "%s layer %d thickness" % (what, i), op, nonneg=True)))
        return {"layers": layers}
    raise ValueError("%s: %s coating must be None, 'bare', a material name, a layer list or {'R': r}, got %r"
                     % (op, what, c))


def _surface_record(s, i, wl, op):
    _keys(s, _SURFACE_KEYS, "element %d (surface)" % i, op)
    if "R" not in s:
        raise ValueError("%s: element %d: a surface needs R" % (op, i))
    R = RT._radius(s.get("R"), "element %d R" % i)
    mirror = s.get("mirror", False)
    if not isinstance(mirror, (bool, np.bool_)):
        raise ValueError("%s: element %d: mirror must be True/False" % (op, i))
    bs = s.get("beamsplitter", None)
    if bs is not None:
        if not isinstance(bs, dict) or not set(bs) <= {"R", "branch"}:
            raise ValueError("%s: element %d: beamsplitter must be {'R': r, 'branch': 'transmit'|'reflect'}" % (op, i))
        r = _num(bs.get("R", 0.5), "element %d beamsplitter R" % i, op)
        if not 0.0 < r < 1.0:
            raise ValueError("%s: element %d: beamsplitter R must lie in (0, 1), got %r" % (op, i, r))
        br = bs.get("branch", "transmit")
        if br not in ("transmit", "reflect"):
            raise ValueError("%s: element %d: branch must be 'transmit' or 'reflect', got %r" % (op, i, br))
        if mirror:
            raise ValueError("%s: element %d: a surface cannot be both a mirror and a beamsplitter" % (op, i))
        bs = {"R": r, "branch": br}
    reflect = bool(mirror) or (bs is not None and bs["branch"] == "reflect")
    if "n" not in s and not reflect:
        raise ValueError("%s: element %d: a refracting surface needs n (the medium after it)" % (op, i))
    med = s.get("n", None)
    n_val = None if med is None else RT.refractive_index(med, wl)
    k = _num(s.get("k", 0.0), "element %d k" % i, op)
    ap = s.get("ap", None)
    ap = None if ap is None else _num(ap, "element %d ap" % i, op, positive=True)
    dec = _pair(s.get("decenter", (0.0, 0.0)), "element %d decenter" % i, op)
    tilt = _pair(s.get("tilt", (0.0, 0.0)), "element %d tilt" % i, op)
    asph = s.get("asph", None)
    if asph is None:
        asph = ()
    elif isinstance(asph, (int, float, bool, str)):
        raise ValueError("%s: element %d: asph must be a sequence (A4, A6, ...)" % (op, i))
    else:
        asph = tuple(_num(a, "element %d asph[%d]" % (i, j), op) for j, a in enumerate(asph))
        if len(asph) > 8:
            raise ValueError("%s: element %d: at most 8 aspheric coefficients" % (op, i))
        while asph and asph[-1] == 0.0:
            asph = asph[:-1]
    if math.isfinite(R) and k > -1.0 and ap is not None and (1.0 + k) * (ap / R) ** 2 > 1.0:
        raise ValueError("%s: element %d: semi-aperture %.3g exceeds the conic's extent for R=%.3g" % (op, i, ap, R))
    t = s.get("t", None)
    t = None if t is None else _num(t, "element %d t" % i, op, nonneg=True)
    return {"kind": "surface", "R": R, "k": k, "asph": asph, "n": med, "n_value": n_val, "ap": ap,
            "mirror": bool(mirror), "beamsplitter": bs, "reflect": reflect, "decenter": dec, "tilt": tilt,
            "coating": _coating(s.get("coating", None), "element %d" % i, op), "t": t,
            "label": str(s.get("label", ""))}


def _break_record(s, i, recs, op):
    _keys(s, _BREAK_KEYS, "element %d (break)" % i, op)
    t = _tnone(s, i, op)
    if "undo" in s:
        if set(s) - {"type", "undo", "t", "label"}:
            raise ValueError("%s: element %d: an 'undo' break takes only undo / t" % (op, i))
        j = s["undo"]
        if isinstance(j, (bool, np.bool_)) or not isinstance(j, (int, np.integer)) or not 0 <= int(j) < len(recs) \
                or recs[int(j)]["kind"] != "break":
            raise ValueError("%s: element %d: undo must be the record index of an earlier break, got %r" % (op, i, j))
        b = recs[int(j)]
        return {"kind": "break", "decenter": (-b["decenter"][0], -b["decenter"][1]),
                "tilt": (-b["tilt"][0], -b["tilt"][1], -b["tilt"][2]),
                "order": "zyx" if b["order"] == "xyz" else "xyz", "t": t, "label": str(s.get("label", ""))}
    order = s.get("order", "xyz")
    if order not in ("xyz", "zyx"):
        raise ValueError("%s: element %d: order must be 'xyz' (decenter, then x→y→z) or 'zyx', got %r" % (op, i, order))
    tl = s.get("tilt", (0.0, 0.0, 0.0))
    if hasattr(tl, "__len__") and len(tl) == 2:
        tl = (tl[0], tl[1], 0.0)
    return {"kind": "break", "decenter": _pair(s.get("decenter", (0.0, 0.0)), "element %d decenter" % i, op),
            "tilt": _pair(tl, "element %d tilt" % i, op, n=3), "order": order, "t": t,
            "label": str(s.get("label", ""))}


def _expand(elements, wl, op):
    """利用者の要素の列 → 素の記録(surface / break / return)の列。"""
    recs = []
    for i, s in enumerate(elements):
        if isinstance(s, (tuple, list)):
            keys = ("R", "t", "n", "k", "ap")
            if len(s) > len(keys):
                raise ValueError("%s: element %d: a tuple is (R, t, n[, k[, ap]])" % (op, i))
            s = {k: v for k, v in zip(keys, s)}
        if not isinstance(s, dict):
            raise ValueError("%s: element %d must be a dict or a (R, t, n) tuple, got %r" % (op, i, type(s).__name__))
        kind = s.get("type", "surface")
        if kind == "surface":
            recs.append(_surface_record(s, i, wl, op))
        elif kind == "break":
            recs.append(_break_record(s, i, recs, op))
        elif kind == "return":
            _keys(s, _RETURN_KEYS, "element %d (return)" % i, op)
            j = s.get("to")
            if isinstance(j, (bool, np.bool_)) or not isinstance(j, (int, np.integer)) or not 0 <= int(j) < len(recs):
                raise ValueError("%s: element %d: 'to' must be an earlier record index, got %r" % (op, i, j))
            recs.append({"kind": "return", "to": int(j), "t": _tnone(s, i, op),
                         "label": str(s.get("label", ""))})
        elif kind == "fold_mirror":
            _keys(s, _FOLD_KEYS, "element %d (fold_mirror)" % i, op)
            ax, ay = _pair(s.get("tilt", (45.0, 0.0)), "element %d tilt" % i, op)
            if abs(ax) >= 90.0 or abs(ay) >= 90.0:
                raise ValueError("%s: element %d: a fold tilt must lie in (-90, 90) degrees" % (op, i))
            lab = str(s.get("label", "fold"))
            recs.append({"kind": "break", "decenter": (0.0, 0.0), "tilt": (ax, ay, 0.0), "order": "xyz", "t": 0.0,
                         "label": lab + ":in", "auto": True})
            refl = s.get("reflectance", None)
            m = _surface_record({"R": s.get("R", INF), "k": s.get("k", 0.0), "asph": s.get("asph", None),
                                 "ap": s.get("ap", None), "mirror": True, "t": 0.0, "label": lab,
                                 "coating": None if refl is None else {"R": refl}}, i, wl, op)
            recs.append(m)
            recs.append({"kind": "break", "decenter": (0.0, 0.0), "tilt": (ax, -ay, 0.0), "order": "zyx",
                         "t": _tnone(s, i, op), "label": lab + ":out", "auto": True})
        elif kind == "plate":
            _keys(s, _PLATE_KEYS, "element %d (plate)" % i, op)
            th = _num(s.get("thickness", 1.0), "element %d thickness" % i, op, positive=True)
            ax, ay = _pair(s.get("tilt", (45.0, 0.0)), "element %d tilt" % i, op)
            if abs(ax) >= 90.0 or abs(ay) >= 90.0:
                raise ValueError("%s: element %d: a plate tilt must lie in (-90, 90) degrees" % (op, i))
            wx, wy = _pair(s.get("wedge", (0.0, 0.0)), "element %d wedge" % i, op)
            med = s.get("n", "BK7")
            lab = str(s.get("label", "plate"))
            bs = s.get("beamsplitter", None)
            branch = s.get("branch", "transmit")
            if branch not in ("transmit", "reflect"):
                raise ValueError("%s: element %d: branch must be 'transmit' or 'reflect'" % (op, i))
            if bs is not None:
                bs = {"R": _num(bs, "element %d beamsplitter" % i, op)} if not isinstance(bs, dict) else dict(bs)
                bs["branch"] = branch
            elif branch == "reflect":
                raise ValueError("%s: element %d: branch 'reflect' needs a beamsplitter reflectance" % (op, i))
            gap = _tnone(s, i, op)
            first = len(recs)
            recs.append({"kind": "break", "decenter": (0.0, 0.0), "tilt": (ax, ay, 0.0), "order": "xyz", "t": 0.0,
                         "label": lab + ":in", "auto": True})
            if branch == "reflect":
                recs.append(_surface_record({"R": INF, "ap": s.get("ap"), "beamsplitter": bs, "t": 0.0,
                                             "label": lab + ":front", "coating": s.get("coating_front")}, i, wl, op))
                recs.append({"kind": "break", "decenter": (0.0, 0.0), "tilt": (ax, -ay, 0.0), "order": "zyx",
                             "t": gap, "label": lab + ":out", "auto": True})
            else:
                front = {"R": INF, "n": med, "ap": s.get("ap"), "t": th, "label": lab + ":front",
                         "coating": s.get("coating_front")}
                if bs is not None:
                    front["beamsplitter"] = bs
                recs.append(_surface_record(front, i, wl, op))
                recs.append(_surface_record({"R": INF, "n": 1.0, "ap": s.get("ap"), "t": 0.0, "tilt": (wx, wy),
                                             "label": lab + ":back", "coating": s.get("coating_back")}, i, wl, op))
                recs.append({"kind": "return", "to": first, "t": gap, "label": lab + ":out", "auto": True})
        else:
            raise ValueError("%s: element %d: unknown type %r (surface / break / return / fold_mirror / plate)"
                             % (op, i, kind))
        if len(recs) > _MAX_RECORDS:
            raise ValueError("%s: more than %d records" % (op, _MAX_RECORDS))
    return recs


def _from_lens_system(system, op):
    """``raytrace.lens_system`` の処方 → 素の記録。鏡の後は座標系が反転するので R・非球面・偏心 y・傾き y の符号を返す。"""
    recs = []
    sign = 1.0
    system = RT._solved(system)
    if system.get("image_R", INF) != INF or system.get("afocal") or             any(s.get("a2") or s.get("odd") for s in system["surfaces"]):
        raise ValueError("%s: the non-coaxial tracer does not read a curved image surface, an afocal flag or the "
                         "a2 / odd (odd-asphere) sag terms of raytrace.lens_system" % op)
    for i, s in enumerate(system["surfaces"]):
        R = s["R"] if s["R"] == INF else sign * s["R"]
        asph = tuple(sign * a for a in s["asph"]) if sign < 0 else tuple(s["asph"])
        dec = (s["decenter"][0], sign * s["decenter"][1]) if sign < 0 else tuple(s["decenter"])
        tilt = (s["tilt"][0], sign * s["tilt"][1]) if sign < 0 else tuple(s["tilt"])
        recs.append({"kind": "surface", "R": R, "k": s["k"], "asph": asph, "n": s["n"],
                     "n_value": s["n_value"], "ap": s["ap"], "mirror": bool(s["mirror"]), "beamsplitter": None,
                     "reflect": bool(s["mirror"]), "decenter": dec, "tilt": tilt, "coating": None,
                     "t": s["t"], "label": ""})
        if s["mirror"]:
            sign = -sign
    return recs


def noncoaxial_system(elements=None, stop=None, object_mm=INF, wavelength_um=WL_D, index_object=1.0, field=(0.0, 0.0),
             image_mm=None, image_tilt=(0.0, 0.0), object_tilt=(0.0, 0.0)):
    """Build a validated non-coaxial sequential system (``table``) — surfaces, coordinate breaks, folds, plates.

    *elements* is a list of dicts (``"type"`` defaults to ``"surface"``), or the dict returned by
    ``raytrace.lens_system`` (converted exactly; its traces then equal ``raytrace``'s to 1e-12):

    * ``{"type": "surface", "R", "t", "n", "k", "ap", "mirror", "asph", "decenter", "tilt", "coating",
      "beamsplitter": {"R": r, "branch": "transmit"|"reflect"}}`` — as in ``raytrace.lens_system``;
      ``decenter`` / ``tilt`` act on that surface only. ``coating`` is used by the ghost analysis
      (None / ``"bare"``, a material name = a quarter-wave single layer, ``[(material, nm), ...]`` from the
      incident side, or ``{"R": r}``).
    * ``{"type": "break", "decenter": (dx, dy), "tilt": (ax, ay, az), "order": "xyz"|"zyx", "t"}`` — a
      coordinate break (decenter, then rotate about x, the new y, the new z; degrees) that moves every later
      surface; ``{"type": "break", "undo": j}`` is the exact inverse of break record *j*.
    * ``{"type": "return", "to": j, "t"}`` — go back to the coordinate system at the entry of record *j*.
    * ``{"type": "fold_mirror", "tilt": (ax, ay), "t", "ap", "R", "reflectance"}`` — a mirror tilted by
      (ax, ay); the axis is reflected (45° folds by 90°) and ``t`` runs along the folded axis.
    * ``{"type": "plate", "thickness", "n", "tilt": (ax, ay), "wedge": (wx, wy), "t", "beamsplitter": r,
      "branch", "coating_front", "coating_back"}`` — a tilted plane-parallel (or wedged) plate, or a plate
      beamsplitter; ``t`` is measured from the front vertex along the incoming axis (transmit branch) or
      along the reflected axis (reflect branch).

    *stop* is the **record** index of the aperture stop (default: the first surface); *field* is
    ``(fx, fy)`` (degrees for an object at infinity, mm otherwise); *image_tilt* / *object_tilt* tilt the
    image / object plane about the local x and y axes (degrees; Scheimpflug). The last record's ``t`` is the
    distance to the image plane (``None`` = the paraxial focus along the axis ray).

    Default: a singlet f ≈ 100 mm followed by a 45° fold mirror (the image lands along +y).
    """
    op = "noncoaxial_system"
    wl = _num(wavelength_um, "wavelength_um", op, positive=True)
    source = None
    stop_arg, image_arg, index_arg = stop, image_mm, index_object
    if elements is None:                                  # 既定: 単レンズ + 45° の折り返し(引数はそのまま効く)
        elements = [{"R": 51.68, "t": 5.0, "n": (1.5168, 64.17), "ap": 12.5, "label": "L1"},
                    {"R": INF, "t": 40.0, "n": 1.0},
                    {"type": "fold_mirror", "tilt": (45.0, 0.0), "ap": 30.0, "t": None, "label": "M1"}]
        stop = 0 if stop is None else stop
    if isinstance(elements, dict) and "surfaces" in elements and "stop" in elements:
        source = elements
        recs = _from_lens_system(source, op)
        if stop is None:
            stop = source["stop"]
        object_mm = source["object_mm"]
        wl = source["wavelength_um"]
        index_object = source["index_object"]
        if field == (0.0, 0.0):
            field = (0.0, source["field"])
        if image_mm is None:
            image_mm = source["image_mm"]
    elif isinstance(elements, (list, tuple)) and len(elements) > 0:
        recs = _expand(list(elements), wl, op)
    else:
        raise ValueError("%s: elements must be a non-empty list or a raytrace.lens_system dict" % op)
    surf_idx = [i for i, r in enumerate(recs) if r["kind"] == "surface"]
    if not surf_idx:
        raise ValueError("%s: the system has no surface" % op)
    for i, r in enumerate(recs[:-1]):
        if r["t"] is None:
            raise ValueError("%s: record %d: only the last record may omit t" % (op, i))
    if stop is None:
        stop = surf_idx[0]
    if isinstance(stop, str):
        hits = [i for i in surf_idx if recs[i]["label"] == stop]
        if len(hits) != 1:
            raise ValueError("%s: stop label %r matches %d surfaces (labels: %s)"
                             % (op, stop, len(hits), [recs[i]["label"] for i in surf_idx]))
        stop = hits[0]
    if isinstance(stop, (bool, np.bool_)) or not isinstance(stop, (int, np.integer)) or int(stop) not in surf_idx:
        raise ValueError("%s: stop must be the record index of a surface (%s), got %r" % (op, surf_idx, stop))
    stop = int(stop)
    if recs[stop]["ap"] is None:
        aps = [recs[i]["ap"] for i in surf_idx if recs[i]["ap"] is not None]
        if not aps:
            raise ValueError("%s: the stop surface needs a semi-aperture 'ap'" % op)
        recs[stop] = dict(recs[stop]); recs[stop]["ap"] = min(aps)
    obj = float(object_mm)
    if obj != INF and (not math.isfinite(obj) or obj <= 0):
        raise ValueError("%s: object_mm must be > 0 or inf, got %r" % (op, object_mm))
    fld = _pair(field, "field", op)
    if obj == INF and max(abs(fld[0]), abs(fld[1])) >= 89.0:
        raise ValueError("%s: a field angle must lie within ±89°" % op)
    it = _pair(image_tilt, "image_tilt", op)
    ot = _pair(object_tilt, "object_tilt", op)
    if max(abs(v) for v in it + ot) >= 89.0:
        raise ValueError("%s: image / object tilts must lie within ±89°" % op)
    if obj == INF and ot != (0.0, 0.0):
        raise ValueError("%s: an object at infinity cannot be tilted" % op)
    n0 = RT.refractive_index(index_object, wl)
    sysd = {"kind": "noncoaxial_system", "records": recs, "stop": stop, "object_mm": obj, "wavelength_um": wl,
            "index_object": n0, "field": fld, "image_mm": None if image_mm is None else _num(image_mm, "image_mm", op),
            "image_tilt": it, "object_tilt": ot, "source": source,
            "elements": None if source is not None else [dict(e) if isinstance(e, dict) else e for e in elements],
            "stop_arg": stop_arg, "image_mm_arg": image_arg, "index_object_arg": index_arg}
    _media(sysd)                                              # validates that every refracting surface has a medium
    if sysd["image_mm"] is None and recs[-1]["t"] is None:
        sysd["image_mm"] = _default_image(sysd)
    return sysd


def _check(sysd, op):
    if isinstance(sysd, dict) and "surfaces" in sysd and "stop" in sysd:
        return noncoaxial_system(sysd)
    if not isinstance(sysd, dict) or sysd.get("kind") != "noncoaxial_system" or "records" not in sysd:
        raise ValueError("%s: expected the table returned by noncoaxial_system() (or raytrace.lens_system()), got %r"
                         % (op, type(sysd).__name__))
    return sysd


# --------------------------------------------------------------------------- #
# 配置(各面の大域の姿勢)
# --------------------------------------------------------------------------- #
def _image_tilt_basis(tilt):
    """傾けた像面 ``z = x·tan(ty) + y·tan(tx)`` の正規直交基底(傾けない像の座標系で、列 = 局所の x, y, 法線)。

    x 軸は面と xz 面の交線、法線は光の進む +z の側、y = 法線 × x(右手系)。傾き 0 なら厳密に単位行列。
    """
    tx, ty = tilt
    if tx == 0.0 and ty == 0.0:
        return np.eye(3)
    gx, gy = math.tan(math.radians(ty)), math.tan(math.radians(tx))
    u = np.array([1.0, 0.0, gx])
    u /= np.linalg.norm(u)
    nrm = np.array([-gx, -gy, 1.0])
    nrm /= np.linalg.norm(nrm)
    v = np.cross(nrm, u)
    return np.stack([u, v, nrm], 1)


def _layout(sysd, image_mm=None):
    """各記録の入口の座標系と、面の姿勢 (R, o)、像面の座標系を返す。``local = (P − o) @ R``。

    ``image`` は傾けない像の座標系 (F, o)、``image_plane`` は傾けた像面そのものの回転(F @ 傾きの基底)。"""
    recs = sysd["records"]
    F = np.eye(3)
    o = np.zeros(3)
    entry, poses = [], []
    last_t = None
    for k, r in enumerate(recs):
        entry.append((F.copy(), o.copy()))
        if r["kind"] == "surface":
            Rg = F @ RT._rot(*r["tilt"])
            og = o + F @ np.array([r["decenter"][0], r["decenter"][1], 0.0])
            poses.append((Rg, og))
            if r["reflect"]:
                F = F @ _REV
        elif r["kind"] == "break":
            B = _break_matrix(r["tilt"], r["order"])
            d = np.array([r["decenter"][0], r["decenter"][1], 0.0])
            if r["order"] == "xyz":
                o = o + F @ d
                F = F @ B
            else:
                F = F @ B
                o = o + F @ d
            poses.append(None)
        else:
            F, o = entry[r["to"]]
            F, o = F.copy(), o.copy()
            poses.append(None)
        last_t = r["t"]
        if r["t"] is not None:
            o = o + F @ np.array([0.0, 0.0, r["t"]])
    # 像面: raytrace.trace_rays と同じ順序の演算(最後の t を一度足して引き戻してから像距離を足す)
    if last_t is not None:
        o_last = o - F @ np.array([0.0, 0.0, last_t])
    else:
        o_last = o
    if image_mm is None:
        image_mm = sysd["image_mm"]
    if image_mm is None:
        image_mm = last_t
    if image_mm is None:
        raise ValueError("the image distance is undefined (give the last t or image_mm)")
    o_img = o_last + F @ np.array([0.0, 0.0, image_mm])
    return {"entry": entry, "poses": poses, "image": (F, o_img), "image_mm": float(image_mm),
            "image_plane": F @ _image_tilt_basis(sysd["image_tilt"])}


def _media(sysd):
    """各面の前後の媒質の屈折率(通常の経路での値)。"""
    recs = sysd["records"]
    wl = sysd["wavelength_um"]
    n = float(sysd["index_object"])
    before, after = {}, {}
    for k, r in enumerate(recs):
        if r["kind"] != "surface":
            continue
        before[k] = n
        if not r["reflect"]:
            if r["n"] is None:
                raise ValueError("record %d: a refracting surface needs n" % k)
            n = RT.refractive_index(r["n"], wl)
        after[k] = n
    return before, after


def _nominal_path(sysd):
    return [(k, "reflect" if r["reflect"] else "refract", +1) for k, r in enumerate(sysd["records"])
            if r["kind"] == "surface"]


# --------------------------------------------------------------------------- #
# 追跡の核
# --------------------------------------------------------------------------- #
def _trace(sysd, P, D, path=None, wavelength_um=None, image_mm=None, layout=None, apertures=True):
    """光線 (P, D) を経路 *path*(記録の番号・働き・向き)に沿って像面まで追う。

    ``raytrace.trace_rays`` と同じ演算(局所へ ``(P − o) @ R``、``_intersect_surface``、法線を入射に向けて
    反転、屈折 ``η D + (η cos i − cos t) N``・反射 ``D − 2(N·D)N``、正規化、大域へ ``Q @ Rᵀ + o``)。
    """
    if path is None:
        path = _nominal_path(sysd)
    wl = sysd["wavelength_um"] if wavelength_um is None else wavelength_um
    lay = layout if layout is not None else _layout(sysd, image_mm)
    recs = sysd["records"]
    if wl == sysd["wavelength_um"]:
        before, after = _media(sysd)
    else:
        before, after = _media(dict(sysd, wavelength_um=wl))
    P = np.array(P, dtype=np.float64)
    D = np.array(D, dtype=np.float64)
    D = D / np.linalg.norm(D, axis=1, keepdims=True)
    N = len(P)
    n_before = float(sysd["index_object"])
    pts, dirs = [P.copy()], [D.copy()]
    opl = np.zeros(N)
    valid = np.ones(N, bool)
    for (k, act, sense) in path:
        r = recs[k]
        Rm, off = lay["poses"][k]
        c = 0.0 if r["R"] == INF else 1.0 / r["R"]
        Pl = (P - off) @ Rm
        Dl = D @ Rm
        t = RT._intersect_surface(Pl, Dl, c, r["k"], r["asph"])
        bad = ~np.isfinite(t) | (t < -1e-9)
        t = np.where(bad, np.nan, t)
        Q = Pl + t[:, None] * Dl
        if apertures and r["ap"] is not None:
            rr = np.hypot(Q[:, 0], Q[:, 1])
            bad |= rr > r["ap"] * (1.0 + 1e-12)
        nrm = RT._surface_normal(Q, c, r["k"], r["asph"])
        flip = np.sum(nrm * Dl, axis=1) > 0
        nrm[flip] *= -1.0
        cos_i = -np.sum(nrm * Dl, axis=1)
        if act == "reflect":
            Dn = Dl - 2.0 * np.sum(nrm * Dl, axis=1)[:, None] * nrm
            n_after = n_before
        else:
            n_after = after[k] if sense > 0 else before[k]
            eta = n_before / n_after
            sin2_t = eta * eta * (1.0 - cos_i * cos_i)
            bad |= sin2_t > 1.0
            cos_t = np.sqrt(np.clip(1.0 - sin2_t, 0.0, None))
            Dn = eta * Dl + (eta * cos_i - cos_t)[:, None] * nrm
        Dn = Dn / np.linalg.norm(Dn, axis=1, keepdims=True)
        opl += n_before * np.abs(t)
        Pg = Q @ Rm.T + off
        Dg = Dn @ Rm.T
        valid &= ~bad
        Pg[~valid] = np.nan
        Dg[~valid] = np.nan
        pts.append(Pg)
        dirs.append(Dg)
        P, D = Pg, Dg
        n_before = n_after
    Fi, oi = lay["image"]
    Ri = Fi
    Pl = (P - oi) @ Ri
    Dl = D @ Ri
    tx, ty = sysd["image_tilt"]
    with np.errstate(divide="ignore", invalid="ignore"):
        if tx == 0.0 and ty == 0.0:
            den = Dl[:, 2]
            tt = -Pl[:, 2] / Dl[:, 2]
        else:
            gx, gy = math.tan(math.radians(ty)), math.tan(math.radians(tx))
            den = Dl[:, 2] - gy * Dl[:, 1] - gx * Dl[:, 0]
            tt = (gy * Pl[:, 1] + gx * Pl[:, 0] - Pl[:, 2]) / den
    Qg = P + tt[:, None] * D
    opl += n_before * np.abs(tt)
    # ★光線が像面とほぼ平行・逆向き(像面の +z へ進まない)なら像面に届かない —— 無効にする。
    #   以前の raytrace は傾いた鏡の後で D_z ≈ 1e-17 の光線を巨大な有限の点(rms 3e18 mm)として有効に数えた。
    valid &= np.isfinite(tt) & (den > _MIN_DZ)
    Qg[~valid] = np.nan
    pts.append(Qg)
    # ★局所座標は傾いた像面そのものの基底で取る(以前は傾けない座標系へ射影し、傾けた向きが cos θ' 倍に縮んでいた)
    loc = (Qg - oi) @ lay["image_plane"]
    return {"points": np.stack(pts, 1), "dirs": np.stack(dirs, 1), "opl": opl, "valid": valid,
            "image_local": loc, "image_mm": lay["image_mm"], "n_image": float(n_before), "layout": lay}


# --------------------------------------------------------------------------- #
# 光線の打ち出しと狙い
# --------------------------------------------------------------------------- #
def _field_dir(fx, fy):
    if fx == 0.0:
        th = math.radians(fy)
        return np.array([0.0, math.sin(th), math.cos(th)])
    d = np.array([math.tan(math.radians(fx)), math.tan(math.radians(fy)), 1.0])
    return d / np.linalg.norm(d)


def _object_point(sysd, fx, fy):
    tx, ty = sysd["object_tilt"]
    z = -sysd["object_mm"] + fy * math.tan(math.radians(tx)) + fx * math.tan(math.radians(ty))
    return np.array([fx, fy, z])


def _object_frame(sysd):
    """物体空間の座標系 = 最初の面より前に**利用者が置いた**座標の切り替えを当てた座標系 (F, o)。無ければ None。"""
    F = np.eye(3)
    o = np.zeros(3)
    moved = False
    for r in sysd["records"]:
        if r["kind"] == "surface" or r.get("auto"):     # 平板・折り返しの展開が作った切り替えは物体空間ではない
            break
        moved = True
        if r["kind"] == "break":
            B = _break_matrix(r["tilt"], r["order"])
            d = np.array([r["decenter"][0], r["decenter"][1], 0.0])
            if r["order"] == "xyz":
                o = o + F @ d
                F = F @ B
            else:
                F = F @ B
                o = o + F @ d
        o = o + F @ np.array([0.0, 0.0, r["t"]])
    return (F, o) if moved else None


def _launch_xy(sysd, X, Y, field, z_ref=0.0):
    """物体空間の座標系の基準面 z = z_ref の点 (X, Y) を通る光線(無限遠なら視野の方向、有限なら物点から)。

    物体空間の座標系は、最初の面より前に座標の切り替えがあればそれを当てたもの(照明の枝のように横から入る系)。
    無ければ大域そのもの(共軸の処方の打ち出しは raytrace と同じ数になる)。
    """
    P, D, opl0 = _launch_local(sysd, X, Y, field, z_ref)
    fr = _object_frame(sysd)
    if fr is not None:
        F, o = fr
        P = P @ F.T + o
        D = D @ F.T
    return P, D, opl0


def _launch_local(sysd, X, Y, field, z_ref=0.0):
    fx, fy = field
    n = len(X)
    if sysd["object_mm"] == INF:
        d = _field_dir(fx, fy)
        D = np.tile(d, (n, 1))
        z0 = min(z_ref, 0.0) - max(10.0, abs(z_ref) + 1.0)
        s = (z0 - z_ref) / D[:, 2]
        P = np.stack([X, Y, np.full(n, z_ref)], 1) + s[:, None] * D
        opl0 = float(sysd["index_object"]) * np.sum(P * D, axis=1)
    else:
        P0 = _object_point(sysd, fx, fy)
        T = np.stack([X, Y, np.full(n, z_ref)], 1)
        D = T - P0
        D = D / np.linalg.norm(D, axis=1, keepdims=True)
        P = np.tile(P0, (n, 1))
        opl0 = np.zeros(n)
    return P, D, opl0


def _stop_xy(sysd, P, D, layout=None):
    stop = sysd["stop"]
    path = [p for p in _nominal_path(sysd) if p[0] <= stop]
    tr = _trace(sysd, P, D, path=path, layout=layout, apertures=False)    # 狙いの途中は口径で切らない
    Rm, off = tr["layout"]["poses"][stop]
    q = (tr["points"][:, -2, :] - off) @ Rm                  # the point on the stop surface, local
    return q[:, :2]


def _aim(sysd, targets, field, layout=None, z_ref=0.0, iters=30):
    """各光線を絞りの局所の点 *targets* (N,2) へ狙う(ベクトル化した Newton 法、差分のヤコビアン)。"""
    tg = np.asarray(targets, float)
    ap = sysd["records"][sysd["stop"]]["ap"]
    # 初期値: 絞りの点を大域へ置き、光線の向き(無限遠)か物点(有限)から基準面 z_ref へ直線で引き戻す
    #   (絞りの前の面の屈折は無視 —— 偏心した絞りでも最初の光線が絞りに当たるように)
    lay0 = layout if layout is not None else _layout(sysd)
    Rs, os_ = lay0["poses"][sysd["stop"]]
    T = np.stack([tg[:, 0], tg[:, 1], np.zeros(len(tg))], 1) @ Rs.T + os_
    fr = _object_frame(sysd)
    if fr is not None:
        T = (T - fr[1]) @ fr[0]
    if sysd["object_mm"] == INF:
        d = _field_dir(*field)
        s0 = (z_ref - T[:, 2]) / d[2]
        X, Y = T[:, 0] + s0 * d[0], T[:, 1] + s0 * d[1]
    else:
        P0 = _object_point(sysd, *field)
        u = (z_ref - P0[2]) / (T[:, 2] - P0[2])
        X, Y = P0[0] + u * (T[:, 0] - P0[0]), P0[1] + u * (T[:, 1] - P0[1])
    h = 1e-5 * max(ap, 1.0)
    ok = np.ones(len(X), bool)
    for _ in range(iters):
        P, D, _ = _launch_xy(sysd, X, Y, field, z_ref)
        q = _stop_xy(sysd, P, D, layout)
        e = q - tg
        fin = np.all(np.isfinite(e), 1)
        ok &= fin
        if np.all(np.abs(e[ok]) < 1e-11 * max(ap, 1.0)):
            break
        P1, D1, _ = _launch_xy(sysd, X + h, Y, field, z_ref)
        P2, D2, _ = _launch_xy(sysd, X, Y + h, field, z_ref)
        qx = _stop_xy(sysd, P1, D1, layout)
        qy = _stop_xy(sysd, P2, D2, layout)
        a, b = (qx[:, 0] - q[:, 0]) / h, (qy[:, 0] - q[:, 0]) / h
        c, d = (qx[:, 1] - q[:, 1]) / h, (qy[:, 1] - q[:, 1]) / h
        det = a * d - b * c
        with np.errstate(divide="ignore", invalid="ignore"):
            sx = (d * e[:, 0] - b * e[:, 1]) / det
            sy = (-c * e[:, 0] + a * e[:, 1]) / det
        good = np.isfinite(sx) & np.isfinite(sy)
        ok &= good
        X = np.where(good, X - sx, X)
        Y = np.where(good, Y - sy, Y)
    P, D, opl0 = _launch_xy(sysd, X, Y, field, z_ref)
    q = _stop_xy(sysd, P, D, layout)
    ok &= np.all(np.isfinite(q), 1) & (np.hypot(*(q - tg).T) < 1e-6 * max(ap, 1.0))
    return P, D, opl0, ok


def _pupil(rings, kind="hexapolar"):
    return RT._pupil_grid(rings, kind)


def _bundle(sysd, field, rings=6, pupil_fill=1.0, kind="hexapolar", path=None, image_mm=None):
    """視野 *field* の瞳を満たす束。共軸の処方から作った系は ``raytrace`` の打ち出し(近軸の入射瞳 + 主光線の補正)と
    同じ光線を、それ以外は絞りの点を 1 本ずつ狙った光線を出す。"""
    px, py = _pupil(rings, kind)
    src = sysd["source"]
    lay = _layout(sysd, image_mm)
    if src is not None and field[0] == 0.0 and src["object_mm"] == sysd["object_mm"] and \
            sysd["object_tilt"] == (0.0, 0.0):
        para = RT._para_at(src)
        dpx, dpy = RT._chief_offset(src, field[1], para)
        P, D, opl0 = RT._launch(src, px + dpx, py + dpy, field[1], para, pupil_fill)
        ok = np.ones(len(px), bool)
    else:
        ap = sysd["records"][sysd["stop"]]["ap"]
        tg = np.stack([px, py], 1) * ap * pupil_fill
        P, D, opl0, ok = _aim(sysd, tg, field, layout=lay)
    tr = _trace(sysd, P, D, path=path, layout=lay)
    tr["valid"] &= ok
    loc = tr["image_local"].copy()
    loc[~tr["valid"]] = np.nan
    ic = int(np.argmin(px * px + py * py))
    tr.update({"pupil": np.stack([px, py], 1), "opl0": opl0, "chief_index": ic, "image_xy": loc[:, :2],
               "chief_xy": loc[ic, :2].copy(), "field": tuple(field)})
    return tr


def _default_image(sysd):
    """最後の記録の t が無いとき、軸の光線に沿った近軸の焦点(接線と球欠の平均)までの距離。"""
    src = sysd["source"]
    if src is not None:
        return RT.paraxial_trace(src)["image_mm"]
    tmp = dict(sysd, image_mm=0.0)
    fp = _focus_point(tmp, (0.0, 0.0))
    if fp is None:
        raise ValueError("noncoaxial_system: cannot trace the axis ray to a focus (give the last t)")
    F, o = _layout(tmp)["image"]
    return float(((fp - o) @ F)[2])


def _axis_jacobians(sysd, field=(0.0, 0.0), h=1e-4):
    """無限遠の物体の軸上の平行束を、入口の面 z = 0 の上で (x, y) へ ±h だけずらして追い、
    (J_stop, J_out) を返す。J_stop = 絞りの局所 (x, y) の変化 / 入口のずれ(2×2)、
    J_out = 像側の方向の変化(軸光線に直交する 2 成分)/ 入口のずれ(2×2)。どちらも中心差分で、
    ``lensfile`` が入射瞳の直径 ENPD や像側 F 値を絞りの半径へ換算するのに使う(近軸量の実光線版)。"""
    lay = _layout(sysd)
    X = np.array([h, -h, 0.0, 0.0, 0.0])
    Y = np.array([0.0, 0.0, h, -h, 0.0])
    P, D, _ = _launch_xy(sysd, X, Y, field, 0.0)
    q = _stop_xy(sysd, P, D, lay)
    tr = _trace(sysd, P, D, layout=lay, apertures=False)
    Do = tr["dirs"][:, -1, :]
    if not (np.all(np.isfinite(q)) and np.all(np.isfinite(Do))):
        raise ValueError("the axial bundle does not reach the stop / image (give a stop that the axis ray passes)")
    d0 = Do[4] / np.linalg.norm(Do[4])
    a = np.array([1.0, 0.0, 0.0]) if abs(d0[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    e1 = np.cross(d0, a)
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(d0, e1)
    Js = np.array([[q[0, 0] - q[1, 0], q[2, 0] - q[3, 0]], [q[0, 1] - q[1, 1], q[2, 1] - q[3, 1]]]) / (2.0 * h)
    dx, dy = (Do[0] - Do[1]) / (2.0 * h), (Do[2] - Do[3]) / (2.0 * h)
    Jo = np.array([[e1 @ dx, e1 @ dy], [e2 @ dx, e2 @ dy]])
    return Js, Jo


# --------------------------------------------------------------------------- #
# op: 例・配置
# --------------------------------------------------------------------------- #
def noncoaxial_example(name="folded_singlet"):
    """A named non-coaxial example system (``table``): folds, a periscope, a beamsplitter, a tilted plate, Scheimpflug.

    ``"folded_singlet"`` (plano-convex BK7 f ≈ 100 mm, then a
    45° fold mirror 40 mm behind it — the image lands along +y), ``"periscope"`` (two parallel 45° mirrors:
    an even number of reflections), ``"coaxial_doublet"`` (``raytrace``'s cemented doublet converted —
    traces equal ``raytrace``), ``"tilted_plate"`` (a 5 mm BK7 plate tilted 30° in the converging beam of
    an f/10 singlet), ``"epi_beamsplitter"`` (a coaxial epi-illumination inspection lens: object → 45° plate
    beamsplitter, 3 mm BK7, R = 0.5 on the front face → doublet → sensor), ``"scheimpflug"`` (the doublet
    imaging a 30°-tilted object at 1:1-ish with the image plane tilted by the closed form) and
    ``"off_axis_parabola"`` (a paraboloid R = −200 used 36 mm off its axis, folded by its own tilt)."""
    op = "noncoaxial_example"
    if name == "folded_singlet":
        return noncoaxial_system([{"R": 51.68, "t": 5.0, "n": (1.5168, 64.17), "ap": 12.5, "label": "L1"},
                         {"R": INF, "t": 40.0, "n": 1.0},
                         {"type": "fold_mirror", "tilt": (45.0, 0.0), "ap": 30.0, "t": None, "label": "M1"}],
                        stop=0)
    if name == "periscope":
        return noncoaxial_system([{"R": 51.68, "t": 5.0, "n": (1.5168, 64.17), "ap": 12.5, "label": "L1"},
                         {"R": INF, "t": 20.0, "n": 1.0},
                         {"type": "fold_mirror", "tilt": (45.0, 0.0), "ap": 30.0, "t": 30.0, "label": "M1"},
                         {"type": "fold_mirror", "tilt": (-45.0, 0.0), "ap": 30.0, "t": None, "label": "M2"}],
                        stop=0)
    if name == "coaxial_doublet":
        return noncoaxial_system(RT.example_system("doublet"))
    if name == "tilted_plate":
        return noncoaxial_system([{"R": 51.68, "t": 5.0, "n": (1.5168, 64.17), "ap": 5.0, "label": "L1"},
                         {"R": INF, "t": 40.0, "n": 1.0},
                         {"type": "plate", "thickness": 5.0, "n": "BK7", "tilt": (30.0, 0.0), "ap": 20.0,
                          "t": None, "label": "P"}], stop=0)
    if name == "epi_beamsplitter":
        return noncoaxial_system([{"type": "plate", "thickness": 3.0, "n": "BK7", "tilt": (45.0, 0.0), "ap": 30.0,
                          "beamsplitter": 0.5, "branch": "transmit", "t": 30.0, "label": "BS"},
                         {"R": 61.47, "t": 6.0, "n": "BK7", "ap": 12.5, "label": "L1"},
                         {"R": -44.64, "t": 2.5, "n": "SF2", "label": "L2"},
                         {"R": -129.94, "t": None, "n": 1.0}],
                        stop="L1", object_mm=150.0, field=(0.0, 0.0))
    if name == "scheimpflug":
        d = RT.example_system("doublet")
        sch = scheimpflug_tilt(d, object_distance_mm=200.0, object_tilt_deg=30.0, verify=False)
        s3 = noncoaxial_system([dict(R=s["R"], t=s["t"], n=s["n"], ap=s["ap"]) for s in d["surfaces"][:-1]] +
                      [{"R": d["surfaces"][-1]["R"], "t": sch["image_distance_mm"], "n": 1.0}],
                      stop=0, object_mm=200.0, object_tilt=(30.0, 0.0), image_tilt=(sch["image_tilt_deg"], 0.0))
        return s3
    if name == "off_axis_parabola":
        return noncoaxial_system([{"R": INF, "n": 1.0, "ap": 8.0, "decenter": (0.0, 36.0), "t": 50.0, "label": "pupil"},
                         {"R": -200.0, "k": -1.0, "mirror": True, "ap": 60.0, "t": None, "label": "OAP"}],
                        stop=0)
    raise ValueError("%s: unknown example %r" % (op, name))


def noncoaxial_layout(system):
    """Global pose of every record (``table``): surface vertices, rotation matrices, the axis polyline.

    Per surface: ``vertex`` (mm, global), ``rotation`` (3×3, columns = the local x, y, z axes in global
    coordinates; ``local = (P − vertex) @ rotation``), ``euler_zyx_deg`` (the same rotation as
    ``Rz(γ)·Ry(β)·Rx(α)`` about the global axes — the extrinsic x-then-y-then-z form other ray tracers take for
    absolute placement), ``normal`` (the local +z) and the record's ``R`` / ``k`` / ``ap`` / ``mirror``.
    ``axis`` is the polyline of the frame origins (the mechanical axis), ``image`` the image-plane pose
    (with ``image_tilt`` its ``rotation`` / ``normal`` are those of the tilted plane itself).
    """
    sysd = _check(system, "noncoaxial_layout")
    lay = _layout(sysd)
    rows = []
    for k, r in enumerate(sysd["records"]):
        if r["kind"] != "surface":
            continue
        Rg, og = lay["poses"][k]
        rows.append({"record": k, "label": r["label"], "vertex": og.tolist(), "rotation": Rg.tolist(),
                     "euler_zyx_deg": _euler_zyx(Rg), "normal": Rg[:, 2].tolist(), "R": r["R"], "k": r["k"],
                     "ap": r["ap"], "mirror": r["mirror"], "beamsplitter": r["beamsplitter"],
                     "reflect": r["reflect"]})
    axis = [e[1].tolist() for e in lay["entry"]] + [lay["image"][1].tolist()]
    _, oi = lay["image"]
    Fi = lay["image_plane"]                     # 傾けた像面そのものの姿勢(列 = 局所の x, y, 法線)
    return {"surfaces": rows, "axis": axis, "image": {"origin": oi.tolist(), "rotation": Fi.tolist(),
                                                      "normal": Fi[:, 2].tolist(), "tilt": sysd["image_tilt"]},
            "image_mm": lay["image_mm"], "n_reflections": sum(1 for r in sysd["records"]
                                                                 if r["kind"] == "surface" and r["reflect"])}


def _euler_zyx(R):
    """R = Rz(γ)·Ry(β)·Rx(α) の (α, β, γ) [度]。"""
    b = math.asin(max(-1.0, min(1.0, -R[2, 0])))
    a = math.atan2(R[2, 1], R[2, 2])
    g = math.atan2(R[1, 0], R[0, 0])
    return [math.degrees(a), math.degrees(b), math.degrees(g)]


# --------------------------------------------------------------------------- #
# op: 追跡
# --------------------------------------------------------------------------- #
def _fields(sysd, fields, op):
    if fields is None:
        return [tuple(sysd["field"])]
    if isinstance(fields, (int, float)) and not isinstance(fields, bool):
        return [(0.0, _num(fields, "field", op))]
    out = []
    for f in fields:
        if isinstance(f, (int, float)) and not isinstance(f, bool):
            out.append((0.0, _num(f, "field", op)))
        else:
            out.append(_pair(f, "field", op))
    if not 1 <= len(out) <= 12:
        raise ValueError("%s: give 1..12 fields" % op)
    return out


def noncoaxial_trace(system, fields=None, rings=4, pupil_fill=1.0, branch=None):
    """Trace pupil-filling real-ray bundles through the 3-D system (``table``).

    Per field: ``image_xy`` (N,2) on the image plane in its local frame (with ``image_tilt``, coordinates on the
    tilted plane itself: distances on a tilted sensor, not their projection), ``valid``, ``points`` (N, n+2, 3)
    global polylines (start, every surface, image), ``chief`` (the chief-ray polyline and its image point),
    ``n_vignetted``. *fields* is a list of ``(fx, fy)`` pairs (or numbers = fy), default the system's field.
    Rays are aimed at the stop: a coaxial prescription converted from ``raytrace`` uses ``raytrace``'s own
    launch (so the numbers equal ``raytrace``'s); any other system aims every ray at its stop point by Newton
    iteration. *branch* overrides every beamsplitter's branch (``"transmit"`` / ``"reflect"``).
    """
    op = "noncoaxial_trace"
    sysd = _check(system, op)
    if branch is not None:
        sysd = _with_branch(sysd, branch, op)
    rings = int(_num(rings, "rings", op, positive=True))
    if rings > 40:
        raise ValueError("%s: rings must be <= 40" % op)
    pf = _num(pupil_fill, "pupil_fill", op, positive=True)
    if pf > 1.0:
        raise ValueError("%s: pupil_fill must be <= 1" % op)
    out = []
    for f in _fields(sysd, fields, op):
        b = _bundle(sysd, f, rings=rings, pupil_fill=pf)
        ic = b["chief_index"]
        out.append({"field": list(f), "image_xy": b["image_xy"], "valid": b["valid"],
                    "points": b["points"], "chief": {"points": b["points"][ic], "image_xy": b["chief_xy"]},
                    "n_vignetted": int((~b["valid"]).sum()), "n_rays": int(b["valid"].sum())})
    return {"fields": out, "image_mm": _layout(sysd)["image_mm"], "stop": sysd["stop"]}


def noncoaxial_spot(system, field=None, rings=6, pupil_fill=1.0):
    """RMS / geometric spot radius (mm) and centroid on the (possibly tilted) image plane (``table``).

    Same statistics as ``raytrace.spot_stats`` (RMS about the centroid of the valid rays), with the
    image coordinates in the image plane's local frame (with ``image_tilt``, measured on the tilted plane itself,
    so the radius is not shrunk by cos θ' along the tilt). *field* is ``(fx, fy)`` or a number (= fy).
    """
    op = "noncoaxial_spot"
    sysd = _check(system, op)
    f = _fields(sysd, None if field is None else [field], op)[0]
    pf = _num(pupil_fill, "pupil_fill", op, positive=True)
    b = _bundle(sysd, f, rings=int(_num(rings, "rings", op, positive=True)), pupil_fill=pf)
    xy = b["image_xy"][b["valid"]]
    if len(xy) == 0:
        raise ValueError("%s: no ray reached the image plane" % op)
    cen = xy.mean(0)
    d = xy - cen
    r = np.hypot(d[:, 0], d[:, 1])
    return {"rms_radius": float(np.sqrt(np.mean(r * r))), "geo_radius": float(r.max()),
            "centroid_x": float(cen[0]), "centroid_y": float(cen[1]),
            "chief_x": float(b["chief_xy"][0]), "chief_y": float(b["chief_xy"][1]),
            "n_rays": int(len(xy)), "n_vignetted": int((~b["valid"]).sum()), "image_mm": b["image_mm"],
            "field": list(f)}


def _chief(sysd, f, layout=None, path=None):
    if sysd["source"] is not None and f[0] == 0.0 and sysd["object_tilt"] == (0.0, 0.0):
        src = sysd["source"]
        para = RT._para_at(src)
        dpx, dpy = RT._chief_offset(src, f[1], para)
        P, D, _ = RT._launch(src, np.array([dpx]), np.array([dpy]), f[1], para)
    else:
        P, D, _, ok = _aim(sysd, np.zeros((1, 2)), f, layout=layout)
        if not ok[0]:
            return None
    tr = _trace(sysd, P, D, path=path, layout=layout)
    if not tr["valid"][0]:
        return None
    return tr


def image_orientation(system, delta=None):
    """Image orientation through folds (``table``): reflections, handedness, rotation.

    Traces the chief ray at the field origin and at small +x / +y field steps and returns the 2×2 Jacobian
    ``J`` of the image position (image-plane local x, y; a right-handed basis with the light travelling
    along +z) with respect to the object field (``fx``, ``fy``). ``det > 0`` is a right-handed image
    (upright or rotated), ``det < 0`` a reversed (mirror) image; ``n_reflections`` counts the reflections on
    the path — the closed form is ``sign(det) = (−1)^n_reflections`` (real, inverting imaging is a
    rotation by 180°). For an object at infinity the field is the ray direction, so the object point lies
    opposite to it and ``J`` is taken with that sign. ``rotation_deg`` is the rotation of the image of the
    object's +y axis (180 for an ordinary inverted image); ``reversed`` is ``det < 0``.
    """
    op = "image_orientation"
    sysd = _check(system, op)
    if delta is None:
        delta = 0.01 if sysd["object_mm"] == INF else 0.01
    h = _num(delta, "delta", op, positive=True)
    lay = _layout(sysd)
    f0 = tuple(sysd["field"])
    res = []
    for f in (f0, (f0[0] + h, f0[1]), (f0[0], f0[1] + h)):
        tr = _chief(sysd, f, layout=lay)
        if tr is None:
            raise ValueError("%s: the chief ray at field %s does not reach the image" % (op, f))
        res.append(tr["image_local"][0, :2])
    J = np.stack([(res[1] - res[0]) / h, (res[2] - res[0]) / h], 1)
    if sysd["object_mm"] == INF:
        J = -J                       # 無限遠の物点は光線の向きの反対側にある(+y へ進む光線は −y の物点から)
    det = float(np.linalg.det(J))
    nrefl = sum(1 for r in sysd["records"] if r["kind"] == "surface" and r["reflect"])
    rot = math.degrees(math.atan2(-J[0, 1], J[1, 1]))
    return {"jacobian": J.tolist(), "det": det, "reversed": bool(det < 0), "n_reflections": nrefl,
            "parity_closed_form": (-1) ** nrefl, "rotation_deg": rot,
            "image_xy": res[0].tolist(), "field": list(f0)}


def _with_branch(sysd, branch, op):
    """同じ処方を、全ての半透鏡の枝を *branch* にして組み直す(枝で座標の展開が変わるので要素から作り直す)。"""
    if branch not in ("transmit", "reflect"):
        raise ValueError("%s: branch must be 'transmit' or 'reflect', got %r" % (op, branch))
    els = sysd.get("elements")
    has = els is not None and any(isinstance(e, dict) and e.get("beamsplitter") is not None for e in els)
    if not has:
        raise ValueError("%s: the system has no beamsplitter" % op)
    new = []
    for e in els:
        if isinstance(e, dict) and e.get("beamsplitter") is not None:
            e = dict(e)
            if e.get("type", "surface") == "plate":
                e["branch"] = branch
            else:
                bs = e["beamsplitter"]
                e["beamsplitter"] = dict(bs, branch=branch) if isinstance(bs, dict) else {"R": bs, "branch": branch}
        new.append(e)
    return noncoaxial_system(new, stop=sysd["stop_arg"], object_mm=sysd["object_mm"], wavelength_um=sysd["wavelength_um"],
                    index_object=sysd["index_object_arg"], field=sysd["field"], image_mm=sysd["image_mm_arg"],
                    image_tilt=sysd["image_tilt"], object_tilt=sysd["object_tilt"])


def beamsplitter_branches(system=None, thickness_mm=3.0, glass="BK7", tilt_deg=45.0, reflectance=0.5,
                          focal_mm=100.0, f_number=10.0, gap_mm=40.0):
    """The two branches of a plate beamsplitter in a converging beam (``table``).

    Builds (or takes) a system ``thin lens → gap → plate beamsplitter`` and traces the **transmit** branch
    (through the plate: laterally displaced by the closed form ``t·sinθ(1 − cosθ/√(n² − sin²θ))`` and
    astigmatic) and the **reflect** branch (off the front face: a fold — the image is the mirror image of the
    unfolded focus). Per branch: image point (global), axis direction, energy fraction (R / T of the coating),
    RMS spot. Default: f = 100 mm, f/10, 3 mm BK7 at 45°, R = 0.5.
    """
    op = "beamsplitter_branches"
    th = _num(thickness_mm, "thickness_mm", op, positive=True)
    tl = _num(tilt_deg, "tilt_deg", op)
    R = _num(reflectance, "reflectance", op)
    if not 0.0 < R < 1.0:
        raise ValueError("%s: reflectance must lie in (0, 1)" % op)
    f = _num(focal_mm, "focal_mm", op, positive=True)
    N = _num(f_number, "f_number", op, positive=True)
    gap = _num(gap_mm, "gap_mm", op, positive=True)
    out = {}
    for br in ("transmit", "reflect"):
        if system is None:
            lens = _paraxial_lens_elements(f, f / (2.0 * N), gap)
            sysd = noncoaxial_system(lens + [{"type": "plate", "thickness": th, "n": glass, "tilt": (tl, 0.0), "ap": 4.0 * f / N,
                                     "beamsplitter": R, "branch": br, "t": None}], stop=0)
        else:
            sysd = _with_branch(_check(system, op), br, op)
        lay = _layout(sysd)
        tr = _chief(sysd, (0.0, 0.0), layout=lay)
        st = noncoaxial_spot(sysd, rings=4, pupil_fill=0.5)
        Fi, oi = lay["image"]
        bsr = [r["beamsplitter"]["R"] for r in sysd["records"] if r["kind"] == "surface" and r["beamsplitter"]]
        energy = float(np.prod([x if br == "reflect" else 1.0 - x for x in bsr])) if bsr else 1.0
        out[br] = {"image_point": tr["points"][0, -1].tolist(), "axis_direction": Fi[:, 2].tolist(),
                   "chief_direction": tr["dirs"][0, -1].tolist(), "energy_fraction": energy,
                   "rms_spot": st["rms_radius"], "image_mm": lay["image_mm"]}
    return out


def _paraxial_lens_elements(f, ap, gap):
    """焦点距離 *f* の平凸 BK7 の単レンズ(平面を像側、絞り = 第 1 面)と、その後ろの間隔 *gap*。"""
    n = RT.refractive_index("BK7")
    if not 0.0 < gap < f - 2.0 / n:
        raise ValueError("beamsplitter_branches: gap_mm must lie between 0 and the back focal length %.4g" % (f - 2.0 / n))
    return [{"R": (n - 1.0) * f, "t": 2.0, "n": "BK7", "ap": ap, "label": "L"},
            {"R": INF, "t": gap, "n": 1.0}]


# --------------------------------------------------------------------------- #
# op: 閉形式
# --------------------------------------------------------------------------- #
def tilted_plate_shift(thickness_mm=5.0, glass="BK7", tilt_deg=30.0, wavelength_um=WL_D):
    """Plane-parallel plate tilted by θ: lateral shift, focus shifts and astigmatism (``table``, closed form).

    With ``n`` the plate index, ``cos θ' = √(n² − sin²θ)/n`` and the path in glass ``L = t/cos θ'``:

    * lateral displacement of a ray: ``Δ = t·sinθ·(1 − cosθ/√(n² − sin²θ))`` (Smith, plane-parallel plates);
    * axial image shift at normal incidence ``t(n − 1)/n``;
    * along a beam at θ (Coddington's equations for a flat surface): the sagittal image moves by
      ``L(cos(θ − θ') − 1/n)`` and the tangential by ``L(cos(θ − θ') − cos²θ/(n cos²θ'))``;
    * astigmatism (tangential − sagittal) ``(t/√(n² − sin²θ))·(1 − n²cos²θ/(n² − sin²θ))`` — never negative: the
      tangential image lies farther (the often-quoted form with the bracket reversed is s − t).
    """
    op = "tilted_plate_shift"
    t = _num(thickness_mm, "thickness_mm", op, positive=True)
    th = _num(tilt_deg, "tilt_deg", op)
    if not abs(th) < 90.0:
        raise ValueError("%s: tilt_deg must lie in (-90, 90)" % op)
    wl = _num(wavelength_um, "wavelength_um", op, positive=True)
    n = RT.refractive_index(glass, wl)
    a = math.radians(abs(th))
    s, c = math.sin(a), math.cos(a)
    q = math.sqrt(n * n - s * s)
    cp = q / n
    L = t / cp
    thp = math.acos(cp)
    lat = t * s * (1.0 - c / q)
    sag = L * (math.cos(a - thp) - 1.0 / n)
    tan = L * (math.cos(a - thp) - c * c / (n * cp * cp))
    ast = (t / q) * (1.0 - n * n * c * c / (q * q))
    return {"n": n, "thickness_mm": t, "tilt_deg": th, "lateral_shift_mm": math.copysign(lat, th) if th else 0.0,
            "axial_shift_normal_mm": t * (n - 1.0) / n, "sagittal_shift_mm": sag, "tangential_shift_mm": tan,
            "astigmatism_mm": abs(ast), "astigmatism_signed_mm": tan - sag, "refraction_angle_deg": math.degrees(thp),
            "glass_path_mm": L}


def scheimpflug_tilt(system=None, object_distance_mm=200.0, object_tilt_deg=30.0, verify=True, heights_mm=None):
    """Scheimpflug condition for a tilted object plane (``table``; closed form, optionally real rays).

    For a lens with focal length ``f`` and principal planes H, H' (from ``raytrace.paraxial_trace``), an object
    plane through the axis point at distance ``s`` before H, tilted by θ (the plane ``z = z₀ + y·tanθ``):
    the image lies at ``s' = s f/(s − f)`` after H' with magnification ``m = −s'/s`` and the image plane is
    tilted by ``tanθ' = m·tanθ`` (the plane ``z = z₀' + y'·tanθ'``). The **hinge**: the object plane meets H
    and the image plane meets H' at the same height ``y_h = s/tanθ`` (H to H' is unit magnification).

    With *verify*, real rays (small pencils aimed at the stop, the paraxial-limit focus of each object point)
    are traced from object heights *heights_mm* (default ±2 mm, 0) and a line is fitted to the image focus
    points: ``image_tilt_traced_deg`` is the real-ray answer. Default lens: ``raytrace``'s cemented doublet.
    """
    op = "scheimpflug"
    src = RT.example_system("doublet") if system is None else system
    if not (isinstance(src, dict) and "surfaces" in src):
        raise ValueError("%s: expected a raytrace.lens_system() table" % op)
    d = _num(object_distance_mm, "object_distance_mm", op, positive=True)
    th = _num(object_tilt_deg, "object_tilt_deg", op)
    if not abs(th) < 89.0:
        raise ValueError("%s: object_tilt_deg must lie in (-89, 89)" % op)
    p = RT.paraxial_trace(RT.lens_system([dict(R=s["R"], t=s["t"], n=s["n"], k=s["k"], ap=s["ap"], asph=s["asph"])
                                          for s in src["surfaces"]], stop=src["stop"],
                                         wavelength_um=src["wavelength_um"]))
    f = p["efl"]
    if not math.isfinite(f) or f <= 0:
        raise ValueError("%s: the lens must have a positive focal length" % op)
    zH = p["pp_front"]                                         # front principal plane, from the first vertex
    zv = sum(s["t"] for s in src["surfaces"][:-1])             # last vertex
    zH2 = zv + p["pp_rear"]                                    # rear principal plane
    s = d + zH
    if s <= f:
        raise ValueError("%s: the object lies inside the front focal length (s = %.4g <= f = %.4g)" % (op, s, f))
    sp = s * f / (s - f)
    m = -sp / s
    tp = math.degrees(math.atan(m * math.tan(math.radians(th))))
    img_dist = zH2 + sp - zv                                   # last vertex → image
    hinge = s / math.tan(math.radians(th)) if th != 0 else INF
    out = {"efl_mm": f, "s_mm": s, "s_prime_mm": sp, "magnification": m, "object_tilt_deg": th,
           "image_tilt_deg": tp, "image_distance_mm": img_dist, "hinge_height_mm": hinge,
           "front_principal_mm": zH, "rear_principal_mm": zH2,
           "object_hinge_point": [0.0, hinge, zH] if math.isfinite(hinge) else None,
           "image_hinge_point": [0.0, hinge, zH2] if math.isfinite(hinge) else None}
    if verify:
        hs = [-2.0, -1.0, 0.0, 1.0, 2.0] if heights_mm is None else [_num(h, "height", op) for h in heights_mm]
        surfs = [dict(R=q["R"], t=q["t"], n=q["n"], k=q["k"], ap=q["ap"], asph=q["asph"]) for q in src["surfaces"][:-1]]
        surfs.append(dict(R=src["surfaces"][-1]["R"], t=img_dist, n=1.0, k=src["surfaces"][-1]["k"],
                          asph=src["surfaces"][-1]["asph"]))
        s3 = noncoaxial_system(surfs, stop=src["stop"], object_mm=d, wavelength_um=src["wavelength_um"],
                      object_tilt=(th, 0.0))
        pts = []
        for h in hs:
            fp = _focus_point(s3, (0.0, h))
            if fp is None:
                continue
            pts.append(fp)
        pts = np.array(pts)
        if len(pts) >= 2:
            A = np.stack([pts[:, 1], np.ones(len(pts))], 1)
            slope = np.linalg.lstsq(A, pts[:, 2], rcond=None)[0][0]
            out["image_tilt_traced_deg"] = math.degrees(math.atan(slope))
            out["focus_points"] = pts.tolist()
            res = pts[:, 2] - A @ np.linalg.lstsq(A, pts[:, 2], rcond=None)[0]
            out["plane_residual_mm"] = float(np.max(np.abs(res)))
    return out


def _closest(p0, d0, p1, d1):
    """2 本の 3-D の直線の最接近点の中点。"""
    w = p0 - p1
    a, b, c = d0 @ d0, d0 @ d1, d1 @ d1
    dd, e = d0 @ w, d1 @ w
    den = a * c - b * b
    if not den > 0:
        return None
    s = (b * e - c * dd) / den
    u = (a * e - b * dd) / den
    return 0.5 * (p0 + s * d0 + p1 + u * d1)


def _focus_point(sysd, f, rel=0.01):
    """視野 *f* の近軸極限の焦点(接線と球欠の平均、大域の点)。``_foci`` を見よ。"""
    r = _foci(sysd, f, rel)
    return None if r is None else 0.5 * (r[0] + r[1])


def _foci(sysd, f, rel=0.01):
    """視野 *f* の点像の近軸極限の焦点(大域の点)。

    絞りの上で対称な 2 本(±h)の光線の最接近点を、接線(y)と球欠(x)で求めて平均する。対称な対なので
    コマ(h の 1 次)は消え、残る h² の項(球面収差)は h と 2h の 2 点で Richardson 外挿して消す。
    主光線と微小光線を交わらせる形は、2 本がほぼ平行で桁落ちする(h = 1e-4·ap で 6e-7 の相対誤差)。
    """
    lay = _layout(sysd)
    ap = sysd["records"][sysd["stop"]]["ap"]
    res = []
    for h in (rel * ap, 2.0 * rel * ap):
        tg = np.array([[0.0, h], [0.0, -h], [h, 0.0], [-h, 0.0]])
        P, D, _, ok = _aim(sysd, tg, f, layout=lay)
        if not np.all(ok):
            return None
        tr = _trace(sysd, P, D, layout=lay)
        if not np.all(np.all(np.isfinite(tr["points"][:, -2, :]), 1)):
            return None
        p = tr["points"][:, -2, :]
        d = tr["dirs"][:, -1, :]
        ft = _closest(p[0], d[0], p[1], d[1])
        fs = _closest(p[2], d[2], p[3], d[3])
        if ft is None or fs is None:
            return None
        res.append((ft, fs))
    return ((4.0 * res[0][0] - res[1][0]) / 3.0, (4.0 * res[0][1] - res[1][1]) / 3.0)


def surface_reflectance(n_before=1.0, n_after="BK7", coating=None, wavelength_um=WL_D, angle_deg=0.0):
    """Residual reflectance of one surface from the material table and its coating (``table``).

    *n_before* / *n_after*: the media (index, ``(nd, vd)``, a glass / material name). *coating*: None or
    ``"bare"`` (Fresnel ``((n₁ − n₂)/(n₁ + n₂))²`` at normal incidence), a material name (a quarter-wave
    single layer of that material at *wavelength_um*, e.g. ``"MGF2"``; closed form
    ``((n₀n_s − n₁²)/(n₀n_s + n₁²))²``), a list ``[(material, thickness_nm), ...]`` from the incident side,
    or ``{"R": r}`` (a given reflectance, e.g. a 50 % beamsplitter coating). Films are evaluated with the
    characteristic-matrix method of ``filmoptics.multilayer_reflectance`` (materials from ``materials``),
    unpolarised, at *angle_deg* in the incident medium. Returns ``R``, ``T = 1 − R`` (lossless) and the
    closed-form value where one exists.
    """
    op = "surface_reflectance"
    wl = _num(wavelength_um, "wavelength_um", op, positive=True)
    ang = _num(angle_deg, "angle_deg", op)
    if not 0.0 <= ang < 90.0:
        raise ValueError("%s: angle_deg must lie in [0, 90)" % op)
    n1 = RT.refractive_index(n_before, wl)
    n2 = RT.refractive_index(n_after, wl)
    spec = _coating(coating, "surface", op)
    R, closed, layers = _reflectance(n1, n2, spec, wl, ang)
    return {"R": R, "T": 1.0 - R, "n_before": n1, "n_after": n2, "wavelength_um": wl, "angle_deg": ang,
            "layers": layers, "closed_form": closed}


def _reflectance(n1, n2, spec, wl, ang=0.0):
    """(R, 閉形式の値 or None, 層の列)。膜は入射側から。内側からの反射も同じ値(吸収の無い積層は相反)。"""
    import filmoptics as FO
    if spec is not None and "R" in spec:
        return float(spec["R"]), float(spec["R"]), []
    layers = []
    closed = None
    if spec is None:
        if ang == 0.0:
            closed = ((n1 - n2) / (n1 + n2)) ** 2
    elif "quarter_wave" in spec:
        dwl = spec.get("design_wavelength_um", wl)
        import materials as _mat
        rec = _mat._record(spec["quarter_wave"], "surface_reflectance")
        nl = float(_mat._nk(rec, dwl, "surface_reflectance")[0][0])
        layers = [(spec["quarter_wave"], 1000.0 * dwl / (4.0 * nl))]
        if ang == 0.0 and dwl == wl:
            closed = ((n1 * n2 - nl * nl) / (n1 * n2 + nl * nl)) ** 2
    else:
        layers = list(spec["layers"])
    R = FO.multilayer_reflectance(layers, n2, wavelengths_nm=[1000.0 * wl], angle_deg=ang, ambient=n1)[0, 1]
    return float(R), closed, [[m, float(d)] for m, d in layers]


# --------------------------------------------------------------------------- #
# ゴースト
# --------------------------------------------------------------------------- #
def _ghost_steps(sysd, i, j):
    """面の記録 i < j の 2 回反射のゴーストの経路。"""
    nom = _nominal_path(sysd)
    idx = [p[0] for p in nom]
    a, b = idx.index(i), idx.index(j)
    steps = [(k, act, +1) for (k, act, _) in nom[:b]]
    steps.append((j, "reflect", +1))
    for (k, act, _) in reversed(nom[a + 1:b]):
        steps.append((k, act, -1))
    steps.append((i, "reflect", -1))
    steps += [(k, act, +1) for (k, act, _) in nom[a + 1:]]
    return steps


def _surface_R(sysd, k, coatings, wl, angle_deg=0.0):
    """面 k の反射率(通常の経路での前後の媒質、膜の指定、入射角 = 前の媒質の中の角)と透過率。"""
    r = sysd["records"][k]
    if r["beamsplitter"] is not None:
        return r["beamsplitter"]["R"], 1.0 - r["beamsplitter"]["R"]
    if r["mirror"]:
        R = r["coating"]["R"] if r["coating"] and "R" in r["coating"] else 1.0
        return R, 0.0
    before, after = _media(sysd)
    spec = coatings.get(k, r["coating"]) if coatings is not None else r["coating"]
    R, _, _ = _reflectance(before[k], after[k], spec, wl, angle_deg)
    return R, 1.0 - R


def _incidence_angles(sysd, f, lay):
    """視野 *f* の主光線の、通常の経路での各面への入射角 [度](前の媒質の中)。主光線が通らなければ 0°。"""
    path = _nominal_path(sysd)
    out = {k: 0.0 for k, _, _ in path}
    tr = _chief(sysd, f, layout=lay)
    if tr is None:
        return out
    for j, (k, _, _) in enumerate(path):
        r = sysd["records"][k]
        Rm, off = lay["poses"][k]
        Q = ((tr["points"][0, j + 1] - off) @ Rm)[None, :]
        c = 0.0 if r["R"] == INF else 1.0 / r["R"]
        nrm = RT._surface_normal(Q, c, r["k"], r["asph"])[0]
        d = tr["dirs"][0, j] @ Rm
        ci = min(1.0, abs(float(nrm @ d)))
        out[k] = math.degrees(math.acos(ci))
    return out


def _coatings_arg(sysd, coatings, op):
    if coatings is None:
        return None
    if isinstance(coatings, (str, list, tuple)) or (isinstance(coatings, dict) and set(coatings) <= {"R", "quarter_wave",
                                                                                                    "design_wavelength_um"}):
        spec = _coating(coatings, "coatings", op)
        return {k: spec for k, r in enumerate(sysd["records"]) if r["kind"] == "surface"}
    if not isinstance(coatings, dict):
        raise ValueError("%s: coatings must be a coating spec or {record index: coating}" % op)
    out = {}
    for k, v in coatings.items():
        if isinstance(k, str) and k.isdigit():
            k = int(k)
        if not isinstance(k, (int, np.integer)) or not 0 <= int(k) < len(sysd["records"]) or \
                sysd["records"][int(k)]["kind"] != "surface":
            raise ValueError("%s: coatings key %r is not a surface record index" % (op, k))
        out[int(k)] = _coating(v, "record %d" % int(k), op)
    return out


def _path_energy(sysd, steps, Rk):
    e = 1.0
    for (k, act, _) in steps:
        R, T = Rk[k]
        r = sysd["records"][k]
        if act == "reflect":
            e *= R
        elif r["beamsplitter"] is not None or not r["mirror"]:
            e *= T
    return e


def _best_focus(xy, dxy):
    """光線の像面での位置 xy と、像面の法線方向の単位あたりの横の進み dxy から、RMS が最小になる z と半径。"""
    m = np.all(np.isfinite(xy), 1) & np.all(np.isfinite(dxy), 1)
    xy, dxy = xy[m], dxy[m]
    if len(xy) < 2:
        return float("nan"), float("nan")
    a = xy - xy.mean(0)
    b = dxy - dxy.mean(0)
    den = float(np.sum(b * b))
    z = -float(np.sum(a * b)) / den if den > 0 else 0.0
    r = a + z * b
    return z, float(np.sqrt(np.mean(np.sum(r * r, 1))))


def ghost_analysis(system, coatings=None, field=None, rings=6, pupil_fill=0.98, pixel_mm=0.005, max_rows=None):
    """Two-reflection ghosts of every surface pair (``table``): focus, size on the sensor and relative intensity.

    For surface records ``i < j`` (refracting surfaces and beamsplitters; nominal mirrors only as the parts of
    the path they already are), the light runs to *j*, reflects, crosses *j−1 … i+1* backwards, reflects at *i*
    and runs on to the image plane — ``N(N−1)/2`` paths. The nominal bundle (same launch as the image) is
    traced along each path with real rays. Per ghost:

    * ``energy_ratio`` — ghost energy / image energy = ``R_i·R_j·Π T`` over the ghost path ÷ ``Π T`` over the
      image path; ``R`` from ``surface_reflectance`` (the media of the prescription and *coatings*:
      a coating for all surfaces, or ``{record: coating}``; records may carry their own ``coating``), at the
      angle of incidence of the field's chief ray on each surface (unpolarised; a 45° beamsplitter plate is not
      treated as normal incidence);
    * ``focus_offset_mm`` — the ghost's best focus relative to the image plane (along the image normal;
      negative = in front of the sensor), ``radius_mm`` (RMS) / ``max_radius_mm`` on the image plane,
      ``centroid_xy`` (image-plane local) and ``offset_xy`` (from the image's chief ray — where the false
      copy lands relative to the true image);
    * ``point_ratio`` — ghost irradiance / image irradiance for a point source whose image fills one
      ``pixel_mm`` disk: ``energy_ratio · (pixel / max(pixel, radius))²``;
    * ``extended_ratio`` — the same for a uniform extended scene: ``energy_ratio · |det J_image| / |det J_ghost|``
      (the ghost spreads the scene over its own magnification); ``jacobian`` is ``J_ghost`` (image-plane position
      of the ghost's chief ray per unit field, 2×2; ``image_jacobian`` the image's own).

    Rows are sorted by ``point_ratio`` (ties by the declared order). ``n_pairs`` = N(N−1)/2.
    """
    op = "ghost_analysis"
    sysd = _check(system, op)
    f = _fields(sysd, None if field is None else [field], op)[0]
    co = _coatings_arg(sysd, coatings, op)
    pix = _num(pixel_mm, "pixel_mm", op, positive=True)
    pf = _num(pupil_fill, "pupil_fill", op, positive=True)
    wl = sysd["wavelength_um"]
    surf = [k for k, r in enumerate(sysd["records"]) if r["kind"] == "surface"]
    cand = [k for k in surf if not sysd["records"][k]["mirror"]]
    lay = _layout(sysd)
    angles = _incidence_angles(sysd, f, lay)
    Rk = {k: _surface_R(sysd, k, co, wl, angles[k]) for k in surf}
    nom = _nominal_path(sysd)
    e_img = _path_energy(sysd, nom, Rk)
    base = _bundle(sysd, f, rings=int(rings), pupil_fill=pf)
    P0, D0 = base["points"][:, 0, :], base["dirs"][:, 0, :]
    ok0 = base["valid"].copy()
    Fi = lay["image_plane"]                     # 傾いた像面の基底(xy と同じ座標系で法線方向の進みを測る)
    Jn = _jacobian(sysd, f, nom, lay)
    rows = []
    for a in range(len(cand)):
        for b in range(a + 1, len(cand)):
            i, j = cand[a], cand[b]
            steps = _ghost_steps(sysd, i, j)
            tr = _trace(sysd, P0[ok0], D0[ok0], path=steps, layout=lay)
            v = tr["valid"]
            xy = tr["image_local"][:, :2]
            dl = tr["dirs"][:, -1, :] @ Fi
            with np.errstate(divide="ignore", invalid="ignore"):
                dxy = dl[:, :2] / dl[:, 2:3]
            e = _path_energy(sysd, steps, Rk) / e_img if e_img > 0 else float("nan")
            frac = float(v.mean()) if len(v) else 0.0
            if v.sum() >= 2:
                z, rbest = _best_focus(xy[v], dxy[v])
                cen = xy[v].mean(0)
                d = xy[v] - cen
                rr = np.hypot(d[:, 0], d[:, 1])
                rad, rmax = float(np.sqrt(np.mean(rr * rr))), float(rr.max())
            else:
                z = rbest = rad = rmax = float("nan")
                cen = np.array([float("nan"), float("nan")])
            e_eff = e * frac
            pr = e_eff * (pix / max(pix, rad)) ** 2 if math.isfinite(rad) else 0.0
            Jg = _jacobian(sysd, f, steps, lay)
            ext = e * abs(np.linalg.det(Jn)) / abs(np.linalg.det(Jg)) if Jg is not None and Jn is not None and \
                abs(np.linalg.det(Jg)) > 0 else float("nan")
            rows.append({"i": i, "j": j, "label": "%s/%s" % (sysd["records"][i]["label"] or "S%d" % i,
                                                              sysd["records"][j]["label"] or "S%d" % j),
                         "R_i": Rk[i][0], "R_j": Rk[j][0], "energy_ratio": e, "reach_fraction": frac,
                         "focus_offset_mm": z, "best_focus_radius_mm": rbest, "radius_mm": rad,
                         "max_radius_mm": rmax, "centroid_xy": cen.tolist(),
                         "offset_xy": (cen - base["chief_xy"]).tolist(), "point_ratio": pr,
                         "extended_ratio": ext, "jacobian": None if Jg is None else Jg.tolist()})
    order = sorted(range(len(rows)), key=lambda q: (-round(rows[q]["point_ratio"], 15), q))
    rows = [rows[q] for q in order]
    if max_rows is not None:
        rows = rows[:int(max_rows)]
    n = len(cand)
    return {"ghosts": rows, "n_pairs": n * (n - 1) // 2, "n_surfaces": n, "field": list(f), "pixel_mm": pix,
            "surface_reflectance": {str(k): Rk[k][0] for k in surf}, "image_energy": e_img,
            "incidence_deg": {str(k): angles[k] for k in surf},
            "image_jacobian": None if Jn is None else Jn.tolist(), "image_chief_xy": base["chief_xy"].tolist()}


def _jacobian(sysd, f, path, lay, h=None):
    """経路 *path* に沿った主光線の像面の位置の、視野についてのヤコビアン(2×2)。"""
    if h is None:
        h = 0.01
    pts = []
    for ff in (f, (f[0] + h, f[1]), (f[0], f[1] + h)):
        if sysd["source"] is not None and ff[0] == 0.0 and sysd["object_tilt"] == (0.0, 0.0):
            src = sysd["source"]
            para = RT._para_at(src)
            dpx, dpy = RT._chief_offset(src, ff[1], para)
            P, D, _ = RT._launch(src, np.array([dpx]), np.array([dpy]), ff[1], para)
        else:
            P, D, _, ok = _aim(sysd, np.zeros((1, 2)), ff, layout=lay)
            if not ok[0]:
                return None
        tr = _trace(sysd, P, D, path=path, layout=lay)
        if not tr["valid"][0]:
            return None
        pts.append(tr["image_local"][0, :2])
    return np.stack([(pts[1] - pts[0]) / h, (pts[2] - pts[0]) / h], 1)


def ghost_path(system, i=None, j=None, field=None, rings=3, pupil_fill=0.98):
    """Real-ray polylines of one two-reflection ghost (``table``): the path i < j, its rays and energy.

    Default pair: the strongest ghost of ``ghost_analysis``. Returns ``steps`` (record, action, direction),
    ``points`` (N, len(steps)+2, 3) global polylines, ``image_xy`` on the image plane and ``valid``.
    """
    op = "ghost_path"
    sysd = _check(system, op)
    f = _fields(sysd, None if field is None else [field], op)[0]
    if i is None or j is None:
        ga = ghost_analysis(sysd, field=f, rings=3)
        if not ga["ghosts"]:
            raise ValueError("%s: the system has fewer than two transmitting surfaces" % op)
        i, j = ga["ghosts"][0]["i"], ga["ghosts"][0]["j"]
    surf = [k for k, r in enumerate(sysd["records"]) if r["kind"] == "surface" and not r["mirror"]]
    for nm, v in (("i", i), ("j", j)):
        if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)) or int(v) not in surf:
            raise ValueError("%s: %s must be a transmitting surface record (%s), got %r" % (op, nm, surf, v))
    i, j = int(i), int(j)
    if not i < j:
        raise ValueError("%s: need i < j" % op)
    base = _bundle(sysd, f, rings=int(rings), pupil_fill=_num(pupil_fill, "pupil_fill", op, positive=True))
    ok = base["valid"]
    steps = _ghost_steps(sysd, i, j)
    tr = _trace(sysd, base["points"][ok, 0, :], base["dirs"][ok, 0, :], path=steps)
    return {"i": i, "j": j, "steps": [list(s) for s in steps], "points": tr["points"], "valid": tr["valid"],
            "image_xy": tr["image_local"][:, :2], "field": list(f)}


def ghost_image(system, coatings=None, field=None, size=128, extent_mm=None, rings=12, pixel_mm=None,
                log=True):
    """Image-plane irradiance of the image plus all two-reflection ghosts of a point source (``image2d``).

    Every ray of the nominal bundle and of each ghost path is binned into a ``size × size`` grid spanning
    ``±extent_mm`` (default: 1.2 × the largest ghost radius) around the chief ray, weighted by the path's
    energy ratio (``ghost_analysis``). The grid is normalised so the brightest **ghost** pixel is compared
    on the same scale as the image: values are relative to the image's peak pixel; with *log* the result is
    ``log10`` of that ratio (floored at −12).
    """
    op = "ghost_image"
    sysd = _check(system, op)
    f = _fields(sysd, None if field is None else [field], op)[0]
    n = int(_num(size, "size", op, positive=True))
    if not 8 <= n <= 1024:
        raise ValueError("%s: size must lie in [8, 1024]" % op)
    ga = ghost_analysis(sysd, coatings=coatings, field=f, rings=3)
    lay = _layout(sysd)
    base = _bundle(sysd, f, rings=int(rings), pupil_fill=0.98)
    ok = base["valid"]
    c = base["chief_xy"]
    if extent_mm is None:
        rm = [g["max_radius_mm"] + float(np.hypot(*(np.array(g["centroid_xy"]) - c)))
              for g in ga["ghosts"] if math.isfinite(g["max_radius_mm"])]
        ext = 1.2 * max(rm) if rm else 1.0
    else:
        ext = _num(extent_mm, "extent_mm", op, positive=True)
    img = np.zeros((n, n))

    def add(xy, w):
        m = np.all(np.isfinite(xy), 1)
        u = (xy[m] - c + ext) / (2.0 * ext) * n
        ij = np.floor(u).astype(int)
        keep = (ij[:, 0] >= 0) & (ij[:, 0] < n) & (ij[:, 1] >= 0) & (ij[:, 1] < n)
        np.add.at(img, (n - 1 - ij[keep, 1], ij[keep, 0]), w)

    nray = max(int(ok.sum()), 1)
    add(base["image_xy"][ok], 1.0 / nray)
    peak = img.max()
    for g in ga["ghosts"]:
        tr = _trace(sysd, base["points"][ok, 0, :], base["dirs"][ok, 0, :], path=_ghost_steps(sysd, g["i"], g["j"]),
                    layout=lay)
        add(tr["image_local"][tr["valid"], :2], g["energy_ratio"] / nray)
    out = img / peak if peak > 0 else img
    if log:
        out = np.log10(np.maximum(out, 1e-12))
    return out
