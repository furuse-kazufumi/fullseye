# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""diabolo — ディアボロ(中国ごま)の解析模型を確かめ、合成映像から軸・回転・位置・糸の張力を読む(台帳 ``diabolo``、2026-10-05)。

物理シミュ × Fullseye 系列。一次情報はロボット学習用のディアボロ解析模型(von Drigalski ほか、ICRA 2021、arXiv:2011.09068)の
LaTeX 原文で、式はそこから写した。公開実装(BSD-3)は読んで比べただけで、コードは写していない。人の演技データはライセンスが
無いので使っていない。学習なし、全部ルール。

論文の模型(ディアボロ = 質点 + 糸が作る補助の回転楕円体 + 重力、1 ステップ = 前進 Euler → 楕円体の外に出たら戻す)を写し、
**原文どおりでは成り立たない所を直して**(:func:`diabolo_spheroid` の docstring)、外の真値 3 系統と突き合わせる:

  * **閉形式・恒等式**: 焦点の恒等式 d_L + d_R = l、前進 Euler のずれ g t dt/2、回転の式 (2) の望遠鏡和と転がりの極限 μ = 1/r、
    振り子の周期(横 2π√(b/g)、縦は楕円の最下点の曲率半径 a²/b で 2π√(a²/(bg)))、静止張力 T = m g a/(2b)、放物線の頂点と受け。
  * **厳密な参照模型**(論文には無い、こちらで足した物): 伸びない糸 + 摩擦のない滑車 = 点の片側拘束 d_L + d_R ≤ l を RATTLE で
    解く(:func:`diabolo_simulate` の ``model="exact"``)。棒が止まっていればエネルギーが有界、焦点軸が鉛直なら角運動量が丸めの桁で
    保存、張力 × 棒の速度の仕事率でエネルギーの変化が閉じる。軸は糸に「乗っている」だけなので、棒を結ぶ面より上では拘束しない。
  * **第 2 実装**: MuJoCo の空間テンドン(棒の先 → ディアボロ → 棒の先、長さの上限 = 糸)。:func:`diabolo_scene_mjcf` は文字列で
    mujoco 不要、走らせる :func:`diabolo_mujoco_simulate` は facade だけで台帳には載せない。

視覚(光線追跡の合成映像 → 規則): 手前のカップの縁の円と底の板の円、2 つの円の厳密な透視投影の多角形モーメントを Gauss–Newton で
マスクのモーメントに合わせて軸と中心を出す(:func:`diabolo_axis_from_image`、残差が大きければ警報 ``ok = False``)。回転は内面の
マーカーの位相と回転ぶれの弧の幅から(:func:`diabolo_marker_phase`、:func:`diabolo_spin_from_markers`。位相だけではナイキストを
超えると折り返す)。張力は棒の先と軸の V 字から(:func:`string_tension_from_sag`)。

numpy 層(台帳 ``diabolo``、16 op): :func:`diabolo_params` / :func:`diabolo_spheroid` / :func:`spheroid_closest` /
  :func:`diabolo_dynamics_step` / :func:`diabolo_simulate` / :func:`diabolo_state_sequence` / :func:`diabolo_throw_catch_truth` /
  :func:`string_tension_static` / :func:`string_tension_from_sag` / :func:`diabolo_camera` / :func:`diabolo_render` /
  :func:`diabolo_axis_from_image` / :func:`diabolo_marker_phase` / :func:`diabolo_spin_from_markers` / :func:`diabolo_track` /
  :func:`diabolo_scene_mjcf`(MJCF 文字列、mujoco 不要)。
mujoco 層(facade のみ): :func:`diabolo_mujoco_simulate`。

正直に: 外の真値は論文の式・閉形式・MuJoCo だけで、実写や公開データとは合わせていない(式の誤りは見つけたが、模型が実物に合うかは
確かめていない)。回転の式 (2) の μ・減衰係数・姿勢(傾きと首振り、ジャイロ)は論文にも模型にも無く、画像から読む軸は描いた時に
与えた姿勢であって力学の結果ではない。描画は理想化(塗り分けた色・Lambert の陰影・無地の背景)で、実物の色・艶・照明では分割の規則を
作り直す必要がある。軸の推定には手前のカップの内側が見えること(視線からの傾き 38° まで)が要る。糸は点で、軸の半径への巻き付き・
糸の質量と伸び・軸の上の滑り摩擦は入れていない。受けの瞬間は厳密模型と論文の模型が完全非弾性、MuJoCo の柔らかい拘束は跳ねる。

規約: 長さ m、時間 s、角 rad(引数名に _deg が付くものだけ度)。世界 x = 前(ロボットから離れる向き)、z = 上、重力 −z。
棒の先は (x_L, x_R) で x_L が +y 側。棒の組は matrix (2, 3)、棒の時系列は (N, 2, 3)。
"""
from __future__ import annotations

import inspect
import math
import xml.etree.ElementTree as ET

import numpy as np
from scipy import ndimage

__all__ = [
    "DIABOLO_STATES",
    "diabolo_params", "diabolo_spheroid", "spheroid_closest", "diabolo_dynamics_step", "diabolo_simulate",
    "diabolo_state_sequence", "diabolo_throw_catch_truth", "string_tension_static", "string_tension_from_sag",
    "diabolo_camera", "diabolo_render", "diabolo_axis_from_image", "diabolo_marker_phase", "diabolo_spin_from_markers",
    "diabolo_track", "diabolo_scene_mjcf",
    # mujoco が要る(facade のみ、台帳の外)
    "diabolo_mujoco_simulate",
]

G = 9.81
#: 論文の状態(糸に乗っている / 糸がたるんで離れている / 飛んでいる)
DIABOLO_STATES = ("on_string", "off_string_loose", "flying")

# 論文の表 I(質量・直径・長さ・軸受)。軸の半径・糸の長さ・カップの奥行きなどは論文に無い → 仮定(assumed に列挙)。
_KINDS = {
    "red": dict(mass=0.2845, diameter=0.127, length=0.143, bearing=False),
    "blue": dict(mass=0.2895, diameter=0.127, length=0.143, bearing=True),
    "patterned": dict(mass=0.218, diameter=0.097, length=0.114, bearing=False),
    "green": dict(mass=0.1415, diameter=0.082, length=0.093, bearing=False),
}
_PARAM_KEYS = {"mass", "diameter", "length", "bearing", "axle_radius", "string_length", "mu_acc", "mu_dec", "c_l", "c_f",
               "taut_margin", "plane_margin", "hub_radius", "hub_z", "marker_radius_frac", "marker_size", "bright_slots",
               "n_slots", "g"}

# 合成映像の色(塗り分け)。内面の黄と底の板の暗い灰、白い反射マーカーと灰のダミー。
_C_OUT = np.array([0.80, 0.14, 0.12])
_C_IN = np.array([0.95, 0.80, 0.15])
_C_HUB = np.array([0.20, 0.20, 0.22])
_C_AXLE = np.array([0.30, 0.30, 0.30])
_C_MARK = np.array([1.0, 1.0, 1.0])
_C_DUMMY = np.array([0.55, 0.55, 0.55])
_C_STRING = np.array([0.10, 0.10, 0.10])
_C_STICK = np.array([0.45, 0.30, 0.15])
_C_TIP = np.array([0.15, 0.35, 0.95])
_LIGHT = np.array([0.45, -0.35, 0.60])          # 面 → 光の向き(世界系、正規化は使う所で)
_DUMMY_WEIGHT = 0.35                            # 灰のダミーの白さ (B − 0.19 G) は反射の約 0.35 倍
#: 円 2 つの透視モーメントが合わない = 底の板が壁に隠れた等の警報の閾値、単位 px(45° で 2.8 px、38° まで ≤ 0.02 px)
_RESIDUAL_ALARM_PX = 0.15


# ----------------------------------------------------------------------------------------------------------------------
# 寸法
def diabolo_params(kind: str = "red", **override) -> dict:
    """ディアボロと糸の寸法の辞書。``kind`` = red / blue / patterned / green(論文の表 I の質量・直径・長さ・軸受)。

    論文に無い値は仮定として ``assumed`` に名前を残す: 軸の半径 6.5 mm(公開実装の既定値)、糸 1.45 m(本文の「145 cm」)、
    μ_acc = 1/r(転がりの極限、rad/m)、μ_dec = 0.8/r、c_L = 1 cm・c_F = 5 cm(論文の図の説明)、張りつめの余裕 3 cm(公開実装)、
    面の規則の余裕 5 cm(本文)、カップの底の板 半径 12 mm・中心から 12 mm、マーカーは内面の 55 % の半径に 8 か所(うち反射は
    0, 1, 3 番 = 回転の向きが一意に決まる非対称の並び。論文は反射しない印刷のダミーで質量の対称を保った)。

    **Raises** ``ValueError``: 知らない ``kind``、綴りの違う鍵(fail-closed)、質量・寸法が有限の正でない、底の板がカップの外、
    c_L ≥ c_F。"""
    if not isinstance(kind, str) or kind not in _KINDS:
        raise ValueError("diabolo_params: unknown kind %r (expected one of %s)" % (kind, sorted(_KINDS)))
    bad = sorted(set(override) - _PARAM_KEYS)
    if bad:
        raise ValueError("diabolo_params: unknown parameter key(s) %s (known: %s)" % (bad, sorted(_PARAM_KEYS)))
    p = dict(_KINDS[kind])
    r = 0.0065
    p.update(kind=kind, axle_radius=r, string_length=1.45, mu_acc=1.0 / r, mu_dec=0.8 / r, c_l=0.01, c_f=0.05,
             taut_margin=0.03, plane_margin=0.05, hub_radius=0.012, hub_z=0.012, marker_radius_frac=0.55,
             marker_size=0.006, bright_slots=(0, 1, 3), n_slots=8, g=G)
    p["assumed"] = ["axle_radius", "string_length", "mu_acc", "mu_dec", "taut_margin", "plane_margin", "hub_radius", "hub_z",
                    "marker_radius_frac", "marker_size", "bright_slots"]
    p.update(override)
    for k in ("mass", "diameter", "length", "axle_radius", "string_length", "hub_radius", "hub_z", "g", "marker_size"):
        v = float(p[k])
        if not (math.isfinite(v) and v > 0):
            raise ValueError("diabolo_params: %s must be finite and > 0 (got %r)" % (k, p[k]))
    for k in ("mu_acc", "mu_dec", "c_l", "c_f", "taut_margin", "plane_margin"):
        if not (math.isfinite(float(p[k])) and float(p[k]) >= 0):
            raise ValueError("diabolo_params: %s must be finite and >= 0 (got %r)" % (k, p[k]))
    if not (0 < p["hub_z"] < p["length"] / 2 and p["hub_radius"] < p["diameter"] / 2):
        raise ValueError("diabolo_params: the hub plate must sit inside the cup")
    if not (0 < p["marker_radius_frac"] < 1):
        raise ValueError("diabolo_params: marker_radius_frac must be in (0, 1)")
    if not (0 <= p["c_l"] < p["c_f"]):
        raise ValueError("diabolo_params: need 0 <= c_l < c_f")
    if int(p["n_slots"]) < 1 or any(not (0 <= int(b) < int(p["n_slots"])) for b in p["bright_slots"]):
        raise ValueError("diabolo_params: bright_slots must index the n_slots marker slots")
    return p


def _check_params(params, who):
    if not isinstance(params, dict) or not {"mass", "string_length", "g", "c_l", "c_f"} <= set(params):
        raise ValueError("%s: params must be the dict from diabolo_params" % who)
    return params


def _v3(x, name):
    try:
        a = np.asarray(x, np.float64).reshape(-1)
    except (TypeError, ValueError) as exc:
        raise ValueError("%s must be a finite 3-vector" % name) from exc
    if a.shape != (3,) or not np.all(np.isfinite(a)):
        raise ValueError("%s must be a finite 3-vector" % name)
    return a


def _pair(sticks, name="sticks"):
    try:
        s = np.asarray(sticks, np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError("%s must be a (2, 3) array (x_L, x_R)" % name) from exc
    if s.shape != (2, 3) or not np.all(np.isfinite(s)):
        raise ValueError("%s must be a finite (2, 3) array (x_L, x_R), got shape %s" % (name, s.shape))
    return s[0].copy(), s[1].copy()


# ----------------------------------------------------------------------------------------------------------------------
# 回転楕円体(式 1)
def diabolo_spheroid(p_left, p_right, string_length: float) -> dict:
    """棒の先 2 点(焦点)と糸の長さ → 補助の回転楕円体: a = l/2、c = |x_L − x_R|/2、b = √(a² − c²)(式 1 の正しい形)。

    ★原文の (1b) は b = √(a² − |x_L − x_R|/2) で、長さと長さの 2 乗の差なので次元が合わない。論文の実機寸法(糸 1.45 m、棒の間隔
    1.10 m)を入れると根の中が負になる(NaN)。楕円の恒等式 a² = b² + c² の形に直した(公開実装も 2 乗で書いている)。原文の値は
    ``b_paper_literal`` に残す。原文の前文は「半長軸 b と半短軸 a」と名前が逆(a = l/2 が半長軸)で、式の側に従う。

    返り ``{"center", "axis"(x_L − x_R の単位ベクトル), "a", "b", "c", "b_paper_literal"}``。
    **Raises** ``ValueError``: 間隔 ≥ 糸、棒が重なる、有限でない入力。"""
    pl, pr = _v3(p_left, "diabolo_spheroid: p_left"), _v3(p_right, "diabolo_spheroid: p_right")
    l = float(string_length)
    if not (math.isfinite(l) and l > 0):
        raise ValueError("diabolo_spheroid: string_length must be finite and > 0")
    d = float(np.linalg.norm(pl - pr))
    if d >= l:
        raise ValueError("diabolo_spheroid: sticks are %.4f m apart, not less than the string length %.4f m" % (d, l))
    if d < 1e-12:
        raise ValueError("diabolo_spheroid: sticks coincide, the spheroid axis is undefined")
    a, c = l / 2.0, d / 2.0
    lit = a * a - d / 2.0
    return {"center": 0.5 * (pl + pr), "axis": (pl - pr) / d, "a": a, "b": math.sqrt(a * a - c * c), "c": c,
            "b_paper_literal": math.sqrt(lit) if lit >= 0 else float("nan")}


def _ellipse_root(r0, z0, z1, g):
    n0 = r0 * z0
    s0, s1 = z1 - 1.0, (0.0 if g < 0 else math.hypot(n0, z1) - 1.0)
    s = 0.0
    for _ in range(200):
        s = 0.5 * (s0 + s1)
        if s == s0 or s == s1:
            break
        g = (n0 / (s + r0)) ** 2 + (z1 / (s + 1.0)) ** 2 - 1.0
        if g > 0:
            s0 = s
        elif g < 0:
            s1 = s
        else:
            break
    return s


def _ellipse_closest(e0, e1, y0, y1):
    """第 1 象限の点 (y0, y1) から楕円 (x0/e0)² + (x1/e1)² = 1(e0 ≥ e1)への最近点(Eberly の二分法)。"""
    if y1 > 0:
        if y0 > 0:
            z0, z1 = y0 / e0, y1 / e1
            g = z0 * z0 + z1 * z1 - 1.0
            if g != 0:
                r0 = (e0 / e1) ** 2
                sb = _ellipse_root(r0, z0, z1, g)
                return r0 * y0 / (sb + r0), y1 / (sb + 1.0)
            return y0, y1
        return 0.0, e1
    num, den = e0 * y0, e0 * e0 - e1 * e1
    if num < den:
        x0 = e0 * num / den
        return x0, e1 * math.sqrt(max(0.0, 1.0 - (x0 / e0) ** 2))
    return e0, 0.0


def _any_perp(u):
    t = np.array([0.0, 0.0, 1.0]) if abs(u[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    w = np.cross(u, t)
    return w / np.linalg.norm(w)


def _check_sph(sph, who):
    if not isinstance(sph, dict) or not {"center", "axis", "a", "b"} <= set(sph):
        raise ValueError("%s: sph must be the dict from diabolo_spheroid" % who)
    return sph


def spheroid_closest(x, sph: dict) -> dict:
    """点 x → 回転楕円体の面の最近点 ``point``・符号つき距離 ``s``(内側 > 0、論文の s の定義)・外向きの単位法線 ``normal``
    (最近点での勾配の向き)。

    最近点は子午面の楕円への Eberly の二分法。★公開実装は中心から放射方向に縮めて戻し(最近点ではない、楕円体の外 5 mm の点で
    最大 2.2 mm 違う)、法線を (x/b, y/a, z/b) で近似する(勾配なら 2 乗、軸の上以外では最大 12.2° ずれる)。ここでは本文の
    「最も近い点へ動かす」と真の法線で書く。**Raises** ``ValueError``: x が有限の 3-vector でない、sph が楕円体の dict でない。"""
    x = _v3(x, "spheroid_closest: x")
    _check_sph(sph, "spheroid_closest")
    u, c0, a, b = np.asarray(sph["axis"], np.float64), np.asarray(sph["center"], np.float64), float(sph["a"]), float(sph["b"])
    r = x - c0
    z = float(r @ u)
    perp = r - z * u
    rho = float(np.linalg.norm(perp))
    e_perp = perp / rho if rho > 1e-15 else _any_perp(u)
    zq, rq = _ellipse_closest(a, b, abs(z), rho)
    zq = math.copysign(zq, z) if z != 0 else zq
    q = c0 + zq * u + rq * e_perp
    inside = (z / a) ** 2 + (rho / b) ** 2 < 1.0
    dist = float(np.linalg.norm(x - q))
    nrm = (zq / a ** 2) * u + (rq / b ** 2) * e_perp
    nrm /= np.linalg.norm(nrm)
    return {"point": q, "s": dist if inside else -dist, "normal": nrm}


def _normal_code_variant(x, sph: dict) -> np.ndarray:
    """公開実装の法線 (x/b, y/a, z/b) の正規化(勾配なら (x/b², y/a², z/b²))。比較用 —— 真の法線との角を門で数える。"""
    u, c0, a, b = sph["axis"], sph["center"], sph["a"], sph["b"]
    r = _v3(x, "x") - c0
    z = float(r @ u)
    perp = r - z * u
    n = (z / a) * u + perp / b
    return n / np.linalg.norm(n)


def _above_stick_plane(x, pl, pr):
    """棒の先 2 点を通り、法線 n = x̂ × (x_L − x_R)(上向き)の面より上か。上なら糸は軸の下にあって引き下ろせない。"""
    n = np.cross([1.0, 0.0, 0.0], pl - pr)
    nn = np.linalg.norm(n)
    if nn < 1e-12:
        return False
    return float((x - 0.5 * (pl + pr)) @ (n / nn)) > 0


def _next_mode(mode, x, s, pl, pr, sph_c, params, flying_rule):
    """論文の状態遷移(図を画像にして読んだ)。LOOSE → ON は図の s < c_F だと ON → LOOSE の帯 (c_L, c_F] と重なって毎ステップ
    行き来するので s ≤ c_L と読む。FLYING → ON は「s < c_F かつ張りつめ かつ棒を結ぶ面より下」(面の規則を足した)。"""
    l, cl, cf = float(params["string_length"]), float(params["c_l"]), float(params["c_f"])
    above = _above_stick_plane(x, pl, pr)
    if flying_rule == "paper":                       # 図: s > c_F で FLYING
        to_fly = s > cf
    else:                                            # 公開実装: 棒の面より上、棒の間、少なくとも片方の棒より高い
        between = float((pl - x) @ (pr - x)) <= 0
        to_fly = above and between and (x[2] > pl[2] or x[2] > pr[2])
    if mode == "flying":
        return "on_string" if (s < cf and 2.0 * sph_c > l - float(params["taut_margin"]) and not above) else "flying"
    if to_fly:
        return "flying"
    if s > cl or (above and s < 0):
        return "off_string_loose"
    return "on_string"


# ----------------------------------------------------------------------------------------------------------------------
# 論文の 1 ステップ(式 2–4 と状態遷移)
_CHOICES = {"plane_rule": ("paper", "code"), "rotation": ("paper", "code"), "flying_rule": ("paper", "code")}


def _check_choice(who, **kw):
    for k, v in kw.items():
        if v not in _CHOICES[k]:
            raise ValueError("%s: %s must be one of %s, got %r" % (who, k, _CHOICES[k], v))


def diabolo_dynamics_step(state: dict, sticks_prev, sticks_now, dt: float, params: dict, *, plane_rule: str = "paper",
                          rotation: str = "paper", flying_rule: str = "paper") -> dict:
    """論文の解析模型を 1 ステップ進める(ディアボロ = 質点 + 補助の回転楕円体 + 重力)。

    ``state`` = ``{"x", "v", "omega", "mode"}``(mode は :data:`DIABOLO_STATES`)。棒の組 = matrix (2, 3)。手順(本文の 1–4):
    前進 Euler で x += v dt、v += g dt → 新しい楕円体 → 状態遷移 → 糸に乗っていて外に出たら最近点へ戻し、v_pull(変位/dt の
    内向き法線成分)を v_origin + v_edge で頭打ち(式 3)、張りつめの近く(間隔 > l − 5 cm)では面の規則(式 4)、外向きの法線速度を
    消す(本文は明記せず、公開実装に合わせた)→ 回転(式 2: ω_t = ω_{t−1} + μ Δ_string、Δ_string = d_R の増分、μ = μ_acc / μ_dec)。
    減衰係数は全部 1(公開実装の既定)。

    選べる形(公開実装との比較用): ``plane_rule`` = "paper"(式 4: n_plane = x̂ × (x_L − x_R) の向きだけ残す)/ "code"(前後の
    成分だけ消す); ``rotation`` = "paper"(式 2、刻みに依らない望遠鏡和)/ "code"(Δω = k (Δd_R/dt − ω r)、k = 0.01。刻みを半分に
    すると ω が 2 倍になる); ``flying_rule`` = "paper"(図: s > c_F)/ "code"(棒を結ぶ面より上)。

    返り ``{"x", "v", "omega", "mode", "s", "pulled", "v_pull_raw"}``。**Raises** ``ValueError``: 選択肢の綴り、知らない mode、
    dt ≤ 0、state の鍵の欠け、棒の組の形。"""
    who = "diabolo_dynamics_step"
    _check_choice(who, plane_rule=plane_rule, rotation=rotation, flying_rule=flying_rule)
    _check_params(params, who)
    if not isinstance(state, dict) or not {"x", "v", "omega", "mode"} <= set(state):
        raise ValueError("%s: state must be a dict with x, v, omega, mode" % who)
    if not (isinstance(dt, (int, float)) and math.isfinite(dt) and dt > 0):
        raise ValueError("%s: dt must be finite and > 0" % who)
    mode = state["mode"]
    if mode not in DIABOLO_STATES:
        raise ValueError("%s: unknown mode %r (expected one of %s)" % (who, mode, DIABOLO_STATES))
    l, g = float(params["string_length"]), float(params["g"])
    pl0, pr0 = _pair(sticks_prev, who + ": sticks_prev")
    pl1, pr1 = _pair(sticks_now, who + ": sticks_now")
    x0, v0 = _v3(state["x"], who + ": state x"), _v3(state["v"], who + ": state v")
    x = x0 + v0 * dt
    v = v0 + np.array([0.0, 0.0, -g]) * dt
    sph1 = diabolo_spheroid(pl1, pr1, l)
    cp = spheroid_closest(x, sph1)
    s = cp["s"]
    d_sticks = 2.0 * sph1["c"]
    new_mode = _next_mode(mode, x, s, pl1, pr1, sph1["c"], params, flying_rule)
    pulled = False
    vpull_raw = np.zeros(3)
    if new_mode == "on_string" and s < 0:
        pulled = True
        q, n_out = cp["point"], cp["normal"]
        n_in = -n_out
        vp = float((q - x) @ n_in) / dt
        vpull = max(vp, 0.0) * n_in
        vpull_raw = vpull.copy()
        sph0 = diabolo_spheroid(pl0, pr0, l)
        dorg = sph1["center"] - sph0["center"]
        cap = (float(np.linalg.norm(dorg)) if float(dorg @ n_in) > 0 else 0.0) / dt     # 原点の移動が内向きなら |Δ原点|/dt
        cap += max(sph0["b"] - sph1["b"], 0.0) / dt                                      # 楕円体の縁が内へ来る速さ
        if np.linalg.norm(vpull) > cap:
            vpull = n_in * cap
        if d_sticks > l - float(params["plane_margin"]) and np.linalg.norm(vpull) > 0:
            mag = np.linalg.norm(vpull)
            if plane_rule == "paper":
                npl = np.cross([1.0, 0.0, 0.0], pl1 - pr1)
                npl /= np.linalg.norm(npl)
                vpull = float(vpull @ npl) * npl
            else:
                nn = np.cross(pl1 - pr1, [0.0, 0.0, 1.0])
                nn /= np.linalg.norm(nn)
                w = vpull - float(vpull @ nn) * nn
                vpull = w / np.linalg.norm(w) * mag if np.linalg.norm(w) > 0 else w
        x = q
        v = v + vpull
        vn = float(v @ n_out)
        if vn > 0:
            v = v - vn * n_out
    omega = float(state["omega"])
    if mode == "on_string" and new_mode == "on_string":
        dstr = float(np.linalg.norm(x - pr1)) - float(np.linalg.norm(x0 - pr0))
        if rotation == "paper":
            mu = float(params["mu_acc"]) if dstr > 0 else float(params["mu_dec"])
            omega = omega + mu * dstr
        else:
            omega = omega + (dstr / dt - omega * float(params["axle_radius"])) * 0.01
    return {"x": x, "v": v, "omega": omega, "mode": new_mode, "s": s, "pulled": pulled, "v_pull_raw": vpull_raw}


# ----------------------------------------------------------------------------------------------------------------------
# 棒の動き(閉形式の関数)。棒の先 = (x_L, x_R)、x_L は +y 側。
_Z0, _GAP = 1.0, 1.1


def _mo_fixed(t, gap=_GAP, z=_Z0):
    return np.array([[0.0, gap / 2, z], [0.0, -gap / 2, z]])


def _mo_linear_accel(t, amp=0.10, freq=2.0):
    """論文の「直線加速」の型: 左右の棒を逆位相で上下(糸が軸の上を往復して回す)。"""
    s = amp * math.sin(2 * math.pi * freq * t)
    return np.array([[0.0, _GAP / 2, _Z0 + s], [0.0, -_GAP / 2, _Z0 - s]])


def _mo_swing(t, amp=0.15, freq=0.9):
    """両手を揃えて左右に振る(ディアボロが大きく振れる)。"""
    s = amp * math.sin(2 * math.pi * freq * t)
    return np.array([[0.0, _GAP / 2 + s, _Z0], [0.0, -_GAP / 2 + s, _Z0]])


def _smooth(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * u * (10 - 15 * u + 6 * u * u)


def _mo_throw(t, t0=0.30, dur=0.20, gap1=1.43, lift=0.10, t_catch=1.40):
    """投げ: t0 から dur で棒を開き(間隔 1.1 → 1.43 m、張りつめの帯 l − 3 cm = 1.42 m より外)持ち上げ、開いたまま待って受ける
    (張りつめているので FLYING → ON_STRING が許される)。t_catch 以降は少し戻す。"""
    u = _smooth((t - t0) / dur)
    w = _smooth((t - t_catch) / 0.3)
    gap = _GAP + (gap1 - _GAP) * u - (gap1 - 1.40) * w * 0.5
    z = _Z0 + lift * u
    return np.array([[0.0, gap / 2, z], [0.0, -gap / 2, z]])


def _mo_vertical_axis(t, top=1.6, bottom=0.5):
    """焦点軸を鉛直に(角運動量の門用: 重力 ∥ 軸)。"""
    return np.array([[0.0, 0.0, top], [0.0, 0.0, bottom]])


_MOTIONS = {"fixed": _mo_fixed, "linear_accel": _mo_linear_accel, "swing": _mo_swing, "throw": _mo_throw,
            "vertical_axis": _mo_vertical_axis}


def _stick_fn(sticks, who):
    """棒の動きの指定 → t ↦ (2, 3)。名前(``"fixed"`` / ``"linear_accel"`` / ``"swing"`` / ``"throw"`` / ``"vertical_axis"``)、
    ``{"kind": 名前, 引数…}``、呼べる物 t ↦ (2, 3)、固定の (2, 3) を受ける。それ以外は ValueError。"""
    if isinstance(sticks, str):
        if sticks not in _MOTIONS:
            raise ValueError("%s: unknown stick motion %r (known: %s)" % (who, sticks, sorted(_MOTIONS)))
        fn = _MOTIONS[sticks]
    elif isinstance(sticks, dict):
        kind = sticks.get("kind")
        if kind not in _MOTIONS:
            raise ValueError("%s: unknown stick motion kind %r (known: %s)" % (who, kind, sorted(_MOTIONS)))
        kw = {k: v for k, v in sticks.items() if k != "kind"}
        allowed = set(inspect.signature(_MOTIONS[kind]).parameters) - {"t"}
        bad = sorted(set(kw) - allowed)
        if bad:
            raise ValueError("%s: stick motion %r has no parameter(s) %s (known: %s)" % (who, kind, bad, sorted(allowed)))
        base = _MOTIONS[kind]

        def fn(t, _b=base, _kw=kw):
            return _b(t, **_kw)
    elif callable(sticks):
        fn = sticks
    else:
        fixed = np.stack(_pair(sticks, who + ": sticks"))

        def fn(t, _f=fixed):
            return _f
    _pair(fn(0.0), who + ": stick motion at t = 0")
    return fn


def _exact_step(x, v, sticks0, sticks1, vsticks1, h: float, params: dict, gvec=None, topology: bool = True) -> dict:
    """伸びない糸・摩擦のない滑車の厳密模型を 1 ステップ(RATTLE)。拘束 = d_L + d_R ≤ l、力 = −T(û_L + û_R)。

    topology = True: 軸は糸の上に「乗っている」だけ → 棒を結ぶ面より上では拘束しない(糸は軸の下をくぐれず引き下ろせない。
    論文の FLYING の面の規則と同じ考え)。False = 糸が軸に通った数珠。位置: 半キック → ドリフト → 外に出たら旧い勾配の向きに戻す
    (SHAKE、λ を Newton)。速度: 接触中は相対法線速度を 0 に(棒の速度を使う)。張力 T(t_{n+1}) = 2 m μ / h。"""
    m, l = float(params["mass"]), float(params["string_length"])
    gv = np.array([0.0, 0.0, -float(params["g"])]) if gvec is None else gvec
    pl0, pr0 = sticks0
    pl1, pr1 = sticks1
    vl1, vr1 = vsticks1
    vh = v + 0.5 * h * gv
    xn = x + h * vh
    lam = 0.0
    taut = False
    if (np.linalg.norm(xn - pl1) + np.linalg.norm(xn - pr1) - l) > 0 and not (topology and _above_stick_plane(xn, pl1, pr1)):
        taut = True
        ul0 = (x - pl0) / np.linalg.norm(x - pl0)
        ur0 = (x - pr0) / np.linalg.norm(x - pr0)
        n0 = ul0 + ur0
        for _ in range(50):
            xt = xn - h * lam * n0
            dl, dr = xt - pl1, xt - pr1
            nl, nr = np.linalg.norm(dl), np.linalg.norm(dr)
            f = nl + nr - l
            df = -h * float((dl / nl + dr / nr) @ n0)
            step = f / df
            lam -= step
            if abs(step) < 1e-16 * max(1.0, abs(lam)) or abs(f) < 1e-15:
                break
        xn = xn - h * lam * n0
        vh = vh - lam * n0
    vn = vh + 0.5 * h * gv
    mu = 0.0
    if taut:
        ul = (xn - pl1) / np.linalg.norm(xn - pl1)
        ur = (xn - pr1) / np.linalg.norm(xn - pr1)
        n1 = ul + ur
        bdot = float(ul @ vl1 + ur @ vr1)
        mu = (float(n1 @ vn) - bdot) / float(n1 @ n1)
        vn = vn - mu * n1
    return {"x": xn, "v": vn, "taut": taut, "tension": 2 * m * mu / h}


def diabolo_simulate(x0, v0, sticks, t_end: float, dt: float, params: dict, *, model: str = "paper", omega0: float = 0.0,
                     mode0: str = "on_string", gvec=None, topology: bool = True, plane_rule: str = "paper",
                     rotation: str = "paper", flying_rule: str = "paper") -> dict:
    """棒の動き ``sticks`` のもとでディアボロを ``t_end`` まで刻み ``dt`` で進める。

    ``sticks`` = 名前(``"fixed"`` / ``"linear_accel"`` / ``"swing"`` / ``"throw"`` / ``"vertical_axis"``)、``{"kind": 名前, 引数…}``、
    呼べる物 t ↦ (2, 3)、固定の (2, 3)。``model`` = "paper"(論文の解析模型、:func:`diabolo_dynamics_step`)/ "exact"(伸びない糸の
    片側拘束を RATTLE で、張力つき。棒の速度は中心差分)。``topology`` は exact だけに効く(True = 棒を結ぶ面より上では糸が効かない)。

    返り ``{"t", "x", "v", "omega", "mode", "tension", "energy", "sticks"}``(energy は J、tension は exact のときだけ、paper は NaN)。
    **Raises** ``ValueError``: model の綴り、t_end < 0 / dt ≤ 0、刻みが多すぎる(> 2,000,000)、棒の動きの指定、params。"""
    who = "diabolo_simulate"
    if model not in ("paper", "exact"):
        raise ValueError("%s: model must be 'paper' or 'exact', got %r" % (who, model))
    _check_choice(who, plane_rule=plane_rule, rotation=rotation, flying_rule=flying_rule)
    _check_params(params, who)
    if mode0 not in DIABOLO_STATES:
        raise ValueError("%s: unknown mode0 %r" % (who, mode0))
    t_end, dt = float(t_end), float(dt)
    if not (math.isfinite(t_end) and t_end >= 0 and math.isfinite(dt) and dt > 0):
        raise ValueError("%s: need t_end >= 0 and dt > 0" % who)
    n = int(round(t_end / dt)) + 1
    if n > 2_000_000:
        raise ValueError("%s: %d steps is too many (t_end / dt)" % (who, n))
    fn = _stick_fn(sticks, who)
    T = np.arange(n) * dt
    X, V = np.empty((n, 3)), np.empty((n, 3))
    W, Ten = np.zeros(n), np.full(n, np.nan)
    Mode = []
    S = np.empty((n, 2, 3))
    m, g = float(params["mass"]), float(params["g"])
    st = {"x": _v3(x0, who + ": x0"), "v": _v3(v0, who + ": v0"), "omega": float(omega0), "mode": mode0}
    gz = np.array([0.0, 0.0, -g]) if gvec is None else _v3(gvec, who + ": gvec")
    eps = 1e-6
    cur = np.asarray(fn(T[0]), np.float64)
    for i in range(n):
        S[i] = cur
        X[i], V[i], W[i] = st["x"], st["v"], st["omega"]
        Mode.append(st["mode"])
        if i == n - 1:
            break
        nxt = np.asarray(fn(T[i + 1]), np.float64)
        if model == "paper":
            st = diabolo_dynamics_step(st, cur, nxt, dt, params, plane_rule=plane_rule, rotation=rotation, flying_rule=flying_rule)
        else:
            vs = (np.asarray(fn(T[i + 1] + eps), np.float64) - np.asarray(fn(T[i + 1] - eps), np.float64)) / (2 * eps)
            r = _exact_step(st["x"], st["v"], (cur[0], cur[1]), (nxt[0], nxt[1]), (vs[0], vs[1]), dt, params, gvec=gz,
                            topology=bool(topology))
            Ten[i + 1] = r["tension"]
            st = {"x": r["x"], "v": r["v"], "omega": st["omega"], "mode": "on_string" if r["taut"] else "off_string_loose"}
        cur = nxt
    E = 0.5 * m * np.sum(V * V, axis=1) - m * (X @ gz)
    return {"t": T, "x": X, "v": V, "omega": W, "mode": np.array(Mode), "tension": Ten, "energy": E, "sticks": S}


def diabolo_state_sequence(X, sticks, params: dict, *, flying_rule: str = "paper", mode0: str = "on_string") -> np.ndarray:
    """位置の列 X (N, 3) と棒 (N, 2, 3) から論文の状態遷移だけを回す(観測した軌跡の分類用、力学は解かない)。有限でない行は
    直前の状態を保つ(追跡が見失ったコマ)。返り (N,) の状態名。**Raises** ``ValueError``: 形・長さ・綴り。"""
    who = "diabolo_state_sequence"
    _check_choice(who, flying_rule=flying_rule)
    _check_params(params, who)
    if mode0 not in DIABOLO_STATES:
        raise ValueError("%s: unknown mode0 %r" % (who, mode0))
    Xa = np.asarray(X, np.float64)
    Sa = np.asarray(sticks, np.float64)
    if Xa.ndim != 2 or Xa.shape[1] != 3 or Sa.shape != (len(Xa), 2, 3):
        raise ValueError("%s: need X (N, 3) and sticks (N, 2, 3), got %s and %s" % (who, Xa.shape, Sa.shape))
    out, mode = [], mode0
    l = float(params["string_length"])
    for x, (pl, pr) in zip(Xa, Sa):
        if not np.all(np.isfinite(x)):
            out.append(mode)
            continue
        sph = diabolo_spheroid(pl, pr, l)
        s = spheroid_closest(x, sph)["s"]
        mode = _next_mode(mode, x, s, pl, pr, sph["c"], params, flying_rule)
        out.append(mode)
    return np.array(out)


# ----------------------------------------------------------------------------------------------------------------------
# 投げと受けの真値(閉形式の放物線)
def diabolo_throw_catch_truth(p0, v0, sticks, params: dict, *, t_min: float = 0.0, t_max: float = 5.0, n_grid: int = 2001) -> dict:
    """放した状態 (p0, v0) からの放物線(閉形式)が、頂点の後で、受けの棒 ``sticks``(固定の (2, 3))に対して「棒を結ぶ面より下
    かつ s < c_F」に入る最初の時刻(論文の FLYING → ON_STRING の条件 + 面の規則。張りつめは呼び手が確かめる)。

    頂点 t_apex = v_z/g、高さ v_z²/(2g) も返す。根は ``n_grid`` 点の格子で符号の変化を見つけ、二分法(80 回)で詰める。受けが
    無ければ t_catch = NaN。**Raises** ``ValueError``: 形、t_max ≤ t_min、n_grid < 3。"""
    who = "diabolo_throw_catch_truth"
    p0, v0 = _v3(p0, who + ": p0"), _v3(v0, who + ": v0")
    _check_params(params, who)
    pl, pr = _pair(sticks, who + ": sticks")
    if not (t_max > t_min) or int(n_grid) < 3:
        raise ValueError("%s: need t_max > t_min and n_grid >= 3" % who)
    g = float(params["g"])
    sph = diabolo_spheroid(pl, pr, float(params["string_length"]))
    cf = float(params["c_f"])
    nup = np.cross([1.0, 0.0, 0.0], pl - pr)
    nup /= np.linalg.norm(nup)
    mid = 0.5 * (pl + pr)

    def pos(t):
        return p0 + v0 * t + 0.5 * np.array([0.0, 0.0, -g]) * t * t

    def f(t):                    # 受け = 「棒の面より下」かつ「s < c_F」。両方を満たすと負になる指標(max)
        x = pos(t)
        return max(spheroid_closest(x, sph)["s"] - cf, float((x - mid) @ nup))

    vz = max(float(v0[2]), 0.0)
    t_apex = vz / g
    out = {"t_apex": t_apex, "apex_height": vz * vz / (2 * g), "apex_z": float(p0[2]) + vz * vz / (2 * g)}
    ts = np.linspace(max(t_min, t_apex), t_max, int(n_grid))
    prev = f(ts[0])
    idx = None
    for k in range(1, len(ts)):
        cur = f(ts[k])
        if prev >= 0 > cur:
            idx = k
            break
        prev = cur
    if idx is None:
        out.update(t_catch=float("nan"), p_catch=np.full(3, np.nan))
        return out
    lo, hi = ts[idx - 1], ts[idx]
    for _ in range(80):
        m_ = 0.5 * (lo + hi)
        if f(m_) >= 0:
            lo = m_
        else:
            hi = m_
    out.update(t_catch=0.5 * (lo + hi), p_catch=pos(0.5 * (lo + hi)))
    return out


# ----------------------------------------------------------------------------------------------------------------------
# 糸の垂れと張力(閉形式)
def string_tension_static(stick_gap: float, params: dict) -> dict:
    """棒が同じ高さ・間隔 2c で止まり、ディアボロが最下点で静止: 垂れ b = √(a² − c²)、張力 T = m g a / (2b)、糸の水平からの角
    atan2(b, c)。**Raises** ``ValueError``: 間隔が (0, 糸) の外。"""
    _check_params(params, "string_tension_static")
    l, m, g = float(params["string_length"]), float(params["mass"]), float(params["g"])
    a, c = l / 2.0, float(stick_gap) / 2.0
    if not (math.isfinite(c) and 0 < c < a):
        raise ValueError("string_tension_static: need 0 < stick_gap < string length (%g), got %r" % (l, stick_gap))
    b = math.sqrt(a * a - c * c)
    return {"sag": b, "tension": m * g * a / (2 * b), "angle_deg": math.degrees(math.atan2(b, c))}


def string_tension_from_sag(p_left, p_right, p_diabolo, mass: float, *, accel=None, g: float = G) -> dict:
    """糸の V 字(棒の先 2 点と軸の位置)から張力を出す(摩擦のない滑車 = 両側の張力が等しい)。

    T (û_L + û_R) = m (a − g⃗) の最小二乗: T = m (a − g⃗)·n / |n|²、n = û_L + û_R(û は軸 → 棒の単位ベクトル)。静止(accel = None)
    なら T = m g / (sin α_L + sin α_R)(α = 糸の水平からの角)と同じ。残差(釣り合いの破れ)も返す —— 大きければ「加速度の入れ忘れ /
    摩擦 / 弾性」の警報。**Raises** ``ValueError``: 形、質量 ≤ 0、軸が棒と重なる。"""
    who = "string_tension_from_sag"
    pl, pr, pd = _v3(p_left, who + ": p_left"), _v3(p_right, who + ": p_right"), _v3(p_diabolo, who + ": p_diabolo")
    mass = float(mass)
    if not (math.isfinite(mass) and mass > 0):
        raise ValueError("%s: mass must be finite and > 0" % who)
    if min(np.linalg.norm(pl - pd), np.linalg.norm(pr - pd)) < 1e-9:
        raise ValueError("%s: the diabolo coincides with a stick tip" % who)
    ul = (pl - pd) / np.linalg.norm(pl - pd)
    ur = (pr - pd) / np.linalg.norm(pr - pd)
    n = ul + ur
    if float(n @ n) < 1e-18:
        raise ValueError("%s: the two string halves are opposite (no vertical support)" % who)
    a = np.zeros(3) if accel is None else _v3(accel, who + ": accel")
    need = mass * (a - np.array([0.0, 0.0, -float(g)]))          # 糸が与える力
    T = float(need @ n) / float(n @ n)
    resid = float(np.linalg.norm(need - T * n))
    al = math.degrees(math.atan2(ul[2], math.hypot(ul[0], ul[1])))
    ar = math.degrees(math.atan2(ur[2], math.hypot(ur[0], ur[1])))
    return {"tension": T, "residual_N": resid, "angle_left_deg": al, "angle_right_deg": ar}


# ----------------------------------------------------------------------------------------------------------------------
# カメラと光線追跡
def diabolo_camera(*, position=(1.4, 0.0, 0.75), look_at=(0.0, 0.0, 0.75), shape=(480, 640), fovy_deg: float = 30.0) -> dict:
    """透視カメラ(既定 = 前 1.4 m から −x を見る、世界の z が上)。返り ``{"C", "R"(行 = 右・下・前), "K", "shape", "look_at"}``。
    **Raises** ``ValueError``: 位置と注視点が重なる、視線が鉛直、画の大きさや画角が不正。"""
    C = _v3(position, "diabolo_camera: position")
    La = _v3(look_at, "diabolo_camera: look_at")
    f = La - C
    if np.linalg.norm(f) < 1e-9:
        raise ValueError("diabolo_camera: position and look_at coincide")
    f /= np.linalg.norm(f)
    up = np.array([0.0, 0.0, 1.0])
    r = np.cross(f, up)
    if np.linalg.norm(r) < 1e-9:
        raise ValueError("diabolo_camera: the line of sight is vertical (up vector undefined)")
    r /= np.linalg.norm(r)
    d = np.cross(f, r)
    try:
        H, W = (int(v) for v in shape)
    except (TypeError, ValueError) as exc:
        raise ValueError("diabolo_camera: shape must be (rows, cols)") from exc
    if H < 16 or W < 16 or not (0 < float(fovy_deg) < 170):
        raise ValueError("diabolo_camera: need shape >= 16 px and 0 < fovy_deg < 170")
    fy = 0.5 * H / math.tan(math.radians(fovy_deg) / 2)
    K = np.array([[fy, 0, (W - 1) / 2.0], [0, fy, (H - 1) / 2.0], [0, 0, 1.0]])
    return {"C": C, "R": np.stack([r, d, f]), "K": K, "shape": (H, W), "look_at": La}


def _check_cam(cam, who):
    if not isinstance(cam, dict) or not {"C", "R", "K", "shape"} <= set(cam):
        raise ValueError("%s: cam must be the dict from diabolo_camera" % who)
    return cam


def _project(cam: dict, P) -> np.ndarray:
    """世界の点 (N, 3) → 画素 (N, 2) = (col, row)。"""
    P = np.atleast_2d(np.asarray(P, np.float64))
    Q = (P - cam["C"]) @ cam["R"].T
    K = cam["K"]
    return np.stack([K[0, 0] * Q[:, 0] / Q[:, 2] + K[0, 2], K[1, 1] * Q[:, 1] / Q[:, 2] + K[1, 2]], axis=1)


def _rays(cam, cols, rows):
    K = cam["K"]
    x = (cols - K[0, 2]) / K[0, 0]
    y = (rows - K[1, 2]) / K[1, 1]
    d = np.stack([x, y, np.ones_like(x)], axis=-1) @ cam["R"]          # 世界系
    return d / np.linalg.norm(d, axis=-1, keepdims=True)


def _body_frame(axis):
    """軸 a → 体の系 (e1, e2, a)。e1 = 世界の z を a に直交な面へ落とした向き(a が鉛直なら世界 x)。位相 ψ はここから測る。"""
    a = np.asarray(axis, np.float64)
    a = a / np.linalg.norm(a)
    z = np.array([0.0, 0.0, 1.0])
    e1 = z - (z @ a) * a
    if np.linalg.norm(e1) < 1e-9:
        e1 = np.array([1.0, 0.0, 0.0]) - a[0] * a
    e1 /= np.linalg.norm(e1)
    return e1, np.cross(a, e1), a


def _angle_deg(u, v) -> float:
    """2 本のベクトルの角 [deg] を atan2(|u×v|, u·v) で(acos の 1 付近の丸めの床を避ける)。"""
    u, v = np.asarray(u, np.float64), np.asarray(v, np.float64)
    return math.degrees(math.atan2(np.linalg.norm(np.cross(u, v)), float(u @ v)))


def _cup_geom(p):
    R, L2, rh, zh = p["diameter"] / 2, p["length"] / 2, p["hub_radius"], p["hub_z"]
    k = (R - rh) / (L2 - zh)
    z0 = zh - rh / k
    zm = zh + p["marker_radius_frac"] * (L2 - zh)
    return R, L2, rh, zh, k, z0, zm, rh + k * (zm - zh)


def _trace(o, d, p):
    """体の系での光線 o + t d((N, 3))→ 当たりの距離・種別(1 外面 2 内面 3 底板 4 軸)・点・法線。"""
    R, L2, rh, zh, k, z0, zm, rm = _cup_geom(p)
    N = len(o)
    tbest = np.full(N, np.inf)
    kind = np.zeros(N, np.int8)
    pt = np.zeros((N, 3))
    nrm = np.zeros((N, 3))
    for sgn in (1.0, -1.0):                  # 手前 (+) と奥 (−) のカップ(円錐殻)
        zz0 = sgn * z0
        A = d[:, 0] ** 2 + d[:, 1] ** 2 - k * k * d[:, 2] ** 2
        B = 2 * (o[:, 0] * d[:, 0] + o[:, 1] * d[:, 1] - k * k * (o[:, 2] - zz0) * d[:, 2])
        Cc = o[:, 0] ** 2 + o[:, 1] ** 2 - k * k * (o[:, 2] - zz0) ** 2
        disc = B * B - 4 * A * Cc
        ok = disc >= 0
        sq = np.sqrt(np.where(ok, disc, 0))
        with np.errstate(divide="ignore", invalid="ignore"):
            for t in ((-B - sq) / (2 * A), (-B + sq) / (2 * A)):
                hit = ok & (t > 1e-9) & (t < tbest)
                z = o[:, 2] + t * d[:, 2]
                hit &= (sgn * z >= zh) & (sgn * z <= L2)
                if hit.any():
                    P = o[hit] + t[hit, None] * d[hit]
                    n = np.stack([P[:, 0], P[:, 1], -k * k * (P[:, 2] - zz0)], 1)
                    n /= np.linalg.norm(n, axis=1, keepdims=True)
                    inner = np.sum(n * d[hit], 1) > 0
                    tbest[hit] = t[hit]
                    pt[hit] = P
                    nrm[hit] = np.where(inner[:, None], -n, n)
                    kind[hit] = np.where(inner, 2, 1)
        with np.errstate(divide="ignore", invalid="ignore"):
            t = (sgn * zh - o[:, 2]) / d[:, 2]
        P = o + t[:, None] * d
        hit = (t > 1e-9) & (t < tbest) & (P[:, 0] ** 2 + P[:, 1] ** 2 <= rh * rh)
        tbest[hit] = t[hit]
        pt[hit] = P[hit]
        nrm[hit] = np.array([0, 0, 1.0]) * np.sign(-d[hit, 2:3])
        kind[hit] = 3
    ra = p["axle_radius"]
    A = d[:, 0] ** 2 + d[:, 1] ** 2
    B = 2 * (o[:, 0] * d[:, 0] + o[:, 1] * d[:, 1])
    Cc = o[:, 0] ** 2 + o[:, 1] ** 2 - ra * ra
    disc = B * B - 4 * A * Cc
    with np.errstate(divide="ignore", invalid="ignore"):
        t = (-B - np.sqrt(np.where(disc >= 0, disc, 0))) / (2 * A)
    z = o[:, 2] + t * d[:, 2]
    hit = (disc >= 0) & (t > 1e-9) & (t < tbest) & (np.abs(z) <= zh)
    if hit.any():
        P = o[hit] + t[hit, None] * d[hit]
        tbest[hit] = t[hit]
        pt[hit] = P
        n = np.stack([P[:, 0], P[:, 1], np.zeros(int(hit.sum()))], 1)
        nrm[hit] = n / np.linalg.norm(n, axis=1, keepdims=True)
        kind[hit] = 4
    return tbest, kind, pt, nrm


def diabolo_render(cam: dict, params: dict, *, center=None, axis=None, phase: float = 0.0, omega: float = 0.0,
                   exposure: float = 0.0, n_sub: int = 8, sticks=None, ss: int = 4, noise: float = 0.0,
                   blur_sigma: float = 0.0, seed: int = 0, background=None) -> np.ndarray:
    """ディアボロの 1 コマを光線追跡で描く(RGB float (H, W, 3)、[0, 1])。

    形 = 2 つのカップ(円錐殻、外面 赤・内面 黄)+ 底の板(暗い灰)+ 軸。マーカーは手前のカップの内面に ``n_slots`` か所(反射 = 白、
    ダミー = 灰)。``center`` の既定はカメラの注視点、``axis`` の既定はカメラへ向く向き。``phase`` = 体の系 e1 から測った回転角、
    ``omega`` [rad/s] と ``exposure`` [s] でマーカーの回転ぶれ(露光の中心 = コマの時刻、``n_sub`` 点で平均)。``sticks`` = (2, 3) を
    渡すと棒と糸(軸へ伸びる 2 本)と棒の先の青い印も描く。``ss`` × ``ss`` の超標本化はディアボロの外接矩形だけ(縁の被覆率が
    正しく出る)。``noise`` = 画素ごとのガウス雑音の σ(``seed`` で再現)、``blur_sigma`` = 光学ぼけ [px]。

    **Raises** ``ValueError``: cam / params の形、軸がゼロ、ss / n_sub < 1、負の雑音・ぼけ・露光。"""
    who = "diabolo_render"
    _check_cam(cam, who)
    if not isinstance(params, dict) or "diameter" not in params or "n_slots" not in params:
        raise ValueError("%s: params must be the dict from diabolo_params" % who)
    if int(ss) < 1 or int(n_sub) < 1 or noise < 0 or blur_sigma < 0 or exposure < 0:
        raise ValueError("%s: need ss >= 1, n_sub >= 1 and non-negative noise / blur_sigma / exposure" % who)
    H, W = cam["shape"]
    center = _v3(cam.get("look_at", cam["C"] + cam["R"][2]) if center is None else center, who + ": center")
    axis = (-cam["R"][2]) if axis is None else _v3(axis, who + ": axis")
    if np.linalg.norm(axis) < 1e-12:
        raise ValueError("%s: axis is zero" % who)
    rows, cols = np.mgrid[0:H, 0:W].astype(np.float64)
    img = np.empty((H, W, 3))
    if background is None:
        gr = 0.50 + 0.12 * (rows / H)
        img[:] = gr[..., None] * np.array([0.92, 0.95, 1.0])
    else:
        img[:] = background
    e1, e2, a = _body_frame(axis)
    if sticks is not None:
        pl, pr = _pair(sticks, who + ": sticks")
        segs = []
        for tip, side in ((pl, 1.0), (pr, -1.0)):
            segs.append((tip, center, _C_STRING, 0.9))
            segs.append((tip, tip + np.array([0.25, side * 0.08, -0.35]), _C_STICK, 3.0))
        for P0, P1, col, half in segs:
            u0, u1 = _project(cam, np.stack([P0, P1]))
            dd = u1 - u0
            tt = np.clip(((cols - u0[0]) * dd[0] + (rows - u0[1]) * dd[1]) / max(float(dd @ dd), 1e-12), 0, 1)
            dist = np.hypot(cols - (u0[0] + tt * dd[0]), rows - (u0[1] + tt * dd[1]))
            cov = np.clip(half + 0.5 - dist, 0, 1)
            img = img * (1 - cov[..., None]) + col * cov[..., None]
        for tip in (pl, pr):
            u = _project(cam, tip[None])[0]
            cov = np.clip(4.5 - np.hypot(cols - u[0], rows - u[1]), 0, 1)
            img = img * (1 - cov[..., None]) + _C_TIP * cov[..., None]
    R = params["diameter"] / 2
    L2 = params["length"] / 2
    corners = np.array([center + sa * L2 * a + R * (sb * e1 + sc * e2) for sa in (-1, 1) for sb in (-1, 1) for sc in (-1, 1)])
    uv = _project(cam, corners)
    c0, r0 = np.floor(uv.min(0)).astype(int) - 2
    c1, r1 = np.ceil(uv.max(0)).astype(int) + 2
    c0, r0, c1, r1 = max(c0, 0), max(r0, 0), min(c1, W - 1), min(r1, H - 1)
    if c1 > c0 and r1 > r0:
        ssi = int(ss)
        off = (np.arange(ssi) + 0.5) / ssi - 0.5
        cc, rr = np.meshgrid(np.arange(c0, c1 + 1), np.arange(r0, r1 + 1))
        shp = cc.shape + (ssi, ssi)
        sc = np.broadcast_to(cc[..., None, None] + off[None, None, None, :], shp).reshape(-1)
        sr = np.broadcast_to(rr[..., None, None] + off[None, None, :, None], shp).reshape(-1)
        dw = _rays(cam, sc, sr)
        Rb = np.stack([e1, e2, a])                                         # 世界 → 体
        o = np.repeat(((cam["C"] - center) @ Rb.T)[None], len(dw), 0)
        db = dw @ Rb.T
        _, kind, P, n = _trace(o, db, params)
        hit = kind > 0
        Lb = (_LIGHT / np.linalg.norm(_LIGHT)) @ Rb.T
        shade = 0.35 + 0.65 * np.clip(n @ Lb, 0, None)
        col = np.zeros((len(dw), 3))
        col[kind == 1] = _C_OUT
        col[kind == 2] = _C_IN
        col[kind == 3] = _C_HUB
        col[kind == 4] = _C_AXLE
        col_sh = col * shade[:, None]
        Rc, L2c, rh, zh, k, z0, zm, rm = _cup_geom(params)
        inner_near = (kind == 2) & (P[:, 2] > 0)
        if inner_near.any():                     # マーカー(手前のカップの内面、位相ごとに平均 = 回転ぶれ)
            Pi = P[inner_near]
            phi = np.arctan2(Pi[:, 1], Pi[:, 0])
            slant = math.sqrt(1 + k * k)
            taus = (np.linspace(-0.5, 0.5, int(n_sub)) * exposure) if exposure > 0 else np.zeros(1)
            acc_bright = np.zeros(len(Pi))
            acc_dummy = np.zeros(len(Pi))
            nsl = int(params["n_slots"])
            bright = set(int(b) for b in params["bright_slots"])
            rmk = params["marker_size"] / 2
            rad = np.hypot(Pi[:, 0], Pi[:, 1])
            dz = (Pi[:, 2] - zm) * slant
            for tau in taus:
                ps = phase + omega * tau
                for j in range(nsl):
                    dphi = np.angle(np.exp(1j * (phi - (ps + 2 * np.pi * j / nsl))))
                    inside = np.hypot(dphi * rad, dz) <= rmk
                    if j in bright:
                        acc_bright += inside
                    else:
                        acc_dummy += inside
            fb = acc_bright / len(taus)
            fd = acc_dummy / len(taus)
            base = col[inner_near] * shade[inner_near, None]
            col_sh[inner_near] = (base * (1 - fb - fd)[:, None] + _C_MARK * 0.97 * fb[:, None]
                                  + (_C_DUMMY * shade[inner_near, None]) * fd[:, None])
        bgs = img[np.clip(sr.round().astype(int), 0, H - 1), np.clip(sc.round().astype(int), 0, W - 1)]
        out = np.where(hit[:, None], col_sh, bgs)
        hh, ww = rr.shape
        img[r0:r1 + 1, c0:c1 + 1] = out.reshape(hh, ww, ssi, ssi, 3).mean(axis=(2, 3))
    if blur_sigma > 0:
        img = ndimage.gaussian_filter(img, (blur_sigma, blur_sigma, 0))
    if noise > 0:
        img = img + np.random.default_rng(int(seed)).normal(0, noise, img.shape)
    return np.clip(img, 0, 1)


# ----------------------------------------------------------------------------------------------------------------------
# 軸の推定(縁の円 + 底の板の円の透視モーメント)
def _poly_moments(uv):
    x, y = uv[:, 0], uv[:, 1]
    xn, yn = np.roll(x, -1), np.roll(y, -1)
    cr = x * yn - xn * y
    A = cr.sum() / 2
    cx = ((x + xn) * cr).sum() / (6 * A)
    cy = ((y + yn) * cr).sum() / (6 * A)
    sxx = ((x * x + x * xn + xn * xn) * cr).sum() / (12 * A) - cx * cx
    syy = ((y * y + y * yn + yn * yn) * cr).sum() / (12 * A) - cy * cy
    sxy = ((x * yn + 2 * x * y + 2 * xn * yn + xn * y) * cr).sum() / (24 * A) - cx * cy
    return abs(A), cx, cy, sxx, sxy, syy


def _circle_uv(cam, C, a, r, n=720):
    e1, e2, _ = _body_frame(a)
    ph = np.linspace(0, 2 * np.pi, n, endpoint=False)
    P = C[None] + r * (np.cos(ph)[:, None] * e1 + np.sin(ph)[:, None] * e2)
    return _project(cam, P)


def _mask_moments(m, cols, rows):
    A = m.sum()
    cx, cy = (m * cols).sum() / A, (m * rows).sum() / A
    return A, cx, cy, (m * (cols - cx) ** 2).sum() / A, (m * (cols - cx) * (rows - cy)).sum() / A, (m * (rows - cy) ** 2).sum() / A


def _nblur(val, w, sigma):
    num = ndimage.gaussian_filter(val * w, sigma)
    den = ndimage.gaussian_filter(w.astype(np.float64), sigma)
    return num / np.maximum(den, 1e-9), den


def _segment_cup(img) -> dict:
    """色の規則で手前のカップの内側(縁の円の中)と底の板を分ける(柔らかいマスク 0〜1)。

    核: 黄の度合い (G − B)/(R + G + B) が内面の値の半分を超える最大の連結成分、穴(底の板・マーカー)は塗りつぶす。縁の画素の
    被覆率 α は G − B の**線形な混合**で解く: α = (GB − GB_外)/(GB_内 − GB_外)、GB_内・GB_外 は縁の内・外の近傍(正規化ぼかし、
    σ 3 px)の局所値(陰影で内面の明るさが場所ごとに違う分を吸収)。色度の比で混ぜると縁が系統的に偏る(試作の 1 回目で 0.37°)。
    底の板 = 暗い穴のうち面積最大(「中心に最も近い穴」だと傾いた時に灰のダミーマーカーを拾った)。"""
    im = np.asarray(img, np.float64)
    S = im.sum(-1) + 1e-6
    GB = im[..., 1] - im[..., 2]
    y_in = (_C_IN[1] - _C_IN[2]) / _C_IN.sum()
    yv = np.clip(GB / S / y_in, 0, 1)
    b = yv > 0.5
    lab, n = ndimage.label(b)
    if n == 0:
        raise ValueError("diabolo_axis_from_image: no cup interior found (is the near cup facing the camera?)")
    sizes = ndimage.sum(b, lab, range(1, n + 1))
    keep = lab == (1 + int(np.argmax(sizes)))
    filled = ndimage.binary_fill_holes(keep)
    holes = filled & ~keep
    holes_d = ndimage.binary_dilation(holes, iterations=2)
    core_in = ndimage.binary_erosion(filled, iterations=2) & ~holes_d
    if not core_in.any():
        raise ValueError("diabolo_axis_from_image: the cup interior is too small to segment")
    ref_in, _ = _nblur(GB, core_in, 3.0)
    ring = ndimage.binary_dilation(filled, iterations=5) & ~ndimage.binary_dilation(filled, iterations=2)
    ref_out, _ = _nblur(GB, ring, 3.0)
    band = ndimage.binary_dilation(filled, iterations=2) & ~ndimage.binary_erosion(filled, iterations=2)
    alpha = np.clip((GB - ref_out) / np.maximum(ref_in - ref_out, 1e-3), 0, 1)
    m = np.where(band, alpha, 0.0)
    m[ndimage.binary_erosion(filled, iterations=2)] = 1.0
    bright = S / 3 > 0.75
    dark_holes = holes & ~bright
    lab2, n2 = ndimage.label(dark_holes)
    if n2 == 0:
        raise ValueError("diabolo_axis_from_image: the hub plate is not visible")
    sizes2 = ndimage.sum(dark_holes, lab2, range(1, n2 + 1))
    hub_core = lab2 == (1 + int(np.argmax(sizes2)))
    hub_in = ndimage.binary_erosion(hub_core, iterations=1)
    href = float(GB[hub_in].mean()) if hub_in.any() else float(GB[hub_core].mean())
    hband = ndimage.binary_dilation(hub_core, iterations=2) & ~hub_in
    ah = np.clip((ref_in - GB) / np.maximum(ref_in - href, 1e-3), 0, 1)
    hm = np.where(hband, ah, 0.0)
    hm[hub_in] = 1.0
    return {"interior": m, "hub": hm, "bright": bright & filled, "filled": filled}


def _axis_from(ab, a0):
    e1, e2, a = _body_frame(a0)
    v = a + ab[0] * e1 + ab[1] * e2
    return v / np.linalg.norm(v)


def _check_rgb(img, who):
    try:
        im = np.asarray(img, np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError("%s: img must be an (H, W, 3) RGB array" % who) from exc
    if im.ndim != 3 or im.shape[2] != 3 or not np.all(np.isfinite(im)):
        raise ValueError("%s: img must be a finite (H, W, 3) RGB array, got shape %s" % (who, im.shape))
    if im.max() > 1.5:
        im = im / 255.0
    return im


def diabolo_axis_from_image(img, cam: dict, params: dict, *, refine: bool = True, iters: int = 15) -> dict:
    """1 コマから手前のカップの縁の中心 ``center_rim`` と軸 ``axis``(カメラ側を向く)を出す。ディアボロの中心 ``center`` =
    center_rim − (L/2) axis。学習なし。

    初期値(弱透視): 縁の楕円の長半径 → 深度、短 / 長 = cos θ、底の板の中心のずれ = (L/2 − z_h) sin θ、θ = atan2(sin, cos)
    (acos の床を避ける)、ずれの向き = 軸の像の向き。仕上げ: 縁の円(半径 R、中心 C)と底の板(半径 r_h、中心 C − (L/2 − z_h) a)の
    厳密な透視投影の多角形モーメント(面積・重心・2 次)を、マスクのモーメントに Gauss–Newton で合わせる(5 自由度、8 残差)。
    残差 ``residual_px`` が 0.15 px を超えたら ``ok = False``(底の板が壁に隠れた等。視線から 45° で 2.8 px、38° まで ≤ 0.02 px)。

    返り ``{"center", "center_rim", "axis", "axis_init", "tilt_init_deg", "a_px", "b_px", "residual_px", "ok", "seg"}``。
    **Raises** ``ValueError``: 画像の形、カップの内側か底の板が見えない(推定不能)。"""
    who = "diabolo_axis_from_image"
    im = _check_rgb(img, who)
    _check_cam(cam, who)
    if not isinstance(params, dict) or "diameter" not in params:
        raise ValueError("%s: params must be the dict from diabolo_params" % who)
    if im.shape[:2] != tuple(cam["shape"]):
        raise ValueError("%s: image %s does not match the camera %s" % (who, im.shape[:2], tuple(cam["shape"])))
    seg = _segment_cup(im)
    H, W = cam["shape"]
    rows, cols = np.mgrid[0:H, 0:W].astype(np.float64)
    A, cx, cy, sxx, sxy, syy = _mask_moments(seg["interior"], cols, rows)
    Ah, hx, hy, *_ = _mask_moments(seg["hub"], cols, rows)
    ev, _ = np.linalg.eigh(np.array([[sxx, sxy], [sxy, syy]]))
    a_px, b_px = 2 * math.sqrt(max(ev[1], 1e-12)), 2 * math.sqrt(max(ev[0], 0))
    R = params["diameter"] / 2
    h = params["length"] / 2 - params["hub_z"]
    f = cam["K"][0, 0]
    depth = f * R / a_px
    s_px = a_px / R
    dx, dy = cx - hx, cy - hy                       # 底 → 縁(像の上で軸の向き)
    sin_t = min(math.hypot(dx, dy) / (h * s_px), 1.0)
    cos_t = min(b_px / a_px, 1.0)
    th = math.atan2(sin_t, cos_t)
    ray = _rays(cam, np.array([cx]), np.array([cy]))[0]
    C = cam["C"] + ray * depth / float(ray @ cam["R"][2])
    dimg = np.array([dx, dy]) / math.hypot(dx, dy) if math.hypot(dx, dy) > 1e-9 else np.array([1.0, 0.0])
    toward = -cam["R"][2]
    a0 = math.cos(th) * toward + math.sin(th) * (dimg[0] * cam["R"][0] + dimg[1] * cam["R"][1])
    a0 /= np.linalg.norm(a0)
    meas = np.array([math.sqrt(A), cx, cy, math.sqrt(sxx), sxy / math.sqrt(math.sqrt(sxx * syy) + 1e-12), math.sqrt(syy), hx, hy])
    out = {"center_rim": C, "axis": a0, "axis_init": a0.copy(), "tilt_init_deg": math.degrees(th), "a_px": a_px,
           "b_px": b_px, "hub_px": (hx, hy), "rim_px": (cx, cy), "seg": seg}
    if not refine:
        out.update(center=C - params["length"] / 2 * a0, residual_px=float("nan"), ok=True)
        return out

    def predict(q):
        Cq, aq = q[:3], _axis_from(q[3:5], a0)
        Ar, ux, uy, qxx, qxy, qyy = _poly_moments(_circle_uv(cam, Cq, aq, R))
        _, hxp, hyp, *_ = _poly_moments(_circle_uv(cam, Cq - h * aq, aq, params["hub_radius"]))
        return np.array([math.sqrt(Ar), ux, uy, math.sqrt(qxx), qxy / math.sqrt(math.sqrt(qxx * qyy) + 1e-12), math.sqrt(qyy),
                         hxp, hyp])

    q = np.concatenate([C, [0.0, 0.0]])
    for _ in range(int(iters)):
        r = predict(q) - meas
        J = np.empty((8, 5))
        for j in range(5):
            dq = np.zeros(5)
            dq[j] = 1e-6
            J[:, j] = (predict(q + dq) - predict(q - dq)) / 2e-6
        step = np.linalg.lstsq(J, -r, rcond=None)[0]
        q = q + step
        if np.linalg.norm(step) < 1e-12:
            break
    ah = _axis_from(q[3:5], a0)
    res = float(np.sqrt(np.mean((predict(q) - meas) ** 2)))
    out.update(center_rim=q[:3], axis=ah, center=q[:3] - params["length"] / 2 * ah, residual_px=res,
               ok=bool(res <= _RESIDUAL_ALARM_PX))
    return out


# ----------------------------------------------------------------------------------------------------------------------
# 回転(マーカーの位相 + ぶれの弧)
def _marker_profile(im, cam, params, pose, nbins: int = 720) -> np.ndarray:
    """推定した姿勢で、マーカーの画素をマーカーの円の面(軸に直交、z_m)へ戻し、体の系 e1 からの方位角の重みつき度数を返す。
    重み = 白さ B − (B/G)_内面 · G(内面の黄では 0、白いマーカーでは被覆率に線形 —— 明るさの閾値だと回転ぶれで弧が薄まると消え、
    試作の 1 回目は 30 rev/s 以上で 0 を返した)。"""
    k_in = _C_IN[2] / _C_IN[1]
    hub = ndimage.binary_dilation(pose["seg"]["hub"] > 0.5, iterations=2)
    wgt = np.clip(im[..., 2] - k_in * im[..., 1], 0, None) * (pose["seg"]["filled"] & ~hub)
    rr, cc = np.nonzero(wgt > 0)
    if len(rr) == 0:
        return np.zeros(nbins)
    w = wgt[rr, cc]
    d = _rays(cam, cc.astype(float), rr.astype(float))
    a = np.asarray(pose["axis"], np.float64)
    zm = _cup_geom(params)[6]
    Cm = np.asarray(pose["center"], np.float64) + zm * a
    t = ((Cm - cam["C"]) @ a) / (d @ a)
    P = cam["C"] + t[:, None] * d - Cm
    e1, e2, _ = _body_frame(a)
    phi = np.mod(np.arctan2(P @ e2, P @ e1), 2 * np.pi)
    hist, _ = np.histogram(phi, bins=nbins, range=(0, 2 * np.pi), weights=w)
    return hist


def _template(params, nbins, width_rad, rm):
    ang = np.arange(nbins) * 2 * np.pi / nbins
    t = np.zeros(nbins)
    half = params["marker_size"] / 2 / rm
    bright = set(int(b) for b in params["bright_slots"])
    for j in range(int(params["n_slots"])):
        c = 2 * np.pi * j / params["n_slots"]
        dphi = np.abs(np.angle(np.exp(1j * (ang - c))))
        prof = (dphi <= half + width_rad / 2) / (2 * half + width_rad)   # 弧の幅 = マーカー幅 + ぶれ、面積は一定
        t += prof * (1.0 if j in bright else _DUMMY_WEIGHT)
    return t


def diabolo_marker_phase(img, cam: dict, params: dict, pose: dict, *, nbins: int = 720, widths=None) -> dict:
    """1 コマのマーカーから回転の位相 ψ(体の系 e1 から、右ねじ)と回転ぶれの弧の幅 |ω|·露光 [rad] を読む。

    ``pose`` は :func:`diabolo_axis_from_image` の返り(軸・中心・分割)。マーカーの画素を推定した姿勢でマーカーの円の面へ戻し、
    方位角の度数(白さで重みづけ)を作る → 弧の幅ごとの型紙(反射 3 か所 + 灰のダミー 5 か所、非対称なので向きが一意)と円周
    相互相関(FFT)で最大を取り、位相は放物線で副標本。返り ``{"phase", "smear", "score", "profile"}``。
    **Raises** ``ValueError``: 画像の形、pose が軸の推定の返りでない、nbins < 16、マーカーが写っていない。"""
    who = "diabolo_marker_phase"
    im = _check_rgb(img, who)
    _check_cam(cam, who)
    if not isinstance(pose, dict) or not {"axis", "center", "seg"} <= set(pose):
        raise ValueError("%s: pose must be the dict from diabolo_axis_from_image" % who)
    if int(nbins) < 16:
        raise ValueError("%s: nbins must be >= 16" % who)
    hist = _marker_profile(im, cam, params, pose, int(nbins))
    if not np.any(hist > 0):
        raise ValueError("%s: no marker pixels found" % who)
    nb = len(hist)
    rm = _cup_geom(params)[7]
    widths = np.linspace(0, 2.0, 101) if widths is None else np.asarray(widths, np.float64)
    Hf = np.fft.rfft(hist - hist.mean())
    best = None
    for wdt in widths:
        t = _template(params, nb, float(wdt), rm)
        t = t - t.mean()
        nt = np.linalg.norm(t)
        if nt == 0:
            continue
        cc = np.fft.irfft(Hf * np.conj(np.fft.rfft(t)), nb) / nt
        k = int(np.argmax(cc))
        if best is None or cc[k] > best[0]:
            best = (float(cc[k]), k, float(wdt), cc)
    if best is None:
        raise ValueError("%s: no usable template width" % who)
    score, k, wdt, cc = best
    y0, y1, y2 = cc[(k - 1) % nb], cc[k], cc[(k + 1) % nb]
    den = y0 - 2 * y1 + y2
    frac = 0.5 * (y0 - y2) / den if den != 0 else 0.0
    return {"phase": float(np.mod((k + frac) * 2 * np.pi / nb, 2 * np.pi)), "smear": wdt, "score": score, "profile": hist}


def diabolo_spin_from_markers(phases, smears, dt: float, exposure: float, *, use_smear: bool = True) -> dict:
    """コマごとの位相 ψ_k(mod 2π)とぶれの弧の幅 → 回転の速さ ω、単位 rad/s(軸のまわり、右ねじ)。

    隣のコマの差を (−π, π] に包むと |ω| dt < π までしか読めない(ナイキストで折り返す、車輪の錯視)。``use_smear`` なら
    弧の幅 / 露光 = |ω| の粗い値で 2π k の枝を選ぶ(折り返さない粗い値 × 折り返す精しい値)。枝の間隔 2π/dt に対して弧の幅の
    誤差が半分より小さいことを前提にする。返り ``{"omega", "omega_wrapped", "omega_smear", "branch"}``。
    **Raises** ``ValueError``: 位相が 2 コマ未満、長さが違う、dt ≤ 0、露光 < 0、有限でない値。"""
    who = "diabolo_spin_from_markers"
    ph = np.asarray(phases, np.float64).reshape(-1)
    sm = np.asarray(smears, np.float64).reshape(-1)
    if len(ph) < 2 or len(sm) != len(ph) or not (np.all(np.isfinite(ph)) and np.all(np.isfinite(sm))):
        raise ValueError("%s: need >= 2 finite phases and as many smears" % who)
    if not (math.isfinite(float(dt)) and dt > 0 and math.isfinite(float(exposure)) and exposure >= 0):
        raise ValueError("%s: need dt > 0 and exposure >= 0" % who)
    dpsi = np.angle(np.exp(1j * np.diff(ph)))
    base = float(np.median(dpsi))
    w_wrapped = base / dt
    w_smear = float(np.median(sm)) / exposure if exposure > 0 else float("nan")
    if not use_smear or not math.isfinite(w_smear):
        return {"omega": w_wrapped, "omega_wrapped": w_wrapped, "omega_smear": w_smear, "branch": 0}
    cands = [(base + 2 * np.pi * k) / dt for k in range(-12, 13)]
    j = int(np.argmin([abs(abs(c) - w_smear) for c in cands]))
    return {"omega": cands[j], "omega_wrapped": w_wrapped, "omega_smear": w_smear, "branch": j - 12}


# ----------------------------------------------------------------------------------------------------------------------
# 棒の先・追跡
def _stick_tips_px(img) -> np.ndarray:
    """青い丸(棒の先の印)の重心 2 つ (2, 2) = (col, row)、col の大きい順。"""
    im = np.asarray(img, np.float64)
    w = np.clip(im[..., 2] - np.maximum(im[..., 0], im[..., 1]), 0, None)
    blue = w > 0.25
    lab, n = ndimage.label(blue)
    if n < 2:
        raise ValueError("found %d stick tips, need 2" % n)
    sizes = ndimage.sum(blue, lab, range(1, n + 1))
    rr, cc = np.mgrid[0:im.shape[0], 0:im.shape[1]]
    cs = []
    for k in 1 + np.argsort(sizes)[-2:]:
        mk = ndimage.binary_dilation(lab == k, iterations=1) * w
        cs.append(((mk * cc).sum() / mk.sum(), (mk * rr).sum() / mk.sum()))
    cs = np.array(cs)
    return cs[np.argsort(-cs[:, 0])]


def _backproject_to_plane(cam, uv, point, normal) -> np.ndarray:
    """画素 (N, 2) を、点 point・法線 normal の面へ逆投影した 3-D 点 (N, 3)。"""
    uv = np.atleast_2d(uv)
    d = _rays(cam, uv[:, 0], uv[:, 1])
    t = ((np.asarray(point) - cam["C"]) @ normal) / (d @ normal)
    return cam["C"] + t[:, None] * d


def diabolo_track(frames, cam: dict, params: dict) -> dict:
    """コマの列 → ディアボロの中心 (N, 3)・軸 (N, 3)・警報 ``ok`` (N,)・残差 (N,)。コマごとに :func:`diabolo_axis_from_image`
    (学習なし、前のコマに頼らない)。推定できないコマは NaN で ``ok = False``。**Raises** ``ValueError``: コマの列が空か列でない。"""
    who = "diabolo_track"
    if isinstance(frames, np.ndarray) and frames.ndim == 4:
        frames = list(frames)
    if not isinstance(frames, (list, tuple)) or len(frames) == 0:
        raise ValueError("%s: frames must be a non-empty list of (H, W, 3) images" % who)
    _check_cam(cam, who)
    n = len(frames)
    C = np.full((n, 3), np.nan)
    A = np.full((n, 3), np.nan)
    ok = np.zeros(n, bool)
    res = np.full(n, np.nan)
    for i, f in enumerate(frames):
        im = _check_rgb(f, who)
        try:
            r = diabolo_axis_from_image(im, cam, params)
        except ValueError:
            continue
        C[i], A[i], ok[i], res[i] = r["center"], r["axis"], r["ok"], r["residual_px"]
    return {"center": C, "axis": A, "ok": ok, "residual_px": res}


# ----------------------------------------------------------------------------------------------------------------------
# mujoco 層
def diabolo_scene_mjcf(params: dict, *, timestep: float = 2.5e-4, solref=(0.0005, 1.0), wrap_axle: bool = False) -> str:
    """第 2 実装の場面の MJCF 文字列(mujoco 不要): 空間テンドン 棒の先 → ディアボロ → 棒の先、長さの上限 = 糸(片側拘束 =
    伸びた時だけ引く = 摩擦のない滑車の厳密模型と同じ物理を、柔らかい拘束と暗黙の速度更新という別の解法で解く)。棒の先は
    mocap(各ステップで位置を書き込む)。ディアボロは自由関節の剛体(質量 = 論文の表 I、慣性は仮定。回転は糸と結合しない)。
    ``wrap_axle`` = True なら軸(半径 r)の円柱にテンドンを巻き付ける形(下側を通す、未検証)。
    **Raises** ``ValueError``: params の形、timestep ≤ 0、solref が 2 つの正の数でない。"""
    who = "diabolo_scene_mjcf"
    _check_params(params, who)
    if not (float(timestep) > 0):
        raise ValueError("%s: timestep must be > 0" % who)
    try:
        sr = [float(v) for v in solref]
    except (TypeError, ValueError) as exc:
        raise ValueError("%s: solref must be two numbers" % who) from exc
    if len(sr) != 2 or not all(math.isfinite(v) and v > 0 for v in sr):
        raise ValueError("%s: solref must be two positive numbers" % who)
    m = params["mass"]
    R = params["diameter"] / 2
    L = params["length"]
    Ia = 0.5 * m * (0.6 * R) ** 2
    It = 0.25 * m * (0.6 * R) ** 2 + m * L * L / 12
    l = params["string_length"]
    root = ET.Element("mujoco", {"model": "diabolo"})
    ET.SubElement(root, "option", {"timestep": "%g" % float(timestep), "gravity": "0 0 %g" % -float(params["g"]),
                                   "integrator": "implicitfast"})
    wb = ET.SubElement(root, "worldbody")
    for name, y in (("stickL", 0.55), ("stickR", -0.55)):
        b = ET.SubElement(wb, "body", {"name": name, "mocap": "true", "pos": "0 %g 1.0" % y})
        ET.SubElement(b, "site", {"name": "s" + name[-1], "size": "0.005"})
    body = ET.SubElement(wb, "body", {"name": "diabolo", "pos": "0 0 0.5"})
    ET.SubElement(body, "freejoint")
    ET.SubElement(body, "inertial", {"pos": "0 0 0", "mass": "%g" % m, "diaginertia": "%g %g %g" % (Ia, It, It)})
    ET.SubElement(body, "site", {"name": "sD", "pos": "0 0 0", "size": "0.003"})
    if wrap_axle:
        ET.SubElement(body, "geom", {"name": "axle", "type": "cylinder", "size": "%g 0.01" % params["axle_radius"],
                                     "euler": "0 90 0", "contype": "0", "conaffinity": "0", "mass": "0"})
        ET.SubElement(body, "site", {"name": "side", "pos": "0 0 %g" % (-3 * params["axle_radius"]), "size": "0.001"})
    ten = ET.SubElement(ET.SubElement(root, "tendon"), "spatial",
                        {"name": "string", "limited": "true", "range": "0 %g" % l, "solreflimit": "%g %g" % tuple(sr),
                         "width": "0.001"})
    ET.SubElement(ten, "site", {"site": "sL"})
    if wrap_axle:
        ET.SubElement(ten, "geom", {"geom": "axle", "sidesite": "side"})
    else:
        ET.SubElement(ten, "site", {"site": "sD"})
    ET.SubElement(ten, "site", {"site": "sR"})
    return ET.tostring(root, encoding="unicode")


def _mujoco():
    try:
        import mujoco
    except ImportError as exc:
        raise ImportError("diabolo: this function needs the optional dependency mujoco (pip install mujoco)") from exc
    return mujoco


def diabolo_mujoco_simulate(params: dict, x0, v0, sticks, t_end: float, *, timestep: float = 2.5e-4, sample_dt: float = 1e-3,
                            solref=(0.0005, 1.0), wrap_axle: bool = False, topology: bool = True) -> dict:
    """第 2 実装を走らせる(mujoco が要る、facade): 棒の動き ``sticks``(:func:`diabolo_simulate` と同じ指定)を mocap に書き込み
    ながら進め、``sample_dt`` ごとに記録する。``topology`` = True なら棒を結ぶ面より上ではテンドンの上限を外す(軸は糸に乗って
    いるだけ)。返り ``{"t", "x", "v", "length", "tension"}``(tension = テンドンの上限拘束の力)。

    **Raises** ``ImportError``: mujoco が無い。``ValueError``: sample_dt が timestep の整数倍でない等。"""
    who = "diabolo_mujoco_simulate"
    mujoco = _mujoco()
    fn = _stick_fn(sticks, who)
    n_sub = int(round(sample_dt / timestep))
    if n_sub < 1 or abs(n_sub * timestep - sample_dt) > 1e-12:
        raise ValueError("%s: sample_dt must be an integer multiple of timestep" % who)
    model = mujoco.MjModel.from_xml_string(diabolo_scene_mjcf(params, timestep=timestep, solref=solref, wrap_axle=wrap_axle))
    data = mujoco.MjData(model)
    data.qpos[:3] = _v3(x0, who + ": x0")
    data.qpos[3:7] = [1, 0, 0, 0]
    data.qvel[:3] = _v3(v0, who + ": v0")
    s0 = np.asarray(fn(0.0), np.float64)
    data.mocap_pos[0], data.mocap_pos[1] = s0[0], s0[1]
    mujoco.mj_forward(model, data)
    n = int(round(float(t_end) / sample_dt)) + 1
    T = np.arange(n) * sample_dt
    X, V, Ln, Ten = np.empty((n, 3)), np.empty((n, 3)), np.empty(n), np.zeros(n)
    tid = 0
    l = float(params["string_length"])
    lim = mujoco.mjtConstraint.mjCNSTR_LIMIT_TENDON
    for i in range(n):
        X[i], V[i], Ln[i] = data.qpos[:3], data.qvel[:3], data.ten_length[tid]
        Ten[i] = float(sum(data.efc_force[k] for k in range(data.nefc) if data.efc_type[k] == lim and data.efc_id[k] == tid))
        if i == n - 1:
            break
        for j in range(n_sub):
            s = np.asarray(fn(T[i] + (j + 1) * timestep), np.float64)
            data.mocap_pos[0], data.mocap_pos[1] = s[0], s[1]
            if topology:
                model.tendon_range[tid, 1] = 1e3 if _above_stick_plane(np.asarray(data.qpos[:3]), s[0], s[1]) else l
            mujoco.mj_step(model, data)
    return {"t": T, "x": X, "v": V, "length": Ln, "tension": Ten}
