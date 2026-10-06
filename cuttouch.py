# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""cuttouch — 包丁を 2 本指の視触覚パッドで持ち、手首の力センサなしに食材の靱性 R と刃の当たり位置を読む(規則だけ、学習なし、2026-10-06)。

:mod:`cutting`(食材の切断を画像で測る)と :mod:`pegtactile`(2 本指の指先の弾性膜で接触レンチを読む)の連鎖。包丁の柄(刃の背)を
2 枚のパッドで挟み、膜の像だけから刃が食材から受ける力 —— 押し V・引き H・指の法線まわりのモーメント M_x —— を復元し、

    刃の当たり位置  Ly = (M_x + Lz·H) / V            (Lz = 把持点から刃先までの高さ、刃が傾いていれば Lz = Lz₀ − Ly·s で
                                                      Ly = (M_x + Lz₀·H) / (V + s·H)、s = 刃先の傾きの正接)
    slice/push 比   ξ̂ = H / V                         (Atkins の摩擦なしの式では H/V = ξ、:func:`cutting.cut_force_atkins`)
    靱性            R = V / (w_eff · g(ξ̂))             (:func:`cutting.cut_force_fit`、w_eff は画像から)

を読む。座標はグリッパ系(:mod:`pegtactile` と同じ: x = パッドの法線、z = 上、y = 柄 / 刃の向き)。食材が刃に加える力は
(0, −H, V)、作用点は把持点から (0, Ly, −Lz)、``M_x = Ly·V − Lz·H``。

ねじりの読みの偏り(このモジュールで見つけて直したこと、門に固定):
  :func:`pegtactile.pad_tactile_read` はパッドのねじりを **無滑り**(Reissner–Sagoci)の関係 M = 16Ga³ω/3 で読む(固着核 r < 0.6a の
  剛体回転 ω)。ところが Hertz 接触のねじりのトラクション q_θ ∝ r/√(a²−r²) は縁で発散するので **どんな小さな M でも縁から滑る**
  (Johnson の定性的注意、:mod:`tactorque`)。部分滑りでは同じ M でもねじれ角 β が無滑りより大きく、無滑りの関係で読むと M を
  **過大に** 読む: 全滑りまでの比 M/M_full = 0.5 で +33 %、0.8 で +85 %(下の数値解、PoC の門 4 で既存の読み手の出力と 0.9 % 以内)。:mod:`pegtactile` の PoC は合成も読みも
  無滑りの模型なので、この偏りは原理的に見えなかった(合成と読みが同じ模型になる弱点)。
  部分滑りのねじり(Lubkin 1951)の閉形式は一次資料で確かめられていない(:mod:`tactorque` も未実装)ので、ここでは **自分で数値的に
  解く**: 接触円を幅の等しい環に分け、Cerruti 核(:func:`tacslip.cerruti_kernel`)の FFT 畳み込みで「環ごとの単位の周方向トラクション →
  周方向変位」の影響行列を作り、滑り環(c < r < a)は q = μp(r)、固着円(r < c)は変位 = 剛体回転 βr として解く。β は固着円の中で
  q ≤ μp がちょうど等号になる値。Hertz の圧力 p = p₀√(1 − r²/a²) で無次元化すると解は 1 本の曲線(M/(μp₀a³)、βG/(μp₀)、c/a)に
  なるので一度だけ解いて使い回す。外の真値は両端: **c → a で Reissner–Sagoci の β = 3M/(16Ga³)**、**c → 0 で全滑りのトルク
  (3π/16)μPa**(どちらも閉形式、門で 0.2 % 以内)。ねじりは ν に依らない(周方向の軸対称の荷重は法線と連成しない)。

正直に:
  * **力の真値の出どころ**: MuJoCo(:func:`cutting.cutting_mujoco_wrist`)は押し V の時系列(手首の柔らかさ・減衰・刃の位置)を出すが、
    その V は関節の摩擦損失に毎歩書いた ``R·w_eff·g(ξ)`` そのもの(滑っている間)で、**切断の力の法則は外から来ていない**(:mod:`cutting`
    と同じ制約)。MuJoCo の場面は縦の 1 自由度なので **引き H も無い** —— H は Atkins の H = ξV で作る。刃の当たり位置の真値は
    場面の幾何(刃先が食材の上面より下にある区間の中点)。
  * パッドの膜の合成は閉形式(Hertz + Cattaneo–Mindlin + 上の部分滑りのねじり)で、せん断とねじりは **重ね合わせ**(Coulomb の
    |q_せん断 + q_ねじり| ≤ μp の連成は解いていない)。全滑りの余裕は「せん断の比 + ねじりの比 < 1」で出す —— 円形接触の滑りの極限曲面は
    凸なのでこれは **十分条件**(保守的)。
  * 部分滑りの補正は「固着円が読みの核 r < 0.6a を含む」間だけ正しい(``readable``)。それを超えると ω は滑り環を含んで意味を失う —— 値は
    返すが ``readable = False`` の印を付ける(黙って数を出さない)。
  * 把持点の位置と刃先までの高さ Lz₀ は既知とする。包丁の重さは空中の 1 コマを ``tare`` に渡して差し引く(姿勢が変わらない間だけ正しい)。

台帳 opsdrive ``cuttouch``(numpy + scipy、3 op): :func:`torsion_partial_slip` / :func:`knife_load_from_pads` / :func:`toughness_from_pads`。
単位: 長さ m(``w_eff_mm`` だけ mm、:mod:`cutting` に合わせる)、力 N、モーメント N·m、靱性 J/m²。失敗は ValueError(fail-closed)。

呼び出し例(既存の pegtactile・cutting の op と繋ぐ。tests/test_cuttouch.py が実行する)::

    import numpy as np
    import cutting, cuttouch, pegtactile
    pad = pegtactile.pad_params()                                  # 把持力 4 N のドーム状パッド
    F = np.array([0.0, -0.14, 2.0])                                # 食材 → 刃: 引き H = 0.14 N、押し V = 2 N
    M = np.cross([0.0, 3e-3, -18e-3], F)                           # 把持点から (0, Ly = 3 mm, −Lz = −18 mm)
    L = pegtactile.peg_wrench_to_pad_loads(-F, -M, pad)            # 2 枚のパッドの荷重(像の代わりに閉形式の読み)
    rd = {k: {"P": L[k]["P"], "q": L[k]["q"], "torsion": L[k]["torsion"]} for k in ("R", "L")}
    k = cuttouch.knife_load_from_pads(rd["R"], rd["L"], pad, 18e-3, torsion_model="no_slip")
    tp = cuttouch.torsion_partial_slip(L["R"]["torsion"], L["R"]["P"], pad)      # 固着円の大きさ・読みの倍率
    w = np.array([10.0, 20.0, 34.0])
    tf = cuttouch.toughness_from_pads([k, k, k], w)                # 同じ力で幅だけ違う 3 コマ(例のため)→ R
    print(round(k["Ly"] * 1e3, 3), round(k["xi"], 3), round(tp["c_over_a"], 3), k["Ly_range_readable"], round(tf["R"], 1))
"""
from __future__ import annotations

import math

import numpy as np

import cutting as C
import pegtactile as PT
import tacsim as T
import tacslip as S
import tactorque as TQ

__all__ = ["torsion_partial_slip", "knife_load_from_pads", "toughness_from_pads"]

#: 読みの核(:func:`pegtactile.pad_tactile_read` の剛体回転の当てはめ窓 r < 0.6a)。固着円がこれを含む間だけ ω = β。
READ_CORE_C_OVER_A = 0.6
_FULL_SLIP_COEF = 3.0 * math.pi / 16.0
_TABLE: dict = {}


# ----------------------------------------------------------------------------------------------------------------------
# 部分滑りのねじりの無次元の数値解(一度だけ)
def _torsion_table(na: int = 64) -> dict:
    """Hertz 接触の部分滑りのねじり(a = 1、G = 1、μp₀ = 1 の無次元)を環 ``na`` 本で解いた表。

    返り: ``c``(固着半径 c/a、降順)、``beta``(βG/(μp₀))、``M``(M/(μp₀a³))、``ratio``(M / 数値の全滑りトルク)、``q``(各行の周方向
    トラクションの環ごとの値 (K, na))、``rc``(環の中心の半径)、``M_full``(数値の全滑りトルク、閉形式 π²/8)。"""
    if na in _TABLE:
        return _TABLE[na]
    n = int(2.5 * na)
    h = 1.0 / na
    kern = S.cerruti_kernel(n, h, 1.0, 0.3)
    c0 = (n - 1) / 2.0
    I, J = np.meshgrid(np.arange(n), np.arange(n))
    X, Y = (I - c0) * h, (J - c0) * h
    off = (np.arange(4) + 0.5) / 4 - 0.5
    rsub = np.stack([np.hypot(X + ox * h, Y + oy * h) for oy in off for ox in off])
    edges = np.linspace(0.0, 1.0, na + 1)
    rc = 0.5 * (edges[:-1] + edges[1:])
    R = np.hypot(X, Y)
    th = np.arctan2(Y, X)
    sn, cs = np.sin(th), np.cos(th)
    cov = np.stack([((rsub >= edges[k]) & (rsub < edges[k + 1])).mean(0) for k in range(na)])
    covsum = cov.sum((1, 2))
    A = np.zeros((na, na))
    mk = np.zeros(na)
    for k in range(na):
        u = TQ._tangential_displacement(-sn * cov[k], cs * cov[k], kern)
        uth = -u["ux"] * sn + u["uy"] * cs
        A[:, k] = (cov * uth).sum((1, 2)) / covsum
        mk[k] = (cov[k] * R).sum() * h * h
    mup = np.sqrt(np.clip(1.0 - rc ** 2, 0.0, None))
    M_full = float(mk @ mup)
    cs_, bs, Ms, qs = [], [], [], []
    for kc in range(na, 1, -1):
        s_, l_ = np.arange(kc), np.arange(kc, na)
        As = A[np.ix_(s_, s_)]
        a_vec = np.linalg.solve(As, rc[s_])
        b_vec = -np.linalg.solve(As, A[np.ix_(s_, l_)] @ mup[l_]) if l_.size else np.zeros(kc)
        ra, rb = a_vec / mup[s_], b_vec / mup[s_]
        pos = ra > 0
        beta = float(np.min((1.0 - rb[pos]) / ra[pos]))
        q = np.concatenate([beta * a_vec + b_vec, mup[l_]])
        cs_.append(edges[kc])
        bs.append(beta)
        Ms.append(float(mk @ q))
        qs.append(q)
    tab = {"c": np.array(cs_), "beta": np.array(bs), "M": np.array(Ms), "ratio": np.array(Ms) / M_full, "q": np.array(qs),
           "rc": rc, "M_full": M_full, "na": na}
    if np.any(np.diff(tab["ratio"]) <= 0) or np.any(np.diff(tab["beta"]) <= 0):
        raise RuntimeError("torsion table is not monotone (na=%d)" % na)
    _TABLE[na] = tab
    return tab


def _interp_ratio(tab, ratio):
    """全滑りまでの比 → (c/a、β/β_RS、行の補間の重み)。比が表の最小より小さければ無滑りの極限(c/a → 1、β/β_RS → 1)へ線形に。"""
    r = tab["ratio"]
    bias_tab = tab["beta"] / (3.0 * tab["M"] / 16.0)
    if ratio <= r[0]:
        f = ratio / r[0]
        return 1.0 + f * (tab["c"][0] - 1.0), 1.0 + f * (bias_tab[0] - 1.0), (0, 0, 1.0)
    i = int(np.searchsorted(r, ratio)) - 1
    i = min(max(i, 0), r.size - 2)
    w = (ratio - r[i]) / (r[i + 1] - r[i])
    return (1 - w) * tab["c"][i] + w * tab["c"][i + 1], (1 - w) * bias_tab[i] + w * bias_tab[i + 1], (i, i + 1, 1.0 - w)


def _pad_hertz(P, pad, op):
    if not (isinstance(P, (int, float, np.integer, np.floating)) and not isinstance(P, bool) and math.isfinite(float(P)) and float(P) > 0):
        raise ValueError("%s: P must be a finite normal force > 0 (pad in contact), got %r" % (op, P))
    hz = T.hertz_sphere(float(P), pad["R"], pad["Es"])
    return hz, _FULL_SLIP_COEF * pad["mu"] * float(P) * hz["a"]


def _contact_hertz(P, pad, contact, op):
    """(pad か contact のどちらか一方)→ (a, p₀, G, μ, 全滑りのトルク)。``contact`` = 接触半径が分かっている Hertz 接触
    ``{"a", "mu", "G"}``(:func:`tactorque.torque_decompose` が使う)。p₀ = 3P/(2πa²)。"""
    if (pad is None) == (contact is None):
        raise ValueError("%s: pass exactly one of pad (pegtactile.pad_params) or contact ({'a', 'mu', 'G'})" % op)
    if pad is not None:
        hz, Mf = _pad_hertz(P, PT._pad(pad), op)
        return hz["a"], hz["p0"], pad["G"], pad["mu"], Mf
    if not isinstance(contact, dict) or any(k not in contact for k in ("a", "mu", "G")):
        raise ValueError("%s: contact must be a dict with a, mu, G (Hertz contact radius, friction, shear modulus)" % op)
    vals = {}
    for k in ("a", "mu", "G"):
        v = contact[k]
        if isinstance(v, bool) or not isinstance(v, (int, float, np.integer, np.floating)) or not (math.isfinite(float(v)) and float(v) > 0):
            raise ValueError("%s: contact[%r] must be finite and > 0, got %r" % (op, k, v))
        vals[k] = float(v)
    if not (isinstance(P, (int, float, np.integer, np.floating)) and not isinstance(P, bool) and math.isfinite(float(P)) and float(P) > 0):
        raise ValueError("%s: P must be a finite normal force > 0 (in contact), got %r" % (op, P))
    a = vals["a"]
    return a, 3.0 * float(P) / (2.0 * math.pi * a * a), vals["G"], vals["mu"], _FULL_SLIP_COEF * vals["mu"] * float(P) * a


# ======================================================================================================================
def torsion_partial_slip(M: float, P: float, pad: dict | None = None, ctx=None, field: bool = False, na: int = 64,
                         from_no_slip_read: bool = False, contact: dict | None = None) -> dict:
    """球面パッド(Hertz、法線力 ``P``)に法線まわりのねじり ``M`` [N·m] を掛けたときの部分滑り: 固着半径 c、ねじれ角 β、全滑りまでの比。

    数値解はモジュール冒頭(環 ``na`` 本の影響行列、無次元の 1 本の曲線を一度だけ)。返り: ``ratio`` = |M| / ((3π/16)μPa)、``c_over_a``、
    ``beta``(部分滑りのねじれ角 [rad])、``beta_no_slip`` = 3M/(16Ga³)(Reissner–Sagoci)、``read_bias`` = β/β_no_slip(無滑りの関係で
    読んだときの M の過大の倍率)、``a``・``p0``・``M_full``、``slipping``(比 ≥ 1 = 全滑り。例外にせず印 —— 滑りは起きる状態で入力の
    誤りではない。β は定まらないので nan)、``readable``(固着円が読みの核 r < 0.6a を含む)。``field=True`` なら ``ctx``
    (:func:`pegtactile.pad_context`)の格子で周方向トラクションを Cerruti 核で畳んだ表面変位 ``ux``・``uy`` [m] と、マーカーの基準位置での
    ``u_markers`` (N, 2) [m] も返す(合成用。全滑りでは作らない)。``from_no_slip_read=True`` なら ``M`` を **無滑りの関係で読んだ値**
    (Reissner–Sagoci、:func:`pegtactile.pad_tactile_read` の ``torsion_model="no_slip"``)と見て、部分滑りの M に直してから同じ表を返す
    (``M`` = 直した値、``M_read`` = 渡した読み。読みが全滑りの像を超えていれば ``M`` = 全滑りのトルクで ``slipping``)。
    ``ratio_table_max`` は表の最後の行の比(これ以上は固着円が環 1 本より小さく、場を作らない)。
    パッドの代わりに ``contact={"a": 接触半径 [m], "mu": 摩擦係数, "G": せん断弾性率 [Pa]}`` を渡すと、接触半径が分かっている Hertz 接触
    (圧力 p₀√(1 − r²/a²)、p₀ = 3P/(2πa²))として同じ数値解を返す —— :func:`tactorque.torque_decompose` の ``Mz`` の補正はこの入口を通る
    (``field=True`` はパッドの格子が要るので ``pad`` だけ)。
    **Raises** ValueError: P ≤ 0・非有限、M が非有限、pad が :func:`pegtactile.pad_params` の表でない、pad と contact の両方 / どちらも無い、
    contact の a・mu・G が正の有限でない、field=True で pad が無い、na < 24。"""
    op = "torsion_partial_slip"
    if field and pad is None:
        raise ValueError("%s: field=True needs pad (the membrane grid comes from pegtactile.pad_context)" % op)
    Mv = float(M) if not isinstance(M, bool) else float("nan")
    if not math.isfinite(Mv):
        raise ValueError("%s: M must be finite, got %r" % (op, M))
    if int(na) != na or int(na) < 24:
        raise ValueError("%s: na must be an integer >= 24" % op)
    a, p0, G, mu, Mf = _contact_hertz(P, pad, contact, op)
    tab = _torsion_table(int(na))
    M_read = None
    if from_no_slip_read:
        M_read = Mv
        Mv = _true_torsion_from_stick_read(Mv, float(P), pad, int(na), contact=contact)[0]
    ratio = abs(Mv) / Mf
    beta_ns = 3.0 * Mv / (16.0 * G * a ** 3)
    out = {"ratio": float(ratio), "a": float(a), "p0": float(p0), "M_full": float(Mf), "beta_no_slip": float(beta_ns), "M": Mv,
           "ratio_table_max": float(tab["ratio"][-1])}
    if M_read is not None:
        out["M_read"] = M_read
    if ratio >= tab["ratio"][-1]:
        out.update({"c_over_a": 0.0, "beta": float("nan"), "read_bias": float("nan"), "slipping": bool(ratio >= 1.0),
                    "readable": False})
        if field:
            raise ValueError("%s: torsion at or beyond full slip (ratio %.3f); no partial-slip field" % (op, ratio))
        return out
    c_a, bias, (i0, i1, w0) = _interp_ratio(tab, ratio)
    out.update({"c_over_a": float(c_a), "beta": float(beta_ns * bias), "read_bias": float(bias), "slipping": False,
                "readable": bool(c_a >= READ_CORE_C_OVER_A)})
    if field and Mv != 0.0:
        ctx = PT._ctx_for(pad, ctx)
        if ratio <= tab["ratio"][0]:
            # 無滑りの極限の近く: 表の最初の行(外周の 1 環だけ滑る)の形を比で縮める
            q_u = tab["q"][0] * (ratio / tab["ratio"][0])
        else:
            q_u = w0 * tab["q"][i0] + (1.0 - w0) * tab["q"][i1]
        # 環ごとの値を半径で線形補間(縁で 0)、μp₀ を掛けて符号を付ける
        rr = np.hypot(ctx["X"], ctx["Y"]) / a
        q = np.interp(rr, np.concatenate([[0.0], tab["rc"], [1.0]]), np.concatenate([[0.0], q_u, [0.0]]), right=0.0)
        q = math.copysign(mu * p0, Mv) * q
        th = np.arctan2(ctx["Y"], ctx["X"])
        u = TQ._tangential_displacement(-np.sin(th) * q, np.cos(th) * q, ctx["kern"])
        pts = ctx["pts_flat"]
        out.update({"ux": u["ux"], "uy": u["uy"], "u_markers": np.column_stack([S._sample(u["ux"], pts), S._sample(u["uy"], pts)])})
    return out


def _true_torsion_from_stick_read(tau_read, P, pad, na, contact=None):
    """無滑りの関係で読んだねじり τ_read(= M·β/β_RS)→ 部分滑りの M。m·bias(m) は単調なので表で逆に引く。"""
    Mf = _contact_hertz(P, pad, contact, "knife_load_from_pads")[4]
    tab = _torsion_table(na)
    bias_tab = tab["beta"] / (3.0 * tab["M"] / 16.0)
    x = tab["ratio"] * bias_tab                         # 読み / M_full
    xr = abs(tau_read) / Mf
    if xr >= x[-1]:
        return math.copysign(Mf, tau_read), 0.0, False, True
    if xr <= x[0]:
        # 無滑りの極限へ線形: x ≈ m (1 + (b0 − 1) m / r0)
        r0, b0 = tab["ratio"][0], bias_tab[0]
        k = (b0 - 1.0) / r0
        m = (-1.0 + math.sqrt(1.0 + 4.0 * k * xr)) / (2.0 * k) if k > 0 else xr
    else:
        m = float(np.interp(xr, x, tab["ratio"]))
    c_a = _interp_ratio(tab, m)[0]
    return math.copysign(m * Mf, tau_read), float(c_a), bool(c_a >= READ_CORE_C_OVER_A), False


def _read_keys(rd, name, op):
    """読みの dict → (P, q, 無滑りの関係で読んだねじり)。

    :func:`pegtactile.pad_tactile_read` は既定(``torsion_model="partial_slip"``)で ``torsion`` を部分滑りに直して返し、無滑りの値を
    ``torsion_no_slip`` に残す。ここでは常に無滑りの値から始める(二重に直さない)。``torsion_model`` の無い dict(閉形式の荷重・0.4.0 の
    読み)は ``torsion`` を無滑りの読みとして扱う。"""
    if not isinstance(rd, dict) or not all(k in rd for k in ("P", "q", "torsion")):
        raise ValueError("%s: %s must be the dict from pegtactile.pad_tactile_read (needs P, q, torsion)" % (op, name))
    q = np.asarray(rd["q"], np.float64).reshape(-1)
    model = rd.get("torsion_model", "no_slip")
    if model == "partial_slip":
        if "torsion_no_slip" not in rd:
            raise ValueError("%s: %s says torsion_model='partial_slip' but has no torsion_no_slip" % (op, name))
        P, tq = float(rd["P"]), float(rd["torsion_no_slip"])
    elif model == "no_slip":
        P, tq = float(rd["P"]), float(rd["torsion"])
    else:
        raise ValueError("%s: %s has an unknown torsion_model %r" % (op, name, model))
    if q.size != 2 or not (np.all(np.isfinite(q)) and math.isfinite(P) and math.isfinite(tq)) or P <= 0:
        raise ValueError("%s: %s has a non-finite or non-positive reading" % (op, name))
    return P, q, tq


def _pad_wrench_of(read_R, read_L, pad, torsion_model, na, op):
    """空中のコマの 2 枚の読み → パッド → 包丁のレンチ(風袋。ねじりは本体と同じ模型で直す)。"""
    PR, qR, tR = _read_keys(read_R, "tare[0]", op)
    PL, qL, tL = _read_keys(read_L, "tare[1]", op)
    if torsion_model == "partial_slip":
        tR = _true_torsion_from_stick_read(tR, PR, pad, na)[0]
        tL = _true_torsion_from_stick_read(tL, PL, pad, na)[0]
    w = PT.pad_loads_to_peg_wrench(PR, qR, PL, qL, pad, torsion=0.5 * (tR + tL))
    return {"F": np.asarray(w["F"], float), "M": np.asarray(w["M"], float)}


def knife_load_from_pads(read_R: dict, read_L: dict, pad: dict, Lz: float, edge_slope: float = 0.0,
                         torsion_model: str = "partial_slip", tare=None, v_min: float = 0.05, na: int = 64) -> dict:
    """2 枚のパッドの読み(:func:`pegtactile.pad_tactile_read`)→ 刃が食材から受ける押し V・引き H・モーメント M_x と、刃の当たり位置 Ly。

    ``Lz`` [m]: 把持点から刃先までの高さ(刃が傾いていれば把持点の真下での値 Lz₀、``edge_slope`` = 刃先の傾きの正接で
    ``Ly = (M_x + Lz₀ H)/(V + s H)``)。``torsion_model``: ``"partial_slip"``(既定 —— 無滑りの関係で読まれたねじりを部分滑りの数値解で
    直す、モジュール冒頭)/ ``"no_slip"``(無滑りの読みのまま = :mod:`pegtactile` 0.4.0 の約束、比べるため)。読みが
    :func:`pegtactile.pad_tactile_read` の既定(既に部分滑りに直した ``torsion`` と無滑りの ``torsion_no_slip``)でも、ここは無滑りの値から
    始めるので二重には直さない。``tare``: 空中の 1 コマの 2 枚の読み
    ``(read_R, read_L)``(または前の返り・``{"F": (3,), "M": (3,)}`` のパッドのレンチ)—— 包丁の重さを差し引く(空中のコマそのものは
    V = 0 で Ly が定まらないので、この op に単独では渡せない)。
    返り: ``V``・``H``・``Mx``(食材 → 刃、グリッパ系)、``Ly``・``xi``(= H/V)、パッドごとの ``torsion``(直した値)・``torsion_read``・
    ``torsion_ratio``・``slip_ratio``(せん断 |q|/μP)・``c_over_a``、``combined_margin`` = 1 − max(せん断の比 + ねじりの比)(十分条件)、
    ``readable``(両方のパッドで固着円が読みの核を含む)、``Ly_range_full_slip``・``Ly_range_readable``(いまの V・H・把持力のまま当たり位置が
    動いたとき、全滑り / 読めなくなるまでの Ly の範囲 = 持てる柄の長さの限界)、``pad_wrench``(パッド → 刃、tare 前)、``torsion_model``。
    **Raises** ValueError: 読みが壊れている、V ≤ ``v_min``(刃が食材を押していない = Ly が定まらない)、綴り違い、Lz が非有限。"""
    op = "knife_load_from_pads"
    pad = PT._pad(pad)
    if torsion_model not in ("partial_slip", "no_slip"):
        raise ValueError("%s: torsion_model must be 'partial_slip' or 'no_slip', got %r" % (op, torsion_model))
    Lz = float(Lz) if not isinstance(Lz, bool) else float("nan")
    s = float(edge_slope) if not isinstance(edge_slope, bool) else float("nan")
    vm = float(v_min) if not isinstance(v_min, bool) else float("nan")
    if not (math.isfinite(Lz) and math.isfinite(s) and math.isfinite(vm) and vm >= 0.0):
        raise ValueError("%s: Lz, edge_slope must be finite and v_min >= 0" % op)
    PR, qR, tR = _read_keys(read_R, "read_R", op)
    PL, qL, tL = _read_keys(read_L, "read_L", op)
    pads = {}
    for side, P_, q_, t_ in (("R", PR, qR, tR), ("L", PL, qL, tL)):
        _, Mf = _pad_hertz(P_, pad, op)
        if torsion_model == "partial_slip":
            tc, c_a, ok, sat = _true_torsion_from_stick_read(t_, P_, pad, int(na))
        else:
            tc = t_
            info = torsion_partial_slip(t_, P_, pad, na=int(na))
            c_a, ok, sat = info["c_over_a"], info["readable"], info["slipping"]
        pads[side] = {"P": P_, "torsion": tc, "torsion_read": t_, "torsion_ratio": abs(tc) / Mf, "M_full": Mf,
                      "slip_ratio": float(np.hypot(*q_) / (pad["mu"] * P_)), "c_over_a": c_a, "readable": bool(ok and not sat)}
    w = PT.pad_loads_to_peg_wrench(PR, qR, PL, qL, pad, torsion=0.5 * (pads["R"]["torsion"] + pads["L"]["torsion"]))
    F, M = np.asarray(w["F"], float), np.asarray(w["M"], float)
    if tare is not None:
        if isinstance(tare, (list, tuple)) and len(tare) == 2:
            tare = _pad_wrench_of(tare[0], tare[1], pad, torsion_model, int(na), op)
        elif isinstance(tare, dict) and "pad_wrench" in tare:
            tare = tare["pad_wrench"]
        if not isinstance(tare, dict) or "F" not in tare or "M" not in tare:
            raise ValueError("%s: tare must be (read_R, read_L) of a frame in the air, a previous result, or a dict with F and M" % op)
        Ft, Mt = np.asarray(tare["F"], float).reshape(3), np.asarray(tare["M"], float).reshape(3)
        if not (np.all(np.isfinite(Ft)) and np.all(np.isfinite(Mt))):
            raise ValueError("%s: tare must be finite" % op)
        F, M = F - Ft, M - Mt
    Ff, Mfood = -F, -M                                   # 準静的: 食材 → 刃 = −(パッド → 刃)
    V, H, Mx = float(Ff[2]), float(-Ff[1]), float(Mfood[0])
    if not (V > vm):
        raise ValueError("%s: push V = %.4g N <= v_min %.4g N (the blade is not loading the food; Ly is undefined)" % (op, V, vm))
    den = V + s * H
    if not (den > 0):
        raise ValueError("%s: V + edge_slope*H = %.4g <= 0; the contact position is undefined" % (op, den))
    Ly = (Mx + Lz * H) / den
    Mf_min = min(pads["R"]["M_full"], pads["L"]["M_full"])
    tab = _torsion_table(int(na))
    m_read = float(np.interp(READ_CORE_C_OVER_A, tab["c"][::-1], tab["ratio"][::-1]))

    def rng(m):
        lim = 2.0 * m * Mf_min                           # 1 枚あたり |M_x|/2 ≤ m M_full
        return ((-lim + Lz * H) / den, (lim + Lz * H) / den)
    comb = 1.0 - max(pads[k]["slip_ratio"] + pads[k]["torsion_ratio"] for k in pads)
    return {"V": V, "H": H, "Mx": Mx, "Ly": float(Ly), "xi": float(H / V), "pads": pads,
            "torsion_ratio": max(pads[k]["torsion_ratio"] for k in pads), "slip_ratio": max(pads[k]["slip_ratio"] for k in pads),
            "c_over_a": min(pads[k]["c_over_a"] for k in pads), "combined_margin": float(comb),
            "readable": bool(pads["R"]["readable"] and pads["L"]["readable"]),
            "Ly_range_full_slip": rng(1.0), "Ly_range_readable": rng(m_read), "ratio_at_read_limit": m_read,
            "pad_wrench": {"F": np.asarray(w["F"], float), "M": np.asarray(w["M"], float)}, "torsion_model": torsion_model,
            "Lz": Lz, "edge_slope": s}


def toughness_from_pads(loads, w_eff_mm, xi: float | None = None, min_w_mm: float = 2.0, readable_only: bool = True) -> dict:
    """:func:`knife_load_from_pads` の列と切っている幅 w_eff [mm] (画像から、:func:`cutting.food_cut_width`)→ 靱性 R と当たり位置の要約。

    R = 原点を通る最小二乗 ``V = R · w_eff · g(ξ)``、g = 1/(1+ξ²)(:func:`cutting.cut_force_fit`、摩擦は R に吸い込まれる)。ξ は
    ``xi`` を渡せばそれ(運動から)、省けば **触覚だけ** の ξ̂ = 中央値(H/V)(w_eff ≥ ``min_w_mm`` かつ読めるコマ)。``readable_only`` なら
    ``readable = False`` のコマは使わない(黙って混ぜない、数は ``n_unreadable`` に)。返り: ``R``・``rms_n``・``n``、``xi_used``・
    ``xi_tactile``(中央値)・``xi_tactile_iqr``、``Ly_median``・``Ly_mad``(読めるコマ)、``n_unreadable``、``model``。
    **Raises** ValueError: 長さ違い、使えるコマが 3 未満、要素が knife_load_from_pads の返りでない。"""
    op = "toughness_from_pads"
    if not isinstance(loads, (list, tuple)) or not loads:
        raise ValueError("%s: loads must be a non-empty list of knife_load_from_pads results" % op)
    for i, L in enumerate(loads):
        if not isinstance(L, dict) or not all(k in L for k in ("V", "H", "Ly", "readable")):
            raise ValueError("%s: loads[%d] is not a knife_load_from_pads result" % (op, i))
    try:
        w = np.asarray(w_eff_mm, np.float64).reshape(-1)
    except (TypeError, ValueError):
        raise ValueError("%s: w_eff_mm must be numeric" % op) from None
    if w.size != len(loads) or not np.all(np.isfinite(w)):
        raise ValueError("%s: w_eff_mm must be finite with one value per load (%d vs %d)" % (op, w.size, len(loads)))
    mw = float(min_w_mm)
    V = np.array([L["V"] for L in loads], float)
    H = np.array([L["H"] for L in loads], float)
    Ly = np.array([L["Ly"] for L in loads], float)
    ok = np.array([bool(L["readable"]) for L in loads])
    use = (w >= mw) & (ok if readable_only else True)
    if use.sum() < 3:
        raise ValueError("%s: only %d usable frames (w_eff >= %g mm%s)" % (op, int(use.sum()), mw, " and readable" if readable_only else ""))
    xr = H[use] / V[use]
    xi_t = float(np.median(xr))
    if xi is None:
        xi_u = abs(xi_t)
    else:
        xi_u = float(xi)
        if not (math.isfinite(xi_u) and xi_u >= 0):
            raise ValueError("%s: xi must be finite and >= 0" % op)
    fit = C.cut_force_fit(V[use], w[use], xi_u, min_w_mm=mw)
    lyu = Ly[use]
    q75, q25 = np.percentile(xr, [75, 25])
    return {"R": fit["R"], "rms_n": fit["rms_n"], "n": fit["n"], "xi_used": xi_u, "xi_tactile": xi_t, "xi_tactile_iqr": float(q75 - q25),
            "Ly_median": float(np.median(lyu)), "Ly_mad": float(np.median(np.abs(lyu - np.median(lyu)))),
            "n_unreadable": int(np.sum((w >= mw) & ~ok)), "model": fit["model"]}
