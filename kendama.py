"""kendama — けん玉の力学と捕球の計画(18 巡目、作り直し): ひもの振り子の定理、振り上げ、弛み、自由落下、皿へ運ぶ閉ループ、
画像の予測の部品(g 既知の放物線の当てはめ、玉の穴の検出)。大皿・小皿・中皿・ろうそくを同じ計画で(技 = 姿勢と受ける皿)。

問題を 2 段に割る(Berkeley 2020 の分け方): (i) **拘束下の振り上げ** = 手元(ひもの支点)を開ループの軌道で持ち上げ、
ひもが張っている間は :func:`ballistics.tether_simulate` と同じ射影法で玉を運ぶ、(ii) **自由落下中の捕球** = ひもが弛んだ後、
知覚した (p, v) から放物線の閉形式で皿の到達点・時刻を出し、皿を速さ・加速度の上限つきで運ぶ(毎 step 計画し直す = 閉ループ)。

定理(門になる閉形式、すべて手元固定・伸びないひも・空気なし):
 1. 大振幅振り子の周期 T(θ₀) = 4√(L/g)·K(k)、k = sin(θ₀/2)、K = 第 1 種完全楕円積分。K は AGM で numpy だけで計算:
    K(k) = π / (2·AGM(1, √(1 − k²)))。小振幅で 2π√(L/g)(1 + θ₀²/16 + …) に戻る。
 2. 張力 T = m(v²/L + g cos θ)(θ は真下からの角)。弛む条件 T ≤ 0 ⇔ v² ≤ −gL cos θ(上半分で速さが足りない)。
 3. 弛む角の閉形式: 真下で速さ v₀ をもつ玉(エネルギーが「棒なら θ₀ で止まる」量 v₀² = 2gL(1 − cos θ₀))は、
    v² = 2gL(cos θ − cos θ₀) と T = 0 から 3 cos θ_s = 2 cos θ₀ → θ_s = arccos(2 cos θ₀ / 3)。θ₀ ≤ π/2 なら弛まない(None)。
    **注意**: θ₀ > π/2 の玉を「静止から放す」と張力 m g cos θ₀ < 0 で最初から弛む(ひもは押せない)ので、θ₀ は
    「真下での速さ」で与える(θ₀ ≤ π/2 では静止から放すのと同じ運動)。
 4. エネルギー: 手元固定なら snap(弛んだひもが張る瞬間)以外で保存、snap の損失 = ½ m v_r²(ballistics の門と同じ)。
 5. 振り上げの閉形式: bang-bang(加速 a を T/2、減速 −a を T/2、a = 4·lift/T²)。a > g なら減速に入った瞬間に弛み、
    玉は速さ 2·lift/T で自由に昇る → 頂点 = lift/2 − L + 2·lift²/(gT²)(手元の出発点から)。a ≤ g なら弛まず玉は昇らない。
 6. 皿の幾何: 玉(半径 r_b)は皿(縁の半径 r_c < r_b)の**縁に乗る**。静止の高さ h_c = √(r_b² − r_c²)、安定条件 = 玉の中心の
    横ずれ ≤ r_c。:func:`ballistics.cup_catch_check` は「皿 > 玉」を前提にするので、有効な皿半径 r_c + r_b と中心を h_c だけ
    上げた皿で呼ぶ(横ずれ ≤ r_c、高さ h_c ≤ h ≤ h_c + 1.5 r_b、相対速さ ≤ v_rel_max)+ 「下から昇ってくる玉は受けない」。

寸法(出どころを分ける):
 - **公表値**(日本けん玉協会 認定けん玉、メーカー公開値): 玉の直径 60 mm、横幅(大皿〜小皿の両端)70 mm、
   全長(けんに玉を刺した状態)180 mm、糸 38〜40 cm(規定なし、推奨)。
 - **ユーザー提供の JKA 16-2 型の説明(一次資料は未確認)**: けんの高さ 160 mm(公式ルール: 摩耗しても 150 mm 以上)、
   皿の目安 大皿 約 42 mm・中皿 約 38 mm・小皿 約 35 mm、重さは全体で概ね 140〜150 g(玉は桜、けんはブナ、自然木なので制限なし)、
   糸は「皿胴にある所定の穴から出して玉と連結する」。「推奨品」(海外で多い形)は大皿 約 49 mm・玉の穴 約 24 mm
   (``preset="recommended_large_cup"``)。
 - **導いた値**: 玉の穴の深さ = けん 160 + 玉 60 − 全長 180 = 40 mm(けん先が穴の底に届くと置いた。実物の穴がもっと浅いなら
   全長かけんの高さの測り方が違う —— 未確認)。
 - **仮定(公表値なし)**: 玉 75 g・けん 70 g(合計 145 g で上の 140〜150 g に合わせた)、皿の深さ = 縁に乗った玉が底に触れない
   深さ(玉の沈み + 1.5 mm: 大皿 10.1 mm・中皿 8.3 mm・小皿 7.1 mm)、皿の縁は鋭い角(玉は縁の半径 r_c の円に乗る)、
   皿胴の直径 26 mm、けんの胴の直径 18 mm、けん先の円錐 15 mm、JKA 型の玉の穴の直径 17 mm、皿胴の中心 = けん先から 58 mm(玉を刺すと玉が皿胴のすぐ上に来る)、
   皿胴の糸穴 = 皿胴の中ほどの側面、玉の糸穴 = 大きな穴の反対側。ひもの有効長(結び目 → 玉の中心)= 糸 + 玉の半径。
 空気抵抗: 直径 60 mm・75 g の玉は 1 s の自由落下で真空より約 7 cm 手前(k = ½ρC_d A/m ≈ 0.009 /m、C_d = 0.4)——
 けん玉の飛翔(≤ 0.5 s)では数 mm。

規約: 世界座標は z 上向き。けんと皿胴は 1 つの剛体。``handle`` = **手元 = 技の持つ所**(kp["grip"]: 皿持ち = 皿胴の中心、
けん持ち = けんの握り、ろうそく = けん先)。姿勢 kp["R_ken"] は技ごとに固定(皿持ち: けん先が 15° 下で大皿 / 小皿が上、けん持ち:
けん先がほぼ真下で中皿が上 —— 傾きは仮定)で、手元は並進だけ。ひもの支点 = 皿胴の糸穴 = 手元 + ``kp["tie_offset"]``、
受ける皿の縁の中心 = 手元 + ``kp["cup_offset"]``、その軸 = ``kp["cup_axis"]``。**玉を動かすのは重力(+ 抗力)とひもの張力(≥ 0)
だけ**で、けんは玉を押さない(触れたら失敗: :func:`kendama_simulate` の ``contact``)。角 θ は支点の真下から測る。全部 numpy(RK は
ballistics の ``_rk4``)。定理の門は ``tie_offset = cup_offset = 0``(点のけん = 旧来の「支点 = 皿」)でも走らせられる。
玉の回転は解かない(ひもが張っている間、玉の中心は糸の延長上にあると置く = 糸穴が結び目を向く)。

精度(正直に): 張っている間の射影法は **1 次精度で散逸的**(60° の振り子、3 s: dt = 1e-3 で振りのエネルギーの 5.7 % を失い
周期は −0.53 %、dt = 1e-4 で 0.59 % / −0.04 %)。定理の門は dt = 1e-4〜2e-4 で通し、dt = 1e-3 は「10 倍粗いと誤差も 10 倍」の
収束の門にする。振り上げの頂点は dt = 1e-3 で閉形式より 4 mm 低い(1e-4 で 0.4 mm)—— 皿の窓 45 mm の中に収まる。
"""
from __future__ import annotations

import math

import numpy as np

import ballistics as B

__all__ = [
    "kendama_params", "elliptic_k_agm", "pendulum_period_exact", "pendulum_launch_speed", "pendulum_rod_simulate",
    "tether_tension_fixed", "tether_slack_angle", "swing_up_plan", "swing_up_apex", "kendama_catch_check", "kendama_simulate",
    "catch_plan_ballistic", "noisy_perceiver", "catch_success_rate", "parabola_fit_g", "catch_plan_staged", "swing_up_lift",
    "hole_detect", "kendama_combo_simulate", "COMBO_SEQUENCES", "JKA_MOSIKAME_GRADES",
]

G = B.G


def _v3(x, name="vector"):
    a = np.asarray(x, np.float64).reshape(-1)
    if a.shape != (3,) or not np.all(np.isfinite(a)):
        raise ValueError("%s must be a finite (3,) vector" % name)
    return a


def _unit(x, name="axis"):
    a = _v3(x, name)
    n = float(np.linalg.norm(a))
    if n < 1e-12:
        raise ValueError("%s must be non-zero" % name)
    return a / n


def _pos(x, name):
    x = float(x)
    if not np.isfinite(x) or x <= 0:
        raise ValueError("%s must be a positive finite number" % name)
    return x


# ─────────────────────────────── 表 ───────────────────────────────

#: 名前つきの寸法の組 [m]。"jka_16_2" = ユーザー提供の JKA 16-2 型の説明(一次資料は未確認)+ 協会の公表値(60 / 70 / 180 mm)、
#: "recommended_large_cup" = 「推奨品」(大皿 約 49 mm、玉の穴 約 24 mm、他は同じ)。穴の直径 17 mm(JKA 型)は仮定。
KENDAMA_PRESETS = {
    "jka_16_2": {"ball_diameter": 0.060, "total_length": 0.180, "ken_length": 0.160, "width": 0.070,
                 "cup_big": 0.042, "cup_base": 0.038, "cup_small": 0.035, "hole_diameter": 0.017},
    "recommended_large_cup": {"ball_diameter": 0.060, "total_length": 0.180, "ken_length": 0.160, "width": 0.070,
                              "cup_big": 0.049, "cup_base": 0.038, "cup_small": 0.035, "hole_diameter": 0.024},
}

#: 公表値の無い寸法の仮定 [m](docstring の「仮定」)。
KENDAMA_ASSUMED = {"cup_floor_gap": 0.0015, "cross_radius": 0.013,
                   "ken_radius": 0.009, "spike_length": 0.015, "cross_from_tip": 0.058, "ken_mass": 0.070}


#: 玉を真上に引き上げて皿で受ける基本技(日本けん玉協会の級の技、ユーザーが調べた持ち方): 受ける皿・持つ所・けんの傾き。
#: 大皿 = 皿持ち(けん先は斜め下、大皿が上)、小皿 = 同じ持ち方で小皿、中皿 = けん持ち(けん先をほぼ真下、中皿が上)、
#: ろうそく = けん先をつまんで中皿で受ける。傾き(15° / 5°)と持つ所の位置は仮定。
KENDAMA_TRICKS = {
    "ozara": {"cup": "big", "grip": "cross", "tilt_deg": 15.0, "name": "大皿"},
    "kozara": {"cup": "small", "grip": "cross", "tilt_deg": 15.0, "name": "小皿"},
    "chuzara": {"cup": "base", "grip": "ken", "tilt_deg": 5.0, "name": "中皿"},
    "rousoku": {"cup": "base", "grip": "spike", "tilt_deg": 5.0, "name": "ろうそく"},
}


def _rot_y(deg: float) -> np.ndarray:
    a = math.radians(deg)
    return np.array([[math.cos(a), 0.0, math.sin(a)], [0.0, 1.0, 0.0], [-math.sin(a), 0.0, math.cos(a)]])


def _trick_pose(trick: str, geo: dict):
    """技の姿勢: けんの局所座標(原点 = 皿胴の中心、けん先 = +x、大皿 = +z)→ 世界の回転 R と、持つ所(局所)と受ける皿(局所の中心・軸・半径)。"""
    tr = KENDAMA_TRICKS[trick]
    hz, s_b, s_t = 0.5 * geo["width"], geo["s_b"], geo["s_t"]
    if tr["cup"] in ("big", "small"):
        R = _rot_y(tr["tilt_deg"])                                  # けん先が tilt だけ下を向く、大皿は上
        if tr["cup"] == "small":
            R = R @ np.diag([1.0, -1.0, -1.0])                      # けんの軸まわりに 180°: 小皿が上
    else:
        R = _rot_y(90.0 - tr["tilt_deg"])                           # けん先がほぼ真下、中皿が上
    grip = {"cross": np.zeros(3), "ken": np.array([s_b + 0.050, 0.0, 0.0]), "spike": np.array([s_t - 0.012, 0.0, 0.0])}[tr["grip"]]
    cup = {"big": (np.array([0.0, 0.0, hz]), np.array([0.0, 0.0, 1.0]), geo["r_big"]),
           "small": (np.array([0.0, 0.0, -hz]), np.array([0.0, 0.0, -1.0]), geo["r_small"]),
           "base": (np.array([s_b, 0.0, 0.0]), np.array([-1.0, 0.0, 0.0]), geo["r_base"])}[tr["cup"]]
    return R, grip, cup


def _pose_top(R, grip, geo) -> float:
    """その姿勢でのけん玉のいちばん高い所(手元から、近似): 3 つの皿の縁の円・握りの輪・けん先の点の最高点。"""
    hz, s_b, s_t = 0.5 * geo["width"], geo["s_b"], geo["s_t"]
    rings = [(np.array([0.0, 0.0, hz]), np.array([0.0, 0.0, 1.0]), geo["r_big"]),
             (np.array([0.0, 0.0, -hz]), np.array([0.0, 0.0, 1.0]), geo["r_small"]),
             (np.array([s_b, 0.0, 0.0]), np.array([1.0, 0.0, 0.0]), geo["r_base"]),
             (np.array([s_b + 0.031, 0.0, 0.0]), np.array([1.0, 0.0, 0.0]), geo["r_grip"])]
    top = float((R @ (np.array([s_t, 0.0, 0.0]) - grip))[2])
    for c, a, r in rings:
        cz = float((R @ (c - grip))[2])
        az = float((R @ a)[2])
        top = max(top, cz + r * math.sqrt(max(0.0, 1.0 - az * az)))
    return top


def kendama_params(preset: str = "jka_16_2", *, trick: str = "ozara", ball_radius: float = None, mass: float = 0.075,
                   string: float = 0.39, cup_radius_big: float = None, cup_depth: float = None, ken_length: float = None,
                   width: float = None, rho: float = 1.2, cd=0.4, cup_offset=None, tie_offset=None, cup_axis=None,
                   g: float = G) -> dict:
    """けん玉の表。既定 = ``preset="jka_16_2"``(玉 60 mm、横幅 70 mm、全長 180 mm は日本けん玉協会の公表値、けんの高さ 160 mm と
    皿 42 / 38 / 35 mm はユーザー提供の JKA 16-2 型の説明(一次資料は未確認))。``"recommended_large_cup"`` = 大皿 49 mm・穴 24 mm。

    鍵: ``ball_radius`` 0.030、``string`` 0.39(糸 = 推奨 38〜40 cm)、``pendulum_length`` = 糸 + 玉の半径(結び目 → 玉の中心、
    玉の糸穴は大きな穴の反対側と置く)、``cup_radius_big`` / ``cup_radius_base`` / ``cup_radius_small``(縁の半径)、``cup_depth``
    (大皿の深さ。既定 = 縁に乗った玉の下端の沈み r_b − √(r_b² − r_c²) + 1.5 mm = 玉が底に触れない深さ、と置く仮定)、``ken_length``(けんの高さ = けん先 → 中皿の縁、160 mm)、``width``(大皿の縁 〜 小皿の縁、70 mm)、
    ``hole_radius`` / ``hole_depth``(玉の大きな穴。深さ = けん + 玉 − 全長 = 40 mm)、``total_length``(組み立ての全長 = けん + 玉 − 穴の深さ)、
    ``cross_radius`` / ``ken_radius`` / ``spike_length`` / ``cross_from_tip``(仮定)、``mass``(玉、仮定 75 g)・``ken_mass``(仮定 70 g)。
    技 ``trick``(:data:`KENDAMA_TRICKS`: "ozara" 大皿 / "kozara" 小皿 / "chuzara" 中皿 / "ろうそく" = "rousoku")が姿勢を決める:
    ``R_ken``(けんの局所座標 → 世界: 局所はけん先 +x・大皿 +z・原点 = 皿胴の中心)、``grip``(持つ所、局所)、受ける皿
    ``catch_cup``("big" / "small" / "base")。そこから手元(= 持つ所)に対する ``cup_offset``(受ける皿の縁の中心)、``cup_axis``
    (受ける皿の軸、世界)、``tie_offset``(皿胴の糸穴: 局所 (0, −cross_radius, 0))、``top_offset``(けん玉のいちばん高い所)、
    ``cup_radius``(受ける皿の縁の半径)を出す。けんと皿胴は 1 つの剛体(姿勢は技ごとに固定、手元は並進)。
    ``cup_offset`` / ``tie_offset`` / ``cup_axis`` を渡すとその値で上書き(0 を渡すと点のけん = 支点 = 皿 = 手元: 定理の門)。
    ``catch_window`` = 0.003 m: :func:`kendama_simulate` は玉の中心が「縁に乗る高さ h_c から 3 mm 以内」に下りてきた瞬間を捕球とする
    (玉が縁に触れた = 着地。縁から 1.5 r_b 上の窓に入っただけでは捕らない: 頂点が窓の中だと頂点で「捕れて」しまう —— 測って退けた)。
    ``rho``/``cd`` = 空気密度・抗力係数(rho = 0 で真空: 定理の門はこれで走らせる)。

    fail-closed: 未知の preset、寸法 ≤ 0、皿の縁 ≥ 玉(縁で受けられない = けん玉ではない)、横幅 < 大皿の直径、糸 ≤ 玉の半径、
    穴の深さが (0, 玉の直径) の外、けん先の太さが穴に入らない、は ValueError。
    返り値には派生量 ``"cup_rest_height"`` = √(r_b² − r_c²)(受ける皿の縁に乗った玉の中心の高さ)、``"bp"``(:func:`ballistics.ball_params`、中実球)。"""
    if trick not in KENDAMA_TRICKS:
        raise ValueError("unknown trick %r (known: %s)" % (trick, ", ".join(KENDAMA_TRICKS)))
    if preset not in KENDAMA_PRESETS:
        raise ValueError("unknown preset %r (known: %s)" % (preset, ", ".join(KENDAMA_PRESETS)))
    ps = KENDAMA_PRESETS[preset]
    asm = KENDAMA_ASSUMED
    r_b = _pos(ps["ball_diameter"] / 2.0 if ball_radius is None else ball_radius, "ball_radius")
    m = _pos(mass, "mass")
    s_len = _pos(string, "string")
    r_c = _pos(ps["cup_big"] / 2.0 if cup_radius_big is None else cup_radius_big, "cup_radius_big")
    kl = _pos(ps["ken_length"] if ken_length is None else ken_length, "ken_length")
    w = _pos(ps["width"] if width is None else width, "width")
    if r_c >= r_b:
        raise ValueError("cup_radius_big must be smaller than ball_radius (the ball rests on the rim of the cup)")
    if w < 2.0 * r_c:
        raise ValueError("width must be at least the diameter of the big cup")
    if s_len <= r_b:
        raise ValueError("string must be longer than the ball radius")
    hole_r = ps["hole_diameter"] / 2.0
    hole_d = kl + 2.0 * r_b - ps["total_length"]
    if not (0.0 < hole_d < 2.0 * r_b):
        raise ValueError("hole depth = ken_length + ball diameter − total length must lie in (0, ball diameter)")
    if hole_r >= r_b:
        raise ValueError("hole must be narrower than the ball")
    def _sag(r):                                   # 縁(半径 r)に乗った玉の下端が縁の面より下がる量
        return r_b - math.sqrt(r_b * r_b - r * r)

    depth = _sag(r_c) + asm["cup_floor_gap"] if cup_depth is None else cup_depth
    if not np.isfinite(depth) or depth < 0:
        raise ValueError("cup_depth must be ≥ 0")
    r_small, r_base = ps["cup_small"] / 2.0, ps["cup_base"] / 2.0
    cross_r = asm["cross_radius"]
    geo = {"width": w, "s_b": -(kl - asm["cross_from_tip"]), "s_t": asm["cross_from_tip"], "r_big": r_c, "r_small": r_small,
           "r_base": r_base, "r_grip": max(asm["ken_radius"] + 0.0058, 0.7 * r_base + 0.0015)}
    R, grip, (c_loc, a_loc, r_catch) = _trick_pose(trick, geo)
    if r_catch >= r_b:
        raise ValueError("the catching cup must be smaller than the ball")
    cup_off = R @ (c_loc - grip) if cup_offset is None else _v3(cup_offset, "cup_offset")
    tie_off = R @ (np.array([0.0, -cross_r, 0.0]) - grip) if tie_offset is None else _v3(tie_offset, "tie_offset")
    axis = R @ a_loc if cup_axis is None else _unit(cup_axis, "cup_axis")
    top = _pose_top(R, grip, geo)
    bp = B.ball_params(r_b, m, cd, rho=rho, g=g, shell=False)
    return {"preset": preset, "ball_radius": r_b, "mass": m, "string": s_len, "pendulum_length": s_len + r_b,
            "cup_radius_big": r_c, "cup_radius_base": r_base, "cup_radius_small": r_small,
            "cup_depth": float(depth), "cup_depth_small": _sag(r_small) + asm["cup_floor_gap"],
            "cup_depth_base": _sag(r_base) + asm["cup_floor_gap"],
            "ken_length": kl, "width": w, "hole_radius": hole_r, "hole_depth": float(hole_d),
            "total_length": float(kl + 2.0 * r_b - hole_d), "cross_radius": cross_r, "ken_radius": asm["ken_radius"],
            "spike_length": asm["spike_length"], "cross_from_tip": asm["cross_from_tip"], "ken_mass": asm["ken_mass"],
            "rho": float(rho), "cd": bp["cd"], "g": float(g), "cup_offset": cup_off, "tie_offset": tie_off, "cup_axis": axis,
            "trick": trick, "catch_cup": KENDAMA_TRICKS[trick]["cup"], "R_ken": R, "grip": grip, "top_offset": float(top),
            "cup_radius": float(r_catch), "cup_rest_height": float(math.sqrt(r_b * r_b - r_catch * r_catch)),
            "catch_window": 0.003, "bp": bp}


# ─────────────────────────────── 振り子の定理 ───────────────────────────────

def elliptic_k_agm(k) -> float:
    """第 1 種完全楕円積分 K(k) = ∫₀^{π/2} dφ / √(1 − k² sin² φ) を算術幾何平均で: K(k) = π / (2·AGM(1, √(1 − k²)))。
    |k| < 1(それ以外は ValueError)。門: K(0) = π/2、K(0.5) = 1.685750354812596(公表値、パラメータ m = k² = 0.25)。"""
    k = float(k)
    if not np.isfinite(k) or abs(k) >= 1.0:
        raise ValueError("need |k| < 1")
    a, b = 1.0, math.sqrt(1.0 - k * k)
    for _ in range(64):
        if abs(a - b) <= 4.0 * np.finfo(float).eps * a:
            break
        a, b = 0.5 * (a + b), math.sqrt(a * b)
    return math.pi / (2.0 * a)


def pendulum_period_exact(L: float, theta0: float, g: float = G) -> float:
    """振幅 θ₀ ∈ (0, π) の振り子(棒、または弛まない範囲のひも)の周期 4√(L/g)·K(sin(θ₀/2))。θ₀ → 0 で 2π√(L/g)。"""
    L = _pos(L, "L")
    g = _pos(g, "g")
    theta0 = float(theta0)
    if not (0.0 < theta0 < math.pi):
        raise ValueError("need 0 < theta0 < π")
    return 4.0 * math.sqrt(L / g) * elliptic_k_agm(math.sin(0.5 * theta0))


def pendulum_launch_speed(theta0: float, L: float, g: float = G) -> float:
    """真下でこの速さを与えると振幅 θ₀ になる(エネルギー保存): v₀ = √(2gL(1 − cos θ₀))。θ₀ ∈ [0, π]。"""
    L = _pos(L, "L")
    g = _pos(g, "g")
    theta0 = float(theta0)
    if not (0.0 <= theta0 <= math.pi):
        raise ValueError("need 0 ≤ theta0 ≤ π")
    return math.sqrt(2.0 * g * L * (1.0 - math.cos(theta0)))


def pendulum_rod_simulate(L: float, theta0: float, t_end: float, dt: float = 1e-3, g: float = G, omega0: float = 0.0) -> dict:
    """棒の振り子(拘束が両側に効く: 弛まない)θ̈ = −(g/L) sin θ を RK4 で。返り値 ``{"t", "theta", "omega", "energy"}``
    (energy = ½L²ω² − gL cos θ、単位質量)。ひもでは弛む θ₀ > π/2 の周期の定理を確かめる比較用。"""
    L = _pos(L, "L")
    g = _pos(g, "g")
    if t_end < 0 or dt <= 0:
        raise ValueError("need t_end ≥ 0 and dt > 0")
    n = int(math.floor(t_end / dt + 1e-9)) + 1
    th, om = float(theta0), float(omega0)
    TH, OM = np.empty(n), np.empty(n)
    c = -g / L

    def f(th, om):
        return om, c * math.sin(th)

    for i in range(n):
        TH[i], OM[i] = th, om
        if i == n - 1:
            break
        k1 = f(th, om)
        k2 = f(th + 0.5 * dt * k1[0], om + 0.5 * dt * k1[1])
        k3 = f(th + 0.5 * dt * k2[0], om + 0.5 * dt * k2[1])
        k4 = f(th + dt * k3[0], om + dt * k3[1])
        th += dt / 6.0 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        om += dt / 6.0 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
    return {"t": np.arange(n) * dt, "theta": TH, "omega": OM, "energy": 0.5 * L * L * OM ** 2 - g * L * np.cos(TH)}


def tether_tension_fixed(v: float, theta: float, L: float, mass: float, g: float = G) -> float:
    """手元固定・伸びないひもの張力 T = m(v²/L + g cos θ)(v = 速さ、θ = 真下からの角)。負なら「ひもは押せない」= 弛む。"""
    L = _pos(L, "L")
    mass = _pos(mass, "mass")
    g = _pos(g, "g")
    v = float(v)
    if not np.isfinite(v) or v < 0:
        raise ValueError("v must be a finite speed ≥ 0")
    return mass * (v * v / L + g * math.cos(float(theta)))


def tether_slack_angle(theta0: float, L: float, g: float = G):
    """真下で速さ v₀ = √(2gL(1 − cos θ₀)) をもつ玉(棒なら θ₀ で止まるエネルギー)のひもが弛む角 θ_s(真下から)。

    導出: v² = 2gL(cos θ − cos θ₀)、T = m(v²/L + g cos θ) = m g (3 cos θ − 2 cos θ₀) = 0 → **cos θ_s = (2/3) cos θ₀**。
    上半分(cos θ_s < 0)に達するのは cos θ₀ < 0 ⇔ θ₀ > π/2 のときだけ。θ₀ ≤ π/2 なら張力は θ₀ で m g cos θ₀ ≥ 0 まで下がる
    だけで弛まない → None。θ₀ = π(頂点にちょうど届くエネルギー)で θ_s = arccos(−2/3) = 131.8°。θ₀ ∈ (0, π] 以外は ValueError。
    θ₀ > π/2 の玉を静止から放すと最初から弛む(張力 m g cos θ₀ < 0)ので、θ₀ は真下での速さで与える。"""
    L = _pos(L, "L")
    g = _pos(g, "g")
    theta0 = float(theta0)
    if not (0.0 < theta0 <= math.pi):
        raise ValueError("need 0 < theta0 ≤ π")
    if theta0 <= 0.5 * math.pi:
        return None
    return float(math.acos(2.0 * math.cos(theta0) / 3.0))


# ─────────────────────────────── 振り上げ(開ループ) ───────────────────────────────

def swing_up_plan(kp: dict, *, lift: float = 0.265, T_lift: float = 0.15, kind: str = "bang", origin=(0.0, 0.0, 0.0),
                  dodge=(0.0, 0.0, 0.0)):
    """手元(皿胴の中心。ひもの支点と大皿はそこから kp の offset だけずれて一緒に動く)の開ループ軌道: ``origin`` から真上へ ``lift`` だけ ``T_lift`` 秒で持ち上げ、以後静止。
    返り値は t → (3,) の関数(t ≤ 0 で origin、t ≥ T_lift で origin + lift·ẑ で静止)。

    ``kind="bang"``: 加速 a = 4·lift/T² を T/2、減速 −a を T/2(速度三角形)。``kind="trap"``: 加速・等速・減速を T/3 ずつ
    (速度台形、a = 9·lift/(2T²))。玉が昇るには減速の加速度が g を超える必要がある(:func:`swing_up_apex` が閉形式で答える)。
    既定 lift = 0.265 m、T = 0.15 s(a = 47 m/s² ≈ 4.8 g、手元の最高速 3.5 m/s)で玉の頂点は大皿の縁の 4.9 cm 上
    (ひもの有効長 0.42 m、大皿の縁は手元の 35 mm 上: :func:`swing_up_apex`)。

    ``dodge`` (3,)(水平): 減速に入って玉が離れた後(bang: T/2 → T、trap: 2T/3 → T)に手元を横へ ``dodge`` だけ逃がす
    (S 字の bang-bang)。玉は皿胴の糸穴の真下から真っ直ぐ昇るので、逃がさないと皿胴・小皿を突き抜ける(物理は玉とけん玉の衝突を
    解かない —— :func:`kendamaworld.kendama_clearance` で数える)。逃がした分は :func:`catch_plan_ballistic` の ``clearance`` が
    玉が大皿の縁より上に出てから戻す。"""
    lift = _pos(lift, "lift")
    T = _pos(T_lift, "T_lift")
    o = _v3(origin, "origin")
    dg = _v3(dodge, "dodge")
    if abs(dg[2]) > 0.0:
        raise ValueError("dodge must be horizontal (z = 0)")
    if kind not in ("bang", "trap"):
        raise ValueError("kind must be 'bang' or 'trap'")
    if kind == "bang":
        a = 4.0 * lift / (T * T)

        def z_of(t):
            if t <= 0.0:
                return 0.0
            if t >= T:
                return lift
            if t < 0.5 * T:
                return 0.5 * a * t * t
            return lift - 0.5 * a * (T - t) ** 2
    else:
        a = 4.5 * lift / (T * T)
        T3 = T / 3.0
        vc = a * T3

        def z_of(t):
            if t <= 0.0:
                return 0.0
            if t >= T:
                return lift
            if t < T3:
                return 0.5 * a * t * t
            if t < 2.0 * T3:
                return 0.5 * a * T3 * T3 + vc * (t - T3)
            return lift - 0.5 * a * (T - t) ** 2

    t_d = 0.5 * T if kind == "bang" else 2.0 * T / 3.0

    def u_of(t):
        if t <= t_d:
            return 0.0
        if t >= T:
            return 1.0
        x = (t - t_d) / (T - t_d)
        return 2.0 * x * x if x < 0.5 else 1.0 - 2.0 * (1.0 - x) ** 2

    def handle(t):
        t = float(t)
        return np.array([o[0], o[1], o[2] + z_of(t)]) + u_of(t) * dg

    handle.T_lift = T
    handle.dodge = dg.copy()
    handle.lift = lift
    handle.accel = a
    handle.kind = kind
    return handle


def swing_up_apex(kp: dict, *, lift: float = 0.265, T_lift: float = 0.15, kind: str = "bang", g: float = None) -> dict:
    """:func:`swing_up_plan` で真下に吊った玉(支点の L 下、静止)がどこまで昇るかの閉形式。
    減速の加速度 a > g なら減速に入った瞬間(bang: T/2、trap: 2T/3)に弛み、そのときの手元の高さ z_s と速さ v_s で自由落下
    → 頂点 z = tie_z + z_s − L + v_s²/(2g)(手元の出発点から測った玉の中心、L = ひもの有効長、tie_z = 支点の手元からの高さ)。
    a ≤ g なら弛まず、玉は支点の L 下で止まる。返り値 ``{"accel", "flies", "slack_t", "z_slack", "v_slack", "apex",
    "apex_above_handle", "apex_above_cup"}``(apex_above_handle = apex − lift、apex_above_cup = それから大皿の縁の高さを引いた量:
    皿に届くには ≥ h_c、皿の窓に入るには h_c ≤ … ≤ h_c + 1.5 r_b)。"""
    lift = _pos(lift, "lift")
    T = _pos(T_lift, "T_lift")
    g = kp["g"] if g is None else _pos(g, "g")
    L = kp["pendulum_length"]
    tie_z = float(kp["tie_offset"][2])
    if kind == "bang":
        a = 4.0 * lift / (T * T)
        t_s, z_s, v_s = 0.5 * T, 0.5 * lift, 2.0 * lift / T
    elif kind == "trap":
        a = 4.5 * lift / (T * T)
        t_s, z_s, v_s = 2.0 * T / 3.0, 0.75 * lift, 1.5 * lift / T
    else:
        raise ValueError("kind must be 'bang' or 'trap'")
    flies = a > g
    if flies:
        apex = tie_z + z_s - L + v_s * v_s / (2.0 * g)
    else:
        t_s, z_s, v_s, apex = None, None, None, tie_z + lift - L
    return {"accel": float(a), "flies": bool(flies), "slack_t": t_s, "z_slack": z_s, "v_slack": v_s, "apex": float(apex),
            "apex_above_handle": float(apex - lift), "apex_above_cup": float(apex - lift - kp["cup_offset"][2])}


# ─────────────────────────────── 皿 ───────────────────────────────

def kendama_catch_check(kp: dict, p_ball, v_ball, cup_center, cup_axis=(0.0, 0.0, 1.0), v_cup=(0.0, 0.0, 0.0),
                        v_rel_max: float = 1.0, window: float = None) -> dict:
    """玉(半径 r_b)が皿(縁の半径 r_c < r_b、縁の中心 cup_center、軸 cup_axis、速度 v_cup)に乗る幾何の判定。

    縁に乗った玉の中心は縁の面から h_c = √(r_b² − r_c²) 上、静的な安定条件は横ずれ ≤ r_c。:func:`ballistics.cup_catch_check`
    (皿 > 玉が前提)を有効な皿(半径 r_c + r_b、中心を軸方向に h_c 上げる)で呼ぶ → 横ずれ ≤ r_c、縁の面からの高さ
    h_c ≤ h ≤ h_c + 1.5 r_b、皿に対する相対速さ ≤ v_rel_max。さらに **下から昇ってくる玉(相対速度の軸成分 > 0)は受けない**
    (皿は上からしか受けられない。支点 = 皿の中心の簡略化では昇る玉が皿の位置を通り抜けるため必要)。
    ``window`` を渡すと高さの窓を「縁に最初に触れる高さ」+ window 以下に狭める(着地の判定: :func:`kendama_simulate` は
    kp["catch_window"])。横ずれ δ の玉は √(r_b² − (r_c − δ)²)(δ = 0 で h_c)で縁に触れる —— 中心からずれた玉は縁の片側に
    先に触れ、皿の中へ転がり込む(横ずれ ≤ r_c なら受けたとする)。
    縁の半径は kp["cup_radius"](受ける皿、無ければ大皿)。返り値 ``{"caught", "lateral", "height" (縁の面から), "speed" (相対), "descending"}``。"""
    axis = _unit(cup_axis, "cup_axis")
    c = _v3(cup_center, "cup_center")
    vrel = _v3(v_ball, "v_ball") - _v3(v_cup, "v_cup")
    h_c = kp["cup_rest_height"]
    r_b = kp["ball_radius"]
    res = B.cup_catch_check(p_ball, vrel, c + h_c * axis, axis, kp.get("cup_radius", kp["cup_radius_big"]) + r_b, r_b, v_rel_max)
    descending = float(vrel @ axis) <= 0.0
    if window is None:
        in_window = True
    else:                                                    # 横ずれ δ の玉が縁に最初に触れる高さ √(r_b² − (r_c − δ)²) から window 以内
        r_c = kp.get("cup_radius", kp["cup_radius_big"])
        dl = max(0.0, r_c - res["lateral"])
        h_touch = math.sqrt(max(r_b * r_b - dl * dl, 0.0))
        in_window = bool(res["height"] + h_c <= h_touch + float(window))
    return {"caught": bool(res["caught"] and descending and in_window), "lateral": res["lateral"], "height": res["height"] + h_c,
            "speed": res["speed"], "descending": bool(descending)}


# ─────────────────────────────── 2 段のシミュレーション ───────────────────────────────

def _travel_time(d: float, v_max: float, a_max: float, s: float = 0.0) -> float:
    """距離 d を bang-bang(速さ ≤ v_max、加速度 ≤ a_max)で動いて止まるまでの時間(閉形式)。``s`` = 目標へ向かう現在の速さ
    (0 ≤ s ≤ v_max に切る。s = 0 なら静止から: d ≤ v²/a で 2√(d/a)、それ以上で d/v + v/a)。動いている途中で呼んでも
    「静止から」より短い正しい残り時間を返す(止まれる距離 s²/(2a) を越えていれば減速だけ s/a)。"""
    s = min(max(0.0, s), v_max)
    if d <= s * s / (2.0 * a_max):
        return s / a_max
    v_peak = math.sqrt(a_max * d + 0.5 * s * s)                  # 加速→減速の三角形の頂点の速さ
    if v_peak <= v_max:
        return (2.0 * v_peak - s) / a_max
    cruise = d - (v_max * v_max - s * s) / (2.0 * a_max) - v_max * v_max / (2.0 * a_max)
    return (v_max - s) / a_max + v_max / a_max + cruise / v_max


def _move_bounded(pos, vel, target, dt: float, v_max: float, a_max: float):
    """皿(支点)を target へ運ぶ 1 歩(racket.racket_move と同じ bang-bang: 止まれる速さで近づき、行き過ぎたら置く)。"""
    d = target - pos
    dist = float(np.linalg.norm(d))
    if dist < 1e-12:
        dv = -vel
        dvn = float(np.linalg.norm(dv))
        if dvn > a_max * dt:
            dv = dv * (a_max * dt / dvn)
        vel2 = vel + dv
        return pos + vel2 * dt, vel2
    u = d / dist
    v_stop = max(0.0, math.sqrt(2.0 * a_max * dist) - a_max * dt)
    v_des = min(v_max, v_stop) * u
    dv = v_des - vel
    dvn = float(np.linalg.norm(dv))
    if dvn > a_max * dt:
        dv = dv * (a_max * dt / dvn)
    vel2 = vel + dv
    pos2 = pos + vel2 * dt
    if float((target - pos2) @ u) < 0.0:
        return target.copy(), np.zeros(3)
    return pos2, vel2


def kendama_simulate(kp: dict, handle, *, p0, v0, t_end: float, dt: float = 1e-3, perceive=None, catch_plan=None, g: float = None,
                     v_max: float = 2.0, a_max: float = 20.0, v_rel_max: float = 1.0, plan_from: float = 0.0,
                     stop_on_miss: bool = True, contact=None, contact_tol: float = 5e-4) -> dict:
    """けん玉の 2 段シミュレーション: ひもが張っている間は支点(**皿胴の糸穴** = 手元 + kp["tie_offset"])に繋がれた玉
    (射影法、:func:`ballistics.tether_simulate` と同じ: 支点固定・真空なら同じ軌跡、ひもの長さ = kp["pendulum_length"])、
    弛んだら自由落下(重力 + 抗力、kp["bp"]; rho = 0 で真空)。毎 step :func:`kendama_catch_check`(大皿 = 手元 + kp["cup_offset"]、
    軸 kp["cup_axis"])で捕球を判定し、捕ったら終わる。

    ``handle`` = 手元(皿胴の中心)の (3,) の固定点か t → (3,) の関数(開ループの振り上げ)。``catch_plan`` があれば、弛んだ後
    (かつ t ≥ ``plan_from``: 振り上げが終わるまでは開ループを優先する)は毎 step ``perceive`` で知覚した (p̂, v̂) を
    ``catch_plan(t, p̂, v̂, cup_state) → {"target": 大皿の縁の中心の目標 (3,), …}`` に渡し、手元を速さ ≤ v_max・加速度 ≤ a_max の
    bang-bang で「目標 − cup_offset」へ運ぶ(手元が動くと支点も動くので、玉が落ちてきて |p − 支点| = L になれば再び張る)。

    知覚 ``perceive``:
     - None → 真値 (p, v)。
     - ``perceive(t, p, v) → (p̂, v̂)``(:func:`noisy_perceiver` など)は計画が生きている step だけ呼ぶ。
     - 属性 ``observe_all = True`` の知覚(:func:`kendamaworld.camera_perceiver`)は **毎 step** ``perceive(t, p, v, scene)`` で呼ぶ
       (scene = ``{"t", "hand", "tie", "cup", "cup_axis", "taut"}`` = 手元の自己受容で分かる量 + 世界を描くための taut
       (玉の姿勢の描画の約束: 張っている間は糸穴が結び目を向き、弛んだら最後の姿勢のまま)。p も世界を描くためだけに渡す)。
       返り値が None なら計画はそのまま(最後の目標へ運び続け、目標が無ければ手元を止める)。

    **玉を動かすのは重力(+ 抗力、rho > 0 のとき)とひもの張力(≥ 0 の片側拘束)だけ**。けんは玉を押さない: ``contact(hand, p) → 隙間 [m]``
    (:func:`kendamaworld.kendama_clearance` など)を渡すと、捕球の前に隙間 < −``contact_tol`` になった step で "hit_ken" として終わる
    (けん先・皿の縁・皿胴に玉が触れた = 失敗)。捕球は ``kp["catch_window"]``(玉が縁に触れた高さ)で判定する。

    終わり方 ``end_reason``: "caught"(捕球)、"hit_ken"(けん玉に触れた)、"missed"(弛んだ後、下向きに落ちながら大皿の面より 2 r_b 以上下に来た。
    ``stop_on_miss=False`` なら止めない: snap の門に使う)、"timeout"(t_end)。
    返り値 ``{"t", "p", "v", "hand", "anchor" (= 支点 = 糸穴), "cup", "cup_v", "taut", "tension", "energy", "snap_times", "snap_loss",
    "slack_t", "caught", "catch_t", "end_reason", "lateral", "plan_log", "n_estimates", "stage", "min_gap"}``(配列は終わった step まで。
    stage = 各 step の制御の段階 ("lift" 振り上げ / "wait" 弛んだが計画前 / 計画の "stage"(hold / carry / absorb)or "plan")。slack_t = ひもが
    張った後で初めて弛んだ時刻、初めから弛んでいれば 0.0、一度も弛まなければ None。energy = ½mv² + mgz。n_estimates = 計画に
    渡した知覚の数)。初期状態が |p₀ − 支点(0)| > L、t_end < 0、dt ≤ 0、上限 ≤ 0 は ValueError。"""
    L = kp["pendulum_length"]
    m = kp["mass"]
    r_b = kp["ball_radius"]
    off = np.asarray(kp["cup_offset"], np.float64)
    tie = np.asarray(kp["tie_offset"], np.float64)
    axis = np.asarray(kp["cup_axis"], np.float64)
    bp = dict(kp["bp"])
    if g is not None:
        bp["g"] = _pos(g, "g")
    g = bp["g"]
    p = _v3(p0, "p0")
    v = _v3(v0, "v0")
    if t_end < 0 or dt <= 0 or v_max <= 0 or a_max <= 0 or v_rel_max < 0 or plan_from < 0:
        raise ValueError("need t_end ≥ 0, dt > 0, v_max > 0, a_max > 0, v_rel_max ≥ 0, plan_from ≥ 0")
    if callable(handle):
        hf = handle
    else:
        h0 = _v3(handle, "handle")
        hf = lambda t: h0  # noqa: E731
    observe_all = bool(getattr(perceive, "observe_all", False))
    if perceive is None:
        perceive = lambda t, p, v: (p, v)  # noqa: E731
    n = int(math.floor(t_end / dt + 1e-9)) + 1
    T = np.arange(n) * dt
    P, V, H, A, C, CV = (np.empty((n, 3)) for _ in range(6))
    Ten = np.zeros(n)
    Taut = np.zeros(n, bool)
    E = np.empty(n)
    snaps, loss = [], 0.0
    hand = np.asarray(hf(0.0), np.float64).copy()
    hand_v = np.zeros(3)
    if np.linalg.norm(p - (hand + tie)) > L + 1e-9:
        raise ValueError("initial state violates the string constraint (|p0 − tie point| > L)")
    Taut[0] = np.linalg.norm(p - (hand + tie)) >= L - 1e-9
    plan_active = False
    slack_t = None
    caught, catch_t, lateral, end = False, None, None, "timeout"
    plan_log = []
    last_target = None
    n_est = 0
    n_used = n
    window = kp.get("catch_window")
    stages = []
    min_gap = float("inf")
    for i in range(n):
        t = float(T[i])
        anchor = hand + tie
        dist0 = float(np.linalg.norm(p - anchor))
        P[i], V[i], H[i], A[i], CV[i] = p, v, hand, anchor, hand_v
        C[i] = hand + off
        E[i] = 0.5 * m * float(v @ v) + m * g * p[2]
        if slack_t is None:
            if i > 0 and Taut[i - 1] and not Taut[i]:
                slack_t = t
            elif i == 1 and not Taut[0] and not Taut[1]:
                slack_t = 0.0
        if contact is not None:
            gap = float(np.asarray(contact(hand, p)).reshape(-1)[0])
            min_gap = min(min_gap, gap)
        if slack_t is not None and not Taut[i]:
            chk = kendama_catch_check(kp, p, v, C[i], axis, hand_v, v_rel_max, window)
            if chk["caught"]:
                caught, catch_t, lateral, end, n_used = True, t, chk["lateral"], "caught", i + 1
                stages.append("caught")
                break
            if stop_on_miss and v[2] < 0.0 and p[2] < C[i][2] - 2.0 * r_b:
                end, lateral, n_used = "missed", chk["lateral"], i + 1
                break
        if contact is not None and gap < -contact_tol:
            end, n_used = "hit_ken", i + 1
            stages.append("hit_ken")
            break
        if i == n - 1:
            stages.append("end")
            break
        planning = catch_plan is not None and slack_t is not None and not Taut[i] and t >= plan_from
        est = None
        if observe_all:
            est = perceive(t, p.copy(), v.copy(), {"t": t, "hand": hand.copy(), "tie": anchor.copy(), "cup": C[i].copy(),
                                                   "cup_axis": axis.copy(), "taut": bool(Taut[i])})
        elif planning:
            est = perceive(t, p, v)
        # 次の手元: 計画が生きていれば bang-bang、なければ開ループの handle
        if planning:
            if not plan_active:
                plan_active = True
                hand_v = (np.asarray(hf(t + dt), np.float64) - hand) / dt
            if est is not None:
                p_hat, v_hat = est
                plan = catch_plan(t, np.asarray(p_hat, np.float64), np.asarray(v_hat, np.float64),
                                  {"p": C[i].copy(), "v": hand_v.copy(), "axis": axis, "anchor": anchor.copy(), "hand": hand.copy(),
                                   "t": t})
                plan_log.append((t, plan))
                last_target = _v3(plan["target"], "target") - off
                n_est += 1
            stages.append(plan_log[-1][1].get("stage", "plan") if plan_log else "hold")
            hand2, hand_v2 = _move_bounded(hand, hand_v, last_target if last_target is not None else hand, dt, v_max, a_max)
        elif plan_active:
            hand2, hand_v2 = _move_bounded(hand, hand_v, last_target if last_target is not None else hand, dt, v_max, a_max)
            stages.append("plan")
        else:
            hand2 = np.asarray(hf(t + dt), np.float64).copy()
            hand_v2 = (hand2 - hand) / dt
            stages.append("lift" if slack_t is None or Taut[i] else "wait")
        anchor2 = hand2 + tie
        pt, vt, _ = B._rk4((p[0], p[1], p[2]), (v[0], v[1], v[2]), (0.0, 0.0, 0.0), dt, bp)
        p2 = np.array(pt)
        v2 = np.array(vt)
        d = p2 - anchor2
        dist = float(np.linalg.norm(d))
        if dist > L:
            rhat = d / dist
            hv = (anchor2 - anchor) / dt
            vr = float((v2 - hv) @ rhat)
            if vr > 0.0:
                if dist0 < L - 1e-9:
                    snaps.append(float(T[i + 1]))
                    loss += 0.5 * m * vr * vr
                v2 = v2 - vr * rhat
                Ten[i + 1] = m * vr / dt
            p2 = anchor2 + rhat * L
            Taut[i + 1] = True
        p, v, hand, hand_v = p2, v2, hand2, hand_v2
    k = n_used
    return {"t": T[:k], "p": P[:k], "v": V[:k], "hand": H[:k], "anchor": A[:k], "cup": C[:k], "cup_v": CV[:k], "taut": Taut[:k],
            "tension": Ten[:k], "energy": E[:k], "snap_times": np.asarray(snaps), "snap_loss": float(loss), "slack_t": slack_t,
            "caught": caught, "catch_t": catch_t, "end_reason": end, "lateral": lateral, "plan_log": plan_log, "n_estimates": n_est,
            "stage": stages[:k], "min_gap": min_gap}


# ─────────────────────────────── 捕球の計画(閉形式 + 閉ループ) ───────────────────────────────

def catch_plan_ballistic(kp: dict, *, v_max: float = 2.0, a_max: float = 20.0, g: float = None, v_target: float = 0.5,
                         v_rel_max: float = 1.0, n_planes: int = 12, plane_step: float = 0.02, clearance: bool = False,
                         margin: float = 0.002):
    """弛んだ玉の (p, v) から放物線の閉形式で皿の到達点を出す計画。返り値は ``plan(t, p, v, cup_state) → dict``。

    捕球の判定は「玉が皿の窓の上端(縁の面 + h_c + 1.5 r_b)に相対速さ ≤ v_rel_max で下向きに入る」瞬間に起きるので、
    窓の上端に玉が速さ ``v_target`` で届く面を選ぶ: 頂点 z_a = z + v_z²/(2g) から z_c = z_a − (h_c + 1.5 r_b) − v_target²/(2g)。
    到達時刻は z + v_z τ − ½ g τ² = z_c + h_c + 1.5 r_b の**遅い方の根**(下降)τ = (v_z + √(v_z² − 2g(z_c + h_c + 1.5 r_b − z)))/g、
    目標の xy = (x + v_x τ, y + v_y τ)。皿が bang-bang で τ までに届かなければ(閉形式の移動時間: 静止から 2√(d/a) または
    d/v + v/a、動いていれば現在の速さ込み)面を ``plane_step`` ずつ下げて ``n_planes`` 段まで探す(下げるほど時間は増え、
    到達速さは増える)。どの面にも間に合わなければ **最上段を返し** ``feasible=False``(到達速さが最小の面に賭ける。
    「最下段へ逃げる」と到達の直前に τ → 0 で必ず不可判定になり皿が 20 cm 沈んで落とす —— 測って退けた)。

    返り値 ``{"target" (皿の中心), "t_hit", "z_plane", "v_ball_hit", "speed_hit", "feasible", "travel", "apex"}``。
    ``clearance=True``: 玉の下端が縁の面(+ ``margin``)より上に出る時刻 τ_up までは皿を**横に動かさない**(高さだけ面へ)——
    大皿の縁はけん玉のいちばん高い所なので、玉が縁の面より上なら xy がどこでもぶつからない。間に合うかは τ − τ_up で判定し、
    玉が縁の面を越えない面は不可。返り値に ``"landing"``(落下点 = 最終の目標)と ``"wait"``(τ_up、0 = 待たない)を足す。
    制限(正直に): 皿は目標で**静止して待つ**(到達時の相対速さ = 玉の速さ)。間に合わない面での「玉に合わせて皿を下げる」
    速度合わせは実装していない —— v_rel_max に頼る。抗力は無視(60 mm の玉の ≤ 0.5 s の飛翔で数 mm、毎 step 計画し直すので消える)。"""
    v_max = _pos(v_max, "v_max")
    a_max = _pos(a_max, "a_max")
    g = kp["g"] if g is None else _pos(g, "g")
    if not (0.0 <= v_target <= v_rel_max) or not np.isfinite(v_target):
        raise ValueError("need 0 ≤ v_target ≤ v_rel_max")
    if n_planes < 1 or plane_step <= 0:
        raise ValueError("need n_planes ≥ 1 and plane_step > 0")
    h_top = kp["cup_rest_height"] + 1.5 * kp["ball_radius"]
    r_b = kp["ball_radius"]
    if margin < 0 or not np.isfinite(margin):
        raise ValueError("margin must be ≥ 0")

    def plan(t, p, v, cup_state) -> dict:
        p = _v3(p, "p")
        v = _v3(v, "v")
        cup_p = _v3(cup_state["p"], "cup_state.p")
        cup_v = _v3(cup_state.get("v", (0.0, 0.0, 0.0)), "cup_state.v")
        t_a = max(0.0, v[2] / g)
        z_apex = p[2] + v[2] * t_a - 0.5 * g * t_a * t_a
        z_best = z_apex - h_top - v_target * v_target / (2.0 * g)
        best = None
        for k in range(n_planes):
            z_c = z_best - k * plane_step
            disc = v[2] * v[2] - 2.0 * g * (z_c + h_top - p[2])
            if disc < 0.0:
                continue
            tau = (v[2] + math.sqrt(disc)) / g
            if tau < 0.0:
                continue
            target = np.array([p[0] + v[0] * tau, p[1] + v[1] * tau, z_c])
            v_hit = np.array([v[0], v[1], v[2] - g * tau])
            wait = 0.0
            if clearance:
                h_clear = z_c + margin + r_b                   # 玉の中心がこの高さを越えれば下端が縁の面より上
                if p[2] < h_clear:
                    disc_u = v[2] * v[2] - 2.0 * g * (h_clear - p[2])
                    wait = (v[2] - math.sqrt(disc_u)) / g if (disc_u >= 0.0 and v[2] > 0.0) else float("inf")
            dvec = target - cup_p
            dist = float(np.linalg.norm(dvec))
            toward = float(cup_v @ dvec) / dist if dist > 1e-12 else 0.0
            travel = _travel_time(dist, v_max, a_max, toward)
            move_to = target if wait <= 0.0 else np.array([cup_p[0], cup_p[1], z_c])
            cand = {"target": move_to, "landing": target, "wait": float(wait), "t_hit": float(t) + tau, "z_plane": float(z_c),
                    "v_ball_hit": v_hit, "speed_hit": float(np.linalg.norm(v_hit)), "feasible": bool(travel <= tau - wait),
                    "travel": float(travel), "apex": float(z_apex)}
            if best is None or cand["feasible"]:
                best = cand                                   # 間に合う最初の(最も高い)面、無ければ最上段のまま(下の節を見よ)
            if cand["feasible"]:
                break
        if best is None:
            best = {"target": cup_p.copy(), "landing": cup_p.copy(), "wait": 0.0, "t_hit": None, "z_plane": float(cup_p[2]),
                    "v_ball_hit": v.copy(),
                    "speed_hit": float(np.linalg.norm(v)), "feasible": False, "travel": 0.0, "apex": float(z_apex)}
        return best

    return plan


def catch_plan_staged(kp: dict, *, v_max: float = 2.0, a_max: float = 20.0, g: float = None, margin: float = 0.005,
                      absorb_time: float = None, absorb_depth: float = 0.02):
    """段階を明示した捕球の制御(大皿・小皿・中皿・ろうそくに同じ計画を使う: 皿の向きは kp の技の姿勢から)。
    返り値は ``plan(t, p, v, cup_state) → dict``(:func:`kendama_simulate` の ``catch_plan``)。

    段階(人のコツ「膝で真上に引き上げ、糸が弛んでから皿を玉の真下へ水平に運び、着地で下げて衝撃を吸う(すくいに行かず待つ)」を写す):
     0. **lift / wait**(:func:`kendama_simulate` 側): 振り上げの間と、弛む前は計画を呼ばない = 弛んでから動かす。
     1. **hold**: 玉の下端がけん玉のいちばん高い所(手元 + kp["top_offset"]、+ ``margin``)より上に出るまで皿を動かさない
        (けんは玉を押せないので、昇ってくる玉にけんを寄せない。玉がそこまで昇らない軌道なら hold のまま = 捕らない)。
     2. **carry**: 皿を今の高さのまま**水平に**、玉が縁に乗る点の真下へ運ぶ: 玉の中心が「皿の中心 + h_c·軸」に下りてくる時刻 τ
        (z(τ) = 皿の高さ + h_c·a_z の遅い根 = 頂点を過ぎて下降中)の玉の xy から h_c·(a_x, a_y) を引いた点。
     3. **absorb**: 着地の ``absorb_time``(既定 √(absorb_depth / a_max) = bang-bang で下げる動きの折り返しの時間)前から、目標を
        ``absorb_depth`` 下げる: 着地の瞬間に皿が下向きに最高速 √(a_max·absorb_depth)(20 m/s²・2 cm で 0.63 m/s)で動いている
        = 相対速さを減らす。absorb_time を長く取ると皿は着地の前に下がり切って止まり、玉はその分深く落ちて速くなる(0.06 s で
        4 技とも縁で弾かれた —— 測って退けた)。
    返り値 ``{"target" (皿の中心の目標), "stage", "landing" (玉が縁に乗る点の真下の皿の中心), "t_land", "wait" (hold の残り), "feasible",
    "apex", "travel"}``。頂点が縁に乗る高さに届かない軌道は ``feasible=False`` で hold。
    制限(正直に): 皿の姿勢は技ごとに固定(手首を回して玉を迎えない)、抗力は予測に入れない(毎回知覚からやり直す)。"""
    v_max = _pos(v_max, "v_max")
    a_max = _pos(a_max, "a_max")
    g = kp["g"] if g is None else _pos(g, "g")
    if not (np.isfinite(absorb_depth) and absorb_depth >= 0):
        raise ValueError("need absorb_depth ≥ 0")
    absorb_time = math.sqrt(absorb_depth / a_max) if absorb_time is None else float(absorb_time)
    if not (np.isfinite(margin) and margin >= 0 and np.isfinite(absorb_time) and absorb_time >= 0):
        raise ValueError("need margin, absorb_time ≥ 0")
    r_b = kp["ball_radius"]
    h_c = kp["cup_rest_height"]
    axis = np.asarray(kp["cup_axis"], np.float64)
    off = np.asarray(kp["cup_offset"], np.float64)
    top = float(kp["top_offset"])
    mem = {"t": -np.inf, "z": None, "cleared": False}

    def plan(t, p, v, cup_state) -> dict:
        p = _v3(p, "p")
        v = _v3(v, "v")
        cup_p = _v3(cup_state["p"], "cup_state.p")
        cup_v = _v3(cup_state.get("v", (0.0, 0.0, 0.0)), "cup_state.v")
        t = float(t)
        if t < mem["t"] or mem["z"] is None:                   # 新しい試行: 受ける高さ = 計画を始めた時の皿の高さ
            mem["z"] = float(cup_p[2])
            mem["cleared"] = False
        mem["t"] = t
        z_cup = mem["z"]
        t_a = max(0.0, v[2] / g)
        z_apex = p[2] + v[2] * t_a - 0.5 * g * t_a * t_a
        z_land = z_cup + h_c * axis[2]
        disc = v[2] * v[2] - 2.0 * g * (z_land - p[2])
        hand_z = z_cup - off[2]
        h_clear = hand_z + top + margin + r_b
        if mem["cleared"] or p[2] >= h_clear:              # 一度越えたら hold に戻らない(下りてくる玉を受けに行く)
            mem["cleared"] = True
            wait = 0.0
        else:
            du = v[2] * v[2] - 2.0 * g * (h_clear - p[2])
            wait = (v[2] - math.sqrt(du)) / g if (du >= 0.0 and v[2] > 0.0) else float("inf")
        if disc < 0.0:
            return {"target": cup_p.copy(), "stage": "hold", "landing": cup_p.copy(), "t_land": None, "wait": float(wait),
                    "feasible": False, "apex": float(z_apex), "travel": 0.0}
        tau = (v[2] + math.sqrt(disc)) / g
        land = np.array([p[0] + v[0] * tau - h_c * axis[0], p[1] + v[1] * tau - h_c * axis[1], z_cup])
        dvec = land - cup_p
        dist = float(np.linalg.norm(dvec))
        toward = float(cup_v @ dvec) / dist if dist > 1e-12 else 0.0
        travel = _travel_time(dist, v_max, a_max, toward)
        feasible = bool(np.isfinite(wait) and travel <= tau - wait)
        if wait > 0.0:
            stage, target = "hold", np.array([cup_p[0], cup_p[1], z_cup])
        elif tau > absorb_time:
            stage, target = "carry", land
        else:
            stage, target = "absorb", land - np.array([0.0, 0.0, absorb_depth])
        return {"target": target, "stage": stage, "landing": land, "t_land": t + tau, "wait": float(wait), "feasible": feasible,
                "apex": float(z_apex), "travel": float(travel)}

    return plan


def swing_up_lift(kp: dict, *, apex_above_cup: float = None, T_lift: float = 0.15, g: float = None) -> float:
    """振り上げ(bang)の持ち上げ量を閉形式で: 玉の頂点が受ける皿の中心の ``apex_above_cup`` 上に来る lift(:func:`swing_up_apex` の逆)。
    頂点 − lift − cup_z = tie_z + lift/2 − L + 2 lift²/(g T²) − lift − cup_z = A を lift の 2 次方程式として正の根。
    既定 A = max(h_c + 0.9 r_b, (top_offset − cup_z) + r_b + 0.035): 玉の下端がけん玉のいちばん高い所を 35 mm 越える頂点
    (:func:`catch_plan_staged` の hold は玉がそこを越えるまで皿を寄せない。越えている時間 ≈ 2√(2·0.03/g) = 0.17 s で皿を
    横へ 10 cm 戻す)。減速の加速度 4·lift/T² が g を超えないと玉は飛ばない(ValueError)。"""
    T = _pos(T_lift, "T_lift")
    g = kp["g"] if g is None else _pos(g, "g")
    if apex_above_cup is None:
        A = max(kp["cup_rest_height"] + 0.9 * kp["ball_radius"],
                float(kp.get("top_offset", kp["cup_offset"][2])) - float(kp["cup_offset"][2]) + kp["ball_radius"] + 0.035)
    else:
        A = float(apex_above_cup)
    a2 = 2.0 / (g * T * T)
    c0 = float(kp["tie_offset"][2]) - kp["pendulum_length"] - float(kp["cup_offset"][2]) - A
    disc = 0.25 - 4.0 * a2 * c0
    if disc < 0:
        raise ValueError("no lift reaches that apex")
    lift = (0.5 + math.sqrt(disc)) / (2.0 * a2)
    if lift <= 0 or 4.0 * lift / (T * T) <= g:
        raise ValueError("the ball would not fly (deceleration ≤ g)")
    return float(lift)


def noisy_perceiver(rng, noise_pos: float = 0.0, noise_vel: float = 0.0):
    """知覚に等方ガウス雑音を足す ``perceive(t, p, v) → (p̂, v̂)``(位置 σ = noise_pos [m]、速度 σ = noise_vel [m/s])。
    負の σ は ValueError。rng = numpy.random.Generator。"""
    if noise_pos < 0 or noise_vel < 0 or not np.isfinite(noise_pos) or not np.isfinite(noise_vel):
        raise ValueError("noise σ must be finite and ≥ 0")

    def perceive(t, p, v):
        p = np.asarray(p, np.float64)
        v = np.asarray(v, np.float64)
        if noise_pos > 0:
            p = p + rng.normal(0.0, noise_pos, 3)
        if noise_vel > 0:
            v = v + rng.normal(0.0, noise_vel, 3)
        return p, v

    return perceive


def catch_success_rate(kp: dict, *, n: int = 20, seed: int = 0, noise_pos: float = 0.0, noise_vel: float = 0.0,
                       jitter_pos: float = 0.01, jitter_vel: float = 0.05, lift: float = None, T_lift: float = 0.15,
                       kind: str = "bang", t_end: float = 1.5, dt: float = 1e-3, v_max: float = 2.0, a_max: float = 20.0,
                       v_rel_max: float = 1.0, v_target: float = 0.5, origin=(0.0, 0.0, 0.0), perceiver_factory=None,
                       dodge=(0.0, -0.10, 0.0), clearance: bool = True, keep_runs: bool = False, planner: str = "staged",
                       contact=None, absorb: bool = True) -> dict:
    """大皿の成功率: 初期状態を散らして n 回(玉は支点(皿胴の糸穴)の L 下に吊り、横に σ = jitter_pos、速度に σ = jitter_vel
    (接線成分)のガウス揺らぎ)、:func:`swing_up_plan`(手元の出発点 ``origin``)で振り上げ、:func:`catch_plan_ballistic` で皿を運ぶ。

    計画: ``planner="staged"``(既定、:func:`catch_plan_staged`: hold → carry → absorb、``absorb=False`` で着地で下げない)か
    "plane"(:func:`catch_plan_ballistic`、``clearance`` つき)。``lift`` 既定 None = :func:`swing_up_lift`(技ごとに頂点が皿の
    h_c + 0.9 r_b 上)。``contact(hand, p) → 隙間`` を渡すとけん玉に触れた試行は "hit_ken" で失敗。
    知覚: 既定は :func:`noisy_perceiver`(noise_pos [m]、noise_vel [m/s]; 0 なら真値)。``perceiver_factory(i) → perceive`` を
    渡すとそれを使う(試行 i ごとに新しい知覚: :func:`kendamaworld.camera_perceiver` で画像だけから予測する閉ループ)。
    初期状態の揺らぎは知覚によらず seed で決まる(同じ seed なら真値と画像の試行が対になる)。
    返り値 ``{"rate", "n", "caught_list", "mean_lateral", "catch_times", "end_reasons", "laterals", "starts"}``
    (mean_lateral = 捕った試行の捕球時の横ずれの平均、無ければ nan。starts = 各試行の (p0, v0))。``dodge`` / ``clearance`` は
    :func:`swing_up_plan` / :func:`catch_plan_ballistic` へ(既定 = 手元を糸穴の側(−y)へ 10 cm 逃がし、玉が大皿の縁より上に出てから
    皿を戻す: 玉がけん玉を突き抜けない構え。逃がさない (0, 0, 0)・False だと 20 試行すべてで玉が皿胴を突き抜けた —— 測って退けた。
    +y へ逃がすとカメラ 2 から見てけんが玉の手前に来て玉を隠し、画像の予測の横ずれが 0.14 → 2.8 mm に増えた)。``keep_runs=True`` で各試行の :func:`kendama_simulate` の返り値と
    知覚を ``"runs"`` / ``"perceivers"`` に残す。n ≤ 0 は ValueError。"""
    if n <= 0:
        raise ValueError("n must be ≥ 1")
    if jitter_pos < 0 or jitter_vel < 0:
        raise ValueError("jitter σ must be ≥ 0")
    rng = np.random.default_rng(seed)
    rng_noise = np.random.default_rng(seed + 7919)
    L = kp["pendulum_length"]
    o = _v3(origin, "origin")
    tie0 = o + np.asarray(kp["tie_offset"], np.float64)
    if lift is None:
        lift = swing_up_lift(kp, T_lift=T_lift)
    handle = swing_up_plan(kp, lift=lift, T_lift=T_lift, kind=kind, origin=o, dodge=dodge)
    if planner == "staged":
        plan = catch_plan_staged(kp, v_max=v_max, a_max=a_max, absorb_depth=0.02 if absorb else 0.0)
    elif planner == "plane":
        plan = catch_plan_ballistic(kp, v_max=v_max, a_max=a_max, v_target=v_target, v_rel_max=v_rel_max, clearance=clearance)
    else:
        raise ValueError("planner must be 'staged' or 'plane'")
    caught_list, times, reasons, lats, starts, runs, pers = [], [], [], [], [], [], []
    for i in range(n):
        while True:
            xy = rng.normal(0.0, jitter_pos, 2)
            if float(xy @ xy) < 0.25 * L * L:
                break
        rel = np.array([xy[0], xy[1], -math.sqrt(L * L - float(xy @ xy))])
        p0 = tie0 + rel
        rhat = rel / L
        v0 = rng.normal(0.0, jitter_vel, 3)
        v0 = v0 - float(v0 @ rhat) * rhat
        starts.append((p0.copy(), v0.copy()))
        perceive = perceiver_factory(i) if perceiver_factory is not None else noisy_perceiver(rng_noise, noise_pos, noise_vel)
        r = kendama_simulate(kp, handle, p0=p0, v0=v0, t_end=t_end, dt=dt, perceive=perceive, catch_plan=plan, v_max=v_max,
                             a_max=a_max, v_rel_max=v_rel_max, plan_from=handle.T_lift, contact=contact)
        if keep_runs:
            runs.append(r)
            pers.append(perceive)
        caught_list.append(bool(r["caught"]))
        times.append(r["catch_t"])
        reasons.append(r["end_reason"])
        lats.append(r["lateral"])
    lat_c = [la for c, la in zip(caught_list, lats) if c and la is not None]
    out = {"rate": float(np.mean(caught_list)), "n": int(n), "caught_list": caught_list,
           "mean_lateral": float(np.mean(lat_c)) if lat_c else float("nan"), "catch_times": times, "end_reasons": reasons,
           "laterals": lats, "starts": starts, "lift": float(lift)}
    if keep_runs:
        out["runs"], out["perceivers"] = runs, pers
    return out


def hole_detect(img, ball_center, ball_radius, *, dark_ratio: float = 0.45, min_sat: float = 0.35, min_chroma: float = 0.1,
                min_area: int = 3) -> dict:
    """玉の像の中の暗い円盤(けん先の穴)を探す: 玉の中心 ``ball_center`` (col, row)・像の半径 ``ball_radius`` [px] の円の内側で、
    明るさ(RGB の平均)が玉の明るさの中央値の ``dark_ratio`` 倍未満、彩度 (max − min)/max ≥ ``min_sat``(灰色の糸を除く)、
    かつ色度(RGB / |RGB|)が玉の色度の中央値から ``min_chroma`` 以上離れた(陰になった玉の面は明るさだけが落ちて色度は同じ
    —— 明るさだけで拾うと影を穴と取り違えた、測って退けた)画素の連結成分のうち最大のもの。返り値 ``{"found", "col", "row", "angle" (玉の中心 → 穴の重心の像の角度 [rad]、
    atan2(Δrow, Δcol)), "offset" (距離 / ball_radius: 0 = 正面、→ 1 = 縁), "ellipticity" (短軸 / 長軸、2 次モーメントから:
    1 = 正面の円、→ 0 = 真横), "area" [px]}``。見つからなければ found False(他は NaN)。
    正面から見た穴の中心は玉の中心と重なり、横へ回るほど縁へ寄って潰れる(offset ≈ sin φ、ellipticity ≈ cos φ、φ = 穴の軸と視線の角)。
    img (H, W, 3)、ball_radius > 0 でなければ ValueError。"""
    from scipy import ndimage
    im = np.asarray(img, np.float64)
    if im.ndim != 3 or im.shape[2] != 3:
        raise ValueError("img must be (H, W, 3)")
    c = np.asarray(ball_center, np.float64).reshape(2)
    r = float(ball_radius)
    if not (np.isfinite(r) and r > 0 and np.all(np.isfinite(c))):
        raise ValueError("ball_radius must be > 0 and ball_center finite")
    H, W = im.shape[:2]
    nan = float("nan")
    miss = {"found": False, "col": nan, "row": nan, "angle": nan, "offset": nan, "ellipticity": nan, "area": 0}
    y0, y1 = max(0, int(math.floor(c[1] - r))), min(H, int(math.ceil(c[1] + r)) + 1)
    x0, x1 = max(0, int(math.floor(c[0] - r))), min(W, int(math.ceil(c[0] + r)) + 1)
    if y1 <= y0 or x1 <= x0:
        return miss
    roi = im[y0:y1, x0:x1]
    yy, xx = np.mgrid[y0:y1, x0:x1]
    inside = (xx - c[0]) ** 2 + (yy - c[1]) ** 2 <= (0.95 * r) ** 2
    if inside.sum() < 4:
        return miss
    br = roi.mean(axis=2)
    mx = roi.max(axis=2)
    sat = np.where(mx > 1e-9, (mx - roi.min(axis=2)) / np.maximum(mx, 1e-9), 0.0)
    ref = float(np.median(br[inside]))
    nrm = np.linalg.norm(roi, axis=2, keepdims=True)
    chrom = roi / np.maximum(nrm, 1e-9)
    ref_c = np.median(chrom[inside], axis=0)
    ref_c = ref_c / max(float(np.linalg.norm(ref_c)), 1e-9)
    cdist = np.linalg.norm(chrom - ref_c, axis=2)
    mask = inside & (br < dark_ratio * ref) & (sat >= min_sat) & (cdist >= min_chroma) & (nrm[..., 0] > 1e-6)
    lab, nlab = ndimage.label(mask)
    if nlab == 0:
        return miss
    sizes = ndimage.sum(mask, lab, range(1, nlab + 1))
    k = int(np.argmax(sizes)) + 1
    if sizes[k - 1] < min_area:
        return miss
    sel = lab == k
    py, px = yy[sel].astype(np.float64), xx[sel].astype(np.float64)
    cx, cy = float(px.mean()), float(py.mean())
    cov = np.cov(np.vstack([px - cx, py - cy])) if px.size > 2 else np.eye(2)
    ev = np.sort(np.linalg.eigvalsh(cov + 1e-12 * np.eye(2)))
    ell = float(math.sqrt(max(ev[0], 0.0) / max(ev[1], 1e-12)))
    dx, dy = cx - c[0], cy - c[1]
    return {"found": True, "col": cx, "row": cy, "angle": float(math.atan2(dy, dx)), "offset": float(math.hypot(dx, dy) / r),
            "ellipticity": ell, "area": int(sel.sum())}


def parabola_fit_g(t, P, *, g: float = G, t_ref: float = None) -> dict:
    """重力 g(−z)を既知とした放物線 p(t) = p_r + v_r (t − t_ref) − ½ g (t − t_ref)² ẑ を最小二乗で当てる(未知 6 = 位置と速度)。

    ``t`` (N,)、``P`` (N, 3)(NaN の行は飛ばす)。``t_ref`` 既定 = 使った最後の時刻(= その瞬間の状態を返す)。各軸は
    [1, t − t_ref] の線形最小二乗(z は ½ g (t − t_ref)² を足してから)。返り値 ``{"p", "v", "t_ref", "rms" (残差の RMS [m]),
    "n"}``。有効な点が 2 未満・時刻が全部同じ・g ≤ 0 は ValueError。真空の正確な標本なら (p, v) を丸め誤差で戻す(門)。"""
    t = np.asarray(t, np.float64).reshape(-1)
    P = np.asarray(P, np.float64).reshape(-1, 3)
    if t.shape[0] != P.shape[0]:
        raise ValueError("t and P must have the same length")
    g = _pos(g, "g")
    ok = np.isfinite(t) & np.isfinite(P).all(axis=1)
    t, P = t[ok], P[ok]
    if t.size < 2:
        raise ValueError("need at least 2 finite samples")
    if float(np.ptp(t)) <= 0.0:
        raise ValueError("samples must span a time interval")
    tr = float(t[-1]) if t_ref is None else float(t_ref)
    tau = t - tr
    A = np.column_stack([np.ones_like(tau), tau])
    Y = P + np.outer(0.5 * g * tau * tau, [0.0, 0.0, 1.0])
    coef, *_ = np.linalg.lstsq(A, Y, rcond=None)
    fit = A @ coef - np.outer(0.5 * g * tau * tau, [0.0, 0.0, 1.0])
    rms = float(np.sqrt(np.mean(np.sum((fit - P) ** 2, axis=1))))
    return {"p": coef[0].copy(), "v": coef[1].copy(), "t_ref": tr, "rms": rms, "n": int(t.size)}


# ─────────────────────────────── 連続技(19 巡目: もしかめ・3 皿の連続) ───────────────────────────────

#: 連続技の皿の順(:func:`kendama_combo_simulate` の ``sequence``)。もしかめ = 大皿 ↔ 中皿、three_cups = 大皿 → 小皿 → 中皿 → 大皿 …
COMBO_SEQUENCES = {"mosikame": ("ozara", "chuzara"), "three_cups": ("ozara", "kozara", "chuzara")}

#: 日本けん玉協会の級・段の認定の、もしかめの回数(kendama.or.jp/tricks/basic_tricks/)。多い順。
JKA_MOSIKAME_GRADES = ((100, "準初段"), (50, "1級"), (40, "2級"), (30, "3級"), (20, "4級"), (10, "5級"), (4, "6級"))


def _mosikame_grade(count: int) -> str:
    """もしかめの連続回数 → 協会の表で何級相当か(4 回未満は「級外」)。"""
    for n, name in JKA_MOSIKAME_GRADES:
        if count >= n:
            return name
    return "級外"


def _combo_poses(kp: dict) -> dict:
    """連続技の姿勢の表: 技 → {"R", "c" (受ける皿の縁の中心、皿胴の中心から、けんの局所), "a" (皿の軸、局所), "r_c", "h_c"}。
    仮定: 連続技では**持つ所 = 皿胴の中心**のまま握り替えない(手元 = 皿胴の中心、向きだけを手首で変える)。"""
    r_b = kp["ball_radius"]
    geo = {"width": kp["width"], "s_b": -(kp["ken_length"] - kp["cross_from_tip"]), "s_t": kp["cross_from_tip"],
           "r_big": kp["cup_radius_big"], "r_small": kp["cup_radius_small"], "r_base": kp["cup_radius_base"], "r_grip": 0.0}
    out = {}
    for tr in KENDAMA_TRICKS:
        if tr == "rousoku":
            continue
        R, _, (c, a, r) = _trick_pose(tr, geo)
        out[tr] = {"R": R, "c": c, "a": a, "r_c": float(r), "h_c": float(math.sqrt(r_b * r_b - r * r))}
    return out


def _rot_log(R) -> np.ndarray:
    """回転行列 → 回転ベクトル(軸 × 角、角 ∈ [0, π])。角 π は (R + I)/2 の列から軸を取る。"""
    c = max(-1.0, min(1.0, 0.5 * (float(np.trace(R)) - 1.0)))
    th = math.acos(c)
    if th < 1e-12:
        return np.zeros(3)
    if math.pi - th < 1e-6:
        M = 0.5 * (R + np.eye(3))
        k = int(np.argmax(np.diag(M)))
        ax = M[:, k] / math.sqrt(max(M[k, k], 1e-300))
        return th * ax / np.linalg.norm(ax)
    w = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]]) / (2.0 * math.sin(th))
    return th * w


def _rot_exp(w) -> np.ndarray:
    """回転ベクトル → 回転行列(Rodrigues)。"""
    th = float(np.linalg.norm(w))
    if th < 1e-15:
        return np.eye(3)
    k = np.asarray(w, np.float64) / th
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(th) * K + (1.0 - math.cos(th)) * K @ K


def _move_pos_vel(pos, vel, target_p, target_v, t_go: float, dt: float, v_max: float, a_max: float):
    """位置**と速度**を目標にする 1 歩(:func:`_move_bounded` は位置だけを目標にして止まる → 落ちてくる玉に速さを合わせられない)。

    残り時間 t_go で (x*, v*) に着く 3 次(エルミート)の軌道の今の加速度 a = (6(x* − x) − 2 t_go (2 v + v*)) / t_go² を、
    |a| ≤ a_max に切り、v + a dt を |v| ≤ v_max の球へ射影する(球への射影は縮小写像なので、実際の加速度 |Δv|/dt も ≤ a_max:
    **最後の 1 歩で加速度の上限を超えない** —— :func:`_move_bounded` は行き過ぎた歩で速度を 0 に置くので超える、卓球の回の教訓)。
    t_go ≤ dt なら速度 v* だけを追う。返り値 (pos2, vel2, acc)。"""
    pos = np.asarray(pos, np.float64)
    vel = np.asarray(vel, np.float64)
    tv = np.asarray(target_v, np.float64)
    if t_go > dt:
        a = (6.0 * (np.asarray(target_p, np.float64) - pos) - 2.0 * t_go * (2.0 * vel + tv)) / (t_go * t_go)
    else:
        a = (tv - vel) / dt
    an = float(np.linalg.norm(a))
    if an > a_max:
        a = a * (a_max / an)
    v2 = vel + a * dt
    vn = float(np.linalg.norm(v2))
    if vn > v_max:
        v2 = v2 * (v_max / vn)
    return pos + v2 * dt, v2, (v2 - vel) / dt


def kendama_combo_simulate(kp: dict, sequence=("ozara", "chuzara"), *, n_catch: int = 10, hand0=(0.0, 0.0, 1.0),
                           hand_v0=(0.0, 0.0, 0.0), z_home: float = None, apex_above_cup: float = 0.20, k_match: float = 0.8,
                           v_max: float = 2.5, a_max: float = 20.0, a_toss: float = 20.0, omega_max: float = 30.0,
                           rot_clear: float = 0.15, v_rel_max: float = 1.0, dt: float = 1e-3, perceive=None, contact=None,
                           contact_tol: float = 5e-4, controller: str = "pos_vel", t_max: float = None, g: float = None) -> dict:
    """連続技: 玉が ``sequence[0]`` の皿に乗った状態から「放つ → 飛んでいる間に持ち替え → 次の皿を着地点の真下へ運び、速さを合わせて受ける」
    を ``n_catch`` 回か最初の失敗まで繰り返す(もしかめ = ("ozara", "chuzara")、3 皿 = ("ozara", "kozara", "chuzara"))。
    手元 ``hand0`` = 皿胴の中心(持ち替えは手首で向きを変えるだけ、握り替えない: 仮定)。最初の皿へは :func:`kendama_simulate` の
    振り上げで受けて、その手元の位置・速度を ``hand0`` / ``hand_v0`` で渡す。

    段階(毎回): **absorb**(受けた皿を上限つきで止める: 玉は皿と一緒)→ **toss**(皿を a_toss で上へ加速し、速さ v_toss に達したら
    a_max(> g)で止める: 止め始めた歩で皿の抗力が負になり玉が離れる。離れた瞬間の玉の速度 = 皿の速度 → 頂点 = 離れた高さ + v²/2g)→
    **flight**(知覚した放物線から着地の時刻 τ と点を出し、手元を「位置 = 着地点の真下(高さ z_home)、速度 = k_match × 玉の着地の速度」へ
    :func:`_move_pos_vel` で運ぶ。持ち替えは玉が皿胴の中心から ``rot_clear``(0.15 m: 皿胴の中心から中皿の縁まで 0.12 m + 玉の半径)以上離れてから(知覚で。
    離れないまま着地に間に合う最後の時刻が来たらそこで始める = 3 皿の大皿 → 小皿の 180° はこちらになることがある)、角速度の上限 ``omega_max`` の
    三角形の角速度で次の姿勢へ回す。回し終わる前には受けない)→ 受けたら absorb に戻る。

    物理: 玉は皿の上では皿と一緒に動く(皿の抗力 ∝ (a_皿 + g ẑ)·軸 ≥ 0 の間。負になったら離れる)、飛んでいる間は重力(+ 抗力)と
    糸の張力(片側拘束、:func:`kendama_simulate` と同じ射影法)だけ。けんは玉を押さない(``contact(hand, p, R) → 隙間`` が −contact_tol
    を下回ったら "hit_ken": :func:`kendamaworld.kendama_clearance` の ``R_ken``)。受ける判定は :func:`kendama_catch_check`(着地の窓
    kp["catch_window"]、相対速さ ≤ ``v_rel_max``: 仮定 1 m/s)。窓に入ったのに速すぎたら "too_fast"。受けた瞬間に玉を縁に乗る位置へ置き、
    速度を皿の速度にする(非弾性・跳ねない: 仮定。置き直す距離 ≤ 窓の 3 mm)。

    放つ高さ(閉形式): 次の着地で玉の中心が乗る高さ z_r の ``apex_above_cup`` 上を頂点にする。今の玉の高さ z₀ から a_toss で加速すると
    離れる高さは z₀ + v²/(2 a_toss) なので v_toss² = 2g (z_r + A − z₀) / (1 + g / a_toss)(抗力は入れない)。
    ``controller="position"``: 飛んでいる間の手元を旧来の :func:`_move_bounded`(位置だけを目標に止まる)で運ぶ対照。
    知覚 ``perceive``: None = 真値。:func:`kendamaworld.camera_perceiver`(``flight_from="cup"``)なら毎 step
    ``perceive(t, p, v, scene)``(scene = 手元の自己受容で分かる量 + 描画用の姿勢 R_ken)を呼び、(p̂, v̂) か None を受ける。
    受けたことは手の感覚で分かる(仮定: 触覚)として ``perceive.reset()`` があれば受けた歩で呼ぶ(前の飛翔の放物線を捨てる)。

    仮定(公表値なし): 手首の角速度 ≤ 30 rad/s、手元の速さ ≤ 2.5 m/s・加速度 ≤ 20 m/s²、k_match = 0.8(人の「膝で速さを合わせる」の程度)。
    返り値 ``{"count" (最初の失敗までに受けた回数), "catches" [{"t", "trick", "rel_speed", "lateral", "apex", "z_catch" (受けた瞬間の玉の中心の高さ), "z_release", "v_release",
    "apex_closed", "rose_then_fell", "energy_drift"}], "end_reason" ("done" | "too_fast" | "hit_ken" | "missed" | "timeout"), "t", "p", "v",
    "hand", "hand_v", "hand_a", "R", "on_cup", "taut", "stage", "min_gap", "grade" (もしかめの級相当), "max_omega"}``。"""
    g = kp["g"] if g is None else _pos(g, "g")
    bp = dict(kp["bp"])
    bp["g"] = g
    poses = _combo_poses(kp)
    seq = tuple(sequence)
    if len(seq) < 2 or any(s not in poses for s in seq):
        raise ValueError("sequence must list ≥ 2 of %s" % ", ".join(poses))
    if not (a_max > g and a_toss > 0 and v_max > 0 and omega_max > 0 and dt > 0 and n_catch >= 1 and 0.0 <= k_match <= 1.0):
        raise ValueError("need a_max > g (the toss must out-decelerate gravity), a_toss, v_max, omega_max, dt > 0, n_catch ≥ 1, "
                         "0 ≤ k_match ≤ 1")
    if controller not in ("pos_vel", "position"):
        raise ValueError("controller must be 'pos_vel' or 'position'")
    a_toss = min(float(a_toss), float(a_max))
    L = kp["pendulum_length"]
    r_b = kp["ball_radius"]
    tie_loc = np.array([0.0, -kp["cross_radius"], 0.0])
    window = kp.get("catch_window")
    zh = np.array([0.0, 0.0, 1.0])
    hand = _v3(hand0, "hand0").copy()
    hand_v = _v3(hand_v0, "hand_v0").copy()
    z_home = float(hand[2]) if z_home is None else float(z_home)
    t_max = (0.9 * n_catch + 1.0) if t_max is None else float(t_max)
    kpj = {s: dict(kp, cup_radius=poses[s]["r_c"], cup_rest_height=poses[s]["h_c"]) for s in poses}

    def cup_of(h, R_, s):
        return h + R_ @ poses[s]["c"], R_ @ poses[s]["a"]

    def rest_z(s):                                           # 手元が z_home のとき、姿勢 s の皿に乗った玉の中心の高さ
        Rs = poses[s]["R"]
        return z_home + float((Rs @ poses[s]["c"])[2]) + poses[s]["h_c"] * float((Rs @ poses[s]["a"])[2])

    j = 0                                                   # 玉が乗っている皿の索引(飛んでいる間は次に受ける皿 = j + 1)
    R = poses[seq[0]]["R"].copy()
    c0, a0 = cup_of(hand, R, seq[0])
    p = c0 + poses[seq[0]]["h_c"] * a0
    v = hand_v.copy()
    on_cup, stage = True, "absorb"
    rot, toss_v, flight, last_plan = None, None, None, None
    catches = []
    end = "timeout"
    n = int(math.floor(t_max / dt)) + 1
    rec = {k: [] for k in ("t", "p", "v", "hand", "hand_v", "hand_a", "R", "on_cup", "taut", "stage")}
    min_gap, max_om = float("inf"), 0.0
    for i in range(n):
        t = i * dt
        s_cur = seq[j % len(seq)]
        s_next = seq[(j + 1) % len(seq)]
        omega = np.zeros(3)
        if rot is not None:                                  # 持ち替え: 三角形の角速度(ピーク = omega_max)
            u = min(1.0, max(0.0, (t - rot["t0"]) / rot["T"]))
            s_u = 2.0 * u * u if u < 0.5 else 1.0 - 2.0 * (1.0 - u) ** 2
            ds = ((4.0 * u if u < 0.5 else 4.0 * (1.0 - u)) / rot["T"]) if u < 1.0 else 0.0
            R = rot["R0"] @ _rot_exp(s_u * rot["w"])
            omega = rot["R0"] @ rot["w"] * ds
            max_om = max(max_om, float(np.linalg.norm(omega)))
            if u >= 1.0:
                R, rot = rot["R1"].copy(), None
        tie = hand + R @ tie_loc
        taut = bool(np.linalg.norm(p - tie) >= L - 1e-9)
        if perceive is not None:
            cc, aa = cup_of(hand, R, s_cur)
            est = perceive(t, p.copy(), v.copy(), {"t": t, "hand": hand.copy(), "tie": tie.copy(), "R_ken": R.copy(), "cup": cc,
                                                   "cup_axis": aa, "rest": cc + poses[s_cur]["h_c"] * aa, "taut": taut})
        else:
            est = (p.copy(), v.copy())
        # ── 判定(飛んでいる間) ──
        if not on_cup:
            cc, aa = cup_of(hand, R, s_next)
            v_cup = hand_v + np.cross(omega, R @ poses[s_next]["c"])
            chk = kendama_catch_check(kpj[s_next], p, v, cc, aa, v_cup, float("inf"), window)
            if chk["caught"] and rot is None and np.allclose(R, poses[s_next]["R"]):
                rel = float(np.linalg.norm(v - v_cup))
                if rel > v_rel_max:
                    end, stage = "too_fast", "too_fast"
                else:
                    zs = np.asarray(flight["z"])
                    catches.append({"t": t, "trick": s_next, "rel_speed": rel, "lateral": chk["lateral"], "apex": float(zs.max()), "z_catch": float(p[2]),
                                    "z_release": flight["z_rel"], "v_release": flight["v_rel"].copy(),
                                    "apex_closed": flight["z_rel"] + flight["v_rel"][2] ** 2 / (2.0 * g),
                                    "rose_then_fell": bool(flight["v_rel"][2] > 0 and v[2] < 0 and zs.max() > flight["z_rel"] + 1e-6
                                                           and int(np.argmax(zs)) < len(zs) - 1),
                                    "energy_drift": float(np.max(np.abs(np.asarray(flight["e"]) - flight["e"][0])))})
                    j += 1
                    s_cur, s_next = seq[j % len(seq)], seq[(j + 1) % len(seq)]
                    on_cup, stage, last_plan, flight = True, "absorb", None, None
                    p, v = cc + poses[s_cur]["h_c"] * aa, v_cup.copy()
                    if hasattr(perceive, "reset"):
                        perceive.reset()
                    if len(catches) >= n_catch:
                        end = "done"
            if end == "timeout" and not on_cup:
                if contact is not None:
                    gap = float(np.asarray(contact(hand, p, R)).reshape(-1)[0])
                    min_gap = min(min_gap, gap)
                    if gap < -contact_tol:
                        end = "hit_ken"
                if end == "timeout" and v[2] < 0.0 and p[2] < cc[2] - 2.0 * r_b:
                    end = "missed"
        for k_, x_ in (("t", t), ("p", p.copy()), ("v", v.copy()), ("hand", hand.copy()), ("hand_v", hand_v.copy()), ("R", R.copy()),
                       ("on_cup", on_cup), ("taut", taut), ("stage", stage)):
            rec[k_].append(x_)
        if end != "timeout" or i == n - 1:
            rec["hand_a"].append(np.zeros(3))
            break
        # ── 手元の制御 ──
        plan = None
        a_cmd = np.zeros(3)
        if on_cup:
            if stage == "absorb":
                a_cmd = -hand_v / dt
                if float(np.linalg.norm(hand_v)) < 1e-12:
                    stage = "toss"
                    toss_v = math.sqrt(max(0.0, 2.0 * g * (rest_z(s_next) + apex_above_cup - float(p[2])) / (1.0 + g / a_toss)))
            if stage == "toss":
                if hand_v[2] < toss_v - 1e-12:
                    a_cmd = np.array([0.0, 0.0, min(a_toss, (toss_v - hand_v[2]) / dt)])
                else:
                    a_cmd = np.array([0.0, 0.0, -a_max])      # 止め始め = 放つ
            an = float(np.linalg.norm(a_cmd))
            if an > a_max:
                a_cmd = a_cmd * (a_max / an)
            _, a_now = cup_of(hand, R, s_cur)
            if float((a_cmd + g * zh) @ a_now) < 0.0:          # 皿の抗力が負 → 玉が離れる(速度 = いまの皿の速度)
                on_cup, stage = False, "flight"
                flight = {"z_rel": float(p[2]), "v_rel": v.copy(), "z": [float(p[2])], "e": [0.5 * float(v @ v) + g * float(p[2])], "braking": True}
        else:
            if est is not None:
                ph, vh = np.asarray(est[0], np.float64), np.asarray(est[1], np.float64)
                Rn = poses[s_next]["R"]
                cn, an_ = Rn @ poses[s_next]["c"], Rn @ poses[s_next]["a"]
                disc = vh[2] * vh[2] - 2.0 * g * (rest_z(s_next) - ph[2])
                if disc >= 0.0 and np.all(np.isfinite(ph)):
                    tau = (vh[2] + math.sqrt(disc)) / g
                    land = ph + vh * tau - 0.5 * g * tau * tau * zh
                    target = np.array([land[0] - poses[s_next]["h_c"] * an_[0] - cn[0],
                                       land[1] - poses[s_next]["h_c"] * an_[1] - cn[1], z_home])
                    last_plan = {"t_land": t + tau, "target": target, "v_target": k_match * (vh - g * tau * zh), "ball": ph}
            plan = last_plan
            if flight["braking"] and hand_v[2] > 0.0:          # 放つ動きの続き: 上向きの皿を a_max(> g)で止め切るまでは計画に渡さない
                plan = None                                    # (途中で緩めると皿が玉に追いつき、玉を押し上げる = 測って退けた)
            else:
                flight["braking"] = False
            if plan is None:
                a_cmd = -hand_v / dt                           # 見えるまで止める(放った直後の止め = 放つ動きの続き)
                an = float(np.linalg.norm(a_cmd))
                if an > a_max:
                    a_cmd = a_cmd * (a_max / an)
            elif rot is None and not np.allclose(R, poses[s_next]["R"]):
                w = _rot_log(R.T @ poses[s_next]["R"])
                T_rot = 2.0 * float(np.linalg.norm(w)) / omega_max
                tau_left = plan["t_land"] - t
                far = float(np.linalg.norm(plan["ball"] - hand)) >= rot_clear
                if (far and tau_left >= T_rot + 0.02) or tau_left <= T_rot + 0.03:
                    rot = {"t0": t + dt, "T": T_rot, "R0": R.copy(), "R1": poses[s_next]["R"].copy(), "w": w}
        if plan is not None:
            if controller == "pos_vel":
                hand2, hand_v2, a_cmd = _move_pos_vel(hand, hand_v, plan["target"], plan["v_target"], plan["t_land"] - t, dt, v_max, a_max)
            else:
                hand2, hand_v2 = _move_bounded(hand, hand_v, plan["target"], dt, v_max, a_max)
                a_cmd = (hand_v2 - hand_v) / dt
        else:
            hand_v2 = hand_v + a_cmd * dt
            vn = float(np.linalg.norm(hand_v2))
            if vn > v_max:
                hand_v2 = hand_v2 * (v_max / vn)
            a_cmd = (hand_v2 - hand_v) / dt
            hand2 = hand + hand_v2 * dt
        rec["hand_a"].append(np.asarray(a_cmd, np.float64).copy())
        # ── 玉 ──
        if on_cup:
            c2, a2 = cup_of(hand2, R, s_cur)
            p, v = c2 + poses[s_cur]["h_c"] * a2, hand_v2.copy()
        else:
            pt, vt, _ = B._rk4((p[0], p[1], p[2]), (v[0], v[1], v[2]), (0.0, 0.0, 0.0), dt, bp)
            p2, v2 = np.array(pt), np.array(vt)
            tie2 = hand2 + R @ tie_loc
            d = p2 - tie2
            dist = float(np.linalg.norm(d))
            if dist > L:                                    # 糸が張った: 片側拘束(kendama_simulate と同じ射影法)
                rhat = d / dist
                vr = float((v2 - (tie2 - tie) / dt) @ rhat)
                if vr > 0.0:
                    v2 = v2 - vr * rhat
                p2 = tie2 + rhat * L
            p, v = p2, v2
            flight["z"].append(float(p[2]))
            flight["e"].append(0.5 * float(v @ v) + g * float(p[2]))
        hand, hand_v = hand2, hand_v2
    out = {k_: np.asarray(x_) for k_, x_ in rec.items() if k_ != "stage"}
    out["stage"] = rec["stage"]
    cnt = len(catches)
    out.update({"count": cnt, "catches": catches, "end_reason": end, "min_gap": min_gap, "max_omega": max_om,
                "grade": _mosikame_grade(cnt), "sequence": seq})
    return out
